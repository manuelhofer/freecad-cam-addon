# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Maschinenobjekt: alle Maschinendaten einer Assembly an einer Stelle.

Die Assembly beschreibt, wie sich die Maschine bewegt (siehe kette.py). Was
FreeCAD darüber hinaus nicht weiß – wie eine Achse im NC-Programm heißt, wie
schnell sie fährt, wo Werkzeug und Werkstück sitzen –, steht im
Maschinenobjekt. So liegt es im Dokument:

    Assembly
    └── Maschine                     Gruppe, eine je Assembly
        ├── X1 · Linear              Betriebsart: verweist auf ein Gelenk
        ├── S4 · Spindel             zwei Betriebsarten desselben Gelenks
        ├── C4 · Positionieren
        ├── Futter · Werkstückaufn.  Aufnahme: verweist auf ein LCS
        └── Y · Schräge Achse        Transformation: verweist auf Betriebsarten

Betriebsart
    Die Rolle, die ein Gelenk im NC-Programm spielt, mit NC-Namen und
    Kennwerten. Ein Drehgelenk kann mehrere haben (S4 und C4).

Aufnahme
    Eine Stelle, an der ein Werkzeug sitzt oder ein Werkstück gespannt wird,
    markiert durch ein lokales Koordinatensystem (LCS). Revolverplätze sind
    Werkzeugaufnahmen mit Platznummer.

Transformation
    Eine Umrechnung der Steuerung zwischen dem rechtwinkligen Programm und
    den Schlitten – bisher nur die schräge Achse (schraege_achse.py).

Jede Betriebsart, Aufnahme und Transformation ist ein eigenes Objekt: So stehen sie
lesbar im Baum, Rückgängig funktioniert von selbst, und ein gelöschtes Gelenk
hinterlässt nur einen leeren Verweis statt verlorener Daten.

Unbekannte Kennwerte sind 0 – keiner dieser Werte kann an einer echten
Maschine 0 sein, also ist 0 als „unbekannt“ eindeutig.

