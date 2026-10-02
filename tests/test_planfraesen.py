# Prüft „Planfräsen“ (W-006 S3b): Block 60 × 40 × 20 mit einem Absatz 5 mm höher an der
# linken Seite (x 0 … 10), Rohteil mit 1 mm Aufmaß rundum (Oberkante 26), Manuels
# Standardfräser Ø 12 (werkzeuge.standardwerkzeug: ae 1,5, ap 25). Die Hüllfläche je Zeile
# (hoehenfeld) hält die Zeilen vor dem Absatz an; die Bahn: eine Lage auf 20 (6 mm bei ap 25),
# 23 Zeilen längs x hin und her, Halbkreise am freien Ende, Rampe ins Material, beim Austritt
# halber Vorschub; die Befehle mit G1, G2, G3 und F; die Zeit. Dann die CAM-Operation im Job:
# angelegt (Tiefen und Höhen wie FreeCAD), gerechnet, geändert, auf den Absatz gestellt,
# gespeichert und geladen. Nur im Gleichlauf (P-2026-10-02-24): jede Zeile in Richtung Gleichlauf,
# danach abheben und von vorne.
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
werkzeug = wz.standardwerkzeug()  # Ø 12: Radius 6
R = werkzeug.durchmesser / 2
form = ff.scheibe(R)
huelle = hf.je_zeile(netz, form, np.array([20.0]), 0.0, 0.5, 141)  # x 0 … 70 auf y = 20
z = huelle[:, 0]
x = 0.5 * np.arange(141)
pruefe(all(abs(z[i] - 25.0) < 1e-6 for i in range(141) if x[i] <= 16.0 - 1e-9), "vor dem Absatz")
# Über der Fläche (die im Netz fehlt) sieht die Stirn erst die Unterseite des Blocks bei 0.
pruefe(
    all(abs(z[i]) < 1e-6 for i in range(141) if 16.0 + 1e-9 < x[i] < 54.0 - 1e-9),
    f"über der Fläche: {[(x[i], z[i]) for i in range(141) if 16 < x[i] < 54][:3]}",
)
pruefe(all(not np.isfinite(z[i]) for i in range(141) if x[i] > 66.0 + 1e-9), "neben dem Teil")
# Die Seitenwand bei x = 60 ragt bis z = 20: unter der Lage 20 nicht im Weg, darüber frei.
rand = [z[i] for i in range(141) if 54.0 + 1e-9 < x[i] < 66.0 - 1e-9]
pruefe(all(abs(wert - 20.0) < 1e-6 for wert in rand), f"an der Seitenwand: {rand[:3]}")
# Zeilen längs y: dieselbe Hüllfläche quer.
# Längs y bei x = 5 liegt der Absatz unter der Stirn (25), bei x = 30 nur die Unterseite (0)
# – an den Enden der Fläche (y 0 und 40) die Seitenwände bis 20 (Stirn R 6: y −6 … 46).
huelle_y = hf.je_zeile(netz, form, np.array([5.0, 30.0]), -10.0, 0.5, 121, laengs_x=False)
pruefe(
    all(abs(wert - 25.0) < 1e-6 for wert in huelle_y[20:101, 0])
    and all(abs(wert) < 1e-6 for wert in huelle_y[33:88, 1])
    and all(abs(wert - 20.0) < 1e-6 for wert in huelle_y[21:32, 1]),
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

# --- Planfräsen: eine Lage, Zeilen vor dem Absatz, Halbkreise, Rampe, Austritt ---------------
# Mit den Werten des Standardfräsers: ae 1,5 als Zeilenabstand, ap 25 als Zustellung – die
# 6 mm über der Fläche sind eine Lage.
planen_einsatz = next(e for e in werkzeug.einsaetze(wz.ALLE) if e.art == wz.PLANEN)
werte = pb.Planwerte(
    form=form,
    zustellung=planen_einsatz.ap,
    zeilenabstand=planen_einsatz.ae,
    aufmass=0.0,
    oben=26.0,
    sicher=31.0,
    rohteil=(-1.0, 61.0, -1.0, 41.0),
)
bahn = pb.planen(netz, werte, [flaeche])
pruefe((bahn.flaechen, bahn.lagen) == (1, 1), f"Flächen, Lagen: {bahn.flaechen}, {bahn.lagen}")
# Die Zeilen quer: Die Seiten y 0 und 40 sind offen – die erste und die letzte Zeile greifen
# nur so breit ins Rohteil (y −1 und 41), dass Breite · Tiefe nicht über ae · ap liegt
# (P-2026-10-01-49): 1,5 · 25 / 6 = 6,25, also von −1 − 6 + 6,25 = −0,75 bis 40,75,
# höchstens 1,5 auseinander: 29 Zeilen (bis dahin 23 von R − 0,2 Ø = 3,6 bis 36,4 – die erste
# griff 10,6 breit).
rand_quer = R - pb.SEITE_ANTEIL * 2 * R
breit = min(2 * R - pb.SEITE_ANTEIL * 2 * R, planen_einsatz.ae * planen_einsatz.ap / 6.0)
erste_y, letzte_y = -1.0 - R + breit, 41.0 + R - breit
anzahl_zeilen = int(math.ceil((letzte_y - erste_y) / planen_einsatz.ae - 1e-9)) + 1
pruefe(anzahl_zeilen == 29 and bahn.zeilen == anzahl_zeilen, f"Zeilen {bahn.zeilen}")
pruefe(abs(bahn.z_min - 20.0) < 1e-9, f"z_min {bahn.z_min}")
vorschub = [p for p in bahn.punkte if not p.eilgang]
hoehen = sorted({round(p.z, 6) for p in vorschub if not p.eintauchen and p.z <= 26.0})
pruefe(all(abs(h - 20.0) < 1e-6 or h > 20.0 for h in hoehen), f"Höhen: {hoehen[:8]}")
in_lage = [p for p in vorschub if abs(p.z - 20.0) < 1e-6]
# Längs: vor dem Absatz (x = 10) hält die Stirn mit R 6 an, über das Ende (60) läuft die Mitte
# um den Überlauf 0,6 Ø = 7,2 hinaus – und nicht weiter als das Rohteil (61) plus R.
ueberlauf = pb.UEBERLAUF_ANTEIL * 2 * R
x_links, x_rechts = min(p.x for p in in_lage), max(p.x for p in in_lage)
pruefe(
    x_links >= 10.0 + R - 1e-6
    and x_links < 10.0 + R + 0.5
    and 66.0 < x_rechts <= 60.0 + ueberlauf + 1e-6,
    f"x {x_links} … {x_rechts}",
)
# Die Zeilen liegen auf y −0,75 … 40,75 (am freien Ende zu sehen) – über den Rand der Fläche
# hinaus, die Wandfahrt muss nicht weiter.
zeilen_y = sorted({round(p.y, 6) for p in in_lage if abs(p.x - x_rechts) < 1e-6})
pruefe(
    len(zeilen_y) == anzahl_zeilen
    and abs(zeilen_y[0] - erste_y) < 1e-6
    and abs(zeilen_y[-1] - letzte_y) < 1e-6,
    f"Zeilen y {zeilen_y[:2]} … {zeilen_y[-2:]}",
)
pruefe(
    abs(min(p.y for p in in_lage) - erste_y) < 1e-6
    and abs(max(p.y for p in in_lage) - letzte_y) < 1e-6,
    f"y {min(p.y for p in in_lage)} … {max(p.y for p in in_lage)}",
)
boegen = [p for p in vorschub if p.bogen is not None]
pruefe(len(boegen) == anzahl_zeilen // 2, f"Bögen: {len(boegen)}")  # am freien Ende, jede zweite
pruefe(all(abs(p.x - x_rechts) < 1e-6 for p in boegen), "Bogen nicht am freien Ende")
abstand_zeilen = (letzte_y - erste_y) / (anzahl_zeilen - 1)
pruefe(
    all(
        abs(math.hypot(p.x - p.bogen[0], p.y - p.bogen[1]) - abstand_zeilen / 2) < 1e-6
        for p in boegen
    ),
    "Bogenradius ist nicht der halbe Zeilenabstand",
)
# Beim Austritt ab x = 61 − R = 55 bis zum Ende der halbe Vorschub.
langsam = [p for p in vorschub if p.anteil < 1.0]
pruefe(
    len(langsam) >= anzahl_zeilen // 2 and all(abs(p.x - x_rechts) < 1e-6 for p in langsam),
    f"Austritt: {len(langsam)} Sätze, x {sorted({round(p.x, 3) for p in langsam})}",
)
# Vor der Wand fährt der Fräser an ihr entlang: zur vorigen Zeile zurück, über die ganze
# Fläche (y 0 bis 40 und darüber hinaus) – so bleibt in den Zwischenräumen und Ecken an der
# Wand nichts stehen (gefunden mit der Simulation, W-006 S3d).
an_der_wand = sorted({round(p.y, 2) for p in in_lage if abs(p.x - x_links) < 1e-6})
pruefe(
    an_der_wand and an_der_wand[0] <= 0.0 and an_der_wand[-1] >= 40.0,
    f"Wandfahrt: y {an_der_wand[:3]} … {an_der_wand[-2:]}",
)
knick = [p for p in vorschub if abs(p.x - (61.0 - R)) < 1e-6]
pruefe(len(knick) >= anzahl_zeilen // 2, f"der Punkt vor dem Austritt fehlt: {len(knick)}")
# Rampe: die Lage beginnt in der Luft vor der Wand (x = 16) senkrecht; wo es im Material
# anfängt, geht es über die Rampe.
eintauchen = [p for p in vorschub if p.eintauchen]
pruefe(len(eintauchen) >= 1, f"Eintauchen: {len(eintauchen)}")
start = bahn.punkte[0]
pruefe(
    start.eilgang and abs(start.z - 31.0) < 1e-9 and abs(start.x - x_links) < 1e-6, f"Start {start}"
)
pruefe(bahn.punkte[-1].eilgang and abs(bahn.punkte[-1].z - 31.0) < 1e-9, "Ende nicht oben")
pruefe(bahn.laenge > anzahl_zeilen * 50.0, f"Länge {bahn.laenge}")
pruefe(bn.dauer(bahn.punkte, 1000.0) > 1.2, f"Zeit {bn.dauer(bahn.punkte, 1000.0)}")
# Die Zeilenrichtung ist gerechnet (Grundsatz 0): längs x 29 Zeilen zu 50 mm, längs y wären
# es 31 Zeilen zu 40 mm in zwei Lagen – längs x ist schneller; die andere Zeit steht dabei.
# Vorgegeben längs y: 31 Zeilen, ohne Vergleich.
pruefe(bahn.richtungen == (True,), f"Richtungen {bahn.richtungen}")
pruefe(
    bahn.zeit > 0 and bahn.zeit_andere is not None and bahn.zeit_andere > bahn.zeit,
    f"Zeit längs x {bahn.zeit}, längs y {bahn.zeit_andere}",
)
pruefe(abs(bahn.zeit - bn.zeit(bahn.punkte, 1000.0)) < 1e-9, "Zeit wie bahn.zeit bei 1000")
quer = pb.planen(netz, pb.Planwerte(*werte.__dict__.values()), [flaeche])
pruefe(quer.zeilen == bahn.zeilen and quer.zeit_andere is not None, "gleich noch einmal")
werte_y = pb.Planwerte(
    form, werte.zustellung, werte.zeilenabstand, 0.0, 26.0, 31.0, werte.rohteil, laengs=False
)
bahn_y_erzwungen = pb.planen(netz, werte_y, [flaeche])
# 31 Zeilen auf x 13,6 … 57,4: Vor dem Absatz (x 10) ist die Seite zu, dort bleibt R − 0,2 Ø
# – und die erste Zeile hätte keine freie Seite: darum zwei Lagen zu 3 mm (2 R · 3 nicht über
# ae · ap). Die Seite bei x 60 ist offen; dort greift die letzte Zeile bei 3 mm Tiefe 9,6 breit
# (R − 0,2 Ø darüber hinaus). Der Zähler zählt die beiden Zeilen an der Absatzwand doppelt,
# weil sie dort in zwei Stücken gefahren werden. Dazu die Zeile an der Absatzwand (x 10 + R +
# Zugabe): Die Zeilen davor ragen in die Wand und fallen weg, die erste freie ließ 0,6 mm an ihr
# stehen (P-2026-10-02-18).
breit_y = min(2 * R - pb.SEITE_ANTEIL * 2 * R, planen_einsatz.ae * planen_einsatz.ap / 3.0)
zeilen_y_erwartet = (
    int(math.ceil((61.0 + R - breit_y - (10.0 + rand_quer)) / planen_einsatz.ae - 1e-9)) + 1
)
x_zeilen_y = {
    round(p.x, 6)
    for p in bahn_y_erzwungen.punkte
    if not p.eilgang and abs(p.z - 20.0) < 1e-6 and p.bogen is None
}
x_wand = 10.0 + R + hf.TOLERANZ + pb.vb.RAND
pruefe(
    any(abs(x - x_wand) < 1e-6 for x in x_zeilen_y),
    f"keine Zeile an der Absatzwand (x {x_wand}): {sorted(x_zeilen_y)[:4]}",
)
pruefe(
    bahn_y_erzwungen.richtungen == (False,)
    and len(x_zeilen_y) == zeilen_y_erwartet + 1 == 32
    and bahn_y_erzwungen.lagen == 2
    and bahn_y_erzwungen.zeilen >= zeilen_y_erwartet
    and bahn_y_erzwungen.zeit_andere is None
    and abs(bahn_y_erzwungen.zeit - bahn.zeit_andere) < 1e-9
    and bahn_y_erzwungen.zeit > bahn.zeit,
    f"längs y erzwungen: {bahn_y_erzwungen.richtungen}, {len(x_zeilen_y)} Zeilenlagen, "
    f"{bahn_y_erzwungen.zeilen} Zeilen, {bahn_y_erzwungen.zeit} min",
)
# Mit dem echten Vorschub (902 mm/min) rechnet die Zeit damit.
werte_vf = pb.Planwerte(
    form, werte.zustellung, werte.zeilenabstand, 0.0, 26.0, 31.0, werte.rohteil, vorschub=902.0
)
bahn_vf = pb.planen(netz, werte_vf, [flaeche])
pruefe(abs(bahn_vf.zeit - bn.zeit(bahn_vf.punkte, 902.0)) < 1e-9, "Zeit mit Vorschub")
befehle = bn.befehle(bahn.punkte, 1000.0, 200.0)
namen = {b.Name for b in befehle}
pruefe({"G0", "G1"} <= namen and ("G2" in namen or "G3" in namen), f"Befehle: {namen}")
print(ascii(f"Planfraesen: {len(bahn.punkte)} Punkte, {len(befehle)} Befehle"))

# Zeilen längs y, wenn die Fläche quer länger ist: das schmale Teil.
schmal = Part.makeBox(20, 60, 10)
oben_schmal = hf.ebenen_oben(schmal)
bahn_y = pb.planen(
    vh.vernetze(schmal),
    pb.Planwerte(form, 25.0, 1.5, 0.0, 12.0, 17.0, (-1.0, 21.0, -1.0, 61.0)),
    [e for e in oben_schmal if abs(e.z - 10.0) < 1e-6],
)
in_lage = [p for p in bahn_y.punkte if not p.eilgang and abs(p.z - 10.0) < 1e-6]
pruefe(
    min(p.y for p in in_lage) <= -6.0 + 1e-6 and max(p.y for p in in_lage) >= 66.0 - 1e-6,
    f"längs y: {min(p.y for p in in_lage)} … {max(p.y for p in in_lage)}",
)
pruefe(abs(bahn_y.z_min - 10.0) < 1e-9 and bahn_y.lagen == 1, "schmal: eine Lage")
pruefe(bahn_y.richtungen == (False,), f"schmal: Zeilen längs y – {bahn_y.richtungen}")

# Zwei Flächen übereinander (P-2026-10-02-21): ein Zapfen 40 × 30 × 10 auf der Platte 100 × 80.
# Die Oberseite des Zapfens greift nicht mehr bis an den Rand des Rohteils aus – dort liegt der
# Boden derselben Bahn, dessen Lage am Rohteil beginnt und es ohnehin räumt; vorher fräste sie
# die ganze Platte 1 mm ab: 151 Zeilen und 15,6 min, jetzt 117 Zeilen und 13,5 min.
platte = Part.makeBox(100, 80, 20, V(0, 0, -30)).fuse(Part.makeBox(40, 30, 10, V(30, 25, -10)))
platte = platte.removeSplitter()
beide = [e for e in hf.ebenen_oben(platte) if e.z > -29]
oben_zapfen = next(e for e in beide if abs(e.z) < 1e-6)
pruefe(len(beide) == 2, f"Zapfen: {[(e.name, e.z) for e in beide]}")
werte_zapfen = pb.Planwerte(form, 25.0, 1.5, 0.0, 1.0, 6.0, (-1.0, 101.0, -1.0, 81.0))
netz_zapfen = hf.netz_ohne(platte, [e.name for e in beide])
allein = pb.planen(netz_zapfen, werte_zapfen, [oben_zapfen])
zusammen = pb.planen(netz_zapfen, werte_zapfen, beide)
in_lage_0 = [p for p in zusammen.punkte if not p.eilgang and abs(p.z) < 1e-6]
in_lage_allein = [p for p in allein.punkte if not p.eilgang and abs(p.z) < 1e-6]
weit = R + pb.UEBERLAUF_ANTEIL * 2 * R + 1.0  # Stirn, Überlauf und etwas Luft


def am_rand_des_rohteils(punkte):
    """Reicht die Stirn (Radius R um die Punkte) quer bis an den Rand des Rohteils (−1 … 101
    oder −1 … 81)?"""
    xs, ys = [p.x for p in punkte], [p.y for p in punkte]
    return (min(xs) - R < -1.0 and max(xs) + R > 101.0) or (
        min(ys) - R < -1.0 and max(ys) + R > 81.0
    )


pruefe(
    in_lage_0
    and not am_rand_des_rohteils(in_lage_0)
    and min(p.x for p in in_lage_0) > 30.0 - weit
    and max(p.x for p in in_lage_0) < 70.0 + weit
    and min(p.y for p in in_lage_0) > 25.0 - weit
    and max(p.y for p in in_lage_0) < 55.0 + weit,
    f"Zapfen oben: x {min(p.x for p in in_lage_0)} … {max(p.x for p in in_lage_0)}, "
    f"y {min(p.y for p in in_lage_0)} … {max(p.y for p in in_lage_0)}",
)
pruefe(
    zusammen.zeilen < 125 and zusammen.zeit < 14.0, f"Zapfen: {zusammen.zeilen}, {zusammen.zeit}"
)
pruefe(am_rand_des_rohteils(in_lage_allein), "Zapfen allein: nicht bis an den Rand des Rohteils")

# Fehler mit einem Satz: Kugel, Zeilenabstand zu groß (über Ø), nichts über der Fläche, keine
# Fläche.
for werte_falsch, ebenen_falsch, text in (
    (pb.Planwerte(ff.kugel(R), 25.0, 1.5, 0.0, 26.0, 31.0, werte.rohteil), [flaeche], "Kugel"),
    (pb.Planwerte(form, 25.0, 13.0, 0.0, 26.0, 31.0, werte.rohteil), [flaeche], "Abstand"),
    (pb.Planwerte(form, 25.0, 1.5, 0.0, 20.0, 31.0, werte.rohteil), [flaeche], "nichts drüber"),
    (werte, [], "keine Fläche"),
):
    try:
        pb.planen(netz, werte_falsch, ebenen_falsch)
    except ValueError as grund:
        pruefe(len(str(grund)) > 10, f"{text}: kein Satz")
    else:
        pruefe(False, f"{text}: keine Fehlermeldung")


# --- Nur im Gleichlauf (P-2026-10-02-24) -----------------------------------------------------
# Manuel: „auswählbar, ob er abhebt und wieder von vorne anfängt“. Die Zeilen folgen einander mit
# wachsendem y, dort liegt das Material; mit M3 liegt es rechts der Fahrt, wenn x fällt: jede
# Zeile vom freien Ende zur Wand, an ihr zurück zur vorigen, abheben, im Eilgang zurück, von
# vorne. Gleich viele Zeilen, länger als hin und her; mit M4 umgekehrt – die Ecken an der Wand
# dann am Anfang jeder Zeile. An der Wand bleibt in beiden nichts stehen (y 0 … 40).
def zeilenfahrten(b):
    ergebnis = []
    for p, q in zip(b.punkte, b.punkte[1:], strict=False):
        if q.eilgang or q.bogen is not None or abs(q.z - 20.0) > 1e-6 or abs(p.z - 20.0) > 1e-6:
            continue
        if abs(q.y - p.y) < 1e-9 and abs(q.x - p.x) > 1.0:
            ergebnis.append(q.x - p.x)
    return ergebnis


def wandfahrt(b):
    return sorted(
        {
            round(p.y, 2)
            for p in b.punkte
            if not p.eilgang and abs(p.z - 20.0) < 1e-6 and abs(p.x - x_links) < 1e-6
        }
    )


for gleichlauf, name in ((True, "M3"), (False, "M4")):
    einzeln = pb.planen(netz, replace(werte, nur_gleichlauf=True, gleichlauf=gleichlauf), [flaeche])
    fahrten_e = zeilenfahrten(einzeln)
    pruefe(einzeln.zeilen == bahn.zeilen, f"{name}: {einzeln.zeilen} Zeilen")
    pruefe(
        fahrten_e and all((dx < 0) == gleichlauf for dx in fahrten_e),
        f"{name}: Richtungen {sorted({round(dx) for dx in fahrten_e})}",
    )
    abgehoben = sum(
        1
        for p, q in zip(einzeln.punkte, einzeln.punkte[1:], strict=False)
        if q.eilgang and abs(q.z - 31.0) < 1e-9 and p.z < 31.0 - 1e-9
    )
    pruefe(abgehoben >= einzeln.zeilen, f"{name}: {abgehoben}-mal abgehoben")
    pruefe(einzeln.zeit > bahn.zeit, f"{name}: {einzeln.zeit:.2f} nicht länger als {bahn.zeit:.2f}")
    wand_e = wandfahrt(einzeln)
    pruefe(wand_e and wand_e[0] <= 0.0 and wand_e[-1] >= 40.0, f"{name}: Wand {wand_e[:2]} …")
    print(ascii(f"Nur im Gleichlauf ({name}): {einzeln.zeit:.2f} min, hin und her {bahn.zeit:.2f}"))

# --- Die CAM-Operation im Job ---------------------------------------------------------------
import Path.Main.Job as PathJob

schaft = werkzeug  # T1, der Standardfräser mit dem Einsatz Planen
kugel = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)
kugel.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=6, vc=150, fz=0.04)]
ue.uebergeben(wz.Bibliothek([schaft, kugel]))
ap, ae = planen_einsatz.ap, planen_einsatz.ae

