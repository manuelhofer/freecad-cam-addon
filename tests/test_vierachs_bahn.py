# Prüft die Schruppbahn rundum (W-003 Stufe V3b): Welle Ø 60 in der Stange Ø 80 –
# fünf Lagen bis Ø 60,6, die Spirale von vorne bis 6,5 mm hinter das Teil (Überlauf,
# V3f), dort auf der Tiefe der letzten Kontur, nie näher ans Teil als das Aufmaß; ist
# das Futter näher, bleibt der Rand des Fräsers den Abstand zum Futter davor. Beim
# Exzenter auch zwischen den Punkten gegen die Formel. Dazu die Path-Befehle für C und A
# mit G93 und die Fälle, die nicht gehen. Nur über gewählten Flächen (V4): Abflachung einer
# Welle – gefräst wird nur, wo der Fräser sie berührt, in Zeilen hin und her; hinein über
# eine Rampe. Gleichlauf über die Rundachse (P-2026-10-02-23): mit M3 steigt φ, während die
# Spirale zum Futter rückt; andersherum (M4) fällt es – dieselbe Bahn gespiegelt. Mit
# Flächen nur im Gleichlauf (P-2026-10-02-26): jede Zeile für sich in einer Richtung.
import math
import os
import sys
from dataclasses import replace

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import restmaterial as rm
from camaddon import spindel as sp
from camaddon import vierachs_bahn as vb
from camaddon import vierachs_flaechen as vf
from camaddon import vierachs_huelle as vh
from camaddon import vierachs_rohteil as vr
from camaddon.sprache import tr

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
R = 6.0
C_LAENGS, C_RADIAL = (0, 0, 1), (1, 0, 0)
# Teil von a = −100 bis 0, Planaufmaß 1; die Stange ragt so weit heraus, wie die Bahn
# braucht: Überlauf 6,5 + Fräser 6 + Abstand zum Futter 5 – Futter bei −117,5.
WERTE = vb.Schruppwerte(
    fraeser_radius=R,
    stange_radius=40.0,
    zustellung=2.0,
    steigung=4.8,
    aufmass=0.3,
    a_stange_vorne=1.0,
    a_futter=-117.5,
)


def schnitte(bahn):
    return [p for p in bahn.punkte if not p.eilgang]


# --- Welle Ø 60 ------------------------------------------------------------------------------
welle = vh.vernetze(Part.makeCylinder(30, 100, V(0, 0, -100)))
bahn = vb.schruppen(welle, C_LAENGS, C_RADIAL, WERTE)

# --- Gleichlauf über die Rundachse (P-2026-10-02-23) ------------------------------------------
# spindel.ist_gleichlauf für jede Lage des Fräsers: M3, das Material rechts der Fahrt, von der
# Spindel aus gesehen. Senkrecht über dem Tisch wie G41; radial am Mantel macht die Rundachse die
# Fahrt: Rückt die Spirale zum Futter vor (−längs), muss φ steigen; nach vorn fallen.
pruefe(sp.ist_gleichlauf((0, 0, -1), (1, 0, 0), (0, -1, 0)), "senkrecht: Material rechts")
pruefe(not sp.ist_gleichlauf((0, 0, -1), (1, 0, 0), (0, 1, 0)), "senkrecht: Material links")
pruefe(sp.ist_gleichlauf((-1, 0, 0), (0, 1, 0), (0, 0, -1)), "radial, zum Futter, φ steigt")
pruefe(not sp.ist_gleichlauf((-1, 0, 0), (0, 1, 0), (0, 0, 1)), "radial, nach vorn, φ steigt")
pruefe(sp.ist_gleichlauf((0, 0, -1), (0, 1, 0), (1, 0, 0)), "längs an der Stirn, außen")


def erste_lage(b):
    lage = []
    for p in b.punkte[1:]:
        if p.eilgang and lage:
            break
        if not p.eilgang:
            lage.append(p)
    return lage


