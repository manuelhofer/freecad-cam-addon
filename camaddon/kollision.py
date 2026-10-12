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
from . import uhren
from .kette import LINEAR
from .sprache import tr

WARNABSTAND = 1.0  # mm, Vorgabe
MIN_SCHRITT = 0.5  # mm: so fein wird es, wo es eng ist
BERUEHRT = 1e-3  # mm: näher gilt als Berührung
# mm: so weit um einen Körper herum nimmt der genaue Abstand die Flächen eines Teils aus einem STL
# (Koerper.ausschnitt) – liegt keine so nah, gilt dieser Abstand (weniger als der wahre).
AUSSCHNITT_RAND = 10.0
KAESTEN_HOECHSTENS = 2000  # Flächen: mehr hat ein Körper, dann ohne die Kästen je Fläche
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
# gemessen am Freiformbeispiel, 24 Kerne: 4 → 83 s, 16 → 60 s, 48 → 54 s; an Manuels 4-Achs-Testteil
# (Halter am Teil, jedes Stück beginnt mit genauen Abständen) 48 → 240 s, 24 → 192 s, 6 → 182 s
STUECKE_JE_ARBEITER = 24
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
    """{Art: ((p0, p1, r, flach), …)} – je Werkzeugteil Strecken (p0, p1: Punkte im LCS der
    Aufnahme) mit Radius, die den Körper aus werkzeugkoerper() enthalten, für die Netzschranke
    (netzabstand): `flach` – der Körper liegt ganz zwischen den Ebenen quer durch p0 und p1
    (Zylinder, Kegel, Schaftfräser samt Kern: unter der Stirn zählt der Abstand zur
    Stirnebene); nicht flach beim Kugelfräser und Lollipop – da beginnt die Strecke in der
    Kugelmitte, die Kapsel ist der Fräser selbst. Der Halter je Abschnitt eine. Beim geraden
    Halter liegen alle auf der Z-Achse; beim gewinkelten sind Werkzeug und Abschnitte gekippt
    wie in werkzeugkoerper() (halter.lage), der Kopf liegt längs der Aufnahmeachse
    (P-2026-10-10-59: an Manuels CLX mit „VDI40 angetrieben radial“ rechnete die Kollision
    sonst jeden Abstand genau – 5300 s auf 24 Kernen)."""
    spitze = -laenge
    if halter is not None and hl.form(halter) is not None:
        ende = -halter.laenge
    else:
        ende = min(spitze + masse.gesamt, 0.0) if masse.gesamt > 0 else 0.0
    oben = min(spitze + masse.schneide, ende)
    radius = masse.durchmesser / 2
    stirn = masse.stirn
    auf_z = {}  # Art -> ((z0, z1, r, flach), …) auf der Achse des Werkzeugs
    kugel = radius if masse.kugel else (stirn.kugel if stirn is not None and stirn.nur_kugel else 0)
    if kugel > 0:  # Kugel an der Spitze: die Kapsel ab der Kugelmitte ist der Fräser selbst
        mitte = spitze + kugel
        r = max(radius, kugel)
        auf_z[SCHNEIDE] = ((mitte, max(oben, mitte), r, False),)
        if r > EINDRINGEN:
            auf_z[KERN] = ((mitte, max(oben, mitte), r - EINDRINGEN, False),)
    elif oben - spitze > 1e-6 and radius > 0:
        auf_z[SCHNEIDE] = ((spitze, oben, radius, True),)
        if radius > EINDRINGEN:
            auf_z[KERN] = ((spitze + EINDRINGEN, oben, radius - EINDRINGEN, True),)
    if masse.hals_laenge > 0 and masse.hals_d > 0:
        hals_ende = min(oben + masse.hals_laenge, ende)
        if hals_ende - oben > 1e-6:
            auf_z[HALS] = ((oben, hals_ende, masse.hals_d / 2, True),)
        oben = hals_ende
    if masse.schaft > 0 and ende - oben > 1e-6:
        auf_z[SCHAFT] = ((oben, ende, masse.schaft / 2, True),)
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
            auf_z[HALTER] = tuple(stufen)
    gewinkelt = halter is not None and halter.gewinkelt
    matrix = hl.lage(halter).toMatrix() if gewinkelt else None

    def punkt(z):
        if matrix is None:
            return (0.0, 0.0, z)
        v = matrix.multiply(FreeCAD.Vector(0.0, 0.0, z))
        return (v.x, v.y, v.z)

    kapseln = {
        art: tuple((punkt(z0), punkt(z1), r, flach) for z0, z1, r, flach in teile)
        for art, teile in auf_z.items()
    }
    if gewinkelt and halter.kopf_d > 0 and halter.versatz > 0:
        # Der Kopf (halter.form): ein Zylinder längs der Aufnahmeachse, ungekippt.
        kopf = ((0.0, 0.0, 0.0), (0.0, 0.0, -(halter.versatz + halter.kopf_d / 2)))
        kapseln[HALTER] = kapseln.get(HALTER, ()) + ((*kopf, halter.kopf_d / 2, True),)
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
    # Ein Teil aus einem STL (stl_teil.flaechennetz_fuer, in eigenen Koordinaten): (Punkte,
    # Dreiecke, Fläche je Dreieck) – sein Netz ist genau, und OpenCascade rechnet nur mit den
    # Flächen in der Nähe (_ausschnitt; P-2026-10-11-101).
    stl: object = None
    _netze: dict = field(default_factory=dict, repr=False)
    _ausschnitt_daten: object = field(default=None, repr=False)
    _kaesten: object = field(default=None, repr=False)  # flaechen_kaesten()
    _flaechen_liste: object = field(default=None, repr=False)  # flaechen_liste()
    _dreiecke_gebaut: dict = field(default_factory=dict, repr=False)  # dreiecks_verbund()
    ausschnitt_gegen: object = field(default=None, repr=False)  # aus dem letzten ausschnitt()
    _huelle: object = field(default=None, repr=False)

    def huelle(self):
        """Der Hüllquader dieses Teils aus einem STL als Körper an seiner Lage – gegen ihn ist
        der Abstand nie größer als gegen das Teil, und OpenCascade rechnet ihn in Mikrosekunden
        (das Bett gegen den Geist: 77 s)."""
        import Part

        if self._huelle is None:
            punkte = self.stl[0]
            unten, oben = punkte.min(axis=0), punkte.max(axis=0)
            groesse = np.maximum(oben - unten, 1e-6)
            self._huelle = Part.makeBox(*map(float, groesse), FreeCAD.Vector(*map(float, unten)))
        self._huelle.Placement = self.form.Placement
        return self._huelle

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
        if toleranz not in self._netze and self.stl is not None:
            punkte, dreiecke, _flaeche = self.stl
            self._netze[toleranz] = na.Netz(None, toleranz, ecken=punkte[dreiecke])
        if toleranz not in self._netze:
            form = self.form.copy()
            form.Placement = FreeCAD.Placement()
            try:
                self._netze[toleranz] = na.Netz(form, toleranz)
            except Exception:  # eine Form, die sich nicht vernetzen lässt: ohne Schranke
                self._netze[toleranz] = None
        return self._netze[toleranz]

    def _ausschnitt_vorbereiten(self):
        """(Kästen der Dreiecke unten, oben, Ecken je Dreieck) – einmal."""
        if self._ausschnitt_daten is None:
            punkte, dreiecke, _flaeche = self.stl
            ecken = punkte[dreiecke]
            self._ausschnitt_daten = (ecken.min(axis=1), ecken.max(axis=1), ecken)
        return self._ausschnitt_daten

    def dreiecks_verbund(self, dreiecke):
        """Die Dreiecke `dreiecke` (Indizes) als ebene Flächen in einem Verbund an der Lage dieses
        Teils – aus denselben Punkten wie die Flächen des Körpers, also genau sie; je Dreieck
        einmal gebaut (P-2026-10-11-109: so braucht kein Nebenrechner den Körper mit 68.242
        Flächen, je 1 GB)."""
        import Part

        ecken = self._ausschnitt_vorbereiten()[2]
        flaechen = []
        for j in np.unique(np.asarray(dreiecke, dtype=np.int64)):
            f = self._dreiecke_gebaut.get(int(j))
            if f is None:
                p = [FreeCAD.Vector(*e) for e in ecken[j]]
                try:
                    f = Part.Face(Part.makePolygon([*p, p[0]]))
                except Part.OCCError:
                    continue  # entartet: kein Punkt, der nicht auch auf einer Nachbarin läge
                self._dreiecke_gebaut[int(j)] = f
            flaechen.append(f)
        verbund = Part.makeCompound(flaechen)
        verbund.Placement = self.form.Placement
        return verbund

    def ausschnitt(self, anderer):
        """Die Flächen dieses Teils aus einem STL nahe am Körper `anderer` (an ihren gesetzten
        Lagen) als Verbund an der Lage dieses Teils – None, wenn keine näher als AUSSCHNITT_RAND
        liegt (dann sind beide mindestens so weit auseinander). Gewählt über die Hüllquader der
        Dreiecke gegen den des anderen, in eigenen Koordinaten."""

        unten_d, oben_d, _ecken = self._ausschnitt_vorbereiten()
        box = anderer.form.BoundBox
        zurueck = np.array(self.form.Placement.inverse().toMatrix().A, dtype=float).reshape(4, 4)
        ecken = np.array(
            [(x, y, z) for x in (box.XMin, box.XMax) for y in (box.YMin, box.YMax)
             for z in (box.ZMin, box.ZMax)],
            dtype=float,
        ) @ zurueck[:3, :3].T + zurueck[:3, 3]  # fmt: skip
        unten, oben = ecken.min(axis=0) - AUSSCHNITT_RAND, ecken.max(axis=0) + AUSSCHNITT_RAND
        nah = np.all((oben_d >= unten) & (unten_d <= oben), axis=1)
        if not nah.any():
            return None
        dreiecke = np.flatnonzero(nah)
        gegen = None  # die Flächen des anderen, die nah genug liegen (sonst der ganze)
        enger = self._enger(anderer, dreiecke, unten_d, oben_d)
        if enger is not None:
            dreiecke, gegen = enger
        self.ausschnitt_gegen = gegen
        return self.dreiecks_verbund(dreiecke)

    def _enger(self, anderer, dreiecke, unten_d, oben_d):
        """Die Dreiecke unter `dreiecke`, die dem Körper `anderer` am nächsten sein können – über
        die Hüllquader seiner einzelnen Flächen statt seines ganzen (P-2026-10-11-109; der
        Revolver gegen den Geist: Tausende Flächen je Stelle, 0,39 s): Erst der genaue Abstand d
        zum Dreieck, dessen Kasten einem Flächenkasten am nächsten liegt; dann alle, deren Kasten
        höchstens d von einem Flächenkasten entfernt liegt – ein weiteres kann nicht näher sein.
        None, wenn das nichts bringt (der Körper hat zu viele Flächen)."""
        import Part

        kaesten = anderer.flaechen_kaesten()
        if kaesten is None or len(dreiecke) < 64:
            return None
        m = np.array(
            self.form.Placement.inverse().multiply(anderer.form.Placement).toMatrix().A,
            dtype=float,
        ).reshape(4, 4)
        ecken = kaesten @ m[:3, :3].T + m[:3, 3]  # (Flächen, 8, 3) in eigenen Koordinaten
        f_lo, f_hi = ecken.min(axis=1), ecken.max(axis=1)
        lo, hi = unten_d[dreiecke], oben_d[dreiecke]
        luecke = np.maximum(
            np.maximum(lo[:, None, :] - f_hi[None, :, :], f_lo[None, :, :] - hi[:, None, :]), 0.0
        )
        schranke = np.sqrt(np.einsum("tfj,tfj->tf", luecke, luecke)).min(axis=1)
        erstes = dreiecke[int(np.argmin(schranke))]
        einzeln = self.dreiecks_verbund([erstes])
        try:
            d_oben = anderer.form.distToShape(einzeln)[0]
        except Exception:  # noqa: BLE001 – dann ohne
            return None
        drin = schranke <= d_oben + 1e-9
        # Vom anderen nur die Flächen, deren Kasten einem der verbliebenen Dreiecke höchstens d
        # nahe kommt – an ihnen liegt der nächste Punkt.
        je_flaeche = np.sqrt(np.einsum("tfj,tfj->tf", luecke[drin], luecke[drin])).min(axis=0)
        nahe_flaechen = np.flatnonzero(je_flaeche <= d_oben + 1e-9)
        gegen = None
        if 0 < len(nahe_flaechen) < len(kaesten):
            gegen = Part.makeCompound([anderer.flaechen_liste()[i] for i in nahe_flaechen])
            gegen.Placement = anderer.form.Placement
        return dreiecke[drin], gegen

    def flaechen_liste(self):
        """Seine Flächen an der eigenen Lage (Faces) – einmal, zu flaechen_kaesten()."""
        if getattr(self, "_flaechen_liste", None) is None:
            lage = self.form.Placement
            self.form.Placement = FreeCAD.Placement()
            try:
                self._flaechen_liste = self.form.Faces
            finally:
                self.form.Placement = lage
        return self._flaechen_liste

    def flaechen_kaesten(self):
        """Die Ecken der Hüllquader seiner Flächen ((Flächen, 8, 3), eigene Koordinaten) – einmal;
        None bei mehr als KAESTEN_HOECHSTENS Flächen."""
        if self._kaesten is None:
            lage = self.form.Placement
            self.form.Placement = FreeCAD.Placement()
            try:
                if self.form.countElement("Face") > KAESTEN_HOECHSTENS:
                    self._kaesten = False
                else:
                    self._kaesten = np.array(
                        [
                            [(x, y, z) for x in (b.XMin, b.XMax) for y in (b.YMin, b.YMax)
                             for z in (b.ZMin, b.ZMax)]
                            for b in (f.BoundBox for f in self.form.Faces)
                        ],
                        dtype=float,
                    ).reshape(-1, 8, 3)  # fmt: skip
            finally:
                self.form.Placement = lage
        return None if self._kaesten is False else self._kaesten

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
    # Der Halter des Werkzeugs der Operation (Nummer in der Abfahrt) am Teil (ausspannung): wie
    # weit das Werkzeug heraussteht und wie weit es hier müsste (mm; 0: nicht gerechnet).
    halter_am_teil: int = -1
    werkzeug: str = ""
    heraus: float = 0.0
    mindestens: float = 0.0

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
        if self.mindestens > self.heraus:
            text += " " + tr(
                "kb.ausspannung",
                werkzeug=self.werkzeug,
                heraus=rw.weg_text(self.heraus),
                mindestens=rw.weg_text(math.ceil(self.mindestens)),
            )
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
    teil_stl: object = (
        None  # (Punkte, Dreiecke, Fläche je Dreieck), wenn das Teil aus einem STL ist
    )

    def zum_senden(self):
        from . import nebenrechner as nr

        teil = self.teil
        if teil is not None and self.teil_stl is not None:
            # Ein Teil aus einem STL: Die Nebenrechner rechnen genau mit seinen Dreiecken
            # (Koerper.dreiecks_verbund); als Form genügt ihnen sein Hüllquader – für die Lage im
            # Raum und die Drehfaktoren (eher zu groß: kleinere Schritte). Den Körper selbst
            # baute jeder neu, je 1 GB (P-2026-10-11-109).
            import Part

            kasten = teil.BoundBox
            teil = Part.makeBox(
                max(kasten.XLength, 1e-6), max(kasten.YLength, 1e-6), max(kasten.ZLength, 1e-6),
                FreeCAD.Vector(kasten.XMin, kasten.YMin, kasten.ZMin),
            )  # fmt: skip
        return replace(
            self,
            teil=nr.Form.von(teil) if teil is not None else None,
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
    from . import stl_teil

    teil = _teil_form(job)
    if teil is None:
        ergebnis.hinweise.append(tr("kb.kein_teil"))
    teil_stl = stl_teil.flaechennetz_fuer(teil) if teil is not None else None
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
        teil_stl,
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
    _abschliessen(
        ergebnis, list(welt.schlimmste.values()), abfahrt, job, rohteil, fortschritt, bibliothek
    )
    return ergebnis


def _abschliessen(ergebnis, befunde, abfahrt, job, rohteil, fortschritt, bibliothek=None):
    """Die Eilgänge ins Rohteil dazu, sortieren, den Fortschritt auf 1 – und wo der Halter am
    Teil ist, wie weit das Werkzeug dort herausstehen müsste (ausspannung)."""
    if rohteil and not ergebnis.abgebrochen:
        befunde += _eilgaenge_ins_rohteil(abfahrt, job)
    # Zwischendurch bedient der Fortschritt die Oberfläche (an Manuels Nasen-Testteil ~2 s).
    zwischendurch = (lambda: fortschritt(0.999)) if fortschritt is not None else None
    try:
        ausspannung(befunde, abfahrt, job, bibliothek, zwischendurch)
    except Exception as fehler:  # noqa: BLE001 – ohne den Satz bleibt der Befund, wie er ist
        FreeCAD.Console.PrintLog(f"CAM-Addon: Ausspannung nicht gerechnet: {fehler}\n")
    # Berührungen zuerst, dann was nur näher kommt – je nach der Zeit.
    ergebnis.befunde = sorted(befunde, key=lambda b: (not b.beruehrung, b.zeit, b.a, b.b))
    if fortschritt is not None and not ergebnis.abgebrochen:
        fortschritt(1.0)


AUSSPANNUNG_HOECHSTENS = 300.0  # mm – weiter heraus sucht ausspannung() nicht
AUSSPANNUNG_SCHRITTE = 10  # Halbierungen: auf 0,3 mm (gemeldet aufgerundet auf ganze mm)
AUSSPANNUNG_STATIONEN = 20  # so viele Stationen nach der ersten Berührung sieht sie nach
# … und über die ganze Operation höchstens so viele Stichproben, dann um die schlimmste herum fein
# (höchstens AUSSPANNUNG_FEIN Stationen): Beim Schruppen in Lagen streift der Halter zuerst nur und
# steckt erst eine Lage tiefer richtig drin (P-2026-10-11-63).
AUSSPANNUNG_PROBEN = 1500
AUSSPANNUNG_FEIN = 400
AUSSPANNUNG_ZELLE = 25.0  # mm – so nah beieinander liegende Stellen fragt sie auf einmal ab
AUSSPANNUNG_NETZ = 0.05  # mm – so fein vernetzt sie das Teil
AUSSPANNUNG_TIEFER = 0.1  # mm – so weit (nach Netz und Schranke) muss der Halter im Teil stecken


def ausspannung(befunde, abfahrt, job, bibliothek=None, zwischendurch=None):
    """Trägt in jeden Befund „der Halter am Teil“ (Befund.halter_am_teil) ein, wie weit das
    Werkzeug heraussteht und wie weit es dort mindestens müsste – der Halter so weit längs der
    Werkzeugachse zurück, dass er das Teil nicht mehr berührt (Manuel, 2026-10-11: „sehr klar
    darauf hinweisen das die ausspannlänge des fräsers nicht ausreicht“). Nachgesehen an der
    ersten Berührung und den Stationen danach (höchstens AUSSPANNUNG_STATIONEN) und über die ganze
    Operation (AUSSPANNUNG_PROBEN Stichproben, um die schlimmste fein) – „mindestens“ gilt so für
    die ganze Operation wie im 4-Achs-Assistenten (vierachs_halter). Je Stelle auf einmal:
    die Kapseln des Halters (werkzeugkapseln) gegen das Netz des Teils (netzabstand), halbiert –
    auch mit gewinkeltem Halter (Revolver): Die Achse ist die des Werkzeugs. Mit OpenCascade Stelle
    für Stelle waren es an Manuels Nasen-Testteil 39 s. `zwischendurch()` wird zwischen den Abfragen
    gerufen (die Oberfläche bleibt bedienbar)."""
    befunde = [b for b in befunde if b.beruehrung and b.halter_am_teil >= 0]
    if not befunde:
        return
    pruefung = abfahrt.pruefung
    teil = _teil_form(job)
    if teil is None or pruefung.werkstueckaufnahme is None:
        return
    netz = na.Netz(teil, AUSSPANNUNG_NETZ)
    werkstueck_glied = pruefung._glied(pruefung.werkstueckaufnahme)
    am_nullpunkt = pruefung._lage(pruefung.werkstueckaufnahme).multiply(
        FreeCAD.Placement(FreeCAD.Vector(*abfahrt.nullpunkt), FreeCAD.Rotation())
    )
    for befund in befunde:
        op = abfahrt.operationen[befund.halter_am_teil]
        halter = rw.werkzeughalter(op.tc, bibliothek)
        if halter is None:
            continue
        masse = rw.werkzeugmasse(op.tc, bibliothek, op.laenge)
        kapseln = werkzeugkapseln(masse, op.laenge, halter).get(HALTER, ())
        if not kapseln:
            continue
        # Je Stelle die Kapseln in Koordinaten des Teils und die Werkzeugachse (zur Aufnahme).
        achse_lcs = FreeCAD.Vector(0, 0, 1)
        if halter.gewinkelt:
            achse_lcs = hl.lage(halter).Rotation.multVec(achse_lcs)

        def bedarf(stellen, op=op, kapseln=kapseln, achse_lcs=achse_lcs):
            """Je Stelle: so weit (mm) müsste das Werkzeug weiter heraus, damit der Halter dort
            nicht ans Teil stößt – 0, wo er frei ist oder auch AUSSPANNUNG_HOECHSTENS nicht reicht.
            """
            von, nach, achsen = [], [], []
            for st in stellen:
                lage = _halter_im_teil(pruefung, op, werkstueck_glied, am_nullpunkt, st)
                achse = lage.Rotation.multVec(achse_lcs)
                for p0, p1, _r, _flach in kapseln:
                    von.append(tuple(lage.multVec(FreeCAD.Vector(*p0))))
                    nach.append(tuple(lage.multVec(FreeCAD.Vector(*p1))))
                    achsen.append(tuple(achse))
            von, nach, achsen = (np.array(x, dtype=float) for x in (von, nach, achsen))
            radien = np.tile([r for _p0, _p1, r, _f in kapseln], len(stellen))
            flach = np.tile([bool(f) for _p0, _p1, _r, f in kapseln], len(stellen))
            je = len(kapseln)
            halter_hier = (netz, von, nach, achsen, radien, flach, je)
            if zwischendurch is not None:
                zwischendurch()
            ergebnis = np.zeros(len(stellen))
            an = np.flatnonzero(_halter_stoesst(halter_hier, np.zeros(len(stellen))))
            if not len(an):
                return ergebnis
            # Weiter nur mit den Stellen, an denen er anstößt.
            zeilen = (an[:, None] * je + np.arange(je)).ravel()
            halter_hier = (netz, von[zeilen], nach[zeilen], achsen[zeilen], radien[zeilen])
            halter_hier += (flach[zeilen], je)
            reicht = ~_halter_stoesst(halter_hier, np.full(len(an), AUSSPANNUNG_HOECHSTENS))
            unten = np.zeros(len(an))
            oben = np.where(reicht, AUSSPANNUNG_HOECHSTENS, 0.0)
            for _ in range(AUSSPANNUNG_SCHRITTE):
                if zwischendurch is not None:
                    zwischendurch()
                mitte = (unten + oben) / 2
                noch = _halter_stoesst(halter_hier, mitte) & reicht
                unten = np.where(noch, mitte, unten)
                oben = np.where(noch, oben, mitte)
            ergebnis[an] = oben
            return ergebnis

        # An der ersten Berührung und den Stationen danach …
        stellen = [abfahrt.stellungen_bei(befund.zeit)]
        k = befund.station
        while (
            k < len(abfahrt.stationen)
            and len(stellen) <= AUSSPANNUNG_STATIONEN
            and abfahrt.stationen[k].operation == befund.halter_am_teil
        ):
            stellen.append(abfahrt.stellungen_an(k))
            k += 1
        noetig = float(bedarf(stellen).max())
        # … und über die ganze Operation: Stichproben, um die schlimmste herum fein.
        erste = op.erste
        letzte = (
            abfahrt.operationen[befund.halter_am_teil + 1].erste - 1
            if befund.halter_am_teil + 1 < len(abfahrt.operationen)
            else len(abfahrt.stationen) - 1
        )
        proben = np.unique(
            np.linspace(erste, letzte, min(AUSSPANNUNG_PROBEN, letzte - erste + 1)).astype(int)
        )
        if len(proben):
            je_probe = bedarf([abfahrt.stellungen_an(int(i)) for i in proben])
            if je_probe.max() > 0:
                noetig = max(noetig, float(je_probe.max()))
                schritt = max(1, (letzte - erste) // max(len(proben) - 1, 1))
                mitte = int(proben[int(np.argmax(je_probe))])
                fein = np.arange(max(erste, mitte - schritt), min(letzte, mitte + schritt) + 1)
                if len(fein) > AUSSPANNUNG_FEIN:
                    fein = fein[:: int(math.ceil(len(fein) / AUSSPANNUNG_FEIN))]
                noetig = max(
                    noetig, float(bedarf([abfahrt.stellungen_an(int(i)) for i in fein]).max())
                )
        if noetig <= 0:
            continue  # nirgends ein Halter, der mit mehr Auskragung frei wäre
        heraus = op.laenge - halter.laenge if halter.laenge else masse.gesamt
        befund.werkzeug = f"T{getattr(op.tc, 'ToolNumber', 0)}"
        befund.heraus = max(float(heraus), 0.0)
        befund.mindestens = befund.heraus + noetig


def _halter_stoesst(halter, weiter):
    """Je Stelle: stößt der Halter ans Teil, um `weiter` (mm je Stelle) längs der Werkzeugachse
    zurückgezogen? `halter`: (Netz des Teils, Kapseln von, nach, Achse, Radien, flach, Kapseln je
    Stelle) aus ausspannung()."""
    netz, von, nach, achsen, radien, flach, je_stelle = halter
    w = np.repeat(np.asarray(weiter, dtype=float), je_stelle)[:, None] * achsen
    von, nach = von + w, nach + w
    # Je Zelle eine Abfrage: netzabstand sammelt die Dreiecke um alle Strecken einer Abfrage –
    # Stellen über das ganze Teil verteilt (Stichproben) hießen sonst alle Dreiecke gegen alle
    # Strecken (an Manuels Nasen-Testteil 5,3 s).
    n = len(von) // je_stelle
    mitte = ((von + nach) / 2).reshape(n, je_stelle, 3).mean(axis=1)
    _zellen, gruppe = np.unique(
        np.floor(mitte / AUSSPANNUNG_ZELLE).astype(np.int64), axis=0, return_inverse=True
    )
    gruppe = np.asarray(gruppe).ravel()
    reichweite = float(radien.max()) + 1.0
    stoesst = np.zeros(n, dtype=bool)
    for g in range(int(gruppe.max()) + 1 if n else 0):
        stellen = np.flatnonzero(gruppe == g)
        zeilen = (stellen[:, None] * je_stelle + np.arange(je_stelle)).ravel()
        abstand = netz.kapseln(von[zeilen], nach[zeilen], reichweite, radien[zeilen], flach[zeilen])
        stoesst[stellen] = (abstand.reshape(-1, je_stelle) < -AUSSPANNUNG_TIEFER).any(axis=1)
    return stoesst


def _halter_im_teil(pruefung, op, werkstueck_glied, am_nullpunkt, stellungen):
    """Die Lage der Aufnahme von `op` in Koordinaten des Teils bei diesen Stellungen – wie _Welt
    die Körper stellt (Bewegung des Glieds · Lage), das Teil am Nullpunkt."""
    wege = {achse: pruefung.verfahren.weg_bei(achse, w) for achse, w in stellungen.items()}
    lage_werkzeug = pruefung._glied_lage(pruefung._glied(op.aufnahme), wege).multiply(
        pruefung._lage(op.aufnahme)
    )
    lage_teil = pruefung._glied_lage(werkstueck_glied, wege).multiply(am_nullpunkt)
    return lage_teil.inverse().multiply(lage_werkzeug)


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
    gesamt = max(1, sum(b - a for a, b in bereiche))
    # Je Kern einer: Auf den SMT-Zwillingen bremst sich OpenCascade aus (P-2026-10-10-63). Die
    # Stücke der Reihe nach, jedes mit dem, was die früheren schon fanden (P-2026-10-11-107).
    gleichzeitig = max(1, min(nr.physische_kerne(), pool.anzahl))
    stuecke = [None] * len(bereiche)
    laufend = {}  # Auftrag -> Nummer des Stücks
    naechstes = 0

    def vergeben():
        nonlocal naechstes
        while naechstes < len(bereiche) and len(laufend) < gleichzeitig:
            bekannt = _bekannt_vor(stuecke, naechstes)
            auftrag = pool.auftrag(
                "kollision",
                "stueck",
                kopie,
                maschine,
                g_fahrt,
                g_daten,
                warnabstand,
                bereiche[naechstes],
                fortschritt=nr.Fortschritt(),
                bekannt=bekannt,
            )
            laufend[auftrag] = naechstes
            naechstes += 1

    def zwischendurch():
        if fortschritt is None:
            return True
        fertig = sum(
            bereiche[j][1] - bereiche[j][0] for j, s in enumerate(stuecke) if s is not None
        )
        unterwegs = sum(
            a.fortschritt * (bereiche[j][1] - bereiche[j][0]) for a, j in laufend.items()
        )
        return fortschritt((fertig + unterwegs) / gesamt * 0.999) is not False

    try:
        vergeben()
        # Die Eilgänge ins Rohteil rechnet dieser Prozess, während die Stücke laufen.
        # Das Fenster ist gesperrt, der Fortschritt arbeitet ohnehin Ereignisse ab: Der Abtrag
        # darf dabei atmen (an der Nocke stand es dafür 1,8 s; P-2026-10-11-68).
        with uhren.atmend():
            rohteil_befunde = _eilgaenge_ins_rohteil(abfahrt, job) if rohteil else []
        while laufend:
            for auftrag in pool.warten_bis_einer(list(laufend), zwischendurch):
                stuecke[laufend.pop(auftrag)] = auftrag.ergebnis
            vergeben()
    except nr.Fehler:
        for auftrag in laufend:
            pool.abbrechen(auftrag)
        raise
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
    _abschliessen(ergebnis, befunde, abfahrt, job, False, fortschritt, bibliothek)
    return ergebnis


def _bekannt_vor(stuecke, nummer):
    """{Schlüssel: kleinster Abstand} aus den fertigen Stücken vor `nummer` (stuecke: Ergebnisse
    von stueck() oder None) – nur frühere: So bleibt die gemeldete Stelle die erste, wie bei der
    Prüfung nacheinander."""
    bekannt = {}
    for stueck in stuecke[:nummer]:
        if stueck is None:
            continue
        for k, befund in stueck["schlimmste"].items():
            if befund.abstand < bekannt.get(k, math.inf):
                bekannt[k] = befund.abstand
    return bekannt


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


def lage_als_daten(lage):
    """Eine Lage (FreeCAD.Placement, halter.lage) als Zahlen für die Nebenrechner – None bleibt."""
    if lage is None:
        return None
    return (tuple(lage.Base), tuple(lage.Rotation.Q))


def _lage_aus_daten(daten):
    if daten is None:
        return None
    basis, q = daten
    return FreeCAD.Placement(FreeCAD.Vector(*basis), FreeCAD.Rotation(*q))


def am_werkstueck_stueck(dokument, maschine, operationen, nullpunkt, achsen, stationen):
    """abfahren.Abfahrt.am_werkstueck für ein Stück Stationen – im Nebenrechner.
    `operationen`: je Operation (Name der Aufnahme, Länge, Lage – lage_als_daten); `achsen`: die
    Achsen der Abfahrt als Nummern in der Kette; `stationen`: [(Operation, wirksame Stellungen,
    dreht eine Rundachse?, Punkt im Programm)]."""
    from .kinematik import Kinematik

    pruefung = _pruefung_fuer(dokument, maschine)
    kette = pruefung.kette.achsen
    achsen = [kette[i] for i in achsen]
    kinematiken = {}
    ergebnis = []
    for operation, wirksam, dreht, punkt in stationen:
        if not dreht:
            ergebnis.append(punkt)
            continue
        kinematik = kinematiken.get(operation)
        if kinematik is None:
            aufnahme, laenge, lage = operationen[operation]
            kinematik = Kinematik(
                pruefung,
                dokument.getObject(aufnahme),
                rw.Einspannung(laenge, _lage_aus_daten(lage)),
                FreeCAD.Vector(*nullpunkt),
            )
            kinematiken[operation] = kinematik
        stellungen = {a: w for a, w in zip(achsen, wirksam, strict=True) if w is not None}
        ergebnis.append(kinematik.am_werkstueck(stellungen))
    return ergebnis


def stueck(dokument, maschine, fahrt, daten, warnabstand, bereich, fortschritt=None, bekannt=None):
    """Prüft die Stationen `bereich` (von, bis) – im Nebenrechner. Gibt die Befunde je Paar,
    die Zahl der Stellen und die Hinweise zurück, als Daten ohne FreeCAD-Objekte. `bekannt`: was
    frühere Stücke fanden (_Welt.bekannt_setzen)."""
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
    welt.bekannt_setzen(bekannt)
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
                tr("kb.teil"), TEIL, daten.teil, self.werkstueck_glied, am_nullpunkt,
                stl=daten.teil_stl,
            )  # fmt: skip
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
        self._felder = {}  # Operation -> ihre Paare als Felder (_Paarfeld)
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
        self._schranke = None  # je Paar des Felds: Abstand mindestens (np, −inf: unbekannt)
        self._genau = None  # … hier genau gerechnet?
        self._schranken_feld = None  # das Paarfeld, zu dem sie gehören
        for feld in getattr(self, "_felder", {}).values():
            feld.schon[:] = False  # die Befunde fangen neu an
        self.bekannt = {}  # bekannt_setzen()
        self._operation = None  # die Operation des letzten Abschnitts
        # Die geraden Vorschubwege der Operation [(Anfang, Ende)] (Programmpunkte, Rundachsen
        # gleich) – ein Eilgang darauf fährt die Schneide, wo sie schon im Vorschub war.
        self._vorschubwege = []
        self._eigener_zuletzt = False  # lag der Abschnitt davor auf einem eigenen Weg?

    def bekannt_setzen(self, bekannt):
        """Die schlimmsten Abstände, die frühere Stücke schon fanden ({(Operation, Name a, Name b,
        nur Vorschub): mm}, P-2026-10-11-107): Ein Paar, das sich dort schon berührte, rechnet
        dieses Stück nicht mehr – wie die Prüfung nacheinander, die es nach der ersten Berührung
        weglässt. Sonst rechnete jedes Stück, das mitten in einer Strecke beginnt, an der der Schaft
        knapp am Teil liegt, dort jede Stelle genau (am Nasen-Testteil ein Stück 194 s statt 3 s).
        """
        self.bekannt = dict(bekannt or {})
        for operation, feld in self._felder.items():
            self._bekannt_anwenden(feld, operation)

    def _bekannt_anwenden(self, feld, operation):
        if not self.bekannt:
            return
        for k, paar in enumerate(feld.paare):
            schluessel = (operation, paar.a.name, paar.b.name, paar.nur_vorschub)
            if self.bekannt.get(schluessel, math.inf) <= 0.0:
                feld.schon[k] = True

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
        if schluessel not in self._schon_gemessen and _quader_spalt(a, b) > BERUEHRT:
            # Die Hüllquader liegen auseinander – ohne OpenCascade, das an einem Körper aus einem
            # STL (68.242 Flächen) je Paar Minuten rechnete (P-2026-10-11-101).
            self._schon_gemessen[schluessel] = False
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
        deltas = np.array(
            [
                abs(b - a) if a is not None and b is not None else 0.0
                for a, b in zip(von, nach, strict=True)
            ]
        )
        feld = self._feld(ziel.operation)
        # Je Paar: so weit bewegen sich die beiden gegeneinander auf dem ganzen Abschnitt.
        paarwege = feld.faktoren @ deltas if len(deltas) else np.zeros(len(feld.paare))
        # Die Schranken gelten weiter, wenn die Maschine stetig hierher fuhr – nicht nach
        # einem Sprung (eine Achse bekommt hier ihren ersten Wert), und nur für Paare, die
        # schon bisher zählten: Die anderen fuhren, ohne dass es mitgezählt hat.
        sprung = any((a is None) != (b is None) for a, b in zip(von, nach, strict=True))
        if sprung or ziel.operation != self._operation or self._schranken_feld is not feld:
            self._schranke = np.full(len(feld.paare), -math.inf)
            self._genau = np.zeros(len(feld.paare), dtype=bool)
            self._schranken_feld = feld
        if ziel.operation != self._operation:
            self._vorschubwege = []
        self._operation = ziel.operation
        eigener_weg = self._eigener_weg(stationen[i], ziel, naechste != i)
        # Ein Eilgang, der dort beginnt, wo ein Vorschub aufhörte: je Paar der Schneide der
        # Abstand am Anfang (nach unten abgeschätzt).
        anfang = {} if ziel.eilgang and not stationen[i].eilgang else None
        bewegt = paarwege > 0
        s = 0.0
        while True:
            self._melden()
            self.ergebnis.stellen += 1
            if self.ergebnis.stellen > HOECHSTENS:
                return False
            weiter = self._stelle(i, naechste, s, feld, paarwege, ziel, anfang, eigener_weg)
            if s >= 1.0 or naechste == i:
                return True
            neu = min(1.0, s + weiter)
            gemerkt = bewegt & (self._schranke > -math.inf)
            if gemerkt.any():
                self._schranke[gemerkt] -= paarwege[gemerkt] * (neu - s)
                self._genau[gemerkt] = False
            if weiter == math.inf:  # nichts, was zählt, kommt sich näher
                return True
            s = neu

    def _feld(self, operation):
        """Die Paare der Operation als Felder (_Paarfeld), je Operation einmal gebaut."""
        feld = self._felder.get(operation)
        if feld is None:
            feld = self._felder[operation] = _Paarfeld(self, self.paare(operation))
            self._bekannt_anwenden(feld, operation)
        return feld

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

    def _stelle(self, i, naechste, s, feld, paarwege, ziel, anfang=None, eigener_weg=False):
        """Prüft die Stelle beim Anteil `s` zwischen Station i und der nächsten; gibt zurück,
        wie weit (als Anteil) es von hier sicher weitergeht: je Paar, das hier zählt, sein
        Abstand (nach unten abgeschätzt) minus Warnabstand, mindestens MIN_SCHRITT, geteilt
        durch seinen Weg (`paarwege`); math.inf, wenn sich nichts gegeneinander bewegt.
        Was es genau rechnet, merkt es als Schranke (_schranke, _genau). `anfang`: Eilgang nach
        einem Vorschub – die Abstände der Schneide am Anfang.

        Die Hüllquader aller Körper und ihre Lücken je Paar rechnet numpy für alle Paare
        zugleich (_Paarfeld) – je Paar in Python waren es an Manuels Nasen-Testteil auf der
        CLX550 85 Paare je Stelle, 0,5 ms (P-2026-10-11-85); einzeln geht es nur weiter, wo ein
        Paar so nah ist, dass die Netzschranke oder OpenCascade entscheiden."""
        abfahrt = self.abfahrt
        von, nach = abfahrt.wirksam(i), abfahrt.wirksam(naechste)
        wege = {}
        for achse, a, b in zip(abfahrt.achsen, von, nach, strict=True):
            if a is None and b is None:
                continue
            wert = b if a is None else a if b is None else a + s * (b - a)
            wert = self.verfahren.begrenzt(achse, wert)
            wege[achse] = self.verfahren.weg_bei(achse, wert)
        # Je Glied seine Lage, je Körper (Glied · Basis) sein Hüllquader in Weltachsen.
        bewegung = []
        lagen = np.empty((len(feld.glieder), 4, 4))
        for g, glied in enumerate(feld.glieder):
            platz = self.pruefung._glied_lage(glied, wege)
            bewegung.append(platz)
            lagen[g] = np.array(platz.toMatrix().A).reshape(4, 4)
        m = np.matmul(lagen[feld.glied_von], feld.basis)
        drehung = m[:, :3, :3]
        mitte = np.einsum("kij,kj->ki", drehung, feld.mitte) + m[:, :3, 3]
        halb = np.einsum("kij,kj->ki", np.abs(drehung), feld.halb)
        unten, oben = mitte - halb, mitte + halb
        pa, pb = feld.pa, feld.pb
        spalt = np.maximum(np.maximum(unten[pa] - oben[pb], unten[pb] - oben[pa]), 0.0)
        # Welche Paare zählen hier?
        aktiv = ~feld.schon
        if ziel.eilgang:
            aktiv &= ~feld.nur_vorschub
        else:
            aktiv &= ~feld.nur_eilgang
        if eigener_weg:
            aktiv &= ~feld.nur_eilgang  # die Schneide fährt, wo sie eben im Vorschub war
        schranke, genau = self._schranke, self._genau
        reicht = feld.reicht
        abstand = np.maximum(np.sqrt(np.sum(spalt * spalt, axis=1)), schranke)
        # Enger: die gedrehten Hüllquader – an einem gekippten Rundtisch ist der Quader in
        # Weltachsen riesig, längs seiner Normalen bleibt er flach.
        nah = aktiv & ~genau & (abstand <= reicht + QUADER_NAH)
        if nah.any():
            a_, b_ = pa[nah], pb[nah]
            abstand[nah] = np.maximum(
                abstand[nah],
                _quader_luecken(
                    mitte[a_], drehung[a_], feld.halb[a_], mitte[b_], drehung[b_], feld.halb[b_]
                ),
            )
        platzierung = {}  # Körper → seine Lage hier; an die Form erst, wenn genau gerechnet wird

        def platz(koerper):
            if koerper not in platzierung:
                g = feld.glied_index[id(koerper)]
                platzierung[koerper] = bewegung[g].multiply(koerper.basis)
            return platzierung[koerper]

        def rechne_genau(k):
            paar = feld.paare[k]
            for koerper in (paar.a, paar.b):
                koerper.form.Placement = platz(koerper)
            wert, stelle = self._abstand(paar.a, paar.b)
            schranke[k], genau[k] = wert, True
            return wert, stelle

        geschaetzt = np.zeros(len(feld.paare), dtype=bool)
        knapp = np.zeros(len(feld.paare), dtype=bool)
        for k in np.flatnonzero(aktiv & ~genau & (abstand <= reicht)):
            paar = feld.paare[k]
            # Enger noch: das Werkzeugteil als Kapseln gegen das Netz des anderen – meist
            # entscheidet das, ohne OpenCascade (Spezifikation Strategien 16.5, Hebel 2).
            netz = self._netzschranke(paar, platz, reicht[k])
            if netz is not None:
                geschaetzt[k] = True
                knapp[k] = netz[1]
                if netz[0] > abstand[k]:
                    abstand[k] = netz[0]
                    schranke[k], genau[k] = netz[0], False
            if abstand[k] <= reicht[k]:  # vielleicht ein Befund
                if self._nicht_schlimmer(paar, ziel.operation, abstand[k], anfang):
                    continue
                abstand[k], stelle = rechne_genau(k)
                if geschaetzt[k]:
                    self._netz_gelernt(paar, abstand[k] > reicht[k])
                if abstand[k] <= reicht[k] and _zaehlt(paar, k, abstand[k], s, anfang):
                    self._merke(paar, float(abstand[k]), stelle, i, naechste, s, ziel)
                    befund = self.schlimmste.get(
                        (ziel.operation, paar.a.name, paar.b.name, paar.nur_vorschub)
                    )
                    feld.schon[k] = befund is not None and befund.abstand <= 0.0
        if anfang is not None and s == 0.0:
            for k in np.flatnonzero(aktiv & feld.nur_eilgang):
                anfang[int(k)] = float(abstand[k])
        # Macht ein Paar den Schritt nur mit seiner Schranke am kürzesten, rechnet es genau –
        # oft liegt es weiter weg, als die Schranke sagt; außer der Schritt reicht auch so bis
        # zur nächsten Station. Davor einmal die Netzschranke, wenn sie noch fehlt: Sie reicht
        # eine Zellenbreite weit und kostet einen Bruchteil – und sieht sie die Oberfläche
        # näher als das, ist sie fast der genaue Abstand (der Kern der Schneide im Vorschub:
        # immer EINDRINGEN von der Oberfläche, ein genauer Abstand machte den Schritt nicht
        # größer). Befunde gibt es dabei keine mehr: Der genaue Abstand ist nie kleiner als
        # die Schranke.
        kandidaten = np.flatnonzero(aktiv & (paarwege > 1e-9))
        if not len(kandidaten):
            return math.inf
        weg = paarwege[kandidaten]
        anteile = np.maximum(abstand[kandidaten] - feld.abzug[kandidaten], MIN_SCHRITT) / weg
        fertig = genau[kandidaten] | knapp[kandidaten]
        while True:
            j = int(np.argmin(anteile))
            k = int(kandidaten[j])
            if fertig[j] or s + anteile[j] >= 1.0:
                return float(anteile[j])
            if not geschaetzt[k]:
                geschaetzt[k] = True
                netz = self._netzschranke(feld.paare[k], platz, reicht[k])
                if netz is not None and (netz[0] > abstand[k] or netz[1]):
                    if netz[0] > abstand[k]:
                        schranke[k], genau[k] = netz[0], False
                        abstand[k] = netz[0]
                        anteile[j] = max(netz[0] - feld.abzug[k], MIN_SCHRITT) / weg[j]
                    fertig[j] = netz[1]
                    continue
            wert, _stelle = rechne_genau(k)
            abstand[k] = wert
            anteile[j] = max(wert - feld.abzug[k], MIN_SCHRITT) / weg[j]
            fertig[j] = True

    def _nicht_schlimmer(self, paar, operation, mindestens, anfang):
        """Hat das Paar in der Operation schon einen Befund, der nicht weiter weg ist als
        `mindestens` (die Schranke hier)? Dann wird die Stelle kein schlimmerer – _merke nähme
        sie nicht –, genau rechnen braucht es sie dafür nicht. Am Nasen-Testteil auf der CLX550
        rechnete es den Halter von T2 beim Wegfahren vom Teil an jeder Stelle genau, 20 ms je
        Stelle. Nicht im Eilgang nach einem Vorschub: Dort zählt der Abstand am Anfang
        (`anfang`, _zaehlt), und der braucht den genauen Wert."""
        if anfang is not None and paar.nur_eilgang:
            return False
        schluessel = (operation, paar.a.name, paar.b.name, paar.nur_vorschub)
        befund = self.schlimmste.get(schluessel)
        if befund is not None and befund.abstand <= mindestens:
            return True
        # Was frühere Stücke schon fanden (bekannt_setzen): Auch dann wird es hier kein
        # schlimmerer – beim Zusammenführen bliebe der frühere.
        return self.bekannt.get(schluessel, math.inf) <= mindestens

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
        m = platzierung(anderer).inverse().multiply(platzierung(werkzeug)).toMatrix()
        p0 = np.array([k[0] for k in werkzeug.kapseln], dtype=float)
        p1 = np.array([k[1] for k in werkzeug.kapseln], dtype=float)
        radius = np.array([k[2] for k in werkzeug.kapseln])
        flach = np.array([k[3] for k in werkzeug.kapseln])
        drehung = np.array(
            [[m.A11, m.A12, m.A13], [m.A21, m.A22, m.A23], [m.A31, m.A32, m.A33]], dtype=float
        )
        ursprung = np.array([m.A14, m.A24, m.A34])
        von = ursprung + p0 @ drehung.T
        nach = ursprung + p1 @ drehung.T
        # So weit suchen, dass die Schranke über `reicht` hinaus noch einen Schritt erlaubt.
        reichweite = float(radius.max()) + reicht + NETZ_SCHRITT
        werte = netz.kapseln(von, nach, reichweite, radius, flach)
        k = int(np.argmin(werte))
        knapp = bool(werte[k] < reichweite - radius[k] - netz.toleranz - 1e-9)
        return float(werte[k]), knapp

    def _abstand(self, a, b):
        """(Abstand in mm, Stelle) zweier Körper an ihrer gesetzten Lage; 0, wenn sie sich
        berühren oder einer im anderen steckt. Ein Teil aus einem STL nur mit seinen Flächen in
        der Nähe (Koerper.ausschnitt) – am Geist (68.242 Flächen) sonst Sekunden je Stelle."""
        form_a, form_b = a.form, b.form
        if a.stl is not None or b.stl is not None:
            stl, anderer = (a, b) if a.stl is not None else (b, a)
            try:
                grob, _punkte, _info = anderer.form.distToShape(stl.huelle())
            except Exception:  # dann eben mit den Flächen
                grob = 0.0
            if grob > AUSSCHNITT_RAND:  # schon der Hüllquader weiter weg: das Teil erst recht
                return grob, None
            if anderer.kapseln:
                genau = self._abstand_stl(stl, anderer)
                if genau is not None:
                    return genau
            nah = stl.ausschnitt(anderer)
            if nah is None:
                return AUSSCHNITT_RAND, None
            gegen = getattr(stl, "ausschnitt_gegen", None) or anderer.form
            form_a, form_b = (nah, gegen) if stl is a else (gegen, nah)
        try:
            abstand, punkte, _info = form_a.distToShape(form_b)
        except Exception:  # eine Form, mit der OpenCascade nicht rechnen kann, hält nichts an
            if (a.name, b.name) not in self._fehler:
                self._fehler.add((a.name, b.name))
                self.ergebnis.hinweise.append(tr("kb.fehler", a=a.name, b=b.name))
            return math.inf, None
        stelle = (punkte[0][0] + punkte[0][1]) * 0.5 if punkte else None
        return abstand, stelle

    def _abstand_stl(self, stl, werkzeug):
        """Der genaue Abstand eines Werkzeugteils (mit Kapseln, die es enthalten) zu einem Teil
        aus einem STL, an ihren gesetzten Lagen – OpenCascade nur mit den Dreiecken, die näher
        sein können (P-2026-10-11-109): erst gegen das Dreieck, dem die Kapseln am nächsten kommen
        (eine Fläche – ein Abstand d nach oben), dann gegen alle, denen sie näher als d kommen.
        Weiter entfernte können nicht die nächsten sein. Am Geist mit dem Halter sonst Tausende
        Flächen je Stelle, 0,33 s. (Abstand, Stelle) oder None (dann wie bisher)."""
        netz = stl.netz(fein=True)
        if netz is None:
            return None
        m = stl.form.Placement.inverse().multiply(werkzeug.form.Placement).toMatrix()
        drehung = np.array(
            [[m.A11, m.A12, m.A13], [m.A21, m.A22, m.A23], [m.A31, m.A32, m.A33]], dtype=float
        )
        ursprung = np.array([m.A14, m.A24, m.A34])
        p0 = np.array([k[0] for k in werkzeug.kapseln], dtype=float) @ drehung.T + ursprung
        p1 = np.array([k[1] for k in werkzeug.kapseln], dtype=float) @ drehung.T + ursprung
        radien = np.array([k[2] for k in werkzeug.kapseln], dtype=float)
        dreiecke, schranke = netz.dreiecke_nah(p0, p1, radien, AUSSCHNITT_RAND)
        if not len(dreiecke):
            return AUSSCHNITT_RAND, None  # die Kapseln, die das Teil enthalten, sind so weit weg

        def abstand_zu(welche):
            verbund = stl.dreiecks_verbund(welche)
            try:
                d, punkte, _info = werkzeug.form.distToShape(verbund)
            except Exception:  # noqa: BLE001 – dann wie bisher
                return None
            stelle = (punkte[0][0] + punkte[0][1]) * 0.5 if punkte else None
            return d, stelle

        naechstes = abstand_zu(dreiecke[[int(np.argmin(schranke))]])
        if naechstes is None:
            return None
        kandidaten = dreiecke[schranke <= naechstes[0] + 1e-9]
        if len(kandidaten) <= 1:
            return naechstes
        alle = abstand_zu(kandidaten)
        return alle if alle is not None and alle[0] <= naechstes[0] else naechstes

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
        werkzeug = self.werkzeuge[ziel.operation]
        halter_am_teil = -1
        am_teil = self.teil is not None and (paar.a is self.teil or paar.b is self.teil)
        if am_teil and any(k is paar.a or k is paar.b for k in werkzeug if k.art == HALTER):
            halter_am_teil = ziel.operation
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
            halter_am_teil=halter_am_teil,
        )


