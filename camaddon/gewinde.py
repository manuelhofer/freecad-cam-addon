# SPDX-License-Identifier: LGPL-2.1-or-later
"""„Gewinde bohren“ aus dem Assistenten (W-006 S3g): FreeCADs Gewinde-Operation (Path.Op.Tapping)
mit einem Gewindebohrer aus der Werkzeugverwaltung – in Bohrungen mit seinem Kernloch
(Gewinde-Ø − Steigung, wie bei metrischen Gewinden üblich: M10 × 1,5 → Ø 8,5). Das Kernloch
macht vorher „Bohren“ oder „Bohrung fräsen“; das Gewinde kommt danach, es tritt gegen keine
Strategie an.

Tiefe: Durch eine durchgehende Bohrung geht der Gewindebohrer um seinen Anschnitt (2 ×
Steigung) hinaus; in einer Sackbohrung bleibt er eine Steigung über dem Grund. Rechts- oder
Linksgewinde sagt das Werkzeug (G84 oder G74 bei FreeCAD). Hier: welche Bohrungen ein
Gewindebohrer kann (passende()), die Bewegungen zum Schätzen der Zeit (planen(): hinein und
heraus mit Steigung · Drehzahl) und das Anlegen der Operation (lege_an()). Läuft ohne
Oberfläche.
"""

import math
from dataclasses import dataclass

from . import bahn as bn
from . import bohrung_bahn as bb
from . import einheiten
from .sprache import tr

GLEICH_D = 0.02  # mm – so genau muss das Kernloch passen
ANSCHNITT = 2.0  # × Steigung: so weit geht er durch eine durchgehende Bohrung hinaus
ABSTAND_GRUND = 1.0  # × Steigung: so weit bleibt er über dem Grund einer Sackbohrung
UEBER_R = 3.0  # mm über dem Rohteil: die Ebene R (wie beim Bohren)


@dataclass
class Gewindebahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt] – die Bewegungen des Zyklus, für die Zeit
    gewinde: int
    z_min: float
    zeit: float  # Minuten
    name: str = ""  # „M10 × 1.5“


def kernloch(durchmesser, steigung):
    """Der Durchmesser des Kernlochs (mm): Gewinde-Ø − Steigung."""
    return durchmesser - steigung


def passende(form, namen, durchmesser, steigung):
    """[Bohrung] – die Bohrungen `namen` von `form` mit dem Kernloch eines Gewindebohrers
    `durchmesser` × `steigung`. ValueError mit einem Satz, wenn eine nicht passt."""
    liste = bb.bohrungen(form, list(namen) or None)
    if not liste:
        raise ValueError(tr("gw.fehler.keine"))
    kern = kernloch(durchmesser, steigung)
    for b in liste:
        if abs(2 * b.radius - kern) > GLEICH_D:
            raise ValueError(
                tr(
                    "gw.fehler.kernloch",
                    gewinde=gewinde_name(durchmesser, steigung),
                    kern=einheiten.text(kern, einheiten.LAENGE),
                    durchmesser=einheiten.text(2 * b.radius, einheiten.LAENGE),
                )
            )
    return liste


def gewinde_name(durchmesser, steigung):
    """„M10x1.5“ – nur ASCII: FreeCAD schreibt den Namen der Operation als Kommentar ins
    Programm, und nicht jede Steuerung liest „ד."""
    return f"M{durchmesser:g}x{steigung:g}"


def tiefe_fuer(b, steigung):
    """Wie tief der Gewindebohrer in die Bohrung `b` geht (z der Spitze)."""
    if b.durch:
        return b.z_unten - ANSCHNITT * steigung
    return b.z_unten + ABSTAND_GRUND * steigung


def planen(liste, steigung, drehzahl, oben, sicher):
    """Die Bewegungen des Gewindezyklus über die Bohrungen `liste` (Reihenfolge des kürzesten
    Wegs): Eilgang über die Bohrung, auf R, mit Steigung · Drehzahl hinein und wieder heraus,
    zurück auf die sichere Höhe – für die Zeit; FreeCAD schreibt sie als G84 bzw. G74."""
    r_ebene = oben + UEBER_R
    offen = list(liste)
    folge = []
    ort = offen[0].mitte if offen else (0.0, 0.0)
    while offen:
        naechste = min(offen, key=lambda b: math.hypot(b.mitte[0] - ort[0], b.mitte[1] - ort[1]))
        offen.remove(naechste)
        folge.append(naechste)
        ort = naechste.mitte
    punkte = []
    z_min = math.inf
    for b in folge:
        x, y = b.mitte
        unten = tiefe_fuer(b, steigung)
        punkte.append(bn.Punkt(True, x, y, sicher))
        punkte.append(bn.Punkt(True, x, y, r_ebene))
        punkte.append(bn.Punkt(False, x, y, unten, True))
        punkte.append(bn.Punkt(False, x, y, r_ebene, True))  # heraus mit demselben Vorschub
        punkte.append(bn.Punkt(True, x, y, sicher))
        z_min = min(z_min, unten)
    vorschub = steigung * drehzahl
    zeit = bn.zeit(punkte, vorschub, vorschub) if vorschub > 0 else 0.0
    return Gewindebahn(punkte, len(folge), z_min, zeit)


