# SPDX-License-Identifier: LGPL-2.1-or-later
# Das Programm nachlesen wie die Steuerung (programm_pruefen, P-2026-10-04-53): Absichtlich
# kaputte Sätze findet es alle – ohne Werkzeuglänge (nach dem Wechsel bis G43; an Siemens nach
# D0 bis D1), Vorschub bei stehender Spindel, ohne F oder mit F0, ein Kreis, dessen Mitte vom
# Anfang und Ende verschieden weit liegt (auch in G18), derselbe Satz zweimal, kein M30. Was der
# Postprozessor für eine Tasche an jeder Steuerung und für eine Welle an der Drehmaschine
# schreibt, liest sich sauber; an der LinuxCNC-Drehmaschine mit G43 im ersten Fahrsatz, an Fanuc
# und Haas ohne G90 (dort der Längsdrehzyklus) und G49 im Kopf.
# Ausführen: freecadcmd tests/test_programm_pruefen.py

import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import Path

from camaddon import postprozessor as pp
from camaddon import programm_pruefen as prp
from camaddon import sprache

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def arten(text, **werte):
    return [(b.art, b.zeile) for b in prp.pruefe(text, **werte).befunde]


sprache.setze_sprache("de")
C = Path.Command

# --- Kaputte Sätze ----------------------------------------------------------------------------
kaputt = "\n".join(
    [
        "%",
        "G17 G21 G90",
        "T1 M6",
        "G0 X0 Y0 Z5",  # 4: ohne Länge
        "G43 H1",
        "G1 Z-1 F100",  # 6: Spindel steht
        "M3 S1000",
        "G2 X10 Y0 I5 J0",
        "G2 X20 Y1 I5 J0",  # 9: Radius 5 / 5,099
        "G1 X30 F0",  # 10: F0
        "G1 X30 F0",  # 11: F0 und doppelt
        "%",
    ]
)
pruefe(
    arten(kaputt)
    == [
        ("laenge", 4),
        ("spindel", 6),
        ("kreis", 9),
        ("vorschub", 10),
        ("vorschub", 11),
        ("doppelt", 11),
        ("ende", 0),
    ],
    f"kaputt: {arten(kaputt)}",
)
# Mit der Länge im Satz (G0 G43 H1 Z5) und M30 ist es sauber; X und Y oben ohne Länge auch.
sauber = "\n".join(
    [
        "%",
        "(Kommentar mit X10 und Z-5)",
        "N10 G17 G21 G49",
        "T1 M6",
        "G0 X10 Y10",
        "G0 G43 H1 Z5",
        "M3 S1000",
        "G1 Z-1 F100",
        "G3 X20 Y10 I5 J0",
        "G53 G0 Z0",
        "M5",
        "M30",
    ]
)
pruefe(arten(sauber) == [], f"sauber: {arten(sauber)}")
# Siemens: der Wechsel bringt D1; SUPA D0 schaltet ab, D1 wieder an; Kommentare mit „;“.
siemens = "\n".join(
    [
        "; X1 Z-9 Kommentar",
        "T1 M6",
        "M3 S1000",
        "G0 X0 Y0 Z5",
        "G1 Z-1 F100",
        "G0 SUPA D0 Z300",
        "G0 X10 Y10",
        "G0 Z5",  # 8: nach D0 ohne Länge
        "G0 D1 Z5",
        "M30",
    ]
)
pruefe(arten(siemens, siemens=True) == [("laenge", 8)], f"Siemens: {arten(siemens, siemens=True)}")
# Ein Kreis in G18 (Z, X; I, K): Mitte bei Z 5, X 0 – vom Anfang 5, vom Ende 5.
g18 = "%\nG18\nM3 S100\nG1 X0 Z0 F50\nG2 X0 Z10 I0 K5\nG2 X1 Z20 I0 K5\nM30"
pruefe(arten(g18) == [("kreis", 6)], f"G18: {arten(g18)}")
# In G93 gehört F in jeden Satz im Vorschub.
g93 = "%\nM3 S100\nG93\nG1 X1 F2\nG1 X2\nG94\nG1 X3\nG1 X4 F100\nM30"
pruefe(arten(g93) == [("vorschub", 5), ("vorschub", 7)], f"G93: {arten(g93)}")
# Ohne G43 an einer Steuerung, die die Länge mit dem Wechsel nimmt: nichts.
pruefe(arten("T1 M6\nM3 S1\nG0 Z5\nM30", laenge_mit_wechsel=True) == [], "mit dem Wechsel")

