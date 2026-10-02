# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Schnittwert-Tabelle in der Werkzeugverwaltung (W-002, Spezifikation Abschnitt 6).

Eine Zeile je Einsatz: vorn der Werkstoff, für den sie gilt – wählbar je Zeile (Manuel,
2026-10-01: „das Material muss zu den Schnittwerten … wenn ich Schnittwerte anlege, muss
ich das Material auswählen“); „Alle Werkstoffe“ gilt für jeden Werkstoff, der keine
eigene Zeile hat. Eingegeben werden ae, ap, vc und fz, gerechnet und grau daneben n, vf
und Q. ae und ap wahlweise in mm oder in % von D – gespeichert wird immer in mm. Die
Daten stehen in werkzeuge.py (je Werkstoff eine Liste), das Rechnen in schnittdaten.py.
"""

import dataclasses
import math

import FreeCAD
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, einheiten
from . import schnittdaten as sd
from . import schruppwerte as sw
from . import werkstoffe as ws
from . import werkzeuge as wz
from .gui_eingriff import BREITE as BILD_BREITE
from .gui_eingriff import EingriffBild
from .gui_hilfe import kopfzeile
from .gui_schruppwerte import SchruppDialog
from .gui_strategie import StrategieDialog
from .gui_teile import GRAU, hinweiszeile, knopf, ruhiges_mausrad
from .gui_zahlen import (
    Zahlenpruefer,
    dezimal,
    groesse_fest,
    groesse_lesen,
    groesse_zeigen,
    zahl_lesen,
    zahl_zeigen,
    zahlenformat,
)
from .sprache import tr

# Spalten der Tabelle.
WERKSTOFF, EINSATZ, AE, AP, VC, FZ, N, VF, Q = range(9)
EINGABE_SPALTEN = {AE: "ae", AP: "ap", VC: "vc", FZ: "fz"}
TABELLE_MINDESTHOEHE = 150  # Pixel
WERKSTOFF_BREITE = 190  # Pixel – die Spalte mit der Auswahl des Werkstoffs
SPAN = einheiten.SPAN  # fz und Spandicke: mm oder inch, feiner gerundet
# Gemerkt in den Einstellungen: ae und ap in % von D statt in mm.
IN_PROZENT = "SchnittwerteInProzent"


def werkstoff_info(werkstoff):
    """Zusammensetzung, Härte, Festigkeit und ISO-Gruppe eines Werkstoffs – als Tooltip der
    Werkstoff-Auswahl in der Zeile; None: „Alle Werkstoffe“."""
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


class SchnittwertBereich(QtGui.QWidget):
    """Überschrift, Satz zum Werkstoff je Zeile, Tabelle, Knöpfe, Hinweise.

    `geaendert()` wird nach jeder Änderung an den Werten aufgerufen; `alle_waehlen()` stellt
    oben „Alle Werkstoffe“ ein – für den ersten Einsatz eines Werkzeugs (D-12).
    """

    def __init__(self, geaendert):
        super().__init__()
        self._geaendert = geaendert
        self.werkzeug = None
        self.bibliothek = None
        self._liste = []  # die gezeigten Zeilen: (Kennung des Werkstoffs, Einsatz)
        self._fuellt = False
        # Die Werkstoffe zur Wahl – ein Modell für die Auswahl in jeder Zeile.
        self._werkstoffe = QtGui.QComboBox()
        self._werkstoffe.hide()

        aufbau = QtGui.QVBoxLayout(self)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.addWidget(kopfzeile(tr("wv.schnittwerte"), "schnittwerte"))
        # Drehwerkzeuge und Taster haben (noch) keine Schnittwerte: ein Satz statt der Tabelle.
        self.ohne_tabelle = QtGui.QLabel()
        self.ohne_tabelle.setWordWrap(True)
        self.ohne_tabelle.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        aufbau.addWidget(self.ohne_tabelle, 1)
        self.inhalt = QtGui.QWidget()
        aufbau.addWidget(self.inhalt, 1)
        aufbau = QtGui.QVBoxLayout(self.inhalt)
        aufbau.setContentsMargins(0, 0, 0, 0)

        zeile = QtGui.QHBoxLayout()
        self.zustand = QtGui.QLabel()
        self.zustand.setWordWrap(True)
        zeile.addWidget(self.zustand, 1)
        # ae und ap in mm oder in % von D – eine Wahl für die ganze Tabelle, gemerkt.
        self.wahl_einheit = QtGui.QComboBox()
        self.wahl_einheit.addItem(tr("wv.zustellung.mm"), False)
        self.wahl_einheit.addItem(tr("wv.zustellung.prozent"), True)
        self.wahl_einheit.setToolTip(tr("wv.zustellung.tooltip"))
        gemerkt = FreeCAD.ParamGet(PARAMETER_PFAD).GetBool(IN_PROZENT, False)
        self.wahl_einheit.setCurrentIndex(self.wahl_einheit.findData(gemerkt))
        self.wahl_einheit.currentIndexChanged.connect(self._einheit_gewechselt)
        zeile.addWidget(self.wahl_einheit)
        aufbau.addLayout(zeile)
        self.zustand.setText(tr("wv.schnittwerte.werkstoffe"))

        self.tabelle = QtGui.QTableWidget(0, 9)
        self.tabelle.setMinimumHeight(TABELLE_MINDESTHOEHE)
        self.tabelle.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tabelle.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tabelle.verticalHeader().hide()
        self.tabelle.setItemDelegate(_Zahlendelegat(self.tabelle))
        self._kopf_setzen()
        kopf = self.tabelle.horizontalHeader()
        kopf.setSectionResizeMode(QtGui.QHeaderView.ResizeToContents)
        kopf.setSectionResizeMode(EINSATZ, QtGui.QHeaderView.Stretch)
        # Die Werkstoff-Spalte fest so breit, dass Nummer und Kurzname zu lesen sind – die
        # Auswahl darin zeigt den Rest beim Aufklappen.
        kopf.setSectionResizeMode(WERKSTOFF, QtGui.QHeaderView.Interactive)
        self.tabelle.setColumnWidth(WERKSTOFF, WERKSTOFF_BREITE)
        self.tabelle.itemChanged.connect(self._zelle_geaendert)
        self.tabelle.currentCellChanged.connect(lambda *_: self._hinweise())
        # Ohne Zeile sagt ein Satz, wie es weitergeht – sonst stünde da eine leere Tabelle
        # (Manuel, 2026-10-02: „die Bedienung schön“).
        self.leer_hinweis = QtGui.QLabel(tr("wv.schnittwerte.leer"))
        self.leer_hinweis.setWordWrap(True)
        self.leer_hinweis.setStyleSheet(f"color: {GRAU.name()};")
        self.leer_hinweis.hide()
        aufbau.addWidget(self.leer_hinweis)
        aufbau.addWidget(self.tabelle, 1)

        zeile = QtGui.QHBoxLayout()
        # Ein Knopf mit Menü: Die Arten stehen zur Wahl, ohne dass eine Liste Platz braucht.
        self.knopf_plus = QtGui.QPushButton(tr("wv.einsatz.plus"))
        self.knopf_plus.setToolTip(tr("wv.einsatz.plus.tooltip"))
        self.knopf_plus.setAutoDefault(False)
        self.menue_plus = QtGui.QMenu(self.knopf_plus)
        self.knopf_plus.setMenu(self.menue_plus)
        self._menue_fuellen()
        zeile.addWidget(self.knopf_plus)
        self.knopf_minus = knopf(
            tr("wv.einsatz.minus"), tr("wv.einsatz.minus.tooltip"), self.einsatz_entfernen
        )
        zeile.addWidget(self.knopf_minus)
        zeile.addStretch()
        self.knopf_planen = knopf(tr("sp.knopf"), "", self.schruppwerte_planen)
        zeile.addWidget(self.knopf_planen)
        self.knopf_vergleich = knopf(
            tr("wv.strategie.knopf"), tr("wv.strategie.knopf.tooltip"), self.strategien_vergleichen
        )
        zeile.addWidget(self.knopf_vergleich)
        aufbau.addLayout(zeile)

        self.hinweis = hinweiszeile()
        aufbau.addWidget(self.hinweis)

        # Zur gewählten Zeile: Bild des Eingriffs, die Werte dazu in Worten und
        # der Spandickenausgleich.
        self.eingriff = QtGui.QWidget()
        zeile = QtGui.QHBoxLayout(self.eingriff)
        zeile.setContentsMargins(0, 0, 0, 0)
        self.bild = EingriffBild()
        self.bild.setToolTip(tr("wv.eingriff.bild.tooltip"))
        # Über jeder Hälfte des Bilds, was sie zeigt – das Bild selbst hat
        # keinen Text, damit es in jeder Sprache passt.
        bild_spalte = QtGui.QVBoxLayout()
        bild_spalte.setSpacing(2)
        titel = QtGui.QHBoxLayout()
        titel.setSpacing(0)
        self.bild_titel = []
        for kurz, name, ansicht in (
            ("ae", tr("wv.eingriff.titel.ae"), tr("wv.eingriff.von_oben")),
            ("ap", tr("wv.eingriff.titel.ap"), tr("wv.eingriff.von_der_seite")),
        ):
            ueberschrift = QtGui.QLabel(
                f"<b>{kurz}</b> – {name}<br><span style='color: {GRAU.name()};'>{ansicht}</span>"
            )
            ueberschrift.setWordWrap(True)
            ueberschrift.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom)
            ueberschrift.setFixedWidth(BILD_BREITE // 2)
            titel.addWidget(ueberschrift)
            self.bild_titel.append(ueberschrift)
        bild_spalte.addLayout(titel)
        bild_spalte.addWidget(self.bild)
        bild_spalte.addStretch()
        zeile.addLayout(bild_spalte)
        rechts = QtGui.QVBoxLayout()
        self.eingriff_text = QtGui.QLabel()
        self.eingriff_text.setWordWrap(True)
        rechts.addWidget(self.eingriff_text)
        self.ausgleich = QtGui.QWidget()
        ausgleich = QtGui.QHBoxLayout(self.ausgleich)
        ausgleich.setContentsMargins(0, 0, 0, 0)
        beschriftung = QtGui.QLabel(tr("wv.ausgleich"))
        beschriftung.setToolTip(tr("wv.ausgleich.tooltip"))
        ausgleich.addWidget(beschriftung)
        self.feld_spandicke = QtGui.QLineEdit()
        self.feld_spandicke.setValidator(Zahlenpruefer(self.feld_spandicke))
        self.feld_spandicke.setFixedWidth(80)  # Platz für „0,090“
        self.feld_spandicke.setToolTip(tr("wv.ausgleich.tooltip"))
        self.feld_spandicke.textChanged.connect(self._ausgleich_rechnen)
        ausgleich.addWidget(self.feld_spandicke)
        self.ausgleich_ergebnis = QtGui.QLabel()
        ausgleich.addWidget(self.ausgleich_ergebnis)
        self.knopf_ausgleich = knopf(
            tr("wv.ausgleich.knopf"), tr("wv.ausgleich.knopf.tooltip"), self.spandicke_ausgleichen
        )
        ausgleich.addWidget(self.knopf_ausgleich)
        ausgleich.addStretch()
        rechts.addWidget(self.ausgleich)
        rechts.addStretch()
        zeile.addLayout(rechts, 1)
        aufbau.addWidget(self.eingriff)

    # --- von außen ------------------------------------------------------------------

    def zeige(self, werkzeug, bibliothek):
        """Zeigt alle Einsätze von `werkzeug` – je Zeile mit dem Werkstoff, für den sie gilt;
        `bibliothek` (werkzeuge.Bibliothek) gibt die Werkstoffe zur Wahl."""
        from .gui_werkzeuge import werkstoffe_anbieten

        self.werkzeug = werkzeug
        self.bibliothek = bibliothek
        if werkzeug is None:
            self.hide()
            return
        self.show()
        # Die Auswahl in den Zeilen teilt das Modell: Beim Neufüllen melden sie eine Wahl –
        # die zählt nicht (_werkstoff_gewechselt).
        self._fuellt = True
        try:
            werkstoffe_anbieten(self._werkstoffe, bibliothek)
        finally:
            self._fuellt = False
        ohne = wz.einsatzarten(werkzeug.art) is None
        self.inhalt.setVisible(not ohne)
        self.ohne_tabelle.setVisible(ohne)
        if ohne:
            gruppe = wz.artdaten(werkzeug.art).gruppe
            self.ohne_tabelle.setText(
                tr("wv.ohne_schnittwerte.drehen")
                if gruppe == wz.GRUPPE_DREHEN
                else tr("wv.ohne_schnittwerte.taster")
            )
            self._liste = []
            return
        self._liste = self._alle_zeilen()
        self._menue_fuellen()
        self._kopf_setzen()
        self._fuellen()

    def auffrischen(self):
        """Nach einer Änderung am Werkzeug (Durchmesser, Schneiden, Art): neu rechnen."""
        if self.werkzeug is not None:
            self.zeige(self.werkzeug, self.bibliothek)

    @property
    def gewaehlt(self):
        """Der gewählte Einsatz, oder None."""
        zeile = self.tabelle.currentRow()
        return self._liste[zeile][1] if 0 <= zeile < len(self._liste) else None

    @property
    def gewaehlter_werkstoff(self):
        """Die Kennung des Werkstoffs der gewählten Zeile – ohne Zeile „Alle Werkstoffe“."""
        zeile = self.tabelle.currentRow()
        return self._liste[zeile][0] if 0 <= zeile < len(self._liste) else wz.ALLE

    def _kennungen(self):
        """Die Kennungen der Werkstoffe in der Reihenfolge der Auswahl: „Alle Werkstoffe“,
        eigene, dann die mitgelieferten nach ISO-Gruppe."""
        return [
            self._werkstoffe.itemData(i)
            for i in range(self._werkstoffe.count())
            if self._werkstoffe.itemData(i) is not None
        ]

    def _alle_zeilen(self):
        """[(Kennung, Einsatz)] in der Reihenfolge der Werkstoffe; Werkstoffe, die die Auswahl
        nicht mehr kennt, zuletzt."""
        bekannt = self._kennungen()
        reihenfolge = [k for k in bekannt if k in self.werkzeug.schnittwerte]
        reihenfolge += [k for k in self.werkzeug.schnittwerte if k not in bekannt]
        return [(k, e) for k in reihenfolge for e in self.werkzeug.schnittwerte[k]]

    # --- Aktionen -------------------------------------------------------------------

    def _werkstoff_objekt(self, kennung):
        """Der Werkstoff (werkstoffe.Werkstoff) zur Kennung – None bei „Alle Werkstoffe“."""
        if kennung == wz.ALLE or self.bibliothek is None:
            return None
        return ws.finde(self.bibliothek.alle_werkstoffe(), kennung)

    def _werkstoff_text(self, kennung):
        werkstoff = self._werkstoff_objekt(kennung)
        return ws.anzeige(werkstoff) if werkstoff is not None else tr("wv.alle_werkstoffe")

    def _zeile_von(self, einsatz):
        return next((z for z, (_k, e) in enumerate(self._liste) if e is einsatz), -1)

    def _liste_fuer(self, kennung):
        return self.werkzeug.schnittwerte.setdefault(kennung, [])

    def _aufraeumen(self, kennung):
        """Eine leere Liste eines Werkstoffs weg – für ihn gelten dann wieder die Zeilen für
        alle Werkstoffe."""
        if kennung != wz.ALLE and not self.werkzeug.schnittwerte.get(kennung):
            self.werkzeug.schnittwerte.pop(kennung, None)

    def _neu_fuellen(self, einsatz, spalte):
        self._geaendert()
        self._liste = self._alle_zeilen()
        self._fuellen()
        self.tabelle.setCurrentCell(self._zeile_von(einsatz), spalte)

    def einsatz_anlegen(self, art, werkstoff=None):
        """Neue Zeile mit ae und ap aus dem Durchmesser vorbelegt – für `werkstoff` (Kennung),
        ohne Angabe für den Werkstoff der gewählten Zeile, ohne Zeile für alle Werkstoffe; gibt
        den Einsatz zurück."""
        if self.werkzeug is None:
            return None
        liste = self._liste_fuer(werkstoff or self.gewaehlter_werkstoff)
        einsatz = wz.vorlage(self.werkzeug, art)
        einsatz.name = wz.name_fuer_neuen(einsatz, liste)
        liste.append(einsatz)
        self._neu_fuellen(einsatz, VC)
        return einsatz

    def einsatz_kopieren(self):
        """Kopie der gewählten Zeile direkt darunter, für denselben Werkstoff, mit Nummer im
        Namen; gibt sie zurück.

        Für Varianten: dieselben Werte, dann etwa ae ändern und beide unter
        „Strategien vergleichen…“ nebeneinanderstellen.
        """
        einsatz = self.gewaehlt
        if einsatz is None:
            return None
        liste = self._liste_fuer(self.gewaehlter_werkstoff)
        kopie = dataclasses.replace(einsatz, name=wz.name_fuer_neuen(einsatz, liste))
        liste.insert(liste.index(einsatz) + 1, kopie)
        # Meist ändert man in der Variante ae; beim Bohrer gibt es keine ae-Spalte.
        self._neu_fuellen(kopie, VC if self._bohrend() else AE)
        return kopie

    def einsatz_entfernen(self):
        """Entfernt die gewählte Zeile; die letzte eines Werkstoffs nimmt seine Liste mit –
        für ihn gelten dann wieder die Zeilen für alle Werkstoffe."""
        zeile = self.tabelle.currentRow()
        if not 0 <= zeile < len(self._liste):
            return
        kennung, einsatz = self._liste[zeile]
        self.werkzeug.schnittwerte[kennung].remove(einsatz)
        self._aufraeumen(kennung)
        self._geaendert()
        self._liste = self._alle_zeilen()
        self._fuellen()
        if self._liste:
            self.tabelle.setCurrentCell(min(zeile, len(self._liste) - 1), EINSATZ)

    def werkstoff_setzen(self, zeile, kennung):
        """Die Zeile `zeile` gilt ab jetzt für den Werkstoff `kennung`: Sie wandert ans Ende
        seiner Liste; die alte Liste, wenn leer, weg."""
        if not 0 <= zeile < len(self._liste):
            return
        vorher, einsatz = self._liste[zeile]
        if kennung == vorher or einsatz not in self.werkzeug.schnittwerte.get(vorher, []):
            return
        self.werkzeug.schnittwerte[vorher].remove(einsatz)
        self._aufraeumen(vorher)
        liste = self._liste_fuer(kennung)
        einsatz.name = wz.name_fuer_neuen(einsatz, liste)
        liste.append(einsatz)
        self._neu_fuellen(einsatz, EINSATZ)

    def strategien_vergleichen(self):
        """„Strategien vergleichen…“: zwei Einsätze, die für den Werkstoff der gewählten Zeile
        gelten, nebeneinander."""
        kennung = self.gewaehlter_werkstoff
        liste = self.werkzeug.einsaetze(kennung) if self.werkzeug is not None else []
        if self._bohrend() or len(liste) < 2:
            return
        # Ohne dezimal(): Die Werkstoffnummer 1.0503 ist keine Kommazahl.
        dialog = StrategieDialog(
            self,
            self.werkzeug,
            list(liste),
            self._werkstoff_objekt(kennung),
            self._werkstoff_text(kennung),
        )
        dialog.exec()
        StrategieDialog.offen = None

    def schruppwerte_planen(self):
        """„Schruppwerte planen…“: der Planer; was er vorschlägt, wird eine neue Zeile für den
        Werkstoff der gewählten Zeile."""
        if self.werkzeug is None or not sw.moeglich(self.werkzeug):
            return
        kennung = self.gewaehlter_werkstoff
        liste = self.werkzeug.einsaetze(kennung)
        dialog = SchruppDialog(
            self,
            self.werkzeug,
            sw.ausgangszeile(liste, self.gewaehlt),
            self._werkstoff_objekt(kennung),
            self._werkstoff_text(kennung),
            tr("sp.uebernehmen"),
            vergleich=sw.vergleichszeile(liste),
        )
        angenommen = dialog.exec()
        SchruppDialog.offen = None
        if angenommen and dialog.einsatz is not None:
            self.einsatz_hinzufuegen(dialog.einsatz, kennung)

    def einsatz_hinzufuegen(self, einsatz, werkstoff=None):
        """Hängt einen fertigen Einsatz an – für `werkstoff` (Kennung), ohne Angabe für den
        Werkstoff der gewählten Zeile."""
        liste = self._liste_fuer(werkstoff or self.gewaehlter_werkstoff)
        einsatz.name = wz.name_fuer_neuen(einsatz, liste)
        liste.append(einsatz)
        self._neu_fuellen(einsatz, EINSATZ)

    def setze(self, zeile, spalte, text):
        """Trägt `text` in eine Zelle ein, wie beim Tippen – für die Szenarien."""
        self.tabelle.item(zeile, spalte).setText(text)

    # --- Tabelle ----------------------------------------------------------------------

    def _bohrend(self):
        """Bohrt das Werkzeug? Dann f je Umdrehung statt fz, ohne ae und ap."""
        return self.werkzeug is not None and wz.bohrend(self.werkzeug.art)

    def _gewinde(self):
        """Ein Gewindebohrer: f ist die Steigung und steht fest."""
        return self.werkzeug is not None and wz.gewindebohrer(self.werkzeug.art)

    @property
    def in_prozent(self):
        """Zeigt die Tabelle ae und ap in % von D? Ohne Durchmesser immer in mm."""
        w = self.werkzeug
        return bool(self.wahl_einheit.currentData()) and w is not None and w.durchmesser > 0

    def _einheit_gewechselt(self, _index):
        FreeCAD.ParamGet(PARAMETER_PFAD).SetBool(IN_PROZENT, bool(self.wahl_einheit.currentData()))
        self._kopf_setzen()
        self._fuellen()

    def _zustellung_zeigen(self, mm):
        """ae oder ap als Text in der gewählten Einheit: % von D, mm oder inch."""
        if self.in_prozent:
            return zahl_zeigen(round(mm / self.werkzeug.durchmesser * 100, 1))
        return groesse_zeigen(mm, einheiten.LAENGE)

    def _kopf_setzen(self):
        """Spaltenköpfe mit Einheit; beim Bohren f je Umdrehung statt fz, ohne ae und ap."""
        bohrer = self._bohrend()
        if bohrer:
            vorschub = ("f\n" + tr("einheit.je_umdrehung"), tr("wv.spalte.f.tooltip"))
        else:
            vorschub = ("fz\n" + einheiten.einheit(einheiten.SPAN), tr("wv.spalte.fz.tooltip"))
        einheit = "% D" if self.in_prozent else einheiten.einheit(einheiten.LAENGE)
        koepfe = [
            (tr("wv.spalte.werkstoff"), tr("wv.spalte.werkstoff.tooltip")),
            (tr("wv.spalte.einsatz"), tr("wv.spalte.einsatz.tooltip")),
            ("ae\n" + einheit, tr("wv.spalte.ae.tooltip")),
            ("ap\n" + einheit, tr("wv.spalte.ap.tooltip")),
            ("vc\n" + einheiten.einheit(einheiten.SCHNITT), tr("wv.spalte.vc.tooltip")),
            vorschub,
            ("n\n" + tr("einheit.drehzahl"), tr("wv.spalte.n.tooltip")),
            ("vf\n" + einheiten.einheit(einheiten.VORSCHUB), tr("wv.spalte.vf.tooltip")),
            ("Q\n" + einheiten.einheit(einheiten.ABTRAG), tr("wv.spalte.q.tooltip")),
        ]
        for spalte, (text, tooltip) in enumerate(koepfe):
            kopf = QtGui.QTableWidgetItem(text)
            kopf.setToolTip(tooltip)
            self.tabelle.setHorizontalHeaderItem(spalte, kopf)
        self.tabelle.setColumnHidden(AE, bohrer)
        self.tabelle.setColumnHidden(AP, bohrer)
        self.wahl_einheit.setVisible(not bohrer)
        # „ae, ap: mm“ oder „ae, ap: in“ – je nach Maßsystem.
        self.wahl_einheit.setItemText(0, tr("wv.zustellung.mm"))
        # Ohne Durchmesser gibt es kein „% von D“.
        self.wahl_einheit.setEnabled(self.werkzeug is not None and self.werkzeug.durchmesser > 0)

    def _menue_fuellen(self):
        self.menue_plus.clear()
        # Nur die Einsätze, die zur Werkzeugart passen (Spezifikation Werkzeugarten, 5).
        arten = wz.einsatzarten(self.werkzeug.art) if self.werkzeug is not None else None
        for art in arten or (wz.EIGEN,):
            aktion = self.menue_plus.addAction(wz.einsatzart_text(art))
            aktion.triggered.connect(lambda _an=False, a=art: self.einsatz_anlegen(a))
        self.menue_plus.addSeparator()
        self.aktion_kopieren = self.menue_plus.addAction(tr("wv.einsatz.kopieren"))
        self.aktion_kopieren.triggered.connect(lambda _an=False: self.einsatz_kopieren())

    def _fuellen(self):
        """Schreibt alle Zeilen neu; die gewählte Zeile bleibt gewählt."""
        zeile_vorher = self.tabelle.currentRow()
        self._fuellt = True
        self.tabelle.setRowCount(len(self._liste))
        for zeile, (kennung, einsatz) in enumerate(self._liste):
            self._zeile_schreiben(zeile, einsatz, kennung)
        self._fuellt = False
        self.knopf_minus.setEnabled(bool(self._liste))
        self.leer_hinweis.setVisible(not self._liste)
        self.aktion_kopieren.setEnabled(bool(self._liste))
        planbar = sw.moeglich(self.werkzeug)
        self.knopf_planen.setEnabled(planbar)
        self.knopf_planen.setToolTip(
            tr("sp.knopf.tooltip") if planbar else tr("sp.knopf.nicht_moeglich")
        )
        if self._liste:
            self.tabelle.setCurrentCell(max(0, min(zeile_vorher, len(self._liste) - 1)), EINSATZ)
        self._hinweise()

    def _zeile_schreiben(self, zeile, einsatz, kennung=None):
        if kennung is None:
            kennung = self._liste[zeile][0]
        self._werkstoff_zelle(zeile, kennung)
        teiler = self.werkzeug.schneiden if self._bohrend() else 1
        vorschub = round(einsatz.fz * teiler, 6)
        if self._gewinde():
            vorschub = self.werkzeug.steigung  # f = P, steht fest
        eingaben = {
            EINSATZ: wz.einsatz_name(einsatz),
            AE: self._zustellung_zeigen(einsatz.ae),
            AP: self._zustellung_zeigen(einsatz.ap),
            VC: groesse_zeigen(einsatz.vc, einheiten.SCHNITT),
            FZ: groesse_zeigen(vorschub, einheiten.SPAN),
        }
        for spalte, text in eingaben.items():
            bearbeitbar = not (spalte == FZ and self._gewinde())
            self.tabelle.setItem(zeile, spalte, self._zelle(text, bearbeitbar=bearbeitbar))
        self._ergebnis_schreiben(zeile, einsatz)

    def _werkstoff_zelle(self, zeile, kennung):
        """Die erste Spalte: in der Zelle die Auswahl der Werkstoffe, dahinter die Kennung
        (item(zeile, WERKSTOFF).data(UserRole) – für die Szenarien)."""
        zelle = QtGui.QTableWidgetItem(self._werkstoff_text(kennung))
        zelle.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        zelle.setData(QtCore.Qt.UserRole, kennung)
        self.tabelle.setItem(zeile, WERKSTOFF, zelle)
        wahl = self.tabelle.cellWidget(zeile, WERKSTOFF)
        if wahl is None:
            wahl = QtGui.QComboBox()
            wahl.setModel(self._werkstoffe.model())
            wahl.setMaxVisibleItems(20)
            # Nicht so breit wie der längste Werkstoff – so breit wie die Zelle.
            wahl.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLengthWithIcon)
            wahl.setMinimumContentsLength(8)
            wahl.currentIndexChanged.connect(lambda _i, w=wahl: self._werkstoff_gewechselt(w))
            ruhiges_mausrad(wahl)
            self.tabelle.setCellWidget(zeile, WERKSTOFF, wahl)
        index = wahl.findData(kennung)
        if index < 0:  # ein Werkstoff, den die Liste nicht mehr kennt: so, wie er heißt
            self._werkstoffe.addItem(kennung, kennung)
            index = wahl.findData(kennung)
        wahl.blockSignals(True)
        wahl.setCurrentIndex(index)
        wahl.blockSignals(False)
        wahl.setToolTip(werkstoff_info(self._werkstoff_objekt(kennung)))

    def _werkstoff_gewechselt(self, wahl):
        """In einer Zeile wurde ein anderer Werkstoff gewählt."""
        if self._fuellt:
            return
        for zeile in range(self.tabelle.rowCount()):
            if self.tabelle.cellWidget(zeile, WERKSTOFF) is wahl:
                self.werkstoff_setzen(zeile, wahl.currentData() or wz.ALLE)
                return

    def _ergebnis_schreiben(self, zeile, einsatz):
        n, vf, q = sd.rechne(self.werkzeug, einsatz)
        for spalte, wert, text in (
            (N, n, zahlenformat().toString(n, "f", 0)),
            (VF, vf, groesse_fest(vf, einheiten.VORSCHUB, 0)),
            (Q, q, groesse_fest(q, einheiten.ABTRAG, 1)),
        ):
            text = text if wert else ""
            zelle = self._zelle(text, bearbeitbar=False)
            zelle.setForeground(GRAU)
            self.tabelle.setItem(zeile, spalte, zelle)

    def _zelle(self, text, bearbeitbar):
        zelle = QtGui.QTableWidgetItem(text)
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        if bearbeitbar:
            flags |= QtCore.Qt.ItemIsEditable
        else:
            zelle.setForeground(GRAU)
        zelle.setFlags(flags)
        return zelle

    def _zelle_geaendert(self, zelle):
        """Eine Eingabe in der Tabelle: in den Einsatz übernehmen und die Zeile neu rechnen."""
        if self._fuellt or zelle.column() == WERKSTOFF:
            return
        zeile, spalte = zelle.row(), zelle.column()
        _kennung, einsatz = self._liste[zeile]
        text = zelle.text().strip()
        if spalte == EINSATZ:
            # Der Name der Art ist kein eigener Name – so folgt er der Sprache.
            einsatz.name = "" if text == wz.einsatzart_text(einsatz.art) else text
        elif spalte in EINGABE_SPALTEN:
            try:
                wert = zahl_lesen(text)
            except ValueError:
                wert = getattr(einsatz, EINGABE_SPALTEN[spalte])
            else:
                if spalte == FZ and self._bohrend():
                    wert = wert / max(self.werkzeug.schneiden, 1)
                if spalte in (AE, AP) and self.in_prozent:
                    wert = wert * self.werkzeug.durchmesser / 100
                else:
                    # Getippt in mm oder inch, m/min oder SFM – gespeichert metrisch.
                    groesse = {VC: einheiten.SCHNITT, FZ: einheiten.SPAN}.get(
                        spalte, einheiten.LAENGE
                    )
                    wert = einheiten.metrisch(wert, groesse)
            setattr(einsatz, EINGABE_SPALTEN[spalte], wert)
        self._fuellt = True
        self._zeile_schreiben(zeile, einsatz)
        self._fuellt = False
        self._geaendert()
        self._hinweise()

    def _hinweise(self):
        """Was an der gewählten Zeile nicht passt – sofort, als Satz. Dazu Bild und Eingriff."""
        einsatz = self.gewaehlt
        w = self.werkzeug
        saetze = []
        self._eingriff_zeigen()
        # Vergleichen lassen sich zwei Einsätze, die für den Werkstoff der Zeile gelten.
        liste = w.einsaetze(self.gewaehlter_werkstoff) if w is not None else []
        self.knopf_vergleich.setEnabled(not self._bohrend() and len(liste) >= 2)
        if einsatz is not None and w is not None and not self._bohrend():
            if w.durchmesser and einsatz.ae > w.durchmesser:
                saetze.append(tr("wv.hinweis.ae_zu_gross"))
            h = sd.spandicke_max(einsatz.fz, einsatz.ae, w.durchmesser)
            if 0 < h < sd.MINDEST_SPANDICKE:
                saetze.append(tr("wv.hinweis.span_duenn", h=groesse_fest(h, einheiten.SPAN, 3)))
            if w.schneidenlaenge and einsatz.ap > w.schneidenlaenge:
                saetze.append(
                    tr(
                        "wv.hinweis.ap_zu_gross",
                        ap=groesse_zeigen(einsatz.ap, einheiten.LAENGE),
                        laenge=groesse_zeigen(w.schneidenlaenge, einheiten.LAENGE),
                    )
                )
        if einsatz is not None and self._gewinde():
            if not einsatz.vc:
                saetze.append(tr("wv.hinweis.vc_fehlt"))
            if not w.steigung:
                saetze.append(tr("wv.hinweis.steigung"))
        elif einsatz is not None and (not einsatz.vc or not einsatz.fz):
            saetze.append(tr("wv.hinweis.vc_fz_fehlen"))
        self.hinweis.setText("\n".join(saetze))
        self.hinweis.setVisible(bool(saetze))

    # --- Eingriff ---------------------------------------------------------------------

    def _eingriff_zeigen(self):
        """Bild und Werte des Eingriffs zur gewählten Zeile; beim Bohrer nichts davon."""
        einsatz, w = self.gewaehlt, self.werkzeug
        if einsatz is None or w is None or self._bohrend() or not w.durchmesser:
            self.eingriff.hide()
            return
        self.eingriff.show()
        d = w.durchmesser
        self.bild.zeige(d, w.schneidenlaenge, einsatz.ae, einsatz.ap)
        phi = sd.eingriffswinkel(einsatz.ae, d)
        # Je Größe eine Zeile: ae, ap, dann der Eingriff.
        zeilen = [
            tr(
                "wv.eingriff.ae",
                ae=groesse_zeigen(einsatz.ae, einheiten.LAENGE),
                ae_d=_zahl(einsatz.ae / d * 100, 0),
            )
        ]
        if w.schneidenlaenge:
            zeilen.append(
                tr(
                    "wv.eingriff.ap_schneide",
                    ap=groesse_zeigen(einsatz.ap, einheiten.LAENGE),
                    ap_d=_zahl(einsatz.ap / d, 1),
                    ap_schneide=_zahl(einsatz.ap / w.schneidenlaenge * 100, 0),
                )
            )
        else:
            zeilen.append(
                tr(
                    "wv.eingriff.ap",
                    ap=groesse_zeigen(einsatz.ap, einheiten.LAENGE),
                    ap_d=_zahl(einsatz.ap / d, 1),
                )
            )
        zeilen.append(
            tr(
                "wv.eingriff.winkel",
                winkel=_zahl(math.degrees(phi), 0),
                anteil=_zahl(math.degrees(phi) / 3.6, 0),
            )
        )
        if einsatz.fz:
            zeilen.append(
                tr(
                    "wv.eingriff.spandicke",
                    hmax=groesse_fest(sd.spandicke_max(einsatz.fz, einsatz.ae, d), SPAN, 3),
                    hm=groesse_fest(sd.spandicke_mittel(einsatz.fz, einsatz.ae, d), SPAN, 3),
                )
            )
        self.eingriff_text.setText("\n".join(zeilen))
        # Ausgleichen lohnt nur, wo der Span dünner wird als fz: bei ae < D/2.
        duenner = 0 < einsatz.ae < d / 2 and einsatz.fz > 0
        self.ausgleich.setVisible(duenner)
        if duenner:
            self.feld_spandicke.setText(
                groesse_fest(sd.spandicke_max(einsatz.fz, einsatz.ae, d), SPAN, 3)
            )

    def _ausgleich_rechnen(self, *_):
        """Zeigt beim Tippen, welches fz die gewünschte Spandicke ergibt."""
        einsatz, w = self.gewaehlt, self.werkzeug
        if einsatz is None or w is None:
            return
        try:
            h = groesse_lesen(self.feld_spandicke.text(), SPAN)
        except ValueError:
            h = 0.0
        fz = sd.fz_fuer_spandicke(h, einsatz.ae, w.durchmesser)
        self.ausgleich_ergebnis.setText(
            tr("wv.ausgleich.ergebnis", fz=groesse_fest(fz, SPAN, 3)) if fz else ""
        )
        self.knopf_ausgleich.setEnabled(fz > 0 and abs(fz - einsatz.fz) > 1e-4)

    def spandicke_ausgleichen(self):
        """Setzt fz so, dass die größte Spandicke dem Wert im Feld entspricht."""
        einsatz, w = self.gewaehlt, self.werkzeug
        if einsatz is None or w is None:
            return
        h = groesse_lesen(self.feld_spandicke.text(), SPAN)
        fz = sd.fz_fuer_spandicke(h, einsatz.ae, w.durchmesser)
        if fz <= 0:
            return
        einsatz.fz = round(fz, 4)
        zeile = self.tabelle.currentRow()
        self._fuellt = True
        self._zeile_schreiben(zeile, einsatz)
        self._fuellt = False
        self._geaendert()
        self._hinweise()


def _zahl(wert, stellen):
    """Zahl mit fester Anzahl Nachkommastellen im Format der Oberfläche."""
    return zahlenformat().toString(float(wert), "f", stellen)


class _Zahlendelegat(QtGui.QStyledItemDelegate):
    """Zahlenspalten bekommen beim Bearbeiten ein Feld, das nur Zahlen annimmt."""

    def createEditor(self, eltern, option, index):
        feld = super().createEditor(eltern, option, index)
        if index.column() in EINGABE_SPALTEN and isinstance(feld, QtGui.QLineEdit):
            feld.setValidator(Zahlenpruefer(feld))
        return feld
