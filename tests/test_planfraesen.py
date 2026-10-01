# Prüft „Planfräsen“ (W-006 S3b): Block 60 × 40 × 20 mit einem Absatz 5 mm höher an der
# linken Seite (x 0 … 10), Rohteil mit 1 mm Aufmaß rundum (Oberkante 26), Schaftfräser Ø 10,
# Zustellung 2, Zeilenabstand 4. Die Hüllfläche je Zeile (hoehenfeld) hält die Zeilen vor dem
# Absatz an; die Bahn: drei Lagen 24 → 22 → 20, Zeilen längs x hin und her, Halbkreise am
# freien Ende, Rampe ins Material, beim Austritt halber Vorschub; die Befehle mit G1, G2, G3
# und F; die Zeit. Dann die CAM-Operation im Job: angelegt (Tiefen und Höhen wie FreeCAD),
# gerechnet, geändert, auf den Absatz gestellt, gespeichert und geladen.
import math
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import bahn as bn
from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import job_schnittwerte as js
from camaddon import planfraesen as pf
from camaddon import planfraesen_bahn as pb
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_huelle as vh
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")

# --- Das Teil: Block mit Absatz; die ebenen Flächen nach oben --------------------------------
block = Part.makeBox(60, 40, 20).fuse(Part.makeBox(10, 40, 5, V(0, 0, 20))).removeSplitter()
ebenen = hf.ebenen_oben(block)
pruefe(len(ebenen) == 2, f"Ebenen nach oben: {[(e.name, e.z) for e in ebenen]}")
flaeche = next((e for e in ebenen if abs(e.z - 20.0) < 1e-6), None)
absatz = next((e for e in ebenen if abs(e.z - 25.0) < 1e-6), None)
pruefe(
    flaeche is not None
    and abs(flaeche.x_von - 10.0) < 1e-6
    and abs(flaeche.x_bis - 60.0) < 1e-6
    and abs(flaeche.y_von) < 1e-6
    and abs(flaeche.y_bis - 40.0) < 1e-6,
    f"die Fläche: {flaeche}",
)
pruefe(absatz is not None and abs(absatz.x_bis - 10.0) < 1e-6, f"der Absatz: {absatz}")
pruefe(hf.oberseite(block) == [absatz.name], f"Oberseite: {hf.oberseite(block)}")

# --- Die Hüllfläche je Zeile: vor dem Absatz hoch, über der Fläche frei, daneben nichts -------
netz = hf.netz_ohne(block, [flaeche.name])
form = ff.scheibe(5.0)
huelle = hf.je_zeile(netz, form, np.array([20.0]), 0.0, 0.5, 141)  # x 0 … 70 auf y = 20
z = huelle[:, 0]
x = 0.5 * np.arange(141)
pruefe(all(abs(z[i] - 25.0) < 1e-6 for i in range(141) if x[i] <= 15.0 - 1e-9), "vor dem Absatz")
# Über der Fläche (die im Netz fehlt) sieht die Stirn erst die Unterseite des Blocks bei 0.
pruefe(
    all(abs(z[i]) < 1e-6 for i in range(141) if 15.0 + 1e-9 < x[i] < 55.0 - 1e-9),
    f"über der Fläche: {[(x[i], z[i]) for i in range(141) if 15 < x[i] < 55][:3]}",
)
pruefe(all(not np.isfinite(z[i]) for i in range(141) if x[i] > 65.0 + 1e-9), "neben dem Teil")
# Die Seitenwand bei x = 60 ragt bis z = 20: unter der Lage 20 nicht im Weg, darüber frei.
rand = [z[i] for i in range(141) if 55.0 + 1e-9 < x[i] < 65.0 - 1e-9]
pruefe(all(abs(wert - 20.0) < 1e-6 for wert in rand), f"an der Seitenwand: {rand[:3]}")
# Zeilen längs y: dieselbe Hüllfläche quer.
# Längs y bei x = 5 liegt der Absatz unter der Stirn (25), bei x = 30 nur die Unterseite (0)
# – an den Enden der Fläche (y 0 und 40) die Seitenwände bis 20.
huelle_y = hf.je_zeile(netz, form, np.array([5.0, 30.0]), -10.0, 0.5, 121, laengs_x=False)
pruefe(
    all(abs(wert - 25.0) < 1e-6 for wert in huelle_y[20:101, 0])
    and all(abs(wert) < 1e-6 for wert in huelle_y[31:90, 1])
    and all(abs(wert - 20.0) < 1e-6 for wert in huelle_y[21:30, 1]),
    f"Zeilen längs y: {huelle_y[18:34, 1]}",
)
# Ein Teil unter z = 0: die Hüllfläche hebt es und senkt das Ergebnis wieder.
tief = Part.makeBox(20, 20, 10, V(0, 0, -30))
h_tief = hf.je_zeile(vh.vernetze(tief), form, np.array([10.0]), 5.0, 1.0, 11)
pruefe(all(abs(wert + 20.0) < 1e-6 for wert in h_tief[:, 0]), f"unter 0: {h_tief[:3, 0]}")
print("Huellflaeche ok")

