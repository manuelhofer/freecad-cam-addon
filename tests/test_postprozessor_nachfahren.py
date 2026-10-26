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

import dataclasses
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


def vorschubsaetze_job(abschnitte, info, spindel=None, werkzeuge=None):
    """[(G, X, Y, Z, Mitte X, Mitte Y, F je Minute, A, B, C)] der Vorschubsätze im Job – modal wie
    FreeCAD (F je Sekunde; in G93 1 ÷ Zeit). Rundachsen, die der Postprozessor mit dem anderen
    Vorzeichen schreibt (Rundum-Bahnen nach DIN: postprozessor._rund_umdrehen), umgedreht.
    `spindel` (eine Liste): je Satz dazu (Drehzahl, links, Kühlung) der Operation; `werkzeuge`:
    ihre Werkzeugnummer."""
    aus = []
    pos = {"X": None, "Y": None, "Z": None}
    rund = dict.fromkeys(RUND)
    g93 = False
    for abschnitt in abschnitte:
        f = None
        umdrehen = pp._rund_umdrehen(abschnitt, info)
        for befehl in abschnitt.befehle:
            name, werte = (befehl.Name, befehl.Parameters) if hasattr(befehl, "Name") else befehl
            name = name.upper().replace("G0", "G", 1) if re.fullmatch(r"G0\d", name) else name
            name = {"G": "G0"}.get(name, name)
            if name in ("G93", "G94"):
                g93 = name == "G93"
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
                kuehl = abschnitt.kuehlung in ("Flood", "Mist")
                spindel.append((round(abschnitt.drehzahl), bool(abschnitt.rueckwaerts), kuehl))
            if werkzeuge is not None:
                werkzeuge.append((int(abschnitt.werkzeug), g93))
    return aus


_WORT = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")


def vorschubsaetze_programm(text, siemens=False, spindel=None, werkzeuge=None):
    """Dasselbe aus dem Programmtext, wie eine Steuerung ihn liest. `spindel` (eine Liste): je Satz
    dazu (Drehzahl, links, Kühlung), wie die Spindel da läuft (0: sie steht); `werkzeuge`: je Satz
    (T, H) – das gewechselte Werkzeug (T mit M6; eine Vorwahl ohne M6 zählt nicht) und die
    eingeschaltete Länge (G43 H, G49: 0)."""
    aus = []
    pos = {"X": None, "Y": None, "Z": None}
    rund = dict.fromkeys(RUND)
    art, f, maschine = "G0", None, False
    drehzahl, links, laeuft, kuehl = 0, False, False, False
    t_aktiv, h_aktiv, g93 = None, 0, False
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
        m6 = any(b == "M" and float(z) == 6.0 for b, z in woerter)
        for b, z in woerter:
            if b == "T" and m6:
                t_aktiv = round(float(z))
            elif b == "H" and 43.0 in g:
                h_aktiv = round(float(z))
            elif b == "S":
                drehzahl = round(float(z))
            elif b == "M" and float(z) in (3.0, 4.0):
                laeuft, links = True, float(z) == 4.0
            elif b == "M" and float(z) == 5.0:
                laeuft = False
            elif b == "M" and float(z) in (7.0, 8.0):
                kuehl = True
            elif b == "M" and float(z) == 9.0:
                kuehl = False
        if 49.0 in g:
            h_aktiv = 0
        if 93.0 in g or 94.0 in g:
            g93 = 93.0 in g
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
            spindel.append((drehzahl if laeuft else 0, links, kuehl))
        if werkzeuge is not None:
            werkzeuge.append((t_aktiv, h_aktiv, g93))
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
    """[(X, Y, Z, F, Bogen)] der Sätze im Vorschub eines Klartext-Programms (L, C, CP) – modal,
    Zahlen mit Vorzeichen, F nur, wenn es sich ändert; Fortsetzungszeilen der Zyklen übersprungen.
    Bogen: bei C und CP um einen Pol in XY (Pol X, Pol Y, im Uhrzeigersinn), sonst None."""
    aus = []
    pos = {"X": None, "Y": None, "Z": None}
    f = None
    pol = None
    for zeile in text.splitlines():
        if zeile.startswith("  "):
            continue
        satz = re.sub(r"^\d+ ", "", zeile).strip()
        if satz.startswith("CC "):
            pol = {a: float(w) for a, w in re.findall(r"\b([XYZ])([-+]\d+\.?\d*)", satz)}
            pol = [pol.get("X"), pol.get("Y")]
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
            aus.append((pos["X"], pos["Y"], pos["Z"], f, (*pol, ipa < 0)))
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
        bogen = None
        if satz.startswith("C ") and pol is not None and None not in pol:
            bogen = (*pol, "DR-" in satz)
        aus.append((pos["X"], pos["Y"], pos["Z"], f, bogen))
    return aus


