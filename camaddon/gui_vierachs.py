# SPDX-License-Identifier: LGPL-2.1-or-later
"""Assistent „4-Achs-Bearbeitung“ (Spezifikation W-003) in zwei Schritten.

Schritt 1, Rohteil (Stufe V1): Man klickt die ebene Stirnfläche eines Teils
an, und das Teil sitzt vorne mittig in einer runden Stange: ein neuer
CAM-Job, das Teil in seinem Modell-Klon, das Rohteil ein Zylinder. Gerechnet
wird in vierachs_rohteil.py. Jede Eingabe geht sofort ins Dokument – wie in
„Maschine bearbeiten“ –, damit die 3D-Ansicht stimmt.

Schritt 2, „Was willst du machen?“ (Stufe V3d, Manuels Wunsch): „Rundum
schruppen“ mit einem Fräser aus der Werkzeugverwaltung – Werkstoff, Einsatz,
Zustellung, Vorschub je Umdrehung und Aufmaß, dazu die Vorschau „→ 5 Lagen“.
„Anlegen“ legt Job, Stange, Werkzeug-Controller und die Operation
(vierachs_operation) als einen Schritt Rückgängig an; „Abbrechen“ verwirft
alles.

Leere Felder gelten mit ihrem grauen Vorschlag (Manuel: „alles einstellbar,
aber mit Vorschlägen als Standard“). Was man einträgt, ist beim nächsten Mal
der Vorschlag – außer dem Stangen-Ø, der hängt am Teil.
"""

import math

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, einheiten, symbol
from . import job_schnittwerte as js
from . import uebergabe_werkzeuge as ue
from . import vierachs_achsen as va
from . import vierachs_operation as vo
from . import vierachs_rohteil as vr
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_maschine import _EnterBleibtImDialog
from .gui_teile import ROT, knopf, mit_einheit, ruhiges_mausrad
from .gui_zahlen import (
    Zahlenpruefer,
    dezimal,
    groesse_fest,
    groesse_lesen,
    groesse_zeigen,
    zahl_lesen,
    zahl_zeigen,
)
from .sprache import tr

GRUEN = "#4e9a06"  # „passt“ – das Grün der Tango-Farben, wie in den Symbolen
GRAU_TEXT = "#6d6d6d"  # gerechnete Werte

# Nach der letzten Eingabe so lange warten, bevor Job und Stange nachziehen –
# sonst rechnet jede Ziffer von „80“ einzeln.
NACHZIEHEN_MS = 250
# Die Animation: das Teil fährt in die Stange, dann dreht es sich einmal.
TAKT_MS = 20
SCHRITTE_FAHREN = 30
SCHRITTE_DREHEN = 40

# Wie die Stange während des Assistenten aussieht (danach wie in CAM üblich).
STANGE_ANZEIGE = ("Flat Lines", 80)
STANGE_CAM = ("Wireframe", 90)  # so legt CAM sie an (Path.Main.Stock.SetupStockObject)

# Vorschläge, die sich das Addon merkt: Feld → (Schlüssel, Vorschlag ab Werk).
GEMERKT = {
    "planaufmass": ("VaPlanaufmass", vr.PLANAUFMASS),
    "abstechbreite": ("VaAbstechbreite", vr.ABSTECHBREITE),
    "spannlaenge": ("VaSpannlaenge", vr.SPANNLAENGE),
}
GEMERKT_RUNDACHSE = "VaRundachse"
GEMERKT_FRAESER = "VaFraeser"  # Kennung des zuletzt gewählten Fräsers

# Welche Werkzeuge „Rundum schruppen“ anbietet: Die Hüllfläche rechnet mit der
# Stirn als Scheibe – für jedes dieser Werkzeuge sicher (vierachs_huelle).
FRAESER_ARTEN = (
    wz.SCHAFTFRAESER,
    wz.TORUSFRAESER,
    wz.KUGELFRAESER,
    wz.NUTENFRAESER,
    wz.PLANFRAESER,
)
VORSCHAU_MS = 400  # nach der letzten Eingabe so lange warten, dann die Lagen rechnen


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def _achstexte():
    """Die Einträge der Liste „Rundachse“ ohne Maschine: Buchstabe → ein Satz, wie die
    Stange liegt."""
    return {"A": tr("va.achse.a"), "B": tr("va.achse.b"), "C": tr("va.achse.c")}


def achstext(achse):
    """Der Eintrag der Liste „Rundachse“ für eine Stangenachse (vierachs_achsen)."""
    if not achse.maschine:
        return _achstexte()[achse.buchstabe]
    richtung = va.achsbuchstabe(achse.laengs)
    if not richtung:
        return tr("va.achse.maschine_schraeg", maschine=achse.maschine, buchstabe=achse.buchstabe)
    return tr(
        "va.achse.maschine", maschine=achse.maschine, buchstabe=achse.buchstabe, richtung=richtung
    )


def gewaehlte_flaeche(dokument):
    """(Teil, „FaceN“) aus der Auswahl in `dokument`; (Teil, None), wenn nur ein Teil
    gewählt ist; None ohne Auswahl.

    Gelesen wird der Weg vom obersten Objekt bis zur Fläche. Teil ist das
    erste Objekt auf diesem Weg mit einer Form – ein Körper, nicht der Block
    darin; so bekommt der Job das Teil, das man in der Liste sieht. Ein
    Modell-Klon eines Jobs zählt als sein Original.
    """
    for auswahl in FreeCADGui.Selection.getSelectionEx(dokument.Name, 0):
        for unterelement in auswahl.SubElementNames or [""]:
            teil, flaeche = _entlang(dokument, auswahl.Object, unterelement)
            if teil is not None:
                return vr.original(teil), flaeche
    return None


def _entlang(dokument, objekt, unterelement):
    """Folgt dem Weg „Körper.Block.Face3“ bis zum ersten Objekt mit einer Form."""
    teile = unterelement.split(".") if unterelement else []
    flaeche = teile.pop() if teile and teile[-1].startswith("Face") else None
    while objekt is not None and not _hat_form(objekt):
        objekt = dokument.getObject(teile.pop(0)) if teile else None
    return objekt, flaeche


def _hat_form(objekt):
    form = getattr(objekt, "Shape", None)
    return form is not None and not form.isNull() and bool(form.Faces)


