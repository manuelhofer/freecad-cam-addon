# SPDX-License-Identifier: LGPL-2.1-or-later
"""Sprache und Zahlen: Dialog beim ersten Start und Seite in den Einstellungen.

Der Dialog beim ersten Start beschriftet sich beim Durchblättern der Liste
sofort in der markierten Sprache um – wer kein Englisch kann, sieht so, dass
er richtig ist, bevor er bestätigt. Darunter Maßsystem und Dezimalzeichen,
mit Beispielzahlen, vorbelegt aus FreeCAD (Stufe B des Plans).

Die Einstellungsseite enthält auch die Gruppe „Updates“ (gui_aktualisierung).
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import einheiten, farben, gui_aktualisierung, klone_speichern, sprache
from .gui_teile import ruhiges_mausrad
from .gui_zahlen import dezimalzeichen
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


def _dezimalzeichenliste():
    """QComboBox mit Komma und Punkt, vorgewählt das gewählte oder FreeCADs Dezimalzeichen."""
    liste = QtGui.QComboBox()
    for zeichen in einheiten.DEZIMALZEICHEN:
        liste.addItem("", zeichen)
    index = liste.findData(dezimalzeichen())
    liste.setCurrentIndex(max(index, 0))
    return liste


def _dezimalzeichen_beschriften(liste, code=None):
    """Die Einträge mit Beispielzahlen – in der Sprache `code` (None: der des Addons)."""
    liste.setItemText(0, tr("zahlen.komma", sprache=code))
    liste.setItemText(1, tr("zahlen.punkt", sprache=code))


def masssystemliste():
    """QComboBox mit mm und inch, vorgewählt das gewählte oder FreeCADs Maßsystem."""
    liste = QtGui.QComboBox()
    for wahl in einheiten.MASSSYSTEME:
        liste.addItem("", wahl)
    liste.setCurrentIndex(max(liste.findData(einheiten.masssystem()), 0))
    return liste


def _masssystem_beschriften(liste, code=None):
    """Die Einträge mit Beispielen – in der Sprache `code` (None: der des Addons)."""
    liste.setItemText(0, tr("zahlen.metrisch", sprache=code))
    liste.setItemText(1, tr("zahlen.zoll", sprache=code))


class ErsterStartDialog(QtGui.QDialog):
    """Fragt beim ersten Start nach Sprache, Maßsystem und Dezimalzeichen."""

    def __init__(self, eltern=None):
        super().__init__(eltern)
        self.liste = _sprachliste(sprache.aktuelle_sprache())
        self.frage = QtGui.QLabel()
        self.frage.setWordWrap(True)
        self.frage_zahlen = QtGui.QLabel()
        self.frage_zahlen.setWordWrap(True)
        self.wahl_masssystem = masssystemliste()
        self.wahl_dezimalzeichen = _dezimalzeichenliste()
        self.hinweis = QtGui.QLabel()
        self.hinweis.setWordWrap(True)
        self.knopf = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok)
        self.knopf.accepted.connect(self.accept)

        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(self.frage)
        aufbau.addWidget(self.liste)
        aufbau.addSpacing(8)
        aufbau.addWidget(self.frage_zahlen)
        aufbau.addWidget(self.wahl_masssystem)
        aufbau.addWidget(self.wahl_dezimalzeichen)
        aufbau.addWidget(self.hinweis)
        aufbau.addWidget(self.knopf)
        self.setMinimumWidth(420)

        self.liste.currentIndexChanged.connect(self._beschriften)
        self._platz_fuer_alle_sprachen()
        self._beschriften()
        ruhiges_mausrad(self)

    def gewaehlt(self):
        """Der Code der markierten Sprache, z. B. "de"."""
        return self.liste.currentData()

    def gewaehltes_dezimalzeichen(self):
        """„,“ oder „.“."""
        return self.wahl_dezimalzeichen.currentData()

    def gewaehltes_masssystem(self):
        """einheiten.METRISCH oder einheiten.ZOLL."""
        return self.wahl_masssystem.currentData()

    def _beschriften(self, *_):
        self._texte_setzen(self.gewaehlt())

    def _texte_setzen(self, code):
        self.setWindowTitle(tr("sprachwahl.titel", sprache=code))
        self.frage.setText(tr("sprachwahl.frage", sprache=code))
        self.frage_zahlen.setText(tr("zahlen.frage", sprache=code))
        _masssystem_beschriften(self.wahl_masssystem, code)
        _dezimalzeichen_beschriften(self.wahl_dezimalzeichen, code)
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
    _uebernehmen(
        dialog.gewaehlt(), dialog.gewaehltes_masssystem(), dialog.gewaehltes_dezimalzeichen()
    )


def _uebernehmen(code, masssystem, zeichen):
    """Speichert Sprache, Maßsystem und Dezimalzeichen sofort – FreeCAD schreibt seine
    Einstellungen sonst erst beim Beenden, und nach einem Absturz käme die Frage wieder –
    und beschriftet neu."""
    sprache.setze_sprache(code)
    einheiten.setze_masssystem(masssystem)
    einheiten.setze_dezimalzeichen(zeichen)
    FreeCAD.saveParameter()
    for aufgabe in NACH_SPRACHWAHL:
        aufgabe()


def beim_ersten_start_fragen():
    """Fragt einmal nach Sprache und Dezimalzeichen, sobald das Hauptfenster steht.

    Auch, wer die Sprache schon gewählt hat, wird einmal gefragt, wenn das
    Dezimalzeichen neu dazugekommen ist – mit seiner Sprache vorgewählt. Nach
    dem Maßsystem allein fragt es nicht noch einmal: Das folgt bis zu einer
    Wahl FreeCADs Einheitensystem.
    """
    if sprache.gewaehlte_sprache() is None or einheiten.gewaehltes_dezimalzeichen() is None:
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
        gruppen_aufbau = QtGui.QFormLayout()
        gruppen_aufbau.addRow(tr("einstellungen.sprache.feld"), self.liste)
        _mit_satz(gruppe, gruppen_aufbau, hinweis)

        self.wahl_masssystem = masssystemliste()
        _masssystem_beschriften(self.wahl_masssystem)
        self.wahl_dezimalzeichen = _dezimalzeichenliste()
        _dezimalzeichen_beschriften(self.wahl_dezimalzeichen)
        zahlen = QtGui.QGroupBox(tr("einstellungen.zahlen.gruppe"))
        zahlen_aufbau = QtGui.QFormLayout()
        zahlen_aufbau.addRow(tr("einstellungen.zahlen.masssystem"), self.wahl_masssystem)
        zahlen_aufbau.addRow(tr("einstellungen.zahlen.feld"), self.wahl_dezimalzeichen)
        self.zahlen_hinweis = QtGui.QLabel(tr("einstellungen.zahlen.hinweis"))
        self.zahlen_hinweis.setWordWrap(True)
        _mit_satz(zahlen, zahlen_aufbau, self.zahlen_hinweis)
        self.gruppe_updates = gui_aktualisierung.einstellungen_gruppe(self)
        dateien = QtGui.QGroupBox(tr("einstellungen.dateien.gruppe"))
        self.klone_einmal = QtGui.QCheckBox(tr("einstellungen.dateien.klone"))
        dateien_aufbau = QtGui.QFormLayout()
        dateien_aufbau.addRow(self.klone_einmal)
        self.klone_hinweis = QtGui.QLabel(tr("einstellungen.dateien.klone.hinweis"))
        self.klone_hinweis.setWordWrap(True)
        _mit_satz(dateien, dateien_aufbau, self.klone_hinweis)

        # Wie viele Nebenrechner (nebenrechner) – vorgegeben alle Kerne (Manuel, 2026-10-24: „alle
        # cpus müssen genutzt werden!“); weniger für den, dessen Rechner nebenbei anderes tut. Von
        # 1 bis zu den Kernen, die der Rechner hat, anfangs alle (Manuel, 2026-10-25: „0 als alle
        # kerne ist doof was ist wenn ich 255 eintragen würde ? … schreib anfangs immer die
        # maximal ermittelte anzahl rein“).
        from . import nebenrechner

        kerne = nebenrechner.anzahl_kerne()
        rechnen = QtGui.QGroupBox(tr("einstellungen.rechnen.gruppe"))
        self.wahl_nebenrechner = QtGui.QSpinBox()
        self.wahl_nebenrechner.setRange(1, kerne)
        self.wahl_nebenrechner.setValue(kerne)
        self.wahl_nebenrechner.setSuffix(tr("einstellungen.rechnen.von", kerne=kerne))
        rechnen_aufbau = QtGui.QFormLayout()
        rechnen_aufbau.addRow(tr("einstellungen.rechnen.feld"), self.wahl_nebenrechner)
        self.rechnen_hinweis = QtGui.QLabel(tr("einstellungen.rechnen.hinweis"))
        self.rechnen_hinweis.setWordWrap(True)
        # Weniger als alle Kerne: gleich darunter, dass es dann länger dauert (Manuel, 2026-10-25).
        self.rechnen_weniger = QtGui.QLabel()
        self.rechnen_weniger.setWordWrap(True)
        self.rechnen_weniger.setStyleSheet(f"color: {farben.GELB};")
        rechnen_aufbau.addRow(self.rechnen_weniger)
        self.wahl_nebenrechner.valueChanged.connect(self._weniger_kerne_zeigen)
        _mit_satz(rechnen, rechnen_aufbau, self.rechnen_hinweis)

        # Die Beta (Manuel, 2026-10-30): neue Wege zum Ausprobieren, das Gewohnte bleibt.
        # Ein Haken in der Gruppe „Updates“, die Erklärung im Tooltip – eine eigene Gruppe mit Satz
        # machte die Seite so hoch, dass die Sätze darüber gestaucht wurden
        # (szenario_erster_start, 680 hoch).
        self.beta_an = QtGui.QCheckBox(tr("einstellungen.beta.haken"))
        self.beta_an.setToolTip(tr("einstellungen.beta.hinweis"))
        self.gruppe_updates.layout().insertWidget(1, self.beta_an)

        aufbau = QtGui.QVBoxLayout(self.form)
        aufbau.addWidget(gruppe)
        aufbau.addWidget(zahlen)
        aufbau.addWidget(dateien)
        aufbau.addWidget(rechnen)
        aufbau.addWidget(self.gruppe_updates)
        aufbau.addStretch()
        ruhiges_mausrad(self.form)  # FreeCADs Einstellungen blättern

    def _weniger_kerne_zeigen(self, anzahl):
        """Unter dem Feld: Stehen weniger Nebenrechner da, als der Rechner Kerne hat, dass es
        länger dauert – sonst nichts."""
        from . import nebenrechner

        kerne = nebenrechner.anzahl_kerne()
        if anzahl < kerne:
            self.rechnen_weniger.setText(
                tr("einstellungen.rechnen.weniger", anzahl=anzahl, kerne=kerne)
            )
            self.rechnen_weniger.show()
        else:
            self.rechnen_weniger.clear()
            self.rechnen_weniger.hide()

    # loadSettings und saveSettings ruft FreeCAD beim Öffnen und bei OK auf.
    def loadSettings(self):
        index = self.liste.findData(sprache.aktuelle_sprache())
        self.liste.setCurrentIndex(max(index, 0))
        index = self.wahl_masssystem.findData(einheiten.masssystem())
        self.wahl_masssystem.setCurrentIndex(max(index, 0))
        index = self.wahl_dezimalzeichen.findData(dezimalzeichen())
        self.wahl_dezimalzeichen.setCurrentIndex(max(index, 0))
        self.klone_einmal.setChecked(klone_speichern.an())
        from . import gui_bearbeitung_beta

        self.beta_an.setChecked(gui_bearbeitung_beta.beta_an())
        from . import nebenrechner

        # Gespeichert heißt 0 „alle“ (ein Rechner mit mehr Kernen nimmt dann alle seine).
        self.wahl_nebenrechner.setValue(nebenrechner.gewuenschte_anzahl())
        self._weniger_kerne_zeigen(self.wahl_nebenrechner.value())
        gui_aktualisierung.einstellungen_laden(self)

    def saveSettings(self):
        _uebernehmen(
            self.liste.currentData(),
            self.wahl_masssystem.currentData(),
            self.wahl_dezimalzeichen.currentData(),
        )
        klone_speichern.setzen(self.klone_einmal.isChecked())
        from . import gui_bearbeitung_beta, gui_start

        if self.beta_an.isChecked() != gui_bearbeitung_beta.beta_an():
            gui_bearbeitung_beta.beta_setzen(self.beta_an.isChecked())
            gui_start.beta_umgeschaltet()
        from . import nebenrechner

        anzahl = self.wahl_nebenrechner.value()
        nebenrechner.anzahl_setzen(0 if anzahl >= nebenrechner.anzahl_kerne() else anzahl)
        gui_aktualisierung.einstellungen_speichern(self)


def einstellungsseite_anmelden():
    FreeCADGui.addPreferencePage(Einstellungsseite, tr("einstellungen.gruppe"))


def _mit_satz(gruppe, formular, satz):
    """Das Formular und darunter ein Satz mit Umbruch in der Gruppe. Als Zeile im Formular bekam
    der Satz nicht die Höhe seines Umbruchs und lief in die nächste Gruppe (Durchsicht 3,
    D-50)."""
    senkrecht = QtGui.QVBoxLayout(gruppe)
    senkrecht.addLayout(formular)
    senkrecht.addWidget(satz)
