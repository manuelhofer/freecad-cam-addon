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
(PUNKTABSTAND); an jeder Stelle darf kein Punkt in der Schneide liegen, außer im Fasenstreifen der
beiden Flächen der Kante, zwischen ihren Enden – und an einer Ecke im Dreieck der Fläche, die die
Kante abschließt (_kappen): Dort läuft die Fase bis zur Ecke durch. Sonst rutscht die Fase zur Spitze (Kegel) bzw. auf
die andere Seite der Stirn; geht keine Lage, bleibt die Stelle aus und das Ergebnis sagt, wie viel.

Schaft und Halter (Aufbau, aus der Werkzeugverwaltung wie „Auf der Maschine prüfen“) bleiben
ABSTAND vom ganzen Teil (grob abgetastet, GROB), alles samt Spindel ABSTAND über dem Tisch – die
Kollisionsprüfung fand am Schwenkteil Spindel und Halter im Rundtisch, wo der Kegel an einer
senkrechten Kante dicht über dem Tisch waagrecht lag. Der Kegel darf dafür um die Normale der
Fase kippen (NEIGEN): Seine Mantellinie läuft dann schräg über die Fase, die Ebene bleibt dieselbe.

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
SCHAFT = 15.0  # mm – ohne Aufbau: so weit über der Schneide gehört der Körper noch zur Prüfung
# mm – so viel Luft lassen Schaft und Halter zum Teil und das ganze Werkzeug zum Tisch (mehr als
# die Warnung der Kollisionsprüfung, 1 mm)
ABSTAND = 1.5
GROB = 1.0  # mm – so dicht wird das ganze Teil für Schaft und Halter abgetastet
RASTER_GROB = 8.0  # mm – die Zellen dafür
# Die Spindel über dem Halter, nur gegen den Tisch (die Maschine kennt die Bahn nicht; die
# Beispielmaschinen haben 45 bis 55 mm).
KOPF_RADIUS = 60.0
KOPF_LAENGE = 150.0
NEIGEN = (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60)  # Grad – so kippt der Kegel um nP
SICHERHEIT = 2.0  # mm – so weit längs der Achse beginnt das Eintauchen
SCHARF = 15.0  # Grad – flacher geknickte Kanten sind glatt, keine Fase
GLEICH_ACHSE = 1e-4  # rad – so wenig anders gilt die Achse als gleich (gerade Stücke zusammen)
GLEICH_ORT = 1e-3  # mm
ANTEILE_KEGEL = (0.5, 0.35, 0.2, 0.08, 0.0)  # wo die Fase auf der Flanke liegt (0: an der Spitze)
ANTEILE_FLACH = (0.5, 0.3, 0.7, 0.15, 0.85)  # wo die Fase auf der Stirn liegt (Anteil des Radius)
KAPPE = 0.2  # so weit zeigt eine Fläche am Ende der Kante hinaus (cos), dann schließt sie sie ab
KAPPE_WEIT = 3.0  # so weit (mal Schenkel und STREIFEN) vom Ende zählen ihre Punkte zur Fase
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
    def schneidhoehe(self):
        """So hoch über der Spitze reicht die Schneide."""
        return max(self.schneide, self.kegelhoehe)

    @property
    def hoehe(self):
        """So hoch über der Spitze wird der Körper ohne Aufbau geprüft."""
        return self.schneidhoehe + SCHAFT


@dataclass
class Aufbau:
    """Was über der Schneide sitzt: Schaft und Halter als Kegelstümpfe (h0, h1, r0, r1 – mm über
    der Spitze, von unten nach oben), ab `kopf` die Spindel (KOPF_RADIUS, nur gegen den Tisch)."""

    stuecke: list
    kopf: float


def aufbau(halter, schaft, auskragung, fraeser):
    """Der Aufbau aus einem geraden Halter (halter.Halter), dem Radius des Schafts und der
    Auskragung (von der Nase des Halters bis zur Spitze, mm) – wie wegkippen.einspannung sie
    liefert."""
    unten = fraeser.schneidhoehe
    stuecke = []
    if auskragung > unten and schaft > 0:
        stuecke.append((unten, float(auskragung), float(schaft), float(schaft)))
    kopf = float(auskragung) + float(halter.laenge)
    h = kopf
    for a in halter.abschnitte:  # von der Spindelnase zum Werkzeug hin
        if a.laenge <= 0:
            continue
        h0, h1 = h - a.laenge, h
        h = h0
        if h1 <= unten:
            continue
        r0, r1 = a.d_unten / 2.0, a.d_oben / 2.0
        if h0 < unten:  # reichte in die Schneide – dort steckt kein Halter
            r0 = r0 + (r1 - r0) * (unten - h0) / (h1 - h0)
            h0 = unten
        stuecke.append((float(h0), float(h1), float(r0), float(r1)))
    stuecke.sort()
    return Aufbau(stuecke, kopf)


