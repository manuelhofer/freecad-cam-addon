# SPDX-License-Identifier: LGPL-2.1-or-later
# Gegenprobe der Postprozessoren (W-041; Manuel, 2026-10-25: „bei den post prozessoren auf jeden
# fall darauf achten das die auch wirlich alles richtig ausgeben“): Das fertige Programm jeder
# G-Code-Steuerung wird wieder eingelesen – modal wie an der Steuerung, Kommentare und
# Satznummern weg – und jeder Satz im Vorschub (G1, G2, G3) mit den Bahnen im Job verglichen:
# Endpunkt, bei Bögen die Mitte und der Drehsinn, der Vorschub in mm/min. Eilgänge,
# Wechselpunkt und Werkzeugwechsel darf der Postprozessor ergänzen, Vorschubsätze nicht.
# Beispiele: der C-Ring (Räumen, Nut mit Helix und Bögen, Messstopp, Schlichten) und die Platte
# mit Zapfen (Planfräsen, Kontur).
# Ausführen: freecadcmd tests/test_postprozessor_nachfahren.py

import math
import os
import re
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402

from camaddon import postprozessor as pp  # noqa: E402
from camaddon import sprache  # noqa: E402

fehler = []
GENAU = 0.0015  # mm – die Koordinaten stehen mit drei Stellen im Programm


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)
        print("FEHLER:", text)


def vorschubsaetze_job(abschnitte):
    """[(G, X, Y, Z, Mitte X, Mitte Y, F in mm/min)] der Vorschubsätze im Job – modal wie FreeCAD
    (F in mm/s)."""
    aus = []
    pos = {"X": None, "Y": None, "Z": None}
    for abschnitt in abschnitte:
        f = None
        for befehl in abschnitt.befehle:
            name, werte = (befehl.Name, befehl.Parameters) if hasattr(befehl, "Name") else befehl
            name = name.upper().replace("G0", "G", 1) if re.fullmatch(r"G0\d", name) else name
            name = {"G": "G0"}.get(name, name)
            if "F" in werte and float(werte["F"]) > 0:
                f = float(werte["F"]) * 60.0
            if name not in ("G0", "G1", "G2", "G3"):
                continue
            start = dict(pos)
            for a in pos:
                if a in werte:
                    pos[a] = float(werte[a])
            if name == "G0" or None in pos.values():
                continue
            if name == "G1" and all(abs(pos[a] - start[a]) < 1e-9 for a in pos):
                continue  # nichts zu fahren – der Postprozessor lässt es weg
            mitte = (None, None)
            if name in ("G2", "G3"):
                mitte = (
                    start["X"] + float(werte.get("I", 0.0)),
                    start["Y"] + float(werte.get("J", 0.0)),
                )
            aus.append((name, pos["X"], pos["Y"], pos["Z"], *mitte, f))
    return aus


_WORT = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")


def vorschubsaetze_programm(text, siemens=False):
    """Dasselbe aus dem Programmtext, wie eine Steuerung ihn liest."""
    aus = []
    pos = {"X": None, "Y": None, "Z": None}
    art, f, maschine = "G0", None, False
    for zeile in text.splitlines():
        zeile = re.sub(r"\([^)]*\)", "", zeile)
        zeile = zeile.split(";", 1)[0].strip().upper()
        if not zeile or zeile.startswith(("%", "O")):
            continue
        zeile = re.sub(r"^N\d+\s*", "", zeile)
        if siemens and ("SUPA" in zeile or "CYCLE" in zeile or ":" in zeile):
            continue  # Wechselpunkt in Maschinenkoordinaten, Zyklen, Marken
        woerter = _WORT.findall(zeile)
        g = [float(z) for b, z in woerter if b == "G"]
        werte = {b: float(z) for b, z in woerter if b not in ("G", "M", "N", "T", "S", "H", "D")}
        maschine = 53.0 in g
        for code in g:
            if code in (0.0, 1.0, 2.0, 3.0):
                art = f"G{int(code)}"
        if "F" in werte:
            f = werte["F"]
        start = dict(pos)
        for a in pos:
            if a in werte:
                pos[a] = None if maschine else werte[a]
        if maschine or art == "G0" or not any(a in werte for a in pos) or None in pos.values():
            continue
        mitte = (None, None)
        if art in ("G2", "G3"):
            mitte = (start["X"] + werte.get("I", 0.0), start["Y"] + werte.get("J", 0.0))
        aus.append((art, pos["X"], pos["Y"], pos["Z"], *mitte, f))
    return aus


def vergleichen(job_saetze, prog_saetze):
    """None, wenn jeder Vorschubsatz stimmt – sonst der erste Unterschied als Satz."""
    if len(job_saetze) != len(prog_saetze):
        return f"{len(prog_saetze)} Vorschubsätze statt {len(job_saetze)}"
    for i, (soll, ist) in enumerate(zip(job_saetze, prog_saetze, strict=True)):
        gleich = soll[0] == ist[0] and all(
            (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= GENAU)
            for a, b in zip(soll[1:6], ist[1:6], strict=True)
        )
        f_gleich = (
            soll[6] is not None
            and ist[6] is not None
            and math.isclose(soll[6], ist[6], rel_tol=1e-3, abs_tol=0.002)
        )
        if not (gleich and f_gleich):
            return f"Satz {i + 1} {ist} statt {soll}"
    return None


sprache.setze_sprache("de")
fraese = pp.Maschineninfo("Fräse", wechselpunkt={"Z": 250.0})
for datei in ("c_ring_nut_3achs.FCStd", "platte_zapfen_tasche.FCStd"):
    doc = FreeCAD.openDocument(os.path.join(ADDON, "beispiele", datei))
    for job in [o for o in doc.Objects if hasattr(o, "Operations")]:
        abschnitte = pp.abschnitte(job)
        soll = vorschubsaetze_job(abschnitte)
        pruefe(len(soll) > 20, f"{job.Label}: nur {len(soll)} Vorschubsätze")
        for kennung in ("linuxcnc", "fanuc", "haas", "mach", "mazak", "grbl", "siemens"):
            for aenderung in ({}, {"satznummern": True}, {"marken": False}):
                s = pp.steuerung(kennung, aenderung)
                programm = pp.programm(abschnitte, s, fraese, job.Label)
                ist = vorschubsaetze_programm(programm.text, siemens=kennung == "siemens")
                unterschied = vergleichen(soll, ist)
                pruefe(not unterschied, f"{datei} {job.Label} {kennung} {aenderung}: {unterschied}")
        print(ascii(f"{job.Label}: {len(soll)} Vorschubsaetze je Steuerung gleich"))
        if datei.startswith("platte"):
            # Die Gegenprobe merkt es: ein Satz 0,01 mm daneben, ein Vorschub anders.
            text = pp.programm(abschnitte, pp.steuerung("fanuc"), fraese, "P").text
            z = re.search(r"^G1 [^\n]*Z(-?\d+\.\d+)", text, re.M)
            daneben = text[: z.start(1)] + f"{float(z.group(1)) + 0.01:.3f}" + text[z.end(1) :]
            pruefe(vergleichen(soll, vorschubsaetze_programm(daneben)), "0,01 mm daneben übersehen")
            f = re.search(r"F(\d+\.\d+)", text)
            anders = text[: f.start(1)] + f"{float(f.group(1)) * 1.01:.3f}" + text[f.end(1) :]
            pruefe(vergleichen(soll, vorschubsaetze_programm(anders)), "anderes F übersehen")
    FreeCAD.closeDocument(doc.Name)

if fehler:
    raise AssertionError("\n".join(fehler[:20]))
print()
print("OK", os.path.basename(__file__))
