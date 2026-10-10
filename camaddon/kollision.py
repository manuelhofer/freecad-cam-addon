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

Am Revolver stecken auch die anderen Werkzeuge (W-002 Stufe H4; Manuel, 2026-10-05: „die
Kollisionsprüfung mit allem, was beladen ist“): Sie drehen mit dem Revolver und fahren mit ihm –
die des Jobs auf ihrem Platz (ihre Nummer), dazu, was laut Magazin der Maschine beladen ist
(magazin, `platz`), wo der Job keins hat. Jedes ihrer Teile zählt gegen Teil, Spannmittel und
Maschine wie das Werkzeug, das gerade arbeitet – auch die Schneide im Vorschub: Sie schneidet
nicht. Ohne Durchmesser (Drehwerkzeuge aus dem Magazin) fehlt ihre Form – sie fehlen dann.

Auf allen Kernen (T-006, P-2026-10-09-08): `kollision_parallel` teilt die Stationen in Stücke und
gibt sie den Nebenrechnern (nebenrechner.py). Die Maschine bekommen sie als Dokumentkopie in ihrer
Grundstellung, alles andere als Daten ohne FreeCAD-Objekte: die Stationen (`Fahrtdaten`), das Teil
als BREP, die Werkzeuge als Maße und Halter (`Daten`, `vorbereiten`). Jedes Stück beginnt mit einem
Vorlauf durch die Stationen seiner Operation davor, damit es die geraden Vorschubwege kennt
(`_vorlauf`); die Schranken fangen neu an (das kostet nur Rechnungen, keine Befunde). Die Stücke
kommen als Befunde je Paar zurück und werden wie in einem Lauf zusammengeführt (die schlimmste
Stelle, bei Gleichstand die erste). Ohne Nebenrechner – oder bei wenigen Stationen – rechnet
`kollision_parallel` wie `kollision` im eigenen Prozess.

