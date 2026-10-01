# Prüft „Plan indexiert“ (W-003 Stufe V4c, W-006 S2): Welle Ø 20 mit einer Abflachung auf
# x = 8 zwischen zwei Wänden (a −30 … −10), Stange Ø 24, Schaftfräser Ø 6, Zustellung 2,
# Zeilenabstand 4 – die Rundachse steht auf 0°, drei Zeilen quer (Y) in zwei Lagen (Ø 24 →
# 10 → 8), die Zeilen enden vor den Wänden, hinein über die Rampe; die Befehle tragen Y und ein
# festes C. Der Abtrag (restmaterial) mit Versatz: über der Abflachung bleibt die Ebene x = 8,
# daneben die Stange; die Kugel versetzt trifft der Strahl, wo sie wirklich liegt. Dann die
# CAM-Operation im Job: angelegt, gerechnet (Ebenen, Lagen, Zeilen), geändert, gespeichert und
# geladen; ohne ebene Fläche oder mit Kugelfräser ein Satz statt einer Bahn.
import math
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import fraeserform as ff
from camaddon import job_schnittwerte as js
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_achsen as va
from camaddon import vierachs_bahn as vb
from camaddon import vierachs_operation as vo
from camaddon import vierachs_plan as vplan
from camaddon import vierachs_planbahn as vp
from camaddon import vierachs_rohteil as vr
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
LAENGS, RADIAL = (0, 0, 1), (1, 0, 0)

# --- Die Abflachung: eine ebene Fläche längs der Stange --------------------------------------
flach_welle = (
    Part.makeCylinder(10, 40, V(0, 0, -40))
    .cut(Part.makeBox(10, 30, 20, V(8, -15, -30)))
    .removeSplitter()
)
alle_namen = [f"Face{i + 1}" for i in range(len(flach_welle.Faces))]
abflachung = next(
    f"Face{i + 1}"
    for i, f in enumerate(flach_welle.Faces)
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-6
)
ebenen = vp.ebenen(flach_welle, LAENGS, RADIAL, alle_namen)
pruefe(len(ebenen) == 1 and ebenen[0].name == abflachung, f"Ebenen: {ebenen}")
if ebenen:
    e = ebenen[0]
    pruefe(abs(e.phi) < 1e-6 and abs(e.tiefe - 8.0) < 1e-6, f"Ebene: φ {e.phi}, Tiefe {e.tiefe}")
    pruefe(abs(e.a_von + 30) < 1e-6 and abs(e.a_bis + 10) < 1e-6, f"längs {e.a_von} … {e.a_bis}")
    pruefe(abs(e.q_von + 6) < 1e-3 and abs(e.q_bis - 6) < 1e-3, f"quer {e.q_von} … {e.q_bis}")
pruefe(vp.ebener_radius(ff.scheibe(3.0)) == 3.0, "ebener Radius der Scheibe")
pruefe(vp.ebener_radius(ff.torus(3.0, 1.0)) == 2.0, "ebener Radius des Torus")
pruefe(vp.ebener_radius(ff.kugel(3.0)) == 0.0, "ebener Radius der Kugel")

