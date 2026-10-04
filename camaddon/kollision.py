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
- die Schneide gegen das Teil im Eilgang – im Vorschub schneidet sie. Beginnt der
  Eilgang dort, wo ein Vorschub aufhörte (so endet jede Tasche: am Boden, dann im
  Eilgang hoch), zählt sie erst, wenn sie dem Teil näher kommt als dort. Fährt sie
  im Vorschub aber mehr als EINDRINGEN ins fertige Teil, ist das ein Befund: Ihr Kern
  (die Schneide, um EINDRINGEN kleiner) darf das Teil nicht berühren – etwa
  wenn ein radiales Werkzeug eine Bahn fährt, die für eines längs Z gerechnet
  ist (Manuels Test, 2026-09-27). Nicht beim Entgraten, Gravieren, Gewinde und
  Bohren: Deren Ergebnis zeigt das Modell meist nicht.

Zwei Maschinenteile (oder das Teil und ein Maschinenteil), die sich schon in
der Grundstellung berühren, prüft es nicht – so liegen Führungen und
Spannflächen aufeinander; hängen sie nicht an einem gemeinsamen Gelenk, sagt
es ein Hinweis. Das Rohteil zählt bei den Abständen nicht (Entscheidung 4c-7: kein Fehlalarm in
einer gefrästen Tasche) – nur ein Eilgang durch Rohteil, das dort noch steht, ist ein Befund
(`rohteil`, _eilgaenge_ins_rohteil: mit dem Abtrag im Quader, restmaterial.fuer_quader).

Entlang der Bahn geht es in Schritten, in denen sich kein Paar um mehr als
seinen Abstand minus Warnabstand näherkommt, mindestens MIN_SCHRITT – so
rutscht keine Berührung zwischen zwei Stellen durch. Wie weit sich zwei Körper
gegeneinander bewegen, zählt je Paar: nur die Achsen, die genau einen von
beiden fahren, eine Drehachse mit dem Abstand des Körpers von ihr. Dreht die
Rundachse das Teil, zählt also sein Radius – nicht die Größe der ganzen
Maschine (W-003 V3e: eine Bahn rundum dreht tausende Grad). Ist der Körper rund
um die Achse (ein Futter, eine Welle), bewegt er sich mit ihr gar nicht.

Den Abstand rechnet OpenCascade (`distToShape`: 0, wenn sich zwei Körper
berühren oder einer im anderen steckt) – nur, wo es nötig ist: Sonst reicht
eine Schranke nach unten, der Abstand der Hüllquader oder der zuletzt genau
gerechnete minus dem Weg seither. Genau gerechnet wird ein Paar, wenn seine
Schranke nicht über dem Warnabstand liegt (dann ist es vielleicht ein Befund)
oder wenn es den nächsten Schritt kürzer macht als alle anderen – und der mit
der Schranke nicht ohnehin bis zur nächsten Station reicht. Stecken zwei in
einer Operation schon ineinander, rechnet es sie dort nicht weiter – schlimmer
wird der Befund nicht.

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
HOECHSTENS = 200000  # Stellen; danach hört es auf und sagt es
# mm: So tief darf die Schneide im Vorschub ins fertige Teil – Rundung der Bahn; tiefer ist
# ein Befund („fährt ins fertige Teil“).
EINDRINGEN = 0.05
# Operationen, die ins fertige Teil schneiden sollen: Fase, Gravur, Gewinde, Bohrspitze
# stehen selten im Modell – auch „Rundum entgraten“ (vierachs_entgraten, W-003 V4d) und
# „Gewinde fräsen“ (gewindefraesen, W-006 S3g) und „Entgraten“ im Quader (entgraten).
INS_TEIL_ERLAUBT = {
    "Deburr",
    "Engrave",
    "Vcarve",
    "ThreadMilling",
    "Tapping",
    "Drilling",
    "vierachs_entgraten",
    "gewindefraesen",
    "entgraten",
    "entgraten3d",  # „Entgraten 3D“ – die Fase; dass sonst nichts verletzt wird, prüft ihre Bahn
}
MELDEN_ALLE = 0.1  # s: so oft ruft es den Fortschritt (und fragt, ob es weitergehen soll)
# Grad: Deckt sich ein Körper um beide Winkel gedreht mit sich selbst, ist er rund um die
# Achse – krumm gewählt, damit kein Futter mit drei oder vier Backen zufällig passt.
RUND_PRUEFWINKEL = (37.1, 131.7)

# Was ein Körper ist.
SCHNEIDE, HALS, SCHAFT, HALTER = "schneide", "hals", "schaft", "halter"
KERN = "kern"  # die Schneide, um EINDRINGEN kleiner – nur gegen das Teil im Vorschub
MASCHINE, TEIL = "maschine", "teil"
SCHRAUBSTOCK = "schraubstock"  # die Backen, wenn der Job „von unten gespannt“ kennt (S3h)
QUADER_NAH = 20.0  # mm – so nah (Quader in Weltachsen) wird mit den gedrehten Quadern nachgesehen
VORSCHUBWEGE = 200  # so viele gerade Vorschubwege merkt sich die Prüfung je Operation
WERKZEUG = (SCHNEIDE, HALS, SCHAFT, HALTER)


# --- Die Körper -----------------------------------------------------------------------------


