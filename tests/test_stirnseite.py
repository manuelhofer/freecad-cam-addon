# Prüft das Fräsen an der Stirnseite (stirnseite.py; Manuel, 2026-10-05: „immer wenn es möglich
# ist, sollte die Y-Achse benutzt werden … bis 85 % … danach muss die C-Achse arbeiten und sich
# drehen“, beide Arten wählbar). Ein Rahmen wie seine CLX550 (X ab −15, Y ±51): Was im Rahmen
# bleibt, fährt mit X und Y, C steht auf 0, die Sätze bleiben, wie sie waren. „C dreht mit“: eine
# Gerade über die Mitte hinaus fährt X, Y, C zusammen in G93, C höchstens 0,5° je Satz, jeder
# Punkt – auch zwischen den Sätzen – liegt am Teil auf der Geraden, im Rahmen. „C in Schritten“:
# ein Kreis Ø 140 – C dreht nur im Eilgang auf sicherer Höhe, im Vorschub steht es; jeder Punkt
# am Teil auf dem Kreis, im Rahmen. Eine Bohrung bei Y 70: C dreht davor. Außerhalb jeder
# Drehung: ein Satz. An der Beispiel-Drehmaschine: der Rahmen aus dem Modell (Y bis 85 % ihrer
# Grenzen, die Drehachse auf der Mitte), und die Kinematik des Prüffensters setzt die Spitze
# mit den gerechneten X, Y, C genau auf die Punkte am Teil. Ein Job mit einer Kontur Ø 140:
# Prüffenster ohne Grenze, abgefahren auf dem Kreis, das Siemens-Programm mit Y im Rahmen und C.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Path

from camaddon import beispielmaschine as bm
from camaddon import kinematik as km
from camaddon import reichweite as rw
from camaddon import stirnseite as st

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


C = Path.Command
R = st.Rahmen(-15.0, 100.0, -51.0, 51.0)


def am_teil(rahmen, befehle, dicht=1):
    """[(x, y, z)] am Teil, die Sätze im Vorschub zwischen den Endpunkten linear (X, Y, C) in
    `dicht` Schritten abgetastet – wie die Maschine sie fährt."""
    punkte, stand = [], {"X": None, "Y": None, "Z": None, "C": 0.0}
    for b in befehle:
        if b.Name not in ("G0", "G1"):
            continue
        neu = dict(stand)
        neu.update({k: float(v) for k, v in b.Parameters.items() if k in "XYZC"})
        if None not in (stand["X"], neu["X"], stand["Y"], neu["Y"]) and b.Name == "G1":
            for k in range(1, dicht + 1):
                t = k / dicht
                x, y, z, c = (stand[a] + t * (neu[a] - stand[a]) for a in "XYZC")
                ux, uy = st.gedreht(rahmen, x, y, -c * rahmen.drehsinn)
                punkte.append((ux, uy, z, x, y, c))
        stand = neu
    return punkte


def abstand_gerade(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay)))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


# --- Im Rahmen: nur X und Y, C auf 0 ------------------------------------------------------------
innen = [
    C("G0", {"X": 10.0, "Y": 0.0, "Z": 5.0}),
    C("G1", {"Z": 0.0, "F": 10.0}),
    C("G1", {"X": 40.0, "Y": 30.0}),
    C("G1", {"X": -10.0, "Y": -40.0}),
    C("G0", {"Z": 5.0}),
]
raus = st.befehle(innen, R, st.MIT)
namen = [b.Name for b in raus]
pruefe("G93" not in namen, f"im Rahmen G93: {namen}")
pruefe(raus[0].Parameters.get("C") == 0.0, f"C steht nicht auf 0: {raus[0].Parameters}")
pruefe(
    [b.Parameters.get("X") for b in raus if b.Name == "G1"][1:] == [40.0, -10.0]
    and not any("C" in b.Parameters for b in raus[1:]),
    f"im Rahmen verändert: {[(b.Name, b.Parameters) for b in raus]}",
)

