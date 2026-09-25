# SPDX-License-Identifier: LGPL-2.1-or-later
"""Oberfläche der Update-Suche: Hinweis beim Start, Knopf in den Einstellungen.

Gesucht wird im Hintergrund, damit FreeCAD beim Start nicht wartet; das
Ergebnis wird im Hauptfenster gezeigt (Qt darf nur dort zeichnen).
"""

import os
import threading

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD
from . import aktualisierung as a
from .sprache import tr

# Für die Oberflächen-Szenarien: kein Netzzugriff beim Start.
AUS_FUER_TESTS = "CAMADDON_OHNE_UPDATE"


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def suche_beim_start():
    return _parameter().GetBool("UpdateBeimStart", True)


class Suche:
    """Sucht im Hintergrund und ruft danach `fertig(ergebnis)` im Hauptfenster auf."""

    def __init__(self, fertig, ordner=None):
        self.fertig = fertig
        self.ordner = ordner
        self.ergebnis = None
        self.uhr = QtCore.QTimer()
        self.uhr.setInterval(300)
        self.uhr.timeout.connect(self._nachsehen)

    def start(self):
        faden = threading.Thread(target=self._suchen, daemon=True)
        faden.start()
        self.uhr.start()

    def _suchen(self):
        if self.ordner:
            self.ergebnis = a.pruefe(self.ordner)
        else:
            self.ergebnis = a.pruefe()

    def _nachsehen(self):
        if self.ergebnis is not None:
            self.uhr.stop()
            self.fertig(self.ergebnis)


class UpdateDialog(QtGui.QDialog):
    """„Neue Version verfügbar – jetzt aktualisieren?“ (nicht modal)."""

    offen = None

    def __init__(self, ergebnis, ordner=None):
        super().__init__(FreeCADGui.getMainWindow())
        UpdateDialog.offen = self
        self.ordner = ordner
        self.setWindowTitle(tr("update.titel"))
        self.text = QtGui.QLabel(
            tr("update.neu", neu=ergebnis.version_neu, jetzt=ergebnis.version_jetzt)
        )
        self.text.setWordWrap(True)
        self.knoepfe = QtGui.QDialogButtonBox()
        self.knopf_jetzt = self.knoepfe.addButton(
            tr("update.jetzt"), QtGui.QDialogButtonBox.AcceptRole
        )
        self.knoepfe.addButton(tr("update.spaeter"), QtGui.QDialogButtonBox.RejectRole)
        self.knoepfe.accepted.connect(self._aktualisieren)
        self.knoepfe.rejected.connect(self.close)
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(self.text)
        aufbau.addWidget(self.knoepfe)
        self.setMinimumWidth(420)

    def _aktualisieren(self):
        try:
            if self.ordner:
                a.aktualisiere(self.ordner)
            else:
                a.aktualisiere()
        except Exception as fehler:
            FreeCAD.Console.PrintError(f"CAM-Addon: {fehler}\n")
            self.text.setText(tr("update.fehlgeschlagen", fehler=str(fehler)))
            self.knopf_jetzt.hide()
            return
        self.text.setText(tr("update.fertig"))
        self.knopf_jetzt.hide()


def zeige(ergebnis, von_hand=False, ordner=None, eltern=None):
    """Zeigt das Ergebnis. Beim Start still, außer es gibt etwas zu tun."""
    eltern = eltern or FreeCADGui.getMainWindow()
    parameter = _parameter()
    if ergebnis.status == a.NEU:
        dialog = UpdateDialog(ergebnis, ordner)
        dialog.show()
        return dialog
    if ergebnis.status == a.LOKAL_GEAENDERT:
        # Einmal je neuer Version sagen, nicht bei jedem Start.
        if von_hand or parameter.GetString("HinweisLokalFuer", "") != ergebnis.version_neu:
            parameter.SetString("HinweisLokalFuer", ergebnis.version_neu)
            QtGui.QMessageBox.information(
                eltern, tr("update.titel"), tr("update.lokal_geaendert", neu=ergebnis.version_neu)
            )
        return None
    if ergebnis.status == a.KEIN_GIT:
        if von_hand or not parameter.GetBool("HinweisKeinGitGezeigt", False):
            parameter.SetBool("HinweisKeinGitGezeigt", True)
            QtGui.QMessageBox.information(eltern, tr("update.titel"), tr("update.kein_git"))
        return None
    if ergebnis.status == a.FEHLER:
        # Beim Start kein Fenster – oft ist nur gerade kein Netz da.
        FreeCAD.Console.PrintWarning(tr("update.fehler", fehler=ergebnis.meldung) + "\n")
        if von_hand:
            QtGui.QMessageBox.warning(
                eltern, tr("update.titel"), tr("update.fehler", fehler=ergebnis.meldung)
            )
        return None
    if von_hand:
        text = (
            tr("update.kein_git_ordner")
            if ergebnis.status == a.KEIN_GIT_ORDNER
            else tr("update.aktuell", jetzt=ergebnis.version_jetzt)
        )
        QtGui.QMessageBox.information(eltern, tr("update.titel"), text)
    return None


_laufend = []  # hält die Suche am Leben, bis sie fertig ist


def beim_start():
    if os.environ.get(AUS_FUER_TESTS) or not suche_beim_start():
        return
    suche = Suche(lambda ergebnis: (zeige(ergebnis), _laufend.clear()))
    _laufend.append(suche)
    # Erst suchen, wenn FreeCAD fertig gestartet ist.
    QtCore.QTimer.singleShot(5000, suche.start)


def einstellungen_gruppe(seite):
    """Gruppe „Updates“ für die Einstellungsseite des Addons."""
    gruppe = QtGui.QGroupBox(tr("update.gruppe"))
    aufbau = QtGui.QVBoxLayout(gruppe)
    seite.update_beim_start = QtGui.QCheckBox(tr("update.beim_start"))
    seite.update_beim_start.setToolTip(tr("update.beim_start.tooltip"))
    knopf = QtGui.QPushButton(tr("update.jetzt_suchen"))

    def jetzt_suchen():
        knopf.setEnabled(False)

        def fertig(ergebnis):
            knopf.setEnabled(True)
            zeige(ergebnis, von_hand=True, eltern=gruppe)
            _laufend.clear()

        suche = Suche(fertig)
        _laufend.append(suche)
        suche.start()

    knopf.clicked.connect(jetzt_suchen)
    aufbau.addWidget(seite.update_beim_start)
    aufbau.addWidget(knopf)
    return gruppe


def einstellungen_laden(seite):
    seite.update_beim_start.setChecked(suche_beim_start())


def einstellungen_speichern(seite):
    _parameter().SetBool("UpdateBeimStart", seite.update_beim_start.isChecked())
