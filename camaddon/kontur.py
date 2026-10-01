# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Kontur“ (W-006 S3, 4.1 Punkt 4) – Schruppen und Schlichten an Wänden
in einem Schritt.

Wie „Planfräsen“ (planfraesen) eine eigene Operation (erbt FreeCADs ObjectOp) mit
Werkzeug-Controller, Kühlmittel und FreeCADs Tiefen und Höhen. Beim Neuberechnen rechnet sie
ihre Bahn aus Modell und Rohteil des Jobs (kontur_bahn.planen): an den gewählten Wänden
entlang – ihre Unterkanten zu Konturen verbunden, versetzt um Radius + Aufmaß in Lagen, dann
bei Radius in einem Zug –, mit tangentialem Ein- und Ausfahren, mit dem Fräser aus dem ToolBit
des Controllers.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Schruppen“, sonst „Schlichten“. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import bahn as bn
from . import hoehenfeld as hf
from . import kontur_bahn as kb
from . import namen
from . import planfraesen as pf
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from .sprache import tr

GRUPPE = "Fräsen"  # die Gruppe der Eigenschaften
ZUSTELLUNG = 2.0  # mm – Vorschlag, solange nichts anderes gesagt ist
AUFMASS = 0.3  # mm – bleibt beim Schruppen fürs Schlichten stehen
AUSTRITT = 50  # % des Vorschubs beim Austritt aus dem Rohteil


