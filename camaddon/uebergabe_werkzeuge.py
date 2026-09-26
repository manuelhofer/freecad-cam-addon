# SPDX-License-Identifier: LGPL-2.1-or-later
"""Werkzeuge an CAM übergeben (W-002, Stufe 2): als FreeCAD-Werkzeugbibliothek „CAM-Addon“.

Jedes Werkzeug der Werkzeugverwaltung wird ein ToolBit (`.fctb`) in FreeCADs
Werkzeugsammlung, alle zusammen eine Bibliothek (`.fctl`) mit den
T-Nummern. Geschrieben wird über die Asset-Verwaltung von CAM
(`cam_assets.add_raw`) – so landen die Dateien dort, wo der Benutzer seine
CAM-Werkzeuge eingestellt hat, und CAM sieht sie sofort.

Die Schnittwerte gehen als „Presets“ mit, die der Wochen-Build von FreeCAD
kennt (Path/Tool/FeedsSpeeds): je Einsatz vc und fz, mit Werkstoff und
Bearbeitungsart. Dann schlägt FreeCADs eigener Knopf im Werkzeug-Controller
unsere Werte vor. Die stabile Version 1.1.3 liest die Presets nicht; die
Werkzeuge selbst übernimmt sie trotzdem.

Die ToolBits heißen `camaddon_<Kennung>`: Eine erneute Übergabe ersetzt sie,
und nur sie – Werkzeuge, die der Benutzer selbst in CAM angelegt hat,
bleiben unberührt. Werkzeuge, die es in der Werkzeugverwaltung nicht mehr
gibt, werden aus der Sammlung entfernt.

Läuft ohne Oberfläche.
"""

import json
from dataclasses import dataclass, field

from . import werkzeuge as wz

BIBLIOTHEK_ID = "camaddon"
BIBLIOTHEK_NAME = "CAM-Addon"
PRAEFIX = "camaddon_"

# Unsere Werkzeugart → Form in FreeCAD (Datei und Typ).
FORMEN = {
    wz.SCHAFTFRAESER: ("endmill", "Endmill"),
    wz.TORUSFRAESER: ("bullnose", "Bullnose"),
    wz.RADIUSFRAESER: ("ballend", "Ballend"),
    wz.FASENFRAESER: ("chamfer", "Chamfer"),
    wz.BOHRER: ("drill", "Drill"),
}

# Unser Einsatz → Bearbeitungsart der FreeCAD-Presets (FeedsSpeeds.OP_TYPES).
BEARBEITUNGSARTEN = {
    wz.VOLLNUT: "slot",
    wz.SCHRUPPEN: "pocket",
    wz.DYNAMISCH: "adaptive",
    wz.SCHLICHTEN: "profile",
    wz.BOHREN: "drill",
    wz.EIGEN: None,
}

SCHNEIDSTOFFE = {wz.VHM: "Carbide", wz.HSS: "HSS"}
FASENWINKEL = 90.0  # °, Fasenfräser ohne eigene Angabe
VORSCHUBVERHAELTNIS_EINTAUCHEN = 0.33  # wie FreeCADs Vorgabe für neue Presets


@dataclass
class Bericht:
    """Was die Übergabe getan hat – für die Rückmeldung im Dialog."""

    werkzeuge: int = 0
    ohne_durchmesser: int = 0  # übersprungen – ohne D gibt es kein Werkzeug
    presets: int = 0
    entfernt: int = 0
    werkstoffe_ohne_freecad: list = field(default_factory=list)  # Kurznamen


def verfuegbar():
    """Gibt es die Asset-Verwaltung von CAM? (1.1.3 und der Wochen-Build haben sie.)"""
    try:
        from Path.Tool.camassets import cam_assets  # noqa: F401 – der Import ist die Frage
    except ImportError:
        return False
    return True


def presets_moeglich():
    """Kennt diese FreeCAD-Version Schnittwert-Presets am Werkzeug? (Wochen-Build ja, 1.1.3 nein)"""
    try:
        from Path.Tool import FeedsSpeeds  # noqa: F401 – der Import ist die Frage
    except ImportError:
        return False
    return True


def freecad_werkstoffe():
    """Werkstoffnummer → (UUID, Name) der FreeCAD-Werkstoffkarten, die eine Nummer haben."""
    try:
        import Materials
    except ImportError:
        return {}
    ergebnis = {}
    for uuid, werkstoff in Materials.MaterialManager().Materials.items():
        nummer = (getattr(werkstoff, "PhysicalProperties", {}) or {}).get("MaterialNumber")
        if nummer:
            ergebnis.setdefault(str(nummer).strip(), (uuid, werkstoff.Name))
    return ergebnis


