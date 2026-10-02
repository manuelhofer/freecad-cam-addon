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

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, einheiten, symbol
from . import bahn as bn
from . import bleistift as bst
from . import bohren as bh
from . import bohrung as bo
from . import bohrung_bahn as bb
from . import entgrat_bahn as eb
from . import entgraten as eg
from . import fraeserform as ff
from . import gewinde as gw
from . import gewinde_bahn as gfb
from . import gewindefraesen as gf
from . import hoehenfeld as hf
from . import job_schnittwerte as js
from . import kontur as ko
from . import kontur_bahn as kb
from . import nut as nu
from . import nut_bahn as nb
from . import planfraesen as pf
from . import raeumen as ra
from . import raeumen_bahn as rb
from . import reiben as rbn
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
GEMERKT_FRAESER = "BaFraeser"  # Kennung des zuletzt gewählten Fräsers (Planfräsen)
GEMERKT_KONTURFRAESER = "BaKonturFraeser"  # … für die Kontur
GEMERKT_RAEUMFRAESER = "BaRaeumFraeser"  # … fürs Räumen
GEMERKT_NUTFRAESER = "BaNutFraeser"  # … für die Nut
GEMERKT_BOHRFRAESER = "BaBohrFraeser"  # … fürs Bohrungsfräsen
GEMERKT_BOHRER = "BaBohrer"  # … fürs Bohren
GEMERKT_REIBAHLE = "BaReibahle"  # … fürs Reiben
GEMERKT_GEWINDEBOHRER = "BaGewindebohrer"  # … fürs Gewinde
GEMERKT_GEWINDEFRAESER = "BaGewindefraeser"  # … fürs Gewindefräsen
GEMERKT_FASENFRAESER = "BaFasenfraeser"  # … fürs Entgraten
GEMERKT_ANBOHRER = "BaAnbohrer"  # … fürs Zentrieren
GEMERKT_SENKER = "BaSenker"  # … fürs Senken
GEMERKT_RESTFRAESER = "BaRestFraeser"  # … fürs Restmaterial
GEMERKT_FRAESER_3D = "BaFraeser3D"  # … fürs 3D-Schlichten
GEMERKT_RESTFRAESER_3D = "BaRestFraeser3D"  # … fürs Restschlichten
GEMERKT_RESTSCHRUPPFRAESER = "BaRestSchruppFraeser"  # … fürs Restschruppen
REST_BREITE = 0.01  # mm – „Material neben der Wand“ beim Restmaterial: eine Bahn bei Radius
VORSCHAU_MS = 400  # nach der letzten Eingabe so lange warten, dann die Bahn rechnen
NACHZIEHEN_MS = 250  # das Rohteil nach einer Eingabe nachziehen
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


def _grau(text=""):
    """Ein grauer Satz – Erklärungen und gerechnete Werte (wie in gui_vierachs)."""
    etikett = QtGui.QLabel(text)
    etikett.setStyleSheet(f"color: {GRAU_TEXT};")
    etikett.setWordWrap(True)
    return etikett


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


def ist_bearbeitung(op):
    """Eine Operation dieses Assistenten – „Planfräsen“, „Räumen“, „Nut“, „Bohrung fräsen“,
    „Kontur“, „Entgraten“, „Gewinde fräsen“, „3D-Schruppen“, „3D-Schlichten“ oder
    „Bleistift“?"""
    return (
        s3op.ist_schlichten3d(op)
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
        FreeCADGui.Control.showDialog(BearbeitungPanel(dokument, gewaehlte_flaeche(dokument)))


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


# --- Die Strategien ---------------------------------------------------------------------------


class _Strategie:
    """Eine 2,5D-Strategie im Assistenten: ihre Texte, Felder, Vorschläge, Vorschau, Anlegen
    und Ändern. Die Schlüssel stehen wörtlich in tr(…) – so findet sie die Sprachprüfung."""

    kennung = ""
    gemerkt = ""  # Parameter: der zuletzt gewählte Fräser
    einsatz_reihenfolge = ()  # welcher Einsatz vorgewählt ist
    bevorzugt = wz.SCHAFTFRAESER  # diese Art vorgewählt, wenn sonst nichts entscheidet

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
    gemerkt = GEMERKT_FRAESER
    einsatz_reihenfolge = (wz.PLANEN, wz.SCHRUPPEN, wz.SCHLICHTEN)

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
        )

    def aendere(self, op, tc, werte, flaechen):
        pf.aendere(
            op, tc, werte["zustellung"], werte["zeilenabstand"], werte["aufmass"], flaechen=flaechen
        )

    def ist(self, op):
        return pf.ist_planfraesen(op)

    def werte_von(self, op):
        return {
            "zustellung": float(op.Zustellung),
            "zeilenabstand": float(op.Zeilenabstand),
            "aufmass": float(op.Aufmass),
        }


