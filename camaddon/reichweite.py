# SPDX-License-Identifier: LGPL-2.1-or-later
"""Reicht der Verfahrweg? Die Bahn eines CAM-Jobs auf der Maschine (W-001, Stufe 4a).

Für jeden Punkt der Bahn die Stellungen der Achsen, bei denen die
Werkzeugspitze gegenüber dem Werkstück auf dem Punkt steht – gehalten gegen
die Grenzen der Gelenke (spezifikation_simulation.md, Abschnitte 3 und 4):

1. Die Drehachsen stehen, wie die Bahn sagt: A, B und C über ihren Namen im
   Programm (C1 → C), ohne Angabe auf 0. Am Revolver steht der Platz des
   Werkzeugs in Arbeitsstellung; Spindeln bleiben, wie sie stehen.
2. Dann hängt der Abstand zwischen Spitze und Punkt linear an den Wegen der
   Linearachsen. Einmal gelöst, gilt für alle Punkte mit derselben Stellung
   der Drehachsen:  Stellungen = s0 + S · Punkt.

Gerechnet wird wie in verfahren.py – die Lage eines Glieds ist das Produkt
der Achsbewegungen vom Bett nach außen –, aber ohne Bauteile zu bewegen. Die
schräge Achse braucht nichts Eigenes: Die Lösung rechnet mit den echten
Richtungen der Schlitten und liefert deshalb gleich ihre Stellungen.

Koordinaten:
- Der Job: Die Bahn ist `op.Path`, so, wie der Postprozessor sie liest (ohne
  die Lage der Operation). Ihr Koordinatensystem ist das LCS der
  Werkstückaufnahme, verschoben um den Nullpunkt des Jobs.
- Das Werkzeug: Die Spitze liegt um die Werkzeuglänge gegen die Z-Achse der
  Werkzeugaufnahme versetzt – deren Z zeigt von der Spitze zur Aufnahme.

Läuft ohne Oberfläche.
"""

import json
import math
from dataclasses import dataclass, field

import FreeCAD

from . import PARAMETER_PFAD, einheiten, maschinenspeicher
from . import bestueckung as bs
from . import halter as hl
from . import job_schnittwerte as js
from . import maschine as m
from . import verfahren as vf
from . import vierachs_rohteil as vr
from . import werkzeuge as wz
from .kette import LINEAR
from .sprache import tr
from .werkstoffe import mit_dezimalzeichen

# Weiter als so (mm) darf die Spitze nicht neben dem Punkt stehen – sonst
# kommen die Linearachsen nicht dorthin (Drehmaschine ohne Y).
UNERREICHBAR_AB = 0.001
# So fein (Grad) wird ein Satz geteilt, in dem sich eine Rundachse dreht.
DREH_SCHRITT = 1.0
RUNDACHSEN = ("A", "B", "C")
# So weit (Kosinus) darf die Werkzeugaufnahme von Z des Jobs abweichen, sonst steht sie quer –
# etwa 25°: ein schräg angestellter Kopf zählt noch, ein radialer Platz nicht.
QUER = 0.9
BOHRZYKLEN = {"G73", "G74", "G76", "G81", "G82", "G83", "G84", "G85", "G86", "G87", "G88", "G89"}
# Befehle ohne Bewegung – Ebene, Maßsystem, Korrekturen, Nullpunkte, Modi: Die Prüfung
# übergeht sie ohne Hinweis.
OHNE_BEWEGUNG = {
    f"G{n}"
    for n in (4, 17, 18, 19, 20, 21, 40, 41, 42, 43, 49, 53, 61, 64, 80, 90, 91, 93, 94, 98, 99)
} | {f"G{n}" for n in (54, 55, 56, 57, 58, 59, "59.1", "59.2", "59.3")}
# Kreisebenen: (erste Achse, zweite Achse, Normale) – G2 dreht von der ersten
# zur zweiten Achse im Uhrzeigersinn, von der Normalen aus gesehen.
EBENEN = {"G17": ("X", "Y", "Z"), "G18": ("Z", "X", "Y"), "G19": ("Y", "Z", "X")}
MITTE = {"X": "I", "Y": "J", "Z": "K"}  # Mittelpunkt eines Kreises, ab seinem Start

# Woher die Länge eines Werkzeugs kommt.
LAENGE_SPINDELNASE = "spindelnase"  # eingetragen: ab Spindelnase, mit Halter
LAENGE_HALTER = "halter"  # geschätzt: Halterlänge + Gesamtlänge − Spanntiefe
LAENGE_VORSCHLAG = "vorschlag"  # im vorgeschlagenen Halter: Halterlänge + Auskragung + 5
LAENGE_GESAMT = "gesamt"  # Gesamtlänge aus der Werkzeugverwaltung, ohne Halter
LAENGE_GESCHAETZT = "geschaetzt"  # keine Gesamtlänge eingetragen: geschätzt wie für CAM
LAENGE_CAM = "cam"  # Länge des CAM-Werkzeugs, ohne Halter

# Wo der Job den eingetragenen Nullpunkt aufbewahrt (JSON: {"X": …, "Z": …}).
EIGENSCHAFT_NULLPUNKT = "CamAddonNullpunkt"
# Die Datei der Maschine, auf der zuletzt geprüft wurde: am Job und – für alle Jobs – in den
# Einstellungen (Durchsicht W-004, D-20).
EIGENSCHAFT_MASCHINE = "CamAddonMaschine"
ZULETZT_MASCHINE = "ZuletztMaschine"


# --- Ergebnis ------------------------------------------------------------------------


@dataclass
class Ueberschreitung:
    """Eine Achse fährt in einer Operation über eine Grenze – der weiteste Punkt."""

    achse: object  # kette.Achse
    name: str  # wie die Achse im Fenster heißt: „X1“, „C1“
    operation: str  # Beschriftung der Operation
    stellung: float  # so weit müsste die Achse
    grenze: float  # die Grenze, über die sie müsste
    punkt: dict  # der Punkt im Programm: {"X": …, "Y": …, "Z": …}, dazu A/B/C ≠ 0
    stellungen: dict  # Achse -> Stellung: so stünde die Maschine an dieser Stelle
    # Wo die Spitze an der Grenze stünde, im Programm wie `punkt` – bei Linearachsen (4e);
    # dazu das Werkzeug („T1“).
    an_grenze: dict = None
    werkzeug: str = ""
    durchmesser: bool = False  # die Achse zählt im Durchmesser (X einer Drehmaschine)
    x_durchmesser: bool = False  # X im Programm als Durchmesser

    def text(self):
        """„X1 fährt in „Tasche“ bis 312,00 mm, die Grenze ist 250,00 mm (bei X 450, Y 0, Z −5).
        An der Grenze stünde die Spitze von T1 bei X 388, Y 0, Z −5.“ – so ist klar, dass X1
        der Schlitten ist und wie weit das Werkzeug reicht (Manuel, 2026-09-29)."""
        text = tr(
            "rw.ueberschreitung",
            achse=self.name,
            operation=self.operation,
            stellung=stellung_text(self.achse, self.stellung, self.durchmesser),
            grenze=stellung_text(self.achse, self.grenze, self.durchmesser),
            punkt=punkt_text(self.punkt, self.x_durchmesser),
        )
        if self.an_grenze is not None:
            text += " " + tr(
                "rw.ueberschreitung.spitze",
                werkzeug=self.werkzeug,
                punkt=punkt_text(self.an_grenze, self.x_durchmesser),
            )
        return text


@dataclass
class Bereich:
    """Was eine Achse für die Bahn braucht – und was ihre Grenzen erlauben."""

    achse: object
    name: str
    von: float
    bis: float
    durchmesser: bool = False  # die Achse zählt im Durchmesser (X einer Drehmaschine)

    def text(self):
        """„X1 braucht −120,00 mm … 140,00 mm, die Grenzen sind −170,00 mm … 150,00 mm.“"""
        d = self.durchmesser
        return tr(
            "rw.bereich",
            achse=self.name,
            von=stellung_text(self.achse, self.von, d),
            bis=stellung_text(self.achse, self.bis, d),
            minimum=_grenze_text(self.achse, self.achse.minimum, d),
            maximum=_grenze_text(self.achse, self.achse.maximum, d),
        )


class Hinweis(str):
    """Ein Hinweis-Satz. `werkzeug`: die Nummer des Werkzeugs, um das es geht – das Fenster
    verweist dann auf die Werkzeugverwaltung (Durchsicht W-004, D-11)."""

    werkzeug = None

    def __new__(cls, text, werkzeug=None):
        satz = super().__new__(cls, text)
        satz.werkzeug = werkzeug
        return satz


