# Prüft messen.py (Plan C3b): was ein Messtaster nach einem Schlichtgang misst.
# 1. Tasche 60 × 40 in einem Block, Ecken R 5, unten Rundungen R 3: Rechteck innen, Mitte (50, 40),
#    Messhöhe auf halber Wand (Oberkante 40, Boden 25 → 32,5).
# 2. Zapfen 30 × 20 auf einer Platte: Rechteck außen.
# 3. Bohrung Ø 20 und Welle Ø 16: rund, innen bzw. außen.
# 4. Soll nach einem Gang mit Aufmaß 1: Tasche 58 × 38, Bohrung 18, Zapfen 32 × 22, Welle 18.
# 5. Eine schräge Wand ergibt kein Merkmal, zwei Taschen nebeneinander auch nicht.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402
import Part  # noqa: E402

from camaddon import messen  # noqa: E402

V = FreeCAD.Vector
fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def namen(form, bedingung):
    return [f"Face{i + 1}" for i, f in enumerate(form.Faces) if bedingung(f)]


def senkrecht_wand(f):
    if f.Surface.__class__.__name__ == "Plane":
        u0, u1, v0, v1 = f.ParameterRange
        return abs(f.normalAt((u0 + u1) / 2, (v0 + v1) / 2).z) < 1e-6
    if f.Surface.__class__.__name__ == "Cylinder":
        return abs(abs(f.Surface.Axis.z) - 1) < 1e-6
    return False


# 1. Tasche
tasche = Part.makeBox(60, 40, 15, V(20, 20, 25))
kanten = [e for e in tasche.Edges if abs(e.BoundBox.ZLength - 15) < 1e-6]
tasche = tasche.makeFillet(5, kanten)
form = Part.makeBox(100, 80, 40).cut(tasche)
boden = [
    e for e in form.Edges if abs(e.BoundBox.ZMax - 25) < 1e-6 and abs(e.BoundBox.ZMin - 25) < 1e-6
]
form = form.makeFillet(3, boden)
wahl = namen(
    form,
    lambda f: f.BoundBox.ZMin > 24.9
    and f.BoundBox.XMin >= 20 - 1e-6
    and f.BoundBox.XMax <= 80 + 1e-6
    and f.BoundBox.YMin >= 20 - 1e-6
    and f.BoundBox.YMax <= 60 + 1e-6,
)
wahl_tasche = wahl
m = messen.merkmal(form, wahl)
print(m)
pruefe(
    m is not None
    and m.art == messen.TASCHE
    and abs(m.x - 50) < 1e-6
    and abs(m.y - 40) < 1e-6
    and abs(m.laenge_x - 60) < 1e-6
    and abs(m.laenge_y - 40) < 1e-6
    and abs(m.z_mess - 32.5) < 1e-6,
    f"Tasche: {m}",
)
s = messen.soll(m, 1.0)
pruefe(abs(s.laenge_x - 58) < 1e-6 and abs(s.laenge_y - 38) < 1e-6, f"Soll Tasche: {s}")

# 2. Zapfen
zapfen = Part.makeBox(100, 80, 10).fuse(Part.makeBox(30, 20, 15, V(35, 30, 10))).removeSplitter()
wahl = namen(zapfen, lambda f: senkrecht_wand(f) and f.BoundBox.ZMin > 9.9)
m = messen.merkmal(zapfen, wahl)
pruefe(m is not None and m.art == messen.ZAPFEN and abs(m.laenge_x - 30) < 1e-6, f"Zapfen: {m}")
s = messen.soll(m, 1.0)
pruefe(abs(s.laenge_x - 32) < 1e-6 and abs(s.laenge_y - 22) < 1e-6, f"Soll Zapfen: {s}")

