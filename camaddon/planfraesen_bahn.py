# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Bahn „Planfräsen“ (W-006 S3, 4.1 Punkt 1): eine Fläche oben eben – Zeilen hin und her,
in Lagen vom Rohteil bis auf die Fläche plus Aufmaß.

- Je gewählter ebener Fläche nach oben (hoehenfeld.ebenen_oben) die Lagen in gleichen
  Schritten von höchstens der Zustellung, von der Oberkante (das Rohteil) bis auf ihre Höhe
  plus Aufmaß.
- Zeilen in der längeren Richtung der Fläche (längs x oder längs y), quer höchstens den
  Zeilenabstand (ae) auseinander; der ebene Teil der Stirn ragt seitlich um SEITE_ANTEIL · Ø
  über den Rand – so bleibt dort kein Grat –, eine Zeile in der Mitte, wenn die Fläche
  schmaler ist. Zeilen, unter denen kein Rohteil liegt, fallen weg (keine Leerzeile, W-006
  Grundsatz 5).
- Längs reicht jede Zeile um den Überlauf (UEBERLAUF_ANTEIL · Ø, W-006 4.1.1) über die Fläche
  hinaus; wo die Hüllfläche (hoehenfeld.je_zeile, das Teil ohne diese Fläche) höher liegt als
  die Lage – eine Wand, ein Absatz nach oben –, hält sie an. Hin und her
  (vierachs_bahn._fahrten): Am Ende einer Zeile ein Halbkreis (G2/G3) zur nächsten, wo beide
  Zeilen dort frei sind; sonst in der Tiefe quer hinüber, oder abheben. Die erste Zeile einer
  Lage beginnt an dem Ende, das in der Luft liegt.
- Hinein: in der Luft (neben dem Rohteil) senkrecht mit dem Eintauchvorschub; im Material
  über die Rampe mit dem Eintauchwinkel längs der ersten Zeile (vierachs_bahn._rampe).
- Beim Austritt aus dem Rohteil fährt die Zeile mit AUSTRITT_ANTEIL des Vorschubs (W-006 E6,
  erster Schritt: Grat beim Austritt).
- Gleichlauf durchgehend (Grundsatz 4) kommt mit der Spirale von außen nach innen, sobald das
  Bahnmodell Konturen versetzen kann (S3e); hin und her ist jede zweite Zeile Gegenlauf.

Gerechnet in (u, v, z): u längs der Zeilen, v quer, z nach oben; die Punkte am Ende in x und
y des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import bahn as bn
from . import hoehenfeld as hf
from . import vierachs_bahn as vb
from . import vierachs_planbahn as vp
from .sprache import tr

UEBERLAUF_ANTEIL = 0.6  # vom Fräser-Ø: so weit läuft die Mitte längs über die Fläche hinaus
SEITE_ANTEIL = 0.2  # vom Fräser-Ø: so weit ragt der ebene Teil der Stirn seitlich über den Rand
AUSTRITT_ANTEIL = 0.5  # vom Vorschub: so langsam beim Austritt aus dem Rohteil
SCHRITT = hf.SCHRITT  # mm – Raster längs der Zeilen
VORSCHAU_SCHRITT = 1.0  # mm – für die Vorschau im Assistenten
GLEICH = vb.GLEICH


@dataclass(frozen=True)
class Planwerte:
    """Was das Planfräsen braucht; Längen in mm, z nach oben im Job."""

    form: object  # fraeserform.Form des Fräsers – mit ebener Stirn (Schaft-, Torus-, Planfräser)
    zustellung: float  # ap: höchstens so tief je Lage
    zeilenabstand: float  # ae: höchstens so weit rücken die Zeilen quer
    aufmass: float  # bleibt auf der Fläche stehen (0: fertig)
    oben: float  # z der Oberkante: das Rohteil (hier beginnen die Lagen)
    sicher: float  # z für den Eilgang über allem
    rohteil: tuple  # (x_von, x_bis, y_von, y_bis) des Rohteils von oben
    ueberlauf: float = None  # längs über die Fläche hinaus (Mitte des Fräsers); None: Vorschlag
    seite: float = None  # seitlich über den Rand (ebener Teil der Stirn); None: Vorschlag
    sicherheit: float = vb.SICHERHEIT  # so weit über dem Material endet der Eilgang hinab
    eintauchwinkel: float = vb.EINTAUCHWINKEL  # Grad, für die Rampe ins Material
    austritt: float = AUSTRITT_ANTEIL


