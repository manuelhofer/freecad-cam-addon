# Prüft die Schruppbahn rundum (W-003 Stufe V3b): Welle Ø 60 in der Stange Ø 80 –
# fünf Lagen bis Ø 60,6, die Spirale von vorne bis 1 mm vor das Futter, nie näher ans
# Teil als das Aufmaß; beim Exzenter auch zwischen den Punkten gegen die Formel. Dazu
# die Path-Befehle für C und A mit G93 und die Fälle, die nicht gehen.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import vierachs_bahn as vb
from camaddon import vierachs_huelle as vh

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
R = 6.0
C_LAENGS, C_RADIAL = (0, 0, 1), (1, 0, 0)
# Teil von a = −100 bis 0, Planaufmaß 1, Abstich 3: Stange vorne bei 1, Futter bei −103.
WERTE = vb.Schruppwerte(
    fraeser_radius=R,
    stange_radius=40.0,
    zustellung=2.0,
    steigung=4.8,
    aufmass=0.3,
    a_stange_vorne=1.0,
    a_futter=-103.0,
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
# Längs: von vorne bis zum Rand des Fräsers 1 mm vor dem Futter.
pruefe(min(p.a for p in bahn.punkte) == -103.0 + 1.0 + R, "hinteres Ende")
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
# Nur 0,5 mm Abstich: Der Fräser bleibt 1 mm vor dem Futter – die letzten 0,5 mm fehlen.
knapp = vb.schruppen(
    welle, C_LAENGS, C_RADIAL, WERTE.__class__(**{**WERTE.__dict__, "a_futter": -100.5})
)
pruefe(
    [s for s, _w in knapp.hinweise] == ["vb.hinten_frei"]
    and abs(knapp.hinweise[0][1]["laenge"] - 0.5) < 1e-9,
    f"Hinweise: {knapp.hinweise}",
)
pruefe(bahn.hinweise == [], f"Exzenter mit Hinweisen: {bahn.hinweise}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