doc = FreeCAD.newDocument("Planfraesen")
doc.UndoMode = 1
teil = doc.addObject("Part::Feature", "Teil")
teil.Shape = block
doc.recompute()
job = PathJob.Create("Job", [teil])
tc1 = js.controller_ohne_transaktion(doc, job, schaft, planen_einsatz)
tc2 = js.controller_ohne_transaktion(doc, job, kugel, kugel.einsaetze(wz.ALLE)[0])
doc.recompute()
pruefe(
    abs(job.Stock.Shape.BoundBox.ZMax - 26.0) < 1e-6,
    f"Rohteil oben {job.Stock.Shape.BoundBox.ZMax}",
)
klon = job.Model.Group[0]
flaeche_im_job = next(e.name for e in hf.ebenen_oben(klon.Shape) if abs(e.z - 20.0) < 1e-6)
absatz_im_job = next(e.name for e in hf.ebenen_oben(klon.Shape) if abs(e.z - 25.0) < 1e-6)

op = pf.lege_an(job, tc1, zustellung=ap, zeilenabstand=ae, flaechen=[flaeche_im_job])
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
    (op.Ebenen, op.Lagen, op.Zeilen) == (1, 1, anzahl_zeilen),
    f"Operation: {op.Ebenen}, {op.Lagen}, {op.Zeilen}",
)
pruefe(op.Richtung == "X", f"Richtung: {op.Richtung!r}")
pruefe(op.getEditorMode("Richtung") == ["ReadOnly"], "Richtung änderbar")
befehle = op.Path.Commands
namen = [b.Name for b in befehle]
pruefe(
    namen[1:4] == ["G0", "G0", "G0"] and namen[-1] == "G0", f"Befehle: {namen[:5]} … {namen[-1]}"
)
schnitte = [b for b in befehle if b.Name in ("G1", "G2", "G3")]
z_werte = sorted({round(b.Parameters["Z"], 6) for b in schnitte if "Z" in b.Parameters})
pruefe(min(z_werte) >= 20.0 - 1e-6 and 20.0 in z_werte, f"Z {z_werte[:6]}")
pruefe(any(b.Name in ("G2", "G3") for b in schnitte), "keine Bögen in der Operation")
f_werte = sorted({round(b.Parameters["F"], 6) for b in schnitte if "F" in b.Parameters})
pruefe(len(f_werte) >= 2, f"F {f_werte}")
pruefe(op.getEditorMode("Lagen") == ["ReadOnly"], "Lagen änderbar")