@dataclass
class Planbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    flaechen: int  # so viele Flächen
    lagen: int  # Lagen, über alle Flächen
    zeilen: int  # Zeilen, über alle Flächen und Lagen
    z_min: float  # die tiefste Spitze (mm)
    laenge: float  # mm im Vorschub


def ueberlauf_vorschlag(form):
    """Der Überlauf längs, wenn nichts anderes gesagt ist: UEBERLAUF_ANTEIL · Ø."""
    return UEBERLAUF_ANTEIL * 2 * form.radius


def planen(netz, werte, ebenen, schritt=SCHRITT):
    """Die Bahn „Planfräsen“ (Planbahn) über die Flächen `ebenen` ([hoehenfeld.Ebene]) mit den
    Werten `werte`; `netz` ist das Teil ohne diese Flächen (hoehenfeld.netz_ohne). ValueError
    mit einem Satz, wenn es nicht geht."""
    w = werte
    form = w.form
    r_eben = vp.ebener_radius(form)
    if r_eben <= 0:
        raise ValueError(tr("pf.fehler.form"))
    if w.zustellung <= 0 or w.zeilenabstand <= 0:
        raise ValueError(tr("pf.fehler.werte"))
    if w.zeilenabstand > 2 * r_eben:
        raise ValueError(tr("pf.fehler.zeilenabstand"))
    if not ebenen:
        raise ValueError(tr("pf.fehler.keine_ebene"))
    ueberlauf = ueberlauf_vorschlag(form) if w.ueberlauf is None else w.ueberlauf
    seite = SEITE_ANTEIL * 2 * form.radius if w.seite is None else w.seite
    zugabe = netz.toleranz + vb.RAND
    geformt = form.mit_aufmass(netz.toleranz)
    punkte = []
    lagen_gesamt = zeilen_gesamt = gefraest = 0
    z_min = math.inf
    laenge = 0.0
    for ebene in sorted(ebenen, key=lambda e: -e.z):
        ziel = ebene.z + w.aufmass
        oben = w.oben
        if oben <= ziel + GLEICH:
            continue  # steht nichts drüber
        anzahl_lagen = max(1, int(math.ceil((oben - ziel) / w.zustellung - 1e-9)))
        lagen = oben - (oben - ziel) * np.arange(1, anzahl_lagen + 1) / anzahl_lagen
        laengs_x = (ebene.x_bis - ebene.x_von) >= (ebene.y_bis - ebene.y_von)
        if laengs_x:
            u_von, u_bis, v_von, v_bis = ebene.x_von, ebene.x_bis, ebene.y_von, ebene.y_bis
            roh_u, roh_v = w.rohteil[0:2], w.rohteil[2:4]
        else:
            u_von, u_bis, v_von, v_bis = ebene.y_von, ebene.y_bis, ebene.x_von, ebene.x_bis
            roh_u, roh_v = w.rohteil[2:4], w.rohteil[0:2]
        v_zeilen = _zeilen_quer(v_von, v_bis, r_eben - seite, w.zeilenabstand)
        # Keine Leerzeile: nur Zeilen, unter denen das Rohteil liegt.
        v_zeilen = v_zeilen[
            (v_zeilen + r_eben > roh_v[0] + GLEICH) & (v_zeilen - r_eben < roh_v[1] - GLEICH)
        ]
        if not len(v_zeilen):
            continue
        # Das Raster längs: die Zeilen reichen um den Überlauf über die Fläche hinaus, die
        # Hüllfläche um den halben Zeilenabstand weiter – dort prüft der Halbkreis, ob er frei ist.
        halb = w.zeilenabstand / 2
        u0, u1 = u_von - ueberlauf - halb, u_bis + ueberlauf + halb
        anzahl = max(2, int(math.ceil((u1 - u0) / schritt - 1e-9)) + 1)
        u_stellen = np.linspace(u0, u1, anzahl)
        schritt_u = float(u_stellen[1] - u_stellen[0])
        huelle = hf.je_zeile(netz, geformt, v_zeilen, u0, schritt_u, anzahl, laengs_x)
        roh = huelle.T  # (Zeilen, Stellen); −inf, wo er nichts trifft
        hoehe = roh + zugabe
        # Dazu der Rand der Fläche quer: Vor einer Wand fährt die Wandfahrt über die erste und
        # letzte Zeile hinaus bis an den Rand – so weit es dort erlaubt ist (_wandfahrt).
        v_rand = (float(v_von), float(v_bis))
        roh_rand = hf.je_zeile(netz, geformt, v_rand, u0, schritt_u, anzahl, laengs_x).T
        hoehe_rand = roh_rand + zugabe
        im_ueberlauf = (u_stellen >= u_von - ueberlauf - GLEICH) & (
            u_stellen <= u_bis + ueberlauf + GLEICH
        )
        im_rohteil = (u_stellen + r_eben > roh_u[0] + GLEICH) & (
            u_stellen - r_eben < roh_u[1] - GLEICH
        )
        gefraest += 1
        vorige = oben
        for lage in lagen:
            lage = float(lage)
            # Die Lage darf dorthin, wo die Hüllfläche nicht höher liegt – und über den Rand
            # der Fläche hinaus auch, wo nichts höher steht als die Fläche selbst: Die
            # Seitenwand des Teils endet genau auf ihrer Höhe, die Zugabe hielte die unterste
            # Lage sonst vor ihr an (wie bei Plan indexiert, P-2026-10-01-10).
            erlaubt = (hoehe <= lage + GLEICH) | (roh <= ziel + GLEICH)
            erlaubt_rand = (hoehe_rand <= lage + GLEICH) | (roh_rand <= ziel + GLEICH)
            drin = erlaubt & im_ueberlauf[None, :]  # die Zeilen selbst
            if not drin.any():
                vorige = lage
                continue
            raster = _Raster(
                u_stellen,
                v_zeilen,
                drin,
                erlaubt,
                im_rohteil,
                laengs_x,
                roh_u,
                r_eben,
                w.zeilenabstand,
                v_rand,
                erlaubt_rand,
            )
            # Von dem Ende beginnen, das in der Luft liegt – sonst vom Anfang.
            erste = int(np.flatnonzero(drin.any(axis=1))[0])
            js = np.flatnonzero(drin[erste])
            if not im_rohteil[js[0]] and not im_rohteil[js[-1]]:
                pass
            elif not im_rohteil[js[-1]]:
                raster = raster.umgekehrt()
            mit_luecke = np.zeros((len(v_zeilen), anzahl + 2), dtype=bool)
            mit_luecke[:, 1:-1] = raster.drin
            for fahrt in vb._fahrten(mit_luecke):
                laenge += _fahrt(punkte, fahrt, raster, lage, vorige, w)
                zeilen_gesamt += len({m for art, m, _js in fahrt if art == "zeile"})
            lagen_gesamt += 1
            vorige = lage
            z_min = min(z_min, lage)
    if gefraest == 0:
        raise ValueError(tr("pf.fehler.nichts"))
    return Planbahn(
        punkte,
        gefraest,
        lagen_gesamt,
        zeilen_gesamt,
        z_min if math.isfinite(z_min) else 0.0,
        laenge,
    )


