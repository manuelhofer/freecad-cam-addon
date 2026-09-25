# SPDX-License-Identifier: LGPL-2.1-or-later
"""Ausführliche Hilfetexte: help/<sprache>/<thema>.html.

Wie bei den kurzen Texten gilt: gewählte Sprache, sonst Englisch, sonst
Deutsch. Eine Übersetzung der Hilfe darf also unvollständig sein.
"""

import os

from . import ADDON_ORDNER, sprache

HILFE_ORDNER = os.path.join(ADDON_ORDNER, "help")

THEMEN = ["achsen", "beschleunigung", "aufnahmen", "glieder"]


def hilfe_ordner():
    """Der Ordner der Hilfe in der aktuellen Sprache (für Verweise zwischen Seiten)."""
    for code in (sprache.aktuelle_sprache(), sprache.STANDARD_SPRACHE, sprache.FUEHRENDE_SPRACHE):
        ordner = os.path.join(HILFE_ORDNER, code)
        if os.path.isdir(ordner):
            return ordner
    return HILFE_ORDNER


def hilfe_datei(thema):
    """Pfad der Hilfeseite zum Thema, mit Rückfall auf Englisch und Deutsch."""
    for code in (sprache.aktuelle_sprache(), sprache.STANDARD_SPRACHE, sprache.FUEHRENDE_SPRACHE):
        pfad = os.path.join(HILFE_ORDNER, code, thema + ".html")
        if os.path.isfile(pfad):
            return pfad
    return None
