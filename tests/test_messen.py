# Prüft messen.py (Plan C3b): was ein Messtaster nach einem Schlichtgang misst.
# 1. Tasche 60 × 40 in einem Block, Ecken R 5, unten Rundungen R 3: Rechteck innen, Mitte (50, 40),
#    Messhöhe auf halber Wand (Oberkante 40, Boden 25 → 32,5).
# 2. Zapfen 30 × 20 auf einer Platte: Rechteck außen.
# 3. Bohrung Ø 20 und Welle Ø 16: rund, innen bzw. außen.
# 4. Soll nach einem Gang mit Aufmaß 1: Tasche 58 × 38, Bohrung 18, Zapfen 32 × 22, Welle 18.
# 5. Eine schräge Wand ergibt kein Merkmal, zwei Taschen nebeneinander auch nicht.
# 8. Die Nut: Breite quer (16, nach 0,15 Rest 15,7), längs X in Y gemessen, längs Y in X, schräg ohne
#    Zyklus, die Ringnut radial bei +X. 9. Die Zyklen je Steuerung im Programm.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402
import Part  # noqa: E402

from camaddon import messen  # noqa: E402

V = FreeCAD.Vector
fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def namen(form, bedingung):
    return [f"Face{i + 1}" for i, f in enumerate(form.Faces) if bedingung(f)]


def senkrecht_wand(f):
    if f.Surface.__class__.__name__ == "Plane":
        u0, u1, v0, v1 = f.ParameterRange
        return abs(f.normalAt((u0 + u1) / 2, (v0 + v1) / 2).z) < 1e-6
    if f.Surface.__class__.__name__ == "Cylinder":
        return abs(abs(f.Surface.Axis.z) - 1) < 1e-6
    return False


# 1. Tasche
tasche = Part.makeBox(60, 40, 15, V(20, 20, 25))
kanten = [e for e in tasche.Edges if abs(e.BoundBox.ZLength - 15) < 1e-6]
tasche = tasche.makeFillet(5, kanten)
form = Part.makeBox(100, 80, 40).cut(tasche)
boden = [
    e for e in form.Edges if abs(e.BoundBox.ZMax - 25) < 1e-6 and abs(e.BoundBox.ZMin - 25) < 1e-6
]
form = form.makeFillet(3, boden)
wahl = namen(
    form,
    lambda f: f.BoundBox.ZMin > 24.9
    and f.BoundBox.XMin >= 20 - 1e-6
    and f.BoundBox.XMax <= 80 + 1e-6
    and f.BoundBox.YMin >= 20 - 1e-6
    and f.BoundBox.YMax <= 60 + 1e-6,
)
wahl_tasche = wahl
m = messen.merkmal(form, wahl)
print(m)
pruefe(
    m is not None
    and m.art == messen.TASCHE
    and abs(m.x - 50) < 1e-6
    and abs(m.y - 40) < 1e-6
    and abs(m.laenge_x - 60) < 1e-6
    and abs(m.laenge_y - 40) < 1e-6
    and abs(m.z_mess - 32.5) < 1e-6,
    f"Tasche: {m}",
)
s = messen.soll(m, 1.0)
pruefe(abs(s.laenge_x - 58) < 1e-6 and abs(s.laenge_y - 38) < 1e-6, f"Soll Tasche: {s}")

# 2. Zapfen
zapfen = Part.makeBox(100, 80, 10).fuse(Part.makeBox(30, 20, 15, V(35, 30, 10))).removeSplitter()
wahl = namen(zapfen, lambda f: senkrecht_wand(f) and f.BoundBox.ZMin > 9.9)
m = messen.merkmal(zapfen, wahl)
pruefe(m is not None and m.art == messen.ZAPFEN and abs(m.laenge_x - 30) < 1e-6, f"Zapfen: {m}")
s = messen.soll(m, 1.0)
pruefe(abs(s.laenge_x - 32) < 1e-6 and abs(s.laenge_y - 22) < 1e-6, f"Soll Zapfen: {s}")

