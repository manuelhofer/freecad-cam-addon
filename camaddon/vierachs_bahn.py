# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bahnen für die 4-Achs-Bearbeitung: rundum schruppen und rundum schlichten
(Spezifikation W-003, Abschnitt 9, Stufen V3b und V5b).

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

„Rundum schlichten“ fährt eine Spirale mit der Schrittweite als Steigung, die
Spitze auf der Hüllfläche des Schlichtfräsers mit seiner Form (fraeserform) plus
Aufmaß – genau an den Stellen der Spirale gerechnet (vierachs_huelle.je_winkel),
alle SCHRITT_PHI_SCHLICHTEN Grad ein Punkt. Wo die Bahn sich zwischen zwei
Punkten nach außen wölbt, hebt sie sich um den Sehnenfehler; gerade Stücke fasst
sie zusammen, solange die Bahn höchstens BAHN_TOLERANZ über den Punkten bleibt
und nie darunter. Vor und hinter dem Teil bleibt die Spitze auf der Tiefe seines
Endes, wie beim Schruppen. Mit dem Rest nach dem Schruppen (restmaterial)
schneidet sie nie tiefer als den Radius des Schlichtfräsers (mindestens das
Aufmaß des Schruppens plus 0,5 mm): Wo mehr stehen blieb – in einer Innenecke,
einer engen Nut –, fährt sie vorher in Stufen, nur über den Umdrehungen, wo es
nötig ist.

„Linien längs“ (V4c, Muster LINIEN) schlichtet statt mit der Spirale in Linien längs der
Achse bei festem Winkel: für Flächen, die nicht rundum gehen – eine Abflachung, eine Nut, eine
Nocke – mit dem Kugel- oder Torusfräser. Die Linien liegen rundum gleich weit auseinander,
höchstens Schrittweite ÷ größter Radius (so bleibt zwischen zweien nicht mehr stehen als
zwischen zwei Umdrehungen der Spirale), und laufen gegenläufig: Am Ende einer Linie dreht die
Rundachse in der Tiefe zur nächsten weiter, wo die dort auch fräst – sonst hebt der Fräser ab.
Mit gewählten Flächen nur die Linien und Stücke über dem Bereich; die Stufen nach dem Schruppen
wie bei der Spirale.

Mit gewählten Flächen (Stufe V4, vierachs_flaechen) fräsen beide nur im Bereich, in dem
der Fräser eine von ihnen berührt; gerechnet wird weiter gegen das ganze Teil. Dazwischen hebt
er über die Stange ab und fährt im Eilgang weiter (Manuel, 2026-09-30: „je nach Rohteil
abheben und irgendwo wieder einsetzen, so dass er nicht kaputt geht“). Wieder hinein geht es
im Eilgang bis knapp über das, was dort noch steht, dann:

- beim Schruppen senkrecht mit dem Eintauchvorschub, wo die Umdrehung davor an derselben
  Stelle schon gefräst hat – die Mitte des Fräsers steht dann über Freiem, er taucht nur mit
  dem Rand ein –, sonst über eine Rampe mit dem Eintauchwinkel längs der Bahn, hin und her,
  bis er unten ist, und auf der Bahn zurück zum Anfang. Jede Lage fährt dieselben Stellen wie
  die davor; so steht über jeder Stelle höchstens noch die Tiefe der Lage davor.
- beim Schlichten senkrecht mit dem Eintauchvorschub: Dort steht nur das Aufmaß.

Gerechnet wird in Rundachs-Koordinaten (a, r, φ) wie in vierachs_huelle.
befehle() macht daraus Path-Befehle: X, Y und Z der Spitze im Rahmen der
Maschine – die Rundachse dreht das Teil darunter, so zeigt FreeCAD die Bahn –,
die Rundachse mit ihrem Buchstaben und der Vorschub nach G93.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import spindel as sp
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
SCHRITT_PHI_SCHLICHTEN = 0.5  # Grad – so dicht liegen die Punkte der Schlichtspirale
TOLERANZ_SCHLICHTEN = 0.005  # mm – so fein wird das Teil fürs Schlichten vernetzt
BAHN_TOLERANZ = 0.002  # mm – so weit darf die zusammengefasste Bahn über den Punkten liegen
SCHLICHT_ZUGABE = 0.5  # mm – Schlichten schneidet mindestens Aufmaß des Schruppens + das
# mm – höchstens so viel hebt der Sehnenfehler einen Punkt: Er gilt für Rundungen; an einer
# Kante springt die Hüllfläche, dort dringt die Gerade kaum ein (längs, um Tausendstel).
SEHNE_HOECHSTENS = 0.02
# mm – so viel weiter als Fräser, Aufmaß und Vernetzung steht ein Ring vor der Wand (D-42)
RING_LUFT = 0.01
EINTAUCHWINKEL = 5.0  # Grad – so steil taucht die Rampe ein, wenn das Werkzeug nichts sagt
RAMPE_MINDESTENS = 0.5  # mm – ein kürzeres Stück hat keinen Platz für eine Rampe
RAMPE_HOECHSTENS = 200  # so oft läuft eine Rampe höchstens hin und her
# So viele Nachkommastellen behält FreeCAD von F, wenn es die Bahn im Dokument speichert.
F_STELLEN = 6
# Das Muster beim Schlichten (V4c): die Spirale, oder Linien längs der Achse bei festem Winkel.
SPIRALE = "spirale"
LINIEN = "linien"
MUSTER = (SPIRALE, LINIEN)
SCHRITT_A_LINIEN = vh.SCHRITT_A  # mm – so dicht liegen die Punkte einer Linie längs


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
    # So weit reicht der Halter seitlich über die Werkzeugachse (halter.seitlich): Reicht er
    # weiter als der Fräser, gilt der Abstand zum Futter von seinem Rand.
    halter: float = 0.0
    # (a, Seite) der Wände des Teils quer zur Achse (vierachs_operation.waende): Vor jeder
    # hält die Spirale eine Umdrehung an – der Ringgang (D-42).
    waende: tuple = ()
    # Wo die Mitte des Fräsers fräst (vierachs_flaechen.Bereich, V4); None: überall – rundum.
    bereich: object = None
    eintauchwinkel: float = EINTAUCHWINKEL  # Grad, für die Rampe ins Material
    # Die Spirale im Gleichlauf für M3 (spindel.fuer_m3): False – andersherum (M4, Gegenlauf).
    gleichlauf: bool = True


@dataclass(frozen=True)
class Schlichtwerte:
    """Was das Schlichten braucht; Längen in mm, a längs der Stangenachse im Job."""

    form: object  # fraeserform.Form des Schlichtfräsers
    stange_radius: float
    schrittweite: float  # so weit längs je Umdrehung der Spirale
    aufmass: float  # bleibt stehen (0: fertig)
    a_stange_vorne: float
    a_futter: float
    sicherheit: float = SICHERHEIT
    ueberlauf: float = None  # so weit hinter das Teil (Mitte des Fräsers); None: Vorschlag
    abstand_futter: float = ABSTAND_FUTTER
    halter: float = 0.0  # wie bei Schruppwerte
    waende: tuple = ()  # wie bei Schruppwerte
    # Der Rest nach dem Schruppen: (a, φ in rad, r) wie restmaterial.Stange; None: kein Schutz.
    rest: tuple = None
    aufmass_schruppen: float = 0.0  # so viel ließ das Schruppen stehen
    bereich: object = None  # wie bei Schruppwerte
    muster: str = SPIRALE  # SPIRALE oder LINIEN (Linien längs, V4c)
    gleichlauf: bool = True  # wie bei Schruppwerte


@dataclass
class Schlichtbahn:
    """Ergebnis von schlichten()."""

    punkte: list  # [Punkt], der erste ist der Start (Eilgang, vor der Stange)
    umdrehungen: float
    r_min: float  # so nah kommt die Spitze der Achse (mm)
    kammhoehe: float  # so hoch bleibt zwischen zwei Bahnen stehen (auf ebener Fläche, mm)
    hinten_frei: float = 0.0  # so viel vom hinteren Ende des Teils erreicht der Fräser nicht
    vorstufen: int = 0  # so oft fährt es vor, wo das Schruppen mehr stehen ließ
    grenze: float = 0.0  # so tief schneidet Schlichten je Stufe höchstens (mm)
    linien: int = 0  # Linien längs (Muster LINIEN): so viele Linien hat die Bahn


def rillenhoehe(fraeser_radius, eckradius, steigung):
    """So hoch bleiben Rillen zwischen zwei Bahnen der Spirale stehen, wenn die Stirn des
    Fräsers mit `eckradius` gerundet ist (beim Kugelfräser: sein Radius), in mm. Die
    Hüllfläche rechnet mit der Stirn als flacher Scheibe – das Teil bleibt sicher, an den
    Rundungen bleibt mehr stehen: in der Mitte zwischen zwei Bahnen am meisten."""
    seitlich = steigung / 2 - (fraeser_radius - eckradius)
    if eckradius <= 0 or seitlich <= 0:
        return 0.0
    seitlich = min(seitlich, eckradius)
    return eckradius - math.sqrt(eckradius * eckradius - seitlich * seitlich)


def ueberlauf_vorschlag(fraeser_radius):
    """Der Überlauf, bis der Fräser das Teil ganz verlassen hat: Radius + UEBERLAUF_ZUGABE."""
    return fraeser_radius + UEBERLAUF_ZUGABE


