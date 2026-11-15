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
from camaddon import vierachs_bahn as vb
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

# --- Nullpunkt wie Manuel an der 4. Achse: Z 0 oben auf dem Mantel (2026-11-15) -----------------
# „da ist mittig vom rohr 0 und in z richtung der höchste punkt und länge meist x eine seite 0“:
# Die Maschine fährt die Sätze, wie die Prüfung sie liest (Z vom Mantel oben), mit G54 oben auf
# dem Mantel der Stange (Ø 60: 30 über der Achse) – die Spitze trifft die Bahn. Gegenprobe: mit
# G54 auf der Achse (wie bis 0.385) stünde sie 30 mm zu tief.
pruefe(p.vierte_achse(), "die 3-Achs-Fräse mit 4. Achse gilt nicht als Fräse mit 4. Achse")
R_STANGE = 30.0
pruefe(abs(vr.mantel_oben(job) - R_STANGE) < 1e-9, f"Mantel oben: {vr.mantel_oben(job)}")
eins_p = rw.einspannung(tc, bib)
gelesen = p.befehle(op, None, aufnahme, eins_p, nullpunkt)
pruefe(
    p.versatz(op, aufnahme, eins_p, nullpunkt) == (0.0, 0.0, R_STANGE),
    f"Versatz: {p.versatz(op, aufnahme, eins_p, nullpunkt)}",
)
bahn_z = [float(b.Parameters["Z"]) for b in befehle if "Z" in b.Parameters]
prog_z = [float(b.Parameters["Z"]) for b in gelesen if "Z" in b.Parameters]
pruefe(
    len(bahn_z) == len(prog_z)
    and all(abs(a - b - R_STANGE) < 1e-9 for a, b in zip(bahn_z, prog_z, strict=False)),
    "die Sätze der Prüfung zählen Z nicht vom Mantel oben",
)
stand, saetze_prog = {}, []
for b in gelesen:
    stand.update({x: float(w) for x, w in b.Parameters.items() if x in "XYZA"})
    if b.Name == "G1" and "A" in stand:
        saetze_prog.append(dict(stand))