class _Paarfeld:
    """Die Paare einer Operation als Felder für _stelle: je Körper sein Glied, seine Basis
    (4 × 4), Mitte und halbe Kanten seines Hüllquaders; je Paar die Körper, was zählt, und je
    Achse, wie weit sich die beiden gegeneinander bewegen (_paarfaktoren)."""

    def __init__(self, welt, paare):
        self.paare = paare
        koerper, index = [], {}
        for paar in paare:
            for k in (paar.a, paar.b):
                if id(k) not in index:
                    index[id(k)] = len(koerper)
                    koerper.append(k)
        glieder, glied_index = [], {}
        for k in koerper:
            if id(k.glied) not in glied_index:
                glied_index[id(k.glied)] = len(glieder)
                glieder.append(k.glied)
        self.glieder = glieder
        self.glied_von = np.array([glied_index[id(k.glied)] for k in koerper], dtype=int)
        self.glied_index = {id(k): glied_index[id(k.glied)] for k in koerper}
        self.basis = np.array([np.array(k.basis.toMatrix().A).reshape(4, 4) for k in koerper])
        self.basis = self.basis.reshape(len(koerper), 4, 4)
        self.mitte = np.array([k.mitte for k in koerper], dtype=float).reshape(-1, 3)
        self.halb = np.array([k.halb for k in koerper], dtype=float).reshape(-1, 3)
        self.pa = np.array([index[id(p.a)] for p in paare], dtype=int)
        self.pb = np.array([index[id(p.b)] for p in paare], dtype=int)
        self.nur_eilgang = np.array([p.nur_eilgang for p in paare], dtype=bool)
        self.nur_vorschub = np.array([p.nur_vorschub for p in paare], dtype=bool)
        # Beim Kern zählt nur eine Berührung: kein Warnabstand, auch nicht für den Schritt.
        self.reicht = np.where(self.nur_vorschub, BERUEHRT, welt.warn)
        self.abzug = np.where(self.nur_vorschub, 0.0, welt.warn)
        self.faktoren = np.array([welt._paarfaktoren(p) for p in paare], dtype=float).reshape(
            len(paare), len(welt.abfahrt.achsen)
        )
        # Stecken die beiden in dieser Operation schon ineinander (Abstand 0)? Dann bleibt der
        # Befund, wie er ist – das Paar braucht nicht mehr gerechnet zu werden.
        self.schon = np.zeros(len(paare), dtype=bool)


