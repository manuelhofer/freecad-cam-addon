# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Fenster „Halter“ (W-002 Stufe D, spezifikation_halter.md, Abschnitt 5).

Aus der Werkzeugverwaltung heraus („Halter …“ beim Werkzeug): links die
Halter mit Suche, Neu (leer oder aus einer Vorlage), Kopieren und Löschen;
rechts Name, Bezeichnung, Spanntiefe und die Kontur als Tabelle der
Abschnitte (Länge, Ø oben, Ø unten), daneben der Halter im Schnitt mit dem
Werkzeug darunter, in den Farben des Werkzeugbilds. Gearbeitet wird an einer Kopie der Bibliothek: OK
übernimmt die Halter in die Werkzeugverwaltung und gibt dem Werkzeug den
gewählten Halter; Abbrechen verwirft alles. Gespeichert wird mit OK oder
Übernehmen der Werkzeugverwaltung – wie bei den Werkstoffen.
"""

import contextlib

from PySide import QtCore, QtGui

from . import einheiten
from . import halter as hl
from . import werkzeuge as wz
from .gui_eingriff import FARBE_KANTE, FARBE_SCHAFT, FARBE_WERKZEUG, FARBE_WERKZEUG_RAND
from .gui_hilfe import kopfzeile
from .gui_teile import GRAU, knopf, mit_einheit, ruhiges_mausrad
from .gui_zahlen import Zahlenpruefer, groesse_fest, groesse_lesen, groesse_zeigen
from .sprache import tr

FENSTER_GROESSE = (820, 520)  # Pixel
LAENGE, D_OBEN, D_UNTEN = range(3)  # Spalten der Kontur
FELDER = ("laenge", "d_oben", "d_unten")
NEUER_ABSCHNITT = 20.0  # mm lang, wenn man einen Abschnitt dazunimmt
BILD_BREITE, BILD_HOEHE = 130, 230  # Pixel
BILD_RAND = 8  # Pixel
SPINDEL_HOEHE = 14  # Pixel: das Stück Spindel über der Spindelnase
FARBE_HALTER = QtGui.QColor("#9aa3ab")
FARBE_HALTER_RAND = QtGui.QColor("#4d555c")
FARBE_SPINDEL = QtGui.QColor("#5c6670")


def _laenge(mm):
    """Eine Länge mit Einheit zum Lesen: „70,00 mm“."""
    return f"{groesse_fest(mm, einheiten.LAENGE, 2)} {einheiten.einheit(einheiten.LAENGE)}"


class HalterDialog(QtGui.QDialog):
    """Die Halter bearbeiten. `werkzeug`: das Werkzeug der Werkzeugverwaltung, aus dem heraus
    das Fenster geöffnet wurde – es bekommt mit OK den gewählten Halter."""

    offen = None  # für die Oberflächen-Szenarien

    def __init__(self, eltern, bibliothek, werkzeug=None):
        super().__init__(eltern)
        HalterDialog.offen = self
        self.original = bibliothek
        self.bibliothek = bibliothek.kopie()
        self.werkzeug = None
        if werkzeug is not None:
            self.werkzeug = next(
                (w for w in self.bibliothek.werkzeuge if w.kennung == werkzeug.kennung), None
            )
        self._gezeigt = []  # die Halter in der Liste, in ihrer Reihenfolge
        self._fuellt = False
        self.setWindowTitle(tr("hd.titel"))
        self.resize(*FENSTER_GROESSE)

        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(kopfzeile(tr("hd.titel"), "halter"))
        teilung = QtGui.QHBoxLayout()
        teilung.addLayout(self._bereich_liste(), 2)
        teilung.addLayout(self._bereich_halter(), 5)
        aufbau.addLayout(teilung, 1)
        self.ok_hinweis = QtGui.QLabel()
        self.ok_hinweis.setWordWrap(True)
        self.ok_hinweis.setStyleSheet(f"color: {GRAU.name()};")
        aufbau.addWidget(self.ok_hinweis)
        self.knoepfe = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
        )
        self.knoepfe.accepted.connect(self.accept)
        self.knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(self.knoepfe)
        ruhiges_mausrad(self)

        halter = self.bibliothek.halter_von(self.werkzeug) if self.werkzeug else None
        self._fuellen(auswahl=halter)

    # --- Aufbau -------------------------------------------------------------------------

    def _bereich_liste(self):
        aufbau = QtGui.QVBoxLayout()
        self.suche = QtGui.QLineEdit()
        self.suche.setPlaceholderText(tr("hd.suche.platzhalter"))
        self.suche.setClearButtonEnabled(True)
        self.suche.textChanged.connect(lambda _text: self._fuellen())
        aufbau.addWidget(self.suche)
        self.liste = QtGui.QListWidget()
        self.liste.currentRowChanged.connect(lambda _zeile: self._zeigen())
        aufbau.addWidget(self.liste, 1)
        zeile = QtGui.QHBoxLayout()
        self.knopf_neu = QtGui.QPushButton(tr("hd.neu"))
        self.knopf_neu.setToolTip(tr("hd.neu.tooltip"))
        self.knopf_neu.setAutoDefault(False)
        self.menue_neu = QtGui.QMenu(self.knopf_neu)
        self.menue_neu.addAction(tr("hd.neu.leer"), lambda: self.neu())
        self.menue_neu.addSeparator()
        for schluessel in hl.VORLAGEN:
            self.menue_neu.addAction(hl.vorlage_text(schluessel), lambda s=schluessel: self.neu(s))
        self.knopf_neu.setMenu(self.menue_neu)
        self.knopf_kopieren = knopf(tr("hd.kopieren"), tr("hd.kopieren.tooltip"), self.kopieren)
        self.knopf_loeschen = knopf(tr("hd.loeschen"), tr("hd.loeschen.tooltip"), self.loeschen)
        for element in (self.knopf_neu, self.knopf_kopieren, self.knopf_loeschen):
            zeile.addWidget(element)
        aufbau.addLayout(zeile)
        return aufbau

    def _bereich_halter(self):
        aufbau = QtGui.QVBoxLayout()
        self.leer = QtGui.QLabel(tr("hd.leer"))
        self.leer.setWordWrap(True)
        aufbau.addWidget(self.leer)
        self.rahmen = QtGui.QWidget()
        innen = QtGui.QVBoxLayout(self.rahmen)
        innen.setContentsMargins(0, 0, 0, 0)

        gitter = QtGui.QGridLayout()
        gitter.setColumnStretch(1, 1)
        self.feld_name = QtGui.QLineEdit()
        self.feld_name.setToolTip(tr("hd.name.tooltip"))
        self.feld_name.textEdited.connect(self._name_geaendert)
        self.feld_bezeichnung = QtGui.QLineEdit()
        self.feld_bezeichnung.setPlaceholderText(tr("wv.bezeichnung.platzhalter"))
        self.feld_bezeichnung.setToolTip(tr("hd.bezeichnung.tooltip"))
        self.feld_bezeichnung.textEdited.connect(self._bezeichnung_geaendert)
        self.feld_spanntiefe = QtGui.QLineEdit()
        self.feld_spanntiefe.setValidator(Zahlenpruefer(self.feld_spanntiefe))
        self.feld_spanntiefe.setToolTip(tr("hd.spanntiefe.tooltip"))
        self.feld_spanntiefe.editingFinished.connect(self._spanntiefe_uebernehmen)
        for reihe, (text, feld) in enumerate(
            (
                (tr("hd.name"), self.feld_name),
                (tr("hd.bezeichnung"), self.feld_bezeichnung),
                (
                    tr("hd.spanntiefe"),
                    mit_einheit(self.feld_spanntiefe, einheiten.einheit(einheiten.LAENGE)),
                ),
            )
        ):
            gitter.addWidget(QtGui.QLabel(text), reihe, 0)
            gitter.addWidget(feld, reihe, 1)
        innen.addLayout(gitter)

        kontur = QtGui.QLabel(tr("hd.kontur"))
        kontur.setToolTip(tr("hd.kontur.tooltip"))
        innen.addWidget(kontur)
        unten = QtGui.QHBoxLayout()
        links = QtGui.QVBoxLayout()
        einheit = einheiten.einheit(einheiten.LAENGE)
        self.tabelle = QtGui.QTableWidget(0, 3)
        self.tabelle.setHorizontalHeaderLabels(
            [
                tr("hd.spalte.laenge", einheit=einheit),
                tr("hd.spalte.d_oben", einheit=einheit),
                tr("hd.spalte.d_unten", einheit=einheit),
            ]
        )
        self.tabelle.horizontalHeader().setSectionResizeMode(QtGui.QHeaderView.Stretch)
        self.tabelle.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tabelle.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tabelle.setItemDelegate(_Zahlendelegat(self.tabelle))
        self.tabelle.setToolTip(tr("hd.kontur.tooltip"))
        self.tabelle.itemChanged.connect(self._zelle_geaendert)
        links.addWidget(self.tabelle, 1)
        zeile = QtGui.QHBoxLayout()
        self.knopf_dazu = knopf(
            tr("hd.abschnitt.dazu"), tr("hd.abschnitt.dazu.tooltip"), self.abschnitt_dazu
        )
        self.knopf_weg = knopf(
            tr("hd.abschnitt.weg"), tr("hd.abschnitt.weg.tooltip"), self.abschnitt_weg
        )
        zeile.addWidget(self.knopf_dazu)
        zeile.addWidget(self.knopf_weg)
        zeile.addStretch()
        links.addLayout(zeile)
        self.zusammenfassung = QtGui.QLabel()
        self.zusammenfassung.setWordWrap(True)
        links.addWidget(self.zusammenfassung)
        self.benutzt = QtGui.QLabel()
        self.benutzt.setWordWrap(True)
        self.benutzt.setStyleSheet(f"color: {GRAU.name()};")
        links.addWidget(self.benutzt)
        unten.addLayout(links, 1)
        self.bild = HalterBild()
        self.bild.setToolTip(tr("hd.bild.tooltip"))
        unten.addWidget(self.bild, 0, QtCore.Qt.AlignTop)
        innen.addLayout(unten, 1)
        aufbau.addWidget(self.rahmen, 1)
        return aufbau

    def keyPressEvent(self, ereignis):
        """Enter bestätigt nur das Feld, nicht das Fenster (wie in der Werkzeugverwaltung)."""
        if ereignis.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            ereignis.accept()  # das Feld hat seinen Wert schon übernommen
            return
        super().keyPressEvent(ereignis)

    # --- Liste --------------------------------------------------------------------------

    def _fuellen(self, auswahl=None):
        """Die Halter, die zur Suche passen, nach Namen; die Auswahl bleibt, wenn es geht."""
        vorher = auswahl or self.gewaehlt
        worte = self.suche.text().lower().split()
        self._gezeigt = [
            h
            for h in self.bibliothek.sortierte_halter()
            if all(wort in f"{hl.text(h)} {h.bezeichnung}".lower() for wort in worte)
        ]
        self.liste.blockSignals(True)
        self.liste.clear()
        for h in self._gezeigt:
            eintrag = QtGui.QListWidgetItem(hl.text(h))
            eintrag.setToolTip(
                tr(
                    "hd.liste.tooltip",
                    laenge=_laenge(h.laenge),
                    durchmesser=_laenge(h.groesster_durchmesser),
                )
            )
            self.liste.addItem(eintrag)
        if vorher in self._gezeigt:
            self.liste.setCurrentRow(self._gezeigt.index(vorher))
        elif self._gezeigt:
            self.liste.setCurrentRow(0)
        self.liste.blockSignals(False)
        self._zeigen()

    @property
    def gewaehlt(self):
        """Der gewählte Halter, oder None."""
        zeile = self.liste.currentRow()
        return self._gezeigt[zeile] if 0 <= zeile < len(self._gezeigt) else None

    def waehle(self, halter):
        """Wählt einen Halter (die Suche wird geleert)."""
        self.suche.blockSignals(True)
        self.suche.clear()
        self.suche.blockSignals(False)
        self._fuellen(auswahl=halter)

    def neu(self, vorlage=None):
        """Ein neuer Halter – leer oder aus einer Vorlage (halter.VORLAGEN)."""
        halter = self.bibliothek.neuer_halter(vorlage)
        if not halter.abschnitte:
            halter.abschnitte.append(hl.Abschnitt(NEUER_ABSCHNITT, 40.0, 40.0))
        self.waehle(halter)
        if vorlage is None:
            self.feld_name.setFocus()
        return halter

    def kopieren(self):
        if self.gewaehlt is not None:
            self.waehle(self.bibliothek.kopiere_halter(self.gewaehlt))

    def loeschen(self, fragen=True):
        """Löscht den gewählten Halter; benutzen ihn Werkzeuge, fragt es vorher."""
        halter = self.gewaehlt
        if halter is None:
            return
        werkzeuge = self.bibliothek.benutzt_von(halter)
        if werkzeuge and fragen:
            antwort = QtGui.QMessageBox.question(
                self,
                tr("hd.titel"),
                tr("hd.loeschen.frage", halter=hl.text(halter), werkzeuge=_nummern(werkzeuge)),
            )
            if antwort != QtGui.QMessageBox.Yes:
                return
        index = self._gezeigt.index(halter)
        self.bibliothek.entferne_halter(halter)
        self._fuellen()
        if self._gezeigt:
            self.liste.setCurrentRow(min(index, len(self._gezeigt) - 1))

    # --- Der gewählte Halter ------------------------------------------------------------

    def _zeigen(self):
        """Zeigt den gewählten Halter in den Feldern, der Tabelle und dem Bild."""
        h = self.gewaehlt
        self.leer.setVisible(h is None)
        self.rahmen.setVisible(h is not None)
        self.knopf_kopieren.setEnabled(h is not None)
        self.knopf_loeschen.setEnabled(h is not None)
        self._ok_hinweis()
        if h is None:
            return
        self._fuellt = True
        self.feld_name.setText(h.name)
        self.feld_name.setPlaceholderText(hl.text(hl.Halter(abschnitte=h.abschnitte)))
        self.feld_bezeichnung.setText(h.bezeichnung)
        self.feld_spanntiefe.setText(groesse_zeigen(h.spanntiefe, einheiten.LAENGE))
        self._tabelle_fuellen()
        self._fuellt = False
        self._neu_berechnet()

    def _tabelle_fuellen(self):
        h = self.gewaehlt
        zeile_vorher = self.tabelle.currentRow()
        self.tabelle.blockSignals(True)
        self.tabelle.setRowCount(len(h.abschnitte))
        for zeile, abschnitt in enumerate(h.abschnitte):
            for spalte, feld in enumerate(FELDER):
                zelle = QtGui.QTableWidgetItem(
                    groesse_zeigen(getattr(abschnitt, feld), einheiten.LAENGE)
                )
                zelle.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.tabelle.setItem(zeile, spalte, zelle)
        self.tabelle.blockSignals(False)
        if h.abschnitte:
            self.tabelle.setCurrentCell(min(max(zeile_vorher, 0), len(h.abschnitte) - 1), LAENGE)

    def _neu_berechnet(self):
        """Nach jeder Änderung: Zusammenfassung, wer ihn benutzt, das Bild, die Liste."""
        h = self.gewaehlt
        if h is None:
            return
        self.zusammenfassung.setText(
            tr(
                "hd.zusammenfassung",
                laenge=_laenge(h.laenge),
                durchmesser=_laenge(h.groesster_durchmesser),
            )
        )
        werkzeuge = self.bibliothek.benutzt_von(h)
        self.benutzt.setText(
            tr("hd.benutzt", werkzeuge=_nummern(werkzeuge)) if werkzeuge else tr("hd.unbenutzt")
        )
        self.knopf_weg.setEnabled(len(h.abschnitte) > 1)
        werkzeug = self.werkzeug if self.werkzeug is not None else _beispielwerkzeug(werkzeuge)
        laenge = 0.0
        if werkzeug is not None:
            laenge = werkzeug.laenge_spindelnase or wz.laenge_mit_halter(werkzeug, h)
        self.bild.zeige(h, werkzeug, laenge)
        zeile = self._gezeigt.index(h)
        eintrag = self.liste.item(zeile)
        if eintrag is not None:
            eintrag.setText(hl.text(h))
        self._ok_hinweis()

    def _ok_hinweis(self):
        """Grau über OK: was OK mit dem Werkzeug macht."""
        if self.werkzeug is None:
            self.ok_hinweis.hide()
            return
        h = self.gewaehlt
        nummer = f"T{self.werkzeug.nummer}"
        if h is None:
            text = tr("hd.ok.ohne", werkzeug=nummer)
        else:
            text = tr("hd.ok.halter", werkzeug=nummer, halter=hl.text(h))
        self.ok_hinweis.setText(text)
        self.ok_hinweis.show()

    def _name_geaendert(self, text):
        if self._fuellt or self.gewaehlt is None:
            return
        self.gewaehlt.name = text
        self._neu_berechnet()

    def _bezeichnung_geaendert(self, text):
        if not self._fuellt and self.gewaehlt is not None:
            self.gewaehlt.bezeichnung = text

    def _spanntiefe_uebernehmen(self):
        h = self.gewaehlt
        if self._fuellt or h is None:
            return
        h.spanntiefe = groesse_lesen(self.feld_spanntiefe.text(), einheiten.LAENGE)
        self.feld_spanntiefe.setText(groesse_zeigen(h.spanntiefe, einheiten.LAENGE))
        self._neu_berechnet()

    def _zelle_geaendert(self, zelle):
        """Eine Zahl in der Kontur: übernehmen, schön zeigen, neu zeichnen."""
        h = self.gewaehlt
        if self._fuellt or h is None or not 0 <= zelle.row() < len(h.abschnitte):
            return
        abschnitt = h.abschnitte[zelle.row()]
        feld = FELDER[zelle.column()]
        with contextlib.suppress(ValueError):  # Unlesbares: bleibt, wie es war
            setattr(abschnitt, feld, groesse_lesen(zelle.text(), einheiten.LAENGE))
        self.tabelle.blockSignals(True)
        zelle.setText(groesse_zeigen(getattr(abschnitt, feld), einheiten.LAENGE))
        self.tabelle.blockSignals(False)
        self._neu_berechnet()

    def abschnitt_dazu(self):
        """Ein Abschnitt unter dem gewählten – so dick, wie der gewählte unten ist."""
        h = self.gewaehlt
        if h is None:
            return
        zeile = self.tabelle.currentRow()
        zeile = zeile if 0 <= zeile < len(h.abschnitte) else len(h.abschnitte) - 1
        d = h.abschnitte[zeile].d_unten if h.abschnitte else 40.0
        h.abschnitte.insert(zeile + 1, hl.Abschnitt(NEUER_ABSCHNITT, d, d))
        self._fuellt = True
        self._tabelle_fuellen()
        self._fuellt = False
        self.tabelle.setCurrentCell(zeile + 1, LAENGE)
        self._neu_berechnet()

    def abschnitt_weg(self):
        """Nimmt den gewählten Abschnitt weg – einer bleibt immer."""
        h = self.gewaehlt
        zeile = self.tabelle.currentRow()
        if h is None or len(h.abschnitte) <= 1 or not 0 <= zeile < len(h.abschnitte):
            return
        del h.abschnitte[zeile]
        self._fuellt = True
        self._tabelle_fuellen()
        self._fuellt = False
        self._neu_berechnet()

    # --- OK und Abbrechen ---------------------------------------------------------------

    def accept(self):
        """Übernimmt die Halter in die Werkzeugverwaltung; das Werkzeug bekommt den gewählten."""
        self._spanntiefe_uebernehmen()
        self.original.halter = self.bibliothek.halter
        halter_je_werkzeug = {w.kennung: w.halter for w in self.bibliothek.werkzeuge}
        for werkzeug in self.original.werkzeuge:
            werkzeug.halter = halter_je_werkzeug.get(werkzeug.kennung, werkzeug.halter)
        if self.werkzeug is not None:
            original = next(
                (w for w in self.original.werkzeuge if w.kennung == self.werkzeug.kennung), None
            )
            if original is not None:
                original.halter = self.gewaehlt.kennung if self.gewaehlt is not None else ""
        HalterDialog.offen = None
        super().accept()

    def reject(self):
        HalterDialog.offen = None
        super().reject()


def _nummern(werkzeuge):
    """„T3, T7“."""
    return ", ".join(f"T{w.nummer}" for w in werkzeuge)


def _beispielwerkzeug(werkzeuge):
    """Das Werkzeug fürs Bild, wenn das Fenster ohne Werkzeug offen ist: das erste, das den
    Halter benutzt – oder keins."""
    return werkzeuge[0] if werkzeuge else None


class _Zahlendelegat(QtGui.QStyledItemDelegate):
    """Die Zellen der Kontur nehmen beim Bearbeiten nur Zahlen an."""

    def createEditor(self, eltern, option, index):
        feld = super().createEditor(eltern, option, index)
        if isinstance(feld, QtGui.QLineEdit):
            feld.setValidator(Zahlenpruefer(feld))
        return feld


class HalterBild(QtGui.QWidget):
    """Der Halter im Schnitt, maßstäblich: oben die Spindel, darunter die Kontur, unter der
    Nase des Halters das Werkzeug bis zur Spitze (Schaft grau, Schneide blau – wie im Bild
    des Werkzeugs)."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(BILD_BREITE, BILD_HOEHE)
        self.halter = None
        self.werkzeug = None
        self.laenge = 0.0

    def zeige(self, halter, werkzeug=None, laenge=0.0):
        """`laenge`: von der Spindelnase bis zur Spitze des Werkzeugs, mm (0 = ohne Werkzeug)."""
        self.halter, self.werkzeug, self.laenge = halter, werkzeug, laenge
        self.update()

    def paintEvent(self, _ereignis):
        maler = QtGui.QPainter(self)
        maler.setRenderHint(QtGui.QPainter.Antialiasing)
        maler.fillRect(self.rect(), self.palette().color(QtGui.QPalette.Base))
        h = self.halter
        if h is not None and h.kontur():
            self._zeichne(maler, h)
        maler.end()

    def _zeichne(self, maler, h):
        w = self.werkzeug if self.laenge > h.laenge else None
        tiefe = max(h.laenge, self.laenge if w is not None else 0.0)
        breite = max(h.groesster_durchmesser, (w.durchmesser if w is not None else 0.0), 1.0)
        platz_x = self.width() - 2 * BILD_RAND
        platz_y = self.height() - 2 * BILD_RAND - SPINDEL_HOEHE
        s = min(platz_x / breite, platz_y / max(tiefe, 1.0))
        mitte = self.width() / 2
        nase = BILD_RAND + SPINDEL_HOEHE  # y der Spindelnase

        # Die Spindel über der Spindelnase, etwas breiter als der Halter.
        halb = h.groesster_durchmesser * s / 2 + 4
        maler.setPen(QtCore.Qt.NoPen)
        maler.setBrush(FARBE_SPINDEL)
        maler.drawRect(QtCore.QRectF(mitte - halb, BILD_RAND, 2 * halb, SPINDEL_HOEHE))

        # Das Werkzeug unter der Nase des Halters – zuerst, der Halter liegt darüber.
        if w is not None:
            spitze = nase + self.laenge * s
            schneide = min(wz.mass(w, "schneidenlaenge") or 2 * w.durchmesser, self.laenge)
            schaft = wz.schaft_fuer_cam(w) or w.durchmesser
            oben = nase + h.laenge * s
            if spitze - schneide * s > oben:
                self._rechteck(
                    maler, mitte, schaft * s, oben, spitze - schneide * s, FARBE_SCHAFT, FARBE_KANTE
                )
            unten = max(oben, spitze - schneide * s)
            self._rechteck(
                maler, mitte, w.durchmesser * s, unten, spitze, FARBE_WERKZEUG, FARBE_WERKZEUG_RAND
            )

        # Der Halter: rechts die Kontur von oben nach unten, links zurück.
        rechts = [QtCore.QPointF(mitte + r * s, nase + a * s) for a, r in h.kontur()]
        links = [QtCore.QPointF(2 * mitte - p.x(), p.y()) for p in reversed(rechts)]
        maler.setPen(QtGui.QPen(FARBE_HALTER_RAND, 1.2))
        maler.setBrush(FARBE_HALTER)
        maler.drawPolygon(QtGui.QPolygonF(rechts + links))

        # Die Spindelnase als Strich.
        maler.setPen(QtGui.QPen(FARBE_SPINDEL, 1.5))
        maler.drawLine(QtCore.QPointF(mitte - halb, nase), QtCore.QPointF(mitte + halb, nase))

    @staticmethod
    def _rechteck(maler, mitte, breite, oben, unten, fuellung, rand):
        maler.setPen(QtGui.QPen(rand, 1.0))
        maler.setBrush(fuellung)
        maler.drawRect(QtCore.QRectF(mitte - breite / 2, oben, breite, unten - oben))