def _zeilen_quer(v_von, v_bis, rand, abstand):
    """Die Zeilen quer: von v_von + rand bis v_bis − rand gleich weit auseinander, höchstens
    `abstand`; eine in der Mitte, wenn die Fläche dafür zu schmal ist."""
    breite = v_bis - v_von
    if breite <= 2 * rand + GLEICH:
        return np.array([(v_von + v_bis) / 2])
    anzahl = int(math.ceil((breite - 2 * rand) / abstand - 1e-9)) + 1
    return np.linspace(v_von + rand, v_bis - rand, anzahl)


@dataclass
class _Raster:
    """Eine Lage im Raster: die Stellen längs (in der Reihenfolge, in der die Fahrten gezählt
    werden), die Zeilen quer, wo gefräst wird, wo das Rohteil liegt."""

    u_stellen: np.ndarray  # (N,) in Zählrichtung
    v_zeilen: np.ndarray  # (Zeilen,)
    drin: np.ndarray  # (Zeilen, N): hier fährt die Zeile
    erlaubt: np.ndarray  # (Zeilen, N): die Lage darf dorthin – für den Halbkreis am Ende
    im_rohteil: np.ndarray  # (N,): die Stirn trifft dort das Rohteil
    laengs_x: bool
    roh_u: tuple  # (von, bis) des Rohteils längs
    r_eben: float
    zeilenabstand: float
    v_rand: tuple  # (von, bis) der Fläche quer – vor und hinter der ersten und letzten Zeile
    erlaubt_rand: np.ndarray  # (2, N): die Lage darf an den Rand – für die Wandfahrt

    def umgekehrt(self):
        return _Raster(
            self.u_stellen[::-1],
            self.v_zeilen,
            self.drin[:, ::-1],
            self.erlaubt[:, ::-1],
            self.im_rohteil[::-1],
            self.laengs_x,
            self.roh_u,
            self.r_eben,
            self.zeilenabstand,
            self.v_rand,
            self.erlaubt_rand[:, ::-1],
        )

    def xy(self, u, v):
        return (float(u), float(v)) if self.laengs_x else (float(v), float(u))


