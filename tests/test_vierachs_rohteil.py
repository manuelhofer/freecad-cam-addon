# Prüft „Teil in die Stange“ (vierachs_rohteil.py, Spezifikation W-003, Abschnitt 5):
# kleinster Kreis und Hülle, nötiger Ø für Quader, Sechskant und eine Welle mit
# Nocken (Mitte der runden Fläche gegen ganzes Teil), die Lage für A, B und C –
# Stirnfläche bei a = 0, Teil dahinter, Normale entlang der Stangenachse –, den
# Vorschlag für den Stangen-Ø, Länge und Lage der Stange, und den Job: Klon an
# seiner Stelle, Original unverändert, Rohteil ein Zylinder, ein Rückgängig; zurück-
# gerechnet aus dem Job: Teil, Stirnfläche, Mitte, Drehlage und Stange.
import math
import os
import random
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import reichweite as rw
from camaddon import vierachs_rohteil as vr

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nahe(a, b, genau=1e-6):
    return abs(a - b) < genau


def gleich(v, w, genau=1e-6):
    return (v - w).Length < genau


# numpy braucht der Rechenkern ab V3 – er muss in jeder FreeCAD-Version da sein.
try:
    import numpy  # noqa: F401 – der Import selbst ist die Prüfung
except ImportError:
    fehler.append("numpy fehlt")

# --- kleinster Kreis und Hülle --------------------------------------------------
quadrat = [(0, 0), (10, 0), (10, 10), (0, 10), (5, 5), (3, 7)]
x, y, r = vr.kleinster_kreis(vr.konvexe_huelle(quadrat))
pruefe(nahe(x, 5) and nahe(y, 5) and nahe(r, 50**0.5), f"Quadrat: {x, y, r}")
pruefe(len(vr.konvexe_huelle(quadrat)) == 4, "Hülle des Quadrats hat nicht 4 Ecken")

zufall = random.Random(7)
wolke = []
for _ in range(2000):
    winkel, abstand = zufall.uniform(0, 2 * math.pi), 10 * math.sqrt(zufall.random())
    wolke.append((3 + abstand * math.cos(winkel), -2 + abstand * math.sin(winkel)))
wolke += [(13, -2), (3 - 5, -2 + 75**0.5), (3 - 5, -2 - 75**0.5)]  # drei auf dem Rand
x, y, r = vr.kleinster_kreis(vr.konvexe_huelle(wolke))
pruefe(nahe(x, 3) and nahe(y, -2) and nahe(r, 10), f"Punktwolke: {x, y, r}")
pruefe(vr.kleinster_kreis([(1, 1)]) == (1, 1, 0.0), "ein Punkt")
x, y, r = vr.kleinster_kreis([(0, 0), (4, 0), (8, 0)])  # auf einer Geraden
pruefe(nahe(x, 4) and nahe(r, 4), f"auf einer Geraden: {x, y, r}")


def flaeche_mit_normale(form, richtung):
    """Die ebene Fläche, deren Außennormale in `richtung` zeigt – die vorderste."""
    kandidaten = [
        (f.CenterOfMass.dot(richtung), f)
        for f in form.Faces
        if vr.ist_eben(f) and gleich(vr.aussennormale(f), richtung, 1e-9)
    ]
    return max(kandidaten, key=lambda k: k[0])[1]


# --- Sechskant: Umkreis 20 -> Ø 40, egal welche Mitte ----------------------------
ecken = [
    FreeCAD.Vector(20 * math.cos(math.radians(60 * i)), 20 * math.sin(math.radians(60 * i)), 0)
    for i in range(6)
]
sechskant = Part.Face(Part.makePolygon(ecken + [ecken[0]])).extrude(FreeCAD.Vector(0, 0, 50))
vorne = flaeche_mit_normale(sechskant, FreeCAD.Vector(0, 0, 1))
mess = vr.vermesse(sechskant, vorne)
pruefe(mess.kreis is None, "Sechskant gilt als rund")
pruefe(nahe(mess.noetig[vr.MITTE_TEIL], 40, 1e-4), f"Sechskant ganz: {mess.noetig}")
pruefe(nahe(mess.noetig[vr.MITTE_FLAECHE], 40, 1e-4), f"Sechskant Fläche: {mess.noetig}")
pruefe(nahe(mess.vorne, 0) and nahe(mess.hinten, -50), f"Sechskant a: {mess.vorne, mess.hinten}")
pruefe(vr.welche_mitte(mess, vr.MITTE_AUTO, 80) == vr.MITTE_TEIL, "eckige Fläche: auto")