class _Raeumen(_Strategie):
    kennung = "raeumen"
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
        return ra.vorschau(
            job,
            job.Model.Group,
            ff.von_werkzeug(werkzeug),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            flaechen,
            aufmass_boden=werte["aufmass_boden"],
            gleichlauf=werte["gleichlauf"],
            schneidenlaenge=float(werkzeug.schneidenlaenge or 0.0),
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
        )

    def ergebnis_text(self, bahn, zeit):
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        ringe = tr("ba.zahl.ring") if bahn.ringe == 1 else tr("ba.zahl.ringe", n=bahn.ringe)
        if bahn.flaechen > 1:
            flaechen = tr("ba.zahl.flaechen", n=bahn.flaechen)
            return tr(
                "ba.ergebnis_raeumen_flaechen",
                flaechen=flaechen,
                lagen=lagen,
                ringe=ringe,
                zeit=zeit,
            )
        return tr("ba.ergebnis_raeumen", lagen=lagen, ringe=ringe, zeit=zeit)

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


class _Nut(_Strategie):
    """Langlöcher in Kreisen (Trochoide) oder mit der Zickzack-Rampe (nut_bahn) – tritt auf dem
    Grund gegen Räumen und Planfräsen an, an den Wänden gegen die Kontur."""

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
            eintauchwinkel=float(werkzeug.eintauchwinkel or 0.0) or vb.EINTAUCHWINKEL,
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
        )

    def ergebnis_text(self, bahn, zeit):
        nuten = tr("ba.zahl.nut") if bahn.nuten == 1 else tr("ba.zahl.nuten", n=bahn.nuten)
        if bahn.vollnut == bahn.nuten:
            return tr("ba.ergebnis_vollnut", nuten=nuten, zeit=zeit)
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        kreise = tr("ba.zahl.kreis") if bahn.kreise == 1 else tr("ba.zahl.kreise", n=bahn.kreise)
        return tr("ba.ergebnis_nut", nuten=nuten, lagen=lagen, kreise=kreise, zeit=zeit)

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
        }


class _Kontur(_Strategie):
    kennung = "kontur"
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
            eintauchwinkel=float(werkzeug.eintauchwinkel or 0.0) or vb.EINTAUCHWINKEL,
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
        return False  # ob der kleine Fräser nachkommt, entscheidet man selbst

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


class _Schlichten3D(_Strategie):
    """Freiformflächen in parallelen Zeilen auf der Hüllfläche des ganzen Teils
    (schlichten3d_bahn) – am liebsten mit dem Kugelfräser; gegen keine Strategie im Wettbewerb."""

    kennung = "schlichten3d"
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
        return s3op.vorschau(
            job,
            job.Model.Group,
            form,
            werte["grathoehe"],
            flaechen,
            aufmass=werte["aufmass"],
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
        )

    def ergebnis_text(self, bahn, zeit):
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
        return s3op.lege_an(job, tc, werte["grathoehe"], werte["aufmass"], flaechen=flaechen)

    def aendere(self, op, tc, werte, flaechen):
        s3op.aendere(op, tc, werte["grathoehe"], werte["aufmass"], flaechen=flaechen)

    def ist(self, op):
        return s3op.ist_schlichten3d(op) and not s3op.ist_restschlichten(op)

    def werte_von(self, op):
        return {"grathoehe": float(op.Grathoehe), "aufmass": float(op.Aufmass)}


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
        return s3op.lege_an(
            job,
            tc,
            werte["grathoehe"],
            werte["aufmass"],
            flaechen=flaechen,
            davor=self.davor(werte),
        )

    def aendere(self, op, tc, werte, flaechen):
        s3op.aendere(
            op, tc, werte["grathoehe"], werte["aufmass"], flaechen=flaechen, davor=self.davor(werte)
        )

    def ist(self, op):
        return s3op.ist_restschlichten(op)

    def werte_von(self, op):
        return {
            "davor": float(op.DurchmesserDavor),
            "grathoehe": float(op.Grathoehe),
            "aufmass": float(op.Aufmass),
        }