@dataclass
class Ergebnis:
    """Was prüfe_job() gefunden hat."""

    ueberschreitungen: list = field(default_factory=list)
    bereiche: list = field(default_factory=list)  # je Achse, in der Reihenfolge der Kette
    hinweise: list = field(default_factory=list)  # fertige Sätze
    punkte: int = 0  # so viele Punkte wurden geprüft
    laengen: dict = field(default_factory=dict)  # Werkzeugnummer -> womit gerechnet (LAENGE_…)

    def in_grenzen(self):
        return not self.ueberschreitungen

    def geschaetzte_laengen(self):
        """Die Werkzeugnummern, deren Länge nicht gemessen ist – alles außer „Länge ab
        Spindelnase“ –, in der Reihenfolge der Operationen."""
        return [nummer for nummer, quelle in self.laengen.items() if quelle != LAENGE_SPINDELNASE]


# --- Texte (ohne Oberfläche) -----------------------------------------------------------


def _zahl(wert, stellen, kuerzen=False):
    """Eine Zahl mit dem gewählten Dezimalzeichen und echtem Minus; `kuerzen` lässt
    Nullen am Ende weg („450“ statt „450,00“)."""
    # + 0.0 macht aus −0,00 eine 0,00.
    text = f"{round(wert, stellen) + 0.0:.{stellen}f}"
    if kuerzen and "." in text:
        text = text.rstrip("0").rstrip(".")
    zeichen = einheiten.gewaehltes_dezimalzeichen() or einheiten.PUNKT
    return mit_dezimalzeichen(text, zeichen).replace("-", "−")


def weg_text(mm):
    """Ein Weg zum Lesen: „−5,77 mm“ bzw. in inch."""
    stellen = einheiten.stellen(einheiten.LAENGE, 2)
    zahl = _zahl(einheiten.anzeige(mm, einheiten.LAENGE), stellen)
    return f"{zahl} {einheiten.einheit(einheiten.LAENGE)}"


def winkel_text(grad):
    """Ein Winkel zum Lesen: „90,0°“."""
    return _zahl(grad, 1) + "°"


def stellung_text(achse, wert, durchmesser=False):
    """Die Stellung einer Achse zum Lesen – mm (inch) oder Grad. `durchmesser`: Die Achse
    zählt im Durchmesser, wie X an einer Drehmaschine – dann „Ø 550,00 mm“, so wie die
    Steuerung es zeigt (Manuel, 2026-09-30); gerechnet wird immer im Radius."""
    if achse.art != LINEAR:
        return winkel_text(wert)
    if durchmesser:
        return einheiten.DURCHMESSER + weg_text(2.0 * wert)
    return weg_text(wert)


def _grenze_text(achse, grenze, durchmesser=False):
    return tr("rw.keine_grenze") if grenze is None else stellung_text(achse, grenze, durchmesser)


def punkt_text(punkt, x_durchmesser=False):
    """Ein Punkt im Programm: „X 450, Y 0, Z −5“ – Rundachsen nur, wenn sie nicht 0 sind.
    `x_durchmesser`: X steht im Programm als Durchmesser („X Ø 900“)."""
    stellen = einheiten.stellen(einheiten.LAENGE, 2)

    def laenge(buchstabe):
        wert = punkt[buchstabe]
        if buchstabe == "X" and x_durchmesser:
            return einheiten.DURCHMESSER + _zahl(
                einheiten.anzeige(2.0 * wert, einheiten.LAENGE), stellen, True
            )
        return _zahl(einheiten.anzeige(wert, einheiten.LAENGE), stellen, True)

    teile = [f"{buchstabe} {laenge(buchstabe)}" for buchstabe in ("X", "Y", "Z")]
    teile += [
        f"{buchstabe} {_zahl(punkt[buchstabe], 3, True)}"
        for buchstabe in RUNDACHSEN
        if punkt.get(buchstabe)
    ]
    return ", ".join(teile)


# --- Nullpunkt des Jobs ------------------------------------------------------------------


def vorschlag_nullpunkt(job):
    """Wo der Nullpunkt des Jobs von der Werkstückaufnahme aus liegt, wenn nichts
    eingetragen ist: das Rohteil mittig auf der Aufnahme, die Unterseite auf der
    Spannfläche. Eine runde Stange längs Z sitzt genau auf ihrer Achse und steckt mit
    ihrer Spannlänge im Futter (4-Achs-Bearbeitung an der Drehmaschine, W-003 V2c).
    Ohne Rohteil der Ursprung."""
    rohteil = getattr(job, "Stock", None)
    form = getattr(rohteil, "Shape", None)
    if form is None or form.isNull():
        return FreeCAD.Vector()
    stange = _stange_laengs_z(rohteil)
    if stange is not None:
        return FreeCAD.Vector(-stange.x, -stange.y, -(stange.z + vr.spannlaenge(job)))
    box = form.BoundBox
    return FreeCAD.Vector(-box.Center.x, -box.Center.y, -box.ZMin)


def _stange_laengs_z(rohteil):
    """Die Mitte des hinteren Endes, wenn das Rohteil ein Zylinder längs +Z ist – sonst
    None. Die Hüllbox eines Zylinders ist nicht genau: Sie lag in einem Versuch 0,043 mm
    neben der Achse."""
    if not hasattr(rohteil, "Radius") or not hasattr(rohteil, "Height"):
        return None
    platz = rohteil.Placement
    if abs(platz.Rotation.multVec(FreeCAD.Vector(0, 0, 1)).z - 1.0) > 1e-9:
        return None
    return FreeCAD.Vector(platz.Base)


def eingetragener_nullpunkt(job):
    """Die am Job eingetragenen Werte: {"X": …, "Y": …, "Z": …} – fehlende gelten mit dem Vorschlag."""
    text = getattr(job, EIGENSCHAFT_NULLPUNKT, "") or ""
    try:
        werte = json.loads(text) if text else {}
    except ValueError:
        return {}
    return {k: float(v) for k, v in werte.items() if k in ("X", "Y", "Z")}


def nullpunkt(job):
    """Der Nullpunkt des Jobs von der Werkstückaufnahme aus: eingetragen, sonst der Vorschlag."""
    vorschlag = vorschlag_nullpunkt(job)
    werte = eingetragener_nullpunkt(job)
    return FreeCAD.Vector(
        werte.get("X", vorschlag.x), werte.get("Y", vorschlag.y), werte.get("Z", vorschlag.z)
    )


def setze_nullpunkt(job, werte):
    """Trägt den Nullpunkt am Job ein; `werte` wie bei eingetragener_nullpunkt(), {} löscht."""
    if EIGENSCHAFT_NULLPUNKT not in job.PropertiesList:
        if not werte:
            return
        job.addProperty(
            "App::PropertyString", EIGENSCHAFT_NULLPUNKT, "CAM-Addon", tr("rw.eigenschaft")
        )
        job.setEditorMode(EIGENSCHAFT_NULLPUNKT, 2)  # ausgeblendet – das Fenster zeigt ihn
    setattr(job, EIGENSCHAFT_NULLPUNKT, json.dumps(werte, sort_keys=True) if werte else "")


def gemerkte_maschine(job=None):
    """Die Maschinendatei, auf der zuletzt geprüft wurde: die des Jobs, sonst überhaupt die
    zuletzt benutzte; "" ohne."""
    pfad = getattr(job, EIGENSCHAFT_MASCHINE, "") if job is not None else ""
    return pfad or FreeCAD.ParamGet(PARAMETER_PFAD).GetString(ZULETZT_MASCHINE, "")


def merke_maschine(job, pfad):
    """Merkt die Maschinendatei am Job und als zuletzt benutzte – und nimmt sie in die Liste
    der Maschinen (maschinenspeicher, W-011). Ein leerer Pfad – die Maschine ist nie
    gespeichert worden – ändert nichts."""
    if not pfad:
        return
    try:
        maschinenspeicher.merken_datei(pfad)
    except Exception as fehler:  # die Liste ist ein Zusatz – das Prüfen geht vor
        FreeCAD.Console.PrintWarning(f"CAM-Addon: Maschinen-Liste: {fehler}\n")
    FreeCAD.ParamGet(PARAMETER_PFAD).SetString(ZULETZT_MASCHINE, pfad)
    if getattr(job, EIGENSCHAFT_MASCHINE, "") == pfad:
        return
    if EIGENSCHAFT_MASCHINE not in job.PropertiesList:
        job.addProperty(
            "App::PropertyString", EIGENSCHAFT_MASCHINE, "CAM-Addon", tr("rw.eigenschaft.maschine")
        )
        job.setEditorMode(EIGENSCHAFT_MASCHINE, 2)  # ausgeblendet – das Addon nutzt sie
    setattr(job, EIGENSCHAFT_MASCHINE, pfad)


# --- Werkzeuglänge -------------------------------------------------------------------------


