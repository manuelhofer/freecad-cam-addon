# SPDX-License-Identifier: LGPL-2.1-or-later
"""Oberfläche der Update-Suche: Hinweis beim Start, Gruppe in den Einstellungen.

Gesucht wird in einem eigenen Thread, damit FreeCAD beim Start nicht wartet.
Das Ergebnis zeigt das Hauptfenster, denn Qt-Fenster dürfen nur aus dem
Haupt-Thread kommen: Ein Zeitgeber schaut dort regelmäßig nach, ob die Suche
fertig ist. Die Suche selbst steht in aktualisierung.py.
"""

import os
import threading

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import ADDON_ORDNER, PARAMETER_PFAD
from . import aktualisierung as a
from .sprache import tr

# Ist diese Umgebungsvariable gesetzt, sucht das Addon beim Start nicht – die
# Oberflächen-Szenarien laufen ohne Netz.
AUS_FUER_TESTS = "CAMADDON_OHNE_UPDATE"

START_VERZOEGERUNG_MS = 5000  # erst suchen, wenn FreeCAD fertig gestartet ist
NACHSEHEN_MS = 300  # so oft schaut das Hauptfenster, ob die Suche fertig ist
DIALOG_BREITE = 420  # Pixel

# Hält jede laufende Suche fest. Sonst räumte Python sie samt Zeitgeber ab,
# bevor sie fertig ist.
_laufende_suchen = []


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def suche_beim_start():
    """Soll beim Start gesucht werden? Einstellbar; ab Werk ja."""
    return _parameter().GetBool("UpdateBeimStart", True)


def beim_start():
    """Sucht kurz nach dem Start im Hintergrund – sofern eingeschaltet."""
    if os.environ.get(AUS_FUER_TESTS) or not suche_beim_start():
        return

    def fertig(ergebnis):
        _laufende_suchen.remove(suche)
        zeige(ergebnis)

    suche = Suche(fertig)
    _laufende_suchen.append(suche)
    QtCore.QTimer.singleShot(START_VERZOEGERUNG_MS, suche.start)


class Suche:
    """Sucht im Hintergrund und ruft danach `fertig(ergebnis)` im Hauptfenster auf."""

    def __init__(self, fertig, ordner=ADDON_ORDNER):
        self.fertig = fertig
        self.ordner = ordner
        self.ergebnis = None  # setzt der Such-Thread, liest der Zeitgeber
        self.uhr = QtCore.QTimer()
        self.uhr.setInterval(NACHSEHEN_MS)
        self.uhr.timeout.connect(self._nachsehen)

    def start(self):
        # daemon: Ein hängendes Git hält FreeCAD beim Beenden nicht auf.
        threading.Thread(target=self._suchen, daemon=True).start()
        self.uhr.start()

    def _suchen(self):  # läuft im Such-Thread
        self.ergebnis = a.pruefe(self.ordner)

    def _nachsehen(self):  # läuft im Hauptfenster
        if self.ergebnis is not None:
            self.uhr.stop()
            self.fertig(self.ergebnis)


def zeige(ergebnis, von_hand=False, ordner=ADDON_ORDNER, eltern=None):
    """Zeigt das Ergebnis einer Suche; gibt den UpdateDialog zurück, falls einer aufgeht.

    Beim Start (`von_hand=False`) bleibt es still, außer es gibt etwas zu tun,
    und manche Hinweise kommen nur einmal. Nach „Jetzt nach Updates suchen“
    gibt es immer eine Antwort.
    """
    eltern = eltern or FreeCADGui.getMainWindow()
    parameter = _parameter()
    if ergebnis.status == a.NEU:
        dialog = UpdateDialog(ergebnis, ordner)
        dialog.show()
        return dialog
    if ergebnis.status == a.LOKAL_GEAENDERT:
        # Einmal je neuer Version sagen, nicht bei jedem Start.
        schon_gesagt = parameter.GetString("HinweisLokalFuer", "") == ergebnis.version_neu
        parameter.SetString("HinweisLokalFuer", ergebnis.version_neu)
        if von_hand or not schon_gesagt:
            _hinweis(eltern, tr("update.lokal_geaendert", neu=ergebnis.version_neu))
    elif ergebnis.status == a.KEIN_GIT:
        schon_gesagt = parameter.GetBool("HinweisKeinGitGezeigt", False)
        parameter.SetBool("HinweisKeinGitGezeigt", True)
        if von_hand or not schon_gesagt:
            _hinweis(eltern, tr("update.kein_git"))
    elif ergebnis.status == a.FEHLER:
        # Beim Start kein Fenster – oft ist nur gerade kein Netz da.
        text = tr("update.fehler", fehler=ergebnis.meldung)
        FreeCAD.Console.PrintWarning(text + "\n")
        if von_hand:
            QtGui.QMessageBox.warning(eltern, tr("update.titel"), text)
    elif von_hand and ergebnis.status == a.KEIN_GIT_ORDNER:
        _hinweis(eltern, tr("update.kein_git_ordner"))
    elif von_hand:  # AKTUELL
        _hinweis(eltern, tr("update.aktuell", jetzt=ergebnis.version_jetzt))
    return None


