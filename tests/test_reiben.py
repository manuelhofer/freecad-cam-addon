# Prüft „Reiben“ (W-006 4.1 Punkt 7): Platte 60 × 40 × 20 mit einer durchgehenden Bohrung Ø 10
# bei (15, 20) und einer gebohrten Sackbohrung Ø 10, 12 tief mit 118°-Spitze bei (45, 20), dazu
# eine Sackbohrung Ø 10 mit ebenem Grund bei (30, 32). Die Reibahle Ø 10 reibt die durchgehende
# bis 1 mm unter den Grund und die mit Spitze bis zum Grund der Wand – im Vorschub hinein und
# heraus (G85); die mit ebenem Grund nicht (kein Bohrer bohrt sie vor). Vorgebohrt wird
# 0,15 bis 0,5 kleiner: Ø 9,8 ja, Ø 10 und Ø 9,4 nicht. Dann die Operationen im Job: „Reiben
# T4“, je Tiefe eine, G85, Art „Drilling“ mit dem Einsatz „Reiben“.
import math
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import bohren as bh
from camaddon import bohrung_bahn as bb
from camaddon import job_schnittwerte as js
from camaddon import reiben as rbn
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")

spitze_h = 5.0 / math.tan(math.radians(59.0))
teil = Part.makeBox(60, 40, 20)
teil = teil.cut(Part.makeCylinder(5, 20, V(15, 20, 0)))
teil = teil.cut(Part.makeCylinder(5, 12, V(45, 20, 8)))
teil = teil.cut(Part.makeCone(0, 5, spitze_h, V(45, 20, 8 - spitze_h)))
teil = teil.cut(Part.makeCylinder(5, 6, V(30, 32, 14))).removeSplitter()
namen = {(round(b.mitte[0]), round(b.mitte[1])): b for b in bb.bohrungen(teil)}
durch, spitz, flach = namen.get((15, 20)), namen.get((45, 20)), namen.get((30, 32))
pruefe(durch and durch.durch, f"durchgehend: {durch}")
pruefe(spitz and not spitz.durch and abs(spitz.spitze - 118) < 0.5, f"Spitze: {spitz}")
pruefe(flach and not flach.durch and flach.spitze == 0, f"eben: {flach}")

# --- Reibahle und Vorbohren ---------------------------------------------------------------------
pruefe(rbn.kann(durch, 10.0) and rbn.kann(spitz, 10.0), "Reibahle Ø 10 passt nicht")
pruefe(not rbn.kann(flach, 10.0) and not rbn.kann(durch, 10.1), "Reibahle passt zu viel")
pruefe(bh.kann(durch, 9.8, 118.0, reiben=True), "Ø 9,8 bohrt nicht vor")
pruefe(bh.kann(spitz, 9.8, 118.0, reiben=True), "Ø 9,8 bohrt die Sackbohrung nicht vor")
pruefe(not bh.kann(durch, 10.0, 118.0, reiben=True), "Ø 10 bohrt vor")
pruefe(not bh.kann(durch, 9.4, 118.0, reiben=True), "Ø 9,4 bohrt vor")
pruefe(not bh.kann(durch, 9.8, 118.0), "Ø 9,8 ohne Reiben")
try:
    bh.passende(teil, [durch.name], 10.0, 118.0, reiben=True)
except ValueError as grund:
    pruefe("Ø 9.5 bis 9.85" in str(grund), f"Vorbohren: {grund}")
else:
    pruefe(False, "Vorbohren mit Ø 10: kein Satz")

liste = rbn.passende(teil, [durch.name, spitz.name], 10.0)
pruefe(len(liste) == 2, f"passende: {len(liste)}")
for titel, flaechen_, d, satz in (
    ("eben", [flach.name], 10.0, "ebenen Grund"),
    ("Ø 12", [durch.name], 12.0, "Reibahle Ø 12"),
):
    try:
        rbn.passende(teil, flaechen_, d)
    except ValueError as grund:
        pruefe(satz in str(grund), f"{titel}: {grund}")
    else:
        pruefe(False, f"{titel}: kein Satz")
pruefe(rbn.endtiefe(durch) == -1.0 and rbn.endtiefe(spitz) == 8.0, "Endtiefen")

bahn = rbn.planen(liste, 20.0, 25.0, 200.0)
pruefe(bahn.bohrungen == 2 and bahn.z_min == -1.0, f"{bahn.bohrungen} Bohrungen, {bahn.z_min}")
heraus = [
    (a, b)
    for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False)
    if not b.eilgang and b.z > a.z
]
pruefe(len(heraus) == 2 and all(b.z == 23.0 for _a, b in heraus), "nicht im Vorschub heraus")
print(ascii(f"Zeit {bahn.zeit:.2f} min"))

# --- Die Operation im Job -----------------------------------------------------------------------
import Path.Main.Job as PathJob

reibahle = wz.Werkzeug(
    nummer=4,
    name="Reibahle 10",
    art=wz.REIBAHLE,
    durchmesser=10.0,
    schneiden=6,
    schneidenlaenge=30.0,
    schneidstoff=wz.VHM,
)
reibahle.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.REIBEN, vc=20.0, fz=0.05)]
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([wz.standardwerkzeug(), reibahle]))
doc = FreeCAD.newDocument("Reiben")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
tc = js.controller_ohne_transaktion(doc, job, reibahle, reibahle.schnittwerte[wz.ALLE][0])
doc.recompute()
op = rbn.lege_an(job, tc, [durch.name, spitz.name])
doc.recompute()
ops = [o for o in job.Operations.Group if rbn.ist_reiben(o)]
pruefe(len(ops) == 2, f"Operationen: {[o.Label for o in job.Operations.Group]}")
pruefe(op.Label == "Reiben T4", f"Name {op.Label}")
tiefen = sorted(round(float(o.FinalDepth), 6) for o in ops)
pruefe(tiefen == [-1.0, 8.0], f"Endtiefen {tiefen}")
pruefe(all("G85" in [c.Name for c in o.Path.Commands] for o in ops), "kein G85")
pruefe(js.operationsart(op) == "Drilling", f"Art {js.operationsart(op)}")
pruefe(wz.REIBEN in js.EINSATZ_NACH_OPERATION["Drilling"], "Einsatz Reiben fehlt")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
