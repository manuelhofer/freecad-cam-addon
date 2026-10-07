# Prüft den Kern von 5 Achsen simultan (W-015 S1, Spezifikation Strategien 16): je Punkt der
# Bahn die Werkzeugachse → Rundachsen stetig, X, Y, Z ohne TCPM – an den drei 5-Achs-Beispielen
# (Tisch/Tisch A, C; Kopf/Tisch B, C; Kopf/Kopf). Zwei Bahnen: die Achse kippt in X von −20° über
# die Senkrechte (den Pol) auf +20°, während die Spitze 40 mm fährt; und die Achse läuft 25°
# geneigt auf einem Kegel um Z (120°), die Spitze steht. Nachgeprüft mit „Auf der Maschine
# prüfen“: Die Spitze steht am gedrehten Werkstück auf jedem Punkt der Bahn, die Werkzeugachse
# ist die gewünschte, keine Rundachse springt (höchstens 6° von Punkt zu Punkt). Ohne TCPM
# wandert die Spitze zwischen zwei Sätzen von der Geraden, wenn sich Rundachsen drehen: Das
# Programm setzt Punkte dazwischen, bis sie höchstens 0,005 mm daneben liegt.
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


def nahe_f(a, b):
    return abs(a - b) < 1e-6 * max(1.0, abs(b))


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
    # Beim G93-Umschreiben darf eine ursprüngliche Freifahrt nicht als Schnitt gelten.
    materialdaten = []
    probe = [
        si.Punkt(kippen[0].spitze, kippen[0].achse, eilgang=True),
        si.Punkt(kippen[10].spitze, kippen[10].achse, eilgang=True),
        si.Punkt(kippen[11].spitze, kippen[11].achse, vorschub=30.0),
    ]
    markiert = si.programm_ohne_tcpm(maschine, probe, g93=True, materialdaten=materialdaten)
    unveraendert = si.programm_ohne_tcpm(maschine, probe, g93=True)
    pruefe(
        [c.toGCode() for c in markiert] == [c.toGCode() for c in unveraendert],
        "Materialdaten ändern NC-Befehle",
    )
    pruefe(len(markiert) == len(materialdaten), "Materialdaten passen nicht zu NC-Sätzen")
    pruefe(
        any(c.Name == "G1" and daten[0] for c, daten in zip(markiert, materialdaten, strict=True)),
        "Umgeschriebener Eilgang nicht erhalten",
    )
    pruefe(
        any(not eil and feed == 30.0 for eil, feed in materialdaten),
        "Schnittvorschub nicht erhalten",
    )
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
        if bahn is kippen:
            # G93: je Satz 1 ÷ Zeit – die Spitze fährt 40 mm mit 10 mm/s, also 4 s (der erste
            # Satz ist der Anfang, im Eilgang). Ungeteilt jeder Satz F 10; verdichtet (die
            # Rundachse dreht 1° je mm) zusammen dieselben 4 s.
            eil = [si.Punkt(bahn[0].spitze, bahn[0].achse, eilgang=True)] + bahn[1:]
            ungeteilt = si.programm_ohne_tcpm(maschine, eil, g93=True, toleranz=None)
            pruefe(
                ungeteilt[0].Name == "G93" and ungeteilt[-1].Name == "G94"
                and all(nahe_f(c.Parameters["F"], 10.0) for c in ungeteilt[2:-1]),
                f"{name}: G93 {[c.toGCode() for c in ungeteilt[:4]]}",
            )  # fmt: skip
            g93 = si.programm_ohne_tcpm(maschine, eil, g93=True)
            summe = sum(1.0 / c.Parameters["F"] for c in g93[2:-1])
            pruefe(abs(summe - 4.0) < 1e-3, f"{name}: verdichtet {summe:.6f} s statt 4")
            op.Gcode = [c.toGCode() for c in g93]
            doc.recompute()
            fahrt = ab.abfahrt(p, job, null)
            dauer = fahrt.stationen[-1].zeit - fahrt.stationen[0].zeit
            pruefe(abs(dauer - 4.0) < 0.05, f"{name}: G93 dauert {dauer:.3f} s statt 4")
    FreeCAD.closeDocument(asm.Document.Name)

# Ohne TCPM fährt die Maschine zwischen zwei Sätzen jede Achse linear: Kippt die Achse in einem
# Satz von 20 mm um 40°, liegt die Spitze in seiner Mitte weit neben der Geraden. Verdichtet
# liegt sie in jedem Teilsatz – auch bei einem und drei Vierteln, unabhängig nachgerechnet –
# höchstens um die Toleranz daneben.


def neben_der_geraden(maschine, a, b, ra, rb, t):
    """Die Spitze am Werkstück beim Anteil t des Satzes a → b (Maschine linear, ohne TCPM): ihr
    Abstand von der Geraden a → b."""
    r = {k: ra[k] + t * (rb[k] - ra[k]) for k in ra}
    pa, pb = maschine.abbildung(ra).punkt(a.spitze), maschine.abbildung(rb).punkt(b.spitze)
    programm = V(*(u + t * (v - u) for u, v in zip(pa, pb, strict=True)))
    abb = maschine.abbildung(r)
    d = programm - V(*abb.b)
    spitze = V(*(sum(abb.a[k][i] * (d.x, d.y, d.z)[k] for k in range(3)) for i in range(3)))
    return spitze.distanceToLine(V(*a.spitze), V(*b.spitze) - V(*a.spitze))


s40 = math.sin(math.radians(20.0))
c40 = math.cos(math.radians(20.0))
gross = [
    si.Punkt((10.0, 20.0, 45.0), (-s40, 0.0, c40), vorschub=10.0),
    si.Punkt((30.0, 20.0, 45.0), (s40, 0.0, c40), vorschub=10.0),
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
    rund = si.rundachsen_entlang(maschine, [b.achse for b in gross])
    vorher = si.abweichung(maschine, gross[0], gross[1], rund[0], rund[1])
    dicht, dicht_rund = si.verdichtet(maschine, gross, rund)
    schlimmste = max(
        neben_der_geraden(maschine, a, b, ra, rb, t)
        for a, b, ra, rb in zip(dicht, dicht[1:], dicht_rund, dicht_rund[1:], strict=False)
        for t in (0.25, 0.5, 0.75)
    )
    print(f"{name}: ungeteilt {vorher:.3f} mm, verdichtet {len(dicht)} Punkte, {schlimmste:.4f} mm")
    pruefe(vorher > 0.1, f"{name}: ungeteilt nur {vorher:.4f} mm daneben")
    pruefe(
        len(dicht) > 2 and schlimmste <= si.TOLERANZ + 1e-6,
        f"{name}: verdichtet {len(dicht)} Punkte, bis {schlimmste:.4f} mm daneben",
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