# --- Quader 40 × 20 × 10, Stirnfläche die mit Normale +X --------------------------
quader = Part.makeBox(40, 20, 10, FreeCAD.Vector(5, 5, 5))
vorne = flaeche_mit_normale(quader, FreeCAD.Vector(1, 0, 0))
mess = vr.vermesse(quader, vorne)
pruefe(nahe(mess.noetig[vr.MITTE_TEIL], (20**2 + 10**2) ** 0.5, 1e-4), f"Quader: {mess.noetig}")
pruefe(nahe(mess.laenge, 40), f"Quader Länge {mess.laenge}")

# --- Welle Ø 60 × 100 mit Nocken bis 36 mm, gedreht und verschoben ----------------
welle = Part.makeCylinder(30, 100).fuse(Part.makeCylinder(10, 30, FreeCAD.Vector(26, 0, 0)))
welle = welle.removeSplitter()
schief = FreeCAD.Placement(FreeCAD.Vector(5, 7, 9), FreeCAD.Rotation(FreeCAD.Vector(1, 2, 0), 30))
welle.Placement = schief
richtung = schief.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
stirn = flaeche_mit_normale(welle, richtung)
mess = vr.vermesse(welle, stirn)
pruefe(mess.kreis is not None and nahe(mess.kreis[1], 30), f"runde Fläche: {mess.kreis}")
pruefe(
    mess.kreis is not None and gleich(mess.kreis[0], schief.multVec(FreeCAD.Vector(0, 0, 100))),
    "Mitte der runden Fläche liegt nicht in Weltkoordinaten",
)
pruefe(nahe(mess.noetig[vr.MITTE_FLAECHE], 72, 0.01), f"Welle mittig: {mess.noetig}")
pruefe(nahe(mess.noetig[vr.MITTE_TEIL], 66, 0.01), f"Welle ganz: {mess.noetig}")
pruefe(nahe(mess.vorne, 0) and nahe(mess.hinten, -100), f"Welle a: {mess.vorne, mess.hinten}")
pruefe(vr.welche_mitte(mess, vr.MITTE_AUTO, 80) == vr.MITTE_FLAECHE, "Ø 80: runde Fläche")
pruefe(vr.welche_mitte(mess, vr.MITTE_AUTO, 70) == vr.MITTE_TEIL, "Ø 70: ganzes Teil")
pruefe(vr.welche_mitte(mess, vr.MITTE_AUTO, 0) == vr.MITTE_FLAECHE, "ohne Ø: runde Fläche")

for buchstabe, (laengs, _radial) in vr.ACHSEN.items():
    for mitte in (vr.MITTE_FLAECHE, vr.MITTE_TEIL):
        gewaehlt = vr.lage(mess, buchstabe, mitte, drehlage=0.0, durchmesser=80)
        gelegt = welle.copy()
        gelegt.transformShape(gewaehlt.placement.toMatrix())
        n = gewaehlt.placement.Rotation.multVec(richtung)
        pruefe(gleich(n, laengs), f"{buchstabe}/{mitte}: Normale zeigt nicht nach vorne ({n})")
        a = [p.Point.dot(laengs) for p in gelegt.Vertexes]
        pruefe(nahe(max(a), 0, 1e-6), f"{buchstabe}/{mitte}: Stirnfläche nicht bei a = 0")
        pruefe(nahe(min(a), -100, 1e-6), f"{buchstabe}/{mitte}: Teil nicht bei a = −100")
        # Kein Punkt weiter von der Achse als der halbe nötige Ø.
        punkte, _ = gelegt.tessellate(vr.TESSELLIERUNG)
        weitester = max((p - laengs * p.dot(laengs)).Length for p in punkte)
        pruefe(
            weitester <= gewaehlt.durchmesser / 2 + 0.01,
            f"{buchstabe}/{mitte}: {weitester} weiter als Ø {gewaehlt.durchmesser}",
        )
        if mitte == vr.MITTE_FLAECHE:  # die Mitte der runden Fläche sitzt auf der Achse
            m = gewaehlt.placement.multVec(mess.kreis[0])
            pruefe(gleich(m, FreeCAD.Vector()), f"{buchstabe}: Mitte der Fläche bei {m}")