# --- Die Bahn: zwei Lagen, drei Zeilen, vor den Wänden halt, über die Rampe hinein ----------
netz = vp.netz_ohne(flach_welle, [abflachung])
werte = vp.Planwerte(
    form=ff.scheibe(3.0),
    stange_radius=12.0,
    zustellung=2.0,
    zeilenabstand=4.0,
    aufmass=0.0,
    a_stange_vorne=1.0,
    a_futter=-60.0,
)
bahn = vp.planen(netz, LAENGS, RADIAL, werte, ebenen)
pruefe(
    (bahn.flaechen, bahn.lagen, bahn.zeilen) == (1, 2, 6),
    f"Flächen, Lagen, Zeilen: {bahn.flaechen}, {bahn.lagen}, {bahn.zeilen}",
)
pruefe(abs(bahn.r_min - 8.0) < 1e-9, f"tiefste Spitze {bahn.r_min}")
start = bahn.punkte[0]
pruefe(start.eilgang and start.a == 1.0 + 3.0 + 2.0 and start.r == 14.0, f"Start: {start}")
vorschub = [p for p in bahn.punkte if not p.eilgang]
pruefe(all(abs(p.phi) < 1e-9 for p in vorschub), "die Rundachse steht nicht auf 0°")
q_soll = 6.0 - 3.0 - vb.TOLERANZ_SCHLICHTEN - vb.RAND - vp.LUFT
pruefe(
    all(abs(p.q) < 1e-9 or abs(abs(p.q) - q_soll) < 1e-6 for p in vorschub),
    f"Zeilen quer: {sorted({round(p.q, 3) for p in vorschub})}",
)
pruefe(all(8.0 - 1e-9 <= p.r <= 12.0 + 1e-9 for p in vorschub), "Spitze außerhalb 8 … 12")
pruefe(
    all(-27.0 - 1e-6 <= p.a <= -13.0 + 1e-6 for p in vorschub),
    f"längs über die Wände hinaus: {min(p.a for p in vorschub)} … {max(p.a for p in vorschub)}",
)
unten = [p for p in vorschub if abs(p.r - 8.0) < 1e-9]
pruefe(
    len(unten) >= 6 and min(p.a for p in unten) < -26.0 < -14.0 < max(p.a for p in unten), "unten"
)
rampen = 0
for vorher, punkt in zip(bahn.punkte, bahn.punkte[1:], strict=False):
    if vorher.eilgang and not punkt.eilgang:
        pruefe(punkt.eintauchen, f"hinein ohne Eintauchvorschub bei a {punkt.a:.2f}")
        rampen += punkt.r > 8.0 + 1e-9  # erst ans Material, dann die Rampe
pruefe(rampen >= 2, f"nur {rampen} Rampen")
pruefe(vb.dauer(bahn, 500.0) > 0.0, "keine Zeit")
befehle = vb.befehle(bahn, LAENGS, RADIAL, "C", 1, 500.0)
schnitte = [b for b in befehle if b.Name == "G1"]
pruefe(all("Y" in b.Parameters and "X" in b.Parameters for b in schnitte), "G1 ohne Y")
pruefe(all(abs(b.Parameters.get("C", 0.0)) < 1e-9 for b in schnitte), "C dreht")
pruefe(
    abs(max(b.Parameters["Y"] for b in schnitte) - q_soll) < 1e-6
    and abs(min(b.Parameters["Y"] for b in schnitte) + q_soll) < 1e-6,
    "Y nicht bis zum Rand",
)
print(ascii(f"Abflachung geplant: {len(bahn.punkte)} Punkte, {len(schnitte)} Saetze"))

# Ohne ebene Fläche, ohne ebene Stirn, Zeilenabstand zu groß: ein Satz.
for werte_falsch, flaechen_falsch, text in (
    (werte, [], "keine Fläche"),
    (vp.Planwerte(ff.kugel(3.0), 12.0, 2.0, 1.0, 0.0, 1.0, -60.0), ebenen, "Kugel"),
    (vp.Planwerte(ff.scheibe(3.0), 12.0, 2.0, 7.0, 0.0, 1.0, -60.0), ebenen, "Zeilenabstand"),
):
    try:
        vp.planen(netz, LAENGS, RADIAL, werte_falsch, flaechen_falsch)
    except ValueError as grund:
        pruefe(len(str(grund)) > 10, f"{text}: kein Satz")
    else:
        pruefe(False, f"{text}: keine Fehlermeldung")

# --- Der Abtrag mit Versatz quer (restmaterial) ----------------------------------------------
stange = rm.Stange(12.0, -60.0, 1.0)
von, nach = [], []
for vorher, punkt in zip(bahn.punkte, bahn.punkte[1:], strict=False):
    if not punkt.eilgang:
        von.append((vorher.a, vorher.r, vorher.phi, vorher.q))
        nach.append((punkt.a, punkt.r, punkt.phi, punkt.q))
stange.fahre_stuecke(von, nach, 3.0)
i20 = int(np.argmin(np.abs(stange.a + 20.0)))


def rest_bei(grad):
    return float(stange.r[i20, int(round(grad)) % len(stange.phi)])


for grad, soll in (
    (0, 8.0),
    (20, 8.0 / math.cos(math.radians(20))),
    (36, 8.0 / math.cos(math.radians(36))),
):
    pruefe(
        abs(rest_bei(grad) - soll) < 0.02,
        f"Rest bei {grad}°: {rest_bei(grad):.3f}, soll {soll:.3f}",
    )