# 3. Bohrung und Welle
gebohrt = Part.makeBox(100, 80, 40).cut(Part.makeCylinder(10, 20, V(50, 40, 20)))
wahl = wahl_bohrung = namen(gebohrt, lambda f: f.Surface.__class__.__name__ == "Cylinder")
m = messen.merkmal(gebohrt, wahl)
pruefe(
    m is not None and m.art == messen.BOHRUNG and abs(m.durchmesser - 20) < 1e-6,
    f"Bohrung: {m}",
)
pruefe(abs(messen.soll(m, 1.0).durchmesser - 18) < 1e-6, "Soll Bohrung")
welle = Part.makeBox(100, 80, 10).fuse(Part.makeCylinder(8, 20, V(50, 40, 10))).removeSplitter()
wahl = namen(welle, lambda f: f.Surface.__class__.__name__ == "Cylinder")
m = messen.merkmal(welle, wahl)
pruefe(m is not None and m.art == messen.WELLE and abs(m.durchmesser - 16) < 1e-6, f"Welle: {m}")
pruefe(abs(messen.soll(m, 1.0).durchmesser - 18) < 1e-6, "Soll Welle")

# 5. Schräge Wand
keil = Part.makeBox(100, 80, 40).cut(
    Part.makeBox(60, 40, 15, V(20, 20, 25)).rotated(V(50, 40, 30), V(0, 0, 1), 30)
)
wahl = namen(keil, lambda f: senkrecht_wand(f) and f.BoundBox.ZMin > 24.9)
pruefe(messen.merkmal(keil, wahl) is None, "schräge Tasche als Rechteck erkannt")

# Zwei Taschen nebeneinander: kein Rechteck über beide.
zwei = Part.makeBox(100, 80, 40).cut(Part.makeBox(30, 40, 15, V(10, 20, 25)))
zwei = zwei.cut(Part.makeBox(30, 40, 15, V(60, 20, 25)))
wahl = namen(zwei, lambda f: senkrecht_wand(f) and f.BoundBox.ZMin > 24.9)
pruefe(messen.merkmal(zwei, wahl) is None, "zwei Taschen als ein Rechteck")

# 6. Die Zeile im Messstopp: geschrieben und wieder gelesen dasselbe.
from camaddon import messstopp as ms  # noqa: E402

for m in (
    messen.soll(messen.merkmal(form, wahl_tasche), 1.0),
    messen.merkmal(gebohrt, wahl_bohrung),
):
    zeile = ms.merkmal_zeile(m, 0.02)
    zurueck, toleranz = ms.merkmal_von(["(MESSSTOPP)", zeile, "M0"])
    pruefe(
        zurueck.art == m.art
        and abs(zurueck.laenge_x - m.laenge_x) < 1e-3
        and abs(zurueck.durchmesser - m.durchmesser) < 1e-3
        and abs(zurueck.z_mess - m.z_mess) < 1e-3
        and abs(toleranz - 0.02) < 1e-9,
        f"Zeile {zeile} → {zurueck}",
    )
pruefe(ms.merkmal_von(["(MESSSTOPP)", "G0 Z45.000", "M0"]) is None, "ohne Zeile ein Merkmal")

# 7. Das Einrichtblatt sagt beim Messstopp, was zu messen ist (auch für das Messen von Hand).
from camaddon import einrichtblatt as eb  # noqa: E402
from camaddon import sprache  # noqa: E402

sprache.setze_sprache("de")


class Stopp:
    Gcode = [
        "(MESSSTOPP)",
        ms.merkmal_zeile(messen.soll(messen.merkmal(form, wahl_tasche), 1.0), 0.02),
        "M0",
    ]


satz = eb._messen_text(Stopp(), sprache.tr)
print(satz)
pruefe(satz.startswith("messen: Tasche 58") and "38" in satz and "±0" in satz, f"Blatt: {satz}")
Stopp.Gcode = ["(MESSSTOPP)", "M0"]
pruefe(eb._messen_text(Stopp(), sprache.tr) == "", "Blatt ohne Merkmal")

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