def vorschau(job, werkzeug, flaechen, drehzahl):
    """Die Bahn für den Assistenten: die Bohrungen `flaechen` im Job mit dem Gewindebohrer
    `werkzeug` (werkzeuge.Werkzeug). ValueError mit einem Satz, wenn es nicht geht."""
    from . import planfraesen as pf
    from . import vierachs_schlichten as vs

    steigung = float(werkzeug.steigung)
    if steigung <= 0:
        raise ValueError(tr("gw.fehler.steigung"))
    form_teil = vs._teil(job.Model.Group)
    liste = passende(form_teil, flaechen, float(werkzeug.durchmesser), steigung)
    *_rohteil, oben = pf.rohteil_von_oben(job)
    bahn = planen(liste, steigung, drehzahl, oben, oben + 5.0)
    bahn.name = gewinde_name(float(werkzeug.durchmesser), steigung)
    return bahn


def je_tiefe(liste, tiefe):
    """[[Bohrung]] – die Bohrungen nach der Tiefe `tiefe(b)` gruppiert, die flachste zuerst:
    FreeCADs Bohr- und Gewinde-Operationen fahren alle Löcher bis zu ihrer einen Endtiefe."""
    gruppen = {}
    for b in liste:
        gruppen.setdefault(round(tiefe(b), 6), []).append(b)
    return [gruppen[z] for z in sorted(gruppen, reverse=True)]


def lege_an(job, tc, flaechen, name=None):
    """Legt FreeCADs „Gewinde“ (Path.Op.Tapping) im Job an – je Tiefe eine Operation (FreeCAD
    fährt alle Löcher einer Operation bis zu ihrer einen Endtiefe: ein durchgehendes Kernloch
    und eine Sackbohrung zusammen schnitten die Sackbohrung zu tief); ohne eigene Transaktion,
    die hält der Aufrufer. Die Bohrungen als Basis, die Tiefe nach tiefe_fuer(), R 3 mm über
    dem Rohteil, ohne Verweilen. Gibt die erste Operation zurück."""
    from . import vierachs_schlichten as vs

    steigung = float(getattr(tc.Tool, "Pitch", 0.0) or 0.0)
    liste = bb.bohrungen(vs._teil(job.Model.Group), list(flaechen) or None)
    gruppen = je_tiefe(liste, lambda b: tiefe_fuer(b, steigung)) or [[]]
    ops = [_lege_eine_an(job, tc, gruppe, steigung, name) for gruppe in gruppen]
    return ops[0]


def _lege_eine_an(job, tc, gruppe, steigung, name):
    import FreeCAD
    import Path.Op.Tapping as PathTapping

    from . import planfraesen as pf
    from . import vierachs_rohteil as vr

    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Tapping")
    # Ohne FreeCADs Vorgaben: Die suchen einen Controller und fragen bei mehreren nach.
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = PathTapping.ObjectTapping(obj, "Tapping", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    obj.Base = [(vr.modell(job), tuple(b.name for b in gruppe))]
    *_rohteil, oben = pf.rohteil_von_oben(job)
    obj.setExpression("FinalDepth", None)
    obj.FinalDepth = min((tiefe_fuer(b, steigung) for b in gruppe), default=0.0)
    obj.RetractHeight = oben + UEBER_R
    obj.ExtraOffset = "None"
    obj.DwellEnabled = False
    obj.DwellTime = 0.0
    durchmesser = float(tc.Tool.Diameter)
    obj.Label = name or tr(
        "gw.name", werkzeug=f"T{tc.ToolNumber}", gewinde=gewinde_name(durchmesser, steigung)
    )
    if FreeCAD.GuiUp:
        import Path.Op.Gui.Base as PathOpGui
        import Path.Op.Gui.Tapping as TappingGui

        obj.ViewObject.Proxy = PathOpGui.ViewProvider(obj.ViewObject, TappingGui.Command.res)
        obj.ViewObject.Visibility = True
    return obj


def ist_gewinde(op):
    """Ist `op` FreeCADs Gewinde-Operation?"""
    proxy = getattr(op, "Proxy", None)
    return type(proxy).__name__ == "ObjectTapping"
