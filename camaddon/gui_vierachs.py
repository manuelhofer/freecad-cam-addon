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
Darunter „Rundum schlichten“ (V5d): Fräser jeder Form, die das Addon kennt
(fraeserform), Einsatz, Schrittweite aus der Werkzeugtabelle mit der Kammhöhe,
Aufmaß, dazu grob gerechnet Umdrehungen und Zeit. Überlauf, Abstand zum Futter
und Sicherheitsabstand (V3f) gelten für beide; die Stange ragt so weit aus dem
Futter, wie Teil, Überlauf, Fräser und Abstand es brauchen – ein Satz sagt, wie
weit. „Anlegen“ legt Job und Stange als einen Schritt Rückgängig an, Controller
und Operationen (vierachs_operation, vierachs_schlichten) als einen zweiten;
„Abbrechen“ verwirft alles.

Leere Felder gelten mit ihrem grauen Vorschlag (Manuel: „alles einstellbar,
aber mit Vorschlägen als Standard“). Was man einträgt, ist beim nächsten Mal
der Vorschlag – außer dem Stangen-Ø, der hängt am Teil.

Flächen wählen (Stufe V4, Manuel 2026-09-30: „nur Flächen am Mantel anklicken, die ich
bearbeiten will … und wenn ich alle anklicke, dann wird komplett rings um bearbeitet“): In
Schritt 2 nimmt ein Klick auf eine Fläche des Teils sie dazu, ein zweiter heraus. Die Liste
nennt Art und Erreichbarkeit (vierachs_flaechen), die 3D-Ansicht färbt die gewählten Flächen
grün, gelb oder rot – nur die Anzeige, danach wieder wie vorher. Ohne Wahl oder mit allen
Mantelflächen: rundum.

Nachträglich ändern (Manuel, 2026-09-29: „wenn ich jetzt hier nochmal
schnittwerte ändern will oder anders werkzeug komme ich nicht mehr in die maske
rein“): Doppelklick auf „Rundum schruppen“ oder „Rundum schlichten“ – oder die
Operation bzw. ihren Job wählen und den Knopf drücken – öffnet Schritt 2 mit
Fräser, Einsatz und Werten der Operation; „Zurück“ führt zu Stange, Mitte und
Rundachse, wie sie im Job stehen. „Übernehmen“ ändert die Operation als einen
Schritt Rückgängig, eine geänderte Stange als einen zweiten davor. Beim
Schruppen lässt sich dabei ein Schlichten dazunehmen.
"""

import contextlib
import html
import math

import FreeCAD
import FreeCADGui
import numpy as np
from PySide import QtCore, QtGui

from . import (
    PARAMETER_PFAD,
    einheiten,
    farben,
    gui_rechnet,
    gui_zeigen,
    stl_anzeige,
    stl_teil,
    symbol,
    uhren,
)
from . import aufloesung as au
from . import bestueckung as bs
from . import formteile as ft
from . import fraeserform as ff
from . import halter as hl
from . import job_schnittwerte as js
from . import magazin as mg
from . import maschine as m
from . import messstopp as ms
from . import uebergabe_werkzeuge as ue
from . import vierachs_achsen as va
from . import vierachs_bahn as vb
from . import vierachs_entgratbahn as ve
from . import vierachs_entgraten as vent
from . import vierachs_flaechen as vf
from . import vierachs_huelle as vh
from . import vierachs_operation as vo
from . import vierachs_plan as vplan
from . import vierachs_planbahn as vp
from . import vierachs_rohteil as vr
from . import vierachs_schlichten as vs
from . import vierachs_vorschau as vv
from . import werkzeuge as wz
from .gui_hilfe import dialog_schliessen, kopfzeile
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

GRUEN = farben.GRUEN  # „passt“ – hell oder dunkel nach dem Theme (farben.py)
GRAU_TEXT = farben.GRAU  # gerechnete Werte


def _im_3d(farbe):
    """Die Farbe einer Fläche in der 3D-Ansicht zur Textfarbe ihrer Zeile in der Liste. Die
    Flächen behalten in jedem Theme ihre Farben (Tango-Grün, Rot, dunkles Gelb) – seit
    P-2026-10-10-42 folgt nur der Text dem Theme (P-2026-10-10-51)."""
    from .gui_kollision import GELB

    return {GRUEN: "#4e9a06", ROT: "#c0392b", GELB: "#b9770e"}.get(farbe, farbe)


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
GEMERKT_SCHLICHTFRAESER = "VaSchlichtfraeser"  # … des zuletzt gewählten Schlichtfräsers
GEMERKT_PLANFRAESER = "VaPlanfraeser"  # … des zuletzt gewählten Fräsers für Plan indexiert
GEMERKT_ENTGRATFRAESER = "VaEntgratfraeser"  # … des zuletzt gewählten Fräsers zum Entgraten
# Welche Bearbeitung man ändert.
SCHRUPPEN, SCHLICHTEN, PLAN, ENTGRATEN = "schruppen", "schlichten", "plan", "entgraten"
# Gelb, wenn die Kugel nach dem Schruppen stellenweise so viel mal Aufmaß × Durchmesser nimmt –
# so viel nimmt sie, wo sie das erste Mal mit ganzer Breite übers Aufmaß fährt (Frage 8,
# P-2026-10-11-44/46: mit Aufmaß × Schrittweite wäre fast jeder Job gelb, auch Manuels Nase mit
# 3,1 mm² gegen 2,4 mm²). Darunter steht grau, wie viel.
REST_VIEL = 2.0
REST_AUFMASS_MINDESTENS = 0.1  # mm: so viel Aufmaß rechnet der Vergleich mindestens
# Vorschlichten (W-031): die Kammhöhe als Anteil seines Aufmaßes – was es zwischen den Bahnen
# stehen lässt, kommt zum Aufmaß dazu, das die Kugel beim Schlichten nimmt.
VORSCHLICHTEN_KAMM_ANTEIL = 1 / 3

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


def _saetze(bahn):
    """(Sätze (n, 4), Eilgänge) einer Bahn der Vorschau für die Nebenrechner (voxelstange.als_feld)
    – an der Bahn gemerkt: Rest und Halter fragen beide danach, und die Schleife über alle Punkte
    kostet am Nasen-Testteil je Bahn eine Zehntelsekunde im Fenster."""
    from . import voxelstange as vx

    gemerkt = getattr(bahn, "_als_saetze", None)
    if gemerkt is None:
        gemerkt = (vx.als_feld(bahn.punkte), np.array([bool(p.eilgang) for p in bahn.punkte]))
        bahn._als_saetze = gemerkt
    return gemerkt


def _achstexte():
    """Die Einträge der Liste „Rundachse“ ohne Maschine: Buchstabe → ein Satz, wie die
    Stange liegt."""
    return {"A": tr("va.achse.a"), "B": tr("va.achse.b"), "C": tr("va.achse.c")}


def achstext(achse):
    """Der Eintrag der Liste „Rundachse“ für eine Stangenachse (vierachs_achsen) – die
    Maschine steht darüber in ihrer eigenen Liste."""
    if not achse.maschine and gleich(achse.laengs, vr.ACHSEN[achse.buchstabe][0]):
        return _achstexte()[achse.buchstabe]
    richtung = va.achsbuchstabe(achse.laengs)
    if not richtung:
        return tr("va.achse.der_maschine_schraeg", buchstabe=achse.buchstabe)
    return tr("va.achse.der_maschine", buchstabe=achse.buchstabe, richtung=richtung)


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
    # Nicht bool(form.Faces): am Geist (STL, 68.242 Flächen) 1 s beim Anklicken der Standfläche.
    return form is not None and not form.isNull() and ft.anzahl(form) > 0


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
        from .gui_hilfe import arbeitsdokument

        dokument = arbeitsdokument()  # das der Auswahl – nicht die Maschine, die gerade aktiv ist
        if dokument is None:
            QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(), tr("va.titel"), tr("va.kein_dokument")
            )
            return
        operation = gewaehlte_operation(dokument)
        if operation is not None:
            bearbeiten(operation)
            return
        from . import gui_stl

        netz = gui_stl.gewaehltes_netz(dokument)
        angebot = None
        if netz is None:  # nichts gewählt, aber ein STL im Dokument: fragen, ob es das sein soll
            angebot = gui_stl.stl_angebot(dokument, tr("va.titel"))
            if angebot is not None and stl_teil.ist_netz(angebot):
                netz, angebot = angebot, None
        if netz is not None:
            # Ein STL (W-017): erst der Körper aus seinen Dreiecken – Maßstab im Fenster davor.
            teil = gui_stl.teil_aus_netz(dokument, netz)
            if teil is None:
                return
            wahl = (teil, None)
        elif angebot is not None:
            wahl = (angebot, None)
        else:
            wahl = gewaehlte_flaeche(dokument)
            if wahl is not None:  # ein Link in der Maschine (B-020): im Dokument des Teils
                from .gui_bearbeitung import _aktivieren, teil_hinter_link

                teil = teil_hinter_link(wahl[0])
                if teil is not wahl[0]:
                    wahl, dokument = (teil, wahl[1]), teil.Document
                    _aktivieren(dokument)
        # Die Transaktion öffnet der Assistent, wenn er den Job anlegt (_neuer_job).
        FreeCADGui.Control.showDialog(VierachsPanel(dokument, wahl))


def klickpunkt(dokument):
    """Wo die gewählte Fläche angeklickt wurde (Weltkoordinaten) – None ohne."""
    for auswahl in FreeCADGui.Selection.getSelectionEx(dokument.Name, 0):
        punkte = list(getattr(auswahl, "PickedPoints", None) or [])
        if punkte:
            return FreeCAD.Vector(punkte[0])
    return None


def gewaehlte_operation(dokument):
    """Die gewählte „Rundum schruppen“ oder „Rundum schlichten“ – oder, ist ein Job oder sein
    Ordner „Operations“ gewählt, sein „Rundum schruppen“ (dort lässt sich das Schlichten
    dazunehmen; Manuel, 2026-09-30: „hier jetzt noch einen schlicht gang hinzufügen“), sonst
    seine erste Rundum-Operation; sonst None."""
    jobs = js.jobs(dokument)
    for objekt in FreeCADGui.Selection.getSelection(dokument.Name):
        if vo.ist_rundum(objekt):
            return objekt
        job = next(
            (j for j in jobs if objekt is j or objekt is getattr(j, "Operations", None)), None
        )
        if job is not None:
            operationen = js.operationen(job)
            gefunden = [o for o in operationen if vo.ist_schruppen(o)]
            gefunden += [o for o in operationen if vo.ist_rundum(o)]
            if gefunden:
                return gefunden[0]
    return None


def bearbeiten(operation):
    """Öffnet den Assistenten zum Ändern von `operation` – in Schritt 2, mit ihren Werten.
    Nichts, solange ein anderes Aufgabenfenster offen ist."""
    if FreeCADGui.Control.activeDialog():
        return
    FreeCADGui.Control.showDialog(VierachsPanel(operation.Document, operation=operation))


def job_von(operation):
    """Der Job, in dem die Operation steht, oder None."""
    for job in js.jobs(operation.Document):
        if operation in js.operationen(job):
            return job
    return None


def _gleiche_achse(a, b):
    """Rechnen zwei Stangenachsen gleich (Buchstabe, Richtung, Drehsinn, Querachse)?"""
    return (a.buchstabe, a.drehsinn, a.quer) == (b.buchstabe, b.drehsinn, b.quer) and gleich(
        a.laengs, b.laengs
    )


def _gleiche_stange(a, b):
    """Liegen die Stangen gleich im Job (Ø, Planaufmaß, Lücke, Spannlänge, Abstechbreite)?"""
    if a is None or b is None:
        return a is b
    return all(
        abs(x - y) < 1e-9
        for x, y in (
            (a.durchmesser, b.durchmesser),
            (a.planaufmass, b.planaufmass),
            (a.luecke, b.luecke),
            (a.spannlaenge, b.spannlaenge),
            (a.abstechbreite, b.abstechbreite),
        )
    )


def gleich(a, b):
    """Zeigen zwei Richtungen gleich (auf 1e-6)?"""
    return (FreeCAD.Vector(a) - FreeCAD.Vector(b)).Length < 1e-6


def achse_der_operation(operation):
    """Die Stangenachse (vierachs_achsen.Stangenachse), mit der die Operation rechnet."""
    return va.Stangenachse(
        str(operation.Rundachse),
        FreeCAD.Vector(operation.Stangenachse),
        drehsinn=int(operation.Drehsinn),
        quer=bool(operation.QuerAufNull),
    )


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

    Während `aufgabe` rechnet (Anlegen, Ändern), zeichnet das Fenster neu, nimmt aber keinen
    Klick an (uhren.atmend; P-2026-10-11-67/-72).
    """
    with uhren.atmend():
        return _im_befehl_ohne_atmen(aufgabe)


def _im_befehl_ohne_atmen(aufgabe):
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
    """Meldet dem Assistenten jede neu angeklickte Fläche – in Schritt 1 die Stirnfläche, in
    Schritt 2 eine Fläche zum Fräsen (V4)."""

    def __init__(self, panel):
        self.panel = panel

    def addSelection(self, _dokument, objekt, unterelement, punkt):
        from .gui_hilfe import lebt

        if not lebt(self.panel):  # das Fenster ist weg: abmelden statt ins Leere zu rufen
            with contextlib.suppress(Exception):
                FreeCADGui.Selection.removeObserver(self)
            return
        if not unterelement:
            return
        # Erst wenn FreeCAD mit der Auswahl fertig ist – der Assistent ändert dabei das
        # Dokument bzw. leert die Auswahl.
        if self.panel.seite == 2:
            uhren.gleich(lambda: self.panel.flaeche_angeklickt(objekt, unterelement))
        else:
            # Der Klickpunkt: An einer runden Fläche liegt das Ende vorne, an dem man klickt.
            angeklickt = FreeCAD.Vector(*punkt) if punkt else None
            uhren.gleich(lambda: self.panel.auswahl_lesen(angeklickt, _dokument))


class _NurFlaechen:
    """Anklicken lassen sich nur Flächen – nicht die Stange, durch die man hindurchklickt."""

    def __init__(self, panel):
        self.panel = panel

    def allow(self, _dokument, objekt, unterelement):
        from .gui_hilfe import lebt

        if not lebt(self.panel):  # das Fenster ist weg: die Sperre auch
            with contextlib.suppress(Exception):
                FreeCADGui.Selection.removeSelectionGate()
            return True
        weg = unterelement.split(".") if unterelement else []
        if not weg or not weg[-1].startswith("Face"):
            return False
        job = self.panel.job
        name = getattr(objekt, "Name", "")
        if self.panel.seite == 2 and job is not None:  # nur das Teil im Job (V4)
            klon = vr.modell(job).Name
            return name == klon or klon in weg
        rohteil = job.Stock if job is not None else None
        return rohteil is None or (name != rohteil.Name and rohteil.Name not in weg)


class _Einfahren:
    """Zeigt ohne Worte, was passiert: Das Teil fährt von seiner alten Lage in die
    Stange und dreht sich einmal um die Stangenachse. Am Ende steht es exakt am Ziel."""

    def __init__(self, objekt, von, nach, achse):
        self.objekt, self.von, self.nach, self.achse = objekt, von, nach, achse
        self.schritt = 0
        self.uhr = QtCore.QTimer()
        self.uhr.setInterval(TAKT_MS)
        self.uhr.timeout.connect(uhren.aus_der_schleife(self.uhr, self._weiter))

    def start(self):
        self.uhr.start()

    def laeuft(self):
        return self.uhr.isActive()

    def stopp(self):
        """Anhalten – das Teil steht dann am Ziel, auch mitten in der Bewegung. Ist die Bewegung
        schon vorbei, bleibt es, wo es ist: Es kann seither eine andere Lage haben (Standfläche,
        „Umdrehen“, Drehlage) – „Anlegen“ setzte es sonst auf das Ziel der ersten Bewegung zurück,
        nachdem die Bahnen schon gerechnet waren (Manuel, 2026-10-12, am Geist: „der Geist da
        falsch drinnen“)."""
        if not self.uhr.isActive():
            return
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
            self.stopp()  # läuft noch: steht danach exakt am Ziel


def _cos_pi(anteil):
    return math.cos(math.pi * anteil)


class _Reihen:
    """Ein Raster aus Reihen „Beschriftung – Feld“ für Schritt 2."""

    def __init__(self):
        self.widget = QtGui.QWidget()
        self.raster = QtGui.QGridLayout(self.widget)
        self.raster.setContentsMargins(0, 0, 0, 0)
        self.zeile = 0
        self._beschriftungen = []

    def reihe(self, text, tooltip, feld, breite=2):
        etikett = QtGui.QLabel(text)
        etikett.setToolTip(tooltip)
        feld.setToolTip(tooltip)
        self.raster.addWidget(etikett, self.zeile, 0)
        self.raster.addWidget(feld, self.zeile, 1, 1, breite)
        self._beschriftungen.append(etikett)
        self.zeile += 1

    def ganz(self, widget):
        """Ein Widget unter den Feldern, über ihre ganze Breite."""
        self.raster.addWidget(widget, self.zeile, 1, 1, 2)
        self.zeile += 1

    def breite_beschriftung(self):
        return max((e.sizeHint().width() for e in self._beschriftungen), default=0)


def _radius(fraeser):
    """Der Radius des Fräsers (Werkzeugverwaltung) – 0 ohne."""
    return float(getattr(fraeser, "durchmesser", 0.0) or 0.0) / 2.0


