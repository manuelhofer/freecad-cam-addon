# SPDX-License-Identifier: LGPL-2.1-or-later
"""5 Achsen: die Wand unter dem Rand mit der Kugel schlichten (W-038; Manuel, 2026-10-25, seine
tiefe Tasche: „dann muss mit einem kurgelfräser die wand geschlichtet werden .. wie immer“).

Eine Tasche, deren Wände überhängen (unten weiter als oben), erreicht von oben kein senkrechter
Fräser: Der Rand steht über der Wand und über den Rundungen am Boden. Gekippt geht es:

- **Höhenlinien:** die gewählten Flächen (Wände, Rundungen) Schnitt für Schnitt in z, von oben
  nach unten. Der Abstand zweier Linien längs der Fläche kommt aus der Grathöhe (s = √(8 R h));
  wo die Fläche flacher wird (die Rundung am Boden), rücken sie in z dichter.
- **Die Kugel:** ihre Mitte um Radius und Aufmaß vor der Fläche (längs ihrer Normalen); jede
  Mitte wird gegen das ganze Teil geprüft (netzabstand – nichts darf näher als der Radius sein),
  wo nicht, fällt die Stelle weg.
- **Die Achse:** je Stelle so wenig gekippt, dass Schneide über der Kugel, Schaft und Halter
  um ihr Spiel vom ganzen Teil bleiben („ausweichkippen“, netzabstand.kapseln): an Stützstellen
  gesucht – erst von der Wand weg, dann zur Mitte der Tasche, dann dazwischen (in einer Ecke
  hängen zwei Wände über) –, dazwischen gemittelt und geglättet, dann jede Stelle nachgeprüft.
  Dann liegt nur die Kugel an der Wand, der Schaft steht durch die Öffnung hinaus. Viele Stellen
  rechnen die Nebenrechner.
- **Gleichlauf:** jede Linie so herum, dass das Material rechts liegt (M3).
- **Ein- und Ausfahren:** über der Mitte der Tasche hinab (sie ist nach dem Schruppen frei),
  quer an die erste Linie, von Linie zu Linie an der Wand hinab; am Ende quer zur Mitte und
  hinauf – die Achse dabei schon (noch) gekippt wie an der Wand, sie schwenkt nicht in der Tasche.

Die Punkte sind wie beim 3D-Schlichten die Spitze der senkrecht gedachten Kugel (Mitte − R · z);
dazu je Punkt die Werkzeugachse – die Maschine führt die Kugelmitte (simultan, mit dem Radius als
Bezug). Läuft ohne Oberfläche.
"""

import contextlib
import math
from dataclasses import dataclass, field

import FreeCAD
import numpy as np

from . import bahn as bn
from .sprache import tr

SCHRITT = 0.5  # mm – so dicht liegen die Punkte einer Linie
FLACH_MINDESTENS = 0.2  # so viel der Schrittweite rückt eine Linie in z mindestens tiefer
ABSTAND = 2.0  # mm – so weit vor der Wand beginnt und endet das Anfahren
SPIEL = 0.01  # mm – so viel näher als Radius + Aufmaß darf das Teil der Kugelmitte kommen
# mm – so genau wird das Teil für die Prüfung der Kugelmitten vernetzt. Feiner nicht: Mit 0,005
# gab Manuels tiefe Tasche (B-Spline-Wände) Millionen Dreiecke, und der Kernel beendete den Lauf
# (2026-10-25). Die Abweichung zieht netzabstand ab – die Prüfung bleibt auf der sicheren Seite.
NETZ_TOLERANZ = 0.02
JE_ABFRAGE = 2000  # so viele Kugelmitten fragt die Prüfung auf einmal
GRATHOEHE = 0.005  # mm – wenn nichts angegeben ist
HINTERSCHNITT = "hinterschnitt"  # die Richtung des 3D-Schlichtens dafür (schlichten3d.RICHTUNGEN)
VORSCHAU_SCHRITT = 1.0  # mm – so dicht liegen die Punkte einer Linie in der Vorschau
PROBEN_JE_FLAECHE = 4  # je Richtung so viele Stellen fragt ueberdeckt()
FLAECHEN_HOECHSTENS = 400  # mehr gewählte Flächen: ueberdeckte() fragt nicht (ein STL)
# Die Achse: je Stelle die kleinste Neigung, bei der Schneide über der Kugel, Schaft und Halter um
# ihr Spiel vom Teil bleiben (Manuels tiefe Tasche: in der Wandmitte 10°, in den Ecken hängen zwei
# Wände über – dort kippt sie schräg in die Ecke).
SPIEL_SCHAFT = 0.2  # mm – Schneide und Schaft (so dick wie die Kugel oder dünner)
SPIEL_HALTER = 1.0  # mm – was dicker ist als die Kugel
NEIGUNG_MAX = 40.0  # Grad
NEIGUNG_GROB = 8.0  # Grad – so grob sucht die Neigung zuerst
NEIGUNG_SCHRITT = 2.0  # Grad – dann so fein
STUETZ_ABSTAND = 3.0  # mm – so dicht längs eines Zugs wird die Neigung gesucht
GLAETTEN = 5.0  # mm – im Umkreis gilt die größte Neigung
JE_KAPSEL = 16  # so viele Stellen fragt frei_stueck auf einmal (nah beieinander)
VERTEILT_AB = 2000  # Stellen: ab so vielen rechnen die Nebenrechner
NOETIG_PROBEN = 40  # so viele anstoßende Stellen fragt _noetig_heraus
NOETIG_HALBIEREN = 8  # so oft halbiert es (HALTER_LAENGER / 256: auf 0,6 mm)
HALTER_LAENGER = 150.0  # mm – weiter heraus sucht _noetig_heraus nicht
HOEHEN_RASTER = 40  # je Fläche so viele Proben je Richtung für die Höhen (_hoehen)
SCHNITTE_VERTEILT_AB = 6  # Höhen: ab so vielen schneiden die Nebenrechner
GENAU_VERTEILT_AB = 100  # knappe Kugelmitten: ab so vielen fragen die Nebenrechner OpenCascade
GENAU_JE_STUECK = 25
STELLEN_JE_STUECK = 200


