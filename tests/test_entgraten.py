# Prüft „Entgraten“ im Quader (W-006 4.1 Punkt 8): ein Fasenfräser bricht Oberkanten mit einer
# Fase. Platte 100 × 60 × 10 mit einem Zapfen 30 × 20 × 10 oben bei (10…40, 20…40) und einer
# Tasche 30 × 20 × 5 bei (55…85, 20…40). Die Kanten (die Wände des Zapfens: ein Zug rundum auf
# z 20; die Oberseite der Platte: ihre Außenkanten und der Rand der Tasche, nicht der Fuß des
# Zapfens), die Lage der Bahn (90°-Fasenfräser Ø 10, spitz: Fase 0,5, Spitze 0,5 tiefer – die
# Achse 0,5 neben der Wand, z 19), Gleichlauf (um den Zapfen im Uhrzeigersinn, in der Tasche
# gegen ihn), tangential hinein, zu breite Fase mit einem Satz, zu niedrige Wand ausgelassen;
# dann die Operation im Job: „Entgraten T3“, Art „entgraten“, Endtiefe 19, und im Quader trägt
# der Kegel an der Kante genau die Fase ab.
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
fraeser = wz.standardwerkzeug()
fase = wz.Werkzeug(
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
fase.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=100.0, fz=0.05)]

platte = Part.makeBox(100, 60, 10)
teil = platte.fuse(Part.makeBox(30, 20, 10, V(10, 20, 10)))
teil = teil.cut(Part.makeBox(30, 20, 5, V(55, 20, 5))).removeSplitter()


def flaechen_wo(bedingung):
    namen = []
    for i, f in enumerate(teil.Faces):
        if bedingung(f):
            namen.append(f"Face{i + 1}")
    return namen


def senkrecht(f):
    bb = f.BoundBox
    return bb.ZMax - bb.ZMin > 1e-6


zapfen = flaechen_wo(
    lambda f: senkrecht(f)
    and f.BoundBox.ZMin > 9.9
    and f.BoundBox.XMin >= 9.9
    and f.BoundBox.XMax <= 40.1
)
oberseite = flaechen_wo(
    lambda f: not senkrecht(f)
    and abs(f.BoundBox.ZMax - 10) < 1e-6
    and f.BoundBox.XMax - f.BoundBox.XMin > 90
)
pruefe((len(zapfen), len(oberseite)) == (4, 1), f"Flächen: {zapfen}, {oberseite}")

# --- Kanten und Ketten --------------------------------------------------------------------------
um_zapfen = eb.ketten(teil, zapfen)
pruefe(
    len(um_zapfen) == 1
    and um_zapfen[0].kontur.geschlossen
    and abs(um_zapfen[0].z_kante - 20) < 1e-6
    and abs(um_zapfen[0].z_boden - 10) < 1e-6,
    f"Zapfen: {[(k.z_kante, k.z_boden, k.kontur.geschlossen) for k in um_zapfen]}",
)
oben = eb.ketten(teil, oberseite)
umfang = sorted(round(k.kontur.draht.Length, 3) for k in oben)
# Außen 2 · (100 + 60) = 320, der Rand der Tasche 2 · (30 + 20) = 100 – der Fuß des Zapfens
# nicht: Dort geht die Wand hinauf, keine Kante mit Grat.
pruefe(umfang == [100.0, 320.0], f"Oberseite: Umfänge {umfang}")
pruefe(all(abs(k.z_kante - 10) < 1e-6 for k in oben), "Oberseite: z 10")
pruefe(eb.hat_oberkanten(teil, zapfen[0]) and eb.hat_oberkanten(teil, oberseite[0]), "passt")
boden = flaechen_wo(lambda f: not senkrecht(f) and abs(f.BoundBox.ZMax - 5) < 1e-6)
pruefe(boden and not eb.hat_oberkanten(teil, boden[0]), "Taschenboden: keine Oberkante")

