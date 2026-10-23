# SPDX-License-Identifier: LGPL-2.1-or-later
"""Flächen wählen für die 4-Achs-Bearbeitung (Spezifikation W-003, Stufe V4).

Manuel (2026-09-30): „Es wäre schön, wenn ich nur Flächen am Mantel anklicken könnte, die ich
bearbeiten will … und wenn ich alle anklicke, dann wird komplett rings um bearbeitet.“

Ein Strahl von außen zur Achse – an der Stelle a unter dem Winkel φ, wie in vierachs_huelle –
trifft das Teil zuerst auf einer Fläche: Dorthin kommt ein radiales Werkzeug. sicht() rechnet
das für ein Raster (a, φ): je Zelle die Fläche und den Radius des ersten Treffers (die
Hüllfläche eines punktförmigen Werkzeugs), dazu je Fläche, in wie vielen Zellen ein Strahl sie
zuerst trifft und in wie vielen überhaupt – beim Eintritt ins Teil oder beim Austritt. Daraus:

- mantelflaechen(): die Flächen, die nach außen schauen – ein Strahl tritt dort ins Teil ein.
  Stirnflächen und Wände quer zur Achse trifft kein Strahl, die Unterseite eines Überhangs
  nur beim Austritt.
- erreichbar(): welcher Anteil einer Fläche zuerst getroffen wird – 1 ganz, 0 gar nicht (unter
  einem Überhang), None: kein Strahl trifft sie (quer zur Achse).
- bereich(): wo die Mitte eines Fräsers mit dem Radius R stehen muss, damit er die gewählten
  Flächen ganz bearbeitet – überall, wo er eine von ihnen berührt. Die Bahn fräst nur dort
  (vierachs_bahn); gerechnet wird sie weiter gegen das ganze Teil, so bleibt es heil.

Gerechnet wird gegen das Netz des Teils, jede Fläche für sich vernetzt (vernetze()), mit der
Nummer der Fläche je Dreieck. Die Dreiecke zeigen nach außen – FreeCAD dreht die der
umgekehrten Flächen um –, so unterscheiden sich Ein- und Austritt.

Läuft ohne Oberfläche; numpy gehört zu FreeCAD.
"""

import math
import os
from dataclasses import dataclass

import numpy as np

from . import formteile as ft
from . import vierachs_huelle as vh
from .sprache import tr

# Ab diesem Anteil gilt eine Fläche als ganz erreichbar: Am Rand einer Fläche entscheidet das
# Netz, welche Nachbarin ein Strahl zuerst trifft.
GANZ = 0.97
KAUM = 0.01  # darunter als nicht erreichbar
RAND = 1.0  # mm – so weit reicht das Raster von sicht_fuer() über die Enden des Teils hinaus
# Das Raster längs liegt um eine Viertel Rasterweite versetzt: Kanten liegen oft auf runden
# Maßen, und ein Strahl genau auf einer Kante sieht beide Flächen zugleich.
VERSATZ_A = vh.SCHRITT_A / 4
_KLEIN = 1e-12
_ZWISCHEN = {}  # sicht_fuer(): die letzten Ergebnisse – der Assistent fragt oft dasselbe
_ZWISCHEN_HOECHSTENS = 4


@dataclass(frozen=True)
class FlaechenNetz:
    """Das vernetzte Teil mit der Fläche je Dreieck."""

    netz: vh.Netz
    flaeche: np.ndarray  # (m,) die Nummer der Fläche je Dreieck – 0 ist form.Faces[0]
    anzahl: int  # so viele Flächen hat die Form


VERNETZT_MERKEN = 3  # so viele Netze bleiben im Hauptprozess (je Form und Toleranz eins)
_gemerkt = {}  # (kennung, toleranz) -> FlaechenNetz, in der Reihenfolge des Vernetzens


def kennung(form):
    """Was eine Form ausmacht, ohne sie zu lesen: die Kennzahlen ihrer Körper (FreeCADs
    `hashCode` – mit der Lage; nach einem Neuberechnen oder Verschieben eine andere) und die
    Zahl ihrer Flächen. Dieselbe Kennung: dasselbe Netz."""
    teile = form.Solids or form.Shells or form.Faces or [form]
    return (tuple(sorted(t.hashCode() for t in teile)), ft.anzahl(form))