def werkzeugkoerper(masse, laenge, halter, mit_kern=False):
    """[(Art, Form)]: Schneide, Hals, Schaft und Halter als Körper im LCS der Aufnahme – die
    Spitze bei Z = −laenge, Z zeigt zur Aufnahme. Die Schneide ist ein Drehkörper aus der
    Stirn des Fräsers (fraeserform: Kugel, Torus, Kegel …), darüber zylindrisch mit D – bei
    ebener Stirn ein Zylinder, der Lollipop eine Kugel. Der Schaft reicht bis zur Nase des
    Halters, auch wenn die Gesamtlänge dafür zu kurz ist – sie ist oft nur geschätzt, die
    Länge ab dem Bezugspunkt dagegen gemessen; sonst schwebte der Fräser vor dem Halter
    (Manuel, 2026-09-30), und was dazwischen steckt, sähe die Kollision nicht. Ohne Halter
    reicht er bis zur Gesamtlänge; was darüber bis zur Aufnahme fehlt, kennt niemand. `mit_kern`: dazu der Kern der Schneide (KERN), um EINDRINGEN kleiner. Ein
    gewinkelter Halter (W-002 Stufe E) kippt das Werkzeug: Seine Spitze liegt dann `laenge`
    vom Bezugspunkt des Halters längs der Werkzeugachse (halter.lage)."""
    import Part

    teile = []

    def zylinder(art, radius, von, bis):
        if radius > 0 and bis - von > 1e-6:
            teile.append((art, Part.makeCylinder(radius, bis - von, FreeCAD.Vector(0, 0, von))))

    spitze = -laenge
    form = hl.form(halter) if halter is not None else None
    if form is not None:
        ende = -halter.laenge
    else:
        ende = min(spitze + masse.gesamt, 0.0) if masse.gesamt > 0 else 0.0
    oben = min(spitze + masse.schneide, ende)
    radius = masse.durchmesser / 2
    stirn = masse.stirn
    if masse.kugel:
        mitte = FreeCAD.Vector(0, 0, spitze + radius)
        teile.append((SCHNEIDE, Part.makeSphere(radius, mitte)))
        if mit_kern and radius > EINDRINGEN:
            teile.append((KERN, Part.makeSphere(radius - EINDRINGEN, mitte)))
    elif stirn is not None and not stirn.eben and oben - spitze > 1e-6:
        teile.append((SCHNEIDE, drehkoerper(stirn, spitze, oben)))
        if mit_kern and stirn.radius > EINDRINGEN:
            kern, unten = _kern(stirn, EINDRINGEN)
            teile.append((KERN, drehkoerper(kern, spitze + unten, oben)))
    else:
        zylinder(SCHNEIDE, radius, spitze, oben)
        if mit_kern and radius > EINDRINGEN:
            zylinder(KERN, radius - EINDRINGEN, spitze + EINDRINGEN, oben)
    if masse.hals_laenge > 0 and masse.hals_d > 0:
        hals_ende = min(oben + masse.hals_laenge, ende)
        zylinder(HALS, masse.hals_d / 2, oben, hals_ende)
        oben = hals_ende
    zylinder(SCHAFT, masse.schaft / 2, oben, ende)
    if halter is not None and halter.gewinkelt:
        matrix = hl.lage(halter).toMatrix()
        teile = [(art, koerper.transformed(matrix)) for art, koerper in teile]
    if form is not None:
        teile.append((HALTER, form))
    return teile


def drehkoerper(stirn, spitze, oben):
    """Die Schneide als Drehkörper um Z: die Stirn (fraeserform.Form) mit der Spitze bei
    Z = `spitze`, darüber zylindrisch bis `oben` – was von der Stirn höher reicht, schneidet
    es dort ab."""
    import Part

    from . import fraeserform as ff

    punkt = FreeCAD.Vector
    kanten = []
    for s in stirn.stuecke:
        von = punkt(s.rho_von, 0, spitze + float(s.hoehe(s.rho_von)))
        bis = punkt(s.rho_bis, 0, spitze + float(s.hoehe(s.rho_bis)))
        if kanten:
            von = kanten[-1].Vertexes[-1].Point  # lückenlos an das Stück davor
        if (bis - von).Length < 1e-9:
            continue
        if s.art in (ff.BOGEN, ff.HOHL):
            w = (s._winkel(s.rho_von) + s._winkel(s.rho_bis)) / 2
            mitte = punkt(
                s.mitte[0] + s.radius * math.cos(w), 0, spitze + s.mitte[1] + s.radius * math.sin(w)
            )
            kanten.append(Part.Arc(von, mitte, bis).toShape())
        else:
            kanten.append(Part.LineSegment(von, bis).toShape())
    rand = kanten[-1].Vertexes[-1].Point
    hoch = max(oben, rand.z)
    ecken = [punkt(rand.x, 0, hoch), punkt(0, 0, hoch), kanten[0].Vertexes[0].Point]
    for von, bis in zip([rand] + ecken[:-1], ecken, strict=True):
        if (bis - von).Length > 1e-9:
            kanten.append(Part.LineSegment(von, bis).toShape())
    koerper = Part.Face(Part.Wire(kanten)).revolve(punkt(), punkt(0, 0, 1), 360)
    if hoch > oben + 1e-9:
        unter = Part.makeCylinder(rand.x + 1, oben - spitze + 1, punkt(0, 0, spitze - 1))
        koerper = koerper.common(unter)
    return koerper


