# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Werkzeugbibliothek des Benutzers (W-002): Werkzeuge und eigene Werkstoffe.

Gespeichert wird als JSON unter FreeCAD.getUserAppDataDir()/CamAddon/ – für
das Parameter-System von FreeCAD ist eine Bibliothek zu groß (Arbeitsregeln,
Abschnitt 7), und dort überlebt sie jedes Update des Addons. Der Dialog
(gui_werkzeuge.py) bearbeitet eine Kopie und speichert erst bei OK oder
Übernehmen.

Läuft ohne Oberfläche.
"""

import copy
import json
import os
import time
import uuid
from dataclasses import dataclass, field

import FreeCAD

from . import einheiten
from . import werkstoffe as ws
from .sprache import tr

FORMAT = 1  # steigt, wenn sich der Aufbau der Datei so ändert, dass alte umgestellt werden müssen
DATEINAME = "werkzeugverwaltung.json"

# Arten von Werkzeugen – gespeichert als diese festen Wörter; die ganze
# Liste mit Maßen und Beispielen steht in ARTDATEN (Spezifikation
# Werkzeugarten, Abschnitt 2).
SCHAFTFRAESER = "schaftfraeser"
KUGELFRAESER = "kugelfraeser"
TORUSFRAESER = "torusfraeser"
KONIKFRAESER = "konikfraeser"
SCHWALBENSCHWANZFRAESER = "schwalbenschwanzfraeser"
LOLLIPOPFRAESER = "lollipopfraeser"
FASENFRAESER = "fasenfraeser"
RADIENFRAESER = "radienfraeser"
PLANFRAESER = "planfraeser"
NUTENFRAESER = "nutenfraeser"
FORMFRAESER = "formfraeser"
GEWINDEFRAESER = "gewindefraeser"
BOHRER = "bohrer"
ZENTRIERBOHRER = "zentrierbohrer"
NC_ANBOHRER = "nc_anbohrer"
GEWINDEBOHRER_RECHTS = "gewindebohrer_rechts"
GEWINDEBOHRER_LINKS = "gewindebohrer_links"
KEGELSENKER = "kegelsenker"
FLACHSENKER = "flachsenker"
REIBAHLE = "reibahle"
BOHRSTANGE = "bohrstange"
AUSSPINDELWERKZEUG = "ausspindelwerkzeug"
DREHWERKZEUG = "drehwerkzeug"
EINSTECHWERKZEUG = "einstechwerkzeug"
GEWINDEDREHWERKZEUG = "gewindedrehwerkzeug"
TASTER = "taster"
# Gespeicherte Wörter, die es nicht mehr gibt -> heutige Art. Bis
# P-2026-09-26-54 hieß der Kugelfräser „Radiusfräser“; ein Radienfräser ist
# aber eine andere Art (Spezifikation Werkzeugarten, Abschnitt 1).
ALTE_ARTEN = {"radiusfraeser": KUGELFRAESER}

# Gruppen in der Auswahl – nicht gespeichert.
GRUPPE_FRAESEN = "fraesen"
GRUPPE_BOHREN = "bohren"
GRUPPE_DREHEN = "drehen"
GRUPPE_ANTASTEN = "antasten"
GRUPPEN = (GRUPPE_FRAESEN, GRUPPE_BOHREN, GRUPPE_DREHEN, GRUPPE_ANTASTEN)

# Die Maße, die eine Art haben kann: Längen in mm, Winkel in Grad, die
# Steigung in mm (gezeigt in inch als Gänge je Zoll).
LAENGEN_FELDER = (
    "durchmesser",
    "schneidenlaenge",
    "gesamtlaenge",
    "schaft",
    "eckradius",
    "spitzen_d",
    "hals_d",
    "hals_laenge",
    "profilradius",
    "schneidenbreite",
    "stechtiefe",
)
WINKEL_FELDER = (
    "eintauchwinkel",
    "spitzenwinkel",
    "kegelwinkel",
    "flankenwinkel",
    "einstellwinkel",
    "plattenwinkel",
)
STEIGUNG = "steigung"
ZAHLEN_FELDER = LAENGEN_FELDER + WINKEL_FELDER + (STEIGUNG,)
# Wie ein Drehwerkzeug die Platte trägt – gespeichert als diese Wörter; leer = unbekannt.
RECHTS, LINKS, NEUTRAL = "rechts", "links", "neutral"
AUSFUEHRUNGEN = (RECHTS, LINKS, NEUTRAL)

VHM, HSS = "vhm", "hss"
# Spitzenwinkel eines Bohrers, wenn keiner eingetragen ist: üblich für Spiralbohrer.
SPITZENWINKEL_BOHRER = 118.0  # Grad
SCHNEIDSTOFFE = (VHM, HSS)

# Steht in der Werkstoff-Auswahl für „Alle Werkstoffe“: Werte, die für jeden
# Werkstoff gelten, der keine eigenen hat.
ALLE = "*"

# Einsätze – wie ein Werkzeug arbeitet; gespeichert als diese festen Wörter.
VOLLNUT = "vollnut"
SCHRUPPEN = "schruppen"
DYNAMISCH = "dynamisch"  # kleines ae, großes ap: trochoidal, HPC, adaptiv
SCHLICHTEN = "schlichten"
BOHREN = "bohren"
EIGEN = "eigen"
# Seit P-2026-09-26-58, je nach Werkzeugart (Spezifikation Werkzeugarten, 5).
PLANEN = "planen"
FASEN = "fasen"
VERRUNDEN = "verrunden"
GEWINDEFRAESEN = "gewindefraesen"
ZENTRIEREN = "zentrieren"
SENKEN = "senken"
REIBEN = "reiben"
GEWINDEBOHREN = "gewindebohren"
AUSDREHEN = "ausdrehen"
EINSATZARTEN = (
    VOLLNUT,
    SCHRUPPEN,
    DYNAMISCH,
    SCHLICHTEN,
    BOHREN,
    PLANEN,
    FASEN,
    VERRUNDEN,
    GEWINDEFRAESEN,
    ZENTRIEREN,
    SENKEN,
    REIBEN,
    GEWINDEBOHREN,
    AUSDREHEN,
    EIGEN,
)


def datei_pfad():
    """Die Datei der Bibliothek beim Benutzer."""
    return os.path.join(FreeCAD.getUserAppDataDir(), "CamAddon", DATEINAME)


def art_text(art):
    """Anzeigename einer Werkzeugart."""
    return {
        SCHAFTFRAESER: tr("wv.art.schaftfraeser"),
        KUGELFRAESER: tr("wv.art.kugelfraeser"),
        TORUSFRAESER: tr("wv.art.torusfraeser"),
        KONIKFRAESER: tr("wv.art.konikfraeser"),
        SCHWALBENSCHWANZFRAESER: tr("wv.art.schwalbenschwanzfraeser"),
        LOLLIPOPFRAESER: tr("wv.art.lollipopfraeser"),
        FASENFRAESER: tr("wv.art.fasenfraeser"),
        RADIENFRAESER: tr("wv.art.radienfraeser"),
        PLANFRAESER: tr("wv.art.planfraeser"),
        NUTENFRAESER: tr("wv.art.nutenfraeser"),
        FORMFRAESER: tr("wv.art.formfraeser"),
        GEWINDEFRAESER: tr("wv.art.gewindefraeser"),
        BOHRER: tr("wv.art.bohrer"),
        ZENTRIERBOHRER: tr("wv.art.zentrierbohrer"),
        NC_ANBOHRER: tr("wv.art.nc_anbohrer"),
        GEWINDEBOHRER_RECHTS: tr("wv.art.gewindebohrer_rechts"),
        GEWINDEBOHRER_LINKS: tr("wv.art.gewindebohrer_links"),
        KEGELSENKER: tr("wv.art.kegelsenker"),
        FLACHSENKER: tr("wv.art.flachsenker"),
        REIBAHLE: tr("wv.art.reibahle"),
        BOHRSTANGE: tr("wv.art.bohrstange"),
        AUSSPINDELWERKZEUG: tr("wv.art.ausspindelwerkzeug"),
        DREHWERKZEUG: tr("wv.art.drehwerkzeug"),
        EINSTECHWERKZEUG: tr("wv.art.einstechwerkzeug"),
        GEWINDEDREHWERKZEUG: tr("wv.art.gewindedrehwerkzeug"),
        TASTER: tr("wv.art.taster"),
    }[art]


def gruppen_text(gruppe):
    """Überschrift einer Gruppe in der Auswahl: „Fräsen“, „Bohren“ …"""
    return {
        GRUPPE_FRAESEN: tr("wv.gruppe.fraesen"),
        GRUPPE_BOHREN: tr("wv.gruppe.bohren"),
        GRUPPE_DREHEN: tr("wv.gruppe.drehen"),
        GRUPPE_ANTASTEN: tr("wv.gruppe.antasten"),
    }[gruppe]


def feld_text(feld, art):
    """Beschriftung eines Feldes – bei manchen Arten heißt es anders (Zapfen-Ø …)."""
    eigen = {
        (ZENTRIERBOHRER, "durchmesser"): tr("wv.durchmesser.zapfen"),
        (ZENTRIERBOHRER, "schaft"): tr("wv.schaft.koerper"),
        (ZENTRIERBOHRER, "schneidenlaenge"): tr("wv.schneidenlaenge.zapfen"),
        (KONIKFRAESER, "durchmesser"): tr("wv.durchmesser.spitze"),
        (LOLLIPOPFRAESER, "durchmesser"): tr("wv.durchmesser.kugel"),
        (TASTER, "durchmesser"): tr("wv.durchmesser.kugel"),
        (TASTER, "schaft"): tr("wv.schaft.taststift"),
        (BOHRSTANGE, "durchmesser"): tr("wv.durchmesser.bohrung"),
        (AUSSPINDELWERKZEUG, "durchmesser"): tr("wv.durchmesser.bohrung"),
        (BOHRSTANGE, "schneidenlaenge"): tr("wv.schneidenlaenge.ausladung"),
        (AUSSPINDELWERKZEUG, "schneidenlaenge"): tr("wv.schneidenlaenge.ausladung"),
        (PLANFRAESER, "schneidenlaenge"): tr("wv.schneidenlaenge.ap"),
        (GEWINDEBOHRER_RECHTS, "schneidenlaenge"): tr("wv.schneidenlaenge.gewinde"),
        (GEWINDEBOHRER_LINKS, "schneidenlaenge"): tr("wv.schneidenlaenge.gewinde"),
        (KEGELSENKER, "spitzenwinkel"): tr("wv.spitzenwinkel.senk"),
        (RADIENFRAESER, "spitzen_d"): tr("wv.spitzen_d.fuehrung"),
        (FLACHSENKER, "spitzen_d"): tr("wv.spitzen_d.fuehrung"),
        (DREHWERKZEUG, "eckradius"): tr("wv.eckradius.drehen"),
        (EINSTECHWERKZEUG, "eckradius"): tr("wv.eckradius.drehen"),
        (EINSTECHWERKZEUG, "schneidenbreite"): tr("wv.schneidenbreite.stechen"),
    }
    if (art, feld) in eigen:
        return eigen[(art, feld)]
    return {
        "durchmesser": tr("wv.durchmesser"),
        "schneiden": tr("wv.schneiden"),
        "schneidenlaenge": tr("wv.schneidenlaenge"),
        "gesamtlaenge": tr("wv.gesamtlaenge"),
        "schaft": tr("wv.schaft"),
        "schneidstoff": tr("wv.schneidstoff"),
        "eckradius": tr("wv.eckradius"),
        "eintauchwinkel": tr("wv.eintauchwinkel"),
        "spitzenwinkel": tr("wv.spitzenwinkel"),
        "spitzen_d": tr("wv.spitzen_d"),
        "kegelwinkel": tr("wv.kegelwinkel"),
        "flankenwinkel": tr("wv.flankenwinkel"),
        "hals_d": tr("wv.hals_d"),
        "hals_laenge": tr("wv.hals_laenge"),
        "profilradius": tr("wv.profilradius"),
        STEIGUNG: tr("wv.steigung"),
        "schneidenbreite": tr("wv.schneidenbreite"),
        "einstellwinkel": tr("wv.einstellwinkel"),
        "plattenwinkel": tr("wv.plattenwinkel"),
        "stechtiefe": tr("wv.stechtiefe"),
        "ausfuehrung": tr("wv.ausfuehrung"),
    }[feld]


def ausfuehrung_text(ausfuehrung):
    """„rechts“, „links“, „neutral“ – oder ein Strich, wenn unbekannt."""
    return {
        RECHTS: tr("wv.ausfuehrung.rechts"),
        LINKS: tr("wv.ausfuehrung.links"),
        NEUTRAL: tr("wv.ausfuehrung.neutral"),
    }.get(ausfuehrung, tr("wv.ausfuehrung.unbekannt"))


def schneidstoff_text(schneidstoff):
    """Kurzname des Schneidstoffs, wie er in der Liste steht: „VHM“, „HSS“."""
    return {VHM: tr("wv.schneidstoff.vhm.kurz"), HSS: tr("wv.schneidstoff.hss.kurz")}[schneidstoff]


def einsatzart_text(art):
    """Anzeigename einer Einsatzart."""
    return {
        VOLLNUT: tr("wv.einsatz.vollnut"),
        SCHRUPPEN: tr("wv.einsatz.schruppen"),
        DYNAMISCH: tr("wv.einsatz.dynamisch"),
        SCHLICHTEN: tr("wv.einsatz.schlichten"),
        BOHREN: tr("wv.einsatz.bohren"),
        PLANEN: tr("wv.einsatz.planen"),
        FASEN: tr("wv.einsatz.fasen"),
        VERRUNDEN: tr("wv.einsatz.verrunden"),
        GEWINDEFRAESEN: tr("wv.einsatz.gewindefraesen"),
        ZENTRIEREN: tr("wv.einsatz.zentrieren"),
        SENKEN: tr("wv.einsatz.senken"),
        REIBEN: tr("wv.einsatz.reiben"),
        GEWINDEBOHREN: tr("wv.einsatz.gewindebohren"),
        AUSDREHEN: tr("wv.einsatz.ausdrehen"),
        EIGEN: tr("wv.einsatz.eigen"),
    }[art]


@dataclass
class Einsatz:
    """Eine Zeile der Schnittwert-Tabelle: wie das Werkzeug arbeitet, mit welchen Werten.

    0 heißt „unbekannt“. Beim Bohrer ist fz der Vorschub je Schneide; die
    Tabelle zeigt ihn als f je Umdrehung (fz · z).
    """

    art: str = EIGEN
    name: str = ""  # eigener Name; leer = Name der Art
    ae: float = 0.0  # seitliche Zustellung, mm
    ap: float = 0.0  # Tiefe, mm
    vc: float = 0.0  # Schnittgeschwindigkeit, m/min
    fz: float = 0.0  # Vorschub je Zahn, mm

    def als_dict(self):
        return {
            "art": self.art,
            "name": self.name,
            "ae": self.ae,
            "ap": self.ap,
            "vc": self.vc,
            "fz": self.fz,
        }

    @classmethod
    def aus_dict(cls, daten):
        e = cls()
        e.art = daten.get("art") if daten.get("art") in EINSATZARTEN else EIGEN
        e.name = str(daten.get("name") or "")
        for wert in ("ae", "ap", "vc", "fz"):
            setattr(e, wert, max(_zahl(daten.get(wert), float, 0.0), 0.0))
        return e


def einsatz_name(einsatz):
    """Was in der ersten Spalte steht: der eigene Name, sonst der der Art."""
    return einsatz.name or einsatzart_text(einsatz.art)


def name_fuer_neuen(einsatz, einsaetze):
    """Der eigene Name für einen Einsatz, der zu `einsaetze` dazukommt.

    Gibt es seinen Namen dort noch nicht, bleibt er, wie er ist (leer = der
    Name der Art, der mit der Sprache wechselt). Sonst bekommt er eine
    Nummer: „Schruppen dynamisch 2“, „… 3“ – und die Kopie von „… 2“ wird
    „… 3“. So bleiben die Zeilen im Vergleich und im Job unterscheidbar.
    """
    vergeben = {einsatz_name(e).lower() for e in einsaetze}
    name = einsatz_name(einsatz)
    if name.lower() not in vergeben:
        return einsatz.name
    stamm, zahl = name, 2
    teile = name.rsplit(" ", 1)
    if len(teile) == 2 and teile[1].isdecimal():
        stamm, zahl = teile[0], int(teile[1]) + 1
    while f"{stamm} {zahl}".lower() in vergeben:
        zahl += 1
    return f"{stamm} {zahl}"


def vorlage(werkzeug, art):
    """Ein neuer Einsatz mit ae und ap als übliche Anteile von D vorbelegt.

    vc und fz bleiben leer – die stehen im Katalog des Herstellers.
    Schneidenlänge unbekannt: für ap zählt dann höchstens 1 × D.
    """
    d = werkzeug.durchmesser
    lang = min(werkzeug.schneidenlaenge, 2 * d) if werkzeug.schneidenlaenge else d
    ae, ap = {
        VOLLNUT: (d, d / 2),
        SCHRUPPEN: (d / 2, d / 2),
        DYNAMISCH: (d / 10, lang),
        SCHLICHTEN: (d / 50, lang),
        # Planfräser: drei Viertel der Breite, ein Drittel der Schneide.
        PLANEN: (d * 0.75, lang / 3),
    }.get(art, (0.0, 0.0))
    # Gerundet, wie es gezeigt wird: 0,01 mm, in inch 0,0001 in.
    return Einsatz(
        art=art,
        ae=einheiten.runden(ae, einheiten.LAENGE, 2),
        ap=einheiten.runden(ap, einheiten.LAENGE, 2),
    )


@dataclass
class Werkzeug:
    """Ein Fräser oder Bohrer mit seiner Geometrie und seinen Schnittwerten. 0 heißt „unbekannt“."""

    # Bleibt, auch wenn sich die T-Nummer ändert.
    kennung: str = field(default_factory=lambda: uuid.uuid4().hex)
    nummer: int = 1  # T-Nummer
    # Wie das Werkzeug in der Steuerung heißt (T="Fräser VHM 12"); leer = beispielname().
    name: str = ""
    art: str = SCHAFTFRAESER
    durchmesser: float = 0.0  # mm
    schneiden: int = 3  # Schneidenzahl z
    schneidenlaenge: float = 0.0  # nutzbare Schneidenlänge in mm – das größte ap
    eckradius: float = 0.0  # mm, nur beim Torusfräser
    # Nur für CAM (Simulation, Kollision); 0 = geschätzt, siehe laenge_fuer_cam().
    gesamtlaenge: float = 0.0  # mm
    schaft: float = 0.0  # Schaftdurchmesser, mm
    # Wie steil der Fräser höchstens eintauchen darf (Rampe, Helix), Grad; 0 = unbekannt.
    eintauchwinkel: float = 0.0
    # Winkel an der Spitze, über beide Schneiden (Bohrer, Anbohrer, Fasenfräser,
    # Senker), Grad; 0 = der übliche der Art (ueblich()).
    spitzenwinkel: float = 0.0
    # Seit P-2026-09-26-55, je nach Art (ARTDATEN); 0 bzw. leer = unbekannt.
    spitzen_d: float = 0.0  # mm: Spitze des Fasenfräsers, Führung des Radienfräsers …
    kegelwinkel: float = 0.0  # Grad je Seite (Konikfräser)
    flankenwinkel: float = 0.0  # Grad (Gewinde, Schwalbenschwanz); 0 = üblich
    hals_d: float = 0.0  # mm
    hals_laenge: float = 0.0  # mm
    profilradius: float = 0.0  # mm (Radienfräser)
    steigung: float = 0.0  # mm je Umdrehung (Gewinde)
    schneidenbreite: float = 0.0  # mm (Nutenfräser, Einstechwerkzeug)
    einstellwinkel: float = 0.0  # Grad (Planfräser, Drehwerkzeug); 0 = üblich
    plattenwinkel: float = 0.0  # Grad (Drehwerkzeug); 0 = üblich
    stechtiefe: float = 0.0  # mm (Einstechwerkzeug)
    ausfuehrung: str = ""  # RECHTS, LINKS, NEUTRAL (Drehwerkzeuge)
    # Warngrenze des Planers: breiter als so viel % von D wird rot, bleibt aber
    # wählbar; 0 = keine. Vorgabe 10 %, egal wie viele Schneiden (Manuel).
    ae_warngrenze: float = 10.0
    schneidstoff: str = VHM
    bezeichnung: str = ""  # frei: Hersteller, Bestellnummer, Beschichtung …
    # Werkstoff-Kennung oder ALLE -> die Einsätze mit ihren Werten.
    schnittwerte: dict = field(default_factory=dict)
    # Felder, die noch Beispielwerte halten (grau gezeigt, aber gültig); nicht gespeichert.
    beispiel: set = field(default_factory=set, compare=False, repr=False)

    def einsaetze(self, werkstoff):
        """Die Tabelle, die für den Werkstoff gilt: seine eigene, sonst die für alle Werkstoffe."""
        if werkstoff in self.schnittwerte:
            return self.schnittwerte[werkstoff]
        return self.schnittwerte.get(ALLE, [])

    def hat_eigene(self, werkstoff):
        """Hat das Werkzeug für diesen Werkstoff eigene Werte?"""
        return werkstoff != ALLE and werkstoff in self.schnittwerte

    def eigene_anlegen(self, werkstoff):
        """Eigene Werte für den Werkstoff – als Kopie der Werte für alle Werkstoffe."""
        vorlage_liste = self.schnittwerte.get(ALLE, [])
        self.schnittwerte[werkstoff] = [Einsatz.aus_dict(e.als_dict()) for e in vorlage_liste]
        return self.schnittwerte[werkstoff]

    def eigene_loeschen(self, werkstoff):
        """Eigene Werte weg – danach gelten wieder die für alle Werkstoffe."""
        if werkstoff != ALLE:
            self.schnittwerte.pop(werkstoff, None)

    def hat_zustellungen(self):
        """Hat irgendein Einsatz (irgendeines Werkstoffs) ae oder ap?"""
        return any(e.ae or e.ap for liste in self.schnittwerte.values() for e in liste)

    def zustellungen_umrechnen(self, faktor):
        """ae und ap aller Einsätze aller Werkstoffe mal `faktor` – für einen neuen Durchmesser.

        vc und fz bleiben, wie sie sind: Die stehen im Katalog des Herstellers
        und hängen nicht einfach am Durchmesser.
        """
        for liste in self.schnittwerte.values():
            for einsatz in liste:
                einsatz.ae = round(einsatz.ae * faktor, 3)
                einsatz.ap = round(einsatz.ap * faktor, 3)

    def zum_bearbeiten(self, werkstoff):
        """Die Liste, die für diesen Werkstoff bearbeitet wird, oder None.

        None heißt: Der Werkstoff hat keine eigenen Werte, gezeigt werden die
        für alle Werkstoffe – ändern kann man sie dort oder nach „Eigene Werte
        anlegen“.
        """
        if werkstoff == ALLE:
            return self.schnittwerte.setdefault(ALLE, [])
        return self.schnittwerte.get(werkstoff)

    def als_dict(self):
        return {
            "kennung": self.kennung,
            "nummer": self.nummer,
            "art": self.art,
            "durchmesser": self.durchmesser,
            "schneiden": self.schneiden,
            "schneidenlaenge": self.schneidenlaenge,
            "eckradius": self.eckradius,
            "gesamtlaenge": self.gesamtlaenge,
            "schaft": self.schaft,
            "eintauchwinkel": self.eintauchwinkel,
            "spitzenwinkel": self.spitzenwinkel,
            **{feld: getattr(self, feld) for feld in NEUE_FELDER},
            "ausfuehrung": self.ausfuehrung,
            "ae_warngrenze": self.ae_warngrenze,
            "schneidstoff": self.schneidstoff,
            "bezeichnung": self.bezeichnung,
            "name": self.name,
            # Eine leere Tabelle „für alle Werkstoffe“ ist dasselbe wie keine:
            # zum_bearbeiten() legt sie schon beim Ansehen an – das darf nicht
            # als Änderung zählen (sonst fragt der Dialog grundlos „Speichern?“).
            "schnittwerte": {
                werkstoff: [e.als_dict() for e in liste]
                for werkstoff, liste in self.schnittwerte.items()
                if liste or werkstoff != ALLE
            },
        }

    @classmethod
    def aus_dict(cls, daten):
        """Liest einen Eintrag; Unlesbares wird durch den Standardwert ersetzt."""
        w = cls()
        w.kennung = str(daten.get("kennung") or w.kennung)
        w.nummer = _zahl(daten.get("nummer"), int, w.nummer)
        art = ALTE_ARTEN.get(daten.get("art"), daten.get("art"))
        w.art = art if art in ARTEN else SCHAFTFRAESER
        w.durchmesser = _zahl(daten.get("durchmesser"), float, 0.0)
        w.schneiden = _zahl(daten.get("schneiden"), int, w.schneiden)
        w.schneidenlaenge = _zahl(daten.get("schneidenlaenge"), float, 0.0)
        w.eckradius = _zahl(daten.get("eckradius"), float, 0.0)
        # Erst seit P-2026-09-25-62 – in älteren Dateien fehlen sie: 0, geschätzt.
        w.gesamtlaenge = max(_zahl(daten.get("gesamtlaenge"), float, 0.0), 0.0)
        w.schaft = max(_zahl(daten.get("schaft"), float, 0.0), 0.0)
        w.eintauchwinkel = min(max(_zahl(daten.get("eintauchwinkel"), float, 0.0), 0.0), 90.0)
        # Erst seit P-2026-09-26-43 – fehlt er, gilt der übliche.
        w.spitzenwinkel = min(max(_zahl(daten.get("spitzenwinkel"), float, 0.0), 0.0), 180.0)
        # Erst seit P-2026-09-26-55; Winkel höchstens 180°, alles nicht negativ.
        for feld in NEUE_FELDER:
            grenze = 180.0 if feld in WINKEL_FELDER else float("inf")
            setattr(w, feld, min(max(_zahl(daten.get(feld), float, 0.0), 0.0), grenze))
        ausfuehrung = daten.get("ausfuehrung")
        w.ausfuehrung = ausfuehrung if ausfuehrung in AUSFUEHRUNGEN else ""
        # Erst seit P-2026-09-26-40 – fehlt sie, gilt die Vorgabe.
        w.ae_warngrenze = min(
            max(_zahl(daten.get("ae_warngrenze"), float, w.ae_warngrenze), 0.0), 100.0
        )
        w.schneidstoff = (
            daten.get("schneidstoff") if daten.get("schneidstoff") in SCHNEIDSTOFFE else VHM
        )
        w.bezeichnung = str(daten.get("bezeichnung") or "")
        w.name = str(daten.get("name") or "")
        schnittwerte = daten.get("schnittwerte")
        if isinstance(schnittwerte, dict):
            w.schnittwerte = {
                str(werkstoff): [Einsatz.aus_dict(e) for e in liste if isinstance(e, dict)]
                for werkstoff, liste in schnittwerte.items()
                if isinstance(liste, list)
            }
        return w


def geschaetzte_laenge(werkzeug):
    """Gesamtlänge, wenn sie niemand eingetragen hat: Schneidenlänge + 2 × D, mindestens 3 × D.

    Ohne Schneidenlänge zählt sie als 2 × D. 0, wenn D unbekannt ist.
    """
    d = werkzeug.durchmesser
    schneide = werkzeug.schneidenlaenge or 2 * d
    return max(schneide + 2 * d, 3 * d)


def laenge_fuer_cam(werkzeug):
    """Die Gesamtlänge fürs ToolBit: eingetragen, sonst geschätzt."""
    return werkzeug.gesamtlaenge or geschaetzte_laenge(werkzeug)


def schaft_fuer_cam(werkzeug):
    """Der Schaftdurchmesser fürs ToolBit: eingetragen, sonst wie D."""
    return werkzeug.schaft or werkzeug.durchmesser


def _zahl(wert, typ, ersatz):
    try:
        return typ(wert)
    except (TypeError, ValueError):
        return ersatz


# --- Die Arten ---------------------------------------------------------------


@dataclass(frozen=True)
class Artdaten:
    """Was eine Werkzeugart ausmacht (Spezifikation Werkzeugarten, Abschnitte 2–4).

    `felder`: was der Dialog zeigt, in dieser Reihenfolge (außer Nummer, Name,
    Art, Bezeichnung). `beispiel`: Werte für ein neues Werkzeug – grau
    gezeigt, aber gültig (Manuel: wer Ø 12 stehen lässt, will Ø 12);
    `beispiel_zoll` dasselbe in runden Zollmaßen, in mm gespeichert.
    `ueblich`: Winkel, die gelten, solange keiner eingetragen ist – grau im
    Feld. `pflicht`: was man zum Rechnen braucht (fett).
    """

    gruppe: str
    felder: tuple
    beispiel: dict
    beispiel_zoll: dict
    ueblich: dict = field(default_factory=dict)
    pflicht: tuple = ("durchmesser", "schneiden")


# Was fast jeder Fräser und Bohrer hat.
_GRUNDFELDER = ("durchmesser", "schneiden", "schneidenlaenge", "gesamtlaenge", "schaft")
_SCHNEIDSTOFF = ("schneidstoff",)
_ZOLL = 25.4  # mm


def _zoll(**werte):
    """Beispiele in inch: Längen in Zoll, die Steigung in Gängen je Zoll – gespeichert in mm."""
    ergebnis = {}
    for feld, x in werte.items():
        # Auf 6 Stellen: 0,03" sind 0,762 mm, nicht 0,7619999999999999.
        if feld in LAENGEN_FELDER:
            x = round(x * _ZOLL, 6)
        elif feld == STEIGUNG:
            x = round(_ZOLL / x, 6)
        ergebnis[feld] = x
    return ergebnis


ARTDATEN = {
    SCHAFTFRAESER: Artdaten(
        GRUPPE_FRAESEN,
        _GRUNDFELDER + _SCHNEIDSTOFF + ("eintauchwinkel",),
        {"durchmesser": 12.0, "schneiden": 3, "schneidenlaenge": 26.0},
        _zoll(durchmesser=1 / 2, schneiden=3, schneidenlaenge=1),
    ),
    KUGELFRAESER: Artdaten(
        GRUPPE_FRAESEN,
        _GRUNDFELDER + _SCHNEIDSTOFF + ("eintauchwinkel",),
        {"durchmesser": 12.0, "schneiden": 2, "schneidenlaenge": 24.0},
        _zoll(durchmesser=1 / 2, schneiden=2, schneidenlaenge=1),
    ),
    TORUSFRAESER: Artdaten(
        GRUPPE_FRAESEN,
        _GRUNDFELDER + _SCHNEIDSTOFF + ("eintauchwinkel", "eckradius"),
        {"durchmesser": 12.0, "schneiden": 4, "schneidenlaenge": 26.0, "eckradius": 1.0},
        _zoll(durchmesser=1 / 2, schneiden=4, schneidenlaenge=1, eckradius=0.03),
    ),
    KONIKFRAESER: Artdaten(
        GRUPPE_FRAESEN,
        _GRUNDFELDER + _SCHNEIDSTOFF + ("kegelwinkel", "eintauchwinkel"),
        {
            "durchmesser": 4.0,
            "schneiden": 2,
            "schneidenlaenge": 20.0,
            "schaft": 8.0,
            "kegelwinkel": 3.0,
        },
        _zoll(
            durchmesser=1 / 8, schneiden=2, schneidenlaenge=3 / 4, schaft=5 / 16, kegelwinkel=3.0
        ),
    ),
    SCHWALBENSCHWANZFRAESER: Artdaten(
        GRUPPE_FRAESEN,
        _GRUNDFELDER + _SCHNEIDSTOFF + ("flankenwinkel", "hals_d"),
        {
            "durchmesser": 20.0,
            "schneiden": 6,
            "schneidenlaenge": 6.0,
            "hals_d": 8.0,
            "schaft": 12.0,
        },
        _zoll(durchmesser=3 / 4, schneiden=6, schneidenlaenge=1 / 4, hals_d=5 / 16, schaft=1 / 2),
        ueblich={"flankenwinkel": 60.0},
    ),
    LOLLIPOPFRAESER: Artdaten(
        GRUPPE_FRAESEN,
        ("durchmesser", "schneiden", "hals_d", "hals_laenge", "gesamtlaenge", "schaft")
        + _SCHNEIDSTOFF,
        {"durchmesser": 8.0, "schneiden": 4, "hals_d": 5.0, "hals_laenge": 20.0, "schaft": 8.0},
        _zoll(durchmesser=5 / 16, schneiden=4, hals_d=3 / 16, hals_laenge=3 / 4, schaft=5 / 16),
    ),
    FASENFRAESER: Artdaten(
        GRUPPE_FRAESEN,
        _GRUNDFELDER + _SCHNEIDSTOFF + ("spitzenwinkel", "spitzen_d"),
        {"durchmesser": 12.0, "schneiden": 2, "schneidenlaenge": 6.0},
        _zoll(durchmesser=1 / 2, schneiden=2, schneidenlaenge=1 / 4),
        ueblich={"spitzenwinkel": 90.0},
    ),
    RADIENFRAESER: Artdaten(
        GRUPPE_FRAESEN,
        ("durchmesser", "schneiden", "profilradius", "spitzen_d")
        + ("schneidenlaenge", "gesamtlaenge", "schaft")
        + _SCHNEIDSTOFF,
        {
            "durchmesser": 14.0,
            "schneiden": 3,
            "profilradius": 3.0,
            "spitzen_d": 8.0,
            "schneidenlaenge": 4.0,
            "schaft": 12.0,
        },
        _zoll(
            durchmesser=1 / 2,
            schneiden=3,
            profilradius=1 / 8,
            spitzen_d=5 / 16,
            schneidenlaenge=3 / 16,
            schaft=1 / 2,
        ),
    ),
    PLANFRAESER: Artdaten(
        GRUPPE_FRAESEN,
        _GRUNDFELDER + _SCHNEIDSTOFF + ("einstellwinkel",),
        {
            "durchmesser": 50.0,
            "schneiden": 5,
            "schneidenlaenge": 6.0,
            "gesamtlaenge": 50.0,
            "schaft": 22.0,
        },
        _zoll(durchmesser=2, schneiden=5, schneidenlaenge=1 / 4, gesamtlaenge=2, schaft=3 / 4),
        ueblich={"einstellwinkel": 45.0},
    ),
    NUTENFRAESER: Artdaten(
        GRUPPE_FRAESEN,
        ("durchmesser", "schneiden", "schneidenbreite", "hals_d", "gesamtlaenge", "schaft")
        + _SCHNEIDSTOFF,
        {
            "durchmesser": 50.0,
            "schneiden": 12,
            "schneidenbreite": 5.0,
            "hals_d": 16.0,
            "gesamtlaenge": 80.0,
            "schaft": 20.0,
        },
        _zoll(
            durchmesser=2,
            schneiden=12,
            schneidenbreite=3 / 16,
            hals_d=5 / 8,
            gesamtlaenge=3,
            schaft=3 / 4,
        ),
    ),
    FORMFRAESER: Artdaten(
        GRUPPE_FRAESEN,
        _GRUNDFELDER + _SCHNEIDSTOFF + ("eintauchwinkel",),
        {"durchmesser": 10.0, "schneiden": 2, "schneidenlaenge": 15.0},
        _zoll(durchmesser=3 / 8, schneiden=2, schneidenlaenge=5 / 8),
    ),
    GEWINDEFRAESER: Artdaten(
        GRUPPE_FRAESEN,
        ("durchmesser", "schneiden", STEIGUNG, "flankenwinkel", "schneidenlaenge")
        + ("hals_d", "hals_laenge", "gesamtlaenge", "schaft")
        + _SCHNEIDSTOFF,
        {
            "durchmesser": 10.0,
            "schneiden": 3,
            STEIGUNG: 1.5,
            "schneidenlaenge": 15.0,
            "hals_d": 7.0,
            "hals_laenge": 20.0,
            "schaft": 10.0,
        },
        _zoll(
            durchmesser=3 / 8,
            schneiden=3,
            steigung=16,
            schneidenlaenge=5 / 8,
            hals_d=1 / 4,
            hals_laenge=3 / 4,
            schaft=3 / 8,
        ),
        ueblich={"flankenwinkel": 60.0},
    ),
    BOHRER: Artdaten(
        GRUPPE_BOHREN,
        _GRUNDFELDER + _SCHNEIDSTOFF + ("spitzenwinkel",),
        {"durchmesser": 12.0, "schneiden": 2, "schneidenlaenge": 60.0},
        _zoll(durchmesser=1 / 2, schneiden=2, schneidenlaenge=2.5),
        ueblich={"spitzenwinkel": SPITZENWINKEL_BOHRER},
    ),
    ZENTRIERBOHRER: Artdaten(
        GRUPPE_BOHREN,
        _GRUNDFELDER + _SCHNEIDSTOFF + ("spitzenwinkel",),
        {
            "durchmesser": 2.5,
            "schneiden": 2,
            "schneidenlaenge": 3.1,
            "gesamtlaenge": 45.0,
            "schaft": 6.3,
        },
        _zoll(
            durchmesser=1 / 8,
            schneiden=2,
            schneidenlaenge=1 / 8,
            gesamtlaenge=2.125,
            schaft=5 / 16,
        ),
        ueblich={"spitzenwinkel": 60.0},
    ),
    NC_ANBOHRER: Artdaten(
        GRUPPE_BOHREN,
        _GRUNDFELDER + _SCHNEIDSTOFF + ("spitzenwinkel",),
        {"durchmesser": 10.0, "schneiden": 2, "schneidenlaenge": 20.0},
        _zoll(durchmesser=3 / 8, schneiden=2, schneidenlaenge=3 / 4),
        ueblich={"spitzenwinkel": 90.0},
    ),
    # Gewindebohrer ohne Schneidenzahl (Manuel): Der Vorschub ist n · P.
    GEWINDEBOHRER_RECHTS: Artdaten(
        GRUPPE_BOHREN,
        ("durchmesser", STEIGUNG, "schneidenlaenge", "gesamtlaenge", "schaft") + _SCHNEIDSTOFF,
        {"durchmesser": 10.0, STEIGUNG: 1.5, "schneidenlaenge": 20.0},
        _zoll(durchmesser=1 / 2, steigung=13, schneidenlaenge=1),
        pflicht=("durchmesser", STEIGUNG),
    ),
    GEWINDEBOHRER_LINKS: Artdaten(
        GRUPPE_BOHREN,
        ("durchmesser", STEIGUNG, "schneidenlaenge", "gesamtlaenge", "schaft") + _SCHNEIDSTOFF,
        {"durchmesser": 10.0, STEIGUNG: 1.5, "schneidenlaenge": 20.0},
        _zoll(durchmesser=1 / 2, steigung=13, schneidenlaenge=1),
        pflicht=("durchmesser", STEIGUNG),
    ),
    KEGELSENKER: Artdaten(
        GRUPPE_BOHREN,
        ("durchmesser", "schneiden", "spitzenwinkel", "spitzen_d", "gesamtlaenge", "schaft")
        + _SCHNEIDSTOFF,
        {"durchmesser": 20.0, "schneiden": 3, "spitzen_d": 4.0, "schaft": 10.0},
        _zoll(durchmesser=3 / 4, schneiden=3, spitzen_d=5 / 32, schaft=3 / 8),
        ueblich={"spitzenwinkel": 90.0},
    ),
    FLACHSENKER: Artdaten(
        GRUPPE_BOHREN,
        ("durchmesser", "schneiden", "spitzen_d", "schneidenlaenge", "gesamtlaenge", "schaft")
        + _SCHNEIDSTOFF,
        {
            "durchmesser": 18.0,
            "schneiden": 3,
            "spitzen_d": 11.0,
            "schneidenlaenge": 12.0,
            "schaft": 12.5,
        },
        _zoll(durchmesser=5 / 8, schneiden=3, spitzen_d=3 / 8, schneidenlaenge=1 / 2, schaft=1 / 2),
    ),
    REIBAHLE: Artdaten(
        GRUPPE_BOHREN,
        _GRUNDFELDER + _SCHNEIDSTOFF,
        {"durchmesser": 10.0, "schneiden": 6, "schneidenlaenge": 30.0},
        _zoll(durchmesser=3 / 8, schneiden=6, schneidenlaenge=1.25),
    ),
    BOHRSTANGE: Artdaten(
        GRUPPE_BOHREN,
        _GRUNDFELDER + _SCHNEIDSTOFF,
        {"durchmesser": 20.0, "schneiden": 1, "schneidenlaenge": 60.0},
        _zoll(durchmesser=3 / 4, schneiden=1, schneidenlaenge=2.5),
    ),
    AUSSPINDELWERKZEUG: Artdaten(
        GRUPPE_BOHREN,
        _GRUNDFELDER + _SCHNEIDSTOFF,
        {"durchmesser": 30.0, "schneiden": 1, "schneidenlaenge": 60.0},
        _zoll(durchmesser=1.25, schneiden=1, schneidenlaenge=2.5),
    ),
    DREHWERKZEUG: Artdaten(
        GRUPPE_DREHEN,
        ("eckradius", "einstellwinkel", "plattenwinkel", "ausfuehrung") + _SCHNEIDSTOFF,
        {"eckradius": 0.8, "ausfuehrung": RECHTS},
        _zoll(eckradius=1 / 32, ausfuehrung=RECHTS),
        ueblich={"einstellwinkel": 95.0, "plattenwinkel": 80.0},
        pflicht=(),
    ),
    EINSTECHWERKZEUG: Artdaten(
        GRUPPE_DREHEN,
        ("schneidenbreite", "eckradius", "stechtiefe", "ausfuehrung") + _SCHNEIDSTOFF,
        {"schneidenbreite": 3.0, "eckradius": 0.2, "stechtiefe": 10.0, "ausfuehrung": RECHTS},
        _zoll(schneidenbreite=1 / 8, eckradius=0.008, stechtiefe=0.4, ausfuehrung=RECHTS),
        pflicht=(),
    ),
    GEWINDEDREHWERKZEUG: Artdaten(
        GRUPPE_DREHEN,
        (STEIGUNG, "flankenwinkel", "ausfuehrung") + _SCHNEIDSTOFF,
        {STEIGUNG: 1.5, "ausfuehrung": RECHTS},
        _zoll(steigung=16, ausfuehrung=RECHTS),
        ueblich={"flankenwinkel": 60.0},
        pflicht=(),
    ),
    TASTER: Artdaten(
        GRUPPE_ANTASTEN,
        ("durchmesser", "gesamtlaenge", "schaft"),
        {"durchmesser": 4.0, "gesamtlaenge": 50.0, "schaft": 3.0},
        _zoll(durchmesser=5 / 32, gesamtlaenge=2, schaft=1 / 8),
        pflicht=(),
    ),
}
ARTEN = tuple(ARTDATEN)  # in der Reihenfolge der Auswahl

# Welche Einsätze „+ Einsatz“ je Art anbietet; „eigen“ geht immer dazu. None:
# keine Schnittwerte – Drehwerkzeuge (FreeCAD dreht nicht) und Taster.
EINSAETZE_JE_ART = {
    SCHAFTFRAESER: (VOLLNUT, SCHRUPPEN, DYNAMISCH, SCHLICHTEN),
    KUGELFRAESER: (SCHRUPPEN, SCHLICHTEN),
    TORUSFRAESER: (VOLLNUT, SCHRUPPEN, DYNAMISCH, SCHLICHTEN),
    KONIKFRAESER: (SCHLICHTEN,),
    SCHWALBENSCHWANZFRAESER: (VOLLNUT,),
    LOLLIPOPFRAESER: (SCHLICHTEN,),
    FASENFRAESER: (FASEN,),
    RADIENFRAESER: (VERRUNDEN,),
    PLANFRAESER: (PLANEN,),
    NUTENFRAESER: (VOLLNUT,),
    FORMFRAESER: (SCHLICHTEN,),
    GEWINDEFRAESER: (GEWINDEFRAESEN,),
    BOHRER: (BOHREN,),
    ZENTRIERBOHRER: (ZENTRIEREN,),
    NC_ANBOHRER: (ZENTRIEREN,),
    GEWINDEBOHRER_RECHTS: (GEWINDEBOHREN,),
    GEWINDEBOHRER_LINKS: (GEWINDEBOHREN,),
    KEGELSENKER: (SENKEN,),
    FLACHSENKER: (SENKEN,),
    REIBAHLE: (REIBEN,),
    BOHRSTANGE: (AUSDREHEN,),
    AUSSPINDELWERKZEUG: (AUSDREHEN,),
    DREHWERKZEUG: None,
    EINSTECHWERKZEUG: None,
    GEWINDEDREHWERKZEUG: None,
    TASTER: None,
}
# Seit P-2026-09-26-55: Maße neben denen, die es vorher schon gab.
NEUE_FELDER = (
    "spitzen_d",
    "kegelwinkel",
    "flankenwinkel",
    "hals_d",
    "hals_laenge",
    "profilradius",
    STEIGUNG,
    "schneidenbreite",
    "einstellwinkel",
    "plattenwinkel",
    "stechtiefe",
)
# Die Beispiele je Art, wie bis P-2026-09-26-55 als eigene Tabellen.
BEISPIELE = {art: daten.beispiel for art, daten in ARTDATEN.items()}
BEISPIELE_ZOLL = {art: daten.beispiel_zoll for art, daten in ARTDATEN.items()}


def artdaten(art):
    """Gruppe, Felder, Beispiele der Art (Artdaten)."""
    return ARTDATEN[art]


def arten_der_gruppe(gruppe):
    """Die Arten einer Gruppe, in der Reihenfolge der Auswahl."""
    return tuple(art for art, daten in ARTDATEN.items() if daten.gruppe == gruppe)


def einsatzarten(art):
    """Die Einsätze, die zur Art passen, und „eigen“ – oder None: keine Schnittwerte."""
    passend = EINSAETZE_JE_ART[art]
    return None if passend is None else passend + (EIGEN,)


def bohrend(art):
    """Bohrt die Art – Vorschub je Umdrehung statt je Zahn, kein ae und ap?"""
    return ARTDATEN[art].gruppe == GRUPPE_BOHREN


def gewindebohrer(art):
    """Ein Gewindebohrer: Der Vorschub je Umdrehung ist die Steigung."""
    return art in (GEWINDEBOHRER_RECHTS, GEWINDEBOHRER_LINKS)


def hat_feld(werkzeug, feld):
    """Hat die Art des Werkzeugs dieses Feld?"""
    return feld in ARTDATEN[werkzeug.art].felder


def ueblich(art, feld):
    """Der übliche Wert eines Winkels bei dieser Art – oder 0, wenn es keinen gibt."""
    return ARTDATEN[art].ueblich.get(feld, 0.0)


def wert(werkzeug, feld):
    """Ein Maß des Werkzeugs: eingetragen, sonst das übliche der Art (Winkel)."""
    return getattr(werkzeug, feld) or ueblich(werkzeug.art, feld)


def beispiele(art):
    """Die Beispielwerte der Art im gewählten Maßsystem."""
    return (BEISPIELE_ZOLL if einheiten.in_zoll() else BEISPIELE)[art]


def beispielwerte_setzen(werkzeug, neu=False):
    """Trägt die Beispielwerte der Art ein und merkt sie in `werkzeug.beispiel`.

    `neu`: in alle Beispielfelder (ein neues Werkzeug); sonst – nach einem
    Wechsel der Art – in die, die noch Beispiel oder leer sind: Der
    Torusfräser bekommt so einen Eckradius und sieht im Bild wie einer aus.
    Beispielfelder, die die neue Art nicht hat (Eckradius), werden leer (0
    bzw. "" bei der Ausführung) – beim Zurückwechseln bekommen sie wieder
    das Beispiel.
    """
    werte = beispiele(werkzeug.art)
    if neu:
        felder = set(werte)
    else:
        felder = set(werkzeug.beispiel) | {feld for feld in werte if not getattr(werkzeug, feld)}
    for feld in felder:
        leer = "" if isinstance(getattr(werkzeug, feld), str) else 0
        setattr(werkzeug, feld, werte.get(feld, leer))
    werkzeug.beispiel = {feld for feld in felder if feld in werte}


def zeile(werkzeug):
    """Eine Zeile für die Liste: „T3  Schaftfräser Ø 12 · z 3 · VHM“, mit eigenem
    Namen „T3  Fräser VHM 12 · Schaftfräser Ø 12 · z 3 · VHM“; je Art, was sie
    hat: „T4  Gewindebohrer rechts Ø 10 · P 1.5 · HSS“.

    Zahlen mit Punkt; die Oberfläche setzt ihr Dezimalzeichen ein. Maße im
    gewählten Maßsystem (in inch „Ø 0.5“).
    """
    w = werkzeug
    werte = {"nummer": w.nummer, "art": art_text(w.art), "werte": " · ".join(merkmale(w))}
    if w.name:
        return tr("wv.zeile.name", name=w.name, **werte)
    return tr("wv.zeile", **werte)


def merkmale(werkzeug):
    """Was ein Werkzeug in der Liste kennzeichnet – je Art, was sie hat:
    [„Ø 12“, „z 3“, „VHM“], beim Gewinde die Steigung, beim Drehwerkzeug der Eckenradius."""
    w = werkzeug
    teile = []
    if hat_feld(w, "durchmesser"):
        teile.append("Ø " + (_laenge_text(w.durchmesser) if w.durchmesser else "?"))
    if hat_feld(w, STEIGUNG) and w.steigung:
        teile.append(steigung_mit_einheit(w.steigung))
    if hat_feld(w, "schneidenbreite") and w.schneidenbreite:
        teile.append(f"b {_laenge_text(w.schneidenbreite)}")
    if ARTDATEN[w.art].gruppe == GRUPPE_DREHEN and w.eckradius:
        teile.append(f"r {_laenge_text(w.eckradius)}")
    if hat_feld(w, "schneiden"):
        teile.append(f"z {w.schneiden}")
    if hat_feld(w, "schneidstoff"):
        teile.append(schneidstoff_text(w.schneidstoff))
    return teile


def steigung_anzeige(mm):
    """Die Steigung als Zahl im gewählten Maßsystem: mm, in inch Gänge je Zoll (2 Stellen)."""
    if einheiten.in_zoll():
        return round(_ZOLL / mm, 2) if mm > 0 else 0.0
    return round(mm, 4)


def steigung_text(mm):
    """Eine Steigung, wie sie gezeigt wird: in mm („1.5“), in inch als Gänge je Zoll („13“)."""
    return f"{steigung_anzeige(mm):g}"


def steigung_lesen(wert):
    """Eine eingetippte Steigung in mm: in inch sind es Gänge je Zoll."""
    if einheiten.in_zoll():
        return _ZOLL / wert if wert > 0 else 0.0
    return wert


def steigung_mit_einheit(mm):
    """„P 1.5“, in inch „13 TPI“ – für Liste und Sätze."""
    if einheiten.in_zoll():
        return tr("wv.steigung.zoll", wert=steigung_text(mm))
    return f"P {steigung_text(mm)}"


def spitzenwinkel_fuer_cam(werkzeug):
    """Der Spitzenwinkel in Grad: eingetragen, sonst der übliche der Art (Bohrer 118°)."""
    return wert(werkzeug, "spitzenwinkel") or SPITZENWINKEL_BOHRER


def beispielname(werkzeug):
    """Ein Name aus den Angaben, solange keiner eingetragen ist: „Schaftfräser T1 VHM D12 L30“.

    Art, T-Nummer, Schneidstoff, Durchmesser, Schneidenlänge – Zahlen immer
    mit Punkt, denn der Name ist für die Steuerung; die Maße im gewählten
    Maßsystem („D0.5 L1“ in inch).
    """
    w = werkzeug
    teile = [art_text(w.art), f"T{w.nummer}"]
    if hat_feld(w, "schneidstoff"):
        teile.append(schneidstoff_text(w.schneidstoff))
    if hat_feld(w, "durchmesser") and w.durchmesser:
        teile.append(f"D{_laenge_text(w.durchmesser)}")
    if hat_feld(w, STEIGUNG) and w.steigung:
        teile.append(f"P{steigung_text(w.steigung)}")
    if hat_feld(w, "schneidenbreite") and w.schneidenbreite:
        teile.append(f"B{_laenge_text(w.schneidenbreite)}")
    if ARTDATEN[w.art].gruppe == GRUPPE_DREHEN and w.eckradius:
        teile.append(f"R{_laenge_text(w.eckradius)}")
    if hat_feld(w, "schneidenlaenge") and w.schneidenlaenge:
        teile.append(f"L{_laenge_text(w.schneidenlaenge)}")
    return " ".join(teile)


def _laenge_text(mm):
    """Eine Länge im gewählten Maßsystem, mit Punkt: „12“, in inch „0.5“."""
    return f"{einheiten.gerundet(mm, einheiten.LAENGE):g}"


def anzeigename(werkzeug):
    """Der eingetragene Name, sonst der Beispielname – so heißt das Werkzeug in CAM."""
    return werkzeug.name or beispielname(werkzeug)


def passt(werkzeug, suche):
    """Findet die Suche das Werkzeug? Jedes Wort muss in Zeile oder Bezeichnung vorkommen.

    Ohne Groß/klein; Komma und Punkt gelten gleich („10,5“ findet Ø 10.5),
    das Ø darf fehlen oder dabei sein („ø12“ findet Ø 12).
    """

    def einheitlich(text):
        return text.lower().replace(",", ".").replace("ø", "")

    text = einheitlich(f"{zeile(werkzeug)} {anzeigename(werkzeug)} {werkzeug.bezeichnung}")
    return all(wort in text for wort in einheitlich(suche).split())


def kurz(werkzeug):
    """Art und Durchmesser ohne Nummer: „Schaftfräser Ø 12“ – für Sätze über ein Werkzeug.
    Arten ohne Durchmesser (Drehwerkzeuge) nur mit ihrem Namen."""
    if not hat_feld(werkzeug, "durchmesser"):
        return art_text(werkzeug.art)
    durchmesser = _laenge_text(werkzeug.durchmesser) if werkzeug.durchmesser else "?"
    return f"{art_text(werkzeug.art)} Ø {durchmesser}"


class BeschaedigteDatei(Exception):
    """Die Datei der Bibliothek ließ sich nicht lesen; `beiseite` ist die gesicherte Kopie."""

    def __init__(self, fehler, beiseite):
        super().__init__(str(fehler))
        self.beiseite = beiseite


class Bibliothek:
    """Werkzeuge und eigene Werkstoffe des Benutzers."""

    def __init__(self, werkzeuge=None, eigene_werkstoffe=None):
        self.werkzeuge = list(werkzeuge or [])
        self.eigene_werkstoffe = list(eigene_werkstoffe or [])

    # --- Werkzeuge --------------------------------------------------------------

    def naechste_nummer(self):
        """Die kleinste T-Nummer, die noch frei ist."""
        belegt = {w.nummer for w in self.werkzeuge}
        nummer = 1
        while nummer in belegt:
            nummer += 1
        return nummer

    def neues_werkzeug(self):
        """Legt einen Schaftfräser mit der nächsten freien Nummer und Beispielwerten an."""
        werkzeug = Werkzeug(nummer=self.naechste_nummer())
        beispielwerte_setzen(werkzeug, neu=True)
        self.werkzeuge.append(werkzeug)
        return werkzeug

    def kopiere(self, werkzeug):
        """Legt eine Kopie mit neuer Kennung und der nächsten freien Nummer an."""
        kopie = Werkzeug.aus_dict(werkzeug.als_dict())
        kopie.kennung = uuid.uuid4().hex
        kopie.nummer = self.naechste_nummer()
        self.werkzeuge.append(kopie)
        return kopie

    def entferne(self, werkzeug):
        self.werkzeuge.remove(werkzeug)

    def mit_nummer(self, nummer, ausser=None):
        """Ein anderes Werkzeug mit dieser T-Nummer, oder None."""
        return next((w for w in self.werkzeuge if w.nummer == nummer and w is not ausser), None)

    def mit_name(self, name, ausser=None):
        """Ein anderes Werkzeug mit diesem eingetragenen Namen (groß/klein gleich), oder None."""
        name = name.strip().lower()
        if not name:
            return None
        return next(
            (w for w in self.werkzeuge if w.name.strip().lower() == name and w is not ausser), None
        )

    def sortierte_werkzeuge(self):
        return sorted(self.werkzeuge, key=lambda w: (w.nummer, w.durchmesser))

    # --- Werkstoffe -------------------------------------------------------------

    def alle_werkstoffe(self):
        """Eigene und mitgelieferte Werkstoffe."""
        return self.eigene_werkstoffe + ws.mitgelieferte()

    # --- Speichern und Laden ----------------------------------------------------

    def als_dict(self):
        return {
            "format": FORMAT,
            "werkstoffe": [w.als_dict() for w in self.eigene_werkstoffe],
            "werkzeuge": [w.als_dict() for w in self.sortierte_werkzeuge()],
        }

    @classmethod
    def aus_dict(cls, daten):
        return cls(
            [Werkzeug.aus_dict(w) for w in daten.get("werkzeuge", []) if isinstance(w, dict)],
            [
                ws.Werkstoff.aus_dict(w, eigen=True)
                for w in daten.get("werkstoffe", [])
                if isinstance(w, dict) and w.get("kennung")
            ],
        )

    def kopie(self):
        """Eine unabhängige Kopie – daran arbeitet der Dialog bis OK."""
        return copy.deepcopy(self)

    def gleich(self, andere):
        """Gleicher Inhalt? Dafür, ob der Dialog nach Änderungen fragen muss."""
        return self.als_dict() == andere.als_dict()

    def speichern(self, pfad=None):
        """Schreibt erst in eine Zwischendatei und ersetzt dann; die vorige Fassung bleibt als .bak.

        So bleibt bei einem Absturz mitten im Schreiben immer eine lesbare Datei.
        """
        pfad = pfad or datei_pfad()
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        zwischen = pfad + ".neu"
        with open(zwischen, "w", encoding="utf-8") as datei:
            json.dump(self.als_dict(), datei, ensure_ascii=False, indent=1)
        if os.path.exists(pfad):
            os.replace(pfad, pfad + ".bak")
        os.replace(zwischen, pfad)

    @classmethod
    def laden(cls, pfad=None):
        """Liest die Bibliothek; ohne Datei ist sie leer.

        Ist die Datei unlesbar, wird sie beiseitegelegt (nichts geht verloren)
        und BeschaedigteDatei geworfen – der Dialog sagt das und beginnt leer.
        """
        pfad = pfad or datei_pfad()
        if not os.path.exists(pfad):
            return cls()
        try:
            with open(pfad, encoding="utf-8") as datei:
                daten = json.load(datei)
            if not isinstance(daten, dict):
                raise ValueError("kein JSON-Objekt")
            return cls.aus_dict(daten)
        except (OSError, ValueError) as fehler:
            beiseite = f"{pfad}.defekt-{time.strftime('%Y%m%d-%H%M%S')}"
            os.replace(pfad, beiseite)
            raise BeschaedigteDatei(fehler, beiseite) from None
