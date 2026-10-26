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
    `dicht` Schritten abgetastet – wie die Maschine sie fährt. Ohne Y-Achse (Rahmen Y 0 bis 0)
    steht kein Y im Programm: dann Y 0."""
    ohne_y = abs(rahmen.y_min) < 1e-9 and abs(rahmen.y_max) < 1e-9
    punkte, stand = [], {"X": None, "Y": 0.0 if ohne_y else None, "Z": None, "C": 0.0}
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

# --- Ohne Y (Drehmaschine nur mit C; Manuel, 2026-10-17: „c und x achse“) ----------------------
# Der Rahmen hat Y 0 bis 0: „C dreht mit“ dreht jeden Punkt auf die X-Achse – polar mit X und C.
# Eine Nut quer, 20 mm von der Mitte (X 20, Y −10 … 10): Y bleibt 0, C dreht, jeder Punkt am Teil
# liegt auf der Geraden.
ohne_y = st.Rahmen(-15.0, 100.0, 0.0, 0.0)
nut = [
    C("G0", {"X": 20.0, "Y": -10.0, "Z": 5.0}),
    C("G1", {"Z": -1.0, "F": 10.0}),
    C("G1", {"X": 20.0, "Y": 10.0}),
    C("G0", {"Z": 5.0}),
]
polar = st.befehle(nut, ohne_y, st.MIT, programm=True)  # fürs Programm: kein Y-Wort
y_polar = [b for b in polar if "Y" in b.Parameters]
pruefe(not y_polar, f"ohne Y: {len(y_polar)} Sätze mit Y (eine Steuerung ohne Y gäbe Alarm)")
c_polar = [float(b.Parameters["C"]) for b in polar if "C" in b.Parameters]
pruefe(max(c_polar) - min(c_polar) > 50.0, f"ohne Y: C dreht nur {c_polar}")
abweichung = max(
    (
        abstand_gerade(p, (20.0, -10.0), (20.0, 10.0))
        for p in am_teil(ohne_y, polar, dicht=4)
        if p[2] < 0
    ),
    default=math.inf,
)
pruefe(abweichung < 0.01, f"ohne Y: am Teil {abweichung:.4f} mm neben der Nut")
print(ascii(f"Ohne Y: {len(polar)} Saetze, C {min(c_polar):.1f} ... {max(c_polar):.1f}"))
# Gegenleser zu P-62: Sätze, die unverändert durchgehen, solange X oder Y noch nicht bekannt sind
# (Eilgang, Gerade, Bohrzyklus), schrieben ihr Y-Wort – ohne Y-Achse auch sie ohne Y.
for erster in (
    C("G0", {"Y": 0.0, "Z": 5.0}),
    C("G1", {"Y": 0.0, "Z": 5.0, "F": 10.0}),
    C("G81", {"Y": 0.0, "Z": -2.0, "R": 2.0, "F": 10.0}),
):
    roh = st.befehle([erster, *nut], ohne_y, st.MIT, programm=True)
    mit_y = [b.toGCode() for b in roh if "Y" in b.Parameters]
    pruefe(not mit_y, f"ohne Y, erster Satz {erster.Name}: {mit_y}")
    vorn = st.befehle([erster], ohne_y, st.MIT)  # Prüfung und Abfahren: Y bleibt
    pruefe("Y" in vorn[-1].Parameters, f"ohne Y, Prüfung: {[b.toGCode() for b in vorn]}")

# Gegenleser zu P-50 (P-2026-10-18-59): „C in Schritten“ ohne Y drehte endlos (jede Stelle neben
# der Mittellinie lag außerhalb) – jetzt wie „C dreht mit“. Und eine Nut durch die Mitte, X ab −5:
# Am Radius 5 muss C um 180° umschlagen; im selben Satz zog die Spitze eine Schleife bis 1,8 mm
# neben die Nut – jetzt hoch, drehen, an derselben Stelle wieder hinunter.
import time  # noqa: E402

beginn = time.time()
schritte_0 = st.befehle(
    [C("G0", {"X": 20.0, "Y": 5.0, "Z": 5.0}), C("G1", {"Z": -1.0, "F": 10.0}),
     C("G1", {"X": 10.0, "Y": 5.0}), C("G0", {"Z": 5.0})],
    st.Rahmen(-2.0, 100.0, 0.0, 0.0), st.SCHRITTE, sicher_z=5.0,
)  # fmt: skip
pruefe(time.time() - beginn < 5.0 and len(schritte_0) < 2000, f"Schritte ohne Y: {len(schritte_0)}")
mitte_5 = st.Rahmen(-5.0, 100.0, 0.0, 0.0)
quer = [
    C("G0", {"X": -10.0, "Y": 0.0, "Z": 5.0}),
    C("G1", {"Z": -1.0, "F": 10.0}),
    C("G1", {"X": 10.0, "Y": 0.0}),
    C("G0", {"Z": 5.0}),
]
quer_raus = st.befehle(quer, mitte_5, st.MIT, sicher_z=5.0)
am_quer = [q for q in am_teil(mitte_5, quer_raus, dicht=8) if q[2] < 0]
neben = max((abs(q[1]) for q in am_quer), default=math.inf)
hoch = sum(1 for b in quer_raus if b.Name == "G0" and set(b.Parameters) == {"Z"})
pruefe(neben < 0.01 and hoch == 1, f"Nut durch die Mitte: {neben:.3f} mm daneben, {hoch}× hoch")
print(ascii(f"Umschlag: {neben:.4f} mm neben der Nut, {hoch} x hoch, {len(quer_raus)} Saetze"))

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
    # TRANSMIT (Manuel, 2026-10-26: die CLX550 hat es): die Bahn in X und Y wie im Job (X im
    # Radius, DIAMOF), kein C in den Sätzen der Stirn, davor SPOS, TRANSMIT, G17, danach TRAFOOF,
    # G18, DIAMON – am Teil direkt auf dem 72-Eck, und kürzer.
    mit_t = pp.programm(
        pp.abschnitte(job), pp.steuerung("siemens", {"transmit": True}), info, "Stirn"
    ).zeilen
    k_ein = mit_t.index("TRANSMIT") if "TRANSMIT" in mit_t else -1
    k_aus = mit_t.index("TRAFOOF") if "TRAFOOF" in mit_t else -1
    innen = mit_t[k_ein + 1 : k_aus]
    pruefe(
        0 < k_ein < k_aus
        and mit_t[k_ein - 1] == "DIAMOF"
        and mit_t[k_ein + 1] == "G17"
        and mit_t[k_aus + 1 : k_aus + 3] == ["G18", "DIAMON"]
        and any(z.startswith("SPOS") for z in mit_t[:k_ein])
        and not any("C" in w and "=" in w for z in innen for w in z.split()),
        f"{modus} TRANSMIT: {mit_t[max(0, k_ein - 6) : k_ein + 4]} … {mit_t[k_aus - 2 : k_aus + 4]}",
    )
    stand_t = {"X": None, "Y": None, "Z": None}
    am_t = []
    for z in innen:
        for w in z.split()[1:] if z.startswith(("G0", "G1")) else []:
            if w[0] in "XYZ" and w[1:2] in "-.0123456789":
                stand_t[w[0]] = float(w[1:])
        if z.startswith("G1") and None not in stand_t.values() and stand_t["Z"] < -0.5:
            am_t.append((stand_t["X"], stand_t["Y"]))
    weit_t = max(
        (
            min(abstand_gerade(q, e0, e1) for e0, e1 in zip(ecken, ecken[1:], strict=False))
            for q in am_t
        ),
        default=math.inf,
    )
    pruefe(
        len(am_t) > 20 and weit_t < 0.01 and len(mit_t) < len(programm),
        f"{modus} TRANSMIT: {len(am_t)} Stellen, {weit_t:.4f} mm daneben, {len(mit_t)} statt {len(programm)} Zeilen",
    )  # fmt: skip
    befunde_t = pp.nachlesen(
        pp.programm(pp.abschnitte(job), pp.steuerung("siemens", {"transmit": True}), info, "S"),
        pp.steuerung("siemens", {"transmit": True}),
        info,
    )[0]
    befunde_t = [b for b in befunde_t if b.art != "spindel"]  # die Operation hier ohne Drehzahl
    pruefe(
        not befunde_t, f"{modus} TRANSMIT nachgelesen: {[(b.art, b.satz) for b in befunde_t[:3]]}"
    )
    print(ascii(f"{modus} TRANSMIT: {len(mit_t)} statt {len(programm)} Zeilen"))

# --- Die Beispiel-Drehmaschine ohne Y (P-2026-10-18-56; Manuel: „es geht um alle Maschinen“) ----
# Der Y-Schlitten steht fest: keine Y-Achse in Kette und Betriebsarten, der Rahmen Y 0 bis 0. Die
# Kontur Ø 140 fährt polar mit X und C – ohne Grenze, am Teil auf dem 72-Eck, im Programm kein Y
# außer 0.
from camaddon import maschine as m  # noqa: E402

asm_0, ma_0 = bm.drehmaschine(bm.DrehmaschinenMasse(mit_y=False))
pruefe(
    not any(m.programmname(b) == "Y" for b in m.betriebsarten(ma_0)),
    "ohne Y: eine Betriebsart Y",
)
p_0 = rw.Pruefung(asm_0, ma_0)
rahmen_0 = st.rahmen(p_0, p_0.werkzeugaufnahme(1), 100.0)
pruefe(
    rahmen_0 is not None and abs(rahmen_0.y_min) < 1e-6 and abs(rahmen_0.y_max) < 1e-6,
    f"ohne Y: Rahmen {rahmen_0}",
)
st.setze_modus(job, st.MIT)
e_0 = p_0.pruefe_job(job, rw.nullpunkt(job))
pruefe(not e_0.ueberschreitungen, f"ohne Y: {[u.text() for u in e_0.ueberschreitungen][:2]}")
fahrt_0 = ab.abfahrt(p_0, job, rw.nullpunkt(job))
am_0 = [
    q
    for q, station in zip(fahrt_0.am_werkstueck(), fahrt_0.stationen, strict=True)
    if not station.eilgang and q[2] < -0.5
]
daneben_0 = (
    max(
        min(abstand_gerade(q, e0, e1) for e0, e1 in zip(ecken, ecken[1:], strict=False))
        for q in am_0
    )
    if am_0
    else math.inf
)
pruefe(len(am_0) > 50 and daneben_0 < 0.01, f"ohne Y: {len(am_0)} Stellen, {daneben_0:.4f} daneben")
info_0 = pp.maschineninfo_dokument(asm_0.Document)
programm_0 = pp.programm(pp.abschnitte(job), pp.steuerung("siemens"), info_0, "Stirn").zeilen
y_0 = [float(w[1:]) for z in programm_0 for w in z.split() if w.startswith("Y")]
c_0 = [z for z in programm_0 if " C" in z or z.startswith("C")]
pruefe(
    not y_0 and len(c_0) > 50,
    f"ohne Y: Y {y_0[:5]}, C {len(c_0)}",
)
print(ascii(f"Ohne Y an der Beispiel-Drehmaschine: {len(am_0)} Stellen, {daneben_0:.4f} daneben"))
FreeCAD.closeDocument(asm_0.Document.Name)

FreeCAD.closeDocument(doc.Name)
FreeCAD.closeDocument(asm.Document.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
