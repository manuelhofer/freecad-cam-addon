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

from camaddon import messstopp as ms  # noqa: E402
from camaddon import postprozessor as pp  # noqa: E402
from camaddon import sprache  # noqa: E402

fehler = []
GENAU = 0.0015  # mm – die Koordinaten stehen mit drei Stellen im Programm


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)
        print("FEHLER:", text)


RUND = ("A", "B", "C")


def vorschubsaetze_job(abschnitte, info, spindel=None):
    """[(G, X, Y, Z, Mitte X, Mitte Y, F je Minute, A, B, C)] der Vorschubsätze im Job – modal wie
    FreeCAD (F je Sekunde; in G93 1 ÷ Zeit). Rundachsen, die der Postprozessor mit dem anderen
    Vorzeichen schreibt (Rundum-Bahnen nach DIN: postprozessor._rund_umdrehen), umgedreht.
    `spindel` (eine Liste): je Satz dazu (Drehzahl, links) der Operation."""
    aus = []
    pos = {"X": None, "Y": None, "Z": None}
    rund = dict.fromkeys(RUND)
    for abschnitt in abschnitte:
        f = None
        umdrehen = pp._rund_umdrehen(abschnitt, info)
        for befehl in abschnitt.befehle:
            name, werte = (befehl.Name, befehl.Parameters) if hasattr(befehl, "Name") else befehl
            name = name.upper().replace("G0", "G", 1) if re.fullmatch(r"G0\d", name) else name
            name = {"G": "G0"}.get(name, name)
            if "F" in werte and float(werte["F"]) > 0:
                f = float(werte["F"]) * 60.0
            if name not in ("G0", "G1", "G2", "G3"):
                continue
            start, start_rund = dict(pos), dict(rund)
            for a in pos:
                if a in werte:
                    pos[a] = float(werte[a])
            for a in RUND:
                if a in werte:
                    rund[a] = -float(werte[a]) if a in umdrehen else float(werte[a])
            if name == "G0" or None in pos.values():
                continue
            if (
                name == "G1"
                and all(abs(pos[a] - start[a]) < 1e-9 for a in pos)
                and rund == start_rund
            ):
                continue  # nichts zu fahren – der Postprozessor lässt es weg
            mitte = (None, None)
            if name in ("G2", "G3"):
                mitte = (
                    start["X"] + float(werte.get("I", 0.0)),
                    start["Y"] + float(werte.get("J", 0.0)),
                )
            aus.append((name, pos["X"], pos["Y"], pos["Z"], *mitte, f, *rund.values()))
            if spindel is not None:
                spindel.append((round(abschnitt.drehzahl), bool(abschnitt.rueckwaerts)))
    return aus


_WORT = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")


def vorschubsaetze_programm(text, siemens=False, spindel=None):
    """Dasselbe aus dem Programmtext, wie eine Steuerung ihn liest. `spindel` (eine Liste): je Satz
    dazu (Drehzahl, links), wie die Spindel da läuft (0: sie steht)."""
    aus = []
    pos = {"X": None, "Y": None, "Z": None}
    rund = dict.fromkeys(RUND)
    art, f, maschine = "G0", None, False
    drehzahl, links, laeuft = 0, False, False
    for zeile in text.splitlines():
        zeile = re.sub(r"\([^)]*\)", "", zeile)
        zeile = zeile.split(";", 1)[0].strip().upper()
        zeile = re.sub(r"\b([ABC])=", r"\1", zeile)  # Siemens: „A=12.5“
        if not zeile or zeile.startswith(("%", "O")):
            continue
        zeile = re.sub(r"^N\d+\s*", "", zeile)
        if siemens and ("SUPA" in zeile or "CYCLE" in zeile or ":" in zeile):
            continue  # Wechselpunkt in Maschinenkoordinaten, Zyklen, Marken
        woerter = _WORT.findall(zeile)
        g = [float(z) for b, z in woerter if b == "G"]
        if 4.0 in g:
            continue  # Verweilen: X/P ist die Zeit (Fanuc „G4 X1.000“), keine Lage
        werte = {b: float(z) for b, z in woerter if b not in ("G", "M", "N", "T", "S", "H", "D")}
        for b, z in woerter:
            if b == "S":
                drehzahl = round(float(z))
            elif b == "M" and float(z) in (3.0, 4.0):
                laeuft, links = True, float(z) == 4.0
            elif b == "M" and float(z) == 5.0:
                laeuft = False
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
        for a in RUND:
            if a in werte:
                rund[a] = werte[a]
        bewegt = any(a in werte for a in (*pos, *RUND))
        if maschine or art == "G0" or not bewegt or None in pos.values():
            continue
        mitte = (None, None)
        if art in ("G2", "G3"):
            mitte = (start["X"] + werte.get("I", 0.0), start["Y"] + werte.get("J", 0.0))
        aus.append((art, pos["X"], pos["Y"], pos["Z"], *mitte, f, *rund.values()))
        if spindel is not None:
            spindel.append((drehzahl if laeuft else 0, links))
    return aus


