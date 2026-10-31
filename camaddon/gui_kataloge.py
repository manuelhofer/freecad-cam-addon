# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Frage nach dem Start „Kataloge der Hersteller laden?“ und das Laden mit Fortschritt
(kataloge.py; Manuel, 2026-10-31: „"hey sollen wir die kataloginhalte downloaden um einfach
deutlich bessere vorhersagen machen zu können" oder sowas .. und dann ja nein vll“).

- Nach dem Start (VERZOEGERUNG_MS): Kommen die Kataloge mit dem Addon (Git-Klon) oder liegen sie
  vollständig im Profil, nichts. Hat man „Ja“ gesagt und ein Update bringt neue Fassungen, holt es
  sie still im Hintergrund. Sonst – außer nach „Nein“ – die Frage: Ja / Später / Nein.
- `zeile(eltern, danach)`: in den Katalogfenstern, wenn noch nichts geladen ist, der Satz dazu und
  der Knopf „Kataloge laden …“ (Gedächtnis „Nächster Schritt als Knopf“); `danach()` füllt das
  Fenster neu.
- `LadenFenster`: der Download in einem Faden, der Fortschritt über einen Zeitgeber – das Fenster
  bleibt bedienbar.
"""

import threading

import FreeCAD
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, kataloge, uhren
from .gui_teile import knopf
from .sprache import tr

VERZOEGERUNG_MS = 8000
NACHSEHEN_MS = 200


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def wahl():
    return _parameter().GetString(kataloge.FRAGE, "")


def wahl_merken(wert):
    _parameter().SetString(kataloge.FRAGE, wert)


def beim_start():
    """Kurz nach dem Start nachsehen (gui_start)."""
    if kataloge.im_addon():
        return
    QtCore.QTimer.singleShot(VERZOEGERUNG_MS, _nach_dem_start)


def _nach_dem_start():
    gewaehlt = wahl()
    if gewaehlt == kataloge.NEIN:
        return
    try:
        offen = kataloge.fehlend()
    except OSError:
        return
    if not offen:
        return
    if gewaehlt == kataloge.JA:
        _still_laden()  # neue Fassungen nach einem Update
        return
    import FreeCADGui

    KatalogFrage(FreeCADGui.getMainWindow()).exec_()


def _still_laden():
    def laden():
        try:
            anzahl = kataloge.laden()
            FreeCAD.Console.PrintMessage(tr("kg.still_fertig", n=anzahl) + "\n")
        except OSError as fehler:
            FreeCAD.Console.PrintWarning(tr("kg.still_fehler", grund=str(fehler)) + "\n")

    threading.Thread(target=laden, name="Kataloge", daemon=True).start()


def _download_text():
    """„etwa 1,1 MB Download, 15,4 MB auf der Platte“ – gepackt etwa ein Fünfzehntel."""
    alle = sum(int(e.get("groesse", 0)) for e in kataloge.index().values())
    return tr(
        "kg.groesse",
        download=kataloge.groesse_text(alle / 14.0),
        platte=kataloge.groesse_text(alle),
    )


class KatalogFrage(QtGui.QDialog):
    """„Kataloge der Hersteller laden?“ – Ja lädt (LadenFenster), Später fragt beim nächsten
    Start wieder, Nein nie mehr (der Knopf in den Katalogfenstern bleibt)."""

    offen = None  # für die Oberflächen-Szenarien

    def __init__(self, eltern=None):
        super().__init__(eltern)
        KatalogFrage.offen = self
        self.setWindowTitle(tr("kg.titel"))
        self.setMinimumWidth(480)
        aufbau = QtGui.QVBoxLayout(self)
        text = QtGui.QLabel(tr("kg.frage") + "\n\n" + _download_text())
        text.setWordWrap(True)
        aufbau.addWidget(text)
        zeile = QtGui.QHBoxLayout()
        zeile.addStretch()
        self.knopf_ja = knopf(tr("kg.ja"), tr("kg.ja.tooltip"), self.ja)
        self.knopf_spaeter = knopf(tr("kg.spaeter"), tr("kg.spaeter.tooltip"), self.spaeter)
        self.knopf_nein = knopf(tr("kg.nein"), tr("kg.nein.tooltip"), self.nein)
        for k in (self.knopf_ja, self.knopf_spaeter, self.knopf_nein):
            zeile.addWidget(k)
        self.knopf_ja.setDefault(True)
        aufbau.addLayout(zeile)

    def ja(self):
        wahl_merken(kataloge.JA)
        self.accept()
        LadenFenster(self.parent()).exec_()

    def spaeter(self):
        wahl_merken(kataloge.SPAETER)
        self.reject()

    def nein(self):
        wahl_merken(kataloge.NEIN)
        self.reject()

    def done(self, ergebnis):
        KatalogFrage.offen = None
        super().done(ergebnis)


class LadenFenster(QtGui.QDialog):
    """Lädt die Kataloge (kataloge.laden) in einem Faden; zeigt Datei und Fortschritt, am Ende
    „fertig“ oder den Grund und „Nochmal“. `fertig()` danach (das Fenster füllt sich neu)."""

    offen = None  # für die Oberflächen-Szenarien

    def __init__(self, eltern=None, fertig=None, adresse=None):
        super().__init__(eltern)
        LadenFenster.offen = self
        self.setWindowTitle(tr("kg.laden.titel"))
        self.setMinimumWidth(460)
        self._fertig = fertig
        self._adresse = adresse
        aufbau = QtGui.QVBoxLayout(self)
        self.text = QtGui.QLabel(tr("kg.laden.start"))
        self.text.setWordWrap(True)
        aufbau.addWidget(self.text)
        self.balken = QtGui.QProgressBar()
        aufbau.addWidget(self.balken)
        zeile = QtGui.QHBoxLayout()
        zeile.addStretch()
        self.knopf_nochmal = knopf(tr("kg.nochmal"), tr("kg.nochmal.tooltip"), self.starten)
        self.knopf_zu = knopf(tr("kg.abbrechen"), tr("kg.abbrechen.tooltip"), self.reject)
        zeile.addWidget(self.knopf_nochmal)
        zeile.addWidget(self.knopf_zu)
        aufbau.addLayout(zeile)
        self.stand = None  # (fertig, alle, Pfad) – setzt der Faden
        self.ergebnis = None  # Anzahl oder Fehlertext – setzt der Faden
        self.abbruch = False
        self.uhr = QtCore.QTimer(self)
        self.uhr.setInterval(NACHSEHEN_MS)
        self.uhr.timeout.connect(uhren.aus_der_schleife(self.uhr, self._nachsehen))
        self.starten()

    def starten(self):
        self.knopf_nochmal.hide()
        self.knopf_zu.setText(tr("kg.abbrechen"))
        self.ergebnis = None
        self.abbruch = False
        threading.Thread(target=self._laden, name="Kataloge", daemon=True).start()
        self.uhr.start()

    def _laden(self):
        try:
            anzahl = kataloge.laden(
                lambda f, a, p: setattr(self, "stand", (f, a, p)),
                self._adresse,
                lambda: self.abbruch,
            )
            self.ergebnis = anzahl
        except OSError as fehler:
            self.ergebnis = str(fehler)

    def _nachsehen(self):
        if self.stand is not None:
            fertig, alle, pfad = self.stand
            self.balken.setMaximum(max(alle, 1))
            self.balken.setValue(fertig)
            if pfad:
                self.text.setText(tr("kg.laden.datei", datei=pfad, n=fertig + 1, alle=alle))
        if self.ergebnis is None:
            return
        self.uhr.stop()
        self.knopf_zu.setText(tr("kg.schliessen"))
        if isinstance(self.ergebnis, str):
            self.text.setText(tr("kg.laden.fehler", grund=self.ergebnis))
            self.knopf_nochmal.show()
            return
        self.balken.setMaximum(1)
        self.balken.setValue(1)
        self.text.setText(tr("kg.laden.fertig", n=self.ergebnis))
        _werkzeugkiste_vorbereiten()
        if self._fertig is not None:
            self._fertig()

    def reject(self):
        self.abbruch = True
        super().reject()

    def done(self, ergebnis):
        LadenFenster.offen = None
        self.uhr.stop()
        super().done(ergebnis)


def _werkzeugkiste_vorbereiten():
    """Die neuen Werkzeuge gleich im Hintergrund prüfen und zwischenspeichern."""
    from . import werkzeugkiste_datei as wd

    def lesen():
        try:
            wd.mitgelieferte()
        except Exception as fehler:  # dann eben beim Öffnen
            FreeCAD.Console.PrintLog(f"CAM-Addon: Werkzeugkiste nicht vorbereitet: {fehler}\n")

    threading.Thread(target=lesen, name="Werkzeugkiste", daemon=True).start()


def zeile(eltern, danach=None):
    """Ein Widget „Die Kataloge der Hersteller sind noch nicht geladen. [Kataloge laden …]“ – None,
    wenn sie da sind. `danach()` nach dem Laden (das Fenster neu füllen)."""
    if kataloge.vorhanden():
        return None
    widget = QtGui.QWidget()
    aufbau = QtGui.QHBoxLayout(widget)
    aufbau.setContentsMargins(0, 0, 0, 0)
    satz = QtGui.QLabel(tr("kg.fehlen"))
    satz.setWordWrap(True)
    satz.setStyleSheet("color: #d08000;")
    aufbau.addWidget(satz, 1)

    def laden():
        wahl_merken(kataloge.JA)

        def fertig():
            widget.hide()
            if danach is not None:
                danach()

        LadenFenster(eltern, fertig).exec_()

    aufbau.addWidget(knopf(tr("kg.knopf"), tr("kg.knopf.tooltip"), laden))
    return widget