pruefe(rest_bei(45) == 12.0, f"Rest bei 45°: {rest_bei(45)} – neben der Abflachung weggenommen")
pruefe(rest_bei(180) == 12.0, "gegenüber weggenommen")
i33 = int(np.argmin(np.abs(stange.a + 33.0)))
pruefe(float(stange.r[i33, 0]) == 12.0, f"hinter der Wand weggenommen: {stange.r[i33, 0]}")

# Die Kugel um 2 quer versetzt: Der Strahl durch ihre Mitte trifft sie dort, wo sie liegt.
kugel = rm.Stange(40.0, -50.0, 1.0)
kugel.schnitte([-20.0], [8.0], [0.0], ff.kugel(3.0), [2.0])
i_k = int(np.argmin(np.abs(kugel.a + 20.0)))
mitte = math.hypot(11.0, 2.0)
pruefe(
    abs(float(kugel.r[i_k, 10]) - (mitte - 3.0)) < 0.01,
    f"Kugel versetzt bei 10°: {kugel.r[i_k, 10]}",
)
pruefe(float(kugel.r[i_k, 350]) == 40.0, "Kugel versetzt: gegenüber des Versatzes weggenommen")
# Bei 0° geht der Strahl 2 mm an der Mitte vorbei: er trifft die Kugel bei 11 − √(9 − 4).
pruefe(
    abs(float(kugel.r[i_k, 0]) - (11.0 - math.sqrt(5.0))) < 0.01,
    f"Kugel versetzt bei 0°: {kugel.r[i_k, 0]}",
)
# Ohne Versatz wie vorher: unter der Spitze 8, 10° daneben höher.
ohne = rm.Stange(40.0, -50.0, 1.0)
ohne.schnitte([-20.0], [8.0], [0.0], ff.kugel(3.0))
pruefe(
    abs(float(ohne.r[i_k, 0]) - 8.0) < 1e-9 and float(ohne.r[i_k, 10]) > 8.0, "Kugel ohne Versatz"
)
print("Abtrag mit Versatz ok")

# --- Die CAM-Operation im Job ---------------------------------------------------------------
schaft = wz.Werkzeug(nummer=1, durchmesser=6, schneiden=3, schneidenlaenge=16)
schaft.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.PLANEN, ae=4, ap=2, vc=120, fz=0.05)]
kugelfraeser = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)
kugelfraeser.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=6, vc=150, fz=0.04)]
bibliothek = wz.Bibliothek([schaft, kugelfraeser])
ue.uebergeben(bibliothek)
pruefe(
    vplan.zeilenabstand_vorschlag(schaft, schaft.einsaetze(wz.ALLE)[0]) == 4.0,
    "ae als Zeilenabstand",
)
pruefe(abs(vplan.zeilenabstand_vorschlag(schaft, None) - 3.6) < 1e-9, "ohne Einsatz: 60 % von D")

doc = FreeCAD.newDocument("Plan")
doc.UndoMode = 1
welle = doc.addObject("Part::Feature", "Welle")
welle.Shape = (
    Part.makeCylinder(10, 40, V(), V(1, 0, 0))
    .cut(Part.makeBox(20, 20, 20, V(10, 8, -10)))
    .removeSplitter()
)
doc.recompute()
stirn = next(
    f
    for f in welle.Shape.Faces
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
)
achse = va.zugewiesen("C")
lage = vr.berechne(welle.Shape, stirn, achse, durchmesser=24)
job = vr.richte_ein(doc, welle, lage, vr.Stange(24.0, frei_hinten=17.5), achse, beschriftung="W")
tc1 = js.controller_ohne_transaktion(doc, job, schaft, schaft.einsaetze(wz.ALLE)[0])
tc2 = js.controller_ohne_transaktion(doc, job, kugelfraeser, kugelfraeser.einsaetze(wz.ALLE)[0])
doc.recompute()
klon = vr.modell(job)
flach_im_job = next(
    f"Face{i + 1}"
    for i, f in enumerate(klon.Shape.Faces)
    if vr.ist_eben(f) and abs(vr.aussennormale(f).dot(V(0, 0, 1))) < 1e-6
)
stirn_im_job = next(
    f"Face{i + 1}"
    for i, f in enumerate(klon.Shape.Faces)
    if vr.ist_eben(f) and abs(vr.aussennormale(f).dot(V(0, 0, 1)) - 1.0) < 1e-6
)

