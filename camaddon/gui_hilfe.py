# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die ausführliche Hilfe im Dialog: Knopf (?) und Hilfefenster.

Die Seiten liegen als HTML in help/<sprache>/ (siehe hilfe.py). Jeder Bereich
des Dialogs hat rechts in seiner Überschrift einen Knopf (?), der die Seite
zu seinem Thema öffnet.
"""

from PySide import QtCore, QtGui

from . import hilfe, symbol
from .sprache import tr

FENSTER_GROESSE = (560, 520)  # Breite, Höhe in Pixeln


def kopfzeile(titel, thema=None):
    """Überschrift eines Bereichs; mit `thema` rechts der Knopf (?) zu dieser Hilfeseite."""
    zeile = QtGui.QWidget()
    aufbau = QtGui.QHBoxLayout(zeile)
    aufbau.setContentsMargins(0, 0, 0, 0)
    aufbau.addWidget(QtGui.QLabel(f"<b>{titel}</b>"))
    aufbau.addStretch()
    if thema:
        knopf = QtGui.QToolButton()
        knopf.setText("?")
        knopf.setToolTip(tr("hilfe.knopf.tooltip"))
        knopf.setObjectName("hilfe_" + thema)  # daran finden ihn die Szenarien
        knopf.clicked.connect(lambda: zeige_hilfe(zeile, thema))
        aufbau.addWidget(knopf)
    return zeile


class BefehlSoGehts:
    """Öffnet „So geht’s“ – der Weg vom Teil zum Programm in sechs Schritten (D-54)."""

    def GetResources(self):
        return {
            "Pixmap": symbol("so_gehts.svg"),
            "MenuText": tr("befehl.so_gehts.titel"),
            "ToolTip": tr("befehl.so_gehts.tooltip"),
        }

    def IsActive(self):
        return True

    def Activated(self):
        import FreeCADGui

        zeige_hilfe(FreeCADGui.getMainWindow(), "so_gehts")


def zeige_hilfe(eltern, thema):
    """Öffnet die Hilfeseite `thema`.

    Nicht modal: Man soll lesen und gleichzeitig im Dialog weiterarbeiten
    können.
    """
    fenster = HilfeFenster(eltern, thema)
    fenster.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    fenster.show()


class HilfeFenster(QtGui.QDialog):
    """Zeigt eine Hilfeseite; Verweise zwischen den Seiten funktionieren."""

    offen = None  # das zuletzt geöffnete Fenster – für die Oberflächen-Szenarien

    def __init__(self, eltern, thema):
        super().__init__(eltern)
        HilfeFenster.offen = self
        self.setWindowTitle(tr("hilfe.titel"))
        self.resize(*FENSTER_GROESSE)
        self.browser = QtGui.QTextBrowser()
        # Verweise wie href="beschleunigung.html" sucht der Browser hier.
        self.browser.setSearchPaths([hilfe.hilfe_ordner()])
        self.browser.setOpenExternalLinks(True)
        pfad = hilfe.hilfe_datei(thema)
        if pfad:
            self.browser.setSource(QtCore.QUrl.fromLocalFile(pfad))
        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Close)
        knoepfe.rejected.connect(self.close)
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(self.browser)
        aufbau.addWidget(knoepfe)
