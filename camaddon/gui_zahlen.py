# SPDX-License-Identifier: LGPL-2.1-or-later
"""Zahlenfelder für alle Dialoge: Format der Oberfläche, Prüfung, Lesen, Zeigen.

Zuerst für „Maschine bearbeiten“ gebaut (B-004, P-2026-09-25-31); hier
zusammengefasst, damit jeder Dialog dieselben Regeln hat: Zahlenformat der
Oberfläche ohne Tausendertrennzeichen, ein leeres Feld heißt „unbekannt“ (0).
"""

from PySide import QtCore, QtGui

GROESSTER_WERT = 1e9  # obere Grenze der Zahlenfelder
NACHKOMMASTELLEN = 6


def zahlenformat():
    """Das Zahlenformat der Oberfläche, aber ohne Tausendertrennzeichen.

    Auf einem deutschen System stellt FreeCAD das deutsche Format ein. Mit
    Tausenderpunkten zeigte das Feld „30.000“, und zurückgelesen ergab das 30
    statt 30000 (B-004). Ohne sie ist jede Eingabe eindeutig: Auf Deutsch ist
    das Komma das Dezimalzeichen, einen Punkt lässt das Feld nicht zu.
    """
    zahlenformat = QtCore.QLocale()
    zahlenformat.setNumberOptions(
        QtCore.QLocale.OmitGroupSeparator | QtCore.QLocale.RejectGroupSeparator
    )
    return zahlenformat


class Zahlenpruefer(QtGui.QDoubleValidator):
    """Lässt nur Zahlen ab 0 im Zahlenformat der Oberfläche zu – und ein leeres Feld.

    Leer heißt „unbekannt“ (0). QDoubleValidator allein hält ein leeres Feld
    für unfertig und meldet es nicht – den Wert zu löschen, bliebe wirkungslos.
    """

    def __init__(self, feld):
        # feld als Qt-Eltern: Der Prüfer lebt so lange wie das Feld.
        super().__init__(0, GROESSTER_WERT, NACHKOMMASTELLEN, feld)
        self.setLocale(zahlenformat())

    def validate(self, text, position):
        if not text.strip():
            return QtGui.QValidator.Acceptable, text, position
        return super().validate(text, position)


def zahl_lesen(text):
    """Liest eine Zahl im Zahlenformat der Oberfläche; ein leeres Feld ist 0 (unbekannt)."""
    text = text.strip()
    if not text:
        return 0.0
    wert, gelesen = zahlenformat().toDouble(text)
    if not gelesen:  # hinter dem Zahlenpruefer nicht möglich
        raise ValueError(f"keine Zahl: {text!r}")
    return wert


def zahl_zeigen(wert):
    """Zeigt eine Zahl im Zahlenformat der Oberfläche; 0 (unbekannt) als leeres Feld."""
    if not wert:
        return ""
    return zahlenformat().toString(float(wert), "g", 12)  # 12 gültige Stellen
