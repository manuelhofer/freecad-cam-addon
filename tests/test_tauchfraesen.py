# Prüft den Entwurf tauchfraesen (Plan C2): Tasche 150 × 100, 40 tief, Ecken R 10; Tauchfräser
# Ø 32, Aufmaß 0,5.
# 1. Jede Stelle liegt so, dass der Fräser die Wand nicht berührt (Abstand zur Kontur ≥ r + Aufmaß).
# 2. Nichts bleibt stehen außer Zwickeln: Jeder Punkt, den die Fräsermitte erreichen darf, liegt
#    höchstens r von einer Stelle entfernt.
# 3. Die Bahn: je Stelle Eilgang darüber, Eintauchen bis zum Boden, Eilgang hoch; die Zeit > 0.
# 4. Zu eng (Tasche schmaler als der Fräser): keine Stelle.
# 5. Reihenfolge von innen nach außen: die erste Stelle an der Mitte, jede weitere höchstens einen
#    Rasterschritt (+ Spiel) vom schon Offenen.
# 6. Die Operation im Job: Block 120 × 80 × 40, Tasche 80 × 50, 30 tief; Schaftfräser Ø 12 mit 20 mm
#    Schneide – zwei Lagen, die zweite im Eilgang bis knapp über die erste; jeder Vorschubsatz
#    senkrecht, keiner unter dem Boden; Art „tauchfraesen“ (Schnittwerte in den Job).
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402
import Part  # noqa: E402

from camaddon import tauchfraesen as tf  # noqa: E402

V = FreeCAD.Vector
fehler = []
r, aufmass = 16.0, 0.5

flaeche = Part.Face(
    Part.makePolygon([V(0, 0, 0), V(150, 0, 0), V(150, 100, 0), V(0, 100, 0), V(0, 0, 0)])
)
platte = flaeche.extrude(V(0, 0, 1))
platte = platte.makeFillet(10, [e for e in platte.Edges if abs(e.BoundBox.ZLength - 1) < 1e-6])
boden = next(f for f in platte.Faces if abs(f.BoundBox.ZMax) < 1e-6 and abs(f.BoundBox.ZMin) < 1e-6)
stellen = tf.stellen(boden, r, aufmass)
kontur = Part.Compound(boden.Edges)
for x, y in stellen:
    abstand = kontur.distToShape(Part.Vertex(V(x, y, 0)))[0]
    if abstand < r + aufmass - 1e-3:
        fehler.append(f"Stelle ({x:.1f}, {y:.1f}) zu nah an der Wand: {abstand:.2f}")
innen = boden.makeOffset2D(-(r + aufmass))
schlimmste = 0.0
x = innen.BoundBox.XMin
while x <= innen.BoundBox.XMax:
    y = innen.BoundBox.YMin
    while y <= innen.BoundBox.YMax:
        if innen.isInside(V(x, y, 0), 1e-6, True):
            schlimmste = max(schlimmste, min(math.hypot(x - a, y - b) for a, b in stellen))
        y += 2.0
    x += 2.0
if schlimmste > r + 1e-6:
    fehler.append(f"dort bliebe Material: {schlimmste:.2f} mm von der nächsten Stelle")
punkte = tf.bahn(stellen, 40.0, 0.5)
if len(punkte) != 3 * len(stellen) or not all(p.eintauchen for p in punkte[1::3]):
    fehler.append("Bahn nicht Eilgang – Eintauchen – Eilgang")
minuten = tf.zeit(punkte, 400.0)
print(
    f"Tauchfräsen: {len(stellen)} Stellen, {minuten:.1f} min, schlimmster Abstand {schlimmste:.1f}"
)
if not 0 < minuten < 60:
    fehler.append(f"Zeit {minuten}")
schmal = Part.Face(
    Part.makePolygon([V(0, 0, 0), V(20, 0, 0), V(20, 20, 0), V(0, 20, 0), V(0, 0, 0)])
)
if tf.stellen(schmal, r, aufmass):
    fehler.append("in einer zu engen Tasche Stellen")