def _kern(stirn, abstand, punkte=400, toleranz=1e-3):
    """Die Stirn des Kerns (fraeserform.Form) und ihre Spitze über der des Fräsers: die Punkte
    der Schneide, die mindestens `abstand` von ihrer Oberfläche entfernt sind. Beim
    Kugelfräser eine Kugel, um `abstand` kleiner. Sonst aus Geraden: Über jedem Punkt der
    Stirn liegt ein Kreis mit `abstand`, die Stirn des Kerns ist der höchste Kreis darüber –
    an `punkte` Stellen, zusammengefasst, solange keine Stelle mehr als `toleranz` neben der
    Sehne liegt."""
    import numpy as np

    from . import fraeserform as ff

    if stirn.nur_kugel:
        return ff.kugel(stirn.radius - abstand), abstand
    rho = np.linspace(0.0, stirn.radius, 8 * punkte)
    z = stirn.hoehe(rho)
    rho = np.concatenate([-rho[::-1], rho])  # gespiegelt: um die Achse herum
    z = np.concatenate([z[::-1], z])
    stellen = np.linspace(0.0, stirn.radius - abstand, punkte)
    kern = stirn.hoehe(stellen) + abstand  # der Kreis über der Stelle selbst, genau
    for i, stelle in enumerate(stellen):
        nah = np.abs(rho - stelle) <= abstand
        oben = z[nah] + np.sqrt(np.maximum(abstand**2 - (rho[nah] - stelle) ** 2, 0.0))
        kern[i] = max(kern[i], float(np.max(oben)))
    behalten = [0]
    for b in range(2, punkte):
        a = behalten[-1]
        sehne = kern[a] + (stellen[a + 1 : b] - stellen[a]) * (
            (kern[b] - kern[a]) / (stellen[b] - stellen[a])
        )
        if np.max(np.abs(sehne - kern[a + 1 : b])) > toleranz:
            behalten.append(b - 1)
    behalten.append(punkte - 1)
    unten = float(kern[0])
    stuecke = tuple(
        ff.Stueck(
            ff.GERADE,
            float(stellen[a]),
            float(stellen[b]),
            z_von=float(kern[a]) - unten,
            z_bis=float(kern[b]) - unten,
        )
        for a, b in zip(behalten, behalten[1:], strict=False)
    )
    return ff.Form(stuecke), unten


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
        # Der Hüllquader als Mitte und halbe Kanten: gedreht ist sein Hüllquader Mitte R·c + t,
        # halbe Kanten |R|·h – ohne die acht Ecken einzeln (kollision._stelle, je Stelle).
        self.mitte = (
            (box.XMin + box.XMax) / 2,
            (box.YMin + box.YMax) / 2,
            (box.ZMin + box.ZMax) / 2,
        )
        self.halb = (
            (box.XMax - box.XMin) / 2,
            (box.YMax - box.YMin) / 2,
            (box.ZMax - box.ZMin) / 2,
        )


