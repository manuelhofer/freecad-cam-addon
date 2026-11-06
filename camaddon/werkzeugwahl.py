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

import threading
from dataclasses import dataclass, field

from . import werkzeuge as wz

RAND = 1.0  # mm: so viel Luft bleibt um einen Bohrer im freien Kreis
SCHRUPPEN_ANTEIL = 0.8  # vom freien Kreis darf der Schruppfräser einnehmen
RASTER = 2.0  # mm: so fein sucht masse() den freien Kreis im Boden
FRAESER = (wz.SCHAFTFRAESER, wz.TORUSFRAESER)
BOHRUNG_ANTEIL = 0.8  # so dick darf ein Fräser fürs Bohrungsfräsen höchstens sein (× Bohrungs-Ø)


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


class _Katalogwerkzeug:
    """Ein Werkzeug des Katalogs, nur mit dem, was Suche und Anzeige brauchen – als
    werkzeuge.Werkzeug belegten 140 000 Größen über 300 MB im Fenster, so ein Zehntel."""

    __slots__ = (
        "art", "durchmesser", "schneidenlaenge", "gesamtlaenge", "auskragung", "steigung",
        "faehigkeiten", "name", "hersteller", "artikel", "link",
        "schaft", "hals_d", "hals_laenge", "eckradius",  # für empfehlung._katalog_fraeser
    )  # fmt: skip

    def __init__(self, daten):
        for feld, wert in zip(self.__slots__, daten, strict=True):
            setattr(self, feld, wert)

    @staticmethod
    def daten(reihe, werte, faehigkeiten):
        """Das Tupel in der Reihenfolge der Felder (so geht es aus dem Nebenrechner)."""
        from . import werkzeugkiste as wk

        name, artikel = werte.get("name", ""), werte.get("artikel", "")
        masse = tuple(
            float(werte.get(feld) or 0.0)
            for feld in ("durchmesser", "schneidenlaenge", "gesamtlaenge", "auskragung", "steigung")
        )
        link = werte.get("link") or reihe.link or wk.suche(reihe.hersteller, artikel, name)
        form = tuple(
            float(werte.get(feld) or 0.0)
            for feld in ("schaft", "hals_d", "hals_laenge", "eckradius")
        )
        return (reihe.art, *masse, faehigkeiten, name, reihe.hersteller, artikel, link, *form)


def katalog_werkzeuge():
    """Alle Werkzeuge des Katalogs der Hersteller, nur mit Maßen (_Katalogwerkzeug; einmal gebaut;
    auch aus einem Faden – gui_bearbeitung_beta.im_katalog: ohne Zwischenspeicher der
    Werkzeugkiste dauert das erste Mal 7 s)."""
    with _KATALOG_SPERRE:
        if not _KATALOG:
            from . import werkzeugkiste as wk

            _KATALOG.extend(_Katalogwerkzeug(d) for d in _katalog_daten(wk.reihen()))
    return _KATALOG


def _katalog_daten(reihen):
    ergebnis = []
    for reihe in reihen:
        gemeinsam = reihe.gemeinsam.get("faehigkeiten", {})
        for groesse in reihe.groessen:
            eigene = groesse.get("faehigkeiten")
            faehig = {**gemeinsam, **eigene} if eigene else gemeinsam
            ergebnis.append(_Katalogwerkzeug.daten(reihe, {**reihe.gemeinsam, **groesse}, faehig))
    return ergebnis


def katalog_daten():
    """Im Nebenrechner: der Katalog als Tupel (_Katalogwerkzeug.daten) – die geprüften Reihen
    belegen über 400 MB; so bleiben sie aus dem Fenster. Danach gibt der Arbeiter sie frei."""
    import gc

    from . import werkzeugkiste as wk
    from . import werkzeugkiste_datei as wd

    daten = _katalog_daten(wk.reihen())
    wd._mitgeliefert = None
    wd._basis = None
    gc.collect()
    return daten


