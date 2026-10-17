# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Stange als Voxel – eine Nachrechnung der Rundum-Bahnen, unabhängig vom Restmodell des
Addons (dort ein Radius je Strahl): Jeder Satz fährt der Reihe nach, je Stellung höchstens einen
halben Voxel weiter, und nimmt weg, was sein Fräser trifft (ein Voxel zählt, wenn seine Mitte im
Fräser liegt). Der Fräser: ein Schaftfräser (flach) oder eine Kugel mit Schaft, seine Achse quer
zur Stange unter dem Winkel ψ (Punkt.phi), die Spitze bei x (Punkt.r), quer um Punkt.q versetzt
– wie vierachs_bahn._QuerAbstand. So fand sich in der Nacht vom 10. auf den 11.10.
(P-2026-10-11-27), dass freie Läufe des Schlichtens an Manuels Nasen-Testteil Material schnitten.

Auf allen Kernen (P-2026-10-11-42; Manuel: „warum rechnet da nur ein kern ??“ – bis dahin lag es
unter tests/ und rechnete in einem Prozess, an 0,5 mm Voxeln eine Viertelstunde): fahre() teilt
die Sätze nach ihrer Arbeit (den Stellungen in der Stange) in Stücke für die Nebenrechner; jedes
Stück rechnet auf seiner Kopie der Stange (gemeinsam, einmal je Arbeiter). Wegnehmen hängt nicht
davon ab, was vorher weg war – die Stange danach ist darum dieselbe wie der Reihe nach: was in
keinem Stück weggenommen wurde. Die Zahl je Satz dagegen schon: Dafür rechnet jedes Stück noch
einmal mit der Stange, wie die Stücke vor ihm sie ließen (`je_satz`), ebenfalls verteilt. Ohne
Nebenrechner rechnet fahre() selbst. Nur numpy – im Arbeiter ohne Dokument.
"""

import hashlib
import math

import numpy as np

from . import formteile as ft

TEIL_TOLERANZ = 0.01  # mm: so fein wird das Teil für teil() vernetzt
_SCHIEF = (1.234567e-5, 2.345678e-5)  # mm: so weit liegen die Strahlen neben den Spaltenmitten
JE_MM_STRECKE = 5.0  # mm Weg: darüber mittelt je_mm()
STUECKE_JE_ARBEITER = 3  # wer früher fertig ist, nimmt das nächste
VERTEILT_AB = 2000  # Stellungen: darunter rechnet fahre() selbst


def als_feld(punkte):
    """Die Sätze als (n, 4): a, r, q, phi (Grad) – Punkte (Attribute) oder schon ein Feld."""
    if isinstance(punkte, np.ndarray):
        return np.asarray(punkte, dtype=float)
    return np.array([(p.a, p.r, p.q, p.phi) for p in punkte], dtype=float).reshape(-1, 4)


def fraeser(form):
    """(Radius, Kugel) für fahre(), so dass der Fräser des Voxelmodells ganz im echten liegt – es
    nimmt eher weniger weg, ein Rest hält nach oben: der Schaft- und Torusfräser als Scheibe mit
    dem Radius ihrer ebenen Stirn, Kugel und Konik als Kugel an der Spitze. None für eine
    Spitze ohne beides (Kegel)."""
    erstes = form.stuecke[0]
    if erstes.art == "eben" and erstes.rho_bis > 0:
        return float(erstes.rho_bis), False
    if form.kugel > 0:
        return float(form.kugel), True
    return None


def je_mm(saetze, weg, h, eilgang=None, strecke=JE_MM_STRECKE):
    """(mm³ je mm Weg, a) je Satz – was der Fräser nimmt (`weg`: Voxel je Satz aus fahre()),
    gemittelt über die letzten `strecke` mm Weg im Vorschub (ein Voxel allein wäre Rauschen).
    Der Weg: längs, radial, quer und am Umfang (r · Δφ). Eilgänge zählen nicht."""
    saetze = als_feld(saetze)
    if len(saetze) < 2:
        return np.zeros(0), np.zeros(0)
    d = np.diff(saetze, axis=0)
    r_mitte = np.abs(saetze[1:, 1] + saetze[:-1, 1]) / 2
    laenge = np.sqrt(
        d[:, 0] ** 2 + d[:, 1] ** 2 + d[:, 2] ** 2 + (r_mitte * np.radians(d[:, 3])) ** 2
    )
    volumen = np.asarray(weg[1:], dtype=float) * h**3
    if eilgang is not None:
        im_vorschub = ~np.asarray(eilgang[1:], dtype=bool)
        laenge, volumen = np.where(im_vorschub, laenge, 0.0), np.where(im_vorschub, volumen, 0.0)
    s = np.concatenate([[0.0], np.cumsum(laenge)])
    v = np.concatenate([[0.0], np.cumsum(volumen)])
    von = np.searchsorted(s, s[1:] - strecke, "right") - 1
    von = np.clip(von, 0, None)
    lang = s[1:] - s[von]
    return np.where(lang > 0, (v[1:] - v[von]) / np.maximum(lang, 1e-9), 0.0), saetze[1:, 0]


def _rahmen(laengs, radial):
    """(L, U, V) wie vierachs_huelle.rahmen – hier ohne FreeCAD."""
    l_ = np.array([float(c) for c in laengs], dtype=float)
    u = np.array([float(c) for c in radial], dtype=float)
    l_ /= np.linalg.norm(l_)
    u -= l_ * float(u @ l_)
    u /= np.linalg.norm(u)
    return l_, u, np.cross(l_, u)


def _packen(maske):
    return np.packbits(maske.ravel())


def _auspacken(gepackt, form):
    return np.unpackbits(gepackt, count=int(np.prod(form))).reshape(form).astype(bool)


def stueck(stange, saetze, r_fraeser, kugel, weg_vorher=None):
    """Auch im Nebenrechner: die Sätze `saetze` ((n, 4), der erste nur als Anfang) auf der Stange
    `stange` (Voxelstange.daten()) ohne `weg_vorher` (gepackt, oder None) – (Voxel je Satz ab dem
    zweiten, gepackt was sie wegnehmen)."""
    v = Voxelstange.aus_daten(stange)
    if weg_vorher is not None:
        v.material &= ~_auspacken(weg_vorher, v.material.shape)
    vorher = v.material.copy()
    zahlen = v._fahre_selbst(saetze, r_fraeser, kugel)
    return zahlen[1:], _packen(vorher & ~v.material)


class Voxelstange:
    def __init__(self, radius, a_von, a_bis, h=1.0):
        self.radius, self.a_von, self.h = float(radius), float(a_von), float(h)
        self.na = int(math.ceil((a_bis - a_von) / h))
        self.ny = int(math.ceil(2 * radius / h))
        self.ac = a_von + (np.arange(self.na) + 0.5) * h
        self.yc = -radius + (np.arange(self.ny) + 0.5) * h
        y = self.yc[:, None]
        z = self.yc[None, :]
        scheibe = (y**2 + z**2) <= radius**2
        self.material = np.broadcast_to(scheibe, (self.na, self.ny, self.ny)).copy()

    def daten(self):
        """Was ein Nebenrechner braucht, um die Stange nachzubauen (aus_daten): klein gepackt."""
        return (self.radius, self.a_von, self.h, self.na, _packen(self.material))

    @classmethod
    def aus_daten(cls, daten):
        radius, a_von, h, na, gepackt = daten
        v = cls(radius, a_von, a_von + na * h, h)
        v.material = _auspacken(gepackt, v.material.shape)
        return v

    def _stellung(self, a, x, psi, q, r_fraeser, kugel):
        """Nimmt weg, was der Fräser an dieser Stellung trifft; gibt die Zahl der Voxel zurück."""
        if x >= self.radius:
            return 0
        h, rad = self.h, self.radius
        c, s = math.cos(psi), math.sin(psi)
        ty, tz = x * c - q * s, x * s + q * c
        lang = rad + r_fraeser - x + 1.0
        ys = (
            ty + r_fraeser * s,
            ty - r_fraeser * s,
            ty + lang * c + r_fraeser * s,
            ty + lang * c - r_fraeser * s,
        )
        zs = (
            tz - r_fraeser * c,
            tz + r_fraeser * c,
            tz + lang * s - r_fraeser * c,
            tz + lang * s + r_fraeser * c,
        )
        i0 = max(0, int((a - r_fraeser - self.a_von) / h))
        i1 = min(self.na, int((a + r_fraeser - self.a_von) / h) + 1)
        j0 = max(0, int((min(ys) + rad) / h))
        j1 = min(self.ny, int((max(ys) + rad) / h) + 1)
        k0 = max(0, int((min(zs) + rad) / h))
        k1 = min(self.ny, int((max(zs) + rad) / h) + 1)
        if i0 >= i1 or j0 >= j1 or k0 >= k1:
            return 0
        teil = self.material[i0:i1, j0:j1, k0:k1]
        if not teil.any():
            return 0
        w = self.ac[i0:i1][:, None, None] - a
        dy = self.yc[j0:j1][None, :, None] - ty
        dz = self.yc[k0:k1][None, None, :] - tz
        t = dy * c + dz * s  # längs der Werkzeugachse, nach außen
        quer = -dy * s + dz * c
        rr = r_fraeser * r_fraeser
        if kugel:
            tm = t - r_fraeser
            drin = ((tm**2 + quer**2 + w**2) <= rr) | (
                (tm >= 0) & (tm <= lang) & (quer**2 + w**2 <= rr)
            )
        else:
            drin = (t >= 0) & (t <= lang) & (quer**2 + w**2 <= rr)
        treffer = drin & teil
        n = int(treffer.sum())
        if n:
            teil[treffer] = False
        return n

    def teil(self, form, laengs, radial, toleranz=TEIL_TOLERANZ):
        """Die Voxel (wie material), deren Mitte in `form` liegt (ein Solid in Job-Koordinaten,
        die Stangenachse `laengs` durch den Nullpunkt, φ = 0 bei `radial`): a = p·L, quer
        y = p·U, z = p·V (vierachs_huelle.rahmen). Gefüllt über das Netz der Form – je Spalte
        (y, z) ein Strahl längs: wo er durch die Dreiecke tritt, wechselt drinnen und draußen.
        In numpy über alle Dreiecke zugleich, Sekunden statt eines isInside je Voxel."""
        # Eine Kopie vernetzen: tessellate am Original hängt das Netz an die Form, und wer sie
        # danach gröber vernetzt, bekäme dieses feine (P-2026-10-18-68).
        punkte, dreiecke = ft.vernetzt(form, toleranz)
        maske = np.zeros(self.material.shape, dtype=bool)
        if not dreiecke:
            return maske
        l_, u_, v_ = _rahmen(laengs, radial)
        p = np.array([[q.x, q.y, q.z] for q in punkte], dtype=float)
        ecken = np.column_stack([p @ l_, p @ u_, p @ v_])[np.array(dreiecke, dtype=np.int64)]
        return self._fuellen(ecken)

    def _fuellen(self, ecken):
        """Die Maske zu den Dreiecken `ecken` ((m, 3, 3) – je Ecke a, y, z)."""
        h, rad = self.h, self.radius
        maske = np.zeros(self.material.shape, dtype=bool)
        # Die Spalten leicht versetzt, damit kein Strahl genau eine Kante oder Ecke trifft.
        y, z = ecken[:, :, 1] - _SCHIEF[0], ecken[:, :, 2] - _SCHIEF[1]
        j0 = np.ceil((y.min(axis=1) + rad) / h - 0.5).astype(np.int64).clip(0, self.ny)
        j1 = np.floor((y.max(axis=1) + rad) / h - 0.5).astype(np.int64).clip(-1, self.ny - 1)
        k0 = np.ceil((z.min(axis=1) + rad) / h - 0.5).astype(np.int64).clip(0, self.ny)
        k1 = np.floor((z.max(axis=1) + rad) / h - 0.5).astype(np.int64).clip(-1, self.ny - 1)
        nj, nk = np.maximum(j1 - j0 + 1, 0), np.maximum(k1 - k0 + 1, 0)
        anzahl = nj * nk
        if not anzahl.sum():
            return maske
        t = np.repeat(np.arange(len(ecken)), anzahl)
        versatz = np.arange(int(anzahl.sum())) - np.repeat(np.cumsum(anzahl) - anzahl, anzahl)
        j = j0[t] + versatz // nk[t]
        k = k0[t] + versatz % nk[t]
        py, pz = self.yc[j], self.yc[k]
        # Baryzentrisch in der Ebene (y, z): liegt die Spalte im Dreieck, und wo trifft sie es?
        y0, y1, y2 = y[t, 0], y[t, 1], y[t, 2]
        z0, z1, z2 = z[t, 0], z[t, 1], z[t, 2]
        det = (y1 - y0) * (z2 - z0) - (y2 - y0) * (z1 - z0)
        gut = np.abs(det) > 1e-12
        det = np.where(gut, det, 1.0)
        b1 = ((py - y0) * (z2 - z0) - (y2 - y0) * (pz - z0)) / det
        b2 = ((y1 - y0) * (pz - z0) - (py - y0) * (z1 - z0)) / det
        drin = gut & (b1 >= 0) & (b2 >= 0) & (b1 + b2 <= 1)
        a = (
            ecken[t, 0, 0]
            + b1 * (ecken[t, 1, 0] - ecken[t, 0, 0])
            + b2 * (ecken[t, 2, 0] - ecken[t, 0, 0])
        )
        j, k, a = j[drin], k[drin], a[drin]
        # Je Spalte die Durchtritte der Reihe nach: zwischen dem 1. und 2., 3. und 4. … drinnen.
        folge = np.lexsort((a, k, j))
        j, k, a = j[folge], k[folge], a[folge]
        spalte = j * self.ny + k
        neu = np.ones(len(spalte), dtype=bool)
        neu[1:] = spalte[1:] != spalte[:-1]
        rang = np.arange(len(spalte)) - np.maximum.accumulate(
            np.where(neu, np.arange(len(spalte)), 0)
        )
        rein, raus = (rang % 2) == 0, (rang % 2) == 1
        # paarweise: jeder Eintritt mit dem Austritt gleich danach (eine offene Spalte zählt nicht)
        paar = rein[:-1] & raus[1:] & (spalte[:-1] == spalte[1:])
        von = np.ceil((a[:-1][paar] - self.a_von) / h - 0.5).astype(np.int64).clip(0, self.na)
        bis = np.floor((a[1:][paar] - self.a_von) / h - 0.5).astype(np.int64).clip(-1, self.na - 1)
        jj, kk = j[:-1][paar], k[:-1][paar]
        stufen = np.zeros((self.na + 1, self.ny, self.ny), dtype=np.int32)
        ok = bis >= von
        np.add.at(stufen, (von[ok], jj[ok], kk[ok]), 1)
        np.add.at(stufen, (bis[ok] + 1, jj[ok], kk[ok]), -1)
        maske[:] = np.cumsum(stufen, axis=0)[:-1] > 0
        return maske

    def _schritte(self, p, n_):
        """So viele Stellungen fährt der Weg von `p` nach `n_` ((a, r, q, phi), je höchstens ein
        halber Voxel)."""
        da, dx, dq = n_[0] - p[0], n_[1] - p[1], n_[2] - p[2]
        dpsi = math.radians(n_[3] - p[3])
        strecke = max(abs(da), abs(dx), abs(dq), abs(dpsi) * (max(abs(p[1]), abs(n_[1])) + 10))
        return max(1, int(math.ceil(strecke / (self.h * 0.5))))

    def fahre(self, punkte, r_fraeser, kugel, je_satz=True, verteilt=True):
        """Je Punkt (ab dem zweiten): so viele Voxel nimmt der Weg dorthin weg (Eilgänge auch) –
        `verteilt` auf den Nebenrechnern. Ohne `je_satz` verteilt nur einmal: Die Stange danach
        stimmt, die Zahlen je Satz zählen dann auch, was ein Stück davor schon wegnahm."""
        saetze = als_feld(punkte)
        if verteilt and len(saetze) > 2:
            weg = self._fahre_verteilt(saetze, r_fraeser, kugel, je_satz)
            if weg is not None:
                return weg
        return self._fahre_selbst(saetze, r_fraeser, kugel)

    def _fahre_verteilt(self, saetze, r_fraeser, kugel, je_satz):
        """fahre() auf den Nebenrechnern – None ohne sie, bei wenig Arbeit oder wenn sie
        scheitern."""
        try:
            from . import nebenrechner as nr
        except ImportError:  # ohne FreeCAD
            return None
        innen = np.minimum(saetze[:-1, 1], saetze[1:, 1]) < self.radius
        arbeit = np.ones(len(saetze), dtype=np.int64)
        arbeit[0] = 0
        for i in np.flatnonzero(innen):
            arbeit[i + 1] = self._schritte(saetze[i], saetze[i + 1])
        if int(arbeit.sum()) < VERTEILT_AB:
            return None
        try:
            pool = nr.pool()
            if not pool.verfuegbar() or pool.anzahl < 2:
                return None
            # Stücke gleicher Arbeit: Sätze von bis (der Satz von − 1 ist ihr Anfang)
            anzahl = min(len(saetze) - 1, pool.anzahl * STUECKE_JE_ARBEITER)
            summe = np.cumsum(arbeit)
            ziele = np.linspace(0, summe[-1], anzahl + 1)[1:-1]
            grenzen = {1, len(saetze)}
            grenzen.update(int(g) for g in np.searchsorted(summe, ziele, "right"))
            grenzen = sorted(g for g in grenzen if 1 <= g <= len(saetze))
            stuecke = list(zip(grenzen, grenzen[1:], strict=False))
            daten = self.daten()
            schluessel = "vx-" + hashlib.sha1(daten[-1].tobytes()).hexdigest()
            stange = pool.gemeinsam(schluessel, daten)

            def rechnen(vorher):
                auftraege = [
                    pool.auftrag(
                        "voxelstange",
                        "stueck",
                        stange,
                        saetze[von - 1 : bis],
                        r_fraeser,
                        kugel,
                        vorher[k],
                    )
                    for k, (von, bis) in enumerate(stuecke)
                ]
                return pool.warten(auftraege, zwischendurch=nr.ereignisse_ohne_eingaben)

            erste = rechnen([None] * len(stuecke))
            # Was die Stücke vor einem wegnahmen – für die Zahlen je Satz die Stange davor.
            form = self.material.shape
            alles, vorher = np.zeros(form, dtype=bool), []
            for _z, genommen in erste:
                vorher.append(_packen(alles) if alles.any() else None)
                alles |= _auspacken(genommen, form)
            ergebnisse = rechnen(vorher) if je_satz else erste
            pool.vergessen(schluessel)
        except nr.Fehler:
            return None
        weg = np.zeros(len(saetze), dtype=np.int64)
        for (von, bis), (zahlen, _g) in zip(stuecke, ergebnisse, strict=True):
            weg[von:bis] = zahlen
        self.material &= ~alles
        return weg

    def _fahre_selbst(self, punkte, r_fraeser, kugel):
        """Wie fahre(), der Reihe nach in diesem Prozess."""
        saetze = als_feld(punkte)
        weg = np.zeros(len(saetze), dtype=np.int64)
        for i in range(1, len(saetze)):
            p, n_ = saetze[i - 1], saetze[i]
            da, dx, dq = n_[0] - p[0], n_[1] - p[1], n_[2] - p[2]
            dpsi = math.radians(n_[3] - p[3])
            schritte = self._schritte(p, n_)
            for k in range(1, schritte + 1):
                t = k / schritte
                weg[i] += self._stellung(
                    p[0] + t * da,
                    p[1] + t * dx,
                    math.radians(p[3]) + t * dpsi,
                    p[2] + t * dq,
                    r_fraeser,
                    kugel,
                )
        return weg
