# SPDX-License-Identifier: LGPL-2.1-or-later
"""Von unten gespannt (Spezifikation Strategien, S3h; Manuel, 2026-10-01: „so viel steckt im
Schraubstock – die Prüfung zeigt es und meldet jede Bahn darunter“).

Am Grundjob steht, wie viel vom Rohteil von unten im Schraubstock steckt (`gespannt`, 0: nichts
eingetragen). pruefen() geht die Bahnen des Jobs und seiner geschwenkten Ebenen durch – die
Spitze des Werkzeugs im Grundjob – und meldet je Operation die tiefste Stelle, an der sie

- unter das Rohteil fährt (ein Bohrer durch: in den Schraubstock oder die Unterlage), oder
- unter der Spannhöhe neben das Rohteil ragt: Dort sitzen die Backen. Wo der Fräser ganz
  über dem Rohteil bleibt – eine Tasche im Teil –, hält ihn nichts auf.

Wie das Rohteil liegt, sagt sein Hüllquader. Kreisbögen zählen mit ihren Punkten, Bohrzyklen
mit dem Grund der Bohrung. schraubstock() gibt die Backen als Körper – fürs Bild und die
Kollision in „Auf der Maschine prüfen“: vorn und hinten (in Y) am Rohteil, so lang wie es, so
hoch wie gespannt. Läuft ohne Oberfläche.
"""

import math

import FreeCAD

from .sprache import tr

EIGENSCHAFT = "CamAddonGespannt"
GENAU = 1e-6  # mm
BOGEN_SCHRITT = math.radians(10.0)
ZYKLEN = ("G73", "G81", "G82", "G83", "G85", "G86", "G89")
BACKE = 20.0  # mm – so dick ist eine Backe des Schraubstocks im Bild und in der Kollision
# Ein runder Rohling (W-021) steckt im Dreibackenfutter: drei Backen, je 120° versetzt, so lang
# (radial) und so breit wie hier.
FUTTERBACKE_LANG = 25.0  # mm
FUTTERBACKE_BREIT = 20.0  # mm
# Das Futter darunter (W-021, Stufe 3: „er hebt das Teil über den Tisch“): ein übliches
# Dreibackenfutter – (Ø, Höhe) in mm, wie die gängigen Größen; genommen wird das kleinste, in dem
# die Backen um den Rohling Platz haben.
FUTTER = (
    (80.0, 50.0),
    (100.0, 58.0),
    (125.0, 66.0),
    (160.0, 80.0),
    (200.0, 92.0),
    (250.0, 106.0),
    (315.0, 120.0),
)


def rund(rohteil):
    """(Mitte x, Mitte y, Radius) eines stehenden runden Rohteils (FreeCADs Zylinder-Rohteil,
    Achse senkrecht) – sonst None."""
    if rohteil is None or not (hasattr(rohteil, "Radius") and hasattr(rohteil, "Height")):
        return None
    lage = rohteil.Placement
    if not lage.Rotation.isIdentity() or str(getattr(rohteil, "Axis", "Z") or "Z") not in ("Z", ""):
        return None
    radius = getattr(rohteil, "Radius", 0.0)
    return float(lage.Base.x), float(lage.Base.y), float(getattr(radius, "Value", radius))


def futter_masse(radius):
    """(Ø, Höhe) des Dreibackenfutters für einen runden Rohling mit `radius` (mm): das kleinste
    aus FUTTER, über das die Backen nicht hinausragen; größer als alle: so breit wie nötig, so
    hoch wie das größte."""
    noetig = 2.0 * (radius + FUTTERBACKE_LANG)
    for durchmesser, hoehe in FUTTER:
        if durchmesser >= noetig - GENAU:
            return durchmesser, hoehe
    return noetig, FUTTER[-1][1]


def futter_hoehe(job):
    """So hoch hebt das Dreibackenfutter den runden Rohling des Jobs über die Spannfläche (mm) –
    0 ohne runden Rohling oder wenn nichts gespannt ist. Eine Stange im Futter der Rundachse
    (4 Achsen, vierachs_rohteil.spannlaenge) sitzt in der Maschine, nicht auf dem Tisch."""
    from . import reichweite as rw
    from . import vierachs_rohteil as vr

    grund = rw.grundjob_von(job)
    kreis = rund(getattr(grund, "Stock", None))
    if kreis is None or gespannt(grund) <= 0 or vr.ist_stange(grund):
        return 0.0
    return futter_masse(kreis[2])[1]


