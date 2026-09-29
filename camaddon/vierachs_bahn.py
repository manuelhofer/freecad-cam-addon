# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bahnen für die 4-Achs-Bearbeitung: rundum schruppen (Spezifikation W-003,
Abschnitt 9, Stufe V3b).

„Rundum schruppen“ nimmt die Stange in Lagen ab, bis aufs Schlichtaufmaß:
Lage k liegt auf dem Radius R_Stange − k · ap. Je Lage läuft eine Spirale mit
der Steigung „Vorschub je Umdrehung“ von vorne – der Fräser ganz vor der
Stange – bis vor das Futter; die Spitze folgt dem höheren von Lage und
Hüllfläche plus Aufmaß (vierachs_huelle, mit dem Radius R + Aufmaß). Danach
geht es radial hinaus und im Eilgang nach vorne zur nächsten Lage.

- Wo die Stirn das Teil nicht trifft, schneidet die Lage.
- Hinten läuft die Spirale über das Teil hinaus, bis der Fräser es ganz
  verlassen hat: Die Mitte des Fräsers kommt den Überlauf hinter das Teil
  (Vorschlag Fräserradius + UEBERLAUF_ZUGABE), dort auf der Tiefe des letzten
  Stücks Kontur – die Kante hinten am Teil wird fertig (Manuel, 2026-09-29:
  „da muss man schon mindestens mal 6.5 drüber fahren“). Der Rand des Fräsers
  bleibt aber immer den Abstand zum Futter vor der Spannfläche; wie weit die
  Stange dafür herausragen muss, rechnet der Assistent (vierachs_rohteil).
- Der Achse kommt die Spitze nicht näher als der Fräserradius.
- Liegen Punkte auf einer Geraden in (a, r, φ) – eine Lage ohne Teil darunter
  –, bleiben nur ihre Enden und alle HOECHSTENS_GRAD einer.
- Wie viele Lagen es braucht, sagt der tiefste Punkt über dem Teil; vor dem
  Teil (Planaufmaß) schneidet jede Lage nur so tief wie sie selbst.

Gerechnet wird in Rundachs-Koordinaten (a, r, φ) wie in vierachs_huelle.
befehle() macht daraus Path-Befehle: X, Y und Z der Spitze im Rahmen der
Maschine – die Rundachse dreht das Teil darunter, so zeigt FreeCAD die Bahn –,
die Rundachse mit ihrem Buchstaben und der Vorschub nach G93.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import vierachs_huelle as vh
from .sprache import tr

SICHERHEIT = 2.0  # mm – so weit über und vor der Stange fährt der Fräser im Eilgang
# mm – so weit bleibt der Rand des Fräsers vor der Spannfläche (Vorschlag): deutlich mehr
# als der Warnabstand der Kollisionsprüfung (1 mm).
ABSTAND_FUTTER = 5.0
UEBERLAUF_ZUGABE = 0.5  # mm – Überlauf = Fräserradius + das: Der Fräser verlässt das Teil ganz
RAND = 0.005  # mm – zum Aufmaß dazu, für Rundungen im Raster
GLEICH = 1e-9  # mm – so wenig Unterschied gilt als derselbe Radius
# So weit dreht die Rundachse höchstens in einem Satz: FreeCAD 1.1.3 zeigt einen Satz
# über mehrere Umdrehungen als Gerade (PathSegmentWalker rechnet den Winkel modulo 360°).
HOECHSTENS_GRAD = 90.0


@dataclass(frozen=True)
class Schruppwerte:
    """Was das Schruppen braucht; Längen in mm, a längs der Stangenachse im Job."""

    fraeser_radius: float
    stange_radius: float
    zustellung: float  # ap: so tief je Lage, radial
    steigung: float  # so weit längs je Umdrehung der Spirale (ae)
    aufmass: float  # bleibt fürs Schlichten stehen
    a_stange_vorne: float  # das vordere Ende der Stange
    a_futter: float  # die Spannfläche: dahinter steckt die Stange im Futter
    sicherheit: float = SICHERHEIT
    ueberlauf: float = None  # so weit hinter das Teil (Mitte des Fräsers); None: Vorschlag
    abstand_futter: float = ABSTAND_FUTTER  # Rand des Fräsers bis zur Spannfläche


def ueberlauf_vorschlag(fraeser_radius):
    """Der Überlauf, bis der Fräser das Teil ganz verlassen hat: Radius + UEBERLAUF_ZUGABE."""
    return fraeser_radius + UEBERLAUF_ZUGABE


@dataclass(frozen=True)
class Punkt:
    """Ein Punkt der Bahn: Stelle längs, Radius der Spitze, Winkel (Grad, fortlaufend)."""

    eilgang: bool
    a: float
    r: float
    phi: float


