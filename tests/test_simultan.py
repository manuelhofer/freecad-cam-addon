# Prüft den Kern von 5 Achsen simultan (W-015 S1, Spezifikation Strategien 16): je Punkt der
# Bahn die Werkzeugachse → Rundachsen stetig, X, Y, Z ohne TCPM – an den drei 5-Achs-Beispielen
# (Tisch/Tisch A, C; Kopf/Tisch B, C; Kopf/Kopf). Zwei Bahnen: die Achse kippt in X von −20° über
# die Senkrechte (den Pol) auf +20°, während die Spitze 40 mm fährt; und die Achse läuft 25°
# geneigt auf einem Kegel um Z (120°), die Spitze steht. Nachgeprüft mit „Auf der Maschine
# prüfen“: Die Spitze steht am gedrehten Werkstück auf jedem Punkt der Bahn, die Werkzeugachse
# ist die gewünschte, keine Rundachse springt (höchstens 6° von Punkt zu Punkt).
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import abfahren as ab
from camaddon import beispielmaschine, sprache
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import simultan as si

V = FreeCAD.Vector
fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")

import Path.Main.Job as PathJob  # noqa: E402
import Path.Op.Custom as PathCustom  # noqa: E402

doc = FreeCAD.newDocument("Simultan")
teil = doc.addObject("Part::Feature", "Block")
teil.Shape = Part.makeBox(60, 40, 30)
doc.recompute()
job = PathJob.Create("Job", [teil])
op = PathCustom.Create("Simultan")
doc.recompute()
null = rw.nullpunkt(job)

kippen = [
    si.Punkt(
        (10.0 + i, 20.0, 45.0),
        (math.sin(math.radians(i - 20.0)), 0.0, math.cos(math.radians(i - 20.0))),
        vorschub=10.0,
    )
    for i in range(41)
]
s25, c25 = math.sin(math.radians(25.0)), math.cos(math.radians(25.0))
kegel = [
    si.Punkt(
        (30.0, 20.0, 45.0),
        (s25 * math.cos(math.radians(3.0 * k)), s25 * math.sin(math.radians(3.0 * k)), c25),
        vorschub=10.0,
    )
    for k in range(41)
]

for bauplan in (
    beispielmaschine.fuenfachs_tisch_tisch,
    beispielmaschine.fuenfachs_kopf_tisch,
    beispielmaschine.fuenfachs_kopf_kopf,
):
    name = bauplan.__name__
    asm, ma = bauplan()
    p = rw.Pruefung(asm, ma)
    tc = op.ToolController
    maschine = sw.Maschine(p, p.werkzeugaufnahme(tc.ToolNumber), rw.einspannung(tc, None), null)
    for bahn_name, bahn in (("kippen", kippen), ("Kegel", kegel)):
        try:
            rund = si.rundachsen_entlang(maschine, [b.achse for b in bahn])
        except ValueError as grund:
            pruefe(False, f"{name}, {bahn_name}: {grund}")
            continue
        sprung = max(max(abs(b[k] - a[k]) for k in a) for a, b in zip(rund, rund[1:], strict=False))
        pruefe(sprung <= 6.0, f"{name}, {bahn_name}: eine Rundachse springt um {sprung:.1f}°")
        daneben = max(
            math.degrees(math.acos(min(1.0, maschine.richtung(r).dot(V(*b.achse).normalize()))))
            for r, b in zip(rund, bahn, strict=True)
        )
        pruefe(daneben < 1e-3, f"{name}, {bahn_name}: Werkzeugachse {daneben:.5f}° daneben")
        befehle = si.programm_ohne_tcpm(maschine, bahn)
        op.Gcode = [c.toGCode() for c in befehle]
        doc.recompute()
        fahrt = ab.abfahrt(p, job, null)
        punkte = [
            am
            for s, am in zip(fahrt.stationen, fahrt.am_werkstueck(), strict=True)
            if s.operation == 0
        ]
        weg = max(min(math.dist(b.spitze, am) for am in punkte) for b in bahn)
        pruefe(weg < 1e-4, f"{name}, {bahn_name}: die Spitze bis {weg:.5f} mm neben der Bahn")
        print(
            f"{name}, {bahn_name}: Sprung {sprung:.2f}°, Spitze {weg:.2e} mm, {rund[0]}…{rund[-1]}"
        )
    FreeCAD.closeDocument(asm.Document.Name)

# Ein Punkt, den die Maschine nicht treffen kann (unter den Tisch): der Satz, warum.
asm, ma = beispielmaschine.fuenfachs_tisch_tisch()
p = rw.Pruefung(asm, ma)
maschine = sw.Maschine(p, p.werkzeugaufnahme(1), 0.0, null)
try:
    si.rundachsen_entlang(maschine, [(0.0, 0.0, 1.0), (0.0, 0.0, -1.0)])
except ValueError as grund:
    pruefe("Punkt 2" in str(grund), f"unter den Tisch: {grund}")
else:
    pruefe(False, "unter den Tisch ohne Fehler")
FreeCAD.closeDocument(asm.Document.Name)
FreeCAD.closeDocument(doc.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
