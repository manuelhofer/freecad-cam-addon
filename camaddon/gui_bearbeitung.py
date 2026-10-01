# SPDX-License-Identifier: LGPL-2.1-or-later
"""Befehl und Assistent „Bearbeitung (Fräsen)“ für ein Teil im Quader (W-006 S3c, E4).

Der Weg: eine Fläche des Teils anklicken – der Job mit dem Rohteil (ein Quader mit Aufmaß je
Seite, wie FreeCADs Job) entsteht sofort –, die Flächen, die eben werden sollen (ohne Wahl
die Oberseite), Werkstoff, Fräser und Einsatz aus der Werkzeugverwaltung, Zustellung,
Zeilenabstand, Aufmaß mit den Vorschlägen grau, darunter „→ 3 Lagen, 30 Zeilen, etwa
2 min“ – und „Anlegen“ legt Werkzeug-Controller und „Planfräsen“ (planfraesen) an. Ein
Doppelklick auf die Operation öffnet den Assistenten zum Ändern (gui_vierachs_operation).

Der Assistent „4-Achs-Bearbeitung“ (gui_vierachs) ist das Vorbild; was dort allgemein ist
(Reihen, Befehl mit Transaktion, Zeit in Worten), kommt von dort. Weitere Strategien (Kontur,
Tasche adaptiv, Bohren) kommen als weitere Blöcke mit Vorschlag und Grund dazu (S3e–S3g).
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, einheiten, symbol
from . import bahn as bn
from . import fraeserform as ff
from . import hoehenfeld as hf
from . import job_schnittwerte as js
from . import planfraesen as pf
from . import uebergabe_werkzeuge as ue
from . import vierachs_plan as vplan
from . import vierachs_planbahn as vp
from . import vierachs_rohteil as vr
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_maschine import _EnterBleibtImDialog
from .gui_teile import ROT, knopf, mit_einheit, ruhiges_mausrad
from .gui_vierachs import (
    GRAU_TEXT,
    GRUEN,
    _entlang,
    _globale_transaktionen,
    _im_befehl,
    _Reihen,
    _zeit_text,
    gewaehlte_flaeche,
    job_von,
)
from .gui_zahlen import Zahlenpruefer, dezimal, groesse_fest, groesse_lesen, groesse_zeigen
from .sprache import tr

AUFMASS_ROHTEIL = 1.0  # mm je Seite, wie FreeCADs Job
GEMERKT_FRAESER = "BaFraeser"  # Kennung des zuletzt gewählten Fräsers
VORSCHAU_MS = 400  # nach der letzten Eingabe so lange warten, dann die Bahn rechnen
NACHZIEHEN_MS = 250  # das Rohteil nach einer Eingabe nachziehen
ROHTEIL_FELDER = ("oben", "seite", "unten")


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def _mm(wert):
    """Eine Länge des Rohteils (Quantity oder Zahl) in mm."""
    try:
        return float(wert.getValueAs("mm"))
    except AttributeError:
        return float(wert)


def _grau(text=""):
    """Ein grauer Satz – Erklärungen und gerechnete Werte (wie in gui_vierachs)."""
    etikett = QtGui.QLabel(text)
    etikett.setStyleSheet(f"color: {GRAU_TEXT};")
    etikett.setWordWrap(True)
    return etikett


class BefehlBearbeitung:
    """Befehl in der Werkzeugleiste: öffnet den Assistenten für die gewählte Fläche – oder
    zum Ändern, wenn „Planfräsen“ gewählt ist."""

    def GetResources(self):
        return {
            "Pixmap": symbol("bearbeitung.svg"),
            "MenuText": tr("befehl.bearbeitung.titel"),
            "ToolTip": tr("befehl.bearbeitung.tooltip"),
        }

    def IsActive(self):
        return not FreeCADGui.Control.activeDialog()

    def Activated(self):
        dokument = FreeCAD.ActiveDocument
        if dokument is None:
            QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(), tr("ba.titel"), tr("ba.kein_dokument")
            )
            return
        operation = gewaehlte_operation(dokument)
        if operation is not None:
            bearbeiten(operation)
            return
        FreeCADGui.Control.showDialog(BearbeitungPanel(dokument, gewaehlte_flaeche(dokument)))


def gewaehlte_operation(dokument):
    """Das gewählte „Planfräsen“ – oder, ist ein Job oder sein Ordner „Operations“ gewählt,
    sein erstes „Planfräsen“; sonst None."""
    jobs = js.jobs(dokument)
    for objekt in FreeCADGui.Selection.getSelection(dokument.Name):
        if pf.ist_planfraesen(objekt):
            return objekt
        job = next(
            (j for j in jobs if objekt is j or objekt is getattr(j, "Operations", None)), None
        )
        if job is not None:
            gefunden = [o for o in js.operationen(job) if pf.ist_planfraesen(o)]
            if gefunden:
                return gefunden[0]
    return None


def bearbeiten(operation):
    """Öffnet den Assistenten zum Ändern von `operation` – mit ihren Werten. Nichts, solange
    ein anderes Aufgabenfenster offen ist."""
    if FreeCADGui.Control.activeDialog():
        return
    FreeCADGui.Control.showDialog(BearbeitungPanel(operation.Document, operation=operation))


class _Beobachter:
    """Meldet dem Assistenten jede angeklickte Fläche."""

    def __init__(self, panel):
        self.panel = panel

    def addSelection(self, _dokument, objekt, unterelement, _punkt):
        if not unterelement:
            return
        # Erst wenn FreeCAD mit der Auswahl fertig ist – der Assistent ändert das Dokument.
        QtCore.QTimer.singleShot(0, lambda: self.panel.angeklickt(objekt, unterelement))


class _NurFlaechen:
    """Anklicken lassen sich nur Flächen – mit Job nur die des Teils darin."""

    def __init__(self, panel):
        self.panel = panel

    def allow(self, _dokument, objekt, unterelement):
        weg = unterelement.split(".") if unterelement else []
        if not weg or not weg[-1].startswith("Face"):
            return False
        job = self.panel.job
        if job is None:
            return True
        klon = vr.modell(job).Name
        return getattr(objekt, "Name", "") == klon or klon in weg


class BearbeitungPanel:
    """Aufgabenfenster „Bearbeitung (Fräsen)“ – anlegen, oder mit `operation=` ändern."""

    offen = None  # das offene Fenster – für die Oberflächen-Szenarien

    def __init__(self, dokument, wahl=None, operation=None):
        BearbeitungPanel.offen = self
        self.doc = dokument
        self.job = None
        self.teil = None
        self.bibliothek = None
        self._fraeser = []  # die Werkzeuge in der Auswahl „Fräser“
        self._einsaetze = []
        self.gewaehlte = []  # die Flächen („Face6“ …) – leer: die Oberseite
        self.vorschau = None  # die grobe Bahn (planfraesen_bahn.Planbahn) oder None
        self.operation = operation  # die angelegte Operation – oder die, die man ändert
        self.zu_aendern = operation
        self._tc_vorher = operation.ToolController if operation is not None else None
        self._vorwahl = None  # beim Ändern: Kennung des Fräsers der Operation
        self._fuellt = False
        self.geschlossen = False
        self._knoepfe = None
        self._beobachter = None
        self._sichtbar_vorher = None  # (Teil, war sichtbar) – das Original
        self._farben_vorher = None  # (Klon, DiffuseColor, ShapeAppearance) vor dem Färben
        self._job_offen = False  # die Transaktion des neuen Jobs ist offen
        self._job_fest = False  # der Job liegt schon als Schritt Rückgängig ab
        self._undo_vorher = len(dokument.UndoNames)
        self._vorschau_uhr = QtCore.QTimer()
        self._vorschau_uhr.setSingleShot(True)
        self._vorschau_uhr.setInterval(VORSCHAU_MS)
        self._vorschau_uhr.timeout.connect(self._vorschau_rechnen)
        self._rohteil_uhr = QtCore.QTimer()
        self._rohteil_uhr.setSingleShot(True)
        self._rohteil_uhr.setInterval(NACHZIEHEN_MS)
        self._rohteil_uhr.timeout.connect(self._rohteil_anwenden)
        self.form = self._baue()
        self._beobachter = _Beobachter(self)
        FreeCADGui.Selection.addObserver(self._beobachter)
        FreeCADGui.Selection.addSelectionGate(_NurFlaechen(self))
        if operation is not None:
            self._zum_aendern()
            return
        if wahl is not None:
            self.teil_waehlen(*wahl)
        self._auffrischen()

    # --- Aufbau -------------------------------------------------------------------------

    def _baue(self):
        form = QtGui.QWidget()
        form.setWindowTitle(tr("ba.titel"))
        form.setWindowIcon(QtGui.QIcon(symbol("bearbeitung.svg")))
        self._enter_filter = _EnterBleibtImDialog(form)
        form.installEventFilter(self._enter_filter)
        aufbau = QtGui.QVBoxLayout(form)
        kopf = kopfzeile(tr("ba.kopf"), "bearbeitung")
        aufbau.addWidget(kopf)
        self.anleitung = QtGui.QLabel(tr("ba.anleitung"))
        self.anleitung.setWordWrap(True)
        aufbau.addWidget(self.anleitung)

        def zahlenfeld(felder, name, text, tooltip, reihen, geaendert):
            eingabe = QtGui.QLineEdit()
            eingabe.setValidator(Zahlenpruefer(eingabe))
            eingabe.textChanged.connect(lambda _text: geaendert())
            felder[name] = eingabe
            reihen.reihe(text, tooltip, mit_einheit(eingabe, einheiten.einheit(einheiten.LAENGE)))
            return eingabe

        def titel(text, tooltip=""):
            etikett = QtGui.QLabel(text)
            etikett.setToolTip(tooltip)
            schrift = etikett.font()
            schrift.setBold(True)
            etikett.setFont(schrift)
            aufbau.addWidget(etikett)
            return etikett

        def grautext(text=""):
            etikett = _grau(text)
            aufbau.addWidget(etikett)
            return etikett

        # --- Teil und Rohteil ---
        oben = _Reihen()
        self.teil_text = QtGui.QLabel(tr("ba.teil.keins"))
        self.teil_text.setWordWrap(True)
        oben.reihe(tr("ba.teil"), "", self.teil_text)
        aufbau.addWidget(oben.widget)
        titel(tr("ba.rohteil"), tr("ba.rohteil.text"))
        grautext(tr("ba.rohteil.text"))
        rohteil = _Reihen()
        self.felder_rohteil = {}
        for feld, text, tooltip in (
            ("oben", tr("ba.rohteil.oben"), tr("ba.rohteil.oben.tooltip")),
            ("seite", tr("ba.rohteil.seite"), tr("ba.rohteil.seite.tooltip")),
            ("unten", tr("ba.rohteil.unten"), tr("ba.rohteil.unten.tooltip")),
        ):
            eingabe = zahlenfeld(
                self.felder_rohteil, feld, text, tooltip, rohteil, self._rohteil_geaendert
            )
            eingabe.setPlaceholderText(groesse_zeigen(AUFMASS_ROHTEIL, einheiten.LAENGE) or "0")
        self.rohteilfelder = rohteil.widget
        aufbau.addWidget(self.rohteilfelder)

        # --- Flächen ---
        titel(tr("ba.flaechen"), tr("ba.flaechen.tooltip"))
        self.flaechen_liste = QtGui.QListWidget()
        self.flaechen_liste.setToolTip(tr("ba.flaechen.liste.tooltip"))
        self.flaechen_liste.setMaximumHeight(90)
        self.flaechen_liste.itemDoubleClicked.connect(
            lambda eintrag: self.flaeche_umschalten(eintrag.data(QtCore.Qt.UserRole))
        )
        aufbau.addWidget(self.flaechen_liste)
        self.flaechen_text = grautext()
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        knoepfe.addWidget(
            knopf(
                tr("ba.flaechen.oberseite_knopf"),
                tr("ba.flaechen.oberseite_knopf.tooltip"),
                self.oberseite_waehlen,
            )
        )
        knoepfe.addWidget(
            knopf(tr("ba.flaechen.leeren"), tr("ba.flaechen.leeren.tooltip"), self.flaechen_leeren)
        )
        knoepfe.addStretch()
        aufbau.addWidget(zeile)

        # --- Werkstoff und Werkzeugverwaltung ---
        werkstoff = _Reihen()
        self.wahl_werkstoff = QtGui.QComboBox()
        self.wahl_werkstoff.currentIndexChanged.connect(lambda _i: self._werkstoff_gewaehlt())
        werkstoff.reihe(tr("va.werkstoff"), tr("va.werkstoff.tooltip"), self.wahl_werkstoff)
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        knoepfe.addWidget(
            knopf(
                tr("va.werkzeugverwaltung"),
                tr("va.werkzeugverwaltung.tooltip"),
                self.werkzeugverwaltung,
            )
        )
        knoepfe.addStretch()
        werkstoff.ganz(zeile)
        aufbau.addWidget(werkstoff.widget)

        # --- Planfräsen ---
        titel(tr("ba.planfraesen"), tr("ba.planfraesen.text"))
        self.erklaerung = grautext(tr("ba.planfraesen.text"))
        plan = _Reihen()
        self.wahl_fraeser = QtGui.QComboBox()
        self.wahl_fraeser.currentIndexChanged.connect(lambda _i: self._fraeser_gewaehlt())
        plan.reihe(tr("va.fraeser"), tr("ba.planfraeser.tooltip"), self.wahl_fraeser)
        self.wahl_einsatz = QtGui.QComboBox()
        self.wahl_einsatz.currentIndexChanged.connect(lambda _i: self._einsatz_gewaehlt())
        plan.reihe(tr("va.einsatz"), tr("ba.planeinsatz.tooltip"), self.wahl_einsatz)
        self.schnittwerte = _grau()
        plan.ganz(self.schnittwerte)
        self.felder = {}
        for feld, text, tooltip in (
            ("zustellung", tr("ba.zustellung"), tr("ba.zustellung.tooltip")),
            ("zeilenabstand", tr("ba.zeilenabstand"), tr("ba.zeilenabstand.tooltip")),
            ("aufmass", tr("ba.aufmass"), tr("ba.aufmass.tooltip")),
        ):
            zahlenfeld(self.felder, feld, text, tooltip, plan, self._vorschau_starten)
        self.planfelder = plan.widget
        aufbau.addWidget(self.planfelder)
        self.ergebnis = grautext()
        self.hinweis = QtGui.QLabel()
        self.hinweis.setWordWrap(True)
        self.hinweis.setStyleSheet(f"color: {ROT};")
        aufbau.addWidget(self.hinweis)
        # Die Beschriftungen aller Blöcke gleich breit: die Felder stehen untereinander.
        bloecke = (oben, rohteil, werkstoff, plan)
        breite = max(r.breite_beschriftung() for r in bloecke)
        for reihen in bloecke:
            reihen.raster.setColumnMinimumWidth(0, breite)
        aufbau.addStretch()
        ruhiges_mausrad(form)
        return form

    # --- Schnittstelle zu FreeCAD ---------------------------------------------------------

    def getStandardButtons(self):
        return QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel

    def modifyStandardButtons(self, knoepfe):
        self._knoepfe = knoepfe
        self._knoepfe_beschriften()

    def knopf_anlegen(self):
        if self._knoepfe is None:
            return None
        return self._knoepfe.button(QtGui.QDialogButtonBox.Ok)

    def _knoepfe_beschriften(self):
        ok = self.knopf_anlegen()
        if ok is None:
            return
        if self.zu_aendern is not None:
            ok.setText(tr("va.uebernehmen"))
            ok.setToolTip(tr("ba.uebernehmen.tooltip"))
        else:
            ok.setText(tr("va.anlegen"))
            ok.setToolTip(tr("ba.anlegen.tooltip"))
        ok.setEnabled(self.job is not None and self._kann_anlegen())

    def _kann_anlegen(self):
        if self.fraeser() is None or self.einsatz() is None:
            return False
        return not self.hinweis.text()

    def accept(self):
        if self.job is None:
            return self.reject()
        if self._rohteil_uhr.isActive():
            self._rohteil_uhr.stop()
            self._rohteil_anwenden()
        if self.vorschau is None:
            self._vorschau_rechnen()
        if not self._kann_anlegen() or self.vorschau is None:
            return False  # der Grund steht rot im Fenster
        if self.zu_aendern is not None:
            if not self._aendern():
                return False
        else:
            # Job und Rohteil: ein Schritt Rückgängig. Die Operation kommt in einem eigenen –
            # in einen gemeinsamen lässt FreeCAD es nicht (_im_befehl).
            if self._job_offen:
                self.doc.commitTransaction()
                self._job_offen = False
                self._job_fest = True
            if not self._anlegen():
                self.doc.openTransaction(tr("ba.titel"))  # für weitere Eingaben
                self._job_offen = True
                return False
        self._vor_dem_schliessen()
        self._fraeser_merken()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    def reject(self):
        self._vor_dem_schliessen()
        if self._job_offen:
            self._sichtbarkeit_zurueck()
            self.doc.abortTransaction()
            self._job_offen = False
        if self._job_fest:  # „Anlegen“ ging nicht, der Job liegt schon als Schritt ab
            self._sichtbarkeit_zurueck()
            while len(self.doc.UndoNames) > self._undo_vorher:
                self.doc.undo()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    def _vor_dem_schliessen(self):
        BearbeitungPanel.offen = None
        self.geschlossen = True
        self._vorschau_uhr.stop()
        self._rohteil_uhr.stop()
        self._farben_zurueck()
        if self._beobachter is not None:
            FreeCADGui.Selection.removeObserver(self._beobachter)
            FreeCADGui.Selection.removeSelectionGate()
            self._beobachter = None
        FreeCADGui.Selection.clearSelection()

    # --- Teil, Job, Rohteil ---------------------------------------------------------------

    def angeklickt(self, objekt, unterelement):
        """Eine angeklickte Fläche: ohne Job macht sie ihr Teil zum Teil des Jobs; mit Job nimmt
        sie die Fläche dazu oder heraus."""
        if self.geschlossen:
            return
        if self.job is None:
            wahl = gewaehlte_flaeche(self.doc)
            if wahl is not None:
                self.teil_waehlen(*wahl)
            return
        teil, flaeche = _entlang(self.doc, self.doc.getObject(objekt), unterelement)
        klon = vr.modell(self.job)
        if teil is None or flaeche is None or vr.original(teil) is not vr.original(klon):
            return
        FreeCADGui.Selection.clearSelection()
        self.flaeche_umschalten(flaeche)

    def teil_waehlen(self, teil, flaeche=None):
        """Das Teil für den Job – der Job mit dem Rohteil entsteht sofort (eine Transaktion,
        bis „Anlegen“ oder „Abbrechen“). `flaeche`: die angeklickte Fläche („Face6“) – ist sie
        eben nach oben, ist sie gewählt, sonst die Oberseite."""
        if self.job is not None or teil is None or self.geschlossen:
            return
        self.teil = teil
        self.teil_text.setText(teil.Label)
        try:
            self.job = _im_befehl(self._neuer_job)
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"Bearbeitung: {fehler}\n")
            self.hinweis.setText(tr("ba.fehler.anlegen", fehler=str(fehler)))
            self.teil = None
            return
        self._job_offen = True
        self._job_zeigen()
        form = vr.modell(self.job).Shape
        if flaeche and hf.ebenen_oben(form, [flaeche]):
            self.gewaehlte = [flaeche]
        else:
            self.gewaehlte = []
        FreeCADGui.Selection.clearSelection()
        self._bearbeitung_fuellen()
        self._flaechen_zeigen()
        self._auffrischen()
        self._vorschau_starten()

    def _neuer_job(self):
        """Legt den Job an und öffnet dafür die Transaktion des Assistenten – nur in
        _im_befehl (wie gui_vierachs._neuer_job)."""
        import Path.Main.Job as PathJob

        self.doc.openTransaction(tr("ba.titel"))
        FreeCAD.setActiveDocument(self.doc.Name)
        job = PathJob.Create("Job", [self.teil])
        job.Label = tr("ba.job", teil=self.teil.Label)
        self._rohteil_setzen(job)
        self.doc.recompute()
        if _globale_transaktionen():
            FreeCAD.setActiveTransaction(tr("ba.titel"), True)
        return job

    def _rohteil_setzen(self, job):
        """Das Rohteil des Jobs mit dem Aufmaß aus den Feldern – ein Quader um das Teil."""
        rohteil = getattr(job, "Stock", None)
        if rohteil is None or not hasattr(rohteil, "ExtZpos"):
            return
        werte = {feld: self._wert(feld) for feld in ROHTEIL_FELDER}
        for name, wert in (
            ("ExtZpos", werte["oben"]),
            ("ExtZneg", werte["unten"]),
            ("ExtXneg", werte["seite"]),
            ("ExtXpos", werte["seite"]),
            ("ExtYneg", werte["seite"]),
            ("ExtYpos", werte["seite"]),
        ):
            if abs(_mm(getattr(rohteil, name)) - wert) > 1e-9:
                setattr(rohteil, name, wert)

    def _rohteil_geaendert(self):
        if not self._fuellt and self.job is not None and self.zu_aendern is None:
            self._rohteil_uhr.start()

    def _rohteil_anwenden(self):
        if self.job is None or self.zu_aendern is not None or self.geschlossen:
            return
        self._rohteil_setzen(self.job)
        self.doc.recompute()
        self._vorschau_starten()

    def _job_zeigen(self):
        """Anzeige des neuen Jobs wie bei FreeCADs Befehl „Job“ – aber in unserer Transaktion.
        Der Klon ist das Teil im Job, das Original verschwindet solange."""
        import Path.Main.Gui.Job as PathJobGui

        ansicht = self.job.ViewObject
        if ansicht is not None and getattr(ansicht, "Proxy", None) is None:
            ansicht.Proxy = PathJobGui.ViewProvider(ansicht)
            ansicht.addExtension("Gui::ViewProviderGroupExtensionPython")
        klon = vr.modell(self.job)
        if klon.ViewObject is not None:
            klon.ViewObject.Visibility = True
            klon.ViewObject.Transparency = 0
        if self.teil.ViewObject is not None:
            self._sichtbar_vorher = (self.teil, self.teil.ViewObject.Visibility)
            self.teil.ViewObject.Visibility = False

    def _sichtbarkeit_zurueck(self):
        if self._sichtbar_vorher is None:
            return
        teil, sichtbar = self._sichtbar_vorher
        self._sichtbar_vorher = None
        try:
            if teil.ViewObject is not None:
                teil.ViewObject.Visibility = sichtbar
        except (ReferenceError, RuntimeError):
            pass

    def _zum_aendern(self):
        """Mit den Werten der Operation: Teil und Rohteil wie im Job (nicht änderbar), Flächen,
        Fräser, Einsatz, Werte; „Übernehmen“ statt „Anlegen“."""
        op = self.zu_aendern
        self.job = job_von(op)
        if self.job is None:
            return
        self.teil = vr.original(vr.modell(self.job))
        self.teil_text.setText(self.teil.Label)
        self.anleitung.setText(tr("ba.aendern.text", name=op.Label))
        rohteil = getattr(self.job, "Stock", None)
        self._fuellt = True
        try:
            if rohteil is not None and hasattr(rohteil, "ExtZpos"):
                for feld, name in (("oben", "ExtZpos"), ("seite", "ExtXpos"), ("unten", "ExtZneg")):
                    wert = _mm(getattr(rohteil, name))
                    self.felder_rohteil[feld].setText(groesse_zeigen(wert, einheiten.LAENGE) or "0")
        finally:
            self._fuellt = False
        self.rohteilfelder.setEnabled(False)
        self.gewaehlte = list(getattr(op, "Flaechen", ()) or ())
        self._bearbeitung_fuellen()
        for feld, wert in (
            ("zustellung", op.Zustellung),
            ("zeilenabstand", op.Zeilenabstand),
            ("aufmass", op.Aufmass),
        ):
            wert = float(wert)
            if abs(wert - self._vorschlag(feld)) > 1e-6:
                self.felder[feld].setText(groesse_zeigen(wert, einheiten.LAENGE) or "0")
        self._flaechen_zeigen()
        self._auffrischen()
        self._vorschau_starten()

    # --- Flächen --------------------------------------------------------------------------

    def flaeche_umschalten(self, name):
        """Nimmt die Fläche `name` („Face6“) dazu – oder heraus, wenn sie schon gewählt ist."""
        if not name or self.job is None:
            return
        if name in self.gewaehlte:
            self.gewaehlte.remove(name)
        else:
            self.gewaehlte.append(name)
        self._flaechen_zeigen()
        self._vorschau_starten()

    def oberseite_waehlen(self):
        if self.job is None:
            return
        self.gewaehlte = hf.oberseite(vr.modell(self.job).Shape)
        self._flaechen_zeigen()
        self._vorschau_starten()

    def flaechen_leeren(self):
        self.gewaehlte = []
        self._flaechen_zeigen()
        self._vorschau_starten()

    def flaechen(self):
        """Die gewählten Flächen („Face6“ …) – leer: die Oberseite."""
        return list(self.gewaehlte)

    def _flaechen_zeigen(self):
        """Die Liste der gewählten Flächen, der Satz darunter und die Farben am Teil."""
        self.flaechen_liste.clear()
        self.flaechen_liste.setVisible(bool(self.gewaehlte))
        if self.job is None:
            self.flaechen_text.setText("")
            return
        form = vr.modell(self.job).Shape
        if not self.gewaehlte:
            namen = ", ".join(hf.oberseite(form)) or "–"
            self.flaechen_text.setText(tr("ba.flaechen.oberseite", namen=namen))
            self._farben_zeigen({})
            return
        farben = {}
        for name in self.gewaehlte:
            ebenen = hf.ebenen_oben(form, [name])
            nummer = int(name[4:]) - 1 if name.startswith("Face") and name[4:].isdigit() else -1
            if nummer < 0 or nummer >= len(form.Faces):
                text, farbe = tr("ba.flaeche.fehlt", name=name), ROT
            elif ebenen:
                z = groesse_zeigen(ebenen[0].z, einheiten.LAENGE) or "0"
                text, farbe = tr("ba.flaeche.eben", name=name, z=z), GRUEN
            else:
                text, farbe = tr("ba.flaeche.nicht_eben", name=name), ROT
            eintrag = QtGui.QListWidgetItem(dezimal(text))
            eintrag.setData(QtCore.Qt.UserRole, name)
            eintrag.setForeground(QtGui.QColor(farbe))
            self.flaechen_liste.addItem(eintrag)
            if nummer >= 0:
                farben[nummer] = farbe
        self.flaechen_text.setText(tr("ba.flaechen.nur"))
        self._farben_zeigen(farben)

    def _farben_zeigen(self, farben):
        """Färbt die Flächen des Teils im Job (wie gui_vierachs._farben_zeigen) – nur die
        Anzeige; _farben_zurueck() stellt sie wieder her."""
        if not farben or self.job is None:
            self._farben_zurueck()
            return
        klon = vr.modell(self.job)
        ansicht = klon.ViewObject
        if ansicht is None or not hasattr(ansicht, "DiffuseColor"):
            return
        if self._farben_vorher is None:
            aussehen = getattr(ansicht, "ShapeAppearance", None)
            self._farben_vorher = (
                klon,
                list(ansicht.DiffuseColor),
                list(aussehen) if aussehen is not None else None,
            )
        grund = self._farben_vorher[1]
        anzahl = len(klon.Shape.Faces)
        if len(grund) != anzahl:
            grund = [tuple(grund[0]) if grund else tuple(ansicht.ShapeColor)] * anzahl
        alpha = grund[0][3] if grund and len(grund[0]) > 3 else 0.0
        neu = list(grund)
        for nummer, farbe in farben.items():
            if nummer < anzahl:
                neu[nummer] = (*(int(farbe[i : i + 2], 16) / 255 for i in (1, 3, 5)), alpha)
        ansicht.DiffuseColor = neu

    def _farben_zurueck(self):
        if self._farben_vorher is None:
            return
        klon, farben, aussehen = self._farben_vorher
        self._farben_vorher = None
        try:
            ansicht = klon.ViewObject
            if ansicht is None:
                return
            if aussehen is not None:
                ansicht.ShapeAppearance = aussehen
            else:
                ansicht.DiffuseColor = farben
        except (ReferenceError, RuntimeError):  # das Teil ist schon weg (Abbrechen)
            pass

    # --- Werkstoff, Fräser, Einsatz -------------------------------------------------------

    def _bearbeitung_fuellen(self):
        """Werkstoff und Fräser anbieten – die Werkzeugverwaltung frisch gelesen."""
        from .gui_werkzeuge import werkstoffe_anbieten

        vorher = self.werkstoff() if self.bibliothek is not None else None
        self.hinweis.setText("")
        try:
            self.bibliothek = wz.Bibliothek.laden()
        except wz.BeschaedigteDatei as fehler:
            self.bibliothek = wz.Bibliothek()
            self.hinweis.setText(tr("wv.fehler.laden", fehler=fehler, datei=fehler.beiseite))
        self._fuellt = True
        try:
            werkstoffe_anbieten(self.wahl_werkstoff, self.bibliothek)
            if vorher is None:
                alle = self.bibliothek.alle_werkstoffe()
                werkstoff, _gemerkt = js.werkstoff_fuer(self.job, alle, self._tc_vorher)
                vorher = werkstoff.kennung if werkstoff is not None else wz.ALLE
            self.wahl_werkstoff.setCurrentIndex(max(0, self.wahl_werkstoff.findData(vorher)))
        finally:
            self._fuellt = False
        if self._tc_vorher is not None and self._vorwahl is None:
            werkzeug = js.werkzeug_von(self._tc_vorher, self.bibliothek)
            self._vorwahl = werkzeug.kennung if werkzeug is not None else ""
        self._fraeser_fuellen()

    def werkstoff(self):
        return self.wahl_werkstoff.currentData() or wz.ALLE

    def _werkstoff_gewaehlt(self):
        if not self._fuellt:
            self._fraeser_fuellen()

    @staticmethod
    def _passende_einsaetze(werkzeug, werkstoff):
        """Die Einsätze mit Drehzahl und Vorschub – nur mit ihnen gibt es einen Controller."""
        return [e for e in werkzeug.einsaetze(werkstoff) if js.werte(werkzeug, e)[1] > 0]

    @staticmethod
    def _ebene_stirn(werkzeug):
        form = ff.von_werkzeug(werkzeug)
        return form is not None and vp.ebener_radius(form) > 0

    def _fraeser_fuellen(self):
        """Die Fräser mit ebener Stirn und Schnittwerten für den Werkstoff; vorgewählt der
        bisher gewählte, beim Ändern der der Operation, sonst der zuletzt benutzte, sonst
        einer mit Einsatz „Planen“, sonst ein Schaftfräser."""
        werkstoff = self.werkstoff()
        vorher = self.fraeser()
        self._fraeser = [
            w
            for w in sorted(self.bibliothek.werkzeuge, key=lambda w: w.nummer)
            if w.durchmesser > 0 and self._ebene_stirn(w) and self._passende_einsaetze(w, werkstoff)
        ]
        kennungen = [w.kennung for w in self._fraeser]
        gemerkt = _parameter().GetString(GEMERKT_FRAESER, "")
        if vorher is not None and vorher.kennung in kennungen:
            wahl = kennungen.index(vorher.kennung)
        elif self._vorwahl in kennungen:
            wahl = kennungen.index(self._vorwahl)
        elif gemerkt in kennungen:
            wahl = kennungen.index(gemerkt)
        else:
            wahl = min(
                range(len(self._fraeser)),
                key=lambda i: (
                    not any(
                        e.art == wz.PLANEN
                        for e in self._passende_einsaetze(self._fraeser[i], werkstoff)
                    ),
                    self._fraeser[i].art != wz.SCHAFTFRAESER,
                    i,
                ),
                default=0,
            )
        self._fuellt = True
        try:
            self.wahl_fraeser.clear()
            for werkzeug in self._fraeser:
                self.wahl_fraeser.addItem(dezimal(wz.zeile(werkzeug)))
            if self._fraeser:
                self.wahl_fraeser.setCurrentIndex(wahl)
        finally:
            self._fuellt = False
        self._einsatz_fuellen()

    def fraeser(self):
        i = self.wahl_fraeser.currentIndex()
        return self._fraeser[i] if 0 <= i < len(self._fraeser) else None

    def _fraeser_gewaehlt(self):
        if not self._fuellt:
            self._einsatz_fuellen()

    def _einsatz_fuellen(self):
        """Die Einsätze des Fräsers; vorgewählt „Planen“, sonst „Schruppen“, sonst
        „Schlichten“; beim Ändern der, mit dem der Controller gesetzt ist."""
        werkzeug = self.fraeser()
        self._einsaetze = (
            self._passende_einsaetze(werkzeug, self.werkstoff()) if werkzeug is not None else []
        )
        arten = [e.art for e in self._einsaetze]
        wahl = next(
            (arten.index(a) for a in (wz.PLANEN, wz.SCHRUPPEN, wz.SCHLICHTEN) if a in arten), 0
        )
        if (
            self._tc_vorher is not None
            and werkzeug is not None
            and werkzeug.kennung == self._vorwahl
        ):
            gemerkt = js.vorgeschlagener_einsatz(self._tc_vorher, self._einsaetze, self.job)
            wahl = gemerkt if gemerkt >= 0 else wahl
        self._fuellt = True
        try:
            self.wahl_einsatz.clear()
            for einsatz in self._einsaetze:
                self.wahl_einsatz.addItem(wz.einsatz_name(einsatz))
            if self._einsaetze:
                self.wahl_einsatz.setCurrentIndex(wahl)
        finally:
            self._fuellt = False
        self._einsatz_gewaehlt()

    def einsatz(self):
        i = self.wahl_einsatz.currentIndex()
        return self._einsaetze[i] if 0 <= i < len(self._einsaetze) else None

    def _einsatz_gewaehlt(self):
        """Drehzahl und Vorschub, die Vorschläge in die Felder."""
        if self._fuellt:
            return
        werkzeug, einsatz = self.fraeser(), self.einsatz()
        if werkzeug is None or einsatz is None:
            self.schnittwerte.setText("")
        else:
            n, vf, _senkrecht = js.werte(werkzeug, einsatz)
            self.schnittwerte.setText(
                tr("va.schnittwerte", n=f"{n:.0f}", vf=groesse_fest(vf, einheiten.VORSCHUB, 0))
            )
        for feld, eingabe in self.felder.items():
            eingabe.setPlaceholderText(
                groesse_zeigen(self._vorschlag(feld), einheiten.LAENGE) or "0"
            )
        self._vorschau_starten()

    def werkzeugverwaltung(self, nummer=None):
        """Öffnet die Werkzeugverwaltung; speichert man dort, liest der Assistent sie neu."""
        from . import gui_werkzeuge

        dialog = gui_werkzeuge.oeffne(nummer)
        if getattr(self, "_werkzeugdialog", None) is not dialog:
            self._werkzeugdialog = dialog
            dialog.gespeichert.connect(self._werkzeuge_gespeichert)

    def _werkzeuge_gespeichert(self):
        if BearbeitungPanel.offen is self and self.job is not None:
            self._bearbeitung_fuellen()

    def _fraeser_merken(self):
        if self.fraeser() is not None:
            _parameter().SetString(GEMERKT_FRAESER, self.fraeser().kennung)

    # --- Werte und Vorschau -----------------------------------------------------------------

    def _vorschlag(self, feld):
        """Der Wert eines leeren Felds (mm)."""
        if feld in ROHTEIL_FELDER:
            return AUFMASS_ROHTEIL
        einsatz = self.einsatz()
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else pf.ZUSTELLUNG
        if feld == "zeilenabstand":
            werkzeug = self.fraeser()
            if werkzeug is None:
                return 0.0
            return vplan.zeilenabstand_vorschlag(werkzeug, einsatz, ff.von_werkzeug(werkzeug))
        return pf.AUFMASS

    def _wert(self, feld):
        """Wert eines Felds (mm); leer oder ungültig gilt der Vorschlag."""
        eingabe = self.felder_rohteil.get(feld) or self.felder[feld]
        text = eingabe.text()
        try:
            return groesse_lesen(text, einheiten.LAENGE) if text.strip() else self._vorschlag(feld)
        except ValueError:
            return self._vorschlag(feld)

    def _vorschau_starten(self):
        if self._fuellt or self.geschlossen:
            return
        self.vorschau = None
        self._vorschau_uhr.start()
        self._knoepfe_beschriften()

    def _vorschau_rechnen(self):
        """Die grobe Bahn (planfraesen.vorschau) für Lagen, Zeilen und Zeit – und damit
        „Anlegen“ weiß, ob es geht."""
        self._vorschau_uhr.stop()
        if self.geschlossen or self.job is None:
            return
        self.vorschau = None
        self.ergebnis.setText("")
        self.hinweis.setText("")
        werkzeug, einsatz = self.fraeser(), self.einsatz()
        if werkzeug is None or einsatz is None:
            self.hinweis.setText(tr("va.planfraeser.keiner"))
            self._knoepfe_beschriften()
            return
        try:
            self.vorschau = pf.vorschau(
                self.job,
                self.job.Model.Group,
                ff.von_werkzeug(werkzeug),
                self._wert("zustellung"),
                self._wert("zeilenabstand"),
                self._wert("aufmass"),
                self.flaechen(),
            )
        except (ValueError, RuntimeError) as fehler:  # RuntimeError: OCC am Netz
            self.hinweis.setText(str(fehler))
        else:
            self.ergebnis.setText(self._ergebnis_text(self.vorschau))
        self._knoepfe_beschriften()

    def _ergebnis_text(self, bahn):
        """„→ 3 Lagen, 30 Zeilen, etwa 2 min“ – bei mehreren Flächen mit ihrer Zahl."""
        _n, vorschub, senkrecht = js.werte(self.fraeser(), self.einsatz())
        zeit = _zeit_text(bn.dauer(bahn.punkte, vorschub, senkrecht)) if vorschub > 0 else "?"
        if bahn.flaechen > 1:
            return tr(
                "ba.ergebnis_flaechen",
                flaechen=bahn.flaechen,
                lagen=bahn.lagen,
                zeilen=bahn.zeilen,
                zeit=zeit,
            )
        return tr("ba.ergebnis", lagen=bahn.lagen, zeilen=bahn.zeilen, zeit=zeit)

    def _auffrischen(self):
        self._knoepfe_beschriften()

    # --- Anlegen und Ändern -----------------------------------------------------------------

    def _anlegen(self):
        """Werkzeug-Controller und „Planfräsen“ in den Job – ein eigener Schritt Rückgängig, in
        einem Befehl (_im_befehl). Geht es nicht, steht der Grund rot im Fenster: False."""
        werte = (self._wert("zustellung"), self._wert("zeilenabstand"), self._wert("aufmass"))
        flaechen = self.flaechen()

        def anlegen():
            self.doc.openTransaction(tr("ba.transaktion.anlegen"))
            try:
                ue.uebergeben(self.bibliothek)
                fremde = js.unbenutzte_fremde_controller(self.job, self.bibliothek)
                js.controller_weg(self.doc, fremde)
                tc = js.controller_ohne_transaktion(
                    self.doc, self.job, self.fraeser(), self.einsatz(), self.werkstoff()
                )
                op = pf.lege_an(self.job, tc, *werte, flaechen=flaechen)
                self.doc.recompute()
            except Exception:
                self.doc.abortTransaction()
                raise
            self.doc.commitTransaction()
            return op

        try:
            self.operation = _im_befehl(anlegen)
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"Bearbeitung: {fehler}\n")
            self.operation = None
            self.hinweis.setText(tr("ba.fehler.anlegen", fehler=str(fehler)))
            self._knoepfe_beschriften()
            return False
        return True

    def _aendern(self):
        """Die Operation bekommt Fräser, Einsatz, Werte und Flächen aus dem Fenster – ein
        eigener Schritt Rückgängig; den alten Controller nimmt es heraus, wenn ihn keine
        Operation mehr benutzt. Geht es nicht, steht der Grund rot im Fenster: False."""
        op = self.zu_aendern
        werte = (self._wert("zustellung"), self._wert("zeilenabstand"), self._wert("aufmass"))
        flaechen = self.flaechen()

        def aendern():
            self.doc.openTransaction(tr("ba.transaktion.aendern"))
            try:
                ue.uebergeben(self.bibliothek)
                bisher = op.ToolController
                tc = js.controller_fuer(
                    self.doc, self.job, self.fraeser(), self.einsatz(), self.werkstoff(), op
                )
                pf.aendere(op, tc, *werte, flaechen=flaechen)
                frei = bisher is not None and not js.operationen_mit(bisher, self.job)
                if frei and bisher is not tc:
                    js.controller_weg(self.doc, [bisher])
                self.doc.recompute()
            except Exception:
                self.doc.abortTransaction()
                raise
            self.doc.commitTransaction()

        try:
            _im_befehl(aendern)
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"Bearbeitung: {fehler}\n")
            self.hinweis.setText(tr("ba.fehler.aendern", fehler=str(fehler)))
            self._knoepfe_beschriften()
            return False
        return True
