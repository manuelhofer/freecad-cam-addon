# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Bohrung fräsen“ (W-006 S3g) – zylindrische Bohrungen mit einem
Schaftfräser in einer Helix hinab, bei großen Bohrungen je Lage Ringe nach außen, dann die Wand
in einem Zug geschlichtet (bohrung_bahn).

Wie „Räumen“ (raeumen) eine eigene Operation (erbt FreeCADs ObjectOp) mit Werkzeug-Controller,
Kühlmittel und FreeCADs Tiefen und Höhen. Beim Neuberechnen rechnet sie ihre Bahn aus Modell und
Rohteil des Jobs, mit dem Fräser aus dem ToolBit des Controllers und seinen Vorschüben für die
Zeit.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Schruppen“, sonst „Schlichten“. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import bahn as bn
from . import bohrung_bahn as bb
from . import kontur as ko
from . import namen
from . import planfraesen as pf
from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_planbahn as vp
from . import vierachs_schlichten as vs
from .sprache import tr

GRUPPE = "Fräsen"
ZUSTELLUNG = 2.0  # mm – Vorschlag, solange nichts anderes gesagt ist
AUFMASS = 0.3  # mm – bleibt an der Wand fürs Schlichten


class BohrungFraesen(PathOp.ObjectOp):
    """Proxy der Operation „Bohrung fräsen“."""

    def opFeatures(self, obj):
        return (
            PathOp.FeatureTool
            | PathOp.FeatureDepths
            | PathOp.FeatureHeights
            | PathOp.FeatureCoolant
        )

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Zustellung = ZUSTELLUNG
        obj.Zeilenabstand = 1.5
        obj.Aufmass = AUFMASS
        obj.AufmassBoden = 0.0
        obj.Schlichten = True
        obj.Gleichlauf = True
        obj.Tiefer = bb.TIEFER
        obj.Sicherheitsabstand = vb.SICHERHEIT
        obj.Eintauchwinkel = vb.EINTAUCHWINKEL
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        neu = []
        for typ, name, text in (
            ("App::PropertyStringList", "Flaechen", tr("bo.eigenschaft.flaechen")),
            ("App::PropertyLength", "Zustellung", tr("bo.eigenschaft.zustellung")),
            ("App::PropertyLength", "Zeilenabstand", tr("bo.eigenschaft.zeilenabstand")),
            ("App::PropertyLength", "Aufmass", tr("bo.eigenschaft.aufmass")),
            ("App::PropertyLength", "AufmassBoden", tr("ra.eigenschaft.aufmass_boden")),
            ("App::PropertyBool", "Schlichten", tr("bo.eigenschaft.schlichten")),
            ("App::PropertyBool", "Gleichlauf", tr("ra.eigenschaft.gleichlauf")),
            ("App::PropertyLength", "Tiefer", tr("bo.eigenschaft.tiefer")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyAngle", "Eintauchwinkel", tr("bo.eigenschaft.eintauchwinkel")),
            ("App::PropertyInteger", "Bohrungen", tr("bo.eigenschaft.bohrungen")),
            ("App::PropertyInteger", "Lagen", tr("pf.eigenschaft.lagen")),
            ("App::PropertyFloat", "Umlaeufe", tr("bo.eigenschaft.umlaeufe")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Bohrungen", "Lagen", "Umlaeufe"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(
                obj, self.job, self.model, self.horizFeed * 60.0, vo.eintauchvorschub(self)
            )
        except ValueError as fehler:
            obj.Bohrungen = obj.Lagen = 0
            obj.Umlaeufe = 0.0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Bohrungen, obj.Lagen = ergebnis.bohrungen, ergebnis.lagen
        obj.Umlaeufe = round(float(ergebnis.umlaeufe), 2)
        self.commandlist.extend(
            bn.befehle(ergebnis.punkte, self.horizFeed * 60.0, vo.eintauchvorschub(self))
        )


def rechne(obj, job, modell, vorschub=0.0, eintauchen=0.0):
    """Die Bahn (bohrung_bahn.Bohrbahn) für die Operation `obj` im Job. ValueError mit einem
    Satz, wenn es nicht geht."""
    form = vs.form_des_controllers(obj.ToolController)
    if form is None or vp.ebener_radius(form) <= 0:
        raise ValueError(tr("bo.fehler.form"))
    return bahn_fuer(
        job,
        modell,
        float(form.radius),
        float(obj.Zustellung),
        float(obj.Zeilenabstand),
        float(obj.Aufmass),
        vo.flaechen(obj),
        aufmass_boden=float(obj.AufmassBoden),
        schlichten=bool(obj.Schlichten),
        gleichlauf=sp.fuer_m3(obj.Gleichlauf, obj.ToolController),
        tiefer=float(obj.Tiefer),
        schneidenlaenge=ko.schneidenlaenge(obj.ToolController),
        oben=min(float(obj.StartDepth), pf.rohteil_von_oben(job)[4]),
        sicher=float(obj.SafeHeight),
        sicherheit=float(obj.Sicherheitsabstand),
        eintauchwinkel=float(obj.Eintauchwinkel),
        vorschub=vorschub,
        eintauchen=eintauchen,
    )


def bahn_fuer(
    job,
    modell,
    fraeser_radius,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    flaechen=(),
    aufmass_boden=0.0,
    schlichten=True,
    gleichlauf=True,
    tiefer=bb.TIEFER,
    schneidenlaenge=0.0,
    oben=None,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    eintauchwinkel=vb.EINTAUCHWINKEL,
    vorschub=0.0,
    eintauchen=0.0,
):
    """Die Bahn „Bohrung fräsen“ für Modell und Rohteil des Jobs. `flaechen`: die gewählten
    Zylinderflächen („Face7“ …); leer: alle Bohrungen des Teils. ValueError mit einem Satz, wenn
    es nicht geht."""
    form_teil = vs._teil(modell)
    *_rohteil, z_oben = pf.rohteil_von_oben(job)
    if oben is None:
        oben = z_oben
    if sicher is None:
        sicher = oben + sicherheit + 3.0
    liste = bb.bohrungen(form_teil, list(flaechen) or None)
    if not liste:
        raise ValueError(tr("bo.fehler.keine"))
    werte = bb.Bohrwerte(
        fraeser_radius=fraeser_radius,
        zustellung=zustellung,
        zeilenabstand=zeilenabstand,
        aufmass=aufmass,
        oben=oben,
        sicher=sicher,
        aufmass_boden=aufmass_boden,
        schlichten=schlichten,
        gleichlauf=gleichlauf,
        tiefer=tiefer,
        schneidenlaenge=schneidenlaenge,
        sicherheit=sicherheit,
        eintauchwinkel=eintauchwinkel,
        vorschub=vorschub,
        eintauchen=eintauchen,
    )
    return bb.planen(werte, liste)


def vorschau(job, modell, fraeser_radius, zustellung, zeilenabstand, aufmass, flaechen, **weiter):
    """Die Bahn für den Assistenten – dieselbe wie bahn_fuer() (sie braucht kein Raster)."""
    return bahn_fuer(
        job, modell, fraeser_radius, zustellung, zeilenabstand, aufmass, flaechen, **weiter
    )


def lege_an(
    job,
    tc,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    aufmass_boden=0.0,
    schlichten=True,
    gleichlauf=True,
    name=None,
    flaechen=(),
    eintauchwinkel=None,
):
    """Legt „Bohrung fräsen“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Tiefen
    und Höhen wie FreeCADs Operationen; die Endtiefe ist der tiefste Grund. Gibt die Operation
    zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "BohrungFraesen")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = BohrungFraesen(obj, "BohrungFraesen", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    obj.Zustellung = zustellung
    obj.Zeilenabstand = zeilenabstand
    obj.Aufmass = aufmass
    obj.AufmassBoden = aufmass_boden
    obj.Schlichten = bool(schlichten)
    obj.Gleichlauf = bool(gleichlauf)
    obj.Flaechen = list(flaechen)
    if eintauchwinkel:  # der Winkel am Fräser, wie in der Vorschau des Assistenten
        obj.Eintauchwinkel = float(eintauchwinkel)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(
        obj.Document, name or tr("bo.name", werkzeug=f"T{tc.ToolNumber}"), obj
    )
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _endtiefe(obj, job):
    """Die Endtiefe: der tiefste Grund der Bohrungen (durchgehende um „Tiefer“ darunter)."""
    try:
        form_teil = vs._teil(job.Model.Group)
        liste = bb.bohrungen(form_teil, list(obj.Flaechen) or None)
    except ValueError:
        liste = []
    if liste:
        tief = min(
            b.z_unten - float(obj.Tiefer) if b.durch else b.z_unten + float(obj.AufmassBoden)
            for b in liste
        )
        obj.setExpression("FinalDepth", None)
        obj.FinalDepth = tief


def aendere(
    obj,
    tc,
    zustellung,
    zeilenabstand,
    aufmass,
    aufmass_boden=0.0,
    schlichten=True,
    gleichlauf=True,
    flaechen=None,
    eintauchwinkel=None,
):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` ohne bleibt. Der Name folgt dem Werkzeug, solange es der
    vorgeschlagene ist."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, tr("bo.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Zustellung = zustellung
    obj.Zeilenabstand = zeilenabstand
    obj.Aufmass = aufmass
    obj.AufmassBoden = aufmass_boden
    obj.Schlichten = bool(schlichten)
    obj.Gleichlauf = bool(gleichlauf)
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    if eintauchwinkel:
        obj.Eintauchwinkel = float(eintauchwinkel)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Bohrung fräsen T1“) – auch mit „ (2)“ dahinter?"""
    return namen.nach_vorlage(name, tr("bo.name", werkzeug="\0"))


def ist_bohrungsfraesen(op):
    """Ist `op` eine Operation dieses Moduls – „Bohrung fräsen“?"""
    return isinstance(getattr(op, "Proxy", None), BohrungFraesen)