def vernetze(form, toleranz=vh.TOLERANZ):
    """Das Netz einer Form (Part.Shape), jede Fläche für sich (FlaechenNetz) – gemerkt: Der
    Simultanvergleich vernetzt dasselbe Teil je Variante und Stufe neu (am Freiformbeispiel
    13 s von 37 s je Bahn, P-2026-10-10-29), und wer zweimal vergleicht, zweimal. Die letzten
    VERNETZT_MERKEN Netze bleiben, in den Nebenrechnern keins (sie bekommen Netze als
    gemeinsame Daten)."""
    if os.environ.get("CAMADDON_ARBEITER") == "1":
        return _vernetze(form, toleranz)
    schluessel = (kennung(form), float(toleranz))
    netz = _gemerkt.get(schluessel)
    if netz is None:
        netz = _vernetze(form, toleranz)
        _gemerkt[schluessel] = netz
        while len(_gemerkt) > VERNETZT_MERKEN:
            del _gemerkt[next(iter(_gemerkt))]
    return netz


def vergessen():
    """Die gemerkten Netze loslassen (Prüfungen, Speicher)."""
    _gemerkt.clear()


def _vernetze(form, toleranz):
    """Das Netz einer Form (Part.Shape), jede Fläche für sich (FlaechenNetz).

    Vernetzt wird eine Kopie ohne Netz, zuerst ganz – so teilen Nachbarflächen die Punkte
    ihrer gemeinsamen Kante, und kein Strahl schlüpft zwischen ihnen durch – und dann Fläche
    für Fläche ausgelesen (wie vierachs_huelle.vernetze).
    """
    from . import stl_teil

    aus_stl = stl_teil.flaechennetz_fuer(form)  # ein Körper aus einem STL: seine Dreiecke
    if aus_stl is not None:
        return FlaechenNetz(vh.Netz(aus_stl[0], aus_stl[1], toleranz), aus_stl[2], ft.anzahl(form))
    kopie = form.copy()
    kopie.tessellate(toleranz)
    punkte, dreiecke, flaeche = [], [], []
    versatz = 0
    flaechen = kopie.Faces
    for nummer, stueck in enumerate(flaechen):
        p, d = stueck.tessellate(toleranz)
        if not d:
            continue
        punkte.extend((q.x, q.y, q.z) for q in p)
        dreiecke.append(np.asarray(d, dtype=np.int64).reshape(-1, 3) + versatz)
        flaeche.append(np.full(len(d), nummer, dtype=np.int64))
        versatz += len(p)
    return FlaechenNetz(
        vh.Netz(
            np.asarray(punkte, dtype=float).reshape(-1, 3),
            np.concatenate(dreiecke) if dreiecke else np.zeros((0, 3), dtype=np.int64),
            toleranz,
        ),
        np.concatenate(flaeche) if flaeche else np.zeros(0, dtype=np.int64),
        len(flaechen),
    )


@dataclass(frozen=True)
class Sicht:
    """Was ein Strahl von außen je Zelle (a[i], phi[j]) zuerst trifft (sicht())."""

    a: np.ndarray  # (n_a,) mm, aufsteigend, gleicher Abstand
    phi: np.ndarray  # (n_phi,) rad, 0 … 2π ohne 2π
    flaeche: np.ndarray  # (n_a, n_phi) die Nummer der Fläche; −1: kein Treffer
    r: np.ndarray  # (n_a, n_phi) mm – wo; vierachs_huelle.KEIN_TREFFER: kein Treffer
    zuerst: np.ndarray  # (anzahl,) so viele Zellen trifft ein Strahl zuerst auf der Fläche
    eintritt: np.ndarray  # (anzahl,) … beim Eintritt ins Teil überhaupt
    austritt: np.ndarray  # (anzahl,) … beim Austritt aus dem Teil


