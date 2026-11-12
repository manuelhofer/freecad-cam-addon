# SPDX-License-Identifier: LGPL-2.1-or-later
# Kurze Geraden zu Bögen und längeren Geraden fassen (bogenfit, Haken „boegen“ im Postprozessor):
# Ein Kreis aus 0,5-mm-Geraden wird wenige Bögen, eine Gerade aus vielen Stücken ein Satz, ein
# Ring mit runden Ecken vier Geraden und vier Bögen – immer höchstens die Toleranz neben der alten
# Bahn (unabhängig nachgemessen). Eine Kette, die zurückläuft, eine Rampe und eine Ecke bleiben.
# Die Mitte eines Bogens passt zu den gerundeten Zahlen des Programms (Kreisendpunkt). In den
# Befehlen einer Operation: nur Ketten von G1 mit gleichem Vorschub; Eilgänge, Bögen, Kommentare,
# Zyklen, Rundachsen bleiben. Im Programm: mit Haken G2/G3, ohne Haken Satz für Satz, nachgelesen
# ohne Befund, im Klartext CC und C.
# Ausführen: freecadcmd tests/test_bogenfit.py

import math
import os
import random
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import numpy as np
import Path

from camaddon import bogenfit as bf
from camaddon import postprozessor as pp
from camaddon import sprache

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
C = Path.Command
TOL = bf.TOLERANZ


def kreis(mx, my, r, von, bis, schritt=0.5, z=0.0):
    n = max(2, int(abs(bis - von) * r / schritt))
    return [(mx + r * math.cos(w), my + r * math.sin(w), z) for w in np.linspace(von, bis, n + 1)]


def dicht(punkte, stuecke, schritt=0.002):
    """Die neue Bahn dicht abgetastet: [(x, y, z)]."""
    neu = [punkte[0]]
    vorher = 0
    for index, bogen in stuecke:
        a, b = np.array(punkte[vorher]), np.array(punkte[index])
        if bogen is None:
            n = max(1, int(np.linalg.norm(b - a) / schritt))
            neu.extend(tuple(a + (b - a) * k / n) for k in range(1, n + 1))
        else:
            mx, my, uhr = bogen
            a0 = math.atan2(a[1] - my, a[0] - mx)
            a1 = math.atan2(b[1] - my, b[0] - mx)
            if uhr:
                while a1 >= a0:
                    a1 -= 2 * math.pi
            else:
                while a1 <= a0:
                    a1 += 2 * math.pi
            r0, r1 = math.hypot(a[0] - mx, a[1] - my), math.hypot(b[0] - mx, b[1] - my)
            n = max(2, int(abs(a1 - a0) * r0 / schritt))
            for k in range(1, n + 1):
                t = k / n
                w, r = a0 + t * (a1 - a0), r0 + t * (r1 - r0)
                neu.append((mx + r * math.cos(w), my + r * math.sin(w), a[2] + t * (b[2] - a[2])))
        vorher = index
    return neu


def abstand(q, p):
    """Der größte Abstand der Punkte q zur Kette p (mm)."""
    q, p = np.asarray(q, dtype=float), np.asarray(p, dtype=float)
    a, d = p[:-1], p[1:] - p[:-1]
    l2 = np.maximum(np.einsum("ij,ij->i", d, d), 1e-18)
    beste = np.full(len(q), np.inf)
    for k in range(len(a)):
        t = np.clip(((q - a[k]) @ d[k]) / l2[k], 0.0, 1.0)
        lot = q - (a[k] + np.outer(t, d[k]))
        beste = np.minimum(beste, np.sqrt(np.einsum("ij,ij->i", lot, lot)))
    return float(beste.max())


def daneben(punkte, stuecke):
    """Wie weit die neue Bahn neben der alten liegt und die alte neben der neuen (mm)."""
    neu = dicht(punkte, stuecke)
    return max(abstand(neu, punkte), abstand(punkte, neu))


# --- Ein Dreiviertelkreis aus 0,5-mm-Geraden: wenige Bögen ------------------------------------
rund = kreis(10.0, -5.0, 20.0, 0.2, 0.2 + 1.5 * math.pi)
stuecke = bf.zusammenfassen(rund)
pruefe(len(rund) > 180, f"Kreis: nur {len(rund)} Punkte")
pruefe(
    len(stuecke) <= 3 and all(b is not None for _i, b in stuecke),
    f"Kreis: {len(stuecke)} Stücke, {sum(1 for _i, b in stuecke if b is None)} Geraden",
)
pruefe(stuecke[-1][0] == len(rund) - 1, "Kreis: der letzte Punkt fehlt")
for _i, (mx, my, uhr) in stuecke:
    pruefe(
        math.hypot(mx - 10.0, my + 5.0) < 0.02 and not uhr, f"Kreis: Mitte {mx:.3f} {my:.3f} {uhr}"
    )