class Befund(str):
    """Ein Satz, der meldet, dass eine Operation in den Schraubstock fährt; `operation`: ihr
    Name."""

    operation = ""

    def __new__(cls, satz, operation):
        befund = super().__new__(cls, satz)
        befund.operation = operation
        return befund


def gespannt(job):
    """So viel (mm) steckt vom Rohteil des Jobs – bei einer Ebene: des Grundjobs – von unten im
    Schraubstock; 0, wenn nichts eingetragen ist."""
    from . import reichweite as rw

    wert = getattr(rw.grundjob_von(job), EIGENSCHAFT, 0.0)
    return float(getattr(wert, "Value", wert) or 0.0)


def setze(job, mm):
    """Trägt am Job ein, wie viel von unten gespannt ist – sichtbar im Eigenschaften-Editor
    (Gruppe „CAM-Addon“), dort auch zu ändern. 0 ohne Eigenschaft legt keine an."""
    if EIGENSCHAFT not in job.PropertiesList:
        if mm <= 0:
            return
        job.addProperty("App::PropertyLength", EIGENSCHAFT, "CAM-Addon", tr("sn.eigenschaft"))
    if abs(gespannt(job) - mm) > GENAU:
        setattr(job, EIGENSCHAFT, max(mm, 0.0))


def schraubstock(job):
    """Die Backen des Schraubstocks als ein Körper in Koordinaten des Grundjobs – None, wenn
    nichts gespannt ist oder es kein Rohteil gibt. In der N-Eck-Stange (W-018) die Backen am
    Ende der Stange (n_eck.backen); mit einer Aufspannung (spannmittel) deren Spannmittel."""
    import Part

    from . import n_eck as ne
    from . import reichweite as rw

    if ne.ist_n_eck(job):
        return ne.backen(job)
    from . import spannmittel as sm

    if sm.aufspannung(job) is not None:  # aus der Sammlung, auf dem Tisch eingerichtet (W-042)
        return sm.koerper_im_job(job)
    tiefe = gespannt(job)
    stock = getattr(rw.grundjob_von(job), "Stock", None)
    rohteil = getattr(stock, "Shape", None)
    if tiefe <= 0 or rohteil is None or rohteil.isNull():
        return None
    box = rohteil.BoundBox
    kreis = rund(stock)
    if kreis is not None:
        return _futter(kreis, box.ZMin, tiefe)
    backen = [
        Part.makeBox(box.XLength, BACKE, tiefe, FreeCAD.Vector(box.XMin, y, box.ZMin))
        for y in (box.YMin - BACKE, box.YMax)
    ]
    return Part.makeCompound(backen)


def _futter(kreis, z, tiefe):
    """Das Dreibackenfutter am runden Rohling (Mitte, Radius): darunter der Körper (futter_masse),
    seine Oberseite bei z; darauf die drei Backen – von z an so hoch, wie er gespannt ist."""
    import Part

    x, y, radius = kreis
    durchmesser, hoehe = futter_masse(radius)
    backen = [Part.makeCylinder(durchmesser / 2, hoehe, FreeCAD.Vector(x, y, z - hoehe))]
    for winkel in (90.0, 210.0, 330.0):
        backe = Part.makeBox(
            FUTTERBACKE_LANG,
            FUTTERBACKE_BREIT,
            tiefe,
            FreeCAD.Vector(radius, -FUTTERBACKE_BREIT / 2, z),
        )
        backe.rotate(FreeCAD.Vector(0, 0, z), FreeCAD.Vector(0, 0, 1), winkel)
        backe.translate(FreeCAD.Vector(x, y, 0))
        backen.append(backe)
    return Part.makeCompound(backen)


