# Prüft die 4. Achse auf der 3-Achs-Fräse (Manuel, 2026-11-15: „die 4te achse würde es eher in ein
# drei backenfutter horizonal entlang der x oder y achse so das die z achse vertikal von oben drauf
# schaut spannen ! und vll sogar mit einem reitstock stützen ..“): die Beispielmaschine
# „3-Achs-Fräse mit 4. Achse“ (beispielmaschine.fraese_vierte_achse) – Teilapparat A längs X mit
# Dreibackenfutter, gegenüber der Reitstock.
#
# Rohr Ø 60 / Ø 50 × 150 längs X mit der Kurvennut 12 breit über 200° (wie test_vierachs_kurvennut,
# mit dem Fräser selbst geschnitten), „Plan indexiert“ mit T1 Ø 8 (ER32 an SK40), mit Reitstock.
# Geprüft: von_maschine liefert A längs X, das Werkzeug von oben; die Stange steckt mit der
# Spannlänge in den Backen, vorn der Zapfen für die Zentrierbohrung; anstellen() bringt die Spitze
# an die Stirn der Stange; die Maschine (verfahren) auf die Achswerte der Sätze gestellt trifft die
# Spitze die Bahn; Siemens, Heidenhain und LinuxCNC schreiben A wie die Bahn (nach DIN umgedreht);
# Kollision: nichts berührt sich, Futter und Reitstock nicht getroffen, nirgends ins Teil;
# Einrichtblatt: die Zentrierbohrung.
# Dazu „Rundum schruppen“ an einer Welle Ø 30 (dünner als die Pinole) in der Stange Ø 40: Die
# Bahn hält vor der Stange Abstand zur Spitze; mit einem zu kurzen Abstand meldet die Kollision
# den Reitstock.
#
# Nacharbeit nach dem Zweifler (2026-11-14):
# - Anfahrt: Nach „T1 M6“ fährt das Programm oben über den ersten Punkt und erst dann Z hinunter
#   (postprozessor._erst_ueber_den_punkt) – aus einer Startstellung über Reitstock oder Futter
#   geht der erste Eilgang nicht hinein (Gegenprobe: die Bahn selbst, Z zuerst, ginge hinein); das
#   Abfahren beginnt am Wechselpunkt oben.
# - Rest vorn: Die Welle wird bis an ihre Stirn gefräst wie in der Mitte (bis 0.377 blieben dort
#   vorn 5 mm am Radius stehen); eine vorn offene Fläche fräst „Plan indexiert“ bis vor ihre Stirn
#   (bis 0.377 8,25 mm zu kurz). Der Zapfen bleibt so dick wie das Teil vorn, mindestens Ø 17.
# - Einrichtblatt: X 0 mit der Zahl (Zapfen hinter der Stirn der Stange) und der Ausspannlänge;
#   der Zapfen wie die Stange ihn hat (mit Planaufmaß 15 15 mm).
# - Reicht der Reitstock nicht: Anstellung.reicht ist falsch, mit fehlt und zu_lang (für das rote
#   Urteil); „Ohne Reitstock“ schaltet den Job um.
# - Zeigt X der Werkstückaufnahme ins Futter, sagt es die Prüfung (Gegenprobe: LCS umgedreht).
import math
import os
import re
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import abfahren as ab
from camaddon import beispielmaschine as bm
from camaddon import einrichtblatt as eb
from camaddon import halter as hl
from camaddon import kollision as kb
from camaddon import maschine as m
from camaddon import postprozessor as pp
from camaddon import reichweite as rw
from camaddon import reitstock as rs
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import verfahren as vf
from camaddon import vierachs_achsen as va
from camaddon import vierachs_huelle as vh
from camaddon import vierachs_operation as vo
from camaddon import vierachs_plan as vplan
from camaddon import vierachs_planbahn as vp
from camaddon import vierachs_rohteil as vr
from camaddon import werkzeuge as wz
from camaddon.kette import LINEAR

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
V = FreeCAD.Vector
RA, RI, LANG = 30.0, 25.0, 150.0
BREITE, WINKEL, A0, A1 = 12.0, 200.0, 55.0, 95.0


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

