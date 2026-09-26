# SPDX-License-Identifier: LGPL-2.1-or-later
"""Werkzeughalter (W-002 Stufe D, spezifikation_halter.md).

Ein Halter sitzt zwischen Spindelnase und Werkzeug. Seine Kontur läuft von
der Spindelnase zum Werkzeug hin, in Abschnitten: je Länge, Ø oben (zur
Spindel) und Ø unten (zum Werkzeug) – gleiche Ø sind ein Zylinder, sonst ein
Kegel, rund um die Werkzeugachse. Was in der Spindel steckt, zählt nicht.
Die Spanntiefe sagt, wie tief der Schaft im Halter steckt; damit schätzt
werkzeuge.laenge_mit_halter() die Länge ab Spindelnase, solange niemand sie
gemessen hat.

Die Halter stehen in der Werkzeugbibliothek (werkzeuge.Bibliothek.halter),
jedes Werkzeug nennt die Kennung seines Halters. Läuft ohne Oberfläche.
"""

import uuid
from dataclasses import dataclass, field

from . import einheiten
from .sprache import tr
from .werkstoffe import mit_dezimalzeichen

# Vorlagen zum Anfangen: typische Maße an SK40 (Flansch Ø63 × 16 mm), keine
# Katalogwerte – (Spanntiefe, Abschnitte (Länge, Ø oben, Ø unten)), alles mm.
_VORLAGEN = {
    "er16": (20.0, ((16.0, 63.0, 63.0), (34.0, 40.0, 32.0), (20.0, 28.0, 28.0))),
    "er25": (28.0, ((16.0, 63.0, 63.0), (34.0, 48.0, 42.0), (20.0, 42.0, 42.0))),
    "er32": (40.0, ((16.0, 63.0, 63.0), (54.0, 50.0, 50.0))),
    "er40": (45.0, ((16.0, 63.0, 63.0), (64.0, 63.0, 63.0))),
    "schrumpf_6": (26.0, ((16.0, 63.0, 63.0), (64.0, 27.0, 21.0))),
    "schrumpf_12": (36.0, ((16.0, 63.0, 63.0), (64.0, 32.0, 24.0))),
    "weldon_20": (50.0, ((16.0, 63.0, 63.0), (47.0, 50.0, 50.0))),
    "hydro_20": (50.0, ((16.0, 63.0, 63.0), (64.0, 50.0, 50.0))),
    "aufsteck_22": (0.0, ((16.0, 63.0, 63.0), (34.0, 48.0, 48.0))),
    "bohrfutter": (30.0, ((16.0, 63.0, 63.0), (84.0, 50.0, 45.0))),
    "vdi30_er25": (28.0, ((40.0, 55.0, 55.0), (20.0, 42.0, 42.0))),
}
VORLAGEN = tuple(_VORLAGEN)  # in der Reihenfolge des Menüs


def vorlage_text(schluessel):
    """Name einer Vorlage: „Spannzangenfutter ER32 · SK40“ …"""
    return {
        "er16": tr("halter.vorlage.er16"),
        "er25": tr("halter.vorlage.er25"),
        "er32": tr("halter.vorlage.er32"),
        "er40": tr("halter.vorlage.er40"),
        "schrumpf_6": tr("halter.vorlage.schrumpf_6"),
        "schrumpf_12": tr("halter.vorlage.schrumpf_12"),
        "weldon_20": tr("halter.vorlage.weldon_20"),
        "hydro_20": tr("halter.vorlage.hydro_20"),
        "aufsteck_22": tr("halter.vorlage.aufsteck_22"),
        "bohrfutter": tr("halter.vorlage.bohrfutter"),
        "vdi30_er25": tr("halter.vorlage.vdi30_er25"),
    }[schluessel]


def _zahl(wert):
    """Ein Maß aus der Datei: eine Zahl, nicht negativ; Unlesbares wird 0."""
    try:
        return max(float(wert), 0.0)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class Abschnitt:
    """Ein Stück der Kontur: Zylinder (gleiche Ø) oder Kegel, alles in mm."""

    laenge: float = 0.0  # entlang der Werkzeugachse
    d_oben: float = 0.0  # zur Spindel hin
    d_unten: float = 0.0  # zum Werkzeug hin

    def als_dict(self):
        return {"laenge": self.laenge, "d_oben": self.d_oben, "d_unten": self.d_unten}

    @classmethod
    def aus_dict(cls, daten):
        return cls(
            _zahl(daten.get("laenge")), _zahl(daten.get("d_oben")), _zahl(daten.get("d_unten"))
        )