def pruefen(job):
    """[Befund] – je Operation, die in den Schraubstock fährt, ein Satz (Modulbeschreibung);
    leer, wenn nichts eingetragen ist oder alles darüber bleibt."""
    from . import n_eck as ne
    from . import reichweite as rw
    from . import schwenken as sw

    if ne.ist_n_eck(job):
        return _pruefen_stange(job)
    tiefe = gespannt(job)
    grundjob = rw.grundjob_von(job)
    rohteil = getattr(getattr(grundjob, "Stock", None), "Shape", None)
    if tiefe <= 0 or rohteil is None or rohteil.isNull():
        return []
    box = rohteil.BoundBox
    oben = box.ZMin + tiefe
    kreis = rund(getattr(grundjob, "Stock", None))
    saetze = []
    for op, ebene in rw.operationen_mit_ebene(grundjob):
        lage = sw.ebene_von(ebene) if ebene is not None else None
        radius = _radius(op)
        unter, neben = None, None  # die tiefste Stelle je Art: (z, Punkt)
        for punkt in _punkte(op.Path.Commands):
            if lage is not None:
                punkt = lage.multVec(punkt)
            if punkt.z < box.ZMin - GENAU:
                if unter is None or punkt.z < unter.z:
                    unter = punkt
            elif (
                punkt.z < oben - GENAU
                and _ragt_heraus(punkt, radius, box, kreis)
                and (neben is None or punkt.z < neben.z)
            ):
                neben = punkt
        if unter is not None:
            satz = tr("sn.unter", operation=op.Label, punkt=_xy(unter), unten=rw.weg_text(box.ZMin))
            saetze.append(Befund(satz, op.Label))
        elif neben is not None:
            werte = {
                "operation": op.Label,
                "punkt": _xy(neben),
                "gespannt": rw.weg_text(tiefe),
                "oben": rw.weg_text(oben),
            }
            satz = tr("sn.neben_futter", **werte) if kreis is not None else tr("sn.neben", **werte)
            saetze.append(Befund(satz, op.Label))
    return saetze


NEBEN_LUFT = 1.0  # mm: so weit bleiben Spannmittel unter der tiefsten Stelle neben dem Rohteil


def neben_dem_rohteil(job):
    """[(Operation, z)] – je Operation des Jobs, deren Fräser über den Umriss des Rohteils
    hinausragt, die tiefste Stelle der Spitze dort (im Grundjob, über der Unterkante des Rohteils
    und unter seiner Oberkante): So tief dürfen daneben keine Spannmittel stehen. Gleich, ob
    „gespannt“ eingetragen ist – fürs Einrichtblatt (Manuel, 2026-10-18: „was hilft da langsames
    fahren .. wenn der bediener diesen wert nicht angibt … im einstellblatt muss natürlich vermerkt
    werden maximal entfernung von z0 … ein wert für jeden fräser“). Leer an der Stange und am
    N-Eck (dort spannt das Futter bzw. der Schraubstock am Ende)."""
    from . import n_eck as ne
    from . import reichweite as rw
    from . import schwenken as sw

    if ne.ist_n_eck(job):
        return []
    grundjob = rw.grundjob_von(job)
    rohteil = getattr(getattr(grundjob, "Stock", None), "Shape", None)
    if rohteil is None or rohteil.isNull():
        return []
    from . import vierachs_rohteil as vr

    if vr.ist_stange(grundjob, getattr(grundjob, "Stock", None)):
        return []
    box = rohteil.BoundBox
    kreis = rund(getattr(grundjob, "Stock", None))
    ergebnis = []
    for op, ebene in rw.operationen_mit_ebene(job):
        lage = sw.ebene_von(ebene) if ebene is not None else None
        radius = _radius(op)
        tiefste = None
        for punkt in _punkte(op.Path.Commands):
            if lage is not None:
                punkt = lage.multVec(punkt)
            if (
                box.ZMin - GENAU <= punkt.z < box.ZMax - GENAU
                and _ragt_heraus(punkt, radius, box, kreis)
                and (tiefste is None or punkt.z < tiefste)
            ):
                tiefste = punkt.z
        if tiefste is not None:
            ergebnis.append((op, float(tiefste)))
    return ergebnis


