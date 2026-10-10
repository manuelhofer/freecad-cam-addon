# SPDX-License-Identifier: LGPL-2.1-or-later
"""Befehl und Assistent „Bearbeitung (Fräsen)“ für ein Teil im Quader (W-006 S3c, E4).

Der Weg: eine Fläche des Teils anklicken – der Job mit dem Rohteil (ein Quader mit Aufmaß je
Seite, wie FreeCADs Job) entsteht sofort –, die Flächen (ebene nach oben fürs Planfräsen,
ohne Wahl die Oberseite; Wände für die Kontur), Werkstoff, dann je Bearbeitung ein Block mit
Haken: Fräser und Einsatz aus der Werkzeugverwaltung, die Werte mit den Vorschlägen grau,
darunter „→ 3 Lagen, 30 Zeilen, etwa 2 min“ – und „Anlegen“ legt Werkzeug-Controller und die
angehakten Operationen an („Planfräsen“, planfraesen; „Kontur“, kontur). Ein Doppelklick auf
eine Operation öffnet den Assistenten zum Ändern mit ihrem Block (gui_vierachs_operation).

Der Assistent „4-Achs-Bearbeitung“ (gui_vierachs) ist das Vorbild; was dort allgemein ist
(Reihen, Befehl mit Transaktion, Zeit in Worten), kommt von dort. Jede Strategie ist eine
_Strategie (was sie braucht, wie sie rechnet), ihr Block im Fenster ein _Block; weitere
(Tasche adaptiv, Bohren) kommen so dazu (S3f, S3g).
"""

import contextlib
import html
import math
import os
from collections import OrderedDict

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, einheiten, spannung, symbol
from . import aufloesung as au
from . import bahn as bn
from . import bleistift as bst
from . import bohren as bh
from . import bohrung as bo
from . import bohrung_bahn as bb
from . import entgrat_bahn as eb
from . import entgraten as eg
from . import entgraten3d as e3op
from . import flanke as flop
from . import flanke_bahn as flb
from . import fraeserform as ff
from . import gewinde as gw
from . import gewinde_bahn as gfb
from . import gewindefraesen as gf
from . import hoehenfeld as hf
from . import job_schnittwerte as js
from . import kontur as ko
from . import kontur_bahn as kb
from . import magazin as mg
from . import maschinenspeicher as msp
from . import materialstand as mst
from . import messstopp as ms
from . import nut as nu
from . import nut_bahn as nb
from . import planfraesen as pf
from . import planfraesen_bahn as pfb
from . import raeumen as ra
from . import raeumen_bahn as rb
from . import reiben as rbn
from . import reichweite as rw
from . import schlichten3d as s3op
from . import schlichten3d_bahn as s3b
from . import schruppen3d as r3op
from . import schruppen3d_bahn as r3b
from . import senken as sk
from . import uebergabe_werkzeuge as ue
from . import vierachs_bahn as vb
from . import vierachs_plan as vplan
from . import vierachs_planbahn as vp
from . import vierachs_rohteil as vr
from . import werkzeuge as wz
from . import werkzeugform as wf
from . import zielzeit as zz
from .gui_hilfe import kopfzeile
from .gui_kollision import GELB
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
# Auf diesen Maschinen dreht eine Rundachse das Teil: Das Rohteil ist eine Stange (W-011 S3).
STANGE_ARTEN = (msp.DREHMASCHINE, msp.FRAESE_4)
GEMERKT_FRAESER = "BaFraeser"  # Kennung des zuletzt gewählten Fräsers (Planfräsen)
GEMERKT_KONTURFRAESER = "BaKonturFraeser"  # … für die Kontur
GEMERKT_RAEUMFRAESER = "BaRaeumFraeser"  # … fürs Räumen
GEMERKT_RESTRAEUMFRAESER = "BaRestRaeumFraeser"  # … fürs Rest räumen
GEMERKT_SCHLICHTFRAESER = "BaSchlichtFraeser"  # … fürs Schlichten danach
GEMERKT_NUTFRAESER = "BaNutFraeser"  # … für die Nut
GEMERKT_BOHRFRAESER = "BaBohrFraeser"  # … fürs Bohrungsfräsen
GEMERKT_BOHRER = "BaBohrer"  # … fürs Bohren
GEMERKT_FLANKENFRAESER = "BaFlankenFraeser"  # … für die Flanke (5 Achsen simultan)
GEMERKT_REIBAHLE = "BaReibahle"  # … fürs Reiben
GEMERKT_GEWINDEBOHRER = "BaGewindebohrer"  # … fürs Gewinde
GEMERKT_GEWINDEFRAESER = "BaGewindefraeser"  # … fürs Gewindefräsen
GEMERKT_FASENFRAESER = "BaFasenfraeser"  # … fürs Entgraten
GEMERKT_ENTGRATEN3D = "BaEntgraten3D"  # … fürs Entgraten 3D
GEMERKT_ANBOHRER = "BaAnbohrer"  # … fürs Zentrieren
GEMERKT_SENKER = "BaSenker"  # … fürs Senken
GEMERKT_RESTFRAESER = "BaRestFraeser"  # … fürs Restmaterial
GEMERKT_FRAESER_3D = "BaFraeser3D"  # … fürs 3D-Schlichten
GEMERKT_RESTFRAESER_3D = "BaRestFraeser3D"  # … fürs Restschlichten
GEMERKT_RESTSCHRUPPFRAESER = "BaRestSchruppFraeser"  # … fürs Restschruppen
# Der zuletzt gewählte Nullpunkt: „modell“ oder „sx,sy,sz“ (nullpunkte()); ohne Eintrag die
# Mitte oben des Rohteils (Manuel, 2026-10-02: „als Auswahl für den Nullpunkt ist Standard
# erstmal oben mittig bitte ausgewählt“).
GEMERKT_NULLPUNKT = "BaNullpunkt"
NULLPUNKT_VORGABE = (0, 0, 1)
REST_BREITE = 0.01  # mm – „Material neben der Wand“ beim Restmaterial: eine Bahn bei Radius
VORSCHAU_MS = 400  # nach der letzten Eingabe so lange warten, dann die Bahn rechnen
NACHZIEHEN_MS = 250  # das Rohteil nach einer Eingabe nachziehen
VORSCHAU_MERK = 60  # so viele Vorschauen merkt sich der Assistent (_Block.vorschau_rechnen)
ROHTEIL_FELDER = ("oben", "seite", "unten")
VERSATZ_FELDER = ("x", "y", "z")  # der Nullpunkt, vom gewählten Punkt aus verschoben


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def _mm(wert):
    """Eine Länge des Rohteils (Quantity oder Zahl) in mm."""
    try:
        return float(wert.getValueAs("mm"))
    except AttributeError:
        return float(wert)


def _ziel_minuten(minuten):
    """„0,4 min“, „7,4 min“ unter 10 Minuten, darüber wie _zeit_text („31 min“, „2 h 5 min“)."""
    if minuten < 10.0:
        return tr("ba.ziel.minuten", min=dezimal(f"{minuten:.1f}"))
    return _zeit_text(minuten)


def _ziel_werkzeug(werkzeug):
    """„T2 Messerkopf Ø 50“."""
    d = groesse_zeigen(werkzeug.durchmesser, einheiten.LAENGE) or "0"
    return tr(
        "ba.ziel.werkzeug", nummer=wz.nummer_text(werkzeug), art=wz.art_text(werkzeug.art), d=d
    )


def _grau(text=""):
    """Ein grauer Satz – Erklärungen und gerechnete Werte (wie in gui_vierachs)."""
    etikett = QtGui.QLabel(text)
    etikett.setStyleSheet(f"color: {GRAU_TEXT};")
    etikett.setWordWrap(True)
    return etikett


class _Satz(QtGui.QLabel):
    """Ein Satz, der an zwei Stellen steht – im Überblick (Schritt 2) und bei den Einstellungen
    (Schritt 3): setText schreibt auch in den Spiegel."""

    def __init__(self, farbe):
        super().__init__()
        self.spiegel = QtGui.QLabel()
        self._erlaubt = True
        for etikett in (self, self.spiegel):
            etikett.setWordWrap(True)
            etikett.setStyleSheet(f"color: {farbe};")
        self._sichtbarkeit()

    def setText(self, text):  # noqa: N802 – Qt-Name
        super().setText(text)
        self.spiegel.setText(text)
        self._sichtbarkeit()

    def erlauben(self, an):
        """Im Überblick nur, wenn die Strategie zur Wahl passt."""
        self._erlaubt = bool(an)
        self._sichtbarkeit()

    def _sichtbarkeit(self):
        # Leer nimmt der Satz keinen Platz (ein leeres Etikett ist eine Zeile hoch).
        leer = not self.text()
        self.setVisible(self._erlaubt and not leer)
        self.spiegel.setVisible(not leer)


def _eintauchwinkel(werkzeug):
    """Der Eintauchwinkel (Grad) für Helix und Rampe: der am Fräser, sonst die Vorgabe – in der
    Vorschau und in der angelegten Operation derselbe (bis P-2026-10-02-65 legte „Anlegen“ Nut
    und Bohrung mit 5° an, die Vorschau rechnete mit den 3° des Standardfräsers)."""
    return float(getattr(werkzeug, "eintauchwinkel", 0.0) or 0.0) or vb.EINTAUCHWINKEL


def _material_text(bahn):
    """„noch 5,6 cm³ – 11,1 cm³ hat „Räumen T1“ schon weggenommen“ – für eine Bahn mit
    Materialstand (W-012), wenn die Operationen davor dort etwas weggenommen haben; sonst ""."""
    weg, davor = getattr(bahn, "weg", 0.0), getattr(bahn, "davor", None)
    if not davor or weg <= 0:
        return ""
    einheit = einheiten.einheit(einheiten.VOLUMEN)
    noch = f"{groesse_fest(bahn.noch / 1000.0, einheiten.VOLUMEN, 1)} {einheit}"
    weg = f"{groesse_fest(weg / 1000.0, einheiten.VOLUMEN, 1)} {einheit}"
    wer = mst.wer_text(davor)
    if len(davor) == 1:
        return tr("ba.material.einer", noch=noch, weg=weg, wer=wer)
    return tr("ba.material.mehrere", noch=noch, weg=weg, wer=wer)


def _waende_um(form, boeden):
    """Die Wände des Teils, die unten an die Böden `boeden` stoßen – Zapfen und Inseln auf ihnen,
    Absätze davor: die nach dem Räumen das Aufmaß tragen (kontur_bahn.boeden_vor)."""
    boeden = set(boeden)
    return [name for name, vor in _boeden_vor_je_wand(form) if vor & boeden]


_BOEDEN_VOR = {}  # Kennung der Form → [(Wand, frozenset der Böden vor ihr)]


def _boeden_vor_je_wand(form):
    """Je Wand des Teils die Böden vor ihr (kontur_bahn.boeden_vor) – je Form einmal gerechnet:
    Der Assistent fragt je Vorschau mehrmals (am Testteil 0,7 s je Mal)."""
    try:
        kasten = form.BoundBox
        schluessel = (form.hashCode(), len(form.Faces), round(form.Volume, 6)) + tuple(
            round(v, 6) for v in (kasten.XMin, kasten.XMax, kasten.YMin, kasten.YMax)
        )
    except Exception:  # eine Form ohne Prüfsumme: rechnen
        schluessel = None
    if schluessel is not None and schluessel in _BOEDEN_VOR:
        return _BOEDEN_VOR[schluessel]
    ergebnis = []
    for i, flaeche in enumerate(form.Faces):
        name = f"Face{i + 1}"
        if not kb.ist_wand(flaeche):
            continue
        vor = kb.boeden_vor(form, [name])
        if vor:
            ergebnis.append((name, frozenset(vor)))
    if schluessel is not None:
        if len(_BOEDEN_VOR) > 16:
            _BOEDEN_VOR.clear()
        _BOEDEN_VOR[schluessel] = ergebnis
    return ergebnis


def _aussennormale(form, name):
    """Die Normale der ebenen Fläche `name` („Face6“) von `form` aus dem Material heraus – None,
    wenn es sie nicht gibt oder sie nicht eben ist."""
    nummer = int(name[4:]) - 1 if name.startswith("Face") and name[4:].isdigit() else -1
    if not 0 <= nummer < len(form.Faces) or not vr.ist_eben(form.Faces[nummer]):
        return None
    return vr.aussennormale(form.Faces[nummer])


def _schraeg(form, name):
    """Wie weit die ebene Fläche `name` gegen die Waagerechte geneigt ist (Grad) – None, wenn sie
    nicht eben ist, nach oben zeigt, eine senkrechte Wand ist (das fräst der Job ohne Schwenken)
    oder nach unten zeigt. Dann geht sie geschwenkt (3+2, gui_schwenken)."""
    normale = _aussennormale(form, name)
    if normale is None:
        return None
    winkel = math.degrees(math.acos(max(-1.0, min(1.0, normale.z))))
    if winkel < 0.5 or abs(winkel - 90.0) < 0.5 or winkel > 179.5:
        return None
    return winkel


def _klappknopf(text, tooltip):
    """Ein fetter Knopf mit Pfeil, der einen Bereich auf- und zuklappt."""
    knopf = QtGui.QToolButton()
    knopf.setArrowType(QtCore.Qt.RightArrow)
    knopf.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
    knopf.setText(text)
    knopf.setToolTip(tooltip)
    knopf.setAutoRaise(True)
    knopf.setCheckable(True)
    schrift = knopf.font()
    schrift.setBold(True)
    knopf.setFont(schrift)
    return knopf


def nullpunkte():
    """[(Text, (sx, sy, sz))] – die 22 Punkte des Rohteil-Quaders zur Wahl als Nullpunkt
    (Manuel, 2026-10-01): die 8 Ecken, die 12 Kantenmitten, die Mitte oben und unten;
    sx, sy, sz je −1, 0 oder 1 – links/rechts ist X, vorne/hinten Y, unten/oben Z."""
    x_namen = {-1: tr("np.links"), 1: tr("np.rechts")}
    y_namen = {-1: tr("np.vorne"), 1: tr("np.hinten")}
    z_namen = {-1: tr("np.unten"), 1: tr("np.oben")}
    punkte = []
    for sz in (1, -1):
        for sy in (-1, 1):
            for sx in (-1, 1):
                text = tr("np.ecke", x=x_namen[sx], y=y_namen[sy], z=z_namen[sz])
                punkte.append((text, (sx, sy, sz)))
    for sz in (1, -1):
        for sy in (-1, 1):  # Kanten längs X
            punkte.append((tr("np.kante", a=y_namen[sy], b=z_namen[sz]), (0, sy, sz)))
        for sx in (-1, 1):  # Kanten längs Y
            punkte.append((tr("np.kante", a=x_namen[sx], b=z_namen[sz]), (sx, 0, sz)))
    for sy in (-1, 1):  # die senkrechten Kanten
        for sx in (-1, 1):
            punkte.append((tr("np.kante", a=x_namen[sx], b=y_namen[sy]), (sx, sy, 0)))
    for sz in (1, -1):
        punkte.append((tr("np.mitte", a=z_namen[sz]), (0, 0, sz)))
    return punkte


def nullpunkt_vorgeben(lage):
    """Merkt `lage` ((sx, sy, sz) aus nullpunkte(), None: wie im Modell) als Nullpunkt für den
    nächsten Job – wie nach „Anlegen“ mit dieser Wahl."""
    text = "modell" if lage is None else ",".join(str(int(s)) for s in lage)
    _parameter().SetString(GEMERKT_NULLPUNKT, text)


def _gemerkter_nullpunkt():
    """Der gemerkte Nullpunkt (sx, sy, sz) – None: wie im Modell; ohne Eintrag die Vorgabe."""
    text = _parameter().GetString(GEMERKT_NULLPUNKT, "").strip()
    if text == "modell":
        return None
    try:
        lage = tuple(int(s) for s in text.split(","))
    except ValueError:
        return NULLPUNKT_VORGABE
    return lage if len(lage) == 3 else NULLPUNKT_VORGABE


def ist_bearbeitung(op):
    """Eine Operation dieses Assistenten – „Planfräsen“, „Räumen“, „Nut“, „Bohrung fräsen“,
    „Kontur“, „Entgraten“, „Gewinde fräsen“, „3D-Schruppen“, „3D-Schlichten“ oder
    „Bleistift“?"""
    return (
        s3op.ist_schlichten3d(op)
        or flop.ist_flanke(op)
        or r3op.ist_schruppen3d(op)
        or bst.ist_bleistift(op)
        or pf.ist_planfraesen(op)
        or ra.ist_raeumen(op)
        or nu.ist_nut(op)
        or bo.ist_bohrungsfraesen(op)
        or ko.ist_kontur(op)
        or eg.ist_entgraten(op)
        or gf.ist_gewindefraesen(op)
    )


class BefehlBearbeitung:
    """Befehl in der Werkzeugleiste: öffnet den Assistenten für die gewählte Fläche – oder
    zum Ändern, wenn „Planfräsen“ oder „Kontur“ gewählt ist."""

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
        FreeCADGui.Control.showDialog(
            BearbeitungPanel(
                dokument, gewaehlte_flaeche(dokument), angeklickt=angeklicktes_teil(dokument)
            )
        )


def gewaehlte_operation(dokument):
    """Das gewählte „Planfräsen“ oder „Kontur“ – oder, ist ein Job oder sein Ordner
    „Operations“ gewählt, seine erste solche Operation; sonst None."""
    jobs = js.jobs(dokument)
    for objekt in FreeCADGui.Selection.getSelection(dokument.Name):
        if ist_bearbeitung(objekt):
            return objekt
        job = next(
            (j for j in jobs if objekt is j or objekt is getattr(j, "Operations", None)), None
        )
        if job is not None:
            gefunden = [o for o in js.operationen(job) if ist_bearbeitung(o)]
            if gefunden:
                return gefunden[0]
    return None


def angeklicktes_teil(dokument):
    """Das angeklickte Objekt mit Form – ein Modell-Klon eines Jobs bleibt der Klon (so weiß
    man, in welchem Job man geklickt hat); None ohne Auswahl."""
    for auswahl in FreeCADGui.Selection.getSelectionEx(dokument.Name, 0):
        for unterelement in auswahl.SubElementNames or [""]:
            teil, _flaeche = _entlang(dokument, auswahl.Object, unterelement)
            if teil is not None:
                return teil
    return None


def vorhandener_job(dokument, teil, angeklickt=None):
    """Der Job, in den ein weiterer Lauf am Teil `teil` geht (W-012 M2; Manuel, 2026-10-02:
    „Frage 1. A“): der, dessen Teil man angeklickt hat (`angeklickt`: sein Modell-Klon), sonst
    der zuletzt angelegte mit diesem Teil. Nur Jobs im Quader – einer mit Stange gehört dem
    4-Achs-Assistenten. None, wenn das Teil noch keinen hat."""
    passende = []
    for job in js.jobs(dokument):
        try:
            klon = vr.modell(job)
        except (AttributeError, IndexError):
            continue
        if vr.original(klon) is not teil or hasattr(getattr(job, "Stock", None), "Radius"):
            continue
        if angeklickt is not None and angeklickt is klon:
            return job
        passende.append(job)
    return passende[-1] if passende else None


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

    def addSelection(self, _dokument, objekt, unterelement, punkt):
        if not unterelement:
            return
        # Erst wenn FreeCAD mit der Auswahl fertig ist – der Assistent ändert das Dokument.
        QtCore.QTimer.singleShot(0, lambda: self.panel.angeklickt(objekt, unterelement, punkt))


class _NurFlaechen:
    """Anklicken lassen sich Flächen – mit Job nur die des Teils darin, und dort auch Kanten (für
    „Entgraten 3D“; Manuel, 2026-10-05: „Kanten anklicken muss sein“)."""

    def __init__(self, panel):
        self.panel = panel

    def allow(self, _dokument, objekt, unterelement):
        weg = unterelement.split(".") if unterelement else []
        if not weg or not weg[-1].startswith(("Face", "Edge")):
            return False
        job = self.panel.job
        if job is None:
            return weg[-1].startswith("Face")  # ohne Job beginnt ein Klick auf eine Fläche
        klon = vr.modell(job).Name
        return getattr(objekt, "Name", "") == klon or klon in weg


# --- Die Strategien ---------------------------------------------------------------------------


class _Strategie:
    """Eine 2,5D-Strategie im Assistenten: ihre Texte, Felder, Vorschläge, Vorschau, Anlegen
    und Ändern. Die Schlüssel stehen wörtlich in tr(…) – so findet sie die Sprachprüfung."""

    kennung = ""
    gemerkt = ""  # Parameter: der zuletzt gewählte Fräser
    nimmt_kanten = False  # bekommt auch angeklickte Kanten („Edge12“) – nur Entgraten 3D
    einsatz_reihenfolge = ()  # welcher Einsatz vorgewählt ist
    bevorzugt = wz.SCHAFTFRAESER  # diese Art vorgewählt, wenn sonst nichts entscheidet
    # mm – das Raster, in dem die Operation ihre Bahn rechnet (aufloesung.py); None: hat keins.
    aufloesung = None

    def aufloesung_erklaerung(self, vorschlag):
        """Die Erklärung zum Feld „Auflösung“ – Kanten haben eine eigene."""
        return tr("ba.aufloesung.tooltip", vorschlag=vorschlag)

    def titel(self):
        return ""

    def text(self):
        return ""

    def fraeser_tooltip(self):
        return ""

    def einsatz_tooltip(self):
        return ""

    def felder(self):
        """((Name, Beschriftung, Tooltip) …) der Zahlenfelder."""
        return ()

    def haken(self):
        """((Name, Beschriftung, Tooltip, Vorgabe) …) der Ja/Nein-Felder."""
        return ()

    def haken_gesperrt(self, feld, block):
        """Warum der Haken `feld` hier nicht geht (ein kurzer Satz) – None, wenn er geht."""
        return None

    def haken_verborgen(self, feld, block):
        """Fehlt der Haken `feld` hier ganz (er hätte an dieser Maschine nie Sinn)?"""
        return False

    def zeit(self, bahn, vorschub, eintauchen):
        """Minuten der Vorschau (bahn.zeit über ihre Punkte, mm/min)."""
        return bn.zeit(bahn.punkte, vorschub, eintauchen)

    def passt(self, form, name):
        """Kann die Strategie etwas mit der Fläche `name` von `form` anfangen?"""
        return False

    def werkzeug_passt(self, werkzeug):
        """Arbeitet die Strategie mit diesem Werkzeug? Vorgabe: ein Fräser mit ebener Stirn."""
        form = ff.von_werkzeug(werkzeug)
        return form is not None and vp.ebener_radius(form) > 0

    def flaechen_fuer(self, form, gewaehlte):
        return [name for name in gewaehlte if self.passt(form, name)]

    def vorgeschlagen(self, form, gewaehlte):
        """Ist der Haken von sich aus gesetzt?"""
        return bool(self.flaechen_fuer(form, gewaehlte))

    def moeglich(self, form, gewaehlte):
        """Geht die Strategie mit dieser Wahl überhaupt?"""
        return bool(self.flaechen_fuer(form, gewaehlte))

    def unmoeglich_text(self):
        return ""

    def vorschlag(self, feld, werkzeug, einsatz):
        return 0.0

    def platzhalter(self, feld, werkzeug, einsatz):
        if feld == "aufloesung":
            return groesse_zeigen(self.aufloesung, einheiten.LAENGE)
        return groesse_zeigen(self.vorschlag(feld, werkzeug, einsatz), einheiten.LAENGE) or "0"

    def vorschau(self, job, werkzeug, werte, flaechen):
        raise NotImplementedError

    def ergebnis_text(self, bahn, zeit):
        return ""

    def lege_an(self, job, tc, werte, flaechen):
        raise NotImplementedError

    def aendere(self, op, tc, werte, flaechen):
        raise NotImplementedError

    def ist(self, op):
        return False

    def werte_von(self, op):
        """{Feld: Wert} der Operation – zum Ändern."""
        return {}


class _Planfraesen(_Strategie):
    kennung = "planfraesen"
    aufloesung = pf.pb.SCHRITT
    gemerkt = GEMERKT_FRAESER
    tief = False  # mit „Schruppen“ schneller als mit „Planen“ (Panel, _planeinsatz_waehlen)

    @property
    def einsatz_reihenfolge(self):
        if self.tief:
            return (wz.SCHRUPPEN, wz.PLANEN, wz.SCHLICHTEN)
        return (wz.PLANEN, wz.SCHRUPPEN, wz.SCHLICHTEN)

    def titel(self):
        return tr("ba.planfraesen")

    def text(self):
        return tr("ba.planfraesen.text")

    def fraeser_tooltip(self):
        return tr("ba.planfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.planeinsatz.tooltip")

    def felder(self):
        return (
            ("zustellung", tr("ba.zustellung"), tr("ba.zustellung.tooltip")),
            ("zeilenabstand", tr("ba.zeilenabstand"), tr("ba.zeilenabstand.tooltip")),
            ("aufmass", tr("ba.aufmass"), tr("ba.aufmass.tooltip")),
        )

    def haken(self):
        return (
            (
                "nur_gleichlauf",
                tr("ba.nur_gleichlauf"),
                tr("ba.nur_gleichlauf.tooltip"),
                False,
            ),
        )

    def passt(self, form, name):
        return bool(hf.ebenen_oben(form, [name]))

    def vorgeschlagen(self, form, gewaehlte):
        return not gewaehlte or bool(self.flaechen_fuer(form, gewaehlte))

    def moeglich(self, form, gewaehlte):
        return True  # ohne ebene Fläche die Oberseite

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else pf.ZUSTELLUNG
        if feld == "zeilenabstand":
            if werkzeug is None:
                return 0.0
            return vplan.zeilenabstand_vorschlag(werkzeug, einsatz, ff.von_werkzeug(werkzeug))
        return pf.AUFMASS

    def vorschau(self, job, werkzeug, werte, flaechen):
        return pf.vorschau(
            job,
            job.Model.Group,
            ff.von_werkzeug(werkzeug),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            flaechen,
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
            nur_gleichlauf=werte.get("nur_gleichlauf", False),
            stand=werte.get("materialstand"),
        )

    def ergebnis_text(self, bahn, zeit):
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        zeilen = tr("ba.zahl.zeile") if bahn.zeilen == 1 else tr("ba.zahl.zeilen", n=bahn.zeilen)
        if bahn.flaechen > 1:
            flaechen = tr("ba.zahl.flaechen", n=bahn.flaechen)
            text = tr(
                "ba.ergebnis_flaechen", flaechen=flaechen, lagen=lagen, zeilen=zeilen, zeit=zeit
            )
        else:
            text = tr("ba.ergebnis", lagen=lagen, zeilen=zeilen, zeit=zeit)
        # Die Zeilenrichtung ist gerechnet, nicht geraten: beide Richtungen, die schnellere –
        # und wie viel langsamer die andere wäre (Grundsatz 0: die Zeit entscheidet).
        richtungen = set(bahn.richtungen)
        if bahn.zeit_andere is None or len(richtungen) != 1 or bahn.zeit <= 0:
            return text
        laengs_x = richtungen.pop()
        richtung, andere = ("X", "Y") if laengs_x else ("Y", "X")
        prozent = int(round((bahn.zeit_andere / bahn.zeit - 1.0) * 100.0))
        if prozent < 1:
            return tr("ba.richtung.gleich", text=text, richtung=richtung, andere=andere)
        return tr(
            "ba.richtung.langsamer", text=text, richtung=richtung, andere=andere, prozent=prozent
        )

    def lege_an(self, job, tc, werte, flaechen):
        return pf.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            flaechen=flaechen,
            nur_gleichlauf=werte.get("nur_gleichlauf", False),
        )

    def aendere(self, op, tc, werte, flaechen):
        pf.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            flaechen=flaechen,
            nur_gleichlauf=werte.get("nur_gleichlauf", False),
        )

    def ist(self, op):
        return pf.ist_planfraesen(op)

    def werte_von(self, op):
        return {
            "zustellung": float(op.Zustellung),
            "zeilenabstand": float(op.Zeilenabstand),
            "aufmass": float(op.Aufmass),
            "nur_gleichlauf": bool(getattr(op, "NurGleichlauf", False)),
        }


class _Raeumen(_Strategie):
    kennung = "raeumen"
    aufloesung = ra.rb.SCHRITT
    gemerkt = GEMERKT_RAEUMFRAESER
    einsatz_reihenfolge = (wz.SCHRUPPEN, wz.PLANEN, wz.SCHLICHTEN)

    def titel(self):
        return tr("ba.raeumen")

    def text(self):
        return tr("ba.raeumen.text")

    def fraeser_tooltip(self):
        return tr("ba.raeumfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.raeumeinsatz.tooltip")

    def felder(self):
        return (
            ("zustellung", tr("ba.zustellung"), tr("ba.zustellung.tooltip")),
            ("zeilenabstand", tr("ba.zeilenabstand"), tr("ba.raeumen.zeilenabstand.tooltip")),
            ("aufmass", tr("ba.aufmass_wand"), tr("ba.aufmass_wand.tooltip")),
            ("aufmass_boden", tr("ba.aufmass_boden"), tr("ba.aufmass_boden.tooltip")),
        )

    def haken(self):
        # Schlichten und Messstopp danach hat der eigene Block „Schlichten danach“
        # (_SchlichtenDanach; bis 0.126.0 zwei Haken hier).
        return (("gleichlauf", tr("ba.gleichlauf"), tr("ba.gleichlauf.tooltip"), True),)

    def passt(self, form, name):
        return bool(hf.ebenen_oben(form, [name])) or bool(kb.waende(form, [name]))

    def flaechen_fuer(self, form, gewaehlte):
        """Die ebenen Flächen nach oben – und die Böden der Taschen, deren Wände gewählt sind."""
        ebenen = [name for name in gewaehlte if hf.ebenen_oben(form, [name])]
        waende = [name for name in gewaehlte if name not in ebenen and kb.waende(form, [name])]
        for boden in rb.taschenboeden(form, waende):
            if boden not in ebenen:
                ebenen.append(boden)
        return ebenen

    def vorgeschlagen(self, form, gewaehlte):
        # Von sich aus nur für ebene Flächen (die Oberseite ohne Wahl); für gewählte
        # Taschenwände bleibt die Kontur der Vorschlag – Räumen lässt sich dazu anhaken.
        return not gewaehlte or any(hf.ebenen_oben(form, [name]) for name in gewaehlte)

    def moeglich(self, form, gewaehlte):
        return True  # ohne ebene Fläche die Oberseite

    def unmoeglich_text(self):
        return tr("ba.raeumen.keine_flaeche")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else ra.ZUSTELLUNG
        if feld == "zeilenabstand":
            if werkzeug is None or werkzeug.durchmesser <= 0:
                return 0.0
            r = werkzeug.durchmesser / 2
            ae = einsatz.ae if einsatz is not None and einsatz.ae > 0 else r / 4
            return min(ae, r)
        if feld == "aufmass":
            return ra.AUFMASS
        return 0.0  # Aufmaß am Boden: die Fläche ist fertig

    def vorschau(self, job, werkzeug, werte, flaechen):
        argumente = (
            job,
            job.Model.Group,
            ff.von_werkzeug(werkzeug),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            flaechen,
        )
        weiter = {
            "aufmass_boden": werte["aufmass_boden"],
            "gleichlauf": werte["gleichlauf"],
            "schneidenlaenge": float(werkzeug.schneidenlaenge or 0.0),
            "vorschub": werte.get("vorschub", 0.0),
            "eintauchen": werte.get("eintauchen", 0.0),
            "stand": werte.get("materialstand"),
            "variante": werte.get("variante"),
            "freivorschub": werte.get("freivorschub", ra.FREIVORSCHUB),
        }
        bahn = ra.vorschau(*argumente, **weiter)
        if bahn.variante == "adaptiv" or weiter["variante"] == rb.RINGE:
            return bahn  # adaptiv hält die Last nach seiner Bauart; „ringe“ ohne Blick auf sie
        # Ringe: Die grobe Vorschau rechnet eine etwas andere Bahn und kann die Last unterschätzen
        # – am Testteil maß sie in der dreieckigen Tasche (Ø 6) 1,7 ae, die genaue Bahn, die die
        # Maschine fährt, 4,5 ae (Werkzeugbruch; Manuel, 2026-10-04). Dann gilt die genaue.
        try:
            return ra.bahn_fuer(*argumente, **weiter)
        except ValueError:
            return bahn

    def ergebnis_text(self, bahn, zeit):
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        if bahn.variante == "adaptiv":
            ringe = tr("ba.zahl.adaptiv")  # die Zahl seiner Bahnen sagt nichts
        elif bahn.variante == rb.STICHE:
            ringe = tr("ba.zahl.stiche", n=bahn.laeufe)  # Manuels Räumen: Stiche und Ringe
        else:
            ringe = tr("ba.zahl.ring") if bahn.ringe == 1 else tr("ba.zahl.ringe", n=bahn.ringe)
        if bahn.flaechen > 1:
            flaechen = tr("ba.zahl.flaechen", n=bahn.flaechen)
            text = tr(
                "ba.ergebnis_raeumen_flaechen",
                flaechen=flaechen,
                lagen=lagen,
                ringe=ringe,
                zeit=zeit,
            )
        else:
            text = tr("ba.ergebnis_raeumen", lagen=lagen, ringe=ringe, zeit=zeit)
        # Ringe wären schneller gewesen, halten die Last aber nicht (Manuel, 2026-10-02: die
        # schnellste gewinnt nur, wenn der ae im Rahmen bleibt) – das Fenster sagt es.
        ueberlastet = getattr(bahn, "ueberlastet", None) or {}
        schneller = [v for v in ueberlastet if 0 < bahn.zeiten.get(v, 0.0) < bahn.zeit]
        if not getattr(bahn, "haelt", True):
            last = dezimal(f"{ueberlastet.get(bahn.variante, 0.0):.1f}")
            text = tr("ba.raeumen.haelt_nicht", text=text, last=last)
        elif schneller:
            variante = min(schneller, key=lambda v: bahn.zeiten[v])
            prozent = int(round((1.0 - bahn.zeiten[variante] / bahn.zeit) * 100.0))
            last = dezimal(f"{ueberlastet[variante]:.1f}")
            text = tr("ba.raeumen.ueberlastet", text=text, prozent=prozent, last=last)
        if getattr(bahn, "gebremst", 0):
            langsam = min(p.anteil for p in bahn.punkte if not p.eilgang)
            text = tr(
                "ba.raeumen.gebremst",
                text=text,
                saetze=bahn.gebremst,
                prozent=int(round(langsam * 100.0)),
            )
        return text

    def lege_an(self, job, tc, werte, flaechen):
        return ra.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["aufmass_boden"],
            werte["gleichlauf"],
            flaechen=flaechen,
            variante=werte.get("variante", "automatisch"),
            freivorschub=werte.get("freivorschub", ra.FREIVORSCHUB),
        )

    def aendere(self, op, tc, werte, flaechen):
        ra.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["aufmass_boden"],
            werte["gleichlauf"],
            flaechen=flaechen,
            variante=werte.get("variante"),
            freivorschub=werte.get("freivorschub"),
        )

    def ist(self, op):
        return ra.ist_raeumen(op)

    def werte_von(self, op):
        return {
            "zustellung": float(op.Zustellung),
            "zeilenabstand": float(op.Zeilenabstand),
            "aufmass": float(op.Aufmass),
            "aufmass_boden": float(op.AufmassBoden),
            "gleichlauf": bool(op.Gleichlauf),
        }


class _RestRaeumen(_Raeumen):
    """Rest räumen (W-013 T3, B-007): räumt mit einem kleineren Fräser die Taschen, in die der
    Fräser des Räumens nicht passt – ein zweites „Räumen“, nur dort, gleich nach dem ersten.
    Welche Taschen das sind, sagt die Vorschau des Räumens (Raeumbahn.ausgelassen); Haken und
    Fräser setzt das Fenster (BearbeitungPanel._restraeumen_einrichten)."""

    kennung = "restraeumen"
    gemerkt = GEMERKT_RESTRAEUMFRAESER

    def titel(self):
        return tr("ba.restraeumen")

    def text(self):
        return tr("ba.restraeumen.text")

    def haken(self):
        return (("gleichlauf", tr("ba.gleichlauf"), tr("ba.gleichlauf.tooltip"), True),)

    def vorgeschlagen(self, form, gewaehlte):
        return False  # nach der Vorschau des Räumens: _restraeumen_einrichten

    def moeglich(self, form, gewaehlte):
        return False  # erst, wenn das Räumen eine Tasche auslässt

    def unmoeglich_text(self):
        return tr("ba.restraeumen.nicht")

    def ist(self, op):
        return False  # zum Ändern ist es ein Räumen wie jedes