erste = stellen[0]
if math.hypot(erste[0] - 75, erste[1] - 50) > 0.7 * 2 * r:
    fehler.append(f"erste Stelle nicht an der Mitte: {erste}")
for i in range(1, len(stellen)):
    abstand = min(math.hypot(stellen[i][0] - a, stellen[i][1] - b) for a, b in stellen[:i])
    if abstand > 0.7 * 2 * r * 1.05:
        fehler.append(f"Stelle {i + 1} nicht neben dem Offenen: {abstand:.1f}")

# --- 6. Die Operation im Job ---------------------------------------------------------------------
import pathlib  # noqa: E402
import tempfile  # noqa: E402

import Path.Main.Job as PathJob  # noqa: E402
from Path.Tool.camassets import user_asset_store  # noqa: E402

from camaddon import job_schnittwerte as js  # noqa: E402
from camaddon import sprache  # noqa: E402
from camaddon import uebergabe_werkzeuge as ue  # noqa: E402
from camaddon import werkzeuge as wz  # noqa: E402

sprache.setze_sprache("de")
teil = Part.makeBox(120, 80, 40).cut(Part.makeBox(80, 50, 30, V(20, 15, 10)))
boden_name = next(
    f"Face{i + 1}"
    for i, f in enumerate(teil.Faces)
    if abs(f.BoundBox.ZMax - 10) < 1e-6 and abs(f.BoundBox.ZMin - 10) < 1e-6
)
t1 = wz.standardwerkzeug()
t1.schneidenlaenge = 20.0
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([t1]))
doc = FreeCAD.newDocument("Tauch")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
einsatz = next(e for e in t1.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
tc = js.controller_ohne_transaktion(doc, job, t1, einsatz)
doc.recompute()
op = tf.lege_an(job, tc, [boden_name], aufmass=0.5, aufmass_boden=0.2)
doc.recompute()
print(f"Operation: {op.Label}, {op.Stellen} Stellen, {op.Lagen} Lagen")
if not (op.Label.startswith("Tauchfräsen T") and op.Stellen > 4 and op.Lagen == 2):
    fehler.append(f"Operation: {op.Label}, {op.Stellen} Stellen, {op.Lagen} Lagen")
if abs(float(op.FinalDepth) - 10.2) > 1e-6 or js.operationsart(op) != "tauchfraesen":
    fehler.append(f"Endtiefe {float(op.FinalDepth)}, Art {js.operationsart(op)}")
r12 = t1.durchmesser / 2
x0 = y0 = z0 = None
for befehl in op.Path.Commands:
    p = befehl.Parameters
    x, y, z = p.get("X", x0), p.get("Y", y0), p.get("Z", z0)
    if befehl.Name == "G1":
        if (x, y) != (x0, y0):
            fehler.append(f"Vorschub nicht senkrecht: {befehl.toGCode()}")
            break
        if z < 10.2 - 1e-6:
            fehler.append(f"unter dem Boden: {befehl.toGCode()}")
            break
        if not (20 + r12 + 0.5 - 1e-3 <= x <= 100 - r12 - 0.5 + 1e-3):
            fehler.append(f"an der Wand: {befehl.toGCode()}")
            break
    x0, y0, z0 = x, y, z
# 29,8 tief (Boden 10 + 0,2) in zwei Lagen: die erste bis 25,1, die zweite im Eilgang bis 26,1.
eilgang_tief = [
    c for c in op.Path.Commands if c.Name == "G0" and abs(c.Parameters.get("Z", 99) - 26.1) < 1e-6
]
if not eilgang_tief:
    fehler.append("zweite Lage nicht im Eilgang bis über die erste (Z 26,1)")
tf.aendere(op, tc, [boden_name], 0.5, 0.2, 12.0)
doc.recompute()
if float(op.Schritt) != 12.0 or op.Stellen <= 4:
    fehler.append(f"geändert: Schritt {float(op.Schritt)}, {op.Stellen} Stellen")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
