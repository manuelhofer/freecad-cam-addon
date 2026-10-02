# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „3D-Schruppen“ (W-006 4.2 Punkt 1) – das Rohteil über Freiformflächen in
Lagen wegräumen: Hauptlagen bei vollem ap und schmalem ae wie das Räumen, dazwischen
Zwischenlagen nur dort, wo über der Fläche noch eine Treppe steht (schruppen3d_bahn). Mit dem
Durchmesser des Fräsers davor (`DurchmesserDavor` > 0) ist sie „Restschruppen“ (W-006 4.2
Punkt 2): nur, was der größere Fräser davor stehen ließ.

Wie „Räumen“ eine eigene Operation (erbt FreeCADs ObjectOp) mit Werkzeug-Controller,
Kühlmittel und FreeCADs Tiefen und Höhen. Beim Neuberechnen rechnet sie ihre Bahn aus Modell
und Rohteil des Jobs, mit dem Fräser aus dem ToolBit des Controllers und seinen Vorschüben für
die Zeit.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Schruppen“. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import bahn as bn
from . import fraeserform as ff
from . import hoehenfeld as hf
from . import kontur as ko
from . import materialstand as mst
from . import namen
from . import planfraesen as pf
from . import raeumen as ra
from . import raeumen_bahn as rb
from . import schruppen3d_bahn as sr
from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from .sprache import tr

GRUPPE = "Fräsen"
AUFMASS = ra.AUFMASS


