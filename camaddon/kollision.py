# SPDX-License-Identifier: LGPL-2.1-or-later
"""Kollision (W-001, Stufe 4c): Stößt beim Abfahren etwas an?

Die Maschine fährt die Bahn ab wie in abfahren.py; zu jeder Zeit steht jeder
Körper an seiner Lage: das Werkzeug der laufenden Operation – Schneide, Hals,
Schaft, Halter – an seiner Aufnahme, das fertige Teil (die Modelle des Jobs)
am Nullpunkt, die Bauteile der Maschine an ihren Gliedern. Geprüft wird
(spezifikation_simulation.md, 4c):

- die Werkzeugseite – das Werkzeug und die Glieder, die es tragen – gegen die
  Werkstückseite – das Teil und die Glieder, die es tragen – und gegen den
  Rest (Bett und alles, was nicht mitfährt);
- die Werkstückseite gegen den Rest;
- die Schneide gegen das Teil nur im Eilgang – im Vorschub schneidet sie.

Zwei Maschinenteile (oder das Teil und ein Maschinenteil), die sich schon in
der Grundstellung berühren, prüft es nicht – so liegen Führungen und
Spannflächen aufeinander; hängen sie nicht an einem gemeinsamen Gelenk, sagt
es ein Hinweis. Das Rohteil zählt nicht: Das Addon trägt kein Material ab.

Den Abstand rechnet OpenCascade (`distToShape`: 0, wenn sich zwei Körper
berühren oder einer im anderen steckt). Hüllquader sortieren Paare aus, die
weit auseinanderliegen. Entlang der Bahn geht es in Schritten, die nie weiter
reichen als der kleinste Abstand minus Warnabstand, mindestens MIN_SCHRITT –
so rutscht keine Berührung zwischen zwei Stellen durch.

Läuft ohne Oberfläche.
"""

import math
import time
from dataclasses import dataclass, field

import FreeCAD

from . import abfahren as ab
from . import halter as hl
from . import reichweite as rw
from .kette import LINEAR
from .sprache import tr

WARNABSTAND = 1.0  # mm, Vorgabe
MIN_SCHRITT = 0.5  # mm: so fein wird es, wo es eng ist
BERUEHRT = 1e-3  # mm: näher gilt als Berührung
GENAU_AB = 5.0  # mm über dem Warnabstand: näher rechnet es genau, sonst reicht der Hüllquader
HOECHSTENS = 200000  # Stellen; danach hört es auf und sagt es
MELDEN_ALLE = 0.1  # s: so oft ruft es den Fortschritt (und fragt, ob es weitergehen soll)

# Was ein Körper ist.
SCHNEIDE, HALS, SCHAFT, HALTER = "schneide", "hals", "schaft", "halter"
MASCHINE, TEIL = "maschine", "teil"
WERKZEUG = (SCHNEIDE, HALS, SCHAFT, HALTER)


# --- Die Körper -----------------------------------------------------------------------------


def werkzeugkoerper(masse, laenge, halter):
    """[(Art, Form)]: Schneide, Hals, Schaft und Halter als Körper im LCS der Aufnahme – die
    Spitze bei Z = −laenge, Z zeigt zur Aufnahme. Die Schneide ist ein Zylinder mit D (der
    Lollipop eine Kugel), der Schaft reicht bis zur Nase des Halters, ohne Halter bis zur
    Gesamtlänge; was darüber bis zur Aufnahme fehlt, kennt niemand."""
    import Part

    teile = []

    def zylinder(art, radius, von, bis):
        if radius > 0 and bis - von > 1e-6:
            teile.append((art, Part.makeCylinder(radius, bis - von, FreeCAD.Vector(0, 0, von))))

    spitze = -laenge
    form = hl.form(halter) if halter is not None else None
    ende = min(spitze + masse.gesamt, 0.0) if masse.gesamt > 0 else 0.0
    if form is not None:
        ende = min(ende, -halter.laenge)
    oben = min(spitze + masse.schneide, ende)
    if masse.kugel:
        radius = masse.durchmesser / 2
        teile.append((SCHNEIDE, Part.makeSphere(radius, FreeCAD.Vector(0, 0, spitze + radius))))
    else:
        zylinder(SCHNEIDE, masse.durchmesser / 2, spitze, oben)
    if masse.hals_laenge > 0 and masse.hals_d > 0:
        hals_ende = min(oben + masse.hals_laenge, ende)
        zylinder(HALS, masse.hals_d / 2, oben, hals_ende)
        oben = hals_ende
    zylinder(SCHAFT, masse.schaft / 2, oben, ende)
    if form is not None:
        teile.append((HALTER, form))
    return teile


