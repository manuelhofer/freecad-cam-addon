# Prüft gleiche_flaechen.py (Manuel, 2026-10-16: die Radien unten nicht einzeln anklicken müssen):
# ein Klotz 100 × 80 × 30 mit einer Tasche 60 × 40 × 10, ihre senkrechten Ecken R 6, ihr Boden
# rundum R 2, die oberen Kanten des Klotzes mit 1 mm Fase. Eine Kehle am Boden angeklickt: die
# anderen Kehlen (liegende Zylinder und Tori, alle R 2 auf derselben Höhe) – nicht die Eckradien
# R 6; ein Eckradius: die drei anderen; eine Fase: die drei anderen; der Taschenboden: keiner
# (der einzige auf −… ); die Oberseite: keine.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402
import Part  # noqa: E402

from camaddon import gleiche_flaechen as gf  # noqa: E402

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
klotz = Part.makeBox(100, 80, 30)
klotz = klotz.makeChamfer(1.0, [k for k in klotz.Edges if abs(k.BoundBox.ZMin - 30) < 1e-6])
tasche = Part.makeBox(60, 40, 10, V(20, 20, 20))
tasche = tasche.makeFillet(6.0, [k for k in tasche.Edges if k.BoundBox.ZLength > 1e-6])
tasche = tasche.makeFillet(2.0, [k for k in tasche.Edges if abs(k.BoundBox.ZMax - 20) < 1e-6])
teil = klotz.cut(tasche)
pruefe(teil.isValid(), "Teil ungültig")


def namen(art_):
    return [f"Face{k + 1}" for k, f in enumerate(teil.Faces) if (a := gf.art(f)) and a.art == art_]


kehlen = namen(gf.RUNDUNG)
ecken = namen(gf.ECKRADIUS)
fasen = namen(gf.FASE)
boeden = namen(gf.BODEN)
pruefe(len(kehlen) == 8, f"Kehlen am Boden: {len(kehlen)} (4 liegende Zylinder, 4 Tori)")
pruefe(len(ecken) == 4, f"Eckradien: {len(ecken)}")
pruefe(len(fasen) == 4, f"Fasen: {len(fasen)}")
pruefe(len(boeden) == 2, f"Böden: {len(boeden)} (oben und Taschenboden)")

a, andere = gf.gleiche(teil, kehlen[0])
pruefe(a is not None and abs(a.mass - 2) < 1e-6, f"Kehle: {a}")
pruefe(sorted(andere) == sorted(kehlen[1:]), f"gleiche Kehlen: {andere} statt {kehlen[1:]}")
a, andere = gf.gleiche(teil, ecken[0])
pruefe(a.art == gf.ECKRADIUS and abs(a.mass - 6) < 1e-6, f"Eckradius: {a}")
pruefe(sorted(andere) == sorted(ecken[1:]), f"gleiche Eckradien: {andere}")
a, andere = gf.gleiche(teil, fasen[0])
pruefe(abs(a.mass - 45) < 0.01, f"Fase: {a}")
pruefe(sorted(andere) == sorted(fasen[1:]), f"gleiche Fasen: {andere}")
for boden in boeden:
    a, andere = gf.gleiche(teil, boden)
    pruefe(a.art == gf.BODEN and andere == [], f"Boden {boden}: {a}, {andere}")
pruefe(gf.gleiche(teil, "Face999") == (None, []), "Fläche, die es nicht gibt")
pruefe(gf.gleiche(teil, "Edge1") == (None, []), "eine Kante")
# Zwei Taschenböden auf derselben Höhe: der andere ist gleich.
zweite = Part.makeBox(10, 10, 10, V(85, 5, 20))
zwei = teil.cut(zweite)
boden_namen = [
    f"Face{k + 1}"
    for k, f in enumerate(zwei.Faces)
    if (a := gf.art(f)) and a.art == gf.BODEN and abs(a.mass - 20) < 1e-6
]
pruefe(len(boden_namen) == 2, f"zwei Böden auf 20: {boden_namen}")
if len(boden_namen) == 2:
    pruefe(gf.gleiche(zwei, boden_namen[0])[1] == [boden_namen[1]], "der andere Boden")

print()
if fehler:
    print("FEHLER test_gleiche_flaechen:")
    for f in fehler:
        print("  -", f)
else:
    print("OK test_gleiche_flaechen")