# --- Was der Postprozessor schreibt ---------------------------------------------------------
tasche = pp.Abschnitt(
    "Tasche",
    3,
    2000.0,
    False,
    "Flood",
    [
        C("G0", {"X": 10.0, "Y": 5.0}),
        C("G0", {"Z": 5.0}),
        C("G1", {"Z": -2.0, "F": 5.0}),
        C("G2", {"X": 20.0, "Y": 5.0, "I": 5.0, "J": 0.0, "F": 10.0}),
        C("G1", {"X": 20.0, "Y": 15.0}),
    ],
    "Fräser Ø 12",
)
zweite = pp.Abschnitt("Zwei", 4, 3000.0, False, "None", list(tasche.befehle), "Fräser Ø 6")
fraese = pp.Maschineninfo("Fräse", wechselpunkt={"Z": 0.0})
for kennung in pp.STEUERUNGEN:
    for aenderung in ({}, {"marken": False}, {"satznummern": True}):
        s = pp.steuerung(kennung, aenderung)
        programm = pp.programm([tasche, zweite], s, fraese, "P")
        befunde, saetze = pp.nachlesen(programm, s, fraese)
        pruefe(
            not befunde and saetze >= 10,
            f"{kennung} {aenderung}: {[(b.art, b.satz) for b in befunde]} ({saetze} Sätze)",
        )
# Die Drehmaschine: LinuxCNC schaltet die Korrektur mit G43 im ersten Fahrsatz ein, die
# anderen mit dem Wechsel (T0101, T1 D1).
dreh = pp.Maschineninfo("Drehmaschine", True, True, {"C": "C4"}, {1: "3"})
welle = pp.Abschnitt(
    "Rundum",
    1,
    3000.0,
    False,
    "None",
    [
        C("G0", {"X": 42.0, "Z": 3.0, "C": 0.0}),
        C("G93"),
        C("G1", {"X": 38.0, "Z": 0.0, "C": 90.0, "F": 0.05}),
        C("G94"),
        C("G0", {"X": 42.0}),
    ],
)
for kennung in pp.STEUERUNGEN:
    s = pp.steuerung(kennung)
    if s.dialekt == "klartext":
        continue  # Heidenhain-Klartext gibt es nur für die Fräse (mit Hinweis, test_postprozessor)
    programm = pp.programm([welle], s, dreh, "W")
    befunde, _saetze = pp.nachlesen(programm, s, dreh)
    pruefe(not befunde, f"Drehmaschine {kennung}: {[(b.art, b.satz) for b in befunde]}")
# An Fanuc- und Haas-Drehmaschinen ist G90 der Längsdrehzyklus, G49 gibt es nicht: ein eigener
# Anfang ohne beide (P-2026-10-04-53).
for kennung in ("fanuc", "haas"):
    woerter_k = " ".join(pp.programm([welle], pp.steuerung(kennung), dreh, "W").zeilen).split()
    pruefe(
        "G90" not in woerter_k and "G49" not in woerter_k and "G18" in woerter_k,
        f"{kennung}-Drehmaschine: {woerter_k[:12]}",
    )
# G90 aus der Bahn (FreeCADs Bohren) entfällt dort; G91 bleibt, mit Hinweis.
mit_g90 = pp.Abschnitt("B", 1, 100.0, False, "None", [C("G90"), C("G0", {"X": 40.0, "Z": 2.0})])
p_g90 = pp.programm([mit_g90], pp.steuerung("fanuc"), dreh, "W")
pruefe(not any("G90" in x.split() for x in p_g90.zeilen), f"Fanuc G90: {p_g90.zeilen}")
mit_g91 = pp.Abschnitt("B", 1, 100.0, False, "None", [C("G91"), C("G0", {"Z": -2.0})])
p_g91 = pp.programm([mit_g91], pp.steuerung("haas"), dreh, "W")
pruefe("G91" in p_g91.zeilen and any("G91" in h for h in p_g91.hinweise), f"G91: {p_g91.hinweise}")
# Wie X zu lesen ist, steht im Kopf – passend zur Maschine (P-2026-10-04-57).
for kennung, durchmesser, radius in (("linuxcnc", "G7", "G8"), ("siemens", "DIAMON", "DIAMOF")):
    z_d = pp.programm([welle], pp.steuerung(kennung), dreh, "W").zeilen
    dreh_r = pp.Maschineninfo("Drehmaschine", True, False, {"C": "C4"}, {1: "3"})
    z_r = pp.programm([welle], pp.steuerung(kennung), dreh_r, "W").zeilen
    pruefe(
        durchmesser in z_d and radius not in z_d and radius in z_r and durchmesser not in z_r,
        f"{kennung}: Durchmesser/Radius {z_d[:8]} / {z_r[:8]}",
    )
