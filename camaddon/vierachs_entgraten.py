# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Rundum entgraten“ (Spezifikation W-003, Stufe V4d; W-006 S2).

Wie „Rundum schruppen“ (vierachs_operation) eine Operation mit Werkzeug-Controller und
Kühlmittel, ohne Höhen und Tiefen in Z. Beim Neuberechnen rechnet sie ihre Bahn aus Modell und
Stange des Jobs (vierachs_entgratbahn.entgraten): An den Außenkanten der gewählten Flächen –
wo sie mit einer anderen Fläche nach außen knicken, auch zum Rest des Teils – fährt der
Fasenfräser aus dem ToolBit des Controllers entlang (oder ein Kugelfräser als Kantenbruch),
die Rundachse dreht mit; die Spitze sinkt an jedem Punkt bis an die Kante und um die
Fasenbreite tiefer.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Fasen“, sonst „Schlichten“ oder „Schruppen“ – und für die Kollisionsprüfung, die ihr erlaubt,
ins fertige Teil zu schneiden (kollision.INS_TEIL_ERLAUBT); der Abtrag lässt ihr die Fase
durchgehen (restmaterial). Kein Qt hier; die Anzeige ist die von „Rundum schruppen“
(gui_vierachs_operation).

Läuft ohne Oberfläche.
"""

import re

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import vierachs_bahn as vb
from . import vierachs_entgratbahn as ve
from . import vierachs_huelle as vh
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from . import werkzeuge as wz
from .sprache import tr

BREITE = ve.BREITE  # mm – die Fasenbreite, wenn nichts anderes gesagt ist
# Die Arten aus der Werkzeugverwaltung, mit denen der Assistent entgratet: der Fasenfräser,
# oder eine Kugel, die die Kante rund bricht.
ARTEN = (wz.FASENFRAESER, wz.KUGELFRAESER, wz.LOLLIPOPFRAESER)


class RundumEntgraten(PathOp.ObjectOp):
    """Proxy der Operation „Rundum entgraten“."""

    def opFeatures(self, obj):
        return PathOp.FeatureTool | PathOp.FeatureCoolant

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Rundachse = "C"
        obj.Stangenachse = FreeCAD.Vector(0, 0, 1)
        obj.Werkzeugrichtung = FreeCAD.Vector(1, 0, 0)
        obj.Drehsinn = 1
        obj.QuerAufNull = True
        obj.Breite = BREITE
        obj.Sicherheitsabstand = vb.SICHERHEIT
        obj.Ueberlauf = vb.ueberlauf_vorschlag(0.0)  # lege_an setzt ihn mit dem Fräser
        obj.AbstandFutter = vb.ABSTAND_FUTTER
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        return vo.eigenschaften_anlegen(
            obj,
            vo.achs_eigenschaften()
            + (("App::PropertyLength", "Breite", tr("ve.eigenschaft.breite")),)
            + vo.abstand_eigenschaften()
            + vo.flaechen_eigenschaften()
            + (
                ("App::PropertyInteger", "Kanten", tr("ve.eigenschaft.kanten")),
                ("App::PropertyInteger", "Ausgelassen", tr("ve.eigenschaft.ausgelassen")),
            ),
        )

    @staticmethod
    def _editormodi(obj):
        for name in ("Kanten", "Ausgelassen"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis
        if "Workplane" in obj.PropertiesList:  # Wochen-Build: die Bahn dreht selbst
            obj.setEditorMode("Workplane", 2)

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            bahn = rechne(obj, self.job, self.model)
        except ValueError as fehler:
            obj.Kanten = obj.Ausgelassen = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Kanten, obj.Ausgelassen = bahn.kanten, bahn.ausgelassen
        if bahn.ausgelassen:
            hinweis = tr("ve.ausgelassen", anzahl=bahn.ausgelassen)
            FreeCAD.Console.PrintWarning(f"{obj.Label}: {hinweis}\n")
        if bahn.hinten_frei > 0:
            from .reichweite import weg_text

            hinweis = tr("vb.hinten_frei", laenge=weg_text(bahn.hinten_frei))
            FreeCAD.Console.PrintWarning(f"{obj.Label}: {hinweis}\n")
        self.commandlist.extend(
            vb.befehle(
                bahn,
                obj.Stangenachse,
                obj.Werkzeugrichtung,
                obj.Rundachse,
                obj.Drehsinn,
                self.horizFeed * 60.0,  # CAM führt mm/s
                obj.QuerAufNull,
                vo.eintauchvorschub(self),
            )
        )


def rechne(obj, job, modell):
    """Die Bahn (vierachs_entgratbahn.Entgratbahn) für die Operation `obj` im Job. ValueError
    mit einem Satz, wenn es nicht geht."""
    form = vs.form_des_controllers(obj.ToolController)
    if form is None:
        raise ValueError(tr("ve.fehler.form"))
    return bahn_fuer(
        job,
        modell,
        obj.Stangenachse,
        obj.Werkzeugrichtung,
        form,
        float(obj.Breite),
        vo.abstaende(obj),
        vo.halter_zum_futter(obj),
        vo.flaechen(obj),
    )


def bahn_fuer(
    job,
    modell,
    laengs,
    radial,
    form,
    breite,
    abstaende,
    halter=0.0,
    flaechen=(),
    toleranz=ve.TOLERANZ,
    schritt=ve.SCHRITT,
):
    """Die Bahn „Rundum entgraten“ für Modell und Stange des Jobs. `abstaende`: (Überlauf,
    Abstand zum Futter, Sicherheitsabstand); `halter`: so weit reicht der Halter seitlich über
    die Werkzeugachse (halter.seitlich); `flaechen`: die gewählten Flächen („Face3“ …; leer:
    alle) – entgratet werden ihre Außenkanten; `toleranz`: so fein wird das Teil vernetzt;
    `schritt`: so dicht liegen die Punkte auf einer Kante. ValueError mit einem Satz, wenn es
    nicht geht."""
    laengs, radius, a_vorne, a_futter = vs._stange(job, laengs)
    form_teil = vs._teil(modell)
    kanten = ve.kanten(form_teil, laengs, radial, flaechen, schritt)
    if not kanten:
        raise ValueError(tr("ve.fehler.keine_kanten"))
    ueberlauf, abstand_futter, sicherheit = abstaende
    werte = ve.Entgratwerte(
        form=form,
        stange_radius=radius,
        breite=breite,
        a_stange_vorne=a_vorne,
        a_futter=a_futter,
        sicherheit=sicherheit,
        ueberlauf=ueberlauf,
        abstand_futter=abstand_futter,
        halter=halter,
    )
    netz = vh.vernetze(form_teil, toleranz)
    return ve.entgraten(netz, laengs, radial, werte, kanten)


def vorschau(job, modell, laengs, radial, form, breite, abstaende, halter=0.0, flaechen=()):
    """Die Bahn grob – für Kanten, Zeit und ob es geht, im Assistenten, bevor es die Operation
    gibt: gröber vernetzt, weniger Punkte je Kante. ValueError wie bahn_fuer()."""
    return bahn_fuer(
        job,
        modell,
        laengs,
        radial,
        form,
        breite,
        abstaende,
        halter,
        flaechen,
        ve.VORSCHAU_TOLERANZ,
        ve.VORSCHAU_SCHRITT,
    )


def kann_entgraten(werkzeug):
    """Taugt der Fräser aus der Werkzeugverwaltung zum Entgraten – ein Fasenfräser, oder ein
    Kugelfräser als Kantenbruch?"""
    return werkzeug.art in ARTEN and werkzeug.durchmesser > 0


def lege_an(
    job,
    tc,
    achse,
    breite=BREITE,
    quer_auf_null=True,
    name=None,
    abstaende=None,
    halter=0.0,
    flaechen=(),
):
    """Legt „Rundum entgraten“ im Job an – ohne eigene Transaktion, die hält der Aufrufer (der
    Assistent). `achse`: vierachs_achsen.Stangenachse; `abstaende`: (Überlauf, Abstand zum
    Futter, Sicherheitsabstand) – ohne: die Vorschläge; `halter`: so weit reicht der Halter
    seitlich über die Werkzeugachse (halter.seitlich); `flaechen`: die gewählten Flächen
    („Face3“ …). Gibt die Operation zurück. Angelegt wie „Rundum schruppen“
    (vierachs_operation.lege_an), mit DoNotSetDefaultValues."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "RundumEntgraten")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = RundumEntgraten(obj, "RundumEntgraten", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    obj.StartDepth = 1.0
    vo.setze_achse(obj, achse, quer_auf_null)
    obj.Breite = breite
    radius = float(tc.Tool.Diameter) / 2
    obj.Ueberlauf, obj.AbstandFutter, obj.Sicherheitsabstand = (
        abstaende or vo.vorgeschlagene_abstaende(radius)
    )
    obj.HalterZumFutter = halter
    obj.Flaechen = list(flaechen)
    obj.Label = name or tr("ve.name", werkzeug=f"T{tc.ToolNumber}")
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def aendere(obj, tc, breite, abstaende=None, halter=None, flaechen=None):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und eine neue Fasenbreite – ohne
    eigene Transaktion; `abstaende`, `halter` und `flaechen` wie bei lege_an, ohne bleiben
    sie. Der Name folgt dem Werkzeug, solange es der vorgeschlagene ist."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = tr("ve.name", werkzeug=f"T{tc.ToolNumber}")
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Breite = breite
    if abstaende is not None:
        obj.Ueberlauf, obj.AbstandFutter, obj.Sicherheitsabstand = abstaende
    if halter is not None:
        obj.HalterZumFutter = halter
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Rundum entgraten T3“)?"""
    vorne, _mitte, hinten = tr("ve.name", werkzeug="\0").partition("\0")
    return re.fullmatch(re.escape(vorne) + r"T\d+" + re.escape(hinten), name) is not None


def ist_entgraten(op):
    """Ist `op` eine Operation dieses Moduls – „Rundum entgraten“?"""
    return isinstance(getattr(op, "Proxy", None), RundumEntgraten)
