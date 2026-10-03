# SPDX-License-Identifier: LGPL-2.1-or-later
"""„Programm schreiben“ – der Postprozessor des Addons mit seinem Fenster (W-005, S1–S3).

Manuel (2026-10-03): „ich möchte nicht den Postprozessor-Generator von FreeCAD nutzen … ich
hätte gern einen guten Postprozessor-Manager“; FreeCADs „Nachbearbeitung“ brach in 1.1.4 mit
„Post processor not identified“ ab. Das Fenster: Job, die Maschine des Jobs mit dem, was der
Postprozessor von ihr weiß, die Steuerung (gemerkt am Job und je Maschine), ihre Befehle zum
Ändern (gemerkt je Steuerung; gelb, was der Maschinenhersteller festlegt), die Vorschau der
ersten Sätze und „Speichern“. Die Maschine ist wählbar – jede offene, auch ungespeichert, und
die gemerkten (Manuel, 2026-10-03: seine neue Drehmaschine war offen, aber nicht gespeichert,
und das Fenster schrieb „Keine Maschine am Job“).
"""

import json
import os

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, symbol
from . import job_schnittwerte as js
from . import maschinenspeicher as msp
from . import postprozessor as pp
from . import reichweite as rw
from .gui_hilfe import kopfzeile
from .gui_teile import knopf, ruhiges_mausrad
from .sprache import tr

EIGENSCHAFT_STEUERUNG = "CamAddonSteuerung"  # am Job: die Kennung der Steuerung
VORSCHAU_SAETZE = 300  # so viele Bewegungssätze zeigt die Vorschau
GELB = "#c4a000"


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def gespeicherte_aenderungen(kennung):
    """{Feld: Text} – was der Benutzer an den Befehlen dieser Steuerung geändert hat."""
    try:
        werte = json.loads(_parameter().GetString(f"Steuerung_{kennung}", "") or "{}")
    except ValueError:
        return {}
    return {k: v for k, v in werte.items() if k in pp.BEFEHLSFELDER and isinstance(v, str)}


def aenderungen_merken(kennung, aenderungen):
    _parameter().SetString(f"Steuerung_{kennung}", json.dumps(aenderungen, ensure_ascii=False))


def steuerung_des_jobs(job):
    """Die Kennung der Steuerung: am Job gemerkt, sonst die für seine Maschine zuletzt
    gewählte, sonst die zuletzt gewählte, sonst LinuxCNC."""
    kennung = getattr(job, EIGENSCHAFT_STEUERUNG, "") if job is not None else ""
    if kennung in pp.STEUERUNGEN:
        return kennung
    try:
        je_maschine = json.loads(_parameter().GetString("SteuerungJeMaschine", "") or "{}")
    except ValueError:
        je_maschine = {}
    pfad = rw.gemerkte_maschine(job) if job is not None else ""
    kennung = je_maschine.get(os.path.normcase(pfad)) if pfad else None
    if kennung in pp.STEUERUNGEN:
        return kennung
    kennung = _parameter().GetString("SteuerungZuletzt", pp.VORGABE)
    return kennung if kennung in pp.STEUERUNGEN else pp.VORGABE


def steuerung_merken(job, kennung):
    """Merkt die Steuerung am Job (ausgeblendete Eigenschaft), je Maschine und als letzte."""
    if job is not None:
        if EIGENSCHAFT_STEUERUNG not in job.PropertiesList:
            job.addProperty(
                "App::PropertyString", EIGENSCHAFT_STEUERUNG, "CAM-Addon", tr("pp.eigenschaft")
            )
            job.setEditorMode(EIGENSCHAFT_STEUERUNG, 2)
        if getattr(job, EIGENSCHAFT_STEUERUNG) != kennung:
            setattr(job, EIGENSCHAFT_STEUERUNG, kennung)
        pfad = rw.gemerkte_maschine(job)
        if pfad:
            try:
                je_maschine = json.loads(_parameter().GetString("SteuerungJeMaschine", "") or "{}")
            except ValueError:
                je_maschine = {}
            je_maschine[os.path.normcase(pfad)] = kennung
            _parameter().SetString("SteuerungJeMaschine", json.dumps(je_maschine))
    _parameter().SetString("SteuerungZuletzt", kennung)