gleich = erste_lage(bahn)
gegen_bahn = vb.schruppen(welle, C_LAENGS, C_RADIAL, replace(WERTE, gleichlauf=False))
gegen = erste_lage(gegen_bahn)
pruefe(
    all(q.phi > p.phi for p, q in zip(gleich, gleich[1:], strict=False))
    and all(q.a <= p.a for p, q in zip(gleich, gleich[1:], strict=False)),
    "M3: φ steigt nicht, während die Spirale zum Futter rückt",
)
pruefe(
    all(q.phi < p.phi for p, q in zip(gegen, gegen[1:], strict=False)),
    "andersherum (M4): φ fällt nicht",
)
pruefe(
    gegen_bahn.lagen == bahn.lagen and [(p.a, p.r) for p in gegen] == [(p.a, p.r) for p in gleich],
    "andersherum nicht dieselbe Bahn gespiegelt",
)
befehle_gegen = vb.befehle(gegen_bahn, C_LAENGS, C_RADIAL, "C", 1, 500.0)
c_werte = [b.Parameters["C"] for b in befehle_gegen if b.Name == "G1" and "C" in b.Parameters]
pruefe(c_werte[5] > c_werte[0], "andersherum: C mit Drehsinn +1 steigt nicht (C = −φ)")
pruefe(bahn.lagen == 5, f"Lagen: {bahn.lagen}")
pruefe(30.3 <= bahn.r_min <= 30.33, f"tiefster Radius: {bahn.r_min}")
start = bahn.punkte[0]
pruefe(
    start.eilgang and (start.a, start.r, start.phi) == (1.0 + R + 2.0, 42.0, 0.0),
    f"Start: {start}",
)
# Die Lagen schneiden auf 38, 36, 34, 32 – die fünfte folgt dem Teil.
radien = sorted({round(p.r, 6) for p in schnitte(bahn)}, reverse=True)
pruefe(radien[:4] == [38.0, 36.0, 34.0, 32.0], f"Radien der Lagen: {radien[:6]}")
# Wo die Stirn das um das Aufmaß dickere Teil trifft (a ≤ 6,3), bleibt sie darüber.
ueber = [p.r for p in schnitte(bahn) if -100 - R - 0.3 <= p.a <= R + 0.3]
pruefe(min(ueber) >= 30.3, f"zu tief über dem Teil: {min(ueber)}")
# Längs: von vorne bis 6,5 mm hinter das Teil (Mitte des Fräsers) – der Fräser verlässt
# es ganz; dort bleibt die Spitze auf der Tiefe der letzten Kontur, statt hochzuspringen.
pruefe(min(p.a for p in bahn.punkte) == -100.0 - R - 0.5, "hinteres Ende")
letzte = [p for p in schnitte(bahn) if p.r < 32]
im_ueberlauf = [p.r for p in letzte if p.a < -100 - R - 0.3]
pruefe(im_ueberlauf and max(im_ueberlauf) < 30.4, f"im Überlauf: {im_ueberlauf[:3]}")
pruefe(bahn.hinten_frei == 0, f"hinten frei: {bahn.hinten_frei}")
pruefe(max(p.a for p in bahn.punkte) == start.a, "vorderes Ende")
# Jede Lage: zuerst radial hinein vor der Stange, dann von vorne nach hinten, nie zurück.
lage = []
for p in bahn.punkte[1:]:
    if p.eilgang:
        if lage:
            pruefe(lage[0].a == start.a, f"Lage beginnt bei {lage[0].a}")
            pruefe(
                all(b.a <= a.a and b.phi >= a.phi for a, b in zip(lage, lage[1:], strict=False)),
                "Spirale läuft nicht stetig nach hinten",
            )
        lage = []
    else:
        lage.append(p)
# Ein Satz dreht höchstens 90° (FreeCAD 1.1.3 zeigt mehr als eine Gerade).
grad = max(abs(b.phi - a.phi) for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False))
pruefe(grad <= vb.HOECHSTENS_GRAD + 1e-9, f"ein Satz dreht {grad}°")
# Die vier oberen Lagen liegen über dem ganzen Teil: je Lage höchstens alle 90° ein Punkt.
pruefe(len(bahn.punkte) < 400 * 4 + 9000, f"zu viele Punkte: {len(bahn.punkte)}")
print(ascii(f"Welle: {bahn.lagen} Lagen, {len(bahn.punkte)} Punkte"))

# --- Exzenter Ø 20, 15 mm außermittig: nie näher als das Aufmaß, auch zwischen den Punkten
exzenter = vh.vernetze(Part.makeCylinder(10, 100, V(15, 0, -100)))
bahn = vb.schruppen(exzenter, C_LAENGS, C_RADIAL, WERTE)


def soll_exzenter(phi_grad):
    """Die höchste Stelle des um das Aufmaß dickeren Exzenters unter der Stirn (mm)."""
    phi = math.radians(phi_grad)
    x, y = 15 * math.cos(phi), -15 * math.sin(phi)
    radius = 10 + WERTE.aufmass
    seitlich = abs(y) - R
    if seitlich <= 0:
        return x + radius
    if seitlich > radius:
        return -math.inf
    return x + math.sqrt(radius * radius - seitlich * seitlich)


