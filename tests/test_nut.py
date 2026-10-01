# Prüft „Nut“ (W-006 4.1 Punkt 6): Platte 100 × 60 × 20 mit zwei Langlöchern – A 20 breit, 10
# tief, Halbkreise um (25, 20) und (55, 20); B 14 breit, durchgehend, um (25, 45) und (75, 45).
# Mit dem Standardfräser Ø 12 (ae 1,5, ap 25): A in Kreisen (Trochoide, Radius 10 − 6 − 0,3),
# B in voller Breite mit der Zickzack-Rampe (je Fahrt höchstens 3 tiefer, der Vorschub für den
# dicken Span gesenkt), beide zuletzt rundum an der Wand. Im Quader: die Nuten leer bis zum Grund
# (B 0,5 tiefer), daneben nichts angeschnitten; die Kreise im Gleichlauf (G3); von Kreis zu Kreis
# hinten weiter. Ein Fräser Ø 25 passt nicht, ein Ø 6 ist für A zu klein (ein Kern bliebe). Dann
# die Operation im Job: „Nut T1“, Endtiefe −0,5 (B durch), Art „nut“.
import math
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import bahn as bn
from camaddon import fraeserform as ff
from camaddon import job_schnittwerte as js
from camaddon import nut as nu
from camaddon import nut_bahn as nb
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")


def langloch(a, b, r, z0, hoehe):
    """Ein Langloch als Körper: Quader zwischen den Mittelpunkten und zwei Zylinder."""
    laenge = b[0] - a[0]
    koerper = Part.makeBox(laenge, 2 * r, hoehe, V(a[0], a[1] - r, z0))
    koerper = koerper.fuse(Part.makeCylinder(r, hoehe, V(a[0], a[1], z0)))
    return koerper.fuse(Part.makeCylinder(r, hoehe, V(b[0], b[1], z0)))


platte = Part.makeBox(100, 60, 20)
teil = platte.cut(langloch((25, 20), (55, 20), 10, 10, 11))
teil = teil.cut(langloch((25, 45), (75, 45), 7, -1, 22)).removeSplitter()

boden_a = next(
    f"Face{i + 1}"
    for i, f in enumerate(teil.Faces)
    if abs(f.BoundBox.ZMax - 10) < 1e-6 and abs(f.BoundBox.ZMin - 10) < 1e-6
)
wand_b = next(
    f"Face{i + 1}"
    for i, f in enumerate(teil.Faces)
    if isinstance(f.Surface, Part.Plane)
    and abs(f.BoundBox.YMin - 52) < 1e-6
    and abs(f.BoundBox.YMax - 52) < 1e-6
)
oberseite = next(
    f"Face{i + 1}" for i, f in enumerate(teil.Faces) if abs(f.BoundBox.ZMin - 20) < 1e-6
)

# --- Erkennung ----------------------------------------------------------------------------------
nuten_a = nb.nuten(teil, [boden_a])
pruefe(len(nuten_a) == 1, f"A: {len(nuten_a)} Nuten")
nut_a = nuten_a[0]
pruefe(
    {nut_a.a, nut_a.b} == {(25.0, 20.0), (55.0, 20.0)} and abs(nut_a.radius - 10) < 1e-9,
    f"A: {nut_a.a} {nut_a.b} r {nut_a.radius}",
)
pruefe((nut_a.z_oben, nut_a.z_unten, nut_a.durch) == (20.0, 10.0, False), f"A: {nut_a}")
nuten_b = nb.nuten(teil, [wand_b])
pruefe(len(nuten_b) == 1 and nuten_b[0].durch, f"B: {nuten_b}")
nut_b = nuten_b[0]
pruefe(abs(nut_b.radius - 7) < 1e-9 and nut_b.z_unten == 0.0, f"B: {nut_b}")
pruefe(not nb.ist_nut(teil, oberseite), "Oberseite als Nut erkannt")
pruefe(nb.ist_grund(teil, boden_a) and not nb.ist_grund(teil, wand_b), "Grund falsch")
beide = nb.nuten(teil, [boden_a, wand_b, boden_a])
pruefe(len(beide) == 2, f"beide: {len(beide)}")
# Eine Wand meint die ganze Nut (Assistent: Nut und Kontur treten so gegeneinander an).
ganz = nb.ganze_nuten(teil, [wand_b, oberseite, boden_a])
pruefe(
    ganz == [*nut_b.waende, oberseite, boden_a] and len(nut_b.waende) >= 4,
    f"ganze Nut: {ganz}",
)