@dataclass(eq=False)
class Koerper:
    """Ein Körper mit seiner Form in eigenen Koordinaten; seine Lage in Koordinaten der
    Assembly ist Bewegung seines Glieds · `basis`."""

    name: str  # im Satz, als Subjekt: „der Schaft von T1“, „„Fraeskopf““, „das Teil“
    art: str
    form: object  # Part.Shape
    glied: object
    basis: object  # FreeCAD.Placement
    ecken: list = field(default_factory=list)  # Ecken des Hüllquaders, eigene Koordinaten

    def __post_init__(self):
        box = self.form.BoundBox
        self.ecken = [
            FreeCAD.Vector(x, y, z)
            for x in (box.XMin, box.XMax)
            for y in (box.YMin, box.YMax)
            for z in (box.ZMin, box.ZMax)
        ]


@dataclass(eq=False)
class _Paar:
    a: Koerper
    b: Koerper
    nur_eilgang: bool = False  # die Schneide gegen das Teil


# --- Das Ergebnis ---------------------------------------------------------------------------


@dataclass
class Befund:
    """Eine Berührung oder eine Stelle näher als der Warnabstand – je Operation und Paar die
    schlimmste (die erste, wenn sie gleich schlimm sind)."""

    beruehrung: bool
    eilgang: bool  # in einem Eilgang
    operation: str
    a: str
    b: str
    abstand: float  # mm
    zeit: float  # s seit Beginn des Jobs
    station: int  # auf diese Station fährt die Maschine gerade zu
    satz: int
    punkt: dict  # Punkt im Programm: {"X": …, "Y": …, "Z": …, "A": …}
    stelle: object = None  # FreeCAD.Vector: wo, in Koordinaten der Assembly

    def text(self):
        werte = {
            "operation": self.operation,
            "a": self.a,
            "b": self.b,
            "satz": self.satz,
            "punkt": rw.punkt_text(self.punkt),
        }
        if self.beruehrung and self.eilgang:
            return tr("kb.beruehrung.eilgang", **werte)
        if self.beruehrung:
            return tr("kb.beruehrung", **werte)
        werte["abstand"] = rw.weg_text(self.abstand)
        if self.eilgang:
            return tr("kb.naehe.eilgang", **werte)
        return tr("kb.naehe", **werte)


@dataclass
class Ergebnis:
    warnabstand: float
    befunde: list = field(default_factory=list)
    hinweise: list = field(default_factory=list)
    abgebrochen: bool = False
    stellen: int = 0  # wie oft es gerechnet hat

    @property
    def beruehrungen(self):
        return [b for b in self.befunde if b.beruehrung]


# --- Die Prüfung ----------------------------------------------------------------------------


