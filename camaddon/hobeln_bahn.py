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

Schritt 2 – **die Bahn** (planen()): Die Schneide läuft auf der Mittellinie (ist die Klinge schmaler
als die Nut, in mehreren Spuren nebeneinander), in kleinen Schritten (SCHRITT, einstellbar), und die
Spindel steht je Satz so, dass die Klinge in Fahrtrichtung zeigt: Winkel = Richtung der Bahn +
Versatz des Werkzeugs (bei welchem Spindelwinkel die Schneide nach +X zeigt – beim Einrichten
gemessen). Der Winkel steht als Kommentar „(SPINDEL …)“ vor jedem Satz; das Programm (Schritt 5)
macht daraus je Steuerung den Spindelwinkel im Satz. Die Nut ist davor gefräst, bis auf `rest` über dem
Grund: Die Klinge taucht im Freien der Nut ein, dann Umläufe, jeder um `zustellung` tiefer (über den
ganzen Umlauf verteilt – kein Absatz), bis auf das Aufmaß; dort ein ebener Umlauf und die
Leerumläufe. Gefahren wird nur vorwärts (die Klinge schneidet nur nach vorn); zwischen zwei Spuren
heraus und wieder hinein.

Noch nicht: Nuten mit Enden (Langloch, zum Rand offen) – dort kommt der Hub mit Abheben dazu.
Das Werkzeug, die Operation und das Programm folgen in den Schritten 3 bis 5.

