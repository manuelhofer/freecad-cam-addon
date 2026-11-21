# Prüft 4 Achsen „C in geschwenkter Lage“ an der Beispiel-5-Achs Tisch/Tisch (Manuel, 2026-11-15:
# „wenn man so etwas auf einem tisch bearbeitetet spand man das meistens am mantel in ein drei
# backenfutter senkrcht zum tisch ! … und meist relativ mittig“): Das Rohr steht im Dreibackenfutter
# mitten auf dem Rundtisch, A schwenkt fest um 90°, C dreht das Rohr, das Werkzeug kommt von oben.
#
# Rohr Ø 60/50 × 120 mit der Kurvennut 12 breit über 200° (wie test_vierachs_kurvennut, mit dem
# Fräser selbst geschnitten), „Plan indexiert“ mit T1 Ø 8 (ER32, HSK-A63). Geprüft: von_maschine
# bietet „C, A auf 90°“ zuerst an und A zuletzt; die Stange steht auf dem Futter mittig auf C; die Bahn
# bleibt im Job (C, kein A – so zeigt FreeCAD sie richtig); die Maschine fährt A fest und C – mit
# eigener Kinematik nachgemessen trifft die Spitze die Bahn; das Programm (Siemens, Heidenhain)
# schwenkt erst hoch über Stange und Futter, dann A, und am Ende zurück; ohne Maschine geht die
# Operation nicht ins Programm; Kollision und Rest: nichts berührt sich, nirgends ins Teil; das
# Futter zählt in der Kollision (Gegenprobe mit Backen bis an die Nut).
import dataclasses
import math
import os
import re
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part
import Path

from camaddon import abfahren as ab
from camaddon import beispielmaschine as bm
from camaddon import einrichtblatt as eb
from camaddon import kollision as kb
from camaddon import maschine as m
from camaddon import postprozessor as pp
from camaddon import reichweite as rw
from camaddon import restmaterial as rm
from camaddon import schwenken as sw
from camaddon import spannung, sprache
from camaddon import vierachs_achsen as va
from camaddon import vierachs_operation as vo
from camaddon import vierachs_plan as vplan
from camaddon import vierachs_planbahn as vp
from camaddon import vierachs_rohteil as vr
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
V = FreeCAD.Vector
RA, RI, LANG = 30.0, 25.0, 120.0
BREITE, WINKEL, A0, A1 = 12.0, 200.0, 45.0, 85.0


def mitte(phi_grad):
    return A0 + (A1 - A0) * 0.5 * (1.0 - math.cos(math.pi * phi_grad / WINKEL))


def strahl(phi_grad):
    p = math.radians(phi_grad)
    return V(0, math.cos(p), math.sin(p))


rohr = Part.makeCylinder(RA, LANG, V(), V(1, 0, 0)).cut(
    Part.makeCylinder(RI, LANG, V(), V(1, 0, 0))
)
schnitte = [
    Part.makeCylinder(BREITE / 2.0, 11.0, V(mitte(f), 0, 0) + strahl(f) * (RI - 3.0), strahl(f))
    for f in np.linspace(0.0, WINKEL, 101)
]
form = rohr.cut(schnitte[0].fuse(schnitte[1:]))

# --- Die Stangenachsen der Tisch/Tisch: „C, A auf 90°“ vorn, A zuletzt -----------------------
asm, ma = bm.fuenfachs_tisch_tisch()
achsen = va.von_maschine(asm, ma)
print(ascii(f"Achsen: {[(a.buchstabe, va.schwenk_text(a), a.anzeige) for a in achsen]}"))
achse = achsen[0]
pruefe(
    achse.buchstabe == "C" and achse.schwenk == (("A", 90.0),) and achse.laengs == V(0, 0, 1),
    f"zuerst: {achse}",
)
# A +90 (wie das Gelenk) neigt den Rundtisch nach vorn: Dorthin kommt der Kopf weiter (Y −200 von
# der Mitte aus 250 mm, nach hinten 200 mm). Im Job kommt das Werkzeug dann aus +Y.
pruefe(va.radial(achse) == V(0, 1, 0) and achse.quer, f"Werkzeug aus {va.radial(achse)}")
pruefe(achse.anzeige == "A −90°", f"an der Steuerung: {achse.anzeige!r}")  # DIN: umgedreht
pruefe([a.buchstabe for a in achsen[1:]] == ["C", "A"], f"danach: {achsen[1:]}")
pruefe(not any(a.schwenk for a in achsen[1:]), "geschwenkt doppelt")
asm_kt, ma_kt = bm.fuenfachs_kopf_tisch()  # Kopf/Tisch: C ohne Schwenken, wie bisher
pruefe(
    [(a.buchstabe, a.schwenk) for a in va.von_maschine(asm_kt, ma_kt)] == [("C", ())],
    "Kopf/Tisch bekommt eine geschwenkte Lage",
)
FreeCAD.closeDocument(asm_kt.Document.Name)

