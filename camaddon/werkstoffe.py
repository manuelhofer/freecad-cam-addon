# SPDX-License-Identifier: LGPL-2.1-or-later
"""Werkstoffe für die Werkzeugverwaltung (W-002): mitgelieferte und eigene.

Die mitgelieferte Liste steht in daten/werkstoffe.json und kommt mit jedem
Update des Addons. Eigene Werkstoffe hält die Bibliothek des Benutzers
(werkzeuge.py). Angezeigt wird ein Werkstoff so, wie man ihn in der
Werkstatt kennt: „1.4301  X5CrNi18-10 · Edelstahl, austenitisch (V2A, 304)“.

Läuft ohne Oberfläche.
"""

import json
import os
import re
from dataclasses import asdict, dataclass, fields

from . import ADDON_ORDNER
from .sprache import tr

DATEI = os.path.join(ADDON_ORDNER, "daten", "werkstoffe.json")

# Die Kennbuchstaben aus den Werkzeugkatalogen, in ihrer üblichen Reihenfolge.
ISO_GRUPPEN = ("P", "M", "K", "N", "S", "H")
# Die Klassen, nach denen Kataloge Schnittwerte nennen (klasse()): Stahl bis 750 N/mm² und
# darüber, rostfrei austenitisch, Guss, Aluminium, Kupfer und Messing, Kunststoff, Titan und
# Nickel, gehärtet.
KLASSEN = ("P1", "P2", "M", "K", "N1", "N2", "N3", "S", "H")
# Stähle bis etwa 750 N/mm² – weich genug für die Werte „Stahl“ jedes Katalogs.
_WEICHE_STAEHLE = ("baustahl", "automatenstahl", "einsatzstahl", "waelzlagerstahl")


@dataclass
class Werkstoff:
    """Ein Werkstoff samt Zustand – „1.2379 geglüht“ und „gehärtet“ sind zwei.

    Zusammensetzung, Härte und Zugfestigkeit sind Text, wie er im Datenblatt
    steht, mit Punkt als Dezimalzeichen; `mit_dezimalzeichen()` zeigt ihn im
    Format der Oberfläche.
    """

    kennung: str  # eindeutig; bei mitgelieferten die Nummer, ggf. mit Zustand („1.2379+H“)
    nummer: str = ""  # Werkstoffnummer, z. B. „1.4301“; Kunststoffe haben keine
    kurzname: str = ""  # Bezeichnung nach chemischer Zusammensetzung, z. B. „X5CrNi18-10“
    gruppe: str = ""  # Schlüssel aus gruppe_text() – bei eigenen auch freier Text
    zustand: str = ""  # Schlüssel aus zustand_text() oder ein Kürzel wie „T6“
    iso: str = "P"  # einer aus ISO_GRUPPEN
    bekannt_als: str = ""  # alte oder gängige Namen: „V2A“, „GG-25“, „EN AW-6082“
    zusammensetzung: str = ""  # Massen-%, z. B. „C ≤ 0.07 · Cr 17.5–19.5“
    haerte: str = ""  # z. B. „≤ 215 HB“, „58–62 HRC“
    zugfestigkeit: str = ""  # N/mm², z. B. „500–700“
    kc11: float = 0.0  # spezifische Schnittkraft kc1.1 in N/mm²; 0 = unbekannt
    mc: float = 0.0  # Anstiegswert der Schnittkraft; 0 = unbekannt
    eigen: bool = False  # vom Benutzer angelegt (änderbar), sonst mitgeliefert

    def als_dict(self):
        """Für die Bibliothek des Benutzers; ohne `eigen`, das ergibt sich beim Laden."""
        daten = asdict(self)
        del daten["eigen"]
        return daten

    @classmethod
    def aus_dict(cls, daten, eigen=False):
        """Liest einen Eintrag; unbekannte Felder werden übergangen, fehlende vorbelegt."""
        bekannt = {f.name for f in fields(cls)} - {"eigen"}
        werte = {k: v for k, v in daten.items() if k in bekannt}
        for zahl in ("kc11", "mc"):
            werte[zahl] = _als_zahl(werte.get(zahl, 0))
        for text in bekannt - {"kc11", "mc"}:
            werte[text] = str(werte.get(text, "") or "")
        if werte["iso"] not in ISO_GRUPPEN:
            werte["iso"] = "P"
        return cls(eigen=eigen, **werte)


