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

from . import PARAMETER_PFAD, einheiten, symbol
from . import halter as hl
from . import uebergabe_werkzeuge as ue
from . import werkstoffe as ws
from . import werkzeuge as wz
from . import werkzeuge_aus_cam as aus_cam
from . import werkzeugkiste as wk
from .gui_halter import HalterDialog
from .gui_hilfe import kopfzeile
from .gui_schnittwerte import SchnittwertBereich
from .gui_teile import GRAU, hinweiszeile, knopf, kurze_liste, mit_einheit, ruhiges_mausrad
from .gui_werkstoffe import WerkstoffDialog
from .gui_werkzeugbild import WerkzeugBild
from .gui_werkzeugbild import symbol as art_symbol
from .gui_zahlen import (
    Zahlenpruefer,
    dezimal,
    groesse_lesen,
    groesse_zeigen,
    zahl_lesen,
    zahl_zeigen,
)
from .sprache import tr

FENSTER_GROESSE = (1100, 760)  # Breite, Höhe in Pixeln
LISTE_BREITE = 300  # Pixel, Startbreite der Werkzeugliste
GROESSTE_NUMMER = 9999
GROESSTE_SCHNEIDENZAHL = 20
SYMBOL_GROESSE = 16  # Pixel, Kästchen mit dem ISO-Buchstaben
# Felder mit Längen – gezeigt in mm oder inch, gespeichert in mm.
# Felder mit Längeneinheit (mm oder in): die Maße der Arten und die Länge ab Spindelnase.
LAENGEN = (*wz.LAENGEN_FELDER, "laenge_spindelnase")

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
        oeffne()


def oeffne(nummer=None):
    """Öffnet die Werkzeugverwaltung – oder holt die offene nach vorn – und wählt, wenn
    angegeben, das Werkzeug mit dieser Nummer. Gibt den Dialog zurück."""
    dialog = WerkzeugDialog.offen
    if dialog is not None and dialog.isVisible():
        dialog.raise_()
        dialog.activateWindow()
    else:
        dialog = WerkzeugDialog()
        dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        dialog.show()
    if nummer is not None:
        dialog.waehle_nummer(nummer)
    return dialog


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


def werkstoffe_anbieten(wahl, bibliothek, klassen=False):
    """Füllt eine Werkstoff-Auswahl: „Alle Werkstoffe“, mit `klassen` die Werkstoffklassen
    („M – rostfreier Stahl“; für die Zeilen der Schnittwert-Tabelle, Manuel, 2026-10-03: „wir
    nehmen die Obergruppen“), eigene, dann die mitgelieferten nach ISO-Gruppe.

    Auch der Dialog „Schnittwerte in den Job“ benutzt sie – ohne Klassen: Am Rohteil steht ein
    Werkstoff. Die Liste klappt höchstens 20 Zeilen hoch auf (kurze_liste).
    """
    kurze_liste(wahl)
    wahl.blockSignals(True)
    wahl.clear()
    wahl.addItem(tr("wv.alle_werkstoffe"), wz.ALLE)
    if klassen:
        wahl.insertSeparator(wahl.count())
        for klasse in ws.KLASSEN:
            wahl.addItem(iso_symbol(ws.klasse_iso(klasse)), ws.klasse_text(klasse), klasse)
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


class Werkzeugbaum(QtGui.QTreeWidget):
    """Die Werkzeugliste, nach Werkzeugart gegliedert – je Art eine Gruppe zum Auf- und
    Zuklappen („Schaftfräser (6)“), darin die Werkzeuge nach Nummer (Manuel, 2026-10-03: „dass
    nicht alle Werkzeuge untereinander dort stehen“). Welche Gruppen zugeklappt sind, merkt
    sie sich (WvZugeklappt)."""

    gewaehlt = QtCore.Signal(object)  # das gewählte Werkzeug, oder None

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setRootIsDecorated(True)
        self.setIndentation(14)
        # Mehrere markieren (Strg, Umschalt) oder eine ganze Gruppe – zum Löschen auf einmal
        # (Manuel, 2026-10-03: „eine Mehrfachauswahl … vll sogar komplette Kategorien“).
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self._gruppen = {}  # Art -> Gruppenzeile
        self._eintraege = []  # die Werkzeugzeilen, in der Reihenfolge der Anzeige
        self._gemeldet = None  # das zuletzt über `gewaehlt` gemeldete Werkzeug
        self.currentItemChanged.connect(self._aktuell_geaendert)
        self.itemExpanded.connect(lambda _e: self._zugeklappt_merken())
        self.itemCollapsed.connect(lambda _e: self._zugeklappt_merken())

    def aufbauen(self, werkzeuge, auswahl=None):
        """Baut den Baum neu: je Art, die vorkommt, eine Gruppe; wählt `auswahl`, sonst das
        erste Werkzeug. Meldet das gewählte über `gewaehlt`."""
        zugeklappt = self._zugeklappt()
        self.blockSignals(True)
        self.clear()
        self._gruppen, self._eintraege = {}, []
        gewaehlt = None
        for art in wz.ARTEN:
            der_art = [w for w in werkzeuge if w.art == art]
            if not der_art:
                continue
            gruppe = QtGui.QTreeWidgetItem([f"{wz.art_text(art)} ({len(der_art)})"])
            gruppe.setIcon(0, art_symbol(art))
            gruppe.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            gruppe.setData(0, QtCore.Qt.UserRole, art)
            schrift = gruppe.font(0)
            schrift.setBold(True)
            gruppe.setFont(0, schrift)
            self.addTopLevelItem(gruppe)
            self._gruppen[art] = gruppe
            for werkzeug in der_art:
                eintrag = QtGui.QTreeWidgetItem([dezimal(wz.zeile(werkzeug))])
                eintrag.setData(0, QtCore.Qt.UserRole, werkzeug)
                gruppe.addChild(eintrag)
                self._eintraege.append(eintrag)
                if werkzeug is auswahl:
                    gewaehlt = eintrag
            gruppe.setExpanded(art not in zugeklappt)
        if gewaehlt is None and self._eintraege:
            gewaehlt = self._eintraege[0]
        if gewaehlt is not None:
            gewaehlt.parent().setExpanded(True)
        self.setCurrentItem(gewaehlt)
        self.blockSignals(False)
        self._gemeldet = self.werkzeug()
        self.gewaehlt.emit(self._gemeldet)

    def eintraege(self):
        """Die Werkzeugzeilen in der Reihenfolge der Anzeige (für Suche und Szenarien)."""
        return list(self._eintraege)

    def werkzeug(self, eintrag=None):
        """Das Werkzeug einer Zeile – ohne Zeile das der gewählten; None bei einer Gruppe."""
        eintrag = self.currentItem() if eintrag is None else eintrag
        if eintrag is None or eintrag.parent() is None:
            return None
        return eintrag.data(0, QtCore.Qt.UserRole)

    def ausgewaehlte(self):
        """Die markierten Werkzeuge in der Reihenfolge der Anzeige – eine markierte Gruppe
        zählt mit allen ihren (gezeigten) Werkzeugen; nichts markiert: das gewählte."""
        markiert = set()
        for eintrag in self.selectedItems():
            if eintrag.parent() is None:
                markiert.update(
                    eintrag.child(i)
                    for i in range(eintrag.childCount())
                    if not eintrag.child(i).isHidden()
                )
            else:
                markiert.add(eintrag)
        werkzeuge = [e.data(0, QtCore.Qt.UserRole) for e in self._eintraege if e in markiert]
        if not werkzeuge and self._gemeldet is not None:
            werkzeuge = [self._gemeldet]
        return werkzeuge

    def waehle(self, werkzeug):
        """Wählt die Zeile des Werkzeugs (und klappt ihre Gruppe auf)."""
        for eintrag in self._eintraege:
            if eintrag.data(0, QtCore.Qt.UserRole) is werkzeug:
                eintrag.parent().setExpanded(True)
                self.setCurrentItem(eintrag)
                return

    def auffrischen(self, werkzeug):
        """Schreibt die Zeile des Werkzeugs neu, ohne den Baum neu zu bauen."""
        for eintrag in self._eintraege:
            if eintrag.data(0, QtCore.Qt.UserRole) is werkzeug:
                eintrag.setText(0, dezimal(wz.zeile(werkzeug)))

    def filtern(self, suche):
        """Zeigt nur die Werkzeuge, die die Suche findet, und nur Gruppen mit Treffern – beim
        Suchen aufgeklappt; ist das gewählte weg, das erste gezeigte."""
        for eintrag in self._eintraege:
            eintrag.setHidden(not wz.passt(eintrag.data(0, QtCore.Qt.UserRole), suche))
        for gruppe in self._gruppen.values():
            treffer = [gruppe.child(i) for i in range(gruppe.childCount())]
            treffer = [e for e in treffer if not e.isHidden()]
            gruppe.setHidden(not treffer)
            if suche and treffer:
                gruppe.setExpanded(True)
        aktuell = self.currentItem()
        if aktuell is not None and not aktuell.isHidden():
            return
        sichtbar = [e for e in self._eintraege if not e.isHidden()]
        self.setCurrentItem(sichtbar[0] if sichtbar else None)

    def _aktuell_geaendert(self, aktuell, _vorher):
        if aktuell is not None and aktuell.parent() is None:
            return  # eine Gruppe (markiert zum Löschen): das gewählte Werkzeug bleibt
        self._gemeldet = self.werkzeug(aktuell)
        self.gewaehlt.emit(self._gemeldet)

    def _zugeklappt(self):
        return set(_parameter().GetString("WvZugeklappt", "").split(","))

    def _zugeklappt_merken(self):
        if self.signalsBlocked():
            return
        zu = [art for art, gruppe in self._gruppen.items() if not gruppe.isExpanded()]
        _parameter().SetString("WvZugeklappt", ",".join(zu))


