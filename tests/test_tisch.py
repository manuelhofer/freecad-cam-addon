# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prüft gui_tisch.masse: Die Platte liegt unter dem Kasten, steht rundum über und ist nie hauchdünn.
Aufruf: freecadcmd tests/test_tisch.py"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from camaddon import gui_tisch as gt  # noqa: E402

fehler = []


def pruefe(wahr, text):
    print(ascii(("ok   " if wahr else "FEHLER ") + text))
    if not wahr:
        fehler.append(text)


mx, my, oben, lx, ly, dicke = gt.masse((0.0, 0.0, -30.0, 100.0, 80.0, 0.0))
pruefe((mx, my) == (50.0, 40.0), f"mittig unter dem Kasten: {mx}, {my}")
pruefe(oben == -30.0, f"Oberkante an der Unterkante des Kastens: {oben}")
pruefe(lx == 150.0 and ly == 130.0, f"rundum ein Viertel der größeren Kante über: {lx} x {ly}")
pruefe(5.0 < dicke < 6.0, f"Dicke 4 % der Diagonale: {dicke}")
_mx, _my, _oben, _lx, _ly, dicke = gt.masse((0.0, 0.0, 0.0, 2.0, 2.0, 1.0))
pruefe(dicke == 0.5, f"ein winziges Teil: mindestens 0,5 mm dick: {dicke}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