class _Schlichtbahn:
    """Die Vorschau von „Schlichten danach“: der Boden (raeumen_bahn.Raeumbahn oder None) und die
    Wände (kontur_bahn-Bahn oder None) hintereinander – `punkte` für Zeit und Materialstand."""

    def __init__(self, boden, wand, waende, aufmass_boden, aufmass_wand, messstopp):
        self.boden = boden
        self.wand = wand
        self.waende = list(waende) if wand is not None else []
        self.aufmass_boden = aufmass_boden
        self.aufmass_wand = aufmass_wand
        self.messstopp = messstopp
        self.punkte = list(getattr(boden, "punkte", [])) + list(getattr(wand, "punkte", []))


class _SchlichtenDanach(_Strategie):
    """Schlichten danach (Spezifikation Strategien 12.4, Option A – Manuel, 2026-10-02: „genau
    so“): nach dem Räumen mit eigenem Fräser und Einsatz erst der Boden, dann die Wände, davor
    auf Wunsch ein Messstopp. Der Boden: ein Räumen ohne Aufmaß am Boden auf dem Material, das
    das Räumen ließ – eine Lage, die Ringe des Räumens oder adaptiv, mit dem Zeilenabstand des
    Felds (leer: der halbe Fräserdurchmesser); es lässt das Aufmaß an den Wänden stehen. Die
    Wände: eine Kontur mit Breite = Aufmaß (nur der Zug an der Wand) bis auf den fertigen Boden,
    in Lagen mit der Zustellung des Einsatzes – unten bleibt keine Stufe. Welche Flächen, gibt
    das Fenster vor (BearbeitungPanel._schlichten_danach_zusatz): die Böden, die das Räumen räumt,
    die Wände um sie – ohne die, die die Kontur fährt. Möglich ist der Block, sobald das Räumen
    angehakt ist (BearbeitungPanel._schlichten_danach_einrichten)."""

    kennung = "schlichtendanach"
    gemerkt = GEMERKT_SCHLICHTFRAESER
    einsatz_reihenfolge = (wz.SCHLICHTEN, wz.SCHRUPPEN, wz.PLANEN)

    def titel(self):
        return tr("ba.schlichten_danach")

    def text(self):
        return tr("ba.schlichten_danach.text")

    def fraeser_tooltip(self):
        return tr("ba.schlichten_danach.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.schlichten_danach.einsatz.tooltip")

    def felder(self):
        return (
            (
                "zustellung",
                tr("ba.schlichten_danach.zustellung"),
                tr("ba.schlichten_danach.zustellung.tooltip"),
            ),
            (
                "zeilenabstand",
                tr("ba.schlichten_danach.zeilenabstand"),
                tr("ba.schlichten_danach.zeilenabstand.tooltip"),
            ),
        )

    def haken(self):
        return (
            ("boden", tr("ba.schlichten_danach.boden_haken"), tr("ba.schlichten_danach.boden_haken.tooltip"), True),
            ("waende", tr("ba.schlichten_danach.waende_haken"), tr("ba.schlichten_danach.waende_haken.tooltip"), True),
            ("messstopp", tr("ba.schlichten_danach.messstopp"), tr("ba.schlichten_danach.messstopp.tooltip"), False),
        )  # fmt: skip

    def vorgeschlagen(self, form, gewaehlte):
        return False  # von Hand, wenn das Räumen Aufmaß lässt

    def moeglich(self, form, gewaehlte):
        return False  # erst mit dem Räumen: _schlichten_danach_einrichten

    def unmoeglich_text(self):
        return tr("ba.schlichten_danach.nicht")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            if einsatz is not None and einsatz.ap > 0:
                return einsatz.ap
            return float(getattr(werkzeug, "schneidenlaenge", 0.0) or 0.0) or ra.ZUSTELLUNG
        if feld == "zeilenabstand":
            if werkzeug is None or werkzeug.durchmesser <= 0:
                return 0.0
            return werkzeug.durchmesser / 2  # der Boden: breit, er ist dünn
        return 0.0

    def vorschau(self, job, werkzeug, werte, flaechen):
        form = ff.von_werkzeug(werkzeug)
        stand = werte.get("materialstand")
        schneide = float(werkzeug.schneidenlaenge or 0.0)
        aufmass_boden = float(werte.get("aufmass_boden", 0.0))
        aufmass_wand = float(werte.get("aufmass_wand", 0.0))
        boeden = list(werte.get("boden_flaechen") or [])
        waende = list(werte.get("wand_flaechen") or [])
        boden = wand = None
        if werte["boden"] and boeden and aufmass_boden > 0:
            try:
                boden = ra.vorschau(
                    job, job.Model.Group, form, werte["zustellung"], werte["zeilenabstand"],
                    aufmass_wand, boeden, aufmass_boden=0.0, gleichlauf=werte["gleichlauf"],
                    schneidenlaenge=schneide, vorschub=werte.get("vorschub", 0.0),
                    eintauchen=werte.get("eintauchen", 0.0), stand=stand,
                )  # fmt: skip
            except mst.SchonWeg:
                boden = None
        if werte["waende"] and waende and aufmass_wand > 0:
            try:
                wand = ko.vorschau(
                    job, job.Model.Group, form, werte["zustellung"], aufmass_wand, aufmass_wand,
                    True, waende, breite=aufmass_wand, schneidenlaenge=schneide, stand=stand,
                )  # fmt: skip
            except mst.SchonWeg:
                wand = None
        if boden is None and wand is None:
            raise ValueError(tr("ba.schlichten_danach.nichts"))
        return _Schlichtbahn(
            boden, wand, waende, aufmass_boden, aufmass_wand, bool(werte["messstopp"])
        )

    def ergebnis_text(self, bahn, zeit):
        einheit = einheiten.einheit(einheiten.LAENGE)

        def mm(wert):
            return f"{groesse_zeigen(wert, einheiten.LAENGE) or '0'} {einheit}"

        teile = []
        if bahn.boden is not None:
            teile.append(tr("ba.schlichten_danach.boden", aufmass=mm(bahn.aufmass_boden)))
        if bahn.waende:
            n = len(bahn.waende)
            waende = tr("ba.zahl.wand") if n == 1 else tr("ba.zahl.waende", n=n)
            teile.append(
                tr("ba.schlichten_danach.waende", waende=waende, aufmass=mm(bahn.aufmass_wand))
            )
        if len(teile) == 2:
            was = tr("ba.schlichten_danach.beides", boden=teile[0], waende=teile[1])
        else:
            was = teile[0] if teile else ""
        text = tr("ba.schlichten_danach.ergebnis", was=was, zeit=zeit)
        if bahn.messstopp:
            text = tr("ba.schlichten_danach.stopp", text=text)
        return text

    def ist(self, op):
        return False  # es legt ein Räumen und eine Kontur an – die ändert man je für sich


class _Nut(_Strategie):
    """Langlöcher in Bögen oder mit der Zickzack-Rampe (nut_bahn) – tritt auf dem Grund gegen
    Räumen und Planfräsen an, an den Wänden gegen die Kontur."""

    kennung = "nut"
    gemerkt = GEMERKT_NUTFRAESER
    vollnut = False  # der gewählte Fräser fräst die gewählten Nuten in voller Breite (Panel)

    @property
    def einsatz_reihenfolge(self):
        if self.vollnut:
            return (wz.VOLLNUT, wz.SCHRUPPEN, wz.DYNAMISCH)
        return (wz.DYNAMISCH, wz.SCHRUPPEN, wz.VOLLNUT)

    def titel(self):
        return tr("ba.nut")

    def text(self):
        return tr("ba.nut.text")

    def fraeser_tooltip(self):
        return tr("ba.nutfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.nuteinsatz.tooltip")

    def felder(self):
        return (
            ("zustellung", tr("ba.zustellung"), tr("ba.nut.zustellung.tooltip")),
            ("zeilenabstand", tr("ba.zeilenabstand"), tr("ba.nut.zeilenabstand.tooltip")),
            ("aufmass", tr("ba.aufmass_schlichten"), tr("ba.aufmass_schlichten.tooltip")),
        )

    def haken(self):
        return (
            ("schlichten", tr("ba.wand_schlichten"), tr("ba.wand_schlichten.tooltip"), True),
            ("gleichlauf", tr("ba.gleichlauf"), tr("ba.gleichlauf.tooltip"), True),
        )

    def passt(self, form, name):
        return nb.ist_nut(form, name)

    def flaechen_fuer(self, form, gewaehlte):
        """Der Grund, wie gewählt – eine Wand aber meint die ganze Nut: alle ihre Wände (so
        auch bei der Kontur, die gegen sie antritt)."""
        return nb.ganze_nuten(form, [n for n in gewaehlte if self.passt(form, n)])

    def vorgeschlagen(self, form, gewaehlte):
        """Von sich aus, wenn alle gewählten Flächen zu Nuten gehören – nur Gründe oder nur
        Wände; beides zusammen ist die Folge Räumen und Kontur."""
        if not gewaehlte or not all(self.passt(form, n) for n in gewaehlte):
            return False
        gruende = [n for n in gewaehlte if nb.ist_grund(form, n)]
        return not gruende or len(gruende) == len(gewaehlte)

    def unmoeglich_text(self):
        return tr("ba.nut.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else nu.ZUSTELLUNG
        if feld == "zeilenabstand":
            if werkzeug is None or werkzeug.durchmesser <= 0:
                return 0.0
            r = werkzeug.durchmesser / 2
            ae = einsatz.ae if einsatz is not None and einsatz.ae > 0 else r / 4
            return min(ae, r)
        return nu.AUFMASS

    def vorschau(self, job, werkzeug, werte, flaechen):
        form = ff.von_werkzeug(werkzeug)
        if form is None or vp.ebener_radius(form) <= 0:
            raise ValueError(tr("nt.fehler.form"))
        return nu.vorschau(
            job,
            job.Model.Group,
            float(form.radius),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            flaechen,
            schlichten=werte["schlichten"],
            gleichlauf=werte["gleichlauf"],
            schneidenlaenge=float(werkzeug.schneidenlaenge or 0.0),
            eintauchwinkel=_eintauchwinkel(werkzeug),
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
            stand=werte.get("materialstand"),
            eintauchen_bei=werte.get("eintauchen_bei"),
        )

    def ergebnis_text(self, bahn, zeit):
        nuten = tr("ba.zahl.nut") if bahn.nuten == 1 else tr("ba.zahl.nuten", n=bahn.nuten)
        if bahn.vollnut == bahn.nuten:
            return tr("ba.ergebnis_vollnut", nuten=nuten, zeit=zeit)
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        boegen = tr("ba.zahl.bogen") if bahn.boegen == 1 else tr("ba.zahl.boegen", n=bahn.boegen)
        return tr("ba.ergebnis_nut", nuten=nuten, lagen=lagen, boegen=boegen, zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return nu.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            schlichten=werte["schlichten"],
            gleichlauf=werte["gleichlauf"],
            flaechen=flaechen,
            eintauchwinkel=werte.get("eintauchwinkel"),
            eintauchstellen=werte.get("eintauchen_bei"),
        )

    def aendere(self, op, tc, werte, flaechen):
        nu.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            schlichten=werte["schlichten"],
            gleichlauf=werte["gleichlauf"],
            flaechen=flaechen,
            eintauchwinkel=werte.get("eintauchwinkel"),
            eintauchstellen=werte.get("eintauchen_bei"),
        )

    def ist(self, op):
        return nu.ist_nut(op)

    def werte_von(self, op):
        return {
            "zustellung": float(op.Zustellung),
            "zeilenabstand": float(op.Zeilenabstand),
            "aufmass": float(op.Aufmass),
            "schlichten": bool(op.Schlichten),
            "gleichlauf": bool(op.Gleichlauf),
            "eintauchen_bei": nu.eintauchstellen(op),
        }


class _Kontur(_Strategie):
    kennung = "kontur"
    aufloesung = ko.kb.SCHRITT
    gemerkt = GEMERKT_KONTURFRAESER
    einsatz_reihenfolge = (wz.SCHRUPPEN, wz.SCHLICHTEN, wz.PLANEN)

    def titel(self):
        return tr("ba.kontur")

    def text(self):
        return tr("ba.kontur.text")

    def fraeser_tooltip(self):
        return tr("ba.konturfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.kontureinsatz.tooltip")

    def felder(self):
        return (
            ("zustellung", tr("ba.zustellung"), tr("ba.kontur.zustellung.tooltip")),
            ("zeilenabstand", tr("ba.zeilenabstand"), tr("ba.kontur.zeilenabstand.tooltip")),
            ("aufmass", tr("ba.aufmass_schlichten"), tr("ba.aufmass_schlichten.tooltip")),
            ("breite", tr("ba.breite"), tr("ba.breite.tooltip")),
        )

    def haken(self):
        return (("schlichten", tr("ba.schlichten"), tr("ba.schlichten.tooltip"), True),)

    def passt(self, form, name):
        return bool(kb.waende(form, [name]))

    def flaechen_fuer(self, form, gewaehlte):
        """Die gewählten Wände – die Wand einer Nut mit allen Wänden der Nut, wie bei der Nut,
        gegen die die Kontur dort antritt (eine Wand meint die Nut)."""
        return nb.ganze_nuten(form, [n for n in gewaehlte if self.passt(form, n)])

    def unmoeglich_text(self):
        return tr("ba.kontur.keine_wand")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else ko.ZUSTELLUNG
        if feld == "zeilenabstand":
            if werkzeug is None:
                return 0.0
            return vplan.zeilenabstand_vorschlag(werkzeug, einsatz, ff.von_werkzeug(werkzeug))
        if feld == "aufmass":
            return ko.AUFMASS
        return 0.0  # Breite: so viel, wie das Rohteil sagt

    def platzhalter(self, feld, werkzeug, einsatz):
        if feld == "breite":
            return tr("ba.breite.leer")
        return super().platzhalter(feld, werkzeug, einsatz)

    def vorschau(self, job, werkzeug, werte, flaechen):
        return ko.vorschau(
            job,
            job.Model.Group,
            ff.von_werkzeug(werkzeug),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["schlichten"],
            flaechen,
            werte["breite"],
            schneidenlaenge=float(werkzeug.schneidenlaenge or 0.0),
            stand=werte.get("materialstand"),
        )

    def ergebnis_text(self, bahn, zeit):
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        bahnen = tr("ba.zahl.bahn") if bahn.bahnen == 1 else tr("ba.zahl.bahnen", n=bahn.bahnen)
        if bahn.konturen > 1:
            konturen = tr("ba.zahl.konturen", n=bahn.konturen)
            return tr(
                "ba.ergebnis_konturen", konturen=konturen, lagen=lagen, bahnen=bahnen, zeit=zeit
            )
        return tr("ba.ergebnis_kontur", lagen=lagen, bahnen=bahnen, zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return ko.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["schlichten"],
            werte["breite"],
            flaechen=flaechen,
        )

    def aendere(self, op, tc, werte, flaechen):
        ko.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["schlichten"],
            werte["breite"],
            flaechen=flaechen,
        )

    def ist(self, op):
        return ko.ist_kontur(op) and not ko.ist_rest(op)

    def werte_von(self, op):
        return {
            "zustellung": float(op.Zustellung),
            "zeilenabstand": float(op.Zeilenabstand),
            "aufmass": float(op.Aufmass),
            "breite": float(op.Breite),
            "schlichten": bool(op.Schlichten),
        }


class _Bohren(_Strategie):
    """FreeCADs Bohren mit einem Bohrer aus der Werkzeugverwaltung (bohren)."""

    kennung = "bohren"
    gemerkt = GEMERKT_BOHRER
    einsatz_reihenfolge = (wz.BOHREN,)

    def titel(self):
        return tr("ba.bohren")

    def text(self):
        return tr("ba.bohren.text")

    def fraeser_tooltip(self):
        return tr("ba.bohrer.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.bohren_einsatz.tooltip")

    def felder(self):
        return (("hub", tr("ba.bohren.hub"), tr("ba.bohren.hub.tooltip")),)

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art == wz.BOHRER

    def passt(self, form, name):
        return any(b.durch or b.spitze > 0 for b in bb.bohrungen(form, [name]))

    def unmoeglich_text(self):
        return tr("ba.bohren.nicht")

    def vorschlag(self, feld, werkzeug, einsatz):
        return 0.0  # Hub: automatisch

    def platzhalter(self, feld, werkzeug, einsatz):
        return tr("ba.bohren.hub.leer")

    def vorschau(self, job, werkzeug, werte, flaechen):
        return bh.vorschau(
            job,
            werkzeug,
            flaechen,
            werte.get("vorschub", 0.0),
            werte["hub"],
            reiben=werte.get("reiben", False),
        )

    def ergebnis_text(self, bahn, zeit):
        bohrungen = (
            tr("ba.zahl.bohrung")
            if bahn.bohrungen == 1
            else tr("ba.zahl.bohrungen", n=bahn.bohrungen)
        )
        hube = tr("ba.zahl.hub") if bahn.hube == 1 else tr("ba.zahl.hube", n=bahn.hube)
        return tr("ba.ergebnis_bohren", bohrungen=bohrungen, hube=hube, zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return bh.lege_an(job, tc, flaechen, werte["hub"])

    def ist(self, op):
        return False  # FreeCADs eigene Operation – sie ändert FreeCADs Fenster


class _Bohrung(_Strategie):
    kennung = "bohrung"
    gemerkt = GEMERKT_BOHRFRAESER
    einsatz_reihenfolge = (wz.SCHRUPPEN, wz.SCHLICHTEN, wz.PLANEN)

    def titel(self):
        return tr("ba.bohrung")

    def text(self):
        return tr("ba.bohrung.text")

    def fraeser_tooltip(self):
        return tr("ba.bohrfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.bohreinsatz.tooltip")

    def felder(self):
        return (
            ("zustellung", tr("ba.zustellung"), tr("ba.bohrung.zustellung.tooltip")),
            ("zeilenabstand", tr("ba.zeilenabstand"), tr("ba.bohrung.zeilenabstand.tooltip")),
            ("aufmass", tr("ba.aufmass_schlichten"), tr("ba.aufmass_schlichten.tooltip")),
        )

    def haken(self):
        return (
            ("schlichten", tr("ba.wand_schlichten"), tr("ba.wand_schlichten.tooltip"), True),
            ("gleichlauf", tr("ba.gleichlauf"), tr("ba.gleichlauf.tooltip"), True),
        )

    def passt(self, form, name):
        return bb.ist_bohrung(form, name)

    def unmoeglich_text(self):
        return tr("ba.bohrung.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else bo.ZUSTELLUNG
        if feld == "zeilenabstand":
            if werkzeug is None or werkzeug.durchmesser <= 0:
                return 0.0
            r = werkzeug.durchmesser / 2
            ae = einsatz.ae if einsatz is not None and einsatz.ae > 0 else r / 4
            return min(ae, r)
        return bo.AUFMASS

    def vorschau(self, job, werkzeug, werte, flaechen):
        form = ff.von_werkzeug(werkzeug)
        if form is None or vp.ebener_radius(form) <= 0:
            raise ValueError(tr("bo.fehler.form"))
        return bo.vorschau(
            job,
            job.Model.Group,
            float(form.radius),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            flaechen,
            schlichten=werte["schlichten"],
            gleichlauf=werte["gleichlauf"],
            schneidenlaenge=float(werkzeug.schneidenlaenge or 0.0),
            eintauchwinkel=_eintauchwinkel(werkzeug),
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
        )

    def ergebnis_text(self, bahn, zeit):
        bohrungen = (
            tr("ba.zahl.bohrung")
            if bahn.bohrungen == 1
            else tr("ba.zahl.bohrungen", n=bahn.bohrungen)
        )
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        return tr(
            "ba.ergebnis_bohrung",
            bohrungen=bohrungen,
            lagen=lagen,
            umlaeufe=f"{bahn.umlaeufe:.0f}",
            zeit=zeit,
        )

    def lege_an(self, job, tc, werte, flaechen):
        return bo.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            schlichten=werte["schlichten"],
            gleichlauf=werte["gleichlauf"],
            flaechen=flaechen,
            eintauchwinkel=werte.get("eintauchwinkel"),
        )

    def aendere(self, op, tc, werte, flaechen):
        bo.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            schlichten=werte["schlichten"],
            gleichlauf=werte["gleichlauf"],
            flaechen=flaechen,
            eintauchwinkel=werte.get("eintauchwinkel"),
        )

    def ist(self, op):
        return bo.ist_bohrungsfraesen(op)

    def werte_von(self, op):
        return {
            "zustellung": float(op.Zustellung),
            "zeilenabstand": float(op.Zeilenabstand),
            "aufmass": float(op.Aufmass),
            "schlichten": bool(op.Schlichten),
            "gleichlauf": bool(op.Gleichlauf),
        }


