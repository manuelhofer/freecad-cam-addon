# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Grenze des Erlaubten zwischen den Knoten des Rasters – gegen die „Zacken aus dem Raster“
(Spezifikation Strategien 13.6).

Das Raster des Räumens (raeumen_bahn._Feld) weiß je Knoten, ob die Spitze auf einer Lage dorthin
darf. Der Ring an der Wand war die Höhenlinie des Abstands zu den gesperrten Knoten, das
Gesperrte dafür eine Zelle breiter: Er folgte den Zellen. An Manuels Testteil lief er in der
Mulde in Treppen von 0,5 mm (219 von 237 Sätzen mit einer Ecke ab 15°), und der Fräser blieb
0,64 bis 1,19 mm vor der Fläche stehen statt 0,3 (gemessen 2026-11-12).

Hier wird die Grenze selbst gesucht – dort, wo die Hüllfläche des Fräsers genau so hoch liegt,
wie die Lage es erlaubt:

- **Wo:** Die Linie zwischen erlaubten und gesperrten Knoten kreuzt Kanten des Rasters. Auf
  jeder dieser Kanten liegt die Grenze irgendwo zwischen dem erlaubten und dem gesperrten Knoten;
  `Nachrechner.grenze` sucht die Stelle mit der Hüllfläche selbst (dieselbe Rechnung wie an den
  Knoten, vierachs_huelle.je_stellung_stueck) – per Sekante, wo die Fläche glatt ist, sonst durch
  Halbieren (eine senkrechte Wand: die Hüllfläche springt) – auf GENAU, und nimmt die letzte
  Stelle, die nachgerechnet erlaubt ist. Nie die Schätzung.
- **Der Ring:** Die Punkte rücken um ABSTAND ins Freie, werden zu Geraden und Kreisbögen
  gefasst (bogenfit, höchstens BOGEN daneben – in der Mulde wird aus dem Achteck ein Kreis) und
  an ihren Proben noch einmal nachgerechnet. Hält eine Probe nicht, gibt es für diese Lage keine
  genaue Grenze: Der Aufrufer rechnet sie wie bisher.
- **Die Ringe davor:** `Grenze.abstand` ist der Abstand jedes Knotens zu diesen Punkten statt zu
  den Zellen – seine Höhenlinien folgen dem glatten Rand (`ring_glatt` fasst auch sie in Bögen).

Näher als bisher erlaubt kommt der Fräser nirgends: Erlaubt ist wie an den Knoten, wo die
Hüllfläche des um Aufmaß und Toleranz größeren Fräsers plus Zugabe nicht über der Lage liegt.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import bogenfit as bf
from . import hoehenfeld as hf
from . import kontur_bahn as kb
from . import raeumen_bahn as rb
from . import vierachs_huelle as vh

GENAU = 0.005  # mm – so nah liegt jeder Punkt der Grenze an der wirklichen, auf der freien Seite
# So weit rückt der Ring von der Grenze ins Freie: Platz für das Fassen in Bögen (BOGEN) und für
# die Sehne zwischen zwei Punkten um eine runde Ecke (höchstens 0,35 mm lang; bei einem Radius
# ab 3 mm – der Fräser um eine scharfe Kante – 0,005 mm).
ABSTAND = 0.015  # mm
BOGEN = 0.01  # mm – so weit dürfen Geraden und Bögen des Rings neben seinen Punkten liegen
# Die Ringe davor (Höhenlinien des Abstands, zwischen den Knoten linear): so weit daneben.
GLATT = 0.03  # mm
# So dicht wird jeder Ring vor dem Fahren nachgerechnet (Strecken und Bögen, nicht nur die
# Proben im Abstand des Rasters): Zwischen zwei Stellen weicht ein Bogen ab Radius 6 mm – der
# Fräser um eine Kante – höchstens 0,001 mm von seiner Sehne ab.
PRUEFEN = 0.2  # mm
GLEICH = rb.GLEICH
_NAH = 0.05  # mm – so nah beieinander zählen zwei Punkte der Grenze als einer (je Kante ≥ 0,5 mm)