def _als_zahl(wert):
    try:
        return float(wert or 0)
    except (TypeError, ValueError):
        return 0.0


_mitgeliefert = None  # die Liste aus daten/werkstoffe.json, einmal gelesen


def mitgelieferte():
    """Die mitgelieferten Werkstoffe, in der Reihenfolge der Datei."""
    global _mitgeliefert
    if _mitgeliefert is None:
        with open(DATEI, encoding="utf-8") as datei:
            daten = json.load(datei)
        _mitgeliefert = [Werkstoff.aus_dict(eintrag) for eintrag in daten["werkstoffe"]]
    return list(_mitgeliefert)


def sortiert(werkstoffe):
    """Nach ISO-Gruppe (P, M, K, N, S, H), darin nach Nummer und Kurzname."""
    return sorted(
        werkstoffe,
        key=lambda w: (ISO_GRUPPEN.index(w.iso), w.nummer or "~", w.kurzname.lower()),
    )


def finde(werkstoffe, kennung):
    """Der Werkstoff mit dieser Kennung, oder None."""
    return next((w for w in werkstoffe if w.kennung == kennung), None)


def klasse(werkstoff):
    """Die Klasse aus KLASSEN, nach der Kataloge Schnittwerte nennen: P1 Bau-, Automaten-,
    Einsatz- und unvergüteter Vergütungsstahl, P2 vergüteter Stahl, Werkzeugstahl und rostfreier
    martensitischer; M, K, S, H wie die ISO-Gruppe; N1 Aluminium, N2 Kupfer, Messing, Bronze,
    N3 Kunststoff."""
    iso, gruppe = werkstoff.iso, werkstoff.gruppe
    if iso == "P":
        weich = gruppe in _WEICHE_STAEHLE or (
            gruppe == "verguetungsstahl" and werkstoff.zustand != "verguetet"
        )
        return "P1" if weich else "P2"
    if iso == "N":
        if gruppe.startswith("aluminium"):
            return "N1"
        return "N3" if gruppe == "kunststoff" else "N2"
    return iso


_klassen = None  # Kennung -> Klasse der mitgelieferten Werkstoffe, einmal gerechnet


def klasse_von(kennung):
    """Die Klasse des mitgelieferten Werkstoffs mit dieser Kennung – "" für eigene und
    unbekannte. Eine Klasse selbst (ist_klasse) ist ihre eigene Klasse: Schnittwerte stehen
    je Klasse (Manuel, 2026-10-03: „wir nehmen die Obergruppen, aber man kann auch für
    einzelne Werkstoffe noch Werte setzen“)."""
    global _klassen
    if kennung in KLASSEN:
        return kennung
    if _klassen is None:
        _klassen = {w.kennung: klasse(w) for w in mitgelieferte()}
    return _klassen.get(kennung, "")


def ist_klasse(kennung):
    """Steht die Kennung für eine Werkstoffklasse (KLASSEN) statt für einen Werkstoff?"""
    return kennung in KLASSEN


def klasse_iso(klasse):
    """Der ISO-Kennbuchstabe der Klasse: P1 und P2 → P, N1 bis N3 → N."""
    return klasse[0]


def neue_kennung(werkstoffe):
    """Eine Kennung für einen eigenen Werkstoff, die es noch nicht gibt."""
    vorhanden = {w.kennung for w in werkstoffe}
    nummer = 1
    while f"eigen-{nummer}" in vorhanden:
        nummer += 1
    return f"eigen-{nummer}"


# --- Anzeige -----------------------------------------------------------------


