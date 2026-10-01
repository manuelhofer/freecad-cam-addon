# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Bleistift“ (W-006 4.2 Punkt 6) – Kehlen nachfahren: dort, wo der
Kugelfräser die gewählte Freiformfläche und ihre Nachbarin zugleich berührt (bleistift_bahn).

Wie „3D-Schlichten“ eine eigene Operation (erbt FreeCADs ObjectOp) mit Werkzeug-Controller,
Kühlmittel und FreeCADs Tiefen und Höhen. Beim Neuberechnen rechnet sie ihre Bahn aus dem
Modell des Jobs, mit dem Fräser aus dem ToolBit des Controllers.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Schlichten“. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import bahn as bn
from . import bleistift_bahn as bb
from . import namen
from . import planfraesen as pf
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from .sprache import tr

GRUPPE = "Fräsen"


class Bleistift(PathOp.ObjectOp):
    """Proxy der Operation „Bleistift“."""

    def opFeatures(self, obj):
        return (
            PathOp.FeatureTool
            | PathOp.FeatureDepths
            | PathOp.FeatureHeights
            | PathOp.FeatureCoolant
        )

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Aufmass = 0.0
        obj.Sicherheitsabstand = vb.SICHERHEIT
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        neu = []
        for typ, name, text in (
            ("App::PropertyStringList", "Flaechen", tr("s3.eigenschaft.flaechen")),
            ("App::PropertyLength", "Aufmass", tr("s3.eigenschaft.aufmass")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyInteger", "Linien", tr("bs.eigenschaft.linien")),
            ("App::PropertyLength", "Laenge", tr("bs.eigenschaft.laenge")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Linien", "Laenge"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(
                obj, self.job, self.model, self.horizFeed * 60.0, vo.eintauchvorschub(self)
            )
        except ValueError as fehler:
            obj.Linien = 0
            obj.Laenge = 0.0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Linien = ergebnis.linien
        obj.Laenge = round(float(ergebnis.laenge), 1)
        self.commandlist.extend(
            bn.befehle(ergebnis.punkte, self.horizFeed * 60.0, vo.eintauchvorschub(self))
        )


def rechne(obj, job, modell, vorschub=0.0, eintauchen=0.0):
    """Die Bahn (bleistift_bahn.Bleistiftbahn) für die Operation `obj` im Job. ValueError mit
    einem Satz, wenn es nicht geht."""
    form = vs.form_des_controllers(obj.ToolController)
    if form is None:
        raise ValueError(tr("bs.fehler.form"))
    return bahn_fuer(
        job,
        modell,
        form,
        vo.flaechen(obj),
        aufmass=float(obj.Aufmass),
        oben=min(float(obj.StartDepth), pf.rohteil_von_oben(job)[4]),
        sicher=float(obj.SafeHeight),
        sicherheit=float(obj.Sicherheitsabstand),
        vorschub=vorschub,
        eintauchen=eintauchen,
    )


def bahn_fuer(
    job,
    modell,
    form,
    flaechen,
    aufmass=0.0,
    oben=None,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    vorschub=0.0,
    eintauchen=0.0,
    toleranz=bb.TOLERANZ_NETZ,
    raster=bb.RASTER,
):
    """Die Bahn „Bleistift“ an den Kehlen der Flächen `flaechen`. ValueError mit einem Satz,
    wenn es nicht geht."""
    form_teil = vs._teil(modell)
    *_rohteil, z_oben = pf.rohteil_von_oben(job)
    if oben is None:
        oben = z_oben
    if sicher is None:
        sicher = oben + sicherheit + 3.0
    werte = bb.Bleistiftwerte(
        form=form,
        oben=oben,
        sicher=sicher,
        aufmass=aufmass,
        sicherheit=sicherheit,
        raster=raster,
        vorschub=vorschub,
        eintauchen=eintauchen,
    )
    return bb.planen(form_teil, list(flaechen), werte, toleranz)


def vorschau(job, modell, form, flaechen, **weiter):
    """Die Bahn für den Assistenten: gröber vernetzt, gröberes Raster."""
    return bahn_fuer(
        job,
        modell,
        form,
        flaechen,
        toleranz=bb.VORSCHAU_TOLERANZ,
        raster=bb.VORSCHAU_RASTER,
        **weiter,
    )


def lege_an(job, tc, aufmass=0.0, name=None, flaechen=()):
    """Legt „Bleistift“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Die
    Endtiefe ist der tiefste Punkt der Flächen. Gibt die Operation zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Bleistift")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = Bleistift(obj, "Bleistift", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    obj.Aufmass = aufmass
    obj.Flaechen = list(flaechen)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(
        obj.Document, name or tr("bs.name", werkzeug=f"T{tc.ToolNumber}"), obj
    )
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _endtiefe(obj, job):
    """Die Endtiefe: der tiefste Punkt der gewählten Freiformflächen – zum Lesen."""
    from . import schlichten3d as s3op

    s3op._endtiefe(obj, job)


def aendere(obj, tc, aufmass=0.0, flaechen=None):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` ohne bleibt. Der Name folgt dem Werkzeug, solange es der
    vorgeschlagene ist."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, tr("bs.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Aufmass = aufmass
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Bleistift T3“) – auch mit „ (2)“?"""
    return namen.nach_vorlage(name, tr("bs.name", werkzeug="\0"))


def ist_bleistift(op):
    """Ist `op` eine Operation dieses Moduls – „Bleistift“?"""
    return isinstance(getattr(op, "Proxy", None), Bleistift)