def ueberdeckt(form, name):
    """Liegt die Fläche `name` unter dem Rand – trifft von einer ihrer Stellen ein Strahl
    senkrecht nach oben das Teil? Dann kommt von oben kein senkrechter Fräser hin (eine Wand, die
    überhängt, die Rundung am Boden unter ihr)."""
    import Part

    try:
        flaeche = form.getElement(name)
    except Exception:  # noqa: BLE001 – keine Fläche dieses Namens
        return False
    if not hasattr(flaeche, "Surface"):
        return False
    oben = form.BoundBox.ZMax + 1.0
    vorzeichen = _richtung_zur_luft(form, flaeche)
    u0, u1, v0, v1 = flaeche.ParameterRange
    n = PROBEN_JE_FLAECHE
    for i in range(n):
        for j in range(n):
            u = u0 + (u1 - u0) * (i + 0.5) / n
            v = v0 + (v1 - v0) * (j + 0.5) / n
            p = flaeche.valueAt(u, v)
            if not flaeche.isInside(p, 1e-4, True):
                continue
            p = p + flaeche.normalAt(u, v) * (0.1 * vorzeichen)
            if p.z >= oben:
                continue
            try:
                strahl = Part.LineSegment(p, FreeCAD.Vector(p.x, p.y, oben)).toShape()
                if strahl.common(form).Length > 1e-6:
                    return True
            except Exception:  # noqa: BLE001 – OCC: lieber nicht überdeckt
                continue
    return False


def ueberdeckte(form, namen):
    """frozenset der Flächen aus `namen`, die unter dem Rand liegen (ueberdeckt) – gefragt nur die,
    die irgendwo überhängen (eine Normale zur Luft zeigt nach unten), und ihre Nachbarn (die
    Rundung am Boden unter einer überhängenden Wand zeigt nach oben). Leer bei mehr als
    FLAECHEN_HOECHSTENS Flächen (ein Teil aus einem STL mit Tausenden Dreiecken: dort schlichtet
    das 3D-Schlichten wie immer). Gemerkt je Form und Wahl – der Assistent fragt bei jeder
    Vorschau."""
    namen = tuple(n for n in namen if str(n).startswith("Face"))
    if not namen or len(namen) > FLAECHEN_HOECHSTENS:
        return frozenset()
    try:
        schluessel = (form.hashCode(), round(float(form.Volume), 3), namen)
    except Exception:  # noqa: BLE001 – keine Form, die sich merken lässt
        schluessel = None
    if schluessel is not None and schluessel in _UEBERDECKT:
        return _UEBERDECKT[schluessel]
    flaechen = {}
    for name in namen:
        with contextlib.suppress(Exception):
            flaeche = form.getElement(name)
            if hasattr(flaeche, "Surface"):
                flaechen[name] = flaeche
    haengen = set()
    for name, flaeche in flaechen.items():
        vorzeichen = _richtung_zur_luft(form, flaeche)
        u0, u1, v0, v1 = flaeche.ParameterRange
        for i in range(PROBEN_JE_FLAECHE + 1):
            for j in range(PROBEN_JE_FLAECHE + 1):
                with contextlib.suppress(Exception):
                    u = u0 + (u1 - u0) * i / PROBEN_JE_FLAECHE
                    v = v0 + (v1 - v0) * j / PROBEN_JE_FLAECHE
                    if flaeche.normalAt(u, v).z * vorzeichen < -0.01:
                        haengen.add(name)
    kanten = {n: {k.hashCode() for k in f.Edges} for n, f in flaechen.items()}
    nachbarn = {n for n in flaechen if any(kanten[n] & kanten[h] for h in haengen)}
    ergebnis = frozenset(n for n in sorted(haengen | nachbarn) if ueberdeckt(form, n))
    if schluessel is not None:
        if len(_UEBERDECKT) > 16:
            _UEBERDECKT.clear()
        _UEBERDECKT[schluessel] = ergebnis
    return ergebnis


_UEBERDECKT = {}  # (Form, Wahl) → ueberdeckte()


@dataclass
class Werte:
    """Was die Bahn braucht; Längen in mm, z nach oben im Job."""

    radius: float  # der Kugel
    sicher: float  # z für den Eilgang über allem
    grathoehe: float = GRATHOEHE
    aufmass: float = 0.0
    vorschub: float = 0.0  # mm/min – für die Zeit; 0: 1000
    eintauchen: float = 0.0
    schritt: float = SCHRITT
    gleichlauf: bool = True
    # Über der Schneide (flanke.koerper_ueber_der_schneide): [(von, bis, Radius)] ab der Spitze –
    # Hals, Schaft, Halter; leer: ein Schaft wie die Kugel. `schneide`: die Schneidenlänge.
    koerper: tuple = ()
    schneide: float = 0.0
    oben: float = None  # z der Oberkante des Rohteils – bis darüber im Eilgang; None: des Teils


@dataclass
class Bahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt]: die Spitze der senkrecht gedachten Kugel
    achsen: list  # je Punkt die Werkzeugachse (x, y, z), von der Spitze weg
    linien: int  # so viele Höhenlinien
    neigung: float  # Grad – so weit steht die Achse gekippt
    laenge: float  # mm im Vorschub
    zeit: float  # Minuten
    weggelassen: int = 0  # Stellen, an denen die Kugel ins Teil schnitte
    # Wie eine Schlichtbahn (schlichten3d_bahn) für den Assistenten und die Operation:
    zeilen: int = 0
    hoehenlinien: int = 0
    umlaeufe: int = 0
    laengs_x: bool = False
    spirale: bool = False
    hinterschnitt: bool = True
    abstand: float = 0.0  # mm – der Abstand der Linien längs der Fläche
    namen: list = field(default_factory=list)
    luecken: list = field(default_factory=list)  # die Kugelmitten (x, y, z), die wegfielen
    anstoesse: int = 0  # davon: Stellen, an denen Schaft oder Halter mit keiner Achse frei blieben
    # (heraus, mindestens) in mm, wenn etwas anstößt: so weit steht das Werkzeug heraus (bis zum
    # Halter), so weit müsste es, damit es überall ginge (None: auch HALTER_LAENGER mehr nicht).
    ausspannen: tuple = None


def _richtung_zur_luft(form, flaeche):
    """+1, wenn die Normale der Fläche (normalAt) zur Luft zeigt, sonst −1 – in ihrer Mitte
    nachgesehen (wie flanke_bahn._zum_teil)."""
    from . import flanke_bahn as fb

    return -1.0 if fb._zum_teil(form, flaeche) else 1.0


def _flaeche_der_kante(flaechen, kante):
    """(Fläche, Vorzeichen) aus `flaechen`, auf der die Kante eines Schnitts liegt – die nächste
    an ihrer Mitte; None, wenn keine nah genug ist."""
    mitte = kante.valueAt(kante.FirstParameter + 0.5 * (kante.LastParameter - kante.FirstParameter))
    beste = None
    for flaeche, vorzeichen in flaechen:
        kasten = FreeCAD.BoundBox(flaeche.BoundBox)
        kasten.enlarge(0.1)
        if not kasten.isInside(mitte):
            continue
        try:
            u, v = flaeche.Surface.parameter(mitte)
            d = (flaeche.Surface.value(u, v) - mitte).Length
        except Exception:  # noqa: BLE001 – OCC
            continue
        if d <= 0.05 and (beste is None or d < beste[0]):
            beste = (d, flaeche, vorzeichen)
    return None if beste is None else beste[1:]


