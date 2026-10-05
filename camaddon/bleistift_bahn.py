# SPDX-License-Identifier: LGPL-2.1-or-later
"""3D, die Bahn „Bleistift“ (W-006 4.2 Punkt 6): Kehlen nachfahren. Wo der Kugelfräser zwei
Flächen zugleich berührt – die gewählte Freiformfläche und ihre Nachbarin, etwa die Platte am
Fuß einer Kuppel –, knickt seine Hüllfläche nach oben: Die Zeilen des 3D-Schlichtens enden
dort, zwischen ihren Enden bleibt ein Rest. Der Bleistift fährt den Knick in einem Zug nach.

- Die Hüllfläche im Raster (RASTER) über den gewählten Flächen ± R, wie beim 3D-Schlichten
  (schlichten3d_bahn._raster): mit dem ganzen Teil, und wo die gewählten Flächen die Höhe
  bestimmen.
- **Ein Knick:** Die zweite Differenz in einer der vier Richtungen (x, y, zwei Diagonalen),
  geteilt durch den Abstand, ist größer als KNICK – die Steigung springt um mehr als KNICK
  (eine glatte Fläche bleibt weit darunter). Nur das Maximum quer zum Knick (eine Zelle breit)
  und nur an den gewählten Flächen; die Lage zwischen den Zellen aus den Nachbarn (die Spitze
  eines V), nicht aus dem Raster.
- Die Knickzellen zu **Linien** verkettet (8 Nachbarn, möglichst geradeaus), geglättet;
  kürzere als MINDESTLAENGE fallen weg. Die Höhe genau – die Hüllfläche an jedem Punkt (alle
  ABSTAND mm), nicht aus dem Raster –, dann vereinfacht (Douglas-Peucker im Raum).
- **Fahren:** Linie für Linie, die nächste zuerst (von ihrem näheren Ende, ein Ring ab der
  nächsten Stelle), im Eilgang über dem Rohteil hin, senkrecht hinab im Eintauchvorschub, auf
  der Linie im Vorschub, hinauf.
- **Bahnen je Seite** (`bahnen`, Vorgabe 0 – nur die Kehle): daneben je Seite so viele Bahnen,
  quer im Abstand `seitlich` (0: der Zeilenabstand des Fräsers bei der Grathöhe GRATHOEHE) – im
  Raum gemessen: An einer steilen Seite rückt die nächste Bahn quer weniger weit, damit sie im
  Raum nicht weiter weg liegt (_daneben). Von außen zur Kehle, abwechselnd links und rechts, die
  Kehle zuletzt; zwischen zwei Bahnen einer Kehle ein kurzer Hub (SICHERHEIT über dem Höheren
  der beiden Enden und der Hüllfläche dazwischen) statt bis über das Rohteil.

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import bahn as bn
from . import hoehenfeld as hf
from . import schlichten3d_bahn as sb
from . import vierachs_bahn as vb
from . import vierachs_huelle as vh
from .sprache import tr

RASTER = 0.25  # mm – das Raster der Hüllfläche
VORSCHAU_RASTER = 0.5  # mm – im Assistenten
TOLERANZ_NETZ = sb.TOLERANZ_NETZ
VORSCHAU_TOLERANZ = sb.VORSCHAU_TOLERANZ
KNICK = 0.3  # so weit muss die Steigung springen (tan) – rund 17°
MINDESTLAENGE = 2.0  # mm – kürzere Linien fallen weg
ABSTAND = 0.5  # mm – so dicht wird die Höhe auf der Linie genau gerechnet
TOLERANZ_GERADE = 0.003  # mm – so weit darf ein ausgelassener Punkt von der Geraden liegen
GLAETTEN = 2  # Zellen je Seite – über so viele wird die Linie gemittelt
GRATHOEHE = 0.01  # mm – daraus der Abstand der Bahnen neben der Kehle, wenn keiner vorgegeben ist


@dataclass
class Bleistiftwerte:
    """Was der Bleistift braucht; Längen in mm, z nach oben im Job."""

    form: object  # fraeserform.Form – am besten eine Kugel
    oben: float  # z, über dem nichts mehr steht (das Rohteil)
    sicher: float  # z für den Eilgang über allem
    aufmass: float = 0.0
    sicherheit: float = vb.SICHERHEIT
    raster: float = RASTER
    vorschub: float = 0.0  # mm/min – für die Zeit; 0: 1000
    eintauchen: float = 0.0
    bahnen: int = 0  # je Seite so viele Bahnen neben der Kehle
    seitlich: float = 0.0  # mm – ihr Abstand im Raum; 0: aus GRATHOEHE und der Form


@dataclass
class Bleistiftbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    linien: int  # so viele Kehlen
    laenge: float  # mm im Vorschub
    zeit: float  # Minuten (bahn.zeit)
    z_min: float
    ringe: int = 0  # davon geschlossen (Bahnen, nicht Kehlen)
    bahnen: int = 0  # Bahnen zusammen – mit denen neben den Kehlen


def _verschoben(a, di, dj):
    """b[i, j] = a[i + di, j + dj] – nan außerhalb."""
    b = np.full(a.shape, np.nan)
    nx, ny = a.shape
    i0, i1 = max(0, -di), min(nx, nx - di)
    j0, j1 = max(0, -dj), min(ny, ny - dj)
    if i1 > i0 and j1 > j0:
        b[i0:i1, j0:j1] = a[i0 + di : i1 + di, j0 + dj : j1 + dj]
    return b


RICHTUNGEN = ((1, 0), (0, 1), (1, 1), (1, -1))


def knicke(z, gewaehlt, schritt):
    """(Maske, Versatz (nx, ny, 2) in Zellen) – die Zellen, an denen die Hüllfläche `z` nach oben
    knickt (Kehlen), eine Zelle breit, nah an den gewählten Flächen; der Versatz zur Spitze des
    V zwischen den Zellen."""
    zz = np.where(np.isfinite(z), z, np.nan)
    werte = []
    for di, dj in RICHTUNGEN:
        abstand = schritt * math.hypot(di, dj)
        k = (_verschoben(zz, di, dj) + _verschoben(zz, -di, -dj) - 2.0 * zz) / abstand
        werte.append(np.where(np.isnan(k), -np.inf, k))
    werte = np.array(werte)
    richtung = np.argmax(werte, axis=0)
    beste = np.take_along_axis(werte, richtung[None], axis=0)[0]
    vor = np.full(z.shape, -np.inf)
    zurueck = np.full(z.shape, -np.inf)
    for k, (di, dj) in enumerate(RICHTUNGEN):
        hier = richtung == k
        vor = np.where(hier, np.nan_to_num(_verschoben(werte[k], di, dj), nan=-np.inf), vor)
        zurueck = np.where(
            hier, np.nan_to_num(_verschoben(werte[k], -di, -dj), nan=-np.inf), zurueck
        )
    nah = gewaehlt.copy()
    for _ in range(2):
        breiter = nah.copy()
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                breiter |= np.nan_to_num(_verschoben(nah.astype(float), di, dj), nan=0.0) > 0.5
        nah = breiter
    maske = (beste > KNICK) & (beste >= zurueck) & (beste > vor) & nah
    # Die Spitze des V: zwischen den Zellen, nach den Werten der Nachbarn.
    plus, minus = np.maximum(vor, 0.0), np.maximum(zurueck, 0.0)
    t = np.where(maske, (plus - minus) / np.maximum(beste + plus + minus, 1e-12), 0.0)
    d = np.array(RICHTUNGEN, dtype=float)[richtung]
    return maske, d * t[..., None]


def _linien(maske):
    """[(Zellen [(i, j)], geschlossen)] – die Knickzellen zu Linien verkettet: von einem Ende
    (oder irgendwo im Ring) aus immer zur Nachbarzelle, die am wenigsten abbiegt."""
    rest = set(zip(*np.nonzero(maske), strict=True))
    nachbarn = [(di, dj) for di in (-1, 0, 1) for dj in (-1, 0, 1) if di or dj]

    def grad(c):
        return sum((c[0] + di, c[1] + dj) in rest for di, dj in nachbarn)

    ergebnis = []
    while rest:
        start = min(rest, key=lambda c: (grad(c) != 1, c))
        zug = [start]
        rest.discard(start)
        richtung = None
        while True:
            jetzt = zug[-1]
            frei = [(di, dj) for di, dj in nachbarn if (jetzt[0] + di, jetzt[1] + dj) in rest]
            if not frei:
                break
            if richtung is None:
                wahl = min(frei, key=lambda d: (abs(d[0]) + abs(d[1]), d))
            else:
                wahl = max(
                    frei,
                    key=lambda d: (d[0] * richtung[0] + d[1] * richtung[1]) / math.hypot(*d),
                )
            richtung = wahl
            naechste = (jetzt[0] + wahl[0], jetzt[1] + wahl[1])
            zug.append(naechste)
            rest.discard(naechste)
        geschlossen = (
            len(zug) > 8 and max(abs(zug[-1][0] - zug[0][0]), abs(zug[-1][1] - zug[0][1])) <= 1
        )
        ergebnis.append((zug, geschlossen))
    # Wo der Knick schräg durchs Raster läuft, ist er stellenweise zwei Zellen breit: Die zweite
    # Zelle wird ein kurzes Stück neben der Linie – es fällt weg, wenn es fast ganz neben einer
    # längeren liegt.
    ergebnis.sort(key=lambda linie: -len(linie[0]))
    belegt = set()
    behalten = []
    for zug, geschlossen in ergebnis:
        neben = sum(
            any((c[0] + di, c[1] + dj) in belegt for di in range(-2, 3) for dj in range(-2, 3))
            for c in zug
        )
        if neben > len(zug) / 2:
            continue
        behalten.append((zug, geschlossen))
        belegt.update(zug)
    return behalten


def _geglaettet(punkte, geschlossen):
    """Gleitender Mittelwert über GLAETTEN Punkte je Seite – an offenen Enden kürzer."""
    n = len(punkte)
    if n < 3:
        return punkte
    ergebnis = np.empty_like(punkte)
    for k in range(n):
        if geschlossen:
            fenster = [(k + m) % n for m in range(-GLAETTEN, GLAETTEN + 1)]
        else:
            breite = min(GLAETTEN, k, n - 1 - k)
            fenster = range(k - breite, k + breite + 1)
        ergebnis[k] = punkte[list(fenster)].mean(axis=0)
    return ergebnis


def _dichter(punkte, geschlossen, abstand):
    """Die Punkte so ergänzt, dass keine zwei weiter als `abstand` auseinanderliegen."""
    zug = np.vstack([punkte, punkte[:1]]) if geschlossen else punkte
    ergebnis = [zug[0]]
    for a, b in zip(zug[:-1], zug[1:], strict=True):
        teile = max(1, int(math.ceil(math.hypot(*(b - a)) / abstand)))
        for k in range(1, teile + 1):
            ergebnis.append(a + (b - a) * k / teile)
    return np.array(ergebnis)


def huelle_an(netz, form, x, y):
    """Die Hüllfläche (so tief darf die Spitze) an den Punkten (x, y) – genau, nicht aus dem
    Raster; KEIN_TREFFER, wo der Fräser das Teil nicht trifft."""
    punkte = netz.punkte
    a, quer, z = punkte[:, 0], punkte[:, 1], punkte[:, 2]
    hub = hf._UEBER_NULL - float(z.min()) if len(z) and z.min() <= 0.0 else 0.0
    hoehe = z + hub
    kanten = vh._kanten(netz.dreiecke)
    ergebnis = np.full(len(x), hf.KEIN_TREFFER)
    for k, (px, py) in enumerate(zip(x, y, strict=True)):
        spalte = np.full(1, hf.KEIN_TREFFER)
        vh._form_treffen(
            spalte, a, hoehe, quer - float(py), kanten, netz.dreiecke, form, float(px), 1.0
        )
        if np.isfinite(spalte[0]):
            ergebnis[k] = spalte[0] - hub
    return ergebnis


def _vereinfacht3d(punkte):
    """Douglas-Peucker im Raum mit TOLERANZ_GERADE – die Indizes, die bleiben."""
    n = len(punkte)
    if n <= 2:
        return list(range(n))
    behalten = np.zeros(n, dtype=bool)
    behalten[0] = behalten[-1] = True
    stapel = [(0, n - 1)]
    while stapel:
        i, j = stapel.pop()
        if j - i < 2:
            continue
        p, q = punkte[i], punkte[j]
        d = q - p
        laenge = float(np.linalg.norm(d))
        innen = punkte[i + 1 : j]
        if laenge < 1e-12:
            abstand = np.linalg.norm(innen - p, axis=1)
        else:
            abstand = np.linalg.norm(np.cross(innen - p, d), axis=1) / laenge
        k = int(np.argmax(abstand))
        if abstand[k] > TOLERANZ_GERADE:
            m = i + 1 + k
            behalten[m] = True
            stapel.append((i, m))
            stapel.append((m, j))
    return list(np.flatnonzero(behalten))


def planen(form_teil, namen, werte, toleranz=TOLERANZ_NETZ):
    """Die Bahn „Bleistift“ (Bleistiftbahn) an den Kehlen der Freiformflächen `namen` von
    `form_teil`. ValueError mit einem Satz, wenn es nicht geht."""
    from . import vierachs_flaechen as vf

    w = werte
    if w.form is None or w.form.radius <= 0:
        raise ValueError(tr("bs.fehler.form"))
    flaechen = sb.freiformflaechen(form_teil, namen)
    if not flaechen:
        raise ValueError(tr("s3.fehler.keine"))
    box = None
    for nummer in vf.nummern(flaechen):
        bb = form_teil.Faces[nummer].BoundBox
        teil = (bb.XMin, bb.XMax, bb.YMin, bb.YMax)
        box = (
            teil
            if box is None
            else (
                min(box[0], teil[0]),
                max(box[1], teil[1]),
                min(box[2], teil[2]),
                max(box[3], teil[3]),
            )
        )
    netz_alle, netz_rest, _gewaehlt = sb._netze(form_teil, flaechen, toleranz)
    aufmass = max(w.aufmass, 0.0)
    geformt = w.form.mit_aufmass(aufmass)
    raster = sb._raster(netz_alle, netz_rest, geformt, box, w)
    schritt = float(raster.xs[1] - raster.xs[0])
    maske, versatz = knicke(raster.z, raster.gewaehlt, schritt)
    linien = []  # je Kehle die Bahnen in ihrer Reihenfolge: [(raum, geschlossen), …]
    seitlich = w.seitlich if w.seitlich > 0 else sb.zeilenabstand(w.form, GRATHOEHE)
    for zellen, geschlossen in _linien(maske):
        i = np.array([c[0] for c in zellen])
        j = np.array([c[1] for c in zellen])
        xy = np.column_stack(
            [
                raster.xs[i] + versatz[i, j, 0] * schritt,
                raster.ys[j] + versatz[i, j, 1] * schritt,
            ]
        )
        xy = _geglaettet(xy, geschlossen)
        laenge = float(np.sum(np.hypot(*np.diff(xy, axis=0).T)))
        if laenge < MINDESTLAENGE:
            continue
        dicht = _dichter(xy, geschlossen, ABSTAND)
        z = huelle_an(netz_alle, geformt, dicht[:, 0], dicht[:, 1])
        if not np.all(np.isfinite(z)):
            continue
        raum = np.column_stack([dicht, z + aufmass])
        bahnen = [(raum[_vereinfacht3d(raum)], geschlossen)]
        if w.bahnen > 0:
            seiten = [_daneben(dicht, z, geschlossen, s, seitlich, w.bahnen, netz_alle, geformt)
                      for s in (1.0, -1.0)]  # fmt: skip
            neben = []
            for k in range(w.bahnen - 1, -1, -1):  # von außen zur Kehle
                for seite in seiten:
                    if k < len(seite):
                        teil = np.column_stack([seite[k][:, :2], seite[k][:, 2] + aufmass])
                        neben.append((teil[_vereinfacht3d(teil)], geschlossen))
            bahnen = neben + bahnen
        linien.append(bahnen)
    if not linien:
        raise ValueError(tr("bs.fehler.keine_kehle"))
    return _fahren(linien, w, netz_alle, geformt, aufmass)


def _daneben(dicht, z, geschlossen, seite, seitlich, anzahl, netz, form):
    """Die Bahnen neben einer Kehle auf einer Seite (`seite` +1: links der Laufrichtung, −1:
    rechts): [Punkte (n, 3)] von innen nach außen, höchstens `anzahl`. Quer zur Linie (in der
    Ebene) so weit, dass die nächste Bahn im Raum `seitlich` neben der vorigen liegt – an einer
    steilen Seite quer weniger weit (ein Schritt mit dem Höhenunterschied, dann nachgerechnet).
    Eine Bahn, an der der Fräser irgendwo nichts trifft, beendet die Seite."""
    zug = np.vstack([dicht[-1:], dicht, dicht[:1]]) if geschlossen else dicht
    tangente = np.gradient(zug, axis=0)
    if geschlossen:
        tangente = tangente[1:-1]
    laenge = np.hypot(tangente[:, 0], tangente[:, 1])
    laenge[laenge < 1e-12] = 1.0
    normale = np.column_stack([-tangente[:, 1], tangente[:, 0]]) / laenge[:, None] * seite
    weit = np.zeros(len(dicht))
    z_vorher = np.asarray(z, dtype=float)
    ergebnis = []
    for _k in range(anzahl):
        versuch = weit + seitlich
        xy = dicht + normale * versuch[:, None]
        z_versuch = huelle_an(netz, form, xy[:, 0], xy[:, 1])
        if not np.all(np.isfinite(z_versuch)):
            break
        # Im Raum soll die Bahn `seitlich` neben der vorigen liegen: quer nur so weit, wie es
        # bei diesem Anstieg dafür reicht.
        dz = z_versuch - z_vorher
        weit = weit + seitlich * seitlich / np.sqrt(seitlich * seitlich + dz * dz)
        xy = _geglaettet(dicht + normale * weit[:, None], geschlossen)
        z_neu = huelle_an(netz, form, xy[:, 0], xy[:, 1])  # genau dort, wo die Bahn liegt
        if not np.all(np.isfinite(z_neu)):
            break
        ergebnis.append(np.column_stack([xy, z_neu]))
        z_vorher = z_neu
    return ergebnis


def _hub(von, nach, w, netz, form, aufmass):
    """Wie hoch der kurze Hub zwischen zwei Bahnen einer Kehle geht: SICHERHEIT über dem
    Höheren der beiden Enden und der Hüllfläche dazwischen (fünf Stellen)."""
    t = np.linspace(0.0, 1.0, 5)
    x = von[0] + (nach[0] - von[0]) * t
    y = von[1] + (nach[1] - von[1]) * t
    unter = huelle_an(netz, form, x, y)
    hoechstes = (
        float(np.max(unter[np.isfinite(unter)])) + aufmass if np.isfinite(unter).any() else w.oben
    )
    return min(w.sicher, max(hoechstes, von[2], nach[2]) + w.sicherheit)


def _fahren(linien, w, netz=None, form=None, aufmass=0.0):
    """Die Kehlen abfahren, die nächste zuerst; je Kehle ihre Bahnen der Reihe nach (von außen
    zur Kehle), dazwischen ein kurzer Hub, die nächste Bahn vom näheren Ende."""
    knapp = min(w.sicher, w.oben + w.sicherheit)
    offen = list(linien)
    ort = None
    punkte = []
    laenge = 0.0
    z_min = math.inf
    ringe = 0
    zaehlen = sum(len(gruppe) for gruppe in linien)
    while offen:
        if ort is None:
            k, umkehren, beginn = 0, False, 0
        else:
            beste = None
            for n, gruppe in enumerate(offen):
                raum, geschlossen = gruppe[0]
                abstand = np.hypot(raum[:, 0] - ort[0], raum[:, 1] - ort[1])
                if geschlossen:
                    m = int(np.argmin(abstand))
                    kandidat = (float(abstand[m]), n, False, m)
                else:
                    kandidat = min(
                        (float(abstand[0]), n, False, 0), (float(abstand[-1]), n, True, 0)
                    )
                if beste is None or kandidat < beste:
                    beste = kandidat
            _, k, umkehren, beginn = beste
        gruppe = offen.pop(k)
        for nummer, (raum, geschlossen) in enumerate(gruppe):
            if (
                nummer
            ):  # die nächste Bahn derselben Kehle: vom näheren Ende bzw. der nächsten Stelle
                abstand = np.hypot(raum[:, 0] - ort[0], raum[:, 1] - ort[1])
                beginn = int(np.argmin(abstand)) if geschlossen else 0
                umkehren = not geschlossen and abstand[-1] < abstand[0]
            if geschlossen:
                gerollt = np.roll(raum, -beginn, axis=0)
                raum = np.vstack([gerollt, gerollt[:1]])
                ringe += 1
            elif umkehren:
                raum = raum[::-1]
            x0, y0, z0 = (float(v) for v in raum[0])
            if nummer:
                letzter = punkte[-1]
                hoch = _hub((letzter.x, letzter.y, letzter.z), (x0, y0, z0), w, netz, form, aufmass)
                punkte.append(bn.Punkt(True, letzter.x, letzter.y, hoch))
                punkte.append(bn.Punkt(True, x0, y0, hoch))
            else:
                punkte.append(bn.Punkt(True, x0, y0, w.sicher if ort is None else knapp))
                punkte.append(bn.Punkt(True, x0, y0, z0 + w.sicherheit))
            punkte.append(bn.Punkt(False, x0, y0, z0, True))
            for x, y, z in raum[1:]:
                punkt = bn.Punkt(False, float(x), float(y), float(z))
                laenge += bn.weg(punkte[-1], punkt)
                punkte.append(punkt)
            z_min = min(z_min, float(raum[:, 2].min()))
            ort = (punkte[-1].x, punkte[-1].y)
        letzter = punkte[-1]
        punkte.append(bn.Punkt(True, letzter.x, letzter.y, knapp))
    punkte.append(bn.Punkt(True, punkte[-1].x, punkte[-1].y, w.sicher))
    zeit = bn.zeit(punkte, w.vorschub if w.vorschub > 0 else 1000.0, w.eintauchen or None)
    return Bleistiftbahn(punkte, len(linien), laenge, zeit, z_min, ringe, zaehlen)
