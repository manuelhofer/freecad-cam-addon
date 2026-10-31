# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Spannmittel (W-042; Manuel, 2026-10-31: „die halter oder aufnahmen einen eigenen knopf …
genau so spannmittel ... eine übersicht von spannmitteln die vorhanden sind … bei den
spannmittteln müsste man sich noch die gedanken machen wie man es macht das man definiert wie er
auf dem tisch aufgespannt ist ... denk dir was aus !“).

**Die Sammlung** (`Sammlung`) sind die Spannmittel, die es in der Werkstatt gibt – eine eigene
Datei neben der Werkzeugverwaltung. Jedes ist eine Beschreibung mit Maßen je Art (`ARTEN`,
`FELDER`): Schraubstock, Zentrischspanner, Dreibackenfutter, Spannpratzen, Nullpunktspannsystem,
Spannplatte. Daraus baut koerper() einen einfachen Körper – fürs Bild und die Kollision; die
Backen liegen am Rohteil an (W-020).

**Die Aufspannung** (`Aufspannung`) sagt, wie das Rohteil eines Jobs auf dem Tisch steht, in vier
Angaben, wie man sie an der Maschine einrichtet:

1. das Spannmittel (eine Kopie steht im Job, so geht die Datei mit auf einen anderen Rechner),
2. darunter, wenn es eins gibt, ein Unterbau – ein Nullpunktspannsystem oder eine Platte: Er hebt
   das Spannmittel um seine Höhe,
3. die Lage auf dem Tisch: X und Y des Bezugspunkts von der Werkstückaufnahme der Maschine aus
   (meist die Tischmitte) und die Drehung um Z in 90°-Schritten. Der Bezugspunkt ist beim
   Schraubstock die Mitte der festen Backe – sie bleibt stehen, wenn ein breiteres Teil kommt –,
   sonst die Mitte des Spannmittels,
4. die Spanntiefe: so viel vom Rohteil steckt in den Backen (bei Pratzen und Platten 0).

