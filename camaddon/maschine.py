# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Maschinenobjekt: alle Maschinendaten einer Assembly an einer Stelle.

Aufbau im Dokument (Spezifikation W-001, Abschnitt 5):

    Assembly
    └── Maschine                (Gruppe, eine je Assembly)
        ├── X1                  (Betriebsart: verweist auf ein Gelenk)
        ├── S4, C4              (zwei Betriebsarten desselben Gelenks)
        └── Revolver            (Aufnahme: verweist auf ein LCS)

Jede Betriebsart und jede Aufnahme ist ein eigenes Objekt: So stehen sie
lesbar im Baum, Rückgängig funktioniert von selbst, und ein gelöschtes Gelenk
lässt nur einen leeren Verweis zurück statt Daten zu verlieren.

Unbekannte Kennwerte sind 0. Keiner dieser Werte kann an einer echten
Maschine 0 sein, also ist 0 als „unbekannt“ eindeutig.

Läuft ohne Oberfläche.
"""

from . import kette as kette_modul
from .kette import DREH, HINWEIS, LINEAR, meldung
from .sprache import tr

# Betriebsarten (Werte der Eigenschaft „Art“; ASCII, weil sie gespeichert
# werden – angezeigt wird die Übersetzung).
ART_LINEAR = "Linear"
ART_POSITIONIEREN = "Positionieren"
ART_SPINDEL = "Spindel"
BETRIEBSARTEN = [ART_LINEAR, ART_POSITIONIEREN, ART_SPINDEL]

# Welche Betriebsarten zu welcher Gelenkart passen.
ERLAUBT = {LINEAR: [ART_LINEAR], DREH: [ART_POSITIONIEREN, ART_SPINDEL]}

# Kennwerte je Betriebsart: (Eigenschaft, Pflicht). Einheiten wie im
# Datenblatt, siehe Spezifikation Abschnitt 4.
WERTE = {
    ART_LINEAR: [("Eilgang", True), ("VorschubMax", False), ("Beschleunigung", False), ("Ruck", False)],
    ART_POSITIONIEREN: [
        ("Endlos", False),
        ("Geschwindigkeit", True),
        ("Beschleunigung", False),
        ("Ruck", False),
    ],
    ART_SPINDEL: [("Drehzahl", True), ("Hochlaufzeit", False)],
}

AUFNAHME_WERKZEUG = "Werkzeug"
AUFNAHME_WERKSTUECK = "Werkstueck"
AUFNAHMEARTEN = [AUFNAHME_WERKZEUG, AUFNAHME_WERKSTUECK]

# Ergebnis der Tisch/Kopf-Zuordnung.
TISCH = "tisch"
KOPF = "kopf"


def art_text(art):
    """Anzeigename einer Betriebsart in der aktuellen Sprache."""
    return {
        ART_LINEAR: tr("art.linear"),
        ART_POSITIONIEREN: tr("art.positionieren"),
        ART_SPINDEL: tr("art.spindel"),
    }[art]


def wert_text(eigenschaft):
    """Anzeigename eines Kennwerts mit Einheit, in der aktuellen Sprache."""
    return {
        "Eilgang": tr("wert.eilgang"),
        "VorschubMax": tr("wert.vorschubmax"),
        "Beschleunigung": tr("wert.beschleunigung"),
        "Ruck": tr("wert.ruck"),
        "Endlos": tr("wert.endlos"),
        "Geschwindigkeit": tr("wert.geschwindigkeit"),
        "Drehzahl": tr("wert.drehzahl"),
        "Hochlaufzeit": tr("wert.hochlaufzeit"),
    }[eigenschaft]


def _eigenschaft(objekt, typ, name, gruppe, doku):
    if name not in objekt.PropertiesList:
        objekt.addProperty(typ, name, gruppe, doku)


class Maschine:
    """Proxy der Gruppe „Maschine“."""

    def __init__(self, objekt):
        objekt.Proxy = self
        _eigenschaft(objekt, "App::PropertyString", "Typ", "Maschine", tr("eigenschaft.maschine.typ"))
        objekt.Typ = "CamAddon::Maschine"
        self.onDocumentRestored(objekt)

    def onDocumentRestored(self, objekt):
        # Nur ein Erkennungszeichen – im Eigenschaften-Editor nicht zeigen.
        objekt.setEditorMode("Typ", 2)

    def dumps(self):
        return None

    def loads(self, _zustand):
        return None


class Betriebsart:
    def __init__(self, objekt):
        objekt.Proxy = self
        _eigenschaft(objekt, "App::PropertyLink", "Gelenk", "Betriebsart", tr("eigenschaft.gelenk"))
        _eigenschaft(objekt, "App::PropertyEnumeration", "Art", "Betriebsart", tr("eigenschaft.art"))
        objekt.Art = BETRIEBSARTEN
        _eigenschaft(objekt, "App::PropertyString", "NcName", "Betriebsart", tr("eigenschaft.ncname"))
        _eigenschaft(objekt, "App::PropertyFloat", "Eilgang", "Werte", tr("eigenschaft.eilgang"))
        _eigenschaft(objekt, "App::PropertyFloat", "VorschubMax", "Werte", tr("eigenschaft.vorschubmax"))
        _eigenschaft(objekt, "App::PropertyFloat", "Beschleunigung", "Werte", tr("eigenschaft.beschleunigung"))
        _eigenschaft(objekt, "App::PropertyFloat", "Ruck", "Werte", tr("eigenschaft.ruck"))
        _eigenschaft(objekt, "App::PropertyBool", "Endlos", "Werte", tr("eigenschaft.endlos"))
        _eigenschaft(objekt, "App::PropertyFloat", "Geschwindigkeit", "Werte", tr("eigenschaft.geschwindigkeit"))
        _eigenschaft(objekt, "App::PropertyFloat", "Drehzahl", "Werte", tr("eigenschaft.drehzahl"))
        _eigenschaft(objekt, "App::PropertyFloat", "Hochlaufzeit", "Werte", tr("eigenschaft.hochlaufzeit"))
        self._sichtbarkeit(objekt)

    def onChanged(self, objekt, eigenschaft):
        if eigenschaft == "Art":
            self._sichtbarkeit(objekt)

    def onDocumentRestored(self, objekt):
        self._sichtbarkeit(objekt)

    @staticmethod
    def _sichtbarkeit(objekt):
        """Im Eigenschaften-Editor nur die Werte zeigen, die zur Art gehören."""
        if "Art" not in objekt.PropertiesList:
            return
        passend = {name for name, _pflicht in WERTE.get(objekt.Art, [])}
        for liste in WERTE.values():
            for name, _pflicht in liste:
                if name in objekt.PropertiesList:
                    objekt.setEditorMode(name, 0 if name in passend else 2)

    def dumps(self):
        return None

    def loads(self, _zustand):
        return None


class Aufnahme:
    def __init__(self, objekt):
        objekt.Proxy = self
        _eigenschaft(objekt, "App::PropertyLink", "Lcs", "Aufnahme", tr("eigenschaft.lcs"))
        _eigenschaft(objekt, "App::PropertyEnumeration", "Art", "Aufnahme", tr("eigenschaft.aufnahmeart"))
        objekt.Art = AUFNAHMEARTEN
        _eigenschaft(objekt, "App::PropertyLink", "Spindel", "Aufnahme", tr("eigenschaft.spindel"))

    def dumps(self):
        return None

    def loads(self, _zustand):
        return None


# --- Anlegen und Finden ----------------------------------------------------


def assembly_von(maschine):
    return next((o for o in maschine.InList if o.TypeId == "Assembly::AssemblyObject"), None)


def ist_maschine(objekt):
    return getattr(objekt, "Typ", None) == "CamAddon::Maschine"


def finde_maschine(assembly):
    return next((o for o in assembly.Group if ist_maschine(o)), None)


def lege_maschine_an(assembly):
    """Legt das Maschinenobjekt in der Assembly an (oder gibt das vorhandene zurück)."""
    vorhanden = finde_maschine(assembly)
    if vorhanden:
        return vorhanden
    objekt = assembly.newObject("App::DocumentObjectGroupPython", "Maschine")
    Maschine(objekt)
    objekt.Label = tr("maschine.standardname")
    return objekt


def neue_betriebsart(maschine, gelenk, art, nc_name):
    objekt = maschine.newObject("App::FeaturePython", "Betriebsart")
    Betriebsart(objekt)
    objekt.Gelenk = gelenk
    objekt.Art = art
    objekt.NcName = nc_name
    objekt.Label = nc_name
    return objekt


def neue_aufnahme(maschine, lcs, art, name, spindel=None):
    objekt = maschine.newObject("App::FeaturePython", "Aufnahme")
    Aufnahme(objekt)
    objekt.Lcs = lcs
    objekt.Art = art
    objekt.Spindel = spindel
    objekt.Label = name
    return objekt


def betriebsarten(maschine):
    return [o for o in maschine.Group if isinstance(getattr(o, "Proxy", None), Betriebsart)]


def aufnahmen(maschine):
    return [o for o in maschine.Group if isinstance(getattr(o, "Proxy", None), Aufnahme)]


# --- Auswerten -------------------------------------------------------------


def rollen(kette, maschine):
    """Tisch oder Kopf je Gelenk, aus den Wegen der Aufnahmen zum Bett.

    Liefert ({gelenk_objekt: TISCH|KOPF}, meldungen). Ein Gelenk auf dem Weg
    zu einer Werkstück- und zugleich zu einer Werkzeugaufnahme ist
    mehrdeutig und bekommt keine Rolle.
    """
    gefunden = {}
    for aufnahme in aufnahmen(maschine):
        if aufnahme.Lcs is None:
            continue
        glied = kette.glied_von(aufnahme.Lcs)
        if glied is None:
            continue
        rolle = TISCH if aufnahme.Art == AUFNAHME_WERKSTUECK else KOPF
        for gelenk in kette.pfad_zum_festen_glied(glied):
            gefunden.setdefault(gelenk.objekt, set()).add(rolle)
    ergebnis, meldungen = {}, []
    for gelenk, menge in gefunden.items():
        if len(menge) == 1:
            ergebnis[gelenk] = menge.pop()
        else:
            meldungen.append(meldung("maschine.rolle_mehrdeutig", gelenk=gelenk.Label))
    return ergebnis, meldungen


def pruefe(maschine, kette=None):
    """Alle Meldungen zum Maschinenobjekt, in ganzen Sätzen."""
    if kette is None:
        kette = kette_modul.lies_kette(assembly_von(maschine))
    meldungen = []
    gelenk_art = {g.objekt: g.art for g in kette.gelenke}
    namen = {}
    arten_je_gelenk = {}

    for ba in betriebsarten(maschine):
        name = ba.NcName.strip()
        if not name:
            meldungen.append(meldung("maschine.name_fehlt", eintrag=ba.Label))
        else:
            namen.setdefault(name.upper(), []).append(ba)
        if ba.Gelenk is None:
            meldungen.append(meldung("maschine.gelenk_fehlt", name=ba.Label))
            continue
        art = gelenk_art.get(ba.Gelenk)
        if art is None:
            meldungen.append(meldung("maschine.gelenk_keine_achse", name=ba.Label, gelenk=ba.Gelenk.Label))
            continue
        if ba.Art not in ERLAUBT[art]:
            meldungen.append(
                meldung(
                    "maschine.art_passt_nicht",
                    name=ba.Label,
                    gelenk=ba.Gelenk.Label,
                    art=art_text(ba.Art),
                )
            )
        arten_je_gelenk.setdefault(ba.Gelenk, []).append(ba)
        for eigenschaft, pflicht in WERTE[ba.Art]:
            if pflicht and not getattr(ba, eigenschaft):
                meldungen.append(
                    meldung(
                        "maschine.pflichtwert_fehlt",
                        name=ba.Label,
                        wert=wert_text(eigenschaft),
                    )
                )

    for gleiche in namen.values():
        if len(gleiche) > 1:
            meldungen.append(meldung("maschine.name_doppelt", name=gleiche[0].NcName.strip()))
    for gelenk, liste in arten_je_gelenk.items():
        arten = [ba.Art for ba in liste]
        if len(set(arten)) < len(arten):
            meldungen.append(meldung("maschine.art_doppelt", gelenk=gelenk.Label))

    for aufnahme in aufnahmen(maschine):
        if aufnahme.Lcs is None:
            meldungen.append(meldung("maschine.lcs_fehlt", name=aufnahme.Label))
        elif kette.glied_von(aufnahme.Lcs) is None:
            meldungen.append(meldung("maschine.lcs_ausserhalb", name=aufnahme.Label))
        spindel = aufnahme.Spindel
        if spindel is not None and getattr(spindel, "Art", None) != ART_SPINDEL:
            meldungen.append(meldung("maschine.spindel_keine_spindel", name=aufnahme.Label))

    arten = {a.Art for a in aufnahmen(maschine)}
    if AUFNAHME_WERKZEUG not in arten:
        meldungen.append(meldung("maschine.keine_werkzeugaufnahme", HINWEIS))
    if AUFNAHME_WERKSTUECK not in arten:
        meldungen.append(meldung("maschine.keine_werkstueckaufnahme", HINWEIS))

    meldungen += rollen(kette, maschine)[1]
    return meldungen