def _ende(teil_hinten, ueberlauf, radius, w):
    """Bis wohin die Mitte des Fräsers längs fährt (a): den Überlauf hinter das Teil, aber
    nicht näher ans Futter, als Fräser oder Halter (der weiter reicht) mit Abstand erlauben."""
    return max(teil_hinten - ueberlauf, w.a_futter + max(radius, w.halter) + w.abstand_futter)


def _kein_platz(radius, w):
    """Der Satz, wenn zwischen Futter und Teil kein Platz ist – mit dem Halter, wenn er es
    ist, der weiter reicht."""
    if w.halter > radius:
        return tr("vb.fehler.platz_halter")
    return tr("vb.fehler.platz")


def _ringe(waende, abstand, a_von, a_bis):
    """Wo die Spirale eine Umdrehung anhält (Ringgang, D-42): vor jeder Wand (a, Seite) so
    weit, dass der Fräser sie berührt – `abstand` (Radius plus Aufmaß) zu der Seite hin, zu
    der sie schaut; nur zwischen a_von und a_bis, von vorn nach hinten, jede Stelle einmal."""
    stellen = {round(a + seite * abstand, 6) for a, seite in waende}
    return sorted((s for s in stellen if a_von < s < a_bis), reverse=True)


def _mit_ringen(a, ringe, je_umdrehung):
    """Die Spirale `a` (je Punkt, fallend) mit einem Ring je Stelle in `ringe`:
    (a, Winkelschritte, Herkunft). Ein Ring sind je_umdrehung Punkte bei festem a; danach läuft
    die Spirale eine Umdrehung später weiter. Herkunft: die Nummer des Punkts der Spirale,
    beim Ring −1 − seine Nummer."""
    k = np.arange(len(a))
    teile_a, teile_k, teile_h = [], [], []
    versatz = 0
    anfang = 0
    for nummer, stelle in enumerate(ringe):
        i = int(np.searchsorted(-a, -stelle, side="left"))  # der erste Punkt mit a <= stelle
        teile_a += [a[anfang:i], np.full(je_umdrehung, stelle)]
        teile_k += [k[anfang:i] + versatz, k[i] + versatz + np.arange(je_umdrehung)]
        teile_h += [k[anfang:i], np.full(je_umdrehung, -1 - nummer)]
        versatz += je_umdrehung
        anfang = i
    teile_a.append(a[anfang:])
    teile_k.append(k[anfang:] + versatz)
    teile_h.append(k[anfang:])
    return np.concatenate(teile_a), np.concatenate(teile_k), np.concatenate(teile_h)


def _ring_radien(r, herkunft, schritte, ring_r, je_umdrehung):
    """Die Radien der Spirale mit Ringen (_mit_ringen): je Ring seine Zeile
    `ring_r[nummer]` (je Winkel) an seinen Punkten, sonst `r` – je Punkt der Spirale mit
    Ringen, oder (so lang wie `herkunft` nicht) je Punkt der Spirale ohne sie."""
    ergebnis = np.array(r, dtype=float)
    if len(ergebnis) != len(herkunft):
        ergebnis = np.empty(len(herkunft))
        spirale = herkunft >= 0
        ergebnis[spirale] = np.asarray(r)[herkunft[spirale]]
    for nummer, zeile in enumerate(ring_r):
        drin = herkunft == -1 - nummer
        ergebnis[drin] = zeile[schritte[drin] % je_umdrehung]
    return ergebnis


@dataclass(frozen=True)
class Punkt:
    """Ein Punkt der Bahn: Stelle längs, Radius der Spitze, Winkel (Grad, fortlaufend);
    `eintauchen`: hierher mit dem Eintauchvorschub (senkrecht ins Material). `q`: der Versatz
    der Spitze quer zur Werkzeugachse (mm, bei C das Y) – 0 bei den Rundum-Bahnen, deren
    Spitze auf dem Strahl von der Achse steht; „Plan indexiert“ (vierachs_planbahn) fährt
    damit Zeilen über eine ebene Fläche. Der Radius ist dann die Höhe der Spitze längs der
    Werkzeugachse, der Winkel der der Rundachse."""

    eilgang: bool
    a: float
    r: float
    phi: float
    eintauchen: bool = False
    q: float = 0.0
    anteil: float = 1.0  # so viel vom Vorschub (die Nut in voller Breite: weniger)


@dataclass
class Bahn:
    """Ergebnis von schruppen()."""

    punkte: list  # [Punkt], der erste ist der Start (Eilgang, vor der Stange)
    lagen: int
    r_min: float  # so nah kommt die Spitze der Achse (mm)
    hinten_frei: float = 0.0  # so viel vom hinteren Ende des Teils erreicht der Fräser nicht


def _drehung(a_anfang, a_ende, gleichlauf):
    """+1, wenn der Winkel der Spirale steigen muss, sonst −1 (P-2026-10-02-23). Im Rahmen des
    Teils – radial (φ = 0), quer, längs – zeigt der Fräser zur Achse, fährt mit steigendem φ
    quer, und das Material liegt dort, wohin die Spirale längs vorrückt: spindel.ist_gleichlauf
    sagt, ob das für M3 Gleichlauf ist. Welche Richtung der Rundachse das an der Maschine ist,
    rechnet befehle() mit ihrem Drehsinn – so stimmt es auf jeder Maschine."""
    vor = 1.0 if a_ende > a_anfang else -1.0
    steigend = sp.ist_gleichlauf((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, vor))
    return 1 if steigend == bool(gleichlauf) else -1


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
    a_ende = _ende(teil_hinten, ueberlauf, radius, w)
    if a_ende >= teil_vorne + radius:
        raise ValueError(_kein_platz(radius, w))
    hinten_frei = max(0.0, a_ende - radius - teil_hinten)

    # Die Spirale: gleich viele Punkte je Umdrehung wie das Raster Winkel hat.
    phi_werte = vh.raster_phi(schritt_phi)
    je_umdrehung = len(phi_werte)
    anzahl = max(1, int(math.ceil((a_anfang - a_ende) / w.steigung * je_umdrehung)))
    k = np.arange(anzahl + 1)
    a = a_anfang - (a_anfang - a_ende) * k / anzahl
    # Mit gewählten Flächen reicht die Hüllfläche über ihren Bereich – dort liegen alle Zeilen.
    a_von, a_bis = a_ende, a_anfang
    if w.bereich is not None and w.bereich.drin.any():
        belegt = w.bereich.a[w.bereich.drin.any(axis=1)]
        a_von = max(a_von, min(float(belegt.min()), a_bis))
        a_bis = min(a_bis, max(float(belegt.max()), a_von))
    a_werte = vh.raster_a(a_von - schritt_a, a_bis + schritt_a, schritt_a)
    huelle = vh.schaftfraeser(netz, laengs, radial, radius + w.aufmass, a_werte, phi_werte)
    huelle = _hinten_weiter(huelle.sicher(), teil_hinten)
    zugabe = w.aufmass + netz.toleranz + RAND
    # Vor jeder Wand hält die Spirale eine Umdrehung an: Sonst kommt der Fräser nur auf
    # einem Teil des Umfangs bis an die Wand (D-42). Die Hüllfläche dort genau an der Stelle
    # des Rings – das Raster nähme den höheren Nachbarn, und der liegt schon an der Wand.
    ringe = _ringe(w.waende, radius + w.aufmass + netz.toleranz + RING_LUFT, a_ende, a_anfang)
    a, k, herkunft = _mit_ringen(a, ringe, je_umdrehung)
    ring_r = [
        vh.schaftfraeser(netz, laengs, radial, radius + w.aufmass, np.array([stelle]), phi_werte)
        .sicher()
        .r[0]
        for stelle in ringe
    ]

    drehung = _drehung(a_anfang, a_ende, w.gleichlauf)

    def boden(versatz):
        """Wie tief die Spitze an jedem Punkt der Spirale darf, wenn sie beim Winkel
        phi[versatz] beginnt (drehung: mit steigendem oder fallendem Winkel)."""
        winkel = (drehung * (versatz + k)) % je_umdrehung
        ergebnis = _ring_radien(huelle.bei(a, winkel), herkunft, winkel, ring_r, je_umdrehung)
        ergebnis = ergebnis + zugabe
        ergebnis = np.where(~np.isfinite(ergebnis) & (a < teil_hinten), w.stange_radius, ergebnis)
        return np.maximum(ergebnis, radius)  # nicht näher an die Achse

    # Wie viele Lagen: bis zum tiefsten Punkt über dem Teil, egal wo die Spirale ihn trifft –
    # mit gewählten Flächen im Bereich.
    auswahl = np.broadcast_to(
        ((huelle.a >= a_ende) & (huelle.a <= a_anfang))[:, None], huelle.r.shape
    )
    if w.bereich is not None:
        auswahl = auswahl & w.bereich.bei(huelle.a[:, None], huelle.phi[None, :])
    ueber_dem_teil = huelle.r[auswahl]
    ueber_dem_teil = ueber_dem_teil[np.isfinite(ueber_dem_teil)]
    r_min = max(float(ueber_dem_teil.min()) + zugabe, radius) if ueber_dem_teil.size else 0.0
    lagen = 0
    if ueber_dem_teil.size:
        lagen = max(0, int(math.ceil((w.stange_radius - r_min) / w.zustellung - GLEICH)))
    sicher = w.stange_radius + w.sicherheit
    punkte = [Punkt(True, a_anfang, sicher, 0.0)]
    if w.bereich is not None:  # gewählte Flächen: Zeilen hin und her (V4)
        zeilen_a = _zeilen(w.bereich, a_ende, a_anfang, w.steigung, ringe)

        def boden_bei(stellen, j):
            """Wie tief die Spitze an den Stellen längs beim Winkelschritt j darf – ein Ring
            genau an seiner Stelle."""
            j = np.broadcast_to(j, np.shape(stellen))
            ergebnis = huelle.bei(stellen, j) + zugabe
            for stelle, zeile in zip(ringe, ring_r, strict=True):
                ergebnis = np.where(np.abs(stellen - stelle) < GLEICH, zeile[j] + zugabe, ergebnis)
            hinten = ~np.isfinite(ergebnis) & (stellen < teil_hinten)
            return np.maximum(np.where(hinten, w.stange_radius, ergebnis), radius)

        rundum = np.arange(je_umdrehung)
        boden_zeilen = np.array(
            [boden_bei(np.full(je_umdrehung, z), rundum) for z in zeilen_a]
        ).reshape(len(zeilen_a), je_umdrehung)
        _schruppen_zeilen(punkte, zeilen_a, boden_zeilen, boden_bei, lagen, w, schritt_phi)
        _eilgang(punkte, a_anfang, sicher, punkte[-1].phi)
        return Bahn(punkte, lagen, r_min, hinten_frei)
    versatz = 0  # die Spirale einer Lage beginnt, wo die letzte endete
    for lage in range(1, lagen + 1):
        r = np.maximum(boden(versatz), w.stange_radius - lage * w.zustellung)
        phi = drehung * (versatz + k) * schritt_phi
        for i in _knicke(r, int(round(HOECHSTENS_GRAD / schritt_phi)), a):
            punkte.append(Punkt(False, float(a[i]), float(r[i]), float(phi[i])))
        versatz += int(k[-1])
        punkte.append(Punkt(True, a_ende, sicher, float(phi[-1])))
        punkte.append(Punkt(True, a_anfang, sicher, float(phi[-1])))
    return Bahn(punkte, lagen, r_min, hinten_frei)