schlimmste = math.inf
for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False):
    if b.eilgang:
        continue
    for t in (i / 10 for i in range(11)):
        stelle = a.a + t * (b.a - a.a)
        if not -100 + R <= stelle <= -R:  # dort zählt nur der Querschnitt
            continue
        luft = a.r + t * (b.r - a.r) - soll_exzenter(a.phi + t * (b.phi - a.phi))
        schlimmste = min(schlimmste, luft)
pruefe(schlimmste >= -1e-6, f"Exzenter: {schlimmste:.4f} mm ins Aufmaß")
pruefe(schlimmste < 0.2, f"Exzenter: überall mindestens {schlimmste:.4f} mm Luft")
print(ascii(f"Exzenter: {bahn.lagen} Lagen, knappste Stelle {schlimmste:.4f} mm"))
# Wo der Exzenter hinter der Achse liegt, kreuzt die Spitze sie: bis an seine nahe Seite
# (15 − 10 = 5 mm hinter der Achse, plus Aufmaß), nicht weiter – bis P-2026-10-03-07 blieb sie
# einen Fräserradius vor der Achse stehen (Manuels Teil neben der Achse: ein Kern blieb).
tiefste = min(p.r for p in schnitte(bahn) if -100 + R <= p.a <= -R)
pruefe(-5.0 - WERTE.aufmass - 0.1 <= tiefste < 0.0, f"über die Achse: tiefste Spitze {tiefste:.2f}")

# --- Path-Befehle ------------------------------------------------------------------------------
kurz = vb.Bahn(
    [
        vb.Punkt(True, 9.0, 42.0, 0.0),
        vb.Punkt(False, 9.0, 38.0, 0.0),
        vb.Punkt(False, 4.2, 38.0, 360.0),
        vb.Punkt(True, 4.2, 42.0, 360.0),
    ],
    1,
    38.0,
)
befehle = vb.befehle(kurz, C_LAENGS, C_RADIAL, "C", 1, 1500.0)
namen = [b.Name for b in befehle]
pruefe(
    namen[0].startswith("(") and namen[1:] == ["G0", "G0", "G93", "G1", "G1", "G0", "G94"],
    f"Befehle: {namen}",
)
pruefe(befehle[1].Parameters == {"X": 42.0}, f"zuerst radial: {befehle[1].Parameters}")
pruefe(
    befehle[2].Parameters == {"X": 42.0, "Y": 0.0, "Z": 9.0, "C": 0.0},
    f"Anfang: {befehle[2].Parameters}",
)
hinein, spirale = befehle[4].Parameters, befehle[5].Parameters
# F auf 6 Stellen, wie FreeCAD es speichert – im Programm (× 60) höchstens 3e-5 daneben.
F_GENAU = 60 * 0.5e-6 + 1e-12
pruefe(abs(hinein["F"] * 60 - 1500 / 4) < F_GENAU, f"F hinein: {hinein}")
weg = math.hypot(4.8, 38.0 * 2 * math.pi)
pruefe(
    abs(spirale["F"] * 60 - 1500 / weg) < F_GENAU
    and spirale["C"] == -360.0
    and abs(spirale["Z"] - 4.2) < 1e-12,
    f"Spirale: {spirale}",
)
pruefe("Y" not in spirale, f"Y in jedem Satz: {spirale}")
# Dreht die Maschine andersherum, zählt die Rundachse mit.
andersrum = vb.befehle(kurz, C_LAENGS, C_RADIAL, "C", -1, 1500.0)
pruefe(andersrum[5].Parameters["C"] == 360.0, f"drehsinn −1: {andersrum[5].Parameters}")
# Rundachse A: Stange längs X, Werkzeug von oben – der Radius steht in Z.
mit_a = vb.befehle(kurz, (1, 0, 0), (0, 0, 1), "A", 1, 1500.0)
pruefe(mit_a[1].Parameters == {"Z": 42.0}, f"A radial: {mit_a[1].Parameters}")
pruefe(
    mit_a[2].Parameters == {"X": 9.0, "Y": 0.0, "Z": 42.0, "A": 0.0},
    f"A Anfang: {mit_a[2].Parameters}",
)
pruefe("Radius in Z" in mit_a[0].Name, f"Kommentar: {mit_a[0].Name}")
ohne_quer = vb.befehle(kurz, C_LAENGS, C_RADIAL, "C", 1, 1500.0, quer_auf_null=False)
pruefe("Y" not in ohne_quer[2].Parameters, f"ohne Y: {ohne_quer[2].Parameters}")
pruefe(abs(vb.dauer(kurz, 1500.0) - (4 + weg) / 1500.0) < 1e-12, f"Dauer: {vb.dauer(kurz, 1500)}")
# Ins Material senkrecht mit dem Eintauchvorschub (V4).
senkrecht = vb.Bahn(
    [kurz.punkte[0], replace(kurz.punkte[1], eintauchen=True), *kurz.punkte[2:]], 1, 38.0
)
eingetaucht = vb.befehle(senkrecht, C_LAENGS, C_RADIAL, "C", 1, 1500.0, eintauchen=300.0)
pruefe(
    abs(eingetaucht[4].Parameters["F"] * 60 - 300 / 4) < F_GENAU, f"F eintauchen: {eingetaucht[4]}"
)
pruefe(abs(eingetaucht[5].Parameters["F"] * 60 - 1500 / weg) < F_GENAU, "F danach")
# Gleich lange Sätze (nach dem ersten, radial hinein) hätten dasselbe F – manche
# Postprozessoren (Fanuc, UCCNC) ließen es dann weg, in G93 ein Alarm. Das zweite bekommt eine
# Einheit der 6. Stelle mehr, das dritte ist wieder das erste (P-2026-09-30-39).
gleich = vb.Bahn(
    [vb.Punkt(False, 9.0, 42.0, 0.0)]
    + [vb.Punkt(False, 9.0 - 1.2 * i, 38.0, 90.0 * i) for i in range(1, 5)],
    1,
    38.0,
)
f_werte = [b.Parameters["F"] for b in vb.befehle(gleich, C_LAENGS, C_RADIAL, "C", 1, 1500.0)[4:8]]
pruefe(
    f_werte[2] == round(f_werte[1] + 1e-6, 6)
    and f_werte[3] == f_werte[1] != f_werte[0]
    and all(round(f, 6) == f for f in f_werte),
    f"gleiche F: {f_werte}",
)
pruefe(
    abs(vb.dauer(senkrecht, 1500.0, 300.0) - (4 / 300.0 + weg / 1500.0)) < 1e-12,
    "Dauer mit Eintauchen",
)

