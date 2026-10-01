# SPDX-License-Identifier: LGPL-2.1-or-later
"""2,5D, die Bahn „Räumen mit Versätzen“ (W-006 S3f): eine ebene Fläche nach oben – die
Oberseite eines Teils oder der Boden einer Tasche – wird mit Ringen geräumt, bei vollem ap und
schmalem ae, ohne Wenden, wie ein HSM-Weg (Manuel, 2026-10-01: „von außen kreisend zur Mitte,
immer volle Tiefe, mit ae Zustellung“).

- Die Ringe liegen auf einem Raster (hoehenfeld.je_zeile, wie bei der Kontur): dort, wo die
  Hüllfläche des Teils ohne die Fläche – mit dem Fräser um das Aufmaß vergrößert – nicht höher
  liegt als die Lage, darf die Spitze hin. Was höher steht (Inseln wie ein Zapfen, die Wände
  einer Tasche, Absätze), ist für den Fräser gesperrt; der Abstand D jeder Stelle zum
  Gesperrten ist das Feld, dessen Höhenlinien die Ringe sind (Marching Squares).
- **Offene Fläche** (die Oberseite): Variante „rohteil“ – Ringe vom Rand des Rohteils her nach
  innen, der erste außen in der Luft (Mitte R − ae außerhalb), dann je ae weiter hinein; wo
  eine Insel sie unterbricht, Läufe; zuletzt um jede Insel die Ringe des Feldes D von außen
  nach innen, so viele, wie dort noch etwas steht. Variante „inseln“ – nur die Ringe des
  Feldes D, von weit außen (am Rand des Rohteils) nach innen bis an die Inseln. Beide werden
  gerechnet, die schnellere zählt (Grundsatz 0).
- **Tasche** (eine geschlossene Kontur um die Fläche, die freie Seite innen): die Ringe des
  Feldes D von innen (der Mitte) nach außen bis an die Wände, mit Aufmaß; hinein über die
  Rampe auf dem innersten Ring, nur einmal je Lage. Die Lagen beginnen an der Oberkante der
  Wände, nicht am Rohteil darüber.
- Gleichlauf: das Material rechts der Fahrtrichtung (Spindel rechtsdrehend, M3 – wie G41);
  Gegenlauf wählbar (Grundsatz 4).
- Eintauchen nur, wo schon frei ist: Ein Raster merkt sich je Lage, wo der Fräser war; das
  tangentiale Ein- und Ausfahren (kontur_bahn._anfahrt) darf nur durch Freies oder Luft. Passt
  nichts, geht es über die Rampe längs des Laufs (vierachs_bahn._rampe). Aufeinanderfolgende
  Ringe hängen aneinander, wenn der Weg dazwischen frei ist (die Spirale); sonst Eilgang knapp
  über dem Rohteil.
- Die Zeit je Variante mit bahn.zeit (Vorschub, Eilgang, Beschleunigung, Ecken).

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field

import numpy as np

from . import bahn as bn
from . import hoehenfeld as hf
from . import kontur_bahn as kb
from . import vierachs_bahn as vb
from . import vierachs_planbahn as vp
from .sprache import tr

SCHRITT = 0.5  # mm – das Raster und der Abstand der Stellen auf den Ringen
VORSCHAU_SCHRITT = 1.0  # mm – für die Vorschau im Assistenten
AUSTRITT_ANTEIL = 0.5  # vom Vorschub: so langsam beim Austritt aus dem Rohteil
VARIANTEN = ("rohteil", "morph", "inseln")
# Der Morph nimmt an seiner breitesten Stelle so viel Eingriff wie ein gerader Schnitt mit
# ae mal diesem Faktor – nicht mehr (Manuels ae ist die Grenze); anderswo weniger.
MORPH_EINGRIFF = 1.0
MORPH_SCHRITTE = 18  # Halbierungen bei der Suche nach dem nächsten Ring
# Ist der Abstand vom ersten Ring zur Insel ringsum so ungleich (kleinster ÷ größter), lohnt der
# Morph nicht: Wo der Spalt schmal ist, lägen die Ringe viel zu eng (die Platte mit dem Zapfen
# außerhalb der Mitte: 66 statt 33 min). Dann wird er gar nicht gerechnet.
MORPH_VERHAELTNIS = 0.4


class _KeinMorph(Exception):
    """Der Morph passt nicht zu dieser Fläche – die Variante entfällt."""


GLEICH = vb.GLEICH
_WINZIG = 1e-9


@dataclass(frozen=True)
class Raeumwerte:
    """Was das Räumen braucht; Längen in mm, z nach oben im Job."""

    form: object  # fraeserform.Form des Fräsers – mit ebener Stirn
    zustellung: float  # ap: höchstens so tief je Lage
    zeilenabstand: float  # ae: so weit rücken die Ringe – höchstens der Radius
    aufmass: float  # bleibt an Wänden und Inseln stehen
    oben: float  # z, wo die Lagen beginnen (das Rohteil)
    sicher: float  # z für den Eilgang über allem
    rohteil: tuple  # (x_von, x_bis, y_von, y_bis) des Rohteils von oben
    aufmass_boden: float = 0.0  # bleibt auf der Fläche stehen (0: fertig)
    gleichlauf: bool = True  # das Material rechts der Fahrtrichtung; sonst links (Gegenlauf)
    variante: str = None  # „rohteil“ oder „inseln“; None: beide rechnen, die schnellere
    einfahrradius: float = None  # der Viertelkreis hinein und heraus; None: der Vorschlag
    schneidenlaenge: float = 0.0  # 0: unbekannt – sonst höchstens so tief je Lage
    sicherheit: float = vb.SICHERHEIT  # so weit über dem Material endet der Eilgang hinab
    eintauchwinkel: float = vb.EINTAUCHWINKEL  # Grad, für die Rampe ins Material
    austritt: float = AUSTRITT_ANTEIL
    vorschub: float = 0.0  # mm/min – für die Zeit; 0: 1000
    eintauchen: float = 0.0  # mm/min senkrecht; 0: wie der Vorschub


@dataclass
class Raeumbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    flaechen: int  # so viele Flächen geräumt
    lagen: int  # Lagen, über alle Flächen
    ringe: int  # Ringe, über alle Flächen und Lagen
    laeufe: int  # Läufe (ein Ring kann in mehreren Läufen gefahren werden)
    z_min: float  # die tiefste Spitze (mm)
    laenge: float  # mm im Vorschub
    zeit: float  # Minuten (bahn.zeit)
    variante: str  # die gerechnete Variante („rohteil“, „inseln“)
    zeiten: dict = field(default_factory=dict)  # Minuten je gerechneter Variante
    rampen: int = 0  # Läufe über die Rampe ins Material
    einfahrten: int = 0  # Läufe, die im Freien eintauchten und tangential oder quer hineinfuhren
    anschluesse: int = 0  # Läufe, die an den vorigen anschlossen (die Spirale)
    rampen_bei: list = field(default_factory=list)  # je Rampe: (Ring, Zahl der Stellen)
    nachgeholt: int = 0  # Anfangsstücke, die nach den Ringen um die Insel nachkamen


# --- Das Raster: Hüllfläche, Rohteil, Freies ---------------------------------------------------


class _Feld:
    """Das Raster über dem Bereich: die Hüllfläche (so tief darf die Spitze), ob der Fräser das
    Rohteil berührt, und – je Lage – wo er schon war (`frei`)."""

    def __init__(self, netz, geformt, zugabe, r, x0, x1, y0, y1, schritt, rohteil, rand_eng):
        self.schritt = float(schritt)
        self.zugabe = zugabe
        self.r = r
        self.x0 = x0 - schritt
        self.y0 = y0 - schritt
        self.nx = max(3, int(math.ceil((x1 - self.x0) / schritt)) + 2)
        self.ny = max(3, int(math.ceil((y1 - self.y0) / schritt)) + 2)
        self.xs = self.x0 + schritt * np.arange(self.nx)
        self.ys = self.y0 + schritt * np.arange(self.ny)
        if len(netz.dreiecke):
            self.roh = hf.je_zeile(netz, geformt, self.ys, self.x0, schritt, self.nx, True)
        else:
            self.roh = np.full((self.nx, self.ny), hf.KEIN_TREFFER)
        gx, gy = np.meshgrid(self.xs, self.ys, indexing="ij")
        self.tiefe = _rohteil_tiefe(gx, gy, rohteil)  # so tief liegt die Zelle im Rohteil
        self.beruehrt = kb._im_rohteil(gx, gy, rohteil, r)  # die Stirn trifft das Rohteil
        # Die Mitte höchstens `rand_eng` außerhalb des Rohteils – für die Ringe des Feldes, die
        # sonst bis R in die Luft schnitten.
        self.eng = kb._im_rohteil(gx, gy, rohteil, rand_eng)
        self.frei = np.zeros((self.nx, self.ny), dtype=bool)
        x0r, x1r, y0r, y1r = rohteil
        self.rohteil_zellen = (gx >= x0r) & (gx <= x1r) & (gy >= y0r) & (gy <= y1r)
        m = int(math.ceil((r - 0.01) / schritt))
        dx = np.arange(-m, m + 1)[:, None] * schritt
        dy = np.arange(-m, m + 1)[None, :] * schritt
        self._stempel = (dx * dx + dy * dy) <= (r - 0.01) ** 2
        self._m = m
        self._kern = None  # die Scheibe im Frequenzraum, für eingriff()

    def zellen(self, x, y):
        """(i, j) der Zellen, in denen (x, y) liegen – auf das Raster begrenzt."""
        i = np.clip(np.rint((np.asarray(x, dtype=float) - self.x0) / self.schritt), 0, self.nx - 1)
        j = np.clip(np.rint((np.asarray(y, dtype=float) - self.y0) / self.schritt), 0, self.ny - 1)
        return i.astype(int), j.astype(int)

    def im_raster(self, x, y):
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        return (x >= self.xs[0]) & (x <= self.xs[-1]) & (y >= self.ys[0]) & (y <= self.ys[-1])

    def erlaubt_feld(self, lage, ziel):
        """(nx, ny): darf die Spitze auf der Lage in die Zelle? Nicht, wo die Hüllfläche höher
        liegt – es sei denn, nichts steht höher als das Ziel (die Fläche selbst)."""
        return (self.roh + self.zugabe <= lage + GLEICH) | (self.roh <= ziel + GLEICH)

    def bei(self, feld, x, y):
        """Der Wert des Feldes an (x, y) – der strengste der vier Nachbarn bei Wahrheitswerten
        (alle müssen), sonst der nächste Knoten."""
        fx = (np.asarray(x, dtype=float) - self.x0) / self.schritt
        fy = (np.asarray(y, dtype=float) - self.y0) / self.schritt
        i0 = np.clip(np.floor(fx).astype(int), 0, self.nx - 1)
        j0 = np.clip(np.floor(fy).astype(int), 0, self.ny - 1)
        i1 = np.minimum(i0 + 1, self.nx - 1)
        j1 = np.minimum(j0 + 1, self.ny - 1)
        if feld.dtype == bool:
            return feld[i0, j0] & feld[i1, j0] & feld[i0, j1] & feld[i1, j1]
        return feld[
            np.clip(np.rint(fx).astype(int), 0, self.nx - 1),
            np.clip(np.rint(fy).astype(int), 0, self.ny - 1),
        ]

    def ungeschnitten(self, x, y):
        """Je Stelle der Anteil der Stirn, unter dem noch ungeschnittenes Rohteil liegt (0 … 1)."""
        i, j = self.zellen(x, y)
        m = self._m
        roh = self.rohteil_zellen & ~self.frei
        zahl = float(self._stempel.sum())
        ergebnis = np.zeros(len(i))
        for k, (ci, cj) in enumerate(zip(i, j, strict=True)):
            i0, j0 = ci - m, cj - m
            a0, b0 = max(i0, 0), max(j0, 0)
            a1, b1 = min(i0 + 2 * m + 1, self.nx), min(j0 + 2 * m + 1, self.ny)
            if a1 <= a0 or b1 <= b0:
                continue
            fenster = roh[a0:a1, b0:b1] & self._stempel[a0 - i0 : a1 - i0, b0 - j0 : b1 - j0]
            ergebnis[k] = fenster.sum() / zahl
        return ergebnis

    def eingriff(self):
        """(nx, ny): je Zelle der Anteil der Stirn über ungeschnittenem Rohteil, wenn die Mitte
        dort steht – wie ungeschnitten(), für alle Zellen auf einmal (Faltung mit der Scheibe
        über die FFT)."""
        m = self._m
        groesse = (self.nx + 2 * m + 1, self.ny + 2 * m + 1)
        if self._kern is None:
            kern = np.zeros(groesse)
            kern[: 2 * m + 1, : 2 * m + 1] = self._stempel
            self._kern = np.fft.rfft2(kern)
        roh = np.zeros(groesse)
        roh[: self.nx, : self.ny] = self.rohteil_zellen & ~self.frei
        gefaltet = np.fft.irfft2(np.fft.rfft2(roh) * self._kern, s=groesse)
        return gefaltet[m : m + self.nx, m : m + self.ny] / float(self._stempel.sum())

    def frei_bei(self, x, y):
        """Ist (x, y) frei: der Fräser war schon da – oder er trifft dort kein Rohteil?"""
        i, j = self.zellen(x, y)
        return self.frei[i, j] | ~self.beruehrt[i, j]

    def merke(self, x, y):
        """Der Fräser ist über (x, y) gefahren: die Zellen unter seiner Stirn sind frei."""
        i, j = self.zellen(x, y)
        m = self._m
        for ci, cj in zip(i, j, strict=True):
            i0, j0 = ci - m, cj - m
            a0, b0 = max(i0, 0), max(j0, 0)
            a1, b1 = min(i0 + 2 * m + 1, self.nx), min(j0 + 2 * m + 1, self.ny)
            if a1 <= a0 or b1 <= b0:
                continue
            self.frei[a0:a1, b0:b1] |= self._stempel[a0 - i0 : a1 - i0, b0 - j0 : b1 - j0]

    def abstand_zu(self, gesperrt):
        """(nx, ny) mm: der Abstand jeder Zelle zum Rand des Gesperrten (`gesperrt`: bool), im
        Gesperrten selbst negativ; +inf, wenn nichts gesperrt ist."""
        if not gesperrt.any():
            return np.full((self.nx, self.ny), np.inf)
        # Der Rand des Gesperrten: gesperrte Zellen mit einem freien Nachbarn (der Rand des
        # Rasters zählt nicht als frei).
        innen = np.ones_like(gesperrt)
        innen[1:, :] &= gesperrt[:-1, :]
        innen[:-1, :] &= gesperrt[1:, :]
        innen[:, 1:] &= gesperrt[:, :-1]
        innen[:, :-1] &= gesperrt[:, 1:]
        rand = gesperrt & ~innen
        ri, rj = np.nonzero(rand)
        if not len(ri):
            ri, rj = np.nonzero(gesperrt)
        rx = self.xs[ri]
        ry = self.ys[rj]
        gx, gy = np.meshgrid(self.xs, self.ys, indexing="ij")
        px, py = gx.ravel(), gy.ravel()
        abstand = np.empty(len(px))
        block = max(1, 2_000_000 // max(len(rx), 1))
        for a in range(0, len(px), block):
            dx = px[a : a + block, None] - rx[None, :]
            dy = py[a : a + block, None] - ry[None, :]
            abstand[a : a + block] = np.sqrt((dx * dx + dy * dy).min(axis=1))
        abstand = abstand.reshape(self.nx, self.ny)
        return np.where(gesperrt, -abstand - self.schritt, abstand)


# --- Höhenlinien (Marching Squares) ------------------------------------------------------------

# Je Fall (Bits: unten links 1, unten rechts 2, oben rechts 4, oben links 8 – über dem Niveau)
# die Kanten, die eine Linie verbindet: 0 unten, 1 rechts, 2 oben, 3 links.
_FAELLE = {
    1: [(3, 0)],
    2: [(0, 1)],
    3: [(3, 1)],
    4: [(1, 2)],
    6: [(0, 2)],
    7: [(3, 2)],
    8: [(2, 3)],
    9: [(0, 2)],
    11: [(1, 2)],
    12: [(1, 3)],
    13: [(0, 1)],
    14: [(3, 0)],
}


def _hoehenlinien(feld, xs, ys, niveau):
    """[(punkte (m, 2), geschlossen)] – die Linien, auf denen `feld` (nx, ny) das Niveau hat;
    Marching Squares mit Interpolation auf den Zellkanten."""
    f = np.where(np.isfinite(feld), feld, np.where(feld > 0, 1e9, -1e9))
    ueber = f > niveau
    c0 = ueber[:-1, :-1]
    c1 = ueber[1:, :-1]
    c2 = ueber[1:, 1:]
    c3 = ueber[:-1, 1:]
    fall = c0 * 1 + c1 * 2 + c2 * 4 + c3 * 8
    ii, jj = np.nonzero((fall > 0) & (fall < 15))
    if not len(ii):
        return []
    faelle = fall[ii, jj]
    f00, f10, f11, f01 = f[ii, jj], f[ii + 1, jj], f[ii + 1, jj + 1], f[ii, jj + 1]

    def anteil(a, b):
        d = b - a
        return np.where(
            np.abs(d) > _WINZIG,
            np.clip((niveau - a) / np.where(np.abs(d) > _WINZIG, d, 1.0), 0.0, 1.0),
            0.5,
        )

    sx = xs[1] - xs[0]
    sy = ys[1] - ys[0]
    # Die Schnittpunkte auf den vier Kanten jeder Zelle: unten, rechts, oben, links.
    kante_x = [xs[ii] + sx * anteil(f00, f10), xs[ii + 1], xs[ii] + sx * anteil(f01, f11), xs[ii]]
    kante_y = [ys[jj], ys[jj] + sy * anteil(f10, f11), ys[jj + 1], ys[jj] + sy * anteil(f00, f01)]
    # Die Kennung jeder Kante (gemeinsam für Nachbarzellen): waagerecht (0, i, j), senkrecht (1, i, j).
    kennung = [
        (0, ii, jj),  # unten
        (1, ii + 1, jj),  # rechts
        (0, ii, jj + 1),  # oben
        (1, ii, jj),  # links
    ]
    mitte = (f00 + f10 + f11 + f01) / 4 > niveau
    segmente = []  # (kennung_a, kennung_b, (xa, ya), (xb, yb))
    for nummer in range(len(ii)):
        fall_n = int(faelle[nummer])
        if fall_n == 5:
            paare = [(3, 2), (0, 1)] if mitte[nummer] else [(3, 0), (1, 2)]
        elif fall_n == 10:
            paare = [(0, 1), (2, 3)] if mitte[nummer] else [(0, 3), (1, 2)]
        else:
            paare = _FAELLE[fall_n]
        for a, b in paare:
            ka = (kennung[a][0], int(kennung[a][1][nummer]), int(kennung[a][2][nummer]))
            kb_ = (kennung[b][0], int(kennung[b][1][nummer]), int(kennung[b][2][nummer]))
            segmente.append(
                (
                    ka,
                    kb_,
                    (float(kante_x[a][nummer]), float(kante_y[a][nummer])),
                    (float(kante_x[b][nummer]), float(kante_y[b][nummer])),
                )
            )
    return _verketten(segmente)


def _verketten(segmente):
    """Segmente (Kante, Kante, Punkt, Punkt) zu Linienzügen – geschlossen, wo der Zug zu seiner
    ersten Kante zurückkommt."""
    an_kante = {}
    for nummer, (ka, kb_, _pa, _pb) in enumerate(segmente):
        an_kante.setdefault(ka, []).append(nummer)
        an_kante.setdefault(kb_, []).append(nummer)
    benutzt = [False] * len(segmente)
    ergebnis = []
    for start in range(len(segmente)):
        if benutzt[start]:
            continue
        benutzt[start] = True
        ka, kb_, pa, pb = segmente[start]
        kette = [pa, pb]
        geschlossen = False
        # vorwärts ab kb_, dann rückwärts ab ka
        for richtung in (1, -1):
            kante = kb_ if richtung == 1 else ka
            while True:
                naechste = [n for n in an_kante.get(kante, ()) if not benutzt[n]]
                if not naechste:
                    break
                n = naechste[0]
                benutzt[n] = True
                na, nb, qa, qb = segmente[n]
                if na == kante:
                    punkt, kante = qb, nb
                else:
                    punkt, kante = qa, na
                if richtung == 1:
                    kette.append(punkt)
                else:
                    kette.insert(0, punkt)
                if kante == (ka if richtung == 1 else kb_):
                    geschlossen = True
                    break
            if geschlossen:
                break
        punkte = np.array(kette, dtype=float)
        if geschlossen and len(punkte) > 1 and np.hypot(*(punkte[0] - punkte[-1])) <= _WINZIG:
            punkte = punkte[:-1]
        ergebnis.append((punkte, geschlossen))
    return ergebnis


def _vereinfacht(punkte, toleranz, geschlossen):
    """Douglas–Peucker: so wenige Ecken, dass der Linienzug höchstens `toleranz` abweicht."""
    if len(punkte) < 3:
        return punkte
    if geschlossen:
        # Zwei Hälften, damit das Ende nicht mit dem Anfang verschmilzt.
        h = len(punkte) // 2
        a = _vereinfacht(punkte[: h + 1], toleranz, False)
        b = _vereinfacht(np.vstack([punkte[h:], punkte[:1]]), toleranz, False)
        return np.vstack([a[:-1], b[:-1]])
    behalten = np.zeros(len(punkte), dtype=bool)
    behalten[0] = behalten[-1] = True
    stapel = [(0, len(punkte) - 1)]
    while stapel:
        i, j = stapel.pop()
        if j <= i + 1:
            continue
        p, q = punkte[i], punkte[j]
        d = q - p
        laenge = math.hypot(d[0], d[1])
        zwischen = punkte[i + 1 : j]
        if laenge <= _WINZIG:
            abstand = np.hypot(zwischen[:, 0] - p[0], zwischen[:, 1] - p[1])
        else:
            abstand = (
                np.abs((zwischen[:, 0] - p[0]) * d[1] - (zwischen[:, 1] - p[1]) * d[0]) / laenge
            )
        k = int(np.argmax(abstand))
        if abstand[k] > toleranz:
            behalten[i + 1 + k] = True
            stapel.append((i, i + 1 + k))
            stapel.append((i + 1 + k, j))
    return punkte[behalten]


def _segmente_aus(punkte, geschlossen):
    """[_Strecke] aus einem Linienzug."""
    ergebnis = []
    n = len(punkte)
    for i in range(n if geschlossen else n - 1):
        p, q = punkte[i], punkte[(i + 1) % n]
        if math.hypot(q[0] - p[0], q[1] - p[1]) > _WINZIG:
            ergebnis.append(kb._Strecke((float(p[0]), float(p[1])), (float(q[0]), float(q[1]))))
    return ergebnis


def _umlauf(punkte):
    """Die Fläche des Umlaufs: > 0 gegen den Uhrzeigersinn."""
    x, y = punkte[:, 0], punkte[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


# --- Die Ringe ------------------------------------------------------------------------------------


@dataclass
class _Ring:
    """Ein Ring: seine Segmente und Proben (kontur_bahn), ob geschlossen; `genau`: aus der
    Geometrie gerechnet (der Versatz einer Insel) – das Raster prüft ihn nicht nach."""

    segmente: list
    proben: object
    geschlossen: bool
    genau: bool = False


def _ring_aus_linie(
    punkte, geschlossen, material_links, feld, niveau, werte, schritt, toleranz, material_hoch=False
):
    """Ein Ring aus einer Höhenlinie des Feldes `werte`: vereinfacht, so gerichtet, dass das
    Material links liegt – oder rechts (Gegenlauf). Das Material liegt, wo das Feld kleiner ist
    (D: näher am Gesperrten) oder, mit `material_hoch`, wo es größer ist (F: tiefer im Rest)."""
    punkte = _vereinfacht(punkte, toleranz, geschlossen)
    if len(punkte) < 2:
        return None
    # Liegt das Material links? Neben der Mitte der längsten Stücke nachsehen – an einer Ecke
    # oder in einer Kerbe trifft die Probe sonst beidseits denselben Knoten.
    n = len(punkte)
    stuecke = range(n if geschlossen else n - 1)
    laengen = [math.hypot(*(punkte[(i + 1) % n] - punkte[i])) for i in stuecke]
    material_ist_links = not material_hoch
    for i in sorted(stuecke, key=lambda k: -laengen[k]):
        p, q = punkte[i], punkte[(i + 1) % n]
        tx, ty = q[0] - p[0], q[1] - p[1]
        laenge = math.hypot(tx, ty) or 1.0
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        weit = 1.5 * schritt
        links = (mx - ty / laenge * weit, my + tx / laenge * weit)
        rechts = (mx + ty / laenge * weit, my - tx / laenge * weit)
        d_links = float(feld.bei(werte, [links[0]], [links[1]])[0])
        d_rechts = float(feld.bei(werte, [rechts[0]], [rechts[1]])[0])
        if abs(d_links - d_rechts) > _WINZIG:
            material_ist_links = (d_links > d_rechts) if material_hoch else (d_links < d_rechts)
            break
    if material_ist_links != material_links:
        punkte = punkte[::-1].copy()
    segmente = _segmente_aus(punkte, geschlossen)
    if not segmente:
        return None
    return _Ring(segmente, kb._abtasten(segmente, schritt, geschlossen), geschlossen)


def _rohteil_tiefe(gx, gy, rohteil):
    """Je Zelle, wie tief sie im Rohteil liegt (mm): drinnen der Abstand zum nächsten Rand,
    draußen der Abstand zum Rohteil, negativ – die Höhenlinien sind die Ringe von
    _rohteil_ring (draußen mit runden Ecken)."""
    x0, x1, y0, y1 = rohteil
    innen = np.minimum(np.minimum(gx - x0, x1 - gx), np.minimum(gy - y0, y1 - gy))
    dx = np.maximum(np.maximum(x0 - gx, 0.0), gx - x1)
    dy = np.maximum(np.maximum(y0 - gy, 0.0), gy - y1)
    return np.where(innen >= 0, innen, -np.hypot(dx, dy))


def _rohteil_ring(rohteil, tiefe, material_links, schritt):
    """Der Ring um das Rohteil, um `tiefe` nach innen gerückt (negativ: außerhalb, die Ecken
    rund mit dem Radius −tiefe); None, wenn er nicht mehr hineinpasst. Gegen den Uhrzeigersinn
    (Material innen = links), sonst umgekehrt."""
    x0, x1, y0, y1 = rohteil
    a0, a1, b0, b1 = x0 + tiefe, x1 - tiefe, y0 + tiefe, y1 - tiefe
    if a1 - a0 <= GLEICH or b1 - b0 <= GLEICH:
        return None
    if tiefe >= 0:
        ecken = [(a0, b0), (a1, b0), (a1, b1), (a0, b1)]
        segmente = [kb._Strecke(ecken[i], ecken[(i + 1) % 4]) for i in range(4)]
    else:
        r = -tiefe
        segmente = [
            kb._Strecke((a0 + r, b0), (a1 - r, b0)),
            kb._Bogen((a1 - r, b0), (a1, b0 + r), (a1 - r, b0 + r), False),
            kb._Strecke((a1, b0 + r), (a1, b1 - r)),
            kb._Bogen((a1, b1 - r), (a1 - r, b1), (a1 - r, b1 - r), False),
            kb._Strecke((a1 - r, b1), (a0 + r, b1)),
            kb._Bogen((a0 + r, b1), (a0, b1 - r), (a0 + r, b1 - r), False),
            kb._Strecke((a0, b1 - r), (a0, b0 + r)),
            kb._Bogen((a0, b0 + r), (a0 + r, b0), (a0 + r, b0 + r), False),
        ]
        segmente = [s for s in segmente if s.laenge > GLEICH]
    if not material_links:
        segmente = [s.umgekehrt() for s in reversed(segmente)]
    return _Ring(segmente, kb._abtasten(segmente, schritt, True), True)


# --- Der Ablauf je Lage -----------------------------------------------------------------------------


@dataclass
class _Stand:
    punkte: list = field(default_factory=list)
    flaechen: int = 0
    lagen: int = 0
    ringe: int = 0
    laeufe: int = 0
    rampen: int = 0  # Läufe, die über die Rampe ins Material gingen
    einfahrten: int = 0  # Läufe, die im Freien eintauchten und tangential hineinfuhren
    seitlich: int = 0  # Läufe, die im Freien eintauchten und quer in die Bahn fuhren
    anschluesse: int = 0  # Läufe, die an den vorigen anschlossen (die Spirale)
    rampen_bei: list = field(default_factory=list)  # je Rampe: (Ring, Zahl der Stellen)
    nachgeholt: int = 0  # Anfangsstücke, die nach den Ringen um die Insel nachkamen
    geraeumt: list = field(default_factory=list)  # (z, x_von, x_bis, y_von, y_bis) je Fläche
    z_min: float = math.inf
    laenge: float = 0.0


class _Lage:
    """Eine Lage: fährt Ringe als Läufe, merkt sich Freies, hängt Läufe aneinander."""

    def __init__(self, st, feld, w, r, r_ein, gerade, lage, vorige, erlaubt, schritt, oben=None):
        self.st = st
        self.feld = feld
        self.w = w
        self.r = r
        self.r_ein = r_ein
        self.gerade = gerade
        self.lage = lage
        self.vorige = vorige
        self.erlaubt = erlaubt
        self.schritt = schritt
        # Wo das Material über der Fläche beginnt (in der Tasche ihre Oberkante) – und die Decke:
        # die Oberkante des Rohteils. Über der ersten Lage einer Tasche darf der Eilgang nur bis
        # über die Decke hinab, denn ob jemand das Rohteil darüber schon weggefräst hat, weiß die
        # Bahn nicht (der Prüfstand fand 2034 mm³ im Eilgang, P-2026-10-01-26).
        self.oben = w.oben if oben is None else oben
        self.decke = w.oben
        self.unten = False  # die Spitze steht auf der Lage (am Ende des letzten Laufs)
        self.ort = None  # (x, y) der Spitze dort
        self.knapp = min(w.sicher, w.oben + w.sicherheit)  # Eilgang über dem Rohteil
        # So viel der Stirn darf beim Ein- und Ausfahren über ungeschnittenem Rohteil liegen:
        # anderthalbmal der Streifen ae, den jeder Ring ohnehin nimmt (Kreisabschnitt).
        h = min(w.zeilenabstand, r)
        abschnitt = r * r * math.acos((r - h) / r) - (r - h) * math.sqrt(2 * r * h - h * h)
        self.schwelle = 1.5 * abschnitt / (math.pi * r * r) + 0.02
        self.reste = []  # [(Ring, Stellen)]: Anfangsstücke, die nach den Ringen nachkommen
        self.verschieben = True
        self.gedreht = False  # gerade ein ganzer Ring, der anderswo anfängt (_eingang_irgendwo)
        # Die freie Seite der Bahn: links im Gleichlauf (das Material rechts), sonst rechts –
        # dorthin gehen das Einfahren und der Weg quer hinein.
        self.frei_rechts = not w.gleichlauf

    def frei(self, qx, qy):
        """Darf das Ein- und Ausfahren dorthin: im Raster, erlaubt, und unter der Stirn höchstens
        so viel ungeschnittenes Rohteil wie im Streifen ae – bis auf den letzten Punkt, der
        liegt auf der Bahn?"""
        qx, qy = np.asarray(qx, dtype=float), np.asarray(qy, dtype=float)
        if not self.feld.im_raster(qx, qy).all():
            return False
        if not self.feld.bei(self.erlaubt, qx, qy).all():
            return False
        if len(qx) < 2:
            return True
        return bool((self.feld.ungeschnitten(qx[:-1], qy[:-1]) <= self.schwelle).all())

    def ring(self, ring, eng=False, kennung="", nur=None, luft=False):
        """Fährt einen Ring – in Läufen, wo erlaubt und Rohteil ist (`eng`: die Mitte höchstens
        ae außerhalb des Rohteils, sonst bis R; `nur`: je Probe, ob sie überhaupt gefahren
        werden soll; `luft`: auch, wo der Fräser kein Rohteil trifft – ein Ring des Morphs
        bleibt ganz, statt an einer Ecke in der Luft in Läufe zu zerfallen). Gibt die Zahl der
        Läufe."""
        self.kennung = kennung
        proben = ring.proben
        x, y = proben.x, proben.y
        n = len(x)
        if n < 2:
            return 0
        im_rohteil = self.feld.eng if eng else self.feld.beruehrt
        drin = self.feld.im_raster(x, y)
        if not ring.genau:
            drin &= self.feld.bei(self.erlaubt, x, y)
        if not luft:
            drin &= im_rohteil[self.feld.zellen(x, y)]
        if nur is not None:
            drin &= nur
        if not drin.any():
            return 0
        laeufe = []  # [(Stellen, Austritt hinten)]
        if ring.geschlossen and drin.all():
            start = self._start(x, y)
            laeufe.append((np.arange(start, start + n + 1) % n, False))
        elif ring.geschlossen:
            luecke = int(np.flatnonzero(~drin)[0])
            for von, bis in vb._stuecke(np.roll(drin, -luecke)):
                naechste = (bis + 1 + luecke) % n
                laeufe.append(
                    (
                        (np.arange(von, bis + 1) + luecke) % n,
                        bool(not im_rohteil[self.feld.zellen(x[naechste], y[naechste])]),
                    )
                )
        else:
            for von, bis in vb._stuecke(drin):
                hinten = bis + 1 < n and bool(
                    not im_rohteil[self.feld.zellen(x[bis + 1], y[bis + 1])]
                )
                laeufe.append((np.arange(von, bis + 1), hinten))
        laeufe = [lauf for lauf in laeufe if len(lauf[0]) >= 2]
        if not laeufe:
            return 0
        # Der nächste Lauf: der, dessen Anfang der Spitze am nächsten liegt.
        while laeufe:
            if self.ort is None:
                naechster = 0
            else:
                naechster = min(
                    range(len(laeufe)),
                    key=lambda k: math.hypot(
                        x[laeufe[k][0][0]] - self.ort[0], y[laeufe[k][0][0]] - self.ort[1]
                    ),
                )
            stellen, hinten = laeufe.pop(naechster)
            self._lauf(ring, stellen, hinten, ring.geschlossen and len(stellen) == n + 1)
        self.st.ringe += 1
        return 1

    def _start(self, x, y):
        """Wo ein ganzer Ring beginnt: der Spitze am nächsten – sonst auf der längsten Geraden."""
        if self.ort is not None:
            return int(np.argmin(np.hypot(x - self.ort[0], y - self.ort[1])))
        return 0

    def _lauf(self, ring, stellen, hinten, ganz):
        """Ein Lauf; `ganz`: der ganze geschlossene Ring (die Stellen enden am Anfang)."""
        w, r = self.w, self.r
        proben, segmente = ring.proben, ring.segmente
        x, y = proben.x[stellen], proben.y[stellen]
        p0 = (float(x[0]), float(y[0]))
        p1 = (float(x[-1]), float(y[-1]))
        t0 = kb._einheit(float(x[1] - x[0]), float(y[1] - y[0]))
        punkte = self.st.punkte
        laenge = 0.0
        # Hängt der Lauf an den vorigen an? Kurzer Weg, und der Weg ist frei (die Spirale).
        angehaengt = False
        if self.unten and self.ort is not None:
            weg = math.hypot(p0[0] - self.ort[0], p0[1] - self.ort[1])
            if weg <= 2.0 * w.zeilenabstand + self.schritt and weg > _WINZIG:
                anzahl = max(2, int(math.ceil(weg / self.schritt)) + 1)
                qx = np.linspace(self.ort[0], p0[0], anzahl)
                qy = np.linspace(self.ort[1], p0[1], anzahl)
                if self.frei(qx, qy) or weg <= w.zeilenabstand + self.schritt:
                    punkt = bn.Punkt(False, p0[0], p0[1], self.lage)
                    laenge += bn.weg(punkte[-1], punkt)
                    punkte.append(punkt)
                    angehaengt = True
            elif weg <= _WINZIG:
                angehaengt = True
            if angehaengt:
                self.st.anschluesse += 1
        ein = (
            None
            if angehaengt
            else kb._anfahrt(p0, t0, self.r_ein, self.gerade, self.frei, True, self.frei_rechts)
        )
        seitlich = None if angehaengt or ein is not None else self._seitlich(p0, t0)
        if not angehaengt and ein is None and seitlich is None and ganz and not self.gedreht:
            # Ein ganzer Ring, an dessen Anfang kein Eingang passt: anderswo anfangen, wo einer
            # passt – der Spitze am nächsten (die Zwickel neben einer Insel, P-2026-10-01-26).
            m = self._eingang_irgendwo(proben, stellen)
            if m is not None:
                grund = np.asarray(stellen[:-1])
                gedreht = np.concatenate([np.roll(grund, -m), grund[m : m + 1]])
                self.gedreht = True
                try:
                    return self._lauf(ring, gedreht, hinten, True)
                finally:
                    self.gedreht = False
        if not angehaengt and ein is None and seitlich is None and not ganz and self.verschieben:
            # Kein Eingang am Anfang (dahinter die Insel, daneben noch Material): weiter vorn
            # suchen – das Anfangsstück kommt nach den Ringen um die Insel nach.
            m = self._eingang_voraus(proben, stellen)
            if m is not None:
                self.reste.append((ring, stellen[: m + 1]))
                self.st.nachgeholt += 1
                return self._lauf(ring, stellen[m:], hinten, False)
        if not angehaengt:
            # Senkrecht hinauf (knapp über das Rohteil), hin, hinab bis knapp über die Lage.
            start = ein.aussen if ein is not None else (seitlich if seitlich is not None else p0)
            hoch = self.knapp if self.unten else w.sicher
            if self.unten and self.ort is not None:
                punkte.append(bn.Punkt(True, self.ort[0], self.ort[1], hoch))
            punkte.append(bn.Punkt(True, start[0], start[1], hoch))
            if ein is not None:
                # Eintauchen im Freien oder in der Luft, dann tangential hinein.
                knapp = self._hinab(start, hoch)
                punkte.append(bn.Punkt(True, start[0], start[1], knapp))
                punkte.append(bn.Punkt(False, start[0], start[1], self.lage, True))
                laenge += kb._anfahrt_punkte(punkte, ein, self.lage, hinein=True)
                self.st.einfahrten += 1
            elif seitlich is not None:
                # Eintauchen im Freien neben der Bahn, dann quer hinein (hinter dem Anfang ist
                # Gesperrtes – etwa die Insel, an der der Ring abriss).
                knapp = self._hinab(start, hoch)
                punkte.append(bn.Punkt(True, start[0], start[1], knapp))
                punkte.append(bn.Punkt(False, start[0], start[1], self.lage, True))
                punkt = bn.Punkt(False, p0[0], p0[1], self.lage)
                laenge += bn.weg(punkte[-1], punkt)
                punkte.append(punkt)
                self.st.seitlich += 1
            else:
                # Im Material: über die Rampe hinab – rundum auf einem ganzen Ring (dann der
                # Ring in der Tiefe, ab dort, wo die Rampe ankam), sonst längs des Laufs hin
                # und her.
                oben_hier = self.vorige
                knapp = min(hoch, self._material_oben() + w.sicherheit)
                punkte.append(bn.Punkt(True, p0[0], p0[1], knapp))
                punkte.append(bn.Punkt(False, p0[0], p0[1], oben_hier, True))
                self.st.rampen += 1
                self.st.rampen_bei.append((getattr(self, "kennung", ""), int(len(stellen))))
                if ganz:
                    laenge += self._rampe_rundum(ring, stellen, oben_hier)
                    return self._fertig(ring, laenge, ein)
                laenge += kb._rampe(punkte, None, x, y, self.lage, oben_hier, w, self.schritt)
        laenge += kb._bahnpunkte(
            punkte, segmente, proben, stellen, self.lage, hinten, w.austritt, r
        )
        self._fertig(ring, laenge, ein, x, y, p1)

    def _hinab(self, start, hoch):
        """Bis wohin der Eilgang über `start` hinab darf: knapp über die Lage, wenn unter der
        Stirn nichts mehr steht – sonst nur knapp über das Material (ein wenig ungeschnittenes
        Rohteil darf die Stirn beim Einfahren treffen, aber im Vorschub, nicht im Eilgang; der
        Prüfstand fand 189 mm³ im Eilgang, P-2026-10-01-26)."""
        knapp = min(hoch, self.lage + self.w.sicherheit)
        if float(self.feld.ungeschnitten([start[0]], [start[1]])[0]) <= 0.0:
            return knapp
        return min(hoch, max(knapp, self._material_oben() + self.w.sicherheit))

    def _material_oben(self):
        """Bis wohin das Material über der Spitze reichen kann: die vorige Lage – über der
        ersten Lage die Decke (das Rohteil, auch wenn die Fläche in einer Tasche tiefer
        beginnt)."""
        if self.vorige < self.oben - GLEICH:
            return self.vorige
        return self.decke

    def _fertig(self, ring, laenge, ein, x=None, y=None, ende=None):
        """Nach dem Lauf: das Freie merken, wo die Spitze steht, die Zähler."""
        if x is None:
            x, y = ring.proben.x, ring.proben.y
        self.feld.merke(x, y)
        if ein is not None:
            self.feld.merke(
                [ein.aussen[0], ein.bogen_punkt[0]], [ein.aussen[1], ein.bogen_punkt[1]]
            )
        letzter = self.st.punkte[-1]
        self.unten = True
        self.ort = ende if ende is not None else (float(letzter.x), float(letzter.y))
        self.st.laenge += laenge
        self.st.laeufe += 1
        self.st.z_min = min(self.st.z_min, self.lage)

    def _eingang_voraus(self, proben, stellen):
        """Die erste Stelle (Index in `stellen`, ab 1) innerhalb von 3 R, an der ein Eingang
        passt – tangential oder quer; None, wenn keine."""
        x, y = proben.x[stellen], proben.y[stellen]
        weg = 0.0
        for m in range(1, len(stellen) - 1):
            weg += math.hypot(float(x[m] - x[m - 1]), float(y[m] - y[m - 1]))
            if weg > 3.0 * self.r:
                return None
            p = (float(x[m]), float(y[m]))
            t = kb._einheit(float(x[m + 1] - x[m]), float(y[m + 1] - y[m]))
            if (
                kb._anfahrt(p, t, self.r_ein, self.gerade, self.frei, True, self.frei_rechts)
                is not None
            ):
                return m
            if self._seitlich(p, t) is not None:
                return m
        return None

    def _eingang_irgendwo(self, proben, stellen):
        """Die Stelle (Index in `stellen`) auf einem ganzen Ring, an der ein Eingang passt –
        tangential oder quer –, der Spitze am nächsten; None, wenn nirgends."""
        grund = np.asarray(stellen[:-1])
        n = len(grund)
        if n < 3:
            return None
        x, y = proben.x[grund], proben.y[grund]
        if self.ort is None:
            reihenfolge = range(n)
        else:
            reihenfolge = np.argsort(np.hypot(x - self.ort[0], y - self.ort[1]))
        schrittweite = max(1, int(round(1.0 / self.schritt)))  # alle 1 mm nachsehen
        for m in reihenfolge:
            m = int(m)
            if m % schrittweite:
                continue
            p = (float(x[m]), float(y[m]))
            k = (m + 1) % n
            t = kb._einheit(float(x[k] - x[m]), float(y[k] - y[m]))
            if kb._anfahrt(p, t, self.r_ein, self.gerade, self.frei, True, self.frei_rechts):
                return m
            if self._seitlich(p, t) is not None:
                return m
        return None

    def reste_fahren(self):
        """Die liegen gebliebenen Anfangsstücke – jetzt ist rundum geschnitten."""
        self.verschieben = False
        reste, self.reste = self.reste, []
        for ring, stellen in reste:
            if len(stellen) >= 2:
                self._lauf(ring, stellen, False, False)

    def _seitlich(self, p0, t0):
        """Der Punkt neben dem Anfang auf der freien Seite (links im Gleichlauf, rechts im
        Gegenlauf), von dem aus der Fräser quer in die Bahn fährt: so weit wie möglich bis
        R + ae, mindestens ae, und der Weg frei."""
        rechts = (t0[1], -t0[0]) if self.frei_rechts else (-t0[1], t0[0])
        for weite in (self.r + self.w.zeilenabstand, self.r, self.r / 2, self.w.zeilenabstand):
            if weite <= _WINZIG:
                continue
            anzahl = max(2, int(math.ceil(weite / self.schritt)) + 1)
            qx = p0[0] + rechts[0] * np.linspace(weite, 0.0, anzahl)
            qy = p0[1] + rechts[1] * np.linspace(weite, 0.0, anzahl)
            if self.frei(qx, qy):
                return (float(qx[0]), float(qy[0]))
        return None

    def _rampe_rundum(self, ring, stellen, oben_hier):
        """Die Rampe rundum auf einem geschlossenen Ring: mit dem Eintauchwinkel längs des
        Rings hinab, so viele Umläufe, wie es braucht, dann der ganze Ring in der Tiefe von
        dort aus. Gibt die Länge zurück."""
        w = self.w
        proben, segmente = ring.proben, ring.segmente
        n = len(proben.x)
        folge = stellen[:-1]  # ohne den Schlusspunkt (= Anfang)
        steil = math.tan(
            math.radians(w.eintauchwinkel if w.eintauchwinkel > 0 else vb.EINTAUCHWINKEL)
        )
        punkte = self.st.punkte
        laenge = 0.0
        hoehe = oben_hier
        seit = 0.0  # Weg seit dem letzten Satz
        letzte_seg = None
        k = 0
        for _ in range(100000):
            i, j = int(folge[k % len(folge)]), int(folge[(k + 1) % len(folge)])
            weg = math.hypot(proben.x[j] - proben.x[i], proben.y[j] - proben.y[i])
            hoehe -= steil * weg
            seit += weg
            k += 1
            unten = hoehe <= self.lage + GLEICH
            seg = int(proben.segment[j])
            if unten or seg != letzte_seg or seit >= 3.0:
                punkt = bn.Punkt(
                    False, float(proben.x[j]), float(proben.y[j]), max(hoehe, self.lage)
                )
                laenge += bn.weg(punkte[-1], punkt)
                punkte.append(punkt)
                seit = 0.0
                letzte_seg = seg
            if unten:
                break
        # Der ganze Ring in der Tiefe, ab der Stelle, wo die Rampe ankam.
        start = int(folge[k % len(folge)])
        rundum = (np.arange(start, start + n + 1)) % n
        laenge += kb._bahnpunkte(
            punkte, segmente, proben, rundum, self.lage, False, w.austritt, self.r
        )
        return laenge

    def heben(self):
        """Am Ende der Lage: tangential heraus, wo es geht, und hinauf."""
        punkte = self.st.punkte
        if not self.unten or not punkte:
            return
        letzter = punkte[-1]
        punkte.append(bn.Punkt(True, letzter.x, letzter.y, self.w.sicher))
        self.unten = False
        self.ort = None


# --- planen ------------------------------------------------------------------------------------


def planen(netz, werte, ebenen, konturen=(), schritt=SCHRITT):
    """Die Bahn „Räumen“ (Raeumbahn) über die Flächen `ebenen` ([hoehenfeld.Ebene]) mit den
    Werten `werte`; `netz` ist das Teil ohne diese Flächen (hoehenfeld.netz_ohne – oder je
    Fläche das ohne die Flächen ihrer Höhe, hoehenfeld.netze_je_hoehe); `konturen`
    ([kontur_bahn.Kontur]) die Unterkanten der Wände des Teils – eine geschlossene um die
    Fläche mit der freien Seite innen macht sie zur Tasche. ValueError mit einem Satz, wenn es
    nicht geht."""
    w = werte
    form = w.form
    r = float(form.radius)
    if r <= 0 or vp.ebener_radius(form) <= 0:
        raise ValueError(tr("ra.fehler.form"))
    if w.zustellung <= 0 or w.zeilenabstand <= 0:
        raise ValueError(tr("ra.fehler.werte"))
    if w.zeilenabstand > r + GLEICH:
        raise ValueError(tr("ra.fehler.zeilenabstand"))
    if not ebenen:
        raise ValueError(tr("ra.fehler.keine_ebene"))
    varianten = (w.variante,) if w.variante in VARIANTEN else VARIANTEN
    if all(_tasche_um(e, konturen) is not None for e in ebenen):
        varianten = ("inseln",)  # nur Taschen: die haben eine Art, von innen nach außen
    ergebnisse = {}
    for variante in varianten:
        st = _Stand()
        try:
            for ebene in sorted(ebenen, key=lambda e: -e.z):
                _flaeche(st, hf.netz_fuer(netz, ebene), w, ebene, konturen, variante, r, schritt)
        except _KeinMorph:
            if len(varianten) > 1:
                continue  # der Morph passt nicht: die anderen Varianten entscheiden
            variante = "rohteil"  # vorgegeben, passt aber nicht: die Ringe vom Rohteil her
            st = _Stand()
            for ebene in sorted(ebenen, key=lambda e: -e.z):
                _flaeche(st, hf.netz_fuer(netz, ebene), w, ebene, konturen, variante, r, schritt)
        if st.flaechen == 0:
            continue
        zeit = bn.zeit(st.punkte, w.vorschub if w.vorschub > 0 else 1000.0, w.eintauchen or None)
        ergebnisse[variante] = (st, zeit)
    if not ergebnisse:
        raise ValueError(tr("ra.fehler.nichts"))
    variante = min(ergebnisse, key=lambda v: ergebnisse[v][1])
    st, zeit = ergebnisse[variante]
    return Raeumbahn(
        st.punkte,
        st.flaechen,
        st.lagen,
        st.ringe,
        st.laeufe,
        st.z_min if math.isfinite(st.z_min) else 0.0,
        st.laenge,
        zeit,
        variante,
        {v: z for v, (_s, z) in ergebnisse.items()},
        st.rampen,
        st.einfahrten + st.seitlich,
        st.anschluesse,
        st.rampen_bei,
        st.nachgeholt,
    )


def kontur_flaeche(kontur):
    """Das Gesicht (Part.Face) einer geschlossenen Kontur, auf z = 0 gelegt – None, wenn OCC
    keins daraus macht."""
    import FreeCAD
    import Part

    if not kontur.geschlossen:
        return None
    try:
        draht = kontur.draht.copy()
        draht.translate(FreeCAD.Vector(0, 0, -kontur.z_unten))
        return Part.Face(draht)
    except Exception:  # OCC: kein Gesicht aus dem Draht
        return None


def innerhalb(flaeche, x, y):
    """Liegt (x, y) im Gesicht (bei z = 0)?"""
    import FreeCAD

    return bool(flaeche.isInside(FreeCAD.Vector(x, y, 0.0), 1e-6, True))


def ist_tasche(kontur, flaeche):
    """Liegt die freie Seite der Kontur innen – eine Tasche, keine Insel?"""
    return innerhalb(
        flaeche,
        kontur.stelle[0] + kontur.normale[0] * 0.01,
        kontur.stelle[1] + kontur.normale[1] * 0.01,
    )


def taschenboeden(form, waende):
    """Die Namen der Böden der Taschen, deren Wände `waende` („Face6“ …) sind: je geschlossener
    Kontur mit der freien Seite innen die ebene Fläche nach oben auf ihrer Unterkante."""
    if not waende:
        return []
    try:
        konturen = kb.konturen(form, list(waende))
    except ValueError:
        return []
    ebenen = hf.ebenen_oben(form)
    ergebnis = []
    for k in konturen:
        flaeche = kontur_flaeche(k)
        if flaeche is None or not ist_tasche(k, flaeche):
            continue
        for e in ebenen:
            if abs(e.z - k.z_unten) > kb.NAH or e.name in ergebnis:
                continue
            if innerhalb(flaeche, (e.x_von + e.x_bis) / 2, (e.y_von + e.y_bis) / 2):
                ergebnis.append(e.name)
    return ergebnis


def _tasche_um(ebene, konturen):
    """Die geschlossene Kontur um die Fläche mit der freien Seite innen – die Tasche; None."""
    mitte = ((ebene.x_von + ebene.x_bis) / 2, (ebene.y_von + ebene.y_bis) / 2)
    beste = None
    for k in konturen:
        if not k.geschlossen or abs(k.z_unten - ebene.z) > kb.NAH:
            continue
        flaeche = kontur_flaeche(k)
        if flaeche is None or not ist_tasche(k, flaeche):
            continue  # die freie Seite liegt außen: eine Insel
        if not innerhalb(flaeche, mitte[0], mitte[1]):
            continue
        if beste is None or flaeche.Area < beste[1]:
            beste = (k, flaeche.Area)
    return beste[0] if beste else None


def _flaeche(st, netz, w, ebene, konturen, variante, r, schritt):
    """Eine Fläche räumen – alle Lagen, in der Variante."""
    tasche = _tasche_um(ebene, konturen)
    if tasche is not None:
        # In der Tasche gibt es nur die Ringe von innen nach außen – in jeder Variante, damit
        # alle dieselbe Arbeit tun (sonst „gewann“ eine, die die Tasche ausließ; P-2026-10-01-26).
        variante = "inseln"
    ziel = ebene.z + max(w.aufmass_boden, 0.0)
    oben = w.oben
    if tasche is not None and _darueber_geraeumt(st, tasche):
        # Die Fläche um die Tasche ist in dieser Bahn schon geräumt: die Lagen beginnen an der
        # Oberkante der Wände. Sonst am Rohteil – ob eine andere Operation das Rohteil über der
        # Tasche schon weggefräst hat, weiß die Bahn nicht (P-2026-10-01-26).
        oben = min(w.oben, tasche.z_oben + max(w.aufmass_boden, 0.0))
    if oben <= ziel + GLEICH:
        return
    zustellung = w.zustellung
    if w.schneidenlaenge > 0:
        zustellung = min(zustellung, w.schneidenlaenge)
    anzahl_lagen = max(1, int(math.ceil((oben - ziel - hf.LAGEN_SPIEL) / zustellung)))
    lagen = oben - (oben - ziel) * np.arange(1, anzahl_lagen + 1) / anzahl_lagen
    x_von, x_bis, y_von, y_bis = w.rohteil
    rand = 3.0 * r + w.zeilenabstand
    if tasche is not None:
        bb = tasche.draht.BoundBox
        x_von, x_bis = max(x_von, bb.XMin - rand), min(x_bis, bb.XMax + rand)
        y_von, y_bis = max(y_von, bb.YMin - rand), min(y_bis, bb.YMax + rand)
    toleranz = netz.toleranz
    zugabe = max(w.aufmass, 0.0) + toleranz + vb.RAND  # mit_aufmass: das Ergebnis heben
    geformt = form_mit_aufmass(w.form, max(w.aufmass, 0.0) + toleranz)
    feld = _Feld(
        netz,
        geformt,
        zugabe,
        r,
        x_von - rand,
        x_bis + rand,
        y_von - rand,
        y_bis + rand,
        schritt,
        w.rohteil,
        w.zeilenabstand + schritt,
    )
    r_ein = w.einfahrradius if w.einfahrradius and w.einfahrradius > 0 else kb.EINFAHRT_ANTEIL * r
    gerade = kb.GERADE_ANTEIL * r
    material_links = not w.gleichlauf  # Gleichlauf (M3): das Material rechts
    genaue = inselringe(konturen, ebene, w, r, schritt, toleranz, material_links)
    vorige = oben
    gefahren = False
    for lage in lagen:
        lage = float(lage)
        erlaubt = feld.erlaubt_feld(lage, ziel)
        feld.frei[:] = False
        ablauf = _Lage(st, feld, w, r, r_ein, gerade, lage, vorige, erlaubt, schritt, oben)
        gesperrt = ~erlaubt
        # Zur sicheren Seite: das Gesperrte um eine Zelle breiter – auch diagonal, sonst
        # berührt der Ring am Niveau 0 an runden Wänden einen gesperrten Knoten und reißt ab.
        breiter = gesperrt.copy()
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di or dj:
                    breiter |= np.roll(np.roll(gesperrt, di, 0), dj, 1)
        gesperrt = breiter
        D = feld.abstand_zu(
            gesperrt & feld.im_raster(*np.meshgrid(feld.xs, feld.ys, indexing="ij"))
        )
        ringe_vorher = st.ringe
        if tasche is None and variante == "inseln" and not np.isfinite(D).any():
            variante = "rohteil"  # keine Insel: nur die Ringe vom Rohteil her
        if tasche is None and variante == "rohteil":
            _ringe_vom_rohteil(ablauf, feld, w, r, D, material_links, schritt, toleranz)
            _ringe_um_inseln(ablauf, feld, w, D, material_links, schritt, toleranz, True, genaue)
        elif tasche is None and variante == "morph":
            _ringe_morph(ablauf, feld, w, r, D, material_links, schritt, toleranz, genaue)
            _ringe_um_inseln(ablauf, feld, w, D, material_links, schritt, toleranz, True, genaue)
        else:
            _ringe_um_inseln(ablauf, feld, w, D, material_links, schritt, toleranz, False, genaue)
        ablauf.reste_fahren()
        ablauf.heben()
        if st.ringe > ringe_vorher:
            st.lagen += 1
            gefahren = True
        vorige = lage
    if gefahren:
        st.flaechen += 1
    st.geraeumt.append((ebene.z, ebene.x_von, ebene.x_bis, ebene.y_von, ebene.y_bis))


def _darueber_geraeumt(st, tasche):
    """Hat diese Bahn die Fläche, in der die Tasche liegt, schon geräumt – eine Fläche auf der
    Höhe ihrer Oberkante, die sie umfasst?"""
    bb = tasche.draht.BoundBox
    for z, x_von, x_bis, y_von, y_bis in st.geraeumt:
        if abs(z - tasche.z_oben) > kb.NAH:
            continue
        x_drin = x_von <= bb.XMin + GLEICH and x_bis >= bb.XMax - GLEICH
        if x_drin and y_von <= bb.YMin + GLEICH and y_bis >= bb.YMax - GLEICH:
            return True
    return False


def form_mit_aufmass(form, aufmass):
    """Die Fräserform um das Aufmaß größer – für die Hüllfläche."""
    return form.mit_aufmass(aufmass)


def _naechster_zuerst(ablauf, ringe, eng, kennung, nur=None, luft=False):
    """Fährt die Ringe – immer den, der der Spitze am nächsten liegt, zuerst."""
    while ringe:
        if ablauf.ort is None:
            naechster = 0
        else:
            naechster = min(
                range(len(ringe)),
                key=lambda k: float(
                    np.min(
                        np.hypot(
                            ringe[k].proben.x - ablauf.ort[0], ringe[k].proben.y - ablauf.ort[1]
                        )
                    )
                ),
            )
        ring = ringe.pop(naechster)
        ablauf.ring(
            ring,
            eng=eng,
            kennung=kennung,
            nur=None if nur is None else nur.get(id(ring)),
            luft=luft,
        )


def _ringe_vom_rohteil(ablauf, feld, w, r, D, material_links, schritt, toleranz):
    """Die Ringe um das, was noch steht – ein Feld F = min(Tiefe im Rohteil + R, D + ae): vom
    Rohteilrand her je ae weiter hinein (der erste Ring R − ae außerhalb, in der Luft) und von
    jeder Insel her je ae weiter hinaus; seine Höhenlinien bei m · ae sind die Ringe, überall ae
    auseinander. Ein Ring, der nur dem Rohteilrand folgt, ist das Rechteck mit runden Ecken
    (analytisch, mit Bögen). Einer, der nur eine Insel umrundet, wartet, bis alles um ihn herum
    weg ist: Die Ringe um die Inseln kommen zuletzt, von außen nach innen, bis an die Insel. Die
    übrigen – das Rechteck, das in die Inseln hineinbeißt, die Zwickel zwischen Insel und Ecke –
    kommen in ihrer Reihenfolge. So gibt es keine zerhackten Ringe und keine Luftfahrten (Manuel,
    2026-10-01: die Ringe sollen am Ende nur noch um den Zapfen fahren)."""
    ae = w.zeilenabstand
    gueltig = feld.beruehrt & feld.im_raster(*np.meshgrid(feld.xs, feld.ys, indexing="ij"))
    F = np.minimum(feld.tiefe + r, D + ae)
    if not gueltig.any():
        return
    hoechste = float(F[gueltig].max())
    if not np.isfinite(hoechste) or hoechste < ae:
        return
    spaeter = {}  # Niveau m → [Ringe nur um Inseln]
    for m in range(1, int(math.floor(hoechste / ae + 1e-9)) + 1):
        niveau = m * ae
        jetzt = []
        for punkte, geschlossen in _hoehenlinien(F, feld.xs, feld.ys, niveau):
            if len(punkte) < 2:
                continue
            laenge = float(np.sum(np.hypot(*np.diff(punkte, axis=0).T)))
            if geschlossen and laenge < 2 * math.pi * ae:
                continue  # winzig: der Ring davor deckt es ab
            i, j = feld.zellen(punkte[:, 0], punkte[:, 1])
            # Was bestimmt den Ring: nur der Rohteilrand (die Insel liegt deutlich weiter weg),
            # nur die Inseln (der Rand liegt deutlich weiter weg) oder beides?
            nur_rand = bool((D[i, j] + ae > niveau + schritt).all())
            nur_insel = bool((feld.tiefe[i, j] + r > niveau + schritt).all())
            if nur_rand and geschlossen:
                ring = _rohteil_ring(w.rohteil, niveau - r, material_links, schritt)
            else:
                ring = _ring_aus_linie(
                    punkte, geschlossen, material_links, feld, niveau, F, schritt, toleranz,
                    material_hoch=not nur_insel,
                )  # fmt: skip
            if ring is None:
                continue
            if nur_insel:
                spaeter.setdefault(m, []).append(ring)
            else:
                jetzt.append(ring)
        _naechster_zuerst(ablauf, jetzt, False, f"rohteil {m}")
    for m in sorted(spaeter, reverse=True):
        _naechster_zuerst(ablauf, spaeter[m], True, f"insel {m}")


def _abschnitt(r, h):
    """Die Fläche des Kreisabschnitts der Höhe h im Kreis mit dem Radius r."""
    h = min(max(h, 0.0), 2.0 * r)
    return r * r * math.acos((r - h) / r) - (r - h) * math.sqrt(max(2.0 * r * h - h * h, 0.0))


def _bilinear(werte, feld, x, y):
    """Die Werte des Feldes (nx, ny) an den Stellen (x, y), bilinear zwischen den Knoten."""
    fx = np.clip((np.asarray(x, dtype=float) - feld.x0) / feld.schritt, 0.0, feld.nx - 1.000001)
    fy = np.clip((np.asarray(y, dtype=float) - feld.y0) / feld.schritt, 0.0, feld.ny - 1.000001)
    i0, j0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - i0, fy - j0
    return (
        werte[i0, j0] * (1 - tx) * (1 - ty)
        + werte[i0 + 1, j0] * tx * (1 - ty)
        + werte[i0, j0 + 1] * (1 - tx) * ty
        + werte[i0 + 1, j0 + 1] * tx * ty
    )


def _kreuzpunkte(werte, xs, ys, niveau):
    """(x, y) aller Stellen, an denen die Höhenlinie `niveau` des Feldes eine Kante des Rasters
    kreuzt – die Punkte der Linie ohne ihre Reihenfolge (für die Suche nach dem nächsten Ring)."""
    s = float(xs[1] - xs[0])
    a, b = werte[:-1, :] - niveau, werte[1:, :] - niveau
    ii, jj = np.nonzero((a > 0) != (b > 0))
    t = a[ii, jj] / (a[ii, jj] - b[ii, jj])
    x1, y1 = xs[ii] + t * s, ys[jj]
    a, b = werte[:, :-1] - niveau, werte[:, 1:] - niveau
    ii, jj = np.nonzero((a > 0) != (b > 0))
    t = a[ii, jj] / (a[ii, jj] - b[ii, jj])
    x2, y2 = xs[ii], ys[jj] + t * s
    return np.concatenate([x1, x2]), np.concatenate([y1, y2])


def _harmonisch(wert, unbekannt, start, genau=1e-6, hoechstens=None):
    """u mit Δu = 0 auf den Zellen `unbekannt`, u = `wert` auf allen anderen – rot-schwarz-SOR
    (Überrelaxation), ab der Schätzung `start`. Die Höhenlinien einer solchen Funktion sind
    glatt und schneiden sich nie; in einem Ring zwischen zwei Rändern ist jede eine einzige
    geschlossene Linie (keine Sattelpunkte) – die Grundlage des Morphs (Bieterman & Sandstrom,
    „A Curvilinear Tool-Path Method for Pocket Machining“, 2003)."""
    u = np.where(unbekannt, start, wert).astype(float)
    unbekannt = unbekannt.copy()
    unbekannt[0, :] = unbekannt[-1, :] = unbekannt[:, 0] = unbekannt[:, -1] = False
    nx, ny = u.shape
    n = max(nx, ny)
    omega = 2.0 / (1.0 + math.sin(math.pi / n))
    flach = u.ravel()
    ii, jj = np.nonzero(unbekannt)
    stellen = ii * ny + jj
    farben = [stellen[(ii + jj) % 2 == 0], stellen[(ii + jj) % 2 == 1]]
    hoechstens = hoechstens or 8 * n
    for _ in range(hoechstens):
        groesste = 0.0
        for idx in farben:
            if not len(idx):
                continue
            mittel = 0.25 * (flach[idx - ny] + flach[idx + ny] + flach[idx - 1] + flach[idx + 1])
            d = omega * (mittel - flach[idx])
            flach[idx] += d
            groesste = max(groesste, float(np.abs(d).max()))
        if groesste < genau:
            break
    return u


def inselringe(konturen, ebene, w, r, schritt, toleranz, material_links):
    """Die Ringe um die Inseln der Fläche, genau gerechnet: der Versatz ihrer Unterkante um
    Radius + Aufmaß (kontur_bahn._versatz – mit Bögen, ein Kreis bleibt ein Kreis). Inseln sind
    geschlossene Konturen auf der Höhe der Fläche mit dem Material innen."""
    ergebnis = []
    for k in konturen:
        if not k.geschlossen or abs(k.z_unten - ebene.z) > kb.NAH:
            continue
        flaeche = kontur_flaeche(k)
        if flaeche is None or ist_tasche(k, flaeche):
            continue
        versatz = kb._versatz(k, r + max(w.aufmass, 0.0), toleranz, schritt)
        if versatz is None:
            continue
        segmente, _proben = versatz  # in Fahrtrichtung der Kontur: das Material rechts
        if material_links:
            segmente = [s.umgekehrt() for s in reversed(segmente)]
        ergebnis.append(_Ring(segmente, kb._abtasten(segmente, schritt, True), True, True))
    return ergebnis


def _genau(ring, genaue, schritt):
    """Der genaue Ring (inselringe), der auf dem Ring aus dem Raster liegt – sonst dieser. Der
    aus dem Raster liegt um die Zelle, um die das Gesperrte breiter ist, und die Zugabe der
    Hüllfläche weiter außen (bis etwa 2 Zellen); liegt er weiter weg, stört dort etwas anderes
    (eine zweite Insel, ein Überhang) – dann gilt der aus dem Raster."""
    for genauer in genaue:
        gx, gy = genauer.proben.x, genauer.proben.y
        rx, ry = ring.proben.x, ring.proben.y
        if len(gx) < 2 or len(rx) < 2:
            continue
        abstand = np.hypot(gx[:, None] - rx[None, :], gy[:, None] - ry[None, :]).min(axis=1)
        if float(abstand.max()) <= 2.0 * schritt + 0.25:
            return genauer
    return ring


def _bogenlaengen(x, y, geschlossen):
    """Die Bogenlänge bis zu jeder Probe – geschlossen mit dem Stück zurück zum Anfang am Ende."""
    if geschlossen:
        x, y = np.append(x, x[0]), np.append(y, y[0])
    return np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])


def _auf_ring(x, y, laengen, gesamt, a):
    """Der Punkt bei der Bogenlänge a (modulo gesamt) auf dem geschlossenen Ring."""
    a = a % gesamt
    k = int(np.searchsorted(laengen, a, side="right") - 1)
    k = min(max(k, 0), len(x) - 1)
    stueck = laengen[k + 1] - laengen[k]
    t = 0.0 if stueck <= _WINZIG else (a - laengen[k]) / stueck
    k1 = (k + 1) % len(x)
    return (x[k] + (x[k1] - x[k]) * t, y[k] + (y[k1] - y[k]) * t)


def _spirale(ringe, uebergang, schritt):
    """Die geschlossenen Ringe (von außen nach innen) als eine Spirale: Jeder Ring beginnt, wo
    der vorige ihn erreicht, läuft einmal herum und geht auf seinem letzten Stück (`uebergang`
    mm, höchstens ein Drittel des Rings) gleitend in den nächsten über – kein Schritt quer,
    keine Ecke, der Eingriff wächst dabei langsam an. Der Übergang liegt innerhalb des Rings:
    Sein Streifen wird ganz geschnitten. Gibt die Punkte (m, 2) zurück; sie enden am Anfang des
    letzten Rings, der nicht dazugehört."""
    punkte = []
    start = 0
    for nummer in range(len(ringe) - 1):
        x = np.roll(ringe[nummer].proben.x, -start)
        y = np.roll(ringe[nummer].proben.y, -start)
        laengen = _bogenlaengen(x, y, True)
        gesamt = float(laengen[-1])
        nx_, ny_ = ringe[nummer + 1].proben.x, ringe[nummer + 1].proben.y
        # Wo der nächste Ring anfängt: am nächsten beim Anfang dieses.
        naechster = int(np.argmin(np.hypot(nx_ - x[0], ny_ - y[0])))
        nx_, ny_ = np.roll(nx_, -naechster), np.roll(ny_, -naechster)
        laengen_n = _bogenlaengen(nx_, ny_, True)
        gesamt_n = float(laengen_n[-1])
        weit = min(uebergang, gesamt / 3.0, gesamt_n / 3.0)
        ende = gesamt - weit
        for k in range(int(np.searchsorted(laengen, ende, side="left"))):
            punkte.append((float(x[k]), float(y[k])))
        anzahl = max(2, int(math.ceil(weit / schritt)))
        for i in range(anzahl + 1):
            alpha = i / anzahl
            p = _auf_ring(x, y, laengen, gesamt, ende + alpha * weit)
            q = _auf_ring(nx_, ny_, laengen_n, gesamt_n, -(1.0 - alpha) * weit * gesamt_n / gesamt)
            punkte.append((p[0] * (1 - alpha) + q[0] * alpha, p[1] * (1 - alpha) + q[1] * alpha))
        start = naechster
    zug = []
    for p in punkte:
        if not zug or math.hypot(p[0] - zug[-1][0], p[1] - zug[-1][1]) > _WINZIG:
            zug.append(p)
    return np.array(zug) if zug else np.zeros((0, 2))


def _ringe_morph(ablauf, feld, w, r, D, material_links, schritt, toleranz, genaue=()):
    """Der Morph (Manuel, 2026-10-01: „im Viereck anfangen, aber immer runder werden, so dass
    er am Ende nur um den Zapfen fährt“): Zwischen dem ersten Ring – dem Rechteck R − ae
    außerhalb des Rohteils – und dem Ring um die Inseln (D = 0) liegt das Feld u mit Δu = 0,
    u = 1 außen und 0 an den Inseln (_harmonisch). Seine Höhenlinien sind die Ringe: das
    Rechteck, von Ring zu Ring runder, zuletzt der Kreis um den Zapfen – jede eine geschlossene
    Linie, ohne Knick, keine zerfällt. Wie weit der nächste Ring nach innen rückt, sagt der
    Eingriff: so weit, dass die Stirn an keiner Stelle des Rings mehr ungeschnittenes Rohteil
    unter sich hat als bei einem geraden Schnitt mit ae (MORPH_EINGRIFF) – an den Ecken, wo das
    Material außen herum läuft, darf er dafür weiter rücken. Der letzte Ring ist der genaue
    Versatz der Insel (inselringe). Gibt es keine Insel im Rohteil, oder reicht eine bis an den
    Rand, gibt es keinen Morph: dann die Ringe vom Rohteil her."""
    ae = w.zeilenabstand
    aussen = ae - r  # die Tiefe des ersten Rings im Rohteil (negativ: außerhalb)
    insel = np.isfinite(D) & (D <= 0.0)
    if not insel.any():
        _ringe_vom_rohteil(ablauf, feld, w, r, D, material_links, schritt, toleranz)
        return  # keine Insel: die Ringe vom Rohteil her sind schon rund genug
    if (insel & (feld.tiefe <= aussen + ae)).any():
        raise _KeinMorph()  # die Insel reicht bis an den Rand
    erster = _rohteil_ring(w.rohteil, aussen, material_links, schritt)
    if erster is None:
        return
    spalt = feld.bei(D, erster.proben.x, erster.proben.y)
    if float(spalt.min()) < MORPH_VERHAELTNIS * float(spalt.max()):
        raise _KeinMorph()
    frei_vorher = feld.frei.copy()
    stufen = [[erster]]
    feld.merke(erster.proben.x, erster.proben.y)
    innen = feld.tiefe > aussen
    unbekannt = innen & ~insel
    abstand_aussen = np.maximum(feld.tiefe - aussen, 0.0)
    nah = np.where(np.isfinite(D), np.maximum(D, 0.0), 0.0)
    summe = nah + abstand_aussen
    with np.errstate(divide="ignore", invalid="ignore"):
        start = np.where(summe > GLEICH, nah / np.where(summe > GLEICH, summe, 1.0), 0.0)
    u = _harmonisch(np.where(insel, 0.0, 1.0), unbekannt, np.clip(start, 0.0, 1.0))
    grenze = _abschnitt(r, min(ae * MORPH_EINGRIFF, r)) / (math.pi * r * r)
    kx, ky = _kreuzpunkte(D, feld.xs, feld.ys, 0.0)
    if not len(kx):
        feld.frei[:] = frei_vorher
        ablauf.ring(erster, kennung="morph 0", luft=True)
        return
    u_insel = float(_bilinear(u, feld, kx, ky).max())  # darüber liegt jeder Ring außerhalb
    niveau = 1.0
    for _nummer in range(1, 100000):
        eingriff = feld.eingriff()
        if float(_bilinear(eingriff, feld, kx, ky).max()) <= grenze + 1e-9:
            break  # der Ring um die Insel ist dran
        unten, oben_ = u_insel, niveau
        for _ in range(MORPH_SCHRITTE):
            mitte = 0.5 * (unten + oben_)
            px, py = _kreuzpunkte(u, feld.xs, feld.ys, mitte)
            if not len(px) or float(_bilinear(eingriff, feld, px, py).max()) <= grenze + 1e-9:
                oben_ = mitte
            else:
                unten = mitte
        if oben_ >= niveau - 1e-9:
            oben_ = niveau - 0.25 * (niveau - u_insel)  # kein Fortschritt: ein Viertel weiter
        niveau = oben_
        ringe = []
        for punkte, geschlossen in _hoehenlinien(u, feld.xs, feld.ys, niveau):
            if len(punkte) < 3:
                continue
            ring = _ring_aus_linie(
                punkte, geschlossen, material_links, feld, niveau, u, schritt, toleranz
            )
            if ring is not None:
                ringe.append(ring)
                feld.merke(ring.proben.x, ring.proben.y)
        if ringe:
            stufen.append(ringe)
    letzte = []
    for punkte, geschlossen in _hoehenlinien(D, feld.xs, feld.ys, 0.0):
        if len(punkte) < 3:
            continue
        ring = _ring_aus_linie(punkte, geschlossen, material_links, feld, 0.0, D, schritt, toleranz)
        if ring is not None:
            letzte.append(_genau(ring, genaue, schritt) if geschlossen else ring)
    feld.frei[:] = frei_vorher  # gefahren und gemerkt wird jetzt, der Reihe nach
    if letzte:
        stufen.append(letzte)
    einzeln = all(len(stufe) == 1 and stufe[0].geschlossen for stufe in stufen)
    if einzeln and len(stufen) >= 2:
        # Eine Spirale: alle Ringe bis auf den letzten in einem Zug, mit gleitenden Übergängen;
        # der letzte (um die Insel, mit Bögen) schließt ohne Absatz an.
        ringe = [stufe[0] for stufe in stufen]
        vorher = ablauf.st.ringe
        zug = _spirale(ringe, 2.0 * r, schritt)
        if len(zug) >= 2:
            segmente = _segmente_aus(zug, False)
            spirale = _Ring(segmente, kb._abtasten(segmente, schritt, False), False)
            ablauf.ring(spirale, kennung="morph", luft=True)
        ablauf.ring(ringe[-1], kennung="morph insel", luft=True)
        ablauf.st.ringe = vorher + len(ringe)  # die Umläufe der Spirale zählen als Ringe
        return
    for nummer, stufe in enumerate(stufen):
        _naechster_zuerst(ablauf, list(stufe), False, f"morph {nummer}", luft=True)


def _ringe_um_inseln(ablauf, feld, w, D, material_links, schritt, toleranz, nur_rest, genaue=()):
    """Die Ringe des Feldes D (Abstand zum Gesperrten) von außen nach innen bis ans Gesperrte –
    alle, oder mit `nur_rest` nur die Stücke, unter deren Stirn noch etwas steht (nach den
    Ringen vom Rohteil her)."""
    if not np.isfinite(D).any() or D[np.isfinite(D)].max() <= 0:
        return
    ae = w.zeilenabstand
    gueltig = feld.beruehrt & feld.im_raster(*np.meshgrid(feld.xs, feld.ys, indexing="ij"))
    if nur_rest:
        rest = gueltig & ~feld.frei & (D >= 0)
        if not rest.any():
            return
        hoechste = float(D[rest].max())
    else:
        drin = gueltig & (D >= 0)
        if not drin.any():
            return
        hoechste = float(D[drin].max())
    j = int(math.ceil(hoechste / ae))
    while j >= 0:
        niveau = j * ae
        linien = _hoehenlinien(D, feld.xs, feld.ys, niveau)
        ringe = []
        nur = {}
        for punkte, geschlossen in linien:
            if len(punkte) < 2:
                continue
            laenge = float(np.sum(np.hypot(*np.diff(punkte, axis=0).T)))
            if geschlossen and laenge < 2 * math.pi * ae:
                continue  # winzig: der nächste Ring deckt es ab
            ring = _ring_aus_linie(
                punkte, geschlossen, material_links, feld, niveau, D, schritt, toleranz
            )
            if ring is None:
                continue
            if j == 0 and geschlossen:
                ring = _genau(ring, genaue, schritt)  # um die Insel: der genaue Versatz
            if nur_rest:
                noetig = feld.ungeschnitten(ring.proben.x, ring.proben.y) > 1e-6
                if not noetig.any():
                    continue
                # Ein Stück rundherum (3 mm), damit kein Lauf an einer Zelle endet.
                breit = max(1, int(round(3.0 / schritt)))
                kern = np.concatenate([noetig[-breit:], noetig, noetig[:breit]])
                nur[id(ring)] = np.convolve(kern, np.ones(2 * breit + 1), "same")[breit:-breit] > 0
            ringe.append(ring)
        _naechster_zuerst(ablauf, ringe, True, f"feld {j}", nur if nur_rest else None)
        j -= 1
