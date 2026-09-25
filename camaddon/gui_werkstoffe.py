# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Werkstoffliste als eigenes Fenster und eigene Werkstoffe (W-002, Abschnitt 4).

Aus der Werkzeugverwaltung heraus („Werkstoffe…“): alle Werkstoffe mit
Suche und ISO-Filter, darunter die Angaben des gewählten. Mitgelieferte sind
schreibgeschützt; „Als eigenen kopieren“ macht eine änderbare Kopie, „Neu“
einen leeren eigenen. Geändert wird die Bibliothek der Werkzeugverwaltung –
gespeichert wird mit deren OK oder Übernehmen.
"""

import re

from PySide import QtCore, QtGui

from . import werkstoffe as ws
from .gui_hilfe import kopfzeile
from .gui_zahlen import Zahlenpruefer, dezimal, zahl_lesen, zahl_zeigen
from .sprache import tr

FENSTER_GROESSE = (900, 600)  # Pixel
ISO, NUMMER, KURZNAME, GRUPPE, HAERTE, BEKANNT = range(6)
GRUPPEN = (
    "baustahl",
    "automatenstahl",
    "einsatzstahl",
    "verguetungsstahl",
    "waelzlagerstahl",
    "formenstahl",
    "kaltarbeitsstahl",
    "warmarbeitsstahl",
    "edelstahl_austenitisch",
    "edelstahl_ferritisch",
    "edelstahl_martensitisch",
    "edelstahl_duplex",
    "edelstahl_ph",
    "grauguss",
    "sphaeroguss",
    "aluminium_knet",
    "aluminium_guss",
    "kupfer",
    "messing",
    "bronze",
    "titan",
    "nickel",
    "kunststoff",
)
ZUSTAENDE = ("", "gegluet", "normalgegluet", "verguetet", "gehaertet", "ausgehaertet")


class WerkstoffDialog(QtGui.QDialog):
    """Alle Werkstoffe, eigene anlegen, kopieren, bearbeiten, löschen.

    `iso_symbol` kommt von der Werkzeugverwaltung (Kästchen in der ISO-Farbe).
    """

    offen = None  # für die Oberflächen-Szenarien

    def __init__(self, eltern, bibliothek, iso_symbol):
        super().__init__(eltern)
        WerkstoffDialog.offen = self
        self.bibliothek = bibliothek
        self.iso_symbol = iso_symbol
        self.geaendert = False
        self._gezeigt = []  # die Werkstoffe in der Tabelle, in ihrer Reihenfolge
        self.setWindowTitle(tr("ws.titel"))
        self.resize(*FENSTER_GROESSE)

        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(kopfzeile(tr("ws.titel"), "werkstoffe"))
        zeile = QtGui.QHBoxLayout()
        self.suche = QtGui.QLineEdit()
        self.suche.setPlaceholderText(tr("ws.suche.platzhalter"))
        self.suche.setToolTip(tr("wv.werkstoff.tooltip"))
        self.suche.textChanged.connect(self._fuellen)
        zeile.addWidget(self.suche, 1)
        self.filter_iso = QtGui.QComboBox()
        self.filter_iso.addItem(tr("ws.alle_iso"), "")
        for iso in ws.ISO_GRUPPEN:
            self.filter_iso.addItem(iso_symbol(iso), f"{iso} – {ws.iso_text(iso)}", iso)
        self.filter_iso.currentIndexChanged.connect(self._fuellen)
        zeile.addWidget(self.filter_iso)
        aufbau.addLayout(zeile)

        self.tabelle = QtGui.QTableWidget(0, 6)
        self.tabelle.setHorizontalHeaderLabels(
            [
                "ISO",
                tr("ws.spalte.nummer"),
                tr("ws.spalte.kurzname"),
                tr("ws.spalte.gruppe"),
                tr("ws.spalte.haerte"),
                tr("ws.spalte.bekannt"),
            ]
        )
        self.tabelle.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tabelle.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tabelle.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tabelle.verticalHeader().hide()
        kopf = self.tabelle.horizontalHeader()
        kopf.setSectionResizeMode(QtGui.QHeaderView.ResizeToContents)
        kopf.setSectionResizeMode(GRUPPE, QtGui.QHeaderView.Stretch)
        self.tabelle.currentCellChanged.connect(lambda *_: self._auswahl_zeigen())
        self.tabelle.cellDoubleClicked.connect(lambda *_: self.bearbeiten())
        aufbau.addWidget(self.tabelle, 1)

        self.angaben = QtGui.QLabel()
        self.angaben.setWordWrap(True)
        self.angaben.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        aufbau.addWidget(self.angaben)

        zeile = QtGui.QHBoxLayout()
        self.knopf_neu = _knopf(tr("ws.neu"), tr("ws.neu.tooltip"), self.neu)
        self.knopf_kopieren = _knopf(tr("ws.kopieren"), tr("ws.kopieren.tooltip"), self.kopieren)
        self.knopf_bearbeiten = _knopf(
            tr("ws.bearbeiten"), tr("ws.bearbeiten.tooltip"), self.bearbeiten
        )
        self.knopf_loeschen = _knopf(tr("ws.loeschen"), tr("ws.loeschen.tooltip"), self.loeschen)
        for knopf in (
            self.knopf_neu,
            self.knopf_kopieren,
            self.knopf_bearbeiten,
            self.knopf_loeschen,
        ):
            zeile.addWidget(knopf)
        zeile.addStretch()
        aufbau.addLayout(zeile)

        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Close)
        knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(knoepfe)
        self._fuellen()

    def keyPressEvent(self, ereignis):
        """Enter in der Suche schließt das Fenster nicht (wie in der Werkzeugverwaltung)."""
        if ereignis.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            ereignis.accept()
            return
        super().keyPressEvent(ereignis)

    # --- Tabelle ------------------------------------------------------------------------

    def _fuellen(self, *_, auswahl=None):
        """Zeigt, was zu Suche und Filter passt: eigene zuerst, dann nach ISO-Gruppe."""
        vorher = auswahl or self.gewaehlt
        suche = self.suche.text().strip()
        iso = self.filter_iso.currentData()
        alle = ws.sortiert(self.bibliothek.eigene_werkstoffe) + ws.sortiert(ws.mitgelieferte())
        self._gezeigt = [
            w for w in alle if (not suche or ws.passt(w, suche)) and (not iso or w.iso == iso)
        ]
        self.tabelle.setRowCount(len(self._gezeigt))
        for zeile, w in enumerate(self._gezeigt):
            zellen = [
                _iso_zelle(self.iso_symbol(w.iso), w.iso),
                QtGui.QTableWidgetItem(w.nummer),
                QtGui.QTableWidgetItem(w.kurzname),
                QtGui.QTableWidgetItem(_gruppe_mit_zustand(w)),
                QtGui.QTableWidgetItem(dezimal(w.haerte)),
                QtGui.QTableWidgetItem(w.bekannt_als),
            ]
            for spalte, zelle in enumerate(zellen):
                if w.eigen:
                    schrift = zelle.font()
                    schrift.setItalic(True)
                    zelle.setFont(schrift)
                    zelle.setToolTip(tr("ws.eigen.tooltip"))
                self.tabelle.setItem(zeile, spalte, zelle)
        zeile = self._gezeigt.index(vorher) if vorher in self._gezeigt else 0
        if self._gezeigt:
            self.tabelle.setCurrentCell(zeile, KURZNAME)
        self._auswahl_zeigen()

    @property
    def gewaehlt(self):
        """Der gewählte Werkstoff, oder None."""
        zeile = self.tabelle.currentRow()
        return self._gezeigt[zeile] if 0 <= zeile < len(self._gezeigt) else None

    def waehle(self, kennung):
        """Wählt den Werkstoff mit dieser Kennung (Suche und Filter werden geleert)."""
        self.suche.clear()
        self.filter_iso.setCurrentIndex(0)
        werkstoff = ws.finde(self.bibliothek.alle_werkstoffe(), kennung)
        self._fuellen(auswahl=werkstoff)

    def _auswahl_zeigen(self):
        w = self.gewaehlt
        self.knopf_kopieren.setEnabled(w is not None)
        self.knopf_bearbeiten.setEnabled(w is not None and w.eigen)
        self.knopf_loeschen.setEnabled(w is not None and w.eigen)
        if w is None:
            self.angaben.setText(tr("ws.nichts_gefunden"))
            return
        zeilen = [f"<b>{ws.anzeige(w)}</b>"]
        if w.zusammensetzung:
            zeilen.append(tr("wv.info.zusammensetzung", text=dezimal(w.zusammensetzung)))
        teile = []
        if w.haerte:
            teile.append(tr("wv.info.haerte", text=dezimal(w.haerte)))
        if w.zugfestigkeit:
            teile.append(tr("wv.info.zugfestigkeit", text=dezimal(w.zugfestigkeit)))
        if w.kc11:
            teile.append(tr("ws.info.kc", kc=zahl_zeigen(w.kc11), mc=zahl_zeigen(w.mc)))
        if teile:
            zeilen.append("  ·  ".join(teile))
        zeilen.append(tr("ws.info.eigen") if w.eigen else tr("ws.info.mitgeliefert"))
        self.angaben.setText("<br>".join(zeilen))

    # --- Aktionen -----------------------------------------------------------------------

    def neu(self):
        """„Neu“: ein leerer eigener Werkstoff, gleich im Bearbeiten-Fenster."""
        w = ws.Werkstoff(ws.neue_kennung(self.bibliothek.alle_werkstoffe()), eigen=True)
        if self._bearbeiten_mit(w, neu=True):
            self.bibliothek.eigene_werkstoffe.append(w)
            self._geaendert(auswahl=w)

    def kopieren(self):
        """„Als eigenen kopieren“: alle Angaben, neue Kennung, änderbar."""
        vorlage = self.gewaehlt
        if vorlage is None:
            return None
        kopie = ws.Werkstoff.aus_dict(vorlage.als_dict(), eigen=True)
        kopie.kennung = ws.neue_kennung(self.bibliothek.alle_werkstoffe())
        self.bibliothek.eigene_werkstoffe.append(kopie)
        self._geaendert(auswahl=kopie)
        return kopie

    def bearbeiten(self):
        """„Bearbeiten…“: nur eigene Werkstoffe."""
        w = self.gewaehlt
        if w is None or not w.eigen:
            return
        if self._bearbeiten_mit(w):
            self._geaendert(auswahl=w)

    def loeschen(self, fragen=True):
        """„Löschen“: nur eigene; eigene Schnittwerte der Werkzeuge dafür gehen mit."""
        w = self.gewaehlt
        if w is None or not w.eigen:
            return
        betroffen = [t for t in self.bibliothek.werkzeuge if t.hat_eigene(w.kennung)]
        if fragen:
            frage = tr("ws.loeschen.frage", werkstoff=ws.anzeige(w))
            if betroffen:
                frage += "\n\n" + tr("ws.loeschen.schnittwerte", anzahl=len(betroffen))
            antwort = QtGui.QMessageBox.question(
                self,
                tr("ws.titel"),
                frage,
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                QtGui.QMessageBox.No,
            )
            if antwort != QtGui.QMessageBox.Yes:
                return
        for werkzeug in betroffen:
            werkzeug.eigene_loeschen(w.kennung)
        self.bibliothek.eigene_werkstoffe.remove(w)
        self._geaendert()

    def _bearbeiten_mit(self, werkstoff, neu=False):
        fenster = WerkstoffBearbeiten(self, werkstoff, self.iso_symbol, neu)
        ergebnis = fenster.exec() == QtGui.QDialog.Accepted
        WerkstoffBearbeiten.offen = None
        return ergebnis

    def _geaendert(self, auswahl=None):
        self.geaendert = True
        self._fuellen(auswahl=auswahl)


class WerkstoffBearbeiten(QtGui.QDialog):
    """Die Angaben eines eigenen Werkstoffs; OK übernimmt sie, Abbrechen nicht."""

    offen = None  # für die Oberflächen-Szenarien

    def __init__(self, eltern, werkstoff, iso_symbol, neu=False):
        super().__init__(eltern)
        WerkstoffBearbeiten.offen = self
        self.werkstoff = werkstoff
        self.setWindowTitle(tr("ws.neu.titel") if neu else tr("ws.bearbeiten.titel"))
        self.setMinimumWidth(520)
        formular = QtGui.QFormLayout(self)
        w = werkstoff

        self.feld_nummer = _textfeld(w.nummer, tr("ws.feld.nummer.platzhalter"))
        formular.addRow(tr("ws.spalte.nummer"), self.feld_nummer)
        self.feld_kurzname = _textfeld(w.kurzname, tr("ws.feld.kurzname.platzhalter"))
        self.feld_kurzname.textChanged.connect(self._pruefen)
        formular.addRow(_fett(tr("ws.spalte.kurzname")), self.feld_kurzname)
        self.feld_gruppe = _auswahl_frei(GRUPPEN, ws.gruppe_text, w.gruppe)
        formular.addRow(tr("ws.spalte.gruppe"), self.feld_gruppe)
        self.feld_zustand = _auswahl_frei(ZUSTAENDE, ws.zustand_text, w.zustand)
        formular.addRow(tr("ws.feld.zustand"), self.feld_zustand)
        self.feld_iso = QtGui.QComboBox()
        for iso in ws.ISO_GRUPPEN:
            self.feld_iso.addItem(iso_symbol(iso), f"{iso} – {ws.iso_text(iso)}", iso)
        self.feld_iso.setCurrentIndex(max(self.feld_iso.findData(w.iso), 0))
        formular.addRow(tr("ws.feld.iso"), self.feld_iso)
        self.feld_bekannt = _textfeld(w.bekannt_als, tr("ws.feld.bekannt.platzhalter"))
        formular.addRow(tr("ws.spalte.bekannt"), self.feld_bekannt)
        # Gespeichert wird mit Punkt; gezeigt und getippt im Format der Oberfläche.
        self.feld_zusammensetzung = _textfeld(
            dezimal(w.zusammensetzung), tr("ws.feld.zusammensetzung.platzhalter")
        )
        formular.addRow(tr("ws.feld.zusammensetzung"), self.feld_zusammensetzung)
        self.feld_haerte = _textfeld(dezimal(w.haerte), tr("ws.feld.haerte.platzhalter"))
        formular.addRow(tr("ws.spalte.haerte"), self.feld_haerte)
        self.feld_rm = _textfeld(dezimal(w.zugfestigkeit), tr("ws.feld.rm.platzhalter"))
        formular.addRow(tr("ws.feld.rm"), self.feld_rm)
        self.feld_kc = QtGui.QLineEdit(zahl_zeigen(w.kc11))
        self.feld_kc.setValidator(Zahlenpruefer(self.feld_kc))
        self.feld_kc.setPlaceholderText(tr("feld.unbekannt"))
        self.feld_kc.setToolTip(tr("ws.feld.kc.tooltip"))
        formular.addRow(tr("ws.feld.kc"), self.feld_kc)
        self.feld_mc = QtGui.QLineEdit(zahl_zeigen(w.mc))
        self.feld_mc.setValidator(Zahlenpruefer(self.feld_mc))
        self.feld_mc.setPlaceholderText(tr("feld.unbekannt"))
        self.feld_mc.setToolTip(tr("ws.feld.kc.tooltip"))
        formular.addRow(tr("ws.feld.mc"), self.feld_mc)

        self.hinweis = QtGui.QLabel(tr("ws.hinweis.kurzname"))
        self.hinweis.setStyleSheet("color: #c0392b;")
        formular.addRow(self.hinweis)
        self.knoepfe = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
        )
        self.knoepfe.accepted.connect(self.accept)
        self.knoepfe.rejected.connect(self.reject)
        formular.addRow(self.knoepfe)
        self._pruefen()

    def _pruefen(self, *_):
        """Ohne Kurzname kein Werkstoff – das steht sofort am Feld."""
        vollstaendig = bool(self.feld_kurzname.text().strip())
        self.hinweis.setVisible(not vollstaendig)
        self.knoepfe.button(QtGui.QDialogButtonBox.Ok).setEnabled(vollstaendig)

    def accept(self):
        w = self.werkstoff
        w.nummer = self.feld_nummer.text().strip()
        w.kurzname = self.feld_kurzname.text().strip()
        w.gruppe = _gewaehlter_schluessel(self.feld_gruppe, GRUPPEN, ws.gruppe_text)
        w.zustand = _gewaehlter_schluessel(self.feld_zustand, ZUSTAENDE, ws.zustand_text)
        w.iso = self.feld_iso.currentData()
        w.bekannt_als = self.feld_bekannt.text().strip()
        w.zusammensetzung = _mit_punkt(self.feld_zusammensetzung.text().strip())
        w.haerte = _mit_punkt(self.feld_haerte.text().strip())
        w.zugfestigkeit = _mit_punkt(self.feld_rm.text().strip())
        w.kc11 = zahl_lesen(self.feld_kc.text())
        w.mc = zahl_lesen(self.feld_mc.text())
        super().accept()


def _iso_zelle(symbol, iso):
    """Nur das Kästchen – der Buchstabe steht schon darin; in Worten als Tooltip."""
    zelle = QtGui.QTableWidgetItem(symbol, "")
    zelle.setToolTip(f"{iso} – {ws.iso_text(iso)}")
    return zelle


def _mit_punkt(text):
    """Zahlen mit Komma („17,5“) wie in der Datei mit Punkt speichern („17.5“)."""
    return re.sub(r"(?<=\d),(?=\d)", ".", text)


def _gruppe_mit_zustand(werkstoff):
    gruppe = ws.gruppe_text(werkstoff.gruppe)
    if werkstoff.zustand:
        return f"{gruppe}, {ws.zustand_text(werkstoff.zustand)}" if gruppe else werkstoff.zustand
    return gruppe


def _auswahl_frei(schluessel, text_von, aktuell):
    """Auswahlliste mit den bekannten Einträgen, in die man auch Eigenes tippen kann."""
    wahl = QtGui.QComboBox()
    wahl.setEditable(True)
    wahl.setInsertPolicy(QtGui.QComboBox.NoInsert)
    for s in schluessel:
        wahl.addItem(text_von(s) if s else "", s)
    index = wahl.findData(aktuell)
    if index >= 0:
        wahl.setCurrentIndex(index)
    else:
        wahl.setEditText(aktuell)
    return wahl


def _gewaehlter_schluessel(wahl, schluessel, text_von):
    """Bekannter Text → sein Schlüssel (folgt dann der Sprache); sonst der getippte Text."""
    text = wahl.currentText().strip()
    for s in schluessel:
        if text == (text_von(s) if s else ""):
            return s
    return text


def _textfeld(text, platzhalter):
    feld = QtGui.QLineEdit(text)
    feld.setPlaceholderText(platzhalter)
    return feld


def _fett(text):
    beschriftung = QtGui.QLabel(text)
    schrift = beschriftung.font()
    schrift.setBold(True)
    beschriftung.setFont(schrift)
    return beschriftung


def _knopf(text, tooltip, aktion):
    knopf = QtGui.QPushButton(text)
    knopf.setToolTip(tooltip)
    knopf.setAutoDefault(False)
    knopf.clicked.connect(lambda: aktion())
    return knopf
