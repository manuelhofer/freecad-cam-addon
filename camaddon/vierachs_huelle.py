# SPDX-License-Identifier: LGPL-2.1-or-later
"""Hüllfläche für die 4-Achs-Bearbeitung (Spezifikation W-003, Abschnitt 9, Stufe V3a).

Ein radiales Werkzeug zeigt von außen auf die Stangenachse. Die Hüllfläche
R(a, φ) sagt, wie nah seine Spitze der Achse kommt, ohne das Teil zu
verletzen – an jeder Stelle a längs der Achse und für jeden Winkel φ, unter
dem das Werkzeug zum Teil steht.

Rundachs-Koordinaten (Abschnitt 3): a längs der Achse, vorne plus. Für den
Winkel φ zeigt x radial zum Werkzeug hin, y seitlich; φ = 0 heißt, das
Werkzeug kommt aus `radial`, und φ wächst rechtshändig um `laengs`.

Gerechnet wird gegen das vernetzte Teil, für den Schaftfräser genau: Seine
Stirn ist eine Kreisscheibe mit dem Radius R quer zu x. Über einem Dreieck ist
x linear; die höchste Stelle eines Dreiecks unter der Scheibe liegt auf einer
Kante – an ihrem Ende oder wo sie den Kreis schneidet – oder dort, wo der
Kreis die Ebene des Dreiecks am höchsten schneidet. numpy rechnet beides für
alle a eines Winkels zugleich. Das Teil ist eine geschlossene Form, also
reicht seine Oberfläche.

Läuft ohne Oberfläche; numpy gehört zu FreeCAD.
"""

import math
from dataclasses import dataclass

import numpy as np

TOLERANZ = 0.02  # mm – so weit darf das Netz von der Oberfläche des Teils abweichen
SCHRITT_A = 0.25  # mm – Raster längs der Achse
SCHRITT_PHI = 1.0  # Grad – Raster rundum
KEIN_TREFFER = -math.inf  # die Stirn trifft das Teil an dieser Stelle nicht
# So viel größer rechnet die Stirn: Berührt sie das Teil nur in einem Punkt (am Rand
# genau tangential), entscheidet sonst das Rundungsrauschen, ob er zählt.
_SAUM = 1e-9  # mm
_KLEIN = 1e-12


@dataclass(frozen=True)
class Netz:
    """Das vernetzte Teil: Punkte im Job und Dreiecke aus je drei Punktnummern."""

    punkte: np.ndarray  # (n, 3)
    dreiecke: np.ndarray  # (m, 3), ganzzahlig
    toleranz: float  # so weit darf das Netz von der Oberfläche abweichen (mm)


def vernetze(form, toleranz=TOLERANZ):
    """Das Netz einer Form (Part.Shape) – ihre Oberfläche in Dreiecken."""
    punkte, dreiecke = form.tessellate(toleranz)
    return Netz(
        np.array([(p.x, p.y, p.z) for p in punkte], dtype=float).reshape(-1, 3),
        np.array(dreiecke, dtype=np.int64).reshape(-1, 3),
        toleranz,
    )


