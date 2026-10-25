# SPDX-License-Identifier: LGPL-2.1-or-later
# Zufällige Bahnen durch jeden Postprozessor (W-041; Manuel, 2026-10-25: „bei den post prozessoren
# auf jeden fall darauf achten das die auch wirlich alles richtig ausgeben“): Geraden, Bögen in
# allen drei Ebenen (auch Radius 0, fast gleiche Enden), Schrauben, Bohrzyklen, eine Rundachse
# über mehrere Umdrehungen, je Programm drei zufällig umgeschaltete Haken, Fräse und Drehmaschine,
# Programmnummern von 0 bis 200 000. Fester Startwert – jedes Mal dieselben Programme. Kein
# Absturz; nachgelesen ohne Befund (außer Kreis: zufällige Bögen sind oft keine).
# Ausführen: freecadcmd tests/test_postprozessor_zufall.py

import os
import random
import sys
import traceback

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import Path  # noqa: E402

from camaddon import postprozessor as pp  # noqa: E402
from camaddon import sprache  # noqa: E402

fehler = []
C = Path.Command
zufall = random.Random(20261025)


def zahl(a, b):
    return round(zufall.uniform(a, b), zufall.choice((0, 1, 3, 6)))


def vorschub(a, b):
    return max(
        zahl(a, b), 0.01
    )  # gerundet nie F0 – das hieße „steh“ (der Postprozessor lässt es weg)


def abschnitt(n):
    x, y, z = zahl(-50, 50), zahl(-50, 50), 20.0
    befehle = [C("G0", {"X": x, "Y": y, "Z": z})]
    for _ in range(zufall.randint(3, 25)):
        art = zufall.choice(("G0", "G1", "G1", "G2", "G3", "G81", "G83", "G17", "G18", "G19", "A"))
        if art in ("G17", "G18", "G19"):
            befehle.append(C(art))
            continue
        if art in ("G81", "G83"):
            p = {"X": zahl(-50, 50), "Y": zahl(-50, 50), "Z": zahl(-20, 0), "R": 2.0}
            p["F"] = vorschub(0.5, 5)
            if art == "G83":
                p["Q"] = zufall.choice((0.0, 1.0, 5.0))
            befehle += [C("G98"), C(art, p), C("G80")]
            continue
        if art == "A":
            befehle.append(
                C("G1", {"X": zahl(-50, 50), "A": zahl(-720, 720), "F": vorschub(0.1, 50)})
            )
            continue
        p = {"X": zahl(-50, 50), "Y": zahl(-50, 50), "Z": zahl(-10, 20)}
        if art in ("G2", "G3"):
            i, j = zufall.choice(((zahl(-20, 20), zahl(-20, 20)), (0.0, 0.0), (1e-4, 0.0)))
            p = {
                "X": x + zufall.choice((0.0, 1e-5, zahl(-5, 5))),
                "Y": y + zufall.choice((0.0, zahl(-5, 5))),
                "Z": zufall.choice((z, zahl(-10, 20))),
                "I": i,
                "J": j,
            }
        if art != "G0":
            p["F"] = vorschub(0.01, 100)
        befehle.append(C(art, p))
        x, y, z = p["X"], p["Y"], p["Z"]
    return pp.Abschnitt(
        f"Op{n}",
        zufall.randint(1, 4),
        zufall.choice((900.0, 12000.0)),
        zufall.random() < 0.2,
        zufall.choice(("None", "Flood", "Mist")),
        befehle,
        "Fräser",
    )


sprache.setze_sprache("de")
fraese = pp.Maschineninfo("Fräse", wechselpunkt={"Z": 250.0})
dreh = pp.Maschineninfo("Drehmaschine", True, True, {"C": "C4"}, {1: "3"})
programme = 0
for runde in range(120):
    teile = [abschnitt(k) for k in range(zufall.randint(1, 4))]
    info = zufall.choice((fraese, dreh))
    for kennung, s0 in pp.STEUERUNGEN.items():
        s = s0
        for haken in zufall.sample([h for h in pp.HAKEN if hasattr(s0, h)], 3):
            s = s.ersetzt(**{haken: not getattr(s, haken)})
        try:
            programm = pp.programm(teile, s, info, "Zufall", nummer=zufall.randint(0, 200000))
            befunde = pp.nachlesen(programm, s, info)[0]
        except Exception:  # noqa: BLE001 – jeder Absturz ist ein Befund
            fehler.append(f"Runde {runde} {kennung}: {traceback.format_exc().splitlines()[-1]}")
            continue
        programme += 1
        arten = {b.art for b in befunde} - {"kreis"}
        if s.dialekt == "mpr":
            continue
        if arten:
            fehler.append(f"Runde {runde} {kennung}: {[(b.art, b.satz[:60]) for b in befunde][:2]}")

print(f"{programme} Programme")
if fehler:
    raise AssertionError("\n".join(fehler[:20]))
print()
print("OK", os.path.basename(__file__))
