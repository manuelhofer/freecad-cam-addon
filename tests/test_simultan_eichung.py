# SPDX-License-Identifier: LGPL-2.1-or-later
"""Eichung der Simultan-Prüfung an bekannter Geometrie (P-2026-10-09-03): ebene Fläche, Kugel
Ø 4, Zeilen so weit, dass genau 0,02 mm Kamm stehen bleibt. fahren() muss das messen, deckung()
muss die Zeilen annehmen, die bahn_grathoehe() ergibt, und zu weite ablehnen."""

import math
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from camaddon import bahn as bn
from camaddon import fraeserform as ff
from camaddon import restmaterial as rm
from camaddon import simultan_abtrag as sa

R, GRAT = 2.0, 0.02


def zeilenabstand(grathoehe):
    return 2.0 * math.sqrt(2.0 * R * grathoehe - grathoehe * grathoehe)


def zeilen(abstand, z=4.0):
    """Zeilen hin und her über |x| ≤ 5,5 bei y von −5,6 bis 5,6 (über die Ebene hinaus, damit
    ihr Rand gedeckt ist), die Spitze auf der Ebene z."""
    punkte, y, richtung = [], -5.6, 1
    while y <= 5.6 + 1e-9:
        punkte += [bn.Punkt(False, -5.5 * richtung, y, z), bn.Punkt(False, 5.5 * richtung, y, z)]
        richtung, y = -richtung, y + abstand
    return punkte


def ebene(groesse):
    """Die Ebene z = 4 über |x|, |y| ≤ 5 als Dreiecke der Kantenlänge `groesse`."""
    xs = np.arange(-5.0, 5.0 + 1e-9, groesse)
    dreiecke = []
    for i in range(len(xs) - 1):
        for j in range(len(xs) - 1):
            a, b = (xs[i], xs[j], 4.0), (xs[i + 1], xs[j], 4.0)
            c, d = (xs[i + 1], xs[j + 1], 4.0), (xs[i], xs[j + 1], 4.0)
            dreiecke += [[a, b, c], [a, c, d]]
    return np.array(dreiecke)


genau = zeilenabstand(GRAT)
assert abs(genau - 0.5643) < 1e-3, genau
# fahren(): der Kamm zwischen den Zeilen ist die Grathöhe – im 0,1- und im 0,05-mm-Raster.
for raster in (0.1, 0.05):
    quader = rm.Quader(-6, 6, -6, 6, 0, 5, schritt=raster)
    sa.fahren(quader, zeilen(genau), ff.kugel(R), 0.6, 1.2)
    innen = (np.abs(quader.x)[:, None] <= 3.0) & (np.abs(quader.y)[None, :] <= 3.0)
    kamm = float(np.max(quader.h[innen] - 4.0))
    assert GRAT - 0.002 <= kamm <= GRAT + 1e-6, f"Raster {raster}: Kamm {kamm}"
# deckung(): mit der Feinheit aus bahn_grathoehe deckt die Bahn jede Zelle (Dreiecke bis 2 mm),
# zu weite Zeilen nicht. Am genauen Abstand (Kamm 0,02) lehnt sie ab – ihre Reserve von 0,002 mm
# an der Prüfkugel –, Dreiecke ab 5 mm Kantenlänge immer (die Unterteilung reicht nicht); darum
# rechnet der Vergleich feiner, als die Grathöhe verlangt.
fein = sa.bahn_grathoehe(GRAT)
assert abs(fein - 0.015) < 1e-9, fein
for groesse in (2.0, 1.0, 0.5, 0.2):
    assert sa.deckung(ebene(groesse), zeilen(zeilenabstand(fein)), R, GRAT) == 0, groesse
    assert sa.deckung(ebene(groesse), zeilen(genau * 1.1), R, GRAT) > 0, groesse
assert sa.deckung(ebene(1.0), zeilen(genau), R, GRAT) > 0, "am genauen Abstand nimmt sie an?"
assert sa.deckung(ebene(1.0), zeilen(0.52), R, GRAT) == 0, "0,52 mm bei 1-mm-Dreiecken"
assert sa.deckung(ebene(5.0), zeilen(zeilenabstand(fein)), R, GRAT) > 0, "5-mm-Dreiecke"
print("OK", os.path.basename(__file__))