def sicht(fnetz, laengs, radial, a_werte, phi_werte):
    """Was ein Strahl von außen zur Achse an den Stellen `a_werte` (aufsteigend, gleicher
    Abstand) unter den Winkeln `phi_werte` (rad) trifft (Sicht) – `laengs` und `radial` wie in
    vierachs_huelle. Auch Treffer hinter der Achse zählen (P-2026-10-03-07)."""
    netz = fnetz.netz
    l_, u_, v_ = vh.rahmen(laengs, radial)
    punkte = netz.punkte
    a = punkte @ l_
    u = punkte @ u_
    v = punkte @ v_
    dreiecke = netz.dreiecke
    normale = np.cross(
        punkte[dreiecke[:, 1]] - punkte[dreiecke[:, 0]],
        punkte[dreiecke[:, 2]] - punkte[dreiecke[:, 0]],
    )
    n_u, n_v = normale @ u_, normale @ v_
    betrag = np.linalg.norm(normale, axis=1)
    a_werte = np.asarray(a_werte, dtype=float)
    phi_werte = np.asarray(phi_werte, dtype=float)
    schritt = a_werte[1] - a_werte[0] if len(a_werte) > 1 else 1.0
    anzahl = fnetz.anzahl
    flaeche = np.full((len(a_werte), len(phi_werte)), -1, dtype=np.int64)
    r = np.full((len(a_werte), len(phi_werte)), vh.KEIN_TREFFER)
    zuerst = np.zeros(anzahl, dtype=np.int64)
    eintritt = np.zeros(anzahl, dtype=np.int64)
    austritt = np.zeros(anzahl, dtype=np.int64)
    for j, phi in enumerate(phi_werte):
        c, s = math.cos(phi), math.sin(phi)
        x = u * c + v * s
        y = v * c - u * s
        treffer = _strahl(a, x, y, dreiecke, a_werte[0], schritt, len(a_werte))
        if treffer is None:
            continue
        index, dreieck, wert = treffer
        # Ein Dreieck, in dessen Ebene der Strahl liegt, streift er nur (eine Wand quer zur
        # Achse genau an ihrer Stelle): Das zählt nicht – dort trifft er die Nachbarflächen.
        zu_ihm = n_u[dreieck] * c + n_v[dreieck] * s
        echt = np.abs(zu_ihm) > 1e-9 * betrag[dreieck]
        index, dreieck, wert, zu_ihm = index[echt], dreieck[echt], wert[echt], zu_ihm[echt]
        if not len(index):
            continue
        f = fnetz.flaeche[dreieck]
        # Je Zelle der höchste Treffer: nach Zelle, darin nach Höhe sortiert – der letzte.
        ordnung = np.lexsort((wert, index))
        sortiert = index[ordnung]
        erster = ordnung[np.r_[sortiert[1:] != sortiert[:-1], True]]
        flaeche[index[erster], j] = f[erster]
        r[index[erster], j] = wert[erster]
        zuerst += np.bincount(f[erster], minlength=anzahl)
        hinein = zu_ihm > 0  # die Normale zeigt zum Strahl: er tritt ein
        for welche, zaehler in ((hinein, eintritt), (~hinein, austritt)):
            paare = np.unique(index[welche] * anzahl + f[welche])  # je Zelle und Fläche einmal
            zaehler += np.bincount(paare % anzahl, minlength=anzahl)
    return Sicht(a_werte, phi_werte, flaeche, r, zuerst, eintritt, austritt)


def _strahl(a, x, y, dreiecke, a0, schritt, anzahl):
    """Wo die Strahlen y = 0 an den Stellen a0 + k · schritt die Dreiecke treffen – auch hinter
    der Achse (x ≤ 0; P-2026-10-03-07): (Zelle k, Dreieck, x) für alle Treffer, oder None. Ein
    Dreieck schneidet die Ebene y = 0 in einer Strecke; über ihr ist x linear."""
    p, q, s = dreiecke[:, 0], dreiecke[:, 1], dreiecke[:, 2]
    y_p, y_q, y_s = y[p], y[q], y[s]
    zaehlt = np.minimum(np.minimum(y_p, y_q), y_s) <= 0.0
    zaehlt &= np.maximum(np.maximum(y_p, y_q), y_s) >= 0.0
    auswahl = np.flatnonzero(zaehlt)
    if not len(auswahl):
        return None
    ecken = (p[auswahl], q[auswahl], s[auswahl])
    a_von = np.full(len(auswahl), math.inf)
    a_bis = np.full(len(auswahl), -math.inf)
    x_von = np.zeros(len(auswahl))
    x_bis = np.zeros(len(auswahl))

    def nimm(drauf, stelle_a, stelle_x):
        nonlocal a_von, a_bis, x_von, x_bis
        kleiner = drauf & (stelle_a < a_von)
        a_von = np.where(kleiner, stelle_a, a_von)
        x_von = np.where(kleiner, stelle_x, x_von)
        groesser = drauf & (stelle_a > a_bis)
        a_bis = np.where(groesser, stelle_a, a_bis)
        x_bis = np.where(groesser, stelle_x, x_bis)

    for k in ecken:  # Ecken auf der Ebene
        nimm(y[k] == 0.0, a[k], x[k])
    for k1, k2 in ((ecken[0], ecken[1]), (ecken[1], ecken[2]), (ecken[2], ecken[0])):
        y1, y2 = y[k1], y[k2]
        kreuzt = y1 * y2 < 0.0  # die Kante geht durch die Ebene
        t = np.where(kreuzt, y1 / np.where(kreuzt, y1 - y2, 1.0), 0.0)
        nimm(kreuzt, a[k1] + t * (a[k2] - a[k1]), x[k1] + t * (x[k2] - x[k1]))
    welches, index = vh._ausbreiten(a_von, a_bis, a0, schritt, anzahl)
    if not len(index):
        return None
    breite = a_bis[welches] - a_von[welches]
    stelle = a0 + schritt * index
    with np.errstate(divide="ignore", invalid="ignore"):
        wert = np.where(
            breite > _KLEIN,
            x_von[welches] + (stelle - a_von[welches]) * (x_bis[welches] - x_von[welches]) / breite,
            np.maximum(x_von[welches], x_bis[welches]),
        )
    vorn = wert > 0.0
    return index[vorn], auswahl[welches][vorn], wert[vorn]


