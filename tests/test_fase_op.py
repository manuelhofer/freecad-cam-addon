# Prüft die Operation „Fase“ im Job (fase, W-037): Ein Quader 40 × 30 × 10, oben rundum 1 × 45°
# gefast. Mit dem Standardfräser Ø 12 in Stufen: „Fase T1“, eine Fase (die vier Flächen sind eine
# Kette), 21 Lagen (Stufe 0,05 von 10 bis 9), Endtiefe 9 (der Fuß), Befehle im Programm, das Raster
# der Operation gilt. Eine größere Stufe (0,25) gibt 5 Lagen. Mit einem 90°-Fasenfräser: „Fase T3“,
# eine Lage, die Spitze auf 9. Ein 60°-Fasenfräser: kein Programm, der Satz nennt 90° und 60°.
# schneide_des_werkzeugs: Kugelfräser nicht, Torusfräser nicht (die Ecke streifte die Fase).
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import fase as fa
from camaddon import job_schnittwerte as js
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")


def fasenfraeser(nummer, winkel):
    w = wz.Werkzeug(
        nummer=nummer,
        name=f"Fase {winkel:g}",
        art=wz.FASENFRAESER,
        durchmesser=10.0,
        schneiden=2,
        schneidenlaenge=5.0,
        spitzenwinkel=winkel,
        spitzen_d=0.5,
        schneidstoff=wz.VHM,
    )
    w.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=100.0, fz=0.05)]
    return w


schaft = wz.standardwerkzeug()
fase90, fase60 = fasenfraeser(3, 90.0), fasenfraeser(4, 60.0)
kugel = wz.Werkzeug(nummer=5, name="Kugel 6", art=wz.KUGELFRAESER, durchmesser=6.0, schneiden=2)
torus = wz.Werkzeug(
    nummer=6, name="Torus 10", art=wz.TORUSFRAESER, durchmesser=10.0, schneiden=4, eckradius=1.0
)
pruefe(
    fa.werkzeug_passt(schaft) and fa.werkzeug_passt(fase90), "Schaft- oder Fasenfräser passt nicht"
)
pruefe(not fa.werkzeug_passt(kugel), "Kugelfräser passt")
pruefe(not fa.werkzeug_passt(torus), "Torusfräser passt")

klotz = Part.makeBox(40, 30, 10)
oben = [
    k for k in klotz.Edges if abs(k.BoundBox.ZMin - 10) < 1e-9 and abs(k.BoundBox.ZMax - 10) < 1e-9
]
klotz = klotz.makeChamfer(1.0, oben)
fasen = []
for i, f in enumerate(klotz.Faces):
    u0, u1, v0, v1 = f.ParameterRange
    if 0.1 < f.normalAt((u0 + u1) / 2, (v0 + v1) / 2).z < 0.9:
        fasen.append(f"Face{i + 1}")
pruefe(len(fasen) == 4, f"Fasen: {fasen}")

import Path.Main.Job as PathJob  # noqa: E402

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([schaft, fase90, fase60]))
doc = FreeCAD.newDocument("FaseOp")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = klotz
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()


def controller(werkzeug):
    tc = js.controller_ohne_transaktion(doc, job, werkzeug, werkzeug.schnittwerte[wz.ALLE][0])
    doc.recompute()
    return tc


op = fa.lege_an(job, controller(schaft), flaechen=fasen)
doc.recompute()
pruefe(op.Label == "Fase T1", f"Name: {op.Label}")
pruefe(
    (op.Fasen, op.Lagen, op.Ausgelassen) == (1, 21, 0), f"{op.Fasen}, {op.Lagen}, {op.Ausgelassen}"
)
pruefe(abs(float(op.FinalDepth) - 9.0) < 1e-6, f"Endtiefe {float(op.FinalDepth)}")
befehle = [c for c in op.Path.Commands if c.Name in ("G1", "G2", "G3")]
pruefe(len(befehle) > 40, f"{len(befehle)} Vorschubsätze")
zs = [c.Parameters["Z"] for c in op.Path.Commands if "Z" in c.Parameters and c.Name == "G1"]
pruefe(zs and abs(min(zs) - 9.0) < 1e-6, f"tiefstes Z {min(zs) if zs else None}")
op.Stufe = 0.25
doc.recompute()
pruefe(op.Lagen == 5, f"Stufe 0,25: {op.Lagen} Lagen")

op90 = fa.lege_an(job, controller(fase90), flaechen=fasen)
doc.recompute()
pruefe(op90.Label == "Fase T3" and op90.Lagen == 1, f"Fasenfräser: {op90.Label}, {op90.Lagen}")
zs = [c.Parameters["Z"] for c in op90.Path.Commands if "Z" in c.Parameters and c.Name == "G1"]
pruefe(zs and abs(min(zs) - 9.0) < 1e-6, f"Spitze bei {min(zs) if zs else None}")

op60 = fa.lege_an(job, controller(fase60), flaechen=fasen)
doc.recompute()
kommentar = " ".join(c.Name for c in op60.Path.Commands if c.Name.startswith("("))
pruefe(op60.Lagen == 0 and "90" in kommentar and "60" in kommentar, f"60°: {kommentar!r}")
pruefe(fa.ist_fase_op(op) and not fa.ist_fase_op(job), "ist_fase_op")
FreeCAD.closeDocument(doc.Name)

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