def _schnitt(verbund, flaechen, z, schritt):
    """[[(Punkt, Normale zur Luft)]] – die Schnitte der Flächen mit der Ebene z, je Draht der
    Reihe nach; die Normale aus der Fläche, auf der die Kante des Schnitts liegt."""
    try:
        draehte = verbund.slice(FreeCAD.Vector(0, 0, 1), z)
    except Exception:  # noqa: BLE001 – OCC: kein Schnitt
        return []
    ergebnis = []
    for draht in draehte:
        stellen = []
        for kante in draht.OrderedEdges:
            fund = _flaeche_der_kante(flaechen, kante)
            if fund is None or kante.Length < 1e-6:
                continue
            flaeche, vorzeichen = fund
            anzahl = max(1, int(math.ceil(kante.Length / schritt)))
            punkte = kante.discretize(Number=anzahl + 1)
            if kante.Orientation == "Reversed":
                punkte = list(reversed(punkte))
            if (
                stellen
                and (stellen[-1][0] - punkte[0]).Length > (stellen[-1][0] - punkte[-1]).Length
            ):
                punkte = list(reversed(punkte))  # an das Ende davor anschließen
            for p in punkte if not stellen else punkte[1:]:
                try:
                    u, v = flaeche.Surface.parameter(p)
                    n = flaeche.normalAt(u, v) * vorzeichen
                except Exception:  # noqa: BLE001 – OCC
                    continue
                if n.Length > 1e-9:
                    stellen.append((p, FreeCAD.Vector(n).normalize()))
        if len(stellen) >= 2:
            ergebnis.append(stellen)
    return ergebnis


def planen(form, namen, w):
    """Die Bahn an den Flächen `namen` von `form` (Werte `w`). ValueError mit einem Satz, wenn es
    nicht geht."""
    import Part

    from . import netzabstand as na

    if w.radius <= 0:
        raise ValueError(tr("hs.fehler.kugel"))
    flaechen = _flaechen(form, namen)
    if not flaechen:
        raise ValueError(tr("hs.fehler.keine"))
    bb = Part.makeCompound([f for f, _v, _n in flaechen]).BoundBox
    mitte = FreeCAD.Vector(bb.Center.x, bb.Center.y, 0.0)
    abstand = math.sqrt(8.0 * w.radius * max(w.grathoehe, 1e-4))
    abstand = min(abstand, w.radius)
    halb = w.radius + max(w.aufmass, 0.0)
    # Weiter als eine Zelle sieht das Netz nicht: die Zelle größer als die Kugel.
    netz = na.Netz(form, toleranz=NETZ_TOLERANZ, zelle=halb + 1.0)
    linien = []  # [[[(Mitte, Normale)]]] – je Höhe die Ringe
    namen = [n for _f, _v, n in flaechen]
    for je_hoehe in _verteilt_schneiden(form, namen, _hoehen(flaechen, bb, abstand), w.schritt):
        ringe = [
            [(FreeCAD.Vector(*(p + n * halb)), FreeCAD.Vector(*n)) for p, n in zip(*r, strict=True)]
            for r in je_hoehe
        ]
        if ringe:
            linien.append(ringe)
    linien = _ohne_doppelte(linien, abstand)
    if not linien:
        raise ValueError(tr("hs.fehler.nichts"))

    # Die Kugelmitten gegen das ganze Teil: nichts näher als Radius + Aufmaß. Das Netz sagt, wie
    # weit mindestens; knapp darunter (die Kugel liegt an, das Netz schätzt um seine Sehnen zu
    # kurz) fragt die echte Form nach.
    alle = np.array([[c.x, c.y, c.z] for ringe in linien for ring in ringe for c, _n in ring])
    mindestens = np.concatenate(
        [netz.abstand(alle[i : i + JE_ABFRAGE]) for i in range(0, len(alle), JE_ABFRAGE)]
    )
    frei = mindestens >= halb - SPIEL - NETZ_TOLERANZ
    knapp = np.flatnonzero(~frei & (mindestens >= halb - SPIEL - 3.0 * NETZ_TOLERANZ))
    if len(knapp):
        frei[knapp] = _in_stuecken(
            form, netz, "genau", (alle[knapp],), (halb - SPIEL,), VERTEILT_AB // 4
        )
    k = 0
    luecken = []
    stuecke = []  # [[(Mitte, Normale)]] – an weggelassenen Stellen geteilt
    for ringe in linien:
        for ring in ringe:
            stueck = []
            for c, n in ring:
                if frei[k]:
                    stueck.append((c, n))
                else:
                    luecken.append((c.x, c.y, c.z))
                    if len(stueck) >= 2:
                        stuecke.append(stueck)
                    stueck = []
                k += 1
            if len(stueck) >= 2:
                stuecke.append(stueck)
    if not stuecke:
        raise ValueError(tr("hs.fehler.nichts"))

    # Die Achse je Stelle: so wenig gekippt, dass Schaft und Halter frei bleiben (_achsen).
    # Ganz lang: Wie weit ein Körper unter die Oberkante des Teils reicht, rechnet frei_stueck je
    # Stelle – gekippt taucht auch ein Bund weit oben am Halter darunter.
    teile = _koerper(w, 1e6)
    zuege, anstoesse = _achsen(form, netz, stuecke, teile, w, mitte)
    zuege = [_gerichtet(z, w.gleichlauf) for z in zuege]
    punkte, achsen, weg = _verbinden(zuege, w, netz, halb) if zuege else ([], [], [])
    anstoesse += weg
    luecken += anstoesse
    ausspannen = _noetig_heraus(form, netz, anstoesse, teile, w, mitte) if anstoesse else None
    if not punkte:
        if ausspannen is not None and ausspannen[1] is not None:
            fehler = ValueError(
                tr(
                    "hs.fehler.anstoss_mindestens",
                    heraus=f"{ausspannen[0]:.0f}",
                    mindestens=f"{math.ceil(ausspannen[1]):.0f}",
                )
            )
            fehler.daten = {"ausspannen": ausspannen}  # „T3 auf … mm ausspannen“ im Assistenten
            raise fehler
        raise ValueError(tr("hs.fehler.anstoss"))
    laenge = sum(
        math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))
        for a, b in zip(punkte, punkte[1:], strict=False)
        if not b.eilgang
    )
    vorschub = w.vorschub or 1000.0
    zeit = bn.zeit(punkte, vorschub, w.eintauchen or None)
    neigung = max(math.degrees(math.acos(max(-1.0, min(1.0, a[2])))) for a in achsen)
    return Bahn(
        punkte=punkte,
        achsen=achsen,
        linien=len(linien),
        neigung=neigung,
        laenge=laenge,
        zeit=zeit,
        weggelassen=len(luecken),
        abstand=abstand,
        namen=[n for _f, _v, n in flaechen],
        luecken=luecken,
        hoehenlinien=len(linien),
        umlaeufe=len(linien),
        anstoesse=len(anstoesse),
        ausspannen=ausspannen,
    )