# 3. Bohrung und Welle
gebohrt = Part.makeBox(100, 80, 40).cut(Part.makeCylinder(10, 20, V(50, 40, 20)))
wahl = wahl_bohrung = namen(gebohrt, lambda f: f.Surface.__class__.__name__ == "Cylinder")
m = messen.merkmal(gebohrt, wahl)
pruefe(
    m is not None and m.art == messen.BOHRUNG and abs(m.durchmesser - 20) < 1e-6,
    f"Bohrung: {m}",
)
pruefe(abs(messen.soll(m, 1.0).durchmesser - 18) < 1e-6, "Soll Bohrung")
welle = Part.makeBox(100, 80, 10).fuse(Part.makeCylinder(8, 20, V(50, 40, 10))).removeSplitter()
wahl = namen(welle, lambda f: f.Surface.__class__.__name__ == "Cylinder")
m = messen.merkmal(welle, wahl)
pruefe(m is not None and m.art == messen.WELLE and abs(m.durchmesser - 16) < 1e-6, f"Welle: {m}")
pruefe(abs(messen.soll(m, 1.0).durchmesser - 18) < 1e-6, "Soll Welle")

# 5. Schräge Wand
keil = Part.makeBox(100, 80, 40).cut(
    Part.makeBox(60, 40, 15, V(20, 20, 25)).rotated(V(50, 40, 30), V(0, 0, 1), 30)
)
wahl = namen(keil, lambda f: senkrecht_wand(f) and f.BoundBox.ZMin > 24.9)
pruefe(messen.merkmal(keil, wahl) is None, "schräge Tasche als Rechteck erkannt")

# Zwei Taschen nebeneinander: kein Rechteck über beide.
zwei = Part.makeBox(100, 80, 40).cut(Part.makeBox(30, 40, 15, V(10, 20, 25)))
zwei = zwei.cut(Part.makeBox(30, 40, 15, V(60, 20, 25)))
wahl = namen(zwei, lambda f: senkrecht_wand(f) and f.BoundBox.ZMin > 24.9)
pruefe(messen.merkmal(zwei, wahl) is None, "zwei Taschen als ein Rechteck")

# 6. Die Zeile im Messstopp: geschrieben und wieder gelesen dasselbe.
from camaddon import messstopp as ms  # noqa: E402

for m in (
    messen.soll(messen.merkmal(form, wahl_tasche), 1.0),
    messen.merkmal(gebohrt, wahl_bohrung),
):
    zeile = ms.merkmal_zeile(m, 0.02)
    zurueck, toleranz = ms.merkmal_von(["(MESSSTOPP)", zeile, "M0"])
    pruefe(
        zurueck.art == m.art
        and abs(zurueck.laenge_x - m.laenge_x) < 1e-3
        and abs(zurueck.durchmesser - m.durchmesser) < 1e-3
        and abs(zurueck.z_mess - m.z_mess) < 1e-3
        and abs(toleranz - 0.02) < 1e-9,
        f"Zeile {zeile} → {zurueck}",
    )
pruefe(ms.merkmal_von(["(MESSSTOPP)", "G0 Z45.000", "M0"]) is None, "ohne Zeile ein Merkmal")
# Mit Korrektur: „KORR3“ in der Zeile; nachträglich gesetzt und wieder weg.
zeile_k = ms.merkmal_zeile(messen.merkmal(gebohrt, wahl_bohrung), 0.02, korrigieren=3)
pruefe(ms.korrektur_von([zeile_k]) == 3 and ms.merkmal_von([zeile_k]) is not None, zeile_k)


class _Op:
    Gcode = ["(MESSSTOPP)", ms.merkmal_zeile(messen.merkmal(gebohrt, wahl_bohrung), 0.02), "M0"]


op_ = _Op()
pruefe(ms.korrektur_von(op_.Gcode) is None, "ohne Korrektur KORR")
ms.korrektur_setzen(op_, 5)
pruefe(ms.korrektur_von(op_.Gcode) == 5, f"gesetzt: {op_.Gcode}")
ms.korrektur_setzen(op_, None)
pruefe(ms.korrektur_von(op_.Gcode) is None and ms.merkmal_von(op_.Gcode), f"weg: {op_.Gcode}")

