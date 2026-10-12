# SPDX-License-Identifier: LGPL-2.1-or-later
"""Ein Zeichen, dass noch gerechnet wird – in den Assistenten „Bearbeitung“ und „4-Achs-Bearbeitung“.

Manuel (2026-10-12, am Geist im 4-Achs-Assistenten): „bis die gelbe Schrift erscheint, dauert es
ein bisschen … man bekommt keine Indikation dafür, dass noch gearbeitet wird … einfach nur irgend
einen Indikator, vielleicht auch einfach ein Rädchen, was erscheint und sich dreht, wenn noch
was gerechnet wird“.

`Anzeige` fragt im Takt, ob der Assistent noch rechnet (eine Funktion, die er mitgibt): Solange
ja, steht oben im Fenster ein Zeichen, das sich dreht, mit „rechnet …“, und unten in der
Statusleiste von FreeCAD ein Balken ohne Ende – die ist immer zu sehen, auch wenn das Fenster
weiter unten steht. „Anlegen“ bleibt bedienbar (Manuel: kein Befehl grau, weil etwas fehlt) –
es rechnet ohnehin selbst zu Ende.
"""

import FreeCADGui
from PySide import QtCore, QtGui

from . import farben
from .sprache import tr

ZEICHEN = "◐◓◑◒"
TAKT_MS = 150
ERST_NACH_MS = 300  # so lange muss es rechnen, bevor das Zeichen erscheint – kein Flackern


class Anzeige:
    """Das Zeichen im Etikett `etikett` (ein QLabel im Fenster, anfangs verborgen) und der Balken
    in der Statusleiste, solange `laeuft()` wahr ist. `ende()` beim Schließen des Fensters."""

    def __init__(self, etikett, laeuft):
        self.etikett = etikett
        self.laeuft = laeuft
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
            an = bool(self.laeuft())
        except Exception:  # noqa: BLE001 – ein Fehler hier darf das Fenster nicht stören
            an = False
        self._seit = self._seit + TAKT_MS if an else 0
        if an and self._seit >= ERST_NACH_MS:
            self._zeichen = (self._zeichen + 1) % len(ZEICHEN)
            self.etikett.setText(f"{ZEICHEN[self._zeichen]}  {tr('re.rechnet')}")
            self.etikett.setToolTip(tr("re.rechnet.tooltip"))
            self.etikett.show()
            self._balken_zeigen(True)
        elif not an:
            self.etikett.hide()
            self._balken_zeigen(False)

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
        self._balken_zeigen(False)