def eilgaenge_job(abschnitte, info):
    """[(X, Y, Z, A, B, C)] der Eilgänge im Job, die etwas fahren – ohne den Zug nach oben nach
    einem Messstopp (dort fährt der Postprozessor zum Wechselpunkt)."""
    aus = []
    pos = {"X": None, "Y": None, "Z": None}
    rund = dict.fromkeys(RUND)
    for abschnitt in abschnitte:
        umdrehen = pp._rund_umdrehen(abschnitt, info)
        nach_messstopp = False
        for befehl in abschnitt.befehle:
            name, werte = (befehl.Name, befehl.Parameters) if hasattr(befehl, "Name") else befehl
            if name == ms.KOMMENTAR:
                nach_messstopp = True
                continue
            name = name.upper().replace("G0", "G", 1) if re.fullmatch(r"G0\d", name) else name
            name = {"G": "G0"}.get(name, name)
            if name not in ("G0", "G1", "G2", "G3"):
                continue
            vorher = (*pos.values(), *rund.values())
            for a in pos:
                if a in werte:
                    pos[a] = float(werte[a])
            for a in RUND:
                if a in werte:
                    rund[a] = -float(werte[a]) if a in umdrehen else float(werte[a])
            if name != "G0" or None in pos.values():
                continue
            if nach_messstopp and set(werte) <= {"Z", "F"}:
                nach_messstopp = False
                continue
            jetzt = (*pos.values(), *rund.values())
            if jetzt != vorher:
                aus.append(jetzt)
    return aus


def eilgaenge_programm(text, siemens=False):
    """Dasselbe aus dem Programmtext – ohne Sätze in Maschinenkoordinaten (G53, SUPA); ein
    Bohrzyklus setzt nur X und Y (zurück geht er auf die Höhe davor)."""
    aus = []
    pos = {"X": None, "Y": None, "Z": None}
    rund = dict.fromkeys(RUND)
    art = "G0"
    for zeile in text.splitlines():
        zeile = re.sub(r"\([^)]*\)", "", zeile)
        zeile = zeile.split(";", 1)[0].strip().upper()
        zeile = re.sub(r"\b([ABC])=", r"\1", zeile)
        if not zeile or zeile.startswith(("%", "O")):
            continue
        zeile = re.sub(r"^N\d+\s*", "", zeile)
        if siemens and ("SUPA" in zeile or "CYCLE" in zeile or ":" in zeile):
            continue
        woerter = _WORT.findall(zeile)
        g = [float(z) for b, z in woerter if b == "G"]
        if 4.0 in g:
            continue  # Verweilen: X/P ist die Zeit (Fanuc „G4 X1.000“), keine Lage
        werte = {b: float(z) for b, z in woerter if b not in ("G", "M", "N", "T", "S", "H", "D")}
        if 53.0 in g:
            for a in pos:
                if a in werte:
                    pos[a] = None
            continue
        zyklus = any(c in (73.0, 81.0, 82.0, 83.0, 84.0, 85.0) for c in g)
        for code in g:
            if code in (0.0, 1.0, 2.0, 3.0):
                art = f"G{int(code)}"
        vorher = (*pos.values(), *rund.values())
        for a in ("X", "Y") if zyklus else pos:
            if a in werte:
                pos[a] = werte[a]
        for a in RUND:
            if a in werte:
                rund[a] = werte[a]
        jetzt = (*pos.values(), *rund.values())
        if art == "G0" and not zyklus and None not in pos.values() and jetzt != vorher:
            aus.append(jetzt)
    return aus


