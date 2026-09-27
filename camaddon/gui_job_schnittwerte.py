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

import html

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, einheiten, symbol
from . import job_schnittwerte as js
from . import uebergabe_werkzeuge as ue
from . import werkstoffe as ws
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_teile import grau, hinweiszeile, ruhiges_mausrad
from .gui_werkzeuge import WerkzeugDialog, werkstoffe_anbieten
from .gui_zahlen import dezimal, groesse_fest, groesse_zeigen, zahl_zeigen, zahlenformat
from .sprache import tr

# Spalten der Tabelle.
TC, WERKZEUG, EINSATZ, N, VF, ZUSTELLUNG, JETZT = range(7)
FENSTER_GROESSE = (1180, 480)  # Pixel – breit genug für „· 2 Ebenen (25 + 1 mm)“


class BefehlSchnittwerteJob:
    """Öffnet den Dialog; ohne Job im aktiven Dokument sagt ein Satz, was fehlt."""

    def GetResources(self):
        return {
            "Pixmap": symbol("schnittwerte_job.svg"),
            "MenuText": tr("befehl.schnittwerte_job.titel"),
            "ToolTip": tr("befehl.schnittwerte_job.tooltip"),
        }

    def IsActive(self):
        # Immer bedienbar, wie „Maschine bearbeiten“: Fehlt der Job, sagt der
        # Befehl, was zu tun ist – ein ausgegrauter Knopf erklärt nichts.
        return True

    def Activated(self):
        dokument = dokument_mit_job(tr("sj.titel"), tr("sj.kein_job"))
        if dokument is None:
            return
        dialog = SchnittwerteJobDialog(dokument=dokument)
        dialog.exec()
        SchnittwerteJobDialog.offen = None


def dokument_mit_job(titel, kein_job):
    """Das Dokument, dessen Jobs gemeint sind (Durchsicht W-004, D-21): das eines
    gewählten Jobs – in jedem offenen Dokument –, sonst das aktive, wenn es Jobs hat,
    sonst das einzige offene mit Jobs; bei mehreren fragt es. Gibt es nirgends einen
    Job, sagt `kein_job` (ein Satz) es – dann None."""
    hauptfenster = FreeCADGui.getMainWindow()
    kandidaten = js.dokumente_mit_jobs(FreeCAD.ActiveDocument)
    if not kandidaten:
        QtGui.QMessageBox.information(hauptfenster, titel, kein_job)
        return None
    for objekt in FreeCADGui.Selection.getSelection("*"):
        for dokument in kandidaten:
            jobs = js.jobs(dokument)
            if any(objekt is job or job in objekt.InListRecursive for job in jobs):
                return dokument
    if kandidaten[0] is FreeCAD.ActiveDocument or len(kandidaten) == 1:
        return kandidaten[0]
    namen = [d.Label for d in kandidaten]
    if len(set(namen)) < len(namen):  # gleiche Namen: der Dateiname hilft
        namen = [f"{d.Label} ({d.Name})" for d in kandidaten]
    name, ok = QtGui.QInputDialog.getItem(
        hauptfenster, titel, tr("jobs.welches_dokument"), namen, 0, False
    )
    return kandidaten[namen.index(name)] if ok else None


def _zahl(wert, stellen=0):
    return zahlenformat().toString(float(wert), "f", stellen)


def _zustellung_text(werte):
    """„10 % · 25 mm · Helix 3°“ aus {Eigenschaft: Wert} von js.zustellung() oder den jetzigen."""
    teile = []
    for eigenschaft in ("StepOver", "StepOverPercent"):
        if eigenschaft in werte:
            teile.append(f"{zahl_zeigen(float(werte[eigenschaft]))} %")
    if "StepDown" in werte:
        tiefe = groesse_zeigen(float(werte["StepDown"]), einheiten.LAENGE)
        teile.append(f"{tiefe} {einheiten.einheit(einheiten.LAENGE)}")
    for eigenschaft in js.HELIX_WINKEL:
        if eigenschaft in werte:
            teile.append(tr("sj.helix", winkel=zahl_zeigen(float(werte[eigenschaft]))))
    return " · ".join(teile)


