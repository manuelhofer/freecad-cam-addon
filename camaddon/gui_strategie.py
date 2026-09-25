# SPDX-License-Identifier: LGPL-2.1-or-later
"""Dialog „Strategien vergleichen“ (W-002, Spezifikation Abschnitt 7).

Zwei Einsätze desselben Werkzeugs nebeneinander: Abtrag, Zeit, Schneidenweg
je cm³ (Verschleiß), genutzte Schneide, Eingriff, Spandicke, Leistung – jede
Zahl mit einem Balken, darunter das Urteil in Sätzen. Gerechnet wird in
schnittdaten.py.
"""

from PySide import QtCore, QtGui

from . import schnittdaten as sd
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_zahlen import dezimal, zahl_zeigen, zahlenformat
from .sprache import tr

FARBE_A = QtGui.QColor("#e67e22")
FARBE_B = QtGui.QColor("#2e86c1")
BALKEN_BREITE, BALKEN_HOEHE = 170, 14  # Pixel
FENSTER_BREITE = 760  # Pixel


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

        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Close)
        knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(knoepfe)

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
            "q": (a.q, b.q, lambda k: f"{_zahl(k.q, 1)} cm³/min"),
            "zeit": (a.zeit, b.zeit, lambda k: f"{_zahl(k.zeit, 1)} min"),
            "weg": (a.schneidenweg, b.schneidenweg, lambda k: f"{_zahl(k.schneidenweg, 2)} m"),
            "ap": (a.ap, b.ap, self._schneide_text),
            "eingriff": (a.eingriff, b.eingriff, lambda k: f"{_zahl(k.eingriff * 100, 0)} %"),
            "span": (a.spandicke, b.spandicke, lambda k: f"{_zahl(k.spandicke, 3)} mm"),
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

    def _schneide_text(self, k):
        if k.schneidenlaenge:
            return tr(
                "wv.strategie.ap.von", ap=zahl_zeigen(k.ap), laenge=zahl_zeigen(k.schneidenlaenge)
            )
        return f"{zahl_zeigen(k.ap)} mm"

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
                    gezeigt[name] = _zahl(wert, 3)
                elif name.startswith("ap"):
                    gezeigt[name] = zahl_zeigen(wert)
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