@dataclass
class Grenze:
    """Die Grenze einer Lage: `abstand` (nx, ny) – mm bis zur Grenze, im Gesperrten negativ;
    `ringe` – die Ringe an der Wand (raeumen_bahn._Ring, genau); `erlaubt_an(x, y)` rechnet
    beliebige Stellen nach."""

    abstand: np.ndarray
    ringe: list
    hoch: float  # so hoch darf die Hüllfläche liegen (mm)
    nachrechner: object
    netz: object = None  # nur die Dreiecke über `hoch` (Nachrechner._ueber) – sagt dasselbe

    def erlaubt_an(self, x, y):
        """Je Stelle: Darf die Spitze auf dieser Lage dorthin – nachgerechnet, nicht aus dem
        Raster?"""
        return self.nachrechner.hoehe(x, y, self.netz) <= self.hoch + GLEICH

    def ring_glatt(self, punkte, geschlossen, material_links, feld, werte, schritt):
        """Ein Ring aus einer Höhenlinie von `abstand` – ring_glatt (für raeumen_bahn, ohne
        diesen Baustein zu laden)."""
        return ring_glatt(punkte, geschlossen, material_links, feld, werte, schritt)


class Nachrechner:
    """Die Hüllfläche eines Feldes (raeumen_bahn._Feld) an beliebigen Stellen: dieselbe Rechnung
    wie an seinen Knoten (hoehenfeld.zeilen_stueck – das Netz so weit gehoben, dass alles über 0
    liegt), nur nicht im Raster."""

    def __init__(self, feld, netz, geformt):
        self.feld = feld
        self.form = geformt
        z = netz.punkte[:, 2] if len(netz.punkte) else np.zeros(0)
        self.hub = hf._UEBER_NULL - float(z.min()) if len(z) and z.min() <= 0.0 else 0.0
        if self.hub:
            gehoben = netz.punkte + np.array([0.0, 0.0, self.hub])
            netz = vh.Netz(gehoben, netz.dreiecke, netz.toleranz)
        self.netz = netz
        self.stellen = 0  # so viele Stellen nachgerechnet
        self.lagen = 0  # Lagen mit genauer Grenze
        self.zurueck = 0  # Lagen, auf denen ein Ring nicht hielt

    def hoehe(self, x, y, netz=None):
        """Die Hüllfläche an den Stellen (x, y) – so tief darf die Spitze dort (ohne Zugabe),
        KEIN_TREFFER, wo der Fräser das Teil nicht trifft. `netz`: nur diese Dreiecke (_ueber)."""
        netz = self.netz if netz is None else netz
        x = np.asarray(x, dtype=float).ravel()
        y = np.asarray(y, dtype=float).ravel()
        if not len(x) or not len(netz.dreiecke):
            return np.full(len(x), hf.KEIN_TREFFER)
        self.stellen += len(x)
        # Längs y, die Höhe z, quer x: wie eine Zeile des Rasters, je Stelle mit eigenem Versatz.
        roh = vh.je_stellung_stueck(
            netz, (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), self.form, np.zeros(len(x)), x, y
        )
        return np.where(np.isfinite(roh), roh - self.hub, roh)

    def _ueber(self, hoch, x=None, y=None):
        """Das Netz nur mit den Dreiecken, die über `hoch` reichen – mit (x, y) nur nahe diesen
        Stellen. Ob die Hüllfläche über `hoch` liegt, sagt es genau wie das ganze: Ein Dreieck
        hebt die Spitze höchstens bis zu seinem höchsten Punkt (die Schneide liegt über der
        Spitze). Am Testteil halbiert es die Rechenzeit der Grenze."""
        netz = self.netz
        if not len(netz.dreiecke) or (x is not None and not len(x)):
            return netz
        ecken = netz.punkte[netz.dreiecke]  # (m, 3, 3), gehoben
        behalten = ecken[:, :, 2].max(axis=1) - self.hub > hoch - GLEICH
        if x is not None:
            weit = float(self.form.aussen().radius) + 1.0
            unten, oben = ecken.min(axis=1), ecken.max(axis=1)
            behalten &= (
                (oben[:, 0] >= float(np.min(x)) - weit)
                & (unten[:, 0] <= float(np.max(x)) + weit)
                & (oben[:, 1] >= float(np.min(y)) - weit)
                & (unten[:, 1] <= float(np.max(y)) + weit)
            )
        return vh.Netz(netz.punkte, netz.dreiecke[behalten], netz.toleranz)

    def grenze(self, lage, ziel, erlaubt, material_links, schritt, wo=None):
        """Die Grenze (Grenze) des Erlaubten auf der Lage – `erlaubt` wie feld.erlaubt_feld(lage,
        ziel). `wo` (nx, ny): nur Linien, die dort einen Punkt haben, bekommen einen Ring (die
        anderen bleiben, wo das Raster sie sieht – niemand fährt an ihnen). None, wenn es keine
        Grenze gibt, das Feld nicht nur von der Hüllfläche begrenzt ist (eine Tasche: `nur`) oder
        ein Ring beim Nachrechnen nicht hält."""
        feld = self.feld
        if feld.nur is not None or erlaubt.all() or not erlaubt.any():
            return None
        hoch = max(lage - feld.zugabe, ziel)
        linien = rb._hoehenlinien(np.where(erlaubt, 1.0, -1.0), feld.xs, feld.ys, 0.0)
        linien = [(p, g) for p, g in linien if len(p) >= 2]
        if not linien:
            return None
        # Jeder Punkt liegt mitten auf einer Kante des Rasters: zwischen welchen Knoten?
        alle = np.vstack([p for p, _g in linien])
        s = feld.schritt
        fx, fy = (alle[:, 0] - feld.x0) / s, (alle[:, 1] - feld.y0) / s
        quer = np.abs(fx - np.rint(fx)) > 0.25  # die Kante liegt längs x
        i0 = np.where(quer, np.floor(fx), np.rint(fx)).astype(int)
        j0 = np.where(quer, np.rint(fy), np.floor(fy)).astype(int)
        i1, j1 = i0 + quer, j0 + ~quer
        vorn = erlaubt[i0, j0]  # der erlaubte Knoten der Kante ist (i0, j0)
        ai, aj = np.where(vorn, i0, i1), np.where(vorn, j0, j1)
        bi, bj = np.where(vorn, i1, i0), np.where(vorn, j1, j0)
        ax, ay, bx, by = feld.xs[ai], feld.ys[aj], feld.xs[bi], feld.ys[bj]
        grenzen = np.cumsum([0] + [len(p) for p, _g in linien])
        gebraucht = np.ones(len(alle), dtype=bool)
        if wo is not None:
            for k in range(len(linien)):
                teil = slice(grenzen[k], grenzen[k + 1])
                gebraucht[teil] = bool(wo[ai[teil], aj[teil]].any())
        t = np.zeros(len(alle))
        if not gebraucht.any():
            return None
        g = gebraucht
        netz = self._ueber(hoch, np.concatenate([ax[g], bx[g]]), np.concatenate([ay[g], by[g]]))
        t[g] = self._verfeinern(ax[g], ay[g], bx[g], by[g], hoch, netz)
        px, py = ax + t * (bx - ax), ay + t * (by - ay)
        ringe = []
        for k, (_p, geschlossen) in enumerate(linien):
            teil = slice(grenzen[k], grenzen[k + 1])
            if not gebraucht[teil][0]:
                continue
            ring = _ring(
                px[teil], py[teil], ax[teil] - bx[teil], ay[teil] - by[teil], geschlossen,
                material_links, schritt,
            )  # fmt: skip
            if ring is None:
                continue
            pruef = kb._abtasten(ring.segmente, PRUEFEN, geschlossen)
            if not (self.hoehe(pruef.x, pruef.y, netz) <= hoch + GLEICH).all():
                self.zurueck += 1
                return None
            ringe.append(ring)
        self.lagen += 1
        abstand = _abstand(feld, erlaubt, quer, i0, j0, np.where(quer, px, py))
        return Grenze(abstand, ringe, hoch, self, self._ueber(hoch))

    def _verfeinern(self, ax, ay, bx, by, hoch, netz=None):
        """Je Kante vom erlaubten Knoten A zum gesperrten B der Anteil t des Wegs, bis zu dem die
        Spitze nachgerechnet erlaubt ist – höchstens GENAU vor einer gesperrten Stelle. Durch
        Halbieren: Schätzen aus den Knoten (Gerade, Parabel) lag am Testteil im Mittel 0,13 mm
        daneben – die Hüllfläche steigt vor der Wand der Mulde fast senkrecht –, und die Sekante
        brauchte mehr Stellen (8,6 je Kante) als das Halbieren (6)."""
        n = len(ax)
        lo, hi = np.zeros(n), np.ones(n)
        eps = GENAU / self.feld.schritt
        while True:
            offen = np.flatnonzero(hi - lo > eps)
            if not len(offen):
                return lo
            t = 0.5 * (lo[offen] + hi[offen])
            f = self.hoehe(
                ax[offen] + t * (bx[offen] - ax[offen]),
                ay[offen] + t * (by[offen] - ay[offen]),
                netz,
            )
            gut = f <= hoch + GLEICH
            lo[offen[gut]] = t[gut]
            hi[offen[~gut]] = t[~gut]


