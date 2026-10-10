# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Fenster „Maschinen“ (W-011 S1, Spezifikation Maschine aus Baugruppe, Abschnitt 12): die
Liste der eigenen Maschinen aus maschinenspeicher – Name, Art, Datei – mit Hinzufügen …, Neue
Maschine …, Bearbeiten, Suchen … (die Datei liegt nicht mehr dort) und Entfernen (nur aus der
Liste). Dazu der Beobachter: Speichert man ein Dokument mit einer Maschine, kommt sie in die
Liste – so auch eine mit „Neue Maschine …“ gebaute, sobald sie eine Datei hat.
"""

import os

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import maschine as m
from . import maschinenspeicher as ms
from . import symbol
from .gui_hilfe import kopfzeile
from .gui_teile import GRAU, ROT, knopf
from .sprache import tr

FENSTER_GROESSE = (760, 380)


class BefehlMaschinen:
    """Menü CAM-Addon → Maschinen …: öffnet die Liste – oder holt sie nach vorn."""

    def GetResources(self):
        return {
            "Pixmap": symbol("maschinen.svg"),
            "MenuText": tr("befehl.maschinen.titel"),
            "ToolTip": tr("befehl.maschinen.tooltip"),
        }

    def IsActive(self):
        return True

    def Activated(self):
        oeffne()


def oeffne():
    """Öffnet das Fenster „Maschinen“ – oder holt das offene nach vorn. Gibt es zurück."""
    dialog = MaschinenDialog.offen
    if dialog is not None and dialog.isVisible():
        dialog.fuellen()
        dialog.raise_()
        dialog.activateWindow()
        return dialog
    dialog = MaschinenDialog()
    dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    dialog.show()
    return dialog


def datei_waehlen(eltern, ordner):
    """Fragt nach einer Maschinen-Datei; "" bei Abbrechen. Die Szenarien ersetzen diese
    Funktion – einen Dateidialog können sie nicht bedienen."""
    pfad, _filter = QtGui.QFileDialog.getOpenFileName(
        eltern, tr("ms.datei_waehlen"), ordner, "FreeCAD (*.FCStd)"
    )
    return pfad


def einlesen(datei, pfad=None):
    """Nimmt die Maschinen aus der Datei in die Liste (`pfad`: ihre Datei, None: beim
    Benutzer). Ist die Datei nicht offen, öffnet sie sie unsichtbar und schließt sie danach
    wieder. Gibt [Eintrag] zurück; Fehler beim Öffnen gehen an den Aufrufer."""
    for dokument in FreeCAD.listDocuments().values():
        if ms.gleiche_datei(dokument.FileName, datei):
            return ms.merken_dokument(dokument, pfad)
    dokument = FreeCAD.openDocument(datei, True)
    try:
        return ms.merken_dokument(dokument, pfad)
    finally:
        FreeCAD.closeDocument(dokument.Name)


class MaschinenDialog(QtGui.QDialog):
    """Die Liste der Maschinen. Die Aktionen hinter den Knöpfen sind öffentliche Methoden."""

    offen = None  # das zuletzt geöffnete Fenster – für die Oberflächen-Szenarien

    def __init__(self, eltern=None, pfad=None):
        super().__init__(eltern or FreeCADGui.getMainWindow())
        MaschinenDialog.offen = self
        self.pfad = pfad  # None: die Liste beim Benutzer
        self.eintraege = []
        self.setWindowTitle(tr("ms.titel"))
        self.resize(*FENSTER_GROESSE)
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(kopfzeile(tr("ms.titel"), "maschinen"))
        text = QtGui.QLabel(tr("ms.text"))
        text.setWordWrap(True)
        text.setStyleSheet(f"color: {GRAU.name()};")
        aufbau.addWidget(text)
        self.tabelle = QtGui.QTableWidget(0, 3)
        self.tabelle.setHorizontalHeaderLabels(
            [tr("ms.spalte.name"), tr("ms.spalte.art"), tr("ms.spalte.datei")]
        )
        self.tabelle.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tabelle.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tabelle.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tabelle.verticalHeader().setVisible(False)
        self.tabelle.horizontalHeader().setStretchLastSection(True)
        self.tabelle.itemSelectionChanged.connect(self._knoepfe_schalten)
        self.tabelle.itemDoubleClicked.connect(lambda _eintrag: self.bearbeiten())
        aufbau.addWidget(self.tabelle, 1)
        self.leer = QtGui.QLabel(tr("ms.leer"))
        self.leer.setWordWrap(True)
        self.leer.setStyleSheet(f"color: {GRAU.name()};")
        aufbau.addWidget(self.leer)
        knoepfe = QtGui.QHBoxLayout()
        self.knopf_hinzufuegen = knopf(
            tr("ms.hinzufuegen"), tr("ms.hinzufuegen.tooltip"), self.hinzufuegen
        )
        self.knopf_neu = knopf(
            tr("befehl.neue_maschine.titel"), tr("ms.neu.tooltip"), self.neue_maschine
        )
        self.knopf_bearbeiten = knopf(
            tr("ms.bearbeiten"), tr("ms.bearbeiten.tooltip"), self.bearbeiten
        )
        self.knopf_suchen = knopf(tr("ms.suchen"), tr("ms.suchen.tooltip"), self.suchen)
        self.knopf_entfernen = knopf(tr("ms.entfernen"), tr("ms.entfernen.tooltip"), self.entfernen)
        for k in (
            self.knopf_hinzufuegen,
            self.knopf_neu,
            self.knopf_bearbeiten,
            self.knopf_suchen,
            self.knopf_entfernen,
        ):
            knoepfe.addWidget(k)
        knoepfe.addStretch()
        schliessen = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Close)
        schliessen.rejected.connect(self.reject)
        knoepfe.addWidget(schliessen)
        aufbau.addLayout(knoepfe)
        self.fuellen()

    # --- Liste ----------------------------------------------------------------------------

    def fuellen(self, auswahl=None):
        """Liest die Liste neu; `auswahl`: die Datei, deren Zeile gewählt sein soll – sonst
        bleibt die gewählte."""
        if auswahl is None and self.gewaehlter() is not None:
            auswahl = self.gewaehlter().datei
        ms.aufraeumen(self.pfad)  # verschwundene Dateien aus dem temporären Ordner
        self.eintraege = ms.laden(self.pfad)
        self.tabelle.setRowCount(len(self.eintraege))
        for zeile, eintrag in enumerate(self.eintraege):
            fehlt = not eintrag.vorhanden
            datei = tr("ms.fehlt", datei=eintrag.datei) if fehlt else eintrag.datei
            for spalte, text in enumerate((eintrag.name, ms.art_text(eintrag), datei)):
                zelle = QtGui.QTableWidgetItem(text)
                zelle.setToolTip(datei if spalte == 2 else text)
                if fehlt:
                    zelle.setForeground(QtGui.QColor(ROT))
                self.tabelle.setItem(zeile, spalte, zelle)
        self.tabelle.resizeColumnsToContents()
        self.leer.setVisible(not self.eintraege)
        gewaehlt = next(
            (i for i, e in enumerate(self.eintraege) if ms.gleiche_datei(e.datei, auswahl)), None
        )
        if gewaehlt is None and self.eintraege:
            gewaehlt = 0
        if gewaehlt is not None:
            self.tabelle.selectRow(gewaehlt)
        self._knoepfe_schalten()

    def gewaehlter(self):
        """Der gewählte Eintrag – oder None."""
        zeilen = self.tabelle.selectionModel().selectedRows()
        if not zeilen or zeilen[0].row() >= len(self.eintraege):
            return None
        return self.eintraege[zeilen[0].row()]

    def _knoepfe_schalten(self):
        eintrag = self.gewaehlter()
        self.knopf_bearbeiten.setEnabled(eintrag is not None and eintrag.vorhanden)
        self.knopf_suchen.setEnabled(eintrag is not None and not eintrag.vorhanden)
        self.knopf_entfernen.setEnabled(eintrag is not None)

    # --- Aktionen -------------------------------------------------------------------------

    def _ordner(self):
        eintrag = self.gewaehlter()
        if eintrag is not None and eintrag.datei:
            return os.path.dirname(eintrag.datei)
        dokument = FreeCAD.ActiveDocument
        return os.path.dirname(dokument.FileName) if dokument and dokument.FileName else ""

    def _einlesen(self, datei):
        """einlesen() mit Meldungen; gibt [Eintrag] zurück – leer bei einem Fehler."""
        try:
            gefunden = einlesen(datei, self.pfad)
        except Exception as fehler:  # keine FreeCAD-Datei, kaputt: sagen statt still scheitern
            QtGui.QMessageBox.warning(
                self, tr("ms.titel"), tr("ms.datei_fehler", datei=datei, fehler=fehler)
            )
            return []
        if not gefunden:
            QtGui.QMessageBox.information(
                self, tr("ms.titel"), tr("ms.keine_maschine", datei=datei)
            )
        return gefunden

    def hinzufuegen(self):
        """Eine Maschinen-Datei wählen und in die Liste nehmen."""
        datei = datei_waehlen(self, self._ordner())
        if not datei:
            return
        gefunden = self._einlesen(datei)
        self.fuellen(auswahl=gefunden[0].datei if gefunden else None)

    def neue_maschine(self):
        """„Neue Maschine …“ – in die Liste kommt sie, sobald sie gespeichert ist."""
        FreeCADGui.runCommand("CamAddon_NeueMaschine")

    def bearbeiten(self):
        """Öffnet die Datei der gewählten Maschine und „Maschine bearbeiten“."""
        eintrag = self.gewaehlter()
        if eintrag is None or not eintrag.vorhanden:
            return
        if FreeCADGui.Control.activeDialog():
            QtGui.QMessageBox.information(self, tr("ms.titel"), tr("ms.anderes_fenster"))
            return
        from . import gui_reichweite

        try:
            dokument = gui_reichweite.oeffne_datei(eintrag.datei)
        except Exception as fehler:
            QtGui.QMessageBox.warning(
                self, tr("ms.titel"), tr("ms.datei_fehler", datei=eintrag.datei, fehler=fehler)
            )
            return
        assembly = next(
            (
                o
                for o in dokument.Objects
                if o.TypeId == "Assembly::AssemblyObject" and m.finde_maschine(o) is not None
            ),
            None,
        )
        if assembly is None:
            QtGui.QMessageBox.information(
                self, tr("ms.titel"), tr("ms.keine_maschine", datei=eintrag.datei)
            )
            return
        gui_reichweite.zeige_dokument(dokument)
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(assembly)
        FreeCADGui.runCommand("CamAddon_MaschineBearbeiten")

    def suchen(self):
        """Die Datei liegt nicht mehr dort: die neue wählen – der Eintrag zieht mit."""
        eintrag = self.gewaehlter()
        if eintrag is None:
            return
        datei = datei_waehlen(self, self._ordner())
        if not datei:
            return
        gefunden = self._einlesen(datei)
        if gefunden and not ms.gleiche_datei(datei, eintrag.datei):
            ms.entfernen(eintrag.datei, self.pfad)
        self.fuellen(auswahl=gefunden[0].datei if gefunden else eintrag.datei)

    def entfernen(self):
        """Nimmt die gewählte Maschine aus der Liste; die Datei bleibt."""
        eintrag = self.gewaehlter()
        if eintrag is None:
            return
        ms.entfernen(eintrag.datei, self.pfad)
        self.fuellen()


class _Beobachter:
    """Speichert man ein Dokument mit einer Maschine, kommt sie in die Liste (W-011)."""

    def slotFinishSaveDocument(self, dokument, _datei):
        try:
            gefunden = ms.merken_dokument(dokument)
        except Exception as fehler:  # die Liste ist ein Zusatz – das Speichern geht vor
            FreeCAD.Console.PrintWarning(f"CAM-Addon: Maschinen-Liste: {fehler}\n")
            return
        dialog = MaschinenDialog.offen
        if gefunden and dialog is not None and dialog.isVisible():
            dialog.fuellen(auswahl=gefunden[0].datei)


_BEOBACHTER = []


def beobachten():
    """Meldet den Beobachter einmal an (gui_start.starten)."""
    if not _BEOBACHTER:
        _BEOBACHTER.append(_Beobachter())
        FreeCAD.addDocumentObserver(_BEOBACHTER[0])
