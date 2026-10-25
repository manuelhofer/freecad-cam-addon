# SPDX-License-Identifier: LGPL-2.1-or-later
# GRBL 1.1 (W-041; Manuel, 2026-10-25: Postprozessoren „perfekt“ – „alle !“): GRBL kennt kein M6,
# keine Bohrzyklen, kein G98/G99, kein G43 H, keine Rundachsen (README „List of Supported G-Codes
# in Grbl v1.1“). Der Wechsel ist ein Halt (M0) nach dem Kommentar mit dem Werkzeug, die
# Bohrzyklen stehen in G0/G1/G4 (G83 mit Zustellungen und Rückzug auf R, G82 mit Verweilen, G85
# heraus im Vorschub, G98: zurück auf die Höhe davor, G99: auf R), Gewindebohren fehlt mit
# Hinweis, Rundachsen bekommen einen Hinweis; nachgelesen ohne Befund.
# Ausführen: freecadcmd tests/test_postprozessor_grbl.py

import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import Path  # noqa: E402

from camaddon import postprozessor as pp  # noqa: E402
from camaddon import sprache  # noqa: E402

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)
        print("FEHLER:", text)


sprache.setze_sprache("de")
C = Path.Command
s = pp.steuerung("grbl")
fraese = pp.Maschineninfo("Fräse")
tasche = pp.Abschnitt(
    "Tasche",
    1,
    12000.0,
    False,
    "Mist",
    [
        C("G0", {"X": 0.0, "Y": 0.0, "Z": 5.0}),
        C("G1", {"Z": -2.0, "F": 5.0}),
        C("G1", {"X": 20.0, "F": 20.0}),
        C("G0", {"Z": 5.0}),
    ],
    "Fräser Ø 6",
)
bohren = pp.Abschnitt(
    "Bohren",
    2,
    900.0,
    False,
    "None",
    [
        C("G90"),
        C("G0", {"Z": 20.0}),
        C("G98"),
        C("G0", {"X": 10.0, "Y": 10.0}),
        C("G0", {"Z": 5.0, "F": 0.0}),
        C("G81", {"X": 10.0, "Y": 10.0, "Z": -8.0, "R": 2.0, "F": 2.0}),
        C("G83", {"X": 30.0, "Y": 10.0, "Z": -12.0, "R": 2.0, "Q": 5.0, "F": 2.0}),
        C("G82", {"X": 40.0, "Y": 10.0, "Z": -4.0, "R": 2.0, "P": 0.5, "F": 2.0}),
        C("G80"),
        C("G99"),
        C("G85", {"X": 50.0, "Y": 10.0, "Z": -6.0, "R": 2.0, "F": 1.0}),
        C("G80"),
        C("G0", {"Z": 20.0}),
    ],
    "Bohrer Ø 5",
)
programm = pp.programm([tasche, bohren], s, fraese, "Teil")
z = programm.zeilen
woerter = " ".join(z).split()

# Kein M6, kein G43, kein G49, keine Zyklen, kein G98/G99; Nebel als M8; ASCII.
for verboten in ("M6", "G43", "G49", "G81", "G82", "G83", "G85", "G98", "G99", "M7"):
    pruefe(verboten not in woerter, f"{verboten} im Programm: {z}")
pruefe(z.count("M0") == 2, f"je Werkzeug ein Halt: {z}")
i = z.index("M0") if "M0" in z else -1
pruefe(i > 0 and z[i - 1].startswith("(T1 "), f"Kommentar vor dem Halt: {z[i - 2 : i + 1]}")
pruefe("M8" in z, f"Nebel als M8: {z}")
# Die Marken als Namen im Kommentar, vorn ANFANG – ohne Halt je Bearbeitung (Manuel, 2026-10-25:
# Werkzeugliste und Sprungnamen „bei jedem post prozessor“).
pruefe(
    "(  ANFANG - Programmanfang - hierher zurueck)" in z
    and "(ANFANG)" in z
    and "(TASCHE - Tasche)" in z
    and "(     fuer: BOHREN)" in z,
    f"Marken und Werkzeugliste: {z[:16]}",
)
pruefe(all(x.isascii() for x in z) and not any(x.startswith("%") for x in z), "ASCII, kein %")

# Bohren ausgeschrieben (G98: zurück auf 5, G99 beim Reiben: auf R).
k = z.index("G0 Z2.000") if "G0 Z2.000" in z else -1
pruefe(
    z[k : k + 3] == ["G0 Z2.000", "G1 Z-8.000 F120.000", "G0 Z5.000"],
    f"G81: {z[k - 1 : k + 4]}",
)
k = z.index("G0 X30.000 Y10.000") if "G0 X30.000 Y10.000" in z else -1
pruefe(
    z[k + 1 : k + 9]
    == [
        "G0 Z2.000",
        "G1 Z-3.000 F120.000",
        "G0 Z2.000",
        "G0 Z-2.500",
        "G1 Z-8.000",
        "G0 Z2.000",
        "G0 Z-7.500",
        "G1 Z-12.000",
    ],
    f"G83: {z[k : k + 11]}",
)
k = z.index("G0 X40.000 Y10.000") if "G0 X40.000 Y10.000" in z else -1
pruefe(
    z[k + 1 : k + 5] == ["G0 Z2.000", "G1 Z-4.000 F120.000", "G4 P0.500", "G0 Z5.000"],
    f"G82: {z[k : k + 6]}",
)
k = z.index("G0 X50.000 Y10.000") if "G0 X50.000 Y10.000" in z else -1
pruefe(
    z[k + 1 : k + 5] == ["G0 Z2.000", "G1 Z-6.000 F60.000", "G1 Z2.000", "G0 Z2.000"],
    f"G85: {z[k : k + 6]}",
)
befunde, saetze = pp.nachlesen(programm, s, fraese)
pruefe(not befunde and saetze > 10, f"nachgelesen: {[(b.art, b.satz) for b in befunde]}")

# Gewindebohren geht nicht: Hinweis, keine Bewegung; Rundachsen: Hinweis.
gewinde = pp.Abschnitt(
    "Gewinde",
    4,
    255.0,
    False,
    "None",
    [
        C("G0", {"X": 60.0, "Y": 30.0, "Z": 24.0}),
        C("G84", {"X": 60.0, "Y": 30.0, "Z": 6.5, "R": 24.0, "S": 255.0, "F": 1.5}),
        C("G80"),
    ],
    "M10",
)
pg = pp.programm([gewinde], s, fraese, "G")
pruefe(not any(x.startswith("G84") for x in pg.zeilen), f"G84 übrig: {pg.zeilen}")
pruefe(any("kein Gewinde" in h for h in pg.hinweise), f"Hinweis Gewinde: {pg.hinweise}")
rund = pp.Abschnitt("Rund", 1, 1000.0, False, "None", [C("G1", {"X": 1.0, "A": 30.0, "F": 1.0})])
pr = pp.programm([rund], s, fraese, "R")
pruefe(any("nur X, Y und Z" in h for h in pr.hinweise), f"Hinweis Rundachsen: {pr.hinweise}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
