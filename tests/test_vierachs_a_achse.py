# Prüft 4 Achsen um eine Rundachse quer zu Z (B-037): die Beispiel-5-Achs Tisch/Tisch mit A in
# Grundstellung – kinematisch eine 4. Achse längs X mit dem Werkzeug von oben. Welle Ø 40 × 30 in
# der Stange Ø 50 längs X, „Rundum schruppen“ mit T1 Ø 12 (ER32, HSK-A63).
#
# Bis 0.375.0 lag die Stange in „Auf der Maschine prüfen“ mit der Unterseite auf dem Rundtisch
# (der Nullpunkt wie bei einem Quader), 80 − 25 mm unter A: Die Prüfung drehte sie um A auf einem
# Kreis um die falsche Achse und meldete „Schneide ins fertige Teil“, wo der Rest „nirgends ins
# Teil“ sagte. Hier mit einer eigenen Rechnung festgehalten: die Maschine (verfahren) auf die
# Achswerte eines Satzes gestellt – die Linearachsen wie ohne TCPM mit A auf 0 –, die Spitze am Teil
# gemessen und mit der Bahn verglichen; dazu das Programm (Siemens): A nach DIN umgedreht, wie die
# Prüfung die Steuerung zählt; die Kollision findet nichts.
import os
import sys
import time

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import abfahren as ab
from camaddon import beispielmaschine as bm
from camaddon import halter as hl
from camaddon import kollision as kb
from camaddon import maschine as m
from camaddon import postprozessor as pp
from camaddon import programm_rechnen as pr
from camaddon import reichweite as rw
from camaddon import sprache
from camaddon import verfahren as vf
from camaddon import vierachs_achsen as va
from camaddon import vierachs_operation as vo
from camaddon import vierachs_rohteil as vr
from camaddon import werkzeuge as wz
from camaddon.kette import LINEAR

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")

asm, ma = bm.fuenfachs_tisch_tisch()
achse = next(a for a in va.von_maschine(asm, ma) if a.buchstabe == "A")
pruefe(achse.laengs == V(1, 0, 0) and va.radial(achse) == V(0, 0, 1), f"A: {achse}")

doc = FreeCAD.newDocument("WelleA")
welle = doc.addObject("Part::Feature", "Welle")
welle.Shape = Part.makeCylinder(20, 30, V(), V(1, 0, 0))
doc.recompute()
stirn = next(
    f
    for f in welle.Shape.Faces
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
)
lage = vr.berechne(welle.Shape, stirn, achse, durchmesser=50)
job = vr.richte_ein(doc, welle, lage, vr.Stange(50.0, frei_hinten=40.0), achse)
tc = job.Tools.Group[0]
tc.Tool.Diameter = 12
tc.ToolNumber = 1
tc.HorizFeed = "1500 mm/min"
bib = wz.Bibliothek()
halter = bib.neuer_halter("er32", None, "HSK-A63")
t1 = bib.neues_werkzeug()
t1.nummer, t1.durchmesser, t1.laenge_spindelnase, t1.halter = 1, 12.0, 125.0, halter.kennung
t1.schneidenlaenge = 25.0
op = vo.lege_an(job, tc, achse, 5.0, 12.0, 0.3, halter=hl.seitlich(halter))
doc.recompute()
befehle = list(op.Path.Commands)
pruefe(sum(1 for b in befehle if "A" in b.Parameters) > 5, "Rundum schruppen ohne A")

# --- Der Nullpunkt: ohne Maschine wie bisher, mit ihr auf A ------------------------------------
p = rw.Pruefung(asm, ma)
ohne = rw.vorschlag_nullpunkt(job)
pruefe(abs(ohne.z - 25.0) < 1e-9, f"ohne Maschine: die Stange auf dem Tisch, Z {ohne.z}")
nullpunkt = rw.nullpunkt(job, p)
pruefe((rw.nullpunkt(job, p) - rw.vorschlag_nullpunkt(job, p)).Length < 1e-12, "nullpunkt()")
aufnahme_ws = p.werkstueckaufnahme
a1 = next(a for a in p.kette.achsen if p.programmbuchstabe(a) == "A")
richtung, ursprung = p.verfahren.achslage(a1)
null_asm = p._lage(aufnahme_ws).multiply(FreeCAD.Placement(nullpunkt, FreeCAD.Rotation())).Base
neben = (null_asm - ursprung) - richtung * (null_asm - ursprung).dot(richtung)
pruefe(neben.Length < 1e-6, f"Der Nullpunkt liegt {neben.Length:.3f} mm neben A")
print(ascii(f"Nullpunkt ohne Maschine {tuple(ohne)}, mit {tuple(nullpunkt)}"))
# „Programm schreiben“ prüft die Reichweite mit demselben Nullpunkt wie „Auf der Maschine prüfen“.
programm_maschine = pr.maschine_je_operation(job, asm.Document)(op)
pruefe(
    programm_maschine is not None and (programm_maschine.nullpunkt - nullpunkt).Length < 1e-9,
    f"Programm schreiben: Nullpunkt {getattr(programm_maschine, 'nullpunkt', None)}",
)

