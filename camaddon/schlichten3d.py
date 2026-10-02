# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „3D-Schlichten“ (W-006 4.2 Punkt 3) – Freiformflächen in parallelen
Zeilen, die Spitze auf der Hüllfläche des ganzen Teils, der Zeilenabstand aus der Grathöhe
(schlichten3d_bahn). Mit dem Durchmesser des Fräsers davor (`DurchmesserDavor` > 0) ist sie
„Restschlichten“ (W-006 4.2 Punkt 8): nur dort, wo der größere Fräser davor mehr stehen ließ.

Wie „Bohrung fräsen“ eine eigene Operation (erbt FreeCADs ObjectOp) mit Werkzeug-Controller,
Kühlmittel und FreeCADs Tiefen und Höhen. Beim Neuberechnen rechnet sie ihre Bahn aus dem
Modell des Jobs, mit dem Fräser aus dem ToolBit des Controllers und seinen Vorschüben für die
Zeit.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Schlichten“. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import bahn as bn
from . import fraeserform as ff
from . import namen
from . import planfraesen as pf
from . import schlichten3d_bahn as sb
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from .sprache import tr

GRUPPE = "Fräsen"
RICHTUNGEN = ("auto", "x", "y", "spirale", "flaeche", "aequidistant")


class Schlichten3D(PathOp.ObjectOp):
    """Proxy der Operation „3D-Schlichten“."""

    def opFeatures(self, obj):
        return (
            PathOp.FeatureTool
            | PathOp.FeatureDepths
            | PathOp.FeatureHeights
            | PathOp.FeatureCoolant
        )

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Grathoehe = sb.GRATHOEHE
        obj.Aufmass = 0.0
        obj.Richtung = list(RICHTUNGEN)
        obj.Richtung = "auto"
        obj.Grenzwinkel = sb.GRENZWINKEL
        obj.Sicherheitsabstand = vb.SICHERHEIT
        obj.DurchmesserDavor = 0.0  # 0: ganz schlichten; sonst Restschlichten
        obj.EckenradiusDavor = 0.0
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        if "Grenzwinkel" in self._eigenschaften(obj):
            obj.Grenzwinkel = 0.0  # gespeichert vor Steil/Flach: wie damals nur Zeilen
        if set(RICHTUNGEN) - set(obj.getEnumerationsOfProperty("Richtung")):
            richtung = str(obj.Richtung)
            obj.Richtung = list(RICHTUNGEN)  # gespeichert vor einer neuen Richtung: die Wahl dazu
            obj.Richtung = richtung
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        neu = []
        for typ, name, text in (
            ("App::PropertyStringList", "Flaechen", tr("s3.eigenschaft.flaechen")),
            ("App::PropertyLength", "Grathoehe", tr("s3.eigenschaft.grathoehe")),
            ("App::PropertyLength", "Aufmass", tr("s3.eigenschaft.aufmass")),
            ("App::PropertyEnumeration", "Richtung", tr("s3.eigenschaft.richtung")),
            ("App::PropertyAngle", "Grenzwinkel", tr("s3.eigenschaft.grenzwinkel")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyInteger", "Zeilen", tr("s3.eigenschaft.zeilen")),
            ("App::PropertyInteger", "Hoehenlinien", tr("s3.eigenschaft.hoehenlinien")),
            ("App::PropertyInteger", "Umlaeufe", tr("s3.eigenschaft.umlaeufe")),
            ("App::PropertyLength", "Abstand", tr("s3.eigenschaft.abstand")),
            ("App::PropertyLength", "DurchmesserDavor", tr("s3.eigenschaft.davor")),
            ("App::PropertyLength", "EckenradiusDavor", tr("s3.eigenschaft.eckenradius_davor")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Zeilen", "Hoehenlinien", "Umlaeufe", "Abstand"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(
                obj, self.job, self.model, self.horizFeed * 60.0, vo.eintauchvorschub(self)
            )
        except ValueError as fehler:
            obj.Zeilen = obj.Hoehenlinien = obj.Umlaeufe = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Zeilen, obj.Hoehenlinien = ergebnis.zeilen, ergebnis.hoehenlinien
        obj.Umlaeufe = ergebnis.umlaeufe
        obj.Abstand = round(float(ergebnis.abstand), 4)
        self.commandlist.extend(
            bn.befehle(ergebnis.punkte, self.horizFeed * 60.0, vo.eintauchvorschub(self))
        )


def rechne(obj, job, modell, vorschub=0.0, eintauchen=0.0):
    """Die Bahn (schlichten3d_bahn.Schlichtbahn) für die Operation `obj` im Job. ValueError
    mit einem Satz, wenn es nicht geht."""
    form = vs.form_des_controllers(obj.ToolController)
    if form is None:
        raise ValueError(tr("s3.fehler.form"))
    return bahn_fuer(
        job,
        modell,
        form,
        float(obj.Grathoehe),
        vo.flaechen(obj),
        aufmass=float(obj.Aufmass),
        richtung=str(obj.Richtung),
        grenzwinkel=float(obj.Grenzwinkel),
        oben=min(float(obj.StartDepth), pf.rohteil_von_oben(job)[4]),
        sicher=float(obj.SafeHeight),
        sicherheit=float(obj.Sicherheitsabstand),
        vorschub=vorschub,
        eintauchen=eintauchen,
        davor=form_davor(obj),
    )


def form_davor(obj):
    """Die Form des Fräsers davor (fraeserform.Form) – None, wenn die Operation ganz schlichtet.
    Eckenradius 0: Schaftfräser, Ø/2 und mehr: Kugel, dazwischen Torus."""
    durchmesser = float(getattr(obj, "DurchmesserDavor", 0.0) or 0.0)
    if durchmesser <= 0:
        return None
    radius = durchmesser / 2
    return ff.torus(radius, min(float(getattr(obj, "EckenradiusDavor", 0.0) or 0.0), radius))


def eckenradius(form):
    """Der Eckenradius einer Fräserform: Kugel ihr Radius, Torus der Bogen am Rand, sonst 0."""
    if form.kugel > 0:
        return float(form.radius) if form.nur_kugel else float(form.kugel)
    letztes = form.stuecke[-1]
    return float(getattr(letztes, "radius", 0.0) or 0.0) if not form.eben else 0.0


def bahn_fuer(
    job,
    modell,
    form,
    grathoehe,
    flaechen,
    aufmass=0.0,
    richtung="auto",
    grenzwinkel=sb.GRENZWINKEL,
    oben=None,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    vorschub=0.0,
    eintauchen=0.0,
    schritt=sb.SCHRITT,
    toleranz=sb.TOLERANZ_NETZ,
    raster=sb.RASTER,
    davor=None,
):
    """Die Bahn „3D-Schlichten“ über die Flächen `flaechen` des Modells – mit `davor` (Form des
    Fräsers davor) nur der Rest. ValueError mit einem Satz, wenn es nicht geht."""
    form_teil = vs._teil(modell)
    *_rohteil, z_oben = pf.rohteil_von_oben(job)
    if oben is None:
        oben = z_oben
    if sicher is None:
        sicher = oben + sicherheit + 3.0
    werte = sb.Schlichtwerte(
        form=form,
        oben=oben,
        sicher=sicher,
        grathoehe=grathoehe,
        aufmass=aufmass,
        richtung=richtung,
        grenzwinkel=grenzwinkel,
        sicherheit=sicherheit,
        schritt=schritt,
        raster=raster,
        vorschub=vorschub,
        eintauchen=eintauchen,
        davor=davor,
    )
    return sb.planen(form_teil, list(flaechen), werte, toleranz)


def vorschau(job, modell, form, grathoehe, flaechen, **weiter):
    """Die Bahn für den Assistenten: gröber abgetastet und vernetzt."""
    return bahn_fuer(
        job,
        modell,
        form,
        grathoehe,
        flaechen,
        schritt=sb.VORSCHAU_SCHRITT,
        toleranz=sb.VORSCHAU_TOLERANZ,
        raster=sb.VORSCHAU_RASTER,
        **weiter,
    )


def lege_an(job, tc, grathoehe, aufmass=0.0, name=None, flaechen=(), davor=(0.0, 0.0)):
    """Legt „3D-Schlichten“ im Job an – mit `davor` (Ø, Eckenradius des Fräsers davor; Ø > 0)
    als „Restschlichten“ – ohne eigene Transaktion, die hält der Aufrufer. Die Endtiefe ist der
    tiefste Punkt der Flächen. Gibt die Operation zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Schlichten3D")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = Schlichten3D(obj, "Schlichten3D", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    obj.Grathoehe = grathoehe
    obj.Aufmass = aufmass
    obj.DurchmesserDavor, obj.EckenradiusDavor = (float(davor[0]), float(davor[1]))
    obj.Flaechen = list(flaechen)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(obj.Document, name or _name(tc, float(davor[0])), obj)
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _endtiefe(obj, job):
    """Die Endtiefe: der tiefste Punkt der gewählten Freiformflächen."""
    from . import vierachs_flaechen as vf

    try:
        form_teil = vs._teil(job.Model.Group)
        nummern = vf.nummern(sb.freiformflaechen(form_teil, list(obj.Flaechen)))
    except ValueError:
        nummern = []
    if nummern:
        obj.setExpression("FinalDepth", None)
        obj.FinalDepth = min(form_teil.Faces[n].BoundBox.ZMin for n in nummern)


def _name(tc, durchmesser_davor=0.0):
    """„3D-Schlichten T3“ – oder „Restschlichten T4“."""
    if durchmesser_davor > 0:
        return tr("rs.name", werkzeug=f"T{tc.ToolNumber}")
    return tr("s3.name", werkzeug=f"T{tc.ToolNumber}")


def aendere(obj, tc, grathoehe, aufmass=0.0, flaechen=None, davor=None):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` und `davor` ohne bleiben. Der Name folgt dem Werkzeug, solange es
    der vorgeschlagene ist."""
    if davor is not None:
        obj.DurchmesserDavor, obj.EckenradiusDavor = (float(davor[0]), float(davor[1]))
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, _name(tc, float(obj.DurchmesserDavor)), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Grathoehe = grathoehe
    obj.Aufmass = aufmass
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („3D-Schlichten T3“, „Restschlichten T4“) –
    auch mit „ (2)“?"""
    return namen.nach_vorlage(name, tr("s3.name", werkzeug="\0")) or namen.nach_vorlage(
        name, tr("rs.name", werkzeug="\0")
    )


def ist_schlichten3d(op):
    """Ist `op` eine Operation dieses Moduls – „3D-Schlichten“ oder „Restschlichten“?"""
    return isinstance(getattr(op, "Proxy", None), Schlichten3D)


def ist_restschlichten(op):
    """Ist `op` „3D-Schlichten“ als „Restschlichten“ – mit dem Fräser davor?"""
    return ist_schlichten3d(op) and float(getattr(op, "DurchmesserDavor", 0.0) or 0.0) > 0
