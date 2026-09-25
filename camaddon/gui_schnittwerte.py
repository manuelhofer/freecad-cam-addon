# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Schnittwert-Tabelle in der Werkzeugverwaltung (W-002, Spezifikation Abschnitt 6).

Eine Zeile je Einsatz: eingegeben werden ae, ap, vc und fz, gerechnet und grau
daneben n, vf und Q. Welche Tabelle gilt, hängt vom Werkstoff oben im Dialog
ab: seine eigene, sonst die für alle Werkstoffe – die ist dann nur zu sehen,
bis man für den Werkstoff eigene Werte anlegt. Die Daten stehen in
werkzeuge.py, das Rechnen in schnittdaten.py.
"""

from PySide import QtCore, QtGui

from . import schnittdaten as sd
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_zahlen import Zahlenpruefer, zahl_lesen, zahl_zeigen, zahlenformat
from .sprache import tr

# Spalten der Tabelle.
EINSATZ, AE, AP, VC, FZ, N, VF, Q = range(8)
EINGABE_SPALTEN = {AE: "ae", AP: "ap", VC: "vc", FZ: "fz"}
TABELLE_MINDESTHOEHE = 150  # Pixel
GRAU = QtGui.QColor("#6d6d6d")  # gerechnete Werte


class SchnittwertBereich(QtGui.QWidget):
    """Überschrift, Zustand (eigene Werte oder für alle), Tabelle, Knöpfe, Hinweise.

    `geaendert()` wird nach jeder Änderung an den Werten aufgerufen.
    """

    def __init__(self, geaendert):
        super().__init__()
        self._geaendert = geaendert
        self.werkzeug = None
        self.werkstoff = wz.ALLE
        self._liste = []  # die gezeigten Einsätze
        self._bearbeitbar = False
        self._fuellt = False

        aufbau = QtGui.QVBoxLayout(self)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.addWidget(kopfzeile(tr("wv.schnittwerte"), "schnittwerte"))

        zeile = QtGui.QHBoxLayout()
        self.zustand = QtGui.QLabel()
        self.zustand.setWordWrap(True)
        zeile.addWidget(self.zustand, 1)
        self.knopf_eigene = _knopf("", tr("wv.eigene_anlegen.tooltip"), self.eigene_anlegen)
        self.knopf_eigene_weg = _knopf(
            tr("wv.eigene_loeschen"), tr("wv.eigene_loeschen.tooltip"), self.eigene_loeschen
        )
        zeile.addWidget(self.knopf_eigene)
        zeile.addWidget(self.knopf_eigene_weg)
        aufbau.addLayout(zeile)

        self.tabelle = QtGui.QTableWidget(0, 8)
        self.tabelle.setMinimumHeight(TABELLE_MINDESTHOEHE)
        self.tabelle.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tabelle.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tabelle.verticalHeader().hide()
        self.tabelle.setItemDelegate(_Zahlendelegat(self.tabelle))
        self._kopf_setzen()
        kopf = self.tabelle.horizontalHeader()
        kopf.setSectionResizeMode(QtGui.QHeaderView.ResizeToContents)
        kopf.setSectionResizeMode(EINSATZ, QtGui.QHeaderView.Stretch)
        self.tabelle.itemChanged.connect(self._zelle_geaendert)
        self.tabelle.currentCellChanged.connect(lambda *_: self._hinweise())
        aufbau.addWidget(self.tabelle, 1)

        zeile = QtGui.QHBoxLayout()
        # Ein Knopf mit Menü: Die Arten stehen zur Wahl, ohne dass eine Liste Platz braucht.
        self.knopf_plus = QtGui.QPushButton(tr("wv.einsatz.plus"))
        self.knopf_plus.setToolTip(tr("wv.einsatz.plus.tooltip"))
        self.knopf_plus.setAutoDefault(False)
        self.menue_plus = QtGui.QMenu(self.knopf_plus)
        self.knopf_plus.setMenu(self.menue_plus)
        zeile.addWidget(self.knopf_plus)
        self.knopf_minus = _knopf(
            tr("wv.einsatz.minus"), tr("wv.einsatz.minus.tooltip"), self.einsatz_entfernen
        )
        zeile.addWidget(self.knopf_minus)
        zeile.addStretch()
        aufbau.addLayout(zeile)

        self.hinweis = QtGui.QLabel()
        self.hinweis.setWordWrap(True)
        self.hinweis.setStyleSheet("color: #c0392b;")
        aufbau.addWidget(self.hinweis)

    # --- von außen ------------------------------------------------------------------

    def zeige(self, werkzeug, werkstoff, werkstoff_kurz):
        """Zeigt die Tabelle, die für `werkzeug` und den Werkstoff (Kennung) gilt.

        `werkstoff_kurz` steht auf dem Knopf: „Eigene Werte für 1.4301 anlegen“.
        """
        self.werkzeug = werkzeug
        self.werkstoff = werkstoff
        self._werkstoff_kurz = werkstoff_kurz
        if werkzeug is None:
            self.hide()
            return
        self.show()
        eigene = werkzeug.zum_bearbeiten(werkstoff)
        self._bearbeitbar = eigene is not None
        self._liste = eigene if eigene is not None else werkzeug.einsaetze(werkstoff)
        if werkstoff == wz.ALLE:
            self.zustand.setText(tr("wv.schnittwerte.alle"))
        elif self._bearbeitbar:
            self.zustand.setText(tr("wv.schnittwerte.eigene", werkstoff=werkstoff_kurz))
        else:
            self.zustand.setText(tr("wv.schnittwerte.geerbt", werkstoff=werkstoff_kurz))
        self.knopf_eigene.setText(tr("wv.eigene_anlegen", werkstoff=werkstoff_kurz))
        self.knopf_eigene.setVisible(not self._bearbeitbar)
        self.knopf_eigene_weg.setVisible(werkzeug.hat_eigene(werkstoff))
        self.knopf_plus.setEnabled(self._bearbeitbar)
        self._menue_fuellen()
        self._kopf_setzen()
        self._fuellen()

    def auffrischen(self):
        """Nach einer Änderung am Werkzeug (Durchmesser, Schneiden, Art): neu rechnen."""
        if self.werkzeug is not None:
            self.zeige(self.werkzeug, self.werkstoff, self._werkstoff_kurz)

    @property
    def gewaehlt(self):
        """Der gewählte Einsatz, oder None."""
        zeile = self.tabelle.currentRow()
        return self._liste[zeile] if 0 <= zeile < len(self._liste) else None

    # --- Aktionen -------------------------------------------------------------------

    def eigene_anlegen(self):
        """Eigene Werte für den gewählten Werkstoff, als Kopie der Werte für alle."""
        self.werkzeug.eigene_anlegen(self.werkstoff)
        self._geaendert()
        self.auffrischen()

    def eigene_loeschen(self, fragen=True):
        """Eigene Werte weg – danach gelten wieder die für alle Werkstoffe."""
        if fragen:
            antwort = QtGui.QMessageBox.question(
                self,
                tr("wv.titel"),
                tr("wv.eigene_loeschen.frage", werkstoff=self._werkstoff_kurz),
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                QtGui.QMessageBox.No,
            )
            if antwort != QtGui.QMessageBox.Yes:
                return
        self.werkzeug.eigene_loeschen(self.werkstoff)
        self._geaendert()
        self.auffrischen()

    def einsatz_anlegen(self, art):
        """Neue Zeile mit ae und ap aus dem Durchmesser vorbelegt; gibt den Einsatz zurück."""
        if not self._bearbeitbar:
            return None
        einsatz = wz.vorlage(self.werkzeug, art)
        self._liste.append(einsatz)
        self._geaendert()
        self._fuellen()
        self.tabelle.setCurrentCell(len(self._liste) - 1, VC)
        return einsatz

    def einsatz_entfernen(self):
        """Entfernt die gewählte Zeile."""
        zeile = self.tabelle.currentRow()
        if not self._bearbeitbar or not 0 <= zeile < len(self._liste):
            return
        del self._liste[zeile]
        self._geaendert()
        self._fuellen()
        self.tabelle.setCurrentCell(min(zeile, len(self._liste) - 1), EINSATZ)

    def setze(self, zeile, spalte, text):
        """Trägt `text` in eine Zelle ein, wie beim Tippen – für die Szenarien."""
        self.tabelle.item(zeile, spalte).setText(text)

    # --- Tabelle ----------------------------------------------------------------------

    def _bohrer(self):
        return self.werkzeug is not None and self.werkzeug.art == wz.BOHRER

    def _kopf_setzen(self):
        """Spaltenköpfe mit Einheit; beim Bohrer f je Umdrehung statt fz, ohne ae und ap."""
        bohrer = self._bohrer()
        if bohrer:
            vorschub = ("f\nmm/U", tr("wv.spalte.f.tooltip"))
        else:
            vorschub = ("fz\nmm", tr("wv.spalte.fz.tooltip"))
        koepfe = [
            (tr("wv.spalte.einsatz"), tr("wv.spalte.einsatz.tooltip")),
            ("ae\nmm", tr("wv.spalte.ae.tooltip")),
            ("ap\nmm", tr("wv.spalte.ap.tooltip")),
            ("vc\nm/min", tr("wv.spalte.vc.tooltip")),
            vorschub,
            ("n\nU/min", tr("wv.spalte.n.tooltip")),
            ("vf\nmm/min", tr("wv.spalte.vf.tooltip")),
            ("Q\ncm³/min", tr("wv.spalte.q.tooltip")),
        ]
        for spalte, (text, tooltip) in enumerate(koepfe):
            kopf = QtGui.QTableWidgetItem(text)
            kopf.setToolTip(tooltip)
            self.tabelle.setHorizontalHeaderItem(spalte, kopf)
        self.tabelle.setColumnHidden(AE, bohrer)
        self.tabelle.setColumnHidden(AP, bohrer)

    def _menue_fuellen(self):
        self.menue_plus.clear()
        arten = (
            [wz.BOHREN, wz.EIGEN]
            if self._bohrer()
            else [
                wz.VOLLNUT,
                wz.SCHRUPPEN,
                wz.DYNAMISCH,
                wz.SCHLICHTEN,
                wz.EIGEN,
            ]
        )
        for art in arten:
            aktion = self.menue_plus.addAction(wz.einsatzart_text(art))
            aktion.triggered.connect(lambda _an=False, a=art: self.einsatz_anlegen(a))

    def _fuellen(self):
        """Schreibt alle Zeilen neu; die gewählte Zeile bleibt gewählt."""
        zeile_vorher = self.tabelle.currentRow()
        self._fuellt = True
        self.tabelle.setRowCount(len(self._liste))
        for zeile, einsatz in enumerate(self._liste):
            self._zeile_schreiben(zeile, einsatz)
        self._fuellt = False
        self.knopf_minus.setEnabled(self._bearbeitbar and bool(self._liste))
        if self._liste:
            self.tabelle.setCurrentCell(max(0, min(zeile_vorher, len(self._liste) - 1)), EINSATZ)
        self._hinweise()

    def _zeile_schreiben(self, zeile, einsatz):
        teiler = self.werkzeug.schneiden if self._bohrer() else 1
        eingaben = {
            EINSATZ: wz.einsatz_name(einsatz),
            AE: zahl_zeigen(einsatz.ae),
            AP: zahl_zeigen(einsatz.ap),
            VC: zahl_zeigen(einsatz.vc),
            FZ: zahl_zeigen(round(einsatz.fz * teiler, 6)),
        }
        for spalte, text in eingaben.items():
            self.tabelle.setItem(zeile, spalte, self._zelle(text, bearbeitbar=self._bearbeitbar))
        self._ergebnis_schreiben(zeile, einsatz)

    def _ergebnis_schreiben(self, zeile, einsatz):
        n, vf, q = sd.rechne(self.werkzeug, einsatz)
        format_ = zahlenformat()
        for spalte, wert, stellen in ((N, n, 0), (VF, vf, 0), (Q, q, 1)):
            text = format_.toString(wert, "f", stellen) if wert else ""
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
        if self._fuellt or not self._bearbeitbar:
            return
        zeile, spalte = zelle.row(), zelle.column()
        einsatz = self._liste[zeile]
        text = zelle.text().strip()
        if spalte == EINSATZ:
            # Der Name der Art ist kein eigener Name – so folgt er der Sprache.
            einsatz.name = "" if text == wz.einsatzart_text(einsatz.art) else text
        elif spalte in EINGABE_SPALTEN:
            try:
                wert = zahl_lesen(text)
            except ValueError:
                wert = getattr(einsatz, EINGABE_SPALTEN[spalte])
            if spalte == FZ and self._bohrer():
                wert = wert / max(self.werkzeug.schneiden, 1)
            setattr(einsatz, EINGABE_SPALTEN[spalte], wert)
        self._fuellt = True
        self._zeile_schreiben(zeile, einsatz)
        self._fuellt = False
        self._geaendert()
        self._hinweise()

    def _hinweise(self):
        """Was an der gewählten Zeile nicht passt – sofort, als Satz."""
        einsatz = self.gewaehlt
        w = self.werkzeug
        saetze = []
        if einsatz is not None and w is not None and not self._bohrer():
            if w.durchmesser and einsatz.ae > w.durchmesser:
                saetze.append(tr("wv.hinweis.ae_zu_gross"))
            if w.schneidenlaenge and einsatz.ap > w.schneidenlaenge:
                saetze.append(
                    tr(
                        "wv.hinweis.ap_zu_gross",
                        ap=zahl_zeigen(einsatz.ap),
                        laenge=zahl_zeigen(w.schneidenlaenge),
                    )
                )
        if einsatz is not None and (not einsatz.vc or not einsatz.fz):
            saetze.append(tr("wv.hinweis.vc_fz_fehlen"))
        self.hinweis.setText("\n".join(saetze))
        self.hinweis.setVisible(bool(saetze))


class _Zahlendelegat(QtGui.QStyledItemDelegate):
    """Zahlenspalten bekommen beim Bearbeiten ein Feld, das nur Zahlen annimmt."""

    def createEditor(self, eltern, option, index):
        feld = super().createEditor(eltern, option, index)
        if index.column() in EINGABE_SPALTEN and isinstance(feld, QtGui.QLineEdit):
            feld.setValidator(Zahlenpruefer(feld))
        return feld


def _knopf(text, tooltip, aktion):
    knopf = QtGui.QPushButton(text)
    knopf.setToolTip(tooltip)
    knopf.setAutoDefault(False)
    knopf.clicked.connect(lambda: aktion())
    return knopf
