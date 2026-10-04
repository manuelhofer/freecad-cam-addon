# SPDX-License-Identifier: LGPL-2.1-or-later
"""Entgraten in 3D (W-015 S5): Fasen an Kanten im Raum – Manuel, 2026-10-04: „es muss schon so
sein, dass man nicht das Werkstück beschädigt“; „grundlegend auf der 5-Achs sollte das ja mit
jedem Fräser möglich sein, der unten flach ist … also bau das nicht nur auf den 45-Grad-Fräser
.. aber mit einem 45-Grad-Fräser kann man schon sehr viel auch auf einer Dreiachs-Maschine
machen“.

Je Punkt der Kante (alle SCHRITT mm) die Kante e, ihre Richtung t und die Außennormalen n1, n2
der beiden Flächen; u1, u2 laufen in den Flächen von der Kante weg. Die Fase ist eine Ebene P
(Normale nP), die die Ecke abschneidet: auf Fläche i bei e + s_i · u_i. Drei Wege:

- 5 Achsen, Fasenfräser (halber Spitzenwinkel α): P symmetrisch, nP = (n1 + n2) normiert, beide
  Schenkel `breite`. Die Achse a steht senkrecht zur Kante und um 90° − α neben nP – so liegt eine
  Mantellinie des Kegels in P. Die Mitte der Fase liegt im Abstand ρ von der Achse auf der Flanke.
- 5 Achsen, Fräser mit ebener Stirn (Schaft, Torus mit seinem ebenen Teil, Planfräser): P wie
  eben, a = nP – die Stirn liegt in P; die Fase liegt neben der Mitte der Stirn (die schneidet
  schlecht), im Abstand δ.
- 3 Achsen, Fasenfräser senkrecht (a = z): P ist die Tangentialebene des Kegels, die die Kante
  enthält – nP · z = sin α, nP ⟂ t; das geht, solange die Kante nicht steiler steigt als die
  Flanke (90° − α). Die Fase ist dann meist nicht symmetrisch: `breite` gilt auf der Fläche, die
  zum Werkzeug schaut (wie beim Entgraten an der Fräse), die andere steht im Ergebnis.

Das Werkstück darf nicht beschädigt werden: Die Flächen nahe den Kanten werden dicht abgetastet
(PUNKTABSTAND); an jeder Stelle darf kein Punkt im Werkzeug liegen (Schneide und SCHAFT mm
darüber), außer im Fasenstreifen der beiden Flächen der Kante, zwischen ihren Enden. Sonst
rutscht die Fase zur Spitze (Kegel) bzw. auf die andere Seite der Stirn; geht keine Lage, bleibt
die Stelle aus und das Ergebnis sagt, wie viel.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field

import numpy as np

from .sprache import tr

SCHRITT = 0.5  # mm – so dicht liegen die Stellen auf der Kante
PUNKTABSTAND = 0.25  # mm – so dicht wird das Teil um die Kanten abgetastet
RASTER = 2.0  # mm – Zellen für die Suche in der Punktwolke
RAND = 0.02  # mm – so tief darf ein Punkt (Rundung) im Werkzeug liegen
STREIFEN = 0.3  # mm – so weit über die Fase hinaus zählt ein Punkt der Kantenflächen noch zu ihr
SCHAFT = 15.0  # mm – so weit über der Schneide gehört der Körper noch zur Prüfung
SICHERHEIT = 2.0  # mm – so weit längs der Achse beginnt das Eintauchen
SCHARF = 15.0  # Grad – flacher geknickte Kanten sind glatt, keine Fase
GLEICH_ACHSE = 1e-4  # rad – so wenig anders gilt die Achse als gleich (gerade Stücke zusammen)
GLEICH_ORT = 1e-3  # mm
ANTEILE_KEGEL = (0.5, 0.35, 0.2, 0.08, 0.0)  # wo die Fase auf der Flanke liegt (0: an der Spitze)
ANTEILE_FLACH = (0.5, 0.3, 0.7, 0.15, 0.85)  # wo die Fase auf der Stirn liegt (Anteil des Radius)
SPRUNG = math.radians(5.0)  # dreht die Achse von Stelle zu Stelle mehr, endet der Lauf
FUENF, DREI = "fuenf", "drei"


@dataclass
class Fraeser3D:
    """Das Werkzeug: Kegel (halbwinkel > 0, `spitze` der Radius der Spitze) oder ebene Stirn
    (halbwinkel 0, `spitze` der Radius ihres ebenen Teils); `radius` außen, `schneide` lang."""

    radius: float
    halbwinkel: float = 0.0  # rad
    spitze: float = 0.0
    schneide: float = 0.0

    @property
    def kegel(self):
        return self.halbwinkel > 1e-9

    @property
    def kegelhoehe(self):
        """So hoch über der Spitze ist der Kegel auf `radius` aufgegangen (mm)."""
        if not self.kegel:
            return 0.0
        return max(self.radius - self.spitze, 0.0) / math.tan(self.halbwinkel)

    def radius_bei(self, h):
        """Radius des Werkzeugkörpers in der Höhe h über der Spitze (numpy)."""
        h = np.asarray(h, dtype=float)
        if self.kegel:
            return np.minimum(
                self.spitze + np.maximum(h, 0.0) * math.tan(self.halbwinkel), self.radius
            )
        return np.full(h.shape, self.radius)

    @property
    def hoehe(self):
        """So hoch über der Spitze wird der Körper geprüft."""
        return max(self.schneide, self.kegelhoehe) + SCHAFT


@dataclass
class Werte3D:
    fraeser: Fraeser3D
    breite: float  # mm – die Fase auf der Fläche (3 Achsen: auf der zum Werkzeug)
    art: str = FUENF  # FUENF oder DREI
    sicher: float = 50.0  # z für die Eilgänge über allem
    sicherheit: float = SICHERHEIT
    gleichlauf: bool = True
    vorschub: float = 0.0  # mm/min – für die Zeit
    # z des Tischs: Kein Teil des Werkzeugs darf darunter (er steht nicht im Modell); None: die
    # Unterkante des Teils.
    tisch: float = None


@dataclass
class Stelle:
    """Ein Punkt der Bahn: die Spitze (die Mitte der Stirn), die Werkzeugachse, wie hierher."""

    spitze: tuple
    achse: tuple
    eilgang: bool = False
    eintauchen: bool = False


@dataclass
class Bahn3D:
    punkte: list  # [Stelle]
    kanten: int  # Kanten mit Fase
    laenge: float  # mm Fase
    ausgelassen: float  # mm Kante ohne Fase
    gruende: dict = field(default_factory=dict)  # Grund → mm
    schenkel: tuple = (0.0, 0.0)  # (kleinster, größter) Schenkel – bei 3 Achsen ungleich
    neigung: float = 0.0  # Grad – die größte Neigung der Achse gegen z
    zeit: float = 0.0  # min im Vorschub


ENG, STEIL, KEINE_STELLUNG, ANFAHRT = "eng", "steil", "keine", "anfahrt"


# --- Die Kanten ------------------------------------------------------------------------------


@dataclass
class Kante3D:
    name: str
    kante: object  # Part.Edge
    flaechen: tuple  # (Part.Face, Part.Face)
    nummern: tuple  # ihre Nummern im Teil (0, 1, …)
    vorzeichen: tuple  # je Fläche ±1: normalAt mal das zeigt nach außen


def _normale(flaeche, p, vorzeichen=1.0):
    u, v = flaeche.Surface.parameter(p)
    n = flaeche.normalAt(u, v)
    return np.array([n.x, n.y, n.z]) * vorzeichen


def _nach_aussen(form, flaeche, p):
    """±1: so zeigt normalAt der Fläche an p aus dem Teil hinaus."""
    import FreeCAD

    n = _normale(flaeche, p)
    probe = FreeCAD.Vector(*(np.array([p.x, p.y, p.z]) + 0.02 * n))
    return -1.0 if form.isInside(probe, 1e-6, False) else 1.0


def kanten(form, namen):
    """[Kante3D] – die konvexen, scharfen Kanten der gewählten Flächen („Face3“: ihre Kanten) und
    Kanten („Edge7“), ohne die auf dem Tisch (an einer Fläche ganz unten, die nach unten zeigt)."""
    import FreeCAD
    import Part

    z_unten = form.BoundBox.ZMin
    gesucht = []
    for name in namen:
        if name.startswith("Face"):
            for kante in form.getElement(name).Edges:
                gesucht.append(kante)
        elif name.startswith("Edge"):
            gesucht.append(form.getElement(name))
    ergebnis, gesehen = [], set()
    for kante in gesucht:
        nummer = next((i for i, k in enumerate(form.Edges) if k.isSame(kante)), None)
        if nummer is None or nummer in gesehen or kante.Length < 2 * SCHRITT:
            continue
        gesehen.add(nummer)
        flaechen = form.ancestorsOfType(form.Edges[nummer], Part.Face)
        if len(flaechen) != 2:
            continue
        mitte = kante.valueAt(
            kante.FirstParameter + 0.5 * (kante.LastParameter - kante.FirstParameter)
        )
        vorzeichen = tuple(_nach_aussen(form, f, mitte) for f in flaechen)
        n1, n2 = (_normale(f, mitte, s) for f, s in zip(flaechen, vorzeichen, strict=True))
        if any(
            n[2] < -0.999 and abs(f.BoundBox.ZMax - z_unten) < 1e-3
            for n, f in zip((n1, n2), flaechen, strict=True)
        ):
            continue  # auf dem Tisch
        winkel = math.degrees(math.acos(max(-1.0, min(1.0, float(n1 @ n2)))))
        if winkel < SCHARF:
            continue  # glatt
        c = (n1 + n2) / np.linalg.norm(n1 + n2)
        p = np.array([mitte.x, mitte.y, mitte.z])
        if form.isInside(FreeCAD.Vector(*(p + 0.05 * c)), 1e-6, False):
            continue  # Innenkante
        nummern = tuple(next(i for i, f in enumerate(form.Faces) if f.isSame(g)) for g in flaechen)
        ergebnis.append(Kante3D(f"Edge{nummer + 1}", kante, tuple(flaechen), nummern, vorzeichen))
    return ergebnis


# --- Die Punktwolke ----------------------------------------------------------------------------


class Wolke:
    """Punkte auf den Flächen (je Punkt die Nummer seiner Fläche), in Zellen von RASTER mm."""

    def __init__(self, punkte, flaechen):
        self.punkte = np.asarray(punkte, dtype=float).reshape(-1, 3)
        self.flaechen = np.asarray(flaechen, dtype=np.int64)
        self._unten = self.punkte.min(axis=0) if len(self.punkte) else np.zeros(3)
        zellen = np.floor((self.punkte - self._unten) / RASTER).astype(np.int64)
        self._n = zellen.max(axis=0) + 1 if len(zellen) else np.ones(3, dtype=np.int64)
        schluessel = (zellen[:, 0] * self._n[1] + zellen[:, 1]) * self._n[2] + zellen[:, 2]
        self._ordnung = np.argsort(schluessel, kind="stable")
        self._schluessel = schluessel[self._ordnung]

    def nah(self, unten, oben):
        """Die Nummern der Punkte in den Zellen, die den Quader unten … oben berühren."""
        if not len(self.punkte):
            return np.zeros(0, dtype=np.int64)
        a = np.floor((np.asarray(unten) - self._unten) / RASTER).astype(np.int64)
        b = np.floor((np.asarray(oben) - self._unten) / RASTER).astype(np.int64)
        a = np.maximum(a, 0)
        b = np.minimum(b, self._n - 1)
        if np.any(b < a):
            return np.zeros(0, dtype=np.int64)
        teile = []
        for i in range(a[0], b[0] + 1):
            for j in range(a[1], b[1] + 1):
                von = (i * self._n[1] + j) * self._n[2] + a[2]
                bis = (i * self._n[1] + j) * self._n[2] + b[2]
                k0 = np.searchsorted(self._schluessel, von, "left")
                k1 = np.searchsorted(self._schluessel, bis, "right")
                if k1 > k0:
                    teile.append(self._ordnung[k0:k1])
        return np.concatenate(teile) if teile else np.zeros(0, dtype=np.int64)


def wolke(form, kanten_, reichweite, punktabstand=PUNKTABSTAND):
    """Die Wolke der Flächen, die näher als `reichweite` an einer der Kanten liegen – Punkte
    etwa alle `punktabstand` mm."""
    if not kanten_:
        return Wolke(np.zeros((0, 3)), np.zeros(0))
    boxen = [k.kante.BoundBox for k in kanten_]
    punkte, nummern = [], []
    for nummer, flaeche in enumerate(form.Faces):
        fb = flaeche.BoundBox
        nah = any(
            fb.XMin - reichweite <= b.XMax
            and b.XMin <= fb.XMax + reichweite
            and fb.YMin - reichweite <= b.YMax
            and b.YMin <= fb.YMax + reichweite
            and fb.ZMin - reichweite <= b.ZMax
            and b.ZMin <= fb.ZMax + reichweite
            for b in boxen
        )
        if not nah:
            continue
        ecken, dreiecke = flaeche.tessellate(0.01)
        if not dreiecke:
            continue
        e = np.array([[v.x, v.y, v.z] for v in ecken])
        d = np.array(dreiecke, dtype=np.int64)
        a, b, c = e[d[:, 0]], e[d[:, 1]], e[d[:, 2]]
        flaechen_ = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        anzahl = np.maximum(1, np.ceil(flaechen_ / punktabstand**2).astype(np.int64))
        # Je Dreieck gleichmäßig verteilte Punkte (baryzentrisch, ein festes Muster je Anzahl).
        welches = np.repeat(np.arange(len(d)), anzahl)
        rng = np.random.default_rng(nummer)
        r1 = np.sqrt(rng.random(len(welches)))
        r2 = rng.random(len(welches))
        p = (
            (1 - r1)[:, None] * a[welches]
            + (r1 * (1 - r2))[:, None] * b[welches]
            + (r1 * r2)[:, None] * c[welches]
        )
        punkte.append(np.vstack([p, e]))
        nummern.append(np.full(len(p) + len(e), nummer))
    if not punkte:
        return Wolke(np.zeros((0, 3)), np.zeros(0))
    return Wolke(np.vstack(punkte), np.concatenate(nummern))


# --- Die Stellung an einem Punkt ----------------------------------------------------------------


@dataclass
class Lage:
    """Wie das Werkzeug an einem Punkt der Kante steht."""

    spitze: np.ndarray
    achse: np.ndarray
    normale: np.ndarray  # der Fase
    tiefe: float  # die Fase liegt so weit unter der Kante (längs normale)
    schenkel: tuple  # (s1, s2)


def _geometrie(k, parameter):
    """(e, t, n1, n2, u1, u2) an der Stelle `parameter` der Kante."""
    p = k.kante.valueAt(parameter)
    t = k.kante.tangentAt(parameter)
    e = np.array([p.x, p.y, p.z])
    t = np.array([t.x, t.y, t.z])
    t /= np.linalg.norm(t)
    n1, n2 = (_normale(f, p, s) for f, s in zip(k.flaechen, k.vorzeichen, strict=True))
    u1 = np.cross(t, n1)
    u1 /= np.linalg.norm(u1)
    if u1 @ n2 > 0:
        u1 = -u1
    u2 = np.cross(t, n2)
    u2 /= np.linalg.norm(u2)
    if u2 @ n1 > 0:
        u2 = -u2
    return e, t, n1, n2, u1, u2


def _fase(e, t, n1, n2, u1, u2, w):
    """(nP, d, s1, s2, oder ein Grund) – die Fasenebene."""
    z = np.array([0.0, 0.0, 1.0])
    if w.art == FUENF:
        n_p = (n1 + n2) / np.linalg.norm(n1 + n2)
        d = -w.breite * float(n_p @ u1)
        return n_p, d, w.breite, w.breite, None
    f = w.fraeser
    if not f.kegel:
        return None, 0, 0, 0, KEINE_STELLUNG
    alpha = f.halbwinkel
    th = t - (t @ z) * z
    laenge_h = float(np.linalg.norm(th))
    if laenge_h < 1e-6:
        return None, 0, 0, 0, STEIL
    kappa = -math.tan(alpha) * float(t @ z) / laenge_h
    if abs(kappa) > 1.0:
        return None, 0, 0, 0, STEIL  # steiler als die Flanke
    th /= laenge_h
    quer = np.cross(z, th)
    beste = None
    for mu in (math.sqrt(1 - kappa * kappa), -math.sqrt(1 - kappa * kappa)):
        h = kappa * th + mu * quer
        n_p = math.sin(alpha) * z + math.cos(alpha) * h
        if n_p @ u1 >= -1e-6 or n_p @ u2 >= -1e-6:
            continue  # die Ebene schnitte eine der Flächen nicht hinter der Kante ab
        if beste is None or n_p @ (n1 + n2) > beste @ (n1 + n2):
            beste = n_p
    if beste is None:
        return None, 0, 0, 0, KEINE_STELLUNG
    # Die Breite auf der Fläche, die zum Werkzeug schaut (wie das Entgraten an der Fräse).
    oben = u1 if n1 @ z >= n2 @ z else u2
    d = -w.breite * float(beste @ oben)
    s1, s2 = -d / float(beste @ u1), -d / float(beste @ u2)
    return beste, d, s1, s2, None


def _lagen(e, t, n_p, d, s1, s2, u1, u2, w, vorher=None):
    """Die möglichen Lagen (Lage) für diese Fase, die beste zuerst."""
    f = w.fraeser
    z = np.array([0.0, 0.0, 1.0])
    q1, q2 = e + s1 * u1, e + s2 * u2
    m = 0.5 * (q1 + q2)
    g = q2 - q1
    breit = float(np.linalg.norm(g))
    g = g / breit if breit > 1e-9 else np.cross(n_p, t)
    ergebnis = []
    if f.kegel:
        alpha = f.halbwinkel
        if w.art == DREI:
            achsen = [z]
        else:
            achsen = [
                math.sin(alpha) * n_p + math.cos(alpha) * g,
                math.sin(alpha) * n_p - math.cos(alpha) * g,
            ]
            if vorher is not None:
                achsen.sort(key=lambda a: -float(a @ vorher))
            else:
                achsen.sort(key=lambda a: -float(a[2]))
            achsen = achsen[:1]  # stetig: die eine Seite
        for a in achsen:
            a = a / np.linalg.norm(a)
            radial = n_p - (n_p @ a) * a
            if np.linalg.norm(radial) < 1e-9:
                continue
            w_r = -radial / np.linalg.norm(radial)  # von der Achse zur Berührung
            mantel = a - (a @ n_p) * n_p
            mantel /= np.linalg.norm(mantel)
            quer_anteil = abs(float(mantel @ g)) or 1e-9
            halb = 0.5 * breit * math.sin(alpha) / quer_anteil  # radial über die halbe Fase
            unten, oben = f.spitze + halb, f.radius - halb
            if oben < unten:
                continue
            for anteil in ANTEILE_KEGEL:
                rho = unten + anteil * (oben - unten)
                h = (rho - f.spitze) / math.tan(alpha)
                spitze = m - h * a - rho * w_r
                ergebnis.append(Lage(spitze, a, n_p, d, (s1, s2)))
    else:
        a = n_p
        r_eben = f.spitze
        for anteil in ANTEILE_FLACH:
            mitte = anteil * r_eben
            if mitte + 0.5 * breit > r_eben or mitte - 0.5 * breit < 0.1 * r_eben:
                continue
            seiten = [g, -g]
            seiten.sort(key=lambda v: -float(v[2]))
            for v in seiten:
                spitze = m + mitte * v
                ergebnis.append(Lage(spitze, a, n_p, d, (s1, s2)))
    return ergebnis


def _unter_dem_tisch(spitze, achse, fraeser, tisch):
    """So tief (mm) reicht das Werkzeug unter den Tisch – 0: nicht (oder kein Tisch)."""
    if tisch is None or tisch == -math.inf:
        return 0.0
    quer = math.sqrt(max(0.0, 1.0 - float(achse[2]) ** 2))
    oben = spitze + fraeser.hoehe * achse
    tiefste = min(float(spitze[2]) - fraeser.spitze * quer, float(oben[2]) - fraeser.radius * quer)
    return max(0.0, tisch - tiefste)


def _verletzung(lage, e, t, k, w, wolke_, enden):
    """Wie tief (mm) das Werkzeug in dieser Lage in das Teil (oder unter den Tisch) schnitte –
    außerhalb des Fasenstreifens; 0: nirgends."""
    f = w.fraeser
    a = lage.achse
    hoehe = f.hoehe
    tisch = _unter_dem_tisch(lage.spitze, a, f, w.tisch)
    if tisch > RAND:
        return tisch
    ecken = np.array([lage.spitze, lage.spitze + hoehe * a])
    unten = ecken.min(axis=0) - f.radius
    oben = ecken.max(axis=0) + f.radius
    nummern = wolke_.nah(unten, oben)
    if not len(nummern):
        return 0.0
    x = wolke_.punkte[nummern]
    rel = x - lage.spitze
    h = rel @ a
    radial = np.linalg.norm(rel - np.outer(h, a), axis=1)
    innen = (h > -RAND) & (h < hoehe) & (radial < f.radius_bei(h) - RAND)
    # Die Stirn: flach schneidet sie nur bis zu ihrer Ebene, der Kegel bis zur Spitze.
    if not innen.any():
        return 0.0
    # Erlaubt: auf den Flächen der Kante, auf der Seite der Fase, nahe der Kante, zwischen ihren
    # Enden.
    eigene = np.isin(wolke_.flaechen[nummern], k.nummern)
    ueber = (x - e) @ lage.normale >= -lage.tiefe - RAND
    quer = (x - e) - np.outer((x - e) @ t, t)
    nahe = np.linalg.norm(quer, axis=1) <= max(lage.schenkel) + STREIFEN
    (p0, t0), (p1, t1) = enden
    zwischen = ((x - p0) @ t0 >= -RAND) & ((p1 - x) @ t1 >= -RAND)
    erlaubt = eigene & ueber & nahe & zwischen
    schlecht = innen & ~erlaubt
    if not schlecht.any():
        return 0.0
    return float(np.max(f.radius_bei(h[schlecht]) - radial[schlecht]))


# --- Die Bahn ---------------------------------------------------------------------------------


def _stellen_der_kante(k, w, wolke_, schritt=SCHRITT):
    """[(Parameter, Lage oder None, Grund)] entlang der Kante, etwa alle `schritt` mm."""
    kurve = k.kante
    anzahl = max(2, int(math.ceil(kurve.Length / schritt)) + 1)
    parameter = np.linspace(kurve.FirstParameter, kurve.LastParameter, anzahl)

    def ende(prm, richtung):
        p = kurve.valueAt(prm)
        tt = kurve.tangentAt(prm)
        tt = np.array([tt.x, tt.y, tt.z]) * richtung
        return np.array([p.x, p.y, p.z]), tt / np.linalg.norm(tt)

    enden = (ende(parameter[0], 1.0), ende(parameter[-1], 1.0))
    ergebnis = []
    vorher = None
    for prm in parameter:
        e, t, n1, n2, u1, u2 = _geometrie(k, prm)
        n_p, d, s1, s2, grund = _fase(e, t, n1, n2, u1, u2, w)
        if grund is not None:
            ergebnis.append((prm, None, grund))
            continue
        gewaehlt, tiefste = None, math.inf
        for lage in _lagen(e, t, n_p, d, s1, s2, u1, u2, w, vorher):
            tief = _verletzung(lage, e, t, k, w, wolke_, enden)
            if tief <= 0.0:
                gewaehlt = lage
                break
            tiefste = min(tiefste, tief)
        if gewaehlt is None:
            ergebnis.append((prm, None, ENG if tiefste < math.inf else KEINE_STELLUNG))
            continue
        vorher = gewaehlt.achse
        ergebnis.append((prm, gewaehlt, None))
    return ergebnis


def _laeufe(stellen, kurve):
    """[[Lage …]] – zusammenhängende Stücke mit Lage; dazu {Grund: mm} ohne. Springt die Achse
    zwischen zwei Stellen um mehr als SPRUNG, beginnt ein neues Stück – dazwischen stünde das
    Werkzeug ungeprüft."""
    laeufe, aktuell, gruende = [], [], {}
    schritt = kurve.Length / max(len(stellen) - 1, 1)
    for _prm, lage, grund in stellen:
        if lage is None:
            gruende[grund] = gruende.get(grund, 0.0) + schritt
            if len(aktuell) >= 2:
                laeufe.append(aktuell)
            aktuell = []
            continue
        if aktuell and _winkel(aktuell[-1].achse, lage.achse) > SPRUNG:
            if len(aktuell) >= 2:
                laeufe.append(aktuell)
            aktuell = []
        aktuell.append(lage)
    if len(aktuell) >= 2:
        laeufe.append(aktuell)
    return laeufe, gruende


def _winkel(a, b):
    return math.acos(max(-1.0, min(1.0, float(a @ b))))


def _stelle_frei(wolke_, fraeser, spitze, achse, tisch=-math.inf):
    """Berührt das Werkzeug mit der Spitze hier und dieser Achse nichts vom Teil (und bleibt über
    dem Tisch)?"""
    if _unter_dem_tisch(spitze, achse, fraeser, tisch) > RAND:
        return False
    ecken = np.array([spitze, spitze + fraeser.hoehe * achse])
    nummern = wolke_.nah(ecken.min(axis=0) - fraeser.radius, ecken.max(axis=0) + fraeser.radius)
    if not len(nummern):
        return True
    rel = wolke_.punkte[nummern] - spitze
    h = rel @ achse
    radial = np.linalg.norm(rel - np.outer(h, achse), axis=1)
    return not np.any((h > -RAND) & (h < fraeser.hoehe) & (radial < fraeser.radius_bei(h) - RAND))


def _frei(wolke_, fraeser, von, bis, achse, tisch=-math.inf):
    """Berührt das Werkzeug (Achse fest) auf dem Weg der Spitze von → bis nichts vom Teil?"""
    laenge = float(np.linalg.norm(bis - von))
    return all(
        _stelle_frei(wolke_, fraeser, von + s * (bis - von), achse, tisch)
        for s in np.linspace(0.0, 1.0, max(2, int(math.ceil(laenge)) + 1))
    )


def _anfahrt(lage, w, wolke_):
    """(oben, vor) – `vor`: längs der Achse so weit zurück, dass das Werkzeug nichts berührt,
    und `sicherheit` dazu (das Eintauchen von dort bleibt im Körper der Schnittstellung – ein
    Kegel oder Zylinder, längs seiner Achse zurückgezogen, liegt in sich selbst); `oben`: auf der
    sicheren Höhe darüber, der Weg hinab frei – senkrecht, sonst längs der Achse. None, wenn
    keiner frei ist."""
    a = lage.achse
    zurueck = 0.0
    while not _stelle_frei(wolke_, w.fraeser, lage.spitze + zurueck * a, a, w.tisch):
        zurueck += 0.5
        if zurueck > w.fraeser.hoehe:
            return None
    vor = lage.spitze + (zurueck + w.sicherheit) * a
    oben = np.array([vor[0], vor[1], max(w.sicher, float(vor[2]))])
    if _frei(wolke_, w.fraeser, oben, vor, a, w.tisch):
        return oben, vor
    if a[2] > 0.1:
        weit = vor + a * max(0.0, (w.sicher - float(vor[2])) / float(a[2]))
        if _frei(wolke_, w.fraeser, weit, vor, a, w.tisch):
            return weit, vor
    return None


def _ausgeduennt(lagen):
    """Die Lagen ohne die, die auf der Geraden zwischen ihren Nachbarn liegen (gleiche Achse)."""
    if len(lagen) <= 2:
        return list(lagen)
    bleibt = [lagen[0]]
    for i in range(1, len(lagen) - 1):
        a, b, c = bleibt[-1], lagen[i], lagen[i + 1]
        gleich = (
            float(np.linalg.norm(a.achse - b.achse)) < GLEICH_ACHSE
            and float(np.linalg.norm(b.achse - c.achse)) < GLEICH_ACHSE
        )
        if gleich:
            ac = c.spitze - a.spitze
            laenge = float(np.linalg.norm(ac))
            if laenge > 1e-9:
                ab = b.spitze - a.spitze
                abstand = float(np.linalg.norm(ab - (ab @ ac) / laenge**2 * ac))
                if abstand < GLEICH_ORT:
                    continue
        bleibt.append(b)
    bleibt.append(lagen[-1])
    return bleibt


def _gleichlauf(lauf, w):
    """Der Lauf in der Richtung, in der der Fräser (M3) im Gleichlauf schneidet: das Teil rechts
    der Fahrt, von oben längs der Achse gesehen."""
    if len(lauf) < 2:
        return lauf
    a = lauf[0].achse
    fahrt = lauf[1].spitze - lauf[0].spitze
    zum_teil = -lauf[0].normale
    rechts = float(np.cross(fahrt, a) @ zum_teil) > 0
    return lauf if rechts == bool(w.gleichlauf) else list(reversed(lauf))


def planen(form, namen, werte, schritt=SCHRITT, punktabstand=PUNKTABSTAND):
    """Die Bahn (Bahn3D) für die gewählten Flächen und Kanten `namen` von `form` – die Stellen
    etwa alle `schritt` mm, das Teil alle `punktabstand` mm abgetastet (gröber für die Vorschau im
    Assistenten). ValueError mit einem Satz, wenn es nichts zu fasen gibt."""
    w = werte
    if w.tisch is None:
        from dataclasses import replace

        w = replace(w, tisch=float(form.BoundBox.ZMin))
    if w.breite <= 0 or w.fraeser.radius <= 0:
        raise ValueError(tr("e3.fehler.werte"))
    if w.art == DREI and not w.fraeser.kegel:
        raise ValueError(tr("e3.fehler.drei_flach"))
    kanten_ = kanten(form, namen)
    if not kanten_:
        raise ValueError(tr("e3.fehler.keine"))
    wolke_ = wolke(form, kanten_, w.fraeser.hoehe + w.fraeser.radius, punktabstand)
    laeufe, gruende = [], {}
    laenge = 0.0
    gefast = 0
    schenkel = []
    for k in kanten_:
        stellen = _stellen_der_kante(k, w, wolke_, schritt)
        teile, ohne = _laeufe(stellen, k.kante)
        for grund, mm in ohne.items():
            gruende[grund] = gruende.get(grund, 0.0) + mm
        if teile:
            gefast += 1
        for lauf in teile:
            lauf = _gleichlauf(lauf, w)
            hinein, heraus = _anfahrt(lauf[0], w, wolke_), _anfahrt(lauf[-1], w, wolke_)
            mm = (len(lauf) - 1) * k.kante.Length / max(len(stellen) - 1, 1)  # längs der Kante
            if hinein is None or heraus is None:
                gruende[ANFAHRT] = gruende.get(ANFAHRT, 0.0) + mm
                continue
            schenkel.extend(min(lage.schenkel) for lage in lauf)
            schenkel.extend(max(lage.schenkel) for lage in lauf)
            laeufe.append((_ausgeduennt(lauf), hinein, heraus))
            laenge += mm
    if not laeufe:
        raise ValueError(tr("e3.fehler.nichts"))
    punkte = _verbinden(laeufe, w)
    neigung = max(
        math.degrees(math.acos(max(-1.0, min(1.0, float(lage.achse[2])))))
        for lauf, _hinein, _heraus in laeufe
        for lage in lauf
    )
    vorschub = w.vorschub or 1000.0
    return Bahn3D(
        punkte,
        gefast,
        laenge,
        sum(gruende.values()),
        gruende,
        (min(schenkel), max(schenkel)) if schenkel else (0.0, 0.0),
        neigung,
        laenge / vorschub,
    )


def _verbinden(laeufe, w):
    """Die Läufe der Reihe nach (der nächste zuerst): über dem Anfang (_anfahrt), längs der Achse
    `sicherheit` davor, eintauchen, der Lauf, längs der Achse heraus, hinauf."""
    punkte = []
    offen = list(laeufe)
    ort = None
    while offen:
        if ort is None:
            k = 0
        else:
            k = min(
                range(len(offen)), key=lambda i: float(np.linalg.norm(offen[i][0][0].spitze - ort))
            )
        lauf, (oben, vor), (oben_nach, nach) = offen.pop(k)
        erste, letzte = lauf[0], lauf[-1]

        def stelle(p, lage, eilgang=False, eintauchen=False):
            return Stelle(
                tuple(float(v) for v in p), tuple(float(v) for v in lage.achse), eilgang, eintauchen
            )

        punkte.append(stelle(oben, erste, True))
        punkte.append(stelle(vor, erste, True))
        punkte.append(stelle(erste.spitze, erste, eintauchen=True))
        for lage in lauf[1:]:
            punkte.append(stelle(lage.spitze, lage))
        punkte.append(stelle(nach, letzte))
        punkte.append(stelle(oben_nach, letzte, True))
        ort = letzte.spitze
    return punkte
