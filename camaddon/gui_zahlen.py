# SPDX-License-Identifier: LGPL-2.1-or-later
"""Zahlenfelder für alle Dialoge: Format der Oberfläche, Prüfung, Lesen, Zeigen.

Zuerst für „Maschine bearbeiten“ gebaut (B-004, P-2026-09-25-31); hier
zusammengefasst, damit jeder Dialog dieselben Regeln hat: das gewählte
Dezimalzeichen (einheiten.py) ohne Tausendertrennzeichen, Eingaben mit Punkt
oder Komma, ein leeres Feld heißt „unbekannt“ (0).
"""

import re

from PySide import QtCore, QtGui

from . import einheiten
from .werkstoffe import mit_dezimalzeichen

GROESSTER_WERT = 1e9  # obere Grenze der Zahlenfelder
NACHKOMMASTELLEN = 6


def zahlenformat():
    """Das Zahlenformat der Oberfläche: das gewählte Dezimalzeichen, ohne Tausendertrennzeichen.

    Ohne Wahl gilt FreeCADs Zahlenformat – auf einem deutschen System das
    Komma. Mit Tausenderpunkten zeigte das Feld „30.000“, und zurückgelesen
    ergab das 30 statt 30000 (B-004); ohne sie ist jede Zahl eindeutig.
    """
    zeichen = einheiten.gewaehltes_dezimalzeichen()
    if zeichen == einheiten.KOMMA:
        zahlenformat = QtCore.QLocale(QtCore.QLocale.German, QtCore.QLocale.Germany)
    elif zeichen == einheiten.PUNKT:
        zahlenformat = QtCore.QLocale.c()
    else:
        zahlenformat = QtCore.QLocale()
    zahlenformat.setNumberOptions(
        QtCore.QLocale.OmitGroupSeparator | QtCore.QLocale.RejectGroupSeparator
    )
    return zahlenformat


def dezimalzeichen():
    """Das Dezimalzeichen, das die Oberfläche gerade zeigt: gewählt, sonst das von FreeCAD."""
    return zahlenformat().decimalPoint()


class Zahlenpruefer(QtGui.QValidator):
    """Lässt Zahlen ab 0 mit Punkt oder Komma zu – und ein leeres Feld.

    Leer heißt „unbekannt“ (0). Punkt und Komma gelten beide als
    Dezimalzeichen, gleich welches eingestellt ist: „12.5“ ist 12,5.
    """

    _TEILWEISE = re.compile(r"\d*([.,]\d*)?")

    def __init__(self, feld):
        # feld als Qt-Eltern: Der Prüfer lebt so lange wie das Feld.
        super().__init__(feld)

    def validate(self, text, position):
        eingabe = text.strip()
        if not eingabe:
            return QtGui.QValidator.Acceptable, text, position
        if not self._TEILWEISE.fullmatch(eingabe):
            return QtGui.QValidator.Invalid, text, position
        teile = re.split(r"[.,]", eingabe)
        if len(teile) > 1 and len(teile[1]) > NACHKOMMASTELLEN:
            return QtGui.QValidator.Invalid, text, position
        try:
            wert = einheiten.zahl_aus_text(eingabe)
        except ValueError:  # nur ein Dezimalzeichen – wird noch
            return QtGui.QValidator.Intermediate, text, position
        if wert > GROESSTER_WERT:
            return QtGui.QValidator.Invalid, text, position
        return QtGui.QValidator.Acceptable, text, position


def zahl_lesen(text):
    """Liest eine Zahl mit Punkt oder Komma; ein leeres Feld ist 0 (unbekannt)."""
    return einheiten.zahl_aus_text(text)


def zahl_zeigen(wert):
    """Zeigt eine Zahl im Zahlenformat der Oberfläche; 0 (unbekannt) als leeres Feld."""
    if not wert:
        return ""
    return zahlenformat().toString(float(wert), "g", 12)  # 12 gültige Stellen


def dezimal(text):
    """Setzt das Dezimalzeichen der Oberfläche in einen Text mit Punkt-Zahlen ein („Ø 8.5“ → „Ø 8,5“)."""
    return mit_dezimalzeichen(text, zahlenformat().decimalPoint())