# --- Was nicht geht ------------------------------------------------------------------------------
for name, werte in (
    ("Vorschub je Umdrehung größer als der Fräser", {"steigung": 13.0}),
    ("kein Platz vor dem Futter", {"a_futter": -1.0}),
    ("Zustellung 0", {"zustellung": 0.0}),
):
    try:
        vb.schruppen(welle, C_LAENGS, C_RADIAL, WERTE.__class__(**{**WERTE.__dict__, **werte}))
        fehler.append(f"{name}: kein Fehler")
    except ValueError:
        pass
# Futter 0,5 mm hinter dem Teil: Der Rand des Fräsers bleibt 5 mm davor – die letzten
# 4,5 mm fehlen. Mit Abstand 2 und ohne Überlauf endet die Mitte am Teil.
knapp = vb.schruppen(
    welle, C_LAENGS, C_RADIAL, WERTE.__class__(**{**WERTE.__dict__, "a_futter": -100.5})
)
pruefe(abs(knapp.hinten_frei - 4.5) < 1e-9, f"hinten frei: {knapp.hinten_frei}")
eigen = vb.schruppen(
    welle,
    C_LAENGS,
    C_RADIAL,
    WERTE.__class__(**{**WERTE.__dict__, "ueberlauf": 0.0, "abstand_futter": 2.0}),
)
pruefe(min(p.a for p in eigen.punkte) == -100.0, f"ohne Überlauf: {min(p.a for p in eigen.punkte)}")
# Ein Halter, der 27,5 mm über die Werkzeugachse reicht (Kopf des „VDI30 angetrieben
# radial“): Er bleibt 5 mm vor dem Futter, die Mitte also 32,5 – die letzten 26 fehlen.
mit_halter = vb.schruppen(
    welle,
    C_LAENGS,
    C_RADIAL,
    WERTE.__class__(**{**WERTE.__dict__, "a_futter": -100.5, "halter": 27.5}),
)
pruefe(abs(mit_halter.hinten_frei - 26.0) < 1e-9, f"mit Halter frei: {mit_halter.hinten_frei}")
pruefe(
    abs(min(p.a for p in mit_halter.punkte) - (-68.0)) < 1e-9,
    f"mit Halter bis {min(p.a for p in mit_halter.punkte)}",
)
schmal = vb.schruppen(
    welle, C_LAENGS, C_RADIAL, WERTE.__class__(**{**WERTE.__dict__, "halter": 3.0})
)
pruefe(
    schmal.punkte == vb.schruppen(welle, C_LAENGS, C_RADIAL, WERTE).punkte,
    "ein schmaler Halter ändert nichts",
)
# Das Futter 20 mm hinter der Stirn: Der Fräser hätte Platz, der Halter nicht.
try:
    vb.schruppen(
        welle,
        C_LAENGS,
        C_RADIAL,
        WERTE.__class__(**{**WERTE.__dict__, "a_futter": -20.0, "halter": 27.5}),
    )
    fehler.append("Halter ohne Platz: kein Fehler")
