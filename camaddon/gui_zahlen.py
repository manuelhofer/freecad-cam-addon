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
    `mit_minus`: auch negative Zahlen, etwa für einen Winkel.
    """

    _TEILWEISE = re.compile(r"\d*([.,]\d*)?")
    _TEILWEISE_MIT_MINUS = re.compile(r"-?\d*([.,]\d*)?")

    def __init__(self, feld, mit_minus=False):
        # feld als Qt-Eltern: Der Prüfer lebt so lange wie das Feld.
        super().__init__(feld)
        self._muster = self._TEILWEISE_MIT_MINUS if mit_minus else self._TEILWEISE

    def validate(self, text, position):
        eingabe = text.strip()
        if not eingabe:
            return QtGui.QValidator.Acceptable, text, position
        if not self._muster.fullmatch(eingabe):
            return QtGui.QValidator.Invalid, text, position
        teile = re.split(r"[.,]", eingabe)
        if len(teile) > 1 and len(teile[1]) > NACHKOMMASTELLEN:
            return QtGui.QValidator.Invalid, text, position
        try:
            wert = einheiten.zahl_aus_text(eingabe)
        except ValueError:  # nur ein Dezimalzeichen oder Minus – wird noch
            return QtGui.QValidator.Intermediate, text, position
        if abs(wert) > GROESSTER_WERT:
            return QtGui.QValidator.Invalid, text, position
        return QtGui.QValidator.Acceptable, text, position


def zahl_lesen(text):
    """Liest eine Zahl mit Punkt oder Komma; ein leeres Feld ist 0 (unbekannt).

    Das andere Zeichen als das eingestellte gilt in „35.000“ als
    Tausendertrennzeichen (einheiten.zahl_aus_text).
    """
    return einheiten.zahl_aus_text(text, dezimalzeichen())


def groesse_zeigen(wert, groesse, metrisch_stellen=None):
    """Ein metrischer Wert als Feldtext im gewählten Maßsystem (einheiten.LAENGE …); 0 leer.

    `metrisch_stellen`: metrisch auf so viele Stellen gerundet (in Zoll gelten
    die Stellen der Größe).
    """
    if metrisch_stellen is not None and not einheiten.in_zoll():
        return zahl_zeigen(round(wert, metrisch_stellen))
    return zahl_zeigen(einheiten.gerundet(wert, groesse))


def groesse_lesen(text, groesse):
    """Ein Feldtext im gewählten Maßsystem als metrischer Wert – so wird gespeichert."""
    return einheiten.metrisch(zahl_lesen(text), groesse)


def groesse_fest(wert, groesse, stellen):
    """Mit fester Zahl Nachkommastellen – metrisch `stellen`, in Zoll die der Größe (Tabellen)."""
    stellen = einheiten.stellen(groesse, stellen)
    return zahlenformat().toString(float(einheiten.anzeige(wert, groesse)), "f", stellen)


def zahl_zeigen(wert):
    """Zeigt eine Zahl im Zahlenformat der Oberfläche; 0 (unbekannt) als leeres Feld.

    Auf 9 Nachkommastellen gerundet (eingeben lassen sich 6): Rechenrauschen wie
    die Höhe −5,6e-18 einer Fläche auf 0 zeigt 0, nicht „-5,60364933565e-18“.
    """
    wert = round(float(wert or 0), 9)
    if not wert:
        return ""
    return zahlenformat().toString(wert, "g", 12)  # 12 gültige Stellen


def winkel_zeigen(grad):
    """Ein Winkel mit einer Nachkommastelle und Gradzeichen („30,0°“); „?“ für unbekannt (None)."""
    if grad is None:
        return "?"
    # + 0.0 macht aus −0,0 eine 0,0 (Rundungsrest bei rechtwinkligen Achsen).
    return zahlenformat().toString(round(grad, 1) + 0.0, "f", 1) + "°"


def dezimal(text):
    """Setzt das Dezimalzeichen der Oberfläche in einen Text mit Punkt-Zahlen ein („Ø 8.5“ → „Ø 8,5“)."""
    return mit_dezimalzeichen(text, zahlenformat().decimalPoint())
