# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Fenster „Spannmittel“ (W-042, spannmittel.py).

Zwei Seiten:

- **Sammlung** – die Spannmittel der Werkstatt, nach Art: links die Liste mit Suche, Neu (leer je
  Art oder „Aus dem Katalog der Hersteller …“), Kopieren, Löschen; rechts Name, Hersteller,
  Bezeichnung, Artikel, Link, die Maße der Art und das Bild – von der Seite und von oben, mit
  einem Beispiel-Rohteil in den Backen.
- **Aufspannung im Job** – wie das Rohteil eines Jobs auf dem Tisch steht: Spannmittel,
  Unterbau, Lage (X, Y von der Werkstückaufnahme, Drehung) und Spanntiefe. Darunter, ob das
  Rohteil passt, wo der Nullpunkt dann liegt, und das Bild mit dem echten Rohteil.

Gearbeitet wird an Kopien: OK speichert die Sammlung und trägt die Aufspannung am Job ein,
Abbrechen verwirft beides.
"""

import contextlib
import math

import FreeCAD
from PySide import QtCore, QtGui

from . import einheiten
from . import spannmittel as sm
from .gui_hilfe import kopfzeile
from .gui_teile import GRAU, fenster_merken, knopf, mit_einheit, ruhiges_mausrad
from .gui_zahlen import Zahlenpruefer, groesse_lesen, groesse_zeigen
from .sprache import tr

FENSTER_GROESSE = (980, 640)  # Pixel
ORANGE = "#b8650f"
FARBE_SPANNMITTEL = QtGui.QColor("#9aa3ab")
FARBE_SPANNMITTEL_RAND = QtGui.QColor("#4d555c")
FARBE_UNTERBAU = QtGui.QColor("#6f7a84")
FARBE_BACKE = QtGui.QColor("#7c93ad")  # Backen, Pratzen, Schrauben – am Rohteil
FARBE_ROHTEIL = QtGui.QColor(240, 180, 90, 200)
FARBE_ROHTEIL_RAND = QtGui.QColor("#a0601a")
FARBE_ACHSE = QtGui.QColor("#c0392b")
BILD_RAND = 14  # Pixel


class BefehlSpannmittel:
    """Öffnet das Fenster „Spannmittel“."""

    def GetResources(self):
        from . import symbol

        return {
            "Pixmap": symbol("spannmittel.svg"),
            "MenuText": tr("befehl.spannmittel.titel"),
            "ToolTip": tr("befehl.spannmittel.tooltip"),
        }

    def IsActive(self):
        return True

    def Activated(self):
        oeffne()


def oeffne(job=None):
    """Öffnet das Fenster; mit `job` gleich auf der Seite „Aufspannung im Job“."""
    import FreeCADGui

    from . import job_schnittwerte as js
    from . import schwenken as sw
    from .gui_reichweite import job_fuer

    dokument = job.Document if job is not None else FreeCAD.ActiveDocument
    jobs = [j for j in js.jobs(dokument) if not sw.ist_ebene(j)]
    gewaehlt = job if job is not None else (job_fuer(jobs) if jobs else None)
    dialog = SpannmittelDialog(
        FreeCADGui.getMainWindow(), jobs=jobs, job=gewaehlt, seite_job=job is not None
    )
    dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    dialog.show()
    return dialog


def _laden():
    try:
        return sm.Sammlung.laden()
    except sm.BeschaedigteDatei as fehler:
        QtGui.QMessageBox.warning(
            None, tr("sm.titel"), tr("sm.fehler.laden", fehler=fehler, datei=fehler.beiseite)
        )
        return sm.Sammlung()


def _laengenfeld(tooltip="", minus=False):
    feld = QtGui.QLineEdit()
    feld.setValidator(Zahlenpruefer(feld, mit_minus=minus))
    feld.setToolTip(tooltip)
    return feld


class SpannmittelDialog(QtGui.QDialog):
    """Sammlung und Aufspannung (siehe oben). `jobs`: die Jobs des Dokuments (ohne Ebenen),
    `job`: der, dessen Aufspannung gezeigt wird; `seite_job`: gleich auf dieser Seite."""

    offen = None  # für die Oberflächen-Szenarien

    def __init__(self, eltern=None, jobs=(), job=None, pfad=None, seite_job=False):
        super().__init__(eltern)
        SpannmittelDialog.offen = self
        self.pfad = pfad
        self.sammlung = sm.Sammlung.laden(pfad) if pfad else _laden()
        self._gespeichert = self.sammlung.kopie()
        self.jobs = list(jobs)
        self.job = job if job in self.jobs else (self.jobs[0] if self.jobs else None)
        self._aufspannungen = {j.Name: sm.aufspannung(j) for j in self.jobs}  # Arbeitskopien
        self._fuellt = False
        self.setWindowTitle(tr("sm.titel"))
        fenster_merken(self, "Spannmittel", FENSTER_GROESSE)
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(kopfzeile(tr("sm.titel"), "spannmittel"))
        self.seiten = QtGui.QTabWidget()
        self.seiten.addTab(self._seite_sammlung(), tr("sm.seite.sammlung"))
        self.seiten.addTab(self._seite_aufspannung(), tr("sm.seite.aufspannung"))
        self.seiten.setTabEnabled(1, bool(self.jobs))
        if not self.jobs:
            self.seiten.setTabToolTip(1, tr("sm.auf.kein_job"))
        self.seiten.currentChanged.connect(lambda _i: self._aufspannung_zeigen())
        aufbau.addWidget(self.seiten, 1)
        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(knoepfe)
        ruhiges_mausrad(self)
        self._fuellen()
        if seite_job and self.job is not None:
            self.seiten.setCurrentIndex(1)
        self._aufspannung_zeigen()

    # --- Seite Sammlung ---------------------------------------------------------------------

    def _seite_sammlung(self):
        seite = QtGui.QWidget()
        teilung = QtGui.QHBoxLayout(seite)
        links = QtGui.QVBoxLayout()
        self.suche = QtGui.QLineEdit()
        self.suche.setPlaceholderText(tr("sm.suche.platzhalter"))
        self.suche.setClearButtonEnabled(True)
        self.suche.textChanged.connect(lambda _text: self._fuellen())
        links.addWidget(self.suche)
        self.liste = QtGui.QTreeWidget()
        self.liste.setHeaderHidden(True)
        self.liste.setIndentation(12)
        self.liste.currentItemChanged.connect(lambda *_a: self._zeigen())
        links.addWidget(self.liste, 1)
        zeile = QtGui.QHBoxLayout()
        self.knopf_neu = QtGui.QPushButton(tr("sm.neu"))
        self.knopf_neu.setToolTip(tr("sm.neu.tooltip"))
        self.knopf_neu.setAutoDefault(False)
        menue = QtGui.QMenu(self.knopf_neu)
        menue.addAction(tr("sm.neu.katalog"), self.aus_katalog)
        menue.addSeparator()
        for art in sm.ARTEN:
            menue.addAction(tr("sm.neu.leer", art=sm.art_text(art)), lambda a=art: self.neu(a))
        self.knopf_neu.setMenu(menue)
        self.knopf_katalog = knopf(
            tr("sm.katalog.knopf"), tr("sm.katalog.knopf.tooltip"), self.aus_katalog
        )
        self.knopf_kopieren = knopf(tr("sm.kopieren"), tr("sm.kopieren.tooltip"), self.kopieren)
        self.knopf_loeschen = knopf(tr("sm.loeschen"), tr("sm.loeschen.tooltip"), self.loeschen)
        for k in (self.knopf_neu, self.knopf_katalog, self.knopf_kopieren, self.knopf_loeschen):
            zeile.addWidget(k)
        links.addLayout(zeile)
        teilung.addLayout(links, 2)

        rechts = QtGui.QVBoxLayout()
        self.leer = QtGui.QLabel(tr("sm.leer"))
        self.leer.setWordWrap(True)
        rechts.addWidget(self.leer)
        self.rahmen = QtGui.QWidget()
        innen = QtGui.QHBoxLayout(self.rahmen)
        innen.setContentsMargins(0, 0, 0, 0)
        # Die Felder rollen, wenn die Quelle lang ist – sonst drückte sie die Felder zusammen.
        rolle = QtGui.QScrollArea()
        rolle.setWidgetResizable(True)
        rolle.setFrameShape(QtGui.QFrame.NoFrame)
        rolle.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        spalte = QtGui.QWidget()
        felder = QtGui.QVBoxLayout(spalte)
        felder.setContentsMargins(0, 0, 4, 0)
        rolle.setWidget(spalte)
        gitter = QtGui.QFormLayout()
        self.feld_name = QtGui.QLineEdit()
        self.feld_hersteller = QtGui.QLineEdit()
        self.feld_bezeichnung = QtGui.QLineEdit()
        self.feld_artikel = QtGui.QLineEdit()
        self.feld_link = QtGui.QLineEdit()
        self.feld_link.setPlaceholderText(tr("sm.link.platzhalter"))
        for feld, eigenschaft in (
            (self.feld_name, "name"),
            (self.feld_hersteller, "hersteller"),
            (self.feld_bezeichnung, "bezeichnung"),
            (self.feld_artikel, "artikel"),
            (self.feld_link, "link"),
        ):
            feld.textEdited.connect(lambda text, e=eigenschaft: self._text_geaendert(e, text))
        knopf_link = knopf(tr("sm.link.oeffnen"), tr("sm.link.tooltip"), self.link_oeffnen)
        zeile_link = QtGui.QWidget()
        link_aufbau = QtGui.QHBoxLayout(zeile_link)
        link_aufbau.setContentsMargins(0, 0, 0, 0)
        link_aufbau.addWidget(self.feld_link, 1)
        link_aufbau.addWidget(knopf_link)
        self.art_text = QtGui.QLabel()
        gitter.addRow(tr("sm.name"), self.feld_name)
        gitter.addRow(tr("sm.art"), self.art_text)
        gitter.addRow(tr("sm.hersteller"), self.feld_hersteller)
        gitter.addRow(tr("sm.bezeichnung"), self.feld_bezeichnung)
        gitter.addRow(tr("sm.artikel"), self.feld_artikel)
        gitter.addRow(tr("sm.link"), zeile_link)
        felder.addLayout(gitter)
        masse = QtGui.QLabel(f"<b>{tr('sm.masse')}</b>")
        felder.addWidget(masse)
        self.gitter_masse = QtGui.QFormLayout()
        felder.addLayout(self.gitter_masse)
        self._massfelder = {}
        self.quelle = QtGui.QLabel()
        self.quelle.setWordWrap(True)
        self.quelle.setStyleSheet(f"color: {GRAU.name()};")
        self.quelle.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        felder.addWidget(self.quelle)
        felder.addStretch()
        innen.addWidget(rolle, 3)
        self.bild = SpannmittelBild()
        self.bild.setToolTip(tr("sm.bild.tooltip"))
        innen.addWidget(self.bild, 2)
        rechts.addWidget(self.rahmen, 1)
        teilung.addLayout(rechts, 5)
        return seite

    def _fuellen(self, auswahl=None):
        """Die Spannmittel, die zur Suche passen, nach Art; die Auswahl bleibt, wenn es geht."""
        vorher = auswahl or self.gewaehlt
        worte = self.suche.text().lower().split()
        self.liste.blockSignals(True)
        self.liste.clear()
        gewaehlt_eintrag = None
        erster = None
        for art in sm.ARTEN:
            der_art = [
                s
                for s in self.sammlung.sortiert()
                if s.art == art
                and all(w in f"{s.text} {s.hersteller} {s.bezeichnung}".lower() for w in worte)
            ]
            if not der_art:
                continue
            gruppe = QtGui.QTreeWidgetItem([f"{sm.art_text(art)} ({len(der_art)})"])
            gruppe.setFlags(QtCore.Qt.ItemIsEnabled)
            schrift = gruppe.font(0)
            schrift.setBold(True)
            gruppe.setFont(0, schrift)
            self.liste.addTopLevelItem(gruppe)
            for s in der_art:
                eintrag = QtGui.QTreeWidgetItem([s.text])
                eintrag.setData(0, QtCore.Qt.UserRole, s.kennung)
                eintrag.setToolTip(0, s.bezeichnung or s.text)
                gruppe.addChild(eintrag)
                erster = erster or eintrag
                if vorher is not None and s.kennung == vorher.kennung:
                    gewaehlt_eintrag = eintrag
            gruppe.setExpanded(True)
        self.liste.blockSignals(False)
        self.liste.setCurrentItem(gewaehlt_eintrag or erster)
        self._zeigen()

    @property
    def gewaehlt(self):
        """Das gewählte Spannmittel, oder None."""
        eintrag = self.liste.currentItem() if hasattr(self, "liste") else None
        kennung = eintrag.data(0, QtCore.Qt.UserRole) if eintrag is not None else None
        return self.sammlung.mit(kennung) if kennung else None

    def waehle(self, spannmittel):
        self.suche.blockSignals(True)
        self.suche.clear()
        self.suche.blockSignals(False)
        self._fuellen(auswahl=spannmittel)

    def _zeigen(self):
        """Die Felder und das Bild des gewählten Spannmittels."""
        s = self.gewaehlt
        self.leer.setVisible(s is None)
        self.rahmen.setVisible(s is not None)
        self.knopf_kopieren.setEnabled(s is not None)
        self.knopf_loeschen.setEnabled(s is not None)
        if s is None:
            self.leer.setText(tr("sm.leer") if not self.sammlung.spannmittel else tr("sm.keins"))
            return
        self._fuellt = True
        self.feld_name.setText(s.name)
        self.feld_hersteller.setText(s.hersteller)
        self.feld_bezeichnung.setText(s.bezeichnung)
        self.feld_artikel.setText(s.artikel)
        self.feld_link.setText(s.link)
        self.art_text.setText(sm.art_text(s.art))
        self._massfelder_bauen(s)
        self.quelle.setText(tr("sm.quelle", quelle=s.quelle) if s.quelle else "")
        self._fuellt = False
        self._bild_zeigen()

    def _massfelder_bauen(self, s):
        while self.gitter_masse.rowCount():
            self.gitter_masse.removeRow(0)
        self._massfelder = {}
        mm = einheiten.einheit(einheiten.LAENGE)
        for feld, _beispiel in sm.FELDER[s.art]:
            if feld == "anzahl":
                wahl = QtGui.QComboBox()
                wahl.addItem("2", 2.0)
                wahl.addItem("4", 4.0)
                wahl.setCurrentIndex(1 if s.mass("anzahl") >= 4 else 0)
                wahl.currentIndexChanged.connect(
                    lambda _i, w=wahl: self._mass_geaendert("anzahl", w.currentData())
                )
                self.gitter_masse.addRow(sm.feld_text(feld), wahl)
                self._massfelder[feld] = wahl
                continue
            eingabe = _laengenfeld(sm.feld_hilfe(feld))
            eingabe.setText(groesse_zeigen(s.mass(feld), einheiten.LAENGE))
            eingabe.editingFinished.connect(lambda f=feld, e=eingabe: self._mass_lesen(f, e))
            self.gitter_masse.addRow(sm.feld_text(feld), mit_einheit(eingabe, mm))
            self._massfelder[feld] = eingabe

    def _mass_lesen(self, feld, eingabe):
        with contextlib.suppress(ValueError):
            self._mass_geaendert(feld, groesse_lesen(eingabe.text(), einheiten.LAENGE))

    def _mass_geaendert(self, feld, wert):
        s = self.gewaehlt
        if s is None or self._fuellt:
            return
        s.masse[feld] = max(float(wert), 0.0)
        self._bild_zeigen()

    def _text_geaendert(self, eigenschaft, text):
        s = self.gewaehlt
        if s is None or self._fuellt:
            return
        setattr(s, eigenschaft, text.strip())
        if eigenschaft in ("name", "hersteller"):
            eintrag = self.liste.currentItem()
            if eintrag is not None:
                eintrag.setText(0, s.text)

    def _bild_zeigen(self):
        s = self.gewaehlt
        if s is None:
            return
        auf = sm.Aufspannung(s)
        self.bild.zeigen(auf, _beispiel_rohteil(s))

    def link_oeffnen(self):
        s = self.gewaehlt
        if s is not None and s.link:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(s.link))

    def neu(self, art):
        s = self.sammlung.dazu(sm.neu(art))
        self.waehle(s)
        self.feld_name.setFocus()
        self.feld_name.selectAll()
        self._auswahl_auffrischen()
        return s

    def kopieren(self):
        if self.gewaehlt is not None:
            self.waehle(self.sammlung.kopiere(self.gewaehlt))
            self._auswahl_auffrischen()

    def loeschen(self, fragen=True):
        s = self.gewaehlt
        if s is None:
            return
        if fragen:
            antwort = QtGui.QMessageBox.question(
                self, tr("sm.titel"), tr("sm.loeschen.frage", name=s.text)
            )
            if antwort != QtGui.QMessageBox.Yes:
                return
        self.sammlung.entferne(s)
        self._fuellen()
        self._auswahl_auffrischen()

    def aus_katalog(self):
        """„Aus dem Katalog der Hersteller …“: angehakte Größen in die Sammlung."""
        from .gui_katalog import KatalogDialog

        dialog = KatalogDialog(
            self,
            tr("sm.katalog.titel"),
            tr("sm.katalog.erklaerung"),
            sm.katalog_reihen(),
            [(art, sm.art_text(art)) for art in sm.ARTEN],
            lambda reihe: reihe.art,
            _groesse_text,
        )
        if not dialog.exec():
            return None
        bericht = sm.katalog_hinzufuegen(self.sammlung, dialog.gewaehlt())
        if bericht.neu:
            self.waehle(bericht.neu[0])
        self._auswahl_auffrischen()
        satz = tr("sm.katalog.bericht", neu=len(bericht.neu))
        if bericht.schon_da:
            satz += " " + tr("sm.katalog.schon_da", namen=", ".join(bericht.schon_da))
        QtGui.QMessageBox.information(self, tr("sm.katalog.titel"), satz)
        return bericht

    # --- Seite Aufspannung -------------------------------------------------------------------

    def _seite_aufspannung(self):
        seite = QtGui.QWidget()
        teilung = QtGui.QHBoxLayout(seite)
        links = QtGui.QVBoxLayout()
        erklaerung = QtGui.QLabel(tr("sm.auf.erklaerung"))
        erklaerung.setWordWrap(True)
        links.addWidget(erklaerung)
        gitter = QtGui.QFormLayout()
        self.wahl_job = QtGui.QComboBox()
        for job in self.jobs:
            self.wahl_job.addItem(job.Label, job.Name)
        self.wahl_job.currentIndexChanged.connect(self._job_gewaehlt)
        self.wahl_spannmittel = QtGui.QComboBox()
        self.wahl_spannmittel.setToolTip(tr("sm.auf.spannmittel.tooltip"))
        self.wahl_unterbau = QtGui.QComboBox()
        self.wahl_unterbau.setToolTip(tr("sm.auf.unterbau.tooltip"))
        mm = einheiten.einheit(einheiten.LAENGE)
        self.feld_x = _laengenfeld(tr("sm.auf.lage.tooltip"), minus=True)
        self.feld_y = _laengenfeld(tr("sm.auf.lage.tooltip"), minus=True)
        self.feld_x.setPlaceholderText("0")
        self.feld_y.setPlaceholderText("0")
        self.wahl_drehung = QtGui.QComboBox()
        for grad in sm.DREHUNGEN:
            self.wahl_drehung.addItem(f"{grad}°", grad)
        self.wahl_drehung.setToolTip(tr("sm.auf.drehung.tooltip"))
        self.feld_tiefe = _laengenfeld(tr("sm.auf.tiefe.tooltip"))
        lage = QtGui.QWidget()
        lage_aufbau = QtGui.QHBoxLayout(lage)
        lage_aufbau.setContentsMargins(0, 0, 0, 0)
        lage_aufbau.addWidget(QtGui.QLabel("X"))
        lage_aufbau.addWidget(mit_einheit(self.feld_x, mm), 1)
        lage_aufbau.addWidget(QtGui.QLabel("Y"))
        lage_aufbau.addWidget(mit_einheit(self.feld_y, mm), 1)
        gitter.addRow(tr("sm.auf.job"), self.wahl_job)
        gitter.addRow(tr("sm.auf.spannmittel"), self.wahl_spannmittel)
        gitter.addRow(tr("sm.auf.unterbau"), self.wahl_unterbau)
        gitter.addRow(tr("sm.auf.lage"), lage)
        gitter.addRow(tr("sm.auf.drehung"), self.wahl_drehung)
        self.zeile_tiefe = mit_einheit(self.feld_tiefe, mm)
        gitter.addRow(tr("sm.auf.tiefe"), self.zeile_tiefe)
        links.addLayout(gitter)
        self.auf_hinweis = QtGui.QLabel()
        self.auf_hinweis.setWordWrap(True)
        self.auf_hinweis.setStyleSheet(f"color: {ORANGE};")
        links.addWidget(self.auf_hinweis)
        self.auf_nullpunkt = QtGui.QLabel()
        self.auf_nullpunkt.setWordWrap(True)
        self.auf_nullpunkt.setStyleSheet(f"color: {GRAU.name()};")
        links.addWidget(self.auf_nullpunkt)
        links.addStretch()
        teilung.addLayout(links, 2)
        self.auf_bild = SpannmittelBild(auf_dem_tisch=True)
        self.auf_bild.setToolTip(tr("sm.auf.bild.tooltip"))
        teilung.addWidget(self.auf_bild, 3)
        for wahl in (self.wahl_spannmittel, self.wahl_unterbau, self.wahl_drehung):
            wahl.currentIndexChanged.connect(lambda _i: self._aufspannung_lesen())
        for feld in (self.feld_x, self.feld_y, self.feld_tiefe):
            feld.editingFinished.connect(self._aufspannung_lesen)
        return seite

    def _auswahl_auffrischen(self):
        """Die Listen „Spannmittel“ und „Unterbau“ aus der Sammlung – und, was der Job hat, auch
        wenn es nicht (mehr) in der Sammlung steht."""
        if not hasattr(self, "wahl_spannmittel"):
            return
        auf = self.aufspannung
        self._fuellt = True
        for wahl, arten, leer, jetzt in (
            (self.wahl_spannmittel, sm.ARTEN, tr("sm.auf.keins"), auf and auf.spannmittel),
            (self.wahl_unterbau, sm.UNTERBAU_ARTEN, tr("sm.auf.direkt"), auf and auf.unterbau),
        ):
            wahl.blockSignals(True)
            wahl.clear()
            wahl.addItem(leer, None)
            kennungen = set()
            for s in self.sammlung.sortiert():
                if s.art in arten:
                    wahl.addItem(f"{s.text} – {sm.art_text(s.art)}", s.kennung)
                    kennungen.add(s.kennung)
            if jetzt and jetzt.kennung not in kennungen:
                wahl.addItem(tr("sm.auf.im_job", name=jetzt.text), jetzt.kennung)
            index = wahl.findData(jetzt.kennung) if jetzt else 0
            wahl.setCurrentIndex(max(index, 0))
            wahl.blockSignals(False)
        self._fuellt = False

    @property
    def aufspannung(self):
        """Die Arbeitskopie der Aufspannung des gewählten Jobs, oder None."""
        return self._aufspannungen.get(self.job.Name) if self.job is not None else None

    def _job_gewaehlt(self, index):
        name = self.wahl_job.itemData(index)
        self.job = next((j for j in self.jobs if j.Name == name), self.job)
        self._aufspannung_zeigen()

    def _aufspannung_zeigen(self):
        """Die Felder der Seite „Aufspannung“ aus der Arbeitskopie des Jobs."""
        if self.job is None:
            return
        self._fuellt = True
        self.wahl_job.setCurrentIndex(max(self.wahl_job.findData(self.job.Name), 0))
        self._fuellt = False
        self._auswahl_auffrischen()
        auf = self.aufspannung
        self._fuellt = True
        self.feld_x.setText(groesse_zeigen(auf.x, einheiten.LAENGE) if auf else "")
        self.feld_y.setText(groesse_zeigen(auf.y, einheiten.LAENGE) if auf else "")
        self.wahl_drehung.setCurrentIndex(sm.DREHUNGEN.index(auf.drehung) if auf else 0)
        if auf is not None and auf.spanntiefe >= 0:
            self.feld_tiefe.setText(groesse_zeigen(auf.spanntiefe, einheiten.LAENGE))
        else:
            self.feld_tiefe.clear()
        self._fuellt = False
        self._aufspannung_beschriften()

    def _aufspannung_lesen(self):
        """Nach jeder Eingabe: die Arbeitskopie aus den Feldern."""
        if self._fuellt or self.job is None:
            return
        kennung = self.wahl_spannmittel.currentData()
        alt = self.aufspannung
        if not kennung:
            self._aufspannungen[self.job.Name] = None
            self._aufspannung_beschriften()
            return
        spannmittel = self._spannmittel_fuer(kennung, alt and alt.spannmittel)
        kennung_unterbau = self.wahl_unterbau.currentData()
        unterbau = (
            self._spannmittel_fuer(kennung_unterbau, alt and alt.unterbau)
            if kennung_unterbau
            else None
        )

        def lesen(feld, standard):
            try:
                return groesse_lesen(feld.text(), einheiten.LAENGE) if feld.text() else standard
            except ValueError:
                return standard

        tiefe = lesen(self.feld_tiefe, -1.0)
        self._aufspannungen[self.job.Name] = sm.Aufspannung(
            spannmittel,
            unterbau,
            lesen(self.feld_x, 0.0),
            lesen(self.feld_y, 0.0),
            int(self.wahl_drehung.currentData() or 0),
            tiefe if self.feld_tiefe.text() else -1.0,
        )
        self._aufspannung_beschriften()

    def _spannmittel_fuer(self, kennung, im_job):
        """Eine Kopie aus der Sammlung – oder, was der Job schon hat."""
        aus_sammlung = self.sammlung.mit(kennung)
        if aus_sammlung is not None:
            return sm.Spannmittel.aus_dict(aus_sammlung.als_dict())
        return im_job if im_job is not None and im_job.kennung == kennung else None

    def _aufspannung_beschriften(self):
        """Hinweise, Nullpunkt, Platzhalter der Spanntiefe und das Bild."""
        auf = self.aufspannung
        box = _rohteil_box(self.job)
        mit_backen = auf is not None and auf.spannmittel.art in sm.MIT_BACKEN
        self.zeile_tiefe.setEnabled(mit_backen)
        if auf is not None:
            self.feld_tiefe.setPlaceholderText(
                groesse_zeigen(auf.spannmittel.mass("spanntiefe"), einheiten.LAENGE)
                if mit_backen
                else ""
            )
        if auf is None:
            self.auf_hinweis.setText("")
            self.auf_nullpunkt.setText(tr("sm.auf.ohne"))
            self.auf_bild.zeigen(None, box)
            return
        if box is None:
            self.auf_hinweis.setText(tr("sm.auf.kein_rohteil"))
            self.auf_nullpunkt.setText("")
            self.auf_bild.zeigen(auf, None)
            return
        self.auf_hinweis.setText("<br>".join(sm.hinweise(auf, box)))
        x, y, z = sm.nullpunkt_vorschlag(auf, box)
        self.auf_nullpunkt.setText(
            tr(
                "sm.auf.nullpunkt",
                x=groesse_zeigen(x, einheiten.LAENGE, 2) or "0",
                y=groesse_zeigen(y, einheiten.LAENGE, 2) or "0",
                z=groesse_zeigen(z, einheiten.LAENGE, 2) or "0",
                einheit=einheiten.einheit(einheiten.LAENGE),
            )
        )
        self.auf_bild.zeigen(auf, box)

    # --- Abschluss ---------------------------------------------------------------------------

    def keyPressEvent(self, ereignis):
        """Enter bestätigt nur das Feld, nicht das Fenster."""
        if ereignis.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            ereignis.accept()
            return
        super().keyPressEvent(ereignis)

    def accept(self):
        """Speichert die Sammlung und trägt geänderte Aufspannungen an den Jobs ein."""
        from . import reichweite as rw

        try:
            self.sammlung.speichern(self.pfad)
        except OSError as fehler:
            QtGui.QMessageBox.warning(
                self, tr("sm.titel"), tr("sm.fehler.speichern", fehler=fehler)
            )
            return
        geaendert = []
        for job in self.jobs:
            neu = self._aufspannungen.get(job.Name)
            alt = sm.aufspannung(job)
            if (neu and neu.als_dict()) == (alt and alt.als_dict()):
                continue
            sm.setze(job, neu)
            # Wo das Teil auf dem Tisch liegt, sagt jetzt das Spannmittel (rw.vorschlag_nullpunkt).
            if neu is not None and rw.eingetragener_nullpunkt(job):
                rw.setze_nullpunkt(job, {})
            geaendert.append(job)
        for dokument in {job.Document for job in geaendert}:
            dokument.recompute()
        SpannmittelDialog.offen = None
        super().accept()

    def reject(self):
        SpannmittelDialog.offen = None
        super().reject()


def _rohteil_box(job):
    rohteil = getattr(getattr(job, "Stock", None), "Shape", None)
    if rohteil is None or rohteil.isNull():
        return None
    return rohteil.BoundBox


def _beispiel_rohteil(s):
    """Ein Rohteil fürs Bild der Sammlung: so breit, dass es gut in die Backen passt."""
    import Part

    if s.art in (sm.SCHRAUBSTOCK, sm.ZENTRISCH):
        breite = max(min(0.5 * s.mass("spannweite_max"), 1.2 * s.mass("backenbreite")), 20.0)
        laenge = max(1.2 * s.mass("backenbreite"), 30.0)
        hoehe = max(s.mass("spanntiefe") + 25.0, 30.0)
        return Part.makeBox(laenge, breite, hoehe).BoundBox
    if s.art == sm.FUTTER:
        d = max(0.4 * s.mass("spannweite_max"), 20.0)
        return Part.makeBox(d, d, d * 0.6).BoundBox
    if s.art == sm.PRATZEN:
        return Part.makeBox(160.0, 100.0, min(40.0, s.mass("hoehe_max") or 40.0)).BoundBox
    laenge = s.mass("laenge") or s.mass("durchmesser")
    return Part.makeBox(0.6 * laenge, 0.6 * (s.mass("breite") or laenge), 30.0).BoundBox


def _groesse_text(reihe, groesse):
    """Eine Zeile im Katalog: „C2 125 – Backen 125 mm, Spannweite bis 160 mm · 123-456“."""
    masse = groesse["masse"]
    teile = []
    if masse.get("backenbreite"):
        teile.append(tr("kt.sm.backen", wert=sm._mm(masse["backenbreite"])))
    weite = masse.get("spannweite_max") or masse.get("spann_max")
    if weite:
        teile.append(tr("kt.sm.weite", wert=sm._mm(weite)))
    if masse.get("durchmesser"):
        teile.append(tr("kt.sm.durchmesser", wert=sm._mm(masse["durchmesser"])))
    if masse.get("hoehe"):
        teile.append(tr("kt.sm.hoehe", wert=sm._mm(masse["hoehe"])))
    text = groesse["name"]
    if teile:
        text += " – " + ", ".join(teile)
    if groesse["artikel"]:
        text += f" · {groesse['artikel']}"
    return text


class SpannmittelBild(QtGui.QWidget):
    """Das Spannmittel von der Seite (oben) und von oben (unten), mit dem Rohteil in den Backen.
    `auf_dem_tisch`: im Bezug der Werkstückaufnahme – gedreht und an seiner Lage, mit dem
    Achsenkreuz am Ursprung; sonst im Bezug des Spannmittels."""

    def __init__(self, auf_dem_tisch=False):
        super().__init__()
        self.auf_dem_tisch = auf_dem_tisch
        self._teile = []  # [(Farbe, Rand, Seite [(x, z)], oben [(x, y)], rund)]
        self.setMinimumSize(260, 360)

    def zeigen(self, auf, box):
        """Baut die Umrisse aus spannmittel.koerper; ohne Aufspannung nur das Rohteil."""
        self._teile = []
        if box is not None:
            if auf is not None:
                self._dazu(auf, box)
            self._rohteil(auf, box)
        self.update()

    def _abbilden(self, auf, punkt, box):
        """Ein Punkt im Bezug des Spannmittels → im Bild (Tisch oder Spannmittel)."""
        x, y, z = punkt
        if not self.auf_dem_tisch or auf is None:
            return x, y, z
        w = math.radians(auf.drehung)
        return (
            auf.x + x * math.cos(w) - y * math.sin(w),
            auf.y + x * math.sin(w) + y * math.cos(w),
            z,
        )

    def _dazu(self, auf, box):
        try:
            form = sm.koerper(auf, box)
        except Exception:  # ein Maß von 0: lieber kein Bild als kein Fenster
            return
        unterbau = (
            len(sm._teile(auf.unterbau, sm.Aufspannung(auf.unterbau), box, 0.0))
            if auf.unterbau
            else 0
        )
        for nummer, teil in enumerate(form.Solids):
            punkte = [self._abbilden(auf, (v.X, v.Y, v.Z), box) for v in teil.Vertexes]
            rund = any(f.Surface.__class__.__name__ == "Cylinder" for f in teil.Faces)
            if rund:
                bb = teil.BoundBox
                mitte = self._abbilden(auf, (bb.Center.x, bb.Center.y, 0.0), box)
                r = bb.XLength / 2
                punkte = [
                    (mitte[0] + r * math.cos(t), mitte[1] + r * math.sin(t), z)
                    for t in [i * math.pi / 18 for i in range(36)]
                    for z in (bb.ZMin, bb.ZMax)
                ]
            if nummer < unterbau:
                farbe = FARBE_UNTERBAU
            elif nummer == unterbau and auf.spannmittel.art != sm.PRATZEN:
                farbe = FARBE_SPANNMITTEL  # der Grundkörper
            else:
                farbe = FARBE_BACKE
            self._teile.append((farbe, FARBE_SPANNMITTEL_RAND, punkte))

    def _rohteil(self, auf, box):
        """Das Rohteil: im Bezug des Spannmittels an seiner Stelle, auf dem Tisch dort, wo die
        Aufspannung es hält."""
        if auf is None:
            ecken = [
                (x, y, z)
                for x in (box.XMin, box.XMax)
                for y in (box.YMin, box.YMax)
                for z in (box.ZMin, box.ZMax)
            ]
            self._teile.append((FARBE_ROHTEIL, FARBE_ROHTEIL_RAND, ecken))
            return
        laengs, quer = sm._quer(box, auf.drehung)
        mx, my, mz = sm.rohteil_mitte(auf, box)
        ecken = [
            self._abbilden(
                auf, (mx + sx * laengs / 2, my + sy * quer / 2, mz + sz * box.ZLength), box
            )
            for sx in (-1, 1)
            for sy in (-1, 1)
            for sz in (0, 1)
        ]
        self._teile.append((FARBE_ROHTEIL, FARBE_ROHTEIL_RAND, ecken))

    def paintEvent(self, _ereignis):
        maler = QtGui.QPainter(self)
        maler.setRenderHint(QtGui.QPainter.Antialiasing)
        maler.fillRect(self.rect(), self.palette().base())
        if not self._teile:
            maler.setPen(GRAU)
            maler.drawText(self.rect(), QtCore.Qt.AlignCenter, tr("sm.bild.leer"))
            return
        alle = [p for _f, _r, punkte in self._teile for p in punkte]
        if self.auf_dem_tisch:
            alle.append((0.0, 0.0, 0.0))
        xs, ys, zs = zip(*alle, strict=True)
        breite = max(max(xs) - min(xs), 1.0)
        tief = max(max(ys) - min(ys), 1.0)
        hoch = max(max(zs) - min(zs), 1.0)
        w = self.width() - 2 * BILD_RAND
        h = self.height() - 3 * BILD_RAND - 2 * 14
        massstab = min(w / breite, h / (tief + hoch))
        links = BILD_RAND + (w - breite * massstab) / 2
        oben_seite = BILD_RAND + 14
        unten_seite = oben_seite + hoch * massstab
        oben_draufsicht = unten_seite + BILD_RAND + 14

        def seite(x, z):
            return QtCore.QPointF(
                links + (x - min(xs)) * massstab, unten_seite - (z - min(zs)) * massstab
            )

        def draufsicht(x, y):
            return QtCore.QPointF(
                links + (x - min(xs)) * massstab, oben_draufsicht + (max(ys) - y) * massstab
            )

        maler.setPen(GRAU)
        maler.drawText(QtCore.QPointF(BILD_RAND, oben_seite - 3), tr("sm.bild.seite"))
        maler.drawText(QtCore.QPointF(BILD_RAND, oben_draufsicht - 3), tr("sm.bild.oben"))
        # Von der Seite: hinten zuerst – die Teile nach ihrer Tiefe (y), das vorderste zuletzt.
        for farbe, rand, punkte in sorted(self._teile, key=lambda t: -min(p[1] for p in t[2])):
            maler.setPen(QtGui.QPen(rand, 1))
            maler.setBrush(farbe)
            maler.drawPolygon(_huelle([seite(p[0], p[2]) for p in punkte]))
        for farbe, rand, punkte in sorted(self._teile, key=lambda t: max(p[2] for p in t[2])):
            maler.setPen(QtGui.QPen(rand, 1))
            maler.setBrush(farbe)
            maler.drawPolygon(_huelle([draufsicht(p[0], p[1]) for p in punkte]))
        if self.auf_dem_tisch:  # der Tisch von der Seite
            maler.setPen(QtGui.QPen(FARBE_SPANNMITTEL_RAND, 2))
            tisch = seite(min(xs), 0.0).y()
            maler.drawLine(
                QtCore.QPointF(BILD_RAND, tisch), QtCore.QPointF(self.width() - BILD_RAND, tisch)
            )
            maler.setPen(GRAU)
            maler.drawText(QtCore.QPointF(self.width() / 2, tisch - 4), tr("sm.bild.tisch"))
        if self.auf_dem_tisch:  # die Werkstückaufnahme: X nach rechts, Y nach oben
            ursprung = draufsicht(0.0, 0.0)
            maler.setPen(QtGui.QPen(FARBE_ACHSE, 2))
            maler.drawLine(ursprung, ursprung + QtCore.QPointF(28, 0))
            maler.drawLine(ursprung, ursprung + QtCore.QPointF(0, -28))
            maler.drawText(ursprung + QtCore.QPointF(31, 4), "X")
            maler.drawText(ursprung + QtCore.QPointF(-4, -31), "Y")


def _huelle(punkte):
    """Die konvexe Hülle der Punkte als Polygon (Monotone Chain)."""
    feld = sorted({(round(p.x(), 2), round(p.y(), 2)) for p in punkte})
    if len(feld) < 3:
        return QtGui.QPolygonF([QtCore.QPointF(*p) for p in feld])

    def kreuz(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    unten, oben = [], []
    for p in feld:
        while len(unten) >= 2 and kreuz(unten[-2], unten[-1], p) <= 0:
            unten.pop()
        unten.append(p)
    for p in reversed(feld):
        while len(oben) >= 2 and kreuz(oben[-2], oben[-1], p) <= 0:
            oben.pop()
        oben.append(p)
    return QtGui.QPolygonF([QtCore.QPointF(*p) for p in unten[:-1] + oben[:-1]])