except ValueError as grund:
    pruefe(str(grund) == tr("vb.fehler.platz_halter"), f"kein Platz für den Halter: {grund}")
pruefe(vb.ueberlauf_vorschlag(6.0) == 6.5, "Vorschlag Überlauf")
# Kugel- und Torusfräser rechnen wie ein Schaftfräser: Zwischen den Bahnen bleiben Rillen –
# Kugel Ø 12 mit 4,8 mm je Umdrehung gut 0,5 mm, Torus mit Eckradius 1 erst ab 10 mm.
pruefe(abs(vb.rillenhoehe(6.0, 6.0, 4.8) - (6 - math.sqrt(36 - 2.4**2))) < 1e-12, "Kugel")
pruefe(vb.rillenhoehe(6.0, 1.0, 4.8) == 0.0, "Torus mit flacher Stirn")
pruefe(abs(vb.rillenhoehe(6.0, 1.0, 11.0) - (1 - math.sqrt(0.75))) < 1e-12, "Torus weit")
pruefe(vb.rillenhoehe(6.0, 0.0, 12.0) == 0.0, "Schaftfräser")
pruefe(bahn.hinten_frei == 0, f"Exzenter hinten frei: {bahn.hinten_frei}")

# --- Ringgang vor einer Wand (D-42) ----------------------------------------------------------
# Welle Ø 50 von −25 bis 0, Ø 36 von −40 bis −25: Die Wand bei −25 schaut zum Futter. Ohne
# Ring kommt die Spirale (4,8 mm je Umdrehung) nur auf einem Teil des Umfangs so weit an die
# Wand, dass der Fräser Ø 12 hinter ihr bis aufs Aufmaß hinunter darf – dort bleibt bis zum
# großen Ø stehen. Mit Ring hält sie bei −25 − 6 − 0,3 = −31,3 eine Umdrehung an.
absatz = Part.makeCylinder(25, 25, V(0, 0, -25)).fuse(Part.makeCylinder(18, 15, V(0, 0, -40)))
absatz_netz = vh.vernetze(absatz.removeSplitter())
werte_absatz = WERTE.__class__(**{**WERTE.__dict__, "stange_radius": 30.0, "a_futter": -60.0})


def rest_hinter_der_wand(bahn):
    """Wie viel die Bahn hinter der Wand (a −30,5 … −26) über Ø 36 stehen lässt, höchstens –
    dicht an der Wand bleibt ohnehin das Aufmaß, dort schlichtet der Ring des Schlichtens."""
    stange = rm.Stange(30.0, -60.0, 1.0)
    von, nach = [], []
    for vorher, punkt in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        if not punkt.eilgang and not vorher.eilgang:
            von.append((vorher.a, vorher.r, vorher.phi))
            nach.append((punkt.a, punkt.r, punkt.phi))
        elif not punkt.eilgang:
            stange.schnitt(punkt.a, punkt.r, punkt.phi, R)
    stange.fahre_stuecke(von, nach, R)
    hinter = (stange.a > -30.6) & (stange.a < -25.9)
    return float(stange.r[hinter].max() - 18.0)


ohne_ring = vb.schruppen(absatz_netz, C_LAENGS, C_RADIAL, werte_absatz)
mit_ring = vb.schruppen(
    absatz_netz,
    C_LAENGS,
    C_RADIAL,
    WERTE.__class__(**{**werte_absatz.__dict__, "waende": ((-25.0, -1),)}),
)
# Der Ring steht Fräser, Aufmaß, Vernetzung und RING_LUFT vor der Wand – so weit, dass der
# um Aufmaß und Vernetzung größere Fräser sie nicht streift; je Lage ein ganzer Umlauf.
stelle = -25.0 - (R + 0.3 + absatz_netz.toleranz + vb.RING_LUFT)
winkel = sorted(p.phi for p in schnitte(mit_ring) if abs(p.a - stelle) < 1e-9)
umlaeufe, anfang = [], None
for vorher, jetzt in zip([None, *winkel], winkel, strict=False):
    if vorher is None or jetzt - vorher > 180.0:  # eine neue Lage
        anfang = jetzt
        umlaeufe.append(0.0)
    umlaeufe[-1] = jetzt - anfang
