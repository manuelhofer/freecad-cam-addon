# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Ringnut fräsen“ – eine Nut in einer Bohrung, von oben überdeckt
(Sicherungsring, O-Ring, Freistich), mit einem Scheiben- oder T-Nutenfräser (ringnut_bahn).

Wie „Bohrung fräsen“ (bohrung) eine eigene Operation (erbt FreeCADs ObjectOp) mit
Werkzeug-Controller, Kühlmittel und FreeCADs Tiefen und Höhen. Beim Neuberechnen rechnet sie ihre
Bahn aus dem Modell des Jobs, mit dem Nutenfräser aus der Werkzeugverwaltung (sonst aus dem
ToolBit des Controllers) und seinen Vorschüben für die Zeit.

Die Nut liegt unter dem Rand: Von oben, wie Materialstand (materialstand), Abtrag im Quader
(restmaterial.fuer_quader) und die Höhenfeld-Prüfer das Teil sehen, nimmt sie nichts weg – sie
zählt dort nicht (ist_ringnut); ob Scheibe, Hals, Schaft und Halter frei sind, prüft
ringnut_bahn.pruefen im Schnitt r–z, und die Kollision (kollision) rechnet die Körper ohnehin
räumlich.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Vollnut“. Kein Qt hier. Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import bahn as bn
from . import materialstand as mst
from . import namen, uhren
from . import planfraesen as pf
from . import ringnut_bahn as rn
from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from .sprache import tr

GRUPPE = "Fräsen"