Läuft ohne Oberfläche.
"""

import re
from dataclasses import dataclass, field

import FreeCAD

from . import kette as kette_modul
from .kette import DREH, HINWEIS, LINEAR, meldung
from .sprache import tr

# Betriebsarten. Die Werte werden im Dokument gespeichert und sind deshalb
# feste ASCII-Wörter; angezeigt wird art_text().
ART_LINEAR = "Linear"
ART_POSITIONIEREN = "Positionieren"
ART_SPINDEL = "Spindel"
ART_REVOLVER = "Revolver"
BETRIEBSARTEN = [ART_LINEAR, ART_POSITIONIEREN, ART_SPINDEL, ART_REVOLVER]

# Welche Betriebsarten zu welcher Art von Achse passen.
ERLAUBT = {LINEAR: [ART_LINEAR], DREH: [ART_POSITIONIEREN, ART_SPINDEL, ART_REVOLVER]}

# Die Kennwerte je Betriebsart: (Eigenschaft, Pflicht). Die Einheiten sind die
# aus Datenblatt und Maschinendaten – siehe Spezifikation W-001, Abschnitt 4.
WERTE = {
    ART_LINEAR: [
        ("Eilgang", False),  # leer: export.VORGABE_EILGANG (D-14)
        ("VorschubMax", False),
        ("Beschleunigung", False),
        ("Ruck", False),
        ("Durchmesser", False),
        ("YNutzen", False),  # nur an Y gezeigt (gui_details): an der Stirnseite (stirnseite)
    ],
    ART_POSITIONIEREN: [
        ("Endlos", False),
        ("NachDin", False),
        ("Geschwindigkeit", False),  # leer: export.VORGABE_DREHGESCHWINDIGKEIT (D-14)
        ("Beschleunigung", False),
        ("Ruck", False),
    ],
    ART_SPINDEL: [("Drehzahl", True), ("Hochlaufzeit", False), ("Leistung", False)],
    ART_REVOLVER: [("Schaltzeit", False), ("Vdi", False)],
}

# Home- und Wechselpunkt einer Linearachse: Schalter und Stellung (Spezifikation Simulation 13).
PUNKTE = ("HomeAn", "Home", "WechselAn", "Wechsel")

# Arten von Aufnahmen (gespeichert, deshalb ASCII).
AUFNAHME_WERKZEUG = "Werkzeug"
AUFNAHME_WERKSTUECK = "Werkstueck"
AUFNAHMEARTEN = [AUFNAHME_WERKZEUG, AUFNAHME_WERKSTUECK]

# Arten von Transformationen (gespeichert, deshalb ASCII) – bisher nur die
# schräge Achse; TRANSMIT, TRACYL, 5-Achs-TCP kämen hier dazu.
TRAFO_SCHRAEGE_ACHSE = "SchraegeAchse"
TRANSFORMATIONEN = [TRAFO_SCHRAEGE_ACHSE]

# Wo eine Achse sitzt – Ergebnis von rollen().
TISCH = "tisch"
KOPF = "kopf"

# Kennzeichen, an dem das Addon seine Gruppe „Maschine“ wiedererkennt.
TYP_MASCHINE = "CamAddon::Maschine"


# --- Anzeigetexte -------------------------------------------------------------


def art_text(art):
    """Anzeigename einer Betriebsart in der eingestellten Sprache."""
    return {
        ART_LINEAR: tr("art.linear"),
        ART_POSITIONIEREN: tr("art.positionieren"),
        ART_SPINDEL: tr("art.spindel"),
        ART_REVOLVER: tr("art.revolver"),
    }[art]


def aufnahmeart_text(art):
    """Anzeigename einer Aufnahmeart: „Werkzeug“ oder „Werkstück“."""
    return tr("aufnahme.werkzeug") if art == AUFNAHME_WERKZEUG else tr("aufnahme.werkstueck")


def trafo_text(art):
    """Anzeigename einer Transformation: „Schräge Achse“."""
    return {TRAFO_SCHRAEGE_ACHSE: tr("trafo.schraege_achse")}[art]


def wert_text(eigenschaft):
    """Anzeigename eines Kennwerts, bei festen Einheiten mit Einheit."""
    return {
        "Eilgang": tr("wert.eilgang"),
        "VorschubMax": tr("wert.vorschubmax"),
        "Beschleunigung": tr("wert.beschleunigung"),
        "Ruck": tr("wert.ruck"),
        "Endlos": tr("wert.endlos"),
        "NachDin": tr("wert.nach_din"),
        "YNutzen": tr("wert.y_nutzen"),
        "Durchmesser": tr("wert.durchmesser"),
        "Geschwindigkeit": tr("wert.geschwindigkeit"),
        "Drehzahl": tr("wert.drehzahl"),
        "Hochlaufzeit": tr("wert.hochlaufzeit"),
        "Leistung": tr("wert.leistung"),
        "Schaltzeit": tr("wert.schaltzeit"),
        "Vdi": tr("wert.vdi"),
    }[eigenschaft]


# --- Die vier Objektarten -----------------------------------------------------
#
# FreeCAD-Objekte aus Python bekommen einen „Proxy“: eine Python-Klasse, die
# die Eigenschaften anlegt und auf Änderungen reagiert. Die Daten selbst
# liegen in den Eigenschaften, nicht im Proxy.

# Modi für FreeCADs setEditorMode: wie eine Eigenschaft im Eigenschaften-Editor steht.
_SICHTBAR = 0
_AUSGEBLENDET = 2


class _Proxy:
    """Gemeinsame Grundlage der Proxys.

    FreeCAD speichert beim Sichern des Dokuments auch den Zustand des Proxys
    (dumps/loads). Unsere Proxys haben keinen eigenen Zustand – alles steht in
    den Eigenschaften –, deshalb gibt es nichts zu speichern.
    """

    def dumps(self):
        return None

    def loads(self, _zustand):
        return None


def _lege_eigenschaften_an(objekt, gruppe, eigenschaften):
    """Legt die fehlenden Eigenschaften an: [(Typ, Name, Beschreibung), …].

    `gruppe` ist die Überschrift, unter der sie im Eigenschaften-Editor stehen.
    """
    for typ, name, beschreibung in eigenschaften:
        if name not in objekt.PropertiesList:
            objekt.addProperty(typ, name, gruppe, beschreibung)


class Maschine(_Proxy):
    """Proxy der Gruppe „Maschine“, die Betriebsarten, Aufnahmen und Transformationen enthält."""

    def __init__(self, objekt):
        objekt.Proxy = self
        _lege_eigenschaften_an(
            objekt,
            "Maschine",
            [("App::PropertyString", "Typ", tr("eigenschaft.maschine.typ"))],
        )
        objekt.Typ = TYP_MASCHINE
        self.onDocumentRestored(objekt)

    def onDocumentRestored(self, objekt):
        # Das Kennzeichen braucht niemand zu sehen oder zu ändern.
        objekt.setEditorMode("Typ", _AUSGEBLENDET)
        # Worin der Werkzeugwechselpunkt gezählt wird (Manuel, 2026-10-03: „der
        # Werkzeugwechselpunkt sollte MKS, also nicht WKS sein … oder es sollte wechselbar
        # sein“) – ältere Maschinen bekommen es beim Laden, gezählt in MKS wie bisher.
        if "WechselBezug" not in objekt.PropertiesList:
            objekt.addProperty(
                "App::PropertyEnumeration",
                "WechselBezug",
                "Maschine",
                tr("eigenschaft.wechsel_bezug"),
            )
            objekt.WechselBezug = list(WECHSEL_BEZUEGE)
            objekt.WechselBezug = WECHSEL_MKS
        # Wie lange ein Werkzeugwechsel selbst dauert (s; Spezifikation Simulation 13) – 0: nicht
        # gezählt, wie bisher.
        if "Wechselzeit" not in objekt.PropertiesList:
            objekt.addProperty(
                "App::PropertyFloat", "Wechselzeit", "Maschine", tr("eigenschaft.wechselzeit")
            )
            objekt.Wechselzeit = 0.0


# Worin Home- und Wechselpunkt zählen (gespeichert, deshalb ASCII): MKS – Maschinenkoordinaten,
# wie der Verfahrweg; WKS – Werkstückkoordinaten, ab dem Nullpunkt des Jobs, die Spitze des
# Werkzeugs (nur der Wechselpunkt; Home zählt immer in MKS).
WECHSEL_MKS = "MKS"
WECHSEL_WKS = "WKS"
WECHSEL_BEZUEGE = (WECHSEL_MKS, WECHSEL_WKS)


# Der Schwenkdatensatz für den Schwenkzyklus der Steuerung (Siemens CYCLE800 _TC): sein Name –
# leer: die Maschine hat einen einzigen –, und worauf sich die Vorzugsrichtung _DIR bezieht
# (Rundachse 1 oder 2; bei der Inbetriebnahme im Schwenkdatensatz eingestellt). Manuel,
# 2026-10-04: „das muss je nach Maschine entschieden werden … das ist ja in der
# Maschinenkonfiguration eingerichtet“.
SCHWENK_BEZUEGE = (1, 2)


def schwenkdatensatz(maschine):
    """Der Name des Schwenkdatensatzes (CYCLE800 _TC) – leer: der einzige der Maschine."""
    return str(getattr(maschine, "Schwenkdatensatz", "") or "").strip()


def schwenk_bezug(maschine):
    """Auf welche Rundachse (1 oder 2) sich die Vorzugsrichtung (_DIR) bezieht – ohne Angabe 1."""
    try:
        wert = int(getattr(maschine, "SchwenkBezug", 1) or 1)
    except (TypeError, ValueError):
        return 1
    return wert if wert in SCHWENK_BEZUEGE else 1


def setze_schwenkdaten(maschine, datensatz, bezug):
    """Trägt Schwenkdatensatz und Richtungsbezug ein (legt die Eigenschaften an, wo nötig)."""
    if "Schwenkdatensatz" not in maschine.PropertiesList:
        maschine.addProperty(
            "App::PropertyString",
            "Schwenkdatensatz",
            "Maschine",
            tr("eigenschaft.schwenkdatensatz"),
        )
    if "SchwenkBezug" not in maschine.PropertiesList:
        maschine.addProperty(
            "App::PropertyInteger", "SchwenkBezug", "Maschine", tr("eigenschaft.schwenk_bezug")
        )
    maschine.Schwenkdatensatz = str(datensatz or "").strip()
    maschine.SchwenkBezug = int(bezug) if int(bezug) in SCHWENK_BEZUEGE else 1


def wechselzeit(maschine):
    """Wie lange ein Werkzeugwechsel dauert (s) – 0 ohne Angabe."""
    return max(0.0, float(getattr(maschine, "Wechselzeit", 0.0) or 0.0))


def wechsel_bezug(maschine):
    """WECHSEL_MKS oder WECHSEL_WKS – ohne Eigenschaft (ältere Maschine): MKS."""
    wert = str(getattr(maschine, "WechselBezug", WECHSEL_MKS) or WECHSEL_MKS)
    return wert if wert in WECHSEL_BEZUEGE else WECHSEL_MKS


def wechselpunkt(maschine):
    """{Programmname: Stellung (mm)} der Linearachsen, die einen eigenen Wechselpunkt haben –
    sonst ihr Home-Punkt; leer, wenn keine einen hat. Gezählt wie wechsel_bezug() sagt; X der
    Drehmaschine als Radius (wie gespeichert)."""
    ergebnis = {}
    for ba in betriebsarten(maschine):
        if ba.Art != ART_LINEAR:
            continue
        if getattr(ba, "WechselAn", False):
            ergebnis[programmname(ba)] = float(ba.Wechsel)
        elif getattr(ba, "HomeAn", False) and wechsel_bezug(maschine) == WECHSEL_MKS:
            ergebnis[programmname(ba)] = float(ba.Home)
    return ergebnis


class Betriebsart(_Proxy):
    """Proxy einer Betriebsart: Gelenk, Art, NC-Name und Kennwerte."""

    def __init__(self, objekt):
        objekt.Proxy = self
        _lege_eigenschaften_an(
            objekt,
            "Betriebsart",
            [
                ("App::PropertyLink", "Gelenk", tr("eigenschaft.gelenk")),
                ("App::PropertyEnumeration", "Art", tr("eigenschaft.art")),
                ("App::PropertyString", "NcName", tr("eigenschaft.ncname")),
            ],
        )
        _lege_eigenschaften_an(
            objekt,
            "Werte",
            [
                ("App::PropertyFloat", "Eilgang", tr("eigenschaft.eilgang")),
                ("App::PropertyFloat", "VorschubMax", tr("eigenschaft.vorschubmax")),
                ("App::PropertyFloat", "Beschleunigung", tr("eigenschaft.beschleunigung")),
                ("App::PropertyFloat", "Ruck", tr("eigenschaft.ruck")),
                ("App::PropertyBool", "Endlos", tr("eigenschaft.endlos")),
                ("App::PropertyFloat", "Geschwindigkeit", tr("eigenschaft.geschwindigkeit")),
                ("App::PropertyFloat", "Drehzahl", tr("eigenschaft.drehzahl")),
                ("App::PropertyFloat", "Hochlaufzeit", tr("eigenschaft.hochlaufzeit")),
                ("App::PropertyFloat", "Schaltzeit", tr("eigenschaft.schaltzeit")),
            ],
        )
        self._neue_werte(objekt)
        objekt.Art = BETRIEBSARTEN  # legt die Auswahlliste fest
        self._nur_passende_werte_zeigen(objekt)

    def onChanged(self, objekt, eigenschaft):
        if eigenschaft == "Art":
            self._nur_passende_werte_zeigen(objekt)

    def onDocumentRestored(self, objekt):
        self._neue_werte(objekt)
        self._nur_passende_werte_zeigen(objekt)

    @staticmethod
    def _neue_werte(objekt):
        """Kennwerte, die später dazukamen – auch in Maschinen, die davor gespeichert sind."""
        _lege_eigenschaften_an(
            objekt,
            "Werte",
            [
                # X einer Drehmaschine als Durchmesser (Manuel, 2026-09-30, P-2026-09-30-54).
                ("App::PropertyBool", "Durchmesser", tr("eigenschaft.durchmesser")),
                # VDI-Größe des Revolvers – für die Halter-Vorlagen (P-2026-09-30-70).
                ("App::PropertyFloat", "Vdi", tr("eigenschaft.vdi")),
                # Home- und Wechselpunkt einer Linearachse (Spezifikation Simulation 13,
                # P-2026-10-02-48): Stellung am Gelenk; „…An“ aus: keiner – 0 ist eine Stellung.
                ("App::PropertyBool", "HomeAn", tr("eigenschaft.home_an")),
                ("App::PropertyFloat", "Home", tr("eigenschaft.home")),
                ("App::PropertyBool", "WechselAn", tr("eigenschaft.wechsel_an")),
                ("App::PropertyFloat", "Wechsel", tr("eigenschaft.wechsel")),
                # Nennleistung einer Spindel – für „Schruppwerte planen“ (Durchsicht D-20).
                ("App::PropertyFloat", "Leistung", tr("eigenschaft.leistung")),
            ],
        )
        # Zählt die Steuerung die Rundachse nach DIN 66217 (postprozessor: C der Rundum-Bahnen)?
        # Vorbelegt an; aus, wenn die Maschine andersherum dreht (Manuel, 2026-10-05: „es muss
        # einstellbar bleiben … der Haken muss raus, wenn nicht nach DIN gedreht wird“). 0.193.1
        # hatte „Gegenlaeufig“ – das fällt weg.
        if "NachDin" not in objekt.PropertiesList:
            objekt.addProperty("App::PropertyBool", "NachDin", "Werte", tr("eigenschaft.nach_din"))
            objekt.NachDin = True
        if "Gegenlaeufig" in objekt.PropertiesList:
            objekt.removeProperty("Gegenlaeufig")
        # So viel Prozent ihres Wegs fährt Y an der Stirnseite, bevor C hilft (Manuel,
        # 2026-10-05: „bis zu einem Verfahrweg von maximal 85 %“, einstellbar).
        if "YNutzen" not in objekt.PropertiesList:
            objekt.addProperty("App::PropertyFloat", "YNutzen", "Werte", tr("eigenschaft.y_nutzen"))
            objekt.YNutzen = 85.0

    @staticmethod
    def _nur_passende_werte_zeigen(objekt):
        """Im Eigenschaften-Editor nur die Kennwerte zeigen, die zur Art gehören."""
        passend = {name for name, _pflicht in WERTE[objekt.Art]}
        alle = {name for liste in WERTE.values() for name, _pflicht in liste}
        # Home und Wechsel trägt „Maschine bearbeiten“ ein; im Editor nur bei Linear zu sehen.
        alle |= set(PUNKTE)
        if objekt.Art == ART_LINEAR:
            passend |= set(PUNKTE)
        # Beim Laden einer älteren Maschine fehlen spätere Kennwerte noch („Durchmesser“),
        # bis onDocumentRestored sie anlegt.
        for name in alle & set(objekt.PropertiesList):
            objekt.setEditorMode(name, _SICHTBAR if name in passend else _AUSGEBLENDET)


class Aufnahme(_Proxy):
    """Proxy einer Werkzeug- oder Werkstückaufnahme."""

    def __init__(self, objekt):
        objekt.Proxy = self
        _lege_eigenschaften_an(
            objekt,
            "Aufnahme",
            [
                ("App::PropertyString", "Bezeichnung", tr("eigenschaft.bezeichnung")),
                # LinkGlobal, weil das LCS in einem Bauteil liegt (eigener
                # Gültigkeitsbereich) – ein einfacher Link wäre „out of scope“.
                ("App::PropertyLinkGlobal", "Lcs", tr("eigenschaft.lcs")),
                ("App::PropertyEnumeration", "Art", tr("eigenschaft.aufnahmeart")),
                ("App::PropertyLink", "Spindel", tr("eigenschaft.spindel")),
                ("App::PropertyInteger", "Platz", tr("eigenschaft.platz")),
            ],
        )
        objekt.Art = AUFNAHMEARTEN  # legt die Auswahlliste fest

    def onDocumentRestored(self, objekt):
        _bestueckung_verbergen(objekt)


class Transformation(_Proxy):
    """Proxy einer Transformation der Steuerung – bisher nur die schräge Achse.

    Sie verweist auf zwei Betriebsarten der Art Linear: die schräge Achse und
    die, die beim Fahren der schrägen mitfährt (ausgleicht), dazu die Namen
    beider im Programm. Der Winkel steht nicht hier, sondern in der Baugruppe
    – in der Richtung der Gelenke (Spezifikation W-001, Abschnitt 7c).
    """

    def __init__(self, objekt):
        objekt.Proxy = self
        _lege_eigenschaften_an(
            objekt,
            "Transformation",
            [
                ("App::PropertyEnumeration", "Art", tr("eigenschaft.transformation")),
                ("App::PropertyLink", "Schraeg", tr("eigenschaft.schraeg")),
                ("App::PropertyLink", "Ausgleich", tr("eigenschaft.ausgleich")),
                ("App::PropertyString", "NameSchraeg", tr("eigenschaft.name_schraeg")),
                ("App::PropertyString", "NameAusgleich", tr("eigenschaft.name_ausgleich")),
            ],
        )
        objekt.Art = TRANSFORMATIONEN  # legt die Auswahlliste fest


def ist_betriebsart(objekt):
    return isinstance(getattr(objekt, "Proxy", None), Betriebsart)


def ist_aufnahme(objekt):
    return isinstance(getattr(objekt, "Proxy", None), Aufnahme)


def ist_transformation(objekt):
    return isinstance(getattr(objekt, "Proxy", None), Transformation)


# --- Anlegen, finden, benennen ------------------------------------------------


def finde_maschine(assembly):
    """Das Maschinenobjekt einer Assembly, oder None."""
    return next((o for o in assembly.Group if getattr(o, "Typ", None) == TYP_MASCHINE), None)


def lege_maschine_an(assembly):
    """Legt das Maschinenobjekt in der Assembly an – oder gibt das vorhandene zurück."""
    vorhanden = finde_maschine(assembly)
    if vorhanden is not None:
        return vorhanden
    objekt = assembly.newObject("App::DocumentObjectGroupPython", "Maschine")
    Maschine(objekt)
    objekt.Label = tr("maschine.standardname")
    return objekt


def assembly_von(maschine):
    """Die Assembly, in der ein Maschinenobjekt liegt."""
    return next((o for o in maschine.InList if o.TypeId == "Assembly::AssemblyObject"), None)


def betriebsarten(maschine):
    return [o for o in maschine.Group if ist_betriebsart(o)]


def aufnahmen(maschine):
    return [o for o in maschine.Group if ist_aufnahme(o)]


def transformationen(maschine):
    return [o for o in maschine.Group if ist_transformation(o)]


# Der Höchstvorschub einer neuen Linearachse, solange keiner eingetragen ist (mm/min) – mit ihm
# fahren die Bahnen im Freien (freiwege; Manuel, 2026-10-04: „wenn nichts drinnen steht ..
# dann halt 10 m/min als Standard setzen in der Maschine beim Anlegen“).
VORSCHUB_MAX_VORGABE = 10000.0


def neue_betriebsart(maschine, gelenk, art, nc_name):
    objekt = maschine.newObject("App::FeaturePython", "Betriebsart")
    Betriebsart(objekt)
    objekt.Gelenk = gelenk
    objekt.Art = art
    objekt.NcName = nc_name
    if art == ART_LINEAR and not float(getattr(objekt, "VorschubMax", 0.0) or 0.0):
        objekt.VorschubMax = VORSCHUB_MAX_VORGABE
    beschrifte(objekt)
    return objekt


# --- Vorschlag: Betriebsarten aus Gelenkart, Name und Richtung (Durchsicht W-004, D-25) ---

_SPINDEL_WORTE = ("spindel", "spindle")
_REVOLVER_WORTE = ("revolver", "turret")
# Ein Achsbuchstabe allein, vielleicht mit Nummer: „X“, „X-Schlitten“, „Achse B2“ – nicht
# das A in „Achse“.
_ACHSBUCHSTABE = re.compile(r"(?<![A-Za-z])([XYZABC])(\d*)(?![A-Za-z])")


def vorgeschlagene_art(achse):
    """Die Betriebsart, die zum Gelenk passt: ein Schiebegelenk linear; ein Drehgelenk mit
    „Spindel“ im Namen eine Spindel, mit „Revolver“ der Revolver, sonst Positionieren."""
    if achse.art == LINEAR:
        return ART_LINEAR
    name = achse.gelenk.Label.lower()
    if any(wort in name for wort in _SPINDEL_WORTE):
        return ART_SPINDEL
    if any(wort in name for wort in _REVOLVER_WORTE):
        return ART_REVOLVER
    return ART_POSITIONIEREN


def vorgeschlagener_name(maschine, achse, art):
    """Der NC-Name für eine neue Betriebsart: Spindeln S1, S2 …, der Revolver T; sonst der
    Achsbuchstabe aus dem Namen des Gelenks („X-Schlitten“ → X1) oder aus seiner Richtung
    (entlang X → X1, um Z gedreht → C1). Schon vergebene Namen zählen weiter (X2)."""
    vergeben = {ba.NcName for ba in betriebsarten(maschine)}
    if art == ART_REVOLVER:
        return "T" if "T" not in vergeben else _frei("T", vergeben, ab=2)
    if art == ART_SPINDEL:
        return _frei("S", vergeben)
    erlaubt = "XYZ" if art == ART_LINEAR else "ABC"
    for buchstabe, nummer in _ACHSBUCHSTABE.findall(achse.gelenk.Label):
        if buchstabe in erlaubt:
            if nummer and buchstabe + nummer not in vergeben:
                return buchstabe + nummer
            return _frei(buchstabe, vergeben)
    anteile = [abs(achse.richtung.x), abs(achse.richtung.y), abs(achse.richtung.z)]
    return _frei(erlaubt[anteile.index(max(anteile))], vergeben)


def _frei(buchstabe, vergeben, ab=1):
    """Der erste freie Name: „X1“, sonst „X2“ …"""
    nummer = ab
    while f"{buchstabe}{nummer}" in vergeben:
        nummer += 1
    return f"{buchstabe}{nummer}"


def schlage_betriebsarten_vor(maschine, kette):
    """Gibt jeder Achse ohne Betriebsart eine – Art und NC-Name wie vorgeschlagen, die
    Kennwerte leer (0 = unbekannt): Die trägt man ein, die Prüfung sagt, welche fehlen.
    Gibt die neuen Betriebsarten zurück."""
    mit_betriebsart = [ba.Gelenk for ba in betriebsarten(maschine)]
    neu = []
    for achse in kette.achsen:
        if any(gelenk == achse.gelenk for gelenk in mit_betriebsart):
            continue
        art = vorgeschlagene_art(achse)
        name = vorgeschlagener_name(maschine, achse, art)
        neu.append(neue_betriebsart(maschine, achse.gelenk, art, name))
    return neu


def neue_aufnahme(maschine, lcs, art, bezeichnung, spindel=None, platz=0):
    objekt = maschine.newObject("App::FeaturePython", "Aufnahme")
    Aufnahme(objekt)
    objekt.Lcs = lcs
    objekt.Art = art
    objekt.Spindel = spindel
    objekt.Platz = platz
    objekt.Bezeichnung = bezeichnung
    beschrifte(objekt)
    return objekt


def neue_schraege_achse(maschine, schraeg, ausgleich):
    """Legt eine schräge Achse an: `schraeg` fährt schräg, `ausgleich` fährt mit.

    Beide sind Betriebsarten der Art Linear. Die Namen im Programm sind
    vorbelegt – der NC-Name ohne Ziffern am Ende (Y1 → Y) – und änderbar.
    """
    objekt = maschine.newObject("App::FeaturePython", "Transformation")
    Transformation(objekt)
    objekt.Art = TRAFO_SCHRAEGE_ACHSE
    objekt.Schraeg = schraeg
    objekt.Ausgleich = ausgleich
    objekt.NameSchraeg = programmname(schraeg)
    objekt.NameAusgleich = programmname(ausgleich)
    beschrifte(objekt)
    return objekt


def programmname(ba):
    """Vorschlag für den Namen einer Achse im Programm: der NC-Name ohne Ziffern am
    Ende – Y1 → Y. Ein Name nur aus Ziffern bleibt, wie er ist."""
    if ba is None:
        return ""
    name = ba.NcName.strip()
    return name.rstrip("0123456789") or name


def name_von(objekt):
    """Der Name, den der Benutzer vergeben hat: NC-Name bzw. Bezeichnung.

    Für jedes andere Objekt die Beschriftung – im Eigenschaften-Editor lässt
    sich z. B. als Spindel ein beliebiges Objekt verlinken.
    """
    if ist_betriebsart(objekt):
        return objekt.NcName.strip() or "?"
    if ist_aufnahme(objekt) and objekt.Bezeichnung:
        return objekt.Bezeichnung
    if ist_transformation(objekt):
        return objekt.NameSchraeg.strip() or "?"
    return objekt.Label


def beschrifte(objekt):
    """Setzt die Beschriftung im Baum aus den Daten: „X1 · Linear“, „Futter · Werkstückaufnahme“.

    Der Name allein taugt nicht als Beschriftung: FreeCAD erlaubt keine
    Beschriftung doppelt und hängt sonst „001“ an – eine Aufnahme „Futter“
    neben dem Bauteil „Futter“ hieße „Futter001“.
    """
    if ist_betriebsart(objekt):
        objekt.Label = f"{name_von(objekt)} · {art_text(objekt.Art)}"
    elif ist_transformation(objekt):
        objekt.Label = f"{name_von(objekt)} · {trafo_text(objekt.Art)}"
    elif objekt.Art == AUFNAHME_WERKZEUG:
        objekt.Label = tr("aufnahme.beschriftung_werkzeug", name=name_von(objekt))
    else:
        objekt.Label = tr("aufnahme.beschriftung_werkstueck", name=name_von(objekt))


# --- Revolver -----------------------------------------------------------------


def platz_name(nummer):
    """Anzeigename eines Revolverplatzes: P1, P2, …"""
    return f"P{nummer}"


def plaetze(maschine, kette, revolver):
    """Die Plätze eines Revolvers, nach Nummer sortiert.

    Plätze sind alle Werkzeugaufnahmen im Glied, das die Achse des Revolvers
    bewegt.
    """
    achse = kette.achse_von(revolver.Gelenk)
    if achse is None:
        return []
    return sorted(
        (
            a
            for a in aufnahmen(maschine)
            if a.Art == AUFNAHME_WERKZEUG
            and a.Lcs is not None
            and kette.glied_von(a.Lcs) is achse.kind
        ),
        key=lambda a: a.Platz,
    )


# --- Revolverplätze -------------------------------------------------------------
#
# Welches Werkzeug auf welchem Platz steckt, legt jeder Job selbst fest (W-002 Stufe G,
# bestueckung.py) – die Maschine kennt nur ihre Plätze. 0.32.0 und 0.32.1 bestückten die
# Plätze in „Maschine bearbeiten“ (Stufe F, Eigenschaft „Werkzeug“); was dort steht, zählt
# nicht mehr und bleibt verborgen.

BESTUECKUNG = "Werkzeug"  # die Eigenschaft von Stufe F an alten Plätzen


def revolverplaetze(maschine, kette):
    """Die Plätze aller Revolver der Maschine – je Revolver nach Nummer."""
    return [
        platz
        for ba in betriebsarten(maschine)
        if ba.Art == ART_REVOLVER
        for platz in plaetze(maschine, kette, ba)
    ]


def vdi_groesse(maschine):
    """Die VDI-Größe der Revolver (Schaft-Ø der Halter, mm; die größte, wenn mehrere) – 0, wenn
    keine eingetragen ist. Die Halter-Vorlagen nehmen sie als Maß (halter.aus_vorlage)."""
    return max(
        (
            float(getattr(ba, "Vdi", 0) or 0)
            for ba in betriebsarten(maschine)
            if ba.Art == ART_REVOLVER
        ),
        default=0.0,
    )


def _bestueckung_verbergen(platz):
    """Die Bestückung von Stufe F an einem alten Platz zählt nicht mehr – nicht zeigen."""
    if BESTUECKUNG in platz.PropertiesList:
        platz.setEditorMode(BESTUECKUNG, _AUSGEBLENDET)


def ist_durchmesser(maschine, gelenk):
    """Zählt die Linearachse an `gelenk` als Durchmesser – X einer Drehmaschine, wie die
    Steuerung es zeigt und im Programm erwartet (Manuel, 2026-09-30: „Ja mit Umschalter
    wichtig ist ja nur was dann beim Postprozess raus kommt“)? Gerechnet wird immer im Radius;
    nur Anzeige und Eingabe verdoppeln."""
    if maschine is None or gelenk is None:
        return False
    return any(
        ba.Gelenk is gelenk and ba.Art == ART_LINEAR and getattr(ba, "Durchmesser", False)
        for ba in betriebsarten(maschine)
    )


def x_im_durchmesser(maschine):
    """Steht X im Programm als Durchmesser? Ja, wenn eine Linearachse, die im Programm X
    heißt (X1, X2 …), im Durchmesser zählt."""
    if maschine is None:
        return False
    return any(
        ba.Art == ART_LINEAR
        and getattr(ba, "Durchmesser", False)
        and programmname(ba).upper() == "X"
        for ba in betriebsarten(maschine)
    )


@dataclass
class Spindeln:
    """Welche Spindel was tut (spindeln()): die Hauptspindel und ihre C-Achse – an der
    Drehmaschine dreht sie das Teil, im Achsbetrieb positioniert sie es –, und die Antriebe der
    Werkzeuge, je mit der C-Achse, die das angetriebene Werkzeug ausrichtet (None ohne)."""

    haupt: object = None  # Betriebsart (Spindel) – oder None
    haupt_c: object = None  # Betriebsart (Positionieren) am selben Gelenk – oder None
    antriebe: list = field(default_factory=list)  # [(Spindel, Positionieren oder None)]

    def ist_antrieb_c(self, ba):
        """Richtet `ba` ein angetriebenes Werkzeug aus (keine Achse der Bahn)?"""
        return any(c is ba for _s, c in self.antriebe if c is not None)


def spindeln(maschine):
    """Spindeln der Maschine nach ihrer Aufgabe (Manuel, 2026-10-03: „es muss … ein S und ein
    C für die Hauptspindel geben und ein S und ein C für die angetriebenen Werkzeuge … der
    Postprozessor muss wissen, welche Achse was macht – in meinem Beispiel: C4 muss sich
    positionieren, das ist die Hauptspindel, und S1 muss die Drehzahl anmachen“). Ein Antrieb
    ist eine Spindel, an der eine Werkzeugaufnahme hängt; die Hauptspindel die erste andere –
    lieber eine mit C-Achse am selben Gelenk. Die C-Achse einer Spindel ist die Betriebsart
    „Positionieren“ an ihrem Gelenk."""
    ergebnis = Spindeln()
    if maschine is None:
        return ergebnis
    arten = betriebsarten(maschine)

    def c_von(spindel):
        return next(
            (
                ba
                for ba in arten
                if ba.Art == ART_POSITIONIEREN
                and spindel.Gelenk is not None
                and ba.Gelenk == spindel.Gelenk
            ),
            None,
        )

    antriebe = []
    for aufnahme in aufnahmen(maschine):
        spindel = getattr(aufnahme, "Spindel", None)
        if aufnahme.Art != AUFNAHME_WERKZEUG or spindel is None or not ist_betriebsart(spindel):
            continue
        if spindel.Art == ART_SPINDEL and all(s is not spindel for s in antriebe):
            antriebe.append(spindel)
    ergebnis.antriebe = [(s, c_von(s)) for s in antriebe]
    andere = [ba for ba in arten if ba.Art == ART_SPINDEL and all(ba is not s for s in antriebe)]
    mit_c = [ba for ba in andere if c_von(ba) is not None]
    ergebnis.haupt = (mit_c or andere or [None])[0]
    if ergebnis.haupt is not None:
        ergebnis.haupt_c = c_von(ergebnis.haupt)
    return ergebnis


def nc_nummer(ba):
    """Die Nummer im NC-Namen („S4“ → „4“), "" ohne."""
    return re.sub(r"\D", "", getattr(ba, "NcName", "") or "") if ba is not None else ""


def globale_platzierung(objekt):
    """Lage eines Objekts in Weltkoordinaten, durch alle umgebenden Parts hindurch."""
    eltern = objekt.Parents  # [(oberstes Objekt, "Pfad.zum.Objekt."), …]
    if eltern:
        wurzel, pfad = eltern[0]
        return wurzel.getPlacementOf(pfad)
    return objekt.Placement


def verteile_plaetze(maschine, kette, revolver, erstes_lcs, anzahl):
    """Legt Revolverplätze P1 … Pn gleichmäßig im Kreis um die Revolverachse an.

    P1 ist `erstes_lcs`; für die übrigen legt die Funktion je ein neues LCS
    im selben Bauteil an, um die Achse gedreht. Eine frühere Verteilung
    desselben Revolvers wird ersetzt. Gibt die Aufnahmen in Platzreihenfolge
    zurück.
    """
    achse = kette.achse_von(revolver.Gelenk)
    if achse is None or anzahl < 1:
        return []
    _entferne_fruehere_verteilung(maschine, kette, revolver, erstes_lcs)

    doc = maschine.Document
    bauteil = erstes_lcs.getParentGeoFeatureGroup()
    bauteil_lage = globale_platzierung(bauteil) if bauteil else FreeCAD.Placement()
    erstes_lage = globale_platzierung(erstes_lcs)
    ergebnis = []
    for nummer in range(1, anzahl + 1):
        if nummer == 1:
            lcs = erstes_lcs
        else:
            winkel = 360.0 * (nummer - 1) / anzahl
            drehung = FreeCAD.Placement(
                FreeCAD.Vector(), FreeCAD.Rotation(achse.richtung, winkel), achse.ursprung
            )
            lcs = doc.addObject("App::LocalCoordinateSystem", erstes_lcs.Name + "_")
            lcs.Label = f"{erstes_lcs.Label}_{platz_name(nummer)}"
            if bauteil:
                bauteil.addObject(lcs)
            # Gedreht wird in Weltkoordinaten; das LCS liegt aber im Bauteil.
            lcs.Placement = bauteil_lage.inverse() * drehung * erstes_lage
        ergebnis.append(
            neue_aufnahme(maschine, lcs, AUFNAHME_WERKZEUG, platz_name(nummer), platz=nummer)
        )
    return ergebnis


def _entferne_fruehere_verteilung(maschine, kette, revolver, erstes_lcs):
    """Entfernt die Plätze des Revolvers und die LCS, die die Verteilhilfe angelegt hatte.

    Von Hand angelegte LCS bleiben: Die Verteilhilfe erkennt ihre eigenen an
    der Beschriftung „<erstes LCS>_P…“.
    """
    doc = maschine.Document
    for platz in plaetze(maschine, kette, revolver):
        doc.removeObject(platz.Name)
    praefix = erstes_lcs.Label + "_P"
    angelegt = [
        o.Name
        for o in doc.Objects
        if o.isDerivedFrom("App::LocalCoordinateSystem") and o.Label.startswith(praefix)
    ]
    for name in angelegt:
        # Ein LCS nimmt beim Löschen seine Achsen und Ebenen mit – deshalb über
        # die Namen gehen und nur löschen, was noch da ist.
        if doc.getObject(name) is not None:
            doc.removeObject(name)


# --- Auswerten ----------------------------------------------------------------


def rollen(kette, maschine):
    """Ob eine Achse im Tisch oder im Kopf sitzt.

    Eine Achse auf dem Weg von einer Werkstückaufnahme zum Bett sitzt im
    Tisch, eine auf dem Weg von einer Werkzeugaufnahme im Kopf. Liegt sie auf
    beiden Wegen, ist das mehrdeutig – dann bekommt sie keine Rolle, und es
    gibt eine Meldung.

    Gibt ({Gelenk: TISCH oder KOPF}, [Meldung]) zurück.
    """
    gefunden = {}  # Gelenk -> {TISCH, KOPF}
    for aufnahme in aufnahmen(maschine):
        glied = kette.glied_von(aufnahme.Lcs) if aufnahme.Lcs is not None else None
        if glied is None:
            continue
        rolle = TISCH if aufnahme.Art == AUFNAHME_WERKSTUECK else KOPF
        for achse in kette.pfad_zum_bett(glied):
            gefunden.setdefault(achse.gelenk, set()).add(rolle)

    eindeutig, meldungen = {}, []
    for gelenk, gefundene_rollen in gefunden.items():
        if len(gefundene_rollen) == 1:
            eindeutig[gelenk] = next(iter(gefundene_rollen))
        else:
            meldungen.append(meldung("maschine.rolle_mehrdeutig", gelenk=gelenk.Label))
    return eindeutig, meldungen


def pruefe(maschine, kette=None):
    """Alle Meldungen zum Maschinenobjekt, als fertige Sätze: erst Warnungen, dann Hinweise."""
    if kette is None:
        kette = kette_modul.lies_kette(assembly_von(maschine))
    from . import schraege_achse  # braucht dieses Modul selbst

    meldungen = (
        _pruefe_betriebsarten(maschine, kette)
        + _pruefe_aufnahmen(maschine, kette)
        + _pruefe_revolver(maschine, kette)
        + schraege_achse.pruefe(maschine, kette)
        + rollen(kette, maschine)[1]
    )
    # Hinweise ans Ende. sorted() ist stabil, die Reihenfolge bleibt sonst erhalten.
    return sorted(meldungen, key=lambda x: x.schwere == HINWEIS)


def _pruefe_betriebsarten(maschine, kette):
    meldungen = []
    gleiche_namen = {}  # NC-Name in Großbuchstaben -> Betriebsarten
    je_gelenk = {}  # Gelenk -> seine Betriebsarten

    for ba in betriebsarten(maschine):
        name = ba.NcName.strip()
        if name:
            gleiche_namen.setdefault(name.upper(), []).append(ba)
        else:
            meldungen.append(meldung("maschine.name_fehlt", bezug=ba, eintrag=name_von(ba)))

        if ba.Gelenk is None:
            meldungen.append(meldung("maschine.gelenk_fehlt", bezug=ba, name=name_von(ba)))
            continue
        achse = kette.achse_von(ba.Gelenk)
        if achse is None:
            meldungen.append(
                meldung(
                    "maschine.gelenk_keine_achse",
                    bezug=ba,
                    name=name_von(ba),
                    gelenk=ba.Gelenk.Label,
                )
            )
            continue
        if ba.Art not in ERLAUBT[achse.art]:
            meldungen.append(
                meldung(
                    "maschine.art_passt_nicht",
                    bezug=ba,
                    name=name_von(ba),
                    gelenk=ba.Gelenk.Label,
                    art=art_text(ba.Art),
                )
            )
        je_gelenk.setdefault(ba.Gelenk, []).append(ba)
        for eigenschaft, pflicht in WERTE[ba.Art]:
            if pflicht and not getattr(ba, eigenschaft):
                meldungen.append(
                    meldung(
                        "maschine.pflichtwert_fehlt",
                        bezug=ba,
                        name=name_von(ba),
                        wert=wert_text(eigenschaft),
                    )
                )

    # NC-Namen sind nicht case-sensitiv: „x1“ und „X1“ sind derselbe Name.
    for gleiche in gleiche_namen.values():
        if len(gleiche) > 1:
            meldungen.append(
                meldung("maschine.name_doppelt", bezug=gleiche[1], name=name_von(gleiche[0]))
            )
    for gelenk, liste in je_gelenk.items():
        arten = [ba.Art for ba in liste]
        if len(set(arten)) < len(arten):
            meldungen.append(meldung("maschine.art_doppelt", bezug=liste[-1], gelenk=gelenk.Label))
    return meldungen


def _pruefe_aufnahmen(maschine, kette):
    meldungen = []
    for aufnahme in aufnahmen(maschine):
        if aufnahme.Lcs is None:
            meldungen.append(meldung("maschine.lcs_fehlt", bezug=aufnahme, name=name_von(aufnahme)))
        elif kette.glied_von(aufnahme.Lcs) is None:
            meldungen.append(
                meldung("maschine.lcs_ausserhalb", bezug=aufnahme, name=name_von(aufnahme))
            )
        spindel = aufnahme.Spindel  # im Eigenschaften-Editor lässt sich jedes Objekt verlinken
        if spindel is not None and not (ist_betriebsart(spindel) and spindel.Art == ART_SPINDEL):
            meldungen.append(
                meldung("maschine.spindel_keine_spindel", bezug=aufnahme, name=name_von(aufnahme))
            )

    vorhandene_arten = {a.Art for a in aufnahmen(maschine)}
    if AUFNAHME_WERKZEUG not in vorhandene_arten:
        meldungen.append(meldung("maschine.keine_werkzeugaufnahme", HINWEIS))
    if AUFNAHME_WERKSTUECK not in vorhandene_arten:
        meldungen.append(meldung("maschine.keine_werkstueckaufnahme", HINWEIS))
    return meldungen


def _pruefe_revolver(maschine, kette):
    meldungen = []
    for ba in betriebsarten(maschine):
        if ba.Art != ART_REVOLVER:
            continue
        nummern = [platz.Platz for platz in plaetze(maschine, kette, ba)]
        if not nummern:
            meldungen.append(meldung("maschine.revolver_ohne_plaetze", bezug=ba, name=name_von(ba)))
        elif 0 in nummern or len(set(nummern)) < len(nummern):
            meldungen.append(meldung("maschine.plaetze_nummern", bezug=ba, name=name_von(ba)))
    return meldungen