# --- Die Maschine: A längs X, das Werkzeug von oben, ein Reitstock -------------------------------
asm, ma = bm.fraese_vierte_achse()
achsen = va.von_maschine(asm, ma)
print(ascii(f"Achsen: {[(a.buchstabe, tuple(a.laengs), a.schwenk) for a in achsen]}"))
pruefe(len(achsen) == 1, f"Stangenachsen: {achsen}")
achse = achsen[0]
pruefe(
    achse.buchstabe == "A"
    and achse.laengs == V(1, 0, 0)
    and va.radial(achse) == V(0, 0, 1)
    and not achse.schwenk,
    f"A: {achse}",
)
pruefe(rs.hat_reitstock(asm), "kein Reitstock gefunden")
pruefe(not rs.hat_reitstock(bm.fraesmaschine()[0]), "die 3-Achs-Fräse hat einen Reitstock")
warnungen = [x.text for x in m.pruefe(ma) if x.schwere != "hinweis"]
pruefe(not warnungen, f"Warnungen der Maschine: {warnungen}")

# --- Job: das Rohr mit Reitstock ------------------------------------------------------------------
doc = FreeCAD.newDocument("RohrVierteAchse")
teil = doc.addObject("Part::Feature", "Rohr")
teil.Shape = form
doc.recompute()
stirn = next(
    f for f in form.Faces if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
)
lage = vr.berechne(form, stirn, achse, durchmesser=60)
# Vorbelegt erst, wenn die Stange weiter als 3 × Ø herausragt: Ø 60 mit 154 mm nicht, Ø 50 schon.
pruefe(not vr.reitstock_vorgabe(lage.vermessung, vr.Stange(60.0)), "Vorgabe bei 154 mm aus Ø 60")
pruefe(vr.reitstock_vorgabe(lage.vermessung, vr.Stange(50.0)), "keine Vorgabe bei 154 mm aus Ø 50")
stange = vr.Stange(60.0, reitstock=True)
job = vr.richte_ein(doc, teil, lage, stange, achse)
laenge = float(job.Stock.Height)
soll_laenge = vr.REITSTOCK_ZAPFEN + LANG + vr.ABSTECHBREITE + vr.SPANNLAENGE
pruefe(vr.mit_reitstock(job) and abs(laenge - soll_laenge) < 1e-6, f"Stange {laenge} lang")
einst = vr.einstellung(job)
pruefe(einst is not None and einst.stange.reitstock, "Einstellung ohne Reitstock")
tc = job.Tools.Group[0]
tc.Tool.Diameter = 8
tc.ToolNumber = 1
tc.HorizFeed = "800 mm/min"
tc.SpindleSpeed = 6000
bib = wz.Bibliothek()
halter = bib.neuer_halter("er32", None, "SK40")
t1 = bib.neues_werkzeug()
t1.nummer, t1.durchmesser, t1.laenge_spindelnase, t1.halter = 1, 8.0, 125.0, halter.kennung
t1.schneidenlaenge = 25.0
modell = vr.modell(job).Shape
alle = [f"Face{i + 1}" for i in range(len(modell.Faces))]
nut = vp.kurvennuten(modell, tuple(achse.laengs), tuple(va.radial(achse)), alle)[0]
op = vplan.lege_an(job, tc, achse, 4.0, 2.0, aufmass=0.0, flaechen=list(nut.namen))
doc.recompute()
befehle = list(op.Path.Commands)
pruefe(sum(1 for b in befehle if "A" in b.Parameters) > 20, "die Kurvennut ohne A")