def kollision(
    abfahrt, job, nullpunkt_des_jobs, bibliothek=None, warnabstand=WARNABSTAND, fortschritt=None
):
    """Prüft die Abfahrt (abfahren.abfahrt) auf Berührungen; gibt ein Ergebnis zurück.

    `fortschritt(anteil)` wird zwischendurch gerufen (0 … 1, höchstens alle
    MELDEN_ALLE Sekunden); gibt es False zurück, hört die Prüfung auf
    (Ergebnis.abgebrochen).
    """
    ergebnis = Ergebnis(warnabstand)
    pruefung = abfahrt.pruefung
    if not abfahrt.stationen or pruefung.werkstueckaufnahme is None:
        return ergebnis
    welt = _Welt(abfahrt, job, nullpunkt_des_jobs, bibliothek, ergebnis, fortschritt)
    try:
        for i in range(len(abfahrt.stationen)):
            welt.station = i
            if not welt.abschnitt(i):
                ergebnis.hinweise.append(
                    tr("kb.zu_viele", anzahl=HOECHSTENS, **_bis_hier(abfahrt, i))
                )
                break
    except _Abbruch:
        ergebnis.abgebrochen = True
        ergebnis.hinweise.append(tr("kb.abgebrochen", **_bis_hier(abfahrt, welt.station)))
    # Berührungen zuerst, dann was nur näher kommt – je nach der Zeit.
    ergebnis.befunde = sorted(
        welt.schlimmste.values(), key=lambda b: (not b.beruehrung, b.zeit, b.a, b.b)
    )
    if fortschritt is not None and not ergebnis.abgebrochen:
        fortschritt(1.0)
    return ergebnis


class _Abbruch(Exception):
    """Der Fortschritt hat „aufhören“ gesagt."""


def _bis_hier(abfahrt, index):
    """Bis wohin geprüft wurde: {"zeit": …, "dauer": …} für die Hinweise."""
    return {
        "zeit": ab.zeit_text(abfahrt.stationen[index].zeit),
        "dauer": ab.zeit_text(abfahrt.dauer),
    }