def werkzeuglaenge(tc, bibliothek):
    """(Länge in mm, Quelle): von der Werkzeugaufnahme bis zur Spitze.

    Aus der Werkzeugverwaltung, wenn das Werkzeug dort steht (wie „Schnittwerte
    in den Job“: über die Kennung, sonst Nummer und Durchmesser): die Länge ab
    Spindelnase, mit Halter – sonst mit seinem Halter geschätzt (Halterlänge +
    Gesamtlänge − Spanntiefe), ohne Halter die Gesamtlänge; fehlt auch sie,
    geschätzt wie für CAM. Sonst die Länge des CAM-Werkzeugs.
    """
    werkzeug = js.werkzeug_von(tc, bibliothek) if bibliothek is not None else None
    if werkzeug is not None:
        if werkzeug.laenge_spindelnase:
            return werkzeug.laenge_spindelnase, LAENGE_SPINDELNASE
        halter = bibliothek.halter_fuer_pruefung(werkzeug)
        if hl.ist_vorschlag(halter):
            return wz.laenge_mit_vorschlag(werkzeug, halter), LAENGE_VORSCHLAG
        if halter is not None:
            return wz.laenge_mit_halter(werkzeug, halter), LAENGE_HALTER
        if werkzeug.gesamtlaenge:
            return werkzeug.gesamtlaenge, LAENGE_GESAMT
        return wz.geschaetzte_laenge(werkzeug), LAENGE_GESCHAETZT
    laenge = getattr(getattr(tc, "Tool", None), "Length", None)
    try:
        return float(laenge.getValueAs("mm")), LAENGE_CAM
    except AttributeError:
        return float(laenge or 0.0), LAENGE_CAM


@dataclass
class Einspannung:
    """Wie das Werkzeug in seiner Aufnahme sitzt (W-002 Stufe E): die Länge vom Bezugspunkt
    bis zur Spitze und die Lage des Bezugspunkts im LCS der Aufnahme (halter.lage) – None
    beim geraden Halter: dann ist es die Spindelnase, und das Werkzeug zeigt längs −Z."""

    laenge: float
    lage: object = None  # FreeCAD.Placement oder None

    def spitze(self):
        """Die Spitze im LCS der Aufnahme."""
        versatz = FreeCAD.Vector(0, 0, -self.laenge)
        return self.lage.multVec(versatz) if self.lage is not None else versatz

    def achse(self):
        """Z des Werkzeugs – von der Spitze weg – im LCS der Aufnahme."""
        z = FreeCAD.Vector(0, 0, 1)
        return self.lage.Rotation.multVec(z) if self.lage is not None else z


def einspannung(tc, bibliothek):
    """Die Einspannung des Werkzeugs eines Controllers: seine Länge (werkzeuglaenge) und die
    Lage aus seinem Halter in der Werkzeugverwaltung."""
    halter = werkzeughalter(tc, bibliothek)
    lage = hl.lage(halter) if halter is not None and halter.gewinkelt else None
    return Einspannung(werkzeuglaenge(tc, bibliothek)[0], lage)


def _einspannung(laenge):
    """Eine Zahl ist die Länge eines gerade eingespannten Werkzeugs."""
    return laenge if isinstance(laenge, Einspannung) else Einspannung(float(laenge))


@dataclass
class Werkzeugmasse:
    """Die Maße eines Werkzeugs für Abfahren und Kollision, in mm."""

    durchmesser: float
    schneide: float  # von der Spitze bis zum Hals (werkzeuge.schneide)
    hals_d: float  # 0: kein Hals
    hals_laenge: float
    schaft: float  # Schaft-Ø
    gesamt: float  # Gesamtlänge
    kugel: bool = False  # Lollipop: die Schneide ist eine Kugel mit D, der Hals sitzt in der Mitte
    stirn: object = None  # die Form der Stirn (fraeserform.Form); None: eben


def werkzeugmasse(tc, bibliothek, laenge):
    """Die Maße des Werkzeugs eines Controllers: aus der Werkzeugverwaltung (eingetragen,
    sonst geschätzt wie für CAM), sonst vom CAM-Werkzeug; `laenge` gilt, wo nichts steht."""
    from . import fraeserform as ff

    w = js.werkzeug_von(tc, bibliothek) if bibliothek is not None else None
    if w is not None and w.durchmesser:
        return Werkzeugmasse(
            durchmesser=w.durchmesser,
            schneide=wz.schneide(w) or 2 * w.durchmesser,
            hals_d=wz.mass(w, "hals_d") if wz.mass(w, "hals_laenge") else 0.0,
            hals_laenge=wz.mass(w, "hals_laenge") if wz.mass(w, "hals_d") else 0.0,
            schaft=wz.schaft_fuer_cam(w),
            gesamt=wz.laenge_fuer_cam(w),
            kugel=w.art == wz.LOLLIPOPFRAESER,
            stirn=ff.von_werkzeug(w),
        )
    bit = getattr(tc, "Tool", None)
    durchmesser = _mm(getattr(bit, "Diameter", None)) or 5.0
    schneide = (
        _mm(getattr(bit, "CuttingEdgeHeight", None))
        or _mm(getattr(bit, "CuttingEdgeLength", None))  # Gewindebohrer
        or _mm(getattr(bit, "BladeThickness", None))  # Scheibenfräser
    )
    return Werkzeugmasse(
        durchmesser=durchmesser,
        schneide=schneide or 2 * durchmesser,
        hals_d=0.0,
        hals_laenge=0.0,
        schaft=_mm(getattr(bit, "ShankDiameter", None)) or durchmesser,
        gesamt=_mm(getattr(bit, "Length", None)) or laenge,
        stirn=_stirn_vom_bit(tc),
    )


def _stirn_vom_bit(tc):
    """Die Form der Stirn aus dem ToolBit eines Controllers (fraeserform), oder None."""
    from . import fraeserform as ff
    from .werkzeuge_aus_cam import vom_controller

    try:
        werkzeug = vom_controller(tc)
    except AttributeError:  # kein ToolBit, wie CAM es anlegt
        return None
    return ff.von_werkzeug(werkzeug) if werkzeug is not None else None


def werkzeughalter(tc, bibliothek):
    """Der Halter des Werkzeugs aus der Werkzeugverwaltung (halter.Halter) – ohne gewählten der
    vorgeschlagene (Bibliothek.halter_fuer_pruefung) –, oder None."""
    if bibliothek is None:
        return None
    werkzeug = js.werkzeug_von(tc, bibliothek)
    return bibliothek.halter_fuer_pruefung(werkzeug) if werkzeug is not None else None


def _mm(wert):
    """Eine Länge vom CAM-Werkzeug in mm: Quantity, Zahl oder nichts (0)."""
    try:
        return float(wert.getValueAs("mm"))
    except AttributeError:
        return float(wert or 0.0)


def werkzeug_kurz(werkzeug):
    """„Schaftfräser Ø 12 (T3)“ – ein Werkzeug der Werkzeugverwaltung in Sätzen; ohne Nummer
    ohne Klammer. Mit dem gewählten Dezimalzeichen."""
    zeichen = einheiten.gewaehltes_dezimalzeichen() or einheiten.PUNKT
    text = mit_dezimalzeichen(wz.kurz(werkzeug), zeichen)
    return f"{text} (T{werkzeug.nummer})" if werkzeug.nummer else text


def werkzeug_text(tc, bibliothek=None):
    """„T3 „Schaftfräser D10““ – so heißt das Werkzeug eines Controllers in Sätzen.

    Steht es in der Werkzeugverwaltung `bibliothek`, mit deren Namen: So heißt
    dasselbe Werkzeug zweier Controller gleich, auch wenn FreeCAD das zweite
    „… L001“ genannt hat (Durchsicht W-004, D-09). Sonst mit dem aus CAM.
    """
    werkzeug = js.werkzeug_von(tc, bibliothek) if bibliothek is not None else None
    if werkzeug is not None:
        name = wz.anzeigename(werkzeug)
    else:
        name = getattr(getattr(tc, "Tool", None), "Label", "") or tc.Label
    return tr("rw.werkzeug", nummer=getattr(tc, "ToolNumber", 0), name=name)


# --- Die Prüfung ----------------------------------------------------------------------------


@dataclass
class _Loesung:
    """Für eine Stellung der Drehachsen: Stellungen der Linearachsen = s0 + S · Punkt.

    `rest0 + R · Punkt` ist, was die Linearachsen nicht erreichen (nur ohne
    volle drei Achsen nicht 0).
    """

    s0: list
    s: list  # je Linearachse eine Zeile (sx, sy, sz)
    rest0: tuple
    r: tuple  # 3 Zeilen (rx, ry, rz)
    voll: bool  # drei unabhängige Linearachsen: jeder Punkt erreichbar

    def erreichbar(self, x, y, z):
        """Kommen die Linearachsen an den Punkt – bis auf UNERREICHBAR_AB?"""
        if self.voll:
            return True
        rest = [
            self.rest0[i] + self.r[i][0] * x + self.r[i][1] * y + self.r[i][2] * z for i in range(3)
        ]
        return math.sqrt(sum(v * v for v in rest)) <= UNERREICHBAR_AB

    def werte(self, x, y, z):
        """Die Stellungen der Linearachsen für den Punkt, in ihrer Reihenfolge."""
        return [
            s0 + zeile[0] * x + zeile[1] * y + zeile[2] * z
            for s0, zeile in zip(self.s0, self.s, strict=True)
        ]