def mantelflaechen(sicht_):
    """Die Nummern der Flächen, die nach außen schauen – dort tritt ein Strahl ins Teil ein."""
    return tuple(int(n) for n in np.flatnonzero(sicht_.eintritt > 0))


def erreichbar(sicht_, nummer):
    """Welcher Anteil der Fläche `nummer` zuerst getroffen wird (0 … 1) – None, wenn kein
    Strahl sie trifft (quer zur Achse). Eine Fläche, die ein Strahl nur beim Austritt trifft
    (die Unterseite eines Überhangs), ist nicht erreichbar: 0."""
    rein, raus = int(sicht_.eintritt[nummer]), int(sicht_.austritt[nummer])
    if rein == 0:
        return 0.0 if raus else None
    return min(1.0, int(sicht_.zuerst[nummer]) / rein)


@dataclass(frozen=True)
class Bereich:
    """Wo die Mitte des Fräsers stehen darf, damit er fräst: drin[i, j] für a[i], phi[j]."""

    a: np.ndarray  # (n_a,) mm, aufsteigend, gleicher Abstand
    phi: np.ndarray  # (n_phi,) rad, 0 … 2π ohne 2π
    drin: np.ndarray  # (n_a, n_phi) bool

    def bei(self, a, phi):
        """drin an den Stellen `a` (mm) unter den Winkeln `phi` (rad), Punkt für Punkt – die
        nächste Zelle; außerhalb des Rasters längs nicht."""
        a = np.asarray(a, dtype=float)
        phi = np.asarray(phi, dtype=float)
        schritt_a = self.a[1] - self.a[0] if len(self.a) > 1 else 1.0
        schritt_phi = self.phi[1] - self.phi[0]
        # Die Hälfte rundet immer auf – auch nach vielen Umdrehungen (φ + n · 360°), wo das
        # Rundungsrauschen sonst mal ab-, mal aufrunden ließe.
        i = np.floor((a - self.a[0]) / schritt_a + 0.5 + 1e-6).astype(np.int64)
        j = np.floor((phi - self.phi[0]) / schritt_phi + 0.5 + 1e-6).astype(np.int64)
        j %= len(self.phi)
        gueltig = (i >= 0) & (i < len(self.a))
        return gueltig & self.drin[np.clip(i, 0, len(self.a) - 1), j]


def bereich(sicht_, gewaehlt, radius):
    """Wo die Mitte eines Fräsers mit `radius` (mm) stehen muss, damit er die Flächen
    `gewaehlt` (Nummern) ganz bearbeitet (Bereich): über ihnen und überall, wo seine Stirn –
    eine Scheibe quer zu seiner Achse – eine von ihnen berührt. Das reicht so weit über den
    Rand der Flächen hinaus, wie der Fräser breit ist; so kommt er auch an ihre Kanten."""
    gewaehlt = np.asarray(sorted(int(n) for n in gewaehlt), dtype=np.int64)
    drin = (
        np.isin(sicht_.flaeche, gewaehlt) if len(gewaehlt) else np.zeros_like(sicht_.flaeche, bool)
    )
    ergebnis = drin.copy()
    if radius > 0 and drin.any():
        ergebnis |= _geweitet(drin, sicht_, radius)
    return Bereich(sicht_.a, sicht_.phi, ergebnis)


