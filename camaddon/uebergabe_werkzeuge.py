# SPDX-License-Identifier: LGPL-2.1-or-later
"""Werkzeuge an CAM übergeben (W-002, Stufe 2): als FreeCAD-Werkzeugbibliothek „CAM-Addon“.

Jedes Werkzeug der Werkzeugverwaltung wird ein ToolBit (`.fctb`) in FreeCADs
Werkzeugsammlung, alle zusammen eine Bibliothek (`.fctl`) mit den
T-Nummern. Geschrieben wird über die Asset-Verwaltung von CAM
(`cam_assets.add_raw`) – so landen die Dateien dort, wo der Benutzer seine
CAM-Werkzeuge eingestellt hat, und CAM sieht sie sofort.

Jede Art bekommt ihre Form in CAM (Spezifikation Werkzeugarten, Abschnitt
6) mit den Maßen, die auch ihr Bild zeigt – was nicht eingetragen ist,
geschätzt wie dort (werkzeuge.mass). Arten ohne eigene Form in CAM gehen
als die nächstliegende (NAEHERUNGEN), der Bericht nennt sie; Drehwerkzeuge
bleiben hier – FreeCAD dreht nicht.

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
from . import werkzeugform as wf

BIBLIOTHEK_ID = "camaddon"
BIBLIOTHEK_NAME = "CAM-Addon"
PRAEFIX = "camaddon_"

# Unsere Werkzeugart → Form in FreeCAD (Datei und Typ; der Gewindefräser
# liegt dort als „thread-mill“).
FORMEN = {
    wz.SCHAFTFRAESER: ("endmill", "Endmill"),
    wz.KUGELFRAESER: ("ballend", "Ballend"),
    wz.TORUSFRAESER: ("bullnose", "Bullnose"),
    wz.KONIKFRAESER: ("taperedballnose", "TaperedBallNose"),
    wz.SCHWALBENSCHWANZFRAESER: ("dovetail", "Dovetail"),
    wz.FASENFRAESER: ("chamfer", "Chamfer"),
    wz.RADIENFRAESER: ("radius", "Radius"),
    wz.NUTENFRAESER: ("slittingsaw", "SlittingSaw"),
    wz.GEWINDEFRAESER: ("thread-mill", "ThreadMill"),
    wz.BOHRER: ("drill", "Drill"),
    wz.NC_ANBOHRER: ("drill", "Drill"),
    wz.GEWINDEBOHRER_RECHTS: ("tap", "Tap"),
    wz.GEWINDEBOHRER_LINKS: ("tap", "Tap"),
    wz.KEGELSENKER: ("chamfer", "Chamfer"),
    wz.REIBAHLE: ("reamer", "Reamer"),
    wz.TASTER: ("probe", "Probe"),
}
# Arten ohne eigene Form in CAM → die Art, als die sie dort ankommen
# (Spezifikation Werkzeugarten, Abschnitt 2, „≈“).
NAEHERUNGEN = {
    wz.LOLLIPOPFRAESER: wz.KUGELFRAESER,
    wz.PLANFRAESER: wz.SCHAFTFRAESER,
    wz.FORMFRAESER: wz.SCHAFTFRAESER,
    wz.ZENTRIERBOHRER: wz.BOHRER,
    wz.FLACHSENKER: wz.SCHAFTFRAESER,
    wz.BOHRSTANGE: wz.SCHAFTFRAESER,
    wz.AUSSPINDELWERKZEUG: wz.SCHAFTFRAESER,
}
FORMEN.update({art: FORMEN[ziel] for art, ziel in NAEHERUNGEN.items()})
# Parameter, die Winkel sind (sonst Längen; Flutes ist eine Anzahl).
WINKEL = {"TipAngle", "TaperAngle", "CuttingEdgeAngle", "cuttingAngle"}

# Unser Einsatz → Bearbeitungsart der FreeCAD-Presets (FeedsSpeeds.OP_TYPES).
BEARBEITUNGSARTEN = {
    wz.VOLLNUT: "slot",
    wz.SCHRUPPEN: "pocket",
    wz.DYNAMISCH: "adaptive",
    wz.SCHLICHTEN: "profile",
    wz.BOHREN: "drill",
    # Seit P-2026-09-26-58: FreeCAD kennt nur diese sechs Arten.
    wz.PLANEN: "pocket",
    wz.FASEN: "profile",
    wz.VERRUNDEN: "profile",
    wz.GEWINDEFRAESEN: "profile",
    wz.ZENTRIEREN: "drill",
    wz.SENKEN: "drill",
    wz.REIBEN: "drill",
    wz.GEWINDEBOHREN: "drill",
    wz.AUSDREHEN: "drill",
    wz.EIGEN: None,
}

SCHNEIDSTOFFE = {wz.VHM: "Carbide", wz.HSS: "HSS"}
VORSCHUBVERHAELTNIS_EINTAUCHEN = 0.33  # wie FreeCADs Vorgabe für neue Presets
VORSCHUBVERHAELTNIS_BOHREN = 1.0  # Bohren: der Vorschub ist der senkrechte
# Kanten der Länge 0 mögen CAMs Skizzen nicht (keine Kappe unter der Säge,
# Schaft so dick wie der Gewindebohrer); 1 µm sieht man nicht.
WINZIG = 0.001  # mm
# Kürzer als Schneide und Hals bauen manche Formen keinen Körper – bei einer
# vertippten Gesamtlänge bekommt CAM so viel Schaft darüber.
MINDESTSCHAFT = 1.0  # mm


@dataclass
class Bericht:
    """Was die Übergabe getan hat – für die Rückmeldung im Dialog."""

    werkzeuge: int = 0
    ohne_durchmesser: int = 0  # übersprungen – ohne D gibt es kein Werkzeug
    # Übersprungen, weil CAM die Art (noch) nicht kennt – Kurztexte „T9 Drehwerkzeug“.
    ohne_form: list = field(default_factory=list)
    # Als nächstliegende Form übergeben: („T7 Lollipopfräser“, „Kugelfräser“).
    naeherungen: list = field(default_factory=list)
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
    parameter = {}
    for name, wert in parameter_fuer_cam(w).items():
        if name == "Flutes":
            parameter[name] = wert
        else:
            parameter[name] = f"{round(wert, 6)} {'°' if name in WINKEL else 'mm'}"
    attribute = {"SpindleDirection": drehrichtung(w)}
    if wz.hat_feld(w, "schneidstoff"):
        attribute["Material"] = SCHNEIDSTOFFE[w.schneidstoff]
    alle = w.schnittwerte.get(wz.ALLE, [])
    span = _span(w, alle[0].fz) if alle else None
    if span:
        attribute["Chipload"] = f"{span} mm"
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


def parameter_fuer_cam(werkzeug):
    """Die Maße als Parameter der Form in CAM: Längen in mm, Winkel in Grad, Flutes.

    Nur Parameter, die die Form hat; was nicht eingetragen ist, geschätzt wie
    im Bild (werkzeugform) – so zeigt CAM dasselbe Werkzeug.
    """
    w = werkzeug
    datei, _typ = FORMEN[w.art]
    parameter = {"Diameter": w.durchmesser}
    parameter.update(_PARAMETER[datei](w))
    unten = max(
        parameter.get("CuttingEdgeHeight", 0.0) + parameter.get("NeckHeight", 0.0),
        parameter.get("CuttingEdgeLength", 0.0),
        parameter.get("NeckLength", 0.0),
    )
    parameter["Length"] = max(wz.laenge_fuer_cam(w), unten + MINDESTSCHAFT)
    return parameter


def drehrichtung(werkzeug):
    """SpindleDirection in CAM: rückwärts, wenn das Werkzeug links dreht (M4 – eingetragen oder
    der Linksgewindebohrer), keine beim Taster."""
    if werkzeug.art == wz.TASTER:
        return "None"
    return "Reverse" if wz.dreht_links(werkzeug) else "Forward"


def _rund(w):
    """Was fast jede Form hat: Schaft und Schneidenzahl."""
    parameter = {"ShankDiameter": wz.mass(w, "schaft")}
    if wz.hat_feld(w, "schneiden"):
        parameter["Flutes"] = w.schneiden
    return parameter


def _endmill(w):
    return {**_rund(w), "CuttingEdgeHeight": wz.mass(w, "schneidenlaenge")}


def _ballend(w):
    r = w.durchmesser / 2
    if w.art == wz.LOLLIPOPFRAESER:
        # So tief reicht die Kugel am Hals; CAM zeigt die Strecke so dick wie die Kugel.
        hoehe = r + wz.mass(w, "hals_laenge")
    else:
        hoehe = max(wz.mass(w, "schneidenlaenge"), r)
    return {**_rund(w), "CuttingEdgeHeight": hoehe}


def _bullnose(w):
    return {**_endmill(w), "CornerRadius": min(wz.mass(w, "eckradius"), w.durchmesser / 2)}


def _taperedballnose(w):
    # Der Kegel endet oben mit der Schneide: Dort hat er TaperDiameter. Der
    # Schaft ist mindestens so dick – wie im Bild.
    lc, winkel, oben = wf.konus(w)
    return {
        **_rund(w),
        "ShankDiameter": max(wz.mass(w, "schaft"), 2 * oben),
        "CuttingEdgeHeight": lc,
        "TaperAngle": 2 * winkel,
        "TaperDiameter": 2 * oben,
    }


def _dovetail(w):
    # CuttingEdgeAngle ist wie der Flankenwinkel zur Stirn gemessen; TipDiameter
    # nimmt CAMs Skizze nicht – er bleibt, wie er ist.
    return {
        **_rund(w),
        "CuttingEdgeHeight": wz.mass(w, "schneidenlaenge"),
        "CuttingEdgeAngle": wz.wert(w, "flankenwinkel"),
        "NeckDiameter": wz.mass(w, "hals_d"),
        "NeckHeight": wz.mass(w, "hals_laenge"),
    }


def _chamfer(w):
    # Im Wochen-Build rechnet CAM D aus Spitze, Winkel und Höhe – so kommt D heraus.
    spitze, hoehe, winkel = wf.kegel(w)
    return {
        **_rund(w),
        "CuttingEdgeAngle": winkel,
        "TipDiameter": spitze,
        "CuttingEdgeHeight": hoehe,
    }


def _radius(w):
    radius, spitze, hoehe = wf.radienprofil(w)
    return {
        **_rund(w),
        "CuttingRadius": radius,
        "TipDiameter": spitze,
        "CuttingEdgeHeight": max(wz.mass(w, "schneidenlaenge"), hoehe),
    }


def _slittingsaw(w):
    # Über der Scheibe sitzt der Hals – in CAM ist das der Schaft.
    hals = wz.mass(w, "hals_d")
    return {
        **_rund(w),
        "ShankDiameter": hals,
        "BladeThickness": wz.mass(w, "schneidenbreite"),
        "CapDiameter": hals,
        "CapHeight": WINZIG,
    }


def _threadmill(w):
    # CAM kennt einen Zahn unten, darüber den Hals bis zum Schaft. Die Spitze
    # des Zahns so breit wie der Grund des Innengewindes (P/8): Dann fräst
    # CAM auf den Nenndurchmesser.
    return {
        **_rund(w),
        "Crest": w.steigung / 8,
        "cuttingAngle": wz.wert(w, "flankenwinkel"),
        "NeckDiameter": wz.mass(w, "hals_d"),
        "NeckLength": wz.mass(w, "schneidenlaenge") + wz.mass(w, "hals_laenge"),
    }


def _drill(w):
    # Beim Zentrierbohrer ist D der Zapfen, und der hat die Spitze eines
    # Bohrers; die Senkung kennt CAM nicht.
    zapfen = w.art == wz.ZENTRIERBOHRER
    spitze = wz.SPITZENWINKEL_BOHRER if zapfen else wz.spitzenwinkel_fuer_cam(w)
    return {"Flutes": w.schneiden, "TipAngle": spitze}


def _tap(w):
    # Keine Schneidenzahl (Manuel): Flutes bleibt, wie CAM es vorgibt.
    schaft = wz.mass(w, "schaft")
    if abs(schaft - w.durchmesser) < WINZIG:
        schaft = w.durchmesser - WINZIG
    parameter = {
        "ShankDiameter": schaft,
        "CuttingEdgeLength": wz.mass(w, "schneidenlaenge"),
    }
    if w.steigung > 0:
        parameter["Pitch"] = w.steigung
    return parameter


def _reamer(w):
    # Die Reibahle hat in CAM keine Schneidenzahl.
    return {
        "ShankDiameter": wz.mass(w, "schaft"),
        "CuttingEdgeHeight": wz.mass(w, "schneidenlaenge"),
    }


def _probe(w):
    return {"ShaftDiameter": wz.mass(w, "schaft")}


_PARAMETER = {
    "endmill": _endmill,
    "ballend": _ballend,
    "bullnose": _bullnose,
    "taperedballnose": _taperedballnose,
    "dovetail": _dovetail,
    "chamfer": _chamfer,
    "radius": _radius,
    "slittingsaw": _slittingsaw,
    "thread-mill": _threadmill,
    "drill": _drill,
    "tap": _tap,
    "reamer": _reamer,
    "probe": _probe,
}


def _span(werkzeug, fz):
    """Was CAM als Chipload bekommt (mm je Zahn), oder None.

    CAM rechnet vf = n · Flutes · Chipload. Hat die Form in CAM keine
    Schneidenzahl (Reibahle), zählt CAM eine: dann f je Umdrehung. Beim
    Gewindebohrer keins – den Vorschub nimmt CAM aus der Steigung.
    """
    if not fz or wz.gewindebohrer(werkzeug.art):
        return None
    if "Flutes" in parameter_fuer_cam(werkzeug):
        return fz
    return round(fz * werkzeug.schneiden, 6)


def _presets(werkzeug, werkstoffe_nach_kennung, freecad_nach_nummer, bericht):
    """Je Einsatz ein Preset; „für alle Werkstoffe“ ohne Werkstoff-Hinweis."""
    presets = []
    # Wie „Schnittwerte in den Job“: Beim Bohren taucht das Werkzeug mit vollem Vorschub.
    if wz.bohrend(werkzeug.art):
        senkrecht = VORSCHUBVERHAELTNIS_BOHREN
    else:
        senkrecht = VORSCHUBVERHAELTNIS_EINTAUCHEN
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
                    "chipload": _span(werkzeug, einsatz.fz),
                    "vert_feed_ratio": senkrecht,
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
        kurz = f"T{werkzeug.nummer} {wz.art_text(werkzeug.art)}"
        if werkzeug.art not in FORMEN:
            bericht.ohne_form.append(kurz)
            continue
        if werkzeug.durchmesser <= 0:
            bericht.ohne_durchmesser += 1
            continue
        if werkzeug.art in NAEHERUNGEN:
            bericht.naeherungen.append((kurz, wz.art_text(NAEHERUNGEN[werkzeug.art])))
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
