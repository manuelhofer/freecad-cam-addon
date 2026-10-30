# Prüft taschen_wahl: Welche Flächen gehören zur Vertiefung der gewählten (Manuel, 2026-10-30:
# „wenn ich jetzt da bloß zwei Wände anklicke, wie willst du die bearbeiten, ohne alles andere
# auch ein bisschen mit zu bearbeiten?“).
# 1. Block mit Tasche, Boden gerundet, oben am Rand gerundet, eine Insel: Eine Wand gewählt ergibt
#    Wände, Bodenrundungen, Boden und die Insel – nicht die Rundungen am oberen Rand, nicht die
#    Oberseite, nicht die Außenseiten.
# 2. Eine geloftete Tasche (B-Spline-Wände, wie Manuels Teil „tief“): zwei Wände ergeben alle
#    Wände und den Boden.
# 3. Die Oberseite allein bleibt allein; eine Außenseite auch.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402
import Part  # noqa: E402

from camaddon import taschen_wahl as tw  # noqa: E402

V = FreeCAD.Vector
fehler = []


def art(form, name):
    return form.Faces[int(name[4:]) - 1].Surface.__class__.__name__


# 1. Block mit Tasche
block = Part.makeBox(100, 80, 40).cut(Part.makeBox(60, 40, 15, V(20, 20, 25)))
boden_kanten = [
    e for e in block.Edges if abs(e.BoundBox.ZMin - 25) < 1e-6 and abs(e.BoundBox.ZMax - 25) < 1e-6
]
block = block.makeFillet(3, boden_kanten)
rand = [
    e
    for e in block.Edges
    if abs(e.BoundBox.ZMin - 40) < 1e-6
    and abs(e.BoundBox.ZMax - 40) < 1e-6
    and e.BoundBox.XMin > 10
    and e.BoundBox.XMax < 90
    and e.BoundBox.YMin > 10
    and e.BoundBox.YMax < 70
]
block = block.makeFillet(2, rand)
block = block.fuse(Part.makeCylinder(5, 10, V(50, 40, 25))).removeSplitter()
nb = tw.nachbarn(block)
wand = next(
    f"Face{i + 1}"
    for i, f in enumerate(block.Faces)
    if f.Surface.__class__.__name__ == "Plane"
    and abs(f.BoundBox.XMin - 80) < 1e-6
    and abs(f.BoundBox.XMax - 80) < 1e-6
)
ganz = tw.vertiefung(block, [wand], nb)
arten = sorted(art(block, n) for n in ganz)
oben = [
    f"Face{i + 1}"
    for i, f in enumerate(block.Faces)
    if abs(f.BoundBox.ZMin - 40) < 1e-6 and abs(f.BoundBox.ZMax - 40) < 1e-6
]
aussen = [
    f"Face{i + 1}"
    for i, f in enumerate(block.Faces)
    if f.BoundBox.XMax < 1e-6 or f.BoundBox.XMin > 100 - 1e-6
]
for n in ganz:
    f = block.Faces[int(n[4:]) - 1]
    if f.BoundBox.ZMax > 40 - 1.9 and art(block, n) != "Plane":
        fehler.append(f"Rundung am oberen Rand in der Tasche: {n} {art(block, n)}")
if set(ganz) & set(oben):
    fehler.append(f"Oberseite in der Tasche: {set(ganz) & set(oben)}")
if set(ganz) & set(aussen):
    fehler.append(f"Außenseite in der Tasche: {set(ganz) & set(aussen)}")
if arten.count("Plane") != 5 or "Cylinder" not in arten:
    fehler.append(f"Tasche: {ganz} {arten} – erwartet 4 Wände, Boden, Rundungen, Insel")
insel = [
    n
    for n in ganz
    if art(block, n) == "Cylinder" and abs(block.Faces[int(n[4:]) - 1].Surface.Radius - 5) < 1e-6
]
if not insel:
    fehler.append(f"die Insel fehlt: {ganz}")
if tw.fehlende(block, ganz, nb):
    fehler.append(f"die ganze Tasche gewählt, trotzdem fehlt: {tw.fehlende(block, ganz, nb)}")


# 2. Geloftete Tasche
def rechteck(b, h, z):
    ecken = [V(-b / 2, -h / 2, z), V(b / 2, -h / 2, z), V(b / 2, h / 2, z), V(-b / 2, h / 2, z)]
    return Part.Wire(Part.makePolygon([*ecken, ecken[0]]))


loft = Part.makeLoft([rechteck(30, 20, 5), rechteck(44, 34, 25), rechteck(40, 30, 45)], True)
freiform = Part.makeBox(80, 80, 40, V(-40, -40, 0)).cut(loft).removeSplitter()
nb = tw.nachbarn(freiform)
waende = [
    f"Face{i + 1}" for i, f in enumerate(freiform.Faces) if art(freiform, f"Face{i + 1}") != "Plane"
]
boden = [
    f"Face{i + 1}"
    for i, f in enumerate(freiform.Faces)
    if abs(f.BoundBox.ZMin - 5) < 1e-6 and abs(f.BoundBox.ZMax - 5) < 1e-6
]
ganz = tw.vertiefung(freiform, waende[:2], nb)
if sorted(ganz, key=lambda n: int(n[4:])) != sorted(waende + boden, key=lambda n: int(n[4:])):
    fehler.append(f"Freiform: {ganz} statt {waende + boden}")

# 3. Oberseite und Außenseite bleiben allein
oben = [
    f"Face{i + 1}"
    for i, f in enumerate(freiform.Faces)
    if abs(f.BoundBox.ZMin - 40) < 1e-6 and abs(f.BoundBox.ZMax - 40) < 1e-6
]
if tw.vertiefung(freiform, oben, nb) != oben:
    fehler.append(f"Oberseite: {tw.vertiefung(freiform, oben, nb)}")
seite = next(f"Face{i + 1}" for i, f in enumerate(freiform.Faces) if f.BoundBox.XMax < -40 + 1e-6)
if tw.fehlende(freiform, [seite], nb):
    fehler.append(f"Außenseite: {tw.fehlende(freiform, [seite], nb)}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