# --- Die Bahn mit dem Standardfräser -------------------------------------------------------------
t1 = wz.standardwerkzeug()
form = ff.von_werkzeug(t1)
R = 6.0
pruefe(nb.verfahren(nut_a, R, 0.3) == "trochoide", "A nicht Trochoide")
pruefe(nb.verfahren(nut_b, R, 0.3) == "vollnut", "B nicht Vollnut")
pruefe(nb.verfahren(nut_a, 12.5) == "zu_schmal", "Ø 25 passt in A?")
pruefe(nb.verfahren(nut_a, 3.0, 0.3) == "zu_breit", "Ø 6 in A kein Kern?")


def werte(**weiter):
    grund = {
        "fraeser_radius": R,
        "zustellung": 25.0,
        "zeilenabstand": 1.5,
        "oben": 20.0,
        "sicher": 25.0,
        "aufmass": 0.3,
        "schneidenlaenge": 26.0,
        "eintauchwinkel": 3.0,
        "vorschub": 902.0,
        "eintauchen": 300.0,
    }
    grund.update(weiter)
    return nb.Nutwerte(**grund)


bahn = nb.planen(werte(), [nut_a, nut_b])
pruefe((bahn.nuten, bahn.vollnut) == (2, 1), f"{bahn.nuten} Nuten, {bahn.vollnut} Vollnut")
pruefe(abs(bahn.z_min + 0.5) < 1e-9, f"z_min {bahn.z_min}")
pruefe(bahn.lagen == 2, f"Lagen {bahn.lagen}")
# A: 30 lang, ae 1,5 – 20 Kreise vorwärts und einer unten an der Helix.
pruefe(bahn.kreise == 21, f"Kreise {bahn.kreise}")
print(ascii(f"Zeit {bahn.zeit:.2f} min, {bahn.laenge:.0f} mm, {bahn.kreise} Kreise"))

# Die Mitte des Fräsers bleibt in der Nut: höchstens r − R neben der Mittellinie.
punkte = bahn.punkte


def neben(p, nut):
    ax, ay = nut.a
    bx, by = nut.b
    t = ((p.x - ax) * (bx - ax) + (p.y - ay) * (by - ay)) / nut.laenge**2
    t = min(max(t, 0.0), 1.0)
    return math.hypot(p.x - ax - t * (bx - ax), p.y - ay - t * (by - ay))


for p in punkte:
    if p.eilgang or p.z > 19.999:
        continue
    nut = nut_a if p.y < 32 else nut_b
    pruefe(neben(p, nut) <= nut.radius - R + 1e-6, f"außerhalb der Nut: {p}")
# Gleichlauf: alle Bögen gegen den Uhrzeigersinn; Gegenlauf alle im Uhrzeigersinn.
boegen = [p.bogen[2] for p in punkte if p.bogen is not None]
pruefe(boegen and not any(boegen), "Bögen im Uhrzeigersinn bei Gleichlauf")
gegen = nb.planen(werte(gleichlauf=False), [nut_a])
pruefe(all(p.bogen[2] for p in gegen.punkte if p.bogen is not None), "Gegenlauf nicht G2")

# Von Kreis zu Kreis hinten weiter: die Geraden auf der Lage von A laufen in +x und liegen
# r_l hinter der Mitte des nächsten Kreises (im freien Raum).
r_l = 10 - R - 0.3
geraden = [
    (a, b)
    for a, b in zip(punkte, punkte[1:], strict=False)
    if not b.eilgang
    and b.bogen is None
    and abs(a.z - 10) < 1e-9
    and abs(b.z - 10) < 1e-9
    and a.y < 32
    and abs(b.y - 20) < 1e-9
    and abs(a.y - 20) < 1e-9
    and abs(b.x - a.x - 1.5) < 1e-6
]
pruefe(len(geraden) >= 19, f"Schritte hinten: {len(geraden)}")

# Vollnut B: je Fahrt höchstens 3 tiefer (min(ap, D/2) / 2), Vorschub für den dicken Span.
rampe = [
    (a, b)
    for a, b in zip(punkte, punkte[1:], strict=False)
    if not b.eilgang
    and b.bogen is None
    and abs(a.y - 45) < 1e-9
    and abs(b.y - 45) < 1e-9
    and abs(b.x - a.x) > 49
]
pruefe(rampe and all(a.z - b.z <= 3 + 1e-9 for a, b in rampe), "Rampe zu steil")
pruefe(
    all(abs(b.anteil - 2 * math.sqrt(0.125 * 0.875)) < 1e-9 for _a, b in rampe),
    f"Anteil {[b.anteil for _a, b in rampe][:2]}",
)
pruefe(min(b.z for _a, b in rampe) == -0.5, "Rampe nicht bis −0,5")


