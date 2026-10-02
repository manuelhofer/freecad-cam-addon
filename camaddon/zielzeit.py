# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Zielzeit (Manuel, 2026-10-02: „Dass man erstmal ein Ziel rechnet von der Zeit her“): bevor
eine Bahn gerechnet wird, wie viel Volumen weg muss und wie lange ein Fräser mit seinen Werten
dafür mindestens braucht. Daran misst sich jede Strategie, und daran sieht man, ob der Fräser
für die Arbeit überhaupt passt – oder ein anderer aus der Werkzeugkiste schneller wäre
(vergleiche()).

Von oben gesehen steht je Zelle Material der Höhe T über dem Teil (wo kein Teil ist: bis zu
seinem Boden). Der Fräser nimmt es in ceil(T ÷ ap) gleichen Lagen, und jede Lage überstreicht
die Zelle einmal mit der Breite ae: Zielzeit = Σ Zelle · Lagen ÷ (ae · vf). So zählt bei einer
Fläche 1000 × 1000, von der 5 mm weg müssen, ap 5 – nicht das ap 25 des Einsatzes: viel
Volumen, aber der Fräser schafft nur ein Fünftel seines Zeitspanvolumens; bei 100 × 100, 25 mm
tief, das volle (Manuels Beispiele). Das wirksame ap ist Volumen ÷ Σ Zelle · Lagen.

