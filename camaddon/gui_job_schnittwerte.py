# SPDX-License-Identifier: LGPL-2.1-or-later
"""Befehl und Dialog „Schnittwerte in den Job“ (W-002, Stufe 2).

Für jeden Werkzeug-Controller des Jobs eine Zeile: welches Werkzeug der
Werkzeugverwaltung dahintersteht, welcher Einsatz gelten soll (vorgeschlagen,
änderbar), was daraus an Drehzahl und Vorschub wird – und was jetzt
eingestellt ist. „Übernehmen“ setzt alles in einem Schritt (Strg+Z). Der
Werkstoff kommt vom Rohteil des Jobs und lässt sich ändern. Die Logik steht
in job_schnittwerte.py.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import job_schnittwerte as js
from . import symbol
from . import werkstoffe as ws
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_werkzeuge import werkstoffe_anbieten
from .gui_zahlen import dezimal, zahlenformat
from .sprache import tr

# Spalten der Tabelle.
TC, WERKZEUG, EINSATZ, N, VF, JETZT = range(6)
FENSTER_GROESSE = (900, 420)  # Pixel
GRAU = QtGui.QColor("#6d6d6d")


class BefehlSchnittwerteJob:
    """Öffnet den Dialog – aktiv, sobald das Dokument einen CAM-Job hat."""

    def GetResources(self):
        return {
            "Pixmap": symbol("schnittwerte_job.svg"),
            "MenuText": tr("befehl.schnittwerte_job.titel"),
            "ToolTip": tr("befehl.schnittwerte_job.tooltip"),
        }

    def IsActive(self):
        return bool(js.jobs(FreeCAD.ActiveDocument))

    def Activated(self):
        dialog = SchnittwerteJobDialog()
        dialog.exec()
        SchnittwerteJobDialog.offen = None


def _zahl(wert, stellen=0):
    return zahlenformat().toString(float(wert), "f", stellen)


class SchnittwerteJobDialog(QtGui.QDialog):
    """Werkzeug-Controller des Jobs mit Einsatz, neuen und jetzigen Werten."""

    offen = None  # für die Oberflächen-Szenarien

    def __init__(self, eltern=None, dokument=None, pfad=None):
        super().__init__(eltern or FreeCADGui.getMainWindow())
        SchnittwerteJobDialog.offen = self
        self.dokument = dokument or FreeCAD.ActiveDocument
        self.jobs = js.jobs(self.dokument)
        try:
            self.bibliothek = wz.Bibliothek.laden(pfad)
        except wz.BeschaedigteDatei as fehler:
            QtGui.QMessageBox.warning(
                self, tr("wv.titel"), tr("wv.fehler.laden", fehler=fehler, datei=fehler.beiseite)
            )
            self.bibliothek = wz.Bibliothek()
        self._zeilen = []  # (tc, werkzeug oder None, Auswahl des Einsatzes)
        self.setWindowTitle(tr("sj.titel"))
        self.resize(*FENSTER_GROESSE)

        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(kopfzeile(tr("sj.titel"), "werkzeuge"))
        formular = QtGui.QFormLayout()
        self.wahl_job = QtGui.QComboBox()
        for job in self.jobs:
            self.wahl_job.addItem(job.Label)
        self.wahl_job.currentIndexChanged.connect(self._job_gewaehlt)
        formular.addRow(tr("sj.job"), self.wahl_job)
        self.wahl_werkstoff = QtGui.QComboBox()
        self.wahl_werkstoff.setToolTip(tr("sj.werkstoff.tooltip"))
        werkstoffe_anbieten(self.wahl_werkstoff, self.bibliothek)
        self.wahl_werkstoff.currentIndexChanged.connect(lambda *_: self._rechnen())
        formular.addRow(tr("wv.werkstoff"), self.wahl_werkstoff)
        self.herkunft = QtGui.QLabel()
        self.herkunft.setWordWrap(True)
        formular.addRow("", self.herkunft)
        aufbau.addLayout(formular)

        self.tabelle = QtGui.QTableWidget(0, 6)
        self.tabelle.setHorizontalHeaderLabels(
            [
                tr("sj.spalte.tc"),
                tr("sj.spalte.werkzeug"),
                tr("wv.spalte.einsatz"),
                "n\nU/min",
                "vf\nmm/min",
                tr("sj.spalte.jetzt"),
            ]
        )
        self.tabelle.verticalHeader().hide()
        self.tabelle.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        kopf = self.tabelle.horizontalHeader()
        kopf.setSectionResizeMode(QtGui.QHeaderView.ResizeToContents)
        kopf.setSectionResizeMode(WERKZEUG, QtGui.QHeaderView.Stretch)
        aufbau.addWidget(self.tabelle, 1)

        self.hinweis = QtGui.QLabel(tr("sj.hinweis"))
        self.hinweis.setWordWrap(True)
        aufbau.addWidget(self.hinweis)

        self.knoepfe = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
        )
        self.knoepfe.button(QtGui.QDialogButtonBox.Ok).setText(tr("sj.uebernehmen"))
        self.knoepfe.accepted.connect(self.uebernehmen)
        self.knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(self.knoepfe)

        self.wahl_job.setVisible(len(self.jobs) > 1)
        formular.labelForField(self.wahl_job).setVisible(len(self.jobs) > 1)
        self._job_gewaehlt()

    @property
    def job(self):
        return self.jobs[self.wahl_job.currentIndex()] if self.jobs else None

    @property
    def werkstoff(self):
        """Kennung des gewählten Werkstoffs, oder wz.ALLE."""
        return self.wahl_werkstoff.currentData() or wz.ALLE

    def _job_gewaehlt(self, *_):
        """Werkstoff vom Rohteil, Zeilen für die Werkzeug-Controller."""
        job = self.job
        werkstoff = js.werkstoff_des_jobs(job, self.bibliothek.alle_werkstoffe()) if job else None
        index = self.wahl_werkstoff.findData(werkstoff.kennung if werkstoff else wz.ALLE)
        self.wahl_werkstoff.blockSignals(True)
        self.wahl_werkstoff.setCurrentIndex(max(index, 0))
        self.wahl_werkstoff.blockSignals(False)
        if werkstoff is not None:
            self.herkunft.setText(tr("sj.herkunft.rohteil", werkstoff=ws.anzeige(werkstoff)))
        else:
            self.herkunft.setText(tr("sj.herkunft.unbekannt"))
        self._zeilen_aufbauen()

    def _zeilen_aufbauen(self):
        tcs = js.werkzeug_controller(self.job) if self.job else []
        self.tabelle.setRowCount(len(tcs))
        self._zeilen = []
        for zeile, tc in enumerate(tcs):
            werkzeug = js.werkzeug_von(tc, self.bibliothek)
            wahl = QtGui.QComboBox()
            wahl.currentIndexChanged.connect(lambda *_, z=zeile: self._zeile_rechnen(z))
            self._zeilen.append((tc, werkzeug, wahl))
            self.tabelle.setItem(zeile, TC, QtGui.QTableWidgetItem(tc.Label))
            if werkzeug is not None:
                zelle = QtGui.QTableWidgetItem(dezimal(wz.zeile(werkzeug)))
            else:
                zelle = _grau(tr("sj.kein_werkzeug"))
                zelle.setToolTip(tr("sj.kein_werkzeug.tooltip"))
            self.tabelle.setItem(zeile, WERKZEUG, zelle)
            self.tabelle.setCellWidget(zeile, EINSATZ, wahl)
            jetzt = tr(
                "sj.jetzt",
                n=_zahl(tc.SpindleSpeed),
                vf=_zahl(float(tc.HorizFeed.getValueAs("mm/min"))),
            )
            self.tabelle.setItem(zeile, JETZT, _grau(jetzt))
        self._rechnen()

    def _rechnen(self):
        """Füllt je Zeile die Einsätze für den gewählten Werkstoff und den Vorschlag."""
        for zeile, (tc, werkzeug, wahl) in enumerate(self._zeilen):
            wahl.blockSignals(True)
            wahl.clear()
            wahl.addItem(tr("sj.nicht_aendern"), -1)
            einsaetze = werkzeug.einsaetze(self.werkstoff) if werkzeug is not None else []
            for i, einsatz in enumerate(einsaetze):
                wahl.addItem(wz.einsatz_name(einsatz), i)
            vorschlag = js.vorgeschlagener_einsatz(tc, einsaetze, self.job)
            if vorschlag >= 0 and not _vollstaendig(werkzeug, einsaetze[vorschlag]):
                vorschlag = -1
            wahl.setCurrentIndex(wahl.findData(vorschlag))
            wahl.setEnabled(bool(einsaetze))
            wahl.blockSignals(False)
            self._zeile_rechnen(zeile)

    def _gewaehlt(self, zeile):
        """(Werkzeug, Einsatz) der Zeile, oder (Werkzeug, None) bei „nicht ändern“."""
        _tc, werkzeug, wahl = self._zeilen[zeile]
        index = wahl.currentData()
        if werkzeug is None or index is None or index < 0:
            return werkzeug, None
        return werkzeug, werkzeug.einsaetze(self.werkstoff)[index]

    def _zeile_rechnen(self, zeile):
        werkzeug, einsatz = self._gewaehlt(zeile)
        if einsatz is None:
            n = vf = ""
        else:
            werte_n, werte_vf, _senkrecht = js.werte(werkzeug, einsatz)
            n = _zahl(werte_n) if werte_n else ""
            vf = _zahl(werte_vf) if werte_vf else ""
        self.tabelle.setItem(zeile, N, QtGui.QTableWidgetItem(n))
        self.tabelle.setItem(zeile, VF, QtGui.QTableWidgetItem(vf))

    def waehle_einsatz(self, zeile, index):
        """Wählt in Zeile `zeile` den Einsatz `index` (-1 = nicht ändern) – für die Szenarien."""
        wahl = self._zeilen[zeile][2]
        wahl.setCurrentIndex(wahl.findData(index))

    def uebernehmen(self):
        """„Übernehmen“: setzt alle Zeilen mit Einsatz in einem Schritt und sagt, wie viele."""
        zuordnung = []
        for zeile, (tc, _werkzeug, _wahl) in enumerate(self._zeilen):
            werkzeug, einsatz = self._gewaehlt(zeile)
            if einsatz is not None:
                zuordnung.append((tc, werkzeug, einsatz))
        anzahl = js.setze(self.dokument, zuordnung) if zuordnung else 0
        self.gesetzt = anzahl
        QtCore.QTimer.singleShot(
            0,
            lambda: QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(), tr("sj.titel"), tr("sj.gesetzt", anzahl=anzahl)
            ),
        )
        self.accept()


def _vollstaendig(werkzeug, einsatz):
    """Hat der Einsatz vc und fz? Sonst wird er nicht vorgeschlagen."""
    n, vf, _senkrecht = js.werte(werkzeug, einsatz)
    return n > 0 and vf > 0


def _grau(text):
    zelle = QtGui.QTableWidgetItem(text)
    zelle.setForeground(GRAU)
    return zelle