op = vplan.lege_an(job, tc1, achse, zustellung=2.0, zeilenabstand=4.0, flaechen=[flach_im_job])
doc.recompute()
pruefe(op.Label == "Plan indexiert T1" and op in job.Operations.Group, f"{op.Label}")
pruefe(vo.ist_rundum(op) and vplan.ist_plan(op) and not vo.ist_schruppen(op), "Art")
pruefe(js.operationsart(op) == "vierachs_plan", f"Art: {js.operationsart(op)}")
pruefe(js.EINSATZ_NACH_OPERATION["vierachs_plan"][0] == wz.PLANEN, "Einsatz Planen")
pruefe(
    (op.Ebenen, op.Lagen, op.Zeilen) == (1, 2, 6),
    f"Operation: {op.Ebenen}, {op.Lagen}, {op.Zeilen}",
)
befehle = op.Path.Commands
namen = [b.Name for b in befehle]
pruefe(namen[2:5] == ["G0", "G0", "G93"] and namen[-1] == "G94", f"Befehle: {namen[:6]}")
schnitte = [b for b in befehle if b.Name == "G1"]
pruefe(all("Y" in b.Parameters for b in schnitte), "G1 ohne Y in der Operation")
c_werte = {round(b.Parameters["C"], 6) for b in schnitte}
pruefe(len(c_werte) == 1, f"C steht nicht: {sorted(c_werte)[:4]}")
x_werte = [b.Parameters["X"] for b in schnitte]
pruefe(
    abs(min(x_werte) - 8.0) < 1e-6 and max(x_werte) <= 12.0 + 1e-6,
    f"X {min(x_werte)} … {max(x_werte)}",
)
tief = [b.Parameters["Z"] for b in schnitte if b.Parameters["X"] < 10.0 - 1e-6]
pruefe(
    min(tief) >= -27.0 - 1e-6 and max(tief) <= -13.0 + 1e-6,
    f"unten längs {min(tief)} … {max(tief)}",
)
pruefe(op.getEditorMode("Lagen") == ["ReadOnly"], "Lagen änderbar")

# Ändern: feiner, mit Aufmaß – vier Lagen bis 8,5, drei Zeilen je Lage.
vplan.aendere(op, tc1, zustellung=1.0, zeilenabstand=3.0, aufmass=0.5)
doc.recompute()
pruefe((op.Lagen, op.Zeilen) == (4, 12), f"geändert: {op.Lagen} Lagen, {op.Zeilen} Zeilen")
x_werte = [b.Parameters["X"] for b in op.Path.Commands if b.Name == "G1"]
pruefe(abs(min(x_werte) - 8.5) < 1e-6, f"mit Aufmaß: {min(x_werte)}")

# Der Kugelfräser, die Stirn allein: ein Satz statt der Bahn.
vplan.aendere(op, tc2, zustellung=1.0, zeilenabstand=3.0, aufmass=0.0)
doc.recompute()
pruefe("ebener Stirn" in op.Path.Commands[1].Name, f"Kugelfräser: {op.Path.Commands[1].Name}")
vplan.aendere(op, tc1, zustellung=2.0, zeilenabstand=4.0, aufmass=0.0, flaechen=[stirn_im_job])
doc.recompute()
pruefe("keine ebene" in op.Path.Commands[1].Name, f"nur die Stirn: {op.Path.Commands[1].Name}")
vplan.aendere(op, tc1, zustellung=2.0, zeilenabstand=4.0, aufmass=0.0, flaechen=[flach_im_job])
doc.recompute()
pruefe(op.Lagen == 2, "zurück: Lagen")

# Speichern und Laden: dieselbe Bahn.
anzahl = len(op.Path.Commands)
pfad = os.path.join(tempfile.mkdtemp(), "plan.FCStd")
doc.saveAs(pfad)
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(pfad)
op = next(o for o in doc.Objects if vplan.ist_plan(o))
op.touch()
doc.recompute()
pruefe(len(op.Path.Commands) == anzahl, f"nach dem Laden {len(op.Path.Commands)} statt {anzahl}")
pruefe(op.getEditorMode("Zeilen") == ["ReadOnly"], "Zeilen nach dem Laden")
print(ascii(f"Operation: {anzahl} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
