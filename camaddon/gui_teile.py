# SPDX-License-Identifier: LGPL-2.1-or-later
"""Kleine Bausteine, die die Dialoge der Werkzeugverwaltung teilen.

Fette Beschriftung für Pflichtfelder, Knopf, Feld mit Einheit, rote
Hinweiszeile und das Grau für gerechnete oder geerbte Werte – einmal hier,
damit jeder Dialog gleich aussieht (P-2026-09-25-54).
"""

from PySide import QtCore, QtGui

GRAU = QtGui.QColor("#6d6d6d")  # gerechnete oder geerbte Werte
ROT = "#c0392b"  # Hinweise, was fehlt oder nicht passt


def fett(text):
    """Beschriftung in Fettschrift – so sind Pflichtfelder markiert."""
    beschriftung = QtGui.QLabel(text)
    schrift = beschriftung.font()
    schrift.setBold(True)
    beschriftung.setFont(schrift)
    return beschriftung


def knopf(text, tooltip, aktion):
    """Knopf, der `aktion()` ohne Argument aufruft; Enter in einem Feld löst ihn nicht aus."""
    k = QtGui.QPushButton(text)
    k.setToolTip(tooltip)
    k.setAutoDefault(False)
    k.clicked.connect(lambda: aktion())
    return k


def mit_einheit(feld, einheit):
    """Feld mit der Einheit rechts daneben."""
    zeile = QtGui.QWidget()
    aufbau = QtGui.QHBoxLayout(zeile)
    aufbau.setContentsMargins(0, 0, 0, 0)
    aufbau.addWidget(feld)
    aufbau.addWidget(QtGui.QLabel(einheit))
    return zeile


def hinweiszeile(text=""):
    """Rote Zeile unter den Feldern: was fehlt oder nicht passt, als Satz."""
    zeile = QtGui.QLabel(text)
    zeile.setWordWrap(True)
    zeile.setStyleSheet(f"color: {ROT};")
    zeile.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
    return zeile


def grau(text):
    """Tabellenzelle in Grau – für gerechnete oder geerbte Werte."""
    zelle = QtGui.QTableWidgetItem(text)
    zelle.setForeground(GRAU)
    return zelle
