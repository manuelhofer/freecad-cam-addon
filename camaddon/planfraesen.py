# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Planfräsen“ (W-006 S3, 4.1 Punkt 1) – die erste 2,5D-Operation des
Addons.

Wie „Rundum schruppen“ (vierachs_operation) eine eigene Operation (erbt FreeCADs ObjectOp)
mit Werkzeug-Controller und Kühlmittel – und mit FreeCADs Tiefen und Höhen (StartDepth,
FinalDepth, SafeHeight, ClearanceHeight), wie seine Operationen sie haben: Die Lagen
beginnen an der Starttiefe (die Oberkante des Rohteils, folgt ihm), der Eilgang läuft auf
der sicheren Höhe. Beim Neuberechnen rechnet sie ihre Bahn aus Modell und Rohteil des Jobs
(planfraesen_bahn.planen): Je gewählter ebener Fläche nach oben – ohne Wahl die Oberseite des
Teils – Zeilen hin und her in Lagen bis auf die Fläche plus Aufmaß, mit dem Fräser aus dem
ToolBit des Controllers.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Planen“, sonst „Schruppen“ oder „Schlichten“. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import bahn as bn
from . import freiwege as fw
from . import hoehenfeld as hf
from . import materialstand as mst
from . import namen
from . import planfraesen_bahn as pb
from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from .sprache import tr
from .vierachs_plan import zeilenabstand_vorschlag  # noqa: F401 – auch für den Assistenten

GRUPPE = "Fräsen"  # die Gruppe der Eigenschaften
ZUSTELLUNG = 2.0  # mm – Vorschlag, solange nichts anderes gesagt ist
AUFMASS = 0.0  # mm – Planfräsen macht die Fläche fertig
AUSTRITT = 50  # % des Vorschubs beim Austritt aus dem Rohteil