def gruppe_text(gruppe):
    """Anzeigename einer Werkstoffgruppe; ein freier Text (eigene Werkstoffe) bleibt, wie er ist."""
    return {
        "baustahl": tr("werkstoff.gruppe.baustahl"),
        "automatenstahl": tr("werkstoff.gruppe.automatenstahl"),
        "einsatzstahl": tr("werkstoff.gruppe.einsatzstahl"),
        "verguetungsstahl": tr("werkstoff.gruppe.verguetungsstahl"),
        "waelzlagerstahl": tr("werkstoff.gruppe.waelzlagerstahl"),
        "formenstahl": tr("werkstoff.gruppe.formenstahl"),
        "kaltarbeitsstahl": tr("werkstoff.gruppe.kaltarbeitsstahl"),
        "warmarbeitsstahl": tr("werkstoff.gruppe.warmarbeitsstahl"),
        "edelstahl_austenitisch": tr("werkstoff.gruppe.edelstahl_austenitisch"),
        "edelstahl_ferritisch": tr("werkstoff.gruppe.edelstahl_ferritisch"),
        "edelstahl_martensitisch": tr("werkstoff.gruppe.edelstahl_martensitisch"),
        "edelstahl_duplex": tr("werkstoff.gruppe.edelstahl_duplex"),
        "edelstahl_ph": tr("werkstoff.gruppe.edelstahl_ph"),
        "grauguss": tr("werkstoff.gruppe.grauguss"),
        "sphaeroguss": tr("werkstoff.gruppe.sphaeroguss"),
        "aluminium_knet": tr("werkstoff.gruppe.aluminium_knet"),
        "aluminium_guss": tr("werkstoff.gruppe.aluminium_guss"),
        "kupfer": tr("werkstoff.gruppe.kupfer"),
        "messing": tr("werkstoff.gruppe.messing"),
        "bronze": tr("werkstoff.gruppe.bronze"),
        "titan": tr("werkstoff.gruppe.titan"),
        "nickel": tr("werkstoff.gruppe.nickel"),
        "kunststoff": tr("werkstoff.gruppe.kunststoff"),
    }.get(gruppe, gruppe)


def zustand_text(zustand):
    """Anzeigename eines Zustands; Kürzel wie „T6“ oder „H111“ bleiben, wie sie sind."""
    return {
        "gegluet": tr("werkstoff.zustand.gegluet"),
        "normalgegluet": tr("werkstoff.zustand.normalgegluet"),
        "verguetet": tr("werkstoff.zustand.verguetet"),
        "gehaertet": tr("werkstoff.zustand.gehaertet"),
        "ausgehaertet": tr("werkstoff.zustand.ausgehaertet"),
    }.get(zustand, zustand)


def iso_text(iso):
    """Was der ISO-Kennbuchstabe umfasst, in Worten."""
    return {
        "P": tr("werkstoff.iso.p"),
        "M": tr("werkstoff.iso.m"),
        "K": tr("werkstoff.iso.k"),
        "N": tr("werkstoff.iso.n"),
        "S": tr("werkstoff.iso.s"),
        "H": tr("werkstoff.iso.h"),
    }[iso]


def klasse_text(klasse):
    """Die Klasse in Worten, wie sie in der Werkstoff-Spalte steht: „M – rostfreier Stahl“,
    „P1 – Stahl bis 750 N/mm²“."""
    return tr(f"werkstoff.klasse.{klasse.lower()}")


def anzeige(werkstoff):
    """Eine Zeile: „1.4301  X5CrNi18-10 · Edelstahl, austenitisch (V2A, 304)“."""
    w = werkstoff
    kopf = f"{w.nummer}  {w.kurzname}" if w.nummer else w.kurzname
    gruppe = gruppe_text(w.gruppe)
    if w.zustand:
        gruppe = f"{gruppe}, {zustand_text(w.zustand)}" if gruppe else zustand_text(w.zustand)
    text = f"{kopf} · {gruppe}" if gruppe else kopf
    return f"{text} ({w.bekannt_als})" if w.bekannt_als else text


def mit_dezimalzeichen(text, zeichen):
    """Setzt `zeichen` als Dezimalzeichen ein: „17.5–19.5“ wird auf Deutsch „17,5–19,5“."""
    if zeichen == ".":
        return text
    return re.sub(r"(?<=\d)\.(?=\d)", zeichen, text)


def passt(werkstoff, suche):
    """Findet die Suche den Werkstoff? Jedes Wort muss irgendwo vorkommen, ohne Groß/klein."""
    text = " ".join(
        (
            anzeige(werkstoff),
            werkstoff.zusammensetzung,
            werkstoff.kennung,
            gruppe_text(werkstoff.gruppe),
        )
    ).lower()
    return all(wort in text for wort in suche.lower().split())
