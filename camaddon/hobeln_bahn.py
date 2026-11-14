# SPDX-License-Identifier: LGPL-2.1-or-later
"""Dichtnut hobeln (Spezifikation Strategien 13.10; Manuel, 2026-11-14: „eine nut in einem deckel
die mit einem "stech" oder "scharb" werkzeug sozusagen rausgekratzt wird … da man dadurch unten am
grund auch ne dichtfläche hinbekommen würde und nicht wie beim fräse querrillen in de nut hat“ –
„form muss egal sein wenn ich in einem teil eine nut zeichne soll diese nachgefahren werden ...
(natürlich wenn man spitze ecken hat geht das nicht man braucht schon rundungen sonst klappt das
nicht)“).

Schritt 1 des Bauplans – **die Nut und ihre Mittellinie**:

- **Erkennen** (hobelnuten()): der Grund einer umlaufenden Nut – eine ebene Fläche, die nach oben
  schaut, mit genau zwei Rändern (außen und innen), überall gleich breit. Die Form ist egal:
  Kreisring, Rechteck mit Radien, der Kontur des Deckels nach.
- **Mittellinie:** der äußere Rand um die halbe Breite nach innen versetzt, als Strecken und Bögen
  in Fahrtrichtung (gegen den Uhrzeigersinn) – auf ihr läuft die Schneide, die Spindel folgt
  ihrer Richtung.
- **Maße:** Breite, Tiefe (bis zur niedrigsten Oberkante der Wände), Länge der Mittellinie, der
  kleinste Radius.
- **Was nicht geht, mit Grund** (Hobelnut.grund): eine spitze Ecke in einer Wand (die Klinge kann
  sich dort nicht drehen), wechselnde Breite.
- **Die Klinge** (klinge_pruefen()): Breite höchstens die der Nut, und ihre hintere äußere Ecke
  darf in der engsten Kurve nicht an die Außenwand stoßen – die Schneide vorn auf der
  Mittellinie, der Körper um `laenge` dahinter.

Noch nicht: Nuten mit Enden (Langloch, zum Rand offen) – dort kommt der Hub mit Abheben dazu.
Die Bahn, das Werkzeug, die Operation und das Programm folgen in den Schritten 2 bis 5.

Läuft ohne Oberfläche.
"""

import math
from collections import OrderedDict
from dataclasses import dataclass

from . import kontur_bahn as kb
from .sprache import tr

BREITE_GLEICH = 0.02  # mm – so gleich muss die Nut überall breit sein
KNICK = math.radians(6.0)  # ab diesem Winkel zwischen zwei Stücken einer Wand: eine Ecke
NETZ = 0.001  # mm – so fein werden Kurven der Wände abgetastet (Ecken von Rundungen trennen)
PROBEN = 0.5  # mm – so dicht wird die Breite an der inneren Wand gemessen
SPIEL = 0.005  # mm – so viel Luft braucht die hintere Ecke der Klinge zur Außenwand
FORMEN_GEMERKT = 8


@dataclass(frozen=True)
class Hobelnut:
    """Eine umlaufende Nut, deren Grund sich hobeln lässt (oder warum nicht: `grund`)."""

    name: str  # die Fläche des Grunds („Face12“)
    flaechen: tuple  # Grund und Wände
    breite: float
    z_boden: float
    z_oben: float  # die niedrigste Oberkante der Wände
    segmente: tuple  # die Mittellinie: kontur_bahn._Strecke / _Bogen, gegen den Uhrzeigersinn
    laenge: float  # der Mittellinie (mm)
    r_min: float  # ihr kleinster Radius; inf: nur Geraden
    geschlossen: bool = True
    grund: str = ""  # warum sie nicht geht – leer: geht

    @property
    def tiefe(self):
        return self.z_oben - self.z_boden

    def text(self):
        """„3 breit, 2 tief, 223 lang, kleinster Radius 10“ – die Zeile im Assistenten."""
        from . import einheiten

        radius = (
            ""
            if not math.isfinite(self.r_min)
            else tr("hn.radius", r=einheiten.text(self.r_min, einheiten.LAENGE))
        )
        return tr(
            "hn.text",
            breite=einheiten.text(self.breite, einheiten.LAENGE),
            tiefe=einheiten.text(self.tiefe, einheiten.LAENGE),
            laenge=einheiten.text(self.laenge, einheiten.LAENGE, 0),
            radius=radius,
        )


# --- Erkennen ---------------------------------------------------------------------------------------

_NUTEN = OrderedDict()  # hashCode → (Form, [Hobelnut])