# --- Die Bahn mit Bögen: Weg, Winkel, Befehle -------------------------------------------------
p0 = bn.Punkt(True, 0.0, 0.0, 10.0)
p1 = bn.Punkt(False, 0.0, 0.0, 0.0, True)
p2 = bn.Punkt(False, 30.0, 0.0, 0.0)
p3 = bn.Punkt(False, 30.0, 4.0, 0.0, bogen=(30.0, 2.0, False), anteil=0.5)
p4 = bn.Punkt(False, 0.0, 4.0, 0.0)
pruefe(abs(bn.weg(p2, p3) - 2 * math.pi) < 1e-9, f"Bogenlänge {bn.weg(p2, p3)}")
pruefe(abs(bn.winkel(p2, p3) - math.pi) < 1e-9, "Halbkreis")
pruefe(bn.im_uhrzeigersinn((30, 0), (30, 4), (32, 2)) is False, "gegen den Uhrzeigersinn")
pruefe(bn.im_uhrzeigersinn((30, 0), (30, 4), (28, 2)) is True, "im Uhrzeigersinn")
pruefe(abs(bn.laenge([p0, p1, p2, p3, p4]) - (10 + 30 + 2 * math.pi + 30)) < 1e-9, "Länge")
# Zeit: 10 mm Eintauchen mit 100, 30 mit 1000, der Bogen halb so schnell, 30 mit 1000.
zeit = bn.dauer([p0, p1, p2, p3, p4], 1000.0, 100.0)
pruefe(abs(zeit - (0.1 + 0.03 + 2 * math.pi / 500 + 0.03)) < 1e-9, f"Zeit {zeit}")
befehle = bn.befehle([p0, p1, p2, p3, p4], 1000.0, 100.0, "Probe")
namen = [b.Name for b in befehle]
pruefe(namen == ["(Probe)", "G0", "G0", "G1", "G1", "G3", "G1"], f"Befehle: {namen}")
bogen = befehle[5]
pruefe(
    abs(bogen.Parameters["I"]) < 1e-9
    and abs(bogen.Parameters["J"] - 2.0) < 1e-9
    and abs(bogen.Parameters["F"] - 1000.0 * 0.5 / 60.0) < 1e-9,
    f"G3: {bogen.Parameters}",
)
pruefe(abs(befehle[3].Parameters["F"] - 100.0 / 60.0) < 1e-9, "Eintauchvorschub")
print("Bahn ok")

