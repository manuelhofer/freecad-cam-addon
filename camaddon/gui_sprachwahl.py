# SPDX-License-Identifier: LGPL-2.1-or-later
"""Sprachwahl: Dialog beim ersten Start und Seite in den Einstellungen.

Der Dialog beim ersten Start beschriftet sich beim Durchblättern der Liste
sofort in der markierten Sprache um – wer kein Englisch kann, sieht so, dass
er richtig ist, bevor er bestätigt.
"""

import FreeCADGui
from PySide import QtCore, QtGui

from . import sprache
from .sprache import tr


def _sprachliste(auswahl):
    """Füllt eine QComboBox mit allen Sprachen, `auswahl` vorgewählt."""
    liste = QtGui.QComboBox()
    for code, name in sprache.verfuegbare_sprachen().items():
        liste.addItem(name, code)
    index = liste.findData(auswahl)
    liste.setCurrentIndex(max(index, 0))
    return liste


class ErsterStartDialog(QtGui.QDialog):
    def __init__(self, eltern=None):
        super().__init__(eltern)
        self.liste = _sprachliste(sprache.STANDARD_SPRACHE)
        self.frage = QtGui.QLabel()
        self.frage.setWordWrap(True)
        self.hinweis = QtGui.QLabel()
        self.hinweis.setWordWrap(True)
        self.knopf = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok)
        self.knopf.accepted.connect(self.accept)

        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(self.frage)
        aufbau.addWidget(self.liste)
        aufbau.addWidget(self.hinweis)
        aufbau.addWidget(self.knopf)
        self.setMinimumWidth(420)

        self.liste.currentIndexChanged.connect(self._beschriften)
        self._beschriften()

    def gewaehlt(self):
        return self.liste.currentData()

    def _beschriften(self, *_):
        code = self.gewaehlt()
        self.setWindowTitle(tr("sprachwahl.titel", sprache=code))
        self.frage.setText(tr("sprachwahl.frage", sprache=code))
        self.hinweis.setText(tr("sprachwahl.hinweis", sprache=code))

    def reject(self):
        # Schließen ohne Wahl gilt als Wahl der Vorauswahl: Die Frage soll
        # nicht bei jedem Start wiederkommen.
        self.accept()


def _erster_start():
    dialog = ErsterStartDialog(FreeCADGui.getMainWindow())
    dialog.exec_()
    sprache.setze_sprache(dialog.gewaehlt())


def beim_ersten_start_fragen():
    """Fragt einmal nach der Sprache, sobald das Hauptfenster steht."""
    if sprache.gewaehlte_sprache() is None:
        QtCore.QTimer.singleShot(0, _erster_start)


class Einstellungsseite:
    """Seite „CAM-Addon“ unter Bearbeiten → Einstellungen."""

    def __init__(self):
        self.form = QtGui.QWidget()
        self.form.setWindowTitle(tr("einstellungen.titel"))
        self.liste = _sprachliste(sprache.aktuelle_sprache())
        hinweis = QtGui.QLabel(tr("einstellungen.sprache.neustart"))
        hinweis.setWordWrap(True)

        gruppe = QtGui.QGroupBox(tr("einstellungen.sprache.gruppe"))
        gruppen_aufbau = QtGui.QFormLayout(gruppe)
        gruppen_aufbau.addRow(tr("einstellungen.sprache.feld"), self.liste)
        gruppen_aufbau.addRow(hinweis)

        from . import gui_aktualisierung

        aufbau = QtGui.QVBoxLayout(self.form)
        aufbau.addWidget(gruppe)
        aufbau.addWidget(gui_aktualisierung.einstellungen_gruppe(self))
        aufbau.addStretch()

    def loadSettings(self):
        from . import gui_aktualisierung

        index = self.liste.findData(sprache.aktuelle_sprache())
        self.liste.setCurrentIndex(max(index, 0))
        gui_aktualisierung.einstellungen_laden(self)

    def saveSettings(self):
        from . import gui_aktualisierung

        sprache.setze_sprache(self.liste.currentData())
        gui_aktualisierung.einstellungen_speichern(self)


def einstellungsseite_anmelden():
    FreeCADGui.addPreferencePage(Einstellungsseite, tr("einstellungen.gruppe"))