def _hinweis(eltern, text):
    QtGui.QMessageBox.information(eltern, tr("update.titel"), text)


class UpdateDialog(QtGui.QDialog):
    """„Neue Version – jetzt aktualisieren?“ Nicht modal: FreeCAD bleibt bedienbar."""

    offen = None  # das zuletzt geöffnete Fenster – für die Oberflächen-Szenarien

    def __init__(self, ergebnis, ordner=ADDON_ORDNER):
        super().__init__(FreeCADGui.getMainWindow())
        UpdateDialog.offen = self
        self.ordner = ordner
        self.setWindowTitle(tr("update.titel"))
        self.setMinimumWidth(DIALOG_BREITE)
        self.text = QtGui.QLabel(
            tr("update.neu", neu=ergebnis.version_neu, jetzt=ergebnis.version_jetzt)
        )
        self.text.setWordWrap(True)
        knoepfe = QtGui.QDialogButtonBox()
        self.knopf_jetzt = knoepfe.addButton(tr("update.jetzt"), QtGui.QDialogButtonBox.AcceptRole)
        knoepfe.addButton(tr("update.spaeter"), QtGui.QDialogButtonBox.RejectRole)
        knoepfe.accepted.connect(self._aktualisieren)
        knoepfe.rejected.connect(self.close)
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(self.text)
        aufbau.addWidget(knoepfe)

    def _aktualisieren(self):
        """Holt den neuen Stand; das Fenster sagt danach, ob es geklappt hat."""
        self.knopf_jetzt.hide()
        try:
            a.aktualisiere(self.ordner)
        except Exception as fehler:  # jeder Fehler von Git: sagen statt still scheitern
            FreeCAD.Console.PrintError(f"CAM-Addon: {fehler}\n")
            self.text.setText(tr("update.fehlgeschlagen", fehler=str(fehler)))
            return
        self.text.setText(tr("update.fertig"))


# --- Gruppe „Updates“ in den Einstellungen --------------------------------------


def einstellungen_gruppe(seite):
    """Die Gruppe für die Einstellungsseite; legt `seite.update_beim_start` an."""
    gruppe = QtGui.QGroupBox(tr("update.gruppe"))
    seite.update_beim_start = QtGui.QCheckBox(tr("update.beim_start"))
    seite.update_beim_start.setToolTip(tr("update.beim_start.tooltip"))
    knopf = QtGui.QPushButton(tr("update.jetzt_suchen"))

    def jetzt_suchen():
        knopf.setEnabled(False)  # bis die Suche fertig ist

        def fertig(ergebnis):
            _laufende_suchen.remove(suche)
            knopf.setEnabled(True)
            zeige(ergebnis, von_hand=True, eltern=gruppe)

        suche = Suche(fertig)
        _laufende_suchen.append(suche)
        suche.start()

    knopf.clicked.connect(jetzt_suchen)
    aufbau = QtGui.QVBoxLayout(gruppe)
    aufbau.addWidget(seite.update_beim_start)
    aufbau.addWidget(knopf)
    return gruppe


def einstellungen_laden(seite):
    seite.update_beim_start.setChecked(suche_beim_start())


def einstellungen_speichern(seite):
    _parameter().SetBool("UpdateBeimStart", seite.update_beim_start.isChecked())