def im_klartext(job_saetze, punkte):
    """None, wenn jeder Endpunkt des Jobs in derselben Folge im Klartext steht (dazwischen darf
    mehr stehen: der Vollkreis in zwei Hälften, die Schraube in Geraden) – mit demselben F."""
    k = 0
    for i, soll in enumerate(job_saetze):
        # Eine Gerade ist der nächste Satz; ein Bogen darf Zwischenpunkte haben (zwei Hälften,
        # die Schraube in Geraden).
        bis = len(punkte) if soll[0] in ("G2", "G3") else min(k + 1, len(punkte))
        anfang = k
        while k < bis and not all(
            abs(a - b) <= GENAU for a, b in zip(soll[1:4], punkte[k][:3], strict=True)
        ):
            k += 1
        if k >= bis:
            return f"Satz {i + 1} {soll} fehlt im Klartext"
        if punkte[k][3] is None or not math.isclose(soll[6], punkte[k][3], rel_tol=1e-3):
            return f"Satz {i + 1} F {punkte[k][3]} statt {soll[6]}"
        # Ein Bogen (auch in Hälften oder als CP): um die Mitte des Jobs, im Drehsinn des Jobs;
        # eine Gerade nie als Bogen.
        for q in punkte[anfang : k + 1]:
            if q[4] is None:
                continue
            if soll[0] not in ("G2", "G3"):
                return f"Satz {i + 1} {soll[0]}: im Klartext ein Bogen {q}"
            if (
                abs(q[4][0] - soll[4]) > GENAU
                or abs(q[4][1] - soll[5]) > GENAU
                or q[4][2] != (soll[0] == "G2")
            ):
                return f"Satz {i + 1} {soll[0]} Mitte {soll[4:6]}: im Klartext {q[4]}"
        k += 1
    return None


def _mitte_aus_r(anfang, ende, r, uhrzeiger, gross):
    """Die Mitte eines Bogens, wie woodWOP sie aus Anfang, Ende, R und DS rechnet: bis 180° liegt
    sie gegen den Uhrzeigersinn links der Sehne, im Uhrzeigersinn rechts; darüber andersherum."""
    dx, dy = ende[0] - anfang[0], ende[1] - anfang[1]
    sehne = math.hypot(dx, dy)
    h = math.sqrt(max(r * r - sehne * sehne / 4, 0.0))
    s = 1.0 if (not uhrzeiger) != gross else -1.0
    return anfang[0] + dx / 2 - s * h * dy / sehne, anfang[1] + dy / 2 + s * h * dx / sehne


