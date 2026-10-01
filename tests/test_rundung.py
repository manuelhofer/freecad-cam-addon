# Prüft „Verrunden“ beim „Entgraten“ (W-006 4.1 Punkt 8): Platte 70 × 40 × 10 mit einem Zapfen
# 20 × 20 × 10 bei (10…30, 10…30) und einem runden Zapfen Ø 16 × 10 bei (50, 20), beide oben mit
# einer Rundung R 2 gezeichnet (FreeCADs Verrundung: vier Zylinder und ein Torus). Ein
# Radienfräser Ø 10 mit R 2 (Führung Ø 6, ein ganzer Viertelkreis): die Spitze auf z 18, die
# Achse 3 neben der Wand; im Quader liegt die Hohlkehle auf der Rundung (nichts ins Teil, nichts
# stehen geblieben). Ein Radienfräser R 1 und ein Fasenfräser bekommen einen Satz, ein Radienfräser
# mit zu breiter Führung auch. An einem Zapfen ohne Rundung rundet er die scharfe Kante mit R 2.
# Dann die Operation im Job: Endtiefe 18, Art „entgraten“.
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


def radienfraeser(nummer, profil, fuehrung=0.0):
    w = wz.Werkzeug(
        nummer=nummer,
        name=f"R{profil:g}",
        art=wz.RADIENFRAESER,
        durchmesser=10.0,
        schneiden=3,
        profilradius=profil,
        spitzen_d=fuehrung,
        schneidstoff=wz.VHM,
    )
    w.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.VERRUNDEN, vc=100.0, fz=0.04)]
    return w


r2 = radienfraeser(5, 2.0)
roh = Part.makeBox(70, 40, 10).fuse(Part.makeBox(20, 20, 10, V(10, 10, 10)))
roh = roh.fuse(Part.makeCylinder(8, 10, V(50, 20, 10))).removeSplitter()
oben = [
    k for k in roh.Edges if abs(k.BoundBox.ZMin - 20) < 1e-6 and abs(k.BoundBox.ZMax - 20) < 1e-6
]
teil = roh.makeFillet(2.0, oben)
index = {f.hashCode(): i for i, f in enumerate(teil.Faces)}
rund = [f"Face{i + 1}" for i in range(len(teil.Faces)) if eb._fase(teil, i, index) is not None]
pruefe(len(rund) == 5, f"Rundungen: {rund}")
pruefe(all(eb._fase(teil, int(n[4:]) - 1, index).radius == 2.0 for n in rund), "Radius nicht 2")

# --- Die Ketten ---------------------------------------------------------------------------------
ketten = eb.ketten(teil, rund)
pruefe(len(ketten) == 2, f"Ketten: {len(ketten)}")
for k in ketten:
    pruefe((k.z_kante, k.radius, k.winkel) == (20.0, 2.0, 0.0), f"Kette {k.z_kante} {k.radius}")
    pruefe(k.kontur.geschlossen, "Kette nicht geschlossen")

# --- Die Bahn -----------------------------------------------------------------------------------
form, winkel, fuehrung, profil = eg.schneide_des_werkzeugs(r2)
pruefe((winkel, fuehrung, profil) == (0.0, 6.0, 2.0), f"Radienfräser: {winkel} {fuehrung} {profil}")


def werte(form_, profil_, spitzenwinkel=0.0, spitze=6.0):
    return eb.Entgratwerte(
        form=form_,
        spitzenwinkel=spitzenwinkel,
        spitze=spitze,
        breite=0.3,
        tiefer=0.5,
        sicher=30.0,
        profilradius=profil_,
    )


netz_nah, netz_fern = eb.netze(teil, rund)
bahn = eb.planen(netz_nah, werte(form, 2.0), ketten, eb.SCHRITT, netz_fern)
pruefe((bahn.ketten, bahn.ausgelassen) == (2, 0), f"{bahn.ketten} Ketten, {bahn.ausgelassen} aus")
pruefe(abs(bahn.z_min - 18.0) < 1e-6, f"Spitze bei z {bahn.z_min}")
pruefe(bahn.modell == (("rundung", 2.0),), f"aus dem Modell: {bahn.modell}")
lage = [p for p in bahn.punkte if not p.eilgang and abs(p.z - 18.0) < 1e-6]
abstand = []
for p in lage:
    if 10 - 4 < p.x < 30 + 4 and 10 - 4 < p.y < 30 + 4:
        abstand.append(max(10 - p.x, p.x - 30, 10 - p.y, p.y - 30))
    elif math.hypot(p.x - 50, p.y - 20) < 13:
        abstand.append(math.hypot(p.x - 50, p.y - 20) - 8)
pruefe(abstand and abs(min(abstand) - 3.0) < 0.02, f"Achse neben der Wand: {min(abstand):.3f}")

