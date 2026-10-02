# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Bahn „Kontur“ (W-006 S3, 4.1 Punkt 4): an gewählten Wänden entlang – außen um einen
Zapfen, innen in einer Tasche, oder an einer einzelnen Wand – mit tangentialem Ein- und
Ausfahren, Schruppen in Lagen mit Aufmaß und Schlichten in einem Zug.

- Wände (waende()): senkrechte Flächen des Teils mit waagerechter Unterkante – eben,
  zylindrisch oder Freiform, wenn sie überall senkrecht steht. Ihre Unterkanten verbinden sich
  zu Konturen (konturen()): geschlossen rundum oder offen (eine Wand, ein Absatz). Wo die freie
  Seite liegt, sagt die Außennormale der Wand.
- Je Kontur die Bahnen als Versatz der Unterkanten (Part.Wire.makeOffset2D: Ecken außen werden
  Bögen, innen schneiden sich die Geraden): Schruppen bei Radius + Aufmaß + k · Zeilenabstand,
  von außen her zur Wand hin, so viele, wie neben der Wand Rohteil steht (oder die Breite
  sagt); in Lagen von der Oberkante des Rohteils bis auf die Unterkante (plus „tiefer“). Dann
  das Schlichten bei Radius: in einem Zug über die ganze Höhe, höchstens die Schneidenlänge je
  Zug.
- Gleichlauf (Grundsatz 4): Bei rechtsdrehender Spindel (M3) liegt das Material rechts der
  Fahrtrichtung (wie G41) – um einen Zapfen im Uhrzeigersinn, in einer Tasche gegen ihn.
- Tangential hinein und heraus: eine Gerade (GERADE_ANTEIL · R) und ein Viertelkreis
  (EINFAHRT_ANTEIL · R) auf der freien Seite; passt das nicht (Hüllfläche, oder es käme einer
  Wand der Konturen näher als die Bahn darf – Radius plus Aufmaß), kürzer, zuletzt senkrecht. Im Material über die Rampe (vierachs_bahn._rampe) längs der Bahn, in der Luft
  senkrecht mit dem Eintauchvorschub.
- Die Hüllfläche (hoehenfeld.je_zeile im Raster – das Teil ohne die Wände und ohne die Flächen
  an ihren waagerechten Kanten, ohne_flaechen()) hält jede Bahn vor Absätzen und anderen Wänden
  an; wo kein Rohteil liegt, fährt keine Bahn (Grundsatz 5); beim Austritt aus dem Rohteil
  langsamer.

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field

import numpy as np

from . import bahn as bn
from . import hoehenfeld as hf
from . import vierachs_bahn as vb
from . import vierachs_planbahn as vp
from .sprache import tr

SCHRITT = 0.5  # mm – Raster längs der Bahn und für die Hüllfläche
VORSCHAU_SCHRITT = 1.0  # mm – für die Vorschau im Assistenten
EINFAHRT_ANTEIL = 1.0  # vom Fräserradius: der Viertelkreis hinein und heraus
GERADE_ANTEIL = 1.0  # vom Fräserradius: die Gerade vor dem Bogen
AUSTRITT_ANTEIL = 0.5  # vom Vorschub: so langsam beim Austritt aus dem Rohteil
SENKRECHT = 1e-6  # so wenig darf die Normale einer Wand von waagerecht abweichen
NAH = 1e-5  # mm – so nah ist dieselbe Stelle
HOECHSTENS_VERSAETZE = 200  # so viele Schruppbahnen je Kontur höchstens (vom Rohteil her)
WAND_SPIEL = 0.05  # mm – so viel näher an eine Wand darf das Ein- und Ausfahren (Sehnen der Kette)
REST_SPIEL = 0.02  # mm – so weit muss der kleine Fräser aus dem großen ragen, damit er dort fährt
GLEICH = vb.GLEICH


@dataclass(frozen=True)
class Konturwerte:
    """Was die Kontur braucht; Längen in mm, z nach oben im Job."""

    form: object  # fraeserform.Form des Fräsers – mit ebener Stirn
    zustellung: float  # ap: höchstens so tief je Lage beim Schruppen
    zeilenabstand: float  # ae: höchstens so weit liegen die Schruppbahnen auseinander
    aufmass: float  # bleibt beim Schruppen an der Wand stehen – fürs Schlichten
    schlichten: bool  # danach bei Radius in einem Zug
    oben: float  # z der Oberkante: das Rohteil (hier beginnen die Lagen)
    sicher: float  # z für den Eilgang über allem
    rohteil: tuple  # (x_von, x_bis, y_von, y_bis) des Rohteils von oben
    breite: float = 0.0  # so viel Material steht neben der Wand; 0: so viel, wie das Rohteil sagt
    tiefer: float = 0.0  # so viel tiefer als die Unterkante der Wand
    einfahrradius: float = None  # der Viertelkreis hinein und heraus; None: der Vorschlag
    schneidenlaenge: float = 0.0  # 0: unbekannt – das Schlichten in einem Zug
    sicherheit: float = vb.SICHERHEIT  # so weit über dem Material endet der Eilgang hinab
    eintauchwinkel: float = vb.EINTAUCHWINKEL  # Grad, für die Rampe ins Material
    austritt: float = AUSTRITT_ANTEIL
    # (Kontur, x, y) → bool je Stelle: nur dort fahren – None: überall (Restmaterial:
    # nur_wo_der_grosse_nicht_hinkam).
    nur_wo: object = None


@dataclass
class Konturbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    konturen: int  # so viele Konturen gefahren
    lagen: int  # Lagen über alle Konturen – Schruppen und Schlichten
    bahnen: int  # Bahnen über alle Konturen und Lagen (je mit Ein- und Ausfahren)
    z_min: float  # die tiefste Spitze (mm)
    laenge: float  # mm im Vorschub


@dataclass(frozen=True)
class Wand:
    """Eine gewählte Wand: eine senkrechte Fläche mit waagerechter Unterkante (waende())."""

    name: str  # „Face3“
    nummer: int  # 0 …
    flaeche: object  # Part.Face
    z_unten: float
    z_oben: float
    kanten: tuple  # die Unterkanten (Part.Edge), alle bei z_unten


@dataclass
class Kontur:
    """Eine Kette von Unterkanten (konturen()) – geschlossen oder offen."""

    draht: object  # Part.Wire der Unterkanten, bei z_unten
    z_unten: float
    z_oben: float
    geschlossen: bool
    stelle: tuple  # (x, y) auf der längsten Unterkante
    normale: tuple  # (nx, ny) dort, zur freien Seite (vom Material weg)
    waende: tuple  # die Namen der Wände