class Kontur(PathOp.ObjectOp):
    """Proxy der Operation „Kontur“."""

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
        obj.Schlichten = True
        obj.Breite = 0.0  # 0: so viel, wie das Rohteil sagt
        obj.Tiefer = 0.0
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
            ("App::PropertyStringList", "Flaechen", tr("ko.eigenschaft.flaechen")),
            ("App::PropertyLength", "Zustellung", tr("ko.eigenschaft.zustellung")),
            ("App::PropertyLength", "Zeilenabstand", tr("ko.eigenschaft.zeilenabstand")),
            ("App::PropertyLength", "Aufmass", tr("ko.eigenschaft.aufmass")),
            ("App::PropertyBool", "Schlichten", tr("ko.eigenschaft.schlichten")),
            ("App::PropertyLength", "Breite", tr("ko.eigenschaft.breite")),
            ("App::PropertyLength", "Tiefer", tr("ko.eigenschaft.tiefer")),
            ("App::PropertyLength", "Einfahrradius", tr("ko.eigenschaft.einfahrradius")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyAngle", "Eintauchwinkel", tr("vo.eigenschaft.eintauchwinkel")),
            ("App::PropertyPercent", "VorschubAustritt", tr("ko.eigenschaft.austritt")),
            ("App::PropertyInteger", "Konturen", tr("ko.eigenschaft.konturen")),
            ("App::PropertyInteger", "Lagen", tr("ko.eigenschaft.lagen")),
            ("App::PropertyInteger", "Bahnen", tr("ko.eigenschaft.bahnen")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Konturen", "Lagen", "Bahnen"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(obj, self.job, self.model)
        except ValueError as fehler:
            obj.Konturen = obj.Lagen = obj.Bahnen = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Konturen, obj.Lagen, obj.Bahnen = ergebnis.konturen, ergebnis.lagen, ergebnis.bahnen
        self.commandlist.extend(
            bn.befehle(
                ergebnis.punkte,
                self.horizFeed * 60.0,  # CAM führt mm/s
                vo.eintauchvorschub(self),
            )
        )


def schneidenlaenge(tc):
    """Die Schneidenlänge des Werkzeugs im Controller (mm) – 0, wenn das ToolBit keine hat."""
    werkzeug = getattr(tc, "Tool", None)
    wert = getattr(werkzeug, "CuttingEdgeHeight", None)
    try:
        return max(0.0, float(getattr(wert, "Value", wert) or 0.0))
    except (TypeError, ValueError):
        return 0.0


def rechne(obj, job, modell):
    """Die Bahn (kontur_bahn.Konturbahn) für die Operation `obj` im Job. ValueError mit einem
    Satz, wenn es nicht geht."""
    form = vs.form_des_controllers(obj.ToolController)
    if form is None:
        raise ValueError(tr("ko.fehler.form"))
    einfahrradius = float(obj.Einfahrradius)
    return bahn_fuer(
        job,
        modell,
        form,
        float(obj.Zustellung),
        float(obj.Zeilenabstand),
        float(obj.Aufmass),
        bool(obj.Schlichten),
        vo.flaechen(obj),
        breite=float(obj.Breite),
        tiefer=float(obj.Tiefer),
        einfahrradius=einfahrradius if einfahrradius > 0 else None,
        schneidenlaenge=schneidenlaenge(obj.ToolController),
        oben=min(float(obj.StartDepth), pf.rohteil_von_oben(job)[4]),  # nie über dem Rohteil
        sicher=float(obj.SafeHeight),
        sicherheit=float(obj.Sicherheitsabstand),
        eintauchwinkel=float(obj.Eintauchwinkel),
        austritt=float(obj.VorschubAustritt) / 100.0,
    )


def bahn_fuer(
    job,
    modell,
    form,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    schlichten=True,
    flaechen=(),
    breite=0.0,
    tiefer=0.0,
    einfahrradius=None,
    schneidenlaenge=0.0,
    oben=None,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    eintauchwinkel=vb.EINTAUCHWINKEL,
    austritt=kb.AUSTRITT_ANTEIL,
    toleranz=hf.TOLERANZ,
    schritt=kb.SCHRITT,
):
    """Die Bahn „Kontur“ für Modell und Rohteil des Jobs an den Wänden `flaechen` („Face6“ …).
    `oben`: z, wo die Lagen beginnen (None: die Oberkante des Rohteils); `sicher`: z für den
    Eilgang (None: Oberkante + Sicherheitsabstand + 3 mm). ValueError mit einem Satz, wenn es
    nicht geht."""
    form_teil = vs._teil(modell)
    x_von, x_bis, y_von, y_bis, z_oben = pf.rohteil_von_oben(job)
    if oben is None:
        oben = z_oben
    if sicher is None:
        sicher = oben + sicherheit + 3.0
    konturen = kb.konturen(form_teil, list(flaechen))
    werte = kb.Konturwerte(
        form=form,
        zustellung=zustellung,
        zeilenabstand=zeilenabstand,
        aufmass=aufmass,
        schlichten=schlichten,
        oben=oben,
        sicher=sicher,
        rohteil=(x_von, x_bis, y_von, y_bis),
        breite=breite,
        tiefer=tiefer,
        einfahrradius=einfahrradius,
        schneidenlaenge=schneidenlaenge,
        sicherheit=sicherheit,
        eintauchwinkel=eintauchwinkel,
        austritt=austritt,
    )
    waende = kb.waende(form_teil, list(flaechen))
    netz_nah, netz_fern = hf.netze_ohne(
        form_teil, [kb.ohne_flaechen(form_teil, waende), [w.name for w in waende]], toleranz
    )
    return kb.planen(netz_nah, werte, konturen, schritt, netz_fern)


def vorschau(
    job,
    modell,
    form,
    zustellung,
    zeilenabstand,
    aufmass,
    schlichten,
    flaechen,
    breite=0.0,
    schneidenlaenge=0.0,
):
    """Die Bahn grob – für Lagen, Bahnen, Zeit und ob es geht, im Assistenten: gröber vernetzt,
    weiter abgetastet. ValueError wie bahn_fuer()."""
    return bahn_fuer(
        job,
        modell,
        form,
        zustellung,
        zeilenabstand,
        aufmass,
        schlichten,
        flaechen,
        breite=breite,
        schneidenlaenge=schneidenlaenge,
        toleranz=hf.VORSCHAU_TOLERANZ,
        schritt=kb.VORSCHAU_SCHRITT,
    )


def lege_an(
    job,
    tc,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    schlichten=True,
    breite=0.0,
    name=None,
    flaechen=(),
):
    """Legt „Kontur“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Tiefen und
    Höhen wie FreeCADs Operationen (planfraesen._hoehen); die Endtiefe ist die tiefste
    Unterkante. Gibt die Operation zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Kontur")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = Kontur(obj, "Kontur", job)
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
    obj.Breite = breite
    obj.Flaechen = list(flaechen)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(
        obj.Document, name or tr("ko.name", werkzeug=f"T{tc.ToolNumber}"), obj
    )
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _endtiefe(obj, job):
    """Die Endtiefe: die tiefste Unterkante der Wände minus „tiefer“ – zum Lesen; die Bahn
    rechnet aus den Wänden."""
    try:
        form_teil = vs._teil(job.Model.Group)
        waende = kb.waende(form_teil, list(obj.Flaechen))
    except ValueError:
        waende = []
    if waende:
        obj.setExpression("FinalDepth", None)
        obj.FinalDepth = min(w.z_unten for w in waende) - float(obj.Tiefer)


def aendere(obj, tc, zustellung, zeilenabstand, aufmass, schlichten, breite=0.0, flaechen=None):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` ohne bleibt. Der Name folgt dem Werkzeug, solange es der
    vorgeschlagene ist."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, tr("ko.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Zustellung = zustellung
    obj.Zeilenabstand = zeilenabstand
    obj.Aufmass = aufmass
    obj.Schlichten = bool(schlichten)
    obj.Breite = breite
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Kontur T1“) – auch mit „ (2)“ dahinter?"""
    return namen.nach_vorlage(name, tr("ko.name", werkzeug="\0"))


def ist_kontur(op):
    """Ist `op` eine Operation dieses Moduls – „Kontur“?"""
    return isinstance(getattr(op, "Proxy", None), Kontur)
