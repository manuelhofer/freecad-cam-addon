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
Nur bei „Bohrung fräsen“ und der Nut, die erst schruppen und dann die Wand schlichten, fährt sie
allein den Schlichtzug der Quelle (schlichtzug()): Helix, Ringe und Bögen noch einmal gingen
durch die Luft (Luftfräsen weg, Manuel) – an einer Bohrung Ø 20 mit dem Ø 12 sind das ein
Mehrfaches des Schlichtzugs (test_gangfolge).
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
    bleibt – None, wenn sie keine hat: der Schlichtzug der Kontur, von „Bohrung fräsen“ und der
    Nut („Schlichtrest“; ihr „Aufmass“ ist das des Schruppens davor), der Boden des Räumens
    („AufmassBoden“), sonst „Aufmass“. Die Nut ohne Schlichtgang: „Aufmass“ (ihre Bögen lassen
    es an der Wand). „Bohrung fräsen“ ohne Schlichtzug: None – ihre Helix fräst dann auf Maß
    (bohrung_bahn._bohrung: das Aufmaß nur mit Schlichten), keine Eigenschaft sagt, was bleibt;
    gang_aufmass() gibt 0. Bis 0.379 hieß es hier „Aufmass“, und der Messstopp danach erwartete
    an der Bohrung Ø 30 nur Ø 29,4 (Gegenprüfung 2026-11-14)."""
    felder = getattr(op, "PropertiesList", ())
    schlichtzug = getattr(op, "Schlichten", False) or getattr(op, "NurSchlichten", False)
    if "Schlichtrest" in felder and schlichtzug:
        return "Schlichtrest"
    if "NurSchlichten" in felder:  # „Bohrung fräsen“, Nut ohne Schlichtzug
        if _bohrung_auf_mass(op):
            return None
        return "Aufmass" if "Aufmass" in felder else None
    if "AufmassBoden" in felder:
        return "AufmassBoden"
    return "Aufmass" if "Aufmass" in felder else None


def _bohrung_auf_mass(op):
    """„Bohrung fräsen“ ohne Schlichtzug: Die Helix fräst die Wand auf Maß."""
    from . import bohrung as bo

    schlichtzug = getattr(op, "Schlichten", False) or getattr(op, "NurSchlichten", False)
    return bo.ist_bohrungsfraesen(op) and not schlichtzug


def gang_aufmass(op):
    """So viel bleibt nach dem Schlichtgang `op` stehen (mm) – None ohne Angabe (gang_feld);
    „Bohrung fräsen“ ohne Schlichtzug 0."""
    feld = gang_feld(op)
    if feld is None:
        return 0.0 if _bohrung_auf_mass(op) else None
    return float(getattr(op, feld))


def _schlichtzug_modul(op):
    """Das Modul (bohrung, nut) mit schlichtzug(), wenn `op` erst schruppt und dann die Wand
    schlichtet – nur dann fährt ihre Leerfahrt allein den Schlichtzug; None sonst."""
    if not getattr(op, "Schlichten", False) or getattr(op, "NurSchlichten", True):
        return None
    from . import bohrung as bo
    from . import nut as nu

    if bo.ist_bohrungsfraesen(op):
        return bo
    if nu.ist_nut(op):
        return nu
    return None


def _leer_modul(quelle):
    """Das Modul, dessen schlichtzug() die Leerfahrt hinter `quelle` fährt – None: ihre ganze
    Bahn noch einmal. Wie _schlichtzug_modul, dazu die Nut, die nur schlichtet (der zweite der
    zwei gleichen Schnitte, „Schlichten danach“): dieselben Züge, aber in der eben geschlichteten
    Nut im Eilgang hinab statt 8 mm im Vorschub (Nut 16 × 8, Gegenprüfung 2026-11-14)."""
    modul = _schlichtzug_modul(quelle)
    if modul is None and getattr(quelle, "NurSchlichten", False):
        from . import nut as nu

        if nu.ist_nut(quelle):
            return nu
    return modul


def nur_schlichtzug(op):
    """Fährt die Leerfahrt zu `op` nur deren Schlichtzug (nicht die ganze Bahn)?"""
    return _schlichtzug_modul(op) is not None


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
        modul = _leer_modul(quelle) if befehle else None
        if modul is not None:
            befehle = self._schlichtzug(obj, quelle, modul)
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

    def _schlichtzug(self, obj, quelle, modul):
        """Die Befehle des Schlichtzugs der Quelle (modul.schlichtzug) – mit den Vorschüben des
        Werkzeugs, wie die Quelle sie fährt; leer, wenn es nicht geht (dann der Fehler wie ohne
        Quelle)."""
        from . import bahn as bn
        from . import vierachs_operation as vo

        vorschub = float(self.horizFeed or 0.0) * 60.0
        try:
            bahn = modul.schlichtzug(
                quelle, self.job, self.model, vorschub, vo.eintauchvorschub(self)
            )
        except ValueError as fehler:
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            return []
        if bahn is None or vorschub <= 0:
            return []
        return list(bn.befehle(bahn.punkte, vorschub, vo.eintauchvorschub(self)))


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