# Ändern: zwei Lagen mit 3 mm; der Absatz allein hat nur 1 mm drüber: eine Lage.
pf.aendere(op, tc1, zustellung=3.0, zeilenabstand=ae, aufmass=0.0)
doc.recompute()
pruefe(op.Lagen == 2, f"geändert: {op.Lagen} Lagen")
pf.aendere(op, tc1, zustellung=ap, zeilenabstand=ae, aufmass=0.0, flaechen=[absatz_im_job])
doc.recompute()
pruefe((op.Ebenen, op.Lagen) == (1, 1), f"Absatz: {op.Ebenen}, {op.Lagen}")
pruefe(abs(float(op.FinalDepth) - 25.0) < 1e-6, f"Endtiefe am Absatz {float(op.FinalDepth)}")
x_werte = [b.Parameters["X"] for b in op.Path.Commands if b.Name == "G1" and "X" in b.Parameters]
pruefe(max(x_werte) <= 10.0 + ueberlauf + 1e-6, f"Absatz: x bis {max(x_werte)}")
# Der Kugelfräser: ein Satz statt der Bahn.
pf.aendere(op, tc2, zustellung=2.0, zeilenabstand=3.0, aufmass=0.0, flaechen=[flaeche_im_job])
doc.recompute()
pruefe("ebener Stirn" in op.Path.Commands[1].Name, f"Kugelfräser: {op.Path.Commands[1].Name}")
pf.aendere(op, tc1, zustellung=ap, zeilenabstand=ae, aufmass=0.5, flaechen=[flaeche_im_job])
doc.recompute()
pruefe(abs(float(op.FinalDepth) - 20.5) < 1e-6 and op.Lagen == 1, "zurück mit Aufmaß")
# Ohne Flächen: die Oberseite des Teils – der Absatz.
pf.aendere(op, tc1, zustellung=ap, zeilenabstand=ae, aufmass=0.0, flaechen=[])
doc.recompute()
pruefe(abs(float(op.FinalDepth) - 25.0) < 1e-6 and op.Ebenen == 1, "ohne Wahl: die Oberseite")

