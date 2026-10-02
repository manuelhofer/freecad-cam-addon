# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Plan indexiert“ (Spezifikation W-003, Stufe V4c; W-006 S2).

Wie „Rundum schruppen“ (vierachs_operation) eine Operation mit Werkzeug-Controller und
Kühlmittel, ohne Höhen und Tiefen in Z. Beim Neuberechnen rechnet sie ihre Bahn aus Modell und
Stange des Jobs (vierachs_planbahn.planen): Je gewählter ebener Fläche längs der Stange steht
die Rundachse so, dass die Fläche zum Werkzeug schaut, und der Fräser mit ebener Stirn –
gelesen aus dem ToolBit des Controllers – fährt Zeilen längs der Achse, quer versetzt mit der
Achse quer zur Stange (bei C das Y), in Lagen bis auf die Fläche plus Aufmaß. Was die „Rundum
schruppen“ des Jobs stehen ließen, rechnet sie mit: Die Lagen beginnen dort, wo noch Material
steht.

Mit einem Bohrer am Controller (P-2026-10-02-08) bohrt sie die gewählten Querbohrungen radial
(vierachs_planbahn.gebohrt_punkte) und heißt „Radial bohren T2“; ebene Flächen fräst nur ein
Fräser.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Planen“, sonst „Schruppen“ oder „Schlichten“. Kein Qt hier; die Anzeige ist die von „Rundum
schruppen“ (gui_vierachs_operation).

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import namen
from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_planbahn as vp
from . import vierachs_schlichten as vs
from .sprache import tr

AUFMASS = 0.0  # mm – Plan indexiert macht die Fläche fertig
ZEILENABSTAND_ANTEIL = 0.6  # ohne ae im Einsatz: so viel vom ebenen Teil der Stirn (Durchmesser)