def mpr_lesen(text, rohteil):
    """Die MPR-Datei, wie woodWOP sie fährt, zurück in Koordinaten des Jobs (woodWOP zählt ab der
    Ecke des Werkstücks, Z vom Boden): je Element KL/KA in der Folge der Bearbeitungen (Art, X, Y,
    Z, F je Minute, Werkzeug, Drehzahl, Kontur, Anfang, Mitte, im Uhrzeigersinn) – die Mitte aus
    Anfang, Ende, R und DS –, dazu die Bohrungen [(X, Y, Z, Werkzeug)]."""
    (x0, y0, z0), (_, _, z1) = rohteil
    konturen, makros = {}, []
    kontur = element = makro = None
    for zeile in text.splitlines():
        zeile = zeile.strip()
        if zeile.startswith("]") and zeile[1:].isdigit():
            kontur, element, makro = konturen.setdefault(int(zeile[1:]), []), None, None
        elif zeile.startswith("$E") and kontur is not None:
            element = {}
            kontur.append(element)
        elif zeile in ("KP", "KL", "KA") and element is not None:
            element["art"] = zeile
        elif zeile.startswith("<"):
            kontur = element = None
            treffer = re.match(r"<\d+\s+\\(\w+)\\", zeile)
            makro = {"name": treffer.group(1) if treffer else ""}
            makros.append(makro)
        elif "=" in zeile:
            schluessel, _, wert = zeile.partition("=")
            if element is not None:
                element[schluessel] = float(wert)
            elif makro is not None:
                makro[schluessel] = wert.strip('"')
    elemente, bohrungen = [], []
    for makro in makros:
        if makro["name"] == "Konturfraesen":
            n, _, erstes = makro["EA"].partition(":")
            letztes = makro["EE"].partition(":")[2]
            f = float(makro["F_"]) * 1000.0
            werkzeug, drehzahl = int(makro["TNO"]), float(makro.get("S_A", 0))
            vorher = None
            for e in konturen[int(n)][int(erstes) : int(letztes) + 1]:
                punkt = (e["X"] + x0, e["Y"] + y0, e["Z"] + z0)
                mitte, uhrzeiger = None, None
                if e["art"] == "KA":
                    uhrzeiger, gross = int(e["DS"]) in (0, 2), int(e["DS"]) in (2, 3)
                    mitte = _mitte_aus_r(vorher, punkt, e["R"], uhrzeiger, gross)
                if e["art"] != "KP":
                    elemente.append((e["art"], *punkt, f, werkzeug, drehzahl, int(n), vorher,
                                     mitte, uhrzeiger))  # fmt: skip
                vorher = punkt
        elif makro["name"] == "BohrVert":
            bohrungen.append((float(makro["XA"]) + x0, float(makro["YA"]) + y0,
                              z1 - float(makro["TI"]), int(makro["TNO"])))  # fmt: skip
    return elemente, bohrungen


def im_mpr(job_saetze, spindel, werkzeuge, elemente):
    """None, wenn jeder Vorschubsatz des Jobs in derselben Folge als Element steht (ein Bogen darf
    in Stücke bis 90° geteilt, eine Schraube in Geraden zerlegt sein): Endpunkt, Werkzeug, Drehzahl;
    ein Bogen in XY mit dem Drehsinn des Jobs und an jeder Stelle auf seinem Kreis, so wie woodWOP
    ihn aus R und DS fährt. Der Vorschub einer Kontur ist der kleinste ihrer Sätze."""
    k = 0
    f_je_kontur = {}
    for i, soll in enumerate(job_saetze):
        bogen = soll[0] in ("G2", "G3")
        bis = len(elemente) if bogen else min(k + 1, len(elemente))
        anfang = k
        while k < bis and not all(
            abs(a - b) <= GENAU for a, b in zip(soll[1:4], elemente[k][1:4], strict=True)
        ):
            k += 1
        if k >= bis:
            return f"Satz {i + 1} {soll} fehlt: {elemente[anfang : anfang + 2]}"
        for e in elemente[anfang : k + 1]:
            if e[5] != werkzeuge[i][0] or (spindel[i][0] > 0 and round(e[6]) != spindel[i][0]):
                return (
                    f"Satz {i + 1}: T{e[5]} S{e[6]:.0f} statt T{werkzeuge[i][0]} S{spindel[i][0]}"
                )
            f_je_kontur.setdefault(e[7], []).append((soll[6], e[4], i))
            if e[0] != "KA":
                continue
            if not bogen or e[10] != (soll[0] == "G2"):
                return f"Satz {i + 1} {soll[0]}: ein Bogen KA im Uhrzeigersinn={e[10]}"
            r_soll = math.hypot(soll[1] - soll[4], soll[2] - soll[5])
            w0 = math.atan2(e[8][1] - e[9][1], e[8][0] - e[9][0])
            w1 = math.atan2(e[2] - e[9][1], e[1] - e[9][0])
            winkel = ((w0 - w1) if e[10] else (w1 - w0)) % (2 * math.pi)
            r = math.hypot(e[1] - e[9][0], e[2] - e[9][1])
            for n in range(1, 8):
                w = w0 + (-1.0 if e[10] else 1.0) * winkel * n / 8
                q = (e[9][0] + r * math.cos(w), e[9][1] + r * math.sin(w))
                daneben = abs(math.hypot(q[0] - soll[4], q[1] - soll[5]) - r_soll)
                if daneben > 0.003:
                    return f"Satz {i + 1} {soll[0]}: der Bogen {daneben:.3f} mm neben dem Kreis"
        k += 1
    for nummer, paare in f_je_kontur.items():
        kleinster = min(f for f, _, _ in paare)
        if any(abs(f_ist - kleinster) > 0.06 for _, f_ist, _ in paare):
            return f"Kontur {nummer}: F {paare[0][1]} statt {kleinster} (der kleinste ihrer Sätze)"
    return None