@dataclass(eq=False)
class _Paar:
    a: Koerper
    b: Koerper
    nur_eilgang: bool = False  # die Schneide gegen das Teil
    nur_vorschub: bool = False  # ihr Kern gegen das Teil: zählt nur eine Berührung


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
    ins_teil: bool = False  # die Schneide fährt im Vorschub ins fertige Teil
    x_durchmesser: bool = False  # X im Programm als Durchmesser (Drehmaschine)
    # Gleich nach einem Werkzeugwechsel ohne Wechselpunkt: das neue Werkzeug („T2“) – die
    # Maschine wechselt, wo sie steht, ein längeres steckt dann im Teil.
    wechsel: str = ""
    # Ein Eilgang durch Rohteil, das dort noch steht (_eilgaenge_ins_rohteil): so tief (mm).
    ins_rohteil: float = 0.0
    # Achsen, die dort am Anschlag stehen („X1, Z1“): Die Maschine erreicht die Stelle nicht – die
    # Kollision rechnet mit der Achse an der Grenze, der Befund folgt aus ihr, nicht aus der Bahn.
    anschlag: str = ""

    def text(self):
        werte = {
            "operation": self.operation,
            "a": self.a,
            "b": self.b,
            "satz": self.satz,
            "punkt": rw.punkt_text(self.punkt, self.x_durchmesser),
        }
        if self.ins_rohteil > 0:
            text = tr("kb.ins_rohteil", tiefe=rw.weg_text(self.ins_rohteil), **werte)
        elif self.ins_teil:
            text = tr("kb.ins_teil", **werte)
        elif self.beruehrung and self.eilgang:
            text = tr("kb.beruehrung.eilgang", **werte)
        elif self.beruehrung:
            text = tr("kb.beruehrung", **werte)
        else:
            werte["abstand"] = rw.weg_text(self.abstand)
            text = tr("kb.naehe.eilgang", **werte) if self.eilgang else tr("kb.naehe", **werte)
        if self.wechsel:
            text += " " + tr("kb.wechsel_ohne_punkt", werkzeug=self.wechsel)
        if self.anschlag:
            text += " " + tr("kb.anschlag", achsen=self.anschlag)
        return text


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
    abfahrt,
    job,
    nullpunkt_des_jobs,
    bibliothek=None,
    warnabstand=WARNABSTAND,
    fortschritt=None,
    rohteil=False,
):
    """Prüft die Abfahrt (abfahren.abfahrt) auf Berührungen; gibt ein Ergebnis zurück.

    `fortschritt(anteil)` wird zwischendurch gerufen (0 … 1, höchstens alle
    MELDEN_ALLE Sekunden); gibt es False zurück, hört die Prüfung auf
    (Ergebnis.abgebrochen). `rohteil`: auch die Eilgänge durch Rohteil, das dort noch steht
    (_eilgaenge_ins_rohteil) – das Fenster prüft es, die Prüfungen mit erfundenen Bahnen in einem
    ungeräumten Rohteil nicht.
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
    befunde = list(welt.schlimmste.values())
    if rohteil and not ergebnis.abgebrochen:
        befunde += _eilgaenge_ins_rohteil(abfahrt, job)
    # Berührungen zuerst, dann was nur näher kommt – je nach der Zeit.
    ergebnis.befunde = sorted(befunde, key=lambda b: (not b.beruehrung, b.zeit, b.a, b.b))
    if fortschritt is not None and not ergebnis.abgebrochen:
        fortschritt(1.0)
    return ergebnis


def _eilgaenge_ins_rohteil(abfahrt, job):
    """[Befund] – je Operation der Eilgang, der am tiefsten durch Rohteil fährt, das dort noch
    steht. Die Abstände oben kennen nur das fertige Teil; was vom Rohteil noch steht, weiß der
    Abtrag (restmaterial.fuer: die Stange eines 4-Achs-Jobs, oder der Quader – ein Kasten als
    Rohteil, Werkzeuge von oben, keine Rundachse) – sonst nichts."""
    from . import restmaterial as rm

    try:
        abtrag = rm.fuer(abfahrt, job, abfahrt.am_werkstueck())
    except Exception as fehler:  # ohne Abtrag bleibt die Prüfung, wie sie war
        FreeCAD.Console.PrintLog(f"CAM-Addon: Eilgänge ins Rohteil: {fehler}\n")
        return []
    if abtrag is None:
        return []
    schlimmste = {}
    for k, tiefe in abtrag.eilgaenge_ins_material([s.eilgang for s in abfahrt.stationen]):
        nummer = abfahrt.stationen[k].operation
        if nummer not in schlimmste or tiefe > schlimmste[nummer][1]:
            schlimmste[nummer] = (k, tiefe)
    befunde = []
    for nummer, (k, tiefe) in schlimmste.items():
        station = abfahrt.stationen[k]
        op = abfahrt.operationen[nummer]
        befunde.append(
            Befund(
                beruehrung=True,
                eilgang=True,
                operation=op.name,
                a=tr("kb.schneide", werkzeug=f"T{getattr(op.tc, 'ToolNumber', 0)}"),
                b=tr("kb.rohteil"),
                abstand=0.0,
                zeit=station.zeit,
                station=k,
                satz=station.satz,
                punkt=rw._programmpunkt(station.punkt, station.rund),
                x_durchmesser=abfahrt.pruefung.x_durchmesser,
                ins_rohteil=tiefe,
            )
        )
    return befunde


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
        # Von unten gespannt (S3h): die Backen stehen am Rohteil wie das Teil – jedes Werkzeugteil
        # zählt gegen sie, auch die Schneide im Vorschub.
        from . import spannung

        backen = spannung.schraubstock(job)
        self.schraubstock = None
        if backen is not None:
            basis = p._lage(p.werkstueckaufnahme).multiply(
                FreeCAD.Placement(FreeCAD.Vector(nullpunkt), FreeCAD.Rotation())
            )
            self.schraubstock = Koerper(
                tr("kb.schraubstock"), SCHRAUBSTOCK, backen, self.werkstueck_glied, basis
            )

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
                    for art, form in werkzeugkoerper(masse, op.laenge, halter, mit_kern=True)
                ]
                if (halter is None or hl.ist_vorschlag(halter)) and nummer not in ohne_halter:
                    ohne_halter.add(nummer)
                    if halter is None:
                        satz = tr("kb.ohne_halter", werkzeug=f"T{nummer}")
                    else:
                        satz = tr(
                            "kb.halter_vorschlag", werkzeug=f"T{nummer}", halter=hl.text(halter)
                        )
                    ergebnis.hinweise.append(rw.Hinweis(satz, nummer))
            self.werkzeuge.append(gebaut[schluessel])

        self._paare = {}  # Glied der Werkzeugaufnahme -> Paare ohne Werkzeug
        self._schon_gemessen = {}  # (a, b) -> berühren sich in der Grundstellung?
        self._faktor = self._drehfaktoren()
        self._fahren = {}  # Glied -> die Achsen, die es fahren
        self._paarfaktor = {}  # (a, b) -> je Achse: mm je mm bzw. Grad gegeneinander
        self._drehfaktoren_je_koerper = {}  # (Körper, Drehachse) -> mm je Grad
        # (a, b) -> (so weit sind sie an der Stelle, an der es gerade ist, mindestens
        # auseinander: zuletzt genau gerechnet, minus dem Weg seither; genau hier gerechnet?)
        self._schranken = {}
        self._operation = None  # die Operation des letzten Abschnitts
        # Die geraden Vorschubwege der Operation [(Anfang, Ende)] (Programmpunkte, Rundachsen
        # gleich) – ein Eilgang darauf fährt die Schneide, wo sie schon im Vorschub war.
        self._vorschubwege = []
        self._eigener_zuletzt = False  # lag der Abschnitt davor auf einem eigenen Weg?

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
        ins_teil_erlaubt = self.abfahrt.operationen[operation].art in INS_TEIL_ERLAUBT
        paare = []
        for koerper in werkzeug:
            for anderer in gegen_werkzeug:
                if koerper.art == KERN:
                    if anderer.art == TEIL and not ins_teil_erlaubt:
                        paare.append(_Paar(koerper, anderer, nur_vorschub=True))
                    continue
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
        if self.schraubstock is not None:
            s.append(self.schraubstock)
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
        Größe von allem, was es gibt (Diagonale über alle Hüllquader). Grob: gilt nur, wo
        _drehfaktor() nichts Genaueres weiß."""
        box = FreeCAD.BoundBox()
        for koerper in self._alle():
            for ecke in koerper.ecken:
                box.add(koerper.basis.multVec(ecke))
        diagonale = box.DiagonalLength if box.isValid() else 1000.0
        return {
            achse: (1.0 if achse.art == LINEAR else math.radians(1.0) * diagonale)
            for achse in self.abfahrt.achsen
        }

    def _paarfaktoren(self, paar):
        """Je Achse der Abfahrt: wie weit sich die beiden Körper des Paars gegeneinander
        höchstens bewegen, in mm je mm bzw. Grad. Fährt die Achse beide oder keinen, 0."""
        schluessel = (id(paar.a), id(paar.b))
        if schluessel not in self._paarfaktor:
            faktoren = []
            for achse in self.abfahrt.achsen:
                faehrt_a = achse in self._achsen_von(paar.a.glied)
                faehrt_b = achse in self._achsen_von(paar.b.glied)
                if faehrt_a == faehrt_b:
                    faktoren.append(0.0)
                elif achse.art == LINEAR:
                    faktoren.append(1.0)
                else:
                    faktoren.append(self._drehfaktor(paar.a if faehrt_a else paar.b, achse))
            self._paarfaktor[schluessel] = faktoren
        return self._paarfaktor[schluessel]

    def _achsen_von(self, glied):
        if glied not in self._fahren:
            self._fahren[glied] = set(self.verfahren.pfad(glied))
        return self._fahren[glied]

    def _drehfaktor(self, koerper, achse):
        """Wie weit sich ein Punkt des Körpers je Grad der Drehachse höchstens bewegt, in mm:
        sein weitester Abstand von ihr (Ecken des Hüllquaders) – 0, wenn er rund um sie ist
        (ein Futter, eine Welle): Dann bleibt er, wo er ist. Liegt noch eine Achse
        dazwischen, ändert sich der Abstand mit ihr – dann gilt die grobe Schätzung."""
        schluessel = (id(koerper), achse)
        if schluessel in self._drehfaktoren_je_koerper:
            return self._drehfaktoren_je_koerper[schluessel]
        if koerper.glied is not achse.kind:
            faktor = self._faktor[achse]
        else:
            richtung, ursprung = self.verfahren.achslage(achse)
            weitester = 0.0
            for ecke in koerper.ecken:
                abstand = koerper.basis.multVec(ecke) - ursprung
                weitester = max(weitester, (abstand - richtung * abstand.dot(richtung)).Length)
            faktor = math.radians(1.0) * weitester
            if faktor > 0 and _rund_um(koerper, richtung, ursprung):
                faktor = 0.0
        self._drehfaktoren_je_koerper[schluessel] = faktor
        return faktor

    def _alle(self):
        koerper = list(self.maschine)
        if self.teil is not None:
            koerper.append(self.teil)
        if self.schraubstock is not None:
            koerper.append(self.schraubstock)
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
        deltas = [
            abs(b - a) if a is not None and b is not None else 0.0
            for a, b in zip(von, nach, strict=True)
        ]
        paare = self.paare(ziel.operation)
        # Je Paar: so weit bewegen sich die beiden gegeneinander auf dem ganzen Abschnitt.
        paarwege = [
            sum(d * f for d, f in zip(deltas, self._paarfaktoren(paar), strict=True))
            for paar in paare
        ]
        # Die Schranken gelten weiter, wenn die Maschine stetig hierher fuhr – nicht nach
        # einem Sprung (eine Achse bekommt hier ihren ersten Wert), und nur für Paare, die
        # schon bisher zählten: Die anderen fuhren, ohne dass es mitgezählt hat.
        schluessel = [(id(paar.a), id(paar.b)) for paar in paare]
        sprung = any((a is None) != (b is None) for a, b in zip(von, nach, strict=True))
        if sprung or ziel.operation != self._operation:
            self._schranken = {}
        else:
            self._schranken = {k: self._schranken[k] for k in schluessel if k in self._schranken}
        if ziel.operation != self._operation:
            self._vorschubwege = []
        self._operation = ziel.operation
        eigener_weg = self._eigener_weg(stationen[i], ziel, naechste != i)
        # Ein Eilgang, der dort beginnt, wo ein Vorschub aufhörte: je Paar der Schneide der
        # Abstand am Anfang (nach unten abgeschätzt).
        anfang = {} if ziel.eilgang and not stationen[i].eilgang else None
        s = 0.0
        while True:
            self._melden()
            self.ergebnis.stellen += 1
            if self.ergebnis.stellen > HOECHSTENS:
                return False
            weiter = self._stelle(
                i, naechste, s, paare, paarwege, schluessel, ziel, anfang, eigener_weg
            )
            if s >= 1.0 or naechste == i:
                return True
            neu = min(1.0, s + weiter)
            for k, weg in zip(schluessel, paarwege, strict=True):
                if k in self._schranken and weg > 0:
                    self._schranken[k] = (self._schranken[k][0] - weg * (neu - s), False)
            if weiter == math.inf:  # nichts, was zählt, kommt sich näher
                return True
            s = neu

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

    def _eigener_weg(self, station, ziel, bewegt):
        """Merkt einen geraden Vorschubweg; für einen Eilgang: Liegt er ganz auf den geraden
        Vorschubwegen der Operation davor (`_auf_wegen`)? Etwa der Wiedereinstieg zwischen den
        Hüben eines Tieflochbohrens (G83 ausgeschrieben, 3+2 am Schwenkkopf): Die Schneide fährt
        in die Bohrung, die sie eben gebohrt hat – im fertigen Teil ist die so groß wie sie, der
        Abstand an der Wand 0, eine Berührung ist es nicht."""
        if not bewegt:  # die letzte Station: ihre Stelle gehört zum Abschnitt davor
            return self._eigener_zuletzt
        self._eigener_zuletzt = False
        if station.operation != ziel.operation or station.rund != ziel.rund:
            return False
        anfang, ende = FreeCAD.Vector(*station.punkt), FreeCAD.Vector(*ziel.punkt)
        if not ziel.eilgang:
            self._vorschubwege.append((anfang, ende))
            del self._vorschubwege[:-VORSCHUBWEGE]
            return False
        self._eigener_zuletzt = _auf_wegen(anfang, ende, self._vorschubwege)
        return self._eigener_zuletzt

    def _stelle(
        self, i, naechste, s, paare, paarwege, schluessel, ziel, anfang=None, eigener_weg=False
    ):
        """Prüft die Stelle beim Anteil `s` zwischen Station i und der nächsten; gibt zurück,
        wie weit (als Anteil) es von hier sicher weitergeht: je Paar, das hier zählt, sein
        Abstand (nach unten abgeschätzt) minus Warnabstand, mindestens MIN_SCHRITT, geteilt
        durch seinen Weg (`paarwege`); math.inf, wenn sich nichts gegeneinander bewegt.
        Was es genau rechnet, merkt es als Schranke (`schluessel`: je Paar der Schlüssel).
        `anfang`: Eilgang nach einem Vorschub – die Abstände der Schneide am Anfang."""
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
        quader = {}  # Körper → (Mitte, Achsen, halbe Kanten) seines gedrehten Hüllquaders
        platzierung = {}  # Körper → seine Lage hier; an die Form erst, wenn genau gerechnet wird

        def lage(koerper):
            if koerper not in huelle:
                glied = koerper.glied
                if glied not in bewegung:
                    bewegung[glied] = self.pruefung._glied_lage(glied, wege)
                platz = bewegung[glied].multiply(koerper.basis)
                platzierung[koerper] = platz
                m = platz.toMatrix()
                cx, cy, cz = koerper.mitte
                hx, hy, hz = koerper.halb
                x = m.A11 * cx + m.A12 * cy + m.A13 * cz + m.A14
                y = m.A21 * cx + m.A22 * cy + m.A23 * cz + m.A24
                z = m.A31 * cx + m.A32 * cy + m.A33 * cz + m.A34
                ex = abs(m.A11) * hx + abs(m.A12) * hy + abs(m.A13) * hz
                ey = abs(m.A21) * hx + abs(m.A22) * hy + abs(m.A23) * hz
                ez = abs(m.A31) * hx + abs(m.A32) * hy + abs(m.A33) * hz
                huelle[koerper] = (x - ex, y - ey, z - ez, x + ex, y + ey, z + ez)
                quader[koerper] = (
                    (x, y, z),
                    ((m.A11, m.A21, m.A31), (m.A12, m.A22, m.A32), (m.A13, m.A23, m.A33)),
                    koerper.halb,
                )
            return huelle[koerper]

        def rechne_genau(k):
            for koerper in (paare[k].a, paare[k].b):
                koerper.form.Placement = platzierung[koerper]
            abstand, stelle = self._abstand(paare[k].a, paare[k].b)
            self._schranken[schluessel[k]] = (abstand, True)
            return abstand, stelle

        schritte = {}  # Paar (Index) -> [Anteil bis zur nächsten Stelle, genau gerechnet?]
        for k, (paar, weg) in enumerate(zip(paare, paarwege, strict=True)):
            if paar.nur_eilgang and not ziel.eilgang or paar.nur_vorschub and ziel.eilgang:
                continue
            if paar.nur_eilgang and eigener_weg:
                continue  # die Schneide fährt, wo sie eben im Vorschub war (_eigener_weg)
            if self._beruehrt_schon(ziel.operation, paar):
                continue  # schlimmer wird es nicht
            # Beim Kern zählt nur eine Berührung: kein Warnabstand, auch nicht für den Schritt.
            reicht = BERUEHRT if paar.nur_vorschub else self.warn
            # Genau hier schon gerechnet (am Ende des letzten Abschnitts): auch gemerkt.
            schranke, ist_genau = self._schranken.get(schluessel[k], (-math.inf, False))
            # Der Abstand der Hüllquader (wie _luecke, hier ausgeschrieben – je Stelle viele Paare).
            h1 = huelle.get(paar.a) or lage(paar.a)
            h2 = huelle.get(paar.b) or lage(paar.b)
            dx = max(h1[0] - h2[3], h2[0] - h1[3], 0.0)
            dy = max(h1[1] - h2[4], h2[1] - h1[4], 0.0)
            dz = max(h1[2] - h2[5], h2[2] - h1[5], 0.0)
            abstand = max(math.sqrt(dx * dx + dy * dy + dz * dz), schranke)
            if abstand <= reicht + QUADER_NAH and not ist_genau:
                # Enger: die gedrehten Hüllquader – an einem gekippten Rundtisch ist der Quader
                # in Weltachsen riesig, längs seiner Normalen bleibt er flach.
                abstand = max(abstand, _quader_luecke(quader[paar.a], quader[paar.b]))
            if abstand <= reicht and not ist_genau:  # vielleicht ein Befund
                abstand, stelle = rechne_genau(k)
                ist_genau = True
                if abstand <= reicht and _zaehlt(paar, k, abstand, s, anfang):
                    self._merke(paar, abstand, stelle, i, naechste, s, ziel)
            if anfang is not None and paar.nur_eilgang and s == 0.0:
                anfang[k] = abstand
            if weg > 1e-9:
                schritte[k] = [self._anteil(paar, abstand, weg), ist_genau]
        # Macht ein Paar den Schritt nur mit seiner Schranke am kürzesten, rechnet es genau –
        # oft liegt es weiter weg, als die Schranke sagt; außer der Schritt reicht auch so bis
        # zur nächsten Station. Befunde gibt es dabei keine mehr: Der genaue Abstand ist nie
        # kleiner als die Schranke.
        while schritte:
            k = min(schritte, key=lambda j: schritte[j][0])
            if schritte[k][1] or s + schritte[k][0] >= 1.0:
                return schritte[k][0]
            abstand, _stelle = rechne_genau(k)
            schritte[k] = [self._anteil(paare[k], abstand, paarwege[k]), True]
        return math.inf

    def _beruehrt_schon(self, operation, paar):
        """Stecken die beiden in dieser Operation schon ineinander (Abstand 0)? Dann bleibt
        der Befund, wie er ist – das Paar braucht nicht mehr gerechnet zu werden."""
        befund = self.schlimmste.get((operation, paar.a.name, paar.b.name, paar.nur_vorschub))
        return befund is not None and befund.abstand <= 0.0

    def _anteil(self, paar, abstand, weg):
        """So weit (als Anteil am Abschnitt) darf es bei diesem Abstand weitergehen."""
        abzug = 0.0 if paar.nur_vorschub else self.warn
        return max(abstand - abzug, MIN_SCHRITT) / weg

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
        schluessel = (ziel.operation, paar.a.name, paar.b.name, paar.nur_vorschub)
        bisher = self.schlimmste.get(schluessel)
        if bisher is not None and bisher.abstand <= abstand + 1e-9:
            return
        punkt = tuple(p + s * (q - p) for p, q in zip(station.punkt, ziel.punkt, strict=True))
        wechsel = ""
        if station.operation != ziel.operation:  # ohne Wechselpunkt direkt von der davor
            vorher, jetzt = (abfahrt.operationen[k] for k in (station.operation, ziel.operation))
            nummer = getattr(jetzt.tc, "ToolNumber", None)
            if (
                nummer is not None
                and nummer != getattr(vorher.tc, "ToolNumber", None)
                and jetzt.laenge > vorher.laenge + 1e-6
            ):
                wechsel = f"T{nummer}"
        anschlag = ", ".join(_am_anschlag(abfahrt, self.verfahren, i, naechste, s))
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
            ins_teil=paar.nur_vorschub,
            x_durchmesser=abfahrt.pruefung.x_durchmesser,
            wechsel=wechsel,
            anschlag=anschlag,
        )


