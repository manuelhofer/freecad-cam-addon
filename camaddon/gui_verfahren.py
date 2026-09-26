# SPDX-License-Identifier: LGPL-2.1-or-later
"""Aufgabenfenster „Maschine verfahren“ (Spezifikation W-001, Stufe 3).

Je Achse eine Zeile: Name (NC-Name der Betriebsart, sonst das Gelenk), ein
Regler, ein Zahlenfeld mit Einheit und darunter die Grenzen. Die Assembly
bewegt sich beim Ziehen mit, über die Grenzen des Gelenks hinaus geht es
nicht. OK behält die Stellung (ein Schritt Rückgängig), Abbrechen stellt
alles zurück, „Grundstellung“ fährt alle Achsen auf den Stand beim Öffnen.
Gerechnet wird in verfahren.py.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import beispielmaschine, symbol
from . import maschine as m
from . import verfahren as vf
from .gui_hilfe import kopfzeile
from .gui_maschine import beispiel_gewuenscht, gewaehlte_assembly
from .gui_teile import GRAU, fett
from .gui_zahlen import zahlenformat
from .kette import LINEAR
from .sprache import tr

# Feinheit der Regler: Schritte je mm bzw. je Grad.
SCHRITTE_JE_EINHEIT = 10
# Reichweite, wenn das Gelenk keine Begrenzung hat: so weit um die Stellung beim Öffnen.
OHNE_GRENZE_LINEAR = 1000.0  # mm
OHNE_GRENZE_DREH = 360.0  # Grad
FELD_GRENZE = 99999.0  # größter Betrag im Zahlenfeld ohne Begrenzung
PLATZ_TOLERANZ = 0.05  # Grad – so nah, und der Platz gilt als eingeschwenkt


class BefehlMaschineVerfahren:
    """Befehl in der Werkzeugleiste: öffnet das Fenster für die gewählte Assembly."""

    def GetResources(self):
        return {
            "Pixmap": symbol("verfahren.svg"),
            "MenuText": tr("befehl.verfahren.titel"),
            "ToolTip": tr("befehl.verfahren.tooltip"),
        }

    def IsActive(self):
        # Wie „Maschine bearbeiten“: bedienbar, solange kein anderes
        # Aufgabenfenster offen ist – was fehlt, sagt der Befehl selbst.
        return not FreeCADGui.Control.activeDialog()

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        assembly = gewaehlte_assembly(doc) if doc else None
        if assembly is None:
            if not beispiel_gewuenscht(tr("vf.titel")):
                return
            assembly, _maschine = beispielmaschine.lade()
            doc = assembly.Document
        verfahren = vf.Verfahren(assembly)
        if not verfahren.achsen:
            QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(), tr("vf.titel"), tr("vf.keine_achsen")
            )
            return
        # Ein Schritt für alles, was bis OK passiert; Abbrechen verwirft ihn.
        doc.openTransaction(tr("vf.titel"))
        FreeCADGui.Control.showDialog(VerfahrPanel(assembly, verfahren))


def _zahl(wert, stellen):
    return zahlenformat().toString(float(wert), "f", stellen)


class VerfahrPanel:
    """Das Aufgabenfenster. FreeCAD ruft `getStandardButtons`, `accept` und `reject` auf."""

    offen = None  # das gerade offene Fenster – für die Oberflächen-Szenarien

    def __init__(self, assembly, verfahren):
        VerfahrPanel.offen = self
        self.assembly = assembly
        self.doc = assembly.Document
        self.verfahren = verfahren
        self.maschine = m.finde_maschine(assembly)
        self.zeilen = {}  # Achse -> (Regler, Zahlenfeld)
        self.platzwahl = {}  # Revolverachse -> (Auswahl, [(Platz, Stellung)])
        self.form = self._baue()

    def getStandardButtons(self):
        return QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel

    def accept(self):
        VerfahrPanel.offen = None
        self.doc.commitTransaction()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    def reject(self):
        VerfahrPanel.offen = None
        # Die Transaktion stellt die Lagen wieder her; zur Sicherheit vorher selbst.
        self.verfahren.grundstellung()
        self.doc.abortTransaction()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    # --- Aufbau ---------------------------------------------------------------------

    def _baue(self):
        form = QtGui.QWidget()
        form.setWindowTitle(tr("vf.titel"))
        form.setWindowIcon(QtGui.QIcon(symbol("verfahren.svg")))
        aufbau = QtGui.QVBoxLayout(form)
        aufbau.addWidget(kopfzeile(tr("vf.titel"), "verfahren"))
        erklaerung = QtGui.QLabel(tr("vf.erklaerung"))
        erklaerung.setWordWrap(True)
        aufbau.addWidget(erklaerung)

        gitter = QtGui.QGridLayout()
        gitter.setColumnStretch(1, 1)
        for i, achse in enumerate(self.verfahren.achsen):
            self._baue_zeile(gitter, 2 * i, achse)
        aufbau.addLayout(gitter)

        self.knopf_grundstellung = QtGui.QPushButton(tr("vf.grundstellung"))
        self.knopf_grundstellung.setToolTip(tr("vf.grundstellung.tooltip"))
        self.knopf_grundstellung.setAutoDefault(False)
        self.knopf_grundstellung.clicked.connect(self.grundstellung)
        zeile = QtGui.QHBoxLayout()
        zeile.addWidget(self.knopf_grundstellung)
        zeile.addStretch()
        aufbau.addLayout(zeile)
        aufbau.addStretch()
        return form

    def _baue_zeile(self, gitter, zeile, achse):
        """Name, Regler und Zahlenfeld; darunter grau die Grenzen."""
        linear = achse.art == LINEAR
        einheit = "mm" if linear else "°"
        stellung = self.verfahren.stellung(achse)
        unten, oben = self._bereich(achse, stellung)

        name = fett(vf.namen(self.maschine, achse))
        name.setToolTip(tr("vf.gelenk.tooltip", gelenk=achse.gelenk.Label))
        regler = QtGui.QSlider(QtCore.Qt.Horizontal)
        regler.setRange(round(unten * SCHRITTE_JE_EINHEIT), round(oben * SCHRITTE_JE_EINHEIT))
        regler.setValue(round(stellung * SCHRITTE_JE_EINHEIT))
        regler.setToolTip(tr("vf.regler.tooltip"))
        feld = QtGui.QDoubleSpinBox()
        feld.setLocale(zahlenformat())
        feld.setDecimals(2 if linear else 1)
        minimum, maximum = self.verfahren.grenzen(achse)
        feld.setRange(
            minimum if minimum is not None else -FELD_GRENZE,
            maximum if maximum is not None else FELD_GRENZE,
        )
        feld.setSuffix(f" {einheit}")
        feld.setValue(stellung)
        feld.setKeyboardTracking(False)  # erst nach Enter oder Verlassen fahren
        regler.valueChanged.connect(lambda wert, a=achse: self.setze(a, wert / SCHRITTE_JE_EINHEIT))
        feld.valueChanged.connect(lambda wert, a=achse: self.setze(a, wert))
        self.zeilen[achse] = (regler, feld)

        gitter.addWidget(name, zeile, 0)
        gitter.addWidget(regler, zeile, 1)
        gitter.addWidget(feld, zeile, 2)
        plaetze = vf.platzstellungen(self.verfahren, self.maschine, achse)
        if plaetze:
            wahl = QtGui.QComboBox()
            wahl.addItem("–", None)
            for platz, platz_stellung in plaetze:
                wahl.addItem(platz, platz_stellung)
            wahl.setToolTip(tr("vf.platz.tooltip"))
            wahl.activated.connect(lambda index, a=achse: self._platz_gewaehlt(a, index))
            gitter.addWidget(wahl, zeile, 3)
            self.platzwahl[achse] = (wahl, plaetze)
            self._platz_zeigen(achse, stellung)
        grenzen = QtGui.QLabel(self._grenzen_text(achse, einheit, 2 if linear else 1))
        grenzen.setStyleSheet(f"color: {GRAU.name()};")
        grenzen.setToolTip(tr("vf.grenzen.tooltip"))
        gitter.addWidget(grenzen, zeile + 1, 1, 1, 2)

    def _bereich(self, achse, stellung):
        """Von wo bis wo der Regler reicht: die Grenzen, sonst ein Stück um die Stellung."""
        minimum, maximum = self.verfahren.grenzen(achse)
        weite = OHNE_GRENZE_LINEAR if achse.art == LINEAR else OHNE_GRENZE_DREH
        unten = minimum if minimum is not None else min(stellung - weite, maximum or stellung)
        oben = maximum if maximum is not None else max(stellung + weite, minimum or stellung)
        return unten, oben

    def _grenzen_text(self, achse, einheit, stellen):
        minimum, maximum = self.verfahren.grenzen(achse)
        if minimum is None and maximum is None:
            return tr("vf.ohne_grenze")
        if maximum is None:
            return tr("vf.nur_min", min=_zahl(minimum, stellen), einheit=einheit)
        if minimum is None:
            return tr("vf.nur_max", max=_zahl(maximum, stellen), einheit=einheit)
        return tr(
            "vf.grenzen",
            min=_zahl(minimum, stellen),
            max=_zahl(maximum, stellen),
            einheit=einheit,
        )

    # --- Aktionen -------------------------------------------------------------------

    def setze(self, achse, stellung):
        """Fährt eine Achse; Regler und Zahlenfeld zeigen danach, was erreicht ist."""
        erreicht = self.verfahren.setze(achse, stellung)
        self._zeige(achse, erreicht)
        return erreicht

    def grundstellung(self):
        """Alle Achsen auf den Stand beim Öffnen."""
        self.verfahren.grundstellung()
        for achse in self.verfahren.achsen:
            self._zeige(achse, self.verfahren.stellung(achse))

    def _zeige(self, achse, stellung):
        regler, feld = self.zeilen[achse]
        for element in (regler, feld):
            element.blockSignals(True)
        regler.setValue(round(stellung * SCHRITTE_JE_EINHEIT))
        feld.setValue(stellung)
        for element in (regler, feld):
            element.blockSignals(False)
        self._platz_zeigen(achse, stellung)

    def waehle_platz(self, achse, platz):
        """Dreht den Revolver, bis `platz` (etwa „P4“) steht, wo beim Öffnen P1 stand."""
        wahl, _plaetze = self.platzwahl[achse]
        self._platz_gewaehlt(achse, wahl.findText(platz))

    def _platz_gewaehlt(self, achse, index):
        wahl, _plaetze = self.platzwahl[achse]
        stellung = wahl.itemData(index)
        if stellung is not None:
            self.setze(achse, stellung)

    def _platz_zeigen(self, achse, stellung):
        """Die Auswahl zeigt den Platz, der gerade an der Stelle von P1 steht – sonst „–“."""
        if achse not in self.platzwahl:
            return
        wahl, plaetze = self.platzwahl[achse]
        index = 0
        for i, (_platz, platz_stellung) in enumerate(plaetze, start=1):
            if abs((stellung - platz_stellung + 180.0) % 360.0 - 180.0) < PLATZ_TOLERANZ:
                index = i
                break
        wahl.blockSignals(True)
        wahl.setCurrentIndex(index)
        wahl.blockSignals(False)

    def achse(self, name):
        """Die Achse mit diesem Namen im Fenster (NC-Name oder Gelenk) – für die Szenarien."""
        return next(a for a in self.verfahren.achsen if vf.namen(self.maschine, a) == name)
