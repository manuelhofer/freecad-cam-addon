# Prüft „Kontur“ (W-006 S3e): Block 100 × 60 × 20 mit einer Tasche 40 × 30 (Ecken R 6), 15 tief,
# bei (30, 15); Rohteil 1 mm rundum (Oberkante 21), Manuels Standardfräser Ø 12
# (werkzeuge.standardwerkzeug: ae 1,5, ap 25, Schneidenlänge 26, Rampe 3°), Aufmaß 0,3,
# Schlichten in einem Zug. Wände und Konturen (außen rundum, die Tasche innen), der Versatz
# mit Bögen, Gleichlauf (M3: außen im Uhrzeigersinn, in der Tasche gegen ihn), tangentiales
# Ein- und Ausfahren – das in der Tasche nicht näher an die gegenüberliegende Wand kommt als
# der Radius (mit Ø 12 gefunden, P-2026-10-01-23) –, Rampe im Material, Lagen und Bahnen,
# eine Wand allein (offen) und eine Taschenwand allein (die Nachbarn halten die Bahn an),
# Fehler mit einem Satz; dann die CAM-Operation im Job: angelegt (Tiefen und Höhen wie
# FreeCAD), gerechnet, geändert, gespeichert und geladen.
import math
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import bahn as bn
from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import job_schnittwerte as js
from camaddon import kontur as ko
from camaddon import kontur_bahn as kb
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")


def rund_rechteck(x0, y0, x1, y1, r, z):
    """Ein Rechteck mit runden Ecken als Draht."""
    kanten = [
        Part.makeLine(V(x0 + r, y0, z), V(x1 - r, y0, z)),
        Part.makeCircle(r, V(x1 - r, y0 + r, z), V(0, 0, 1), -90, 0),
        Part.makeLine(V(x1, y0 + r, z), V(x1, y1 - r, z)),
        Part.makeCircle(r, V(x1 - r, y1 - r, z), V(0, 0, 1), 0, 90),
        Part.makeLine(V(x1 - r, y1, z), V(x0 + r, y1, z)),
        Part.makeCircle(r, V(x0 + r, y1 - r, z), V(0, 0, 1), 90, 180),
        Part.makeLine(V(x0, y1 - r, z), V(x0, y0 + r, z)),
        Part.makeCircle(r, V(x0 + r, y0 + r, z), V(0, 0, 1), 180, 270),
    ]
    return Part.Wire(kanten)


def flaeche_umlauf(punkte):
    """Die Fläche des Umlaufs (Schnürsenkel): > 0 gegen den Uhrzeigersinn."""
    summe = 0.0
    for (x0, y0), (x1, y1) in zip(punkte, punkte[1:] + punkte[:1], strict=False):
        summe += x0 * y1 - x1 * y0
    return summe / 2