# --- Wände und Konturen -----------------------------------------------------------------------


def ist_wand(flaeche):
    """Steht die Fläche senkrecht – ihre Normale überall waagerecht?"""
    try:
        u0, u1, v0, v1 = flaeche.ParameterRange
        for i in range(3):
            for j in range(3):
                u = u0 + (u1 - u0) * (2 * i + 1) / 6
                v = v0 + (v1 - v0) * (2 * j + 1) / 6
                n = flaeche.normalAt(u, v)
                if n.Length < 0.5 or abs(n.z) > SENKRECHT * n.Length:
                    return False
    except Exception:  # OCC: entartete Fläche
        return False
    return True


def _waagerecht(kante, z):
    if any(abs(v.Point.z - z) > NAH for v in kante.Vertexes):
        return False
    mitte = kante.valueAt((kante.FirstParameter + kante.LastParameter) / 2)
    return abs(mitte.z - z) <= NAH


def waende(form, namen):
    """[Wand] – die Flächen `namen` („Face3“ …) von `form` (Part.Shape), die senkrecht stehen und
    eine waagerechte Unterkante haben; andere zählen nicht."""
    from . import vierachs_flaechen as vf

    ergebnis = []
    for nummer in vf.nummern(namen):
        if nummer >= len(form.Faces):
            continue
        flaeche = form.Faces[nummer]
        if not ist_wand(flaeche):
            continue
        bb = flaeche.BoundBox
        if bb.ZMax - bb.ZMin <= NAH:
            continue
        kanten = tuple(k for k in flaeche.Edges if _waagerecht(k, bb.ZMin))
        if not kanten:
            continue
        ergebnis.append(
            Wand(f"Face{nummer + 1}", nummer, flaeche, float(bb.ZMin), float(bb.ZMax), kanten)
        )
    return ergebnis


def ohne_flaechen(form, waende_):
    """Die Namen der Flächen, gegen die die Hüllfläche nicht rechnet: die Wände selbst und die
    Flächen an ihren waagerechten Kanten (Boden, Oberseite) – der Fräser fährt genau im Abstand
    seines Radius an der Wand entlang und berührt deren Kanten; alles andere (Absätze, nicht
    gewählte Wände) hält ihn an."""
    import Part

    nummern = {f.hashCode(): i for i, f in enumerate(form.Faces)}
    ergebnis = set()
    for wand in waende_:
        ergebnis.add(wand.name)
        for kante in wand.flaeche.Edges:
            zs = [v.Point.z for v in kante.Vertexes]
            if max(zs) - min(zs) > NAH:
                continue
            for nachbar in form.ancestorsOfType(kante, Part.Face):
                i = nummern.get(nachbar.hashCode())
                if i is not None:
                    ergebnis.add(f"Face{i + 1}")
    return sorted(ergebnis, key=lambda n: int(n[4:]))


def boeden_vor(form, namen):
    """Die Namen der ebenen Flächen nach oben an den Unterkanten der Wände `namen` – der Boden
    vor einem Absatz, in einer Tasche; None, wenn eine Wand unten irgendwo an keinen solchen
    Boden stößt (an die Unterseite des Teils, eine Bohrung): Dort räumt kein Planfräsen und
    kein Räumen, was neben ihr steht (P-2026-10-02-17)."""
    import Part

    waende_ = waende(form, namen)
    if not waende_:
        return None
    ebenen = {e.name for e in hf.ebenen_oben(form)}
    nummern = {f.hashCode(): i for i, f in enumerate(form.Faces)}
    boeden = set()
    for wand in waende_:
        for kante in wand.kanten:
            unten = set()
            for nachbar in form.ancestorsOfType(kante, Part.Face):
                i = nummern.get(nachbar.hashCode())
                if i is not None and f"Face{i + 1}" in ebenen:
                    unten.add(f"Face{i + 1}")
            if not unten:
                return None
            boeden |= unten
    return boeden


def _schluessel(kante):
    mitte = kante.valueAt((kante.FirstParameter + kante.LastParameter) / 2)
    return (round(mitte.x, 4), round(mitte.y, 4), round(mitte.z, 4), round(kante.Length, 4))


def _freie_seite(wand, kante):
    """((x, y), (nx, ny)): die Mitte der Unterkante und die Normale der Wand dort, vom Material
    weg (Face.normalAt beachtet die Orientierung im Körper, vierachs_rohteil.aussennormale)."""
    mitte = kante.valueAt((kante.FirstParameter + kante.LastParameter) / 2)
    try:
        u, v = wand.flaeche.Surface.parameter(mitte)
        n = wand.flaeche.normalAt(u, v)
    except Exception:  # OCC: keine Parameter – die Mitte der Fläche
        u0, u1, v0, v1 = wand.flaeche.ParameterRange
        n = wand.flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    laenge = math.hypot(n.x, n.y) or 1.0
    return (float(mitte.x), float(mitte.y)), (float(n.x / laenge), float(n.y / laenge))


def konturen(form, namen):
    """[Kontur] – die Unterkanten der Wände `namen` zu Ketten verbunden: Wände mit derselben
    Unterkante, soweit ihre Unterkanten zusammenhängen (Part.sortEdges); die tiefsten zuletzt.
    ValueError, wenn keine der Flächen eine Wand ist."""
    import Part

    alle = waende(form, namen)
    if not alle:
        raise ValueError(tr("ko.fehler.keine_wand"))
    gruppen = []
    for wand in sorted(alle, key=lambda w: w.z_unten):
        if gruppen and abs(gruppen[-1][0].z_unten - wand.z_unten) <= NAH:
            gruppen[-1].append(wand)
        else:
            gruppen.append([wand])
    ergebnis = []
    for gruppe in gruppen:
        kanten, wand_der_kante = [], {}
        for wand in gruppe:
            for kante in wand.kanten:
                kanten.append(kante)
                wand_der_kante[_schluessel(kante)] = wand
        for kette in Part.sortEdges(kanten):
            schluessel = [_schluessel(k) for k in kette]
            beteiligt = [wand_der_kante[s] for s in schluessel if s in wand_der_kante]
            if not beteiligt:
                continue
            laengste = max(kette, key=lambda k: k.Length)
            wand = wand_der_kante.get(_schluessel(laengste), beteiligt[0])
            stelle, normale = _freie_seite(wand, laengste)
            draht = Part.Wire(kette)
            ergebnis.append(
                Kontur(
                    draht,
                    float(gruppe[0].z_unten),
                    max(w.z_oben for w in beteiligt),
                    draht.isClosed(),
                    stelle,
                    normale,
                    tuple(sorted({w.name for w in beteiligt}, key=lambda n: int(n[4:]))),
                )
            )
    return sorted(ergebnis, key=lambda k: -k.z_unten)