class Pruefung:
    """Eine Maschine, bereit für die Bahnen eines Jobs.

    `assembly` und `maschine`: die Maschine; `werkstueckaufnahme`: die
    Aufnahme, an der der Job liegt – ohne Angabe die erste. Die Maschine
    bleibt, wie sie ist; gerechnet wird ab ihrer Stellung beim Anlegen – auch
    wenn `verfahren` sie danach bewegt (etwa „dorthin fahren“ im Fenster).
    """

    def __init__(self, assembly, maschine, werkstueckaufnahme=None, kette=None):
        self.maschine = maschine
        self.verfahren = vf.Verfahren(assembly, kette)
        self.kette = self.verfahren.kette
        self._in_assembly = assembly.Placement.inverse()
        aufnahmen = [a for a in m.aufnahmen(maschine) if self._glied(a) is not None]
        # Die LCS der Aufnahmen beim Anlegen, in Koordinaten der Assembly.
        self._ausgang = {
            a: self._in_assembly.multiply(m.globale_platzierung(a.Lcs)) for a in aufnahmen
        }
        werkstueck = [a for a in aufnahmen if a.Art == m.AUFNAHME_WERKSTUECK]
        if werkstueckaufnahme not in werkstueck:
            werkstueckaufnahme = werkstueck[0] if werkstueck else None
        self.werkstueckaufnahme = werkstueckaufnahme
        self.werkzeugaufnahmen = [a for a in aufnahmen if a.Art == m.AUFNAHME_WERKZEUG]
        # Was im Durchmesser zählt – nur für die Texte; gerechnet wird im Radius.
        self.durchmesser = {a for a in self.kette.achsen if m.ist_durchmesser(maschine, a.gelenk)}
        self.x_durchmesser = m.x_im_durchmesser(maschine)
        self.revolver = [b for b in m.betriebsarten(maschine) if b.Art == m.ART_REVOLVER]
        self._platzstellung = {}  # Werkzeugaufnahme -> (Revolverachse, Stellung)
        for revolver in self.revolver:
            achse = self.kette.achse_von(revolver.Gelenk)
            if achse is None:
                continue
            stellungen = dict(vf.platzstellungen(self.verfahren, maschine, achse))
            for platz in m.plaetze(maschine, self.kette, revolver):
                if m.name_von(platz) in stellungen:
                    self._platzstellung[platz] = (achse, stellungen[m.name_von(platz)])

    # --- Was die Maschine hergibt ---------------------------------------------------

    def _glied(self, aufnahme):
        return self.kette.glied_von(aufnahme.Lcs) if aufnahme.Lcs is not None else None

    def _lage(self, aufnahme):
        """Das LCS der Aufnahme beim Anlegen, in Koordinaten der Assembly."""
        return self._ausgang[aufnahme]

    def werkzeugaufnahme(self, nummer):
        """Die Aufnahme für das Werkzeug mit dieser Nummer: am Revolver der Platz mit der
        Nummer, sonst die erste Werkzeugaufnahme, die nicht auf einem Revolver sitzt – oder
        None."""
        for platz in self._platzstellung:
            if platz.Platz == nummer:
                return platz
        frei = [a for a in self.werkzeugaufnahmen if a not in self._platzstellung]
        return frei[0] if frei else None

    def mit_revolver(self):
        """Hat die Maschine Revolverplätze – und damit eine Bestückung je Job?"""
        return bool(self._platzstellung)

    def platznummern(self):
        """Die Nummern der Revolverplätze, aufsteigend – leer ohne Revolver (W-002 Stufe G:
        bestueckung.platz_fuer)."""
        return sorted({platz.Platz for platz in self._platzstellung})

    def _achsen_zwischen(self, werkzeugaufnahme):
        """Die Achsen auf dem Weg Werkzeug – Bett – Werkstück, in der Reihenfolge der Kette."""
        auf_dem_weg = set(self.verfahren.pfad(self._glied(werkzeugaufnahme)))
        auf_dem_weg |= set(self.verfahren.pfad(self._glied(self.werkstueckaufnahme)))
        return [a for a in self.kette.achsen if a in auf_dem_weg]

    def _dreh_wege(self, werkzeugaufnahme, drehachsen, rund):
        """Die Wege der Drehachsen: Revolver in Arbeitsstellung, Rundachsen aus `rund`
        ({"A": Grad, …}), alle anderen bleiben (Weg 0)."""
        wege = {}
        revolver = self._platzstellung.get(werkzeugaufnahme)
        for achse in drehachsen:
            if revolver is not None and achse is revolver[0]:
                wege[achse] = self.verfahren.weg_bei(achse, revolver[1])
                continue
            buchstabe = _programmbuchstabe(self.maschine, achse)
            if buchstabe is not None:
                wege[achse] = self.verfahren.weg_bei(achse, rund.get(buchstabe, 0.0))
        return wege

    def _glied_lage(self, glied, wege):
        """Die Bewegung eines Glieds seit dem Ausgang, bei diesen Wegen (fehlende: 0)."""
        gesamt = FreeCAD.Placement()
        for achse in self.verfahren.pfad(glied):
            gesamt = gesamt.multiply(self.verfahren.bewegung(achse, wege.get(achse, 0.0)))
        return gesamt

    def _spitze(self, werkzeugaufnahme, laenge, wege):
        """Die Werkzeugspitze in Koordinaten der Assembly; `laenge`: die Länge eines gerade
        eingespannten Werkzeugs oder seine Einspannung."""
        lage = self._glied_lage(self._glied(werkzeugaufnahme), wege).multiply(
            self._lage(werkzeugaufnahme)
        )
        return lage.multVec(_einspannung(laenge).spitze())

    def _job_lage(self, nullpunkt, wege):
        """Placement vom Job in Koordinaten der Assembly."""
        glied = self._glied(self.werkstueckaufnahme)
        verschiebung = FreeCAD.Placement(nullpunkt, FreeCAD.Rotation())
        return (
            self._glied_lage(glied, wege)
            .multiply(self._lage(self.werkstueckaufnahme))
            .multiply(verschiebung)
        )

    def _loese(self, werkzeugaufnahme, laenge, nullpunkt, linear, dreh_wege):
        """Die Linearachsen für eine Stellung der Drehachsen (siehe _Loesung) – oder None, wenn
        sie sich nicht eindeutig auflösen lassen (mehr Achsen als Richtungen)."""
        import numpy

        wege = dict(dreh_wege)
        spitze0 = self._spitze(werkzeugaufnahme, laenge, wege)
        job0 = self._job_lage(nullpunkt, wege)
        spalten = []
        for achse in linear:
            wege[achse] = 1.0
            d = (self._spitze(werkzeugaufnahme, laenge, wege) - spitze0) - (
                self._job_lage(nullpunkt, wege).Base - job0.Base
            )
            wege[achse] = 0.0
            spalten.append((d.x, d.y, d.z))
        j = numpy.array(spalten, dtype=float).T.reshape(3, len(linear))
        if numpy.linalg.matrix_rank(j, tol=1e-9) < len(linear):
            return None
        drehung = job0.Rotation.toMatrix()
        r = numpy.array(
            [
                [drehung.A11, drehung.A12, drehung.A13],
                [drehung.A21, drehung.A22, drehung.A23],
                [drehung.A31, drehung.A32, drehung.A33],
            ]
        )
        b0 = numpy.array(tuple(job0.Base - spitze0))
        j_plus = numpy.linalg.pinv(j)
        vz = numpy.array([self.verfahren._vorzeichen[a] for a in linear])
        start = numpy.array([self.verfahren.start[a] for a in linear])
        # Stellung = Start + Vorzeichen · Weg, Weg = J⁺ · (R · Punkt + b0)
        s = (vz[:, None] * (j_plus @ r)).tolist()
        s0 = (start + vz * (j_plus @ b0)).tolist()
        rest = numpy.eye(3) - j @ j_plus
        return _Loesung(
            s0=s0,
            s=s,
            rest0=tuple((rest @ b0).tolist()),
            r=tuple(map(tuple, (rest @ r).tolist())),
            voll=len(linear) == 3,
        )

    def _z_verkehrt(self, werkzeugaufnahme, dreh_wege):
        """Zeigt die Z-Achse der Werkzeugaufnahme zum Werkstück hin? Dann liegt sie
        wahrscheinlich andersherum als gedacht (Spezifikation, Abschnitt 3)."""
        werkzeug = self._glied_lage(self._glied(werkzeugaufnahme), dreh_wege).multiply(
            self._lage(werkzeugaufnahme)
        )
        werkstueck = self._glied_lage(self._glied(self.werkstueckaufnahme), dreh_wege).multiply(
            self._lage(self.werkstueckaufnahme)
        )
        z = werkzeug.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
        return (werkstueck.Base - werkzeug.Base).dot(z) > 0

    def _werkzeug_aus(self, werkzeugaufnahme, dreh_wege, richtung, einspannung=None):
        """Kommt das Werkzeug dieser Aufnahme aus `richtung` (in den Achsen des Jobs)? Z des
        Werkzeugs zeigt von der Spitze weg – dorther kommt es; beim geraden Halter (und ohne
        `einspannung`) ist es Z der Werkzeugaufnahme."""
        werkzeug = self._glied_lage(self._glied(werkzeugaufnahme), dreh_wege).multiply(
            self._lage(werkzeugaufnahme)
        )
        werkstueck = self._glied_lage(self._glied(self.werkstueckaufnahme), dreh_wege).multiply(
            self._lage(self.werkstueckaufnahme)
        )
        achse = einspannung.achse() if einspannung is not None else FreeCAD.Vector(0, 0, 1)
        z = werkstueck.Rotation.inverted().multVec(werkzeug.Rotation.multVec(achse))
        soll = FreeCAD.Vector(richtung)
        return soll.Length > 0 and z.dot(soll) / soll.Length > 1 - (1 - QUER) / 2

    def kommt_aus(self, nummer, richtung, einspannung=None):
        """(Aufnahme, kommt das Werkzeug `nummer` aus `richtung`?) – wie der Hinweis „nicht
        radial“ beim Prüfen, für den 4-Achs-Assistenten, bevor es eine Bahn gibt (W-002
        Stufe E5). `richtung` in den Achsen des Jobs, `einspannung` mit der Lage aus dem
        Halter. (None, None), wenn es für die Nummer keinen Platz gibt."""
        aufnahme = self.werkzeugaufnahme(nummer)
        if aufnahme is None:
            return None, None
        _linear, drehachsen = self.achsen_fuer(aufnahme)
        grundstellung = self._dreh_wege(aufnahme, drehachsen, {})
        return aufnahme, self._werkzeug_aus(aufnahme, grundstellung, richtung, einspannung)

    def _werkzeug_quer(self, werkzeugaufnahme, dreh_wege, einspannung=None):
        """Steht das Werkzeug quer zu Z des Jobs – ein radialer Platz oder Halter am Revolver?
        Die Bahnen der CAM-Operationen sind für ein Werkzeug längs Z gerechnet; ein radiales
        führe sie quer durchs Teil (Manuels Test, 2026-09-27)."""
        werkzeug = self._glied_lage(self._glied(werkzeugaufnahme), dreh_wege).multiply(
            self._lage(werkzeugaufnahme)
        )
        werkstueck = self._glied_lage(self._glied(self.werkstueckaufnahme), dreh_wege).multiply(
            self._lage(self.werkstueckaufnahme)
        )
        achse = einspannung.achse() if einspannung is not None else FreeCAD.Vector(0, 0, 1)
        z = werkzeug.Rotation.multVec(achse)
        return abs(werkstueck.Rotation.inverted().multVec(z).z) < QUER

    def achsen_fuer(self, werkzeugaufnahme):
        """(Linearachsen, Drehachsen) zwischen dieser Werkzeugaufnahme und dem Werkstück."""
        achsen = self._achsen_zwischen(werkzeugaufnahme)
        return [a for a in achsen if a.art == LINEAR], [a for a in achsen if a.art != LINEAR]

    def gefahrene_achsen(self, werkzeugaufnahme):
        """Die Achsen, die für diese Werkzeugaufnahme fahren: die Linearachsen dazwischen, der
        Revolver und die Rundachsen, die positionieren – keine Spindeln."""
        linear, drehachsen = self.achsen_fuer(werkzeugaufnahme)
        return linear + list(self._dreh_wege(werkzeugaufnahme, drehachsen, {}))

    def loeser(self, werkzeugaufnahme, laenge, nullpunkt_des_jobs):
        """Für eine Operation: eine Funktion rund → (_Loesung oder None, {Drehachse: Stellung}).

        `rund` wie {"A": Grad}. Wie eine Steuerung ohne TCPM: X, Y und Z sind die
        Linearachsen, gelöst mit den Rundachsen auf 0 (der Revolver in
        Arbeitsstellung) – die Rundachsen drehen das Werkstück (oder den Kopf) dann
        darunter weg. So zeigt auch FreeCAD eine Bahn mit A, B und C
        (Spezifikation W-003, V3e).
        """
        linear, drehachsen = self.achsen_fuer(werkzeugaufnahme)
        grundstellung = self._dreh_wege(werkzeugaufnahme, drehachsen, {})
        geloest = self._loese(werkzeugaufnahme, laenge, nullpunkt_des_jobs, linear, grundstellung)
        drehungen = {}

        def loesung(rund):
            schluessel = tuple(round(rund.get(b, 0.0), 9) for b in RUNDACHSEN)
            if schluessel not in drehungen:
                dreh_wege = self._dreh_wege(werkzeugaufnahme, drehachsen, rund)
                drehungen[schluessel] = {
                    a: self.verfahren.stellung_bei(a, w) for a, w in dreh_wege.items()
                }
            return geloest, drehungen[schluessel]

        return loesung

    def stellungen(self, punkt, werkzeugaufnahme, laenge, nullpunkt_des_jobs, rund=None):
        """{Achse: Stellung} für alle Achsen zwischen Werkzeug und Werkstück für den Bahnpunkt
        `punkt` (x, y, z im Job) mit den Rundachsen `rund` (wie {"A": Grad}) – ohne TCPM wie
        in loeser(): Mit den Rundachsen auf 0 stünde die Spitze auf `punkt`. None, wenn die
        Linearachsen nicht dorthin kommen oder sich nicht eindeutig auflösen lassen."""
        achsen = self._achsen_zwischen(werkzeugaufnahme)
        linear = [a for a in achsen if a.art == LINEAR]
        drehachsen = [a for a in achsen if a.art != LINEAR]
        dreh_wege = self._dreh_wege(werkzeugaufnahme, drehachsen, rund or {})
        # Ohne TCPM: die Linearachsen wie mit den Rundachsen auf 0 (loeser()).
        grundstellung = self._dreh_wege(werkzeugaufnahme, drehachsen, {})
        loesung = self._loese(werkzeugaufnahme, laenge, nullpunkt_des_jobs, linear, grundstellung)
        if loesung is None or not loesung.erreichbar(*punkt):
            return None
        ergebnis = {a: self.verfahren.stellung_bei(a, w) for a, w in dreh_wege.items()}
        ergebnis.update(zip(linear, loesung.werte(*punkt), strict=True))
        return ergebnis

    # --- Der Job --------------------------------------------------------------------

    def pruefe_job(self, job, nullpunkt_des_jobs=None, bibliothek=None):
        """Prüft alle aktiven Operationen des Jobs; gibt ein Ergebnis zurück.

        `nullpunkt_des_jobs`: Vector von der Werkstückaufnahme zum Nullpunkt des
        Jobs, ohne Angabe nullpunkt(job). `bibliothek`: die Werkzeugverwaltung
        (werkzeuge.Bibliothek) für die Werkzeuglängen.
        """
        ergebnis = Ergebnis()
        if self.werkstueckaufnahme is None:
            ergebnis.hinweise.append(tr("rw.keine_werkstueckaufnahme"))
            return ergebnis
        if not self.werkzeugaufnahmen:
            ergebnis.hinweise.append(tr("rw.keine_werkzeugaufnahme"))
            return ergebnis
        if nullpunkt_des_jobs is None:
            nullpunkt_des_jobs = nullpunkt(job)
        sammler = _Sammler(self, ergebnis)
        self._bestueckung_pruefen(job, bibliothek, sammler)
        for op in _operationen(job):
            self._pruefe_operation(op, nullpunkt_des_jobs, bibliothek, sammler)
        sammler.fertig()
        return ergebnis

    def _bestueckung_pruefen(self, job, bibliothek, sammler):
        """Stecken im Job zwei Werkzeuge auf einem Revolverplatz (W-002 Stufe G)? Die Maschine
        nähme nur eines – ein Satz sagt, welche und wo."""
        if not self._platzstellung:
            return  # ohne Revolver keine Plätze
        zeichen = einheiten.gewaehltes_dezimalzeichen() or einheiten.PUNKT
        for nummer, auf in bs.doppelt(job, bibliothek):
            namen = ", ".join(mit_dezimalzeichen(bs.kurz(e), zeichen) for e in auf)
            sammler.hinweis(tr("rw.bestueckung.doppelt", platz=f"P{nummer}", werkzeuge=namen))

    def _pruefe_operation(self, op, nullpunkt_des_jobs, bibliothek, sammler):
        tc = getattr(op, "ToolController", None)
        if tc is None:
            sammler.hinweis(tr("rw.ohne_controller", operation=op.Label))
            return
        nummer = getattr(tc, "ToolNumber", 0)
        aufnahme = self.werkzeugaufnahme(nummer)
        if aufnahme is None:
            sammler.hinweis(
                tr(
                    "rw.platz_fehlt",
                    operation=op.Label,
                    nummer=nummer,
                    revolver=m.name_von(self.revolver[0]) if self.revolver else "",
                )
            )
            return
        laenge, quelle = werkzeuglaenge(tc, bibliothek)
        sammler.laenge(tc, laenge, quelle, bibliothek)
        eingespannt = einspannung(tc, bibliothek)

        linear, drehachsen = self.achsen_fuer(aufnahme)
        if len(linear) > 3:
            sammler.zu_viele(linear)
            return
        grundstellung = self._dreh_wege(aufnahme, drehachsen, {})
        radial = getattr(op, "Werkzeugrichtung", None) if _ist_rundum(op) else None
        if self._z_verkehrt(aufnahme, grundstellung):
            sammler.hinweis(tr("rw.z_verkehrt", aufnahme=m.name_von(aufnahme)))
        elif radial is not None:
            # Eine Bahn von „Rundum schruppen“ ist für ein radiales Werkzeug gerechnet.
            if not self._werkzeug_aus(aufnahme, grundstellung, radial, eingespannt):
                # Steht die Aufnahme selbst radial (Sternrevolver, P-2026-09-30-52), hilft ein
                # gerader Halter – sonst ein gewinkelter.
                werte = {
                    "operation": op.Label,
                    "werkzeug": f"T{nummer}",
                    "aufnahme": m.name_von(aufnahme),
                    "richtung": richtung_text(radial),
                }
                if self._werkzeug_aus(aufnahme, grundstellung, radial):
                    sammler.hinweis(tr("rw.werkzeug_radial_gerade", **werte))
                else:
                    sammler.hinweis(tr("rw.werkzeug_radial", **werte))
        elif self._werkzeug_quer(aufnahme, grundstellung, eingespannt):
            sammler.hinweis(
                tr(
                    "rw.werkzeug_quer",
                    operation=op.Label,
                    werkzeug=f"T{nummer}",
                    aufnahme=m.name_von(aufnahme),
                )
            )
        loesung = self.loeser(aufnahme, eingespannt, nullpunkt_des_jobs)
        from .kinematik import Kinematik

        kinematik = Kinematik(self, aufnahme, eingespannt, nullpunkt_des_jobs)
        sammler.beginne(op.Label, linear, drehachsen, kinematik, f"T{nummer}")
        vorhanden = {_programmbuchstabe(self.maschine, a) for a in drehachsen} - {None}
        fremd = set()  # Rundachsen, um die das Programm dreht, die Maschine aber nicht hat
        for schritt in _bahn(op.Path.Commands, sammler.unbekannt):
            fremd |= {b for b, w in schritt.rund.items() if abs(w) > 1e-9} - vorhanden
            if schritt.art == "punkt":
                sammler.punkt(schritt.ort, schritt.rund, *loesung(schritt.rund))
                continue
            # Kreis: Punkte an den Umkehrstellen jeder Achse
            geloest, dreh = loesung(schritt.rund)
            if geloest is None:
                sammler.zu_viele(linear)
                continue
            for punkt in schritt.ort.punkte(geloest.s):
                sammler.punkt(punkt, schritt.rund, geloest, dreh)
        for buchstabe in sorted(fremd):
            sammler.rundachse_fehlt(buchstabe, sorted(vorhanden))
        sammler.ende_operation()