def toolbit_daten(werkzeug, werkstoffe_nach_kennung, freecad_nach_nummer, bericht):
    """Das ToolBit als dict im Format von `.fctb` (Version 2)."""
    w = werkzeug
    datei, typ = FORMEN[w.art]
    d = w.durchmesser
    schneide = w.schneidenlaenge or 2 * d
    parameter = {
        "Diameter": f"{d} mm",
        "Flutes": w.schneiden,
        "Length": f"{wz.laenge_fuer_cam(w)} mm",
        "ShankDiameter": f"{wz.schaft_fuer_cam(w)} mm",
        "CuttingEdgeHeight": f"{schneide} mm",
    }
    if w.art == wz.TORUSFRAESER:
        parameter["CornerRadius"] = f"{w.eckradius or d / 10} mm"
    if w.art == wz.BOHRER:
        parameter["TipAngle"] = f"{wz.spitzenwinkel_fuer_cam(w)} °"
        del parameter["CuttingEdgeHeight"]
    if w.art == wz.FASENFRAESER:
        # Im Wochen-Build ergibt sich D aus Spitze, Winkel und Höhe:
        # 0 + 2 · D/2 · tan(90°/2) = D.
        parameter["CuttingEdgeAngle"] = f"{FASENWINKEL} °"
        parameter["TipDiameter"] = "0 mm"
        parameter["CuttingEdgeHeight"] = f"{d / 2} mm"
    alle = w.schnittwerte.get(wz.ALLE, [])
    attribute = {
        "Material": SCHNEIDSTOFFE[w.schneidstoff],
        "SpindleDirection": "Forward",
    }
    if alle and alle[0].fz:
        attribute["Chipload"] = f"{alle[0].fz} mm"
    daten = {
        "version": 2,
        "id": PRAEFIX + w.kennung,
        "name": wz.anzeigename(w),
        "shape": f"{datei}.fcstd",
        "shape-type": typ,
        "parameter": parameter,
        "attribute": attribute,
        # Woran das Addon seine Werkzeuge wiedererkennt; FreeCAD lässt
        # unbekannte Schlüssel stehen.
        "camaddon": {"kennung": w.kennung, "nummer": w.nummer},
    }
    presets = _presets(w, werkstoffe_nach_kennung, freecad_nach_nummer, bericht)
    if presets:
        daten["presets"] = presets
        bericht.presets += len(presets)
    return daten


def _presets(werkzeug, werkstoffe_nach_kennung, freecad_nach_nummer, bericht):
    """Je Einsatz ein Preset; „für alle Werkstoffe“ ohne Werkstoff-Hinweis."""
    presets = []
    for kennung, einsaetze in werkzeug.schnittwerte.items():
        hinweis = None
        name_werkstoff = ""
        if kennung != wz.ALLE:
            werkstoff = werkstoffe_nach_kennung.get(kennung)
            if werkstoff is None:
                continue  # Werkstoff gibt es nicht mehr
            name_werkstoff = werkstoff.nummer or werkstoff.kurzname
            uuid, name = freecad_nach_nummer.get(werkstoff.nummer, (None, werkstoff.kurzname))
            if uuid is None and werkstoff.kurzname not in bericht.werkstoffe_ohne_freecad:
                bericht.werkstoffe_ohne_freecad.append(werkstoff.kurzname)
            hinweis = {"uuid": uuid, "name": name}
        for einsatz in einsaetze:
            if not einsatz.vc and not einsatz.fz:
                continue
            titel = wz.einsatz_name(einsatz)
            presets.append(
                {
                    "name": f"{titel} – {name_werkstoff}" if name_werkstoff else titel,
                    "material_hint": hinweis,
                    "op_type_hint": BEARBEITUNGSARTEN[einsatz.art],
                    "surface_speed": einsatz.vc or None,
                    "chipload": einsatz.fz or None,
                    "vert_feed_ratio": VORSCHUBVERHAELTNIS_EINTAUCHEN,
                    "notes": f"ae {einsatz.ae:g} mm, ap {einsatz.ap:g} mm (CAM-Addon)",
                }
            )
    return presets


def uebergeben(bibliothek):
    """Schreibt alle Werkzeuge und die Bibliothek „CAM-Addon“ in CAMs Werkzeugsammlung."""
    from Path.Tool.camassets import cam_assets

    bericht = Bericht()
    werkstoffe_nach_kennung = {w.kennung: w for w in bibliothek.alle_werkstoffe()}
    freecad_nach_nummer = freecad_werkstoffe()
    tools = []
    neue_ids = set()
    for werkzeug in bibliothek.sortierte_werkzeuge():
        if werkzeug.durchmesser <= 0:
            bericht.ohne_durchmesser += 1
            continue
        daten = toolbit_daten(werkzeug, werkstoffe_nach_kennung, freecad_nach_nummer, bericht)
        cam_assets.add_raw("toolbit", daten["id"], json.dumps(daten, indent=2).encode("utf-8"))
        tools.append({"nr": werkzeug.nummer, "path": f"{daten['id']}.fctb"})
        neue_ids.add(daten["id"])
        bericht.werkzeuge += 1
    for uri in cam_assets.list_assets(asset_type="toolbit", store="local"):
        if uri.asset_id.startswith(PRAEFIX) and uri.asset_id not in neue_ids:
            cam_assets.delete(uri, store="local")
            bericht.entfernt += 1
    daten = {"label": BIBLIOTHEK_NAME, "tools": tools, "version": 1}
    cam_assets.add_raw("toolbitlibrary", BIBLIOTHEK_ID, json.dumps(daten, indent=2).encode("utf-8"))
    return bericht