class WerkzeugDialog(QtGui.QDialog):
    """Die Werkzeugverwaltung. Die Aktionen hinter den Knöpfen sind öffentliche Methoden."""

    offen = None  # das zuletzt geöffnete Fenster – für die Oberflächen-Szenarien
    gespeichert = QtCore.Signal()  # nach jedem Speichern – das Prüffenster rechnet dann neu

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
        # Holen und Übergeben nebeneinander: ein Knopf mit Menü der Bibliotheken.
        self.knopf_aus_cam = QtGui.QPushButton(tr("wv.aus_cam"))
        self.knopf_aus_cam.setToolTip(tr("wv.aus_cam.tooltip"))
        self.knopf_aus_cam.setAutoDefault(False)
        self.knopf_aus_cam.setEnabled(ue.verfuegbar())
        self.menue_aus_cam = QtGui.QMenu(self.knopf_aus_cam)
        self.menue_aus_cam.aboutToShow.connect(self._menue_aus_cam_fuellen)
        self.knopf_aus_cam.setMenu(self.menue_aus_cam)
        unten.addWidget(self.knopf_aus_cam)
        self.knopf_cam = knopf(tr("wv.cam"), tr("wv.cam.tooltip"), self.an_cam_uebergeben)
        self.knopf_cam.setEnabled(ue.verfuegbar())
        unten.addWidget(self.knopf_cam)
        unten.addStretch()
        unten.addWidget(self._knoepfe())
        aufbau.addLayout(unten)
        ruhiges_mausrad(self)

        self._liste_aufbauen(auswahl=self._zuletzt_gewaehlt())

    # --- Aufbau -------------------------------------------------------------------

    def _bereich_werkstoff(self):
        """Oben: „Werkstoffe…“ (die Liste mit Suche, allen Angaben und eigenen Werkstoffen)
        und mm/inch. Der Werkstoff selbst steht je Zeile in der Schnittwert-Tabelle (Manuel,
        2026-10-01: „das Material muss zu den Schnittwerten“)."""
        rahmen = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(rahmen)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.addWidget(kopfzeile(tr("wv.werkstoffe_masssystem"), "werkstoffe"))
        zeile = QtGui.QHBoxLayout()
        self.knopf_werkstoffe = knopf(
            tr("wv.werkstoffe"), tr("wv.werkstoffe.tooltip"), self.werkstoffe_zeigen
        )
        zeile.addWidget(self.knopf_werkstoffe)
        zeile.addStretch()
        # mm oder inch – gilt für das ganze Addon; gespeichert wird in mm.
        self.wahl_masssystem = QtGui.QComboBox()
        self.wahl_masssystem.addItem("mm", einheiten.METRISCH)
        self.wahl_masssystem.addItem("inch", einheiten.ZOLL)
        self.wahl_masssystem.setToolTip(tr("wv.masssystem.tooltip"))
        self.wahl_masssystem.setCurrentIndex(self.wahl_masssystem.findData(einheiten.masssystem()))
        self.wahl_masssystem.currentIndexChanged.connect(self._masssystem_gewechselt)
        zeile.addWidget(self.wahl_masssystem)
        aufbau.addLayout(zeile)
        return rahmen

    def _bereich_liste(self):
        rahmen = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(rahmen)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.addWidget(kopfzeile(tr("wv.werkzeuge"), "werkzeuge"))
        self.suche = QtGui.QLineEdit()
        self.suche.setPlaceholderText(tr("wv.suche.platzhalter"))
        self.suche.setToolTip(tr("wv.suche.tooltip"))
        self.suche.setClearButtonEnabled(True)
        self.suche.textChanged.connect(lambda *_: self._filtern())
        aufbau.addWidget(self.suche)
        self.liste = Werkzeugbaum()
        self.liste.gewaehlt.connect(self._werkzeug_gewaehlt)
        aufbau.addWidget(self.liste, 1)
        zeile = QtGui.QHBoxLayout()
        self.knopf_neu = knopf(tr("wv.neu"), tr("wv.neu.tooltip"), self.werkzeug_anlegen)
        self.knopf_kopieren = knopf(
            tr("wv.kopieren"), tr("wv.kopieren.tooltip"), self.werkzeug_kopieren
        )
        self.knopf_loeschen = knopf(
            tr("wv.loeschen"), tr("wv.loeschen.tooltip"), self.werkzeug_loeschen
        )
        for element in (self.knopf_neu, self.knopf_kopieren, self.knopf_loeschen):
            zeile.addWidget(element)
        aufbau.addLayout(zeile)
        # Die Werkzeugkiste der Hersteller (W-007): Reihen echter Werkzeuge mit Werten.
        self.knopf_kiste = knopf(tr("wv.kiste"), tr("wv.kiste.tooltip"), self.kiste_zeigen)
        aufbau.addWidget(self.knopf_kiste)
        return rahmen

    def _bereich_werkzeug(self):
        self._laengen_zeilen = []  # Felder mit Längeneinheit – beim Wechsel mm/inch neu beschriftet
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

        # Die Arten nach Gruppen – „Fräsen“, „Bohren“ … als Überschrift, nicht wählbar.
        self.feld_art = QtGui.QComboBox()
        for gruppe in wz.GRUPPEN:
            self.feld_art.addItem(wz.gruppen_text(gruppe))
            kopf = self.feld_art.model().item(self.feld_art.count() - 1)
            kopf.setEnabled(False)
            schrift = kopf.font()
            schrift.setBold(True)
            kopf.setFont(schrift)
            for art in wz.arten_der_gruppe(gruppe):
                # Vor jedem Namen das Bild der Art, klein – wie in InventorCAM.
                self.feld_art.addItem(art_symbol(art), wz.art_text(art), art)
        self.feld_art.setIconSize(QtCore.QSize(20, 20))
        self.feld_art.setMaxVisibleItems(self.feld_art.count())
        self.feld_art.setToolTip(tr("wv.art.tooltip"))
        self.feld_art.currentIndexChanged.connect(self._art_geaendert)

        # Alle Maße, die eine Art haben kann. Welche zu sehen sind und in welcher
        # Reihenfolge, legt _felder_anordnen() je Art fest (wz.ARTDATEN).
        self._zahlenfelder = {}  # Feldname -> Eingabefeld
        self._felder = {}  # Feldname -> (Beschriftung, Zeile mit Feld und Einheit)
        for feld in wz.ZAHLEN_FELDER:
            eingabe = self._zahlenfeld(_tooltip(feld), feld)
            if feld in LAENGEN:
                zeile = self._mit_laenge(eingabe)
            elif feld == wz.STEIGUNG:
                zeile = mit_einheit(eingabe, _steigung_einheit())
                self._steigung_zeile = zeile
            else:
                zeile = mit_einheit(eingabe, "°")
            self._zahlenfelder[feld] = eingabe
            self._felder[feld] = (QtGui.QLabel(), zeile)
        # Für alle Arten, unter ihren Maßen: die Länge ab Spindelnase, mit Halter – für
        # „Auf der Maschine prüfen“ (W-001 Stufe 4a). Leer gilt die Gesamtlänge.
        eingabe = self._zahlenfeld(tr("wv.laenge_spindelnase.tooltip"), "laenge_spindelnase")
        self._zahlenfelder["laenge_spindelnase"] = eingabe
        self.beschriftung_laenge_spindelnase = QtGui.QLabel(tr("wv.laenge_spindelnase"))
        self.beschriftung_laenge_spindelnase.setToolTip(tr("wv.laenge_spindelnase.tooltip"))
        self.zeile_laenge_spindelnase = self._mit_laenge(eingabe)
        # Daneben der Halter (W-002 Stufe D): Auswahl und „Halter …“ für das Fenster.
        self.feld_halter = QtGui.QComboBox()
        self.feld_halter.setToolTip(tr("wv.halter.tooltip"))
        self.feld_halter.currentIndexChanged.connect(self._halter_gewaehlt)
        self.knopf_halter = knopf(
            tr("wv.halter.knopf"), tr("wv.halter.knopf.tooltip"), self.halter_zeigen
        )
        self.zeile_halter = QtGui.QWidget()
        halter_aufbau = QtGui.QHBoxLayout(self.zeile_halter)
        halter_aufbau.setContentsMargins(0, 0, 0, 0)
        halter_aufbau.addWidget(self.feld_halter, 1)
        halter_aufbau.addWidget(self.knopf_halter)
        self.beschriftung_halter = QtGui.QLabel(tr("wv.halter"))
        self.beschriftung_halter.setToolTip(tr("wv.halter.tooltip"))

        self.feld_schneiden = QtGui.QSpinBox()
        self.feld_schneiden.setRange(1, GROESSTE_SCHNEIDENZAHL)
        self.feld_schneiden.setToolTip(tr("wv.schneiden.tooltip"))
        self.feld_schneiden.valueChanged.connect(self._schneiden_geaendert)
        self._felder["schneiden"] = (QtGui.QLabel(), self.feld_schneiden)

        self.feld_schneidstoff = QtGui.QComboBox()
        self.feld_schneidstoff.addItem(tr("wv.schneidstoff.vhm"), wz.VHM)
        self.feld_schneidstoff.addItem(tr("wv.schneidstoff.hss"), wz.HSS)
        self.feld_schneidstoff.setToolTip(tr("wv.schneidstoff.tooltip"))
        self.feld_schneidstoff.currentIndexChanged.connect(self._schneidstoff_geaendert)
        self._felder["schneidstoff"] = (QtGui.QLabel(), self.feld_schneidstoff)

        self.feld_ausfuehrung = QtGui.QComboBox()
        self.feld_ausfuehrung.addItem(wz.ausfuehrung_text(""), "")
        for ausfuehrung in wz.AUSFUEHRUNGEN:
            self.feld_ausfuehrung.addItem(wz.ausfuehrung_text(ausfuehrung), ausfuehrung)
        self.feld_ausfuehrung.setToolTip(tr("wv.ausfuehrung.tooltip"))
        self.feld_ausfuehrung.currentIndexChanged.connect(self._ausfuehrung_geaendert)
        self._felder["ausfuehrung"] = (QtGui.QLabel(), self.feld_ausfuehrung)

        self.feld_drehrichtung = QtGui.QComboBox()
        for drehrichtung in wz.DREHRICHTUNGEN:
            self.feld_drehrichtung.addItem(wz.drehrichtung_text(drehrichtung), drehrichtung)
        self.feld_drehrichtung.setToolTip(tr("wv.drehrichtung.tooltip"))
        self.feld_drehrichtung.currentIndexChanged.connect(self._drehrichtung_geaendert)
        self._felder[wz.DREHRICHTUNG] = (QtGui.QLabel(), self.feld_drehrichtung)

        # Wie bisher erreichbar: feld_durchmesser, zeile_eckradius, beschriftung_eckradius …
        for feld, (beschriftung, zeile) in self._felder.items():
            setattr(self, f"beschriftung_{feld}", beschriftung)
            setattr(self, f"zeile_{feld}", zeile)
        for feld, eingabe in self._zahlenfelder.items():
            setattr(self, f"feld_{feld}", eingabe)
        self._angeordnet = None  # für welche Art die Felder gerade angeordnet sind

        self.feld_name = QtGui.QLineEdit()
        self.feld_name.setToolTip(tr("wv.name.tooltip"))
        self.feld_name.textEdited.connect(self._name_geaendert)

        self.feld_bezeichnung = QtGui.QLineEdit()
        self.feld_bezeichnung.setPlaceholderText(tr("wv.bezeichnung.platzhalter"))
        self.feld_bezeichnung.setToolTip(tr("wv.bezeichnung.tooltip"))
        self.feld_bezeichnung.textEdited.connect(self._bezeichnung_geaendert)

        # Woher das Werkzeug kommt (P-2026-10-02-46): Hersteller und Artikelnummer, dazu die
        # Seite zum Bestellen und der Katalog – „Öffnen“ zeigt sie im Browser.
        self._herkunft = []  # (Beschriftung, Zeile) – angeordnet unter der Bezeichnung
        for eigenschaft, text, tooltip in (
            ("hersteller", tr("wv.hersteller"), tr("wv.hersteller.tooltip")),
            ("artikel", tr("wv.artikel"), tr("wv.artikel.tooltip")),
            ("link", tr("wv.link"), tr("wv.link.tooltip")),
            ("katalog", tr("wv.katalog"), tr("wv.katalog.tooltip")),
        ):
            feld = QtGui.QLineEdit()
            feld.setToolTip(tooltip)
            feld.textEdited.connect(lambda text, e=eigenschaft: self._text_geaendert(e, text))
            setattr(self, f"feld_{eigenschaft}", feld)
            zeile = feld
            if eigenschaft in ("link", "katalog"):
                zeile = QtGui.QWidget()
                zeilen_aufbau = QtGui.QHBoxLayout(zeile)
                zeilen_aufbau.setContentsMargins(0, 0, 0, 0)
                zeilen_aufbau.addWidget(feld, 1)
                oeffnen = knopf(
                    tr("wv.oeffnen"),
                    tr("wv.oeffnen.tooltip"),
                    lambda f=feld: self.oeffnen(f.text()),
                )
                setattr(self, f"knopf_{eigenschaft}", oeffnen)
                zeilen_aufbau.addWidget(oeffnen)
            beschriftung = QtGui.QLabel(text)
            beschriftung.setToolTip(tooltip)
            self._herkunft.append((beschriftung, zeile))

        # Oben Nummer und Art, darunter der Name über die ganze Breite; die
        # Maße der Art ordnet _felder_anordnen() darunter an, zu zweit je Reihe.
        self._gitter = gitter
        gitter.addWidget(QtGui.QLabel(tr("wv.nummer")), 0, 0)
        gitter.addWidget(self.feld_nummer, 0, 1)
        gitter.addWidget(QtGui.QLabel(tr("wv.art")), 0, 2)
        gitter.addWidget(self.feld_art, 0, 3)
        gitter.addWidget(QtGui.QLabel(tr("wv.name")), 1, 0)
        gitter.addWidget(self.feld_name, 1, 1, 1, 3)
        self.beschriftung_bezeichnung = QtGui.QLabel(tr("wv.bezeichnung"))

        # Grau: Beispielwerte eines neuen Werkzeugs – sie gelten trotzdem.
        self.beispiel_hinweis = QtGui.QLabel(tr("wv.beispiel"))
        self.beispiel_hinweis.setWordWrap(True)
        self.beispiel_hinweis.setStyleSheet(f"color: {GRAU.name()};")
        self.hinweis = hinweiszeile()
        # Rechts neben den Feldern das Werkzeug im richtigen Verhältnis.
        self.werkzeugbild = WerkzeugBild()
        self.werkzeugbild.setToolTip(tr("wv.werkzeugbild.tooltip"))
        self._felder_anordnen(wz.SCHAFTFRAESER)

        aufbau.addWidget(self.formular_rahmen)
        self.schnittwerte = SchnittwertBereich(self._schnittwerte_geaendert)
        aufbau.addWidget(self.schnittwerte, 1)
        return rahmen

    def _mit_laenge(self, feld):
        """Feld mit der Längeneinheit (mm oder in) daneben."""
        zeile = mit_einheit(feld, einheiten.einheit(einheiten.LAENGE))
        self._laengen_zeilen.append(zeile)
        return zeile

    @staticmethod
    def _zeigen(eigenschaft, wert):
        """Der Feldtext zu einem Wert: Längen im gewählten Maßsystem, Winkel in Grad,
        die Steigung in mm oder Gängen je Zoll."""
        if eigenschaft in LAENGEN:
            return groesse_zeigen(wert, einheiten.LAENGE)
        if eigenschaft == wz.STEIGUNG:
            return zahl_zeigen(wz.steigung_anzeige(wert))
        return zahl_zeigen(wert)

    @staticmethod
    def _lesen(eigenschaft, text):
        """Ein Feldtext als gespeicherter Wert: Längen und Steigung in mm."""
        if eigenschaft in LAENGEN:
            return groesse_lesen(text, einheiten.LAENGE)
        if eigenschaft == wz.STEIGUNG:
            return wz.steigung_lesen(zahl_lesen(text))
        return zahl_lesen(text)

    def _zahlenfeld(self, tooltip, eigenschaft):
        feld = QtGui.QLineEdit()
        feld.setValidator(Zahlenpruefer(feld))
        feld.setPlaceholderText(tr("feld.unbekannt"))
        feld.setToolTip(tooltip)
        feld.textEdited.connect(lambda _text: self._beispiel_weg(eigenschaft))
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

    def _masssystem_gewechselt(self, _index):
        """mm oder inch: gilt sofort für das ganze Addon; Felder und Tabelle zeigen um."""
        # Was noch im Feld steht, gilt in der Einheit, in der es getippt wurde.
        self._felder_uebernehmen()
        einheiten.setze_masssystem(self.wahl_masssystem.currentData())
        for zeile in self._laengen_zeilen:
            zeile.einheit.setText(einheiten.einheit(einheiten.LAENGE))
        self._steigung_zeile.einheit.setText(_steigung_einheit())
        self._liste_aufbauen(auswahl=self.werkzeug)

    def werkstoffe_zeigen(self):
        """„Werkstoffe…“: die ganze Liste, eigene anlegen und ändern – vorgewählt der Werkstoff
        der gewählten Zeile der Schnittwerte; danach bietet die Tabelle die Liste neu an."""
        dialog = WerkstoffDialog(self, self.bibliothek, iso_symbol)
        kennung = self.schnittwerte.gewaehlter_werkstoff
        if kennung != wz.ALLE:
            dialog.waehle(kennung)
        dialog.exec()
        WerkstoffDialog.offen = None
        if dialog.geaendert:
            self._schnittwerte_zeigen()

    # --- Werkzeugliste ----------------------------------------------------------------

    def waehle_nummer(self, nummer):
        """Wählt das erste Werkzeug mit dieser Nummer; False, wenn es keines gibt."""
        self._felder_uebernehmen()
        werkzeug = next(
            (w for w in self.bibliothek.sortierte_werkzeuge() if w.nummer == nummer), None
        )
        if werkzeug is not None:
            self._liste_aufbauen(auswahl=werkzeug)
        return werkzeug is not None

    def _zuletzt_gewaehlt(self):
        kennung = _parameter().GetString("WvWerkzeug", "")
        return next((w for w in self.bibliothek.werkzeuge if w.kennung == kennung), None)

    def _liste_aufbauen(self, auswahl=None):
        """Baut die Liste neu (je Art eine Gruppe, darin nach Nummer) und wählt `auswahl` oder
        das erste Werkzeug."""
        self.liste.aufbauen(self.bibliothek.sortierte_werkzeuge(), auswahl)
        # Ein neues oder gewähltes Werkzeug, das die Suche verstecken würde:
        # lieber die Suche leeren, als es unsichtbar zu bearbeiten.
        if self.werkzeug is not None and not wz.passt(self.werkzeug, self.suche.text()):
            self.suche.clear()
        self._filtern()

    def _filtern(self):
        """Zeigt nur die Werkzeuge, die die Suche findet; ist das gewählte weg, das erste gezeigte."""
        self.liste.filtern(self.suche.text())

    def _zeile_auffrischen(self):
        """Schreibt die Listenzeile des gewählten Werkzeugs neu, ohne die Liste neu zu bauen."""
        if self.werkzeug is not None:
            self.liste.auffrischen(self.werkzeug)

    def _werkzeug_gewaehlt(self, werkzeug):
        self.werkzeug = werkzeug
        if self.werkzeug is not None:
            _parameter().SetString("WvWerkzeug", self.werkzeug.kennung)
        self._felder_fuellen()

    def werkzeug_anlegen(self):
        """„Neu“: ein Schaftfräser mit der nächsten freien Nummer und grauen Beispielwerten."""
        werkzeug = self.bibliothek.neues_werkzeug()
        self._liste_aufbauen(auswahl=werkzeug)
        # Der Durchmesser markiert: Tippen ersetzt das Beispiel.
        self.feld_durchmesser.setFocus()
        self.feld_durchmesser.selectAll()
        return werkzeug

    def werkzeug_kopieren(self):
        """„Kopieren“: das gewählte Werkzeug mit allen Werten und neuer Nummer."""
        if self.werkzeug is None:
            return None
        kopie = self.bibliothek.kopiere(self.werkzeug)
        self._liste_aufbauen(auswahl=kopie)
        return kopie

    def werkzeug_loeschen(self, fragen=True):
        """„Löschen“: alle markierten Werkzeuge (eine markierte Gruppe: ihre Werkzeuge), sonst
        das gewählte – nach Rückfrage; `fragen=False` für die Szenarien."""
        weg = self.liste.ausgewaehlte()
        if not weg:
            return
        if fragen:
            zeilen = [dezimal(wz.zeile(w)) for w in weg]
            if len(weg) == 1:
                frage = tr("wv.loeschen.frage", werkzeug=zeilen[0])
            else:
                liste = "\n".join(zeilen[:12] + (["…"] if len(zeilen) > 12 else []))
                frage = tr("wv.loeschen.frage_mehrere", anzahl=len(weg), liste=liste)
            antwort = QtGui.QMessageBox.question(
                self,
                tr("wv.titel"),
                frage,
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                QtGui.QMessageBox.No,
            )
            if antwort != QtGui.QMessageBox.Yes:
                return
        # Danach das nächste in der Anzeige hinter dem letzten gelöschten, sonst das davor.
        angezeigt = [e.data(0, QtCore.Qt.UserRole) for e in self.liste.eintraege()]
        letzte = max(angezeigt.index(w) for w in weg)
        for werkzeug in weg:
            self.bibliothek.entferne(werkzeug)
        rest = [w for w in angezeigt if w not in weg]
        zeile = min(letzte - len(weg) + 1, len(rest) - 1)  # alle gelöschten lagen davor
        self._liste_aufbauen(auswahl=rest[zeile] if rest else None)

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
        for feld, eingabe in self._zahlenfelder.items():
            eingabe.setText(self._zeigen(feld, getattr(w, feld)))
        self.feld_schneiden.setValue(w.schneiden)
        self.feld_ausfuehrung.setCurrentIndex(max(self.feld_ausfuehrung.findData(w.ausfuehrung), 0))
        links = wz.LINKS if wz.dreht_links(w) else wz.RECHTS
        self.feld_drehrichtung.setCurrentIndex(self.feld_drehrichtung.findData(links))
        self.feld_schneidstoff.setCurrentIndex(self.feld_schneidstoff.findData(w.schneidstoff))
        self.feld_bezeichnung.setText(w.bezeichnung)
        for eigenschaft in ("hersteller", "artikel", "link", "katalog"):
            feld = getattr(self, f"feld_{eigenschaft}")
            feld.setText(getattr(w, eigenschaft))
            feld.setCursorPosition(0)  # der Anfang einer langen Adresse, nicht ihr Ende
        self.knopf_link.setEnabled(bool(w.link))
        self.knopf_katalog.setEnabled(bool(w.katalog))
        self.feld_name.setText(w.name)
        self._halter_anbieten()
        self._fuellt = False
        self._felder_anordnen(w.art)
        self._beispiele_zeigen()
        self._schaetzung_zeigen()
        self.werkzeugbild.zeige(w)
        self._hinweise()
        self._schnittwerte_zeigen()

    def _schnittwerte_zeigen(self):
        """Die Schnittwerte des gewählten Werkzeugs – alle, je Zeile mit ihrem Werkstoff."""
        self.schnittwerte.zeige(self.werkzeug, self.bibliothek)

    def _schnittwerte_geaendert(self):
        """Eine Änderung in der Tabelle; gespeichert wird erst mit OK oder Übernehmen."""

    def _felder_anordnen(self, art):
        """Die Maße der Art unter Nummer, Art und Name, zu zweit je Reihe, Pflicht fett;
        darunter Bezeichnung und Hinweise, rechts das Bild. Was die Art nicht hat,
        ist nicht zu sehen – sein Wert bleibt, falls man zurückwechselt."""
        if art == self._angeordnet:
            return
        self._angeordnet = art
        gitter = self._gitter
        daten = wz.artdaten(art)
        for beschriftung, zeile in self._felder.values():
            gitter.removeWidget(beschriftung)
            gitter.removeWidget(zeile)
            beschriftung.hide()
            zeile.hide()
        for widget in (
            self.beschriftung_laenge_spindelnase,
            self.zeile_laenge_spindelnase,
            self.beschriftung_halter,
            self.zeile_halter,
            self.beschriftung_bezeichnung,
            self.feld_bezeichnung,
            *(teil for paar in self._herkunft for teil in paar),
            self.beispiel_hinweis,
            self.hinweis,
            self.werkzeugbild,
        ):
            gitter.removeWidget(widget)
        for i, feld in enumerate(daten.felder):
            beschriftung, zeile = self._felder[feld]
            beschriftung.setText(wz.feld_text(feld, art))
            reihe, spalte = 2 + i // 2, 2 * (i % 2)
            gitter.addWidget(beschriftung, reihe, spalte)
            gitter.addWidget(zeile, reihe, spalte + 1)
            # Fett erst nach dem Einhängen: Hängt eine Beschriftung zum ersten
            # Mal im schon gezeigten Dialog, setzt FreeCADs Stylesheet ihre
            # Schrift zurück (gesehen in 1.1.3, Steigung beim Gewindebohrer).
            schrift = beschriftung.font()
            schrift.setBold(feld in daten.pflicht)
            beschriftung.setFont(schrift)
            beschriftung.show()
            zeile.show()
        unten = 2 + (len(daten.felder) + 1) // 2
        gitter.addWidget(self.beschriftung_laenge_spindelnase, unten, 0)
        gitter.addWidget(self.zeile_laenge_spindelnase, unten, 1)
        # Der Halter über die ganze Breite – Namen wie „Spannzangenfutter ER32 · SK40“.
        gitter.addWidget(self.beschriftung_halter, unten + 1, 0)
        gitter.addWidget(self.zeile_halter, unten + 1, 1, 1, 3)
        gitter.addWidget(self.beschriftung_bezeichnung, unten + 2, 0)
        gitter.addWidget(self.feld_bezeichnung, unten + 2, 1, 1, 3)
        # Hersteller und Artikel, darunter Bestellen und Katalog – zu zweit je Reihe.
        for i, (beschriftung, zeile) in enumerate(self._herkunft):
            reihe, spalte = unten + 3 + i // 2, 2 * (i % 2)
            gitter.addWidget(beschriftung, reihe, spalte)
            gitter.addWidget(zeile, reihe, spalte + 1)
        gitter.addWidget(self.beispiel_hinweis, unten + 5, 0, 1, 4)
        gitter.addWidget(self.hinweis, unten + 6, 0, 1, 4)
        gitter.addWidget(self.werkzeugbild, 0, 4, unten + 7, 1, QtCore.Qt.AlignTop)

    def _beispielfelder(self):
        return {
            **self._zahlenfelder,
            "schneiden": self.feld_schneiden,
            "ausfuehrung": self.feld_ausfuehrung,
        }

    def _beispiele_zeigen(self):
        """Beispielwerte grau, dazu der Satz, dass sie gelten."""
        beispiel = self.werkzeug.beispiel if self.werkzeug is not None else set()
        for eigenschaft, feld in self._beispielfelder().items():
            feld.setStyleSheet(f"color: {GRAU.name()};" if eigenschaft in beispiel else "")
        self.beispiel_hinweis.setVisible(bool(beispiel))

    def _beispiel_weg(self, eigenschaft):
        """Eigene Eingabe in einem Beispielfeld: Der Wert ist ab jetzt der eigene, nicht grau."""
        if self._fuellt or self.werkzeug is None or eigenschaft not in self.werkzeug.beispiel:
            return
        self.werkzeug.beispiel.discard(eigenschaft)
        self._beispiele_zeigen()
        self.werkzeugbild.zeige(self.werkzeug)

    def _schaetzung_zeigen(self):
        """Leere Felder für Name, Gesamtlänge und Schaft zeigen grau, was stattdessen gilt."""
        w = self.werkzeug
        self.feld_name.setPlaceholderText(
            tr("wv.name.platzhalter", name=wz.beispielname(w)) if w is not None else ""
        )
        if w is None or not w.durchmesser:
            laenge = schaft = tr("feld.unbekannt")
        else:
            laenge = tr(
                "wv.gesamtlaenge.platzhalter",
                wert=groesse_zeigen(wz.geschaetzte_laenge(w), einheiten.LAENGE),
            )
            geschaetzt = wz.schaft_fuer_cam(w)
            wert = groesse_zeigen(geschaetzt, einheiten.LAENGE)
            if geschaetzt == w.durchmesser:
                schaft = tr("wv.schaft.platzhalter", wert=wert)
            else:  # Taster, Zentrierbohrer: ein Anteil von D
                schaft = tr("wv.schaft.platzhalter.geschaetzt", wert=wert)
        self.feld_gesamtlaenge.setPlaceholderText(laenge)
        self.feld_schaft.setPlaceholderText(schaft)
        # Leer gilt mit Halter Halterlänge + Gesamtlänge − Spanntiefe, ohne die Gesamtlänge –
        # eingetragen oder geschätzt.
        halter = self.bibliothek.halter_von(w) if w is not None else None
        gesamt = (w.gesamtlaenge or wz.geschaetzte_laenge(w)) if w is not None else 0.0
        if halter is not None:
            platzhalter = tr(
                "wv.laenge_spindelnase.platzhalter_halter",
                wert=groesse_zeigen(wz.laenge_mit_halter(w, halter), einheiten.LAENGE),
            )
        elif gesamt:
            platzhalter = tr(
                "wv.laenge_spindelnase.platzhalter", wert=groesse_zeigen(gesamt, einheiten.LAENGE)
            )
        else:
            platzhalter = tr("feld.unbekannt")
        self.feld_laenge_spindelnase.setPlaceholderText(platzhalter)
        # Beim gewinkelten Halter zählt die Länge ab seinem Bezugspunkt (W-002 Stufe E).
        gewinkelt = halter is not None and halter.gewinkelt
        self.beschriftung_laenge_spindelnase.setText(
            tr("wv.laenge_bezugspunkt") if gewinkelt else tr("wv.laenge_spindelnase")
        )
        tooltip = (
            tr("wv.laenge_bezugspunkt.tooltip")
            if gewinkelt
            else tr("wv.laenge_spindelnase.tooltip")
        )
        self.beschriftung_laenge_spindelnase.setToolTip(tooltip)
        self.feld_laenge_spindelnase.setToolTip(tooltip)
        # Leere Winkel: grau der übliche der Art (Bohrer 118°, Gewinde 60° …).
        for feld in wz.WINKEL_FELDER:
            ueblich = wz.ueblich(w.art, feld) if w is not None else 0.0
            self._zahlenfelder[feld].setPlaceholderText(
                tr("wv.ueblich.platzhalter", wert=zahl_zeigen(ueblich))
                if ueblich
                else tr("feld.unbekannt")
            )

    def _hinweise(self):
        """Zeigt am Werkzeug, was fehlt oder nicht passt – sofort, nicht erst beim Speichern."""
        w = self.werkzeug
        saetze = []
        if w is not None:
            pflicht = wz.artdaten(w.art).pflicht
            if "durchmesser" in pflicht and not w.durchmesser:
                saetze.append(tr("wv.hinweis.durchmesser"))
            if wz.STEIGUNG in pflicht and not w.steigung:
                saetze.append(tr("wv.hinweis.steigung"))
            if w.gesamtlaenge and w.gesamtlaenge < w.schneidenlaenge:
                saetze.append(
                    tr(
                        "wv.hinweis.gesamtlaenge",
                        laenge=groesse_zeigen(w.gesamtlaenge, einheiten.LAENGE),
                        schneide=groesse_zeigen(w.schneidenlaenge, einheiten.LAENGE),
                    )
                )
            doppelt = self.bibliothek.mit_nummer(w.nummer, ausser=w)
            if doppelt is not None:
                saetze.append(
                    tr("wv.hinweis.nummer", nummer=w.nummer, werkzeug=dezimal(wz.kurz(doppelt)))
                )
            gleicher_name = self.bibliothek.mit_name(w.name, ausser=w)
            if gleicher_name is not None:
                saetze.append(tr("wv.hinweis.name", name=w.name, nummer=gleicher_name.nummer))
        self.hinweis.setText("\n".join(saetze))
        self.hinweis.setVisible(bool(saetze))

    def _halter_anbieten(self):
        """Die Auswahl der Halter: „ohne“ und alle nach Namen; gewählt der des Werkzeugs."""
        auswahl = self.feld_halter
        auswahl.blockSignals(True)
        auswahl.clear()
        auswahl.addItem(tr("wv.halter.ohne"), "")
        for halter in self.bibliothek.sortierte_halter():
            auswahl.addItem(hl.text(halter), halter.kennung)
        kennung = self.werkzeug.halter if self.werkzeug is not None else ""
        auswahl.setCurrentIndex(max(auswahl.findData(kennung), 0))
        auswahl.blockSignals(False)

    def _halter_gewaehlt(self, index):
        w = self.werkzeug
        if self._fuellt or w is None or index < 0:
            return
        w.halter = self.feld_halter.itemData(index) or ""
        self._geaendert()

    def halter_zeigen(self):
        """„Halter …“: Halter anlegen und bearbeiten; mit OK bekommt das gewählte Werkzeug den
        dort gewählten Halter. Gespeichert wird mit OK oder Übernehmen hier."""
        dialog = HalterDialog(self, self.bibliothek, self.werkzeug)
        if dialog.exec():
            self._halter_anbieten()
            if self.werkzeug is not None:
                self._geaendert()

    def _geaendert(self):
        """Nach jeder Eingabe: Listenzeile, Hinweise und Schnittwerte auf den neuen Stand."""
        self._zeile_auffrischen()
        self._schaetzung_zeigen()
        self.werkzeugbild.zeige(self.werkzeug)
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
        # Beispielfelder und leere Felder bekommen die Beispiele der neuen Art.
        wz.beispielwerte_setzen(self.werkzeug)
        self._felder_fuellen()
        self._liste_aufbauen(auswahl=self.werkzeug)  # in die Gruppe der neuen Art

    def _schneiden_geaendert(self, wert):
        if self._fuellt or self.werkzeug is None:
            return
        self.werkzeug.schneiden = int(wert)
        self._beispiel_weg("schneiden")
        self._geaendert()

    def _ausfuehrung_geaendert(self, _index):
        if self._fuellt or self.werkzeug is None:
            return
        self.werkzeug.ausfuehrung = self.feld_ausfuehrung.currentData() or ""
        self._beispiel_weg("ausfuehrung")
        self._geaendert()

    def _drehrichtung_geaendert(self, _index):
        if self._fuellt or self.werkzeug is None:
            return
        self.werkzeug.drehrichtung = self.feld_drehrichtung.currentData() or ""
        self._geaendert()

    def _schneidstoff_geaendert(self, _index):
        if self._fuellt or self.werkzeug is None:
            return
        self.werkzeug.schneidstoff = self.feld_schneidstoff.currentData()
        self._geaendert()

    def _name_geaendert(self, text):
        if self._fuellt or self.werkzeug is None:
            return
        self.werkzeug.name = text.strip()
        self._geaendert()

    def _bezeichnung_geaendert(self, text):
        if self._fuellt or self.werkzeug is None:
            return
        self.werkzeug.bezeichnung = text.strip()

    def _text_geaendert(self, eigenschaft, text):
        """Hersteller, Artikel, Bestellseite, Katalog – gespeichert mit OK oder Übernehmen."""
        if self._fuellt or self.werkzeug is None:
            return
        setattr(self.werkzeug, eigenschaft, text.strip())
        if eigenschaft in ("link", "katalog"):
            getattr(self, f"knopf_{eigenschaft}").setEnabled(bool(text.strip()))

    @staticmethod
    def oeffnen(adresse):
        """Öffnet die Bestellseite oder den Katalog im Browser (ohne „https://“ davor ergänzt).
        Gibt zurück, ob es ging; ohne Adresse geschieht nichts."""
        adresse = adresse.strip()
        if not adresse:
            return False
        if "://" not in adresse:
            adresse = "https://" + adresse
        return bool(QtGui.QDesktopServices.openUrl(QtCore.QUrl(adresse)))

    def _zahl_uebernehmen(self, feld, eigenschaft):
        if self._fuellt or self.werkzeug is None:
            return
        # Steht noch da, was das Feld beim Füllen zeigte, bleibt der Wert: Das
        # Feld zeigt 12 Stellen, zurückgelesen wäre ein längerer Wert gekürzt –
        # eine Änderung, die niemand gemacht hat.
        gezeigt = self._zeigen(eigenschaft, getattr(self.werkzeug, eigenschaft))
        if feld.text().strip() == gezeigt:
            return
        try:
            neu = self._lesen(eigenschaft, feld.text())
        except ValueError:  # noch keine Zahl („,“ oder „-“): bleibt, wie es war
            feld.setText(gezeigt)
            return
        if eigenschaft == "durchmesser":
            self._zustellungen_anpassen(self.werkzeug.durchmesser, neu)
        setattr(self.werkzeug, eigenschaft, neu)
        self._beispiel_weg(eigenschaft)
        self._geaendert()

    def _zustellungen_anpassen(self, alt, neu, fragen=True):
        """Neuer Durchmesser: ae und ap der Einsätze mit umrechnen? Fragt, wenn es welche gibt.

        Gedacht für „Kopieren“ und dann einen anderen Durchmesser eintragen –
        die Zeilen passen dann wieder zum Fräser. Gibt zurück, ob umgerechnet
        wurde.
        """
        if alt <= 0 or neu <= 0 or alt == neu or not self.werkzeug.hat_zustellungen():
            return False
        if fragen:
            antwort = QtGui.QMessageBox.question(
                self,
                tr("wv.titel"),
                tr(
                    "wv.umrechnen.frage",
                    alt=groesse_zeigen(alt, einheiten.LAENGE),
                    neu=groesse_zeigen(neu, einheiten.LAENGE),
                ),
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                QtGui.QMessageBox.Yes,
            )
            if antwort != QtGui.QMessageBox.Yes:
                return False
        self.werkzeug.zustellungen_umrechnen(neu / alt)
        return True

    def _felder_uebernehmen(self):
        """Übernimmt, was noch im Zahlenfeld mit dem Fokus steht (vor dem Speichern)."""
        for eigenschaft, feld in self._zahlenfelder.items():
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
        self.gespeichert.emit()
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

    def _menue_aus_cam_fuellen(self):
        """Die Werkzeugbibliotheken von FreeCAD CAM, je eine Zeile mit der Zahl der Werkzeuge."""
        self.menue_aus_cam.clear()
        try:
            bibliotheken = aus_cam.bibliotheken()
        except Exception as fehler:  # jeder Fehler von CAM soll als Satz ankommen
            FreeCAD.Console.PrintError(f"CAM-Addon: Bibliotheken lesen: {fehler}\n")
            bibliotheken = []
        for adresse, name, anzahl in bibliotheken:
            aktion = self.menue_aus_cam.addAction(
                tr("wv.aus_cam.eintrag", name=name, anzahl=anzahl)
            )
            aktion.triggered.connect(lambda _an=False, a=adresse: self.aus_cam_uebernehmen(a))
        if self.menue_aus_cam.isEmpty():
            self.menue_aus_cam.addAction(tr("wv.aus_cam.leer")).setEnabled(False)

    def aus_cam_uebernehmen(self, adresse):
        """Übernimmt die Werkzeuge einer FreeCAD-Bibliothek; gespeichert wird mit OK/Übernehmen.

        Gibt den Bericht zurück (oder None); die Rückmeldung zeigt
        `aus_cam_bericht_zeigen`, damit die Szenarien sie ohne Fenster prüfen.
        """
        self._felder_uebernehmen()
        try:
            bericht = aus_cam.uebernehmen(self.bibliothek, adresse)
        except Exception as fehler:  # jeder Fehler von CAM soll als Satz ankommen
            FreeCAD.Console.PrintError(f"CAM-Addon: Aus CAM übernehmen: {fehler}\n")
            QtGui.QMessageBox.warning(self, tr("wv.titel"), tr("wv.aus_cam.fehler", fehler=fehler))
            return None
        self._liste_aufbauen(auswahl=bericht.neu[0] if bericht.neu else self.werkzeug)
        QtCore.QTimer.singleShot(0, lambda: self.aus_cam_bericht_zeigen(bericht))
        return bericht

    def aus_cam_bericht_zeigen(self, bericht):
        QtGui.QMessageBox.information(self, tr("wv.aus_cam"), aus_cam_text(bericht))

    def kiste_zeigen(self):
        """„Werkzeuge der Hersteller …“: die Reihen der Werkzeugkiste zum Anhaken; „Hinzufügen“
        legt sie in die eigene (aus_kiste_hinzufuegen). Gibt das Fenster zurück."""
        dialog = KisteDialog(self)
        self.kiste = dialog
        dialog.accepted.connect(lambda: self.aus_kiste_hinzufuegen(dialog.gewaehlt()))
        dialog.open()
        return dialog

    def aus_kiste_hinzufuegen(self, kennungen):
        """Legt die Reihen `kennungen` der Werkzeugkiste in die eigene; gespeichert wird mit OK
        oder Übernehmen. Gibt den Bericht zurück (werkzeugkiste.Bericht); die Rückmeldung
        zeigt `kiste_bericht_zeigen`."""
        self._felder_uebernehmen()
        bericht = wk.hinzufuegen(self.bibliothek, kennungen)
        self._liste_aufbauen(auswahl=bericht.neu[0] if bericht.neu else self.werkzeug)
        QtCore.QTimer.singleShot(0, lambda: self.kiste_bericht_zeigen(bericht))
        return bericht

    def kiste_bericht_zeigen(self, bericht):
        QtGui.QMessageBox.information(
            self,
            tr("wv.kiste.titel"),
            tr("wv.kiste.bericht", neu=len(bericht.neu), schon=len(bericht.schon_da)),
        )

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