# 7. Das Einrichtblatt sagt beim Messstopp, was zu messen ist (auch für das Messen von Hand).
from camaddon import einrichtblatt as eb  # noqa: E402
from camaddon import sprache  # noqa: E402

sprache.setze_sprache("de")


class Stopp:
    Gcode = [
        "(MESSSTOPP)",
        ms.merkmal_zeile(messen.soll(messen.merkmal(form, wahl_tasche), 1.0), 0.02),
        "M0",
    ]


satz = eb._messen_text(Stopp(), sprache.tr)
print(satz)
pruefe(satz.startswith("messen: Tasche 58") and "38" in satz and "±0" in satz, f"Blatt: {satz}")
Stopp.Gcode = ["(MESSSTOPP)", "M0"]
pruefe(eb._messen_text(Stopp(), sprache.tr) == "", "Blatt ohne Merkmal")

# 8. Die Nut (seit 0.381): ihre Breite quer zur Mittellinie, an einer Stelle. Eine geschlossene
#    Nut 30 × 16, 8 tief (die Mittellinie in X von x 51 bis 65, y 30): gemessen in Y in der Mitte
#    (58, 30) auf halber Wand (z 16); nach einem Gang mit 0,15 Rest 15,7, auf Maß 16.
NUT_B = 16.0


def nut_block(winkel=0.0, mitte=(58.0, 30.0)):
    """Ein Block 100 × 60 × 20 mit der Nut 30 × 16, 8 tief, um `winkel` (Grad) um ihre Mitte
    gedreht; dazu ihr Grund („Face…“) und ihre Wände."""
    mx, my = mitte
    nut = (
        Part.makeBox(14, NUT_B, 8, V(mx - 7, my - NUT_B / 2, 12))
        .fuse(Part.makeCylinder(NUT_B / 2, 8, V(mx - 7, my, 12)))
        .fuse(Part.makeCylinder(NUT_B / 2, 8, V(mx + 7, my, 12)))
    )
    if winkel:
        nut = nut.rotated(V(mx, my, 12), V(0, 0, 1), winkel)
    block = Part.makeBox(100, 60, 20).cut(nut).removeSplitter()
    grund = namen(
        block,
        lambda f: f.Surface.__class__.__name__ == "Plane" and abs(f.BoundBox.ZMax - 12) < 1e-6,
    )
    waende = namen(block, lambda f: senkrecht_wand(f) and f.BoundBox.ZMin > 11.9)
    return block, grund, waende


nut_x, grund_x, waende_x = nut_block()
for wahl, was in ((grund_x, "Grund"), (waende_x, "Wände"), (waende_x[:1], "eine Wand")):
    m = messen.merkmal(nut_x, wahl)
    pruefe(
        m is not None
        and m.art == messen.NUT
        and abs(m.breite - NUT_B) < 1e-6
        and m.achse == "Y"
        and abs(m.x - 58) < 1e-6
        and abs(m.y - 30) < 1e-6
        and abs(m.z_mess - 16) < 1e-6
        and m.innen
        and m.zyklus_moeglich,
        f"Nut in X ({was}): {m}",
    )