Im Bezug des Spannmittels liegt der Ursprung auf dem Tisch unter dem Bezugspunkt, x längs der
Backen, y quer dazu (die Spannrichtung), z nach oben. Beim Schraubstock liegt das Rohteil mit
seiner Seite an der festen Backe bei y 0, beim Zentrischspanner mittig. Daraus folgen der
Vorschlag für den Nullpunkt (nullpunkt_vorschlag) und der Körper im Job (koerper_im_job). Läuft
ohne Oberfläche.
"""

import copy
import json
import math
import os
import time
import uuid
from dataclasses import dataclass, field

from .sprache import tr

DATEINAME = "spannmittel.json"
FORMAT = "camaddon-spannmittel"
VERSION = 1
EIGENSCHAFT = "CamAddonAufspannung"  # am Grundjob: die Aufspannung als JSON
GENAU = 1e-6

SCHRAUBSTOCK, ZENTRISCH, FUTTER, PRATZEN, NULLPUNKT, PLATTE = (
    "schraubstock",
    "zentrisch",
    "futter",
    "pratzen",
    "nullpunkt",
    "platte",
)
ARTEN = (SCHRAUBSTOCK, ZENTRISCH, FUTTER, PRATZEN, NULLPUNKT, PLATTE)  # Reihenfolge der Anzeige
UNTERBAU_ARTEN = (NULLPUNKT, PLATTE)  # was unter einem anderen Spannmittel stehen kann
MIT_BACKEN = (SCHRAUBSTOCK, ZENTRISCH, FUTTER)  # das Rohteil steckt in Backen (Spanntiefe)

# Die Maße je Art, in der Reihenfolge der Felder, mit Beispielwerten für ein neues (mm). Die
# Beispiele sind übliche Größen: ein Schraubstock mit 125er Backen, ein Zentrischspanner wie ein
# 5-Achs-Spanner mit 77er Backen, ein Futter Ø 160 …
FELDER = {
    SCHRAUBSTOCK: (
        ("backenbreite", 125.0),
        ("backenhoehe", 40.0),
        ("spannweite_min", 0.0),
        ("spannweite_max", 160.0),
        ("laenge", 420.0),
        ("breite", 125.0),
        ("hoehe", 115.0),
        ("spanntiefe", 10.0),
    ),
    ZENTRISCH: (
        ("backenbreite", 77.0),
        ("backenhoehe", 20.0),
        ("spannweite_min", 0.0),
        ("spannweite_max", 130.0),
        ("laenge", 210.0),
        ("breite", 77.0),
        ("hoehe", 100.0),
        ("spanntiefe", 3.0),
    ),
    FUTTER: (
        ("durchmesser", 160.0),
        ("hoehe", 80.0),
        ("backenhoehe", 30.0),
        ("backenbreite", 20.0),
        ("spannweite_min", 5.0),
        ("spannweite_max", 160.0),
        ("spanntiefe", 10.0),
    ),
    PRATZEN: (
        ("anzahl", 2.0),
        ("laenge", 100.0),
        ("breite", 30.0),
        ("dicke", 20.0),
        ("hoehe_max", 60.0),
        ("auflage", 10.0),
    ),
    NULLPUNKT: (
        ("durchmesser", 138.0),
        ("laenge", 0.0),
        ("breite", 0.0),
        ("hoehe", 40.0),
    ),
    PLATTE: (
        ("laenge", 400.0),
        ("breite", 300.0),
        ("hoehe", 60.0),
    ),
}
# So dick ist eine Backe (in y), als Anteil der Backenbreite, zwischen den Grenzen (mm) – die
# Kataloge nennen das nicht; für Bild und Kollision reicht es.
BACKE_ANTEIL = 0.2
BACKE_MIN, BACKE_MAX = 15.0, 40.0
FUTTERBACKE_LANG = 0.18  # Anteil am Futter-Ø: so lang ist eine Backe radial
SCHRAUBE_D = 14.0  # mm – die Schraube einer Pratze (M12 mit Mutter)
DREHUNGEN = (0, 90, 180, 270)  # Grad um Z


def art_text(art):
    """Der Name einer Art zum Lesen."""
    return {
        SCHRAUBSTOCK: tr("sm.art.schraubstock"),
        ZENTRISCH: tr("sm.art.zentrisch"),
        FUTTER: tr("sm.art.futter"),
        PRATZEN: tr("sm.art.pratzen"),
        NULLPUNKT: tr("sm.art.nullpunkt"),
        PLATTE: tr("sm.art.platte"),
    }.get(art, art)


def feld_text(feld):
    """Die Beschriftung eines Maßes (FELDER)."""
    return {
        "backenbreite": tr("sm.feld.backenbreite"),
        "backenhoehe": tr("sm.feld.backenhoehe"),
        "spannweite_min": tr("sm.feld.spannweite_min"),
        "spannweite_max": tr("sm.feld.spannweite_max"),
        "laenge": tr("sm.feld.laenge"),
        "breite": tr("sm.feld.breite"),
        "hoehe": tr("sm.feld.hoehe"),
        "spanntiefe": tr("sm.feld.spanntiefe"),
        "durchmesser": tr("sm.feld.durchmesser"),
        "anzahl": tr("sm.feld.anzahl"),
        "dicke": tr("sm.feld.dicke"),
        "hoehe_max": tr("sm.feld.hoehe_max"),
        "auflage": tr("sm.feld.auflage"),
    }.get(feld, feld)


def feld_hilfe(feld):
    """Der Tooltip eines Maßes (FELDER)."""
    return {
        "backenbreite": tr("sm.feld.backenbreite.tooltip"),
        "backenhoehe": tr("sm.feld.backenhoehe.tooltip"),
        "spannweite_min": tr("sm.feld.spannweite_min.tooltip"),
        "spannweite_max": tr("sm.feld.spannweite_max.tooltip"),
        "laenge": tr("sm.feld.laenge.tooltip"),
        "breite": tr("sm.feld.breite.tooltip"),
        "hoehe": tr("sm.feld.hoehe.tooltip"),
        "spanntiefe": tr("sm.feld.spanntiefe.tooltip"),
        "durchmesser": tr("sm.feld.durchmesser.tooltip"),
        "dicke": tr("sm.feld.dicke.tooltip"),
        "hoehe_max": tr("sm.feld.hoehe_max.tooltip"),
        "auflage": tr("sm.feld.auflage.tooltip"),
    }.get(feld, "")


def _zahl(wert, standard=0.0):
    try:
        zahl = float(wert)
    except (TypeError, ValueError):
        return standard
    return zahl if math.isfinite(zahl) and zahl >= 0 else standard


@dataclass
class Spannmittel:
    """Ein Spannmittel – eine Beschreibung, kein einzelnes Stück."""

    kennung: str = field(default_factory=lambda: uuid.uuid4().hex)
    art: str = SCHRAUBSTOCK
    name: str = ""
    hersteller: str = ""
    bezeichnung: str = ""  # frei: Reihe, Bestellnummer …
    artikel: str = ""
    link: str = ""
    quelle: str = ""  # woher die Maße kommen (Katalog)
    masse: dict = field(default_factory=dict)

    def mass(self, feld):
        """Ein Maß in mm – eingetragen, sonst der Beispielwert der Art."""
        if feld in self.masse:
            return _zahl(self.masse[feld])
        return dict(FELDER.get(self.art, ())).get(feld, 0.0)

    @property
    def text(self):
        """Der Name zum Lesen: eingetragen, sonst Hersteller und Art."""
        if self.name:
            return self.name
        return " ".join(t for t in (self.hersteller, art_text(self.art)) if t)

    def als_dict(self):
        return {
            "kennung": self.kennung,
            "art": self.art,
            "name": self.name,
            "hersteller": self.hersteller,
            "bezeichnung": self.bezeichnung,
            "artikel": self.artikel,
            "link": self.link,
            "quelle": self.quelle,
            "masse": {k: float(v) for k, v in self.masse.items()},
        }

    @classmethod
    def aus_dict(cls, daten):
        art = daten.get("art")
        masse = daten.get("masse") or {}
        felder = dict(FELDER.get(art, ()))
        return cls(
            kennung=str(daten.get("kennung") or uuid.uuid4().hex),
            art=art if art in ARTEN else SCHRAUBSTOCK,
            name=str(daten.get("name") or ""),
            hersteller=str(daten.get("hersteller") or ""),
            bezeichnung=str(daten.get("bezeichnung") or ""),
            artikel=str(daten.get("artikel") or ""),
            link=str(daten.get("link") or ""),
            quelle=str(daten.get("quelle") or ""),
            masse={k: _zahl(v) for k, v in masse.items() if k in felder},
        )


def neu(art):
    """Ein neues Spannmittel der Art mit den Beispielmaßen."""
    return Spannmittel(art=art, masse=dict(FELDER[art]))


class BeschaedigteDatei(Exception):
    """Die Datei der Sammlung war unlesbar; sie liegt jetzt unter `beiseite`."""

    def __init__(self, fehler, beiseite):
        super().__init__(str(fehler))
        self.beiseite = beiseite


def datei_pfad():
    """Die Datei der Sammlung beim Benutzer – neben der Werkzeugverwaltung."""
    import FreeCAD

    return os.path.join(FreeCAD.getUserAppDataDir(), "CamAddon", DATEINAME)


class Sammlung:
    """Die Spannmittel der Werkstatt."""

    def __init__(self, spannmittel=None):
        self.spannmittel = list(spannmittel or [])

    def sortiert(self):
        """Nach Art (ARTEN), darin nach Namen."""
        return sorted(
            self.spannmittel,
            key=lambda s: (ARTEN.index(s.art) if s.art in ARTEN else 99, s.text.lower()),
        )

    def mit(self, kennung):
        return next((s for s in self.spannmittel if s.kennung == kennung), None)

    def dazu(self, spannmittel):
        """Nimmt ein Spannmittel auf; der Name bekommt eine Nummer, wenn es ihn schon gibt."""
        spannmittel.name = self._freier_name(spannmittel.text)
        self.spannmittel.append(spannmittel)
        return spannmittel

    def kopiere(self, spannmittel):
        kopie = Spannmittel.aus_dict(spannmittel.als_dict())
        kopie.kennung = uuid.uuid4().hex
        return self.dazu(kopie)

    def entferne(self, spannmittel):
        self.spannmittel.remove(spannmittel)

    def gleiches(self, spannmittel):
        """Ein Spannmittel mit demselben Hersteller und Namen – oder None (für den Katalog: was
        schon da ist, bleibt, wie es ist)."""
        return next(
            (
                s
                for s in self.spannmittel
                if s.hersteller == spannmittel.hersteller and s.name == spannmittel.name
            ),
            None,
        )

    def _freier_name(self, name):
        namen = {s.name for s in self.spannmittel}
        if name not in namen:
            return name
        nummer = 2
        while f"{name} ({nummer})" in namen:
            nummer += 1
        return f"{name} ({nummer})"

    def kopie(self):
        return copy.deepcopy(self)

    def als_dict(self):
        return {
            "format": FORMAT,
            "version": VERSION,
            "spannmittel": [s.als_dict() for s in self.spannmittel],
        }

    def gleich(self, andere):
        return self.als_dict() == andere.als_dict()

    @classmethod
    def aus_dict(cls, daten):
        return cls([Spannmittel.aus_dict(d) for d in daten.get("spannmittel") or []])

    def speichern(self, pfad=None):
        """Erst in eine Zwischendatei, dann ersetzen; die vorige Fassung bleibt als .bak."""
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
        """Liest die Sammlung; ohne Datei ist sie leer. Eine unlesbare Datei wird beiseitegelegt
        (BeschaedigteDatei)."""
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


# --- Aufspannung -------------------------------------------------------------------------------


@dataclass
class Aufspannung:
    """Wie das Rohteil eines Jobs auf dem Tisch steht (siehe oben)."""

    spannmittel: Spannmittel = None
    unterbau: Spannmittel = None
    x: float = 0.0  # mm, der Bezugspunkt von der Werkstückaufnahme aus
    y: float = 0.0
    drehung: int = 0  # Grad um Z (DREHUNGEN)
    spanntiefe: float = -1.0  # mm im Spannmittel; < 0: die des Spannmittels

    @property
    def tiefe(self):
        """So viel steckt vom Rohteil in den Backen (mm); 0 ohne Backen."""
        if self.spannmittel is None or self.spannmittel.art not in MIT_BACKEN:
            return 0.0
        tiefe = self.spanntiefe if self.spanntiefe >= 0 else self.spannmittel.mass("spanntiefe")
        return min(tiefe, self.spannmittel.mass("backenhoehe"))

    @property
    def unterbau_hoehe(self):
        return self.unterbau.mass("hoehe") if self.unterbau is not None else 0.0

    def als_dict(self):
        return {
            "spannmittel": self.spannmittel.als_dict() if self.spannmittel else None,
            "unterbau": self.unterbau.als_dict() if self.unterbau else None,
            "x": self.x,
            "y": self.y,
            "drehung": self.drehung,
            "spanntiefe": self.spanntiefe,
        }

    @classmethod
    def aus_dict(cls, daten):
        spannmittel = daten.get("spannmittel")
        unterbau = daten.get("unterbau")
        drehung = int(_zahl(daten.get("drehung"), 0.0)) % 360
        return cls(
            Spannmittel.aus_dict(spannmittel) if isinstance(spannmittel, dict) else None,
            Spannmittel.aus_dict(unterbau) if isinstance(unterbau, dict) else None,
            _vorzeichen(daten.get("x")),
            _vorzeichen(daten.get("y")),
            drehung if drehung in DREHUNGEN else 0,
            float(daten.get("spanntiefe", -1.0) if _ist_zahl(daten.get("spanntiefe")) else -1.0),
        )


def _ist_zahl(wert):
    try:
        return math.isfinite(float(wert))
    except (TypeError, ValueError):
        return False


def _vorzeichen(wert):
    return float(wert) if _ist_zahl(wert) else 0.0


def aufspannung(job):
    """Die Aufspannung des Jobs – bei einer geschwenkten Ebene die ihres Grundjobs –, oder None."""
    from . import reichweite as rw

    grund = rw.grundjob_von(job)
    text = getattr(grund, EIGENSCHAFT, "") or ""
    if not text:
        return None
    try:
        daten = json.loads(text)
    except ValueError:
        return None
    auf = Aufspannung.aus_dict(daten) if isinstance(daten, dict) else None
    return auf if auf is not None and auf.spannmittel is not None else None


def setze(job, auf):
    """Trägt die Aufspannung am Job ein (None: entfernt sie). Die Spanntiefe gilt auch für die
    Prüfung „von unten gespannt“ (spannung.gespannt)."""
    from . import spannung

    if auf is None:
        if EIGENSCHAFT in job.PropertiesList:
            job.removeProperty(EIGENSCHAFT)
        return
    if EIGENSCHAFT not in job.PropertiesList:
        job.addProperty("App::PropertyString", EIGENSCHAFT, "CAM-Addon", tr("sm.eigenschaft"))
        job.setEditorMode(EIGENSCHAFT, 2)
    text = json.dumps(auf.als_dict(), ensure_ascii=False)
    if getattr(job, EIGENSCHAFT) != text:
        setattr(job, EIGENSCHAFT, text)
    if auf.spannmittel.art in MIT_BACKEN:
        spannung.setze(job, auf.tiefe)
    elif spannung.EIGENSCHAFT in job.PropertiesList:
        spannung.setze(job, 0.0)


# --- Maße am Rohteil ---------------------------------------------------------------------------


def _quer(box, drehung):
    """(längs der Backen, quer – die Spannweite) des Rohteils im Bezug des Spannmittels."""
    if drehung in (90, 270):
        return box.YLength, box.XLength
    return box.XLength, box.YLength


def backe_dicke(sm):
    return max(BACKE_MIN, min(BACKE_MAX, BACKE_ANTEIL * sm.mass("backenbreite")))


def auflage(auf, box):
    """Wo die Unterseite des Rohteils liegt (mm über dem Tisch, mit Unterbau)."""
    sm = auf.spannmittel
    unten = auf.unterbau_hoehe
    if sm.art in (SCHRAUBSTOCK, ZENTRISCH):
        return unten + sm.mass("hoehe") - auf.tiefe
    if sm.art == FUTTER:
        return unten + sm.mass("hoehe") + sm.mass("backenhoehe") - auf.tiefe
    if sm.art in (NULLPUNKT, PLATTE):
        return unten + sm.mass("hoehe")
    return unten  # Pratzen: auf dem Tisch oder dem Unterbau


def rohteil_mitte(auf, box):
    """Die Mitte der Unterseite des Rohteils im Bezug des Spannmittels (x, y, z)."""
    _laengs, quer = _quer(box, auf.drehung)
    y = quer / 2.0 if auf.spannmittel.art == SCHRAUBSTOCK else 0.0
    return (0.0, y, auflage(auf, box))


def _drehen(x, y, grad):
    w = math.radians(grad)
    return x * math.cos(w) - y * math.sin(w), x * math.sin(w) + y * math.cos(w)


def nullpunkt_vorschlag(auf, box):
    """Der Nullpunkt des Jobs von der Werkstückaufnahme aus (x, y, z), wenn das Rohteil mit der
    Hüllbox `box` (im Job) so aufgespannt ist: Seine Unterseite liegt auf der Auflage, seine Mitte
    da, wo das Spannmittel sie hält."""
    mx, my, mz = rohteil_mitte(auf, box)
    dx, dy = _drehen(mx, my, auf.drehung)
    return (
        auf.x + dx - box.Center.x,
        auf.y + dy - box.Center.y,
        mz - box.ZMin,
    )


def hinweise(auf, box):
    """Sätze, wenn das Rohteil nicht in das Spannmittel passt – sonst eine leere Liste."""
    sm = auf.spannmittel
    saetze = []
    laengs, quer = _quer(box, auf.drehung)
    if sm.art in MIT_BACKEN:
        weite = max(laengs, quer) if sm.art == FUTTER else quer
        if weite > sm.mass("spannweite_max") + GENAU:
            saetze.append(
                tr("sm.hinweis.zu_breit", breite=_mm(weite), weite=_mm(sm.mass("spannweite_max")))
            )
        elif weite < sm.mass("spannweite_min") - GENAU:
            saetze.append(
                tr("sm.hinweis.zu_schmal", breite=_mm(weite), weite=_mm(sm.mass("spannweite_min")))
            )
        if auf.tiefe >= box.ZLength - GENAU:
            saetze.append(tr("sm.hinweis.ganz_drin", tiefe=_mm(auf.tiefe)))
        if auf.spanntiefe > sm.mass("backenhoehe") + GENAU:
            saetze.append(tr("sm.hinweis.tiefer_als_backen", backen=_mm(sm.mass("backenhoehe"))))
    if sm.art == PRATZEN and box.ZLength > sm.mass("hoehe_max") + GENAU:
        saetze.append(
            tr("sm.hinweis.pratzen_hoch", hoehe=_mm(box.ZLength), hoch=_mm(sm.mass("hoehe_max")))
        )
    return saetze


def _mm(wert):
    from . import einheiten

    return f"{einheiten.text(wert, einheiten.LAENGE)} {einheiten.einheit(einheiten.LAENGE)}"


# --- Körper ------------------------------------------------------------------------------------


def koerper(auf, box):
    """Das Spannmittel (mit Unterbau) im Bezug des Spannmittels als ein Körper (Part.Shape), die
    Backen am Rohteil mit der Hüllbox `box` – fürs Bild und die Kollision."""
    import FreeCAD
    import Part

    teile = []
    if auf.unterbau is not None:
        # Mittig unter dem Grundkörper – beim Schraubstock liegt der Bezug an der festen Backe.
        mitte = _teile(auf.spannmittel, auf, box, 0.0)[0].BoundBox.Center
        for teil in _teile(auf.unterbau, Aufspannung(auf.unterbau), box, 0.0):
            teil.translate(FreeCAD.Vector(mitte.x, mitte.y, 0.0))
            teile.append(teil)
    teile += _teile(auf.spannmittel, auf, box, auf.unterbau_hoehe)
    return Part.makeCompound(teile)


def _box(x0, x1, y0, y1, z0, z1):
    import FreeCAD
    import Part

    return Part.makeBox(
        max(x1 - x0, 0.01), max(y1 - y0, 0.01), max(z1 - z0, 0.01), FreeCAD.Vector(x0, y0, z0)
    )


def _zylinder(radius, z0, z1, x=0.0, y=0.0):
    import FreeCAD
    import Part

    return Part.makeCylinder(max(radius, 0.01), max(z1 - z0, 0.01), FreeCAD.Vector(x, y, z0))


def _teile(sm, auf, box, z):
    """Die Teile eines Spannmittels, unten bei `z`."""
    import FreeCAD

    laengs, quer = _quer(box, auf.drehung)
    if sm.art in (SCHRAUBSTOCK, ZENTRISCH):
        b = sm.mass("backenbreite")
        breite = max(sm.mass("breite"), b)
        hoehe = sm.mass("hoehe")
        hb = min(sm.mass("backenhoehe"), hoehe)
        dicke = backe_dicke(sm)
        laenge = max(sm.mass("laenge"), quer + 2 * dicke)
        if sm.art == SCHRAUBSTOCK:
            y0, y1 = -dicke, -dicke + laenge
            backen = ((-dicke, 0.0), (quer, quer + dicke))
        else:
            y0, y1 = -laenge / 2.0, laenge / 2.0
            backen = ((-quer / 2.0 - dicke, -quer / 2.0), (quer / 2.0, quer / 2.0 + dicke))
        teile = [_box(-breite / 2, breite / 2, y0, y1, z, z + hoehe - hb)]
        teile += [_box(-b / 2, b / 2, a, e, z + hoehe - hb, z + hoehe) for a, e in backen]
        return teile
    if sm.art == FUTTER:
        d = sm.mass("durchmesser")
        hoehe = sm.mass("hoehe")
        hb = sm.mass("backenhoehe")
        bb = sm.mass("backenbreite")
        radius = max(laengs, quer) / 2.0
        lang = FUTTERBACKE_LANG * d
        teile = [_zylinder(d / 2, z, z + hoehe)]
        for winkel in (90.0, 210.0, 330.0):
            backe = _box(radius, radius + lang, -bb / 2, bb / 2, z + hoehe, z + hoehe + hb)
            backe.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), winkel)
            teile.append(backe)
        return teile
    if sm.art == PRATZEN:
        oben = z + box.ZLength
        lang, breit, dick = sm.mass("laenge"), sm.mass("breite"), sm.mass("dicke")
        ueber = sm.mass("auflage")
        anzahl = 4 if sm.mass("anzahl") >= 4 else 2
        teile = []
        for seite in (-1.0, 1.0):
            rand = seite * laengs / 2.0
            innen, aussen = rand - seite * ueber, rand - seite * ueber + seite * lang
            x0, x1 = min(innen, aussen), max(innen, aussen)
            ys = (0.0,) if anzahl == 2 else (-quer / 4.0, quer / 4.0)
            for y in ys:
                teile.append(_box(x0, x1, y - breit / 2, y + breit / 2, oben, oben + dick))
                mitte = (innen + aussen) / 2.0
                teile.append(_zylinder(SCHRAUBE_D / 2, z, oben + dick + 15.0, mitte, y))
        return teile
    if sm.art == NULLPUNKT and sm.mass("durchmesser") > 0 and not sm.mass("laenge"):
        return [_zylinder(sm.mass("durchmesser") / 2, z, z + sm.mass("hoehe"))]
    laenge = sm.mass("laenge") or sm.mass("durchmesser")
    breite = sm.mass("breite") or laenge
    return [_box(-laenge / 2, laenge / 2, -breite / 2, breite / 2, z, z + sm.mass("hoehe"))]


def koerper_im_job(job):
    """Das Spannmittel des Jobs in Koordinaten des Grundjobs, die Backen am Rohteil – None ohne
    Aufspannung oder Rohteil."""
    import FreeCAD

    from . import reichweite as rw

    auf = aufspannung(job)
    stock = getattr(rw.grundjob_von(job), "Stock", None)
    rohteil = getattr(stock, "Shape", None)
    if auf is None or rohteil is None or rohteil.isNull():
        return None
    box = rohteil.BoundBox
    form = koerper(auf, box)
    mx, my, mz = rohteil_mitte(auf, box)
    platz = FreeCAD.Placement()
    platz.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), auf.drehung)
    gedreht = platz.Rotation.multVec(FreeCAD.Vector(mx, my, mz))
    platz.Base = FreeCAD.Vector(box.Center.x, box.Center.y, box.ZMin) - gedreht
    form.Placement = platz.multiply(form.Placement)
    return form


def beschreibung(auf, tr=tr):
    """Ein Satz fürs Einrichtblatt: „Gressel C2 125 auf Nullpunkt …, bei X 0, Y −50, um 90°
    gedreht, 8 mm gespannt“; `tr` in der Sprache des Blatts."""
    teile = [auf.spannmittel.text]
    if auf.unterbau is not None:
        teile.append(tr("sm.beschreibung.auf", unterbau=auf.unterbau.text))
    teile.append(tr("sm.beschreibung.lage", x=_mm(auf.x), y=_mm(auf.y)))
    if auf.drehung:
        teile.append(tr("sm.beschreibung.gedreht", grad=auf.drehung))
    if auf.tiefe > 0:
        teile.append(tr("sm.beschreibung.gespannt", tiefe=_mm(auf.tiefe)))
    return ", ".join(teile)


# --- Katalog der Hersteller --------------------------------------------------------------------

KATALOG = "spannmittel_daten"  # der Ordner der Reihen (katalog)
# So heißen die Maße in manchen Katalogdateien.
_ANDERE_NAMEN = {"spann_min": "spannweite_min", "spann_max": "spannweite_max"}


def katalog_reihen():
    """Die Reihen der Hersteller (katalog.Reihe), nur die mit einer bekannten Art."""
    from . import katalog

    return [r for r in katalog.reihen(KATALOG) if r.art in ARTEN]


def aus_katalog(reihe, groesse):
    """Ein Spannmittel aus einer Größe einer Reihe. Was der Katalog nicht nennt, bekommt den
    Beispielwert der Art, und die Quelle sagt welche."""
    masse = {_ANDERE_NAMEN.get(k, k): v for k, v in groesse["masse"].items()}
    if "hoehe" not in masse and "koerperhoehe" in masse and reihe.art in (SCHRAUBSTOCK, ZENTRISCH):
        masse["hoehe"] = masse["koerperhoehe"] + masse.get("backenhoehe", 0.0)
    felder = dict(FELDER[reihe.art])
    if reihe.art == NULLPUNKT and "laenge" in masse and "durchmesser" not in masse:
        masse["durchmesser"] = 0.0  # eckig
    fehlt = [f for f in felder if f not in masse]
    quelle = reihe.quelle
    if fehlt:
        quelle = tr(
            "sm.katalog.geschaetzt",
            quelle=quelle,
            felder=", ".join(feld_text(f) for f in fehlt),
        ).strip()
    return Spannmittel(
        art=reihe.art,
        name=f"{reihe.hersteller} {groesse['name']}".strip(),
        hersteller=reihe.hersteller,
        bezeichnung=reihe.titel,
        artikel=groesse["artikel"],
        link=groesse["link"] or reihe.link,
        quelle=quelle,
        masse={f: masse.get(f, wert) for f, wert in felder.items()},
    )


def katalog_hinzufuegen(sammlung, auswahl):
    """Nimmt die gewählten Größen in die Sammlung (katalog.auswahl_aufloesen); was es schon gibt
    (gleicher Hersteller und Name), bleibt, wie es ist. Gespeichert wird hier nichts."""
    from . import katalog

    bericht = katalog.Bericht()
    for reihe, groesse in katalog.auswahl_aufloesen(katalog_reihen(), auswahl):
        neu_ = aus_katalog(reihe, groesse)
        if sammlung.gleiches(neu_) is not None:
            bericht.schon_da.append(neu_.name)
            continue
        bericht.neu.append(sammlung.dazu(neu_))
    return bericht