pruefe(
    len(umlaeufe) == mit_ring.lagen and min(umlaeufe) >= 359.0 - 1e-6,
    f"Ringe bei {stelle:.3f}: {umlaeufe} ({mit_ring.lagen} Lagen)",
)
rest_ohne, rest_mit = rest_hinter_der_wand(ohne_ring), rest_hinter_der_wand(mit_ring)
pruefe(rest_ohne > 3.0, f"ohne Ring hinter der Wand nur {rest_ohne:.3f} stehen")
pruefe(rest_mit < 0.3 + 0.1, f"mit Ring hinter der Wand {rest_mit:.3f} stehen")
print(ascii(f"Wand: hinten ohne Ring {rest_ohne:.2f} mm, mit Ring {rest_mit:.2f} mm stehen"))

# --- Die Rampe (V4) ------------------------------------------------------------------------------
# Eine Bahn auf dem Radius 10, 1° je Punkt: Von 12 hinab mit 5° gegen die Bahn – 2 mm brauchen
# etwa 22 mm. Auf einem langen Stück einmal hin, auf der Bahn zurück zum Anfang; auf einem
# kurzen (10°, 1,7 mm) hin und her, immer tiefer.
steil = math.tan(math.radians(5.0))
for bis, name in ((399, "lang"), (10, "kurz")):
    lauf_a, lauf_r, lauf_phi = np.zeros(400), np.full(400, 10.0), np.arange(400) * 1.0
    rampe = vb._rampe(lauf_a, lauf_r, lauf_phi, 0, bis, 12.0, WERTE)
    stellen = [(0.0, 12.0, 0.0), *rampe]
    unten = next(i for i, s_ in enumerate(stellen) if s_[1] <= 10.0 + 1e-12)
    neigung = max(
        (v[1] - n[1]) / (max(v[1], n[1]) * math.radians(abs(n[2] - v[2])))
        for v, n in zip(stellen[:unten], stellen[1 : unten + 1], strict=True)
    )
    pruefe(neigung <= steil + 1e-9, f"Rampe {name}: {math.degrees(math.atan(neigung)):.3f}°")
    pruefe(all(0.0 <= s_[2] <= bis for s_ in stellen), f"Rampe {name}: aus dem Stück")
    pruefe(stellen[-1] == (0.0, 10.0, 0.0), f"Rampe {name}: endet bei {stellen[-1]}")
    pruefe(all(s_[1] == 10.0 for s_ in stellen[unten:]), f"Rampe {name}: zurück nicht auf der Bahn")
    wenden = sum(
        1
        for v, m, n in zip(stellen, stellen[1:], stellen[2:], strict=False)
        if (m[2] - v[2]) * (n[2] - m[2]) < 0
    )
    pruefe((wenden == 1) if name == "lang" else wenden > 3, f"Rampe {name}: {wenden} Wenden")
pruefe(vb._stuecke(np.array([False, True, True, False, True])) == [(1, 2), (4, 4)], "Stücke")