@dataclass(frozen=True)
class Huelle:
    """R(a, φ) im Raster: r[i, j] für a[i] und phi[j]; KEIN_TREFFER, wo das Werkzeug das
    Teil nicht trifft."""

    a: np.ndarray  # (n_a,) mm, aufsteigend, gleicher Abstand
    phi: np.ndarray  # (n_phi,) rad, 0 … 2π (ohne 2π), gleicher Abstand
    r: np.ndarray  # (n_a, n_phi) mm

    def sicher(self):
        """Die Hüllfläche mit dem höchsten der drei Nachbarn rundum (über die Naht bei 0°
        weiter): Zusammen mit bei() liegt die wahre Hüllfläche zwischen den
        Rasterpunkten darunter. Ein Punkt des Teils, den die Scheibe zwischen zwei
        Stellen a nur am Rand streift, liegt einen Winkelschritt weiter mitten
        darunter – und dort ist er höher, solange er mindestens einen Fräserradius
        von der Achse weg ist."""
        r = self.r
        return Huelle(
            self.a, self.phi, np.maximum(np.maximum(np.roll(r, 1, 1), r), np.roll(r, -1, 1))
        )

    def bei(self, a, j):
        """Der Wert an der Stelle `a` (mm) für den Winkel phi[j]: der höhere der beiden
        Rasterpunkte daneben; außerhalb des Rasters KEIN_TREFFER. `a` und `j` dürfen
        gleich lange Felder sein – dann Punkt für Punkt."""
        a = np.asarray(a, dtype=float)
        j = np.asarray(j) % len(self.phi)
        schritt = self.a[1] - self.a[0] if len(self.a) > 1 else 1.0
        lage = (a - self.a[0]) / schritt
        links = np.floor(lage + 1e-9).astype(np.int64)
        rechts = np.where(np.abs(lage - np.rint(lage)) < 1e-9, links, links + 1)
        n = len(self.a)

        def wert(i):
            gueltig = (i >= 0) & (i < n)
            return np.where(gueltig, self.r[np.clip(i, 0, n - 1), j], KEIN_TREFFER)

        return np.maximum(wert(links), wert(rechts))


def rahmen(laengs, radial):
    """(L, U, V) als numpy-Einheitsvektoren: längs, radial (φ = 0) und quer = L × U."""
    l_ = np.array(laengs, dtype=float)
    u = np.array(radial, dtype=float)
    l_ /= np.linalg.norm(l_)
    u -= l_ * float(u @ l_)
    u /= np.linalg.norm(u)
    return l_, u, np.cross(l_, u)


def raster_a(a_von, a_bis, schritt=SCHRITT_A):
    """Die Stellen längs von `a_von` bis mindestens `a_bis` im Abstand `schritt`."""
    anzahl = max(1, int(math.ceil((a_bis - a_von) / schritt - 1e-9)) + 1)
    return a_von + schritt * np.arange(anzahl)


def raster_phi(schritt_grad=SCHRITT_PHI):
    """Die Winkel rundum (rad), 0 … 2π ohne 2π; 360 muss durch `schritt_grad` teilbar sein."""
    anzahl = int(round(360.0 / schritt_grad))
    return np.radians(360.0 / anzahl) * np.arange(anzahl)


def schaftfraeser(netz, laengs, radial, radius, a_werte, phi_werte):
    """Hüllfläche des Schaftfräsers mit `radius` gegen `netz` (Huelle).

    `a_werte` (aufsteigend, gleicher Abstand) und `phi_werte` (rad) geben das
    Raster; `laengs` und `radial` die Rundachs-Koordinaten im Job. Die Achse
    geht durch den Nullpunkt des Jobs.
    """
    l_, u_, v_ = rahmen(laengs, radial)
    punkte = netz.punkte
    a = punkte @ l_
    u = punkte @ u_
    v = punkte @ v_
    kanten = _kanten(netz.dreiecke)
    a_werte = np.asarray(a_werte, dtype=float)
    schritt = a_werte[1] - a_werte[0] if len(a_werte) > 1 else 1.0
    r = np.full((len(a_werte), len(phi_werte)), KEIN_TREFFER)
    for j, phi in enumerate(phi_werte):
        c, s = math.cos(phi), math.sin(phi)
        x = u * c + v * s
        y = v * c - u * s
        spalte = np.full(len(a_werte), KEIN_TREFFER)
        _kanten_treffen(spalte, a, x, y, kanten, radius, a_werte[0], schritt)
        _dreiecke_treffen(spalte, a, x, y, netz.dreiecke, radius, a_werte[0], schritt)
        r[:, j] = spalte
    return Huelle(a_werte, np.asarray(phi_werte, dtype=float), r)


