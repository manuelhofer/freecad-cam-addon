# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Form eines Fräsers als Drehprofil – für die Hüllfläche der 4-Achs-Bearbeitung
(vierachs_huelle), den Abtrag in der Simulation und die Schneide in Abfahren und Kollision
(Spezifikation W-003, Stufe V5a).

Ein Fräser, der von außen auf das Teil zeigt, trifft es mit seiner Stirn. Beschrieben wird
deren Fläche als Profil: z ist die Höhe über der Spitze längs der Werkzeugachse, ρ der Abstand
von ihr. Ein Profil ist eine Folge von Stücken, jedes mit wachsendem ρ und nie fallendem z:

- EBEN: eine Scheibe, z fest (Schaftfräser, die Spitze des Fasenfräsers),
- BOGEN: ein erhabener Kreisbogen, die untere Hälfte eines Kreises (Kugel, Eckradius),
- HOHL: ein hohler Kreisbogen, die obere Hälfte eines Kreises (Radienfräser),
- GERADE: ein Kegel (Konik-, Fasenfräser, die Platten des Planfräsers).

Über dem letzten Stück geht der Fräser zylindrisch weiter. Die Maße kommen wie für sein Bild
und für CAM aus werkzeugform – so rechnet die Bahn mit dem Werkzeug, das man sieht.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass
from functools import cached_property

import numpy as np

from . import werkzeuge as wz
from . import werkzeugform as wf

EBEN, BOGEN, HOHL, GERADE = "eben", "bogen", "hohl", "gerade"
_GENAU = 1e-9  # mm – so nah gilt als dieselbe Stelle
_BOGEN_SCHRITT = math.radians(0.25)  # so fein wird ein Bogen für die konvexe Hülle unterteilt


@dataclass(frozen=True)
class Stueck:
    """Ein Stück des Profils von rho_von bis rho_bis (mm).

    EBEN hat die Höhe z_von; GERADE geht von z_von nach z_bis; BOGEN und HOHL liegen auf dem
    Kreis um `mitte` (ρ, z) mit `radius` – BOGEN auf seiner unteren, HOHL auf seiner oberen
    Hälfte."""

    art: str
    rho_von: float
    rho_bis: float
    z_von: float = 0.0
    z_bis: float = 0.0
    mitte: tuple = (0.0, 0.0)
    radius: float = 0.0

    def hoehe(self, rho):
        """z an den Stellen `rho` (numpy), die im Stück liegen müssen."""
        rho = np.asarray(rho, dtype=float)
        if self.art == EBEN:
            return np.full(rho.shape, self.z_von)
        if self.art == GERADE:
            breite = self.rho_bis - self.rho_von
            if breite <= _GENAU:
                return np.full(rho.shape, self.z_von)
            return self.z_von + (rho - self.rho_von) * ((self.z_bis - self.z_von) / breite)
        quer = np.sqrt(np.maximum(self.radius**2 - (rho - self.mitte[0]) ** 2, 0.0))
        return self.mitte[1] - quer if self.art == BOGEN else self.mitte[1] + quer

    def punkt(self, rho):
        """(ρ, z) an der Stelle `rho`."""
        return float(rho), float(self.hoehe(rho))

    def normale(self, rho):
        """Die Normale (ρ, z) an der Stelle `rho`, vom Fräser weg (nach unten, außen)."""
        if self.art == EBEN:
            return 0.0, -1.0
        if self.art == GERADE:
            d_rho, d_z = self.rho_bis - self.rho_von, self.z_bis - self.z_von
            laenge = math.hypot(d_rho, d_z)
            return d_z / laenge, -d_rho / laenge
        p_rho, p_z = self.punkt(rho)
        n_rho, n_z = (p_rho - self.mitte[0]) / self.radius, (p_z - self.mitte[1]) / self.radius
        return (n_rho, n_z) if self.art == BOGEN else (-n_rho, -n_z)

    def unterteilt(self):
        """Punkte (ρ, z) auf dem Stück, Bögen fein unterteilt – für die konvexe Hülle."""
        if self.art in (EBEN, GERADE):
            return [self.punkt(self.rho_von), self.punkt(self.rho_bis)]
        von, bis = (self._winkel(r) for r in (self.rho_von, self.rho_bis))
        anzahl = max(2, int(math.ceil(abs(bis - von) / _BOGEN_SCHRITT)) + 1)
        return [
            (
                self.mitte[0] + self.radius * math.cos(w),
                self.mitte[1] + self.radius * math.sin(w),
            )
            for w in np.linspace(von, bis, anzahl)
        ]

    def _winkel(self, rho):
        p_rho, p_z = self.punkt(rho)
        return math.atan2(p_z - self.mitte[1], p_rho - self.mitte[0])


