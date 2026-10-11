# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Stange als Voxel – eine Nachrechnung der Rundum-Bahnen, unabhängig vom Restmodell des
Addons (dort ein Radius je Strahl): Jeder Satz fährt der Reihe nach, je Stellung höchstens einen
halben Voxel weiter, und nimmt weg, was sein Fräser trifft (ein Voxel zählt, wenn seine Mitte im
Fräser liegt). Der Fräser: ein Schaftfräser (flach) oder eine Kugel mit Schaft, seine Achse quer
zur Stange unter dem Winkel ψ (Punkt.phi), die Spitze bei x (Punkt.r), quer um Punkt.q versetzt
– wie vierachs_bahn._QuerAbstand. So fand sich in der Nacht vom 10. auf den 11.10.
(P-2026-10-11-27), dass freie Läufe des Schlichtens an Manuels Nasen-Testteil Material schnitten.

Auf allen Kernen (P-2026-10-11-42; Manuel: „warum rechnet da nur ein kern ??“ – bis dahin lag es
unter tests/ und rechnete in einem Prozess, an 0,5 mm Voxeln eine Viertelstunde): fahre() teilt
die Sätze nach ihrer Arbeit (den Stellungen in der Stange) in Stücke für die Nebenrechner; jedes
Stück rechnet auf seiner Kopie der Stange (gemeinsam, einmal je Arbeiter). Wegnehmen hängt nicht
davon ab, was vorher weg war – die Stange danach ist darum dieselbe wie der Reihe nach: was in
keinem Stück weggenommen wurde. Die Zahl je Satz dagegen schon: Dafür rechnet jedes Stück noch
einmal mit der Stange, wie die Stücke vor ihm sie ließen (`je_satz`), ebenfalls verteilt. Ohne
Nebenrechner rechnet fahre() selbst. Nur numpy – im Arbeiter ohne Dokument.
"""

import hashlib
import math

import numpy as np

STUECKE_JE_ARBEITER = 3  # wer früher fertig ist, nimmt das nächste
VERTEILT_AB = 2000  # Stellungen: darunter rechnet fahre() selbst


def _als_feld(punkte):
    """Die Sätze als (n, 4): a, r, q, phi (Grad) – Punkte (Attribute) oder schon ein Feld."""
    if isinstance(punkte, np.ndarray):
        return np.asarray(punkte, dtype=float)
    return np.array([(p.a, p.r, p.q, p.phi) for p in punkte], dtype=float).reshape(-1, 4)


def _packen(maske):
    return np.packbits(maske.ravel())


def _auspacken(gepackt, form):
    return np.unpackbits(gepackt, count=int(np.prod(form))).reshape(form).astype(bool)


def stueck(stange, saetze, r_fraeser, kugel, weg_vorher=None):
    """Auch im Nebenrechner: die Sätze `saetze` ((n, 4), der erste nur als Anfang) auf der Stange
    `stange` (Voxelstange.daten()) ohne `weg_vorher` (gepackt, oder None) – (Voxel je Satz ab dem
    zweiten, gepackt was sie wegnehmen)."""
    v = Voxelstange.aus_daten(stange)
    if weg_vorher is not None:
        v.material &= ~_auspacken(weg_vorher, v.material.shape)
    vorher = v.material.copy()
    zahlen = v._fahre_selbst(saetze, r_fraeser, kugel)
    return zahlen[1:], _packen(vorher & ~v.material)


class Voxelstange:
    def __init__(self, radius, a_von, a_bis, h=1.0):
        self.radius, self.a_von, self.h = float(radius), float(a_von), float(h)
        self.na = int(math.ceil((a_bis - a_von) / h))
        self.ny = int(math.ceil(2 * radius / h))
        self.ac = a_von + (np.arange(self.na) + 0.5) * h
        self.yc = -radius + (np.arange(self.ny) + 0.5) * h
        y = self.yc[:, None]
        z = self.yc[None, :]
        scheibe = (y**2 + z**2) <= radius**2
        self.material = np.broadcast_to(scheibe, (self.na, self.ny, self.ny)).copy()

    def daten(self):
        """Was ein Nebenrechner braucht, um die Stange nachzubauen (aus_daten): klein gepackt."""
        return (self.radius, self.a_von, self.h, self.na, _packen(self.material))

    @classmethod
    def aus_daten(cls, daten):
        radius, a_von, h, na, gepackt = daten
        v = cls(radius, a_von, a_von + na * h, h)
        v.material = _auspacken(gepackt, v.material.shape)
        return v

    def _stellung(self, a, x, psi, q, r_fraeser, kugel):
        """Nimmt weg, was der Fräser an dieser Stellung trifft; gibt die Zahl der Voxel zurück."""
        if x >= self.radius:
            return 0
        h, rad = self.h, self.radius
        c, s = math.cos(psi), math.sin(psi)
        ty, tz = x * c - q * s, x * s + q * c
        lang = rad + r_fraeser - x + 1.0
        ys = (
            ty + r_fraeser * s,
            ty - r_fraeser * s,
            ty + lang * c + r_fraeser * s,
            ty + lang * c - r_fraeser * s,
        )
        zs = (
            tz - r_fraeser * c,
            tz + r_fraeser * c,
            tz + lang * s - r_fraeser * c,
            tz + lang * s + r_fraeser * c,
        )
        i0 = max(0, int((a - r_fraeser - self.a_von) / h))
        i1 = min(self.na, int((a + r_fraeser - self.a_von) / h) + 1)
        j0 = max(0, int((min(ys) + rad) / h))
        j1 = min(self.ny, int((max(ys) + rad) / h) + 1)
        k0 = max(0, int((min(zs) + rad) / h))
        k1 = min(self.ny, int((max(zs) + rad) / h) + 1)
        if i0 >= i1 or j0 >= j1 or k0 >= k1:
            return 0
        teil = self.material[i0:i1, j0:j1, k0:k1]
        if not teil.any():
            return 0
        w = self.ac[i0:i1][:, None, None] - a
        dy = self.yc[j0:j1][None, :, None] - ty
        dz = self.yc[k0:k1][None, None, :] - tz
        t = dy * c + dz * s  # längs der Werkzeugachse, nach außen
        quer = -dy * s + dz * c
        rr = r_fraeser * r_fraeser
        if kugel:
            tm = t - r_fraeser
            drin = ((tm**2 + quer**2 + w**2) <= rr) | (
                (tm >= 0) & (tm <= lang) & (quer**2 + w**2 <= rr)
            )
        else:
            drin = (t >= 0) & (t <= lang) & (quer**2 + w**2 <= rr)
        treffer = drin & teil
        n = int(treffer.sum())
        if n:
            teil[treffer] = False
        return n

    def _schritte(self, p, n_):
        """So viele Stellungen fährt der Weg von `p` nach `n_` ((a, r, q, phi), je höchstens ein
        halber Voxel)."""
        da, dx, dq = n_[0] - p[0], n_[1] - p[1], n_[2] - p[2]
        dpsi = math.radians(n_[3] - p[3])
        strecke = max(abs(da), abs(dx), abs(dq), abs(dpsi) * (max(abs(p[1]), abs(n_[1])) + 10))
        return max(1, int(math.ceil(strecke / (self.h * 0.5))))

    def fahre(self, punkte, r_fraeser, kugel, je_satz=True, verteilt=True):
        """Je Punkt (ab dem zweiten): so viele Voxel nimmt der Weg dorthin weg (Eilgänge auch) –
        `verteilt` auf den Nebenrechnern. Ohne `je_satz` verteilt nur einmal: Die Stange danach
        stimmt, die Zahlen je Satz zählen dann auch, was ein Stück davor schon wegnahm."""
        saetze = _als_feld(punkte)
        if verteilt and len(saetze) > 2:
            weg = self._fahre_verteilt(saetze, r_fraeser, kugel, je_satz)
            if weg is not None:
                return weg
        return self._fahre_selbst(saetze, r_fraeser, kugel)

    def _fahre_verteilt(self, saetze, r_fraeser, kugel, je_satz):
        """fahre() auf den Nebenrechnern – None ohne sie, bei wenig Arbeit oder wenn sie
        scheitern."""
        try:
            from . import nebenrechner as nr
        except ImportError:  # ohne FreeCAD
            return None
        innen = np.minimum(saetze[:-1, 1], saetze[1:, 1]) < self.radius
        arbeit = np.ones(len(saetze), dtype=np.int64)
        arbeit[0] = 0
        for i in np.flatnonzero(innen):
            arbeit[i + 1] = self._schritte(saetze[i], saetze[i + 1])
        if int(arbeit.sum()) < VERTEILT_AB:
            return None
        try:
            pool = nr.pool()
            if not pool.verfuegbar() or pool.anzahl < 2:
                return None
            # Stücke gleicher Arbeit: Sätze von bis (der Satz von − 1 ist ihr Anfang)
            anzahl = min(len(saetze) - 1, pool.anzahl * STUECKE_JE_ARBEITER)
            summe = np.cumsum(arbeit)
            ziele = np.linspace(0, summe[-1], anzahl + 1)[1:-1]
            grenzen = {1, len(saetze)}
            grenzen.update(int(g) for g in np.searchsorted(summe, ziele, "right"))
            grenzen = sorted(g for g in grenzen if 1 <= g <= len(saetze))
            stuecke = list(zip(grenzen, grenzen[1:], strict=False))
            daten = self.daten()
            schluessel = "vx-" + hashlib.sha1(daten[-1].tobytes()).hexdigest()
            stange = pool.gemeinsam(schluessel, daten)

            def rechnen(vorher):
                auftraege = [
                    pool.auftrag(
                        "voxelstange",
                        "stueck",
                        stange,
                        saetze[von - 1 : bis],
                        r_fraeser,
                        kugel,
                        vorher[k],
                    )
                    for k, (von, bis) in enumerate(stuecke)
                ]
                return pool.warten(auftraege, zwischendurch=nr.ereignisse_ohne_eingaben)

            erste = rechnen([None] * len(stuecke))
            # Was die Stücke vor einem wegnahmen – für die Zahlen je Satz die Stange davor.
            form = self.material.shape
            alles, vorher = np.zeros(form, dtype=bool), []
            for _z, genommen in erste:
                vorher.append(_packen(alles) if alles.any() else None)
                alles |= _auspacken(genommen, form)
            ergebnisse = rechnen(vorher) if je_satz else erste
            pool.vergessen(schluessel)
        except nr.Fehler:
            return None
        weg = np.zeros(len(saetze), dtype=np.int64)
        for (von, bis), (zahlen, _g) in zip(stuecke, ergebnisse, strict=True):
            weg[von:bis] = zahlen
        self.material &= ~alles
        return weg

    def _fahre_selbst(self, punkte, r_fraeser, kugel):
        """Wie fahre(), der Reihe nach in diesem Prozess."""
        saetze = _als_feld(punkte)
        weg = np.zeros(len(saetze), dtype=np.int64)
        for i in range(1, len(saetze)):
            p, n_ = saetze[i - 1], saetze[i]
            da, dx, dq = n_[0] - p[0], n_[1] - p[1], n_[2] - p[2]
            dpsi = math.radians(n_[3] - p[3])
            schritte = self._schritte(p, n_)
            for k in range(1, schritte + 1):
                t = k / schritte
                weg[i] += self._stellung(
                    p[0] + t * da,
                    p[1] + t * dx,
                    math.radians(p[3]) + t * dpsi,
                    p[2] + t * dq,
                    r_fraeser,
                    kugel,
                )
        return weg
