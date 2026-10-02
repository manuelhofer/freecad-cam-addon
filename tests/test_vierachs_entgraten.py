# Prüft „Rundum entgraten“ (W-003 Stufe V4d, W-006 S2): Welle Ø 20 mit einer Abflachung auf
# x = 8 zwischen zwei Wänden (a −30 … −10). Die Außenkanten der gewählten Flächen (kanten()):
# an der Abflachung ihre zwei langen Kanten zum Zylinder, mit den Wänden dazu deren Bögen oben
# – keine Innenkante, keine Naht, keine Stirnkante. Die Bahn mit dem Fasenfräser Ø 8 (90°,
# Spitze Ø 1): die Rundachse steht auf jedem Punkt der Kante, die Spitze 0,3 unter der Kante,
# Stücke ohne Abheben verkettet; der Kugelfräser als Kantenbruch; nah am Futter fallen Kanten
# weg; am Absatz einer Stufenwelle ein Ring rundum. Der Abtrag lässt die Fase durch (kein
# Blau). Im Gleichlauf (P-2026-10-02-25): je Kante die Richtung, mit der das Material rechts der
# Fahrt liegt (M3). Dann die CAM-Operation im Job: angelegt, gerechnet, geändert, gespeichert und
# geladen.
import math
import os
import sys
import tempfile
from dataclasses import replace

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import fraeserform as ff
from camaddon import job_schnittwerte as js
from camaddon import kollision as ko
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_achsen as va
from camaddon import vierachs_bahn as vb
from camaddon import vierachs_entgratbahn as ve
from camaddon import vierachs_entgraten as vent
from camaddon import vierachs_huelle as vh
from camaddon import vierachs_operation as vo
from camaddon import vierachs_rohteil as vr
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
LAENGS, RADIAL = (0, 0, 1), (1, 0, 0)
KANTENWINKEL = math.degrees(math.atan2(6.0, 8.0))  # 36,87°: die lange Kante bei (8, ±6)

# --- Die Kanten: Außenkanten der gewählten Flächen -------------------------------------------
flach_welle = (
    Part.makeCylinder(10, 40, V(0, 0, -40))
    .cut(Part.makeBox(10, 30, 20, V(8, -15, -30)))
    .removeSplitter()
)
abflachung = next(
    f"Face{i + 1}"
    for i, f in enumerate(flach_welle.Faces)
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-6
)
waende = [
    f"Face{i + 1}"
    for i, f in enumerate(flach_welle.Faces)
    if vr.ist_eben(f) and abs(vr.aussennormale(f).z) > 0.99 and abs(f.CenterOfMass.x - 9) < 2
]
pruefe(len(waende) == 2, f"Wände: {waende}")
k_ab = ve.kanten(flach_welle, LAENGS, RADIAL, [abflachung])
pruefe(
    len(k_ab) == 2
    and all(
        k.flaechen[0] == abflachung
        and not k.geschlossen
        and abs(k.knick - KANTENWINKEL) < 0.01
        and abs(k.laenge - 20.0) < 1e-6
        and len(k.punkte) == 81
        for k in k_ab
    ),
    f"Kanten der Abflachung: {[(k.name, k.flaechen, k.knick, k.laenge) for k in k_ab]}",
)
k_w = ve.kanten(flach_welle, LAENGS, RADIAL, [abflachung] + waende)
pruefe(
    len(k_w) == 6 and sum(abs(k.knick - 90.0) < 1e-6 for k in k_w) == 4,
    f"mit Wänden: {[(k.name, k.flaechen, round(k.knick, 1)) for k in k_w]}",
)
k_wand = ve.kanten(flach_welle, LAENGS, RADIAL, waende[:1])
pruefe(
    len(k_wand) == 2 and all(abs(k.knick - 90.0) < 1e-6 for k in k_wand),
    f"eine Wand allein (Innenkante zur Abflachung dabei?): {[k.name for k in k_wand]}",
)
k_alle = ve.kanten(flach_welle, LAENGS, RADIAL, [])
pruefe(len(k_alle) == 6, f"alle Flächen: {len(k_alle)} Kanten – die Stirnkreise zählen nicht")
pruefe(ve.eindringtiefe(ff.kegel(0.5, 4.0, 3.5), 0.3) == 0.3, "Eindringtiefe des Kegels")
pruefe(
    abs(ve.eindringtiefe(ff.kugel(3.0), 0.3) - (3.0 - math.sqrt(9.0 - 0.09))) < 1e-9,
    "Eindringtiefe der Kugel",
)
pruefe(ve.eindringtiefe(ff.kugel(1.0), 2.0) == 1.0, "Eindringtiefe: höchstens der Kugelradius")

