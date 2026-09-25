# SPDX-License-Identifier: LGPL-2.1-or-later
"""Schnittwerte aus der Werkzeugverwaltung in die Werkzeug-Controller eines CAM-Jobs (W-002, Stufe 2).

Ein Werkzeug-Controller (TC) hält in FreeCAD Drehzahl und Vorschübe für ein
Werkzeug. Dieses Modul findet zu jedem TC das Werkzeug der
Werkzeugverwaltung – über die ToolBit-ID „camaddon_…“ der übergebenen
Bibliothek, sonst über T-Nummer und Durchmesser –, schlägt einen Einsatz
vor und rechnet n und vf aus dessen vc und fz. Gesetzt wird in einer
Transaktion (ein Strg+Z).

Das ist der Weg für FreeCAD 1.1.3, das Schnittwerte am Werkzeug nicht kennt;
im Wochen-Build geht es zusätzlich über FreeCADs eigenen Vorschlag.

Läuft ohne Oberfläche.
"""

import FreeCAD

from . import schnittdaten as sd
from . import werkzeuge as wz
from .uebergabe_werkzeuge import PRAEFIX

# Anteil des Vorschubs beim Eintauchen und Rampen – wie FreeCADs Vorgabe für
# neue Presets. Beim Bohren ist der senkrechte Vorschub der Vorschub selbst.
VERHAELTNIS_EINTAUCHEN = 0.33
DURCHMESSER_TOLERANZ = 0.01  # mm, für die Suche über T-Nummer und Durchmesser

# Operation (Modul der CAM-Operation) → Einsatz, der am ehesten passt.
EINSATZ_NACH_OPERATION = {
    "Adaptive": wz.DYNAMISCH,
    "Pocket": wz.SCHRUPPEN,
    "PocketShape": wz.SCHRUPPEN,
    "MillFace": wz.SCHRUPPEN,
    "Profile": wz.SCHLICHTEN,
    "Slot": wz.VOLLNUT,
    "Drilling": wz.BOHREN,
}


def jobs(dokument):
    """Die CAM-Jobs im Dokument."""
    if dokument is None:
        return []
    return [o for o in dokument.Objects if type(getattr(o, "Proxy", None)).__name__ == "ObjectJob"]


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
    rohteil = getattr(job, "Stock", None)
    material = getattr(rohteil, "ShapeMaterial", None)
    if material is None:
        return None
    nummer = str((getattr(material, "PhysicalProperties", {}) or {}).get("MaterialNumber", ""))
    if not nummer.strip():
        return None
    return next((w for w in werkstoffe if w.nummer == nummer.strip()), None)


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
    """
    if not einsaetze:
        return -1
    beschriftung = tc.Label.lower()
    for i, einsatz in enumerate(einsaetze):
        if wz.einsatz_name(einsatz).lower() in beschriftung:
            return i
    for operation in _operationen(job):
        if getattr(operation, "ToolController", None) is not tc:
            continue
        art = EINSATZ_NACH_OPERATION.get(type(operation.Proxy).__module__.rsplit(".", 1)[-1])
        for i, einsatz in enumerate(einsaetze):
            if einsatz.art == art:
                return i
    return 0


def _operationen(job):
    try:
        return job.Proxy.allOperations()
    except AttributeError:
        return []


def werte(werkzeug, einsatz):
    """(n in U/min, vf in mm/min, senkrechter Vorschub in mm/min) für diesen Einsatz."""
    n, vf, _q = sd.rechne(werkzeug, einsatz)
    senkrecht = vf if werkzeug.art == wz.BOHRER else vf * VERHAELTNIS_EINTAUCHEN
    return n, vf, senkrecht


def setze(dokument, zuordnung):
    """Setzt Drehzahl und Vorschübe; `zuordnung` = [(tc, werkzeug, einsatz), …].

    Alles in einer Transaktion: ein Strg+Z nimmt es zurück. Gibt die Zahl der
    gesetzten TC zurück.
    """
    gesetzt = 0
    dokument.openTransaction("Schnittwerte übernehmen")
    try:
        for tc, werkzeug, einsatz in zuordnung:
            n, vf, senkrecht = werte(werkzeug, einsatz)
            if n <= 0 or vf <= 0:
                continue  # ohne vc und fz lieber nichts als 0 U/min
            tc.SpindleSpeed = float(round(n))
            tc.HorizFeed = FreeCAD.Units.Quantity(f"{round(vf)} mm/min")
            tc.VertFeed = FreeCAD.Units.Quantity(f"{round(senkrecht)} mm/min")
            gesetzt += 1
    except Exception:
        dokument.abortTransaction()
        raise
    dokument.commitTransaction()
    dokument.recompute()
    return gesetzt
