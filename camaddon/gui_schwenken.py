# SPDX-License-Identifier: LGPL-2.1-or-later
"""Befehl und Aufgabenfenster „Ebene schwenken (3+2) …“ (W-014 F5, Spezifikation Strategien 15).

Eine schräge, ebene Fläche am Teil eines Jobs anklicken – das Fenster sagt, wie weit die Ebene
gegen den Tisch gekippt ist und wohin die Rundachsen der Maschine dafür fahren; „OK“ legt die
Ebene als eigenen Job an (schwenken.lege_an) und öffnet auf Wunsch gleich den Assistenten
„Bearbeitung“ darin – dort ist die Fläche oben, und jede Strategie rechnet wie an einer
3-Achs-Maschine. Ein Programm für die Aufspannung schreibt „Programm schreiben“ am Grundjob.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import job_schnittwerte as js
from . import reichweite as rw
from . import schwenken as sw
from . import symbol
from . import vierachs_rohteil as vr
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_zahlen import zahlenformat
from .sprache import tr

GRUEN = "#4e9a06"
ROT = "#cc0000"


class BefehlSchwenken:
    """Befehl: eine Ebene schwenken – aus der gewählten Fläche eines Jobs."""

    def GetResources(self):
        return {
            "Pixmap": symbol("schwenken.svg"),
            "MenuText": tr("befehl.schwenken.titel"),
            "ToolTip": tr("befehl.schwenken.tooltip"),
        }

    def IsActive(self):
        return not FreeCADGui.Control.activeDialog()

    def Activated(self):
        dokument = FreeCAD.ActiveDocument
        job, flaeche = gewaehlt(dokument) if dokument is not None else (None, None)
        if job is None:
            QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(), tr("sw.titel"), tr("sw.kein_job")
            )
            return
        FreeCADGui.Control.showDialog(SchwenkenPanel(job, flaeche))


def gewaehlt(dokument):
    """(Grundjob, Fläche) aus der Auswahl: eine Fläche am Modell eines Jobs (ist der Job selbst
    eine Ebene, ihr Grundjob – die Flächen heißen dort gleich), sonst ein gewählter Job, sonst
    der einzige im Dokument; (None, None), wenn es keinen gibt."""
    jobs = [j for j in js.jobs(dokument) if not hasattr(getattr(j, "Stock", None), "Radius")]
    for auswahl in FreeCADGui.Selection.getSelectionEx(dokument.Name):
        objekt = auswahl.Object
        for job in jobs:
            try:
                klon = vr.modell(job)
            except (AttributeError, IndexError):
                continue
            if objekt is klon or objekt is job or job in objekt.InListRecursive:
                flaechen = [n for n in auswahl.SubElementNames if n.startswith("Face")]
                return rw.grundjob_von(job), (flaechen[0] if flaechen else None)
    grund = [j for j in jobs if not sw.ist_ebene(j)]
    return (grund[0], None) if len(grund) == 1 else (None, None)


def maschine_fuer(job, controller=None):
    """Die verbindliche Jobmaschine, sonst genau eine offene; keine Ersatz-Rundachsen."""
    from .gui_reichweite import _maschine_des_jobs, offene_maschinen

    controller = (
        controller if controller is not None else next(iter(js.werkzeug_controller(job)), None)
    )
    if controller is None or controller not in js.werkzeug_controller(job):
        return None, ""
    bibliothek = wz.Bibliothek.laden()
    eigene = _maschine_des_jobs(job)
    if eigene is not None:
        kandidaten = [eigene]
    elif getattr(job, rw.EIGENSCHAFT_MASCHINE, ""):
        return None, ""  # Eine unlesbare Zuordnung nicht durch eine andere Fräse ersetzen.
    else:
        kandidaten = offene_maschinen(job.Document)
        if len(kandidaten) != 1:
            return None, ""
    for assembly, maschine in kandidaten:
        try:
            pruefung = rw.Pruefung(assembly, maschine)
            aufnahme = pruefung.werkzeugaufnahme(int(controller.ToolNumber))
            if aufnahme is None:
                continue
            ergebnis = sw.Maschine(
                pruefung, aufnahme, rw.einspannung(controller, bibliothek), rw.nullpunkt(job)
            )
        except Exception as fehler:  # Keine unlesbare Definition durch eine andere ersetzen.
            FreeCAD.Console.PrintLog(f"CAM-Addon: Schwenken: {fehler}\n")
            continue
        return ergebnis, maschine.Label
    return None, ""


class SchwenkenPanel:
    """Das Aufgabenfenster: Grundjob, Maschine, die angeklickte Fläche und was daraus wird."""

    offen = None  # für die Szenarien

    def __init__(self, grundjob, flaeche=None):
        self.grundjob = grundjob
        self.flaeche = None
        self.winkel = None  # (Neigung, Richtung) – statt einer Fläche
        self.lage = None
        self.rund = None
        self.vorhanden = None  # der Job einer gleichen Ebene, die es schon gibt
        self._knoepfe = None
        self.werkzeugwahl = QtGui.QComboBox()
        self.werkzeugwahl.setToolTip(tr("sw.panel.werkzeug.tooltip"))
        for tc in js.werkzeug_controller(grundjob):
            self.werkzeugwahl.addItem(tc.Label, tc.Name)
        for obj in FreeCADGui.Selection.getSelection():
            tc = getattr(obj, "ToolController", obj)
            index = self.werkzeugwahl.findData(getattr(tc, "Name", ""))
            if index >= 0:
                self.werkzeugwahl.setCurrentIndex(index)
                break
        self.maschine, maschinenname = (
            maschine_fuer(grundjob, self._controller())
            if self._controller() is not None
            else (None, "")
        )
        self.form = QtGui.QWidget()
        self.form.setWindowTitle(tr("sw.titel"))
        aufbau = QtGui.QVBoxLayout(self.form)
        aufbau.addWidget(kopfzeile(tr("sw.titel"), "schwenken"))
        text = QtGui.QLabel(tr("sw.panel.text"))
        text.setWordWrap(True)
        aufbau.addWidget(text)
        raster = QtGui.QFormLayout()
        raster.addRow(tr("sw.panel.grundjob"), QtGui.QLabel(grundjob.Label))
        self.maschine_text = QtGui.QLabel(
            tr("sw.panel.maschine", maschine=maschinenname)
            if self.maschine is not None
            else tr("sw.panel.ohne_maschine")
        )
        self.maschine_text.setWordWrap(True)
        raster.addRow(tr("sw.panel.maschine_titel"), self.maschine_text)
        raster.addRow(tr("sw.panel.werkzeug"), self.werkzeugwahl)
        self.grenzen_text = QtGui.QLabel(self._grenzen_text())
        self.grenzen_text.setWordWrap(True)
        raster.addRow(tr("sw.panel.grenzen"), self.grenzen_text)
        self.flaeche_text = QtGui.QLabel(tr("sw.panel.anklicken"))
        raster.addRow(tr("sw.panel.flaeche"), self.flaeche_text)
        # Oder ohne Fläche: Neigung und Richtung (angestellter Kugelfräser, Bohrung im Winkel).
        winkel = QtGui.QWidget()
        winkel_aufbau = QtGui.QHBoxLayout(winkel)
        winkel_aufbau.setContentsMargins(0, 0, 0, 0)
        self.feld_neigung = self._winkelfeld(0.0, 180.0, tr("sw.panel.neigung.tooltip"))
        self.feld_richtung = self._winkelfeld(-180.0, 180.0, tr("sw.panel.richtung.tooltip"))
        for beschriftung, feld in (
            (tr("sw.panel.neigung"), self.feld_neigung),
            (tr("sw.panel.richtung"), self.feld_richtung),
        ):
            winkel_aufbau.addWidget(QtGui.QLabel(beschriftung))
            winkel_aufbau.addWidget(feld)
        knopf_winkel = QtGui.QPushButton(tr("sw.panel.winkel_knopf"))
        knopf_winkel.setToolTip(tr("sw.panel.winkel_knopf.tooltip"))
        knopf_winkel.setAutoDefault(False)
        knopf_winkel.clicked.connect(self.winkel_nehmen)
        winkel_aufbau.addWidget(knopf_winkel)
        winkel_aufbau.addStretch()
        raster.addRow(tr("sw.panel.winkel"), winkel)
        aufbau.addLayout(raster)
        self.ergebnis = QtGui.QLabel("")
        self.ergebnis.setWordWrap(True)
        aufbau.addWidget(self.ergebnis)
        self.haken_bearbeiten = QtGui.QCheckBox(tr("sw.panel.bearbeiten"))
        self.haken_bearbeiten.setChecked(True)
        self.haken_bearbeiten.setToolTip(tr("sw.panel.bearbeiten.tooltip"))
        aufbau.addWidget(self.haken_bearbeiten)
        aufbau.addStretch()
        FreeCADGui.Selection.addObserver(self)
        SchwenkenPanel.offen = self
        self.werkzeugwahl.currentIndexChanged.connect(self._werkzeug_wechsel)
        if flaeche:
            self.waehle(flaeche)

    # --- Auswahl -------------------------------------------------------------------------

    def _controller(self):
        name = self.werkzeugwahl.currentData()
        return self.grundjob.Document.getObject(name) if name else None

    def _maschine_neu(self):
        tc = self._controller()
        self.maschine, name = maschine_fuer(self.grundjob, tc) if tc is not None else (None, "")
        self.maschine_text.setText(
            tr("sw.panel.maschine", maschine=name)
            if self.maschine is not None
            else tr("sw.panel.ohne_maschine")
        )
        self.grenzen_text.setText(self._grenzen_text())

    def _werkzeug_wechsel(self, _index):
        self._maschine_neu()
        if self.flaeche is not None:
            self.waehle(self.flaeche)
        elif self.winkel is not None:
            self.winkel_nehmen()
        else:
            self.lage, self.rund, self.vorhanden = None, None, None
            self._zeige(tr("sw.panel.anklicken"), ROT)

    def _grenzen_text(self):
        if self._controller() is None:
            return tr("sw.panel.werkzeug_fehlt")
        if self.maschine is None:
            return tr("sw.panel.maschine_fehlt")
        if not self.maschine.rundachsen:
            return tr("sw.panel.feste_achse")
        zeichen = zahlenformat().decimalPoint()

        def zahl(wert):
            if wert is None:
                return tr("sw.panel.offene_grenze")
            return f"{wert:g}°".replace(".", zeichen).replace("-", "−")

        return "; ".join(
            (
                tr("sw.panel.grenzachse_offen", achse=a.buchstabe)
                if a.minimum is None and a.maximum is None
                else tr(
                    "sw.panel.grenzachse",
                    achse=a.buchstabe,
                    von=zahl(a.minimum),
                    bis=zahl(a.maximum),
                )
            )
            for a in self.maschine.rundachsen
        )

    def addSelection(self, dokument, objekt, unterelement, _punkt):
        if not unterelement or not unterelement.startswith("Face"):
            return
        if dokument != self.grundjob.Document.Name:
            return
        gemeint = self.grundjob.Document.getObject(objekt)
        if gemeint is None:
            return
        klone = [vr.modell(self.grundjob)] + [vr.modell(e) for e in sw.ebenen_von(self.grundjob)]
        if gemeint in klone:
            QtCore.QTimer.singleShot(0, lambda: self.waehle(unterelement))

    def _winkelfeld(self, von, bis, tooltip):
        feld = QtGui.QDoubleSpinBox()
        feld.setLocale(zahlenformat())
        feld.setRange(von, bis)
        feld.setDecimals(1)
        feld.setSuffix(" °")
        feld.setToolTip(tooltip)
        return feld

    def waehle(self, flaeche):
        """Die Fläche (am Modell des Grundjobs): Ebene, Schwenkwinkel und Rundachsen zeigen."""
        self.flaeche, self.winkel = flaeche, None
        self.lage, self.rund, self.vorhanden = None, None, None
        self.flaeche_text.setText(flaeche)
        try:
            lage = sw.ebene_aus_flaeche(vr.modell(self.grundjob).Shape, flaeche)
        except ValueError as grund:
            self._zeige(str(grund), ROT)
            return
        self._pruefen(flaeche, lage)

    def winkel_nehmen(self):
        """„Übernehmen“: die Ebene aus Neigung und Richtung statt aus einer Fläche."""
        neigung, richtung = self.feld_neigung.value(), self.feld_richtung.value()
        self.flaeche, self.winkel = None, (neigung, richtung)
        self.lage, self.rund, self.vorhanden = None, None, None
        bezeichnung = sw.text_winkel(neigung, richtung)
        self.flaeche_text.setText(bezeichnung)
        lage = sw.ebene(sw.normale_aus_winkeln(neigung, richtung), FreeCAD.Vector())
        self._pruefen(bezeichnung, lage)

    def _pruefen(self, flaeche, lage):
        """Schwenkwinkel und Rundachsen der Ebene `lage` – grün, oder rot, warum nicht."""
        self.lage, self.rund, self.vorhanden = None, None, None
        winkel = sw.schwenkwinkel(lage)
        if self.maschine is None:
            self._zeige(
                (
                    tr("sw.panel.werkzeug_fehlt")
                    if self._controller() is None
                    else tr("sw.panel.maschine_fehlt")
                ),
                ROT,
            )
            return
        normale = sw.normale_der(lage)
        if self.maschine is not None:
            loesungen = self.maschine.loese(normale)
            if not loesungen:
                self._zeige(tr("sw.fehler.keine_stellung", flaeche=flaeche), ROT)
                return
            rund = loesungen[0]
            if not all(a.erlaubt(rund[a.buchstabe]) for a in self.maschine.rundachsen):
                text = tr("sw.fehler.grenze", flaeche=flaeche, rundachsen=sw.text_rundachsen(rund))
                self._zeige(text, ROT)
                return
        self.lage, self.rund = lage, rund
        grad = f"{winkel:.1f}".rstrip("0").rstrip(".")
        text = tr(
            "sw.panel.ergebnis", flaeche=flaeche, winkel=grad, rundachsen=sw.text_rundachsen(rund)
        )
        if not rund:
            text = tr("sw.panel.fest_erreichbar", flaeche=flaeche)
        # Eine parallele Fläche (dieselbe Normale) liegt in derselben Ebene: kein zweiter Job.
        self.vorhanden = next(
            (
                e
                for e in sw.ebenen_von(self.grundjob)
                if sw.normale_der(sw.ebene_von(e)).dot(normale) > 1.0 - 1e-9
            ),
            None,
        )
        if winkel < 0.01 and all(abs(w) < 1e-6 for w in rund.values()):
            self.vorhanden = self.grundjob
        if self.vorhanden is not None:
            text += ". " + tr("sw.panel.vorhanden", job=self.vorhanden.Label)
        self._zeige(text, GRUEN)

    def _zeige(self, text, farbe):
        self.ergebnis.setText(text)
        self.ergebnis.setStyleSheet(f"color: {farbe};")
        self._ok_freigeben()

    # --- Knöpfe --------------------------------------------------------------------------

    def getStandardButtons(self):
        return QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel

    def modifyStandardButtons(self, knoepfe):
        """FreeCADs OK nur für eine mit der gewählten Maschine zulässige Richtung freigeben."""
        self._knoepfe = knoepfe
        self._ok_freigeben()

    def _ok_freigeben(self):
        if self._knoepfe is not None:
            self._knoepfe.button(QtGui.QDialogButtonBox.Ok).setEnabled(self.lage is not None)

    def accept(self):
        if self.lage is None:
            self._zeige(self.ergebnis.text() or tr("sw.panel.anklicken"), ROT)
            return False
        # Ein geänderter Maschinenbezug oder Anschlag darf die im Fenster zuvor
        # berechnete Freigabe nicht weiterverwenden.
        self._maschine_neu()
        if self.flaeche is not None:
            self.waehle(self.flaeche)
        else:
            self.winkel_nehmen()
        if self.lage is None:
            return False
        if self.vorhanden is not None:
            job, flaeche = self.vorhanden, self.flaeche
            _zeigen(job)
            bearbeiten = self.haken_bearbeiten.isChecked()
            self._schliessen()
            if bearbeiten:
                QtCore.QTimer.singleShot(0, lambda: _bearbeiten(job, flaeche))
            return True
        dokument = self.grundjob.Document
        dokument.openTransaction(tr("sw.titel"))
        try:
            job = sw.lege_an(self.grundjob, self.flaeche, self.maschine, winkel=self.winkel)
        except Exception as fehler:  # ein Satz statt eines halben Jobs
            dokument.abortTransaction()
            self._zeige(str(fehler), ROT)
            return False
        dokument.commitTransaction()
        _zeigen(job)
        bearbeiten = self.haken_bearbeiten.isChecked()
        flaeche = self.flaeche
        self._schliessen()
        if bearbeiten:
            QtCore.QTimer.singleShot(0, lambda: _bearbeiten(job, flaeche))
        return True

    def reject(self):
        self._schliessen()
        return True

    def _schliessen(self):
        FreeCADGui.Selection.removeObserver(self)
        SchwenkenPanel.offen = None
        FreeCADGui.Control.closeDialog()


def _zeigen(job):
    """Die Ebene zeigen, wie das Werkzeug sie sieht: ihr Modell (die Fläche oben) sichtbar, das
    Teil im Grundjob und das Original ausgeblendet – sonst lägen die Bahnen der Ebene neben
    einem anders gedrehten Teil."""
    klon = vr.modell(job)
    original = vr.original(klon)
    if original.ViewObject is not None:
        original.ViewObject.Visibility = False
    zeige_job(job)
    if klon.ViewObject is not None:
        klon.ViewObject.Transparency = 0


def zeige_job(job):
    """Von den Jobs der Aufspannung (Grundjob und geschwenkte Ebenen) nur `job` zeigen: sein
    Modell und seine Operationen sichtbar, die der anderen nicht – jede Ebene hat ihr Teil anders
    gedreht, und ihre Bahnen passen nur zu ihm. Gibt [(Objekt, war sichtbar)] zurück (für
    zeige_wieder); ohne Ebenen: nichts geändert, leer."""
    from . import bestueckung as bs

    jobs = bs.aufspannung(job)
    vorher = []
    if len(jobs) < 2:
        return vorher
    for j in jobs:
        for objekt in (vr.modell(j), getattr(j, "Operations", None)):
            ansicht = getattr(objekt, "ViewObject", None)
            if ansicht is None:
                continue
            vorher.append((objekt, ansicht.Visibility))
            ansicht.Visibility = j is job
    return vorher


def zeige_wieder(vorher):
    """Die Sichtbarkeit, wie zeige_job sie vorfand."""
    for objekt, sichtbar in vorher:
        try:
            if objekt.ViewObject is not None:
                objekt.ViewObject.Visibility = sichtbar
        except (ReferenceError, RuntimeError):  # inzwischen gelöscht
            pass


def _bearbeiten(job, flaeche):
    """Der Assistent „Bearbeitung“ im Job der Ebene, die Fläche gewählt."""
    from .gui_bearbeitung import BearbeitungPanel

    klon = vr.modell(job)
    FreeCADGui.Selection.clearSelection()
    FreeCADGui.Control.showDialog(
        BearbeitungPanel(job.Document, (vr.original(klon), flaeche), angeklickt=klon)
    )