@dataclass
class Bahn:
    """Ergebnis von schruppen()."""

    punkte: list  # [Punkt], der erste ist der Start (Eilgang, vor der Stange)
    lagen: int
    r_min: float  # so nah kommt die Spitze der Achse (mm)
    hinten_frei: float = 0.0  # so viel vom hinteren Ende des Teils erreicht der Fräser nicht


def schruppen(netz, laengs, radial, werte, schritt_a=vh.SCHRITT_A, schritt_phi=vh.SCHRITT_PHI):
    """Die Schruppbahn (Bahn) für `netz` (vierachs_huelle.vernetze, im Job) mit den
    Schruppwerten `werte`; `laengs` und `radial` wie in vierachs_huelle.

    ValueError, wenn die Werte nicht gehen – mit einem Satz für den Menschen.
    """
    w = werte
    if w.fraeser_radius <= 0 or w.zustellung <= 0 or w.steigung <= 0:
        raise ValueError(tr("vb.fehler.werte"))
    if w.steigung > 2 * w.fraeser_radius:
        raise ValueError(tr("vb.fehler.steigung"))
    l_, _u, _v = vh.rahmen(laengs, radial)
    a_teil = netz.punkte @ l_
    teil_vorne, teil_hinten = float(a_teil.max()), float(a_teil.min())
    radius = w.fraeser_radius
    ueberlauf = ueberlauf_vorschlag(radius) if w.ueberlauf is None else w.ueberlauf
    a_anfang = w.a_stange_vorne + radius + w.sicherheit
    a_ende = max(teil_hinten - ueberlauf, w.a_futter + radius + w.abstand_futter)
    if a_ende >= teil_vorne + radius:
        raise ValueError(tr("vb.fehler.platz"))
    hinten_frei = max(0.0, a_ende - radius - teil_hinten)

    # Die Spirale: gleich viele Punkte je Umdrehung wie das Raster Winkel hat.
    phi_werte = vh.raster_phi(schritt_phi)
    je_umdrehung = len(phi_werte)
    anzahl = max(1, int(math.ceil((a_anfang - a_ende) / w.steigung * je_umdrehung)))
    k = np.arange(anzahl + 1)
    a = a_anfang - (a_anfang - a_ende) * k / anzahl
    a_werte = vh.raster_a(a_ende - schritt_a, a_anfang + schritt_a, schritt_a)
    huelle = vh.schaftfraeser(netz, laengs, radial, radius + w.aufmass, a_werte, phi_werte)
    huelle = _hinten_weiter(huelle.sicher(), teil_hinten)
    zugabe = w.aufmass + netz.toleranz + RAND

    def boden(versatz):
        """Wie tief die Spitze an jedem Punkt der Spirale darf, wenn sie beim Winkel
        phi[versatz] beginnt."""
        ergebnis = huelle.bei(a, (versatz + k) % je_umdrehung) + zugabe
        ergebnis = np.where(~np.isfinite(ergebnis) & (a < teil_hinten), w.stange_radius, ergebnis)
        return np.maximum(ergebnis, radius)  # nicht näher an die Achse

    # Wie viele Lagen: bis zum tiefsten Punkt über dem Teil, egal wo die Spirale ihn trifft.
    ueber_dem_teil = huelle.r[(huelle.a >= a_ende) & (huelle.a <= a_anfang)]
    ueber_dem_teil = ueber_dem_teil[np.isfinite(ueber_dem_teil)]
    r_min = max(float(ueber_dem_teil.min()) + zugabe, radius) if ueber_dem_teil.size else 0.0
    lagen = 0
    if ueber_dem_teil.size:
        lagen = max(0, int(math.ceil((w.stange_radius - r_min) / w.zustellung - GLEICH)))
    sicher = w.stange_radius + w.sicherheit
    punkte = [Punkt(True, a_anfang, sicher, 0.0)]
    versatz = 0  # die Spirale einer Lage beginnt, wo die letzte endete
    for lage in range(1, lagen + 1):
        r = np.maximum(boden(versatz), w.stange_radius - lage * w.zustellung)
        phi = (versatz + k) * schritt_phi
        for i in _knicke(r, int(round(HOECHSTENS_GRAD / schritt_phi))):
            punkte.append(Punkt(False, float(a[i]), float(r[i]), float(phi[i])))
        versatz += anzahl
        punkte.append(Punkt(True, a_ende, sicher, float(phi[-1])))
        punkte.append(Punkt(True, a_anfang, sicher, float(phi[-1])))
    return Bahn(punkte, lagen, r_min, hinten_frei)


