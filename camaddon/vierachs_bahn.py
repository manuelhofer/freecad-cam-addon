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
SCHRITT_PHI_SCHLICHTEN = 0.5  # Grad – so dicht liegen die Punkte der Schlichtspirale
TOLERANZ_SCHLICHTEN = 0.005  # mm – so fein wird das Teil fürs Schlichten vernetzt
BAHN_TOLERANZ = 0.002  # mm – so weit darf die zusammengefasste Bahn über den Punkten liegen
SCHLICHT_ZUGABE = 0.5  # mm – Schlichten schneidet mindestens Aufmaß des Schruppens + das
# mm – höchstens so viel hebt der Sehnenfehler einen Punkt: Er gilt für Rundungen; an einer
# Kante springt die Hüllfläche, dort dringt die Gerade kaum ein (längs, um Tausendstel).
SEHNE_HOECHSTENS = 0.02


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
    # Der Rest nach dem Schruppen: (a, φ in rad, r) wie restmaterial.Stange; None: kein Schutz.
    rest: tuple = None
    aufmass_schruppen: float = 0.0  # so viel ließ das Schruppen stehen


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
    l_, _u, _v = vh.rahmen(laengs, radial)
    a_teil = netz.punkte @ l_
    teil_vorne, teil_hinten = float(a_teil.max()), float(a_teil.min())
    ueberlauf = ueberlauf_vorschlag(radius) if w.ueberlauf is None else w.ueberlauf
    a_anfang = w.a_stange_vorne + radius + w.sicherheit
    a_ende = max(teil_hinten - ueberlauf, w.a_futter + radius + w.abstand_futter)
    if a_ende >= teil_vorne + radius:
        raise ValueError(tr("vb.fehler.platz"))
    hinten_frei = max(0.0, a_ende - radius - teil_hinten)

    # Die Spirale: Punkt k liegt bei a_anfang − s · k / N unter dem Winkel k · Δφ. Je Winkel
    # j kommt sie an a_anfang − s · (j / N + m) vorbei – dort rechnet die Hüllfläche.
    phi = vh.raster_phi(schritt_phi)
    je_umdrehung = len(phi)
    s = w.schrittweite
    anzahl = int(math.ceil((a_anfang - a_ende) / s * je_umdrehung - 1e-9))
    umdrehungen = int(math.ceil(anzahl / je_umdrehung))
    zugabe = w.aufmass + netz.toleranz  # das Netz liegt bis zu seiner Toleranz innen
    anfang_je_winkel = a_anfang - s * (np.arange(je_umdrehung) / je_umdrehung + umdrehungen)
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
    r = huelle[umdrehungen - k // je_umdrehung, k % je_umdrehung]
    r = np.where(np.isfinite(r), r, w.stange_radius)  # trifft rundum nichts: bleibt oben
    r = np.maximum(r, radius)  # nicht näher an die Achse
    # Wo das Schruppen mehr stehen ließ als die Grenze (eine Innenecke, eine enge Nut), fährt
    # Schlichten vorher in Stufen, von oben nach unten – jede höchstens die Grenze unter der
    # davor, nur wo es nötig ist.
    stufen, grenze = [], 0.0
    if w.rest is not None:
        grenze = max(radius, w.aufmass_schruppen + SCHLICHT_ZUGABE)
        oben = _nicht_tiefer(w.rest, form, 0.0, a, k * math.radians(schritt_phi))
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
    winkel = k * schritt_phi
    punkte = [Punkt(True, a_anfang, sicher, 0.0)]
    umdrehungen_vor = 0
    for r_stufe, stuecke in stufen:
        for von, bis in stuecke:
            _spirale(punkte, a, r_stufe, winkel, von, bis, sicher, abstand)
            umdrehungen_vor += (bis - von) / je_umdrehung
    _spirale(punkte, a, r, winkel, 0, anzahl, sicher, abstand)
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


def _spirale(punkte, a, r, winkel, von, bis, sicher, abstand):
    """Hängt das Stück von..bis der Spirale an `punkte`: im Eilgang über den Anfang, hinein,
    die Spirale mit Sehnenfehler und zusammengefasst, radial hinaus. Der Winkel zählt weiter,
    wo die Rundachse steht – sie dreht nicht zurück."""
    weiter = punkte[-1].phi
    versatz = 360.0 * math.ceil((weiter - winkel[von]) / 360.0 - 1e-9)
    stueck = r[von : bis + 1]
    stueck = stueck + _sehnenfehler(stueck)
    anfahren = Punkt(True, float(a[von]), sicher, float(winkel[von] + versatz))
    if anfahren != punkte[-1]:
        punkte.append(anfahren)
    for i in _zusammengefasst(stueck, BAHN_TOLERANZ, abstand):
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


def _zusammengefasst(r, toleranz, hoechstens):
    """Die Punkte, die bleiben: Anfang, Ende und so wenige dazwischen, dass die Gerade zwischen
    zwei bleibenden Punkten über keinem ausgelassenen liegt und höchstens `toleranz` darüber
    – längs der Spirale sind a und φ ohnehin linear. Höchstens `hoechstens` Punkte weit."""
    werte = r.tolist()
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