# --- C dreht mit: eine Gerade über X −15 hinaus ------------------------------------------------
gerade = [
    C("G0", {"X": 30.0, "Y": 0.0, "Z": 2.0}),
    C("G1", {"Z": 0.0, "F": 10.0}),
    C("G1", {"X": -40.0, "Y": 0.0}),
    C("G1", {"X": -40.0, "Y": 20.0}),
    C("G0", {"Z": 5.0}),
]
raus = st.befehle(gerade, R, st.MIT)
namen = [b.Name for b in raus]
pruefe("G93" in namen and namen.index("G93") < len(namen) - 1 and "G94" in namen, f"G93: {namen}")
punkte = am_teil(R, raus, dicht=10)
weit = max(
    min(abstand_gerade(p, (30, 0), (-40, 0)), abstand_gerade(p, (-40, 0), (-40, 20)))
    for p in punkte
)
pruefe(weit < 0.005, f"mit: {weit:.4f} mm neben der Bahn")
pruefe(all(R.enthaelt(p[3], p[4]) for p in punkte), "mit: außerhalb des Rahmens")
c_werte = [float(b.Parameters["C"]) for b in raus if "C" in b.Parameters]
pruefe(
    max(abs(a - b) for a, b in zip(c_werte, c_werte[1:], strict=False)) <= 0.5 + 1e-6,
    f"mit: C springt {max(abs(a - b) for a, b in zip(c_werte, c_werte[1:], strict=False)):.3f}°",
)
ende = punkte[-1]
pruefe(abs(ende[0] + 40) < 1e-6 and abs(ende[1] - 20) < 1e-6, f"mit: Ende {ende[:2]}")

# --- Durch die Drehmitte, X nicht dahinter (x_min 0): C dreht dort um 180°, wenigstens so langsam
# wie auf 1 mm Radius – am Teil weiter auf der Geraden.
null = st.Rahmen(0.0, 100.0, -51.0, 51.0)
quer = [
    C("G0", {"X": 20.0, "Y": 0.0, "Z": 2.0}),
    C("G1", {"Z": 0.0, "F": 10.0}),
    C("G1", {"X": -20.0, "Y": 0.0}),
]
raus = st.befehle(quer, null, st.MIT)
punkte = am_teil(null, raus, dicht=20)
weit = max(abstand_gerade(p, (20, 0), (-20, 0)) for p in punkte)
pruefe(weit < 0.005, f"Mitte: {weit:.4f} mm neben der Geraden")
pruefe(all(null.enthaelt(p[3], p[4]) for p in punkte), "Mitte: außerhalb des Rahmens")
stand_c, dreh = 0.0, []
for b_ in raus:
    if b_.Name == "G1" and "C" in b_.Parameters and "F" in b_.Parameters:
        delta = abs(float(b_.Parameters["C"]) - stand_c)
        zeit = 1.0 / (float(b_.Parameters["F"]) * 60.0)  # min
        dreh.append((delta, zeit))
        stand_c = float(b_.Parameters["C"])
gross = [(d, z) for d, z in dreh if d > 10.0]
pruefe(
    gross and all(z >= 1.0 * math.radians(d) / (10.0 * 60.0) - 1e-9 for d, z in gross),
    f"Mitte: C {[round(d, 1) for d, _ in gross]}° in {[round(z * 60000, 1) for _, z in gross]} ms",
)

# --- C in Schritten: ein Kreis Ø 140 ---------------------------------------------------------
kreis = [
    C("G0", {"X": 70.0, "Y": 0.0, "Z": 5.0}),
    C("G1", {"Z": -1.0, "F": 10.0}),
    C("G3", {"X": -70.0, "Y": 0.0, "Z": -1.0, "I": -70.0, "J": 0.0}),
    C("G3", {"X": 70.0, "Y": 0.0, "Z": -1.0, "I": 70.0, "J": 0.0}),
    C("G0", {"Z": 5.0}),
]
raus = st.befehle(kreis, R, st.SCHRITTE, sicher_z=5.0)
stand_z = None
dreht_im_vorschub = []
dreht_unten = []
for b in raus:
    if "Z" in b.Parameters:
        stand_z = float(b.Parameters["Z"])
    if "C" in b.Parameters and b.Name != "G0":
        dreht_im_vorschub.append(b)
    if "C" in b.Parameters and b.Name == "G0" and stand_z is not None and stand_z < 5.0 - 1e-9:
        dreht_unten.append(b)
pruefe(not dreht_im_vorschub, f"Schritte: C dreht im Vorschub: {dreht_im_vorschub[:2]}")
pruefe(not dreht_unten, f"Schritte: C dreht unten: {dreht_unten[:2]}")
punkte = [p for p in am_teil(R, raus, dicht=4) if p[2] < 0]
pruefe(
    punkte and max(abs(math.hypot(p[0], p[1]) - 70.0) for p in punkte) < 0.01,
    f"Schritte: neben dem Kreis {max(abs(math.hypot(p[0], p[1]) - 70.0) for p in punkte):.4f}",
)
pruefe(all(R.enthaelt(p[3], p[4]) for p in punkte), "Schritte: außerhalb des Rahmens")
winkel = [math.degrees(math.atan2(p[1], p[0])) % 360 for p in punkte]
pruefe(
    max(winkel) - min(winkel) > 350, f"Schritte: nicht rundum {min(winkel):.0f}…{max(winkel):.0f}"
)
drehungen = sum(1 for b in raus if b.Name == "G0" and "C" in b.Parameters)
print(ascii(f"Kreis in Schritten: {drehungen} Drehungen, {len(raus)} Saetze"))