# --- Die Bahn: Fase 0,3 unter der Kante, die Rundachse steht auf ihr ----------------------
netz = vh.vernetze(flach_welle, ve.TOLERANZ)
fase = ff.kegel(0.5, 4.0, 3.5)  # Fasenfräser Ø 8, 90°, Spitze Ø 1
werte = ve.Entgratwerte(
    form=fase, stange_radius=12.0, breite=0.3, a_stange_vorne=1.0, a_futter=-60.0
)
bahn = ve.entgraten(netz, LAENGS, RADIAL, werte, k_ab)
pruefe((bahn.kanten, bahn.ausgelassen) == (2, 0), f"{bahn.kanten} Kanten, {bahn.ausgelassen}")
pruefe(abs(bahn.laenge - 40.0) < 0.01, f"Länge {bahn.laenge}")
vorschub = [p for p in bahn.punkte if not p.eilgang]
pruefe(
    all(9.69 <= p.r <= 9.73 for p in vorschub), f"Fase: {sorted({round(p.r, 3) for p in vorschub})}"
)
pruefe(all(-30.0 - 1e-6 <= p.a <= -10.0 + 1e-6 for p in vorschub), "über die Wände hinaus")
pruefe(
    all(abs(abs(p.phi) - KANTENWINKEL) < 0.05 for p in vorschub),
    f"die Rundachse steht nicht auf der Kante: {sorted({round(p.phi, 1) for p in vorschub})}",
)
start = bahn.punkte[0]
pruefe(start.eilgang and start.a == 1.0 + 4.0 + 2.0 and start.r == 14.0, f"Start: {start}")
pruefe(sum(1 for p in vorschub if p.eintauchen) == 2, "zweimal hinein mit dem Eintauchvorschub")
for vorher, punkt in zip(bahn.punkte, bahn.punkte[1:], strict=False):
    if punkt.eintauchen:
        pruefe(vorher.eilgang and vorher.r <= punkt.r + 2.0 + 1e-9, "nicht knapp über der Kante")
ende = bahn.punkte[-1]
pruefe(ende.eilgang and ende.a == 7.0 and ende.r == 14.0, f"Ende: {ende}")
pruefe(abs(vb.dauer(bahn, 400.0) - 0.1) < 0.02, f"Dauer {vb.dauer(bahn, 400.0)}")

# Mit den Wänden: die Bögen oben – alles verkettet zu einer Fahrt um den Rand der Abflachung
# (jedes Stück beginnt, wo das vorige endet; die Naht des Zylinders teilt die Bögen).
bahn_w = ve.entgraten(netz, LAENGS, RADIAL, werte, k_w)
pruefe((bahn_w.kanten, bahn_w.ausgelassen) == (6, 0), f"mit Wänden: {bahn_w.kanten} Kanten")
bogen = [p for p in bahn_w.punkte if not p.eilgang and abs(p.a + 30.0) < 1e-6]
pruefe(
    len(bogen) > 10
    and max(p.phi for p in bogen) - min(p.phi for p in bogen) > 2 * KANTENWINKEL - 0.1
    and all(9.69 <= p.r <= 9.73 for p in bogen),
    f"Bogen bei −30: {len(bogen)} Punkte, φ {min(p.phi for p in bogen):.1f} … "
    f"{max(p.phi for p in bogen):.1f}",
)
pruefe(sum(1 for p in bahn_w.punkte if p.eintauchen) == 1, "die Stücke nicht verkettet")
r_fase = 10.0 + ve.TOLERANZ - 0.3  # die Spitze an der Kante: Länge auf diesem Radius
bogenlaenge = 2 * r_fase * math.radians(KANTENWINKEL)
pruefe(abs(bahn_w.laenge - (40.0 + 2 * bogenlaenge)) < 0.1, f"Länge mit Wänden {bahn_w.laenge}")
pruefe(
    all(
        abs(p.phi - q.phi) <= vb.HOECHSTENS_GRAD + 1e-6
        for p, q in zip(bahn_w.punkte, bahn_w.punkte[1:], strict=False)
    ),
    "ein Satz dreht mehr als 90°",
)

# Der Kugelfräser bricht die Kante rund: nur so tief, dass es 0,3 breit wird.
kugel = ve.Entgratwerte(
    form=ff.kugel(3.0), stange_radius=12.0, breite=0.3, a_stange_vorne=1.0, a_futter=-60.0
)
bahn_k = ve.entgraten(netz, LAENGS, RADIAL, kugel, k_ab)
tief = ve.eindringtiefe(ff.kugel(3.0), 0.3)
pruefe(
    all(abs(p.r - (10.0 + ve.TOLERANZ - tief)) < 0.01 for p in bahn_k.punkte if not p.eilgang),
    f"Kugel: {sorted({round(p.r, 3) for p in bahn_k.punkte if not p.eilgang})}",
)

