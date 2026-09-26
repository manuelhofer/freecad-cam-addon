# SPDX-License-Identifier: LGPL-2.1-or-later
"""Verteilhilfe für Revolverplätze: Revolver, ersten Platz und Anzahl wählen.

Die Plätze legt danach maschine.verteile_plaetze() an – P1 ist das gewählte
Koordinatensystem, die übrigen liegen gleichmäßig im Kreis um die
Revolverachse.
"""

from PySide import QtGui

from . import maschine as m
from .gui_teile import ruhiges_mausrad
from .sprache import tr

VORGABE_ANZAHL = 12  # häufigste Revolvergröße
KLEINSTE_ANZAHL, GROESSTE_ANZAHL = 2, 96


class VerteilDialog(QtGui.QDialog):
    """Fragt ab, was verteilt werden soll; `ergebnis()` liefert die Wahl.

    `lcs_fuer(revolver)` liefert die Koordinatensysteme, die sich mit dem
    Revolver drehen – nur sie taugen als erster Platz.
    """

    def __init__(self, eltern, revolver, lcs_fuer):
        super().__init__(eltern)
        self.setWindowTitle(tr("dialog.plaetze_verteilen"))
        self.revolver = revolver
        self.lcs_fuer = lcs_fuer
        self._angeboten = []  # die Koordinatensysteme in der Liste „erster Platz“

        aufbau = QtGui.QFormLayout(self)
        erklaerung = QtGui.QLabel(tr("verteilen.erklaerung"))
        erklaerung.setWordWrap(True)
        aufbau.addRow(erklaerung)

        self.wahl_revolver = QtGui.QComboBox()
        for ba in revolver:
            self.wahl_revolver.addItem(m.name_von(ba))
        self.wahl_revolver.currentIndexChanged.connect(self._erste_plaetze_anbieten)
        aufbau.addRow(tr("verteilen.revolver"), self.wahl_revolver)

        self.wahl_lcs = QtGui.QComboBox()
        aufbau.addRow(tr("verteilen.erster_platz"), self.wahl_lcs)

        self.anzahl = QtGui.QSpinBox()
        self.anzahl.setRange(KLEINSTE_ANZAHL, GROESSTE_ANZAHL)
        self.anzahl.setValue(VORGABE_ANZAHL)
        aufbau.addRow(tr("verteilen.anzahl"), self.anzahl)

        self.hinweis = QtGui.QLabel()
        self.hinweis.setWordWrap(True)
        aufbau.addRow(self.hinweis)

        self.knoepfe = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
        )
        self.knoepfe.accepted.connect(self.accept)
        self.knoepfe.rejected.connect(self.reject)
        aufbau.addRow(self.knoepfe)
        ruhiges_mausrad(self)

        self._erste_plaetze_anbieten()

    def ergebnis(self):
        """(Revolver, erstes Koordinatensystem, Anzahl)."""
        return (
            self.revolver[self.wahl_revolver.currentIndex()],
            self._angeboten[self.wahl_lcs.currentIndex()],
            self.anzahl.value(),
        )

    def _erste_plaetze_anbieten(self, *_):
        """Füllt „erster Platz“ mit den Koordinatensystemen des gewählten Revolvers."""
        revolver = self.revolver[self.wahl_revolver.currentIndex()]
        # Was die Verteilhilfe selbst angelegt hat („…_P2“), taugt nicht als
        # erster Platz einer neuen Verteilung.
        self._angeboten = [lcs for lcs in self.lcs_fuer(revolver) if "_P" not in lcs.Label]
        self.wahl_lcs.clear()
        for lcs in self._angeboten:
            self.wahl_lcs.addItem(lcs.Label)
        gibt_es = bool(self._angeboten)
        self.hinweis.setText("" if gibt_es else tr("verteilen.kein_lcs"))
        self.knoepfe.button(QtGui.QDialogButtonBox.Ok).setEnabled(gibt_es)