def _gefasst(punkte, geschlossen, toleranz):
    """Der Linienzug `punkte` (m, 2) in Strecken und Bögen (kontur_bahn), höchstens `toleranz`
    daneben (bogenfit) – geschlossen bis zurück zum ersten Punkt."""
    p = np.asarray(punkte, dtype=float)
    if geschlossen:
        p = np.vstack([p, p[:1]])
    kette = np.column_stack([p, np.zeros(len(p))])
    segmente = []
    vorher = 0
    for index, bogen in bf.stuecke(kette, toleranz):
        von = (float(p[vorher, 0]), float(p[vorher, 1]))
        nach = (float(p[index, 0]), float(p[index, 1]))
        vorher = index
        if math.hypot(nach[0] - von[0], nach[1] - von[1]) <= 1e-9:
            continue
        if bogen is None:
            segmente.append(kb._Strecke(von, nach))
        else:
            segmente.extend(kb._geteilt(kb._Bogen(von, nach, (bogen[0], bogen[1]), bool(bogen[2]))))
    return segmente


def _ring(px, py, frei_x, frei_y, geschlossen, material_links, schritt):
    """Der Ring an der Grenze durch die Punkte (px, py) – (frei_x, frei_y) zeigt je Punkt vom
    gesperrten zum erlaubten Knoten seiner Kante: um ABSTAND ins Freie gerückt, so gerichtet,
    dass das Gesperrte (dort steht das Material) links liegt – oder rechts –, in Strecken und
    Bögen gefasst. None, wenn es keiner wird (zu wenige Punkte)."""
    p = np.column_stack([px, py])
    frei = np.column_stack([frei_x, frei_y])
    # Liegt die Grenze nahe an einem Knoten, liegen die Punkte seiner beiden Kanten fast
    # aufeinander – und oft in verkehrter Folge: Am Testteil lief die Rampe rundum dort 0,001 mm
    # zurück (ein „Kehren“ im Prüfstand). Von solchen Punkten bleibt einer.
    behalten = np.zeros(len(p), dtype=bool)
    letzter = None
    for k in range(len(p)):
        if letzter is None or math.hypot(*(p[k] - p[letzter])) > _NAH:
            behalten[k] = True
            letzter = k
    if geschlossen and behalten.sum() > 2:
        erster = int(np.flatnonzero(behalten)[0])
        if math.hypot(*(p[erster] - p[letzter])) <= _NAH:
            behalten[letzter] = False
    p, frei = p[behalten], frei[behalten]
    if len(p) < (3 if geschlossen else 2):
        return None
    if geschlossen:
        t = np.roll(p, -1, axis=0) - np.roll(p, 1, axis=0)
    else:
        t = np.empty_like(p)
        t[1:-1] = p[2:] - p[:-2]
        t[0], t[-1] = p[1] - p[0], p[-1] - p[-2]
    lang = np.hypot(t[:, 0], t[:, 1])
    n = np.column_stack([-t[:, 1], t[:, 0]]) / np.maximum(lang, 1e-12)[:, None]  # links der Fahrt
    seite = n[:, 0] * frei[:, 0] + n[:, 1] * frei[:, 1]  # > 0: links liegt das Freie
    # Eine Höhenlinie hat das Erlaubte durchweg auf derselben Seite: Alle Punkte rücken dorthin,
    # auch die an einer Ecke, wo die Kante fast längs der Linie liegt (dort sagte das Vorzeichen
    # je Punkt nichts).
    links_frei = float(seite.sum()) > 0.0
    q = p + ABSTAND * (1.0 if links_frei else -1.0) * n
    if (not links_frei) != material_links:
        q = q[::-1]
    segmente = _gefasst(q, geschlossen, BOGEN)
    if not segmente:
        return None
    proben = kb._abtasten(segmente, schritt, geschlossen)
    return rb._Ring(segmente, proben, geschlossen, genau=True, grenze=True)