def in_folge(soll, ist):
    """None, wenn jeder Eilgang aus `soll` in derselben Folge in `ist` steht (dazwischen darf
    mehr stehen: Wechselpunkt, Anfahren nach dem Wechsel)."""
    k = 0
    for i, p in enumerate(soll):
        while k < len(ist) and not all(
            (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= GENAU)
            for a, b in zip(p, ist[k], strict=True)
        ):
            k += 1
        if k >= len(ist):
            return f"Eilgang {i + 1} {p} fehlt"
        k += 1
    return None


def klartext_punkte(text):
    """[(X, Y, Z, F)] der Sätze im Vorschub eines Klartext-Programms (L, C) – modal, Zahlen mit
    Vorzeichen, F nur, wenn es sich ändert; Fortsetzungszeilen der Zyklen übersprungen."""
    aus = []
    pos = {"X": None, "Y": None, "Z": None}
    f = None
    pol = None
    for zeile in text.splitlines():
        if zeile.startswith("  "):
            continue
        satz = re.sub(r"^\d+ ", "", zeile).strip()
        if satz.startswith("CC "):
            pol = [float(w) for _a, w in re.findall(r"\b([XY])([-+]\d+\.?\d*)", satz)]
            continue
        if satz.startswith("CP "):
            # Die Schraubenlinie: um IPA um den Pol gedreht, Z um IZ.
            ipa = float(re.search(r"IPA([-+]\d+\.?\d*)", satz).group(1))
            iz = re.search(r"IZ([-+]\d+\.?\d*)", satz)
            r = math.hypot(pos["X"] - pol[0], pos["Y"] - pol[1])
            w = math.atan2(pos["Y"] - pol[1], pos["X"] - pol[0]) + math.radians(ipa)
            pos["X"], pos["Y"] = pol[0] + r * math.cos(w), pol[1] + r * math.sin(w)
            pos["Z"] += float(iz.group(1)) if iz else 0.0
            m = re.search(r"\bF(\d+\.?\d*)", satz)
            f = float(m.group(1)) if m else f
            aus.append((pos["X"], pos["Y"], pos["Z"], f))
            continue
        if not satz.startswith(("L ", "C ")):
            continue
        for a, w in re.findall(r"\b([XYZ])([-+]\d+\.?\d*)", satz):
            pos[a] = float(w)
        m = re.search(r"\bF(\d+\.?\d*)", satz)
        if m:
            f = float(m.group(1))
        if "FMAX" in satz or "M91" in satz or None in pos.values():
            continue
        aus.append((pos["X"], pos["Y"], pos["Z"], f))
    return aus


def im_klartext(job_saetze, punkte):
    """None, wenn jeder Endpunkt des Jobs in derselben Folge im Klartext steht (dazwischen darf
    mehr stehen: der Vollkreis in zwei Hälften, die Schraube in Geraden) – mit demselben F."""
    k = 0
    for i, soll in enumerate(job_saetze):
        # Eine Gerade ist der nächste Satz; ein Bogen darf Zwischenpunkte haben (zwei Hälften,
        # die Schraube in Geraden).
        bis = len(punkte) if soll[0] in ("G2", "G3") else min(k + 1, len(punkte))
        while k < bis and not all(
            abs(a - b) <= GENAU for a, b in zip(soll[1:4], punkte[k][:3], strict=True)
        ):
            k += 1
        if k >= bis:
            return f"Satz {i + 1} {soll} fehlt im Klartext"
        if punkte[k][3] is None or not math.isclose(soll[6], punkte[k][3], rel_tol=1e-3):
            return f"Satz {i + 1} F {punkte[k][3]} statt {soll[6]}"
        k += 1
    return None


