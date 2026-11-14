# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Leerfahrt: derselbe Schnitt noch einmal, ohne Zustellung (Manuel, 2026-11-14: „es muss auch
die möglichkeit geben das man leerfahrten eingeben kann .. also beispielsweise schruppen .. erstes
vorschlichten ... und danach nochmal erstes vorschlichten .... dann messsen ... dann
vertigschlichten ... und dann nochmal vertig schlichten ... dann hat man immer 100 % das richtige
mass“).

Beim ersten Schnitt drängt es Fräser und Wand ab; fährt derselbe Schnitt noch einmal, nimmt er, was
die Abdrängung stehen ließ – erst danach stimmt, was man misst, und erst danach stimmt das Maß.

Eine eigene Operation, die nichts rechnet: Sie fährt die Bahn ihrer Quelle (`Quelle`, eine
Operation im selben Job) Satz für Satz noch einmal – mit deren Werkzeug, Vorschüben und Höhen.
Ändert sich die Quelle (anderes Aufmaß, anderer Fräser), rechnet FreeCAD die Leerfahrt danach von
selbst neu (die Verknüpfung). Für Materialstand, Abfahren und Kollision ist sie eine Operation wie
jede andere: Sie nimmt nichts weg, was die Quelle nicht schon genommen hat.

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import namen
from . import planfraesen as pf
from .sprache import tr

GRUPPE = "Fräsen"
FAHREN = ("G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03")


def gang_feld(op):
    """Der Name der Eigenschaft, in der bei `op` steht, was nach ihrem Schlichtgang stehen
    bleibt – None, wenn sie keine hat: der Schlichtzug der Kontur („Schlichtrest“; ihr „Aufmass“
    ist das des Schruppens davor), der Boden des Räumens („AufmassBoden“), sonst „Aufmass“."""
    felder = getattr(op, "PropertiesList", ())
    if "Schlichtrest" in felder and getattr(op, "Schlichten", False):
        return "Schlichtrest"
    if "AufmassBoden" in felder:
        return "AufmassBoden"
    return "Aufmass" if "Aufmass" in felder else None


def gang_aufmass(op):
    """So viel bleibt nach dem Schlichtgang `op` stehen (mm) – None ohne Angabe (gang_feld)."""
    feld = gang_feld(op)
    return None if feld is None else float(getattr(op, feld))


class Leerfahrt(PathOp.ObjectOp):
    """Proxy der Operation „Leerfahrt“."""

    def opFeatures(self, obj):
        return (
            PathOp.FeatureTool
            | PathOp.FeatureDepths
            | PathOp.FeatureHeights
            | PathOp.FeatureCoolant
        )

    def initOperation(self, obj):
        self._eigenschaften(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)

    @staticmethod
    def _eigenschaften(obj):
        for typ, name, text in (
            ("App::PropertyLink", "Quelle", tr("lf.eigenschaft.quelle")),
            ("App::PropertyLength", "Aufmass", tr("lf.eigenschaft.aufmass")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
        obj.setEditorMode("Aufmass", 1)  # nur lesen: das der Quelle

    def opExecute(self, obj):
        quelle = getattr(obj, "Quelle", None)
        befehle = list(quelle.Path.Commands) if quelle is not None else []
        fahrten = [b for b in befehle if b.Name in FAHREN]
        # FreeCAD hängt jeder Operation „G0 Z<Freifahrhöhe>“ an – auch dieser: das der Quelle
        # stünde sonst doppelt da.
        if fahrten and fahrten[-1].Name in ("G0", "G00") and set(fahrten[-1].Parameters) == {"Z"}:
            fahrten = fahrten[:-1]
        if not fahrten or not getattr(quelle, "Active", True):
            text = tr("lf.fehler.quelle")
            FreeCAD.Console.PrintError(f"{obj.Label}: {text}\n")
            self.commandlist.append(Path.Command("(Leerfahrt ohne Quelle)"))
            return
        aufmass = gang_aufmass(quelle)
        if aufmass is not None and abs(float(obj.Aufmass) - aufmass) > 1e-9:
            obj.Aufmass = aufmass
        self.commandlist.extend(Path.Command(b.Name, dict(b.Parameters)) for b in fahrten)


def lege_an(job, quelle, name=None):
    """Legt die Leerfahrt zu `quelle` im Job an (hinten) – ohne eigene Transaktion, die hält der
    Aufrufer. Werkzeug, Kühlung, Höhen und Tiefen wie die Quelle. Gibt die Operation zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Leerfahrt")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = Leerfahrt(obj, "Leerfahrt", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = quelle.ToolController
    obj.OpToolDiameter = quelle.ToolController.Tool.Diameter
    obj.CoolantMode = getattr(quelle, "CoolantMode", job.SetupSheet.CoolantMode)
    pf._hoehen(obj, proxy, job)
    for feld in ("StartDepth", "FinalDepth", "SafeHeight", "ClearanceHeight"):
        if feld in quelle.PropertiesList and feld in obj.PropertiesList:
            obj.setExpression(feld, None)
            setattr(obj, feld, getattr(quelle, feld))
    obj.Quelle = quelle
    if gang_aufmass(quelle) is not None:
        obj.Aufmass = gang_aufmass(quelle)
    obj.Label = namen.eindeutig(dokument, name or tr("lf.name", quelle=quelle.Label), obj)
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def ist_leerfahrt(op):
    """Ist `op` eine Leerfahrt des Addons?"""
    return isinstance(getattr(op, "Proxy", None), Leerfahrt)