# Drehlage 90°: um die Stangenachse gedreht, Stirnfläche bleibt bei a = 0.
l0 = vr.lage(mess, "C", vr.MITTE_TEIL, 0.0, 80)
l90 = vr.lage(mess, "C", vr.MITTE_TEIL, 90.0, 80)
p0 = l0.placement.multVec(stirn.CenterOfMass)
p90 = l90.placement.multVec(stirn.CenterOfMass)
gedreht = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 90).multVec(p0)
pruefe(gleich(p90, gedreht, 1e-6), f"Drehlage: {p90} statt {gedreht}")
pruefe(nahe(vr.aufmass(l0, 80), 7, 0.01), f"Aufmaß {vr.aufmass(l0, 80)}")

# --- Drehteil (V2b): eine runde Fläche gibt die Stangenachse ----------------------------------
# Welle Ø 30 längs X von x 0 bis 80, am Ende x 80 eine Kegelspitze bis x 95. Geklickt auf den
# Mantel nahe x 70: Die Achse X wird die Stangenachse, vorne liegt die Kegelspitze (a 0), das
# Teil reicht bis a −95, Mitte auf der Achse, Ø 30 nötig. Nahe x 10: das andere Ende vorne;
# „Umdrehen“ tauscht zurück. Kegel und Kugel geben ihre Achse ebenso; eine Freiform nicht.
LAENGS_X = FreeCAD.Vector(1, 0, 0)
drehteil = (
    Part.makeCylinder(15, 80, FreeCAD.Vector(0, 0, 0), LAENGS_X)
    .fuse(Part.makeCone(15, 0, 15, FreeCAD.Vector(80, 0, 0), LAENGS_X))
    .removeSplitter()
)
dt_mantel = next(f for f in drehteil.Faces if isinstance(f.Surface, Part.Cylinder))
dv = vr.vermesse(drehteil, dt_mantel, nahe=FreeCAD.Vector(70, 0, 15))
pruefe(dv.rund and gleich(dv.normale, LAENGS_X), f"Mantel nahe x 70: Normale {dv.normale}")
pruefe(nahe(dv.vorne, 0.0) and nahe(dv.hinten, -95.0), f"vorne/hinten {dv.vorne}, {dv.hinten}")
pruefe(nahe(dv.noetig[vr.MITTE_FLAECHE], 30.0, 1e-3), f"nötig {dv.noetig}")
pruefe(nahe(dv.kreis[1], 15.0, 1e-3), f"Ø der Fläche {2 * dv.kreis[1]}")
dt_lage = vr.lage(dv, "A")
dt_spitze = dt_lage.placement.multVec(FreeCAD.Vector(95, 0, 0))
pruefe(
    gleich(dt_spitze, FreeCAD.Vector(0, 0, 0)),
    f"Kegelspitze nicht vorne auf der Achse: {dt_spitze}",
)
dv = vr.vermesse(drehteil, dt_mantel, nahe=FreeCAD.Vector(10, 0, 15))
pruefe(gleich(dv.normale, LAENGS_X * -1) and nahe(dv.hinten, -95.0), f"nahe x 10: {dv.normale}")
dv = vr.vermesse(drehteil, dt_mantel, nahe=FreeCAD.Vector(10, 0, 15), umgedreht=True)
pruefe(gleich(dv.normale, LAENGS_X), f"umgedreht: {dv.normale}")
dt_kegel = next(f for f in drehteil.Faces if isinstance(f.Surface, Part.Cone))
pruefe(gleich(vr.vermesse(drehteil, dt_kegel).normale, LAENGS_X), "Kegel: Achse nicht LAENGS_X")
dt_kugel = Part.makeSphere(10)
pruefe(vr.vermesse(dt_kugel, dt_kugel.Faces[0]).rund, "Kugel: keine runde Fläche")
dt_freiform = Part.BSplineSurface()
dt_freiform.interpolate([[FreeCAD.Vector(i, j, 0.1 * i * j) for j in range(4)] for i in range(4)])
try:
    vr.vermesse(drehteil, dt_freiform.toShape())
