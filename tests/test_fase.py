# Prüft gezeichnete Fasen beim „Entgraten“ (W-006 4.1 Punkt 8): Platte 70 × 40 × 10 mit einem
# Zapfen 20 × 20 × 10 bei (10…30, 10…30) und einem runden Zapfen Ø 16 × 10 bei (50, 20), beide
# oben mit einer Fase 1 × 45° gezeichnet. Die schrägen Flächen sind Fasen (eben und Kegel), die
# Wände und die Oberseiten nicht; ihre Ketten liegen auf z 20 (dort läge die Kante ohne Fase),
# 1 mm breit, 45°; die Oberseite eines Zapfens bringt seine Fase mit. Mit dem 90°-Fasenfräser Ø 10
# (spitz) steht die Spitze 1,5 unter z 20, die Achse 0,5 neben der Wand; im Quader liegt der Kegel
# genau auf der Fase (nichts ins Teil, nichts stehen geblieben). Ein 60°-Fräser bekommt einen
# Satz. Dann die Operation im Job: zwei Kantenzüge, Endtiefe 18,5.
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
from camaddon import entgrat_bahn as eb
from camaddon import entgraten as eg
from camaddon import fraeserform as ff
from camaddon import job_schnittwerte as js
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
fase90 = wz.Werkzeug(
    nummer=3,
    name="Fase 90",
    art=wz.FASENFRAESER,
    durchmesser=10.0,
    schneiden=2,
    schneidenlaenge=5.0,
    spitzenwinkel=90.0,
    spitzen_d=0.0,
    schneidstoff=wz.VHM,
)
fase90.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=100.0, fz=0.05)]

teil = Part.makeBox(70, 40, 10).fuse(Part.makeBox(20, 20, 10, V(10, 10, 10)))
teil = teil.fuse(Part.makeCylinder(8, 10, V(50, 20, 10))).removeSplitter()
oben = [
    k for k in teil.Edges if abs(k.BoundBox.ZMin - 20) < 1e-6 and abs(k.BoundBox.ZMax - 20) < 1e-6
]
teil = teil.makeChamfer(1.0, oben)
schraeg = []
for i, f in enumerate(teil.Faces):
    u0, u1, v0, v1 = f.ParameterRange
    n = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    if 0.1 < n.z < 0.9:
        schraeg.append(f"Face{i + 1}")
pruefe(len(schraeg) == 5, f"schräge Flächen: {schraeg}")
pruefe(all(eb.ist_fase(teil, n) for n in schraeg), "nicht jede schräge Fläche ist eine Fase")
waende = [
    f"Face{i + 1}"
    for i, f in enumerate(teil.Faces)
    if f.BoundBox.ZMin > 9.9 and f.BoundBox.ZMax - f.BoundBox.ZMin > 5
]
pruefe(waende and not any(eb.ist_fase(teil, n) for n in waende), f"Wände als Fase: {waende}")
deckel = [
    f"Face{i + 1}"
    for i, f in enumerate(teil.Faces)
    if abs(f.BoundBox.ZMin - 20) < 1e-6 and abs(f.BoundBox.ZMax - 20) < 1e-6
]
pruefe(len(deckel) == 2 and all(eb.hat_fasen(teil, n) for n in deckel), f"Deckel: {deckel}")
pruefe(not any(eb.ist_fase(teil, n) for n in deckel), "Deckel als Fase")

# --- Die Ketten ---------------------------------------------------------------------------------
ketten = eb.ketten(teil, schraeg)
pruefe(len(ketten) == 2, f"Ketten: {len(ketten)}")
for k in ketten:
    pruefe(abs(k.z_kante - 20.0) < 1e-6 and abs(k.z_boden - 10.0) < 1e-6, f"Höhen {k}")
    pruefe(
        abs(k.breite - 1.0) < 1e-6 and abs(k.winkel - 45.0) < 1e-6, f"Fase {k.breite} {k.winkel}"
    )
    pruefe(k.kontur.geschlossen, "Kette nicht geschlossen")
pruefe(len(eb.ketten(teil, deckel[:1])) == 1, "die Oberseite bringt ihre Fase nicht mit")