def _ist_rundum(op):
    """Ist `op` eine Operation „Rundum schruppen“ (vierachs_operation)?"""
    from .vierachs_operation import ist_rundum

    return ist_rundum(op)


def richtung_text(richtung):
    """„+X“, „−Z“ … – eine Richtung längs einer Achse des Jobs, sonst die drei Zahlen."""
    v = FreeCAD.Vector(richtung)
    if v.Length > 0:
        v.normalize()
    for buchstabe, wert in zip("XYZ", (v.x, v.y, v.z), strict=True):
        if abs(abs(wert) - 1) < 1e-6:
            return ("+" if wert > 0 else "−") + buchstabe
    return f"({_zahl(v.x, 2)}; {_zahl(v.y, 2)}; {_zahl(v.z, 2)})"


def _programmbuchstabe(maschine, achse):
    """Der Buchstabe der Rundachse im Programm (C1 → „C“), wenn sie positionieren kann."""
    for ba in m.betriebsarten(maschine):
        if ba.Gelenk == achse.gelenk and ba.Art == m.ART_POSITIONIEREN:
            buchstabe = m.programmname(ba).upper()
            return buchstabe if buchstabe in RUNDACHSEN else None
    return None


def _operationen(job):
    """Die aktiven Operationen des Jobs, wie der Postprozessor sie nimmt: oben in der
    Gruppe „Operations“ (eine Nachbearbeitung trägt die Bahn ihrer Operation)."""
    gruppe = getattr(getattr(job, "Operations", None), "Group", [])
    ergebnis = []
    for op in gruppe:
        if hasattr(op, "Group") and not hasattr(op, "Path"):
            ergebnis += [o for o in op.Group if hasattr(o, "Path")]
        elif hasattr(op, "Path"):
            ergebnis.append(op)
    return [op for op in ergebnis if getattr(op, "Active", True) and op.Path is not None]