def ring_glatt(punkte, geschlossen, material_links, feld, werte, schritt, toleranz=GLATT):
    """Ein Ring aus einer Höhenlinie von Grenze.abstand: gerichtet wie
    raeumen_bahn._ring_aus_linie, aber in Geraden und Bögen gefasst (höchstens `toleranz`
    daneben) statt auf GLAETTEN · Raster vereinfacht – die Linie hat keine Zacken mehr, die das
    Vereinfachen wegnehmen müsste, und aus dem Kreis um eine Kuppel wird kein Vieleck."""
    roh = rb._ring_aus_linie(punkte, geschlossen, material_links, feld, 0.0, werte, schritt, 1e-9)
    if roh is None:
        return None
    p = [s.von for s in roh.segmente]
    if not geschlossen:
        p.append(roh.segmente[-1].nach)
    segmente = _gefasst(np.array(p), geschlossen, toleranz)
    if not segmente:
        return None
    return rb._Ring(segmente, kb._abtasten(segmente, schritt, geschlossen), geschlossen)


def _laengs(xs, saat):
    """(n, m) mm²: je Knoten k der Linie (Stellen `xs`) das Quadrat seines Abstands zum nächsten
    Punkt auf derselben Linie – `saat` (n − 1, m): die Stelle des Punkts zwischen den Knoten k
    und k + 1, NaN ohne; inf, wo die Linie keinen hat."""
    n, m = len(xs), saat.shape[1]
    ohne = np.isnan(saat)
    links = np.full((n, m), -np.inf)
    links[1:] = np.maximum.accumulate(np.where(ohne, -np.inf, saat), axis=0)
    rechts = np.full((n, m), np.inf)
    rechts[:-1] = np.minimum.accumulate(np.where(ohne, np.inf, saat)[::-1], axis=0)[::-1]
    d = np.minimum(xs[:, None] - links, rechts - xs[:, None])
    return d * d