def _je_mass_einer(werkzeuge, schluessel, hoechstens):
    """Je Maß (`schluessel(w)`) einer – der mit Link zuerst –, höchstens `hoechstens`."""
    gesehen, auswahl = set(), []
    for w in sorted(werkzeuge, key=lambda w: not getattr(w, "link", "")):
        k = schluessel(w)
        if k in gesehen:
            continue
        gesehen.add(k)
        auswahl.append(w)
        if len(auswahl) >= hoechstens:
            break
    return auswahl


def gewindebohrer_im_katalog(kernloch_d, katalog, hoechstens=3):
    """Gewindebohrer (rechts) des Katalogs, deren Kernloch `kernloch_d` ist (gewinde.GLEICH_D) –
    je Gewinde (Ø × Steigung) einer, das am besten passende zuerst (Gedächtnis „Empfehlen über das
    Magazin hinaus“)."""
    from . import gewinde as gw

    gut = [
        w
        for w in katalog
        if w.art == wz.GEWINDEBOHRER_RECHTS
        and (w.steigung or 0) > 0
        and abs(gw.kernloch(w.durchmesser, w.steigung) - kernloch_d) <= gw.GLEICH_D
    ]
    # Das Kernloch am nächsten zuerst (M8 × 1,25 vor 5/16-18 UNC bei Ø 6,8), dann das gröbere.
    gut.sort(key=lambda w: (round(abs(gw.kernloch(w.durchmesser, w.steigung) - kernloch_d), 2),
                            -w.steigung))  # fmt: skip
    return _je_mass_einer(
        gut, lambda w: (round(w.durchmesser, 2), round(w.steigung, 3)), hoechstens
    )


def bohrer_im_katalog(durchmesser, tiefe, katalog, hoechstens=3, art=wz.BOHRER):
    """Bohrer (oder mit `art` Reibahlen) des Katalogs mit genau diesem Ø (auf 0,01 mm), die
    `tiefe` erreichen – keine Wendeplattenbohrer; je Hersteller einer, die kürzesten zuerst (am
    steifsten)."""
    gut = [
        w
        for w in katalog
        if w.art == art
        and abs(w.durchmesser - durchmesser) <= 0.005
        and not w.faehigkeiten.get("wendeplatten")
        and (not tiefe or (w.schneidenlaenge or w.gesamtlaenge or 0) >= tiefe - 1e-6)
    ]
    gut.sort(key=lambda w: w.schneidenlaenge or w.gesamtlaenge or 0)
    return _je_mass_einer(gut, lambda w: getattr(w, "hersteller", ""), hoechstens)


def gewindefraeser_im_katalog(kernloch_d, tiefe, katalog, hoechstens=3):
    """[(Gewindefräser, Gewinde)] des Katalogs, deren Steigung zum Kernloch `kernloch_d` ein
    Gewinde der Tabelle ergibt (gewinde_bahn.gewinde_fuer) und die mit Luft hineinpassen – je
    Gewinde einer, das gröbste zuerst, darin der dickste Fräser (am steifsten). Was `tiefe` nicht
    erreicht (Auskragung bzw. Schneidenlänge bekannt und kürzer), fällt weg."""
    from . import gewinde_bahn as gfb

    gut = []
    for w in katalog:
        if w.art != wz.GEWINDEFRAESER or (w.steigung or 0) <= 0 or w.durchmesser <= 0:
            continue
        if w.durchmesser > kernloch_d - 2 * gfb.LUFT + gfb.GLEICH:
            continue
        reicht = getattr(w, "auskragung", 0.0) or w.schneidenlaenge or 0.0
        if tiefe and reicht and reicht < tiefe - 1e-6:
            continue
        gewinde = gfb.gewinde_fuer(kernloch_d, w.steigung)
        if gewinde is not None:
            gut.append((w, gewinde))
    gut.sort(key=lambda e: (-e[1].steigung, -e[0].durchmesser, not getattr(e[0], "link", "")))
    gesehen, auswahl = set(), []
    for w, gewinde in gut:
        if gewinde.name in gesehen:
            continue
        gesehen.add(gewinde.name)
        auswahl.append((w, gewinde))
        if len(auswahl) >= hoechstens:
            break
    return auswahl