def _tooltip(feld):
    """Der Tooltip eines Maßes."""
    return {
        "durchmesser": tr("wv.durchmesser.tooltip"),
        "schneidenlaenge": tr("wv.schneidenlaenge.tooltip"),
        "gesamtlaenge": tr("wv.gesamtlaenge.tooltip"),
        "schaft": tr("wv.schaft.tooltip"),
        "eckradius": tr("wv.eckradius.tooltip"),
        "spitzen_d": tr("wv.spitzen_d.tooltip"),
        "hals_d": tr("wv.hals_d.tooltip"),
        "hals_laenge": tr("wv.hals_laenge.tooltip"),
        "auskragung": tr("wv.auskragung.tooltip"),
        "profilradius": tr("wv.profilradius.tooltip"),
        "schneidenbreite": tr("wv.schneidenbreite.tooltip"),
        "stechtiefe": tr("wv.stechtiefe.tooltip"),
        "eintauchwinkel": tr("wv.eintauchwinkel.tooltip"),
        "spitzenwinkel": tr("wv.spitzenwinkel.tooltip"),
        "kegelwinkel": tr("wv.kegelwinkel.tooltip"),
        "flankenwinkel": tr("wv.flankenwinkel.tooltip"),
        "einstellwinkel": tr("wv.einstellwinkel.tooltip"),
        "plattenwinkel": tr("wv.plattenwinkel.tooltip"),
        wz.STEIGUNG: tr("wv.steigung.tooltip"),
    }[feld]


