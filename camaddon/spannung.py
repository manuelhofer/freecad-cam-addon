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
mit dem Grund der Bohrung. Läuft ohne Oberfläche.
"""

import math

import FreeCAD

from .sprache import tr

EIGENSCHAFT = "CamAddonGespannt"
GENAU = 1e-6  # mm
BOGEN_SCHRITT = math.radians(10.0)
ZYKLEN = ("G73", "G81", "G82", "G83", "G85", "G86", "G89")


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


def pruefen(job):
    """[Befund] – je Operation, die in den Schraubstock fährt, ein Satz (Modulbeschreibung);
    leer, wenn nichts eingetragen ist oder alles darüber bleibt."""
    from . import reichweite as rw
    from . import schwenken as sw

    tiefe = gespannt(job)
    grundjob = rw.grundjob_von(job)
    rohteil = getattr(getattr(grundjob, "Stock", None), "Shape", None)
    if tiefe <= 0 or rohteil is None or rohteil.isNull():
        return []
    box = rohteil.BoundBox
    oben = box.ZMin + tiefe
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
                and _ragt_heraus(punkt, radius, box)
                and (neben is None or punkt.z < neben.z)
            ):
                neben = punkt
        if unter is not None:
            satz = tr("sn.unter", operation=op.Label, punkt=_xy(unter), unten=rw.weg_text(box.ZMin))
            saetze.append(Befund(satz, op.Label))
        elif neben is not None:
            satz = tr(
                "sn.neben",
                operation=op.Label,
                punkt=_xy(neben),
                gespannt=rw.weg_text(tiefe),
                oben=rw.weg_text(oben),
            )
            saetze.append(Befund(satz, op.Label))
    return saetze


def _radius(op):
    """Der Radius des Werkzeugs der Operation in mm (0, wenn unbekannt)."""
    werkzeug = getattr(getattr(op, "ToolController", None), "Tool", None)
    durchmesser = getattr(werkzeug, "Diameter", 0.0)
    return float(getattr(durchmesser, "Value", durchmesser) or 0.0) / 2.0


def _ragt_heraus(punkt, radius, box):
    """Reicht der Fräser an dieser Stelle über den Umriss des Rohteils hinaus?"""
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