# --- Die Bahn -----------------------------------------------------------------------------------
form = ff.von_werkzeug(fase90)
werte = eb.Entgratwerte(
    form=form, spitzenwinkel=90.0, spitze=0.0, breite=0.3, tiefer=0.5, sicher=30.0
)
netz_nah, netz_fern = eb.netze(teil, schraeg)
bahn = eb.planen(netz_nah, werte, ketten, eb.SCHRITT, netz_fern)
pruefe((bahn.ketten, bahn.ausgelassen) == (2, 0), f"{bahn.ketten} Ketten, {bahn.ausgelassen} aus")
pruefe(abs(bahn.z_min - 18.5) < 1e-6, f"Spitze bei z {bahn.z_min}")
pruefe(bahn.modell == (1.0,), f"Breiten aus dem Modell: {bahn.modell}")
vorschub = [p for p in bahn.punkte if not p.eilgang and abs(p.z - 18.5) < 1e-6]
abstand = []
for p in vorschub:
    if 10 - 1 < p.x < 30 + 1 and 10 - 1 < p.y < 30 + 1:
        abstand.append(max(10 - p.x, p.x - 30, 10 - p.y, p.y - 30))
    elif math.hypot(p.x - 50, p.y - 20) < 12:
        abstand.append(math.hypot(p.x - 50, p.y - 20) - 8)
pruefe(abstand and abs(min(abstand) - 0.5) < 0.02, f"Achse neben der Wand: {min(abstand):.3f}")

try:
    eb.planen(
        netz_nah,
        eb.Entgratwerte(
            form=form, spitzenwinkel=60.0, spitze=0.0, breite=0.3, tiefer=0.5, sicher=30
        ),
        ketten,
        eb.SCHRITT,
        netz_fern,
    )
except ValueError as grund:
    pruefe("90°" in str(grund) and "60°" in str(grund), f"60°: {grund}")
else:
    pruefe(False, "60°-Fräser an der 45°-Fase: kein Satz")


# --- Im Quader: der Kegel liegt auf der Fase ----------------------------------------------------
def fein(punkte):
    """Die Bögen in kurze Geraden – fahre() kennt nur Geraden."""
    ergebnis = [punkte[0]]
    for a, b in zip(punkte, punkte[1:], strict=False):
        if b.bogen is None:
            ergebnis.append(b)
            continue
        mx, my, uhr = b.bogen
        r = math.hypot(a.x - mx, a.y - my)
        w0 = math.atan2(a.y - my, a.x - mx)
        weit = bn.winkel(a, b) * (-1 if uhr else 1)
        n = max(2, int(abs(weit) / math.radians(2)))
        for i in range(1, n + 1):
            w = w0 + weit * i / n
            z = a.z + (b.z - a.z) * i / n
            ergebnis.append(bn.Punkt(False, mx + r * math.cos(w), my + r * math.sin(w), z))
    return ergebnis


quader = rm.Quader(0, 70, 0, 40, 0, 20, schritt=0.05)
quader.h[:] = 20.0
punkte = fein(bahn.punkte)
for a, b in zip(punkte, punkte[1:], strict=False):
    quader.fahre((a.x, a.y, a.z), (b.x, b.y, b.z), form)


def hoehe(x, y):
    i = int(np.argmin(np.abs(quader.x - x)))
    j = int(np.argmin(np.abs(quader.y - y)))
    return float(quader.h[i, j])


# Quer über die Fase an der Seite x = 30 des eckigen Zapfens und an der Seite des runden: Von der
# Wand (s = 0) zur Oberseite (s = 1) steigt sie von 19 auf 20.
for s in (0.1, 0.3, 0.5, 0.7, 0.9):
    eckig = hoehe(30 - s, 20)
    rund = hoehe(50 + 8 - s, 20)
    pruefe(abs(eckig - (19 + s)) < 0.06, f"eckig bei s {s}: {eckig:.3f}")
    pruefe(abs(rund - (19 + s)) < 0.06, f"rund bei s {s}: {rund:.3f}")
pruefe(abs(hoehe(20, 20) - 20.0) < 1e-9, "Oberseite des Zapfens angeschnitten")

# --- Die Operation im Job -----------------------------------------------------------------------
import Path.Main.Job as PathJob

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([wz.standardwerkzeug(), fase90]))
doc = FreeCAD.newDocument("Fase")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
tc = js.controller_ohne_transaktion(doc, job, fase90, fase90.schnittwerte[wz.ALLE][0])
doc.recompute()
op = eg.lege_an(job, tc, flaechen=schraeg)
doc.recompute()
pruefe(op.Label == "Entgraten T3" and op.Ketten == 2, f"{op.Label}, {op.Ketten} Ketten")
pruefe(abs(float(op.FinalDepth) - 18.5) < 1e-6, f"Endtiefe {float(op.FinalDepth)}")
print(ascii(f"Operation: {len(op.Path.Commands)} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