def _quer(g, ys):
    """(n, m) mm²: je Knoten das Kleinste über die Linien j von g[i, j] + (ys[j'] − ys[j])² – wie
    raeumen_bahn._Feld.abstand_zu, nach Achsen getrennt."""
    n, m = g.shape
    dy2 = (ys[:, None] - ys[None, :]) ** 2
    aus = np.empty((n, m))
    block = max(1, 2_000_000 // max(m * m, 1))
    for a in range(0, n, block):
        aus[a : a + block] = (g[a : a + block, None, :] + dy2[None, :, :]).min(axis=2)
    return aus


def _abstand(feld, erlaubt, quer, i0, j0, wo):
    """(nx, ny) mm: der Abstand jedes Knotens zum nächsten Punkt der Grenze, im Gesperrten
    negativ. Die Punkte liegen auf Kanten des Rasters – `quer`: zwischen (i0, j0) und
    (i0 + 1, j0) an der Stelle x = `wo`, sonst zwischen (i0, j0) und (i0, j0 + 1) an y = `wo`.
    Darum geht es nach Achsen getrennt wie bisher zu den Randzellen: je Linie der Abstand längs,
    dann das Kleinste über die Linien quer – einmal für die Punkte auf Zeilen, einmal für die auf
    Spalten. Zwischen zwei Punkten (höchstens 0,71 Zellen auseinander) ist der Abstand zur Linie
    kleiner als zum nächsten Punkt: 1 mm vor der Grenze um 0,016 mm, 0,5 mm davor um 0,03."""
    xs, ys = np.asarray(feld.xs, dtype=float), np.asarray(feld.ys, dtype=float)
    auf_x = np.full((feld.nx - 1, feld.ny), np.nan)
    auf_x[i0[quer], j0[quer]] = wo[quer]
    auf_y = np.full((feld.ny - 1, feld.nx), np.nan)
    auf_y[j0[~quer], i0[~quer]] = wo[~quer]
    d2 = np.minimum(_quer(_laengs(xs, auf_x), ys), _quer(_laengs(ys, auf_y), xs).T)
    d = np.sqrt(d2)
    return np.where(erlaubt, d, -d)