# --- Nur die Abflachung (V4) ----------------------------------------------------------------------
# Welle Ø 20 von −40 bis 0, Abflachung auf x = 8 von −30 bis −10, Stange Ø 24, Fräser R 3:
# gefräst wird nur, wo er die Abflachung berührt, in Zeilen bei festem a hin und her (Manuel:
# „man kann ja auch einfach zurück drehen für so eine Fläche“), vor ihren Wänden eine Zeile als
# Ring. Je Lage eine Fahrt: über eine Rampe hinein, am Ende jeder Zeile in der Tiefe zur
# nächsten, am Ende heraus – die Rundachse dreht nie ganz herum. Über der Abflachung bleibt das
# Aufmaß, gegenüber die Stange.
flach_welle = (
    Part.makeCylinder(10, 40, V(0, 0, -40))
    .cut(Part.makeBox(10, 30, 20, V(8, -15, -30)))
    .removeSplitter()
)
abflachung = next(
    i
    for i, f in enumerate(flach_welle.Faces)
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-6
)
sicht_flach = vf.sicht(
    vf.vernetze(flach_welle), C_LAENGS, C_RADIAL, vf.raster_a(-45.0, 5.0), vh.raster_phi()
)
bereich_flach = vf.bereich(sicht_flach, [abflachung], 3.0)
werte_flach = vb.Schruppwerte(
    fraeser_radius=3.0,
    stange_radius=12.0,
    zustellung=2.0,
    steigung=2.4,
    aufmass=0.3,
    a_stange_vorne=1.0,
    a_futter=-60.0,
    waende=((-30.0, 1), (-10.0, -1)),
    bereich=bereich_flach,
)
flach_bahn = vb.schruppen(vh.vernetze(flach_welle), C_LAENGS, C_RADIAL, werte_flach)
vorschub = schnitte(flach_bahn)
drin = bereich_flach.bei([p.a for p in vorschub], np.radians([p.phi for p in vorschub]))
pruefe(drin.all(), f"{int((~drin).sum())} Punkte im Vorschub außerhalb des Bereichs")
pruefe(flach_bahn.lagen == 2, f"Abflachung: {flach_bahn.lagen} Lagen")
rampen = senkrechte = 0
for n, punkt in enumerate(flach_bahn.punkte):
    if not punkt.eintauchen:
        continue
    folge = []
    for q in flach_bahn.punkte[n + 1 :]:
        if q.eilgang:
            break
        folge.append(q)
    # Die Rampe fährt gleich weiter und kommt auf der Bahn zum Anfang zurück; senkrecht
    # beginnt die Bahn dort, wo es hinab ging – dann nur durch Luft: Wo nichts zu fräsen ist,
    # liegt der Punkt nicht tiefer als die Lage davor.
    gleich = [abs(q.a - punkt.a) < 1e-9 and abs(q.phi - punkt.phi) < 1e-9 for q in folge]
    if bool(folge) and not gleich[0] and any(gleich[1:]):
        rampen += 1
    else:
        senkrechte += 1
        luft = flach_bahn.punkte[n - 1].r - punkt.r
        pruefe(luft <= werte_flach.sicherheit + 1e-6, f"senkrecht {luft:.3f} mm ins Material")
pruefe(
    rampen >= 1 and rampen + senkrechte == flach_bahn.lagen,
    f"{rampen} Rampen, {senkrechte} senkrecht",
)
heraus = sum(
    1
    for v, n in zip(flach_bahn.punkte, flach_bahn.punkte[1:], strict=False)
    if n.eilgang and not v.eilgang
)
pruefe(heraus == flach_bahn.lagen, f"{heraus}-mal heraus bei {flach_bahn.lagen} Lagen")
winkel_bahn = [p.phi for p in flach_bahn.punkte[1:]]
pruefe(
    max(winkel_bahn) - min(winkel_bahn) < 120.0,
    f"die Rundachse dreht von {min(winkel_bahn):.0f}° bis {max(winkel_bahn):.0f}°",
)
wenden, zuletzt = 0, 0.0  # wie oft die Rundachse im Vorschub die Richtung wechselt
for v, n in zip(vorschub, vorschub[1:], strict=False):
    dreht = n.phi - v.phi
    if abs(dreht) > 1e-9:
        wenden += zuletzt * dreht < 0
        zuletzt = dreht
pruefe(wenden >= 10, f"nur {wenden}-mal zurückgedreht")
# Vor der Wand bei −30 (sie schaut nach vorn) liegt eine Zeile als Ring: Fräser, Aufmaß,
# Vernetzung und RING_LUFT davor.
ring = -30.0 + 3.0 + 0.3 + vh.TOLERANZ + vb.RING_LUFT
pruefe(any(abs(p.a - ring) < 1e-6 for p in vorschub), f"keine Zeile als Ring bei {ring:.3f}")
stange = rm.Stange(12.0, -60.0, 1.0)
von, nach = [], []
for vorher, punkt in zip(flach_bahn.punkte, flach_bahn.punkte[1:], strict=False):
    if not punkt.eilgang:
        von.append((vorher.a, vorher.r, vorher.phi))
        nach.append((punkt.a, punkt.r, punkt.phi))
