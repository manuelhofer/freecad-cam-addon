# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Dichtnut hobeln“ – Schritt 4 des Bauplans (Spezifikation Strategien 13.10).

Ein Stoßwerkzeug (werkzeuge.STOSSWERKZEUG) steht in der Spindel und wird längs der Mittellinie
einer umlaufenden Nut gezogen; die Spindel dreht nicht, sie stellt die Schneide je Satz in
Fahrtrichtung (hobeln_bahn). Die Nut ist davor gefräst bis auf den Rest über dem Grund; die
Operation nimmt ihn in Umläufen weg, mit Leerumläufen am Ende – die Riefen laufen längs der Nut.

Wie „Ringnut fräsen“ (ringnut) eine eigene Operation (FreeCADs ObjectOp) mit Werkzeug-Controller,
Kühlmittel und FreeCADs Tiefen und Höhen. Den Spindelwinkel trägt jeder Satz als Kommentar
„(SPINDEL …)“ davor; das Programm (postprozessor) macht daraus je Steuerung den Winkel der
stehenden Spindel. Der Vorschub ist der des Controllers (beim Hobeln die Schnittgeschwindigkeit).

Von oben gesehen nimmt die Klinge nicht mehr weg als ein Fräser so breit wie sie – für Materialstand
und Abfahren zählt sie so; ob sie in der Nut bleibt, prüft hobeln_bahn (die Klinge als Rechteck).

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import bahn as bn
from . import hobeln_bahn as hb
from . import namen
from . import planfraesen as pf
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from .sprache import tr

GRUPPE = "Hobeln"
ZUSTELLUNG = 0.05  # mm je Umlauf – vorsichtig unter Horns Grenze 0,3 je Hub
REST = 0.2  # mm, die das Fräsen davor über dem Grund stehen lässt
VORSCHUB = 6000.0  # mm/min Hub – ein Zehntel von Horns 60 m/min, die Spindel hält je Satz an


