# SPDX-License-Identifier: LGPL-2.1-or-later
"""Befehl und Dialog „Schnittwerte in den Job“ (W-002, Stufe 2).

Für jeden Werkzeug-Controller des Jobs eine Zeile: welches Werkzeug der
Werkzeugverwaltung dahintersteht, welcher Einsatz gelten soll (vorgeschlagen,
änderbar), was daraus an Drehzahl und Vorschub wird, welche Operationen
Schrittweite und Zustelltiefe bekommen – und was jetzt eingestellt ist.
„Übernehmen“ setzt alles in einem Schritt (Strg+Z). Der Werkstoff kommt vom
Rohteil des Jobs und lässt sich ändern. Die Logik steht in
job_schnittwerte.py.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, symbol
from . import job_schnittwerte as js
from . import uebergabe_werkzeuge as ue
from . import werkstoffe as ws
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_teile import grau, hinweiszeile
from .gui_werkzeuge import werkstoffe_anbieten
from .gui_zahlen import dezimal, zahl_zeigen, zahlenformat
from .sprache import tr

# Spalten der Tabelle.
TC, WERKZEUG, EINSATZ, N, VF, ZUSTELLUNG, JETZT = range(7)
FENSTER_GROESSE = (1180, 480)  # Pixel – breit genug für „· 2 Ebenen (25 + 1 mm)“


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


def _zustellung_text(werte):
    """„10 % · 25 mm · Helix 3°“ aus {Eigenschaft: Wert} von js.zustellung() oder den jetzigen."""
    teile = []
    for eigenschaft in ("StepOver", "StepOverPercent"):
        if eigenschaft in werte:
            teile.append(f"{zahl_zeigen(float(werte[eigenschaft]))} %")
    if "StepDown" in werte:
        teile.append(f"{zahl_zeigen(float(werte['StepDown']))} mm")
    for eigenschaft in js.HELIX_WINKEL:
        if eigenschaft in werte:
            teile.append(tr("sj.helix", winkel=zahl_zeigen(float(werte[eigenschaft]))))
    return " · ".join(teile)


def _ebenen_text(dicken):
    """„1 Ebene“, „2 Ebenen (25 + 1 mm)“, „5 Ebenen (4 × 25 + 3 mm)“."""
    if len(dicken) == 1:
        return tr("sj.ebene_eine")
    if len(dicken) <= 3:
        teile = " + ".join(zahl_zeigen(d) for d in dicken)
    elif len(set(dicken)) == 1:
        teile = f"{len(dicken)} × {zahl_zeigen(dicken[0])}"
    else:
        teile = f"{len(dicken) - 1} × {zahl_zeigen(dicken[0])} + {zahl_zeigen(dicken[-1])}"
    return tr("sj.ebenen", anzahl=len(dicken), dicken=teile)


def _jetzt(operation, eigenschaften):
    """Die jetzigen Werte dieser Eigenschaften einer Operation, in mm, % und Grad."""
    werte = {}
    for eigenschaft in eigenschaften:
        wert = getattr(operation, eigenschaft)
        einheit = "deg" if eigenschaft in js.HELIX_WINKEL else "mm"
        werte[eigenschaft] = wert.getValueAs(einheit) if hasattr(wert, "getValueAs") else wert
    return werte


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
        self._duenn = {}  # Zeile → Sätze zu dünnen letzten Ebenen
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
        self.wahl_werkstoff.currentIndexChanged.connect(lambda *_: self._werkstoff_gewaehlt())
        formular.addRow(tr("wv.werkstoff"), self.wahl_werkstoff)
        self.herkunft = QtGui.QLabel()
        self.herkunft.setWordWrap(True)
        self.knopf_am_rohteil = QtGui.QPushButton(tr("sj.am_rohteil"))
        self.knopf_am_rohteil.setToolTip(tr("sj.am_rohteil.tooltip"))
        self.knopf_am_rohteil.setAutoDefault(False)
        self.knopf_am_rohteil.clicked.connect(self.werkstoff_am_rohteil)
        zeile = QtGui.QHBoxLayout()
        zeile.addWidget(self.herkunft, 1)
        zeile.addWidget(self.knopf_am_rohteil)
        formular.addRow("", zeile)
        aufbau.addLayout(formular)

        self.tabelle = QtGui.QTableWidget(0, 7)
        self.tabelle.setHorizontalHeaderLabels(
            [
                tr("sj.spalte.tc"),
                tr("sj.spalte.werkzeug"),
                tr("wv.spalte.einsatz"),
                "n\n" + tr("einheit.drehzahl"),
                "vf\nmm/min",
                tr("sj.spalte.zustellung"),
                tr("sj.spalte.jetzt"),
            ]
        )
        self.tabelle.horizontalHeaderItem(ZUSTELLUNG).setToolTip(tr("sj.zustellung.tooltip"))
        self.tabelle.verticalHeader().hide()
        self.tabelle.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        kopf = self.tabelle.horizontalHeader()
        kopf.setSectionResizeMode(QtGui.QHeaderView.ResizeToContents)
        kopf.setSectionResizeMode(WERKZEUG, QtGui.QHeaderView.Stretch)
        aufbau.addWidget(self.tabelle, 1)
        self.ebenen_hinweis = hinweiszeile()
        self.ebenen_hinweis.hide()
        aufbau.addWidget(self.ebenen_hinweis)

        # Ein Knopf mit Menü: je Werkzeug seine Einsätze – ein Klick legt an.
        self.knopf_tc_neu = QtGui.QPushButton(tr("sj.tc_neu"))
        self.knopf_tc_neu.setToolTip(tr("sj.tc_neu.tooltip"))
        self.knopf_tc_neu.setAutoDefault(False)
        self.menue_tc_neu = QtGui.QMenu(self.knopf_tc_neu)
        self.menue_tc_neu.aboutToShow.connect(self._menue_tc_neu_fuellen)
        self.knopf_tc_neu.setMenu(self.menue_tc_neu)
        zeile = QtGui.QHBoxLayout()
        zeile.addWidget(self.knopf_tc_neu)
        zeile.addStretch()
        aufbau.addLayout(zeile)

        self.mit_zustellung = QtGui.QCheckBox(tr("sj.zustellung"))
        self.mit_zustellung.setToolTip(tr("sj.zustellung.tooltip"))
        self.mit_zustellung.setChecked(_parameter().GetBool("SjZustellung", True))
        self.mit_zustellung.toggled.connect(self._zustellung_zeigen)
        aufbau.addWidget(self.mit_zustellung)

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
        self._zustellung_zeigen()

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
        self._knopf_am_rohteil_zeigen()
        self._zeilen_aufbauen()

    def _werkstoff_gewaehlt(self):
        self._knopf_am_rohteil_zeigen()
        self._rechnen()

    def _gewaehlter_werkstoff(self):
        return ws.finde(self.bibliothek.alle_werkstoffe(), self.werkstoff)

    def _knopf_am_rohteil_zeigen(self):
        """Nur, wenn es für den gewählten Werkstoff eine FreeCAD-Karte gibt und sie noch fehlt."""
        werkstoff = self._gewaehlter_werkstoff()
        passt = werkstoff is not None and self.job is not None and js.karte_fuer(werkstoff)
        schon_da = passt and js.nummer_am_rohteil(self.job) == werkstoff.nummer
        self.knopf_am_rohteil.setVisible(bool(passt) and not schon_da)

    def werkstoff_am_rohteil(self):
        """Trägt den gewählten Werkstoff als FreeCAD-Werkstoffkarte am Rohteil ein."""
        werkstoff = self._gewaehlter_werkstoff()
        if werkstoff is None or self.job is None:
            return None
        name = js.setze_werkstoff_am_rohteil(self.dokument, self.job, werkstoff)
        self._job_gewaehlt()
        return name

    def _zeilen_aufbauen(self):
        tcs = js.werkzeug_controller(self.job) if self.job else []
        self.tabelle.setRowCount(len(tcs))
        self._zeilen = []
        self._duenn = {}
        for zeile, tc in enumerate(tcs):
            werkzeug = js.werkzeug_von(tc, self.bibliothek)
            wahl = QtGui.QComboBox()
            wahl.currentIndexChanged.connect(lambda *_, z=zeile: self._zeile_rechnen(z))
            self._zeilen.append((tc, werkzeug, wahl))
            self.tabelle.setItem(zeile, TC, QtGui.QTableWidgetItem(tc.Label))
            if werkzeug is not None:
                zelle = QtGui.QTableWidgetItem(dezimal(wz.zeile(werkzeug)))
            else:
                zelle = grau(tr("sj.kein_werkzeug"))
                zelle.setToolTip(tr("sj.kein_werkzeug.tooltip"))
            self.tabelle.setItem(zeile, WERKZEUG, zelle)
            self.tabelle.setCellWidget(zeile, EINSATZ, wahl)
            jetzt = tr(
                "sj.jetzt",
                n=_zahl(tc.SpindleSpeed),
                vf=_zahl(float(tc.HorizFeed.getValueAs("mm/min"))),
            )
            self.tabelle.setItem(zeile, JETZT, grau(jetzt))
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
        self.tabelle.setItem(zeile, ZUSTELLUNG, self._zustellung_zelle(zeile, werkzeug, einsatz))
        self._ebenen_hinweis_zeigen()

    def _zustellung_zelle(self, zeile, werkzeug, einsatz):
        """Welche Operationen des TC Schrittweite und Zustelltiefe bekommen – und ihr jetziger Wert."""
        tc = self._zeilen[zeile][0]
        zeilen, jetzt, duenn = [], [], []
        for operation in js.operationen_mit(tc, self.job) if einsatz is not None else []:
            neu = js.zustellung(operation, werkzeug, einsatz)
            if not neu:
                continue
            text = f"{operation.Label}: {_zustellung_text(neu)}"
            ohne_bahn = js.ohne_bahn(operation)
            if ohne_bahn:
                text += " · " + tr("sj.ohne_basis")
            dicken = js.ebenen(operation, neu["StepDown"]) if "StepDown" in neu else []
            if dicken and not ohne_bahn:
                text += " · " + _ebenen_text(dicken)
                rest = js.duenne_letzte_ebene(dicken, neu["StepDown"])
                if rest is not None:
                    duenn.append(self._duenn_satz(operation, werkzeug, *rest))
            zeilen.append(text)
            vorher = _zustellung_text(_jetzt(operation, neu))
            jetzt.append(f"{operation.Label}: {vorher}")
        self._duenn[zeile] = duenn
        zelle = QtGui.QTableWidgetItem("\n".join(zeilen))
        if jetzt:
            zelle.setToolTip(tr("sj.zustellung.jetzt", werte="\n".join(jetzt)))
        return zelle

    @staticmethod
    def _duenn_satz(operation, werkzeug, rest, ap_ohne):
        """Der Satz zu einer dünnen letzten Ebene – mit ap, wenn die Schneide dafür reicht."""
        satz = tr("sj.ebene_duenn", operation=operation.Label, rest=zahl_zeigen(rest))
        if werkzeug.schneidenlaenge and ap_ohne <= werkzeug.schneidenlaenge:
            satz += " " + tr(
                "sj.ebene_duenn.ap",
                ap=zahl_zeigen(ap_ohne),
                laenge=zahl_zeigen(werkzeug.schneidenlaenge),
            )
        return satz

    def _ebenen_hinweis_zeigen(self):
        """Unter der Tabelle: welche Operation eine dünne letzte Ebene fahren würde."""
        saetze = [s for zeile in sorted(self._duenn) for s in self._duenn[zeile]]
        self.ebenen_hinweis.setText("\n".join(saetze))
        self.ebenen_hinweis.setVisible(bool(saetze) and self.mit_zustellung.isChecked())

    def _zustellung_zeigen(self, *_):
        """Die Spalte Zustellung nur, wenn sie auch übernommen wird; die Wahl merken."""
        an = self.mit_zustellung.isChecked()
        self.tabelle.setColumnHidden(ZUSTELLUNG, not an)
        _parameter().SetBool("SjZustellung", an)
        self.tabelle.resizeRowsToContents()
        self._ebenen_hinweis_zeigen()

    def _menue_tc_neu_fuellen(self):
        """Je Werkzeug ein Untermenü mit den Einsätzen, die vc und fz haben."""
        self.menue_tc_neu.clear()
        for werkzeug in self.bibliothek.sortierte_werkzeuge():
            einsaetze = [
                e for e in werkzeug.einsaetze(self.werkstoff) if _vollstaendig(werkzeug, e)
            ]
            if not einsaetze or not werkzeug.durchmesser:
                continue
            untermenue = self.menue_tc_neu.addMenu(dezimal(wz.zeile(werkzeug)))
            for einsatz in einsaetze:
                aktion = untermenue.addAction(wz.einsatz_name(einsatz))
                aktion.triggered.connect(
                    lambda _an=False, w=werkzeug, e=einsatz: self.controller_anlegen(w, e)
                )
        if self.menue_tc_neu.isEmpty():
            leer = self.menue_tc_neu.addAction(tr("sj.tc_neu.leer"))
            leer.setEnabled(False)

    def controller_anlegen(self, werkzeug, einsatz):
        """Neuer Werkzeug-Controller im Job, benannt nach dem Einsatz, mit n und vf.

        Übergibt vorher alle Werkzeuge an CAM – so ist das Werkzeug in der
        Bibliothek „CAM-Addon“ und auf dem gespeicherten Stand. Gibt den
        Controller zurück (oder None).
        """
        if self.job is None:
            return None
        try:
            ue.uebergeben(self.bibliothek)
            tc = js.lege_controller_an(self.dokument, self.job, werkzeug, einsatz)
        except Exception as fehler:  # jeder Fehler von CAM soll als Satz ankommen
            FreeCAD.Console.PrintError(f"CAM-Addon: Werkzeug-Controller anlegen: {fehler}\n")
            QtGui.QMessageBox.warning(self, tr("sj.titel"), tr("sj.tc_neu.fehler", fehler=fehler))
            return None
        self._zeilen_aufbauen()
        return tc

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
        job = self.job if self.mit_zustellung.isChecked() else None
        gesetzt = js.setze(self.dokument, zuordnung, job) if zuordnung else js.Gesetzt()
        self.gesetzt = gesetzt
        if gesetzt.operationen:
            text = tr(
                "sj.gesetzt.operationen",
                anzahl=gesetzt.controller,
                operationen=", ".join(gesetzt.operationen),
            )
        else:
            text = tr("sj.gesetzt", anzahl=gesetzt.controller)
        QtCore.QTimer.singleShot(
            0,
            lambda: QtGui.QMessageBox.information(FreeCADGui.getMainWindow(), tr("sj.titel"), text),
        )
        self.accept()


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def _vollstaendig(werkzeug, einsatz):
    """Hat der Einsatz vc und fz? Sonst wird er nicht vorgeschlagen."""
    n, vf, _senkrecht = js.werte(werkzeug, einsatz)
    return n > 0 and vf > 0