Läuft ohne Oberfläche.
"""

import math
import os
import time
import uuid
from dataclasses import dataclass, field, replace
from types import SimpleNamespace

import FreeCAD
import numpy as np

from . import abfahren as ab
from . import halter as hl
from . import netzabstand as na
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
# Nebenrechner: ab so vielen Stationen lohnen sie sich, so viele Stücke bekommt jeder, und so
# lang ist ein Stück mindestens (die Stationen sind verschieden teuer – viele Stücke gleichen das aus).
PARALLEL_AB = 60
STUECKE_JE_ARBEITER = 48  # gemessen am Freiformbeispiel, 24 Kerne: 4 → 83 s, 16 → 60 s, 48 → 54 s
STUECK_MINDESTENS = 20
# Die Netzschranke (Spezifikation Strategien 16.5, Hebel 2): Werkzeugteile als Kapseln gegen
# das vernetzte Teil, die Backen und die Bauteile der Maschine – so fein vernetzt (mm). Beim
# Teil muss sie den Kern (EINDRINGEN unter der Schneide) von der Oberfläche unterscheiden.
NETZ_TOLERANZ = {"teil": 0.01, "schraubstock": 0.02, "maschine": 0.05}
# Für den Warnabstand (1 mm) reicht ein gröberes Netz des Teils – ein Zehntel der Dreiecke; die
# Abfrage sucht dort um große Radien (Halter) herum, und die Suchweite wächst mit dem Radius.
NETZ_TOLERANZ_GROB = {"teil": 0.3, "schraubstock": 0.3}
NETZ_SCHRITT = 2.0  # mm – so weit über den Warnabstand hinaus sucht die Netzschranke (Schritt)
# So oft darf die Netzschranke je Paar nichts entscheiden, was der genaue Abstand dann doch
# entscheidet (Kapsel zu grob: der flache Halter von unten, der Kern eines Schaftfräsers am
# Boden) – danach fragt das Paar nur noch OpenCascade.
NETZ_FEHLVERSUCHE = 3


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


def werkzeugkapseln(masse, laenge, halter):
    """{Art: ((z0, z1, r, flach), …)} – je Werkzeugteil Strecken auf der Z-Achse der Aufnahme mit
    Radius, die den Körper aus werkzeugkoerper() enthalten, für die Netzschranke (netzabstand):
    `flach` – der Körper liegt ganz zwischen z0 und z1 (Zylinder, Kegel, Schaftfräser samt
    Kern: unter der Stirn zählt der Abstand zur Stirnebene); nicht flach beim Kugelfräser und
    Lollipop – da beginnt die Strecke in der Kugelmitte, die Kapsel ist der Fräser selbst. Der
    Halter je Abschnitt eine. Leer beim gewinkelten Halter: Seine Teile liegen nicht auf der
    Z-Achse."""
    if halter is not None and halter.gewinkelt:
        return {}
    spitze = -laenge
    if halter is not None and hl.form(halter) is not None:
        ende = -halter.laenge
    else:
        ende = min(spitze + masse.gesamt, 0.0) if masse.gesamt > 0 else 0.0
    oben = min(spitze + masse.schneide, ende)
    radius = masse.durchmesser / 2
    stirn = masse.stirn
    kapseln = {}
    kugel = radius if masse.kugel else (stirn.kugel if stirn is not None and stirn.nur_kugel else 0)
    if kugel > 0:  # Kugel an der Spitze: die Kapsel ab der Kugelmitte ist der Fräser selbst
        mitte = spitze + kugel
        r = max(radius, kugel)
        kapseln[SCHNEIDE] = ((mitte, max(oben, mitte), r, False),)
        if r > EINDRINGEN:
            kapseln[KERN] = ((mitte, max(oben, mitte), r - EINDRINGEN, False),)
    elif oben - spitze > 1e-6 and radius > 0:
        kapseln[SCHNEIDE] = ((spitze, oben, radius, True),)
        if radius > EINDRINGEN:
            kapseln[KERN] = ((spitze + EINDRINGEN, oben, radius - EINDRINGEN, True),)
    if masse.hals_laenge > 0 and masse.hals_d > 0:
        hals_ende = min(oben + masse.hals_laenge, ende)
        if hals_ende - oben > 1e-6:
            kapseln[HALS] = ((oben, hals_ende, masse.hals_d / 2, True),)
        oben = hals_ende
    if masse.schaft > 0 and ende - oben > 1e-6:
        kapseln[SCHAFT] = ((oben, ende, masse.schaft / 2, True),)
    if halter is not None:
        stufen = []
        z = 0.0
        for abschnitt in halter.abschnitte:
            if abschnitt.laenge <= 0:
                continue
            r = max(abschnitt.d_oben, abschnitt.d_unten) / 2
            if r > 0:
                stufen.append((-z - abschnitt.laenge, -z, r, True))
            z += abschnitt.laenge
        if stufen:
            kapseln[HALTER] = tuple(stufen)
    return kapseln


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
    # Werkzeugteile: Kapseln (z0, z1, r) um die eigene Z-Achse, die den Körper enthalten –
    # für die Netzschranke (werkzeugkapseln); leer: keine Schranke für diesen Körper.
    kapseln: tuple = ()
    _netze: dict = field(default_factory=dict, repr=False)

    def netz(self, fein=True):
        """Die Oberfläche als Netz in eigenen Koordinaten (netzabstand.Netz), beim ersten Mal
        gebaut – `fein` für Berührungen (NETZ_TOLERANZ), sonst gröber (NETZ_TOLERANZ_GROB, wo
        es das gibt); None für Körper, gegen die es keine Netzschranke gibt."""
        toleranzen = (
            NETZ_TOLERANZ if fein or self.art not in NETZ_TOLERANZ_GROB else NETZ_TOLERANZ_GROB
        )
        toleranz = toleranzen.get(self.art)
        if toleranz is None:
            return None
        if toleranz not in self._netze:
            form = self.form.copy()
            form.Placement = FreeCAD.Placement()
            try:
                self._netze[toleranz] = na.Netz(form, toleranz)
            except Exception:  # eine Form, die sich nicht vernetzen lässt: ohne Schranke
                self._netze[toleranz] = None
        return self._netze[toleranz]

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
    umgekehrt: frozenset = frozenset()  # Rundachsen, die das Programm umgekehrt schreibt
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
            "punkt": rw.punkt_text(self.punkt, self.x_durchmesser, self.umgekehrt),
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


# --- Die Daten (ohne FreeCAD-Objekte, für die Nebenrechner) ---------------------------------


@dataclass
class Werkzeugdaten:
    """Das Werkzeug einer Operation: Nummer, Maße und Halter – woraus werkzeugkoerper() baut."""

    tc_name: str
    nummer: int
    masse: object  # reichweite.Werkzeugmasse
    halter: object  # halter.Halter oder None


@dataclass
class Daten:
    """Alles außer der Maschine und den Stationen, was die Prüfung braucht – `vorbereiten()`.
    `teil` und `schraubstock` sind Formen (Part.Shape), zum Senden BREP (`zum_senden`)."""

    kennung: str
    nullpunkt: tuple
    teil: object = None
    schraubstock: object = None
    werkzeuge: list = field(default_factory=list)  # je Operation ein Werkzeugdaten
    beladen: list = field(default_factory=list)  # [(Platznummer, Maße, Länge, Halter)]

    def zum_senden(self):
        from . import nebenrechner as nr

        return replace(
            self,
            teil=nr.Form.von(self.teil) if self.teil is not None else None,
            schraubstock=(
                nr.Form.von(self.schraubstock) if self.schraubstock is not None else None
            ),
        )

    def formen_lesen(self):
        """Die Formen aus den BREP-Texten (im Nebenrechner)."""
        from . import nebenrechner as nr

        return replace(
            self,
            teil=self.teil.form() if isinstance(self.teil, nr.Form) else self.teil,
            schraubstock=(
                self.schraubstock.form()
                if isinstance(self.schraubstock, nr.Form)
                else self.schraubstock
            ),
        )


@dataclass
class Fahrtdaten:
    """Die Stationen einer Abfahrt ohne FreeCAD-Objekte: Achsen als Nummern in der Kette,
    Operationen als Namen und Zahlen – `fahrtdaten()`, zurück mit `_fahrt_aus()`."""

    kennung: str
    stationen: list
    wirksam: list
    achsen: list  # Nummern in pruefung.kette.achsen
    nullpunkt: tuple
    operationen: (
        list  # [(Name, Controller-Name, Werkzeugnummer, Aufnahme-Name, Länge, erste, Sätze, Art)]
    )


@dataclass(frozen=True)
class Maschinendaten:
    """Die Maschine für einen Nebenrechner: die Namen von Assembly, Maschinenobjekt und
    Werkstückaufnahme in der Dokumentkopie (die kommt als nebenrechner.Dokument daneben)."""

    assembly: str
    maschine: str
    aufnahme: str


def vorbereiten(abfahrt, job, bibliothek, ergebnis, nullpunkt=None):
    """Die Daten für die Prüfung aus Job und Werkzeugverwaltung; Hinweise (kein Teil, ohne
    Halter geprüft) kommen in `ergebnis.hinweise`."""
    from . import spannung

    if nullpunkt is None:
        nullpunkt = abfahrt.nullpunkt
    teil = _teil_form(job)
    if teil is None:
        ergebnis.hinweise.append(tr("kb.kein_teil"))
    werkzeuge = []
    ohne_halter = set()
    for op in abfahrt.operationen:
        nummer = getattr(op.tc, "ToolNumber", 0)
        halter = rw.werkzeughalter(op.tc, bibliothek)
        werkzeuge.append(
            Werkzeugdaten(
                op.tc.Name, nummer, rw.werkzeugmasse(op.tc, bibliothek, op.laenge), halter
            )
        )
        if (halter is None or hl.ist_vorschlag(halter)) and nummer not in ohne_halter:
            ohne_halter.add(nummer)
            if halter is None:
                satz = tr("kb.ohne_halter", werkzeug=f"T{nummer}")
            else:
                satz = tr("kb.halter_vorschlag", werkzeug=f"T{nummer}", halter=hl.text(halter))
            ergebnis.hinweise.append(rw.Hinweis(satz, nummer))
    return Daten(
        uuid.uuid4().hex,
        tuple(nullpunkt),
        teil,
        spannung.schraubstock(job),
        werkzeuge,
        _beladen_daten(abfahrt.pruefung, job, bibliothek),
    )


def fahrtdaten(abfahrt):
    """Die Abfahrt ohne FreeCAD-Objekte (Fahrtdaten)."""
    achsen = list(abfahrt.pruefung.kette.achsen)
    return Fahrtdaten(
        uuid.uuid4().hex,
        list(abfahrt.stationen),
        [abfahrt.wirksam(i) for i in range(len(abfahrt.stationen))],
        [achsen.index(a) for a in abfahrt.achsen],
        tuple(abfahrt.nullpunkt),
        [
            (
                op.name,
                op.tc.Name,
                getattr(op.tc, "ToolNumber", 0),
                op.aufnahme.Name,
                op.laenge,
                op.erste,
                op.saetze,
                op.art,
            )
            for op in abfahrt.operationen
        ],
    )


def _fahrt_aus(fahrt, pruefung):
    """Die Abfahrt aus Fahrtdaten, mit der Maschine `pruefung` (im Nebenrechner)."""
    dokument = pruefung.maschine.Document
    kette = pruefung.kette.achsen
    operationen = [
        ab.OperationAbfahrt(
            name,
            SimpleNamespace(Name=tc_name, ToolNumber=nummer),
            dokument.getObject(aufnahme),
            laenge,
            erste,
            saetze,
            art,
        )
        for name, tc_name, nummer, aufnahme, laenge, erste, saetze, art in fahrt.operationen
    ]
    return ab.Abfahrt(
        pruefung,
        [kette[i] for i in fahrt.achsen],
        list(fahrt.stationen),
        operationen,
        nullpunkt=FreeCAD.Vector(*fahrt.nullpunkt),
        _wirksam=list(fahrt.wirksam),
    )


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
    daten = vorbereiten(abfahrt, job, bibliothek, ergebnis, nullpunkt_des_jobs)
    welt = _Welt(abfahrt, daten, ergebnis, fortschritt)
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
    _abschliessen(ergebnis, list(welt.schlimmste.values()), abfahrt, job, rohteil, fortschritt)
    return ergebnis


def _abschliessen(ergebnis, befunde, abfahrt, job, rohteil, fortschritt):
    """Die Eilgänge ins Rohteil dazu, sortieren, den Fortschritt auf 1."""
    if rohteil and not ergebnis.abgebrochen:
        befunde += _eilgaenge_ins_rohteil(abfahrt, job)
    # Berührungen zuerst, dann was nur näher kommt – je nach der Zeit.
    ergebnis.befunde = sorted(befunde, key=lambda b: (not b.beruehrung, b.zeit, b.a, b.b))
    if fortschritt is not None and not ergebnis.abgebrochen:
        fortschritt(1.0)


def kollision_parallel(
    abfahrt,
    job,
    nullpunkt_des_jobs,
    bibliothek=None,
    warnabstand=WARNABSTAND,
    fortschritt=None,
    rohteil=False,
    nebenrechner=None,
):
    """Wie kollision(), auf allen Kernen (T-006): die Stationen in Stücken auf den Nebenrechnern.
    Ohne Nebenrechner, bei wenigen Stationen oder wenn die Nebenrechner scheitern (Warnung im
    Report-Fenster), rechnet es wie kollision() hier. `fortschritt` wie dort – es wird gerufen,
    solange die Stücke laufen; False bricht ab."""
    from . import nebenrechner as nr

    pool = nebenrechner if nebenrechner is not None else nr.pool()
    stationen = len(abfahrt.stationen)
    if not pool.verfuegbar() or pool.anzahl < 2 or stationen < PARALLEL_AB:
        return kollision(
            abfahrt, job, nullpunkt_des_jobs, bibliothek, warnabstand, fortschritt, rohteil
        )
    try:
        return _verteilt(
            pool, abfahrt, job, nullpunkt_des_jobs, bibliothek, warnabstand, fortschritt, rohteil
        )
    except nr.Abgebrochen:
        ergebnis = Ergebnis(warnabstand)
        ergebnis.abgebrochen = True
        ergebnis.hinweise.append(tr("kb.abgebrochen", **_bis_hier(abfahrt, 0)))
        return ergebnis
    except nr.Fehler as fehler:
        FreeCAD.Console.PrintWarning(
            f"CAM-Addon: Kollision auf den Nebenrechnern gescheitert, rechne hier: {fehler}\n"
        )
        return kollision(
            abfahrt, job, nullpunkt_des_jobs, bibliothek, warnabstand, fortschritt, rohteil
        )


def _verteilt(pool, abfahrt, job, nullpunkt, bibliothek, warnabstand, fortschritt, rohteil):
    from . import nebenrechner as nr

    ergebnis = Ergebnis(warnabstand)
    pruefung = abfahrt.pruefung
    if not abfahrt.stationen or pruefung.werkstueckaufnahme is None:
        return ergebnis
    daten = vorbereiten(abfahrt, job, bibliothek, ergebnis, nullpunkt)
    kopie, maschine = _maschinendaten(pool, pruefung)
    fahrt = fahrtdaten(abfahrt)
    schluessel = (f"kollision-fahrt-{fahrt.kennung}", f"kollision-daten-{daten.kennung}")
    g_fahrt = pool.gemeinsam(schluessel[0], fahrt)
    g_daten = pool.gemeinsam(schluessel[1], daten.zum_senden())
    bereiche = _bereiche(len(abfahrt.stationen), pool.anzahl)
    auftraege = []
    for bereich in bereiche:
        auftrag = pool.auftrag(
            "kollision",
            "stueck",
            kopie,
            maschine,
            g_fahrt,
            g_daten,
            warnabstand,
            bereich,
            fortschritt=nr.Fortschritt(),
        )
        auftrag.gewicht = bereich[1] - bereich[0]
        auftraege.append(auftrag)

    def zwischendurch():
        if fortschritt is None:
            return True
        return fortschritt(nr.fortschritt_von(auftraege) * 0.999) is not False

    try:
        # Die Eilgänge ins Rohteil rechnet dieser Prozess, während die Stücke laufen.
        rohteil_befunde = _eilgaenge_ins_rohteil(abfahrt, job) if rohteil else []
        stuecke = pool.warten(auftraege, zwischendurch)
    finally:
        for s in schluessel:
            pool.vergessen(s)
    schlimmste = {}
    zu_viele = None
    for stueck in stuecke:
        for k, befund in stueck["schlimmste"].items():
            if befund.stelle is not None:
                befund.stelle = FreeCAD.Vector(*befund.stelle)
            bisher = schlimmste.get(k)
            if bisher is None or bisher.abstand > befund.abstand + 1e-9:
                schlimmste[k] = befund
        ergebnis.stellen += stueck["stellen"]
        for text, nummer in stueck["hinweise"]:
            hinweis = rw.Hinweis(text, nummer) if nummer is not None else text
            if hinweis not in ergebnis.hinweise:
                ergebnis.hinweise.append(hinweis)
        if stueck["zu_viele"] and zu_viele is None:
            zu_viele = stueck["bis"]
    if zu_viele is not None:
        ergebnis.hinweise.append(
            tr("kb.zu_viele", anzahl=HOECHSTENS, **_bis_hier(abfahrt, zu_viele))
        )
    befunde = list(schlimmste.values())
    if rohteil:
        befunde += rohteil_befunde
    _abschliessen(ergebnis, befunde, abfahrt, job, False, fortschritt)
    return ergebnis


def _bereiche(stationen, arbeiter):
    """[(von, bis)] – die Stationen in Stücke: je Arbeiter STUECKE_JE_ARBEITER, keins kürzer als
    STUECK_MINDESTENS."""
    anzahl = max(1, min(arbeiter * STUECKE_JE_ARBEITER, stationen // STUECK_MINDESTENS))
    grenzen = [round(k * stationen / anzahl) for k in range(anzahl + 1)]
    return [(a, b) for a, b in zip(grenzen, grenzen[1:], strict=False) if b > a]


def _maschinendaten(pool, pruefung):
    """(Dokumentkopie, Maschinendaten) für die Nebenrechner – die Kopie in der Grundstellung
    der Prüfung: Das Fenster hat die Maschine vielleicht verfahren, gerechnet wird ab der
    Stellung beim Anlegen."""
    verfahren = pruefung.verfahren
    assembly = verfahren.assembly
    if pruefung.maschine.Document is not assembly.Document:
        raise NichtTeilbar("Maschine und Assembly in verschiedenen Dokumenten")
    weg = dict(verfahren.weg)
    bewegt = any(abs(w) > 1e-12 for w in weg.values())
    if bewegt:
        verfahren.grundstellung()
    try:
        kopie = pool.kopie(assembly.Document)
    finally:
        if bewegt:
            verfahren.setze_alle({a: verfahren.stellung_bei(a, w) for a, w in weg.items()})
    return kopie, Maschinendaten(
        assembly.Name, pruefung.maschine.Name, pruefung.werkstueckaufnahme.Name
    )


class NichtTeilbar(Exception):
    """Die Prüfung lässt sich nicht auf Nebenrechner verteilen."""


# --- Im Nebenrechner ------------------------------------------------------------------------

_pruefung_im_arbeiter = None  # (Kennung, Prüfung) – die Maschine, je Kopie einmal gelesen
_welt_im_arbeiter = None  # (Kennung, Welt) – Körper und Paare, je Fahrt und Daten einmal


def _pruefung_fuer(dokument, maschine):
    """Die Prüfung (reichweite.Pruefung) aus der Dokumentkopie – gemerkt, bis eine andere
    Kopie kommt."""
    global _pruefung_im_arbeiter
    stat = os.stat(dokument.FileName) if dokument.FileName else None
    kennung = (
        dokument.Name,
        stat.st_size if stat else 0,
        stat.st_mtime_ns if stat else 0,
        maschine,
    )
    if _pruefung_im_arbeiter is None or _pruefung_im_arbeiter[0] != kennung:
        pruefung = rw.Pruefung(
            dokument.getObject(maschine.assembly),
            dokument.getObject(maschine.maschine),
            dokument.getObject(maschine.aufnahme),
        )
        _pruefung_im_arbeiter = (kennung, pruefung)
    return _pruefung_im_arbeiter[1]


def stueck(dokument, maschine, fahrt, daten, warnabstand, bereich, fortschritt=None):
    """Prüft die Stationen `bereich` (von, bis) – im Nebenrechner. Gibt die Befunde je Paar,
    die Zahl der Stellen und die Hinweise zurück, als Daten ohne FreeCAD-Objekte."""
    global _welt_im_arbeiter
    beginn = time.perf_counter()
    pruefung = _pruefung_fuer(dokument, maschine)
    kennung = (fahrt.kennung, daten.kennung, warnabstand, id(pruefung))
    ergebnis = Ergebnis(warnabstand)
    if _welt_im_arbeiter is None or _welt_im_arbeiter[0] != kennung:
        abfahrt = _fahrt_aus(fahrt, pruefung)
        welt = _Welt(abfahrt, daten.formen_lesen(), ergebnis, fortschritt, bereich)
        _welt_im_arbeiter = (kennung, welt)
    else:
        welt = _welt_im_arbeiter[1]
        welt.neu(ergebnis, fortschritt, bereich)
    aufbau = time.perf_counter() - beginn
    zu_viele = None
    welt.vorlauf(bereich[0])
    for i in range(*bereich):
        welt.station = i
        if not welt.abschnitt(i):
            zu_viele = i
            break
    return {
        "aufbau_s": aufbau,  # die Welt gebaut (oder wiederverwendet) – zum Messen
        "lauf_s": time.perf_counter() - beginn - aufbau,
        "schlimmste": {
            k: replace(b, stelle=tuple(b.stelle) if b.stelle is not None else None)
            for k, b in welt.schlimmste.items()
        },
        "stellen": ergebnis.stellen,
        "hinweise": [(str(h), getattr(h, "werkzeug", None)) for h in ergebnis.hinweise],
        "zu_viele": zu_viele is not None,
        "bis": zu_viele if zu_viele is not None else bereich[1] - 1,
    }


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
                umgekehrt=abfahrt.pruefung.umgekehrt,
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
    """Alle Körper, die Paare je Operation und das Abtasten der Bahn – aus der Abfahrt (mit der
    Maschine) und den Daten (vorbereiten). `bereich` (von, bis): nur diese Stationen, für den
    Fortschritt; `neu()` setzt für ein weiteres Stück zurück, was zum Lauf gehört."""

    def __init__(self, abfahrt, daten, ergebnis, fortschritt=None, bereich=None):
        self.abfahrt = abfahrt
        self.pruefung = abfahrt.pruefung
        self.verfahren = self.pruefung.verfahren
        self.warn = ergebnis.warnabstand
        self._fehler = set()  # Paare, deren Abstand FreeCAD nicht rechnen konnte
        self.neu(ergebnis, fortschritt, bereich)
        p = self.pruefung
        nullpunkt = daten.nullpunkt

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
        am_nullpunkt = p._lage(p.werkstueckaufnahme).multiply(
            FreeCAD.Placement(FreeCAD.Vector(*nullpunkt), FreeCAD.Rotation())
        )
        self.teil = None
        if daten.teil is not None:
            self.teil = Koerper(
                tr("kb.teil"), TEIL, daten.teil, self.werkstueck_glied, am_nullpunkt
            )
        # Von unten gespannt (S3h): die Backen stehen am Rohteil wie das Teil – jedes Werkzeugteil
        # zählt gegen sie, auch die Schneide im Vorschub.
        self.schraubstock = None
        if daten.schraubstock is not None:
            self.schraubstock = Koerper(
                tr("kb.schraubstock"),
                SCHRAUBSTOCK,
                daten.schraubstock,
                self.werkstueck_glied,
                am_nullpunkt,
            )

        # Je Operation ihr Werkzeug; gleiche Werkzeuge nur einmal gebaut.
        self.werkzeuge = []
        gebaut = {}
        for op, w in zip(abfahrt.operationen, daten.werkzeuge, strict=True):
            schluessel = (w.tc_name, op.aufnahme.Name, round(op.laenge, 6))
            if schluessel not in gebaut:
                glied = p._glied(op.aufnahme)
                basis = p._lage(op.aufnahme)
                kapseln = werkzeugkapseln(w.masse, op.laenge, w.halter)
                gebaut[schluessel] = [
                    Koerper(
                        _werkzeug_name(art, w.nummer, w.halter),
                        art,
                        form,
                        glied,
                        basis,
                        kapseln=kapseln.get(art, ()),
                    )
                    for art, form in werkzeugkoerper(w.masse, op.laenge, w.halter, mit_kern=True)
                ]
            self.werkzeuge.append(gebaut[schluessel])
        # Die übrigen Werkzeuge im Revolver (W-002 Stufe H4): Platz-Aufnahme → [Körper].
        self.beladen = _beladen_koerper(p, daten.beladen)

        self._paare = {}  # Glied der Werkzeugaufnahme -> Paare ohne Werkzeug
        self._schon_gemessen = {}  # (a, b) -> berühren sich in der Grundstellung?
        self._faktor = self._drehfaktoren()
        self._fahren = {}  # Glied -> die Achsen, die es fahren
        self._paarfaktor = {}  # (a, b) -> je Achse: mm je mm bzw. Grad gegeneinander
        self._drehfaktoren_je_koerper = {}  # (Körper, Drehachse) -> mm je Grad
        self._netz_fehl = (
            {}
        )  # (a, b) -> wie oft die Netzschranke nichts entschied (NETZ_FEHLVERSUCHE)

    def neu(self, ergebnis, fortschritt=None, bereich=None):
        """Für einen (weiteren) Lauf über `bereich`: Ergebnis, Fortschritt und alles, was
        entlang der Bahn mitläuft, zurück auf den Anfang – die Körper und Paare bleiben."""
        self.ergebnis = ergebnis
        self._fortschritt = fortschritt
        self._gemeldet = -math.inf  # wann zuletzt gemeldet
        self.bereich = bereich if bereich is not None else (0, len(self.abfahrt.stationen))
        self.station = self.bereich[0]  # die Station, von der aus es gerade prüft
        self.schlimmste = {}  # (Operation, Name a, Name b, nur Vorschub) -> Befund
        # (a, b) -> (so weit sind sie an der Stelle, an der es gerade ist, mindestens
        # auseinander: zuletzt genau gerechnet, minus dem Weg seither; genau hier gerechnet?)
        self._schranken = {}
        self._operation = None  # die Operation des letzten Abschnitts
        # Die geraden Vorschubwege der Operation [(Anfang, Ende)] (Programmpunkte, Rundachsen
        # gleich) – ein Eilgang darauf fährt die Schneide, wo sie schon im Vorschub war.
        self._vorschubwege = []
        self._eigener_zuletzt = False  # lag der Abschnitt davor auf einem eigenen Weg?

    def vorlauf(self, bis):
        """Vor einem Stück, das bei Station `bis` beginnt: die geraden Vorschubwege der
        Operation davor einsammeln (ab ihrer ersten Station), ohne Abstände zu rechnen – damit
        ein Eilgang im Stück weiß, ob er fährt, wo die Schneide schon im Vorschub war."""
        stationen = self.abfahrt.stationen
        if bis <= 0 or bis >= len(stationen):
            return
        operation = stationen[bis].operation
        anfang = max(0, self.abfahrt.operationen[operation].erste - 1)
        # Gemerkt werden nur die letzten VORSCHUBWEGE Vorschubwege: weiter zurück muss es nicht.
        vorschuebe, zurueck = 0, bis - 1
        while zurueck > anfang:
            if not stationen[zurueck + 1].eilgang:
                vorschuebe += 1
                if vorschuebe >= VORSCHUBWEGE:
                    break
            zurueck -= 1
        for i in range(max(anfang, zurueck), bis):
            ziel = stationen[i + 1]
            if ziel.operation != self._operation:
                self._vorschubwege = []
            self._operation = ziel.operation
            if not ziel.eilgang or i == bis - 1:
                self._eigener_weg(stationen[i], ziel, True)

    # --- Paare --------------------------------------------------------------------------

    def _seiten(self, werkzeug_glied):
        """(Werkzeugseite, Werkstückseite) als Mengen von Gliedern – was beide tragen, gehört
        zum Rest."""
        werkzeug = {a.kind for a in self.verfahren.pfad(werkzeug_glied)}
        werkstueck = {a.kind for a in self.verfahren.pfad(self.werkstueck_glied)}
        gemeinsam = werkzeug & werkstueck
        return werkzeug - gemeinsam, werkstueck - gemeinsam

    def paare(self, operation):
        """Die Paare, die in dieser Operation zählen – mit den Werkzeugen, die auf den anderen
        Plätzen des Revolvers stecken (H4)."""
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
        aufnahme = self.abfahrt.operationen[operation].aufnahme
        for platz, koerper_liste in self.beladen.items():
            if platz is aufnahme:
                continue  # dort steckt das Werkzeug, das gerade arbeitet
            for koerper in koerper_liste:
                if koerper.glied is not glied:
                    continue  # nur auf demselben Revolver wie das arbeitende
                paare.extend(_Paar(koerper, anderer) for anderer in gegen_werkzeug)
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
        for beladen in self.beladen.values():
            koerper.extend(beladen)
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
        von, bis = self.bereich
        if self._fortschritt((self.station - von) / max(bis - von, 1)) is False:
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
            # Die Netzschranke schon gerechnet? Und sagt sie den Abstand fast genau (das Netz sieht
            # die Oberfläche näher als eine Zelle) – dann lohnt kein genauer Abstand mehr für den
            # Schritt, er wäre kaum größer.
            geschaetzt, knapp = False, False
            if abstand <= reicht and not ist_genau:
                # Enger noch: das Werkzeugteil als Kapseln gegen das Netz des anderen – meist
                # entscheidet das, ohne OpenCascade (Spezifikation Strategien 16.5, Hebel 2).
                netz = self._netzschranke(paar, platzierung, reicht)
                if netz is not None:
                    geschaetzt = True
                    knapp = netz[1]
                    if netz[0] > abstand:
                        abstand = netz[0]
                        self._schranken[schluessel[k]] = (abstand, False)
            if abstand <= reicht and not ist_genau:  # vielleicht ein Befund
                abstand, stelle = rechne_genau(k)
                ist_genau = True
                if geschaetzt:
                    self._netz_gelernt(paar, abstand > reicht)
                if abstand <= reicht and _zaehlt(paar, k, abstand, s, anfang):
                    self._merke(paar, abstand, stelle, i, naechste, s, ziel)
            if anfang is not None and paar.nur_eilgang and s == 0.0:
                anfang[k] = abstand
            if weg > 1e-9:
                schritte[k] = [
                    self._anteil(paar, abstand, weg),
                    ist_genau or knapp,
                    geschaetzt,
                    abstand,
                ]
        # Macht ein Paar den Schritt nur mit seiner Schranke am kürzesten, rechnet es genau –
        # oft liegt es weiter weg, als die Schranke sagt; außer der Schritt reicht auch so bis
        # zur nächsten Station. Davor einmal die Netzschranke, wenn sie noch fehlt: Sie reicht
        # eine Zellenbreite weit und kostet einen Bruchteil – und sieht sie die Oberfläche
        # näher als das, ist sie fast der genaue Abstand (der Kern der Schneide im Vorschub:
        # immer EINDRINGEN von der Oberfläche, ein genauer Abstand machte den Schritt nicht
        # größer). Befunde gibt es dabei keine mehr: Der genaue Abstand ist nie kleiner als
        # die Schranke.
        while schritte:
            k = min(schritte, key=lambda j: schritte[j][0])
            anteil, fertig, geschaetzt, abstand = schritte[k]
            if fertig or s + anteil >= 1.0:
                return anteil
            if not geschaetzt:
                schritte[k][2] = True
                reicht = BERUEHRT if paare[k].nur_vorschub else self.warn
                netz = self._netzschranke(paare[k], platzierung, reicht)
                if netz is not None and (netz[0] > abstand or netz[1]):
                    if netz[0] > abstand:
                        self._schranken[schluessel[k]] = (netz[0], False)
                        schritte[k][0] = self._anteil(paare[k], netz[0], paarwege[k])
                        schritte[k][3] = netz[0]
                    schritte[k][1] = netz[1]
                    continue
            abstand, _stelle = rechne_genau(k)
            schritte[k] = [self._anteil(paare[k], abstand, paarwege[k]), True, True, abstand]
        return math.inf

    def _netz_gelernt(self, paar, umsonst):
        """Merkt je Paar, ob die Netzschranke umsonst war (sie entschied nichts, der genaue
        Abstand dann doch); nach NETZ_FEHLVERSUCHE Malen in Folge lässt das Paar sie weg."""
        k = (id(paar.a), id(paar.b))
        self._netz_fehl[k] = self._netz_fehl.get(k, 0) + 1 if umsonst else 0

    def _netzschranke(self, paar, platzierung, reicht):
        """(Wie weit die beiden mindestens auseinander sind, knapp?) aus den Kapseln des
        Werkzeugteils gegen das Netz des anderen (netzabstand) – höchstens eine Zellenbreite
        des Netzes; `knapp`: das Netz hat die Oberfläche näher als eine Zelle gesehen, die
        Schranke ist dann fast der Abstand (beim Kugelfräser bis auf die Toleranz). None, wenn
        das Paar keine Kapseln oder kein Netz hat."""
        if paar.a.kapseln:
            werkzeug, anderer = paar.a, paar.b
        elif paar.b.kapseln:
            werkzeug, anderer = paar.b, paar.a
        else:
            return None
        if self._netz_fehl.get((id(paar.a), id(paar.b)), 0) >= NETZ_FEHLVERSUCHE:
            return None
        netz = anderer.netz(fein=reicht < 0.1)  # Berührung: fein; Warnabstand: grob reicht
        if netz is None:
            return None
        # Die Kapseln in die Koordinaten des anderen: seine Lage zurück, die des Werkzeugs hin.
        m = platzierung[anderer].inverse().multiply(platzierung[werkzeug]).toMatrix()
        z0 = np.array([k[0] for k in werkzeug.kapseln])
        z1 = np.array([k[1] for k in werkzeug.kapseln])
        radius = np.array([k[2] for k in werkzeug.kapseln])
        flach = np.array([k[3] for k in werkzeug.kapseln])
        achse = np.array([m.A13, m.A23, m.A33])
        ursprung = np.array([m.A14, m.A24, m.A34])
        von = ursprung + z0[:, None] * achse
        nach = ursprung + z1[:, None] * achse
        # So weit suchen, dass die Schranke über `reicht` hinaus noch einen Schritt erlaubt.
        reichweite = float(radius.max()) + reicht + NETZ_SCHRITT
        werte = netz.kapseln(von, nach, reichweite, radius, flach)
        k = int(np.argmin(werte))
        knapp = bool(werte[k] < reichweite - radius[k] - netz.toleranz - 1e-9)
        return float(werte[k]), knapp

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
            umgekehrt=abfahrt.pruefung.umgekehrt,
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


def _beladen_daten(pruefung, job, bibliothek):
    """[(Platznummer, Maße, Länge, Halter)] – was außer dem arbeitenden Werkzeug im Revolver
    steckt (W-002 Stufe H4): die Werkzeuge des Jobs auf dem Platz ihrer Nummer und, wo der Job
    keins hat, die laut Magazin der Maschine dort beladenen; `_beladen_koerper` baut daraus die
    Körper. Leer ohne Revolver."""
    from . import bestueckung as bs
    from . import magazin as mg

    if not pruefung.mit_revolver():
        return []
    ergebnis = []
    im_job = set()

    def stecke(nummer, masse, laenge, halter):
        ergebnis.append((nummer, masse, laenge, halter))

    for eintrag in bs.eintraege(job, bibliothek) if job is not None else []:
        if eintrag.werkzeug is not None:
            im_job.add(eintrag.werkzeug.kennung)
        tc = eintrag.controller[0]
        laenge = rw.einspannung(tc, bibliothek).laenge
        halter = rw.werkzeughalter(tc, bibliothek)
        for nummer in eintrag.nummern:
            stecke(nummer, rw.werkzeugmasse(tc, bibliothek, laenge), laenge, halter)
    if bibliothek is None:
        return ergebnis
    maschine = getattr(pruefung, "maschine", None)
    datei = getattr(getattr(maschine, "Document", None), "FileName", "") or mg.maschine_von(job)
    magazin = mg.des_jobs(None, bibliothek, datei) if datei else None
    for eintrag in magazin.eintraege if magazin is not None else []:
        werkzeug = bibliothek.werkzeug_mit_kennung(eintrag.werkzeug)
        if eintrag.platz <= 0 or werkzeug is None or werkzeug.kennung in im_job:
            continue
        if not werkzeug.durchmesser:
            continue  # ohne Durchmesser keine Form (ein Drehwerkzeug)
        laenge = rw.laenge_des_werkzeugs(werkzeug, bibliothek)[0]
        halter = bibliothek.halter_fuer_pruefung(werkzeug)
        stecke(eintrag.platz, rw.masse_des_werkzeugs(werkzeug), laenge, halter)
    return ergebnis


def _beladen_koerper(pruefung, eintraege):
    """{Platz-Aufnahme: [Körper]} aus den Einträgen von _beladen_daten – der erste Eintrag je
    Platz zählt, einer ohne Maße oder Länge nicht."""
    if not eintraege or not pruefung.mit_revolver():
        return {}
    plaetze = {nummer: pruefung.werkzeugaufnahme(nummer) for nummer in pruefung.platznummern()}
    ergebnis = {}
    for nummer, masse, laenge, halter in eintraege:
        aufnahme = plaetze.get(nummer)
        if aufnahme is None or aufnahme in ergebnis or masse is None or laenge <= 0:
            continue
        glied, basis = pruefung._glied(aufnahme), pruefung._lage(aufnahme)
        kapseln = werkzeugkapseln(masse, laenge, halter)
        ergebnis[aufnahme] = [
            Koerper(
                _beladen_name(art, nummer, halter),
                art,
                form,
                glied,
                basis,
                kapseln=kapseln.get(art, ()),
            )
            for art, form in werkzeugkoerper(masse, laenge, halter)
        ]
    return ergebnis


def _beladen_name(art, nummer, halter):
    """„die Schneide von T2 (steckt im Revolver)“ – ein Teil eines Werkzeugs, das gerade nicht
    arbeitet."""
    return tr("kb.im_revolver", koerper=_werkzeug_name(art, nummer, halter))


def _werkzeug_name(art, nummer, halter):
    werkzeug = f"T{nummer}"
    if art in (SCHNEIDE, KERN):
        return tr("kb.schneide", werkzeug=werkzeug)
    if art == HALS:
        return tr("kb.hals", werkzeug=werkzeug)
    if art == SCHAFT:
        return tr("kb.schaft", werkzeug=werkzeug)
    return tr("kb.halter", werkzeug=werkzeug, halter=hl.text(halter))
