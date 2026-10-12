# SPDX-License-Identifier: LGPL-2.1-or-later
"""Ein Zeichen, dass noch gerechnet wird – in den Assistenten „Bearbeitung“ und „4-Achs-Bearbeitung“.

Manuel (2026-10-12, am Geist im 4-Achs-Assistenten): „bis die gelbe Schrift erscheint, dauert es
ein bisschen … man bekommt keine Indikation dafür, dass noch gearbeitet wird … einfach nur irgend
einen Indikator, vielleicht auch einfach ein Rädchen, was erscheint und sich dreht, wenn noch
was gerechnet wird“.

`Anzeige` fragt im Takt, ob der Assistent noch rechnet (eine Funktion, die er mitgibt): Solange
ja, steht oben im Fenster ein Zeichen, das sich dreht, mit „rechnet …“, und unten in der
Statusleiste von FreeCAD ein Balken ohne Ende – die ist immer zu sehen, auch wenn das Fenster
weiter unten steht –, und neben „Anlegen“ oben und unten dreht sich ein Rad, „Anlegen“ ist so lange
grau (Manuel, 2026-10-12: „Anlegen oben und unten sollte ausgegraut werden, solange“).
"""

import FreeCADGui
from PySide import QtCore, QtGui

from . import farben
from .sprache import tr

ZEICHEN = "◐◓◑◒"
TAKT_MS = 100
RAD_SCHRITT = 36  # Grad je Takt – eine Umdrehung in einer Sekunde
ERST_NACH_MS = 300  # so lange muss es rechnen, bevor das Zeichen erscheint – kein Flackern


class Rad(QtGui.QWidget):
    """Ein Kreis, der sich dreht, solange gerechnet wird – ein Bogen, der umläuft, neben
    „Anlegen“ (Manuel, 2026-10-12: „der Streifen unten rechts ist zu unauffällig … neben Anlegen
    ein sich drehender Kreis, damit man es sehen kann, wenn man auf Anlegen klicken will“)."""

    def __init__(self, groesse=20):
        super().__init__()
        self.setFixedSize(groesse, groesse)
        self.setToolTip(tr("re.rechnet.tooltip"))
        self._winkel = 0
        self.hide()

    def weiter(self):
        self._winkel = (self._winkel + RAD_SCHRITT) % 360
        self.update()

    def paintEvent(self, _ereignis):  # noqa: N802 – Qt
        maler = QtGui.QPainter(self)
        maler.setRenderHint(QtGui.QPainter.Antialiasing)
        stift = QtGui.QPen(self.palette().color(QtGui.QPalette.Highlight))
        stift.setWidth(3)
        stift.setCapStyle(QtCore.Qt.RoundCap)
        maler.setPen(stift)
        maler.drawArc(self.rect().adjusted(3, 3, -3, -3), -self._winkel * 16, 270 * 16)
        maler.end()


class Anzeige:
    """Das Zeichen im Etikett `etikett` (ein QLabel im Fenster, anfangs verborgen), die Räder
    (rad()) und der Balken in der Statusleiste, solange `laeuft()` wahr ist; `bei_wechsel()`,
    wenn es zu rechnen beginnt oder aufhört (der Assistent sperrt dann „Anlegen“ – `an`).
    `ende()` beim Schließen des Fensters."""

    def __init__(self, etikett, laeuft, bei_wechsel=None):
        self.etikett = etikett
        self.laeuft = laeuft
        self.bei_wechsel = bei_wechsel
        self.an = False
        self._raeder = []
        self._zeichen = 0
        self._seit = 0
        self._balken = None
        etikett.setStyleSheet(f"color: {farben.GRAU};")
        etikett.hide()
        self._uhr = QtCore.QTimer()
        self._uhr.setInterval(TAKT_MS)
        self._uhr.timeout.connect(self._takt)
        self._uhr.start()

    def _takt(self):
        try:
            self._takt_zeigen()
        except RuntimeError:  # das Fenster ist weg (ohne „Abbrechen“ zu): nicht weiter ticken
            self.ende()

    def _takt_zeigen(self):
        try:
            an = bool(self.laeuft())
        except Exception:  # noqa: BLE001 – ein Fehler hier darf das Fenster nicht stören
            an = False
        self._seit = self._seit + TAKT_MS if an else 0
        if an and self._seit >= ERST_NACH_MS:
            self._zeichen = (self._zeichen + 1) % len(ZEICHEN)
            self.etikett.setText(f"{ZEICHEN[self._zeichen]}  {tr('re.rechnet')}")
            self.etikett.setToolTip(tr("re.rechnet.tooltip"))
            self.etikett.show()
            for rad in self._raeder:
                rad.show()
                rad.weiter()
            self._balken_zeigen(True)
            self._wechsel(True)
        elif not an:
            self.etikett.hide()
            for rad in self._raeder:
                rad.hide()
            self._balken_zeigen(False)
            self._wechsel(False)

    def _wechsel(self, an):
        if an != self.an:
            self.an = an
            if self.bei_wechsel is not None:
                self.bei_wechsel()

    def rad(self, rad=None):
        """Ein Rad (für neben „Anlegen“), das mit dieser Anzeige dreht – ein neues oder `rad`."""
        rad = rad if rad is not None else Rad()
        self._raeder.append(rad)
        return rad

    def _balken_zeigen(self, an):
        try:
            leiste = FreeCADGui.getMainWindow().statusBar()
        except Exception:  # noqa: BLE001 – ohne Hauptfenster nur das Zeichen
            return
        if an and self._balken is None:
            self._balken = QtGui.QProgressBar()
            self._balken.setRange(0, 0)  # ohne Ende: läuft hin und her
            self._balken.setMaximumWidth(140)
            self._balken.setMaximumHeight(14)
            self._balken.setTextVisible(False)
            self._balken.setToolTip(tr("re.rechnet.tooltip"))
            leiste.addPermanentWidget(self._balken)
            leiste.showMessage(tr("re.rechnet.leiste"))
        elif not an and self._balken is not None:
            leiste.removeWidget(self._balken)
            self._balken.deleteLater()
            self._balken = None
            leiste.clearMessage()

    @property
    def zu_sehen(self):
        """Steht das Zeichen gerade da?"""
        return not self.etikett.isHidden()

    def ende(self):
        """Beim Schließen: die Uhr aus, der Balken weg."""
        self._uhr.stop()
        try:
            self._balken_zeigen(False)
        except RuntimeError:  # der Balken ist schon weg
            self._balken = None