def bereich_aus_maske(sicht_, drin, radius):
    """Der Bereich (Bereich) für einen Fräser mit `radius` über den Zellen `drin` (wie
    `sicht_.r`: Stellen × Winkel) einer Hüllfläche oder Sicht – über ihnen und überall, wo seine
    Stirn eine von ihnen berührt (_geweitet). Für die Sektoren beim Schruppen rundum
    (vierachs_bahn.schruppen, SEKTOREN_AB)."""
    drin = np.asarray(drin, dtype=bool)
    ergebnis = drin.copy()
    if radius > 0 and drin.any():
        ergebnis |= _geweitet(drin, sicht_, radius)
    return Bereich(sicht_.a, sicht_.phi, ergebnis)


def _geweitet(drin, sicht_, radius):
    """Die Zellen, deren Fräser eine Zelle aus `drin` berührt. Es genügen die Zellen am Rand
    von `drin`: Der Fräser einer Zelle weiter innen reicht nicht weiter hinaus. Eine Zelle
    (a', φ') auf dem Radius r' liegt unter dem Fräser bei (a, φ), wenn
    (a − a')² + (r' · sin(φ − φ'))² ≤ R² – je Zeile k ein Stück rundum."""
    anzahl_a, anzahl_phi = drin.shape
    innen = drin & np.roll(drin, 1, axis=1) & np.roll(drin, -1, axis=1)
    innen[1:] &= drin[:-1]
    innen[:-1] &= drin[1:]
    innen[[0, -1]] = False
    zeile, spalte = np.nonzero(drin & ~innen)
    r = np.maximum(sicht_.r[zeile, spalte], _KLEIN)  # am Rand des Teils: ein Treffer
    schritt_a = sicht_.a[1] - sicht_.a[0] if len(sicht_.a) > 1 else 1.0
    schritt_phi = sicht_.phi[1] - sicht_.phi[0]
    stufen = np.zeros((anzahl_a, anzahl_phi), dtype=np.int64)
    voll = np.zeros(anzahl_a, dtype=bool)
    weit = int(math.floor(radius / schritt_a + 1e-9))
    for k in range(-weit, weit + 1):
        ziel = zeile + k
        da = (ziel >= 0) & (ziel < anzahl_a)
        if not da.any():
            continue
        halb = math.sqrt(max(radius * radius - (k * schritt_a) ** 2, 0.0))
        winkel = np.arcsin(np.minimum(halb / r[da], 1.0))
        n = np.floor(winkel / schritt_phi + 1e-9).astype(np.int64)
        ziel, mitte = ziel[da], spalte[da]
        rundum = 2 * n + 1 >= anzahl_phi
        voll[ziel[rundum]] = True
        ziel, mitte, n = ziel[~rundum], mitte[~rundum], n[~rundum]
        anfang = (mitte - n) % anzahl_phi
        ende = (mitte + n + 1) % anzahl_phi
        np.add.at(stufen, (ziel, anfang), 1)
        np.add.at(stufen, (ziel, ende), -1)
        ueber = anfang >= ende  # geht über die Naht bei 0°
        np.add.at(stufen, (ziel[ueber], np.zeros(int(ueber.sum()), dtype=np.int64)), 1)
    return (np.cumsum(stufen, axis=1) > 0) | voll[:, None]


def nummern(namen):
    """Die Nummern der Flächen (0 …) zu ihren Namen („Face3“ → 2); andere Namen zählen nicht."""
    ergebnis = set()
    for name in namen:
        if name.startswith("Face") and name[4:].isdigit() and int(name[4:]) > 0:
            ergebnis.add(int(name[4:]) - 1)
    return tuple(sorted(ergebnis))


def namen(nummern_):
    """Die Namen der Flächen („Face3“) zu ihren Nummern (0 …)."""
    return [f"Face{n + 1}" for n in sorted(nummern_)]


def raster_a(a_von, a_bis):
    """Die Stellen längs für sicht(): wie vierachs_huelle.raster_a, um VERSATZ_A versetzt."""
    return vh.raster_a(a_von + VERSATZ_A, a_bis)


