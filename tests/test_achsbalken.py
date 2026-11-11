# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prüft gui_reichweite.balken_stellen: wo auf dem Balken einer Achse ihre Grenzen und der Bedarf
der Bahn liegen – und ob es reicht. Aufruf: freecadcmd tests/test_achsbalken.py"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from camaddon import gui_reichweite as gr  # noqa: E402

fehler = []


def pruefe(wahr, text):
    print(ascii(("ok   " if wahr else "FEHLER ") + text))
    if not wahr:
        fehler.append(text)


g0, g1, v0, v1, reicht = gr.balken_stellen(-100.0, 100.0, -250.0, 250.0)
pruefe((g0, g1) == (0.0, 1.0), f"in den Grenzen: die Grenzen füllen den Balken ({g0}, {g1})")
pruefe(abs(v0 - 0.3) < 1e-9 and abs(v1 - 0.7) < 1e-9 and reicht, f"Bedarf mittig: {v0}, {v1}")
g0, g1, v0, v1, reicht = gr.balken_stellen(-470.0, -100.0, -250.0, 250.0)
pruefe(not reicht, "über der Grenze: reicht nicht")
pruefe(v0 == 0.0 and g0 > 0.0 and g1 == 1.0, f"der Balken zeigt auch, was darüber hinausgeht: {g0}")
g0, g1, v0, v1, reicht = gr.balken_stellen(40.0, 10.0, -250.0, 250.0)
pruefe(v0 < v1 and reicht, "von und bis vertauscht: sortiert")
for grenzen in ((None, None), (float("-inf"), float("inf")), (5.0, 5.0)):
    g0, g1, v0, v1, reicht = gr.balken_stellen(0.0, 720.0, *grenzen)
    pruefe((g0, g1) == (0.0, 1.0) and reicht and v0 < v1, f"ohne endliche Grenzen {grenzen}: frei")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