# --- Planfräsen: drei Lagen, Zeilen vor dem Absatz, Halbkreise, Rampe, Austritt -------------
werte = pb.Planwerte(
    form=form,
    zustellung=2.0,
    zeilenabstand=4.0,
    aufmass=0.0,
    oben=26.0,
    sicher=31.0,
    rohteil=(-1.0, 61.0, -1.0, 41.0),
)
bahn = pb.planen(netz, werte, [flaeche])
pruefe((bahn.flaechen, bahn.lagen) == (1, 3), f"Flächen, Lagen: {bahn.flaechen}, {bahn.lagen}")
pruefe(bahn.zeilen == 30, f"Zeilen {bahn.zeilen}")  # 10 je Lage: 3 … 37, höchstens 4 auseinander
pruefe(abs(bahn.z_min - 20.0) < 1e-9, f"z_min {bahn.z_min}")
vorschub = [p for p in bahn.punkte if not p.eilgang]
hoehen = sorted({round(p.z, 6) for p in vorschub if not p.eintauchen and p.z <= 26.0})
pruefe(
    all(any(abs(h - lage) < 1e-6 for lage in (24.0, 22.0, 20.0)) or h > 24.0 for h in hoehen),
    f"Höhen: {hoehen[:8]}",
)
in_lage = [p for p in vorschub if any(abs(p.z - lage) < 1e-6 for lage in (24.0, 22.0, 20.0))]
pruefe(
    min(p.x for p in in_lage) >= 15.0 - 1e-6 and max(p.x for p in in_lage) <= 66.0 + 1e-6,
    f"x {min(p.x for p in in_lage)} … {max(p.x for p in in_lage)}",
)
pruefe(
    abs(min(p.y for p in in_lage) - 3.0) < 1e-6 and abs(max(p.y for p in in_lage) - 37.0) < 1e-6,
    f"y {min(p.y for p in in_lage)} … {max(p.y for p in in_lage)}",
)
boegen = [p for p in vorschub if p.bogen is not None]
pruefe(len(boegen) >= 12, f"Bögen: {len(boegen)}")  # je Lage am freien Ende (x = 66)
pruefe(all(abs(p.x - 66.0) < 1e-6 for p in boegen), "Bogen nicht am freien Ende")
pruefe(
    all(abs(math.hypot(p.x - p.bogen[0], p.y - p.bogen[1]) - 17.0 / 9.0) < 1e-6 for p in boegen),
    "Bogenradius ist nicht der halbe Zeilenabstand",
)
# Beim Austritt bei x = 61 − 5 = 56 bis 66 der halbe Vorschub.
langsam = [p for p in vorschub if p.anteil < 1.0]
pruefe(
    len(langsam) >= 15 and all(abs(p.x - 66.0) < 1e-6 for p in langsam),
    f"Austritt: {len(langsam)} Sätze, x {sorted({round(p.x, 3) for p in langsam})}",
)
knick = [p for p in vorschub if abs(p.x - 56.0) < 1e-6]
pruefe(len(knick) >= 15, f"der Punkt vor dem Austritt fehlt: {len(knick)}")
# Rampe: die erste Lage beginnt in der Luft (x = 66) senkrecht, die Zeile in der Mitte vor
# dem Absatz endet mit dem Schritt quer; wo es im Material anfängt, geht es über die Rampe.
eintauchen = [p for p in vorschub if p.eintauchen]
pruefe(len(eintauchen) >= 3, f"Eintauchen: {len(eintauchen)}")
start = bahn.punkte[0]
pruefe(
    start.eilgang and abs(start.z - 31.0) < 1e-9 and abs(start.x - 66.0) < 1e-6, f"Start {start}"
)
pruefe(bahn.punkte[-1].eilgang and abs(bahn.punkte[-1].z - 31.0) < 1e-9, "Ende nicht oben")
pruefe(bahn.laenge > 3 * 10 * 50.0, f"Länge {bahn.laenge}")
pruefe(bn.dauer(bahn.punkte, 1000.0) > 1.5, f"Zeit {bn.dauer(bahn.punkte, 1000.0)}")
befehle = bn.befehle(bahn.punkte, 1000.0, 200.0)
namen = {b.Name for b in befehle}
pruefe({"G0", "G1"} <= namen and ("G2" in namen or "G3" in namen), f"Befehle: {namen}")
print(ascii(f"Planfraesen: {len(bahn.punkte)} Punkte, {len(befehle)} Befehle"))

