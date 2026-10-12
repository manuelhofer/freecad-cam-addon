# SPDX-License-Identifier: LGPL-2.1-or-later
"""Räumlicher Materialstand als getrennte Abschnitte auf senkrechten CAD-Strahlen.

Ein Strahl darf Material unter und über einem Hohlraum tragen. Seine ursprünglichen
Abschnitte stammen aus BRep-Schnitten, nicht aus einer Oberflächenvernetzung. Kugeln
und endliche Schaftfräser mit fester Richtung schneiden über die ganze Gerade; jede andere
Schneide (Torus, Konik, Fase, Radien) setzt sich daraus zusammen (koerperteile).
Das XY-Raster bleibt eine Näherung; es ersetzt keine BRep-/NC-Qualitätsprüfung.
"""

import hashlib
import math
from collections import OrderedDict

import numpy as np
import Part
from FreeCAD import Vector

from . import uhren
from .sprache import tr

MAX_STRAHLEN = 1000000
MAX_GRENZEN = 8000000
BLOCK = 2048
GENAU = 1e-9
_GEMERKT = OrderedDict()


def _vektor(wert):
    v = np.asarray(tuple(wert), dtype=float)
    if v.shape != (3,) or not np.isfinite(v).all():
        raise ValueError(tr("rm3.fehler.geometrie"))
    return v


def koerperteile(form, laenge, toleranz):
    """Die Schneide eines Fräsers (fraeserform.Form, `laenge` hoch) als Kugeln und Zylinder auf
    seiner Achse: (innen, aussen), je eine Liste von ("kugel", z der Mitte, Radius) und
    ("schaft", z unten, Radius, Länge) – z ab der Spitze längs der Achse.

    `innen` liegt ganz im Fräser: Im Vorschub trägt es nie mehr ab, als er schneidet (kein
    freier Raum, wo noch Material steht). `aussen` umfasst ihn: Im Eilgang sieht es alles, was
    er streifen könnte. Kugel- und Schaftfräser sind genau. Jede andere Schneide ist innen eine
    Treppe: an jeder Stufe (ρ, z) des Profils ein Zylinder mit Radius ρ von z bis zum Ende der
    Schneide – das Profil steigt nach außen nie ab, so liegt jeder ganz im Fräser –, die Stufen
    höchstens `toleranz` breit und hoch, die Kugel an der Spitze eines Konikfräsers genau; außen
    der Zylinder mit dem vollen Radius ab der Spitze. Bis P-2026-10-11-90 gab es den räumlichen
    Materialstand nur nach Kugel- und Schaftfräsern – stand davor ein Torusfräser, keinen."""
    r = float(form.radius)
    if form.nur_kugel:
        teile = [("kugel", r, r), ("schaft", r, r, laenge - r)]
        return teile, teile
    if form.eben:
        teile = [("schaft", 0.0, r, laenge)]
        return teile, teile
    innen = []
    k = float(form.kugel)
    if k > GENAU:
        innen.append(("kugel", k, k))
    stufen = []
    for stueck in form.stuecke:
        if stueck.art == "eben":
            stufen.append((stueck.rho_bis, stueck.z_von))
            continue
        if k > GENAU and stueck is form.stuecke[0]:
            continue  # die Kugel an der Spitze steht schon genau da
        # Gleich weit längs des Profils: Am steilen Ende eines Eckradius stiege z sonst in einer
        # Stufe um ein Vielfaches von `toleranz`.
        if stueck.art == "gerade":
            z_von, z_bis = stueck.z_von, stueck.z_bis
            anzahl = max(
                1, math.ceil(math.hypot(stueck.rho_bis - stueck.rho_von, z_bis - z_von) / toleranz)
            )
            for n in range(1, anzahl + 1):
                rho = stueck.rho_von + (stueck.rho_bis - stueck.rho_von) * n / anzahl
                stufen.append((rho, z_von + (z_bis - z_von) * n / anzahl))
            continue
        von, bis = (stueck._winkel(x) for x in (stueck.rho_von, stueck.rho_bis))
        anzahl = max(1, math.ceil(abs(bis - von) * stueck.radius / toleranz))
        for n in range(1, anzahl + 1):
            w = von + (bis - von) * n / anzahl
            rho = stueck.mitte[0] + stueck.radius * math.cos(w)
            stufen.append((min(rho, stueck.rho_bis), float(stueck.hoehe(min(rho, stueck.rho_bis)))))
    for rho, z in stufen:
        if rho > GENAU and z < laenge - GENAU:
            innen.append(("schaft", z, rho, laenge - z))
    return innen, [("schaft", 0.0, r, laenge)]


def teile_abtragen(ziel, von, nach, achse, teile, quer=0.0, laengs=0.0):
    """Trägt die Teile (koerperteile) längs der Geraden von → nach der Spitze ab, die Achse fest.
    `quer`: jeder Radius um so viel größer (< 0: kleiner – die Sehne eines Bogens); `laengs`:
    jeder Zylinder an beiden Enden um so viel länger (< 0: kürzer). Mit beiden gleich wächst
    oder schrumpft jedes Teil rundum (die Bewegungsschranke in raum_bahn). Gibt das abgetragene
    Volumen zurück."""
    u = np.asarray(achse, dtype=float)
    a, b = np.asarray(von, dtype=float), np.asarray(nach, dtype=float)
    volumen = 0.0
    for teil in teile:
        if teil[0] == "kugel":
            _art, z, radius = teil
            if radius + quer > GENAU:
                volumen += ziel.kugel(a + z * u, b + z * u, radius + quer)
            continue
        _art, z, radius, laenge = teil
        if radius + quer > GENAU and laenge + 2 * laengs > GENAU:
            unten = z - laengs
            volumen += ziel.schaft(
                a + unten * u, b + unten * u, u, radius + quer, laenge + 2 * laengs
            )
    return volumen


# Ab so vielen Blöcken Strahlen schneiden die Nebenrechner (je Block ein boolescher Schnitt, am
# Schwenkteil ~1 s; 40 nacheinander im Hauptprozess standen 41 s; P-2026-10-11-69).
VERTEILT_AB = 4