# --- Bohrung bei Y 70 ---------------------------------------------------------------------------
bohren = [
    C("G0", {"X": 0.0, "Y": 0.0, "Z": 5.0}),
    C("G81", {"X": 0.0, "Y": 70.0, "Z": -5.0, "R": 2.0, "F": 2.0}),
    C("G80"),
]
raus = st.befehle(bohren, R, st.MIT)
zyklus = next(b for b in raus if b.Name == "G81")
davor = raus[raus.index(zyklus) - 1]
x, y = zyklus.Parameters["X"], zyklus.Parameters["Y"]
c = float(davor.Parameters.get("C", 0.0))
ux, uy = st.gedreht(R, x, y, -c)
pruefe(
    davor.Name == "G0" and R.enthaelt(x, y) and abs(ux) < 1e-6 and abs(uy - 70) < 1e-6,
    f"Bohrung: {davor} {zyklus}",
)

# --- Nicht erreichbar ---------------------------------------------------------------------------
try:
    st.befehle([C("G0", {"X": 150.0, "Y": 0.0, "Z": 5.0})], R, st.MIT)
    pruefe(False, "X 150 erreichbar?")
except ValueError:
    pass

# --- Die Beispiel-Drehmaschine: Rahmen aus dem Modell, Kinematik des Prüffensters ------------
asm, ma = bm.drehmaschine()
p = rw.Pruefung(asm, ma)
aufnahme = p.werkzeugaufnahme(1)
rahmen = st.rahmen(p, aufnahme, 100.0)
y_achse = next(a for a in p.kette.achsen if a.art == "linear" and "Y" in a.gelenk.Label.upper())
print(
    ascii(f"Rahmen der Beispiel-Drehmaschine: {rahmen}, Y1 {y_achse.minimum} … {y_achse.maximum}")
)
pruefe(rahmen is not None, "kein Rahmen an der Drehmaschine")
if rahmen is not None:
    pruefe(
        math.hypot(*rahmen.mitte) < 1e-6
        and abs(rahmen.y_max - 0.85 * y_achse.maximum) < 1e-6
        and abs(rahmen.y_min - 0.85 * y_achse.minimum) < 1e-6,
        f"Rahmen: {rahmen}",
    )
    # „Y an der Stirnseite nutzen bis“ 50 %: der Rahmen halb so breit wie der Weg.
    from camaddon import maschine as m

    y_ba = next(
        b for b in m.betriebsarten(ma) if b.Art == m.ART_LINEAR and m.programmname(b) == "Y"
    )
    pruefe(y_ba.YNutzen == 85.0, f"YNutzen vorbelegt {y_ba.YNutzen}")
    y_ba.YNutzen = 50.0
    halb = st.rahmen(p, aufnahme, 100.0)
    pruefe(abs(halb.y_max - 0.5 * y_achse.maximum) < 1e-6, f"50 %: {halb}")
    y_ba.YNutzen = 85.0
    k = km.Kinematik(p, aufnahme, 100.0, FreeCAD.Vector())
    weit = [C("G0", {"X": 20.0, "Y": 0.0, "Z": 2.0}), C("G1", {"Z": 0.0, "F": 10.0})]
    weit.append(C("G1", {"X": -2.0 * rahmen.y_max, "Y": 0.0}))
    for modus in st.MODI:
        raus = st.befehle(weit, rahmen, modus, sicher_z=2.0)
        daneben = 0.0
        for q in am_teil(rahmen, raus):
            stellungen = k.stellungen((q[3], q[4], q[2]), {"C": q[5]})
            if stellungen is None:
                daneben = math.inf
                break
            ist = k.am_werkstueck(stellungen)
            daneben = max(daneben, math.dist(ist[:2], q[:2]))
        pruefe(daneben < 1e-6, f"{modus}: Kinematik setzt die Spitze {daneben} mm daneben")

# Ein Job an der Drehmaschine: eine Kontur Ø 140 an der Stirn (weit über Y ±51) – das Prüffenster
# fährt sie ohne Grenze, die Spitze am Teil auf dem 72-Eck der Bahn; das Siemens-Programm hält Y im Rahmen
# und schaltet C ein.
import Part  # noqa: E402
import Path.Main.Job as PathJob  # noqa: E402
import Path.Op.Custom as PathCustom  # noqa: E402