# --- Segmente und Proben ----------------------------------------------------------------------


@dataclass(frozen=True)
class _Strecke:
    von: tuple
    nach: tuple

    @property
    def laenge(self):
        return math.hypot(self.nach[0] - self.von[0], self.nach[1] - self.von[1])

    @property
    def bogen(self):
        return None

    def umgekehrt(self):
        return _Strecke(self.nach, self.von)

    def bei(self, t):
        return (
            self.von[0] + (self.nach[0] - self.von[0]) * t,
            self.von[1] + (self.nach[1] - self.von[1]) * t,
        )


@dataclass(frozen=True)
class _Bogen:
    von: tuple
    nach: tuple
    mitte: tuple
    uhr: bool  # im Uhrzeigersinn (G2)

    @property
    def radius(self):
        return math.hypot(self.von[0] - self.mitte[0], self.von[1] - self.mitte[1])

    @property
    def winkel(self):
        a0 = math.atan2(self.von[1] - self.mitte[1], self.von[0] - self.mitte[0])
        a1 = math.atan2(self.nach[1] - self.mitte[1], self.nach[0] - self.mitte[0])
        grad = ((a0 - a1) if self.uhr else (a1 - a0)) % (2 * math.pi)
        if grad < 1e-12 and not _nah(self.von, self.nach):
            grad = 2 * math.pi
        return grad

    @property
    def laenge(self):
        return self.radius * self.winkel

    @property
    def bogen(self):
        return (self.mitte[0], self.mitte[1], self.uhr)

    def umgekehrt(self):
        return _Bogen(self.nach, self.von, self.mitte, not self.uhr)

    def bei(self, t):
        a0 = math.atan2(self.von[1] - self.mitte[1], self.von[0] - self.mitte[0])
        a = a0 - t * self.winkel if self.uhr else a0 + t * self.winkel
        r = self.radius
        return (self.mitte[0] + r * math.cos(a), self.mitte[1] + r * math.sin(a))


def _nah(p, q):
    return abs(p[0] - q[0]) <= NAH and abs(p[1] - q[1]) <= NAH


def _geteilt(bogen):
    """Ein Bogen über mehr als einen Halbkreis in zwei – so hat jeder Satz G2/G3 einen klaren
    Weg."""
    if bogen.winkel <= math.pi + 1e-9:
        return [bogen]
    halb = bogen.bei(0.5)
    return [
        _Bogen(bogen.von, halb, bogen.mitte, bogen.uhr),
        _Bogen(halb, bogen.nach, bogen.mitte, bogen.uhr),
    ]


def _segmente(draht, toleranz):
    """Die Kanten des Drahts in seiner Reihenfolge als Strecken und Bögen – andere Kurven als
    Linienzug (discretize). Die Richtung jeder Kante folgt aus dem Anschluss an die Nachbarn."""
    import Part

    kanten = draht.OrderedEdges
    ergebnis = []
    ende = None
    for nummer, kante in enumerate(kanten):
        ecken = [(float(v.Point.x), float(v.Point.y)) for v in kante.Vertexes]
        a, b = ecken[0], ecken[-1]
        umgekehrt = False
        if len(ecken) > 1:
            if ende is None:
                if len(kanten) > 1:
                    naechste = [(v.Point.x, v.Point.y) for v in kanten[nummer + 1].Vertexes]
                    if any(_nah(a, e) for e in naechste) and not any(_nah(b, e) for e in naechste):
                        umgekehrt = True
            elif _nah(ende, b) and not _nah(ende, a):
                umgekehrt = True
        if umgekehrt:
            a, b = b, a
        kurve = kante.Curve
        f, g = kante.FirstParameter, kante.LastParameter
        if isinstance(kurve, (Part.Line, Part.LineSegment)):
            if not _nah(a, b):
                ergebnis.append(_Strecke(a, b))
        elif isinstance(kurve, Part.Circle):
            mitte = (float(kurve.Center.x), float(kurve.Center.y))
            halb = kante.valueAt((f + g) / 2)
            halb = (float(halb.x), float(halb.y))
            if _nah(a, b):  # der ganze Kreis: zwei Hälften
                viertel = kante.valueAt(f + (g - f) / 4)
                uhr = bn.im_uhrzeigersinn(a, halb, (viertel.x, viertel.y))
                ergebnis.extend((_Bogen(a, halb, mitte, uhr), _Bogen(halb, a, mitte, uhr)))
            else:
                ergebnis.extend(_geteilt(_Bogen(a, b, mitte, bn.im_uhrzeigersinn(a, b, halb))))
        else:
            punkte = [(float(p.x), float(p.y)) for p in kante.discretize(Deflection=toleranz)]
            if umgekehrt:
                punkte.reverse()
            ergebnis.extend(
                _Strecke(p, q) for p, q in zip(punkte, punkte[1:], strict=False) if not _nah(p, q)
            )
        ende = b
    return ergebnis


@dataclass
class _Proben:
    """Die Bahn abgetastet: Stellen höchstens `schritt` auseinander, je Stelle ihr Segment."""

    x: np.ndarray
    y: np.ndarray
    segment: np.ndarray  # (N,) Nummer des Segments
    a: np.ndarray  # (N,) Weg bis zur Stelle


def _abtasten(segmente, schritt, geschlossen):
    xs, ys, nummern = [], [], []
    for nummer, s in enumerate(segmente):
        anzahl = max(1, int(math.ceil(s.laenge / schritt - 1e-9)))
        for i in range(anzahl):
            p = s.bei(i / anzahl)
            xs.append(p[0])
            ys.append(p[1])
            nummern.append(nummer)
    if not geschlossen and segmente:
        p = segmente[-1].nach
        xs.append(p[0])
        ys.append(p[1])
        nummern.append(len(segmente) - 1)
    x, y = np.array(xs, dtype=float), np.array(ys, dtype=float)
    a = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
    return _Proben(x, y, np.array(nummern, dtype=int), a)