# --- Job: das Rohr im Futter auf dem Rundtisch ---------------------------------------------------
doc = FreeCAD.newDocument("RohrGeschwenkt")
teil = doc.addObject("Part::Feature", "Rohr")
teil.Shape = form
doc.recompute()
stirn = next(
    f for f in form.Faces if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
)
lage = vr.berechne(form, stirn, achse, durchmesser=60)
job = vr.richte_ein(doc, teil, lage, vr.Stange(60.0), achse)
pruefe(vr.im_tischfutter(job) and vr.schwenk_text(job) == "A90", "nicht im Tischfutter")
tc = job.Tools.Group[0]
tc.Tool.Diameter = 8
tc.ToolNumber = 1
tc.HorizFeed = "800 mm/min"
tc.SpindleSpeed = 6000
bib = wz.Bibliothek()
halter = bib.neuer_halter("er32", None, "HSK-A63")
t1 = bib.neues_werkzeug()
t1.nummer, t1.durchmesser, t1.laenge_spindelnase, t1.halter = 1, 8.0, 125.0, halter.kennung
t1.schneidenlaenge = 25.0
modell = vr.modell(job).Shape
alle = [f"Face{i + 1}" for i in range(len(modell.Faces))]
nut = vp.kurvennuten(modell, tuple(achse.laengs), tuple(va.radial(achse)), alle)[0]
op = vplan.lege_an(job, tc, achse, 4.0, 2.0, aufmass=0.0, flaechen=list(nut.namen))
doc.recompute()
befehle = list(op.Path.Commands)
achsen_der_bahn = {k for b in befehle for k in b.Parameters}
# Gerechnet wie das Gelenk (A90), gezeigt wie die Steuerung (A −90°) – wie in der Liste.
pruefe(
    op.SchwenkGelenk == "A90"
    and op.Schwenkstellung == "A −90°"
    and op.Werkzeugrichtung == V(0, 1, 0),
    f"Operation: {op.SchwenkGelenk!r} {op.Schwenkstellung!r} {op.Werkzeugrichtung}",
)
pruefe("C" in achsen_der_bahn and "A" not in achsen_der_bahn, f"Bahn: {achsen_der_bahn}")
# Vorn in der Bahn: Nur über „Programm schreiben“ des Addons ist sie ein Maschinenprogramm.
pruefe(
    any(b.Name.startswith(vo.KOMMENTAR_GESCHWENKT) and "[A -90]" in b.Name for b in befehle[:3]),
    f"Bahn ohne Kommentar vorn: {[b.Name for b in befehle[:3]]}",
)

p = rw.Pruefung(asm, ma)
nullpunkt = rw.nullpunkt(job, p)
ws = p.werkstueckaufnahme
c1 = next(a for a in p.kette.achsen if p.programmbuchstabe(a) == "C")
richtung, ursprung = p.verfahren.achslage(c1)
null_asm = p._lage(ws).multiply(FreeCAD.Placement(nullpunkt, FreeCAD.Rotation())).Base
neben = (null_asm - ursprung) - richtung * (null_asm - ursprung).dot(richtung)
unten = nullpunkt.z + job.Stock.Placement.Base.z  # das hintere Ende der Stange über dem Rundtisch
futter_d, futter_h = spannung.futter_masse(RA)
print(ascii(f"Nullpunkt {tuple(nullpunkt)}, Stange {unten:.1f} über dem Tisch, Futter {futter_d}"))
pruefe(neben.Length < 1e-6, f"Die Stange steht {neben.Length:.3f} mm neben C")
pruefe(abs(unten - futter_h) < 1e-6, f"Die Stange beginnt {unten} über dem Tisch")
futter = spannung.schraubstock(job)
pruefe(
    futter is not None
    and abs(futter.BoundBox.ZMin - (job.Stock.Placement.Base.z - futter_h)) < 1e-6,
    "kein Futter unter der Stange",
)

# --- Die Maschine fährt A fest, C dreht: eigene Kinematik ---------------------------------------
aufnahme = p.werkzeugaufnahme(1)
eins = rw.einspannung(tc, bib)
gefahren = p.befehle(op, None, aufnahme, eins, nullpunkt)
bewegt = [b for b in gefahren if b.Name in ("G0", "G1")]
pruefe(
    set(bewegt[0].Parameters) == {"Z"}
    and set(bewegt[1].Parameters) == {"X", "Y"}
    and bewegt[2].Parameters == {"A": 90.0},
    f"vor der Bahn: {[(b.Name, b.Parameters) for b in bewegt[:3]]}",
)
verfahren = p.verfahren
linear, dreh = p.achsen_fuer(aufnahme)
rund = {p.programmbuchstabe(a): a for a in dreh if p.programmbuchstabe(a)}


