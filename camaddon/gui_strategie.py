# SPDX-License-Identifier: LGPL-2.1-or-later
"""Dialog „Strategien vergleichen“ (W-002, Spezifikation Abschnitt 7).

Zwei Einsätze desselben Werkzeugs nebeneinander: Abtrag, Zeit, Schneidenweg
je cm³ (Verschleiß), genutzte Schneide, Eingriff, Spandicke, Leistung – jede
Zahl mit einem Balken, darunter das Urteil in Sätzen. Ganz unten alle
Einsätze der Tabelle auf einen Blick, das Beste je Spalte fett; ein Klick
nimmt die Zeile als B. Gerechnet wird in schnittdaten.py.
"""

from PySide import QtCore, QtGui

from . import einheiten
from . import schnittdaten as sd
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_teile import ruhiges_mausrad
from .gui_zahlen import dezimal, groesse_fest, groesse_zeigen, zahl_zeigen, zahlenformat
from .sprache import tr

FARBE_A = QtGui.QColor("#e67e22")
FARBE_B = QtGui.QColor("#2e86c1")
BALKEN_BREITE, BALKEN_HOEHE = 170, 14  # Pixel
FENSTER_BREITE = 760  # Pixel

# Spalten der Übersicht aller Einsätze.
UE_NAME, UE_Q, UE_ZEIT, UE_WEG, UE_AP, UE_EINGRIFF, UE_SPAN, UE_LEISTUNG = range(8)


def _wert_text(wert, stellen, groesse):
    """Eine Zelle der Übersicht: mit Größe im gewählten Maßsystem."""
    if groesse is None:
        return zahl_zeigen(wert) if stellen is None else _zahl(wert, stellen)
    if stellen is None:
        return groesse_zeigen(wert, groesse)
    return groesse_fest(wert, groesse, stellen)


def _mit_einheit(wert, stellen, groesse):
    """„22,9 cm³/min“ bzw. „1,40 in³/min“."""
    return f"{groesse_fest(wert, groesse, stellen)} {einheiten.einheit(groesse)}"


def _zahl(wert, stellen):
    return zahlenformat().toString(float(wert), "f", stellen)


class Balken(QtGui.QWidget):
    """Ein waagrechter Balken: `anteil` 0 … 1 der vollen Breite, in `farbe`."""

    def __init__(self, farbe):
        super().__init__()
        self.farbe = farbe
        self.anteil = 0.0
        self.setFixedSize(BALKEN_BREITE, BALKEN_HOEHE)

    def setze(self, anteil):
        self.anteil = max(0.0, min(anteil, 1.0))
        self.update()

    def paintEvent(self, _ereignis):
        maler = QtGui.QPainter(self)
        maler.fillRect(self.rect(), self.palette().color(QtGui.QPalette.AlternateBase))
        breite = int(self.width() * self.anteil)
        if breite > 0:
            maler.fillRect(0, 0, breite, self.height(), self.farbe)
        maler.end()