@dataclass
class Halter:
    """Ein Halter – eine Beschreibung, kein einzelnes Stück: Mehrere Werkzeuge können
    denselben haben."""

    kennung: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    bezeichnung: str = ""  # frei: Hersteller, Bestellnummer …
    spanntiefe: float = 0.0  # mm: so tief steckt der Schaft im Halter
    abschnitte: list = field(default_factory=list)  # von der Spindelnase zum Werkzeug hin

    @property
    def laenge(self):
        """Von der Spindelnase bis zur Nase des Halters, in mm (im Katalog meist „A“)."""
        return sum(a.laenge for a in self.abschnitte)

    @property
    def groesster_durchmesser(self):
        return max((max(a.d_oben, a.d_unten) for a in self.abschnitte), default=0.0)

    def radius_bei(self, abstand):
        """Der Radius im Abstand `abstand` (mm) unter der Spindelnase – im Kegel dazwischen
        geradlinig; 0 außerhalb des Halters. An einer Stufe gilt der größere Radius."""
        if abstand < 0:
            return 0.0
        oben = 0.0
        radius = 0.0
        for a in self.abschnitte:
            unten = oben + a.laenge
            if oben <= abstand <= unten and a.laenge > 0:
                anteil = (abstand - oben) / a.laenge
                radius = max(radius, (a.d_oben + anteil * (a.d_unten - a.d_oben)) / 2)
            oben = unten
        return radius

    def kontur(self):
        """Die Kontur als Punkte (Abstand unter der Spindelnase, Radius) von oben nach unten –
        je Abschnitt Anfang und Ende; zum Zeichnen und für Drehkörper."""
        punkte = []
        oben = 0.0
        for a in self.abschnitte:
            if a.laenge <= 0:
                continue
            punkte.append((oben, a.d_oben / 2))
            oben += a.laenge
            punkte.append((oben, a.d_unten / 2))
        return punkte

    def als_dict(self):
        return {
            "kennung": self.kennung,
            "name": self.name,
            "bezeichnung": self.bezeichnung,
            "spanntiefe": self.spanntiefe,
            "abschnitte": [a.als_dict() for a in self.abschnitte],
        }

    @classmethod
    def aus_dict(cls, daten):
        """Liest einen Eintrag; Unlesbares wird durch den Standardwert ersetzt."""
        h = cls()
        h.kennung = str(daten.get("kennung") or h.kennung)
        h.name = str(daten.get("name") or "")
        h.bezeichnung = str(daten.get("bezeichnung") or "")
        h.spanntiefe = _zahl(daten.get("spanntiefe"))
        abschnitte = daten.get("abschnitte")
        if isinstance(abschnitte, list):
            h.abschnitte = [Abschnitt.aus_dict(a) for a in abschnitte if isinstance(a, dict)]
        return h


def aus_vorlage(schluessel):
    """Ein neuer Halter aus einer Vorlage – mit Beispielmaßen, die die Bezeichnung nennt."""
    spanntiefe, abschnitte = _VORLAGEN[schluessel]
    return Halter(
        name=vorlage_text(schluessel),
        bezeichnung=tr("halter.beispielmasse"),
        spanntiefe=spanntiefe,
        abschnitte=[Abschnitt(*werte) for werte in abschnitte],
    )


def text(halter):
    """Für Listen und Auswahl: der Name – ohne Namen „Halter, 70 mm lang“."""
    if halter.name.strip():
        return halter.name.strip()
    laenge = f"{einheiten.gerundet(halter.laenge, einheiten.LAENGE):g}"
    zeichen = einheiten.gewaehltes_dezimalzeichen() or einheiten.PUNKT
    laenge = mit_dezimalzeichen(laenge, zeichen)
    return tr("halter.ohne_name", laenge=f"{laenge} {einheiten.einheit(einheiten.LAENGE)}")