# --- Sammeln ------------------------------------------------------------------------------


class _Sammler:
    """Nimmt die Punkte einer Prüfung auf: Bereiche, Überschreitungen, Hinweise."""

    def __init__(self, pruefung, ergebnis):
        self.pruefung = pruefung
        self.ergebnis = ergebnis
        self._bereich = {}  # Achse -> [von, bis]
        self._weitester = {}  # (Nummer der Operation, Achse, Seite) -> Ueberschreitung
        self._hinweise = []
        self._nummer = -1  # der wievielten Operation die Punkte gehören
        self.operation = ""
        self._linear = []
        self._rund = []  # Drehachsen, die gegen ihre Grenzen gehalten werden
        self._unerreichbar = 0
        self._punkte_hier = 0
        self._erster_unerreichbarer = None
        self._unbekannt = set()
        self._werkzeuge = {}  # Nummer der Operation -> (Kinematik, „T1“)

    def hinweis(self, satz):
        if satz not in self._hinweise:
            self._hinweise.append(satz)

    def laenge(self, tc, laenge, quelle, bibliothek=None):
        """Sagt, womit gerechnet wurde, wenn es nicht die Länge ab Spindelnase ist."""
        nummer = getattr(tc, "ToolNumber", 0)
        self.ergebnis.laengen.setdefault(nummer, quelle)
        werte = {"werkzeug": werkzeug_text(tc, bibliothek), "laenge": weg_text(laenge)}
        if quelle == LAENGE_HALTER:
            halter = werkzeughalter(tc, bibliothek)
            if halter is not None and halter.gewinkelt:  # das Feld heißt dann so (D-40)
                self.hinweis(Hinweis(tr("rw.laenge_halter_gewinkelt", **werte), nummer))
            else:
                self.hinweis(Hinweis(tr("rw.laenge_halter", **werte), nummer))
        elif quelle == LAENGE_VORSCHLAG:
            halter = werkzeughalter(tc, bibliothek)
            werte["halter"] = hl.text(halter) if halter is not None else ""
            self.hinweis(Hinweis(tr("rw.laenge_vorschlag", **werte), nummer))
        elif quelle == LAENGE_GESAMT:
            self.hinweis(Hinweis(tr("rw.laenge_gesamt", **werte), nummer))
        elif quelle == LAENGE_GESCHAETZT:
            self.hinweis(Hinweis(tr("rw.laenge_geschaetzt", **werte), nummer))
        elif quelle == LAENGE_CAM:
            self.hinweis(Hinweis(tr("rw.laenge_cam", **werte), nummer))

    def rundachse_fehlt(self, buchstabe, vorhanden):
        """Das Programm dreht um `buchstabe`, die Maschine hat diese Rundachse nicht – die
        Prüfung rechnet ohne die Drehung. Etwa ein Job des 4-Achs-Assistenten mit A auf
        einer Drehmaschine mit C (Manuels Test, W-003 V2c)."""
        if vorhanden:
            text = tr(
                "rw.rundachse_fehlt_andere",
                operation=self.operation,
                buchstabe=buchstabe,
                achsen=", ".join(vorhanden),
            )
        else:
            text = tr("rw.rundachse_fehlt", operation=self.operation, buchstabe=buchstabe)
        self.hinweis(text)

    def zu_viele(self, linear):
        namen = ", ".join(vf.namen(self.pruefung.maschine, a) for a in linear)
        self.hinweis(tr("rw.zu_viele_achsen", achsen=namen))

    def unbekannt(self, befehl):
        if befehl not in self._unbekannt:
            self._unbekannt.add(befehl)
            self.hinweis(tr("rw.befehl", operation=self.operation, befehl=befehl))

    def beginne(self, operation, linear, drehachsen, kinematik=None, werkzeug=""):
        """Die Punkte einer neuen Operation kommen; `kinematik` (kinematik.Kinematik) sagt
        später, wo die Spitze an einer Grenze stünde."""
        self._nummer += 1
        self._werkzeuge[self._nummer] = (kinematik, werkzeug)
        self.operation = operation
        self._linear = linear
        self._rund = [a for a in drehachsen if _begrenzt_pruefen(self.pruefung.maschine, a)]
        self._unerreichbar = 0
        self._punkte_hier = 0
        self._erster_unerreichbarer = None
        self._unbekannt = set()

    def punkt(self, punkt, rund, loesung, dreh):
        """Ein Punkt der Bahn (x, y, z) mit den Rundachsen `rund`; `loesung` und `dreh` für
        deren Stellung (Pruefung._loese und die Stellungen der Drehachsen)."""
        if loesung is None:
            self.zu_viele(self._linear)
            return
        self._punkte_hier += 1
        if not loesung.erreichbar(*punkt):
            self._unerreichbar += 1
            if self._erster_unerreichbarer is None:
                self._erster_unerreichbarer = _programmpunkt(punkt, rund)
            return
        werte = list(zip(self._linear, loesung.werte(*punkt), strict=True))
        werte += [(achse, dreh[achse]) for achse in self._rund]
        self.ergebnis.punkte += 1
        for achse, stellung in werte:
            bereich = self._bereich.get(achse)
            if bereich is None:
                self._bereich[achse] = [stellung, stellung]
            elif stellung < bereich[0]:
                bereich[0] = stellung
            elif stellung > bereich[1]:
                bereich[1] = stellung
            if achse.minimum is not None and stellung < achse.minimum - 1e-6:
                self._merke(achse, "min", achse.minimum, stellung, punkt, rund, werte, dreh)
            elif achse.maximum is not None and stellung > achse.maximum + 1e-6:
                self._merke(achse, "max", achse.maximum, stellung, punkt, rund, werte, dreh)

    def _merke(self, achse, seite, grenze, stellung, punkt, rund, werte, dreh):
        """Eine Überschreitung – gemerkt, wenn sie in dieser Operation die weiteste ist."""
        schluessel = (self._nummer, achse, seite)
        bisher = self._weitester.get(schluessel)
        if bisher is not None and abs(stellung - grenze) <= abs(bisher.stellung - grenze):
            return
        stellungen = dict(dreh)
        stellungen.update(werte)
        self._weitester[schluessel] = Ueberschreitung(
            achse=achse,
            name=vf.namen(self.pruefung.maschine, achse),
            operation=self.operation,
            stellung=stellung,
            grenze=grenze,
            punkt=_programmpunkt(punkt, rund),
            stellungen=stellungen,
            durchmesser=achse in self.pruefung.durchmesser,
            x_durchmesser=self.pruefung.x_durchmesser,
        )

    def ende_operation(self):
        if self._unerreichbar:
            self.hinweis(
                tr(
                    "rw.unerreichbar",
                    operation=self.operation,
                    punkt=punkt_text(self._erster_unerreichbarer, self.pruefung.x_durchmesser),
                    anzahl=self._unerreichbar,
                    gesamt=self._punkte_hier,
                )
            )

    def fertig(self):
        maschine = self.pruefung.maschine

        def reihenfolge(achse):
            """Erst die Linearachsen, dann die Drehachsen, je nach Namen: X1, Y1, Z1, C1."""
            return achse.art != LINEAR, vf.namen(maschine, achse)

        # Nach Operation (wie im Job), dann Achse, erst die untere Grenze.
        schluessel = sorted(self._weitester, key=lambda k: (k[0], reihenfolge(k[1]), k[2] != "min"))
        for nummer, achse, _seite in schluessel:
            kinematik, werkzeug = self._werkzeuge.get(nummer, (None, ""))
            if kinematik is not None and achse.art == LINEAR:
                _an_grenze_rechnen(self._weitester[(nummer, achse, _seite)], kinematik, werkzeug)
        self.ergebnis.ueberschreitungen = [self._weitester[k] for k in schluessel]
        self.ergebnis.bereiche = [
            Bereich(a, vf.namen(maschine, a), von, bis, a in self.pruefung.durchmesser)
            for a, (von, bis) in sorted(self._bereich.items(), key=lambda e: reihenfolge(e[0]))
        ]
        self.ergebnis.hinweise = list(self._hinweise)