class _Welt:
    """Alle Körper, die Paare je Operation und das Abtasten der Bahn."""

    def __init__(self, abfahrt, job, nullpunkt, bibliothek, ergebnis, fortschritt=None):
        self.abfahrt = abfahrt
        self.station = 0  # die Station, von der aus es gerade prüft
        self._fortschritt = fortschritt
        self._gemeldet = -math.inf  # wann zuletzt
        self.pruefung = abfahrt.pruefung
        self.verfahren = self.pruefung.verfahren
        self.warn = ergebnis.warnabstand
        self.ergebnis = ergebnis
        self.schlimmste = {}  # (Operation, Name a, Name b) -> Befund
        self._fehler = set()  # Paare, deren Abstand FreeCAD nicht rechnen konnte
        p = self.pruefung

        self.maschine = []
        for glied in p.kette.glieder:
            for bauteil in glied.bauteile:
                form = _lokale_form(bauteil)
                if form is not None:
                    basis = FreeCAD.Placement(self.verfahren.ausgang[bauteil])
                    self.maschine.append(
                        Koerper(f"„{bauteil.Label}“", MASCHINE, form, glied, basis)
                    )
        self.werkstueck_glied = p._glied(p.werkstueckaufnahme)
        form = _teil_form(job)
        self.teil = None
        if form is None:
            ergebnis.hinweise.append(tr("kb.kein_teil"))
        else:
            basis = p._lage(p.werkstueckaufnahme).multiply(
                FreeCAD.Placement(FreeCAD.Vector(nullpunkt), FreeCAD.Rotation())
            )
            self.teil = Koerper(tr("kb.teil"), TEIL, form, self.werkstueck_glied, basis)

        # Je Operation ihr Werkzeug; gleiche Werkzeuge nur einmal gebaut.
        self.werkzeuge = []
        gebaut = {}
        ohne_halter = set()
        for op in abfahrt.operationen:
            nummer = getattr(op.tc, "ToolNumber", 0)
            schluessel = (op.tc.Name, op.aufnahme.Name, round(op.laenge, 6))
            if schluessel not in gebaut:
                halter = rw.werkzeughalter(op.tc, bibliothek)
                masse = rw.werkzeugmasse(op.tc, bibliothek, op.laenge)
                glied = p._glied(op.aufnahme)
                basis = p._lage(op.aufnahme)
                gebaut[schluessel] = [
                    Koerper(_werkzeug_name(art, nummer, halter), art, form, glied, basis)
                    for art, form in werkzeugkoerper(masse, op.laenge, halter)
                ]
                if halter is None and nummer not in ohne_halter:
                    ohne_halter.add(nummer)
                    satz = tr("kb.ohne_halter", werkzeug=f"T{nummer}")
                    ergebnis.hinweise.append(rw.Hinweis(satz, nummer))
            self.werkzeuge.append(gebaut[schluessel])

        self._paare = {}  # Glied der Werkzeugaufnahme -> Paare ohne Werkzeug
        self._schon_gemessen = {}  # (a, b) -> berühren sich in der Grundstellung?
        self._faktor = self._drehfaktoren()

    # --- Paare --------------------------------------------------------------------------

    def _seiten(self, werkzeug_glied):
        """(Werkzeugseite, Werkstückseite) als Mengen von Gliedern – was beide tragen, gehört
        zum Rest."""
        werkzeug = {a.kind for a in self.verfahren.pfad(werkzeug_glied)}
        werkstueck = {a.kind for a in self.verfahren.pfad(self.werkstueck_glied)}
        gemeinsam = werkzeug & werkstueck
        return werkzeug - gemeinsam, werkstueck - gemeinsam

    def paare(self, operation):
        """Die Paare, die in dieser Operation zählen."""
        werkzeug = self.werkzeuge[operation]
        glied = werkzeug[0].glied if werkzeug else None
        if glied not in self._paare:
            self._paare[glied] = self._maschinenpaare(glied)
        maschinenpaare, gegen_werkzeug = self._paare[glied]
        paare = []
        for koerper in werkzeug:
            for anderer in gegen_werkzeug:
                nur_eilgang = koerper.art == SCHNEIDE and anderer.art == TEIL
                paare.append(_Paar(koerper, anderer, nur_eilgang))
        return paare + maschinenpaare

    def _maschinenpaare(self, werkzeug_glied):
        """(Paare ohne Werkzeug, Körper, gegen die das Werkzeug zählt) für ein Werkzeugglied."""
        werkzeugseite, werkstueckseite = self._seiten(werkzeug_glied)
        w = [k for k in self.maschine if k.glied in werkzeugseite]
        s = [k for k in self.maschine if k.glied in werkstueckseite]
        r = [k for k in self.maschine if k not in w and k not in s]
        if self.teil is not None:
            s.append(self.teil)
        paare = [
            _Paar(a, b)
            for a, b in [(a, b) for a in w for b in s + r] + [(a, b) for a in s for b in r]
            if not self._beruehren_sich_schon(a, b)
        ]
        return paare, s + r

    def _beruehren_sich_schon(self, a, b):
        """Berühren sich zwei Körper schon in der Grundstellung? Dann prüft es sie nicht –
        mit Hinweis, wenn zwei Maschinenteile nicht an einem gemeinsamen Gelenk hängen."""
        schluessel = (id(a), id(b))
        if schluessel not in self._schon_gemessen:
            for k in (a, b):
                k.form.Placement = k.basis
            abstand, _stelle = self._abstand(a, b)
            beruehren = abstand <= BERUEHRT
            self._schon_gemessen[schluessel] = beruehren
            if beruehren and a.art == b.art == MASCHINE and not self._nachbarn(a.glied, b.glied):
                self.ergebnis.hinweise.append(tr("kb.schon_beruehrt", a=a.name, b=b.name))
        return self._schon_gemessen[schluessel]

    def _nachbarn(self, g1, g2):
        return g1 is g2 or any(
            {achse.eltern, achse.kind} == {g1, g2} for achse in self.pruefung.kette.achsen
        )

    # --- Schritte -----------------------------------------------------------------------

    def _drehfaktoren(self):
        """Je Drehachse: wie weit sich ein Punkt je Grad höchstens bewegt, in mm – aus der
        Größe von allem, was es gibt (Diagonale über alle Hüllquader)."""
        box = FreeCAD.BoundBox()
        for koerper in self._alle():
            for ecke in koerper.ecken:
                box.add(koerper.basis.multVec(ecke))
        diagonale = box.DiagonalLength if box.isValid() else 1000.0
        return {
            achse: (1.0 if achse.art == LINEAR else math.radians(1.0) * diagonale)
            for achse in self.abfahrt.achsen
        }

    def _alle(self):
        koerper = list(self.maschine)
        if self.teil is not None:
            koerper.append(self.teil)
        for werkzeug in self.werkzeuge:
            koerper.extend(werkzeug)
        return koerper

    def abschnitt(self, i):
        """Tastet den Weg von Station i zur nächsten ab; False, wenn es zu viele Stellen
        werden."""
        abfahrt = self.abfahrt
        stationen = abfahrt.stationen
        naechste = min(i + 1, len(stationen) - 1)
        von, nach = abfahrt.wirksam(i), abfahrt.wirksam(naechste)
        ziel = stationen[naechste]
        weg = sum(
            abs(b - a) * self._faktor[achse]
            for achse, a, b in zip(abfahrt.achsen, von, nach, strict=True)
            if a is not None and b is not None
        )
        paare = self.paare(ziel.operation)
        s = 0.0
        while True:
            self._melden()
            self.ergebnis.stellen += 1
            if self.ergebnis.stellen > HOECHSTENS:
                return False
            kleinster = self._stelle(i, naechste, s, paare, ziel)
            if s >= 1.0 or weg <= 1e-9 or naechste == i:
                return True
            schritt = max(kleinster - self.warn, MIN_SCHRITT)
            s = min(1.0, s + schritt / weg)

    def _melden(self):
        """Ruft den Fortschritt, wenn es Zeit ist; sagt er „aufhören“, endet die Prüfung."""
        if self._fortschritt is None:
            return
        jetzt = time.monotonic()
        if jetzt - self._gemeldet < MELDEN_ALLE:
            return
        self._gemeldet = jetzt
        if self._fortschritt(self.station / len(self.abfahrt.stationen)) is False:
            raise _Abbruch

    def _stelle(self, i, naechste, s, paare, ziel):
        """Prüft die Stelle beim Anteil `s` zwischen Station i und der nächsten; gibt den
        kleinsten Abstand zurück (unter den Paaren, die hier zählen – nach unten
        abgeschätzt)."""
        abfahrt = self.abfahrt
        von, nach = abfahrt.wirksam(i), abfahrt.wirksam(naechste)
        wege = {}
        for achse, a, b in zip(abfahrt.achsen, von, nach, strict=True):
            if a is None and b is None:
                continue
            wert = b if a is None else a if b is None else a + s * (b - a)
            wert = self.verfahren.begrenzt(achse, wert)
            wege[achse] = self.verfahren.weg_bei(achse, wert)
        bewegung = {}
        huelle = {}

        def lage(koerper):
            if koerper not in huelle:
                glied = koerper.glied
                if glied not in bewegung:
                    bewegung[glied] = self.pruefung._glied_lage(glied, wege)
                platz = bewegung[glied].multiply(koerper.basis)
                koerper.form.Placement = platz
                punkte = [platz.multVec(e) for e in koerper.ecken]
                huelle[koerper] = (
                    min(p.x for p in punkte),
                    min(p.y for p in punkte),
                    min(p.z for p in punkte),
                    max(p.x for p in punkte),
                    max(p.y for p in punkte),
                    max(p.z for p in punkte),
                )
            return huelle[koerper]

        kleinster = math.inf
        for paar in paare:
            if paar.nur_eilgang and not ziel.eilgang:
                continue
            luecke = _luecke(lage(paar.a), lage(paar.b))
            if luecke > self.warn + GENAU_AB:
                kleinster = min(kleinster, luecke)
                continue
            abstand, stelle = self._abstand(paar.a, paar.b)
            kleinster = min(kleinster, abstand)
            if abstand <= self.warn:
                self._merke(paar, abstand, stelle, i, naechste, s, ziel)
        return kleinster

    def _abstand(self, a, b):
        """(Abstand in mm, Stelle) zweier Körper an ihrer gesetzten Lage; 0, wenn sie sich
        berühren oder einer im anderen steckt."""
        try:
            abstand, punkte, _info = a.form.distToShape(b.form)
        except Exception:  # eine Form, mit der OpenCascade nicht rechnen kann, hält nichts an
            if (a.name, b.name) not in self._fehler:
                self._fehler.add((a.name, b.name))
                self.ergebnis.hinweise.append(tr("kb.fehler", a=a.name, b=b.name))
            return math.inf, None
        stelle = (punkte[0][0] + punkte[0][1]) * 0.5 if punkte else None
        return abstand, stelle

    def _merke(self, paar, abstand, stelle, i, naechste, s, ziel):
        """Merkt die Stelle, wenn sie für diese Operation und dieses Paar die schlimmste ist."""
        abfahrt = self.abfahrt
        station = abfahrt.stationen[i]
        schluessel = (ziel.operation, paar.a.name, paar.b.name)
        bisher = self.schlimmste.get(schluessel)
        if bisher is not None and bisher.abstand <= abstand + 1e-9:
            return
        punkt = tuple(p + s * (q - p) for p, q in zip(station.punkt, ziel.punkt, strict=True))
        self.schlimmste[schluessel] = Befund(
            beruehrung=abstand <= BERUEHRT,
            eilgang=ziel.eilgang,
            operation=abfahrt.operationen[ziel.operation].name,
            a=paar.a.name,
            b=paar.b.name,
            abstand=max(abstand, 0.0),
            zeit=station.zeit + s * (ziel.zeit - station.zeit),
            station=naechste,
            satz=ziel.satz,
            punkt=rw._programmpunkt(punkt, ziel.rund),
            stelle=stelle,
        )