def _am_anschlag(abfahrt, verfahren, i, naechste, s):
    """Die Namen der Achsen („X1“), die beim Anteil `s` zwischen Station i und der nächsten
    über ihre Grenze müssten – dort steht die Maschine am Anschlag (wie im Abspieler)."""
    from .verfahren import namen

    von, nach = abfahrt.wirksam(i), abfahrt.wirksam(naechste)
    ergebnis = []
    for achse, a, b in zip(abfahrt.achsen, von, nach, strict=True):
        if a is None and b is None:
            continue
        wert = b if a is None else a if b is None else a + s * (b - a)
        if abs(verfahren.begrenzt(achse, wert) - wert) > 1e-6:
            ergebnis.append(namen(abfahrt.pruefung.maschine, achse))
    return ergebnis


def _zaehlt(paar, k, abstand, s, anfang):
    """Ist die Stelle ein Befund? Im Eilgang nach einem Vorschub (`anfang`) die Schneide erst,
    wenn sie dem Teil näher kommt als am Anfang – ein Rückzug vom Teil weg ist keiner."""
    if anfang is None or not paar.nur_eilgang:
        return True
    return s > 0.0 and abstand < anfang.get(k, math.inf) - 1e-6


def _auf_wegen(anfang, ende, wege, genau=1e-6):
    """Liegt die Strecke `anfang` → `ende` ganz auf `wege` [(Anfang, Ende)] – auf derselben
    Geraden, lückenlos aneinander?"""
    d = ende - anfang
    laenge = d.Length
    if laenge < genau:
        return False
    richtung = d * (1.0 / laenge)

    def neben(p):
        v = p - anfang
        return (v - richtung * v.dot(richtung)).Length

    stuecke = sorted(
        tuple(sorted(((p - anfang).dot(richtung), (q - anfang).dot(richtung))))
        for p, q in wege
        if neben(p) <= genau and neben(q) <= genau
    )
    gedeckt = None  # bis hierher liegt die Strecke auf den Wegen
    for t0, t1 in stuecke:
        if gedeckt is None:
            if t0 <= genau and t1 >= -genau:
                gedeckt = t1
        elif t0 <= gedeckt + genau:
            gedeckt = max(gedeckt, t1)
    return gedeckt is not None and gedeckt >= laenge - genau


