# SPDX-License-Identifier: LGPL-2.1-or-later
"""Zahlen des Addons: Dezimalzeichen und Lesen von Eingaben (Stufe B des Plans).

Das Dezimalzeichen wählt man beim ersten Start und in den Einstellungen des
Addons (Manuel: „bei der Installation auswählbar … mit Beispielzahlen … und
in den Einstellungen wieder ändern“); bis dahin gilt FreeCADs Zahlenformat.
Eingaben nehmen immer Punkt und Komma – wer „12.5“ tippt, meint 12,5, egal
was eingestellt ist. Tausendertrennzeichen gibt es nicht (B-004).

Läuft ohne Oberfläche; das Zahlenformat für Qt baut gui_zahlen daraus.
"""

import re

import FreeCAD

from . import PARAMETER_PFAD

KOMMA, PUNKT = ",", "."
DEZIMALZEICHEN = (KOMMA, PUNKT)

_DEZIMALZEICHEN = "Dezimalzeichen"  # Schlüssel in den Einstellungen
# Eine Zahl, wie sie in einem Feld stehen darf: Ziffern, höchstens ein
# Dezimalzeichen (Punkt oder Komma), vorn ein Minus.
_ZAHL = re.compile(r"-?(\d+([.,]\d*)?|[.,]\d+)")


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def gewaehltes_dezimalzeichen():
    """Das gewählte Dezimalzeichen („,“ oder „.“), oder None – dann gilt FreeCADs Zahlenformat."""
    zeichen = _parameter().GetString(_DEZIMALZEICHEN, "")
    return zeichen if zeichen in DEZIMALZEICHEN else None


def setze_dezimalzeichen(zeichen):
    """Merkt das Dezimalzeichen; alles andere als „,“ oder „.“ vergisst es."""
    if zeichen in DEZIMALZEICHEN:
        _parameter().SetString(_DEZIMALZEICHEN, zeichen)
    else:
        _parameter().RemString(_DEZIMALZEICHEN)


def zahl_aus_text(text):
    """Liest eine Eingabe mit Punkt oder Komma („12,5“ wie „12.5“); leer ist 0 (unbekannt).

    Wirft ValueError, wenn der Text keine Zahl ist.
    """
    text = text.strip()
    if not text:
        return 0.0
    if not _ZAHL.fullmatch(text):
        raise ValueError(f"keine Zahl: {text!r}")
    return float(text.replace(",", "."))