def _einzelne_strecke(draht):
    import Part

    if len(draht.Edges) != 1:
        return None
    kante = draht.Edges[0]
    if not isinstance(kante.Curve, (Part.Line, Part.LineSegment)) or len(kante.Vertexes) < 2:
        return None
    a, b = kante.Vertexes[0].Point, kante.Vertexes[-1].Point
    return _Strecke((float(a.x), float(a.y)), (float(b.x), float(b.y)))


def _parallel(strecke, d):
    tx, ty = strecke.nach[0] - strecke.von[0], strecke.nach[1] - strecke.von[1]
    laenge = math.hypot(tx, ty) or 1.0
    nx, ny = -ty / laenge * d, tx / laenge * d
    return _Strecke(
        (strecke.von[0] + nx, strecke.von[1] + ny), (strecke.nach[0] + nx, strecke.nach[1] + ny)
    )


def _versatz(kontur, d, toleranz, schritt):
    """(Segmente, Proben) des Versatzes um `d` auf der freien Seite der Kontur, in Fahrtrichtung
    (Material rechts); None, wenn es ihn nicht gibt (zu groß für die Tasche)."""
    import FreeCAD

    ziel = (kontur.stelle[0] + kontur.normale[0] * d, kontur.stelle[1] + kontur.normale[1] * d)
    draht = kontur.draht.copy()
    draht.translate(FreeCAD.Vector(0, 0, -kontur.z_unten))  # makeOffset2D will z = 0
    einzeln = _einzelne_strecke(draht)  # eine Gerade allein spannt keine Ebene auf
    kandidaten = []
    for vorzeichen in (1.0, -1.0):
        if einzeln is not None:
            kandidaten.append([_parallel(einzeln, vorzeichen * d)])
            continue
        try:
            ergebnis = draht.makeOffset2D(vorzeichen * d, 0, False, not kontur.geschlossen, False)
        except Exception:  # OCC: „offset result has no wires“
            continue
        for teil in ergebnis.Wires:
            segmente = _segmente(teil, toleranz)
            if segmente:
                kandidaten.append(segmente)
    for segmente in kandidaten:
        proben = _abtasten(segmente, schritt, kontur.geschlossen)
        abstand = np.hypot(proben.x - ziel[0], proben.y - ziel[1])
        if abstand.min() <= max(schritt, 0.01 * d):
            return _in_fahrtrichtung(
                segmente, proben, int(abstand.argmin()), kontur.normale, schritt, kontur.geschlossen
            )
    return None


def _in_fahrtrichtung(segmente, proben, nahe, normale, schritt, geschlossen):
    """Gleichlauf: das Material rechts, die freie Seite (die Normale) links. Liegt sie rechts
    der Fahrtrichtung an der Stelle `nahe`, dreht sich die Bahn um."""
    n = len(proben.x)
    j = (nahe + 1) % n if geschlossen else min(nahe + 1, n - 1)
    i = nahe if j != nahe else nahe - 1
    tx, ty = proben.x[j] - proben.x[i], proben.y[j] - proben.y[i]
    if -ty * normale[0] + tx * normale[1] < 0:
        segmente = [s.umgekehrt() for s in reversed(segmente)]
        proben = _abtasten(segmente, schritt, geschlossen)
    return segmente, proben


def _startstelle(segmente, proben):
    """Die Stelle, an der eine geschlossene Bahn beginnt: die Mitte der längsten Geraden – dort
    ist Platz zum Ein- und Ausfahren."""
    strecken = [(s.laenge, i) for i, s in enumerate(segmente) if isinstance(s, _Strecke)]
    if not strecken:
        return 0
    _laenge, nummer = max(strecken)
    mitte = segmente[nummer].bei(0.5)
    stellen = np.flatnonzero(proben.segment == nummer)
    if not len(stellen):
        return 0
    abstand = np.hypot(proben.x[stellen] - mitte[0], proben.y[stellen] - mitte[1])
    return int(stellen[abstand.argmin()])


def _kette(kontur, toleranz, schritt):
    """(x, y) der Unterkanten der Kontur, höchstens `schritt` auseinander – für das Band der
    Hüllfläche."""
    import FreeCAD

    draht = kontur.draht.copy()
    draht.translate(FreeCAD.Vector(0, 0, -kontur.z_unten))
    proben = _abtasten(_segmente(draht, toleranz), schritt, kontur.geschlossen)
    return proben.x, proben.y


def _im_rohteil(x, y, rohteil, r):
    """Trifft die Stirn (Radius r) an (x, y) das Rohteil (von oben ein Rechteck)?"""
    x_von, x_bis, y_von, y_bis = rohteil
    dx = np.maximum(np.maximum(x_von - x, x - x_bis), 0.0)
    dy = np.maximum(np.maximum(y_von - y, y - y_bis), 0.0)
    return np.hypot(dx, dy) < r - GLEICH


# --- Hüllfläche im Raster ---------------------------------------------------------------------