class BefehlProgrammSchreiben:
    """Befehl: das NC-Programm eines Jobs mit dem Postprozessor des Addons schreiben."""

    def GetResources(self):
        return {
            "Pixmap": symbol("programm.svg"),
            "MenuText": tr("befehl.programm.titel"),
            "ToolTip": tr("befehl.programm.tooltip"),
        }

    def IsActive(self):
        return True

    def Activated(self):
        from .gui_job_schnittwerte import dokument_mit_job
        from .gui_reichweite import gewaehlter_job

        dokument = dokument_mit_job(tr("pp.titel"), tr("pp.kein_job"))
        if dokument is None:
            return
        jobs = js.jobs(dokument)
        dialog = ProgrammDialog(jobs, gewaehlter_job(jobs) or jobs[0])
        dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        dialog.show()


class ProgrammDialog(QtGui.QDialog):
    """Job, Maschine, Steuerung, Befehle, Vorschau, Datei – und „Speichern“."""

    offen = None  # für die Szenarien

    def __init__(self, jobs, job, eltern=None):
        super().__init__(eltern or FreeCADGui.getMainWindow())
        ProgrammDialog.offen = self
        self.jobs = list(jobs)
        self.job = job
        self.info = pp.Maschineninfo()
        self._maschinen = []  # [(Name, Pfad, Dokument)] – pp.maschinen_zur_wahl()
        self._ungespeichert = False  # die gewählte Maschine liegt in keiner Datei
        self._fuellt = False
        self.setWindowTitle(tr("pp.titel"))
        self.resize(820, 760)
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(kopfzeile(tr("pp.titel"), "programm"))
        erklaerung = QtGui.QLabel(tr("pp.erklaerung"))
        erklaerung.setWordWrap(True)
        aufbau.addWidget(erklaerung)

        raster = QtGui.QGridLayout()
        self.wahl_job = QtGui.QComboBox()
        for j in self.jobs:
            self.wahl_job.addItem(j.Label)
        self.wahl_job.currentIndexChanged.connect(self._job_gewaehlt)
        raster.addWidget(QtGui.QLabel(tr("pp.job")), 0, 0)
        raster.addWidget(self.wahl_job, 0, 1)
        self.wahl_maschine = QtGui.QComboBox()
        self.wahl_maschine.setToolTip(tr("pp.maschine.wahl.tooltip"))
        self.wahl_maschine.currentIndexChanged.connect(self._maschine_gewaehlt)
        self.maschine_text = QtGui.QLabel()
        self.maschine_text.setWordWrap(True)
        spalte = QtGui.QVBoxLayout()
        spalte.addWidget(self.wahl_maschine)
        spalte.addWidget(self.maschine_text)
        raster.addWidget(QtGui.QLabel(tr("pp.maschine")), 1, 0, QtCore.Qt.AlignTop)
        raster.addLayout(spalte, 1, 1)
        self.wahl_steuerung = QtGui.QComboBox()
        for kennung, s in pp.STEUERUNGEN.items():
            self.wahl_steuerung.addItem(s.name, kennung)
        self.wahl_steuerung.setToolTip(tr("pp.steuerung.tooltip"))
        self.wahl_steuerung.currentIndexChanged.connect(self._steuerung_gewaehlt)
        self.knopf_befehle = knopf(tr("pp.befehle"), tr("pp.befehle.tooltip"), self._befehle_zeigen)
        self.knopf_befehle.setCheckable(True)
        zeile = QtGui.QHBoxLayout()
        zeile.addWidget(self.wahl_steuerung, 1)
        zeile.addWidget(self.knopf_befehle)
        raster.addWidget(QtGui.QLabel(tr("pp.steuerung")), 2, 0)
        raster.addLayout(zeile, 2, 1)
        raster.setColumnStretch(1, 1)
        aufbau.addLayout(raster)

        # Die Befehle der Steuerung – eingeklappt, bis man „Befehle …“ drückt.
        self.befehle = QtGui.QWidget()
        befehle_aufbau = QtGui.QVBoxLayout(self.befehle)
        befehle_aufbau.setContentsMargins(0, 0, 0, 0)
        self.tabelle = QtGui.QTableWidget(len(pp.BEFEHLSFELDER), 2)
        self.tabelle.setHorizontalHeaderLabels([tr("pp.spalte.befehl"), tr("pp.spalte.text")])
        self.tabelle.horizontalHeader().setStretchLastSection(True)
        self.tabelle.verticalHeader().setVisible(False)
        self.tabelle.itemChanged.connect(self._befehl_geaendert)
        befehle_aufbau.addWidget(self.tabelle)
        zeile = QtGui.QHBoxLayout()
        self.befehle_hinweis = QtGui.QLabel(tr("pp.befehle.hinweis"))
        self.befehle_hinweis.setWordWrap(True)
        zeile.addWidget(self.befehle_hinweis, 1)
        self.knopf_zuruecksetzen = knopf(
            tr("pp.zuruecksetzen"), tr("pp.zuruecksetzen.tooltip"), self.zuruecksetzen
        )
        zeile.addWidget(self.knopf_zuruecksetzen)
        befehle_aufbau.addLayout(zeile)
        self.befehle.hide()
        aufbau.addWidget(self.befehle)

        self.hinweise = QtGui.QLabel()
        self.hinweise.setWordWrap(True)
        self.hinweise.setStyleSheet(f"color: {GELB};")
        aufbau.addWidget(self.hinweise)
        aufbau.addWidget(QtGui.QLabel(tr("pp.vorschau")))
        self.vorschau = QtGui.QPlainTextEdit()
        self.vorschau.setReadOnly(True)
        schrift = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        self.vorschau.setFont(schrift)
        self.vorschau.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        aufbau.addWidget(self.vorschau, 1)

        zeile = QtGui.QHBoxLayout()
        zeile.addWidget(QtGui.QLabel(tr("pp.datei")))
        self.feld_datei = QtGui.QLineEdit()
        zeile.addWidget(self.feld_datei, 1)
        zeile.addWidget(knopf("…", tr("pp.datei.waehlen"), self._datei_waehlen))
        aufbau.addLayout(zeile)
        self.ergebnis = QtGui.QLabel()
        self.ergebnis.setWordWrap(True)
        aufbau.addWidget(self.ergebnis)
        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Close)
        self.knopf_speichern = knoepfe.addButton(
            tr("pp.speichern"), QtGui.QDialogButtonBox.ActionRole
        )
        self.knopf_speichern.setToolTip(tr("pp.speichern.tooltip"))
        self.knopf_speichern.clicked.connect(self.speichern)
        knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(knoepfe)
        ruhiges_mausrad(self)
        self.wahl_job.setCurrentIndex(max(0, self.jobs.index(job) if job in self.jobs else 0))
        self._job_gewaehlt(self.wahl_job.currentIndex())

    # --- Job, Maschine, Steuerung ---------------------------------------------------------

    def _job_gewaehlt(self, index):
        if not 0 <= index < len(self.jobs):
            return
        self.job = self.jobs[index]
        self._fuellt = True
        try:
            self._maschinen_fuellen()
            kennung = steuerung_des_jobs(self.job)
            self.wahl_steuerung.setCurrentIndex(max(0, self.wahl_steuerung.findData(kennung)))
        finally:
            self._fuellt = False
        self._steuerung_gewaehlt()

    def _maschinen_fuellen(self):
        """Die Maschinen zur Wahl – gewählt die, die sich der Job gemerkt hat; hat er keine, die
        erste offene (auch ungespeichert); sonst „keine“."""
        self._maschinen = pp.maschinen_zur_wahl()
        pfad = rw.gemerkte_maschine(self.job)
        gewaehlt = next(
            (k for k, (_n, p, _d) in enumerate(self._maschinen) if msp.gleiche_datei(p, pfad)),
            None,
        )
        if gewaehlt is None and pfad and os.path.isfile(pfad):
            self._maschinen.append((os.path.splitext(os.path.basename(pfad))[0], pfad, None))
            gewaehlt = len(self._maschinen) - 1
        if gewaehlt is None:
            gewaehlt = next(
                (k for k, (_n, _p, d) in enumerate(self._maschinen) if d is not None), None
            )
        self.wahl_maschine.blockSignals(True)
        try:
            self.wahl_maschine.clear()
            self.wahl_maschine.addItem(tr("pp.maschine.keine_wahl"))
            for name, pfad_, dok in self._maschinen:
                if dok is not None and not pfad_:
                    name = f"{name} – {tr('pp.maschine.nicht_gespeichert')}"
                self.wahl_maschine.addItem(name)
            self.wahl_maschine.setCurrentIndex(0 if gewaehlt is None else gewaehlt + 1)
        finally:
            self.wahl_maschine.blockSignals(False)
        self._maschine_gewaehlt()

    def maschine_waehlen(self, name):
        """Wählt die Maschine mit diesem Namen (wie in der Liste, ohne Zusatz) – für die
        Szenarien; gibt zurück, ob es sie gibt."""
        for k, (n, _p, _d) in enumerate(self._maschinen):
            if n == name:
                self.wahl_maschine.setCurrentIndex(k + 1)
                return True
        return False

    def _maschine_gewaehlt(self, *_):
        """Was der Postprozessor von der gewählten Maschine weiß; gewählt mit Datei, merkt sich
        der Job sie (wie beim Prüfen)."""
        k = self.wahl_maschine.currentIndex() - 1
        self._ungespeichert = False
        if 0 <= k < len(self._maschinen):
            _name, pfad, dok = self._maschinen[k]
            if dok is not None:
                self.info = pp.maschineninfo_dokument(dok)
            else:
                self.info = pp.maschineninfo_datei(pfad)
            self._ungespeichert = not pfad
            if pfad and not self._fuellt and self.job is not None:
                rw.merke_maschine(self.job, pfad)
        else:
            self.info = pp.Maschineninfo()
        self.maschine_text.setText(self._maschine_beschreiben())
        if not self._fuellt:
            self.vorschau_rechnen()

    def _maschine_beschreiben(self):
        i = self.info
        if not i.name:
            return tr("pp.maschine.keine")
        teile = [tr("pp.maschine.drehen") if i.drehmaschine else tr("pp.maschine.fraesen")]
        if i.drehmaschine:
            teile.append(tr("pp.maschine.x_d") if i.x_durchmesser else tr("pp.maschine.x_r"))
        rundachsen = dict(i.rundachsen)
        if i.drehmaschine and (i.hauptspindel_name or "C" in rundachsen):
            teile.append(
                tr(
                    "pp.maschine.hauptspindel",
                    s=i.hauptspindel_name or "–",
                    c=rundachsen.pop("C", "–"),
                )
            )
        for buchstabe, name in sorted(rundachsen.items()):
            teile.append(tr("pp.maschine.rundachse", buchstabe=buchstabe, name=name))
        if i.angetrieben:
            je_antrieb = {}
            for t, n in sorted(i.angetrieben.items()):
                je_antrieb.setdefault(n, []).append(t)
            plaetze = ", ".join(
                (f"T{t[0]}" if len(t) == 1 else f"T{t[0]}…T{t[-1]}")
                + f" → S{n}"
                + (f" ({i.antrieb_c[n]})" if n in i.antrieb_c else "")
                for n, t in je_antrieb.items()
            )
            teile.append(tr("pp.maschine.angetrieben", plaetze=plaetze))
        if i.wechselpunkt:
            punkt = " ".join(
                f"{b} {(w * 2.0 if b == 'X' and i.drehmaschine and i.x_durchmesser else w):g}"
                for b, w in sorted(i.wechselpunkt.items())
            )
            bezug = "WKS" if i.wechsel_wks else "MKS"
            teile.append(tr("pp.maschine.wechselpunkt", punkt=punkt, bezug=bezug))
        else:
            teile.append(tr("pp.maschine.ohne_wechselpunkt"))
        text = f"{i.name} – " + " · ".join(teile)
        if self._ungespeichert:
            text += "\n" + tr("pp.maschine.ungespeichert")
        return text

    def kennung(self):
        return self.wahl_steuerung.currentData() or pp.VORGABE

    def steuerung(self):
        return pp.steuerung(self.kennung(), gespeicherte_aenderungen(self.kennung()))

    def _steuerung_gewaehlt(self, *_):
        if not self._fuellt:
            steuerung_merken(self.job, self.kennung())
        self._tabelle_fuellen()
        self.feld_datei.setText(pp.dateiname(self.job, self.steuerung()))
        self.vorschau_rechnen()

    # --- Befehle ------------------------------------------------------------------------

    def _befehle_zeigen(self):
        self.befehle.setVisible(self.knopf_befehle.isChecked())

    def _tabelle_fuellen(self):
        s = self.steuerung()
        geaendert = gespeicherte_aenderungen(self.kennung())
        self.tabelle.blockSignals(True)
        try:
            for zeile, feld in enumerate(pp.BEFEHLSFELDER):
                titel, erklaerung = pp.feld_text(feld)
                name = QtGui.QTableWidgetItem(titel)
                name.setFlags(QtCore.Qt.ItemIsEnabled)
                name.setToolTip(erklaerung)
                text = QtGui.QTableWidgetItem(getattr(s, feld).replace("\n", " | "))
                text.setData(QtCore.Qt.UserRole, feld)
                if feld in s.vom_hersteller:
                    for eintrag in (name, text):
                        eintrag.setForeground(QtGui.QColor(GELB))
                    text.setToolTip(tr("pp.feld.hersteller"))
                if feld in geaendert:
                    schrift = text.font()
                    schrift.setBold(True)
                    text.setFont(schrift)
                self.tabelle.setItem(zeile, 0, name)
                self.tabelle.setItem(zeile, 1, text)
            self.tabelle.resizeColumnToContents(0)
        finally:
            self.tabelle.blockSignals(False)

    def _befehl_geaendert(self, eintrag):
        feld = eintrag.data(QtCore.Qt.UserRole)
        if feld not in pp.BEFEHLSFELDER:
            return
        self.befehl_setzen(feld, eintrag.text().replace(" | ", "\n"))

    def befehl_setzen(self, feld, text):
        """Ändert einen Befehl der gewählten Steuerung (gemerkt je Steuerung)."""
        aenderungen = gespeicherte_aenderungen(self.kennung())
        if text == getattr(pp.STEUERUNGEN[self.kennung()], feld):
            aenderungen.pop(feld, None)
        else:
            aenderungen[feld] = text
        aenderungen_merken(self.kennung(), aenderungen)
        self._tabelle_fuellen()
        self.vorschau_rechnen()

    def zuruecksetzen(self):
        """Alle Befehle der gewählten Steuerung wie vorbelegt."""
        aenderungen_merken(self.kennung(), {})
        self._tabelle_fuellen()
        self.vorschau_rechnen()

    # --- Vorschau und Speichern ---------------------------------------------------------

    def _programm(self, vorschau=None):
        return pp.programm(
            pp.abschnitte(self.job), self.steuerung(), self.info, self.job.Label, vorschau
        )

    def vorschau_rechnen(self):
        if self.job is None:
            return
        programm = self._programm(VORSCHAU_SAETZE)
        self.vorschau.setPlainText(programm.text)
        self.hinweise.setText("\n".join(programm.hinweise))
        self.hinweise.setVisible(bool(programm.hinweise))
        self.ergebnis.setText("")

    def _datei_waehlen(self):
        s = self.steuerung()
        pfad, _filter = QtGui.QFileDialog.getSaveFileName(
            self, tr("pp.datei.waehlen"), self.feld_datei.text(), f"*{s.endung};;*"
        )
        if pfad:
            self.feld_datei.setText(pfad)

    def speichern(self):
        """Schreibt das ganze Programm in die Datei; gibt den Pfad zurück (None, wenn es nicht
        ging – der Grund steht im Fenster)."""
        pfad = self.feld_datei.text().strip()
        if not pfad:
            self._datei_waehlen()
            pfad = self.feld_datei.text().strip()
            if not pfad:
                return None
        programm = self._programm()
        try:
            with open(pfad, "w", encoding="utf-8", newline="\n") as datei:
                datei.write(programm.text)
        except OSError as fehler:
            self.ergebnis.setText(tr("pp.fehler.speichern", fehler=str(fehler)))
            self.ergebnis.setStyleSheet("color: #cc0000;")
            return None
        steuerung_merken(self.job, self.kennung())
        self.ergebnis.setStyleSheet("")
        self.ergebnis.setText(
            tr("pp.gespeichert", datei=pfad, saetze=programm.saetze, zeilen=len(programm.zeilen))
        )
        return pfad

    def done(self, ergebnis):
        ProgrammDialog.offen = None
        super().done(ergebnis)