class _Gewinde(_Strategie):
    """FreeCADs Gewinde mit einem Gewindebohrer aus der Werkzeugverwaltung (gewinde) – nach
    dem Kernloch, gegen keine Strategie im Wettbewerb; den Haken setzt man selbst."""

    kennung = "gewinde"
    gemerkt = GEMERKT_GEWINDEBOHRER
    einsatz_reihenfolge = (wz.GEWINDEBOHREN,)

    def titel(self):
        return tr("ba.gewinde")

    def text(self):
        return tr("ba.gewinde.text")

    def fraeser_tooltip(self):
        return tr("ba.gewindebohrer.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.gewinde_einsatz.tooltip")

    def werkzeug_passt(self, werkzeug):
        return wz.gewindebohrer(werkzeug.art) and werkzeug.steigung > 0

    def passt(self, form, name):
        return bb.ist_bohrung(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob eine Bohrung ein Gewinde bekommt, sagt das Modell nicht

    def unmoeglich_text(self):
        return tr("ba.gewinde.nicht")

    def vorschau(self, job, werkzeug, werte, flaechen):
        steigung = float(werkzeug.steigung or 0.0)
        drehzahl = werte.get("vorschub", 0.0) / steigung if steigung > 0 else 0.0
        return gw.vorschau(job, werkzeug, flaechen, drehzahl)

    def ergebnis_text(self, bahn, zeit):
        gewinde = tr("ba.zahl.gewinde", n=bahn.gewinde, name=bahn.name)
        return tr("ba.ergebnis_gewinde", gewinde=gewinde, zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return gw.lege_an(job, tc, flaechen)

    def ist(self, op):
        return False  # FreeCADs eigene Operation – sie ändert FreeCADs Fenster


class _Gewindefraesen(_Strategie):
    """„Gewinde fräsen“ mit einem Gewindefräser aus der Werkzeugverwaltung (gewindefraesen) –
    nach dem Kernloch, statt „Gewinde bohren“; den Haken setzt man selbst."""

    kennung = "gewindefraesen"
    gemerkt = GEMERKT_GEWINDEFRAESER
    einsatz_reihenfolge = (wz.GEWINDEFRAESEN,)

    def titel(self):
        return tr("ba.gewindefraesen")

    def text(self):
        return tr("ba.gewindefraesen.text")

    def fraeser_tooltip(self):
        return tr("ba.gewindefraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.gewindefraesen_einsatz.tooltip")

    def haken(self):
        return (("gleichlauf", tr("ba.gleichlauf"), tr("ba.gleichlauf.tooltip"), True),)

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art == wz.GEWINDEFRAESER and (werkzeug.steigung or 0.0) > 0

    def passt(self, form, name):
        return bb.ist_bohrung(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob eine Bohrung ein Gewinde bekommt, sagt das Modell nicht

    def unmoeglich_text(self):
        return tr("ba.gewindefraesen.nicht")

    def vorschau(self, job, werkzeug, werte, flaechen):
        return gf.vorschau(
            job,
            werkzeug,
            flaechen,
            gleichlauf=werte["gleichlauf"],
            vorschub=werte.get("vorschub", 0.0),
        )

    def ergebnis_text(self, bahn, zeit):
        gewinde = bahn.gewinde_text()
        if abs(bahn.umlaeufe - 1.0) < 0.05:
            return tr("ba.ergebnis_gewindefraesen.einer", gewinde=gewinde, zeit=zeit)
        umlaeufe = f"{bahn.umlaeufe:.1f}".rstrip("0").rstrip(".")
        return tr(
            "ba.ergebnis_gewindefraesen",
            gewinde=gewinde,
            umlaeufe=dezimal(umlaeufe),
            zeit=zeit,
        )

    def lege_an(self, job, tc, werte, flaechen):
        werkzeug = werte["werkzeug"]
        return gf.lege_an(
            job,
            tc,
            float(werkzeug.steigung),
            gf.zaehne_von(werkzeug),
            gleichlauf=werte["gleichlauf"],
            flaechen=flaechen,
        )

    def aendere(self, op, tc, werte, flaechen):
        werkzeug = werte["werkzeug"]
        gf.aendere(
            op,
            tc,
            float(werkzeug.steigung),
            gf.zaehne_von(werkzeug),
            gleichlauf=werte["gleichlauf"],
            flaechen=flaechen,
        )

    def ist(self, op):
        return gf.ist_gewindefraesen(op)

    def werte_von(self, op):
        return {"gleichlauf": bool(op.Gleichlauf)}


class _Entgraten(_Strategie):
    """Ein Fasenfräser bricht die Oberkanten der gewählten Wände (entgraten) – zuletzt, gegen
    keine Strategie im Wettbewerb; den Haken setzt man selbst."""

    kennung = "entgraten"
    aufloesung = eg.eb.SCHRITT
    gemerkt = GEMERKT_FASENFRAESER
    einsatz_reihenfolge = (wz.FASEN, wz.VERRUNDEN)

    def titel(self):
        return tr("ba.entgraten")

    def text(self):
        return tr("ba.entgraten.text")

    def fraeser_tooltip(self):
        return tr("ba.fasenfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.fasen_einsatz.tooltip")

    def felder(self):
        return (
            ("breite", tr("ba.entgraten.breite"), tr("ba.entgraten.breite.tooltip")),
            ("tiefer", tr("ba.entgraten.tiefer"), tr("ba.entgraten.tiefer.tooltip")),
        )

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art in (wz.FASENFRAESER, wz.RADIENFRAESER)

    def passt(self, form, name):
        return eb.hat_oberkanten(form, name) or eb.hat_fasen(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        # Eine scharfe Kante: ob sie eine Fase bekommt, sagt die Zeichnung. Eine gezeichnete
        # Fase sagt das Modell – außer einer Senkung über einer Bohrung (die senkt „Senken“).
        return any(
            not sk.ist_senkung(form, f"Face{f.nummer + 1}")
            for f in eb._gewaehlte_fasen(form, gewaehlte)
        )

    def unmoeglich_text(self):
        return tr("ba.entgraten.nicht")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "breite":
            return eb.BREITE
        if feld == "tiefer":
            return eb.TIEFER
        return 0.0

    def vorschau(self, job, werkzeug, werte, flaechen):
        return eg.vorschau(job, werkzeug, werte["breite"], werte["tiefer"], flaechen)

    def ergebnis_text(self, bahn, zeit):
        def zuege(n):
            return tr("ba.zahl.kantenzug") if n == 1 else tr("ba.zahl.kantenzuege", n=n)

        if bahn.ausgelassen:
            text = tr(
                "ba.ergebnis_entgraten_ausgelassen",
                zuege=zuege(bahn.ketten),
                zeit=zeit,
                ausgelassen=zuege(bahn.ausgelassen),
            )
        else:
            text = tr("ba.ergebnis_entgraten", zuege=zuege(bahn.ketten), zeit=zeit)
        modell = getattr(bahn, "modell", ())
        einheit = einheiten.einheit(einheiten.LAENGE)
        fasen_ = [groesse_zeigen(b, einheiten.LAENGE, 2) or "0" for a, b in modell if a == "fase"]
        rund = [groesse_zeigen(r, einheiten.LAENGE, 2) or "0" for a, r in modell if a != "fase"]
        if fasen_:
            text += tr("ba.entgraten.aus_modell", breite=f"{', '.join(fasen_)} {einheit}")
        if rund:
            text += tr("ba.entgraten.rundung_modell", radius=", ".join(rund))
        return text

    def lege_an(self, job, tc, werte, flaechen):
        return eg.lege_an(job, tc, werte["breite"], werte["tiefer"], flaechen=flaechen)

    def aendere(self, op, tc, werte, flaechen):
        eg.aendere(op, tc, werte["breite"], werte["tiefer"], flaechen=flaechen)

    def ist(self, op):
        return eg.ist_entgraten(op)

    def werte_von(self, op):
        return {"breite": float(op.Breite), "tiefer": float(op.Tiefer)}


class _Entgraten3D(_Strategie):
    """Fasen an Kanten im Raum (W-015 S5; Manuel, 2026-10-04: „nicht das Werkstück beschädigen“,
    „nicht nur auf den 45-Grad-Fräser“, „auch auf einer Dreiachs-Maschine“): an einer 5-Achs-Maschine
    angestellt (Fasenfräser oder ebene Stirn), sonst der Fasenfräser senkrecht – den Haken setzt
    man selbst."""

    kennung = "entgraten3d"
    gemerkt = GEMERKT_ENTGRATEN3D
    nimmt_kanten = True
    einsatz_reihenfolge = (wz.FASEN, wz.SCHLICHTEN)
    bevorzugt = wz.FASENFRAESER
    aufloesung = e3op.e3.SCHRITT  # der Schritt auf der Kante

    def aufloesung_erklaerung(self, vorschlag):
        return tr("ba.aufloesung.kante.tooltip", vorschlag=vorschlag)

    def titel(self):
        return tr("ba.e3")

    def text(self):
        return tr("ba.e3.text")

    def fraeser_tooltip(self):
        return tr("ba.e3.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.fasen_einsatz.tooltip")

    def felder(self):
        return (("breite", tr("ba.e3.breite"), tr("ba.e3.breite.tooltip")),)

    def haken(self):
        return (("fuenf", tr("ba.e3.fuenf"), tr("ba.e3.fuenf.tooltip"), True),)

    def haken_verborgen(self, feld, block):
        return feld == "fuenf" and not block.panel._fuenfachs()

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art == wz.FASENFRAESER or werkzeug.art in e3op.FLACH

    def passt(self, form, name):
        return e3op.passt(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        # Welche Kante eine Fase bekommt, sagt die Zeichnung – hat man Kanten angeklickt, dann
        # dafür (Manuel, 2026-10-05: „Kanten anklicken muss sein“).
        return any(str(n).startswith("Edge") and self.passt(form, n) for n in gewaehlte)

    def unmoeglich_text(self):
        return tr("ba.e3.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        return e3op.BREITE if feld == "breite" else 0.0

    def _fuenf(self, werte):
        return bool(werte.get("fuenf", False))

    def vorschau(self, job, werkzeug, werte, flaechen):
        return e3op.vorschau(
            job,
            werkzeug,
            werte["breite"],
            flaechen,
            fuenf=self._fuenf(werte),
            vorschub=werte.get("vorschub", 0.0),
        )

    def zeit(self, bahn, vorschub, eintauchen):
        return bahn.laenge / vorschub if vorschub > 0 else bahn.zeit

    def ergebnis_text(self, bahn, zeit):
        kanten_ = tr("ba.e3.kante") if bahn.kanten == 1 else tr("ba.e3.kanten", n=bahn.kanten)
        text = tr("ba.ergebnis_e3", kanten=kanten_, zeit=zeit)
        if bahn.schenkel[1] - bahn.schenkel[0] > 0.01:
            von = groesse_zeigen(bahn.schenkel[0], einheiten.LAENGE, 2) or "0"
            bis = groesse_zeigen(bahn.schenkel[1], einheiten.LAENGE, 2) or "0"
            text += tr("ba.e3.schenkel", von=von, bis=bis)
        if bahn.ausgelassen >= 0.5:
            text += " " + e3op.ausgelassen_text(bahn)
        return text

    def lege_an(self, job, tc, werte, flaechen):
        return e3op.lege_an(job, tc, werte["breite"], self._fuenf(werte), flaechen=flaechen)

    def aendere(self, op, tc, werte, flaechen):
        e3op.aendere(op, tc, werte["breite"], self._fuenf(werte), flaechen=flaechen)

    def ist(self, op):
        return e3op.ist_entgraten3d(op)

    def werte_von(self, op):
        return {"breite": float(op.Fasenbreite), "fuenf": bool(op.FuenfAchsen)}


def _kegel_ergebnis(bahn, zeit):
    stellen = tr("ba.zahl.stelle") if bahn.stellen == 1 else tr("ba.zahl.stellen", n=bahn.stellen)
    tiefe = groesse_zeigen(bahn.tiefe, einheiten.LAENGE, 2) or "0"
    return tr(
        "ba.ergebnis_kegel",
        stellen=stellen,
        tiefe=f"{tiefe} {einheiten.einheit(einheiten.LAENGE)}",
        zeit=zeit,
    )


class _Zentrieren(_Strategie):
    """FreeCADs Bohren mit einem NC-Anbohrer über den Bohrungen (senken) – vor dem Bohren, gegen
    keine Strategie im Wettbewerb; den Haken setzt man selbst."""

    kennung = "zentrieren"
    gemerkt = GEMERKT_ANBOHRER
    einsatz_reihenfolge = (wz.ZENTRIEREN,)

    def titel(self):
        return tr("ba.zentrieren")

    def text(self):
        return tr("ba.zentrieren.text")

    def fraeser_tooltip(self):
        return tr("ba.anbohrer.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.zentrieren_einsatz.tooltip")

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art == wz.NC_ANBOHRER

    def passt(self, form, name):
        return bb.ist_bohrung(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob angebohrt wird, hängt am Bohrer, nicht am Modell

    def unmoeglich_text(self):
        return tr("ba.zentrieren.nicht")

    def vorschau(self, job, werkzeug, werte, flaechen):
        return sk.vorschau_zentrieren(job, werkzeug, flaechen, werte.get("vorschub", 0.0))

    def ergebnis_text(self, bahn, zeit):
        return _kegel_ergebnis(bahn, zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return sk.zentrieren_anlegen(job, tc, flaechen)

    def ist(self, op):
        return False  # FreeCADs eigene Operation – sie ändert FreeCADs Fenster


class _Rest(_Strategie):
    """Restmaterial: eine Kontur mit einem kleineren Fräser nur dort, wo der große davor nicht
    hinkam (kontur, RadiusDavor) – nach der Kontur, den Haken setzt man selbst."""

    kennung = "rest"
    gemerkt = GEMERKT_RESTFRAESER
    einsatz_reihenfolge = (wz.SCHLICHTEN, wz.SCHRUPPEN)

    def titel(self):
        return tr("ba.rest")

    def text(self):
        return tr("ba.rest.text")

    def fraeser_tooltip(self):
        return tr("ba.restfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.resteinsatz.tooltip")

    def felder(self):
        return (
            ("davor", tr("ba.rest.davor"), tr("ba.rest.davor.tooltip")),
            ("zustellung", tr("ba.zustellung"), tr("ba.rest.zustellung.tooltip")),
        )

    def passt(self, form, name):
        return bool(kb.waende(form, [name]))

    def vorgeschlagen(self, form, gewaehlte):
        return False  # nach den Rundungen und den Fräsern: BearbeitungPanel._rest_vorschlagen

    def unmoeglich_text(self):
        return tr("ba.rest.nicht")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            if einsatz is not None and einsatz.ap > 0:
                return einsatz.ap
            return float(werkzeug.durchmesser) if werkzeug is not None else ko.ZUSTELLUNG
        return 0.0  # davor: vom Fenster (_zusatz)

    def platzhalter(self, feld, werkzeug, einsatz):
        if feld == "davor":
            return tr("ba.rest.davor.leer")
        return super().platzhalter(feld, werkzeug, einsatz)

    def vorschau(self, job, werkzeug, werte, flaechen):
        davor = float(werte.get("davor", 0.0))
        if davor <= 0:
            raise ValueError(tr("ba.rest.davor.fehlt"))
        form = ff.von_werkzeug(werkzeug)
        return ko.vorschau(
            job,
            job.Model.Group,
            form,
            werte["zustellung"],
            float(form.radius),
            0.0,
            False,
            flaechen,
            REST_BREITE,
            schneidenlaenge=float(werkzeug.schneidenlaenge or 0.0),
            radius_davor=davor / 2,
        )

    def ergebnis_text(self, bahn, zeit):
        stellen_n = max(1, round(bahn.bahnen / max(bahn.lagen, 1)))
        stellen = tr("ba.zahl.stelle") if stellen_n == 1 else tr("ba.zahl.stellen", n=stellen_n)
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        return tr("ba.ergebnis_rest", stellen=stellen, lagen=lagen, zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        r = float(tc.Tool.Diameter) / 2
        return ko.lege_an(
            job,
            tc,
            werte["zustellung"],
            r,
            0.0,
            False,
            REST_BREITE,
            flaechen=flaechen,
            radius_davor=float(werte["davor"]) / 2,
        )

    def aendere(self, op, tc, werte, flaechen):
        r = float(tc.Tool.Diameter) / 2
        ko.aendere(
            op,
            tc,
            werte["zustellung"],
            r,
            0.0,
            False,
            REST_BREITE,
            flaechen=flaechen,
            radius_davor=float(werte["davor"]) / 2,
        )

    def ist(self, op):
        return ko.ist_rest(op)

    def werte_von(self, op):
        return {"davor": 2 * float(op.RadiusDavor), "zustellung": float(op.Zustellung)}


class _Schruppen3D(_Strategie):
    """Das Rohteil über Freiformflächen in Lagen wegräumen, Zwischenlagen für die Treppe
    (schruppen3d_bahn) – mit dem Fräser fürs Räumen; gegen keine Strategie im Wettbewerb."""

    kennung = "schruppen3d"
    aufloesung = r3op.sr.SCHRITT
    gemerkt = GEMERKT_RAEUMFRAESER
    einsatz_reihenfolge = (wz.SCHRUPPEN, wz.PLANEN, wz.SCHLICHTEN)

    def titel(self):
        return tr("ba.r3")

    def text(self):
        return tr("ba.r3.text")

    def fraeser_tooltip(self):
        return tr("ba.r3.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.r3.einsatz.tooltip")

    def felder(self):
        return (
            ("zustellung", tr("ba.zustellung"), tr("ba.zustellung.tooltip")),
            ("zeilenabstand", tr("ba.zeilenabstand"), tr("ba.raeumen.zeilenabstand.tooltip")),
            ("aufmass", tr("ba.aufmass"), tr("ba.r3.aufmass.tooltip")),
            ("zwischen", tr("ba.zwischenlagen"), tr("ba.zwischenlagen.tooltip")),
        )

    def haken(self):
        return (("gleichlauf", tr("ba.gleichlauf"), tr("ba.gleichlauf.tooltip"), True),)

    def passt(self, form, name):
        return s3b.ist_freiform(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        # Sobald eine Freiformfläche gewählt ist – auch neben Oberseite und Bohrungen (eine
        # Formplatte, P-2026-10-02-14); gefräst werden nur die Freiformflächen (flaechen_fuer).
        return any(self.passt(form, n) for n in gewaehlte)

    def unmoeglich_text(self):
        return tr("ba.r3.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zwischen":
            return r3b.ZWISCHEN
        if feld == "aufmass":
            return r3op.AUFMASS
        return _Raeumen().vorschlag(feld, werkzeug, einsatz)

    def vorschau(self, job, werkzeug, werte, flaechen):
        return r3op.vorschau(
            job,
            job.Model.Group,
            ff.von_werkzeug(werkzeug),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            flaechen,
            zwischen=werte["zwischen"],
            gleichlauf=werte["gleichlauf"],
            schneidenlaenge=float(werkzeug.schneidenlaenge or 0.0),
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
            stand=werte.get("materialstand"),
        )

    def ergebnis_text(self, bahn, zeit):
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        ringe = tr("ba.zahl.ring") if bahn.ringe == 1 else tr("ba.zahl.ringe", n=bahn.ringe)
        if not bahn.zwischenlagen:
            return tr("ba.ergebnis_raeumen", lagen=lagen, ringe=ringe, zeit=zeit)
        zwischen = (
            tr("ba.zahl.zwischenlage")
            if bahn.zwischenlagen == 1
            else tr("ba.zahl.zwischenlagen", n=bahn.zwischenlagen)
        )
        if not bahn.lagen:  # eine Höhlung: die volle Lage findet nichts, nur die Zwischenlagen
            return tr("ba.ergebnis_raeumen", lagen=zwischen, ringe=ringe, zeit=zeit)
        return tr("ba.ergebnis_r3", lagen=lagen, zwischen=zwischen, ringe=ringe, zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return r3op.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["zwischen"],
            werte["gleichlauf"],
            flaechen=flaechen,
        )

    def aendere(self, op, tc, werte, flaechen):
        r3op.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["zwischen"],
            werte["gleichlauf"],
            flaechen=flaechen,
        )

    def ist(self, op):
        return r3op.ist_schruppen3d(op) and not r3op.ist_restschruppen(op)

    def werte_von(self, op):
        return {
            "zustellung": float(op.Zustellung),
            "zeilenabstand": float(op.Zeilenabstand),
            "aufmass": float(op.Aufmass),
            "zwischen": float(op.Zwischenlagen),
            "gleichlauf": bool(op.Gleichlauf),
        }


class _Restschruppen(_Schruppen3D):
    """Restschruppen: das 3D-Schruppen mit einem kleineren Fräser nur dort, wo der größere
    davor Material stehen ließ (schruppen3d mit DurchmesserDavor) – nach dem 3D-Schruppen, den
    Haken setzt man selbst."""

    kennung = "restschruppen"
    gemerkt = GEMERKT_RESTSCHRUPPFRAESER

    def titel(self):
        return tr("ba.rr")

    def text(self):
        return tr("ba.rr.text")

    def fraeser_tooltip(self):
        return tr("ba.rr.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.rr.einsatz.tooltip")

    def felder(self):
        return (("davor", tr("ba.rr.davor"), tr("ba.rr.davor.tooltip")),) + super().felder()

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob der kleine Fräser nachkommt, entscheidet man selbst

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "davor":
            return 0.0  # vom Fenster (_zusatz)
        return super().vorschlag(feld, werkzeug, einsatz)

    def platzhalter(self, feld, werkzeug, einsatz):
        if feld == "davor":
            return tr("ba.rr.davor.leer")
        return super().platzhalter(feld, werkzeug, einsatz)

    @staticmethod
    def davor(werte):
        """(Ø, Eckenradius) des Fräsers davor aus den Werten – von Hand eingetragen ein
        Schaftfräser. ValueError mit einem Satz, wenn keiner da ist."""
        durchmesser = float(werte.get("davor", 0.0) or 0.0)
        if durchmesser <= 0:
            raise ValueError(tr("ba.rr.davor.fehlt"))
        return durchmesser, float(werte.get("davor_eck") or 0.0)

    def vorschau(self, job, werkzeug, werte, flaechen):
        durchmesser, eckenradius = self.davor(werte)
        return r3op.vorschau(
            job,
            job.Model.Group,
            ff.von_werkzeug(werkzeug),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            flaechen,
            zwischen=werte["zwischen"],
            gleichlauf=werte["gleichlauf"],
            schneidenlaenge=float(werkzeug.schneidenlaenge or 0.0),
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
            davor=ff.torus(durchmesser / 2, min(eckenradius, durchmesser / 2)),
        )

    def lege_an(self, job, tc, werte, flaechen):
        return r3op.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["zwischen"],
            werte["gleichlauf"],
            flaechen=flaechen,
            davor=self.davor(werte),
        )

    def aendere(self, op, tc, werte, flaechen):
        r3op.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["zwischen"],
            werte["gleichlauf"],
            flaechen=flaechen,
            davor=self.davor(werte),
        )

    def ist(self, op):
        return r3op.ist_restschruppen(op)

    def werte_von(self, op):
        return dict(super().werte_von(op), davor=float(op.DurchmesserDavor))


def _kippachse(job):
    """„X“ oder „Y“: um welche Achse des Jobs ein angestellter Kugelfräser kippt – die der ersten
    schwenkenden Rundachse der Maschine des Jobs (A um X, B um Y), sonst „X“."""
    datei = rw.gemerkte_maschine(job) if job is not None else ""
    eintrag = msp.finde(msp.laden(), datei) if datei else None
    for buchstabe in getattr(eintrag, "rundachsen", ()) or ():
        if buchstabe in ("A", "B"):
            return "X" if buchstabe == "A" else "Y"
    return "X"


def _wegkippen_bedarf(job, werkzeug, bahn, form):
    """wegkippen.Bedarf für die Vorschau: wie weit der Kugelfräser an der Bahn mindestens
    herausstehen muss – senkrecht und weggekippt – und wie weit er heraussteht (Halter und Länge
    aus der Werkzeugverwaltung, wie „Auf der Maschine prüfen“). None, wenn es nicht geht."""
    from . import vierachs_schlichten as vs
    from . import wegkippen as wk

    try:
        bibliothek = wz.Bibliothek.laden()
    except (wz.BeschaedigteDatei, OSError):
        bibliothek = None
    einspannung = wk.einspannung_werkzeug(werkzeug, bibliothek)
    punkte = [(p.x, p.y, p.z) for p in bahn.punkte if not p.eilgang]
    if einspannung is None or not punkte:
        return None
    teil = vs._teil(job.Model.Group)
    return wk.bedarf(teil, punkte, float(form.radius), einspannung)


def _job_der(op):
    """Der Job der Operation – None, wenn sie in keinem steht."""
    return next((j for j in js.jobs(op.Document) if op in js.operationen(j)), None)


class _Schlichten3D(_Strategie):
    """Freiformflächen in parallelen Zeilen auf der Hüllfläche des ganzen Teils
    (schlichten3d_bahn) – am liebsten mit dem Kugelfräser; gegen keine Strategie im Wettbewerb."""

    kennung = "schlichten3d"
    aufloesung = s3op.sb.SCHRITT
    gemerkt = GEMERKT_FRAESER_3D
    einsatz_reihenfolge = (wz.SCHLICHTEN, wz.SCHRUPPEN)
    bevorzugt = wz.KUGELFRAESER
    ARTEN = (wz.KUGELFRAESER, wz.TORUSFRAESER, wz.SCHAFTFRAESER, wz.KONIKFRAESER)

    def titel(self):
        return tr("ba.s3")

    def text(self):
        return tr("ba.s3.text")

    def fraeser_tooltip(self):
        return tr("ba.s3.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.s3.einsatz.tooltip")

    def felder(self):
        return (
            ("grathoehe", tr("ba.grathoehe"), tr("ba.grathoehe.tooltip")),
            ("aufmass", tr("ba.aufmass"), tr("ba.s3.aufmass.tooltip")),
        )

    def haken(self):
        # 5 Achsen simultan S2 (angestellt.py; Manuel, 2026-10-04: „Ja, so bauen“) – ohne Vorgabe.
        return (
            ("anstellen", tr("ba.s3.anstellen"), tr("ba.s3.anstellen.tooltip"), False),
            ("wegkippen", tr("ba.s3.wegkippen"), tr("ba.s3.wegkippen.tooltip"), False),
        )

    def haken_verborgen(self, feld, block):
        # Anstellen und Wegkippen nur an einer 5-Achs-Maschine – sonst wären sie nur Rauschen.
        return feld in ("anstellen", "wegkippen") and not block.panel._fuenfachs()

    def haken_gesperrt(self, feld, block):
        if feld not in ("anstellen", "wegkippen"):
            return None
        try:
            eintrag = block.panel.maschine()
        except AttributeError:  # die Wahl der Maschine gibt es noch nicht
            eintrag = None
        if eintrag is None or not eintrag.vorhanden or eintrag.art != msp.FRAESE_5:
            return tr("ba.s3.anstellen.ohne_maschine")
        werkzeug = block.fraeser()
        if werkzeug is None or werkzeug.art != wz.KUGELFRAESER:
            return tr("ba.s3.anstellen.ohne_kugel")
        return None

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art in self.ARTEN and ff.von_werkzeug(werkzeug) is not None

    def passt(self, form, name):
        return s3b.ist_freiform(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        # Sobald eine Freiformfläche gewählt ist – auch neben Oberseite und Bohrungen (eine
        # Formplatte, P-2026-10-02-14); gefräst werden nur die Freiformflächen (flaechen_fuer).
        return any(self.passt(form, n) for n in gewaehlte)

    def unmoeglich_text(self):
        return tr("ba.s3.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        return s3b.GRATHOEHE if feld == "grathoehe" else 0.0

    def vorschau(self, job, werkzeug, werte, flaechen):
        form = ff.von_werkzeug(werkzeug)
        if form is None:
            raise ValueError(tr("s3.fehler.form"))
        bahn = s3op.vorschau(
            job,
            job.Model.Group,
            form,
            werte["grathoehe"],
            flaechen,
            aufmass=werte["aufmass"],
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
        )
        if werte.get("wegkippen") and form.nur_kugel:
            bahn.wegkippen = _wegkippen_bedarf(job, werkzeug, bahn, form)
        return bahn

    def ergebnis_text(self, bahn, zeit):
        text = self._ergebnis_text(bahn, zeit)
        bedarf = getattr(bahn, "wegkippen", None)
        if bedarf is None:
            return text
        werte = {
            "text": text,
            "senkrecht": groesse_zeigen(bedarf.senkrecht, einheiten.LAENGE, 1) or "0",
            "gekippt": groesse_zeigen(bedarf.gekippt, einheiten.LAENGE, 1) or "0",
            "auskragung": groesse_zeigen(bedarf.auskragung, einheiten.LAENGE, 1) or "0",
        }
        if bedarf.auskragung < bedarf.gekippt:
            return tr("ba.s3.wegkippen.zu_kurz", **werte)
        return tr("ba.s3.wegkippen.bedarf", **werte)

    def _ergebnis_text(self, bahn, zeit):
        zeilen = tr("ba.zahl.zeile") if bahn.zeilen == 1 else tr("ba.zahl.zeilen", n=bahn.zeilen)
        werte = {
            "zeilen": zeilen,
            "richtung": "X" if bahn.laengs_x else "Y",
            "abstand": groesse_zeigen(bahn.abstand, einheiten.LAENGE, 2) or "0",
            "zeit": zeit,
        }
        if getattr(bahn, "aequidistant", False):
            ringe = tr("ba.zahl.ring") if bahn.zeilen == 1 else tr("ba.zahl.ringe", n=bahn.zeilen)
            return tr("ba.ergebnis_s3_aequi", ringe=ringe, **werte)
        if getattr(bahn, "flaeche", False):
            kurven = (
                tr("ba.zahl.kurve") if bahn.zeilen == 1 else tr("ba.zahl.kurven", n=bahn.zeilen)
            )
            return tr("ba.ergebnis_s3_flaeche", kurven=kurven, **werte)
        if bahn.spirale:
            werte["umlaeufe"] = (
                tr("ba.zahl.umlauf")
                if bahn.umlaeufe == 1
                else tr("ba.zahl.umlaeufe", n=bahn.umlaeufe)
            )
            if bahn.hoehenlinien:
                return tr("ba.ergebnis_s3_spirale_steil", n=bahn.hoehenlinien, **werte)
            return tr("ba.ergebnis_s3_spirale", **werte)
        if bahn.hoehenlinien:
            return tr("ba.ergebnis_s3_steil", n=bahn.hoehenlinien, **werte)
        return tr("ba.ergebnis_s3", **werte)

    def lege_an(self, job, tc, werte, flaechen):
        op = s3op.lege_an(job, tc, werte["grathoehe"], werte["aufmass"], flaechen=flaechen)
        s3op.stelle_an(op, werte.get("anstellen", False), _kippachse(job))
        s3op.stelle_weg(op, werte.get("wegkippen", False))
        return op

    def aendere(self, op, tc, werte, flaechen):
        s3op.aendere(op, tc, werte["grathoehe"], werte["aufmass"], flaechen=flaechen)
        s3op.stelle_an(op, werte.get("anstellen", False), _kippachse(_job_der(op)))
        s3op.stelle_weg(op, werte.get("wegkippen", False))

    def ist(self, op):
        return s3op.ist_schlichten3d(op) and not s3op.ist_restschlichten(op)

    def werte_von(self, op):
        return {
            "grathoehe": float(op.Grathoehe),
            "aufmass": float(op.Aufmass),
            "anstellen": bool(getattr(op, "Anstellen", False)),
            "wegkippen": bool(getattr(op, "Wegkippen", False)),
        }


class _Flanke(_Strategie):
    """Die Flanke (5 Achsen simultan, flanke_bahn; Manuel, 2026-10-04: „Ja, so bauen“, „selbst
    anhaken, wenn schneller“): schräge Wände aus Geraden mit dem Mantel eines Schaftfräsers in
    einem Umlauf – an einer 5-Achs-Maschine, im Wettbewerb mit dem 3D-Schlichten."""

    kennung = "flanke"
    gemerkt = GEMERKT_FLANKENFRAESER
    einsatz_reihenfolge = (wz.SCHLICHTEN, wz.SCHRUPPEN)
    bevorzugt = wz.SCHAFTFRAESER
    aufloesung = flb.SCHRITT  # der Schritt an gekrümmten Kanten

    def aufloesung_erklaerung(self, vorschlag):
        return tr("ba.aufloesung.kante.tooltip", vorschlag=vorschlag)

    def titel(self):
        return tr("ba.fl")

    def text(self):
        return tr("ba.fl.text")

    def fraeser_tooltip(self):
        return tr("ba.fl.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.s3.einsatz.tooltip")

    def felder(self):
        return (("aufmass", tr("ba.aufmass"), tr("ba.fl.aufmass.tooltip")),)

    def passt(self, form, name):
        return flb.ist_wand(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        return any(self.passt(form, n) for n in gewaehlte)  # die Zeit entscheidet (_wettbewerb)

    def unmoeglich_text(self):
        return tr("ba.fl.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        return 0.0

    def vorschau(self, job, werkzeug, werte, flaechen):
        form = ff.von_werkzeug(werkzeug)
        if form is None or not form.eben:
            raise ValueError(tr("fl.fehler.fraeser"))
        radius = float(form.radius)
        schneide = float(getattr(werkzeug, "schneidenlaenge", 0.0) or 0.0) or 4.0 * radius
        return flop.bahn_fuer(
            job,
            job.Model.Group,
            radius,
            schneide,
            flaechen,
            aufmass=werte["aufmass"],
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
        )

    def zeit(self, bahn, vorschub, eintauchen):
        return bahn.zeit  # mit dem Drehen der Achse (flanke_bahn._laenge_und_zeit)

    def ergebnis_text(self, bahn, zeit):
        umlaeufe = (
            tr("ba.fl.umlauf") if bahn.umlaeufe == 1 else tr("ba.fl.umlaeufe", n=bahn.umlaeufe)
        )
        werte = {"umlaeufe": umlaeufe, "neigung": f"{bahn.neigung:.0f}", "zeit": zeit}
        if bahn.lagen > 1:
            return tr("ba.ergebnis_fl_lagen", lagen=bahn.lagen, **werte)
        return tr("ba.ergebnis_fl", **werte)

    def lege_an(self, job, tc, werte, flaechen):
        return flop.lege_an(job, tc, werte["aufmass"], flaechen=flaechen)

    def aendere(self, op, tc, werte, flaechen):
        flop.aendere(op, tc, werte["aufmass"], flaechen=flaechen)

    def ist(self, op):
        return flop.ist_flanke(op)

    def werte_von(self, op):
        return {"aufmass": float(op.Aufmass)}


class _Restschlichten(_Schlichten3D):
    """Restschlichten: das 3D-Schlichten mit einem kleineren Fräser nur dort, wo der größere
    davor nicht hinkam (schlichten3d mit DurchmesserDavor) – nach dem 3D-Schlichten, den Haken
    setzt man selbst."""

    kennung = "restschlichten"
    gemerkt = GEMERKT_RESTFRAESER_3D
    ARTEN = (wz.KUGELFRAESER, wz.TORUSFRAESER)

    def titel(self):
        return tr("ba.rs")

    def text(self):
        return tr("ba.rs.text")

    def fraeser_tooltip(self):
        return tr("ba.rs.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.rs.einsatz.tooltip")

    def felder(self):
        return (("davor", tr("ba.rs.davor"), tr("ba.rs.davor.tooltip")),) + super().felder()

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob der kleine Fräser nachkommt, entscheidet man selbst

    def unmoeglich_text(self):
        return tr("ba.rs.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "davor":
            return 0.0  # vom Fenster (_zusatz)
        return super().vorschlag(feld, werkzeug, einsatz)

    def platzhalter(self, feld, werkzeug, einsatz):
        if feld == "davor":
            return tr("ba.rs.davor.leer")
        return super().platzhalter(feld, werkzeug, einsatz)

    @staticmethod
    def davor(werte):
        """(Ø, Eckenradius) des Fräsers davor aus den Werten – von Hand eingetragen eine Kugel.
        ValueError mit einem Satz, wenn keiner da ist."""
        durchmesser = float(werte.get("davor", 0.0) or 0.0)
        if durchmesser <= 0:
            raise ValueError(tr("ba.rs.davor.fehlt"))
        eckenradius = werte.get("davor_eck")
        return durchmesser, float(durchmesser / 2 if eckenradius is None else eckenradius)

    def vorschau(self, job, werkzeug, werte, flaechen):
        form = ff.von_werkzeug(werkzeug)
        if form is None:
            raise ValueError(tr("s3.fehler.form"))
        durchmesser, eckenradius = self.davor(werte)
        return s3op.vorschau(
            job,
            job.Model.Group,
            form,
            werte["grathoehe"],
            flaechen,
            aufmass=werte["aufmass"],
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
            davor=ff.torus(durchmesser / 2, min(eckenradius, durchmesser / 2)),
        )

    def lege_an(self, job, tc, werte, flaechen):
        op = s3op.lege_an(
            job,
            tc,
            werte["grathoehe"],
            werte["aufmass"],
            flaechen=flaechen,
            davor=self.davor(werte),
        )
        s3op.stelle_an(op, werte.get("anstellen", False), _kippachse(job))
        s3op.stelle_weg(op, werte.get("wegkippen", False))
        return op

    def aendere(self, op, tc, werte, flaechen):
        s3op.aendere(
            op, tc, werte["grathoehe"], werte["aufmass"], flaechen=flaechen, davor=self.davor(werte)
        )
        s3op.stelle_an(op, werte.get("anstellen", False), _kippachse(_job_der(op)))
        s3op.stelle_weg(op, werte.get("wegkippen", False))

    def ist(self, op):
        return s3op.ist_restschlichten(op)

    def werte_von(self, op):
        return {
            "davor": float(op.DurchmesserDavor),
            "grathoehe": float(op.Grathoehe),
            "aufmass": float(op.Aufmass),
            "anstellen": bool(getattr(op, "Anstellen", False)),
            "wegkippen": bool(getattr(op, "Wegkippen", False)),
        }


class _Bleistift(_Strategie):
    """Die Kehlen der Freiformflächen nachfahren, wo der Kugelfräser zwei Flächen zugleich
    berührt (bleistift_bahn) – nach dem 3D-Schlichten, mit demselben Fräser; den Haken setzt man
    selbst."""

    kennung = "bleistift"
    aufloesung = bst.bb.RASTER
    gemerkt = GEMERKT_FRAESER_3D
    einsatz_reihenfolge = (wz.SCHLICHTEN, wz.SCHRUPPEN)
    bevorzugt = wz.KUGELFRAESER
    ARTEN = (wz.KUGELFRAESER, wz.TORUSFRAESER)

    def titel(self):
        return tr("ba.bs")

    def text(self):
        return tr("ba.bs.text")

    def fraeser_tooltip(self):
        return tr("ba.bs.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.bs.einsatz.tooltip")

    def felder(self):
        return (
            ("aufmass", tr("ba.aufmass"), tr("ba.bs.aufmass.tooltip")),
            ("breite", tr("ba.bs.breite"), tr("ba.bs.breite.tooltip")),
        )

    @staticmethod
    def _bahnen(werkzeug, werte):
        """Bahnen je Seite aus dem Feld „Breite je Seite“ (bleistift.bahnen_fuer)."""
        form = ff.von_werkzeug(werkzeug) if werkzeug is not None else None
        return bst.bahnen_fuer(werte.get("breite", 0.0), form)

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art in self.ARTEN and ff.von_werkzeug(werkzeug) is not None

    def passt(self, form, name):
        return s3b.ist_freiform(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob die Kehle nachgefahren wird, entscheidet man selbst

    def unmoeglich_text(self):
        return tr("ba.bs.keine")

    def vorschau(self, job, werkzeug, werte, flaechen):
        form = ff.von_werkzeug(werkzeug)
        if form is None:
            raise ValueError(tr("bs.fehler.form"))
        return bst.vorschau(
            job,
            job.Model.Group,
            form,
            flaechen,
            aufmass=werte["aufmass"],
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
            bahnen=self._bahnen(werkzeug, werte),
        )

    def ergebnis_text(self, bahn, zeit):
        kehlen = tr("ba.zahl.kehle") if bahn.linien == 1 else tr("ba.zahl.kehlen", n=bahn.linien)
        laenge = groesse_zeigen(bahn.laenge, einheiten.LAENGE, 0) or "0"
        einheit = einheiten.einheit(einheiten.LAENGE)
        return tr("ba.ergebnis_bs", kehlen=kehlen, laenge=f"{laenge} {einheit}", zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        bahnen = bst.bahnen_fuer(werte.get("breite", 0.0), bst.vs.form_des_controllers(tc))
        return bst.lege_an(job, tc, werte["aufmass"], flaechen=flaechen, bahnen=bahnen)

    def aendere(self, op, tc, werte, flaechen):
        bahnen = bst.bahnen_fuer(werte.get("breite", 0.0), bst.vs.form_des_controllers(tc))
        bst.aendere(op, tc, werte["aufmass"], flaechen=flaechen, bahnen=bahnen)

    def ist(self, op):
        return bst.ist_bleistift(op)

    def werte_von(self, op):
        return {"aufmass": float(op.Aufmass), "breite": bst.breite_von(op)}


class _Senken(_Strategie):
    """FreeCADs Bohren mit einem Kegelsenker in die Senkungen des Modells (senken) – nach dem
    Bohren; das Modell sagt, dass sie kommen, darum vorgeschlagen."""

    kennung = "senken"
    gemerkt = GEMERKT_SENKER
    einsatz_reihenfolge = (wz.SENKEN,)

    def titel(self):
        return tr("ba.senken")

    def text(self):
        return tr("ba.senken.text")

    def fraeser_tooltip(self):
        return tr("ba.senker.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.senken_einsatz.tooltip")

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art == wz.KEGELSENKER

    def passt(self, form, name):
        return sk.ist_senkung(form, name)

    def unmoeglich_text(self):
        return tr("ba.senken.nicht")

    def vorschau(self, job, werkzeug, werte, flaechen):
        return sk.vorschau_senken(job, werkzeug, flaechen, werte.get("vorschub", 0.0))

    def ergebnis_text(self, bahn, zeit):
        return _kegel_ergebnis(bahn, zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return sk.senken_anlegen(job, tc, flaechen)

    def ist(self, op):
        return False  # FreeCADs eigene Operation – sie ändert FreeCADs Fenster


class _Reiben(_Strategie):
    """FreeCADs Bohren mit einer Reibahle, G85 (reiben) – nach Bohren und Senken; der Bohrer
    bohrt dann kleiner vor, Bohrung fräsen und Kontur treten dort nicht an. Den Haken setzt
    man selbst: Ob eine Bohrung gerieben wird, steht nicht im Modell."""

    kennung = "reiben"
    gemerkt = GEMERKT_REIBAHLE
    einsatz_reihenfolge = (wz.REIBEN,)

    def titel(self):
        return tr("ba.reiben")

    def text(self):
        return tr("ba.reiben.text")

    def fraeser_tooltip(self):
        return tr("ba.reibahle.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.reiben_einsatz.tooltip")

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art == wz.REIBAHLE

    def passt(self, form, name):
        return any(b.durch or b.spitze > 0 for b in bb.bohrungen(form, [name]))

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob gerieben wird (H7), sagt das Modell nicht

    def unmoeglich_text(self):
        return tr("ba.reiben.nicht")

    def vorschau(self, job, werkzeug, werte, flaechen):
        return rbn.vorschau(job, werkzeug, flaechen, werte.get("vorschub", 0.0))

    def ergebnis_text(self, bahn, zeit):
        bohrungen = (
            tr("ba.zahl.bohrung")
            if bahn.bohrungen == 1
            else tr("ba.zahl.bohrungen", n=bahn.bohrungen)
        )
        return tr("ba.ergebnis_reiben", bohrungen=bohrungen, zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return rbn.lege_an(job, tc, flaechen)

    def ist(self, op):
        return False  # FreeCADs eigene Operation – sie ändert FreeCADs Fenster


STRATEGIEN = (
    _Planfraesen,
    _Raeumen,
    _RestRaeumen,
    _SchlichtenDanach,
    _Nut,
    _Zentrieren,
    _Bohren,
    _Bohrung,
    _Kontur,
    _Rest,
    _Schruppen3D,
    _Restschruppen,
    _Schlichten3D,
    _Flanke,
    _Restschlichten,
    _Bleistift,
    _Senken,
    _Reiben,
    _Gewinde,
    _Gewindefraesen,
    _Entgraten,
    _Entgraten3D,
)


def _zahlenfeld(felder, name, text, tooltip, reihen, geaendert):
    eingabe = QtGui.QLineEdit()
    eingabe.setValidator(Zahlenpruefer(eingabe))
    eingabe.textChanged.connect(lambda _text: geaendert())
    felder[name] = eingabe
    reihen.reihe(text, tooltip, mit_einheit(eingabe, einheiten.einheit(einheiten.LAENGE)))
    return eingabe


class _Block:
    """Der Block einer Strategie im Fenster: der Haken als Titel, die Erklärung, Fräser und
    Einsatz, die Felder, das Ergebnis – und der Zustand dazu (Vorschau, Operation)."""

    def __init__(self, panel, strategie):
        self.panel = panel
        self.s = strategie
        self._fraeser = []  # die Werkzeuge in der Auswahl „Fräser“
        self._einsaetze = []
        self.vorwahl = None  # beim Ändern: Kennung des Fräsers der Operation
        self.tc_vorher = None  # beim Ändern: ihr Controller
        self.vorschau = None  # die grobe Bahn oder None
        self.schon_weg = False  # „Hier ist nichts mehr zu tun“ (Materialstand, W-012)
        self.zeit = None  # Minuten der Vorschau (bahn.zeit) – für den Wettbewerb
        self.ergebnis_basis = ""  # die Ergebniszeile ohne den Vergleich
        self.operation = None  # die angelegte Operation
        self.von_hand = False  # der Haken ist von Hand gesetzt – kein Vorschlag mehr
        self.moeglich = True  # die Strategie geht mit der Wahl der Flächen
        # Schritt 2, der Überblick: der Haken mit dem Titel, das Ergebnis, rot was fehlt – oder,
        # passt die Strategie nicht zur Wahl, eine Zeile „Titel – was man anklicken muss“.
        self.widget = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(self.widget)
        aufbau.setContentsMargins(0, 0, 0, 0)
        self.haken = QtGui.QCheckBox(strategie.titel())
        self.haken.setToolTip(strategie.text())
        schrift = self.haken.font()
        schrift.setBold(True)
        self.haken.setFont(schrift)
        self.haken.toggled.connect(lambda _an: self.panel.haken_geklickt(self))
        aufbau.addWidget(self.haken)
        self.kurz = _grau()
        self.kurz.setTextFormat(QtCore.Qt.RichText)
        self.kurz.hide()
        aufbau.addWidget(self.kurz)
        self.ergebnis = _Satz(GRAU_TEXT)
        aufbau.addWidget(self.ergebnis)
        # Was nach den Operationen davor noch zu tun ist (W-012; Manuel: „Ist überhaupt noch
        # viel Material vorhanden, was ich wegmachen muss“).
        self.material = _Satz(GRAU_TEXT)
        aufbau.addWidget(self.material)
        self.hinweis = _Satz(ROT)
        aufbau.addWidget(self.hinweis)
        # Schritt 3, die Einstellungen – nur solange angehakt: der Titel, die Erklärung, Fräser,
        # Einsatz, Felder und Haken, darunter dasselbe Ergebnis.
        self.einstellungen = QtGui.QWidget()
        unten = QtGui.QVBoxLayout(self.einstellungen)
        unten.setContentsMargins(0, 0, 0, 0)
        self.titel = QtGui.QLabel(strategie.titel())
        schrift = self.titel.font()
        schrift.setBold(True)
        self.titel.setFont(schrift)
        unten.addWidget(self.titel)
        self.erklaerung = _grau(strategie.text())
        unten.addWidget(self.erklaerung)
        self.inhalt = QtGui.QWidget()
        innen = QtGui.QVBoxLayout(self.inhalt)
        innen.setContentsMargins(0, 0, 0, 0)
        self.reihen = _Reihen()
        self.wahl_fraeser = QtGui.QComboBox()
        self.wahl_fraeser.currentIndexChanged.connect(lambda _i: self._fraeser_gewaehlt())
        self.reihen.reihe(tr("va.fraeser"), strategie.fraeser_tooltip(), self.wahl_fraeser)
        self.wahl_einsatz = QtGui.QComboBox()
        self.wahl_einsatz.currentIndexChanged.connect(lambda _i: self._einsatz_gewaehlt())
        self.reihen.reihe(tr("va.einsatz"), strategie.einsatz_tooltip(), self.wahl_einsatz)
        self.schnittwerte = _grau()
        self.reihen.ganz(self.schnittwerte)
        # Steht der Fräser nicht im Magazin der Maschine (W-002 Stufe H2, E3 a): gelb, was das
        # heißt, und ein Knopf, der ihn dort einträgt.
        self.magazin_zeile = QtGui.QWidget()
        magazin = QtGui.QVBoxLayout(self.magazin_zeile)
        magazin.setContentsMargins(0, 0, 0, 0)
        self.magazin_satz = QtGui.QLabel()
        self.magazin_satz.setWordWrap(True)
        self.magazin_satz.setStyleSheet(f"color: {GELB};")
        magazin.addWidget(self.magazin_satz)
        self.knopf_magazin = knopf(
            tr("mg.uebernehmen"), tr("mg.uebernehmen.tooltip"), self.ins_magazin
        )
        magazin.addWidget(self.knopf_magazin, 0, QtCore.Qt.AlignLeft)
        self.magazin_zeile.hide()
        self.reihen.ganz(self.magazin_zeile)
        if strategie.kennung == "raeumen":
            self.wahl_bahn = QtGui.QComboBox()
            self.wahl_bahn.addItem(tr("ba.raeumen.bisherig"), "automatisch")
            self.wahl_bahn.addItem(tr("ba.raeumen.schnell_frei"), ra.ADAPTIV_FREI)
            self.reihen.reihe(tr("ba.raeumen.bahn"), tr("ba.raeumen.bahn.tooltip"), self.wahl_bahn)
            self.freivorschub = QtGui.QLineEdit()
            self.freivorschub.setValidator(Zahlenpruefer(self.freivorschub))
            self.freivorschub.setPlaceholderText(
                groesse_zeigen(ra.FREIVORSCHUB, einheiten.VORSCHUB)
            )
            self.freivorschub.textChanged.connect(lambda _text: self.panel.vorschau_starten())
            self.freivorschub_zeile = mit_einheit(
                self.freivorschub, einheiten.einheit(einheiten.VORSCHUB)
            )
            self.reihen.reihe(
                tr("ba.raeumen.freivorschub"),
                tr("ba.raeumen.freivorschub.tooltip"),
                self.freivorschub_zeile,
            )
            self.freivorschub_etikett = self.reihen._beschriftungen[-1]
            self.freivorschub_zeile.hide()
            self.freivorschub_etikett.hide()
            self.wahl_bahn.currentIndexChanged.connect(lambda _i: self._raeumwahl_geaendert())
        self.felder = {}
        for feld, text, tooltip in strategie.felder():
            _zahlenfeld(self.felder, feld, text, tooltip, self.reihen, self.panel.vorschau_starten)
        if strategie.aufloesung:  # T-009: die Auflösung je Strategie, leer = Vorschlag
            _zahlenfeld(
                self.felder,
                "aufloesung",
                tr("ba.aufloesung"),
                strategie.aufloesung_erklaerung(
                    groesse_zeigen(strategie.aufloesung, einheiten.LAENGE)
                ),
                self.reihen,
                self.panel.vorschau_starten,
            )
        self.haken_felder = {}
        self._haken_texte = {}  # Name → (Beschriftung, Tooltip) – gesperrt kommt der Grund dazu
        for feld, text, tooltip, vorgabe in strategie.haken():
            kasten = QtGui.QCheckBox(text)
            kasten.setToolTip(tooltip)
            kasten.setChecked(vorgabe)
            kasten.toggled.connect(lambda _an: self.panel.vorschau_starten())
            self.haken_felder[feld] = kasten
            self._haken_texte[feld] = (text, tooltip)
            self.reihen.ganz(kasten)
        innen.addWidget(self.reihen.widget)
        # Die Eintauchstelle je geschlossener Nut (W-012 E1; Manuel: „an einer von mir aus
        # wählbaren Position in der Nut … aber natürlich mit Vorschlag“, Frage 2: a).
        self.eintauchen = {}  # Schlüssel der Nut → Anteil von A nach B; ohne: der Vorschlag
        self.stelle_waehlt = None  # „Im Bild wählen …“ wartet auf einen Klick: Schlüssel
        self._stellen = []  # aus der letzten Vorschau: (Schlüssel, Anteil, vorgeschlagen, A, B)
        self._stellen_zeilen = {}  # Schlüssel → die Teile ihrer Zeile
        self.stellen_box = QtGui.QWidget()
        self.stellen_aufbau = QtGui.QVBoxLayout(self.stellen_box)
        self.stellen_aufbau.setContentsMargins(0, 0, 0, 0)
        self.stellen_box.setVisible(False)
        innen.addWidget(self.stellen_box)
        unten.addWidget(self.inhalt)
        unten.addWidget(self.ergebnis.spiegel)
        unten.addWidget(self.material.spiegel)
        unten.addWidget(self.hinweis.spiegel)

    # --- Zustand ---

    def aktiv(self):
        """Angehakt und möglich: Die Strategie wird gerechnet und angelegt (beim Ändern ist der
        Haken gesetzt und gesperrt)."""
        return self.moeglich and self.haken.isChecked()

    def zustand_zeigen(self):
        # Im Überblick (Schritt 2): passt die Strategie, der Haken und ihr Ergebnis – die Zeit
        # und um wie viel langsamer; passt sie nicht, der Titel und der Satz, was man dafür
        # anklicken muss. Ihre Felder stehen in Schritt 3, solange sie angehakt ist (Manuel,
        # 2026-10-02: „Du musst das irgendwie sinnvoll aufteilen … in Schritten“).
        self.haken.setVisible(self.moeglich)
        self.ergebnis.erlauben(self.moeglich)
        self.material.erlauben(self.moeglich)
        self.hinweis.erlauben(self.moeglich)
        self.kurz.setVisible(not self.moeglich)
        self.einstellungen.setVisible(self.aktiv())
        if not self.moeglich:
            titel = html.escape(self.s.titel())
            self.kurz.setText(f"<b>{titel}</b> – {html.escape(self.erklaerung.text())}")

    def fraeser(self):
        i = self.wahl_fraeser.currentIndex()
        return self._fraeser[i] if 0 <= i < len(self._fraeser) else None

    def einsatz(self):
        i = self.wahl_einsatz.currentIndex()
        return self._einsaetze[i] if 0 <= i < len(self._einsaetze) else None

    def vorschlag(self, feld):
        return self.s.vorschlag(feld, self.fraeser(), self.einsatz())

    def wert(self, feld):
        """Wert eines Felds (mm); leer oder ungültig gilt der Vorschlag."""
        text = self.felder[feld].text()
        try:
            return groesse_lesen(text, einheiten.LAENGE) if text.strip() else self.vorschlag(feld)
        except ValueError:
            return self.vorschlag(feld)

    def haken_pruefen(self):
        """Haken, die nur mit einer bestimmten Maschine oder einem bestimmten Fräser gehen
        (Strategie.haken_gesperrt): gesperrt, abgehakt, der Grund hinter der Beschriftung."""
        for feld, kasten in getattr(self, "haken_felder", {}).items():
            grund = self.s.haken_gesperrt(feld, self)
            text, tooltip = self._haken_texte[feld]
            verborgen = self.s.haken_verborgen(feld, self)
            kasten.setVisible(not verborgen)
            if verborgen:
                grund = grund or ""
            kasten.setEnabled(grund is None)
            # Selbst abgehakt, weil er nicht ging – geht er wieder (eine andere Maschine), kommt
            # der Haken zurück (Entgraten 3D: „angestellt“ ist an einer 5-Achs-Maschine an).
            selbst_ab = self.__dict__.setdefault("_selbst_abgehakt", set())
            if grund is not None and kasten.isChecked():
                kasten.setChecked(False)
                selbst_ab.add(feld)
            elif grund is None and feld in selbst_ab:
                selbst_ab.discard(feld)
                kasten.setChecked(True)
            kasten.setText(
                text if grund is None else tr("ba.haken.gesperrt", text=text, grund=grund)
            )
            kasten.setToolTip(tooltip)

    def werte(self):
        werte = {feld: self.wert(feld) for feld in self.felder}
        werte.update({feld: kasten.isChecked() for feld, kasten in self.haken_felder.items()})
        if self.s.kennung == "nut":
            werte["eintauchen_bei"] = dict(self.eintauchen)
        elif self.s.kennung == "raeumen":
            werte["variante"] = self.wahl_bahn.currentData()
            text = self.freivorschub.text().strip()
            try:
                werte["freivorschub"] = (
                    groesse_lesen(text, einheiten.VORSCHUB) if text else ra.FREIVORSCHUB
                )
            except ValueError:  # unfertige Eingabe: die Vorschau nennt den ungültigen Vorschub
                werte["freivorschub"] = 0.0
        return werte

    def _raeumwahl_geaendert(self):
        schnell = self.wahl_bahn.currentData() == ra.ADAPTIV_FREI
        self.freivorschub_zeile.setVisible(schnell)
        self.freivorschub_etikett.setVisible(schnell)
        self.panel.vorschau_starten()

    def raeumwahl_von(self, op):
        """Die gespeicherte Räumwahl zeigen; auch eine bisher vorgegebene Variante bleibt."""
        variante = str(op.Variante)
        bisher = "automatisch" if variante == ra.ADAPTIV_FREI else variante
        self.wahl_bahn.setItemData(0, bisher)
        if bisher != "automatisch":
            self.wahl_bahn.setItemText(0, tr("ba.raeumen.bisherig_variante", variante=bisher))
        self.wahl_bahn.setCurrentIndex(1 if variante == ra.ADAPTIV_FREI else 0)
        self.freivorschub.setText(groesse_zeigen(float(op.Freivorschub) * 60.0, einheiten.VORSCHUB))

    # --- Die Eintauchstelle der Nut (W-012 E1) ---

    def stellen_zeigen(self, stellen):
        """Je geschlossener Nut eine Zeile „Eintauchen bei“: die Liste – der Vorschlag, die beiden
        Enden, die Mitte, eine angeklickte Stelle – und „Im Bild wählen …“. Neu gebaut, wenn sich
        die Nuten ändern; sonst nur die Texte."""
        stellen = list(stellen or [])
        gleich = [st[0] for st in stellen] == [st[0] for st in self._stellen]
        self._stellen = stellen
        if not gleich:
            while self.stellen_aufbau.count():
                alt = self.stellen_aufbau.takeAt(0).widget()
                if alt is not None:
                    alt.deleteLater()
            self._stellen_zeilen = {}
            for nummer, (schluessel, *_rest) in enumerate(stellen):
                self._stellen_zeilen[schluessel] = self._stelle_zeile(nummer, len(stellen))
        for schluessel, anteil, vorgeschlagen, a, b in stellen:
            self._stelle_fuellen(schluessel, anteil, vorgeschlagen, a, b)
        self.stellen_box.setVisible(bool(stellen))

    def _stelle_zeile(self, nummer, anzahl):
        zeile = QtGui.QWidget()
        aufbau = QtGui.QHBoxLayout(zeile)
        aufbau.setContentsMargins(0, 0, 0, 0)
        text = tr("ba.nut.eintauchen")
        if anzahl > 1:
            text = tr("ba.nut.eintauchen.nut", n=nummer + 1)
        etikett = QtGui.QLabel(text)
        etikett.setToolTip(tr("ba.nut.eintauchen.tooltip"))
        aufbau.addWidget(etikett)
        wahl = QtGui.QComboBox()
        wahl.setToolTip(tr("ba.nut.eintauchen.tooltip"))
        ruhiges_mausrad(wahl)
        aufbau.addWidget(wahl, 1)
        im_bild = QtGui.QPushButton(tr("ba.nut.im_bild"))
        im_bild.setToolTip(tr("ba.nut.im_bild.tooltip"))
        im_bild.setCheckable(True)
        aufbau.addWidget(im_bild)
        self.stellen_aufbau.addWidget(zeile)
        teile = {"wahl": wahl, "im_bild": im_bild}
        wahl.currentIndexChanged.connect(lambda _i, t=teile: self._stelle_gewaehlt(t))
        im_bild.toggled.connect(lambda an, t=teile: self._im_bild(t, an))
        return teile

    def _stelle_fuellen(self, schluessel, anteil, vorgeschlagen, a, b):
        """Die Liste einer Nut: an erster Stelle der Vorschlag, dann Ende, Ende, Mitte und die
        angeklickte Stelle; gewählt, was im Block steht."""
        teile = self._stellen_zeilen[schluessel]
        teile["schluessel"], teile["a"], teile["b"] = schluessel, a, b
        wahl = teile["wahl"]

        def ort(t):
            x = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            return {
                "x": groesse_zeigen(x, einheiten.LAENGE) or "0",
                "y": groesse_zeigen(y, einheiten.LAENGE) or "0",
            }

        if vorgeschlagen and anteil is not None:
            vorschlag = tr("ba.nut.vorschlag.stelle", **ort(anteil))
        elif vorgeschlagen:
            vorschlag = tr("ba.nut.vorschlag.enden")
        else:  # gewählt – der Vorschlag rechnet erst ohne Wahl
            vorschlag = tr("ba.nut.vorschlag")
        eintraege = [
            (vorschlag, None),
            (tr("ba.nut.ende", **ort(0.0)), 0.0),
            (tr("ba.nut.ende", **ort(1.0)), 1.0),
            (tr("ba.nut.mitte", **ort(0.5)), 0.5),
        ]
        gewaehlt = self.eintauchen.get(schluessel)
        if gewaehlt is not None and all(abs(gewaehlt - wert) > 1e-6 for _t, wert in eintraege[1:]):
            eintraege.append((tr("ba.nut.angeklickt", **ort(gewaehlt)), gewaehlt))
        wahl.blockSignals(True)
        try:
            wahl.clear()
            for text, wert in eintraege:
                wahl.addItem(text, wert)
            index = 0
            if gewaehlt is not None:
                index = next(
                    (i for i, (_t, w) in enumerate(eintraege) if w is not None
                     and abs(w - gewaehlt) < 1e-6),
                    0,
                )  # fmt: skip
            wahl.setCurrentIndex(index)
        finally:
            wahl.blockSignals(False)

    def _stelle_gewaehlt(self, teile):
        if self.panel._fuellt or "schluessel" not in teile:
            return
        wert = teile["wahl"].currentData()
        if wert is None:
            self.eintauchen.pop(teile["schluessel"], None)
        else:
            self.eintauchen[teile["schluessel"]] = float(wert)
        self.panel.vorschau_starten()

    def _im_bild(self, teile, an):
        """„Im Bild wählen …“: der nächste Klick in die Nut ist ihre Eintauchstelle."""
        for andere in self._stellen_zeilen.values():
            if andere is not teile and andere["im_bild"].isChecked():
                andere["im_bild"].blockSignals(True)
                andere["im_bild"].setChecked(False)
                andere["im_bild"].blockSignals(False)
        self.stelle_waehlt = teile.get("schluessel") if an else None

    def stelle_angeklickt(self, punkt):
        """Der Klick für „Im Bild wählen …“: die Stelle der Mittellinie, die ihm am nächsten
        liegt, wird die Eintauchstelle der Nut."""
        teile = self._stellen_zeilen.get(self.stelle_waehlt)
        self.stelle_waehlt = None
        if teile is None:
            return
        teile["im_bild"].blockSignals(True)
        teile["im_bild"].setChecked(False)
        teile["im_bild"].blockSignals(False)
        a, b = teile["a"], teile["b"]
        dx, dy = b[0] - a[0], b[1] - a[1]
        laenge2 = dx * dx + dy * dy
        anteil = 0.0
        if laenge2 > 1e-12:
            x, y = float(punkt[0]), float(punkt[1])
            anteil = min(1.0, max(0.0, ((x - a[0]) * dx + (y - a[1]) * dy) / laenge2))
        self.eintauchen[teile["schluessel"]] = anteil
        self.panel.vorschau_starten()

    def kann_anlegen(self):
        return self.fraeser() is not None and self.einsatz() is not None and not self.hinweis.text()

    def merken(self):
        if self.fraeser() is not None:
            _parameter().SetString(self.s.gemerkt, self.fraeser().kennung)

    # --- Fräser und Einsatz ---

    @staticmethod
    def _passende_einsaetze(werkzeug, werkstoff):
        """Die Einsätze mit Drehzahl und Vorschub – nur mit ihnen gibt es einen Controller."""
        return [e for e in werkzeug.einsaetze(werkstoff) if js.werte(werkzeug, e)[1] > 0]

    def fraeser_setzen(self, werkzeug):
        """Wählt `werkzeug` in der Auswahl „Fräser“, wenn es dort steht; gibt zurück, ob."""
        kennungen = [w.kennung for w in self._fraeser]
        if werkzeug is None or werkzeug.kennung not in kennungen:
            return False
        self.wahl_fraeser.setCurrentIndex(kennungen.index(werkzeug.kennung))
        return True

    def fraeser_fuellen(self, bibliothek, werkstoff):
        """Die Werkzeuge, mit denen die Strategie arbeitet (_Strategie.werkzeug_passt: Fräser mit
        ebener Stirn, beim Bohren Bohrer), mit Schnittwerten für den Werkstoff; vorgewählt der
        bisher gewählte, beim Ändern der der Operation, sonst der zuletzt benutzte, sonst
        einer mit dem ersten Einsatz der Reihenfolge, sonst ein Schaftfräser."""
        vorher = self.fraeser()
        # Mit Magazin der Maschine (W-002 Stufe H2, E7 a) dessen Werkzeuge vorn, beladene zuerst.
        magazin = self.panel.magazin()
        self._fraeser = [
            w
            for w in mg.sortiert(bibliothek.werkzeuge, magazin)
            if w.durchmesser > 0
            and self.s.werkzeug_passt(w)
            and self._passende_einsaetze(w, werkstoff)
        ]
        kennungen = [w.kennung for w in self._fraeser]
        gemerkt = _parameter().GetString(self.s.gemerkt, "")
        erster = self.s.einsatz_reihenfolge[0] if self.s.einsatz_reihenfolge else None
        if vorher is not None and vorher.kennung in kennungen:
            wahl = kennungen.index(vorher.kennung)
        elif self.vorwahl in kennungen:
            wahl = kennungen.index(self.vorwahl)
        elif gemerkt in kennungen and (
            magazin is None
            or mg.rang(self._fraeser[kennungen.index(gemerkt)], magazin) != mg.NICHT_IM_MAGAZIN
        ):
            wahl = kennungen.index(gemerkt)
        else:
            wahl = min(
                range(len(self._fraeser)),
                key=lambda i: (
                    not any(
                        e.art == erster
                        for e in self._passende_einsaetze(self._fraeser[i], werkstoff)
                    ),
                    mg.rang(self._fraeser[i], magazin) == mg.NICHT_IM_MAGAZIN,
                    self._fraeser[i].art != self.s.bevorzugt,
                    i,
                ),
                default=0,
            )
        self.panel._fuellt = True
        try:
            self.wahl_fraeser.clear()
            for werkzeug in self._fraeser:
                self.wahl_fraeser.addItem(dezimal(mg.zeile(werkzeug, magazin)))
            if self._fraeser:
                self.wahl_fraeser.setCurrentIndex(wahl)
        finally:
            self.panel._fuellt = False
        self.magazin_pruefen()
        self.einsatz_fuellen(werkstoff)

    def _fraeser_gewaehlt(self):
        self.haken_pruefen()
        if not self.panel._fuellt:
            self.magazin_pruefen()
            self.einsatz_fuellen(self.panel.werkstoff())

    def magazin_pruefen(self):
        """Der gelbe Satz, wenn der gewählte Fräser nicht im Magazin der Maschine steht (E3 a):
        Das Programm ruft ihn mit einer freien Nummer auf, an der Steuerung fehlt er."""
        werkzeug = self.fraeser()
        text = mg.fehlt_text(werkzeug, self.panel.magazin()) if werkzeug is not None else ""
        self.magazin_satz.setText(text)
        self.magazin_zeile.setVisible(bool(text))

    def ins_magazin(self):
        """„Ins Magazin übernehmen“: der gewählte Fräser ins Magazin der Maschine – mit der
        Nummer, die er im Job schon hat, sonst der nächsten freien –, die Werkzeugverwaltung
        gespeichert, die Listen neu. Gibt den Eintrag zurück – None, wenn es nicht geht."""
        magazin = self.panel.magazin()
        werkzeug = self.fraeser()
        if magazin is None or werkzeug is None:
            return None
        eintrag = mg.uebernehmen(self.panel.bibliothek, magazin, werkzeug, self.panel.job)
        self.panel._bearbeitung_fuellen()
        return eintrag

    def einsatz_fuellen(self, werkstoff):
        """Die Einsätze des Fräsers; vorgewählt nach der Reihenfolge der Strategie; beim
        Ändern der, mit dem der Controller gesetzt ist."""
        werkzeug = self.fraeser()
        self._einsaetze = (
            self._passende_einsaetze(werkzeug, werkstoff) if werkzeug is not None else []
        )
        arten = [e.art for e in self._einsaetze]
        wahl = next((arten.index(a) for a in self.s.einsatz_reihenfolge if a in arten), 0)
        if self.tc_vorher is not None and werkzeug is not None and werkzeug.kennung == self.vorwahl:
            gemerkt = js.vorgeschlagener_einsatz(self.tc_vorher, self._einsaetze, self.panel.job)
            wahl = gemerkt if gemerkt >= 0 else wahl
        self.panel._fuellt = True
        try:
            self.wahl_einsatz.clear()
            for einsatz in self._einsaetze:
                self.wahl_einsatz.addItem(wz.einsatz_name(einsatz))
            if self._einsaetze:
                self.wahl_einsatz.setCurrentIndex(wahl)
        finally:
            self.panel._fuellt = False
        self._einsatz_gewaehlt()

    def _einsatz_gewaehlt(self):
        """Drehzahl und Vorschub, die Vorschläge in die Felder."""
        if self.panel._fuellt:
            return
        werkzeug, einsatz = self.fraeser(), self.einsatz()
        if werkzeug is None or einsatz is None:
            self.schnittwerte.setText("")
        else:
            n, vf, _senkrecht = js.werte_im_job(werkzeug, einsatz, self.panel.job)
            self.schnittwerte.setText(
                tr("va.schnittwerte", n=f"{n:.0f}", vf=groesse_fest(vf, einheiten.VORSCHUB, 0))
            )
        for feld, eingabe in self.felder.items():
            eingabe.setPlaceholderText(self.s.platzhalter(feld, werkzeug, einsatz))
        self.panel.vorschau_starten()

    # --- Vorschau ---

    def vorschau_rechnen(self, job, flaechen, zusatz=None):
        """Die grobe Bahn – Lagen, Zeilen bzw. Bahnen, Zeit – und damit „Anlegen“ weiß, ob
        es geht; der Grund steht rot. `zusatz`: Werte, die der Assistent vorgibt (die Breite
        der Kontur nach dem Räumen)."""
        self.vorschau = None
        self.zeit = None
        self.schon_weg = False
        self.ergebnis_basis = ""
        self.ergebnis.setText("")
        self.material.setText("")
        self.hinweis.setText("")
        werkzeug, einsatz = self.fraeser(), self.einsatz()
        if werkzeug is None or einsatz is None:
            self.hinweis.setText(tr("va.planfraeser.keiner"))
            return
        _n, vorschub, senkrecht = js.werte_im_job(werkzeug, einsatz, self.panel.job)
        werte = dict(self.werte(), vorschub=vorschub, eintauchen=senkrecht, **(zusatz or {}))
        # Woraus nichts anders ist als beim letzten Mal, kommt dasselbe heraus – nur das ändert
        # sich, wovon die Vorschau abhängt (am Testteil warm 4,2 s je Lauf für alle Blöcke).
        schluessel = _merk_schluessel(self.s.kennung, job, werkzeug, einsatz, werte, flaechen)
        merk = getattr(self.panel, "vorschau_merk", None)
        if schluessel is not None and merk is not None and schluessel in merk:
            merk.move_to_end(schluessel)
            self._gemerkt_zeigen(merk[schluessel])
            return
        try:
            self.vorschau = self.s.vorschau(job, werkzeug, werte, flaechen)
        except (ValueError, RuntimeError) as fehler:  # RuntimeError: OCC am Netz
            self.hinweis.setText(str(fehler))
            self.schon_weg = isinstance(fehler, mst.SchonWeg)
            self._merken(merk, schluessel)
            return
        self.zeit = self.s.zeit(self.vorschau, vorschub, senkrecht) if vorschub > 0 else None
        if self.zeit is not None and self.s.kennung in IM_FREIEN_SCHNELL:
            self.zeit = _zeit_im_freien(job, werkzeug, werte, self.vorschau, vorschub, senkrecht)
        zeit = _zeit_text(self.zeit) if self.zeit is not None else "?"
        self.ergebnis_basis = self.s.ergebnis_text(self.vorschau, zeit)
        self.ergebnis.setText(self.ergebnis_basis)
        self.material.setText(_material_text(self.vorschau))
        if self.s.kennung == "nut":
            self.stellen_zeigen(getattr(self.vorschau, "stellen", None))
        self._merken(merk, schluessel)

    def _merken(self, merk, schluessel):
        """Merkt, was die Vorschau ergab – höchstens VORSCHAU_MERK, die ältesten fallen heraus."""
        if schluessel is None or merk is None:
            return
        merk[schluessel] = (
            self.vorschau,
            self.zeit,
            self.schon_weg,
            self.ergebnis_basis,
            self.material.text(),
            self.hinweis.text(),
        )
        while len(merk) > VORSCHAU_MERK:
            merk.popitem(last=False)

    def _gemerkt_zeigen(self, gemerkt):
        vorschau, zeit, schon_weg, basis, material, hinweis = gemerkt
        self.vorschau, self.zeit, self.schon_weg = vorschau, zeit, schon_weg
        self.ergebnis_basis = basis
        self.ergebnis.setText(basis)
        self.material.setText(material)
        self.hinweis.setText(hinweis)
        if self.s.kennung == "nut" and vorschau is not None:
            self.stellen_zeigen(getattr(vorschau, "stellen", None))

    def leeren(self):
        self.vorschau = None
        self.zeit = None
        self.schon_weg = False
        self.ergebnis_basis = ""
        self.ergebnis.setText("")
        self.material.setText("")
        self.hinweis.setText("")


# Die Blöcke, deren Operationen im Freien mit dem Freivorschub fahren (freiwege) – ihre Zeit im
# Assistenten rechnet ihn mit, und der Wettbewerb vergleicht so die Zeiten der Operationen.
IM_FREIEN_SCHNELL = {
    "planfraesen",
    "raeumen",
    "restraeumen",
    "nut",
    "kontur",
    "entgraten",
    "schruppen3d",
    "restschruppen",
    "schlichten3d",
    "restschlichten",
    "bleistift",
}


def _zeit_im_freien(job, werkzeug, werte, bahn, vorschub, eintauchen):
    """Die Zeit der Vorschau (min) mit dem Freivorschub im Freien – wie die Operation fährt
    (freiwege). Gerechnet im Materialstand, den der Assistent dem Block gibt; ohne ihn wie
    bisher."""
    from . import freiwege as fw

    punkte = getattr(bahn, "punkte", None)
    stand = werte.get("materialstand")
    form = ff.von_werkzeug(werkzeug)
    if not punkte or stand is None or form is None:
        return bn.zeit(punkte or [], vorschub, eintauchen)
    quader = mst._kopie(stand).quader
    neu, _weg = fw.schneller(punkte, form, quader, vorschub, fw.freivorschub_fuer(job))
    return bn.zeit(neu, vorschub, eintauchen)


def _merk_schluessel(kennung, job, werkzeug, einsatz, werte, flaechen):
    """Woraus die Vorschau eines Blocks gerechnet wird, als Text: Strategie, Flächen, Werkzeug,
    Einsatz, alle Werte (der Materialstand mit seiner Kennung), Teil und Rohteil im Job (Lage,
    Hüllquader, Volumen, Form). Was sich nicht eindeutig schreiben lässt (eine Adresse im Text),
    trifft nie – dann wird gerechnet. None, wenn es nicht geht."""
    try:
        stand = werte.get("materialstand")
        rein = sorted((k, repr(v)) for k, v in werte.items() if k != "materialstand")
        teile = []
        for objekt in (vr.modell(job), getattr(job, "Stock", None)):
            form = getattr(objekt, "Shape", None)
            if form is None or form.isNull():
                teile.append(None)
                continue
            bb = form.BoundBox
            huelle = (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)
            teile.append((repr(objekt.Placement), huelle, round(form.Volume, 6), form.hashCode()))
        text = repr(
            (
                kennung,
                tuple(flaechen),
                repr(werkzeug),
                repr(einsatz),
                rein,
                getattr(stand, "kennung", None) if stand is not None else None,
                teile,
            )
        )
    except Exception:  # ein Wert ohne Text – dann eben rechnen
        return None
    return None if " at 0x" in text else text


def rohteil_kandidaten(dokument, teil=None):
    """Die Körper im Dokument, die das Rohteil sein können (W-011 S4): geschlossene Körper oben
    im Baum – nicht das Teil selbst, nichts aus einem Job (Modell, Rohteil, Werkzeuge,
    Operationen), keine Features in einem Körper, keine Gruppen. Nach dem Namen sortiert."""
    ergebnis = []
    for objekt in dokument.Objects:
        if objekt is teil or not hasattr(objekt, "Shape") or hasattr(objekt, "Path"):
            continue
        if any(hasattr(objekt, e) for e in ("PathResource", "StockType", "ToolBitID", "ExtZpos")):
            continue
        if objekt.isDerivedFrom("App::DocumentObjectGroup"):
            continue
        if objekt.getParentGeoFeatureGroup() is not None:
            continue  # ein Feature in einem Körper – der Körper zählt
        ansicht = getattr(objekt, "ViewObject", None)
        if ansicht is not None and not getattr(ansicht, "ShowInTree", True):
            continue
        try:
            form = objekt.Shape
            fest = not form.isNull() and form.Volume > 1e-9 and form.isClosed()
        except Exception:  # eine kaputte Form: kein Rohteil
            fest = False
        if fest:
            ergebnis.append(objekt)
    return sorted(ergebnis, key=lambda o: o.Label)


class BearbeitungPanel:
    """Aufgabenfenster „Bearbeitung (Fräsen)“ – anlegen, oder mit `operation=` ändern."""

    offen = None  # das offene Fenster – für die Oberflächen-Szenarien

    def __init__(self, dokument, wahl=None, operation=None, neu=False, angeklickt=None):
        BearbeitungPanel.offen = self
        self.doc = dokument
        # Hat das Teil schon einen Job, kommen die neuen Operationen dort hinein (W-012 M2) –
        # außer `neu`: „Neuer Job …“ für eine zweite Aufspannung.
        self._neu = bool(neu)
        self._job_dazu = False  # der Job war schon da: Aufspannung fest, nichts zurückzunehmen
        self._wahl_anfang = wahl  # (Teil, „FaceN“) – für den Wechsel zum 4-Achs-Assistenten
        self.job = None
        self.teil = None
        self.bibliothek = None
        self.gewaehlte = []  # die Flächen („Face6“ …) – leer: die Oberseite
        self.kanten = []  # angeklickte Kanten („Edge12“ …) – nur für „Entgraten 3D“
        self.operation = operation  # die erste angelegte Operation – oder die, die man ändert
        self.operationen = []  # alle angelegten
        self.zu_aendern = operation
        self.block_zu_aendern = None
        self._fuellt = False
        self._ruhig = False  # das Fenster setzt selbst einen Fräser: keine neue Vorschau
        self.geschlossen = False
        self._knoepfe = None
        self._beobachter = None
        self._sichtbar_vorher = None  # (Teil, war sichtbar) – das Original
        self._aufspannung_vorher = []  # [(Objekt, war sichtbar)] – gui_schwenken.zeige_job
        self._rohteil_sichtbar_vorher = None  # (Körper, war sichtbar) – das Rohteil-Original
        # Je Block gemerkte Vorschauen über die Läufe hinweg: woraus gerechnet → was herauskam.
        self.vorschau_merk = OrderedDict()
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
        self._nullpunkt_uhr = QtCore.QTimer()
        self._nullpunkt_uhr.setSingleShot(True)
        self._nullpunkt_uhr.setInterval(NACHZIEHEN_MS)
        self._nullpunkt_uhr.timeout.connect(self._nullpunkt_anwenden)
        self._nullpunkte = nullpunkte()
        self._unten = None  # die Fläche des Teils, die unten liegt („Face6“) – None: wie modelliert
        self._viertel = 0  # X um so viele Viertel um Z gedreht
        self.bloecke = []
        self.form = self._baue()
        self.plan = next(b for b in self.bloecke if b.s.kennung == "planfraesen")
        self.raeumen = next(b for b in self.bloecke if b.s.kennung == "raeumen")
        self.restraeumen = next(b for b in self.bloecke if b.s.kennung == "restraeumen")
        self.schlichten_danach = next(b for b in self.bloecke if b.s.kennung == "schlichtendanach")
        self.nut = next(b for b in self.bloecke if b.s.kennung == "nut")
        self._raeumen_boeden = None  # nur diese Taschenböden räumen (_folge); None: alle
        self.bohren = next(b for b in self.bloecke if b.s.kennung == "bohren")
        self.bohrung = next(b for b in self.bloecke if b.s.kennung == "bohrung")
        self.kontur = next(b for b in self.bloecke if b.s.kennung == "kontur")
        self.gewinde = next(b for b in self.bloecke if b.s.kennung == "gewinde")
        self.gewindefraesen = next(b for b in self.bloecke if b.s.kennung == "gewindefraesen")
        self.entgraten = next(b for b in self.bloecke if b.s.kennung == "entgraten")
        self.entgraten3d = next(b for b in self.bloecke if b.s.kennung == "entgraten3d")
        self.zentrieren = next(b for b in self.bloecke if b.s.kennung == "zentrieren")
        self.senken = next(b for b in self.bloecke if b.s.kennung == "senken")
        self.reiben = next(b for b in self.bloecke if b.s.kennung == "reiben")
        self.schlichten3d = next(b for b in self.bloecke if b.s.kennung == "schlichten3d")
        self.flanke = next(b for b in self.bloecke if b.s.kennung == "flanke")
        self.schruppen3d = next(b for b in self.bloecke if b.s.kennung == "schruppen3d")
        self.bleistift = next(b for b in self.bloecke if b.s.kennung == "bleistift")
        self.rest = next(b for b in self.bloecke if b.s.kennung == "rest")
        self.restschlichten = next(b for b in self.bloecke if b.s.kennung == "restschlichten")
        self.restschruppen = next(b for b in self.bloecke if b.s.kennung == "restschruppen")
        self._beobachter = _Beobachter(self)
        FreeCADGui.Selection.addObserver(self._beobachter)
        FreeCADGui.Selection.addSelectionGate(_NurFlaechen(self))
        if operation is not None:
            self._zum_aendern()
            self.seite_zeigen(2)
            return
        if wahl is not None:
            self._beginnen(wahl, angeklickt)
        self.seite_zeigen(0)
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
        # Oben, in welchem der drei Schritte man ist; darunter, was dort zu tun ist.
        self.schritt_text = QtGui.QLabel()
        schrift = self.schritt_text.font()
        schrift.setBold(True)
        schrift.setPointSizeF(schrift.pointSizeF() * 1.15)
        self.schritt_text.setFont(schrift)
        aufbau.addWidget(self.schritt_text)
        self.anleitung = QtGui.QLabel(tr("ba.anleitung"))
        self.anleitung.setWordWrap(True)
        aufbau.addWidget(self.anleitung)

        ziel = [aufbau]  # wohin titel() und grautext() setzen

        def titel(text, tooltip=""):
            etikett = QtGui.QLabel(text)
            etikett.setToolTip(tooltip)
            schrift = etikett.font()
            schrift.setBold(True)
            etikett.setFont(schrift)
            ziel[0].addWidget(etikett)
            return etikett

        def grautext(text=""):
            etikett = _grau(text)
            ziel[0].addWidget(etikett)
            return etikett

        # Drei Schritte wie im 4-Achs-Assistenten (Manuel, 2026-10-02: „man fragt es in Schritten
        # ab“, „Rohteil und Nullpunkt … wo man auf Weiter klicken kann, wenn's fertig ist“):
        # Aufspannung – was soll weg – Einstellungen. „Anlegen“ geht aus jedem Schritt.
        self.seiten = []
        for _nummer in range(3):
            seite = QtGui.QWidget()
            seite_aufbau = QtGui.QVBoxLayout(seite)
            seite_aufbau.setContentsMargins(0, 0, 0, 0)
            aufbau.addWidget(seite)
            self.seiten.append(seite)

        # --- Schritt 1: Aufspannung – Maschine, Teil, Rohteil, Nullpunkt ---
        ziel[0] = self.seiten[0].layout()
        # Hat das Teil schon einen Job, kommen die neuen Operationen dort hinein (W-012 M2).
        self.dazu_zeile = QtGui.QWidget()
        dazu = QtGui.QHBoxLayout(self.dazu_zeile)
        dazu.setContentsMargins(0, 0, 0, 0)
        self.dazu_text = QtGui.QLabel()
        self.dazu_text.setWordWrap(True)
        dazu.addWidget(self.dazu_text, 1)
        self.knopf_neuer_job = knopf(
            tr("ba.neuer_job"), tr("ba.neuer_job.tooltip"), lambda: self.neuer_job()
        )
        dazu.addWidget(self.knopf_neuer_job, 0, QtCore.Qt.AlignTop)
        self.dazu_zeile.setVisible(False)
        ziel[0].addWidget(self.dazu_zeile)
        oben = _Reihen()
        # Die Maschine zuerst (W-011 S2; Manuel, 2026-10-02: „Immer wenn ich ein Teil lade,
        # sollte ich die Maschine auswählen“): die Liste aus „Maschinen …“, gemerkt am Job.
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        self.wahl_maschine = QtGui.QComboBox()
        knoepfe.addWidget(self.wahl_maschine, 1)
        self.knopf_maschinen = knopf(
            tr("befehl.maschinen.titel"), tr("ba.maschine.liste.tooltip"), self.maschinen_oeffnen
        )
        knoepfe.addWidget(self.knopf_maschinen)
        oben.reihe(tr("ba.maschine"), tr("ba.maschine.tooltip"), zeile)
        self.maschine_hinweis = _grau()
        oben.ganz(self.maschine_hinweis)
        # Liegt die Datei nicht mehr dort: gleich hier weiter – wiederfinden oder aus der Liste
        # nehmen, statt über „Maschinen …“ (Manuel, 2026-10-10: im Flow bleiben).
        self.maschine_knoepfe = QtGui.QWidget()
        reihe = QtGui.QHBoxLayout(self.maschine_knoepfe)
        reihe.setContentsMargins(0, 0, 0, 0)
        self.knopf_maschine_suchen = knopf(
            tr("ms.suchen"), tr("ms.suchen.tooltip"), self.maschine_suchen
        )
        self.knopf_maschine_entfernen = knopf(
            tr("ba.maschine.entfernen"),
            tr("ba.maschine.entfernen.tooltip"),
            self.maschine_entfernen,
        )
        reihe.addWidget(self.knopf_maschine_suchen)
        reihe.addWidget(self.knopf_maschine_entfernen)
        reihe.addStretch()
        oben.ganz(self.maschine_knoepfe)
        self.maschine_knoepfe.hide()
        # Drehmaschine oder 4-Achs-Fräse: Das Rohteil ist eine Stange (W-011 S3) – weiter im
        # 4-Achs-Assistenten, mit Teil, Fläche und Maschine.
        self.knopf_vierachs = knopf(
            tr("ba.maschine.vierachs"), tr("ba.maschine.vierachs.tooltip"), self.zum_vierachs
        )
        self.knopf_vierachs.setVisible(False)
        oben.ganz(self.knopf_vierachs)
        self.teil_text = QtGui.QLabel(tr("ba.teil.keins"))
        self.teil_text.setWordWrap(True)
        oben.reihe(tr("ba.teil"), "", self.teil_text)
        # Wie das Teil auf dem Tisch liegt (Manuel, 2026-10-02: „man klickt auf eine Fläche,
        # welche dann sozusagen unten ist … fehlt nur noch die X- und Y-Achse – aber das muss
        # sein“): in Schritt 1 macht ein Klick auf eine ebene Fläche sie zur Unterseite, X dreht
        # in Vierteln um Z; Rohteil und Nullpunkt folgen.
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        self.unten_text = QtGui.QLabel(tr("ba.unten.modell"))
        knoepfe.addWidget(self.unten_text, 1)
        # Erst dieser Knopf macht den nächsten Klick zur Unterseite – ein Klick auf die Fläche,
        # die bearbeitet werden soll, dreht so nie aus Versehen das Teil.
        self.knopf_unten_waehlen = QtGui.QPushButton(tr("ba.unten.waehlen"))
        self.knopf_unten_waehlen.setToolTip(tr("ba.unten.waehlen.tooltip"))
        self.knopf_unten_waehlen.setCheckable(True)
        knoepfe.addWidget(self.knopf_unten_waehlen)
        self.knopf_unten_modell = knopf(
            tr("ba.unten.zurueck"), tr("ba.unten.zurueck.tooltip"), lambda: self.unten_waehlen(None)
        )
        knoepfe.addWidget(self.knopf_unten_modell)
        oben.reihe(tr("ba.unten"), tr("ba.unten.tooltip"), zeile)
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        self.x_text = QtGui.QLabel(tr("ba.x.modell"))
        knoepfe.addWidget(self.x_text, 1)
        self.knopf_x_links = knopf(tr("ba.x.links"), tr("ba.x.tooltip"), lambda: self.x_drehen(1))
        knoepfe.addWidget(self.knopf_x_links)
        self.knopf_x_rechts = knopf(
            tr("ba.x.rechts"), tr("ba.x.tooltip"), lambda: self.x_drehen(-1)
        )
        knoepfe.addWidget(self.knopf_x_rechts)
        oben.reihe(tr("ba.x"), tr("ba.x.tooltip"), zeile)
        ziel[0].addWidget(oben.widget)
        self._maschinen_fuellen()
        self.wahl_maschine.currentIndexChanged.connect(lambda _i: self._maschine_gewaehlt())
        self._lage_zeigen()
        titel(tr("ba.rohteil"), tr("ba.rohteil.text"))
        # Ein Quader mit Aufmaß – oder ein Körper aus dem Dokument (W-011 S4; Manuel,
        # 2026-10-02: „Rohteil kann auch ein konstruiertes Teil sein“).
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        self.knopf_rohteil_quader = QtGui.QRadioButton(tr("ba.rohteil.quader"))
        self.knopf_rohteil_quader.setToolTip(tr("ba.rohteil.text"))
        self.knopf_rohteil_teil = QtGui.QRadioButton(tr("ba.rohteil.teil"))
        self.knopf_rohteil_teil.setToolTip(tr("ba.rohteil.teil.tooltip"))
        self.knopf_rohteil_quader.setChecked(True)
        knoepfe.addWidget(self.knopf_rohteil_quader)
        knoepfe.addWidget(self.knopf_rohteil_teil)
        knoepfe.addStretch()
        ziel[0].addWidget(zeile)
        self.rohteil_erklaerung = grautext(tr("ba.rohteil.text"))
        koerper = _Reihen()
        self.wahl_rohteil = QtGui.QComboBox()
        koerper.reihe(tr("ba.rohteil.koerper"), tr("ba.rohteil.teil.tooltip"), self.wahl_rohteil)
        self.rohteil_koerper = koerper.widget
        self.rohteil_koerper.setVisible(False)
        ziel[0].addWidget(self.rohteil_koerper)
        self.knopf_rohteil_teil.toggled.connect(lambda _an: self._rohteil_art_geaendert())
        self.wahl_rohteil.currentIndexChanged.connect(lambda _i: self._rohteil_geaendert())
        rohteil = _Reihen()
        self.felder_rohteil = {}
        for feld, text, tooltip in (
            ("oben", tr("ba.rohteil.oben"), tr("ba.rohteil.oben.tooltip")),
            ("seite", tr("ba.rohteil.seite"), tr("ba.rohteil.seite.tooltip")),
            ("unten", tr("ba.rohteil.unten"), tr("ba.rohteil.unten.tooltip")),
        ):
            eingabe = _zahlenfeld(
                self.felder_rohteil, feld, text, tooltip, rohteil, self._rohteil_geaendert
            )
            eingabe.setPlaceholderText(groesse_zeigen(AUFMASS_ROHTEIL, einheiten.LAENGE) or "0")
        self.rohteilfelder = rohteil.widget
        ziel[0].addWidget(self.rohteilfelder)
        # Von unten gespannt (S3h, Manuel 2026-10-01): so viel steckt im Schraubstock – auch beim
        # Ändern einstellbar, es verschiebt nichts.
        reihen_spannung = _Reihen()
        self.felder_spannung = {}
        _zahlenfeld(
            self.felder_spannung,
            "gespannt",
            tr("ba.gespannt"),
            tr("ba.gespannt.tooltip"),
            reihen_spannung,
            self._spannung_geaendert,
        ).setPlaceholderText("0")
        self.spannungfelder = reihen_spannung.widget
        ziel[0].addWidget(self.spannungfelder)
        self.nullpunkt_titel = titel(tr("ba.nullpunkt"), tr("ba.nullpunkt.text"))
        self.nullpunkt_text = grautext(tr("ba.nullpunkt.text"))
        nullpunkt = _Reihen()
        self.wahl_nullpunkt = QtGui.QComboBox()
        self.wahl_nullpunkt.addItem(tr("ba.nullpunkt.modell"), 0)
        for nummer, (text, _lage) in enumerate(self._nullpunkte, start=1):
            self.wahl_nullpunkt.addItem(text, nummer)
        gemerkt = _gemerkter_nullpunkt()
        if gemerkt is not None:
            nummer = next(
                (n for n, (_t, lage) in enumerate(self._nullpunkte, start=1) if lage == gemerkt),
                0,
            )
            self.wahl_nullpunkt.setCurrentIndex(self.wahl_nullpunkt.findData(nummer))
        self.wahl_nullpunkt.currentIndexChanged.connect(lambda _i: self._nullpunkt_geaendert())
        nullpunkt.reihe(
            tr("ba.nullpunkt.wahl"), tr("ba.nullpunkt.wahl.tooltip"), self.wahl_nullpunkt
        )
        self.felder_nullpunkt = {}
        for feld, text in (
            ("x", tr("ba.nullpunkt.x")),
            ("y", tr("ba.nullpunkt.y")),
            ("z", tr("ba.nullpunkt.z")),
        ):
            eingabe = _zahlenfeld(
                self.felder_nullpunkt,
                feld,
                text,
                tr("ba.nullpunkt.versatz.tooltip"),
                nullpunkt,
                self._nullpunkt_geaendert,
            )
            eingabe.setPlaceholderText("0")
        self.nullpunktfelder = nullpunkt.widget
        ziel[0].addWidget(self.nullpunktfelder)

        # --- Schritt 2: was soll weg – Flächen, Werkstoff, Ziel, die Strategien im Überblick ---
        ziel[0] = self.seiten[1].layout()
        # Was in Schritt 1 gilt, als eine graue Zeile (ändern: „Zurück“).
        self.rohteil_kurz = grautext()
        titel(tr("ba.flaechen"), tr("ba.flaechen.tooltip"))
        self.flaechen_liste = QtGui.QListWidget()
        self.flaechen_liste.setToolTip(tr("ba.flaechen.liste.tooltip"))
        self.flaechen_liste.itemDoubleClicked.connect(
            lambda eintrag: self.flaeche_umschalten(eintrag.data(QtCore.Qt.UserRole))
        )
        ziel[0].addWidget(self.flaechen_liste)
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
        ziel[0].addWidget(zeile)
        # Eine schräge ebene Fläche gewählt: geschwenkt fräsen (3+2, W-014).
        self.schwenken_zeile = QtGui.QWidget()
        schwenken = QtGui.QVBoxLayout(self.schwenken_zeile)
        schwenken.setContentsMargins(0, 0, 0, 0)
        self.schwenken_text = QtGui.QLabel()
        self.schwenken_text.setWordWrap(True)
        schwenken.addWidget(self.schwenken_text)
        self.schwenken_knopf = knopf(
            tr("ba.schwenken.knopf"), tr("ba.schwenken.knopf.tooltip"), self.ebene_schwenken
        )
        schwenken.addWidget(self.schwenken_knopf, 0, QtCore.Qt.AlignLeft)
        self.schwenken_zeile.hide()
        ziel[0].addWidget(self.schwenken_zeile)
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
        ziel[0].addWidget(werkstoff.widget)
        # Das Ziel: wie viel weg muss und wie lange es mindestens dauert (Manuel, 2026-10-02:
        # „dass man erstmal ein Ziel rechnet von der Zeit her“).
        self.ziel_text = grautext()
        self.ziel_text.setToolTip(tr("ba.ziel.tooltip"))
        # Der schnellere Fräser aus der Ziel-Zeile mit einem Klick – freiwillig (Manuel,
        # 2026-10-02: „ja, aber man muss nicht – wenn man es mit einem Fräser fräsen will, ist
        # das so“).
        self._schneller = None  # zielzeit.Angebot hinter „Schneller aus der Werkzeugkiste“
        self.knopf_schneller = knopf(
            tr("ba.ziel.uebernehmen"), tr("ba.ziel.uebernehmen.tooltip"), self.schneller_uebernehmen
        )
        self.knopf_schneller.hide()
        zeile_schneller = QtGui.QHBoxLayout()
        zeile_schneller.setContentsMargins(0, 0, 0, 0)
        zeile_schneller.addWidget(self.knopf_schneller)
        zeile_schneller.addStretch()
        ziel[0].addLayout(zeile_schneller)
        # Je Strategie ein Haken mit ihrem Ergebnis – was zur Wahl passt oben, darunter
        # eingeklappt, was (noch) nicht passt (_bloecke_ordnen).
        strategien = QtGui.QWidget()
        self._block_aufbau = QtGui.QVBoxLayout(strategien)
        self._block_aufbau.setContentsMargins(0, 0, 0, 0)
        self._block_anfang = 0
        ziel[0].addWidget(strategien)
        for strategie in STRATEGIEN:
            block = _Block(self, strategie())
            self.bloecke.append(block)
            self._block_aufbau.addWidget(block.widget)
        # Was nicht passt, steht eingeklappt unter einer Zeile mit seiner Zahl; ein Klick zeigt je
        # Strategie, was man dafür im 3D anklicken muss.
        self.passt_nicht = QtGui.QWidget()
        kopf_aufbau = QtGui.QHBoxLayout(self.passt_nicht)
        kopf_aufbau.setContentsMargins(0, 0, 0, 0)
        self.passt_nicht_knopf = _klappknopf("", tr("ba.passt_nicht.tooltip"))
        kopf_aufbau.addWidget(self.passt_nicht_knopf)
        self.passt_nicht_kurz = _grau(tr("ba.passt_nicht.zu"))
        kopf_aufbau.addWidget(self.passt_nicht_kurz, 1)
        self.passt_nicht.hide()
        self._block_aufbau.addWidget(self.passt_nicht)
        self._reihe = [b.widget for b in self.bloecke] + [self.passt_nicht]
        self.passt_nicht_knopf.toggled.connect(self._passt_nicht_aufklappen)

        # --- Schritt 3: die Einstellungen der angehakten Strategien ---
        ziel[0] = self.seiten[2].layout()
        self.nichts_angehakt = grautext(tr("ba.einstellungen.leer"))
        for block in self.bloecke:
            ziel[0].addWidget(block.einstellungen)
            block.zustand_zeigen()
        ziel[0] = aufbau
        for seite in self.seiten:
            seite.layout().addStretch()

        # Unter allen Schritten: rot, welche gewählte Fläche am Ende keine genaue Bahn hätte
        # (Grundsatz 0; Manuel, 2026-10-03: „das Teil sollte danach schon so ausschauen, wie's
        # ausschauen soll“), rot, was nicht geht, und „Zurück“ / „Weiter“.
        self.unfertig = QtGui.QLabel()
        self.unfertig.setWordWrap(True)
        self.unfertig.setStyleSheet(f"color: {ROT};")
        self.unfertig.hide()
        aufbau.addWidget(self.unfertig)
        self.hinweis = QtGui.QLabel()
        self.hinweis.setWordWrap(True)
        self.hinweis.setStyleSheet(f"color: {ROT};")
        aufbau.addWidget(self.hinweis)
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        self.knopf_zurueck = knopf(tr("ba.zurueck"), tr("ba.zurueck.tooltip"), self.zurueck)
        knoepfe.addWidget(self.knopf_zurueck)
        knoepfe.addStretch()
        self.knopf_weiter = knopf(tr("ba.weiter"), tr("ba.weiter.tooltip"), self.weiter)
        knoepfe.addWidget(self.knopf_weiter)
        # Dasselbe wie „OK“ der Aufgabe: „Anlegen“, beim Ändern „Übernehmen“.
        self.knopf_fertig = knopf(tr("va.anlegen"), tr("ba.anlegen.tooltip"), self.accept)
        self.knopf_fertig.hide()
        knoepfe.addWidget(self.knopf_fertig)
        aufbau.addWidget(zeile)
        self._seite = 0
        # Die Beschriftungen aller Blöcke gleich breit: die Felder stehen untereinander.
        reihen = [oben, koerper, rohteil, nullpunkt, werkstoff] + [b.reihen for b in self.bloecke]
        breite = max(r.breite_beschriftung() for r in reihen)
        for r in reihen:
            r.raster.setColumnMinimumWidth(0, breite)
        aufbau.addStretch()
        ruhiges_mausrad(form)
        return form

    # --- Die Schritte -----------------------------------------------------------------------

    def seite(self):
        """Der gezeigte Schritt: 0 Aufspannung, 1 was soll weg, 2 Einstellungen."""
        return self._seite

    def seite_zeigen(self, nummer):
        """Zeigt den Schritt `nummer` (0–2): seine Seite, oben „Schritt 2 von 3 – …“, darunter
        die passende Anleitung; „Zurück“ und „Weiter“, wo es sie gibt – weiter erst mit Job."""
        self._seite = max(0, min(int(nummer), len(self.seiten) - 1))
        for i, seite in enumerate(self.seiten):
            seite.setVisible(i == self._seite)
        namen = (
            tr("ba.schritt.aufspannung"),
            tr("ba.schritt.was"),
            tr("ba.schritt.einstellungen"),
        )
        self.schritt_text.setText(
            tr(
                "ba.schritt",
                nummer=self._seite + 1,
                anzahl=len(self.seiten),
                name=namen[self._seite],
            )
        )
        if self.zu_aendern is None:
            if self._job_dazu:
                erste = tr("ba.anleitung.dazu")  # die Zeile darunter sagt, welcher Job
            else:
                erste = tr("ba.anleitung") if self.job is None else tr("ba.anleitung.job")
            anleitungen = (
                erste,
                tr("ba.anleitung.was"),
                tr("ba.anleitung.einstellungen"),
            )
            self.anleitung.setText(anleitungen[self._seite])
        self._rohteil_kurz_zeigen()
        letzte = self._seite == len(self.seiten) - 1
        self.knopf_zurueck.setVisible(self._seite > 0)
        self.knopf_weiter.setVisible(not letzte)
        self.knopf_weiter.setEnabled(self.job is not None and not self.nur_vierachs())
        # Im letzten Schritt steht „Anlegen“ dort, wo vorher „Weiter“ stand (Manuel,
        # 2026-10-02: „als Mensch erwartet man dann den Button unten, wo der Weiter-Button war“).
        self.knopf_fertig.setVisible(letzte)
        self._knoepfe_beschriften()
        self.nichts_angehakt.setVisible(not self.aktive_bloecke())

    def weiter(self):
        if self.job is not None and not self.nur_vierachs():
            self.seite_zeigen(self._seite + 1)

    def zurueck(self):
        self.seite_zeigen(self._seite - 1)

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
        aendern = self.zu_aendern is not None
        geht = self.job is not None and self._kann_anlegen()
        unten = getattr(self, "knopf_fertig", None)
        for knopf_ in (self.knopf_anlegen(), unten):
            if knopf_ is None:
                continue
            if aendern:
                knopf_.setText(tr("va.uebernehmen"))
                knopf_.setToolTip(tr("ba.uebernehmen.tooltip"))
            else:
                knopf_.setText(tr("va.anlegen"))
                knopf_.setToolTip(tr("ba.anlegen.tooltip"))
            knopf_.setEnabled(geht)

    def aktive_bloecke(self):
        return [b for b in self.bloecke if b.aktiv()]

    def _kann_anlegen(self):
        aktive = self.aktive_bloecke()
        if not aktive or self.hinweis.text():
            return False
        return all(b.kann_anlegen() for b in aktive)

    def accept(self):
        if self.job is None:
            return self.reject()
        if self.nur_vierachs():
            QtGui.QMessageBox.information(self.form, tr("ba.titel"), tr("ba.maschine.drehmaschine"))
            return False
        if self._rohteil_uhr.isActive():
            self._rohteil_uhr.stop()
            self._rohteil_anwenden()
        if self._nullpunkt_uhr.isActive():
            self._nullpunkt_uhr.stop()
            self._nullpunkt_anwenden()
        if any(b.vorschau is None for b in self.aktive_bloecke()):
            self._vorschau_rechnen()
        if not self._kann_anlegen() or any(b.vorschau is None for b in self.aktive_bloecke()):
            return False  # der Grund steht rot im Fenster
        if self.zu_aendern is not None:
            if not self._aendern():
                return False
        else:
            # Job und Rohteil: ein Schritt Rückgängig. Die Operationen kommen in einem eigenen –
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
        for block in self.aktive_bloecke():
            block.merken()
        if not self._aufspannung_fest():
            nullpunkt_vorgeben(self.nullpunkt())
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    def reject(self):
        self._vor_dem_schliessen()
        if self._aufspannung_vorher:
            from .gui_schwenken import zeige_wieder

            zeige_wieder(self._aufspannung_vorher)
            self._aufspannung_vorher = []
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
        from .gui_reichweite import job_merken

        job_merken(self.job)  # Prüfen, Bestückung und Programm nehmen ihn ohne Auswahl
        self._vorschau_uhr.stop()
        self._rohteil_uhr.stop()
        self._nullpunkt_uhr.stop()
        self._farben_zurueck()
        if self._beobachter is not None:
            FreeCADGui.Selection.removeObserver(self._beobachter)
            FreeCADGui.Selection.removeSelectionGate()
            self._beobachter = None
        FreeCADGui.Selection.clearSelection()

    # --- Teil, Job, Rohteil ---------------------------------------------------------------

    def angeklickt(self, objekt, unterelement, punkt=None):
        """Eine angeklickte Fläche: ohne Job macht sie ihr Teil zum Teil des Jobs; mit Job nimmt
        sie die Fläche dazu oder heraus – wartet „Im Bild wählen …“ auf eine Eintauchstelle der
        Nut, ist der Punkt diese Stelle."""
        if self.geschlossen:
            return
        if self.nut.stelle_waehlt is not None and self.job is not None and punkt is not None:
            FreeCADGui.Selection.clearSelection()
            self.nut.stelle_angeklickt(punkt)
            return
        if self.job is None:
            wahl = gewaehlte_flaeche(self.doc)
            if wahl is not None:
                self._beginnen(wahl, angeklicktes_teil(self.doc))
            return
        weg = unterelement.split(".") if unterelement else []
        if weg and weg[-1].startswith("Edge"):
            teil, _flaeche = _entlang(self.doc, self.doc.getObject(objekt), ".".join(weg[:-1]))
            klon = vr.modell(self.job)
            if teil is None or vr.original(teil) is not vr.original(klon):
                return
            FreeCADGui.Selection.clearSelection()
            self.kante_umschalten(weg[-1])
            return
        teil, flaeche = _entlang(self.doc, self.doc.getObject(objekt), unterelement)
        klon = vr.modell(self.job)
        if teil is None or flaeche is None or vr.original(teil) is not vr.original(klon):
            return
        FreeCADGui.Selection.clearSelection()
        if self.knopf_unten_waehlen.isChecked() and not self._aufspannung_fest():
            self.knopf_unten_waehlen.setChecked(False)
            self.unten_waehlen(flaeche)  # „Fläche anklicken …“: die Fläche, die unten liegt
            return
        self.flaeche_umschalten(flaeche)

    # --- Wie das Teil auf dem Tisch liegt -------------------------------------------------

    def unten_waehlen(self, flaeche):
        """Macht die ebene Fläche `flaeche` („Face6“) zur Unterseite: Das Teil im Job dreht sich
        so, dass sie nach unten zeigt, Rohteil und Nullpunkt folgen. None: wie modelliert."""
        if self.job is None or self._aufspannung_fest():
            return
        if flaeche is not None and _aussennormale(self.teil.Shape, flaeche) is None:
            self.hinweis.setText(tr("ba.unten.nicht_eben", name=flaeche))
            return
        self.hinweis.setText("")
        self._unten = flaeche
        self._lage_geaendert()

    def x_drehen(self, viertel):
        """Dreht das Teil im Job um Z – X zeigt danach ein Viertel weiter (+1: gegen den
        Uhrzeigersinn, von oben gesehen)."""
        if self.job is None or self._aufspannung_fest():
            return
        self._viertel = (self._viertel + int(viertel)) % 4
        self._lage_geaendert()

    def aufspannung(self):
        """Die Drehung vom Teil, wie es modelliert ist, in den Job: die Unterseite nach −Z, dann
        um Z in Vierteln."""
        drehung = FreeCAD.Rotation()
        if self._unten is not None and self.teil is not None:
            normale = _aussennormale(self.teil.Shape, self._unten)
            if normale is not None:
                drehung = FreeCAD.Rotation(normale, FreeCAD.Vector(0, 0, -1))
        um_z = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 90.0 * self._viertel)
        return um_z.multiply(drehung)

    def _lage_geaendert(self):
        self._lage_zeigen()
        self._nullpunkt_setzen(self.job)
        if FreeCADGui.ActiveDocument is not None and FreeCADGui.ActiveDocument.ActiveView:
            FreeCADGui.SendMsgToActiveView("ViewFit")  # gedreht liegt das Teil woanders
        self._flaechen_zeigen()
        self._ziel_gemerkt = None  # gedreht kann der Kasten gleich bleiben, das Teil nicht
        self.vorschau_starten()

    def _lage_zeigen(self):
        """„Face6 liegt unten“ / „wie modelliert“, „um 90° gedreht“ – neben den Knöpfen."""
        if self._unten is None:
            self.unten_text.setText(tr("ba.unten.modell"))
        else:
            self.unten_text.setText(tr("ba.unten.flaeche", name=self._unten))
        self.knopf_unten_modell.setEnabled(self._unten is not None)
        if self._viertel == 0:
            self.x_text.setText(tr("ba.x.modell"))
        else:
            self.x_text.setText(tr("ba.x.gedreht", grad=90 * self._viertel))

    def _beginnen(self, wahl, angeklickt=None):
        """Das angeklickte Teil: Hat es schon einen Job, kommen die neuen Operationen dort
        hinein (job_dazu), sonst entsteht ein neuer (teil_waehlen)."""
        teil, flaeche = wahl
        job = None if self._neu else vorhandener_job(self.doc, teil, angeklickt)
        if job is not None:
            self.job_dazu(job, flaeche)
        else:
            self.teil_waehlen(teil, flaeche)

    def job_dazu(self, job, flaeche=None):
        """Ein weiterer Lauf am Teil (W-012 M2): die neuen Operationen in den Job, den es schon
        hat, hinter die vorhandenen – Maschine, Rohteil, Nullpunkt und Lage bleiben, wie sie
        dort stehen (Schritt 1 grau). „Neuer Job …“ legt stattdessen einen neuen an."""
        if self.job is not None or self.geschlossen:
            return
        self.job = job
        self._job_dazu = True
        self.teil = vr.original(vr.modell(job))
        self.teil_text.setText(self.teil.Label)
        # Hat der Job geschwenkte Ebenen (3+2), nur sein Teil und seine Bahnen im Bild.
        from .gui_schwenken import zeige_job

        self._aufspannung_vorher = zeige_job(job)
        self._aufspannung_zeigen()
        ops = [o for o in js.operationen(job) if getattr(o, "Active", True)]
        if not ops:
            text = tr("ba.dazu.keine", job=job.Label)
        elif len(ops) == 1:
            text = tr("ba.dazu.eine", job=job.Label, name=ops[0].Label)
        else:
            text = tr("ba.dazu.mehrere", job=job.Label, n=len(ops), name=ops[-1].Label)
        self.dazu_text.setText(text)
        self.dazu_zeile.setVisible(True)
        form = vr.modell(job).Shape
        if flaeche and any(b.s.passt(form, flaeche) for b in self.bloecke):
            self.gewaehlte = [flaeche]
        else:
            self.gewaehlte = []
        self.kanten = []
        FreeCADGui.Selection.clearSelection()
        self._bearbeitung_fuellen()
        self._flaechen_zeigen()
        self._auffrischen()
        self.seite_zeigen(self._seite)
        self.vorschau_starten()

    def neuer_job(self):
        """„Neuer Job …“: statt in den vorhandenen Job einen neuen anlegen – eine zweite
        Aufspannung. Dieses Fenster schließt, ein neues öffnet sich mit Teil und Flächen."""
        if not self._job_dazu or self.teil is None:
            return
        dokument, teil = self.doc, self.teil
        flaeche = self.gewaehlte[0] if self.gewaehlte else None
        self.reject()

        def oeffnen():
            FreeCADGui.Control.showDialog(BearbeitungPanel(dokument, (teil, flaeche), neu=True))

        QtCore.QTimer.singleShot(0, oeffnen)

    def _aufspannung_fest(self):
        """Stehen Maschine, Rohteil, Nullpunkt und Lage im Job schon fest – beim Ändern einer
        Operation und bei einem weiteren Lauf am selben Job (W-012 M2)?"""
        return self.zu_aendern is not None or self._job_dazu

    def teil_waehlen(self, teil, flaeche=None):
        """Das Teil für den Job – der Job mit dem Rohteil entsteht sofort (eine Transaktion,
        bis „Anlegen“ oder „Abbrechen“). `flaeche`: die angeklickte Fläche („Face6“) – ist sie
        eben nach oben oder eine Wand, ist sie gewählt, sonst die Oberseite."""
        if self.job is not None or teil is None or self.geschlossen:
            return
        self.teil = teil
        self.teil_text.setText(teil.Label)
        if self.wahl_rohteil.count():
            self._rohteil_liste_fuellen()  # das Teil selbst ist kein Rohteil
        try:
            self.job = _im_befehl(self._neuer_job)
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"Bearbeitung: {fehler}\n")
            self.hinweis.setText(tr("ba.fehler.anlegen", fehler=str(fehler)))
            self.teil = None
            return
        self._job_offen = True
        self._job_zeigen()
        self._maschine_gewaehlt()  # der neue Job bekommt die gewählte Maschine
        if self.nullpunkt() is not None or self._nullpunkt_versatz().Length > 0:
            self._nullpunkt_setzen(self.job)
        form = vr.modell(self.job).Shape
        if flaeche and any(b.s.passt(form, flaeche) for b in self.bloecke):
            self.gewaehlte = [flaeche]
        else:
            self.gewaehlte = []
        self.kanten = []
        FreeCADGui.Selection.clearSelection()
        self._bearbeitung_fuellen()
        self._flaechen_zeigen()
        self._auffrischen()
        self.seite_zeigen(self._seite)  # mit dem Job geht „Weiter“
        self.vorschau_starten()

    def _neuer_job(self):
        """Legt den Job an und öffnet dafür die Transaktion des Assistenten – nur in
        _im_befehl (wie gui_vierachs._neuer_job)."""
        import Path.Main.Job as PathJob

        self.doc.openTransaction(tr("ba.titel"))
        FreeCAD.setActiveDocument(self.doc.Name)
        job = PathJob.Create("Job", [self.teil])
        job.Label = tr("ba.job", teil=self.teil.Label)
        self._rohteil_setzen(job)
        spannung.setze(job, self._gespannt())
        self.doc.recompute()
        if _globale_transaktionen():
            FreeCAD.setActiveTransaction(tr("ba.titel"), True)
        return job

    # --- Maschine (W-011 S2) ------------------------------------------------------------------

    def _maschinen_fuellen(self, auswahl=None):
        """Die Maschinen aus der Liste („Maschinen …“) in die Wahl. Vorgewählt `auswahl` (eine
        Datei; "" heißt keine), ohne die des Jobs, sonst die zuletzt benutzte, sonst die
        erste. Ohne Maschine in der Liste steht „keine“ da – der Assistent rechnet dann mit
        einer 3-Achs-Fräse."""
        msp.aufraeumen()  # verschwundene Dateien aus dem temporären Ordner
        eintraege = msp.laden()
        gewollt = auswahl is not None
        if not gewollt:
            auswahl = rw.gemerkte_maschine(self.job)
        index = next(
            (i for i, e in enumerate(eintraege) if msp.gleiche_datei(e.datei, auswahl)), None
        )
        keine = not eintraege or (index is None and gewollt)
        self._maschinen_fuellt = True
        try:
            self.wahl_maschine.clear()
            if keine:
                self.wahl_maschine.addItem(tr("ba.maschine.keine"), "")
            for eintrag in eintraege:
                art = msp.art_text(eintrag)
                text = (
                    eintrag.name
                    if eintrag.name == art
                    else tr("ba.maschine.eintrag", name=eintrag.name, art=art)
                )
                if not eintrag.vorhanden:
                    text = tr("ba.maschine.fehlt", maschine=text)
                self.wahl_maschine.addItem(text, eintrag.datei)
            if index is not None:
                self.wahl_maschine.setCurrentIndex(index + int(keine))
            else:
                self.wahl_maschine.setCurrentIndex(0)
        finally:
            self._maschinen_fuellt = False
        self._maschine_gewaehlt()

    def _fuenfachs(self):
        """Ist eine 5-Achs-Maschine gewählt (für Anstellen und Flanke)?"""
        try:
            eintrag = self.maschine()
        except AttributeError:  # die Wahl der Maschine gibt es noch nicht
            return False
        return eintrag is not None and eintrag.vorhanden and eintrag.art == msp.FRAESE_5

    def maschine(self):
        """Der Eintrag der gewählten Maschine (maschinenspeicher.Eintrag) – oder None."""
        datei = self.wahl_maschine.currentData() or ""
        return msp.finde(msp.laden(), datei) if datei else None

    def magazin(self):
        """Das Magazin, das für die gewählte Maschine gilt (W-002 Stufe H2) – None ohne."""
        wahl = getattr(self, "wahl_maschine", None)  # die Wahl der Maschine gibt es noch nicht
        datei = (wahl.currentData() or "") if wahl is not None else ""
        if not datei or self.bibliothek is None:
            return None
        return mg.des_jobs(None, self.bibliothek, datei)

    def _maschine_gewaehlt(self):
        """Die Wahl gilt: am Job gemerkt (und als zuletzt benutzt), der Satz darunter, die
        graue Zeile in Schritt 2."""
        if getattr(self, "_maschinen_fuellt", False):
            return
        eintrag = self.maschine()
        stange = eintrag is not None and eintrag.vorhanden and eintrag.art in STANGE_ARTEN
        if eintrag is None:
            self.maschine_hinweis.setText(tr("ba.maschine.leer"))
            self.maschine_hinweis.setStyleSheet(f"color: {GRAU_TEXT};")
        elif not eintrag.vorhanden:
            self.maschine_hinweis.setText(tr("ba.maschine.nicht_gefunden"))
            self.maschine_hinweis.setStyleSheet(f"color: {ROT};")
        elif eintrag.art == msp.DREHMASCHINE:
            self.maschine_hinweis.setText(tr("ba.maschine.drehmaschine"))
            self.maschine_hinweis.setStyleSheet(f"color: {ROT};")
        elif stange:
            self.maschine_hinweis.setText(tr("ba.maschine.rundachse"))
            self.maschine_hinweis.setStyleSheet(f"color: {GRAU_TEXT};")
        else:
            self.maschine_hinweis.setText("")
        self.maschine_hinweis.setVisible(bool(self.maschine_hinweis.text()))
        self.maschine_knoepfe.setVisible(eintrag is not None and not eintrag.vorhanden)
        self.knopf_vierachs.setVisible(stange and not self._aufspannung_fest())
        if hasattr(self, "knopf_weiter"):
            self.seite_zeigen(self._seite)  # „Weiter“ geht auf der Drehmaschine nicht
        if eintrag is not None and self.job is not None and not self._aufspannung_fest():
            rw.merke_maschine(self.job, eintrag.datei)
        for block in getattr(self, "bloecke", ()):
            block.haken_pruefen()  # Anstellen geht nur an einer 5-Achs-Maschine
            if self.bibliothek is not None:  # das Magazin der Maschine (W-002 Stufe H2)
                block.fraeser_fuellen(self.bibliothek, self.werkstoff())
        if hasattr(self, "flanke") and self.job is not None and self.gewaehlte:
            self._flaechen_zeigen()  # die Flanke auch
            self.vorschau_starten()
        self._rohteil_kurz_zeigen()

    def nur_vierachs(self):
        """Ob die gewählte Maschine eine Drehmaschine ist: Dann ist das Rohteil eine Stange, und
        nur der 4-Achs-Assistent passt – „Weiter“ und „Anlegen“ gehen hier nicht."""
        eintrag = self.maschine() if hasattr(self, "wahl_maschine") else None
        return (
            eintrag is not None
            and eintrag.vorhanden
            and eintrag.art == msp.DREHMASCHINE
            and not self._aufspannung_fest()
        )

    def zum_vierachs(self):
        """Drehmaschine oder 4-Achs-Fräse: Dieser Assistent schließt (der Job geht zurück), der
        4-Achs-Assistent öffnet sich mit dem Teil, der angeklickten Fläche und der Maschine –
        ihre Datei ist dann offen, er wählt sie vor."""
        from . import gui_reichweite, gui_vierachs

        eintrag = self.maschine()
        if eintrag is None or not eintrag.vorhanden:
            return
        doc = self.doc
        wahl = self._wahl_anfang or ((self.teil, None) if self.teil is not None else None)
        self.reject()
        try:
            maschine = gui_reichweite.oeffne_datei(eintrag.datei)
        except Exception as fehler:  # nicht mehr lesbar: ohne Maschine weiter
            QtGui.QMessageBox.warning(
                FreeCADGui.getMainWindow(),
                tr("ba.titel"),
                tr("ms.datei_fehler", datei=eintrag.datei, fehler=fehler),
            )
            maschine = None
        gui_reichweite.zeige_dokument(doc)
        FreeCAD.setActiveDocument(doc.Name)
        QtCore.QTimer.singleShot(
            0,
            lambda: FreeCADGui.Control.showDialog(
                gui_vierachs.VierachsPanel(doc, wahl, maschine=maschine)
            ),
        )

    def maschine_suchen(self):
        """„Suchen …“: die Datei der gewählten Maschine liegt nicht mehr dort – die neue wählen,
        der Eintrag zieht mit (wie in „Maschinen …“)."""
        from . import gui_maschinen

        eintrag = self.maschine()
        if eintrag is None:
            return
        datei = gui_maschinen.datei_waehlen(self.form, os.path.dirname(eintrag.datei))
        if not datei:
            return
        try:
            gefunden = gui_maschinen.einlesen(datei)
        except Exception as fehler:  # keine FreeCAD-Datei, kaputt: sagen statt still scheitern
            QtGui.QMessageBox.warning(
                self.form, tr("ba.titel"), tr("ms.datei_fehler", datei=datei, fehler=fehler)
            )
            return
        if gefunden and not msp.gleiche_datei(datei, eintrag.datei):
            msp.entfernen(eintrag.datei)
        self._maschinen_fuellen(gefunden[0].datei if gefunden else eintrag.datei)

    def maschine_entfernen(self):
        """„Aus der Liste nehmen“: der Eintrag ohne Datei verschwindet; eine Datei bleibt."""
        eintrag = self.maschine()
        if eintrag is None:
            return
        msp.entfernen(eintrag.datei)
        self._maschinen_fuellen("")

    def maschinen_oeffnen(self):
        """„Maschinen …“: die Liste zum Hinzufügen und Bauen; danach ist die Wahl neu gefüllt."""
        from . import gui_maschinen

        dialog = gui_maschinen.oeffne()
        dialog.finished.connect(
            lambda _ergebnis: (
                self._maschinen_fuellen(self.wahl_maschine.currentData() or None)
                if not self.geschlossen
                else None
            )
        )

    def _rohteil_liste_fuellen(self):
        """Die Körper, die das Rohteil sein können – der gewählte bleibt, wenn es ihn noch gibt."""
        vorher_name = self.wahl_rohteil.currentData()
        vorher, self._fuellt = self._fuellt, True
        try:
            self.wahl_rohteil.clear()
            for koerper in rohteil_kandidaten(self.doc, self.teil):
                self.wahl_rohteil.addItem(koerper.Label, koerper.Name)
            index = self.wahl_rohteil.findData(vorher_name) if vorher_name else -1
            self.wahl_rohteil.setCurrentIndex(max(index, 0))
        finally:
            self._fuellt = vorher

    def _rohteil_art_geaendert(self):
        """Quader oder Körper aus dem Dokument: die Felder dazu, die Liste der Körper."""
        teil = self.knopf_rohteil_teil.isChecked()
        if teil and self.wahl_rohteil.count() == 0:
            self._rohteil_liste_fuellen()
        if teil and self.wahl_rohteil.count() == 0:
            self.knopf_rohteil_teil.blockSignals(True)
            self.knopf_rohteil_quader.setChecked(True)
            self.knopf_rohteil_teil.blockSignals(False)
            self.rohteil_erklaerung.setText(tr("ba.rohteil.keine_teile"))
            return
        self.rohteil_erklaerung.setText(tr("ba.rohteil.teil.text" if teil else "ba.rohteil.text"))
        self.rohteil_koerper.setVisible(teil)
        self.rohteilfelder.setVisible(not teil)
        self._rohteil_geaendert()

    def rohteil_koerper_gewaehlt(self):
        """Der Körper aus dem Dokument, der das Rohteil ist – None beim Quader mit Aufmaß."""
        if not self.knopf_rohteil_teil.isChecked():
            return None
        name = self.wahl_rohteil.currentData()
        return self.doc.getObject(name) if name else None

    def _rohteil_original_zeigen(self, koerper):
        """Wie beim Teil: Ist ein Körper das Rohteil, zeigt der Job seinen Klon, das Original
        verschwindet – ein anderer Körper oder der Quader holt das vorige zurück."""
        if self._rohteil_sichtbar_vorher is not None:
            vorher, sichtbar = self._rohteil_sichtbar_vorher
            if vorher is koerper:
                return
            self._rohteil_sichtbar_vorher = None
            with contextlib.suppress(ReferenceError, RuntimeError, AttributeError):
                vorher.ViewObject.Visibility = sichtbar
        if koerper is not None and getattr(koerper, "ViewObject", None) is not None:
            self._rohteil_sichtbar_vorher = (koerper, koerper.ViewObject.Visibility)
            koerper.ViewObject.Visibility = False

    def _rohteil_ersetzen(self, job, neu):
        """Setzt `neu` als Rohteil des Jobs und löscht das alte (wie FreeCADs Job-Fenster)."""
        alt = getattr(job, "Stock", None)
        job.Stock = neu
        if alt is not None and alt is not neu:
            self.doc.removeObject(alt.Name)

    def _rohteil_setzen(self, job):
        """Das Rohteil des Jobs: der gewählte Körper aus dem Dokument (ein Klon von ihm, wie bei
        FreeCADs „Rohteil aus vorhandenem Körper“) oder ein Quader um das Teil mit dem Aufmaß aus
        den Feldern."""
        import Path.Main.Job as PathJob
        import Path.Main.Stock as PathStock

        koerper = self.rohteil_koerper_gewaehlt()
        rohteil = getattr(job, "Stock", None)
        self._rohteil_original_zeigen(koerper)
        if koerper is not None:
            if koerper not in (getattr(rohteil, "Objects", None) or []):
                FreeCAD.setActiveDocument(self.doc.Name)
                klon = PathJob.createResourceClone(job, koerper, "Stock", "Stock")
                PathStock.SetupStockObject(klon, PathStock.StockType.Unknown)
                klon.Proxy.execute(klon)
                if klon.ViewObject is not None:
                    klon.ViewObject.Visibility = True
                self._rohteil_ersetzen(job, klon)
            return
        if rohteil is None or not hasattr(rohteil, "ExtZpos"):
            FreeCAD.setActiveDocument(self.doc.Name)
            self._rohteil_ersetzen(job, PathStock.CreateFromBase(job))
            rohteil = job.Stock
        werte = {feld: self._rohteil_wert(feld) for feld in ROHTEIL_FELDER}
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

    def _rohteil_wert(self, feld):
        """Wert eines Rohteil-Felds (mm); leer oder ungültig gilt 1 mm."""
        text = self.felder_rohteil[feld].text()
        try:
            return groesse_lesen(text, einheiten.LAENGE) if text.strip() else AUFMASS_ROHTEIL
        except ValueError:
            return AUFMASS_ROHTEIL

    def _rohteil_kurz_zeigen(self):
        """„Aufmaß 1 mm rundum · Nullpunkt: wie im Modell“ – oben in Schritt 2."""
        if not hasattr(self, "rohteil_kurz") or not hasattr(self, "wahl_nullpunkt"):
            return
        mm = einheiten.einheit(einheiten.LAENGE)
        werte = [self._rohteil_wert(feld) for feld in ROHTEIL_FELDER]
        zahlen = [groesse_zeigen(w, einheiten.LAENGE) or "0" for w in werte]
        koerper = self.rohteil_koerper_gewaehlt() if hasattr(self, "knopf_rohteil_teil") else None
        if koerper is not None:
            aufmass = tr("ba.rohteil.kurz_teil", name=koerper.Label)
        elif len(set(zahlen)) == 1:
            aufmass = tr("ba.rohteil.kurz_rundum", wert=f"{zahlen[0]} {mm}")
        else:
            aufmass = tr("ba.rohteil.kurz", oben=zahlen[0], seite=zahlen[1], unten=zahlen[2], mm=mm)
        verschoben = any(self.felder_nullpunkt[f].text().strip() for f in VERSATZ_FELDER)
        wahl = self.wahl_nullpunkt.currentText()
        if verschoben:
            nullpunkt = tr("ba.nullpunkt.kurz_verschoben", wahl=wahl)
        else:
            nullpunkt = tr("ba.nullpunkt.kurz", wahl=wahl)
        teile = [aufmass, nullpunkt]
        if self._gespannt() > 0:
            wert = groesse_zeigen(self._gespannt(), einheiten.LAENGE)
            teile.append(tr("ba.gespannt.kurz", wert=f"{wert} {mm}"))
        eintrag = self.maschine() if hasattr(self, "wahl_maschine") else None
        if eintrag is not None:
            teile.insert(0, tr("ba.maschine.kurz", name=eintrag.name))
        self.rohteil_kurz.setText(" · ".join(teile))

    def _gespannt(self):
        """Von unten gespannt (mm) – leer oder ungültig 0."""
        text = self.felder_spannung["gespannt"].text() if hasattr(self, "felder_spannung") else ""
        try:
            return max(groesse_lesen(text, einheiten.LAENGE), 0.0) if text.strip() else 0.0
        except ValueError:
            return 0.0

    def _spannung_geaendert(self):
        self._rohteil_kurz_zeigen()
        if not self._fuellt and self.job is not None and not self.geschlossen:
            spannung.setze(rw.grundjob_von(self.job), self._gespannt())

    def _rohteil_geaendert(self):
        self._rohteil_kurz_zeigen()
        if not self._fuellt and self.job is not None and not self._aufspannung_fest():
            self._rohteil_uhr.start()

    def _rohteil_anwenden(self):
        if self.job is None or self._aufspannung_fest() or self.geschlossen:
            return
        self._rohteil_setzen(self.job)
        self.doc.recompute()
        self._nullpunkt_setzen(self.job)  # die Ecken des Rohteils sind gewandert
        # Mehr oder weniger über den Flächen: Planen oder Schruppen (P-2026-10-02-54).
        self._planeinsatz_waehlen(vr.modell(self.job).Shape)
        self.vorschau_starten()

    # --- Nullpunkt ------------------------------------------------------------------------

    def nullpunkt(self):
        """(sx, sy, sz) des gewählten Punkts am Rohteil-Quader – None: wie im Modell."""
        nummer = self.wahl_nullpunkt.currentData()
        return self._nullpunkte[nummer - 1][1] if nummer else None

    def _nullpunkt_versatz(self):
        """Der Versatz vom gewählten Punkt (mm) – leer oder ungültig 0."""
        werte = []
        for feld in VERSATZ_FELDER:
            text = self.felder_nullpunkt[feld].text()
            try:
                werte.append(groesse_lesen(text, einheiten.LAENGE) if text.strip() else 0.0)
            except ValueError:
                werte.append(0.0)
        return FreeCAD.Vector(*werte)

    def _nullpunkt_geaendert(self):
        self._rohteil_kurz_zeigen()
        if not self._fuellt and self.job is not None and not self._aufspannung_fest():
            self._nullpunkt_uhr.start()

    def _nullpunkt_anwenden(self):
        if self.job is None or self._aufspannung_fest() or self.geschlossen:
            return
        self._nullpunkt_setzen(self.job)
        self.vorschau_starten()

    def _nullpunkt_setzen(self, job):
        """Rückt das Teil im Job (den Klon) mit dem Rohteil so, dass der gewählte Punkt des
        Rohteil-Quaders, um den Versatz verschoben, im Ursprung liegt – „wie im Modell“ legt
        den Klon wieder auf das Original. Der Quader kommt aus dem Original und den
        Aufmaßen der Felder; das Rohteil aus dem Modell merkt sich seine Lage nur beim
        Anlegen (Path.Main.Stock), darum wird es mitgeschoben."""
        klon = vr.modell(job)
        teil = vr.original(klon)
        lage = self.nullpunkt()
        punkt = FreeCAD.Vector()
        drehung = FreeCAD.Placement(FreeCAD.Vector(), self.aufspannung())
        koerper = self.rohteil_koerper_gewaehlt()
        if lage is not None:
            # Die Ecken des Rohteils: der Körper aus dem Dokument – oder Teil plus Aufmaß.
            gedreht = (koerper if koerper is not None else teil).Shape.copy()
            gedreht.Placement = drehung.multiply(gedreht.Placement)
            bb = gedreht.BoundBox
            werte = {feld: self._rohteil_wert(feld) for feld in ROHTEIL_FELDER}
            if koerper is not None:
                werte = dict.fromkeys(ROHTEIL_FELDER, 0.0)
            unten = (bb.XMin - werte["seite"], bb.YMin - werte["seite"], bb.ZMin - werte["unten"])
            oben = (bb.XMax + werte["seite"], bb.YMax + werte["seite"], bb.ZMax + werte["oben"])
            punkt = FreeCAD.Vector(
                *(
                    (u + o) / 2 if s == 0 else (o if s > 0 else u)
                    for s, u, o in zip(lage, unten, oben, strict=True)
                )
            )
            punkt = punkt + self._nullpunkt_versatz()
        neu = (
            FreeCAD.Placement(punkt * -1.0, FreeCAD.Rotation())
            .multiply(drehung)
            .multiply(teil.Placement)
        )
        rohteil = getattr(job, "Stock", None)
        if koerper is not None and koerper in (getattr(rohteil, "Objects", None) or []):
            # Der Klon des Körpers wandert wie das Teil: dieselbe Verschiebung und Drehung.
            neu_rohteil = neu.multiply(teil.Placement.inverse()).multiply(koerper.Placement)
            alt_rohteil = rohteil.Placement
            if (alt_rohteil.Base - neu_rohteil.Base).Length > 1e-9 or not (
                alt_rohteil.Rotation.isSame(neu_rohteil.Rotation, 1e-9)
            ):
                rohteil.Placement = neu_rohteil
                self.doc.recompute()
        alt = klon.Placement
        if (alt.Base - neu.Base).Length < 1e-9 and alt.Rotation.isSame(neu.Rotation, 1e-9):
            return
        klon.Placement = neu
        self.doc.recompute()
        if rohteil is not None and hasattr(rohteil, "ExtZpos"):
            kasten = klon.Shape.BoundBox
            rohteil.Placement = FreeCAD.Placement(
                FreeCAD.Vector(kasten.XMin, kasten.YMin, kasten.ZMin), FreeCAD.Rotation()
            )
            self.doc.recompute()

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
        self._rohteil_original_zeigen(None)
        if self._sichtbar_vorher is None:
            return
        teil, sichtbar = self._sichtbar_vorher
        self._sichtbar_vorher = None
        try:
            if teil.ViewObject is not None:
                teil.ViewObject.Visibility = sichtbar
        except (ReferenceError, RuntimeError):
            pass

    def _aufspannung_zeigen(self):
        """Maschine, Rohteil, Nullpunkt und Lage, wie sie im Job stehen – nur zum Lesen: beim
        Ändern einer Operation und bei einem weiteren Lauf am selben Job (W-012 M2)."""
        rohteil = getattr(self.job, "Stock", None)
        self._fuellt = True
        try:
            original = (getattr(rohteil, "Objects", None) or [None])[0]
            if original is not None:  # ein Körper aus dem Dokument (W-011 S4)
                self.wahl_rohteil.addItem(original.Label, original.Name)
                self.knopf_rohteil_teil.setChecked(True)
                self.rohteil_koerper.setVisible(True)
                self.rohteilfelder.setVisible(False)
            for knopf_art in (self.knopf_rohteil_quader, self.knopf_rohteil_teil):
                knopf_art.setEnabled(False)
            self.wahl_rohteil.setEnabled(False)
            if rohteil is not None and hasattr(rohteil, "ExtZpos"):
                for feld, name in (("oben", "ExtZpos"), ("seite", "ExtXpos"), ("unten", "ExtZneg")):
                    wert = _mm(getattr(rohteil, name))
                    self.felder_rohteil[feld].setText(groesse_zeigen(wert, einheiten.LAENGE) or "0")
            tiefe = spannung.gespannt(self.job)
            self.felder_spannung["gespannt"].setText(
                groesse_zeigen(tiefe, einheiten.LAENGE) if tiefe > 0 else ""
            )
        finally:
            self._fuellt = False
        self.rohteilfelder.setEnabled(False)
        # Die des Jobs – sie bleibt, wie sie im Job steht (ohne: „keine“).
        self._maschinen_fuellen(getattr(self.job, rw.EIGENSCHAFT_MASCHINE, ""))
        self.wahl_maschine.setEnabled(False)
        self.knopf_maschinen.setEnabled(False)
        for widget in (self.nullpunkt_titel, self.nullpunkt_text, self.nullpunktfelder):
            widget.setVisible(False)  # der Nullpunkt bleibt, wie er im Job steht
        # Wie das Teil liegt, bleibt ebenso.
        self.unten_text.setText(tr("ba.lage.job"))
        self.x_text.setText(tr("ba.lage.job"))
        for widget in (
            self.knopf_unten_waehlen,
            self.knopf_unten_modell,
            self.knopf_x_links,
            self.knopf_x_rechts,
        ):
            widget.setEnabled(False)

    def _zum_aendern(self):
        """Mit den Werten der Operation: Teil und Rohteil wie im Job (nicht änderbar), Flächen,
        ihr Block mit Fräser, Einsatz, Werten – die anderen Blöcke bleiben weg; „Übernehmen“
        statt „Anlegen“."""
        op = self.zu_aendern
        self.job = job_von(op)
        if self.job is None:
            return
        block = next((b for b in self.bloecke if b.s.ist(op)), None)
        if block is None:
            return
        self.block_zu_aendern = block
        block.tc_vorher = op.ToolController
        self.teil = vr.original(vr.modell(self.job))
        self.teil_text.setText(self.teil.Label)
        self.anleitung.setText(tr("ba.aendern.text", name=op.Label))
        self._aufspannung_zeigen()
        self._fuellt = True
        try:
            for anderer in self.bloecke:
                if anderer is not block:
                    anderer.widget.setVisible(False)
                    anderer.haken.setChecked(False)
            block.haken.setChecked(True)
            block.haken.setEnabled(False)
            block.von_hand = True
        finally:
            self._fuellt = False
        for b in self.bloecke:
            b.zustand_zeigen()
        namen = list(getattr(op, "Flaechen", ()) or ())
        self.gewaehlte = [n for n in namen if not n.startswith("Edge")]
        self.kanten = [n for n in namen if n.startswith("Edge")]
        self._bearbeitung_fuellen()
        self._fuellt = True
        try:
            werte_der_op = dict(block.s.werte_von(op))
            if "aufloesung" in block.felder:
                werte_der_op["aufloesung"] = au.wert(op, 0.0)
            for feld, wert in werte_der_op.items():
                if feld == "eintauchen_bei":  # die Eintauchstellen der Nut (W-012 E1)
                    block.eintauchen = dict(wert)
                    continue
                if feld in block.haken_felder:
                    block.haken_felder[feld].setChecked(bool(wert))
                    continue
                wert = float(wert)
                if abs(wert - block.vorschlag(feld)) > 1e-6:
                    block.felder[feld].setText(groesse_zeigen(wert, einheiten.LAENGE) or "0")
            if block is self.raeumen:
                block.raeumwahl_von(op)
        finally:
            self._fuellt = False
        self._flaechen_zeigen()
        self._auffrischen()
        self.vorschau_starten()

    # --- Flächen --------------------------------------------------------------------------

    def kante_umschalten(self, name):
        """Nimmt die Kante `name` („Edge12“) dazu – oder heraus, wenn sie schon gewählt ist. Mit
        Kanten arbeitet nur „Entgraten 3D“."""
        if not name or self.job is None:
            return
        if name in self.kanten:
            self.kanten.remove(name)
        else:
            self.kanten.append(name)
        self._flaechen_zeigen()
        self.vorschau_starten()

    def _wahl(self, block):
        """Was der Block bekommt: die gewählten Flächen – „Entgraten 3D“ dazu die Kanten."""
        if getattr(block.s, "nimmt_kanten", False):
            return list(self.gewaehlte) + list(self.kanten)
        return self.gewaehlte

    def flaeche_umschalten(self, name):
        """Nimmt die Fläche `name` („Face6“) dazu – oder heraus, wenn sie schon gewählt ist; eine
        Kante („Edge12“) wie kante_umschalten."""
        if name and str(name).startswith("Edge"):
            self.kante_umschalten(name)
            return
        if not name or self.job is None:
            return
        if name in self.gewaehlte:
            self.gewaehlte.remove(name)
        else:
            self.gewaehlte.append(name)
        self._flaechen_zeigen()
        self.vorschau_starten()

    def oberseite_waehlen(self):
        if self.job is None:
            return
        self.gewaehlte = hf.oberseite(vr.modell(self.job).Shape)
        self._flaechen_zeigen()
        self.vorschau_starten()

    def flaechen_leeren(self):
        self.gewaehlte = []
        self.kanten = []
        self._flaechen_zeigen()
        self.vorschau_starten()

    def flaechen(self):
        """Die gewählten Flächen („Face6“ …) – leer: die Oberseite."""
        return list(self.gewaehlte)

    def _flaechen_zeigen(self):
        """Die Liste der gewählten Flächen, der Satz darunter, die Farben am Teil – und die
        Haken der Blöcke, wie die Wahl sie nahelegt."""
        self.flaechen_liste.clear()
        self.flaechen_liste.setVisible(bool(self.gewaehlte or self.kanten))
        self.schwenken_zeile.hide()
        if self.job is None:
            self.flaechen_text.setText("")
            return
        form = vr.modell(self.job).Shape
        farben = {}
        for name in self.gewaehlte:
            nummer = int(name[4:]) - 1 if name.startswith("Face") and name[4:].isdigit() else -1
            if nummer < 0 or nummer >= len(form.Faces):
                text, farbe = tr("ba.flaeche.fehlt", name=name), ROT
            elif self.nut.s.passt(form, name):
                n = nb.nuten(form, [name])[0]
                breite = groesse_zeigen(2 * n.radius, einheiten.LAENGE) or "0"
                laenge = groesse_zeigen(n.gesamtlaenge, einheiten.LAENGE) or "0"
                if n.offen:
                    z = groesse_zeigen(n.z_unten, einheiten.LAENGE) or "0"
                    text = tr("ba.flaeche.nut_offen", name=name, breite=breite, laenge=laenge, z=z)
                elif n.durch:
                    text = tr("ba.flaeche.nut_durch", name=name, breite=breite, laenge=laenge)
                else:
                    z = groesse_zeigen(n.z_unten, einheiten.LAENGE) or "0"
                    text = tr("ba.flaeche.nut_grund", name=name, breite=breite, laenge=laenge, z=z)
                farbe = GRUEN
            elif self.plan.s.passt(form, name):
                z = groesse_zeigen(hf.ebenen_oben(form, [name])[0].z, einheiten.LAENGE) or "0"
                text, farbe = tr("ba.flaeche.eben", name=name, z=z), GRUEN
            elif self.bohrung.s.passt(form, name):
                b = bb.bohrungen(form, [name])[0]
                d = groesse_zeigen(2 * b.radius, einheiten.LAENGE) or "0"
                if b.durch:
                    text = tr("ba.flaeche.bohrung_durch", name=name, d=d)
                elif b.spitze > 0:
                    z = groesse_zeigen(b.z_unten, einheiten.LAENGE) or "0"
                    text = tr(
                        "ba.flaeche.bohrung_spitze", name=name, d=d, z=z, winkel=f"{b.spitze:.0f}"
                    )
                else:
                    z = groesse_zeigen(b.z_unten, einheiten.LAENGE) or "0"
                    text = tr("ba.flaeche.bohrung_sack", name=name, d=d, z=z)
                farbe = GRUEN
            elif self.kontur.s.passt(form, name):
                z = groesse_zeigen(kb.waende(form, [name])[0].z_unten, einheiten.LAENGE) or "0"
                text, farbe = tr("ba.flaeche.wand", name=name, z=z), GRUEN
            elif self.senken.s.passt(form, name):
                senkung = sk.senkungen(form, [name])[0]
                d = groesse_zeigen(senkung.durchmesser, einheiten.LAENGE) or "0"
                winkel = f"{round(senkung.winkel, 1):g}"
                text, farbe = tr("ba.flaeche.senkung", name=name, d=d, winkel=winkel), GRUEN
            elif self.flanke.s.passt(form, name) and self._fuenfachs():
                z = groesse_zeigen(form.Faces[nummer].BoundBox.ZMin, einheiten.LAENGE) or "0"
                text, farbe = tr("ba.flaeche.flanke", name=name, z=z), GRUEN
            elif self.schlichten3d.s.passt(form, name):
                z = groesse_zeigen(form.Faces[nummer].BoundBox.ZMin, einheiten.LAENGE) or "0"
                text, farbe = tr("ba.flaeche.freiform", name=name, z=z), GRUEN
            elif eb.ist_fase(form, name):
                text, farbe = tr("ba.flaeche.fase", name=name), GRUEN
            elif _schraeg(form, name) is not None:
                winkel = f"{_schraeg(form, name):.0f}"
                text, farbe = tr("ba.flaeche.schraeg", name=name, winkel=winkel), ROT
            else:
                text, farbe = tr("ba.flaeche.nichts", name=name), ROT
            eintrag = QtGui.QListWidgetItem(dezimal(text))
            eintrag.setData(QtCore.Qt.UserRole, name)
            eintrag.setForeground(QtGui.QColor(farbe))
            self.flaechen_liste.addItem(eintrag)
            if nummer >= 0:
                farben[nummer] = farbe
        kanten_farben = {}
        for name in self.kanten:
            nummer = int(name[4:]) - 1 if name[4:].isdigit() else -1
            if 0 <= nummer < len(form.Edges) and self.entgraten3d.s.passt(form, name):
                laenge = groesse_zeigen(form.Edges[nummer].Length, einheiten.LAENGE) or "0"
                text, farbe = tr("ba.kante.fase", name=name, laenge=laenge), GRUEN
            else:
                text, farbe = tr("ba.kante.nichts", name=name), ROT
            eintrag = QtGui.QListWidgetItem(dezimal(text))
            eintrag.setData(QtCore.Qt.UserRole, name)
            eintrag.setForeground(QtGui.QColor(farbe))
            self.flaechen_liste.addItem(eintrag)
            if nummer >= 0:
                kanten_farben[nummer] = farbe
        # Die Liste so hoch wie ihre Einträge – höchstens fünf, dann rollt sie.
        zeile = max(self.flaechen_liste.sizeHintForRow(0), 1)
        rand = 2 * self.flaechen_liste.frameWidth() + 4
        self.flaechen_liste.setFixedHeight(
            min(5, max(1, self.flaechen_liste.count())) * zeile + rand
        )
        if not self.gewaehlte and self.kanten:
            self.flaechen_text.setText(tr("ba.flaechen.nur_kanten"))
        elif not self.gewaehlte:
            namen = ", ".join(hf.oberseite(form)) or "–"
            self.flaechen_text.setText(tr("ba.flaechen.oberseite", namen=namen))
        else:
            self.flaechen_text.setText(tr("ba.flaechen.nur"))
        self._schwenken_zeigen(form)
        self._farben_zeigen(farben, kanten_farben)
        self._haken_vorschlagen(form)

    def _schwenken_zeigen(self, form):
        """Ist eine gewählte Fläche schräg, die Zeile „geschwenkt fräsen“ mit dem Knopf – auch
        an einem neuen Job: Der Knopf legt ihn dann ohne Operationen an (P-2026-10-10-40)."""
        schraege = [n for n in self.gewaehlte if _schraeg(form, n) is not None]
        if self._fuenfachs():
            # Schräge Wände aus Geraden fräst die Flanke (5 Achsen simultan) ohne Schwenken.
            schraege = [n for n in schraege if not self.flanke.s.passt(form, n)]
        if not schraege:
            return
        name = schraege[0]
        winkel = f"{_schraeg(form, name):.0f}"
        self.schwenken_text.setText(tr("ba.schwenken.text", name=name, winkel=winkel))
        self.schwenken_knopf.show()
        self.schwenken_zeile.show()

    def ebene_schwenken(self):
        """„Ebene schwenken (3+2) …“: Der Assistent schließt, ohne Operationen anzulegen, das
        Fenster dafür öffnet mit der ersten schrägen Fläche – im Grundjob dieses Jobs. Ist der
        Job neu, bleibt er stehen, ohne Operationen: Vorher musste „Anlegen“ erst etwas anlegen,
        das keiner wollte (Manuel, 2026-10-10, an einer Bohrung in einer 41°-Schräge: „Ich will
        nur dass Loch da fräsen“)."""
        if self.job is None:
            return
        form = vr.modell(self.job).Shape
        schraege = [n for n in self.gewaehlte if _schraeg(form, n) is not None]
        if not schraege:
            return
        grundjob, flaeche = rw.grundjob_von(self.job), schraege[0]
        if self._job_offen:
            self._job_ohne_operationen_behalten()
        else:
            self.reject()

        def oeffnen():
            from .gui_schwenken import SchwenkenPanel

            FreeCADGui.Control.showDialog(SchwenkenPanel(grundjob, flaeche))

        QtCore.QTimer.singleShot(0, oeffnen)

    def _job_ohne_operationen_behalten(self):
        """Schließt den Assistenten und behält den neuen Job – Teil, Maschine, Rohteil und
        Nullpunkt wie bei „Anlegen“, ein Schritt Rückgängig –, nur ohne Operationen."""
        if self._rohteil_uhr.isActive():
            self._rohteil_uhr.stop()
            self._rohteil_anwenden()
        if self._nullpunkt_uhr.isActive():
            self._nullpunkt_uhr.stop()
            self._nullpunkt_anwenden()
        self.doc.commitTransaction()
        self._job_offen = False
        self._vor_dem_schliessen()
        if not self._aufspannung_fest():
            nullpunkt_vorgeben(self.nullpunkt())
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()

    def _haken_vorschlagen(self, form):
        """Je Block: möglich mit dieser Wahl? Dann der Haken, wie die Wahl ihn nahelegt –
        solange ihn niemand von Hand gesetzt hat."""
        if self.zu_aendern is not None:
            return
        self._reibahle_waehlen(form)
        gerieben = self._gerieben(form)
        self._bohrer_waehlen(form, gerieben)
        self._gewindebohrer_waehlen(form)
        self._gewindefraeser_waehlen(form)
        self._senker_waehlen(form)
        self._entgratfraeser_waehlen(form)
        self._nutfraeser_waehlen(form)
        self._planeinsatz_waehlen(form)
        self._fuellt = True
        try:
            for block in self.bloecke:
                moeglich = block.s.moeglich(form, self._wahl(block))
                grund = None
                if block is self.bohren:
                    moeglich = moeglich and self._bohrer_da(form, gerieben)
                if block is self.reiben:
                    moeglich = moeglich and self._reibahle_da(form)
                if gerieben and block in (self.bohrung, self.kontur) and moeglich:
                    # Geriebene Bohrungen bohrt der Bohrer kleiner vor – gefräst wären sie auf
                    # Maß, die Reibahle hätte nichts zu tun.
                    geriebene = set(self.reiben.s.flaechen_fuer(form, self.gewaehlte))
                    eigene = set(block.s.flaechen_fuer(form, self.gewaehlte))
                    if eigene <= geriebene:
                        moeglich, grund = False, tr("ba.bohrung.gerieben")
                if block is self.gewinde:
                    moeglich = moeglich and self._gewindebohrer_da(form)
                if block is self.gewindefraesen:
                    moeglich = moeglich and self._gewindefraeser_da(form)
                if block in (self.entgraten, self.entgraten3d, self.zentrieren):
                    moeglich = moeglich and bool(block._fraeser)
                if block is self.senken:
                    moeglich = moeglich and self._senker_da(form)
                if block is self.schlichten_danach:
                    # Mit dem Räumen (es steht davor in der Liste) – ein Haken von Hand bleibt.
                    moeglich = self.raeumen.aktiv()
                if block is self.flanke and moeglich and not self._fuenfachs():
                    moeglich, grund = False, tr("ba.fl.ohne_maschine")
                block.moeglich = moeglich
                block.haken.setEnabled(moeglich)
                block.erklaerung.setText(
                    block.s.text() if moeglich else grund or block.s.unmoeglich_text()
                )
                if not moeglich:
                    block.haken.setChecked(False)
                elif not block.von_hand:
                    vorschlag = block.s.vorgeschlagen(form, self._wahl(block))
                    if block is self.bohrung and self._von_raeumen_geraeumt(form):
                        vorschlag = False  # Räumen + Kontur ist dort die Folge
                    if self.kanten and not self.gewaehlte and block is not self.entgraten3d:
                        vorschlag = False  # nur Kanten gewählt: die sollen eine Fase bekommen
                    block.haken.setChecked(vorschlag)
                block.zustand_zeigen()
        finally:
            self._fuellt = False
        self._restfraeser_waehlen()
        self._rest_vorschlagen(form)
        self._restschlichtfraeser_waehlen()
        self._bloecke_ordnen()

    def _bloecke_ordnen(self):
        """Die Blöcke, die zur Wahl passen, oben – in ihrer Reihenfolge –, darunter unter einer
        Zeile mit ihrer Zahl, was (noch) nicht passt: eingeklappt, bis man darauf klickt, dann je
        Strategie der Titel und der Satz, was man anklicken muss. Passt nichts, steht alles da."""
        passend = [b.widget for b in self.bloecke if b.moeglich]
        andere = [b.widget for b in self.bloecke if not b.moeglich]
        reihe = passend + [self.passt_nicht] + andere
        if reihe != self._reihe:
            for widget in self._reihe:
                self._block_aufbau.removeWidget(widget)
            for i, widget in enumerate(reihe):
                self._block_aufbau.insertWidget(self._block_anfang + i, widget)
            self._reihe = reihe
        self.passt_nicht.setVisible(bool(andere) and bool(passend))
        self.nichts_angehakt.setVisible(not self.aktive_bloecke())
        self.passt_nicht_knopf.setText(tr("ba.passt_nicht", anzahl=len(andere)))
        offen = self.passt_nicht_knopf.isChecked() or not passend
        for widget in passend:
            widget.setVisible(True)
        for widget in andere:
            widget.setVisible(offen)

    def _passt_nicht_aufklappen(self, offen):
        """Klappt die Liste auf oder zu, was nicht zur Wahl passt."""
        self.passt_nicht_knopf.setArrowType(QtCore.Qt.DownArrow if offen else QtCore.Qt.RightArrow)
        self.passt_nicht_kurz.setText(
            tr("ba.passt_nicht.offen") if offen else tr("ba.passt_nicht.zu")
        )
        self._bloecke_ordnen()

    def haken_geklickt(self, block):
        if self._fuellt:
            return
        block.von_hand = True
        block.zustand_zeigen()
        self.nichts_angehakt.setVisible(not self.aktive_bloecke())
        if block is self.reiben and self.job is not None:
            # Gerieben: kleiner vorbohren, Bohrung fräsen und Kontur treten dort nicht an.
            self._haken_vorschlagen(vr.modell(self.job).Shape)
        # Gewinde bohren oder fräsen – beides in dieselben Bohrungen schnitte zwei Gänge.
        paar = {self.gewinde: self.gewindefraesen, self.gewindefraesen: self.gewinde}
        anderer = paar.get(block)
        if anderer is not None and block.aktiv() and anderer.aktiv():
            self._fuellt = True
            try:
                anderer.haken.setChecked(False)
                anderer.von_hand = True
                anderer.zustand_zeigen()
            finally:
                self._fuellt = False
        self.vorschau_starten()

    def _farben_zeigen(self, farben, kanten=None):
        """Färbt die Flächen (und die angeklickten Kanten) des Teils im Job (wie
        gui_vierachs._farben_zeigen) – nur die Anzeige; _farben_zurueck() stellt sie wieder her."""
        if (not farben and not kanten) or self.job is None:
            self._farben_zurueck()
            return
        klon = vr.modell(self.job)
        ansicht = klon.ViewObject
        if ansicht is None or not hasattr(ansicht, "DiffuseColor"):
            return
        if self._farben_vorher is None:
            aussehen = getattr(ansicht, "ShapeAppearance", None)
            linien = getattr(ansicht, "LineColorArray", None)
            self._farben_vorher = (
                klon,
                list(ansicht.DiffuseColor),
                list(aussehen) if aussehen is not None else None,
                list(linien) if linien is not None else None,
            )
        self._kanten_faerben(ansicht, klon, kanten or {})
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

    def _kanten_faerben(self, ansicht, klon, kanten):
        """Die angeklickten Kanten in ihrer Farbe (LineColorArray), die anderen wie vorher."""
        if not hasattr(ansicht, "LineColorArray") or self._farben_vorher[3] is None:
            return
        anzahl = len(klon.Shape.Edges)
        grund = list(self._farben_vorher[3])
        if len(grund) != anzahl:
            grund = [tuple(grund[0]) if grund else tuple(ansicht.LineColor)] * anzahl
        alpha = grund[0][3] if grund and len(grund[0]) > 3 else 0.0
        neu = list(grund)
        for nummer, farbe in kanten.items():
            if nummer < anzahl:
                neu[nummer] = (*(int(farbe[i : i + 2], 16) / 255 for i in (1, 3, 5)), alpha)
        with contextlib.suppress(TypeError, ValueError):  # ohne Farbe je Kante: wie vorher
            ansicht.LineColorArray = neu

    def _farben_zurueck(self):
        if self._farben_vorher is None:
            return
        klon, farben, aussehen, linien = self._farben_vorher
        self._farben_vorher = None
        try:
            ansicht = klon.ViewObject
            if ansicht is None:
                return
            if linien is not None and hasattr(ansicht, "LineColorArray"):
                ansicht.LineColorArray = linien
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
        tc_vorher = self.block_zu_aendern.tc_vorher if self.block_zu_aendern else None
        self._fuellt = True
        try:
            werkstoffe_anbieten(self.wahl_werkstoff, self.bibliothek)
            if vorher is None:
                alle = self.bibliothek.alle_werkstoffe()
                werkstoff, _gemerkt = js.werkstoff_fuer(self.job, alle, tc_vorher)
                vorher = werkstoff.kennung if werkstoff is not None else wz.ALLE
            self.wahl_werkstoff.setCurrentIndex(max(0, self.wahl_werkstoff.findData(vorher)))
        finally:
            self._fuellt = False
        block = self.block_zu_aendern
        if block is not None and block.tc_vorher is not None and block.vorwahl is None:
            werkzeug = js.werkzeug_von(block.tc_vorher, self.bibliothek)
            block.vorwahl = werkzeug.kennung if werkzeug is not None else ""
        for block in self.bloecke:
            block.fraeser_fuellen(self.bibliothek, self.werkstoff())

    def werkstoff(self):
        return self.wahl_werkstoff.currentData() or wz.ALLE

    def _werkstoff_gewaehlt(self):
        if not self._fuellt:
            for block in self.bloecke:
                block.fraeser_fuellen(self.bibliothek, self.werkstoff())

    def fraeser(self):
        """Der Fräser des Planfräsens – für die Szenarien und zum Lesen."""
        return self.plan.fraeser()

    def einsatz(self):
        return self.plan.einsatz()

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

    # --- Werte und Vorschau -----------------------------------------------------------------

    def vorschau_starten(self):
        if self._fuellt or self._ruhig or self.geschlossen:
            return
        for block in self.bloecke:
            block.vorschau = None
        self._vorschau_uhr.start()
        self._knoepfe_beschriften()

    def _vorschau_rechnen(self):
        """Die grobe Bahn je angehaktem Block – und damit „Anlegen“ weiß, ob es geht. Was die
        Strategien mit den gewählten Flächen anfangen können, gilt für den ganzen Lauf
        (_eigene, P-2026-10-03-28: am Testteil 95 Fragen je Lauf)."""
        self._vorschau_uhr.stop()
        if self.geschlossen or self.job is None:
            return
        self._flaechen_merk = {}
        try:
            self._vorschau_rechnen_mit_merk()
        finally:
            self._flaechen_merk = None

    def _vorschau_rechnen_mit_merk(self):
        form = vr.modell(self.job).Shape
        self._raeumen_boeden = None
        boeden = self._nur_boeden(form)
        gerechnet = {}  # Block → woraus seine Vorschau gerechnet ist (_block_rechnen)
        for block in self.bloecke:
            self._block_rechnen(block, form, boeden, gerechnet)
        self._wettbewerb(form, nur_bohrung=boeden is not None)
        # Der Wettbewerb setzt Haken um: Das Planfräsen verliert ihn ans Räumen oder umgekehrt.
        # Wer dahinter gerechnet hat, stand dann auf dem Material des Verlierers („… hat
        # „Planfräsen“ schon weggenommen“ unter dem 3D-Schruppen, obwohl das Räumen angehakt ist –
        # B-009; die Kontur mit „die Tasche räumt das Räumen“ ohne Räumen, P-2026-10-02-17): Er
        # rechnet noch einmal, und der Wettbewerb entscheidet mit den neuen Zeiten. Höchstens
        # zweimal – dann steht es.
        for _runde in range(2):
            neu = [b for b in self.bloecke if self._block_rechnen(b, form, boeden, gerechnet, True)]
            if not neu:
                break
            self._wettbewerb(form, nur_bohrung=boeden is not None)
        self._schon_weg_abhaken()
        self._ziel_zeigen(form)
        self._raeumen_ausgelassen_zeigen()
        self._unfertig_zeigen(form)
        self._knoepfe_beschriften()

    # --- Das Teil muss herauskommen (Grundsatz 0) -------------------------------------------

    def _fertige_flaechen(self, block, form):
        """Die gewählten Flächen, die der Block mit seinen Werten genau fertig macht – so, wie
        sie gezeichnet sind: ohne Aufmaß, mit seinem Haken „Schlichten“. Schruppen mit Aufmaß
        (Räumen an Wänden, 3D-Schruppen, Rest räumen an Wänden) zählt nicht, auch nicht, was
        nur Ecken (Restmaterial), Kehlen (Bleistift) oder Anbohrungen (Zentrieren) macht."""
        werte = block.werte()
        if block is self.plan:
            return self._flaechen(block, form) if not float(werte.get("aufmass", 0.0)) else []
        if block in (self.raeumen, self.restraeumen):
            if float(werte.get("aufmass_boden", 0.0)):
                return []
            return self._raeumt(form) if block is self.raeumen else self._flaechen(block, form)
        if block is self.schlichten_danach:
            zusatz = self._schlichten_danach_zusatz(form)
            flaechen = list(zusatz.get("boden_flaechen", ())) if werte.get("boden") else []
            if werte.get("waende"):
                flaechen += list(zusatz.get("wand_flaechen", ()))
            return flaechen
        if block in (self.nut, self.kontur, self.bohrung):
            if werte.get("schlichten") or not float(werte.get("aufmass", 0.0)):
                return self._flaechen(block, form)
            return []
        if block in (
            self.bohren,
            self.gewinde,
            self.gewindefraesen,
            self.entgraten,
            self.entgraten3d,
            self.senken,
            self.reiben,
            self.schlichten3d,
            self.restschlichten,
        ):
            return self._flaechen(block, form)
        if block is self.flanke:
            return self._flaechen(block, form) if not float(werte.get("aufmass", 0.0)) else []
        return []

    def _unfertige(self, form):
        """[(Fläche, [Blöcke, die sie fertig machten])] für jede gewählte Fläche, die am Ende
        keine genaue Bahn hätte – ohne die, mit denen keine Strategie etwas anfangen kann (die
        stehen rot in der Liste)."""
        je_block = {
            b: set(self._fertige_flaechen(b, form)) for b in self.bloecke if b.aktiv() or b.moeglich
        }
        fertig = set().union(*(je_block[b] for b in self.aktive_bloecke()))
        ergebnis = []
        for name in self.gewaehlte:
            if name in fertig or not any(b.s.passt(form, name) for b in self.bloecke):
                continue
            koennten = [b for b in self.bloecke if not b.aktiv() and name in je_block.get(b, ())]
            ergebnis.append((name, koennten))
        return ergebnis

    def _unfertig_zeigen(self, form):
        """Rot über den Blöcken, welche gewählte Fläche am Ende keine genaue Bahn hätte – ein
        Zapfen aus dem Räumen wäre ein Vieleck im Aufmaß – und welcher Haken sie fertig macht."""
        unfertig = self._unfertige(form) if self.job is not None else []
        if not unfertig:
            self.unfertig.hide()
            return
        namen = [name for name, _k in unfertig]
        flaechen = ", ".join(namen[:4]) + (" …" if len(namen) > 4 else "")
        bloecke = []
        for _name, koennten in unfertig:
            for block in koennten:
                if block not in bloecke:
                    bloecke.append(block)
        if bloecke:
            titel = ", ".join(f"„{b.s.titel()}“" for b in bloecke)
            text = tr("ba.unfertig", flaechen=flaechen, bloecke=titel)
        else:
            text = tr("ba.unfertig.keiner", flaechen=flaechen)
        self.unfertig.setText(dezimal(text))
        self.unfertig.show()

    def _block_rechnen(self, block, form, boeden, gerechnet, nur_anders=False):
        """Die Vorschau eines Blocks, wenn er angehakt ist oder im Wettbewerb steht; sonst leer.
        `gerechnet` merkt je Block, woraus sie gerechnet ist – seine Flächen, was der Assistent
        ihm vorgibt, sein Materialstand. Mit `nur_anders` (nach dem Wettbewerb) rechnet er nur,
        wenn sich daran etwas geändert hat. Gibt zurück, ob er gerechnet hat."""
        if nur_anders and boeden is not None and block in (self.plan, self.raeumen):
            return False  # die Folge (_folge) hat beide gerechnet, mit ihren Sätzen
        dabei = block.aktiv() or self._im_wettbewerb(block)
        if block is self.raeumen and boeden is not None and dabei:
            self._folge(form, boeden)  # setzt die Haken selbst, vor allen dahinter
            return False
        if block is self.restraeumen:
            self._restraeumen_einrichten(form)  # nach dem Räumen: was es ausließ
            dabei = block.aktiv() or self._im_wettbewerb(block)
        if block is self.schlichten_danach:
            self._schlichten_danach_einrichten(form)  # nur mit dem Räumen
            dabei = block.aktiv()
        if not dabei:
            # Nach dem Wettbewerb bleibt stehen, was er dem Verlierer hingeschrieben hat – nur
            # „Rest räumen“ und „Schlichten danach“ ohne Räumen davor haben nichts mehr zu sagen.
            if not nur_anders or block in (self.restraeumen, self.schlichten_danach):
                block.leeren()
                gerechnet.pop(block, None)
            return False
        eigen = zusatz = self._zusatz(block, form)
        stand = None
        if block in (self.plan, self.nut, self.raeumen, self.kontur, self.schruppen3d):
            stand = self._materialstand(block, form)
            zusatz = dict(zusatz or {}, materialstand=stand)
        elif block in (self.restraeumen, self.schlichten_danach):
            # Nach dem Räumen derselben Flächen – sie treten nicht gegen es an.
            stand = self._materialstand(block, form, flaechen=())
            zusatz = dict(zusatz or {}, materialstand=stand)
        flaechen = self._flaechen(block, form)
        woraus = (tuple(flaechen), eigen, getattr(stand, "kennung", None))
        if nur_anders and gerechnet.get(block) == woraus:
            return False
        block.vorschau_rechnen(self.job, flaechen, zusatz)
        gerechnet[block] = woraus
        if block is self.kontur:
            self._kontur_text(form, eigen)
        if block is self.bohren and zusatz and block.ergebnis_basis:
            d = groesse_zeigen(block.fraeser().durchmesser, einheiten.LAENGE) or "0"
            block.ergebnis.setText(tr("ba.bohren.vorbohren", text=block.ergebnis_basis, d=d))
        return True

    def _raeumt(self, form):
        """Die Flächen, die das Räumen wirklich räumt: seine Flächen ohne die Böden der Taschen,
        in die sein Fräser nicht passt (B-007; raeumen_bahn.Raeumbahn.ausgelassen)."""
        ausgelassen = set(getattr(self.raeumen.vorschau, "ausgelassen", None) or [])
        rest = self.restraeumen
        if rest.aktiv() and rest.vorschau is not None:
            # Was „Rest räumen“ mit dem kleineren Fräser nachholt, ist geräumt.
            ausgelassen &= set(getattr(rest.vorschau, "ausgelassen", None) or [])
        return set(self._flaechen(self.raeumen, form)) - ausgelassen

    def _raeumen_ausgelassen_zeigen(self):
        """Hinter das Ergebnis des Räumens, in welche Taschen sein Fräser nicht passt (B-007,
        Manuels Testteil: die dreieckige Tasche und der Ø 12) – sie bleiben stehen; bisher fiel
        das ohne ein Wort aus."""
        block = self.raeumen
        ausgelassen = list(getattr(block.vorschau, "ausgelassen", None) or [])
        text = block.ergebnis.text()
        if not ausgelassen or not text or block.fraeser() is None:
            return
        d = groesse_zeigen(block.fraeser().durchmesser, einheiten.LAENGE) or "0"
        flaechen = ", ".join(ausgelassen)
        rest = self.restraeumen
        if rest.aktiv() and rest.vorschau is not None:
            werkzeug = mg.genannt(rest.fraeser(), self.magazin())
            if len(ausgelassen) == 1:
                neu = tr(
                    "ba.raeumen.ausgelassen.rest", text=text, flaeche=flaechen, d=d, t=werkzeug
                )
            else:
                neu = tr(
                    "ba.raeumen.ausgelassen.rest.mehrere", text=text, flaechen=flaechen, d=d,
                    t=werkzeug,
                )  # fmt: skip
        elif len(ausgelassen) == 1:
            neu = tr("ba.raeumen.ausgelassen", text=text, flaeche=flaechen, d=d)
        else:
            neu = tr("ba.raeumen.ausgelassen.mehrere", text=text, flaechen=flaechen, d=d)
        block.ergebnis.setText(neu)

    def _restraeumen_einrichten(self, form):
        """„Rest räumen“ nach der Vorschau des Räumens (W-013 T3; Manuel: „auch mit mehreren
        Arbeitsschritten“): Lässt das Räumen eine Tasche aus, weil sein Fräser nicht hineinpasst,
        und passt ein kleinerer aus der Werkzeugverwaltung, wird der Block möglich, bekommt den
        größten, der passt, und – solange niemand ihn von Hand gesetzt hat – den Haken. Sonst
        steht er bei dem, was nicht zur Wahl passt. Fährt die Kontur die Wände einer solchen
        Tasche, bekommt auch „Restmaterial“ den Haken: Ihr Fräser kommt dort nicht überall hin."""
        rest, gross = self.restraeumen, self.raeumen
        ausgelassen = []
        if gross.aktiv() and gross.fraeser() is not None and self.zu_aendern is None:
            ausgelassen = list(getattr(gross.vorschau, "ausgelassen", None) or [])
        passend = self._restraeumfraeser(form, ausgelassen) if ausgelassen else None
        moeglich = passend is not None
        geaendert = moeglich != rest.moeglich
        self._fuellt = self._ruhig = True
        try:
            rest.moeglich = moeglich
            rest.haken.setEnabled(moeglich)
            rest.erklaerung.setText(rest.s.text() if moeglich else rest.s.unmoeglich_text())
            if not moeglich:
                rest.haken.setChecked(False)
            elif not rest.von_hand:
                rest.haken.setChecked(True)
            # Der größte, der passt – ein kleinerer, von Hand gewählt, bleibt.
            jetzt = rest.fraeser()
            zu_gross = jetzt is None or (
                moeglich and float(jetzt.durchmesser) > float(passend.durchmesser) + 1e-6
            )
            if moeglich and zu_gross:
                self._fuellt = False  # die Einsätze des neuen Fräsers füllen
                rest.fraeser_setzen(passend)
                self._fuellt = True
            rest.zustand_zeigen()
            wand = self.rest
            an_der_wand = set(_waende_um(form, ausgelassen)) & set(
                self._flaechen(self.kontur, form)
            )
            dazu = rest.aktiv() and self.kontur.aktiv() and bool(an_der_wand)
            if dazu and wand.moeglich and not wand.von_hand:
                wand.haken.setChecked(True)
                wand.zustand_zeigen()
        finally:
            self._fuellt = self._ruhig = False
        if geaendert:
            self._bloecke_ordnen()

    def _restraeumfraeser(self, form, ausgelassen):
        """Der größte Fräser der Werkzeugverwaltung, kleiner als der des Räumens, der in alle
        Taschen passt, die es ausließ – None, wenn keiner. Probiert wird mit der Vorschau, vom
        größten her; das Ergebnis je Wahl gemerkt."""
        rest, gross = self.restraeumen, self.raeumen
        gross_d = float(gross.fraeser().durchmesser)
        werte = gross.werte()
        schluessel = (
            tuple(ausgelassen),
            round(gross_d, 6),
            round(float(werte["aufmass"]), 6),
            tuple(w.kennung for w in rest._fraeser),
            self.werkstoff(),
        )
        gemerkt = getattr(self, "_restraeumfraeser_gemerkt", None)
        if gemerkt is not None and gemerkt[0] == schluessel:
            return gemerkt[1]
        passend = None
        kleiner = [w for w in rest._fraeser if float(w.durchmesser) < gross_d - 1e-6]
        for werkzeug in sorted(kleiner, key=lambda w: -float(w.durchmesser)):
            einsaetze = rest._passende_einsaetze(werkzeug, self.werkstoff())
            arten = [e.art for e in einsaetze]
            einsatz = next(
                (einsaetze[arten.index(a)] for a in rest.s.einsatz_reihenfolge if a in arten),
                einsaetze[0] if einsaetze else None,
            )
            if einsatz is None:
                continue
            try:
                bahn = ra.vorschau(
                    self.job,
                    self.job.Model.Group,
                    ff.von_werkzeug(werkzeug),
                    rest.s.vorschlag("zustellung", werkzeug, einsatz),
                    rest.s.vorschlag("zeilenabstand", werkzeug, einsatz),
                    float(werte["aufmass"]),
                    ausgelassen,
                    schneidenlaenge=float(werkzeug.schneidenlaenge or 0.0),
                )
            except (ValueError, RuntimeError):
                continue  # passt auch nicht
            if not bahn.ausgelassen:
                passend = werkzeug
                break
        self._restraeumfraeser_gemerkt = (schluessel, passend)
        return passend

    def _schlichten_danach_einrichten(self, form):
        """„Schlichten danach“ geht, sobald das Räumen angehakt ist und gerechnet hat (nicht beim
        Ändern). Wird es möglich, ist der Fräser des Räumens vorgewählt – mit seinem Einsatz
        „Schlichten“ (einsatz_reihenfolge); einen anderen wählt man von Hand. Angehakt wird es nur
        von Hand: Ob nach dem Räumen geschlichtet wird, entscheidet, wer fräst."""
        block, gross = self.schlichten_danach, self.raeumen
        moeglich = self.zu_aendern is None and gross.aktiv()
        geaendert = moeglich != block.moeglich
        self._fuellt = self._ruhig = True
        try:
            block.moeglich = moeglich
            block.haken.setEnabled(moeglich)
            block.erklaerung.setText(block.s.text() if moeglich else block.s.unmoeglich_text())
            if not moeglich:
                block.haken.setChecked(False)
            elif not block.von_hand and gross.fraeser() is not None:
                jetzt = block.fraeser()
                if jetzt is None or jetzt.kennung != gross.fraeser().kennung:
                    self._fuellt = False  # die Einsätze des Fräsers füllen
                    block.fraeser_setzen(gross.fraeser())
                    self._fuellt = True
            block.zustand_zeigen()
        finally:
            self._fuellt = self._ruhig = False
        if geaendert:
            self._bloecke_ordnen()

    def _schlichten_danach_zusatz(self, form):
        """Was „Schlichten danach“ vom Räumen übernimmt: die Böden, die es räumt, die Wände um sie –
        ohne die, die die Kontur schon fährt –, seine Aufmaße und den Gleichlauf."""
        raeumen = self.raeumen
        if not raeumen.aktiv():
            return {}
        werte = raeumen.werte()
        boeden = sorted(self._raeumt(form))
        kontur = set(self._flaechen(self.kontur, form)) if self.kontur.aktiv() else set()
        waende = [w for w in _waende_um(form, boeden) if w not in kontur]
        return {
            "boden_flaechen": boeden,
            "wand_flaechen": waende,
            "aufmass_wand": float(werte["aufmass"]),
            "aufmass_boden": float(werte["aufmass_boden"]),
            "gleichlauf": bool(werte["gleichlauf"]),
        }

    def _schon_weg_abhaken(self):
        """Wer „Hier ist nichts mehr zu tun“ sagt (Materialstand, W-012), verliert den Haken –
        solange ihn niemand von Hand gesetzt hat; sonst stünde dort ein Haken, und „Anlegen“
        ginge nicht."""
        weg = [b for b in self.bloecke if b.aktiv() and b.schon_weg and not b.von_hand]
        if not weg:
            return
        self._fuellt = True
        try:
            for block in weg:
                block.haken.setChecked(False)
                block.zustand_zeigen()
        finally:
            self._fuellt = False
        self.nichts_angehakt.setVisible(not self.aktive_bloecke())

    def _ziel_zeigen(self, form):
        """Wie viel weg muss und wie lange der Fräser des Räumens (sonst des Planfräsens, der
        Kontur) mit seinen Werten dafür mindestens braucht – mit dem ap, das jede Stelle hergibt
        – und welcher Fräser der Werkzeugkiste schneller wäre (zielzeit; Manuel, 2026-10-02)."""
        self.ziel_text.setText("")
        self._schneller = None
        self.knopf_schneller.hide()
        material = self._ziel_material(form)
        if material is None or material.volumen <= 0:
            return
        volumen = groesse_fest(material.volumen / 1000.0, einheiten.VOLUMEN, 1)
        saetze = [
            tr("ba.ziel.volumen", volumen=f"{volumen} {einheiten.einheit(einheiten.VOLUMEN)}")
        ]
        eigene = None
        # Die angehakten zuerst: Nach „Übernehmen“ räumt oft das Planfräsen allein, und das
        # Räumen behält nur den Fräser für den Rest.
        bloecke = (self.raeumen, self.plan, self.kontur)
        for block in sorted(bloecke, key=lambda b: not b.aktiv()):
            werkzeug, einsatz = block.fraeser(), block.einsatz()
            werte = zz.werte(werkzeug, einsatz) if werkzeug and einsatz else None
            if werte is not None and werkzeug.art in zz.WEGNEHMER:
                eigene = (werkzeug, zz.ziel(material, werkzeug.durchmesser / 2, *werte))
                break
        if eigene is not None:
            werkzeug, ziel = eigene
            ap = groesse_zeigen(ziel.ap_wirksam, einheiten.LAENGE, 1) or "0"
            saetze.append(
                tr(
                    "ba.ziel.mit",
                    werkzeug=_ziel_werkzeug(werkzeug),
                    zeit=_ziel_minuten(ziel.zeit),
                    ap=f"{ap} {einheiten.einheit(einheiten.LAENGE)}",
                    anteil=int(round(100.0 * ziel.ap_wirksam / ziel.ap)),
                )
            )
            if ziel.rest > 0.02 * material.volumen:
                rest = groesse_fest(ziel.rest / 1000.0, einheiten.VOLUMEN, 1)
                saetze.append(
                    tr("ba.ziel.rest", rest=f"{rest} {einheiten.einheit(einheiten.VOLUMEN)}")
                )
        angebote = []
        if self.bibliothek is not None:
            angebote = zz.vergleiche(material, self.bibliothek.werkzeuge, self.werkstoff())
        if angebote:
            beste = angebote[0]
            vergleich = None
            if eigene is not None:
                gleich = [a for a in angebote if a.werkzeug.kennung == eigene[0].kennung]
                vergleich = gleich[0].zeit if gleich else eigene[1].zeit
            # Schon in den angehakten Strategien (übernommen): kein Angebot mehr.
            genutzt = {
                b.fraeser().kennung
                for b in (self.plan, self.raeumen, self.kontur, self.rest)
                if b.aktiv() and b.fraeser() is not None
            }
            schon = beste.werkzeug.kennung in genutzt and (
                beste.danach is None or beste.danach.werkzeug.kennung in genutzt
            )
            if not schon and (
                eigene is None
                or (beste.werkzeug.kennung != eigene[0].kennung and beste.zeit < 0.8 * vergleich)
            ):
                wer = _ziel_werkzeug(beste.werkzeug)
                if beste.danach is not None:
                    wer = tr(
                        "ba.ziel.danach", werkzeug=wer, rest=_ziel_werkzeug(beste.danach.werkzeug)
                    )
                saetze.append(tr("ba.ziel.schneller", werkzeug=wer, zeit=_ziel_minuten(beste.zeit)))
                if self.zu_aendern is None:
                    self._schneller = beste
                    self.knopf_schneller.show()
        self.ziel_text.setText(" ".join(saetze))
        self._ziel_je_block(form, material)

    def schneller_uebernehmen(self):
        """„Übernehmen“ unter der Ziel-Zeile: die schnelleren Fräser in die Strategien – ein
        Planfräser ins Planfräsen und der für den Rest ins Räumen (das Räumen nimmt dann nur
        die Taschenböden, _folge), ein Schaftfräser ins Räumen und der für den Rest ins
        Restmaterial. Gibt zurück, ob sich etwas geändert hat."""
        angebot = self._schneller
        if angebot is None or self.job is None:
            return False
        erster = angebot.werkzeug
        rest = angebot.danach.werkzeug if angebot.danach is not None else None
        if erster.art == wz.PLANFRAESER:
            paare = ((self.plan, erster), (self.raeumen, rest))
        else:
            paare = ((self.raeumen, erster), (self.rest, rest))
        geaendert = False
        for block, werkzeug in paare:
            if werkzeug is not None and block.fraeser_setzen(werkzeug):
                geaendert = True
        if geaendert:
            self.knopf_schneller.hide()
            self.vorschau_starten()
        return geaendert

    def _ziel_je_block(self, form, material):
        """Hinter die Zeit von Planfräsen und Räumen, wie gut ihr Weg ist (Manuel, 2026-10-02:
        „Ist diese Wegestrategie wirklich gut?“): ihre Zeit geteilt durch die Zielzeit ihres
        Fräsers mit ihren Werten für das, was bis zu ihren Flächen weg muss – „1,03 × Ziel“.
        Räumt das Räumen nach dem Planfräsen nur die Taschenböden, zählt nur die Tasche."""
        for block in (self.plan, self.raeumen):
            werkzeug, einsatz, basis = block.fraeser(), block.einsatz(), block.ergebnis_basis
            text = block.ergebnis.text()
            if None in (block.zeit, werkzeug, einsatz) or not basis or not text.startswith(basis):
                continue
            ebenen = hf.ebenen_oben(form, self._flaechen(block, form))
            if not ebenen:
                continue
            oben = None
            if block is self.raeumen and self._raeumen_boeden is not None:
                plan = hf.ebenen_oben(form, self._flaechen(self.plan, form))
                oben = min(e.z for e in plan) if plan else None
            werte = block.werte()
            try:
                ae, ap = float(werte["zeilenabstand"]), float(werte["zustellung"])
            except (TypeError, ValueError):
                continue
            ziel = zz.ziel(
                material.bis(min(e.z for e in ebenen), oben),
                werkzeug.durchmesser / 2,
                ae,
                ap,
                js.werte_im_job(werkzeug, einsatz, self.job)[1],
            )
            if not (0 < ziel.zeit < math.inf):
                continue
            # Gleich hinter die Zeit – was danach steht (Zeilenrichtung, Vergleich, Folge), bleibt.
            zeit = _zeit_text(block.zeit)
            ende = basis.find(zeit) + len(zeit)
            if ende < len(zeit):
                continue
            faktor = dezimal(f"{block.zeit / ziel.zeit:.2f}")
            neu = tr("ba.ziel.faktor", text=basis[:ende], faktor=faktor)
            if not text.startswith(neu):
                block.ergebnis.setText(neu + text[ende:])

    def _ziel_material(self, form):
        """Das Material zwischen Rohteil (Kasten des Jobs) und Teil (zielzeit.Material) – einmal
        gerechnet je Teil und Rohteil –, darin, was nach den Operationen im Job noch steht (der
        Materialstand, W-012; beim Ändern vor der Operation): Was eine Operation davor schon
        weggenommen hat, muss nicht mehr weg."""
        rohteil = getattr(self.job, "Stock", None)
        if rohteil is None or getattr(rohteil, "Shape", None) is None or rohteil.Shape.isNull():
            return None
        kasten, teil = rohteil.Shape.BoundBox, form.BoundBox
        schluessel = tuple(
            round(w, 6)
            for w in (kasten.XMin, kasten.XMax, kasten.YMin, kasten.YMax, kasten.ZMax)
            + (teil.XMin, teil.XMax, teil.YMin, teil.YMax, teil.ZMin, teil.ZMax, form.Volume)
        )
        gemerkt = getattr(self, "_ziel_gemerkt", None)
        if gemerkt is not None and gemerkt[0] == schluessel:
            material = gemerkt[1]
        else:
            try:
                material = zz.material(
                    form, (kasten.XMin, kasten.XMax, kasten.YMin, kasten.YMax), kasten.ZMax
                )
            except Exception:  # ein Teil, das sich nicht vernetzen lässt: ohne Ziel
                material = None
            self._ziel_gemerkt = (schluessel, material)
        stand = mst.fuer(self.job, vor=self.zu_aendern) if material is not None else None
        if stand is None:
            return material
        gemerkt = getattr(self, "_ziel_stand", None)
        if gemerkt is None or gemerkt[0] != (schluessel, stand.kennung):
            gemerkt = (
                (schluessel, stand.kennung),
                material.unter(stand.hoehen_an(material.x, material.y)),
            )
            self._ziel_stand = gemerkt
        return gemerkt[1]

    def _kontur_text(self, form, zusatz):
        """Der Satz der Kontur, wenn ein anderer Block vor ihr neben den Wänden räumt."""
        if not zusatz or not self.kontur.ergebnis_basis:
            return
        davor = self._kontur_davor(form)
        if davor == "planen":
            text = tr("ba.kontur.nach_planen", text=self.kontur.ergebnis_basis)
        elif davor == "raeumen":
            text = tr("ba.kontur.nach_raeumen_boden", text=self.kontur.ergebnis_basis)
        else:
            text = tr("ba.kontur.nach_raeumen", text=self.kontur.ergebnis_basis)
        self.kontur.ergebnis.setText(text)

    def _materialstand(self, block, form, flaechen=None, mit=()):
        """Der Materialstand vor dem Block (W-012): das Rohteil, die Operationen, die im Job
        schon stehen – beim Ändern die vor der Operation –, dazu die Vorschauen der angehakten
        Blöcke davor in diesem Lauf (sie werden vor ihm angelegt; die in `mit` auch ohne Haken).
        Wer dieselben Flächen hat (`flaechen`, ohne: die des Blocks), tritt gegen ihn an und
        kommt nicht davor (Räumen und Planfräsen am Grund der Nut). None ohne Materialstand."""
        if self.zu_aendern is not None:
            return mst.fuer(self.job, vor=self.zu_aendern)
        eigene = set(self._flaechen(block, form) if flaechen is None else flaechen)
        dazu = []
        for anderer in self.bloecke:
            if anderer is block:
                break
            werkzeug = anderer.fraeser()
            dabei = anderer.aktiv() or anderer in mit
            if not dabei or anderer.vorschau is None or werkzeug is None:
                continue
            if eigene & set(self._flaechen(anderer, form)):
                continue
            fraeser = ff.von_werkzeug(werkzeug)
            if fraeser is not None:
                dazu.append((anderer.s.titel(), anderer.vorschau.punkte, fraeser))
        return mst.fuer(self.job, dazu=dazu)

    def _zusatz(self, block, form):
        """Was der Assistent einem Block vorgibt: Räumt das Räumen den Boden einer Tasche, deren
        Wände die Kontur fährt, und ist die Breite der Kontur leer, dann steht neben den Wänden
        nur noch das Aufmaß des Räumens – die Kontur schlichtet nur noch (Räumen + Kontur mit
        Breite = Aufmaß, die schnellste Folge in der Tasche; Spezifikation Abschnitt 11). Fräst
        das Planfräsen die Böden vor allen Wänden (ein Absatz), steht dort höchstens sein Rest
        an der Wand (P-2026-10-02-17)."""
        if block is self.gewindefraesen:
            return {"werkzeug": block.fraeser()}  # Steigung und Zähne kennt CAM nicht
        if block is self.bohren:
            return {"reiben": True} if self._gerieben(form) else None
        if block is self.rest:
            if self.rest.felder["davor"].text().strip():
                return None  # von Hand eingetragen
            davor = self._davor_durchmesser()
            return {"davor": davor} if davor else None
        if block is self.restschlichten:
            return self._davor_3d(self.restschlichten, self.schlichten3d)
        if block is self.schlichten_danach:
            return self._schlichten_danach_zusatz(form)
        if block is self.restschruppen:
            return self._davor_3d(self.restschruppen, self.schruppen3d)
        if block is not self.kontur or self.kontur.felder["breite"].text().strip():
            return None  # die Breite von Hand eingetragen
        davor = self._kontur_davor(form)
        if davor in ("tasche", "raeumen"):
            return {"breite": max(float(self.raeumen.werte()["aufmass"]), 0.01)}
        if davor == "planen":
            return {"breite": pfb.rest_an_der_wand(float(self.plan.werte()["zeilenabstand"]))}
        return None

    def _kontur_davor(self, form):
        """Wer vor der Kontur neben ihren Wänden räumt: „tasche“ – das Räumen den Boden einer
        Tasche, deren Wände sie fährt; „raeumen“, „planen“ – das Räumen, das Planfräsen die Böden
        vor allen ihren Wänden (ein Absatz, ein Zapfen); sonst None. An einem Absatz fuhr die
        Kontur sonst alle Bahnen vom Rohteil her noch einmal, durch Luft (P-2026-10-02-17)."""
        if self.raeumen.aktiv():
            waende = self.kontur.s.flaechen_fuer(form, self.gewaehlte)
            boeden = set(rb.taschenboeden(form, waende))
            # Nur, wenn das Räumen jede dieser Taschen auch räumt: In eine, in die sein Fräser
            # nicht passt, führe die Kontur sonst mit „nur das Aufmaß“ ins Volle (B-007) – dann
            # sieht sie selbst nach, was noch steht (Materialstand).
            if boeden and boeden <= self._raeumt(form):
                return "tasche"
            if boeden & set(self._flaechen(self.raeumen, form)):
                return None
        vor = kb.boeden_vor(form, self._flaechen(self.kontur, form))
        if vor:
            if self.raeumen.aktiv() and vor <= self._raeumt(form):
                return "raeumen"
            if self.plan.aktiv() and vor <= set(self._flaechen(self.plan, form)):
                return "planen"
        return None

    def _davor_durchmesser(self):
        """Der Ø des Fräsers vor dem Restmaterial: eingetragen, sonst der der Kontur, sonst der
        des Räumens in diesem Fenster – None, wenn keiner da ist."""
        text = self.rest.felder["davor"].text().strip()
        if text:
            try:
                return groesse_lesen(text, einheiten.LAENGE)
            except ValueError:
                return None
        for gross in (self.kontur, self.raeumen):
            if gross.aktiv() and gross.fraeser() is not None:
                return float(gross.fraeser().durchmesser)
        return None

    def _davor_3d(self, rest, gross):
        """{"davor": Ø, "davor_eck": Eckenradius} des Fräsers vor dem Block `rest`
        (Restschlichten, Restschruppen): ist das Feld leer, der des Blocks `gross` in diesem
        Fenster (mit seiner Form); beim Ändern der Eckenradius der Operation, solange ihr Ø im
        Feld steht – sonst None (von Hand eingetragen: eine Kugel beim Restschlichten, ein
        Schaftfräser beim Restschruppen)."""
        text = rest.felder["davor"].text().strip()
        if not text:
            werkzeug = gross.fraeser() if gross.aktiv() else None
            form = ff.von_werkzeug(werkzeug) if werkzeug is not None else None
            if form is None:
                return None
            return {"davor": float(werkzeug.durchmesser), "davor_eck": s3op.eckenradius(form)}
        op = self.zu_aendern
        if op is None or not rest.s.ist(op):
            return None
        try:
            durchmesser = groesse_lesen(text, einheiten.LAENGE)
        except ValueError:
            return None
        if abs(durchmesser - float(op.DurchmesserDavor)) > 1e-6:
            return None
        return {"davor_eck": float(op.EckenradiusDavor)}

    def _restschlichtfraeser_waehlen(self):
        """Wählt in den Blöcken Restschlichten und Restschruppen den größten Fräser, der kleiner
        ist als der davor – wenn der gewählte es nicht ist."""
        for rest, gross in (
            (self.restschlichten, self.schlichten3d),
            (self.restschruppen, self.schruppen3d),
        ):
            davor = (self._davor_3d(rest, gross) or {}).get("davor")
            if davor is None:
                text = rest.felder["davor"].text().strip()
                try:
                    davor = groesse_lesen(text, einheiten.LAENGE) if text else None
                except ValueError:
                    davor = None
            if not davor:
                continue
            jetzt = rest.fraeser()
            if jetzt is not None and jetzt.durchmesser < davor - 1e-6:
                continue
            kleiner = [
                (w.durchmesser, i)
                for i, w in enumerate(rest._fraeser)
                if w.durchmesser < davor - 1e-6
            ]
            if kleiner:
                rest.wahl_fraeser.setCurrentIndex(max(kleiner)[1])

    def _restfraeser_waehlen(self):
        """Wählt im Block Restmaterial den größten Fräser, der kleiner ist als der davor – wenn
        der gewählte es nicht ist."""
        davor = self._davor_durchmesser()
        if not davor:
            return
        jetzt = self.rest.fraeser()
        if jetzt is not None and jetzt.durchmesser < davor - 1e-6:
            return
        kleiner = [
            (w.durchmesser, i)
            for i, w in enumerate(self.rest._fraeser)
            if w.durchmesser < davor - 1e-6
        ]
        if kleiner:
            self.rest.wahl_fraeser.setCurrentIndex(max(kleiner)[1])

    def _rest_vorschlagen(self, form):
        """Der Haken bei „Restmaterial“, wenn die Kontur gezeichnete Rundungen innen fährt, die
        kleiner sind als ihr Fräser, und ein kleinerer da ist (Manuel, 2026-10-02: „Ja“) – sonst
        blieb in einer Ecke R 4 nach dem Ø 12 R 6 stehen. Von Hand gesetzt bleibt er, wie er ist."""
        rest = self.rest
        klein = rest.fraeser()
        if rest.von_hand or not rest.moeglich or klein is None or not self.kontur.aktiv():
            return
        gross = self.kontur.fraeser()
        if gross is None or float(klein.durchmesser) >= float(gross.durchmesser) - 1e-6:
            return
        waende = rest.s.flaechen_fuer(form, self.gewaehlte)
        bohrungen = {b.name for b in bb.bohrungen(form, waende)}
        radius = float(gross.durchmesser) / 2
        if any(
            r < radius - 1e-6 and name not in bohrungen
            for name, r in kb.innenrundungen(form, waende)
        ):
            self._fuellt = True
            try:
                rest.haken.setChecked(True)
                rest.zustand_zeigen()
            finally:
                self._fuellt = False

    def _flaechen(self, block, form):
        """Die Flächen des Blocks – beim Räumen ohne die, die das Planfräsen schon fräst
        (_folge: dann nur die Taschenböden); beim Bohrungsfräsen ohne die, die das Bohren
        bohrt, wenn beide nicht um dieselben Bohrungen wetteifern (ein Flansch: der Bohrer die
        Lochkreisbohrungen, der Fräser die große in der Mitte; P-2026-10-02-12)."""
        flaechen = self._eigene(block, form)
        if block is self.raeumen and self._raeumen_boeden is not None:
            return list(self._raeumen_boeden)
        if block is self.restraeumen:
            # Nur die Taschen, die das Räumen ausließ (Raeumbahn.ausgelassen).
            if not self.raeumen.aktiv():
                return []
            return list(getattr(self.raeumen.vorschau, "ausgelassen", None) or [])
        if block is self.schlichten_danach:
            # Die Böden, die das Räumen räumt (die Wände um sie: _schlichten_danach_zusatz).
            return sorted(self._raeumt(form)) if self.raeumen.aktiv() else []
        if (
            block is self.bohrung
            and self.bohren.aktiv()
            and not self._gleiche_flaechen(block, form, self.bohren)
        ):
            gebohrt = set(self._eigene(self.bohren, form))
            return [f for f in flaechen if f not in gebohrt]
        if block is self.kontur:
            weg = set()
            if self._gerieben(form):
                weg |= set(self.reiben.s.flaechen_fuer(form, self.gewaehlte))
            # Was ein anderer angehakter Block macht, fährt die Kontur nicht nach – außer er
            # wetteifert mit ihr um genau dieselben Flächen (ein Lagerbock: die gebohrten Ø 9
            # unter den Senkungen nicht, P-2026-10-02-15).
            for anderer in (self.bohren, self.bohrung, self.nut):
                if anderer.aktiv() and not self._gleiche_flaechen(block, form, anderer):
                    weg |= set(self._eigene(anderer, form))
            return [f for f in flaechen if f not in weg]
        if (
            block is self.schlichten3d
            and self.flanke.aktiv()
            and not self._gleiche_flaechen(block, form, self.flanke)
        ):
            # Die schrägen Wände fräst die Flanke – das 3D-Schlichten den Rest (eine Kuppel).
            flanke = set(self._eigene(self.flanke, form))
            return [f for f in flaechen if f not in flanke]
        return flaechen

    def _bohrer_da(self, form, gerieben=False):
        """Hat die Werkzeugverwaltung einen Bohrer, der wenigstens eine der gewählten Bohrungen
        bohrt – durchgehend oder mit seiner Spitze darunter, mit seinem Durchmesser (`gerieben`:
        um die Reibzugabe kleiner)? Die anderen fräst „Bohrung fräsen“ (P-2026-10-02-12)."""
        return any(self._bohrbare(form, w, gerieben) for w in self.bohren._fraeser)

    def _bohrbare(self, form, werkzeug=None, gerieben=False):
        """Die gewählten Bohrungen, die der Bohrer `werkzeug` – ohne: der im Block Bohren –
        bohrt (bohren.kann)."""
        werkzeug = werkzeug or self.bohren.fraeser()
        if werkzeug is None:
            return []
        winkel = werkzeug.spitzenwinkel or bh.SPITZENWINKEL
        ergebnis = []
        for name in self.gewaehlte:
            if not bb.ist_bohrung(form, name):
                continue
            liste = bb.bohrungen(form, [name])
            if liste and all(bh.kann(b, werkzeug.durchmesser, winkel, gerieben) for b in liste):
                ergebnis.append(name)
        return ergebnis

    def _eigene(self, block, form):
        """Die Flächen, mit denen der Block bei dieser Wahl arbeitet: beim Bohren nur die
        Bohrungen, die sein Bohrer bohrt, sonst alle, mit denen er etwas anfangen kann."""
        if block is self.bohren:
            return self._bohrbare(form, gerieben=self._gerieben(form))
        merk = getattr(self, "_flaechen_merk", None)
        if merk is None:
            return block.s.flaechen_fuer(form, self._wahl(block))
        if id(block) not in merk:
            merk[id(block)] = list(block.s.flaechen_fuer(form, self._wahl(block)))
        return list(merk[id(block)])

    def _gerieben(self, form):
        """Wird gerieben – Reiben angehakt, und eine Reibahle passt zu den gewählten Bohrungen?"""
        return self.reiben.haken.isChecked() and self._reibahle_da(form)

    def _reibahle_da(self, form):
        """Hat die Werkzeugverwaltung eine Reibahle für alle gewählten Bohrungen?"""
        liste = bb.bohrungen(form, [n for n in self.gewaehlte if bb.ist_bohrung(form, n)] or [""])
        return bool(liste) and any(
            all(rbn.kann(b, w.durchmesser) for b in liste) for w in self.reiben._fraeser
        )

    def _reibahle_waehlen(self, form):
        """Wählt im Block Reiben die Reibahle mit dem Durchmesser der gewählten Bohrungen – wenn
        die gewählte nicht passt."""
        liste = bb.bohrungen(form, [n for n in self.gewaehlte if bb.ist_bohrung(form, n)] or [""])
        if not liste:
            return
        jetzt = self.reiben.fraeser()
        if jetzt is not None and all(rbn.kann(b, jetzt.durchmesser) for b in liste):
            return
        for i, w in enumerate(self.reiben._fraeser):
            if all(rbn.kann(b, w.durchmesser) for b in liste):
                self.reiben.wahl_fraeser.setCurrentIndex(i)
                return

    def _bohrungs_durchmesser(self, form):
        """Der Durchmesser der gewählten Bohrungen – None, wenn keine oder verschiedene."""
        namen = [n for n in self.gewaehlte if bb.ist_bohrung(form, n)]
        durchmesser = {round(2 * b.radius, 3) for b in bb.bohrungen(form, namen or [""])}
        return durchmesser.pop() if len(durchmesser) == 1 else None

    def _gewindebohrer_da(self, form):
        """Hat die Werkzeugverwaltung einen Gewindebohrer, dessen Kernloch alle gewählten
        Bohrungen haben?"""
        d = self._bohrungs_durchmesser(form)
        return d is not None and any(
            abs(gw.kernloch(w.durchmesser, w.steigung) - d) <= gw.GLEICH_D
            for w in self.gewinde._fraeser
        )

    def _gewindebohrer_waehlen(self, form):
        """Wählt im Block Gewinde den Gewindebohrer, dessen Kernloch die gewählten Bohrungen
        haben – wenn der gewählte nicht passt."""
        d = self._bohrungs_durchmesser(form)
        if d is None:
            return
        jetzt = self.gewinde.fraeser()
        if jetzt is not None and abs(gw.kernloch(jetzt.durchmesser, jetzt.steigung) - d) <= (
            gw.GLEICH_D
        ):
            return
        for i, w in enumerate(self.gewinde._fraeser):
            if abs(gw.kernloch(w.durchmesser, w.steigung) - d) <= gw.GLEICH_D:
                self.gewinde.wahl_fraeser.setCurrentIndex(i)
                return

    def _gewindefraeser_passt(self, werkzeug, liste):
        """Fräst `werkzeug` in alle Bohrungen `liste` ein Gewinde (gewinde_bahn.stelle)?"""
        werte = gf.aus_werkzeug(werkzeug)
        w = gfb.Gewindewerte(
            fraeser_radius=werte["fraeser_radius"],
            steigung=float(werkzeug.steigung or 0.0),
            oben=max((b.z_oben for b in liste), default=0.0),
            sicher=0.0,
            zaehne=gf.zaehne_von(werkzeug),
            flankenwinkel=werte["flankenwinkel"],
            spitze=werte["spitze"],
            hals_radius=werte["hals_radius"],
            reichweite=werte["reichweite"],
        )
        if w.steigung <= 0:
            return False
        try:
            for b in liste:
                gfb.stelle(b, w)
        except ValueError:
            return False
        return True

    def _gewindefraeser_liste(self, form):
        namen = [n for n in self.gewaehlte if bb.ist_bohrung(form, n)]
        return bb.bohrungen(form, namen) if namen else []

    def _gewindefraeser_da(self, form):
        """Hat die Werkzeugverwaltung einen Gewindefräser, der in alle gewählten Bohrungen ein
        Gewinde fräst – seine Steigung zu ihrem Kernloch, klein genug?"""
        liste = self._gewindefraeser_liste(form)
        return bool(liste) and any(
            self._gewindefraeser_passt(w, liste) for w in self.gewindefraesen._fraeser
        )

    def _gewindefraeser_waehlen(self, form):
        """Wählt im Block Gewinde fräsen einen Gewindefräser, der zu den gewählten Bohrungen
        passt – wenn der gewählte es nicht tut."""
        liste = self._gewindefraeser_liste(form)
        if not liste:
            return
        jetzt = self.gewindefraesen.fraeser()
        if jetzt is not None and self._gewindefraeser_passt(jetzt, liste):
            return
        for i, w in enumerate(self.gewindefraesen._fraeser):
            if self._gewindefraeser_passt(w, liste):
                self.gewindefraesen.wahl_fraeser.setCurrentIndex(i)
                return

    @staticmethod
    def _entgrat_passt(werkzeug, fasen_):
        """Fräst `werkzeug` alle gezeichneten Fasen und Rundungen `fasen_` – ein Fasenfräser mit
        ihrem Winkel, ein Radienfräser mit ihrem Radius?"""
        for f in fasen_:
            if f.radius > 0:
                if werkzeug.art != wz.RADIENFRAESER:
                    return False
                profil, _spitze, _hoehe = wf.radienprofil(werkzeug)
                if abs(profil - f.radius) > eb.RADIUS_GLEICH:
                    return False
            else:
                if werkzeug.art != wz.FASENFRAESER:
                    return False
                _spitze, _hoehe, winkel = wf.kegel(werkzeug)
                if abs(winkel / 2 - f.winkel) > eb.FASE_WINKEL:
                    return False
        return True

    def _entgratfraeser_waehlen(self, form):
        """Wählt im Block Entgraten den Fräser für die gezeichneten Fasen und Rundungen der Wahl
        – wenn der gewählte sie nicht kann."""
        fasen_ = eb._gewaehlte_fasen(form, self.gewaehlte)
        if not fasen_:
            return
        jetzt = self.entgraten.fraeser()
        if jetzt is not None and self._entgrat_passt(jetzt, fasen_):
            return
        for i, w in enumerate(self.entgraten._fraeser):
            if self._entgrat_passt(w, fasen_):
                self.entgraten.wahl_fraeser.setCurrentIndex(i)
                return

    def _senker_passt(self, werkzeug, liste):
        winkel = float(werkzeug.spitzenwinkel or sk.SPITZENWINKEL)
        return all(
            abs(s.winkel - winkel) <= sk.GLEICH_WINKEL
            and s.durchmesser <= werkzeug.durchmesser + sk.GLEICH_D
            for s in liste
        )

    def _senker_da(self, form):
        """Hat die Werkzeugverwaltung einen Kegelsenker für alle gewählten Senkungen – ihr
        Winkel, mindestens ihr Ø?"""
        liste = sk.senkungen(form, [n for n in self.gewaehlte if sk.ist_senkung(form, n)] or [""])
        return bool(liste) and any(self._senker_passt(w, liste) for w in self.senken._fraeser)

    def _senker_waehlen(self, form):
        """Wählt im Block Senken den Kegelsenker, der zu den gewählten Senkungen passt – den
        kleinsten, wenn der gewählte nicht passt."""
        liste = sk.senkungen(form, [n for n in self.gewaehlte if sk.ist_senkung(form, n)] or [""])
        if not liste:
            return
        jetzt = self.senken.fraeser()
        if jetzt is not None and self._senker_passt(jetzt, liste):
            return
        passend = [
            (w.durchmesser, i)
            for i, w in enumerate(self.senken._fraeser)
            if self._senker_passt(w, liste)
        ]
        if passend:
            self.senken.wahl_fraeser.setCurrentIndex(min(passend)[1])

    def _bohrer_waehlen(self, form, gerieben=False):
        """Wählt im Block Bohren den Bohrer mit dem Durchmesser der gewählten Bohrungen – wenn
        der gewählte nicht passt; `gerieben`: den größten, der um die Reibzugabe kleiner ist."""
        anzahl = [len(self._bohrbare(form, w, gerieben)) for w in self.bohren._fraeser]
        if not anzahl or max(anzahl) == 0:
            return
        jetzt = self.bohren.fraeser()
        if jetzt is not None and len(self._bohrbare(form, jetzt, gerieben)) == max(anzahl):
            return
        passend = [i for i, n in enumerate(anzahl) if n == max(anzahl)]
        wahl = max(passend, key=lambda i: self.bohren._fraeser[i].durchmesser)
        self.bohren.wahl_fraeser.setCurrentIndex(wahl if gerieben else passend[0])

    def _planeinsatz_waehlen(self, form):
        """Wählt im Planfräsen den Einsatz, mit dem der Fräser schneller ist (Grundsatz 0;
        P-2026-10-02-54): „Planen“ – großes ae bei kleinem ap – für eine dünne Schicht,
        „Schruppen“ mit der ganzen Schneide für tiefes Material. Je Einsatz die Zielzeit bis zu
        seinen Flächen (zielzeit.ziel), die kürzere gewinnt. Neu gewählt wird nur, wenn sich das
        ändert – sonst bleibt, was von Hand gewählt ist."""
        block = self.plan
        werkzeug = block.fraeser()
        material = self._ziel_material(form) if werkzeug is not None else None
        ebenen = hf.ebenen_oben(form, self._flaechen(block, form)) if material is not None else []
        if not ebenen:
            return
        bis = material.bis(min(e.z for e in ebenen))
        zeiten = {}
        for einsatz in block._einsaetze:
            werte = zz.werte(werkzeug, einsatz) if einsatz.art in zz.WEGNEHMEN else None
            if werte is not None and einsatz.art in (wz.PLANEN, wz.SCHRUPPEN):
                zeit = zz.ziel(bis, werkzeug.durchmesser / 2, *werte).zeit
                zeiten[einsatz.art] = min(zeit, zeiten.get(einsatz.art, math.inf))
        if len(zeiten) < 2:
            return
        tief = zeiten[wz.SCHRUPPEN] < zeiten[wz.PLANEN]
        if tief != block.s.tief:
            block.s.tief = tief
            block.einsatz_fuellen(self.werkstoff())

    def _nutfraeser_waehlen(self, form):
        """Wählt im Block Nut einen Fräser, der in die gewählten Nuten passt, wenn der gewählte es
        nicht tut – am liebsten den größten, der Bögen fährt, sonst den größten, der hineinpasst;
        und den Einsatz dazu: „Vollnut“ zuerst, wenn er sie in voller Breite fräst."""
        namen = [n for n in self.gewaehlte if nb.ist_nut(form, n)]
        liste = nb.nuten(form, namen) if namen else []
        if not liste:
            return
        block = self.nut
        aufmass = block.wert("aufmass") if block.haken_felder["schlichten"].isChecked() else 0.0

        def arten(w):
            return {nb.verfahren(n, w.durchmesser / 2, aufmass) for n in liste}

        geht = {"boegen", "vollnut"}
        wahl = block.wahl_fraeser.currentIndex()
        jetzt = block.fraeser()
        if jetzt is None or not arten(jetzt) <= geht:
            boegen = [i for i, w in enumerate(block._fraeser) if arten(w) == {"boegen"}]
            passen = [i for i, w in enumerate(block._fraeser) if arten(w) <= geht]
            if boegen or passen:
                wahl = max(boegen or passen, key=lambda i: block._fraeser[i].durchmesser)
        if not 0 <= wahl < len(block._fraeser):
            return
        vollnut = "vollnut" in arten(block._fraeser[wahl])
        anders = vollnut != block.s.vollnut
        block.s.vollnut = vollnut
        if wahl != block.wahl_fraeser.currentIndex():
            block.wahl_fraeser.setCurrentIndex(wahl)  # füllt die Einsätze neu
        elif anders:
            block.einsatz_fuellen(self.werkstoff())

    def _von_raeumen_geraeumt(self, form):
        """Räumt das Räumen die Böden aller gewählten Bohrungen (Sackbohrungen, deren Wände
        gewählt sind – rb.taschenboeden)? Dann ist dort Räumen und danach die Kontur mit dem
        Aufmaß die Folge (Spezifikation Abschnitt 11), und „Bohrung fräsen“ tritt nicht an –
        es würde die ganze Bohrung fräsen, die Kontur nur das Aufmaß (auf Manuels Platte:
        „Bohrung fräsen wäre 1741 % langsamer“)."""
        if not self.raeumen.aktiv():
            return False
        bohrungen = self.bohrung.s.flaechen_fuer(form, self.gewaehlte)
        if not bohrungen:
            return False
        geraeumt = set(self._flaechen(self.raeumen, form))
        for name in bohrungen:
            boeden = rb.taschenboeden(form, [name])
            if not boeden or not set(boeden) <= geraeumt:
                return False
        return True

    def _gleiche_flaechen(self, block, form, andere=None):
        """Löst `andere` – ohne: einer der Gegner des Blocks (_gegner) – dieselbe Aufgabe, genau
        dieselben Flächen?"""
        eigene = set(self._eigene(block, form))
        gegner = [andere] if andere is not None else self._gegner(block)
        return any(set(self._eigene(g, form)) == eigene for g in gegner)

    def _nur_boeden(self, form):
        """Die Taschenböden, die nur das Räumen kann – wenn außer ihnen auch ebene Flächen
        gewählt sind, die das Planfräsen könnte; sonst None."""
        if self.zu_aendern is not None or not self.plan.moeglich or not self.raeumen.moeglich:
            return None
        flach = self.plan.s.flaechen_fuer(form, self.gewaehlte)
        alle = self.raeumen.s.flaechen_fuer(form, self.gewaehlte)
        if not flach or not set(flach) < set(alle):
            return None
        return [f for f in alle if f not in flach]

    def _folge(self, form, boeden):
        """Ebene Flächen und Taschenböden gewählt: Entweder räumt das Räumen alles, oder das
        Planfräsen fräst die ebenen Flächen und das Räumen nur die Böden – die schnellere Folge
        bekommt die Haken (Grundsatz 0), solange niemand sie von Hand gesetzt hat. Sind beide
        angehakt, räumt das Räumen nur die Böden: keine Fläche zweimal."""
        plan, raeumen = self.plan, self.raeumen
        flaechen = raeumen.s.flaechen_fuer(form, self.gewaehlte)

        def mit_stand(eigene, mit=()):  # der Materialstand vor dem Räumen dieser Flächen
            return {"materialstand": self._materialstand(raeumen, form, eigene, mit)}

        if not plan.aktiv() and (plan.von_hand or not plan.moeglich):
            raeumen.vorschau_rechnen(self.job, flaechen, mit_stand(flaechen))
            return
        if plan.vorschau is None:
            eben = plan.s.flaechen_fuer(form, self.gewaehlte)
            plan.vorschau_rechnen(
                self.job, eben, {"materialstand": self._materialstand(plan, form, eben)}
            )
        raeumen.vorschau_rechnen(self.job, flaechen, mit_stand(flaechen))
        alles = (raeumen.vorschau, raeumen.zeit, raeumen.ergebnis_basis, raeumen.hinweis.text())
        # Nur die Böden: Das Planfräsen fräst davor die ebenen Flächen – es gehört dazu.
        raeumen.vorschau_rechnen(self.job, boeden, mit_stand(boeden, (plan,)))
        nur = (raeumen.vorschau, raeumen.zeit, raeumen.ergebnis_basis, raeumen.hinweis.text())
        zeiten = (plan.zeit, alles[1], nur[1])
        if not (plan.von_hand or raeumen.von_hand) and all(z and z > 0 for z in zeiten):
            folge_schneller = plan.zeit + nur[1] < alles[1]
            self._fuellt = True
            try:
                plan.haken.setChecked(folge_schneller)
                raeumen.haken.setChecked(True)
                plan.zustand_zeigen()
                raeumen.zustand_zeigen()
            finally:
                self._fuellt = False
        if plan.aktiv():
            self._raeumen_boeden = list(boeden)
            raeumen.vorschau, raeumen.zeit, raeumen.ergebnis_basis, hinweis = nur
        else:
            raeumen.vorschau, raeumen.zeit, raeumen.ergebnis_basis, hinweis = alles
        raeumen.ergebnis.setText(raeumen.ergebnis_basis)
        raeumen.material.setText(_material_text(raeumen.vorschau))
        raeumen.hinweis.setText(hinweis)
        if not all(z and z > 0 for z in zeiten):
            return
        folge, ganz = plan.zeit + nur[1], alles[1]
        prozent = int(round((max(folge, ganz) / min(folge, ganz) - 1.0) * 100.0))
        if plan.aktiv():
            plan.ergebnis.setText(
                tr("ba.wettbewerb.folge", text=plan.ergebnis_basis, prozent=prozent)
            )
            raeumen.ergebnis.setText(tr("ba.wettbewerb.nur_boeden", text=nur[2]))
        else:
            plan.ergebnis.setText(
                tr("ba.wettbewerb.folge_langsamer", text=plan.ergebnis_basis, prozent=prozent)
            )
            raeumen.ergebnis.setText(tr("ba.wettbewerb.alles", text=alles[2], prozent=prozent))

    def _gruppen(self):
        """Die Strategien, die dieselbe Aufgabe lösen: Planfräsen, Räumen und Nut auf ebenen
        Flächen (dem Grund einer Nut); Bohren, Bohrung fräsen, Kontur und Nut an Wänden. Die Nut
        steht in beiden – sie tritt dort an, wo ihre Flächen dieselben sind."""
        return (
            (self.plan, self.raeumen, self.nut),
            (self.bohren, self.bohrung, self.kontur, self.nut),
            (self.schlichten3d, self.flanke),
        )

    def _gegner(self, block):
        """Die Strategien, die dieselbe Aufgabe lösen wie `block` – aus allen seinen Gruppen."""
        gegner = []
        for gruppe in self._gruppen():
            if block in gruppe:
                gegner.extend(b for b in gruppe if b is not block and b not in gegner)
        return gegner

    def _im_wettbewerb(self, block):
        """Rechnet der Block mit, obwohl er nicht angehakt ist – weil sein Gegner auf denselben
        Flächen angehakt ist und niemand seinen Haken von Hand genommen hat (Grundsatz 0: die
        Zeit entscheidet)?"""
        if self.zu_aendern is not None or not block.moeglich or block.von_hand:
            return False
        gegner = [g for g in self._gegner(block) if g.aktiv()]
        if not gegner:
            return False
        form = vr.modell(self.job).Shape
        if block is self.raeumen and self._nur_boeden(form) is not None:
            return True  # die Folge mit den Taschenböden (_folge)
        if block is self.bohrung and self._von_raeumen_geraeumt(form):
            return False
        return any(self._gleiche_flaechen(block, form, g) for g in gegner)

    def _wettbewerb(self, form, nur_bohrung=False):
        """Je Gruppe (_gruppen: Planfräsen gegen Räumen; Bohren, Bohrung fräsen und Kontur) auf
        denselben Flächen: die schnellste bekommt den Haken, jede Zeile sagt, um wie viel –
        solange niemand einen Haken der Gruppe von Hand gesetzt hat. `nur_bohrung`: die erste
        Gruppe rechnet die Folge (_folge)."""
        if self.zu_aendern is not None:
            return
        for gruppe in self._gruppen():
            if nur_bohrung and self.plan in gruppe:
                continue
            self._wettbewerb_gruppe(form, gruppe)

    def _wettbewerb_gruppe(self, form, gruppe):
        """Die schnellste der Gruppe bekommt den Haken; wer nicht geht (rot), verliert ihn, wenn
        eine andere auf denselben Flächen geht – sonst ginge „Anlegen“ nicht (ein Ø 12 passt
        nicht in die Bohrung Ø 8,5, die der Bohrer bohrt)."""
        mit = [b for b in gruppe if b.zeit is not None and b.zeit > 0 and b.moeglich]
        if not mit:
            return
        teile = {}
        for b in gruppe:
            eigene = frozenset(self._eigene(b, form))
            if eigene:
                teile.setdefault(eigene, []).append(b)
        if len(teile) > 1:
            # Verschiedene Flächen (ein Flansch: der Bohrer die kleinen Bohrungen, der Fräser
            # alle; ein Deckel: die Kontur auch die Wände der Tasche) – je gleiche Flächen ein
            # eigener Wettbewerb; wer allein steht, bleibt; wer dort rot ist, verliert den Haken.
            for teil in teile.values():
                if len(teil) > 1:
                    self._wettbewerb_gruppe(form, teil)
            return
        # Auf dem Grund einer Nut schnitten Planfräsen und Räumen zuerst in voller Breite – mehr
        # als ae, nur scheinbar schneller (an der offenen Nut 0,19 statt 0,85 min, mit Eilgang
        # ins Material). Kann die Nut sie fräsen, treten sie nicht an (P-2026-10-01-47).
        # Hält das Räumen die Last auch in der Nut („adaptiv“ in einer breiten, seit 0.126.0),
        # tritt es an wie jede andere, die Zeit entscheidet.
        voll = []
        if self.nut in mit and self._nur_nutgruende(form):
            bahn = self.raeumen.vorschau
            haelt = getattr(bahn, "variante", "") in ("adaptiv", rb.STICHE) and getattr(
                bahn, "haelt", False
            )
            voll = [b for b in mit if b is self.plan or (b is self.raeumen and not haelt)]
            for b in voll:
                b.ergebnis.setText(tr("ba.wettbewerb.vollschnitt", text=b.ergebnis_basis))
            mit = [b for b in mit if b not in voll]
        mit.sort(key=lambda b: b.zeit)
        rot = [
            b
            for b in gruppe
            if b not in mit
            and b.aktiv()
            and b.hinweis.text()
            and self._gleiche_flaechen(mit[0], form, b)
        ]
        if len(mit) < 2:
            if rot or voll:  # allein in dieser Gruppe – entschieden wird, wo sie Gegner hat
                self._haken_setzen(gruppe, mit[0], rot + voll)
            return
        schnellste, zweite = mit[0], mit[1]

        def prozent(block):
            return int(round((block.zeit / schnellste.zeit - 1.0) * 100.0))

        # Unter 1 % nicht „0 % langsamer“, sondern „weniger als 1 %“ – den Haken hat trotzdem die
        # schnellere (P-2026-10-02-53: die Nut in Bögen und die Kontur liegen oft gleichauf).
        basis, andere = schnellste.ergebnis_basis, zweite.s.titel()
        if prozent(zweite) < 1:
            text = tr("ba.wettbewerb.schnellste_knapp", text=basis, andere=andere)
        else:
            text = tr(
                "ba.wettbewerb.schnellste", text=basis, andere=andere, prozent=prozent(zweite)
            )
        schnellste.ergebnis.setText(text)
        for langsamer in mit[1:]:
            basis, andere = langsamer.ergebnis_basis, schnellste.s.titel()
            if prozent(langsamer) < 1:
                text = tr("ba.wettbewerb.langsamer_knapp", text=basis, andere=andere)
            else:
                text = tr(
                    "ba.wettbewerb.langsamer", text=basis, andere=andere, prozent=prozent(langsamer)
                )
            langsamer.ergebnis.setText(text)
        self._haken_setzen(gruppe, schnellste, mit[1:] + rot + voll)

    def _nur_nutgruende(self, form):
        """Sind die Flächen der Nut in dieser Wahl nur Gründe von Nuten (keine Wand)?"""
        flaechen = self.nut.s.flaechen_fuer(form, self.gewaehlte)
        return bool(flaechen) and all(
            nb.ist_grund(form, n) and nb.ist_nut(form, n) for n in flaechen
        )

    def _haken_setzen(self, gruppe, schnellste, andere):
        """Der Haken bei `schnellste`, nicht bei `andere` – solange niemand einen Haken der
        Gruppe von Hand gesetzt hat."""
        if any(b.von_hand for b in gruppe):
            return
        self._fuellt = True
        try:
            for b in [schnellste, *andere]:
                b.haken.setChecked(b is schnellste)
                b.zustand_zeigen()
        finally:
            self._fuellt = False

    def _auffrischen(self):
        self._knoepfe_beschriften()

    # --- Anlegen und Ändern -----------------------------------------------------------------

    def _anlegen(self):
        """Werkzeug-Controller und die angehakten Operationen in den Job – ein eigener Schritt
        Rückgängig, in einem Befehl (_im_befehl). Geht es nicht, steht der Grund rot im
        Fenster: False."""
        form = vr.modell(self.job).Shape
        aktive = self.aktive_bloecke()

        folge = []  # die weiteren Operationen eines Blocks (Schlichten danach: Boden und Wände)

        def anlegen():
            self.doc.openTransaction(tr("ba.transaktion.anlegen"))
            ops = []
            try:
                ue.uebergeben(self.bibliothek)
                if not self._job_dazu:  # im vorhandenen Job bleibt, was dort steht
                    fremde = js.unbenutzte_fremde_controller(self.job, self.bibliothek)
                    js.controller_weg(self.doc, fremde)
                tc_davor = None
                for block in aktive:
                    tc = js.controller_ohne_transaktion(
                        self.doc, self.job, block.fraeser(), block.einsatz(), self.werkstoff()
                    )
                    flaechen = self._flaechen(block, form)
                    werte = dict(block.werte(), **(self._zusatz(block, form) or {}))
                    werte["eintauchwinkel"] = _eintauchwinkel(block.fraeser())
                    if block is self.schlichten_danach:
                        neue = self._schlichten_danach_anlegen(tc, tc_davor or tc, werte)
                        ops.append(neue[0])
                        folge.extend(neue[1:])
                    else:
                        neue_op = block.s.lege_an(self.job, tc, werte, flaechen)
                        au.setze(neue_op, werte.get("aufloesung", 0.0))
                        ops.append(neue_op)
                    tc_davor = tc
                    # Gleich rechnen: Die nächste rechnet mit dem Material, das diese lässt
                    # (Materialstand, W-012) – FreeCAD rechnete sie sonst in beliebiger Folge.
                    self.doc.recompute()
                self.doc.recompute()
            except Exception:
                self.doc.abortTransaction()
                raise
            self.doc.commitTransaction()
            return ops

        try:
            self.operationen = _im_befehl(anlegen)
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"Bearbeitung: {fehler}\n")
            self.operationen = []
            self.operation = None
            self.hinweis.setText(tr("ba.fehler.anlegen", fehler=str(fehler)))
            self._knoepfe_beschriften()
            return False
        for block, op in zip(aktive, self.operationen, strict=False):
            block.operation = op
        self.operation = self.operationen[0] if self.operationen else None
        self.operationen += folge
        return True

    def _schlichten_danach_anlegen(self, tc, tc_davor, werte):
        """Die Operationen von „Schlichten danach“ – auf Wunsch der Messstopp (mit dem Controller
        davor, `tc_davor`), dann der Boden (ein Räumen ohne Aufmaß am Boden), dann die Wände (eine
        Kontur mit Breite = Aufmaß, nur der Zug an der Wand) – so viel davon, wie die Vorschau
        fand. In der Transaktion von _anlegen; gibt die neuen Operationen zurück."""
        bahn = self.schlichten_danach.vorschau
        werkzeug = f"T{tc.ToolNumber}"
        ops = []
        if werte.get("messstopp"):
            ops.append(ms.lege_an(self.job, tc_davor, tc))
        if getattr(bahn, "boden", None) is not None:
            ops.append(
                ra.lege_an(
                    self.job, tc, werte["zustellung"], werte["zeilenabstand"],
                    werte["aufmass_wand"], 0.0, werte["gleichlauf"],
                    name=tr("ba.schlichten_danach.boden_name", werkzeug=werkzeug),
                    flaechen=werte["boden_flaechen"],
                )  # fmt: skip
            )
            self.doc.recompute()  # die Wände rechnen mit dem fertigen Boden
        if getattr(bahn, "waende", None):
            aufmass = werte["aufmass_wand"]
            ops.append(
                ko.lege_an(
                    self.job, tc, werte["zustellung"], aufmass, aufmass, True, aufmass,
                    tr("ba.raeumen.schlichten_name", werkzeug=werkzeug), flaechen=bahn.waende,
                )  # fmt: skip
            )
        if not ops or (len(ops) == 1 and werte.get("messstopp")):
            raise ValueError(tr("ba.schlichten_danach.nichts"))
        return ops

    def _aendern(self):
        """Die Operation bekommt Fräser, Einsatz, Werte und Flächen aus ihrem Block – ein
        eigener Schritt Rückgängig; den alten Controller nimmt es heraus, wenn ihn keine
        Operation mehr benutzt. Geht es nicht, steht der Grund rot im Fenster: False."""
        op = self.zu_aendern
        block = self.block_zu_aendern
        form = vr.modell(self.job).Shape
        flaechen = block.s.flaechen_fuer(form, self.gewaehlte)
        werte = block.werte()
        werte["eintauchwinkel"] = _eintauchwinkel(block.fraeser())
        if block is self.gewindefraesen:
            werte["werkzeug"] = block.fraeser()  # Steigung und Zähne kennt CAM nicht

        def aendern():
            self.doc.openTransaction(tr("ba.transaktion.aendern"))
            try:
                ue.uebergeben(self.bibliothek)
                bisher = op.ToolController
                tc = js.controller_fuer(
                    self.doc, self.job, block.fraeser(), block.einsatz(), self.werkstoff(), op
                )
                block.s.aendere(op, tc, werte, flaechen)
                au.setze(op, werte.get("aufloesung", 0.0))
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
