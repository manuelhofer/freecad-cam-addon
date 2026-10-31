# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Kataloge der Hersteller für Spannmittel und Halter (W-042; Manuel, 2026-10-31: „das beides
gut vorgefüllt ist oder das halt wie bei den werkzeugen du schon von sehr vielen herstellern die
sachen erstellst ... das die datenbanken schon voll sind“).

Wie die Werkzeugkiste (W-007): je Reihe eines Herstellers ihre Größen mit den Maßen aus seinem
Katalog. Die Reihen stehen als JSON in einem Ordner des Addons (`spannmittel_daten`,
`halter_daten`), je Datei

    {"reihen": [{"hersteller": …, "titel": …, "art"/"typ": …, "link": …, "quelle": …,
                 "groessen": [{"name": …, "artikel": …, "link": …, "masse": {…}}]}]}

`quelle` sagt, woher die Maße kommen und was abgeleitet ist. Wo eine Artikelnummer fehlt, ist sie
nicht belegt. Läuft ohne Oberfläche.
"""

import json
import os
from dataclasses import dataclass, field

ORDNER = os.path.dirname(os.path.abspath(__file__))


@dataclass
class Reihe:
    kennung: str  # „datei:nummer“
    hersteller: str
    titel: str
    art: str  # Spannmittel: spannmittel.ARTEN; Halter: der Typ (schrumpf, hydro …)
    link: str = ""
    quelle: str = ""
    aufnahme: str = ""  # nur Halter: SK40, HSK-A63 …
    groessen: list = field(default_factory=list)  # [{"name", "artikel", "link", "masse"}]

    @property
    def anzahl(self):
        return len(self.groessen)


def _text(wert):
    return str(wert).strip() if isinstance(wert, (str, int, float)) else ""


def _masse(daten):
    masse = {}
    for name, wert in (daten or {}).items():
        try:
            zahl = float(wert)
        except (TypeError, ValueError):
            continue
        if zahl >= 0:
            masse[str(name)] = zahl
    return masse


def lesen(pfad):
    """Die Reihen einer Datei – Unlesbares bleibt draußen (eine leere Liste, wenn die ganze Datei
    unlesbar ist)."""
    try:
        with open(pfad, encoding="utf-8") as datei:
            daten = json.load(datei)
    except (OSError, ValueError):
        return []
    name = os.path.splitext(os.path.basename(pfad))[0]
    reihen = []
    for nummer, reihe in enumerate(daten.get("reihen") or [] if isinstance(daten, dict) else []):
        if not isinstance(reihe, dict):
            continue
        groessen = []
        for groesse in reihe.get("groessen") or []:
            if not isinstance(groesse, dict) or not _text(groesse.get("name")):
                continue
            groessen.append(
                {
                    "name": _text(groesse.get("name")),
                    "artikel": _text(groesse.get("artikel")),
                    "link": _text(groesse.get("link")),
                    "masse": _masse(groesse.get("masse")),
                }
            )
        if not groessen:
            continue
        reihen.append(
            Reihe(
                f"{name}:{nummer}",
                _text(reihe.get("hersteller")),
                _text(reihe.get("titel")),
                _text(reihe.get("art") or reihe.get("typ")),
                _text(reihe.get("link")),
                _text(reihe.get("quelle")),
                _text(reihe.get("aufnahme")),
                groessen,
            )
        )
    return reihen


def reihen(ordner):
    """Alle Reihen der Dateien des Katalogs `ordner` („halter_daten“) – im Addon oder, aus dem
    Download, im Profil (kataloge.ordner) –, nach Hersteller und Titel."""
    from . import kataloge

    pfad = kataloge.ordner(ordner)
    if not os.path.isdir(pfad):
        return []
    alle = []
    for datei in sorted(os.listdir(pfad)):
        if datei.endswith(".json"):
            alle += lesen(os.path.join(pfad, datei))
    return sorted(alle, key=lambda r: (r.hersteller.lower(), r.titel.lower()))


def auswahl_aufloesen(alle, auswahl):
    """[(Reihe, Größe)] zu einer Auswahl: je Eintrag die Kennung einer Reihe (alle Größen) oder
    (Kennung, Nummer der Größe)."""
    nach_kennung = {r.kennung: r for r in alle}
    ergebnis = []
    for eintrag in auswahl:
        kennung, nummer = eintrag if isinstance(eintrag, tuple) else (eintrag, None)
        reihe = nach_kennung.get(kennung)
        if reihe is None:
            continue
        if nummer is None:
            ergebnis += [(reihe, g) for g in reihe.groessen]
        elif 0 <= nummer < len(reihe.groessen):
            ergebnis.append((reihe, reihe.groessen[nummer]))
    return ergebnis


@dataclass
class Bericht:
    """Was „Übernehmen“ gebracht hat: neu angelegt, schon da (blieb, wie es war)."""

    neu: list = field(default_factory=list)
    schon_da: list = field(default_factory=list)