@dataclass(frozen=True)
class Form:
    """Die Stirn eines Fräsers als Folge von Stücken (Stueck), von der Spitze (ρ = 0, z = 0)
    nach außen."""

    stuecke: tuple

    @property
    def radius(self):
        """Der größte Radius der Stirn (mm) – darüber geht der Fräser zylindrisch weiter."""
        return self.stuecke[-1].rho_bis

    @property
    def hoehe_rand(self):
        """z am Rand (ρ = radius)."""
        return float(self.stuecke[-1].hoehe(self.radius))

    @property
    def eben(self):
        """Nur eine Scheibe – der Schaftfräser."""
        return len(self.stuecke) == 1 and self.stuecke[0].art == EBEN

    @property
    def kugel(self):
        """Der Radius der Kugel an der Spitze (Kugel-, Konikfräser), sonst 0."""
        erstes = self.stuecke[0]
        if erstes.art == BOGEN and abs(erstes.mitte[0]) < _GENAU and erstes.rho_von < _GENAU:
            return erstes.radius
        return 0.0

    @property
    def nur_kugel(self):
        """Nichts als die Kugel – der Kugelfräser."""
        return len(self.stuecke) == 1 and self.kugel > 0

    @property
    def konvex(self):
        """Ohne hohle Stücke: Längs einer Kante ist die Höhe unter dem Fräser dann konkav."""
        return all(s.art != HOHL for s in self.stuecke)

    def aussen(self):
        """Die Form ohne Hohlkehle: jedes hohle Stück durch seine Sehne ersetzt. Die Sehne liegt
        unter dem Bogen – ein Fräser mit ihr bleibt höher, das Teil sicher. So rechnet die
        Hüllfläche den Radienfräser; seine Kehle rundet beim 4-Achs-Fräsen keine Kante."""
        if self.konvex:
            return self
        return Form(
            tuple(
                (
                    Stueck(
                        GERADE,
                        s.rho_von,
                        s.rho_bis,
                        z_von=float(s.hoehe(s.rho_von)),
                        z_bis=float(s.hoehe(s.rho_bis)),
                    )
                    if s.art == HOHL
                    else s
                )
                for s in self.stuecke
            )
        )

    def scheiben(self):
        """(Radius, Höhe) der ebenen Stücke und des Rands: Dort endet eine Kante, die unter dem
        Fräser herauskommt – diese Stellen rechnet vierachs_huelle genau."""
        ergebnis = [(s.rho_bis, s.z_von) for s in self.stuecke if s.art == EBEN]
        if not ergebnis or abs(ergebnis[-1][0] - self.radius) > _GENAU:
            ergebnis.append((self.radius, self.hoehe_rand))
        return ergebnis

    def hoehe(self, rho):
        """z über der Spitze im Abstand `rho` von der Achse (numpy); inf, wo der Fräser nicht
        ist (rho > radius)."""
        rho = np.asarray(rho, dtype=float)
        z = np.full(rho.shape, np.inf)
        for stueck in self.stuecke:
            drin = (rho >= stueck.rho_von - _GENAU) & (rho <= stueck.rho_bis + _GENAU)
            if drin.any():
                wert = stueck.hoehe(np.clip(rho, stueck.rho_von, stueck.rho_bis))
                z = np.where(drin, np.minimum(z, wert), z)
        return z

    def kammhoehe(self, schrittweite):
        """So hoch bleibt zwischen zwei Bahnen im Abstand `schrittweite` stehen (mm): die Höhe
        der Stirn in der Mitte dazwischen – 0 unter der Scheibe, inf, wenn die Bahnen weiter
        auseinander liegen als der Fräser breit ist."""
        return float(self.hoehe(schrittweite / 2))

    @cached_property
    def _huelle(self):
        """Die konvexe Hülle des Profils von unten: Punkte (ρ, z) und je Kante ihr Winkel gegen
        die Ebene quer zur Achse (rad, steigend) – die Seite des Fräsers als letzte, senkrecht."""
        punkte = [p for stueck in self.stuecke for p in stueck.unterteilt()]
        punkte.append((self.radius, self.hoehe_rand + max(self.radius, 1.0)))
        punkte.sort()
        unten = []
        for p in punkte:
            while len(unten) >= 2 and _kreuz(unten[-2], unten[-1], p) <= _GENAU * _GENAU:
                unten.pop()
            unten.append(p)
        rho = np.array([p[0] for p in unten])
        z = np.array([p[1] for p in unten])
        winkel = np.arctan2(np.diff(z), np.diff(rho))
        return rho, z, np.maximum.accumulate(winkel)

    def stuetze(self, neigung):
        """(ρ, z) der Stelle, mit der der Fräser eine Ebene zuerst berührt, deren Normale um
        `neigung` (rad, numpy, 0 … < π/2) gegen die Werkzeugachse geneigt ist – auf der Seite, zu
        der die Ebene ansteigt. Quer zur Achse (0) berührt die Mitte."""
        rho, z, winkel = self._huelle
        i = np.searchsorted(winkel, np.asarray(neigung, dtype=float), side="left")
        return rho[i], z[i]

    def mit_aufmass(self, aufmass):
        """Der Fräser um `aufmass` größer – rundum, wie von einer Kugel mit diesem Radius
        abgerollt –, wieder mit der Spitze bei z = 0. Wer damit rechnet, hebt das Ergebnis um
        `aufmass`: So bleibt das Aufmaß auch an steilen Wänden genau."""
        if aufmass <= 0:
            return self
        neu = []
        vorher = None  # (Punkt am Ende, Normale dort) des vorigen Stücks
        for stueck in self.stuecke:
            if vorher is not None:
                neu.extend(_ecke(vorher[0], vorher[1], stueck.normale(stueck.rho_von), aufmass))
            versetzt = _versetzt(stueck, aufmass)
            if versetzt is not None:
                neu.append(versetzt)
            vorher = (stueck.punkt(stueck.rho_bis), stueck.normale(stueck.rho_bis))
        neu.extend(_ecke(vorher[0], vorher[1], (1.0, 0.0), aufmass))  # zur Seite hin
        return Form(tuple(_gehoben(s, aufmass) for s in neu))


