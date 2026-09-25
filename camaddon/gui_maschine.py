# SPDX-License-Identifier: LGPL-2.1-or-later
"""Dialog „Maschine bearbeiten“ (Spezifikation W-001, Abschnitt 11).

Ein Aufgabenfenster links, damit die 3D-Ansicht sichtbar bleibt. Der ganze
Dialog ist eine Transaktion: OK übernimmt alles als einen Schritt
Rückgängig, Abbrechen verwirft alles.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import gui_zeigen, hilfe
from . import kette as kette_modul
from . import maschine as m
from .gui_start import symbol
from .kette import HINWEIS, LINEAR
from .sprache import tr

ROLLE = QtCore.Qt.UserRole

# Welche Kennwerte eine Einheit neben dem Feld brauchen (bei den anderen
# steht sie schon im Namen) – abhängig davon, ob die Achse fährt oder dreht.
EINHEIT_LINEAR = {"Beschleunigung": "m/s²", "Ruck": "m/s³"}
EINHEIT_DREH = {"Beschleunigung": "U/s²", "Ruck": "U/s³"}


# --- Maschine finden ------------------------------------------------------


def _assemblies(doc):
    return [o for o in doc.Objects if o.TypeId == "Assembly::AssemblyObject"]


def _gewaehlte_assembly(doc):
    """Assembly aus Auswahl, aktiver Assembly oder der einzigen im Dokument."""
    for objekt in FreeCADGui.Selection.getSelection(doc.Name):
        kandidaten = [objekt] + objekt.InListRecursive
        for kandidat in kandidaten:
            if kandidat.TypeId == "Assembly::AssemblyObject":
                return kandidat
    try:
        import UtilsAssembly

        aktiv = UtilsAssembly.activeAssembly()
        if aktiv is not None:
            return aktiv
    except ImportError:
        pass
    alle = _assemblies(doc)
    if len(alle) == 1:
        return alle[0]
    if len(alle) > 1:
        namen = [a.Label for a in alle]
        name, ok = QtGui.QInputDialog.getItem(
            FreeCADGui.getMainWindow(),
            tr("dialog.titel"),
            tr("dialog.welche_baugruppe"),
            namen,
            0,
            False,
        )
        if ok:
            return alle[namen.index(name)]
    return None


class BefehlMaschineBearbeiten:
    def GetResources(self):
        return {
            "Pixmap": symbol("maschine.svg"),
            "MenuText": tr("befehl.maschine.titel"),
            "ToolTip": tr("befehl.maschine.tooltip"),
        }

    def IsActive(self):
        # Immer bedienbar: Fehlt die Baugruppe, erklärt der Befehl, was zu tun
        # ist – ein ausgegrauter Knopf erklärt nichts.
        return FreeCADGui.Control.activeDialog() is False

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        assembly = _gewaehlte_assembly(doc) if doc else None
        if assembly is None:
            QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(), tr("dialog.titel"), tr("dialog.keine_baugruppe")
            )
            return
        doc.openTransaction(tr("dialog.titel"))
        maschine = m.lege_maschine_an(assembly)
        FreeCADGui.Control.showDialog(MaschinenPanel(assembly, maschine))


# --- Hilfen für den Aufbau ------------------------------------------------


def _kopfzeile(titel, thema=None):
    """Überschrift eines Bereichs, rechts der Hilfe-Knopf (?) zum Thema."""
    zeile = QtGui.QWidget()
    aufbau = QtGui.QHBoxLayout(zeile)
    aufbau.setContentsMargins(0, 0, 0, 0)
    aufbau.addWidget(QtGui.QLabel(f"<b>{titel}</b>"))
    aufbau.addStretch()
    if thema:
        knopf = QtGui.QToolButton()
        knopf.setText("?")
        knopf.setToolTip(tr("hilfe.knopf.tooltip"))
        knopf.setObjectName("hilfe_" + thema)
        knopf.clicked.connect(lambda: zeige_hilfe(zeile, thema))
        aufbau.addWidget(knopf)
    return zeile


class HilfeFenster(QtGui.QDialog):
    """Ausführliche Hilfe; Verweise zwischen den Seiten funktionieren."""

    offen = None

    def __init__(self, eltern, thema):
        super().__init__(eltern)
        HilfeFenster.offen = self
        self.setWindowTitle(tr("hilfe.titel"))
        self.resize(560, 520)
        self.browser = QtGui.QTextBrowser()
        self.browser.setSearchPaths([hilfe.hilfe_ordner()])
        self.browser.setOpenExternalLinks(True)
        pfad = hilfe.hilfe_datei(thema)
        if pfad:
            self.browser.setSource(QtCore.QUrl.fromLocalFile(pfad))
        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Close)
        knoepfe.rejected.connect(self.close)
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(self.browser)
        aufbau.addWidget(knoepfe)


def zeige_hilfe(eltern, thema):
    # Nicht modal: Man soll lesen und gleichzeitig im Dialog weiterarbeiten können.
    fenster = HilfeFenster(eltern, thema)
    fenster.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    fenster.show()


def _zahl_lesen(text):
    """Liest eine Zahl, Komma oder Punkt; leer = 0 (unbekannt)."""
    text = text.strip().replace(",", ".")
    if not text:
        return 0.0
    return float(text)


def _zahl_zeigen(wert):
    if not wert:
        return ""
    return QtCore.QLocale().toString(float(wert), "g", 12)


def _symbol_status(ok):
    stil = QtGui.QApplication.style()
    return stil.standardIcon(
        QtGui.QStyle.SP_DialogApplyButton if ok else QtGui.QStyle.SP_MessageBoxWarning
    )


# --- Aufgabenfenster -------------------------------------------------------


class MaschinenPanel:
    # Das gerade offene Fenster – für die Oberflächen-Szenarien.
    offen = None

    def __init__(self, assembly, maschine):
        MaschinenPanel.offen = self
        self.geschlossen = False
        self.assembly = assembly
        self.maschine = maschine
        self.doc = assembly.Document
        self.kette = kette_modul.lies_kette(assembly)
        self.wackeln = None
        self._zeige_ziel = None
        self._zeige_uhr = QtCore.QTimer()
        self._zeige_uhr.setSingleShot(True)
        # Erst zeigen, wenn die Maus kurz auf einer Zeile verweilt – nicht bei
        # jedem Überstreichen.
        self._zeige_uhr.setInterval(250)
        self._zeige_uhr.timeout.connect(lambda: self._zeige(self._zeige_ziel))
        self.form = self._baue()
        self._fuelle_alles()
        # Gleich ein Gelenk gewählt, damit „+ Betriebsart“ sofort bedienbar ist.
        if self.achsen.topLevelItemCount():
            self.achsen.setCurrentItem(self.achsen.topLevelItem(0))

    # FreeCAD-Schnittstelle des Aufgabenfensters
    def getStandardButtons(self):
        return QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel

    def accept(self):
        self.geschlossen = True
        self._zeigen_beenden()
        self.doc.commitTransaction()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    def reject(self):
        self.geschlossen = True
        self._zeigen_beenden()
        self.doc.abortTransaction()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    # Aufbau
    def _baue(self):
        form = QtGui.QWidget()
        form.setWindowTitle(tr("dialog.titel"))
        form.setWindowIcon(QtGui.QIcon(symbol("maschine.svg")))
        aufbau = QtGui.QVBoxLayout(form)

        name_zeile = QtGui.QHBoxLayout()
        name_zeile.addWidget(QtGui.QLabel(tr("dialog.name")))
        self.name = QtGui.QLineEdit(self.maschine.Label)
        self.name.setToolTip(tr("dialog.name.tooltip"))
        self.name.editingFinished.connect(self._name_geaendert)
        name_zeile.addWidget(self.name)
        aufbau.addLayout(name_zeile)

        # Achsen
        aufbau.addWidget(_kopfzeile(tr("dialog.achsen"), "achsen"))
        self.achsen = QtGui.QTreeWidget()
        self.achsen.setHeaderHidden(True)
        self.achsen.setToolTip(tr("dialog.achsen.tooltip"))
        self.achsen.setMouseTracking(True)
        self.achsen.itemEntered.connect(lambda eintrag, _s: self._zeige_spaeter(eintrag.data(0, ROLLE)))
        self.achsen.currentItemChanged.connect(self._achse_gewaehlt)
        self.achsen.setMinimumHeight(160)
        aufbau.addWidget(self.achsen)
        self.achsen_knoepfe = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(self.achsen_knoepfe)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        self.knopf_betriebsart = QtGui.QPushButton(tr("dialog.betriebsart_neu"))
        self.knopf_betriebsart.setToolTip(tr("dialog.betriebsart_neu.tooltip"))
        self.knopf_betriebsart.clicked.connect(self._betriebsart_menue)
        self.knopf_ba_weg = QtGui.QPushButton(tr("dialog.entfernen"))
        self.knopf_ba_weg.clicked.connect(self._betriebsart_entfernen)
        knoepfe.addWidget(self.knopf_betriebsart)
        knoepfe.addWidget(self.knopf_ba_weg)
        aufbau.addWidget(self.achsen_knoepfe)

        # Details der gewählten Betriebsart oder Aufnahme – der Kasten wandert
        # jeweils unter die Liste, in der gerade etwas gewählt ist.
        self.detail_kasten = QtGui.QFrame()
        self.detail_kasten.setFrameShape(QtGui.QFrame.StyledPanel)
        kasten = QtGui.QVBoxLayout(self.detail_kasten)
        self.detail_titel = QtGui.QLabel()
        self.detail_titel.setWordWrap(True)
        kasten.addWidget(self.detail_titel)
        self.detail = QtGui.QWidget()
        self.detail_aufbau = QtGui.QFormLayout(self.detail)
        self.detail_aufbau.setContentsMargins(0, 0, 0, 0)
        kasten.addWidget(self.detail)
        self.detail_kasten.hide()
        aufbau.addWidget(self.detail_kasten)
        self._aufbau = aufbau

        # Aufnahmen
        aufbau.addWidget(_kopfzeile(tr("dialog.aufnahmen"), "aufnahmen"))
        self.aufnahmen = QtGui.QTreeWidget()
        self.aufnahmen.setHeaderHidden(True)
        self.aufnahmen.setToolTip(tr("dialog.aufnahmen.tooltip"))
        self.aufnahmen.setMouseTracking(True)
        self.aufnahmen.itemEntered.connect(lambda eintrag, _s: self._zeige_spaeter(eintrag.data(0, ROLLE)))
        self.aufnahmen.currentItemChanged.connect(self._aufnahme_gewaehlt)
        self.aufnahmen.setMinimumHeight(110)
        aufbau.addWidget(self.aufnahmen)
        self.aufnahmen_knoepfe = QtGui.QWidget()
        knoepfe = QtGui.QGridLayout(self.aufnahmen_knoepfe)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        self.knopf_werkzeug = QtGui.QPushButton(tr("dialog.werkzeugaufnahme_neu"))
        self.knopf_werkzeug.clicked.connect(lambda: self._aufnahme_neu(m.AUFNAHME_WERKZEUG))
        self.knopf_werkstueck = QtGui.QPushButton(tr("dialog.werkstueckaufnahme_neu"))
        self.knopf_werkstueck.clicked.connect(lambda: self._aufnahme_neu(m.AUFNAHME_WERKSTUECK))
        self.knopf_verteilen = QtGui.QPushButton(tr("dialog.plaetze_verteilen"))
        self.knopf_verteilen.setToolTip(tr("dialog.plaetze_verteilen.tooltip"))
        self.knopf_verteilen.clicked.connect(self._plaetze_verteilen)
        self.knopf_auf_weg = QtGui.QPushButton(tr("dialog.entfernen"))
        self.knopf_auf_weg.clicked.connect(self._aufnahme_entfernen)
        knoepfe.addWidget(self.knopf_werkzeug, 0, 0)
        knoepfe.addWidget(self.knopf_werkstueck, 0, 1)
        knoepfe.addWidget(self.knopf_verteilen, 1, 0)
        knoepfe.addWidget(self.knopf_auf_weg, 1, 1)
        aufbau.addWidget(self.aufnahmen_knoepfe)

        # Glieder
        aufbau.addWidget(_kopfzeile(tr("dialog.glieder"), "glieder"))
        self.glieder = QtGui.QListWidget()
        self.glieder.setToolTip(tr("dialog.glieder.tooltip"))
        self.glieder.setMouseTracking(True)
        self.glieder.itemEntered.connect(lambda eintrag: self._zeige_spaeter(eintrag.data(ROLLE)))
        self.glieder.setWordWrap(True)
        aufbau.addWidget(self.glieder)

        # Hinweise
        aufbau.addWidget(_kopfzeile(tr("dialog.hinweise")))
        self.hinweise = QtGui.QListWidget()
        self.hinweise.setWordWrap(True)
        self.hinweise.itemClicked.connect(self._hinweis_geklickt)
        aufbau.addWidget(self.hinweise)
        return form

    # Füllen
    def _fuelle_alles(self, auswahl=None):
        self._detail_leeren()
        self._fuelle_achsen(auswahl)
        self._fuelle_aufnahmen(auswahl)
        self._fuelle_glieder()
        self._pruefen()
        self._knoepfe_schalten()

    def _fuelle_achsen(self, auswahl=None):
        self.achsen.blockSignals(True)
        self.achsen.clear()
        je_gelenk = {}
        for ba in m.betriebsarten(self.maschine):
            je_gelenk.setdefault(ba.Gelenk, []).append(ba)
        wahl_item = None
        for gelenk in self.kette.gelenke:
            zeichen = "↔" if gelenk.art == LINEAR else "⟳"
            art = tr("gelenk.schiebe") if gelenk.art == LINEAR else tr("gelenk.dreh")
            eintrag = QtGui.QTreeWidgetItem([f"{zeichen}  {gelenk.objekt.Label}   ({art})"])
            eintrag.setData(0, ROLLE, ("gelenk", gelenk.objekt))
            self.achsen.addTopLevelItem(eintrag)
            liste = je_gelenk.pop(gelenk.objekt, [])
            if not liste:
                leer = QtGui.QTreeWidgetItem([tr("dialog.noch_keine_betriebsart")])
                leer.setToolTip(0, tr("dialog.noch_keine_betriebsart.tooltip"))
                leer.setForeground(0, QtGui.QBrush(QtGui.QColor("gray")))
                leer.setFlags(QtCore.Qt.NoItemFlags)
                eintrag.addChild(leer)
            for ba in liste:
                kind = self._betriebsart_eintrag(ba)
                eintrag.addChild(kind)
                if ba == auswahl:
                    wahl_item = kind
            eintrag.setExpanded(True)
        # Betriebsarten, deren Gelenk fehlt oder keine Achse ist.
        for liste in je_gelenk.values():
            for ba in liste:
                kind = self._betriebsart_eintrag(ba)
                self.achsen.addTopLevelItem(kind)
                if ba == auswahl:
                    wahl_item = kind
        self.achsen.blockSignals(False)
        if wahl_item is not None:
            self.achsen.setCurrentItem(wahl_item)

    def _betriebsart_eintrag(self, ba):
        eintrag = QtGui.QTreeWidgetItem([self._text_betriebsart(ba)])
        eintrag.setData(0, ROLLE, ("ba", ba))
        return eintrag

    @staticmethod
    def _text_betriebsart(ba):
        return f"{m.name_von(ba)}  ·  {m.art_text(ba.Art)}"

    @staticmethod
    def _text_aufnahme(auf):
        art = tr("aufnahme.werkzeug") if auf.Art == m.AUFNAHME_WERKZEUG else tr("aufnahme.werkstueck")
        lcs = auf.Lcs.Label if auf.Lcs is not None else "?"
        teile = [m.name_von(auf), art, "→ " + lcs]
        if auf.Spindel is not None:
            teile.append(tr("aufnahme.angetrieben_von", spindel=m.name_von(auf.Spindel)))
        return "  ·  ".join(teile)

    def _fuelle_aufnahmen(self, auswahl=None):
        self.aufnahmen.blockSignals(True)
        self.aufnahmen.clear()
        wahl_item = None
        # Revolverplätze stehen gesammelt unter ihrem Revolver (zugeklappt),
        # sonst wird die Liste bei 12 Plätzen unübersichtlich.
        gruppe_von = {}
        for ba in m.betriebsarten(self.maschine):
            if ba.Art == m.ART_REVOLVER:
                liste = m.plaetze(self.maschine, self.kette, ba)
                if liste:
                    kopf = QtGui.QTreeWidgetItem(
                        [tr("dialog.revolver_gruppe", name=m.name_von(ba), anzahl=len(liste))]
                    )
                    kopf.setData(0, ROLLE, ("revolver", ba))
                    self.aufnahmen.addTopLevelItem(kopf)
                    for auf in liste:
                        gruppe_von[auf] = kopf
        for auf in sorted(m.aufnahmen(self.maschine), key=lambda a: (a.Art, a.Platz, a.Label)):
            eintrag = QtGui.QTreeWidgetItem([self._text_aufnahme(auf)])
            eintrag.setData(0, ROLLE, ("auf", auf))
            if auf in gruppe_von:
                gruppe_von[auf].addChild(eintrag)
            else:
                self.aufnahmen.addTopLevelItem(eintrag)
            if auf == auswahl:
                wahl_item = eintrag
        self.aufnahmen.blockSignals(False)
        if wahl_item is not None:
            if wahl_item.parent() is not None:
                wahl_item.parent().setExpanded(True)
            self.aufnahmen.setCurrentItem(wahl_item)

    # Zeigen in der 3D-Ansicht
    def _zeige_spaeter(self, daten):
        self._zeige_ziel = daten
        self._zeige_uhr.start()

    def _zeige(self, daten):
        """Hebt hervor, worum es in der Zeile geht; ein Gelenk wackelt kurz."""
        if self.geschlossen or not daten:
            return
        art, objekt = daten
        gelenk = None
        if art == "gelenk":
            gelenk = objekt
        elif art == "ba":
            gelenk = objekt.Gelenk
        if gelenk is not None:
            achse = next((g for g in self.kette.gelenke if g.objekt == gelenk), None)
            if achse is None:
                return
            gui_zeigen.hervorheben(gui_zeigen.koerper_hinter(self.kette, achse))
            # Läuft schon eine Bewegung für dieses Gelenk, nicht neu anfangen.
            if self.wackeln and self.wackeln.laeuft() and self.wackeln.gelenk is achse:
                return
            if self.wackeln:
                self.wackeln.stopp()
            self.wackeln = gui_zeigen.Wackeln(self.assembly, self.kette, achse)
            self.wackeln.start()
        elif art == "glied":
            gui_zeigen.hervorheben(objekt.koerper)
        elif art == "auf":
            gui_zeigen.hervorheben([objekt.Lcs])
        elif art == "revolver":
            gui_zeigen.hervorheben([a.Lcs for a in m.plaetze(self.maschine, self.kette, objekt)])

    def _zeigen_beenden(self):
        """Vor dem Schließen: Bewegung anhalten, alles zurück, Markierung weg."""
        self._zeige_uhr.stop()
        if self.wackeln:
            self.wackeln.stopp()
        FreeCADGui.Selection.clearSelection()

    def _fuelle_glieder(self):
        self.glieder.clear()
        nummer = 1
        for glied in self.kette.glieder:
            if glied.fest:
                titel = tr("dialog.glied_bett")
            else:
                nummer += 1
                titel = tr("dialog.glied_nummer", nummer=nummer)
            eintrag = QtGui.QListWidgetItem(f"{titel}: {glied.namen()}")
            eintrag.setData(ROLLE, ("glied", glied))
            self.glieder.addItem(eintrag)

    def _pruefen(self):
        meldungen = list(self.kette.meldungen) + m.pruefe(self.maschine, self.kette)
        self.meldungen = meldungen
        self.hinweise.clear()
        if not meldungen:
            eintrag = QtGui.QListWidgetItem(_symbol_status(True), tr("dialog.alles_gut"))
            self.hinweise.addItem(eintrag)
        stil = QtGui.QApplication.style()
        for meldung in meldungen:
            icon = stil.standardIcon(
                QtGui.QStyle.SP_MessageBoxInformation
                if meldung.schwere == HINWEIS
                else QtGui.QStyle.SP_MessageBoxWarning
            )
            eintrag = QtGui.QListWidgetItem(icon, meldung.text)
            eintrag.setToolTip(meldung.text)
            eintrag.setData(ROLLE, meldung.bezug)
            self.hinweise.addItem(eintrag)
        # Status-Symbol je Betriebsart: Warnung, wenn sich eine Meldung auf sie bezieht.
        betroffen = {x.bezug for x in meldungen if x.bezug is not None}
        for baum in (self.achsen, self.aufnahmen):
            it = QtGui.QTreeWidgetItemIterator(baum)
            while it.value():
                art, objekt = it.value().data(0, ROLLE) or (None, None)
                if art in ("ba", "auf"):
                    it.value().setIcon(0, _symbol_status(objekt not in betroffen))
                it += 1

    def _knoepfe_schalten(self):
        eintrag = self.achsen.currentItem()
        art, _objekt = (eintrag.data(0, ROLLE) if eintrag else None) or (None, None)
        self.knopf_betriebsart.setEnabled(art in ("gelenk", "ba"))
        self.knopf_ba_weg.setEnabled(art == "ba")
        eintrag = self.aufnahmen.currentItem()
        daten = eintrag.data(0, ROLLE) if eintrag is not None else None
        self.knopf_auf_weg.setEnabled(bool(daten) and daten[0] == "auf")
        revolver = [ba for ba in m.betriebsarten(self.maschine) if ba.Art == m.ART_REVOLVER]
        self.knopf_verteilen.setEnabled(bool(revolver))

    # Auswahl und Details
    def _gelenk_des_eintrags(self, eintrag):
        art, objekt = eintrag.data(0, ROLLE) or (None, None)
        if art == "gelenk":
            return objekt
        if art == "ba":
            return objekt.Gelenk
        return None

    def _achse_gewaehlt(self, aktuell, _vorher):
        if aktuell is not None:
            self.aufnahmen.blockSignals(True)
            self.aufnahmen.setCurrentItem(None)
            self.aufnahmen.blockSignals(False)
        art, objekt = (aktuell.data(0, ROLLE) if aktuell else None) or (None, None)
        self._detail_leeren()
        if art == "ba":
            self._detail_betriebsart(objekt)
        self._knoepfe_schalten()

    def _aufnahme_gewaehlt(self, aktuell, _vorher):
        if aktuell is not None:
            self.achsen.blockSignals(True)
            self.achsen.setCurrentItem(None)
            self.achsen.blockSignals(False)
        self._detail_leeren()
        daten = aktuell.data(0, ROLLE) if aktuell is not None else None
        if daten and daten[0] == "auf":
            self._detail_aufnahme(daten[1])
        self._knoepfe_schalten()

    def _detail_leeren(self):
        self.detail_titel.setText("")
        while self.detail_aufbau.rowCount():
            self.detail_aufbau.removeRow(0)
        self.detail_kasten.hide()

    def _detail_unter(self, anker):
        """Zeigt den Detailkasten direkt unter `anker` (einer Knopfzeile)."""
        self._aufbau.removeWidget(self.detail_kasten)
        self._aufbau.insertWidget(self._aufbau.indexOf(anker) + 1, self.detail_kasten)
        self.detail_kasten.show()

    def _detail_betriebsart(self, ba):
        self._detail_unter(self.achsen_knoepfe)
        gelenk = ba.Gelenk.Label if ba.Gelenk is not None else "?"
        self.detail_titel.setText(
            tr("dialog.detail_betriebsart", art=m.art_text(ba.Art), gelenk=gelenk)
        )
        name = QtGui.QLineEdit(ba.NcName)
        name.setPlaceholderText(tr("dialog.ncname.platzhalter"))
        name.setToolTip(tr("eigenschaft.ncname"))
        name.editingFinished.connect(lambda: self._setze(ba, "NcName", name.text().strip(), label=True))
        self.detail_aufbau.addRow(tr("dialog.ncname"), name)

        linear = self._gelenkart(ba) == LINEAR
        einheiten = EINHEIT_LINEAR if linear else EINHEIT_DREH
        for eigenschaft, pflicht in m.WERTE[ba.Art]:
            beschriftung = m.wert_text(eigenschaft)
            if eigenschaft in einheiten:
                beschriftung += f" ({einheiten[eigenschaft]})"
            if eigenschaft == "Endlos":
                feld = QtGui.QCheckBox()
                feld.setChecked(bool(ba.Endlos))
                feld.toggled.connect(lambda wert, e=eigenschaft: self._setze(ba, e, bool(wert)))
            else:
                feld = QtGui.QLineEdit(_zahl_zeigen(getattr(ba, eigenschaft)))
                feld.setValidator(QtGui.QDoubleValidator(0, 1e9, 6))
                feld.setPlaceholderText(tr("feld.pflicht") if pflicht else tr("feld.unbekannt"))
                feld.editingFinished.connect(
                    lambda f=feld, e=eigenschaft: self._setze(ba, e, _zahl_lesen(f.text()))
                )
            feld.setToolTip(ba.getDocumentationOfProperty(eigenschaft))
            label = QtGui.QLabel(beschriftung)
            if pflicht:
                schrift = label.font()
                schrift.setBold(True)
                label.setFont(schrift)
            self.detail_aufbau.addRow(label, feld)
        if any(e == "Beschleunigung" for e, _p in m.WERTE[ba.Art]):
            verweis = QtGui.QLabel(f'<a href="beschleunigung">{tr("dialog.beschleunigung_ermitteln")}</a>')
            verweis.linkActivated.connect(lambda thema: zeige_hilfe(self.form, thema))
            self.detail_aufbau.addRow(verweis)

    def _detail_aufnahme(self, auf):
        self._detail_unter(self.aufnahmen_knoepfe)
        if auf.Art == m.AUFNAHME_WERKZEUG:
            self.detail_titel.setText(tr("dialog.detail_werkzeugaufnahme", name=m.name_von(auf)))
        else:
            self.detail_titel.setText(tr("dialog.detail_werkstueckaufnahme", name=m.name_von(auf)))
        name = QtGui.QLineEdit(m.name_von(auf))
        name.setToolTip(tr("eigenschaft.bezeichnung"))
        name.editingFinished.connect(
            lambda: name.text().strip() and self._setze(auf, "Bezeichnung", name.text().strip(), label=True)
        )
        self.detail_aufbau.addRow(tr("dialog.aufnahme_name"), name)

        lcs_liste = QtGui.QComboBox()
        for lcs in self._alle_lcs():
            lcs_liste.addItem(lcs.Label, lcs.Name)
        lcs_liste.setCurrentIndex(max(lcs_liste.findData(auf.Lcs.Name if auf.Lcs else ""), 0))
        lcs_liste.setToolTip(tr("eigenschaft.lcs"))
        lcs_liste.currentIndexChanged.connect(
            lambda _i: self._setze(auf, "Lcs", self.doc.getObject(lcs_liste.currentData()))
        )
        self.detail_aufbau.addRow(tr("dialog.aufnahme_lcs"), lcs_liste)

        if auf.Art == m.AUFNAHME_WERKZEUG:
            antrieb = QtGui.QComboBox()
            antrieb.addItem(tr("dialog.kein_antrieb"), "")
            for ba in m.betriebsarten(self.maschine):
                if ba.Art == m.ART_SPINDEL:
                    antrieb.addItem(m.name_von(ba), ba.Name)
            antrieb.setCurrentIndex(max(antrieb.findData(auf.Spindel.Name if auf.Spindel else ""), 0))
            antrieb.setToolTip(tr("eigenschaft.spindel"))
            antrieb.currentIndexChanged.connect(
                lambda _i: self._setze(
                    auf, "Spindel", self.doc.getObject(antrieb.currentData()) if antrieb.currentData() else None
                )
            )
            self.detail_aufbau.addRow(tr("dialog.aufnahme_antrieb"), antrieb)

            platz = QtGui.QSpinBox()
            platz.setRange(0, 999)
            platz.setSpecialValueText(tr("dialog.kein_platz"))
            platz.setValue(auf.Platz)
            platz.setPrefix("P")
            platz.setToolTip(tr("eigenschaft.platz"))
            platz.valueChanged.connect(lambda wert: self._setze(auf, "Platz", int(wert)))
            self.detail_aufbau.addRow(tr("dialog.aufnahme_platz"), platz)

    def _gelenkart(self, ba):
        gelenk = next((g for g in self.kette.gelenke if g.objekt == ba.Gelenk), None)
        return gelenk.art if gelenk else None

    def _alle_lcs(self):
        return [o for o in self.assembly.OutListRecursive if o.isDerivedFrom("App::LocalCoordinateSystem")]

    # Ändern
    def _setze(self, objekt, eigenschaft, wert, label=False):
        if getattr(objekt, eigenschaft) == wert:
            return
        setattr(objekt, eigenschaft, wert)
        if label:
            m.beschrifte(objekt)
        if eigenschaft in ("Lcs", "Platz"):
            # Kann eine Aufnahme in die Revolvergruppe hinein oder heraus
            # bewegen – dann die Liste neu aufbauen.
            QtCore.QTimer.singleShot(0, lambda: self._neu_aufbauen(objekt))
        else:
            self._auffrischen()

    def _auffrischen(self):
        """Texte, Status-Symbole und Hinweise der vorhandenen Zeilen erneuern.

        Bewusst ohne clear() und Neuaufbau: Die Listen nach jeder Eingabe neu
        zu bauen, ließ FreeCAD unter PySide6 gelegentlich abstürzen (gefunden
        im Szenario, P-2026-09-25-17).
        """
        if self.geschlossen:
            return
        for baum in (self.achsen, self.aufnahmen):
            it = QtGui.QTreeWidgetItemIterator(baum)
            while it.value():
                art, objekt = it.value().data(0, ROLLE) or (None, None)
                if art == "ba":
                    it.value().setText(0, self._text_betriebsart(objekt))
                elif art == "auf":
                    it.value().setText(0, self._text_aufnahme(objekt))
                it += 1
        self._pruefen()
        self._knoepfe_schalten()

    def _neu_aufbauen(self, auswahl):
        if not self.geschlossen:
            self._fuelle_alles(auswahl)

    def _name_geaendert(self):
        text = self.name.text().strip()
        if text:
            self.maschine.Label = text

    def _betriebsart_menue(self):
        eintrag = self.achsen.currentItem()
        gelenk_objekt = self._gelenk_des_eintrags(eintrag) if eintrag else None
        gelenk = next((g for g in self.kette.gelenke if g.objekt == gelenk_objekt), None)
        if gelenk is None:
            return
        menue = QtGui.QMenu(self.form)
        beschreibung = {
            m.ART_LINEAR: tr("art.linear.beschreibung"),
            m.ART_POSITIONIEREN: tr("art.positionieren.beschreibung"),
            m.ART_SPINDEL: tr("art.spindel.beschreibung"),
            m.ART_REVOLVER: tr("art.revolver.beschreibung"),
        }
        for art in m.ERLAUBT[gelenk.art]:
            aktion = menue.addAction(f"{m.art_text(art)} – {beschreibung[art]}")
            aktion.triggered.connect(lambda _c=False, a=art: self._betriebsart_neu(gelenk.objekt, a))
        self._letztes_menue = menue
        menue.popup(self.knopf_betriebsart.mapToGlobal(QtCore.QPoint(0, self.knopf_betriebsart.height())))

    def _betriebsart_neu(self, gelenk_objekt, art):
        ba = m.neue_betriebsart(self.maschine, gelenk_objekt, art, "")
        self._fuelle_alles(auswahl=ba)
        self._fokus_auf_ncname()

    def _fokus_auf_ncname(self):
        if self.detail_aufbau.rowCount():
            feld = self.detail_aufbau.itemAt(0, QtGui.QFormLayout.FieldRole).widget()
            feld.setFocus()

    def _betriebsart_entfernen(self):
        eintrag = self.achsen.currentItem()
        art, objekt = (eintrag.data(0, ROLLE) if eintrag else None) or (None, None)
        if art != "ba":
            return
        for auf in m.aufnahmen(self.maschine):
            if auf.Spindel == objekt:
                auf.Spindel = None
        self.doc.removeObject(objekt.Name)
        self._detail_leeren()
        self._fuelle_alles()

    def _aufnahme_neu(self, art):
        alle = self._alle_lcs()
        if not alle:
            QtGui.QMessageBox.information(self.form, tr("dialog.titel"), tr("dialog.kein_lcs"))
            return
        # Vorauswahl: ein in der 3D-Ansicht gewähltes LCS, sonst das erste freie.
        belegt = {a.Lcs for a in m.aufnahmen(self.maschine)}
        gewaehlt = [o for o in FreeCADGui.Selection.getSelection() if o in alle]
        lcs = gewaehlt[0] if gewaehlt else next((x for x in alle if x not in belegt), alle[0])
        name = tr("aufnahme.werkzeug") if art == m.AUFNAHME_WERKZEUG else tr("aufnahme.werkstueck")
        auf = m.neue_aufnahme(self.maschine, lcs, art, name)
        self._fuelle_alles(auswahl=auf)

    def _aufnahme_entfernen(self):
        eintrag = self.aufnahmen.currentItem()
        daten = eintrag.data(0, ROLLE) if eintrag is not None else None
        if not daten or daten[0] != "auf":
            return
        self.doc.removeObject(daten[1].Name)
        self._detail_leeren()
        self._fuelle_alles()

    def _plaetze_verteilen(self):
        revolver = [ba for ba in m.betriebsarten(self.maschine) if ba.Art == m.ART_REVOLVER]
        if not revolver:
            return
        dialog = VerteilDialog(self.form, revolver, self._lcs_im_revolver)
        if dialog.exec_() != QtGui.QDialog.Accepted:
            return
        ba, lcs, anzahl = dialog.ergebnis()
        m.verteile_plaetze(self.maschine, self.kette, ba, lcs, anzahl)
        self.doc.recompute()
        self._fuelle_alles()

    def _lcs_im_revolver(self, ba):
        gelenk = next((g for g in self.kette.gelenke if g.objekt == ba.Gelenk), None)
        if gelenk is None:
            return []
        return [lcs for lcs in self._alle_lcs() if self.kette.glied_von(lcs) is gelenk.kind]

    def _hinweis_geklickt(self, eintrag):
        bezug = eintrag.data(ROLLE)
        if bezug is None:
            return
        for baum in (self.achsen, self.aufnahmen):
            it = QtGui.QTreeWidgetItemIterator(baum)
            while it.value():
                daten = it.value().data(0, ROLLE)
                if daten and daten[1] == bezug:
                    if it.value().parent() is not None:
                        it.value().parent().setExpanded(True)
                    baum.setCurrentItem(it.value())
                    baum.scrollToItem(it.value())
                    return
                it += 1


class VerteilDialog(QtGui.QDialog):
    """Revolver, ersten Platz und Anzahl wählen."""

    def __init__(self, eltern, revolver, lcs_fuer):
        super().__init__(eltern)
        self.setWindowTitle(tr("dialog.plaetze_verteilen"))
        self.revolver = revolver
        self.lcs_fuer = lcs_fuer
        aufbau = QtGui.QFormLayout(self)
        erklaerung = QtGui.QLabel(tr("verteilen.erklaerung"))
        erklaerung.setWordWrap(True)
        aufbau.addRow(erklaerung)
        self.wahl_revolver = QtGui.QComboBox()
        for ba in revolver:
            self.wahl_revolver.addItem(m.name_von(ba))
        self.wahl_revolver.currentIndexChanged.connect(self._lcs_fuellen)
        aufbau.addRow(tr("verteilen.revolver"), self.wahl_revolver)
        self.wahl_lcs = QtGui.QComboBox()
        aufbau.addRow(tr("verteilen.erster_platz"), self.wahl_lcs)
        self.anzahl = QtGui.QSpinBox()
        self.anzahl.setRange(2, 96)
        self.anzahl.setValue(12)
        aufbau.addRow(tr("verteilen.anzahl"), self.anzahl)
        self.hinweis = QtGui.QLabel()
        self.hinweis.setWordWrap(True)
        aufbau.addRow(self.hinweis)
        self.knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        self.knoepfe.accepted.connect(self.accept)
        self.knoepfe.rejected.connect(self.reject)
        aufbau.addRow(self.knoepfe)
        self._lcs_fuellen()

    def _lcs_fuellen(self, *_):
        self.wahl_lcs.clear()
        liste = self.lcs_fuer(self.revolver[self.wahl_revolver.currentIndex()])
        # Von der Verteilhilfe selbst angelegte LCS nicht als „ersten Platz“ anbieten.
        liste = [lcs for lcs in liste if "_P" not in lcs.Label]
        self._lcs = liste
        for lcs in liste:
            self.wahl_lcs.addItem(lcs.Label)
        ok = bool(liste)
        self.hinweis.setText("" if ok else tr("verteilen.kein_lcs"))
        self.knoepfe.button(QtGui.QDialogButtonBox.Ok).setEnabled(ok)

    def ergebnis(self):
        return (
            self.revolver[self.wahl_revolver.currentIndex()],
            self._lcs[self.wahl_lcs.currentIndex()],
            self.anzahl.value(),
        )
