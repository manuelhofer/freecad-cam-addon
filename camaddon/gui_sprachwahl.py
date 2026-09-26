# SPDX-License-Identifier: LGPL-2.1-or-later
"""Sprachwahl: Dialog beim ersten Start und Seite in den Einstellungen.

Der Dialog beim ersten Start beschriftet sich beim Durchblättern der Liste
sofort in der markierten Sprache um – wer kein Englisch kann, sieht so, dass
er richtig ist, bevor er bestätigt.

Die Einstellungsseite enthält auch die Gruppe „Updates“ (gui_aktualisierung).
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import gui_aktualisierung, sprache
from .sprache import tr

# Was nach einer Sprachwahl geschehen soll (gui_start: Knöpfe neu beschriften).
NACH_SPRACHWAHL = []


def _sprachliste(auswahl):
    """Füllt eine QComboBox mit allen Sprachen, `auswahl` vorgewählt."""
    liste = QtGui.QComboBox()
    for code, name in sprache.verfuegbare_sprachen().items():
        liste.addItem(name, code)
    index = liste.findData(auswahl)
    liste.setCurrentIndex(max(index, 0))
    return liste


class ErsterStartDialog(QtGui.QDialog):
    """Fragt beim ersten Start nach der Sprache der Oberfläche."""

    def __init__(self, eltern=None):
        super().__init__(eltern)
        self.liste = _sprachliste(sprache.aktuelle_sprache())
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
        self._platz_fuer_alle_sprachen()
        self._beschriften()

    def gewaehlt(self):
        """Der Code der markierten Sprache, z. B. "de"."""
        return self.liste.currentData()

    def _beschriften(self, *_):
        self._texte_setzen(self.gewaehlt())

    def _texte_setzen(self, code):
        self.setWindowTitle(tr("sprachwahl.titel", sprache=code))
        self.frage.setText(tr("sprachwahl.frage", sprache=code))
        self.hinweis.setText(tr("sprachwahl.hinweis", sprache=code))

    def _platz_fuer_alle_sprachen(self):
        """Macht das Fenster gleich so groß, dass die Texte jeder Sprache hineinpassen.

        Beim Umschalten wächst ein offenes Fenster nicht auf jedem System mit
        (bei Manuel unter KDE nicht) – der längere Text wäre abgeschnitten.
        """
        breite = max(self.minimumWidth(), self.sizeHint().width())
        hoehe = 0
        for index in range(self.liste.count()):
            self._texte_setzen(self.liste.itemData(index))
            hoehe = max(hoehe, self.heightForWidth(breite), self.sizeHint().height())
        self.setMinimumSize(breite, hoehe)

    def reject(self):
        # Schließen ohne Wahl gilt als Wahl der Vorauswahl: Die Frage soll
        # nicht bei jedem Start wiederkommen.
        self.accept()


def _erster_start():
    dialog = ErsterStartDialog(FreeCADGui.getMainWindow())
    dialog.exec_()  # wartet, bis eine Sprache gewählt ist
    _uebernehmen(dialog.gewaehlt())


def _uebernehmen(code):
    """Speichert die Sprache sofort – FreeCAD schreibt seine Einstellungen sonst erst beim
    Beenden, und nach einem Absturz käme die Frage wieder – und beschriftet neu."""
    sprache.setze_sprache(code)
    FreeCAD.saveParameter()
    for aufgabe in NACH_SPRACHWAHL:
        aufgabe()


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

        aufbau = QtGui.QVBoxLayout(self.form)
        aufbau.addWidget(gruppe)
        aufbau.addWidget(gui_aktualisierung.einstellungen_gruppe(self))
        aufbau.addStretch()

    # loadSettings und saveSettings ruft FreeCAD beim Öffnen und bei OK auf.
    def loadSettings(self):
        index = self.liste.findData(sprache.aktuelle_sprache())
        self.liste.setCurrentIndex(max(index, 0))
        gui_aktualisierung.einstellungen_laden(self)

    def saveSettings(self):
        _uebernehmen(self.liste.currentData())
        gui_aktualisierung.einstellungen_speichern(self)


def einstellungsseite_anmelden():
    FreeCADGui.addPreferencePage(Einstellungsseite, tr("einstellungen.gruppe"))