except ValueError:
    pass
else:
    pruefe(False, "Freiform als Stirnfläche")

# --- Vorschlag, Länge und Lage der Stange -----------------------------------------
pruefe(vr.vorschlag_durchmesser(72) == 75, "Vorschlag für Ø 72")
pruefe(vr.vorschlag_durchmesser(66) == 70, "Vorschlag für Ø 66")
pruefe(vr.vorschlag_durchmesser(68.5) == 75, "Vorschlag für Ø 68,5")
pruefe(nahe(vr.vorschlag_durchmesser(40, zoll=True), 25.4 * 14 / 8), "Vorschlag in Zoll")
stange = vr.Stange(80.0)
pruefe(nahe(vr.stangenlaenge(mess, stange), 134), "Stangenlänge")
for buchstabe, (laengs, _radial) in vr.ACHSEN.items():
    platz = vr.stangen_placement(mess, stange, buchstabe)
    zylinder = Part.makeCylinder(40, vr.stangenlaenge(mess, stange))
    zylinder.Placement = platz
    a = [ecke.Point.dot(laengs) for ecke in zylinder.Vertexes]
    pruefe(
        nahe(max(a), 1) and nahe(min(a), -133), f"Stange {buchstabe}: a von {min(a)} bis {max(a)}"
    )

# --- Job: Klon an seiner Stelle, Zylinder-Rohteil, ein Rückgängig -----------------
import Path.Main.Stock as PathStock  # noqa: E402 – erst hier: die Rechnung braucht kein CAM

dok = FreeCAD.newDocument("VierachsRohteil")
dok.UndoMode = 1
teil = dok.addObject("Part::Feature", "Welle")
teil.Shape = welle
dok.recompute()
teil_vorher = FreeCAD.Placement(teil.Placement)
form = teil.Shape
stirn_teil = flaeche_mit_normale(form, richtung)
nummer = 1 + next(i for i, f in enumerate(form.Faces) if f.isSame(stirn_teil))
flaechenname = f"Face{nummer}"
objekte_vorher = len(dok.Objects)

dok.openTransaction("Teil in die Stange")
mess = vr.vermesse(teil.Shape, teil.Shape.getElement(flaechenname))
im_job = vr.lage(mess, "C", vr.MITTE_AUTO, 0.0, 80)
job = vr.richte_ein(dok, teil, im_job, stange, "C", beschriftung="Welle – 4 Achsen")
dok.commitTransaction()

pruefe(job.Label == "Welle – 4 Achsen", f"Name des Jobs: {job.Label}")
rohteil = job.Stock
pruefe(
    PathStock.StockType.FromStock(rohteil) == PathStock.StockType.CreateCylinder,
    "Rohteil ist kein Zylinder",
)
pruefe(nahe(rohteil.Radius.Value, 40) and nahe(rohteil.Height.Value, 134), "Maße des Rohteils")
bb = rohteil.Shape.BoundBox
pruefe(nahe(bb.ZMin, -133, 1e-6) and nahe(bb.ZMax, 1, 1e-6), f"Rohteil in Z: {bb}")
pruefe(nahe(bb.XMin, -40, 1e-6) and nahe(bb.XMax, 40, 1e-6), f"Rohteil in X: {bb}")
klon = vr.modell(job)
pruefe(vr.original(klon) is teil, "original() findet das Teil hinter dem Klon nicht")
pruefe(vr.original(teil) is teil, "original() eines Teils")
kbb = klon.Shape.BoundBox
pruefe(nahe(kbb.ZMax, 0, 1e-6) and nahe(kbb.ZMin, -100, 1e-6), f"Klon in Z: {kbb}")
# Die Hüllbox gekrümmter Flächen ist in OCC nur auf etwa 0,003 mm genau.
pruefe(nahe(kbb.XMax, 36, 0.01) and nahe(kbb.XMin, -30, 0.01), f"Klon quer: {kbb}")
pruefe(teil.Placement == teil_vorher, "Das Original hat sich bewegt")
pruefe(len([o for o in dok.Objects if "Stock" in o.Name]) == 1, "altes Rohteil nicht entfernt")
# Die Stange merkt sich ihre Spannlänge: „Auf der Maschine prüfen“ steckt sie damit ins
# Futter, genau auf ihrer Achse (V2c) – hinten bei Z −133, davon 30 mm im Futter.
pruefe(vr.spannlaenge(job) == 30.0, f"Spannlänge am Job: {vr.spannlaenge(job)}")
pruefe("Hidden" in job.getEditorMode(vr.EIGENSCHAFT_SPANNLAENGE), "Spannlänge sichtbar")
vorschlag = rw.vorschlag_nullpunkt(job)
pruefe((vorschlag - FreeCAD.Vector(0, 0, 103)).Length < 1e-9, f"Nullpunkt im Futter: {vorschlag}")