def spitze_im_job(null):
    """Die Spitze im Teil (Job am Nullpunkt `null` an der Werkstückaufnahme, mit dem Tisch)."""
    welt = m.globale_platzierung(aufnahme.Lcs).multVec(eins.spitze())
    job_welt = m.globale_platzierung(ws.Lcs).multiply(FreeCAD.Placement(null, FreeCAD.Rotation()))
    return job_welt.inverse().multVec(welt)


def jacobi(null):
    """Je Linearachse 1 mm: wie die Spitze im Teil fährt (bei den Rundachsen, wie sie stehen)."""
    s0, spalten = spitze_im_job(null), []
    for a in linear:
        verfahren.setze(a, verfahren.stellung(a) + 1.0, grenzen=False)
        spalten.append(tuple(spitze_im_job(null) - s0))
        verfahren.setze(a, verfahren.stellung(a) - 1.0, grenzen=False)
    return np.array(spalten).T, s0


def mit_c(liste):
    stand, aus = {}, []
    for b in liste:
        stand.update({k: float(v) for k, v in b.Parameters.items() if k in "XYZABC"})
        if "C" in b.Parameters and b.Name in ("G0", "G1"):
            aus.append(dict(stand))
    return aus


def neben_der_bahn(
    saetze, null, nach_dem_schwenken=True, versatz=(0.0, 0.0, 0.0), ursprung=(0.0, 0.0, 0.0)
):
    """So weit (mm) steht die Spitze höchstens neben der Bahn, wenn die Maschine `saetze` fährt
    und das Teil am Nullpunkt `null` sitzt – eingerichtet wie der Einrichter: nach dem Schwenken
    (A fest, C 0) die Spitze an die Stirn auf der Achse (G54), oder bei A 0 (`versatz` dazu: so
    rechnete das Programm bis zum Fund des Zweiflers). Ohne TCPM: X, Y, Z sind die Linearachsen
    ab G54, je 1 mm wie die Spitze bei A 0 C 0 im Teil fährt; A und C wie das Gelenk.
    `ursprung`: der Punkt im Job, an dem G54 eingerichtet ist (mit dem Schwenkzyklus: ungeschwenkt
    an der Stirn der Stange – die Steuerung schwenkt ihn mit: so weit fährt sie die Linearachsen,
    dass die Spitze nach dem Schwenken an ihm steht, gerechnet mit der Kinematik der Maschine)."""
    verfahren.grundstellung()
    start = np.array([verfahren.stellung(a) for a in linear])
    j0, _s = jacobi(null)  # X, Y, Z im Programm: wie bei Rundachsen 0
    if nach_dem_schwenken:
        for buchstabe, wert in achse.schwenk:
            verfahren.setze(rund[buchstabe], wert, grenzen=False)
    js, s = jacobi(null)
    ziel = np.array(ursprung) - np.array(tuple(s))
    g54 = start + np.linalg.lstsq(js, ziel, rcond=None)[0]  # Spitze am Ursprung
    paare = list(zip(mit_c(befehle), mit_c(saetze), strict=True))
    groesste = 0.0
    for bahn, programm in paare[:: max(1, len(paare) // 15)]:
        punkt = np.array([programm.get(x, 0.0) for x in "XYZ"]) + np.array(versatz)
        wege = g54 + np.linalg.solve(j0, punkt)
        verfahren.grundstellung()
        for a, w in zip(linear, wege, strict=True):
            verfahren.setze(a, w, grenzen=False)
        for buchstabe, a in rund.items():
            verfahren.setze(a, programm.get(buchstabe, 0.0), grenzen=False)  # wie das Gelenk
        soll = FreeCAD.Rotation(V(achse.laengs), -achse.drehsinn * bahn["C"]).multVec(
            V(*(bahn.get(x, 0.0) for x in "XYZ"))
        )
        groesste = max(groesste, (spitze_im_job(null) - soll).Length)
    verfahren.grundstellung()
    return len(paare), groesste


anzahl, groesste = neben_der_bahn(gefahren, nullpunkt)
print(ascii(f"Spitze: {anzahl} Sätze, höchstens {groesste:.6f} mm neben der Bahn"))
pruefe(groesste < 1e-6, f"Spitze {groesste:.4f} mm neben der Bahn")
# Das Rohr sitzt 5 mm tiefer als im Modell (das Futter niedriger, tiefer gespannt): Eingerichtet
# nach dem Schwenken trifft dasselbe Programm die Bahn am echten Teil. Bis zum Fund des Zweiflers
# (2026-11-14) zählte es von G54 bei A 0 – mit dem Abstand Stirn–Schwenkachse aus dem Modell im
# Programm: 7,07 mm daneben und 5 mm tiefer, der Anfahrsatz 2 mm im Rohteil.
tiefer = nullpunkt + V(0, 0, -5.0)
_anzahl, echt = neben_der_bahn(gefahren, tiefer)
schwenkung = sw.schwenkung_der_operation(op, sw.Maschine(p, aufnahme, eins, nullpunkt), job)
_anzahl, frueher = neben_der_bahn(gefahren, tiefer, False, schwenkung.versatz)
print(ascii(f"5 mm tiefer gespannt: {echt:.6f} mm, früher (G54 bei A 0) {frueher:.3f} mm"))
pruefe(echt < 1e-6, f"5 mm tiefer gespannt: {echt:.4f} mm neben der Bahn")
pruefe(abs(frueher - math.hypot(5.0, 5.0)) < 0.01, f"Gegenprobe G54 bei A 0: {frueher:.4f} mm")
reich = p.pruefe_job(job, nullpunkt, bib)
pruefe(not reich.ueberschreitungen, f"über: {[u.text() for u in reich.ueberschreitungen][:2]}")
pruefe(not any("radial" in h for h in reich.hinweise), f"Hinweise: {reich.hinweise}")

# --- Das Programm ohne Schwenkzyklus: erst hoch, A fest, C dreht, am Ende zurück ---------------
# (Haken „Mit dem Schwenkzyklus der Steuerung“ aus – oder eine Steuerung ohne: „nach dem Schwenken
# einrichten“, wie bis 0.385, mit Hinweis.)
maschine_sw = sw.Maschine(p, aufnahme, eins, nullpunkt)
info = pp.maschineninfo_dokument(asm.Document)
ohne_zyklus = {k: pp.steuerung(k).ersetzt(schwenkzyklus=False) for k in ("siemens", "heidenhain")}
# Ungeschwenkt einrichten hängt an einem eigenen Haken, vorbelegt aus (Zweifler 2026-11-15: ob C
# unter CYCLE800 / PLANE SPATIAL den Rahmen mitnimmt, ist an keiner Maschine belegt).
steuerung_zyklus = {
    k: pp.steuerung(k, {"rohr_ungeschwenkt": True}) for k in ("siemens", "heidenhain")
}
for kennung in ("siemens", "heidenhain"):
    vorgabe = pp.steuerung(kennung)
    pruefe(
        vorgabe.schwenkzyklus and vorgabe.lage_mit_zyklus and not vorgabe.rohr_ungeschwenkt,
        f"{kennung}: Haken vorbelegt {vorgabe.schwenkzyklus} {vorgabe.rohr_ungeschwenkt}",
    )
    pruefe(not pp.lage_mit_zyklus(vorgabe), f"{kennung}: ungeschwenkt still vorbelegt")
    # Ohne den Haken: der Weg „nach dem Schwenken“ (0.376.0) Zeile für Zeile – dasselbe Programm
    # wie mit Abschnitten, die den Weg mit Zyklus gar nicht kennen (so schrieb es die Basis).
    roh = pp.abschnitte(job, maschine=maschine_sw)
    basis = [dataclasses.replace(a, lage_zyklus=None, stirn_oben=None) for a in roh]
    jetzt = pp.programm(roh, vorgabe, info, "Rohr")
    wie_basis = pp.programm(basis, vorgabe, info, "Rohr")
    pruefe(
        jetzt.zeilen == wie_basis.zeilen,
        f"{kennung}: Haken aus ist nicht der Weg nach dem Schwenken "
        f"({len(jetzt.zeilen)}/{len(wie_basis.zeilen)} Zeilen)",
    )
    pruefe(
        not any("ohne Teil" in z for z in jetzt.zeilen), f"{kennung}: Probelauf ohne Haken im Kopf"
    )
for kennung, schwenken, zurueck, c_wort in (
    ("siemens", "G0 A1=-90.000", "G0 A1=0.000", r"C1="),
    ("heidenhain", "L A-90.000 R0 FMAX", "L A+0.000 R0 FMAX", r" C[+-]\d"),
):
    programm = pp.programm(
        pp.abschnitte(job, maschine=maschine_sw), ohne_zyklus[kennung], info, "Rohr"
    )
    zeilen = [z.split(" ", 1)[1] if kennung == "heidenhain" else z for z in programm.zeilen]
    an = next((i for i, z in enumerate(zeilen) if z == schwenken), -1)
    erste_c = next((i for i, z in enumerate(zeilen) if re.search(c_wort, z)), -1)
    hoch = zeilen[an - 2] if an > 1 else ""  # erst hoch, dann über C, dann schwenken
    ueber_c = zeilen[an - 1] if an > 0 else ""
    print(
        ascii(
            f"{kennung} ohne Zyklus: {hoch} | {zeilen[an] if an >= 0 else '-'} | "
            f"Hinweise {programm.hinweise}"
        )
    )
    pruefe(
        0 < an < erste_c and "Z" in hoch and "X" in ueber_c and "Y" in ueber_c,
        f"{kennung}: Schwenken {an} ({hoch} | {ueber_c}), erstes C {erste_c}",
    )
    pruefe(sum(z.startswith(schwenken) for z in zeilen) == 1, f"{kennung}: A mehrmals")
    pruefe(zurueck in zeilen[erste_c:], f"{kennung}: am Ende nicht zurück")
    pruefe(
        len(programm.hinweise) == 1 and "ohne Schwenkzyklus" in programm.hinweise[0],
        f"{kennung} ohne Zyklus: {programm.hinweise}",
    )
    pruefe(not any("CAM-Addon:" in z for z in zeilen), f"{kennung}: Kommentar der Bahn im Programm")
    # Im Kopf: G54 wird nach dem Schwenken eingerichtet (A wie die Steuerung zählt).
    kopf = [z for z in zeilen if re.search(r"G54: .*A [−-]90 und C 0 schwenken", z)]
    pruefe(kopf, f"{kennung}: Kopf ohne Nullpunkt nach dem Schwenken")

# --- Mit dem Schwenkzyklus: ungeschwenkt eingerichtet, wie Manuel (2026-11-15) ---------------
# „dann ist z0 vom tisch die entfernteste stelle .. und wenn das rohr senkrecht also man durch das
# loch zum tisch schauen kann ist mittig im rohr xy0“: G54 bei A 0 C 0 mitten im Rohr, oben an der
# Stirn der Stange; CYCLE800 / PLANE SPATIAL schwenkt um ihn, den Weg zur Schwenkachse nimmt die
# Steuerung aus ihrer Kinematik. Nachgerechnet mit eigener Kinematik: Die Spitze trifft die Bahn –
# auch mit dem Rohr 5 mm tiefer gespannt (G54 an der Stirn gemessen). Gegenprobe: dasselbe
# Programm mit G54 nach dem Schwenken an der Stirn des Teils eingerichtet liegt um das Planaufmaß
# daneben – Einrichtblatt und Kopf sagen deshalb, wo.
vorn = vr.stirn_oben(job)
pruefe(vorn is not None and vorn > 0.5, f"Stirn der Stange über dem Teil: {vorn}")
lage = [a for a in pp.abschnitte(job, maschine=maschine_sw) if a.lage_zyklus is not None]
pruefe(len(lage) == 1, f"Abschnitte mit Schwenkzyklus: {len(lage)}")
im_zyklus, schwenk_zyklus, _register = lage[0].lage_zyklus
pruefe(
    not any(b.Name == "G0" and set(b.Parameters) == {"A"} for b in im_zyklus),
    "im Zyklus steht A noch in den Sätzen",
)
pruefe(
    abs(abs(sw.zyklus_winkel(schwenk_zyklus.ebene)[1][2]) - 90.0) < 1e-6,
    f"Winkel des Zyklus: {sw.zyklus_winkel(schwenk_zyklus.ebene)}",
)
# Der Weg zur Stirn der Stange unabhängig von vierachs_rohteil abgeleitet: der weiteste Punkt des
# Rohteils längs der Stangenachse der Maschine (achse.laengs), im Job.
laengs_job = V(achse.laengs)
weit_vorn = max(v.Point.dot(laengs_job) for v in job.Stock.Shape.Vertexes)
d_job = tuple(float(w) for w in laengs_job * weit_vorn)
pruefe(abs(weit_vorn - vorn) < 1e-6, f"Stirn der Stange: {weit_vorn} statt {vorn}")
pruefe(
    max(abs(a - b) for a, b in zip(vr.stirn_weg(job), d_job, strict=True)) < 1e-6,
    f"stirn_weg {vr.stirn_weg(job)} statt {d_job}",
)
# Der Zyklus stellt A (im Programm steht es nicht mehr): davor so, wie er schwenkt.
geschwenkt_im_zyklus = [Path.Command("G0", dict(schwenk_zyklus.rund)), *im_zyklus]
_anzahl, mit_zyklus = neben_der_bahn(geschwenkt_im_zyklus, nullpunkt, ursprung=d_job)
_anzahl, mit_zyklus_tiefer = neben_der_bahn(geschwenkt_im_zyklus, tiefer, ursprung=d_job)
_anzahl, falsch_eingerichtet = neben_der_bahn(geschwenkt_im_zyklus, nullpunkt)
print(
    ascii(
        f"Schwenkzyklus: {mit_zyklus:.6f} mm, 5 mm tiefer {mit_zyklus_tiefer:.6f} mm, G54 nach dem "
        f"Schwenken an der Stirn des Teils {falsch_eingerichtet:.3f} mm (Planaufmaß {vorn:g})"
    )
)
pruefe(mit_zyklus < 1e-6, f"Schwenkzyklus: {mit_zyklus:.4f} mm neben der Bahn")
pruefe(mit_zyklus_tiefer < 1e-6, f"Schwenkzyklus 5 mm tiefer: {mit_zyklus_tiefer:.4f} mm")
pruefe(abs(falsch_eingerichtet - vorn) < 1e-6, f"Gegenprobe: {falsch_eingerichtet:.4f} mm")
for kennung, zyklus_satz, zurueck_satz, c_wort in (
    ("siemens", "CYCLE800(", "CYCLE800()", r"C1="),
    ("heidenhain", "PLANE SPATIAL", "PLANE RESET", r" C[+-]\d"),
):
    programm = pp.programm(
        pp.abschnitte(job, maschine=maschine_sw), steuerung_zyklus[kennung], info, "Rohr"
    )
    zeilen = [z.split(" ", 1)[1] if kennung == "heidenhain" else z for z in programm.zeilen]
    an = [i for i, z in enumerate(zeilen) if z.startswith(zyklus_satz) and z != zurueck_satz]
    erste_c = next((i for i, z in enumerate(zeilen) if re.search(c_wort, z)), -1)
    zurueck = [i for i, z in enumerate(zeilen) if z.startswith(zurueck_satz)]
    print(ascii(f"{kennung} mit Zyklus: {[zeilen[i] for i in an]} | Hinweise {programm.hinweise}"))
    # Erst hoch, über C (X 0 Y 0 ungeschwenkt), dann der Zyklus; A steht nicht mehr im Programm.
    # (nach dem Wechselpunkt ganz oben ohne „Z“ davor – dort ist es schon hoch)
    davor = [z for z in zeilen[max(0, an[0] - 12) : an[0]] if re.match(r"(G0|L) |G53", z)]
    pruefe(
        len(an) == 1 and an[0] < erste_c and zurueck and zurueck[-1] > erste_c,
        f"{kennung}: Zyklus {an}, erstes C {erste_c}, zurück {zurueck}",
    )
    pruefe(
        len(davor) >= 2
        and any("Z" in z for z in davor[:-1])
        and re.search(r"X\+?0\.000 Y\+?0\.000", davor[-1]),
        f"{kennung}: vor dem Zyklus {davor}",
    )
    pruefe(
        not any(re.search(r"\bA1?=?[+-]?90", z.split(";")[0]) for z in zeilen),
        f"{kennung}: A im Programm",
    )
    pruefe(not programm.hinweise, f"{kennung} mit Zyklus: {programm.hinweise}")
    # Die Vorzugsrichtung: A an der Steuerung −90 (nach DIN umgedreht), die kleinere der zwei
    # Stellungen (die andere: A +90 mit C 180 – jedes C der Bahn läge 180° daneben).
    richtung_ok = (
        an and zeilen[an[0]].endswith(",-1,0,1)")
        if kennung == "siemens"
        else an and zeilen[an[0]].split()[-1] == "SEQ-"
    )
    pruefe(richtung_ok, f"{kennung}: Vorzugsrichtung im Zyklus {[zeilen[i] for i in an]}")
    pruefe(
        any("ungeschwenkt einrichten" in z for z in zeilen)
        and not any("schwenken, dann einrichten" in z for z in zeilen),
        f"{kennung}: Kopf ohne ungeschwenkt einrichten",
    )
    probelauf = [z for z in zeilen if "C einmal ohne Teil" in z and "nicht mitdreht" in z]
    pruefe(probelauf and probelauf[0] in zeilen[: an[0]], f"{kennung}: Kopf ohne Probelauf")
    pruefe(not any(z.startswith("G55") for z in zeilen), f"{kennung}: G55 mit Schwenkzyklus")
    if kennung == "siemens":  # CYCLE800() dreht nicht zurück: danach A 0 über C
        pruefe("G0 A1=0.000" in zeilen[zurueck[-1] :], "siemens: nach CYCLE800() nicht auf A 0")
    else:  # PLANE RESET TURN dreht selbst: vorher im Rahmen über C
        vor_reset = zeilen[zurueck[-1] - 1] if zurueck else ""
        pruefe(re.search(r"^L [XY][+-]\d", vor_reset), f"heidenhain: vor PLANE RESET {vor_reset}")
    # Die Sätze im Zyklus: dieselben X, Y, Z wie ohne Zyklus, um den geschwenkten Weg zur Stirn
    # der Stange verschoben (a · d).
    if kennung == "siemens":
        ohne = pp.programm(
            pp.abschnitte(job, maschine=maschine_sw), ohne_zyklus["siemens"], info, "Rohr"
        ).zeilen
        ad = np.array(schwenkung.abbildung.a) @ np.array(d_job)

        def bahnsaetze(zz):
            aus = []
            for z in zz:
                if z.startswith("G1 ") and "C1=" in z:
                    w = dict(re.findall(r"\b([XYZ])(-?\d+\.\d+)", z))
                    aus.append(tuple(float(w.get(k, "nan")) for k in "XYZ"))
            return aus

        mit_s, ohne_s = bahnsaetze(zeilen), bahnsaetze(ohne)
        paare = [
            (m_, o_)
            for m, o in zip(mit_s, ohne_s, strict=False)
            for m_, o_ in [(m, o)]
            if not any(math.isnan(x) for x in m + o)
        ]
        weit = max(
            (max(abs(m[i] - o[i] + ad[i]) for i in range(3)) for m, o in paare), default=math.inf
        )
        print(ascii(f"Sätze mit/ohne Zyklus: {len(mit_s)}/{len(ohne_s)}, höchstens {weit:.4f} mm"))
        pruefe(len(mit_s) == len(ohne_s) and weit < 0.0015, f"Sätze im Zyklus: {weit:.4f} mm")
# Einrichtblatt: das Futter auf dem Rundtisch und der Nullpunkt nach dem Schwenken.
futter_text = eb.spannung_text(job, sprache.tr)
null_text = eb.nullpunkt_text(job, sprache.tr)
print(ascii(f"Einrichtblatt: {futter_text} | {null_text}"))
pruefe(f"Dreibackenfutter Ø {futter_d:g}" in futter_text, f"Einrichtblatt Spannung: {futter_text}")
pruefe("nach dem Schwenken auf A −90" in null_text, f"Einrichtblatt Nullpunkt: {null_text}")
# Mit dem Schwenkzyklus (Siemens, wie „Programm schreiben“ ihn schreibt): ungeschwenkt.
zyklus_text = eb.nullpunkt_text(job, sprache.tr, steuerung=steuerung_zyklus["siemens"])
print(ascii(f"Einrichtblatt mit Zyklus: {zyklus_text}"))
pruefe(
    "ungeschwenkt" in zyklus_text
    and "mittig im Rohr" in zyklus_text
    and f"{eb._zahl(vorn)} mm über der Stirn des Teils" in zyklus_text
    and "CYCLE800" in zyklus_text,
    f"Einrichtblatt mit Zyklus: {zyklus_text}",
)
ohne_text = eb.nullpunkt_text(job, sprache.tr, steuerung=ohne_zyklus["siemens"])
pruefe("nach dem Schwenken" in ohne_text, f"Einrichtblatt Haken aus: {ohne_text}")
sprache.setze_sprache("en")
englisch = eb.nullpunkt_text(job, sprache.tr, steuerung=steuerung_zyklus["heidenhain"])
sprache.setze_sprache("de")
pruefe("unswivelled" in englisch and "PLANE SPATIAL" in englisch, f"englisch: {englisch}")
ohne = pp.abschnitte(job)  # ohne Maschine: nicht ins Programm
pruefe(
    ohne and not ohne[0].befehle and "geschwenkter Lage (A −90°)" in ohne[0].hinweis,
    f"ohne Maschine: {[(a.hinweis, len(a.befehle)) for a in ohne]}",
)

# --- Kollision und Rest -------------------------------------------------------------------------
fahrt = ab.abfahrt(p, job, nullpunkt, bib)
# Das Prüffenster sagt, wovon „Spitze im Programm“ zählt: nach dem Schwenken (Haken aus); mit dem
# Haken nennt der Satz die Stirn der Stange.
bezuege = [o.bezug for o in fahrt.operationen]
pruefe(bezuege == [sprache.tr("ab.bezug.geschwenkt")], f"Spitze zählt von: {bezuege}")
satz_pruef = ab.programm_nullpunkt_text(job, p)
pruefe(satz_pruef == sprache.tr("rw.nullpunkt.geschwenkt"), f"Prüffenster: {satz_pruef!r}")
kollision = kb.kollision(fahrt, job, nullpunkt, bib)
texte = [b.text() for b in kollision.befunde]
print(ascii(f"Kollision: {len(fahrt.stationen)} Stationen, {texte[:3]}"))
pruefe(not kollision.befunde, f"Befunde: {texte[:3]}")
# Geschwenkt wird über der Achse von C (das Programm fährt dorthin, die Prüfung mit): X, Y im
# Programm bei Rundachsen 0 auf C – vom Nullpunkt nach dem Schwenken aus gezählt.
ueber = [s.punkt for s in fahrt.stationen if 1e-6 < abs(s.rund.get("A", 0.0)) < 90.0 - 1e-6]
soll_ueber = (-schwenkung.versatz[0], -schwenkung.versatz[1])
pruefe(
    ueber and all(math.dist(u[:2], soll_ueber) < 1e-6 for u in ueber),
    f"geschwenkt bei {ueber[:1]}, soll über C {soll_ueber}",
)
abtrag = rm.fuer(fahrt, job, fahrt.am_werkstueck())
abtrag.bis_station(len(fahrt.stationen) - 1)
vergleich = abtrag.vergleich()
print(ascii(f"Rest: {vergleich.kleinster:.3f} … {vergleich.groesster:.3f} mm"))
pruefe(vergleich.kleinster > -rm.BLAU_AB, f"ins Teil: {vergleich.kleinster:.3f} mm")
# Gegenprobe: Backen so hoch, dass sie bis an die Nut reichen – das Werkzeug trifft das Futter.
setattr(job, vr.EIGENSCHAFT_SPANNLAENGE, 118.0)
gegen = kb.kollision(fahrt, job, nullpunkt, bib)
futter_texte = [b.text() for b in gegen.befunde if "Dreibackenfutter" in b.text()]
pruefe(
    futter_texte, f"Gegenprobe: das Futter trifft nichts ({[b.text() for b in gegen.befunde][:2]})"
)
setattr(job, vr.EIGENSCHAFT_SPANNLAENGE, vr.SPANNLAENGE)

# --- Mischjob: danach die Stirn von oben planen (A 0) --------------------------------------------
# Das Programm schwenkt nach der geschwenkten Lage zurück (hoch, über C, A 0), die Prüfung fährt
# es mit; die geschwenkte Lage bekommt den nächsten Nullpunkt (G55, nach dem Schwenken
# eingerichtet), die Stirn behält G54 bei A 0.
plan = doc.addObject("Path::Feature", "StirnPlanen")
plan.addProperty("App::PropertyLink", "ToolController")
plan.ToolController = tc
plan.addProperty("App::PropertyBool", "Active")
plan.Active = True
plan.Path = Path.Path(
    [
        Path.Command("G0", {"X": -40.0, "Y": 0.0, "Z": 10.0}),
        Path.Command("G1", {"Z": 0.5, "F": 5.0}),
        Path.Command("G1", {"X": 40.0, "F": 5.0}),
        Path.Command("G0", {"Z": 10.0}),
    ]
)
job.Operations.Group = [op, plan]
doc.recompute()
misch = ab.abfahrt(p, job, nullpunkt, bib)
erste_plan = misch.operationen[1].erste
nach = [s.rund.get("A", 0.0) for s in misch.stationen[misch.operationen[0].erste : erste_plan]]
pruefe(
    any(1e-6 < abs(a) < 90.0 - 1e-6 for a in nach[-95:]) and abs(nach[-1]) < 1e-9,
    f"Mischjob: nicht zurückgeschwenkt ({nach[-3:]})",
)
pruefe(
    all(abs(s.rund.get("A", 0.0)) < 1e-9 for s in misch.stationen[erste_plan:]),
    "Mischjob: die Stirn mit gekipptem Tisch",
)
misch_befunde = [b.text() for b in kb.kollision(misch, job, nullpunkt, bib).befunde]
pruefe(not misch_befunde, f"Mischjob: {misch_befunde[:2]}")
zeilen = pp.programm(
    pp.abschnitte(job, maschine=maschine_sw), ohne_zyklus["siemens"], info, "Rohr"
).zeilen
an = next((i for i, z in enumerate(zeilen) if z == "G0 A1=-90.000"), -1)
zurueck = next((i for i, z in enumerate(zeilen) if z == "G0 A1=0.000"), -1)
g54 = [i for i, z in enumerate(zeilen) if z.startswith("G54")]
g55 = [i for i, z in enumerate(zeilen) if z.startswith("G55")]
print(ascii(f"Mischjob: G55 {g55}, A-90 {an}, A0 {zurueck}, G54 {g54}"))
pruefe(g55 and g55[0] < an < zurueck and g54 and g54[-1] > zurueck, "Mischjob: Nullpunkte")
pruefe(
    any(re.search(r"G55: .*A [−-]90 und C 0 schwenken", z) for z in zeilen),
    "Mischjob: Kopf ohne G55",
)
misch_null = eb.nullpunkt_text(job, sprache.tr)
pruefe("G54 ungeschwenkt" in misch_null and "G55 nach dem Schwenken" in misch_null, misch_null)
# Mit dem Schwenkzyklus: ein Nullpunkt für beide (G54 an der Stirn der Stange) – die Stirn von oben
# zählt ebenso von dort (Z 0,5 über der Stirn des Teils: 0,5 − Planaufmaß).
zeilen = pp.programm(
    pp.abschnitte(job, maschine=maschine_sw), steuerung_zyklus["siemens"], info, "Rohr"
).zeilen
plan_z = [float(w) for z in zeilen for w in re.findall(r"^G1 Z(-?\d+\.\d+)", z)]
print(ascii(f"Mischjob mit Zyklus: G55 {[z for z in zeilen if z.startswith('G55')]}, {plan_z}"))
pruefe(not any(z.startswith("G55") for z in zeilen), "Mischjob mit Zyklus: G55")
pruefe(any(abs(z - (0.5 - vorn)) < 1e-3 for z in plan_z), f"Mischjob: Stirn Z {plan_z}")
misch_zyklus = eb.nullpunkt_text(job, sprache.tr, steuerung=steuerung_zyklus["siemens"])
pruefe("G55" not in misch_zyklus and "ungeschwenkt" in misch_zyklus, misch_zyklus)

FreeCAD.closeDocument(doc.Name)
FreeCAD.closeDocument(asm.Document.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