# Speichern und Laden: dieselbe Bahn.
pf.aendere(op, tc1, zustellung=ap, zeilenabstand=ae, aufmass=0.0, flaechen=[flaeche_im_job])
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

# --- Großer Fräser, großes ae: zwischen den Zeilen frei (P-2026-10-02-30) -------------------
# Manuels Platte mit dem Planfräser Ø 50, ae 35, ap 2: Die Zeilen liegen 30 mm auseinander. Am
# Ende der Zeile vor dem Zapfen fuhr die Wandfahrt gerade zurück zur vorigen Zeile – 33,75 mm an
# der Zapfenachse vorbei, nötig sind 25 + 10: in jeder Lage in den Zapfen. Jetzt wird auch
# zwischen den Zeilen geprüft; nirgends unter seiner Oberkante näher als 35 mm.
platte = Part.makeBox(200, 200, 30, V(-100, -100, -30))
manuel = (
    platte.fuse(Part.makeCylinder(10, 20, V(50, 50, 0)))
    .cut(Part.makeCylinder(22.5, 20, V(-50, -50, -20)))
    .removeSplitter()
)
ebenen_manuel = [e for e in hf.ebenen_oben(manuel) if abs(e.z) < 1e-6]
werte_gross = pb.Planwerte(
    ff.scheibe(25.0), 2.0, 35.0, 0.0, 20.0, 25.0, (-100.0, 100.0, -100.0, 100.0),
    vorschub=955.0, eintauchen=286.0,
)  # fmt: skip
gross = pb.planen(hf.netze_je_hoehe(manuel, ebenen_manuel), werte_gross, ebenen_manuel)
naechste = math.inf
for von, nach in zip(gross.punkte, gross.punkte[1:], strict=False):
    if nach.eilgang:
        continue
    for t in np.linspace(0.0, 1.0, 41):
        z = von.z + t * (nach.z - von.z)
        if z < 20.0 - 1e-6:
            x, y = von.x + t * (nach.x - von.x), von.y + t * (nach.y - von.y)
            naechste = min(naechste, math.hypot(x - 50.0, y - 50.0))
pruefe(naechste >= 35.0 - 0.05, f"Ø 50 am Zapfen: {naechste:.2f} mm von der Achse (nötig 35)")
print(f"Ø 50 auf der Platte: {gross.zeit:.1f} min, am Zapfen {naechste:.2f} mm von der Achse")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