# Zurückgerechnet (V3h, zum Ändern): Teil, Stirnfläche, Mitte, Drehlage und Stange stehen
# im Job selbst.
Z = FreeCAD.Vector(0, 0, 1)
e = vr.einstellung(job)
pruefe(e is not None, "Einstellung nicht zurückgerechnet")
if e is not None:
    pruefe(e.teil is teil and e.flaeche == flaechenname, f"Teil/Fläche: {e.flaeche}")
    pruefe(
        e.mitte == im_job.mitte and nahe(e.drehlage, 0) and gleich(e.laengs, Z),
        f"Mitte/Drehlage/Achse: {e.mitte}, {e.drehlage}, {e.laengs}",
    )
    pruefe(e.stange == stange, f"Stange: {e.stange}")

# Noch einmal mit A und anderem Ø: derselbe Job, das Rohteil wird angepasst, nicht ersetzt.
dok.openTransaction("anders")
name_rohteil = job.Stock.Name
im_job = vr.lage(mess, "A", vr.MITTE_AUTO, 0.0, 90)
vr.richte_ein(dok, teil, im_job, vr.Stange(90.0, 2.0, 3.0, 30.0), "A", job=job)
dok.commitTransaction()
pruefe(job.Stock.Name == name_rohteil, "Rohteil ersetzt statt angepasst")
bb = job.Stock.Shape.BoundBox
pruefe(nahe(bb.XMin, -133, 1e-6) and nahe(bb.XMax, 2, 1e-6), f"Rohteil bei A: {bb}")
pruefe(nahe(bb.YMin, -45, 1e-6) and nahe(bb.ZMax, 45, 1e-6), f"Rohteil bei A quer: {bb}")
e = vr.einstellung(job)
pruefe(
    e is not None
    and e.stange == vr.Stange(90.0, 2.0, 3.0, 30.0)
    and gleich(e.laengs, FreeCAD.Vector(1, 0, 0))
    and e.mitte == im_job.mitte,
    f"Einstellung bei A: {e}",
)
# B, ganzes Teil mittig, um 90° gedreht, andere Stange.
dok.openTransaction("gedreht")
im_job = vr.lage(mess, "B", vr.MITTE_TEIL, 90.0, 75)
vr.richte_ein(dok, teil, im_job, vr.Stange(75.0, 0.5, 4.0, 25.0), "B", job=job)
dok.commitTransaction()
e = vr.einstellung(job)
pruefe(
    e is not None
    and e.mitte == vr.MITTE_TEIL
    and nahe(e.drehlage, 90, 1e-6)
    and e.stange == vr.Stange(75.0, 0.5, 4.0, 25.0),
    f"Einstellung bei B, gedreht: {e and (e.mitte, e.drehlage, e.stange)}",
)
# Quer verschoben liegt das Teil nicht mehr, wie der Assistent es legt: keine Einstellung.
klon = vr.modell(job)
lage_klon = FreeCAD.Placement(klon.Placement)
klon.Placement = FreeCAD.Placement(lage_klon.Base + FreeCAD.Vector(1, 0, 0), lage_klon.Rotation)
pruefe(vr.einstellung(job) is None, "verschobener Klon gilt als eingerichtet")
klon.Placement = lage_klon

undo = len(dok.UndoNames)
pruefe(undo == 3, f"{undo} Schritte Rückgängig statt 3: {dok.UndoNames}")
dok.undo()
dok.undo()
dok.undo()
dok.recompute()
pruefe(len(dok.Objects) == objekte_vorher, f"nach Rückgängig: {[o.Name for o in dok.Objects]}")
FreeCAD.closeDocument(dok.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