pruefe(daneben(rund, stuecke) <= TOL + 0.0015, f"Kreis: {daneben(rund, stuecke):.4f} mm daneben")
# Andersherum: im Uhrzeigersinn.
zurueck = bf.zusammenfassen(rund[::-1])
pruefe(all(b is not None and b[2] for _i, b in zurueck), f"Uhrzeigersinn: {zurueck}")

# --- Eine Gerade aus vielen Stücken, die Punkte bis 0,002 daneben: ein Satz ---------------------
random.seed(4)
gerade = [(0.5 * k, 0.3 * k + random.uniform(-0.002, 0.002), 1.0) for k in range(200)]
stuecke = bf.zusammenfassen(gerade)
pruefe(stuecke == [(199, None)], f"Gerade: {stuecke}")
# … im Raum (eine Rampe): auch ein Satz, kein Bogen.
rampe = [(0.5 * k, 0.0, -0.01 * k) for k in range(100)]
pruefe(bf.zusammenfassen(rampe) == [(99, None)], f"Rampe: {bf.zusammenfassen(rampe)}")
# Ein Kreis, der dabei sinkt (eine Wendel in Geraden): Bögen gibt es nur auf gleicher Höhe.
wendel = [(x, y, -0.002 * k) for k, (x, y, _z) in enumerate(kreis(0.0, 0.0, 8.0, 0.0, math.pi))]
stuecke = bf.zusammenfassen(wendel)
pruefe(all(b is None for _i, b in stuecke), "Wendel: ein Bogen trotz Gefälle")
pruefe(daneben(wendel, stuecke) <= TOL + 0.0015, f"Wendel: {daneben(wendel, stuecke):.4f} daneben")

# --- Ein Ring mit runden Ecken (100 × 60, R 8): vier Geraden, vier Viertelbögen -----------------
ring = [(50.0, y, 0.0) for y in np.arange(-22.0, 22.0, 0.5)]
ring += kreis(42.0, 22.0, 8.0, 0.0, 0.5 * math.pi)
ring += [(x, 30.0, 0.0) for x in np.arange(41.5, -42.0, -0.5)]
ring += kreis(-42.0, 22.0, 8.0, 0.5 * math.pi, math.pi)
ring += [(-50.0, y, 0.0) for y in np.arange(21.5, -22.0, -0.5)]
ring += kreis(-42.0, -22.0, 8.0, math.pi, 1.5 * math.pi)
ring += [(x, -30.0, 0.0) for x in np.arange(-41.5, 42.0, 0.5)]
ring += kreis(42.0, -22.0, 8.0, 1.5 * math.pi, 2.0 * math.pi)
stuecke = bf.zusammenfassen(ring)
n_boegen = sum(1 for _i, b in stuecke if b is not None)
pruefe(len(ring) > 500, f"Ring: {len(ring)} Punkte")
pruefe(n_boegen == 4 and len(stuecke) <= 10, f"Ring: {len(stuecke)} Stücke, {n_boegen} Bögen")
pruefe(daneben(ring, stuecke) <= TOL + 0.0015, f"Ring: {daneben(ring, stuecke):.4f} mm daneben")

# --- Was bleiben muss ----------------------------------------------------------------------------
# Hin und zurück auf derselben Geraden: nicht ein Satz zum Ende.
hin_her = [(float(x), 0.0, 0.0) for x in (0, 1, 2, 3, 4, 3, 2, 1, 0, 1, 2)]
stuecke = bf.zusammenfassen(hin_her)
pruefe([i for i, _b in stuecke] == [4, 8, 10], f"hin und her: {stuecke}")
# Eine Ecke von 90°: zwei Geraden, kein Bogen.
ecke = [(0.5 * k, 0.0, 0.0) for k in range(21)] + [(10.0, 0.5 * k, 0.0) for k in range(1, 21)]
pruefe(bf.zusammenfassen(ecke) == [(20, None), (40, None)], f"Ecke: {bf.zusammenfassen(ecke)}")
# Treppen von 0,5 mm (die Zacken aus dem Raster) sind keine Rundung: sie bleiben.
treppe = []
for k in range(20):
    treppe += [(0.5 * k, 0.5 * k, 0.0), (0.5 * k + 0.5, 0.5 * k, 0.0)]
pruefe(len(bf.zusammenfassen(treppe)) == len(treppe) - 1, "Treppe geglättet")
# Zwei Punkte, einer: nichts zu tun.
pruefe(bf.zusammenfassen([(0, 0, 0), (1, 0, 0)]) == [(1, None)], "zwei Punkte")
pruefe(bf.zusammenfassen([(0, 0, 0)]) == [], "ein Punkt")
print("Ketten ok")

