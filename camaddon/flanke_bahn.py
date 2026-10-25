# SPDX-License-Identifier: LGPL-2.1-or-later
"""5 Achsen simultan, S3: die Flanke (W-015, Spezifikation Strategien 16.3; Manuel, 2026-10-04:
„Ja, so bauen“ – nach dem Versuch an der Tasche mit 10° Formschräge: 0,45 statt 4,26 min).

Eine schräge Wand, deren Fläche aus Geraden besteht – eine Ebene, ein Kegel, ein schräger
Zylinder, eine Regelfläche –, fräst der Mantel eines Schaftfräsers in einem Umlauf: Seine Achse
liegt parallel zur Mantellinie der Wand (der Geraden in ihr), um seinen Radius davor. An einer
Ebene ist die Mantellinie die Fallinie, am Kegel die Linie zur Spitze, an anderen Flächen die
gerade Parameterlinie.

- **Welche Wände** (`ist_wand`): Ebene, Kegel, schräger Zylinder oder eine Fläche mit geraden
  Parameterlinien, die um 0,5° bis 45° von der Senkrechten abweicht – nach oben offen oder
  überhängend (Hinterschnitt) – senkrechte Wände fräst die Kontur, flachere das 3D-Schlichten.
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
- **Der Halter:** Mit `halter_pruefen` (die Körper über der Schneide, die dicker sind als sie:
  Halter, ein dicker Schaft) sieht die Bahn, wo er in die Wand führe – in den unteren Lagen liegt
  er dort, wo die Wand weiter oben steht (legros im Forum, 2026-10-10: ein Kegel, der ER16 im
  Kegel; Manuel, 2026-10-11: „es hilft nichts wenn der halter dann in den kegel reinballert“) –
  und wie weit das Werkzeug mindestens herausstehen müsste.
- **An- und Abfahren:** im Eilgang über dem Anfang die Achse entlang hinab, im Eintauchvorschub
  bis ABSTAND vor der Wand, quer an die Wand; am Ende quer weg und die Achse entlang hinauf.

Gerechnet in x, y, z des Jobs; je Punkt die Spitze und die Werkzeugachse (von der Spitze weg).
Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field, replace

import FreeCAD
import numpy as np

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
HALTER_NETZ = 0.05  # mm – so fein wird das Teil für halter_pruefen vernetzt
HALTER_TIEFER = 0.1  # mm – so weit (nach Netz und Schranke) muss ein Körper ins Teil, um zu zählen
HALTER_JE_ABFRAGE = 16  # so viele Stellen fragt halter_pruefen auf einmal (nah beieinander)
HALTER_LAENGER = 300.0  # mm – weiter heraus sucht halter_pruefen nicht
HALTER_SCHRITT = 1.0  # mm – so dicht längs der Bahn prüft halter_pruefen (die Bahn hat 0,2 mm)
# Ob der Fräser an einer Stelle ins Teil schneidet (_schneidet), fragt je Stelle und Lage
# OpenCascade – am Kegel mit drei Lagen 2364-mal, 15 s. Ab so vielen rechnen die Nebenrechner,
# je Auftrag so viele Stellen.
PARALLEL_AB = 200
STELLEN_JE_STUECK = 40
UEBERLAPP = 0.5  # mm – so viel überlappen sich zwei Lagen
ENDE_HALBIEREN = 30  # so oft halbiert mantellinie bis zum Ende der Geraden (Diagonale / 2³⁰)


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
    # Am Hinterschnitt (die Wand hängt über): so weit je Umlauf von innen an die Wand – den Keil
    # unter dem Rand, den das Räumen von oben stehen lässt (_versaetze); 0: ein Umlauf.
    quer: float = 0.0


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
    anstoss: object = None  # Anstoss: Halter oder Schaft im Teil (halter_pruefen), sonst None


@dataclass
class Anstoss:
    """Wo die Körper über der Schneide ins Teil führen (halter_pruefen)."""

    stellen: int  # so viele der geprüften Stellen im Vorschub (etwa je HALTER_SCHRITT eine)
    heraus: float  # mm von der Spitze bis zum ersten dickeren Körper (meist der Halter)
    mindestens: float  # mm – so weit müsste er von der Spitze weg sein, damit nichts anstößt


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
    if _zum_teil(form, flaeche):
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
        for _ in range(ENDE_HALBIEREN):
            mitte = (drin + draussen) / 2
            if flaeche.isInside(punkt + richtung * mitte, 1e-4, True):
                drin = mitte
            else:
                draussen = mitte
        return punkt + richtung * drin

    return ende(-achse), ende(achse), achse, n


def _zum_teil(form, flaeche):
    """Zeigt die Normale der Fläche (normalAt) ins Teil? In der Mitte der Fläche nachgesehen: An
    ihrem Rand läge der Prüfpunkt einer überhängenden Wand – die Normale zeigt schräg nach unten –
    an einer scharfen Bodenkante im Boden, und die Normale wäre falsch herum. Je Form und Fläche
    gemerkt: mantellinie fragt es an jeder Stelle (beim Anlegen an Manuels tiefer Tasche ein
    Fünftel der 25 s, in denen das Fenster stand)."""
    from . import uhren

    uhren.atmen()
    schluessel = (id(form), form.hashCode(), flaeche.hashCode())
    if schluessel in _ZUM_TEIL:
        return _ZUM_TEIL[schluessel]
    if len(_ZUM_TEIL) > 512:
        _ZUM_TEIL.clear()
    _ZUM_TEIL[schluessel] = ergebnis = _zum_teil_rechnen(form, flaeche)
    return ergebnis


_ZUM_TEIL = {}  # (id der Form, Fläche) → _zum_teil


def _zum_teil_rechnen(form, flaeche):
    u0, u1, v0, v1 = flaeche.ParameterRange
    mitte = flaeche.valueAt((u0 + u1) / 2, (v0 + v1) / 2)
    if not flaeche.isInside(mitte, 1e-4, True):
        mitte = flaeche.Surface.value(*flaeche.Surface.parameter(flaeche.CenterOfMass))
    u, v = flaeche.Surface.parameter(mitte)
    return bool(form.isInside(mitte + flaeche.normalAt(u, v) * 0.05, 1e-6, False))


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
    """Kann die Flanke die Fläche `name` fräsen? Eine Wand aus Geraden, NEIGUNG_MIN …
    NEIGUNG_MAX von der Senkrechten (Modul-Text) – nach oben offen oder überhängend (ein
    Hinterschnitt: die Tasche unten weiter als oben; Manuel, 2026-10-25, seine tiefe Tasche an
    der G550: Von oben kommt kein Fräser unter den Rand, gekippt längs der Wand schon)."""
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
    return NEIGUNG_MIN <= neigung <= NEIGUNG_MAX and (kopf - fuss).Length > 1e-3


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


def _versetzt(stelle, versatz, w):
    """Die Stelle (_stelle) um `versatz` weiter von der Wand weg – wie _stelle mit so viel mehr
    Aufmaß gerechnet, ohne die Mantellinie neu zu suchen."""
    if versatz <= 0.0:
        return stelle
    _spitze, achse, normale, punkt, laenge, flaeche = stelle
    spitze = punkt + normale * (w.radius + max(w.aufmass, 0.0) + versatz)
    tiefster = spitze.z - w.radius * math.sqrt(max(0.0, 1.0 - achse.z**2))
    if tiefster < punkt.z - 1e-9:
        spitze = spitze + achse * ((punkt.z - tiefster) / max(achse.z, 1e-6))
    return (spitze, achse, normale, punkt, laenge, flaeche)


def _versaetze(stuecke, w):
    """[Versatz] der Umläufe eines Zugs, von innen nach außen, der letzte 0: An einer Wand, die
    überhängt, steht nach dem Räumen von oben ein Keil davor – so dick, wie die Wand auf ihrer
    Länge nach außen geht (Länge · sin Neigung). Je Umlauf höchstens `w.quer` davon (Manuel,
    2026-10-25, seine tiefe Tasche: „an den kanten muss man halt anstellen ... solange bis mit
    dem schruppwerkzeug erstmal alles weg ist“)."""
    if w.quer <= 0.0:
        return [0.0]
    dicke = max(
        (
            st[4] * math.sqrt(max(0.0, 1.0 - st[1].z ** 2))
            for stueck in stuecke
            for st in stueck
            if st[2].z < -1e-6
        ),
        default=0.0,
    )
    anzahl = int(math.ceil(dicke / w.quer - 1e-9))
    return [k * w.quer for k in range(anzahl - 1, 0, -1)] + [0.0]


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
        versaetze = _versaetze(stuecke, w)
        umlauf_stuecke = {
            v: [[_versetzt(st, v, w) for st in s] for s in stuecke] for v in versaetze
        }
        # Erst für alle Stellen, Lagen und Umläufe, ob der Fräser dort geht – auf einmal, verteilt.
        gehen = iter(
            _gehen(
                form,
                [
                    (stelle, lage)
                    for lage in range(lagen)
                    for v in versaetze
                    for st in umlauf_stuecke[v]
                    for stelle in st
                ],
                hoehe,
                w,
            )
        )
        for lage, v in ((lage, v) for lage in range(lagen) for v in versaetze):
            w_v = replace(w, aufmass=w.aufmass + v)  # für _grenze: die Stellen dazwischen
            for stueck in umlauf_stuecke[v]:
                teile, aus = [], []
                davor = None  # (Stelle, geht) der Stelle davor
                for stelle in stueck:
                    geht = next(gehen)
                    if davor is not None and davor[1] != geht:
                        # Wo es von „geht“ auf „schneidet“ wechselt: die Grenze genauer.
                        grenze = _grenze(form, davor[0], stelle, davor[1], lage, hoehe, w_v)
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


def halter_pruefen(form, bahn, koerper, radius):
    """Anstoss oder None: Führen die Körper über der Schneide – `koerper` [(von, bis, Radius)],
    von und bis in mm längs der Achse ab der Spitze (Hals, Schaft, Halter) – an einer Stelle der
    Bahn im Vorschub ins Teil `form`? Es zählen nur die dicker als die Schneide (`radius`): Ein
    Schaft wie sie liegt an der Wand nur an, wie sie (halter_an_stellen)."""
    stellen = [p for p in bahn.punkte if not p.eilgang]
    if not stellen:
        return None
    spitzen = np.array([tuple(p.spitze) for p in stellen], dtype=float)
    achsen = np.array([tuple(p.achse) for p in stellen], dtype=float)
    return halter_an_stellen(form, spitzen, achsen, koerper, radius)


def dickere_koerper(koerper, radius):
    """Die Körper aus `koerper`, die dicker sind als die Schneide (`radius`) und Länge haben."""
    return [(a, b, r) for a, b, r in koerper if r > radius + 1e-3 and b - a > 1e-6]


def ausgewaehlt(spitzen, schritt=HALTER_SCHRITT):
    """Die Indizes der Stellen, etwa je `schritt` Weg eine – ein Halter ist breit, er steckt nie
    nur 0,2 mm im Teil (am Kegel 2400 Stellen in drei Lagen: 15 statt 2 s)."""
    if len(spitzen) < 2:
        return np.arange(len(spitzen))
    weg = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(spitzen, axis=0), axis=1))])
    marken = np.arange(0.0, weg[-1] + schritt, schritt)
    return np.unique(np.minimum(np.searchsorted(weg, marken), len(weg) - 1))


def stoesst_an(netz, spitzen, achsen, teile, weiter):
    """[bool] je Stelle: führt einer der Körper `teile` ins Teil (das Netz `netz`), um `weiter`
    (je Stelle) zur Spindel geschoben? Auch in einem Nebenrechner für ein Stück der Stellen."""
    reichweite = max(r for _a, _b, r in teile) + 1.0
    ergebnis = np.zeros(len(spitzen), dtype=bool)
    for anfang in range(0, len(spitzen), HALTER_JE_ABFRAGE):
        hier = slice(anfang, anfang + HALTER_JE_ABFRAGE)
        s, a, w = spitzen[hier], achsen[hier], weiter[hier]
        von = np.concatenate([s + (t[0] + w)[:, None] * a for t in teile])
        nach = np.concatenate([s + (t[1] + w)[:, None] * a for t in teile])
        radien = np.concatenate([np.full(len(s), t[2]) for t in teile])
        abstand = netz.kapseln(von, nach, reichweite, radien, np.ones(len(von), dtype=bool))
        ergebnis[hier] = (abstand.reshape(len(teile), -1) < -HALTER_TIEFER).any(axis=0)
    return ergebnis


def noetig_weiter(netz, spitzen, achsen, teile):
    """(Indizes der Stellen, die anstoßen, so viel weiter heraus wäre es je davon frei – mm):
    erst alle Stellen, dann für die anstoßenden eine Halbierung bis HALTER_LAENGER, auf 0,1 mm
    genau. Auch in einem Nebenrechner für ein Stück der Stellen."""
    alle = np.arange(len(spitzen))
    an = alle[stoesst_an(netz, spitzen, achsen, teile, np.zeros(len(alle)))]
    if not len(an):
        return an, np.zeros(0)
    unten, oben = np.zeros(len(an)), np.full(len(an), HALTER_LAENGER)
    for _ in range(12):  # auf 0,1 mm genau
        mitte = (unten + oben) / 2
        noch = stoesst_an(netz, spitzen[an], achsen[an], teile, mitte)
        unten = np.where(noch, mitte, unten)
        oben = np.where(noch, oben, mitte)
    return an, oben


def halter_an_stellen(form, spitzen, achsen, koerper, radius, netz=None):
    """Anstoss oder None für die Stellen (Spitzen und Werkzeugachsen zur Spindel, (n, 3)):
    etwa je HALTER_SCHRITT eine geprüft (ausgewaehlt), gerechnet mit dem Netz des Teils
    (netzabstand), je HALTER_JE_ABFRAGE Stellen auf einmal; `mindestens` aus einer Halbierung je
    anstoßender Stelle: um wie viel weiter oben die Körper frei wären (noetig_weiter)."""
    from . import netzabstand as na

    teile = dickere_koerper(koerper, radius)
    if not teile or not len(spitzen):
        return None
    if netz is None:
        netz = na.Netz(form, HALTER_NETZ)
    waehle = ausgewaehlt(spitzen)
    an, weiter = noetig_weiter(netz, spitzen[waehle], achsen[waehle], teile)
    if not len(an):
        return None
    heraus = min(a for a, _b, _r in teile)
    return Anstoss(len(an), heraus, heraus + float(weiter.max()))


def _lage(stelle, lage, hoehe):
    """(Spitze, Achse, Normale) der Stelle in der Lage `lage` (von oben gezählt)."""
    spitze, achse, normale, _fuss, laenge, _flaeche = stelle
    return (spitze + achse * max(0.0, laenge - (lage + 1) * hoehe), achse, normale)


def _geht(form, stelle, lage, hoehe, w):
    """Schneidet der Fräser an der Stelle in dieser Lage nirgends ins Teil?"""
    spitze, achse, _normale = _lage(stelle, lage, hoehe)
    return not _schneidet(form, spitze, achse, min(w.schneide, stelle[4] + 1.0), w.radius)


def _gehen(form, paare, hoehe, w):
    """[_geht] je (Stelle, Lage) aus `paare` – ab PARALLEL_AB auf den Nebenrechnern
    (geht_stueck), sonst oder wenn sie scheitern hier. Dieselbe Rechnung, dasselbe Ergebnis."""
    fragen = []
    for stelle, lage in paare:
        spitze, achse, _normale = _lage(stelle, lage, hoehe)
        fragen.append((tuple(spitze), tuple(achse), min(w.schneide, stelle[4] + 1.0)))
    if len(fragen) >= PARALLEL_AB:
        verteilt = _gehen_verteilt(form, fragen, w.radius)
        if verteilt is not None:
            return verteilt
    return geht_stueck(form, fragen, w.radius)


def _gehen_verteilt(form, fragen, radius):
    """geht_stueck in Stücken auf den Nebenrechnern – None ohne sie oder wenn sie scheitern."""
    import hashlib

    from . import nebenrechner as nr

    pool = nr.pool()
    if not pool.verfuegbar() or pool.anzahl < 2:
        return None
    bereiche = nr.stuecke(len(fragen), pool.anzahl, je_arbeiter=3, mindestens=STELLEN_JE_STUECK)
    if len(bereiche) < 2:
        return None
    try:
        brep = form.exportBrepToString()
        teil = pool.gemeinsam("fl-teil-" + hashlib.sha1(brep.encode()).hexdigest(), nr.Form(brep))
        auftraege = [
            pool.auftrag("flanke_bahn", "geht_stueck", teil, fragen[von:bis], radius)
            for von, bis in bereiche
        ]
        teile = pool.warten(auftraege, zwischendurch=nr.ereignisse_ohne_eingaben)
    except Exception as fehler:  # noqa: BLE001 – dann rechnet es hier, wie bisher
        FreeCAD.Console.PrintWarning(
            f"CAM-Addon: Flanke auf den Nebenrechnern gescheitert, rechne hier: {fehler}\n"
        )
        return None
    return [geht for teil_ in teile for geht in teil_]


def geht_stueck(form, fragen, radius):
    """Je (Spitze, Achse, Länge) aus `fragen` (Tupel): schneidet der Fräser dort nirgends ins Teil
    (_schneidet)? Auch im Nebenrechner für ein Stück davon."""
    v = FreeCAD.Vector
    return [not _schneidet(form, v(*s), v(*a), laenge, radius) for s, a, laenge in fragen]


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


def _weg(normale):
    """Wohin es zum An- und Abfahren von der Wand weg geht: die Normale – an einer überhängenden
    Wand (sie zeigt nach unten) waagerecht, sonst tauchte die gekippte Stirn vor der Wand in den
    Boden."""
    if normale.z >= 0.0:
        return normale
    waagerecht = FreeCAD.Vector(normale.x, normale.y, 0.0)
    return waagerecht.normalize() if waagerecht.Length > 1e-9 else normale


def _umlauf(teil, w):
    """[Stelle] – ein Umlauf mit An- und Abfahren."""
    ergebnis = []
    s0, a0, n0 = teil[0]
    frei = s0 + _weg(n0) * ABSTAND
    oben = w.oben + w.sicherheit
    for hoehe, eilgang in ((w.sicher, True), (oben, True)):
        lam = max(0.0, (hoehe - frei.z) / max(a0.z, 1e-6))
        ergebnis.append(Stelle(tuple(frei + a0 * lam), tuple(a0), eilgang=eilgang))
    ergebnis.append(Stelle(tuple(frei), tuple(a0), eintauchen=True))
    for s, a, _n in teil:
        ergebnis.append(Stelle(tuple(s), tuple(a)))
    s1, a1, n1 = teil[-1]
    weg = s1 + _weg(n1) * ABSTAND
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
