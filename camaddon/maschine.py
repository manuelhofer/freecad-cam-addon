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
ART_REVOLVER = "Revolver"
BETRIEBSARTEN = [ART_LINEAR, ART_POSITIONIEREN, ART_SPINDEL, ART_REVOLVER]

# Welche Betriebsarten zu welcher Gelenkart passen.
ERLAUBT = {LINEAR: [ART_LINEAR], DREH: [ART_POSITIONIEREN, ART_SPINDEL, ART_REVOLVER]}

# Kennwerte je Betriebsart: (Eigenschaft, Pflicht). Einheiten wie im
# Datenblatt, siehe Spezifikation Abschnitt 4.
WERTE = {
    ART_LINEAR: [
        ("Eilgang", True),
        ("VorschubMax", False),
        ("Beschleunigung", False),
        ("Ruck", False),
    ],
    ART_POSITIONIEREN: [
        ("Endlos", False),
        ("Geschwindigkeit", True),
        ("Beschleunigung", False),
        ("Ruck", False),
    ],
    ART_SPINDEL: [("Drehzahl", True), ("Hochlaufzeit", False)],
    ART_REVOLVER: [("Schaltzeit", False)],
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
        ART_REVOLVER: tr("art.revolver"),
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
        "Schaltzeit": tr("wert.schaltzeit"),
    }[eigenschaft]


def _eigenschaft(objekt, typ, name, gruppe, doku):
    if name not in objekt.PropertiesList:
        objekt.addProperty(typ, name, gruppe, doku)


class Maschine:
    """Proxy der Gruppe „Maschine“."""

    def __init__(self, objekt):
        objekt.Proxy = self
        _eigenschaft(
            objekt, "App::PropertyString", "Typ", "Maschine", tr("eigenschaft.maschine.typ")
        )
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
        _eigenschaft(
            objekt, "App::PropertyEnumeration", "Art", "Betriebsart", tr("eigenschaft.art")
        )
        objekt.Art = BETRIEBSARTEN
        _eigenschaft(
            objekt, "App::PropertyString", "NcName", "Betriebsart", tr("eigenschaft.ncname")
        )
        _eigenschaft(objekt, "App::PropertyFloat", "Eilgang", "Werte", tr("eigenschaft.eilgang"))
        _eigenschaft(
            objekt, "App::PropertyFloat", "VorschubMax", "Werte", tr("eigenschaft.vorschubmax")
        )
        _eigenschaft(
            objekt,
            "App::PropertyFloat",
            "Beschleunigung",
            "Werte",
            tr("eigenschaft.beschleunigung"),
        )
        _eigenschaft(objekt, "App::PropertyFloat", "Ruck", "Werte", tr("eigenschaft.ruck"))
        _eigenschaft(objekt, "App::PropertyBool", "Endlos", "Werte", tr("eigenschaft.endlos"))
        _eigenschaft(
            objekt,
            "App::PropertyFloat",
            "Geschwindigkeit",
            "Werte",
            tr("eigenschaft.geschwindigkeit"),
        )
        _eigenschaft(objekt, "App::PropertyFloat", "Drehzahl", "Werte", tr("eigenschaft.drehzahl"))
        _eigenschaft(
            objekt, "App::PropertyFloat", "Hochlaufzeit", "Werte", tr("eigenschaft.hochlaufzeit")
        )
        _eigenschaft(
            objekt, "App::PropertyFloat", "Schaltzeit", "Werte", tr("eigenschaft.schaltzeit")
        )
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
        # Global: Das LCS liegt in einem Bauteil (eigener Gültigkeitsbereich),
        # das Maschinenobjekt daneben – ein einfacher Link wäre „out of scope“.
        _eigenschaft(
            objekt, "App::PropertyString", "Bezeichnung", "Aufnahme", tr("eigenschaft.bezeichnung")
        )
        _eigenschaft(objekt, "App::PropertyLinkGlobal", "Lcs", "Aufnahme", tr("eigenschaft.lcs"))
        _eigenschaft(
            objekt, "App::PropertyEnumeration", "Art", "Aufnahme", tr("eigenschaft.aufnahmeart")
        )
        objekt.Art = AUFNAHMEARTEN
        _eigenschaft(objekt, "App::PropertyLink", "Spindel", "Aufnahme", tr("eigenschaft.spindel"))
        _eigenschaft(objekt, "App::PropertyInteger", "Platz", "Aufnahme", tr("eigenschaft.platz"))

    def onDocumentRestored(self, objekt):
        # Ältere Dateien ohne Platz bekommen die Eigenschaft nachgereicht.
        _eigenschaft(objekt, "App::PropertyInteger", "Platz", "Aufnahme", tr("eigenschaft.platz"))

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
    beschrifte(objekt)
    return objekt