m_nut = messen.merkmal(nut_x, grund_x)
s_nut = messen.soll(m_nut, 0.15)
pruefe(abs(s_nut.breite - 15.7) < 1e-9 and s_nut.achse == "Y", f"Soll Nut: {s_nut}")
pruefe(abs(messen.soll(m_nut, 0.0).breite - NUT_B) < 1e-9, "Soll Nut auf Maß")
print(messen.text(s_nut))
pruefe(
    messen.text(s_nut).replace(",", ".") == "Nut 15.7 mm quer in Y",
    f"Text Nut: {messen.text(s_nut)}",
)
# Die Zeile im Messstopp hin und zurück.
zurueck, toleranz = ms.merkmal_von(["(MESSSTOPP)", ms.merkmal_zeile(s_nut, 0.02), "M0"])
pruefe(
    zurueck.art == messen.NUT
    and abs(zurueck.breite - 15.7) < 1e-6
    and zurueck.achse == "Y"
    and abs(zurueck.z_mess - 16) < 1e-6,
    f"Zeile Nut → {zurueck}",
)
# Die Nut längs Y: gemessen in X.
m_y = messen.merkmal(*nut_block(90.0)[:2])
pruefe(m_y is not None and m_y.achse == "X" and abs(m_y.breite - NUT_B) < 1e-6, f"Nut Y: {m_y}")
# Schräg (30°): ein Merkmal, aber kein Zyklus – „quer, 120° schräg“ (die Messrichtung).
m_s = messen.merkmal(*nut_block(30.0)[:2])
pruefe(
    m_s is not None
    and m_s.achse is None
    and not m_s.zyklus_moeglich
    and abs(m_s.winkel - 120) < 1e-3,
    f"schräge Nut: {m_s}",
)
pruefe("schräg" in messen.text(m_s), f"Text schräge Nut: {messen.text(m_s)}")
# Die Nut und ein Fremder in der Wahl: kein Merkmal (man mäße etwas, das nicht gewählt ist).
deckel = namen(nut_x, lambda f: abs(f.BoundBox.ZMin - 20) < 1e-6)
pruefe(messen.merkmal(nut_x, grund_x + deckel) is None, "Nut mit dem Deckel als Nut")
# Ringnut Ø 30 … Ø 50 um (40, 40), 3 tief: radial bei +X gemessen – (60, 40) in X, 10 breit.
ring = Part.makeBox(80, 80, 20).cut(
    Part.makeCylinder(25, 3, V(40, 40, 17)).cut(Part.makeCylinder(15, 3, V(40, 40, 17)))
)
grund_r = namen(
    ring, lambda f: abs(f.BoundBox.ZMax - 17) < 1e-6 and abs(f.BoundBox.ZMin - 17) < 1e-6
)
m_r = messen.nut_merkmal(ring, grund_r)
pruefe(
    m_r is not None
    and m_r.achse == "X"
    and abs(m_r.breite - 10) < 1e-6
    and abs(m_r.x - 60) < 1e-6
    and abs(m_r.y - 40) < 1e-6
    and abs(m_r.z_mess - 18.5) < 1e-6,
    f"Ringnut: {m_r}",
)

# 9. Die Zyklen je Steuerung im Programm (Handbücher: Siemens Messzyklen 06/2019 Kap. 3.3.9 und
#    4.1.7, CYCLE977 S_MVAR 3, S_MA 2 = Y, Tabelle 3-16 _OVR[16] „Differenz Nutbreite“; Heidenhain
#    TNC 640 10/2023 Kap. 6.9, Zyklus 425 wie im Beispiel; Renishaw 9812 mit Y). Ohne Taster, an
#    einer Steuerung ohne Zyklus und bei der schrägen Nut: der Halt mit dem Sollmaß.
import Path  # noqa: E402

from camaddon import postprozessor as pp  # noqa: E402

C = Path.Command
fraese = pp.Maschineninfo("Fräse")
vorher = pp.Abschnitt(
    "Nut", 2, 900.0, False, "None", [C("G0", {"X": 58.0, "Y": 30.0, "Z": 25.0})], "Fräser"
)
danach = pp.Abschnitt(
    "Nut auf Maß", 2, 900.0, False, "None", [C("G0", {"X": 58.0, "Y": 30.0, "Z": 25.0})], "Fräser"
)


def stopp_mit(m, korr=None):
    zeilen_ = ms.zeilen(25.0, 900.0)
    zeilen_.insert(1, ms.merkmal_zeile(m, 0.02, korrigieren=korr))
    return pp.Abschnitt("Messstopp", 2, 900.0, False, "None", [C(z) for z in zeilen_], "Fräser")


def programm(kennung, m, taster="99", korr=None):
    s = pp.steuerung(kennung, {"taster": taster} if taster else {})
    return [
        x.strip() for x in pp.programm([vorher, stopp_mit(m, korr), danach], s, fraese, "N").zeilen
    ]