# Falsche Fräser: R 1, ein Fasenfräser, eine zu breite Führung.
fase90 = wz.Werkzeug(
    nummer=3,
    name="Fase 90",
    art=wz.FASENFRAESER,
    durchmesser=10.0,
    schneiden=2,
    schneidenlaenge=5.0,
    spitzenwinkel=90.0,
    spitzen_d=0.0,
)
for titel, werkzeug, satzteil in (
    ("R 1", radienfraeser(6, 1.0), "braucht einen Radienfräser"),
    ("Fasenfräser", fase90, "braucht einen Radienfräser"),
):
    f_, w_, s_, p_ = eg.schneide_des_werkzeugs(werkzeug)
    try:
        eb.planen(netz_nah, werte(f_, p_, w_, s_), ketten, eb.SCHRITT, netz_fern)
    except ValueError as grund:
        pruefe(satzteil in str(grund), f"{titel}: {grund}")
    else:
        pruefe(False, f"{titel}: kein Satz")
try:
    eg.schneide_des_werkzeugs(radienfraeser(7, 2.0, fuehrung=8.0))
except ValueError as grund:
    pruefe("Viertelkreis" in str(grund), f"Führung zu breit: {grund}")
else:
    pruefe(False, "Führung zu breit: kein Satz")


# --- Im Quader: die Hohlkehle liegt auf der Rundung ---------------------------------------------
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


def quader_nach(bahn_):
    q = rm.Quader(0, 70, 0, 40, 0, 20, schritt=0.05)
    q.h[:] = 20.0
    punkte = fein(bahn_.punkte)
    for a, b in zip(punkte, punkte[1:], strict=False):
        q.fahre((a.x, a.y, a.z), (b.x, b.y, b.z), form)
    return q


def hoehe(q, x, y):
    i = int(np.argmin(np.abs(q.x - x)))
    j = int(np.argmin(np.abs(q.y - y)))
    return float(q.h[i, j])


quader = quader_nach(bahn)
# Quer über die Rundung an der Seite x = 30 des eckigen Zapfens und an der Seite des runden: s
# von der Wand nach innen, die Rundung hat dort 18 + √(4 − (2 − s)²).
for s in (0.4, 0.8, 1.2, 1.6, 1.9):
    soll = 18.0 + math.sqrt(4.0 - (2.0 - s) ** 2)
    eckig = hoehe(quader, 30 - s, 20)
    rund_ = hoehe(quader, 50 + 8 - s, 20)
    pruefe(abs(eckig - soll) < 0.08, f"eckig bei s {s}: {eckig:.3f}, soll {soll:.3f}")
    pruefe(abs(rund_ - soll) < 0.08, f"rund bei s {s}: {rund_:.3f}, soll {soll:.3f}")
pruefe(abs(hoehe(quader, 20, 20) - 20.0) < 1e-9, "Oberseite des Zapfens angeschnitten")
pruefe(abs(hoehe(quader, 35, 20) - 18.0) < 1e-9, "neben dem Zapfen nicht auf z 18")

# --- Eine scharfe Kante runden ------------------------------------------------------------------
scharf = Part.makeBox(70, 40, 10).fuse(Part.makeBox(20, 20, 10, V(10, 10, 10))).removeSplitter()
waende = [
    f"Face{i + 1}"
    for i, f in enumerate(scharf.Faces)
    if f.BoundBox.ZMin > 9.9 and f.BoundBox.ZMax - f.BoundBox.ZMin > 5
]
k_scharf = eb.ketten(scharf, waende)
n_nah, n_fern = eb.netze(scharf, waende)
gerundet = eb.planen(n_nah, werte(form, 2.0), k_scharf, eb.SCHRITT, n_fern)
pruefe(abs(gerundet.z_min - 18.0) < 1e-6 and gerundet.modell == (), f"scharf: {gerundet.z_min}")
q2 = quader_nach(gerundet)
for s in (0.4, 1.2, 1.9):
    soll = 18.0 + math.sqrt(4.0 - (2.0 - s) ** 2)
    pruefe(abs(hoehe(q2, 30 - s, 20) - soll) < 0.08, f"scharf gerundet bei s {s}")

# --- Die Operation im Job -----------------------------------------------------------------------
import Path.Main.Job as PathJob

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([wz.standardwerkzeug(), r2]))
doc = FreeCAD.newDocument("Rundung")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
tc = js.controller_ohne_transaktion(doc, job, r2, r2.schnittwerte[wz.ALLE][0])
doc.recompute()
op = eg.lege_an(job, tc, flaechen=rund)
doc.recompute()
pruefe(op.Label == "Entgraten T5" and op.Ketten == 2, f"{op.Label}, {op.Ketten} Ketten")
pruefe(abs(float(op.FinalDepth) - 18.0) < 1e-6, f"Endtiefe {float(op.FinalDepth)}")
pruefe(abs(eg.eindringtiefe(op) - 2.0) < 1e-9, f"Eindringtiefe {eg.eindringtiefe(op)}")
pruefe(js.operationsart(op) == "entgraten", f"Art {js.operationsart(op)}")
print(ascii(f"Operation: {len(op.Path.Commands)} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