def strahlen_stueck(form, x, y, z_von, z_bis, dx, dy, start, ende):
    """Auch im Nebenrechner: [(i, j, unten, oben)] – die Abschnitte der senkrechten Strahlen
    `start` … `ende` − 1 (Nummer i · len(y) + j) im Körper `form`, aus dem BRep-Schnitt."""
    ny = len(y)
    linien = Part.makeCompound(
        [
            Part.makeLine(
                Vector(x[i // ny], y[i % ny], z_von - 1), Vector(x[i // ny], y[i % ny], z_bis + 1)
            )
            for i in range(start, ende)
        ]
    )
    ergebnis = []
    for kante in form.common(linien).Edges:
        bb = kante.BoundBox
        if bb.XLength > GENAU or bb.YLength > GENAU:
            raise ValueError(tr("rm3.fehler.geometrie"))
        if bb.ZLength > GENAU:
            i = int(round((bb.XMin - x[0]) / dx))
            j = int(round((bb.YMin - y[0]) / dy))
            ergebnis.append((i, j, bb.ZMin, bb.ZMax))
    return ergebnis


def _verteilt(form, args, bloecke, fortschritt):
    """strahlen_stueck() je Block auf den Nebenrechnern – die Ergebnisse in der Reihenfolge der
    Blöcke; None ohne sie (dann rechnet der Aufrufer selbst)."""
    try:
        from . import nebenrechner as nr
    except ImportError:
        return None
    try:
        pool = nr.pool()
        if not pool.verfuegbar() or pool.anzahl < 2:
            return None
        brep = form.exportBrepToString()
        schluessel = "rm3-form-" + hashlib.sha1(brep.encode("utf-8")).hexdigest()
        koerper = pool.gemeinsam(schluessel, nr.Form(brep))
        auftraege = [
            pool.auftrag("raum_material", "strahlen_stueck", koerper, *args, start, ende)
            for start, ende in bloecke
        ]

        def zwischendurch():
            nr.ereignisse_ohne_eingaben()
            if fortschritt is None:
                return True
            return bool(fortschritt(nr.fortschritt_von(auftraege)))

        try:
            return pool.warten(auftraege, zwischendurch=zwischendurch)
        finally:
            pool.vergessen(schluessel)
    except nr.Abgebrochen as fehler:
        raise ValueError(tr("s5p.fehler.unvollstaendig")) from fehler
    except nr.Fehler as fehler:
        if fehler.art == "ValueError":
            raise ValueError(fehler.satz) from fehler
        return None


def _ist_quader(form):
    """Füllt `form` (ein Körper) ihren achsparallelen Hüllquader ganz aus?"""
    try:
        if len(form.Solids) != 1:
            return False
        box = form.BoundBox
        quader = box.XLength * box.YLength * box.ZLength
        return quader > 0 and abs(form.Volume - quader) <= 1e-9 * quader
    except Exception:  # noqa: BLE001 – im Zweifel schneiden
        return False


class Material:
    """Mehrere Z-Intervalle je Strahl; NaN markiert freie Speicherplätze."""

    def __init__(self, form, schritt=0.5, fortschritt=None):
        box = form.BoundBox
        if (
            not math.isfinite(schritt)
            or schritt <= 0
            or form.isNull()
            or not form.Solids
            or min(box.XLength, box.YLength, box.ZLength) <= 0
        ):
            raise ValueError(tr("rm3.fehler.geometrie"))
        nx, ny = math.ceil(box.XLength / schritt), math.ceil(box.YLength / schritt)
        if nx * ny > MAX_STRAHLEN:
            raise ValueError(tr("rm3.fehler.raster"))
        self.dx, self.dy = box.XLength / nx, box.YLength / ny
        self.x = box.XMin + (np.arange(nx) + 0.5) * self.dx
        self.y = box.YMin + (np.arange(ny) + 0.5) * self.dy
        self.z_von, self.z_bis = box.ZMin, box.ZMax
        self.schritt = max(self.dx, self.dy)
        self.ausgelassen = ()  # Unveränderliche Angaben; auch Materialkopien teilen keine Liste.
        self.bewegungsfehler = 0.0  # Einseitige zusätzliche Schranke des Simultansweeps.
        self.grenzen = np.full((nx, ny, 1, 2), np.nan)
        if _ist_quader(form):
            # Ein Quader (das übliche Rohteil): Jeder Strahl durch eine Zellmitte geht von unten
            # bis oben – ohne BRep-Schnitt (am Schwenkteil 2 s auf allen Kernen).
            self.grenzen[:, :, 0, 0] = box.ZMin
            self.grenzen[:, :, 0, 1] = box.ZMax
            return
        bloecke = [(start, min(nx * ny, start + BLOCK)) for start in range(0, nx * ny, BLOCK)]
        args = (self.x, self.y, box.ZMin, box.ZMax, self.dx, self.dy)
        stuecke = (
            _verteilt(form, args, bloecke, fortschritt) if len(bloecke) >= VERTEILT_AB else None
        )
        if stuecke is None:
            stuecke = []
            for start, ende in bloecke:
                if fortschritt is not None and not fortschritt(start / (nx * ny)):
                    raise ValueError(tr("s5p.fehler.unvollstaendig"))
                stuecke.append(strahlen_stueck(form, *args, start, ende))
        for stueck in stuecke:
            for i, j, unten, oben in stueck:
                self._eintragen(i, j, unten, oben)

    def _platz(self, anzahl):
        if anzahl <= self.grenzen.shape[2]:
            return
        neu = max(anzahl, 2 * self.grenzen.shape[2])
        nx, ny = len(self.x), len(self.y)
        if nx * ny * neu * 2 > MAX_GRENZEN:
            raise ValueError(tr("rm3.fehler.raster"))
        g = np.full((nx, ny, neu, 2), np.nan)
        g[:, :, : self.grenzen.shape[2]] = self.grenzen
        self.grenzen = g

    def _eintragen(self, i, j, unten, oben):
        g = self.grenzen[i, j]
        paare = sorted([tuple(v) for v in g if np.isfinite(v[0])] + [(unten, oben)])
        vereint = []
        for a, b in paare:
            if vereint and a <= vereint[-1][1] + GENAU:
                vereint[-1][1] = max(b, vereint[-1][1])
            else:
                vereint.append([a, b])
        self._platz(len(vereint))
        self.grenzen[i, j] = np.nan
        self.grenzen[i, j, : len(vereint)] = vereint

    def kopie(self):
        """Unabhängiger Materialzweig; Koordinaten werden unverändert geteilt."""
        neu = object.__new__(Material)
        neu.__dict__ = self.__dict__.copy()
        neu.grenzen = self.grenzen.copy()
        return neu

    @property
    def volumen(self):
        """Materialvolumen der Strahlabschnitte mit ihren tatsächlichen XY-Zellflächen."""
        return float(np.nansum(self.grenzen[..., 1] - self.grenzen[..., 0])) * self.dx * self.dy

    def belegt(self, punkte):
        """Material an Punkten (n, 3); vier Nachbarstrahlen gemeinsam für die Vorschau."""
        p = np.asarray(punkte, dtype=float)
        if p.ndim != 2 or p.shape[1] != 3 or not np.isfinite(p).all():
            raise ValueError(tr("rm3.fehler.geometrie"))
        i = np.floor((p[:, 0] - self.x[0]) / self.dx).astype(int)
        j = np.floor((p[:, 1] - self.y[0]) / self.dy).astype(int)
        treffer = np.zeros(len(p), dtype=bool)
        for di, dj in ((0, 0), (0, 1), (1, 0), (1, 1)):
            ix, iy = i + di, j + dj
            drin = (ix >= 0) & (ix < len(self.x)) & (iy >= 0) & (iy < len(self.y))
            g = self.grenzen[ix[drin], iy[drin]]
            z = p[drin, 2, None]
            treffer[drin] |= np.any((z >= g[..., 0] - GENAU) & (z <= g[..., 1] + GENAU), axis=1)
        return treffer

    def _fenster(self, unten, oben):
        ix = np.searchsorted(self.x, [unten[0], oben[0]], side="left")
        iy = np.searchsorted(self.y, [unten[1], oben[1]], side="left")
        return slice(ix[0], min(len(self.x), ix[1] + 1)), slice(iy[0], min(len(self.y), iy[1] + 1))

    def _abtragen(self, fenster, unten, oben):
        beide, anzahl, abtrag = _schneiden(self.grenzen[fenster], unten, oben)
        volumen = float(np.nansum(abtrag)) * self.dx * self.dy
        self._platz(anzahl)
        self.grenzen[fenster] = np.nan
        self.grenzen[fenster][:, :, :anzahl] = beide[:, :, :anzahl]
        return volumen

    def _abtragen_zellen(self, i, j, unten, oben):
        """Wie _abtragen, aber an einzelnen Strahlen (i, j), jeder höchstens einmal."""
        beide, anzahl, _abtrag = _schneiden(self.grenzen[i, j], unten, oben)
        self._platz(anzahl)
        self.grenzen[i, j] = np.nan
        self.grenzen[i, j, :anzahl] = beide[:, :anzahl]

    def kugel(self, von, nach, radius):
        """Eine Kugel mit MITTE von/nach schneidet ihre ganze Gerade, in jeder Richtung."""
        from .simultan_abtrag import kugelschnitt

        a, b = _vektor(von), _vektor(nach)
        if not math.isfinite(radius) or radius <= 0:
            raise ValueError(tr("rm3.fehler.geometrie"))
        f = self._fenster(np.minimum(a, b) - radius, np.maximum(a, b) + radius)
        x, y = np.meshgrid(self.x[f[0]], self.y[f[1]], indexing="ij")
        unten = kugelschnitt(x, y, a, b, radius)
        oben = -kugelschnitt(x, y, a * (1, 1, -1), b * (1, 1, -1), radius)
        return self._abtragen(f, unten, oben)

    def schaft(self, von, nach, achse, radius, laenge):
        """Endlicher Schaftfräser mit fester Achse von Spitze zum Schaft, kontinuierlich."""
        a, b, u = _vektor(von), _vektor(nach), _vektor(achse)
        if (
            not math.isfinite(radius)
            or not math.isfinite(laenge)
            or min(radius, laenge, np.linalg.norm(u)) <= 0
        ):
            raise ValueError(tr("rm3.fehler.geometrie"))
        u = u / np.linalg.norm(u)
        ecken = np.array([a, b, a + laenge * u, b + laenge * u])
        f = self._fenster(ecken.min(axis=0) - radius, ecken.max(axis=0) + radius)
        x, y = np.meshgrid(self.x[f[0]], self.y[f[1]], indexing="ij")
        unten, oben = schaftschnitt(x, y, a, b, u, radius, laenge)
        return self._abtragen(f, unten, oben)


def _schneiden(g, unten, oben):
    """Die Abschnitte `g` (…, Plätze, 2) ohne [unten, oben] (…) je Strahl: (die neuen, sortiert,
    freie Plätze NaN und hinten; wie viele höchstens belegt; die abgetragene Länge je Platz)."""
    a, b = g[..., 0], g[..., 1]
    schnitt_unten, schnitt_oben = unten[..., None], oben[..., None]
    abtrag = np.maximum(0, np.minimum(b, schnitt_oben) - np.maximum(a, schnitt_unten))
    # Nicht getroffene und völlig freie Strahlen unverändert lassen. Zwei
    # Stücke entstehen nur, wenn der Schnitt wirklich innerhalb des Materials liegt.
    trifft = (
        (schnitt_oben > a + GENAU) & (schnitt_unten < b - GENAU) & (schnitt_oben > schnitt_unten)
    )
    links = np.stack([a, np.where(trifft, np.minimum(b, schnitt_unten), b)], axis=-1)
    rechts = np.stack([np.maximum(a, schnitt_oben), b], axis=-1)
    links[links[..., 1] <= links[..., 0] + GENAU] = np.nan
    rechts[~trifft | (rechts[..., 1] <= rechts[..., 0] + GENAU)] = np.nan
    beide = np.concatenate([links, rechts], axis=-2)
    reihenfolge = np.argsort(np.nan_to_num(beide[..., 0], nan=np.inf), axis=-1)
    beide = np.take_along_axis(beide, reihenfolge[..., None], axis=-2)
    anzahl = max(1, int(np.max(np.sum(np.isfinite(beide[..., 0]), axis=-1), initial=0)))
    return beide, anzahl, abtrag


# So viele Strahlen schneidet ein Stapel (_Stapel) auf einmal – genug, dass numpy nicht je
# Bewegung von vorn anfängt, wenig genug für den Speicher (~30 Felder je Strahl).
STAPEL_STRAHLEN = 100000


class _Stapel:
    """Schnitte einer Bahn, gesammelt und auf einmal abgetragen: Abtragen ist vertauschbar (was
    zwei Bewegungen wegnehmen, ist ihre Vereinigung, in jeder Reihenfolge) – je Bewegung einzeln
    rechnete numpy je Aufruf ~100 kleine Felder, am Schwenkteil 13690-mal 1,1 ms
    (P-2026-10-11-75). Eilgänge prüft der Aufrufer nach leeren() einzeln am Material."""

    def __init__(self, material):
        self.material = material
        self.kugeln = []  # (von, nach, radius)
        self.schaefte = []  # (von, nach, radius, laenge) mit self.achse
        self.achse = None
        self.strahlen = 0

    def _dazu(self, unten, oben):
        m = self.material
        breit = (oben[0] - unten[0]) / m.dx + 2
        tief = (oben[1] - unten[1]) / m.dy + 2
        self.strahlen += max(0.0, breit) * max(0.0, tief)
        if self.strahlen >= STAPEL_STRAHLEN:
            self.leeren()

    def kugel(self, von, nach, radius):
        a, b = _vektor(von), _vektor(nach)
        if not math.isfinite(radius) or radius <= 0:
            raise ValueError(tr("rm3.fehler.geometrie"))
        self.kugeln.append((a, b, float(radius)))
        self._dazu(np.minimum(a, b) - radius, np.maximum(a, b) + radius)
        return 0.0

    def schaft(self, von, nach, achse, radius, laenge):
        a, b, u = _vektor(von), _vektor(nach), _vektor(achse)
        if (
            not math.isfinite(radius)
            or not math.isfinite(laenge)
            or min(radius, laenge, np.linalg.norm(u)) <= 0
        ):
            raise ValueError(tr("rm3.fehler.geometrie"))
        u = u / np.linalg.norm(u)
        if self.achse is not None and np.any(np.abs(self.achse - u) > 1e-12):
            self.leeren()
        self.achse = u
        self.schaefte.append((a, b, float(radius), float(laenge)))
        ecken = np.array([a, b, a + laenge * u, b + laenge * u])
        self._dazu(ecken.min(axis=0) - radius, ecken.max(axis=0) + radius)
        return 0.0

    def _strahlen(self, unten, oben):
        """Die Strahlen in den Fenstern (wie Material._fenster) aller Bewegungen: (Nummer der
        Bewegung, i, j) je Strahl."""
        m = self.material
        ix0 = np.searchsorted(m.x, unten[:, 0], side="left")
        ix1 = np.minimum(len(m.x), np.searchsorted(m.x, oben[:, 0], side="left") + 1)
        iy0 = np.searchsorted(m.y, unten[:, 1], side="left")
        iy1 = np.minimum(len(m.y), np.searchsorted(m.y, oben[:, 1], side="left") + 1)
        breit, tief = np.maximum(0, ix1 - ix0), np.maximum(0, iy1 - iy0)
        anzahl = breit * tief
        welche = np.repeat(np.arange(len(anzahl)), anzahl)
        k = np.arange(int(anzahl.sum())) - np.repeat(np.cumsum(anzahl) - anzahl, anzahl)
        return welche, ix0[welche] + k // tief[welche], iy0[welche] + k % tief[welche]

    def leeren(self):
        """Alles Gesammelte abtragen."""
        m = self.material
        teile = []  # (i, j, unten, oben)
        if self.kugeln:
            a = np.array([k[0] for k in self.kugeln])
            b = np.array([k[1] for k in self.kugeln])
            r = np.array([k[2] for k in self.kugeln])
            welche, i, j = self._strahlen(
                np.minimum(a, b) - r[:, None], np.maximum(a, b) + r[:, None]
            )
            x, y = m.x[i], m.y[j]
            spiegel = np.array([1.0, 1.0, -1.0])
            unten = _kugelschnitt_zellen(x, y, a[welche], b[welche], r[welche])
            oben = -_kugelschnitt_zellen(x, y, a[welche] * spiegel, b[welche] * spiegel, r[welche])
            teile.append((i, j, unten, oben))
        if self.schaefte:
            u = self.achse
            a = np.array([s[0] for s in self.schaefte])
            b = np.array([s[1] for s in self.schaefte])
            r = np.array([s[2] for s in self.schaefte])
            laenge = np.array([s[3] for s in self.schaefte])
            spitze = np.minimum(a, b)
            ende = np.maximum(a, b)
            weit = laenge[:, None] * u
            unten_ = np.minimum(spitze, spitze + weit) - r[:, None]
            oben_ = np.maximum(ende, ende + weit) + r[:, None]
            welche, i, j = self._strahlen(unten_, oben_)
            unten, oben = _schaftschnitt_zellen(
                m.x[i], m.y[j], a[welche], b[welche], u, r[welche], laenge[welche]
            )
            teile.append((i, j, unten, oben))
        self.kugeln, self.schaefte, self.strahlen = [], [], 0
        if not teile:
            return
        i = np.concatenate([t[0] for t in teile])
        j = np.concatenate([t[1] for t in teile])
        unten = np.concatenate([t[2] for t in teile])
        oben = np.concatenate([t[3] for t in teile])
        trifft = oben > unten
        i, j, unten, oben = i[trifft], j[trifft], unten[trifft], oben[trifft]
        if not len(i):
            return
        # Je Strahl die Vereinigung der Schnitte (Lücken bis GENAU schließt auch das Abtragen
        # nacheinander: ein so dünnes Stück fällt dort weg), dann Runde um Runde je Strahl
        # einen Abschnitt.
        strahl = i * len(m.y) + j
        reihenfolge = np.lexsort((unten, strahl))
        strahl, unten, oben = strahl[reihenfolge], unten[reihenfolge], oben[reihenfolge]
        neu_strahl = np.empty(len(strahl), dtype=bool)
        neu_strahl[0] = True
        neu_strahl[1:] = strahl[1:] != strahl[:-1]
        # Bisher höchstes oben im selben Strahl (Präfix-Maximum in Verdopplungsschritten, genau –
        # ein Versatz je Strahl kostete bei 10⁵ Strahlen mehr Stellen, als GENAU hat).
        bisher = oben.copy()
        weit = 1
        while weit < len(strahl):
            gleich = strahl[weit:] == strahl[:-weit]
            if not gleich.any():
                break
            bisher[weit:] = np.where(
                gleich, np.maximum(bisher[weit:], bisher[:-weit]), bisher[weit:]
            )
            weit *= 2
        beginnt = neu_strahl.copy()
        beginnt[1:] |= unten[1:] > bisher[:-1] + GENAU
        anfang = np.flatnonzero(beginnt)
        strahl = strahl[anfang]
        unten = unten[anfang]
        oben = np.maximum.reduceat(oben, anfang)
        runde = (
            np.arange(len(anfang))
            - np.flatnonzero(neu_strahl[anfang])[np.cumsum(neu_strahl[anfang]) - 1]
        )
        for nummer in range(int(runde.max()) + 1):
            hier = runde == nummer
            s_ = strahl[hier]
            m._abtragen_zellen(s_ // len(m.y), s_ % len(m.y), unten[hier], oben[hier])
        # Zwischen zwei Stapeln zeichnet das Fenster neu – ohne Maus und Tastatur, wie beim Warten
        # auf die Nebenrechner (_verteilt): Der Stapel rechnet nur an seinem eigenen Material
        # (am Schwenkteil stand das Neuberechnen der Ebenen sonst 4,6 s am Stück).
        with uhren.atmend():
            uhren.atmen()


def _kugelschnitt_zellen(xs, ys, a, b, radius):
    """simultan_abtrag.kugelschnitt je Strahl mit eigener Strecke a → b (n, 3) und eigenem
    Radius."""
    with np.errstate(invalid="ignore", divide="ignore"):
        d = b - a
        dx, dy = xs - a[:, 0], ys - a[:, 1]
        quer2 = d[:, 0] ** 2 + d[:, 1] ** 2
        senkrecht = quer2 < 1e-20
        q = np.where(senkrecht, 1.0, quer2)
        lang2 = np.where(senkrecht, 1.0, np.sum(d * d, axis=1))
        r2 = radius**2
        t0 = (dx * d[:, 0] + dy * d[:, 1]) / q
        rho2 = np.maximum(0.0, dx**2 + dy**2 - t0**2 * quer2)
        innen = r2 - rho2
        t = t0 - d[:, 2] * np.sqrt(np.maximum(innen, 0) / (q * lang2))
        t = np.clip(t, 0.0, 1.0)
        innen = r2 - (dx - t * d[:, 0]) ** 2 - (dy - t * d[:, 1]) ** 2
        schraeg = np.where(
            innen >= 0, a[:, 2] + t * d[:, 2] - np.sqrt(np.maximum(innen, 0)), np.inf
        )
        innen = r2 - dx**2 - dy**2
        gerade = np.where(
            innen >= 0, np.minimum(a[:, 2], b[:, 2]) - np.sqrt(np.maximum(innen, 0)), np.inf
        )
        return np.where(senkrecht, gerade, schraeg)


def _schaftschnitt_zellen(xs, ys, a, b, u, radius, laenge):
    """schaftschnitt je Strahl mit eigener Strecke a → b (n, 3), eigenem Radius und eigener Länge;
    die Achse `u` (Einheitsvektor) für alle gleich. Die Vektoren in Komponenten: Summen über die
    letzte Achse (n, 3) sind in numpy so langsam wie alles andere zusammen."""
    with np.errstate(invalid="ignore", divide="ignore"):
        ux, uy, uz = (float(c) for c in u)
        dx, dy, dz = b[:, 0] - a[:, 0], b[:, 1] - a[:, 1], b[:, 2] - a[:, 2]
        wx, wy, wz = xs - a[:, 0], ys - a[:, 1], -a[:, 2]
        h0 = wx * ux + wy * uy + wz * uz
        hd = dx * ux + dy * uy + dz * uz
        hz = uz
        # v = w − h0·u, q = d − hd·u (quer zur Achse), e = (0, 0, 1) − hz·u
        vx, vy, vz = wx - h0 * ux, wy - h0 * uy, wz - h0 * uz
        qx, qy, qz = dx - hd * ux, dy - hd * uy, dz - hd * uz
        ex, ey, ez = -hz * ux, -hz * uy, 1.0 - hz * uz
        ee = ex * ex + ey * ey + ez * ez
        r2 = radius**2
        unten, oben = np.full(xs.shape, np.inf), np.full(xs.shape, -np.inf)

        def nimm(z, t):
            endlich = np.isfinite(z) & np.isfinite(t)
            z, t = np.where(endlich, z, 0), np.where(endlich, t, 0)
            h = h0 + hz * z - hd * t
            rx, ry, rz = vx + z * ex - t * qx, vy + z * ey - t * qy, vz + z * ez - t * qz
            gut = (
                endlich
                & (t >= -GENAU)
                & (t <= 1 + GENAU)
                & (h >= -GENAU)
                & (h <= laenge + GENAU)
                & (rx * rx + ry * ry + rz * rz <= r2 + GENAU)
            )
            np.minimum(unten, np.where(gut, z, np.inf), out=unten)
            np.maximum(oben, np.where(gut, z, -np.inf), out=oben)

        for t in (0.0, 1.0):
            rx, ry, rz = vx - t * qx, vy - t * qy, vz - t * qz
            lo, hi = _nullstellen(
                ee, 2 * (rx * ex + ry * ey + rz * ez), rx * rx + ry * ry + rz * rz - r2
            )
            if abs(hz) > 1e-14:
                stirnen = ((-h0 + hd * t) / hz, (laenge - h0 + hd * t) / hz)
                lo = np.maximum(lo, np.minimum(*stirnen))
                hi = np.minimum(hi, np.maximum(*stirnen))
            nimm(lo, np.full(xs.shape, t))
            nimm(hi, np.full(xs.shape, t))
        for h in (np.zeros(xs.shape), laenge * np.ones(xs.shape)):
            if abs(hz) > 1e-14:
                z0, zt = (h - h0) / hz, hd / hz
                rx, ry, rz = vx + z0 * ex, vy + z0 * ey, vz + z0 * ez
                sx, sy, sz = zt * ex - qx, zt * ey - qy, zt * ez - qz
                lo, hi = _nullstellen(
                    sx * sx + sy * sy + sz * sz,
                    2 * (rx * sx + ry * sy + rz * sz),
                    rx * rx + ry * ry + rz * rz - r2,
                )
                for t in (np.maximum(0, lo), np.minimum(1, hi)):
                    z = z0 + np.where(np.isfinite(t), t, 0) * zt
                    nimm(np.where(np.isfinite(t), z, np.inf), t)
            else:
                schief = np.abs(hd) > 1e-14
                t = np.where(schief, (h0 - h) / np.where(schief, hd, 1.0), np.nan)
                rx, ry, rz = vx - t * qx, vy - t * qy, vz - t * qz
                lo, hi = _nullstellen(
                    ee, 2 * (rx * ex + ry * ey + rz * ez), rx * rx + ry * ry + rz * rz - r2
                )
                nimm(lo, t)
                nimm(hi, t)
        qq = qx * qx + qy * qy + qz * qz
        quer = qq > 1e-14
        if quer.any():
            qq = np.where(quer, qq, 1.0)
            t0 = np.where(quer, (vx * qx + vy * qy + vz * qz) / qq, np.nan)
            tz = np.where(quer, (ex * qx + ey * qy + ez * qz) / qq, np.nan)
            rx, ry, rz = vx - t0 * qx, vy - t0 * qy, vz - t0 * qz
            sx, sy, sz = ex - tz * qx, ey - tz * qy, ez - tz * qz
            lo, hi = _nullstellen(
                sx * sx + sy * sy + sz * sz,
                2 * (rx * sx + ry * sy + rz * sz),
                rx * rx + ry * ry + rz * rz - r2,
            )
            nimm(lo, t0 + np.where(np.isfinite(lo), lo, 0) * tz)
            nimm(hi, t0 + np.where(np.isfinite(hi), hi, 0) * tz)
        return unten, oben


def _nullstellen(a, b, c):
    """Beide Grenzen a*z²+b*z+c <= 0; lineare und konstante Fälle eingeschlossen."""
    a, b, c = np.broadcast_arrays(a, b, c)
    d = b * b - 4 * a * c
    quadratisch = a > 1e-14
    wurzel = np.sqrt(np.maximum(0, d))
    mit = np.where(quadratisch, 2 * a, 1)
    lo, hi = (-b - wurzel) / mit, (-b + wurzel) / mit
    linear = ~quadratisch & (np.abs(b) > 1e-14)
    z = -c / np.where(linear, b, 1)
    lo = np.where(linear, np.where(b < 0, z, -np.inf), lo)
    hi = np.where(linear, np.where(b > 0, z, np.inf), hi)
    konstant = ~quadratisch & ~linear
    lo = np.where(konstant & (c <= GENAU), -np.inf, lo)
    hi = np.where(konstant & (c <= GENAU), np.inf, hi)
    fehlt = (quadratisch & (d < -GENAU)) | (konstant & (c > GENAU))
    return np.where(fehlt, np.inf, lo), np.where(fehlt, -np.inf, hi)


def schaftschnitt(xs, ys, von, nach, achse, radius, laenge):
    """Z-Intervall eines Strahls im Sweep eines beliebig gerichteten endlichen Zylinders.

    Die zulässigen (z,t) erfüllen einen quadratischen Radialabstand, t in [0,1]
    und eine lineare axiale Grenze. Z-Extrema liegen bei t=0/1, an einer Stirn
    oder am radialen Rand mit verschwindender Ableitung nach t. Alle werden geprüft.
    """
    a, b, u = _vektor(von), _vektor(nach), _vektor(achse)
    if not np.isfinite([radius, laenge]).all() or min(radius, laenge, np.linalg.norm(u)) <= 0:
        raise ValueError(tr("rm3.fehler.geometrie"))
    u = u / np.linalg.norm(u)
    xs, ys = np.broadcast_arrays(np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))
    d = b - a
    w = np.stack(np.broadcast_arrays(xs - a[0], ys - a[1], np.full_like(xs, -a[2])), axis=-1)
    e = np.array([0.0, 0.0, 1.0])
    h0, hd, hz = w @ u, float(d @ u), float(u[2])
    v, dz, vz = w - h0[..., None] * u, d - hd * u, e - hz * u
    unten, oben = np.full(xs.shape, np.inf), np.full(xs.shape, -np.inf)

    def nimm(z, t):
        endlich = np.isfinite(z) & np.isfinite(t)
        z, t = np.where(endlich, z, 0), np.where(endlich, t, 0)
        h = h0 + hz * z - hd * t
        radial = v + z[..., None] * vz - t[..., None] * dz
        gut = (
            endlich
            & (t >= -GENAU)
            & (t <= 1 + GENAU)
            & (h >= -GENAU)
            & (h <= laenge + GENAU)
            & (np.sum(radial * radial, axis=-1) <= radius**2 + GENAU)
        )
        np.minimum(unten, np.where(gut, z, np.inf), out=unten)
        np.maximum(oben, np.where(gut, z, -np.inf), out=oben)

    # Rand der Zeit und gegebenenfalls Schnitte durch die Stirnflächen.
    for t in (0.0, 1.0):
        r = v - t * dz
        lo, hi = _nullstellen(float(vz @ vz), 2 * (r @ vz), np.sum(r * r, axis=-1) - radius**2)
        if abs(hz) > 1e-14:
            stirnen = ((-h0 + hd * t) / hz, (laenge - h0 + hd * t) / hz)
            lo = np.maximum(lo, np.minimum(*stirnen))
            hi = np.minimum(hi, np.maximum(*stirnen))
        nimm(lo, np.full(xs.shape, t))
        nimm(hi, np.full(xs.shape, t))
    for h in (0.0, laenge):
        if abs(hz) > 1e-14:
            z0, zt = (h - h0) / hz, hd / hz
            r, s = v + z0[..., None] * vz, zt * vz - dz
            lo, hi = _nullstellen(float(s @ s), 2 * (r @ s), np.sum(r * r, axis=-1) - radius**2)
            for t in (np.maximum(0, lo), np.minimum(1, hi)):
                z = z0 + np.where(np.isfinite(t), t, 0) * zt
                nimm(np.where(np.isfinite(t), z, np.inf), t)
        elif abs(hd) > 1e-14:
            t = (h0 - h) / hd
            r = v - t[..., None] * dz
            lo, hi = _nullstellen(float(vz @ vz), 2 * (r @ vz), np.sum(r * r, axis=-1) - radius**2)
            nimm(lo, t)
            nimm(hi, t)
    dd = float(dz @ dz)
    if dd > 1e-14:
        t0, tz = (v @ dz) / dd, float(vz @ dz) / dd
        r, s = v - t0[..., None] * dz, vz - tz * dz
        lo, hi = _nullstellen(float(s @ s), 2 * (r @ s), np.sum(r * r, axis=-1) - radius**2)
        nimm(lo, t0 + np.where(np.isfinite(lo), lo, 0) * tz)
        nimm(hi, t0 + np.where(np.isfinite(hi), hi, 0) * tz)
    return unten, oben


def _jobs_vor(job):
    from . import schwenken as sw

    folge = sw.folge_vor(job)  # Grundjob, Ebenen oder Aufspannungen davor (W-018)
    if not folge:
        raise ValueError(tr("rm3.fehler.geometrie"))
    return folge


def _simultane_vorbereiten(job):
    """Wirkliche NC und Kinematik der Simultanvorgänger, einmal pro Materialanfrage."""
    from . import maschinenzugang as mz
    from . import materialstand as ms
    from . import simultan_operation as so
    from . import simultan_planung as sp
    from . import werkzeuge as wz

    result = {}
    bib = None
    for davor in _jobs_vor(job):
        for op in ms.operationen_vor(davor):
            if not so.ist_simultan(op):
                continue
            m = mz._maschine(davor, op)
            key = (davor.Name, op.Name)
            if m is None or m is False:
                result[key] = m
                continue
            if bib is None:
                bib = wz.Bibliothek.laden()
            try:
                programm = so.programm(op, m)
            except ValueError:
                result[key] = False
                continue
            result[key] = (m, programm, bib, sp._sicherheitszustand(m.pruefung, bib))
    return result


def _kennungen(job, schritt=0.5, simultane=None):
    """Je Stand vor `job` ein Schlüssel: [das Rohteil, nach dem Grundjob, nach der ersten Ebene,
    …] – Rohteil, Richtungen, Werkzeugkörper und vollständige aktive Vorgängerpfade, jeder Schlüssel
    über alles bis dahin. So fängt die nächste Ebene beim Stand der vorigen an (fuer_ebene)."""
    from . import maschinenzugang as mz
    from . import materialstand as ms
    from . import schwenken as sw

    if simultane is None:
        simultane = _simultane_vorbereiten(job)
    summe = hashlib.sha256(repr([job.Grundjob.Stock.Shape.exportBrepToString(), schritt]).encode())
    ergebnis = [summe.hexdigest()]
    for davor in _jobs_vor(job):
        lage = sw.lage_im_grundjob(davor)
        daten = [tuple(lage.toMatrix().A) if lage is not None else None]
        for op in ms.operationen_vor(davor):
            tc = op.ToolController
            daten.append(
                (
                    op.Name,
                    ms._kennung_op(op),
                    str(getattr(tc.Tool, "CuttingEdgeHeight", "")),
                    tuple(tuple(a) for a in getattr(op, "Werkzeugachsen", ())),
                    bool(getattr(op, "Anstellen", False)),
                    bool(getattr(op, "Wegkippen", False)),
                    mz.operation_erreichbar(davor, op),
                )
            )
            vorbereitet = simultane.get((davor.Name, op.Name))
            if vorbereitet is not None and vorbereitet is not False:
                m, programm, _bib, sicherheit = vorbereitet
                daten.append(
                    (
                        tuple(c.toGCode() for c in programm.befehle),
                        programm.materialdaten,
                        tuple(m.nullpunkt),
                        repr(m.laenge),
                        sicherheit,
                    )
                )
        summe.update(repr(daten).encode())
        ergebnis.append(summe.hexdigest())
    return ergebnis


def kennung(job, schritt=0.5, simultane=None):
    """Rohteil, Richtungen, Werkzeugkörper und vollständige aktive Vorgängerpfade."""
    from . import materialstand as ms

    if simultane is not None:
        return _kennungen(job, schritt, simultane)[-1]
    return ms.im_durchgang(
        "raum", (ms.objekt_schluessel(job), schritt), lambda: _kennungen(job, schritt)[-1]
    )


# So viele Stände merkt sich fuer_ebene (auch die Zwischenstände nach jeder Ebene und das Rohteil).
GEMERKT_HOECHSTENS = 6


def _merken(schluessel, material):
    _GEMERKT[schluessel] = material
    _GEMERKT.move_to_end(schluessel)
    while len(_GEMERKT) > GEMERKT_HOECHSTENS:
        _GEMERKT.popitem(last=False)


def fuer_ebene(job, schritt=0.5, fortschritt=None):
    """Gemeinsamer Rest vor einer 3+2-Ebene; None bei nicht sicher nachlesbarer Bearbeitung.

    Die Ausgabe ist nur zum Lesen. Ein unbekannter Schnitt darf niemals freie Räume
    vortäuschen. Daher bleiben solche Ebenen beim vollständigen ursprünglichen Rohteil.
    """
    from . import maschinenzugang as mz
    from . import materialstand as ms
    from . import reichweite as rw
    from . import schwenken as sw
    from . import simultan_operation as so
    from . import vierachs_schlichten as vs

    simultane = _simultane_vorbereiten(job)
    kennungen = _kennungen(job, schritt, simultane)
    key = kennungen[-1]
    if key in _GEMERKT:
        _GEMERKT.move_to_end(key)
        return _GEMERKT[key]
    # Beim letzten gemerkten Stand weiter (dem Rohteil oder nach einer Ebene davor): Jede Ebene
    # fuhr sonst alle Ebenen vor ihr noch einmal ab, und das Rohteil schnitt jede neu.
    jobs = _jobs_vor(job)
    beginn = next((n for n in range(len(jobs) - 1, -1, -1) if kennungen[n] in _GEMERKT), None)
    if beginn is None:
        beginn = 0
        material = Material(job.Grundjob.Stock.Shape, schritt, fortschritt)
        _merken(kennungen[0], material.kopie())
    else:
        _GEMERKT.move_to_end(kennungen[beginn])
        material = _GEMERKT[kennungen[beginn]].kopie()
    stapel = _Stapel(material)
    for nummer, davor in enumerate(jobs[beginn:], beginn):
        if nummer > beginn:
            stapel.leeren()
            _merken(kennungen[nummer], material.kopie())
        lage = sw.lage_im_grundjob(davor)
        achse = np.array(tuple(lage.Rotation.multVec(Vector(0, 0, 1)))) if lage else (0, 0, 1)

        def ort(p, lage=lage):
            return np.array(tuple(lage.multVec(Vector(*p)))) if lage else np.asarray(p)

        for op in ms.operationen_vor(davor):
            if mz.operation_erreichbar(davor, op) is False:
                material.ausgelassen += ((op.Label, davor.Label),)
                continue  # Nicht gefahrener Schnitt darf keinen freien Raum vortäuschen.
            if so.ist_simultan(op):
                stapel.leeren()
                vorbereitet = simultane.get((davor.Name, op.Name))
                if vorbereitet is None:
                    return None  # Ohne tatsächliche Kinematik kein räumlich gedachter Schnitt.
                if vorbereitet is False:
                    material.ausgelassen += ((op.Label, davor.Label),)
                    continue
                m, programm, bib, _sicherheit = vorbereitet
                from . import abfahren as ab
                from . import raum_bahn as rb
                from .simultan_bereiche import _Ansicht

                # Ausschließlich diese tatsächliche NC: keine anderen Ebenen oder
                # noch einmal die ungekippte Quellbahn in die Materialfolge einführen.
                view = _Ansicht(
                    op,
                    _pruefprogramm=(so.pruefschluessel(m), programm.befehle),
                    _pruefmaterial=programm.materialdaten,
                )
                j = _Ansicht(davor, Operations=_Ansicht(davor.Operations, Group=[view]))
                fahrt = ab.abfahrt(m.pruefung, j, m.nullpunkt, bib)
                tc = op.ToolController
                form = vs.form_des_controllers(tc)
                laenge = float(getattr(tc.Tool, "CuttingEdgeHeight", 0))
                if form is None or not fahrt.stationen:
                    return None
                try:
                    if not rb.abtragen(
                        material, fahrt, programm.materialdaten, form, laenge, fortschritt
                    ):
                        return None
                except ValueError as fehler:
                    if str(fehler) == tr("s5p.fehler.unvollstaendig"):
                        raise
                    return None  # Unbekannte Geometrie/Budget: keinen halben Rest veröffentlichen.
                material.ausgelassen += tuple(
                    (f"{op.Label} – {n}: {grund}", davor.Label) for n, grund in programm.ausgelassen
                )
                continue
            tc = op.ToolController
            form = vs.form_des_controllers(tc)
            laenge = float(getattr(tc.Tool, "CuttingEdgeHeight", 0))
            if (
                form is None
                or not math.isfinite(laenge)
                or laenge <= (form.radius if form.nur_kugel else 0)
            ):
                return None
            innen, aussen = koerperteile(form, laenge, material.schritt)
            unbekannt = []
            letzter = None
            for s in rw._bahn(op.Path.Commands, unbekannt.append, rueckzug=True):
                if any(abs(v) > 1e-8 for v in s.rund.values()):
                    return None
                radius = form.radius
                if s.art == "bogen":
                    bogen = s.ort
                    anzahl = max(2, int(math.ceil(abs(bogen.winkel) * bogen.radius / 0.5)))
                    punkte = [bogen.bei(k / anzahl) for k in range(1, anzahl + 1)]
                    # Die kleinere Scheibe ist sicher in der tatsächlichen Bogenfahrt.
                    radius -= bogen.radius * (1 - math.cos(abs(bogen.winkel) / (2 * anzahl)))
                else:
                    punkte = [s.ort]
                for p in punkte:
                    jetzt = ort(p)
                    if letzter is not None:
                        if fortschritt is not None and not fortschritt(0.5):
                            raise ValueError(tr("s5p.fehler.unvollstaendig"))
                        u = np.asarray(achse)
                        # Im Vorschub gesammelt (_Stapel); ein Eilgang am Material, wie es
                        # dann steht – schneidet er, ist der Rest nicht sicher.
                        if s.eilgang:
                            stapel.leeren()
                        ziel = material if s.eilgang else stapel
                        teile = aussen if s.eilgang else innen
                        volumen = teile_abtragen(
                            ziel, letzter, jetzt, u, teile, radius - form.radius
                        )
                        if s.eilgang and volumen > 1e-7:
                            return None
                    letzter = jetzt
            if unbekannt:
                return None
    stapel.leeren()
    _merken(key, material)
    return material
