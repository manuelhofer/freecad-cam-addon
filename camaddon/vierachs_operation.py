# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Rundum schruppen“ (Spezifikation W-003, Abschnitt 10, Stufe V3c).

Eine Operation wie die von FreeCAD: ein Path::FeaturePython, dessen Proxy
Path.Op.Base.ObjectOp erbt – mit Werkzeug-Controller und Kühlmittel, ohne
Höhen und Tiefen in Z (sonst hinge die Basis ein „G0 Z Sicherheitshöhe“ an, und
das hieße bei C: längs zum Futter). Beim Neuberechnen rechnet sie ihre Bahn aus
dem Modell und der Stange des Jobs (vierachs_huelle, vierachs_bahn); ihre Werte
stehen als Eigenschaften in der Gruppe „4-Achs“. Die Spannlänge kommt vom Job
(vierachs_rohteil.spannlaenge), sonst gilt der Vorschlag. Überlauf und Abstand zum
Futter (V3f) kamen mit 0.27 dazu; ältere Operationen bekommen sie beim Laden so, dass
ihre Bahn bleibt, wie sie war. Die gewählten Flächen (V4, „Flaechen“) kamen mit 0.30: leer
heißt rundum – wie bisher.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Kein
Qt hier; die Anzeige liegt in gui_vierachs_operation.py.

