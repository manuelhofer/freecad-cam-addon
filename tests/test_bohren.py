# Prüft „Bohren“ aus dem Assistenten (W-006 S3g): FreeCADs Bohr-Operation mit einem Bohrer aus der
# Werkzeugverwaltung. Block 100 × 60 × 20 mit zwei durchgehenden Bohrungen Ø 20 bei (25, 30) und
# (50, 15), einer durchgehenden Ø 6 bei (50, 50) und einer Sackbohrung Ø 34 × 10 bei (75, 30).
# Die Spitze (Ø 20 bei 118°: 6,009 mm), die Hübe (tiefer als 3 × D: je 1 × D), welche Bohrungen
# ein Bohrer kann (gleicher Durchmesser, durchgehend – die Sackbohrung nicht, mit einem Satz),
# die Bewegungen des Zyklus und ihre Zeit – schneller als „Bohrung fräsen“ mit Manuels
# Standardfräser; dann FreeCADs Operation im Job: G81 für Ø 20 (die Spitze unter dem Grund, R über
# dem Rohteil), G83 mit Q 6 für Ø 6, „Bohren T2“, Art „Drilling“.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import pathlib
import tempfile

import FreeCAD
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import bohren as bh
from camaddon import bohrung_bahn as bb
from camaddon import job_schnittwerte as js
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
schruppen = next(e for e in fraeser.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)


def bohrer(nummer, d):
    w = wz.Werkzeug(
        nummer=nummer,
        name=f"HSS {d:g}",
        art=wz.BOHRER,
        durchmesser=d,
        schneiden=2,
        schneidenlaenge=8 * d,
        spitzenwinkel=118.0,
        schneidstoff=wz.HSS,
    )
    w.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.1)]
    return w


b20, b6 = bohrer(2, 20.0), bohrer(3, 6.0)

teil = Part.makeBox(100, 60, 20)
for r, x, y in ((10, 25, 30), (10, 50, 15), (3, 50, 50)):
    teil = teil.cut(Part.makeCylinder(r, 20, V(x, y, 0)))
teil = teil.cut(Part.makeCylinder(17, 10, V(75, 30, 10))).removeSplitter()
alle = bb.bohrungen(teil)
d20 = [b.name for b in alle if abs(b.radius - 10.0) < 1e-6]
d6 = [b.name for b in alle if abs(b.radius - 3.0) < 1e-6]
sack = [b.name for b in alle if not b.durch]
pruefe((len(d20), len(d6), len(sack)) == (2, 1, 1), f"Bohrungen: {d20}, {d6}, {sack}")

# --- Spitze und Hübe ----------------------------------------------------------------------------
pruefe(abs(bh.spitze(20.0, 118.0) - 10.0 / math.tan(math.radians(59.0))) < 1e-9, "Spitze")
pruefe(abs(bh.spitze(20.0, 118.0) - 6.009) < 0.001, f"Spitze Ø 20: {bh.spitze(20.0, 118.0)}")
pruefe(bh.hub_fuer(29.0, 20.0) == 0.0, "Ø 20, 29 tief: in einem Zug")
pruefe(bh.hub_fuer(26.0, 6.0) == 6.0, "Ø 6, 26 tief: je 6")
pruefe(bh.hub_fuer(26.0, 6.0, 4.0) == 4.0, "Hub von Hand")

# --- Welche Bohrungen ein Bohrer kann ---------------------------------------------------------
pruefe(len(bh.passende(teil, d20, 20.0)) == 2, "Ø 20 passt")
for namen, d, text, satzteil in (
    (sack, 34.0, "Sackbohrung", "ebenen Grund"),
    (d6, 20.0, "Ø 6 mit Ø 20", "Bohrung Ø 6 "),
    ([], 20.0, "keine", "Keine Bohrung"),
):
    try:
        bh.passende(teil, namen or ["Face999"], d)
    except ValueError as grund:
        pruefe(satzteil in str(grund).replace(",", "."), f"{text}: {grund}")
    else:
        pruefe(False, f"{text}: keine Fehlermeldung")