def fraeser_fuer_bohrung(durchmesser, tiefe, katalog, hoechstens=3):
    """Fräser des Katalogs fürs Bohrungsfräsen in Ø `durchmesser`: Schaft- oder Torusfräser
    zwischen der Hälfte und BOHRUNG_ANTEIL des Ø (darunter bliebe der Kern lange stehen), die ins
    Volle dürfen (nicht ausdrücklich „nicht mittenschneidend“) und die `tiefe` erreichen – die,
    für die der Hersteller Bohrfräsen nennt, zuerst, dann die dicksten; je Ø einer."""
    gut = []
    for w in katalog:
        if w.art not in FRAESER or not w.durchmesser:
            continue
        if not 0.5 * durchmesser - 1e-6 <= w.durchmesser <= BOHRUNG_ANTEIL * durchmesser + 1e-6:
            continue
        if w.faehigkeiten.get("mittenschneidend") is False:
            continue
        reicht = getattr(w, "auskragung", 0.0) or w.schneidenlaenge or 0.0
        if tiefe and reicht and reicht < tiefe - 1e-6:
            continue
        gut.append(w)
    gut.sort(key=lambda w: (not w.faehigkeiten.get("bohrfraesen"), -w.durchmesser))
    return _je_mass_einer(gut, lambda w: round(w.durchmesser, 2), hoechstens)


def katalog_laden_im_hintergrund():
    """Den Katalog in einem Faden bauen (0,5 s) – läuft er schon oder ist er da: nichts. Fehlen
    noch die geprüften Reihen der Werkzeugkiste, bereitet sie erst ein Nebenrechner vor
    (werkzeugkiste_datei.im_hintergrund_vorbereiten); wer wartet, ruft wieder. Wer danach etwas
    zeigt, sieht aus dem Hauptfaden nach (katalog_bereit) – ein Qt-Zeitgeber aus dem Faden liefe
    nie."""
    from . import nebenrechner as nr
    from . import werkzeugkiste_datei as wd

    global _LAEDT
    if _KATALOG or _LAEDT:
        return
    if not wd.bereit() and not _OHNE_NEBENRECHNER:
        # Die Reihen nicht ins Fenster: Ein Nebenrechner baut den Katalog und schickt die Tupel.
        try:
            auftrag = nr.pool().auftrag("werkzeugwahl", "katalog_daten")
        except Exception:  # noqa: BLE001 – ohne Nebenrechner: die Reihen hier vorbereiten
            auftrag = None
        if auftrag is not None:
            _LAEDT = True

            def fertig(a):
                global _LAEDT, _OHNE_NEBENRECHNER
                _LAEDT = False
                if a.ergebnis is None:
                    _OHNE_NEBENRECHNER = True  # beim nächsten Ruf wie bisher im Fenster
                elif not _KATALOG:
                    with _KATALOG_SPERRE:
                        _KATALOG.extend(_Katalogwerkzeug(d) for d in a.ergebnis)

            auftrag.bei_fertig = fertig
            return
        wd.im_hintergrund_vorbereiten()
        if not wd.bereit():
            return  # der Aufrufer sieht wieder nach und ruft noch einmal
    _LAEDT = True

    def laden():
        global _LAEDT
        try:
            katalog_werkzeuge()
        finally:
            _LAEDT = False

    threading.Thread(target=laden, name="Katalog", daemon=True).start()


_LAEDT = False
_OHNE_NEBENRECHNER = False  # der Nebenrechner lieferte keinen Katalog: im Fenster bauen


def katalog_bereit():
    """Ist der Katalog schon gebaut (dann kostet katalog_werkzeuge() nichts)?"""
    return bool(_KATALOG)


_KATALOG = []
_KATALOG_SPERRE = threading.Lock()


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