@dataclass
class Werte3D:
    fraeser: Fraeser3D
    breite: float  # mm – die Fase auf der Fläche (3 Achsen: auf der zum Werkzeug)
    art: str = FUENF  # FUENF oder DREI
    sicher: float = 50.0  # z für die Eilgänge über allem
    sicherheit: float = SICHERHEIT
    gleichlauf: bool = True
    vorschub: float = 0.0  # mm/min – für die Zeit
    # z des Tischs: Kein Teil des Werkzeugs kommt ihm näher als ABSTAND (er steht nicht im
    # Modell); None: die Unterkante des Teils.
    tisch: float = None
    aufbau: Aufbau = None  # None: nur die Schneide und SCHAFT mm darüber


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
TISCH, HALTER = "tisch", "halter"


# --- Die Kanten ------------------------------------------------------------------------------


@dataclass
class Kante3D:
    name: str
    kante: object  # Part.Edge
    flaechen: tuple  # (Part.Face, Part.Face)
    nummern: tuple  # ihre Nummern im Teil (0, 1, …)
    vorzeichen: tuple  # je Fläche ±1: normalAt mal das zeigt nach außen
    # Je Ende (Anfang, Ende der Kurve) die Flächen, die die Kante dort abschließen (_kappen).
    kappen: tuple = ((), ())


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
        # Konvex: Von der Kante ein Stück über Fläche 1 hinaus (+n1) und von Fläche 2 weg (−n2)
        # liegt Luft – an einer Innenkante (Boden an einer Wand) das Material der anderen Fläche.
        # Die Winkelhalbierende der Normalen taugt dafür nicht: Sie zeigt an beiden ins Freie.
        d = (n1 - n2) / np.linalg.norm(n1 - n2)
        p = np.array([mitte.x, mitte.y, mitte.z])
        if any(form.isInside(FreeCAD.Vector(*(p + 0.05 * r)), 1e-6, False) for r in (d, -d)):
            continue  # Innenkante
        nummern = tuple(next(i for i, f in enumerate(form.Faces) if f.isSame(g)) for g in flaechen)
        kappen = tuple(_kappen(form, form.Edges[nummer], nummern, ende) for ende in (0, 1))
        ergebnis.append(
            Kante3D(f"Edge{nummer + 1}", kante, tuple(flaechen), nummern, vorzeichen, kappen)
        )
    return ergebnis


def _kappen(form, kante, nummern, ende):
    """Die Nummern der Flächen, die die Kante am Anfang (0) bzw. Ende (1) abschließen: Ihre
    Außennormale zeigt dort über das Ende hinaus – eine Ecke des Teils, keine Wand, an der die
    Kante endet. Dort darf die Fase durchlaufen und das Dreieck jenseits der Fasenebene aus der
    Fläche nehmen (wie jede Fase, die bis zur Ecke geht); an einer Wand hört sie vorher auf."""
    import FreeCAD
    import Part

    prm = kante.FirstParameter if ende == 0 else kante.LastParameter
    p = kante.valueAt(prm)
    t = kante.tangentAt(prm)
    hinaus = np.array([t.x, t.y, t.z]) * (-1.0 if ende == 0 else 1.0)
    hinaus /= np.linalg.norm(hinaus)
    ecke = next((v for v in kante.Vertexes if v.Point.distanceToPoint(p) < 1e-6), None)
    if ecke is None:
        return ()
    ergebnis = []
    for flaeche in form.ancestorsOfType(ecke, Part.Face):
        nummer = next((i for i, f in enumerate(form.Faces) if f.isSame(flaeche)), None)
        if nummer is None or nummer in nummern or nummer in ergebnis:
            continue
        ecken, dreiecke = flaeche.tessellate(0.1)
        if not dreiecke:
            continue
        mitte = sum((ecken[i] for i in dreiecke[0]), FreeCAD.Vector()) * (1.0 / 3.0)
        n = _normale(flaeche, p, _nach_aussen(form, flaeche, mitte))
        if float(n @ hinaus) > KAPPE:
            ergebnis.append(nummer)
    return tuple(ergebnis)