class DichtnutHobeln(PathOp.ObjectOp):
    """Proxy der Operation „Dichtnut hobeln“."""

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
        obj.Rest = REST
        obj.Leerumlaeufe = 1
        obj.Satzlaenge = hb.SCHRITT
        obj.Sicherheitsabstand = vb.SICHERHEIT

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)

    @staticmethod
    def _eigenschaften(obj):
        for typ, name, text in (
            ("App::PropertyStringList", "Flaechen", tr("ho.eigenschaft.flaechen")),
            ("App::PropertyLength", "Zustellung", tr("ho.eigenschaft.zustellung")),
            ("App::PropertyLength", "Rest", tr("ho.eigenschaft.rest")),
            ("App::PropertyLength", "Aufmass", tr("ho.eigenschaft.aufmass")),
            ("App::PropertyInteger", "Leerumlaeufe", tr("ho.eigenschaft.leerumlaeufe")),
            ("App::PropertyLength", "Satzlaenge", tr("ho.eigenschaft.satzlaenge")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyInteger", "Nuten", tr("ho.eigenschaft.nuten")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
        obj.setEditorMode("Nuten", 1)

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(
                obj, self.job, self.model, self.horizFeed * 60.0, self.vertFeed * 60.0
            )
        except ValueError as fehler:
            obj.Nuten = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        punkte, nuten = ergebnis
        obj.Nuten = nuten
        self.commandlist.extend(
            bn.befehle(punkte, self.horizFeed * 60.0, (self.vertFeed * 60.0) or None)
        )


def werkzeug_des_controllers(tc):
    """Das Stoßwerkzeug des Controllers aus der Werkzeugverwaltung – None, wenn es keins ist."""
    from . import job_schnittwerte as js
    from . import werkzeuge as wz

    try:
        bibliothek = wz.Bibliothek.laden()
    except Exception:  # noqa: BLE001
        return None
    werkzeug = js.werkzeug_von(tc, bibliothek)
    if werkzeug is None or werkzeug.art != wz.STOSSWERKZEUG:
        return None
    return werkzeug


def controller(dokument, job, werkzeug, vorschub=VORSCHUB, nummer=None):
    """Legt den Werkzeug-Controller für das Stoßwerkzeug `werkzeug` an – ohne eigene Transaktion.

    Die Spindel steht (SpindleDir „None“, 0 U/min: kein M3 im Programm); der Vorschub ist die
    Hubgeschwindigkeit, eintauchen mit einem Viertel davon."""
    from Path.Tool import Controller
    from Path.Tool.camassets import cam_assets

    from . import job_schnittwerte as js

    nummer = nummer or js._platz_im_magazin(job, werkzeug)
    nummer = nummer or js._aus_magazin(job, werkzeug) or werkzeug.nummer or js.freie_nummer(job)
    FreeCAD.setActiveDocument(dokument.Name)
    bit = js.werkzeug_im_job(job, werkzeug)
    if bit is None:
        bit = cam_assets.get(f"toolbit://{js.PRAEFIX}{werkzeug.kennung}").attach_to_doc(
            doc=dokument
        )
        js._ohne_zaehler(bit, wz_name(werkzeug))
        if getattr(bit, "ViewObject", None) is not None:
            bit.ViewObject.Visibility = False
    name = f"T{nummer} {werkzeug.name} – {tr('ho.einsatz')}" if werkzeug.name else None
    tc = Controller.Create(
        name or f"T{nummer} {tr('ho.einsatz')}", tool=bit, toolNumber=nummer or werkzeug.nummer
    )
    job.Proxy.addToolController(tc)
    tc.SpindleDir = "None"
    tc.SpindleSpeed = 0.0
    tc.HorizFeed = FreeCAD.Units.Quantity(f"{round(vorschub)} mm/min")
    tc.VertFeed = FreeCAD.Units.Quantity(f"{round(vorschub / 4.0)} mm/min")
    return tc


def wz_name(werkzeug):
    """Der Anzeigename des Werkzeugs (werkzeuge.anzeigename)."""
    from . import werkzeuge as wz

    return wz.anzeigename(werkzeug)


def werte_fuer(werkzeug, sicher, vorschub, eintauchen=0.0, zustellung=ZUSTELLUNG, rest=REST,
               aufmass=0.0, leerumlaeufe=1, satzlaenge=hb.SCHRITT, sicherheit=vb.SICHERHEIT):  # fmt: skip
    """Die Hobelwerte (hobeln_bahn.Hobelwerte) zum Stoßwerkzeug `werkzeug`."""
    return hb.Hobelwerte(
        breite=float(werkzeug.schneidenbreite),
        laenge=float(werkzeug.klingenlaenge),
        versatz=float(werkzeug.spindelwinkel),
        zustellung=float(zustellung),
        rest=float(rest),
        sicher=float(sicher),
        vorschub=float(vorschub),
        eintauchen=float(eintauchen or 0.0),
        aufmass=float(aufmass),
        leerumlaeufe=int(leerumlaeufe),
        sicherheit=float(sicherheit),
        schritt=max(float(satzlaenge), 0.05),
    )


def rechne(obj, job, modell, vorschub=0.0, eintauchen=0.0):
    """([bahn.Punkt] aller Nuten hintereinander, Anzahl Nuten) für die Operation `obj`.
    ValueError mit einem Satz, wenn es nicht geht."""
    werkzeug = werkzeug_des_controllers(obj.ToolController)
    if werkzeug is None:
        raise ValueError(tr("ho.fehler.werkzeug"))
    form_teil = vs._teil(modell)
    nuten = hb.hobelnuten(form_teil, list(obj.Flaechen) or None)
    if not nuten:
        raise ValueError(tr("ho.fehler.keine"))
    w = werte_fuer(
        werkzeug, float(obj.SafeHeight), vorschub or 1000.0, eintauchen,
        float(obj.Zustellung), float(obj.Rest), float(obj.Aufmass), int(obj.Leerumlaeufe),
        float(obj.Satzlaenge), float(obj.Sicherheitsabstand),
    )  # fmt: skip
    punkte = []
    for nut in nuten:
        punkte.extend(hb.planen(nut, w).punkte)
    return punkte, len(nuten)


def lege_an(job, tc, flaechen=(), name=None, zustellung=ZUSTELLUNG, rest=REST, aufmass=0.0,
            leerumlaeufe=1):  # fmt: skip
    """Legt „Dichtnut hobeln“ im Job an – ohne eigene Transaktion. Gibt die Operation zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "DichtnutHobeln")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = DichtnutHobeln(obj, "DichtnutHobeln", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    obj.Flaechen = list(flaechen)
    obj.Zustellung = float(zustellung)
    obj.Rest = float(rest)
    obj.Aufmass = float(aufmass)
    obj.Leerumlaeufe = int(leerumlaeufe)
    try:
        liste = hb.hobelnuten(vs._teil(job.Model.Group), list(flaechen) or None)
    except ValueError:
        liste = []
    if liste:
        obj.setExpression("FinalDepth", None)
        obj.FinalDepth = min(n.z_boden for n in liste)
    obj.Label = namen.eindeutig(dokument, name or tr("ho.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def ist_hobeln(op):
    """Ist `op` eine Operation „Dichtnut hobeln“?"""
    return isinstance(getattr(op, "Proxy", None), DichtnutHobeln)