def _flaechen(form, namen):
    """[(Fläche, Vorzeichen zur Luft, Name)] der Flächen `namen` von `form`, die es gibt."""
    flaechen = []
    for name in namen:
        try:
            flaeche = form.getElement(name)
        except Exception:  # noqa: BLE001 – keine Fläche dieses Namens
            continue
        if hasattr(flaeche, "Surface"):
            flaechen.append((flaeche, _richtung_zur_luft(form, flaeche), name))
    return flaechen


def _hoehen(flaechen, bb, abstand):
    """[z] der Höhenlinien von oben nach unten: je Linie um den Abstand längs der Fläche tiefer –
    in z um so viel weniger, wie die Flächen dort flach liegen (FLACH_MINDESTENS). Wie flach, aus
    einem Raster je Fläche (HOEHEN_RASTER²) um die Höhe herum: So stehen alle Höhen vorher fest,
    und die Schnitte rechnen die Nebenrechner."""
    proben = []  # (z, waagerechter Anteil der Normalen)
    for flaeche, _v, _n in flaechen:
        u0, u1, v0, v1 = flaeche.ParameterRange
        for i in range(HOEHEN_RASTER + 1):
            for j in range(HOEHEN_RASTER + 1):
                u = u0 + (u1 - u0) * i / HOEHEN_RASTER
                v = v0 + (v1 - v0) * j / HOEHEN_RASTER
                try:
                    p = flaeche.valueAt(u, v)
                    n = flaeche.normalAt(u, v)
                except Exception:  # noqa: BLE001 – OCC
                    continue
                if n.Length > 1e-9:
                    proben.append((p.z, math.sqrt(max(0.0, 1.0 - (n.z / n.Length) ** 2))))
    proben = np.array(proben) if proben else np.zeros((0, 2))
    hoehen, z = [], bb.ZMax - 0.05
    while z > bb.ZMin + 0.02:
        hoehen.append(z)
        nah = proben[np.abs(proben[:, 0] - z) <= abstand, 1] if len(proben) else []
        flach = float(np.min(nah)) if len(nah) else 1.0
        z -= abstand * max(flach, FLACH_MINDESTENS)
    return hoehen


_FLAECHEN = {}  # im Nebenrechner: (id der Form, Namen) → (Form, Flächen mit Vorzeichen, Verbund)


def schneiden_stueck(form, namen, hoehen, schritt):
    """Je Höhe die Ringe der Schnitte [(Punkte (k, 3), Normalen zur Luft (k, 3))] (_schnitt) –
    auch im Nebenrechner für ein Stück der Höhen (die Flächen je Form einmal)."""
    import Part

    from . import uhren

    schluessel = (id(form), tuple(namen))
    gemerkt = _FLAECHEN.get(schluessel)
    if gemerkt is None or gemerkt[0] is not form:
        _FLAECHEN.clear()
        flaechen = _flaechen(form, namen)
        gemerkt = (form, flaechen, Part.makeCompound([f for f, _v, _n in flaechen]))
        _FLAECHEN[schluessel] = gemerkt
    _form, flaechen, verbund = gemerkt
    paare = [(f, v) for f, v, _n in flaechen]
    ergebnis = []
    for z in hoehen:
        uhren.atmen()
        ringe = []
        for schnitt in _schnitt(verbund, paare, z, schritt):
            punkte = np.array([[p.x, p.y, p.z] for p, _n in schnitt])
            normalen = np.array([[n.x, n.y, n.z] for _p, n in schnitt])
            ringe.append((punkte, normalen))
        ergebnis.append(ringe)
    return ergebnis


def _verteilt_schneiden(form, namen, hoehen, schritt):
    """schneiden_stueck über alle Höhen – ab SCHNITTE_VERTEILT_AB Höhen auf den Nebenrechnern, in
    Stücken der Reihe nach; sonst oder wenn sie scheitern hier."""
    import hashlib

    from . import nebenrechner as nr

    try:
        pool = nr.pool()
        if len(hoehen) < SCHNITTE_VERTEILT_AB or not pool.verfuegbar() or pool.anzahl < 2:
            raise nr.NichtVerfuegbar("hier")
        bereiche = nr.stuecke(len(hoehen), pool.anzahl, je_arbeiter=2, mindestens=2)
        brep = form.exportBrepToString()
        teil = pool.gemeinsam("hs-teil-" + hashlib.sha1(brep.encode()).hexdigest(), nr.Form(brep))
        auftraege = [
            pool.auftrag(
                "hinterschnitt_bahn", "schneiden_stueck", teil, list(namen), hoehen[a:b], schritt
            )
            for a, b in bereiche
        ]
        teile = pool.warten(auftraege, zwischendurch=nr.ereignisse_ohne_eingaben)
        return [je_hoehe for teil_ in teile for je_hoehe in teil_]
    except Exception as fehler:  # noqa: BLE001 – dann rechnet es hier, wie bisher
        if not isinstance(fehler, nr.NichtVerfuegbar):
            FreeCAD.Console.PrintWarning(
                f"CAM-Addon: Wand unter dem Rand auf den Nebenrechnern gescheitert: {fehler}\n"
            )
        return schneiden_stueck(form, namen, hoehen, schritt)


def genau_stueck(form, mitten, mindestens):
    """(n,) bool: Liegt jede Kugelmitte mindestens `mindestens` vom Teil (genau, OpenCascade)? Für
    die knappen, bei denen das Netz zu kurz schätzt – auch im Nebenrechner für ein Stück davon."""
    import Part

    from . import uhren

    ergebnis = np.zeros(len(mitten), dtype=bool)
    for i, m in enumerate(np.asarray(mitten, dtype=float).reshape(-1, 3)):
        uhren.atmen()
        with contextlib.suppress(Exception):  # OCC: lieber weglassen
            ergebnis[i] = form.distToShape(Part.Vertex(FreeCAD.Vector(*m)))[0] >= mindestens
    return ergebnis


def genau_stueck_form(form, _toleranz, _zelle, mitten, mindestens):
    """genau_stueck für _verteilt (dort mit Toleranz und Zelle des Netzes)."""
    return genau_stueck(form, mitten, mindestens)