# --- Die Punktwolke ----------------------------------------------------------------------------


class Wolke:
    """Punkte auf den Flächen (je Punkt die Nummer seiner Fläche), in Zellen von `raster` mm."""

    def __init__(self, punkte, flaechen, raster=RASTER):
        self.punkte = np.asarray(punkte, dtype=float).reshape(-1, 3)
        self.flaechen = np.asarray(flaechen, dtype=np.int64)
        self.raster = float(raster)
        self._unten = self.punkte.min(axis=0) if len(self.punkte) else np.zeros(3)
        zellen = np.floor((self.punkte - self._unten) / self.raster).astype(np.int64)
        self._n = zellen.max(axis=0) + 1 if len(zellen) else np.ones(3, dtype=np.int64)
        schluessel = (zellen[:, 0] * self._n[1] + zellen[:, 1]) * self._n[2] + zellen[:, 2]
        self._ordnung = np.argsort(schluessel, kind="stable")
        self._schluessel = schluessel[self._ordnung]

    def nah(self, unten, oben):
        """Die Nummern der Punkte in den Zellen, die den Quader unten … oben berühren."""
        if not len(self.punkte):
            return np.zeros(0, dtype=np.int64)
        a = np.floor((np.asarray(unten) - self._unten) / self.raster).astype(np.int64)
        b = np.floor((np.asarray(oben) - self._unten) / self.raster).astype(np.int64)
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


def wolke(form, kanten_, reichweite, punktabstand=PUNKTABSTAND, raster=RASTER):
    """Die Wolke der Flächen, die näher als `reichweite` an einer der Kanten liegen – Punkte
    etwa alle `punktabstand` mm, auch auf ihren Kanten (eine gerade hat sonst nur ihre Enden)."""
    if not kanten_:
        return Wolke(np.zeros((0, 3)), np.zeros(0), raster)
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
        rand = [
            [q.x, q.y, q.z]
            for kante in flaeche.Edges
            if kante.Length > 1e-9
            for q in kante.discretize(Distance=punktabstand)
        ]
        alle = np.vstack([p, e] + ([np.array(rand)] if rand else []))
        punkte.append(alle)
        nummern.append(np.full(len(alle), nummer))
    if not punkte:
        return Wolke(np.zeros((0, 3)), np.zeros(0), raster)
    return Wolke(np.vstack(punkte), np.concatenate(nummern), raster)


# --- Die Stellung an einem Punkt ----------------------------------------------------------------


@dataclass
class Lage:
    """Wie das Werkzeug an einem Punkt der Kante steht."""

    spitze: np.ndarray
    achse: np.ndarray
    normale: np.ndarray  # der Fase
    tiefe: float  # die Fase liegt so weit unter der Kante (längs normale)
    schenkel: tuple  # (s1, s2)
    anteil: float = 0.0  # wo die Fase am Fräser liegt (ANTEILE_KEGEL, ANTEILE_FLACH)
    seite: float = 0.0  # Stirn: auf welcher Seite ihrer Mitte (±1 längs q1 → q2)