saetze_prog = saetze_prog[:: max(1, len(saetze_prog) // 15)]


def neben_mit_g54(g54_ueber_achse):
    """Die Spitze höchstens so weit neben der Bahn, wenn G54 um `g54_ueber_achse` über dem
    Nullpunkt des Jobs (der Achse) eingerichtet ist und die Maschine die Sätze der Prüfung fährt."""
    verfahren.grundstellung()
    s0_hier = spitze_im_job()
    weit = 0.0
    for satz in saetze_prog:
        punkt = V(*(satz.get(x, 0.0) for x in "XYZ")) + V(0, 0, g54_ueber_achse)
        wege = np.linalg.lstsq(jacobi, np.array(tuple(punkt - s0_hier)), rcond=None)[0]
        for a, w in zip(linear, wege, strict=True):
            verfahren.setze(a, start[a] + w, grenzen=False)
        verfahren.setze(a_eigene, satz["A"], grenzen=False)
        im_teil = V(satz["X"], satz["Y"], satz["Z"] + R_STANGE)  # der Punkt der Bahn im Job
        soll = FreeCAD.Rotation(V(achse.laengs), -achse.drehsinn * satz["A"]).multVec(im_teil)
        weit = max(weit, (spitze_im_job() - soll).Length)
        verfahren.grundstellung()
    return weit


oben_trifft, auf_achse = neben_mit_g54(R_STANGE), neben_mit_g54(0.0)
print(
    ascii(
        f"G54 oben auf dem Mantel: {oben_trifft:.6f} mm, Gegenprobe auf der Achse {auf_achse:.3f}"
    )
)
pruefe(len(saetze_prog) >= 5 and oben_trifft < 1e-6, f"Mantel oben: {oben_trifft:.4f} mm")
pruefe(abs(auf_achse - R_STANGE) < 1e-6, f"Gegenprobe G54 auf der Achse: {auf_achse:.4f} mm")
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


pruefe(pp.vierte_achse(info), f"Maschineninfo ohne 4. Achse: {info.rundachsen}")
for kennung, muster in (
    ("siemens", r"\bA1=(?:AC[PN]\()?(-?\d+\.\d+)"),
    ("heidenhain", r"\bA([+-]\d+\.\d+)"),
    ("linuxcnc", r"\bA(-?\d+\.\d+)"),
):
    programm = pp.programm(pp.abschnitte(job), pp.steuerung(kennung), info, "Rohr")
    # Im Kopf: wo G54 liegt – Z 0 oben auf dem Mantel, mit dem Ø.
    pruefe(
        any(re.search(r"Z 0 oben auf dem Mantel, (Ø|D) 60\b", z) for z in programm.zeilen[:30]),
        f"{kennung}: Kopf ohne Z 0 oben auf dem Mantel",
    )
    werte = [float(w) for z in programm.zeilen for w in re.findall(muster, z.split(";")[0])]
    gleich = [x for x in werte if wie_die_bahn(x)]
    print(
        ascii(f"{kennung}: {len(werte)} A-Wörter, {len(gleich)} wie die Bahn, {programm.hinweise}")
    )
    pruefe(not programm.hinweise, f"{kennung}: {programm.hinweise}")
    pruefe(len(werte) >= len(set(in_der_bahn)) // 2, f"{kennung}: nur {len(werte)} A-Wörter")
    pruefe(len(gleich) >= len(werte) - 2, f"{kennung}: A nicht wie die Bahn ({werte[:5]})")

# Z im Programm: vom Mantel oben – die Z-Wörter der LinuxCNC-Zeilen mit A sind die der Bahn − 30.
# Gegenprobe: dasselbe Programm für eine Maschine ohne 4. Achse (3-Achs-Fräse, keine Maschine)
# zählt Z weiter von der Achse, Zeile für Zeile wie bis 0.385.
mit_vierter = pp.programm(pp.abschnitte(job), pp.steuerung("linuxcnc"), info, "Rohr").zeilen
ohne_vierte = pp.programm(
    pp.abschnitte(job), pp.steuerung("linuxcnc"), pp.Maschineninfo(), "Rohr"
).zeilen
z_mit = [float(w) for z in mit_vierter for w in re.findall(r"\bZ(-?\d+\.\d+)", z.split("(")[0])]
z_ohne = [float(w) for z in ohne_vierte for w in re.findall(r"\bZ(-?\d+\.\d+)", z.split("(")[0])]
im_job = {round(float(b.Parameters["Z"]), 3) for b in befehle if "Z" in b.Parameters}
pruefe(
    z_ohne and all(round(z, 3) in im_job for z in z_ohne),
    f"ohne 4. Achse: Z nicht wie die Bahn ({z_ohne[:5]})",
)
pruefe(not any("Mantel" in z for z in ohne_vierte), "ohne 4. Achse: Mantel im Kopf")
verschoben = [z for z in z_mit if round(z + R_STANGE, 3) in im_job]
print(
    ascii(
        f"Z vom Mantel: {len(verschoben)} von {len(z_mit)} Z-Wörtern, ohne 4. Achse {len(z_ohne)}"
    )
)
# Der Wechselpunkt (Z oben, in MKS) zählt nicht vom Nullpunkt – jedes andere Z ist die Bahn − 30.
pruefe(len(verschoben) >= len(z_mit) - 3, f"Z nicht vom Mantel: {z_mit[:6]}")

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


def hinein(zeilen, start, dz=0.0):
    """Fährt der erste Eilgang nach dem Wechsel (Z oben, X/Y wie `start`) in ein Spannmittel?
    Die Sätze nach „M6“/„TOOL CALL“ bis zum ersten mit Z: ändert sich Z, fährt die Spindel an der
    X/Y-Stelle dieses Satzes hinunter (ohne X/Y im Satz: an der alten). Gibt den Namen oder "".
    `dz`: so weit über dem Nullpunkt des Jobs liegt Z 0 des Programms (an der 4. Achse: der
    Mantel oben)."""
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
            z = float(worte["Z"]) + dz
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
        getroffen = hinein(zeilen, start, R_STANGE)
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
null_text = eb.nullpunkt_text(job, sprache.tr, info)
print(ascii(f"Nullpunkt: {null_text}"))
raus = laenge - vr.SPANNLAENGE
pruefe(
    f"{eb._zahl(vr.REITSTOCK_ZAPFEN)} " in null_text and f"{eb._zahl(raus)} " in null_text,
    f"Nullpunkt ohne Zapfen {vr.REITSTOCK_ZAPFEN} oder Ausspannlänge {raus}: {null_text}",
)
pruefe(f"Z 0 oben auf dem Mantel, Ø {eb._zahl(60.0)} mm" in null_text, f"Mantel: {null_text}")
# Ohne Maschine mit 4. Achse (keine Maschine am Job): wie bisher auf der Achse.
achse_text = eb.nullpunkt_text(job, sprache.tr, pp.Maschineninfo())
pruefe("Mantel" not in achse_text and "auf der Achse" in achse_text, f"ohne: {achse_text}")
sprache.setze_sprache("en")
englisch = eb.nullpunkt_text(job, sprache.tr, info)
sprache.setze_sprache("de")
pruefe("Z 0 on top of the bar" in englisch, f"englisch: {englisch}")
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
kollision = kb.kollision_parallel(fahrt, job, nullpunkt, bib)
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
# B-038 (Zweifler 2026-11-14): Vorn kann die Bahn mit Reitstock nicht ausfahren (die Pinole), sie
# taucht hinten neben der Schulter ein – bis 0.379 im Eilgang 0,37 mm neben der Wand, „Auf der
# Maschine prüfen“ meldete es. Geprüft, mit und ohne Reitstock (T1 Ø 16 mit Halter ER32/SK40):
# jeder Eilgang mindestens den Sicherheitsabstand vom Fertigteil (der Fräser als Zylinder, je
# Satz), die Kollision ohne Befund, der Rest wie ohne Reitstock.
# Nacharbeit (Zweifler 2026-11-14): dasselbe neben stehendem ROHTEIL – die Fläche hinten vor dem
# Futter mit einer Lücke von 30 mm (die letzten mm erreicht der Fräser nicht, dort steht die Stange
# bis r 25; die Helix begann 0,12 mm daneben, der Eilgang fuhr bis 9 mm unter ihre Oberkante) und
# eine Welle Ø 40 in der Stange Ø 50 (neben der Fläche steht das Rohteil über dem Teil: 0,145 mm).
# Je Bahn wird der Weg JEDES Eilgangs (nicht nur sein Ende) gegen das Material gemessen, das dann
# steht: das Material selbst abgefahren (restmaterial.Stange), vor jedem Eilgang der Fräser um den
# Sicherheitsabstand größer, die Spitze um ihn tiefer – nimmt er etwas weg, fehlt der Abstand.


def flach_oben(welle_r, x0, x1, z):
    welle = Part.makeCylinder(welle_r, 100.0, V(), V(1, 0, 0))
    return welle.cut(Part.makeBox(x1 - x0, 80, 40, V(x0, -40, z))).removeSplitter()


bahnen = []  # (Bahn, netz, laengs, radial, werte) – je planen() der Prüffälle
_planen_echt = vp.planen


def _planen_gemerkt(netz, laengs, radial, werte, *args, **kw):
    bahn = _planen_echt(netz, laengs, radial, werte, *args, **kw)
    bahnen.append((bahn, netz, laengs, radial, werte))
    return bahn


def eilgang_eindringen(bahn, netz, laengs, radial, w, spiel=0.05):
    """(mm, Punkt): wie weit der um den Sicherheitsabstand größere Fräser auf dem Weg eines
    Eilgangs höchstens ins Material oder ins Teil eindränge – 0: überall Abstand."""
    s = float(w.sicherheit) - spiel
    gross = w.form.mit_aufmass(s)
    a_vorn = float(w.a_stange_vorne)
    anzahl = max(2, int(math.ceil((a_vorn - min(float(w.a_futter), a_vorn - 1.0)) / rm.SCHRITT_A)))
    material = rm.Stange(float(w.stange_radius), a_vorn - anzahl * rm.SCHRITT_A, a_vorn)
    teil = rm.Stange(float(w.stange_radius) + 80.0, material.a[0], a_vorn + 60.0)
    teil.r = rm.teilradien(netz, laengs, radial, teil).astype(float)

    def eindringen(stange, von, nach):
        vorher = stange.r.copy()
        v, n = np.array(von, dtype=float), np.array(nach, dtype=float)
        v[1] -= s
        n[1] -= s
        stange.fahre_stuecke(v[None, :], n[None, :], gross)
        weg = vorher - stange.r
        stange.r = vorher
        weg = weg[np.isfinite(weg)]
        return float(weg.max()) if weg.size else 0.0

    schlimmst, vorschub = (0.0, None), []
    pk = bahn.punkte
    for k in range(1, len(pk)):
        p0, p1 = pk[k - 1], pk[k]
        von, nach = (p0.a, p0.r, p0.phi, p0.q), (p1.a, p1.r, p1.phi, p1.q)
        if not p1.eilgang:
            vorschub.append((von, nach))
            continue
        if vorschub:
            material.fahre_stuecke(
                np.array([x[0] for x in vorschub]), np.array([x[1] for x in vorschub]), w.form
            )
            vorschub = []
        quer = math.hypot(p1.a - p0.a, p1.q - p0.q) + abs(p1.phi - p0.phi)
        if quer > 1e-6 or p1.r < p0.r - 1e-9:  # senkrecht hinauf ist frei
            tief = max(eindringen(material, von, nach), eindringen(teil, von, nach))
            if tief > schlimmst[0]:
                schlimmst = (tief, k)
        material.fahre_stuecke(np.array([von]), np.array([nach]), w.form)
    return schlimmst


eben = flach_oben(25.0, 60, 100, 10)
t1.durchmesser, t1.schneidenlaenge = 16.0, 30.0
FAELLE = (
    # Name, Teil, Stange, Lücke hinten vor dem Futter
    ("vorn offen", eben, 50.0, 0.0),
    ("hinten mit Lücke", flach_oben(25.0, 0, 40, 10), 50.0, 30.0),
    ("Welle Ø 40 in Ø 50", flach_oben(20.0, 30, 70, 10), 50.0, 0.0),
)
vp.planen = _planen_gemerkt
reste = {}
for name, teilform, durchmesser, luecke in FAELLE:
    for mit in (True, False):
        doc = FreeCAD.newDocument(f"Flaeche{len(reste)}")
        mit_flaeche = doc.addObject("Part::Feature", "Teil")
        mit_flaeche.Shape = teilform
        doc.recompute()
        stirn = next(
            f
            for f in teilform.Faces
            if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
        )
        lage = vr.berechne(teilform, stirn, achse, durchmesser=durchmesser)
        stange = vr.Stange(durchmesser, reitstock=mit, frei_hinten=luecke)
        job = vr.richte_ein(doc, mit_flaeche, lage, stange, achse)
        tc = job.Tools.Group[0]
        tc.Tool.Diameter, tc.ToolNumber, tc.HorizFeed, tc.SpindleSpeed = 16, 1, "800 mm/min", 4000
        modell = vr.modell(job).Shape
        flaeche = next(
            f"Face{i + 1}"
            for i, f in enumerate(modell.Faces)
            if vr.ist_eben(f) and abs(f.normalAt(0, 0).z - 1.0) < 1e-6 and f.BoundBox.ZMax < 11
        )
        bahnen.clear()
        plan = vplan.lege_an(
            job, tc, achse, 4.0, 8.0, aufmass=0.0, flaechen=[flaeche], halter=hl.seitlich(halter)
        )
        doc.recompute()
        sicherheit = float(plan.Sicherheitsabstand)
        stand, auf_der_flaeche = {"X": 0.0, "Y": 0.0, "Z": 0.0, "A": 0.0}, []
        naechster = (math.inf, None)
        for i, b in enumerate(plan.Path.Commands):
            stand.update({x: float(w) for x, w in b.Parameters.items() if x in "XYZA"})
            if b.Name == "G1" and stand["Z"] < 11.0:
                auf_der_flaeche.append(stand["X"])
            if b.Name == "G0":
                dreh = FreeCAD.Rotation(V(achse.laengs), -achse.drehsinn * stand["A"])
                spitze = dreh.multVec(V(stand["X"], stand["Y"], stand["Z"]))
                fraeser = Part.makeCylinder(8.0, 60.0, spitze, dreh.multVec(V(0, 0, 1)))
                naechster = min(naechster, (fraeser.distToShape(modell)[0], i))
        tief = max(
            (eilgang_eindringen(*eintrag) for eintrag in bahnen),
            key=lambda t: t[0],
            default=(0.0, None),
        )
        print(
            ascii(
                f"Plan {name}, Reitstock {mit}: G1 auf der Fläche bis X "
                f"{max(auf_der_flaeche, default=None)}; nächster Eilgang {naechster[0]:.3f} mm "
                f"vom Teil (Satz {naechster[1]}); Eilgang ins Material/Teil {tief[0]:.3f} mm "
                f"(Punkt {tief[1]}, {len(bahnen)} Bahnen)"
            )
        )
        pruefe(bahnen, f"{name}, Reitstock {mit}: planen() nicht gerufen")
        if name == "vorn offen":
            pruefe(
                auf_der_flaeche and max(auf_der_flaeche) >= 0.0,
                f"Reitstock {mit}: Fläche bis X {max(auf_der_flaeche, default=None)}",
            )
        pruefe(
            naechster[0] >= sicherheit - 0.05,
            f"{name}, Reitstock {mit}: Eilgang {naechster[0]:.3f} mm am Teil (Satz {naechster[1]})",
        )
        pruefe(
            tief[0] <= 0.05,
            f"{name}, Reitstock {mit}: Eilgang {tief[0]:.3f} mm zu nah am Material "
            f"(Punkt {tief[1]})",
        )
        rs.anstellen(asm, ma, job)
        p = rw.Pruefung(asm, ma)
        nullpunkt = rw.nullpunkt(job, p)
        fahrt = ab.abfahrt(p, job, nullpunkt, bib)
        texte = [b.text() for b in kb.kollision_parallel(fahrt, job, nullpunkt, bib).befunde]
        abtrag = rm.fuer(fahrt, job, fahrt.am_werkstueck())
        abtrag.bis_station(len(fahrt.stationen) - 1)
        reste[name, mit] = abtrag.vergleich()
        print(
            ascii(
                f"  Kollision {texte[:3]}; Rest {reste[name, mit].kleinster:.3f} … "
                f"{reste[name, mit].groesster:.3f} mm"
            )
        )
        pruefe(not texte, f"Plan {name}, Reitstock {mit}: {texte[:3]}")
        pruefe(
            reste[name, mit].kleinster > -rm.BLAU_AB,
            f"{name}: ins Teil {reste[name, mit].kleinster:.3f} mm",
        )
        FreeCAD.closeDocument(doc.Name)
    pruefe(
        abs(reste[name, True].groesster - reste[name, False].groesster) < 0.05,
        f"{name}: Rest mit Reitstock bis {reste[name, True].groesster:.3f}, ohne "
        f"{reste[name, False].groesster:.3f}",
    )
vp.planen = _planen_echt
FreeCAD.closeDocument(asm.Document.Name)

# --- Die allgemeine Prüfung der Eilgänge (B-038, vierachs_bahn.eilgaenge_sichern) ----------
# Vor a 10 steht etwas bis 20 hoch: Ein Eilgang darf dort nur bis 22 hinab. Senkrecht bis 12: im
# Eilgang bis 22, der Rest im Eintauchvorschub; quer in der Höhe 12 hinüber: erst hinauf auf 22,
# dann hinüber, hinab im Vorschub. Ein Eilgang im ausgelassenen Bereich (Bohren in Hüben) bleibt.


def tiefst_wand(a, q, phi):
    return np.where(np.asarray(a, dtype=float) < 10.0, 22.0, -math.inf)


P = vb.Punkt
roh = [
    P(True, 20.0, 30.0, 0.0),
    P(True, 5.0, 30.0, 0.0),
    P(True, 5.0, 12.0, 0.0),  # senkrecht hinab, zu tief
    P(False, 5.0, 10.0, 0.0, True),
    P(True, 5.0, 30.0, 0.0),  # hinauf: frei
    P(True, 20.0, 30.0, 0.0),
    P(True, 20.0, 12.0, 0.0),  # hinab im Freien: bleibt
    P(True, 5.0, 12.0, 0.0),  # quer an die Wand, zu tief
    P(False, 5.0, 10.0, 0.0, True),
    P(True, 5.0, 30.0, 0.0),
    P(True, 5.0, 12.0, 0.0),  # ausgelassen
]
gesichert, anzahl = vb.eilgaenge_sichern(roh, tiefst_wand, [(10, 11)])
soll = [
    P(True, 20.0, 30.0, 0.0),
    P(True, 5.0, 30.0, 0.0),
    P(True, 5.0, 22.0, 0.0),
    P(False, 5.0, 12.0, 0.0, True),
    P(False, 5.0, 10.0, 0.0, True),
    P(True, 5.0, 30.0, 0.0),
    P(True, 20.0, 30.0, 0.0),
    P(True, 20.0, 12.0, 0.0),
    P(True, 20.0, 22.0, 0.0),
    P(True, 5.0, 22.0, 0.0),
    P(False, 5.0, 12.0, 0.0, True),
    P(False, 5.0, 10.0, 0.0, True),
    P(True, 5.0, 30.0, 0.0),
    P(True, 5.0, 12.0, 0.0),
]
pruefe(
    anzahl == 2 and gesichert == soll,
    f"Eilgänge gesichert ({anzahl}): {[(p.eilgang, p.a, p.r) for p in gesichert]}",
)
nichts, null = vb.eilgaenge_sichern(roh[:2], tiefst_wand)
pruefe(null == 0 and nichts == roh[:2], "Eilgang in der Höhe 30 geändert")

# --- Das Material über der Fläche für die Eilgänge (B-038 Nacharbeit, vierachs_planbahn._Stand) ---
# Stange Ø 50, Stirn bei a 0, Schaftfräser Ø 16, Sicherheitsabstand 2. Drei Zeilen (q −8, 0, 8)
# von a −10 bis −50 auf 15 gefräst: Darüber darf der Eilgang bis 15 + Sicherheit; die Stange vor
# dem Ende der Zeilen (ab a −2) steht noch bis 25 – an a −11 ist sie 1 + 8 mm weg, der Eilgang
# bleibt um √(1,99² − 1²) über ihr (das Raster bis 0,15 mm mehr, zur sicheren Seite: Eine Zelle,
# die der Fräser nur zum Teil geräumt hat, steht ganz); an a −13 sieht er sie nicht mehr. Vor der
# Stange (a ≥ R + s) steht nichts, auf einem anderen Winkel gilt das Raster nicht.
from camaddon import fraeserform as ff  # noqa: E402

w_stand = vp.Planwerte(
    form=ff.scheibe(8.0), stange_radius=25.0, zustellung=4.0, zeilenabstand=8.0, aufmass=0.0,
    a_stange_vorne=0.0, a_futter=-80.0, sicherheit=2.0,
)  # fmt: skip
ebene_0 = vp.Ebene("Face1", 0.0, 10.0, -20.0, 0.0, -20.0, 20.0)
st = vp._Stand(w_stand, ebene_0, -60.0, -40.0, 40.0)
s_e = 2.0 - vb.EILGANG_SPIEL
vorher = float(st.tiefst([-30.0], [0.0], [0.0])[0])
pruefe(abs(vorher - (25.0 + s_e)) < 0.02, f"Stand: über der Stange {vorher:.3f}")
pruefe(
    st.tiefst([10.0], [0.0], [0.0])[0] == -math.inf
    and st.tiefst([-30.0], [0.0], [90.0])[0] == -math.inf,
    "Stand: vor der Stange oder auf einem anderen Winkel steht etwas",
)
for q_z in (-8.0, 0.0, 8.0):
    st.abtragen(
        [P(True, -10.0, 30.0, 0.0, q=q_z), P(False, -10.0, 15.0, 0.0, True, q_z),
         P(False, -50.0, 15.0, 0.0, q=q_z)],
        1,
    )  # fmt: skip
werte_st = [float(x) for x in st.tiefst([-30.0, -13.0, -11.0], [0.0, 0.0, 0.0], [0.0] * 3)]
soll_st = [15.0 + s_e, 15.0 + s_e, 25.0 + math.sqrt(s_e**2 - 1.0)]
pruefe(
    all(y - 0.01 <= x <= y + 0.15 for x, y in zip(werte_st, soll_st, strict=True)),
    f"Stand nach den Zeilen: {werte_st}, soll {soll_st}",
)
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
