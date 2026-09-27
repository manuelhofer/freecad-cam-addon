# SPDX-License-Identifier: LGPL-2.1-or-later
"""Schnittwerte aus der Werkzeugverwaltung in die Werkzeug-Controller eines CAM-Jobs (W-002, Stufe 2).

Ein Werkzeug-Controller (TC) hält in FreeCAD Drehzahl und Vorschübe für ein
Werkzeug. Dieses Modul findet zu jedem TC das Werkzeug der
Werkzeugverwaltung – über die ToolBit-ID „camaddon_…“ der übergebenen
Bibliothek, sonst über T-Nummer und Durchmesser –, schlägt einen Einsatz
vor und rechnet n und vf aus dessen vc und fz. Passt der Einsatz zu einer
Operation, die den TC benutzt, bekommt sie auch ae und ap als Schrittweite
und Zustelltiefe. Gesetzt wird in einer Transaktion (ein Strg+Z).

Das ist der Weg für FreeCAD 1.1.3, das Schnittwerte am Werkzeug nicht kennt;
im Wochen-Build geht es zusätzlich über FreeCADs eigenen Vorschlag.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field

import FreeCAD

from . import schnittdaten as sd
from . import werkzeuge as wz
from .uebergabe_werkzeuge import PRAEFIX, freecad_werkstoffe

# Anteil des Vorschubs beim Eintauchen und Rampen – wie FreeCADs Vorgabe für
# neue Presets. Beim Bohren ist der senkrechte Vorschub der Vorschub selbst.
VERHAELTNIS_EINTAUCHEN = 0.33
DURCHMESSER_TOLERANZ = 0.01  # mm, für die Suche über T-Nummer und Durchmesser

# Operation (Modul der CAM-Operation) → Einsätze, die zu ihr passen, der
# passendste zuerst. Ein Werkzeug mit nur einer Art Einsatz bekommt ohnehin
# dessen erste Zeile.
EINSATZ_NACH_OPERATION = {
    "Adaptive": (wz.DYNAMISCH,),
    "Pocket": (wz.SCHRUPPEN,),
    "PocketShape": (wz.SCHRUPPEN,),
    "MillFace": (wz.PLANEN, wz.SCHRUPPEN),
    "MillFacing": (wz.PLANEN, wz.SCHRUPPEN),  # Planfräsen im Wochen-Build
    "Profile": (wz.SCHLICHTEN, wz.VERRUNDEN, wz.FASEN),
    "Slot": (wz.VOLLNUT,),
    "Deburr": (wz.FASEN, wz.VERRUNDEN),  # Entgraten: an der Kante entlang
    "Engrave": (wz.FASEN,),
    "Vcarve": (wz.FASEN,),
    "ThreadMilling": (wz.GEWINDEFRAESEN,),
    "Tapping": (wz.GEWINDEBOHREN,),
    # Die Bohrung des Wochen-Builds kann auch Gewinde schneiden.
    "Drilling": (
        wz.BOHREN,
        wz.ZENTRIEREN,
        wz.SENKEN,
        wz.REIBEN,
        wz.AUSDREHEN,
        wz.GEWINDEBOHREN,
    ),
}


# Operation → Einsätze, deren ae und ap als Schrittweite und Zustelltiefe
# in sie passen. Dynamisch nur ins Adaptive: Nur dort hält FreeCAD den
# Eingriff klein – eine Tasche fährt zuerst eine volle Nut, mit ap über die
# ganze Schneide bräche der Fräser. Das Profil bekommt nichts: Mit ihm wird
# auch ausgeschnitten, also in voller Nut.
ZUSTELLUNG_NACH_OPERATION = {
    "Adaptive": (wz.DYNAMISCH, wz.SCHRUPPEN),
    "Pocket": (wz.SCHRUPPEN,),
    "PocketShape": (wz.SCHRUPPEN,),
    "MillFace": (wz.PLANEN, wz.SCHRUPPEN),
    "MillFacing": (wz.PLANEN, wz.SCHRUPPEN),
    "Slot": (wz.VOLLNUT,),
}


# Der Eintauchwinkel der Helix im Adaptiv: im Wochen-Build HelixMaxRampAngle,
# in 1.1.3 HelixAngle – beide in Grad.
HELIX_WINKEL = ("HelixMaxRampAngle", "HelixAngle")

# Dünner als dieser Anteil von ap ist die letzte Ebene nur ein Rest: ein
# eigener Umlauf (im Adaptiv mit eigener Helix) für wenig Material.
DUENNE_EBENE = 0.25


@dataclass
class Gesetzt:
    """Was setze() geändert hat."""

    controller: int = 0  # Anzahl
    operationen: list = field(default_factory=list)  # Beschriftungen


def jobs(dokument):
    """Die CAM-Jobs im Dokument."""
    if dokument is None:
        return []
    return [o for o in dokument.Objects if type(getattr(o, "Proxy", None)).__name__ == "ObjectJob"]


def dokumente_mit_jobs(aktiv=None):
    """Die offenen Dokumente mit CAM-Jobs – `aktiv` (das aktive Dokument) zuerst."""
    alle = [d for d in FreeCAD.listDocuments().values() if jobs(d)]
    return sorted(alle, key=lambda d: d is not aktiv)


def werkzeug_controller(job):
    """Die Werkzeug-Controller des Jobs, in ihrer Reihenfolge."""
    werkzeuge = getattr(job, "Tools", None)
    return list(werkzeuge.Group) if werkzeuge is not None else []


def werkstoff_des_jobs(job, werkstoffe):
    """Der Werkstoff der Werkzeugverwaltung, der zum Werkstoff des Rohteils passt, oder None.

    Verglichen wird die Werkstoffnummer der FreeCAD-Werkstoffkarte
    (MaterialNumber). Gibt es mehrere Einträge mit der Nummer (geglüht und
    gehärtet), gilt der erste – der Dialog lässt ihn ändern.
    """
    nummer = nummer_am_rohteil(job)
    if not nummer:
        return None
    return next((w for w in werkstoffe if w.nummer == nummer), None)


def nummer_am_rohteil(job):
    """Die Werkstoffnummer der Werkstoffkarte am Rohteil, oder „“."""
    material = getattr(getattr(job, "Stock", None), "ShapeMaterial", None)
    if material is None:
        return ""
    return str(
        (getattr(material, "PhysicalProperties", {}) or {}).get("MaterialNumber", "")
    ).strip()


def karte_fuer(werkstoff):
    """(UUID, Name) der FreeCAD-Werkstoffkarte mit der Nummer des Werkstoffs, oder None."""
    if werkstoff is None or not werkstoff.nummer:
        return None
    return freecad_werkstoffe().get(werkstoff.nummer)


def setze_werkstoff_am_rohteil(dokument, job, werkstoff):
    """Trägt am Rohteil die FreeCAD-Werkstoffkarte mit der Nummer des Werkstoffs ein.

    Dann schlägt „Schnittwerte in den Job“ den Werkstoff beim nächsten Mal
    selbst vor, und im Wochen-Build findet FreeCADs eigener Vorschlag die
    Schnittwerte. Gibt den Namen der Karte zurück, oder None, wenn FreeCAD
    keine Karte mit dieser Nummer hat. Eine Transaktion (ein Strg+Z).
    """
    import Materials

    karte = karte_fuer(werkstoff)
    rohteil = getattr(job, "Stock", None)
    if karte is None or rohteil is None or not hasattr(rohteil, "ShapeMaterial"):
        return None
    uuid, name = karte
    dokument.openTransaction("Werkstoff am Rohteil")
    try:
        rohteil.ShapeMaterial = Materials.MaterialManager().getMaterial(uuid)
    except Exception:
        dokument.abortTransaction()
        raise
    dokument.commitTransaction()
    dokument.recompute()
    return name


def werkzeug_von(tc, bibliothek):
    """Das Werkzeug der Werkzeugverwaltung zu diesem TC, oder None."""
    werkzeug = getattr(tc, "Tool", None)
    kennung = str(getattr(werkzeug, "ToolBitID", "") or "")
    if kennung.startswith(PRAEFIX):
        gefunden = next(
            (w for w in bibliothek.werkzeuge if w.kennung == kennung[len(PRAEFIX) :]), None
        )
        if gefunden is not None:
            return gefunden
    durchmesser = _mm(getattr(werkzeug, "Diameter", None))
    for w in bibliothek.werkzeuge:
        if w.nummer == getattr(tc, "ToolNumber", -1) and abs(w.durchmesser - durchmesser) < (
            DURCHMESSER_TOLERANZ
        ):
            return w
    return None


def _mm(wert):
    try:
        return float(wert.getValueAs("mm"))
    except AttributeError:
        return 0.0


def vorgeschlagener_einsatz(tc, einsaetze, job):
    """Welche Zeile der Tabelle am ehesten passt; Index oder -1, wenn es keine gibt.

    Erst der Name des TC („T3 Schruppen dynamisch“ enthält den Namen einer
    Zeile), dann die Operationen, die den TC benutzen, sonst die erste Zeile.
    Passen mehrere Namen, gewinnt der längste: „T3 Schruppen dynamisch“
    enthält auch „Schruppen“.
    """
    if not einsaetze:
        return -1
    beschriftung = tc.Label.lower()
    passend = [
        i for i, einsatz in enumerate(einsaetze) if wz.einsatz_name(einsatz).lower() in beschriftung
    ]
    if passend:
        return max(passend, key=lambda i: len(wz.einsatz_name(einsaetze[i])))
    for operation in operationen_mit(tc, job):
        for art in EINSATZ_NACH_OPERATION.get(operationsart(operation), ()):
            for i, einsatz in enumerate(einsaetze):
                if einsatz.art == art:
                    return i
    return 0


def operationen(job):
    """Die Operationen des Jobs."""
    try:
        return job.Proxy.allOperations()
    except AttributeError:
        return []


def operationen_mit(tc, job):
    """Die Operationen des Jobs, die diesen Werkzeug-Controller benutzen."""
    return [o for o in operationen(job) if getattr(o, "ToolController", None) is tc]


def unbenutzte_fremde_controller(job, bibliothek):
    """Werkzeug-Controller, die keine Operation benutzt und deren Werkzeug nicht in der
    Werkzeugverwaltung steht – etwa FreeCADs „TC: 5mm Endmill“, den jeder neue Job
    bekommt (Durchsicht W-004, D-30)."""
    return [
        tc
        for tc in werkzeug_controller(job)
        if werkzeug_von(tc, bibliothek) is None and not operationen_mit(tc, job)
    ]


def entferne_controller(dokument, controller, schritt):
    """Entfernt die Werkzeug-Controller wie Löschen im Baum: mit ihrem Werkzeug samt dessen
    Körper, wenn kein anderer Controller es benutzt (FreeCADs eigenes onDelete). Ein Schritt
    Rückgängig."""
    dokument.openTransaction(schritt)
    for tc in controller:
        proxy = getattr(tc, "Proxy", None)
        if hasattr(proxy, "onDelete"):
            proxy.onDelete(tc)
        if dokument.getObject(tc.Name) is not None:
            dokument.removeObject(tc.Name)
    dokument.commitTransaction()
    dokument.recompute()


def operationsart(operation):
    """Die Art einer CAM-Operation – der Name ihres Moduls: „Adaptive“, „Pocket“ …"""
    return type(getattr(operation, "Proxy", None)).__module__.rsplit(".", 1)[-1]


def zustellung(operation, werkzeug, einsatz):
    """{Eigenschaft: Wert} – Schrittweite und Zustelltiefe aus dem Einsatz, {} wenn er nicht passt.

    Die Schrittweite steht in FreeCAD in Prozent von D: in 1.1.3 als ganze
    Zahl (StepOver), im Adaptive des Wochen-Builds als Kommazahl
    (StepOverPercent). Abgerundet – aufgerundet läge sie über dem ae, das
    der Einsatz erlaubt.
    """
    if einsatz.art not in ZUSTELLUNG_NACH_OPERATION.get(operationsart(operation), ()):
        return {}
    werte = {}
    d = werkzeug.durchmesser
    if einsatz.ae > 0 and d > 0:
        prozent = min(einsatz.ae / d * 100.0, 100.0)
        if hasattr(operation, "StepOverPercent"):
            werte["StepOverPercent"] = max(math.floor(prozent * 10 + 1e-9) / 10, 0.1)
        elif hasattr(operation, "StepOver"):
            werte["StepOver"] = max(math.floor(prozent + 1e-9), 1)
    if einsatz.ap > 0 and hasattr(operation, "StepDown"):
        werte["StepDown"] = round(einsatz.ap, 3)
    # Der Eintauchwinkel gehört zum Werkzeug; das Adaptiv taucht helikal ein.
    if werkzeug.eintauchwinkel > 0:
        for eigenschaft in HELIX_WINKEL:
            if hasattr(operation, eigenschaft):
                werte[eigenschaft] = round(werkzeug.eintauchwinkel, 2)
                break
    return werte


def ebenen(operation, zustelltiefe):
    """Die Dicke der Ebenen in mm, die `operation` mit dieser Zustelltiefe fährt; [] wenn unbekannt.

    Gezählt wird von ihrer Starttiefe – FreeCAD setzt dafür die Oberkante des
    Rohteils – bis zur Endtiefe, mit FreeCADs eigener Rechnung
    (PathUtils.depth_params). Ein 25 mm tiefes Loch unter 1 mm Rohteil mit
    Zustelltiefe 25: [25, 1].
    """
    try:
        from PathScripts import PathUtils

        oben = float(operation.StartDepth.getValueAs("mm"))
        tiefen = PathUtils.depth_params(
            clearance_height=float(operation.ClearanceHeight.getValueAs("mm")),
            safe_height=float(operation.SafeHeight.getValueAs("mm")),
            start_depth=oben,
            step_down=zustelltiefe,
            z_finish_step=0.0,
            final_depth=float(operation.FinalDepth.getValueAs("mm")),
            user_depths=None,
        ).data
    except Exception:  # nur eine Anzeige – dann eben ohne Ebenen
        return []
    dicken = []
    for tiefe in tiefen:
        dicken.append(round(oben - float(tiefe), 3))
        oben = float(tiefe)
    return dicken


def ohne_bahn(operation):
    """True, wenn die Operation keine Basisgeometrie und deshalb keine Bahn hat.

    Adaptiv, Tasche, Planfräsen und Nut rechnen ohne Basisgeometrie nichts
    (ausprobiert in 1.1.3 und im Wochen-Build) – dann helfen auch
    Schrittweite und Zustelltiefe nicht.
    """
    if not hasattr(operation, "Base") or operation.Base:
        return False
    befehle = getattr(getattr(operation, "Path", None), "Commands", [])
    return not any(b.Name in ("G1", "G2", "G3") for b in befehle)


def duenne_letzte_ebene(dicken, zustelltiefe):
    """(Rest, ap ohne ihn), wenn die letzte Ebene nur ein Rest ist – sonst None.

    „ap ohne ihn“ ist die Zustelltiefe, mit der dieselbe Tiefe eine Ebene
    weniger braucht, auf 0,01 mm aufgerundet.
    """
    if len(dicken) < 2 or dicken[-1] >= DUENNE_EBENE * zustelltiefe:
        return None
    ohne = math.ceil(sum(dicken) / (len(dicken) - 1) * 100 - 1e-6) / 100
    return dicken[-1], ohne


def werte(werkzeug, einsatz):
    """(n in U/min, vf in mm/min, senkrechter Vorschub in mm/min) für diesen Einsatz."""
    n, vf, _q = sd.rechne(werkzeug, einsatz)
    # Bohrende Arten (Bohrer, Senker, Reibahle …) tauchen mit vollem Vorschub ein.
    senkrecht = vf if wz.bohrend(werkzeug.art) else vf * VERHAELTNIS_EINTAUCHEN
    return n, vf, senkrecht


def controller_name(werkzeug, einsatz):
    """„T3 Schruppen dynamisch“, mit eingetragenem Namen „T3 Fräser VHM 12 – Schruppen dynamisch“.

    Am Einsatz im Namen erkennt vorgeschlagener_einsatz() ihn wieder.
    """
    if werkzeug.name:
        return f"T{werkzeug.nummer} {werkzeug.name} – {wz.einsatz_name(einsatz)}"
    return f"T{werkzeug.nummer} {wz.einsatz_name(einsatz)}"


def lege_controller_an(dokument, job, werkzeug, einsatz):
    """Legt im Job einen Werkzeug-Controller für `werkzeug` an und setzt n und vf aus `einsatz`.

    Das Werkzeug kommt aus der Bibliothek „CAM-Addon“ – es muss vorher
    übergeben sein (uebergabe_werkzeuge.uebergeben). Der Name nennt den
    Einsatz (controller_name). Eine Transaktion: Strg+Z nimmt Controller
    und Werkzeug zurück. Gibt den neuen Controller zurück.
    """
    from Path.Tool import Controller
    from Path.Tool.camassets import cam_assets

    # Controller.Create legt im aktiven Dokument an.
    FreeCAD.setActiveDocument(dokument.Name)
    dokument.openTransaction("Werkzeug-Controller anlegen")
    try:
        bit = cam_assets.get(f"toolbit://{PRAEFIX}{werkzeug.kennung}").attach_to_doc(doc=dokument)
        tc = Controller.Create(
            controller_name(werkzeug, einsatz), tool=bit, toolNumber=werkzeug.nummer
        )
        job.Proxy.addToolController(tc)
        _setze_werte(tc, werkzeug, einsatz)
    except Exception:
        dokument.abortTransaction()
        raise
    dokument.commitTransaction()
    dokument.recompute()
    return tc


def _setze_werte(tc, werkzeug, einsatz):
    """Drehzahl und Vorschübe eines TC aus dem Einsatz; False, wenn vc oder fz fehlen."""
    n, vf, senkrecht = werte(werkzeug, einsatz)
    if n <= 0 or vf <= 0:
        return False  # ohne vc und fz lieber nichts als 0 U/min
    tc.SpindleSpeed = float(round(n))
    tc.HorizFeed = FreeCAD.Units.Quantity(f"{round(vf)} mm/min")
    tc.VertFeed = FreeCAD.Units.Quantity(f"{round(senkrecht)} mm/min")
    return True


def setze(dokument, zuordnung, job=None):
    """Setzt Drehzahl und Vorschübe; `zuordnung` = [(tc, werkzeug, einsatz), …].

    Mit `job` bekommen auch dessen Operationen, die einen der TC benutzen,
    Schrittweite und Zustelltiefe aus dem Einsatz, wenn er zu ihnen passt
    (zustellung()). Alles in einer Transaktion: ein Strg+Z nimmt es zurück.
    Gibt zurück, wie viele TC und Operationen gesetzt wurden (Gesetzt).
    """
    gesetzt = Gesetzt()
    dokument.openTransaction("Schnittwerte übernehmen")
    try:
        for tc, werkzeug, einsatz in zuordnung:
            if not _setze_werte(tc, werkzeug, einsatz):
                continue
            gesetzt.controller += 1
            for operation in operationen_mit(tc, job) if job is not None else []:
                neu = zustellung(operation, werkzeug, einsatz)
                for eigenschaft, wert in neu.items():
                    # Die Zustelltiefe hängt in FreeCAD an einer Formel aus dem
                    # SetupSheet (Vorgabe: Werkzeugdurchmesser) – mit ihr stünde
                    # nach dem Neuberechnen wieder D da.
                    operation.setExpression(eigenschaft, None)
                    if eigenschaft == "StepDown":
                        wert = FreeCAD.Units.Quantity(f"{wert} mm")
                    setattr(operation, eigenschaft, wert)
                if neu:
                    gesetzt.operationen.append(operation.Label)
    except Exception:
        dokument.abortTransaction()
        raise
    dokument.commitTransaction()
    dokument.recompute()
    return gesetzt
