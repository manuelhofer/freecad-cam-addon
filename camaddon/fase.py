# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Fase“ (W-037) – eine angeklickte gezeichnete Fase: mit dem Schaftfräser in
Stufen, mit dem Fasenfräser ihres Winkels in einer Runde (fase_bahn).

Wie „Entgraten“ (entgraten) eine eigene Operation (erbt FreeCADs ObjectOp) mit
Werkzeug-Controller, Kühlmittel und FreeCADs Tiefen und Höhen. Beim Neuberechnen rechnet sie ihre
Bahn aus Modell und Rohteil des Jobs, mit dem Fräser aus dem ToolBit des Controllers, und mit dem,
was die Operationen davor stehen lassen (materialstand): Darüber beginnt sie, wo noch Material
steht.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Schlichten“, beim Fasenfräser „Fasen“. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import aufloesung as au
from . import bahn as bn
from . import fase_bahn as fb
from . import fraeserform as ff
from . import freiwege as fw
from . import hoehenfeld as hf
from . import materialstand as mst
from . import namen, uhren
from . import planfraesen as pf
from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_planbahn as vp
from . import vierachs_schlichten as vs
from . import werkzeuge as wz
from . import werkzeugform as wf
from .sprache import tr

GRUPPE = "Fräsen"


class Fase(PathOp.ObjectOp):
    """Proxy der Operation „Fase“."""

    def opFeatures(self, obj):
        return (
            PathOp.FeatureTool
            | PathOp.FeatureDepths
            | PathOp.FeatureHeights
            | PathOp.FeatureCoolant
        )

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Stufe = fb.STUFE
        obj.Zustellung = fb.ZUSTELLUNG
        obj.Sicherheitsabstand = vb.SICHERHEIT
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        au.eigenschaft(obj, GRUPPE)
        neu = []
        for typ, name, text in (
            ("App::PropertyStringList", "Flaechen", tr("fa.eigenschaft.flaechen")),
            ("App::PropertyLength", "Stufe", tr("fa.eigenschaft.stufe")),
            ("App::PropertyLength", "Zustellung", tr("fa.eigenschaft.zustellung")),
            ("App::PropertyLength", "Einfahrradius", tr("fa.eigenschaft.einfahrradius")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyInteger", "Fasen", tr("fa.eigenschaft.fasen")),
            ("App::PropertyInteger", "Lagen", tr("fa.eigenschaft.lagen")),
            ("App::PropertyInteger", "Ausgelassen", tr("fa.eigenschaft.ausgelassen")),
            ("App::PropertyString", "Materialstand", tr("ms.eigenschaft.materialstand")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Fasen", "Lagen", "Ausgelassen"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis
        obj.setEditorMode("Materialstand", 2)  # woraus gerechnet (gui_materialstand)

    @uhren.atmend_rechnen
    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(obj, self.job, self.model)
        except ValueError as fehler:
            obj.Fasen = obj.Lagen = obj.Ausgelassen = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Fasen, obj.Lagen, obj.Ausgelassen = ergebnis.fasen, ergebnis.lagen, ergebnis.ausgelassen
        if ergebnis.ausgelassen:
            FreeCAD.Console.PrintWarning(
                f"{obj.Label}: {tr('fa.ausgelassen', anzahl=ergebnis.ausgelassen)}\n"
            )
        # Im Freien mit dem Freivorschub, kurz vor dem Material langsam (freiwege, Manuel
        # 2026-10-04: „gib Gas bis kurz davor … bei allen Strategien“).
        punkte, _schnell = fw.fuer_operation(self.job, obj, ergebnis.punkte, self.horizFeed * 60.0)
        self.commandlist.extend(
            bn.befehle(punkte, self.horizFeed * 60.0, vo.eintauchvorschub(self))
        )


def schneide_des_werkzeugs(werkzeug):
    """(Form, Spitzenwinkel, Ø der Spitze) des Werkzeugs aus der Werkzeugverwaltung: ein
    Fasenfräser (sein ganzer Winkel), oder ein Fräser mit ganz ebener Stirn (0, 0) – ValueError
    mit einem Satz bei einem anderen."""
    if werkzeug is not None and werkzeug.art == wz.FASENFRAESER:
        spitze, _hoehe, winkel = wf.kegel(werkzeug)
        return ff.von_werkzeug(werkzeug), float(winkel), float(spitze)
    form = ff.von_werkzeug(werkzeug) if werkzeug is not None else None
    if form is None or vp.ebener_radius(form) < float(form.radius) - 1e-6:
        raise ValueError(tr("fa.fehler.form"))
    return form, 0.0, 0.0


def werkzeug_passt(werkzeug):
    """Fährt die Operation mit diesem Werkzeug – ein Fasenfräser, oder ganz ebene Stirn?"""
    try:
        schneide_des_werkzeugs(werkzeug)
    except ValueError:
        return False
    return True


def rechne(obj, job, modell):
    """Die Bahn (fase_bahn.Fasenbahn) für die Operation `obj` im Job. ValueError mit einem Satz,
    wenn es nicht geht."""
    from .werkzeuge_aus_cam import vom_controller

    form, winkel, spitze = schneide_des_werkzeugs(vom_controller(obj.ToolController))
    # Was die Operationen davor schon weggenommen haben (W-012) – und woraus das gerechnet ist:
    # Ändert sich davor etwas, rechnet gui_materialstand die Fase neu.
    stand = mst.fuer(job, vor=obj)
    if "Materialstand" in obj.PropertiesList:
        obj.Materialstand = mst.kennung_vor(job, obj)
    return bahn_fuer(
        job,
        modell,
        form,
        winkel,
        spitze,
        float(obj.Stufe),
        float(obj.Zustellung),
        vo.flaechen(obj),
        einfahrradius=float(obj.Einfahrradius),
        sicher=float(obj.SafeHeight),
        sicherheit=float(obj.Sicherheitsabstand),
        gleichlauf=sp.fuer_m3(True, obj.ToolController),
        schritt=au.wert(obj, fb.SCHRITT),
        stand=stand,
    )


def bahn_fuer(
    job,
    modell,
    form,
    spitzenwinkel,
    spitze,
    stufe=fb.STUFE,
    zustellung=fb.ZUSTELLUNG,
    flaechen=(),
    einfahrradius=None,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    toleranz=hf.TOLERANZ,
    schritt=fb.SCHRITT,
    gleichlauf=True,
    stand=None,
):
    """Die Bahn „Fase“ für Modell und Rohteil des Jobs an den Fasen unter `flaechen` („Face5“ …).
    `sicher`: z für den Eilgang (None: Oberkante des Rohteils + Sicherheitsabstand + 3 mm);
    `stand` der Materialstand davor (None: das ganze Rohteil). ValueError mit einem Satz, wenn es
    nicht geht."""
    form_teil = vs._teil(modell)
    *_rohteil, z_oben = pf.rohteil_von_oben(job)
    if sicher is None:
        sicher = z_oben + sicherheit + 3.0
    fasen = fb.fasen(form_teil, list(flaechen))
    if not fasen:
        raise ValueError(tr("fa.fehler.keine"))
    werte = fb.Fasenwerte(
        form=form,
        sicher=sicher,
        oben=z_oben,
        stufe=stufe if stufe and stufe > 0 else fb.STUFE,
        zustellung=zustellung if zustellung and zustellung > 0 else fb.ZUSTELLUNG,
        spitzenwinkel=spitzenwinkel,
        spitze=spitze,
        einfahrradius=einfahrradius,
        sicherheit=sicherheit,
        gleichlauf=gleichlauf,
    )
    netz_nah, netz_fern = fb.netze(form_teil, fasen, toleranz)
    return fb.planen(form_teil, netz_nah, netz_fern, werte, fasen, schritt, stand)


def vorschau(job, werkzeug, stufe, zustellung, flaechen, stand=None):
    """Die Bahn grob – für Fasen, Lagen, Zeit und ob es geht, im Assistenten: gröber vernetzt,
    weiter abgetastet. ValueError wie bahn_fuer()."""
    form, winkel, spitze = schneide_des_werkzeugs(werkzeug)
    return bahn_fuer(
        job,
        job.Model.Group,
        form,
        winkel,
        spitze,
        stufe,
        zustellung,
        flaechen,
        toleranz=hf.VORSCHAU_TOLERANZ,
        schritt=fb.VORSCHAU_SCHRITT,
        stand=stand,
    )


def lege_an(job, tc, stufe=fb.STUFE, zustellung=fb.ZUSTELLUNG, name=None, flaechen=()):
    """Legt „Fase“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Tiefen und Höhen
    wie FreeCADs Operationen; die Endtiefe ist der tiefste Fuß der Fasen. Gibt die Operation
    zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Fase")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = Fase(obj, "Fase", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    obj.Stufe = stufe
    obj.Zustellung = zustellung
    obj.Einfahrradius = float(tc.Tool.Diameter) / 2
    obj.Flaechen = list(flaechen)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(
        obj.Document, name or tr("fa.name", werkzeug=f"T{tc.ToolNumber}"), obj
    )
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _endtiefe(obj, job):
    """Die Endtiefe: der tiefste Fuß der Fasen."""
    try:
        fasen = fb.fasen(vs._teil(job.Model.Group), list(obj.Flaechen))
    except ValueError:
        return
    if fasen:
        obj.setExpression("FinalDepth", None)
        obj.FinalDepth = min(f.z_unten for f in fasen)


def aendere(obj, tc, stufe, zustellung, flaechen=None):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` ohne bleibt. Der Name folgt dem Werkzeug, solange es der
    vorgeschlagene ist."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, tr("fa.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Stufe = stufe
    obj.Zustellung = zustellung
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Fase T4“) – auch mit „ (2)“ dahinter?"""
    return namen.nach_vorlage(name, tr("fa.name", werkzeug="\0"))


def ist_fase_op(op):
    """Ist `op` eine Operation dieses Moduls – „Fase“?"""
    return isinstance(getattr(op, "Proxy", None), Fase)