# --- Das Teil: Block mit runder Tasche; Wände und Konturen -----------------------------------
tasche = Part.Face(rund_rechteck(30, 15, 70, 45, 6, 5)).extrude(V(0, 0, 20))
teil = Part.makeBox(100, 60, 20).cut(tasche).removeSplitter()
namen = [f"Face{i + 1}" for i in range(len(teil.Faces))]
waende = kb.waende(teil, namen)
pruefe(len(waende) == 12, f"Wände: {[w.name for w in waende]}")
pruefe(all(len(w.kanten) == 1 for w in waende), "jede Wand eine Unterkante")
aussen_waende = [w for w in waende if abs(w.z_unten) < 1e-6]
taschen_waende = [w for w in waende if abs(w.z_unten - 5.0) < 1e-6]
pruefe(len(aussen_waende) == 4 and len(taschen_waende) == 8, "4 außen, 8 in der Tasche")
oben = next(e.name for e in hf.ebenen_oben(teil) if abs(e.z - 20.0) < 1e-6)
boden = next(e.name for e in hf.ebenen_oben(teil) if abs(e.z - 5.0) < 1e-6)
pruefe(not kb.waende(teil, [oben, boden]), "Oberseite und Boden sind keine Wände")
konturen = kb.konturen(teil, namen)
pruefe(len(konturen) == 2, f"Konturen: {len(konturen)}")
tasche_k, aussen_k = konturen[0], konturen[1]  # die tiefste zuletzt
pruefe(
    abs(tasche_k.z_unten - 5.0) < 1e-6 and tasche_k.geschlossen and len(tasche_k.waende) == 8,
    f"Tasche: {tasche_k.z_unten}, {tasche_k.geschlossen}, {tasche_k.waende}",
)
pruefe(
    abs(aussen_k.z_unten) < 1e-6 and aussen_k.geschlossen and len(aussen_k.waende) == 4,
    f"außen: {aussen_k.z_unten}, {aussen_k.geschlossen}, {aussen_k.waende}",
)
# Die freie Seite: in der Tasche nach innen (auf der langen Wand bei y = 45 nach −y), außen
# vom Teil weg.
pruefe(abs(tasche_k.normale[1] + 1.0) < 1e-6 or abs(tasche_k.normale[1] - 1.0) < 1e-6, "Tasche")
sx, sy = tasche_k.stelle
pruefe(
    (abs(sy - 45.0) < 1e-6 and tasche_k.normale[1] < 0)
    or (abs(sy - 15.0) < 1e-6 and tasche_k.normale[1] > 0),
    f"freie Seite der Tasche: {tasche_k.stelle} {tasche_k.normale}",
)
sx, sy = aussen_k.stelle
pruefe(
    (abs(sy - 60.0) < 1e-6 and aussen_k.normale[1] > 0)
    or (abs(sy) < 1e-6 and aussen_k.normale[1] < 0),
    f"freie Seite außen: {aussen_k.stelle} {aussen_k.normale}",
)
# Gegen die Hüllfläche rechnet das Teil ohne die Wände und ihre Nachbarn: hier alles.
pruefe(len(kb.ohne_flaechen(teil, waende)) == 15, f"ohne: {kb.ohne_flaechen(teil, waende)}")
nur_eine = kb.waende(teil, ["Face2"])
pruefe(
    set(kb.ohne_flaechen(teil, nur_eine)) == {"Face2", "Face3", "Face5"},
    f"ohne (eine Wand): {kb.ohne_flaechen(teil, nur_eine)}",
)
print("Waende ok")