class _Huelle:
    """Die Hüllfläche (hoehenfeld.je_zeile) im Raster über einem Rechteck – abgefragt an jeder
    Stelle der Bahn mit dem höchsten der vier Nachbarn, so bleibt die Seite der Sicherheit.

    Zwei Netze: Nahe an der Wand (im `band` um die Kette) zählt `netz_nah` – das Teil ohne die
    Wände und ohne die Flächen an ihren waagerechten Kanten, denn der Fräser fährt genau im
    Abstand seines Radius an der Wand entlang und berührt deren Kanten; weiter weg zählt
    `netz_fern` – nur ohne die Wände –, damit die Oberseite hinter einer Wand und der Boden
    vor ihr die Bahn dort anhalten, wo sie hingehören."""

    def __init__(
        self,
        netz_nah,
        netz_fern,
        geformt,
        zugabe,
        x0,
        x1,
        y0,
        y1,
        schritt,
        kette=None,
        band=0.0,
        waende=(),
    ):
        self.schritt = schritt
        self.zugabe = zugabe
        self.waende = list(waende)  # [(x, y, geschlossen, z_oben)] der Unterkanten der Konturen
        self.x0 = x0 - schritt
        self.y0 = y0 - schritt
        self.nx = max(2, int(math.ceil((x1 - self.x0) / schritt)) + 2)
        self.ny = max(2, int(math.ceil((y1 - self.y0) / schritt)) + 2)
        self.ys = self.y0 + schritt * np.arange(self.ny)
        self.roh = self._raster(netz_nah, geformt)
        if netz_fern is not None and netz_fern is not netz_nah and kette is not None:
            nah = self._nahe(kette, band)
            self.roh = np.where(nah, self.roh, self._raster(netz_fern, geformt))

    def _raster(self, netz, geformt):
        if not len(netz.dreiecke):
            return np.full((self.nx, self.ny), hf.KEIN_TREFFER)
        return hf.je_zeile(netz, geformt, self.ys, self.x0, self.schritt, self.nx, True)

    def _nahe(self, kette, band):
        """(nx, ny): liegt der Knoten höchstens `band` von der Kette (x, y der Unterkanten)?"""
        kx, ky = kette
        xs = self.x0 + self.schritt * np.arange(self.nx)
        nah = np.zeros((self.nx, self.ny), dtype=bool)
        if not len(kx):
            return nah
        dx2 = (xs[:, None] - kx[None, :]) ** 2
        for j, y in enumerate(self.ys):
            d2 = dx2 + ((y - ky) ** 2)[None, :]
            nah[:, j] = d2.min(axis=1) <= band * band
        return nah

    def roh_bei(self, x, y):
        fx = (np.asarray(x, dtype=float) - self.x0) / self.schritt
        fy = (np.asarray(y, dtype=float) - self.y0) / self.schritt
        i0 = np.clip(np.floor(fx).astype(int), 0, self.nx - 1)
        j0 = np.clip(np.floor(fy).astype(int), 0, self.ny - 1)
        i1 = np.minimum(i0 + 1, self.nx - 1)
        j1 = np.minimum(j0 + 1, self.ny - 1)
        return np.maximum(
            np.maximum(self.roh[i0, j0], self.roh[i1, j0]),
            np.maximum(self.roh[i0, j1], self.roh[i1, j1]),
        )

    def erlaubt(self, x, y, lage, ziel):
        """Darf die Spitze auf der Lage dorthin? Ja, wo die Hüllfläche nicht höher liegt – und
        wo nichts höher steht als das Ziel (die Unterkante der Wand)."""
        roh = self.roh_bei(x, y)
        return (roh + self.zugabe <= lage + GLEICH) | (roh <= ziel + GLEICH)

    def abstand_zur_wand(self, x, y, lage):
        """So weit (mm) ist jede Stelle von der nächsten Wand der Konturen entfernt, die über
        die Lage hinaufreicht – unendlich, wo keine ist. Die Hüllfläche blendet diese Wände
        nahe der Bahn aus (der Fräser fährt im Abstand seines Radius an ihnen entlang); das
        Ein- und Ausfahren muss sie trotzdem meiden."""
        ergebnis = np.full(len(x), np.inf)
        for kx, ky, geschlossen, z_oben in self.waende:
            if z_oben > lage + GLEICH and len(kx) > 1:
                ergebnis = np.minimum(ergebnis, _abstand_polylinie(x, y, kx, ky, geschlossen))
        return ergebnis


def nur_wo_der_grosse_nicht_hinkam(r_gross, r_klein, toleranz, schritt):
    """Für Konturwerte.nur_wo – das Restmaterial (W-006 4.1 Punkt 5): je Stelle der Bahn des
    kleinen Fräsers (Radius r_klein), ob sein Kreis dort aus jedem Kreis des großen herausragt
    (Radius r_gross, seine Bahn im Abstand r_gross an denselben Wänden): Abstand zu dessen Bahn
    größer als r_gross − r_klein. Dort ließ der große Material stehen – in Ecken innen, in
    Nuten, schmaler als er. Um r_klein längs der Bahn verlängert, damit der kleine sauber
    anschließt. Gibt es die Bahn des großen nicht (zu groß für die Tasche), überall."""
    bahnen = {}
    grenze = r_gross - r_klein + REST_SPIEL
    weiter = max(1, int(math.ceil(r_klein / schritt)))

    def nur_wo(k, x, y):
        if id(k) not in bahnen:
            gross = _versatz(k, r_gross, toleranz, schritt)
            bahnen[id(k)] = None if gross is None else (gross[1].x, gross[1].y)
        bahn = bahnen[id(k)]
        if bahn is None:
            return np.ones(len(x), dtype=bool)
        maske = _abstand_polylinie(x, y, bahn[0], bahn[1], k.geschlossen) > grenze
        breiter = maske.copy()
        for schieben in range(1, weiter + 1):
            if k.geschlossen:
                breiter |= np.roll(maske, schieben) | np.roll(maske, -schieben)
            else:
                breiter[schieben:] |= maske[:-schieben]
                breiter[:-schieben] |= maske[schieben:]
        return breiter

    return nur_wo


def _abstand_polylinie(qx, qy, kx, ky, geschlossen):
    """Der Abstand jedes Punkts (qx, qy) zum Linienzug (kx, ky), geschlossen oder offen."""
    ax, ay = np.asarray(kx, dtype=float), np.asarray(ky, dtype=float)
    bx, by = np.roll(ax, -1), np.roll(ay, -1)
    if not geschlossen:
        ax, ay, bx, by = ax[:-1], ay[:-1], bx[:-1], by[:-1]
    dx, dy = bx - ax, by - ay
    laenge2 = dx * dx + dy * dy
    qx = np.asarray(qx, dtype=float)[:, None]
    qy = np.asarray(qy, dtype=float)[:, None]
    t = ((qx - ax) * dx + (qy - ay) * dy) / np.where(laenge2 > 0, laenge2, 1.0)
    t = np.clip(t, 0.0, 1.0)
    return np.hypot(qx - (ax + t * dx), qy - (ay + t * dy)).min(axis=1)


# --- Die Bahn ---------------------------------------------------------------------------------


@dataclass
class _Stand:
    punkte: list = field(default_factory=list)
    konturen: int = 0
    lagen: int = 0
    bahnen: int = 0
    z_min: float = math.inf
    laenge: float = 0.0


@dataclass(frozen=True)
class _Anfahrt:
    """Ein tangentiales Ein- oder Ausfahren: die Gerade außen (`aussen` … `bogen_punkt`), der
    Viertelkreis um `mitte` zwischen `bogen_punkt` und dem Punkt auf der Bahn."""

    aussen: tuple
    bogen_punkt: tuple
    bahn_punkt: tuple
    mitte: tuple
    uhr: bool
    r_e: float
    laenge_gerade: float


