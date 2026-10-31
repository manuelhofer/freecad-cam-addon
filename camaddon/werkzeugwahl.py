# SPDX-License-Identifier: LGPL-2.1-or-later
"""Welche Werkzeuge für eine Tasche passen – aus der Werkzeugverwaltung und aus dem Katalog der
Hersteller (Plan C2; Manuel, 2026-10-31: „das sinnvollste wäre man sucht grösten bohrer den man hat
bohrt mittig ein loch und fräst dann erstmal im schruppen mit dem möglichst größten spanvolumen das
zeug da raus und schlichtet dann ... wenn man jetzt aber kein platz hat für nen bohrer … einen fräser
der tief genug ist und macht eine helix … oder … einem wendeplatten bohrer oder einem messerkopf
bohrfräsen ... alles möglichkeiten die der benutzer haben muss wenn er die richtigen werkzeuge hat
oder eben vorschläge für werkzeuge bekommt“).

`masse(form, namen)` misst die Tasche aus ihren Flächen: Tiefe (Boden bis Oberkante der Wände),
den größten freien Kreis im Boden (dort geht ein Bohrer hinein) und den kleinsten Innenradius der
senkrechten Rundungen (größer darf der Schlichtfräser nicht sein). `vorschlaege(masse, eigene,
katalog)` sucht je Weg das größte passende Werkzeug – erst unter den eigenen, dann im Katalog, wenn
dort ein größeres steht:

- **vorbohren:** Bohrer, Ø höchstens der freie Kreis minus Rand, so lang wie die Tasche tief,
- **schruppen:** Schaft-, Torus- und Hochvorschubfräser, Ø höchstens 80 % des freien Kreises (die
  Länge zählt nicht: er schruppt in Lagen),
- **ecken:** Fräser für die Rundungen, Ø höchstens 2 × der kleinste Innenradius,
- **bohrfraesen:** Fräser, die laut Hersteller helikal ins Volle dürfen (Fähigkeit „bohrfraesen“ –
  nach der Recherche 2026-10-31 eine Eigenschaft von Fräsern, nicht von Wendeplattenbohrern), Ø bis
  80 % des freien Kreises; mit Ø-Fenster nur, wenn der freie Kreis darin liegt,
- **tauchfraesen:** Fräser, die laut Hersteller tauchen (Tauchfräser), und Wendeplattenbohrer, für
  die der Hersteller die Brillenbohrung nennt; Ø höchstens der freie Kreis
  (tauchfraesen.py taucht in Lagen: die Länge zählt nicht).

Läuft ohne Oberfläche.
"""

from dataclasses import dataclass, field

from . import werkzeuge as wz

RAND = 1.0  # mm: so viel Luft bleibt um einen Bohrer im freien Kreis
SCHRUPPEN_ANTEIL = 0.8  # vom freien Kreis darf der Schruppfräser einnehmen
RASTER = 2.0  # mm: so fein sucht masse() den freien Kreis im Boden
FRAESER = (wz.SCHAFTFRAESER, wz.TORUSFRAESER)


@dataclass
class Masse:
    tiefe: float = 0.0  # mm, Boden bis Oberkante der Wände
    frei: float = 0.0  # mm, Ø des größten freien Kreises im Boden
    innenradius: float = 0.0  # mm, der kleinste der senkrechten Rundungen; 0: keine


@dataclass
class Vorschlag:
    weg: str  # "vorbohren", "schruppen", "ecken", "bohrfraesen", "tauchfraesen"
    eigenes: object = None  # das größte passende aus der Werkzeugverwaltung
    katalog: list = field(default_factory=list)  # größere aus dem Katalog (bis zu 3)
    grenze: float = 0.0  # mm: so groß darf es höchstens sein


def masse(form, namen):
    """Die Maße der Tasche aus ihren Flächen (Namen in `form`)."""
    import FreeCAD
    import Part

    flaechen = [form.getElement(n) for n in namen]
    boeden = [
        f for f in flaechen if f.Surface.__class__.__name__ == "Plane" and _normale(f).z > 0.99
    ]
    ergebnis = Masse()
    if not boeden:
        return ergebnis
    boden = max(boeden, key=lambda f: f.Area)
    z = boden.BoundBox.ZMax
    ergebnis.tiefe = max((f.BoundBox.ZMax for f in flaechen), default=z) - z
    box = boden.BoundBox
    rand = Part.Compound(boden.Edges)
    beste = 0.0
    x = box.XMin + RASTER / 2
    while x < box.XMax:
        y = box.YMin + RASTER / 2
        while y < box.YMax:
            punkt = FreeCAD.Vector(x, y, z)
            if boden.isInside(punkt, 1e-6, True):
                beste = max(beste, rand.distToShape(Part.Vertex(punkt))[0])
            y += RASTER
        x += RASTER
    ergebnis.frei = 2.0 * beste
    radien = []
    for f in flaechen:
        if f.Surface.__class__.__name__ != "Cylinder":
            continue
        achse = f.Surface.Axis
        if abs(achse.z) > 0.99 and not _gewoelbt(f):
            radien.append(f.Surface.Radius)
    ergebnis.innenradius = min(radien) if radien else 0.0
    return ergebnis