def _kanten(dreiecke):
    """Die Kanten der Dreiecke, jede einmal: (k, 2) Punktnummern."""
    paare = np.concatenate([dreiecke[:, [0, 1]], dreiecke[:, [1, 2]], dreiecke[:, [2, 0]]])
    paare.sort(axis=1)
    return np.unique(paare, axis=0)


def _ausbreiten(von, bis, a0, schritt, anzahl):
    """Je Intervall [von, bis] (mm) die Rasterstellen darin: (welches, index) – welches
    Intervall und welche Stelle, für alle zusammen."""
    i_von = np.maximum(np.ceil((von - a0) / schritt - 1e-9), 0).astype(np.int64)
    i_bis = np.minimum(np.floor((bis - a0) / schritt + 1e-9), anzahl - 1).astype(np.int64)
    je = np.maximum(i_bis - i_von + 1, 0)
    beginn = np.cumsum(je) - je
    welches = np.repeat(np.arange(len(je)), je)
    index = np.repeat(i_von - beginn, je) + np.arange(int(je.sum()))
    return welches, index


def _kanten_treffen(spalte, a, x, y, kanten, radius, a0, schritt):
    """Die höchste Stelle jeder Kante unter der Scheibe – an ihrem Ende oder wo sie den
    Kreis schneidet –, für alle Stellen a zugleich; in `spalte` eingetragen.

    Kanten ganz hinter der Achse (x ≤ 0) zählen nicht: So nah kommt das Werkzeug
    der Achse ohnehin nicht (vierachs_bahn sperrt sie).
    """
    radius += _SAUM
    p, q = kanten[:, 0], kanten[:, 1]
    y_p, y_q = y[p], y[q]
    zaehlt = (np.minimum(np.abs(y_p), np.abs(y_q)) <= radius) | (y_p * y_q < 0)
    zaehlt &= np.maximum(x[p], x[q]) > 0
    p, q = p[zaehlt], q[zaehlt]
    if not len(p):
        return
    a_p, y_p, x_p = a[p], y[p], x[p]
    d_a, d_y, d_x = a[q] - a_p, y[q] - y_p, x[q] - x_p
    qa = d_a * d_a + d_y * d_y
    welches, index = _ausbreiten(
        np.minimum(a_p, a[q]) - radius, np.maximum(a_p, a[q]) + radius, a0, schritt, len(spalte)
    )
    if not len(index):
        return
    a_p, y_p, x_p = a_p[welches], y_p[welches], x_p[welches]
    d_a, d_y, d_x, qa = d_a[welches], d_y[welches], d_x[welches], qa[welches]
    neben = a_p - (a0 + schritt * index)
    # Die Punkte der Kante in der Scheibe: qa·t² + qb·t + qc ≤ 0, 0 ≤ t ≤ 1.
    qb = 2.0 * (d_a * neben + d_y * y_p)
    qc = neben * neben + y_p * y_p - radius * radius
    punkt = qa < _KLEIN  # die Kante steht längs x – von oben ein Punkt
    diskriminante = qb * qb - 4.0 * qa * qc
    # Die Nullstellen ohne Auslöschung: w = −(qb ± √D)/2, t = w/qa und qc/w.
    w = -0.5 * (qb + np.copysign(np.sqrt(np.maximum(diskriminante, 0.0)), qb))
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = w / qa
        t2 = np.where(w == 0, 0.0, qc / w)
    t_von = np.maximum(np.minimum(t1, t2), 0.0)
    t_bis = np.minimum(np.maximum(t1, t2), 1.0)
    trifft = np.where(punkt, qc <= 0.0, (diskriminante >= 0.0) & (t_von <= t_bis))
    # x ist längs der Kante linear: am höheren Ende des Stücks in der Scheibe.
    wert = x_p + np.where(punkt, np.maximum(d_x, 0.0), d_x * np.where(d_x > 0, t_bis, t_von))
    np.maximum.at(spalte, index[trifft], wert[trifft])