def _quader_luecke(a, b):
    """Ein Abstand, den zwei gedrehte Quader (Mitte, drei Achsen, halbe Kanten) mindestens
    haben: die größte Lücke ihrer Schatten auf ihre sechs Kantenrichtungen – auf jeder Richtung
    ist die Lücke der Schatten höchstens der Abstand (0: überall überdeckt)."""
    (ca, achsen_a, ha), (cb, achsen_b, hb) = a, b
    dx, dy, dz = cb[0] - ca[0], cb[1] - ca[1], cb[2] - ca[2]
    beste = 0.0
    for ux, uy, uz in achsen_a + achsen_b:
        ra = (
            ha[0] * abs(ux * achsen_a[0][0] + uy * achsen_a[0][1] + uz * achsen_a[0][2])
            + ha[1] * abs(ux * achsen_a[1][0] + uy * achsen_a[1][1] + uz * achsen_a[1][2])
            + ha[2] * abs(ux * achsen_a[2][0] + uy * achsen_a[2][1] + uz * achsen_a[2][2])
        )
        rb = (
            hb[0] * abs(ux * achsen_b[0][0] + uy * achsen_b[0][1] + uz * achsen_b[0][2])
            + hb[1] * abs(ux * achsen_b[1][0] + uy * achsen_b[1][1] + uz * achsen_b[1][2])
            + hb[2] * abs(ux * achsen_b[2][0] + uy * achsen_b[2][1] + uz * achsen_b[2][2])
        )
        luecke = abs(dx * ux + dy * uy + dz * uz) - ra - rb
        if luecke > beste:
            beste = luecke
    return beste