def _pruefen_stange(job):
    """pruefen() in der N-Eck-Stange (W-018): je Operation, deren Fräser unter dem oberen Rand
    der Backen über ihren vorderen Rand reicht, ein Satz – mit der Stelle, die am weitesten
    hineinreicht."""
    from . import n_eck as ne
    from . import reichweite as rw

    if getattr(getattr(job, "Stock", None), "Shape", None) is None:
        return []
    vorn, oben = ne.backen_x(job), ne.backen_oben(job)
    saetze = []
    for op, _ebene in rw.operationen_mit_ebene(job):
        radius = _radius(op)
        tiefste = None
        for punkt in _punkte(op.Path.Commands):
            if (
                punkt.x + radius > vorn + GENAU
                and punkt.z < oben - GENAU
                and (tiefste is None or punkt.x > tiefste.x)
            ):
                tiefste = punkt
        if tiefste is not None:
            satz = tr("sn.backen", operation=op.Label, punkt=_xy(tiefste), x=rw.weg_text(vorn))
            saetze.append(Befund(satz, op.Label))
    return saetze


def _radius(op):
    """Der Radius des Werkzeugs der Operation in mm (0, wenn unbekannt)."""
    werkzeug = getattr(getattr(op, "ToolController", None), "Tool", None)
    durchmesser = getattr(werkzeug, "Diameter", 0.0)
    return float(getattr(durchmesser, "Value", durchmesser) or 0.0) / 2.0


def _ragt_heraus(punkt, radius, box, kreis=None):
    """Reicht der Fräser an dieser Stelle über den Umriss des Rohteils hinaus – beim runden
    Rohling (`kreis`: Mitte, Radius) über seinen Umfang?"""
    if kreis is not None:
        return math.hypot(punkt.x - kreis[0], punkt.y - kreis[1]) + radius > kreis[2] + GENAU
    return (
        punkt.x - radius < box.XMin - GENAU
        or punkt.x + radius > box.XMax + GENAU
        or punkt.y - radius < box.YMin - GENAU
        or punkt.y + radius > box.YMax + GENAU
    )


def _xy(punkt):
    from . import reichweite as rw

    return rw.punkt_text({"X": punkt.x, "Y": punkt.y, "Z": punkt.z})


def _punkte(befehle):
    """Die Stellen der Spitze (Vector, im Job der Operation): jeder Satz mit seinem Ziel,
    Kreisbögen (G2/G3 in XY) in Stücken, Bohrzyklen mit dem Grund der Bohrung."""
    x = y = z = None
    for befehl in befehle:
        name = befehl.Name.upper()
        werte = befehl.Parameters
        if name in ZYKLEN:
            bx, by = werte.get("X", x), werte.get("Y", y)
            if bx is not None and by is not None and "Z" in werte:
                yield FreeCAD.Vector(bx, by, werte["Z"])
            x, y = bx, by
            continue
        if not any(k in werte for k in "XYZ"):
            continue
        nx, ny, nz = werte.get("X", x), werte.get("Y", y), werte.get("Z", z)
        if name in ("G2", "G02", "G3", "G03") and None not in (x, y, z, nx, ny, nz):
            yield from _bogen(x, y, z, nx, ny, nz, werte, name in ("G2", "G02"))
        elif None not in (nx, ny, nz):
            yield FreeCAD.Vector(nx, ny, nz)
        x, y, z = nx, ny, nz


def _bogen(x, y, z, nx, ny, nz, werte, uhrzeiger):
    """Punkte eines Kreisbogens um (x + I, y + J) in XY, z linear dazwischen."""
    mx, my = x + werte.get("I", 0.0), y + werte.get("J", 0.0)
    r = math.hypot(x - mx, y - my)
    a0 = math.atan2(y - my, x - mx)
    a1 = math.atan2(ny - my, nx - mx)
    weite = (a0 - a1) if uhrzeiger else (a1 - a0)
    weite %= 2 * math.pi
    if weite < GENAU:
        weite = 2 * math.pi  # ein ganzer Kreis
    n = max(1, math.ceil(weite / BOGEN_SCHRITT))
    for i in range(1, n + 1):
        t = i / n
        a = a0 - weite * t if uhrzeiger else a0 + weite * t
        yield FreeCAD.Vector(mx + r * math.cos(a), my + r * math.sin(a), z + (nz - z) * t)