def _rampe(a, r, phi, von, bis, oben, w):
    """Die Rampe ins Material am Anfang des Stücks von..bis: von `oben` über dem Punkt von längs
    der Bahn hinab, mit dem Eintauchwinkel gegen sie, hin und her, bis sie die Bahn r erreicht
    – dann auf ihr zurück zum Anfang: [(a, r, φ)] ohne den Anfang. So fräst sie weg, was unter
    ihr stehen blieb."""
    steil = math.tan(math.radians(w.eintauchwinkel if w.eintauchwinkel > 0 else EINTAUCHWINKEL))
    hoehe = oben
    ergebnis = []
    i, richtung = von, 1
    for _ in range(RAMPE_HOECHSTENS * (bis - von + 1)):
        j = i + richtung
        if not von <= j <= bis:  # am Ende des Stücks: kehrt um
            richtung = -richtung
            j = i + richtung
        bogen = max(hoehe, float(r[j])) * math.radians(float(phi[j] - phi[i]))
        hoehe -= steil * math.hypot(float(a[j] - a[i]), bogen)
        if hoehe <= r[j]:
            zurueck = range(j, von - 1, -1)
            ergebnis.extend((float(a[m]), float(r[m]), float(phi[m])) for m in zurueck)
            return ergebnis
        ergebnis.append((float(a[j]), hoehe, float(phi[j])))
        i = j
    ergebnis.append((float(a[von]), float(r[von]), float(phi[von])))  # nie unten: senkrecht
    return ergebnis


def _laenge(a, r, phi, von, bis):
    """Wie lang das Stück von..bis der Bahn an der Spitze ist (mm)."""
    bogen = r[von:bis] * np.diff(np.radians(phi[von : bis + 1]))
    return float(np.sum(np.hypot(np.diff(a[von : bis + 1]), bogen)))


def _stuecke(im):
    """[(von, bis)] – die Läufe, in denen `im` wahr ist (Punktnummern, bis einschließlich)."""
    rand = np.diff(np.concatenate([[0], np.asarray(im, dtype=np.int8), [0]]))
    return list(
        zip(
            np.flatnonzero(rand == 1).tolist(),
            (np.flatnonzero(rand == -1) - 1).tolist(),
            strict=True,
        )
    )


def _eilgang(punkte, a, r, phi):
    """Im Eilgang nach (a, r, φ) – eine lange Drehung in Schritten von höchstens
    HOECHSTENS_GRAD, wie die Bahn selbst."""
    vorher = punkte[-1]
    schritte = max(1, int(math.ceil(abs(phi - vorher.phi) / HOECHSTENS_GRAD - 1e-9)))
    for m in range(1, schritte + 1):
        t = m / schritte
        punkt = Punkt(
            True,
            vorher.a + t * (a - vorher.a),
            vorher.r + t * (r - vorher.r),
            vorher.phi + t * (phi - vorher.phi),
        )
        if punkt != punkte[-1]:
            punkte.append(punkt)


# --- Mit gewählten Flächen: Zeilen hin und her (V4) -----------------------------------------
# Manuel (2026-09-30, zum Bild der Spirale mit Eilgängen rundum): „man kann ja auch einfach
# zurück drehen für so eine Fläche“. Jede Zeile liegt bei festem a und fährt nur über ihre
# Stücke im Bereich; am Ende geht es in der Tiefe einen Schritt längs zur nächsten Zeile und
# die Rundachse dreht zurück. Abgehoben wird nur, wo die nächste Zeile nicht dort weitergeht.


def _zeilen(bereich, a_von, a_bis, abstand, ringe=()):
    """Die Stellen längs der Zeilen im Bereich, von vorn nach hinten: gleich weit auseinander,
    höchstens `abstand`, die erste an seinem vorderen, die letzte an seinem hinteren Ende –
    nur zwischen a_von und a_bis; dazu die Ringe vor den Wänden (`ringe`)."""
    belegt = bereich.drin.any(axis=1)
    if not belegt.any():
        return np.zeros(0)
    oben = min(float(bereich.a[belegt].max()), a_bis)
    unten = max(float(bereich.a[belegt].min()), a_von)
    if oben < unten - GLEICH:
        return np.zeros(0)
    anzahl = max(1, int(math.ceil((oben - unten) / abstand - 1e-9)))
    stellen = list(oben - (oben - unten) * np.arange(anzahl + 1) / anzahl)
    stellen += [ring for ring in ringe if unten - GLEICH <= ring <= oben + GLEICH]
    ergebnis = []
    for stelle in sorted(stellen, reverse=True):
        if not ergebnis or ergebnis[-1] - stelle > 1e-6:
            ergebnis.append(stelle)
    return np.array(ergebnis)


def _bereiche(drin):
    """Die Stücke einer Zeile im Bereich: [(Anfang, Länge)] in Winkelschritten, nach dem Anfang
    geordnet; ein Stück über die Naht bei 0° reicht über das Ende hinaus; rundum [(0, N)]."""
    n = len(drin)
    if not drin.any():
        return []
    if drin.all():
        return [(0, n)]
    frei = int(np.flatnonzero(~drin)[0])  # die Stücke von einer Lücke aus gezählt
    gedreht = np.roll(drin, -frei)
    return sorted(((von + frei) % n, bis - von + 1) for von, bis in _stuecke(gedreht))


def _von_bis(von, bis):
    """Die Winkelschritte von `von` bis `bis`, beide dabei, in Schritten von ±1."""
    return np.arange(von, bis + (1 if bis >= von else -1), 1 if bis >= von else -1)


def _einzeln(drin, steigend, absteigend=False):
    """Die Fahrten für „nur im Gleichlauf“ (P-2026-10-02-24): jedes Stück jeder Zeile eine
    Fahrt für sich, alle in dieselbe Richtung (`steigend`: mit wachsenden Winkelschritten oder
    Stellen) – dazwischen hebt der Fräser ab und setzt am Anfang der nächsten neu ein. Die
    Zeilen der Reihe nach, `absteigend` von der letzten an. `drin` wie bei _fahrten()."""
    fahrten = []
    zeilen = range(drin.shape[0] - 1, -1, -1) if absteigend else range(drin.shape[0])
    for m in zeilen:
        for anfang, laenge in _bereiche(drin[m]):
            letzte = anfang + laenge - 1
            js = _von_bis(anfang, letzte) if steigend else _von_bis(letzte, anfang)
            fahrten.append([("zeile", m, js)])
    return fahrten


def _fahrten(drin):
    """Wie die Zeilen hin und her gefahren werden: [[Teil, …], …] – je Fahrt, was ohne Abheben
    am Stück geht. Ein Teil ist ("zeile", m, js): Zeile m über die Winkelschritte js
    (fortlaufend), oder ("schritt", m, j): von Zeile m zur nächsten beim Winkelschritt j. Die
    Richtung wechselt von Zeile zu Zeile. `drin`: (Zeilen, N) – wo gefräst wird. Getrennte
    Stücke des Bereichs (zwei Abflachungen) fährt es nacheinander ganz – so hebt der Fräser nur
    zwischen ihnen ab, nicht in jeder Zeile."""
    ergebnis = []
    for teil in _zusammenhaengend(drin):
        ergebnis += _fahrten_eines(teil)
    return ergebnis


