# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „3D-Schlichten“ (W-006 4.2 Punkt 3) – Freiformflächen in parallelen
Zeilen, die Spitze auf der Hüllfläche des ganzen Teils, der Zeilenabstand aus der Grathöhe
(schlichten3d_bahn). Mit dem Durchmesser des Fräsers davor (`DurchmesserDavor` > 0) ist sie
„Restschlichten“ (W-006 4.2 Punkt 8): nur dort, wo der größere Fräser davor mehr stehen ließ.
Mit `Anstellen` steht ein Kugelfräser angestellt (5 Achsen simultan, angestellt.py): Die Bahn
bleibt die senkrechte (die Kugel fährt sie), dazu je Satz die Werkzeugachse (`Werkzeugachsen`).

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

from . import angestellt as an
from . import bahn as bn
from . import fraeserform as ff
from . import freiwege as fw
from . import namen
from . import planfraesen as pf
from . import schlichten3d_bahn as sb
from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from . import wegkippen as wk
from .sprache import tr

GRUPPE = "Fräsen"
GRUPPE_5ACHS = "5-Achs"
RICHTUNGEN = ("auto", "x", "y", "spirale", "flaeche", "aequidistant", "winkel")


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
        obj.Winkel = sb.WINKEL_VORGABE
        obj.Einseitig = False
        obj.Sicherheitsabstand = vb.SICHERHEIT
        obj.DurchmesserDavor = 0.0  # 0: ganz schlichten; sonst Restschlichten
        obj.EckenradiusDavor = 0.0
        self._anstellen_vorbelegen(obj)
        self._editormodi(obj)

    @staticmethod
    def _anstellen_vorbelegen(obj):
        obj.Anstellen = False
        obj.Anstellwinkel = an.WINKEL
        obj.Kippachse = list(an.UM)
        obj.Kippachse = an.UM[0]
        obj.Werkzeugachsen = []
        obj.Wegkippen = False
        obj.WegkippenBis = wk.WINKEL_MAX
        obj.SpielHalter = wk.SPIEL_HALTER
        obj.SpielSchaft = wk.SPIEL_SCHAFT

    def opOnDocumentRestored(self, obj):
        neu = self._eigenschaften(obj)
        if "Anstellen" in neu:
            self._anstellen_vorbelegen(obj)  # gespeichert vor dem Anstellen: senkrecht
        elif "Wegkippen" in neu:
            obj.Wegkippen = False  # gespeichert vor dem Wegkippen: wie damals
            obj.WegkippenBis = wk.WINKEL_MAX
        if "SpielHalter" in neu and "Anstellen" not in neu:
            obj.SpielHalter = wk.SPIEL_HALTER
            obj.SpielSchaft = wk.SPIEL_SCHAFT
        if "Grenzwinkel" in neu:
            obj.Grenzwinkel = 0.0  # gespeichert vor Steil/Flach: wie damals nur Zeilen
        if "Winkel" in neu:
            obj.Winkel = sb.WINKEL_VORGABE  # gilt nur mit der Richtung „winkel“
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
            ("App::PropertyAngle", "Winkel", tr("s3.eigenschaft.winkel")),
            ("App::PropertyBool", "Einseitig", tr("s3.eigenschaft.einseitig")),
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
        for typ, name, text in (
            ("App::PropertyBool", "Anstellen", tr("an.eigenschaft.anstellen")),
            ("App::PropertyAngle", "Anstellwinkel", tr("an.eigenschaft.winkel")),
            ("App::PropertyEnumeration", "Kippachse", tr("an.eigenschaft.kippachse")),
            ("App::PropertyVectorList", "Werkzeugachsen", tr("an.eigenschaft.achsen")),
            ("App::PropertyBool", "Wegkippen", tr("wk.eigenschaft.wegkippen")),
            ("App::PropertyAngle", "WegkippenBis", tr("wk.eigenschaft.bis")),
            ("App::PropertyLength", "SpielHalter", tr("wk.eigenschaft.spiel_halter")),
            ("App::PropertyLength", "SpielSchaft", tr("wk.eigenschaft.spiel_schaft")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE_5ACHS, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Zeilen", "Hoehenlinien", "Umlaeufe", "Abstand"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis
        obj.setEditorMode("Werkzeugachsen", 2)  # gerechnet, je Satz – nicht zum Ansehen

    def execute(self, obj):
        """Wie jede Operation – mit `Anstellen` danach je Satz der fertigen Bahn die
        Werkzeugachse (angestellt.achsen): Erst jetzt stehen alle Sätze fest, auch die, die
        FreeCAD vorn und hinten anfügt."""
        ergebnis = super().execute(obj)
        achsen = []
        if _gekippt(obj) and obj.Active and getattr(obj, "Path", None):
            achsen = self._achsen(obj)
        obj.Werkzeugachsen = [FreeCAD.Vector(*a) for a in achsen]
        return ergebnis

    def _achsen(self, obj):
        """Die Werkzeugachsen je Satz – leer (senkrecht), wenn es kein Kugelfräser ist."""
        radius = an.radius_von(obj)
        if radius is None:
            FreeCAD.Console.PrintWarning(tr("an.nur_kugel", operation=obj.Label) + "\n")
            return []
        try:
            form_teil = vs._teil(self.model)
        except (AttributeError, ValueError):
            return []
        if getattr(obj, "Wegkippen", False):
            return self._wegkippen(obj, form_teil, radius)
        return an.achsen(
            list(obj.Path.Commands),
            form_teil,
            radius,
            aufmass=float(obj.Aufmass),
            um=str(obj.Kippachse),
            winkel=float(obj.Anstellwinkel),
        )

    @staticmethod
    def _wegkippen(obj, form_teil, radius):
        """Die Werkzeugachsen fürs Wegkippen (wegkippen.achsen) – mit Halter und Auskragung, wie
        „Auf der Maschine prüfen“ sie nimmt; reicht auch der größte Winkel nicht, ein Satz."""
        try:
            halter, schaft, auskragung = wk.einspannung(obj.ToolController)
        except ValueError as grund:
            FreeCAD.Console.PrintWarning(f"{obj.Label}: {grund}\n")
            return []
        ergebnis = wk.achsen(
            list(obj.Path.Commands),
            form_teil,
            radius,
            halter,
            schaft,
            auskragung,
            winkel_max=float(obj.WegkippenBis),
            spiel_halter=float(obj.SpielHalter),
            spiel_schaft=float(obj.SpielSchaft),
        )
        if ergebnis.anstoesse:
            FreeCAD.Console.PrintWarning(
                tr(
                    "wk.anstoesse",
                    operation=obj.Label,
                    stellen=ergebnis.anstoesse,
                    auskragung=f"{auskragung:.1f}",
                    winkel=f"{float(obj.WegkippenBis):.0f}",
                )
                + "\n"
            )
        return ergebnis.achsen

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
        punkte = ergebnis.punkte
        if _gekippt(obj):
            punkte = an.gerade(punkte)  # eine Achse je Satz: Bögen als Geraden, kurze Sätze
        else:
            # Im Freien mit dem Freivorschub, kurz vor dem Material langsam (freiwege, Manuel
            # 2026-10-04: „gib Gas bis kurz davor … bei allen Strategien“).
            punkte, _schnell = fw.fuer_operation(self.job, obj, punkte, self.horizFeed * 60.0)
        self.commandlist.extend(
            bn.befehle(punkte, self.horizFeed * 60.0, vo.eintauchvorschub(self))
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
        winkel=float(obj.Winkel),
        einseitig=bool(obj.Einseitig),
        grenzwinkel=float(obj.Grenzwinkel),
        oben=min(float(obj.StartDepth), pf.rohteil_von_oben(job)[4]),
        sicher=float(obj.SafeHeight),
        sicherheit=float(obj.Sicherheitsabstand),
        vorschub=vorschub,
        eintauchen=eintauchen,
        davor=form_davor(obj),
        gleichlauf=sp.fuer_m3(True, obj.ToolController),
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
    winkel=sb.WINKEL_VORGABE,
    einseitig=False,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    vorschub=0.0,
    eintauchen=0.0,
    schritt=sb.SCHRITT,
    toleranz=sb.TOLERANZ_NETZ,
    raster=sb.RASTER,
    davor=None,
    gleichlauf=True,
):
    """Die Bahn „3D-Schlichten“ über die Flächen `flaechen` des Modells – mit `davor` (Form des
    Fräsers davor) nur der Rest; `gleichlauf` False: die Höhenlinien mit dem Material links (M4).
    ValueError mit einem Satz, wenn es nicht geht."""
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
        winkel=winkel,
        einseitig=einseitig,
        grenzwinkel=grenzwinkel,
        sicherheit=sicherheit,
        schritt=schritt,
        raster=raster,
        vorschub=vorschub,
        eintauchen=eintauchen,
        davor=davor,
        gleichlauf=gleichlauf,
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


def _gekippt(obj):
    """Kippt die Achse – angestellt oder weggekippt?"""
    return bool(getattr(obj, "Anstellen", False) or getattr(obj, "Wegkippen", False))


def stelle_an(obj, anstellen, kippachse=None):
    """Setzt „Anstellen“ (der Kugelfräser angestellt, 5 Achsen simultan) – angestellt mit der
    Kippachse `kippachse` („X“, „Y“; None: wie sie ist). Ohne eigene Transaktion."""
    obj.Anstellen = bool(anstellen)
    if anstellen and kippachse in an.UM:
        obj.Kippachse = kippachse


def stelle_weg(obj, wegkippen):
    """Setzt „Wegkippen“ (5 Achsen simultan, wegkippen.py). Ohne eigene Transaktion."""
    obj.Wegkippen = bool(wegkippen)


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
