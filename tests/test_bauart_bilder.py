# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prüft, dass jede Bauart im Fenster „Neue Maschine“ ihr Bild hat (resources/icons/bauart_*.svg)
und jeder Weg der Fragen im Assistenten „Bearbeitung“ seines (weg_*.svg) – und dass sie sich lesen
lassen. Aufruf: freecadcmd tests/test_bauart_bilder.py"""

import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from camaddon import beispielmaschine, symbol  # noqa: E402

fehler = []


def pruefe(wahr, text):
    print(ascii(("ok   " if wahr else "FEHLER ") + text))
    if not wahr:
        fehler.append(text)


for art in beispielmaschine.ARTEN:
    pfad = symbol(f"bauart_{art}.svg")
    pruefe(os.path.exists(pfad), f"Bild für {art}: {os.path.basename(pfad)}")
    if os.path.exists(pfad):
        wurzel = ET.parse(pfad).getroot()
        pruefe(wurzel.tag.endswith("svg") and len(wurzel) >= 4, f"{art}: lesbares SVG mit Inhalt")

# Die Wege der Fragen „Wie soll das Material raus?“ und „Die Wände unter dem Rand“.
for weg in ("vorbohren", "helix", "tauchen", "flanke", "spirale"):
    pfad = symbol(f"weg_{weg}.svg")
    pruefe(os.path.exists(pfad), f"Bild für den Weg {weg}: {os.path.basename(pfad)}")
    if os.path.exists(pfad):
        wurzel = ET.parse(pfad).getroot()
        pruefe(wurzel.tag.endswith("svg") and len(wurzel) >= 3, f"{weg}: lesbares SVG mit Inhalt")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
