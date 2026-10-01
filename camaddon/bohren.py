# SPDX-License-Identifier: LGPL-2.1-or-later
"""„Bohren“ aus dem Assistenten (W-006 S3g): FreeCADs Bohr-Operation (Path.Op.Drilling) mit einem
Bohrer aus der Werkzeugverwaltung – für durchgehende Bohrungen mit dem Durchmesser des Bohrers.
Die Spitze geht um ihre Länge unter den Grund (ExtraOffset „Drill Tip“), damit die Bohrung bis
unten den vollen Durchmesser hat; tiefer als dreimal der Durchmesser in Hüben (G83), sonst in
einem Zug (G81). Eine Sackbohrung mit ebenem Grund kann ein Bohrer nicht – seine Spitze bliebe
stehen; die fräst „Bohrung fräsen“.

Hier: welche Bohrungen ein Bohrer kann (passende()), die Bewegungen des Zyklus zum Schätzen der
Zeit (planen(): Eilgang über die Bohrung, auf R, im Vorschub hinab – je Hub zurück auf R und
im Eilgang wieder bis knapp über den Grund des vorigen –, zuletzt zurück auf die sichere Höhe,
wie G98) und das Anlegen der Operation (lege_an()). Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

from . import bahn as bn
from . import bohrung_bahn as bb
from . import einheiten
from .sprache import tr

GLEICH_D = 0.02  # mm – so genau muss der Bohrer zur Bohrung passen
TIEF_AB = 3.0  # × D: tiefer bohrt er in Hüben (G83)
HUB_ANTEIL = 1.0  # × D: so tief je Hub, wenn nichts anderes gesagt ist
SPITZENWINKEL = 118.0  # Grad, wenn das Werkzeug keinen hat
UEBER_R = 3.0  # mm über dem Rohteil liegt die Ebene R (wie FreeCADs SafeHeightOffset)
ABSTAND_HUB = 0.5  # mm – so knapp über den Grund des vorigen Hubs fährt der Eilgang zurück


@dataclass
class Bohrbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt] – die Bewegungen des Zyklus, für die Zeit
    bohrungen: int
    hube: int  # über alle Bohrungen (ohne Hübe: je Bohrung einer)
    z_min: float  # die tiefste Spitze
    zeit: float  # Minuten (bahn.zeit)


def spitze(durchmesser, spitzenwinkel=SPITZENWINKEL):
    """Die Länge der Spitze (mm): so weit liegt sie unter dem vollen Durchmesser."""
    winkel = spitzenwinkel if 0 < spitzenwinkel < 180 else SPITZENWINKEL
    return (durchmesser / 2.0) / math.tan(math.radians(winkel / 2.0))


def hub_fuer(tiefe, durchmesser, hub=0.0):
    """So tief je Hub (mm): `hub`, wenn gesagt – sonst 1 × D bei Bohrungen tiefer als 3 × D,
    flacher in einem Zug (0). `tiefe` ist die Tiefe im Material (Oberkante Rohteil bis zur
    Spitze), nicht die Fahrt ab der Ebene R: die Luft darüber zählt nicht."""
    if hub > 0:
        return hub
    return durchmesser * HUB_ANTEIL if tiefe > TIEF_AB * durchmesser + 1e-9 else 0.0


def passende(form, namen, durchmesser):
    """[Bohrung] – die Bohrungen `namen` von `form`, die ein Bohrer mit `durchmesser` bohrt.
    ValueError mit einem Satz, wenn eine nicht passt (anderer Durchmesser, ebener Grund)."""
    liste = bb.bohrungen(form, list(namen) or None)
    if not liste:
        raise ValueError(tr("bh.fehler.keine"))
    for b in liste:
        if not b.durch:
            raise ValueError(
                tr("bh.fehler.sack", durchmesser=einheiten.text(2 * b.radius, einheiten.LAENGE))
            )
        if abs(2 * b.radius - durchmesser) > GLEICH_D:
            raise ValueError(
                tr(
                    "bh.fehler.durchmesser",
                    bohrer=einheiten.text(durchmesser, einheiten.LAENGE),
                    durchmesser=einheiten.text(2 * b.radius, einheiten.LAENGE),
                )
            )
    return liste


def planen(liste, durchmesser, spitzenwinkel, oben, sicher, vorschub, hub=0.0):
    """Die Bewegungen des Bohrzyklus über die Bohrungen `liste` (in der Reihenfolge des
    kürzesten Wegs) – für die Zeit; FreeCAD schreibt sie als G81/G83."""
    r_ebene = oben + UEBER_R
    lang = spitze(durchmesser, spitzenwinkel)
    offen = list(liste)
    folge = []
    ort = offen[0].mitte if offen else (0.0, 0.0)
    while offen:
        naechste = min(offen, key=lambda b: math.hypot(b.mitte[0] - ort[0], b.mitte[1] - ort[1]))
        offen.remove(naechste)
        folge.append(naechste)
        ort = naechste.mitte
    punkte = []
    hube = 0
    z_min = math.inf
    for b in folge:
        x, y = b.mitte
        unten = b.z_unten - lang
        q = hub_fuer(oben - unten, durchmesser, hub)  # die Tiefe im Material, nicht ab R
        punkte.append(bn.Punkt(True, x, y, sicher))
        punkte.append(bn.Punkt(True, x, y, r_ebene))
        tiefe = r_ebene
        while tiefe > unten + 1e-9:
            if q > 0 and tiefe < r_ebene - 1e-9:
                punkte.append(bn.Punkt(True, x, y, min(r_ebene, tiefe + ABSTAND_HUB)))
            ziel = max(unten, tiefe - q) if q > 0 else unten
            punkte.append(bn.Punkt(False, x, y, ziel, True))
            hube += 1
            tiefe = ziel
            if q > 0 and tiefe > unten + 1e-9:
                punkte.append(bn.Punkt(True, x, y, r_ebene))
        punkte.append(bn.Punkt(True, x, y, sicher))
        z_min = min(z_min, unten)
    zeit = bn.zeit(punkte, vorschub, vorschub) if vorschub > 0 else 0.0
    return Bohrbahn(punkte, len(folge), hube, z_min, zeit)


def vorschau(job, werkzeug, flaechen, vorschub, hub=0.0):
    """Die Bahn für den Assistenten: die Bohrungen `flaechen` im Job mit dem Bohrer `werkzeug`
    (werkzeuge.Werkzeug). ValueError mit einem Satz, wenn es nicht geht."""
    from . import planfraesen as pf
    from . import vierachs_schlichten as vs

    form_teil = vs._teil(job.Model.Group)
    liste = passende(form_teil, flaechen, float(werkzeug.durchmesser))
    *_rohteil, oben = pf.rohteil_von_oben(job)
    return planen(
        liste,
        float(werkzeug.durchmesser),
        float(werkzeug.spitzenwinkel or SPITZENWINKEL),
        oben,
        oben + 5.0,
        vorschub,
        hub,
    )


def lege_an(job, tc, flaechen, hub=0.0, name=None):
    """Legt FreeCADs „Bohren“ (Path.Op.Drilling) im Job an – je Tiefe des Grunds eine Operation
    (FreeCAD bohrt alle Löcher einer Operation bis zu ihrer einen Endtiefe); ohne eigene
    Transaktion, die hält der Aufrufer. Die Bohrungen als Basis, die Spitze unter den Grund
    („Drill Tip“), Hübe wie hub_fuer(), zurück auf R zwischen den Bohrungen (G98). Gibt die
    erste Operation zurück."""
    from . import gewinde as gw
    from . import vierachs_schlichten as vs

    liste = bb.bohrungen(vs._teil(job.Model.Group), list(flaechen) or None)
    gruppen = gw.je_tiefe(liste, lambda b: b.z_unten) or [[]]
    ops = [_lege_eine_an(job, tc, gruppe, hub, name) for gruppe in gruppen]
    return ops[0]


def _lege_eine_an(job, tc, gruppe, hub, name):
    import FreeCAD
    import Path.Op.Drilling as PathDrilling

    from . import planfraesen as pf
    from . import vierachs_rohteil as vr

    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Drilling")
    # Ohne FreeCADs Vorgaben: Die suchen einen Controller und fragen bei mehreren nach.
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = PathDrilling.ObjectDrilling(obj, "Drilling", job)
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
    obj.FinalDepth = min((b.z_unten for b in gruppe), default=0.0)
    obj.RetractHeight = oben + UEBER_R
    obj.ExtraOffset = "Drill Tip"
    durchmesser = float(tc.Tool.Diameter)
    tiefe = max((oben - (b.z_unten - spitze(durchmesser)) for b in gruppe), default=0.0)
    q = hub_fuer(tiefe, durchmesser, hub)
    obj.PeckEnabled = q > 0
    obj.PeckDepth = q if q > 0 else durchmesser
    obj.DwellEnabled = False
    obj.DwellTime = 0.0
    obj.KeepToolDown = False
    obj.Label = name or tr("bh.name", werkzeug=f"T{tc.ToolNumber}")
    if FreeCAD.GuiUp:
        import Path.Op.Gui.Base as PathOpGui
        import Path.Op.Gui.Drilling as DrillingGui

        obj.ViewObject.Proxy = PathOpGui.ViewProvider(obj.ViewObject, DrillingGui.Command.res)
        obj.ViewObject.Visibility = True
    return obj


def ist_bohren(op):
    """Ist `op` FreeCADs Bohr-Operation?"""
    proxy = getattr(op, "Proxy", None)
    return type(proxy).__name__ == "ObjectDrilling"