# --- Die Mitte passt zu den gerundeten Zahlen ----------------------------------------------------
random.seed(7)
schlimmster = einzeln = 0.0
for _ in range(4000):
    r = random.uniform(0.3, 900.0)
    mx, my = random.uniform(-200, 200), random.uniform(-200, 200)
    a0 = random.uniform(0, 2 * math.pi)
    weit = random.uniform(0.02, 1.5 * math.pi) * random.choice((-1, 1))
    if abs(weit) * r < 0.2:
        continue
    start = (mx + r * math.cos(a0), my + r * math.sin(a0))
    ende = (mx + r * math.cos(a0 + weit), my + r * math.sin(a0 + weit))
    i, j = bf.mitte_gerundet(start, ende, (mx, my))
    xs, ys, xe, ye = (round(v, 3) for v in (*start, *ende))
    pruefe(abs(i - round(i, 3)) < 1e-9 and abs(j - round(j, 3)) < 1e-9, "I/J nicht gerundet")
    schlimmster = max(schlimmster, abs(math.hypot(i, j) - math.hypot(xe - xs - i, ye - ys - j)))
    # Die Mitte bleibt, wo sie war (bis auf die Rundung und den Schub auf die Mittelsenkrechte).
    pruefe(
        math.hypot(xs + i - mx, ys + j - my) < 0.01 + 0.002 * r / max(abs(weit) * r, 1.0),
        "Mitte verschoben",
    )
    i0, j0 = round(mx - start[0], 3), round(my - start[1], 3)
    einzeln = max(einzeln, abs(math.hypot(i0, j0) - math.hypot(xe - xs - i0, ye - ys - j0)))
pruefe(schlimmster <= 0.0011, f"Kreisendpunkt: Abstände bis {schlimmster:.4f} mm verschieden")
print(f"Mitte ok (gerundet bis {schlimmster:.4f} mm, einzeln gerundet wären es bis {einzeln:.4f})")

# --- In den Befehlen einer Operation -------------------------------------------------------------
F, FREI = 15.0, 166.0
befehle = [("(Räumen)", {}), ("G0", {"Z": 5.0}), ("G0", {"X": rund[0][0], "Y": rund[0][1]})]
befehle.append(("G0", {"X": rund[0][0], "Y": rund[0][1], "Z": 0.0}))
befehle += [("G1", {"X": x, "Y": y, "Z": z, "F": F}) for x, y, z in rund[1:]]
ende_rund = rund[-1]
befehle += [
    ("G1", {"X": ende_rund[0] + 0.5 * k, "Y": ende_rund[1], "Z": 0.0, "F": FREI})
    for k in range(1, 30)
]
befehle.append(("G2", {"X": 100.0, "Y": 0.0, "Z": 0.0, "I": 5.0, "J": 0.0, "F": F}))
befehle += [("G1", {"X": 100.0 + 0.5 * k, "F": F}) for k in range(1, 30)]  # nur X: modal
befehle.append(("G0", {"Z": 5.0}))
neu = bf.befehle_gefasst(befehle)
namen = [n for n, _w in neu]
pruefe(namen[:4] == ["(Räumen)", "G0", "G0", "G0"], f"Anfang: {namen[:5]}")
pruefe(len(neu) <= 12, f"gefasst: {len(neu)} statt {len(befehle)} Befehle – {namen}")
boegen = [w for n, w in neu if n == "G3"]
pruefe(1 <= len(boegen) <= 3 and all(w["F"] == F for w in boegen), f"Bögen: {boegen}")
frei = [w for n, w in neu if n == "G1" and w.get("F") == FREI]
pruefe(
    len(frei) == 1 and abs(frei[0]["X"] - (ende_rund[0] + 14.5)) < 1e-9,
    f"der schnellere Vorschub bleibt ein eigener Satz: {frei}",
)
pruefe(namen.count("G2") == 1 and ("G2", befehle[-31][1]) in neu, "der Bogen, der schon da war")
letzte = [w for n, w in neu if n == "G1"][-1]
pruefe(
    abs(letzte["X"] - 114.5) < 1e-9 and abs(letzte["Y"]) < 1e-9 and letzte["F"] == F,
    f"modal: {letzte}",
)
pruefe(neu[-1] == ("G0", {"Z": 5.0}), f"Ende: {neu[-1]}")
# Stück für Stück: Wer nur den Anfang nimmt, bekommt denselben Anfang.
anfang = []
for befehl in bf.gefasst(befehle):
    anfang.append(befehl)
    if len(anfang) == 5:
        break