# --- Die Bewegungen des Zyklus und die Zeit ------------------------------------------------------
VF = 902.0
_n, vf_bohren, _senkrecht = js.werte(b20, b20.schnittwerte[wz.ALLE][0])
gebohrt = bh.planen(bh.passende(teil, d20, 20.0), 20.0, 118.0, 21.0, 26.0, vf_bohren)
pruefe(
    (gebohrt.bohrungen, gebohrt.hube) == (2, 2) and abs(gebohrt.z_min + 6.009) < 0.001,
    f"Ø 20: {gebohrt.bohrungen} Bohrungen, {gebohrt.hube} Hübe, z_min {gebohrt.z_min}",
)
vorschub = [p for p in gebohrt.punkte if not p.eilgang]
pruefe(
    len(vorschub) == 2 and all(p.eintauchen for p in vorschub),
    f"Ø 20: {len(vorschub)} Sätze im Vorschub",
)
r_ebene = {round(p.z, 6) for p in gebohrt.punkte if p.eilgang and p.z < 26.0}
pruefe(r_ebene == {24.0}, f"R: {r_ebene}")
fraesen = bb.planen(
    bb.Bohrwerte(
        6.0, schruppen.ap, schruppen.ae, 0.3, 21.0, 26.0,
        schneidenlaenge=fraeser.schneidenlaenge, eintauchwinkel=fraeser.eintauchwinkel,
        vorschub=VF, eintauchen=VF * 0.3,
    ),
    bb.bohrungen(teil, d20),
)  # fmt: skip
pruefe(
    gebohrt.zeit < fraesen.zeit,
    f"Bohren {gebohrt.zeit:.2f} min, Bohrung fräsen {fraesen.zeit:.2f} min",
)
print(f"Bohren {gebohrt.zeit:.2f} min, Bohrung fraesen {fraesen.zeit:.2f} min")
_n, vf6, _s = js.werte(b6, b6.schnittwerte[wz.ALLE][0])
tief = bh.planen(bh.passende(teil, d6, 6.0), 6.0, 118.0, 21.0, 26.0, vf6)
spitze6 = bh.spitze(6.0, 118.0)
soll = math.ceil((24.0 - (0.0 - spitze6)) / 6.0 - 1e-9)
pruefe(tief.hube == soll, f"Ø 6: {tief.hube} Hübe statt {soll}")
stufen = sorted({round(p.z, 3) for p in tief.punkte if not p.eilgang}, reverse=True)
pruefe(
    stufen[:2] == [18.0, 12.0] and abs(stufen[-1] + spitze6) < 1e-3,
    f"Ø 6: Tiefen {stufen}",
)
# Die Luft über dem Rohteil zählt nicht: Oberkante 16 – im Material 17,8 tief (< 3 × D) und in
# einem Zug, obwohl die Fahrt ab R (19) bis zur Spitze 20,8 lang ist.
flach = bh.planen(bh.passende(teil, d6, 6.0), 6.0, 118.0, 16.0, 21.0, vf6)
pruefe(flach.hube == 1, f"Ø 6 unter Oberkante 16: {flach.hube} Hübe statt 1")
print("Bahn ok")

# --- FreeCADs Operation im Job ------------------------------------------------------------------
import Path.Main.Job as PathJob

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([fraeser, b20, b6]))
doc = FreeCAD.newDocument("Bohren")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 1.0
doc.recompute()
klon = job.Model.Group[0]
im_job = bb.bohrungen(klon.Shape)
namen20 = [b.name for b in im_job if abs(b.radius - 10.0) < 1e-6]
namen6 = [b.name for b in im_job if abs(b.radius - 3.0) < 1e-6]
tc2 = js.controller_ohne_transaktion(doc, job, b20, b20.schnittwerte[wz.ALLE][0])
op = bh.lege_an(job, tc2, namen20)
doc.recompute()
pruefe(op.Label == "Bohren T2" and op in job.Operations.Group, f"{op.Label}")
pruefe(bh.ist_bohren(op) and js.operationsart(op) == "Drilling", f"Art: {js.operationsart(op)}")
zyklen = [c for c in op.Path.Commands if c.Name in ("G81", "G83")]
pruefe(
    len(zyklen) == 2 and all(c.Name == "G81" for c in zyklen),
    f"Ø 20: {[c.Name for c in zyklen]}",
)
pruefe(
    all(abs(c.Parameters["Z"] + 6.009) < 0.01 for c in zyklen),
    f"Z {[round(c.Parameters['Z'], 3) for c in zyklen]}",
)
pruefe(
    all(abs(c.Parameters["R"] - 24.0) < 1e-6 for c in zyklen),
    f"R {[c.Parameters['R'] for c in zyklen]}",
)
orte = sorted((round(c.Parameters["X"], 3), round(c.Parameters["Y"], 3)) for c in zyklen)
pruefe(orte == [(25.0, 30.0), (50.0, 15.0)], f"Orte {orte}")
tc3 = js.controller_ohne_transaktion(doc, job, b6, b6.schnittwerte[wz.ALLE][0])
op6 = bh.lege_an(job, tc3, namen6)
doc.recompute()
zyklen6 = [c for c in op6.Path.Commands if c.Name in ("G81", "G83")]
pruefe(
    len(zyklen6) == 1 and zyklen6[0].Name == "G83" and abs(zyklen6[0].Parameters["Q"] - 6.0) < 1e-6,
    f"Ø 6: {[(c.Name, c.Parameters.get('Q')) for c in zyklen6]}",
)
print(ascii(f"Operation: {[c.Name for c in op.Path.Commands]}"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