# Zeilen längs y, wenn die Fläche quer länger ist: das schmale Teil.
schmal = Part.makeBox(20, 60, 10)
oben_schmal = hf.ebenen_oben(schmal)
bahn_y = pb.planen(
    vh.vernetze(schmal),
    pb.Planwerte(form, 2.0, 4.0, 0.0, 12.0, 17.0, (-1.0, 21.0, -1.0, 61.0)),
    [e for e in oben_schmal if abs(e.z - 10.0) < 1e-6],
)
in_lage = [p for p in bahn_y.punkte if not p.eilgang and abs(p.z - 10.0) < 1e-6]
pruefe(
    min(p.y for p in in_lage) <= -6.0 + 1e-6 and max(p.y for p in in_lage) >= 66.0 - 1e-6,
    f"längs y: {min(p.y for p in in_lage)} … {max(p.y for p in in_lage)}",
)
pruefe(abs(bahn_y.z_min - 10.0) < 1e-9 and bahn_y.lagen == 1, "schmal: eine Lage")

# Fehler mit einem Satz: Kugel, Zeilenabstand zu groß, nichts über der Fläche, keine Fläche.
for werte_falsch, ebenen_falsch, text in (
    (pb.Planwerte(ff.kugel(5.0), 2.0, 4.0, 0.0, 26.0, 31.0, werte.rohteil), [flaeche], "Kugel"),
    (pb.Planwerte(form, 2.0, 12.0, 0.0, 26.0, 31.0, werte.rohteil), [flaeche], "Abstand"),
    (pb.Planwerte(form, 2.0, 4.0, 0.0, 20.0, 31.0, werte.rohteil), [flaeche], "nichts drüber"),
    (werte, [], "keine Fläche"),
):
    try:
        pb.planen(netz, werte_falsch, ebenen_falsch)
    except ValueError as grund:
        pruefe(len(str(grund)) > 10, f"{text}: kein Satz")
    else:
        pruefe(False, f"{text}: keine Fehlermeldung")

# --- Die CAM-Operation im Job ---------------------------------------------------------------
import Path.Main.Job as PathJob

schaft = wz.Werkzeug(nummer=1, durchmesser=10, schneiden=3, schneidenlaenge=20)
schaft.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.PLANEN, ae=4, ap=2, vc=120, fz=0.05)]
kugel = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)
kugel.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=6, vc=150, fz=0.04)]
ue.uebergeben(wz.Bibliothek([schaft, kugel]))

doc = FreeCAD.newDocument("Planfraesen")
doc.UndoMode = 1
teil = doc.addObject("Part::Feature", "Teil")
teil.Shape = block
doc.recompute()
job = PathJob.Create("Job", [teil])
tc1 = js.controller_ohne_transaktion(doc, job, schaft, schaft.einsaetze(wz.ALLE)[0])
tc2 = js.controller_ohne_transaktion(doc, job, kugel, kugel.einsaetze(wz.ALLE)[0])
doc.recompute()
pruefe(
    abs(job.Stock.Shape.BoundBox.ZMax - 26.0) < 1e-6,
    f"Rohteil oben {job.Stock.Shape.BoundBox.ZMax}",
)
klon = job.Model.Group[0]
flaeche_im_job = next(e.name for e in hf.ebenen_oben(klon.Shape) if abs(e.z - 20.0) < 1e-6)
absatz_im_job = next(e.name for e in hf.ebenen_oben(klon.Shape) if abs(e.z - 25.0) < 1e-6)