class StrategieDialog(QtGui.QDialog):
    """Vergleicht zwei Einsätze; `vergleiche(a, b)` wählt sie (Zeilennummern)."""

    offen = None  # das zuletzt geöffnete Fenster – für die Oberflächen-Szenarien

    def __init__(self, eltern, werkzeug, einsaetze, werkstoff, werkstoff_text):
        super().__init__(eltern)
        StrategieDialog.offen = self
        self.werkzeug = werkzeug
        self.einsaetze = einsaetze
        self.werkstoff = werkstoff
        self.setWindowTitle(tr("wv.strategie.titel"))
        self.setMinimumWidth(FENSTER_BREITE)

        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(kopfzeile(tr("wv.strategie.titel"), "strategien"))
        self.kopf = QtGui.QLabel(
            tr("wv.strategie.kopf", werkzeug=dezimal(wz.zeile(werkzeug)), werkstoff=werkstoff_text)
        )
        self.kopf.setWordWrap(True)
        aufbau.addWidget(self.kopf)

        wahl = QtGui.QHBoxLayout()
        self.wahl_a = self._wahl(FARBE_A, "A", wahl)
        wahl.addWidget(QtGui.QLabel(tr("wv.strategie.gegen")))
        self.wahl_b = self._wahl(FARBE_B, "B", wahl)
        wahl.addStretch()
        aufbau.addLayout(wahl)

        self.gitter = QtGui.QGridLayout()
        self.gitter.setHorizontalSpacing(10)
        self._zeilen = {}
        for zeile, (schluessel, text, tooltip) in enumerate(self._kennzahlen()):
            beschriftung = QtGui.QLabel(text)
            beschriftung.setToolTip(tooltip)
            self.gitter.addWidget(beschriftung, zeile, 0)
            balken_a, wert_a = Balken(FARBE_A), QtGui.QLabel()
            balken_b, wert_b = Balken(FARBE_B), QtGui.QLabel()
            for spalte, widget in enumerate((balken_a, wert_a, balken_b, wert_b), start=1):
                self.gitter.addWidget(widget, zeile, spalte)
            self._zeilen[schluessel] = (balken_a, wert_a, balken_b, wert_b)
        aufbau.addLayout(self.gitter)

        self.urteil = QtGui.QLabel()
        self.urteil.setWordWrap(True)
        self.urteil.setTextFormat(QtCore.Qt.RichText)
        self.urteil.setFrameShape(QtGui.QFrame.StyledPanel)
        self.urteil.setMargin(8)
        aufbau.addWidget(self.urteil)

        aufbau.addWidget(QtGui.QLabel(f"<b>{tr('wv.strategie.alle')}</b>"))
        self.uebersicht = self._baue_uebersicht()
        aufbau.addWidget(self.uebersicht)

        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Close)
        knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(knoepfe)
        ruhiges_mausrad(self)

        a, b = _vorwahl(einsaetze)
        self.wahl_a.currentIndexChanged.connect(self._rechnen)
        self.wahl_b.currentIndexChanged.connect(self._rechnen)
        self.vergleiche(a, b)

    def _wahl(self, farbe, buchstabe, zeile):
        marke = QtGui.QLabel(f" {buchstabe} ")
        marke.setStyleSheet(
            f"background: {farbe.name()}; color: white; font-weight: bold; border-radius: 3px;"
        )
        zeile.addWidget(marke)
        wahl = QtGui.QComboBox()
        for einsatz in self.einsaetze:
            wahl.addItem(wz.einsatz_name(einsatz))
        zeile.addWidget(wahl)
        return wahl

    def _baue_uebersicht(self):
        """Alle Einsätze mit ihren Kennzahlen; das Beste je Spalte fett."""
        tabelle = QtGui.QTableWidget(len(self.einsaetze), 8)
        tabelle.verticalHeader().hide()
        tabelle.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        tabelle.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        tabelle.setToolTip(tr("wv.strategie.alle.tooltip"))
        koepfe = [
            (tr("wv.spalte.einsatz"), ""),
            ("Q\n" + einheiten.einheit(einheiten.ABTRAG), tr("wv.strategie.q.tooltip")),
            (tr("wv.strategie.alle.zeit"), tr("wv.strategie.zeit.tooltip")),
            (tr("wv.strategie.alle.weg"), tr("wv.strategie.weg.tooltip")),
            (tr("wv.strategie.alle.ap"), tr("wv.strategie.ap.tooltip")),
            (tr("wv.strategie.alle.eingriff"), tr("wv.strategie.eingriff.tooltip")),
            (tr("wv.strategie.alle.span"), tr("wv.strategie.span.tooltip")),
            ("P\nkW", tr("wv.strategie.leistung.tooltip")),
        ]
        for spalte, (text, tooltip) in enumerate(koepfe):
            kopf = QtGui.QTableWidgetItem(text)
            kopf.setToolTip(tooltip)
            tabelle.setHorizontalHeaderItem(spalte, kopf)
        kopfleiste = tabelle.horizontalHeader()
        kopfleiste.setSectionResizeMode(QtGui.QHeaderView.ResizeToContents)
        kopfleiste.setSectionResizeMode(UE_NAME, QtGui.QHeaderView.Stretch)

        kennzahlen = [sd.kennzahlen(self.werkzeug, e, self.werkstoff) for e in self.einsaetze]
        # Spalte: (Wert, Nachkommastellen oder None, das Beste, Größe für mm/inch oder None).
        spalten = {
            UE_Q: (lambda k: k.q, 1, max, einheiten.ABTRAG),
            UE_ZEIT: (lambda k: k.zeit, 1, min, None),
            UE_WEG: (lambda k: k.schneidenweg, 2, min, einheiten.WEG_JE_VOLUMEN),
            UE_AP: (lambda k: k.ap, None, max, einheiten.LAENGE),
            UE_EINGRIFF: (lambda k: k.eingriff * 100, 0, None, None),
            UE_SPAN: (lambda k: k.spandicke, 3, None, einheiten.SPAN),
            UE_LEISTUNG: (lambda k: k.leistung, 1, None, None),
        }
        for zeile, (einsatz, k) in enumerate(zip(self.einsaetze, kennzahlen, strict=True)):
            tabelle.setItem(zeile, UE_NAME, QtGui.QTableWidgetItem(wz.einsatz_name(einsatz)))
            for spalte, (wert, stellen, _bestes, groesse) in spalten.items():
                w = wert(k)
                text = "" if not w else _wert_text(w, stellen, groesse)
                zelle = QtGui.QTableWidgetItem(text)
                zelle.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                tabelle.setItem(zeile, spalte, zelle)
        # Das Beste je Spalte fett – nur unter Einsätzen mit Werten.
        for spalte, (wert, _stellen, bestes, _groesse) in spalten.items():
            werte = [wert(k) for k in kennzahlen if wert(k)]
            if bestes is None or len(werte) < 2:
                continue
            ziel = bestes(werte)
            for zeile, k in enumerate(kennzahlen):
                if wert(k) and abs(wert(k) - ziel) < 1e-9:
                    zelle = tabelle.item(zeile, spalte)
                    schrift = zelle.font()
                    schrift.setBold(True)
                    zelle.setFont(schrift)
        tabelle.setColumnHidden(UE_LEISTUNG, not any(k.leistung for k in kennzahlen))
        hoehe = tabelle.horizontalHeader().sizeHint().height() + 2
        hoehe += sum(tabelle.rowHeight(z) for z in range(tabelle.rowCount()))
        tabelle.setFixedHeight(min(hoehe + 2, 260))
        tabelle.cellClicked.connect(lambda zeile, _spalte: self.als_b(zeile))
        return tabelle

    def als_b(self, zeile):
        """Nimmt eine Zeile der Übersicht als B; war sie A, tauschen A und B."""
        a, b = self.wahl_a.currentIndex(), self.wahl_b.currentIndex()
        if zeile == a:
            self.vergleiche(b, zeile)
        else:
            self.vergleiche(a, zeile)

    def _uebersicht_markieren(self):
        """Färbt in der Übersicht die Namen von A und B wie ihre Balken."""
        a, b = self.wahl_a.currentIndex(), self.wahl_b.currentIndex()
        for zeile in range(self.uebersicht.rowCount()):
            zelle = self.uebersicht.item(zeile, UE_NAME)
            farbe = FARBE_A if zeile == a else FARBE_B if zeile == b else None
            if farbe is None:
                zelle.setBackground(QtGui.QBrush())
                zelle.setForeground(QtGui.QBrush())
            else:
                zelle.setBackground(farbe)
                zelle.setForeground(QtGui.QColor("white"))

    def _kennzahlen(self):
        """(Schlüssel, Beschriftung, Tooltip) der Zeilen, in Anzeigereihenfolge."""
        return [
            ("q", tr("wv.strategie.q"), tr("wv.strategie.q.tooltip")),
            ("zeit", tr("wv.strategie.zeit"), tr("wv.strategie.zeit.tooltip")),
            ("weg", tr("wv.strategie.weg"), tr("wv.strategie.weg.tooltip")),
            ("ap", tr("wv.strategie.ap"), tr("wv.strategie.ap.tooltip")),
            ("eingriff", tr("wv.strategie.eingriff"), tr("wv.strategie.eingriff.tooltip")),
            ("span", tr("wv.strategie.span"), tr("wv.strategie.span.tooltip")),
            ("leistung", tr("wv.strategie.leistung"), tr("wv.strategie.leistung.tooltip")),
        ]

    def vergleiche(self, a, b):
        """Wählt die Einsätze mit den Zeilennummern `a` und `b` und rechnet."""
        for wahl, zeile in ((self.wahl_a, a), (self.wahl_b, b)):
            wahl.blockSignals(True)
            wahl.setCurrentIndex(zeile)
            wahl.blockSignals(False)
        self._rechnen()

    def _rechnen(self, *_):
        ea = self.einsaetze[self.wahl_a.currentIndex()]
        eb = self.einsaetze[self.wahl_b.currentIndex()]
        self.a = sd.kennzahlen(self.werkzeug, ea, self.werkstoff)
        self.b = sd.kennzahlen(self.werkzeug, eb, self.werkstoff)
        a, b = self.a, self.b
        lc = self.werkzeug.schneidenlaenge
        werte = {
            "q": (a.q, b.q, lambda k: _mit_einheit(k.q, 1, einheiten.ABTRAG)),
            "zeit": (a.zeit, b.zeit, lambda k: f"{_zahl(k.zeit, 1)} min"),
            "weg": (
                a.schneidenweg,
                b.schneidenweg,
                lambda k: _mit_einheit(k.schneidenweg, 2, einheiten.WEG_JE_VOLUMEN),
            ),
            "ap": (a.ap, b.ap, self._schneide_text),
            "eingriff": (a.eingriff, b.eingriff, lambda k: f"{_zahl(k.eingriff * 100, 0)} %"),
            "span": (
                a.spandicke,
                b.spandicke,
                lambda k: _mit_einheit(k.spandicke, 3, einheiten.SPAN),
            ),
            "leistung": (a.leistung, b.leistung, self._leistung_text),
        }
        for schluessel, (wert_a, wert_b, text) in werte.items():
            balken_a, feld_a, balken_b, feld_b = self._zeilen[schluessel]
            groesste = max(wert_a, wert_b, lc if schluessel == "ap" else 0)
            balken_a.setze(wert_a / groesste if groesste else 0)
            balken_b.setze(wert_b / groesste if groesste else 0)
            feld_a.setText(text(a) if wert_a else "–")
            feld_b.setText(text(b) if wert_b else "–")
        self.urteil.setText(self._urteil_text(ea, eb))
        self._uebersicht_markieren()

    def _schneide_text(self, k):
        if k.schneidenlaenge:
            return tr(
                "wv.strategie.ap.von",
                ap=groesse_zeigen(k.ap, einheiten.LAENGE),
                laenge=groesse_zeigen(k.schneidenlaenge, einheiten.LAENGE),
            )
        return f"{groesse_zeigen(k.ap, einheiten.LAENGE)} {einheiten.einheit(einheiten.LAENGE)}"

    def _leistung_text(self, k):
        return f"{_zahl(k.leistung, 1)} kW · {_zahl(k.drehmoment, 0)} Nm"

    def _urteil_text(self, ea, eb):
        """Die Sätze des Urteils; die Namen tragen die Farbe ihres Balkens."""
        name_a, name_b = wz.einsatz_name(ea), wz.einsatz_name(eb)
        if name_a == name_b:
            name_a, name_b = f"{name_a} A", f"{name_b} B"
        farbig = {
            name_a: f'<b style="color:{FARBE_A.name()}">{name_a}</b>',
            name_b: f'<b style="color:{FARBE_B.name()}">{name_b}</b>',
        }
        saetze = []
        for schluessel, werte in sd.urteil(self.a, self.b, name_a, name_b):
            gezeigt = {}
            for name, wert in werte.items():
                if isinstance(wert, str):
                    gezeigt[name] = farbig.get(wert, wert)
                elif name == "faktor":
                    gezeigt[name] = _zahl(wert, 1)
                elif name.startswith("anteil"):
                    gezeigt[name] = _zahl(wert, 0)
                elif name == "h":
                    gezeigt[name] = groesse_fest(wert, einheiten.SPAN, 3)
                elif name.startswith("ap"):
                    gezeigt[name] = groesse_zeigen(wert, einheiten.LAENGE)
                else:
                    gezeigt[name] = _zahl(wert, 1)
            saetze.append(_urteil_satz(schluessel, gezeigt))
        return " ".join(saetze)


