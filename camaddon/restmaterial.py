# SPDX-License-Identifier: LGPL-2.1-or-later
"""Rohteil und Fertigteil in der Simulation (Spezifikation W-003, Stufe V3g).

Manuel (2026-09-29): „haben wir eine rohteil und fertigteil vergleich in der
‚simualtion‘“.

Die Stange als Radien über (a, φ): r[i, j] – wie weit das Material an der Stelle a_i
längs der Achse unter dem Winkel φ_j reicht (SCHRITT_A × SCHRITT_PHI, wie die
Hüllfläche in vierachs_huelle: φ = 0 in Richtung `radial`, rechtshändig um `laengs`).
Ein radiales Werkzeug – der Fräser von „Rundum schruppen“ zeigt von außen auf die
Achse – nimmt weg, was in ihm liegt: Steht seine Spitze auf dem Radius r beim Winkel
φ_t und der Stelle a_t, trifft ein Strahl aus der Achse unter φ_j (Δ = φ_j − φ_t) das
Werkzeug ab ρ = r / cos Δ, solange er seitlich innerhalb des Fräsers bleibt
(r · |tan Δ| ≤ √(R² − (a_i − a_t)²)); dort endet das Material. Zwischen zwei Punkten
der Bahn fährt der Fräser in Schritten von höchstens TEILSCHRITT am Umfang.

Am Ende der Vergleich mit dem fertigen Teil (vergleiche): seine Radien im selben
Raster (die Hüllfläche einer Scheibe von einer halben Rasterweite, vierachs_huelle),
je Zelle der Rest darüber – grün bis Aufmaß + 0,1 mm, gelb darüber, rot ab Aufmaß
+ 1 mm, blau, wo mehr als 0,05 mm im Teil fehlen.

Läuft ohne Oberfläche; numpy gehört zu FreeCAD.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import vierachs_huelle as vh

SCHRITT_A = 0.5  # mm – Raster längs der Achse
SCHRITT_PHI = 1.0  # Grad – Raster rundum
TEILSCHRITT = 0.5  # mm – so fein fährt der Fräser zwischen zwei Punkten der Bahn

# Vergleich mit dem fertigen Teil
GRUEN_BIS = 0.1  # mm über dem Aufmaß
ROT_AB = 1.0  # mm über dem Aufmaß
BLAU_AB = 0.05  # mm im Teil
OHNE_TEIL, GRUEN, GELB, ROT, BLAU = range(5)  # Werte in Vergleich.farbe


class Stange:
    """Die Radien des Materials über (a, φ) – anfangs die ganze Stange."""

    def __init__(self, radius, a_von, a_bis, schritt_a=SCHRITT_A, schritt_phi=SCHRITT_PHI):
        anzahl_a = max(2, int(math.ceil((a_bis - a_von) / schritt_a - 1e-9)) + 1)
        self.a = a_von + schritt_a * np.arange(anzahl_a)
        self.phi = vh.raster_phi(schritt_phi)
        self.radius = float(radius)
        self.r = np.full((anzahl_a, len(self.phi)), self.radius)
        self._schritt_phi = math.radians(schritt_phi)

    def zuruecksetzen(self):
        self.r.fill(self.radius)

    def fahre(self, von, nach, fraeser_radius):
        """Der Fräser fährt von `von` nach `nach` – je (a, r, φ in Grad am Teil) – und nimmt
        weg, was er dabei trifft (den Anfang nicht: der kam mit dem Stück davor)."""
        a0, r0, p0 = von
        a1, r1, p1 = nach
        bogen = abs(math.radians(p1 - p0)) * max(r0, r1)
        weg = max(bogen, abs(a1 - a0), abs(r1 - r0))
        anzahl = max(1, int(math.ceil(weg / TEILSCHRITT)))
        for k in range(1, anzahl + 1):
            t = k / anzahl
            self.schnitt(a0 + t * (a1 - a0), r0 + t * (r1 - r0), p0 + t * (p1 - p0), fraeser_radius)

    def schnitt(self, a_t, r_t, phi_t_grad, fraeser_radius):
        """Nimmt weg, was der Fräser mit der Spitze bei (a_t, r_t, φ_t) trifft."""
        radius = fraeser_radius
        if r_t >= self.radius or radius <= 0:
            return  # über der Stange: trifft nichts
        i0 = int(np.searchsorted(self.a, a_t - radius, "left"))
        i1 = int(np.searchsorted(self.a, a_t + radius, "right"))
        if i0 >= i1:
            return
        seitlich = np.sqrt(np.maximum(radius * radius - (self.a[i0:i1] - a_t) ** 2, 0.0))
        r_t = max(r_t, 1e-6)
        weit = math.atan(radius / r_t)  # weiter weg trifft kein Strahl den Fräser
        phi_t = math.radians(phi_t_grad)
        mitte = phi_t / self._schritt_phi
        von = int(math.floor(mitte - weit / self._schritt_phi))
        bis = int(math.ceil(mitte + weit / self._schritt_phi))
        spalten = np.arange(von, bis + 1)
        delta = spalten * self._schritt_phi - phi_t
        j = spalten % len(self.phi)
        tan = np.abs(np.tan(delta))
        trifft = (r_t * tan)[None, :] <= seitlich[:, None]
        bis_hier = np.where(trifft, (r_t / np.cos(delta))[None, :], np.inf)
        zeilen = np.arange(i0, i1)
        block = np.ix_(zeilen, j)
        self.r[block] = np.minimum(self.r[block], bis_hier)


@dataclass
class Vergleich:
    """Was nach dem Abtragen auf dem fertigen Teil bleibt (vergleiche())."""

    rest: np.ndarray  # (n_a, n_phi) mm über dem Teil; nan, wo kein Teil ist
    farbe: np.ndarray  # (n_a, n_phi) OHNE_TEIL, GRUEN, GELB, ROT oder BLAU
    kleinster: float  # mm – so wenig bleibt (negativ: im Teil)
    groesster: float  # mm – so viel bleibt höchstens


def teilradien(netz, laengs, radial, stange):
    """Die Radien des fertigen Teils im Raster der Stange – −inf, wo es keins gibt. Die Scheibe
    einer halben Rasterweite fasst, was zwischen den Strahlen liegt."""
    return vh.schaftfraeser(netz, laengs, radial, SCHRITT_A / 2, stange.a, stange.phi).r


def vergleiche(stange, teil, aufmass):
    """Das Restmaterial gegen das fertige Teil (`teil`: teilradien()), je Zelle eingefärbt;
    `aufmass`: das Schlichtaufmaß, das stehen bleiben soll (mm)."""
    da = np.isfinite(teil)
    rest = np.where(da, stange.r - teil, np.nan)
    farbe = np.full(stange.r.shape, OHNE_TEIL, dtype=np.int8)
    farbe[da & (rest <= aufmass + GRUEN_BIS)] = GRUEN
    farbe[da & (rest > aufmass + GRUEN_BIS)] = GELB
    farbe[da & (rest >= aufmass + ROT_AB)] = ROT
    farbe[da & (rest < -BLAU_AB)] = BLAU
    if not da.any():
        return Vergleich(rest, farbe, 0.0, 0.0)
    return Vergleich(rest, farbe, float(np.nanmin(rest)), float(np.nanmax(rest)))


class Abtrag:
    """Die Stange eines 4-Achs-Jobs beim Abfahren (abfahren.Abfahrt): was bis zu einer
    Station weg ist. fuer() baut es – nur für Jobs mit runder Stange und „Rundum
    schruppen“."""

    def __init__(self, stange, laengs, radial, stationen, aufmass, formen):
        self.stange = stange
        self.laengs, self.radial = laengs, radial
        # je Station (a, r, φ in Grad, fortlaufend), Fräserradius, Operation, gültig
        self.a, self.r, self.phi, self.fraeser, self.operation, self.gueltig = stationen
        self.aufmass = aufmass
        self._formen = formen
        self._teil = None  # teilradien(), einmal gerechnet
        self.bis = 0  # abgetragen bis vor diese Station

    def bis_station(self, index):
        """Trägt ab bis einschließlich Station `index`; zurück rechnet es von vorn."""
        index = min(index, len(self.a) - 1)
        if index + 1 < self.bis:
            self.stange.zuruecksetzen()
            self.bis = 0
        for k in range(max(self.bis, 1), index + 1):
            if not (self.gueltig[k - 1] and self.gueltig[k]):
                continue
            if self.operation[k - 1] != self.operation[k]:
                continue
            self.stange.fahre(
                (self.a[k - 1], self.r[k - 1], self.phi[k - 1]),
                (self.a[k], self.r[k], self.phi[k]),
                self.fraeser[k],
            )
        self.bis = max(self.bis, index + 1)

    def vergleich(self):
        """Das Restmaterial gegen das fertige Teil (Vergleich) – die Radien des Teils rechnet
        es beim ersten Mal."""
        if self._teil is None:
            import Part

            form = self._formen[0] if len(self._formen) == 1 else Part.makeCompound(self._formen)
            netz = vh.vernetze(form)
            self._teil = teilradien(netz, self.laengs, self.radial, self.stange)
        return vergleiche(self.stange, self._teil, self.aufmass)


def fuer(abfahrt, job, am_werkstueck):
    """Das Abtrag für diesen Job – oder None, wenn das Rohteil keine runde Stange ist oder
    keine Operation „Rundum schruppen“ darin läuft. `am_werkstueck`: je Station die Spitze
    am gedrehten Teil (abfahren.Abfahrt.am_werkstueck)."""
    import FreeCAD

    from .vierachs_operation import ist_rundum

    rohteil = getattr(job, "Stock", None)
    if rohteil is None or not hasattr(rohteil, "Radius") or not hasattr(rohteil, "Height"):
        return None
    ops = {o.Label: o for o in getattr(job.Operations, "Group", []) if ist_rundum(o)}
    rundum = [
        k
        for k, op in enumerate(abfahrt.operationen)
        if op.art == operationsart_rundum() and op.name in ops
    ]
    if not rundum or not abfahrt.stationen:
        return None
    laengs = rohteil.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    erste = ops[abfahrt.operationen[rundum[0]].name]
    radial = FreeCAD.Vector(erste.Werkzeugrichtung)
    a_hinten = rohteil.Placement.Base.dot(laengs)
    stange = Stange(float(rohteil.Radius), a_hinten, a_hinten + float(rohteil.Height))
    l_, u_, v_ = vh.rahmen(laengs, radial)
    punkte = np.array(am_werkstueck, dtype=float).reshape(-1, 3)
    a = punkte @ l_
    u, v = punkte @ u_, punkte @ v_
    r = np.hypot(u, v)
    phi = np.degrees(np.unwrap(np.arctan2(v, u)))
    operation = np.array([s.operation for s in abfahrt.stationen])
    radien = {
        k: float(abfahrt.operationen[k].tc.Tool.Diameter.getValueAs("mm")) / 2 for k in rundum
    }
    fraeser = np.array([radien.get(k, 0.0) for k in operation])
    gueltig = np.array(
        [s.stellungen is not None and s.operation in radien for s in abfahrt.stationen]
    )
    aufmass = min(float(ops[abfahrt.operationen[k].name].Aufmass) for k in rundum)
    formen = [
        o.Shape
        for o in getattr(job.Model, "Group", [])
        if getattr(o, "Shape", None) is not None and not o.Shape.isNull()
    ]
    if not formen:
        return None
    return Abtrag(stange, laengs, radial, (a, r, phi, fraeser, operation, gueltig), aufmass, formen)


def operationsart_rundum():
    """Wie job_schnittwerte.operationsart() „Rundum schruppen“ nennt (der Name seines
    Moduls)."""
    return "vierachs_operation"


# --- Darstellung (ohne Coin: Felder, die gui_abfahren in die Ansicht gibt) ---------------

SCHWERE = {OHNE_TEIL: 0, GRUEN: 1, GELB: 2, ROT: 3, BLAU: 4}  # was in einem Block zählt


def darstellung(stange, zeilen=2, spalten=2):
    """(Punkte, Anzahl längs, Anzahl rundum) fürs Bild: die Oberfläche der Stange im Job, je
    `zeilen` × `spalten` Zellen ein Punkt – der tiefste Radius darin; rundum geschlossen
    (der erste Winkel noch einmal am Ende)."""
    r = _bloecke(stange.r, zeilen, spalten, np.min)
    a = stange.a[: r.shape[0] * zeilen : zeilen]
    phi = stange.phi[: r.shape[1] * spalten : spalten]
    phi = np.append(phi, phi[0] + 2 * math.pi)
    r = np.concatenate([r, r[:, :1]], axis=1)
    return a, phi, r


def farben(vergleich, zeilen=2, spalten=2):
    """Die Farbe je Punkt von darstellung(): die schwerste im Block (Blau vor Rot …)."""
    schwere = np.vectorize(SCHWERE.get)(vergleich.farbe)
    block = _bloecke(schwere, zeilen, spalten, np.max)
    zurueck = {v: k for k, v in SCHWERE.items()}
    farbe = np.vectorize(zurueck.get)(block)
    return np.concatenate([farbe, farbe[:, :1]], axis=1)


def _bloecke(werte, zeilen, spalten, wie):
    n_a = werte.shape[0] // zeilen
    n_phi = werte.shape[1] // spalten
    beschnitten = werte[: n_a * zeilen, : n_phi * spalten]
    return wie(beschnitten.reshape(n_a, zeilen, n_phi, spalten), axis=(1, 3))
