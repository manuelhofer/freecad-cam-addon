# SPDX-License-Identifier: LGPL-2.1-or-later
"""Sprachsystem: alle Texte der Oberfläche kommen aus translations/<code>.json.

Warum kein Qt-Linguist (.ts/.qm) wie in FreeCAD selbst: Manuel wollte eine
Datei, die jeder ohne Werkzeug übersetzen kann – en.json kopieren, Werte
übersetzen, fertig (P-2026-09-25-09).

Aufbau einer Sprachdatei: ein flaches JSON-Objekt, Schlüssel -> Text. Der
Eintrag "_sprache" nennt die Sprache in ihrer eigenen Schreibweise, so wie sie
in der Auswahl erscheint. Platzhalter schreiben sich {name} und werden über
tr(schluessel, name=...) gefüllt.
"""

import json
import os

import FreeCAD

from . import ADDON_ORDNER, PARAMETER_PFAD

SPRACH_ORDNER = os.path.join(ADDON_ORDNER, "translations")

# Neu installiert gilt Englisch; fehlt ein Text in einer Sprache, auch.
STANDARD_SPRACHE = "en"

# Deutsch ist die führende Datei; sie ist der letzte Rückfall, damit nie ein
# nackter Schlüssel auf dem Bildschirm steht, solange Deutsch ihn kennt.
FUEHRENDE_SPRACHE = "de"

_zwischenspeicher = {}


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def lade_datei(code):
    """Liest translations/<code>.json; unbekannte Sprache ergibt {}."""
    if code not in _zwischenspeicher:
        pfad = os.path.join(SPRACH_ORDNER, code + ".json")
        try:
            with open(pfad, encoding="utf-8") as datei:
                _zwischenspeicher[code] = json.load(datei)
        except FileNotFoundError:
            _zwischenspeicher[code] = {}
        except ValueError as fehler:
            # Eine kaputte Übersetzung darf das Addon nicht lahmlegen.
            FreeCAD.Console.PrintError(f"CAM-Addon: {pfad}: {fehler}\n")
            _zwischenspeicher[code] = {}
    return _zwischenspeicher[code]


def verfuegbare_sprachen():
    """Alle Sprachdateien als {code: Name in der Sprache selbst}, sortiert."""
    sprachen = {}
    for dateiname in sorted(os.listdir(SPRACH_ORDNER)):
        code, endung = os.path.splitext(dateiname)
        if endung == ".json":
            sprachen[code] = lade_datei(code).get("_sprache", code)
    return sprachen


def gewaehlte_sprache():
    """Die vom Benutzer gewählte Sprache oder None, solange nie gewählt."""
    return _parameter().GetString("Sprache", "") or None


def aktuelle_sprache():
    return gewaehlte_sprache() or STANDARD_SPRACHE


def setze_sprache(code):
    _parameter().SetString("Sprache", code)


def tr(schluessel, sprache=None, **werte):
    """Text zum Schlüssel in der aktuellen Sprache, Platzhalter gefüllt.

    Reihenfolge: gewünschte Sprache, Englisch, Deutsch, zuletzt der Schlüssel
    selbst – der fällt dann beim Testen sofort auf.
    """
    for code in (sprache or aktuelle_sprache(), STANDARD_SPRACHE, FUEHRENDE_SPRACHE):
        text = lade_datei(code).get(schluessel)
        if text:
            break
    else:
        FreeCAD.Console.PrintWarning(f"CAM-Addon: Text fehlt: {schluessel}\n")
        text = schluessel
    if werte:
        try:
            text = text.format(**werte)
        except (KeyError, IndexError, ValueError):
            # Falscher Platzhalter in einer Übersetzung: lieber roh zeigen
            # als abstürzen.
            FreeCAD.Console.PrintWarning(f"CAM-Addon: Platzhalter in {schluessel}\n")
    return text
