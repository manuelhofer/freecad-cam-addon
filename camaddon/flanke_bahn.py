# SPDX-License-Identifier: LGPL-2.1-or-later
"""5 Achsen simultan, S3: die Flanke (W-015, Spezifikation Strategien 16.3; Manuel, 2026-10-04:
„Ja, so bauen“ – nach dem Versuch an der Tasche mit 10° Formschräge: 0,45 statt 4,26 min).

Eine schräge Wand, deren Fläche aus Geraden besteht – eine Ebene, ein Kegel, ein schräger
Zylinder, eine Regelfläche –, fräst der Mantel eines Schaftfräsers in einem Umlauf: Seine Achse
liegt parallel zur Mantellinie der Wand (der Geraden in ihr), um seinen Radius davor. An einer
Ebene ist die Mantellinie die Fallinie, am Kegel die Linie zur Spitze, an anderen Flächen die
gerade Parameterlinie.

- **Welche Wände** (`ist_wand`): Ebene, Kegel, schräger Zylinder oder eine Fläche mit geraden
  Parameterlinien, die nach oben offen ist und um 0,5° bis 45° von der Senkrechten abweicht –
  senkrechte Wände fräst die Kontur, flachere das 3D-Schlichten.
- **Umläufe:** Die unteren Kanten der gewählten Wände hängen sich zu Zügen zusammen; je Zug ein
  Umlauf im Gleichlauf (das Material rechts, M3). Stoßen zwei Wände in einer scharfen Kante
  aneinander (die Normalen mehr als KNICK auseinander), endet der Umlauf dort und beginnt an der
  nächsten Wand neu.
- **Stellen:** an geraden Kanten einer Ebene alle SCHRITT_EBEN (die Achse bleibt), sonst alle
  SCHRITT. Je Stelle die Spitze: der Fuß der Mantellinie plus (Radius + Aufmaß) entlang der
  Normale – die Stirn steht dann nirgends tiefer als der Fuß (sonst wird sie so weit gehoben).
  Würde der Fräser dort in eine andere Fläche des Teils schneiden (eine scharfe Innenecke), fällt
  die Stelle weg – dort bleibt Material, wie bei jedem Schaftfräser.
- **Lagen:** Ist die Wand länger als die Schneide, mehrere Umläufe von oben nach unten.
- **An- und Abfahren:** im Eilgang über dem Anfang die Achse entlang hinab, im Eintauchvorschub
  bis ABSTAND vor der Wand, quer an die Wand; am Ende quer weg und die Achse entlang hinauf.

Gerechnet in x, y, z des Jobs; je Punkt die Spitze und die Werkzeugachse (von der Spitze weg).
Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field

import FreeCAD

from .sprache import tr

NEIGUNG_MIN = 0.5  # Grad – so weit muss eine Wand mindestens von der Senkrechten abweichen
NEIGUNG_MAX = 45.0  # Grad – flacher ist es das 3D-Schlichten
SCHRITT = 0.2  # mm – so dicht liegen die Stellen an gekrümmten Kanten
SCHRITT_EBEN = 2.0  # mm – an geraden Kanten einer Ebene (die Achse bleibt; dazwischen halbiert)
KNICK = 1.0  # Grad – mehr zwischen den Normalen zweier Wände: eine scharfe Kante
ABSTAND = 2.0  # mm – so weit vor der Wand beginnt und endet ein Umlauf
GERADE = 1e-4  # mm je mm – so weit darf eine Parameterlinie von der Sehne abweichen
TOLERANZ = 0.002  # mm – so viel näher als der Radius darf eine andere Fläche der Achse kommen
SICHERHEIT = 2.0  # mm über dem Rohteil
UEBERLAPP = 0.5  # mm – so viel überlappen sich zwei Lagen


@dataclass
class Flankenwerte:
    """Was die Flanke braucht; Längen in mm, z nach oben im Job."""

    radius: float  # des Schaftfräsers
    schneide: float  # Schneidenlänge
    oben: float  # z, über dem nichts mehr steht (das Rohteil)
    sicher: float  # z für den Eilgang über allem
    aufmass: float = 0.0
    vorschub: float = 0.0  # mm/min – für die Zeit; 0: 1000
    eintauchen: float = 0.0
    sicherheit: float = SICHERHEIT
    gleichlauf: bool = True
    schritt: float = SCHRITT  # so dicht liegen die Stellen an gekrümmten Kanten (T-009)


@dataclass
class Stelle:
    """Ein Punkt der Bahn: die Spitze, die Werkzeugachse (von der Spitze weg), wie hierher."""

    spitze: tuple
    achse: tuple
    eilgang: bool = False
    eintauchen: bool = False


@dataclass
class Flankenbahn:
    """Ergebnis von planen()."""

    punkte: list  # [Stelle]
    umlaeufe: int  # Umläufe (je Zug und Lage)
    lagen: int
    laenge: float  # mm im Vorschub
    zeit: float  # Minuten
    neigung: float  # Grad – die größte Neigung der Achse gegen die Senkrechte
    weggelassen: int = 0  # Stellen, an denen der Fräser in eine andere Fläche schnitte
    zuege: list = field(default_factory=list)  # je Zug die Flächen


# --- Die Wände ------------------------------------------------------------------------------


def _v(p):
    return FreeCAD.Vector(*p)


def _gerade_linie(kurve, von, bis):
    """Ist die Kurve zwischen den Parametern gerade (GERADE je mm)? Die Endpunkte dazu."""
    a, b = kurve.value(von), kurve.value(bis)
    laenge = (b - a).Length
    if laenge < 1e-6:
        return False, a, b
    for k in (0.25, 0.5, 0.75):
        p = kurve.value(von + (bis - von) * k)
        d = p - a
        quer = (d - (b - a) * (d.dot(b - a) / laenge**2)).Length
        if quer > GERADE * laenge:
            return False, a, b
    return True, a, b


def mantellinie(form, flaeche, punkt):
    """(Fuß, Kopf, Achse, Normale) der Mantellinie der Fläche (Part.Face) durch `punkt`: Fuß und
    Kopf, wo sie die Fläche unten und oben verlässt, die Achse nach oben, die Normale zur Luft
    hin und quer zur Achse. None, wenn die Fläche dort keine Gerade hat."""
    import Part

    flaeche_typ = flaeche.Surface
    u, v = flaeche_typ.parameter(punkt)
    n = flaeche.normalAt(u, v)
    if form.isInside(punkt + n * 0.05, 1e-6, False):
        n = -n
    if _eben(flaeche):
        z = FreeCAD.Vector(0, 0, 1)
        achse = z - n * z.dot(n)
    elif isinstance(flaeche_typ, Part.Cone):
        achse = punkt - flaeche_typ.Apex
    elif isinstance(flaeche_typ, Part.Cylinder):
        achse = FreeCAD.Vector(flaeche_typ.Axis)
    else:
        u0, u1, v0, v1 = flaeche.ParameterRange
        achse = None
        for iso, von, bis in (
            (flaeche_typ.uIso(u), v0, v1),
            (flaeche_typ.vIso(v), u0, u1),
        ):
            gerade, a, b = _gerade_linie(iso, von, bis)
            if gerade and abs((b - a).z) > 1e-6:
                achse = b - a
                break
        if achse is None:
            return None
    if achse.Length < 1e-9:
        return None
    achse.normalize()
    if achse.z < 0:
        achse = -achse
    n = n - achse * n.dot(achse)
    if n.Length < 1e-9:
        return None
    n.normalize()

    # Fuß und Kopf: die Gerade so weit, wie sie in der Fläche liegt (halbieren).
    def ende(richtung):
        drin, draussen = 0.0, max(flaeche.BoundBox.DiagonalLength, 1.0)
        for _ in range(40):
            mitte = (drin + draussen) / 2
            if flaeche.isInside(punkt + richtung * mitte, 1e-4, True):
                drin = mitte
            else:
                draussen = mitte
        return punkt + richtung * drin

    return ende(-achse), ende(achse), achse, n


def _eben(flaeche):
    """Ist die Fläche eben – auch als B-Spline (ein Loft zwischen zwei Rechtecken)? Dann ist jede
    Gerade in ihr eine Mantellinie; die Flanke nimmt die Fallinie."""
    import Part

    if isinstance(flaeche.Surface, Part.Plane):
        return True
    try:
        return flaeche.findPlane(1e-6) is not None
    except Exception:  # ältere Fassung ohne findPlane
        return False


def ist_wand(form, name):
    """Kann die Flanke die Fläche `name` fräsen? Eine Wand aus Geraden, nach oben offen,
    NEIGUNG_MIN … NEIGUNG_MAX von der Senkrechten (Modul-Text)."""
    try:
        flaeche = form.getElement(name)
    except Exception:  # keine Fläche dieses Namens
        return False
    if not hasattr(flaeche, "Surface") or flaeche.Area < 1e-6:
        return False
    u0, u1, v0, v1 = flaeche.ParameterRange
    punkt = flaeche.valueAt((u0 + u1) / 2, (v0 + v1) / 2)
    if not flaeche.isInside(punkt, 1e-4, True):
        punkt = flaeche.CenterOfMass
        punkt = flaeche.Surface.value(*flaeche.Surface.parameter(punkt))
    linie = mantellinie(form, flaeche, punkt)
    if linie is None:
        return False
    fuss, kopf, achse, normale = linie
    neigung = math.degrees(math.acos(max(-1.0, min(1.0, achse.z))))
    return NEIGUNG_MIN <= neigung <= NEIGUNG_MAX and normale.z > 0 and (kopf - fuss).Length > 1e-3


def wandflaechen(form, namen):
    """Die Namen aus `namen`, die die Flanke fräsen kann."""
    return [n for n in namen if n.startswith("Face") and ist_wand(form, n)]


# --- Die Züge ------------------------------------------------------------------------------


def _untere_kanten(form, name):
    """[(Kante, Name)] – die Kanten der Fläche, an denen ihre Mantellinien unten beginnen: An der
    Mitte der Kante liegt der Fuß der Mantellinie, ihr Kopf weit darüber, und die Kante läuft
    quer zu ihr (eine Seite der Wand ist selbst fast eine Mantellinie)."""
    flaeche = form.getElement(name)
    ergebnis = []
    for kante in flaeche.Edges:
        if kante.Length < 1e-6:
            continue
        mitte = kante.FirstParameter + 0.5 * (kante.LastParameter - kante.FirstParameter)
        p = kante.valueAt(mitte)
        linie = mantellinie(form, flaeche, p)
        if linie is None:
            continue
        fuss, kopf, achse, _normale = linie
        tangente = kante.tangentAt(mitte)
        if tangente.Length > 0:
            tangente.normalize()
        quer = abs(tangente.dot(achse)) < math.cos(math.radians(45.0))
        if quer and (fuss - p).Length < 1e-3 and (kopf - p).Length > 1e-2:
            ergebnis.append((kante, name))
    return ergebnis


def zuege(form, namen, genau=1e-3):
    """[[(Kante, Name, umgedreht)]] – die unteren Kanten der Wände, zu Zügen aneinander gehängt
    (Ende an Anfang), je Zug ob er geschlossen ist: [(Zug, geschlossen)]."""
    offen = []
    for name in namen:
        offen.extend(_untere_kanten(form, name))
    ergebnis = []
    while offen:
        kante, name = offen.pop(0)
        zug = [(kante, name, False)]
        for richtung in (1, -1):
            while True:
                if richtung == 1:
                    k, _n, um = zug[-1]
                    ende = k.Vertexes[0].Point if um else k.Vertexes[-1].Point
                else:
                    k, _n, um = zug[0]
                    ende = k.Vertexes[-1].Point if um else k.Vertexes[0].Point
                treffer = None
                for i, (k2, n2) in enumerate(offen):
                    a, b = k2.Vertexes[0].Point, k2.Vertexes[-1].Point
                    if (a - ende).Length < genau:
                        treffer = (i, k2, n2, richtung == -1)
                        break
                    if (b - ende).Length < genau:
                        treffer = (i, k2, n2, richtung == 1)
                        break
                if treffer is None:
                    break
                i, k2, n2, um2 = treffer
                offen.pop(i)
                if richtung == 1:
                    zug.append((k2, n2, um2))
                else:
                    zug.insert(0, (k2, n2, um2))
        k0, _n0, um0 = zug[0]
        k1, _n1, um1 = zug[-1]
        anfang = k0.Vertexes[-1].Point if um0 else k0.Vertexes[0].Point
        ende = k1.Vertexes[0].Point if um1 else k1.Vertexes[-1].Point
        ergebnis.append((zug, (anfang - ende).Length < genau))
    return ergebnis


def _punkte_der_kante(form, kante, name, umgedreht, schritt=SCHRITT):
    """[Punkt] entlang der Kante in Fahrrichtung: an einer geraden Kante einer Ebene alle
    SCHRITT_EBEN (die Achse bleibt dort; wo eine Innenecke beginnt, sucht _grenze genauer), sonst
    alle `schritt`."""
    import Part

    flaeche = form.getElement(name)
    eben = _eben(flaeche) and isinstance(kante.Curve, Part.Line)
    anzahl = max(1, int(math.ceil(kante.Length / (SCHRITT_EBEN if eben else schritt))))
    punkte = kante.discretize(Number=anzahl + 1)
    return list(reversed(punkte)) if umgedreht else punkte


# --- Die Bahn ------------------------------------------------------------------------------


def _winkel(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b)))))


def _stelle(form, flaeche, punkt, w):
    """(Spitze, Achse, Normale, Fuß, Wandlänge, Fläche) an `punkt` auf der unteren Kante – die
    Spitze um Radius und Aufmaß vor der Mantellinie, die Stirn nirgends tiefer als der Fuß (ihr
    tiefster Punkt liegt R · sin(Neigung) unter der Mitte); None ohne Mantellinie."""
    linie = mantellinie(form, flaeche, punkt)
    if linie is None:
        return None
    fuss, kopf, achse, normale = linie
    spitze = punkt + normale * (w.radius + max(w.aufmass, 0.0))
    tiefster = spitze.z - w.radius * math.sqrt(max(0.0, 1.0 - achse.z**2))
    if tiefster < punkt.z - 1e-9:
        spitze = spitze + achse * ((punkt.z - tiefster) / max(achse.z, 1e-6))
    return (spitze, achse, normale, punkt, (kopf - fuss).Length, flaeche)


def _stellen_des_zugs(form, zug, w):
    """[[Stelle als Tupel (_stelle)]] – die Stellen eines Zugs, an scharfen Kanten in Stücke
    geteilt."""
    stuecke, stueck = [], []
    for kante, name, umgedreht in zug:
        flaeche = form.getElement(name)
        for punkt in _punkte_der_kante(form, kante, name, umgedreht, w.schritt):
            stelle = _stelle(form, flaeche, punkt, w)
            if stelle is None:
                continue
            if stueck:
                davor = stueck[-1]
                if (davor[3] - punkt).Length < 1e-6:
                    if (
                        _winkel(davor[2], stelle[2]) <= KNICK
                        and _winkel(davor[1], stelle[1]) <= KNICK
                    ):
                        continue  # dieselbe Stelle am Übergang zweier Wände
                    stuecke.append(stueck)
                    stueck = []
            stueck.append(stelle)
    if stueck:
        stuecke.append(stueck)
    return stuecke


def _schneidet(form, spitze, achse, laenge, radius):
    """Schnitte der Fräser hier ins Teil – in eine andere Fläche, eine scharfe Innenecke? Sein
    Zylinder, um TOLERANZ kleiner, darf das Teil nicht berühren (seine Wand berührt er dann
    nicht, den Boden unter der Stirn auch nicht)."""
    import Part

    zylinder = Part.makeCylinder(radius - TOLERANZ, laenge, spitze, achse)
    try:
        return form.distToShape(zylinder)[0] < 1e-9
    except Exception:  # eine Form, mit der OpenCascade nicht rechnen kann: lieber weglassen
        return True


def planen(form, namen, werte):
    """Die Bahn „Flanke“ (Flankenbahn) an den Wänden `namen` von `form` mit `werte`. ValueError
    mit einem Satz, wenn es nicht geht."""
    w = werte
    if w.radius <= 0 or w.schneide <= 0:
        raise ValueError(tr("fl.fehler.fraeser"))
    waende = wandflaechen(form, namen)
    if not waende:
        raise ValueError(tr("fl.fehler.keine"))
    punkte = []
    umlaeufe = lagen_max = weggelassen = 0
    neigung = 0.0
    namen_je_zug = []
    for zug, geschlossen in zuege(form, waende):
        stuecke = _stellen_des_zugs(form, zug, w)
        if geschlossen and stuecke and stuecke[0]:
            erste, letzte = stuecke[0][0], stuecke[-1][-1]
            glatt = _winkel(erste[2], letzte[2]) <= KNICK and _winkel(erste[1], letzte[1]) <= KNICK
            if len(stuecke) == 1 and glatt:
                stuecke[0].append(stuecke[0][0])  # rundherum: zurück zum Anfang
            elif len(stuecke) > 1 and glatt:
                stuecke[0] = stuecke.pop() + stuecke[0]  # der Anfang lag mitten in einer Wand
        # Gleichlauf: das Material rechts der Fahrrichtung (M3).
        stuecke = [_gerichtet(s, w.gleichlauf) for s in stuecke if len(s) >= 2]
        wand = max((st[4] for s in stuecke for st in s), default=0.0)
        lagen = max(1, int(math.ceil((wand - UEBERLAPP) / max(w.schneide - UEBERLAPP, 0.1))))
        lagen_max = max(lagen_max, lagen)
        hoehe = wand / lagen
        namen_je_zug.append(sorted({n for _k, n, _u in zug}))
        for lage in range(lagen):
            for stueck in stuecke:
                teile, aus = [], []
                davor = None  # (Stelle, geht) der Stelle davor
                for stelle in stueck:
                    geht = _geht(form, stelle, lage, hoehe, w)
                    if davor is not None and davor[1] != geht:
                        # Wo es von „geht“ auf „schneidet“ wechselt: die Grenze genauer.
                        grenze = _grenze(form, davor[0], stelle, davor[1], lage, hoehe, w)
                        if grenze is not None:
                            if davor[1]:
                                aus.append(grenze)
                            else:
                                aus = [grenze]
                    if geht:
                        aus.append(_lage(stelle, lage, hoehe))
                        neigung = max(neigung, _winkel(stelle[1], FreeCAD.Vector(0, 0, 1)))
                    else:
                        weggelassen += 1
                        if aus and (davor is None or davor[1]):
                            teile.append(aus)
                        aus = []
                    davor = (stelle, geht)
                if aus:
                    teile.append(aus)
                for teil in teile:
                    if len(teil) >= 2:
                        punkte.extend(_umlauf(teil, w))
                        umlaeufe += 1
    if not punkte:
        raise ValueError(tr("fl.fehler.nichts"))
    laenge, zeit = _laenge_und_zeit(punkte, w)
    return Flankenbahn(
        punkte, umlaeufe, lagen_max, laenge, zeit, neigung, weggelassen, namen_je_zug
    )


def _lage(stelle, lage, hoehe):
    """(Spitze, Achse, Normale) der Stelle in der Lage `lage` (von oben gezählt)."""
    spitze, achse, normale, _fuss, laenge, _flaeche = stelle
    return (spitze + achse * max(0.0, laenge - (lage + 1) * hoehe), achse, normale)


def _geht(form, stelle, lage, hoehe, w):
    """Schneidet der Fräser an der Stelle in dieser Lage nirgends ins Teil?"""
    spitze, achse, _normale = _lage(stelle, lage, hoehe)
    return not _schneidet(form, spitze, achse, min(w.schneide, stelle[4] + 1.0), w.radius)


def _grenze(form, a, b, a_geht, lage, hoehe, w, schritte=12):
    """(Spitze, Achse, Normale) der letzten Stelle zwischen `a` und `b` (Stellen), an der der
    Fräser noch nicht ins Teil schneidet – halbiert auf der Geraden zwischen ihren Füßen; None,
    wenn sie zu nah beieinander liegen."""
    if (a[3] - b[3]).Length <= w.schritt * 1.01:
        return None
    gut, schlecht = (a, b) if a_geht else (b, a)
    for _ in range(schritte):
        mitte = _zwischen(form, gut, schlecht, w)
        if mitte is None:
            return None
        if _geht(form, mitte, lage, hoehe, w):
            gut = mitte
        else:
            schlecht = mitte
    return _lage(gut, lage, hoehe) if gut is not a and gut is not b else None


def _zwischen(form, a, b, w):
    """Die Stelle in der Mitte zwischen `a` und `b` – ihr Fuß halb zwischen den Füßen, auf ihrer
    Wand; None, wenn dort keine Mantellinie ist."""
    fuss = (a[3] + b[3]) * 0.5
    for flaeche in (a[5], b[5]):
        if flaeche.isInside(fuss, 1e-4, True):
            return _stelle(form, flaeche, fuss, w)
    return None


def _gerichtet(stueck, gleichlauf):
    """Das Stück so herum, dass das Material rechts liegt (Gleichlauf mit M3) – sonst links."""
    rechts = 0.0
    for (s0, _a0, n0, *_r0), (s1, *_r1) in zip(stueck, stueck[1:], strict=False):
        t = s1 - s0
        rechts += -t.y * n0.x + t.x * n0.y  # (t × z) · (−n): das Material rechts
    if (rechts > 0) != gleichlauf:
        return list(reversed(stueck))
    return stueck


def _umlauf(teil, w):
    """[Stelle] – ein Umlauf mit An- und Abfahren."""
    ergebnis = []
    s0, a0, n0 = teil[0]
    frei = s0 + n0 * ABSTAND
    oben = w.oben + w.sicherheit
    for hoehe, eilgang in ((w.sicher, True), (oben, True)):
        lam = max(0.0, (hoehe - frei.z) / max(a0.z, 1e-6))
        ergebnis.append(Stelle(tuple(frei + a0 * lam), tuple(a0), eilgang=eilgang))
    ergebnis.append(Stelle(tuple(frei), tuple(a0), eintauchen=True))
    for s, a, _n in teil:
        ergebnis.append(Stelle(tuple(s), tuple(a)))
    s1, a1, n1 = teil[-1]
    weg = s1 + n1 * ABSTAND
    ergebnis.append(Stelle(tuple(weg), tuple(a1)))
    lam = max(0.0, (w.sicher - weg.z) / max(a1.z, 1e-6))
    ergebnis.append(Stelle(tuple(weg + a1 * lam), tuple(a1), eilgang=True))
    return ergebnis


def _laenge_und_zeit(punkte, w):
    """(mm im Vorschub, Minuten) – wie bahn.zeit, dazu dreht die Achse: Ändert sie ihre
    Richtung um die Senkrechte (an einer Tisch/Tisch-Maschine dreht C), zählt der Winkel in Grad
    wie mm (wie G93 in „Auf der Maschine prüfen“)."""
    from . import fahrzeit as fz

    vorschub = (w.vorschub or 1000.0) / 60.0
    eintauchen = (w.eintauchen or w.vorschub or 1000.0) / 60.0
    schnell = fz.EILGANG / 60.0
    a = fz.BESCHLEUNIGUNG
    saetze, laenge = [], 0.0
    for von, nach in zip(punkte, punkte[1:], strict=False):
        d = [q - p for p, q in zip(von.spitze, nach.spitze, strict=True)]
        if nach.eilgang:
            fest = fz.eilgangzeit(d, (schnell, schnell, schnell), (a, a, a))
            saetze.append(fz.Satz(0.0, schnell, a, fest=fest))
            continue
        weg = math.sqrt(sum(x * x for x in d))
        laenge += weg
        drehung = 0.0
        if math.hypot(von.achse[0], von.achse[1]) > 1e-3 and math.hypot(*nach.achse[:2]) > 1e-3:
            w0 = math.atan2(von.achse[1], von.achse[0])
            w1 = math.atan2(nach.achse[1], nach.achse[0])
            drehung = abs(math.degrees((w1 - w0 + math.pi) % (2 * math.pi) - math.pi))
        f = eintauchen if nach.eintauchen else vorschub
        saetze.append(fz.Satz(max(weg, drehung), f, a, tuple(d), tuple(d)))
    return laenge, sum(fz.zeiten(saetze)) / 60.0