def sicht_fuer(form, laengs, radial, rand=RAND, toleranz=vh.TOLERANZ):
    """Die Sicht (Sicht) auf die Form (Part.Shape im Job) im Raster der Hüllfläche, `rand` (mm)
    über ihre Enden hinaus. Die letzten Ergebnisse bleiben gemerkt – für dieselbe Form (gleiche
    Kennung, Fläche und Lage), Achse und Raster rechnet es nicht noch einmal."""
    kasten = form.BoundBox
    schluessel = (
        form.hashCode(),
        round(form.Area, 6),
        tuple(round(w, 6) for w in (kasten.XMin, kasten.YMin, kasten.ZMin, kasten.XMax)),
        tuple(round(float(w), 9) for w in laengs),
        tuple(round(float(w), 9) for w in radial),
        rand,
        toleranz,
    )
    if schluessel not in _ZWISCHEN:
        fnetz = vernetze(form, toleranz)
        l_, _u, _v = vh.rahmen(laengs, radial)
        a_teil = fnetz.netz.punkte @ l_
        a_werte = raster_a(float(a_teil.min()) - rand, float(a_teil.max()) + rand)
        if len(_ZWISCHEN) >= _ZWISCHEN_HOECHSTENS:
            _ZWISCHEN.pop(next(iter(_ZWISCHEN)))
        _ZWISCHEN[schluessel] = sicht(fnetz, laengs, radial, a_werte, vh.raster_phi())
    return _ZWISCHEN[schluessel]


def bereich_fuer(form, laengs, radial, namen_, radius, toleranz=vh.TOLERANZ):
    """Der Bereich (Bereich) für einen Fräser mit `radius` über den Flächen `namen_` („Face3“ …)
    der Form (Part.Shape im Job) – None ohne gewählte Flächen: rundum. ValueError mit einem
    Satz, wenn es eine der Flächen nicht gibt oder keine von außen erreichbar ist."""
    gewaehlt = nummern(namen_)
    if not gewaehlt:
        return None
    anzahl = ft.anzahl(form)
    fehlt = [n for n in gewaehlt if n >= anzahl]
    if fehlt:
        raise ValueError(tr("vf.fehler.fehlt", namen=", ".join(namen(fehlt))))
    rand = max(RAND, math.ceil(radius) + RAND)  # so kommt der Fräser über die Enden hinaus
    ergebnis = bereich(sicht_fuer(form, laengs, radial, rand, toleranz), gewaehlt, radius)
    if not ergebnis.drin.any():
        stirn = stirnseitig(form, laengs, namen_)
        if stirn:
            # Manuels Ring (2026-10-12: Face28, Face6, Face17 – die Ringnuten auf der Stirn
            # „werden garnicht bearbeitet“): sagen, dass sie längs der Achse schauen, und wohin.
            raise ValueError(tr("vf.fehler.stirnseite", namen=", ".join(stirn)))
        raise ValueError(tr("vf.fehler.nicht_erreichbar"))
    return ergebnis


# So nah an 1 muss die Normale einer ebenen Fläche an der Stangenachse liegen (stirnseitig).
STIRN_GENAU = 0.999
STIRN_SPIEL = 0.05  # mm – so genau zählt nur_vor_stirn Stellen und Radien
STIRN_SCHRAEG = 0.5  # cos 60°: so weit darf ein Kegel vor der Stirn von quer abweichen (Fase 45°)


def stirnseitig(form, laengs, namen_):
    """Die Flächen unter `namen_` („Face3“ …), die längs der Stangenachse schauen – ebene
    Flächen der Stirnseite (ihre Normale längs `laengs`, nach vorn oder zum Futter): Die
    erreicht ein Fräser von außen (radial) nie; sie gehören in „Bearbeitung“ von vorn."""
    import FreeCAD

    from . import vierachs_rohteil as vr

    achse = FreeCAD.Vector(laengs)
    if achse.Length < 1e-9:
        return []
    achse.normalize()
    ergebnis = []
    for nummer, flaeche in ft.flaechen(form, nummern(namen_)):
        if not vr.ist_eben(flaeche):
            continue
        normale = vr.aussennormale(flaeche)
        if normale is not None and abs(normale.dot(achse)) >= STIRN_GENAU:
            ergebnis.append(f"Face{nummer + 1}")
    return ergebnis


