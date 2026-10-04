# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das fertige Programm Satz für Satz nachlesen – wie eine Steuerung es läse – und melden, was an
der Maschine schiefginge (Manuel, 2026-10-04: „verbessere die Postprozessoren bis ins Extreme“;
er kann G-Code nicht selbst prüfen). Gefunden hat so etwas zuerst P-2026-10-04-51: Nach dem
Werkzeugwechsel fehlte die Längenkorrektur.

Gelesen wird der Text, den postprozessor.programm schreibt: Satznummern und Kommentare weg, dann
Wort für Wort – G- und M-Befehle, Adressen mit Zahl (Siemens auch „C4=12.5“). Gezählt wird modal
wie an der Steuerung: Bewegungsart, Vorschub, Spindel, Werkzeug und seine Länge, Ebene, G93/G94.

Geprüft (je Fund ein Befund mit Zeile und Satz):
- LAENGE: eine Bewegung in Z (an der Drehmaschine jede) ohne eingeschaltete Werkzeuglänge – nach
  dem Wechsel bis G43 (Siemens: D0 bis D1 oder bis zum nächsten Wechsel).
- SPINDEL: ein Satz im Vorschub (G1, G2, G3), während die Spindel steht.
- VORSCHUB: ein Satz im Vorschub ohne gültiges F – keins seit G93/G94 oder F0; in G93 (1 ÷
  Zeit) muss F in jedem Satz stehen (LinuxCNC und die meisten Steuerungen).
- KREIS: ein Bogen, dessen Mitte vom Anfang und vom Ende verschieden weit liegt (mehr als
  KREIS_TOLERANZ) – die Steuerung bliebe mit Alarm stehen.
- DOPPELT: derselbe Satz im Vorschub zweimal hintereinander (nichts zu fahren).
- ENDE: kein Programmende (M30 oder M2).
- ZEICHEN: ein Zeichen außerhalb von ASCII (mit `nur_ascii`: Fanuc, Haas, Mach brechen ab).