def _zusammenhaengend(drin):
    """Die zusammenhängenden Stücke des Bereichs (Zeilen, N): je eins ein Feld wie `drin`, das
    nur sie hat – zusammen hängen Stücke benachbarter Zeilen, die sich rundum überlappen;
    geordnet nach ihrer ersten Zeile und ihrem ersten Winkel."""
    anzahl, n = drin.shape
    stuecke = [_bereiche(drin[m]) for m in range(anzahl)]
    eltern = {(m, k): (m, k) for m in range(anzahl) for k in range(len(stuecke[m]))}

    def wurzel(x):
        while eltern[x] != x:
            eltern[x] = eltern[eltern[x]]
            x = eltern[x]
        return x

    for m in range(1, anzahl):
        for k, (anfang, laenge) in enumerate(stuecke[m]):
            for k0, (anfang0, laenge0) in enumerate(stuecke[m - 1]):
                if (anfang0 - anfang) % n < laenge or (anfang - anfang0) % n < laenge0:
                    eltern[wurzel((m, k))] = wurzel((m - 1, k0))
    gruppen = {}
    for schluessel in sorted(eltern):
        gruppen.setdefault(wurzel(schluessel), []).append(schluessel)
    ergebnis = []
    for mitglieder in sorted(gruppen.values()):
        feld = np.zeros(drin.shape, dtype=bool)
        for m, k in mitglieder:
            anfang, laenge = stuecke[m][k]
            feld[m, (anfang + np.arange(laenge)) % n] = True
        ergebnis.append(feld)
    return ergebnis


def _fahrten_eines(drin):
    """_fahrten() für ein zusammenhängendes Stück des Bereichs."""
    anzahl, n = drin.shape
    fahrten, fahrt, ende, richtung = [], None, 0, 1
    for m in range(anzahl):
        stuecke = _bereiche(drin[m])
        if not stuecke:
            if fahrt:
                fahrten.append(fahrt)
            fahrt = None
        for nummer, (anfang, laenge) in enumerate(stuecke[::richtung]):
            teile = None
            if nummer == 0 and fahrt:
                teile = _anschluss(drin[m - 1], ende, anfang, laenge, richtung, m, n)
            if teile is None:
                if fahrt:
                    fahrten.append(fahrt)
                if laenge >= n:  # rundum
                    js = _von_bis(0, richtung * n)
                else:
                    letzte = anfang + laenge - 1
                    js = _von_bis(anfang, letzte) if richtung > 0 else _von_bis(letzte, anfang)
                fahrt = [("zeile", m, js)]
            else:
                fahrt.extend(teile)
            ende = int(fahrt[-1][2][-1])
        richtung = -richtung
    if fahrt:
        fahrten.append(fahrt)
    return fahrten


def _anschluss(davor, ende, anfang, laenge, richtung, m, n):
    """Die Teile, mit denen es in der Tiefe von Zeile m − 1 (endet beim Winkelschritt `ende`,
    `davor`: wo sie im Bereich ist) in Zeile m weitergeht, die über das Stück (anfang, laenge)
    in `richtung` fährt – oder None, wenn es nicht geht: dann hebt der Fräser ab. Liegt das
    Ende über dem Stück, geht es dort hinüber, fährt das Stück erst bis zu seinem Anfang und
    dann ganz; sonst zurück auf der alten Zeile bis über den Anfang des Stücks."""
    if laenge >= n:  # rundum: gleich hinüber und einmal herum
        return [("schritt", m - 1, ende), ("zeile", m, _von_bis(ende, ende + richtung * n))]
    anfang_ = anfang if richtung > 0 else anfang + laenge - 1  # wo das Stück beginnt
    darin = (ende - anfang) % n < laenge
    if darin:  # hinüber, bis zum Anfang des Stücks, dann ganz hindurch
        weit = ((ende - anfang_) * richtung) % n
        start = ende - richtung * weit
        teile = [("schritt", m - 1, ende)]
        if start != ende:
            teile.append(("zeile", m, _von_bis(ende, start)))
    else:  # auf der alten Zeile zurück bis über den Anfang – sie muss dort im Bereich sein
        weit = ((anfang_ - ende) * richtung) % n
        start = ende + richtung * weit
        zurueck = _von_bis(ende, start)
        if not davor[zurueck % n].all():
            return None
        teile = [("zeile", m - 1, zurueck), ("schritt", m - 1, start)]
    return teile + [("zeile", m, _von_bis(start, start + richtung * (laenge - 1)))]


def _folge(fahrt, zeilen_a, hoehe, schritt_hoehe, schritt_laengs=vh.SCHRITT_A):
    """Die Punkte einer Fahrt: (a, r, j, m) – j fortlaufende Winkelschritte, m die Zeile (−1
    auf dem Weg zwischen zwei Zeilen). `hoehe`: (Zeilen, N) die Tiefe auf den Zeilen;
    `schritt_hoehe(m, j, stellen)`: die Tiefe auf dem Weg von Zeile m zur nächsten."""
    n = hoehe.shape[1]
    teile = []
    for art, m, js in fahrt:
        if art == "zeile":
            teile.append((np.full(len(js), zeilen_a[m]), hoehe[m, js % n], js, np.full(len(js), m)))
            continue
        von, bis = zeilen_a[m], zeilen_a[m + 1]
        anzahl = max(1, int(math.ceil(abs(von - bis) / schritt_laengs - 1e-9)))
        stellen = von + (bis - von) * np.arange(1, anzahl) / anzahl
        if len(stellen):
            tiefe = schritt_hoehe(m, int(js), stellen)
            teile.append((stellen, tiefe, np.full(len(stellen), js), np.full(len(stellen), -1)))
    return tuple(np.concatenate([t[i] for t in teile]) for i in range(4))


def _winkel(j, schritt_phi, jetzt):
    """Die Winkel (Grad) der Winkelschritte j – um ganze Umdrehungen so verschoben, dass der
    erste dem jetzigen Winkel der Rundachse am nächsten liegt."""
    phi = j * schritt_phi
    return phi + 360.0 * round((jetzt - float(phi[0])) / 360.0)


def _einfahrt(punkte, a, r, phi, oben, offen, w):
    """Über den Anfang der Fahrt, im Eilgang bis knapp über `oben` (höher steht dort nichts),
    hinein: senkrecht mit dem Eintauchvorschub, wo es `offen` ist, nichts zu fräsen ist oder
    die ganze Fahrt für eine Rampe zu kurz ist – sonst über die Rampe längs der Fahrt (auch
    über den Schritt zur nächsten Zeile, wenn die erste kurz ist)."""
    sicher = w.stange_radius + w.sicherheit
    a0, r0, p0 = float(a[0]), float(r[0]), float(phi[0])
    _eilgang(punkte, a0, sicher, p0)
    knapp = min(sicher, oben + w.sicherheit)
    if knapp < sicher:
        punkte.append(Punkt(True, a0, knapp, p0))
    rampe = getattr(w, "eintauchwinkel", None) is not None and not offen and r0 < oben - GLEICH
    if rampe and _laenge(a, r, phi, 0, len(a) - 1) >= RAMPE_MINDESTENS:
        punkte.append(Punkt(False, a0, oben, p0, True))  # bis ans Material
        punkte.extend(Punkt(False, *stelle) for stelle in _rampe(a, r, phi, 0, len(a) - 1, oben, w))
    else:
        punkte.append(Punkt(False, a0, r0, p0, True))


def _schruppen_zeilen(punkte, zeilen_a, boden, boden_bei, lagen, w, schritt_phi):
    """Die Lagen, wenn nur im Bereich gefräst wird (V4): Zeilen hin und her (_fahrten), jede Lage
    auf denselben Stellen – so steht über jeder höchstens die Tiefe der Lage davor. `boden`:
    (Zeilen, N) wie tief die Spitze darf, `boden_bei(stellen, j)` dasselbe dazwischen. Senkrecht
    hinein geht es, wo die Zeile davor (höchstens einen Fräserradius weiter vorn) in dieser Lage
    schon fräste, sonst über die Rampe."""
    if not len(zeilen_a):
        return
    n = boden.shape[1]
    phi_werte = np.radians(schritt_phi * np.arange(n))
    drin = w.bereich.bei(zeilen_a[:, None], phi_werte[None, :])
    fahrten = _fahrten(drin)
    sicher = w.stange_radius + w.sicherheit
    abstand = int(round(HOECHSTENS_GRAD / schritt_phi))
    nah = np.concatenate([[False], np.diff(-zeilen_a) <= w.fraeser_radius + GLEICH])
    davor = np.full(boden.shape, float(w.stange_radius))
    for lage in range(1, lagen + 1):
        ebene = w.stange_radius - lage * w.zustellung
        hoehe = np.maximum(boden, ebene)
        gefraest = np.zeros(boden.shape, dtype=bool)

        def schritt_hoehe(_m, j, stellen, ebene=ebene):
            return np.maximum(boden_bei(stellen, j % n), ebene)

        for fahrt in fahrten:
            a, r, j, m = _folge(fahrt, zeilen_a, hoehe, schritt_hoehe)
            phi = _winkel(j, schritt_phi, punkte[-1].phi)
            m0, j0 = fahrt[0][1], int(j[0]) % n
            offen = nah[m0] and gefraest[m0 - 1, j0]
            _einfahrt(punkte, a, r, phi, davor[m0, j0], offen, w)
            for i in _knicke(r, abstand, a, phi):
                punkte.append(Punkt(False, float(a[i]), float(r[i]), float(phi[i])))
            punkte.append(Punkt(True, float(a[-1]), sicher, float(phi[-1])))
            auf_zeile = m >= 0
            gefraest[m[auf_zeile], j[auf_zeile] % n] = True
        davor = hoehe


