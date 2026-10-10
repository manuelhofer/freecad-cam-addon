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

import hashlib
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


def schaftfraeser(netz, laengs, radial, radius, a_werte, phi_werte, nur_vorne=False):
    """Hüllfläche des Schaftfräsers mit `radius` gegen `netz` (Huelle).

    `a_werte` (aufsteigend, gleicher Abstand) und `phi_werte` (rad) geben das
    Raster; `laengs` und `radial` die Rundachs-Koordinaten im Job. Die Achse
    geht durch den Nullpunkt des Jobs. `nur_vorne`: nur Kanten und Dreiecke, die
    (teils) vor der Achse liegen – so sieht der Strahl von der Achse nach außen das
    Teil, wie das Prüffenster es braucht (restmaterial.teilradien; bis P-2026-10-03-07
    galt das für alle).
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
        k, d = kanten, netz.dreiecke
        if nur_vorne:
            k = k[np.maximum(x[k[:, 0]], x[k[:, 1]]) > 0]
            d = d[np.maximum(np.maximum(x[d[:, 0]], x[d[:, 1]]), x[d[:, 2]]) > 0]
        _kanten_treffen(spalte, a, x, y, k, radius, a_werte[0], schritt)
        _dreiecke_treffen(spalte, a, x, y, d, radius, a_werte[0], schritt)
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


def je_stellung(netz, laengs, radial, form, phi, q, a):
    """Die Hüllfläche eines Fräsers mit der Form `form` für beliebige Stellungen: je Stellung k
    kommt er aus der Richtung phi[k] (rad), seine Achse um q[k] (mm) quer versetzt, an der Stelle
    a[k] längs – r[k] die Höhe der Spitze längs seiner Achse; KEIN_TREFFER, wo er das Teil nicht
    trifft. Je Richtung rechnen alle ihre Stellungen in einem Zug – die Kerne nehmen den Versatz
    je Stelle –, aufgeteilt in Bänder quer (BAND_JE_RADIUS Fräserradien breit), damit je Band nur
    die Kanten und Dreiecke dazukommen, die quer unter den Fräser reichen (vierachs_quer, V5e:
    die Spirale mit der Querachse für Schaft- und Torusfräser). Viele Stellungen an einem großen
    Netz gehen nach Richtungen in Stücken an die Nebenrechner (_je_stellung_verteilt)."""
    phi = np.asarray(phi, dtype=float)
    q = np.asarray(q, dtype=float)
    a = np.asarray(a, dtype=float)
    if len(a) >= PARALLEL_AB_STELLUNGEN and len(a) * len(netz.dreiecke) >= PARALLEL_AB_ARBEIT:
        ergebnis = _je_stellung_verteilt(netz, laengs, radial, form, phi, q, a)
        if ergebnis is not None:
            return ergebnis
    return je_stellung_stueck(netz, laengs, radial, form, phi, q, a)


# Nebenrechner (P-2026-10-10-57): ab so vielen Stellungen, und wenn Stellungen mal Dreiecke so
# viel Arbeit ergeben, gehen die Stellungen in Stücken an sie – am 4-Achs-Testteil viermal 2 s je
# Schlichtbahn, dreimal 0,9 s beim Schruppen.
PARALLEL_AB_STELLUNGEN = 1000
PARALLEL_AB_ARBEIT = 2_000_000
STUECKE_JE_ARBEITER = 4


def kennung(netz):
    """Ein Fingerabdruck des Netzes: seine Punkte und Dreiecke."""
    pruef = hashlib.blake2b(digest_size=16)
    for teil in (netz.punkte, netz.dreiecke):
        feld = np.ascontiguousarray(teil)
        pruef.update(str(feld.shape).encode())
        pruef.update(feld.tobytes())
    return pruef.digest()


def _je_stellung_verteilt(netz, laengs, radial, form, phi, q, a):
    """je_stellung() auf den Nebenrechnern: die Richtungen der Reihe nach in Stücke mit etwa
    gleich vielen Stellungen – jede Richtung ganz in einem Stück, sie rechnet ihre Stellungen in
    einem Zug. None ohne Nebenrechner (dann rechnet der Aufrufer selbst)."""
    import FreeCAD

    from . import nebenrechner as nr

    pool = nr.pool()
    if not pool.verfuegbar() or pool.anzahl < 2:
        return None
    richtungen, welche = np.unique(phi, return_inverse=True)
    stuecke = max(2, min(pool.anzahl * STUECKE_JE_ARBEITER, len(richtungen)))
    bis = np.cumsum(np.bincount(welche, minlength=len(richtungen)))
    # Je Richtung das Stück: nach der Zahl der Stellungen bis dahin.
    stueck_je_richtung = np.minimum((bis - 1) * stuecke // len(a), stuecke - 1)
    stueck = stueck_je_richtung[welche]
    netz_gemeinsam = pool.gemeinsam("vh-netz-" + kennung(netz).hex(), netz)
    laengs = tuple(float(x) for x in laengs)
    radial = tuple(float(x) for x in radial)
    teile = [np.flatnonzero(stueck == k) for k in range(stuecke)]
    teile = [t for t in teile if len(t)]
    auftraege = [
        pool.auftrag(
            "vierachs_huelle",
            "je_stellung_stueck",
            netz_gemeinsam,
            laengs,
            radial,
            form,
            phi[t],
            q[t],
            a[t],
        )
        for t in teile
    ]
    try:
        ergebnisse = pool.warten(auftraege, zwischendurch=nr.ereignisse)
    except nr.Fehler as fehler:
        FreeCAD.Console.PrintWarning(
            f"CAM-Addon: Hüllfläche je Stellung auf den Nebenrechnern gescheitert, rechne hier: "
            f"{fehler}\n"
        )
        return None
    ergebnis = np.full(len(a), KEIN_TREFFER)
    for t, teil in zip(teile, ergebnisse, strict=True):
        ergebnis[t] = teil
    return ergebnis


def je_stellung_stueck(netz, laengs, radial, form, phi, q, a):
    """je_stellung() hier im Prozess – im Nebenrechner für ein Stück oder ohne sie."""
    phi = np.asarray(phi, dtype=float)
    q = np.asarray(q, dtype=float)
    a = np.asarray(a, dtype=float)
    ergebnis = np.full(len(a), KEIN_TREFFER)
    if not len(a):
        return ergebnis
    l_, u_, v_ = rahmen(laengs, radial)
    punkte = netz.punkte
    a_p = punkte @ l_
    u = punkte @ u_
    v = punkte @ v_
    kanten = _kanten(netz.dreiecke)
    band = BAND_JE_RADIUS * max(form.aussen().radius, 1.0)
    for richtung in np.unique(phi):
        in_richtung = np.flatnonzero(phi == richtung)
        c, s = math.cos(richtung), math.sin(richtung)
        x = u * c + v * s
        y = v * c - u * s
        baender = np.floor(q[in_richtung] / band).astype(np.int64)
        for nummer in np.unique(baender):
            welche = in_richtung[baender == nummer]
            welche = welche[np.argsort(a[welche], kind="stable")]
            spalte = np.full(len(welche), KEIN_TREFFER)
            _form_treffen(
                spalte, a_p, x, y, kanten, netz.dreiecke, form, a[welche], None, q[welche]
            )
            ergebnis[welche] = spalte
    return ergebnis


BAND_JE_RADIUS = 2.0  # so breit (in Fräserradien) ist ein Band quer in je_stellung


def _kanten(dreiecke):
    """Die Kanten der Dreiecke, jede einmal: (k, 2) Punktnummern."""
    paare = np.concatenate([dreiecke[:, [0, 1]], dreiecke[:, [1, 2]], dreiecke[:, [2, 0]]])
    paare.sort(axis=1)
    return np.unique(paare, axis=0)


def _ausbreiten(von, bis, a0, schritt, anzahl):
    """Je Intervall [von, bis] (mm) die Rasterstellen darin: (welches, index) – welches
    Intervall und welche Stelle, für alle zusammen. Ohne `schritt` (None) ist `a0` die Folge
    der Stellen selbst (aufsteigend, beliebige Abstände) – so rechnen die Kerne nur dort, wo
    eine Werkzeugstellung sie braucht (vierachs_quer)."""
    if schritt is None:
        i_von = np.searchsorted(a0, von - 1e-9, side="left").astype(np.int64)
        i_bis = (np.searchsorted(a0, bis + 1e-9, side="right") - 1).astype(np.int64)
    else:
        i_von = np.maximum(np.ceil((von - a0) / schritt - 1e-9), 0).astype(np.int64)
        i_bis = np.minimum(np.floor((bis - a0) / schritt + 1e-9), anzahl - 1).astype(np.int64)
    je = np.maximum(i_bis - i_von + 1, 0)
    beginn = np.cumsum(je) - je
    welches = np.repeat(np.arange(len(je)), je)
    index = np.repeat(i_von - beginn, je) + np.arange(int(je.sum()))
    return welches, index


def _stelle(a0, schritt, index):
    """Die Stelle längs zu den Rasternummern `index` (siehe _ausbreiten)."""
    return a0[index] if schritt is None else a0 + schritt * index


# So viele Paare (Element, Stelle) rechnet ein Block auf einmal (P-2026-10-09-11): Ein Block
# bleibt mit allen Zwischenergebnissen im Cache des Kerns. Alle Paare auf einmal (zig Millionen
# je Zeile bei einer großen Kugel) wanderten je Rechenschritt durch den Speicher – und rechnen
# mehrere Kerne zugleich, teilen sie sich dessen Bandbreite: 24 Nebenrechner waren so nur
# 1,8-mal so schnell wie einer. Gemessen an der Kuppel (378 Zeilen, Kugel Ø 12, 65 000
# Dreiecke): allein 60 s → 24 s mit Blöcken von 32 768; auf 24 Arbeitern 6,1 s mit 32 768,
# 2,6 s mit 8192 (zwei Arbeiter teilen sich den Cache eines Kerns). Allein sind 8192 ein
# Fünftel langsamer als 32 768 – die Arbeiter sind der Regelfall.
BLOCK = 1 << 13


def _ausbreiten_bloecke(von, bis, a0, schritt, anzahl, block=None):
    """Wie _ausbreiten, aber in Blöcken von etwa `block` Paaren (BLOCK): liefert je Block
    (welches, index) – `welches` als Nummern in `von`/`bis`. Die Elemente kommen in ihrer
    Reihenfolge, so dass jeder Block aufeinanderfolgende Elemente ganz enthält."""
    if block is None:
        block = BLOCK
    if schritt is None:
        i_von = np.searchsorted(a0, von - 1e-9, side="left").astype(np.int64)
        i_bis = (np.searchsorted(a0, bis + 1e-9, side="right") - 1).astype(np.int64)
    else:
        i_von = np.maximum(np.ceil((von - a0) / schritt - 1e-9), 0).astype(np.int64)
        i_bis = np.minimum(np.floor((bis - a0) / schritt + 1e-9), anzahl - 1).astype(np.int64)
    je = np.maximum(i_bis - i_von + 1, 0)
    gesamt = int(je.sum())
    if gesamt == 0:
        return
    summe = np.cumsum(je)
    grenzen = np.searchsorted(summe, np.arange(block, gesamt, block), side="left") + 1
    anfang = 0
    for ende in [*grenzen.tolist(), len(je)]:
        if ende <= anfang:
            continue
        je_block = je[anfang:ende]
        n = int(je_block.sum())
        if n:
            beginn = np.cumsum(je_block) - je_block
            welches = np.repeat(np.arange(anfang, ende), je_block)
            index = np.repeat(i_von[anfang:ende] - beginn, je_block) + np.arange(n)
            yield welches, index
        anfang = ende


def _kanten_treffen(spalte, a, x, y, kanten, radius, a0, schritt, versatz=None):
    """Die höchste Stelle jeder Kante unter der Scheibe – an ihrem Ende oder wo sie den
    Kreis schneidet –, für alle Stellen a zugleich; in `spalte` eingetragen.

    Auch Kanten hinter der Achse (x ≤ 0) zählen: Die Spitze darf über die Achse hinaus, bis
    sie das Teil dahinter trifft (P-2026-10-03-07; bis dahin sperrte vierachs_bahn sie einen
    Fräserradius vor der Achse, und Kanten dahinter zählten nicht).

    `versatz`: je Stelle der Versatz der Werkzeugachse quer (mm, je_stellung); ohne: 0.
    """
    radius += _SAUM
    p, q = kanten[:, 0], kanten[:, 1]
    zaehlt = _im_band(np.minimum(y[p], y[q]), np.maximum(y[p], y[q]), radius, versatz)
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
    a_p, y_p, x_p = a_p[welches], y_p[welches] - _quer(versatz, index), x_p[welches]
    d_a, d_y, d_x, qa = d_a[welches], d_y[welches], d_x[welches], qa[welches]
    neben = a_p - _stelle(a0, schritt, index)
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


def _dreiecke_treffen(spalte, a, x, y, dreiecke, radius, a0, schritt, form=None, versatz=None):
    """Wo der Kreis die Ebene eines Dreiecks am höchsten schneidet und diese Stelle im
    Dreieck liegt – für alle Stellen a zugleich; in `spalte` eingetragen. Mit `form`
    (fraeserform.Form): die Stelle des Profils, die die Ebene zuerst berührt. `versatz` wie
    bei _kanten_treffen."""
    radius += _SAUM
    p, q, s = dreiecke[:, 0], dreiecke[:, 1], dreiecke[:, 2]
    unten = np.minimum(np.minimum(y[p], y[q]), y[s])
    oben = np.maximum(np.maximum(y[p], y[q]), y[s])
    zaehlt = _im_band(unten, oben, radius, versatz)  # auch hinter der Achse, wie die Kanten
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
    if versatz is not None:
        _dreiecke_versetzt(
            spalte, a, x, y, (p, q, s), (n_a, n_y, n_x), versatz_a, y_stern, hoch, form,
            a0, schritt, versatz,
        )  # fmt: skip
        return
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
    stelle_a = _stelle(a0, schritt, index) + versatz_a[auswahl]
    wert = (
        x[p]
        - (n_a[auswahl] * (stelle_a - a[p]) + n_y[auswahl] * (y_stern[auswahl] - y[p]))
        / n_x[auswahl]
    )
    if form is not None:
        wert = wert - hoch[auswahl]
    np.maximum.at(spalte, index, wert)


def _dreiecke_versetzt(
    spalte, a, x, y, ecken, normale, versatz_a, y_stern, hoch, form, a0, schritt, versatz
):
    """_dreiecke_treffen mit einem Versatz je Stelle: Die Gerade, auf der die Stirn die Ebene
    zuerst berührt, liegt dann je Stelle bei y_stern + versatz – je Paar (Dreieck, Stelle)
    geschnitten. Gepaart wird über das ganze Dreieck längs (verschoben um versatz_a)."""
    p, q, s = ecken
    n_a, n_y, n_x = normale
    a_unten = np.minimum(np.minimum(a[p], a[q]), a[s]) - versatz_a
    a_oben = np.maximum(np.maximum(a[p], a[q]), a[s]) - versatz_a
    welches, index = _ausbreiten(a_unten, a_oben, a0, schritt, len(spalte))
    if not len(index):
        return
    gerade = y_stern[welches] + versatz[index]
    s_von = np.full(len(index), math.inf)
    s_bis = np.full(len(index), -math.inf)
    for k1, k2 in ((p, q), (q, s), (s, p)):
        y1, y2 = y[k1][welches], y[k2][welches]
        dy = y2 - y1
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (gerade - y1) / dy
        auf = (np.abs(dy) > _KLEIN) & (t >= 0.0) & (t <= 1.0)
        a1, a2 = a[k1][welches], a[k2][welches]
        stelle = a1 + np.where(auf, t, 0.0) * (a2 - a1)
        s_von = np.where(auf, np.minimum(s_von, stelle), s_von)
        s_bis = np.where(auf, np.maximum(s_bis, stelle), s_bis)
    stelle_a = _stelle(a0, schritt, index) + versatz_a[welches]
    trifft = (s_von <= stelle_a + 1e-9) & (stelle_a <= s_bis + 1e-9)
    if not trifft.any():
        return
    w, i = welches[trifft], index[trifft]
    ecke = p[w]
    wert = (
        x[ecke]
        - (n_a[w] * (stelle_a[trifft] - a[ecke]) + n_y[w] * (gerade[trifft] - y[ecke])) / n_x[w]
    )
    if form is not None:
        wert = wert - hoch[w]
    np.maximum.at(spalte, i, wert)


def _im_band(unten, oben, radius, versatz):
    """Welche Elemente (quer von `unten` bis `oben`) unter einen Fräser mit `radius` kommen
    können – um die Achse (ohne Versatz) oder um irgendeinen der Versätze."""
    if versatz is None:
        return (unten <= radius) & (oben >= -radius)
    return (unten <= float(np.max(versatz)) + radius) & (oben >= float(np.min(versatz)) - radius)


def _quer(versatz, index):
    """Der Versatz quer je Paar – ohne Versatz 0."""
    return 0.0 if versatz is None else versatz[index]


# --- Jede Fräserform (V5a) -----------------------------------------------------------------

_GOLDEN = (math.sqrt(5.0) - 1.0) / 2.0
_GOLDEN_SCHRITTE = 25  # die Suche längs einer Kante: auf 1e-5 der Länge unter dem Fräser


def _form_treffen(spalte, a, x, y, kanten, dreiecke, form, a0, schritt, versatz=None):
    """Wie tief die Spitze eines Fräsers mit `form` an jeder Stelle a0 + k · schritt darf –
    gegen Ecken, Dreiecke und Kanten; in `spalte` eingetragen. `versatz`: je Stelle der
    Versatz der Werkzeugachse quer (je_stellung); ohne: 0."""
    form = form.aussen()
    radius = form.radius
    if form.eben:  # der Schaftfräser: wie immer
        _kanten_treffen(spalte, a, x, y, kanten, radius, a0, schritt, versatz)
        _dreiecke_treffen(spalte, a, x, y, dreiecke, radius, a0, schritt, versatz=versatz)
        return
    # Zuerst die Dreiecke (billig, und sie legen die Fläche unter der Spitze fest), dann Ecken
    # und Kanten nur, wo sie höher kommen können als das, was schon steht (P-2026-10-09-11).
    _dreiecke_treffen(spalte, a, x, y, dreiecke, radius, a0, schritt, form, versatz)
    _ecken_treffen(spalte, a, x, y, form, a0, schritt, versatz)
    if form.nur_kugel:
        _kanten_kugel(spalte, a, x, y, kanten, form.kugel, a0, schritt, versatz)
        return
    for rand, hoehe in form.scheiben():  # wo eine Kante unter Scheibe oder Rand herauskommt
        teil = np.full(len(spalte), KEIN_TREFFER)
        _kanten_treffen(teil, a, x, y, kanten, rand, a0, schritt, versatz)
        np.maximum(spalte, teil - hoehe, out=spalte)
    _kanten_suchen(spalte, a, x, y, kanten, form, a0, schritt, versatz)


def _ecken_treffen(spalte, a, x, y, form, a0, schritt, versatz=None):
    """Die Punkte (a, x, y) unter dem Fräser: Die Spitze darf bis x − z(Abstand) – für alle
    Stellen a zugleich; in `spalte` eingetragen. Auch Punkte hinter der Achse (x ≤ 0) zählen
    (wie bei den Kanten, P-2026-10-03-07)."""
    radius = form.radius + _SAUM
    zaehlt = np.nonzero(_im_band(y, y, radius, versatz))[0]
    if not len(zaehlt):
        return
    a_p, x_p, y_p = a[zaehlt], x[zaehlt], y[zaehlt]
    if versatz is None:
        halb = np.sqrt(np.maximum(radius * radius - y_p * y_p, 0.0))
    else:  # quer je Stelle anders: längs so weit wie der Fräser, gesiebt nach dem Abstand
        halb = np.full(len(y_p), radius)
    for welches, index in _ausbreiten_bloecke(a_p - halb, a_p + halb, a0, schritt, len(spalte)):
        # Höher als der Punkt selbst kommt die Spitze an ihm nicht: Stellen, die schon höher
        # stehen, brauchen ihn nicht.
        offen = x_p[welches] > spalte[index]
        welches, index = welches[offen], index[offen]
        if not len(index):
            continue
        abstand = np.hypot(
            a_p[welches] - _stelle(a0, schritt, index), y_p[welches] - _quer(versatz, index)
        )
        if versatz is not None:
            unter = abstand <= radius
            welches, index, abstand = welches[unter], index[unter], abstand[unter]
        wert = x_p[welches] - form.hoehe(np.minimum(abstand, form.radius))
        np.maximum.at(spalte, index, wert)


def _kanten_im_streifen(a, x, y, kanten, radius, versatz=None):
    """Die Kanten, die unter den Fräser kommen können: (p, q) Punktnummern."""
    p, q = kanten[:, 0], kanten[:, 1]
    zaehlt = _im_band(np.minimum(y[p], y[q]), np.maximum(y[p], y[q]), radius, versatz)
    return p[zaehlt], q[zaehlt]  # auch hinter der Achse (P-2026-10-03-07)


def _kanten_kugel(spalte, a, x, y, kanten, radius, a0, schritt, versatz=None):
    """Die Kugel mit `radius` (Mitte radius über der Spitze) gegen die Kanten, genau: Ihre Mitte
    liegt im Abstand radius von der Geraden der Kante – die höhere Lösung, wenn der Fußpunkt
    zwischen den Enden liegt. Die Enden selbst rechnet _ecken_treffen."""
    p, q = _kanten_im_streifen(a, x, y, kanten, radius + _SAUM, versatz)
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
    x_p, y_p = x[p], y[p]
    # Die Spitze kommt an einer Kante nie höher als deren höheres Ende (die Mitte der Kugel
    # höchstens radius darüber): Stellen, die schon höher stehen, brauchen sie nicht – an einer
    # glatten Fläche sind das nach den Dreiecken die meisten (P-2026-10-09-11). Block für
    # Block: Was ein Block eingetragen hat, spart dem nächsten Paare.
    hoechstens = np.maximum(x_p, x_p + e_x * laenge)
    for welches, index in _ausbreiten_bloecke(
        np.minimum(a_p, a_q) - radius, np.maximum(a_p, a_q) + radius, a0, schritt, len(spalte)
    ):
        offen = hoechstens[welches] > spalte[index]
        welches, index = welches[offen], index[offen]
        if not len(index):
            continue
        w_a = _stelle(a0, schritt, index) - a_p[welches]
        w_y = _quer(versatz, index) - y_p[welches]
        b_a, b_y, b_x = e_a[welches], e_y[welches], e_x[welches]
        b_quadrat, b_laenge = quadrat[welches], laenge[welches]
        laengs = w_a * b_a + w_y * b_y
        b = -2.0 * laengs * b_x
        c = w_a * w_a + w_y * w_y - laengs * laengs - radius * radius
        diskriminante = b * b - 4.0 * b_quadrat * c
        w_x = (-b + np.sqrt(np.maximum(diskriminante, 0.0))) / (2.0 * b_quadrat)
        fuss = (laengs + w_x * b_x) / b_laenge
        trifft = (diskriminante >= 0.0) & (fuss >= 0.0) & (fuss <= 1.0)
        wert = x_p[welches] + w_x - radius
        np.maximum.at(spalte, index[trifft], wert[trifft])


def _kanten_paare(spalte, a, x, y, kanten, radius, a0, schritt, versatz=None):
    """Je Kante und Stelle a das Stück der Kante unter dem Fräser (Abstand ≤ radius zur
    Werkzeugachse) – nur, wo es höher liegen kann als, was `spalte` schon hat. Gibt (Stelle,
    Anfang (a, y, x), Richtung (a, y, x), t_von, t_bis) oder None."""
    p, q = _kanten_im_streifen(a, x, y, kanten, radius, versatz)
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
    anfang = (a[p], y[p] - _quer(versatz, index), x[p])
    richtung = (a[q] - a[p], y[q] - y[p], x[q] - x[p])
    neben = anfang[0] - _stelle(a0, schritt, index)
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


def _kanten_suchen(spalte, a, x, y, kanten, form, a0, schritt, versatz=None):
    """Das Profil (konvex, fraeserform.Form.aussen) gegen die Kanten: Längs einer Kante ist x
    linear, der Abstand zur Werkzeugachse konvex und das Profil konvex und steigend –
    x − z(Abstand) also konkav. Seine höchste Stelle auf dem Stück unter dem Fräser findet der
    goldene Schnitt."""
    paare = _kanten_paare(spalte, a, x, y, kanten, form.radius, a0, schritt, versatz)
    if paare is None:
        return
    index, anfang, richtung, unten, oben = paare
    stelle = _stelle(a0, schritt, index)

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