# --- Die Bahn: zwei Konturen, Lagen, Bahnen, Richtung, Ein- und Ausfahren, Rampe -------------
netz, netz_fern = hf.netze_ohne(teil, [kb.ohne_flaechen(teil, waende), [w.name for w in waende]])
pruefe(len(netz.dreiecke) == 0 and len(netz.punkte) == 0, "ohne alles: leer, auch die Ecken")
pruefe(len(netz_fern.dreiecke) > 100, f"fern: {len(netz_fern.dreiecke)} Dreiecke")
werkzeug = wz.standardwerkzeug()
R = werkzeug.durchmesser / 2  # 6
schruppen = next(e for e in werkzeug.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
form = ff.scheibe(R)
werte = kb.Konturwerte(
    form=form,
    zustellung=schruppen.ap,
    zeilenabstand=schruppen.ae,
    aufmass=0.3,
    schlichten=True,
    oben=21.0,
    sicher=26.0,
    rohteil=(-1.0, 101.0, -1.0, 61.0),
    schneidenlaenge=werkzeug.schneidenlaenge,
    eintauchwinkel=werkzeug.eintauchwinkel,
)
bahn = kb.planen(netz, werte, konturen, netz_fern=netz_fern)
# Außen: eine Lage Schruppen (21 mm bei ap 25), Schlichten in einem Zug (die Schneide 26);
# Tasche: eine Lage (21 → 5), ein Zug. Außen je Lage eine Bahn (1 mm Rohteil), in der Tasche
# sechs nebeneinander (6,3 … 13,8 in Schritten von 1,5 – 15,3 passt nicht mehr hinein).
pruefe(bahn.konturen == 2, f"Konturen {bahn.konturen}")
pruefe(bahn.lagen == 1 + 1 + 1 + 1, f"Lagen {bahn.lagen}")
pruefe(bahn.bahnen == 1 + 1 + 6 + 1, f"Bahnen {bahn.bahnen}")
pruefe(abs(bahn.z_min) < 1e-9, f"z_min {bahn.z_min}")
vorschub = [p for p in bahn.punkte if not p.eilgang]
pruefe(sum(1 for p in vorschub if p.eintauchen) == bahn.bahnen, "je Bahn einmal hinab")
pruefe(sum(1 for p in vorschub if p.bogen is not None) > 20, "Bögen")
pruefe(not any(p.anteil < 1.0 for p in vorschub), "geschlossen: kein Austritt")
# Gleichlauf (Spindel rechtsdrehend, M3 – wie G41): das Schlichten in der Tasche (z = 5) läuft
# gegen den Uhrzeigersinn, außen (z = 0) mit ihm – das Material liegt rechts.
innen = [
    (p.x, p.y)
    for p in vorschub
    if abs(p.z - 5.0) < 1e-9 and 24 < p.x < 76 and 9 < p.y < 51 and p.bogen is None
]
pruefe(
    len(innen) > 4 and flaeche_umlauf(innen) > 0, f"Tasche gegen den Uhrzeigersinn: {len(innen)}"
)
aussen = [(p.x, p.y) for p in vorschub if abs(p.z) < 1e-9 and p.bogen is None]
pruefe(len(aussen) > 4 and flaeche_umlauf(aussen) < 0, "außen im Uhrzeigersinn")
# Der Versatz: Schlichten bei 6 (x = −6 … 106), Schruppen bei 6,3 (die Ecken als Bögen R 6,3).
schlicht_aussen = [p for p in vorschub if abs(p.z) < 1e-9]  # Schrupplage und Schlichten
x_unten = {round(p.x, 3) for p in schlicht_aussen}
pruefe(
    {-6.3, -6.0, 106.0, 106.3} <= x_unten and min(x_unten) >= -6.3 - 1e-6,
    f"Versatz außen bei z = 0: {sorted(x_unten)[:3]} … {sorted(x_unten)[-3:]}",
)
ecken = [
    p
    for p in schlicht_aussen
    if p.bogen is not None and abs(math.hypot(p.x - p.bogen[0], p.y - p.bogen[1]) - R) < 1e-6
]
pruefe(len(ecken) >= 4, f"Ecken als Bögen: {len(ecken)}")
# Die Geraden längs der langen Seiten (ohne das Ein- und Ausfahren quer zur Wand).
schrupp_aussen = [
    b.y
    for a, b in zip(vorschub, vorschub[1:], strict=False)
    if abs(a.z) < 1e-9
    and abs(b.z) < 1e-9
    and b.bogen is None
    and abs(a.y - b.y) < 1e-9
    and abs(a.x - b.x) > 1.0
    and abs(b.y) > 60
]
pruefe(
    schrupp_aussen and abs(max(schrupp_aussen) - 66.3) < 1e-6,
    f"Schruppen bei R + Aufmaß: y bis {max(schrupp_aussen, default=None)}",
)
# Ein- und Ausfahren: der Viertelkreis R 6 (G3, gegen den Uhrzeigersinn) an der Anfangsstelle, davor
# die Gerade 6 lang quer von der Wand weg – außen in der Luft: senkrecht hinab.
start = next(i for i, p in enumerate(bahn.punkte) if not p.eilgang and abs(p.z) < 1e-9)
hinein = bahn.punkte[start : start + 3]
pruefe(hinein[0].eintauchen and hinein[2].bogen is not None and not hinein[2].bogen[2], "Einfahrt")
pruefe(
    abs(bn.weg(hinein[0], hinein[1]) - R) < 1e-6
    and abs(math.hypot(hinein[2].x - hinein[2].bogen[0], hinein[2].y - hinein[2].bogen[1]) - R)
    < 1e-6,
    "Einfahrt: Gerade 6, Bogen R 6",
)
# In der Tasche beginnt das Schruppen im Material: über die Rampe – Punkte zwischen den Lagen.
lagen_z = {21.0, 5.0, 0.0}
zwischen = [
    p
    for p in vorschub
    if 30 < p.x < 70 and 15 < p.y < 45 and min(abs(p.z - z) for z in lagen_z) > 1e-6
]
pruefe(len(zwischen) > 20, f"Rampe in der Tasche: {len(zwischen)} Punkte")
pruefe(
    not any(
        min(abs(p.z - z) for z in lagen_z) > 1e-6
        for p in vorschub
        if not (30 < p.x < 70 and 15 < p.y < 45)
    ),
    "außen in der Luft: keine Rampe",
)
# Alle Taschenpunkte bleiben in der Tasche – auch das Ein- und Ausfahren der innersten
# Schruppbahn, das zur Mitte schwenkt, kommt der Wand gegenüber nicht näher als R (mit Ø 12
# reichte es 1,8 mm hinein, bis die Hüllfläche die eigenen Wände mitzählte).
taschenpunkte = [p for p in vorschub if 15 < p.y < 45 and 5 <= p.z < 21 and 25 < p.x < 75]
pruefe(
    all(30 + R - 1e-6 <= p.x <= 70 - R + 1e-6 for p in taschenpunkte)
    and all(15 + R - 1e-6 <= p.y <= 45 - R + 1e-6 for p in taschenpunkte),
    f"Taschenpunkte: x {min(p.x for p in taschenpunkte)} … {max(p.x for p in taschenpunkte)}, "
    f"y {min(p.y for p in taschenpunkte)} … {max(p.y for p in taschenpunkte)}",
)
pruefe(bahn.punkte[0].eilgang and abs(bahn.punkte[0].z - 26.0) < 1e-9, "Start oben")
pruefe(bahn.punkte[-1].eilgang and abs(bahn.punkte[-1].z - 26.0) < 1e-9, "Ende oben")
pruefe(bahn.laenge > 3000.0, f"Länge {bahn.laenge}")
befehle = bn.befehle(bahn.punkte, 1000.0, 200.0)
pruefe({"G0", "G1", "G2", "G3"} <= {b.Name for b in befehle}, "Befehle G0 … G3")
print(ascii(f"Kontur: {len(bahn.punkte)} Punkte, {len(befehle)} Befehle"))

# --- Eine Wand allein: offen, vom Anfang bis zum Ende, die Nachbarn halten an ----------------
eine = kb.konturen(teil, ["Face2"])  # y = 0
pruefe(len(eine) == 1 and not eine[0].geschlossen, "eine Wand: offen")
netz_eine, fern_eine = hf.netze_ohne(teil, [kb.ohne_flaechen(teil, nur_eine), ["Face2"]])
bahn_eine = kb.planen(netz_eine, werte, eine, netz_fern=fern_eine)
pruefe(
    bahn_eine.lagen == 2 and bahn_eine.bahnen == 2,
    f"eine Wand: {bahn_eine.lagen}, {bahn_eine.bahnen}",
)
punkte_eine = [p for p in bahn_eine.punkte if not p.eilgang]
pruefe(
    all(p.y <= -R + 1e-6 for p in punkte_eine)
    and min(p.y for p in punkte_eine) >= -(R + 0.3 + 2 * R) - 1e-6,
    f"eine Wand: y {min(p.y for p in punkte_eine)} … {max(p.y for p in punkte_eine)}",
)
# Vor den Ecken halten die Nachbarwände (x = 0 und 100) die Bahn an – knapp davor, mit dem
# Raster 0,5 mm und der Stirn um die Toleranz größer –, der Fräser deckt die Wand trotzdem
# ganz; das Einfahren reicht darüber hinaus.
laengs = [p for p in punkte_eine if abs(p.y + R) < 1e-6 or abs(p.y + R + 0.3) < 1e-6]
pruefe(
    min(p.x for p in laengs) <= 2.5 and max(p.x for p in laengs) >= 97.5,
    f"eine Wand: längs x {min(p.x for p in laengs)} … {max(p.x for p in laengs)}",
)
pruefe(
    min(p.x for p in punkte_eine) <= -2.5 and max(p.x for p in punkte_eine) >= 102.5,
    f"eine Wand: x {min(p.x for p in punkte_eine)} … {max(p.x for p in punkte_eine)}",
)
# Eine Taschenwand allein (y = 45, Face10): die Bahn bleibt in der Tasche, vor den Bögen
# links und rechts hält die Hüllfläche sie an – und das Ausfahren bleibt frei.
wand10 = kb.waende(teil, ["Face10"])
pruefe(len(wand10) == 1 and abs(wand10[0].z_unten - 5.0) < 1e-6, "Face10 ist die Taschenwand")
netz10, fern10 = hf.netze_ohne(teil, [kb.ohne_flaechen(teil, wand10), ["Face10"]])
bahn10 = kb.planen(netz10, werte, kb.konturen(teil, ["Face10"]), netz_fern=fern10)
punkte10 = [p for p in bahn10.punkte if not p.eilgang]
pruefe(
    all(
        30.0 + R - 1e-6 <= p.x <= 70.0 - R + 1e-6 and 15.0 + R - 1e-6 <= p.y <= 45.0 - R + 1e-6
        for p in punkte10
    ),
    f"Taschenwand: x {min(p.x for p in punkte10)} … {max(p.x for p in punkte10)}, "
    f"y {min(p.y for p in punkte10)} … {max(p.y for p in punkte10)}",
)
pruefe(bahn10.bahnen >= 9, f"Taschenwand: {bahn10.bahnen} Bahnen")

# --- Fehler mit einem Satz: Kugel, Zeilenabstand (über Ø), keine Wand, nichts neben der Wand -
for werte_falsch, konturen_falsch, netz_falsch, text in (
    (
        kb.Konturwerte(ff.kugel(R), 25.0, 1.5, 0.3, True, 21.0, 26.0, werte.rohteil),
        konturen,
        netz,
        "Kugel",
    ),
    (
        kb.Konturwerte(form, 25.0, 13.0, 0.3, True, 21.0, 26.0, werte.rohteil),
        konturen,
        netz,
        "Abstand",
    ),
    (werte, [], netz, "keine Kontur"),
    (
        kb.Konturwerte(form, 25.0, 1.5, 0.3, True, 21.0, 26.0, (0.0, 100.0, 0.0, 60.0)),
        [aussen_k],
        netz,
        "nichts neben der Wand",
    ),
):
    try:
        kb.planen(netz_falsch, werte_falsch, konturen_falsch)
    except ValueError as grund:
        pruefe(len(str(grund)) > 10, f"{text}: kein Satz")
    else:
        pruefe(False, f"{text}: keine Fehlermeldung")
try:
    kb.konturen(teil, [oben])
except ValueError as grund:
    pruefe("Wand" in str(grund), f"keine Wand: {grund}")
else:
    pruefe(False, "keine Wand: keine Fehlermeldung")
print("Fehler ok")

# --- Die CAM-Operation im Job ---------------------------------------------------------------
import Path.Main.Job as PathJob

schaft = werkzeug  # T1, der Standardfräser mit dem Einsatz Schruppen
ue.uebergeben(wz.Bibliothek([schaft]))
ap, ae = schruppen.ap, schruppen.ae

doc = FreeCAD.newDocument("Kontur")
doc.UndoMode = 1
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
tc1 = js.controller_ohne_transaktion(doc, job, schaft, schruppen)
doc.recompute()
pruefe(
    abs(job.Stock.Shape.BoundBox.ZMax - 21.0) < 1e-6,
    f"Rohteil oben {job.Stock.Shape.BoundBox.ZMax}",
)
pruefe(abs(ko.schneidenlaenge(tc1) - 26.0) < 1e-6, f"Schneidenlänge {ko.schneidenlaenge(tc1)}")
klon = job.Model.Group[0]
waende_im_job = [w.name for w in kb.waende(klon.Shape, [f"Face{i + 1}" for i in range(15)])]
pruefe(len(waende_im_job) == 12, f"Wände im Job: {waende_im_job}")

op = ko.lege_an(job, tc1, zustellung=ap, zeilenabstand=ae, flaechen=waende_im_job)
doc.recompute()
pruefe(op.Label == "Kontur T1" and op in job.Operations.Group, f"{op.Label}")
pruefe(ko.ist_kontur(op), "Art")
pruefe(js.operationsart(op) == "kontur", f"Art: {js.operationsart(op)}")
pruefe(js.EINSATZ_NACH_OPERATION["kontur"][0] == wz.SCHRUPPEN, "Einsatz Schruppen")
pruefe(
    abs(float(op.StartDepth) - 21.0) < 1e-6 and abs(float(op.FinalDepth)) < 1e-6,
    f"Tiefen {float(op.StartDepth)} … {float(op.FinalDepth)}",
)
pruefe(float(op.SafeHeight) > 21.0, "Höhen")
pruefe(
    (op.Konturen, op.Lagen, op.Bahnen) == (2, 4, 9),
    f"Operation: {op.Konturen}, {op.Lagen}, {op.Bahnen}",
)
pruefe(op.Schlichten is True and abs(float(op.Aufmass) - 0.3) < 1e-9, "Vorgaben")
befehle = op.Path.Commands
namen_befehle = [b.Name for b in befehle]
pruefe(
    namen_befehle[1:3] == ["G0", "G0"] and namen_befehle[-1] == "G0",
    f"Befehle: {namen_befehle[:4]} … {namen_befehle[-1]}",
)
schnitte = [b for b in befehle if b.Name in ("G1", "G2", "G3")]
pruefe(any(b.Name == "G2" for b in schnitte) and any(b.Name == "G3" for b in schnitte), "Bögen")
z_werte = sorted({round(b.Parameters["Z"], 6) for b in schnitte if "Z" in b.Parameters})
pruefe(min(z_werte) >= -1e-6 and 0.0 in z_werte and 5.0 in z_werte, f"Z {z_werte[:6]}")
pruefe(op.getEditorMode("Bahnen") == ["ReadOnly"], "Bahnen änderbar")

# Ändern: Zustellung 12,5 – zwei Schrupplagen je Kontur; ohne Schlichten keine Schlichtbahn;
# nur die Taschenwände: eine Kontur, Endtiefe 5.
ko.aendere(op, tc1, 12.5, ae, 0.3, True)
doc.recompute()
pruefe(op.Lagen == 2 + 1 + 2 + 1, f"geändert: {op.Lagen} Lagen")
ko.aendere(op, tc1, 12.5, ae, 0.3, False)
doc.recompute()
pruefe(op.Lagen == 2 + 2 and op.Bahnen == 2 + 6 * 2, f"ohne Schlichten: {op.Lagen}, {op.Bahnen}")
taschen_im_job = [
    w for w in waende_im_job if abs(kb.waende(klon.Shape, [w])[0].z_unten - 5.0) < 1e-6
]
ko.aendere(op, tc1, ap, ae, 0.3, True, flaechen=taschen_im_job)
doc.recompute()
pruefe(
    op.Konturen == 1 and abs(float(op.FinalDepth) - 5.0) < 1e-6,
    f"Tasche: {op.Konturen}, {float(op.FinalDepth)}",
)
# Breite 1: eine Schruppbahn je Lage in der Tasche – und die Schlichtbahn.
ko.aendere(op, tc1, ap, ae, 0.3, True, breite=1.0, flaechen=taschen_im_job)
doc.recompute()
pruefe(op.Bahnen == 1 + 1, f"Breite 1: {op.Bahnen} Bahnen")

# Speichern und Laden: dieselbe Bahn.
ko.aendere(op, tc1, ap, ae, 0.3, True, flaechen=waende_im_job)
doc.recompute()
anzahl = len(op.Path.Commands)
pfad = os.path.join(tempfile.mkdtemp(), "kontur.FCStd")
doc.saveAs(pfad)
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(pfad)
op = next(o for o in doc.Objects if ko.ist_kontur(o))
op.touch()
doc.recompute()
pruefe(len(op.Path.Commands) == anzahl, f"nach dem Laden {len(op.Path.Commands)} statt {anzahl}")
pruefe(op.getEditorMode("Lagen") == ["ReadOnly"], "Lagen nach dem Laden")
print(ascii(f"Operation: {anzahl} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