def planen(netz, werte, konturen_, schritt=SCHRITT, netz_fern=None):
    """Die Bahn „Kontur“ (Konturbahn) an den Konturen `konturen_` ([Kontur]) mit den Werten
    `werte`; `netz` ist das Teil ohne die Wände und ihre Nachbarn (hoehenfeld.netz_ohne mit
    ohne_flaechen()), `netz_fern` das Teil nur ohne die Wände – es zählt weiter weg von der Wand
    (_Huelle). ValueError mit einem Satz, wenn es nicht geht."""
    w = werte
    form = w.form
    r = float(form.radius)
    if r <= 0 or vp.ebener_radius(form) <= 0:
        raise ValueError(tr("ko.fehler.form"))
    if w.zustellung <= 0 or w.zeilenabstand <= 0:
        raise ValueError(tr("ko.fehler.werte"))
    if w.zeilenabstand > 2 * r + GLEICH:
        raise ValueError(tr("ko.fehler.zeilenabstand"))
    if not konturen_:
        raise ValueError(tr("ko.fehler.keine_wand"))
    r_ein = w.einfahrradius if w.einfahrradius and w.einfahrradius > 0 else EINFAHRT_ANTEIL * r
    gerade = GERADE_ANTEIL * r
    zugabe = netz.toleranz + vb.RAND
    geformt = form.mit_aufmass(netz.toleranz)
    # Die Unterkanten aller Konturen: das Band der Hüllfläche je Kontur und der Abstand, den
    # das Ein- und Ausfahren zu jeder Wand hält.
    ketten = [(k, _kette(k, netz.toleranz, 2 * schritt)) for k in konturen_]
    waende = [(kx, ky, k.geschlossen, k.z_oben) for k, (kx, ky) in ketten]
    st = _Stand()
    for kontur, kette in ketten:
        _kontur(
            st,
            kontur,
            w,
            r,
            r_ein,
            gerade,
            netz,
            netz_fern,
            geformt,
            zugabe,
            schritt,
            kette,
            waende,
        )
    if st.konturen == 0:
        raise ValueError(tr("ko.fehler.nichts"))
    return Konturbahn(
        st.punkte,
        st.konturen,
        st.lagen,
        st.bahnen,
        st.z_min if math.isfinite(st.z_min) else 0.0,
        st.laenge,
    )


def _kontur(st, k, w, r, r_ein, gerade, netz, netz_fern, geformt, zugabe, schritt, kette, waende):
    """Eine Kontur: die Versätze fürs Schruppen (so viele, wie Rohteil neben der Wand steht),
    der fürs Schlichten, die Hüllfläche über allem, dann die Lagen."""
    ziel = k.z_unten - max(w.tiefer, 0.0)
    oben = w.oben
    if w.breite > 0:
        # Mit der Breite sagt man: Daneben ist schon geräumt (eine Tasche, das Räumen davor) –
        # dann auch über der Oberkante der Wände; die Lagen beginnen dort, nicht am Rohteil
        # (sonst fährt jede Bahn ihre Rampe durch Luft – auf der Platte 20 mm, P-2026-10-01-26).
        oben = min(oben, k.z_oben)
    if oben <= ziel + GLEICH:
        return
    aufmass = max(w.aufmass, 0.0)
    toleranz = netz.toleranz
    if w.breite > 0:
        # Zu schruppen ist nur, was über das Aufmaß hinaus steht: bei Breite = Aufmaß nichts –
        # dann bleibt allein das Schlichten.
        dick = w.breite - aufmass
        if dick > GLEICH:
            anzahl = max(1, int(math.ceil(dick / w.zeilenabstand - 1e-9)))
            abstaende = [r + aufmass + i * dick / anzahl for i in range(anzahl)]
        else:
            abstaende = []
    else:
        abstaende = [r + aufmass + i * w.zeilenabstand for i in range(HOECHSTENS_VERSAETZE)]
    schrupp = []  # [(d, Segmente, Proben)] von der Wand nach außen
    for d in abstaende:
        versatz = _versatz(k, d, toleranz, schritt)
        if versatz is None:
            break
        segmente, proben = versatz
        if not _im_rohteil(proben.x, proben.y, w.rohteil, r).any():
            break
        schrupp.append((d, segmente, proben))
    schlicht = None
    if w.schlichten:
        versatz = _versatz(k, r, toleranz, schritt)
        if versatz is not None and _im_rohteil(versatz[1].x, versatz[1].y, w.rohteil, r).any():
            schlicht = (r, versatz[0], versatz[1])
    alle = schrupp + ([schlicht] if schlicht is not None else [])
    if not alle:
        return
    rand = r_ein + gerade + r + schritt
    huelle = _Huelle(
        netz,
        netz_fern,
        geformt,
        zugabe,
        min(p.x.min() for _d, _s, p in alle) - rand,
        max(p.x.max() for _d, _s, p in alle) + rand,
        min(p.y.min() for _d, _s, p in alle) - rand,
        max(p.y.max() for _d, _s, p in alle) + rand,
        schritt,
        kette,
        r + aufmass + 2 * schritt,
        waende,
    )
    st.konturen += 1
    anzahl_lagen = max(1, int(math.ceil((oben - ziel - hf.LAGEN_SPIEL) / w.zustellung)))
    lagen = oben - (oben - ziel) * np.arange(1, anzahl_lagen + 1) / anzahl_lagen
    vorige = oben
    for lage in lagen:
        lage = float(lage)
        # (von, bis): so nah und so fern von der Wand ist diese Lage schon geräumt
        geraeumt = (math.inf, 0.0)
        gefahren = False
        for d, segmente, proben in reversed(schrupp):
            if _bahnen(
                st,
                k,
                d,
                segmente,
                proben,
                lage,
                vorige,
                geraeumt,
                huelle,
                ziel,
                w,
                r,
                r_ein,
                gerade,
                schritt,
            ):
                gefahren = True
                geraeumt = (min(geraeumt[0], d - r), max(geraeumt[1], d + r))
        if gefahren:
            st.lagen += 1
            st.z_min = min(st.z_min, lage)
        vorige = lage
    if schlicht is None:
        return
    d, segmente, proben = schlicht
    hoehe = oben - ziel
    anzahl = 1
    if 0 < w.schneidenlaenge < hoehe - GLEICH:
        anzahl = max(1, int(math.ceil((hoehe - hf.LAGEN_SPIEL) / w.schneidenlaenge)))
    geraeumt = (schrupp[0][0] - r, schrupp[-1][0] + r) if schrupp else (math.inf, 0.0)
    for lage in oben - hoehe * np.arange(1, anzahl + 1) / anzahl:
        if _bahnen(
            st,
            k,
            d,
            segmente,
            proben,
            float(lage),
            oben,
            geraeumt,
            huelle,
            ziel,
            w,
            r,
            r_ein,
            gerade,
            schritt,
        ):
            st.lagen += 1
            st.z_min = min(st.z_min, float(lage))