def _luecke(h1, h2):
    """Abstand zweier Hüllquader (0, wenn sie sich überlappen) – nie mehr als der echte."""
    summe = 0.0
    for k in range(3):
        spalt = max(h1[k] - h2[k + 3], h2[k] - h1[k + 3], 0.0)
        summe += spalt * spalt
    return math.sqrt(summe)


def _rund_um(koerper, richtung, ursprung):
    """Bleibt der Körper, wo er ist, wenn er sich um die Achse dreht? Um zwei krumme
    Winkel gedreht, deckt er sich mit sich selbst – erst der Hüllquader, dann das Volumen
    der Schnittmenge. Im Zweifel nein."""
    try:
        form = koerper.form.copy()
        form.Placement = koerper.basis
        volumen = form.Volume
        if volumen <= 0:
            return False
        box = form.BoundBox
        for winkel in RUND_PRUEFWINKEL:
            gedreht = form.copy()
            gedreht.rotate(ursprung, richtung, winkel)
            b = gedreht.BoundBox
            grenze = 1e-3 * max(box.DiagonalLength, 1.0)
            if any(
                abs(x - y) > grenze
                for x, y in zip(
                    (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax),
                    (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax),
                    strict=True,
                )
            ):
                return False
            if abs(form.common(gedreht).Volume - volumen) > 1e-5 * volumen:
                return False
        return True
    except Exception:  # eine Form, mit der OpenCascade nicht rechnen kann: nicht rund
        return False


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

    from .reichweite import grundjob_von

    formen = []
    # Eine geschwenkte Ebene (3+2): das Teil, wie es gespannt ist – im Grundjob.
    for objekt in getattr(getattr(grundjob_von(job), "Model", None), "Group", []):
        form = getattr(objekt, "Shape", None)
        if form is not None and not form.isNull():
            formen.append(form.copy())
    return Part.makeCompound(formen) if formen else None


def _werkzeug_name(art, nummer, halter):
    werkzeug = f"T{nummer}"
    if art in (SCHNEIDE, KERN):
        return tr("kb.schneide", werkzeug=werkzeug)
    if art == HALS:
        return tr("kb.hals", werkzeug=werkzeug)
    if art == SCHAFT:
        return tr("kb.schaft", werkzeug=werkzeug)
    return tr("kb.halter", werkzeug=werkzeug, halter=hl.text(halter))