# --- Die Fase -----------------------------------------------------------------------------------
tiefe, tiefer, kegel = eb.masse(0.5, 0.5, 90.0, 0.0, 5.0)
pruefe(abs(tiefe - 0.5) < 1e-9 and abs(tiefer - 0.5) < 1e-9 and abs(kegel - 5.0) < 1e-9, "masse")
pruefe(abs(eb.abstand_zur_wand(0.5, 90.0, 0.0) - 0.5) < 1e-9, "Abstand 90°")
pruefe(
    abs(eb.abstand_zur_wand(0.5, 60.0, 1.0) - (0.5 + 0.5 * math.tan(math.radians(30)))) < 1e-9,
    "60°",
)
try:
    eb.masse(6.0, 0.5, 90.0, 0.0, 5.0)
except ValueError as grund:
    pruefe("höchstens 5 mm" in str(grund), f"zu breit: {grund}")
else:
    pruefe(False, "zu breit: keine Fehlermeldung")

# --- Die Bahn -----------------------------------------------------------------------------------
form = ff.von_werkzeug(fase)
werte = eb.Entgratwerte(form, 90.0, 0.0, 0.5, 0.5, sicher=26.0)
netz_nah, netz_fern = eb.netze(teil, zapfen)
bahn = eb.planen(netz_nah, werte, um_zapfen, netz_fern=netz_fern)
im_vorschub = [p for p in bahn.punkte if not p.eilgang]
lage = [p for p in im_vorschub if abs(p.z - 19.0) < 1e-6]
pruefe(
    (bahn.ketten, bahn.ausgelassen, bahn.bahnen) == (1, 0, 1) and abs(bahn.z_min - 19.0) < 1e-6,
    f"Zapfen: {bahn.ketten} Ketten, {bahn.ausgelassen} aus, {bahn.bahnen} Bahnen, z {bahn.z_min}",
)


def abstand_rechteck(x, y, x0, x1, y0, y1):
    dx = max(x0 - x, 0.0, x - x1)
    dy = max(y0 - y, 0.0, y - y1)
    return math.hypot(dx, dy)


# Die Bahn selbst (ohne Ein- und Ausfahren): genau 0,5 neben dem Zapfen.
nah = [abstand_rechteck(p.x, p.y, 10, 40, 20, 40) for p in lage]
pruefe(min(nah) > 0.5 - 1e-3, f"näher als 0,5 am Zapfen: {min(nah):.4f}")
auf_der_bahn = [d for d in nah if d < 0.5 + 1e-3]
pruefe(len(auf_der_bahn) >= 8, f"nur {len(auf_der_bahn)} Sätze auf der Bahn")
pruefe(any(p.bogen is not None for p in lage), "keine Bögen (Ecken, Einfahren)")


def flaeche(punkte):
    """Vorzeichen der Fläche des Linienzugs: > 0 gegen den Uhrzeigersinn."""
    x = np.array([p.x for p in punkte])
    y = np.array([p.y for p in punkte])
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


auf_bahn_punkte = [p for p, d in zip(lage, nah, strict=True) if d < 0.5 + 1e-3]
pruefe(flaeche(auf_bahn_punkte) < 0, "um den Zapfen nicht im Uhrzeigersinn (Gleichlauf)")
# Hinein senkrecht in der Luft neben dem Zapfen, dann tangential:
hinab = next(i for i, p in enumerate(bahn.punkte) if not p.eilgang)
start = bahn.punkte[hinab]
pruefe(
    abs(start.z - 19.0) < 1e-6 and abstand_rechteck(start.x, start.y, 10, 40, 20, 40) > 2.0,
    f"Eintauchen bei ({start.x:.2f}, {start.y:.2f}, {start.z:.2f})",
)
print(f"Zapfen: {len(bahn.punkte)} Saetze, {bahn.laenge:.1f} mm im Vorschub")