def _an_grenze_rechnen(ueberschreitung, kinematik, werkzeug):
    """Trägt ein, wo die Spitze an der Grenze stünde – die Achse auf der Grenze, alle
    anderen wie an der Stelle der Überschreitung."""
    stellungen = dict(ueberschreitung.stellungen)
    stellungen[ueberschreitung.achse] = ueberschreitung.grenze
    try:
        x, y, z = kinematik.programm(stellungen)
    except Exception as fehler:  # eine halb eingerichtete Maschine soll nicht stören
        FreeCAD.Console.PrintLog(f"CAM-Addon: Spitze an der Grenze: {fehler}\n")
        return
    punkt = {b: w for b, w in ueberschreitung.punkt.items() if b in RUNDACHSEN}
    punkt.update({"X": x, "Y": y, "Z": z})
    ueberschreitung.an_grenze = punkt
    ueberschreitung.werkzeug = werkzeug


def _begrenzt_pruefen(maschine, achse):
    """Wird eine Drehachse gegen ihre Grenzen gehalten? Ja, wenn sie positioniert und nicht
    endlos ist – Revolver und Spindeln nicht."""
    for ba in m.betriebsarten(maschine):
        if ba.Gelenk == achse.gelenk and ba.Art == m.ART_POSITIONIEREN:
            return not ba.Endlos
    return False


def _programmpunkt(punkt, rund):
    werte = {"X": punkt[0], "Y": punkt[1], "Z": punkt[2]}
    werte.update({b: rund.get(b, 0.0) for b in RUNDACHSEN})
    return werte


# --- Die Bahn lesen -------------------------------------------------------------------------


@dataclass
class _Bogen:
    """Ein Kreisbogen der Bahn in seiner Ebene (G17/G18/G19), auch als Schraube."""

    mitte: tuple  # Mittelpunkt (x, y, z)
    radius: float
    achsen: tuple  # Indizes (erste, zweite, Normale) in (x, y, z)
    winkel0: float  # Startwinkel (Bogenmaß) in der Ebene
    winkel: float  # überstrichener Winkel, positiv gegen den Uhrzeigersinn
    hoehe0: float  # Start entlang der Normalen
    steigung: float  # Weg entlang der Normalen über den ganzen Bogen

    def bei(self, t):
        """Der Punkt beim Anteil `t` (0 … 1) des Bogens."""
        phi = self.winkel0 + t * self.winkel
        erste, zweite, normale = self.achsen
        punkt = [0.0, 0.0, 0.0]
        punkt[erste] = self.mitte[erste] + self.radius * math.cos(phi)
        punkt[zweite] = self.mitte[zweite] + self.radius * math.sin(phi)
        punkt[normale] = self.hoehe0 + t * self.steigung
        return tuple(punkt)

    def punkte(self, zeilen):
        """Die Stellen im Bogen, an denen eine der Achsen (Zeilen von S) umkehrt – Start
        und Ende prüft die Bahn ohnehin."""
        return [self.bei(t) for t in self.anteile(zeilen)]

    def anteile(self, zeilen):
        """Wo im Bogen (Anteil 0 … 1, aufsteigend) eine der Achsen umkehrt.

        Entlang des Kreises ist eine Achse a + b·cos φ + c·sin φ (+ Schraube);
        ihr Größtes liegt bei φ = atan2(c, b), ihr Kleinstes gegenüber.
        """
        erste, zweite, _normale = self.achsen
        anteile = set()
        for zeile in zeilen:
            b, c = zeile[erste], zeile[zweite]
            if abs(b) < 1e-12 and abs(c) < 1e-12:
                continue
            for phi in (math.atan2(c, b), math.atan2(c, b) + math.pi):
                t = _anteil(phi, self.winkel0, self.winkel)
                if t is not None:
                    anteile.add(t)
        return sorted(anteile)


@dataclass
class _Schritt:
    """Was die Bahn liefert: ein Punkt (x, y, z) oder ein Kreisbogen (_Bogen)."""

    art: str  # "punkt" oder "bogen"
    ort: object  # (x, y, z) oder _Bogen
    rund: dict  # Rundachsen dort: {"A": …, "B": …, "C": …}
    eilgang: bool  # die Bewegung hierher: Eilgang – sonst Vorschub
    vorschub: float  # zuletzt gesetztes F (FreeCAD: mm/s), 0 = keins
    satz: int  # der wievielte Befehl der Bahn (ab 1)
    invers: bool = False  # G93: F ist 1 ÷ Zeit des ganzen Satzes (FreeCAD: ÷ 60)
    anteil: float = 1.0  # so viel vom Satz macht dieser Schritt aus (für G93)


def _anteil(phi, start, ueberstrichen):
    """Bei welchem Anteil (0 … 1) des Bogens der Winkel `phi` liegt – oder None."""
    if abs(ueberstrichen) < 1e-12:
        return None
    # Wie weit vom Start aus, in der Drehrichtung des Bogens.
    weg = ((phi - start) if ueberstrichen > 0 else (start - phi)) % (2 * math.pi)
    t = weg / abs(ueberstrichen)
    return t if 0.0 < t < 1.0 else None


