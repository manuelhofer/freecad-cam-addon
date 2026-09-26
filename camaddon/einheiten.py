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


def zahl_aus_text(text, dezimalzeichen=PUNKT):
    """Liest eine Eingabe mit Punkt oder Komma („12,5“ wie „12.5“); leer ist 0 (unbekannt).

    `dezimalzeichen` ist das eingestellte – es trennt immer die
    Nachkommastellen. Das andere Zeichen auch, außer die Zahl ist mit
    Tausendertrennzeichen geschrieben: „35.000“ ist bei eingestelltem Komma
    35000 (so meint es, wer so tippt – B-004), „1,500“ bei Punkt 1500. „12.5“
    und „0.125“ bleiben Dezimalzahlen. Wirft ValueError, wenn der Text keine
    Zahl ist.
    """
    text = text.strip()
    if not text:
        return 0.0
    anderes = PUNKT if dezimalzeichen == KOMMA else KOMMA
    if re.fullmatch(rf"-?[1-9]\d{{0,2}}(\{anderes}\d{{3}})+", text):
        text = text.replace(anderes, "")
    if not _ZAHL.fullmatch(text):
        raise ValueError(f"keine Zahl: {text!r}")
    return float(text.replace(",", "."))