# --- Nullpunkt und Reitstock -------------------------------------------------------------------
ergebnis = rs.anstellen(asm, ma, job)
print(ascii(f"Reitstock: {ergebnis}"))
pruefe(ergebnis is not None and not ergebnis.meldung, f"anstellen: {ergebnis}")
p = rw.Pruefung(asm, ma)
nullpunkt = rw.nullpunkt(job, p)
spannflaeche = job.Stock.Placement.Base + V(vr.SPANNLAENGE, 0, 0)  # im Job
pruefe(
    (spannflaeche + nullpunkt).Length < 1e-6,
    f"Spannfläche {tuple(spannflaeche + nullpunkt)} neben der Aufnahme",
)
gefunden = rs.finde(asm)
vorne = job.Stock.Placement.multVec(V(0, 0, laenge))
an_der_spitze = p._job_lage(nullpunkt, {}).multVec(vorne) - m.globale_platzierung(gefunden.lcs).Base
pruefe(
    an_der_spitze.Length < 1e-6, f"Stirn der Stange {an_der_spitze.Length:.3f} mm neben der Spitze"
)
nochmal = rs.anstellen(asm, ma, job)
pruefe(nochmal is not None and not nochmal.bewegt, "anstellen bewegt ein zweites Mal")

# --- Die Spitze, wenn die Maschine die Achswerte eines Satzes fährt (eigene Rechnung) ------------
aufnahme_ws = p.werkstueckaufnahme
aufnahme = p.werkzeugaufnahme(1)
eins = rw.einspannung(tc, bib)
verfahren = vf.Verfahren(asm)
linear = [a for a in verfahren.achsen if a.art == LINEAR and a.gelenk.Label in ("X", "Y", "Z")]
a1 = next(a for a in p.kette.achsen if p.programmbuchstabe(a) == "A")
a_eigene = next(a for a in verfahren.achsen if a.gelenk is a1.gelenk)
stand, saetze = {}, []
for b in befehle:
    stand.update({x: float(w) for x, w in b.Parameters.items() if x in "XYZA"})
    if b.Name == "G1" and "A" in stand:
        saetze.append(dict(stand))