def bohrungen_job(abschnitte):
    """[(X, Y, Z, Werkzeug)] der Bohrzyklen im Job."""
    aus, pos = [], {"X": None, "Y": None}
    for abschnitt in abschnitte:
        for befehl in abschnitt.befehle:
            name, werte = (befehl.Name, befehl.Parameters) if hasattr(befehl, "Name") else befehl
            for a in pos:
                if a in werte:
                    pos[a] = float(werte[a])
            if name.upper() in ("G81", "G82", "G83", "G73", "G85") and "Z" in werte:
                aus.append((pos["X"], pos["Y"], float(werte["Z"]), int(abschnitt.werkzeug)))
    return aus


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
        spindel_soll, werkzeug_soll = [], []
        soll = vorschubsaetze_job(abschnitte, fraese, spindel_soll, werkzeug_soll)
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
                # Bei jedem Vorschubsatz läuft die Spindel mit Drehzahl und Drehsinn der Operation,
                # die Kühlung wie an ihr – auch nach Messstopp, Wechsel und Einstieg hinter einer
                # Marke.
                spindel_ist, werkzeug_ist = [], []
                vorschubsaetze_programm(
                    programm.text, kennung == "siemens", spindel_ist, werkzeug_ist
                )
                # Das gewechselte Werkzeug und – wo die Steuerung G43 H braucht – seine Länge.
                mit_h = bool(pp.steuerung(kennung).laenge_ein)
                falsch_w = next(
                    (
                        (i, w, ist)
                        for i, (w, ist) in enumerate(zip(werkzeug_soll, werkzeug_ist, strict=True))
                        if ist[2] != w[1]  # G93 (1 ÷ Zeit) oder G94 (mm/min) wie im Job
                        or (kennung != "grbl" and (ist[0] != w[0] or (mit_h and ist[1] != w[0])))
                    ),
                    None,
                )
                pruefe(
                    not falsch_w, f"{datei} {job.Label} {kennung} {aenderung}: Werkzeug {falsch_w}"
                )
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
            # Die Werkzeuge in derselben Folge (TOOL CALL n; derselbe n hintereinander zählt einmal).

            def folge(nummern):
                return [n for i, n in enumerate(nummern) if i == 0 or n != nummern[i - 1]]

            gerufen = folge([int(n) for n in re.findall(r"TOOL CALL (\d+) ", programm.text)])
            soll_w = folge([int(a.werkzeug) for a in abschnitte if a.werkzeug])
            pruefe(gerufen == soll_w, f"{datei} {kennung}: Werkzeuge {gerufen} statt {soll_w}")
        if not rundum:
            # woodWOP (MPR, Homag/Weeke): die Konturen und Bohrungen zurück in Koordinaten des
            # Jobs – jeder Vorschubsatz, jeder Bogen so, wie die Maschine ihn aus R und DS fährt.
            box = job.Stock.Shape.BoundBox
            rohteil = ((box.XMin, box.YMin, box.ZMin), (box.XMax, box.YMax, box.ZMax))
            programm = pp.programm(
                abschnitte, pp.steuerung("woodwop"), fraese, job.Label, rohteil=rohteil
            )
            elemente, bohrungen = mpr_lesen(programm.text, rohteil)
            unterschied = im_mpr(soll, spindel_soll, werkzeug_soll, elemente)
            pruefe(not unterschied, f"{datei} {job.Label} woodwop: {unterschied}")
            soll_b = bohrungen_job(abschnitte)
            pruefe(
                len(soll_b) == len(bohrungen)
                and all(
                    a[3] == b[3]
                    and all(abs(u - v) <= GENAU for u, v in zip(a[:3], b[:3], strict=True))
                    for a, b in zip(soll_b, bohrungen, strict=True)
                ),
                f"{datei} {job.Label} woodwop: Bohrungen {bohrungen[:3]} statt {soll_b[:3]}",
            )
            print(
                ascii(f"{job.Label} woodWOP: {len(elemente)} Elemente, {len(bohrungen)} Bohrungen")
            )
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
            # Eine Operation, die nichts fräst (nur Eilgänge): kein Werkzeugwechsel dafür, ein
            # Hinweis; ein Messstopp (nur M-Befehle) bleibt.
            from Path.Op import Custom

            leer = Custom.Create("Leer", parentJob=job)
            leer.ToolController = job.Operations.Group[0].ToolController
            leer.Source = "Text"
            leer.Gcode = ["G0 X0 Y0 Z20", "G0 Z30"]
            doc.recompute()
            pruefe(
                pp.ohne_arbeit(leer) and not pp.ohne_arbeit(job.Operations.Group[0]),
                "ohne_arbeit",
            )
            mit_leer = pp.abschnitte(job)
            p_leer = pp.programm(mit_leer, pp.steuerung("fanuc"), fraese, "L")
            pruefe(
                mit_leer[-1].werkzeug == 0
                and p_leer.text.count(" M6")
                == pp.programm(abschnitte, pp.steuerung("fanuc"), fraese, "L").text.count(" M6")
                and any("fräst nichts" in h for h in p_leer.hinweise),
                f"leere Operation: {mit_leer[-1]} {p_leer.hinweise}",
            )
            doc.removeObject(leer.Name)
            doc.recompute()
            # Gemischt: Flut mit Linkslauf, Nebel, ohne Kühlung mit anderer Drehzahl – Spindel und
            # Kühlung bei jedem Vorschubsatz wie an der Operation.
            arten = (("Flood", True, 1800.0), ("Mist", False, 2255.0), ("None", False, 3100.0))
            gemischt = [
                dataclasses.replace(a, kuehlung=k, rueckwaerts=r, drehzahl=d)
                for a, (k, r, d) in zip(abschnitte, arten, strict=False)
            ]
            g_soll = []
            vorschubsaetze_job(gemischt, fraese, g_soll)
            for kennung in ("linuxcnc", "fanuc", "haas", "mach", "mazak", "grbl", "siemens"):
                for aenderung in ({}, {"marken": False}):
                    g_ist = []
                    text_g = pp.programm(
                        gemischt, pp.steuerung(kennung, aenderung), fraese, "G"
                    ).text
                    vorschubsaetze_programm(text_g, kennung == "siemens", g_ist)
                    falsch = next(
                        (
                            (i, a, b)
                            for i, (a, b) in enumerate(zip(g_soll, g_ist, strict=True))
                            if a != b
                        ),
                        None,
                    )
                    pruefe(not falsch, f"gemischt {kennung} {aenderung}: {falsch}")
            # Die Länge des vorigen Werkzeugs (G43 H mit der falschen Nummer) fällt auf.
            w_soll = []
            vorschubsaetze_job(abschnitte, fraese, None, w_soll)
            letztes_h = re.findall(r"G43 H(\d+)", text)[-1]
            falsches_h = text[::-1].replace(f"G43 H{letztes_h}"[::-1], "G43 H99"[::-1], 1)[::-1]
            w_ist = []
            vorschubsaetze_programm(falsches_h, False, None, w_ist)
            pruefe(
                any(i[1] != w[0] for w, i in zip(w_soll, w_ist, strict=True)),
                "falsches H übersehen",
            )
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
            # Ein Pol 0,01 mm daneben, ein Bogen im falschen Drehsinn – die Endpunkte bleiben.
            cc = re.search(r"^\d+ CC X([-+]\d+\.\d+)", text, re.M)
            dr = re.search(r"^\d+ C [^\n]*DR([-+])", text, re.M)
            pruefe(cc is not None and dr is not None, "Klartext der Platte ohne Bogen")
            if cc is not None and dr is not None:
                pol = text[: cc.start(1)] + f"{float(cc.group(1)) + 0.01:+.3f}" + text[cc.end(1) :]
                pruefe(im_klartext(soll, klartext_punkte(pol)), "Klartext: Pol daneben übersehen")
                anders = "+" if dr.group(1) == "-" else "-"
                falsch_dr = text[: dr.start(1)] + anders + text[dr.end(1) :]
                pruefe(
                    im_klartext(soll, klartext_punkte(falsch_dr)), "Klartext: Drehsinn übersehen"
                )
    FreeCAD.closeDocument(doc.Name)

if fehler:
    raise AssertionError("\n".join(fehler[:20]))
print()
print("OK", os.path.basename(__file__))