class Schruppen3D(PathOp.ObjectOp):
    """Proxy der Operation „3D-Schruppen“."""

    def opFeatures(self, obj):
        return (
            PathOp.FeatureTool
            | PathOp.FeatureDepths
            | PathOp.FeatureHeights
            | PathOp.FeatureCoolant
        )

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Zustellung = ra.ZUSTELLUNG
        obj.Zeilenabstand = 1.5
        obj.Aufmass = AUFMASS
        obj.Zwischenlagen = sr.ZWISCHEN
        obj.Gleichlauf = True
        obj.Sicherheitsabstand = vb.SICHERHEIT
        obj.Eintauchwinkel = vb.EINTAUCHWINKEL
        obj.DurchmesserDavor = 0.0  # 0: das ganze Rohteil; sonst Restschruppen
        obj.EckenradiusDavor = 0.0
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        neu = []
        for typ, name, text in (
            ("App::PropertyStringList", "Flaechen", tr("r3.eigenschaft.flaechen")),
            ("App::PropertyLength", "Zustellung", tr("ra.eigenschaft.zustellung")),
            ("App::PropertyLength", "Zeilenabstand", tr("ra.eigenschaft.zeilenabstand")),
            ("App::PropertyLength", "Aufmass", tr("r3.eigenschaft.aufmass")),
            ("App::PropertyLength", "Zwischenlagen", tr("r3.eigenschaft.zwischenlagen")),
            ("App::PropertyBool", "Gleichlauf", tr("ra.eigenschaft.gleichlauf")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyAngle", "Eintauchwinkel", tr("vo.eigenschaft.eintauchwinkel")),
            ("App::PropertyInteger", "Lagen", tr("r3.eigenschaft.lagen")),
            ("App::PropertyInteger", "Zwischen", tr("r3.eigenschaft.zwischen")),
            ("App::PropertyInteger", "Ringe", tr("ra.eigenschaft.ringe")),
            ("App::PropertyLength", "DurchmesserDavor", tr("r3.eigenschaft.davor")),
            ("App::PropertyLength", "EckenradiusDavor", tr("r3.eigenschaft.eckenradius_davor")),
            ("App::PropertyString", "Materialstand", tr("ms.eigenschaft.materialstand")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Lagen", "Zwischen", "Ringe"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis
        obj.setEditorMode("Materialstand", 2)  # woraus gerechnet (gui_materialstand)

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(
                obj, self.job, self.model, self.horizFeed * 60.0, vo.eintauchvorschub(self)
            )
        except ValueError as fehler:
            obj.Lagen = obj.Zwischen = obj.Ringe = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Lagen, obj.Zwischen, obj.Ringe = (
            ergebnis.lagen,
            ergebnis.zwischenlagen,
            ergebnis.ringe,
        )
        self.commandlist.extend(
            bn.befehle(ergebnis.punkte, self.horizFeed * 60.0, vo.eintauchvorschub(self))
        )


def rechne(obj, job, modell, vorschub=0.0, eintauchen=0.0):
    """Die Bahn (schruppen3d_bahn.Schruppbahn) für die Operation `obj` im Job. ValueError mit
    einem Satz, wenn es nicht geht."""
    form = vs.form_des_controllers(obj.ToolController)
    if form is None:
        raise ValueError(tr("ra.fehler.form"))
    # Was die Operationen davor schon weggenommen haben (W-012) – und woraus das gerechnet ist:
    # Ändert sich davor etwas, rechnet gui_materialstand das 3D-Schruppen neu.
    stand = mst.fuer(job, vor=obj)
    if "Materialstand" in obj.PropertiesList:
        obj.Materialstand = mst.kennung_vor(job, obj)
    return bahn_fuer(
        job,
        modell,
        form,
        float(obj.Zustellung),
        float(obj.Zeilenabstand),
        float(obj.Aufmass),
        vo.flaechen(obj),
        zwischen=float(obj.Zwischenlagen),
        gleichlauf=sp.fuer_m3(obj.Gleichlauf, obj.ToolController),
        schneidenlaenge=ko.schneidenlaenge(obj.ToolController),
        oben=min(float(obj.StartDepth), pf.rohteil_von_oben(job)[4]),
        sicher=float(obj.SafeHeight),
        sicherheit=float(obj.Sicherheitsabstand),
        eintauchwinkel=float(obj.Eintauchwinkel),
        vorschub=vorschub,
        eintauchen=eintauchen,
        davor=form_davor(obj),
        stand=stand,
    )


def form_davor(obj):
    """Die Form des Fräsers davor (fraeserform.Form) – None, wenn die Operation das ganze
    Rohteil schruppt. Eckenradius 0: Schaftfräser, sonst Torus (bis Ø/2)."""
    durchmesser = float(getattr(obj, "DurchmesserDavor", 0.0) or 0.0)
    if durchmesser <= 0:
        return None
    radius = durchmesser / 2
    return ff.torus(radius, min(float(getattr(obj, "EckenradiusDavor", 0.0) or 0.0), radius))


def bahn_fuer(
    job,
    modell,
    form,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    flaechen=(),
    zwischen=sr.ZWISCHEN,
    gleichlauf=True,
    schneidenlaenge=0.0,
    oben=None,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    eintauchwinkel=vb.EINTAUCHWINKEL,
    toleranz=hf.TOLERANZ,
    schritt=sr.SCHRITT,
    vorschub=0.0,
    eintauchen=0.0,
    davor=None,
    stand=None,
):
    """Die Bahn „3D-Schruppen“ über den Freiformflächen `flaechen` für Modell und Rohteil des
    Jobs – mit `davor` (Form des größeren Fräsers davor) nur der Rest; mit `stand` (der
    Materialstand davor) nur, was die Operationen davor übrig ließen. ValueError mit einem
    Satz, wenn es nicht geht."""
    form_teil = vs._teil(modell)
    x_von, x_bis, y_von, y_bis, z_oben = pf.rohteil_von_oben(job)
    if oben is None:
        oben = z_oben
    if sicher is None:
        sicher = oben + sicherheit + 3.0
    werte = rb.Raeumwerte(
        form=form,
        zustellung=zustellung,
        zeilenabstand=zeilenabstand,
        aufmass=aufmass,
        oben=oben,
        sicher=sicher,
        rohteil=(x_von, x_bis, y_von, y_bis),
        gleichlauf=gleichlauf,
        schneidenlaenge=schneidenlaenge,
        sicherheit=sicherheit,
        eintauchwinkel=eintauchwinkel,
        vorschub=vorschub,
        eintauchen=eintauchen,
    )
    return sr.planen(form_teil, list(flaechen), werte, zwischen, toleranz, schritt, davor, stand)


def vorschau(job, modell, form, zustellung, zeilenabstand, aufmass, flaechen, **weiter):
    """Die Bahn grob – für den Assistenten: gröber vernetzt, gröberes Raster."""
    return bahn_fuer(
        job,
        modell,
        form,
        zustellung,
        zeilenabstand,
        aufmass,
        flaechen,
        toleranz=hf.VORSCHAU_TOLERANZ,
        schritt=sr.VORSCHAU_SCHRITT,
        **weiter,
    )


def lege_an(
    job,
    tc,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    zwischen=sr.ZWISCHEN,
    gleichlauf=True,
    name=None,
    flaechen=(),
    davor=(0.0, 0.0),
):
    """Legt „3D-Schruppen“ im Job an – mit `davor` (Ø, Eckenradius des Fräsers davor; Ø > 0)
    als „Restschruppen“ – ohne eigene Transaktion, die hält der Aufrufer. Die Endtiefe ist der
    tiefste Punkt der Flächen plus Aufmaß. Gibt die Operation zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Schruppen3D")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = Schruppen3D(obj, "Schruppen3D", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    _werte(obj, zustellung, zeilenabstand, aufmass, zwischen, gleichlauf)
    obj.DurchmesserDavor, obj.EckenradiusDavor = (float(davor[0]), float(davor[1]))
    obj.Flaechen = list(flaechen)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(obj.Document, name or _name(tc, float(davor[0])), obj)
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _werte(obj, zustellung, zeilenabstand, aufmass, zwischen, gleichlauf):
    obj.Zustellung = zustellung
    obj.Zeilenabstand = zeilenabstand
    obj.Aufmass = aufmass
    obj.Zwischenlagen = max(float(zwischen), 0.0)
    obj.Gleichlauf = bool(gleichlauf)


def _endtiefe(obj, job):
    """Die Endtiefe: der tiefste Punkt der gewählten Freiformflächen plus Aufmaß – zum Lesen;
    die Bahn rechnet aus den Flächen."""
    try:
        _flaechen, z_unten = sr.bereich(vs._teil(job.Model.Group), list(obj.Flaechen))
    except ValueError:
        return
    obj.setExpression("FinalDepth", None)
    obj.FinalDepth = z_unten + float(obj.Aufmass)


def aendere(
    obj,
    tc,
    zustellung,
    zeilenabstand,
    aufmass,
    zwischen=sr.ZWISCHEN,
    gleichlauf=True,
    flaechen=None,
    davor=None,
):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` und `davor` ohne bleiben. Der Name folgt dem Werkzeug, solange es
    der vorgeschlagene ist."""
    if davor is not None:
        obj.DurchmesserDavor, obj.EckenradiusDavor = (float(davor[0]), float(davor[1]))
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, _name(tc, float(obj.DurchmesserDavor)), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    _werte(obj, zustellung, zeilenabstand, aufmass, zwischen, gleichlauf)
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def _name(tc, durchmesser_davor=0.0):
    """„3D-Schruppen T1“ – oder „Restschruppen T5“."""
    if durchmesser_davor > 0:
        return tr("rr.name", werkzeug=f"T{tc.ToolNumber}")
    return tr("r3.name", werkzeug=f"T{tc.ToolNumber}")


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („3D-Schruppen T1“, „Restschruppen T5“) – auch
    mit „ (2)“?"""
    return namen.nach_vorlage(name, tr("r3.name", werkzeug="\0")) or namen.nach_vorlage(
        name, tr("rr.name", werkzeug="\0")
    )


def ist_schruppen3d(op):
    """Ist `op` eine Operation dieses Moduls – „3D-Schruppen“ oder „Restschruppen“?"""
    return isinstance(getattr(op, "Proxy", None), Schruppen3D)


def ist_restschruppen(op):
    """Ist `op` „3D-Schruppen“ als „Restschruppen“ – mit dem Fräser davor?"""
    return ist_schruppen3d(op) and float(getattr(op, "DurchmesserDavor", 0.0) or 0.0) > 0
