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
pruefe(op.Schwenkstellung == "A90" and op.Werkzeugrichtung == V(0, 1, 0), "Operation")
pruefe("C" in achsen_der_bahn and "A" not in achsen_der_bahn, f"Bahn: {achsen_der_bahn}")
# Vorn in der Bahn: Nur über „Programm schreiben“ des Addons ist sie ein Maschinenprogramm.
pruefe(
    any(b.Name.startswith(vo.KOMMENTAR_GESCHWENKT) for b in befehle[:3]),
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


def neben_der_bahn(saetze, null, nach_dem_schwenken=True, versatz=(0.0, 0.0, 0.0)):
    """So weit (mm) steht die Spitze höchstens neben der Bahn, wenn die Maschine `saetze` fährt
    und das Teil am Nullpunkt `null` sitzt – eingerichtet wie der Einrichter: nach dem Schwenken
    (A fest, C 0) die Spitze an die Stirn auf der Achse (G54), oder bei A 0 (`versatz` dazu: so
    rechnete das Programm bis zum Fund des Zweiflers). Ohne TCPM: X, Y, Z sind die Linearachsen
    ab G54, je 1 mm wie die Spitze bei A 0 C 0 im Teil fährt; A und C wie das Gelenk."""
    verfahren.grundstellung()
    start = np.array([verfahren.stellung(a) for a in linear])
    j0, _s = jacobi(null)  # X, Y, Z im Programm: wie bei Rundachsen 0
    if nach_dem_schwenken:
        for buchstabe, wert in achse.schwenk:
            verfahren.setze(rund[buchstabe], wert, grenzen=False)
    js, s = jacobi(null)
    g54 = start + np.linalg.lstsq(js, -np.array(tuple(s)), rcond=None)[0]  # Spitze an der Stirn
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

# --- Das Programm: erst hoch, A fest, C dreht, am Ende zurück ---------------------------------
maschine_sw = sw.Maschine(p, aufnahme, eins, nullpunkt)
info = pp.maschineninfo_dokument(asm.Document)
for kennung, schwenken, zurueck, c_wort in (
    ("siemens", "G0 A1=-90.000", "G0 A1=0.000", r"C1="),
    ("heidenhain", "L A-90.000 R0 FMAX", "L A+0.000 R0 FMAX", r" C[+-]\d"),
):
    programm = pp.programm(
        pp.abschnitte(job, maschine=maschine_sw), pp.steuerung(kennung), info, "Rohr"
    )
    zeilen = [z.split(" ", 1)[1] if kennung == "heidenhain" else z for z in programm.zeilen]
    an = next((i for i, z in enumerate(zeilen) if z == schwenken), -1)
    erste_c = next((i for i, z in enumerate(zeilen) if re.search(c_wort, z)), -1)
    hoch = zeilen[an - 2] if an > 1 else ""  # erst hoch, dann über C, dann schwenken
    ueber_c = zeilen[an - 1] if an > 0 else ""
    print(
        ascii(
            f"{kennung}: {hoch} | {zeilen[an] if an >= 0 else '-'} | Hinweise {programm.hinweise}"
        )
    )
    pruefe(
        0 < an < erste_c and "Z" in hoch and "X" in ueber_c and "Y" in ueber_c,
        f"{kennung}: Schwenken {an} ({hoch} | {ueber_c}), erstes C {erste_c}",
    )
    pruefe(sum(z.startswith(schwenken) for z in zeilen) == 1, f"{kennung}: A mehrmals")
    pruefe(zurueck in zeilen[erste_c:], f"{kennung}: am Ende nicht zurück")
    pruefe(not programm.hinweise, f"{kennung}: {programm.hinweise}")
    pruefe(not any("CAM-Addon:" in z for z in zeilen), f"{kennung}: Kommentar der Bahn im Programm")
    # Im Kopf: G54 wird nach dem Schwenken eingerichtet (A wie die Steuerung zählt).
    kopf = [z for z in zeilen if re.search(r"G54: .*A [−-]90 und C 0 schwenken", z)]
    pruefe(kopf, f"{kennung}: Kopf ohne Nullpunkt nach dem Schwenken")
# Einrichtblatt: das Futter auf dem Rundtisch und der Nullpunkt nach dem Schwenken.
futter_text = eb.spannung_text(job, sprache.tr)
null_text = eb.nullpunkt_text(job, sprache.tr)
print(ascii(f"Einrichtblatt: {futter_text} | {null_text}"))
pruefe(f"Dreibackenfutter Ø {futter_d:g}" in futter_text, f"Einrichtblatt Spannung: {futter_text}")
pruefe("nach dem Schwenken auf A −90" in null_text, f"Einrichtblatt Nullpunkt: {null_text}")
ohne = pp.abschnitte(job)  # ohne Maschine: nicht ins Programm
pruefe(
    ohne and not ohne[0].befehle and "geschwenkter Lage" in ohne[0].hinweis,
    f"ohne Maschine: {[(a.hinweis, len(a.befehle)) for a in ohne]}",
)

# --- Kollision und Rest -------------------------------------------------------------------------
fahrt = ab.abfahrt(p, job, nullpunkt, bib)
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
    pp.abschnitte(job, maschine=maschine_sw), pp.steuerung("siemens"), info, "Rohr"
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

FreeCAD.closeDocument(doc.Name)
FreeCAD.closeDocument(asm.Document.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