# --- Im Quader: die Nuten leer, daneben nichts angeschnitten ------------------------------------
def fein(punkte_):
    """Die Bögen in kurze Geraden – fahre() kennt nur Geraden."""
    ergebnis = [punkte_[0]]
    for a, b in zip(punkte_, punkte_[1:], strict=False):
        if b.bogen is None:
            ergebnis.append(b)
            continue
        mx, my, uhr = b.bogen
        r = math.hypot(a.x - mx, a.y - my)
        w0 = math.atan2(a.y - my, a.x - mx)
        weit = bn.winkel(a, b) * (-1 if uhr else 1)
        n = max(2, int(abs(weit) / math.radians(3)))
        for i in range(1, n + 1):
            w = w0 + weit * i / n
            z = a.z + (b.z - a.z) * i / n
            ergebnis.append(bn.Punkt(False, mx + r * math.cos(w), my + r * math.sin(w), z))
    return ergebnis


q = rm.Quader(0, 100, 0, 60, -1, 20, schritt=0.25)
q.h[:] = 20.0
fein_ = fein(punkte)
for a, b in zip(fein_, fein_[1:], strict=False):
    q.fahre((a.x, a.y, a.z), (b.x, b.y, b.z), form)
xs, ys = np.meshgrid(q.x, q.y, indexing="ij")


def abstand_nut(nut):
    ax, ay = nut.a
    bx, by = nut.b
    t = np.clip(((xs - ax) * (bx - ax) + (ys - ay) * (by - ay)) / nut.laenge**2, 0.0, 1.0)
    return np.hypot(xs - ax - t * (bx - ax), ys - ay - t * (by - ay))


for nut, grund in ((nut_a, 10.0), (nut_b, -0.5)):
    d = abstand_nut(nut)
    innen = d < nut.radius - 0.3  # bis aufs Aufmaß: dort muss alles weg sein
    pruefe(np.all(np.abs(q.h[innen] - grund) < 1e-6), f"Nut {nut.radius}: nicht leer")
    wand = (d > nut.radius - 0.2) & (d < nut.radius - 0.05)  # das Schlichten nahm das Aufmaß
    pruefe(np.all(q.h[wand] < grund + 1e-6), f"Nut {nut.radius}: Aufmaß an der Wand")
aussen = (abstand_nut(nut_a) > 10.05) & (abstand_nut(nut_b) > 7.05)
pruefe(np.all(q.h[aussen] >= 20.0 - 1e-9), "neben den Nuten angeschnitten")

# --- Werte, die nicht gehen ---------------------------------------------------------------------
for titel, w_, satz in (
    ("Ø 25", werte(fraeser_radius=12.5), "breit, der Fräser Ø 25"),
    ("Ø 6", werte(fraeser_radius=3.0), "bliebe ein Kern"),
):
    try:
        nb.planen(w_, [nut_a])
    except ValueError as grund:
        pruefe(satz in str(grund), f"{titel}: {grund}")
    else:
        pruefe(False, f"{titel}: kein Satz")

# --- Die Operation im Job -----------------------------------------------------------------------
import Path.Main.Job as PathJob

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([t1]))
doc = FreeCAD.newDocument("Nut")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
einsatz = next(e for e in t1.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
tc = js.controller_ohne_transaktion(doc, job, t1, einsatz)
doc.recompute()
op = nu.lege_an(job, tc, 25.0, 1.5, flaechen=[boden_a, wand_b])
doc.recompute()
pruefe(op.Label == "Nut T1" and op.Nuten == 2, f"{op.Label}, {op.Nuten} Nuten")
pruefe(abs(float(op.FinalDepth) + 0.5) < 1e-6, f"Endtiefe {float(op.FinalDepth)}")
pruefe(js.operationsart(op) == "nut", f"Art {js.operationsart(op)}")
pruefe(op.Kreise == 21 and op.Lagen == 2, f"Kreise {op.Kreise}, Lagen {op.Lagen}")
befehle = [c.Name for c in op.Path.Commands]
pruefe("G3" in befehle and "G2" not in befehle, "Bögen nicht G3")
print(ascii(f"Operation: {len(befehle)} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