# Nah am Futter: die Bögen bei −30 fallen weg, die langen Kanten enden bei −26.
nah = ve.Entgratwerte(form=fase, stange_radius=12.0, breite=0.3, a_stange_vorne=1.0, a_futter=-35.0)
bahn_n = ve.entgraten(netz, LAENGS, RADIAL, nah, k_w)
pruefe((bahn_n.kanten, bahn_n.ausgelassen) == (4, 2), f"nah: {bahn_n.kanten}, {bahn_n.ausgelassen}")
pruefe(
    abs(min(p.a for p in bahn_n.punkte if not p.eilgang) + 26.0) < 1e-6
    and abs(bahn_n.hinten_frei - 10.0) < 1e-6,
    f"nah: a bis {min(p.a for p in bahn_n.punkte if not p.eilgang)}, frei {bahn_n.hinten_frei}",
)

# Fehler mit einem Satz: Breite 0, keine Kanten, zu nah am Futter für alles.
for werte_falsch, kanten_falsch, text in (
    (ve.Entgratwerte(fase, 12.0, 0.0, 1.0, -60.0), k_ab, "Breite 0"),
    (werte, [], "keine Kanten"),
    (ve.Entgratwerte(fase, 12.0, 0.3, 1.0, -15.0), k_w, "alles zu nah am Futter"),
):
    try:
        ve.entgraten(netz, LAENGS, RADIAL, werte_falsch, kanten_falsch)
    except ValueError as grund:
        pruefe(len(str(grund)) > 10, f"{text}: kein Satz")
    else:
        pruefe(False, f"{text}: keine Fehlermeldung")

# Die Befehle: G1 ohne Y, C steht auf jeder langen Kante, dreht über den Bogen.
befehle = vb.befehle(bahn_w, LAENGS, RADIAL, "C", 1, 400.0)
schnitte = [b for b in befehle if b.Name == "G1"]
pruefe(len(schnitte) > 20 and all("Y" not in b.Parameters for b in schnitte), "G1 mit Y")
c_werte = sorted({round(b.Parameters.get("C", 0.0), 1) for b in schnitte})
pruefe(len(c_werte) > 20 and min(c_werte) <= -36.8 and max(c_werte) >= 36.8, f"C: {c_werte[:5]}")
print(ascii(f"Abflachung entgratet: {len(bahn.punkte)} und {len(bahn_w.punkte)} Punkte"))

# --- Stufenwelle: am Absatz ein Ring rundum – eine Umdrehung, endet, wo er begann ---------
stufe = (
    Part.makeCylinder(10, 30, V(0, 0, -40))
    .fuse(Part.makeCylinder(8, 10, V(0, 0, -10)))
    .removeSplitter()
)
k_s = ve.kanten(stufe, LAENGS, RADIAL, [])
pruefe(
    len(k_s) == 1 and k_s[0].geschlossen and abs(k_s[0].knick - 90.0) < 1e-6,
    f"Stufe: {[(k.name, k.geschlossen, k.knick) for k in k_s]}",
)
bahn_s = ve.entgraten(vh.vernetze(stufe, ve.TOLERANZ), LAENGS, RADIAL, werte, k_s)
ring = [p for p in bahn_s.punkte if not p.eilgang]
pruefe(
    all(abs(p.a + 10.0) < 1e-6 and 9.69 <= p.r <= 9.73 for p in ring)
    and abs(abs(ring[-1].phi - ring[0].phi) - 360.0) < 1e-6
    and abs(bahn_s.laenge - 2 * math.pi * 9.72) < 0.5,
    f"Ring: a {ring[0].a}, φ {ring[0].phi} … {ring[-1].phi}, Länge {bahn_s.laenge}",
)
pruefe(sum(1 for p in bahn_s.punkte if p.eintauchen) == 1, "Ring: einmal hinein")
# Im Gleichlauf (P-2026-10-02-25): Am Absatz liegt das Material längs hinten (die dicke Seite);
# mit M3 von der Spindel aus rechts der Fahrt – φ steigt; andersherum (M4) fällt es.
gegen_s = ve.entgraten(
    vh.vernetze(stufe, ve.TOLERANZ), LAENGS, RADIAL, replace(werte, gleichlauf=False), k_s
)
ring_g = [p for p in gegen_s.punkte if not p.eilgang]
pruefe(
    ring[-1].phi > ring[0].phi and ring_g[-1].phi < ring_g[0].phi,
    f"Ring: M3 φ {ring[0].phi} → {ring[-1].phi}, M4 {ring_g[0].phi} → {ring_g[-1].phi}",
)
# Um die Abflachung herum: die lange Kante oben (φ > 0) längs nach vorn, die untere nach hinten
# – und alles weiter in einer Fahrt verkettet.
oben_lang = [
    (p, q)
    for p, q in zip(bahn_w.punkte, bahn_w.punkte[1:], strict=False)
    if not q.eilgang and not p.eilgang and abs(q.a - p.a) > 1.0 and q.phi > 1.0
]
unten_lang = [
    (p, q)
    for p, q in zip(bahn_w.punkte, bahn_w.punkte[1:], strict=False)
    if not q.eilgang and not p.eilgang and abs(q.a - p.a) > 1.0 and q.phi < -1.0
]
pruefe(
    oben_lang
    and unten_lang
    and all(q.a > p.a for p, q in oben_lang)
    and all(q.a < p.a for p, q in unten_lang),
    "Abflachung nicht im Gleichlauf",
)