# --- Die Spitze, wenn die Maschine die Achswerte eines Satzes fährt (eigene Rechnung) ------------
aufnahme = p.werkzeugaufnahme(1)
eins = rw.einspannung(tc, bib)
verfahren = vf.Verfahren(asm)
linear = [a for a in verfahren.achsen if a.art == LINEAR]
a_eigene = next(a for a in verfahren.achsen if a.gelenk is a1.gelenk)


stand, saetze = {}, []
for b in befehle:
    stand.update({x: float(w) for x, w in b.Parameters.items() if x in "XYZA"})
    if b.Name == "G1" and abs(stand.get("A", 0.0)) > 5.0:
        saetze.append(dict(stand))
saetze = saetze[:: max(1, len(saetze) // 12)]


def neben_der_bahn(null):
    """(Sätze, höchstens so weit (mm) steht die Spitze am Teil neben der Bahn) mit dem Nullpunkt
    `null` – die Linearachsen wie ohne TCPM (A auf 0) aus je 1 mm Fahrt gelöst, dann A gefahren."""

    def spitze_im_job():
        welt = m.globale_platzierung(aufnahme.Lcs).multVec(eins.spitze())
        job_welt = m.globale_platzierung(aufnahme_ws.Lcs).multiply(
            FreeCAD.Placement(null, FreeCAD.Rotation())
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
    for stand in saetze:
        punkt = V(*(stand.get(x, 0.0) for x in "XYZ"))
        wege = np.linalg.lstsq(jacobi, np.array(tuple(punkt - s0)), rcond=None)[0]
        for a, w in zip(linear, wege, strict=True):
            verfahren.setze(a, start[a] + w, grenzen=False)
        verfahren.setze(a_eigene, stand["A"], grenzen=False)  # die Stellung zählt wie das Gelenk
        ist = spitze_im_job()
        soll = FreeCAD.Rotation(V(achse.laengs), -achse.drehsinn * stand["A"]).multVec(punkt)
        groesste = max(groesste, (ist - soll).Length)
        verfahren.grundstellung()
    return len(saetze), groesste


gemessen, groesste = neben_der_bahn(nullpunkt)
_n, vorher = neben_der_bahn(ohne)  # Gegenprobe: der Nullpunkt bis 0.375.0
print(ascii(f"Spitze am Teil an {gemessen} Sätzen: höchstens {groesste:.6f} mm neben der Bahn, "
            f"mit dem Nullpunkt bis 0.375.0 {vorher:.1f} mm"))  # fmt: skip
pruefe(gemessen >= 5 and groesste < 1e-6, f"Spitze {groesste:.3f} mm neben der Bahn")
pruefe(vorher > 10.0, f"Gegenprobe: mit der Stange auf dem Tisch nur {vorher:.3f} mm daneben")

# --- Das Programm: A nach DIN umgedreht – die Prüfung zählt die Steuerung genauso -------------
pruefe(a1 is not None and vf.programm_vorzeichen(a1, p.kette) == -1, "A zählt wie das Gelenk")
pruefe("A" in p.umgekehrt, f"Prüfung: umgekehrt {p.umgekehrt}")
info = pp.maschineninfo_dokument(asm.Document)
zeilen = pp.programm(pp.abschnitte(job), pp.steuerung("siemens"), info, "WelleA").zeilen
adresse = info.rundachsen.get("A", "A") + "="  # Siemens: „A1=90.000“
im_programm = [float(w[len(adresse) :]) for z in zeilen for w in z.split() if w.startswith(adresse)]
in_der_bahn = [float(b.Parameters["A"]) for b in befehle if "A" in b.Parameters]
pruefe(
    len(im_programm) == len(in_der_bahn)
    and all(abs(x + y) < 1e-3 for x, y in zip(im_programm, in_der_bahn, strict=True)),
    f"A im Programm {im_programm[:4]}, in der Bahn {in_der_bahn[:4]}",
)

# --- Kollision: nichts ins Teil, nichts berührt sich --------------------------------------------
# Bis A ±90°: hinein und eine Vierteldrehung. Weiter berühren sich Spindel und Rundtisch – das ist
# echt (B-037 (2)): Liegt das Rohr auf dem Tisch, steht seine Achse nur 80 mm über ihm, der
# Rundtisch hat 140 mm Radius; so spannt man nicht (Manuel, 2026-11-15) – dafür „C, A auf 90°“
# (test_vierachs_geschwenkt).
beginn = time.time()
fahrt = ab.abfahrt(p, job, nullpunkt, bib)
bis = next(
    (i for i, s in enumerate(fahrt.stationen) if abs(s.rund.get("A", 0.0)) > 90.0),
    len(fahrt.stationen),
)
anfang = ab.Abfahrt(p, fahrt.achsen, fahrt.stationen[:bis], fahrt.operationen)
anfang._fertig()
gedreht = max(abs(s.rund.get("A", 0.0)) for s in anfang.stationen)
pruefe(gedreht > 60.0, f"bis Station {bis} dreht A nur {gedreht:.0f}°")
kollision = kb.kollision(anfang, job, nullpunkt, bib)
texte = [b.text() for b in kollision.befunde]
dauer = time.time() - beginn
print(ascii(f"Kollision: {bis} Stationen bis A {gedreht:.0f} in {dauer:.1f} s, {texte[:3]}"))
pruefe(not kollision.befunde, f"Befunde: {texte[:3]}")

FreeCAD.closeDocument(doc.Name)
FreeCAD.closeDocument(asm.Document.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