class _Bleistift(_Strategie):
    """Die Kehlen der Freiformflächen nachfahren, wo der Kugelfräser zwei Flächen zugleich
    berührt (bleistift_bahn) – nach dem 3D-Schlichten, mit demselben Fräser; den Haken setzt man
    selbst."""

    kennung = "bleistift"
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
        return (("aufmass", tr("ba.aufmass"), tr("ba.bs.aufmass.tooltip")),)

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
        )

    def ergebnis_text(self, bahn, zeit):
        kehlen = tr("ba.zahl.kehle") if bahn.linien == 1 else tr("ba.zahl.kehlen", n=bahn.linien)
        laenge = groesse_zeigen(bahn.laenge, einheiten.LAENGE, 0) or "0"
        einheit = einheiten.einheit(einheiten.LAENGE)
        return tr("ba.ergebnis_bs", kehlen=kehlen, laenge=f"{laenge} {einheit}", zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return bst.lege_an(job, tc, werte["aufmass"], flaechen=flaechen)

    def aendere(self, op, tc, werte, flaechen):
        bst.aendere(op, tc, werte["aufmass"], flaechen=flaechen)

    def ist(self, op):
        return bst.ist_bleistift(op)

    def werte_von(self, op):
        return {"aufmass": float(op.Aufmass)}


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
    _Nut,
    _Zentrieren,
    _Bohren,
    _Bohrung,
    _Kontur,
    _Rest,
    _Schruppen3D,
    _Restschruppen,
    _Schlichten3D,
    _Restschlichten,
    _Bleistift,
    _Senken,
    _Reiben,
    _Gewinde,
    _Gewindefraesen,
    _Entgraten,
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
        self.zeit = None  # Minuten der Vorschau (bahn.zeit) – für den Wettbewerb
        self.ergebnis_basis = ""  # die Ergebniszeile ohne den Vergleich
        self.operation = None  # die angelegte Operation
        self.von_hand = False  # der Haken ist von Hand gesetzt – kein Vorschlag mehr
        self.moeglich = True  # die Strategie geht mit der Wahl der Flächen
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
        self.erklaerung = _grau(strategie.text())
        aufbau.addWidget(self.erklaerung)
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
        self.felder = {}
        for feld, text, tooltip in strategie.felder():
            _zahlenfeld(self.felder, feld, text, tooltip, self.reihen, self.panel.vorschau_starten)
        self.haken_felder = {}
        for feld, text, tooltip, vorgabe in strategie.haken():
            kasten = QtGui.QCheckBox(text)
            kasten.setToolTip(tooltip)
            kasten.setChecked(vorgabe)
            kasten.toggled.connect(lambda _an: self.panel.vorschau_starten())
            self.haken_felder[feld] = kasten
            self.reihen.ganz(kasten)
        innen.addWidget(self.reihen.widget)
        self.ergebnis = _grau()
        innen.addWidget(self.ergebnis)
        self.hinweis = QtGui.QLabel()
        self.hinweis.setWordWrap(True)
        self.hinweis.setStyleSheet(f"color: {ROT};")
        innen.addWidget(self.hinweis)
        aufbau.addWidget(self.inhalt)

    # --- Zustand ---

    def aktiv(self):
        """Angehakt und möglich: Die Strategie wird gerechnet und angelegt (beim Ändern ist der
        Haken gesetzt und gesperrt)."""
        return self.moeglich and self.haken.isChecked()

    def zustand_zeigen(self):
        self.inhalt.setEnabled(self.aktiv())

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

    def werte(self):
        werte = {feld: self.wert(feld) for feld in self.felder}
        werte.update({feld: kasten.isChecked() for feld, kasten in self.haken_felder.items()})
        return werte

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

    def fraeser_fuellen(self, bibliothek, werkstoff):
        """Die Werkzeuge, mit denen die Strategie arbeitet (_Strategie.werkzeug_passt: Fräser mit
        ebener Stirn, beim Bohren Bohrer), mit Schnittwerten für den Werkstoff; vorgewählt der
        bisher gewählte, beim Ändern der der Operation, sonst der zuletzt benutzte, sonst
        einer mit dem ersten Einsatz der Reihenfolge, sonst ein Schaftfräser."""
        vorher = self.fraeser()
        self._fraeser = [
            w
            for w in sorted(bibliothek.werkzeuge, key=lambda w: w.nummer)
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
        elif gemerkt in kennungen:
            wahl = kennungen.index(gemerkt)
        else:
            wahl = min(
                range(len(self._fraeser)),
                key=lambda i: (
                    not any(
                        e.art == erster
                        for e in self._passende_einsaetze(self._fraeser[i], werkstoff)
                    ),
                    self._fraeser[i].art != self.s.bevorzugt,
                    i,
                ),
                default=0,
            )
        self.panel._fuellt = True
        try:
            self.wahl_fraeser.clear()
            for werkzeug in self._fraeser:
                self.wahl_fraeser.addItem(dezimal(wz.zeile(werkzeug)))
            if self._fraeser:
                self.wahl_fraeser.setCurrentIndex(wahl)
        finally:
            self.panel._fuellt = False
        self.einsatz_fuellen(werkstoff)

    def _fraeser_gewaehlt(self):
        if not self.panel._fuellt:
            self.einsatz_fuellen(self.panel.werkstoff())

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
            n, vf, _senkrecht = js.werte(werkzeug, einsatz)
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
        self.ergebnis_basis = ""
        self.ergebnis.setText("")
        self.hinweis.setText("")
        werkzeug, einsatz = self.fraeser(), self.einsatz()
        if werkzeug is None or einsatz is None:
            self.hinweis.setText(tr("va.planfraeser.keiner"))
            return
        _n, vorschub, senkrecht = js.werte(werkzeug, einsatz)
        werte = dict(self.werte(), vorschub=vorschub, eintauchen=senkrecht, **(zusatz or {}))
        try:
            self.vorschau = self.s.vorschau(job, werkzeug, werte, flaechen)
        except (ValueError, RuntimeError) as fehler:  # RuntimeError: OCC am Netz
            self.hinweis.setText(str(fehler))
            return
        self.zeit = bn.zeit(self.vorschau.punkte, vorschub, senkrecht) if vorschub > 0 else None
        zeit = _zeit_text(self.zeit) if self.zeit is not None else "?"
        self.ergebnis_basis = self.s.ergebnis_text(self.vorschau, zeit)
        self.ergebnis.setText(self.ergebnis_basis)

    def leeren(self):
        self.vorschau = None
        self.zeit = None
        self.ergebnis_basis = ""
        self.ergebnis.setText("")
        self.hinweis.setText("")


class BearbeitungPanel:
    """Aufgabenfenster „Bearbeitung (Fräsen)“ – anlegen, oder mit `operation=` ändern."""

    offen = None  # das offene Fenster – für die Oberflächen-Szenarien

    def __init__(self, dokument, wahl=None, operation=None):
        BearbeitungPanel.offen = self
        self.doc = dokument
        self.job = None
        self.teil = None
        self.bibliothek = None
        self.gewaehlte = []  # die Flächen („Face6“ …) – leer: die Oberseite
        self.operation = operation  # die erste angelegte Operation – oder die, die man ändert
        self.operationen = []  # alle angelegten
        self.zu_aendern = operation
        self.block_zu_aendern = None
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
        self._nullpunkt_uhr = QtCore.QTimer()
        self._nullpunkt_uhr.setSingleShot(True)
        self._nullpunkt_uhr.setInterval(NACHZIEHEN_MS)
        self._nullpunkt_uhr.timeout.connect(self._nullpunkt_anwenden)
        self._nullpunkte = nullpunkte()
        self.bloecke = []
        self.form = self._baue()
        self.plan = next(b for b in self.bloecke if b.s.kennung == "planfraesen")
        self.raeumen = next(b for b in self.bloecke if b.s.kennung == "raeumen")
        self.nut = next(b for b in self.bloecke if b.s.kennung == "nut")
        self._raeumen_boeden = None  # nur diese Taschenböden räumen (_folge); None: alle
        self.bohren = next(b for b in self.bloecke if b.s.kennung == "bohren")
        self.bohrung = next(b for b in self.bloecke if b.s.kennung == "bohrung")
        self.kontur = next(b for b in self.bloecke if b.s.kennung == "kontur")
        self.gewinde = next(b for b in self.bloecke if b.s.kennung == "gewinde")
        self.gewindefraesen = next(b for b in self.bloecke if b.s.kennung == "gewindefraesen")
        self.entgraten = next(b for b in self.bloecke if b.s.kennung == "entgraten")
        self.zentrieren = next(b for b in self.bloecke if b.s.kennung == "zentrieren")
        self.senken = next(b for b in self.bloecke if b.s.kennung == "senken")
        self.reiben = next(b for b in self.bloecke if b.s.kennung == "reiben")
        self.schlichten3d = next(b for b in self.bloecke if b.s.kennung == "schlichten3d")
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
            eingabe = _zahlenfeld(
                self.felder_rohteil, feld, text, tooltip, rohteil, self._rohteil_geaendert
            )
            eingabe.setPlaceholderText(groesse_zeigen(AUFMASS_ROHTEIL, einheiten.LAENGE) or "0")
        self.rohteilfelder = rohteil.widget
        aufbau.addWidget(self.rohteilfelder)

        # --- Nullpunkt ---
        self.nullpunkt_titel = titel(tr("ba.nullpunkt"), tr("ba.nullpunkt.text"))
        self.nullpunkt_text = grautext(tr("ba.nullpunkt.text"))
        nullpunkt = _Reihen()
        self.wahl_nullpunkt = QtGui.QComboBox()
        self.wahl_nullpunkt.addItem(tr("ba.nullpunkt.modell"), 0)
        for nummer, (text, _lage) in enumerate(self._nullpunkte, start=1):
            self.wahl_nullpunkt.addItem(text, nummer)
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
        aufbau.addWidget(self.nullpunktfelder)

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

        # --- Die Bearbeitungen: je Strategie ein Block mit Haken ---
        for strategie in STRATEGIEN:
            block = _Block(self, strategie())
            self.bloecke.append(block)
            aufbau.addWidget(block.widget)
        self.hinweis = QtGui.QLabel()
        self.hinweis.setWordWrap(True)
        self.hinweis.setStyleSheet(f"color: {ROT};")
        aufbau.addWidget(self.hinweis)
        # Die Beschriftungen aller Blöcke gleich breit: die Felder stehen untereinander.
        reihen = [oben, rohteil, nullpunkt, werkstoff] + [b.reihen for b in self.bloecke]
        breite = max(r.breite_beschriftung() for r in reihen)
        for r in reihen:
            r.raster.setColumnMinimumWidth(0, breite)
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
        self._nullpunkt_uhr.stop()
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
        eben nach oben oder eine Wand, ist sie gewählt, sonst die Oberseite."""
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
        if self.nullpunkt() is not None or self._nullpunkt_versatz().Length > 0:
            self._nullpunkt_setzen(self.job)
        form = vr.modell(self.job).Shape
        if flaeche and any(b.s.passt(form, flaeche) for b in self.bloecke):
            self.gewaehlte = [flaeche]
        else:
            self.gewaehlte = []
        FreeCADGui.Selection.clearSelection()
        self._bearbeitung_fuellen()
        self._flaechen_zeigen()
        self._auffrischen()
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
        self.doc.recompute()
        if _globale_transaktionen():
            FreeCAD.setActiveTransaction(tr("ba.titel"), True)
        return job

    def _rohteil_setzen(self, job):
        """Das Rohteil des Jobs mit dem Aufmaß aus den Feldern – ein Quader um das Teil."""
        rohteil = getattr(job, "Stock", None)
        if rohteil is None or not hasattr(rohteil, "ExtZpos"):
            return
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

    def _rohteil_geaendert(self):
        if not self._fuellt and self.job is not None and self.zu_aendern is None:
            self._rohteil_uhr.start()

    def _rohteil_anwenden(self):
        if self.job is None or self.zu_aendern is not None or self.geschlossen:
            return
        self._rohteil_setzen(self.job)
        self.doc.recompute()
        self._nullpunkt_setzen(self.job)  # die Ecken des Rohteils sind gewandert
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
        if not self._fuellt and self.job is not None and self.zu_aendern is None:
            self._nullpunkt_uhr.start()

    def _nullpunkt_anwenden(self):
        if self.job is None or self.zu_aendern is not None or self.geschlossen:
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
        if lage is not None:
            bb = teil.Shape.BoundBox
            werte = {feld: self._rohteil_wert(feld) for feld in ROHTEIL_FELDER}
            unten = (bb.XMin - werte["seite"], bb.YMin - werte["seite"], bb.ZMin - werte["unten"])
            oben = (bb.XMax + werte["seite"], bb.YMax + werte["seite"], bb.ZMax + werte["oben"])
            punkt = FreeCAD.Vector(
                *(
                    (u + o) / 2 if s == 0 else (o if s > 0 else u)
                    for s, u, o in zip(lage, unten, oben, strict=True)
                )
            )
            punkt = punkt + self._nullpunkt_versatz()
        neu = FreeCAD.Placement(punkt * -1.0, FreeCAD.Rotation()).multiply(teil.Placement)
        alt = klon.Placement
        if (alt.Base - neu.Base).Length < 1e-9 and alt.Rotation.isSame(neu.Rotation, 1e-9):
            return
        klon.Placement = neu
        self.doc.recompute()
        rohteil = getattr(job, "Stock", None)
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
        rohteil = getattr(self.job, "Stock", None)
        self._fuellt = True
        try:
            if rohteil is not None and hasattr(rohteil, "ExtZpos"):
                for feld, name in (("oben", "ExtZpos"), ("seite", "ExtXpos"), ("unten", "ExtZneg")):
                    wert = _mm(getattr(rohteil, name))
                    self.felder_rohteil[feld].setText(groesse_zeigen(wert, einheiten.LAENGE) or "0")
            for anderer in self.bloecke:
                if anderer is not block:
                    anderer.widget.setVisible(False)
                    anderer.haken.setChecked(False)
            block.haken.setChecked(True)
            block.haken.setEnabled(False)
            block.von_hand = True
        finally:
            self._fuellt = False
        self.rohteilfelder.setEnabled(False)
        for widget in (self.nullpunkt_titel, self.nullpunkt_text, self.nullpunktfelder):
            widget.setVisible(False)  # der Nullpunkt bleibt, wie er im Job steht
        self.gewaehlte = list(getattr(op, "Flaechen", ()) or ())
        self._bearbeitung_fuellen()
        self._fuellt = True
        try:
            for feld, wert in block.s.werte_von(op).items():
                if feld in block.haken_felder:
                    block.haken_felder[feld].setChecked(bool(wert))
                    continue
                wert = float(wert)
                if abs(wert - block.vorschlag(feld)) > 1e-6:
                    block.felder[feld].setText(groesse_zeigen(wert, einheiten.LAENGE) or "0")
        finally:
            self._fuellt = False
        self._flaechen_zeigen()
        self._auffrischen()
        self.vorschau_starten()

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
        self.vorschau_starten()

    def oberseite_waehlen(self):
        if self.job is None:
            return
        self.gewaehlte = hf.oberseite(vr.modell(self.job).Shape)
        self._flaechen_zeigen()
        self.vorschau_starten()

    def flaechen_leeren(self):
        self.gewaehlte = []
        self._flaechen_zeigen()
        self.vorschau_starten()

    def flaechen(self):
        """Die gewählten Flächen („Face6“ …) – leer: die Oberseite."""
        return list(self.gewaehlte)

    def _flaechen_zeigen(self):
        """Die Liste der gewählten Flächen, der Satz darunter, die Farben am Teil – und die
        Haken der Blöcke, wie die Wahl sie nahelegt."""
        self.flaechen_liste.clear()
        self.flaechen_liste.setVisible(bool(self.gewaehlte))
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
            elif self.schlichten3d.s.passt(form, name):
                z = groesse_zeigen(form.Faces[nummer].BoundBox.ZMin, einheiten.LAENGE) or "0"
                text, farbe = tr("ba.flaeche.freiform", name=name, z=z), GRUEN
            elif eb.ist_fase(form, name):
                text, farbe = tr("ba.flaeche.fase", name=name), GRUEN
            else:
                text, farbe = tr("ba.flaeche.nichts", name=name), ROT
            eintrag = QtGui.QListWidgetItem(dezimal(text))
            eintrag.setData(QtCore.Qt.UserRole, name)
            eintrag.setForeground(QtGui.QColor(farbe))
            self.flaechen_liste.addItem(eintrag)
            if nummer >= 0:
                farben[nummer] = farbe
        if not self.gewaehlte:
            namen = ", ".join(hf.oberseite(form)) or "–"
            self.flaechen_text.setText(tr("ba.flaechen.oberseite", namen=namen))
        else:
            self.flaechen_text.setText(tr("ba.flaechen.nur"))
        self._farben_zeigen(farben)
        self._haken_vorschlagen(form)

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
        self._fuellt = True
        try:
            for block in self.bloecke:
                moeglich = block.s.moeglich(form, self.gewaehlte)
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
                if block in (self.entgraten, self.zentrieren):
                    moeglich = moeglich and bool(block._fraeser)
                if block is self.senken:
                    moeglich = moeglich and self._senker_da(form)
                block.moeglich = moeglich
                block.haken.setEnabled(moeglich)
                block.erklaerung.setText(
                    block.s.text() if moeglich else grund or block.s.unmoeglich_text()
                )
                if not moeglich:
                    block.haken.setChecked(False)
                elif not block.von_hand:
                    vorschlag = block.s.vorgeschlagen(form, self.gewaehlte)
                    if block is self.bohrung and self._von_raeumen_geraeumt(form):
                        vorschlag = False  # Räumen + Kontur ist dort die Folge
                    block.haken.setChecked(vorschlag)
                block.zustand_zeigen()
        finally:
            self._fuellt = False
        self._restfraeser_waehlen()
        self._restschlichtfraeser_waehlen()

    def haken_geklickt(self, block):
        if self._fuellt:
            return
        block.von_hand = True
        block.zustand_zeigen()
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
        if self._fuellt or self.geschlossen:
            return
        for block in self.bloecke:
            block.vorschau = None
        self._vorschau_uhr.start()
        self._knoepfe_beschriften()

    def _vorschau_rechnen(self):
        """Die grobe Bahn je angehaktem Block – und damit „Anlegen“ weiß, ob es geht."""
        self._vorschau_uhr.stop()
        if self.geschlossen or self.job is None:
            return
        form = vr.modell(self.job).Shape
        self._raeumen_boeden = None
        boeden = self._nur_boeden(form)
        for block in self.bloecke:
            if (
                block is self.raeumen
                and boeden is not None
                and (block.aktiv() or self._im_wettbewerb(block))
            ):
                self._folge(form, boeden)
                continue
            if block.aktiv() or self._im_wettbewerb(block):
                zusatz = self._zusatz(block, form)
                block.vorschau_rechnen(self.job, self._flaechen(block, form), zusatz)
                if block is self.kontur and zusatz and block.ergebnis_basis:
                    block.ergebnis.setText(tr("ba.kontur.nach_raeumen", text=block.ergebnis_basis))
                if block is self.bohren and zusatz and block.ergebnis_basis:
                    d = groesse_zeigen(block.fraeser().durchmesser, einheiten.LAENGE) or "0"
                    block.ergebnis.setText(
                        tr("ba.bohren.vorbohren", text=block.ergebnis_basis, d=d)
                    )
            else:
                block.leeren()
        self._wettbewerb(form, nur_bohrung=boeden is not None)
        self._knoepfe_beschriften()

    def _zusatz(self, block, form):
        """Was der Assistent einem Block vorgibt: Räumt das Räumen den Boden einer Tasche, deren
        Wände die Kontur fährt, und ist die Breite der Kontur leer, dann steht neben den Wänden
        nur noch das Aufmaß des Räumens – die Kontur schlichtet nur noch (Räumen + Kontur mit
        Breite = Aufmaß, die schnellste Folge in der Tasche; Spezifikation Abschnitt 11)."""
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
        if block is self.restschruppen:
            return self._davor_3d(self.restschruppen, self.schruppen3d)
        if block is not self.kontur or not self.raeumen.aktiv():
            return None
        if self.kontur.felder["breite"].text().strip():
            return None  # von Hand eingetragen
        waende = self.kontur.s.flaechen_fuer(form, self.gewaehlte)
        boeden = rb.taschenboeden(form, waende)
        if not boeden or not set(boeden) & set(self._flaechen(self.raeumen, form)):
            return None
        return {"breite": max(float(self.raeumen.werte()["aufmass"]), 0.01)}

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

    def _flaechen(self, block, form):
        """Die Flächen des Blocks – beim Räumen ohne die, die das Planfräsen schon fräst
        (_folge: dann nur die Taschenböden); beim Bohrungsfräsen ohne die, die das Bohren
        bohrt, wenn beide nicht um dieselben Bohrungen wetteifern (ein Flansch: der Bohrer die
        Lochkreisbohrungen, der Fräser die große in der Mitte; P-2026-10-02-12)."""
        flaechen = self._eigene(block, form)
        if block is self.raeumen and self._raeumen_boeden is not None:
            return list(self._raeumen_boeden)
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
            if not self._gleiche_flaechen(block, form):
                for anderer in (self.bohren, self.bohrung, self.nut):
                    if anderer.aktiv():
                        weg |= set(anderer.s.flaechen_fuer(form, self.gewaehlte))
            return [f for f in flaechen if f not in weg]
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
        return block.s.flaechen_fuer(form, self.gewaehlte)

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

    def _nutfraeser_waehlen(self, form):
        """Wählt im Block Nut einen Fräser, der in die gewählten Nuten passt, wenn der gewählte es
        nicht tut – am liebsten den größten, der Kreise fährt (Trochoide), sonst den größten, der
        hineinpasst; und den Einsatz dazu: „Vollnut“ zuerst, wenn er sie in voller Breite fräst."""
        namen = [n for n in self.gewaehlte if nb.ist_nut(form, n)]
        liste = nb.nuten(form, namen) if namen else []
        if not liste:
            return
        block = self.nut
        aufmass = block.wert("aufmass") if block.haken_felder["schlichten"].isChecked() else 0.0

        def arten(w):
            return {nb.verfahren(n, w.durchmesser / 2, aufmass) for n in liste}

        geht = {"trochoide", "vollnut"}
        wahl = block.wahl_fraeser.currentIndex()
        jetzt = block.fraeser()
        if jetzt is None or not arten(jetzt) <= geht:
            kreise = [i for i, w in enumerate(block._fraeser) if arten(w) == {"trochoide"}]
            passen = [i for i, w in enumerate(block._fraeser) if arten(w) <= geht]
            if kreise or passen:
                wahl = max(kreise or passen, key=lambda i: block._fraeser[i].durchmesser)
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
        if not plan.aktiv() and (plan.von_hand or not plan.moeglich):
            raeumen.vorschau_rechnen(self.job, raeumen.s.flaechen_fuer(form, self.gewaehlte))
            return
        if plan.vorschau is None:
            plan.vorschau_rechnen(self.job, plan.s.flaechen_fuer(form, self.gewaehlte))
        raeumen.vorschau_rechnen(self.job, raeumen.s.flaechen_fuer(form, self.gewaehlte))
        alles = (raeumen.vorschau, raeumen.zeit, raeumen.ergebnis_basis, raeumen.hinweis.text())
        raeumen.vorschau_rechnen(self.job, boeden)
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
        voll = []
        if self.nut in mit and self._nur_nutgruende(form):
            voll = [b for b in mit if b in (self.plan, self.raeumen)]
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
        schnellste.ergebnis.setText(
            tr(
                "ba.wettbewerb.schnellste",
                text=schnellste.ergebnis_basis,
                andere=zweite.s.titel(),
                prozent=int(round((zweite.zeit / schnellste.zeit - 1.0) * 100.0)),
            )
        )
        for langsamer in mit[1:]:
            langsamer.ergebnis.setText(
                tr(
                    "ba.wettbewerb.langsamer",
                    text=langsamer.ergebnis_basis,
                    andere=schnellste.s.titel(),
                    prozent=int(round((langsamer.zeit / schnellste.zeit - 1.0) * 100.0)),
                )
            )
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

        def anlegen():
            self.doc.openTransaction(tr("ba.transaktion.anlegen"))
            ops = []
            try:
                ue.uebergeben(self.bibliothek)
                fremde = js.unbenutzte_fremde_controller(self.job, self.bibliothek)
                js.controller_weg(self.doc, fremde)
                for block in aktive:
                    tc = js.controller_ohne_transaktion(
                        self.doc, self.job, block.fraeser(), block.einsatz(), self.werkstoff()
                    )
                    flaechen = self._flaechen(block, form)
                    werte = dict(block.werte(), **(self._zusatz(block, form) or {}))
                    ops.append(block.s.lege_an(self.job, tc, werte, flaechen))
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
        return True

    def _aendern(self):
        """Die Operation bekommt Fräser, Einsatz, Werte und Flächen aus ihrem Block – ein
        eigener Schritt Rückgängig; den alten Controller nimmt es heraus, wenn ihn keine
        Operation mehr benutzt. Geht es nicht, steht der Grund rot im Fenster: False."""
        op = self.zu_aendern
        block = self.block_zu_aendern
        form = vr.modell(self.job).Shape
        flaechen = block.s.flaechen_fuer(form, self.gewaehlte)
        werte = block.werte()
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
