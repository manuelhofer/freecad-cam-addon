# Prüft die Schruppbahn rundum (W-003 Stufe V3b): Welle Ø 60 in der Stange Ø 80 –
# fünf Lagen bis Ø 60,6, die Spirale von vorne bis 6,5 mm hinter das Teil (Überlauf,
# V3f), dort auf der Tiefe der letzten Kontur, nie näher ans Teil als das Aufmaß; ist
# das Futter näher, bleibt der Rand des Fräsers den Abstand zum Futter davor. Beim
# Exzenter auch zwischen den Punkten gegen die Formel. Dazu die Path-Befehle für C und A
# mit G93 und die Fälle, die nicht gehen.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import vierachs_bahn as vb
from camaddon import vierachs_huelle as vh
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
# Ohne Teil darunter reicht die Lage bis an die Sperre (Fräserradius), nicht weiter.
pruefe(min(p.r for p in schnitte(bahn)) >= R, "näher an die Achse als der Fräserradius")

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
pruefe(abs(hinein["F"] * 60 - 1500 / 4) < 1e-9, f"F hinein: {hinein}")
weg = math.hypot(4.8, 38.0 * 2 * math.pi)
pruefe(
    abs(spirale["F"] * 60 - 1500 / weg) < 1e-9
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

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