def _noetig_heraus(form, netz, anstoesse, teile, w, mitte):
    """(heraus, mindestens) – wie weit das Werkzeug bis zum Halter heraussteht und wie weit es
    müsste, damit an den Stellen `anstoesse` (Kugelmitten; NOETIG_PROBEN davon) eine Achse frei
    bliebe: Halter um so viel höher, der Schaft darunter so viel länger, halbiert bis HALTER_LAENGER
    (mindestens None: auch so nicht). None ohne Halter (nichts dicker als die Kugel)."""
    dick = [t for t in teile if t[2] > w.radius + 1e-3]
    if not dick:
        return None
    heraus = min(t[0] for t in dick)
    alle = np.asarray(anstoesse, dtype=float).reshape(-1, 3)
    wahl = np.unique(np.linspace(0, len(alle) - 1, min(len(alle), NOETIG_PROBEN)).astype(int))
    mitten = alle[wahl]
    richtungen = _richtungen(mitten, np.zeros_like(mitten), mitte)
    start = np.zeros(len(mitten))

    def geht(mehr):
        laenger = [
            (
                (v, b + mehr if b >= heraus - 1e-6 else b, r, sp)
                if r <= w.radius + 1e-3
                else (v + mehr, b + mehr, r, sp)
            )
            for v, b, r, sp in teile
        ]
        kipp = _in_stuecken(
            form, netz, "suchen", (mitten, richtungen, start), (laenger, w.radius), 0
        )
        return not np.isnan(kipp[:, 0]).any()

    if not geht(HALTER_LAENGER):
        return heraus, None
    unten, oben = 0.0, HALTER_LAENGER
    for _ in range(NOETIG_HALBIEREN):
        mitte_ = (unten + oben) / 2
        if geht(mitte_):
            oben = mitte_
        else:
            unten = mitte_
    return heraus, heraus + oben


def _ohne_doppelte(linien, abstand):
    """Die Höhen ohne die, deren Kugelmitten alle schon eine Höhe davor fuhr (bis auf ein Zehntel
    des Abstands): In einer Rundung mit dem Radius der Kugel liegt die Kugel in jeder Höhe gleich –
    an Manuels tiefer Tasche 13 Höhen, ein Weg."""
    ergebnis, davor = [], None
    for ringe in linien:
        mitten = np.array([[c.x, c.y, c.z] for ring in ringe for c, _n in ring])
        if davor is not None and _alle_nah(mitten, davor, 0.1 * abstand):
            continue
        ergebnis.append(ringe)
        davor = mitten
    return ergebnis


def _alle_nah(punkte, andere, weite):
    """Liegt jeder Punkt (n, 3) näher als `weite` an einem der anderen (m, 3)?"""
    for i in range(0, len(punkte), 256):
        d = np.linalg.norm(punkte[i : i + 256, None, :] - andere[None, :, :], axis=2)
        if (d.min(axis=1) > weite).any():
            return False
    return True


def _koerper(w, laenge):
    """[(von, bis, Radius, Spiel)] längs der Achse ab der Spitze: die Schneide über der Kugel (ab
    1,5 R – darunter liegt die Kugel selbst an), dann was `w.koerper` darüber nennt (Hals, Schaft,
    Halter; ohne: ein Schaft wie die Kugel), nichts weiter als `laenge` (darüber steht nichts)."""
    r = w.radius
    unten = 1.5 * r
    teile = []
    if w.koerper:
        schneide = max(float(w.schneide or 0.0), unten)
        if schneide > unten:
            teile.append((unten, min(schneide, laenge), r, SPIEL_SCHAFT))
        for von, bis, radius in w.koerper:
            von, bis = max(float(von), unten), min(float(bis), laenge)
            if bis > von + 1e-6 and radius > 0:
                spiel = SPIEL_HALTER if radius > r + 1e-3 else SPIEL_SCHAFT
                teile.append((von, bis, float(radius), spiel))
    if not teile:
        teile.append((unten, max(laenge, unten + 1.0), r, SPIEL_SCHAFT))
    return teile


def frei_stueck(netz, spitzen, achsen, teile):
    """(n,) bool: Bleiben die Körper `teile` [(von, bis, Radius, Spiel)] an den Stellen (Spitzen
    und Achsen zur Spindel, (n, 3)) um ihr Spiel vom Teil (das Netz `netz`, netzabstand)? Je
    Körper für sich (die Suchweite nach seinem Radius) und nur so weit, wie er unter die Oberkante
    des Teils reicht – darüber stößt nichts an; je JE_KAPSEL Stellen auf einmal (nah beieinander,
    längs eines Zugs)."""
    spitzen = np.asarray(spitzen, dtype=float).reshape(-1, 3)
    achsen = np.asarray(achsen, dtype=float).reshape(-1, 3)
    n = len(spitzen)
    ergebnis = np.ones(n, dtype=bool)
    if n == 0 or not len(netz.ecken):
        return ergebnis
    oben = getattr(netz, "hs_oben", None)
    if oben is None:
        oben = netz.hs_oben = float(netz.ecken[..., 2].max())
    sinus = np.sqrt(np.clip(1.0 - achsen[:, 2] ** 2, 0.0, 1.0))
    for von, bis, radius, spiel in teile:
        # So weit längs der Achse reicht der Körper unter die Oberkante (plus Spiel).
        bis_hier = np.minimum(
            bis, (oben + spiel + radius * sinus - spitzen[:, 2]) / np.maximum(achsen[:, 2], 1e-3)
        )
        offen = np.flatnonzero((bis_hier > von + 1e-6) & ergebnis)
        reichweite = radius + spiel + 0.5
        for anfang in range(0, len(offen), JE_KAPSEL):
            k = offen[anfang : anfang + JE_KAPSEL]
            d = netz.kapseln(
                spitzen[k] + von * achsen[k],
                spitzen[k] + bis_hier[k, None] * achsen[k],
                reichweite,
                np.full(len(k), radius),
                np.ones(len(k), dtype=bool),
            )
            ergebnis[k[d < spiel]] = False
    return ergebnis


def _achse(kipp):
    """Die Achse (n, 3) zu Kippvektoren (n, 2) in Grad: Richtung und Neigung."""
    kipp = np.asarray(kipp, dtype=float).reshape(-1, 2)
    t = np.radians(np.linalg.norm(kipp, axis=1))
    richtung = kipp / np.maximum(np.linalg.norm(kipp, axis=1), 1e-12)[:, None]
    return np.column_stack([np.sin(t)[:, None] * richtung, np.cos(t)])