def _quader_spalt(a, b):
    """Der Abstand der Hüllquader zweier Körper an ihrer Grundlage (`basis`), in Weltachsen –
    nie mehr als ihr wahrer Abstand."""
    unten, oben = [], []
    for k in (a, b):
        m = np.array(k.basis.toMatrix().A, dtype=float).reshape(4, 4)
        mitte = m[:3, :3] @ np.asarray(k.mitte, dtype=float) + m[:3, 3]
        halb = np.abs(m[:3, :3]) @ np.asarray(k.halb, dtype=float)
        unten.append(mitte - halb)
        oben.append(mitte + halb)
    spalt = np.maximum(np.maximum(unten[0] - oben[1], unten[1] - oben[0]), 0.0)
    return float(np.sqrt(np.sum(spalt * spalt)))


def _quader_luecken(ca, ra, ha, cb, rb, hb):
    """_quader_luecke für viele Paare zugleich: je Paar (Mitten (n, 3), Drehungen (n, 3, 3) –
    die Achsen in den Spalten –, halbe Kanten (n, 3)) die größte Lücke der Schatten auf die
    sechs Kantenrichtungen; 0, wenn überall überdeckt."""
    achsen_a = np.swapaxes(ra, 1, 2)  # je Zeile eine Achse
    achsen_b = np.swapaxes(rb, 1, 2)
    u = np.concatenate([achsen_a, achsen_b], axis=1)  # (n, 6, 3)
    schatten_a = np.einsum("nuk,nk->nu", np.abs(np.einsum("nuj,nkj->nuk", u, achsen_a)), ha)
    schatten_b = np.einsum("nuk,nk->nu", np.abs(np.einsum("nuj,nkj->nuk", u, achsen_b)), hb)
    luecke = np.abs(np.einsum("nuj,nj->nu", u, cb - ca)) - schatten_a - schatten_b
    return np.maximum(luecke.max(axis=1), 0.0)


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