def _zuerst(werte, wert):
    """`werte` mit `wert` vorn (wenn er dabei ist), sonst in ihrer Reihenfolge."""
    return sorted(werte, key=lambda x: x != wert)


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
    """Die möglichen Lagen (Lage) für diese Fase, die beste zuerst – erst beim Abholen gerechnet
    (meist passt eine der ersten). Mit der Lage der Stelle davor (`vorher`) zuerst die ihr
    nächste Achse und dort ihr Anteil: Sonst sprang die Spitze an einer Kante, an der eine
    Prüfung knapp mal hält und mal nicht, von Stelle zu Stelle zwischen zwei Anteilen (am Klotz
    unten an der Schräge, 0,9 mm hin und her)."""
    f = w.fraeser
    z = np.array([0.0, 0.0, 1.0])
    q1, q2 = e + s1 * u1, e + s2 * u2
    m = 0.5 * (q1 + q2)
    g = q2 - q1
    breit = float(np.linalg.norm(g))
    g = g / breit if breit > 1e-9 else np.cross(n_p, t)
    if f.kegel:
        alpha = f.halbwinkel
        if w.art == DREI:
            achsen = [z]
        else:
            # Stetig: die eine Seite der Fase. Dort senkrecht zur Kante, sonst um nP gekippt
            # (NEIGEN, nach oben zuerst) – mit einer Stelle davor so nah wie möglich an ihr.
            seiten = [g, -g]
            ziel = vorher.achse if vorher is not None else z
            seite = max(seiten, key=lambda s: float((math.cos(alpha) * s) @ ziel))
            quer = np.cross(n_p, seite)
            achsen = []
            for grad in NEIGEN:
                paar = []
                for vz in (1.0, -1.0) if grad else (1.0,):
                    th = math.radians(grad) * vz
                    richtung = math.cos(th) * seite + math.sin(th) * quer
                    paar.append(math.sin(alpha) * n_p + math.cos(alpha) * richtung)
                achsen.extend(sorted(paar, key=lambda a: -float(a[2])))
            if vorher is not None:
                achsen.sort(key=lambda a: -float(a @ vorher.achse))
        anteile = _zuerst(ANTEILE_KEGEL, vorher.anteil if vorher is not None else None)
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
            for anteil in anteile:
                rho = unten + anteil * (oben - unten)
                h = (rho - f.spitze) / math.tan(alpha)
                spitze = m - h * a - rho * w_r
                yield Lage(spitze, a, n_p, d, (s1, s2), anteil)
    else:
        a = n_p
        r_eben = f.spitze
        paare = []
        for anteil in ANTEILE_FLACH:
            mitte = anteil * r_eben
            if mitte + 0.5 * breit > r_eben or mitte - 0.5 * breit < 0.1 * r_eben:
                continue
            for vz in sorted((1.0, -1.0), key=lambda vz: -float(vz * g[2])):  # oben zuerst
                paare.append((anteil, vz))
        if vorher is not None:
            paare = _zuerst(paare, (vorher.anteil, vorher.seite))
        for anteil, vz in paare:
            spitze = m + anteil * r_eben * vz * g
            yield Lage(spitze, a, n_p, d, (s1, s2), anteil, vz)


def _tisch(spitze, achse, w):
    """So viel (mm) kommt das Werkzeug – Schneide, Schaft, Halter, Spindel – dem Tisch näher als
    ABSTAND; 0: nicht (oder kein Tisch). Je Stück liegt der tiefste Punkt an einem seiner Enden."""
    if w.tisch is None or w.tisch == -math.inf:
        return 0.0
    f = w.fraeser
    az = float(achse[2])
    quer = math.sqrt(max(0.0, 1.0 - az * az))
    ecken = [(0.0, f.spitze if f.kegel else f.radius), (f.kegelhoehe, f.radius)]
    ecken.append((f.schneidhoehe if w.aufbau is not None else f.hoehe, f.radius))
    if w.aufbau is not None:
        for h0, h1, r0, r1 in w.aufbau.stuecke:
            ecken.extend(((h0, r0), (h1, r1)))
        ecken.extend(((w.aufbau.kopf, KOPF_RADIUS), (w.aufbau.kopf + KOPF_LAENGE, KOPF_RADIUS)))
    tiefste = float(spitze[2]) + min(h * az - r * quer for h, r in ecken)
    return max(0.0, w.tisch + ABSTAND - tiefste)


def _umriss(aufbau, fraeser):
    """Der Umriss des Aufbaus im Halbschnitt: [((h, r), (h, r))] – Mäntel, Stufen, oben zu."""
    segmente = []
    vorher = None
    for h0, h1, r0, r1 in aufbau.stuecke:
        if vorher is None:
            unten = fraeser.radius if abs(h0 - fraeser.schneidhoehe) < 1e-6 else 0.0
            if r0 > unten:  # die Stufe über der Schneide (oder der Boden)
                segmente.append(((h0, min(unten, r0)), (h0, r0)))
        else:
            segmente.append((vorher, (h0, r0)))
        segmente.append(((h0, r0), (h1, r1)))
        vorher = (h1, r1)
    if vorher is not None:
        segmente.append((vorher, (vorher[0], 0.0)))
    return segmente