def _bahn(befehle, unbekannt, rueckzug=False):
    """Liest die Befehle einer Bahn; liefert je Punkt und je Kreisbogen einen _Schritt.

    Punkte, deren X, Y oder Z noch niemand gesetzt hat (am Anfang einer
    Operation), werden übersprungen. Unbekannte Befehle mit Bewegung meldet
    `unbekannt(name)`. `rueckzug`: nach einem Bohrzyklus auch der Punkt, auf den
    er zurückzieht – fürs Abfahren; die Reichweite kennt die Höhe schon.
    """
    lage = {"X": None, "Y": None, "Z": None}
    rund = dict.fromkeys(RUNDACHSEN, 0.0)
    absolut = True
    ebene = "G17"
    rueckzug_auf_r = False  # G99: nach dem Zyklus auf R, sonst (G98) auf die Ausgangshöhe
    zyklus = {}  # Z und R des letzten Bohrzyklus
    vorschub = 0.0
    invers = False  # G93 statt G94

    def bekannt():
        return all(v is not None for v in lage.values())

    def ziel(werte):
        neu = dict(lage)
        for buchstabe in ("X", "Y", "Z"):
            if buchstabe in werte:
                wert = float(werte[buchstabe])
                if absolut:
                    neu[buchstabe] = wert
                elif neu[buchstabe] is not None:
                    neu[buchstabe] += wert
        neu_rund = dict(rund)
        for buchstabe in RUNDACHSEN:
            if buchstabe in werte:
                wert = float(werte[buchstabe])
                neu_rund[buchstabe] = wert if absolut else neu_rund[buchstabe] + wert
        return neu, neu_rund

    for satz, befehl in enumerate(befehle, start=1):
        name = befehl.Name.upper()
        werte = befehl.Parameters
        if "F" in werte:
            vorschub = float(werte["F"])
        if not name or name.startswith("(") or name[0] in "MTSFON":
            continue
        name = _ohne_null(name)
        if name == "G90":
            absolut = True
        elif name == "G91":
            absolut = False
        elif name in EBENEN:
            ebene = name
        elif name == "G98":
            rueckzug_auf_r = False
        elif name == "G99":
            rueckzug_auf_r = True
        elif name in ("G93", "G94"):
            invers = name == "G93"
        if name in OHNE_BEWEGUNG:
            continue

        if name in ("G0", "G1"):
            eilgang = name == "G0"
            neu, neu_rund = ziel(werte)
            if bekannt() and any(abs(neu_rund[b] - rund[b]) > 1e-9 for b in RUNDACHSEN):
                # Eine Rundachse dreht sich im Satz: Punkte in kleinen Schritten.
                schritte = max(
                    1,
                    math.ceil(max(abs(neu_rund[b] - rund[b]) for b in RUNDACHSEN) / DREH_SCHRITT),
                )
                von = (lage["X"], lage["Y"], lage["Z"])
                nach = (neu["X"], neu["Y"], neu["Z"])
                for k in range(1, schritte + 1):
                    t = k / schritte
                    punkt = tuple(a + t * (b - a) for a, b in zip(von, nach, strict=True))
                    zwischen = {b: rund[b] + t * (neu_rund[b] - rund[b]) for b in RUNDACHSEN}
                    yield _Schritt(
                        "punkt", punkt, zwischen, eilgang, vorschub, satz, invers, 1 / schritte
                    )
                lage, rund = neu, neu_rund
                continue
            lage, rund = neu, neu_rund
            if bekannt():
                punkt = (lage["X"], lage["Y"], lage["Z"])
                yield _Schritt("punkt", punkt, dict(rund), eilgang, vorschub, satz, invers)
        elif name in ("G2", "G3"):
            if not bekannt():
                lage, rund = ziel(werte)
                continue
            bogen = _bogen(lage, werte, ebene, name == "G3", absolut)
            lage, rund = ziel(werte)
            if bogen is not None:
                # Mit G93 zählt die Zeit des ganzen Bogens erst an seinem Ende.
                yield _Schritt("bogen", bogen, dict(rund), False, vorschub, satz, invers, 0.0)
            if bekannt():
                punkt = (lage["X"], lage["Y"], lage["Z"])
                yield _Schritt("punkt", punkt, dict(rund), False, vorschub, satz, invers)
        elif name in BOHRZYKLEN:
            if "Z" in werte:
                zyklus["Z"] = float(werte["Z"])
            if "R" in werte:
                zyklus["R"] = float(werte["R"])
            ausgang = lage["Z"]
            for buchstabe in ("X", "Y"):
                if buchstabe in werte:
                    lage[buchstabe] = float(werte[buchstabe])
            if lage["X"] is None or lage["Y"] is None or "Z" not in zyklus:
                continue
            # Über dem Loch und auf R im Eilgang, auf den Grund im Vorschub.
            hoehen = [
                (hoehe, eilgang)
                for hoehe, eilgang in (
                    (ausgang, True),
                    (zyklus.get("R"), True),
                    (zyklus["Z"], False),
                )
                if hoehe is not None
            ]
            for hoehe, eilgang in hoehen:
                punkt = (lage["X"], lage["Y"], hoehe)
                yield _Schritt("punkt", punkt, dict(rund), eilgang, vorschub, satz)
            lage["Z"] = zyklus.get("R") if rueckzug_auf_r or ausgang is None else ausgang
            if rueckzug:
                punkt = (lage["X"], lage["Y"], lage["Z"])
                yield _Schritt("punkt", punkt, dict(rund), True, vorschub, satz)
        elif any(b in werte for b in ("X", "Y", "Z", *RUNDACHSEN)):
            unbekannt(name)


def _ohne_null(name):
    """„G01“ → „G1“, „G00“ → „G0“ – FreeCAD schreibt beides."""
    if len(name) > 2 and name[0] == "G" and name[1] == "0" and name[2].isdigit():
        return "G" + name[2:]
    return name


def _bogen(lage, werte, ebene, gegen_uhrzeiger, absolut):
    """Der Kreisbogen vom jetzigen Punkt zum Ziel (I/J/K ab dem Start oder R) – oder None."""
    erste, zweite, normale = EBENEN[ebene]
    index = {"X": 0, "Y": 1, "Z": 2}
    start = (lage["X"], lage["Y"], lage["Z"])
    ende = list(start)
    for buchstabe in ("X", "Y", "Z"):
        if buchstabe in werte:
            wert = float(werte[buchstabe])
            ende[index[buchstabe]] = wert if absolut else start[index[buchstabe]] + wert
    e, z, n = index[erste], index[zweite], index[normale]
    if MITTE[erste] in werte or MITTE[zweite] in werte:
        mitte_e = start[e] + float(werte.get(MITTE[erste], 0.0))
        mitte_z = start[z] + float(werte.get(MITTE[zweite], 0.0))
    elif "R" in werte:
        mitte = _mitte_aus_radius(
            (start[e], start[z]), (ende[e], ende[z]), float(werte["R"]), gegen_uhrzeiger
        )
        if mitte is None:
            return None
        mitte_e, mitte_z = mitte
    else:
        return None
    radius = math.hypot(start[e] - mitte_e, start[z] - mitte_z)
    if radius < 1e-9:
        return None
    winkel0 = math.atan2(start[z] - mitte_z, start[e] - mitte_e)
    winkel1 = math.atan2(ende[z] - mitte_z, ende[e] - mitte_e)
    if gegen_uhrzeiger:
        ueberstrichen = (winkel1 - winkel0) % (2 * math.pi)
    else:
        ueberstrichen = -((winkel0 - winkel1) % (2 * math.pi))
    if abs(ueberstrichen) < 1e-9:  # Start = Ende: ein Vollkreis
        ueberstrichen = 2 * math.pi if gegen_uhrzeiger else -2 * math.pi
    mitte = [0.0, 0.0, 0.0]
    mitte[e], mitte[z] = mitte_e, mitte_z
    return _Bogen(
        mitte=tuple(mitte),
        radius=radius,
        achsen=(e, z, n),
        winkel0=winkel0,
        winkel=ueberstrichen,
        hoehe0=start[n],
        steigung=ende[n] - start[n],
    )


def _mitte_aus_radius(start, ende, radius, gegen_uhrzeiger):
    """Mittelpunkt eines Kreises mit R: Negatives R heißt der Bogen über 180°."""
    dx, dy = ende[0] - start[0], ende[1] - start[1]
    sehne = math.hypot(dx, dy)
    if sehne < 1e-12 or sehne > 2 * abs(radius) + 1e-9:
        return None
    abstand = math.sqrt(max(radius * radius - sehne * sehne / 4, 0.0))
    # Links der Sehne (von Start nach Ende gesehen) liegt die Mitte eines
    # Bogens gegen den Uhrzeigersinn unter 180°.
    links = (-dy / sehne, dx / sehne)
    seite = 1.0 if gegen_uhrzeiger else -1.0
    if radius < 0:
        seite = -seite
    mitte_sehne = ((start[0] + ende[0]) / 2, (start[1] + ende[1]) / 2)
    return (
        mitte_sehne[0] + seite * abstand * links[0],
        mitte_sehne[1] + seite * abstand * links[1],
    )
