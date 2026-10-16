# SPDX-License-Identifier: LGPL-2.1-or-later
"""„Beispiele laden …“: die Testteile aus `beispiele/` auf Wunsch von GitHub holen (beispiele.py) –
das Update lädt sie nicht mit (Manuel, 2026-10-16: „mit beispiel datein" oder "ohne beispiel
dateien"“). Das Fenster nennt jede Datei mit Größe, holt im Hintergrund und öffnet danach den
Ordner."""

import os
import threading

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import ADDON_ORDNER, symbol, uhren
from . import aktualisierung as a
from . import beispiele as bsp
from .gui_zahlen import dezimal
from .sprache import tr

NACHSEHEN_MS = 200


def _groesse(anzahl_bytes):
    """„3,3 MB“, „97 kB“ – mit dem Dezimalzeichen der Sprache."""
    if anzahl_bytes >= 1_000_000:
        return dezimal(f"{anzahl_bytes / 1_000_000:.1f} MB")
    return f"{max(round(anzahl_bytes / 1000), 1)} kB"


class BeispieleDialog(QtGui.QDialog):
    """Die Liste der Beispiele mit Haken, „Laden“ und „Ordner öffnen“."""

    offen = None  # für die Szenarien

    def __init__(self, eltern=None, liste=None, wohin=None, hole=None):
        super().__init__(eltern or FreeCADGui.getMainWindow())
        BeispieleDialog.offen = self
        self.setWindowTitle(tr("bsp.titel"))
        self.wohin = wohin or bsp.ordner()
        self.beispiele = liste if liste is not None else bsp.liste()
        self._hole = hole
        self._ergebnis = None
        self._stand = (0, 0, None)
        aufbau = QtGui.QVBoxLayout(self)
        text = QtGui.QLabel(
            tr(
                "bsp.text",
                anzahl=len(self.beispiele),
                groesse=_groesse(sum(b.bytes for b in self.beispiele)),
                ordner=self.wohin,
            )
        )
        text.setWordWrap(True)
        text.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        aufbau.addWidget(text)
        # Zu Beginn nichts angehakt, darüber „Alle anhaken“ und „Alle abhaken“ wie in der
        # Werkzeugkiste (Manuel, 2026-10-16: „hier erstmal alles nicht angeklickt .. und nen button
        # wie in der werkzeuglsite ... alles anhacken und nichts anhacken“).
        oben = QtGui.QHBoxLayout()
        self.knopf_alle = QtGui.QPushButton(tr("bsp.alle"))
        self.knopf_alle.setToolTip(tr("bsp.alle.tooltip"))
        self.knopf_alle.clicked.connect(lambda: self.alle_setzen(True))
        self.knopf_keine = QtGui.QPushButton(tr("bsp.keine"))
        self.knopf_keine.setToolTip(tr("bsp.keine.tooltip"))
        self.knopf_keine.clicked.connect(lambda: self.alle_setzen(False))
        oben.addWidget(self.knopf_alle)
        oben.addWidget(self.knopf_keine)
        oben.addStretch()
        aufbau.addLayout(oben)
        self.liste = QtGui.QListWidget()
        for beispiel in self.beispiele:
            zeile = f"{beispiel.name} – {_groesse(beispiel.bytes)}"
            if bsp.schon_da(beispiel, self.wohin):
                zeile += " – " + tr("bsp.schon_da")
            eintrag = QtGui.QListWidgetItem(zeile)
            eintrag.setFlags(eintrag.flags() | QtCore.Qt.ItemIsUserCheckable)
            eintrag.setCheckState(QtCore.Qt.Unchecked)
            self.liste.addItem(eintrag)
        self.liste.itemChanged.connect(lambda _eintrag: self._laden_freigeben())
        aufbau.addWidget(self.liste)
        self.stand = QtGui.QLabel()
        self.stand.setWordWrap(True)
        aufbau.addWidget(self.stand)
        knoepfe = QtGui.QHBoxLayout()
        self.knopf_laden = QtGui.QPushButton(tr("bsp.laden"))
        self.knopf_laden.setToolTip(tr("bsp.laden.tooltip"))
        self.knopf_laden.clicked.connect(self.laden)
        self.knopf_ordner = QtGui.QPushButton(tr("bsp.ordner"))
        self.knopf_ordner.setToolTip(tr("bsp.ordner.tooltip"))
        self.knopf_ordner.clicked.connect(self.ordner_oeffnen)
        self.knopf_ordner.setEnabled(os.path.isdir(self.wohin))
        schliessen = QtGui.QPushButton(tr("bsp.schliessen"))
        schliessen.clicked.connect(self.reject)
        knoepfe.addWidget(self.knopf_laden)
        knoepfe.addWidget(self.knopf_ordner)
        knoepfe.addStretch()
        knoepfe.addWidget(schliessen)
        aufbau.addLayout(knoepfe)
        self.uhr = QtCore.QTimer(self)
        self.uhr.setInterval(NACHSEHEN_MS)
        self.uhr.timeout.connect(uhren.aus_der_schleife(self.uhr, self._nachsehen))
        self.resize(560, 420)
        self._laden_freigeben()

    def alle_setzen(self, an):
        """Hakt alle Dateien an (`an`) oder ab."""
        zustand = QtCore.Qt.Checked if an else QtCore.Qt.Unchecked
        for i in range(self.liste.count()):
            self.liste.item(i).setCheckState(zustand)

    def _laden_freigeben(self):
        """„Laden“ geht, sobald etwas angehakt ist – und nicht, solange geladen wird."""
        if not self.uhr_laeuft():
            self.knopf_laden.setEnabled(bool(self.gewaehlt()))

    def uhr_laeuft(self):
        uhr = getattr(self, "uhr", None)
        return uhr is not None and uhr.isActive()

    def gewaehlt(self):
        return [
            b
            for i, b in enumerate(self.beispiele)
            if self.liste.item(i).checkState() == QtCore.Qt.Checked
        ]

    def laden(self):
        """Holt die angehakten Beispiele im Hintergrund; der Stand steht darunter."""
        auswahl = self.gewaehlt()
        if not auswahl:
            return
        hole = self._hole
        if hole is None:
            installierer = a._installierer(ADDON_ORDNER)
            installierer.netz_vorbereiten()  # im Hauptthread: Qt lädt nur dort
            hole = installierer.hole
        self.knopf_laden.setEnabled(False)
        self._ergebnis = None

        def fortschritt(i, anzahl, beispiel):
            self._stand = (i, anzahl, beispiel)

        def im_hintergrund():
            try:
                self._ergebnis = bsp.laden(auswahl, self.wohin, hole, fortschritt)
            except Exception as fehler:  # noqa: BLE001 – erscheint im Fenster
                self._ergebnis = ([], [], [(None, str(fehler))])

        # daemon: Ein hängender Download hält FreeCAD beim Beenden nicht auf.
        threading.Thread(target=im_hintergrund, daemon=True).start()
        self.uhr.start()

    def _nachsehen(self):
        if self._ergebnis is None:
            i, anzahl, beispiel = self._stand
            if beispiel is not None:
                self.stand.setText(tr("bsp.laedt", nummer=i + 1, anzahl=anzahl, name=beispiel.name))
            return
        self.uhr.stop()
        geladen, da, fehler = self._ergebnis
        satz = tr("bsp.fertig", geladen=len(geladen), da=len(da), ordner=self.wohin)
        if fehler:
            namen = ", ".join(b.name if b is not None else "?" for b, _g in fehler[:3])
            satz += " " + tr("bsp.fehler", anzahl=len(fehler), namen=namen, grund=fehler[0][1])
        self.stand.setText(satz)
        self._laden_freigeben()
        self.knopf_ordner.setEnabled(os.path.isdir(self.wohin))

    def ordner_oeffnen(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self.wohin))

    def done(self, ergebnis):
        BeispieleDialog.offen = None
        self.uhr.stop()
        super().done(ergebnis)


class BefehlBeispieleLaden:
    """Befehl im Menü: die Beispiele (Testteile) auf Wunsch laden."""

    def GetResources(self):
        return {
            "Pixmap": symbol("so_gehts.svg"),
            "MenuText": tr("befehl.beispiele.titel"),
            "ToolTip": tr("befehl.beispiele.tooltip"),
        }

    def IsActive(self):
        return BeispieleDialog.offen is None

    def Activated(self):
        if not bsp.liste():
            FreeCAD.Console.PrintWarning(tr("bsp.keine_liste") + "\n")
            return
        BeispieleDialog().show()