def suchen_stueck(netz, mitten, richtungen, start, teile, radius):
    """Je Stelle (Kugelmitte (n, 3), Richtungen (n, k, 2) der Reihe nach, kleinste Neigung (n,))
    der Kippvektor (Grad, (n, 2)) mit der kleinsten Neigung bis NEIGUNG_MAX, bei der die Körper
    frei bleiben (frei_stueck): erst in Schritten von NEIGUNG_GROB (je Neigung die Richtungen der
    Reihe nach), dann zwischen der letzten, die anstieß, und der ersten freien in
    NEIGUNG_SCHRITT; nan, wo keine geht."""
    mitten = np.asarray(mitten, dtype=float).reshape(-1, 3)
    richtungen = np.asarray(richtungen, dtype=float).reshape(len(mitten), -1, 2)
    start = np.asarray(start, dtype=float).reshape(-1)
    n = len(mitten)
    ergebnis = np.full((n, 2), np.nan)
    neigung = np.full(n, np.nan)
    welche = np.zeros(n, dtype=int)

    def versuchen(hier, t, j):
        kipp = richtungen[hier, j] * t[:, None]
        achsen = _achse(kipp)
        achsen[t <= 1e-9] = (0.0, 0.0, 1.0)
        return frei_stueck(netz, mitten[hier] - radius * achsen, achsen, teile), kipp

    offen = np.arange(n)
    stufen = np.arange(0.0, NEIGUNG_MAX + 1e-9, NEIGUNG_GROB)
    for nummer, t in enumerate(stufen):
        if not len(offen):
            break
        unten = stufen[nummer + 1] if nummer + 1 < len(stufen) else t
        hier = offen[start[offen] < unten - 1e-9] if nummer + 1 < len(stufen) else offen
        t_hier = np.maximum(np.full(len(hier), t), start[hier])
        for j in range(richtungen.shape[1]):
            if not len(hier):
                break
            ok, kipp = versuchen(hier, t_hier, j)
            ergebnis[hier[ok]], neigung[hier[ok]], welche[hier[ok]] = kipp[ok], t_hier[ok], j
            hier, t_hier = hier[~ok], t_hier[~ok]
        offen = offen[np.isnan(neigung[offen])]
    # Fein: in derselben Richtung von der Stufe davor her, die erste freie.
    gefunden = np.flatnonzero(~np.isnan(neigung))
    unten = np.maximum(neigung[gefunden] - NEIGUNG_GROB, start[gefunden])
    for t0 in np.arange(NEIGUNG_SCHRITT, NEIGUNG_GROB - 1e-9, NEIGUNG_SCHRITT):
        hier_t = unten + t0
        kleiner = hier_t < neigung[gefunden] - 1e-9
        hier = gefunden[kleiner]
        if not len(hier):
            continue
        kipp = richtungen[hier, welche[hier]] * hier_t[kleiner][:, None]
        achsen = _achse(kipp)
        ok = frei_stueck(netz, mitten[hier] - radius * achsen, achsen, teile)
        ergebnis[hier[ok]] = kipp[ok]
        neigung[hier[ok]] = hier_t[kleiner][ok]
        gefunden_neu = np.ones(len(gefunden), dtype=bool)
        gefunden_neu[np.isin(gefunden, hier[ok])] = False
        gefunden, unten = gefunden[gefunden_neu], unten[gefunden_neu]
    return ergebnis


def frei_stueck_form(form, toleranz, zelle, spitzen, achsen, teile):
    """frei_stueck mit dem Netz von `form` – im Nebenrechner (das Netz je Form einmal)."""
    return frei_stueck(_netz_von(form, toleranz, zelle), spitzen, achsen, teile)


def suchen_stueck_form(form, toleranz, zelle, mitten, richtungen, start, teile, radius):
    """suchen_stueck mit dem Netz von `form` – im Nebenrechner (das Netz je Form einmal)."""
    return suchen_stueck(_netz_von(form, toleranz, zelle), mitten, richtungen, start, teile, radius)


_NETZE = {}  # im Nebenrechner: (id der Form, Toleranz, Zelle) → (Form, Netz)


def _netz_von(form, toleranz, zelle):
    from . import netzabstand as na

    schluessel = (id(form), float(toleranz), float(zelle))
    gemerkt = _NETZE.get(schluessel)
    if gemerkt is None or gemerkt[0] is not form:
        _NETZE.clear()  # eine Form zur Zeit – eine neue ersetzt die alte
        gemerkt = (form, na.Netz(form, toleranz=toleranz, zelle=zelle))
        _NETZE[schluessel] = gemerkt
    return gemerkt[1]


def _verteilt(form, netz, funktion, stuecke_args, mindestens):
    """[Ergebnis je Stück] – die Stücke (Argumente nach dem Netz) auf den Nebenrechnern, wenn es
    mindestens `mindestens` Stellen sind und es sie gibt; sonst oder wenn sie scheitern hier."""
    import hashlib

    from . import nebenrechner as nr

    lokal = {
        "frei": frei_stueck,
        "suchen": suchen_stueck,
        "genau": lambda _netz, *a: genau_stueck(form, *a),
    }[funktion]
    anzahl = sum(len(a[0]) for a in stuecke_args)
    try:
        pool = nr.pool()
        if anzahl < mindestens or not pool.verfuegbar() or pool.anzahl < 2:
            raise nr.NichtVerfuegbar("hier")
        brep = form.exportBrepToString()
        teil = pool.gemeinsam("hs-teil-" + hashlib.sha1(brep.encode()).hexdigest(), nr.Form(brep))
        auftraege = [
            pool.auftrag(
                "hinterschnitt_bahn",
                funktion + "_stueck_form",
                teil,
                netz.toleranz,
                netz.zelle,
                *args,
            )
            for args in stuecke_args
        ]
        return pool.warten(auftraege, zwischendurch=nr.ereignisse_ohne_eingaben)
    except Exception as fehler:  # noqa: BLE001 – dann rechnet es hier, wie bisher
        if not isinstance(fehler, nr.NichtVerfuegbar):
            FreeCAD.Console.PrintWarning(
                f"CAM-Addon: Wand unter dem Rand auf den Nebenrechnern gescheitert: {fehler}\n"
            )
        return [lokal(netz, *args) for args in stuecke_args]


def _in_stuecken(form, netz, funktion, felder, weiter, mindestens=VERTEILT_AB):
    """funktion (frei/suchen/genau) über die Felder (je (n, …), zusammen geschnitten) in Stücken für die
    Nebenrechner, die Ergebnisse wieder aneinander."""
    from . import nebenrechner as nr

    n = len(felder[0])
    if n == 0:
        return np.zeros((0, 2)) if funktion == "suchen" else np.zeros(0, dtype=bool)
    if funktion == "genau":
        mindestens = min(mindestens, GENAU_VERTEILT_AB)
    try:
        groesse = nr.pool().anzahl if n >= mindestens else 1
    except Exception:  # noqa: BLE001
        groesse = 1
    je_stueck = GENAU_JE_STUECK if funktion == "genau" else STELLEN_JE_STUECK
    bereiche = nr.stuecke(n, max(1, groesse), je_arbeiter=3, mindestens=je_stueck)
    args = [tuple(f[a:b] for f in felder) + tuple(weiter) for a, b in bereiche]
    teile = _verteilt(form, netz, funktion, args, mindestens)
    return np.concatenate([np.asarray(t) for t in teile])