def _aufbau_im_teil(spitze, achse, w, grob):
    """So viel (mm) kommen Schaft und Halter dem Teil näher als ABSTAND; 0: nicht."""
    if w.aufbau is None or grob is None or not w.aufbau.stuecke:
        return 0.0
    stuecke = w.aufbau.stuecke
    h_unten = min(s[0] for s in stuecke)
    h_oben = max(s[1] for s in stuecke)
    r_max = max(max(s[2], s[3]) for s in stuecke) + ABSTAND
    ecken = np.array([spitze + h_unten * achse, spitze + h_oben * achse])
    nummern = grob.nah(ecken.min(axis=0) - r_max, ecken.max(axis=0) + r_max)
    if not len(nummern):
        return 0.0
    rel = grob.punkte[nummern] - spitze
    h = rel @ achse
    radial = np.linalg.norm(rel - np.outer(h, achse), axis=1)
    nah = (h > h_unten - ABSTAND) & (h < h_oben + ABSTAND) & (radial < r_max)
    if not nah.any():
        return 0.0
    h, radial = h[nah], radial[nah]
    tief = np.zeros(len(h))
    for h0, h1, r0, r1 in stuecke:  # drinnen
        im = (h >= h0) & (h <= h1)
        if im.any():
            r = r0 + (h[im] - h0) / max(h1 - h0, 1e-9) * (r1 - r0)
            tief[im] = np.maximum(tief[im], r - radial[im] + ABSTAND)
    p = np.stack([h, radial], axis=1)
    for (ha, ra), (hb, rb) in _umriss(w.aufbau, w.fraeser):  # draußen, zu nah
        a = np.array([ha, ra])
        ab = np.array([hb, rb]) - a
        lang = float(ab @ ab)
        s = np.clip(((p - a) @ ab) / lang, 0.0, 1.0) if lang > 1e-12 else np.zeros(len(p))
        abstand = np.linalg.norm(p - (a + np.outer(s, ab)), axis=1)
        tief = np.maximum(tief, ABSTAND - abstand)
    return float(max(0.0, tief.max()))


def _verletzung(lage, e, t, k, w, wolke_, enden):
    """Wie tief (mm) die Schneide in dieser Lage in das Teil schnitte – außerhalb des
    Fasenstreifens; 0: nirgends."""
    f = w.fraeser
    a = lage.achse
    hoehe = f.schneidhoehe if w.aufbau is not None else f.hoehe
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
    flaechen = wolke_.flaechen[nummern]
    eigene = np.isin(flaechen, k.nummern)
    ueber = (x - e) @ lage.normale >= -lage.tiefe - RAND
    quer = (x - e) - np.outer((x - e) @ t, t)
    weit = max(lage.schenkel) + STREIFEN
    nahe = np.linalg.norm(quer, axis=1) <= weit
    (p0, t0), (p1, t1) = enden
    zwischen = ((x - p0) @ t0 >= -RAND) & ((p1 - x) @ t1 >= -RAND)
    # Dazu an einer Ecke die Fläche, die die Kante abschließt (_kappen), nahe dem Ende.
    kappe = np.zeros(len(x), dtype=bool)
    for (p_e, _t_e), nummern_e in zip(enden, k.kappen, strict=True):
        if nummern_e:
            kappe |= np.isin(flaechen, nummern_e) & (
                np.linalg.norm(x - p_e, axis=1) <= KAPPE_WEIT * weit
            )
    erlaubt = ueber & nahe & ((eigene & zwischen) | kappe)
    schlecht = innen & ~erlaubt
    if not schlecht.any():
        return 0.0
    return float(np.max(f.radius_bei(h[schlecht]) - radial[schlecht]))


# --- Die Bahn ---------------------------------------------------------------------------------


def _stellen_der_kante(k, w, wolke_, schritt=SCHRITT, grob=None):
    """[(Parameter, Lage oder None, Grund)] entlang der Kante, etwa alle `schritt` mm. Je Lage
    zuerst der Tisch (TISCH), dann die Schneide (ENG), dann Schaft und Halter (HALTER, in der
    groben Wolke). Ohne Lage der Grund: TISCH, wenn er im Weg war (höher spannen hilft dann am
    meisten), sonst HALTER, sonst ENG."""
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
        gewaehlt, grund = None, KEINE_STELLUNG
        erste = None  # die Achse der ersten Lagen
        for lage in _lagen(e, t, n_p, d, s1, s2, u1, u2, w, vorher):
            if erste is None:
                erste = lage.achse
            elif grund == ENG and not np.array_equal(lage.achse, erste):
                break  # gekippt wird für Tisch und Halter – nicht, wo schon die Schneide anstößt
            if _tisch(lage.spitze, lage.achse, w) > 0.0:  # zuerst: der ist billig
                grund = TISCH
                continue
            if _verletzung(lage, e, t, k, w, wolke_, enden) > 0.0:
                if grund == KEINE_STELLUNG:
                    grund = ENG
                continue
            if _aufbau_im_teil(lage.spitze, lage.achse, w, grob) > 0.0:
                if grund in (KEINE_STELLUNG, ENG):
                    grund = HALTER
                continue
            gewaehlt = lage
            break
        if gewaehlt is None:
            ergebnis.append((prm, None, grund))
            continue
        vorher = gewaehlt
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