def _fahrt(punkte, fahrt, raster, lage, vorige, w):
    """Eine Fahrt (vierachs_bahn._fahrten mit Zeile = Zeile quer, Winkelschritt = Stelle
    längs, mit der Lücke an beiden Enden) an die Bahn: hinein über das erste Stück, die Zeilen,
    zwischen ihnen Halbkreis oder Schritt, am Ende hinauf. Gibt die Länge im Vorschub zurück."""
    r_ = raster
    teile = []  # (art, m, js) mit js ohne die Lücke (0 … N − 1)
    for art, m, js in fahrt:
        if art == "zeile":
            teile.append((art, m, np.asarray(js) - 1))
        else:
            teile.append((art, m, int(js) - 1))
    _art, m0, js0 = teile[0]
    laenge = _einfahrt(punkte, r_, m0, js0, lage, vorige, w)
    for nummer, (art, m, js) in enumerate(teile):
        if art == "zeile":
            laenge += _zeile(punkte, r_, m, js, lage, w, nummer == 0)
            continue
        laenge += _schritt(punkte, r_, m, js, lage, teile, nummer)
    art, m, js = teile[-1]
    if art == "zeile" and len(js) > 1 and _wand(r_, m, int(js[-1]), 1 if js[-1] > js[0] else -1):
        laenge += _wandfahrt(punkte, r_, m, int(js[-1]), lage, teile, len(teile), ende=True)
    letzter = punkte[-1]
    punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
    return laenge


def _wand(r_, m, j, richtung):
    """Endet Zeile m an der Stelle j in Richtung `richtung` vor einer Wand – die nächste Stelle
    ist dort nicht erlaubt? Am Rand des Rasters (dem Überlauf) nicht."""
    k = j + richtung
    return 0 <= k < len(r_.u_stellen) and not bool(r_.erlaubt[m, k])