def _zeit_text(minuten):
    """„56 min“, „2 h 44 min“ – auf ganze Minuten."""
    gesamt = max(1, int(round(minuten)))
    if gesamt < 60:
        return tr("va.zeit.min", min=gesamt)
    return tr("va.zeit.h", h=gesamt // 60, min=gesamt % 60)


class VierachsPanel:
    """Das Aufgabenfenster. FreeCAD ruft `getStandardButtons`, `modifyStandardButtons`,
    `accept` und `reject` auf."""

    offen = None  # das gerade offene Fenster – für die Oberflächen-Szenarien

    def __init__(self, dokument, wahl=None, operation=None, maschine=None):
        VierachsPanel.offen = self
        self.doc = dokument
        # Die Maschine, mit der es losgeht (Assembly oder ihr Dokument) – aus Schritt 1 des
        # Assistenten „Bearbeitung“, wenn dort eine Drehmaschine gewählt war (W-011 S3).
        self._maschine_vorwahl = maschine
        self.teil = None  # das Original, das in die Stange soll
        self.flaeche = None  # „FaceN“ der Stirnfläche
        self.vermessung = None
        self._nahe = None  # an einer runden Fläche: wo sie angeklickt wurde (V2b)
        self.umgedreht = False  # an einer runden Fläche: das andere Ende vorne („Umdrehen“)
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
        self._uhr.timeout.connect(uhren.aus_der_schleife(self._uhr, self._anwenden))
        self.seite = 1  # 1: Rohteil, 2: Was willst du machen?
        self.bibliothek = None  # die Werkzeugverwaltung – geladen, wenn Schritt 2 kommt
        self._pruefung = None  # (Assembly, reichweite.Pruefung) der gewählten Maschine
        self._fraeser = []  # die Werkzeuge in der Auswahl „Fräser“
        self._einsaetze = []  # die Einsätze in der Auswahl „Einsatz“
        self.vorschau = None  # die Bahn der Vorschau (vierachs_bahn.Bahn) oder None
        self.operation = operation  # die angelegte Operation – oder die, die man ändert
        # Ändern statt anlegen: die Operation, ihr Controller und ihre Rundachse.
        self.zu_aendern = operation
        self._tc_vorher = operation.ToolController if operation is not None else None
        self._achse_fest = achse_der_operation(operation) if operation is not None else None
        self._vorwahl = None  # beim Ändern: Kennung des Fräsers der Operation ("": keiner)
        self._vorwahl_schlichten = None  # dasselbe, wenn man „Rundum schlichten“ ändert
        self._art = SCHLICHTEN if vs.ist_schlichten(operation) else SCHRUPPEN
        if vplan.ist_plan(operation):
            self._art = PLAN
        self._vorwahl_plan = None  # beim Ändern: Kennung des Fräsers von „Plan indexiert“
        self._planfraeser = []  # die Werkzeuge in der Auswahl „Fräser“ bei Plan indexiert
        self._planeinsaetze = []
        self.vorschau_plan = None  # die grobe Bahn „Plan indexiert“ (vierachs_planbahn.Planbahn)
        self._plan_von_hand = False  # der Haken „Plan indexiert“ wurde von Hand gesetzt
        self._planfraeser_von_hand = False  # das Werkzeug bei „Plan indexiert“ von Hand gewählt
        # Neben dem Fräser ein Bohrer für die Querbohrungen (eigene Operation, P-2026-10-02-11):
        # der vorgeschlagene (werkzeuge.Werkzeug), ob der Haken von Hand gesetzt wurde, seine Bahn.
        self._planbohrer = None
        self._planbohrer_von_hand = False
        self.vorschau_planbohren = None
        self._plan_erlaubt = True  # beim Ändern: ob „Plan indexiert“ dazukommen darf
        if vent.ist_entgraten(operation):
            self._art = ENTGRATEN
        self._vorwahl_entgraten = None  # beim Ändern: Kennung des Fräsers von „Rundum entgraten“
        self._entgratfraeser = []  # die Werkzeuge in der Auswahl „Fräser“ beim Entgraten
        self._entgrateinsaetze = []
        self.vorschau_entgraten = None  # die grobe Bahn (vierachs_entgratbahn.Entgratbahn)
        self._entgraten_von_hand = False  # der Haken „Rundum entgraten“ wurde von Hand gesetzt
        self._entgraten_erlaubt = True  # beim Ändern: ob „Rundum entgraten“ dazukommen darf
        self._schlichtfraeser = []  # die Werkzeuge in der Auswahl „Fräser“ beim Schlichten
        self._schlichteinsaetze = []
        self.vorschau_schlichten = None  # die grobe Schlichtbahn (vierachs_bahn.Schlichtbahn)
        self._schlichten_vorgewaehlt = False  # der Haken „Rundum schlichten“ ist gesetzt
        self._schlichten_vorschlag = False  # … und so war der Vorschlag (ein Fräser mit Einsatz)
        self._schlichten_von_hand = False  # der Haken „Rundum schlichten“ wurde von Hand gesetzt
        self._schlichten_selbst = False  # der Assistent setzt ihn gerade selbst
        self._muster_von_hand = False  # das Muster wurde von Hand gewählt: kein Vorschlag mehr
        # Die Wendelnut des Teils (vierachs_wendel.Wendel, W-030): erkannt für welches Modell, das
        # Ergebnis und der Auftrag dazu.
        self._wendel_schluessel = None
        self._wendel = None
        self._wendel_auftrag = None
        self._schruppen_wendel_von_hand = False
        self._querachse_von_hand = False  # der Haken „mit der Querachse“ von Hand gesetzt
        self._sektoren_y_von_hand = False  # „Sektoren in Zeilen mit Y“ von Hand gesetzt
        self._y_weg_gemerkt = {}  # (Dokument, Maschine) → Weg der Querachse (y_weg)
        self._anstellen_von_hand = False  # der Haken „Kugel anstellen“ von Hand gesetzt
        self._stetig_von_hand = False  # der Haken „C dreht nicht zurück“ von Hand gesetzt
        self._querachse_schruppen_von_hand = False  # … beim Schruppen
        self._stetig_schruppen_von_hand = False  # „C dreht nicht zurück“ beim Schruppen
        self._noetig_von_hand = False  # „Folgelagen nur, wo nötig“ von Hand gesetzt
        self.gewaehlte = []  # die Flächen zum Fräsen („Face3“ …), V4 – leer: rundum
        self._farben_vorher = None  # (Klon, DiffuseColor, ShapeAppearance) vor dem Färben
        self._transaktion_offen = False  # beim Ändern: Schritt 1 hat etwas geändert
        self._stange_jetzt = None  # die Stange, wie sie zuletzt in den Job kam
        self._stange_vorher = None  # beim Ändern: wie die Stange aussah (DisplayMode, …)
        # Rückgängig-Schritte vor dem Assistenten; Job und Stange liegen nach „Anlegen“ als
        # eigener Schritt ab, auch wenn das Schruppen danach nicht geht (Abbrechen: zurück).
        self._undo_vorher = len(dokument.UndoNames)
        self._rohteil_fest = False
        self._vorschau_uhr = QtCore.QTimer()
        self._vorschau_uhr.setSingleShot(True)
        self._vorschau_uhr.setInterval(VORSCHAU_MS)
        self._vorschau_uhr.timeout.connect(
            uhren.aus_der_schleife(self._vorschau_uhr, self._vorschau_rechnen)
        )
        # Die Vorschau rechnen die Nebenrechner (P-2026-10-09-09): je Bearbeitung ein Auftrag,
        # die Nummer sagt, ob eine Antwort noch zur letzten Eingabe gehört.
        self._vorschau_nummer = 0
        self._vorschau_auftraege = {}  # Name („schruppen“, „planbohren“ …) -> Auftrag
        self._rest_auftrag = None  # der Rest für die Kugel (vierachs_vorschau.rest)
        # Vorschlichten (W-031): wo es fährt (a von, bis; None: das ganze Teil), seine Bahn, die
        # Aufträge für die Bahn und den Rest danach, und ob man den Haken selbst gesetzt hat.
        self._vorschlicht_bereich = None
        self.vorschau_vorschlichten = None
        self._vor_auftrag = None  # {Name: Auftrag} – der Wendel nach in Blöcken
        self._vor_rest_auftrag = None
        self._vor_teile = ({}, {}, [])  # Ergebnisse, Gründe, gescheiterte Blöcke
        self._vorschlichten_von_hand = False
        self._vorschlichten_vorgeschlagen = False
        self._halter_auftrag = None  # stößt der Halter an (vierachs_vorschau.halter, Frage 7)
        self._vorwaermen()
        self._vorschau_ergebnisse = {}
        self._vorschau_gruende = {}
        self.form = self._baue()
        self._rechnet = gui_rechnet.Anzeige(
            self.rechnet, self.rechnet_noch, bei_wechsel=self._knoepfe_beschriften
        )
        self._rechnet.rad(self.rad_unten)
        # Räumt FreeCAD das Fenster ohne „Abbrechen“ weg (das Dokument zu), hier aufräumen – sonst
        # riefen Beobachter und Uhren ins Leere (Manuel, 2026-10-12: „deleted object“).
        self.form.destroyed.connect(lambda *_a: self._verschwunden())
        self._beobachter = None
        if operation is not None:
            self._zum_aendern()
            return
        self._beobachter = _Beobachter(self)
        FreeCADGui.Selection.addObserver(self._beobachter)
        FreeCADGui.Selection.addSelectionGate(_NurFlaechen(self))
        if wahl is not None and wahl[1] is not None:
            self.waehle_flaeche(*wahl, nahe=klickpunkt(dokument))
        elif wahl is not None and stl_teil.aus_stl(wahl[0]):
            # Ein Körper aus einem STL: zuerst seine Standfläche anklicken – sie kommt ans Futter –
            # oder eine seiner Achsen wählen.
            from .gui_stl import teil_aus_netz

            self._stl_teil = vr.original(wahl[0])
            self.anleitung.setText(tr("va.anleitung.stl", bericht=teil_aus_netz.bericht))
            self.teilachsen.show()
        self._auffrischen()

    def _zum_aendern(self):
        """Schritt 2 mit Fräser, Einsatz und Werten der Operation; „Zurück“ führt zu Schritt 1,
        wie der Job eingerichtet ist (vierachs_rohteil.einstellung). Lässt sich das nicht
        zurückrechnen – der Job sieht nicht mehr aus, wie der Assistent ihn anlegt –, bleibt
        Schritt 1 zu. Die Bearbeitung bleibt angehakt – weg geht sie mit Entf im Baum. Beim
        Schruppen lässt sich „Rundum schlichten“ dazunehmen, solange der Job keins hat; beim
        Schlichten ist das Schruppen ausgeblendet."""
        self.job = job_von(self.zu_aendern)
        self.mit_schruppen.setEnabled(False)
        self.mit_schlichten.setEnabled(False)
        self.mit_plan.setEnabled(False)
        self.mit_entgraten.setEnabled(False)
        schruppen_teile = (
            self.mit_schruppen,
            self.erklaerung_schruppen,
            self.schruppfelder,
            self.ergebnis,
            self.hinweis_rund,
            self.lage_schruppen,
        )
        schlichten_teile = (
            self.mit_schlichten,
            self.erklaerung_schlichten,
            self.schlichtfelder,
            self.ergebnis_schlichten,
            self.lage_schlichten,
        )
        plan_teile = (
            self.mit_plan,
            self.erklaerung_plan,
            self.plan_grund,
            self.planfelder,
            self.ergebnis_plan,
            self.lage_plan,
        )
        entgraten_teile = (
            self.mit_entgraten,
            self.erklaerung_entgraten,
            self.entgrat_grund,
            self.entgratfelder,
            self.ergebnis_entgraten,
            self.lage_entgraten,
        )
        if self._art == SCHLICHTEN:
            self.mit_schruppen.setChecked(False)
            self.mit_schlichten.setChecked(True)
            self.mit_plan.setChecked(False)
            self.mit_entgraten.setChecked(False)
            self._plan_erlaubt = self._entgraten_erlaubt = False
            for teil in schruppen_teile + plan_teile + entgraten_teile:
                teil.hide()
            erklaerung = self.erklaerung_schlichten
        elif self._art == PLAN:
            self.mit_schruppen.setChecked(False)
            self.mit_schlichten.setChecked(False)
            self.mit_plan.setChecked(True)
            self.mit_entgraten.setChecked(False)
            self._entgraten_erlaubt = False
            for teil in schruppen_teile + schlichten_teile + entgraten_teile + (self.plan_grund,):
                teil.hide()
            erklaerung = self.erklaerung_plan
        elif self._art == ENTGRATEN:
            self.mit_schruppen.setChecked(False)
            self.mit_schlichten.setChecked(False)
            self.mit_plan.setChecked(False)
            self.mit_entgraten.setChecked(True)
            self._plan_erlaubt = False
            for teil in schruppen_teile + schlichten_teile + plan_teile + (self.entgrat_grund,):
                teil.hide()
            erklaerung = self.erklaerung_entgraten
        else:
            schon = [o for o in js.operationen(self.job) if vs.ist_schlichten(o)]
            self.mit_schlichten.setChecked(False)
            self.mit_schlichten.setEnabled(not schon)
            self.erklaerung_schlichten.setText(
                tr("va.schlichten.schon", name=schon[0].Label)
                if schon
                else tr("va.schlichten.dazu")
            )
            schon_plan = [o for o in js.operationen(self.job) if vplan.ist_plan(o)]
            self.mit_plan.setChecked(False)
            self._plan_erlaubt = not schon_plan
            self.erklaerung_plan.setText(
                tr("va.plan.schon", name=schon_plan[0].Label) if schon_plan else tr("va.plan.dazu")
            )
            schon_entgraten = [o for o in js.operationen(self.job) if vent.ist_entgraten(o)]
            self.mit_entgraten.setChecked(False)
            self._entgraten_erlaubt = not schon_entgraten
            self.erklaerung_entgraten.setText(
                tr("va.entgraten.schon", name=schon_entgraten[0].Label)
                if schon_entgraten
                else tr("va.entgraten.dazu")
            )
            erklaerung = self.erklaerung_schruppen
        text = tr("va.aendern.text")
        einstellung = vr.einstellung(self.job) if self.job is not None else None
        if einstellung is not None and gleich(einstellung.laengs, self._achse_fest.laengs):
            self._schritt1_aus(einstellung)
            text += " " + tr("va.aendern.zurueck")
        else:
            self.knopf_zurueck.hide()
            text += " " + tr("va.aendern.rohteil_fest")
        if self._beobachter is None:  # Flächen wählen (V4) geht auch, wenn Schritt 1 fest ist
            self._beobachter = _Beobachter(self)
            FreeCADGui.Selection.addObserver(self._beobachter)
            FreeCADGui.Selection.addSelectionGate(_NurFlaechen(self))
        erklaerung.setText(text)
        self._auffrischen()
        self.zeige_seite(2)
        self._werte_der_operation()
        fraeser, vorwahl = {
            SCHLICHTEN: (self.schlichtfraeser(), self._vorwahl_schlichten),
            PLAN: (self.planfraeser(), self._vorwahl_plan),
            ENTGRATEN: (self.entgratfraeser(), self._vorwahl_entgraten),
        }.get(self._art, (self.fraeser(), self._vorwahl))
        if self._tc_vorher is not None and (fraeser is None or fraeser.kennung != vorwahl):
            self.hinweis_aendern.setText(
                tr("va.aendern.werkzeug_fehlt", controller=self._tc_vorher.Label)
            )
            self.hinweis_aendern.show()

    def _schritt1_aus(self, einstellung):
        """Schritt 1, wie der Job eingerichtet ist: Teil, Stirnfläche, Mitte, Drehlage, Stange
        und die Rundachse der Operation – jeder Wert steht im Feld. Ab jetzt gilt die Liste
        „Rundachse“, und ein Klick auf eine andere Fläche des Teils legt es neu."""
        self.teil, self.flaeche = einstellung.teil, einstellung.flaeche
        self.vermessung, self.mitte = einstellung.vermessung, einstellung.mitte
        self._nahe, self.umgedreht = None, einstellung.umgedreht
        self.teilachsen.setVisible(stl_teil.aus_stl(self.teil))
        stange, laenge = einstellung.stange, einheiten.LAENGE
        self._fuellt = True
        try:
            self._achse_waehlen(self._achse_fest)
            self._achse_fest = None
            self.feld_stange.setText(groesse_zeigen(stange.durchmesser, laenge))
            self.feld_drehlage.setText(zahl_zeigen(einstellung.drehlage))  # 0: leer
            for feld, wert in (
                ("planaufmass", stange.planaufmass),
                ("abstechbreite", stange.abstechbreite),
                ("spannlaenge", stange.spannlaenge),
            ):
                self.felder_laenge[feld].setText(groesse_zeigen(wert, laenge) or "0")
        finally:
            self._fuellt = False
        self.lage = vr.lage(
            self.vermessung, self.achse(), self.mitte, einstellung.drehlage, stange.durchmesser
        )
        self._stange_jetzt = stange
        if self._beobachter is None:  # sonst hinge der erste beim Schließen weiter an FreeCAD
            self._beobachter = _Beobachter(self)
            FreeCADGui.Selection.addObserver(self._beobachter)
            FreeCADGui.Selection.addSelectionGate(_NurFlaechen(self))

    def _achse_waehlen(self, achse):
        """Beim Ändern: Maschine und Rundachse, mit denen die Operation rechnet – Buchstabe,
        Richtung, Drehsinn und Querachse gleich. Findet sich keine (die Maschine ist nicht
        offen), gilt „ohne Maschine“ mit der Achse der Operation als eigenem Eintrag."""
        ohne = [va.zugewiesen(b) for b in _achstexte()]
        for i, eintrag in enumerate(self._maschinen):
            if isinstance(eintrag, str):
                continue
            kandidaten = eintrag.achsen if eintrag is not None else ohne
            j = next((j for j, k in enumerate(kandidaten) if _gleiche_achse(k, achse)), -1)
            if j >= 0:
                self._waehle_maschine_ohne_signal(i)
                self.wahl_achse.setCurrentIndex(j)
                return
        self._waehle_maschine_ohne_signal(len(self._maschinen) - 1)
        self._achsen.append(achse)
        self.wahl_achse.addItem(achstext(achse))
        self.wahl_achse.setCurrentIndex(len(self._achsen) - 1)
        self.wahl_achse.setEnabled(True)

    def _werte_der_operation(self):
        """Die Werte der Operation in die Felder – leer, wo sie dem Vorschlag gleichen: dann
        folgen sie ihm wie beim Anlegen. Der Überlauf ist leer, wenn er Radius + 0,5 mm ihres
        Fräsers ist."""
        op = self.zu_aendern
        if self._art == SCHLICHTEN:
            paare = [
                ("schrittweite", op.Schrittweite),
                ("aufmass_schlichten", op.Aufmass),
            ]
            self._muster_setzen(vs.muster_der_operation(op), von_hand=True)
            self.linien_nur_gleichlauf.setChecked(bool(getattr(op, "NurGleichlauf", False)))
            self._querachse_von_hand = True
            self._querachse_vorschlagen()
            self.schlichten_querachse.setChecked(
                self.schlichten_querachse.isEnabled() and bool(getattr(op, "Querachse", False))
            )
            self._anstellen_von_hand = True
            self._anstellen_vorschlagen()
            self.schlichten_anstellen.setChecked(
                self.schlichten_anstellen.isEnabled() and bool(getattr(op, "Anstellen", True))
            )
            self._stetig_von_hand = True
            self._stetig_vorschlagen()
            self.schlichten_stetig.setChecked(
                self.schlichten_stetig.isEnabled() and bool(getattr(op, "Stetig", True))
            )
        elif self._art == PLAN:
            paare = [
                ("zustellung_plan", op.Zustellung),
                ("zeilenabstand", op.Zeilenabstand),
                ("aufmass_plan", op.Aufmass),
            ]
            self.plan_nur_gleichlauf.setChecked(bool(getattr(op, "NurGleichlauf", False)))
            self.wahl_plan_weg.setCurrentIndex(
                max(0, self.wahl_plan_weg.findData(vplan.weg_der_operation(op)))
            )
            self.plan_schaft.setChecked(bool(getattr(op, "Schaft", False)))
        elif self._art == ENTGRATEN:
            paare = [("breite", op.Breite)]
        else:
            paare = [
                ("zustellung", op.Zustellung),
                ("steigung", op.VorschubJeUmdrehung),
                ("aufmass", op.Aufmass),
            ]
            self.schruppen_nur_gleichlauf.setChecked(bool(getattr(op, "NurGleichlauf", False)))
            self._querachse_schruppen_von_hand = True
            self._querachse_vorschlagen()
            self.schruppen_querachse.setChecked(
                self.schruppen_querachse.isEnabled() and bool(getattr(op, "Querachse", False))
            )
            self._stetig_schruppen_von_hand = True
            self._stetig_schruppen_vorschlagen()
            self.schruppen_stetig.setChecked(
                self.schruppen_stetig.isEnabled() and bool(getattr(op, "Stetig", True))
            )
            self._noetig_von_hand = True
            self._stetig_schruppen_vorschlagen()
            self.schruppen_noetig.setChecked(
                self.schruppen_noetig.isEnabled() and bool(getattr(op, "NurNoetig", True))
            )
            self._sektoren_y_von_hand = True
            self._sektoren_y_vorschlagen()
            self.schruppen_sektoren_y.setChecked(
                self.schruppen_sektoren_y.isEnabled() and bool(getattr(op, "SektorenY", False))
            )
            self.schruppen_sektor_wellen.setChecked(bool(getattr(op, "SektorWellen", True)))
            self.schruppen_sektor_wellen.setEnabled(self.sektoren_y())
            self._schruppen_wendel_von_hand = True
            self.schruppen_wendel.setVisible(bool(getattr(op, "Wendel", False)))
            self.schruppen_wendel.setChecked(bool(getattr(op, "Wendel", False)))
        paare += [("abstand_futter", op.AbstandFutter), ("sicherheit", op.Sicherheitsabstand)]
        # Die Auflösung: nur ein gesetzter Wert (0 ist der Vorschlag und bleibt grau).
        if self._art == SCHLICHTEN:
            grad = au.wert_rundum(op, 0.0)
            if grad > 0:
                self._feld("aufloesung_schlichten").setText(zahl_zeigen(grad))
        elif self._art == SCHRUPPEN:
            laengs, grad = au.wert(op, 0.0), au.wert_rundum(op, 0.0)
            if laengs > 0:
                self._feld("aufloesung").setText(groesse_zeigen(laengs, einheiten.LAENGE))
            if grad > 0:
                self._feld("aufloesung_rundum").setText(zahl_zeigen(grad))
        elif self._art in (PLAN, ENTGRATEN):
            mm = au.wert(op, 0.0)
            if mm > 0:
                feld = "aufloesung_plan" if self._art == PLAN else "aufloesung_entgraten"
                self._feld(feld).setText(groesse_zeigen(mm, einheiten.LAENGE))
        self.gewaehlte = list(vo.flaechen(op))
        self._flaechen_zeigen()
        for feld, wert in paare:
            wert = float(wert)
            if abs(wert - self._vorschlag(feld)) > 1e-6:
                text = groesse_zeigen(wert, einheiten.LAENGE) or "0"  # Aufmaß 0 ist eine Zahl
                self._feld(feld).setText(text)
        ueberlauf = float(op.Ueberlauf)
        if abs(ueberlauf - vb.ueberlauf_vorschlag(0.0, vr.abstechbreite(self.job))) > 1e-6:
            self._feld("ueberlauf").setText(groesse_zeigen(ueberlauf, einheiten.LAENGE) or "0")

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
        with contextlib.suppress(Exception):  # links neben den Knöpfen: das Rad (gui_rechnet)
            knoepfe.layout().insertWidget(0, self._rechnet.rad())
        self._knoepfe_beschriften()

    def _knoepfe_beschriften(self):
        """OK oben und der Knopf unten rechts sagen dasselbe: in Schritt 1 „Weiter“, in Schritt 2
        „Anlegen“ oder „Übernehmen“ – und sind zusammen gesperrt oder frei; gesperrt auch,
        solange gerechnet wird (gui_rechnet)."""
        ok = self.knopf_anlegen()
        if self.seite == 1:
            text, tooltip = tr("va.weiter"), tr("va.weiter.tooltip")
            frei = self.job is not None
            unten = getattr(self, "knopf_weiter", None)
        else:
            if self.zu_aendern is not None:
                text, tooltip = tr("va.uebernehmen"), tr("va.uebernehmen.tooltip")
            else:
                text, tooltip = tr("va.anlegen"), tr("va.anlegen.tooltip")
            frei = self.job is not None and self._kann_anlegen()
            unten = getattr(self, "knopf_fertig", None)
        anzeige = getattr(self, "_rechnet", None)
        if anzeige is not None and anzeige.an:
            frei = False
        for k in (ok, unten):
            if k is None:
                continue
            k.setText(text)
            k.setToolTip(tooltip)
            k.setEnabled(frei)

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
        if self.zu_aendern is not None:
            return self._uebernehmen()
        if self.seite == 1:
            self.zeige_seite(2)
            return False  # „Weiter“: das Fenster bleibt offen
        schruppen, schlichten = self._gewaehlt()
        bearbeitung = schruppen or schlichten or self.plan_an() or self.entgraten_an()
        if bearbeitung and not self._bearbeitung_pruefen():
            return False  # der Grund steht rot im Fenster
        # Job und Stange: ein Schritt Rückgängig. Die Bearbeitungen kommen in einem eigenen
        # (_bearbeitungen_anlegen) – in einen gemeinsamen lässt FreeCAD es nicht (_im_befehl).
        self._anzeige_wie_in_cam()
        self._maschine_merken()
        self.doc.commitTransaction()
        self._rohteil_fest = True
        if bearbeitung and not self._bearbeitungen_anlegen():
            self._stange_anzeigen(*STANGE_ANZEIGE, waehlbar=False)
            self.doc.openTransaction(tr("va.titel"))  # für weitere Eingaben
            return False
        self._vor_dem_schliessen()
        self._vorschlaege_merken()
        self.doc.commitTransaction()
        dialog_schliessen(self.doc)
        with uhren.still():  # Qt baut das Fenster noch ab
            self.doc.recompute()
        return True

    def _uebernehmen(self):
        """Beim Ändern: in Schritt 1 „Weiter“; in Schritt 2 „Übernehmen“ – eine geänderte
        Stange als eigener Schritt Rückgängig (wie beim Anlegen), dann die Operation (und ein
        dazugenommenes Schlichten), und schließen. Geht es nicht, bleibt das Fenster offen (der
        Grund steht rot darin)."""
        if self.seite == 1:
            self.zeige_seite(2)
            return False
        if not self._bearbeitung_pruefen():
            return False
        if self._transaktion_offen:
            self.doc.commitTransaction()
            self._transaktion_offen = False
            self._rohteil_fest = True
        if not self._aendern():
            return False
        self._vor_dem_schliessen()
        self._stange_zurueck()
        self._fraeser_merken()
        self.doc.commitTransaction()
        dialog_schliessen(self.doc)
        with uhren.still():  # Qt baut das Fenster noch ab
            self.doc.recompute()
        return True

    def reject(self):
        self._vor_dem_schliessen()
        if self.zu_aendern is None:
            self._sichtbarkeit_zurueck()
            self.doc.abortTransaction()
        elif self._transaktion_offen:  # beim Ändern: was Schritt 1 geändert hat
            self.doc.abortTransaction()
            self._transaktion_offen = False
        if self._rohteil_fest:  # Job bzw. Stange liegen schon als Schritt ab
            while len(self.doc.UndoNames) > self._undo_vorher:
                self.doc.undo()
        self._stange_zurueck()
        dialog_schliessen(self.doc)
        with uhren.still():  # Qt baut das Fenster noch ab
            self.doc.recompute()
        return True

    def rechnet_noch(self):
        """Rechnet noch etwas für das Fenster – die Uhr nach einer Eingabe, eine Vorschau oder
        der Rest für die Kugel auf den Nebenrechnern?"""
        if self.geschlossen:
            return False
        rest = self._rest_auftrag
        return (
            self._vorschau_uhr.isActive()
            or any(not a.erledigt for a in self._vorschau_auftraege.values())
            or (rest is not None and not rest.erledigt)
        )

    def _verschwunden(self):
        """Das Fenster ist weg, ohne dass es geschlossen wurde: aufräumen wie beim Schließen."""
        if not self.geschlossen:
            with contextlib.suppress(Exception):
                self._vor_dem_schliessen()
            self.geschlossen = True

    def _vor_dem_schliessen(self):
        """Bewegung anhalten, Auswahl-Hilfen abmelden."""
        VierachsPanel.offen = None
        self.geschlossen = True
        self._rechnet.ende()
        from .gui_reichweite import job_merken

        job_merken(self.job)  # Prüfen, Bestückung und Programm nehmen ihn ohne Auswahl
        self._uhr.stop()
        self._vorschau_uhr.stop()
        self._vorschau_abbrechen()
        if self.einfahren:
            self.einfahren.stopp()
        self._farben_zurueck()
        if self._beobachter is not None:
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
        self.rechnet = QtGui.QLabel()  # gui_rechnet: dreht sich, solange es rechnet
        aussen.addWidget(self.rechnet)
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
        # Ein Teil aus einem STL: statt einer Fläche eine seiner Achsen längs der Stange (Manuel,
        # 2026-10-11: „X, Y oder Z zur Wahl – beides ja“).
        self.teilachsen = QtGui.QWidget()
        reihe = QtGui.QHBoxLayout(self.teilachsen)
        reihe.setContentsMargins(0, 0, 0, 0)
        reihe.addWidget(QtGui.QLabel(tr("va.teilachse")))
        self.knoepfe_teilachse = {}
        for achse in vr.TEILACHSEN:
            taste = QtGui.QPushButton(achse)
            taste.setToolTip(tr("va.teilachse.tooltip", achse=achse))
            taste.setAutoDefault(False)
            taste.clicked.connect(lambda _an=False, a=achse: self.waehle_teilachse(a))
            reihe.addWidget(taste)
            self.knoepfe_teilachse[achse] = taste
        reihe.addStretch(1)
        self.teilachsen.hide()
        aufbau.addWidget(self.teilachsen)

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
        # An einer runden Fläche (V2b): das andere Ende nach vorne.
        self.knopf_umdrehen = QtGui.QPushButton(tr("va.umdrehen"))
        self.knopf_umdrehen.setToolTip(tr("va.umdrehen.tooltip"))
        self.knopf_umdrehen.setAutoDefault(False)
        self.knopf_umdrehen.clicked.connect(lambda: self.umdrehen())
        self.knopf_umdrehen.hide()
        raster.addWidget(self.knopf_umdrehen, zeile, 1, QtCore.Qt.AlignLeft)
        zeile += 1

        # Maschine zuerst (Manuel, 2026-09-29: „vll sollte man als erstes die abfrage machen
        # ‚hey was hast du für ne maschine‘“): Sie gibt die Rundachse vor (V2a, V3f).
        self.wahl_maschine = QtGui.QComboBox()
        self.wahl_maschine.setToolTip(tr("va.maschine.tooltip"))
        raster.addWidget(beschriftung(tr("va.maschine"), tr("va.maschine.tooltip")), zeile, 0)
        raster.addWidget(self.wahl_maschine, zeile, 1, 1, 2)
        zeile += 1
        self.maschine_text = self._grau()
        self.maschine_text.setWordWrap(True)
        raster.addWidget(self.maschine_text, zeile, 1, 1, 2)
        zeile += 1
        self.wahl_achse = QtGui.QComboBox()
        self.wahl_achse.setToolTip(tr("va.rundachse.tooltip"))
        raster.addWidget(beschriftung(tr("va.rundachse"), tr("va.rundachse.tooltip")), zeile, 0)
        raster.addWidget(self.wahl_achse, zeile, 1, 1, 2)
        zeile += 1
        self._maschinen_fuellen(vorwahl=self._maschine_vorwahl)
        self.wahl_maschine.currentIndexChanged.connect(
            lambda _i: None if self._fuellt else self._maschine_gewaehlt()
        )
        self.wahl_achse.currentIndexChanged.connect(
            lambda _i: None if self._fuellt else self.waehle_rundachse()
        )

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
            # Eine gemerkte 0 grau als „0“ – leer sah es aus, als fehle der Wert (Manuel,
            # 2026-09-30: „in planaufmass steht nix drinnen?“).
            eingabe.setPlaceholderText(groesse_zeigen(self._gemerkt(feld), einheiten.LAENGE) or "0")
            self.felder_laenge[feld] = eingabe
            raster.addWidget(beschriftung(text, tooltip), zeile, 0)
            raster.addWidget(mit_einheit(eingabe, einheiten.einheit(einheiten.LAENGE)), zeile, 1)
            zeile += 1
        self.laenge_text = self._grau()
        raster.addWidget(self.laenge_text, zeile - 1, 2)
        aufbau.addWidget(self.felder)

        self.urteil = QtGui.QLabel()
        self.urteil.setWordWrap(True)
        self.urteil.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        aufbau.addWidget(self.urteil)
        # Unten rechts „Weiter“ wie im Assistenten „Bearbeitung“ (Manuel, 2026-10-03: „wenn ein
        # Zurück steht, bitte auch ein Anlegen unten rechts, wo das Weiter stand“).
        self.knopf_weiter = knopf(tr("va.weiter"), tr("va.weiter.tooltip"), self.accept)
        zeile = QtGui.QHBoxLayout()
        zeile.addStretch()
        zeile.addWidget(self.knopf_weiter)
        aufbau.addLayout(zeile)
        aufbau.addStretch()
        return ruhiges_mausrad(form)

    def _baue_bearbeitung(self):
        """Schritt 2: Was willst du machen? – der Werkstoff für beide, „Rundum schruppen“,
        „Rundum schlichten“ (V5d) und die Abstände für beide."""
        seite = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(seite)
        aufbau.setContentsMargins(0, 0, 0, 0)

        def zahlenfeld(felder, name, text, tooltip, reihen, einheit=None):
            eingabe = QtGui.QLineEdit()
            eingabe.setValidator(Zahlenpruefer(eingabe))
            eingabe.textChanged.connect(lambda _text: self._vorschau_starten())
            felder[name] = eingabe
            reihen.reihe(
                text, tooltip, mit_einheit(eingabe, einheit or einheiten.einheit(einheiten.LAENGE))
            )

        def aufloesungsfelder(felder, reihen, laengs, rundum):
            """Die Auflösung (T-009): längs in mm (`laengs`, None: keins) und rundum in Grad
            (`rundum`) – leer gilt der Vorschlag, der grau im Feld steht."""
            if laengs is not None:
                zahlenfeld(
                    felder,
                    "aufloesung",
                    tr("va.aufloesung"),
                    tr("va.aufloesung.tooltip", vorschlag=groesse_zeigen(laengs, einheiten.LAENGE)),
                    reihen,
                )
                felder["aufloesung"].setPlaceholderText(groesse_zeigen(laengs, einheiten.LAENGE))
            name = "aufloesung_rundum" if laengs is not None else "aufloesung_schlichten"
            zahlenfeld(
                felder,
                name,
                tr("va.aufloesung_rundum"),
                tr("va.aufloesung_rundum.tooltip", vorschlag=zahl_zeigen(rundum)),
                reihen,
                "°",
            )
            felder[name].setPlaceholderText(zahl_zeigen(rundum))

        def haken(text, tooltip, umgeschaltet, an=False):
            kasten = QtGui.QCheckBox(text)
            # Vor dem Verbinden: Die Felder, die `umgeschaltet` schaltet, gibt es noch nicht.
            kasten.setChecked(an)
            kasten.setToolTip(tooltip)
            schrift = kasten.font()
            schrift.setBold(True)
            kasten.setFont(schrift)
            kasten.toggled.connect(umgeschaltet)
            aufbau.addWidget(kasten)
            return kasten

        def grau(text=""):
            etikett = self._grau()
            etikett.setText(text)
            etikett.setWordWrap(True)
            aufbau.addWidget(etikett)
            return etikett

        def gelb():
            """Ein Satz in Gelb, bis er etwas sagt ausgeblendet (_lage_zeigen) – mit dem
            Verweis „T3 öffnen …“ zum Werkzeug (D-41)."""
            from .gui_kollision import GELB

            etikett = QtGui.QLabel()
            etikett.setWordWrap(True)
            etikett.setTextFormat(QtCore.Qt.RichText)
            etikett.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse
            )
            etikett.setStyleSheet(f"color: {GELB};")
            etikett.linkActivated.connect(self._werkzeug_oeffnen)
            etikett.hide()
            aufbau.addWidget(etikett)
            return etikett

        # Werkstoff und Werkzeugverwaltung gelten für beide Bearbeitungen.
        oben = _Reihen()
        self.wahl_werkstoff = QtGui.QComboBox()
        self.wahl_werkstoff.currentIndexChanged.connect(lambda _i: self._werkstoff_gewaehlt())
        oben.reihe(tr("va.werkstoff"), tr("va.werkstoff.tooltip"), self.wahl_werkstoff)
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
        oben.ganz(zeile)
        aufbau.addWidget(oben.widget)

        # --- Flächen (V4) ---
        self.flaechen_titel = QtGui.QLabel(tr("va.flaechen"))
        self.flaechen_titel.setToolTip(tr("va.flaechen.tooltip"))
        schrift = self.flaechen_titel.font()
        schrift.setBold(True)
        self.flaechen_titel.setFont(schrift)
        aufbau.addWidget(self.flaechen_titel)
        self.flaechen_liste = QtGui.QListWidget()
        self.flaechen_liste.setToolTip(tr("va.flaechen.liste.tooltip"))
        self.flaechen_liste.itemDoubleClicked.connect(
            lambda eintrag: self.flaeche_umschalten(eintrag.data(QtCore.Qt.UserRole))
        )
        self.flaechen_liste.hide()  # erst, wenn eine Fläche gewählt ist
        aufbau.addWidget(self.flaechen_liste)
        self.flaechen_text = grau(tr("va.flaechen.rundum"))
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        self.knopf_alle_flaechen = knopf(
            tr("va.flaechen.alle_knopf"),
            tr("va.flaechen.alle_knopf.tooltip"),
            self.alle_mantelflaechen,
        )
        self.knopf_flaechen_leeren = knopf(
            tr("va.flaechen.leeren"), tr("va.flaechen.leeren.tooltip"), self.flaechen_leeren
        )
        knoepfe.addWidget(self.knopf_alle_flaechen)
        knoepfe.addWidget(self.knopf_flaechen_leeren)
        knoepfe.addStretch()
        aufbau.addWidget(zeile)

        # --- Rundum schruppen ---
        self.mit_schruppen = haken(
            tr("va.schruppen"), tr("va.schruppen.tooltip"), self._schruppen_umgeschaltet, an=True
        )
        self.erklaerung_schruppen = grau(tr("va.schruppen.text"))
        self.hinweis_aendern = QtGui.QLabel()  # beim Ändern: der Fräser fehlt
        self.hinweis_aendern.setWordWrap(True)
        self.hinweis_aendern.setStyleSheet(f"color: {ROT};")
        self.hinweis_aendern.hide()
        aufbau.addWidget(self.hinweis_aendern)
        schruppen = _Reihen()
        self.wahl_fraeser = QtGui.QComboBox()
        self.wahl_fraeser.currentIndexChanged.connect(lambda _i: self._fraeser_gewaehlt())
        schruppen.reihe(tr("va.fraeser"), tr("va.fraeser.tooltip"), self.wahl_fraeser)
        self.wahl_einsatz = QtGui.QComboBox()
        self.wahl_einsatz.currentIndexChanged.connect(lambda _i: self._einsatz_gewaehlt())
        schruppen.reihe(tr("va.einsatz"), tr("va.einsatz.tooltip"), self.wahl_einsatz)
        self.schnittwerte = self._grau()
        schruppen.ganz(self.schnittwerte)
        self.felder_schruppen = {}
        for feld, text, tooltip in (
            ("zustellung", tr("va.zustellung"), tr("va.zustellung.tooltip")),
            ("steigung", tr("va.steigung"), tr("va.steigung.tooltip")),
            ("aufmass", tr("va.aufmass"), tr("va.aufmass.tooltip")),
        ):
            zahlenfeld(self.felder_schruppen, feld, text, tooltip, schruppen)
        aufloesungsfelder(self.felder_schruppen, schruppen, vh.SCHRITT_A, vh.SCHRITT_PHI)
        # Mit gewählten Flächen die Zeilen nur im Gleichlauf (P-2026-10-02-26).
        self.schruppen_nur_gleichlauf = QtGui.QCheckBox(tr("ba.nur_gleichlauf"))
        self.schruppen_nur_gleichlauf.setToolTip(tr("va.schruppen.nur_gleichlauf.tooltip"))
        self.schruppen_nur_gleichlauf.toggled.connect(lambda _an: self._vorschau_starten())
        schruppen.ganz(self.schruppen_nur_gleichlauf)
        # Schruppen mit der Querachse (V5e, P-2026-10-03-23) – wie beim Schlichten.
        self.schruppen_querachse = QtGui.QCheckBox(tr("va.querachse"))
        self.schruppen_querachse.setToolTip(tr("va.querachse.schruppen.tooltip"))
        self.schruppen_querachse.toggled.connect(
            lambda _an: self._querachse_schruppen_umgeschaltet()
        )
        schruppen.ganz(self.schruppen_querachse)
        self.querachse_grund_schruppen = self._grau()
        self.querachse_grund_schruppen.setWordWrap(True)
        schruppen.ganz(self.querachse_grund_schruppen)
        # C dreht dabei nicht zurück (Manuel, 2026-10-11, Frage 11: „als option anbieten … wens
        # ruhiger wird ists gut“): frei mit der Querachse, dann angehakt.
        self.schruppen_stetig = QtGui.QCheckBox(tr("va.stetig"))
        self.schruppen_stetig.setToolTip(tr("va.stetig.schruppen.tooltip"))
        self.schruppen_stetig.toggled.connect(lambda _an: self._stetig_schruppen_umgeschaltet())
        schruppen.ganz(self.schruppen_stetig)
        # Folgelagen nur, wo die davor nicht bis auf die Fläche kam (P-2026-10-11-57/58) – rundum
        # frei, dann angehakt.
        self.schruppen_noetig = QtGui.QCheckBox(tr("va.nur_noetig"))
        self.schruppen_noetig.setToolTip(tr("va.nur_noetig.tooltip"))
        self.schruppen_noetig.toggled.connect(lambda _an: self._noetig_umgeschaltet())
        schruppen.ganz(self.schruppen_noetig)
        # Steht nur noch in Sektoren etwas: Zeilen dort mit Y bei stehender Rundachse (W-026;
        # Manuel, 2026-10-17: „man [kann] die c achse sperren … nur beim schruppen“) – mit der
        # Querachse und „nur nötig“ frei, dann angehakt.
        self.schruppen_sektoren_y = QtGui.QCheckBox(tr("va.sektoren_y"))
        self.schruppen_sektoren_y.setToolTip(tr("va.sektoren_y.tooltip"))
        self.schruppen_sektoren_y.toggled.connect(lambda _an: self._sektoren_y_umgeschaltet())
        schruppen.ganz(self.schruppen_sektoren_y)
        # Schlitze darin als offene Nut in Wellen (Manuel, 2026-10-18: „Wellen, als Haken
        # vorbelegt“) – mit den Sektoren frei, angehakt.
        self.schruppen_sektor_wellen = QtGui.QCheckBox(tr("va.sektor_wellen"))
        self.schruppen_sektor_wellen.setToolTip(tr("va.sektor_wellen.tooltip"))
        self.schruppen_sektor_wellen.setChecked(True)
        self.schruppen_sektor_wellen.toggled.connect(lambda _an: self._sektor_wellen_umgeschaltet())
        schruppen.ganz(self.schruppen_sektor_wellen)
        # Der Wendelnut nach (W-030; Manuel: „Schruppen, Vorschlichten und Schlichten der Nut
        # nach“ – „Ja, vorgewählt bei Wendelnut“): zu sehen, sobald eine erkannt ist.
        self.schruppen_wendel = QtGui.QCheckBox(tr("va.schruppen_wendel"))
        self.schruppen_wendel.setToolTip(tr("va.schruppen_wendel.tooltip"))
        self.schruppen_wendel.toggled.connect(lambda _an: self._schruppen_wendel_umgeschaltet())
        self.schruppen_wendel.hide()
        schruppen.ganz(self.schruppen_wendel)
        self.schruppfelder = schruppen.widget
        aufbau.addWidget(self.schruppfelder)
        self.ergebnis = grau()
        self.halter_schruppen = gelb()  # Halter oder Schaft stoßen ans Teil (Frage 7)
        self.hinweis_rund = grau()  # Kugel- und Torusfräser: wie ein Schaftfräser
        self.lage_schruppen = gelb()  # der Fräser säße auf der Maschine nicht radial

        # --- Rundum schlichten (V5d) ---
        self.mit_schlichten = haken(
            tr("va.schlichten"), tr("va.schlichten.tooltip"), self._schlichten_umgeschaltet
        )
        self.erklaerung_schlichten = grau(tr("va.schlichten.text"))
        schlichten = _Reihen()
        # Schruppen – messen – schlichten (Manuel, 2026-10-17: „ich will schruppen .. messen ..
        # schlichten“): ein Messstopp zwischen beiden, wie „Schlichten danach“ in „Bearbeitung“.
        # Frei, wenn beide angelegt werden; aus vorbelegt – er hält jedes Programm an.
        self.schlichten_messstopp = QtGui.QCheckBox(tr("va.messstopp"))
        self.schlichten_messstopp.setToolTip(tr("va.messstopp.tooltip"))
        schlichten.ganz(self.schlichten_messstopp)
        self.wahl_schlichtfraeser = QtGui.QComboBox()
        self.wahl_schlichtfraeser.currentIndexChanged.connect(
            lambda _i: self._schlichtfraeser_gewaehlt()
        )
        schlichten.reihe(
            tr("va.fraeser"), tr("va.schlichtfraeser.tooltip"), self.wahl_schlichtfraeser
        )
        self.wahl_schlichteinsatz = QtGui.QComboBox()
        self.wahl_schlichteinsatz.currentIndexChanged.connect(
            lambda _i: self._schlichteinsatz_gewaehlt()
        )
        schlichten.reihe(
            tr("va.einsatz"), tr("va.schlichteinsatz.tooltip"), self.wahl_schlichteinsatz
        )
        self.schnittwerte_schlichten = self._grau()
        schlichten.ganz(self.schnittwerte_schlichten)
        self.felder_schlichten = {}
        # Die Kammhöhe, aus der die Schrittweite kommt (P-2026-10-11-40; Manuel, Frage 6).
        zahlenfeld(
            self.felder_schlichten,
            "kammhoehe_ziel",
            tr("va.kammhoehe_ziel"),
            tr("va.kammhoehe_ziel.tooltip"),
            schlichten,
        )
        self.felder_schlichten["kammhoehe_ziel"].textChanged.connect(
            lambda _text: self._schrittweite_vorschlag_zeigen()
        )
        zahlenfeld(
            self.felder_schlichten,
            "schrittweite",
            tr("va.schrittweite"),
            tr("va.schrittweite.tooltip"),
            schlichten,
        )
        # Die Kammhöhe aus der Schrittweite gleich beim Tippen, nicht erst mit der Vorschau.
        self.felder_schlichten["schrittweite"].textChanged.connect(
            lambda _text: self._kammhoehe_zeigen()
        )
        self.kammhoehe = self._grau()
        self.kammhoehe.hide()  # erst, wenn es eine Kammhöhe gibt
        schlichten.ganz(self.kammhoehe)
        from .gui_kollision import GELB

        self.kammhoehe_ae = self._grau()  # gelb: Schrittweite über „ae max“ des Einsatzes
        self.kammhoehe_ae.setWordWrap(True)
        self.kammhoehe_ae.setStyleSheet(f"color: {GELB};")
        self.kammhoehe_ae.hide()
        schlichten.ganz(self.kammhoehe_ae)
        aufloesungsfelder(self.felder_schlichten, schlichten, None, vb.SCHRITT_PHI_SCHLICHTEN)
        zahlenfeld(
            self.felder_schlichten,
            "aufmass_schlichten",
            tr("va.aufmass_schlichten"),
            tr("va.aufmass_schlichten.tooltip"),
            schlichten,
        )
        # Das Muster (V4c): Spirale oder Linien längs – vorgeschlagen nach den Flächen, der
        # Grund steht grau darunter (W-006 E5: Vorschlag mit Grund, änderbar).
        self.wahl_muster = QtGui.QComboBox()
        for muster, text in (
            (vb.SPIRALE, tr("va.muster.spirale")),
            (vb.LINIEN, tr("va.muster.linien")),
            (vb.WENDEL, tr("va.muster.wendel")),
        ):
            self.wahl_muster.addItem(text, muster)
        self.wahl_muster.currentIndexChanged.connect(lambda _i: self._muster_gewaehlt())
        schlichten.reihe(tr("va.muster"), tr("va.muster.tooltip"), self.wahl_muster)
        self.muster_grund = self._grau()
        self.muster_grund.setWordWrap(True)
        schlichten.ganz(self.muster_grund)
        # Linien längs nur im Gleichlauf (P-2026-10-02-28) – die Spirale fährt immer so.
        self.linien_nur_gleichlauf = QtGui.QCheckBox(tr("ba.nur_gleichlauf"))
        self.linien_nur_gleichlauf.setToolTip(tr("va.linien.nur_gleichlauf.tooltip"))
        self.linien_nur_gleichlauf.setEnabled(self.muster() == vb.LINIEN)
        self.linien_nur_gleichlauf.toggled.connect(lambda _an: self._vorschau_starten())
        self.wahl_muster.currentIndexChanged.connect(
            lambda _i: self.linien_nur_gleichlauf.setEnabled(self.muster() == vb.LINIEN)
        )
        schlichten.ganz(self.linien_nur_gleichlauf)
        # Die Spirale mit der Querachse (V5e, Manuels Y-Gedanke): vorgeschlagen, wenn die
        # Maschine eine Achse quer zur Stange hat und ein Kugelfräser schlichtet.
        self.schlichten_querachse = QtGui.QCheckBox(tr("va.querachse"))
        self.schlichten_querachse.setToolTip(tr("va.querachse.tooltip"))
        self.schlichten_querachse.toggled.connect(lambda _an: self._querachse_umgeschaltet())
        schlichten.ganz(self.schlichten_querachse)
        self.querachse_grund = self._grau()
        self.querachse_grund.setWordWrap(True)
        schlichten.ganz(self.querachse_grund)
        # Die Kugel dabei angestellt (Manuel, 2026-10-04: „als Haken, der aber pauschal angehakt
        # ist“): frei mit der Querachse und dem Kugelfräser.
        self.schlichten_anstellen = QtGui.QCheckBox(tr("va.anstellen"))
        self.schlichten_anstellen.setToolTip(tr("va.anstellen.tooltip"))
        self.schlichten_anstellen.toggled.connect(lambda _an: self._anstellen_umgeschaltet())
        schlichten.ganz(self.schlichten_anstellen)
        # C dreht dabei nicht zurück (P-2026-10-11-37; Manuel zu Frage 9: „nur da wo y nötig ist
        # … ist das the way to go“): frei mit der Querachse, dann angehakt.
        self.schlichten_stetig = QtGui.QCheckBox(tr("va.stetig"))
        self.schlichten_stetig.setToolTip(tr("va.stetig.tooltip"))
        self.schlichten_stetig.toggled.connect(lambda _an: self._stetig_umgeschaltet())
        schlichten.ganz(self.schlichten_stetig)
        self.schlichtfelder = schlichten.widget
        aufbau.addWidget(self.schlichtfelder)
        self.ergebnis_schlichten = grau()
        # Was die Kugel nach dem Schruppen nimmt (Frage 8) – grau, gelb wenn viel.
        self.rest_schlichten = grau()
        self.rest_schlichten.setToolTip(tr("va.rest.tooltip"))
        self.rest_schlichten.hide()
        # Vorschlichten (W-031; Manuel, 2026-10-18: „das man hier vll noch die möglichkeit dann
        # gibt "vorschlichten" als hacken anzubieten .. zwischen schruppen und schlichten“): die
        # Kugel des Schlichtens auf das Aufmaß des Schruppens, nur wo sie viel nähme – als eigene
        # Operation vor dem Schlichten.
        self.vorschlichten = QtGui.QCheckBox(tr("va.vorschlichten"))
        self.vorschlichten.setToolTip(tr("va.vorschlichten.tooltip"))
        self.vorschlichten.toggled.connect(self._vorschlichten_umgeschaltet)
        self.vorschlichten.hide()
        aufbau.addWidget(self.vorschlichten)
        self.ergebnis_vorschlichten = grau()
        self.ergebnis_vorschlichten.hide()
        self.halter_schlichten = gelb()
        self.lage_schlichten = gelb()
        self.schlichtfelder.setEnabled(False)
        self.schlichtfelder.setVisible(False)

        # --- Plan indexiert (V4c) ---
        self.mit_plan = haken(tr("va.plan"), tr("va.plan.tooltip"), self._plan_umgeschaltet)
        self.erklaerung_plan = grau(tr("va.plan.text"))
        self.plan_grund = grau()  # der Vorschlag mit Grund – oder warum es nicht geht
        plan = _Reihen()
        self.wahl_planfraeser = QtGui.QComboBox()
        self.wahl_planfraeser.currentIndexChanged.connect(lambda _i: self._planfraeser_gewaehlt())
        plan.reihe(tr("va.fraeser"), tr("va.planfraeser.tooltip"), self.wahl_planfraeser)
        self.wahl_planeinsatz = QtGui.QComboBox()
        self.wahl_planeinsatz.currentIndexChanged.connect(lambda _i: self._planeinsatz_gewaehlt())
        plan.reihe(tr("va.einsatz"), tr("va.planeinsatz.tooltip"), self.wahl_planeinsatz)
        self.schnittwerte_plan = self._grau()
        plan.ganz(self.schnittwerte_plan)
        self.felder_plan = {}
        for feld, text, tooltip in (
            ("zustellung_plan", tr("va.zustellung_plan"), tr("va.zustellung_plan.tooltip")),
            ("zeilenabstand", tr("va.zeilenabstand"), tr("va.zeilenabstand.tooltip")),
            ("aufmass_plan", tr("va.aufmass_plan"), tr("va.aufmass_plan.tooltip")),
        ):
            zahlenfeld(self.felder_plan, feld, text, tooltip, plan)
        zahlenfeld(  # die Auflösung (T-009): so fein wird das Teil vernetzt, leer der Vorschlag
            self.felder_plan,
            "aufloesung_plan",
            tr("va.aufloesung_netz"),
            tr(
                "va.aufloesung_netz.tooltip",
                vorschlag=groesse_zeigen(vp.TOLERANZ, einheiten.LAENGE),
            ),
            plan,
        )
        self.felder_plan["aufloesung_plan"].setPlaceholderText(
            groesse_zeigen(vp.TOLERANZ, einheiten.LAENGE)
        )
        # Der Weg über der Fläche (P-2026-10-12-146; Manuel, 2026-10-12: „außenrum ist alles frei
        # … so dass er D's fährt“): Zeilen hin und her oder Stiche von der offenen Seite.
        self.wahl_plan_weg = QtGui.QComboBox()
        for weg, text in (
            (vp.WEG_ZEILEN, tr("va.plan.weg.zeilen")),
            (vp.WEG_STICHE_GLEICHLAUF, tr("va.plan.weg.stiche_gleichlauf")),
            (vp.WEG_STICHE_GEGENLAUF, tr("va.plan.weg.stiche_gegenlauf")),
        ):
            self.wahl_plan_weg.addItem(text, weg)
        self.wahl_plan_weg.currentIndexChanged.connect(lambda _i: self._plan_weg_gewaehlt())
        plan.reihe(tr("va.plan.weg"), tr("va.plan.weg.tooltip"), self.wahl_plan_weg)
        # Die Zeilen nur im Gleichlauf: jede von vorne zum Futter, dazwischen abheben
        # (P-2026-10-02-24, Manuel: „auswählbar, ob er abhebt und wieder von vorne anfängt“).
        self.plan_nur_gleichlauf = QtGui.QCheckBox(tr("ba.nur_gleichlauf"))
        self.plan_nur_gleichlauf.setToolTip(tr("va.plan.nur_gleichlauf.tooltip"))
        self.plan_nur_gleichlauf.toggled.connect(lambda _an: self._vorschau_starten())
        plan.ganz(self.plan_nur_gleichlauf)
        # Die Seiten mit dem Schaft statt mit der Stirn (Manuel, 2026-10-11, Frage 10: „die
        # seiten beide variationen anbieten“) – wo die Schneide reicht; grau darunter, welche.
        self.plan_schaft = QtGui.QCheckBox(tr("va.plan.schaft"))
        self.plan_schaft.setToolTip(tr("va.plan.schaft.tooltip"))
        self.plan_schaft.toggled.connect(lambda _an: self._vorschau_starten())
        plan.ganz(self.plan_schaft)
        self.plan_schaft_grund = self._grau()
        self.plan_schaft_grund.setWordWrap(True)
        plan.ganz(self.plan_schaft_grund)
        self.mit_planbohrer = QtGui.QCheckBox()
        self.mit_planbohrer.setToolTip(tr("va.plan.mit_bohrer.tooltip"))
        self.mit_planbohrer.toggled.connect(lambda _an: self._planbohrer_umgeschaltet())
        self.mit_planbohrer.hide()  # nur mit Querbohrungen neben anderem und einem Bohrer
        plan.ganz(self.mit_planbohrer)
        self.planfelder = plan.widget
        aufbau.addWidget(self.planfelder)
        self.ergebnis_plan = grau()
        self.halter_plan = gelb()
        self.lage_plan = gelb()
        self.planfelder.setEnabled(False)
        self.planfelder.setVisible(False)
        self.mit_plan.setEnabled(False)  # bis eine ebene Fläche längs der Stange gewählt ist

        # --- Rundum entgraten (V4d) ---
        self.mit_entgraten = haken(
            tr("va.entgraten"), tr("va.entgraten.tooltip"), self._entgraten_umgeschaltet
        )
        self.erklaerung_entgraten = grau(tr("va.entgraten.text"))
        self.entgrat_grund = grau()  # der Vorschlag mit Grund – oder warum es nicht geht
        entgraten = _Reihen()
        self.wahl_entgratfraeser = QtGui.QComboBox()
        self.wahl_entgratfraeser.currentIndexChanged.connect(
            lambda _i: self._entgratfraeser_gewaehlt()
        )
        entgraten.reihe(tr("va.fraeser"), tr("va.entgratfraeser.tooltip"), self.wahl_entgratfraeser)
        self.wahl_entgrateinsatz = QtGui.QComboBox()
        self.wahl_entgrateinsatz.currentIndexChanged.connect(
            lambda _i: self._entgrateinsatz_gewaehlt()
        )
        entgraten.reihe(tr("va.einsatz"), tr("va.entgrateinsatz.tooltip"), self.wahl_entgrateinsatz)
        self.schnittwerte_entgraten = self._grau()
        entgraten.ganz(self.schnittwerte_entgraten)
        self.felder_entgraten = {}
        zahlenfeld(
            self.felder_entgraten, "breite", tr("va.breite"), tr("va.breite.tooltip"), entgraten
        )
        zahlenfeld(  # die Auflösung (T-009): der Schritt auf der Kante, leer der Vorschlag
            self.felder_entgraten,
            "aufloesung_entgraten",
            tr("va.aufloesung_kante"),
            tr(
                "va.aufloesung_kante.tooltip",
                vorschlag=groesse_zeigen(vent.ve.SCHRITT, einheiten.LAENGE),
            ),
            entgraten,
        )
        self.felder_entgraten["aufloesung_entgraten"].setPlaceholderText(
            groesse_zeigen(vent.ve.SCHRITT, einheiten.LAENGE)
        )
        self.entgratfelder = entgraten.widget
        aufbau.addWidget(self.entgratfelder)
        self.ergebnis_entgraten = grau()
        self.lage_entgraten = gelb()
        self.entgratfelder.setEnabled(False)
        self.entgratfelder.setVisible(False)
        self.mit_entgraten.setEnabled(False)  # bis es Außenkanten und einen Fräser dafür gibt

        # --- Abstände für alle ---
        aufbau.addSpacing(6)
        self.abstaende_titel = QtGui.QLabel(tr("va.abstaende"))
        self.abstaende_titel.setToolTip(tr("va.abstaende.tooltip"))
        schrift = self.abstaende_titel.font()
        schrift.setBold(True)
        self.abstaende_titel.setFont(schrift)
        aufbau.addWidget(self.abstaende_titel)
        abstaende = _Reihen()
        for feld, text, tooltip in (
            ("ueberlauf", tr("va.ueberlauf"), tr("va.ueberlauf.tooltip")),
            ("abstand_futter", tr("va.abstand_futter"), tr("va.abstand_futter.tooltip")),
            ("sicherheit", tr("va.sicherheit"), tr("va.sicherheit.tooltip")),
        ):
            zahlenfeld(self.felder_schruppen, feld, text, tooltip, abstaende)
        self.abstandsfelder = abstaende.widget
        aufbau.addWidget(self.abstandsfelder)
        # Die Beschriftungen aller Blöcke gleich breit: die Felder stehen untereinander.
        bloecke = (oben, schruppen, schlichten, plan, entgraten, abstaende)
        breite = max(r.breite_beschriftung() for r in bloecke)
        for reihen in bloecke:
            reihen.raster.setColumnMinimumWidth(0, breite)

        self.ausspannen = grau()  # wie weit die Stange aus dem Futter ragen muss
        self.radius_hinweis = grau(tr("va.radius"))
        self.hinweis_bearbeitung = QtGui.QLabel()
        self.hinweis_bearbeitung.setWordWrap(True)
        self.hinweis_bearbeitung.setStyleSheet(f"color: {ROT};")
        # Mit Verweis: Stirnflächen gehören in „Bearbeitung“ von vorn (_stirnseite_verweis).
        self.hinweis_bearbeitung.setTextFormat(QtCore.Qt.RichText)
        self.hinweis_bearbeitung.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse
        )
        self.hinweis_bearbeitung.linkActivated.connect(self._werkzeug_oeffnen)
        aufbau.addWidget(self.hinweis_bearbeitung)
        self.knopf_zurueck = knopf(
            tr("va.zurueck"), tr("va.zurueck.tooltip"), lambda: self.zeige_seite(1)
        )
        # Rechts daneben „Anlegen“ (beim Ändern „Übernehmen“) – dasselbe wie OK oben.
        self.knopf_fertig = knopf(tr("va.anlegen"), tr("va.anlegen.tooltip"), self.accept)
        zeile = QtGui.QHBoxLayout()
        zeile.addWidget(self.knopf_zurueck)
        zeile.addStretch()
        self.rad_unten = gui_rechnet.Rad()  # dreht, solange gerechnet wird (gui_rechnet)
        zeile.addWidget(self.rad_unten)
        zeile.addWidget(self.knopf_fertig)
        aufbau.addLayout(zeile)
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

    def auswahl_lesen(self, punkt=None, dokument=None):
        """Nimmt die angeklickte Fläche – aufgerufen, wenn man in der 3D-Ansicht klickt; nur
        in Schritt 1. `punkt`: wo (Weltkoordinaten) – an einer runden Fläche das Ende vorne.
        Liegt das Teil (auch hinter einem Link) in einem anderen Dokument (`dokument`: wo
        geklickt wurde), öffnet sich das Fenster dort neu, solange es noch keinen Job gibt
        (B-020)."""
        from .gui_bearbeitung import teil_hinter_link

        if self.geschlossen or self.seite != 1:
            return
        wahl = gewaehlte_flaeche(self.doc)
        if wahl is None and dokument and dokument != self.doc.Name:
            anderes = FreeCAD.listDocuments().get(dokument)
            wahl = gewaehlte_flaeche(anderes) if anderes is not None else None
        if wahl is None or wahl[1] is None:
            return
        teil = teil_hinter_link(wahl[0])
        if teil.Document is not self.doc:
            if self.job is None and self.zu_aendern is None:
                self._im_dokument_neu(teil, wahl[1])
            return
        if wahl != (self.teil, self.flaeche):
            self.waehle_flaeche(*wahl, nahe=punkt)

    def _im_dokument_neu(self, teil, flaeche):
        """Das Teil liegt in einem anderen Dokument als das Fenster: Es schließt und öffnet sich
        dort neu, mit Teil und Fläche (ein Aufgabenfenster gehört zu seinem Dokument)."""
        from .gui_bearbeitung import _aktivieren

        dokument, maschine = teil.Document, self._maschine_vorwahl
        self.reject()

        def oeffnen():
            _aktivieren(dokument)
            FreeCADGui.Control.showDialog(
                VierachsPanel(dokument, (teil, flaeche), maschine=maschine)
            )

        QtCore.QTimer.singleShot(0, oeffnen)

    def waehle_teilachse(self, achse):
        """Legt das Teil aus einem STL mit seiner Achse `achse` („X“, „Y“, „Z“) längs der Stange,
        ihr Plus-Ende vorne – ohne Fläche (vierachs_rohteil.vermesse_achse)."""
        teil = self.teil if self.teil is not None else getattr(self, "_stl_teil", None)
        if teil is not None:
            self.waehle_flaeche(teil, achse)

    def waehle_flaeche(self, teil, flaeche, nahe=None):
        """Legt `teil` mit seiner Fläche `flaeche` („FaceN“) vorne in die Stange – eine runde
        Fläche mit ihrer Achse als Stangenachse, das Ende nahe `nahe` vorne (V2b); „X“, „Y“, „Z“:
        eine Achse des Teils längs der Stange (waehle_teilachse)."""
        teil = vr.original(teil)
        form = teil.Shape
        if flaeche in vr.TEILACHSEN:
            vermessung, element, am_futter = vr.vermesse_achse(form, flaeche), None, False
        else:
            try:
                element = form.getElement(flaeche)
                vermessung = vr.vermesse(form, element, nahe)
            except ValueError:  # weder eben noch rund (oder keine solche Fläche)
                self._hinweis(tr("va.nicht_eben", flaeche=flaeche, teil=teil.Label))
                return
            # Eine ebene Fläche eines Teils aus einem STL liegt am Futter (seine Standfläche;
            # Manuel, 2026-10-11: „Standfläche zum Futter, abstechen“) – „Umdrehen“ legt sie nach
            # vorne.
            am_futter = vr.ist_eben(element) and stl_teil.aus_stl(teil)
            if am_futter:
                vermessung = vr.vermesse(form, element, nahe, True)
        self._nahe, self.umgedreht = nahe, am_futter
        if self.zu_aendern is not None and teil is not self.teil:
            self._hinweis(tr("va.aendern.anderes_teil", teil=self.teil.Label))
            return
        if self.job is not None and teil is not self.teil:
            # Ein anderes Teil: alles bisher Angelegte zurück, frisch anfangen.
            self._vor_neuem_teil()
            self.gewaehlte = []
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
            if self.maschinenwahl() is not None:  # A, B, C gibt es nur ohne Maschine
                self._waehle_maschine_ohne_signal(len(self._maschinen) - 1)
            index = self._index_ohne_maschine(buchstabe)
            if index != self.wahl_achse.currentIndex():
                self.wahl_achse.setCurrentIndex(index)
                return  # der Wechsel ruft diese Methode noch einmal
        vorher = FreeCAD.Placement(vr.modell(self.job).Placement) if self.job else None
        if self._anwenden() and vorher is not None:
            self._zeige_bewegung(vorher)

    def umdrehen(self):
        """„Umdrehen“: An einer runden Fläche kommt das andere Ende des Teils nach vorne – eine
        ebene Fläche liegt danach am Futter (wird abgestochen) oder wieder vorne."""
        if self.vermessung is None or self.teil is None:
            return
        self.umgedreht = not self.umgedreht
        if self.flaeche in vr.TEILACHSEN:
            self.vermessung = vr.vermesse_achse(self.teil.Shape, self.flaeche, self.umgedreht)
            self._anwenden()
            return
        element = self.teil.Shape.getElement(self.flaeche)
        self.vermessung = vr.vermesse(self.teil.Shape, element, self._nahe, self.umgedreht)
        self._anwenden()

    def plus90(self):
        """Dreht das Teil in der Stange um weitere 90°."""
        neu = (self._drehlage() + 90.0) % 360.0
        self.feld_drehlage.setText(zahl_zeigen(neu))  # 0 bleibt leer: der Vorschlag

    def maschinenwahl(self):
        """Was in der Liste „Maschine“ gewählt ist: vierachs_achsen.Maschinenwahl, der Pfad
        der zuletzt benutzten (noch zu öffnen) oder None – ohne Maschine."""
        i = self.wahl_maschine.currentIndex()
        return self._maschinen[i] if 0 <= i < len(self._maschinen) else None

    def _maschinen_fuellen(self, vorwahl=None):
        """Die Liste „Maschine“: die offenen Maschinen, zum Öffnen die zuletzt benutzte (D-20)
        und die aus der Liste „Maschinen …“, deren Rundachse die Stange dreht (W-011 S3),
        „ohne Maschine“. Vorgewählt die Maschine mit Assembly oder Dokument `vorwahl`, sonst
        die erste mit einer Rundachse für die Stange, sonst „ohne“."""
        import os

        from . import maschinenspeicher as msp
        from . import reichweite as rw
        from .gui_reichweite import gleiche_datei

        offen = va.maschinen(self.doc)
        self._maschinen = list(offen)
        self._aus_liste = {}  # Datei → Name aus der Liste der Maschinen

        def dabei(pfad):
            return any(gleiche_datei(e.assembly.Document.FileName, pfad) for e in offen) or any(
                isinstance(e, str) and gleiche_datei(e, pfad) for e in self._maschinen
            )

        gemerkt = rw.gemerkte_maschine()
        if gemerkt and os.path.isfile(gemerkt) and not dabei(gemerkt):
            self._maschinen.append(gemerkt)
        for eintrag in msp.laden():
            if eintrag.art in (msp.DREHMASCHINE, msp.FRAESE_4, msp.FRAESE_5) and eintrag.vorhanden:
                self._aus_liste[os.path.normcase(os.path.abspath(eintrag.datei))] = eintrag.name
                if not dabei(eintrag.datei):
                    self._maschinen.append(eintrag.datei)
        self._maschinen.append(None)
        wahl = next(
            (
                i
                for i, e in enumerate(offen)
                if e.achsen and (vorwahl is None or vorwahl in (e.assembly, e.assembly.Document))
            ),
            len(self._maschinen) - 1,
        )
        vorher, self._fuellt = self._fuellt, True
        try:
            self.wahl_maschine.clear()
            for i, eintrag in enumerate(self._maschinen):
                self.wahl_maschine.addItem(self._maschinentext(eintrag))
                if isinstance(eintrag, va.Maschinenwahl) and not eintrag.achsen:
                    self.wahl_maschine.model().item(i).setEnabled(False)
            self.wahl_maschine.setCurrentIndex(wahl)
        finally:
            self._fuellt = vorher
        self._achsen_fuellen()

    def _maschinentext(self, eintrag):
        import os

        from . import reichweite as rw
        from .gui_reichweite import gleiche_datei

        if isinstance(eintrag, va.Maschinenwahl):
            if not eintrag.achsen:
                return tr("va.maschine.ohne_rundachse", name=eintrag.name)
            return eintrag.name
        if isinstance(eintrag, str):
            name = getattr(self, "_aus_liste", {}).get(os.path.normcase(os.path.abspath(eintrag)))
            if name is not None and not gleiche_datei(eintrag, rw.gemerkte_maschine()):
                return tr("va.maschine.aus_liste", name=name)
            return tr(
                "va.maschine.oeffnen",
                name=name or os.path.splitext(os.path.basename(eintrag))[0],
            )
        return tr("va.maschine.ohne")

    def _waehle_maschine_ohne_signal(self, index):
        vorher, self._fuellt = self._fuellt, True
        try:
            self.wahl_maschine.setCurrentIndex(index)
        finally:
            self._fuellt = vorher
        self._achsen_fuellen()

    def _maschine_gewaehlt(self):
        """Eine andere Maschine: ihre Rundachse gilt, die Stange legt sich um. Die zuletzt
        benutzte öffnet sich dafür erst – die 3D-Ansicht bleibt beim Teil."""
        eintrag = self.maschinenwahl()
        if isinstance(eintrag, str):
            self._maschinen_fuellen(vorwahl=self._oeffne_maschine(eintrag))
        else:
            self._achsen_fuellen()
        self.waehle_rundachse()

    def _oeffne_maschine(self, pfad):
        """Öffnet die Datei der Maschine und holt das Teil wieder nach vorn; gibt das
        Dokument zurück, oder None mit einem roten Satz."""
        from .gui_reichweite import oeffne_datei, zeige_dokument

        try:
            dokument = oeffne_datei(pfad)
        except Exception as fehler:  # nicht mehr lesbar
            self._hinweis(tr("va.maschine.oeffnen_fehler", fehler=str(fehler)))
            return None
        FreeCAD.setActiveDocument(self.doc.Name)
        zeige_dokument(self.doc)
        return dokument

    def _achsen_fuellen(self):
        """Die Liste „Rundachse“ und der Satz darüber für die gewählte Maschine: ihre
        Rundachsen für die Stange – oder ohne Maschine A, B und C (die zuletzt gewählte
        vor)."""
        eintrag = self.maschinenwahl()
        if isinstance(eintrag, va.Maschinenwahl):
            self._achsen = list(eintrag.achsen)
            self.maschine_text.setText(
                tr(
                    "va.maschine.kann",
                    linear=", ".join(eintrag.linear) or "–",
                    rund=", ".join(a.buchstabe for a in eintrag.achsen) or "–",
                    plaetze=eintrag.plaetze,
                )
            )
        else:
            self._achsen = [va.zugewiesen(b) for b in _achstexte()]
            self.maschine_text.setText(tr("va.maschine.ohne.text"))
        vorher, self._fuellt = self._fuellt, True
        try:
            self.wahl_achse.clear()
            for achse in self._achsen:
                self.wahl_achse.addItem(achstext(achse))
            index = 0
            if eintrag is None:
                gemerkt = _parameter().GetString(GEMERKT_RUNDACHSE, vr.RUNDACHSE)
                index = max(0, self._index_ohne_maschine(gemerkt))
            self.wahl_achse.setCurrentIndex(index)
            self.wahl_achse.setEnabled(len(self._achsen) > 1)
        finally:
            self._fuellt = vorher

    def achse(self):
        """Die gewählte Stangenachse (vierachs_achsen.Stangenachse) – beim Ändern die der
        Operation."""
        if self._achse_fest is not None:
            return self._achse_fest
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
        if nummer == 2 and self.zu_aendern is not None:
            titel = tr("va.kopf.aendern", name=self.zu_aendern.Label)
        if nummer == 1 and self.zu_aendern is not None and self._stange_vorher is None:
            ansicht = self.job.Stock.ViewObject if self.job.Stock is not None else None
            if ansicht is not None:  # durchsichtig: Flächen des Teils lassen sich anklicken
                self._stange_vorher = (
                    ansicht.DisplayMode,
                    ansicht.Transparency,
                    ansicht.Selectable,
                )
                self._stange_anzeigen(*STANGE_ANZEIGE, waehlbar=False)
        self._kopf_text.setText(f"<b>{titel}</b>")
        if nummer == 2:
            self._bearbeitung_fuellen()
            self._flaechen_zeigen()
        else:  # die Länge der Stange hängt auch am Fräser aus Schritt 2 (Überlauf)
            self._farben_zurueck()
            self._auffrischen()
        self._knoepfe_beschriften()

    def _bearbeitung_fuellen(self):
        """Werkstoff und die Fräser beider Bearbeitungen anbieten – die Werkzeugverwaltung frisch
        gelesen. Der Werkstoff kommt vom Rohteil oder ist der zuletzt benutzte (wie in
        „Schnittwerte in den Job“). Beim ersten Mal ist „Rundum schlichten“ angehakt, wenn ein
        Fräser einen Einsatz „Schlichten“ hat."""
        from .gui_werkzeuge import werkstoffe_anbieten

        vorher = self.werkstoff() if self.bibliothek is not None else None
        self.hinweis_bearbeitung.setText("")
        try:
            self.bibliothek = wz.Bibliothek.laden()
        except wz.BeschaedigteDatei as fehler:
            self.bibliothek = wz.Bibliothek()
            self._rot(tr("wv.fehler.laden", fehler=fehler, datei=fehler.beiseite))
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
            kennung = werkzeug.kennung if werkzeug is not None else ""
            if self._art == SCHLICHTEN:
                self._vorwahl, self._vorwahl_schlichten = "", kennung
            elif self._art == PLAN:
                self._vorwahl, self._vorwahl_plan = "", kennung
            elif self._art == ENTGRATEN:
                self._vorwahl, self._vorwahl_entgraten = "", kennung
            else:
                self._vorwahl = kennung
        # Zählt X der Maschine im Durchmesser, zeigt das Prüffenster X so – FreeCADs eigene
        # Postprozessoren schreiben trotzdem den Radius (P-2026-09-30-54).
        wahl = self.maschinenwahl()
        if isinstance(wahl, va.Maschinenwahl) and m.x_im_durchmesser(wahl.maschine):
            self.radius_hinweis.setText(tr("va.radius_durchmesser"))
        else:
            self.radius_hinweis.setText(tr("va.radius"))
        self.radius_hinweis.setVisible(self.buchstabe() == "C")
        self._fraeser_fuellen()
        self._schlichtfraeser_fuellen()
        self._planfraeser_fuellen()
        self._entgratfraeser_fuellen()
        self._muster_vorschlagen()
        self._querachse_vorschlagen()
        self._plan_vorschlagen()
        self._entgraten_vorschlagen()
        if self.zu_aendern is None and not self._schlichten_vorgewaehlt:
            self._schlichten_vorgewaehlt = True
            werkstoff = self.werkstoff()
            self._schlichten_vorschlag = any(
                self._hat_schlichten(w, werkstoff) for w in self._schlichtfraeser
            )
            self._schlichten_setzen(self._schlichten_vorschlag)
        self._schlichten_vorschlagen()

    def werkstoff(self):
        """Kennung des gewählten Werkstoffs, oder wz.ALLE."""
        return self.wahl_werkstoff.currentData() or wz.ALLE

    def _werkstoff_gewaehlt(self):
        if not self._fuellt:
            self._fraeser_fuellen()
            self._schlichtfraeser_fuellen()

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
            for w in self._sortiert()
            if w.art in FRAESER_ARTEN
            and w.durchmesser > 0
            and self._passende_einsaetze(w, werkstoff)
        ]
        kennungen = [w.kennung for w in self._fraeser]
        gemerkt = _parameter().GetString(GEMERKT_FRAESER, "")
        if vorher is not None and vorher.kennung in kennungen:
            wahl = kennungen.index(vorher.kennung)
        elif self._vorwahl in kennungen:  # beim Ändern: der Fräser der Operation
            wahl = kennungen.index(self._vorwahl)
        elif gemerkt in kennungen and self._im_magazin(gemerkt):
            wahl = kennungen.index(gemerkt)
        else:
            arten = [w.art for w in self._fraeser]
            wahl = arten.index(wz.SCHAFTFRAESER) if wz.SCHAFTFRAESER in arten else 0
        self._fuellt = True
        try:
            self.wahl_fraeser.clear()
            for werkzeug in self._fraeser:
                self.wahl_fraeser.addItem(self._zeile(werkzeug))
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
            if not self._planfraeser_von_hand and self._art != PLAN:
                self._planfraeser_fuellen()  # „Plan indexiert“ nimmt den Schruppfräser

    def _einsatz_fuellen(self):
        """Die Einsätze des Fräsers; vorgewählt „Schruppen“, sonst „Schruppen dynamisch“,
        sonst der erste."""
        werkzeug = self.fraeser()
        self._einsaetze = (
            self._passende_einsaetze(werkzeug, self.werkstoff()) if werkzeug is not None else []
        )
        arten = [e.art for e in self._einsaetze]
        wahl = next((arten.index(a) for a in (wz.SCHRUPPEN, wz.DYNAMISCH) if a in arten), 0)
        if (
            self._tc_vorher is not None
            and werkzeug is not None
            and werkzeug.kennung == (self._vorwahl)
        ):  # beim Ändern: der Einsatz, mit dem der Controller gesetzt ist
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
        """Der gewählte Einsatz (werkzeuge.Einsatz) oder None."""
        i = self.wahl_einsatz.currentIndex()
        return self._einsaetze[i] if 0 <= i < len(self._einsaetze) else None

    def _einsatz_gewaehlt(self):
        """Drehzahl und Vorschub zeigen, die Vorschläge in die Felder, die Lagen neu rechnen."""
        if self._fuellt:
            return
        werkzeug, einsatz = self.fraeser(), self.einsatz()
        self.schnittwerte.setText(self._schnittwerte_text(werkzeug, einsatz))
        for feld, eingabe in self.felder_schruppen.items():
            if feld == "ueberlauf":  # die Abstechbreite + 0,5 mm
                eingabe.setPlaceholderText(
                    tr(
                        "va.ueberlauf.vorschlag",
                        zugabe=groesse_zeigen(vb.UEBERLAUF_ZUGABE, einheiten.LAENGE),
                    )
                )
            else:
                eingabe.setPlaceholderText(groesse_zeigen(self._vorschlag(feld), einheiten.LAENGE))
        self._querachse_vorschlagen()
        self._vorschau_starten()

    def _schnittwerte_text(self, werkzeug, einsatz):
        """„n 3979 1/min · vf 955 mm/min“ – leer ohne Fräser oder Einsatz."""
        if werkzeug is None or einsatz is None:
            return ""
        n, vf, _senkrecht = js.werte_im_job(werkzeug, einsatz, self.job)
        return tr("va.schnittwerte", n=f"{n:.0f}", vf=groesse_fest(vf, einheiten.VORSCHUB, 0))

    # --- Flächen (V4) ---------------------------------------------------------------------

    def flaeche_angeklickt(self, objekt, unterelement):
        """In Schritt 2 wurde eine Fläche angeklickt (`objekt`: Name, `unterelement`: Weg bis
        „Face3“): Gehört sie zum Teil im Job, kommt sie dazu oder heraus. Danach ist die Auswahl
        wieder leer – die Farben zeigen, was gewählt ist."""
        if self.geschlossen or self.seite != 2 or self.job is None:
            return
        teil, flaeche = _entlang(self.doc, self.doc.getObject(objekt), unterelement)
        klon = vr.modell(self.job)
        if teil is None or flaeche is None or vr.original(teil) is not vr.original(klon):
            return
        FreeCADGui.Selection.clearSelection()
        self.flaeche_umschalten(flaeche)

    def flaeche_umschalten(self, name):
        """Nimmt die Fläche `name` („Face3“) dazu – oder heraus, wenn sie schon gewählt ist."""
        if name in self.gewaehlte:
            self.gewaehlte.remove(name)
        else:
            self.gewaehlte.append(name)
        self._flaechen_geaendert()

    def alle_mantelflaechen(self):
        """Jede Fläche, die nach außen schaut – das ist rundum."""
        if self.job is None:
            return
        self.gewaehlte = vf.namen(vf.mantelflaechen(self._sicht()))
        self._flaechen_geaendert()

    def flaechen_leeren(self):
        """Keine Fläche gewählt: rundum."""
        self.gewaehlte = []
        self._flaechen_geaendert()

    def _flaechen_geaendert(self):
        self._flaechen_zeigen()
        self._plan_vorschlagen()
        self._schlichten_vorschlagen()
        self._muster_vorschlagen()  # nach dem Plan: es sieht auf die Flächen, die der Kugel bleiben
        self._querachse_vorschlagen()
        self._entgraten_vorschlagen()
        self._vorschau_starten()

    def _muster_vorschlagen(self):
        """Das Muster fürs Schlichten, das zu den gewählten Flächen passt (V4c; W-006 E5:
        Vorschlag mit Grund, änderbar): Linien längs, wenn sie nicht rundum gehen – eine
        Abflachung, eine Nut –, sonst die Spirale. Gesetzt wird es, solange man keins von Hand
        gewählt hat; der Grund steht grau darunter."""
        if self.job is None:
            return
        muster, grund = vb.SPIRALE, tr("va.muster.vorschlag.spirale")
        # Mit Flächen ohne die, die „Plan indexiert“ fertig macht (W-027); rundum die Spirale –
        # auch mit Plan indexiert, sie fährt über dessen Flächen angehoben.
        flaechen = self._schlicht_flaechen() if self.flaechen() else []
        wendel = self._wendel_erkannt()
        if flaechen:
            werkzeug = self.schlichtfraeser()
            radius = werkzeug.durchmesser / 2 if werkzeug is not None else 0.0
            bereich = vf.bereich(self._sicht(), vf.nummern(flaechen), radius)
            belegt = bereich.drin[bereich.drin.any(axis=1)]
            if belegt.size and not belegt.all():
                muster, grund = vb.LINIEN, tr("va.muster.vorschlag.linien")
        elif wendel is not None:
            # Eine Wendelnut: ihr nach (W-030; Manuel, 2026-10-18: „Ja, vorgewählt bei
            # Wendelnut“).
            muster, grund = vb.WENDEL, self._wendel_grund(wendel)
        self.muster_grund.setText(grund)
        self._schruppen_wendel_vorschlagen(wendel if not flaechen else None)
        if not self._muster_von_hand:
            self._muster_setzen(muster)

    def _schruppen_wendel_vorschlagen(self, wendel):
        """„Der Wendelnut nach“ beim Schruppen: zu sehen mit einer Wendelnut, dann angehakt,
        solange man ihn nicht von Hand gesetzt hat; ohne Wendelnut weg."""
        self.schruppen_wendel.setVisible(wendel is not None)
        if self._schruppen_wendel_von_hand:
            return
        vorher = self._fuellt
        self._fuellt = True
        try:
            self.schruppen_wendel.setChecked(wendel is not None)
        finally:
            self._fuellt = vorher

    def schruppen_wendel_an(self):
        """Schruppt das Schruppen die Wendelnut ihr nach?"""
        return self.schruppen_wendel.isVisible() and self.schruppen_wendel.isChecked()

    def _schruppen_wendel_umgeschaltet(self):
        if self._fuellt:
            return
        self._schruppen_wendel_von_hand = True
        self._vorschau_starten()

    def _wendel_grund(self, wendel):
        """„Vorschlag: der Wendel nach – die Nut läuft mit 60 mm Steigung um …“"""
        gaenge = (
            tr("va.wendel.eingaengig")
            if wendel.gaenge == 1
            else tr("va.wendel.mehrgaengig", gaenge=wendel.gaenge)
        )
        return tr(
            "va.muster.vorschlag.wendel",
            steigung=groesse_zeigen(round(abs(wendel.steigung), 1), einheiten.LAENGE),
            gaenge=gaenge,
            richtung=tr("va.wendel.rechts" if wendel.steigung > 0 else "va.wendel.links"),
        )

    def _wendel_erkannt(self):
        """Die Wendelnut des Teils (vierachs_wendel.Wendel) oder None. Für ein neues Modell
        beginnt das Erkennen auf einem Nebenrechner (ohne einen hier) – ist es da, schlägt
        _wendel_angekommen das Muster noch einmal vor."""
        from . import nebenrechner as nr

        if self.job is None:
            return None
        try:
            modell = vr.modell(self.job)
            schluessel = (self.job.Name, vh.form_kennung(modell.Shape), tuple(self.achse().laengs))
        except Exception:  # noqa: BLE001 – ohne Modell kein Vorschlag
            return None
        if schluessel == self._wendel_schluessel:
            return self._wendel
        if self._wendel_auftrag is not None and not self._wendel_auftrag.erledigt:
            if getattr(self._wendel_auftrag, "_schluessel", None) == schluessel:
                return None
            self._wendel_auftrag.abbrechen()
        self._wendel_auftrag = None
        achse = self.achse()
        argumente = (tuple(achse.laengs), tuple(va.radial(achse)))
        pool = nr.pool()
        if pool.verfuegbar():
            try:
                auftrag = pool.auftrag(
                    "vierachs_vorschau",
                    "wendel",
                    pool.kopie(self.doc, wiederverwenden=True),
                    self.job.Name,
                    *argumente,
                )
            except nr.NichtVerfuegbar:
                auftrag = None
            if auftrag is not None:
                auftrag._schluessel = schluessel
                auftrag.bei_fertig = lambda a: self._wendel_angekommen(schluessel, a)
                self._wendel_auftrag = auftrag
                return None
        try:
            self._wendel = vv.wendel(self.doc, self.job.Name, *argumente)
        except Exception as fehler:  # noqa: BLE001 – ohne Erkennen die Spirale
            FreeCAD.Console.PrintLog(f"CAM-Addon: Wendel erkennen: {fehler}\n")
            self._wendel = None
        self._wendel_schluessel = schluessel
        return self._wendel

    def _wendel_angekommen(self, schluessel, auftrag):
        if self.geschlossen or auftrag is not self._wendel_auftrag:
            return
        self._wendel_auftrag = None
        self._wendel = auftrag.ergebnis if auftrag.fehler is None else None
        self._wendel_schluessel = schluessel
        if self._wendel is None:
            return
        vorher = (self.muster(), self.schruppen_wendel.isChecked())
        self._muster_vorschlagen()
        self._querachse_vorschlagen()
        if (self.muster(), self.schruppen_wendel.isChecked()) != vorher:
            self._vorschau_starten()

    def _muster_setzen(self, muster, von_hand=False):
        """Wählt `muster` (vierachs_bahn.SPIRALE, LINIEN) in der Liste – ohne dass es als von
        Hand gewählt zählt, außer `von_hand` (beim Ändern: das Muster der Operation)."""
        vorher = self._fuellt
        self._fuellt = True
        try:
            self.wahl_muster.setCurrentIndex(max(0, self.wahl_muster.findData(muster)))
        finally:
            self._fuellt = vorher
        if von_hand:
            self._muster_von_hand = True

    def muster(self):
        """Das gewählte Muster fürs Schlichten: vierachs_bahn.SPIRALE oder LINIEN."""
        return self.wahl_muster.currentData() or vb.SPIRALE

    def _querachse_vorschlagen(self):
        """Der Haken „mit der Querachse“ (V5e): geht mit der Spirale und einer Achse quer zur
        Stange an der Maschine, mit jedem Fräser, dessen Form das Addon kennt (P-2026-10-03-22:
        auch Schaft- und Torusfräser) – dann vorgeschlagen (angehakt), solange man ihn nicht von
        Hand gesetzt hat; sonst aus und gesperrt, der Grund steht grau darunter."""
        if self.job is None:
            return
        achse = self.achse()
        werkzeug = self.schlichtfraeser()
        form = ff.von_werkzeug(werkzeug) if werkzeug is not None else None
        if not achse.quer:
            geht, grund = False, tr("va.querachse.keine", maschine=achse.maschine)
        elif self.muster() not in (vb.SPIRALE, vb.WENDEL):
            geht, grund = False, tr("va.querachse.nur_spirale")
        elif form is None:
            geht, grund = False, tr("va.querachse.ohne_form")
        elif self._schlicht_flaechen():
            # Mit Flächen (gewählt, oder ohne die, die „Plan indexiert“ fertig macht): die Spirale
            # rundum, über den übrigen Flächen angehoben im Freivorschub (Frage 12, Manuel
            # 2026-10-11; vierachs_bahn.Schlichtwerte.flaechen_netz) – ohne den Haken Zeilen ohne Y.
            geht, grund = True, tr("va.querachse.mit_flaechen")
        elif form.nur_kugel:
            geht, grund = True, tr("va.querachse.vorschlag")
        else:
            geht, grund = True, tr("va.querachse.vorschlag_stirn")
        self.querachse_grund.setText(grund)
        self._haken_setzen(self.schlichten_querachse, geht, self._querachse_von_hand)
        self._anstellen_vorschlagen()
        self._stetig_vorschlagen()
        # Beim Schruppen: rundum (mit gewählten Flächen fährt es Zeilen) und ein Fräser mit Form.
        schrupp_form = ff.von_werkzeug(self.fraeser()) if self.fraeser() is not None else None
        if not achse.quer:
            geht, grund = False, tr("va.querachse.keine", maschine=achse.maschine)
        elif self.flaechen():
            geht, grund = False, tr("va.querachse.nur_rundum")
        elif schrupp_form is None:
            geht, grund = False, tr("va.querachse.ohne_form")
        else:
            geht, grund = True, tr("va.querachse.schruppen.vorschlag")
        self.querachse_grund_schruppen.setText(grund)
        self._haken_setzen(self.schruppen_querachse, geht, self._querachse_schruppen_von_hand)
        self._stetig_schruppen_vorschlagen()

    def _haken_setzen(self, haken, geht, von_hand):
        """Ein Haken „mit der Querachse“: frei und vorgeschlagen, wenn es geht – solange er nicht
        von Hand gesetzt ist –, sonst aus und gesperrt."""
        vorher = self._fuellt
        self._fuellt = True
        try:
            haken.setEnabled(geht)
            if not geht:
                haken.setChecked(False)
            elif not von_hand:
                haken.setChecked(True)
        finally:
            self._fuellt = vorher

    def querachse(self):
        """Schlichten mit der Querachse (angehakt und möglich)?"""
        return self.schlichten_querachse.isEnabled() and self.schlichten_querachse.isChecked()

    def _anstellen_vorschlagen(self):
        """Der Haken „Kugel anstellen“: frei mit der Querachse und dem Kugelfräser, dann angehakt,
        solange man ihn nicht von Hand gesetzt hat."""
        werkzeug = self.schlichtfraeser()
        form = ff.von_werkzeug(werkzeug) if werkzeug is not None else None
        # Frei wie der Haken darüber – auch, solange die Schlichtfelder noch gesperrt sind.
        quer = self.schlichten_querachse.isChecked() and self.schlichten_querachse.isEnabledTo(
            self.schlichtfelder
        )
        geht = quer and form is not None and form.nur_kugel
        self._haken_setzen(self.schlichten_anstellen, geht, self._anstellen_von_hand)

    def anstellen(self):
        """Die Kugel mit der Querachse anstellen (angehakt und möglich)?"""
        return self.schlichten_anstellen.isEnabled() and self.schlichten_anstellen.isChecked()

    def _stetig_vorschlagen(self):
        """Der Haken „C dreht nicht zurück“: frei mit der Querachse, dann angehakt, solange man ihn
        nicht von Hand gesetzt hat."""
        quer = self.schlichten_querachse.isChecked() and self.schlichten_querachse.isEnabledTo(
            self.schlichtfelder
        )
        self._haken_setzen(self.schlichten_stetig, quer, self._stetig_von_hand)

    def stetig(self):
        """Mit der Querachse dreht C nicht zurück (angehakt und möglich)?"""
        return self.schlichten_stetig.isEnabled() and self.schlichten_stetig.isChecked()

    def _stetig_umgeschaltet(self):
        if self._fuellt:
            return
        self._stetig_von_hand = True
        self._vorschau_starten()

    def querachse_schruppen(self):
        """Schruppen mit der Querachse (angehakt und möglich)?"""
        return self.schruppen_querachse.isEnabled() and self.schruppen_querachse.isChecked()

    def _stetig_schruppen_vorschlagen(self):
        """„C dreht nicht zurück“ beim Schruppen: frei mit der Querachse, dann angehakt, solange
        man ihn nicht von Hand gesetzt hat."""
        quer = self.schruppen_querachse.isChecked() and self.schruppen_querachse.isEnabledTo(
            self.schruppfelder
        )
        self._haken_setzen(self.schruppen_stetig, quer, self._stetig_schruppen_von_hand)
        # Rundum mit und ohne Querachse (P-2026-10-11-58), mit gewählten Flächen fährt es Zeilen.
        self._haken_setzen(
            self.schruppen_noetig, not self.flaechen() or quer, self._noetig_von_hand
        )
        self._sektoren_y_vorschlagen()

    def _sektoren_y_vorschlagen(self):
        """„Sektoren in Zeilen mit Y – C steht“: frei mit der Querachse und „Folgelagen nur, wo
        nötig“ (die Sektoren gibt es nur so), dann angehakt, solange man ihn nicht von Hand
        gesetzt hat."""
        # isEnabledTo: Solange „Rundum schruppen“ aus ist, sind seine Felder gesperrt – der Vorschlag
        # gilt trotzdem (sonst blieb der Haken grau, Gegenleser zu P-48).
        quer = self.schruppen_querachse.isChecked() and self.schruppen_querachse.isEnabledTo(
            self.schruppfelder
        )
        noetig = self.schruppen_noetig.isChecked() and self.schruppen_noetig.isEnabledTo(
            self.schruppfelder
        )
        geht = quer and noetig and not self.flaechen()
        self._haken_setzen(self.schruppen_sektoren_y, geht, self._sektoren_y_von_hand)
        self.schruppen_sektor_wellen.setEnabled(self.sektoren_y())

    def sektor_wellen(self):
        """Schlitze in den Sektoren als offene Nut in Wellen (angehakt und möglich)?"""
        return self.sektoren_y() and self.schruppen_sektor_wellen.isChecked()

    def _sektor_wellen_umgeschaltet(self):
        if self._fuellt:
            return
        self._vorschau_starten()

    def sektoren_y(self):
        """Beim Schruppen mit der Querachse Sektoren als Zeilen mit Y (angehakt und möglich)?"""
        return self.schruppen_sektoren_y.isEnabled() and self.schruppen_sektoren_y.isChecked()

    def _sektoren_y_umgeschaltet(self):
        if self._fuellt:
            return
        self._sektoren_y_von_hand = True
        self.schruppen_sektor_wellen.setEnabled(self.sektoren_y())
        self._vorschau_starten()

    def y_weg(self):
        """So weit fährt die Querachse der gewählten Maschine von der Mitte aus (mm, ± – nach
        ihrem Y-Anteil, stirnseite.y_nutzen): an einer Drehmaschine mit C aus ihrer Kinematik
        (stirnseite.rahmen, Y 0 auf der Drehachse; Gegenleser zu P-48), sonst aus den Grenzen des
        Gelenks ihrer Y-Achse; ohne Maschine oder Grenzen unbegrenzt (math.inf). Je Maschine
        einmal gerechnet."""
        wahl = self.maschinenwahl()
        if not isinstance(wahl, va.Maschinenwahl):
            return math.inf
        schluessel = (wahl.assembly.Document.Name, wahl.maschine.Name)
        if schluessel not in self._y_weg_gemerkt:
            self._y_weg_gemerkt[schluessel] = self._y_weg_rechnen(wahl)
        return self._y_weg_gemerkt[schluessel]

    def _y_weg_rechnen(self, wahl):
        from . import kette as kt
        from . import maschine as m
        from . import reichweite as rw
        from . import stirnseite as st

        try:
            pruefung = rw.Pruefung(wahl.assembly, wahl.maschine)
            werkzeug = self.fraeser()
            aufnahme = pruefung.werkzeugaufnahme(werkzeug.nummer if werkzeug else 1)
            if aufnahme is None and pruefung.werkzeugaufnahmen:
                aufnahme = pruefung.werkzeugaufnahmen[0]
            rahmen = st.rahmen(pruefung, aufnahme, 100.0) if aufnahme is not None else None
        except Exception:  # noqa: BLE001 – ohne Kinematik: die Grenzen des Gelenks
            rahmen = None
        if rahmen is not None:
            weg = min(-rahmen.y_min, rahmen.y_max)
            return weg if weg > 0 else math.inf
        for ba in m.betriebsarten(wahl.maschine):
            if ba.Art != m.ART_LINEAR or m.programmname(ba).upper() != "Y":
                continue
            gelenk = getattr(ba, "Gelenk", None)
            if gelenk is None:
                return math.inf
            unten, oben = kt._begrenzung(gelenk, kt.LINEAR)
            if unten is None or oben is None:
                return math.inf
            weg = min(abs(unten), abs(oben)) * st.y_nutzen(wahl.maschine) / 100.0
            return weg if weg > 0 else math.inf
        return math.inf

    def stetig_schruppen(self):
        """Beim Schruppen mit der Querachse dreht C nicht zurück (angehakt und möglich)?"""
        return self.schruppen_stetig.isEnabled() and self.schruppen_stetig.isChecked()

    def _stetig_schruppen_umgeschaltet(self):
        if self._fuellt:
            return
        self._stetig_schruppen_von_hand = True
        self._vorschau_starten()

    def nur_noetig(self):
        """Beim Schruppen mit der Querachse Folgelagen nur, wo nötig (angehakt und möglich)?"""
        return self.schruppen_noetig.isEnabled() and self.schruppen_noetig.isChecked()

    def _noetig_umgeschaltet(self):
        if self._fuellt:
            return
        self._noetig_von_hand = True
        self._sektoren_y_vorschlagen()
        self._vorschau_starten()

    def _querachse_umgeschaltet(self):
        if self._fuellt:
            return
        self._querachse_von_hand = True
        self._anstellen_vorschlagen()
        self._stetig_vorschlagen()
        self._schrittweite_vorschlag_zeigen()
        self._vorschau_starten()

    def _anstellen_umgeschaltet(self):
        if self._fuellt:
            return
        self._anstellen_von_hand = True
        self._schrittweite_vorschlag_zeigen()
        self._vorschau_starten()

    def _schrittweite_vorschlag_zeigen(self):
        """Der Vorschlag der Schrittweite grau im Feld – er hängt an Kammhöhe, Fräser, Einsatz und
        ob die Kugel angestellt fährt (vierachs_schlichten.schrittweite_vorschlag)."""
        eingabe = self.felder_schlichten.get("schrittweite")
        if eingabe is not None:
            eingabe.setPlaceholderText(
                groesse_zeigen(self._vorschlag("schrittweite"), einheiten.LAENGE) or "0"
            )
        self._kammhoehe_zeigen()

    def _kammhoehe_zeigen(self):
        """„→ Kammhöhe …“ unter der Schrittweite – aus der eingetragenen oder vorgeschlagenen, so
        genau, dass man sie sieht (0,15 mm mit der Kugel Ø 12: 0,0005 statt „0,000“; Manuel,
        2026-10-18: „auch wenn ich die schrittweite eingebe .. ändert sich an der kammhöhe nix“).
        Mit flacher Stirn gilt sie auf ebenen Stellen; liegt die Schrittweite über „ae max“ des
        Einsatzes und die Kugel fährt nicht angestellt, ein Satz in Gelb."""
        werkzeug = self.schlichtfraeser() if self.felder_schlichten else None
        schrittweite = self._wert("schrittweite") if werkzeug is not None else 0.0
        if werkzeug is None or not 0 < schrittweite <= werkzeug.durchmesser:
            self.kammhoehe.hide()
            self.kammhoehe_ae.hide()
            return
        form = ff.von_werkzeug(werkzeug)
        hoehe = form.kammhoehe(schrittweite)
        stellen = 3 if hoehe >= 0.01 or hoehe < 1e-5 else 4
        text = tr("va.kammhoehe", hoehe=groesse_fest(hoehe, einheiten.LAENGE, stellen))
        if form.eben:
            text += " " + tr("va.kammhoehe.eben")
        self.kammhoehe.setText(text)
        self.kammhoehe.show()
        einsatz = self.schlichteinsatz()
        angestellt = self.querachse() and self.anstellen()
        ueber = (
            einsatz is not None
            and einsatz.ae_max > 0
            and schrittweite > einsatz.ae_max + 1e-9
            and not form.eben
            and not angestellt
        )
        if ueber:
            self.kammhoehe_ae.setText(
                tr(
                    "va.kammhoehe.ueber_ae",
                    schrittweite=groesse_zeigen(schrittweite, einheiten.LAENGE),
                    ae=groesse_zeigen(einsatz.ae_max, einheiten.LAENGE),
                )
            )
        self.kammhoehe_ae.setVisible(ueber)

    def _querachse_schruppen_umgeschaltet(self):
        if self._fuellt:
            return
        self._querachse_schruppen_von_hand = True
        self._stetig_schruppen_vorschlagen()
        self._vorschau_starten()

    def _muster_gewaehlt(self):
        if self._fuellt:
            return
        self._muster_von_hand = True
        self._querachse_vorschlagen()
        self._vorschau_starten()

    def flaechen(self):
        """Die Flächen für die Operationen („Face3“ …): die gewählten – leer heißt rundum, auch
        wenn alle Mantelflächen gewählt sind (Manuel: „wenn ich alle anklicke, dann wird
        komplett rings um bearbeitet“)."""
        if not self.gewaehlte or self.job is None:
            return []
        mantel = set(vf.namen(vf.mantelflaechen(self._sicht())))
        if mantel and mantel <= set(self.gewaehlte):
            return []
        return list(self.gewaehlte)

    def _sicht(self):
        """Was ein Strahl von außen zuerst trifft (vierachs_flaechen.Sicht) – für das Teil, wie
        es im Job liegt, und die gewählte Rundachse; einmal gerechnet (vf.sicht_fuer merkt es
        sich)."""
        achse = self.achse()
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            return vf.sicht_fuer(vr.modell(self.job).Shape, achse.laengs, va.radial(achse))
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def _erreichbar(self, sicht, nummer):
        """(Text, Farbe), wie weit ein radiales Werkzeug an die Fläche `nummer` kommt."""
        from .gui_kollision import GELB

        anteil = vf.erreichbar(sicht, nummer)
        if anteil is None:
            return tr("va.flaeche.quer"), ROT
        if anteil >= vf.GANZ:
            return tr("va.flaeche.ganz"), GRUEN
        if anteil <= vf.KAUM:
            return tr("va.flaeche.nicht"), ROT
        return tr("va.flaeche.teil", prozent=f"{100 * anteil:.0f}"), GELB

    def _flaechen_zeigen(self):
        """Die Liste der gewählten Flächen mit Art und Erreichbarkeit, der Satz darunter und die
        Farben in der 3D-Ansicht."""
        self.flaechen_liste.clear()
        self.flaechen_liste.setVisible(bool(self.gewaehlte))
        if not self.gewaehlte or self.job is None:
            self.flaechen_text.setText(tr("va.flaechen.rundum"))
            self._farben_zeigen({})
            return
        sicht = self._sicht()
        form = vr.modell(self.job).Shape
        laengs = self.achse().laengs
        farben = {}
        for name in self.gewaehlte:
            nummer = vf.nummern([name])
            if not nummer or nummer[0] >= ft.anzahl(form):
                art, (erreichbar, farbe) = "?", (tr("va.flaeche.fehlt"), ROT)
            else:
                art = vf.beschreibung(ft.flaeche(form, nummer[0]), laengs)
                erreichbar, farbe = self._erreichbar(sicht, nummer[0])
                farben[nummer[0]] = _im_3d(farbe)
            eintrag = QtGui.QListWidgetItem(
                dezimal(tr("va.flaeche.zeile", name=name, art=art, erreichbar=erreichbar))
            )
            eintrag.setForeground(QtGui.QBrush(QtGui.QColor(farbe)))
            eintrag.setData(QtCore.Qt.UserRole, name)
            self.flaechen_liste.addItem(eintrag)
        zeilen = min(len(self.gewaehlte), 5)
        hoehe = self.flaechen_liste.sizeHintForRow(0) * zeilen
        self.flaechen_liste.setFixedHeight(hoehe + 2 * self.flaechen_liste.frameWidth() + 4)
        rundum = not self.flaechen()
        self.flaechen_text.setText(tr("va.flaechen.alle") if rundum else tr("va.flaechen.nur"))
        self._farben_zeigen(farben)

    def _farben_zeigen(self, farben):
        """Färbt die Flächen des Teils im Job: `farben` Nummer → „#rrggbb“, die anderen, wie sie
        waren. Nur die Anzeige – _farben_zurueck() stellt sie wieder her; ohne Farben gleich."""
        if not farben or self.job is None:
            self._farben_zurueck()
            return
        klon = vr.modell(self.job)
        ansicht = klon.ViewObject
        if stl_anzeige.als_netz(klon):  # ein Teil aus einem STL: das Netz trägt die Farben
            stl_anzeige.flaechen_faerben(klon, farben)
            self._farben_vorher = (klon, None, None)
            return
        if ansicht is None:
            return
        if not hasattr(ansicht, "DiffuseColor"):  # 26.3: ein Material je Fläche
            if not hasattr(ansicht, "ShapeAppearance"):
                return
            if self._farben_vorher is None:
                self._farben_vorher = (klon, None, list(ansicht.ShapeAppearance))
            gui_zeigen.flaechen_material(
                ansicht, ft.anzahl(klon.Shape), self._farben_vorher[2], farben
            )
            return
        if self._farben_vorher is None:
            aussehen = getattr(ansicht, "ShapeAppearance", None)
            self._farben_vorher = (
                klon,
                list(ansicht.DiffuseColor),
                list(aussehen) if aussehen is not None else None,
            )
        grund = self._farben_vorher[1]
        anzahl = ft.anzahl(klon.Shape)
        if len(grund) != anzahl:
            grund = [tuple(grund[0]) if grund else tuple(ansicht.ShapeColor)] * anzahl
        alpha = grund[0][3] if grund and len(grund[0]) > 3 else 0.0
        neu = list(grund)
        for nummer, farbe in farben.items():
            if nummer < anzahl:
                neu[nummer] = (*(int(farbe[i : i + 2], 16) / 255 for i in (1, 3, 5)), alpha)
        ansicht.DiffuseColor = neu

    def _farben_zurueck(self):
        """Die Flächen des Teils wieder in ihren eigenen Farben."""
        if self._farben_vorher is None:
            return
        klon, farben, aussehen = self._farben_vorher
        self._farben_vorher = None
        try:
            ansicht = klon.ViewObject
            if ansicht is None:
                return
            if farben is None and aussehen is None:  # das Netz (stl_anzeige)
                stl_anzeige.flaechen_faerben(klon, {})
                return
            if aussehen is not None:
                ansicht.ShapeAppearance = aussehen
            else:
                ansicht.DiffuseColor = farben
        except (ReferenceError, RuntimeError):  # das Teil ist schon weg (Abbrechen)
            pass

    def _eintauchwinkel(self):
        """So steil taucht das Schruppen zwischen gewählten Flächen ein: der Eintauchwinkel des
        Fräsers aus der Werkzeugverwaltung, ohne Angabe der Vorschlag (Grad)."""
        return self._eintauchwinkel_fuer(self.fraeser())

    @staticmethod
    def _eintauchwinkel_fuer(werkzeug):
        """Der Eintauchwinkel von `werkzeug` aus der Werkzeugverwaltung (Grad), ohne Angabe
        oder ohne Werkzeug der Vorschlag."""
        if werkzeug is not None and werkzeug.eintauchwinkel > 0:
            return werkzeug.eintauchwinkel
        return vb.EINTAUCHWINKEL

    # --- Rundum schlichten (V5d) ---------------------------------------------------------

    def _hat_schlichten(self, werkzeug, werkstoff):
        """Hat der Fräser für den Werkstoff einen Einsatz „Schlichten“ mit Schnittwerten?"""
        return any(e.art == wz.SCHLICHTEN for e in self._passende_einsaetze(werkzeug, werkstoff))

    def _schlichtfraeser_fuellen(self):
        """Die Fräser, deren Form das Addon kennt (fraeserform), mit Schnittwerten für den
        Werkstoff; vorgewählt der bisher gewählte, beim Ändern der der Operation, sonst der
        zuletzt benutzte, sonst einer mit Einsatz „Schlichten“ – Kugel vor Torus vor den
        anderen."""
        werkstoff = self.werkstoff()
        vorher = self.schlichtfraeser()
        self._schlichtfraeser = [
            w
            for w in self._sortiert()
            if w.durchmesser > 0
            and ff.von_werkzeug(w) is not None
            and self._passende_einsaetze(w, werkstoff)
        ]
        kennungen = [w.kennung for w in self._schlichtfraeser]
        gemerkt = _parameter().GetString(GEMERKT_SCHLICHTFRAESER, "")
        if vorher is not None and vorher.kennung in kennungen:
            wahl = kennungen.index(vorher.kennung)
        elif self._vorwahl_schlichten in kennungen:  # beim Ändern: der Fräser der Operation
            wahl = kennungen.index(self._vorwahl_schlichten)
        elif gemerkt in kennungen and self._im_magazin(gemerkt):
            wahl = kennungen.index(gemerkt)
        else:
            rang = {wz.KUGELFRAESER: 0, wz.TORUSFRAESER: 1}
            wahl = min(
                range(len(self._schlichtfraeser)),
                key=lambda i: (
                    not self._hat_schlichten(self._schlichtfraeser[i], werkstoff),
                    rang.get(self._schlichtfraeser[i].art, 2),
                    i,
                ),
                default=0,
            )
        self._fuellt = True
        try:
            self.wahl_schlichtfraeser.clear()
            for werkzeug in self._schlichtfraeser:
                self.wahl_schlichtfraeser.addItem(self._zeile(werkzeug))
            if self._schlichtfraeser:
                self.wahl_schlichtfraeser.setCurrentIndex(wahl)
        finally:
            self._fuellt = False
        self._schlichteinsatz_fuellen()

    def schlichtfraeser(self):
        """Der gewählte Fräser fürs Schlichten (werkzeuge.Werkzeug) oder None."""
        i = self.wahl_schlichtfraeser.currentIndex()
        return self._schlichtfraeser[i] if 0 <= i < len(self._schlichtfraeser) else None

    def _schlichtfraeser_gewaehlt(self):
        if not self._fuellt:
            self._schlichteinsatz_fuellen()

    def _schlichteinsatz_fuellen(self):
        """Die Einsätze des Schlichtfräsers; vorgewählt „Schlichten“, beim Ändern der, mit dem
        der Controller gesetzt ist."""
        werkzeug = self.schlichtfraeser()
        self._schlichteinsaetze = (
            self._passende_einsaetze(werkzeug, self.werkstoff()) if werkzeug is not None else []
        )
        arten = [e.art for e in self._schlichteinsaetze]
        wahl = arten.index(wz.SCHLICHTEN) if wz.SCHLICHTEN in arten else 0
        if (
            self._art == SCHLICHTEN
            and self._tc_vorher is not None
            and werkzeug is not None
            and werkzeug.kennung == self._vorwahl_schlichten
        ):
            gemerkt = js.vorgeschlagener_einsatz(self._tc_vorher, self._schlichteinsaetze, self.job)
            wahl = gemerkt if gemerkt >= 0 else wahl
        self._fuellt = True
        try:
            self.wahl_schlichteinsatz.clear()
            for einsatz in self._schlichteinsaetze:
                self.wahl_schlichteinsatz.addItem(wz.einsatz_name(einsatz))
            if self._schlichteinsaetze:
                self.wahl_schlichteinsatz.setCurrentIndex(wahl)
        finally:
            self._fuellt = False
        self._schlichteinsatz_gewaehlt()

    def schlichteinsatz(self):
        """Der gewählte Einsatz fürs Schlichten (werkzeuge.Einsatz) oder None."""
        i = self.wahl_schlichteinsatz.currentIndex()
        return self._schlichteinsaetze[i] if 0 <= i < len(self._schlichteinsaetze) else None

    def _schlichteinsatz_gewaehlt(self):
        """Drehzahl und Vorschub, die Schrittweite aus der Werkzeugtabelle als Vorschlag."""
        if self._fuellt:
            return
        werkzeug, einsatz = self.schlichtfraeser(), self.schlichteinsatz()
        self.schnittwerte_schlichten.setText(self._schnittwerte_text(werkzeug, einsatz))
        for feld, eingabe in self.felder_schlichten.items():
            eingabe.setPlaceholderText(
                groesse_zeigen(self._vorschlag(feld), einheiten.LAENGE) or "0"
            )
        self._querachse_vorschlagen()
        self._vorschau_starten()

    def _schruppen_da(self):
        """Gibt es vor dem Schlichten ein Schruppen – angehakt oder schon im Job?"""
        if self.mit_schruppen.isChecked():
            return True
        return self.job is not None and any(vo.ist_schruppen(o) for o in js.operationen(self.job))

    def _schlicht_argumente(self):
        """Die Argumente für die grobe Schlichtbahn (vierachs_vorschau.schlichten, nach Dokument
        und Job) für Umdrehungen und Zeit – die Kammhöhe steht danach im Fenster. ValueError mit
        einem Satz, wenn es nicht geht."""
        werkzeug = self.schlichtfraeser()
        if not self._schruppen_da():
            raise ValueError(tr("vs.fehler.ohne_schruppen"))
        form = ff.von_werkzeug(werkzeug)
        schrittweite = self._wert("schrittweite")
        self._kammhoehe_zeigen()
        achse = self.achse()
        return (
            tuple(achse.laengs),
            tuple(va.radial(achse)),
            form,
            schrittweite,
            self._wert("aufmass_schlichten"),
            (
                self._ueberlauf_fuer(werkzeug),
                self._wert("abstand_futter"),
                self._wert("sicherheit"),
            ),
            self._halter_fuer(werkzeug),
            self._schlicht_flaechen(),
            self.muster(),
        ), {
            "nur_gleichlauf": self.linien_nur_gleichlauf.isChecked(),
            "querachse": self.querachse(),
            "anstellen": self.anstellen(),
            "stetig": self.stetig(),
        }

    def _schlicht_text(self, bahn):
        """„→ 290 Umdrehungen, etwa 56 min“ (bei Linien längs „→ 126 Linien längs, …“) – und
        was hinten nicht erreicht wird."""
        from .reichweite import weg_text

        _n, vorschub, _senkrecht = js.werte_im_job(
            self.schlichtfraeser(), self.schlichteinsatz(), self.job
        )
        zeit = (
            _zeit_text(
                vb.dauer(
                    bahn,
                    vorschub,
                    freivorschub=self._freivorschub(),
                    fraeser_radius=_radius(self.schlichtfraeser()),
                )
            )
            if vorschub > 0
            else "?"
        )
        if bahn.linien:
            text = tr("va.schlichten.ergebnis_linien", linien=f"{bahn.linien}", zeit=zeit)
        elif getattr(bahn, "wendel_bahnen", 0):
            text = tr("va.schlichten.ergebnis_wendel", bahnen=f"{bahn.wendel_bahnen}", zeit=zeit)
        else:
            text = tr("va.schlichten.ergebnis", umdrehungen=f"{bahn.umdrehungen:.0f}", zeit=zeit)
        if bahn.hinten_frei > 0:
            text += " " + tr("vb.hinten_frei", laenge=weg_text(bahn.hinten_frei))
        return text

    # --- Plan indexiert (V4c) -------------------------------------------------------------

    def _planfraeser_fuellen(self):
        """Die Fräser mit ebener Stirn (vierachs_planbahn.ebener_radius) mit Schnittwerten für
        den Werkstoff; vorgewählt der von Hand gewählte, beim Ändern der der Operation, sonst der
        Fräser des Schruppens (Manuel, 2026-10-11, Frage 10: „der fräser vom schruppen“), sonst
        der bisher gewählte, sonst der zuletzt benutzte, sonst einer mit Einsatz „Planen“, sonst
        ein Schaftfräser."""
        werkstoff = self.werkstoff()
        vorher = self.planfraeser()
        self._planfraeser = [
            w
            for w in self._sortiert()
            if w.durchmesser > 0
            and (self._ebene_stirn(w) or vplan.bohrer_von(w))
            and self._passende_einsaetze(w, werkstoff)
        ]
        kennungen = [w.kennung for w in self._planfraeser]
        gemerkt = _parameter().GetString(GEMERKT_PLANFRAESER, "")
        schrupp = self.fraeser() if self.mit_schruppen.isChecked() else None
        if self._planfraeser_von_hand and vorher is not None and vorher.kennung in kennungen:
            wahl = kennungen.index(vorher.kennung)
        elif self._vorwahl_plan in kennungen:  # beim Ändern: der Fräser der Operation
            wahl = kennungen.index(self._vorwahl_plan)
        elif schrupp is not None and schrupp.kennung in kennungen and not vplan.bohrer_von(schrupp):
            wahl = kennungen.index(schrupp.kennung)
        elif vorher is not None and vorher.kennung in kennungen:
            wahl = kennungen.index(vorher.kennung)
        elif gemerkt in kennungen and self._im_magazin(gemerkt):
            wahl = kennungen.index(gemerkt)
        else:
            wahl = min(
                range(len(self._planfraeser)),
                key=lambda i: (
                    vplan.bohrer_von(self._planfraeser[i]) is not None,
                    not self._hat_einsatz(self._planfraeser[i], werkstoff, wz.PLANEN),
                    self._planfraeser[i].art != wz.SCHAFTFRAESER,
                    i,
                ),
                default=0,
            )
        self._fuellt = True
        try:
            self.wahl_planfraeser.clear()
            for werkzeug in self._planfraeser:
                self.wahl_planfraeser.addItem(self._zeile(werkzeug))
            if self._planfraeser:
                self.wahl_planfraeser.setCurrentIndex(wahl)
        finally:
            self._fuellt = False
        self._planeinsatz_fuellen()

    @staticmethod
    def _ebene_stirn(werkzeug):
        """Hat der Fräser eine ebene Stirn (Schaft-, Torus-, Planfräser)?"""
        form = ff.von_werkzeug(werkzeug)
        return form is not None and vp.ebener_radius(form) > 0

    def _hat_einsatz(self, werkzeug, werkstoff, art):
        """Hat der Fräser für den Werkstoff einen Einsatz der Art `art` mit Schnittwerten?"""
        return any(e.art == art for e in self._passende_einsaetze(werkzeug, werkstoff))

    def planfraeser(self):
        """Der gewählte Fräser für Plan indexiert (werkzeuge.Werkzeug) oder None."""
        i = self.wahl_planfraeser.currentIndex()
        return self._planfraeser[i] if 0 <= i < len(self._planfraeser) else None

    def _planfraeser_gewaehlt(self):
        if not self._fuellt:
            self._planfraeser_von_hand = True
            self._planeinsatz_fuellen()
            self._plan_vorschlagen()  # der Bohrer daneben nur zu einem Fräser

    def planbohrer(self):
        """(Durchmesser, Spitzenwinkel), wenn bei Plan indexiert ein Bohrer gewählt ist – er
        bohrt die Querbohrungen radial (vierachs_plan.bohrer_von) –, sonst None."""
        return vplan.bohrer_von(self.planfraeser())

    def bohrer_dazu(self):
        """Der Bohrer, der neben dem Fräser von „Plan indexiert“ die gewählten Querbohrungen
        bohrt – eine eigene Operation „Radial bohren“ (werkzeuge.Werkzeug) –, oder None: Der
        Haken ist aus oder nicht da, oder bei „Fräser“ steht selbst ein Bohrer."""
        if self._planbohrer is None or self.mit_planbohrer.isHidden():
            return None
        if not self.mit_planbohrer.isChecked() or self.planbohrer() is not None:
            return None
        return self._planbohrer

    def _planbohrer_umgeschaltet(self):
        if not self._fuellt:
            self._planbohrer_von_hand = True
            self._vorschau_starten()

    def _planbohrer_dazu(self, paare, sonst):
        """Sind neben Querbohrungen (`paare`) auch Flächen oder Nuten gewählt (`sonst`) und
        fräst sie ein Fräser, bietet der Haken „Die Bohrungen mit … bohren“ einen Bohrer an, der
        sie alle bohrt – angehakt, solange man ihn nicht von Hand abgewählt hat: bohren ist
        schneller als fräsen. Sonst verschwindet er."""
        bohrer = None
        if paare and sonst and self.planbohrer() is None:
            bohrer = next(
                (w for w in self._planfraeser if vp.bohrer_passt(paare, vplan.bohrer_von(w))),
                None,
            )
        self._planbohrer = bohrer
        vorher = self._fuellt
        self._fuellt = True
        try:
            if bohrer is not None:
                self.mit_planbohrer.setText(
                    tr(
                        "va.plan.mit_bohrer",
                        bohrer=self._zeile(bohrer),
                    )
                )
                if not self._planbohrer_von_hand:
                    self.mit_planbohrer.setChecked(True)
            self.mit_planbohrer.setVisible(bohrer is not None)
        finally:
            self._fuellt = vorher

    def _bohrnamen(self):
        """Die Namen der gewählten Flächen, die Querbohrungen sind."""
        if self.job is None:
            return []
        achse = self.achse()
        form = vr.modell(self.job).Shape
        paare = vp.bohrungen(form, achse.laengs, va.radial(achse), self.flaechen())
        return list(dict.fromkeys(e.name for e, _b in paare))

    def _bohreinsatz(self, werkzeug):
        """Der Einsatz des Bohrers: „Bohren“, sonst der erste mit Schnittwerten."""
        einsaetze = self._passende_einsaetze(werkzeug, self.werkstoff())
        return next(
            (e for e in einsaetze if e.art == wz.BOHREN), einsaetze[0] if einsaetze else None
        )

    def _bohrer_dazu_anlegen(self, achse, quer_auf_null, loecher):
        """Legt neben „Plan indexiert“ die Operation „Radial bohren“ mit dem Bohrer daneben
        (bohrer_dazu) über die Querbohrungen `loecher` an – ohne eigene Transaktion."""
        bohrer = self.bohrer_dazu()
        tc = js.controller_ohne_transaktion(
            self.doc,
            self.job,
            bohrer,
            self._bohreinsatz(bohrer),
            self.werkstoff(),
            self._programmnummer(bohrer),
        )
        sicherheit, _ueberlauf, abstand = self._abstaende()
        return vplan.lege_an(
            self.job,
            tc,
            achse,
            self._wert("zustellung_plan"),
            self._wert("zeilenabstand"),
            self._wert("aufmass_plan"),
            quer_auf_null=quer_auf_null,
            abstaende=(self._ueberlauf_fuer(bohrer), abstand, sicherheit),
            halter=self._halter_fuer(bohrer),
            flaechen=loecher,
        )

    def _plan_namen(self):
        """Die Flächen, auf die „Plan indexiert“ schaut: die gewählten – oder rundum (alle
        Mantelflächen) mit einer Achse quer zur Stange die ebenen Mantelflächen, auch schräg zur
        Achse (P-2026-10-03-09; Manuel: „die Maschine hat eine Y-Achse … den Winkel richtig
        stellen und die Y-Achse verfahren“)."""
        if stl_teil.aus_stl(self.teil):
            return []  # nur Dreiecke, jedes eben – keine Abflachung, die Plan indexiert fräst
        flaechen = self.flaechen()
        if flaechen or self.job is None or not self.achse().quer:
            return flaechen
        achse = self.achse()
        form = vr.modell(self.job).Shape
        mantel = set(vf.namen(vf.mantelflaechen(self._sicht())))
        # Dazu die Ebenen zur Achse hin, vor denen frei ist (Frage 10: die Unterseite der Nase) –
        # von außen sieht man sie nicht, unter den Mantelflächen sind sie nicht.
        alle = [f"Face{i + 1}" for i in range(ft.anzahl(form))]
        return [
            e.name
            for e in vp.ebenen(form, achse.laengs, va.radial(achse), alle)
            if e.name in mantel or e.hoechste <= vp.GERADE
        ]

    def _schlicht_flaechen(self):
        """Die Flächen für „Rundum schlichten“: die gewählten ohne die, die „Plan indexiert“
        fertig macht (W-027; Manuel, 2026-10-17: „wichtig ist, dass danach die Kugel nicht
        nochmal alles das fährt, was schon weg ist“) – bleibt keine, die gewählten (der Haken geht
        dann aus, _schlichten_vorschlagen); rundum mit „Plan indexiert“ für die ebenen
        Mantelflächen alle anderen Mantelflächen (sonst führe die Spirale die ebenen noch
        einmal)."""
        flaechen = self.flaechen()
        if not self.plan_an() or self.job is None:
            return flaechen
        if flaechen:
            return self._kugel_uebrig() or flaechen
        eben = set(self._plan_namen())
        if not eben:
            return flaechen
        mantel = vf.namen(vf.mantelflaechen(self._sicht()))
        return [f for f in mantel if f not in eben]

    def _kugel_uebrig(self):
        """Mit gewählten Flächen und „Plan indexiert“ an: die Flächen, die der Kugel bleiben –
        ohne die ebenen, die Bohrungen und die Nuten auf dem Mantel, die Plan indexiert fertig
        macht (an der Nase: die schrägen Flächen oben und unten; Seiten und Spitze nicht)."""
        flaechen = self.flaechen()
        if not flaechen or not self.plan_an() or self.job is None:
            return flaechen
        fertig = {e.name for e in self._plan_ebenen()}
        return [f for f in flaechen if f not in fertig]

    def _schlichten_vorschlagen(self):
        """Der Haken „Rundum schlichten“ neben „Plan indexiert“ (W-027): Macht Plan indexiert
        alle gewählten Flächen fertig, geht er aus – solange man ihn nicht von Hand gesetzt hat –
        und der Satz darunter sagt es; bleiben Flächen für die Kugel, stehen sie darunter. Beim
        Ändern einer Operation bleibt er, wie er ist."""
        if self.job is None or self.zu_aendern is not None or not self._schlichten_vorgewaehlt:
            return
        flaechen = self.flaechen()
        text, an = tr("va.schlichten.text"), self._schlichten_vorschlag
        if flaechen and self.plan_an():
            uebrig = self._kugel_uebrig()
            fertig = ", ".join(f for f in flaechen if f not in uebrig)
            if fertig and uebrig:
                text += " " + tr("va.schlichten.ohne_plan", uebrig=", ".join(uebrig), fertig=fertig)
            elif fertig:
                text, an = tr("va.schlichten.plan_alles", flaechen=fertig), False
        self.erklaerung_schlichten.setText(text)
        if not self._schlichten_von_hand and self.mit_schlichten.isEnabled():
            self._schlichten_setzen(an)

    def _schlichten_setzen(self, an):
        """Setzt den Haken „Rundum schlichten“ als Vorschlag – zählt nicht als von Hand."""
        self._schlichten_selbst = True
        try:
            self.mit_schlichten.setChecked(bool(an))
        finally:
            self._schlichten_selbst = False

    def _plan_flaechen(self):
        """(Flächen für „Plan indexiert“, Flächen für den Bohrer daneben – oder None)."""
        flaechen = self._plan_namen()
        if self.bohrer_dazu() is None:
            return flaechen, None
        loecher = self._bohrnamen()
        return [f for f in flaechen if f not in loecher], loecher

    def _planbohrer_vorschlagen(self, paare, nur_bohrungen):
        """Sind nur Querbohrungen gewählt und bohrt ein Bohrer der Liste sie alle, ist er
        vorgewählt (bohren geht schneller als fräsen); sonst wieder der Fräser – solange man
        das Werkzeug nicht von Hand gewählt hat. Gibt den vorgeschlagenen Bohrer zurück."""
        bohrer = next(
            (
                w
                for w in self._planfraeser
                if nur_bohrungen and vp.bohrer_passt(paare, vplan.bohrer_von(w))
            ),
            None,
        )
        if self._planfraeser_von_hand or self._art == PLAN:
            return bohrer
        jetzt = self.planfraeser()
        if bohrer is not None:
            ziel = bohrer
        elif jetzt is not None and vplan.bohrer_von(jetzt):
            ziel = next((w for w in self._planfraeser if not vplan.bohrer_von(w)), None)
        else:
            ziel = None
        if ziel is not None and ziel is not jetzt:
            self._fuellt = True
            try:
                self.wahl_planfraeser.setCurrentIndex(self._planfraeser.index(ziel))
            finally:
                self._fuellt = False
            self._planeinsatz_fuellen()
        return bohrer

    def _planeinsatz_fuellen(self):
        """Die Einsätze des Fräsers; vorgewählt „Planen“, sonst „Schruppen“, sonst „Schlichten“;
        beim Ändern der, mit dem der Controller gesetzt ist."""
        werkzeug = self.planfraeser()
        self._planeinsaetze = (
            self._passende_einsaetze(werkzeug, self.werkstoff()) if werkzeug is not None else []
        )
        arten = [e.art for e in self._planeinsaetze]
        wahl = next(
            (arten.index(a) for a in (wz.PLANEN, wz.SCHRUPPEN, wz.SCHLICHTEN) if a in arten), 0
        )
        if (
            self._art == PLAN
            and self._tc_vorher is not None
            and werkzeug is not None
            and werkzeug.kennung == self._vorwahl_plan
        ):
            gemerkt = js.vorgeschlagener_einsatz(self._tc_vorher, self._planeinsaetze, self.job)
            wahl = gemerkt if gemerkt >= 0 else wahl
        self._fuellt = True
        try:
            self.wahl_planeinsatz.clear()
            for einsatz in self._planeinsaetze:
                self.wahl_planeinsatz.addItem(wz.einsatz_name(einsatz))
            if self._planeinsaetze:
                self.wahl_planeinsatz.setCurrentIndex(wahl)
        finally:
            self._fuellt = False
        self._planeinsatz_gewaehlt()

    def planeinsatz(self):
        """Der gewählte Einsatz für Plan indexiert (werkzeuge.Einsatz) oder None."""
        i = self.wahl_planeinsatz.currentIndex()
        return self._planeinsaetze[i] if 0 <= i < len(self._planeinsaetze) else None

    def _planeinsatz_gewaehlt(self):
        """Drehzahl und Vorschub, die Vorschläge in die Felder."""
        if self._fuellt:
            return
        werkzeug, einsatz = self.planfraeser(), self.planeinsatz()
        self.schnittwerte_plan.setText(self._schnittwerte_text(werkzeug, einsatz))
        self._schaft_zeigen()
        bohrer = vplan.bohrer_von(werkzeug)
        for feld, eingabe in self.felder_plan.items():
            eingabe.setPlaceholderText(
                groesse_zeigen(self._vorschlag(feld), einheiten.LAENGE) or "0"
            )
            eingabe.setEnabled(not bohrer)  # der Bohrer braucht weder Lagen noch Zeilen
        self._vorschau_starten()

    def plan_an(self):
        """Ist „Plan indexiert“ angehakt? Geht es nicht, nimmt _plan_vorschlagen den Haken
        heraus; beim Ändern der Operation ist er gesetzt und gesperrt."""
        return self.mit_plan.isChecked()

    def _plan_umgeschaltet(self, an):
        if not self._fuellt:
            self._plan_von_hand = True
        if self.job is not None:
            self._schlichten_vorschlagen()  # was Plan indexiert fertig macht, fährt die Kugel nicht
            self._muster_vorschlagen()
            self._querachse_vorschlagen()  # rundum oder nur die übrigen Flächen (Frage 12)
        self.planfelder.setEnabled(an)
        self.planfelder.setVisible(an)
        self.ergebnis_plan.setVisible(an)
        self._umgeschaltet()

    def _plan_ebenen(self):
        """[vierachs_planbahn.Ebene, …] – die gewählten ebenen Flächen längs der Stange, die
        gewählten Bohrungen quer zu ihr (je Seite eine) und die Nuten auf dem Mantel
        (vierachs_planbahn.Mantelnut) – alle mit ihrem Namen."""
        flaechen = self._plan_namen()
        if not flaechen or self.job is None:
            return []
        achse = self.achse()
        form = vr.modell(self.job).Shape
        laengs, radial = achse.laengs, va.radial(achse)
        ebenen = vp.ebenen(form, laengs, radial, flaechen)
        bohrungen = [e for e, _b in vp.bohrungen(form, laengs, radial, flaechen)]
        return ebenen + bohrungen + vp.mantelnuten(form, laengs, radial, flaechen)

    def _plan_vorschlagen(self):
        """Ob „Plan indexiert“ geht – gewählte ebene Flächen längs der Stange und an der
        Maschine eine Achse quer dazu (bei C das Y) – und der Vorschlag mit Grund (W-006 E5):
        angehakt, wenn es geht und man es nicht von Hand abgewählt hat; der Satz darunter sagt,
        warum – oder warum nicht. Beim Ändern bleibt der Haken, wie er ist."""
        if self.job is None or self._art == PLAN:
            return
        ebenen = self._plan_ebenen()
        achse = self.achse()
        self._planbohrer_dazu([], False)  # der Bohrer daneben nur, wenn es unten passt
        if not ebenen and stl_teil.aus_stl(self.teil):
            geht, grund = False, tr("va.plan.stl")
        elif not ebenen:
            geht, grund = False, tr("va.plan.keine_ebene")
        elif not achse.quer:
            geht, grund = False, tr("va.plan.keine_querachse", maschine=achse.maschine)
        elif not self._planfraeser:
            namen = ", ".join(e.name for e in ebenen)
            geht, grund = True, tr("va.plan.kein_fraeser", flaechen=namen)
        else:
            namen = ", ".join(dict.fromkeys(e.name for e in ebenen))
            form = vr.modell(self.job).Shape
            laengs, radial = achse.laengs, va.radial(achse)
            namen_plan = self._plan_namen()
            eben = vp.ebenen(form, laengs, radial, namen_plan)
            mantel = vp.mantelnuten(form, laengs, radial, namen_plan)
            paare = vp.bohrungen(form, laengs, radial, namen_plan)
            nur_bohrungen = bool(paare) and not eben and not mantel
            bohrer = self._planbohrer_vorschlagen(paare, nur_bohrungen)
            self._planbohrer_dazu(paare, bool(eben or mantel))
            if bohrer is not None:
                geht, grund = True, tr(
                    "va.plan.vorschlag_bohren",
                    flaechen=namen,
                    bohrer=self._zeile(bohrer),
                )
            elif nur_bohrungen:
                geht, grund = True, tr("va.plan.vorschlag_bohrung", flaechen=namen)
            elif mantel and not eben and not paare:
                geht, grund = True, tr("va.plan.vorschlag_mantel", flaechen=namen)
            elif paare or mantel:
                geht, grund = True, tr("va.plan.vorschlag_gemischt", flaechen=namen)
            elif not self.flaechen():  # rundum: ein Angebot, kein Haken von selbst
                schraeg = [e for e in eben if e.steigung]
                grund = tr("va.plan.vorschlag_rundum", flaechen=namen)
                if schraeg:
                    grund += " " + tr(
                        "va.plan.schraeg",
                        flaeche=schraeg[0].name,
                        winkel=dezimal(f"{schraeg[0].neigung:.1f}"),
                    )
                geht = True
            else:
                geht, grund = True, tr("va.plan.vorschlag", flaechen=namen)
        geht = geht and self._plan_erlaubt
        self.plan_grund.setText(grund)
        war = self.plan_an()
        vorher = self._fuellt
        self._fuellt = True
        try:
            self.mit_plan.setEnabled(geht)
            if not geht:
                self.mit_plan.setChecked(False)
            elif not self._plan_von_hand and self.zu_aendern is None:
                # Auch rundum vorbelegt an (Manuel, 2026-10-11, Frage 10: der Schruppfräser macht
                # die ebenen Flächen, die Kugel den Rest) – bis dahin nur angeboten.
                self.mit_plan.setChecked(bool(self._planfraeser))
        finally:
            self._fuellt = vorher
        self.planfelder.setEnabled(self.plan_an())
        self.planfelder.setVisible(self.plan_an())
        self.ergebnis_plan.setVisible(self.plan_an())
        self._schaft_zeigen()
        if self.plan_an() != war:
            self._umgeschaltet()

    def _schaft_zeigen(self):
        """Der Haken „Seiten mit dem Schaft“: frei, wenn unter den Flächen von „Plan indexiert“
        eine Seite ist, bis zu deren Unterkante der Fräser hinunterreicht – Schneide und Hals
        (vierachs_planbahn.schaft_lage, vierachs_plan.reicht_hinab);
        grau darunter, welche mit dem Schaft gehen und welche bei der Stirn bleiben."""
        werkzeug = self.planfraeser()
        seiten = []  # (Name, so lang muss die Schneide sein)
        if self.job is not None and werkzeug is not None and not vplan.bohrer_von(werkzeug):
            achse = self.achse()
            form = vr.modell(self.job).Shape
            laengs, radial = achse.laengs, va.radial(achse)
            radius = self.stange().durchmesser / 2
            for ebene in vp.ebenen(form, laengs, radial, self._plan_namen()):
                lage = vp.schaft_lage(form, ebene, laengs, radial, radius)
                if lage is not None:
                    seiten.append((ebene.name, lage[2]))
        # So tief reicht er hinunter: Schneide und Hals (die Auskragung N; vierachs_plan.reicht)
        schneide = (
            vplan.reicht_werkzeug(werkzeug, self._wert("zustellung_plan"))
            if werkzeug is not None
            else 0.0
        )
        geht = [n for n, weg in seiten if schneide > 0 and weg <= schneide]
        zu_kurz = [(n, weg) for n, weg in seiten if not (schneide > 0 and weg <= schneide)]
        saetze = []
        if not seiten:
            saetze.append(tr("va.plan.schaft.keine"))
        if geht:
            saetze.append(tr("va.plan.schaft.geht", flaechen=", ".join(geht)))
        if zu_kurz:
            braucht = einheiten.text(max(weg for _n, weg in zu_kurz), einheiten.LAENGE, 1)
            if schneide > 0:
                saetze.append(
                    tr(
                        "va.plan.schaft.zu_kurz",
                        flaechen=", ".join(n for n, _w in zu_kurz),
                        werkzeug=f"T{werkzeug.nummer}",
                        schneide=einheiten.text(schneide, einheiten.LAENGE, 1),
                        braucht=braucht,
                    )
                )
            else:
                saetze.append(
                    tr(
                        "va.plan.schaft.ohne_schneide",
                        flaechen=", ".join(n for n, _w in zu_kurz),
                        werkzeug=f"T{werkzeug.nummer}",
                        braucht=braucht,
                    )
                )
        vorher = self._fuellt
        self._fuellt = True
        try:
            self.plan_schaft.setEnabled(bool(geht))
            if not geht:
                self.plan_schaft.setChecked(False)
        finally:
            self._fuellt = vorher
        self.plan_schaft_grund.setText(" ".join(saetze))

    def plan_schaft_an(self):
        """Die Seiten mit dem Schaft (angehakt und möglich)?"""
        return self.plan_schaft.isEnabled() and self.plan_schaft.isChecked()

    def plan_weg(self):
        """Der Weg über den ebenen Flächen (vierachs_planbahn.WEG_…)."""
        return self.wahl_plan_weg.currentData() or vp.WEG_ZEILEN

    def _plan_weg_gewaehlt(self):
        """„Nur Gleichlauf“ gilt nur für die Zeilen; die Stiche wählen ihn selbst."""
        self.plan_nur_gleichlauf.setEnabled(self.plan_weg() == vp.WEG_ZEILEN)
        self._vorschau_starten()

    def _plan_argumente(self):
        """{"plan": Argumente, "planbohren": Argumente} für die grobe Bahn „Plan indexiert“
        (vierachs_vorschau.plan) für Lagen, Zeilen und Zeit – „planbohren“ nur mit dem Bohrer
        für die Querbohrungen daneben."""
        werkzeug = self.planfraeser()
        flaechen, loecher = self._plan_flaechen()
        argumente = {"plan": self._plan_argumente_mit(werkzeug, flaechen)}
        if loecher:
            argumente["planbohren"] = self._plan_argumente_mit(self.bohrer_dazu(), loecher)
        return argumente

    def _plan_argumente_mit(self, werkzeug, flaechen):
        """Die Argumente für vierachs_vorschau.plan mit `werkzeug` (Fräser oder Bohrer) über
        `flaechen`."""
        achse = self.achse()
        bohrer = vplan.bohrer_von(werkzeug)
        return (
            tuple(achse.laengs),
            tuple(va.radial(achse)),
            vplan.form_des_bohrers(bohrer) if bohrer else ff.von_werkzeug(werkzeug),
            self._wert("zustellung_plan"),
            self._wert("zeilenabstand"),
            self._wert("aufmass_plan"),
            (
                self._ueberlauf_fuer(werkzeug),
                self._wert("abstand_futter"),
                self._wert("sicherheit"),
            ),
            self._halter_fuer(werkzeug),
            flaechen,
            self._eintauchwinkel_fuer(werkzeug),
            bohrer,
        ), {
            "nur_gleichlauf": self.plan_nur_gleichlauf.isChecked(),
            "weg": self.plan_weg(),
            "schaft": self.plan_schaft_an() and not bohrer,
            "schneide": vplan.reicht_werkzeug(werkzeug, self._wert("zustellung_plan")),
            "schrupp": self._plan_schrupp(),
        }

    def _plan_schrupp(self):
        """Wovon die Vorschau von „Plan indexiert“ ausgeht (vierachs_vorschau.plan): vom Schruppen,
        das der Assistent anlegt (seine Argumente), von dem im Job ("job") – oder von der Stange
        (None)."""
        if self.mit_schruppen.isChecked() and self.fraeser() is not None:
            try:
                return self._schrupp_argumente()
            except ValueError:
                return None
        if self.job is not None and any(vo.ist_schruppen(o) for o in js.operationen(self.job)):
            return "job"
        return None

    def _plan_text(self, bahn):
        """„→ 2 Lagen, 6 Zeilen, etwa 1 min“ – bei mehreren Flächen mit ihrer Zahl, und was
        hinten nicht erreicht wird."""
        from .reichweite import weg_text

        _n, vorschub, _senkrecht = js.werte_im_job(self.planfraeser(), self.planeinsatz(), self.job)
        zeit = (
            _zeit_text(
                vb.dauer(
                    bahn,
                    vorschub,
                    freivorschub=self._freivorschub(),
                    fraeser_radius=_radius(self.planfraeser()),
                )
            )
            if vorschub > 0
            else "?"
        )
        if getattr(bahn, "seiten", 0):
            n = bahn.bohrungen
            text = tr(
                "va.plan.ergebnis_bohren",
                bohrungen=tr("va.plan.bohrung") if n == 1 else tr("va.plan.bohrungen_zahl", n=n),
                seiten=(
                    tr("va.plan.seite") if bahn.seiten == 1 else tr("va.plan.seiten", n=bahn.seiten)
                ),
                huebe=tr("va.plan.hub") if bahn.huebe == 1 else tr("va.plan.huebe", n=bahn.huebe),
                zeit=zeit,
            )
            achse = self.achse()
            form = vr.modell(self.job).Shape
            laengs, radial = achse.laengs, va.radial(achse)
            if vp.ebenen(form, laengs, radial, self.flaechen()) or vp.mantelnuten(
                form, laengs, radial, self.flaechen()
            ):
                text += " " + tr("va.plan.nur_bohrungen")
            return text
        stiche = self.plan_weg() != vp.WEG_ZEILEN
        if bahn.flaechen > 1 and stiche:
            text = tr(
                "va.plan.ergebnis_flaechen_stiche",
                flaechen=bahn.flaechen,
                lagen=bahn.lagen,
                zeilen=bahn.zeilen,
                zeit=zeit,
            )
        elif bahn.flaechen > 1:
            text = tr(
                "va.plan.ergebnis_flaechen",
                flaechen=bahn.flaechen,
                lagen=bahn.lagen,
                zeilen=bahn.zeilen,
                zeit=zeit,
            )
        elif stiche:
            text = tr("va.plan.ergebnis_stiche", lagen=bahn.lagen, zeilen=bahn.zeilen, zeit=zeit)
        else:
            text = tr("va.plan.ergebnis", lagen=bahn.lagen, zeilen=bahn.zeilen, zeit=zeit)
        if getattr(bahn, "nuten", 0):
            text += " " + tr("va.plan.nuten", n=bahn.nuten)
        if getattr(bahn, "bohrungen", 0):
            text += " " + tr("va.plan.bohrungen", n=bahn.bohrungen)
        if getattr(bahn, "mantelnuten", 0):
            text += " " + tr("va.plan.mantelnuten", n=bahn.mantelnuten)
        dazu = self.vorschau_planbohren
        bohrer = self.bohrer_dazu()
        if dazu is not None and bohrer is not None:
            _n, f_bohren, _s = js.werte_im_job(bohrer, self._bohreinsatz(bohrer), self.job)
            n = dazu.bohrungen
            text += " " + tr(
                "va.plan.dazu_bohren",
                bohrer=mg.genannt(bohrer, self._magazin()),
                bohrungen=tr("va.plan.bohrung") if n == 1 else tr("va.plan.bohrungen_zahl", n=n),
                seiten=(
                    tr("va.plan.seite") if dazu.seiten == 1 else tr("va.plan.seiten", n=dazu.seiten)
                ),
                huebe=tr("va.plan.hub") if dazu.huebe == 1 else tr("va.plan.huebe", n=dazu.huebe),
                zeit=_zeit_text(vb.dauer(dazu, f_bohren)) if f_bohren > 0 else "?",
            )
        if bahn.hinten_frei > 0:
            text += " " + tr("vb.hinten_frei", laenge=weg_text(bahn.hinten_frei))
        return text

    # --- Rundum entgraten (V4d) -----------------------------------------------------------

    def _entgratfraeser_fuellen(self):
        """Die Fräser zum Entgraten (vierachs_entgraten.kann_entgraten: Fasenfräser, Kugel)
        mit Schnittwerten für den Werkstoff; vorgewählt der bisher gewählte, beim Ändern der
        der Operation, sonst der zuletzt benutzte, sonst ein Fasenfräser mit Einsatz „Fasen“,
        sonst ein Fasenfräser, sonst die Kugel."""
        werkstoff = self.werkstoff()
        vorher = self.entgratfraeser()
        self._entgratfraeser = [
            w
            for w in self._sortiert()
            if vent.kann_entgraten(w) and self._passende_einsaetze(w, werkstoff)
        ]
        kennungen = [w.kennung for w in self._entgratfraeser]
        gemerkt = _parameter().GetString(GEMERKT_ENTGRATFRAESER, "")
        if vorher is not None and vorher.kennung in kennungen:
            wahl = kennungen.index(vorher.kennung)
        elif self._vorwahl_entgraten in kennungen:  # beim Ändern: der Fräser der Operation
            wahl = kennungen.index(self._vorwahl_entgraten)
        elif gemerkt in kennungen and self._im_magazin(gemerkt):
            wahl = kennungen.index(gemerkt)
        else:
            wahl = min(
                range(len(self._entgratfraeser)),
                key=lambda i: (
                    self._entgratfraeser[i].art != wz.FASENFRAESER,
                    not self._hat_einsatz(self._entgratfraeser[i], werkstoff, wz.FASEN),
                    i,
                ),
                default=0,
            )
        self._fuellt = True
        try:
            self.wahl_entgratfraeser.clear()
            for werkzeug in self._entgratfraeser:
                self.wahl_entgratfraeser.addItem(self._zeile(werkzeug))
            if self._entgratfraeser:
                self.wahl_entgratfraeser.setCurrentIndex(wahl)
        finally:
            self._fuellt = False
        self._entgrateinsatz_fuellen()

    def entgratfraeser(self):
        """Der gewählte Fräser zum Entgraten (werkzeuge.Werkzeug) oder None."""
        i = self.wahl_entgratfraeser.currentIndex()
        return self._entgratfraeser[i] if 0 <= i < len(self._entgratfraeser) else None

    def _entgratfraeser_gewaehlt(self):
        if not self._fuellt:
            self._entgrateinsatz_fuellen()
            self._entgraten_vorschlagen()

    def _entgrateinsatz_fuellen(self):
        """Die Einsätze des Fräsers; vorgewählt „Fasen“, sonst „Schlichten“, sonst „Schruppen“;
        beim Ändern der, mit dem der Controller gesetzt ist."""
        werkzeug = self.entgratfraeser()
        self._entgrateinsaetze = (
            self._passende_einsaetze(werkzeug, self.werkstoff()) if werkzeug is not None else []
        )
        arten = [e.art for e in self._entgrateinsaetze]
        wahl = next(
            (arten.index(a) for a in (wz.FASEN, wz.SCHLICHTEN, wz.SCHRUPPEN) if a in arten), 0
        )
        if (
            self._art == ENTGRATEN
            and self._tc_vorher is not None
            and werkzeug is not None
            and werkzeug.kennung == self._vorwahl_entgraten
        ):
            gemerkt = js.vorgeschlagener_einsatz(self._tc_vorher, self._entgrateinsaetze, self.job)
            wahl = gemerkt if gemerkt >= 0 else wahl
        self._fuellt = True
        try:
            self.wahl_entgrateinsatz.clear()
            for einsatz in self._entgrateinsaetze:
                self.wahl_entgrateinsatz.addItem(wz.einsatz_name(einsatz))
            if self._entgrateinsaetze:
                self.wahl_entgrateinsatz.setCurrentIndex(wahl)
        finally:
            self._fuellt = False
        self._entgrateinsatz_gewaehlt()

    def entgrateinsatz(self):
        """Der gewählte Einsatz zum Entgraten (werkzeuge.Einsatz) oder None."""
        i = self.wahl_entgrateinsatz.currentIndex()
        return self._entgrateinsaetze[i] if 0 <= i < len(self._entgrateinsaetze) else None

    def _entgrateinsatz_gewaehlt(self):
        """Drehzahl und Vorschub, der Vorschlag ins Feld."""
        if self._fuellt:
            return
        werkzeug, einsatz = self.entgratfraeser(), self.entgrateinsatz()
        self.schnittwerte_entgraten.setText(self._schnittwerte_text(werkzeug, einsatz))
        for feld, eingabe in self.felder_entgraten.items():
            eingabe.setPlaceholderText(
                groesse_zeigen(self._vorschlag(feld), einheiten.LAENGE) or "0"
            )
        self._vorschau_starten()

    def entgraten_an(self):
        """Ist „Rundum entgraten“ angehakt? Geht es nicht, nimmt _entgraten_vorschlagen den
        Haken heraus; beim Ändern der Operation ist er gesetzt und gesperrt."""
        return self.mit_entgraten.isChecked()

    def _entgraten_umgeschaltet(self, an):
        if not self._fuellt:
            self._entgraten_von_hand = True
        self.entgratfelder.setEnabled(an)
        self.entgratfelder.setVisible(an)
        self.ergebnis_entgraten.setVisible(an)
        self._umgeschaltet()

    def _entgrat_kanten(self):
        """[vierachs_entgratbahn.Kante] – die Außenkanten der gewählten Flächen (leer: alle),
        grob unterteilt – zum Zählen. Keine an einem Körper aus einem STL: Zwischen seinen Dreiecken
        liegen nur Knicke der Annäherung, kein Grat."""
        if self.job is None or stl_teil.aus_stl(self.teil):
            return []
        achse = self.achse()
        return ve.kanten(
            vr.modell(self.job).Shape,
            achse.laengs,
            va.radial(achse),
            self.flaechen(),
            ve.VORSCHAU_SCHRITT,
        )

    def _entgraten_vorschlagen(self):
        """Ob „Rundum entgraten“ geht – Außenkanten an den gewählten Flächen und ein Fräser
        dafür mit Schnittwerten – und der Vorschlag mit Grund (W-006 E5): angehakt, wenn ein
        Fasenfräser gewählt ist und man es nicht von Hand abgewählt hat; mit der Kugel allein
        bleibt der Haken aus, und der Satz sagt, wie es ginge. Beim Ändern bleibt der Haken,
        wie er ist."""
        if self.job is None or self._art == ENTGRATEN:
            return
        werkzeug = self.entgratfraeser()
        kanten = self._entgrat_kanten() if werkzeug is not None else []
        if werkzeug is None:
            geht, vorschlag, grund = False, False, tr("va.entgraten.kein_fraeser")
        elif not kanten and stl_teil.aus_stl(self.teil):
            geht, vorschlag, grund = False, False, tr("va.entgraten.stl")
        elif not kanten:
            geht, vorschlag, grund = False, False, tr("va.entgraten.keine_kanten")
        elif werkzeug.art == wz.FASENFRAESER:
            geht, vorschlag = True, True
            grund = tr(
                "va.entgraten.vorschlag",
                kanten=len(kanten),
                werkzeug=mg.genannt(werkzeug, self._magazin()),
            )
        else:
            geht, vorschlag = True, False
            grund = tr(
                "va.entgraten.kugel",
                kanten=len(kanten),
                werkzeug=mg.genannt(werkzeug, self._magazin()),
            )
        geht = geht and self._entgraten_erlaubt
        self.entgrat_grund.setText(grund)
        war = self.entgraten_an()
        vorher = self._fuellt
        self._fuellt = True
        try:
            self.mit_entgraten.setEnabled(geht)
            if not geht:
                self.mit_entgraten.setChecked(False)
            elif not self._entgraten_von_hand and self.zu_aendern is None:
                self.mit_entgraten.setChecked(vorschlag)
        finally:
            self._fuellt = vorher
        self.entgratfelder.setEnabled(self.entgraten_an())
        self.entgratfelder.setVisible(self.entgraten_an())
        self.ergebnis_entgraten.setVisible(self.entgraten_an())
        if self.entgraten_an() != war:
            self._umgeschaltet()

    def _entgrat_argumente(self):
        """Die Argumente für die grobe Bahn „Rundum entgraten“ (vierachs_vorschau.entgraten)
        für Kanten und Zeit."""
        werkzeug = self.entgratfraeser()
        achse = self.achse()
        return (
            tuple(achse.laengs),
            tuple(va.radial(achse)),
            ff.von_werkzeug(werkzeug),
            self._wert("breite"),
            (
                self._ueberlauf_fuer(werkzeug),
                self._wert("abstand_futter"),
                self._wert("sicherheit"),
            ),
            self._halter_fuer(werkzeug),
            self.flaechen(),
        ), {}

    def _entgrat_text(self, bahn):
        """„→ 4 Kanten, etwa 1 min“ – mit den Kanten, die der Fräser nicht erreicht, und was
        hinten nicht erreicht wird."""
        from .reichweite import weg_text

        _n, vorschub, _senkrecht = js.werte_im_job(
            self.entgratfraeser(), self.entgrateinsatz(), self.job
        )
        zeit = (
            _zeit_text(
                vb.dauer(
                    bahn,
                    vorschub,
                    freivorschub=self._freivorschub(),
                    fraeser_radius=_radius(self.entgratfraeser()),
                )
            )
            if vorschub > 0
            else "?"
        )
        if bahn.ausgelassen:
            text = tr(
                "va.entgraten.ergebnis_ausgelassen",
                kanten=bahn.kanten,
                zeit=zeit,
                ausgelassen=bahn.ausgelassen,
            )
        else:
            text = tr("va.entgraten.ergebnis", kanten=bahn.kanten, zeit=zeit)
        if bahn.hinten_frei > 0:
            text += " " + tr("vb.hinten_frei", laenge=weg_text(bahn.hinten_frei))
        return text

    def _vorschlag(self, feld):
        """Der Wert eines leeren Felds (mm): Zustellung und Vorschub je Umdrehung aus dem
        Einsatz (ap und ae – ae höchstens der Durchmesser), das Aufmaß 0,3 mm, der Überlauf
        Fräserradius + 0,5 mm, Abstand zum Futter 5 mm, Sicherheitsabstand 2 mm; beim Schlichten
        die Schrittweite aus der Werkzeugtabelle (ae) und das Aufmaß 0."""
        if feld == "kammhoehe_ziel":
            return vs.KAMMHOEHE
        if feld == "schrittweite":
            werkzeug = self.schlichtfraeser()
            if werkzeug is None:
                return 0.0
            return vs.schrittweite_vorschlag(
                werkzeug,
                self.schlichteinsatz(),
                self._wert("kammhoehe_ziel"),
                angestellt=self.querachse() and self.anstellen(),
                eingegeben=bool(self._feld("kammhoehe_ziel").text().strip()),
            )
        if feld == "zustellung_plan":
            einsatz = self.planeinsatz()
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else vo.ZUSTELLUNG
        if feld == "zeilenabstand":
            werkzeug = self.planfraeser()
            if werkzeug is None:
                return 0.0
            return vplan.zeilenabstand_vorschlag(
                werkzeug, self.planeinsatz(), ff.von_werkzeug(werkzeug)
            )
        if feld == "aufmass_plan":
            return vplan.AUFMASS
        if feld == "breite":
            return vent.BREITE
        if feld == "aufmass_schlichten":
            return vs.AUFMASS
        if feld == "aufmass":
            return vo.AUFMASS
        if feld == "aufloesung":
            return vh.SCHRITT_A
        if feld == "aufloesung_rundum":
            return vh.SCHRITT_PHI
        if feld == "aufloesung_schlichten":
            return vb.SCHRITT_PHI_SCHLICHTEN
        if feld == "aufloesung_plan":
            return vp.TOLERANZ
        if feld == "aufloesung_entgraten":
            return vent.ve.SCHRITT
        if feld in ("ueberlauf", "abstand_futter", "sicherheit"):
            radius = self.fraeser().durchmesser / 2 if self.fraeser() is not None else 0.0
            ueberlauf, abstand, sicherheit = vo.vorgeschlagene_abstaende(radius, self.job)
            return {"ueberlauf": ueberlauf, "abstand_futter": abstand}.get(feld, sicherheit)
        einsatz = self.einsatz()
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else vo.ZUSTELLUNG
        werkzeug = self.fraeser()
        durchmesser = werkzeug.durchmesser if werkzeug is not None else 0.0
        if einsatz is not None and 0 < einsatz.ae <= durchmesser:
            return einsatz.ae
        return vo.STEIGUNG_ANTEIL * durchmesser

    def _feld(self, feld):
        """Das Eingabefeld `feld` in Schritt 2 – Schruppen, Abstände, Schlichten oder Plan."""
        return (
            self.felder_schruppen.get(feld)
            or self.felder_schlichten.get(feld)
            or self.felder_plan.get(feld)
            or self.felder_entgraten[feld]
        )

    def _aufloesung(self, feld):
        """Die eingetragene Auflösung des Felds (mm bzw. Grad) – 0, wenn leer oder ungültig:
        dann gilt der Vorschlag der Operation (aufloesung.py)."""
        text = self._feld(feld).text()
        if not text.strip():
            return 0.0
        try:
            if feld in ("aufloesung", "aufloesung_plan", "aufloesung_entgraten"):
                return max(0.0, groesse_lesen(text, einheiten.LAENGE))
            return max(0.0, zahl_lesen(text))
        except ValueError:
            return 0.0

    def _aufloesung_setzen(self, op, schlichten=False):
        """Trägt die eingetragene Auflösung an die Operation (0 = Vorschlag)."""
        if schlichten:
            au.setze_rundum(op, self._aufloesung("aufloesung_schlichten"))
        else:
            au.setze(op, self._aufloesung("aufloesung"))
            au.setze_rundum(op, self._aufloesung("aufloesung_rundum"))

    def _wert(self, feld):
        """Wert eines Felds in Schritt 2 (mm); leer oder ungültig gilt der Vorschlag."""
        text = self._feld(feld).text()
        try:
            return groesse_lesen(text, einheiten.LAENGE) if text.strip() else self._vorschlag(feld)
        except ValueError:
            return self._vorschlag(feld)

    def _schruppen_umgeschaltet(self, an):
        # Die Felder eines Abschnitts nur, solange er angehakt ist – sonst der Titel, die
        # Erklärung und warum (Manuel, 2026-10-02: „die Bedienung schön“).
        self.schruppfelder.setEnabled(an)
        self.schruppfelder.setVisible(an)
        self.ergebnis.setVisible(an)
        self._umgeschaltet()

    def _schlichten_umgeschaltet(self, an):
        if not self._fuellt and not self._schlichten_selbst and self._schlichten_vorgewaehlt:
            self._schlichten_von_hand = True
        self.schlichtfelder.setEnabled(an)
        self.schlichtfelder.setVisible(an)
        self.ergebnis_schlichten.setVisible(an)
        self._vorschlichten_zeigen()
        self._umgeschaltet()

    # --- Vorschlichten (W-031) -------------------------------------------------------------

    def _vorschlichten_zeigen(self):
        """Der Haken „Vorschlichten“ steht unter dem Schlichten, solange es angehakt ist – nicht
        beim Ändern einer Operation (die Operation dazu legt nur „Anlegen“ an)."""
        sichtbar = self.mit_schlichten.isChecked() and self.zu_aendern is None
        self.vorschlichten.setVisible(sichtbar)
        self.ergebnis_vorschlichten.setVisible(
            sichtbar and self.vorschlichten.isChecked() and bool(self.ergebnis_vorschlichten.text())
        )

    def vorschlichten_an(self):
        """Wird mit „Anlegen“ vorgeschlichtet?"""
        return (
            self.mit_schlichten.isChecked()
            and self.zu_aendern is None
            and self.vorschlichten.isChecked()
            and self.schlichtfraeser() is not None
        )

    def _vorschlichten_umgeschaltet(self, an):
        if not self._fuellt and not self._vorschlichten_vorgeschlagen:
            self._vorschlichten_von_hand = True
        self._vorschlichten_zurueck()
        self._vorschlichten_zeigen()
        if an:
            self._vorschlichten_starten()
        self._knoepfe_beschriften()

    def _vorschlicht_einsatz(self):
        """Der Einsatz des Vorschlichtens: „Schruppen“ der Kugel, wenn die Werkzeugtabelle einen
        hat (dafür sind ihre Werte), sonst der des Schlichtens."""
        for einsatz in self._schlichteinsaetze:
            if einsatz.art == wz.SCHRUPPEN:
                return einsatz
        return self.schlichteinsatz()

    def _vorschlicht_aufmass(self):
        """Das Aufmaß, auf das vorgeschlichtet wird: das des Schruppens (Manuel, 2026-10-12: „mit
        der Kugel auf 0,3 mm“) – nie unter dem des Schlichtens."""
        return max(self._wert("aufmass"), self._wert("aufmass_schlichten"))

    def _vorschlicht_schrittweite(self):
        """So weit, dass zwischen den Bahnen höchstens ein Drittel des Aufmaßes stehen bleibt
        (VORSCHLICHTEN_KAMM_ANTEIL) – mit flacher Stirn ae des Einsatzes; höchstens ae des
        Einsatzes „Schruppen“, wenn er einen hat (die Werte, die der Fräser kann)."""
        werkzeug = self.schlichtfraeser()
        einsatz = self._vorschlicht_einsatz()
        form = ff.von_werkzeug(werkzeug)
        if form.eben:
            return vs.schrittweite_vorschlag(werkzeug, einsatz)
        kamm = max(self._vorschlicht_aufmass() * VORSCHLICHTEN_KAMM_ANTEIL, 0.01)
        schritt = vs.schrittweite_fuer_kammhoehe(form, kamm)
        if einsatz is not None and einsatz.art == wz.SCHRUPPEN and einsatz.ae > 0:
            schritt = min(schritt, einsatz.ae)
        return round(min(schritt, werkzeug.durchmesser), 3)

    def _vorschlichten_zurueck(self):
        """Nimmt die Aufträge des Vorschlichtens zurück und leert seine Zeile."""
        for name in ("_vor_auftrag", "_vor_rest_auftrag"):
            auftraege = getattr(self, name)
            setattr(self, name, None)
            if auftraege is None:
                continue
            for auftrag in auftraege.values() if isinstance(auftraege, dict) else [auftraege]:
                if not auftrag.erledigt:
                    auftrag.abbrechen()
        self.vorschau_vorschlichten = None
        self.ergebnis_vorschlichten.setText("")
        self.ergebnis_vorschlichten.hide()

    def _vorschlichten_starten(self):
        """Die grobe Bahn des Vorschlichtens auf einem Nebenrechner (wie die Schlichtvorschau, mit
        seinem Aufmaß, seiner Schrittweite und nur dem Stück längs) – danach der Rest für die Kugel
        nach ihm (_vor_rest_starten). Ohne Nebenrechner nur der Satz, was angelegt wird."""
        from . import nebenrechner as nr

        if not self.vorschlichten_an() or self.job is None or self.geschlossen:
            return
        self._vorschlichten_zurueck()
        try:
            args, kwargs = self._schlicht_argumente()
        except ValueError:
            return
        args = list(args)
        args[3] = self._vorschlicht_schrittweite()
        args[4] = self._vorschlicht_aufmass()
        kwargs = dict(kwargs, laengs_bereich=self._vorschlicht_bereich)
        self._vorschlicht_satz(tr("va.vorschau.rechnet"))
        pool = nr.pool()
        if not pool.verfuegbar():
            self._vorschlicht_satz(self._vorschlicht_text(None))
            return
        nummer = self._vorschau_nummer
        # Der Wendel nach in Blöcken, je einer auf einem Nebenrechner (_wendel_teilen).
        auftraege = self._wendel_teilen({"vor": (tuple(args), kwargs)}, name="vor")
        laufend = {}
        try:
            kopie = pool.kopie(self.doc, wiederverwenden=True)
            for name, (argumente, schluessel) in auftraege.items():
                laufend[name] = pool.auftrag(
                    "vierachs_vorschau",
                    "schlichten",
                    kopie,
                    self.job.Name,
                    *argumente,
                    **schluessel,
                )
        except nr.NichtVerfuegbar:
            for auftrag in laufend.values():
                auftrag.abbrechen()
            self._vorschlicht_satz(self._vorschlicht_text(None))
            return
        self._vor_auftrag = laufend
        self._vor_teile = ({}, {}, [])
        for name, auftrag in laufend.items():
            auftrag.bei_fertig = lambda a, name=name: self._vorschlichten_angekommen(
                nummer, name, a
            )

    def _vorschlicht_satz(self, text, farbe=None):
        self.ergebnis_vorschlichten.setStyleSheet(f"color: {farbe or GRAU_TEXT};")
        self.ergebnis_vorschlichten.setText(text)
        self._vorschlichten_zeigen()

    def _vorschlicht_text(self, bahn):
        """„→ Kugel T3 auf 0,3 Aufmaß, Schrittweite 2,19, Z −57 … 5: 34 Umdrehungen, etwa 3 min“ –
        ohne Bahn ohne Umdrehungen und Zeit."""
        werkzeug = self.schlichtfraeser()
        bereich = self._vorschlicht_bereich
        if bereich is not None:
            richtung = va.achsbuchstabe(FreeCAD.Vector(*self.achse().laengs)) or tr(
                "va.rest.laengs"
            )
            wo = tr(
                "va.vorschlichten.wo",
                richtung=richtung,
                von=einheiten.text(bereich[0], einheiten.LAENGE, 0).replace("-", "−"),
                bis=einheiten.text(bereich[1], einheiten.LAENGE, 0).replace("-", "−"),
            )
        else:
            wo = tr("va.vorschlichten.ganz")
        text = tr(
            "va.vorschlichten.was",
            werkzeug=f"T{werkzeug.nummer}",
            aufmass=groesse_zeigen(self._vorschlicht_aufmass(), einheiten.LAENGE),
            schrittweite=groesse_zeigen(self._vorschlicht_schrittweite(), einheiten.LAENGE),
            wo=wo,
        )
        if bahn is None:
            return text
        _n, vorschub, _senkrecht = js.werte_im_job(werkzeug, self._vorschlicht_einsatz(), self.job)
        zeit = (
            _zeit_text(
                vb.dauer(
                    bahn,
                    vorschub,
                    freivorschub=self._freivorschub(),
                    fraeser_radius=_radius(werkzeug),
                )
            )
            if vorschub > 0
            else "?"
        )
        if bahn.linien:
            menge = tr("va.schlichten.ergebnis_linien", linien=f"{bahn.linien}", zeit=zeit)
        elif getattr(bahn, "wendel_bahnen", 0):
            menge = tr("va.schlichten.ergebnis_wendel", bahnen=f"{bahn.wendel_bahnen}", zeit=zeit)
        else:
            menge = tr("va.schlichten.ergebnis", umdrehungen=f"{bahn.umdrehungen:.0f}", zeit=zeit)
        return f"{text} {menge.removeprefix('→ ')}."

    def _vorschlichten_angekommen(self, nummer, name, auftrag):
        laufend = self._vor_auftrag
        if (
            nummer != self._vorschau_nummer
            or self.geschlossen
            or not isinstance(laufend, dict)
            or laufend.get(name) is not auftrag
        ):
            return
        ergebnisse, gruende, gescheitert = self._vor_teile
        if auftrag.fehler is None:
            ergebnisse[name] = auftrag.ergebnis
        elif auftrag.fehlerart == "ValueError":
            gruende[name] = auftrag.fehlersatz
        else:
            if not auftrag.abgebrochen:
                FreeCAD.Console.PrintWarning(f"CAM-Addon: Vorschlichten: {auftrag.fehler}\n")
            gescheitert.append(name)
        if not all(a.erledigt for a in laufend.values()):
            return
        self._vor_auftrag = None
        if gescheitert:
            self._vorschlicht_satz(self._vorschlicht_text(None))
            return
        self._wendel_zusammenfuegen(ergebnisse, gruende, name="vor")
        if gruende:
            self._vorschlicht_satz(next(iter(gruende.values())), ROT)
            return
        self.vorschau_vorschlichten = ergebnisse.get("vor")
        if self.vorschau_vorschlichten is None:
            self._vorschlicht_satz(self._vorschlicht_text(None))
            return
        self._vorschlicht_satz(self._vorschlicht_text(self.vorschau_vorschlichten))
        self._vor_rest_starten()

    def _vor_rest_starten(self):
        """Der Rest für die Kugel nach Schruppen und Vorschlichten (vierachs_vorschau.rest mit
        `vor`) – ob es reicht, sagt _vor_rest_angekommen."""
        from . import nebenrechner as nr
        from . import voxelstange as vx

        if (
            self.vorschau is None
            or self.vorschau_schlichten is None
            or self.vorschau_vorschlichten is None
        ):
            return
        schrupp_form = ff.von_werkzeug(self.fraeser())
        schlicht_form = ff.von_werkzeug(self.schlichtfraeser())
        soll = self._rest_soll()
        if vx.fraeser(schrupp_form) is None or vx.fraeser(schlicht_form) is None or soll <= 0:
            return
        pool = nr.pool()
        if not pool.verfuegbar():
            return
        nummer = self._vorschau_nummer
        try:
            auftrag = pool.auftrag(
                "vierachs_vorschau",
                "rest",
                pool.kopie(self.doc, wiederverwenden=True),
                self.job.Name,
                tuple(self.achse().laengs),
                _saetze(self.vorschau),
                schrupp_form,
                _saetze(self.vorschau_schlichten),
                schlicht_form,
                REST_VIEL * soll,
                vor=_saetze(self.vorschau_vorschlichten),
                vor_form=schlicht_form,
            )
        except nr.NichtVerfuegbar:
            return
        text = self.ergebnis_vorschlichten.text()
        auftrag.bei_fertig = lambda a: self._vor_rest_angekommen(nummer, a, soll, text)
        self._vor_rest_auftrag = auftrag

    def _vor_rest_angekommen(self, nummer, auftrag, soll, text):
        """Nach dem Vorschlichten: grau, wie viel die Kugel beim Schlichten höchstens nimmt; gelb,
        wenn es noch mehr als REST_VIEL × `soll` ist."""
        from .gui_kollision import GELB

        if (
            nummer != self._vorschau_nummer
            or self.geschlossen
            or auftrag is not self._vor_rest_auftrag
        ):
            return
        self._vor_rest_auftrag = None
        e = auftrag.ergebnis if auftrag.fehler is None else None
        if not e:
            return

        def flaeche(wert):
            return einheiten.text(wert, einheiten.QUERSCHNITT, 1 if wert >= 1 else 2)

        viel = e["hoechstens"] > REST_VIEL * soll
        satz = tr(
            "va.vorschlichten.danach_viel" if viel else "va.vorschlichten.danach",
            menge=flaeche(e["hoechstens"]),
            soll=flaeche(soll),
        )
        self._vorschlicht_satz(f"{text} {satz}", GELB if viel else None)

    def _umgeschaltet(self):
        """Ein Haken ging an oder aus: die Abstände gelten, solange einer an ist; die Stange
        ragt so weit heraus, wie die angehakten Bearbeitungen es brauchen."""
        schruppen, schlichten = self._gewaehlt()
        # Der Messstopp zwischen Schruppen und Schlichten: nur, wenn beide neu angelegt werden.
        beide = schruppen and schlichten and self.zu_aendern is None
        self.schlichten_messstopp.setEnabled(beide)
        self.schlichten_messstopp.setVisible(self.zu_aendern is None)
        bearbeitung = schruppen or schlichten or self.plan_an() or self.entgraten_an()
        self.abstandsfelder.setEnabled(bearbeitung)
        self.hinweis_bearbeitung.setText("")
        self._lage_zeigen()
        if bearbeitung:
            self._vorschau_starten()
        elif self.vermessung is not None:  # ohne Fräser reicht die Abstechbreite hinten
            if not _gleiche_stange(self.stange(), self._stange_jetzt):
                self._anwenden()
            self.ausspannen.setText(self._ausspannen_text())
        self._knoepfe_beschriften()

    def messstopp(self):
        """Ein Messstopp zwischen Schruppen und Schlichten (angehakt und möglich)?"""
        return self.schlichten_messstopp.isEnabled() and self.schlichten_messstopp.isChecked()

    def _gewaehlt(self):
        """(Schruppen, Schlichten): welche Bearbeitungen angelegt bzw. geändert werden – beim
        Ändern die der Operation, beim Schruppen dazu ein angehaktes Schlichten."""
        return self.mit_schruppen.isChecked(), self.mit_schlichten.isChecked()

    def _vorschau_starten(self):
        if self._fuellt:
            return
        self.vorschau = None
        self.vorschau_schlichten = None
        self.vorschau_plan = None
        self.vorschau_planbohren = None
        self.vorschau_entgraten = None
        self._vorschau_abbrechen()  # was noch zur Eingabe davor rechnet, ist veraltet
        self._vorschau_uhr.start()  # erst nach einer kurzen Pause rechnen
        self._knoepfe_beschriften()

    def _vorschau_rechnen(self):
        """Die Bahnen wie die Operationen sie rechnen – das Schruppen genau, für „→ 5 Lagen
        (Ø 80 → Ø 60,6)“, das Schlichten grob, für Umdrehungen und Zeit – und damit „Anlegen“
        weiß, ob es geht."""
        self._vorschau_uhr.stop()
        schruppen, schlichten = self._gewaehlt()
        plan = self.plan_an()
        entgraten = self.entgraten_an()
        if self.geschlossen or self.seite != 2:
            return
        self._lage_zeigen()
        if not (schruppen or schlichten or plan or entgraten):
            return
        self.vorschau = None
        self.vorschau_schlichten = None
        self.vorschau_plan = None
        self.vorschau_entgraten = None
        for etikett in (
            self.ergebnis,
            self.ergebnis_schlichten,
            self.kammhoehe,
            self.ergebnis_plan,
            self.ergebnis_entgraten,
        ):
            etikett.setText("")
        self.kammhoehe.hide()
        self.kammhoehe_ae.hide()
        self._rest_zurueck()
        self._vorschlichten_zurueck()
        self._vorschlichten_zeigen()
        self.hinweis_bearbeitung.setText("")
        if schruppen and (self.fraeser() is None or self.einsatz() is None):
            self._rot(tr("va.fraeser.keiner"))
            self._knoepfe_beschriften()
            return
        if schlichten and (self.schlichtfraeser() is None or self.schlichteinsatz() is None):
            self._rot(tr("va.schlichtfraeser.keiner"))
            self._knoepfe_beschriften()
            return
        if plan and (self.planfraeser() is None or self.planeinsatz() is None):
            self._rot(tr("va.planfraeser.keiner"))
            self._knoepfe_beschriften()
            return
        if entgraten and (self.entgratfraeser() is None or self.entgrateinsatz() is None):
            self._rot(tr("va.entgratfraeser.keiner"))
            self._knoepfe_beschriften()
            return
        if self.vermessung is not None and not _gleiche_stange(self.stange(), self._stange_jetzt):
            self._anwenden()  # die Stange ragt so weit heraus, wie die Fräser hinten brauchen
        self.ausspannen.setText(self._ausspannen_text())
        # Je Bearbeitung die Argumente (vierachs_vorschau: Funktion nach Dokument und Job) – ein
        # ValueError dabei ist schon ein Grund, ohne zu rechnen.
        self._vorschau_ergebnisse, self._vorschau_gruende = {}, {}
        auftraege = {}
        for name, an, argumente in (
            (SCHRUPPEN, schruppen, self._schrupp_argumente),
            (SCHLICHTEN, schlichten, self._schlicht_argumente),
            (PLAN, plan, self._plan_argumente),
            (ENTGRATEN, entgraten, self._entgrat_argumente),
        ):
            if not an:
                continue
            try:
                werte = argumente()
            except ValueError as fehler:
                self._vorschau_gruende[name] = str(fehler)
                continue
            if name == PLAN:
                auftraege.update(werte)
            else:
                auftraege[name] = werte
        auftraege = self._wendel_teilen(auftraege)
        if not self._vorschau_im_hintergrund(auftraege):
            for name, (args, kwargs) in auftraege.items():
                try:
                    self._vorschau_ergebnisse[name] = self._vorschau_selbst(name, args, kwargs)
                except ValueError as fehler:
                    self._vorschau_gruende[name] = str(fehler)
            self._vorschau_abschliessen()

    def _schrupp_argumente(self):
        """Die Argumente für die Schruppbahn (vierachs_vorschau.schruppen) – genau, für
        „→ 5 Lagen (Ø 80 → Ø 60,6)“."""
        werkzeug = self.fraeser()
        self.hinweis_rund.setText(self._rund_text(werkzeug))
        achse = self.achse()
        return (
            tuple(achse.laengs),
            tuple(va.radial(achse)),
            werkzeug.durchmesser / 2,
            self._wert("zustellung"),
            self._wert("steigung"),
            self._wert("aufmass"),
            *self._abstaende(),
            self._halter_fuer(werkzeug),
            self.flaechen(),
            self._eintauchwinkel(),
        ), {
            "nur_gleichlauf": self.schruppen_nur_gleichlauf.isChecked(),
            "form": ff.von_werkzeug(werkzeug),
            # Mit der Querachse wie die Operation (bis P-2026-10-17-48 rechnete die Vorschau ohne
            # sie: „→ 5 Lagen“, angelegt wurden sechs; am Ring mit Y die Spirale statt der Zeilen).
            "querachse": self.querachse_schruppen(),
            "stetig": self.stetig_schruppen(),
            "nur_noetig": self.nur_noetig(),
            "oben": vo.stufen_des_werkzeugs(werkzeug, self.bibliothek),
            "sektoren_y": self.sektoren_y(),
            "y_weg": self.y_weg(),
            "wendel": self.schruppen_wendel_an(),
            "sektor_wellen": self.sektor_wellen(),
        }

    @staticmethod
    def _vorwaermen():
        """Die Nebenrechner starten und laden, was die Vorschau braucht, während man noch
        Flächen anklickt – die erste Vorschau wartet dann nicht darauf (P-2026-10-11-13)."""
        from . import nebenrechner as nr

        try:
            nr.pool().vorwaermen(
                ["vierachs_vorschau", "vierachs_huelle", "vierachs_bahn", "vierachs_quer"]
            )
        except Exception as fehler:  # noqa: BLE001 – ohne Vorwärmen rechnet die Vorschau wie bisher
            FreeCAD.Console.PrintLog(f"CAM-Addon: Nebenrechner vorwärmen: {fehler}\n")

    @staticmethod
    def _vorschau_funktion(name):
        """Die Funktion in vierachs_vorschau zum Namen des Auftrags („schlichten#3“: ein Block der
        Wendel, _wendel_teilen)."""
        name = name.split("#")[0]
        return "plan" if name == "planbohren" else name

    def _vorschau_selbst(self, name, args, kwargs):
        """Eine Vorschau im eigenen Prozess – ohne Nebenrechner, oder wenn einer scheitert."""
        return getattr(vv, self._vorschau_funktion(name))(self.doc, self.job.Name, *args, **kwargs)

    def _vorschau_im_hintergrund(self, auftraege):
        """Gibt die Vorschauen {Name: (args, kwargs)} den Nebenrechnern (P-2026-10-09-09): Das
        Fenster bleibt bedienbar, die Ergebnisse kommen über _vorschau_angekommen. False ohne
        Nebenrechner – dann rechnet der Aufrufer selbst."""
        from . import nebenrechner as nr

        pool = nr.pool()
        if not auftraege or not pool.verfuegbar():
            return False
        self._vorschau_abbrechen()
        self._vorschau_nummer += 1
        nummer = self._vorschau_nummer
        try:
            kopie = pool.kopie(self.doc, wiederverwenden=True)  # liest nur
            for name, (args, kwargs) in auftraege.items():
                auftrag = pool.auftrag(
                    "vierachs_vorschau",
                    self._vorschau_funktion(name),
                    kopie,
                    self.job.Name,
                    *args,
                    **kwargs,
                )
                auftrag.bei_fertig = lambda a, name=name: self._vorschau_angekommen(nummer, name, a)
                self._vorschau_auftraege[name] = auftrag
        except nr.NichtVerfuegbar:
            self._vorschau_abbrechen()
            return False
        for name, etikett in self._vorschau_etiketten().items():
            if any(n.split("#")[0] == name for n in auftraege):
                etikett.setText(tr("va.vorschau.rechnet"))
        return True

    @staticmethod
    def _wendel_bloecke():
        """In so viele Blöcke teilt sich die Vorschau der Wendel – einer je Nebenrechner (1 ohne
        sie: dann rechnet sie in einem Stück)."""
        from . import nebenrechner as nr

        pool = nr.pool()
        return pool.anzahl if pool.verfuegbar() and pool.anzahl >= 2 else 1

    def _wendel_teilen(self, auftraege, name=SCHLICHTEN):
        """Die Vorschau „der Wendel nach“ in Blöcke von Bahnen, je ein Auftrag (`name`#k, mit
        wendel_teil=(k, n)): Ein Nebenrechner verteilt nicht weiter – rechnete einer alle Bahnen,
        rechnete ein Kern (Manuel, 2026-10-18: „rechnet da gerade nur ein kern ??“)."""
        if name not in auftraege:
            return auftraege
        args, kwargs = auftraege[name]
        bloecke = self._wendel_bloecke()
        if len(args) < 9 or args[8] != vb.WENDEL or bloecke < 2:
            return auftraege
        geteilt = {n: a for n, a in auftraege.items() if n != name}
        for k in range(bloecke):
            geteilt[f"{name}#{k}"] = (args, dict(kwargs, wendel_teil=(k, bloecke)))
        return geteilt

    @staticmethod
    def _wendel_zusammenfuegen(ergebnisse, gruende, name=SCHLICHTEN):
        """Die Blöcke `name`#k (_wendel_teilen) wieder zu einer Bahn unter `name` – mit dem Grund
        eines Blocks, wenn einer nicht ging."""
        teile = sorted(
            (int(n.split("#")[1]), n)
            for n in set(ergebnisse) | set(gruende)
            if n.startswith(name + "#")
        )
        if not teile:
            return
        grund = next((gruende.pop(n) for _k, n in teile if n in gruende), None)
        bahnen = [ergebnisse.pop(n, None) for _k, n in teile]
        for _k, n in teile:
            gruende.pop(n, None)
        bahn = None if grund is not None else vb.wendel_zusammen(bahnen)
        if bahn is None or not bahn.wendel_bahnen:
            gruende[name] = grund or tr("vw.fehler.keine")
        else:
            ergebnisse[name] = bahn

    def _vorschau_etiketten(self):
        return {
            SCHRUPPEN: self.ergebnis,
            SCHLICHTEN: self.ergebnis_schlichten,
            PLAN: self.ergebnis_plan,
            ENTGRATEN: self.ergebnis_entgraten,
        }

    def _vorschau_angekommen(self, nummer, name, auftrag):
        """Ein Nebenrechner ist mit einer Vorschau fertig: Ergebnis oder Grund merken; sind alle
        da, zeigen. Antworten auf eine ältere Eingabe (andere Nummer) zählen nicht."""
        if nummer != self._vorschau_nummer or self.geschlossen:
            return
        if auftrag.fehler is None:
            self._vorschau_ergebnisse[name] = auftrag.ergebnis
        elif auftrag.fehlerart == "ValueError":
            self._vorschau_gruende[name] = auftrag.fehlersatz
        elif not auftrag.abgebrochen:
            FreeCAD.Console.PrintWarning(
                f"CAM-Addon: Vorschau „{name}“ auf dem Nebenrechner gescheitert, rechne hier: "
                f"{auftrag.fehler}\n"
            )
            try:
                self._vorschau_ergebnisse[name] = self._vorschau_selbst(
                    name, auftrag.args[2:], auftrag.kwargs
                )
            except ValueError as fehler:
                self._vorschau_gruende[name] = str(fehler)
        if all(a.erledigt for a in self._vorschau_auftraege.values()):
            self._vorschau_auftraege = {}
            self._vorschau_abschliessen()

    def _vorschau_abschliessen(self):
        """Die Ergebnisse und Gründe ins Fenster – wie die Operationen sie rechnen."""
        e, gruende = self._vorschau_ergebnisse, self._vorschau_gruende
        self._wendel_zusammenfuegen(e, gruende)
        self.vorschau = e.get(SCHRUPPEN)
        if self.vorschau is not None:  # aus dem Nebenrechner: „Anlegen“ nimmt sie wieder
            vo.merke_bahn(self.vorschau)
        self.vorschau_schlichten = e.get(SCHLICHTEN)
        self.vorschau_plan = e.get(PLAN)
        self.vorschau_planbohren = e.get("planbohren")
        self.vorschau_entgraten = e.get(ENTGRATEN)
        for name, etikett, text in (
            (SCHRUPPEN, self.ergebnis, self._lagen_text),
            (SCHLICHTEN, self.ergebnis_schlichten, self._schlicht_text),
            (PLAN, self.ergebnis_plan, self._plan_text),
            (ENTGRATEN, self.ergebnis_entgraten, self._entgrat_text),
        ):
            etikett.setText(text(e[name]) if e.get(name) is not None else "")
        self._rest_starten()
        self._halter_starten()
        hinweis = " ".join(
            gruende[name]
            for name in (SCHRUPPEN, SCHLICHTEN, PLAN, "planbohren", ENTGRATEN)
            if name in gruende
        )
        self.hinweis_bearbeitung.setText(
            self._stirnseite_verweis(html.escape(hinweis, quote=False))
        )
        self._knoepfe_beschriften()

    def _rot(self, text):
        """Den roten Satz unter Schritt 2 als Text setzen: Das Label ist RichText (für den
        Verweis zur Stirnseite, P-2026-10-17-33) – ein „<“ in einer Fehlermeldung wäre sonst ein
        Tag, und Zeilenumbrüche fielen weg."""
        self.hinweis_bearbeitung.setText(html.escape(text, quote=False).replace("\n", "<br>"))

    def _stirnseite_verweis(self, hinweis):
        """Hinter den roten Satz zu Stirnflächen (vierachs_flaechen.stirnseitig – ein radialer
        Fräser erreicht sie nie; Manuels Ring, 2026-10-12: die Ringnuten auf der Stirn „werden
        garnicht bearbeitet“) der Verweis „„Bearbeitung“ von vorn öffnen …“ (zur_bearbeitung);
        sonst der Satz, wie er ist."""
        if not hinweis or self.job is None or not self.gewaehlte:
            return hinweis
        try:
            achse = self.achse()
            stirn = vf.stirnseitig(vr.modell(self.job).Shape, achse.laengs, self.gewaehlte)
        except Exception:  # noqa: BLE001 – der Verweis ist ein Zusatz
            return hinweis
        if not stirn:
            return hinweis
        verweis = html.escape(tr("va.zur_bearbeitung"), quote=False)
        return f'{hinweis} <a href="bearbeitung:{",".join(stirn)}">{verweis}</a>'

    def zur_bearbeitung(self, namen):
        """Stirnflächen (`namen`, „Face6“ …): Dieser Assistent schließt (der Job geht zurück), der
        Assistent „Bearbeitung“ (3 Achsen, von vorn) öffnet sich mit dem Teil und diesen Flächen
        – das Gegenstück zu gui_bearbeitung.BearbeitungPanel.zum_vierachs."""
        from . import gui_bearbeitung

        doc, teil = self.doc, self.teil
        if teil is None or not namen:
            return
        if (
            self.zu_aendern is None
            and self.job is not None
            and gui_bearbeitung.drehmaschine_stirn(self.job)
        ):
            # Die Stange bleibt (ohne Bearbeitungen): „Bearbeitung“ fräst an ihrer Stirnseite
            # mit axialem Werkzeug (W-025) – sonst legte sie einen Quader-Job an, und die
            # Drehmaschine wäre dort abgewiesen. An einer Fräse oder ohne Maschine nimmt
            # „Bearbeitung“ die Stange nicht: dann wie bisher zurück (Gegenleser zu P-43).
            self._stange_behalten()
        else:
            self.reject()
        FreeCAD.setActiveDocument(doc.Name)
        QtCore.QTimer.singleShot(
            0,
            lambda: FreeCADGui.Control.showDialog(
                gui_bearbeitung.BearbeitungPanel(doc, (teil, namen[0]), flaechen=list(namen))
            ),
        )

    def _stange_behalten(self):
        """Schließt wie „Anlegen“ ohne Bearbeitungen: Job und Stange bleiben (ein Schritt
        Rückgängig), das Fenster geht zu – für zur_bearbeitung."""
        if self._uhr.isActive():
            self._uhr.stop()
            self._anwenden()
        self._anzeige_wie_in_cam()
        self._maschine_merken()
        self.doc.commitTransaction()
        self._rohteil_fest = True
        self._vor_dem_schliessen()
        self._vorschlaege_merken()
        dialog_schliessen(self.doc)
        with uhren.still():
            self.doc.recompute()

    def _vorschau_abwarten(self):
        """Wartet, bis die Nebenrechner mit der laufenden Vorschau fertig sind – das Fenster
        verarbeitet dabei seine Ereignisse. Für „Anlegen“, wenn die Vorschau noch fehlt."""
        from . import nebenrechner as nr

        auftraege = [a for a in self._vorschau_auftraege.values() if not a.erledigt]
        if not auftraege:
            return
        # Was scheiterte, hat _vorschau_angekommen schon behandelt.
        with contextlib.suppress(nr.Fehler):
            nr.pool().warten(
                auftraege, zwischendurch=lambda: QtGui.QApplication.processEvents() or True
            )

    def _vorschau_abbrechen(self):
        """Nimmt die Aufträge einer laufenden Vorschau zurück (ihre Nebenrechner enden)."""
        for auftrag in self._vorschau_auftraege.values():
            if not auftrag.erledigt:
                auftrag.abbrechen()
        self._vorschau_auftraege = {}
        self._rest_zurueck()

    # --- Der Rest für die Kugel (Frage 8) ---------------------------------------------------

    def _rest_zurueck(self):
        """Nimmt den Auftrag für den Rest zurück und leert die Zeile."""
        auftrag, self._rest_auftrag = self._rest_auftrag, None
        if auftrag is not None and not auftrag.erledigt:
            auftrag.abbrechen()
        self.rest_schlichten.setText("")
        self.rest_schlichten.hide()
        self._halter_zurueck()

    # --- Stößt der Halter an? (Frage 7) -----------------------------------------------------

    def _halter_etiketten(self):
        return {
            SCHRUPPEN: self.halter_schruppen,
            SCHLICHTEN: self.halter_schlichten,
            PLAN: self.halter_plan,
        }

    def _halter_zurueck(self):
        auftrag, self._halter_auftrag = self._halter_auftrag, None
        if auftrag is not None and not auftrag.erledigt:
            auftrag.abbrechen()
        for etikett in self._halter_etiketten().values():
            etikett.setText("")
            etikett.hide()

    def _halter_starten(self):
        """Wenn die Vorschauen da sind: auf einem Nebenrechner nachrechnen, ob Hals, Schaft oder
        Halter der Fräser längs ihrer Bahn ans Teil stoßen (vierachs_vorschau.halter) – „Kollision
        prüfen“ sagt es sonst erst nach dem Anlegen, mit der Maschine. Ohne Nebenrechner nichts."""
        from . import nebenrechner as nr
        from . import vierachs_halter as vhalter

        self._halter_zurueck()
        if self.geschlossen or self.job is None:
            return
        bahnen, werkzeuge = {}, {}
        for name, bahn, werkzeug in (
            (SCHRUPPEN, self.vorschau, self.fraeser()),
            (SCHLICHTEN, self.vorschau_schlichten, self.schlichtfraeser()),
            (PLAN, self.vorschau_plan, self.planfraeser()),
        ):
            if bahn is None or werkzeug is None:
                continue
            koerper = vhalter.koerper(werkzeug, self.bibliothek)
            if not koerper:
                continue
            bahnen[name] = (
                *_saetze(bahn),
                koerper,
                werkzeug.durchmesser / 2,
            )
            werkzeuge[name] = werkzeug
        pool = nr.pool()
        if not bahnen or not pool.verfuegbar():
            self._halter_zeigen({}, werkzeuge)  # was die Schruppbahn selbst weiß (anstoss)
            return
        achse = self.achse()
        nummer = self._vorschau_nummer
        try:
            auftrag = pool.auftrag(
                "vierachs_vorschau",
                "halter",
                pool.kopie(self.doc, wiederverwenden=True),
                self.job.Name,
                tuple(achse.laengs),
                tuple(va.radial(achse)),
                bahnen,
            )
        except nr.NichtVerfuegbar:
            self._halter_zeigen({}, werkzeuge)
            return
        auftrag.bei_fertig = lambda a: self._halter_angekommen(nummer, a, werkzeuge)
        self._halter_auftrag = auftrag

    def _halter_angekommen(self, nummer, auftrag, werkzeuge):
        """Je Bearbeitung, deren Halter anstößt, gelb: wie weit das Werkzeug heraussteht und wie
        weit es müsste, wo längs – mit dem Verweis zum Werkzeug in der Werkzeugverwaltung."""
        if (
            nummer != self._vorschau_nummer
            or self.geschlossen
            or auftrag is not self._halter_auftrag
        ):
            return
        self._halter_auftrag = None
        if auftrag.fehler is not None:
            if not auftrag.abgebrochen:
                FreeCAD.Console.PrintWarning(f"CAM-Addon: Halter prüfen: {auftrag.fehler}\n")
            return
        self._halter_zeigen(auftrag.ergebnis or {}, werkzeuge)

    def _halter_zeigen(self, befunde, werkzeuge):
        """Die gelben Zeilen „Halter stößt an“: je Bearbeitung der Befund der Prüfung längs der
        Bahn – beim Schruppen sonst, was die Bahn selbst weiß: Seit sie Schaft und Halter ausweicht
        (P-2026-10-12-170), stößt der Halter nicht mehr an, hält die Spitze aber höher, und dort
        bleibt Material (Bahn.anstoss)."""
        richtung = va.achsbuchstabe(FreeCAD.Vector(*self.achse().laengs)) or tr("va.rest.laengs")
        for name, etikett in self._halter_etiketten().items():
            befund = befunde.get(name)
            if befund is None and name == SCHRUPPEN and getattr(self.vorschau, "anstoss", ()):
                befund = self._anstoss_jetzt(werkzeuge.get(name))
            if befund is None or name not in werkzeuge:
                continue
            _stellen, heraus, mindestens, a_von, a_bis = befund
            werkzeug = werkzeuge[name]
            kennung = f"T{werkzeug.nummer}"
            satz = tr(
                "va.halter_stoesst",
                werkzeug=kennung,
                heraus=einheiten.text(heraus, einheiten.LAENGE, 0),
                mindestens=einheiten.text(math.ceil(mindestens), einheiten.LAENGE, 0),
                richtung=richtung,
                von=einheiten.text(a_von, einheiten.LAENGE, 0).replace("-", "−"),
                bis=einheiten.text(a_bis, einheiten.LAENGE, 0).replace("-", "−"),
            )
            verweis = html.escape(tr("rw.werkzeug_oeffnen", werkzeug=kennung), quote=False)
            etikett.setText(
                f'{html.escape(satz, quote=False)} <a href="werkzeug:{werkzeug.nummer}">{verweis}</a>'
                + self._ausspannen_verweis(werkzeug, heraus, mindestens)
            )
            etikett.show()

    def _anstoss_jetzt(self, werkzeug):
        """Der Befund aus Bahn.anstoss der Schrupp-Vorschau mit der Ausspannung, die das Werkzeug
        jetzt hat – None, wenn sie reicht (nach „T1 auf … ausspannen“ gilt die Vorschau noch mit
        der alten). Wie weit es mindestens heraus muss, hängt nicht an der Ausspannung: Das sagt
        der Abstand von Spitze und Teil, wo der Halter sie hielt."""
        alt, mindestens, a_von, a_bis = self.vorschau.anstoss
        stufen = vo.stufen_des_werkzeugs(werkzeug, self.bibliothek) if werkzeug else ()
        jetzt = max((ab for _r, ab in stufen), default=alt)
        if jetzt >= mindestens - vb.ANSTOSS_AB:
            return None
        return (None, jetzt, mindestens, a_von, a_bis)

    def _ausspannen_verweis(self, werkzeug, heraus, mindestens):
        """Der nächste Schritt zur gelben Zeile „Halter stößt an“ als Verweis (Manuel: die Meldung
        bietet an, was zu tun ist): „T1 auf 50 mm ausspannen“ – die Länge ab Spindelnase um so viel
        länger (werkzeug_ausspannen()). Reicht die Gesamtlänge dafür nicht (es bliebe weniger als ein
        Schaftdurchmesser im Halter), sagt es das stattdessen."""
        from . import reichweite as rw

        if self.bibliothek is None:
            return ""
        kennung = f"T{werkzeug.nummer}"
        auf = rw.ausspannen_auf(werkzeug, self.bibliothek, heraus, mindestens)
        if auf is None:
            satz = tr(
                "va.halter_zu_kurz",
                werkzeug=kennung,
                gesamt=einheiten.text(float(werkzeug.gesamtlaenge), einheiten.LAENGE, 0),
            )
            return " " + html.escape(satz, quote=False)
        ziel, neu = auf
        text = tr(
            "va.halter_ausspannen",
            werkzeug=kennung,
            heraus=einheiten.text(ziel, einheiten.LAENGE, 0),
        )
        return f' · <a href="ausspannen:{werkzeug.nummer}:{neu:.3f}:{ziel}">{html.escape(text)}</a>'

    def werkzeug_ausspannen(self, nummer, laenge, heraus):
        """„T1 auf 50 mm ausspannen“ (_ausspannen_verweis): die Länge ab Spindelnase von T`nummer`
        in der Werkzeugverwaltung auf `laenge` mm – so misst sie das Voreinstellgerät, wenn es
        `heraus` mm heraussteht –, gespeichert; grau darunter, was gesetzt ist, dann prüft es neu.
        Gibt das Werkzeug zurück – None, wenn es nicht (mehr) da ist."""
        from . import reichweite as rw

        werkzeug = next(
            (
                w
                for w in (self.bibliothek.werkzeuge if self.bibliothek else ())
                if w.nummer == nummer
            ),
            None,
        )
        if werkzeug is None:
            return None
        rw.ausspannen_setzen(werkzeug, laenge, heraus)
        self.bibliothek.speichern()
        satz = rw.ausgespannt_text(werkzeug, heraus, laenge)
        # Grau dorthin, wo die gelbe Zeile mit diesem Verweis stand – nicht zu Bearbeitungen, die
        # das Werkzeug nur vorgewählt haben.
        zeilen = [
            etikett
            for etikett in self._halter_etiketten().values()
            if f'href="ausspannen:{nummer}:' in etikett.text()
        ]
        self._halter_starten()
        for etikett in zeilen:
            etikett.setText(
                f'<span style="color: {GRAU_TEXT};">{html.escape(satz, quote=False)}</span>'
            )
            etikett.show()
        return werkzeug

    def _rest_soll(self):
        """mm² – was die Kugel ohne Rest höchstens nimmt: das Aufmaß des Schruppens über ihrem
        eigenen (mindestens REST_AUFMASS_MINDESTENS) mal ihr Durchmesser – so greift sie ein, wo
        sie das erste Mal übers Aufmaß fährt."""
        aufmass = self._wert("aufmass") - self._wert("aufmass_schlichten")
        return max(aufmass, REST_AUFMASS_MINDESTENS) * self.schlichtfraeser().durchmesser

    def _rest_starten(self):
        """Wenn Schrupp- und Schlichtvorschau da sind: auf einem Nebenrechner nachrechnen, was
        die Kugel nach dem Schruppen nimmt (vierachs_vorschau.rest), die Zeile darunter füllt
        _rest_angekommen. Ohne Nebenrechner nichts – im Fenster stünde es sonst Sekunden."""
        from . import nebenrechner as nr
        from . import voxelstange as vx

        self._rest_zurueck()
        if self.vorschau is None or self.vorschau_schlichten is None or self.geschlossen:
            return
        schrupp_form = ff.von_werkzeug(self.fraeser())
        schlicht_form = ff.von_werkzeug(self.schlichtfraeser())
        soll = self._rest_soll()
        if vx.fraeser(schrupp_form) is None or vx.fraeser(schlicht_form) is None or soll <= 0:
            return
        pool = nr.pool()
        if not pool.verfuegbar():
            return

        saetze = _saetze

        nummer = self._vorschau_nummer
        try:
            auftrag = pool.auftrag(
                "vierachs_vorschau",
                "rest",
                pool.kopie(self.doc, wiederverwenden=True),
                self.job.Name,
                tuple(self.achse().laengs),
                saetze(self.vorschau),
                schrupp_form,
                saetze(self.vorschau_schlichten),
                schlicht_form,
                REST_VIEL * soll,
            )
        except nr.NichtVerfuegbar:
            return
        auftrag.bei_fertig = lambda a: self._rest_angekommen(nummer, a, soll)
        self._rest_auftrag = auftrag
        self.rest_schlichten.setStyleSheet(f"color: {GRAU_TEXT};")
        self.rest_schlichten.setText(tr("va.rest.rechnet"))
        self.rest_schlichten.show()

    def _rest_angekommen(self, nummer, auftrag, soll):
        """Der Rest ist gerechnet: grau, wie viel die Kugel höchstens nimmt – gelb und wo, wenn
        es mehr als REST_VIEL × `soll` ist. Eine Antwort auf eine ältere Eingabe zählt nicht."""
        from .gui_kollision import GELB

        if nummer != self._vorschau_nummer or self.geschlossen or auftrag is not self._rest_auftrag:
            return
        self._rest_auftrag = None
        e = auftrag.ergebnis if auftrag.fehler is None else None
        if not e:
            if auftrag.fehler is not None and not auftrag.abgebrochen:
                FreeCAD.Console.PrintWarning(f"CAM-Addon: Rest für die Kugel: {auftrag.fehler}\n")
            self.rest_schlichten.hide()
            return

        def flaeche(wert):
            return einheiten.text(wert, einheiten.QUERSCHNITT, 1 if wert >= 1 else 2)

        def stelle(wert):
            return einheiten.text(wert, einheiten.LAENGE, 0).replace("-", "−")

        # Wo vorgeschlichtet wird: wo die Kugel viel nähme, einen Radius davor und dahinter (W-031).
        radius = _radius(self.schlichtfraeser())
        self._vorschlicht_bereich = (
            (e["a_von"] - radius, e["a_bis"] + radius) if e["a_von"] is not None else None
        )
        vorgeschlagen = False
        if (
            self._vorschlicht_bereich is not None
            and not self._vorschlichten_von_hand
            and not self.vorschlichten.isChecked()
            and self.vorschlichten.isVisible()
        ):
            # Wo die Kugel viel nähme, ist das Vorschlichten vorgeschlagen – angehakt, abwählbar
            # (Manuel: Neues als Haken, vorbelegt an; „nur die Bereiche, wo die Kugel viel nähme“).
            self._vorschlichten_vorgeschlagen = True
            try:
                self.vorschlichten.setChecked(True)  # rechnet es (_vorschlichten_umgeschaltet)
            finally:
                self._vorschlichten_vorgeschlagen = False
            vorgeschlagen = True
        elif self.vorschlichten_an():
            self._vorschlichten_starten()
        if e["a_von"] is None:
            self.rest_schlichten.setStyleSheet(f"color: {GRAU_TEXT};")
            self.rest_schlichten.setText(
                tr("va.rest.wenig", menge=flaeche(e["hoechstens"]), soll=flaeche(soll))
            )
        else:
            richtung = va.achsbuchstabe(FreeCAD.Vector(*self.achse().laengs)) or tr(
                "va.rest.laengs"
            )
            self.rest_schlichten.setStyleSheet(f"color: {GELB};")
            self.rest_schlichten.setText(
                tr(
                    "va.rest.viel",
                    menge=flaeche(e["hoechstens"]),
                    faktor=f"{e['hoechstens'] / soll:.0f}",
                    soll=flaeche(soll),
                    strecke=(
                        f"{einheiten.text(e['strecke'], einheiten.LAENGE, 0)} "
                        f"{einheiten.einheit(einheiten.LAENGE)}"
                        if e["strecke"] < 1000
                        else f"{einheiten.text(e['strecke'] / 1000, einheiten.STRECKE, 1)} "
                        f"{einheiten.einheit(einheiten.STRECKE)}"
                    ),
                    richtung=richtung,
                    von=stelle(e["a_von"]),
                    bis=stelle(e["a_bis"]),
                )
                + (" " + tr("va.vorschlichten.vorgeschlagen") if vorgeschlagen else "")
            )
        self.rest_schlichten.show()

    def _lage_zeigen(self):
        """Unter jedem angehakten Fräser ein gelber Satz, wenn er auf der gewählten Maschine
        nicht radial zur Stange säße – mit dem Halter, der fehlt (W-002 Stufe E5)."""
        schruppen, schlichten = self._gewaehlt()
        for etikett, an, werkzeug in (
            (self.lage_schruppen, schruppen, self.fraeser()),
            (self.lage_schlichten, schlichten, self.schlichtfraeser()),
            (self.lage_plan, self.plan_an(), self.planfraeser()),
            (self.lage_entgraten, self.entgraten_an(), self.entgratfraeser()),
        ):
            text = self._lage_text(werkzeug) if an else ""
            etikett.setText(text)
            etikett.setVisible(bool(text))

    def _lage_text(self, werkzeug):
        """Die gelben Sätze zu `werkzeug` auf der gewählten Maschine: nicht in ihrem Magazin
        (W-002 Stufe H2, E3 a – mit „ins Magazin übernehmen“), dann wie es sitzt (_lage_satz)."""
        saetze = []
        magazin = self._magazin()
        fehlt = mg.fehlt_text(werkzeug, magazin) if werkzeug is not None else ""
        if fehlt:
            verweis = html.escape(tr("mg.uebernehmen"), quote=False)
            saetze.append(
                f'{html.escape(fehlt, quote=False)} <a href="magazin:{werkzeug.kennung}">'
                f"{verweis}</a>"
            )
        lage = self._lage_satz(werkzeug)
        if lage:
            saetze.append(lage)
        return "<br>".join(saetze)

    def _lage_satz(self, werkzeug):
        """Der Satz zu `werkzeug` auf der gewählten Maschine (reichweite.Pruefung.kommt_aus):
        leer, wenn es radial aus der Richtung der Bahn kommt – oder ohne offene Maschine."""
        from . import reichweite as rw

        eintrag = self.maschinenwahl()
        if werkzeug is None or self.bibliothek is None:
            return ""
        pruefung = self._pruefung_fuer(eintrag)
        if pruefung is None:
            return ""
        richtung = va.radial(self.achse())
        einspannung = rw.Einspannung(0.0, hl.lage(self.bibliothek.halter_von(werkzeug)))
        # Am Revolver der Platz, den es in diesem Job bekommt (W-002 Stufe G).
        nummer = self._programmnummer(werkzeug, self._vorgemerkt(werkzeug))
        name = mg.genannt(werkzeug, self._magazin())
        if nummer is None:
            return html.escape(tr("va.lage.alle_belegt", werkzeug=name, maschine=eintrag.name))
        aufnahme, radial = pruefung.kommt_aus(nummer, richtung, einspannung)
        if aufnahme is None:
            return html.escape(tr("va.lage.kein_platz", werkzeug=name, maschine=eintrag.name))
        if radial:
            return ""
        # Steht die Aufnahme selbst radial (Sternrevolver), hilft ein gerader Halter.
        _aufnahme, gerade = pruefung.kommt_aus(nummer, richtung)
        werte = {
            "werkzeug": name,
            "aufnahme": m.name_von(aufnahme),
            "richtung": rw.richtung_text(richtung),
        }
        if gerade:
            satz = tr("va.lage.nicht_radial_gerade", **werte)
        else:
            satz = tr("va.lage.nicht_radial", **werte)
        if werkzeug.nummer <= 0:  # ohne Nummer findet der Verweis es nicht
            return html.escape(satz, quote=False)
        verweis = html.escape(tr("rw.werkzeug_oeffnen", werkzeug=name), quote=False)
        return (
            f'{html.escape(satz, quote=False)} <a href="werkzeug:{werkzeug.nummer}">{verweis}</a>'
        )

    def _freivorschub(self):
        """Der Freivorschub der Maschine des Jobs (freiwege) – für die Zeit der Vorschau: Wo die
        Bahn durchs Freie fährt, fährt sie mit ihm (vierachs_bahn._frei)."""
        from . import freiwege as fw

        return fw.freivorschub_fuer(self.job) if self.job is not None else fw.FREIVORSCHUB

    def _maschinen_datei(self):
        """Die Datei der gewählten Maschine – "" ohne (oder ungespeichert)."""
        eintrag = self.maschinenwahl()
        if isinstance(eintrag, str):
            return eintrag
        if isinstance(eintrag, va.Maschinenwahl):
            return eintrag.assembly.Document.FileName or ""
        return ""

    def _magazin(self):
        """Das Magazin, das für die gewählte Maschine gilt (W-002 Stufe H2) – None ohne."""
        datei = self._maschinen_datei()
        if not datei or self.bibliothek is None:
            return None
        return mg.des_jobs(None, self.bibliothek, datei)

    def _im_magazin(self, kennung):
        """Steht das Werkzeug mit `kennung` im Magazin der Maschine – oder gibt es keins? Der
        zuletzt benutzte Fräser ist nur dann vorgewählt (E7 a)."""
        magazin = self._magazin()
        return magazin is None or any(e.werkzeug == kennung for e in magazin.eintraege)

    def _sortiert(self):
        """Die Werkzeuge der Werkzeugverwaltung in der Reihenfolge der Listen (E7 a): mit
        Magazin die beladenen vorn, dann die übrigen des Magazins, dann die anderen."""
        return mg.sortiert(self.bibliothek.werkzeuge, self._magazin())

    def _zeile(self, werkzeug):
        """Die Listenzeile eines Werkzeugs: am Revolver vorn der Platz im Job (_platz_vorsatz),
        dann mit Magazin seine Nummer dort („T3 · P5“, „– … nicht im Magazin“, magazin.zeile),
        ohne Magazin die aus der Werkzeugverwaltung."""
        vorsatz = self._platz_vorsatz(werkzeug)
        magazin = self._magazin()
        if magazin is None:
            return vorsatz + dezimal(wz.zeile(werkzeug))
        return vorsatz + dezimal(mg.zeile(werkzeug, magazin, platz=not vorsatz))

    def _platz_vorsatz(self, werkzeug):
        """„P3 · “ vor einem Fräser, der in diesem Job auf P3 steckt oder dorthin käme (W-002
        Stufe G) – vorn, damit es die schmale Liste nicht abschneidet. Nur an einer Maschine
        mit Revolver."""
        pruefung = self._pruefung_fuer(self.maschinenwahl())
        if pruefung is None or self.bibliothek is None or not pruefung.mit_revolver():
            return ""
        nummer = self._programmnummer(werkzeug)
        return f"P{nummer} · " if nummer is not None else ""

    def _programmnummer(self, werkzeug, vorgemerkt=None):
        """So ruft das Programm `werkzeug` auf: auf der gewählten Maschine mit Revolver der
        Platz, den es in diesem Job hat oder bekommt (bestueckung.platz_fuer – T3 für P3,
        W-002 Stufe G); ohne Maschine oder ohne Revolver seine Nummer aus der
        Werkzeugverwaltung. None, wenn alle Plätze im Job belegt sind – das sagt der gelbe
        Satz. `vorgemerkt`: {Nummer: Kennung} der Fräser, die mit in den Job kommen."""
        if werkzeug is None or self.bibliothek is None:
            return None
        pruefung = self._pruefung_fuer(self.maschinenwahl())
        nummern = pruefung.platznummern() if pruefung is not None else []
        return bs.platz_fuer(
            self.job,
            werkzeug,
            self.bibliothek,
            nummern,
            vorgemerkt,
            maschine=self._maschinen_datei() or None,
        )

    def _vorgemerkt(self, werkzeug):
        """{Nummer: Kennung} der Fräser, die vor `werkzeug` mit ihm zusammen neu in den Job
        kommen (Schruppen, dann Schlichten, dann Plan indexiert, dann Entgraten) – so bekommen
        zwei nicht denselben Platz. None beim Ändern oder ohne solche."""
        if self.zu_aendern is not None or werkzeug is None:
            return None
        schruppen, schlichten = self._gewaehlt()
        ergebnis = {}
        for an, anderer in (
            (schruppen, self.fraeser()),
            (schlichten, self.schlichtfraeser()),
            (self.plan_an(), self.planfraeser()),
            (self.entgraten_an(), self.entgratfraeser()),
        ):
            if anderer is not None and anderer.kennung == werkzeug.kennung:
                break  # ab hier kommen die, die nach `werkzeug` dran sind
            if an and anderer is not None and anderer.kennung not in ergebnis.values():
                nummer = self._programmnummer(anderer, ergebnis or None)
                if nummer is not None:
                    ergebnis[nummer] = anderer.kennung
        return ergebnis or None

    def _pruefung_fuer(self, eintrag):
        """Die Prüfung (reichweite.Pruefung) der gewählten offenen Maschine – einmal gebaut
        je Maschine; None ohne offene Maschine oder wenn sie sich nicht lesen lässt."""
        from . import reichweite as rw

        if not isinstance(eintrag, va.Maschinenwahl):
            return None
        if self._pruefung is None or self._pruefung[0] is not eintrag.assembly:
            try:
                pruefung = rw.Pruefung(eintrag.assembly, eintrag.maschine)
            except Exception as fehler:  # eine halb gebaute Maschine: kein Satz
                FreeCAD.Console.PrintLog(f"4-Achs-Bearbeitung, Maschine: {fehler}\n")
                pruefung = None
            self._pruefung = (eintrag.assembly, pruefung)
        return self._pruefung[1]

    def _rund_text(self, werkzeug):
        """Bei Kugel- und Torusfräsern ein Satz: Gerechnet wird wie mit einem Schaftfräser,
        das Teil bleibt sicher – und wie hoch Rillen zwischen den Bahnen stehen bleiben
        (Manuel testete 2026-09-29 einen Rundfräser)."""
        if werkzeug.art == wz.KUGELFRAESER:
            eckradius = werkzeug.durchmesser / 2
        elif werkzeug.art == wz.TORUSFRAESER:
            eckradius = min(wz.mass(werkzeug, "eckradius"), werkzeug.durchmesser / 2)
        else:
            return ""
        rille = vb.rillenhoehe(werkzeug.durchmesser / 2, eckradius, self._wert("steigung"))
        art = wz.art_text(werkzeug.art)
        if rille < 0.005:
            return tr("va.rund.ohne_rillen", art=art)
        return tr("va.rund", art=art, rille=groesse_fest(rille, einheiten.LAENGE, 2))

    def _abstaende(self):
        """(Sicherheitsabstand, Überlauf, Abstand zum Futter) fürs Schruppen (mm)."""
        return (
            self._wert("sicherheit"),
            self._ueberlauf_fuer(self.fraeser()),
            self._wert("abstand_futter"),
        )

    def _ueberlauf_fuer(self, werkzeug):
        """Der Überlauf (mm): eingetragen gilt er für alle Bearbeitungen, leer die Abstechbreite
        + 0,5 mm – das gerade Stück hinter dem Teil fürs Abstechen (P-2026-10-03-08)."""
        text = self.felder_schruppen["ueberlauf"].text()
        if text.strip():
            try:
                return groesse_lesen(text, einheiten.LAENGE)
            except ValueError:
                pass
        radius = werkzeug.durchmesser / 2 if werkzeug is not None else 0.0
        return vb.ueberlauf_vorschlag(radius, self._laenge("abstechbreite"))

    def _halter_fuer(self, werkzeug):
        """So weit reicht der Halter des Fräsers aus der Werkzeugverwaltung seitlich über die
        Werkzeugachse (halter.seitlich, mm) – 0 ohne Halter."""
        if werkzeug is None or self.bibliothek is None:
            return 0.0
        return hl.seitlich(self.bibliothek.halter_von(werkzeug))

    def _bedarf_hinten(self):
        """[(Überlauf, Fräserradius, Halter, Abstand zum Futter)] – was die Fräser hinter dem
        Teil brauchen: die angehakten und, beim Ändern, die anderen Bearbeitungen im Job. Vor
        dem Futter zählt, was weiter reicht: der Fräser oder sein Halter (halter.seitlich)."""
        schruppen, schlichten = self._gewaehlt()
        abstand = self._wert("abstand_futter")
        bedarf = []
        for an, werkzeug in (
            (schruppen, self.fraeser()),
            (schlichten, self.schlichtfraeser()),
            (self.plan_an(), self.planfraeser()),
            (self.entgraten_an(), self.entgratfraeser()),
        ):
            if an and werkzeug is not None:
                bedarf.append(
                    (
                        self._ueberlauf_fuer(werkzeug),
                        werkzeug.durchmesser / 2,
                        self._halter_fuer(werkzeug),
                        abstand,
                    )
                )
        if self.zu_aendern is not None and self.job is not None:
            for op in js.operationen(self.job):
                if vo.ist_rundum(op) and op is not self.zu_aendern:
                    ueberlauf, abstand_op, _sicherheit = vo.abstaende(op)
                    bedarf.append(
                        (
                            ueberlauf,
                            float(op.OpToolDiameter) / 2,
                            vo.halter_zum_futter(op),
                            abstand_op,
                        )
                    )
        return bedarf

    @staticmethod
    def _hinten(bedarf):
        """Überlauf + was weiter reicht (Fräser oder Halter) + Abstand zum Futter (mm)."""
        ueberlauf, radius, halter, abstand = bedarf
        return ueberlauf + max(radius, halter) + abstand

    def _frei_hinten(self):
        """Was die Fräser hinter dem Teil brauchen: Überlauf, Fräserradius oder Halter (was
        weiter reicht) und Abstand zum Futter (mm), der größte – 0 ohne Bearbeitung oder ohne
        Fräser."""
        return max((self._hinten(b) for b in self._bedarf_hinten()), default=0.0)

    def _ausspannen_text(self):
        """„Die Stange muss 78,5 mm aus dem Futter ragen: Planaufmaß 1,0 + Teil 60,0 + …“ –
        mit dem Fräser, der hinten am meisten braucht; leer, solange das Teil nicht vermessen
        ist."""
        if self.vermessung is None:
            return ""
        stange = self.stange()

        def mm(wert):
            return groesse_fest(wert, einheiten.LAENGE, 1)

        teile = [
            tr("va.ausspannen.planaufmass", wert=mm(stange.planaufmass)),
            tr("va.ausspannen.teil", wert=mm(self.vermessung.laenge)),
        ]
        bedarf = self._bedarf_hinten()
        if bedarf and stange.frei_hinten > stange.abstechbreite:
            ueberlauf, radius, halter, abstand = max(bedarf, key=self._hinten)
            teile += [
                tr("va.ausspannen.ueberlauf", wert=mm(ueberlauf)),
                (
                    tr("va.ausspannen.halter", wert=mm(halter))
                    if halter > radius
                    else tr("va.ausspannen.fraeser", wert=mm(radius))
                ),
                tr("va.ausspannen.abstand", wert=mm(abstand)),
            ]
        else:
            teile.append(tr("va.ausspannen.abstechbreite", wert=mm(stange.abstechbreite)))
        return tr(
            "va.ausspannen",
            laenge=mm(vr.ausspannlaenge(self.vermessung, stange)),
            einheit=einheiten.einheit(einheiten.LAENGE),
            teile=" + ".join(teile),
        )

    def _lagen_text(self, bahn):
        """„→ 5 Lagen (Ø 80 → Ø 60,6)“ – und was hinten nicht erreicht wird."""
        from .reichweite import weg_text

        laenge = einheiten.LAENGE
        if bahn.lagen == 0:
            text = tr("va.lagen.keine")
        elif bahn.r_min < 0:
            # Unter die Mitte (eine Fläche zur Achse hin): ein Durchmesser sagte „Ø −61,8“.
            von = groesse_fest(self.stange().durchmesser, laenge, 1)
            tiefe = groesse_fest(-bahn.r_min, laenge, 1)
            if bahn.lagen == 1:
                text = tr("va.lagen.eine_unter", von=von, tiefe=tiefe)
            else:
                text = tr("va.lagen.unter", lagen=bahn.lagen, von=von, tiefe=tiefe)
        else:
            von = groesse_fest(self.stange().durchmesser, laenge, 1)
            bis = groesse_fest(2 * bahn.r_min, laenge, 1)
            if bahn.lagen == 1:
                text = tr("va.lagen.eine", von=von, bis=bis)
            else:
                text = tr("va.lagen", lagen=bahn.lagen, von=von, bis=bis)
        if getattr(bahn, "wendel_bahnen", 0):
            text += " " + tr("va.lagen.wendel", bahnen=bahn.wendel_bahnen)
        if bahn.hinten_frei > 0:
            text += " " + tr("vb.hinten_frei", laenge=weg_text(bahn.hinten_frei))
        return text

    def _kann_anlegen(self):
        """Schritt 2: ohne Bearbeitung immer; sonst, wenn Fräser und Einsatz der angehakten
        gewählt sind und die Vorschau keinen Fehler meldet."""
        schruppen, schlichten = self._gewaehlt()
        if schruppen and (self.fraeser() is None or self.einsatz() is None):
            return False
        if schlichten and (self.schlichtfraeser() is None or self.schlichteinsatz() is None):
            return False
        if self.plan_an() and (self.planfraeser() is None or self.planeinsatz() is None):
            return False
        if self.entgraten_an() and (self.entgratfraeser() is None or self.entgrateinsatz() is None):
            return False
        return not self.hinweis_bearbeitung.text()

    def werkzeugverwaltung(self, nummer=None):
        """Öffnet die Werkzeugverwaltung – mit `nummer` bei diesem Werkzeug; speichert man
        dort, liest Schritt 2 sie neu."""
        from . import gui_werkzeuge

        dialog = gui_werkzeuge.oeffne(nummer)
        if getattr(self, "_werkzeugdialog", None) is not dialog:
            self._werkzeugdialog = dialog
            dialog.gespeichert.connect(self._werkzeuge_gespeichert)

    def _werkzeug_oeffnen(self, ziel):
        """„werkzeug:3“ im gelben Satz: die Werkzeugverwaltung bei T3 (D-41); „magazin:…“:
        das Werkzeug ins Magazin der Maschine (E3 a)."""
        art, wert = ziel.split(":", 1)
        if art == "bearbeitung":
            self.zur_bearbeitung([n for n in wert.split(",") if n])
        elif art == "magazin":
            self.ins_magazin(wert)
        elif art == "ausspannen":
            nummer, laenge, heraus = wert.split(":")
            self.werkzeug_ausspannen(int(nummer), float(laenge), int(heraus))
        else:
            self.werkzeugverwaltung(int(wert))

    def ins_magazin(self, kennung):
        """„Ins Magazin übernehmen“ (W-002 Stufe H2, E3 a): das Werkzeug ins Magazin der
        gewählten Maschine, die Werkzeugverwaltung gespeichert, die Listen neu. Gibt den
        Eintrag zurück – None, wenn es nicht geht."""
        magazin = self._magazin()
        werkzeug = self.bibliothek.werkzeug_mit_kennung(kennung) if self.bibliothek else None
        if magazin is None or werkzeug is None:
            return None
        eintrag = mg.uebernehmen(self.bibliothek, magazin, werkzeug, self.job)
        self._bearbeitung_fuellen()
        return eintrag

    def _werkzeuge_gespeichert(self):
        if VierachsPanel.offen is self and self.seite == 2:
            self._bearbeitung_fuellen()

    def _bearbeitung_pruefen(self):
        """Gehen die angehakten Bearbeitungen mit Fräser, Einsatz und Werten? Rechnet die
        Vorschau, wenn sie noch fehlt."""
        schruppen, schlichten = self._gewaehlt()
        plan = self.plan_an()
        entgraten = self.entgraten_an()
        if (
            (schruppen and self.vorschau is None)
            or (schlichten and self.vorschau_schlichten is None)
            or (plan and self.vorschau_plan is None)
            or (entgraten and self.vorschau_entgraten is None)
        ):
            self._vorschau_rechnen()
            self._vorschau_abwarten()
        if schruppen and (
            self.fraeser() is None or self.einsatz() is None or self.vorschau is None
        ):
            return False
        if schlichten and (
            self.schlichtfraeser() is None
            or self.schlichteinsatz() is None
            or self.vorschau_schlichten is None
        ):
            return False
        if plan and (
            self.planfraeser() is None or self.planeinsatz() is None or self.vorschau_plan is None
        ):
            return False
        return not entgraten or (
            self.entgratfraeser() is not None
            and self.entgrateinsatz() is not None
            and self.vorschau_entgraten is not None
        )

    def _bearbeitungen_anlegen(self):
        """Werkzeug-Controller und die angehakten Bearbeitungen in den Job – zusammen ein
        eigener Schritt Rückgängig, in einem Befehl (_im_befehl). Den Controller, den jeder neue
        Job von FreeCAD bekommt, nimmt es heraus (D-30). Geht es nicht, steht der Grund rot im
        Fenster: False."""
        schruppen, schlichten = self._gewaehlt()
        plan = self.plan_an()
        entgraten = self.entgraten_an()
        achse = self.achse()
        werte = (self._wert("zustellung"), self._wert("steigung"), self._wert("aufmass"))
        sicherheit, ueberlauf, abstand = self._abstaende()
        schlicht_abstaende = (
            self._ueberlauf_fuer(self.schlichtfraeser()),
            abstand,
            sicherheit,
        )
        plan_abstaende = (self._ueberlauf_fuer(self.planfraeser()), abstand, sicherheit)
        entgrat_abstaende = (self._ueberlauf_fuer(self.entgratfraeser()), abstand, sicherheit)
        anzahl = sum(1 for an in (schruppen, schlichten, plan, entgraten) if an)
        if anzahl > 1 and (plan or entgraten):
            name = tr("va.transaktion.mehrere")
        elif schruppen and schlichten:
            name = tr("va.transaktion.beide")
        elif plan:
            name = tr("va.transaktion.plan")
        elif entgraten:
            name = tr("va.transaktion.entgraten")
        else:
            name = tr("va.transaktion.schruppen") if schruppen else tr("va.transaktion.schlichten")
        flaechen = self.flaechen()
        schlicht_flaechen = self._schlicht_flaechen()
        muster = self.muster()

        def anlegen():
            self.doc.openTransaction(name)
            try:
                ue.uebergeben(self.bibliothek)
                fremde = js.unbenutzte_fremde_controller(self.job, self.bibliothek)
                js.controller_weg(self.doc, fremde)
                # Zwischen den Schritten zeichnet das Fenster neu (uhren.atmen, ohne Klicks): Am
                # Geist (STL) stand es sonst 2,3–3,5 s am Stück – je Werkzeug 0,4–0,6 s, je
                # Operation 0,5–0,8 s in FreeCAD.
                uhren.atmen()
                angelegt = []
                if schruppen:
                    tc = js.controller_ohne_transaktion(
                        self.doc,
                        self.job,
                        self.fraeser(),
                        self.einsatz(),
                        self.werkstoff(),
                        self._programmnummer(self.fraeser()),
                    )
                    uhren.atmen()
                    neu_schruppen = vo.lege_an(
                        self.job,
                        tc,
                        achse,
                        *werte,
                        quer_auf_null=achse.quer,
                        abstaende=(ueberlauf, abstand, sicherheit),
                        halter=self._halter_fuer(self.fraeser()),
                        flaechen_=flaechen,
                        eintauchwinkel=self._eintauchwinkel(),
                        nur_gleichlauf=self.schruppen_nur_gleichlauf.isChecked(),
                        querachse=self.querachse_schruppen(),
                        stetig=self.stetig_schruppen(),
                        nur_noetig=self.nur_noetig(),
                        sektoren_y=self.sektoren_y(),
                        y_weg=self.y_weg(),
                        wendel=self.schruppen_wendel_an(),
                        sektor_wellen=self.sektor_wellen(),
                    )
                    self._aufloesung_setzen(neu_schruppen)
                    angelegt.append(neu_schruppen)
                    uhren.atmen()
                if schlichten:
                    tc_davor = tc if schruppen else None
                    if self.vorschlichten_an():
                        # Vor dem Schlichten (und vor dem Messstopp) das Vorschlichten (W-031):
                        # dieselbe Kugel mit dem Einsatz „Schruppen“, wenn sie einen hat.
                        tc_vor = js.controller_ohne_transaktion(
                            self.doc,
                            self.job,
                            self.schlichtfraeser(),
                            self._vorschlicht_einsatz(),
                            self.werkstoff(),
                            self._programmnummer(self.schlichtfraeser()),
                        )
                        neu_vor = vs.lege_an(
                            self.job,
                            tc_vor,
                            achse,
                            self._vorschlicht_schrittweite(),
                            self._vorschlicht_aufmass(),
                            quer_auf_null=achse.quer,
                            abstaende=schlicht_abstaende,
                            halter=self._halter_fuer(self.schlichtfraeser()),
                            flaechen=schlicht_flaechen,
                            muster=muster,
                            nur_gleichlauf=self.linien_nur_gleichlauf.isChecked(),
                            querachse=self.querachse(),
                            anstellen=self.anstellen(),
                            stetig=self.stetig(),
                            name=tr("vs.name_vor", werkzeug=f"T{tc_vor.ToolNumber}"),
                            laengs_bereich=self._vorschlicht_bereich,
                        )
                        self._aufloesung_setzen(neu_vor, schlichten=True)
                        angelegt.append(neu_vor)
                        tc_davor = tc_vor
                        uhren.atmen()
                    tc = js.controller_ohne_transaktion(
                        self.doc,
                        self.job,
                        self.schlichtfraeser(),
                        self.schlichteinsatz(),
                        self.werkstoff(),
                        self._programmnummer(self.schlichtfraeser()),
                    )
                    uhren.atmen()
                    if tc_davor is not None and self.messstopp():
                        # Schruppen – messen – schlichten: der Messstopp mit dem Controller des
                        # Schruppens, danach die Spindel mit der Drehzahl des Schlichtens.
                        angelegt.append(ms.lege_an(self.job, tc_davor, tc))
                    neu_schlichten = vs.lege_an(
                        self.job,
                        tc,
                        achse,
                        self._wert("schrittweite"),
                        self._wert("aufmass_schlichten"),
                        quer_auf_null=achse.quer,
                        abstaende=schlicht_abstaende,
                        halter=self._halter_fuer(self.schlichtfraeser()),
                        flaechen=schlicht_flaechen,
                        muster=muster,
                        nur_gleichlauf=self.linien_nur_gleichlauf.isChecked(),
                        querachse=self.querachse(),
                        anstellen=self.anstellen(),
                        stetig=self.stetig(),
                    )
                    self._aufloesung_setzen(neu_schlichten, schlichten=True)
                    angelegt.append(neu_schlichten)
                    uhren.atmen()
                if plan:
                    plan_flaechen, loecher = self._plan_flaechen()
                    tc = js.controller_ohne_transaktion(
                        self.doc,
                        self.job,
                        self.planfraeser(),
                        self.planeinsatz(),
                        self.werkstoff(),
                        self._programmnummer(self.planfraeser()),
                    )
                    uhren.atmen()
                    angelegt.append(
                        vplan.lege_an(
                            self.job,
                            tc,
                            achse,
                            self._wert("zustellung_plan"),
                            self._wert("zeilenabstand"),
                            self._wert("aufmass_plan"),
                            quer_auf_null=achse.quer,
                            abstaende=plan_abstaende,
                            halter=self._halter_fuer(self.planfraeser()),
                            flaechen=plan_flaechen,
                            eintauchwinkel=self._eintauchwinkel_fuer(self.planfraeser()),
                            nur_gleichlauf=self.plan_nur_gleichlauf.isChecked(),
                            schaft=self.plan_schaft_an(),
                            raster=self._aufloesung("aufloesung_plan"),
                            weg=self.plan_weg(),
                        )
                    )
                    if loecher:
                        angelegt.append(self._bohrer_dazu_anlegen(achse, achse.quer, loecher))
                    uhren.atmen()
                if entgraten:
                    tc = js.controller_ohne_transaktion(
                        self.doc,
                        self.job,
                        self.entgratfraeser(),
                        self.entgrateinsatz(),
                        self.werkstoff(),
                        self._programmnummer(self.entgratfraeser()),
                    )
                    uhren.atmen()
                    angelegt.append(
                        vent.lege_an(
                            self.job,
                            tc,
                            achse,
                            self._wert("breite"),
                            quer_auf_null=achse.quer,
                            abstaende=entgrat_abstaende,
                            halter=self._halter_fuer(self.entgratfraeser()),
                            flaechen=flaechen,
                            raster=self._aufloesung("aufloesung_entgraten"),
                        )
                    )
                    uhren.atmen()
                self.doc.recompute()
            except Exception:
                self.doc.abortTransaction()
                raise
            return angelegt

        try:
            angelegt = _im_befehl(anlegen)
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"4-Achs-Bearbeitung: {fehler}\n")
            self.operation = None
            self._rot(tr("va.fehler.anlegen", fehler=str(fehler)))
            self._knoepfe_beschriften()
            return False
        self.operation = angelegt[0] if angelegt else None
        return True

    def _aendern(self):
        """Die Operation bekommt Fräser, Einsatz und Werte aus dem Fenster – ein eigener
        Schritt Rückgängig, in einem Befehl (_im_befehl): Ein anderer Fräser kommt als
        Werkzeug in den Job. Den bisherigen Controller nimmt es heraus, wenn ihn keine
        Operation mehr benutzt. Beim Schruppen legt ein angehaktes „Rundum schlichten“ dieses
        dazu an. Geht es nicht, steht der Grund rot im Fenster: False."""
        op = self.zu_aendern
        schlichten_dazu = self._art == SCHRUPPEN and self.mit_schlichten.isChecked()
        plan_dazu = self._art == SCHRUPPEN and self.plan_an()
        entgraten_dazu = self._art == SCHRUPPEN and self.entgraten_an()
        sicherheit, ueberlauf, abstand = self._abstaende()
        schlicht_abstaende = (
            self._ueberlauf_fuer(self.schlichtfraeser()),
            abstand,
            sicherheit,
        )
        plan_abstaende = (self._ueberlauf_fuer(self.planfraeser()), abstand, sicherheit)
        entgrat_abstaende = (self._ueberlauf_fuer(self.entgratfraeser()), abstand, sicherheit)
        if self._art == SCHLICHTEN:
            name = tr("va.transaktion.aendern_schlichten")
        elif self._art == PLAN:
            name = tr("va.transaktion.aendern_plan")
        elif self._art == ENTGRATEN:
            name = tr("va.transaktion.aendern_entgraten")
        else:
            name = tr("va.transaktion.aendern")
        flaechen = self.flaechen()
        schlicht_flaechen = self._schlicht_flaechen()
        muster = self.muster()

        def aendern():
            self.doc.openTransaction(name)
            try:
                ue.uebergeben(self.bibliothek)
                bisher = op.ToolController
                if self._art == SCHLICHTEN:
                    tc = js.controller_fuer(
                        self.doc,
                        self.job,
                        self.schlichtfraeser(),
                        self.schlichteinsatz(),
                        self.werkstoff(),
                        op,
                        self._programmnummer(self.schlichtfraeser()),
                    )
                    vs.aendere(
                        op,
                        tc,
                        self._wert("schrittweite"),
                        self._wert("aufmass_schlichten"),
                        schlicht_abstaende,
                        self._halter_fuer(self.schlichtfraeser()),
                        schlicht_flaechen,
                        muster,
                        nur_gleichlauf=self.linien_nur_gleichlauf.isChecked(),
                        querachse=self.querachse(),
                        anstellen=self.anstellen(),
                        stetig=self.stetig(),
                    )
                    self._aufloesung_setzen(op, schlichten=True)
                elif self._art == PLAN:
                    tc = js.controller_fuer(
                        self.doc,
                        self.job,
                        self.planfraeser(),
                        self.planeinsatz(),
                        self.werkstoff(),
                        op,
                        self._programmnummer(self.planfraeser()),
                    )
                    vplan.aendere(
                        op,
                        tc,
                        self._wert("zustellung_plan"),
                        self._wert("zeilenabstand"),
                        self._wert("aufmass_plan"),
                        plan_abstaende,
                        self._halter_fuer(self.planfraeser()),
                        flaechen,
                        self._eintauchwinkel_fuer(self.planfraeser()),
                        nur_gleichlauf=self.plan_nur_gleichlauf.isChecked(),
                        schaft=self.plan_schaft_an(),
                        raster=self._aufloesung("aufloesung_plan"),
                        weg=self.plan_weg(),
                    )
                elif self._art == ENTGRATEN:
                    tc = js.controller_fuer(
                        self.doc,
                        self.job,
                        self.entgratfraeser(),
                        self.entgrateinsatz(),
                        self.werkstoff(),
                        op,
                        self._programmnummer(self.entgratfraeser()),
                    )
                    vent.aendere(
                        op,
                        tc,
                        self._wert("breite"),
                        entgrat_abstaende,
                        self._halter_fuer(self.entgratfraeser()),
                        flaechen,
                        raster=self._aufloesung("aufloesung_entgraten"),
                    )
                else:
                    tc = js.controller_fuer(
                        self.doc,
                        self.job,
                        self.fraeser(),
                        self.einsatz(),
                        self.werkstoff(),
                        op,
                        self._programmnummer(self.fraeser()),
                    )
                    vo.aendere(
                        op,
                        tc,
                        self._wert("zustellung"),
                        self._wert("steigung"),
                        self._wert("aufmass"),
                        abstaende_=(ueberlauf, abstand, sicherheit),
                        halter_=self._halter_fuer(self.fraeser()),
                        flaechen_=flaechen,
                        eintauchwinkel=self._eintauchwinkel(),
                        nur_gleichlauf=self.schruppen_nur_gleichlauf.isChecked(),
                        querachse=self.querachse_schruppen(),
                        stetig=self.stetig_schruppen(),
                        nur_noetig=self.nur_noetig(),
                        sektoren_y=self.sektoren_y(),
                        y_weg=self.y_weg(),
                        wendel=self.schruppen_wendel_an(),
                        sektor_wellen=self.sektor_wellen(),
                    )
                    self._aufloesung_setzen(op)
                if schlichten_dazu:
                    tc_neu = js.controller_ohne_transaktion(
                        self.doc,
                        self.job,
                        self.schlichtfraeser(),
                        self.schlichteinsatz(),
                        self.werkstoff(),
                        self._programmnummer(self.schlichtfraeser()),
                    )
                    self._aufloesung_setzen(
                        vs.lege_an(
                            self.job,
                            tc_neu,
                            self.achse(),
                            self._wert("schrittweite"),
                            self._wert("aufmass_schlichten"),
                            quer_auf_null=op.QuerAufNull,
                            abstaende=schlicht_abstaende,
                            halter=self._halter_fuer(self.schlichtfraeser()),
                            flaechen=schlicht_flaechen,
                            muster=muster,
                            nur_gleichlauf=self.linien_nur_gleichlauf.isChecked(),
                            querachse=self.querachse(),
                            anstellen=self.anstellen(),
                            stetig=self.stetig(),
                        ),
                        schlichten=True,
                    )
                if plan_dazu:
                    plan_flaechen, loecher = self._plan_flaechen()
                    tc_plan = js.controller_ohne_transaktion(
                        self.doc,
                        self.job,
                        self.planfraeser(),
                        self.planeinsatz(),
                        self.werkstoff(),
                        self._programmnummer(self.planfraeser()),
                    )
                    vplan.lege_an(
                        self.job,
                        tc_plan,
                        self.achse(),
                        self._wert("zustellung_plan"),
                        self._wert("zeilenabstand"),
                        self._wert("aufmass_plan"),
                        quer_auf_null=op.QuerAufNull,
                        abstaende=plan_abstaende,
                        halter=self._halter_fuer(self.planfraeser()),
                        flaechen=plan_flaechen,
                        eintauchwinkel=self._eintauchwinkel_fuer(self.planfraeser()),
                        nur_gleichlauf=self.plan_nur_gleichlauf.isChecked(),
                        schaft=self.plan_schaft_an(),
                        raster=self._aufloesung("aufloesung_plan"),
                        weg=self.plan_weg(),
                    )
                    if loecher:
                        self._bohrer_dazu_anlegen(self.achse(), op.QuerAufNull, loecher)
                if entgraten_dazu:
                    tc_entgraten = js.controller_ohne_transaktion(
                        self.doc,
                        self.job,
                        self.entgratfraeser(),
                        self.entgrateinsatz(),
                        self.werkstoff(),
                        self._programmnummer(self.entgratfraeser()),
                    )
                    vent.lege_an(
                        self.job,
                        tc_entgraten,
                        self.achse(),
                        self._wert("breite"),
                        quer_auf_null=op.QuerAufNull,
                        abstaende=entgrat_abstaende,
                        halter=self._halter_fuer(self.entgratfraeser()),
                        flaechen=flaechen,
                        raster=self._aufloesung("aufloesung_entgraten"),
                    )
                self._maschine_merken()
                frei = bisher is not None and not js.operationen_mit(bisher, self.job)
                if frei and bisher is not tc:
                    js.controller_weg(self.doc, [bisher])
                self.doc.recompute()
            except Exception:
                self.doc.abortTransaction()
                raise

        try:
            _im_befehl(aendern)
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"4-Achs-Bearbeitung: {fehler}\n")
            self._rot(tr("va.fehler.aendern", fehler=str(fehler)))
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
            self._frei_hinten(),
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
                if self.zu_aendern is not None:
                    self._rohteil_aendern()
                self.job = vr.richte_ein(
                    self.doc, self.teil, self.lage, stange, self.achse(), job=self.job
                )
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"4-Achs-Bearbeitung: {fehler}\n")
            self._hinweis(tr("va.fehler", fehler=str(fehler)))
            return False
        self._stange_jetzt = stange
        if erstes_mal:
            self._job_zeigen()
        self._auffrischen()
        return True

    def _rohteil_aendern(self):
        """Beim Ändern vor jeder Änderung in Schritt 1: die Transaktion „Stange ändern“ öffnen
        (einmal) und die Rundachse aller „Rundum schruppen“ des Jobs nachziehen – so rechnen
        sie gleich mit der neuen Lage."""
        if not self._transaktion_offen:
            self.doc.openTransaction(tr("va.transaktion.rohteil"))
            self._transaktion_offen = True
        for op in js.operationen(self.job):
            if vo.ist_rundum(op):
                vo.setze_achse(op, self.achse())

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
            klon.ViewObject.Transparency = 0
            if stl_teil.aus_stl(self.teil):  # ohne die Kanten der Dreiecke, wie das Netz
                from .gui_stl import ohne_kanten

                ohne_kanten(klon)
            # Ein Teil aus einem STL als Netz – am Geist 1,8 s weniger beim ersten Klick.
            stl_anzeige.zeigen(klon, True)
        if self.teil.ViewObject is not None:
            self._sichtbar_vorher = (self.teil, stl_anzeige.sichtbar(self.teil))
            stl_anzeige.zeigen(self.teil, False)
        self._stange_anzeigen(*STANGE_ANZEIGE, waehlbar=False)

    def _stange_anzeigen(self, darstellung, durchsicht, waehlbar):
        ansicht = self.job.Stock.ViewObject if self.job and self.job.Stock else None
        if ansicht is None:
            return
        ansicht.DisplayMode = darstellung
        ansicht.Transparency = durchsicht
        ansicht.Selectable = waehlbar

    def _stange_zurueck(self):
        """Beim Ändern: die Stange wieder so, wie sie vor dem Fenster aussah."""
        if self._stange_vorher is None:
            return
        darstellung, durchsicht, waehlbar = self._stange_vorher
        self._stange_vorher = None
        self._stange_anzeigen(darstellung, durchsicht, waehlbar)

    def _anzeige_wie_in_cam(self):
        """Nach „Anlegen“ sieht die Stange aus wie jedes Rohteil in CAM."""
        self._stange_anzeigen(*STANGE_CAM, waehlbar=True)

    def _sichtbarkeit_zurueck(self):
        if self._sichtbar_vorher is not None:
            teil, sichtbar = self._sichtbar_vorher
            if teil.ViewObject is not None:
                stl_anzeige.zeigen(teil, sichtbar)
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
        if self.maschinenwahl() is None:  # A, B, C – die Maschine gibt ihre selbst vor
            parameter.SetString(GEMERKT_RUNDACHSE, self.buchstabe())
        self._fraeser_merken()

    def _maschine_merken(self):
        """Die gewählte Maschine merkt sich der Job: „Auf der Maschine prüfen“ nimmt dieselbe
        (D-20). Nur eine gespeicherte – ohne Datei gibt es nichts zu merken."""
        from . import reichweite as rw

        eintrag = self.maschinenwahl()
        if isinstance(eintrag, va.Maschinenwahl) and self.job is not None:
            rw.merke_maschine(self.job, eintrag.assembly.Document.FileName)

    def _fraeser_merken(self):
        schruppen, schlichten = self._gewaehlt()
        if schruppen and self.fraeser() is not None:
            _parameter().SetString(GEMERKT_FRAESER, self.fraeser().kennung)
        if schlichten and self.schlichtfraeser() is not None:
            _parameter().SetString(GEMERKT_SCHLICHTFRAESER, self.schlichtfraeser().kennung)
        if self.plan_an() and self.planfraeser() is not None:
            _parameter().SetString(GEMERKT_PLANFRAESER, self.planfraeser().kennung)
        if self.entgraten_an() and self.entgratfraeser() is not None:
            _parameter().SetString(GEMERKT_ENTGRATFRAESER, self.entgratfraeser().kennung)

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
        self.knopf_umdrehen.setVisible(True)
        if mess.rund:  # V2b: eine runde Fläche, ihre Achse ist die Stangenachse
            art = tr("va.art.mantel", d=groesse_fest(2 * mess.kreis[1], einheit_laenge, 1))
            self.knopf_mitte_flaeche.setText(tr("va.mitte.achse"))
        elif mess.kreis is not None:
            art = tr("va.art.rund", d=groesse_fest(2 * mess.kreis[1], einheit_laenge, 1))
            self.knopf_mitte_flaeche.setText(tr("va.mitte.flaeche"))
        else:
            art = tr("va.art.eben")
            self.knopf_mitte_flaeche.setText(tr("va.mitte.flaeche_eckig"))
        flaeche = self.flaeche
        teilachse = flaeche in vr.TEILACHSEN
        self.knopf_mitte_flaeche.setEnabled(not teilachse)  # ohne Fläche keine Mitte der Fläche
        if teilachse:
            flaeche = tr("va.teilachse.name", achse=flaeche)
            art = tr("va.art.teilachse_minus") if self.umgedreht else tr("va.art.teilachse_plus")
        elif not mess.rund and self.umgedreht:
            art = tr("va.art.am_futter", art=art)
        self.teil_text.setText(tr("va.teil.text", teil=self.teil.Label, flaeche=flaeche, art=art))
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