class PlanIndexiert(PathOp.ObjectOp):
    """Proxy der Operation „Plan indexiert“."""

    def opFeatures(self, obj):
        return PathOp.FeatureTool | PathOp.FeatureCoolant

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Rundachse = "C"
        obj.Stangenachse = FreeCAD.Vector(0, 0, 1)
        obj.Werkzeugrichtung = FreeCAD.Vector(1, 0, 0)
        obj.Drehsinn = 1
        obj.QuerAufNull = True
        obj.Zustellung = vo.ZUSTELLUNG
        obj.Zeilenabstand = 4.0
        obj.Aufmass = AUFMASS
        obj.Sicherheitsabstand = vb.SICHERHEIT
        obj.Ueberlauf = vb.ueberlauf_vorschlag(0.0)  # lege_an setzt ihn mit dem Fräser
        obj.AbstandFutter = vb.ABSTAND_FUTTER
        obj.Eintauchwinkel = vb.EINTAUCHWINKEL
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
            + (
                ("App::PropertyLength", "Zustellung", tr("vp.eigenschaft.zustellung")),
                ("App::PropertyLength", "Zeilenabstand", tr("vp.eigenschaft.zeilenabstand")),
                ("App::PropertyLength", "Aufmass", tr("vp.eigenschaft.aufmass")),
            )
            + vo.abstand_eigenschaften()
            + vo.flaechen_eigenschaften()
            + (
                ("App::PropertyAngle", "Eintauchwinkel", tr("vo.eigenschaft.eintauchwinkel")),
                ("App::PropertyBool", "NurGleichlauf", tr("pf.eigenschaft.nur_gleichlauf")),
                ("App::PropertyInteger", "Ebenen", tr("vp.eigenschaft.ebenen")),
                ("App::PropertyInteger", "Lagen", tr("vp.eigenschaft.lagen")),
                ("App::PropertyInteger", "Zeilen", tr("vp.eigenschaft.zeilen")),
                ("App::PropertyInteger", "Huebe", tr("vp.eigenschaft.huebe")),
            ),
        )

    @staticmethod
    def _editormodi(obj):
        for name in ("Ebenen", "Lagen", "Zeilen", "Huebe"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis
        if "Workplane" in obj.PropertiesList:  # Wochen-Build: die Bahn dreht selbst
            obj.setEditorMode("Workplane", 2)

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            bahn = rechne(obj, self.job, self.model)
        except ValueError as fehler:
            obj.Ebenen = obj.Lagen = obj.Zeilen = obj.Huebe = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Ebenen, obj.Lagen, obj.Zeilen = bahn.flaechen, bahn.lagen, bahn.zeilen
        obj.Huebe = bahn.huebe
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
    """Die Bahn (vierachs_planbahn.Planbahn) für die Operation `obj` im Job – nach den „Rundum
    schruppen“ des Jobs. ValueError mit einem Satz, wenn es nicht geht."""
    bohrer = bohrer_des_controllers(obj.ToolController)
    form = form_des_bohrers(bohrer) if bohrer else vs.form_des_controllers(obj.ToolController)
    if form is None:
        raise ValueError(tr("vp.fehler.form"))
    return bahn_fuer(
        job,
        modell,
        obj.Stangenachse,
        obj.Werkzeugrichtung,
        form,
        float(obj.Zustellung),
        float(obj.Zeilenabstand),
        float(obj.Aufmass),
        vo.abstaende(obj),
        vs.schruppbahnen(job, modell),
        vo.halter_zum_futter(obj),
        vo.flaechen(obj),
        float(obj.Eintauchwinkel),
        bohrer=bohrer,
        gleichlauf=sp.fuer_m3(True, obj.ToolController),
        nur_gleichlauf=bool(getattr(obj, "NurGleichlauf", False)),
    )


def bohrer_von(werkzeug):
    """(Durchmesser, Spitzenwinkel) eines Bohrers aus der Werkzeugverwaltung – None bei jedem
    anderen Werkzeug: Mit ihm bohrt „Plan indexiert“ die Querbohrungen radial."""
    from . import bohren as bh
    from . import werkzeuge as wz

    if werkzeug is None or werkzeug.art != wz.BOHRER or werkzeug.durchmesser <= 0:
        return None
    winkel = wz.wert(werkzeug, "spitzenwinkel") or bh.SPITZENWINKEL
    return float(werkzeug.durchmesser), float(winkel)


def bohrer_des_controllers(tc):
    """bohrer_von() für das Werkzeug eines Werkzeug-Controllers (aus seinem ToolBit)."""
    from .werkzeuge_aus_cam import vom_controller

    try:
        return bohrer_von(vom_controller(tc))
    except AttributeError:  # kein ToolBit, wie CAM es anlegt
        return None


def form_des_bohrers(bohrer):
    """Die Form des Bohrers (fraeserform): ein Kegel mit seinem Spitzenwinkel bis zum Ø."""
    from . import bohren as bh
    from . import fraeserform as ff

    durchmesser, winkel = bohrer
    return ff.kegel(0.0, durchmesser / 2, bh.spitze(durchmesser, winkel))


def bahn_fuer(
    job,
    modell,
    laengs,
    radial,
    form,
    zustellung,
    zeilenabstand,
    aufmass,
    abstaende,
    schruppen=(),
    halter=0.0,
    flaechen=(),
    eintauchwinkel=vb.EINTAUCHWINKEL,
    toleranz=vp.TOLERANZ,
    bohrer=None,
    gleichlauf=True,
    nur_gleichlauf=False,
):
    """Die Bahn „Plan indexiert“ für Modell und Stange des Jobs. `abstaende`: (Überlauf,
    Abstand zum Futter, Sicherheitsabstand); `schruppen`: [(Bahn, Fräserradius, Aufmaß)] der
    Schruppbahnen davor (vierachs_schlichten.schruppbahnen()) – die Lagen beginnen auf dem Rest;
    `halter`: so weit reicht der Halter seitlich über die Werkzeugachse (halter.seitlich);
    `flaechen`: die gewählten Flächen („Face3“ …) – gefräst werden die ebenen längs der Stange
    darunter; `toleranz`: so fein wird das Teil vernetzt; `bohrer`: (Durchmesser,
    Spitzenwinkel) – die Querbohrungen radial bohren (bohrer_von()), ebene Flächen nicht;
    `gleichlauf`: im Gleichlauf für M3 (spindel.fuer_m3 mit dem Controller); `nur_gleichlauf`:
    die Zeilen jede im Gleichlauf, dazwischen abheben (sonst hin und her). ValueError mit einem
    Satz, wenn es nicht geht."""
    laengs, radius, a_vorne, a_futter = vs._stange(job, laengs)
    form_teil = vs._teil(modell)
    ebenen = [] if bohrer else vp.ebenen(form_teil, laengs, radial, flaechen)
    bohrungen = vp.bohrungen(form_teil, laengs, radial, flaechen)
    mantelnuten = [] if bohrer else vp.mantelnuten(form_teil, laengs, radial, flaechen)
    if bohrer and not bohrungen:
        raise ValueError(tr("vp.fehler.keine_bohrung"))
    if not ebenen and not bohrungen and not mantelnuten:
        raise ValueError(tr("vp.fehler.keine_ebene"))
    ueberlauf, abstand_futter, sicherheit = abstaende
    werte = vp.Planwerte(
        form=form,
        stange_radius=radius,
        zustellung=zustellung,
        zeilenabstand=zeilenabstand,
        aufmass=aufmass,
        a_stange_vorne=a_vorne,
        a_futter=a_futter,
        sicherheit=sicherheit,
        ueberlauf=ueberlauf,
        abstand_futter=abstand_futter,
        halter=halter,
        eintauchwinkel=eintauchwinkel,
        rest=vs.rest_nach(schruppen, radius, a_futter, a_vorne) if schruppen else None,
        bohrer=bohrer,
        gleichlauf=gleichlauf,
        nur_gleichlauf=nur_gleichlauf,
    )
    netz = vp.netz_ohne(form_teil, [e.name for e in ebenen], toleranz)
    return vp.planen(
        netz,
        laengs,
        radial,
        werte,
        ebenen,
        nuten_=vp.nuten(form_teil, laengs, radial, ebenen),
        bohrungen_=bohrungen,
        mantelnuten_=mantelnuten,
    )


def vorschau(
    job,
    modell,
    laengs,
    radial,
    form,
    zustellung,
    zeilenabstand,
    aufmass,
    abstaende,
    halter=0.0,
    flaechen=(),
    eintauchwinkel=vb.EINTAUCHWINKEL,
    bohrer=None,
    nur_gleichlauf=False,
):
    """Die Bahn grob – für Lagen, Zeilen, Zeit und ob es geht, im Assistenten, bevor es die
    Operationen gibt: ohne den Rest nach dem Schruppen, gröber vernetzt. ValueError wie
    bahn_fuer()."""
    return bahn_fuer(
        job,
        modell,
        laengs,
        radial,
        form,
        zustellung,
        zeilenabstand,
        aufmass,
        abstaende,
        (),
        halter,
        flaechen,
        eintauchwinkel,
        vp.VORSCHAU_TOLERANZ,
        bohrer,
        nur_gleichlauf=nur_gleichlauf,
    )


def zeilenabstand_vorschlag(werkzeug, einsatz, form=None):
    """Der Zeilenabstand, wenn nichts anderes gesagt ist: ae des Einsatzes aus der
    Werkzeugtabelle, sonst ZEILENABSTAND_ANTEIL vom ebenen Teil der Stirn (`form`,
    fraeserform.Form) bzw. vom Durchmesser – nie mehr als die ebene Stirn breit ist."""
    breit = 2 * vp.ebener_radius(form) if form is not None else werkzeug.durchmesser
    if breit <= 0:
        breit = werkzeug.durchmesser
    if einsatz is not None and 0 < einsatz.ae <= breit:
        return einsatz.ae
    return ZEILENABSTAND_ANTEIL * breit


def lege_an(
    job,
    tc,
    achse,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    quer_auf_null=True,
    name=None,
    abstaende=None,
    halter=0.0,
    flaechen=(),
    eintauchwinkel=None,
    nur_gleichlauf=False,
):
    """Legt „Plan indexiert“ im Job an – ohne eigene Transaktion, die hält der Aufrufer (der
    Assistent). `achse`: vierachs_achsen.Stangenachse; `abstaende`: (Überlauf, Abstand zum
    Futter, Sicherheitsabstand) – ohne: die Vorschläge; `halter`: so weit reicht der Halter
    seitlich über die Werkzeugachse (halter.seitlich); `flaechen`: die gewählten Flächen
    („Face3“ …); `eintauchwinkel`: Grad, ohne der Vorschlag. Gibt die Operation zurück.
    Angelegt wie „Rundum schruppen“ (vierachs_operation.lege_an), mit DoNotSetDefaultValues."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "PlanIndexiert")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = PlanIndexiert(obj, "PlanIndexiert", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    obj.StartDepth = 1.0
    vo.setze_achse(obj, achse, quer_auf_null)
    obj.Zustellung = zustellung
    obj.Zeilenabstand = zeilenabstand
    obj.Aufmass = aufmass
    radius = float(tc.Tool.Diameter) / 2
    obj.Ueberlauf, obj.AbstandFutter, obj.Sicherheitsabstand = (
        abstaende or vo.vorgeschlagene_abstaende(radius)
    )
    obj.HalterZumFutter = halter
    obj.Flaechen = list(flaechen)
    if eintauchwinkel:
        obj.Eintauchwinkel = eintauchwinkel
    obj.NurGleichlauf = bool(nur_gleichlauf)
    obj.Label = namen.eindeutig(obj.Document, name or _name(tc), obj)
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def aendere(
    obj,
    tc,
    zustellung,
    zeilenabstand,
    aufmass,
    abstaende=None,
    halter=None,
    flaechen=None,
    eintauchwinkel=None,
    nur_gleichlauf=None,
):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `abstaende`, `halter`, `flaechen`, `eintauchwinkel` und `nur_gleichlauf` wie
    bei lege_an, ohne bleiben sie. Der Name folgt dem Werkzeug, solange es der vorgeschlagene ist.
    """
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, _name(tc), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Zustellung = zustellung
    obj.Zeilenabstand = zeilenabstand
    obj.Aufmass = aufmass
    if abstaende is not None:
        obj.Ueberlauf, obj.AbstandFutter, obj.Sicherheitsabstand = abstaende
    if halter is not None:
        obj.HalterZumFutter = halter
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    if eintauchwinkel:
        obj.Eintauchwinkel = eintauchwinkel
    if nur_gleichlauf is not None:
        obj.NurGleichlauf = bool(nur_gleichlauf)


def _name(tc):
    """Der vorgeschlagene Name: „Plan indexiert T1“ – mit einem Bohrer „Radial bohren T2“."""
    if bohrer_des_controllers(tc):
        return tr("vp.name_bohren", werkzeug=f"T{tc.ToolNumber}")
    return tr("vp.name", werkzeug=f"T{tc.ToolNumber}")


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Plan indexiert T1“, „Radial bohren T2“) –
    auch mit „ (2)“ dahinter?"""
    return namen.nach_vorlage(name, tr("vp.name", werkzeug="\0")) or namen.nach_vorlage(
        name, tr("vp.name_bohren", werkzeug="\0")
    )


def ist_plan(op):
    """Ist `op` eine Operation dieses Moduls – „Plan indexiert“?"""
    return isinstance(getattr(op, "Proxy", None), PlanIndexiert)
