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

Jeder andere Fräser (Stufe V5a) kommt als Drehprofil (fraeserform.Form): gegen
die Ecken des Netzes genau (Höhe des Profils in ihrem Abstand), gegen die
Dreiecke genau über die konvexe Hülle des Profils (fraeserform.Form.stuetze),
gegen die Kanten genau für die Kugel; für die anderen Profile ist die Höhe
längs einer Kante konkav, dort sucht der goldene Schnitt die höchste Stelle.
Wo eine Kante unter einer Scheibe oder dem Rand herauskommt, rechnet die
Scheibe genau. Eine Hohlkehle (Radienfräser) zählt als ihre Sehne
(fraeserform.Form.aussen) – der Fräser bleibt höher, das Teil sicher.
je_winkel() rechnet je Winkel auf einem eigenen Raster längs – das Schlichten
genau an den Stellen seiner Spirale.

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
    """Das Netz einer Form (Part.Shape) – ihre Oberfläche in Dreiecken.

    Vernetzt wird eine Kopie ohne Netz: Eine Form behält das Netz, das zuerst für
    sie gerechnet wurde, wenn es fein genug ist – etwa das feinere vom Vermessen.
    Dann hinge die Bahn davon ab, was vorher geschah, und sähe nach dem Laden
    anders aus (ausprobiert, P-2026-09-27-48).
    """
    punkte, dreiecke = form.copy().tessellate(toleranz)
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


def fraeser(netz, laengs, radial, form, a_werte, phi_werte):
    """Hüllfläche eines Fräsers mit der Form `form` (fraeserform.Form) gegen `netz` im Raster
    `a_werte` × `phi_werte` (Huelle) – wie schaftfraeser(), für jede Form."""
    a_werte = np.asarray(a_werte, dtype=float)
    phi_werte = np.asarray(phi_werte, dtype=float)
    schritt = a_werte[1] - a_werte[0] if len(a_werte) > 1 else 1.0
    anfang = np.full(len(phi_werte), a_werte[0])
    r = je_winkel(netz, laengs, radial, form, anfang, schritt, len(a_werte), phi_werte)
    return Huelle(a_werte, phi_werte, r)


def je_winkel(netz, laengs, radial, form, a0, schritt, anzahl, phi_werte):
    """Die Hüllfläche eines Fräsers mit der Form `form` für jeden Winkel phi_werte[j] (rad) an
    den Stellen a0[j] + k · schritt, k = 0 … anzahl − 1: r[k, j] (mm); KEIN_TREFFER, wo er das
    Teil nicht trifft. Jeder Winkel hat sein eigenes Raster längs – so rechnet das Schlichten
    genau an den Stellen, an denen seine Spirale vorbeikommt."""
    l_, u_, v_ = rahmen(laengs, radial)
    punkte = netz.punkte
    a = punkte @ l_
    u = punkte @ u_
    v = punkte @ v_
    kanten = _kanten(netz.dreiecke)
    r = np.full((anzahl, len(phi_werte)), KEIN_TREFFER)
    for j, phi in enumerate(phi_werte):
        c, s = math.cos(phi), math.sin(phi)
        x = u * c + v * s
        y = v * c - u * s
        spalte = np.full(anzahl, KEIN_TREFFER)
        _form_treffen(spalte, a, x, y, kanten, netz.dreiecke, form, float(a0[j]), schritt)
        r[:, j] = spalte
    return r


