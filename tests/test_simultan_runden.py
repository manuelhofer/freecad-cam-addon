# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Runden des Simultanvergleichs (P-2026-10-09-04): ohne „Alle Kombinationen“ je Kugel, die
größte zuerst, drei Stufen – entlang der Fläche frei, die übrigen Richtungen frei, alle Richtungen
mit den festen Anstellungen; mit allem eine Runde."""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from camaddon import simultan_planung as sp


class Kugel:
    def __init__(self, name, radius):
        self.name, self.radius = name, radius

    def __repr__(self):
        return self.name


k2, k3, k6 = Kugel("k2", 2.0), Kugel("k3", 3.0), Kugel("k6", 6.0)
controller = [k2, k6, k3]


def runden(richtungen=sp.RICHTUNGEN, anstellungen=sp.ANSTELLUNGEN, alle=False):
    return list(sp._runden(controller, lambda k: k.radius, richtungen, anstellungen, alle))


frei = ("frei", "frei_gesamt")
uebrige = ("x", "y", "spirale", "aequidistant")
assert runden(alle=True) == [([k2, k6, k3], sp.RICHTUNGEN, sp.ANSTELLUNGEN)]
assert runden(alle=True, richtungen=("x",), anstellungen=("X",)) == [([k2, k6, k3], ("x",), ("X",))]
assert runden() == [
    ([k6], ("flaeche",), frei),
    ([k6], uebrige, frei),
    ([k6], sp.RICHTUNGEN, ("X", "Y")),
    ([k3], ("flaeche",), frei),
    ([k3], uebrige, frei),
    ([k3], sp.RICHTUNGEN, ("X", "Y")),
    ([k2], ("flaeche",), frei),
    ([k2], uebrige, frei),
    ([k2], sp.RICHTUNGEN, ("X", "Y")),
]
# Ohne „flaeche“ beginnt die erste Richtung; ohne feste Anstellungen gibt es keine dritte Stufe.
assert runden(richtungen=("x", "y"), anstellungen=("frei",)) == [
    ([k6], ("x",), ("frei",)),
    ([k6], ("y",), ("frei",)),
    ([k3], ("x",), ("frei",)),
    ([k3], ("y",), ("frei",)),
    ([k2], ("x",), ("frei",)),
    ([k2], ("y",), ("frei",)),
]
# Nur feste Anstellungen: sie sind dann die einzige Stufe.
assert runden(richtungen=("flaeche",), anstellungen=("X", "Y")) == [
    ([k6], ("flaeche",), ("X", "Y")),
    ([k3], ("flaeche",), ("X", "Y")),
    ([k2], ("flaeche",), ("X", "Y")),
]
assert runden(richtungen=("y", "flaeche"), anstellungen=("Y", "frei_gesamt")) == [
    ([k6], ("flaeche",), ("frei_gesamt",)),
    ([k6], ("y",), ("frei_gesamt",)),
    ([k6], ("y", "flaeche"), ("Y",)),
    ([k3], ("flaeche",), ("frei_gesamt",)),
    ([k3], ("y",), ("frei_gesamt",)),
    ([k3], ("y", "flaeche"), ("Y",)),
    ([k2], ("flaeche",), ("frei_gesamt",)),
    ([k2], ("y",), ("frei_gesamt",)),
    ([k2], ("y", "flaeche"), ("Y",)),
]
assert list(sp._runden([], lambda k: k.radius, sp.RICHTUNGEN, sp.ANSTELLUNGEN, False)) == []
print("OK", os.path.basename(__file__))