class RingnutFraesen(PathOp.ObjectOp):
    """Proxy der Operation „Ringnut fräsen“."""

    def opFeatures(self, obj):
        return (
            PathOp.FeatureTool
            | PathOp.FeatureDepths
            | PathOp.FeatureHeights
            | PathOp.FeatureCoolant
        )

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Zustellung = 0.0
        obj.Schlichten = True
        obj.Rest = rn.SCHLICHT_REST
        obj.Gleichlauf = True
        obj.Sicherheitsabstand = vb.SICHERHEIT
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        neu = []
        for typ, name, text in (
            ("App::PropertyStringList", "Flaechen", tr("rn.eigenschaft.flaechen")),
            ("App::PropertyLength", "Zustellung", tr("rn.eigenschaft.zustellung")),
            ("App::PropertyBool", "Schlichten", tr("rn.eigenschaft.schlichten")),
            ("App::PropertyLength", "Rest", tr("rn.eigenschaft.rest")),
            ("App::PropertyBool", "Gleichlauf", tr("ra.eigenschaft.gleichlauf")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyInteger", "Nuten", tr("rn.eigenschaft.nuten")),
            ("App::PropertyInteger", "Kreise", tr("rn.eigenschaft.kreise")),
            ("App::PropertyString", "Materialstand", tr("ms.eigenschaft.materialstand")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Nuten", "Kreise"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis
        obj.setEditorMode("Materialstand", 2)  # woraus gerechnet (gui_materialstand)

    @uhren.atmend_rechnen
    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(
                obj, self.job, self.model, self.horizFeed * 60.0, vo.eintauchvorschub(self)
            )
        except ValueError as fehler:
            obj.Nuten = obj.Kreise = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Nuten, obj.Kreise = ergebnis.nuten, ergebnis.kreise
        for name, grund in ergebnis.nicht_passend:
            FreeCAD.Console.PrintWarning(f"{obj.Label}: {name}: {grund}\n")
        self.commandlist.extend(
            bn.befehle(ergebnis.punkte, self.horizFeed * 60.0, vo.eintauchvorschub(self))
        )


def werkzeug_des_controllers(tc):
    """(Nutenfräser, Halter, Länge ab Spindelnase) des Controllers: aus der Werkzeugverwaltung
    (mit Hals, Schaft und Halter), sonst aus dem ToolBit (der Schaft ist dort der Hals) – None
    statt des Werkzeugs, wenn es keins gibt."""
    from . import job_schnittwerte as js
    from . import werkzeuge as wz
    from .werkzeuge_aus_cam import vom_controller

    try:
        bibliothek = wz.Bibliothek.laden()
    except Exception:  # noqa: BLE001 – ohne Werkzeugverwaltung aus dem ToolBit
        bibliothek = None
    werkzeug = js.werkzeug_von(tc, bibliothek) if bibliothek is not None else None
    halter, laenge = None, 0.0
    if werkzeug is not None and bibliothek is not None:
        halter, laenge = halter_und_laenge(werkzeug, bibliothek)
    if werkzeug is None:
        try:
            werkzeug = vom_controller(tc)
        except AttributeError:
            werkzeug = None
    return werkzeug, halter, laenge


def halter_und_laenge(werkzeug, bibliothek):
    """(Halter, Länge ab Spindelnase) – der Halter, mit dem die Prüfung rechnet
    (Bibliothek.halter_fuer_pruefung), und die Länge darin; (None, 0) ohne."""
    from . import werkzeuge as wz

    try:
        halter = bibliothek.halter_fuer_pruefung(werkzeug)
    except Exception:  # noqa: BLE001
        halter = None
    if halter is None or halter.gewinkelt:
        return None, 0.0
    return halter, float(wz.laenge_im_halter(werkzeug, halter))


def rechne(obj, job, modell, vorschub=0.0, eintauchen=0.0):
    """Die Bahn (ringnut_bahn.Ringnutbahn) für die Operation `obj` im Job. ValueError mit einem
    Satz, wenn es nicht geht."""
    werkzeug, halter, laenge = werkzeug_des_controllers(obj.ToolController)
    # Der Materialstand davor nur gelesen: Steht in der Bohrung noch Material, ist sie nicht
    # fertig, und die Scheibe führe im Eilgang hinein (ringnut_bahn._bohrung_offen).
    stand = mst.fuer(job, vor=obj)
    if "Materialstand" in obj.PropertiesList:
        obj.Materialstand = mst.kennung_vor(job, obj)
    if stand is None:
        _bohrung_davor(obj, job, modell)
    return bahn_fuer(
        job,
        modell,
        werkzeug,
        float(obj.Zustellung),
        vo.flaechen(obj),
        schlichten=bool(obj.Schlichten),
        rest=float(obj.Rest),
        gleichlauf=sp.fuer_m3(obj.Gleichlauf, obj.ToolController),
        sicher=float(obj.SafeHeight),
        sicherheit=float(obj.Sicherheitsabstand),
        vorschub=vorschub,
        eintauchen=eintauchen,
        halter=halter,
        laenge=laenge,
        stand=stand,
    )


def _bohrung_davor(obj, job, modell):
    """Ohne Materialstand (davor eine Simultan-Operation oder eine gedrehte Rundachse –
    materialstand.fuer gibt dann None) sieht niemand, ob die Bohrung über der Nut fertig ist: Die
    Scheibe führe mittig hinab und begänne den ersten Kreis am Radius der Bohrung – auch in einer,
    die noch voll ist (Nachprüfung der Gegenprüfer, 2026-11-14). Dann muss eine aktive Operation
    davor im Job eine Wand der Bohrung über der Nut als Fläche haben (Bohrung fräsen, Reiben,
    Kontur, Schlichten danach); sonst ValueError mit dem Satz."""
    form_teil = vs._teil(modell)
    davor = set()
    for op in job.Operations.Group:
        if op == obj:
            break
        if getattr(op, "Active", True):
            davor.update(vo.flaechen(op))
            for _teil, namen in getattr(op, "Base", None) or ():
                davor.update(namen)
    for nut in rn.ringnuten(form_teil, list(vo.flaechen(obj)) or None):
        waende = rn.waende_ueber(form_teil, nut)
        if waende and not davor.intersection(waende):
            raise ValueError(tr("rn.fehler.bohrung_unbekannt", nut=nut.text()))


def bahn_fuer(
    job,
    modell,
    werkzeug,
    zustellung=0.0,
    flaechen=(),
    schlichten=True,
    rest=rn.SCHLICHT_REST,
    gleichlauf=True,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    vorschub=0.0,
    eintauchen=0.0,
    halter=None,
    laenge=0.0,
    stand=None,
):
    """Die Bahn „Ringnut fräsen“ für das Modell des Jobs. `flaechen`: Flächen der Nuten (eine
    genügt je Nut); leer: alle erreichbaren Ringnuten des Teils. ValueError mit einem Satz."""
    form_teil = vs._teil(modell)
    *_rohteil, z_oben = pf.rohteil_von_oben(job)
    if sicher is None:
        sicher = z_oben + sicherheit + 3.0
    liste = rn.ringnuten(form_teil, list(flaechen) or None)
    if not liste:
        raise ValueError(tr("rn.fehler.keine"))
    werte = rn.Ringnutwerte(
        werkzeug=werkzeug,
        zustellung=zustellung if zustellung > 0 else zustellung_vorschlag(werkzeug, None),
        sicher=sicher,
        sicherheit=sicherheit,
        gleichlauf=gleichlauf,
        schlichten=schlichten,
        rest=rest,
        vorschub=vorschub,
        eintauchen=eintauchen,
        halter=halter,
        laenge=laenge,
    )
    return rn.planen(werte, liste, form_teil, stand)


def zustellung_vorschlag(werkzeug, einsatz):
    """ae je radialer Stufe: das ae des Einsatzes, höchstens ringnut_bahn.STUFE_ANTEIL · D – die
    Einsätze eines Nutenfräsers nennen für die Vollnut ae = D (am Ø 19 aus den Richtwerten)."""
    if werkzeug is None or werkzeug.durchmesser <= 0:
        return 0.0
    grenze = rn.STUFE_ANTEIL * float(werkzeug.durchmesser)
    ae = float(getattr(einsatz, "ae", 0.0) or 0.0)
    return min(ae, grenze) if ae > 0 else grenze


def vorschau(job, modell, werkzeug, zustellung, flaechen, **weiter):
    """Die Bahn für den Assistenten – dieselbe wie bahn_fuer()."""
    return bahn_fuer(job, modell, werkzeug, zustellung, flaechen, **weiter)


def lege_an(job, tc, zustellung=0.0, schlichten=True, gleichlauf=True, name=None, flaechen=()):
    """Legt „Ringnut fräsen“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Tiefen
    und Höhen wie FreeCADs Operationen; die Endtiefe ist die tiefste Nut. Gibt die Operation
    zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "RingnutFraesen")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = RingnutFraesen(obj, "RingnutFraesen", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    obj.Zustellung = float(zustellung)
    obj.Schlichten = bool(schlichten)
    obj.Gleichlauf = bool(gleichlauf)
    obj.Flaechen = list(flaechen)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(
        obj.Document, name or tr("rn.name", werkzeug=f"T{tc.ToolNumber}"), obj
    )
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _endtiefe(obj, job):
    """Die Endtiefe: der Grund der tiefsten Nut."""
    try:
        form_teil = vs._teil(job.Model.Group)
        liste = rn.ringnuten(form_teil, list(obj.Flaechen) or None)
    except ValueError:
        liste = []
    if liste:
        obj.setExpression("FinalDepth", None)
        obj.FinalDepth = min(n.z_unten for n in liste)


def aendere(obj, tc, zustellung=0.0, schlichten=True, gleichlauf=True, flaechen=None):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` ohne bleibt. Der Name folgt dem Werkzeug, solange es der
    vorgeschlagene ist."""
    if namen.nach_vorlage(obj.Label, tr("rn.name", werkzeug="\0")):
        obj.Label = namen.eindeutig(obj.Document, tr("rn.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Zustellung = float(zustellung)
    obj.Schlichten = bool(schlichten)
    obj.Gleichlauf = bool(gleichlauf)
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def ist_ringnut(op):
    """Ist `op` eine Operation dieses Moduls – „Ringnut fräsen“?"""
    return isinstance(getattr(op, "Proxy", None), RingnutFraesen)