# --- Der Abtrag lässt die Fase durch: ohne sie wäre die Kante blau -----------------------
a_st, r_st, phi_st, op_st, gut_st = [], [], [], [], []
for punkt in bahn_w.punkte:
    a_st.append(punkt.a)
    r_st.append(punkt.r)
    phi_st.append(punkt.phi)
    op_st.append(0)
    gut_st.append(True)
stationen = (np.array(a_st), np.array(r_st), np.array(phi_st), np.array(op_st), np.array(gut_st))
# Die Stange vorher wie das Teil: nur die Fase nimmt noch etwas weg.
stange = rm.Stange(12.0, -60.0, 1.0)
teil = rm.teilradien(vh.vernetze(flach_welle), LAENGS, RADIAL, stange)
stange.r = np.where(np.isfinite(teil) & (teil > 0), np.maximum(teil, 0.0), stange.r)
ohne = rm.Abtrag(stange, LAENGS, RADIAL, stationen, {0: fase}, 0.0, [flach_welle])
ohne.bis_station(len(a_st) - 1)
blau_ohne = int((ohne.vergleich().farbe == rm.BLAU).sum())
stange.r = np.where(np.isfinite(teil) & (teil > 0), np.maximum(teil, 0.0), 12.0)
mit = rm.Abtrag(stange, LAENGS, RADIAL, stationen, {0: fase}, 0.0, [flach_welle], fasen={0: 0.3})
mit.bis_station(len(a_st) - 1)
vergleich = mit.vergleich()
blau_mit = int((vergleich.farbe == rm.BLAU).sum())
pruefe(blau_ohne > 10 and blau_mit == 0, f"blau ohne Fase {blau_ohne}, mit {blau_mit}")
pruefe(vergleich.kleinster >= -rm.BLAU_AB - 1e-9, f"kleinster {vergleich.kleinster}")
# Zurück an den Anfang und noch einmal: dasselbe.
mit.bis_station(0)
mit.bis_station(len(a_st) - 1)
pruefe(int((mit.vergleich().farbe == rm.BLAU).sum()) == 0, "nach dem Zurückrechnen blau")
pruefe("vierachs_entgraten" in ko.INS_TEIL_ERLAUBT, "Kollision: ins Teil erlaubt")
pruefe("vierachs_entgraten" in rm.operationsarten_rundum(), "Abtrag: Rundum-Art")
print("Abtrag mit Fase ok")

# --- Die CAM-Operation im Job ---------------------------------------------------------------
fasenfraeser = wz.Werkzeug(
    nummer=3, art=wz.FASENFRAESER, durchmesser=8, schneiden=2, spitzenwinkel=90, spitzen_d=1
)
fasenfraeser.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=100, fz=0.03)]
kugelfraeser = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)
kugelfraeser.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=6, vc=150, fz=0.04)]
pruefe(vent.kann_entgraten(fasenfraeser) and vent.kann_entgraten(kugelfraeser), "kann entgraten")
pruefe(not vent.kann_entgraten(wz.Werkzeug(nummer=1, durchmesser=6)), "Schaftfräser entgratet")
bibliothek = wz.Bibliothek([fasenfraeser, kugelfraeser])
ue.uebergeben(bibliothek)

doc = FreeCAD.newDocument("Entgraten")
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
tc3 = js.controller_ohne_transaktion(doc, job, fasenfraeser, fasenfraeser.einsaetze(wz.ALLE)[0])
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

