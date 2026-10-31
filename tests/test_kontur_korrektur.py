# Prüft die Kontur mit Radiuskorrektur der Steuerung (Plan C3b Stufe 2; Manuel, 2026-10-31: „1.b“ –
# Konturprogrammierung): Der Schlichtkreis trägt je Satz die Kontur des Teils als Notiz
# (kontur_bahn._korrektur), der Postprozessor schreibt ihn mit G41/G42.
# 1. Tasche 60 × 40, Ecken R 5 (kleiner als der Fräser Ø 12): Die Kontur ist das scharfe Rechteck –
#    jeder Punkt auf einer Wandgeraden, die Ecken genau auf den gedachten Ecken; kein Bogen.
# 2. Ecken R 10: die Ecken Bögen R 10 um die Mitten der Rundungen.
# 3. Die Bahn selbst (die Mitte) ist mit und ohne Korrektur dieselbe.
# 4. Der Postprozessor (LinuxCNC): „G41“, die Fahrt auf den ersten Konturpunkt, die Kontur, „G40“,
#    keine Bögen des Ein- und Ausfahrens; GRBL (ohne Korrektur): die Mitte, keine Notizen.
import math
import os
import pathlib
import re
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402
import Part  # noqa: E402
import Path.Main.Job as PathJob  # noqa: E402
from Path.Tool.camassets import user_asset_store  # noqa: E402

from camaddon import fraeserform as ff  # noqa: E402
from camaddon import kontur as ko  # noqa: E402
from camaddon import sprache  # noqa: E402
from camaddon import werkzeuge as wz  # noqa: E402

V = FreeCAD.Vector
fehler = []
sprache.setze_sprache("de")


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def tasche(ecke):
    koerper = Part.makeBox(60, 40, 15, V(20, 20, 25))
    kanten = [e for e in koerper.Edges if abs(e.BoundBox.ZLength - 15) < 1e-6]
    koerper = koerper.makeFillet(ecke, kanten)
    teil = Part.makeBox(100, 80, 40).cut(koerper)
    waende = [
        f"Face{i + 1}"
        for i, f in enumerate(teil.Faces)
        if f.BoundBox.ZMin > 24.9
        and f.BoundBox.ZLength > 1
        and f.BoundBox.XMin >= 20 - 1e-6
        and f.BoundBox.XMax <= 80 + 1e-6
    ]
    return teil, waende


t1 = wz.standardwerkzeug()
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
form = ff.von_werkzeug(t1)
r = float(form.radius)


def bahn(teil, waende, korrektur):
    doc = FreeCAD.newDocument("Korrektur")
    objekt = doc.addObject("Part::Feature", "Teil")
    objekt.Shape = teil
    doc.recompute()
    job = PathJob.Create("Job", [objekt])
    job.Stock.ExtZpos = 0.0
    doc.recompute()
    ergebnis = ko.bahn_fuer(
        job, job.Model.Group, form, 15.0, 2.0, 0.3, True, waende, korrektur=korrektur
    )
    FreeCAD.closeDocument(doc.Name)
    return ergebnis


def kontur_punkte(punkte):
    return [p for p in punkte if p.notiz and p.notiz.startswith("KOMP X")]


def zahl(text, buchstabe):
    m = re.search(rf"\b{buchstabe}(-?[0-9.]+)", text)
    return float(m.group(1)) if m else None


# 1. Ecken R 5
teil5, waende5 = tasche(5)
mit = bahn(teil5, waende5, True)
ohne = bahn(teil5, waende5, False)
kp = kontur_punkte(mit.punkte)
anfang = [p for p in mit.punkte if p.notiz and p.notiz.startswith("KOMP ANFANG")]
ende = [p for p in mit.punkte if p.notiz and p.notiz.startswith("KOMP ENDE")]
print(f"R5: {len(kp)} Konturpunkte, Anfang {anfang[0].notiz if anfang else None}")
pruefe(
    len(anfang) == 1 and len(ende) == 1 and kp, f"R5: Notizen {len(anfang)}/{len(ende)}/{len(kp)}"
)
pruefe(anfang and "G41" in anfang[0].notiz, "Gleichlauf in der Tasche: nicht G41")
for p in kp:
    x, y = zahl(p.notiz, "X"), zahl(p.notiz, "Y")
    auf_wand = min(abs(x - 20), abs(x - 80), abs(y - 20), abs(y - 60))
    pruefe(
        auf_wand < 1e-3 and 20 - 1e-3 <= x <= 80 + 1e-3, f"R5: Punkt nicht auf der Wand {p.notiz}"
    )
    pruefe(" G2" not in p.notiz and " G3" not in p.notiz, f"R5: Bogen in der Kontur {p.notiz}")
