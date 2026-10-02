# SPDX-License-Identifier: LGPL-2.1-or-later
"""Werkzeuge aus einer Werkzeugbibliothek von FreeCAD CAM übernehmen (W-002).

Die Gegenrichtung zu uebergabe_werkzeuge.py: Wer seine Fräser schon in
FreeCAD angelegt hat, soll sie nicht abtippen. Übernommen werden Art,
T-Nummer, die Maße, die die Art hat (Durchmesser, Schneiden, Längen, Schaft,
Winkel, Hals, Steigung …), Schneidstoff und der Name – Schnittwerte hat eine
Bibliothek in FreeCAD 1.1.3 nicht. Jede Form in CAM hat ihre Art
(Spezifikation Werkzeugarten, Abschnitt 6); nur eigene Formen („Custom“)
bleiben draußen und werden genannt.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field

from . import werkzeuge as wz
from .uebergabe_werkzeuge import BIBLIOTHEK_ID, PRAEFIX

# Form in FreeCAD (ShapeType, klein geschrieben) → Art in der Werkzeugverwaltung.
# Ein Gravierstichel (VBit) ist ein spitzer Fasenfräser; der Gewindebohrer ist
# links, wenn CAM ihn rückwärts drehen lässt.
ARTEN = {
    "endmill": wz.SCHAFTFRAESER,
    "ballend": wz.KUGELFRAESER,
    "bullnose": wz.TORUSFRAESER,
    "taperedballnose": wz.KONIKFRAESER,
    "dovetail": wz.SCHWALBENSCHWANZFRAESER,
    "chamfer": wz.FASENFRAESER,
    "vbit": wz.FASENFRAESER,
    "radius": wz.RADIENFRAESER,
    "slittingsaw": wz.NUTENFRAESER,
    "threadmill": wz.GEWINDEFRAESER,
    "drill": wz.BOHRER,
    "tap": wz.GEWINDEBOHRER_RECHTS,
    "reamer": wz.REIBAHLE,
    "probe": wz.TASTER,
}
DURCHMESSER_TOLERANZ = 0.001  # mm – gleich, wenn so nah


@dataclass
class Bericht:
    """Was uebernehmen() getan hat – Namen, wie sie in FreeCAD heißen."""

    neu: list = field(default_factory=list)  # die übernommenen Werkzeuge
    schon_da: list = field(default_factory=list)  # gleiche Nummer, Art und Durchmesser
    neue_nummer: list = field(default_factory=list)  # (Name, Nummer in FreeCAD, neue Nummer)
    andere_form: list = field(default_factory=list)  # Formen, die es hier nicht gibt
    unlesbar: list = field(default_factory=list)  # Fehler beim Lesen – steht im Bericht-Fenster


def _assets():
    from Path.Tool import camassets

    # Wie CAMs eigene Bibliotheksfenster: Ein leerer Speicher bekommt zuerst
    # die mitgelieferte Bibliothek von FreeCAD.
    camassets.ensure_assets_initialized(camassets.cam_assets)
    return camassets.cam_assets


def bibliotheken():
    """Die Werkzeugbibliotheken von FreeCAD CAM, ohne „CAM-Addon“: [(Adresse, Name, Anzahl)].

    Eine Bibliothek, die sich nicht lesen lässt, fehlt in der Liste und
    steht im Bericht-Fenster von FreeCAD – die übrigen bleiben wählbar.
    """
    import FreeCAD

    assets = _assets()
    ergebnis = []
    for adresse in assets.list_assets(asset_type="toolbitlibrary"):
        if adresse.asset_id == BIBLIOTHEK_ID:
            continue
        try:
            bibliothek = assets.get(adresse)
            ergebnis.append((str(adresse), str(bibliothek.label), len(bibliothek.get_bits())))
        except Exception as fehler:  # eine kaputte Datei soll die anderen nicht verstecken
            FreeCAD.Console.PrintWarning(f"CAM-Addon: Bibliothek {adresse}: {fehler}\n")
    return sorted(ergebnis, key=lambda eintrag: eintrag[1].lower())


STELLEN = 4  # Maße auf 0,0001 mm – FreeCAD rechnet manche aus (Fasenfräser: 10.260512242…)


def _mm(objekt, eigenschaft):
    wert = getattr(objekt, eigenschaft, None)
    try:
        return round(float(wert.getValueAs("mm")), STELLEN)
    except AttributeError:
        return round(_zahl(wert), STELLEN)


def _grad(objekt, name):
    """Ein Winkel des ToolBits in Grad, 0 wenn es ihn nicht gibt."""
    wert = getattr(objekt, name, 0)
    try:
        return round(float(wert.getValueAs("deg")), STELLEN)
    except AttributeError:
        return round(_zahl(wert), STELLEN)


def _zahl(wert):
    try:
        return float(wert)
    except (TypeError, ValueError):
        return 0.0


def werkzeug_aus(bit, nummer):
    """Ein ToolBit als Werkzeug der Werkzeugverwaltung, oder None bei einer Form, die es hier nicht gibt.

    Gesetzt wird nur, was die Art als Feld hat. Hat CAM keine Schneidenzahl
    (Reibahle, Bohrer ohne Angabe), gilt die der Beispiele der Art.
    """
    o = bit.obj
    art = ARTEN.get(str(getattr(o, "ShapeType", "") or "").lower())
    if art is None:
        return None
    rueckwaerts = str(getattr(o, "SpindleDirection", "")) == "Reverse"
    if art == wz.GEWINDEBOHRER_RECHTS and rueckwaerts:
        art = wz.GEWINDEBOHRER_LINKS
    werte = {
        "durchmesser": _mm(o, "Diameter"),
        "schneidenlaenge": _mm(o, "CuttingEdgeHeight") or _mm(o, "CuttingEdgeLength"),
        "gesamtlaenge": _mm(o, "Length"),
        "schaft": _mm(o, "ShankDiameter") or _mm(o, "ShaftDiameter"),
        "eckradius": _mm(o, "CornerRadius"),
        "spitzenwinkel": _grad(o, "TipAngle") or _grad(o, "CuttingEdgeAngle"),
        "kegelwinkel": round(_grad(o, "TaperAngle") / 2, STELLEN),
        "flankenwinkel": _grad(o, "CuttingEdgeAngle") or _grad(o, "cuttingAngle"),
        "spitzen_d": _mm(o, "TipDiameter"),
        "hals_d": _mm(o, "NeckDiameter"),
        "profilradius": _mm(o, "CuttingRadius"),
        "schneidenbreite": _mm(o, "BladeThickness"),
        "steigung": _mm(o, "Pitch"),
    }
    if art == wz.NUTENFRAESER:
        # Über der Scheibe hat CAM nur den Schaft – er ist auch der Hals.
        werte["hals_d"] = werte["schaft"]
    if art == wz.GEWINDEFRAESER:
        werte.update(_gewindefraeser(o, werte))
    w = wz.Werkzeug(nummer=int(nummer), art=art)
    for feld, wert in werte.items():
        if wz.hat_feld(w, feld):
            setattr(w, feld, wert)
    if wz.hat_feld(w, "schneiden"):
        schneiden = int(_zahl(getattr(o, "Flutes", 0)))
        w.schneiden = schneiden if schneiden >= 1 else wz.ARTDATEN[art].beispiel["schneiden"]
    if wz.hat_feld(w, "schneidstoff"):
        w.schneidstoff = wz.HSS if "hss" in str(getattr(o, "Material", "")).lower() else wz.VHM
    if wz.hat_feld(w, wz.DREHRICHTUNG) and rueckwaerts and art != wz.GEWINDEBOHRER_LINKS:
        w.drehrichtung = wz.LINKS
    w.name = str(bit.label)
    return w


class _Bit:
    """Das ToolBit eines Werkzeug-Controllers, wie werkzeug_aus() es liest: Objekt und Name."""

    def __init__(self, objekt):
        self.obj = objekt
        self.label = objekt.Label


def vom_controller(tc):
    """Das Werkzeug eines Werkzeug-Controllers, gelesen aus seinem ToolBit im Dokument (Form,
    Durchmesser, Eckradius …) – so, wie CAM damit fräst. None ohne ToolBit oder bei einer Form,
    die es hier nicht gibt."""
    bit = getattr(tc, "Tool", None)
    if bit is None:
        return None
    return werkzeug_aus(_Bit(bit), getattr(tc, "ToolNumber", 1))


def _gewindefraeser(o, werte):
    """Schneidenlänge und Hals des Gewindefräsers: In CAM hat er einen Zahn
    unten, darüber den Hals bis zum Schaft (NeckLength ab der Spitze)."""
    d, hals = werte["durchmesser"], werte["hals_d"]
    winkel = werte["flankenwinkel"] or 60.0
    zahn = max(d - hals, 0.0) * math.tan(math.radians(winkel / 2)) + _mm(o, "Crest")
    zahn = round(zahn, STELLEN)
    hals_laenge = round(max(_mm(o, "NeckLength") - zahn, 0.0), STELLEN)
    return {"schneidenlaenge": zahn, "hals_laenge": hals_laenge}


def uebernehmen(bibliothek, adresse):
    """Übernimmt die Werkzeuge der FreeCAD-Bibliothek `adresse` in `bibliothek`; gibt den Bericht.

    Ein Werkzeug mit gleicher Nummer, Art und gleichem Durchmesser gibt es
    schon – es bleibt, wie es ist (mit seinen Schnittwerten). Ist nur die
    Nummer vergeben, bekommt das neue eine freie, die auch in der Quelle
    nicht vorkommt – sonst schöbe es die folgenden Werkzeuge mit. Ein
    Werkzeug, das sich nicht lesen lässt, steht im Bericht; die anderen
    kommen trotzdem. Gespeichert wird hier nichts – das macht der Dialog mit
    OK oder Übernehmen.
    """
    import FreeCAD

    quelle = _assets().get(adresse)
    bits = sorted(quelle.get_bits(), key=lambda b: quelle.get_bit_no_from_bit(b) or 0)
    in_der_quelle = {quelle.get_bit_no_from_bit(b) for b in bits}
    bericht = Bericht()
    for bit in bits:
        name = str(bit.label)
        try:
            _uebernehme_eines(bibliothek, bit, name, quelle, in_der_quelle, bericht)
        except Exception as fehler:  # ein kaputtes Werkzeug soll die anderen nicht aufhalten
            FreeCAD.Console.PrintWarning(f"CAM-Addon: Werkzeug {name}: {fehler}\n")
            bericht.unlesbar.append(name)
    return bericht


def _uebernehme_eines(bibliothek, bit, name, quelle, in_der_quelle, bericht):
    """Ein Werkzeug der Quelle: übernehmen oder im Bericht sagen, warum nicht."""
    if str(bit.get_id()).startswith(PRAEFIX):
        bericht.schon_da.append(name)  # vom Addon selbst übergeben
        return
    nummer = quelle.get_bit_no_from_bit(bit) or _freie_nummer(bibliothek, in_der_quelle)
    werkzeug = werkzeug_aus(bit, nummer)
    if werkzeug is None:
        bericht.andere_form.append(name)
        return
    if _schon_da(bibliothek, werkzeug):
        bericht.schon_da.append(name)
        return
    if bibliothek.mit_nummer(werkzeug.nummer) is not None:
        neue = _freie_nummer(bibliothek, in_der_quelle)
        bericht.neue_nummer.append((name, werkzeug.nummer, neue))
        werkzeug.nummer = neue
    bibliothek.werkzeuge.append(werkzeug)
    bericht.neu.append(werkzeug)


def _schon_da(bibliothek, werkzeug):
    """Gibt es das Werkzeug schon? Gleiche Art und gleicher Durchmesser – und gleiche
    Nummer oder, falls es beim letzten Mal umnummeriert wurde, gleicher Name (vor
    P-2026-09-26-33 stand der Name aus CAM in der Bezeichnung)."""
    for w in bibliothek.werkzeuge:
        gleich = w.art == werkzeug.art and (
            abs(w.durchmesser - werkzeug.durchmesser) < DURCHMESSER_TOLERANZ
        )
        if gleich and (w.nummer == werkzeug.nummer or werkzeug.name in (w.name, w.bezeichnung)):
            return True
    return False


def _freie_nummer(bibliothek, auch_nicht):
    """Die kleinste T-Nummer, die weder in der Bibliothek noch in `auch_nicht` vorkommt."""
    belegt = {w.nummer for w in bibliothek.werkzeuge} | set(auch_nicht)
    nummer = 1
    while nummer in belegt:
        nummer += 1
    return nummer