Läuft ohne Oberfläche und ohne FreeCAD.
"""

import math
import re
from dataclasses import dataclass, field

KREIS_TOLERANZ = 0.002  # mm – so weit dürfen die Abstände zur Mitte am Anfang und Ende abweichen
LAENGE, SPINDEL, VORSCHUB, KREIS, DOPPELT, ENDE, ZEICHEN = (
    "laenge",
    "spindel",
    "vorschub",
    "kreis",
    "doppelt",
    "ende",
    "zeichen",
)


@dataclass
class Befund:
    art: str  # LAENGE, SPINDEL …
    zeile: int  # 1, 2 … im Programm
    satz: str


@dataclass
class Pruefung:
    befunde: list = field(default_factory=list)
    saetze: int = 0  # Bewegungssätze

    def von(self, art):
        return [b for b in self.befunde if b.art == art]


def _ohne_kommentar(zeile, siemens):
    zeile = re.sub(r"\([^)]*\)", "", zeile)
    if siemens or ";" in zeile:
        zeile = zeile.split(";", 1)[0]
    return re.sub(r"^\s*N\d+\s*", "", zeile).strip()


def _zerlegen(satz):
    """(G-Befehle, M-Befehle, {Adresse: Zahl}) eines Satzes."""
    g, m, werte = [], [], {}
    for teil in satz.split():
        treffer = re.fullmatch(r"([A-Z]+)(\d*)=(-?[\d.]+)", teil.upper())
        if treffer:
            werte[treffer.group(1) + treffer.group(2)] = float(treffer.group(3))
            continue
        treffer = re.fullmatch(r"([A-Z])(-?[\d.]+)", teil.upper())
        if not treffer:
            continue
        adresse, zahl = treffer.group(1), treffer.group(2)
        if adresse == "G":
            g.append(zahl.lstrip("0") or "0")
        elif adresse == "M":
            m.append(zahl.lstrip("0") or "0")
        else:
            try:
                werte[adresse] = float(zahl)
            except ValueError:
                continue
    return g, m, werte


def pruefe(text, siemens=False, drehmaschine=False, laenge_mit_wechsel=False, nur_ascii=False):
    """Pruefung des Programms `text`. `siemens`: Kommentare mit „;“, die Länge kommt mit dem
    Wechsel (D1) und geht mit D0; `laenge_mit_wechsel`: auch sonst nimmt der Wechsel die Länge
    mit (eine Steuerung ohne G43); `drehmaschine`: die Länge zählt in jeder Achse; `nur_ascii`:
    jedes Zeichen außerhalb von ASCII ist ein Befund."""
    pruefung = Pruefung()
    befunde = pruefung.befunde
    bewegung = None  # "0", "1", "2", "3"
    f = None  # gültiger Vorschub
    spindel = False
    laenge = True  # bis zum ersten Wechsel: wie eingerichtet
    ebene = "17"
    g93 = False
    stand = {}
    davor = None
    ende = False
    for nummer, roh in enumerate(text.splitlines(), start=1):
        if nur_ascii and not roh.isascii():
            befunde.append(Befund(ZEICHEN, nummer, roh))
        satz = _ohne_kommentar(roh, siemens)
        if not satz or satz.startswith("%"):
            continue
        g, m, werte = _zerlegen(satz)
        if siemens:
            if re.search(r"\bD0\b", satz.upper()):
                laenge = False
            if re.search(r"\bD[1-9]\d*\b", satz.upper()):
                laenge = True
        for code in g:
            if code in ("0", "1", "2", "3"):
                bewegung = code
            elif code in ("17", "18", "19"):
                ebene = code
            elif code in ("93", "94", "95"):
                f = None
                g93 = code == "93"
            elif code == "43" or code.startswith("43."):
                laenge = True
            elif code == "49":
                laenge = False
        for adresse, wert in werte.items():
            # Siemens: „M1=3“ – Spindel 1 rechts, „M1=5“ aus (der Antrieb an der Drehmaschine).
            if adresse[0] == "M" and adresse[1:].isdigit():
                m.append(f"{wert:g}")
        for code in m:
            if code in ("3", "4", "133", "134"):  # M133/M134: Haas, angetriebenes Werkzeug
                spindel = True
            elif code in ("5", "135"):
                spindel = False
            elif code == "6":
                laenge = siemens or laenge_mit_wechsel
            elif code in ("30", "2"):
                ende = True
        if drehmaschine and "T" in werte:
            # „T0101“ (Fanuc, Haas, Mach) nimmt die Korrektur mit; LinuxCNC erst mit G43.
            laenge = siemens or laenge_mit_wechsel
        if "F" in werte:
            f = werte["F"] if werte["F"] > 0 else None
        if siemens and re.match(r"T\S*\s+D[1-9]", satz.upper()):
            laenge = True  # Drehmaschine: „T1 D1“
        if re.search(r"\bG53\b|\bSUPA\b|\bG75\b|\bG28\b", satz.upper()):
            continue  # Maschinenkoordinaten: ohne Länge gefahren, ändert den Stand im WKS nicht
        achsen = {k: v for k, v in werte.items() if k[0] in "XYZABCUVW" and len(k) <= 2}
        if not achsen or bewegung is None:
            continue
        pruefung.saetze += 1
        z_bewegt = any(k.startswith("Z") for k in achsen) or (drehmaschine and achsen)
        if z_bewegt and not laenge:
            befunde.append(Befund(LAENGE, nummer, roh))
        if bewegung in ("1", "2", "3"):
            if not spindel:
                befunde.append(Befund(SPINDEL, nummer, roh))
            if f is None or (g93 and "F" not in werte):
                befunde.append(Befund(VORSCHUB, nummer, roh))
            if satz == davor:
                befunde.append(Befund(DOPPELT, nummer, roh))
        if bewegung in ("2", "3") and "R" not in werte:
            _kreis(befunde, nummer, roh, stand, werte, ebene)
        stand.update({k[0]: v for k, v in achsen.items()})
        davor = satz
    if not ende:
        befunde.append(Befund(ENDE, 0, ""))
    return pruefung


def _kreis(befunde, nummer, roh, stand, werte, ebene):
    a, b, i, j = {
        "17": ("X", "Y", "I", "J"),
        "18": ("Z", "X", "K", "I"),
        "19": ("Y", "Z", "J", "K"),
    }[ebene]
    if a not in stand or b not in stand:
        return
    mitte_a = stand[a] + werte.get(i, 0.0)
    mitte_b = stand[b] + werte.get(j, 0.0)
    ende_a, ende_b = werte.get(a, stand[a]), werte.get(b, stand[b])
    r0 = math.hypot(stand[a] - mitte_a, stand[b] - mitte_b)
    r1 = math.hypot(ende_a - mitte_a, ende_b - mitte_b)
    if abs(r0 - r1) > KREIS_TOLERANZ:
        befunde.append(Befund(KREIS, nummer, f"{roh}  (r {r0:.4f} / {r1:.4f})"))