def _richtungen(mitten, normalen, mitte):
    """(n, 3, 2): je Stelle die Richtungen, in die die Achse kippen darf, der Reihe nach – von der
    Wand weg (die Normale, waagerecht), zur Mitte der Tasche, dazwischen."""
    weg = normalen[:, :2].copy()
    zur_mitte = np.array([mitte.x, mitte.y]) - mitten[:, :2]
    for v in (weg, zur_mitte):
        laenge = np.linalg.norm(v, axis=1)
        v /= np.where(laenge > 1e-9, laenge, 1.0)[:, None]
    leer = np.linalg.norm(weg, axis=1) < 0.5
    weg[leer] = zur_mitte[leer]
    zwischen = weg + zur_mitte
    laenge = np.linalg.norm(zwischen, axis=1)
    zwischen = np.where(laenge[:, None] > 1e-6, zwischen / np.maximum(laenge, 1e-9)[:, None], weg)
    return np.stack([weg, zur_mitte, zwischen], axis=1)


def _achsen(form, netz, stuecke, teile, w, mitte):
    """([[(Mitte, Achse, Normale)]], [weggelassene Kugelmitten]) – je Stück an Stützstellen (etwa
    je STUETZ_ABSTAND) die kleinste Neigung, bei der Schaft und Halter frei bleiben (suchen_stueck),
    dazwischen gemittelt, je Stelle die größte Neigung im Umkreis GLAETTEN; dann jede Stelle
    nachgeprüft, wo nicht frei noch einmal gesucht – geht auch das nicht, fällt sie weg."""
    v = FreeCAD.Vector
    mitten = [np.array([[c.x, c.y, c.z] for c, _n in s]) for s in stuecke]
    normalen = [np.array([[n.x, n.y, n.z] for _c, n in s]) for s in stuecke]
    wege = [
        np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(m, axis=0), axis=1))])
        for m in mitten
    ]
    stuetzen = []
    for weg in wege:
        marken = np.arange(0.0, weg[-1] + STUETZ_ABSTAND, STUETZ_ABSTAND)
        wahl = np.unique(np.minimum(np.searchsorted(weg, marken), len(weg) - 1))
        stuetzen.append(np.unique(np.concatenate([wahl, [len(weg) - 1]])))
    s_mitten = np.concatenate([m[i] for m, i in zip(mitten, stuetzen, strict=True)])
    s_normalen = np.concatenate([n[i] for n, i in zip(normalen, stuetzen, strict=True)])
    # Unter einer überhängenden Fläche kippt die Achse mindestens so weit wie sie: erst ab da.
    start = (
        np.floor(np.degrees(np.arcsin(np.clip(-s_normalen[:, 2], 0.0, 1.0))) / NEIGUNG_SCHRITT)
        * NEIGUNG_SCHRITT
    )
    richtungen = _richtungen(s_mitten, s_normalen, mitte)
    kipp = _in_stuecken(
        form, netz, "suchen", (s_mitten, richtungen, start), (teile, w.radius), VERTEILT_AB // 4
    )
    zuege, weg_damit = [], []
    k = 0
    for m, n, weg, wahl in zip(mitten, normalen, wege, stuetzen, strict=True):
        s_kipp = kipp[k : k + len(wahl)]
        k += len(wahl)
        gut = ~np.isnan(s_kipp[:, 0])
        if not gut.any():
            weg_damit.extend(tuple(p) for p in m)
            continue
        s_weg, s_kipp = weg[wahl][gut], s_kipp[gut]
        # Die Neigung je Stützstelle: die größte im Umkreis – die Achse kippt rechtzeitig.
        t = np.linalg.norm(s_kipp, axis=1)
        t_umkreis = np.array([t[np.abs(s_weg - x) <= GLAETTEN].max() for x in s_weg])
        richtung = s_kipp / np.maximum(t, 1e-9)[:, None]
        richtung[t < 1e-9] = 0.0
        stelle_kipp = np.column_stack(
            [np.interp(weg, s_weg, richtung[:, 0]), np.interp(weg, s_weg, richtung[:, 1])]
        )
        laenge = np.linalg.norm(stelle_kipp, axis=1)
        stelle_t = np.interp(weg, s_weg, t_umkreis)
        stelle_kipp = (
            np.where(laenge[:, None] > 1e-9, stelle_kipp / np.maximum(laenge, 1e-9)[:, None], 0.0)
            * stelle_t[:, None]
        )
        zuege.append([m, n, stelle_kipp])
    # Jede Stelle nachgeprüft; wo nicht frei, noch einmal gesucht (ab der Neigung dort).
    alle_m = np.concatenate([z[0] for z in zuege]) if zuege else np.zeros((0, 3))
    alle_k = np.concatenate([z[2] for z in zuege]) if zuege else np.zeros((0, 2))
    achsen = _achse(alle_k)
    ok = _in_stuecken(form, netz, "frei", (alle_m - w.radius * achsen, achsen), (teile,))
    nochmal = np.flatnonzero(~ok)
    if len(nochmal):
        alle_n = np.concatenate([z[1] for z in zuege])
        neu = _in_stuecken(
            form,
            netz,
            "suchen",
            (
                alle_m[nochmal],
                _richtungen(alle_m[nochmal], alle_n[nochmal], mitte),
                np.linalg.norm(alle_k[nochmal], axis=1),
            ),
            (teile, w.radius),
            VERTEILT_AB // 4,
        )
        geht = ~np.isnan(neu[:, 0])
        alle_k[nochmal[geht]] = neu[geht]
        ok[nochmal[geht]] = True
        achsen = _achse(alle_k)
    ergebnis = []
    k = 0
    for m, n, _kipp in zuege:
        stueck = []
        for i in range(len(m)):
            if ok[k + i]:
                stueck.append((v(*m[i]), v(*achsen[k + i]), v(*n[i])))
            else:
                weg_damit.append(tuple(m[i]))
                if len(stueck) >= 2:
                    ergebnis.append(stueck)
                stueck = []
        if len(stueck) >= 2:
            ergebnis.append(stueck)
        k += len(m)
    return ergebnis, weg_damit


def _gerichtet(stueck, gleichlauf):
    """Das Stück so herum, dass das Material rechts der Fahrtrichtung liegt (Gleichlauf, M3)."""
    rechts = 0.0
    for (c0, _a0, n0), (c1, _a1, _n1) in zip(stueck, stueck[1:], strict=False):
        t = c1 - c0
        rechts += -t.y * n0.x + t.x * n0.y  # (t × z) · (−n): das Material rechts
    if (rechts > 0) != gleichlauf:
        return list(reversed(stueck))
    return stueck