op = pf.lege_an(job, tc1, zustellung=2.0, zeilenabstand=4.0, flaechen=[flaeche_im_job])
doc.recompute()
pruefe(op.Label == "Planfräsen T1" and op in job.Operations.Group, f"{op.Label}")
pruefe(pf.ist_planfraesen(op), "Art")
pruefe(js.operationsart(op) == "planfraesen", f"Art: {js.operationsart(op)}")
pruefe(js.EINSATZ_NACH_OPERATION["planfraesen"][0] == wz.PLANEN, "Einsatz Planen")
pruefe(
    abs(float(op.StartDepth) - 26.0) < 1e-6 and abs(float(op.FinalDepth) - 20.0) < 1e-6,
    f"Tiefen {float(op.StartDepth)} … {float(op.FinalDepth)}",
)
pruefe(
    float(op.SafeHeight) > 26.0 and float(op.ClearanceHeight) > float(op.SafeHeight) - 1e-6, "Höhen"
)
pruefe(
    (op.Ebenen, op.Lagen, op.Zeilen) == (1, 3, 30),
    f"Operation: {op.Ebenen}, {op.Lagen}, {op.Zeilen}",
)
befehle = op.Path.Commands
namen = [b.Name for b in befehle]
pruefe(
    namen[1:4] == ["G0", "G0", "G0"] and namen[-1] == "G0", f"Befehle: {namen[:5]} … {namen[-1]}"
)
schnitte = [b for b in befehle if b.Name in ("G1", "G2", "G3")]
z_werte = sorted({round(b.Parameters["Z"], 6) for b in schnitte if "Z" in b.Parameters})
pruefe(min(z_werte) >= 20.0 - 1e-6 and 20.0 in z_werte and 22.0 in z_werte, f"Z {z_werte[:6]}")
pruefe(any(b.Name in ("G2", "G3") for b in schnitte), "keine Bögen in der Operation")
f_werte = sorted({round(b.Parameters["F"], 6) for b in schnitte if "F" in b.Parameters})
pruefe(len(f_werte) >= 2, f"F {f_werte}")
pruefe(op.getEditorMode("Lagen") == ["ReadOnly"], "Lagen änderbar")

# Ändern: eine Lage mehr mit 1,5 mm; der Absatz allein hat nur 1 mm drüber: eine Lage.
pf.aendere(op, tc1, zustellung=1.5, zeilenabstand=4.0, aufmass=0.0)
doc.recompute()
pruefe(op.Lagen == 4, f"geändert: {op.Lagen} Lagen")
pf.aendere(op, tc1, zustellung=2.0, zeilenabstand=4.0, aufmass=0.0, flaechen=[absatz_im_job])
doc.recompute()
pruefe((op.Ebenen, op.Lagen) == (1, 1), f"Absatz: {op.Ebenen}, {op.Lagen}")
pruefe(abs(float(op.FinalDepth) - 25.0) < 1e-6, f"Endtiefe am Absatz {float(op.FinalDepth)}")
x_werte = [b.Parameters["X"] for b in op.Path.Commands if b.Name == "G1" and "X" in b.Parameters]
pruefe(max(x_werte) <= 16.0 + 1e-6, f"Absatz: x bis {max(x_werte)}")
# Der Kugelfräser: ein Satz statt der Bahn.
pf.aendere(op, tc2, zustellung=2.0, zeilenabstand=3.0, aufmass=0.0, flaechen=[flaeche_im_job])
doc.recompute()
pruefe("ebener Stirn" in op.Path.Commands[1].Name, f"Kugelfräser: {op.Path.Commands[1].Name}")
pf.aendere(op, tc1, zustellung=2.0, zeilenabstand=4.0, aufmass=0.5, flaechen=[flaeche_im_job])
doc.recompute()
pruefe(abs(float(op.FinalDepth) - 20.5) < 1e-6 and op.Lagen == 3, "zurück mit Aufmaß")
# Ohne Flächen: die Oberseite des Teils – der Absatz.
pf.aendere(op, tc1, zustellung=2.0, zeilenabstand=4.0, aufmass=0.0, flaechen=[])
doc.recompute()
pruefe(abs(float(op.FinalDepth) - 25.0) < 1e-6 and op.Ebenen == 1, "ohne Wahl: die Oberseite")

# Speichern und Laden: dieselbe Bahn.
pf.aendere(op, tc1, zustellung=2.0, zeilenabstand=4.0, aufmass=0.0, flaechen=[flaeche_im_job])
doc.recompute()
anzahl = len(op.Path.Commands)
pfad = os.path.join(tempfile.mkdtemp(), "planfraesen.FCStd")
doc.saveAs(pfad)
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(pfad)
op = next(o for o in doc.Objects if pf.ist_planfraesen(o))
op.touch()
doc.recompute()
pruefe(len(op.Path.Commands) == anzahl, f"nach dem Laden {len(op.Path.Commands)} statt {anzahl}")
pruefe(op.getEditorMode("Zeilen") == ["ReadOnly"], "Zeilen nach dem Laden")
print(ascii(f"Operation: {anzahl} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