def rundum_nichts(bahn, stange_radius):
    """Nimmt die Rundum-Schruppbahn `bahn` (vierachs_bahn.Bahn) nichts weg – kein Vorschubpunkt
    unter dem Radius der Stange (bis aufs Spiel), die Spirale fährt die ganze Länge in der Luft?
    Manuels Messspitzenhalter (2026-10-18): Stange Ø 33 = Teil Ø 33, vorn ein Bund 0,8 hoch und
    ein Rand 0,3 hoch – der radiale Fräser Ø 12 kommt zwischen Bund und Rand nicht hinein, die
    Hülle hält ihn überall auf dem Stangenradius („was will er da rundum schruppen ???“). Dann
    gehört der Haken aus, nicht „→ 1 Lage (Ø 33,0 mm → Ø 15,6 mm)“ hin."""
    return not any(
        not p.eilgang
        and not getattr(p, "frei", False)
        and math.hypot(p.r, getattr(p, "q", 0.0)) < stange_radius - STIRN_SPIEL
        for p in bahn.punkte
    )


def _stirnstuecke(form, l_, u_, v_):
    """[(r von, r bis, a dort, a dort)] – die Flächen des Teils, die nach vorn schauen, je als
    Stück, auf dem a linear mit dem Radius geht: eine Ebene quer zur Stange (a fest), ein Kegel um
    die Achse, der höchstens STIRN_SCHRAEG von quer abweicht (eine Fase 45° außen: Manuels
    Messspitzenhalter). Andere Flächen nach vorn (Rundungen, Senkungen neben der Achse) in kurzen
    Stücken aus ihrer Vernetzung."""
    import FreeCAD
    import Part

    from . import vierachs_rohteil as vr

    achse = FreeCAD.Vector(*l_)
    stuecke = []
    for flaeche in form.Faces:
        try:
            punkte, _dreiecke = flaeche.copy().tessellate(0.02)
        except Exception:  # noqa: BLE001 – eine Fläche ohne Netz: keine Stirn
            continue
        if not punkte:
            continue
        p = np.array([[q.x, q.y, q.z] for q in punkte], dtype=float)
        a = p @ l_
        r = np.hypot(p @ u_, p @ v_)
        if vr.ist_eben(flaeche):
            normale = vr.aussennormale(flaeche)
            if normale is not None and normale.dot(achse) >= STIRN_GENAU:
                mitte = float(a.mean())
                # Die Punkte des Netzes liegen auf dem Rand: Geht die Achse durch die Fläche (eine
                # volle Stirn), reicht sie bis r 0 – sonst hielte sie sich für einen Ring am Rand.
                r_von = float(r.min())
                if flaeche.isInside(achse * mitte, 1e-6, True):
                    r_von = 0.0
                stuecke.append((r_von, float(r.max()), mitte, mitte))
            continue
        kurve = flaeche.Surface
        if isinstance(kurve, Part.Cone):
            richtung = FreeCAD.Vector(kurve.Axis)
            spitze = FreeCAD.Vector(kurve.Apex)
            quer = spitze - achse * spitze.dot(achse)
            if abs(abs(richtung.dot(achse)) - 1.0) < 1e-6 and quer.Length < 1e-4:
                u0, u1, v0, v1 = flaeche.ParameterRange
                normale = flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
                if normale.dot(achse) >= STIRN_SCHRAEG:
                    i_von, i_bis = int(np.argmin(r)), int(np.argmax(r))
                    stuecke.append(
                        (float(r[i_von]), float(r[i_bis]), float(a[i_von]), float(a[i_bis]))
                    )
                continue
        # Sonst je Punkt der Vernetzung (höchstens 400), mit der Normalen dort.
        schritt = max(1, len(punkte) // 400)
        for k in range(0, len(punkte), schritt):
            try:
                uv = kurve.parameter(punkte[k])
                normale = flaeche.normalAt(*uv)
            except Exception:  # noqa: BLE001
                continue
            if normale.dot(achse) >= STIRN_SCHRAEG:
                stuecke.append(
                    (float(r[k]) - STIRN_SPIEL, float(r[k]) + STIRN_SPIEL, float(a[k]), float(a[k]))
                )
    return stuecke


def _vorn_bei(stuecke, r):
    """a der vordersten Fläche nach vorn beim Radius r (_stirnstuecke) – None, wenn dort keine
    liegt."""
    vorn = None
    for r_von, r_bis, a_von, a_bis in stuecke:
        if not r_von - 1e-6 <= r <= r_bis + 1e-6:
            continue
        if r_bis - r_von > 1e-9:
            t = min(max((r - r_von) / (r_bis - r_von), 0.0), 1.0)
            a = a_von + (a_bis - a_von) * t
        else:
            a = max(a_von, a_bis)
        vorn = a if vorn is None else max(vorn, a)
    return vorn


def nur_vor_stirn(form, laengs, radial, bahn, stange_radius):
    """Liegt alles, was die Rundum-Schruppbahn `bahn` (vierachs_bahn.Bahn) am Teil wegnimmt, nur
    in einer Scheibe vor der Stirn – vor der vordersten Fläche, die beim Radius des Schnitts nach
    vorn schaut (_stirnstuecke: eine Ebene quer, eine Fase)? Manuels Messspitzenhalter
    (2026-10-18): Stange Ø 33 = Teil Ø 33, vorn ein Bund 0,8 hoch, außen eine Fase bis 0,2 hinter
    den Bund; „was will er da rundum schruppen ??? … das teil hat aussen durchmesser schon den
    richtigen“. Dann ist es keine Arbeit für den radialen Fräser: Was zur Stirn offen ist, fräst
    „Bearbeitung“ von vorn. Die vorderste Fläche zählt: Hinter einer Nut im Mantel schaut deren
    Wand auch nach vorn, vor ihr liegt aber das Teil. Eine Scheibe ist es, wenn die Schnitte
    längs dünner liegen, als sie radial breit sind – ein langer Absatz hinter einer Schulter
    (10 mm lang, 6 mm tief) bleibt Rundum. Schnitte vor dem Teil (die Spirale beginnt in der
    Luft) zählen nicht. False ohne Schnitt oder mit Schnitten anderswo."""
    import FreeCAD

    from . import vierachs_huelle as vh

    l_, u_, v_ = vh.rahmen(laengs, radial)
    achse = FreeCAD.Vector(*l_)
    teil_vorne = max((FreeCAD.Vector(p.X, p.Y, p.Z).dot(achse) for p in form.Vertexes), default=0.0)
    schnitte = []
    for p in bahn.punkte:
        if p.eilgang or getattr(p, "frei", False):
            continue
        r = math.hypot(p.r, getattr(p, "q", 0.0))
        if r < stange_radius - STIRN_SPIEL and p.a <= teil_vorne + STIRN_SPIEL:
            schnitte.append((float(p.a), r))
    if not schnitte:
        return False
    stuecke = _stirnstuecke(form, l_, u_, v_)
    if not stuecke:
        return False
    gemerkt = {}
    for a, r in schnitte:
        schluessel = round(r, 3)
        if schluessel not in gemerkt:
            gemerkt[schluessel] = _vorn_bei(stuecke, r)
        vorn = gemerkt[schluessel]
        if vorn is None or a < vorn - STIRN_SPIEL:
            return False  # ein Schnitt, vor dem keine Stirnfläche liegt: der Mantel
    a_werte = [a for a, _r in schnitte]
    r_werte = [r for _a, r in schnitte]
    return (max(a_werte) - min(a_werte)) <= (max(r_werte) - min(r_werte)) + STIRN_SPIEL


def beschreibung(flaeche, laengs):
    """Was die Fläche ist, in Worten – für die Liste im Assistenten: „Zylinder Ø 20,00 mm,
    mittig“, „Zylinder Ø 20,00 mm, 15,00 mm außermittig“, „Ebene“, „Kegel“, „Freiform“. Die Stangenachse geht
    durch den Nullpunkt, längs `laengs`."""
    import FreeCAD
    import Part

    from .reichweite import weg_text

    flaeche_ = flaeche.Surface
    if isinstance(flaeche_, Part.Plane) or flaeche.findPlane() is not None:
        return tr("vf.art.ebene")
    if isinstance(flaeche_, Part.Cylinder):
        laengs = FreeCAD.Vector(laengs)
        laengs.normalize()
        mitte = flaeche_.Center
        neben = mitte - laengs * mitte.dot(laengs)
        parallel = abs(abs(flaeche_.Axis.dot(laengs)) - 1) < 1e-6
        durchmesser = weg_text(2 * flaeche_.Radius)
        if parallel and neben.Length < 1e-3:
            return tr("vf.art.zylinder_mittig", d=durchmesser)
        if parallel:
            return tr("vf.art.zylinder_aussermittig", d=durchmesser, versatz=weg_text(neben.Length))
        return tr("vf.art.zylinder_quer", d=durchmesser)
    if isinstance(flaeche_, Part.Cone):
        return tr("vf.art.kegel")
    if isinstance(flaeche_, Part.Toroid):
        return tr("vf.art.torus")
    if isinstance(flaeche_, Part.Sphere):
        return tr("vf.art.kugel")
    return tr("vf.art.freiform")