def _normale(flaeche):
    u0, u1, v0, v1 = flaeche.ParameterRange
    return flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)


def _gewoelbt(flaeche):
    from . import taschen_wahl as tw

    return tw.gewoelbt(flaeche)


def katalog_werkzeuge():
    """Alle Werkzeuge des Katalogs der Hersteller, nur mit Maßen (einmal gebaut)."""
    if not _KATALOG:
        from . import werkzeugkiste as wk

        for reihe in wk.reihen():
            for werkzeug in wk.werkzeuge(reihe, mit_werten=False):
                _KATALOG.append(werkzeug)
    return _KATALOG


_KATALOG = []


def _passend(werkzeuge, arten, grenze, tiefe, bedingung=None):
    """Die Werkzeuge der Arten bis Ø `grenze`, die `tiefe` erreichen, nach Ø absteigend."""
    gut = []
    for w in werkzeuge:
        if w.art not in arten or not w.durchmesser or w.durchmesser > grenze + 1e-6:
            continue
        laenge = w.schneidenlaenge or w.gesamtlaenge
        if tiefe and laenge and laenge < tiefe - 1e-6:
            continue
        if bedingung is not None and not bedingung(w):
            continue
        gut.append(w)
    return sorted(gut, key=lambda w: -w.durchmesser)


def _vorschlag(weg, arten, grenze, tiefe, eigene, katalog, bedingung=None):
    if grenze <= 0:
        return None
    mein = _passend(eigene, arten, grenze, tiefe, bedingung)
    eigenes = mein[0] if mein else None
    groesser = [
        w
        for w in _passend(katalog, arten, grenze, tiefe, bedingung)
        if eigenes is None or w.durchmesser > eigenes.durchmesser + 1e-6
    ]
    # Je Ø nur einer, die größten zuerst, höchstens drei.
    gesehen, auswahl = set(), []
    for w in groesser:
        schluessel = round(w.durchmesser, 2)
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        auswahl.append(w)
        if len(auswahl) >= 3:
            break
    if eigenes is None and not auswahl:
        return None
    return Vorschlag(weg, eigenes, auswahl, grenze)


def _helix_passt(werkzeug, frei):
    """Darf der Fräser laut Hersteller helikal ins Volle – und, wenn er ein Ø-Fenster nennt, liegt
    der freie Kreis `frei` darin (darunter liefe er auf; darüber geht es mit Räumen weiter)?"""
    f = werkzeug.faehigkeiten
    if not f.get("bohrfraesen"):
        return False
    d_min = float(f.get("helix_d_min") or 0.0)
    return frei >= d_min - 1e-6


def vorschlaege(m, eigene, katalog=None):
    """[Vorschlag] je Weg, für die Tasche mit den Maßen `m`; `eigene`: die Werkzeuge der
    Werkzeugverwaltung, `katalog`: die des Katalogs (ohne: katalog_werkzeuge())."""
    if katalog is None:
        katalog = katalog_werkzeuge()
    ergebnis = []
    if m.frei <= 0:
        return ergebnis
    bohrer = _vorschlag(
        "vorbohren", (wz.BOHRER,), m.frei - 2 * RAND, m.tiefe, eigene, katalog,
        lambda w: not w.faehigkeiten.get("wendeplatten"),
    )  # fmt: skip
    schruppen = _vorschlag("schruppen", FRAESER, SCHRUPPEN_ANTEIL * m.frei, 0.0, eigene, katalog)
    ecken = None
    if m.innenradius:
        ecken = _vorschlag(
            "ecken", (*FRAESER, wz.KUGELFRAESER), 2 * m.innenradius, m.tiefe, eigene, katalog
        )
    bohrfraesen = _vorschlag(
        "bohrfraesen", FRAESER, SCHRUPPEN_ANTEIL * m.frei, 0.0, eigene, katalog,
        lambda w: _helix_passt(w, m.frei),
    )  # fmt: skip
    tauchen = _vorschlag(
        "tauchfraesen", (*FRAESER, wz.BOHRER), m.frei, 0.0, eigene, katalog,
        lambda w: bool(w.faehigkeiten.get("tauchfraesen"))
        or "brillenbohrung" in (w.faehigkeiten.get("bohrverwendung") or []),
    )  # fmt: skip
    return [v for v in (bohrer, schruppen, ecken, bohrfraesen, tauchen) if v is not None]