Was der Fräser nicht erreicht – Innenecken und Nuten enger als er: die Schließung des Bodens
mit seiner Scheibe –, ist sein Rest; dafür braucht es danach einen kleineren (folge()). Eine
Untergrenze: Luft, Eintauchen, Halte und Eilgang kommen in jeder Bahn dazu – wie weit eine Bahn
darüber liegt, sagt, wie gut sie ist."""

import math
from dataclasses import dataclass

import numpy as np

from . import hoehenfeld as hf
from . import schnittdaten as sd
from . import vierachs_huelle as vh
from . import werkzeuge as wz

SCHRITT = 1.0  # mm – das Raster von oben, mindestens
ZELLEN = 250_000  # höchstens so viele Zellen – größere Teile bekommen ein gröberes Raster
TOLERANZ = 0.05  # mm – so fein wird das Teil vernetzt (eine Schätzung, keine Bahn)
DUENN = 0.01  # mm – weniger Material über einer Zelle zählt nicht (Rauschen des Netzes)
# Die Einsätze, mit denen ein Fräser Material wegnimmt – in dieser Reihenfolge gesucht.
WEGNEHMEN = (wz.SCHRUPPEN, wz.DYNAMISCH, wz.PLANEN, wz.VOLLNUT)
WEGNEHMER = (wz.SCHAFTFRAESER, wz.TORUSFRAESER, wz.PLANFRAESER, wz.NUTENFRAESER)


@dataclass
class Material:
    """Was weg muss, von oben: je Zelle (Mitten `x`, `y`) der Boden – das Teil, wo eins ist,
    sonst der Boden des Rohteils – unter der Oberseite `oben` (eine Zahl oder je Zelle)."""

    x: np.ndarray
    y: np.ndarray
    oben: object
    boden: np.ndarray  # (len(x), len(y)) – z, bis wohin weg muss
    sx: float
    sy: float

    @property
    def zelle(self):
        return self.sx * self.sy

    @property
    def hoehe(self):
        hoehe = np.maximum(self.oben - self.boden, 0.0)
        return np.where(hoehe > DUENN, hoehe, 0.0)

    @property
    def volumen(self):
        """mm³"""
        return float(self.hoehe.sum()) * self.zelle

    def ohne(self, erreicht):
        """Was bleibt, wenn bis `erreicht` (je Zelle) weggenommen ist – für den nächsten Fräser."""
        oben = np.minimum(np.maximum(erreicht, self.boden), self.oben)
        return Material(self.x, self.y, oben, self.boden, self.sx, self.sy)

    def bis(self, z, oben=None):
        """Nur, was über `z` liegt – und mit `oben` unter dieser Höhe: was eine Strategie bis zu
        ihren Flächen wegnimmt (Planfräsen der Oberseite: die Tasche darunter nicht; Räumen der
        Taschenböden nach dem Planfräsen: nur die Tasche)."""
        boden = np.maximum(self.boden, float(z))
        deckel = self.oben if oben is None else np.minimum(self.oben, float(oben))
        return Material(self.x, self.y, deckel, boden, self.sx, self.sy)


def material(teil, rohteil, oben, unten=None, schritt=None):
    """Das Material über dem Teil (Part-Form) im Rohteil von oben – (x_von, x_bis, y_von,
    y_bis) bis `oben`; `unten`: so tief reicht das Rohteil (None: bis zum Boden des Teils, was
    darunter liegt, bleibt). `schritt`: das Raster (None: SCHRITT, gröber für große Teile)."""
    x_von, x_bis, y_von, y_bis = (float(w) for w in rohteil)
    if unten is None:
        unten = teil.BoundBox.ZMin
    if schritt is None:
        schritt = max(SCHRITT, math.sqrt((x_bis - x_von) * (y_bis - y_von) / ZELLEN))
    x, sx = _mitten(x_von, x_bis, schritt)
    y, sy = _mitten(y_von, y_bis, schritt)
    # Ohne `innen`: Eine Mitte auf der inneren Kante zweier Dreiecke derselben Fläche fiele
    # sonst durch die Fläche (die Diagonale einer Deckfläche: 0,8 % zu viel Volumen).
    teilhoehe = hf.hoehen(vh.vernetze(teil, TOLERANZ), x, y)
    boden = np.where(np.isfinite(teilhoehe), teilhoehe, float(unten))
    return Material(x, y, float(oben), np.minimum(boden, float(oben)), sx, sy)


def _mitten(von, bis, schritt):
    """Die Mitten der Zellen von `von` bis `bis`, gleich breit, höchstens `schritt` – und ihre
    Breite."""
    anzahl = max(1, int(math.ceil((bis - von) / schritt - 1e-9)))
    breite = (bis - von) / anzahl
    return von + breite * (np.arange(anzahl) + 0.5), breite


@dataclass
class Ziel:
    """Die Zielzeit eines Fräsers mit seinen Werten für ein Material."""

    radius: float
    ae: float
    ap: float
    vf: float  # mm/min
    volumen: float  # mm³ – was er wegnehmen kann
    rest: float  # mm³ – was er nicht erreicht (Ecken, Nuten enger als er)
    zeit: float  # min
    ap_wirksam: float  # mm – so viel ap nutzt er im Mittel
    erreicht: np.ndarray = None  # je Zelle: so tief kommt er

    @property
    def zeitspanvolumen(self):
        """cm³/min – wirksam, mit dem ap, das die Stellen hergeben."""
        return self.volumen / self.zeit / 1000.0 if self.zeit > 0 else 0.0

    @property
    def zeitspanvolumen_voll(self):
        """cm³/min – mit dem vollen ap des Einsatzes (ae · ap · vf)."""
        return sd.zeitspanvolumen(self.ae, self.ap, self.vf)


def ziel(material, radius, ae, ap, vf):
    """Die Zielzeit eines Schaftfräsers mit `radius` und den Werten `ae`, `ap` (mm) und `vf`
    (mm/min) für das Material (material())."""
    erreicht = np.maximum(_schliessung(material, radius), material.boden)
    hoehe = np.maximum(material.oben - erreicht, 0.0)
    hoehe = np.where(hoehe > DUENN, hoehe, 0.0)
    lagen = np.ceil(hoehe / ap - 1e-9)
    ueberstrichen = float(lagen.sum()) * material.zelle
    volumen = float(hoehe.sum()) * material.zelle
    zeit = ueberstrichen / (ae * vf) if ae > 0 and vf > 0 else math.inf
    return Ziel(
        radius=radius,
        ae=ae,
        ap=ap,
        vf=vf,
        volumen=volumen,
        rest=max(material.volumen - volumen, 0.0),
        zeit=zeit,
        ap_wirksam=volumen / ueberstrichen if ueberstrichen > 0 else 0.0,
        erreicht=erreicht,
    )


def _schliessung(material, radius):
    """So tief kommt die Stirn eines Schaftfräsers mit `radius` je Zelle: Die Spitze steht über
    jeder Stelle so tief, wie der höchste Boden unter ihrer Scheibe zulässt (Dehnung), und eine
    Zelle wird so tief, wie die tiefste Spitze, deren Scheibe sie überdeckt (Schrumpfung). Neben
    dem Rohteil darf der Fräser stehen – dort liegt der Boden des Rohteils. Die Scheibe ist eine
    halbe Zelle kleiner: Der Boden ist in der Mitte jeder Zelle gemessen – eine Ecke mit dem
    Radius des Fräsers ließe im Raster sonst einen Saum stehen."""
    radius = max(radius - 0.5 * min(material.sx, material.sy), 0.0)
    rand_x = int(math.ceil(radius / material.sx)) + 1
    rand_y = int(math.ceil(radius / material.sy)) + 1
    unten = float(np.min(material.boden))
    feld = np.pad(material.boden, ((rand_x, rand_x), (rand_y, rand_y)), constant_values=unten)
    spitze = _scheibe(feld, radius, material.sx, material.sy, np.maximum, -math.inf)
    stirn = _scheibe(spitze, radius, material.sx, material.sy, np.minimum, math.inf)
    return stirn[rand_x:-rand_x, rand_y:-rand_y]


def _scheibe(feld, radius, sx, sy, wahl, fuell):
    """Je Zelle `wahl` (np.maximum, np.minimum) über die Scheibe mit `radius` um sie."""
    ergebnis = np.full(feld.shape, fuell)
    n = feld.shape[0]
    for di in range(int(math.floor(radius / sx)) + 1):
        quer = math.sqrt(max(radius * radius - (di * sx) ** 2, 0.0))
        lauf = _laufend(feld, int(math.floor(quer / sy + 1e-9)), wahl, fuell)
        if di >= n:
            break
        ergebnis[: n - di] = wahl(ergebnis[: n - di], lauf[di:])
        if di:
            ergebnis[di:] = wahl(ergebnis[di:], lauf[: n - di])
    return ergebnis


def _laufend(feld, halb, wahl, fuell):
    """Je Zelle `wahl` über das Fenster ±`halb` längs der zweiten Achse – in log₂ Schritten:
    Jeder Schritt verdoppelt das Fenster, zwei überlappende ergeben jede Breite."""
    if halb <= 0:
        return feld
    breite = 2 * halb + 1
    rand = np.full((feld.shape[0], halb), fuell)
    m = np.concatenate([rand, feld, rand], axis=1)
    k = 1
    while 2 * k <= breite:
        m = wahl(m[:, :-k], m[:, k:])
        k *= 2
    laenge = feld.shape[1]
    return wahl(m[:, :laenge], m[:, breite - k : breite - k + laenge])


@dataclass
class Angebot:
    """Ein Fräser der Werkzeugkiste mit seinem Einsatz und seiner Zielzeit."""

    werkzeug: object  # werkzeuge.Werkzeug
    einsatz: object  # werkzeuge.Einsatz
    ziel: Ziel
    danach: object = None  # Angebot für seinen Rest – None: er lässt keinen

    @property
    def zeit(self):
        """min – mit dem Fräser für den Rest."""
        return self.ziel.zeit + (self.danach.zeit if self.danach is not None else 0.0)


def werte(werkzeug, einsatz):
    """(ae, ap, vf) eines Einsatzes – ap 0: die Schneidenlänge; None, wenn etwas fehlt."""
    vf = sd.vorschub(sd.drehzahl(einsatz.vc, werkzeug.durchmesser), werkzeug.schneiden, einsatz.fz)
    ap = einsatz.ap or werkzeug.schneidenlaenge
    if werkzeug.schneidenlaenge > 0:
        ap = min(ap, werkzeug.schneidenlaenge)
    if einsatz.ae <= 0 or ap <= 0 or vf <= 0:
        return None
    return einsatz.ae, ap, vf


def einsatz_zum_wegnehmen(werkzeug, werkstoff=wz.ALLE):
    """Der Einsatz, mit dem der Fräser Material wegnimmt (WEGNEHMEN) und dem größten
    Zeitspanvolumen – None, wenn er keinen mit Werten hat."""
    besser = None
    for einsatz in werkzeug.einsaetze(werkstoff):
        if einsatz.art not in WEGNEHMEN or werte(werkzeug, einsatz) is None:
            continue
        q = sd.zeitspanvolumen(*werte(werkzeug, einsatz))
        if besser is None or q > besser[0]:
            besser = (q, einsatz)
    return besser[1] if besser else None


def vergleiche(material, werkzeuge, werkstoff=wz.ALLE, rest_klein=0.02):
    """Die Fräser der Werkzeugkiste nebeneinander: je Fräser (WEGNEHMER) mit seinem Einsatz zum
    Wegnehmen die Zielzeit – und für seinen Rest (mehr als `rest_klein` des Volumens) der
    schnellste kleinere, der ihn ganz schafft. [Angebot], das schnellste zuerst; wer am Ende
    noch etwas stehen lässt, steht hinter allen, die alles schaffen."""
    gesamt = material.volumen
    einzeln = []
    for werkzeug in werkzeuge:
        if werkzeug.art not in WEGNEHMER or werkzeug.durchmesser <= 0:
            continue
        einsatz = einsatz_zum_wegnehmen(werkzeug, werkstoff)
        if einsatz is None:
            continue
        ae, ap, vf = werte(werkzeug, einsatz)
        einzeln.append(
            Angebot(werkzeug, einsatz, ziel(material, werkzeug.durchmesser / 2, ae, ap, vf))
        )
    for angebot in einzeln:
        if angebot.ziel.rest <= rest_klein * gesamt:
            continue
        rest = material.ohne(angebot.ziel.erreicht)
        kleinere = []
        for anderes in einzeln:
            if anderes.werkzeug.durchmesser >= angebot.werkzeug.durchmesser:
                continue
            ae, ap, vf = anderes.ziel.ae, anderes.ziel.ap, anderes.ziel.vf
            fuer_rest = ziel(rest, anderes.ziel.radius, ae, ap, vf)
            if fuer_rest.rest <= rest_klein * gesamt:
                kleinere.append(Angebot(anderes.werkzeug, anderes.einsatz, fuer_rest))
        if kleinere:
            angebot.danach = min(kleinere, key=lambda a: a.zeit)
    return sorted(einzeln, key=lambda a: (not _schafft_alles(a, gesamt, rest_klein), a.zeit))


def _schafft_alles(angebot, gesamt, rest_klein):
    letztes = angebot.danach or angebot
    return angebot.ziel.rest <= rest_klein * gesamt or letztes.ziel.rest <= rest_klein * gesamt