# Die Tasche: gegen den Uhrzeigersinn, 0,5 neben ihren Wänden, auf z 9.
werte_oben = eb.Entgratwerte(form, 90.0, 0.0, 0.5, 0.5, sicher=26.0)
netz_nah, netz_fern = eb.netze(teil, oberseite)
bahn_oben = eb.planen(netz_nah, werte_oben, oben, netz_fern=netz_fern)
pruefe(bahn_oben.ketten == 2, f"Oberseite: {bahn_oben.ketten} Ketten")
tasche = [
    p
    for p in bahn_oben.punkte
    if not p.eilgang and abs(p.z - 9.0) < 1e-6 and 55 < p.x < 85 and 20 < p.y < 40
]
innen = [min(p.x - 55, 85 - p.x, p.y - 20, 40 - p.y) for p in tasche]
pruefe(innen and min(innen) > 0.5 - 1e-3, f"Tasche: {min(innen) if innen else None}")
auf_rand = [p for p, d in zip(tasche, innen, strict=True) if d < 0.5 + 1e-3]
pruefe(len(auf_rand) >= 4 and flaeche(auf_rand) > 0, "Tasche: nicht gegen den Uhrzeigersinn")

# Zu niedrige Wand: Fase 6 mm an der Tasche (5 tief) mit einem Ø 20 – die Kette bleibt aus.
gross = ff.kegel(0.0, 10.0, 10.0)
werte_tief = eb.Entgratwerte(gross, 90.0, 0.0, 6.0, 0.5, sicher=26.0)
tasche_kette = [k for k in oben if round(k.kontur.draht.Length, 3) == 100.0]
try:
    eb.planen(netz_nah, werte_tief, tasche_kette, netz_fern=netz_fern)
except ValueError as grund:
    pruefe("niedriger als die Fase" in str(grund), f"zu niedrig: {grund}")
else:
    pruefe(False, "zu niedrig: keine Fehlermeldung")

# --- Im Quader: der Kegel trägt an der Kante genau die Fase ab ----------------------------------
quader = rm.Quader(0, 100, 0, 60, 0, 20, schritt=0.1)
quader.h[:] = 10.0
im_zapfen = (
    (quader.x[:, None] >= 10)
    & (quader.x[:, None] <= 40)
    & (quader.y[None, :] >= 20)
    & (quader.y[None, :] <= 40)
)
quader.h[im_zapfen] = 20.0
vorschub = [p for p in bahn.punkte if not p.eilgang]
quader.fahre_stuecke(
    [(a.x, a.y, a.z) for a in vorschub[:-1]], [(b.x, b.y, b.z) for b in vorschub[1:]], form
)
# Mitten auf der Längsseite y = 40 des Zapfens: x = 25, von innen nach außen.
i = int(np.argmin(np.abs(quader.x - 25.0)))
for y_soll, z_soll in ((39.0, 20.0), (39.7, 19.8), (39.9, 19.6)):
    j = int(np.argmin(np.abs(quader.y - y_soll)))
    pruefe(abs(quader.h[i, j] - z_soll) < 0.06, f"Fase bei y {y_soll}: {quader.h[i, j]:.3f}")

# --- Die Operation im Job -----------------------------------------------------------------------
import Path.Main.Job as PathJob

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([fraeser, fase]))
doc = FreeCAD.newDocument("Entgraten")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 1.0
doc.recompute()
tc = js.controller_ohne_transaktion(doc, job, fase, fase.schnittwerte[wz.ALLE][0])
doc.recompute()
op = eg.lege_an(job, tc, 0.5, 0.5, flaechen=zapfen)
doc.recompute()
pruefe(op.Label == "Entgraten T3" and op in job.Operations.Group, f"{op.Label}")
pruefe(js.operationsart(op) == "entgraten", f"Art {js.operationsart(op)}")
pruefe(abs(float(op.FinalDepth) - 19.0) < 1e-6, f"Endtiefe {op.FinalDepth}")
pruefe(op.Ketten == 1 and op.Ausgelassen == 0, f"Ketten {op.Ketten}, aus {op.Ausgelassen}")
befehle = [c for c in op.Path.Commands if c.Name in ("G1", "G2", "G3")]
pruefe(any(c.Name in ("G2", "G3") for c in befehle), "keine Bögen im Programm")
pruefe(
    all(
        abs(c.Parameters.get("Z", 19.0) - 19.0) < 1e-6 or c.Parameters.get("Z", 0) > 19
        for c in befehle
    ),
    "Vorschub unter z 19",
)
pruefe(abs(eg.eindringtiefe(op) - 1.0) < 1e-9, f"Eindringtiefe {eg.eindringtiefe(op)}")
print(ascii(f"Operation: {len(op.Path.Commands)} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