def alle_hobelnuten(form):
    """[Hobelnut] – alle umlaufenden Nuten der Form, auch die nicht hobelbaren (Hobelnut.grund)."""
    kennung = form.hashCode()
    eintrag = _NUTEN.get(kennung)
    if eintrag is not None and eintrag[0].isSame(form):
        return eintrag[1]
    ergebnis = _nuten(form)
    _NUTEN[kennung] = (form, ergebnis)
    while len(_NUTEN) > FORMEN_GEMERKT:
        _NUTEN.popitem(last=False)
    return ergebnis


def hobelnuten(form, namen=None):
    """[Hobelnut] – die hobelbaren Nuten der Form; mit `namen` nur die, zu denen eine dieser
    Flächen gehört (der Grund oder eine Wand)."""
    gesucht = set(namen) if namen is not None else None
    return [
        n
        for n in alle_hobelnuten(form)
        if not n.grund and (gesucht is None or gesucht & set(n.flaechen))
    ]


def _ist_grund(flaeche):
    """Eine ebene Fläche, die nach oben schaut, mit genau zwei Rändern?"""
    import Part

    if not isinstance(flaeche.Surface, Part.Plane) or len(flaeche.Wires) != 2:
        return False
    # Nicht über den Kasten: Mit Freiformrändern ist er um Hundertstel zu hoch.
    if abs(abs(flaeche.Surface.Axis.z) - 1.0) > 1e-9:
        return False
    u0, u1, v0, v1 = flaeche.ParameterRange
    return flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2).z > 1.0 - 1e-6


def _nuten(form):

    alle = form.Faces
    ergebnis = []
    for nummer, flaeche in enumerate(alle):
        if not _ist_grund(flaeche):
            continue
        aussen = flaeche.OuterWire
        innen = next(w for w in flaeche.Wires if not w.isSame(aussen))
        waende, z_oben = _waende(form, alle, flaeche)
        z_boden = float(flaeche.Surface.Position.z)
        if not waende or z_oben <= z_boden + kb.NAH:
            continue  # kein Grund zwischen zwei Wänden: eine Stufe, ein Absatz
        name = f"Face{nummer + 1}"
        breite, schwankung = _breite(aussen, innen)
        grund = ""
        segmente, laenge, r_min = (), 0.0, math.inf
        if schwankung > BREITE_GLEICH:
            grund = tr(
                "hn.grund.breite",
                von=_mm(breite - schwankung / 2),
                bis=_mm(breite + schwankung / 2),
            )
        else:
            ecke = _ecke(aussen) or _ecke(innen)
            if ecke is not None:
                grund = tr("hn.grund.ecke", x=_mm(ecke[0]), y=_mm(ecke[1]))
            else:
                segmente = _mittellinie(aussen, breite)
                if not segmente:
                    grund = tr("hn.grund.mittellinie")
                else:
                    laenge = sum(s.laenge for s in segmente)
                    r_min = _kleinster_radius(segmente)
        ergebnis.append(
            Hobelnut(
                name, (name, *waende), breite, z_boden, z_oben, tuple(segmente), laenge, r_min,
                True, grund,
            )  # fmt: skip
        )
    return ergebnis


def _mm(wert):
    from . import einheiten

    return einheiten.text(wert, einheiten.LAENGE)


def _waende(form, alle, grund):
    """(Namen der Wände am Rand des Grunds, die niedrigste Oberkante) – Wände stehen senkrecht
    und steigen vom Grund auf. Fehlt an einer Kante die Wand, ist es keine Nut: ([], 0)."""
    import Part

    namen, oben = [], math.inf
    z = float(grund.Surface.Position.z)
    for kante in grund.Edges:
        wand = None
        for nachbar in form.ancestorsOfType(kante, Part.Face):
            if nachbar.isSame(grund):
                continue
            hoehen = [float(v.Point.z) for v in nachbar.Vertexes]  # genau, anders als der Kasten
            if kb.ist_wand(nachbar) and max(hoehen) > z + kb.NAH and min(hoehen) > z - kb.NAH:
                wand = nachbar
        if wand is None:
            return [], 0.0
        oben = min(oben, max(float(v.Point.z) for v in wand.Vertexes))
        for k, f in enumerate(alle):
            if f.isSame(wand):
                if f"Face{k + 1}" not in namen:
                    namen.append(f"Face{k + 1}")
                break
    return namen, oben


def _breite(aussen, innen):
    """(Breite, Schwankung): der Abstand der inneren Wand zur äußeren, an Stellen alle PROBEN mm
    – der Mittelwert und der Unterschied zwischen größtem und kleinstem."""
    import Part

    anzahl = max(24, int(innen.Length / PROBEN))
    abstaende = [aussen.distToShape(Part.Vertex(p))[0] for p in innen.discretize(Number=anzahl)]
    kleinste, groesste = min(abstaende), max(abstaende)
    return (kleinste + groesste) / 2.0, groesste - kleinste