def _steigung_einheit():
    """Einheit neben der Steigung: mm, in inch Gänge je Zoll."""
    return tr("wv.einheit.gaenge") if einheiten.in_zoll() else "mm"


def aus_cam_text(bericht):
    """Die Rückmeldung nach „Aus CAM übernehmen“, Absatz für Absatz."""
    absaetze = [tr("wv.aus_cam.bericht.neu", anzahl=len(bericht.neu))]
    if bericht.neue_nummer:
        liste = ", ".join(f"{name}: T{alt} → T{neu}" for name, alt, neu in bericht.neue_nummer)
        absaetze.append(tr("wv.aus_cam.bericht.neue_nummer", liste=liste))
    if bericht.schon_da:
        absaetze.append(tr("wv.aus_cam.bericht.schon_da", namen=", ".join(bericht.schon_da)))
    if bericht.andere_form:
        absaetze.append(tr("wv.aus_cam.bericht.andere_form", namen=", ".join(bericht.andere_form)))
    if bericht.unlesbar:
        absaetze.append(tr("wv.aus_cam.bericht.unlesbar", namen=", ".join(bericht.unlesbar)))
    if bericht.neu:
        absaetze.append(tr("wv.aus_cam.bericht.weiter"))
    return "\n\n".join(absaetze)


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
    if bericht.naeherungen:
        liste = ", ".join(
            tr("wv.cam.naeherung.eintrag", werkzeug=werkzeug, form=form)
            for werkzeug, form in bericht.naeherungen
        )
        absaetze.append(tr("wv.cam.naeherung", liste=liste))
    if bericht.ohne_form:
        absaetze.append(tr("wv.cam.ohne_form", liste=", ".join(bericht.ohne_form)))
    if bericht.entfernt:
        absaetze.append(tr("wv.cam.entfernt", anzahl=bericht.entfernt))
    absaetze.append(tr("wv.cam.weiter"))
    return "\n\n".join(absaetze)


