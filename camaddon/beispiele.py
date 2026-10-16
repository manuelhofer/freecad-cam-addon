# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Beispiele auf Wunsch holen (Manuel, 2026-10-16: „ich finde es sollten alle testteile im repo
vorhanden sein ja ... allerdings solte der benutzer auch irgendwie die möglichkeit haben sie nicht
zu laden“).

Die Teile in `beispiele/` stehen im Repository, das Update lädt sie aber nicht mit
(`.gitattributes`: export-ignore – das ZIP von GitHub lässt sie weg). `daten/beispiele.json` nennt
sie mit Größe und Prüfsumme (scripts/beispiele_liste.py schreibt die Liste). Geladen wird von
GitHub in den Ordner der Benutzerdaten von FreeCAD – nicht in den Addon-Ordner, den ein Update
ersetzt. Eine Datei, die schon mit derselben Prüfsumme dort liegt, bleibt.

Läuft ohne Oberfläche; das Fenster steht in gui_beispiele.py.
"""

import hashlib
import json
import os
import urllib.parse
from dataclasses import dataclass

from . import ADDON_ORDNER

LISTE = os.path.join(ADDON_ORDNER, "daten", "beispiele.json")
ADRESSE = "https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/{pfad}"
ZEITLIMIT_S = 60  # je Datei


@dataclass(frozen=True)
class Beispiel:
    """Eine Datei aus `beispiele/`."""

    pfad: str  # im Repository, „beispiele/…“
    bytes: int
    sha256: str

    @property
    def name(self):
        """Der Pfad unter `beispiele/` – so heißt sie auch im Zielordner."""
        return self.pfad.split("/", 1)[1] if "/" in self.pfad else self.pfad


def liste(datei=LISTE):
    """[Beispiel] aus der Liste; [] ohne Liste."""
    try:
        with open(datei, encoding="utf-8") as quelle:
            daten = json.load(quelle)
    except (OSError, ValueError):
        return []
    return [
        Beispiel(e["pfad"], int(e["bytes"]), str(e["sha256"])) for e in daten.get("dateien", [])
    ]


def ordner():
    """Wohin die Beispiele kommen: …/CamAddon/beispiele in den Benutzerdaten von FreeCAD."""
    import FreeCAD

    return os.path.join(FreeCAD.getUserAppDataDir(), "CamAddon", "beispiele")


def ziel(beispiel, wohin):
    return os.path.join(wohin, *beispiel.name.split("/"))


def pruefsumme(daten):
    return hashlib.sha256(daten).hexdigest()


def schon_da(beispiel, wohin):
    """Liegt die Datei schon so im Zielordner (Größe und Prüfsumme)?"""
    pfad = ziel(beispiel, wohin)
    try:
        if os.path.getsize(pfad) != beispiel.bytes:
            return False
        with open(pfad, "rb") as quelle:
            return pruefsumme(quelle.read()) == beispiel.sha256
    except OSError:
        return False


def adresse(beispiel):
    return ADRESSE.format(pfad=urllib.parse.quote(beispiel.pfad))


def laden(beispiele, wohin, hole, fortschritt=None):
    """Holt die Beispiele nach `wohin` – `hole(adresse, zeitlimit_s)` gibt die Bytes (installieren.
    hole). `fortschritt(i, anzahl, beispiel)` vor jeder Datei. Gibt (geladen, schon da, [(Beispiel,
    Grund)]) zurück; eine Datei mit falscher Prüfsumme wird nicht geschrieben."""
    geladen, da, fehler = [], [], []
    for i, beispiel in enumerate(beispiele):
        if fortschritt is not None:
            fortschritt(i, len(beispiele), beispiel)
        if schon_da(beispiel, wohin):
            da.append(beispiel)
            continue
        try:
            daten = hole(adresse(beispiel), ZEITLIMIT_S)
        except (OSError, ValueError) as grund:  # kein Netz, nicht gefunden
            fehler.append((beispiel, str(grund)))
            continue
        if pruefsumme(daten) != beispiel.sha256:
            fehler.append((beispiel, "Prüfsumme"))
            continue
        pfad = ziel(beispiel, wohin)
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        with open(pfad + ".teil", "wb") as datei:
            datei.write(daten)
        os.replace(pfad + ".teil", pfad)
        geladen.append(beispiel)
    return geladen, da, fehler
