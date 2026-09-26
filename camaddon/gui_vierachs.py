# SPDX-License-Identifier: LGPL-2.1-or-later
"""Assistent „4-Achs-Bearbeitung“ (Spezifikation W-003) – Schritt Rohteil (Stufe V1).

Man klickt die ebene Stirnfläche eines Teils an, und das Teil sitzt vorne
mittig in einer runden Stange: ein neuer CAM-Job, das Teil in seinem
Modell-Klon, das Rohteil ein Zylinder. Gerechnet wird in
vierachs_rohteil.py. Jede Eingabe geht sofort ins Dokument – wie in
„Maschine bearbeiten“ –, damit die 3D-Ansicht stimmt; „Anlegen“ übernimmt
alles als einen Schritt Rückgängig, „Abbrechen“ verwirft auch Job und
Stange. Flächen, Werkzeuge und Bahnen (Schritte 2 bis 4) kommen in den
Stufen V3 bis V6 dazu.

Leere Felder gelten mit ihrem grauen Vorschlag (Manuel: „alles einstellbar,
aber mit Vorschlägen als Standard“). Was man einträgt, ist beim nächsten Mal
der Vorschlag – außer dem Stangen-Ø, der hängt am Teil.
"""

import math

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, einheiten, symbol
from . import vierachs_rohteil as vr
from .gui_hilfe import kopfzeile
from .gui_maschine import _EnterBleibtImDialog
from .gui_teile import ROT, knopf, mit_einheit, ruhiges_mausrad
from .gui_zahlen import (
    Zahlenpruefer,
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


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def _achstexte():
    """Die Einträge der Liste „Rundachse“: Buchstabe → ein Satz, wie die Stange liegt."""
    return {"A": tr("va.achse.a"), "B": tr("va.achse.b"), "C": tr("va.achse.c")}


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
        # Ein Schritt für alles, was bis „Anlegen“ passiert; Abbrechen verwirft ihn.
        dokument.openTransaction(tr("va.titel"))
        FreeCADGui.Control.showDialog(VierachsPanel(dokument, wahl))


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
        """OK heißt „Anlegen“ und geht erst, wenn das Teil in der Stange liegt.

        Aufgehoben wird die Knopfleiste, nicht der Knopf: Mit der Python-Hülle
        der Leiste verfiele auch die des Knopfs (ausprobiert, P-2026-09-26-79) –
        CAM macht es ebenso (Path.Op.Gui.Base.TaskPanel).
        """
        self._knoepfe = knoepfe
        ok = self.knopf_anlegen()
        ok.setText(tr("va.anlegen"))
        ok.setToolTip(tr("va.anlegen.tooltip"))
        ok.setEnabled(self.job is not None)

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
        self._vor_dem_schliessen()
        self._anzeige_wie_in_cam()
        self._vorschlaege_merken()
        self.doc.commitTransaction()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    def reject(self):
        self._vor_dem_schliessen()
        self._sichtbarkeit_zurueck()
        self.doc.abortTransaction()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    def _vor_dem_schliessen(self):
        """Bewegung anhalten, Auswahl-Hilfen abmelden."""
        VierachsPanel.offen = None
        self.geschlossen = True
        self._uhr.stop()
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
        aufbau = QtGui.QVBoxLayout(form)
        aufbau.addWidget(kopfzeile(tr("va.kopf"), "vierachs"))
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

        self.wahl_achse = QtGui.QComboBox()
        for buchstabe, text in _achstexte().items():
            self.wahl_achse.addItem(text, buchstabe)
        gemerkt = _parameter().GetString(GEMERKT_RUNDACHSE, vr.RUNDACHSE)
        self.wahl_achse.setCurrentIndex(max(0, self.wahl_achse.findData(gemerkt)))
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
        """Nimmt die angeklickte Fläche – aufgerufen, wenn man in der 3D-Ansicht klickt."""
        if self.geschlossen:
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
        """Die Stange dreht um A, B oder C – danach liegt sie in X, Y oder Z."""
        if buchstabe is not None:
            self.wahl_achse.setCurrentIndex(self.wahl_achse.findData(buchstabe))
            return  # der Wechsel ruft diese Methode noch einmal
        vorher = FreeCAD.Placement(vr.modell(self.job).Placement) if self.job else None
        if self._anwenden() and vorher is not None:
            self._zeige_bewegung(vorher)

    def plus90(self):
        """Dreht das Teil in der Stange um weitere 90°."""
        neu = (self._drehlage() + 90.0) % 360.0
        self.feld_drehlage.setText(zahl_zeigen(neu))  # 0 bleibt leer: der Vorschlag

    def buchstabe(self):
        """Der Buchstabe der Rundachse: A, B oder C."""
        return self.wahl_achse.currentData() or vr.RUNDACHSE

    def _zeige_bewegung(self, von):
        """Das Teil fährt von `von` an seine Stelle in der Stange und dreht sich einmal
        um die Stangenachse – so sieht man, wohin es kam und welche Achse dreht."""
        klon = vr.modell(self.job)
        laengs, _radial = vr.ACHSEN[self.buchstabe()]
        self.einfahren = _Einfahren(klon, von, FreeCAD.Placement(klon.Placement), laengs)
        self.einfahren.start()

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
            self.vermessung, self.buchstabe(), self.mitte, self._drehlage(), stange.durchmesser
        )
        erstes_mal = self.job is None
        try:
            self.job = vr.richte_ein(
                self.doc,
                self.teil,
                self.lage,
                stange,
                self.buchstabe(),
                job=self.job,
                beschriftung=tr("va.job", teil=self.teil.Label) if erstes_mal else None,
            )
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"4-Achs-Bearbeitung: {fehler}\n")
            self._hinweis(tr("va.fehler", fehler=str(fehler)))
            return False
        if erstes_mal:
            self._job_zeigen()
        self._auffrischen()
        return True

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
        self.doc.openTransaction(tr("va.titel"))
        self.job = None

    def _vorschlaege_merken(self):
        """Was man eingetragen hat, ist beim nächsten Mal der Vorschlag."""
        parameter = _parameter()
        for feld, (schluessel, _ab_werk) in GEMERKT.items():
            if self.felder_laenge[feld].text().strip():
                parameter.SetFloat(schluessel, self._laenge(feld))
        parameter.SetString(GEMERKT_RUNDACHSE, self.buchstabe())

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
        ok = self.knopf_anlegen()
        if ok is not None:
            ok.setEnabled(self.job is not None)

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