def _schneide_frei(wolke_, fraeser, hoehe, spitze, achse):
    """Berührt die Schneide (bis `hoehe` über der Spitze) nichts von der Wolke?"""
    ecken = np.array([spitze, spitze + hoehe * achse])
    nummern = wolke_.nah(ecken.min(axis=0) - fraeser.radius, ecken.max(axis=0) + fraeser.radius)
    if not len(nummern):
        return True
    rel = wolke_.punkte[nummern] - spitze
    h = rel @ achse
    radial = np.linalg.norm(rel - np.outer(h, achse), axis=1)
    return not np.any((h > -RAND) & (h < hoehe) & (radial < fraeser.radius_bei(h) - RAND))


def _stelle_frei(spitze, achse, w, wolke_, grob=None):
    """Berührt das Werkzeug mit der Spitze hier und dieser Achse nichts vom Teil, bleiben Schaft
    und Halter ABSTAND davon und alles ABSTAND über dem Tisch?"""
    f = w.fraeser
    if _tisch(spitze, achse, w) > 0.0:
        return False
    hoehe = f.schneidhoehe if w.aufbau is not None else f.hoehe
    if not _schneide_frei(wolke_, f, hoehe, spitze, achse):
        return False
    if grob is not None and not _schneide_frei(grob, f, hoehe, spitze, achse):
        return False  # weiter weg von den Kanten
    return _aufbau_im_teil(spitze, achse, w, grob) <= 0.0


def _frei(von, bis, achse, w, wolke_, grob=None):
    """Bleibt das Werkzeug (Achse fest) auf dem Weg der Spitze von → bis frei (_stelle_frei)?"""
    laenge = float(np.linalg.norm(bis - von))
    return all(
        _stelle_frei(von + s * (bis - von), achse, w, wolke_, grob)
        for s in np.linspace(0.0, 1.0, max(2, int(math.ceil(laenge)) + 1))
    )


def _anfahrt(lage, w, wolke_, grob=None):
    """(oben, vor) – `vor`: längs der Achse so weit zurück, dass das Werkzeug nichts berührt,
    und `sicherheit` dazu (das Eintauchen von dort bleibt im Körper der Schnittstellung – ein
    Kegel oder Zylinder, längs seiner Achse zurückgezogen, liegt in sich selbst); `oben`: auf der
    sicheren Höhe darüber, der Weg hinab frei – senkrecht, sonst längs der Achse. None, wenn
    keiner frei ist."""
    a = lage.achse
    zurueck = 0.0
    while not _stelle_frei(lage.spitze + zurueck * a, a, w, wolke_, grob):
        zurueck += 0.5
        if zurueck > w.fraeser.hoehe:
            return None
    vor = lage.spitze + (zurueck + w.sicherheit) * a
    oben = np.array([vor[0], vor[1], max(w.sicher, float(vor[2]))])
    if _frei(oben, vor, a, w, wolke_, grob):
        return oben, vor
    if a[2] > 0.1:
        weit = vor + a * max(0.0, (w.sicher - float(vor[2])) / float(a[2]))
        if _frei(weit, vor, a, w, wolke_, grob):
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
    grob = None
    if w.aufbau is not None and w.aufbau.stuecke:
        reich = max(s[1] for s in w.aufbau.stuecke)
        reich += max(max(s[2], s[3]) for s in w.aufbau.stuecke) + ABSTAND
        grob = wolke(form, kanten_, reich, max(GROB, punktabstand), RASTER_GROB)
    laeufe, gruende = [], {}
    laenge = 0.0
    gefast = 0
    schenkel = []
    for k in kanten_:
        stellen = _stellen_der_kante(k, w, wolke_, schritt, grob)
        teile, ohne = _laeufe(stellen, k.kante)
        for grund, mm in ohne.items():
            gruende[grund] = gruende.get(grund, 0.0) + mm
        if teile:
            gefast += 1
        for lauf in teile:
            lauf = _gleichlauf(lauf, w)
            hinein = _anfahrt(lauf[0], w, wolke_, grob)
            heraus = _anfahrt(lauf[-1], w, wolke_, grob)
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