def _verbinden(zuege, w, netz, halb):
    """([bahn.Punkt], [Achse], [weggelassene Kugelmitten]) – die Züge der Reihe nach, von Zug zu
    Zug (geschlossene Linien am nächsten Punkt begonnen) auf der Geraden, wenn Kugel, Schaft und
    Halter dort frei bleiben (_gerade_frei). Sonst und am Anfang und Ende längs der Achse hinaus
    auf die Sicherheitshöhe und hinein (_zugang): So bleiben Schaft und Halter, wo sie an der Wand
    frei waren – über die Mitte der Tasche stieße eine stark gekippte Achse drüben an den Rand.
    Die Punkte sind die Spitze der senkrecht gedachten Kugel."""
    punkte, achsen, weg = [], [], []

    def dazu(c, a, eilgang=False, eintauchen=False):
        spitze = c - FreeCAD.Vector(0, 0, w.radius)
        punkte.append(bn.Punkt(eilgang, spitze.x, spitze.y, spitze.z, eintauchen))
        achsen.append((a.x, a.y, a.z))

    def geschlossen(zug):
        return (zug[0][0] - zug[-1][0]).Length <= 2.0 * w.schritt

    def verlassen(zug):
        """Vom Ende des Zugs hinaus – geht es dort nicht, den Zug zurück und von seinem Anfang."""
        stelle = zug[-1]
        zugang = _zugang(netz, stelle, w, halb, teile)
        if zugang is None:
            for c, a, _n in reversed(zug[:-1]):
                dazu(c, a)
            stelle = zug[0]
            zugang = _zugang(netz, stelle, w, halb, teile)
        c, a, _n = stelle
        if zugang is None:
            hoch = c + a * ((w.sicher + w.radius - c.z) / max(a.z, 0.2))
            zugang = (c, c + a * ABSTAND, _ueber(netz, c, a, w), hoch)
        vor, knapp, ueber, hoch = zugang
        if vor is not c:
            dazu(vor, a)
        dazu(knapp, a)
        if ueber is not None:
            dazu(ueber, a)
        dazu(hoch, a, eilgang=True)

    teile = _koerper(w, 1e6)
    davor = None  # der Zug davor
    for zug in zuege:
        ende = davor[-1] if davor is not None else None
        if ende is not None and geschlossen(zug):
            k = min(range(len(zug)), key=lambda i: (zug[i][0] - ende[0]).Length)
            zug = zug[k:] + zug[1 : k + 1] if k else zug
        if ende is None or not _gerade_frei(netz, ende, zug[0], halb, w.radius, teile):
            zugang = _zugang(netz, zug[0], w, halb, teile)
            if zugang is None:
                weg.extend((c.x, c.y, c.z) for c, _a, _n in zug)
                continue
            if davor is not None:
                verlassen(davor)
            vor, knapp, ueber, hoch = zugang
            a0 = zug[0][1]
            dazu(hoch, a0, eilgang=True)
            if ueber is not None:
                dazu(ueber, a0, eilgang=True)
            dazu(knapp, a0)
            dazu(vor, a0, eintauchen=True)
        for c, a, _n in zug:
            dazu(c, a)
        davor = zug
    if davor is not None:
        verlassen(davor)
    return punkte, achsen, weg


def _zugang(netz, stelle, w, halb, teile):
    """(vor, knapp, über, hoch) – die Kugelmitten, über die es an die Stelle geht und von ihr weg:
    vor der Wand (ABSTAND waagerecht – dort liegt kein Aufmaß mehr), ABSTAND längs der Achse
    darüber, auf der Achse über dem Teil (_ueber; None, wenn knapp schon darüber liegt) und in
    Sicherheitshöhe. Im Eilgang nur bis über das Teil – ein G0 fährt auf vielen Steuerungen keine
    Gerade (regelwerk_bahnen 7a) –, längs der Achse hinab im Vorschub, vor der Wand eintauchen.
    Erst vor der Wand, sonst an der Stelle selbst; None, wenn auch das nicht frei bleibt
    (_gerade_frei)."""
    c, a, n = stelle
    waag = FreeCAD.Vector(n.x, n.y, 0.0)
    waag = waag.normalize() if waag.Length > 1e-9 else FreeCAD.Vector(0, 0, 0)
    for vor in (c + waag * ABSTAND, c):
        hoch = vor + a * ((w.sicher + w.radius - vor.z) / max(a.z, 0.2))
        if vor is not c and not _gerade_frei(netz, (c, a, n), (vor, a, n), halb, w.radius, teile):
            continue
        if _gerade_frei(netz, (hoch, a, n), (vor, a, n), halb, w.radius, teile):
            return vor, vor + a * ABSTAND, _ueber(netz, vor, a, w), hoch
    return None


def _ueber(netz, mitte, achse, w):
    """Die Kugelmitte auf der Achse durch `mitte`, deren Kugel ABSTAND über dem Teil steht – None,
    wenn sie nicht weiter als ABSTAND längs der Achse über `mitte` liegt."""
    oben = getattr(netz, "hs_oben", None)
    if oben is None:
        oben = netz.hs_oben = float(netz.ecken[..., 2].max()) if len(netz.ecken) else mitte.z
    if w.oben is not None:
        oben = max(oben, float(w.oben))  # steht vom Rohteil noch etwas über dem Teil
    weit = (oben + ABSTAND + w.radius - mitte.z) / max(achse.z, 0.2)
    if weit <= ABSTAND + 1e-6:
        return None
    return mitte + achse * min(weit, (w.sicher + w.radius - mitte.z) / max(achse.z, 0.2))


def _gerade_frei(netz, von, nach, halb, radius, teile):
    """Bleiben Kugel und Körper auf der Geraden von der Stelle `von` zur Stelle `nach` frei – die
    Achse dabei zwischen beiden gemittelt, wie die Maschine sie dreht?"""
    a, b = von[0], nach[0]
    schritte = max(2, int(math.ceil((b - a).Length / 1.0)) + 1)
    s = np.linspace(0.0, 1.0, schritte)[:, None]
    mitten = np.array([a.x, a.y, a.z]) * (1 - s) + np.array([b.x, b.y, b.z]) * s
    achsen = (
        np.array([von[1].x, von[1].y, von[1].z]) * (1 - s)
        + np.array([nach[1].x, nach[1].y, nach[1].z]) * s
    )
    achsen /= np.linalg.norm(achsen, axis=1)[:, None]
    # Wie bei den Stellen der Züge: knapp unter der Schranke des Netzes liegt die Kugel an (die
    # Enden sind oft Stellen eines Zugs) – das Netz schätzt dort um seine Sehnen zu kurz.
    if (netz.abstand(mitten) < halb - SPIEL - 3.0 * NETZ_TOLERANZ).any():
        return False
    return bool(frei_stueck(netz, mitten - radius * achsen, achsen, teile).all())