def _schlichten_zeilen(
    netz, laengs, radial, w, a_anfang, a_ende, teil_vorne, teil_hinten, hinten_frei, schritt_phi
):
    """Schlichten nur im Bereich (V4): Zeilen im Abstand der Schrittweite hin und her
    (_fahrten), die Spitze auf der Hüllfläche genau an den Stellen der Zeilen, vor den Wänden
    eine Zeile als Ring; hinein senkrecht mit dem Eintauchvorschub, knapp über dem Rest. Wo das
    Schruppen mehr stehen ließ als die Grenze, vorher in Stufen wie beim Schlichten rundum."""
    form = w.form
    radius = form.radius
    s = w.schrittweite
    zugabe = w.aufmass + netz.toleranz
    geformt = form.mit_aufmass(zugabe)
    phi = vh.raster_phi(schritt_phi)
    n = len(phi)
    sicher = w.stange_radius + w.sicherheit
    abstand = int(round(HOECHSTENS_GRAD / schritt_phi))
    punkte = [Punkt(True, a_anfang, sicher, 0.0)]
    ringe = _ringe(w.waende, radius + zugabe + RING_LUFT, a_ende, a_anfang)
    gleichmaessig = _zeilen(w.bereich, a_ende, a_anfang, s)
    if not len(gleichmaessig):
        punkte.append(Punkt(True, a_anfang, sicher, 0.0))
        return Schlichtbahn(punkte, 0.0, 0.0, form.kammhoehe(s), hinten_frei)
    # Die gleichmäßigen Zeilen auf einmal (aufsteigend gerechnet), die Ringe je für sich.
    unten = float(gleichmaessig[-1])
    weite = (
        (float(gleichmaessig[0]) - unten) / (len(gleichmaessig) - 1)
        if len(gleichmaessig) > 1
        else s
    )
    anfang = np.full(n, unten)
    huelle = vh.je_winkel(netz, laengs, radial, geformt, anfang, weite, len(gleichmaessig), phi)
    huelle = _auffuellen(huelle, anfang, weite, teil_vorne, teil_hinten)[::-1] + zugabe
    zeilen = dict(zip(gleichmaessig.tolist(), huelle, strict=True))
    for ring in ringe:
        if unten - GLEICH <= ring <= gleichmaessig[0] + GLEICH:
            zeile = vh.je_winkel(netz, laengs, radial, geformt, np.full(n, ring), s, 1, phi)[0]
            zeilen[ring] = zeile + zugabe
    zeilen_a = np.array(sorted(zeilen, reverse=True))
    zeilen_a = zeilen_a[np.concatenate([[True], np.diff(-zeilen_a) > 1e-6])]
    hoehe = np.array([zeilen[z] for z in zeilen_a.tolist()])
    hoehe = np.maximum(np.where(np.isfinite(hoehe), hoehe, w.stange_radius), radius)
    drin = w.bereich.bei(zeilen_a[:, None], phi[None, :])

    def schritt_hoehe(m, j, stellen, ebene=None):
        """Die Hüllfläche genau auf dem Weg von Zeile m zur nächsten beim Winkelschritt j –
        vor und hinter dem Teil die höhere der beiden Zeilen."""
        wert = vh.je_winkel(
            netz,
            laengs,
            radial,
            geformt,
            np.array([stellen[-1]]),
            float(stellen[0] - stellen[1]) if len(stellen) > 1 else 1.0,
            len(stellen),
            phi[[j % n]],
        )[::-1, 0]
        daneben = max(hoehe[m, j % n], hoehe[m + 1, j % n])
        wert = np.where(np.isfinite(wert), wert + zugabe, daneben)
        if ebene is not None:
            wert = np.maximum(wert, np.maximum(ebene[m, j % n], ebene[m + 1, j % n]))
        return np.maximum(wert, radius)

    umdrehungen = 0.0

    def fahren(ziel, wo, stand, ebene=None):
        """Die Zeilen über `wo` auf der Tiefe `ziel`; `stand`: so hoch steht dort noch etwas.
        Gibt zurück, wo gefräst wurde."""
        nonlocal umdrehungen
        gefraest = np.zeros(ziel.shape, dtype=bool)
        for fahrt in _fahrten(wo):
            a, r, j, m = _folge(
                fahrt, zeilen_a, ziel, lambda mm, jj, st: schritt_hoehe(mm, jj, st, ebene)
            )
            winkel = _winkel(j, schritt_phi, punkte[-1].phi)
            m0, j0 = fahrt[0][1], int(j[0]) % n
            oben = w.stange_radius if stand is None else max(float(stand[m0, j0]), float(r[0]))
            _einfahrt(punkte, a, r, winkel, oben, True, w)
            gehoben = r + _sehnenfehler(r)
            fest = np.flatnonzero(_a_knicke(a) | _a_knicke(winkel)) + 1 if len(a) > 2 else []
            for i in _zusammengefasst(gehoben, BAHN_TOLERANZ, abstand, list(fest)):
                punkte.append(Punkt(False, float(a[i]), float(gehoben[i]), float(winkel[i])))
            punkte.append(Punkt(True, float(a[-1]), sicher, float(winkel[-1])))
            auf_zeile = m >= 0
            gefraest[m[auf_zeile], j[auf_zeile] % n] = True
            umdrehungen += float(np.sum(np.abs(np.diff(winkel)))) / 360.0
        return gefraest

    # Wo das Schruppen mehr stehen ließ als die Grenze: vorher in Stufen.
    stufen, grenze, stand = 0, 0.0, None
    if w.rest is not None:
        grenze = max(radius, w.aufmass_schruppen + SCHLICHT_ZUGABE)
        gitter_a = np.repeat(zeilen_a, n)
        gitter_phi = np.tile(phi, len(zeilen_a))
        oben = _nicht_tiefer(w.rest, form, 0.0, gitter_a, gitter_phi).reshape(hoehe.shape)
        stand = np.maximum(oben, hoehe)
        tiefste = float(np.max(np.where(drin, oben - hoehe, 0.0)))
        for stufe in range(1, int(math.ceil(max(tiefste, 0.0) / grenze - 1e-9))):
            ebene = np.maximum(hoehe, oben - stufe * grenze)
            noetig = (ebene > hoehe + BAHN_TOLERANZ) & drin
            if not noetig.any():
                continue
            gefraest = fahren(ebene, noetig, stand, ebene)
            stand = np.where(gefraest, np.minimum(stand, ebene), stand)
            stufen += 1
    fahren(hoehe, drin, stand)
    _eilgang(punkte, a_anfang, sicher, punkte[-1].phi)
    r_min = float(np.min(hoehe[drin])) if drin.any() else 0.0
    return Schlichtbahn(punkte, umdrehungen, r_min, form.kammhoehe(s), hinten_frei, stufen, grenze)