saetze = saetze[:: max(1, len(saetze) // 15)]


def spitze_im_job():
    welt = m.globale_platzierung(aufnahme.Lcs).multVec(eins.spitze())
    job_welt = m.globale_platzierung(aufnahme_ws.Lcs).multiply(
        FreeCAD.Placement(nullpunkt, FreeCAD.Rotation())
    )
    return job_welt.inverse().multVec(welt)


verfahren.grundstellung()
s0 = spitze_im_job()
spalten = []
for a in linear:
    verfahren.setze(a, verfahren.stellung(a) + 1.0, grenzen=False)
    spalten.append(tuple(spitze_im_job() - s0))
    verfahren.setze(a, verfahren.stellung(a) - 1.0, grenzen=False)
jacobi = np.array(spalten).T
start = {a: verfahren.stellung(a) for a in linear}
groesste = 0.0
for satz in saetze:
    punkt = V(*(satz.get(x, 0.0) for x in "XYZ"))
    wege = np.linalg.lstsq(jacobi, np.array(tuple(punkt - s0)), rcond=None)[0]
    for a, w in zip(linear, wege, strict=True):
        verfahren.setze(a, start[a] + w, grenzen=False)
    verfahren.setze(a_eigene, satz["A"], grenzen=False)  # die Stellung zählt wie das Gelenk
    soll = FreeCAD.Rotation(V(achse.laengs), -achse.drehsinn * satz["A"]).multVec(punkt)
    groesste = max(groesste, (spitze_im_job() - soll).Length)
    verfahren.grundstellung()
print(ascii(f"Spitze an {len(saetze)} Sätzen: höchstens {groesste:.6f} mm neben der Bahn"))
pruefe(len(saetze) >= 5 and groesste < 1e-6, f"Spitze {groesste:.4f} mm neben der Bahn")
reich = p.pruefe_job(job, nullpunkt, bib)
pruefe(not reich.ueberschreitungen, f"über: {[u.text() for u in reich.ueberschreitungen][:2]}")
pruefe(not rw._laengs_ins_futter(p, job), "X der Spannfläche zeigt ins Futter")
# Gegenprobe: das LCS der Spannfläche um Z gedreht – X zeigt ins Futter, die Prüfung sagt es.
lcs = p.werkstueckaufnahme.Lcs
alt_lage = FreeCAD.Placement(lcs.Placement)
lcs.Placement = lcs.Placement.multiply(FreeCAD.Placement(V(), FreeCAD.Rotation(V(0, 0, 1), 180)))
asm.Document.recompute()
umgedreht = rw.Pruefung(asm, ma)
satz = [h for h in umgedreht.pruefe_job(job, None, bib).hinweise if "Futter" in h]
print(ascii(f"Gegenprobe LCS umgedreht: {satz}"))
pruefe(rw._laengs_ins_futter(umgedreht, job) and satz, "LCS umgedreht: nichts gesagt")
lcs.Placement = alt_lage
asm.Document.recompute()

# --- Das Programm: A wie die Bahn (nach DIN 66217 umgedreht, wenn die Prüfung es sagt) ------------
# Die Fräse zählt X wie die Steuerung (der Tisch fährt mit X plus nach links): Nach DIN dreht +A
# das Werkzeug rechtsherum um +X, das Teil also andersherum als das Gelenk – das Programm schreibt
# A umgedreht, und das Prüffenster zählt genauso.
vorzeichen = vf.programm_vorzeichen(a1, p.kette)
pruefe(vorzeichen == -1 and "A" in p.umgekehrt, f"A: Vorzeichen {vorzeichen}, {p.umgekehrt}")
in_der_bahn = [float(b.Parameters["A"]) for b in befehle if "A" in b.Parameters]
info = pp.maschineninfo_dokument(asm.Document)


def wie_die_bahn(wert):
    """Steht `wert` (A im Programm, an einer Moduloachse 0 … 360) so in der Bahn?"""
    return any(abs((wert - vorzeichen * y + 180.0) % 360.0 - 180.0) < 1e-3 for y in in_der_bahn)


for kennung, muster in (
    ("siemens", r"\bA1=(?:AC[PN]\()?(-?\d+\.\d+)"),
    ("heidenhain", r"\bA([+-]\d+\.\d+)"),
    ("linuxcnc", r"\bA(-?\d+\.\d+)"),
):
    programm = pp.programm(pp.abschnitte(job), pp.steuerung(kennung), info, "Rohr")
    werte = [float(w) for z in programm.zeilen for w in re.findall(muster, z.split(";")[0])]
    gleich = [x for x in werte if wie_die_bahn(x)]
    print(
        ascii(f"{kennung}: {len(werte)} A-Wörter, {len(gleich)} wie die Bahn, {programm.hinweise}")
    )
    pruefe(not programm.hinweise, f"{kennung}: {programm.hinweise}")
    pruefe(len(werte) >= len(set(in_der_bahn)) // 2, f"{kennung}: nur {len(werte)} A-Wörter")
    pruefe(len(gleich) >= len(werte) - 2, f"{kennung}: A nicht wie die Bahn ({werte[:5]})")

# --- Die erste Anfahrt: oben über den Punkt, dann Z hinunter ----------------------------------
# Wo Teilapparat, Futter und Reitstock im Job stehen (Hüllboxen; Z oben, X von – bis).
welt_job = m.globale_platzierung(p.werkstueckaufnahme.Lcs).multiply(
    FreeCAD.Placement(nullpunkt, FreeCAD.Rotation())
)
kisten = {}
for o in asm.Document.Objects:
    if o.Label in ("Teilapparat", "Futterkoerper", "Reitstockkoerper"):
        lage_im_job = (
            welt_job.inverse().multiply(m.globale_platzierung(o)).multiply(o.Placement.inverse())
        )
        kisten[o.Label] = o.Shape.transformGeometry(lage_im_job.toMatrix()).BoundBox
pruefe(len(kisten) == 3, f"Spannmittel: {sorted(kisten)}")
RADIUS_T1 = 4.0


def hinein(zeilen, start):
    """Fährt der erste Eilgang nach dem Wechsel (Z oben, X/Y wie `start`) in ein Spannmittel?
    Die Sätze nach „M6“/„TOOL CALL“ bis zum ersten mit Z: ändert sich Z, fährt die Spindel an der
    X/Y-Stelle dieses Satzes hinunter (ohne X/Y im Satz: an der alten). Gibt den Namen oder ""."""
    x, y = start
    nach = False
    for zeile in zeilen:
        roh = re.sub(r"\(.*?\)", "", zeile.split(";")[0])
        if not nach:
            nach = bool(re.search(r"\bM0?6\b|TOOL CALL", roh))
            continue
        worte = dict(re.findall(r"\b([XYZ])([+-]?\d+(?:\.\d*)?)", roh))
        x, y = float(worte.get("X", x)), float(worte.get("Y", y))
        if "Z" in worte:
            z = float(worte["Z"])
            for name, k in kisten.items():
                ueber = k.XMin - RADIUS_T1 < x < k.XMax + RADIUS_T1
                ueber = ueber and k.YMin - RADIUS_T1 < y < k.YMax + RADIUS_T1
                if ueber and z < k.ZMax:
                    return name
            return ""
    return "kein Satz mit Z"


starts = {
    "über dem Reitstock": (kisten["Reitstockkoerper"].Center.x, 0.0),
    "über dem Futter": (kisten["Futterkoerper"].Center.x, 0.0),
}
for kennung in ("siemens", "heidenhain", "linuxcnc"):
    zeilen = pp.programm(pp.abschnitte(job), pp.steuerung(kennung), info, "Rohr").zeilen
    for wo, start in starts.items():
        getroffen = hinein(zeilen, start)
        pruefe(not getroffen, f"{kennung}: der erste Eilgang {wo} fährt in {getroffen}")
# Gegenprobe: in der Reihenfolge der Bahn (G0 Z allein zuerst, wie bis 0.377 im Programm).
bahn_zeilen = ["M6"] + [
    " ".join([b.Name] + [f"{k}{float(w):.3f}" for k, w in b.Parameters.items()]) for b in befehle
]
gegen = hinein(bahn_zeilen, starts["über dem Reitstock"])
print(ascii(f"Gegenprobe Z zuerst über dem Reitstock: {gegen}"))
pruefe(gegen == "Reitstockkoerper", f"Gegenprobe: {gegen}")

# --- Einrichtblatt -----------------------------------------------------------------------------
text = eb.spannung_text(job, sprache.tr)
print(ascii(f"Einrichtblatt: {text}"))
pruefe("Reitstock" in text and "DIN 332" in text, f"Einrichtblatt: {text}")
pruefe(f"Zapfen {eb._zahl(vr.REITSTOCK_ZAPFEN)}" in text, f"Zapfen im Einrichtblatt: {text}")
null_text = eb.nullpunkt_text(job, sprache.tr)
print(ascii(f"Nullpunkt: {null_text}"))
raus = laenge - vr.SPANNLAENGE
pruefe(
    f"{eb._zahl(vr.REITSTOCK_ZAPFEN)} " in null_text and f"{eb._zahl(raus)} " in null_text,
    f"Nullpunkt ohne Zapfen {vr.REITSTOCK_ZAPFEN} oder Ausspannlänge {raus}: {null_text}",
)
# Mit Planaufmaß 15 ist der Zapfen 15 lang – nicht „mindestens 10“.
doc15 = FreeCAD.newDocument("RohrPlan15")
teil15 = doc15.addObject("Part::Feature", "Rohr")
teil15.Shape = form
doc15.recompute()
job15 = vr.richte_ein(doc15, teil15, lage, vr.Stange(60.0, 15.0, reitstock=True), achse)
text15 = eb.spannung_text(job15, sprache.tr) + " | " + eb.nullpunkt_text(job15, sprache.tr)
print(ascii(f"Planaufmaß 15: {text15}"))
pruefe(
    f"Zapfen {eb._zahl(15.0)}" in text15 and f"{eb._zahl(15.0)} " in text15.split(" | ")[1],
    f"Planaufmaß 15: {text15}",
)
FreeCAD.closeDocument(doc15.Name)

# --- Kollision und Rest: Futter und Reitstock nicht getroffen, nirgends ins Teil ------------------
fahrt = ab.abfahrt(p, job, nullpunkt, bib)
# Die erste Operation kommt vom Wechselpunkt oben: erst über den ersten Punkt, dann hinunter.
erste_bahn = next(i for i, st in enumerate(fahrt.stationen) if not st.ziel)
davor = fahrt.stationen[erste_bahn - 1] if erste_bahn else None
pruefe(
    fahrt.stationen[0].ziel == ab.WECHSEL
    and davor is not None
    and davor.ziel == ab.WECHSEL
    and abs(davor.punkt[0] - fahrt.stationen[erste_bahn].punkt[0]) < 1e-6
    and abs(davor.punkt[1] - fahrt.stationen[erste_bahn].punkt[1]) < 1e-6
    and davor.punkt[2] > fahrt.stationen[erste_bahn].punkt[2] + 50.0,
    f"Anfahrt: {[(st.ziel, tuple(round(x, 1) for x in st.punkt)) for st in fahrt.stationen[:4]]}",
)
kollision = kb.kollision(fahrt, job, nullpunkt, bib)
texte = [b.text() for b in kollision.befunde]
print(ascii(f"Kollision: {len(fahrt.stationen)} Stationen, {texte[:3]}"))
pruefe(not kollision.befunde, f"Befunde: {texte[:3]}")
abtrag = rm.fuer(fahrt, job, fahrt.am_werkstueck())
abtrag.bis_station(len(fahrt.stationen) - 1)
vergleich = abtrag.vergleich()
print(ascii(f"Rest: {vergleich.kleinster:.3f} … {vergleich.groesster:.3f} mm"))
pruefe(vergleich.kleinster > -rm.BLAU_AB, f"ins Teil: {vergleich.kleinster:.3f} mm")
FreeCAD.closeDocument(doc.Name)

# --- Rundum schruppen vor der Spitze: Welle Ø 30 in der Stange Ø 40 -----------------------------
doc = FreeCAD.newDocument("WelleReitstock")
welle = doc.addObject("Part::Feature", "Welle")
welle.Shape = Part.makeCylinder(15.0, 80.0, V(), V(1, 0, 0))
doc.recompute()
stirn = next(
    f
    for f in welle.Shape.Faces
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
)
lage = vr.berechne(welle.Shape, stirn, achse, durchmesser=40)
job = vr.richte_ein(doc, welle, lage, vr.Stange(40.0, frei_hinten=20.0, reitstock=True), achse)
tc = job.Tools.Group[0]
tc.Tool.Diameter = 12
tc.ToolNumber = 1
tc.HorizFeed = "1500 mm/min"
t1.durchmesser, t1.schneidenlaenge = 12.0, 25.0
schruppen = vo.lege_an(job, tc, achse, 5.0, 4.8, 0.3, halter=hl.seitlich(halter))
doc.recompute()
befehle = list(schruppen.Path.Commands)
a_vorne = float(job.Stock.Placement.Base.x) + float(job.Stock.Height)
stand, r_vorn = {"X": 0.0, "Y": 0.0, "Z": 0.0}, []
for b in befehle:
    stand.update({x: float(w) for x, w in b.Parameters.items() if x in "XYZ"})
    if b.Name == "G1" and stand["X"] > a_vorne - 6.0:
        r_vorn.append(math.hypot(stand["Y"], stand["Z"]))
schutz = rs.schutz_radius(float(schruppen.AbstandFutter))
print(ascii(f"Schruppen: {len(befehle)} Sätze, vor der Stirn höchstens bis r {min(r_vorn):.2f}"))
pruefe(r_vorn and min(r_vorn) >= schutz - 1e-6, f"vor der Stirn bis r {min(r_vorn):.2f}")
# Der Rest vorn an der Welle (Zweifler: bis 0.377 r 22,82 in den letzten 6 mm vor ihrer Stirn,
# 5 mm am Radius stehen geblieben): dort wie in der Mitte; im Zapfen nicht dünner als die Welle.
r_bereich = {"vorn": [], "mitte": [], "zapfen": []}
stand = {"X": 0.0, "Y": 0.0, "Z": 0.0}
for b in befehle:
    stand.update({x: float(w) for x, w in b.Parameters.items() if x in "XYZ"})
    if b.Name != "G1":
        continue
    r = math.hypot(stand["Y"], stand["Z"])
    if -6.0 <= stand["X"] <= 0.0:
        r_bereich["vorn"].append(r)
    elif -50.0 <= stand["X"] <= -30.0:
        r_bereich["mitte"].append(r)
    elif 0.0 < stand["X"] <= a_vorne:
        r_bereich["zapfen"].append(r)
kleinste = {k: min(v) if v else math.inf for k, v in r_bereich.items()}
print(ascii(f"Schruppen, kleinster Radius der Bahn: {kleinste}"))
pruefe(
    kleinste["vorn"] < kleinste["mitte"] + 0.01,
    f"vorn an der Welle bis r {kleinste['vorn']:.3f}, in der Mitte {kleinste['mitte']:.3f}",
)
pruefe(kleinste["zapfen"] >= 15.0, f"Zapfen bis r {kleinste['zapfen']:.3f} (Welle r 15)")
# Der Schutz: im Zapfen so dick wie die Welle, an einer Welle Ø 12 mindestens Ø 17 – mit Satz.
geschuetzt = rs.schutz(job, achse.laengs, 5.0, vh.vernetze(vr.modell(job).Shape))
pruefe(
    geschuetzt is not None
    and abs(float(geschuetzt.radien.min()) - 15.0) < 0.01
    and geschuetzt.zu_duenn == 0.0,
    f"Zapfen der Welle Ø 30: {geschuetzt and (geschuetzt.radien.min(), geschuetzt.zu_duenn)}",
)
duenn_welle = Part.makeCylinder(6.0, 80.0, V(-80.0, 0, 0), V(1, 0, 0))  # im Job, Stirn bei 0
duenn = rs.schutz(job, achse.laengs, 5.0, vh.vernetze(duenn_welle))
pruefe(
    duenn is not None
    and abs(float(duenn.radien.min()) - rs.ZAPFEN_RADIUS_MIN) < 1e-9
    and abs(duenn.zu_duenn - (rs.ZAPFEN_RADIUS_MIN - 6.0)) < 0.01,
    f"Zapfen der Welle Ø 12: {duenn and (duenn.radien.min(), duenn.zu_duenn)}",
)
pruefe(rs.anstellen(asm, ma, job).meldung == "", "Reitstock an die Welle")
p = rw.Pruefung(asm, ma)
nullpunkt = rw.nullpunkt(job, p)


def kollision_vorn(job):
    """Die Kollision der ersten zwei Umdrehungen – dort fährt die Spirale vor der Stirn."""
    fahrt = ab.abfahrt(p, job, nullpunkt, bib)
    bis = next(
        (i for i, s in enumerate(fahrt.stationen) if abs(s.rund.get("A", 0.0)) > 720.0),
        len(fahrt.stationen),
    )
    anfang = ab.Abfahrt(p, fahrt.achsen, fahrt.stationen[:bis], fahrt.operationen)
    anfang._fertig()
    return [b.text() for b in kb.kollision(anfang, job, nullpunkt, bib).befunde]


texte = kollision_vorn(job)
print(ascii(f"Kollision vorn: {texte[:3]}"))
pruefe(not texte, f"Befunde: {texte[:3]}")
# Gegenprobe: mit 0,5 mm Abstand kommt der Fräser der Pinole näher als der Warnabstand.
schruppen.AbstandFutter = 0.5
doc.recompute()
texte = kollision_vorn(job)
print(ascii(f"Gegenprobe Abstand 0,5: {texte[:3]}"))
pruefe(any("Reitstock" in t for t in texte), f"Gegenprobe: der Reitstock fehlt ({texte[:3]})")

# Ohne Reitstock im Job fährt er aus dem Weg: ans Ende, weit vom Futter.
vorher_x = m.globale_platzierung(gefunden.lcs).Base.x
setattr(job, vr.EIGENSCHAFT_REITSTOCK, False)
weg = rs.anstellen(asm, ma, job)
nachher_x = m.globale_platzierung(gefunden.lcs).Base.x
print(ascii(f"Ohne Reitstock: {weg}, Spitze von x {vorher_x:.1f} nach {nachher_x:.1f}"))
pruefe(weg.bewegt and nachher_x > vorher_x + 100.0, f"ohne Reitstock: {weg}")
FreeCAD.closeDocument(doc.Name)

# --- Reicht der Reitstock nicht: für das rote Urteil, „Ohne Reitstock“ ---------------------------
doc = FreeCAD.newDocument("WelleLang")
lang = doc.addObject("Part::Feature", "Welle")
lang.Shape = Part.makeCylinder(25.0, 340.0, V(), V(1, 0, 0))
doc.recompute()
stirn = next(
    f
    for f in lang.Shape.Faces
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
)
lage = vr.berechne(lang.Shape, stirn, achse, durchmesser=60)
job = vr.richte_ein(doc, lang, lage, vr.Stange(60.0, reitstock=True), achse)
zu_lang = rs.anstellen(asm, ma, job)
print(ascii(f"Stange {float(job.Stock.Height):.0f} lang: {zu_lang}"))
pruefe(
    not zu_lang.reicht and zu_lang.zu_lang and zu_lang.gestuetzt and zu_lang.fehlt > 1.0,
    f"zu lang: {zu_lang}",
)
pruefe(rs.ohne_reitstock(job) and not vr.mit_reitstock(job), "„Ohne Reitstock“ schaltet nicht um")
danach = rs.anstellen(asm, ma, job)
pruefe(danach.reicht and not danach.gestuetzt, f"ohne Reitstock: {danach}")
FreeCAD.closeDocument(doc.Name)

# --- Plan indexiert: eine vorn offene Fläche bis an die Stirn ------------------------------------
# Welle Ø 50 × 100, oben eine Fläche bei z 10 über die vorderen 40 mm (Zweifler: mit Reitstock
# fräste die Bahn sie bis 0.377 nur bis X −8,25 – 8,25 mm blieben 15 mm hoch stehen).
doc = FreeCAD.newDocument("FlaecheVorn")
eben = Part.makeCylinder(25.0, 100.0, V(), V(1, 0, 0)).cut(Part.makeBox(40, 60, 30, V(60, -30, 10)))
eben = eben.removeSplitter()
mit_flaeche = doc.addObject("Part::Feature", "Teil")
mit_flaeche.Shape = eben
doc.recompute()
stirn = next(
    f for f in eben.Faces if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
)
lage = vr.berechne(eben, stirn, achse, durchmesser=50)
job = vr.richte_ein(doc, mit_flaeche, lage, vr.Stange(50.0, reitstock=True), achse)
tc = job.Tools.Group[0]
tc.Tool.Diameter, tc.ToolNumber, tc.HorizFeed, tc.SpindleSpeed = 16, 1, "800 mm/min", 4000
modell = vr.modell(job).Shape
flaeche = next(
    f"Face{i + 1}"
    for i, f in enumerate(modell.Faces)
    if vr.ist_eben(f) and abs(f.normalAt(0, 0).z - 1.0) < 1e-6 and f.BoundBox.ZMax < 11
)
plan = vplan.lege_an(job, tc, achse, 4.0, 8.0, aufmass=0.0, flaechen=[flaeche])
doc.recompute()
stand, auf_der_flaeche = {"X": 0.0, "Y": 0.0, "Z": 0.0}, []
for b in plan.Path.Commands:
    stand.update({x: float(w) for x, w in b.Parameters.items() if x in "XYZ"})
    if b.Name == "G1" and stand["Z"] < 11.0:
        auf_der_flaeche.append(stand["X"])
print(ascii(f"Plan vorn offen: G1 auf der Fläche bis X {max(auf_der_flaeche, default=None)}"))
pruefe(auf_der_flaeche and max(auf_der_flaeche) >= 0.0, f"Fläche bis X {max(auf_der_flaeche)}")
FreeCAD.closeDocument(doc.Name)
FreeCAD.closeDocument(asm.Document.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
