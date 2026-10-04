# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Nut“ (W-006 4.1 Punkt 6) – Langlöcher mit einem Schaftfräser, der nicht
breiter ist als sie: in Bögen bei voller Schneide – geschlossene nach einer Helix, offene von
außen; ist die Nut kaum breiter als der Fräser, in einer Zickzack-Rampe; zuletzt die Wand
rundum (nut_bahn).

Wie „Bohrung fräsen“ (bohrung) eine eigene Operation (erbt FreeCADs ObjectOp) mit
Werkzeug-Controller, Kühlmittel und FreeCADs Tiefen und Höhen. Beim Neuberechnen rechnet sie ihre
Bahn aus Modell und Rohteil des Jobs, mit dem Fräser aus dem ToolBit des Controllers und seinen
Vorschüben für die Zeit.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Dynamisch“, sonst „Schruppen“, sonst „Vollnut“. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import bahn as bn
from . import freiwege as fw
from . import kontur as ko
from . import materialstand as mst
from . import namen
from . import nut_bahn as nb
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


class Nut(PathOp.ObjectOp):
    """Proxy der Operation „Nut“."""

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
        obj.Schlichten = True
        obj.Gleichlauf = True
        obj.Tiefer = nb.TIEFER
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
            ("App::PropertyStringList", "Flaechen", tr("nt.eigenschaft.flaechen")),
            ("App::PropertyLength", "Zustellung", tr("nt.eigenschaft.zustellung")),
            ("App::PropertyLength", "Zeilenabstand", tr("nt.eigenschaft.zeilenabstand")),
            ("App::PropertyLength", "Aufmass", tr("bo.eigenschaft.aufmass")),
            ("App::PropertyBool", "Schlichten", tr("nt.eigenschaft.schlichten")),
            ("App::PropertyBool", "Gleichlauf", tr("ra.eigenschaft.gleichlauf")),
            ("App::PropertyLength", "Tiefer", tr("nt.eigenschaft.tiefer")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyAngle", "Eintauchwinkel", tr("nt.eigenschaft.eintauchwinkel")),
            ("App::PropertyInteger", "Nuten", tr("nt.eigenschaft.nuten")),
            ("App::PropertyInteger", "Lagen", tr("pf.eigenschaft.lagen")),
            ("App::PropertyInteger", "Boegen", tr("nt.eigenschaft.boegen")),
            ("App::PropertyString", "Materialstand", tr("ms.eigenschaft.materialstand")),
            ("App::PropertyStringList", "Eintauchstellen", tr("nt.eigenschaft.eintauchstellen")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Nuten", "Lagen", "Boegen"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis
        obj.setEditorMode("Materialstand", 2)  # woraus gerechnet (gui_materialstand)
        if "Kreise" in obj.PropertiesList:  # bis P-2026-10-02-52 (Trochoide): ausgeblendet
            obj.setEditorMode("Kreise", 2)

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(
                obj, self.job, self.model, self.horizFeed * 60.0, vo.eintauchvorschub(self)
            )
        except ValueError as fehler:
            obj.Nuten = obj.Lagen = obj.Boegen = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Nuten, obj.Lagen, obj.Boegen = ergebnis.nuten, ergebnis.lagen, ergebnis.boegen
        # Im Freien mit dem Freivorschub, kurz vor dem Material langsam (freiwege, Manuel
        # 2026-10-04: „gib Gas bis kurz davor … bei allen Strategien“).
        punkte, _schnell = fw.fuer_operation(self.job, obj, ergebnis.punkte, self.horizFeed * 60.0)
        self.commandlist.extend(
            bn.befehle(punkte, self.horizFeed * 60.0, vo.eintauchvorschub(self))
        )


def rechne(obj, job, modell, vorschub=0.0, eintauchen=0.0):
    """Die Bahn (nut_bahn.Nutbahn) für die Operation `obj` im Job. ValueError mit einem Satz,
    wenn es nicht geht."""
    form = vs.form_des_controllers(obj.ToolController)
    if form is None or vp.ebener_radius(form) <= 0:
        raise ValueError(tr("nt.fehler.form"))
    # Was die Operationen davor schon weggenommen haben (W-012) – und woraus das gerechnet ist:
    # Ändert sich davor etwas, rechnet gui_materialstand die Nut neu.
    stand = mst.fuer(job, vor=obj)
    if "Materialstand" in obj.PropertiesList:
        obj.Materialstand = mst.kennung_vor(job, obj)
    return bahn_fuer(
        job,
        modell,
        float(form.radius),
        float(obj.Zustellung),
        float(obj.Zeilenabstand),
        float(obj.Aufmass),
        vo.flaechen(obj),
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
        stand=stand,
        eintauchen_bei=eintauchstellen(obj),
    )


def bahn_fuer(
    job,
    modell,
    fraeser_radius,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    flaechen=(),
    schlichten=True,
    gleichlauf=True,
    tiefer=nb.TIEFER,
    schneidenlaenge=0.0,
    oben=None,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    eintauchwinkel=vb.EINTAUCHWINKEL,
    vorschub=0.0,
    eintauchen=0.0,
    stand=None,
    eintauchen_bei=None,
):
    """Die Bahn „Nut“ für Modell und Rohteil des Jobs. `flaechen`: Wände oder Grund der Nuten
    („Face7“ …); `stand`: der Materialstand davor (materialstand) – die Lagen beginnen dann,
    wo in der Nut noch Material ist. ValueError mit einem Satz, wenn es nicht geht."""
    form_teil = vs._teil(modell)
    *_rohteil, z_oben = pf.rohteil_von_oben(job)
    if oben is None:
        oben = z_oben
    if sicher is None:
        sicher = oben + sicherheit + 3.0
    liste = nb.nuten(form_teil, list(flaechen))
    if not liste:
        raise ValueError(tr("nt.fehler.keine"))
    werte = nb.Nutwerte(
        fraeser_radius=fraeser_radius,
        zustellung=zustellung,
        zeilenabstand=zeilenabstand,
        oben=oben,
        sicher=sicher,
        aufmass=aufmass,
        schlichten=schlichten,
        gleichlauf=gleichlauf,
        tiefer=tiefer,
        schneidenlaenge=schneidenlaenge,
        eintauchwinkel=eintauchwinkel,
        sicherheit=sicherheit,
        vorschub=vorschub,
        eintauchen=eintauchen,
        eintauchen_bei=eintauchen_bei or None,
    )
    return nb.planen(werte, liste, stand)


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
    schlichten=True,
    gleichlauf=True,
    name=None,
    flaechen=(),
    eintauchwinkel=None,
    eintauchstellen=None,
):
    """Legt „Nut“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Tiefen und Höhen
    wie FreeCADs Operationen; die Endtiefe ist der tiefste Grund. Gibt die Operation zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Nut")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = Nut(obj, "Nut", job)
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
    obj.Schlichten = bool(schlichten)
    obj.Gleichlauf = bool(gleichlauf)
    obj.Flaechen = list(flaechen)
    if eintauchwinkel:  # der Winkel am Fräser, wie in der Vorschau des Assistenten
        obj.Eintauchwinkel = float(eintauchwinkel)
    obj.Eintauchstellen = als_texte(eintauchstellen)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(
        obj.Document, name or tr("nt.name", werkzeug=f"T{tc.ToolNumber}"), obj
    )
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _endtiefe(obj, job):
    """Die Endtiefe: der tiefste Grund der Nuten (durchgehende um „Tiefer“ darunter)."""
    try:
        liste = nb.nuten(vs._teil(job.Model.Group), list(obj.Flaechen))
    except ValueError:
        liste = []
    if liste:
        tief = min(n.z_unten - float(obj.Tiefer) if n.durch else n.z_unten for n in liste)
        obj.setExpression("FinalDepth", None)
        obj.FinalDepth = tief


def aendere(
    obj,
    tc,
    zustellung,
    zeilenabstand,
    aufmass,
    schlichten=True,
    gleichlauf=True,
    flaechen=None,
    eintauchwinkel=None,
    eintauchstellen=None,
):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` ohne bleibt. Der Name folgt dem Werkzeug, solange es der
    vorgeschlagene ist."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, tr("nt.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Zustellung = zustellung
    obj.Zeilenabstand = zeilenabstand
    obj.Aufmass = aufmass
    obj.Schlichten = bool(schlichten)
    obj.Gleichlauf = bool(gleichlauf)
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    if eintauchwinkel:
        obj.Eintauchwinkel = float(eintauchwinkel)
    if eintauchstellen is not None:
        obj.Eintauchstellen = als_texte(eintauchstellen)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def eintauchstellen(obj):
    """Die gewählten Eintauchstellen der Operation (W-012 E1): {Schlüssel der Nut: Anteil von A
    nach B} aus ihrer Eigenschaft „Eintauchstellen“ („Face7=0.25“ je Nut); ohne Wahl leer – der
    Vorschlag."""
    ergebnis = {}
    for text in getattr(obj, "Eintauchstellen", None) or []:
        name, _gleich, wert = str(text).partition("=")
        try:
            ergebnis[name] = min(1.0, max(0.0, float(wert)))
        except ValueError:
            continue
    return ergebnis


def als_texte(stellen):
    """{Schlüssel: Anteil} als Liste für die Eigenschaft „Eintauchstellen“."""
    return [f"{name}={float(anteil):.4f}" for name, anteil in sorted((stellen or {}).items())]


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Nut T1“) – auch mit „ (2)“ dahinter?"""
    return namen.nach_vorlage(name, tr("nt.name", werkzeug="\0"))


def ist_nut(op):
    """Ist `op` eine Operation dieses Moduls – „Nut“?"""
    return isinstance(getattr(op, "Proxy", None), Nut)
