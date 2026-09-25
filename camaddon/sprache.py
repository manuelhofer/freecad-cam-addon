# SPDX-License-Identifier: LGPL-2.1-or-later
"""Sprachsystem: Alle Texte der Oberfläche kommen aus translations/<code>.json.

Eine Sprachdatei ist ein flaches JSON-Objekt, Schlüssel -> Text. Der Eintrag
"_sprache" nennt die Sprache in ihrer eigenen Schreibweise, so wie sie in der
Auswahl erscheint. Platzhalter schreiben sich {name} und werden über
tr(schluessel, name=…) gefüllt.

Warum nicht Qt Linguist (.ts/.qm) wie FreeCAD selbst: Gewünscht war eine
Datei, die jeder ohne Werkzeug übersetzen kann – en.json kopieren, Texte
übersetzen, fertig (P-2026-09-25-09). Die Anleitung dazu steht in
translations/README.md.
"""

import json
import os

import FreeCAD

from . import ADDON_ORDNER, PARAMETER_PFAD

SPRACH_ORDNER = os.path.join(ADDON_ORDNER, "translations")

# Nach der Installation gilt Englisch, bis der Benutzer eine Sprache wählt.
STANDARD_SPRACHE = "en"

# Deutsch ist die führende Sprache: Jeder Text entsteht zuerst auf Deutsch,
# de.json ist deshalb immer vollständig.
FUEHRENDE_SPRACHE = "de"

_geladen = {}  # Code -> Inhalt der Sprachdatei; jede Datei wird nur einmal gelesen


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def lade_datei(code):
    """Der Inhalt von translations/<code>.json; {} bei unbekannter oder kaputter Datei."""
    if code not in _geladen:
        pfad = os.path.join(SPRACH_ORDNER, code + ".json")
        try:
            with open(pfad, encoding="utf-8") as datei:
                _geladen[code] = json.load(datei)
        except FileNotFoundError:
            _geladen[code] = {}
        except ValueError as fehler:
            # Eine kaputte Übersetzung darf das Addon nicht lahmlegen.
            FreeCAD.Console.PrintError(f"CAM-Addon: {pfad}: {fehler}\n")
            _geladen[code] = {}
    return _geladen[code]


def verfuegbare_sprachen():
    """Alle Sprachdateien als {Code: Name der Sprache in ihr selbst}, nach Code sortiert."""
    sprachen = {}
    for dateiname in sorted(os.listdir(SPRACH_ORDNER)):
        code, endung = os.path.splitext(dateiname)
        if endung == ".json":
            sprachen[code] = lade_datei(code).get("_sprache", code)
    return sprachen


def gewaehlte_sprache():
    """Die Sprache, die der Benutzer gewählt hat – oder None, solange er nie gewählt hat."""
    return _parameter().GetString("Sprache", "") or None


def aktuelle_sprache():
    """Die Sprache der Oberfläche: die gewählte, sonst Englisch."""
    return gewaehlte_sprache() or STANDARD_SPRACHE


def setze_sprache(code):
    _parameter().SetString("Sprache", code)


def rueckfall_reihe(sprache=None):
    """Die Sprachen, in denen ein Text gesucht wird, der Reihe nach.

    Erst die gewünschte (ohne Angabe die eingestellte), dann Englisch, zuletzt
    Deutsch. So darf eine Übersetzung unvollständig sein.
    """
    return (sprache or aktuelle_sprache(), STANDARD_SPRACHE, FUEHRENDE_SPRACHE)


def tr(schluessel, sprache=None, **werte):
    """Der Text zum Schlüssel, die Platzhalter mit `werte` gefüllt.

    `sprache` wählt eine andere als die eingestellte Sprache – etwa, um beim
    ersten Start die Sprachauswahl schon in der gerade markierten Sprache zu
    zeigen.
    """
    text = _suche_text(schluessel, sprache)
    if not werte:
        return text
    try:
        return text.format(**werte)
    except (KeyError, IndexError, ValueError):
        # Falscher Platzhalter in einer Übersetzung: lieber den Text roh
        # zeigen als abstürzen.
        FreeCAD.Console.PrintWarning(f"CAM-Addon: Platzhalter in {schluessel}\n")
        return text


def _suche_text(schluessel, sprache):
    for code in rueckfall_reihe(sprache):
        text = lade_datei(code).get(schluessel)
        if text:
            return text
    # Kennt keine Sprache den Schlüssel, erscheint er selbst – das fällt beim
    # Testen sofort auf.
    FreeCAD.Console.PrintWarning(f"CAM-Addon: Text fehlt: {schluessel}\n")
    return schluessel