def _bahnen(
    st, k, d, segmente, proben, lage, vorige, geraeumt, huelle, ziel, w, r, r_ein, gerade, schritt
):
    """Eine Bahn (ein Versatz) auf einer Lage: wo die Hüllfläche es erlaubt und Rohteil liegt –
    geschlossen in einem Zug ab der Mitte der längsten Geraden, sonst in Läufen. Gibt die Zahl
    der Läufe zurück."""
    x, y = proben.x, proben.y
    n = len(x)
    if n < 2:
        return 0
    erlaubt = huelle.erlaubt(x, y, lage, ziel)
    im_rohteil = _im_rohteil(x, y, w.rohteil, r)
    drin = erlaubt & im_rohteil
    if w.nur_wo is not None:
        drin = drin & np.asarray(w.nur_wo(k, x, y), dtype=bool)
    if not drin.any():
        return 0
    laeufe = []  # [(Stellen, Austritt hinten)]
    if k.geschlossen and drin.all():
        start = _startstelle(segmente, proben)
        laeufe.append((np.arange(start, start + n + 1) % n, False))
    elif k.geschlossen:
        luecke = int(np.flatnonzero(~drin)[0])
        for von, bis in vb._stuecke(np.roll(drin, -luecke)):
            naechste = (bis + 1 + luecke) % n
            laeufe.append(
                (
                    (np.arange(von, bis + 1) + luecke) % n,
                    bool(erlaubt[naechste] and not im_rohteil[naechste]),
                )
            )
    else:
        for von, bis in vb._stuecke(drin):
            hinten = bis + 1 < n and bool(erlaubt[bis + 1] and not im_rohteil[bis + 1])
            laeufe.append((np.arange(von, bis + 1), hinten))
    anzahl = 0
    for stellen, hinten in laeufe:
        if len(stellen) < 2:
            continue
        _lauf(
            st,
            d,
            segmente,
            proben,
            stellen,
            hinten,
            lage,
            vorige,
            geraeumt,
            huelle,
            ziel,
            w,
            r,
            r_ein,
            gerade,
            schritt,
        )
        anzahl += 1
    return anzahl


def _einheit(dx, dy):
    laenge = math.hypot(dx, dy)
    return (dx / laenge, dy / laenge) if laenge > 0 else (1.0, 0.0)


def _lauf(
    st,
    d,
    segmente,
    proben,
    stellen,
    hinten,
    lage,
    vorige,
    geraeumt,
    huelle,
    ziel,
    w,
    r,
    r_ein,
    gerade,
    schritt,
):
    """Ein Lauf: Eilgang über den Anfang, hinab – in der Luft senkrecht, im Material über die
    Rampe –, tangential hinein, die Bahn, tangential heraus, hinauf. `geraeumt`: (von, bis) –
    so nah und so fern von der Wand haben die Bahnen davor diese Lage schon geräumt."""
    x, y = proben.x[stellen], proben.y[stellen]
    p0 = (float(x[0]), float(y[0]))
    p1 = (float(x[-1]), float(y[-1]))
    t0 = _einheit(x[1] - x[0], y[1] - y[0])
    t1 = _einheit(x[-1] - x[-2], y[-1] - y[-2])

    # Hinein und heraus nicht näher an eine Wand als die Bahn selbst darf: beim Schruppen
    # Radius + Aufmaß, beim Schlichten der Radius (die Hüllfläche sieht diese Wände nicht).
    mindest = min(d, r + max(w.aufmass, 0.0)) - WAND_SPIEL

    def frei(qx, qy):
        return bool(huelle.erlaubt(qx, qy, lage, ziel).all()) and bool(
            (huelle.abstand_zur_wand(qx, qy, lage) >= mindest).all()
        )

    ein = _anfahrt(p0, t0, r_ein, gerade, frei, hinein=True)
    aus = _anfahrt(p1, t1, r_ein, gerade, frei, hinein=False)
    start = ein.aussen if ein is not None else p0
    reichweite = d + (ein.r_e + ein.laenge_gerade if ein is not None else 0.0)
    # Wie nah kommt die Stirn am Einfahrpunkt der Wand – gemessen, nicht geschätzt: In einer
    # kleinen runden Bohrung biegt das Einfahren zur Wand zurück, und der Eilgang hinab streifte
    # den Ring, den die Bahn erst noch nimmt (vom Prüfstand gefunden, P-2026-10-01-29).
    abstand = float(huelle.abstand_zur_wand(np.array([start[0]]), np.array([start[1]]), lage)[0])
    nah = min(abstand, reichweite) - r
    frei_von, frei_bis = geraeumt
    material = (
        vorige > lage + GLEICH
        and bool(_im_rohteil(np.array([start[0]]), np.array([start[1]]), w.rohteil, r)[0])
        and (reichweite + r > frei_bis + GLEICH or nah < frei_von - GLEICH)
        # Mit der Breite steht weiter weg von der Wand nichts mehr: Dort taucht er im Freien ein.
        and (w.breite <= 0 or nah < w.breite - GLEICH)
    )
    punkte = st.punkte
    punkte.append(bn.Punkt(True, start[0], start[1], w.sicher))
    oben_hier = vorige if material else lage
    knapp = min(w.sicher, oben_hier + w.sicherheit)
    if knapp < w.sicher - GLEICH:
        punkte.append(bn.Punkt(True, start[0], start[1], knapp))
    laenge = 0.0
    if material:
        punkte.append(bn.Punkt(False, start[0], start[1], vorige, True))  # bis ans Material
        laenge += _rampe(punkte, ein, x, y, lage, vorige, w, schritt)
    else:
        punkte.append(bn.Punkt(False, start[0], start[1], lage, True))
    if ein is not None:
        laenge += _anfahrt_punkte(punkte, ein, lage, hinein=True)
    laenge += _bahnpunkte(punkte, segmente, proben, stellen, lage, hinten, w.austritt, r)
    if aus is not None:
        laenge += _anfahrt_punkte(punkte, aus, lage, hinein=False)
    letzter = punkte[-1]
    punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
    st.laenge += laenge
    st.bahnen += 1