def je_versatz(netz, laengs, radial, form, phi0, a0, schritt, anzahl, q_werte):
    """Die Hüllfläche eines Fräsers mit der Form `form`, der aus der festen Richtung φ0 (rad)
    kommt – die Rundachse steht –, mit der Werkzeugachse um q_werte[j] (mm) quer versetzt:
    r[k, j] die Höhe der Spitze längs dieser Richtung an den Stellen a0 + k · schritt;
    KEIN_TREFFER, wo er das Teil nicht trifft („Plan indexiert“, V4c). Wie je_winkel(), nur
    ist hier je Spalte der Versatz anders, nicht der Winkel."""
    l_, u_, v_ = rahmen(laengs, radial)
    punkte = netz.punkte
    a = punkte @ l_
    u = punkte @ u_
    v = punkte @ v_
    c, s = math.cos(phi0), math.sin(phi0)
    x = u * c + v * s
    y = v * c - u * s
    kanten = _kanten(netz.dreiecke)
    r = np.full((anzahl, len(q_werte)), KEIN_TREFFER)
    for j, q in enumerate(q_werte):
        spalte = np.full(anzahl, KEIN_TREFFER)
        _form_treffen(spalte, a, x, y - float(q), kanten, netz.dreiecke, form, float(a0), schritt)
        r[:, j] = spalte
    return r


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

    Auch Kanten hinter der Achse (x ≤ 0) zählen: Die Spitze darf über die Achse hinaus, bis
    sie das Teil dahinter trifft (P-2026-10-03-07; bis dahin sperrte vierachs_bahn sie einen
    Fräserradius vor der Achse, und Kanten dahinter zählten nicht).
    """
    radius += _SAUM
    p, q = kanten[:, 0], kanten[:, 1]
    y_p, y_q = y[p], y[q]
    zaehlt = (np.minimum(np.abs(y_p), np.abs(y_q)) <= radius) | (y_p * y_q < 0)
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


def _dreiecke_treffen(spalte, a, x, y, dreiecke, radius, a0, schritt, form=None):
    """Wo der Kreis die Ebene eines Dreiecks am höchsten schneidet und diese Stelle im
    Dreieck liegt – für alle Stellen a zugleich; in `spalte` eingetragen. Mit `form`
    (fraeserform.Form): die Stelle des Profils, die die Ebene zuerst berührt."""
    radius += _SAUM
    p, q, s = dreiecke[:, 0], dreiecke[:, 1], dreiecke[:, 2]
    unten = np.minimum(np.minimum(y[p], y[q]), y[s])
    oben = np.maximum(np.maximum(y[p], y[q]), y[s])
    zaehlt = (unten <= radius) & (oben >= -radius)  # auch hinter der Achse, wie die Kanten
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
    if form is None:  # die Scheibe berührt mit ihrem Rand
        beruehrt, hoch = radius, 0.0
    else:
        beruehrt, hoch = form.stuetze(np.where(flach, 0.0, np.arctan2(schraeg, n_x)))
    versatz_a = np.where(flach, 0.0, -beruehrt * n_a / teiler)
    y_stern = np.where(flach, 0.0, -beruehrt * n_y / teiler)
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
    if form is not None:
        wert = wert - hoch[auswahl]
    np.maximum.at(spalte, index, wert)


# --- Jede Fräserform (V5a) -----------------------------------------------------------------

_GOLDEN = (math.sqrt(5.0) - 1.0) / 2.0
_GOLDEN_SCHRITTE = 25  # die Suche längs einer Kante: auf 1e-5 der Länge unter dem Fräser


def _form_treffen(spalte, a, x, y, kanten, dreiecke, form, a0, schritt):
    """Wie tief die Spitze eines Fräsers mit `form` an jeder Stelle a0 + k · schritt darf –
    gegen Ecken, Dreiecke und Kanten; in `spalte` eingetragen."""
    form = form.aussen()
    radius = form.radius
    if form.eben:  # der Schaftfräser: wie immer
        _kanten_treffen(spalte, a, x, y, kanten, radius, a0, schritt)
        _dreiecke_treffen(spalte, a, x, y, dreiecke, radius, a0, schritt)
        return
    _ecken_treffen(spalte, a, x, y, form, a0, schritt)
    _dreiecke_treffen(spalte, a, x, y, dreiecke, radius, a0, schritt, form)
    if form.nur_kugel:
        _kanten_kugel(spalte, a, x, y, kanten, form.kugel, a0, schritt)
        return
    for rand, hoehe in form.scheiben():  # wo eine Kante unter Scheibe oder Rand herauskommt
        teil = np.full(len(spalte), KEIN_TREFFER)
        _kanten_treffen(teil, a, x, y, kanten, rand, a0, schritt)
        np.maximum(spalte, teil - hoehe, out=spalte)
    _kanten_suchen(spalte, a, x, y, kanten, form, a0, schritt)


def _ecken_treffen(spalte, a, x, y, form, a0, schritt):
    """Die Punkte (a, x, y) unter dem Fräser: Die Spitze darf bis x − z(Abstand) – für alle
    Stellen a zugleich; in `spalte` eingetragen. Auch Punkte hinter der Achse (x ≤ 0) zählen
    (wie bei den Kanten, P-2026-10-03-07)."""
    radius = form.radius + _SAUM
    zaehlt = np.nonzero(np.abs(y) <= radius)[0]
    if not len(zaehlt):
        return
    a_p, x_p, y_p = a[zaehlt], x[zaehlt], y[zaehlt]
    halb = np.sqrt(np.maximum(radius * radius - y_p * y_p, 0.0))
    welches, index = _ausbreiten(a_p - halb, a_p + halb, a0, schritt, len(spalte))
    if not len(index):
        return
    abstand = np.hypot(a_p[welches] - (a0 + schritt * index), y_p[welches])
    wert = x_p[welches] - form.hoehe(np.minimum(abstand, form.radius))
    np.maximum.at(spalte, index, wert)


def _kanten_im_streifen(a, x, y, kanten, radius):
    """Die Kanten, die unter den Fräser kommen können: (p, q) Punktnummern."""
    p, q = kanten[:, 0], kanten[:, 1]
    y_p, y_q = y[p], y[q]
    zaehlt = (np.minimum(np.abs(y_p), np.abs(y_q)) <= radius) | (y_p * y_q < 0)
    return p[zaehlt], q[zaehlt]  # auch hinter der Achse (P-2026-10-03-07)


def _kanten_kugel(spalte, a, x, y, kanten, radius, a0, schritt):
    """Die Kugel mit `radius` (Mitte radius über der Spitze) gegen die Kanten, genau: Ihre Mitte
    liegt im Abstand radius von der Geraden der Kante – die höhere Lösung, wenn der Fußpunkt
    zwischen den Enden liegt. Die Enden selbst rechnet _ecken_treffen."""
    p, q = _kanten_im_streifen(a, x, y, kanten, radius + _SAUM)
    if not len(p):
        return
    d_a, d_y, d_x = a[q] - a[p], y[q] - y[p], x[q] - x[p]
    laenge = np.sqrt(d_a * d_a + d_y * d_y + d_x * d_x)
    e_a, e_y, e_x = d_a / laenge, d_y / laenge, d_x / laenge
    quadrat = 1.0 - e_x * e_x
    liegt = quadrat > 1e-12  # längs x: von oben ein Punkt, das rechnen die Ecken
    p, e_a, e_y, e_x, quadrat, laenge = (
        p[liegt],
        e_a[liegt],
        e_y[liegt],
        e_x[liegt],
        quadrat[liegt],
        laenge[liegt],
    )
    a_p = a[p]
    a_q = a_p + e_a * laenge
    welches, index = _ausbreiten(
        np.minimum(a_p, a_q) - radius, np.maximum(a_p, a_q) + radius, a0, schritt, len(spalte)
    )
    if not len(index):
        return
    w_a = a0 + schritt * index - a_p[welches]
    w_y = -y[p][welches]
    e_a, e_y, e_x = e_a[welches], e_y[welches], e_x[welches]
    quadrat, laenge = quadrat[welches], laenge[welches]
    laengs = w_a * e_a + w_y * e_y
    b = -2.0 * laengs * e_x
    c = w_a * w_a + w_y * w_y - laengs * laengs - radius * radius
    diskriminante = b * b - 4.0 * quadrat * c
    w_x = (-b + np.sqrt(np.maximum(diskriminante, 0.0))) / (2.0 * quadrat)
    fuss = (laengs + w_x * e_x) / laenge
    trifft = (diskriminante >= 0.0) & (fuss >= 0.0) & (fuss <= 1.0)
    wert = x[p][welches] + w_x - radius
    np.maximum.at(spalte, index[trifft], wert[trifft])


def _kanten_paare(spalte, a, x, y, kanten, radius, a0, schritt):
    """Je Kante und Stelle a das Stück der Kante unter dem Fräser (Abstand ≤ radius zur
    Werkzeugachse) – nur, wo es höher liegen kann als, was `spalte` schon hat. Gibt (Stelle,
    Anfang (a, y, x), Richtung (a, y, x), t_von, t_bis) oder None."""
    p, q = _kanten_im_streifen(a, x, y, kanten, radius)
    if not len(p):
        return None
    welches, index = _ausbreiten(
        np.minimum(a[p], a[q]) - radius, np.maximum(a[p], a[q]) + radius, a0, schritt, len(spalte)
    )
    if not len(index):
        return None
    p, q = p[welches], q[welches]
    hoechstens = np.maximum(x[p], x[q])  # höher als das Ende kann sie nicht (z ≥ 0)
    offen = hoechstens > spalte[index]
    p, q, index = p[offen], q[offen], index[offen]
    anfang = (a[p], y[p], x[p])
    richtung = (a[q] - a[p], y[q] - y[p], x[q] - x[p])
    neben = anfang[0] - (a0 + schritt * index)
    qa = richtung[0] ** 2 + richtung[1] ** 2
    qb = 2.0 * (richtung[0] * neben + richtung[1] * anfang[1])
    qc = neben * neben + anfang[1] ** 2 - radius * radius
    diskriminante = qb * qb - 4.0 * qa * qc
    liegt = (qa > _KLEIN) & (diskriminante >= 0.0)
    wurzel = np.sqrt(np.maximum(diskriminante, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = np.where(liegt, (-qb - wurzel) / (2.0 * qa), 0.0)
        t2 = np.where(liegt, (-qb + wurzel) / (2.0 * qa), -1.0)
    t_von, t_bis = np.maximum(t1, 0.0), np.minimum(t2, 1.0)
    zaehlt = liegt & (t_von <= t_bis)
    if not zaehlt.any():
        return None
    auswahl = np.nonzero(zaehlt)[0]
    return (
        index[auswahl],
        tuple(k[auswahl] for k in anfang),
        tuple(k[auswahl] for k in richtung),
        t_von[auswahl],
        t_bis[auswahl],
    )


def _kanten_suchen(spalte, a, x, y, kanten, form, a0, schritt):
    """Das Profil (konvex, fraeserform.Form.aussen) gegen die Kanten: Längs einer Kante ist x
    linear, der Abstand zur Werkzeugachse konvex und das Profil konvex und steigend –
    x − z(Abstand) also konkav. Seine höchste Stelle auf dem Stück unter dem Fräser findet der
    goldene Schnitt."""
    paare = _kanten_paare(spalte, a, x, y, kanten, form.radius, a0, schritt)
    if paare is None:
        return
    index, anfang, richtung, unten, oben = paare
    stelle = a0 + schritt * index

    def hoehe(t):
        abstand = np.hypot(anfang[0] + t * richtung[0] - stelle, anfang[1] + t * richtung[1])
        return anfang[2] + t * richtung[2] - form.hoehe(np.minimum(abstand, form.radius))

    m1 = oben - _GOLDEN * (oben - unten)
    m2 = unten + _GOLDEN * (oben - unten)
    f1, f2 = hoehe(m1), hoehe(m2)
    for _ in range(_GOLDEN_SCHRITTE):
        rechts = f1 < f2  # die höchste Stelle liegt zwischen m1 und oben
        unten = np.where(rechts, m1, unten)
        oben = np.where(rechts, oben, m2)
        neu = np.where(rechts, unten + _GOLDEN * (oben - unten), oben - _GOLDEN * (oben - unten))
        f_neu = hoehe(neu)
        m1, m2, f1, f2 = (
            np.where(rechts, m2, neu),
            np.where(rechts, neu, m1),
            np.where(rechts, f2, f_neu),
            np.where(rechts, f_neu, f1),
        )
    np.maximum.at(spalte, index, np.maximum(f1, f2))