stange.fahre_stuecke(von, nach, 3.0)
winkel = np.degrees(stange.phi)
winkel = np.where(winkel > 180, winkel - 360, winkel)
nah = np.abs(winkel) <= 20
ebene = 8.0 / np.cos(np.radians(winkel[nah]))[None, :]  # die Ebene x = 8 auf dem Strahl
ueber = stange.r[np.ix_((stange.a > -28.5) & (stange.a < -11.5), nah)]
rest_flach = float((ueber - ebene).max())
pruefe(rest_flach < 0.3 + 0.2, f"über der Abflachung bleiben {rest_flach:.3f} mm")
# Dicht an den Wänden kommt nur der Rand des Fräsers hin, und seine Stirn steht schräg zur
# Ebene, wo er nicht senkrecht über ihr steht: Dort bleibt mehr – ohne Ring bis 2,3 mm, mit
# Ring gut 1 mm. Eben fräst sie erst „Plan indexiert“ (V4c).
ecke = stange.r[np.ix_((stange.a > -29.6) & (stange.a < -10.4), nah)]
rest_ecke = float((ecke - ebene).max())
pruefe(rest_ecke < 1.3, f"in den Ecken der Abflachung bleiben {rest_ecke:.3f} mm")
gegenueber = stange.r[:, np.abs(winkel) >= 120]
pruefe(float(gegenueber.min()) == 12.0, f"gegenüber abgetragen: bis {float(gegenueber.min())}")
# Nur im Gleichlauf (P-2026-10-02-26): jede Zeile für sich, mit M3 φ steigend (die Zeilen rücken
# zum Futter, dort ist das Material), dazwischen abheben; M4 andersherum. Über der Abflachung
# bleibt nicht mehr stehen als hin und her.
for gleichlauf, name in ((True, "M3"), (False, "M4")):
    einzeln = vb.schruppen(
        vh.vernetze(flach_welle),
        C_LAENGS,
        C_RADIAL,
        replace(werte_flach, nur_gleichlauf=True, gleichlauf=gleichlauf),
    )
    # Je Fahrt (zwischen zwei Eilgängen) vom Anfang zum Ende: der Winkel in einer Richtung (die
    # Rampe der ersten Zeile einer Lage fährt hin und her, am Ende steht sie wieder am Anfang).
    fahrten_e, jetzt = [], []
    for p in einzeln.punkte:
        if p.eilgang:
            if len(jetzt) > 1:
                fahrten_e.append(jetzt)
            jetzt = []
        else:
            jetzt.append(p)
    pruefe(
        len(fahrten_e) >= 2 * einzeln.lagen
        and all((f[-1].phi > f[0].phi) == gleichlauf for f in fahrten_e),
        f"{name}: Zeilen nicht alle in einer Richtung "
        f"{[round(f[-1].phi - f[0].phi, 1) for f in fahrten_e]}",
    )
    pruefe(einzeln.lagen == flach_bahn.lagen, f"{name}: {einzeln.lagen} Lagen")
print(
    ascii(
        f"Abflachung: {flach_bahn.lagen} Lagen, {rampen} Rampen, {senkrechte} senkrecht, "
        f"darüber {rest_flach:.2f} mm, in den Ecken {rest_ecke:.2f} mm"
    )
)

# --- Zwei Abflachungen gegenüber (V4): eine nach der anderen ---------------------------------
# Dieselbe Welle mit einer zweiten Abflachung auf x = −8, beide gewählt: Je Lage fräst der
# Fräser erst die eine ganz, dann die andere – heraus nur zweimal je Lage, nicht in jeder
# Zeile. Die Rampe läuft längs der ganzen Fahrt, wenn die erste Zeile kurz ist.
zwei = flach_welle.cut(Part.makeBox(10, 30, 20, V(-18, -15, -30))).removeSplitter()
beide = [
    f"Face{i + 1}"
    for i, f in enumerate(zwei.Faces)
    if vr.ist_eben(f) and abs(abs(vr.aussennormale(f).x) - 1) < 1e-6
]
pruefe(len(beide) == 2, f"zwei Abflachungen: {beide}")
zwei_bahn = vb.schruppen(
    vh.vernetze(zwei),
    C_LAENGS,
    C_RADIAL,
    replace(werte_flach, bereich=vf.bereich_fuer(zwei, C_LAENGS, C_RADIAL, beide, 3.0)),
)
heraus = sum(
    1
    for v, n in zip(zwei_bahn.punkte, zwei_bahn.punkte[1:], strict=False)
    if n.eilgang and not v.eilgang
)
pruefe(heraus == 2 * zwei_bahn.lagen, f"{heraus}-mal heraus bei {zwei_bahn.lagen} Lagen")
print(ascii(f"Zwei Abflachungen: {zwei_bahn.lagen} Lagen, {heraus}-mal heraus"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