def _ebenen_text(dicken):
    """„1 Ebene“, „2 Ebenen (25 + 1 mm)“, „5 Ebenen (4 × 25 + 3 mm)“."""
    if len(dicken) == 1:
        return tr("sj.ebene_eine")

    def zeigen(dicke):
        return groesse_zeigen(dicke, einheiten.LAENGE)

    if len(dicken) <= 3:
        teile = " + ".join(zeigen(d) for d in dicken)
    elif len(set(dicken)) == 1:
        teile = f"{len(dicken)} × {zeigen(dicken[0])}"
    else:
        teile = f"{len(dicken) - 1} × {zeigen(dicken[0])} + {zeigen(dicken[-1])}"
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
        self._pfad = pfad  # die Werkzeugverwaltung; None: die übliche Datei
        try:
            self.bibliothek = wz.Bibliothek.laden(pfad)
        except wz.BeschaedigteDatei as fehler:
            QtGui.QMessageBox.warning(
                self, tr("wv.titel"), tr("wv.fehler.laden", fehler=fehler, datei=fehler.beiseite)
            )
            self.bibliothek = wz.Bibliothek()
        self._zeilen = []  # (tc, werkzeug oder None, Auswahl des Einsatzes)
        self._duenn = {}  # Zeile → [(Satz, vorgeschlagenes ap oder None)] zu dünnen Ebenen
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
                "vf\n" + einheiten.einheit(einheiten.VORSCHUB),
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
        # Controller, die nichts tun und nicht aus der Werkzeugverwaltung kommen (D-30).
        self.unbenutzt = QtGui.QLabel()
        self.unbenutzt.setWordWrap(True)
        self.unbenutzt.setToolTip(tr("sj.unbenutzt.tooltip"))
        self.knopf_unbenutzt_weg = QtGui.QPushButton(tr("sj.unbenutzt.entfernen"))
        self.knopf_unbenutzt_weg.setToolTip(tr("sj.unbenutzt.entfernen.tooltip"))
        self.knopf_unbenutzt_weg.setAutoDefault(False)
        self.knopf_unbenutzt_weg.clicked.connect(self.unbenutzte_entfernen)
        self.zeile_unbenutzt = QtGui.QWidget()
        zeile = QtGui.QHBoxLayout(self.zeile_unbenutzt)
        zeile.setContentsMargins(0, 0, 0, 0)
        zeile.addWidget(self.unbenutzt, 1)
        zeile.addWidget(self.knopf_unbenutzt_weg)
        aufbau.addWidget(self.zeile_unbenutzt)
        self.ebenen_hinweis = hinweiszeile()
        # Mit Verweis „ap … übernehmen“ (D-29).
        self.ebenen_hinweis.setTextFormat(QtCore.Qt.RichText)
        self.ebenen_hinweis.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse
        )
        self.ebenen_hinweis.linkActivated.connect(self.ap_uebernehmen)
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
        ruhiges_mausrad(self)

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
        """Werkstoff vom Rohteil – oder der zuletzt gewählte –, Zeilen für die Controller."""
        job = self.job
        alle = self.bibliothek.alle_werkstoffe()
        werkstoff, gemerkt = js.werkstoff_fuer(job, alle) if job else (None, False)
        index = self.wahl_werkstoff.findData(werkstoff.kennung if werkstoff else wz.ALLE)
        self.wahl_werkstoff.blockSignals(True)
        self.wahl_werkstoff.setCurrentIndex(max(index, 0))
        self.wahl_werkstoff.blockSignals(False)
        if werkstoff is None:
            self.herkunft.setText(tr("sj.herkunft.unbekannt"))
        elif not gemerkt:
            self.herkunft.setText(tr("sj.herkunft.rohteil", werkstoff=ws.anzeige(werkstoff)))
        elif js.werkstoff_des_jobs(job, alle) is not None:
            text = tr("sj.herkunft.rohteil_gemerkt", werkstoff=ws.anzeige(werkstoff))
            self.herkunft.setText(text)
        else:
            self.herkunft.setText(tr("sj.herkunft.gemerkt", werkstoff=ws.anzeige(werkstoff)))
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
            # Beim Blättern in der Tabelle verstellt das Rad den Einsatz nicht.
            wahl = ruhiges_mausrad(QtGui.QComboBox())
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
                vf=groesse_fest(float(tc.HorizFeed.getValueAs("mm/min")), einheiten.VORSCHUB, 0),
            )
            self.tabelle.setItem(zeile, JETZT, grau(jetzt))
        unbenutzt = js.unbenutzte_fremde_controller(self.job, self.bibliothek) if self.job else []
        namen = ", ".join(f"„{tc.Label}“" for tc in unbenutzt)
        self.unbenutzt.setText(tr("sj.unbenutzt", namen=namen))
        self.zeile_unbenutzt.setVisible(bool(unbenutzt))
        self._rechnen()

    def unbenutzte_entfernen(self):
        """„Entfernen“: die unbenutzten fremden Controller samt Werkzeug – ein Schritt
        Rückgängig (D-30). Gibt ihre Namen zurück."""
        unbenutzt = js.unbenutzte_fremde_controller(self.job, self.bibliothek) if self.job else []
        namen = [tc.Label for tc in unbenutzt]
        if unbenutzt:
            js.entferne_controller(self.dokument, unbenutzt, tr("sj.unbenutzt.schritt"))
        self._zeilen_aufbauen()
        return namen

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
            vf = groesse_fest(werte_vf, einheiten.VORSCHUB, 0) if werte_vf else ""
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
                    duenn.append(self._duenn_satz(zeile, operation, werkzeug, *rest))
            zeilen.append(text)
            vorher = _zustellung_text(_jetzt(operation, neu))
            jetzt.append(f"{operation.Label}: {vorher}")
        self._duenn[zeile] = duenn
        zelle = QtGui.QTableWidgetItem("\n".join(zeilen))
        if jetzt:
            zelle.setToolTip(tr("sj.zustellung.jetzt", werte="\n".join(jetzt)))
        return zelle

    @staticmethod
    def _duenn_satz(zeile, operation, werkzeug, rest, ap_ohne):
        """Der Satz zu einer dünnen letzten Ebene – mit ap, wenn die Schneide dafür reicht –
        als (HTML, Verweis „ap:Zeile:Wert“ oder None)."""
        satz = tr(
            "sj.ebene_duenn",
            operation=operation.Label,
            rest=groesse_zeigen(rest, einheiten.LAENGE),
        )
        if not werkzeug.schneidenlaenge or ap_ohne > werkzeug.schneidenlaenge:
            return html.escape(satz, quote=False), None
        ap = groesse_zeigen(ap_ohne, einheiten.LAENGE)
        satz += " " + tr(
            "sj.ebene_duenn.ap",
            ap=ap,
            laenge=groesse_zeigen(werkzeug.schneidenlaenge, einheiten.LAENGE),
        )
        verweis = f"ap:{zeile}:{ap_ohne!r}"
        knopf = html.escape(tr("sj.ebene_duenn.uebernehmen", ap=ap), quote=False)
        return f'{html.escape(satz, quote=False)} <a href="{verweis}">{knopf}</a>', verweis

    def _ebenen_hinweis_zeigen(self):
        """Unter der Tabelle: welche Operation eine dünne letzte Ebene fahren würde."""
        saetze = [s for zeile in sorted(self._duenn) for s, _verweis in self._duenn[zeile]]
        self.ebenen_hinweis.setText("<br>".join(saetze))
        self.ebenen_hinweis.setVisible(bool(saetze) and self.mit_zustellung.isChecked())

    def ap_uebernehmen(self, verweis):
        """„ap:Zeile:Wert“ – die vorgeschlagene Zustelltiefe in den Einsatz der Zeile, in der
        Werkzeugverwaltung gespeichert; danach rechnet der Dialog neu (D-29). Gibt zurück, ob
        es geklappt hat."""
        _art, zeile, wert = verweis.split(":")
        _werkzeug, einsatz = self._gewaehlt(int(zeile))
        if einsatz is None:
            return False
        offen = WerkzeugDialog.offen
        if offen is not None and offen.isVisible():
            # Deren OK schriebe sonst den alten Wert zurück.
            QtGui.QMessageBox.information(self, tr("sj.titel"), tr("sj.ebene_duenn.wv_offen"))
            return False
        einsatz.ap = float(wert)
        try:
            self.bibliothek.speichern(self._pfad)
        except OSError as fehler:
            QtGui.QMessageBox.warning(
                self, tr("wv.titel"), tr("wv.fehler.speichern", fehler=fehler)
            )
            return False
        self._rechnen()
        return True

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
            tc = js.lege_controller_an(self.dokument, self.job, werkzeug, einsatz, self.werkstoff)
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
        if zuordnung:
            gesetzt = js.setze(self.dokument, zuordnung, job, self.werkstoff)
        else:
            gesetzt = js.Gesetzt()
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
