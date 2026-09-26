# SPDX-License-Identifier: LGPL-2.1-or-later
"""Befehl und Dialog „Neue Maschine …“ (W-001, Stufe 3b, Schritt 7).

Man wählt eine Bauart und bekommt sie fertig eingerichtet in einem neuen
Dokument – bei der Drehmaschine mit den eigenen Maßen: Name, Bettneigung,
Winkel der Y-Achse, Wege, Revolverplätze, Höchstdrehzahl (Manuel: „so, dass
es ein Leichtes ist, so etwas zu erstellen“). Steht Y schräg, kommt die
schräge Achse gleich mit (beispielmaschine.drehmaschine). Die übrigen
Bauarten haben feste Maße. Danach öffnet sich „Maschine bearbeiten“.

Derselbe Dialog öffnet sich hinter „Beispielmaschine laden …“ in
„Maschine bearbeiten“ und „Maschine verfahren“.
"""

import FreeCADGui
from PySide import QtCore, QtGui

from . import beispielmaschine, einheiten, symbol
from .gui_hilfe import kopfzeile
from .gui_teile import hinweiszeile, ruhiges_mausrad
from .gui_zahlen import zahlenformat
from .sprache import tr

ROLLE = QtCore.Qt.UserRole
GROESSTE_DREHZAHL = 100000  # U/min im Feld


class BefehlNeueMaschine:
    """Befehl in der Werkzeugleiste: Bauart wählen, Maße eintragen, bauen."""

    def GetResources(self):
        return {
            "Pixmap": symbol("neue_maschine.svg"),
            "MenuText": tr("befehl.neue_maschine.titel"),
            "ToolTip": tr("befehl.neue_maschine.tooltip"),
        }

    def IsActive(self):
        return not FreeCADGui.Control.activeDialog()

    def Activated(self):
        gewaehlt = waehle(tr("neu.titel"))
        if gewaehlt is None:
            return
        assembly, _maschine = beispielmaschine.lade(*gewaehlt)
        # Gleich „Maschine bearbeiten“ – dort steht, was gebaut wurde.
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(assembly)
        FreeCADGui.runCommand("CamAddon_MaschineBearbeiten")


def waehle(titel):
    """Zeigt den Dialog; gibt (Bauart, Maße oder None) zurück – oder None bei Abbrechen."""
    dialog = NeueMaschineDialog(FreeCADGui.getMainWindow(), titel)
    if not dialog.exec():
        return None
    return dialog.gewaehlt(), dialog.masse()


