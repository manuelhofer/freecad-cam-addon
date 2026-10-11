# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Stange als Voxel – eine Nachrechnung der Rundum-Bahnen für die Prüfungen, unabhängig vom
Restmodell des Addons (dort ein Radius je Strahl): Jeder Satz fährt der Reihe nach, je Stellung
höchstens einen halben Voxel weiter, und nimmt weg, was sein Fräser trifft (ein Voxel zählt, wenn
seine Mitte im Fräser liegt). Der Fräser: ein Schaftfräser (flach) oder eine Kugel mit Schaft,
seine Achse quer zur Stange unter dem Winkel ψ (Punkt.phi), die Spitze bei x (Punkt.r), quer um
Punkt.q versetzt – wie vierachs_bahn._QuerAbstand. So fand sich in der Nacht vom 10. auf den 11.10.
(P-2026-10-11-27), dass freie Läufe des Schlichtens an Manuels Nasen-Testteil Material schnitten.
"""

import math

import numpy as np


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

    def fahre(self, punkte, r_fraeser, kugel):
        """Je Punkt (ab dem zweiten): so viele Voxel nimmt der Weg dorthin weg (Eilgänge auch)."""
        weg = np.zeros(len(punkte), dtype=np.int64)
        for i in range(1, len(punkte)):
            p, n_ = punkte[i - 1], punkte[i]
            da, dx, dq = n_.a - p.a, n_.r - p.r, n_.q - p.q
            dpsi = math.radians(n_.phi - p.phi)
            strecke = max(abs(da), abs(dx), abs(dq), abs(dpsi) * (max(abs(p.r), abs(n_.r)) + 10))
            schritte = max(1, int(math.ceil(strecke / (self.h * 0.5))))
            for k in range(1, schritte + 1):
                t = k / schritte
                weg[i] += self._stellung(
                    p.a + t * da,
                    p.r + t * dx,
                    math.radians(p.phi) + t * dpsi,
                    p.q + t * dq,
                    r_fraeser,
                    kugel,
                )
        return weg