for kennung, erwartet in (
    ("siemens", 'CYCLE977(3,,,1,15.700,,,2,1,0,,,,2,1,"",,0,0,0,0,0,1,0,,1,0)'),
    ("siemens", "IF (ABS(_OVR[16])>0.020) GOTOF MESSEN_AUS1"),
    ("siemens", "G1 Z16.000 F1000"),
    ("fanuc", "G65 P9812 Y15.700 H0.020"),
    ("haas", "G65 P9812 Y15.700 H0.020"),
    ("heidenhain", "TCH PROBE 425 MESSEN BREITE INNEN ~"),
    ("heidenhain_tnc640", "Q272=+2 ;MESSACHSE ~"),
    ("heidenhain_tnc640", "Q311=+15.700 ;SOLL-LAENGE ~"),
    ("heidenhain_tnc640", "Q288=+15.720 ;GROESSTMASS ~"),
    ("heidenhain_tnc640", "Q289=+15.680 ;KLEINSTMASS ~"),
    ("heidenhain_tnc640", "Q328=+58.000 ;STARTPUNKT 1. ACHSE ~"),
    ("heidenhain_tnc640", "Q301=+1 ;FAHREN AUF S. HOEHE"),
):
    z_k = programm(kennung, s_nut)
    pruefe(
        any(x.endswith(erwartet) for x in z_k),
        f"{kennung}: „{erwartet}“ fehlt: {[x for x in z_k if 'P98' in x or 'CYCLE' in x or 'Q' in x]}",
    )
    pruefe("M0" not in z_k or kennung == "siemens", f"{kennung}: Halt trotz Taster")
# Die Nut längs Y: in X (Siemens S_MA 1, Renishaw X, Heidenhain Q272=+1).
m_yx = messen.soll(m_y, 0.15)
pruefe(
    'CYCLE977(3,,,1,15.700,,,2,1,0,,,,1,1,"",,0,0,0,0,0,1,0,,1,0)' in programm("siemens", m_yx),
    "Siemens Nut in X",
)
pruefe("G65 P9812 X15.700 H0.020" in programm("fanuc", m_yx), "Renishaw Nut in X")
pruefe(
    any(x.endswith("Q272=+1 ;MESSACHSE ~") for x in programm("heidenhain_tnc640", m_yx)),
    "Heidenhain Nut in X",
)
# Mit Korrektur: Siemens 203 mit der Messachse, Renishaw T, Heidenhain Q330 und ±0,5.
pruefe(
    'CYCLE977(203,,1,1,15.700,,,2,1,0,,,,2,1,"2",,0,0.5,0.020,-0.020,0,1,0,,1,1)'
    in programm("siemens", s_nut, korr=2),
    f"Siemens Nut korrigieren: {[x for x in programm('siemens', s_nut, korr=2) if 'CYCLE' in x]}",
)
pruefe("G65 P9812 Y15.700 T2 U0.5" in programm("fanuc", s_nut, korr=2), "Renishaw Nut korrigieren")
z_hk = programm("heidenhain_tnc640", s_nut, korr=2)
pruefe(
    any(x.endswith("Q330=+2 ;WERKZEUG ~") for x in z_hk)
    and any(x.endswith("Q288=+16.200 ;GROESSTMASS ~") for x in z_hk),
    "Heidenhain Nut korrigieren",
)
# Ohne Taster, LinuxCNC (kein Zyklus), schräg: der Halt, die Meldung sagt das Sollmaß.
for kennung, m, taster in (
    ("siemens", s_nut, ""),
    ("linuxcnc", s_nut, "99"),
    ("siemens", messen.soll(m_s, 0.15), "99"),
    ("heidenhain_tnc640", messen.soll(m_s, 0.15), "99"),
):
    z_h = programm(kennung, m, taster)
    pruefe(
        any(x.endswith("M0") for x in z_h)
        and not any("CYCLE977" in x or "TCH PROBE" in x for x in z_h),
        f"{kennung} ({m.winkel}°, T{taster}): kein Halt oder doch ein Zyklus",
    )
    meldung = next((x for x in z_h if "Nut 15" in x and "NC" in x), "")
    # (Heidenhain schreibt am Halt keine Meldung – wie bei den anderen Merkmalen.)
    pruefe(
        meldung or kennung.startswith("heidenhain"),
        f"{kennung}: keine Meldung mit dem Sollmaß: {[x for x in z_h if 'Mess' in x]}",
    )
print(next((x for x in programm("linuxcnc", s_nut) if "Nut 15" in x), "keine Meldung"))

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