def _anfahrt(p, t, r_ein, gerade, frei, hinein, frei_rechts=False):
    """Das Ein- (`hinein`) oder Ausfahren am Punkt `p` der Bahn mit der Fahrtrichtung `t`: der
    Viertelkreis liegt auf der freien Seite – links (Gleichlauf, das Material rechts) oder
    rechts (`frei_rechts`: Gegenlauf) –, die Gerade davor bzw. danach quer von der Wand
    weg. Passt es nicht (`frei` sagt nein), ohne Gerade, dann halb und viertel so groß; None,
    wenn gar nichts passt – dann senkrecht."""
    rechts = (t[1], -t[0]) if frei_rechts else (-t[1], t[0])
    richtung = -1.0 if hinein else 1.0
    for r_e, lang in ((r_ein, gerade), (r_ein, 0.0), (r_ein / 2, 0.0), (r_ein / 4, 0.0)):
        if r_e <= GLEICH:
            continue
        c = (p[0] + rechts[0] * r_e, p[1] + rechts[1] * r_e)
        a = (c[0] + richtung * t[0] * r_e, c[1] + richtung * t[1] * r_e)
        b = (a[0] + rechts[0] * lang, a[1] + rechts[1] * lang)
        xs, ys = list(np.linspace(b[0], a[0], 5)), list(np.linspace(b[1], a[1], 5))
        bogen_x, bogen_y = [], []
        for s in np.linspace(0.0, 1.0, 9):
            ex, ey = _einheit(
                (1 - s) * (a[0] - c[0]) + s * (p[0] - c[0]),
                (1 - s) * (a[1] - c[1]) + s * (p[1] - c[1]),
            )
            bogen_x.append(c[0] + ex * r_e)
            bogen_y.append(c[1] + ey * r_e)
        if not frei(np.array(xs + bogen_x), np.array(ys + bogen_y)):
            continue
        durch = (bogen_x[4], bogen_y[4])
        uhr = bn.im_uhrzeigersinn(a, p, durch) if hinein else bn.im_uhrzeigersinn(p, a, durch)
        return _Anfahrt(b, a, p, c, uhr, r_e, lang)
    return None


def _anfahrt_punkte(punkte, an, lage, hinein):
    """Die Sätze des Ein- oder Ausfahrens auf der Lage; gibt die Länge zurück."""
    laenge = 0.0
    if hinein:
        folge = [(an.bogen_punkt, None), (an.bahn_punkt, (an.mitte[0], an.mitte[1], an.uhr))]
    else:
        folge = [(an.bogen_punkt, (an.mitte[0], an.mitte[1], an.uhr)), (an.aussen, None)]
    for (px, py), bogen in folge:
        punkt = bn.Punkt(False, px, py, lage, bogen=bogen)
        if bn.weg(punkte[-1], punkt) < 1e-9:
            continue
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge


def _rampe(punkte, ein, x, y, lage, vorige, w, schritt):
    """Die Rampe ins Material längs des Einfahrens und der Bahn (vierachs_bahn._rampe): hinab
    mit dem Eintauchwinkel, dann auf der Lage zurück zum Anfang. Gibt die Länge zurück."""
    xs, ys = [], []
    if ein is not None:
        for von, nach in ((ein.aussen, ein.bogen_punkt),):
            laenge = math.hypot(nach[0] - von[0], nach[1] - von[1])
            anzahl = max(1, int(math.ceil(laenge / schritt - 1e-9)))
            for i in range(anzahl):
                xs.append(von[0] + (nach[0] - von[0]) * i / anzahl)
                ys.append(von[1] + (nach[1] - von[1]) * i / anzahl)
        bogen = _Bogen(ein.bogen_punkt, ein.bahn_punkt, ein.mitte, ein.uhr)
        anzahl = max(1, int(math.ceil(bogen.laenge / schritt - 1e-9)))
        for i in range(anzahl):
            px, py = bogen.bei(i / anzahl)
            xs.append(px)
            ys.append(py)
    xs.extend(float(v) for v in x)
    ys.extend(float(v) for v in y)
    px, py = np.array(xs), np.array(ys)
    a = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(px), np.diff(py)))])
    if len(a) < 2 or a[-1] <= GLEICH:
        punkt = bn.Punkt(False, float(px[0]), float(py[0]), lage, True)
        punkte.append(punkt)
        return 0.0
    tiefe = np.full(len(a), lage)
    still = np.zeros(len(a))
    laenge = 0.0
    for stelle_a, stelle_z, _phi in vb._rampe(a, tiefe, still, 0, len(a) - 1, vorige, w):
        m = int(np.searchsorted(a, stelle_a))
        m = min(max(m, 0), len(a) - 1)
        punkt = bn.Punkt(False, float(px[m]), float(py[m]), float(stelle_z))
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge


def _bahnpunkte(punkte, segmente, proben, stellen, lage, hinten, austritt, r):
    """Die Sätze der Bahn über die Stellen: je Segmentgrenze ein Satz – Gerade oder Bogen (G2/G3)
    –, der letzte bis zum Ende des Laufs. Endet der Lauf, weil das Rohteil endet (`hinten`),
    fahren die letzten 2 R mit dem Austritts-Anteil des Vorschubs. Gibt die Länge zurück."""
    x, y, seg = proben.x, proben.y, proben.segment
    langsam_ab = None
    if hinten:
        weg = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x[stellen]), np.diff(y[stellen])))])
        langsam_ab = int(np.flatnonzero(weg[-1] - weg <= 2 * r + GLEICH)[0])
    laenge = 0.0
    for pos in range(1, len(stellen)):
        i, h = int(stellen[pos]), int(stellen[pos - 1])
        letzte = pos == len(stellen) - 1
        if seg[i] == seg[h] and not letzte and pos != langsam_ab:
            continue
        langsam = langsam_ab is not None and (pos > langsam_ab or langsam_ab == 0)
        punkt = bn.Punkt(
            False,
            float(x[i]),
            float(y[i]),
            lage,
            bogen=segmente[int(seg[h])].bogen,
            anteil=austritt if langsam else 1.0,
        )
        if bn.weg(punkte[-1], punkt) < 1e-9:
            continue
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge
