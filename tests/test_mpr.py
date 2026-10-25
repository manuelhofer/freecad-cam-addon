# SPDX-License-Identifier: LGPL-2.1-or-later
# woodWOP-MPR für Homag und Weeke (P-2026-10-25-52; Manuel, 2026-10-25, zu Herberts Homag: „mach
# das einfach“): Der Postprozessor schreibt Konturen und Bearbeitungen statt G-Code – das
# Werkstück aus dem Rohteil, Z vom Boden, Bögen mit R und DS, ein Vollkreis in zwei Hälften, der
# Vorschub in m/min (wechselt er in einer Kontur: der kleinere, mit Hinweis), Bohrungen als
# BohrVert mit der Tiefe ab Oberseite; erst alle Konturen, dann die Bearbeitungen, „!“ am Ende.
# Nachgelesen: nichts am richtigen Programm, Befunde an absichtlich kaputten.
# Ausführen: freecadcmd tests/test_mpr.py

import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import Path  # noqa: E402

from camaddon import (
    mpr,  # noqa: E402
    sprache,  # noqa: E402
)
from camaddon import postprozessor as pp  # noqa: E402
from camaddon import programm_pruefen as prp  # noqa: E402

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)
        print("FEHLER:", text)


def element(zeilen, nummer, kontur=1):
    """Die Zeilen des Elements $E`nummer` der Kontur ]`kontur` bis zur Leerzeile."""
    i = zeilen.index(f"]{kontur}")
    i = zeilen.index(f"$E{nummer}", i)
    j = zeilen.index("", i)
    return zeilen[i + 1 : j]


def makro(zeilen, name, nummer=0):
    """Die Zeilen des `nummer`-ten Makros <… \\name\\ bis zur Leerzeile."""
    anfaenge = [i for i, z in enumerate(zeilen) if z.startswith("<") and f"\\{name}\\" in z]
    i = anfaenge[nummer]
    j = zeilen.index("", i)
    return zeilen[i + 1 : j]


sprache.setze_sprache("de")
C = Path.Command
ROHTEIL = ((0.0, 0.0, -20.0), (300.0, 200.0, 0.0))  # oben Z 0, 20 dick
tasche = pp.Abschnitt(
    "Tasche",
    3,
    18000.0,
    False,
    "None",
    [
        C("(Tasche)"),
        C("G0", {"X": 10.0, "Y": 5.0, "Z": 5.0}),
        C("G1", {"Z": -2.0, "F": 50.0}),  # FreeCAD: mm/s – 3000 mm/min
        C("G1", {"X": 20.0, "F": 100.0}),
        C("G2", {"X": 30.0, "Y": 5.0, "I": 5.0, "J": 0.0, "F": 100.0}),  # Halbkreis R 5
        C("G3", {"X": 30.0, "Y": 5.0, "I": -5.0, "J": 0.0}),  # Vollkreis
        C("G0", {"Z": 5.0}),
        C("G0", {"X": 50.0, "Y": 50.0}),
        C("G1", {"Z": -5.0, "F": 50.0}),
        C("G1", {"X": 60.0, "Y": 50.0}),
        C("G0", {"Z": 5.0}),
    ],
    "Fräser Ø 12",
)
bohren = pp.Abschnitt(
    "Bohren",
    5,
    3000.0,
    False,
    "None",
    [
        C("G0", {"Z": 20.0}),
        C("G98"),
        C("G0", {"X": 100.0, "Y": 100.0}),
        C("G0", {"Z": 5.0}),
        C("G81", {"X": 100.0, "Y": 100.0, "Z": -12.0, "R": 2.0, "F": 2.0}),
        C("G81", {"X": 120.0, "Y": 100.0, "Z": -12.0, "R": 2.0, "F": 2.0}),
        C("G80"),
        C("G0", {"Z": 20.0}),
    ],
    "Bohrer Ø 5",
)
s = pp.steuerung("woodwop")
pruefe(s.dialekt == "mpr" and s.endung == ".mpr", f"Steuerung: {s.dialekt} {s.endung}")
fraese = pp.Maschineninfo("Fräse")
prog = pp.programm([tasche, bohren], s, fraese, "Platte", rohteil=ROHTEIL)
z = prog.zeilen

# Kopf und Werkstück
pruefe(z[0] == "[H" and 'VERSION="4.0"' in z and 'MAT="HOMAG"' in z, f"Kopf: {z[:5]}")
pruefe('L="300"' in z and 'B="200"' in z and 'D="20"' in z, "Variablen L, B, D")
pruefe(all(x in z for x in ("<100 \\Werkstck\\", 'LA="L"', 'BR="B"', 'DI="D"')), "Werkstück")

# Kontur 1: Anfang über dem Teil, Z vom Boden (5 → 25, −2 → 18)
pruefe(element(z, 0) == ["KP", "X=10", "Y=5", "Z=25"], f"KP: {element(z, 0)}")
pruefe(element(z, 1) == ["KL", "X=10", "Y=5", "Z=18"], f"Eintauchen: {element(z, 1)}")
pruefe(element(z, 2) == ["KL", "X=20", "Y=5", "Z=18"], f"Gerade: {element(z, 2)}")
pruefe(element(z, 3) == ["KA", "X=30", "Y=5", "Z=18", "R=5.001", "DS=0"], f"G2: {element(z, 3)}")
pruefe(element(z, 4) == ["KA", "X=20", "Y=5", "Z=18", "R=5.001", "DS=1"], f"G3 1: {element(z, 4)}")
pruefe(element(z, 5) == ["KA", "X=30", "Y=5", "Z=18", "R=5.001", "DS=1"], f"G3 2: {element(z, 5)}")
pruefe(element(z, 2, kontur=2) == ["KL", "X=60", "Y=50", "Z=15"], "Kontur 2")

# Die Bearbeitungen nach allen Konturen, in ihrer Folge
letzte_kontur = max(i for i, x in enumerate(z) if x.startswith("]"))
erstes_makro = min(i for i, x in enumerate(z) if x.startswith("<105") or x.startswith("<102"))
pruefe(letzte_kontur < erstes_makro, "Konturen vor den Bearbeitungen")
k1 = makro(z, "Konturfraesen", 0)
for soll in ('EA="1:0"', 'EE="1:5"', 'MDA="SEN"', 'RK="NOWRK"', 'ZA="@0"', 'TNO="3"', 'F_="3"',
             'SM="1"', 'S_A="18000"'):  # fmt: skip
    pruefe(soll in k1, f"Konturfräsen 1 ohne {soll}: {k1}")
k2 = makro(z, "Konturfraesen", 1)
pruefe('EA="2:0"' in k2 and 'EE="2:2"' in k2 and 'F_="3"' in k2, f"Konturfräsen 2: {k2}")
b1 = makro(z, "BohrVert", 0)
for soll in ('XA="100"', 'YA="100"', 'TI="12"', 'TNO="5"', 'F_="0.12"', 'S_A="3000"'):
    pruefe(soll in b1, f"BohrVert ohne {soll}: {b1}")
pruefe('XA="120"' in makro(z, "BohrVert", 1), "zweite Bohrung")
pruefe(z[-1] == "!" and "<101 \\Kommentar\\" in z and 'KM="Platte"' in z, f"Ende: {z[-6:]}")
pruefe(all(x.isascii() for x in z), "nur ASCII")
pruefe(
    any("woodWOP: Eine Kontur hat nur einen Vorschub – an 1 Konturen" in h for h in prog.hinweise),
    f"Hinweis Vorschub: {prog.hinweise}",
)
pruefe(prog.saetze == 9, f"Sätze: {prog.saetze}")  # 5 + 2 Elemente, 2 Bohrungen
pruefe(mpr.text(z).count("\r\n") == len(z), "CR LF")
befunde, saetze = pp.nachlesen(prog, s, fraese)
pruefe(not befunde and saetze == 9, f"nachgelesen: {[(b.art, b.satz) for b in befunde]}")

# Weeke: nur der Maschinentyp anders
weeke = pp.programm([tasche], pp.steuerung("woodwop_weeke"), fraese, "P", rohteil=ROHTEIL)
pruefe('MAT="WEEKE"' in weeke.zeilen, "Weeke")

# Eine Schraube (Helix): in Geraden; Rundachsen: Hinweis
helix = pp.Abschnitt(
    "Helix",
    3,
    18000.0,
    False,
    "None",
    [
        C("G0", {"X": 15.0, "Y": 10.0, "Z": 2.0}),
        C("G2", {"X": 15.0, "Y": 10.0, "Z": -1.0, "I": -5.0, "J": 0.0, "F": 20.0}),
        C("G0", {"Z": 5.0}),
    ],
)
ph = pp.programm([helix], s, fraese, "H", rohteil=ROHTEIL)
kl = [x for x in ph.zeilen if x == "KL"]
pruefe(len(kl) > 20 and "KA" not in ph.zeilen, f"Schraube: {len(kl)} Geraden")
pruefe(any("in Geraden zerlegt" in h for h in ph.hinweise), f"Hinweis Schraube: {ph.hinweise}")
rund = pp.Abschnitt("Rund", 3, 1000.0, False, "None",
                    [C("G0", {"X": 0.0, "Y": 0.0, "Z": 5.0}),
                     C("G1", {"X": 10.0, "A": 30.0, "F": 10.0})])  # fmt: skip
pr = pp.programm([rund], s, fraese, "R", rohteil=ROHTEIL)
pruefe(any("Rundachsen" in h for h in pr.hinweise), f"Hinweis Rundachsen: {pr.hinweise}")

# Nachgelesen: absichtlich kaputt
text = prog.text
kaputt = {
    prp.ENDE: text.replace("\n!\n", "\n"),
    prp.KREIS: text.replace("R=5.001", "R=4"),
    "nummer": text.replace('EE="1:5"', 'EE="1:9"'),
    prp.VORSCHUB: text.replace('F_="0.12"', 'F_="0"'),
}
for art, falsch in kaputt.items():
    arten = {b.art for b in mpr.pruefe(falsch).befunde}
    pruefe(art in arten, f"nachgelesen {art}: {arten}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