class KisteDialog(QtGui.QDialog):
    """„Werkzeuge der Hersteller“ (W-007): die Werkzeugkiste als Baum – je Werkzeugart eine
    Gruppe, darin die Reihen der Hersteller, darin jede Größe mit eigenem Haken (Manuel,
    2026-10-03: „diese Einteilung … und EINZELNE Bohrer aufnehmen, nicht gleich alle“). Alle
    angehakt; der Tooltip einer Reihe sagt, woher Maße, Nummern und Werte kommen."""

    def __init__(self, eltern=None):
        super().__init__(eltern)
        self.setWindowTitle(tr("wv.kiste.titel"))
        self.resize(720, 600)
        aufbau = QtGui.QVBoxLayout(self)
        erklaerung = QtGui.QLabel(tr("wv.kiste.erklaerung"))
        erklaerung.setWordWrap(True)
        aufbau.addWidget(erklaerung)
        self.baum = QtGui.QTreeWidget()
        self.baum.setHeaderHidden(True)
        self.baum.setIndentation(16)
        self._reihen = []  # die Zeilen der Reihen, in der Reihenfolge der Anzeige
        haken = (
            QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsAutoTristate
        )
        reihen = wk.reihen()
        for art in wz.ARTEN:
            der_art = [r for r in reihen if r.art == art]
            if not der_art:
                continue
            anzahl = sum(r.anzahl for r in der_art)
            gruppe = QtGui.QTreeWidgetItem([f"{wz.art_text(art)} ({anzahl})"])
            gruppe.setIcon(0, art_symbol(art))
            gruppe.setFlags(haken)
            schrift = gruppe.font(0)
            schrift.setBold(True)
            gruppe.setFont(0, schrift)
            self.baum.addTopLevelItem(gruppe)
            for reihe in der_art:
                zeile = QtGui.QTreeWidgetItem(
                    [
                        tr(
                            "wv.kiste.reihe",
                            hersteller=reihe.hersteller or tr("wv.kiste.beispiel"),
                            titel=reihe.titel,
                            anzahl=reihe.anzahl,
                        )
                    ]
                )
                zeile.setData(0, QtCore.Qt.UserRole, reihe.kennung)
                zeile.setToolTip(0, reihe.quelle)
                zeile.setFlags(haken)
                gruppe.addChild(zeile)
                self._reihen.append(zeile)
                for nummer, werkzeug in enumerate(wk.werkzeuge(reihe)):
                    groesse = QtGui.QTreeWidgetItem([dezimal(wz.zeile_ohne_nummer(werkzeug))])
                    groesse.setData(0, QtCore.Qt.UserRole, (reihe.kennung, nummer))
                    groesse.setFlags(haken)
                    groesse.setCheckState(0, QtCore.Qt.Checked)
                    zeile.addChild(groesse)
            gruppe.setExpanded(True)
        aufbau.addWidget(self.baum, 1)
        unten = QtGui.QHBoxLayout()
        self.knopf_alle = knopf(
            tr("wv.kiste.alle"), tr("wv.kiste.alle.tooltip"), lambda: self.alle_setzen(True)
        )
        self.knopf_keine = knopf(
            tr("wv.kiste.keine"), tr("wv.kiste.keine.tooltip"), lambda: self.alle_setzen(False)
        )
        unten.addWidget(self.knopf_alle)
        unten.addWidget(self.knopf_keine)
        unten.addStretch()
        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        self.knopf_hinzufuegen = knoepfe.button(QtGui.QDialogButtonBox.Ok)
        self.knopf_hinzufuegen.setText(tr("wv.kiste.hinzufuegen"))
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        unten.addWidget(knoepfe)
        aufbau.addLayout(unten)

    def reihen_eintraege(self):
        """Die Zeilen der Reihen in der Reihenfolge der Anzeige (für die Szenarien)."""
        return list(self._reihen)

    def alle_setzen(self, an):
        """„Alle anhaken“ / „Alle abhaken“."""
        zustand = QtCore.Qt.Checked if an else QtCore.Qt.Unchecked
        for i in range(self.baum.topLevelItemCount()):
            self.baum.topLevelItem(i).setCheckState(0, zustand)

    def gewaehlt(self):
        """Was angehakt ist: je Reihe ihre Kennung, wenn alle Größen angehakt sind, sonst
        (Kennung, Nummer) je angehakter Größe – so, wie werkzeugkiste.hinzufuegen es nimmt."""
        auswahl = []
        for zeile in self._reihen:
            groessen = [zeile.child(i) for i in range(zeile.childCount())]
            angehakt = [g for g in groessen if g.checkState(0) == QtCore.Qt.Checked]
            if len(angehakt) == len(groessen):
                auswahl.append(zeile.data(0, QtCore.Qt.UserRole))
            else:
                auswahl.extend(g.data(0, QtCore.Qt.UserRole) for g in angehakt)
        return auswahl
