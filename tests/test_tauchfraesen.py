# Prüft den Entwurf tauchfraesen (Plan C2): Tasche 150 × 100, 40 tief, Ecken R 10; Tauchfräser
# Ø 32, Aufmaß 0,5.
# 1. Jede Stelle liegt so, dass der Fräser die Wand nicht berührt (Abstand zur Kontur ≥ r + Aufmaß).
# 2. Nichts bleibt stehen außer Zwickeln: Jeder Punkt, den die Fräsermitte erreichen darf, liegt
#    höchstens r von einer Stelle entfernt.
# 3. Die Bahn: je Stelle Eilgang darüber, Eintauchen bis zum Boden, Eilgang hoch; die Zeit > 0.
# 4. Zu eng (Tasche schmaler als der Fräser): keine Stelle.
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

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
