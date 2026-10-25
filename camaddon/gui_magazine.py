# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Fenster „Magazine“ der Werkzeugverwaltung (W-002 Stufe H; Manuel, 2026-10-05: „das Paket
sollte in der Werkzeugverwaltung geschnürt werden“, „man kann beliebig viele Magazine machen“,
„die Maschine muss aber schon bestehen“).

Links die Magazine, je Maschine aufklappbar darunter (Manuel, 2026-10-05: „dass erstmal die
Maschine da steht … mit einem Plus aufklappbar, sozusagen als Kategorie, und man dann die
verschiedenen Magazine zu der Maschine sehen kann“), darunter Neu, Kopieren, Löschen; rechts das
gewählte: Name, Maschine aus dem
Maschinenspeicher, ob es für sie gilt, wie viele Plätze Wechsler bzw. Revolver haben, und je
Werkzeug eine Zeile – T-Nummer, Werkzeug aus der Werkzeugverwaltung, Name an der Steuerung,
beladen auf Platz (leer: nicht beladen). Es ändert die Bibliothek des Werkzeugdialogs; gespeichert
wird mit dessen OK oder Übernehmen. Unten rot, was nicht zusammenpasst (eine Nummer oder ein
Platz zweimal, ein Platz über der Zahl der Plätze).
"""

import math
import os

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import einheiten, farben
from . import halter as hl
from . import maschine as m
from . import maschinenspeicher as msp
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_teile import GRAU, fenster_merken, knopf, ruhiges_mausrad
from .gui_zahlen import groesse_lesen, groesse_zeigen
from .sprache import tr

FENSTER_GROESSE = (1000, 620)
LISTE_BREITE = 260
GROESSTE_NUMMER = 9999
GROESSTE_PLATZ = 999
ROT = farben.ROT
SPALTE_T, SPALTE_WERKZEUG, SPALTE_NAME, SPALTE_PLATZ, SPALTE_HERAUS, SPALTE_HALTER = range(6)
# Die Anteile der Spalten an der Breite der Tabelle am Anfang (sie füllen sie immer ganz, Manuel,
# 2026-10-18: „das komplette fenster ausgefüllt wird wenn wir es von der größe her verziehen aber
# halt auch einzeln“); mit der Maus ziehen, gemerkt in SPALTEN_GEMERKT.
SPALTEN_ANTEILE = (90, 330, 170, 110, 170, 220)
SPALTEN_GEMERKT = "MagazinSpalten3"
SPALTE_MINDESTENS = 40  # Pixel – schmaler wird keine Spalte
ROLLE = (
    QtCore.Qt.UserRole
)  # an einer Zeile des Baums: ("maschine", Datei) oder ("magazin", Kennung)


def werkzeug_text(werkzeug):
    """„Schaftfräser Ø 12 – VHM 12 lang“ – wie die Zeile das Werkzeug zeigt."""
    text = wz.kurz(werkzeug)
    return f"{text} – {werkzeug.name}" if werkzeug.name else text


def ungespeicherte_maschine():
    """Das erste offene Dokument mit einer Maschine, das in keiner Datei liegt (eine Maschine aus
    „Neue Maschine …“) – None ohne."""
    for dokument in FreeCAD.listDocuments().values():
        if dokument.FileName:
            continue
        for objekt in dokument.Objects:
            if objekt.TypeId == "Assembly::AssemblyObject" and m.finde_maschine(objekt) is not None:
                return dokument
    return None


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
    """Sätze, was nicht zusammenpasst: keine Maschine (dann nimmt kein Job die Nummern – legros im
    Forum, 2026-10-10: „you can specify the pocket location, but it doesn't seem to take it into
    account“; seine Beispielmaschine war nicht gespeichert), eine T-Nummer zweimal, ein Platz
    zweimal, ein Platz über der Zahl der Plätze."""
    saetze = []
    if not magazin.maschine and maschinen:
        saetze.append(tr("mg.problem.ohne_maschine"))
    elif not magazin.maschine:
        saetze.append(tr("mg.problem.keine_maschinen"))
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
        self._offen = set()  # die Maschinen (Datei), deren Magazine aufgeklappt sind
        self.setWindowTitle(tr("mg.titel"))
        fenster_merken(self, "Magazine", FENSTER_GROESSE)
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
        unter = QtGui.QHBoxLayout()
        self.probleme = QtGui.QLabel()
        self.probleme.setWordWrap(True)
        self.probleme.setStyleSheet(f"color: {ROT};")
        unter.addWidget(self.probleme, 1)
        # Ohne Maschine der nächste Schritt gleich daneben: die offene Maschine speichern.
        self.knopf_maschine_speichern = QtGui.QPushButton()
        self.knopf_maschine_speichern.setToolTip(tr("mg.maschine_speichern.tooltip"))
        self.knopf_maschine_speichern.clicked.connect(lambda: self.maschine_speichern())
        self.knopf_maschine_speichern.hide()
        unter.addWidget(self.knopf_maschine_speichern, 0, QtCore.Qt.AlignTop)
        aufbau.addLayout(unter)
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
        self.liste = QtGui.QTreeWidget()
        self.liste.setHeaderHidden(True)
        self.liste.setRootIsDecorated(True)
        self.liste.currentItemChanged.connect(self._zeile_gewaehlt)
        self.liste.itemExpanded.connect(lambda z: self._offen.add(z.data(0, ROLLE)[1]))
        self.liste.itemCollapsed.connect(lambda z: self._offen.discard(z.data(0, ROLLE)[1]))
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
        self.tabelle = QtGui.QTableWidget(0, 6)
        self.tabelle.setHorizontalHeaderLabels(
            [
                tr("mg.spalte.t"),
                tr("mg.spalte.werkzeug"),
                tr("mg.spalte.name"),
                tr("mg.spalte.platz"),
                tr("mg.spalte.heraus"),
                tr("mg.spalte.halter"),
            ]
        )
        # Jede Spalte mit der Maus breiter oder schmaler (Manuel, 2026-10-18: „warum kann ich die
        # spalte Werkzeug oder generell eine spalte dort nicht in der länge … ziehen“), und
        # zusammen füllen sie die Tabelle immer ganz: Wird das Fenster verzogen, wachsen alle im
        # Verhältnis; zieht man einen Trennstrich, gibt die Spalte rechts davon ab (_Spalten).
        self.spalten = _Spalten(self.tabelle)
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

    def _maschinenname(self, datei):
        eintrag = msp.finde(self.maschinen, datei) if datei else None
        if eintrag is not None:
            return eintrag.name
        if datei:  # nicht (mehr) im Maschinenspeicher: der Dateiname
            import os

            return os.path.splitext(os.path.basename(datei))[0]
        return tr("mg.ohne_maschine")

    def _titel(self, magazin):
        """Die Zeile eines Magazins unter seiner Maschine: sein Name, ✓ wenn es für sie gilt."""
        gilt = "" if not magazin.maschine or not magazin.gilt else " ✓"
        return f"{magazin.name or tr('mg.ohne_name')}{gilt}"

    def _gruppen(self):
        """[(Datei, [Magazin])] – je Maschine ihre Magazine, in der Reihenfolge des
        Maschinenspeichers; Maschinen, die es dort nicht gibt, danach; ohne Maschine zuletzt."""
        reihe = [m.datei for m in self.maschinen]
        dateien = []
        for magazin in self.bibliothek.magazine:
            datei = magazin.maschine or ""
            gleich = next((d for d in dateien if msp.gleiche_datei(d, datei)), None)
            if gleich is None and datei not in dateien:
                dateien.append(datei)

        def rang(datei):
            if not datei:
                return (2, 0)
            k = next((i for i, r in enumerate(reihe) if msp.gleiche_datei(r, datei)), None)
            return (0, k) if k is not None else (1, 0)

        dateien.sort(key=rang)
        return [
            (
                datei,
                [
                    m
                    for m in self.bibliothek.magazine
                    if (m.maschine or "") == datei
                    or (datei and m.maschine and msp.gleiche_datei(m.maschine, datei))
                ],
            )
            for datei in dateien
        ]

    def _liste_fuellen(self, auswahl=None):
        """Der Baum: je Maschine eine Zeile (fett, mit der Zahl ihrer Magazine), aufklappbar,
        darunter ihre Magazine. Aufgeklappt bleibt, was aufgeklappt war, und die Maschine des
        gewählten Magazins."""
        self._fuellt = True
        gewaehlt = None
        try:
            self.liste.clear()
            for datei, magazine in self._gruppen():
                oben = QtGui.QTreeWidgetItem([f"{self._maschinenname(datei)} ({len(magazine)})"])
                oben.setData(0, ROLLE, ("maschine", datei))
                schrift = oben.font(0)
                schrift.setBold(True)
                oben.setFont(0, schrift)
                oben.setToolTip(0, datei or tr("mg.ohne_maschine"))
                self.liste.addTopLevelItem(oben)
                for magazin in magazine:
                    zeile = QtGui.QTreeWidgetItem([self._titel(magazin)])
                    zeile.setData(0, ROLLE, ("magazin", magazin.kennung))
                    oben.addChild(zeile)
                    if magazin is auswahl:
                        gewaehlt = zeile
                        self._offen.add(datei)
                oben.setExpanded(datei in self._offen)
            if gewaehlt is not None:
                self.liste.setCurrentItem(gewaehlt)
        finally:
            self._fuellt = False
        self._zeile_gewaehlt(self.liste.currentItem())

    def _zeile_gewaehlt(self, zeile, _vorher=None):
        if self._fuellt:
            return
        art, wert = zeile.data(0, ROLLE) if zeile is not None else ("", "")
        self.magazin = (
            next((m for m in self.bibliothek.magazine if m.kennung == wert), None)
            if art == "magazin"
            else None
        )
        self.rechts.setEnabled(self.magazin is not None)
        self.knopf_kopieren.setEnabled(self.magazin is not None)
        self.knopf_loeschen.setEnabled(self.magazin is not None)
        self._magazin_zeigen()

    def gewaehlte_maschine(self):
        """Die Maschine (Datei) der gewählten Zeile – der Maschine selbst oder ihres Magazins;
        None ohne Wahl."""
        zeile = self.liste.currentItem()
        if zeile is None:
            return None
        if zeile.parent() is not None:
            zeile = zeile.parent()
        return zeile.data(0, ROLLE)[1]

    def magazin_anlegen(self):
        """„Neu“: ein Magazin – ist eine Maschine gewählt (ihre Zeile im Baum), für sie; sonst
        für die erste Maschine, für die noch keins gilt."""
        zeile = self.liste.currentItem()
        datei = None
        if zeile is not None and zeile.parent() is None:
            datei = zeile.data(0, ROLLE)[1]
        if datei:
            name = self._maschinenname(datei)
        else:
            frei = next(
                (m for m in self.maschinen if self.bibliothek.magazin_fuer(m.datei) is None),
                None,
            )
            datei = frei.datei if frei is not None else ""
            name = frei.name if frei is not None else tr("mg.neu.name")
        vorhanden = {m.name for m in self.bibliothek.magazine}
        if name in vorhanden:  # ein zweites für dieselbe Maschine: „… 2“
            k = 2
            while f"{name} {k}" in vorhanden:
                k += 1
            name = f"{name} {k}"
        magazin = self.bibliothek.neues_magazin(name, datei)
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
            # So weit schaut es an diesem Platz heraus (Manuel, 2026-10-18: „im magazin extra
            # dafür ein wert“); leer: der Standard aus der Werkzeugliste, grau.
            werkzeug = self.bibliothek.werkzeug_mit_kennung(eintrag.werkzeug)
            heraus = QtGui.QLineEdit(
                groesse_zeigen(eintrag.heraus, einheiten.LAENGE) if eintrag.heraus > 0 else ""
            )
            heraus.setPlaceholderText(self._heraus_standard(werkzeug))
            heraus.setToolTip(tr("mg.heraus.tooltip"))
            heraus.textEdited.connect(lambda text, e=eintrag: self._heraus_gesetzt(e, text))
            self.tabelle.setCellWidget(zeile, SPALTE_HERAUS, heraus)
            # Der Halter an dieser Maschine (W-024): leer heißt der des Werkzeugs.
            halter = QtGui.QComboBox()
            halter.setToolTip(tr("mg.halter.tooltip"))
            werkzeug = self.bibliothek.werkzeug_mit_kennung(eintrag.werkzeug)
            eigener = self.bibliothek.halter_von(werkzeug) if werkzeug is not None else None
            halter.addItem(
                tr("mg.halter.wie_werkzeug", halter=hl.text(eigener) if eigener else "–"), ""
            )
            for h in self.bibliothek.sortierte_halter():
                halter.addItem(hl.text(h), h.kennung)
            index = halter.findData(eintrag.halter) if eintrag.halter else 0
            halter.setCurrentIndex(max(index, 0))
            halter.currentIndexChanged.connect(
                lambda _i, e=eintrag, w=halter: self._setze(e, "halter", w.currentData() or "")
            )
            self.tabelle.setCellWidget(zeile, SPALTE_HALTER, halter)

    def _heraus_standard(self, werkzeug):
        """Grau im leeren Feld „Schaut heraus“: der Wert aus der Werkzeugliste – eingetragen,
        oder aus der Länge ab Spindelnase und dem Halter; sonst „wie in der Werkzeugliste“."""
        wert = 0.0
        if werkzeug is not None:
            halter = self.bibliothek.halter_von(werkzeug)
            if werkzeug.ausspannlaenge:
                wert = werkzeug.ausspannlaenge
            elif werkzeug.laenge_spindelnase and halter is not None:
                wert = max(werkzeug.laenge_spindelnase - halter.laenge, 0.0)
        if wert > 0:
            return tr("mg.heraus.platzhalter", wert=groesse_zeigen(wert, einheiten.LAENGE))
        return tr("mg.heraus.wie_liste")

    def _heraus_gesetzt(self, eintrag, text):
        """„Schaut heraus“ geändert: der Wert des Platzes (leer: 0 – wie in der Werkzeugliste)."""
        if self._fuellt:
            return
        try:
            wert = groesse_lesen(text, einheiten.LAENGE) if text.strip() else 0.0
        except ValueError:
            return  # noch nicht fertig getippt
        self._setze(eintrag, "heraus", max(float(wert), 0.0))

    def _setze(self, eintrag, feld, wert):
        if self._fuellt:
            return
        setattr(eintrag, feld, wert)
        self._probleme_zeigen()

    def _probleme_zeigen(self):
        saetze = probleme(self.magazin, self.maschinen) if self.magazin else []
        self.probleme.setText("\n".join(saetze))
        offen = (
            ungespeicherte_maschine()
            if self.magazin is not None and not self.magazin.maschine
            else None
        )
        if offen is not None:
            self.knopf_maschine_speichern.setText(
                tr("mg.maschine_speichern", name=offen.Label or offen.Name)
            )
        self.knopf_maschine_speichern.setVisible(offen is not None)

    def maschine_speichern(self, pfad=None):
        """„Maschine … speichern …“: die offene, ungespeicherte Maschine in eine Datei (ohne
        `pfad` fragt ein Dateifenster), in den Maschinen-Speicher, und das gewählte Magazin gilt
        für sie. Gibt den Pfad zurück oder None."""
        dokument = ungespeicherte_maschine()
        if dokument is None or self.magazin is None:
            return None
        if pfad is None:
            vorschlag = os.path.join(
                os.path.expanduser("~"), f"{dokument.Label or dokument.Name}.FCStd"
            )
            pfad, _filter = QtGui.QFileDialog.getSaveFileName(
                self, tr("mg.maschine_speichern.titel"), vorschlag, "*.FCStd"
            )
            if not pfad:
                return None
        if not pfad.lower().endswith(".fcstd"):
            pfad += ".FCStd"
        dokument.saveAs(pfad)
        eintraege = msp.merken_dokument(dokument)
        self.maschinen = msp.laden()
        if eintraege:
            self.magazin.maschine = eintraege[0].datei
            if self.bibliothek.magazin_fuer(self.magazin.maschine) in (None, self.magazin):
                self.bibliothek.magazin_gilt(self.magazin)
        self._liste_fuellen(self.magazin)
        return pfad

    def _name_geaendert(self, text):
        if self.magazin is not None and not self._fuellt:
            self.magazin.name = text.strip()
            self._titel_auffrischen()

    def _titel_auffrischen(self):
        zeile = self.liste.currentItem()
        if self.magazin is not None and zeile is not None and zeile.parent() is not None:
            zeile.setText(0, self._titel(self.magazin))

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


class _Spalten(QtCore.QObject):
    """Die Spalten einer Tabelle füllen ihre Breite immer ganz und lassen sich einzeln ziehen:
    Beim Verziehen des Fensters wachsen und schrumpfen alle im Verhältnis (die Anteile), beim
    Ziehen eines Trennstrichs gibt die Spalte rechts davon ab oder bekommt dazu – keine wird
    schmaler als SPALTE_MINDESTENS. Die Anteile merkt sich das Fenster (SPALTEN_GEMERKT)."""

    def __init__(self, tabelle):
        super().__init__(tabelle)
        self.tabelle = tabelle
        self._setzt = False
        self.anteile = self._gemerkt() or self._normiert(SPALTEN_ANTEILE)
        kopf = tabelle.horizontalHeader()
        kopf.setSectionResizeMode(QtGui.QHeaderView.Interactive)
        kopf.setMinimumSectionSize(SPALTE_MINDESTENS)
        kopf.setStretchLastSection(True)  # die letzte füllt, was die anderen lassen
        tabelle.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        kopf.sectionResized.connect(self._gezogen)
        tabelle.viewport().installEventFilter(self)
        self.anpassen()

    def eventFilter(self, objekt, ereignis):
        if ereignis.type() == QtCore.QEvent.Resize:
            self.anpassen()
        return False

    def _normiert(self, werte):
        summe = float(sum(werte)) or 1.0
        return [float(w) / summe for w in werte]

    def _gemerkt(self):
        from . import PARAMETER_PFAD

        text = FreeCAD.ParamGet(PARAMETER_PFAD).GetString(SPALTEN_GEMERKT, "")
        try:
            werte = [float(t) for t in text.split(",") if t.strip()]
        except ValueError:
            return None
        if len(werte) != self.tabelle.columnCount() or min(werte) <= 0:
            return None
        return self._normiert(werte)

    def _merken(self):
        from . import PARAMETER_PFAD

        text = ",".join(f"{a:.4f}" for a in self.anteile)
        FreeCAD.ParamGet(PARAMETER_PFAD).SetString(SPALTEN_GEMERKT, text)

    def anpassen(self):
        """Die Breiten aus den Anteilen – zusammen genau die Breite der Tabelle."""
        breite = self.tabelle.viewport().width()
        n = self.tabelle.columnCount()
        if breite <= 0 or n == 0:
            return
        breiten = [max(int(round(a * breite)), SPALTE_MINDESTENS) for a in self.anteile[: n - 1]]
        self._setzt = True
        try:
            for spalte, b in enumerate(breiten):  # die letzte streckt Qt auf den Rest
                if self.tabelle.columnWidth(spalte) != b:
                    self.tabelle.setColumnWidth(spalte, b)
        finally:
            self._setzt = False

    def _gezogen(self, spalte, alt, neu):
        """Ein Trennstrich wurde gezogen: Die letzte Spalte gleicht es aus (sie streckt Qt) –
        reicht sie nicht, geben die Spalten rechts vom Strich ab, zuletzt die gezogene selbst,
        damit die Tabelle nie breiter wird als ihr Fenster. Die neuen Anteile merken."""
        if self._setzt:
            return
        n = self.tabelle.columnCount()
        kopf = self.tabelle.horizontalHeader()
        ueber = kopf.length() - self.tabelle.viewport().width()
        if spalte < n - 1 and ueber > 0:
            rechts = list(range(spalte + 1, n - 1))
            breiten = [self.tabelle.columnWidth(s) for s in rechts]
            spiel = [max(b - SPALTE_MINDESTENS, 0) for b in breiten]
            nehmen = min(ueber, sum(spiel))
            self._setzt = True
            try:
                if nehmen > 0:
                    for s, b, sp in zip(rechts, breiten, spiel, strict=True):
                        self.tabelle.setColumnWidth(s, b - math.ceil(nehmen * sp / sum(spiel)))
                rest = kopf.length() - self.tabelle.viewport().width()
                if rest > 0:
                    self.tabelle.setColumnWidth(
                        spalte, max(self.tabelle.columnWidth(spalte) - rest, SPALTE_MINDESTENS)
                    )
            finally:
                self._setzt = False
        breite = self.tabelle.viewport().width()
        if breite > 0:
            self.anteile = self._normiert([self.tabelle.columnWidth(s) for s in range(n)])
            self._merken()


def oeffnen(werkzeugdialog):
    """Öffnet „Magazine“ zur Bibliothek des Werkzeugdialogs; gibt das Fenster zurück."""
    dialog = MagazinDialog(werkzeugdialog, werkzeugdialog.bibliothek)
    dialog.open()
    return dialog