def _richtung_am_ende(segment, anfang):
    """Die Fahrtrichtung (Winkel) am Anfang oder Ende eines Stücks."""
    if segment.bogen is None:
        return math.atan2(segment.nach[1] - segment.von[1], segment.nach[0] - segment.von[0])
    p = segment.von if anfang else segment.nach
    radial = math.atan2(p[1] - segment.mitte[1], p[0] - segment.mitte[0])
    return radial - math.pi / 2 if segment.uhr else radial + math.pi / 2


def _knick(a, b):
    """Der Winkel (0 … π) zwischen dem Ende von `a` und dem Anfang von `b`."""
    d = (_richtung_am_ende(b, True) - _richtung_am_ende(a, False)) % (2 * math.pi)
    return min(d, 2 * math.pi - d)


def _ecke(draht):
    """Die erste Ecke im Rand `draht` – (x, y), wo zwei Stücke mit einem Knick aneinanderstoßen;
    None, wenn alles gerundet ist."""
    segmente = kb._segmente(draht, NETZ)
    for a, b in zip(segmente, segmente[1:] + segmente[:1], strict=True):
        if _knick(a, b) > KNICK:
            return a.nach
    return None


def _mittellinie(aussen, breite):
    """Die Mittellinie als Strecken und Bögen, gegen den Uhrzeigersinn – der äußere Rand um die
    halbe Breite nach innen; [] wenn der Versatz nicht ein geschlossener Zug wird."""
    try:
        draehte = kb._versatz_draehte(aussen, -breite / 2.0, False)
    except Exception:  # noqa: BLE001 – OpenCascade: kein Versatz
        return []
    if len(draehte) != 1 or not draehte[0].isClosed():
        return []
    segmente = kb._segmente(draehte[0], NETZ)
    if not segmente:
        return []
    # Gegen den Uhrzeigersinn: die umlaufene Fläche (Gaußsche Trapezformel über die Stellen) > 0.
    proben = kb._abtasten(segmente, 0.5, True)
    x, y = proben.x, proben.y
    flaeche = 0.5 * float(
        (x * (y[list(range(1, len(y))) + [0]]) - y * x[list(range(1, len(x))) + [0]]).sum()
    )
    if flaeche < 0:
        segmente = [s.umgekehrt() for s in reversed(segmente)]
    return segmente


def _kleinster_radius(segmente):
    """Der kleinste Radius der Mittellinie: der der Bögen; bei Linienzügen (eine Freiformkurve)
    der Umkreis dreier Stellen nacheinander."""
    kleinster = math.inf
    for a, b in zip(segmente, segmente[1:] + segmente[:1], strict=True):
        if a.bogen is not None:
            kleinster = min(kleinster, a.radius)
        elif b.bogen is None:
            winkel = _knick(a, b)
            if winkel > 1e-4:  # zwei Sehnen einer Kurve: R ≈ mittlere Sehne ÷ Winkel
                kleinster = min(kleinster, 0.5 * (a.laenge + b.laenge) / winkel)
    return kleinster


# --- Die Klinge -------------------------------------------------------------------------------------


def kleinster_radius_fuer(nut_breite, breite, laenge):
    """Der kleinste Radius der Mittellinie, den eine Klinge (`breite` breit, der Körper `laenge`
    hinter der Schneide) in einer Nut der Breite `nut_breite` fahren kann: Ihre hintere äußere
    Ecke bleibt vor der Außenwand – √((R + b/2)² + L²) ≤ R + B/2 − SPIEL. 0: jede Kurve; inf:
    die Klinge ist zu breit."""
    luft = (nut_breite - breite) / 2.0 - SPIEL
    if luft < 0:
        return math.inf
    if laenge <= 0:
        return 0.0
    if luft <= 1e-12:
        return math.inf
    # (R + b/2)² + L² = (R + b/2 + luft)²  →  R = (L² − luft²) ÷ (2 · luft) − b/2
    return max(0.0, (laenge * laenge - luft * luft) / (2.0 * luft) - breite / 2.0)


def klinge_pruefen(nut, breite, laenge):
    """ "" wenn die Klinge die Nut fahren kann – sonst der Satz, warum nicht (zu breit; der
    Radius, den sie bräuchte)."""
    if breite <= 0:
        return tr("hn.grund.klinge_breite_fehlt")
    if breite > nut.breite - 2 * SPIEL + 1e-9:
        return tr("hn.grund.klinge_breit", b=_mm(breite), breite=_mm(nut.breite))
    noetig = kleinster_radius_fuer(nut.breite, breite, laenge)
    if nut.r_min < noetig - 1e-9:
        return tr(
            "hn.grund.klinge_radius", r=_mm(nut.r_min), noetig=_mm(noetig), laenge=_mm(laenge)
        )
    return ""
