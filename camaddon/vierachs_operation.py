# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Rundum schruppen“ (Spezifikation W-003, Abschnitt 10, Stufe V3c).

Eine Operation wie die von FreeCAD: ein Path::FeaturePython, dessen Proxy
Path.Op.Base.ObjectOp erbt – mit Werkzeug-Controller und Kühlmittel, ohne
Höhen und Tiefen in Z (sonst hinge die Basis ein „G0 Z Sicherheitshöhe“ an, und
das hieße bei C: längs zum Futter). Beim Neuberechnen rechnet sie ihre Bahn aus
dem Modell und der Stange des Jobs (vierachs_huelle, vierachs_bahn); ihre Werte
stehen als Eigenschaften in der Gruppe „4-Achs“. Die Spannlänge kommt vom Job
(vierachs_rohteil.spannlaenge), sonst gilt der Vorschlag.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Kein
Qt hier; die Anzeige liegt in gui_vierachs_operation.py.

Läuft ohne Oberfläche.
"""

import re

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import vierachs_achsen as va
from . import vierachs_bahn as vb
from . import vierachs_huelle as vh
from . import vierachs_rohteil as vr
from .sprache import tr

GRUPPE = "4-Achs"
ZUSTELLUNG = 2.0  # mm – Vorschläge, solange nichts anderes gesagt ist
STEIGUNG_ANTEIL = 0.4  # Vorschub je Umdrehung als Anteil von D
AUFMASS = 0.3  # mm
GERADE = 1e-6


class RundumSchruppen(PathOp.ObjectOp):
    """Proxy der Operation „Rundum schruppen“."""

    def opFeatures(self, obj):
        return PathOp.FeatureTool | PathOp.FeatureCoolant

    def initOperation(self, obj):
        for typ, name, text in (
            ("App::PropertyString", "Rundachse", tr("vo.eigenschaft.rundachse")),
            ("App::PropertyVector", "Stangenachse", tr("vo.eigenschaft.stangenachse")),
            ("App::PropertyVector", "Werkzeugrichtung", tr("vo.eigenschaft.werkzeugrichtung")),
            ("App::PropertyInteger", "Drehsinn", tr("vo.eigenschaft.drehsinn")),
            ("App::PropertyBool", "QuerAufNull", tr("vo.eigenschaft.quer_auf_null")),
            ("App::PropertyLength", "Zustellung", tr("vo.eigenschaft.zustellung")),
            ("App::PropertyLength", "VorschubJeUmdrehung", tr("vo.eigenschaft.steigung")),
            ("App::PropertyLength", "Aufmass", tr("vo.eigenschaft.aufmass")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("vo.eigenschaft.sicherheit")),
            ("App::PropertyInteger", "Lagen", tr("vo.eigenschaft.lagen")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
        obj.Rundachse = "C"
        obj.Stangenachse = FreeCAD.Vector(0, 0, 1)
        obj.Werkzeugrichtung = FreeCAD.Vector(1, 0, 0)
        obj.Drehsinn = 1
        obj.QuerAufNull = True
        obj.Zustellung = ZUSTELLUNG
        obj.VorschubJeUmdrehung = 4.0
        obj.Aufmass = AUFMASS
        obj.Sicherheitsabstand = vb.SICHERHEIT
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._editormodi(obj)

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
            )
        )


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
    )


def bahn_fuer(
    job, modell, laengs, radial, fraeser_radius, zustellung, steigung, aufmass, sicherheit=None
):
    """Die Schruppbahn für Modell und Stange des Jobs – auch für die Vorschau im Assistenten,
    bevor es die Operation gibt. ValueError mit einem Satz, wenn es nicht geht."""
    laengs = FreeCAD.Vector(laengs)
    if laengs.Length < GERADE:
        raise ValueError(tr("vo.fehler.achse"))
    laengs.normalize()
    radius, a_hinten, a_vorne = stange(job, laengs)
    werte = vb.Schruppwerte(
        fraeser_radius=fraeser_radius,
        stange_radius=radius,
        zustellung=zustellung,
        steigung=steigung,
        aufmass=aufmass,
        a_stange_vorne=a_vorne,
        a_futter=a_hinten + (vr.spannlaenge(job) or vr.SPANNLAENGE),
        sicherheit=vb.SICHERHEIT if sicherheit is None else sicherheit,
    )
    formen = [o.Shape for o in modell if not o.Shape.isNull()]
    if not formen:
        raise ValueError(tr("vo.fehler.modell"))
    form = formen[0] if len(formen) == 1 else _verbunden(formen)
    return vb.schruppen(vh.vernetze(form), laengs, radial, werte)


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


def _verbunden(formen):
    import Part

    return Part.makeCompound(formen)


def lege_an(job, tc, achse, zustellung, steigung, aufmass, quer_auf_null=True, name=None):
    """Legt „Rundum schruppen“ im Job an – ohne eigene Transaktion, die hält der Aufrufer
    (der Assistent). `achse`: vierachs_achsen.Stangenachse. Gibt die Operation zurück.

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
    obj.Rundachse = achse.buchstabe
    obj.Stangenachse = FreeCAD.Vector(achse.laengs)
    obj.Werkzeugrichtung = va.radial(achse)
    obj.Drehsinn = achse.drehsinn
    obj.QuerAufNull = quer_auf_null
    obj.Zustellung = zustellung
    obj.VorschubJeUmdrehung = steigung
    obj.Aufmass = aufmass
    obj.Label = name or tr("vo.name", werkzeug=f"T{tc.ToolNumber}")
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def aendere(obj, tc, zustellung, steigung, aufmass):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion, die hält der Aufrufer (der Assistent beim Ändern). Der Name folgt dem
    Werkzeug, solange es der vorgeschlagene ist: „Rundum schruppen T1“ wird „… T3“."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = tr("vo.name", werkzeug=f"T{tc.ToolNumber}")
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Zustellung = zustellung
    obj.VorschubJeUmdrehung = steigung
    obj.Aufmass = aufmass


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Rundum schruppen T3“)?"""
    vorne, _mitte, hinten = tr("vo.name", werkzeug="\0").partition("\0")
    return re.fullmatch(re.escape(vorne) + r"T\d+" + re.escape(hinten), name) is not None


def ist_rundum(op):
    """Ist `op` eine Operation dieses Moduls?"""
    return isinstance(getattr(op, "Proxy", None), RundumSchruppen)


def _ascii(text):
    """Für Kommentare im NC-Programm: ohne Umlaute – nicht jede Steuerung nimmt sie."""
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe")):
        text = text.replace(alt, neu)
    text = text.replace("Ü", "Ue").replace("ß", "ss").replace("–", "-")
    return text.encode("ascii", "replace").decode("ascii").replace("(", "[").replace(")", "]")