from camaddon import abfahren as ab  # noqa: E402
from camaddon import postprozessor as pp  # noqa: E402

doc = FreeCAD.newDocument("Stirn")
scheibe = doc.addObject("Part::Feature", "Scheibe")
scheibe.Shape = Part.makeCylinder(75.0, 20.0, FreeCAD.Vector(0, 0, -20))
doc.recompute()
job = PathJob.Create("Job", [scheibe])
op = PathCustom.Create("Kontur")
zeilen = ["G0 X70 Y0 Z5", "G1 Z-1 F10"]
for k in range(1, 73):
    w = math.radians(5.0 * k)
    zeilen.append(f"G1 X{70 * math.cos(w):.4f} Y{70 * math.sin(w):.4f}")
zeilen.append("G0 Z5")
op.Gcode = zeilen
doc.recompute()
nullpunkt = rw.nullpunkt(job)
for modus in st.MODI:
    st.setze_modus(job, modus)
    e = p.pruefe_job(job, nullpunkt)
    pruefe(not e.ueberschreitungen, f"{modus}: {[u.text() for u in e.ueberschreitungen][:2]}")
    fahrt = ab.abfahrt(p, job, nullpunkt)
    am = [
        q
        for q, station in zip(fahrt.am_werkstueck(), fahrt.stationen, strict=True)
        if not station.eilgang and q[2] < -0.5
    ]
    ecken = [
        (70 * math.cos(math.radians(5.0 * k)), 70 * math.sin(math.radians(5.0 * k)))
        for k in range(73)
    ]
    daneben = (
        max(
            min(abstand_gerade(q, e0, e1) for e0, e1 in zip(ecken, ecken[1:], strict=False))
            for q in am
        )
        if am
        else math.inf
    )
    pruefe(len(am) > 50 and daneben < 0.01, f"{modus}: {len(am)} Stellen, {daneben:.4f} daneben")
    info = pp.maschineninfo_dokument(asm.Document)
    programm = pp.programm(pp.abschnitte(job), pp.steuerung("siemens"), info, "Stirn").zeilen
    y_werte = [float(w[1:]) for z in programm for w in z.split() if w.startswith("Y")]
    pruefe(
        info.stirn is not None
        and max(abs(y) for y in y_werte) <= 51.0005
        and any("C" in z and "=" in z for z in programm if z.startswith("G"))
        and any(z.startswith("SPOS") for z in programm),
        f"{modus}: Programm Y bis {max(abs(y) for y in y_werte):.3f}, {programm[:30]}",
    )
    # Gelesen wie eine Steuerung nach DIN 66217 (+C: das Werkzeug dreht gegenüber dem Werkstück
    # rechtsherum um +Z): X im Durchmesser, C mit ACP/ACN – am Teil auf dem 72-Eck.
    stand = {"X": None, "Y": 0.0, "Z": None, "C": 0.0}
    am_teil_din = []
    for z in programm:
        if not z.startswith(("G0", "G1")):
            continue
        for w in z.split()[1:]:
            if w[0] in "XYZ" and w[1:2] in "-.0123456789":
                stand[w[0]] = float(w[1:])
            elif w.startswith("C") and "=AC" in w:
                ziel = float(w.split("(")[1].rstrip(")"))
                d = (ziel - stand["C"]) % 360.0 if "ACP" in w else -((stand["C"] - ziel) % 360.0)
                stand["C"] += 0.0 if abs(d) > 359.9995 else d
        if z.startswith("G1") and None not in (stand["X"], stand["Z"]) and stand["Z"] < -0.5:
            gx, gy = stand["X"] / 2.0, stand["Y"]
            c, s_ = math.cos(math.radians(stand["C"])), math.sin(math.radians(stand["C"]))
            am_teil_din.append((c * gx - s_ * gy, s_ * gx + c * gy))
    weit_din = max(
        min(abstand_gerade(q, e0, e1) for e0, e1 in zip(ecken, ecken[1:], strict=False))
        for q in am_teil_din
    )
    pruefe(
        len(am_teil_din) > 20 and weit_din < 0.01,
        f"{modus}: nach DIN gelesen {weit_din:.4f} mm neben der Bahn",
    )
    print(ascii(f"{modus}: {len(programm)} Zeilen, Y bis {max(abs(y) for y in y_werte):.2f}"))
FreeCAD.closeDocument(doc.Name)
FreeCAD.closeDocument(asm.Document.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
