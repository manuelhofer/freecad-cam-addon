# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Räumen“ (W-006 S3f) – eine ebene Fläche nach oben (die Oberseite, der
Boden einer Tasche) mit Ringen räumen: bei vollem ap und schmalem ae, ohne Wenden, von außen
kreisend nach innen (offene Fläche) oder von innen nach außen (Tasche), im Gleichlauf.

Wie „Planfräsen“ (planfraesen) und „Kontur“ (kontur) eine eigene Operation (erbt FreeCADs
ObjectOp) mit Werkzeug-Controller, Kühlmittel und FreeCADs Tiefen und Höhen. Beim Neuberechnen
rechnet sie ihre Bahn aus Modell und Rohteil des Jobs (raeumen_bahn.planen) – in beiden
Varianten (Ringe vom Rohteil her, Ringe um die Inseln her), die schnellere zählt (Grundsatz 0)
–, mit dem Fräser aus dem ToolBit des Controllers und den Vorschüben des Controllers für die
Zeit.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Schruppen“, sonst „Planen“. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import bahn as bn
from . import hoehenfeld as hf
from . import kontur as ko
from . import kontur_bahn as kb
from . import namen
from . import planfraesen as pf
from . import raeumen_bahn as rb
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from .sprache import tr

GRUPPE = "Fräsen"  # die Gruppe der Eigenschaften
ZUSTELLUNG = 2.0  # mm – Vorschlag, solange nichts anderes gesagt ist
AUFMASS = 0.3  # mm – bleibt an Wänden und Inseln stehen
AUSTRITT = 50  # % des Vorschubs beim Austritt aus dem Rohteil
VARIANTEN = ("automatisch",) + rb.VARIANTEN