def _kreuz(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _ecke(punkt, von, bis, radius):
    """Wo die Normale springt (eine Ecke), rollt die Kugel um die Ecke: ein Bogen um sie."""
    w_von, w_bis = math.atan2(von[1], von[0]), math.atan2(bis[1], bis[0])
    if w_bis - w_von <= 1e-12:
        return []
    return [
        Stueck(
            BOGEN,
            punkt[0] + radius * von[0],
            punkt[0] + radius * bis[0],
            mitte=punkt,
            radius=radius,
        )
    ]


def _versetzt(stueck, d):
    """Das Stück um `d` nach außen versetzt (längs seiner Normale); None, wenn es verschwindet."""
    s = stueck
    if s.art == EBEN:
        return Stueck(EBEN, s.rho_von, s.rho_bis, z_von=s.z_von - d)
    if s.art == GERADE:
        n_rho, n_z = s.normale(s.rho_von)
        return Stueck(
            GERADE,
            s.rho_von + d * n_rho,
            s.rho_bis + d * n_rho,
            z_von=s.z_von + d * n_z,
            z_bis=s.z_bis + d * n_z,
        )
    radius = s.radius + d if s.art == BOGEN else s.radius - d
    if radius <= _GENAU:
        return None
    faktor = radius / s.radius
    return Stueck(
        s.art,
        s.mitte[0] + (s.rho_von - s.mitte[0]) * faktor,
        s.mitte[0] + (s.rho_bis - s.mitte[0]) * faktor,
        mitte=s.mitte,
        radius=radius,
    )


def _gehoben(stueck, d):
    """Das Stück um `d` höher."""
    s = stueck
    return Stueck(
        s.art,
        s.rho_von,
        s.rho_bis,
        z_von=s.z_von + d,
        z_bis=s.z_bis + d,
        mitte=(s.mitte[0], s.mitte[1] + d),
        radius=s.radius,
    )


# --- Die Formen --------------------------------------------------------------------------


def scheibe(radius):
    """Schaftfräser: eine ebene Stirn."""
    return Form((Stueck(EBEN, 0.0, radius),))


def kugel(radius):
    """Kugelfräser: die untere Hälfte einer Kugel."""
    return Form((Stueck(BOGEN, 0.0, radius, mitte=(0.0, radius), radius=radius),))


def torus(radius, eckradius):
    """Torusfräser: eben bis radius − eckradius, dann gerundet."""
    if eckradius <= _GENAU:
        return scheibe(radius)
    if eckradius >= radius - _GENAU:
        return kugel(radius)
    innen = radius - eckradius
    return Form(
        (
            Stueck(EBEN, 0.0, innen),
            Stueck(BOGEN, innen, radius, mitte=(innen, eckradius), radius=eckradius),
        )
    )


def konik(radius, kegelwinkel, schneidenlaenge, radius_oben):
    """Konikfräser: Kugel mit `radius` an der Spitze, darüber der Kegel mit `kegelwinkel` (Grad,
    je Seite) bis zur Schneidenlänge, wo er `radius_oben` hat (werkzeugform.konus)."""
    alpha = math.radians(kegelwinkel)
    if alpha <= 1e-9:
        return kugel(radius)
    rho_t, z_t = radius * math.cos(alpha), radius * (1 - math.sin(alpha))
    if schneidenlaenge <= z_t + _GENAU or radius_oben <= rho_t + _GENAU:
        return kugel(radius)
    return Form(
        (
            Stueck(BOGEN, 0.0, rho_t, mitte=(0.0, radius), radius=radius),
            Stueck(GERADE, rho_t, radius_oben, z_von=z_t, z_bis=schneidenlaenge),
        )
    )


def kegel(radius_spitze, radius, hoehe):
    """Fasenfräser: eben bis `radius_spitze` (0 = spitz), dann der Kegel bis `radius` in der
    Höhe `hoehe`."""
    stuecke = []
    if radius_spitze > _GENAU:
        stuecke.append(Stueck(EBEN, 0.0, radius_spitze))
    stuecke.append(Stueck(GERADE, radius_spitze, radius, z_von=0.0, z_bis=hoehe))
    return Form(tuple(stuecke))


def radien(radius_spitze, profilradius, radius):
    """Radienfräser: eben bis `radius_spitze` (die Führung), dann die Hohlkehle mit
    `profilradius` bis `radius` – ihr Mittelpunkt liegt auf der Höhe der Spitze, wie in
    werkzeugform.radienprofil."""
    mitte = radius_spitze + profilradius
    stuecke = []
    if radius_spitze > _GENAU:
        stuecke.append(Stueck(EBEN, 0.0, radius_spitze))
    stuecke.append(Stueck(HOHL, radius_spitze, radius, mitte=(mitte, 0.0), radius=profilradius))
    return Form(tuple(stuecke))


# Welche Arten eine Form haben; Form- und Gewindefräser kennt das Addon nicht genau genug.
ARTEN = (
    wz.SCHAFTFRAESER,
    wz.KUGELFRAESER,
    wz.TORUSFRAESER,
    wz.KONIKFRAESER,
    wz.SCHWALBENSCHWANZFRAESER,
    wz.LOLLIPOPFRAESER,
    wz.FASENFRAESER,
    wz.RADIENFRAESER,
    wz.PLANFRAESER,
    wz.NUTENFRAESER,
)


def von_werkzeug(werkzeug):
    """Die Form eines Fräsers aus der Werkzeugverwaltung – mit denselben Maßen wie sein Bild
    (werkzeugform) –, oder None, wenn das Addon sie nicht kennt."""
    w = werkzeug
    r = w.durchmesser / 2
    if r <= 0 or w.art not in ARTEN:
        return None
    if w.art in (wz.KUGELFRAESER, wz.LOLLIPOPFRAESER):
        return kugel(r)
    if w.art == wz.TORUSFRAESER:
        return torus(r, min(wz.mass(w, "eckradius"), r))
    if w.art == wz.KONIKFRAESER:
        schneidenlaenge, winkel, oben = wf.konus(w)
        return konik(r, winkel, schneidenlaenge, oben)
    if w.art == wz.FASENFRAESER:
        spitze, hoehe, _winkel = wf.kegel(w)
        return kegel(spitze / 2, r, hoehe)
    if w.art == wz.RADIENFRAESER:
        profil, spitze, _hoehe = wf.radienprofil(w)
        return radien(spitze / 2, profil, r)
    if w.art == wz.PLANFRAESER:
        return _planfraeser(w, r)
    # Schaft-, Nuten-, Schwalbenschwanzfräser: Was über der Stirn schmaler wird, trifft von
    # außen nichts zuerst.
    return scheibe(r)


def _planfraeser(w, r):
    """Die Platten schneiden unten mit dem Einstellwinkel – wie im Bild (werkzeugform)."""
    ap = wz.mass(w, "schneidenlaenge")
    kappa = wz.wert(w, "einstellwinkel") or 90.0
    innen = ap / math.tan(math.radians(kappa)) if kappa < 89.9 else 0.0
    if innen <= _GENAU or innen >= r:
        return scheibe(r)
    return kegel(r - innen, r, ap)