class BefehlVierachs:
    """Befehl in der Werkzeugleiste: öffnet den Assistenten für die gewählte Fläche."""

    def GetResources(self):
        return {
            "Pixmap": symbol("vierachs.svg"),
            "MenuText": tr("befehl.vierachs.titel"),
            "ToolTip": tr("befehl.vierachs.tooltip"),
        }

    def IsActive(self):
        # Wie „Maschine bearbeiten“: bedienbar, solange kein anderes
        # Aufgabenfenster offen ist – was fehlt, sagt der Assistent selbst.
        return not FreeCADGui.Control.activeDialog()

    def Activated(self):
        dokument = FreeCAD.ActiveDocument
        if dokument is None:
            QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(), tr("va.titel"), tr("va.kein_dokument")
            )
            return
        wahl = gewaehlte_flaeche(dokument)
        # Die Transaktion öffnet der Assistent, wenn er den Job anlegt (_neuer_job).
        FreeCADGui.Control.showDialog(VierachsPanel(dokument, wahl))


class _Intern:
    """Ein FreeCAD-Befehl ohne Knopf: führt eine Aufgabe aus (_im_befehl)."""

    NAME = "CamAddon_VierachsIntern"
    aufgabe = None

    def GetResources(self):
        return {"MenuText": tr("va.titel")}

    def IsActive(self):
        return True

    def Activated(self):
        aufgabe, _Intern.aufgabe = _Intern.aufgabe, None
        if aufgabe is not None:
            aufgabe()


def _globale_transaktionen():
    """Hat FreeCAD noch die Transaktionen für alle Dokumente zugleich (bis 1.1)? Der
    Wochen-Build führt sie je Dokument."""
    try:
        return int(FreeCAD.Version()[0]) <= 1
    except (ValueError, IndexError):
        return False


def _im_befehl(aufgabe):
    """Führt `aufgabe()` als FreeCAD-Befehl aus und gibt ihr Ergebnis zurück; eine Ausnahme
    kommt danach durch.

    Warum (bis FreeCAD 1.1): Legt CAM ein Werkzeug an (ToolBit – auch den Controller,
    den jeder neue Job bekommt), öffnet und schließt es dafür ein verstecktes Dokument,
    und dabei schließt FreeCAD außerhalb eines Befehls die offene Transaktion – was
    danach kommt, ließe sich nicht mehr rückgängig machen (ausprobiert in 1.1.3,
    P-2026-09-27-49). In einem Befehl schützt FreeCAD die Transaktion, die darin geöffnet
    wird; vorher darf keine offen sein. Der Wochen-Build führt Transaktionen je Dokument
    – dort läuft `aufgabe` einfach so.
    """
    if not _globale_transaktionen():
        return aufgabe()
    if _Intern.NAME not in FreeCADGui.listCommands():
        FreeCADGui.addCommand(_Intern.NAME, _Intern())
    ergebnis = {}

    def ausfuehren():
        try:
            ergebnis["wert"] = aufgabe()
        except Exception as fehler:  # nach dem Befehl weiterreichen
            ergebnis["fehler"] = fehler

    _Intern.aufgabe = ausfuehren
    FreeCADGui.runCommand(_Intern.NAME)
    if "fehler" in ergebnis:
        raise ergebnis["fehler"]
    return ergebnis.get("wert")


class _Beobachter:
    """Meldet dem Assistenten jede neu angeklickte Fläche."""

    def __init__(self, panel):
        self.panel = panel

    def addSelection(self, _dokument, _objekt, unterelement, _punkt):
        if unterelement:
            # Erst wenn FreeCAD mit der Auswahl fertig ist – der Assistent ändert
            # dabei das Dokument.
            QtCore.QTimer.singleShot(0, self.panel.auswahl_lesen)


class _NurFlaechen:
    """Anklicken lassen sich nur Flächen – nicht die Stange, durch die man hindurchklickt."""

    def __init__(self, panel):
        self.panel = panel

    def allow(self, _dokument, objekt, unterelement):
        weg = unterelement.split(".") if unterelement else []
        if not weg or not weg[-1].startswith("Face"):
            return False
        rohteil = self.panel.job.Stock if self.panel.job is not None else None
        name = getattr(objekt, "Name", "")
        return rohteil is None or (name != rohteil.Name and rohteil.Name not in weg)


class _Einfahren:
    """Zeigt ohne Worte, was passiert: Das Teil fährt von seiner alten Lage in die
    Stange und dreht sich einmal um die Stangenachse. Am Ende steht es exakt am Ziel."""

    def __init__(self, objekt, von, nach, achse):
        self.objekt, self.von, self.nach, self.achse = objekt, von, nach, achse
        self.schritt = 0
        self.uhr = QtCore.QTimer()
        self.uhr.setInterval(TAKT_MS)
        self.uhr.timeout.connect(self._weiter)

    def start(self):
        self.uhr.start()

    def laeuft(self):
        return self.uhr.isActive()

    def stopp(self):
        """Anhalten – das Teil steht dann am Ziel, auch mitten in der Bewegung."""
        self.uhr.stop()
        if self.objekt.Placement != self.nach:
            self.objekt.Placement = self.nach

    def _weiter(self):
        self.schritt += 1
        if self.schritt < SCHRITTE_FAHREN:
            anteil = self.schritt / SCHRITTE_FAHREN
            # Langsam an, langsam aus.
            self.objekt.Placement = self.von.sclerp(self.nach, 0.5 - 0.5 * _cos_pi(anteil))
        elif self.schritt < SCHRITTE_FAHREN + SCHRITTE_DREHEN:
            anteil = (self.schritt - SCHRITTE_FAHREN) / SCHRITTE_DREHEN
            drehung = FreeCAD.Rotation(self.achse, 360.0 * (0.5 - 0.5 * _cos_pi(anteil)))
            self.objekt.Placement = FreeCAD.Placement(FreeCAD.Vector(), drehung).multiply(self.nach)
        else:
            self.stopp()


def _cos_pi(anteil):
    return math.cos(math.pi * anteil)