class Raeumen(PathOp.ObjectOp):
    """Proxy der Operation „Räumen“."""

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
        obj.Gleichlauf = True
        obj.Variante = "automatisch"
        obj.Einfahrradius = 0.0  # 0: der Vorschlag (der Fräserradius)
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
            ("App::PropertyStringList", "Flaechen", tr("ra.eigenschaft.flaechen")),
            ("App::PropertyLength", "Zustellung", tr("ra.eigenschaft.zustellung")),
            ("App::PropertyLength", "Zeilenabstand", tr("ra.eigenschaft.zeilenabstand")),
            ("App::PropertyLength", "Aufmass", tr("ra.eigenschaft.aufmass")),
            ("App::PropertyLength", "AufmassBoden", tr("ra.eigenschaft.aufmass_boden")),
            ("App::PropertyBool", "Gleichlauf", tr("ra.eigenschaft.gleichlauf")),
            ("App::PropertyEnumeration", "Variante", tr("ra.eigenschaft.variante")),
            ("App::PropertyLength", "Einfahrradius", tr("ko.eigenschaft.einfahrradius")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyAngle", "Eintauchwinkel", tr("vo.eigenschaft.eintauchwinkel")),
            ("App::PropertyPercent", "VorschubAustritt", tr("ko.eigenschaft.austritt")),
            ("App::PropertyInteger", "Ebenen", tr("pf.eigenschaft.ebenen")),
            ("App::PropertyInteger", "Lagen", tr("pf.eigenschaft.lagen")),
            ("App::PropertyInteger", "Ringe", tr("ra.eigenschaft.ringe")),
            ("App::PropertyInteger", "Laeufe", tr("ra.eigenschaft.laeufe")),
            ("App::PropertyString", "Gerechnet", tr("ra.eigenschaft.gerechnet")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
                neu.append(name)
                if name == "Variante":
                    obj.Variante = list(VARIANTEN)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Ebenen", "Lagen", "Ringe", "Laeufe", "Gerechnet"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(
                obj, self.job, self.model, self.horizFeed * 60.0, vo.eintauchvorschub(self)
            )
        except ValueError as fehler:
            obj.Ebenen = obj.Lagen = obj.Ringe = obj.Laeufe = 0
            obj.Gerechnet = ""
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Ebenen, obj.Lagen = ergebnis.flaechen, ergebnis.lagen
        obj.Ringe, obj.Laeufe = ergebnis.ringe, ergebnis.laeufe
        obj.Gerechnet = gerechnet_text(ergebnis)
        self.commandlist.extend(
            bn.befehle(
                ergebnis.punkte,
                self.horizFeed * 60.0,  # CAM führt mm/s
                vo.eintauchvorschub(self),
            )
        )


def gerechnet_text(ergebnis):
    """„rohteil 36,9 min · inseln 41,4 min“ – die Varianten mit ihrer Zeit, die gewählte vorn."""
    teile = [f"{ergebnis.variante} {ergebnis.zeit:.1f} min"]
    for name, zeit in ergebnis.zeiten.items():
        if name != ergebnis.variante:
            teile.append(f"{name} {zeit:.1f} min")
    return " · ".join(teile)


def rechne(obj, job, modell, vorschub=0.0, eintauchen=0.0):
    """Die Bahn (raeumen_bahn.Raeumbahn) für die Operation `obj` im Job; `vorschub` und
    `eintauchen` (mm/min) für die Zeit, nach der die Variante fällt. ValueError mit einem Satz,
    wenn es nicht geht."""
    form = vs.form_des_controllers(obj.ToolController)
    if form is None:
        raise ValueError(tr("ra.fehler.form"))
    einfahrradius = float(obj.Einfahrradius)
    variante = str(obj.Variante)
    return bahn_fuer(
        job,
        modell,
        form,
        float(obj.Zustellung),
        float(obj.Zeilenabstand),
        float(obj.Aufmass),
        vo.flaechen(obj),
        aufmass_boden=float(obj.AufmassBoden),
        gleichlauf=bool(obj.Gleichlauf),
        variante=variante if variante in rb.VARIANTEN else None,
        einfahrradius=einfahrradius if einfahrradius > 0 else None,
        schneidenlaenge=ko.schneidenlaenge(obj.ToolController),
        oben=min(float(obj.StartDepth), pf.rohteil_von_oben(job)[4]),  # nie über dem Rohteil
        sicher=float(obj.SafeHeight),
        sicherheit=float(obj.Sicherheitsabstand),
        eintauchwinkel=float(obj.Eintauchwinkel),
        austritt=float(obj.VorschubAustritt) / 100.0,
        vorschub=vorschub,
        eintauchen=eintauchen,
    )


def bahn_fuer(
    job,
    modell,
    form,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    flaechen=(),
    aufmass_boden=0.0,
    gleichlauf=True,
    variante=None,
    einfahrradius=None,
    schneidenlaenge=0.0,
    oben=None,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    eintauchwinkel=vb.EINTAUCHWINKEL,
    austritt=rb.AUSTRITT_ANTEIL,
    toleranz=hf.TOLERANZ,
    schritt=rb.SCHRITT,
    vorschub=0.0,
    eintauchen=0.0,
):
    """Die Bahn „Räumen“ für Modell und Rohteil des Jobs. `flaechen`: die gewählten Flächen
    („Face6“ …) – geräumt werden die ebenen nach oben darunter; leer: die Oberseite des Teils.
    `oben`: z, wo die Lagen beginnen (None: die Oberkante des Rohteils); `sicher`: z für den
    Eilgang (None: Oberkante + Sicherheitsabstand + 3 mm); `vorschub` und `eintauchen` (mm/min)
    für die Zeit, nach der die Variante fällt. ValueError mit einem Satz, wenn es nicht
    geht."""
    form_teil = vs._teil(modell)
    x_von, x_bis, y_von, y_bis, z_oben = pf.rohteil_von_oben(job)
    if oben is None:
        oben = z_oben
    if sicher is None:
        sicher = oben + sicherheit + 3.0
    namen = list(flaechen) or hf.oberseite(form_teil)
    ebenen = hf.ebenen_oben(form_teil, namen)
    if not ebenen:
        raise ValueError(tr("ra.fehler.keine_ebene"))
    werte = rb.Raeumwerte(
        form=form,
        zustellung=zustellung,
        zeilenabstand=zeilenabstand,
        aufmass=aufmass,
        oben=oben,
        sicher=sicher,
        rohteil=(x_von, x_bis, y_von, y_bis),
        aufmass_boden=aufmass_boden,
        gleichlauf=gleichlauf,
        variante=variante,
        einfahrradius=einfahrradius,
        schneidenlaenge=schneidenlaenge,
        sicherheit=sicherheit,
        eintauchwinkel=eintauchwinkel,
        austritt=austritt,
        vorschub=vorschub,
        eintauchen=eintauchen,
    )
    netz = hf.netze_je_hoehe(form_teil, ebenen, toleranz)
    return rb.planen(netz, werte, ebenen, konturen_des_teils(form_teil), schritt)


def konturen_des_teils(form_teil):
    """Die Unterkanten aller Wände des Teils als Konturen – leer, wenn es keine Wand gibt."""
    namen = [f"Face{i + 1}" for i in range(len(form_teil.Faces))]
    try:
        return kb.konturen(form_teil, namen)
    except ValueError:
        return []


def vorschau(
    job,
    modell,
    form,
    zustellung,
    zeilenabstand,
    aufmass,
    flaechen,
    aufmass_boden=0.0,
    gleichlauf=True,
    schneidenlaenge=0.0,
    vorschub=0.0,
    eintauchen=0.0,
):
    """Die Bahn grob – für Lagen, Ringe, Zeit und ob es geht, im Assistenten: gröber vernetzt,
    gröberes Raster. ValueError wie bahn_fuer()."""
    return bahn_fuer(
        job,
        modell,
        form,
        zustellung,
        zeilenabstand,
        aufmass,
        flaechen,
        aufmass_boden=aufmass_boden,
        gleichlauf=gleichlauf,
        schneidenlaenge=schneidenlaenge,
        toleranz=hf.VORSCHAU_TOLERANZ,
        schritt=rb.VORSCHAU_SCHRITT,
        vorschub=vorschub,
        eintauchen=eintauchen,
    )


def lege_an(
    job,
    tc,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    aufmass_boden=0.0,
    gleichlauf=True,
    name=None,
    flaechen=(),
):
    """Legt „Räumen“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Tiefen und
    Höhen wie FreeCADs Operationen (planfraesen._hoehen); die Endtiefe ist die tiefste Fläche
    plus Aufmaß am Boden. Gibt die Operation zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Raeumen")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = Raeumen(obj, "Raeumen", job)
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
    obj.Gleichlauf = bool(gleichlauf)
    obj.Flaechen = list(flaechen)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(
        obj.Document, name or tr("ra.name", werkzeug=f"T{tc.ToolNumber}"), obj
    )
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _endtiefe(obj, job):
    """Die Endtiefe: die tiefste gewählte Fläche plus Aufmaß am Boden – zum Lesen; die Bahn
    rechnet aus den Flächen."""
    try:
        form_teil = vs._teil(job.Model.Group)
        namen = list(obj.Flaechen) or hf.oberseite(form_teil)
        ebenen = hf.ebenen_oben(form_teil, namen)
    except ValueError:
        ebenen = []
    if ebenen:
        obj.setExpression("FinalDepth", None)
        obj.FinalDepth = min(e.z for e in ebenen) + float(obj.AufmassBoden)


def aendere(
    obj,
    tc,
    zustellung,
    zeilenabstand,
    aufmass,
    aufmass_boden=0.0,
    gleichlauf=True,
    flaechen=None,
):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` ohne bleibt. Der Name folgt dem Werkzeug, solange es der
    vorgeschlagene ist."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, tr("ra.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Zustellung = zustellung
    obj.Zeilenabstand = zeilenabstand
    obj.Aufmass = aufmass
    obj.AufmassBoden = aufmass_boden
    obj.Gleichlauf = bool(gleichlauf)
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Räumen T1“) – auch mit „ (2)“ dahinter?"""
    return namen.nach_vorlage(name, tr("ra.name", werkzeug="\0"))


def ist_raeumen(op):
    """Ist `op` eine Operation dieses Moduls – „Räumen“?"""
    return isinstance(getattr(op, "Proxy", None), Raeumen)