def _luecke(h1, h2):
    """Abstand zweier Hüllquader (0, wenn sie sich überlappen) – nie mehr als der echte."""
    summe = 0.0
    for k in range(3):
        spalt = max(h1[k] - h2[k + 3], h2[k] - h1[k + 3], 0.0)
        summe += spalt * spalt
    return math.sqrt(summe)


def _lokale_form(bauteil):
    """Die Form eines Bauteils in seinen eigenen Koordinaten, oder None ohne Körper."""
    import Part

    try:
        form = Part.getShape(bauteil, "", needSubElement=False, refine=False, transform=False)
    except Exception:  # ein Bauteil, aus dem FreeCAD keine Form macht, zählt nicht
        return None
    if form.isNull() or not (form.Solids or form.Faces):
        return None
    return form.copy()


def _teil_form(job):
    """Das fertige Teil: die Modelle des Jobs als ein Körper, in Koordinaten des Jobs."""
    import Part

    formen = []
    for objekt in getattr(getattr(job, "Model", None), "Group", []):
        form = getattr(objekt, "Shape", None)
        if form is not None and not form.isNull():
            formen.append(form.copy())
    return Part.makeCompound(formen) if formen else None


def _werkzeug_name(art, nummer, halter):
    werkzeug = f"T{nummer}"
    if art == SCHNEIDE:
        return tr("kb.schneide", werkzeug=werkzeug)
    if art == HALS:
        return tr("kb.hals", werkzeug=werkzeug)
    if art == SCHAFT:
        return tr("kb.schaft", werkzeug=werkzeug)
    return tr("kb.halter", werkzeug=werkzeug, halter=hl.text(halter))