class PlanFraesen(PathOp.ObjectOp):
    """Proxy der Operation „Planfräsen“."""

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
        obj.Zeilenabstand = 4.0
        obj.Aufmass = AUFMASS
        obj.Ueberlauf = 0.0  # 0: der Vorschlag (0,6 · Ø)
        obj.Sicherheitsabstand = vb.SICHERHEIT
        obj.Eintauchwinkel = vb.EINTAUCHWINKEL
        obj.VorschubAustritt = AUSTRITT
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        neu = []
        for typ, name, text in (
            ("App::PropertyStringList", "Flaechen", tr("pf.eigenschaft.flaechen")),
            ("App::PropertyLength", "Zustellung", tr("pf.eigenschaft.zustellung")),
            ("App::PropertyLength", "Zeilenabstand", tr("pf.eigenschaft.zeilenabstand")),
            ("App::PropertyLength", "Aufmass", tr("pf.eigenschaft.aufmass")),
            ("App::PropertyLength", "Ueberlauf", tr("pf.eigenschaft.ueberlauf")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyAngle", "Eintauchwinkel", tr("vo.eigenschaft.eintauchwinkel")),
            ("App::PropertyPercent", "VorschubAustritt", tr("pf.eigenschaft.austritt")),
            ("App::PropertyBool", "NurGleichlauf", tr("pf.eigenschaft.nur_gleichlauf")),
            ("App::PropertyInteger", "Ebenen", tr("pf.eigenschaft.ebenen")),
            ("App::PropertyInteger", "Lagen", tr("pf.eigenschaft.lagen")),
            ("App::PropertyInteger", "Zeilen", tr("pf.eigenschaft.zeilen")),
            ("App::PropertyString", "Richtung", tr("pf.eigenschaft.richtung")),
            ("App::PropertyString", "Materialstand", tr("ms.eigenschaft.materialstand")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Ebenen", "Lagen", "Zeilen", "Richtung"):
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
            obj.Ebenen = obj.Lagen = obj.Zeilen = 0
            obj.Richtung = ""
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Ebenen, obj.Lagen, obj.Zeilen = ergebnis.flaechen, ergebnis.lagen, ergebnis.zeilen
        obj.Richtung = ", ".join("X" if laengs_x else "Y" for laengs_x in ergebnis.richtungen)
        # Im Freien mit dem Freivorschub, kurz vor dem Material langsam (freiwege, Manuel
        # 2026-10-04: „gib Gas bis kurz davor … bei allen Strategien“).
        punkte, _schnell = fw.fuer_operation(self.job, obj, ergebnis.punkte, self.horizFeed * 60.0)
        self.commandlist.extend(
            bn.befehle(
                punkte,
                self.horizFeed * 60.0,  # CAM führt mm/s
                vo.eintauchvorschub(self),
            )
        )


def rechne(obj, job, modell, vorschub=0.0, eintauchen=0.0):
    """Die Bahn (planfraesen_bahn.Planbahn) für die Operation `obj` im Job; `vorschub` und
    `eintauchen` (mm/min) für die Zeit, nach der die Zeilenrichtung fällt. ValueError mit
    einem Satz, wenn es nicht geht."""
    form = vs.form_des_controllers(obj.ToolController)
    if form is None:
        raise ValueError(tr("pf.fehler.form"))
    # Was die Operationen davor schon weggenommen haben (W-012) – und woraus das gerechnet ist:
    # Ändert sich davor etwas, rechnet gui_materialstand das Planfräsen neu.
    stand = mst.fuer(job, vor=obj)
    if "Materialstand" in obj.PropertiesList:
        obj.Materialstand = mst.kennung_vor(job, obj)
    ueberlauf = float(obj.Ueberlauf)
    return bahn_fuer(
        job,
        modell,
        form,
        float(obj.Zustellung),
        float(obj.Zeilenabstand),
        float(obj.Aufmass),
        ueberlauf if ueberlauf > 0 else None,
        vo.flaechen(obj),
        min(float(obj.StartDepth), rohteil_von_oben(job)[4]),  # nie über dem Rohteil anfangen
        float(obj.SafeHeight),
        float(obj.Sicherheitsabstand),
        float(obj.Eintauchwinkel),
        float(obj.VorschubAustritt) / 100.0,
        vorschub=vorschub,
        eintauchen=eintauchen,
        nur_gleichlauf=bool(getattr(obj, "NurGleichlauf", False)),
        gleichlauf=sp.fuer_m3(True, obj.ToolController),
        stand=stand,
    )


def rohteil_von_oben(job):
    """(x_von, x_bis, y_von, y_bis, z_oben) des Rohteils im Job – ValueError ohne Rohteil."""
    rohteil = getattr(job, "Stock", None)
    form = getattr(rohteil, "Shape", None)
    if form is None or form.isNull():
        raise ValueError(tr("pf.fehler.rohteil"))
    bb = form.BoundBox
    return (float(bb.XMin), float(bb.XMax), float(bb.YMin), float(bb.YMax), float(bb.ZMax))


def bahn_fuer(
    job,
    modell,
    form,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    ueberlauf=None,
    flaechen=(),
    oben=None,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    eintauchwinkel=vb.EINTAUCHWINKEL,
    austritt=pb.AUSTRITT_ANTEIL,
    toleranz=hf.TOLERANZ,
    schritt=pb.SCHRITT,
    vorschub=0.0,
    eintauchen=0.0,
    nur_gleichlauf=False,
    gleichlauf=True,
    stand=None,
):
    """Die Bahn „Planfräsen“ für Modell und Rohteil des Jobs. `flaechen`: die gewählten Flächen
    („Face6“ …) – gefräst werden die ebenen nach oben darunter; leer: die Oberseite des Teils.
    `oben`: z, wo die Lagen beginnen (None: die Oberkante des Rohteils); `sicher`: z für den
    Eilgang (None: Oberkante + Sicherheitsabstand + 3 mm); `vorschub` und `eintauchen` (mm/min)
    für die Zeit, nach der je Fläche die Zeilenrichtung fällt; `nur_gleichlauf`: jede Zeile im
    Gleichlauf, danach abheben und von vorne (sonst hin und her), `gleichlauf` die Richtung dafür
    bei M3 (spindel.fuer_m3); `stand`: der Materialstand davor (materialstand) – was die
    Operationen davor weggenommen haben, fräst es nicht noch einmal. ValueError mit einem Satz,
    wenn es nicht geht."""
    form_teil = vs._teil(modell)
    x_von, x_bis, y_von, y_bis, z_oben = rohteil_von_oben(job)
    if oben is None:
        oben = z_oben
    if sicher is None:
        sicher = oben + sicherheit + 3.0
    namen = list(flaechen) or hf.oberseite(form_teil)
    ebenen = hf.ebenen_oben(form_teil, namen)
    if not ebenen:
        raise ValueError(tr("pf.fehler.keine_ebene"))
    werte = pb.Planwerte(
        form=form,
        zustellung=zustellung,
        zeilenabstand=zeilenabstand,
        aufmass=aufmass,
        oben=oben,
        sicher=sicher,
        rohteil=(x_von, x_bis, y_von, y_bis),
        ueberlauf=ueberlauf,
        sicherheit=sicherheit,
        eintauchwinkel=eintauchwinkel,
        austritt=austritt,
        vorschub=vorschub,
        eintauchen=eintauchen,
        nur_gleichlauf=nur_gleichlauf,
        gleichlauf=gleichlauf,
    )
    netz = hf.netze_je_hoehe(form_teil, ebenen, toleranz)
    return pb.planen(netz, werte, ebenen, schritt, stand)


def vorschau(
    job,
    modell,
    form,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    flaechen=(),
    vorschub=0.0,
    eintauchen=0.0,
    nur_gleichlauf=False,
    stand=None,
):
    """Die Bahn grob – für Lagen, Zeilen, Zeit und ob es geht, im Assistenten: gröber vernetzt,
    weniger Stellen je Zeile. ValueError wie bahn_fuer()."""
    return bahn_fuer(
        job,
        modell,
        form,
        zustellung,
        zeilenabstand,
        aufmass,
        None,
        flaechen,
        toleranz=hf.VORSCHAU_TOLERANZ,
        schritt=pb.VORSCHAU_SCHRITT,
        vorschub=vorschub,
        eintauchen=eintauchen,
        nur_gleichlauf=nur_gleichlauf,
        stand=stand,
    )


def lege_an(
    job,
    tc,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    name=None,
    flaechen=(),
    nur_gleichlauf=False,
):
    """Legt „Planfräsen“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Tiefen
    und Höhen wie FreeCADs Operationen: die Starttiefe folgt dem Rohteil, die sichere Höhe und
    die Freifahrhöhe dem Einrichtblatt des Jobs; die Endtiefe ist die Fläche plus Aufmaß. Gibt
    die Operation zurück. Angelegt mit DoNotSetDefaultValues wie „Rundum schruppen“ – ohne
    Rückfrage nach dem Controller."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "PlanFraesen")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = PlanFraesen(obj, "PlanFraesen", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    _hoehen(obj, proxy, job)
    obj.Zustellung = zustellung
    obj.Zeilenabstand = zeilenabstand
    obj.Aufmass = aufmass
    obj.Flaechen = list(flaechen)
    obj.NurGleichlauf = bool(nur_gleichlauf)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(
        obj.Document, name or tr("pf.name", werkzeug=f"T{tc.ToolNumber}"), obj
    )
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _hoehen(obj, proxy, job):
    """Starttiefe, sichere Höhe und Freifahrhöhe wie FreeCADs Operationen aus dem
    Einrichtblatt – als Ausdruck, wo es einen gibt, sonst vom Rohteil."""
    blatt = job.SetupSheet
    _x_von, _x_bis, _y_von, _y_bis, z_oben = rohteil_von_oben(job)
    # FreeCADs Vorgabe „OpStartDepth“ liegt 1 mm über dem Modell, nicht auf dem Rohteil: Endet
    # das Rohteil oben am Teil (ein Zapfen), gäbe das eine Lage Luft – und aus einer Lage von
    # 20 zwei von 10,5 (Manuels Platte, P-2026-10-01-20). Die Lagen beginnen am Rohteil.
    ausdruck = blatt.StartDepthExpression
    if not ausdruck or ausdruck.strip() == "OpStartDepth":
        ausdruck = "OpStockZMax"
    if not proxy.applyExpression(obj, "StartDepth", ausdruck):
        obj.StartDepth = z_oben
    if not proxy.applyExpression(obj, "SafeHeight", blatt.SafeHeightExpression):
        obj.SafeHeight = z_oben + 3.0
    if not proxy.applyExpression(obj, "ClearanceHeight", blatt.ClearanceHeightExpression):
        obj.ClearanceHeight = z_oben + 5.0


def _endtiefe(obj, job):
    """Die Endtiefe: die tiefste der gewählten Flächen plus Aufmaß – zum Lesen; die Bahn rechnet
    aus den Flächen."""
    try:
        form_teil = vs._teil(job.Model.Group)
        namen = list(obj.Flaechen) or hf.oberseite(form_teil)
        ebenen = hf.ebenen_oben(form_teil, namen)
    except ValueError:
        ebenen = []
    if ebenen:
        obj.setExpression("FinalDepth", None)
        obj.FinalDepth = min(e.z for e in ebenen) + float(obj.Aufmass)


def aendere(obj, tc, zustellung, zeilenabstand, aufmass, flaechen=None, nur_gleichlauf=None):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` und `nur_gleichlauf` ohne bleiben. Der Name folgt dem Werkzeug,
    solange es der vorgeschlagene ist."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, tr("pf.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Zustellung = zustellung
    obj.Zeilenabstand = zeilenabstand
    obj.Aufmass = aufmass
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    if nur_gleichlauf is not None:
        obj.NurGleichlauf = bool(nur_gleichlauf)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Planfräsen T1“) – auch mit „ (2)“ dahinter?"""
    return namen.nach_vorlage(name, tr("pf.name", werkzeug="\0"))


def ist_planfraesen(op):
    """Ist `op` eine Operation dieses Moduls – „Planfräsen“?"""
    return isinstance(getattr(op, "Proxy", None), PlanFraesen)
