# SPDX-License-Identifier: LGPL-2.1-or-later
"""Werkzeuge aus einer Werkzeugbibliothek von FreeCAD CAM übernehmen (W-002).

Die Gegenrichtung zu uebergabe_werkzeuge.py: Wer seine Fräser schon in
FreeCAD angelegt hat, soll sie nicht abtippen. Übernommen werden Art,
T-Nummer, Durchmesser, Schneiden, Schneidenlänge, Gesamtlänge, Schaft,
Eckradius, Schneidstoff und der Name als Bezeichnung – Schnittwerte hat eine
Bibliothek in FreeCAD 1.1.3 nicht. Formen, die die Werkzeugverwaltung nicht
kennt (Gravierstichel, Sägen, Gewindefräser, Taster …), bleiben draußen und
werden genannt.

Läuft ohne Oberfläche.
"""

from dataclasses import dataclass, field

from . import werkzeuge as wz
from .uebergabe_werkzeuge import BIBLIOTHEK_ID, PRAEFIX

# Form in FreeCAD (ShapeType, klein geschrieben) → Art in der Werkzeugverwaltung.
# Ein Gravierstichel (VBit) ist kein Fasenfräser: Die Werkzeugverwaltung
# kennt keinen Spitzenwinkel, zurück an CAM käme er mit 90° an.
ARTEN = {
    "endmill": wz.SCHAFTFRAESER,
    "bullnose": wz.TORUSFRAESER,
    "ballend": wz.RADIUSFRAESER,
    "chamfer": wz.FASENFRAESER,
    "drill": wz.BOHRER,
}
DURCHMESSER_TOLERANZ = 0.001  # mm – gleich, wenn so nah


@dataclass
class Bericht:
    """Was uebernehmen() getan hat – Namen, wie sie in FreeCAD heißen."""

    neu: list = field(default_factory=list)  # die übernommenen Werkzeuge
    schon_da: list = field(default_factory=list)  # gleiche Nummer, Art und Durchmesser
    neue_nummer: list = field(default_factory=list)  # (Name, Nummer in FreeCAD, neue Nummer)
    andere_form: list = field(default_factory=list)  # Formen, die es hier nicht gibt


def _assets():
    from Path.Tool import camassets

    # Wie CAMs eigene Bibliotheksfenster: Ein leerer Speicher bekommt zuerst
    # die mitgelieferte Bibliothek von FreeCAD.
    camassets.ensure_assets_initialized(camassets.cam_assets)
    return camassets.cam_assets


def bibliotheken():
    """Die Werkzeugbibliotheken von FreeCAD CAM, ohne „CAM-Addon“: [(Adresse, Name, Anzahl)]."""
    assets = _assets()
    ergebnis = []
    for adresse in assets.list_assets(asset_type="toolbitlibrary"):
        if adresse.asset_id == BIBLIOTHEK_ID:
            continue
        bibliothek = assets.get(adresse)
        ergebnis.append((str(adresse), str(bibliothek.label), len(bibliothek.get_bits())))
    return sorted(ergebnis, key=lambda eintrag: eintrag[1].lower())


def _mm(objekt, eigenschaft):
    wert = getattr(objekt, eigenschaft, None)
    try:
        return float(wert.getValueAs("mm"))
    except AttributeError:
        return _zahl(wert)


def _zahl(wert):
    try:
        return float(wert)
    except (TypeError, ValueError):
        return 0.0


def werkzeug_aus(bit, nummer):
    """Ein ToolBit als Werkzeug der Werkzeugverwaltung, oder None bei einer Form, die es hier nicht gibt."""
    o = bit.obj
    art = ARTEN.get(str(getattr(o, "ShapeType", "") or "").lower())
    if art is None:
        return None
    w = wz.Werkzeug(nummer=int(nummer), art=art)
    w.durchmesser = _mm(o, "Diameter")
    schneiden = int(_zahl(getattr(o, "Flutes", 0)))
    if schneiden >= 1:
        w.schneiden = schneiden
    elif art == wz.BOHRER:
        w.schneiden = 2
    w.schneidenlaenge = _mm(o, "CuttingEdgeHeight")
    w.gesamtlaenge = _mm(o, "Length")
    w.schaft = _mm(o, "ShankDiameter")
    if art == wz.TORUSFRAESER:
        w.eckradius = _mm(o, "CornerRadius")
    w.schneidstoff = wz.HSS if "hss" in str(getattr(o, "Material", "")).lower() else wz.VHM
    w.bezeichnung = str(bit.label)
    return w


def uebernehmen(bibliothek, adresse):
    """Übernimmt die Werkzeuge der FreeCAD-Bibliothek `adresse` in `bibliothek`; gibt den Bericht.

    Ein Werkzeug mit gleicher Nummer, Art und gleichem Durchmesser gibt es
    schon – es bleibt, wie es ist (mit seinen Schnittwerten). Ist nur die
    Nummer vergeben, bekommt das neue eine freie, die auch in der Quelle
    nicht vorkommt – sonst schöbe es die folgenden Werkzeuge mit. Gespeichert
    wird hier nichts – das macht der Dialog mit OK oder Übernehmen.
    """
    quelle = _assets().get(adresse)
    bits = sorted(quelle.get_bits(), key=lambda b: quelle.get_bit_no_from_bit(b) or 0)
    in_der_quelle = {quelle.get_bit_no_from_bit(b) for b in bits}
    bericht = Bericht()
    for bit in bits:
        name = str(bit.label)
        if str(bit.get_id()).startswith(PRAEFIX):
            bericht.schon_da.append(name)  # vom Addon selbst übergeben
            continue
        nummer = quelle.get_bit_no_from_bit(bit) or _freie_nummer(bibliothek, in_der_quelle)
        werkzeug = werkzeug_aus(bit, nummer)
        if werkzeug is None:
            bericht.andere_form.append(name)
            continue
        if _schon_da(bibliothek, werkzeug):
            bericht.schon_da.append(name)
            continue
        if bibliothek.mit_nummer(werkzeug.nummer) is not None:
            neue = _freie_nummer(bibliothek, in_der_quelle)
            bericht.neue_nummer.append((name, werkzeug.nummer, neue))
            werkzeug.nummer = neue
        bibliothek.werkzeuge.append(werkzeug)
        bericht.neu.append(werkzeug)
    return bericht


def _schon_da(bibliothek, werkzeug):
    """Gibt es das Werkzeug schon? Gleiche Art und gleicher Durchmesser – und gleiche
    Nummer oder, falls es beim letzten Mal umnummeriert wurde, gleicher Name."""
    for w in bibliothek.werkzeuge:
        gleich = w.art == werkzeug.art and (
            abs(w.durchmesser - werkzeug.durchmesser) < DURCHMESSER_TOLERANZ
        )
        if gleich and (w.nummer == werkzeug.nummer or w.bezeichnung == werkzeug.bezeichnung):
            return True
    return False


def _freie_nummer(bibliothek, auch_nicht):
    """Die kleinste T-Nummer, die weder in der Bibliothek noch in `auch_nicht` vorkommt."""
    belegt = {w.nummer for w in bibliothek.werkzeuge} | set(auch_nicht)
    nummer = 1
    while nummer in belegt:
        nummer += 1
    return nummer