pruefe(anfang == neu[:5], "der Generator gibt einen anderen Anfang")
# Rundachsen, G91, eine andere Ebene, G93: nichts anfassen.
for stoerer in (("G1", {"X": 1.0, "A": 30.0, "F": F}), ("G91", {}), ("G18", {}), ("G93", {})):
    mit = [*befehle[:10], stoerer, *befehle[10:]]
    pruefe(bf.befehle_gefasst(mit) == mit, f"{stoerer[0]}: trotzdem gefasst")
# Nach einem Bohrzyklus ist der Ort unbekannt: erst der Eilgang mit X, Y und Z legt ihn wieder fest.
zyklus = [
    ("G0", {"X": 0.0, "Y": 0.0, "Z": 5.0}),
    ("G81", {"X": 0.0, "Y": 0.0, "Z": -5.0, "R": 2.0, "F": 2.0}),
    ("G80", {}),
    *[("G1", {"X": 0.5 * k, "F": F}) for k in range(1, 20)],
]
pruefe(bf.befehle_gefasst(zyklus) == zyklus, "nach dem Zyklus gefasst, ohne den Ort zu kennen")
# „G1 F0“ an der Stelle (FreeCADs Brennschneiden) bleibt, wie es ist.
steht = [("G0", {"X": 0.0, "Y": 0.0, "Z": 0.0}), ("G1", {"F": 0.0}), ("G1", {"X": 1.0, "F": F})]
pruefe(bf.befehle_gefasst(steht) == steht, "G1 F0 angefasst")
print("Befehle ok")

# --- Im Programm ----------------------------------------------------------------------------------
fraese = pp.Maschineninfo("Fräse", False)
ring_befehle = [C("(Ring)"), C("G0", {"X": ring[0][0], "Y": ring[0][1], "Z": 5.0})]
ring_befehle.append(C("G1", {"X": ring[0][0], "Y": ring[0][1], "Z": 0.0, "F": 5.0}))
ring_befehle += [C("G1", {"X": x, "Y": y, "Z": z, "F": F}) for x, y, z in ring[1:]]
ring_befehle.append(C("G0", {"Z": 5.0}))
abschnitt = pp.Abschnitt("Ring", 1, 8000.0, False, "Flood", ring_befehle)
for kennung in ("siemens", "fanuc", "linuxcnc", "haas", "mach", "grbl", "mazak"):
    s = pp.steuerung(kennung)
    pruefe(s.boegen, f"{kennung}: der Haken ist nicht vorbelegt")
    mit = pp.programm([abschnitt], s, fraese, "R")
    ohne = pp.programm([abschnitt], pp.steuerung(kennung, {"boegen": False}), fraese, "R")
    g23 = [
        z for z in mit.zeilen if z.lstrip("N0123456789 ").startswith(("G2 ", "G3 ", "G2X", "G3X"))
    ]
    pruefe(len(g23) == 4, f"{kennung}: {len(g23)} Bögen im Programm")
    pruefe(
        mit.saetze <= 14 and ohne.saetze >= len(ring),
        f"{kennung}: {mit.saetze} / {ohne.saetze} Sätze",
    )
    pruefe(
        not any(z.lstrip("N0123456789 ").startswith(("G2 ", "G3 ")) for z in ohne.zeilen),
        f"{kennung}: Bögen ohne Haken",
    )
    befunde = pp.nachlesen(mit, s, fraese)[0]
    pruefe(not befunde, f"{kennung}: nachgelesen {[(b.art, b.text) for b in befunde][:3]}")
# Heidenhain: Kreismitte und Kreis.
klar = pp.programm([abschnitt], pp.steuerung("heidenhain"), fraese, "R")
pruefe(
    sum(1 for z in klar.zeilen if " CC " in f" {z} ") == 4
    and sum(1 for z in klar.zeilen if " DR+" in z) == 4,
    f"Klartext: {[z for z in klar.zeilen if 'CC' in z or 'DR' in z][:6]}",
)
pruefe(not pp.nachlesen(klar, pp.steuerung("heidenhain"), fraese)[0], "Klartext nachgelesen")
# Die Vorschau zeigt denselben Anfang wie das Programm.
s = pp.steuerung("siemens")
ganz = pp.programm([abschnitt], s, fraese, "R").zeilen
vorschau = pp.programm([abschnitt], s, fraese, "R", vorschau=5).zeilen
k = next(i for i, z in enumerate(ganz) if z.startswith(("G2 ", "G3 ")))
pruefe(
    vorschau[: k + 1] == ganz[: k + 1],
    f"Vorschau: {vorschau[k - 2 : k + 2]} / {ganz[k - 2 : k + 2]}",
)
# An der Drehmaschine und mit Rundachse bleibt die Bahn Satz für Satz.
dreh = pp.programm([abschnitt], s, pp.Maschineninfo("Drehmaschine", True), "R")
pruefe(dreh.saetze >= len(ring), f"Drehmaschine: {dreh.saetze} Sätze")
print("Programm ok")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