def neue_aufnahme(maschine, lcs, art, name, spindel=None, platz=0):
    objekt = maschine.newObject("App::FeaturePython", "Aufnahme")
    Aufnahme(objekt)
    objekt.Lcs = lcs
    objekt.Art = art
    objekt.Spindel = spindel
    objekt.Platz = platz
    objekt.Bezeichnung = name
    beschrifte(objekt)
    return objekt


def name_von(objekt):
    """Der Name, den der Benutzer vergeben hat (NC-Name bzw. Bezeichnung)."""
    if isinstance(getattr(objekt, "Proxy", None), Betriebsart):
        return objekt.NcName.strip() or "?"
    return getattr(objekt, "Bezeichnung", "") or objekt.Label


def beschrifte(objekt):
    """Setzt die Beschriftung im Baum aus den Daten.

    Der Name allein taugt nicht als Label: FreeCAD erlaubt kein Label doppelt
    und hängt sonst „001“ an – eine Aufnahme „Futter“ neben dem Bauteil
    „Futter“ hieße dann „Futter001“ (gefunden im Szenario).
    """
    if isinstance(getattr(objekt, "Proxy", None), Betriebsart):
        objekt.Label = f"{name_von(objekt)} · {art_text(objekt.Art)}"
    elif objekt.Art == AUFNAHME_WERKZEUG:
        objekt.Label = tr("aufnahme.beschriftung_werkzeug", name=name_von(objekt))
    else:
        objekt.Label = tr("aufnahme.beschriftung_werkstueck", name=name_von(objekt))


def globale_platzierung(objekt):
    """Lage eines Objekts in der Welt, durch alle umgebenden Parts hindurch."""
    eltern = objekt.Parents
    if eltern:
        wurzel, pfad = eltern[0]
        return wurzel.getPlacementOf(pfad)
    return objekt.Placement


def platz_name(nummer):
    """Anzeigename eines Revolverplatzes: P1, P2, …"""
    return f"P{nummer}"


def plaetze(maschine, kette, revolver):
    """Die Werkzeugaufnahmen, die der Revolver (eine Betriebsart) trägt,
    nach Platznummer sortiert – das sind alle im Glied hinter seinem Gelenk."""
    gelenk = next((g for g in kette.gelenke if g.objekt == revolver.Gelenk), None)
    if gelenk is None:
        return []
    liste = [
        a
        for a in aufnahmen(maschine)
        if a.Art == AUFNAHME_WERKZEUG
        and a.Lcs is not None
        and kette.glied_von(a.Lcs) is gelenk.kind
    ]
    return sorted(liste, key=lambda a: a.Platz)


