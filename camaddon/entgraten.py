# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Entgraten“ im Quader (W-006 S3, 4.1 Punkt 8) – ein Fasenfräser bricht die
Oberkanten der gewählten Wände mit einer Fase (entgrat_bahn).

Wie „Kontur“ (kontur) eine eigene Operation (erbt FreeCADs ObjectOp) mit Werkzeug-Controller,
Kühlmittel und FreeCADs Tiefen und Höhen. Beim Neuberechnen rechnet sie ihre Bahn aus Modell
und Rohteil des Jobs, mit dem Fasenfräser aus dem ToolBit des Controllers (Spitzenwinkel,
Spitze, Durchmesser).

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Fasen“. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import re

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import bahn as bn
from . import entgrat_bahn as eb
from . import fraeserform as ff
from . import hoehenfeld as hf
from . import planfraesen as pf
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from . import werkzeuge as wz
from . import werkzeugform as wf
from .sprache import tr

GRUPPE = "Fräsen"


class Entgraten(PathOp.ObjectOp):
    """Proxy der Operation „Entgraten“."""

    def opFeatures(self, obj):
        return (
            PathOp.FeatureTool
            | PathOp.FeatureDepths
            | PathOp.FeatureHeights
            | PathOp.FeatureCoolant
        )

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Breite = eb.BREITE
        obj.Tiefer = eb.TIEFER
        obj.Einfahrradius = eb.EINFAHRT
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
            ("App::PropertyStringList", "Flaechen", tr("eg.eigenschaft.flaechen")),
            ("App::PropertyLength", "Breite", tr("eg.eigenschaft.breite")),
            ("App::PropertyLength", "Tiefer", tr("eg.eigenschaft.tiefer")),
            ("App::PropertyLength", "Einfahrradius", tr("eg.eigenschaft.einfahrradius")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyInteger", "Ketten", tr("eg.eigenschaft.ketten")),
            ("App::PropertyInteger", "Ausgelassen", tr("eg.eigenschaft.ausgelassen")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Ketten", "Ausgelassen"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(obj, self.job, self.model)
        except ValueError as fehler:
            obj.Ketten = obj.Ausgelassen = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Ketten, obj.Ausgelassen = ergebnis.ketten, ergebnis.ausgelassen
        if ergebnis.ausgelassen:
            FreeCAD.Console.PrintWarning(
                f"{obj.Label}: {tr('eg.ausgelassen', anzahl=ergebnis.ausgelassen)}\n"
            )
        self.commandlist.extend(
            bn.befehle(ergebnis.punkte, self.horizFeed * 60.0, vo.eintauchvorschub(self))
        )


def kegel_des_werkzeugs(werkzeug):
    """(Form, Spitzenwinkel, Ø der Spitze) eines Fasenfräsers aus der Werkzeugverwaltung –
    ValueError mit einem Satz bei einem anderen Werkzeug."""
    if werkzeug is None or werkzeug.art != wz.FASENFRAESER:
        raise ValueError(tr("eg.fehler.form"))
    spitze, _hoehe, winkel = wf.kegel(werkzeug)
    return ff.von_werkzeug(werkzeug), float(winkel), float(spitze)


def rechne(obj, job, modell):
    """Die Bahn (entgrat_bahn.Entgratbahn) für die Operation `obj` im Job. ValueError mit einem
    Satz, wenn es nicht geht."""
    from .werkzeuge_aus_cam import vom_controller

    form, winkel, spitze = kegel_des_werkzeugs(vom_controller(obj.ToolController))
    return bahn_fuer(
        job,
        modell,
        form,
        winkel,
        spitze,
        float(obj.Breite),
        float(obj.Tiefer),
        vo.flaechen(obj),
        einfahrradius=float(obj.Einfahrradius),
        sicher=float(obj.SafeHeight),
        sicherheit=float(obj.Sicherheitsabstand),
    )


def bahn_fuer(
    job,
    modell,
    form,
    spitzenwinkel,
    spitze,
    breite=eb.BREITE,
    tiefer=eb.TIEFER,
    flaechen=(),
    einfahrradius=None,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    toleranz=hf.TOLERANZ,
    schritt=eb.SCHRITT,
):
    """Die Bahn „Entgraten“ für Modell und Rohteil des Jobs an den Flächen `flaechen` („Face6“ …:
    Wände, oder ebene Flächen nach oben – dann die Wände, die an ihren Kanten hinab gehen).
    `sicher`: z für den Eilgang (None: Oberkante des Rohteils + Sicherheitsabstand + 3 mm).
    ValueError mit einem Satz, wenn es nicht geht."""
    form_teil = vs._teil(modell)
    *_rohteil, z_oben = pf.rohteil_von_oben(job)
    if sicher is None:
        sicher = z_oben + sicherheit + 3.0
    ketten = eb.ketten(form_teil, list(flaechen))
    werte = eb.Entgratwerte(
        form=form,
        spitzenwinkel=spitzenwinkel,
        spitze=spitze,
        breite=breite,
        tiefer=tiefer,
        sicher=sicher,
        einfahrradius=einfahrradius,
        sicherheit=sicherheit,
    )
    netz_nah, netz_fern = eb.netze(form_teil, list(flaechen), toleranz)
    return eb.planen(netz_nah, werte, ketten, schritt, netz_fern)


def vorschau(job, werkzeug, breite, tiefer, flaechen):
    """Die Bahn grob – für Ketten, Bahnen, Zeit und ob es geht, im Assistenten: gröber vernetzt,
    weiter abgetastet. ValueError wie bahn_fuer()."""
    form, winkel, spitze = kegel_des_werkzeugs(werkzeug)
    return bahn_fuer(
        job,
        job.Model.Group,
        form,
        winkel,
        spitze,
        breite,
        tiefer,
        flaechen,
        toleranz=hf.VORSCHAU_TOLERANZ,
        schritt=eb.VORSCHAU_SCHRITT,
    )


def lege_an(job, tc, breite=eb.BREITE, tiefer=eb.TIEFER, name=None, flaechen=()):
    """Legt „Entgraten“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Tiefen und
    Höhen wie FreeCADs Operationen; die Endtiefe ist die tiefste Spitze. Gibt die Operation
    zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Entgraten")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = Entgraten(obj, "Entgraten", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    obj.Breite = breite
    obj.Tiefer = tiefer
    obj.Flaechen = list(flaechen)
    _endtiefe(obj, job)
    obj.Label = name or tr("eg.name", werkzeug=f"T{tc.ToolNumber}")
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _endtiefe(obj, job):
    """Die Endtiefe: die tiefste Spitze – die tiefste Kante minus Fase und „Tiefer“."""
    from .werkzeuge_aus_cam import vom_controller

    try:
        _form, winkel, spitze = kegel_des_werkzeugs(vom_controller(obj.ToolController))
        ketten = eb.ketten(vs._teil(job.Model.Group), list(obj.Flaechen))
        fase, tiefer, _kegel = eb.masse(
            float(obj.Breite),
            float(obj.Tiefer),
            winkel,
            spitze,
            float(obj.ToolController.Tool.Diameter) / 2,
        )
    except ValueError:
        return
    obj.setExpression("FinalDepth", None)
    obj.FinalDepth = min(k.z_kante for k in ketten) - fase - tiefer


def aendere(obj, tc, breite, tiefer, flaechen=None):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` ohne bleibt. Der Name folgt dem Werkzeug, solange es der
    vorgeschlagene ist."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = tr("eg.name", werkzeug=f"T{tc.ToolNumber}")
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Breite = breite
    obj.Tiefer = tiefer
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def eindringtiefe(obj):
    """So tief (mm) geht die Spitze der Operation unter die Kante: Fase plus „Tiefer“ – so tief
    darf es im Vergleich im Quader dort ins Teil gehen (restmaterial.fuer_quader). 0, wenn das
    Werkzeug kein Fasenfräser ist."""
    from .werkzeuge_aus_cam import vom_controller

    try:
        _form, winkel, spitze = kegel_des_werkzeugs(vom_controller(obj.ToolController))
        fase, tiefer, _kegel = eb.masse(
            float(obj.Breite),
            float(obj.Tiefer),
            winkel,
            spitze,
            float(obj.ToolController.Tool.Diameter) / 2,
        )
    except (ValueError, AttributeError):
        return 0.0
    return fase + tiefer


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Entgraten T5“)?"""
    vorne, _mitte, hinten = tr("eg.name", werkzeug="\0").partition("\0")
    return re.fullmatch(re.escape(vorne) + r"T\d+" + re.escape(hinten), name) is not None


def ist_entgraten(op):
    """Ist `op` eine Operation dieses Moduls – „Entgraten“ im Quader?"""
    return isinstance(getattr(op, "Proxy", None), Entgraten)
