# SPDX-License-Identifier: LGPL-2.1-or-later
"""5 Achsen simultan, S4: Wegkippen (W-015, Spezifikation Strategien 16.3; Manuel, 2026-10-04:
„Ja, bauen“).

In einer tiefen Kavität muss ein senkrechter Fräser so weit herausstehen, dass der Halter über
den Rand kommt – an einer Kavität 30 tief gut 30 mm, wie schlank der Halter auch ist. Kippt die
Achse um die Mitte der Kugel von der Wand weg, nur wo es nötig ist, reicht ein kürzerer: mit
einem Schrumpffutter Ø 21 bis 30° gekippt 21,7 mm, knapp dreimal so steif (Versuch in der
Spezifikation). Die Kugel bleibt, wo sie ist – die Bahn des 3D-Schlichtens gilt weiter, wie beim
Anstellen (angestellt.py, dort auch die Sätze für die Maschine).

**Wie:** Das Teil als Höhenfeld (`Huelle`: hoehenfeld.hoehen – je Rasterpunkt die oberste Höhe;
gefragt wird das Höchste der vier Rasterpunkte um eine Stelle, lieber zu vorsichtig). Halter und Schaft als Punkte auf Ringen um die
Achse (`koerper`). Ein Punkt, der tiefer liegt als das Höhenfeld dort plus Spiel, stößt an. Je
Stelle der Bahn die kleinste Neigung (WINKEL_SCHRITT bis `winkel_max`): ins Freie (die Richtungen
zu den Rasterpunkten im Umkreis des Halters, gewichtet mit ihrer Tiefe) oder den Abfall hinab
(die Steigung des Höhenfelds, über den Halbmesser des Halters aufs Höchste gebracht), was weniger
Neigung braucht – geht beides nicht, die erste von RICHTUNGEN, die geht. Senkrecht zählt
nur der Halter: Ein Schaft bis zum Ø der Kugel stößt senkrecht nirgends an, wo die Kugel nicht
schon anstieße (das Höhenfeld meldete an jeder senkrechten Wand Fehlalarm). Entlang der Bahn
geglättet (`geglaettet`): je Stelle die größte Neigung im Umkreis GLAETTEN, in der Richtung der
Stelle, die sie braucht – die Achse kippt rechtzeitig, nicht ruckartig. Wo auch WINKEL_MAX nicht
reicht, bleibt die Neigung, die am wenigsten anstößt nicht bekannt – die Stelle bleibt senkrecht
und zählt als `anstoesse` (die Kollision sagt es).

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import numpy as np

RASTER = 0.5  # mm – das Höhenfeld des Teils
TOLERANZ = 0.05  # mm – so fein wird das Teil vernetzt
SPIEL_HALTER = 1.0  # mm – so weit bleibt der Halter vom Teil weg
SPIEL_SCHAFT = 0.2  # mm – so weit der Schaft
WINKEL_MAX = 30.0  # Grad – so weit kippt die Achse höchstens
WINKEL_SCHRITT = 1.0  # Grad
RICHTUNGEN = 8  # so viele Richtungen ringsum, wenn die Steigung nicht reicht
GLAETTEN = 5.0  # mm – im Umkreis entlang der Bahn gilt die größte Neigung
RING_ABSTAND = 2.0  # mm – so dicht liegen die Punkte auf Halter und Schaft
BEWEGUNG = ("G0", "G00", "G1", "G01")
EILGANG = ("G0", "G00")


@dataclass
class Koerper:
    """Halter und Schaft als Punkte im Rahmen des Werkzeugs (Spitze 0, Achse +z), zur Nase hin:
    `halter` (k, 3) ab der Nase, `schaft` (k, 3) von über der Kugel bis zur Nase – beide für eine
    Auskragung (Nase über der Spitze)."""

    halter: np.ndarray
    schaft: np.ndarray
    auskragung: float


def _ringe(radius_bei, z_von, z_bis):
    """Punkte auf Ringen von z_von bis z_bis, der Radius je Höhe aus `radius_bei(z)`."""
    if z_bis <= z_von:
        return np.zeros((0, 3))
    hoehen = np.linspace(z_von, z_bis, max(2, int(math.ceil((z_bis - z_von) / RING_ABSTAND)) + 1))
    punkte = []
    for z in hoehen:
        r = radius_bei(z)
        if r <= 0:
            continue
        n = max(8, int(math.ceil(2 * math.pi * r / RING_ABSTAND)))
        w = np.linspace(0.0, 2 * math.pi, n, endpoint=False)
        punkte.append(np.column_stack([r * np.cos(w), r * np.sin(w), np.full(n, z)]))
    return np.vstack(punkte) if punkte else np.zeros((0, 3))


def koerper(halter, schaft_radius, kugel_radius, auskragung, bis=math.inf):
    """Koerper für einen Halter (halter.Halter, gerade) mit der Nase `auskragung` über der Spitze
    und einem Schaft mit `schaft_radius` (etwas kleiner gerechnet: Er läuft an Wänden entlang) –
    nur bis zur Höhe `bis` über der Spitze (darüber reicht nichts mehr ans Teil)."""
    abschnitte = [a for a in reversed(halter.abschnitte) if a.laenge > 0]  # von der Nase hinauf
    teile, z = [], auskragung
    if abschnitte:
        nase = abschnitte[0].d_unten / 2
        # Die Stirn der Nase: Ringe vom Schaft bis zum Rand.
        for r in np.arange(schaft_radius + RING_ABSTAND, nase + 1e-9, RING_ABSTAND):
            teile.append(_ringe(lambda _z, r=r: r, z, z))
    for a in abschnitte:
        unten, oben = a.d_unten / 2, a.d_oben / 2
        von = z

        def radius(h, von=von, unten=unten, oben=oben, laenge=a.laenge):
            return unten + (oben - unten) * (h - von) / laenge

        teile.append(_ringe(radius, von, von + a.laenge))
        z += a.laenge
    halter_punkte = np.vstack([t for t in teile if len(t)]) if teile else np.zeros((0, 3))
    halter_punkte = halter_punkte[halter_punkte[:, 2] <= bis]
    schaft = _ringe(lambda _z: max(schaft_radius - 0.1, 0.1), 1.5 * kugel_radius, auskragung)
    return Koerper(halter_punkte, schaft, auskragung)


class Huelle:
    """Das Teil als Höhenfeld: je Rasterpunkt die oberste Höhe (um eine Zelle verbreitert)."""

    def __init__(self, form, rand, raster=RASTER, toleranz=TOLERANZ):
        from . import hoehenfeld as hf
        from . import vierachs_flaechen as vf

        box = form.BoundBox
        self.x = np.arange(box.XMin - rand, box.XMax + rand + raster, raster)
        self.y = np.arange(box.YMin - rand, box.YMax + rand + raster, raster)
        netz = vf.vernetze(form, toleranz).netz
        z = hf.hoehen(netz, self.x, self.y)
        self.z = np.where(z <= hf.KEIN_TREFFER + 1.0, -np.inf, z)
        self.hoechste = float(np.max(self.z)) if np.isfinite(self.z).any() else -math.inf
        self.raster = raster
        self._abfall = {}

    def hoehe(self, x, y):
        """Die Höhe an (x, y) (Arrays): das Höchste der vier Rasterpunkte um die Stelle – lieber
        zu vorsichtig; außerhalb −∞."""
        fx = (np.asarray(x) - self.x[0]) / self.raster
        fy = (np.asarray(y) - self.y[0]) / self.raster
        i0, j0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
        drin = (i0 >= 0) & (j0 >= 0) & (i0 < len(self.x) - 1) & (j0 < len(self.y) - 1)
        ergebnis = np.full(np.shape(fx), -np.inf)
        i, j = i0[drin], j0[drin]
        ergebnis[drin] = np.maximum(
            np.maximum(self.z[i, j], self.z[i + 1, j]),
            np.maximum(self.z[i, j + 1], self.z[i + 1, j + 1]),
        )
        return ergebnis

    def ins_freie(self, x, y, radius):
        """Je (x, y) die waagerechte Richtung zum Freien im Umkreis `radius` (_ins_freie)."""
        return _ins_freie(self, np.asarray(x), np.asarray(y), radius)

    def abfall(self, x, y, radius):
        """Je (x, y) die waagerechte Richtung, in die das Teil im Umkreis `radius` abfällt (das
        Höhenfeld aufs Höchste im Umkreis, dessen Steigung abwärts) – (0, 0), wo es eben ist."""
        zellen = max(1, int(round(radius / self.raster)))
        if zellen not in self._abfall:
            feld = _breiter(self.z, zellen)
            endlich = np.where(
                np.isfinite(feld), feld, np.nanmin(np.where(np.isfinite(feld), feld, np.nan))
            )
            gx, gy = np.gradient(endlich, self.raster, self.raster)
            self._abfall[zellen] = (gx, gy)
        gx, gy = self._abfall[zellen]
        i = np.clip(
            np.rint((np.asarray(x) - self.x[0]) / self.raster).astype(int), 0, len(self.x) - 1
        )
        j = np.clip(
            np.rint((np.asarray(y) - self.y[0]) / self.raster).astype(int), 0, len(self.y) - 1
        )
        d = np.column_stack([-gx[i, j], -gy[i, j]])
        laenge = np.linalg.norm(d, axis=1)
        d[laenge > 1e-9] /= laenge[laenge > 1e-9, None]
        d[laenge <= 1e-9] = 0.0
        return d


def _ins_freie(huelle, x, y, radius, schritt=1.0):
    """Je (x, y) die waagerechte Richtung zum Freien im Umkreis `radius`: die Richtungen zu den
    Rasterpunkten dort, gewichtet mit ihrer Tiefe unter dem Höchsten im Umkreis."""
    gitter = np.arange(-radius, radius + 1e-9, schritt)
    dx, dy = np.meshgrid(gitter, gitter, indexing="ij")
    im_kreis = dx**2 + dy**2 <= radius**2
    dx, dy = dx[im_kreis], dy[im_kreis]
    ergebnis = np.zeros((len(x), 2))
    for k0 in range(0, len(x), 256):
        px, py = np.asarray(x[k0 : k0 + 256])[:, None], np.asarray(y[k0 : k0 + 256])[:, None]
        z = huelle.hoehe(px + dx[None, :], py + dy[None, :])
        z = np.where(np.isfinite(z), z, np.nan)
        oben = np.nanmax(np.where(np.isnan(z), -np.inf, z), axis=1)[:, None]
        tiefe = np.nan_to_num(oben - z, nan=0.0, posinf=0.0, neginf=0.0)
        d = np.column_stack([(tiefe * dx).sum(axis=1), (tiefe * dy).sum(axis=1)])
        laenge = np.linalg.norm(d, axis=1)
        d[laenge > 1e-9] /= laenge[laenge > 1e-9, None]
        d[laenge <= 1e-9] = 0.0
        ergebnis[k0 : k0 + 256] = d
    return ergebnis


def _breiter(z, zellen):
    """Das Höchste im Quadrat ±zellen um jeden Rasterpunkt (getrennt längs x und y)."""
    from numpy.lib.stride_tricks import sliding_window_view

    if zellen <= 0:
        return z
    rand = np.pad(z, ((zellen, zellen), (0, 0)), constant_values=-np.inf)
    z = sliding_window_view(rand, 2 * zellen + 1, axis=0).max(axis=-1)
    rand = np.pad(z, ((0, 0), (zellen, zellen)), constant_values=-np.inf)
    return sliding_window_view(rand, 2 * zellen + 1, axis=1).max(axis=-1)


def _bis(huelle, spitzen_z, halter, winkel_max):
    """Wie hoch über der Spitze (im Rahmen des Werkzeugs) ein Punkt des Halters höchstens liegen
    kann, um noch ans Teil zu reichen – bei der tiefsten Spitze und bis `winkel_max` gekippt."""
    if not np.isfinite(huelle.hoechste) or not len(spitzen_z):
        return math.inf
    radius = max((max(a.d_oben, a.d_unten) / 2 for a in halter.abschnitte), default=0.0)
    w = math.radians(winkel_max)
    hoehe = huelle.hoechste + SPIEL_HALTER - float(np.min(spitzen_z))
    return (hoehe + radius * math.sin(w)) / max(math.cos(w), 0.1)


def _basis(achsen):
    """Je Achse (n, 3) zwei Richtungen quer dazu (u, v)."""
    hilf = np.where(np.abs(achsen[:, 2:3]) < 0.9, [[0.0, 0.0, 1.0]], [[1.0, 0.0, 0.0]])
    u = np.cross(achsen, hilf)
    u /= np.linalg.norm(u, axis=1)[:, None]
    v = np.cross(achsen, u)
    return u, v


def stoesst(huelle, mitten, achsen, koerper_, kugel_radius, mit_schaft):
    """Je Stelle (Mitte der Kugel, Achse; je (n, 3)): stoßen der Halter – und, wo `mit_schaft`
    (bool je Stelle; None: nirgends), der Schaft – ans Teil? (n,) bool."""
    n = len(mitten)
    ergebnis = np.zeros(n, dtype=bool)
    if n == 0:
        return ergebnis
    spitzen = mitten - kugel_radius * achsen
    u, v = _basis(achsen)
    for punkte, spiel, welche in (
        (koerper_.halter, SPIEL_HALTER, np.arange(n)),
        (
            koerper_.schaft,
            SPIEL_SCHAFT,
            np.flatnonzero(mit_schaft) if mit_schaft is not None else np.zeros(0, dtype=int),
        ),
    ):
        if not len(punkte) or not len(welche):
            continue
        for k0 in range(0, len(welche), 256):
            k = welche[k0 : k0 + 256]
            welt = (
                spitzen[k, None, :]
                + punkte[None, :, 0:1] * u[k, None, :]
                + punkte[None, :, 1:2] * v[k, None, :]
                + punkte[None, :, 2:3] * achsen[k, None, :]
            )
            unter = welt[..., 2] < huelle.hoehe(welt[..., 0], welt[..., 1]) + spiel
            ergebnis[k] |= unter.any(axis=1)
    return ergebnis


def _gekippt(richtungen, winkel):
    """Achsen (n, 3): z um `winkel` Grad (je Stelle) zur waagerechten Richtung (n, 2) gekippt."""
    w = np.radians(np.asarray(winkel, dtype=float))
    achsen = np.zeros((len(richtungen), 3))
    achsen[:, 0] = np.sin(w) * richtungen[:, 0]
    achsen[:, 1] = np.sin(w) * richtungen[:, 1]
    achsen[:, 2] = np.cos(w)
    return achsen


def _kleinste(huelle, mitten, kandidat, koerper_, kugel_radius, winkel_max):
    """Je Stelle die kleinste Neigung (Grad) in Richtung `kandidat` (n, 2), bei der nichts
    anstößt – inf, wo keine bis `winkel_max` geht. Erst in Schritten von 5°, dann zwischen der
    letzten, die anstieß, und der ersten freien in WINKEL_SCHRITT."""
    n = len(mitten)
    winkel = np.full(n, np.inf)
    offen = np.linalg.norm(kandidat, axis=1) > 0.5
    grob = max(WINKEL_SCHRITT, 5.0)
    alle = np.ones(n, dtype=bool)
    for w in np.arange(grob, winkel_max + grob - 1e-9, grob):
        w = min(w, winkel_max)
        k = np.flatnonzero(offen)
        if not len(k):
            break
        frei = ~stoesst(
            huelle, mitten[k], _gekippt(kandidat[k], np.full(len(k), w)), koerper_, kugel_radius,
            alle[k],
        )  # fmt: skip
        treffer = k[frei]
        winkel[treffer] = w
        offen[treffer] = False
        for fein in np.arange(w - grob + WINKEL_SCHRITT, w - 1e-9, WINKEL_SCHRITT):
            if fein <= 0 or not len(treffer):
                continue
            passt = ~stoesst(
                huelle, mitten[treffer], _gekippt(kandidat[treffer], np.full(len(treffer), fein)),
                koerper_, kugel_radius, alle[treffer],
            )  # fmt: skip
            kleiner = treffer[passt & (winkel[treffer] > fein)]
            winkel[kleiner] = fein
    return winkel


def noetig(huelle, mitten, koerper_, kugel_radius, halter_radius, winkel_max=WINKEL_MAX):
    """(Neigung in Grad (n,), Richtung (n, 2), geht (n,)) – je Stelle die kleinste Neigung, bei
    der nichts anstößt: ins Freie (Huelle.ins_freie) oder den Abfall hinab (Huelle.abfall), was
    weniger braucht; geht beides nicht, die erste von RICHTUNGEN ringsum. Wo keine bis
    `winkel_max` geht: 0 und geht False."""
    n = len(mitten)
    winkel = np.zeros(n)
    richtung = np.zeros((n, 2))
    offen = stoesst(huelle, mitten, _gekippt(richtung, winkel), koerper_, kugel_radius, None)
    geht = ~offen
    k = np.flatnonzero(offen)
    if len(k):
        x, y = mitten[k, 0], mitten[k, 1]
        bester, beste_richtung = np.full(len(k), np.inf), np.zeros((len(k), 2))
        for kandidat in (
            huelle.ins_freie(x, y, halter_radius + 10.0),
            huelle.abfall(x, y, halter_radius),
        ):
            w = _kleinste(huelle, mitten[k], kandidat, koerper_, kugel_radius, winkel_max)
            besser = w < bester
            bester[besser], beste_richtung[besser] = w[besser], kandidat[besser]
        for nummer in range(RICHTUNGEN):
            rest = np.flatnonzero(~np.isfinite(bester))
            if not len(rest):
                break
            w0 = 2 * math.pi * nummer / RICHTUNGEN
            kandidat = np.tile([math.cos(w0), math.sin(w0)], (len(rest), 1))
            w = _kleinste(huelle, mitten[k[rest]], kandidat, koerper_, kugel_radius, winkel_max)
            gefunden = np.isfinite(w)
            bester[rest[gefunden]] = w[gefunden]
            beste_richtung[rest[gefunden]] = kandidat[gefunden]
        gefunden = np.isfinite(bester)
        winkel[k[gefunden]] = bester[gefunden]
        richtung[k[gefunden]] = beste_richtung[gefunden]
        geht[k[gefunden]] = True
    return winkel, richtung, geht


def geglaettet(punkte, winkel, richtung, umkreis=GLAETTEN):
    """(Neigung, Richtung) entlang der Bahn geglättet: je Stelle die größte Neigung im Umkreis
    `umkreis` (mm Weg), mit der Richtung der Stelle, die sie braucht."""
    weg = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(punkte, axis=0), axis=1))])
    neu_w, neu_r = winkel.copy(), richtung.copy()
    for i in range(len(punkte)):
        a = np.searchsorted(weg, weg[i] - umkreis)
        b = np.searchsorted(weg, weg[i] + umkreis, "right")
        k = a + int(np.argmax(winkel[a:b]))
        if winkel[k] > neu_w[i]:
            neu_w[i], neu_r[i] = winkel[k], richtung[k]
    return neu_w, neu_r


@dataclass
class Ergebnis:
    """Was wegkippen() rechnet."""

    achsen: list  # je Befehl (x, y, z); (0, 0, 0) ohne Bewegung
    neigung: float  # Grad – die größte
    gekippt: int  # Stellen im Vorschub, an denen die Achse kippt
    anstoesse: int  # Stellen, an denen auch WINKEL_MAX nicht reicht


def achsen(befehle, form, kugel_radius, halter, schaft_radius, auskragung, winkel_max=WINKEL_MAX):
    """Ergebnis: je Befehl (Path.Command, senkrecht gerechnet) die Werkzeugachse – im Vorschub so
    wenig gekippt wie nötig, damit der Halter mit dieser `auskragung` (Nase über der Spitze) und
    der Schaft nirgends anstoßen; Eilgänge wie angestellt.achsen (hinauf mit der Achse davor,
    sonst mit der des nächsten Schnitts)."""
    from . import angestellt as an

    stellen = []
    stand = [None, None, None]
    for i, befehl in enumerate(befehle):
        name = befehl.Name.upper()
        if name not in BEWEGUNG:
            continue
        werte = befehl.Parameters
        stand = [float(werte[k]) if k in werte else stand[j] for j, k in enumerate("XYZ")]
        if None not in stand:
            stellen.append((i, tuple(stand), name in EILGANG))
    vorschub = [s for s in stellen if not s[2]]
    ergebnis = [an.KEINE] * len(befehle)
    if not vorschub:
        return Ergebnis(ergebnis, 0.0, 0, 0)
    mitten = np.array([p for _i, p, _e in vorschub]) + np.array([0.0, 0.0, kugel_radius])
    halter_radius = max((max(a.d_oben, a.d_unten) / 2 for a in halter.abschnitte), default=10.0)
    huelle = Huelle(form, halter_radius + auskragung + 10.0)
    bis = _bis(huelle, mitten[:, 2] - kugel_radius, halter, winkel_max)
    koerper_ = koerper(halter, schaft_radius, kugel_radius, auskragung, bis)
    nase = halter.abschnitte[-1].d_unten / 2 if halter.abschnitte else halter_radius
    winkel, richtung, geht = noetig(huelle, mitten, koerper_, kugel_radius, nase, winkel_max)
    winkel, richtung = geglaettet(mitten, winkel, richtung)
    je_satz = {
        i: tuple(a) for (i, _p, _e), a in zip(vorschub, _gekippt(richtung, winkel), strict=True)
    }
    letzte, punkt_davor, kommend = None, None, None
    naechste = [None] * len(stellen)
    for k in range(len(stellen) - 1, -1, -1):
        i, _p, eilgang = stellen[k]
        if not eilgang:
            kommend = je_satz[i]
        naechste[k] = kommend
    for k, (i, p, eilgang) in enumerate(stellen):
        if not eilgang:
            achse = je_satz[i]
        elif letzte is not None and an._nach_oben(punkt_davor, p):
            achse = letzte
        else:
            achse = naechste[k] or letzte or an.SENKRECHT
        ergebnis[i] = achse
        letzte, punkt_davor = achse, p
    return Ergebnis(
        ergebnis,
        float(winkel.max()),
        int(np.count_nonzero(winkel > 0)),
        int(np.count_nonzero(~geht)),
    )


def kuerzeste_auskragung(
    form,
    punkte,
    kugel_radius,
    halter,
    schaft_radius,
    winkel_max=WINKEL_MAX,
    von=None,
    bis=80.0,
    genau=0.25,
):
    """Die kürzeste Auskragung (mm, Nase über der Spitze), mit der an allen `punkte` (Spitzen,
    senkrecht gerechnet; (n, 3)) bis `winkel_max` gekippt nichts anstößt – inf, wenn auch `bis`
    nicht reicht. Mit winkel_max 0: senkrecht."""
    punkte = np.asarray(punkte, dtype=float)
    mitten = punkte + np.array([0.0, 0.0, kugel_radius])
    halter_radius = max((max(a.d_oben, a.d_unten) / 2 for a in halter.abschnitte), default=10.0)
    huelle = Huelle(form, halter_radius + bis + 10.0)
    nase = halter.abschnitte[-1].d_unten / 2 if halter.abschnitte else halter_radius
    unten = von if von is not None else 2 * kugel_radius

    hoehe_bis = _bis(huelle, punkte[:, 2], halter, winkel_max)

    def reicht(laenge):
        k = koerper(halter, schaft_radius, kugel_radius, laenge, hoehe_bis)
        if winkel_max <= 0:
            return not stoesst(
                huelle, mitten, np.tile([0.0, 0.0, 1.0], (len(mitten), 1)), k, kugel_radius, None
            ).any()
        return bool(noetig(huelle, mitten, k, kugel_radius, nase, winkel_max)[2].all())

    if not reicht(bis):
        return math.inf
    if reicht(unten):
        return unten
    while bis - unten > genau:
        mitte = (unten + bis) / 2
        if reicht(mitte):
            bis = mitte
        else:
            unten = mitte
    return bis
