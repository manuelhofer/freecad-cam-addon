# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Fenster „Magazine“ der Werkzeugverwaltung (W-002 Stufe H; Manuel, 2026-10-05: „das Paket
sollte in der Werkzeugverwaltung geschnürt werden“, „man kann beliebig viele Magazine machen“,
„die Maschine muss aber schon bestehen“).

Links die Magazine (Neu, Kopieren, Löschen), rechts das gewählte: Name, Maschine aus dem
Maschinenspeicher, ob es für sie gilt, wie viele Plätze Wechsler bzw. Revolver haben, und je
Werkzeug eine Zeile – T-Nummer, Werkzeug aus der Werkzeugverwaltung, Name an der Steuerung,
beladen auf Platz (leer: nicht beladen). Es ändert die Bibliothek des Werkzeugdialogs; gespeichert
wird mit dessen OK oder Übernehmen. Unten rot, was nicht zusammenpasst (eine Nummer oder ein
Platz zweimal, ein Platz über der Zahl der Plätze).
"""

import FreeCADGui
from PySide import QtGui

from . import maschinenspeicher as msp
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_teile import GRAU, knopf, ruhiges_mausrad
from .sprache import tr

FENSTER_GROESSE = (1000, 620)
LISTE_BREITE = 260
GROESSTE_NUMMER = 9999
GROESSTE_PLATZ = 999
ROT = "#cc0000"
SPALTE_T, SPALTE_WERKZEUG, SPALTE_NAME, SPALTE_PLATZ = range(4)
BREITEN = {SPALTE_T: 90, SPALTE_NAME: 190, SPALTE_PLATZ: 130}  # Pixel; das Werkzeug füllt den Rest


def werkzeug_text(werkzeug):
    """„Schaftfräser Ø 12 – VHM 12 lang“ – wie die Zeile das Werkzeug zeigt."""
    text = wz.kurz(werkzeug)
    return f"{text} – {werkzeug.name}" if werkzeug.name else text


def platz_text(magazin, maschinen):
    """„30 Plätze“ / „12 Plätze (Revolver der Maschine)“ – oder leer."""
    eintrag = msp.finde(maschinen, magazin.maschine) if magazin.maschine else None
    if magazin.plaetze > 0:
        return ""
    if eintrag is not None and eintrag.revolver and eintrag.plaetze:
        return tr("mg.plaetze.revolver", plaetze=eintrag.plaetze)
    return ""


def plaetze_von(magazin, maschinen):
    """Wie viele Plätze das Magazin hat: eingetragen, sonst die des Revolvers der Maschine,
    sonst 0 (unbekannt)."""
    if magazin.plaetze > 0:
        return magazin.plaetze
    eintrag = msp.finde(maschinen, magazin.maschine) if magazin.maschine else None
    return eintrag.plaetze if eintrag is not None and eintrag.revolver else 0


def probleme(magazin, maschinen):
    """Sätze, was nicht zusammenpasst: eine T-Nummer zweimal, ein Platz zweimal, ein Platz über
    der Zahl der Plätze."""
    saetze = []
    gesehen = {}
    for e in magazin.eintraege:
        if e.nummer in gesehen:
            saetze.append(tr("mg.problem.nummer", nummer=e.nummer))
        gesehen[e.nummer] = e
    plaetze = {}
    for e in magazin.eintraege:
        if not e.platz:
            continue
        if e.platz in plaetze:
            saetze.append(tr("mg.problem.platz", platz=e.platz))
        plaetze[e.platz] = e
    hoechstens = plaetze_von(magazin, maschinen)
    if hoechstens:
        zu_weit = sorted(p for p in plaetze if p > hoechstens)
        if zu_weit:
            saetze.append(tr("mg.problem.zu_weit", platz=zu_weit[0], plaetze=hoechstens))
    return list(dict.fromkeys(saetze))


class MagazinDialog(QtGui.QDialog):
    """Die Magazine einer Bibliothek bearbeiten (die Arbeitskopie des Werkzeugdialogs)."""

    offen = None  # für die Oberflächen-Szenarien

    def __init__(self, eltern, bibliothek):
        super().__init__(eltern or FreeCADGui.getMainWindow())
        MagazinDialog.offen = self
        self.bibliothek = bibliothek
        self.maschinen = msp.laden()
        self.magazin = None
        self._fuellt = False
        self.setWindowTitle(tr("mg.titel"))
        self.resize(*FENSTER_GROESSE)
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(kopfzeile(tr("mg.titel"), "magazine"))
        erklaerung = QtGui.QLabel(tr("mg.erklaerung"))
        erklaerung.setWordWrap(True)
        erklaerung.setStyleSheet(f"color: {GRAU.name()};")
        aufbau.addWidget(erklaerung)
        teilung = QtGui.QSplitter()
        teilung.addWidget(self._bereich_liste())
        teilung.addWidget(self._bereich_magazin())
        teilung.setStretchFactor(1, 1)
        teilung.setSizes([LISTE_BREITE, FENSTER_GROESSE[0] - LISTE_BREITE])
        aufbau.addWidget(teilung, 1)
        self.probleme = QtGui.QLabel()
        self.probleme.setWordWrap(True)
        self.probleme.setStyleSheet(f"color: {ROT};")
        aufbau.addWidget(self.probleme)
        unten = QtGui.QHBoxLayout()
        speichern = QtGui.QLabel(tr("mg.speichern"))
        speichern.setStyleSheet(f"color: {GRAU.name()};")
        unten.addWidget(speichern, 1)
        schliessen = QtGui.QPushButton(tr("mg.schliessen"))
        schliessen.clicked.connect(self.accept)
        unten.addWidget(schliessen)
        aufbau.addLayout(unten)
        ruhiges_mausrad(self)
        self._liste_fuellen(self.bibliothek.magazine[0] if self.bibliothek.magazine else None)

    # --- Aufbau ---------------------------------------------------------------------------

    def _bereich_liste(self):
        rahmen = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(rahmen)
        aufbau.setContentsMargins(0, 0, 0, 0)
        self.liste = QtGui.QListWidget()
        self.liste.currentRowChanged.connect(self._magazin_gewaehlt)
        aufbau.addWidget(self.liste, 1)
        zeile = QtGui.QHBoxLayout()
        self.knopf_neu = knopf(tr("mg.neu"), tr("mg.neu.tooltip"), self.magazin_anlegen)
        self.knopf_kopieren = knopf(
            tr("mg.kopieren"), tr("mg.kopieren.tooltip"), self.magazin_kopieren
        )
        self.knopf_loeschen = knopf(
            tr("mg.loeschen"), tr("mg.loeschen.tooltip"), self.magazin_loeschen
        )
        for element in (self.knopf_neu, self.knopf_kopieren, self.knopf_loeschen):
            zeile.addWidget(element)
        aufbau.addLayout(zeile)
        return rahmen

    def _bereich_magazin(self):
        self.rechts = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(self.rechts)
        aufbau.setContentsMargins(0, 0, 0, 0)
        formular = QtGui.QFormLayout()
        self.feld_name = QtGui.QLineEdit()
        self.feld_name.setToolTip(tr("mg.name.tooltip"))
        self.feld_name.textEdited.connect(self._name_geaendert)
        formular.addRow(tr("mg.name"), self.feld_name)
        self.wahl_maschine = QtGui.QComboBox()
        self.wahl_maschine.setToolTip(tr("mg.maschine.tooltip"))
        self.wahl_maschine.currentIndexChanged.connect(self._maschine_gewaehlt)
        formular.addRow(tr("mg.maschine"), self.wahl_maschine)
        self.haken_gilt = QtGui.QCheckBox(tr("mg.gilt"))
        self.haken_gilt.setToolTip(tr("mg.gilt.tooltip"))
        self.haken_gilt.toggled.connect(self._gilt_geaendert)
        formular.addRow("", self.haken_gilt)
        plaetze = QtGui.QHBoxLayout()
        self.feld_plaetze = QtGui.QSpinBox()
        self.feld_plaetze.setRange(0, GROESSTE_PLATZ)
        self.feld_plaetze.setSpecialValueText("–")
        self.feld_plaetze.setToolTip(tr("mg.plaetze.tooltip"))
        self.feld_plaetze.valueChanged.connect(self._plaetze_geaendert)
        plaetze.addWidget(self.feld_plaetze)
        self.plaetze_text = QtGui.QLabel()
        self.plaetze_text.setStyleSheet(f"color: {GRAU.name()};")
        plaetze.addWidget(self.plaetze_text, 1)
        formular.addRow(tr("mg.plaetze"), plaetze)
        aufbau.addLayout(formular)
        self.tabelle = QtGui.QTableWidget(0, 4)
        self.tabelle.setHorizontalHeaderLabels(
            [
                tr("mg.spalte.t"),
                tr("mg.spalte.werkzeug"),
                tr("mg.spalte.name"),
                tr("mg.spalte.platz"),
            ]
        )
        self.tabelle.horizontalHeader().setSectionResizeMode(
            SPALTE_WERKZEUG, QtGui.QHeaderView.Stretch
        )
        self.tabelle.verticalHeader().setVisible(False)
        self.tabelle.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        aufbau.addWidget(self.tabelle, 1)
        zeile = QtGui.QHBoxLayout()
        self.knopf_dazu = knopf(tr("mg.dazu"), tr("mg.dazu.tooltip"), self.werkzeug_dazu)
        self.knopf_entfernen = knopf(
            tr("mg.entfernen"), tr("mg.entfernen.tooltip"), self.zeilen_entfernen
        )
        self.knopf_nummern = knopf(
            tr("mg.aus_nummern"), tr("mg.aus_nummern.tooltip"), self.aus_nummern
        )
        for element in (self.knopf_dazu, self.knopf_entfernen, self.knopf_nummern):
            zeile.addWidget(element)
        zeile.addStretch()
        aufbau.addLayout(zeile)
        return self.rechts

    # --- Liste ----------------------------------------------------------------------------

    def _titel(self, magazin):
        eintrag = msp.finde(self.maschinen, magazin.maschine) if magazin.maschine else None
        maschine = eintrag.name if eintrag is not None else tr("mg.ohne_maschine")
        gilt = "" if not magazin.maschine or not magazin.gilt else " ✓"
        name = magazin.name or tr("mg.ohne_name")
        if name == maschine:  # heißt wie die Maschine: einmal genügt
            return f"{name}{gilt}"
        return f"{name} – {maschine}{gilt}"

    def _liste_fuellen(self, auswahl=None):
        self._fuellt = True
        try:
            self.liste.clear()
            for magazin in self.bibliothek.magazine:
                self.liste.addItem(self._titel(magazin))
        finally:
            self._fuellt = False
        if auswahl is not None and auswahl in self.bibliothek.magazine:
            self.liste.setCurrentRow(self.bibliothek.magazine.index(auswahl))
        self._magazin_gewaehlt(self.liste.currentRow())

    def _magazin_gewaehlt(self, zeile):
        if self._fuellt:
            return
        magazine = self.bibliothek.magazine
        self.magazin = magazine[zeile] if 0 <= zeile < len(magazine) else None
        self.rechts.setEnabled(self.magazin is not None)
        self.knopf_kopieren.setEnabled(self.magazin is not None)
        self.knopf_loeschen.setEnabled(self.magazin is not None)
        self._magazin_zeigen()

    def magazin_anlegen(self):
        """„Neu“: ein Magazin – für die erste Maschine, für die noch keins gilt."""
        frei = next(
            (m for m in self.maschinen if self.bibliothek.magazin_fuer(m.datei) is None), None
        )
        maschine = frei.datei if frei is not None else ""
        name = frei.name if frei is not None else tr("mg.neu.name")
        magazin = self.bibliothek.neues_magazin(name, maschine)
        self._liste_fuellen(magazin)
        return magazin

    def magazin_kopieren(self):
        if self.magazin is None:
            return None
        kopie = self.bibliothek.kopiere_magazin(
            self.magazin, tr("mg.kopie.name", name=self.magazin.name)
        )
        self._liste_fuellen(kopie)
        return kopie

    def magazin_loeschen(self, fragen=True):
        if self.magazin is None:
            return
        if fragen:
            antwort = QtGui.QMessageBox.question(
                self,
                tr("mg.titel"),
                tr("mg.loeschen.frage", name=self.magazin.name),
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                QtGui.QMessageBox.No,
            )
            if antwort != QtGui.QMessageBox.Yes:
                return
        self.bibliothek.magazine.remove(self.magazin)
        self._liste_fuellen(self.bibliothek.magazine[0] if self.bibliothek.magazine else None)

    # --- Das gewählte Magazin -------------------------------------------------------------

    def _magazin_zeigen(self):
        self._fuellt = True
        try:
            magazin = self.magazin
            self.feld_name.setText(magazin.name if magazin else "")
            self.wahl_maschine.clear()
            self.wahl_maschine.addItem(tr("mg.ohne_maschine"), "")
            for eintrag in self.maschinen:
                self.wahl_maschine.addItem(
                    f"{eintrag.name} – {msp.art_text(eintrag)}", eintrag.datei
                )
            index = 0
            if magazin and magazin.maschine:
                index = next(
                    (
                        i + 1
                        for i, e in enumerate(self.maschinen)
                        if msp.gleiche_datei(e.datei, magazin.maschine)
                    ),
                    0,
                )
                if index == 0:  # eine Maschine, die nicht (mehr) im Speicher steht
                    self.wahl_maschine.addItem(magazin.maschine, magazin.maschine)
                    index = self.wahl_maschine.count() - 1
            self.wahl_maschine.setCurrentIndex(index)
            self.haken_gilt.setChecked(bool(magazin and magazin.gilt))
            self.haken_gilt.setEnabled(bool(magazin and magazin.maschine))
            self.feld_plaetze.setValue(magazin.plaetze if magazin else 0)
            self.plaetze_text.setText(platz_text(magazin, self.maschinen) if magazin else "")
            self._tabelle_fuellen()
        finally:
            self._fuellt = False
        self._probleme_zeigen()

    def _tabelle_fuellen(self):
        self.tabelle.setRowCount(0)
        if self.magazin is None:
            return
        werkzeuge = sorted(self.bibliothek.werkzeuge, key=wz.nach_nummer)
        for eintrag in self.magazin.sortierte_eintraege():
            zeile = self.tabelle.rowCount()
            self.tabelle.insertRow(zeile)
            nummer = QtGui.QSpinBox()
            nummer.setRange(1, GROESSTE_NUMMER)
            nummer.setPrefix("T")
            nummer.setValue(max(eintrag.nummer, 1))
            nummer.valueChanged.connect(lambda wert, e=eintrag: self._setze(e, "nummer", wert))
            self.tabelle.setCellWidget(zeile, SPALTE_T, nummer)
            wahl = QtGui.QComboBox()
            for werkzeug in werkzeuge:
                wahl.addItem(werkzeug_text(werkzeug), werkzeug.kennung)
            index = wahl.findData(eintrag.werkzeug)
            if index < 0:
                wahl.addItem(tr("mg.werkzeug_fehlt"), eintrag.werkzeug)
                index = wahl.count() - 1
            wahl.setCurrentIndex(index)
            wahl.currentIndexChanged.connect(
                lambda _i, e=eintrag, w=wahl: self._setze(e, "werkzeug", w.currentData())
            )
            self.tabelle.setCellWidget(zeile, SPALTE_WERKZEUG, wahl)
            name = QtGui.QLineEdit(eintrag.name)
            name.setPlaceholderText(tr("mg.name_steuerung.platzhalter"))
            name.setToolTip(tr("mg.name_steuerung.tooltip"))
            name.textEdited.connect(lambda text, e=eintrag: self._setze(e, "name", text.strip()))
            self.tabelle.setCellWidget(zeile, SPALTE_NAME, name)
            platz = QtGui.QSpinBox()
            platz.setRange(0, GROESSTE_PLATZ)
            platz.setSpecialValueText(tr("mg.nicht_beladen"))
            platz.setPrefix("P")
            platz.setValue(eintrag.platz)
            platz.setToolTip(tr("mg.platz.tooltip"))
            platz.valueChanged.connect(lambda wert, e=eintrag: self._setze(e, "platz", wert))
            self.tabelle.setCellWidget(zeile, SPALTE_PLATZ, platz)
        for spalte, breite in BREITEN.items():
            self.tabelle.setColumnWidth(spalte, breite)

    def _setze(self, eintrag, feld, wert):
        if self._fuellt:
            return
        setattr(eintrag, feld, wert)
        self._probleme_zeigen()

    def _probleme_zeigen(self):
        saetze = probleme(self.magazin, self.maschinen) if self.magazin else []
        self.probleme.setText("\n".join(saetze))

    def _name_geaendert(self, text):
        if self.magazin is not None and not self._fuellt:
            self.magazin.name = text.strip()
            self._titel_auffrischen()

    def _titel_auffrischen(self):
        zeile = self.liste.currentRow()
        if self.magazin is not None and zeile >= 0:
            self.liste.item(zeile).setText(self._titel(self.magazin))

    def _maschine_gewaehlt(self, _index):
        if self.magazin is None or self._fuellt:
            return
        self.magazin.maschine = self.wahl_maschine.currentData() or ""
        if self.magazin.maschine and self.bibliothek.magazin_fuer(self.magazin.maschine) in (
            None,
            self.magazin,
        ):
            self.bibliothek.magazin_gilt(self.magazin)
        else:
            self.magazin.gilt = False
        self._liste_fuellen(self.magazin)

    def _gilt_geaendert(self, an):
        if self.magazin is None or self._fuellt:
            return
        if an:
            self.bibliothek.magazin_gilt(self.magazin)
        else:
            self.magazin.gilt = False
        self._liste_fuellen(self.magazin)

    def _plaetze_geaendert(self, wert):
        if self.magazin is None or self._fuellt:
            return
        self.magazin.plaetze = int(wert)
        self.plaetze_text.setText(platz_text(self.magazin, self.maschinen))
        self._probleme_zeigen()

    # --- Werkzeuge ------------------------------------------------------------------------

    def werkzeug_dazu(self, werkzeug=None):
        """„Werkzeug dazu“: das erste Werkzeug der Werkzeugverwaltung, das noch nicht im Magazin
        ist (oder `werkzeug`), mit der nächsten freien Nummer. Gibt den Eintrag zurück."""
        if self.magazin is None:
            return None
        if werkzeug is None:
            werkzeug = next(
                (
                    w
                    for w in sorted(self.bibliothek.werkzeuge, key=wz.nach_nummer)
                    if self.magazin.eintrag_von(w) is None
                ),
                None,
            )
        if werkzeug is None:
            return None
        eintrag = self.magazin.hinzufuegen(werkzeug)
        self._magazin_zeigen()
        return eintrag

    def zeilen_entfernen(self):
        if self.magazin is None:
            return
        zeilen = sorted({i.row() for i in self.tabelle.selectedIndexes()})
        if not zeilen:
            zeile = self.tabelle.currentRow()
            zeilen = [zeile] if zeile >= 0 else []
        sortiert = self.magazin.sortierte_eintraege()
        weg = {id(sortiert[z]) for z in zeilen if 0 <= z < len(sortiert)}
        self.magazin.eintraege = [e for e in self.magazin.eintraege if id(e) not in weg]
        self._magazin_zeigen()

    def aus_nummern(self):
        """„Aus den Nummern der Werkzeugverwaltung“: jedes Werkzeug mit Nummer, das noch nicht im
        Magazin ist, mit seiner Nummer (ist sie im Magazin schon vergeben: der nächsten freien)."""
        if self.magazin is None:
            return 0
        neu = 0
        for werkzeug in sorted(self.bibliothek.werkzeuge, key=wz.nach_nummer):
            if werkzeug.nummer <= 0 or self.magazin.eintrag_von(werkzeug) is not None:
                continue
            nummer = werkzeug.nummer
            if self.magazin.mit_nummer(nummer) is not None:
                nummer = self.magazin.naechste_nummer()
            self.magazin.hinzufuegen(werkzeug, nummer)
            neu += 1
        self._magazin_zeigen()
        return neu

    def accept(self):
        MagazinDialog.offen = None
        super().accept()

    def reject(self):
        MagazinDialog.offen = None
        super().reject()


def oeffnen(werkzeugdialog):
    """Öffnet „Magazine“ zur Bibliothek des Werkzeugdialogs; gibt das Fenster zurück."""
    dialog = MagazinDialog(werkzeugdialog, werkzeugdialog.bibliothek)
    dialog.open()
    return dialog