def verteile_plaetze(maschine, kette, revolver, erstes_lcs, anzahl):
    """Verteilhilfe: legt zum ersten Platz die übrigen gleichmäßig im Kreis um
    die Revolverachse an (je ein neues LCS neben dem ersten) und nummeriert
    alle als P1 … Pn. Bestehende Werkzeugaufnahmen dieses Revolvers werden
    dabei ersetzt. Gibt die Aufnahmen in Platzreihenfolge zurück."""
    import FreeCAD

    gelenk = next((g for g in kette.gelenke if g.objekt == revolver.Gelenk), None)
    if gelenk is None or anzahl < 1:
        return []
    doc = maschine.Document
    # Frühere Verteilung ersetzen: alte Platz-Aufnahmen weg, und die LCS, die
    # die Verteilhilfe selbst angelegt hatte (erkennbar am Namen), auch.
    for alt in plaetze(maschine, kette, revolver):
        doc.removeObject(alt.Name)
    praefix = erstes_lcs.Label + "_P"
    alte = [
        o.Name
        for o in doc.Objects
        if o.isDerivedFrom("App::LocalCoordinateSystem") and o.Label.startswith(praefix)
    ]
    for name in alte:
        # Ein LCS nimmt seine Achsen und Ebenen beim Löschen mit – daher
        # über Namen, nicht über die (dann teils gelöschten) Objekte.
        if doc.getObject(name) is not None:
            doc.removeObject(name)

    behaelter = erstes_lcs.getParentGeoFeatureGroup()
    behaelter_global = globale_platzierung(behaelter) if behaelter else FreeCAD.Placement()
    erstes_global = globale_platzierung(erstes_lcs)
    ergebnis = []
    for nummer in range(1, anzahl + 1):
        if nummer == 1:
            lcs = erstes_lcs
        else:
            winkel = 360.0 * (nummer - 1) / anzahl
            drehung = FreeCAD.Placement(
                FreeCAD.Vector(), FreeCAD.Rotation(gelenk.richtung, winkel), gelenk.ursprung
            )
            lcs = doc.addObject("App::LocalCoordinateSystem", erstes_lcs.Name + "_")
            lcs.Label = f"{erstes_lcs.Label}_{platz_name(nummer)}"
            if behaelter:
                behaelter.addObject(lcs)
            lcs.Placement = behaelter_global.inverse() * drehung * erstes_global
        ergebnis.append(
            neue_aufnahme(maschine, lcs, AUFNAHME_WERKZEUG, platz_name(nummer), platz=nummer)
        )
    return ergebnis


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
            meldungen.append(meldung("maschine.name_fehlt", bezug=ba, eintrag=name_von(ba)))
        else:
            namen.setdefault(name.upper(), []).append(ba)
        if ba.Gelenk is None:
            meldungen.append(meldung("maschine.gelenk_fehlt", bezug=ba, name=name_von(ba)))
            continue
        art = gelenk_art.get(ba.Gelenk)
        if art is None:
            meldungen.append(
                meldung(
                    "maschine.gelenk_keine_achse",
                    bezug=ba,
                    name=name_von(ba),
                    gelenk=ba.Gelenk.Label,
                )
            )
            continue
        if ba.Art not in ERLAUBT[art]:
            meldungen.append(
                meldung(
                    "maschine.art_passt_nicht",
                    bezug=ba,
                    name=name_von(ba),
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
                        bezug=ba,
                        name=name_von(ba),
                        wert=wert_text(eigenschaft),
                    )
                )

    for gleiche in namen.values():
        if len(gleiche) > 1:
            meldungen.append(
                meldung("maschine.name_doppelt", bezug=gleiche[1], name=gleiche[0].NcName.strip())
            )
    for gelenk, liste in arten_je_gelenk.items():
        arten = [ba.Art for ba in liste]
        if len(set(arten)) < len(arten):
            meldungen.append(meldung("maschine.art_doppelt", bezug=liste[-1], gelenk=gelenk.Label))

    for aufnahme in aufnahmen(maschine):
        if aufnahme.Lcs is None:
            meldungen.append(meldung("maschine.lcs_fehlt", bezug=aufnahme, name=name_von(aufnahme)))
        elif kette.glied_von(aufnahme.Lcs) is None:
            meldungen.append(
                meldung("maschine.lcs_ausserhalb", bezug=aufnahme, name=name_von(aufnahme))
            )
        spindel = aufnahme.Spindel
        if spindel is not None and getattr(spindel, "Art", None) != ART_SPINDEL:
            meldungen.append(
                meldung("maschine.spindel_keine_spindel", bezug=aufnahme, name=name_von(aufnahme))
            )

    for ba in betriebsarten(maschine):
        if ba.Art != ART_REVOLVER:
            continue
        nummern = [a.Platz for a in plaetze(maschine, kette, ba)]
        if not nummern:
            meldungen.append(meldung("maschine.revolver_ohne_plaetze", bezug=ba, name=name_von(ba)))
        elif 0 in nummern or len(set(nummern)) < len(nummern):
            meldungen.append(meldung("maschine.plaetze_nummern", bezug=ba, name=name_von(ba)))

    arten = {a.Art for a in aufnahmen(maschine)}
    if AUFNAHME_WERKZEUG not in arten:
        meldungen.append(meldung("maschine.keine_werkzeugaufnahme", HINWEIS))
    if AUFNAHME_WERKSTUECK not in arten:
        meldungen.append(meldung("maschine.keine_werkstueckaufnahme", HINWEIS))

    meldungen += rollen(kette, maschine)[1]
    return meldungen
