# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die ausführlichen Hilfeseiten: help/<sprache>/<thema>.html.

Gesucht wird wie bei den kurzen Texten (sprache.rueckfall_reihe): gewählte
Sprache, sonst Englisch, sonst Deutsch. Eine Übersetzung der Hilfe darf also
unvollständig sein.
"""

import os

from . import ADDON_ORDNER, sprache

HILFE_ORDNER = os.path.join(ADDON_ORDNER, "help")

# Die Themen; jedes gibt es als eigene Seite. „So geht’s“ zuerst: der Weg vom Teil zum
# Programm in sechs Schritten, mit Verweisen auf alle anderen Seiten (D-54).
THEMEN = [
    "so_gehts",
    "achsen",
    "beschleunigung",
    "transformationen",
    "maschinen",
    "neue_maschine",
    "aufnahmen",
    "bestueckung",
    "glieder",
    "werkstoffe",
    "werkzeuge",
    "halter",
    "magazine",
    "schnittwerte",
    "strategien",
    "schruppwerte",
    "verfahren",
    "reichweite",
    "vierachs",
    "bearbeitung",
    "schwenken",
    "simultan_planung",
    "programm",
]


def hilfe_ordner():
    """Der Hilfe-Ordner der eingestellten Sprache – für Verweise zwischen den Seiten."""
    for code in sprache.rueckfall_reihe():
        ordner = os.path.join(HILFE_ORDNER, code)
        if os.path.isdir(ordner):
            return ordner
    return HILFE_ORDNER


def hilfe_datei(thema):
    """Pfad der Hilfeseite zu einem Thema, oder None, wenn es sie in keiner Sprache gibt."""
    for code in sprache.rueckfall_reihe():
        pfad = os.path.join(HILFE_ORDNER, code, thema + ".html")
        if os.path.isfile(pfad):
            return pfad
    return None