def _hinten_weiter(huelle, teil_hinten):
    """Hinter dem Teil (a < teil_hinten), wo der Fräser es nicht mehr trifft, gilt die Tiefe
    des letzten Stücks Kontur davor – im Überlauf fährt er so aus dem Teil heraus, wie er an
    dessen Ende war, statt auf den Stangenradius zu springen."""
    r = huelle.r.copy()
    for i in range(len(huelle.a) - 2, -1, -1):  # von vorne nach hinten
        if huelle.a[i] < teil_hinten:
            leer = ~np.isfinite(r[i])
            r[i, leer] = r[i + 1, leer]
    return vh.Huelle(huelle.a, huelle.phi, r)


def _knicke(r, abstand):
    """Die Stellen der Spirale, die bleiben: Anfang, Ende, wo der Radius sich ändert, und
    alle `abstand` Stellen eine – dazwischen liegen die Punkte auf einer Geraden in
    (a, r, φ)."""
    anders = np.abs(np.diff(r)) > GLEICH
    bleibt = np.arange(len(r)) % abstand == 0
    bleibt[0] = bleibt[-1] = True
    bleibt[1:-1] |= anders[:-1] | anders[1:]
    return np.nonzero(bleibt)[0]


def befehle(bahn, laengs, radial, buchstabe, drehsinn, vorschub, quer_auf_null=True):
    """Die Bahn als Path-Befehle.

    X, Y und Z sind die Spitze im Rahmen der Maschine: a längs, r radial (die
    Richtung `radial`). Die Rundachse `buchstabe` dreht das Teil darunter:
    Steht das Werkzeug unter φ zum Teil, ist ihr Wert −drehsinn · φ. `drehsinn`
    +1 heißt, ein positiver Wert dreht das Teil rechtshändig um `laengs` – so
    zeigt FreeCAD die Bahn. Vorschübe stehen zwischen G93 und G94: F = 1 ÷ Zeit,
    damit der Fräser am Werkstück mit `vorschub` (mm/min) fährt, egal wie weit er
    von der Achse weg ist. CAM führt F in mm/s, der Postprozessor schreibt ×60 –
    deshalb steht hier F ÷ 60. `quer_auf_null`: die Achse quer (bei C das Y) am
    Anfang auf 0, damit das Werkzeug auf der Mitte steht.
    """
    import Path

    l_, u_, v_ = vh.rahmen(laengs, radial)
    genutzt = [i for i in range(3) if abs(l_[i]) > GLEICH or abs(u_[i]) > GLEICH]
    quer = [i for i in range(3) if i not in genutzt]
    radial_achsen = [i for i in range(3) if abs(u_[i]) > GLEICH]

    def lage(punkt):
        spitze = l_ * punkt.a + u_ * punkt.r
        werte = {"XYZ"[i]: float(spitze[i]) for i in genutzt}
        werte[buchstabe] = -drehsinn * punkt.phi
        return werte

    ergebnis = [
        Path.Command(
            f"(4-Achs rundum: {buchstabe} dreht das Teil, Radius in "
            f"{''.join('XYZ'[i] for i in radial_achsen)}, Vorschub G93)"
        )
    ]
    if not bahn.punkte:
        return ergebnis
    start = bahn.punkte[0]
    spitze = l_ * start.a + u_ * start.r
    ergebnis.append(Path.Command("G0", {"XYZ"[i]: float(spitze[i]) for i in radial_achsen}))
    anfang = lage(start)
    if quer_auf_null:
        anfang.update({"XYZ"[i]: 0.0 for i in quer})
    ergebnis.append(Path.Command("G0", anfang))
    ergebnis.append(Path.Command("G93"))
    vorher = start
    for punkt in bahn.punkte[1:]:
        if punkt.eilgang:
            ergebnis.append(Path.Command("G0", lage(punkt)))
        else:
            weg = _weg(vorher, punkt)
            if weg < 1e-6:
                continue
            werte = lage(punkt)
            werte["F"] = vorschub / weg / 60.0
            ergebnis.append(Path.Command("G1", werte))
        vorher = punkt
    ergebnis.append(Path.Command("G94"))
    return ergebnis


def _weg(von, nach):
    """Der Weg der Spitze am Werkstück von einem Punkt zum nächsten (mm)."""
    r = (von.r + nach.r) / 2
    bogen = r * math.radians(nach.phi - von.phi)
    return math.sqrt((nach.a - von.a) ** 2 + (nach.r - von.r) ** 2 + bogen * bogen)


def dauer(bahn, vorschub):
    """So lange fährt die Bahn im Vorschub (Minuten) – ohne Eilgänge."""
    zeit = 0.0
    for von, nach in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        if not nach.eilgang:
            zeit += _weg(von, nach) / vorschub
    return zeit