class NeueMaschineDialog(QtGui.QDialog):
    """Die Bauarten als Liste, darunter, was die gewählte zeigt, und bei der
    Drehmaschine ihre Maße. Vorgewählt ist die zuletzt gebaute; Doppelklick baut."""

    offen = None  # der gerade offene Dialog – für die Prüfungen

    def __init__(self, eltern=None, titel=None):
        super().__init__(eltern)
        self.setWindowTitle(titel or tr("neu.titel"))
        self.setMinimumWidth(520)
        text = QtGui.QLabel(tr("beispiel.auswahl.text"))
        text.setWordWrap(True)
        self.liste = QtGui.QListWidget()
        for art in beispielmaschine.ARTEN:
            eintrag = QtGui.QListWidgetItem(beispielmaschine.titel(art))
            eintrag.setData(ROLLE, art)
            self.liste.addItem(eintrag)
        # So hoch, dass alle Bauarten ohne Rollbalken hineinpassen.
        self.liste.setFixedHeight(
            self.liste.sizeHintForRow(0) * self.liste.count() + 2 * self.liste.frameWidth() + 4
        )
        self.beschreibung = QtGui.QLabel()
        self.beschreibung.setWordWrap(True)
        self.beschreibung.setMinimumHeight(3 * self.fontMetrics().lineSpacing())
        self.beschreibung.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.masse_bereich = self._baue_masse()
        self.fest = QtGui.QLabel(tr("neu.masse.fest"))
        self.fest.setWordWrap(True)
        self.fehler = hinweiszeile()
        self.fehler.hide()
        self.knoepfe = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
        )
        self.knoepfe.button(QtGui.QDialogButtonBox.Ok).setText(tr("neu.bauen"))
        self.knoepfe.accepted.connect(self.accept)
        self.knoepfe.rejected.connect(self.reject)
        self.liste.currentItemChanged.connect(self._gewechselt)
        self.liste.itemDoubleClicked.connect(lambda _eintrag: self.accept())

        aufbau = QtGui.QVBoxLayout(self)
        for widget in (text, self.liste, self.beschreibung):
            aufbau.addWidget(widget)
        aufbau.addWidget(kopfzeile(tr("neu.masse"), "neue_maschine"))
        for widget in (self.masse_bereich, self.fest, self.fehler, self.knoepfe):
            aufbau.addWidget(widget)
        zuletzt = beispielmaschine.zuletzt_gewaehlt()
        self.liste.setCurrentRow(beispielmaschine.ARTEN.index(zuletzt))
        ruhiges_mausrad(self)
        NeueMaschineDialog.offen = self

    # --- Aufbau ---------------------------------------------------------------------

    def _baue_masse(self):
        """Die Felder der Drehmaschine, vorbelegt wie das Beispiel."""
        vorgabe = beispielmaschine.DrehmaschinenMasse()
        bereich = QtGui.QWidget()
        formular = QtGui.QFormLayout(bereich)
        formular.setContentsMargins(0, 0, 0, 0)

        self.feld_name = QtGui.QLineEdit()
        self.feld_name.setPlaceholderText(beispielmaschine.titel(beispielmaschine.DREHMASCHINE))
        self.feld_name.setToolTip(tr("neu.name.tooltip"))
        formular.addRow(tr("neu.name"), self.feld_name)

        self.feld_bett = _winkelfeld(vorgabe.bettneigung, beispielmaschine.BETTNEIGUNG_BEREICH)
        self.feld_bett.setToolTip(tr("neu.bettneigung.tooltip"))
        formular.addRow(tr("neu.bettneigung"), self.feld_bett)
        self.feld_y_winkel = _winkelfeld(vorgabe.y_winkel, beispielmaschine.Y_WINKEL_BEREICH)
        self.feld_y_winkel.setToolTip(tr("neu.y_winkel.tooltip"))
        formular.addRow(tr("neu.y_winkel"), self.feld_y_winkel)

        self.felder_weg = {}
        for achse, weg in (("X", vorgabe.weg_x), ("Y", vorgabe.weg_y), ("Z", vorgabe.weg_z)):
            von, bis = _wegfeld(weg[0], unten=True), _wegfeld(weg[1], unten=False)
            zeile = QtGui.QWidget()
            reihe = QtGui.QHBoxLayout(zeile)
            reihe.setContentsMargins(0, 0, 0, 0)
            reihe.addWidget(von)
            reihe.addWidget(QtGui.QLabel(tr("neu.bis")))
            reihe.addWidget(bis)
            zeile.setToolTip(tr("neu.weg.tooltip"))
            formular.addRow(tr("neu.weg", achse=achse), zeile)
            self.felder_weg[achse] = (von, bis)

        self.feld_plaetze = QtGui.QSpinBox()
        self.feld_plaetze.setRange(*beispielmaschine.PLAETZE_BEREICH)
        self.feld_plaetze.setValue(vorgabe.plaetze)
        self.feld_plaetze.setToolTip(tr("neu.plaetze.tooltip"))
        formular.addRow(tr("neu.plaetze"), self.feld_plaetze)

        self.feld_drehzahl = QtGui.QSpinBox()
        self.feld_drehzahl.setRange(1, GROESSTE_DREHZAHL)
        self.feld_drehzahl.setSingleStep(100)
        self.feld_drehzahl.setValue(round(vorgabe.drehzahl))
        self.feld_drehzahl.setSuffix(" " + tr("neu.drehzahl.einheit"))
        self.feld_drehzahl.setToolTip(tr("neu.drehzahl.tooltip"))
        formular.addRow(tr("neu.drehzahl"), self.feld_drehzahl)

        # Wer etwas ändert, bekommt den alten roten Satz nicht mehr zu sehen.
        felder = [self.feld_bett, self.feld_y_winkel, self.feld_plaetze, self.feld_drehzahl]
        felder += [f for paar in self.felder_weg.values() for f in paar]
        for feld in felder:
            feld.valueChanged.connect(lambda _wert: self.fehler.hide())
        return bereich

    # --- Auswahl und Ergebnis -------------------------------------------------------

    def _gewechselt(self, aktuell, _vorher):
        art = aktuell.data(ROLLE) if aktuell is not None else None
        self.beschreibung.setText(beispielmaschine.beschreibung(art) if art else "")
        mit_massen = art == beispielmaschine.DREHMASCHINE
        self.masse_bereich.setVisible(mit_massen)
        self.fest.setVisible(not mit_massen)
        self.fehler.hide()

    def gewaehlt(self):
        """Die gewählte Bauart, oder None."""
        eintrag = self.liste.currentItem()
        return eintrag.data(ROLLE) if eintrag is not None else None

    def masse(self):
        """Die eingetragenen Maße (beispielmaschine.DrehmaschinenMasse) – nur bei der
        Drehmaschine, sonst None."""
        if self.gewaehlt() != beispielmaschine.DREHMASCHINE:
            return None
        wege = {
            achse: tuple(einheiten.metrisch(f.value(), einheiten.LAENGE) for f in felder)
            for achse, felder in self.felder_weg.items()
        }
        return beispielmaschine.DrehmaschinenMasse(
            name=self.feld_name.text().strip(),
            bettneigung=self.feld_bett.value(),
            y_winkel=self.feld_y_winkel.value(),
            weg_x=wege["X"],
            weg_y=wege["Y"],
            weg_z=wege["Z"],
            plaetze=self.feld_plaetze.value(),
            drehzahl=float(self.feld_drehzahl.value()),
        )

    def accept(self):
        """Baut erst, wenn die Maße passen; sonst sagt die rote Zeile, was nicht passt."""
        masse = self.masse()
        fehler = masse.fehler() if masse is not None else []
        if fehler:
            # Derselbe Satz für mehrere Wege steht nur einmal da.
            saetze = dict.fromkeys(satz for _feld, satz in fehler)
            self.fehler.setText(" ".join(saetze))
            self.fehler.show()
            return
        super().accept()

    def done(self, ergebnis):
        NeueMaschineDialog.offen = None
        super().done(ergebnis)


def _winkelfeld(wert, bereich):
    feld = QtGui.QDoubleSpinBox()
    feld.setLocale(zahlenformat())
    feld.setDecimals(1)
    feld.setRange(*bereich)
    feld.setSuffix(" °")
    feld.setValue(wert)
    return feld


def _wegfeld(wert, unten):
    """Ein Ende eines Wegs in mm oder inch; 0 liegt immer dazwischen."""
    feld = QtGui.QDoubleSpinBox()
    feld.setLocale(zahlenformat())
    feld.setDecimals(einheiten.stellen(einheiten.LAENGE, 0))
    grenze = einheiten.anzeige(beispielmaschine.GROESSTER_WEG, einheiten.LAENGE)
    if unten:
        feld.setRange(-grenze, 0.0)
    else:
        feld.setRange(0.0, grenze)
    feld.setSuffix(f" {einheiten.einheit(einheiten.LAENGE)}")
    feld.setValue(einheiten.anzeige(wert, einheiten.LAENGE))
    return feld