Läuft ohne Oberfläche.
"""

import math
from collections import OrderedDict
from dataclasses import dataclass

from . import bahn as bn
from . import kontur_bahn as kb
from .sprache import tr

BREITE_GLEICH = 0.02  # mm – so gleich muss die Nut überall breit sein
KNICK = math.radians(6.0)  # ab diesem Winkel zwischen zwei Stücken einer Wand: eine Ecke
NETZ = 0.001  # mm – so fein werden Kurven der Wände abgetastet (Ecken von Rundungen trennen)
PROBEN = 0.5  # mm – so dicht wird die Breite an der inneren Wand gemessen
SPIEL = 0.005  # mm – so viel Luft braucht die hintere Ecke der Klinge zur Außenwand
FORMEN_GEMERKT = 8
SCHRITT = 0.5  # mm – so lang ist ein Satz der Hobelbahn (die Spindel dreht je Satz nach)
SPUR_UEBERLAPP = 0.2  # so viel der Klingenbreite überlappen zwei Spuren
SPUR_REST = 0.05  # mm – so schmal darf der Rand am Grund je Seite ungehobelt bleiben: eine Spur
SPUR_SCHRAEG = math.radians(2.0)  # so schräg darf die Spur seitlich ausweichen (weich, nicht quer)
SPINDEL = "SPINDEL"  # der Kommentar mit dem Spindelwinkel vor jedem Satz: „(SPINDEL 123.456)“


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


# --- Die Bahn ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Hobelwerte:
    """Was das Hobeln braucht; Längen in mm, Winkel in Grad, z nach oben im Job."""

    breite: float  # der Klinge (quer zur Fahrt)
    laenge: float  # der Klinge hinter der Schneide
    versatz: float  # bei diesem Spindelwinkel zeigt die Schneide nach +X
    zustellung: float  # je Umlauf tiefer (Horn: höchstens 0,3 je Hub)
    rest: float  # so viel steht nach dem Fräsen noch über dem Grund
    sicher: float  # z für den Eilgang über allem
    vorschub: float  # mm/min – die Schnittgeschwindigkeit
    eintauchen: float = 0.0  # mm/min – hinab in die gefräste Nut; 0: wie der Vorschub
    aufmass: float = 0.0  # bleibt auf dem Grund stehen
    leerumlaeufe: int = 1  # Umläufe auf Endtiefe ohne Zustellung
    sicherheit: float = 2.0  # so weit über der Oberkante endet der Eilgang hinab
    schritt: float = SCHRITT


@dataclass
class Hobelbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], je Satz der Spindelwinkel als Notiz „SPINDEL …“
    winkel: list  # je Punkt der Spindelwinkel (Grad, fortlaufend) – None im Eilgang
    spuren: int
    umlaeufe: int  # je Spur, mit den Leerumläufen
    laenge: float  # mm im Vorschub
    zeit: float  # Minuten


def _stellen(nut, schritt):
    """[(x, y, Richtung rad)] längs der Mittellinie, höchstens `schritt` auseinander, der erste
    Punkt am Anfang, ohne Wiederholung am Ende (geschlossen)."""
    ergebnis = []
    for s in nut.segmente:
        anzahl = max(1, int(math.ceil(s.laenge / schritt - 1e-9)))
        for i in range(anzahl):
            t = i / anzahl
            x, y = s.bei(t)
            if s.bogen is None:
                richtung = math.atan2(s.nach[1] - s.von[1], s.nach[0] - s.von[0])
            else:
                radial = math.atan2(y - s.mitte[1], x - s.mitte[0])
                richtung = radial - math.pi / 2 if s.uhr else radial + math.pi / 2
            ergebnis.append((float(x), float(y), richtung))
    return ergebnis


def _spuren(nut, breite):
    """Die Versätze der Spuren quer zur Mittellinie (mm, + nach links): eine, wenn die Klinge die
    Nut füllt; sonst so viele, dass sie mit SPUR_UEBERLAPP überlappen und die äußeren an den
    Wänden laufen."""
    frei = max(nut.breite - breite - 2 * SPIEL, 0.0) / 2.0
    if frei <= SPUR_REST + 1e-9:
        return [0.0]
    abstand = breite * (1.0 - SPUR_UEBERLAPP)
    anzahl = int(math.ceil(2 * frei / abstand - 1e-9)) + 1
    return [-frei + 2 * frei * k / (anzahl - 1) for k in range(anzahl)]


def _kruemmung(stellen, laenge):
    """Je Stelle der kleinste Krümmungsradius (mit Vorzeichen: + Linkskurve) über die Länge der
    Klinge dahinter – dort schwenkt ihre hintere Ecke aus; inf auf Geraden."""
    n = len(stellen)
    radien = []
    for i in range(n):
        x0, y0, r0 = stellen[i - 1]
        x1, y1, r1 = stellen[i]
        ds = math.hypot(x1 - x0, y1 - y0)
        dr = (r1 - r0 + math.pi) % (2 * math.pi) - math.pi
        radien.append(ds / dr if abs(dr) > 1e-9 else math.inf)
    ergebnis = []
    for i in range(n):
        kleinster, weg, k = math.inf, 0.0, i
        while weg <= laenge + 1e-9 and k > i - n:
            r = radien[k % n]
            if abs(r) < abs(kleinster):
                kleinster = r
            x0, y0, _r = stellen[(k - 1) % n]
            x1, y1, _r = stellen[k % n]
            weg += math.hypot(x1 - x0, y1 - y0)
            k -= 1
        ergebnis.append(kleinster)
    return ergebnis


def _weich(stellen, versaetze, d_spur):
    """Die Versätze je Stelle so geglättet, dass die Spur höchstens um SPUR_SCHRAEG seitlich
    ausweicht – nur in die sichere Richtung (weiter weg von d_spur), nie zurück: Sonst spränge die
    Klinge am Anfang einer Kurve quer (am Rechteck R 10 um 19°)."""
    n = len(versaetze)
    s = [d - d_spur for d in versaetze]
    k = math.tan(SPUR_SCHRAEG)
    wege = []
    for i in range(n):
        x0, y0, _r = stellen[i - 1]
        x1, y1, _r = stellen[i]
        wege.append(math.hypot(x1 - x0, y1 - y0))
    for _ in range(4 * n):
        geaendert = False
        for i in list(range(n)) + list(range(n - 1, -1, -1)):
            for j, weg in ((i - 1, wege[i]), ((i + 1) % n, wege[(i + 1) % n])):
                nachbar = s[j % n]
                grenze = abs(nachbar) - k * weg
                if grenze > abs(s[i]) + 1e-12 and (s[i] == 0 or (s[i] > 0) == (nachbar > 0)):
                    s[i] = math.copysign(grenze, nachbar)
                    geaendert = True
        if not geaendert:
            break
    return [d_spur + v for v in s]


def _versatz_erlaubt(nut, breite, laenge, radius):
    """So weit darf die Spur in einer Kurve mit `radius` zur Außenwand hin liegen, damit die hintere
    äußere Ecke der Klinge vor ihr bleibt: √((R + d + b/2)² + L²) ≤ R + B/2 − SPIEL."""
    r = abs(radius)
    if not math.isfinite(r):
        return math.inf
    aussen = r + nut.breite / 2.0 - SPIEL
    if aussen <= laenge:
        return -math.inf
    return math.sqrt(aussen * aussen - laenge * laenge) - r - breite / 2.0


def planen(nut, werte):
    """Die Hobelbahn (Hobelbahn) für die Nut `nut` (Hobelnut) mit den Werten `werte`
    (Hobelwerte). ValueError mit einem Satz, wenn es nicht geht."""
    w = werte
    grund = klinge_pruefen(nut, w.breite, w.laenge)
    if grund:
        raise ValueError(grund)
    if w.zustellung <= 0 or w.vorschub <= 0:
        raise ValueError(tr("hn.fehler.werte"))
    z_ende = nut.z_boden + max(w.aufmass, 0.0)
    z_start = min(nut.z_boden + max(w.rest, 0.0), nut.z_oben)
    if z_start < z_ende:
        z_start = z_ende
    stellen = _stellen(nut, max(w.schritt, 0.05))
    hoch = nut.z_oben + w.sicherheit
    punkte, winkel_ = [], []
    letzter_winkel = None

    def winkel_bei(richtung):
        """Der Spindelwinkel (Grad) zur Fahrtrichtung, fortlaufend – ohne Sprung um 360°."""
        nonlocal letzter_winkel
        wert = math.degrees(richtung) + w.versatz
        if letzter_winkel is not None:
            wert += 360.0 * round((letzter_winkel - wert) / 360.0)
        letzter_winkel = wert
        return wert

    def setze(punkt, winkel):
        notiz = None if winkel is None else f"{SPINDEL} {winkel:.3f}"
        punkte.append(bn.Punkt(punkt[0], punkt[1], punkt[2], punkt[3], punkt[4], None, 1.0, notiz))
        winkel_.append(winkel)

    tiefe = z_start - z_ende
    umlaeufe = max(1, int(math.ceil(tiefe / w.zustellung - 1e-9))) if tiefe > 1e-9 else 0
    spuren = _spuren(nut, w.breite)
    kruemmung = _kruemmung(stellen, w.laenge) if len(spuren) > 1 else None
    for d_spur in spuren:
        reihe = []
        for i in range(len(stellen)):
            d = d_spur
            if kruemmung is not None:
                # In der Kurve schwenkt die hintere Ecke zur Außenwand aus: Die Spur rückt dort
                # so weit nach innen (am Rechteck R 10 mit der Klinge 2,6 × 2 sonst 0,11 mm² über
                # die Wand).
                erlaubt = _versatz_erlaubt(nut, w.breite, w.laenge, kruemmung[i])
                if kruemmung[i] > 0:  # Linkskurve: die Außenwand liegt rechts (−)
                    d = max(d, -erlaubt)
                elif kruemmung[i] < 0:
                    d = min(d, erlaubt)
            reihe.append(d)
        reihe = _weich(stellen, reihe, d_spur)
        reihe = [
            (x + d * -math.sin(richtung), y + d * math.cos(richtung), richtung)
            for (x, y, richtung), d in zip(stellen, reihe, strict=True)
        ]
        x0, y0, r0 = reihe[0]
        a0 = winkel_bei(r0)
        # Über dem Anfang dreht die Spindel in Richtung – oben, nicht erst in der Nut (dort stieße
        # die Klinge beim Drehen an die Wände); im Eilgang hinab bis über die Nut, in die gefräste
        # Nut im Eintauchvorschub bis auf den Rest.
        setze((True, x0, y0, w.sicher, False), a0)
        setze((True, x0, y0, hoch, False), None)
        setze((False, x0, y0, z_start, True), a0)
        z = z_start
        anzahl = len(reihe)
        for _u in range(umlaeufe):
            z_neu = max(z - w.zustellung, z_ende)
            for k in range(1, anzahl + 1):
                x, y, richtung = reihe[k % anzahl]
                z_k = z + (z_neu - z) * k / anzahl
                setze((False, x, y, z_k, False), winkel_bei(richtung))
            z = z_neu
        for _u in range(1 + max(int(w.leerumlaeufe), 0)):  # eben auf Endtiefe, dann leer
            for k in range(1, anzahl + 1):
                x, y, richtung = reihe[k % anzahl]
                setze((False, x, y, z_ende, False), winkel_bei(richtung))
        setze((True, x0, y0, w.sicher, False), None)  # senkrecht hinaus
    laenge = bn.laenge(punkte)
    zeit = bn.zeit(punkte, w.vorschub, w.eintauchen or None)
    return Hobelbahn(
        punkte, winkel_, len(spuren), umlaeufe + 1 + max(int(w.leerumlaeufe), 0), laenge, zeit
    )