def schlichten(netz, laengs, radial, werte, schritt_phi=SCHRITT_PHI_SCHLICHTEN):
    """Die Schlichtbahn (Schlichtbahn) für `netz` (vierachs_huelle.vernetze, im Job, fein:
    TOLERANZ_SCHLICHTEN) mit den Schlichtwerten `werte`; `laengs` und `radial` wie in
    vierachs_huelle.

    ValueError, wenn die Werte nicht gehen – mit einem Satz für den Menschen.
    """
    w = werte
    form = w.form
    radius = form.radius
    if radius <= 0 or w.schrittweite <= 0:
        raise ValueError(tr("vb.fehler.schrittweite"))
    if w.schrittweite > 2 * radius:
        raise ValueError(tr("vb.fehler.schrittweite_gross"))
    if w.muster not in MUSTER:
        raise ValueError(tr("vb.fehler.muster", muster=w.muster))
    l_, _u, _v = vh.rahmen(laengs, radial)
    a_teil = netz.punkte @ l_
    teil_vorne, teil_hinten = float(a_teil.max()), float(a_teil.min())
    ueberlauf = ueberlauf_vorschlag(radius) if w.ueberlauf is None else w.ueberlauf
    a_anfang = w.a_stange_vorne + radius + w.sicherheit
    a_ende = _ende(teil_hinten, ueberlauf, radius, w)
    if a_ende >= teil_vorne + radius:
        raise ValueError(_kein_platz(radius, w))
    hinten_frei = max(0.0, a_ende - radius - teil_hinten)
    if w.muster == LINIEN:  # Linien längs (V4c)
        return _schlichten_linien(
            netz, laengs, radial, w, a_anfang, a_ende, teil_vorne, teil_hinten, hinten_frei
        )
    if w.bereich is not None:  # gewählte Flächen: Zeilen hin und her (V4)
        return _schlichten_zeilen(
            netz,
            laengs,
            radial,
            w,
            a_anfang,
            a_ende,
            teil_vorne,
            teil_hinten,
            hinten_frei,
            schritt_phi,
        )

    # Die Spirale: Punkt k liegt bei a_anfang − s · k / N unter dem Winkel k · Δφ. Je Winkel
    # j kommt sie an a_anfang − s · (j / N + m) vorbei – dort rechnet die Hüllfläche.
    phi = vh.raster_phi(schritt_phi)
    je_umdrehung = len(phi)
    s = w.schrittweite
    anzahl = int(math.ceil((a_anfang - a_ende) / s * je_umdrehung - 1e-9))
    umdrehungen = int(math.ceil(anzahl / je_umdrehung))
    zugabe = w.aufmass + netz.toleranz  # das Netz liegt bis zu seiner Toleranz innen
    # Mit fallendem Winkel (drehung −1) kommt die Spirale am Winkel j vorbei, wo k ≡ −j.
    drehung = _drehung(a_anfang, a_ende, w.gleichlauf)
    erster = (drehung * np.arange(je_umdrehung)) % je_umdrehung
    anfang_je_winkel = a_anfang - s * (erster / je_umdrehung + umdrehungen)
    huelle = vh.je_winkel(
        netz,
        laengs,
        radial,
        form.mit_aufmass(zugabe),
        anfang_je_winkel,
        s,
        umdrehungen + 1,
        phi,
    )
    huelle = _auffuellen(huelle, anfang_je_winkel, s, teil_vorne, teil_hinten) + zugabe
    k = np.arange(anzahl + 1)
    a = a_anfang - s * k / je_umdrehung
    r = huelle[umdrehungen - k // je_umdrehung, (drehung * k) % je_umdrehung]
    # Vor jeder Wand hält die Spirale eine Umdrehung an (Ringgang, D-42) – die Hüllfläche
    # dort genau an dieser Stelle gerechnet; so weit vor der Wand, dass der um Aufmaß und
    # Vernetzung größere Fräser sie nicht streift.
    ringe = _ringe(w.waende, radius + zugabe + RING_LUFT, a_ende, a_anfang)
    a, k, herkunft = _mit_ringen(a, ringe, je_umdrehung)
    ring_r = [
        vh.je_winkel(
            netz,
            laengs,
            radial,
            form.mit_aufmass(zugabe),
            np.full(je_umdrehung, stelle),
            s,
            1,
            phi,
        )[0]
        + zugabe
        for stelle in ringe
    ]
    r = _ring_radien(r, herkunft, drehung * k, ring_r, je_umdrehung)
    anzahl = len(a) - 1
    r = np.where(np.isfinite(r), r, w.stange_radius)  # trifft rundum nichts: bleibt oben
    r = np.maximum(r, radius)  # nicht näher an die Achse
    # Wo das Schruppen mehr stehen ließ als die Grenze (eine Innenecke, eine enge Nut), fährt
    # Schlichten vorher in Stufen, von oben nach unten – jede höchstens die Grenze unter der
    # davor, nur wo es nötig ist.
    stufen, grenze = [], 0.0
    if w.rest is not None:
        grenze = max(radius, w.aufmass_schruppen + SCHLICHT_ZUGABE)
        oben = _nicht_tiefer(w.rest, form, 0.0, a, drehung * k * math.radians(schritt_phi))
        anzahl_stufen = int(math.ceil(max(float(np.max(oben - r)), 0.0) / grenze - 1e-9))
        stand = oben.copy()  # bis hier steht noch Material über der Spitze, je Punkt
        for stufe in range(1, anzahl_stufen):
            hoehe = np.maximum(r, oben - stufe * grenze)
            noetig = hoehe > r + BAHN_TOLERANZ
            if not noetig.any():
                continue
            stuecke = _abschnitte(noetig, np.maximum(stand - hoehe, 0.0), je_umdrehung)
            stufen.append((hoehe, stuecke))
            for von, bis in stuecke:
                np.minimum(stand[von : bis + 1], hoehe[von : bis + 1], out=stand[von : bis + 1])
    sicher = w.stange_radius + w.sicherheit
    abstand = int(round(HOECHSTENS_GRAD / schritt_phi))
    winkel = drehung * k * schritt_phi
    punkte = [Punkt(True, a_anfang, sicher, 0.0)]
    umdrehungen_vor = 0
    for r_stufe, stuecke in stufen:
        for von, bis in stuecke:
            _spirale(punkte, a, r_stufe, winkel, von, bis, sicher, abstand, drehung)
            umdrehungen_vor += (bis - von) / je_umdrehung
    _spirale(punkte, a, r, winkel, 0, anzahl, sicher, abstand, drehung)
    punkte.append(Punkt(True, a_anfang, sicher, punkte[-1].phi))
    return Schlichtbahn(
        punkte,
        anzahl / je_umdrehung + umdrehungen_vor,
        float(np.min(r)),
        form.kammhoehe(s),
        hinten_frei,
        len(stufen),
        grenze,
    )


# --- Linien längs (V4c) ---------------------------------------------------------------------
# Manuel (2026-09-30): „mehrere Strategien, je nach Werkzeug kann das anders ausfallen“. Jede
# Linie liegt bei festem Winkel und fährt längs über ihre Stücke im Bereich; am Ende dreht die
# Rundachse in der Tiefe zur nächsten Linie, die Richtung wechselt. Die Fahrten kommen von
# _fahrten() wie beim Hin und Her – nur mit Linie statt Zeile und Stelle längs statt
# Winkelschritt; längs gibt es keine Naht, deshalb rechnet es mit einer Lücke an beiden Enden.


def linienwinkel(r_max, schrittweite):
    """Die Winkel (Grad) der Linien längs: rundum gleich weit auseinander, höchstens
    `schrittweite` ÷ `r_max` weit (im Bogenmaß) – so bleibt zwischen zwei Linien auf dem
    größten Radius nicht mehr stehen als zwischen zwei Umdrehungen der Spirale."""
    anzahl = max(1, int(math.ceil(2.0 * math.pi * max(r_max, GLEICH) / schrittweite - 1e-9)))
    return 360.0 * np.arange(anzahl) / anzahl


def _schlichten_linien(
    netz, laengs, radial, w, a_anfang, a_ende, teil_vorne, teil_hinten, hinten_frei
):
    """Schlichten in Linien längs (Muster LINIEN): die Spitze auf der Hüllfläche genau auf den
    Linien, alle SCHRITT_A_LINIEN ein Punkt; mit Bereich nur die Linien und Stücke darüber;
    hinein senkrecht mit dem Eintauchvorschub, knapp über dem Rest; wo das Schruppen mehr
    stehen ließ als die Grenze, vorher in Stufen wie bei der Spirale."""
    form = w.form
    radius = form.radius
    s = w.schrittweite
    zugabe = w.aufmass + netz.toleranz
    geformt = form.mit_aufmass(zugabe)
    sicher = w.stange_radius + w.sicherheit
    punkte = [Punkt(True, a_anfang, sicher, 0.0)]
    # Die Linien: im Winkelabstand s ÷ r_max – r_max der größte Radius des Teils plus Aufmaß.
    _l, u_, v_ = vh.rahmen(laengs, radial)
    r_teil = np.hypot(netz.punkte @ u_, netz.punkte @ v_)
    r_max = max(float(r_teil.max()) + zugabe if len(r_teil) else 0.0, radius)
    winkel = linienwinkel(r_max, s)
    phi = np.radians(winkel)
    # Die Stellen längs: von hinten nach vorn, höchstens SCHRITT_A_LINIEN auseinander.
    anzahl = max(2, int(math.ceil((a_anfang - a_ende) / SCHRITT_A_LINIEN - 1e-9)) + 1)
    a_stellen = np.linspace(a_ende, a_anfang, anzahl)
    schritt = float(a_stellen[1] - a_stellen[0])
    # Wo gefräst wird: über dem Bereich, ohne Bereich überall. Linien ohne Stück bleiben als
    # Lücke stehen – so hängen nur Nachbarn zusammen; die Reihe beginnt nach einer Lücke, damit
    # ein Stück über die Naht bei 0° ein Stück bleibt.
    if w.bereich is not None:
        drin = w.bereich.bei(a_stellen[None, :], phi[:, None])
    else:
        drin = np.ones((len(winkel), anzahl), dtype=bool)
    belegt = drin.any(axis=1)
    if not belegt.any():
        punkte.append(Punkt(True, a_anfang, sicher, 0.0))
        return Schlichtbahn(punkte, 0.0, 0.0, form.kammhoehe(s), hinten_frei)
    if not belegt.all():
        reihe = (np.arange(len(winkel)) + int(np.flatnonzero(~belegt)[0])) % len(winkel)
        winkel, phi, drin, belegt = winkel[reihe], phi[reihe], drin[reihe], belegt[reihe]
    n = len(winkel)
    # Die Hüllfläche nur auf den Linien, über denen etwas liegt.
    huelle = vh.je_winkel(
        netz,
        laengs,
        radial,
        geformt,
        np.full(int(belegt.sum()), a_ende),
        schritt,
        anzahl,
        phi[belegt],
    )
    anfang = np.full(int(belegt.sum()), a_ende)
    huelle = _auffuellen(huelle, anfang, schritt, teil_vorne, teil_hinten).T + zugabe
    hoehe = np.full((n, anzahl), float(w.stange_radius))
    hoehe[belegt] = np.where(np.isfinite(huelle), huelle, w.stange_radius)
    hoehe = np.maximum(hoehe, radius)

    def folge(fahrt, ziel):
        """Die Punkte einer Fahrt: (a, r, Winkel in Grad, Linie, Stelle) – Linie und Stelle −1
        auf der Drehung zur nächsten Linie, in der Tiefe der höheren von beiden."""
        teile = []
        for art, m, js in fahrt:
            if art == "zeile":
                k = np.asarray(js) - 1  # ohne die Lücke am Anfang
                teile.append(
                    (a_stellen[k], ziel[m, k], np.full(len(k), winkel[m]), np.full(len(k), m), k)
                )
                continue
            k = int(js) - 1
            r = max(float(ziel[m, k]), float(ziel[m + 1, k]))
            teile.append(
                (
                    a_stellen[[k]],
                    np.array([r]),
                    np.array([winkel[m + 1]]),
                    np.array([-1]),
                    np.array([-1]),
                )
            )
        return tuple(np.concatenate([t[i] for t in teile]) for i in range(5))

    umdrehungen = 0.0

    def fahren(ziel, wo, stand):
        """Die Linien über `wo` auf der Tiefe `ziel`; `stand`: so hoch steht dort noch etwas.
        Gibt zurück, wo gefräst wurde."""
        nonlocal umdrehungen
        gefraest = np.zeros(ziel.shape, dtype=bool)
        mit_luecke = np.zeros((n, anzahl + 2), dtype=bool)
        mit_luecke[:, 1:-1] = wo
        for fahrt in _fahrten(mit_luecke):
            a, r, grad, m, k = folge(fahrt, ziel)
            grad = np.degrees(np.unwrap(np.radians(grad)))  # über die Naht bei 0° hinweg
            grad = grad + 360.0 * round((punkte[-1].phi - float(grad[0])) / 360.0)
            m0, k0 = int(m[0]), int(k[0])
            oben = w.stange_radius if stand is None else max(float(stand[m0, k0]), float(r[0]))
            _einfahrt(punkte, a, r, grad, oben, True, w)
            gehoben = r + _sehnenfehler(r)
            fest = np.flatnonzero(_a_knicke(a) | _a_knicke(grad)) + 1 if len(a) > 2 else []
            for i in _zusammengefasst(gehoben, BAHN_TOLERANZ, len(a), list(fest)):
                punkte.append(Punkt(False, float(a[i]), float(gehoben[i]), float(grad[i])))
            punkte.append(Punkt(True, float(a[-1]), sicher, float(grad[-1])))
            auf_linie = m >= 0
            gefraest[m[auf_linie], k[auf_linie]] = True
            umdrehungen += float(np.sum(np.abs(np.diff(grad)))) / 360.0
        return gefraest

    # Wo das Schruppen mehr stehen ließ als die Grenze: vorher in Stufen.
    stufen, grenze, stand = 0, 0.0, None
    if w.rest is not None:
        grenze = max(radius, w.aufmass_schruppen + SCHLICHT_ZUGABE)
        gitter_a = np.tile(a_stellen, n)
        gitter_phi = np.repeat(phi, anzahl)
        oben = _nicht_tiefer(w.rest, form, 0.0, gitter_a, gitter_phi).reshape(hoehe.shape)
        stand = np.maximum(oben, hoehe)
        tiefste = float(np.max(np.where(drin, oben - hoehe, 0.0)))
        for stufe in range(1, int(math.ceil(max(tiefste, 0.0) / grenze - 1e-9))):
            ebene = np.maximum(hoehe, oben - stufe * grenze)
            noetig = (ebene > hoehe + BAHN_TOLERANZ) & drin
            if not noetig.any():
                continue
            gefraest = fahren(ebene, noetig, stand)
            stand = np.where(gefraest, np.minimum(stand, ebene), stand)
            stufen += 1
    fahren(hoehe, drin, stand)
    _eilgang(punkte, a_anfang, sicher, punkte[-1].phi)
    r_min = float(np.min(hoehe[drin]))
    return Schlichtbahn(
        punkte,
        umdrehungen,
        r_min,
        form.kammhoehe(s),
        hinten_frei,
        stufen,
        grenze,
        linien=int(belegt.sum()),
    )


def _abschnitte(noetig, tiefe, je_umdrehung):
    """[(von, bis)] Punktnummern der Stücke einer Stufe: Nötige Punkte, die höchstens eine
    Umdrehung auseinanderliegen, fährt ein Stück am Stück. Es beginnt in der Umdrehung vor
    seinem ersten nötigen Punkt dort, wo es am wenigsten tief eintaucht (`tiefe` je Punkt) –
    von denen der letzte – und endet am letzten nötigen Punkt."""
    nummern = np.flatnonzero(noetig)
    luecken = np.flatnonzero(np.diff(nummern) > je_umdrehung)
    anfaenge = np.concatenate([nummern[:1], nummern[luecken + 1]])
    enden = np.concatenate([nummern[luecken], nummern[-1:]])
    ergebnis = []
    frei = 0  # ab hier darf das nächste Stück beginnen
    for erster, letzter in zip(anfaenge.tolist(), enden.tolist(), strict=True):
        fruehestens = max(frei, erster - je_umdrehung)
        fenster = tiefe[fruehestens : erster + 1]
        flach = np.flatnonzero(fenster <= fenster.min() + BAHN_TOLERANZ)
        ergebnis.append((fruehestens + int(flach[-1]), letzter))
        frei = letzter + 1
    return ergebnis


def _spirale(punkte, a, r, winkel, von, bis, sicher, abstand, drehung=1):
    """Hängt das Stück von..bis der Spirale an `punkte`: im Eilgang über den Anfang, hinein,
    die Spirale mit Sehnenfehler und zusammengefasst, radial hinaus. Der Winkel zählt weiter,
    wo die Rundachse steht – sie dreht nicht zurück (`drehung`: −1, wenn er fällt)."""
    weiter = punkte[-1].phi
    if drehung > 0:
        versatz = 360.0 * math.ceil((weiter - winkel[von]) / 360.0 - 1e-9)
    else:
        versatz = -360.0 * math.ceil((winkel[von] - weiter) / 360.0 - 1e-9)
    stueck = r[von : bis + 1]
    stueck = stueck + _sehnenfehler(stueck)
    anfahren = Punkt(True, float(a[von]), sicher, float(winkel[von] + versatz))
    if anfahren != punkte[-1]:
        punkte.append(anfahren)
    ringe = np.flatnonzero(_a_knicke(a[von : bis + 1])) + 1
    for i in _zusammengefasst(stueck, BAHN_TOLERANZ, abstand, ringe.tolist()):
        j = von + i
        punkte.append(Punkt(False, float(a[j]), float(stueck[i]), float(winkel[j] + versatz)))
    punkte.append(Punkt(True, float(a[bis]), sicher, float(winkel[bis] + versatz)))


def _auffuellen(huelle, anfang_je_winkel, schritt, teil_vorne, teil_hinten):
    """Vor und hinter dem Teil – wo die Mitte des Fräsers über das Teil hinaus ist – die Tiefe
    an seinem Ende: Der Fräser fährt so an und aus dem Teil heraus, wie er an dessen Ende war,
    statt mit dem Rand an der Kante hinabzurollen (wie das Schruppen, V3f)."""
    ergebnis = huelle.copy()
    zeilen = np.arange(len(huelle))[:, None]
    spalten = np.arange(huelle.shape[1])
    vorne = np.floor((teil_vorne - anfang_je_winkel) / schritt + 1e-9).astype(np.int64)
    hinten = np.ceil((teil_hinten - anfang_je_winkel) / schritt - 1e-9).astype(np.int64)
    vorne = np.clip(vorne, 0, len(huelle) - 1)
    hinten = np.clip(hinten, 0, len(huelle) - 1)
    wert_vorne = huelle[vorne, spalten]
    wert_hinten = huelle[hinten, spalten]
    davor = (zeilen > vorne[None, :]) & np.isfinite(wert_vorne)[None, :]
    dahinter = (zeilen < hinten[None, :]) & np.isfinite(wert_hinten)[None, :]
    ergebnis = np.where(davor, wert_vorne[None, :], ergebnis)
    return np.where(dahinter, wert_hinten[None, :], ergebnis)


def _nicht_tiefer(rest, form, grenze, a, phi):
    """Wie tief die Spitze an den Punkten (a, φ in rad) höchstens darf, damit der Fräser
    nirgends mehr als `grenze` unter den Rest nach dem Schruppen schneidet: je Stelle des
    Rests unter dem Fräser seine Höhe dort minus Profil – der höchste Wert, minus `grenze`.
    Zwischen den Rasterpunkten gilt der höchste Nachbar."""
    rest_a, rest_phi, rest_r = rest
    schritt_a = rest_a[1] - rest_a[0]
    schritt_phi = rest_phi[1] - rest_phi[0]
    radius = form.radius
    n_a = int(math.ceil(radius / schritt_a))
    klein = max(float(np.min(rest_r)), radius)
    n_phi = min(len(rest_phi) // 2, int(math.ceil(math.asin(radius / klein) / schritt_phi)) + 1)
    rand = np.full((n_a, rest_r.shape[1]), -math.inf)
    breit = np.concatenate([rand, rest_r, rand])
    tiefste = np.full(rest_r.shape, -math.inf)
    with np.errstate(invalid="ignore"):
        for i in range(-n_a, n_a + 1):
            zeilen = breit[n_a + i : n_a + i + len(rest_a)]
            for j in range(-n_phi, n_phi + 1):
                r_p = np.roll(zeilen, -j, axis=1)
                delta = j * schritt_phi
                seitlich = r_p * abs(math.sin(delta))
                abstand = np.sqrt((i * schritt_a) ** 2 + seitlich * seitlich)
                unter = abstand <= radius
                wert = r_p * math.cos(delta) - form.hoehe(np.minimum(abstand, radius))
                np.maximum(tiefste, np.where(unter, wert, -math.inf), out=tiefste)
    tiefste -= grenze
    lage_a = (a - rest_a[0]) / schritt_a
    lage_phi = np.mod(phi - rest_phi[0], 2 * math.pi) / schritt_phi
    ergebnis = np.full(len(a), -math.inf)
    for i in (np.floor(lage_a), np.ceil(lage_a)):
        drin = (i >= 0) & (i < len(rest_a))
        zeile = np.clip(i, 0, len(rest_a) - 1).astype(np.int64)
        for j in (np.floor(lage_phi), np.ceil(lage_phi)):
            spalte = j.astype(np.int64) % len(rest_phi)
            ergebnis = np.maximum(ergebnis, np.where(drin, tiefste[zeile, spalte], -math.inf))
    return ergebnis


def _sehnenfehler(r):
    """Um so viel heben sich die Punkte, damit die Gerade zwischen zwei Punkten nicht unter die
    Hüllfläche fällt, wo sie sich nach außen wölbt: ein Achtel der zweiten Differenz, je
    Punkt das größte der Nachbarschaft, höchstens SEHNE_HOECHSTENS."""
    wolbung = np.zeros(len(r))
    if len(r) >= 3:
        zweite = -(r[:-2] - 2.0 * r[1:-1] + r[2:])
        wolbung[1:-1] = np.clip(zweite / 8.0, 0.0, SEHNE_HOECHSTENS)
    heben = wolbung.copy()
    heben[1:] = np.maximum(heben[1:], wolbung[:-1])
    heben[:-1] = np.maximum(heben[:-1], wolbung[1:])
    return heben


def _zusammengefasst(r, toleranz, hoechstens, fest=()):
    """Die Punkte, die bleiben: Anfang, Ende, die Punkte in `fest` und so wenige dazwischen,
    dass die Gerade zwischen zwei bleibenden Punkten über keinem ausgelassenen liegt und
    höchstens `toleranz` darüber – zwischen ihnen sind a und φ linear (an den Punkten in
    `fest` knickt a: ein Ring beginnt oder endet). Höchstens `hoechstens` Punkte weit."""
    werte = r.tolist()
    fest = set(fest)
    bleibt = [0]
    anfang = 0
    unten, oben = -math.inf, math.inf  # erlaubte Steigung ab dem Anfang
    for i in range(1, len(werte)):
        schritte = i - anfang
        steigung = (werte[i] - werte[anfang]) / schritte
        if schritte > hoechstens or not unten <= steigung <= oben:
            anfang = i - 1
            bleibt.append(anfang)
            schritte = 1
            unten, oben = -math.inf, math.inf
        # Ab hier muss die Gerade über Punkt i liegen, höchstens `toleranz` darüber.
        unten = max(unten, (werte[i] - werte[anfang]) / schritte)
        oben = min(oben, (werte[i] + toleranz - werte[anfang]) / schritte)
        if i in fest and i < len(werte) - 1:
            bleibt.append(i)
            anfang = i
            unten, oben = -math.inf, math.inf
    if bleibt[-1] != len(werte) - 1:
        bleibt.append(len(werte) - 1)
    return bleibt


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


def _knicke(r, abstand, a=None, phi=None):
    """Die Stellen der Spirale, die bleiben: Anfang, Ende, wo der Radius sich ändert, wo ein
    Ring beginnt oder endet (`a` ändert dort seine Steigung), wo die Rundachse umkehrt
    (`phi`, hin und her) und alle `abstand` Stellen eine – dazwischen liegen die Punkte auf
    einer Geraden in (a, r, φ)."""
    anders = np.abs(np.diff(r)) > GLEICH
    bleibt = np.arange(len(r)) % abstand == 0
    bleibt[0] = bleibt[-1] = True
    bleibt[1:-1] |= anders[:-1] | anders[1:]
    for x in (a, phi):
        if x is not None and len(x) > 2:
            bleibt[1:-1] |= _a_knicke(x)
    return np.nonzero(bleibt)[0]


def _a_knicke(a):
    """Je innerem Punkt: Ändert `a` dort seine Steigung – beginnt oder endet ein Ring?"""
    return np.abs(np.diff(a, 2)) > GLEICH


def befehle(
    bahn, laengs, radial, buchstabe, drehsinn, vorschub, quer_auf_null=True, eintauchen=None
):
    """Die Bahn als Path-Befehle.

    X, Y und Z sind die Spitze im Rahmen der Maschine: a längs, r radial (die
    Richtung `radial`). Die Rundachse `buchstabe` dreht das Teil darunter:
    Steht das Werkzeug unter φ zum Teil, ist ihr Wert −drehsinn · φ. `drehsinn`
    +1 heißt, ein positiver Wert dreht das Teil rechtshändig um `laengs` – so
    zeigt FreeCAD die Bahn. Vorschübe stehen zwischen G93 und G94: F = 1 ÷ Zeit,
    damit der Fräser am Werkstück mit `vorschub` (mm/min) fährt, egal wie weit er
    von der Achse weg ist. CAM führt F in mm/s, der Postprozessor schreibt ×60 –
    deshalb steht hier F ÷ 60. `quer_auf_null`: die Achse quer (bei C das Y) am
    Anfang auf 0, damit das Werkzeug auf der Mitte steht. `eintauchen`: der Vorschub
    (mm/min) zu Punkten, an denen der Fräser senkrecht eintaucht; ohne: `vorschub`.
    """
    import Path

    l_, u_, v_ = vh.rahmen(laengs, radial)
    genutzt = [i for i in range(3) if abs(l_[i]) > GLEICH or abs(u_[i]) > GLEICH]
    quer = [i for i in range(3) if i not in genutzt]
    radial_achsen = [i for i in range(3) if abs(u_[i]) > GLEICH]
    # Fährt die Bahn quer versetzt (Plan indexiert), steht die Querachse in jedem Satz.
    mit_quer = any(abs(p.q) > GLEICH for p in bahn.punkte)

    def lage(punkt):
        spitze = l_ * punkt.a + u_ * punkt.r + v_ * punkt.q
        werte = {"XYZ"[i]: float(spitze[i]) for i in genutzt}
        if mit_quer:
            werte.update({"XYZ"[i]: float(spitze[i]) for i in quer})
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
    f_vorher = None
    for punkt in bahn.punkte[1:]:
        if punkt.eilgang:
            ergebnis.append(Path.Command("G0", lage(punkt)))
        else:
            weg = _weg(vorher, punkt)
            if weg < 1e-6:
                continue
            werte = lage(punkt)
            f = (eintauchen if punkt.eintauchen and eintauchen else vorschub) * punkt.anteil
            werte["F"] = f_vorher = _anderes_f(f / weg / 60.0, f_vorher)
            ergebnis.append(Path.Command("G1", werte))
        vorher = punkt
    ergebnis.append(Path.Command("G94"))
    return ergebnis


def _anderes_f(f, vorher):
    """F für G93 auf F_STELLEN Stellen – gleicht es dem F davor, eine Einheit der letzten
    Stelle mehr. In G93 muss F in jedem Satz stehen, doch manche Postprozessoren (Fanuc,
    UCCNC) lassen ein F weg, das dem vorigen gleicht (P-2026-09-30-39, Manuel: „Es muss ja für
    alle funktionieren“). So bleibt es verschieden, auch nach Speichern und Laden; im Programm
    (F × 60 auf 3 Stellen) sieht man den Unterschied nicht."""
    f = round(f, F_STELLEN)
    if vorher is not None and f == vorher:
        f = round(f + 10.0**-F_STELLEN, F_STELLEN)
    return f


def _weg(von, nach):
    """Der Weg der Spitze am Werkstück von einem Punkt zum nächsten (mm)."""
    r = math.hypot((von.r + nach.r) / 2, (von.q + nach.q) / 2)
    bogen = r * math.radians(nach.phi - von.phi)
    laengs, radial, quer = nach.a - von.a, nach.r - von.r, nach.q - von.q
    return math.sqrt(laengs * laengs + radial * radial + quer * quer + bogen * bogen)


def dauer(bahn, vorschub, eintauchen=None):
    """So lange fährt die Bahn im Vorschub (Minuten) – ohne Eilgänge; `eintauchen` wie bei
    befehle()."""
    zeit = 0.0
    for von, nach in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        if not nach.eilgang:
            f = (eintauchen if nach.eintauchen and eintauchen else vorschub) * nach.anteil
            zeit += _weg(von, nach) / f
    return zeit