lcnc_dreh = pp.programm([welle], pp.steuerung("linuxcnc"), dreh, "W").zeilen
pruefe("G0 G43 H1 X84.000 Z3.000 C0.000" in lcnc_dreh, f"LinuxCNC Drehmaschine: {lcnc_dreh}")
# Über der Höchstdrehzahl der Maschine: S auf sie, die Vorschübe im selben Maß – fz bleibt
# (sonst begrenzte die Steuerung nur S, und der Span je Zahn wüchse).
schnell = pp.Abschnitt("Klein", 3, 30000.0, False, "None", list(tasche.befehle), "Ø 2")
begrenzt_info = pp.Maschineninfo("Fräse", drehzahl_max=12000.0)
p_s = pp.programm([schnell], pp.steuerung("linuxcnc"), begrenzt_info, "P")
pruefe(
    "M3 S12000" in p_s.zeilen
    and any("F120.000" in x for x in p_s.zeilen)  # G1 F300 × 0,4
    and any("F240.000" in x for x in p_s.zeilen)  # G2 F600 × 0,4
    and any("30000" in h and "12000" in h for h in p_s.hinweise),
    f"Drehzahl begrenzt: {[x for x in p_s.zeilen if 'S' in x or 'F' in x]}, {p_s.hinweise}",
)
p_frei = pp.programm([tasche], pp.steuerung("linuxcnc"), begrenzt_info, "P")
pruefe("M3 S2000" in p_frei.zeilen and not p_frei.hinweise, f"unter der Grenze: {p_frei.hinweise}")
# Groß (über 2 MB): an Siemens und Fanuc der Hinweis, es von extern bzw. per DNC zu fahren.
gross = pp.Programm(["G1 X1.000 Y2.000 Z3.000 F100.000"] * 80000, [], 80000)
pruefe(
    "MB" in pp.groesse_text(gross, pp.steuerung("siemens"))
    and "EXTCALL" in pp.groesse_text(gross, pp.steuerung("siemens"))
    and "DNC" in pp.groesse_text(gross, pp.steuerung("fanuc"))
    and pp.groesse_text(gross, pp.steuerung("linuxcnc")) == ""
    and pp.groesse_text(pp.Programm(["M30"], [], 0), pp.steuerung("siemens")) == "",
    f"groß: {pp.groesse_text(gross, pp.steuerung('siemens'))!r}",
)
# Kommentare nur in ASCII (P-2026-10-04-60): Fanuc, Haas, Mach, LinuxCNC – „Fräser Ø 12“ wird
# „Fraeser D 12“; Siemens behält die Umlaute. Der Prüfer meldet sonst jedes Zeichen.
for kennung in pp.STEUERUNGEN:
    s = pp.steuerung(kennung)
    p_a = pp.programm([tasche], s, fraese, "Größe – Ø")
    nicht_ascii = [x for x in p_a.zeilen if not x.isascii()]
    if kennung == "siemens":
        pruefe(nicht_ascii, "Siemens: Umlaute ersetzt")
    else:
        pruefe(
            not nicht_ascii and any("Fraeser D 12" in x for x in p_a.zeilen),
            f"{kennung}: {nicht_ascii}",
        )
    befunde, _saetze = pp.nachlesen(p_a, s, fraese)
    pruefe(not befunde, f"{kennung} ASCII: {[(b.art, b.satz) for b in befunde]}")
mit_umlaut = pp.programm([tasche], pp.steuerung("fanuc", {"nur_ascii": False}), fraese, "Ö")
befunde, _saetze = pp.nachlesen(mit_umlaut, pp.steuerung("fanuc", {"nur_ascii": True}), fraese)
pruefe(any(b.art == prp.ZEICHEN for b in befunde), "Prüfer: Umlaut nicht gemeldet")
# {werkzeug} im Wechsel: Siemens mit Werkzeugverwaltung ruft über Namen (P-2026-10-04-62).
namen = pp.programm(
    [tasche], pp.steuerung("siemens", {"wechsel_fraesen": 'T="{werkzeug}" M6'}), fraese, "P"
).zeilen
pruefe('T="Fraeser D 12" M6' in namen, f"Name im Wechsel: {[x for x in namen if 'M6' in x]}")
# Haas: angetriebenes Werkzeug vorwärts M133, rückwärts M134 (P die Drehzahl).
links = pp.Abschnitt("Links", 1, 1200.0, True, "None", list(welle.befehle))
z_haas = pp.programm([welle, links], pp.steuerung("haas"), dreh, "W").zeilen
pruefe(
    "M133 P3000" in z_haas and "M134 P1200" in z_haas, f"Haas: {[x for x in z_haas if 'M13' in x]}"
)
# Der Satz fürs Fenster.
text = pp.nachgelesen_text([prp.Befund(prp.LAENGE, 12, "G0 Z5.000")], 40)
pruefe(text.startswith("Nachgelesen") and "Zeile 12" in text and "G0 Z5.000" in text, text)
pruefe("nichts gefunden" in pp.nachgelesen_text([], 40), "gut")

if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