ecken = {(round(zahl(p.notiz, "X")), round(zahl(p.notiz, "Y"))) for p in kp}
pruefe({(20, 20), (80, 20), (80, 60), (20, 60)} <= ecken, f"R5: Ecken {sorted(ecken)}")
# 3. Die Mitte bleibt dieselbe
pruefe(
    [(p.x, p.y, p.z) for p in mit.punkte] == [(p.x, p.y, p.z) for p in ohne.punkte]
    and not any(p.notiz for p in ohne.punkte),
    "Korrektur ändert die Bahn",
)

# 2. Ecken R 10
teil10, waende10 = tasche(10)
mit10 = bahn(teil10, waende10, True)
boegen = [p for p in kontur_punkte(mit10.punkte) if " G" in p.notiz]
print(f"R10: {len(boegen)} Bögen, z. B. {boegen[0].notiz if boegen else None}")
pruefe(len(boegen) == 4, f"R10: {len(boegen)} Bögen")
for p in boegen:
    x, y, mx, my = (zahl(p.notiz, b) for b in "XYIJ")
    pruefe(abs(math.hypot(x - mx, y - my) - 10) < 1e-3, f"R10: Bogenradius {p.notiz}")

# 4. Der Postprozessor
from camaddon import bahn as bn  # noqa: E402
from camaddon import postprozessor as pp  # noqa: E402

abschnitt = pp.Abschnitt(
    "Kontur T1", 1, 2000.0, False, "None", bn.befehle(mit.punkte, 900.0, 300.0), "Fräser"
)
fraese = pp.Maschineninfo("Fräse")


def programm(kennung):
    return pp.programm([abschnitt], pp.steuerung(kennung), fraese, "Korrektur").zeilen


z = programm("linuxcnc")
k_ein = z.index("G41") if "G41" in z else -1
k_aus = z.index("G40") if "G40" in z else -1
print("\n".join(z[k_ein - 2 : k_ein + 9]))
pruefe(0 <= k_ein < k_aus, f"LinuxCNC: G41 {k_ein}, G40 {k_aus}")
zwischen = z[k_ein + 1 : k_aus]
pruefe(zwischen and "X50" in zwischen[0] and "Y60" in zwischen[0], f"erste Fahrt: {zwischen[:1]}")
pruefe(
    not any(x.startswith(("G2", "G3")) for x in zwischen),
    f"R5: Bögen in der Kontur: {[x for x in zwischen if x.startswith(('G2', 'G3'))]}",
)
pruefe(not any("KOMP" in x for x in z), "Notizen im Programm")
nach = z[k_aus + 1 : k_aus + 3]
pruefe(nach and nach[0].startswith("G1"), f"nach G40: {nach}")
zf = pp.programm([abschnitt], pp.steuerung("fanuc"), fraese, "Korrektur").zeilen
pruefe(any(x.startswith("G41 D1") for x in zf), "Fanuc: kein „G41 D1“")
zg = pp.programm([abschnitt], pp.steuerung("grbl"), fraese, "Korrektur").zeilen
pruefe(
    not any(x.startswith(("G41", "G40")) for x in zg) and not any("KOMP" in x for x in zg),
    "GRBL: Korrektur oder Notizen",
)
# Mit R 10: Bögen G3 in der Kontur (die Tasche gegen den Uhrzeigersinn).
abschnitt = pp.Abschnitt(
    "Kontur T1", 1, 2000.0, False, "None", bn.befehle(mit10.punkte, 900.0, 300.0), "Fräser"
)
z10 = programm("linuxcnc")
pruefe(sum(x.startswith("G3") for x in z10) >= 4, f"R10: {sum(x.startswith('G3') for x in z10)}")

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
