# SPDX-License-Identifier: LGPL-2.1-or-later
"""Werkzeughalter (W-002 Stufe D, spezifikation_halter.md).

Ein Halter sitzt zwischen Spindelnase und Werkzeug. Seine Kontur läuft von
der Spindelnase zum Werkzeug hin, in Abschnitten: je Länge, Ø oben (zur
Spindel) und Ø unten (zum Werkzeug) – gleiche Ø sind ein Zylinder, sonst ein
Kegel, rund um die Werkzeugachse. Was in der Spindel steckt, zählt nicht.
Die Spanntiefe sagt, wie tief der Schaft im Halter steckt; damit schätzt
werkzeuge.laenge_mit_halter() die Länge ab Spindelnase, solange niemand sie
gemessen hat.

Wie das Werkzeug zur Maschine steht, sagt der Halter (Stufe E, Manuel
2026-09-30): **gerade** – das Werkzeug in der Achse der Aufnahme, wie in einer
Frässpindel oder einem axialen VDI-Halter – oder **gewinkelt** – um `winkel`
gegen die Aufnahmeachse gekippt, um `drehung` um sie gedreht (von der
Bezugsrichtung X der Aufnahme aus), mit der Werkzeugachse `versatz` unter der
Aufnahme; bis dorthin reicht der Kopf. Dort liegt der Bezugspunkt: Von ihm aus
laufen die Kontur und die Länge des Werkzeugs längs der Werkzeugachse; beim
geraden Halter ist es die Spindelnase. lage() rechnet das.

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
    "vdi30_radial": (20.0, ((35.0, 50.0, 50.0), (20.0, 28.0, 28.0))),
    "vdi30_axial": (20.0, ((45.0, 55.0, 55.0), (25.0, 28.0, 28.0))),
    "winkelkopf_90": (25.0, ((30.0, 60.0, 60.0), (20.0, 32.0, 32.0))),
}
VORLAGEN = tuple(_VORLAGEN)  # in der Reihenfolge des Menüs
# Gewinkelte Vorlagen: (Winkel, Drehung in Grad, Versatz, Kopf-Ø in mm).
_GEWINKELT = {
    "vdi30_radial": (90.0, 0.0, 55.0, 55.0),
    "winkelkopf_90": (90.0, 0.0, 110.0, 80.0),
}

GERADE, GEWINKELT = "gerade", "gewinkelt"  # Halter.richtung


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
        "vdi30_radial": tr("halter.vorlage.vdi30_radial"),
        "vdi30_axial": tr("halter.vorlage.vdi30_axial"),
        "winkelkopf_90": tr("halter.vorlage.winkelkopf_90"),
    }[schluessel]


def _zahl(wert):
    """Ein Maß aus der Datei: eine Zahl, nicht negativ; Unlesbares wird 0."""
    try:
        return max(float(wert), 0.0)
    except (TypeError, ValueError):
        return 0.0


def _winkel(wert, standard):
    """Ein Winkel aus der Datei (Grad), endlich; Unlesbares wird `standard`."""
    try:
        zahl = float(wert)
    except (TypeError, ValueError):
        return standard
    return zahl if abs(zahl) < 1e6 else standard


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
    abschnitte: list = field(default_factory=list)  # vom Bezugspunkt zum Werkzeug hin
    richtung: str = GERADE  # GERADE oder GEWINKELT
    winkel: float = 90.0  # Grad zwischen Aufnahmeachse und Werkzeugachse (gewinkelt)
    drehung: float = 0.0  # Grad um die Aufnahmeachse, von ihrer Bezugsrichtung X aus
    versatz: float = 0.0  # mm längs der Aufnahmeachse bis zur Werkzeugachse (gewinkelt)
    kopf_d: float = 0.0  # mm: Ø des Kopfs von der Aufnahme bis zum Bezugspunkt

    @property
    def gewinkelt(self):
        return self.richtung == GEWINKELT

    @property
    def laenge(self):
        """Vom Bezugspunkt bis zur Nase des Halters, in mm – beim geraden Halter von der
        Spindelnase (im Katalog meist „A“)."""
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
            "richtung": self.richtung,
            "winkel": self.winkel,
            "drehung": self.drehung,
            "versatz": self.versatz,
            "kopf_d": self.kopf_d,
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
        h.richtung = GEWINKELT if daten.get("richtung") == GEWINKELT else GERADE
        h.winkel = min(max(_winkel(daten.get("winkel"), 90.0), 0.0), 180.0)
        h.drehung = _winkel(daten.get("drehung"), 0.0)
        h.versatz = _zahl(daten.get("versatz"))
        h.kopf_d = _zahl(daten.get("kopf_d"))
        return h


def lage(halter):
    """Wie das Werkzeug in der Aufnahme sitzt (FreeCAD.Placement im LCS der Aufnahme): sein
    Bezugspunkt und seine Achse, Z von der Spitze weg. Ohne Halter und beim geraden Halter
    keine Verschiebung und keine Drehung. Die Spitze zeigt dann in Richtung
    (sin α · cos β, sin α · sin β, −cos α) mit α = winkel und β = drehung."""
    import FreeCAD

    if halter is None or not halter.gewinkelt:
        return FreeCAD.Placement()
    drehung = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), halter.drehung).multiply(
        FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), -halter.winkel)
    )
    return FreeCAD.Placement(FreeCAD.Vector(0, 0, -halter.versatz), drehung)


def form(halter):
    """Der Halter als Körper im LCS der Aufnahme: die Aufnahme bei Z = 0. Beim geraden zeigt
    das Werkzeug nach −Z; je Abschnitt ein Zylinder oder Kegel. Beim gewinkelten der Kopf –
    ein Zylinder längs der Aufnahmeachse bis über den Bezugspunkt hinaus, um seinen Radius
    (dort sitzt das Winkelgetriebe) –, dann die Abschnitte längs der Werkzeugachse
    (lage()). None ohne Kontur."""
    import FreeCAD
    import Part

    abgang = _abschnitte_form(halter)
    if not halter.gewinkelt:
        return abgang
    teile = [] if abgang is None else [abgang.transformed(lage(halter).toMatrix())]
    if halter.kopf_d > 0 and halter.versatz > 0:
        kopf = Part.makeCylinder(
            halter.kopf_d / 2,
            halter.versatz + halter.kopf_d / 2,
            FreeCAD.Vector(0, 0, 0),
            FreeCAD.Vector(0, 0, -1),
        )
        teile.append(kopf)
    return Part.makeCompound(teile) if teile else None


def _abschnitte_form(halter):
    """Die Abschnitte als Körper: der Bezugspunkt bei Z = 0, das Werkzeug nach −Z."""
    import FreeCAD
    import Part

    teile = []
    oben = 0.0
    nach_unten = FreeCAD.Vector(0, 0, -1)
    for abschnitt in halter.abschnitte:
        if abschnitt.laenge <= 0:
            continue
        basis = FreeCAD.Vector(0, 0, -oben)
        r1, r2 = abschnitt.d_oben / 2, abschnitt.d_unten / 2
        if abs(r1 - r2) < 1e-9:
            if r1 > 0:
                teile.append(Part.makeCylinder(r1, abschnitt.laenge, basis, nach_unten))
        else:
            teile.append(Part.makeCone(r1, r2, abschnitt.laenge, basis, nach_unten))
        oben += abschnitt.laenge
    return Part.makeCompound(teile) if teile else None


def aus_vorlage(schluessel):
    """Ein neuer Halter aus einer Vorlage – mit Beispielmaßen, die die Bezeichnung nennt."""
    spanntiefe, abschnitte = _VORLAGEN[schluessel]
    halter = Halter(
        name=vorlage_text(schluessel),
        bezeichnung=tr("halter.beispielmasse"),
        spanntiefe=spanntiefe,
        abschnitte=[Abschnitt(*werte) for werte in abschnitte],
    )
    if schluessel in _GEWINKELT:
        halter.richtung = GEWINKELT
        halter.winkel, halter.drehung, halter.versatz, halter.kopf_d = _GEWINKELT[schluessel]
    return halter


def text(halter):
    """Für Listen und Auswahl: der Name – ohne Namen „Halter, 70 mm lang“."""
    if halter.name.strip():
        return halter.name.strip()
    laenge = f"{einheiten.gerundet(halter.laenge, einheiten.LAENGE):g}"
    zeichen = einheiten.gewaehltes_dezimalzeichen() or einheiten.PUNKT
    laenge = mit_dezimalzeichen(laenge, zeichen)
    return tr("halter.ohne_name", laenge=f"{laenge} {einheiten.einheit(einheiten.LAENGE)}")