def _wandfahrt(punkte, r_, m, j, lage, teile, nummer, ende=False):
    """Vor einer Wand (Zeile m endet an der Stelle j): An der Wand bleibt zwischen zwei Zeilen
    stehen, was keine der beiden mit der Rundung der Stirn erreicht – die Zeilen hin und her
    lassen jeden zweiten Zwischenraum an der Wand aus (der Schritt zur nächsten Zeile liegt am
    anderen Ende), und vor der ersten und hinter der letzten Zeile bleibt die Ecke. Darum fährt
    der Fräser hier an der Wand entlang: zurück bis zum Anfang der vorigen Zeile (sie begann an
    dieser Seite) – vor der ersten Zeile bis an den Rand der Fläche, so weit es dort erlaubt ist
    – und wieder her; am `ende` einer Fahrt erst hinter die letzte Zeile bis an den Rand, dann
    zurück, ohne wieder herzukommen. Gibt die Länge zurück."""
    hier = punkte[-1]
    u = float(r_.u_stellen[j])
    v_m = float(r_.v_zeilen[m])
    ziele = []
    letzte = len(r_.v_zeilen) - 1
    if ende and m == letzte and bool(r_.erlaubt_rand[1, j]) and r_.v_rand[1] > v_m + GLEICH:
        ziele.append(r_.xy(u, r_.v_rand[1]))
    vorige = next(
        (js for art, m_, js in reversed(teile[:nummer]) if art == "zeile" and m_ == m - 1), None
    )
    unten = None
    if vorige is not None and len(vorige):
        unten = (float(r_.u_stellen[vorige[0]]), float(r_.v_zeilen[m - 1]))
    elif m >= 1 and bool(r_.erlaubt[m - 1, j]):
        unten = (u, float(r_.v_zeilen[m - 1]))
    if (
        m <= 1
        and bool(r_.erlaubt_rand[0, j])
        and r_.v_rand[0] < float(r_.v_zeilen[0]) - GLEICH
        and (m == 0 or bool(r_.erlaubt[0, j]))
    ):
        unten = (u, r_.v_rand[0])  # über die erste Zeile hinaus bis an den Rand
    if unten is not None:
        ziele.append(r_.xy(*unten))
    if not ziele:
        return 0.0
    if not ende:
        ziele.append((hier.x, hier.y))
    laenge = 0.0
    for x, y in ziele:
        punkt = bn.Punkt(False, x, y, lage)
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge


def _einfahrt(punkte, r_, m, js, lage, vorige, w):
    """Über den Anfang der ersten Zeile im Eilgang, hinab bis knapp über das Material: in der
    Luft senkrecht mit dem Eintauchvorschub auf die Lage; im Rohteil senkrecht bis ans Material
    und dann über die Rampe längs der Zeile. Gibt die Länge der Rampe zurück."""
    u = r_.u_stellen[js]
    v = float(r_.v_zeilen[m])
    x0, y0 = r_.xy(u[0], v)
    punkte.append(bn.Punkt(True, x0, y0, w.sicher))
    luft = not r_.im_rohteil[js[0]]
    oben = lage if luft else vorige
    knapp = min(w.sicher, oben + w.sicherheit)
    if knapp < w.sicher:
        punkte.append(bn.Punkt(True, x0, y0, knapp))
    if luft or len(js) < 2 or vorige <= lage + GLEICH:
        punkte.append(bn.Punkt(False, x0, y0, lage, True))
        return 0.0
    punkte.append(bn.Punkt(False, x0, y0, vorige, True))  # bis ans Material
    tiefe = np.full(len(u), lage)
    still = np.zeros(len(u))
    laenge = 0.0
    for stelle_u, stelle_z, _phi in vb._rampe(u, tiefe, still, 0, len(u) - 1, vorige, w):
        x, y = r_.xy(stelle_u, v)
        punkt = bn.Punkt(False, x, y, float(stelle_z))
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge


def _zeile(punkte, r_, m, js, lage, w, erste):
    """Die Zeile m über die Stellen js (in Fahrtrichtung): bis zum Ende, beim Austritt aus dem
    Rohteil langsamer. Den Anfang gibt es schon (Einfahrt oder Schritt). Gibt die Länge
    zurück."""
    v = float(r_.v_zeilen[m])
    u_a, u_b = float(r_.u_stellen[js[0]]), float(r_.u_stellen[js[-1]])
    laenge = 0.0
    if abs(u_b - u_a) < GLEICH:
        return 0.0
    vorwaerts = u_b > u_a
    kante = r_.roh_u[1] - r_.r_eben if vorwaerts else r_.roh_u[0] + r_.r_eben
    zwischen = (u_a < kante < u_b) if vorwaerts else (u_b < kante < u_a)
    ganz_drin = (u_b <= kante + GLEICH) if vorwaerts else (u_b >= kante - GLEICH)
    if zwischen:
        x, y = r_.xy(kante, v)
        punkt = bn.Punkt(False, x, y, lage)
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    x, y = r_.xy(u_b, v)
    anteil = 1.0 if ganz_drin else w.austritt
    punkt = bn.Punkt(False, x, y, lage, anteil=anteil)
    laenge += bn.weg(punkte[-1], punkt)
    punkte.append(punkt)
    return laenge


def _schritt(punkte, r_, m, j, lage, teile, nummer):
    """Von Zeile m zur nächsten an der Stelle j: ein Halbkreis in Fahrtrichtung hinaus, wenn
    beide Zeilen dort und auf dem Bogen frei sind – sonst gerade quer, vor einer Wand erst
    noch an ihr entlang zur vorigen Zeile und zurück (_wandfahrt). Gibt die Länge
    zurück."""
    v_von, v_bis = float(r_.v_zeilen[m]), float(r_.v_zeilen[m + 1])
    u = float(r_.u_stellen[j])
    x1, y1 = r_.xy(u, v_bis)
    # Die Richtung der Zeile davor: hin (wachsende Stellen) oder zurück.
    richtung = 1
    for art, _m, js in reversed(teile[:nummer]):
        if art == "zeile" and len(js) > 1:
            richtung = 1 if js[-1] > js[0] else -1
            break
    halb = abs(v_bis - v_von) / 2
    schritt_u = abs(float(r_.u_stellen[1] - r_.u_stellen[0])) if len(r_.u_stellen) > 1 else 1.0
    weit = int(math.ceil(halb / schritt_u - 1e-9))
    bis = j + richtung * weit
    frei = 0 <= bis < len(r_.u_stellen)
    if frei:
        stellen = np.arange(j, bis + richtung, richtung)
        frei = bool(r_.erlaubt[m, stellen].all() and r_.erlaubt[m + 1, stellen].all())
    laenge = 0.0
    if frei and halb > GLEICH:
        u_mitte = u
        u_durch = u + richtung * halb
        v_mitte = (v_von + v_bis) / 2
        mx, my = r_.xy(u_mitte, v_mitte)
        durch = r_.xy(u_durch, v_mitte)
        von = (punkte[-1].x, punkte[-1].y)
        uhr = bn.im_uhrzeigersinn(von, (x1, y1), durch)
        punkt = bn.Punkt(False, x1, y1, lage, bogen=(mx, my, uhr))
    else:
        if _wand(r_, m, j, richtung):
            laenge += _wandfahrt(punkte, r_, m, j, lage, teile, nummer)
        punkt = bn.Punkt(False, x1, y1, lage)
    laenge += bn.weg(punkte[-1], punkt)
    punkte.append(punkt)
    if punkt.bogen is None and _wand(r_, m, j, richtung):
        laenge += _ueber_die_letzte(punkte, r_, m + 1, j, lage)
    return laenge


def _ueber_die_letzte(punkte, r_, m, j, lage):
    """Beginnt die letzte Zeile m vor einer Wand (an der Stelle j), bleibt hinter ihr an der
    Wand die Ecke stehen: erst an der Wand entlang bis an den Rand der Fläche und zurück, so
    weit es dort erlaubt ist (wie _wandfahrt vor der ersten Zeile). Gibt die Länge zurück."""
    v_m = float(r_.v_zeilen[m])
    if m != len(r_.v_zeilen) - 1 or not bool(r_.erlaubt_rand[1, j]) or r_.v_rand[1] <= v_m + GLEICH:
        return 0.0
    hier = punkte[-1]
    laenge = 0.0
    for x, y in (r_.xy(float(r_.u_stellen[j]), r_.v_rand[1]), (hier.x, hier.y)):
        punkt = bn.Punkt(False, x, y, lage)
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge
