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

# Arten von Werkzeugen – gespeichert als diese festen Wörter.
SCHAFTFRAESER = "schaftfraeser"
TORUSFRAESER = "torusfraeser"
RADIUSFRAESER = "radiusfraeser"
FASENFRAESER = "fasenfraeser"
BOHRER = "bohrer"
ARTEN = (SCHAFTFRAESER, TORUSFRAESER, RADIUSFRAESER, FASENFRAESER, BOHRER)

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
EINSATZARTEN = (VOLLNUT, SCHRUPPEN, DYNAMISCH, SCHLICHTEN, BOHREN, EIGEN)


def datei_pfad():
    """Die Datei der Bibliothek beim Benutzer."""
    return os.path.join(FreeCAD.getUserAppDataDir(), "CamAddon", DATEINAME)


def art_text(art):
    """Anzeigename einer Werkzeugart."""
    return {
        SCHAFTFRAESER: tr("wv.art.schaftfraeser"),
        TORUSFRAESER: tr("wv.art.torusfraeser"),
        RADIUSFRAESER: tr("wv.art.radiusfraeser"),
        FASENFRAESER: tr("wv.art.fasenfraeser"),
        BOHRER: tr("wv.art.bohrer"),
    }[art]


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
        BOHREN: (0.0, 0.0),
        EIGEN: (0.0, 0.0),
    }[art]
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
    spitzenwinkel: float = 0.0  # Grad, nur beim Bohrer; 0 = üblich (SPITZENWINKEL_BOHRER)
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
        w.art = daten.get("art") if daten.get("art") in ARTEN else SCHAFTFRAESER
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


# Beispielwerte je Art für ein neues Werkzeug – grau gezeigt, aber gültig
# (Manuel: wer Ø 12 stehen lässt, will Ø 12).
BEISPIELE = {
    SCHAFTFRAESER: {"durchmesser": 12.0, "schneiden": 3, "schneidenlaenge": 26.0},
    TORUSFRAESER: {"durchmesser": 12.0, "schneiden": 4, "schneidenlaenge": 26.0, "eckradius": 1.0},
    RADIUSFRAESER: {"durchmesser": 12.0, "schneiden": 2, "schneidenlaenge": 24.0},
    FASENFRAESER: {"durchmesser": 12.0, "schneiden": 2, "schneidenlaenge": 6.0},
    BOHRER: {"durchmesser": 12.0, "schneiden": 2, "schneidenlaenge": 60.0},
}
# In inch runde Zoll-Maße (mm, weil metrisch gespeichert): ½", Schneide 1",
# Eckradius 0,03", Fase ¼", Bohrer 2½".
BEISPIELE_ZOLL = {
    SCHAFTFRAESER: {"durchmesser": 12.7, "schneiden": 3, "schneidenlaenge": 25.4},
    TORUSFRAESER: {
        "durchmesser": 12.7,
        "schneiden": 4,
        "schneidenlaenge": 25.4,
        "eckradius": 0.762,
    },
    RADIUSFRAESER: {"durchmesser": 12.7, "schneiden": 2, "schneidenlaenge": 25.4},
    FASENFRAESER: {"durchmesser": 12.7, "schneiden": 2, "schneidenlaenge": 6.35},
    BOHRER: {"durchmesser": 12.7, "schneiden": 2, "schneidenlaenge": 63.5},
}


def beispiele(art):
    """Die Beispielwerte der Art im gewählten Maßsystem."""
    return (BEISPIELE_ZOLL if einheiten.in_zoll() else BEISPIELE)[art]


def beispielwerte_setzen(werkzeug, neu=False):
    """Trägt die Beispielwerte der Art ein und merkt sie in `werkzeug.beispiel`.

    `neu`: in alle Beispielfelder (ein neues Werkzeug); sonst – nach einem
    Wechsel der Art – in die, die noch Beispiel oder leer sind: Der
    Torusfräser bekommt so einen Eckradius und sieht im Bild wie einer aus.
    Beispielfelder, die die neue Art nicht hat (Eckradius), werden 0.
    """
    werte = beispiele(werkzeug.art)
    if neu:
        felder = set(werte)
    else:
        felder = set(werkzeug.beispiel) | {feld for feld in werte if not getattr(werkzeug, feld)}
    for feld in felder:
        setattr(werkzeug, feld, werte.get(feld, 0))
    werkzeug.beispiel = {feld for feld in felder if feld in werte}


def zeile(werkzeug):
    """Eine Zeile für die Liste: „T3  Schaftfräser Ø 12 · z 3 · VHM“, mit eigenem
    Namen „T3  Fräser VHM 12 · Schaftfräser Ø 12 · z 3 · VHM“.

    Zahlen mit Punkt; die Oberfläche setzt ihr Dezimalzeichen ein. Der
    Durchmesser im gewählten Maßsystem (in inch „Ø 0.5“).
    """
    w = werkzeug
    durchmesser = _laenge_text(w.durchmesser) if w.durchmesser else "?"
    werte = {
        "nummer": w.nummer,
        "art": art_text(w.art),
        "durchmesser": durchmesser,
        "schneiden": w.schneiden,
        "schneidstoff": schneidstoff_text(w.schneidstoff),
    }
    if w.name:
        return tr("wv.zeile.name", name=w.name, **werte)
    return tr("wv.zeile", **werte)


def spitzenwinkel_fuer_cam(werkzeug):
    """Der Spitzenwinkel des Bohrers in Grad: eingetragen, sonst der übliche (118°)."""
    return werkzeug.spitzenwinkel or SPITZENWINKEL_BOHRER


def beispielname(werkzeug):
    """Ein Name aus den Angaben, solange keiner eingetragen ist: „Schaftfräser T1 VHM D12 L30“.

    Art, T-Nummer, Schneidstoff, Durchmesser, Schneidenlänge – Zahlen immer
    mit Punkt, denn der Name ist für die Steuerung; die Maße im gewählten
    Maßsystem („D0.5 L1“ in inch).
    """
    w = werkzeug
    teile = [art_text(w.art), f"T{w.nummer}", schneidstoff_text(w.schneidstoff)]
    if w.durchmesser:
        teile.append(f"D{_laenge_text(w.durchmesser)}")
    if w.schneidenlaenge:
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
    """Art und Durchmesser ohne Nummer: „Schaftfräser Ø 12“ – für Sätze über ein Werkzeug."""
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
