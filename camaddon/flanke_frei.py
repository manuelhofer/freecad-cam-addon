# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Wege der Flanke, die nur durch die Luft gehen, schnell fahren.

Die Flanke (flanke_bahn) taucht je Umlauf von oben die Achse entlang ein und fährt, wo die Ecke
der Tasche versperrt ist, ABSTAND vor der Wand zum Anfang zurück – beides im Eintauch- oder
Arbeitsvorschub, denn sie weiß nicht, was davor geräumt wurde. In Manuels tiefer Tasche waren das
1,1 m von 3,4 m (Manuel, 2026-11-06: „da fuhr er oben ziemlich lang in der luft“).

Das Material von oben (materialstand) reicht hier nicht: Die Wände hängen über, und von oben steht
unter dem Rand alles voll. Darum ein räumliches Gitter aus dem räumlichen Rest (raum_material) oder,
ohne Ebenen, aus den Höhen; beim Abfahren der Bahn nimmt das Werkzeug mit seiner Achse weg, was es
trifft – so zählen die Umläufe davor mit. Was es nicht kennt, steht für es noch da: Dort bleibt der
langsame Weg, das ist die sichere Seite.

Läuft ohne Oberfläche."""

import math
from dataclasses import dataclass, replace

import numpy as np

from . import uhren

ZELLE = 0.5  # mm – so grob ist das Gitter mindestens
SCHRITT = 1.0  # mm – so dicht wird entlang der Bahn nachgesehen
ABTRAG_SCHRITT = 2.0  # mm – so dicht trägt die Bahn ab: stehen bleibt höchstens zu viel Material
RAND = 0.3  # mm über den Radius hinaus muss es frei sein – mehr als die halbe Zelle (0,25)
SICHER = 0.1  # mm – so viel kleiner trägt eine Bahn davor ab
VORLAUF = 2.0  # mm vor dem Material und vor dem Ende bleibt der Eintauchvorschub
MINDEST = 5.0  # mm – kürzere Stücke lohnen das Beschleunigen nicht
HOECHSTENS = 400_000_000  # Zellen – größer rechnet das Gitter nicht


class Gitter:
    """Das Material im Raum: `voll[i, j, k]` an (x[i], y[j], z[k])."""

    def __init__(self, x, y, z, voll):
        self.x, self.y, self.z, self.voll = x, y, z, voll

    @classmethod
    def aus_hoehen(cls, x, y, h, zelle=ZELLE):
        """Voll ist, was unter den Höhen `h[i, j]` liegt (−inf: nichts) – None ohne Material oder
        wenn es zu viele Zellen würden."""
        schritt = float(x[1] - x[0])
        jede = max(1, int(round(zelle / schritt)))
        x, y, h = x[::jede], y[::jede], _hoechste_je_block(h, jede)
        endlich = h[np.isfinite(h)]
        if not len(endlich):
            return None
        z_unten, z_oben = float(endlich.min()), float(endlich.max())
        dz = max(zelle, schritt * jede)
        z = np.arange(z_unten - dz, z_oben + dz, dz)
        if len(x) * len(y) * len(z) > HOECHSTENS:
            return None
        return cls(x, y, z, h[:, :, None] > z[None, None, :])

    @classmethod
    def aus_abschnitten(cls, x, y, grenzen, zelle=ZELLE):
        """Voll ist, was in den Abschnitten `grenzen[i, j, n] = (unten, oben)` der senkrechten
        Strahlen liegt (raum_material.Material) – None ohne Material oder bei zu vielen Zellen."""
        endlich = grenzen[np.isfinite(grenzen)]
        if not len(endlich):
            return None
        z = np.arange(float(endlich.min()), float(endlich.max()) + zelle, zelle)
        if len(x) * len(y) * len(z) > HOECHSTENS:
            return None
        voll = np.zeros((len(x), len(y), len(z)), dtype=bool)
        for n in range(grenzen.shape[2]):
            unten, oben = grenzen[:, :, n, 0, None], grenzen[:, :, n, 1, None]
            with np.errstate(invalid="ignore"):
                voll |= (z[None, None, :] >= unten - zelle) & (z[None, None, :] <= oben + zelle)
        return cls(np.asarray(x), np.asarray(y), z, voll)

    def _zellen(self, spitze, achse, radius, von, bis):
        """(Ausschnitt, Maske): die Zellen im Zylinder um die Achse, `von` bis `bis` über der
        Spitze – (None, None), wo er neben dem Gitter liegt."""
        p = np.asarray(spitze, dtype=float)
        a = np.asarray(achse, dtype=float)
        e0, e1 = p + a * von, p + a * bis
        unten, oben = np.minimum(e0, e1) - radius, np.maximum(e0, e1) + radius
        i0, i1 = np.searchsorted(self.x, unten[0]), np.searchsorted(self.x, oben[0], side="right")
        j0, j1 = np.searchsorted(self.y, unten[1]), np.searchsorted(self.y, oben[1], side="right")
        k0, k1 = np.searchsorted(self.z, unten[2]), np.searchsorted(self.z, oben[2], side="right")
        if i1 <= i0 or j1 <= j0 or k1 <= k0:
            return None, None
        dx = (self.x[i0:i1] - p[0])[:, None, None]
        dy = (self.y[j0:j1] - p[1])[None, :, None]
        dz = (self.z[k0:k1] - p[2])[None, None, :]
        t = dx * a[0] + dy * a[1] + dz * a[2]
        maske = (t >= von) & (t <= bis) & (dx * dx + dy * dy + dz * dz - t * t <= radius * radius)
        return (slice(i0, i1), slice(j0, j1), slice(k0, k1)), maske

    def trifft(self, spitze, achse, radius, von, bis):
        """Steht im Zylinder Material?"""
        stueck, maske = self._zellen(spitze, achse, radius, von, bis)
        return stueck is not None and bool((self.voll[stueck] & maske).any())

    def abtragen(self, spitze, achse, radius, bis):
        """Das Werkzeug nimmt weg, was in ihm steht."""
        stueck, maske = self._zellen(spitze, achse, radius, 0.0, bis)
        if stueck is not None:
            self.voll[stueck] &= ~maske

    def kugel_abtragen(self, mitte, radius):
        """Eine Kugel nimmt weg, was in ihr steht."""
        p = np.asarray(mitte, dtype=float)
        i0, i1 = np.searchsorted(self.x, p[0] - radius), np.searchsorted(
            self.x, p[0] + radius, "right"
        )
        j0, j1 = np.searchsorted(self.y, p[1] - radius), np.searchsorted(
            self.y, p[1] + radius, "right"
        )
        k0, k1 = np.searchsorted(self.z, p[2] - radius), np.searchsorted(
            self.z, p[2] + radius, "right"
        )
        if i1 <= i0 or j1 <= j0 or k1 <= k0:
            return
        dx = (self.x[i0:i1] - p[0])[:, None, None]
        dy = (self.y[j0:j1] - p[1])[None, :, None]
        dz = (self.z[k0:k1] - p[2])[None, None, :]
        self.voll[i0:i1, j0:j1, k0:k1] &= dx * dx + dy * dy + dz * dz > radius * radius


def _hoechste_je_block(h, jede):
    """Die Höhen auf jede `jede`-te Zelle: je Block die höchste – nichts geht verloren."""
    if jede == 1:
        return h
    n, m = h.shape
    zeilen = np.maximum.reduceat(h, np.arange(0, n, jede), axis=0)
    return np.maximum.reduceat(zeilen, np.arange(0, m, jede), axis=1)


@dataclass
class _Lage:
    """Wo das Werkzeug steht – wie eine Stelle der Flanke."""

    spitze: tuple
    achse: tuple


def _einheit(achse):
    laenge = math.sqrt(sum(float(v) * float(v) for v in achse)) or 1.0
    return tuple(float(v) / laenge for v in achse)


def _zwischen(von, nach, schritt):
    """[(Spitze, Achse)] entlang von `von` nach `nach` (Stellen), `nach` eingeschlossen."""
    laenge = math.dist(von.spitze, nach.spitze)
    n = max(1, int(math.ceil(laenge / schritt)))
    aus = []
    for k in range(1, n + 1):
        t = k / n
        spitze = tuple(a + (b - a) * t for a, b in zip(von.spitze, nach.spitze, strict=True))
        achse = tuple(a + (b - a) * t for a, b in zip(von.achse, nach.achse, strict=True))
        aus.append((spitze, _einheit(achse)))
    return aus


class _Abtrag:
    """Das Werkzeug fährt die Bahn ab und nimmt weg – alle ABTRAG_SCHRITT, nicht je Satz: Die Sätze
    an gekrümmten Wänden sind oft nur Zehntel lang."""

    def __init__(self, abtragen):
        self.abtragen = abtragen
        self.letzte = None

    def fahre(self, von, nach):
        for spitze, achse in _zwischen(von, nach, ABTRAG_SCHRITT):
            if self.letzte is None or math.dist(self.letzte, spitze) >= ABTRAG_SCHRITT:
                self.abtragen(spitze, achse)
                self.letzte = spitze


def fahre_kugel(gitter, punkte, radius, schneide):
    """Eine angestellte Kugelbahn davor nimmt weg: `punkte` (spitze, achse, eilgang) – die Spitze
    ist die der senkrecht gedachten Kugel, ihre Mitte liegt `radius` darüber. Etwas kleiner als das
    Werkzeug: Lieber bleibt Material stehen, als dass frei scheint, was es nicht ist."""
    r = radius - SICHER

    def abtragen(spitze, achse):
        mitte = (spitze[0], spitze[1], spitze[2] + radius)
        gitter.kugel_abtragen(mitte, r)
        gitter.abtragen(mitte, achse, r, schneide - radius)

    _bahn_abfahren(punkte, abtragen)


def fahre_flanke(gitter, punkte, radius, schneide):
    """Eine Flanke davor nimmt weg – `punkte` wie bei fahre_kugel, die Spitze ist die echte."""

    def abtragen(spitze, achse):
        gitter.abtragen(spitze, achse, radius - SICHER, schneide)

    _bahn_abfahren(punkte, abtragen)


def _bahn_abfahren(punkte, abtragen):
    fahrt = _Abtrag(abtragen)
    for von, nach in zip(punkte, punkte[1:], strict=False):
        if not nach.eilgang:
            fahrt.fahre(von, nach)
        uhren.atmen()


def kugelwege_pruefen(punkte, achsen, gitter, radius, schneide):
    """([bahn.Punkt], [Achse]) – die Bahn unter dem Rand (hinterschnitt_bahn): Ihre schnellen Wege
    (Punkt.anteil über 1) sind nur gegen das Teil geprüft. Steht dort noch Material – der Keil,
    wenn die Flanke erst danach kommt –, bleibt der Weg nur bis VORLAUF davor schnell, der Rest
    taucht ein (Manuels tiefe Tasche: mit 10 m/min bis in den Keil). Die Spitze ist die der
    senkrecht gedachten Kugel."""

    def abtragen(spitze, achse):
        mitte = (spitze[0], spitze[1], spitze[2] + radius)
        gitter.kugel_abtragen(mitte, radius - SICHER)
        gitter.abtragen(mitte, achse, radius - SICHER, schneide - radius)

    def frei_bis(von, nach):
        """Wie weit (mm) der Weg frei ist – None: bis ans Ende."""
        wege = _zwischen(von, nach, SCHRITT)
        for k, (spitze, achse) in enumerate(wege):
            mitte = (spitze[0], spitze[1], spitze[2] + radius)
            if gitter.trifft(mitte, achse, radius + RAND, -radius - RAND, schneide - radius):
                return math.dist(von.spitze, nach.spitze) * k / len(wege)
        return None

    fahrt = _Abtrag(abtragen)
    aus_punkte, aus_achsen = list(punkte[:1]), list(achsen[:1])
    for p0, p1, a0, a1 in zip(punkte, punkte[1:], achsen, achsen[1:], strict=False):
        von = _Lage((p0.x, p0.y, p0.z), _einheit(a0))
        nach = _Lage((p1.x, p1.y, p1.z), _einheit(a1))
        uhren.atmen()
        if p1.eilgang:
            aus_punkte.append(p1)
            aus_achsen.append(a1)
            continue
        if p1.anteil > 1.0 and p1.bogen is None:
            frei = frei_bis(von, nach)
            if frei is not None:
                laenge = math.dist(von.spitze, nach.spitze)
                schnell = frei - VORLAUF
                if schnell >= MINDEST:
                    t = schnell / laenge
                    x, y, z = (
                        a + (b - a) * t for a, b in zip(von.spitze, nach.spitze, strict=True)
                    )
                    aus_punkte.append(replace(p1, x=x, y=y, z=z))
                    aus_achsen.append(a1)
                p1 = replace(p1, anteil=1.0, eintauchen=True)
        if p1.anteil <= 1.0:
            fahrt.fahre(von, nach)
        aus_punkte.append(p1)
        aus_achsen.append(a1)
    return aus_punkte, aus_achsen


def _erstes_material(gitter, von, nach, radius):
    """Wie weit (mm) die Spitze von `von` nach `nach` frei eintaucht – None: bis ans Ende."""
    achse = _einheit(von.achse)
    laenge = math.dist(von.spitze, nach.spitze)
    n = max(1, int(math.ceil(laenge / SCHRITT)))
    for k in range(1, n + 1):
        t = k / n
        spitze = tuple(a + (b - a) * t for a, b in zip(von.spitze, nach.spitze, strict=True))
        if gitter.trifft(spitze, achse, radius + RAND, -SCHRITT, VORLAUF):
            return laenge * (k - 1) / n
    return None


def _eintauchen(gitter, von, nach, radius):
    """[Stelle] statt des Eintauchens `von` → `nach`: im Eilgang, bis VORLAUF vor dem Material oder
    dem Ende, den Rest wie bisher."""
    laenge = math.dist(von.spitze, nach.spitze)
    if laenge < 1e-9:
        return [nach]
    frei = _erstes_material(gitter, von, nach, radius)
    frei = (laenge if frei is None else frei) - VORLAUF
    if frei < MINDEST:
        return [nach]
    t = frei / laenge
    spitze = tuple(a + (b - a) * t for a, b in zip(von.spitze, nach.spitze, strict=True))
    return [replace(nach, spitze=spitze, eilgang=True, eintauchen=False), nach]


def _frei_markieren(saetze, frei):
    """[Stelle] zu den `saetze`n (von, nach): `frei` je Satz – ein freies Stück im Freivorschub, wenn
    es lohnt; die letzten VORLAUF davor, wo wieder Material kommt, bleiben im Vorschub."""
    aus = [nach for _von, nach in saetze]
    i = 0
    while i < len(saetze):
        if not frei[i]:
            i += 1
            continue
        ende = i
        while ende < len(saetze) and frei[ende]:
            ende += 1
        laengen = [math.dist(von.spitze, nach.spitze) for von, nach in saetze[i:ende]]
        if sum(laengen) >= MINDEST:
            rest = VORLAUF if ende < len(saetze) else 0.0
            schnell = ende
            while rest > 0.0 and schnell > i:
                schnell -= 1
                rest -= laengen[schnell - i]
            for k in range(i, schnell):
                aus[k] = replace(aus[k], frei=True)
        i = ende
    return aus


def _zufahrt(gitter, fahrt, stellen, radius, schneide):
    """Die Stellen einer Zufahrt, frei wo möglich; `stellen[0]` ist die Stelle davor. Nachgesehen
    wird alle SCHRITT, nicht je Satz."""
    saetze = list(zip(stellen, stellen[1:], strict=False))
    frei = []
    letzte, war_frei = None, True
    for von, nach in saetze:
        for spitze, achse in _zwischen(von, nach, SCHRITT):
            if letzte is None or math.dist(letzte, spitze) >= SCHRITT:
                letzte = spitze
                war_frei = not gitter.trifft(spitze, achse, radius + RAND, 0.0, schneide)
                if not war_frei:
                    break
        frei.append(war_frei)
        if not war_frei:
            fahrt.fahre(von, nach)
        uhren.atmen()
    return _frei_markieren(saetze, frei)


def ohne_luft(stellen, gitter, radius, schneide):
    """Die Stellen der Flanke (flanke_bahn.Stelle), die Wege durch die Luft schnell: das Eintauchen
    im Eilgang bis vor das Material, die Zufahrten und Keil-Umläufe im Freivorschub (Stelle.frei).
    Die Umläufe an der Wand selbst bleiben, wie sie sind. `gitter`: das Material vor der Operation;
    das Abfahren nimmt daraus weg."""

    def abtragen(spitze, achse):
        gitter.abtragen(spitze, achse, radius, schneide)

    fahrt = _Abtrag(abtragen)
    aus = []
    i = 0
    while i < len(stellen):
        stelle = stellen[i]
        davor = stellen[i - 1] if i else None
        uhren.atmen()
        if davor is None or stelle.eilgang:
            aus.append(stelle)
            i += 1
        elif stelle.eintauchen:
            aus.extend(_eintauchen(gitter, davor, stelle, radius))
            fahrt.fahre(davor, stelle)
            i += 1
        elif stelle.zufahrt:
            ende = i
            while ende < len(stellen) and stellen[ende].zufahrt:
                ende += 1
            aus.extend(_zufahrt(gitter, fahrt, stellen[i - 1 : ende], radius, schneide))
            i = ende
        else:
            fahrt.fahre(davor, stelle)
            aus.append(stelle)
            i += 1
    return aus