def _dreiecke_treffen(spalte, a, x, y, dreiecke, radius, a0, schritt):
    """Wo der Kreis die Ebene eines Dreiecks am höchsten schneidet und diese Stelle im
    Dreieck liegt – für alle Stellen a zugleich; in `spalte` eingetragen."""
    radius += _SAUM
    p, q, s = dreiecke[:, 0], dreiecke[:, 1], dreiecke[:, 2]
    unten = np.minimum(np.minimum(y[p], y[q]), y[s])
    oben = np.maximum(np.maximum(y[p], y[q]), y[s])
    zaehlt = (unten <= radius) & (oben >= -radius)
    zaehlt &= np.maximum(np.maximum(x[p], x[q]), x[s]) > 0  # wie bei den Kanten
    p, q, s = p[zaehlt], q[zaehlt], s[zaehlt]
    if not len(p):
        return
    # Normale in (a, y, x), zum Werkzeug hin (x > 0).
    e1 = (a[q] - a[p], y[q] - y[p], x[q] - x[p])
    e2 = (a[s] - a[p], y[s] - y[p], x[s] - x[p])
    n_a = e1[1] * e2[2] - e1[2] * e2[1]
    n_y = e1[2] * e2[0] - e1[0] * e2[2]
    n_x = e1[0] * e2[1] - e1[1] * e2[0]
    betrag = np.sqrt(n_a * n_a + n_y * n_y + n_x * n_x)
    umkehren = np.where(n_x < 0, -1.0, 1.0)
    n_a, n_y, n_x = n_a * umkehren, n_y * umkehren, n_x * umkehren
    # Steht das Dreieck längs x, liegt seine höchste Stelle auf einer Kante.
    liegt = n_x > 1e-9 * np.maximum(betrag, _KLEIN)
    p, q, s = p[liegt], q[liegt], s[liegt]
    n_a, n_y, n_x = n_a[liegt], n_y[liegt], n_x[liegt]
    if not len(p):
        return
    schraeg = np.sqrt(n_a * n_a + n_y * n_y)
    flach = schraeg <= 1e-9 * n_x  # quer zu x: überall gleich hoch – die Mitte zählt
    teiler = np.where(flach, 1.0, schraeg)
    versatz_a = np.where(flach, 0.0, -radius * n_a / teiler)
    y_stern = np.where(flach, 0.0, -radius * n_y / teiler)
    # Die Gerade y = y_stern schneidet das Dreieck (von oben gesehen) von s_von bis s_bis.
    s_von = np.full(len(p), math.inf)
    s_bis = np.full(len(p), -math.inf)
    for k1, k2 in ((p, q), (q, s), (s, p)):
        dy = y[k2] - y[k1]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (y_stern - y[k1]) / dy
        auf = (np.abs(dy) > _KLEIN) & (t >= 0.0) & (t <= 1.0)
        stelle = a[k1] + np.where(auf, t, 0.0) * (a[k2] - a[k1])
        s_von = np.where(auf, np.minimum(s_von, stelle), s_von)
        s_bis = np.where(auf, np.maximum(s_bis, stelle), s_bis)
    trifft = s_von <= s_bis
    if not trifft.any():
        return
    welches, index = _ausbreiten(
        (s_von - versatz_a)[trifft], (s_bis - versatz_a)[trifft], a0, schritt, len(spalte)
    )
    if not len(index):
        return
    auswahl = np.nonzero(trifft)[0][welches]
    p = p[auswahl]
    stelle_a = a0 + schritt * index + versatz_a[auswahl]
    wert = (
        x[p]
        - (n_a[auswahl] * (stelle_a - a[p]) + n_y[auswahl] * (y_stern[auswahl] - y[p]))
        / n_x[auswahl]
    )
    np.maximum.at(spalte, index, wert)