class VierachsPanel:
    """Das Aufgabenfenster. FreeCAD ruft `getStandardButtons`, `modifyStandardButtons`,
    `accept` und `reject` auf."""

    offen = None  # das gerade offene Fenster – für die Oberflächen-Szenarien

    def __init__(self, dokument, wahl=None):
        VierachsPanel.offen = self
        self.doc = dokument
        self.teil = None  # das Original, das in die Stange soll
        self.flaeche = None  # „FaceN“ der Stirnfläche
        self.vermessung = None
        self.lage = None
        self.job = None
        self.mitte = vr.MITTE_AUTO  # bis man selbst eine Mitte wählt
        self.einfahren = None
        self.geschlossen = False
        self._knoepfe = None  # FreeCADs Knopfleiste (modifyStandardButtons)
        self._sichtbar_vorher = None  # (Original, Sichtbarkeit) – für Abbrechen
        self._fuellt = False  # während Felder von hier aus gesetzt werden
        self._uhr = QtCore.QTimer()
        self._uhr.setSingleShot(True)
        self._uhr.setInterval(NACHZIEHEN_MS)
        self._uhr.timeout.connect(self._anwenden)
        self.seite = 1  # 1: Rohteil, 2: Was willst du machen?
        self.bibliothek = None  # die Werkzeugverwaltung – geladen, wenn Schritt 2 kommt
        self._fraeser = []  # die Werkzeuge in der Auswahl „Fräser“
        self._einsaetze = []  # die Einsätze in der Auswahl „Einsatz“
        self.vorschau = None  # die Bahn der Vorschau (vierachs_bahn.Bahn) oder None
        self.operation = None  # die angelegte Operation
        # Rückgängig-Schritte vor dem Assistenten; Job und Stange liegen nach „Anlegen“ als
        # eigener Schritt ab, auch wenn das Schruppen danach nicht geht (Abbrechen: zurück).
        self._undo_vorher = len(dokument.UndoNames)
        self._rohteil_fest = False
        self._vorschau_uhr = QtCore.QTimer()
        self._vorschau_uhr.setSingleShot(True)
        self._vorschau_uhr.setInterval(VORSCHAU_MS)
        self._vorschau_uhr.timeout.connect(self._vorschau_rechnen)
        self.form = self._baue()
        self._beobachter = _Beobachter(self)
        FreeCADGui.Selection.addObserver(self._beobachter)
        FreeCADGui.Selection.addSelectionGate(_NurFlaechen(self))
        if wahl is not None and wahl[1] is not None:
            self.waehle_flaeche(*wahl)
        self._auffrischen()

    # --- Schnittstelle zu FreeCAD ---------------------------------------------

    def getStandardButtons(self):
        return QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel

    def modifyStandardButtons(self, knoepfe):
        """OK heißt in Schritt 1 „Weiter“, in Schritt 2 „Anlegen“; es geht erst, wenn das
        Teil in der Stange liegt.

        Aufgehoben wird die Knopfleiste, nicht der Knopf: Mit der Python-Hülle
        der Leiste verfiele auch die des Knopfs (ausprobiert, P-2026-09-26-79) –
        CAM macht es ebenso (Path.Op.Gui.Base.TaskPanel).
        """
        self._knoepfe = knoepfe
        self._knoepfe_beschriften()

    def _knoepfe_beschriften(self):
        ok = self.knopf_anlegen()
        if ok is None:
            return
        if self.seite == 1:
            ok.setText(tr("va.weiter"))
            ok.setToolTip(tr("va.weiter.tooltip"))
            ok.setEnabled(self.job is not None)
        else:
            ok.setText(tr("va.anlegen"))
            ok.setToolTip(tr("va.anlegen.tooltip"))
            ok.setEnabled(self.job is not None and self._kann_anlegen())

    def knopf_anlegen(self):
        """Der Knopf „Anlegen“ (FreeCADs OK), oder None, solange das Fenster nicht steht."""
        if self._knoepfe is None:
            return None
        return self._knoepfe.button(QtGui.QDialogButtonBox.Ok)

    def accept(self):
        if self.job is None:
            return self.reject()
        if self._uhr.isActive():  # die letzte Eingabe noch übernehmen
            self._uhr.stop()
            self._anwenden()
        if self.seite == 1:
            self.zeige_seite(2)
            return False  # „Weiter“: das Fenster bleibt offen
        schruppen = self.mit_schruppen.isChecked()
        if schruppen and not self._schruppen_pruefen():
            return False  # der Grund steht rot im Fenster
        # Job und Stange: ein Schritt Rückgängig. Das Schruppen kommt in einem eigenen
        # (_schruppen_anlegen) – in einen gemeinsamen lässt FreeCAD es nicht (_im_befehl).
        self._anzeige_wie_in_cam()
        self.doc.commitTransaction()
        self._rohteil_fest = True
        if schruppen and not self._schruppen_anlegen():
            self._stange_anzeigen(*STANGE_ANZEIGE, waehlbar=False)
            self.doc.openTransaction(tr("va.titel"))  # für weitere Eingaben
            return False
        self._vor_dem_schliessen()
        self._vorschlaege_merken()
        self.doc.commitTransaction()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    def reject(self):
        self._vor_dem_schliessen()
        self._sichtbarkeit_zurueck()
        self.doc.abortTransaction()
        if self._rohteil_fest:  # Job und Stange liegen schon als Schritt ab
            while len(self.doc.UndoNames) > self._undo_vorher:
                self.doc.undo()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    def _vor_dem_schliessen(self):
        """Bewegung anhalten, Auswahl-Hilfen abmelden."""
        VierachsPanel.offen = None
        self.geschlossen = True
        self._uhr.stop()
        self._vorschau_uhr.stop()
        if self.einfahren:
            self.einfahren.stopp()
        FreeCADGui.Selection.removeObserver(self._beobachter)
        FreeCADGui.Selection.removeSelectionGate()
        FreeCADGui.Selection.clearSelection()

    # --- Aufbau ---------------------------------------------------------------

    def _baue(self):
        form = QtGui.QWidget()
        form.setWindowTitle(tr("va.titel"))
        form.setWindowIcon(QtGui.QIcon(symbol("vierachs.svg")))
        self._enter_filter = _EnterBleibtImDialog(form)  # Enter schließt den Dialog nicht
        form.installEventFilter(self._enter_filter)
        aussen = QtGui.QVBoxLayout(form)
        kopf = kopfzeile(tr("va.kopf"), "vierachs")
        self._kopf_text = kopf.findChild(QtGui.QLabel)
        aussen.addWidget(kopf)
        self.seiten = QtGui.QStackedWidget()
        aussen.addWidget(self.seiten)
        rohteil = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(rohteil)
        aufbau.setContentsMargins(0, 0, 0, 0)
        self.seiten.addWidget(rohteil)
        self.seiten.addWidget(self._baue_bearbeitung())
        self.anleitung = QtGui.QLabel(tr("va.anleitung"))
        self.anleitung.setWordWrap(True)
        aufbau.addWidget(self.anleitung)

        self.felder = QtGui.QWidget()
        raster = QtGui.QGridLayout(self.felder)
        raster.setContentsMargins(0, 0, 0, 0)
        zeile = 0

        def beschriftung(text, tooltip=""):
            etikett = QtGui.QLabel(text)
            etikett.setToolTip(tooltip)
            return etikett

        self.teil_text = QtGui.QLabel()
        self.teil_text.setWordWrap(True)
        raster.addWidget(beschriftung(tr("va.teil")), zeile, 0)
        raster.addWidget(self.teil_text, zeile, 1, 1, 2)
        zeile += 1

        self.feld_stange = self._zahlenfeld(tr("va.stange.tooltip"))
        raster.addWidget(beschriftung(tr("va.stange"), tr("va.stange.tooltip")), zeile, 0)
        raster.addWidget(
            mit_einheit(self.feld_stange, einheiten.einheit(einheiten.LAENGE)), zeile, 1, 1, 2
        )
        zeile += 1

        self.knopf_mitte_flaeche = QtGui.QRadioButton()
        self.knopf_mitte_teil = QtGui.QRadioButton(tr("va.mitte.teil"))
        for knopf_mitte, mitte in (
            (self.knopf_mitte_flaeche, vr.MITTE_FLAECHE),
            (self.knopf_mitte_teil, vr.MITTE_TEIL),
        ):
            knopf_mitte.setToolTip(tr("va.mitte.tooltip"))
            knopf_mitte.toggled.connect(
                lambda an, mitte=mitte: an and not self._fuellt and self.waehle_mitte(mitte)
            )
        self.braucht_flaeche = self._grau()
        self.braucht_teil = self._grau()
        raster.addWidget(beschriftung(tr("va.mitte"), tr("va.mitte.tooltip")), zeile, 0)
        raster.addWidget(self.knopf_mitte_flaeche, zeile, 1)
        raster.addWidget(self.braucht_flaeche, zeile, 2)
        zeile += 1
        raster.addWidget(self.knopf_mitte_teil, zeile, 1)
        raster.addWidget(self.braucht_teil, zeile, 2)
        zeile += 1

        self.feld_drehlage = QtGui.QLineEdit()
        self.feld_drehlage.setValidator(Zahlenpruefer(self.feld_drehlage, mit_minus=True))
        self.feld_drehlage.setPlaceholderText("0")
        self.feld_drehlage.setToolTip(tr("va.drehlage.tooltip"))
        self.feld_drehlage.textChanged.connect(self._eingabe)
        drehlage = mit_einheit(self.feld_drehlage, "°")
        drehlage.layout().addWidget(knopf(tr("va.plus90"), tr("va.plus90.tooltip"), self.plus90))
        raster.addWidget(beschriftung(tr("va.drehlage"), tr("va.drehlage.tooltip")), zeile, 0)
        raster.addWidget(drehlage, zeile, 1, 1, 2)
        zeile += 1

        self.felder_laenge = {}
        for feld, text, tooltip in (
            ("planaufmass", tr("va.planaufmass"), tr("va.planaufmass.tooltip")),
            ("abstechbreite", tr("va.abstechbreite"), tr("va.abstechbreite.tooltip")),
            ("spannlaenge", tr("va.spannlaenge"), tr("va.spannlaenge.tooltip")),
        ):
            eingabe = self._zahlenfeld(tooltip)
            eingabe.setPlaceholderText(groesse_zeigen(self._gemerkt(feld), einheiten.LAENGE))
            self.felder_laenge[feld] = eingabe
            raster.addWidget(beschriftung(text, tooltip), zeile, 0)
            raster.addWidget(mit_einheit(eingabe, einheiten.einheit(einheiten.LAENGE)), zeile, 1)
            zeile += 1
        self.laenge_text = self._grau()
        raster.addWidget(self.laenge_text, zeile - 1, 2)

        # Erst die Rundachsen der offenen Maschinen – die gibt die Maschine vor (V2a) –,
        # dann A, B, C ohne Maschine.
        self._achsen = va.offene(self.doc) + [va.zugewiesen(b) for b in _achstexte()]
        self.wahl_achse = QtGui.QComboBox()
        for achse in self._achsen:
            self.wahl_achse.addItem(achstext(achse))
        if self._achsen[0].maschine:
            self.wahl_achse.setCurrentIndex(0)
        else:
            gemerkt = _parameter().GetString(GEMERKT_RUNDACHSE, vr.RUNDACHSE)
            self.wahl_achse.setCurrentIndex(max(0, self._index_ohne_maschine(gemerkt)))
        self.wahl_achse.setToolTip(tr("va.rundachse.tooltip"))
        self.wahl_achse.currentIndexChanged.connect(lambda _i: self.waehle_rundachse())
        raster.addWidget(beschriftung(tr("va.rundachse"), tr("va.rundachse.tooltip")), zeile, 0)
        raster.addWidget(self.wahl_achse, zeile, 1, 1, 2)
        zeile += 1
        aufbau.addWidget(self.felder)

        self.urteil = QtGui.QLabel()
        self.urteil.setWordWrap(True)
        self.urteil.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        aufbau.addWidget(self.urteil)
        aufbau.addStretch()
        return ruhiges_mausrad(form)

    def _baue_bearbeitung(self):
        """Schritt 2: Was willst du machen? – zuerst „Rundum schruppen“."""
        seite = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(seite)
        aufbau.setContentsMargins(0, 0, 0, 0)
        self.mit_schruppen = QtGui.QCheckBox(tr("va.schruppen"))
        self.mit_schruppen.setChecked(True)
        self.mit_schruppen.setToolTip(tr("va.schruppen.tooltip"))
        schrift = self.mit_schruppen.font()
        schrift.setBold(True)
        self.mit_schruppen.setFont(schrift)
        self.mit_schruppen.toggled.connect(self._schruppen_umgeschaltet)
        aufbau.addWidget(self.mit_schruppen)
        erklaerung = self._grau()
        erklaerung.setText(tr("va.schruppen.text"))
        erklaerung.setWordWrap(True)
        aufbau.addWidget(erklaerung)

        self.schruppfelder = QtGui.QWidget()
        raster = QtGui.QGridLayout(self.schruppfelder)
        raster.setContentsMargins(0, 0, 0, 0)
        zeile = 0

        def reihe(text, tooltip, feld, breite=2):
            nonlocal zeile
            etikett = QtGui.QLabel(text)
            etikett.setToolTip(tooltip)
            feld.setToolTip(tooltip)
            raster.addWidget(etikett, zeile, 0)
            raster.addWidget(feld, zeile, 1, 1, breite)
            zeile += 1

        self.wahl_werkstoff = QtGui.QComboBox()
        self.wahl_werkstoff.currentIndexChanged.connect(lambda _i: self._werkstoff_gewaehlt())
        reihe(tr("va.werkstoff"), tr("va.werkstoff.tooltip"), self.wahl_werkstoff)
        self.wahl_fraeser = QtGui.QComboBox()
        self.wahl_fraeser.currentIndexChanged.connect(lambda _i: self._fraeser_gewaehlt())
        reihe(tr("va.fraeser"), tr("va.fraeser.tooltip"), self.wahl_fraeser, 1)
        raster.addWidget(
            knopf(
                tr("va.werkzeugverwaltung"),
                tr("va.werkzeugverwaltung.tooltip"),
                self.werkzeugverwaltung,
            ),
            zeile - 1,
            2,
        )
        self.wahl_einsatz = QtGui.QComboBox()
        self.wahl_einsatz.currentIndexChanged.connect(lambda _i: self._einsatz_gewaehlt())
        reihe(tr("va.einsatz"), tr("va.einsatz.tooltip"), self.wahl_einsatz)
        self.schnittwerte = self._grau()
        raster.addWidget(self.schnittwerte, zeile, 1, 1, 2)
        zeile += 1
        self.felder_schruppen = {}
        for feld, text, tooltip in (
            ("zustellung", tr("va.zustellung"), tr("va.zustellung.tooltip")),
            ("steigung", tr("va.steigung"), tr("va.steigung.tooltip")),
            ("aufmass", tr("va.aufmass"), tr("va.aufmass.tooltip")),
        ):
            eingabe = QtGui.QLineEdit()
            eingabe.setValidator(Zahlenpruefer(eingabe))
            eingabe.textChanged.connect(lambda _text: self._vorschau_starten())
            self.felder_schruppen[feld] = eingabe
            reihe(text, tooltip, mit_einheit(eingabe, einheiten.einheit(einheiten.LAENGE)))
        aufbau.addWidget(self.schruppfelder)
        self.ergebnis = self._grau()
        self.ergebnis.setWordWrap(True)
        aufbau.addWidget(self.ergebnis)
        self.radius_hinweis = self._grau()
        self.radius_hinweis.setWordWrap(True)
        self.radius_hinweis.setText(tr("va.radius"))
        aufbau.addWidget(self.radius_hinweis)
        self.hinweis_bearbeitung = QtGui.QLabel()
        self.hinweis_bearbeitung.setWordWrap(True)
        self.hinweis_bearbeitung.setStyleSheet(f"color: {ROT};")
        aufbau.addWidget(self.hinweis_bearbeitung)
        zurueck = knopf(tr("va.zurueck"), tr("va.zurueck.tooltip"), lambda: self.zeige_seite(1))
        aufbau.addWidget(zurueck, 0, QtCore.Qt.AlignLeft)
        aufbau.addStretch()
        return seite

    def _zahlenfeld(self, tooltip):
        feld = QtGui.QLineEdit()
        feld.setValidator(Zahlenpruefer(feld))
        feld.setToolTip(tooltip)
        feld.textChanged.connect(self._eingabe)
        return feld

    @staticmethod
    def _grau():
        etikett = QtGui.QLabel()
        etikett.setStyleSheet(f"color: {GRAU_TEXT};")
        return etikett

    # --- Aktionen (auch für die Szenarien) --------------------------------------

    def auswahl_lesen(self):
        """Nimmt die angeklickte Fläche – aufgerufen, wenn man in der 3D-Ansicht klickt; nur
        in Schritt 1."""
        if self.geschlossen or self.seite != 1:
            return
        wahl = gewaehlte_flaeche(self.doc)
        if wahl is not None and wahl[1] is not None and wahl != (self.teil, self.flaeche):
            self.waehle_flaeche(*wahl)

    def waehle_flaeche(self, teil, flaeche):
        """Legt `teil` mit seiner Fläche `flaeche` („FaceN“) vorne in die Stange."""
        teil = vr.original(teil)
        try:
            form = teil.Shape
            element = form.getElement(flaeche)
            vermessung = vr.vermesse(form, element)
        except ValueError:  # nicht eben (oder keine solche Fläche)
            self._hinweis(tr("va.nicht_eben", flaeche=flaeche, teil=teil.Label))
            return
        if self.job is not None and teil is not self.teil:
            # Ein anderes Teil: alles bisher Angelegte zurück, frisch anfangen.
            self._vor_neuem_teil()
        self.teil, self.flaeche, self.vermessung = teil, flaeche, vermessung
        self.mitte = vr.MITTE_AUTO
        erstes_mal = self.job is None
        if self._anwenden() and erstes_mal:
            self._zeige_bewegung(FreeCAD.Placement(self.teil.Placement))

    def waehle_mitte(self, mitte):
        """Mitte der runden Fläche (MITTE_FLAECHE) oder ganzes Teil (MITTE_TEIL)."""
        self.mitte = mitte
        self._anwenden()

    def waehle_rundachse(self, buchstabe=None):
        """Die Stange dreht um A, B oder C ohne Maschine – danach liegt sie in X, Y oder Z;
        ohne `buchstabe`: was in der Liste gewählt ist (auch eine Achse der Maschine)."""
        if buchstabe is not None:
            self.wahl_achse.setCurrentIndex(self._index_ohne_maschine(buchstabe))
            return  # der Wechsel ruft diese Methode noch einmal
        vorher = FreeCAD.Placement(vr.modell(self.job).Placement) if self.job else None
        if self._anwenden() and vorher is not None:
            self._zeige_bewegung(vorher)

    def plus90(self):
        """Dreht das Teil in der Stange um weitere 90°."""
        neu = (self._drehlage() + 90.0) % 360.0
        self.feld_drehlage.setText(zahl_zeigen(neu))  # 0 bleibt leer: der Vorschlag

    def achse(self):
        """Die gewählte Stangenachse (vierachs_achsen.Stangenachse)."""
        return self._achsen[max(0, self.wahl_achse.currentIndex())]

    def buchstabe(self):
        """Der Buchstabe der Rundachse: A, B oder C."""
        return self.achse().buchstabe

    def _index_ohne_maschine(self, buchstabe):
        """Der Eintrag „A/B/C – ohne Maschine“ mit diesem Buchstaben, oder -1."""
        for i, achse in enumerate(self._achsen):
            if not achse.maschine and achse.buchstabe == buchstabe:
                return i
        return -1

    def _zeige_bewegung(self, von):
        """Das Teil fährt von `von` an seine Stelle in der Stange und dreht sich einmal
        um die Stangenachse – so sieht man, wohin es kam und welche Achse dreht."""
        klon = vr.modell(self.job)
        laengs = self.achse().laengs
        self.einfahren = _Einfahren(klon, von, FreeCAD.Placement(klon.Placement), laengs)
        self.einfahren.start()

    # --- Schritt 2: Was willst du machen? -----------------------------------------

    def zeige_seite(self, nummer):
        """Schritt 1 (Rohteil) oder 2 (Was willst du machen?) – 2 erst, wenn es den Job gibt."""
        if nummer == 2 and self.job is None:
            return
        if self._uhr.isActive():
            self._uhr.stop()
            self._anwenden()
        self.seite = nummer
        self.seiten.setCurrentIndex(nummer - 1)
        titel = tr("va.kopf") if nummer == 1 else tr("va.kopf.bearbeitung")
        self._kopf_text.setText(f"<b>{titel}</b>")
        if nummer == 2:
            self._bearbeitung_fuellen()
        self._knoepfe_beschriften()

    def _bearbeitung_fuellen(self):
        """Werkstoff, Fräser und Einsatz anbieten – die Werkzeugverwaltung frisch gelesen.
        Der Werkstoff kommt vom Rohteil oder ist der zuletzt benutzte (wie in „Schnittwerte
        in den Job“)."""
        from .gui_werkzeuge import werkstoffe_anbieten

        vorher = self.werkstoff() if self.bibliothek is not None else None
        self.hinweis_bearbeitung.setText("")
        try:
            self.bibliothek = wz.Bibliothek.laden()
        except wz.BeschaedigteDatei as fehler:
            self.bibliothek = wz.Bibliothek()
            self.hinweis_bearbeitung.setText(
                tr("wv.fehler.laden", fehler=fehler, datei=fehler.beiseite)
            )
        self._fuellt = True
        try:
            werkstoffe_anbieten(self.wahl_werkstoff, self.bibliothek)
            if vorher is None:
                alle = self.bibliothek.alle_werkstoffe()
                werkstoff, _gemerkt = js.werkstoff_fuer(self.job, alle)
                vorher = werkstoff.kennung if werkstoff is not None else wz.ALLE
            self.wahl_werkstoff.setCurrentIndex(max(0, self.wahl_werkstoff.findData(vorher)))
        finally:
            self._fuellt = False
        self.radius_hinweis.setVisible(self.buchstabe() == "C")
        self._fraeser_fuellen()

    def werkstoff(self):
        """Kennung des gewählten Werkstoffs, oder wz.ALLE."""
        return self.wahl_werkstoff.currentData() or wz.ALLE

    def _werkstoff_gewaehlt(self):
        if not self._fuellt:
            self._fraeser_fuellen()

    @staticmethod
    def _passende_einsaetze(werkzeug, werkstoff):
        """Die Einsätze mit Drehzahl und Vorschub – nur mit ihnen gibt es einen Controller."""
        return [e for e in werkzeug.einsaetze(werkstoff) if js.werte(werkzeug, e)[1] > 0]

    def _fraeser_fuellen(self):
        """Die Fräser der Werkzeugverwaltung mit Schnittwerten für den Werkstoff; vorgewählt
        der bisher gewählte, sonst der zuletzt benutzte, sonst der erste Schaftfräser."""
        werkstoff = self.werkstoff()
        vorher = self.fraeser()
        self._fraeser = [
            w
            for w in sorted(self.bibliothek.werkzeuge, key=lambda w: w.nummer)
            if w.art in FRAESER_ARTEN
            and w.durchmesser > 0
            and self._passende_einsaetze(w, werkstoff)
        ]
        kennungen = [w.kennung for w in self._fraeser]
        gemerkt = _parameter().GetString(GEMERKT_FRAESER, "")
        if vorher is not None and vorher.kennung in kennungen:
            wahl = kennungen.index(vorher.kennung)
        elif gemerkt in kennungen:
            wahl = kennungen.index(gemerkt)
        else:
            arten = [w.art for w in self._fraeser]
            wahl = arten.index(wz.SCHAFTFRAESER) if wz.SCHAFTFRAESER in arten else 0
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
        """Der gewählte Fräser (werkzeuge.Werkzeug) oder None."""
        i = self.wahl_fraeser.currentIndex()
        return self._fraeser[i] if 0 <= i < len(self._fraeser) else None

    def _fraeser_gewaehlt(self):
        if not self._fuellt:
            self._einsatz_fuellen()

    def _einsatz_fuellen(self):
        """Die Einsätze des Fräsers; vorgewählt „Schruppen“, sonst „Schruppen dynamisch“,
        sonst der erste."""
        werkzeug = self.fraeser()
        self._einsaetze = (
            self._passende_einsaetze(werkzeug, self.werkstoff()) if werkzeug is not None else []
        )
        arten = [e.art for e in self._einsaetze]
        wahl = next((arten.index(a) for a in (wz.SCHRUPPEN, wz.DYNAMISCH) if a in arten), 0)
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
        """Der gewählte Einsatz (werkzeuge.Einsatz) oder None."""
        i = self.wahl_einsatz.currentIndex()
        return self._einsaetze[i] if 0 <= i < len(self._einsaetze) else None

    def _einsatz_gewaehlt(self):
        """Drehzahl und Vorschub zeigen, die Vorschläge in die Felder, die Lagen neu rechnen."""
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
        for feld, eingabe in self.felder_schruppen.items():
            eingabe.setPlaceholderText(groesse_zeigen(self._vorschlag(feld), einheiten.LAENGE))
        self._vorschau_starten()

    def _vorschlag(self, feld):
        """Der Wert eines leeren Felds (mm): Zustellung und Vorschub je Umdrehung aus dem
        Einsatz (ap und ae – ae höchstens der Durchmesser), das Aufmaß 0,3 mm."""
        if feld == "aufmass":
            return vo.AUFMASS
        einsatz = self.einsatz()
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else vo.ZUSTELLUNG
        werkzeug = self.fraeser()
        durchmesser = werkzeug.durchmesser if werkzeug is not None else 0.0
        if einsatz is not None and 0 < einsatz.ae <= durchmesser:
            return einsatz.ae
        return vo.STEIGUNG_ANTEIL * durchmesser

    def _wert(self, feld):
        """Wert eines Felds in Schritt 2 (mm); leer oder ungültig gilt der Vorschlag."""
        text = self.felder_schruppen[feld].text()
        try:
            return groesse_lesen(text, einheiten.LAENGE) if text.strip() else self._vorschlag(feld)
        except ValueError:
            return self._vorschlag(feld)

    def _schruppen_umgeschaltet(self, an):
        self.schruppfelder.setEnabled(an)
        self.ergebnis.setVisible(an)
        self.hinweis_bearbeitung.setText("")
        if an:
            self._vorschau_starten()
        self._knoepfe_beschriften()

    def _vorschau_starten(self):
        if self._fuellt:
            return
        self.vorschau = None
        self._vorschau_uhr.start()  # erst nach einer kurzen Pause rechnen
        self._knoepfe_beschriften()

    def _vorschau_rechnen(self):
        """Die Bahn wie die Operation sie rechnet – für „→ 5 Lagen (Ø 80 → Ø 60,6)“ und damit
        „Anlegen“ weiß, ob es geht."""
        self._vorschau_uhr.stop()
        if self.geschlossen or self.seite != 2 or not self.mit_schruppen.isChecked():
            return
        self.vorschau = None
        self.ergebnis.setText("")
        self.hinweis_bearbeitung.setText("")
        werkzeug = self.fraeser()
        if werkzeug is None or self.einsatz() is None:
            self.hinweis_bearbeitung.setText(tr("va.fraeser.keiner"))
            self._knoepfe_beschriften()
            return
        achse = self.achse()
        try:
            self.vorschau = vo.bahn_fuer(
                self.job,
                self.job.Model.Group,
                achse.laengs,
                va.radial(achse),
                werkzeug.durchmesser / 2,
                self._wert("zustellung"),
                self._wert("steigung"),
                self._wert("aufmass"),
            )
        except ValueError as fehler:
            self.hinweis_bearbeitung.setText(str(fehler))
        else:
            self.ergebnis.setText(self._lagen_text(self.vorschau))
        self._knoepfe_beschriften()

    def _lagen_text(self, bahn):
        """„→ 5 Lagen (Ø 80 → Ø 60,6)“ – und was hinten nicht erreicht wird."""
        from .reichweite import weg_text

        laenge = einheiten.LAENGE
        if bahn.lagen == 0:
            text = tr("va.lagen.keine")
        else:
            von = groesse_fest(self.stange().durchmesser, laenge, 1)
            bis = groesse_fest(2 * bahn.r_min, laenge, 1)
            if bahn.lagen == 1:
                text = tr("va.lagen.eine", von=von, bis=bis)
            else:
                text = tr("va.lagen", lagen=bahn.lagen, von=von, bis=bis)
        if bahn.hinten_frei > 0:
            text += " " + tr("vb.hinten_frei", laenge=weg_text(bahn.hinten_frei))
        return text

    def _kann_anlegen(self):
        """Schritt 2: ohne Schruppen immer; mit, wenn Fräser und Einsatz gewählt sind und die
        Vorschau keinen Fehler meldet."""
        if not self.mit_schruppen.isChecked():
            return True
        return (
            self.fraeser() is not None
            and self.einsatz() is not None
            and not self.hinweis_bearbeitung.text()
        )

    def werkzeugverwaltung(self):
        """Öffnet die Werkzeugverwaltung; speichert man dort, liest Schritt 2 sie neu."""
        from . import gui_werkzeuge

        dialog = gui_werkzeuge.oeffne()
        if getattr(self, "_werkzeugdialog", None) is not dialog:
            self._werkzeugdialog = dialog
            dialog.gespeichert.connect(self._werkzeuge_gespeichert)

    def _werkzeuge_gespeichert(self):
        if VierachsPanel.offen is self and self.seite == 2:
            self._bearbeitung_fuellen()

    def _schruppen_pruefen(self):
        """Geht das Schruppen mit Fräser, Einsatz und Werten? Rechnet die Vorschau, wenn sie
        noch fehlt."""
        if self.vorschau is None:
            self._vorschau_rechnen()
        return (
            self.fraeser() is not None and self.einsatz() is not None and self.vorschau is not None
        )

    def _schruppen_anlegen(self):
        """Werkzeug-Controller und „Rundum schruppen“ in den Job – ein eigener Schritt
        Rückgängig, in einem Befehl (_im_befehl). Den Controller, den jeder neue Job von
        FreeCAD bekommt, nimmt es heraus (D-30). Geht es nicht, steht der Grund rot im
        Fenster: False."""
        werkzeug, einsatz, achse = self.fraeser(), self.einsatz(), self.achse()
        werte = (self._wert("zustellung"), self._wert("steigung"), self._wert("aufmass"))

        def anlegen():
            self.doc.openTransaction(tr("va.transaktion.schruppen"))
            try:
                ue.uebergeben(self.bibliothek)
                fremde = js.unbenutzte_fremde_controller(self.job, self.bibliothek)
                js.controller_weg(self.doc, fremde)
                tc = js.controller_ohne_transaktion(
                    self.doc, self.job, werkzeug, einsatz, self.werkstoff()
                )
                operation = vo.lege_an(self.job, tc, achse, *werte, quer_auf_null=achse.quer)
                self.doc.recompute()
            except Exception:
                self.doc.abortTransaction()
                raise
            return operation

        try:
            self.operation = _im_befehl(anlegen)
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"4-Achs-Bearbeitung: {fehler}\n")
            self.operation = None
            self.hinweis_bearbeitung.setText(tr("va.fehler.anlegen", fehler=str(fehler)))
            self._knoepfe_beschriften()
            return False
        return True

    # --- Rechnen und ins Dokument ------------------------------------------------

    def _eingabe(self, _text=""):
        if not self._fuellt:
            self._uhr.start()  # erst nach einer kurzen Pause nachziehen

    def _drehlage(self):
        try:
            return zahl_lesen(self.feld_drehlage.text())
        except ValueError:
            return 0.0

    def _gemerkt(self, feld):
        schluessel, ab_werk = GEMERKT[feld]
        return _parameter().GetFloat(schluessel, ab_werk)

    def _laenge(self, feld):
        """Wert eines Längenfelds in mm; leer oder ungültig gilt der Vorschlag."""
        text = self.felder_laenge[feld].text()
        try:
            return groesse_lesen(text, einheiten.LAENGE) if text.strip() else self._gemerkt(feld)
        except ValueError:
            return self._gemerkt(feld)

    def vorschlag_stange(self):
        """Der Stangen-Ø, der gilt, wenn das Feld leer ist (mm)."""
        mitte = vr.welche_mitte(self.vermessung, self.mitte, 0.0)
        return vr.vorschlag_durchmesser(self.vermessung.noetig[mitte], einheiten.in_zoll())

    def stange(self):
        """Die Stange aus den Feldern (vierachs_rohteil.Stange)."""
        try:
            durchmesser = groesse_lesen(self.feld_stange.text(), einheiten.LAENGE)
        except ValueError:
            durchmesser = 0.0
        if durchmesser <= 0:
            durchmesser = self.vorschlag_stange()
        return vr.Stange(
            durchmesser,
            self._laenge("planaufmass"),
            self._laenge("abstechbreite"),
            self._laenge("spannlaenge"),
        )

    def _anwenden(self):
        """Rechnet die Lage und zieht Job und Stange nach. Gibt zurück, ob es geklappt hat."""
        if self.vermessung is None or self.geschlossen:
            self._auffrischen()
            return False
        if self.einfahren:
            self.einfahren.stopp()
        stange = self.stange()
        self.lage = vr.lage(
            self.vermessung, self.achse(), self.mitte, self._drehlage(), stange.durchmesser
        )
        erstes_mal = self.job is None
        try:
            if erstes_mal:
                self.job = _im_befehl(lambda: self._neuer_job(stange))
            else:
                self.job = vr.richte_ein(
                    self.doc, self.teil, self.lage, stange, self.achse(), job=self.job
                )
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"4-Achs-Bearbeitung: {fehler}\n")
            self._hinweis(tr("va.fehler", fehler=str(fehler)))
            return False
        if erstes_mal:
            self._job_zeigen()
        self._auffrischen()
        return True

    def _neuer_job(self, stange):
        """Legt den Job an und öffnet dafür die Transaktion des Assistenten – nur in
        _im_befehl. Sie bleibt offen bis „Anlegen“ oder „Abbrechen“: So geht alles bis
        dahin mit einem Strg+Z zurück."""
        self.doc.openTransaction(tr("va.titel"))
        job = vr.richte_ein(
            self.doc,
            self.teil,
            self.lage,
            stange,
            self.achse(),
            beschriftung=tr("va.job", teil=self.teil.Label),
        )
        if _globale_transaktionen():
            # Offen halten über das Ende des Befehls hinaus – sonst schlösse FreeCAD sie dort.
            FreeCAD.setActiveTransaction(tr("va.titel"), True)
        return job

    def _job_zeigen(self):
        """Anzeige des neuen Jobs wie bei FreeCADs Befehl „Job“ – aber in unserer
        Transaktion (FreeCADs Befehl öffnet eine eigene). Der Klon ist das Teil in
        der Stange, das Original verschwindet solange."""
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
        self._stange_anzeigen(*STANGE_ANZEIGE, waehlbar=False)

    def _stange_anzeigen(self, darstellung, durchsicht, waehlbar):
        ansicht = self.job.Stock.ViewObject if self.job and self.job.Stock else None
        if ansicht is None:
            return
        ansicht.DisplayMode = darstellung
        ansicht.Transparency = durchsicht
        ansicht.Selectable = waehlbar

    def _anzeige_wie_in_cam(self):
        """Nach „Anlegen“ sieht die Stange aus wie jedes Rohteil in CAM."""
        self._stange_anzeigen(*STANGE_CAM, waehlbar=True)

    def _sichtbarkeit_zurueck(self):
        if self._sichtbar_vorher is not None:
            teil, sichtbar = self._sichtbar_vorher
            if teil.ViewObject is not None:
                teil.ViewObject.Visibility = sichtbar
            self._sichtbar_vorher = None

    def _vor_neuem_teil(self):
        """Ein anderes Teil wurde angeklickt: den bisherigen Job verwerfen."""
        if self.einfahren:
            self.einfahren.stopp()
            self.einfahren = None
        self._sichtbarkeit_zurueck()
        self.doc.abortTransaction()
        self.job = None  # der nächste öffnet eine neue Transaktion (_neuer_job)

    def _vorschlaege_merken(self):
        """Was man eingetragen hat, ist beim nächsten Mal der Vorschlag."""
        parameter = _parameter()
        for feld, (schluessel, _ab_werk) in GEMERKT.items():
            if self.felder_laenge[feld].text().strip():
                parameter.SetFloat(schluessel, self._laenge(feld))
        parameter.SetString(GEMERKT_RUNDACHSE, self.buchstabe())
        if self.mit_schruppen.isChecked() and self.fraeser() is not None:
            parameter.SetString(GEMERKT_FRAESER, self.fraeser().kennung)

    # --- Anzeige ------------------------------------------------------------------

    def _hinweis(self, text):
        self.urteil.setStyleSheet(f"color: {ROT};")
        self.urteil.setText(text)

    def _auffrischen(self):
        """Beschriftungen, Vorschläge und Urteil – das Dokument bleibt, wie es ist."""
        self._fuellt = True
        try:
            self._auffrischen_innen()
        finally:
            self._fuellt = False
        self._knoepfe_beschriften()

    def _auffrischen_innen(self):
        mess = self.vermessung
        self.felder.setEnabled(mess is not None)
        if mess is None:
            self.teil_text.setText(tr("va.teil.leer"))
            self.urteil.setText("")
            return
        einheit_laenge = einheiten.LAENGE
        if mess.kreis is not None:
            art = tr("va.art.rund", d=groesse_fest(2 * mess.kreis[1], einheit_laenge, 1))
            self.knopf_mitte_flaeche.setText(tr("va.mitte.flaeche"))
        else:
            art = tr("va.art.eben")
            self.knopf_mitte_flaeche.setText(tr("va.mitte.flaeche_eckig"))
        self.teil_text.setText(
            tr("va.teil.text", teil=self.teil.Label, flaeche=self.flaeche, art=art)
        )
        self.braucht_flaeche.setText(
            tr("va.braucht", d=groesse_fest(mess.noetig[vr.MITTE_FLAECHE], einheit_laenge, 1))
        )
        self.braucht_teil.setText(
            tr("va.braucht", d=groesse_fest(mess.noetig[vr.MITTE_TEIL], einheit_laenge, 1))
        )
        self.feld_stange.setPlaceholderText(groesse_zeigen(self.vorschlag_stange(), einheit_laenge))
        if self.lage is None:
            return
        gewaehlt = self.knopf_mitte_flaeche if self.lage.mitte == vr.MITTE_FLAECHE else None
        (gewaehlt or self.knopf_mitte_teil).setChecked(True)
        stange = self.stange()
        self.laenge_text.setText(
            tr("va.laenge", laenge=groesse_fest(vr.stangenlaenge(mess, stange), einheit_laenge, 1))
        )
        rest = vr.aufmass(self.lage, stange.durchmesser)
        if rest >= 0:
            self.urteil.setStyleSheet(f"color: {GRUEN};")
            self.urteil.setText(tr("va.passt", aufmass=groesse_fest(rest, einheit_laenge, 1)))
        else:
            vorschlag = vr.vorschlag_durchmesser(self.lage.durchmesser, einheiten.in_zoll())
            self._hinweis(
                tr(
                    "va.passt_nicht",
                    noetig=groesse_fest(self.lage.durchmesser, einheit_laenge, 1),
                    vorschlag=groesse_fest(vorschlag, einheit_laenge, 1),
                )
            )