def vergleichen(job_saetze, prog_saetze):
    """None, wenn jeder Vorschubsatz stimmt – sonst der erste Unterschied als Satz."""
    if len(job_saetze) != len(prog_saetze):
        return f"{len(prog_saetze)} Vorschubsätze statt {len(job_saetze)}"
    for i, (soll, ist) in enumerate(zip(job_saetze, prog_saetze, strict=True)):
        gleich = soll[0] == ist[0] and all(
            (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= GENAU)
            for a, b in zip((*soll[1:6], *soll[7:]), (*ist[1:6], *ist[7:]), strict=True)
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
for datei in ("c_ring_nut_3achs.FCStd", "platte_zapfen_tasche.FCStd", "testteil_4achs_nase.FCStd"):
    doc = FreeCAD.openDocument(os.path.join(ADDON, "beispiele", datei))
    for job in [o for o in doc.Objects if hasattr(o, "Operations")]:
        abschnitte = pp.abschnitte(job)
        spindel_soll = []
        soll = vorschubsaetze_job(abschnitte, fraese, spindel_soll)
        pruefe(len(soll) > 20, f"{job.Label}: nur {len(soll)} Vorschubsätze")
        pruefe(
            all(a.nullpunkte == tuple(job.Fixtures) for a in abschnitte),
            f"{job.Label}: Nullpunkte {abschnitte[0].nullpunkte} statt {job.Fixtures}",
        )
        rundum = any(w is not None for s in soll for w in s[7:])
        steuerungen = ("linuxcnc", "fanuc", "haas", "mach", "mazak", "grbl", "siemens")
        for kennung in [k for k in steuerungen if not (rundum and k == "grbl")]:
            for aenderung in (
                {},
                {"satznummern": True},
                {"marken": False, "nullpunkt_setzen": True},
            ):
                s = pp.steuerung(kennung, aenderung)
                programm = pp.programm(abschnitte, s, fraese, job.Label)
                ist = vorschubsaetze_programm(programm.text, siemens=kennung == "siemens")
                unterschied = vergleichen(soll, ist)
                pruefe(not unterschied, f"{datei} {job.Label} {kennung} {aenderung}: {unterschied}")
                # Bei jedem Vorschubsatz läuft die Spindel mit Drehzahl und Drehsinn der Operation
                # – auch nach Messstopp, Wechsel und Einstieg hinter einer Marke.
                spindel_ist = []
                vorschubsaetze_programm(programm.text, kennung == "siemens", spindel_ist)
                falsch = next(
                    (
                        (i, a, b)
                        for i, (a, b) in enumerate(zip(spindel_soll, spindel_ist, strict=True))
                        if a[0] > 0 and a != b
                    ),
                    None,
                )
                pruefe(not falsch, f"{datei} {job.Label} {kennung} {aenderung}: Spindel {falsch}")
                fehlt = in_folge(
                    eilgaenge_job(abschnitte, fraese),
                    eilgaenge_programm(programm.text, siemens=kennung == "siemens"),
                )
                pruefe(not fehlt, f"{datei} {job.Label} {kennung} {aenderung}: {fehlt}")
        for kennung in () if rundum else ("heidenhain", "heidenhain_tnc640"):
            programm = pp.programm(abschnitte, pp.steuerung(kennung), fraese, job.Label)
            unterschied = im_klartext(soll, klartext_punkte(programm.text))
            pruefe(not unterschied, f"{datei} {job.Label} {kennung}: {unterschied}")
        print(ascii(f"{job.Label}: {len(soll)} Vorschubsaetze je Steuerung gleich"))
        if datei.startswith("platte"):
            # Jeder Haken einzeln umgeschaltet, an jeder Steuerung (außer woodWOP): nachgelesen
            # ohne Befund, Vorschub und Eilgänge wie im Job (Klartext: jeder Endpunkt).
            mit = pp.Maschineninfo("Fräse", wechselpunkt={"Z": 250.0})
            mit.hochlauf = {"haupt": 1.0}
            eil = eilgaenge_job(abschnitte, mit)
            for kennung, s0 in pp.STEUERUNGEN.items():
                if s0.dialekt == "mpr":
                    continue
                for haken in (h for h in pp.HAKEN if hasattr(s0, h)):
                    s = s0.ersetzt(**{haken: not getattr(s0, haken)})
                    p_h = pp.programm(abschnitte, s, mit, job.Label, nummer=12)
                    befunde = pp.nachlesen(p_h, s, mit)[0]
                    if s.dialekt == "klartext":
                        u = im_klartext(soll, klartext_punkte(p_h.text))
                    else:
                        siemens = kennung == "siemens"
                        u = vergleichen(
                            soll, vorschubsaetze_programm(p_h.text, siemens)
                        ) or in_folge(eil, eilgaenge_programm(p_h.text, siemens))
                    pruefe(
                        not befunde and not u,
                        f"{kennung} {haken}={getattr(s, haken)}: {u} {[b.art for b in befunde[:3]]}",
                    )
            # Die Gegenprobe merkt es: ein Satz 0,01 mm daneben, ein Vorschub anders.
            text = pp.programm(abschnitte, pp.steuerung("fanuc"), fraese, "P").text
            z = re.search(r"^G1 [^\n]*Z(-?\d+\.\d+)", text, re.M)
            daneben = text[: z.start(1)] + f"{float(z.group(1)) + 0.01:.3f}" + text[z.end(1) :]
            pruefe(vergleichen(soll, vorschubsaetze_programm(daneben)), "0,01 mm daneben übersehen")
            f = re.search(r"F(\d+\.\d+)", text)
            anders = text[: f.start(1)] + f"{float(f.group(1)) * 1.01:.3f}" + text[f.end(1) :]
            pruefe(vergleichen(soll, vorschubsaetze_programm(anders)), "anderes F übersehen")
            ohne_m3 = re.sub(r"^M3 S\d+\n", "", text, count=1, flags=re.M)
            spindel_ohne = []
            vorschubsaetze_programm(ohne_m3, False, spindel_ohne)
            pruefe(
                any(a[0] > 0 and a != b for a, b in zip(spindel_soll, spindel_ohne, strict=True)),
                "fehlendes M3 übersehen",
            )
            g0 = re.search(r"^G0 X[^\n]*Y(-?\d+\.\d+)", text, re.M)
            daneben = text[: g0.start(1)] + f"{float(g0.group(1)) + 0.01:.3f}" + text[g0.end(1) :]
            pruefe(
                in_folge(eilgaenge_job(abschnitte, fraese), eilgaenge_programm(daneben)),
                "Eilgang 0,01 mm daneben übersehen",
            )
            text = pp.programm(abschnitte, pp.steuerung("heidenhain"), fraese, "P").text
            z = re.search(r"^\d+ L [^\n]*Z([-+]\d+\.\d+) R0 F\d", text, re.M)
            daneben = text[: z.start(1)] + f"{float(z.group(1)) + 0.01:+.3f}" + text[z.end(1) :]
            pruefe(
                im_klartext(soll, klartext_punkte(daneben)), "Klartext: 0,01 mm daneben übersehen"
            )
    FreeCAD.closeDocument(doc.Name)

if fehler:
    raise AssertionError("\n".join(fehler[:20]))
print()
print("OK", os.path.basename(__file__))
