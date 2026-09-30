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
from dataclasses import dataclass

import numpy as np

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


def vernetze(form, toleranz=vh.TOLERANZ):
    """Das Netz einer Form (Part.Shape), jede Fläche für sich (FlaechenNetz).

    Vernetzt wird eine Kopie ohne Netz, zuerst ganz – so teilen Nachbarflächen die Punkte
    ihrer gemeinsamen Kante, und kein Strahl schlüpft zwischen ihnen durch – und dann Fläche
    für Fläche ausgelesen (wie vierachs_huelle.vernetze).
    """
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
    vierachs_huelle. Treffer hinter der Achse zählen nicht."""
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
    """Wo die Strahlen y = 0 an den Stellen a0 + k · schritt die Dreiecke treffen, x > 0:
    (Zelle k, Dreieck, x) für alle Treffer, oder None. Ein Dreieck schneidet die Ebene y = 0 in
    einer Strecke; über ihr ist x linear."""
    p, q, s = dreiecke[:, 0], dreiecke[:, 1], dreiecke[:, 2]
    y_p, y_q, y_s = y[p], y[q], y[s]
    zaehlt = np.minimum(np.minimum(y_p, y_q), y_s) <= 0.0
    zaehlt &= np.maximum(np.maximum(y_p, y_q), y_s) >= 0.0
    zaehlt &= np.maximum(np.maximum(x[p], x[q]), x[s]) > 0.0
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
    anzahl = len(form.Faces)
    fehlt = [n for n in gewaehlt if n >= anzahl]
    if fehlt:
        raise ValueError(tr("vf.fehler.fehlt", namen=", ".join(namen(fehlt))))
    rand = max(RAND, math.ceil(radius) + RAND)  # so kommt der Fräser über die Enden hinaus
    ergebnis = bereich(sicht_fuer(form, laengs, radial, rand, toleranz), gewaehlt, radius)
    if not ergebnis.drin.any():
        raise ValueError(tr("vf.fehler.nicht_erreichbar"))
    return ergebnis


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