def _urteil_satz(schluessel, werte):
    """Ein Satz des Urteils – die Schlüssel stehen hier als fester Text (test_sprache)."""
    return {
        "wv.urteil.unvollstaendig": lambda: tr("wv.urteil.unvollstaendig"),
        "wv.urteil.q_gleich": lambda: tr("wv.urteil.q_gleich"),
        "wv.urteil.q": lambda: tr("wv.urteil.q", **werte),
        "wv.urteil.weg_weniger": lambda: tr("wv.urteil.weg_weniger", **werte),
        "wv.urteil.weg_mehr": lambda: tr("wv.urteil.weg_mehr", **werte),
        "wv.urteil.ap": lambda: tr("wv.urteil.ap", **werte),
        "wv.urteil.eingriff": lambda: tr("wv.urteil.eingriff", **werte),
        "wv.urteil.leistung": lambda: tr("wv.urteil.leistung", **werte),
        "wv.urteil.span_duenn": lambda: tr("wv.urteil.span_duenn", **werte),
    }[schluessel]()


def _vorwahl(einsaetze):
    """A und B beim Öffnen: Vollnut gegen dynamisches Schruppen, sonst die ersten beiden."""
    arten = [e.art for e in einsaetze]
    a = arten.index(wz.VOLLNUT) if wz.VOLLNUT in arten else 0
    if wz.DYNAMISCH in arten and arten.index(wz.DYNAMISCH) != a:
        b = arten.index(wz.DYNAMISCH)
    else:
        b = 1 if a == 0 else 0
    return a, b