op = vent.lege_an(job, tc3, achse, breite=0.3, flaechen=[flach_im_job])
doc.recompute()
pruefe(op.Label == "Rundum entgraten T3" and op in job.Operations.Group, f"{op.Label}")
pruefe(vo.ist_rundum(op) and vent.ist_entgraten(op) and not vo.ist_schruppen(op), "Art")
pruefe(js.operationsart(op) == "vierachs_entgraten", f"Art: {js.operationsart(op)}")
pruefe(js.EINSATZ_NACH_OPERATION["vierachs_entgraten"][0] == wz.FASEN, "Einsatz Fasen")
pruefe((op.Kanten, op.Ausgelassen) == (2, 0), f"Operation: {op.Kanten}, {op.Ausgelassen}")
befehle = op.Path.Commands
namen = [b.Name for b in befehle]
pruefe(namen[2:5] == ["G0", "G0", "G93"] and namen[-1] == "G94", f"Befehle: {namen[:6]}")
schnitte = [b for b in befehle if b.Name == "G1"]
pruefe(all("Y" not in b.Parameters for b in schnitte), "G1 mit Y in der Operation")
x_werte = [b.Parameters["X"] for b in schnitte]
pruefe(all(9.69 <= x <= 9.73 for x in x_werte), f"X {min(x_werte)} … {max(x_werte)}")
# Die Rundachse steht je Kante – die zwei Kanten liegen 2 × 36,87° auseinander (wo die
# Abflachung im Job liegt, sagt die Einrichtung).
c_werte = sorted({round(b.Parameters.get("C", 0.0), 2) for b in schnitte})
pruefe(
    len(c_werte) == 2 and abs(c_werte[1] - c_werte[0] - 2 * KANTENWINKEL) < 0.05,
    f"C: {c_werte}",
)
pruefe(op.getEditorMode("Kanten") == ["ReadOnly"], "Kanten änderbar")

# Ändern: breiter – tiefer; die Stirn allein: keine Außenkante (die Stirn zählt nicht).
vent.aendere(op, tc3, breite=0.5)
doc.recompute()
x_werte = [b.Parameters["X"] for b in op.Path.Commands if b.Name == "G1"]
pruefe(all(9.49 <= x <= 9.53 for x in x_werte), f"breiter: X {min(x_werte)} … {max(x_werte)}")
vent.aendere(op, tc3, breite=0.3, flaechen=[stirn_im_job])
doc.recompute()
pruefe("Aussenkante" in op.Path.Commands[1].Name, f"nur die Stirn: {op.Path.Commands[1].Name}")
pruefe((op.Kanten, op.Ausgelassen) == (0, 0), "nach dem Fehler nicht 0")
# Der Kugelfräser als Kantenbruch.
vent.aendere(op, tc2, breite=0.3, flaechen=[flach_im_job])
doc.recompute()
pruefe(op.Label == "Rundum entgraten T2", f"Name folgt dem Werkzeug: {op.Label}")
x_werte = [b.Parameters["X"] for b in op.Path.Commands if b.Name == "G1"]
pruefe(
    all(abs(x - (10.0 + ve.TOLERANZ - tief)) < 0.01 for x in x_werte),
    f"Kugel: X {min(x_werte)} … {max(x_werte)}",
)
vent.aendere(op, tc3, breite=0.3, flaechen=[flach_im_job])
doc.recompute()
pruefe(op.Kanten == 2, "zurück: Kanten")

# Speichern und Laden: dieselben Kanten, die Fase gleich tief (das Netz des geladenen Teils
# ist ein anderes – Punkte, die die Bahn zusammenfasst, können sich um Tausendstel verschieben).
anzahl = len(op.Path.Commands)
pfad = os.path.join(tempfile.mkdtemp(), "entgraten.FCStd")
doc.saveAs(pfad)
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(pfad)
op = next(o for o in doc.Objects if vent.ist_entgraten(o))
op.touch()
doc.recompute()
pruefe((op.Kanten, op.Ausgelassen) == (2, 0), f"nach dem Laden {op.Kanten}, {op.Ausgelassen}")
x_werte = [b.Parameters["X"] for b in op.Path.Commands if b.Name == "G1"]
pruefe(
    len(op.Path.Commands) >= 17 and all(9.69 <= x <= 9.73 for x in x_werte),
    f"nach dem Laden {len(op.Path.Commands)} Befehle (vorher {anzahl}), X {min(x_werte)}",
)
pruefe(op.getEditorMode("Ausgelassen") == ["ReadOnly"], "Ausgelassen nach dem Laden")
print(ascii(f"Operation: {anzahl} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