Läuft ohne Oberfläche.
"""

import math

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import aufloesung as au
from . import fraeserform as ff
from . import freiwege as fw
from . import namen
from . import spindel as sp
from . import vierachs_achsen as va
from . import vierachs_bahn as vb
from . import vierachs_flaechen as vf
from . import vierachs_huelle as vh
from . import vierachs_rohteil as vr
from .sprache import tr

GRUPPE = "4-Achs"
ZUSTELLUNG = 2.0  # mm – Vorschläge, solange nichts anderes gesagt ist
STEIGUNG_ANTEIL = 0.4  # Vorschub je Umdrehung als Anteil von D
AUFMASS = 0.3  # mm
GERADE = 1e-6
WAND_RAND = 1e-3  # mm – eine Planfläche so nah an einem Ende des Teils ist seine Stirn


class RundumSchruppen(PathOp.ObjectOp):
    """Proxy der Operation „Rundum schruppen“."""

    def opFeatures(self, obj):
        return PathOp.FeatureTool | PathOp.FeatureCoolant

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Rundachse = "C"
        obj.Stangenachse = FreeCAD.Vector(0, 0, 1)
        obj.Werkzeugrichtung = FreeCAD.Vector(1, 0, 0)
        obj.Drehsinn = 1
        obj.QuerAufNull = True
        obj.Zustellung = ZUSTELLUNG
        obj.VorschubJeUmdrehung = 4.0
        obj.Aufmass = AUFMASS
        obj.Sicherheitsabstand = vb.SICHERHEIT
        obj.Ueberlauf = vb.ueberlauf_vorschlag(0.0)  # lege_an setzt ihn mit dem Fräser
        obj.AbstandFutter = vb.ABSTAND_FUTTER
        obj.Eintauchwinkel = vb.EINTAUCHWINKEL
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        neu = self._eigenschaften(obj)
        if "Ueberlauf" in neu:  # bis 0.26: kein Überlauf – das Futter begrenzte die Bahn
            obj.Ueberlauf = vb.ueberlauf_vorschlag(float(obj.OpToolDiameter) / 2)
        if "AbstandFutter" in neu:  # bis 0.26 fest 2 mm
            obj.AbstandFutter = 2.0
        if "Eintauchwinkel" in neu:  # bis 0.29: rundum, ohne Rampe
            obj.Eintauchwinkel = vb.EINTAUCHWINKEL
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        au.eigenschaft(obj, GRUPPE)  # die Auflösung längs (mm) und rundum (Grad), T-009
        au.eigenschaft_rundum(obj, GRUPPE)
        return eigenschaften_anlegen(
            obj,
            achs_eigenschaften()
            + (
                ("App::PropertyLength", "Zustellung", tr("vo.eigenschaft.zustellung")),
                ("App::PropertyLength", "VorschubJeUmdrehung", tr("vo.eigenschaft.steigung")),
                ("App::PropertyLength", "Aufmass", tr("vo.eigenschaft.aufmass")),
            )
            + abstand_eigenschaften()
            + flaechen_eigenschaften()
            + (
                ("App::PropertyAngle", "Eintauchwinkel", tr("vo.eigenschaft.eintauchwinkel")),
                ("App::PropertyBool", "NurGleichlauf", tr("pf.eigenschaft.nur_gleichlauf")),
                ("App::PropertyBool", "Querachse", tr("vo.eigenschaft.querachse")),
                ("App::PropertyInteger", "Lagen", tr("vo.eigenschaft.lagen")),
            ),
        )

    @staticmethod
    def _editormodi(obj):
        obj.setEditorMode("Lagen", 1)  # nur lesen: das Ergebnis
        if "Workplane" in obj.PropertiesList:  # Wochen-Build: die Bahn dreht selbst
            obj.setEditorMode("Workplane", 2)

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            bahn = rechne(obj, self.job, self.model, self.radius)
        except ValueError as fehler:
            obj.Lagen = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({_ascii(str(fehler))})"))
            return
        obj.Lagen = bahn.lagen
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
                eintauchvorschub(self),
                fw.freivorschub_fuer(self.job),  # im Freien schnell (vierachs_bahn._frei)
                fraeser_radius=float(obj.OpToolDiameter) / 2,
            )
        )


def eintauchvorschub(proxy):
    """Der Vorschub senkrecht ins Material (mm/min) vom Werkzeug-Controller – None ohne ihn."""
    senkrecht = getattr(proxy, "vertFeed", 0) or 0
    return senkrecht * 60.0 if senkrecht > 0 else None  # CAM führt mm/s


def flaechen_eigenschaften():
    """Die gewählten Flächen (V4) – „Rundum schruppen“ und „Rundum schlichten“ haben sie
    beide, wie achs_eigenschaften(). Leer: rundum; ältere Operationen bekommen sie leer."""
    return (("App::PropertyStringList", "Flaechen", tr("vo.eigenschaft.flaechen")),)


def flaechen(obj):
    """Die gewählten Flächen der Operation („Face3“ …) – leer: rundum."""
    return tuple(getattr(obj, "Flaechen", ()) or ())


def achs_eigenschaften():
    """Die Eigenschaften der Rundachse – „Rundum schruppen“ und „Rundum schlichten“
    (vierachs_schlichten) haben sie beide: (Typ, Name, Text)."""
    return (
        ("App::PropertyString", "Rundachse", tr("vo.eigenschaft.rundachse")),
        ("App::PropertyVector", "Stangenachse", tr("vo.eigenschaft.stangenachse")),
        ("App::PropertyVector", "Werkzeugrichtung", tr("vo.eigenschaft.werkzeugrichtung")),
        ("App::PropertyInteger", "Drehsinn", tr("vo.eigenschaft.drehsinn")),
        ("App::PropertyBool", "QuerAufNull", tr("vo.eigenschaft.quer_auf_null")),
    )


def abstand_eigenschaften():
    """Überlauf, Abstand zum Futter, Sicherheitsabstand und wie weit der Halter zum Futter
    hin reicht – wie achs_eigenschaften(). Den Halter gibt es seit 0.29: Ältere Operationen
    bekommen 0, ihre Bahn bleibt."""
    return (
        ("App::PropertyLength", "Ueberlauf", tr("vo.eigenschaft.ueberlauf")),
        ("App::PropertyLength", "AbstandFutter", tr("vo.eigenschaft.abstand_futter")),
        ("App::PropertyLength", "Sicherheitsabstand", tr("vo.eigenschaft.sicherheit")),
        ("App::PropertyLength", "HalterZumFutter", tr("vo.eigenschaft.halter_zum_futter")),
    )


def eigenschaften_anlegen(obj, liste):
    """Legt die Eigenschaften aus `liste` ((Typ, Name, Text)) in der Gruppe „4-Achs“ an, die
    fehlen; gibt ihre Namen zurück."""
    neu = []
    for typ, name, text in liste:
        if name not in obj.PropertiesList:
            obj.addProperty(typ, name, GRUPPE, text)
            neu.append(name)
    return neu


def form_des_controllers(tc):
    """Die Form des Fräsers eines Werkzeug-Controllers (fraeserform.Form), oder None."""
    from .werkzeuge_aus_cam import vom_controller

    werkzeug = vom_controller(tc)
    return ff.von_werkzeug(werkzeug) if werkzeug is not None else None


def rechne(obj, job, modell, fraeser_radius):
    """Die Bahn (vierachs_bahn.Bahn) für die Operation `obj` im Job – ValueError mit einem
    Satz, wenn es nicht geht."""
    return bahn_fuer(
        job,
        modell,
        obj.Stangenachse,
        obj.Werkzeugrichtung,
        fraeser_radius,
        float(obj.Zustellung),
        float(obj.VorschubJeUmdrehung),
        float(obj.Aufmass),
        float(obj.Sicherheitsabstand),
        float(obj.Ueberlauf),
        float(obj.AbstandFutter),
        halter_zum_futter(obj),
        flaechen(obj),
        float(obj.Eintauchwinkel),
        gleichlauf=sp.fuer_m3(True, obj.ToolController),
        nur_gleichlauf=bool(getattr(obj, "NurGleichlauf", False)),
        form=form_des_controllers(obj.ToolController),
        querachse=bool(getattr(obj, "Querachse", False)),
        schritt_a=au.wert(obj, vh.SCHRITT_A),
        schritt_phi=au.wert_rundum(obj, vh.SCHRITT_PHI),
    )


def bahn_fuer(
    job,
    modell,
    laengs,
    radial,
    fraeser_radius,
    zustellung,
    steigung,
    aufmass,
    sicherheit=None,
    ueberlauf=None,
    abstand_futter=None,
    halter=0.0,
    flaechen_=(),
    eintauchwinkel=vb.EINTAUCHWINKEL,
    gleichlauf=True,
    nur_gleichlauf=False,
    form=None,
    r_tiefste=-math.inf,
    querachse=False,
    schritt_a=vh.SCHRITT_A,
    schritt_phi=vh.SCHRITT_PHI,
):
    """Die Schruppbahn für Modell und Stange des Jobs – auch für die Vorschau im Assistenten,
    bevor es die Operation gibt. Ohne Angabe gelten Sicherheitsabstand, Überlauf und Abstand
    zum Futter wie vorgeschlagen; `halter`: so weit reicht der Halter seitlich über die
    Werkzeugachse (halter.seitlich); `flaechen_`: die gewählten Flächen („Face3“ …), leer:
    rundum; `eintauchwinkel` (Grad) für die Rampe ins Material zwischen ihnen; `gleichlauf`:
    die Spirale im Gleichlauf für M3 (spindel.fuer_m3 mit dem Controller); `querachse`: die
    Spirale mit der Querachse (vierachs_bahn.Schruppwerte.querachse). ValueError mit einem Satz,
    wenn es nicht geht."""
    laengs = FreeCAD.Vector(laengs)
    if laengs.Length < GERADE:
        raise ValueError(tr("vo.fehler.achse"))
    laengs.normalize()
    radius, a_hinten, a_vorne = stange(job, laengs)
    formen = [o.Shape for o in modell if not o.Shape.isNull()]
    if not formen:
        raise ValueError(tr("vo.fehler.modell"))
    teil = formen[0] if len(formen) == 1 else _verbunden(formen)
    werte = vb.Schruppwerte(
        fraeser_radius=fraeser_radius,
        stange_radius=radius,
        zustellung=zustellung,
        steigung=steigung,
        aufmass=aufmass,
        a_stange_vorne=a_vorne,
        a_futter=a_hinten + (vr.spannlaenge(job) or vr.SPANNLAENGE),
        sicherheit=vb.SICHERHEIT if sicherheit is None else sicherheit,
        ueberlauf=ueberlauf,
        abstand_futter=vb.ABSTAND_FUTTER if abstand_futter is None else abstand_futter,
        halter=halter,
        waende=waende(teil, laengs),
        bereich=vf.bereich_fuer(teil, laengs, radial, flaechen_, fraeser_radius),
        eintauchwinkel=eintauchwinkel,
        gleichlauf=gleichlauf,
        nur_gleichlauf=nur_gleichlauf,
        form=form,
        r_tiefste=r_tiefste,
        querachse=querachse,
    )
    return vb.schruppen(vh.vernetze(teil), laengs, radial, werte, schritt_a, schritt_phi)


def stange(job, laengs):
    """(Radius, a hinten, a vorne) der runden Stange des Jobs, längs `laengs` – die Achse
    muss durch den Nullpunkt des Jobs gehen. ValueError, wenn es keine solche ist."""
    rohteil = getattr(job, "Stock", None)
    if rohteil is None or not hasattr(rohteil, "Radius") or not hasattr(rohteil, "Height"):
        raise ValueError(tr("vo.fehler.stange"))
    richtung = rohteil.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    basis = rohteil.Placement.Base
    neben = basis - laengs * basis.dot(laengs)
    if abs(abs(richtung.dot(laengs)) - 1) > GERADE or neben.Length > 1e-3:
        raise ValueError(tr("vo.fehler.stange_achse"))
    enden = (basis.dot(laengs), (basis + richtung * float(rohteil.Height)).dot(laengs))
    return float(rohteil.Radius), min(enden), max(enden)


def waende(form, laengs):
    """[(a, Seite)] der Wände des Teils: ebene Flächen quer zur Stangenachse zwischen seinem
    hinteren und vorderen Ende (ein Absatz, die Flanke einer Nut) – Seite +1, wenn die Wand
    nach vorn schaut, −1, wenn zum Futter hin. Vor jeder hält die Spirale eine Umdrehung an
    (Ringgang, D-42)."""
    laengs = FreeCAD.Vector(laengs)
    enden = [v.Point.dot(laengs) for v in form.Vertexes]
    if not enden:
        return ()
    hinten, vorne = min(enden), max(enden)
    gefunden = set()
    for flaeche in form.Faces:
        if not vr.ist_eben(flaeche):
            continue
        quer = vr.aussennormale(flaeche).dot(laengs)
        if abs(abs(quer) - 1) > GERADE:
            continue
        a = flaeche.CenterOfMass.dot(laengs)
        if hinten + WAND_RAND < a < vorne - WAND_RAND:
            gefunden.add((round(a, 6), 1 if quer > 0 else -1))
    return tuple(sorted(gefunden))


def _verbunden(formen):
    import Part

    return Part.makeCompound(formen)


def lege_an(
    job,
    tc,
    achse,
    zustellung,
    steigung,
    aufmass,
    quer_auf_null=True,
    name=None,
    abstaende=None,
    halter=0.0,
    flaechen_=(),
    eintauchwinkel=None,
    nur_gleichlauf=False,
    querachse=False,
):
    """Legt „Rundum schruppen“ im Job an – ohne eigene Transaktion, die hält der Aufrufer
    (der Assistent). `achse`: vierachs_achsen.Stangenachse. `abstaende`: (Überlauf, Abstand
    zum Futter, Sicherheitsabstand) – ohne: die Vorschläge. `halter`: so weit reicht der
    Halter des Werkzeugs seitlich über dessen Achse (halter.seitlich). `flaechen_`: die
    gewählten Flächen („Face3“ …), leer: rundum; `eintauchwinkel`: Grad, ohne der Vorschlag.
    Gibt die Operation zurück.

    Angelegt wie FreeCADs eigene Operationen, aber mit DoNotSetDefaultValues:
    Sonst fragte FreeCAD nach Job und Controller, sobald es mehrere gibt – in
    FreeCADCmd ein Fehler.
    """
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "RundumSchruppen")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = RundumSchruppen(obj, "RundumSchruppen", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    obj.StartDepth = 1.0
    setze_achse(obj, achse, quer_auf_null)
    obj.Zustellung = zustellung
    obj.VorschubJeUmdrehung = steigung
    obj.Aufmass = aufmass
    _setze_abstaende(obj, abstaende or vorgeschlagene_abstaende(float(tc.Tool.Diameter) / 2, job))
    obj.HalterZumFutter = halter
    obj.Flaechen = list(flaechen_)
    if eintauchwinkel:
        obj.Eintauchwinkel = eintauchwinkel
    obj.NurGleichlauf = bool(nur_gleichlauf)
    obj.Querachse = bool(querachse)
    obj.Label = namen.eindeutig(
        obj.Document, name or tr("vo.name", werkzeug=f"T{tc.ToolNumber}"), obj
    )
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def vorgeschlagene_abstaende(fraeser_radius, job=None):
    """(Überlauf, Abstand zum Futter, Sicherheitsabstand), wie vorgeschlagen (mm) – der Überlauf
    aus der Abstechbreite des Jobs."""
    abstech = vr.abstechbreite(job) if job is not None else vb.ABSTECHBREITE
    return (
        vb.ueberlauf_vorschlag(fraeser_radius, abstech),
        vb.ABSTAND_FUTTER,
        vb.SICHERHEIT,
    )


def abstaende(obj):
    """(Überlauf, Abstand zum Futter, Sicherheitsabstand) der Operation (mm)."""
    return float(obj.Ueberlauf), float(obj.AbstandFutter), float(obj.Sicherheitsabstand)


def _setze_abstaende(obj, werte):
    obj.Ueberlauf, obj.AbstandFutter, obj.Sicherheitsabstand = werte


def halter_zum_futter(obj):
    """So weit reicht der Halter der Operation seitlich über die Werkzeugachse (mm)."""
    return float(obj.HalterZumFutter)


def aendere(
    obj,
    tc,
    zustellung,
    steigung,
    aufmass,
    abstaende_=None,
    halter_=None,
    flaechen_=None,
    eintauchwinkel=None,
    nur_gleichlauf=None,
    querachse=None,
):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion, die hält der Aufrufer (der Assistent beim Ändern). `abstaende_`, `halter_`,
    `flaechen_` und `eintauchwinkel`: wie bei lege_an; ohne bleiben sie. Der Name folgt dem
    Werkzeug, solange es der vorgeschlagene ist: „Rundum schruppen T1“ wird „… T3“."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, tr("vo.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Zustellung = zustellung
    obj.VorschubJeUmdrehung = steigung
    obj.Aufmass = aufmass
    if abstaende_ is not None:
        _setze_abstaende(obj, abstaende_)
    if halter_ is not None:
        obj.HalterZumFutter = halter_
    if flaechen_ is not None and list(flaechen_) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen_)
    if eintauchwinkel:
        obj.Eintauchwinkel = eintauchwinkel
    if nur_gleichlauf is not None:
        obj.NurGleichlauf = bool(nur_gleichlauf)
    if querachse is not None and bool(querachse) != bool(getattr(obj, "Querachse", False)):
        obj.Querachse = bool(querachse)


def setze_achse(obj, achse, quer_auf_null=None):
    """Rundachse, Stangenachse, Werkzeugrichtung, Drehsinn und „quer auf 0“ der Operation aus
    `achse` (vierachs_achsen.Stangenachse) – nur, was sich ändert. `quer_auf_null`: ohne
    Angabe wie `achse.quer`."""
    werte = {
        "Rundachse": achse.buchstabe,
        "Stangenachse": FreeCAD.Vector(achse.laengs),
        "Werkzeugrichtung": va.radial(achse),
        "Drehsinn": achse.drehsinn,
        "QuerAufNull": achse.quer if quer_auf_null is None else quer_auf_null,
    }
    for name, wert in werte.items():
        if getattr(obj, name) != wert:
            setattr(obj, name, wert)


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Rundum schruppen T3“) – auch mit „ (2)“ dahinter?"""
    return namen.nach_vorlage(name, tr("vo.name", werkzeug="\0"))


def ist_rundum(op):
    """Ist `op` eine 4-Achs-Operation des Addons: „Rundum schruppen“, „Rundum schlichten“
    (vierachs_schlichten), „Plan indexiert“ (vierachs_plan) oder „Rundum entgraten“
    (vierachs_entgraten)?"""
    name = type(getattr(op, "Proxy", None)).__name__
    return ist_schruppen(op) or name in ("RundumSchlichten", "PlanIndexiert", "RundumEntgraten")


def ist_schruppen(op):
    """Ist `op` eine Operation dieses Moduls – „Rundum schruppen“?"""
    return isinstance(getattr(op, "Proxy", None), RundumSchruppen)


def _ascii(text):
    """Für Kommentare im NC-Programm: ohne Umlaute – nicht jede Steuerung nimmt sie."""
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe")):
        text = text.replace(alt, neu)
    text = text.replace("Ü", "Ue").replace("ß", "ss").replace("–", "-")
    return text.encode("ascii", "replace").decode("ascii").replace("(", "[").replace(")", "]")
