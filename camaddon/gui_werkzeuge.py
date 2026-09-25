# SPDX-License-Identifier: LGPL-2.1-or-later
"""Befehl und Dialog „Werkzeugverwaltung“ (W-002).

Oben der Werkstoff – er kommt zuerst, weil die Schnittwerte von ihm
abhängen –, links die Werkzeuge, rechts das gewählte Werkzeug. Der Dialog
arbeitet an einer Kopie der Bibliothek und speichert wie die Einstellungen
von FreeCAD: OK, Übernehmen, Abbrechen (fragt nach, wenn etwas geändert ist).
Die Daten stehen in werkzeuge.py und werkstoffe.py.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, symbol
from . import uebergabe_werkzeuge as ue
from . import werkstoffe as ws
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_schnittwerte import SchnittwertBereich
from .gui_werkstoffe import WerkstoffDialog
from .gui_zahlen import Zahlenpruefer, dezimal, zahl_lesen, zahl_zeigen
from .sprache import tr

FENSTER_GROESSE = (1100, 760)  # Breite, Höhe in Pixeln
LISTE_BREITE = 300  # Pixel, Startbreite der Werkzeugliste
GROESSTE_NUMMER = 9999
GROESSTE_SCHNEIDENZAHL = 20
SYMBOL_GROESSE = 16  # Pixel, Kästchen mit dem ISO-Buchstaben

# Farben der ISO-Gruppen, wie auf Wendeplatten-Schachteln und in Katalogen:
# (Hintergrund, Schrift).
ISO_FARBEN = {
    "P": ("#1c63b7", "#ffffff"),
    "M": ("#f2c500", "#000000"),
    "K": ("#d7261e", "#ffffff"),
    "N": ("#2e9a44", "#ffffff"),
    "S": ("#e07b12", "#ffffff"),
    "H": ("#8c8c8c", "#ffffff"),
}


class BefehlWerkzeugverwaltung:
    """Öffnet die Werkzeugverwaltung – oder holt sie nach vorn, wenn sie schon offen ist."""

    def GetResources(self):
        return {
            "Pixmap": symbol("werkzeugverwaltung.svg"),
            "MenuText": tr("befehl.werkzeugverwaltung.titel"),
            "ToolTip": tr("befehl.werkzeugverwaltung.tooltip"),
        }

    def IsActive(self):
        return True

    def Activated(self):
        offen = WerkzeugDialog.offen
        if offen is not None and offen.isVisible():
            offen.raise_()
            offen.activateWindow()
            return
        dialog = WerkzeugDialog()
        dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        dialog.show()


def iso_symbol(iso):
    """Kästchen in der Farbe der ISO-Gruppe mit ihrem Buchstaben."""
    hintergrund, schrift = ISO_FARBEN[iso]
    bild = QtGui.QPixmap(SYMBOL_GROESSE, SYMBOL_GROESSE)
    bild.fill(QtCore.Qt.transparent)
    maler = QtGui.QPainter(bild)
    maler.setRenderHint(QtGui.QPainter.Antialiasing)
    maler.setBrush(QtGui.QColor(hintergrund))
    maler.setPen(QtCore.Qt.NoPen)
    maler.drawRoundedRect(0, 0, SYMBOL_GROESSE, SYMBOL_GROESSE, 3, 3)
    maler.setPen(QtGui.QColor(schrift))
    schriftart = maler.font()
    schriftart.setBold(True)
    schriftart.setPixelSize(SYMBOL_GROESSE - 4)
    maler.setFont(schriftart)
    maler.drawText(bild.rect(), QtCore.Qt.AlignCenter, iso)
    maler.end()
    return QtGui.QIcon(bild)


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def werkstoffe_anbieten(wahl, bibliothek):
    """Füllt eine Werkstoff-Auswahl: „Alle Werkstoffe“, eigene, dann die mitgelieferten nach ISO-Gruppe.

    Auch der Dialog „Schnittwerte in den Job“ benutzt sie.
    """
    wahl.blockSignals(True)
    wahl.clear()
    wahl.addItem(tr("wv.alle_werkstoffe"), wz.ALLE)
    gruppen = [ws.sortiert(bibliothek.eigene_werkstoffe)]
    mitgeliefert = ws.sortiert(ws.mitgelieferte())
    for iso in ws.ISO_GRUPPEN:
        gruppen.append([w for w in mitgeliefert if w.iso == iso])
    for gruppe in gruppen:
        if not gruppe:
            continue
        wahl.insertSeparator(wahl.count())
        for werkstoff in gruppe:
            wahl.addItem(iso_symbol(werkstoff.iso), ws.anzeige(werkstoff), werkstoff.kennung)
    wahl.blockSignals(False)


class WerkzeugDialog(QtGui.QDialog):
    """Die Werkzeugverwaltung. Die Aktionen hinter den Knöpfen sind öffentliche Methoden."""

    offen = None  # das zuletzt geöffnete Fenster – für die Oberflächen-Szenarien

    def __init__(self, eltern=None, pfad=None):
        super().__init__(eltern or FreeCADGui.getMainWindow())
        WerkzeugDialog.offen = self
        self.pfad = pfad or wz.datei_pfad()
        self.bibliothek = self._laden()
        self._gespeichert = self.bibliothek.kopie()
        self.werkzeug = None  # das gewählte Werkzeug
        self._fuellt = False  # während Felder gefüllt werden, zählt keine Eingabe

        self.setWindowTitle(tr("wv.titel"))
        self.resize(*FENSTER_GROESSE)
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(self._bereich_werkstoff())
        teilung = QtGui.QSplitter()
        teilung.addWidget(self._bereich_liste())
        teilung.addWidget(self._bereich_werkzeug())
        teilung.setStretchFactor(1, 1)
        teilung.setSizes([LISTE_BREITE, FENSTER_GROESSE[0] - LISTE_BREITE])
        aufbau.addWidget(teilung, 1)
        unten = QtGui.QHBoxLayout()
        self.knopf_cam = self._knopf(tr("wv.cam"), tr("wv.cam.tooltip"), self.an_cam_uebergeben)
        self.knopf_cam.setEnabled(ue.verfuegbar())
        unten.addWidget(self.knopf_cam)
        unten.addStretch()
        unten.addWidget(self._knoepfe())
        aufbau.addLayout(unten)

        self._werkstoffe_anbieten()
        self.waehle_werkstoff(_parameter().GetString("WvWerkstoff", wz.ALLE))
        self._liste_aufbauen(auswahl=self._zuletzt_gewaehlt())

    # --- Aufbau -------------------------------------------------------------------

    def _bereich_werkstoff(self):
        rahmen = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(rahmen)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.addWidget(kopfzeile(tr("wv.werkstoff"), "werkstoffe"))
        self.wahl_werkstoff = QtGui.QComboBox()
        self.wahl_werkstoff.setEditable(True)
        self.wahl_werkstoff.setInsertPolicy(QtGui.QComboBox.NoInsert)
        self.wahl_werkstoff.setToolTip(tr("wv.werkstoff.tooltip"))
        self.wahl_werkstoff.setMaxVisibleItems(20)
        suche = QtGui.QCompleter(self.wahl_werkstoff.model(), self.wahl_werkstoff)
        suche.setFilterMode(QtCore.Qt.MatchContains)
        suche.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        suche.setCompletionMode(QtGui.QCompleter.PopupCompletion)
        self.wahl_werkstoff.setCompleter(suche)
        self.wahl_werkstoff.currentIndexChanged.connect(self._werkstoff_gewaehlt)
        # Getippter Text, der zu nichts passt, weicht wieder dem gewählten Werkstoff.
        self.wahl_werkstoff.lineEdit().editingFinished.connect(self._werkstoff_text_zuruecksetzen)
        zeile = QtGui.QHBoxLayout()
        zeile.addWidget(self.wahl_werkstoff, 1)
        self.knopf_werkstoffe = self._knopf(
            tr("wv.werkstoffe"), tr("wv.werkstoffe.tooltip"), self.werkstoffe_zeigen
        )
        zeile.addWidget(self.knopf_werkstoffe)
        aufbau.addLayout(zeile)
        self.werkstoff_info = QtGui.QLabel()
        self.werkstoff_info.setWordWrap(True)
        self.werkstoff_info.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        aufbau.addWidget(self.werkstoff_info)
        return rahmen

    def _bereich_liste(self):
        rahmen = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(rahmen)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.addWidget(kopfzeile(tr("wv.werkzeuge"), "werkzeuge"))
        self.liste = QtGui.QListWidget()
        self.liste.currentRowChanged.connect(self._werkzeug_gewaehlt)
        aufbau.addWidget(self.liste, 1)
        zeile = QtGui.QHBoxLayout()
        self.knopf_neu = self._knopf(tr("wv.neu"), tr("wv.neu.tooltip"), self.werkzeug_anlegen)
        self.knopf_kopieren = self._knopf(
            tr("wv.kopieren"), tr("wv.kopieren.tooltip"), self.werkzeug_kopieren
        )
        self.knopf_loeschen = self._knopf(
            tr("wv.loeschen"), tr("wv.loeschen.tooltip"), self.werkzeug_loeschen
        )
        for knopf in (self.knopf_neu, self.knopf_kopieren, self.knopf_loeschen):
            zeile.addWidget(knopf)
        aufbau.addLayout(zeile)
        return rahmen

    def _knopf(self, text, tooltip, aktion):
        knopf = QtGui.QPushButton(text)
        knopf.setToolTip(tooltip)
        knopf.setAutoDefault(False)  # Enter in einem Feld soll keinen Knopf auslösen
        knopf.clicked.connect(aktion)
        return knopf

    def _bereich_werkzeug(self):
        rahmen = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(rahmen)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.addWidget(kopfzeile(tr("wv.werkzeug"), "werkzeuge"))
        self.leer = QtGui.QLabel(tr("wv.leer"))
        self.leer.setWordWrap(True)
        aufbau.addWidget(self.leer)

        # Zwei Spalten aus Beschriftung und Feld, damit unten Platz für die
        # Schnittwerte bleibt.
        self.formular_rahmen = QtGui.QWidget()
        gitter = QtGui.QGridLayout(self.formular_rahmen)
        gitter.setContentsMargins(0, 0, 0, 0)
        gitter.setColumnStretch(1, 1)
        gitter.setColumnStretch(3, 1)

        self.feld_nummer = QtGui.QSpinBox()
        self.feld_nummer.setRange(1, GROESSTE_NUMMER)
        self.feld_nummer.setPrefix("T")
        self.feld_nummer.setToolTip(tr("wv.nummer.tooltip"))
        self.feld_nummer.valueChanged.connect(self._nummer_geaendert)
        self.feld_nummer.editingFinished.connect(self._nach_nummer)

        self.feld_art = QtGui.QComboBox()
        for art in wz.ARTEN:
            self.feld_art.addItem(wz.art_text(art), art)
        self.feld_art.setToolTip(tr("wv.art.tooltip"))
        self.feld_art.currentIndexChanged.connect(self._art_geaendert)

        self.feld_durchmesser = self._zahlenfeld(tr("wv.durchmesser.tooltip"), "durchmesser")

        self.feld_schneiden = QtGui.QSpinBox()
        self.feld_schneiden.setRange(1, GROESSTE_SCHNEIDENZAHL)
        self.feld_schneiden.setToolTip(tr("wv.schneiden.tooltip"))
        self.feld_schneiden.valueChanged.connect(self._schneiden_geaendert)

        self.feld_schneidenlaenge = self._zahlenfeld(
            tr("wv.schneidenlaenge.tooltip"), "schneidenlaenge"
        )
        self.feld_eckradius = self._zahlenfeld(tr("wv.eckradius.tooltip"), "eckradius")
        self.zeile_eckradius = _mit_einheit(self.feld_eckradius, "mm")
        self.beschriftung_eckradius = QtGui.QLabel(tr("wv.eckradius"))

        self.feld_schneidstoff = QtGui.QComboBox()
        self.feld_schneidstoff.addItem(tr("wv.schneidstoff.vhm"), wz.VHM)
        self.feld_schneidstoff.addItem(tr("wv.schneidstoff.hss"), wz.HSS)
        self.feld_schneidstoff.setToolTip(tr("wv.schneidstoff.tooltip"))
        self.feld_schneidstoff.currentIndexChanged.connect(self._schneidstoff_geaendert)

        self.feld_bezeichnung = QtGui.QLineEdit()
        self.feld_bezeichnung.setPlaceholderText(tr("wv.bezeichnung.platzhalter"))
        self.feld_bezeichnung.setToolTip(tr("wv.bezeichnung.tooltip"))
        self.feld_bezeichnung.textEdited.connect(self._bezeichnung_geaendert)

        zeilen = [
            (QtGui.QLabel(tr("wv.nummer")), self.feld_nummer),
            (QtGui.QLabel(tr("wv.art")), self.feld_art),
            (_fett(tr("wv.durchmesser")), _mit_einheit(self.feld_durchmesser, "mm")),
            (_fett(tr("wv.schneiden")), self.feld_schneiden),
            (
                QtGui.QLabel(tr("wv.schneidenlaenge")),
                _mit_einheit(self.feld_schneidenlaenge, "mm"),
            ),
            (self.beschriftung_eckradius, self.zeile_eckradius),
            (QtGui.QLabel(tr("wv.schneidstoff")), self.feld_schneidstoff),
        ]
        for i, (beschriftung, feld) in enumerate(zeilen):
            gitter.addWidget(beschriftung, i // 2, 2 * (i % 2))
            gitter.addWidget(feld, i // 2, 2 * (i % 2) + 1)
        unten = (len(zeilen) + 1) // 2
        gitter.addWidget(QtGui.QLabel(tr("wv.bezeichnung")), unten, 0)
        gitter.addWidget(self.feld_bezeichnung, unten, 1, 1, 3)

        self.hinweis = QtGui.QLabel()
        self.hinweis.setWordWrap(True)
        self.hinweis.setStyleSheet("color: #c0392b;")
        gitter.addWidget(self.hinweis, unten + 1, 0, 1, 4)

        aufbau.addWidget(self.formular_rahmen)
        self.schnittwerte = SchnittwertBereich(self._schnittwerte_geaendert)
        aufbau.addWidget(self.schnittwerte, 1)
        return rahmen

    def _zahlenfeld(self, tooltip, eigenschaft):
        feld = QtGui.QLineEdit()
        feld.setValidator(Zahlenpruefer(feld))
        feld.setPlaceholderText(tr("feld.unbekannt"))
        feld.setToolTip(tooltip)
        feld.editingFinished.connect(lambda: self._zahl_uebernehmen(feld, eigenschaft))
        return feld

    def _knoepfe(self):
        self.knoepfe = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Apply | QtGui.QDialogButtonBox.Cancel
        )
        self.knoepfe.accepted.connect(self.accept)
        self.knoepfe.rejected.connect(self.reject)
        self.knoepfe.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.uebernehmen)
        return self.knoepfe

    def keyPressEvent(self, ereignis):
        """Enter bestätigt nur das Feld, in dem es gedrückt wurde (wie B-005).

        Das Feld übernimmt seinen Wert und reicht die Taste weiter; käme sie
        hier bei QDialog an, drückte sie OK. Die Knopfleiste macht OK beim
        Zeigen von selbst zum Standardknopf – setDefault(False) hilft nicht
        (ausprobiert im Szenario).
        """
        if ereignis.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            ereignis.accept()
            return
        super().keyPressEvent(ereignis)

    # --- Werkstoff ------------------------------------------------------------------

    def _werkstoffe_anbieten(self):
        werkstoffe_anbieten(self.wahl_werkstoff, self.bibliothek)

    @property
    def werkstoff(self):
        """Die Kennung des gewählten Werkstoffs, oder wz.ALLE."""
        return self.wahl_werkstoff.currentData() or wz.ALLE

    def waehle_werkstoff(self, kennung):
        """Wählt den Werkstoff mit dieser Kennung; unbekannt: „Alle Werkstoffe“."""
        index = self.wahl_werkstoff.findData(kennung)
        self.wahl_werkstoff.setCurrentIndex(max(index, 0))
        self._werkstoff_gewaehlt()

    def _werkstoff_gewaehlt(self, *_):
        kennung = self.werkstoff
        _parameter().SetString("WvWerkstoff", kennung)
        werkstoff = ws.finde(self.bibliothek.alle_werkstoffe(), kennung)
        self.werkstoff_info.setText(self._info_text(werkstoff))
        self._schnittwerte_zeigen()

    def werkstoffe_zeigen(self):
        """„Werkstoffe…“: die ganze Liste, eigene anlegen und ändern; danach ist der dort
        gewählte Werkstoff auch hier gewählt."""
        dialog = WerkstoffDialog(self, self.bibliothek, iso_symbol)
        if self.werkstoff != wz.ALLE:
            dialog.waehle(self.werkstoff)
        dialog.exec()
        WerkstoffDialog.offen = None
        gewaehlt = dialog.gewaehlt
        if dialog.geaendert:
            self._werkstoffe_anbieten()
        self.waehle_werkstoff(gewaehlt.kennung if gewaehlt is not None else self.werkstoff)

    def _werkstoff_text_zuruecksetzen(self):
        wahl = self.wahl_werkstoff
        text = wahl.itemText(wahl.currentIndex())
        if wahl.currentText() != text:
            wahl.setEditText(text)

    def _info_text(self, werkstoff):
        """Zusammensetzung, Härte, Festigkeit und ISO-Gruppe des gewählten Werkstoffs."""
        if werkstoff is None:
            return tr("wv.alle_werkstoffe.info")
        zeilen = []
        if werkstoff.zusammensetzung:
            zeilen.append(tr("wv.info.zusammensetzung", text=dezimal(werkstoff.zusammensetzung)))
        teile = []
        if werkstoff.haerte:
            teile.append(tr("wv.info.haerte", text=dezimal(werkstoff.haerte)))
        if werkstoff.zugfestigkeit:
            teile.append(tr("wv.info.zugfestigkeit", text=dezimal(werkstoff.zugfestigkeit)))
        teile.append(tr("wv.info.iso", iso=werkstoff.iso, text=ws.iso_text(werkstoff.iso)))
        zeilen.append("  ·  ".join(teile))
        return "\n".join(zeilen)

    # --- Werkzeugliste ----------------------------------------------------------------

    def _zuletzt_gewaehlt(self):
        kennung = _parameter().GetString("WvWerkzeug", "")
        return next((w for w in self.bibliothek.werkzeuge if w.kennung == kennung), None)

    def _liste_aufbauen(self, auswahl=None):
        """Baut die Liste neu (sortiert nach Nummer) und wählt `auswahl` oder das erste Werkzeug."""
        self._reihenfolge = self.bibliothek.sortierte_werkzeuge()
        if auswahl in self._reihenfolge:
            zeile = self._reihenfolge.index(auswahl)
        else:
            zeile = 0 if self._reihenfolge else -1
        self.liste.blockSignals(True)
        self.liste.clear()
        for werkzeug in self._reihenfolge:
            self.liste.addItem(dezimal(wz.zeile(werkzeug)))
        self.liste.setCurrentRow(zeile)
        self.liste.blockSignals(False)
        self._werkzeug_gewaehlt(zeile)

    def _zeile_auffrischen(self):
        """Schreibt die Listenzeile des gewählten Werkzeugs neu, ohne die Liste neu zu bauen."""
        if self.werkzeug is None:
            return
        eintrag = self.liste.item(self._reihenfolge.index(self.werkzeug))
        eintrag.setText(dezimal(wz.zeile(self.werkzeug)))

    def _werkzeug_gewaehlt(self, zeile):
        self.werkzeug = self._reihenfolge[zeile] if 0 <= zeile < len(self._reihenfolge) else None
        if self.werkzeug is not None:
            _parameter().SetString("WvWerkzeug", self.werkzeug.kennung)
        self._felder_fuellen()

    def werkzeug_anlegen(self):
        """„Neu“: ein Schaftfräser mit der nächsten freien Nummer; der Durchmesser wartet."""
        werkzeug = self.bibliothek.neues_werkzeug()
        self._liste_aufbauen(auswahl=werkzeug)
        self.feld_durchmesser.setFocus()
        return werkzeug

    def werkzeug_kopieren(self):
        """„Kopieren“: das gewählte Werkzeug mit allen Werten und neuer Nummer."""
        if self.werkzeug is None:
            return None
        kopie = self.bibliothek.kopiere(self.werkzeug)
        self._liste_aufbauen(auswahl=kopie)
        return kopie

    def werkzeug_loeschen(self, fragen=True):
        """„Löschen“: nach Rückfrage; `fragen=False` für die Szenarien."""
        if self.werkzeug is None:
            return
        if fragen:
            antwort = QtGui.QMessageBox.question(
                self,
                tr("wv.titel"),
                tr("wv.loeschen.frage", werkzeug=dezimal(wz.zeile(self.werkzeug))),
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                QtGui.QMessageBox.No,
            )
            if antwort != QtGui.QMessageBox.Yes:
                return
        zeile = self._reihenfolge.index(self.werkzeug)
        self.bibliothek.entferne(self.werkzeug)
        naechstes = self.bibliothek.sortierte_werkzeuge()
        self._liste_aufbauen(
            auswahl=naechstes[min(zeile, len(naechstes) - 1)] if naechstes else None
        )

    # --- Felder des Werkzeugs --------------------------------------------------------

    def _felder_fuellen(self):
        """Zeigt das gewählte Werkzeug in den Feldern – oder den Hinweis, dass es keins gibt."""
        w = self.werkzeug
        self.leer.setVisible(w is None)
        self.formular_rahmen.setVisible(w is not None)
        self.knopf_kopieren.setEnabled(w is not None)
        self.knopf_loeschen.setEnabled(w is not None)
        if w is None:
            self._schnittwerte_zeigen()
            return
        self._fuellt = True
        self.feld_nummer.setValue(w.nummer)
        self.feld_art.setCurrentIndex(self.feld_art.findData(w.art))
        self.feld_durchmesser.setText(zahl_zeigen(w.durchmesser))
        self.feld_schneiden.setValue(w.schneiden)
        self.feld_schneidenlaenge.setText(zahl_zeigen(w.schneidenlaenge))
        self.feld_eckradius.setText(zahl_zeigen(w.eckradius))
        self.feld_schneidstoff.setCurrentIndex(self.feld_schneidstoff.findData(w.schneidstoff))
        self.feld_bezeichnung.setText(w.bezeichnung)
        self._fuellt = False
        self._eckradius_zeigen()
        self._hinweise()
        self._schnittwerte_zeigen()

    def _schnittwerte_zeigen(self):
        """Die Schnittwerte des gewählten Werkzeugs für den gewählten Werkstoff."""
        kennung = self.werkstoff
        werkstoff = ws.finde(self.bibliothek.alle_werkstoffe(), kennung)
        kurz = (werkstoff.nummer or werkstoff.kurzname) if werkstoff else tr("wv.alle_werkstoffe")
        self.schnittwerte.zeige(self.werkzeug, kennung, kurz, werkstoff)

    def _schnittwerte_geaendert(self):
        """Eine Änderung in der Tabelle; gespeichert wird erst mit OK oder Übernehmen."""

    def _eckradius_zeigen(self):
        """Den Eckradius gibt es nur beim Torusfräser."""
        sichtbar = self.werkzeug is not None and self.werkzeug.art == wz.TORUSFRAESER
        self.zeile_eckradius.setVisible(sichtbar)
        self.beschriftung_eckradius.setVisible(sichtbar)

    def _hinweise(self):
        """Zeigt am Werkzeug, was fehlt oder nicht passt – sofort, nicht erst beim Speichern."""
        w = self.werkzeug
        saetze = []
        if w is not None:
            if not w.durchmesser:
                saetze.append(tr("wv.hinweis.durchmesser"))
            doppelt = self.bibliothek.mit_nummer(w.nummer, ausser=w)
            if doppelt is not None:
                saetze.append(
                    tr("wv.hinweis.nummer", nummer=w.nummer, werkzeug=dezimal(wz.kurz(doppelt)))
                )
        self.hinweis.setText("\n".join(saetze))
        self.hinweis.setVisible(bool(saetze))

    def _geaendert(self):
        """Nach jeder Eingabe: Listenzeile, Hinweise und Schnittwerte auf den neuen Stand."""
        self._zeile_auffrischen()
        self._hinweise()
        self.schnittwerte.auffrischen()

    def _nummer_geaendert(self, wert):
        if self._fuellt or self.werkzeug is None:
            return
        self.werkzeug.nummer = int(wert)
        self._geaendert()

    def _nach_nummer(self):
        """Nach der Eingabe der Nummer: Liste neu sortieren, das Werkzeug bleibt gewählt."""
        if self.werkzeug is not None:
            self._liste_aufbauen(auswahl=self.werkzeug)

    def _art_geaendert(self, _index):
        if self._fuellt or self.werkzeug is None:
            return
        self.werkzeug.art = self.feld_art.currentData()
        self._eckradius_zeigen()
        self._geaendert()

    def _schneiden_geaendert(self, wert):
        if self._fuellt or self.werkzeug is None:
            return
        self.werkzeug.schneiden = int(wert)
        self._geaendert()

    def _schneidstoff_geaendert(self, _index):
        if self._fuellt or self.werkzeug is None:
            return
        self.werkzeug.schneidstoff = self.feld_schneidstoff.currentData()
        self._geaendert()

    def _bezeichnung_geaendert(self, text):
        if self._fuellt or self.werkzeug is None:
            return
        self.werkzeug.bezeichnung = text.strip()

    def _zahl_uebernehmen(self, feld, eigenschaft):
        if self._fuellt or self.werkzeug is None:
            return
        setattr(self.werkzeug, eigenschaft, zahl_lesen(feld.text()))
        self._geaendert()

    def _felder_uebernehmen(self):
        """Übernimmt, was noch im Zahlenfeld mit dem Fokus steht (vor dem Speichern)."""
        for feld, eigenschaft in (
            (self.feld_durchmesser, "durchmesser"),
            (self.feld_schneidenlaenge, "schneidenlaenge"),
            (self.feld_eckradius, "eckradius"),
        ):
            self._zahl_uebernehmen(feld, eigenschaft)

    # --- Speichern -------------------------------------------------------------------

    @property
    def geaendert(self):
        """Gibt es Änderungen, die noch nicht gespeichert sind?"""
        return not self.bibliothek.gleich(self._gespeichert)

    def _laden(self):
        try:
            return wz.Bibliothek.laden(self.pfad)
        except wz.BeschaedigteDatei as fehler:
            QtGui.QMessageBox.warning(
                self, tr("wv.titel"), tr("wv.fehler.laden", fehler=fehler, datei=fehler.beiseite)
            )
            return wz.Bibliothek()

    def uebernehmen(self):
        """„Übernehmen“: speichert und lässt den Dialog offen. True, wenn es geklappt hat."""
        self._felder_uebernehmen()
        try:
            self.bibliothek.speichern(self.pfad)
        except OSError as fehler:
            QtGui.QMessageBox.warning(
                self, tr("wv.titel"), tr("wv.fehler.speichern", fehler=fehler)
            )
            return False
        self._gespeichert = self.bibliothek.kopie()
        return True

    def an_cam_uebergeben(self):
        """„Speichern und an CAM übergeben“: Werkzeuge als Bibliothek „CAM-Addon“ in CAM.

        Gibt den Bericht zurück (oder None); das Fenster mit der Rückmeldung
        zeigt `bericht_zeigen`, damit die Szenarien es ohne Fenster prüfen können.
        """
        if not self.uebernehmen():
            return None
        try:
            bericht = ue.uebergeben(self.bibliothek)
        except Exception as fehler:  # jeder Fehler von CAM soll als Satz ankommen
            FreeCAD.Console.PrintError(f"CAM-Addon: Übergabe an CAM: {fehler}\n")
            QtGui.QMessageBox.warning(self, tr("wv.titel"), tr("wv.cam.fehler", fehler=fehler))
            return None
        QtCore.QTimer.singleShot(0, lambda: self.bericht_zeigen(bericht))
        return bericht

    def bericht_zeigen(self, bericht):
        """Was übergeben wurde und wie es in CAM weitergeht."""
        QtGui.QMessageBox.information(self, tr("wv.cam.titel"), bericht_text(bericht))

    def accept(self):
        """OK: speichern und schließen – schließt nicht, wenn das Speichern scheitert."""
        if self.uebernehmen():
            WerkzeugDialog.offen = None
            super().accept()

    def reject(self):
        """Abbrechen, Esc, Schließen: fragt nach, wenn noch etwas ungespeichert ist."""
        self._felder_uebernehmen()
        if self.geaendert:
            antwort = QtGui.QMessageBox.question(
                self,
                tr("wv.titel"),
                tr("wv.frage.speichern"),
                QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel,
                QtGui.QMessageBox.Save,
            )
            if antwort == QtGui.QMessageBox.Cancel:
                return
            if antwort == QtGui.QMessageBox.Save and not self.uebernehmen():
                return
        WerkzeugDialog.offen = None
        super().reject()


def bericht_text(bericht):
    """Die Rückmeldung nach „An CAM übergeben“, Absatz für Absatz."""
    absaetze = [tr("wv.cam.werkzeuge", anzahl=bericht.werkzeuge)]
    if ue.presets_moeglich():
        absaetze.append(tr("wv.cam.presets", anzahl=bericht.presets))
        if bericht.werkstoffe_ohne_freecad:
            absaetze.append(
                tr("wv.cam.ohne_werkstoff", liste=", ".join(bericht.werkstoffe_ohne_freecad))
            )
    else:
        absaetze.append(tr("wv.cam.ohne_presets"))
    if bericht.ohne_durchmesser:
        absaetze.append(tr("wv.cam.ohne_durchmesser", anzahl=bericht.ohne_durchmesser))
    if bericht.entfernt:
        absaetze.append(tr("wv.cam.entfernt", anzahl=bericht.entfernt))
    absaetze.append(tr("wv.cam.weiter"))
    return "\n\n".join(absaetze)


def _fett(text):
    beschriftung = QtGui.QLabel(text)
    schrift = beschriftung.font()
    schrift.setBold(True)
    beschriftung.setFont(schrift)
    return beschriftung


def _mit_einheit(feld, einheit):
    """Feld mit der Einheit rechts daneben."""
    zeile = QtGui.QWidget()
    aufbau = QtGui.QHBoxLayout(zeile)
    aufbau.setContentsMargins(0, 0, 0, 0)
    aufbau.addWidget(feld)
    aufbau.addWidget(QtGui.QLabel(einheit))
    return zeile
