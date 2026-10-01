# SPDX-License-Identifier: LGPL-2.1-or-later
"""Rohteil und Fertigteil in der Simulation (Spezifikation W-003, Stufe V3g).

Manuel (2026-09-29): „haben wir eine rohteil und fertigteil vergleich in der
‚simualtion‘“.

Die Stange als Radien über (a, φ): r[i, j] – wie weit das Material an der Stelle a_i
längs der Achse unter dem Winkel φ_j reicht (SCHRITT_A × SCHRITT_PHI, wie die
Hüllfläche in vierachs_huelle: φ = 0 in Richtung `radial`, rechtshändig um `laengs`).
Ein radiales Werkzeug – der Fräser von „Rundum schruppen“ und „Rundum schlichten“ zeigt
von außen auf die Achse – nimmt weg, was in ihm liegt: Steht seine Spitze auf dem Radius
r beim Winkel φ_t und der Stelle a_t, trifft ein Strahl aus der Achse unter φ_j
(Δ = φ_j − φ_t, d = a_i − a_t längs) die Stirn des Fräsers (fraeserform: z(ℓ) über der
Spitze im Abstand ℓ von seiner Achse) bei ρ · cos Δ = r + z(ℓ), ℓ = √(d² + (ρ · sin Δ)²);
dort endet das Material. Beim Schaftfräser ist z = 0: ρ = r / cos Δ, solange
r · |tan Δ| ≤ √(R² − d²). Sonst sucht es ℓ von z = 0 aus schrittweise – ℓ wächst mit z,
so kommt es von unten an die erste Lösung heran. Zwischen zwei Punkten der Bahn fährt der
Fräser in Schritten von höchstens TEILSCHRITT am Umfang; die Schritte eines Stücks rechnet
es zusammen.

Steht die Werkzeugachse um q quer versetzt neben dem Strahl („Plan indexiert“, V4c – die
Rundachse steht auf φ_t, der Fräser fährt mit dem Y), ist r die Höhe der Spitze längs der
Werkzeugachse, und der Strahl trifft die Stirn im Abstand ℓ = √(d² + (ρ · sin Δ − q)²) von
ihr – sonst alles gleich.

Am Ende der Vergleich mit dem fertigen Teil (vergleiche): seine Radien im selben
Raster (die Hüllfläche einer Scheibe von einer halben Rasterweite, vierachs_huelle),
je Zelle der Rest darüber – grün bis Aufmaß + 0,1 mm, gelb darüber, rot ab Aufmaß
+ 1 mm; verglichen wird mit dem Aufmaß der letzten Bearbeitung. Blau, wo mehr als
0,05 mm im Teil fehlen – das liest es genau auf dem Strahl (Scheibe GENAU): Neben einer
Wand sähe die breitere Scheibe schon die Wand, und was der Kugelfräser dort weg nahm,
fehlte scheinbar im Teil. An einer scharfen Kante und an den Enden ist erst blau, was
tiefer liegt als die halbe Änderung zur Nachbarzelle – dort weiß das Raster nicht genau, wo
das Teil liegt. Wo das Teil nicht rund um die Achse liegt (manche Strahlen einer Stelle
haben es vor sich, andere nur dahinter oder gar nicht), vergleicht es gar nicht: Ein Fräser nah an der Achse nähme auf
einem Strahl weg, was zwischen Achse und Teil liegt, und für die Stange mit einem Radius je
Strahl fehlte dann das Teil dahinter (Manuels Testteil, P-2026-09-30-44).

Mit gewählten Flächen (V4, bei allen Rundum-Operationen des Jobs) färbt der Vergleich nur
sie: Was nicht gewählt ist, bleibt Stange und zählt nicht als „zu viel stehen geblieben“ –
nur Blau, im Teil, gilt überall.

Läuft ohne Oberfläche; numpy gehört zu FreeCAD.
"""

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from . import fraeserform as ff
from . import vierachs_huelle as vh

SCHRITT_A = 0.5  # mm – Raster längs der Achse
SCHRITT_PHI = 1.0  # Grad – Raster rundum
TEILSCHRITT = 0.5  # mm – so fein fährt der Fräser zwischen zwei Punkten der Bahn
TEILSCHRITTE_JE_BLOCK = 50000  # so viele Teilschritte rechnet fahre_stuecke() auf einmal
GENAU = 1e-3  # mm – mit einer so kleinen Scheibe liest der Vergleich das Teil auf dem Strahl
SUCHSCHRITTE = 30  # so oft rückt ein Strahl höchstens an die Stirn heran
TABELLE = 4096  # so viele Stücke hat die Stirn zum Nachschlagen
ZELLEN_JE_BLOCK = 200000  # so viele Zellen rechnet es auf einmal

# Vergleich mit dem fertigen Teil
GRUEN_BIS = 0.1  # mm über dem Aufmaß
ROT_AB = 1.0  # mm über dem Aufmaß
BLAU_AB = 0.05  # mm im Teil
OHNE_TEIL, GRUEN, GELB, ROT, BLAU = range(5)  # Werte in Vergleich.farbe


class Stange:
    """Die Radien des Materials über (a, φ) – anfangs die ganze Stange."""

    def __init__(self, radius, a_von, a_bis, schritt_a=SCHRITT_A, schritt_phi=SCHRITT_PHI):
        anzahl_a = max(2, int(math.ceil((a_bis - a_von) / schritt_a - 1e-9)) + 1)
        self.a = a_von + schritt_a * np.arange(anzahl_a)
        self.phi = vh.raster_phi(schritt_phi)
        self.radius = float(radius)
        self.r = np.full((anzahl_a, len(self.phi)), self.radius)
        self._schritt_a = float(schritt_a)
        self._schritt_phi = math.radians(schritt_phi)

    def zuruecksetzen(self):
        self.r.fill(self.radius)

    def fahre(self, von, nach, fraeser):
        """Der Fräser fährt von `von` nach `nach` – je (a, r, φ in Grad am Teil) – und nimmt
        weg, was er dabei trifft (den Anfang nicht: der kam mit dem Stück davor). `fraeser`:
        seine Form (fraeserform.Form) oder der Radius eines Schaftfräsers."""
        self.fahre_stuecke([von], [nach], fraeser)

    def fahre_stuecke(self, von, nach, fraeser):
        """Wie fahre(), für viele Stücke auf einmal: `von` und `nach` je (n, 3) – oder (n, 4)
        mit dem Versatz quer (vierachs_bahn.Punkt.q) als viertem Wert. Wie herum er sie
        fährt, ist gleich – weg ist, was irgendein Schritt trifft.

        Blockweise, höchstens TEILSCHRITTE_JE_BLOCK Teilschritte zugleich: Das Minimum je Zelle
        hängt nicht von der Reihenfolge ab, das Ergebnis bleibt gleich – nur der Speicher
        bleibt klein (vorher 195 MB für 1,1 Millionen Teilschritte am großen Teil, W-006
        S1, P-2026-09-30-77)."""
        von, nach = _mit_versatz(von), _mit_versatz(nach)
        if not len(von):
            return
        bogen = np.abs(np.radians(nach[:, 2] - von[:, 2])) * np.maximum(von[:, 1], nach[:, 1])
        gerade = np.abs(nach[:, [0, 1, 3]] - von[:, [0, 1, 3]]).max(axis=1)
        weg = np.maximum(bogen, gerade)
        anzahl = np.maximum(1, np.ceil(weg / TEILSCHRITT)).astype(np.int64)
        summe = np.cumsum(anzahl)
        start = 0
        while start < len(von):
            ziel = summe[start] - anzahl[start] + TEILSCHRITTE_JE_BLOCK
            ende = max(int(np.searchsorted(summe, ziel, "right")), start + 1)
            self._teilschritte(von[start:ende], nach[start:ende], anzahl[start:ende], fraeser)
            start = ende

    def _teilschritte(self, von, nach, anzahl, fraeser):
        """fahre_stuecke() für einen Block: die Stücke in `anzahl` Teilschritte zerlegt."""
        stueck = np.repeat(np.arange(len(von)), anzahl)
        vorher = np.repeat(np.cumsum(anzahl) - anzahl, anzahl)
        t = ((np.arange(len(stueck)) - vorher + 1) / anzahl[stueck])[:, None]
        punkte = von[stueck] + t * (nach[stueck] - von[stueck])
        self.schnitte(punkte[:, 0], punkte[:, 1], punkte[:, 2], fraeser, punkte[:, 3])

    def schnitt(self, a_t, r_t, phi_t_grad, fraeser):
        """Nimmt weg, was der Fräser mit der Spitze bei (a_t, r_t, φ_t) trifft."""
        self.schnitte([a_t], [r_t], [phi_t_grad], fraeser)

    def schnitte(self, a_t, r_t, phi_t_grad, fraeser, q_t=None):
        """Wie schnitt(), an vielen Stellen auf einmal (Folgen gleicher Länge). `q_t`: der
        Versatz der Werkzeugachse quer zum Strahl (mm, vierachs_bahn.Punkt.q); ohne 0."""
        form = fraeser if isinstance(fraeser, ff.Form) else None
        radius = form.radius if form is not None else float(fraeser)
        a_t = np.asarray(a_t, dtype=float)
        r_t = np.asarray(r_t, dtype=float)
        phi_t = np.radians(np.asarray(phi_t_grad, dtype=float))
        q_t = np.zeros(len(a_t)) if q_t is None else np.asarray(q_t, dtype=float)
        drin = r_t < self.radius  # darüber trifft er nichts
        if radius <= 0 or not drin.any():
            return
        a_t, r_t, phi_t, q_t = a_t[drin], np.maximum(r_t[drin], 1e-6), phi_t[drin], q_t[drin]
        # Weiter weg trifft kein Strahl den Fräser: von q − R bis q + R quer.
        von_winkel = np.arctan((q_t - radius) / r_t)
        bis_winkel = np.arctan((q_t + radius) / r_t)
        zeilen = int(math.ceil(2 * radius / self._schritt_a)) + 2
        spalten = int(math.ceil(float((bis_winkel - von_winkel).max()) / self._schritt_phi)) + 3
        je = max(1, ZELLEN_JE_BLOCK // (zeilen * spalten))
        for von in range(0, len(a_t), je):
            stellen = slice(von, von + je)
            self._block(
                a_t[stellen],
                r_t[stellen],
                phi_t[stellen],
                q_t[stellen],
                von_winkel[stellen],
                radius,
                form,
                zeilen,
                spalten,
            )

    def _block(self, a_t, r_t, phi_t, q_t, von_winkel, radius, form, zeilen, spalten):
        """schnitte() für einen Block von Stellen: je Stelle `zeilen` × `spalten` Zellen um
        ihre Spitze, in denen der Fräser liegen kann."""
        erste_zeile = np.searchsorted(self.a, a_t - radius, "left")
        zeile = erste_zeile[:, None] + np.arange(zeilen)[None, :]
        zeile_da = zeile < len(self.a)
        zeile = np.minimum(zeile, len(self.a) - 1)
        d = self.a[zeile] - a_t[:, None]  # längs von der Spitze
        zeile_da &= np.abs(d) <= radius
        schritt = self._schritt_phi
        erste_spalte = np.floor((phi_t + von_winkel) / schritt).astype(np.int64)
        spalte = erste_spalte[:, None] + np.arange(spalten)[None, :]
        delta = spalte * schritt - phi_t[:, None]  # zur Werkzeugachse
        spalte_da = np.abs(delta) < math.pi / 2 - 1e-9
        zelle = zeile[:, :, None] * len(self.phi) + (spalte % len(self.phi))[:, None, :]
        gueltig = zeile_da[:, :, None] & spalte_da[:, None, :]
        alle = self.r.reshape(-1)
        if form is None or form.eben:
            # Wo der Strahl die Ebene der Spitze trifft, quer von der Werkzeugachse gemessen.
            quer = np.abs(r_t[:, None] * np.tan(delta) - q_t[:, None])
            seitlich = np.sqrt(np.maximum(radius * radius - d * d, 0.0))
            trifft = quer[:, None, :] <= seitlich[:, :, None]
            bis_hier = np.where(trifft, (r_t[:, None] / np.cos(delta))[:, None, :], np.inf)
        else:
            bis_hier = _stirn(form, r_t, d, delta, gueltig, alle[zelle], q_t)
        da = gueltig & np.isfinite(bis_hier)
        if da.any():  # eine Zelle kann mehrmals vorkommen – at() nimmt das kleinste
            np.minimum.at(alle, zelle[da], bis_hier[da])


def _stirn(form, r_t, d, delta, gueltig, steht, q_t=None):
    """Wo die Strahlen die Stirn des Fräsers (Form) mit der Spitze auf r_t treffen – ihr
    Abstand von der Achse, (Stellen, Zeilen, Spalten); inf, wo keiner trifft oder er nichts
    wegnimmt. `d`: je Stelle und Zeile längs von der Spitze, `delta`: je Stelle und Spalte
    der Winkel zur Werkzeugachse (rad); `gueltig`: die Zellen, die zählen; `steht`: bis wohin
    dort noch Material steht; `q_t`: je Stelle der Versatz der Werkzeugachse quer (mm)."""
    q_t = np.zeros(len(r_t)) if q_t is None else q_t
    cos = np.cos(delta)[:, None, :]
    if form.nur_kugel:  # der Strahl trifft die untere Hälfte der Kugel – geschlossen
        sin = np.sin(delta)[:, None, :]
        mitte = r_t[:, None, None] + form.radius  # die Mitte: so hoch, um q quer versetzt
        q = q_t[:, None, None]
        entlang = mitte * cos + q * sin  # die Mitte, auf den Strahl projiziert
        quer = mitte * sin - q * cos  # ihr Abstand vom Strahl
        innen = form.radius**2 - (d * d)[:, :, None] - quer * quer
        return np.where(innen >= 0, entlang - np.sqrt(np.maximum(innen, 0.0)), np.inf)
    # Sonst gesucht, über den Abstand ℓ von der Werkzeugachse, an dem der Strahl die Stirn
    # trifft: dort ist ℓ = F(ℓ) = √(d² + ((r_t + z(ℓ)) · tan Δ)²), davor F(ℓ) > ℓ. Die Suche
    # kommt von unten heran – bei gewölbter Stirn mit Newton (g = F − ℓ ist dann konvex: kein
    # Schritt schießt über die erste Lösung), sonst Schritt für Schritt ℓ ← F(ℓ). Jeder Schritt
    # gibt eine Stelle, vor der der Strahl die Stirn sicher nicht trifft; liegt sie schon über
    # dem, was steht, nimmt der Fräser dort nichts weg. Die erste ist die Ebene der Spitze.
    groesse = steht.shape
    ergebnis = np.full(steht.size, np.inf)
    offen = np.flatnonzero((gueltig & (r_t[:, None, None] / cos < steht)).ravel())
    if not offen.size:
        return ergebnis.reshape(groesse)
    d2 = np.broadcast_to((d * d)[:, :, None], groesse).ravel()[offen]
    tan = np.broadcast_to(np.tan(delta)[:, None, :], groesse).ravel()[offen]
    q = np.broadcast_to(q_t[:, None, None], groesse).ravel()[offen]
    unten = np.broadcast_to(r_t[:, None, None], groesse).ravel()[offen]
    cos = np.broadcast_to(cos, groesse).ravel()[offen]
    steht = steht.ravel()[offen]
    quer = np.sqrt(d2 + (unten * tan - q) ** 2)
    noch = np.arange(offen.size)
    with np.errstate(invalid="ignore", divide="ignore"):
        for _ in range(SUCHSCHRITTE):
            ell = quer[noch]
            z, steigung = _hoehe(form, ell)
            hoch = unten[noch] + z
            seitlich = hoch * tan[noch] - q[noch]  # quer von der Werkzeugachse
            weiter = np.sqrt(d2[noch] + seitlich * seitlich)  # F(ℓ)
            rho = hoch / cos[noch]
            schneidet = rho < steht[noch]
            g = weiter - ell
            fertig = schneidet & (g <= 1e-9)
            ergebnis[offen[noch[fertig]]] = rho[fertig]
            if form.konvex:
                faellt = 1.0 - seitlich * tan[noch] * steigung / weiter  # −g′
                neu = ell + g / np.where(faellt > 1e-12, faellt, 1.0)
                trifft = faellt > 1e-12  # sonst steigt g: Der Strahl verfehlt die Stirn
            else:
                neu, trifft = weiter, True
            quer[noch] = neu
            noch = noch[schneidet & ~fertig & trifft & (neu <= form.radius)]
            if not noch.size:
                break
    # Noch nicht angekommen: dort nimmt dieser Schritt nichts weg – die Nachbarn tun es.
    return ergebnis.reshape(groesse)


def _mit_versatz(punkte):
    """Punkte (n, 3) oder (n, 4) als (n, 4): a, r, φ, Versatz quer (ohne: 0)."""
    punkte = np.asarray(punkte, dtype=float)
    if punkte.size == 0:
        return np.zeros((0, 4))
    punkte = punkte.reshape(len(punkte), -1)
    if punkte.shape[1] == 3:
        punkte = np.concatenate([punkte, np.zeros((len(punkte), 1))], axis=1)
    return punkte


@lru_cache(maxsize=32)
def _profil(form):
    """Die Stirn als Tabelle (ℓ, z), gleichmäßig in u = 1 − √(1 − ℓ/R): Zum Rand hin, wo sie
    steil wird, liegen die Punkte dichter."""
    u = np.linspace(0.0, 1.0, TABELLE + 1)
    ell = form.radius * (1.0 - (1.0 - u) ** 2)
    return ell, form.hoehe(ell)


def _hoehe(form, quer):
    """z der Stirn im Abstand `quer` von der Werkzeugachse und die Steigung dort – aus der
    Tabelle (_profil), dazwischen gerade; inf außerhalb des Fräsers."""
    ell, tabelle = _profil(form)
    stelle = (1.0 - np.sqrt(np.maximum(1.0 - quer / form.radius, 0.0))) * TABELLE
    links = np.minimum(stelle.astype(np.int64), TABELLE - 1)
    breite = ell[links + 1] - ell[links]
    steigung = (tabelle[links + 1] - tabelle[links]) / breite
    anteil = np.clip(quer - ell[links], 0.0, breite)
    z = tabelle[links] + anteil * steigung
    return np.where(quer <= form.radius, z, np.inf), steigung


@dataclass
class Vergleich:
    """Was nach dem Abtragen auf dem fertigen Teil bleibt (vergleiche())."""

    rest: np.ndarray  # (n_a, n_phi) mm über dem Teil; nan, wo kein Teil ist
    farbe: np.ndarray  # (n_a, n_phi) OHNE_TEIL, GRUEN, GELB, ROT oder BLAU
    kleinster: float  # mm – so wenig bleibt (negativ: im Teil)
    groesster: float  # mm – so viel bleibt höchstens (auf den gewählten Flächen)
    nur_gewaehlte: bool = False  # nur auf den gewählten Flächen verglichen (V4)
    # ((von, bis), …) mm längs, wo das Teil nicht rund um die Achse liegt und nicht verglichen
    # wird (vergleiche()) – leer: überall verglichen.
    ohne_vergleich: tuple = ()


def teilradien(netz, laengs, radial, stange, radius=SCHRITT_A / 2):
    """Die Radien des fertigen Teils im Raster der Stange – −inf, wo es keins gibt, negativ, wo
    es nur hinter der Achse liegt. Die Scheibe einer halben Rasterweite fasst, was zwischen den
    Strahlen liegt; mit `radius` GENAU liest es das Teil auf den Strahlen."""
    return vh.schaftfraeser(netz, laengs, radial, radius, stange.a, stange.phi).r


def vergleiche(stange, teil, aufmass, genau=None, nur=None, erlaubt=None):
    """Das Restmaterial gegen das fertige Teil (`teil`: teilradien()), je Zelle eingefärbt;
    `aufmass`: das Aufmaß, das stehen bleiben soll (mm). `genau`: das Teil auf den Strahlen
    (teilradien() mit GENAU) – nur was dort fehlt, ist blau. `nur`: (n_a, n_phi) die Zellen
    der gewählten Flächen – nur sie bekommen Grün, Gelb oder Rot; Blau gilt überall.
    `erlaubt`: (n_a, n_phi) mm, so tief darf es je Zelle ins Teil gehen, ohne blau zu werden –
    die Fase von „Rundum entgraten“ (Abtrag.fasen).

    Wo an einer Stelle manche Strahlen aus der Achse das Teil vor sich haben und andere nicht
    (sie sehen es nur hinter der Achse oder gar nicht), liegt es nicht rund um die Achse
    (Manuels Testteil hinten, P-2026-09-30-44) – dort vergleicht es gar nicht
    (Vergleich.ohne_vergleich): Die Stange kennt je Strahl nur einen Radius. Kommt der Fräser
    dort nah an die Achse, nimmt er auf einem Strahl weg, was zwischen Achse und Teil liegt,
    und für die Stange sähe es aus, als fehlte das Teil dahinter. Ein Rohr hat jeder Strahl
    vor sich – dort kommt kein Fräser an die Achse, es wird verglichen."""
    with np.errstate(invalid="ignore"):
        da = teil > 0  # das Teil vor der Achse
    halb = da.any(axis=1) & ~da.all(axis=1)
    da = da & ~halb[:, None]
    genau = teil if genau is None else genau
    tief = np.where(da & np.isfinite(genau), stange.r - genau, np.nan)
    if nur is not None:
        da = da & nur
    rest = np.where(da, stange.r - teil, np.nan)
    farbe = np.full(stange.r.shape, OHNE_TEIL, dtype=np.int8)
    farbe[da & (rest <= aufmass + GRUEN_BIS)] = GRUEN
    farbe[da & (rest > aufmass + GRUEN_BIS)] = GELB
    farbe[da & (rest >= aufmass + ROT_AB)] = ROT
    # Wo sich das Teil von einer Zelle zur nächsten stark ändert – an einer scharfen Kante, an
    # den Enden –, weiß das Raster nicht genau, wo es liegt: Dort ist erst blau, was tiefer
    # liegt als die halbe Änderung zum Nachbarn (Manuels Testteil: 0,11 mm an der Kante, 0,05
    # mm auf der Stirnebene – am Körper nachgemessen kein Eindringen, P-2026-09-30-44).
    schwelle = BLAU_AB + 0.5 * _spruenge(genau)
    if erlaubt is not None:
        schwelle = schwelle + erlaubt
    with np.errstate(invalid="ignore"):
        blau = tief < -schwelle
        farbe[blau] = BLAU
        tief = np.where(blau, tief, np.maximum(tief, -BLAU_AB))
    kleinster = float(np.nanmin(tief)) if np.isfinite(tief).any() else 0.0
    groesster = float(np.nanmax(rest)) if da.any() else 0.0
    return Vergleich(rest, farbe, kleinster, groesster, nur is not None, _bereiche(stange, halb))


def _bereiche(stange, zeilen):
    """Die zusammenhängenden Stücke der Zeilen `zeilen` ((n_a,) bool) als ((von, bis), …) mm
    längs – bis an den Rand ihrer Zellen, höchstens bis an die Enden der Stange."""
    stuecke = []
    for i in np.flatnonzero(zeilen):
        if stuecke and stuecke[-1][1] == i - 1:
            stuecke[-1][1] = i
        else:
            stuecke.append([i, i])
    halb = stange._schritt_a / 2
    a = stange.a
    return tuple(
        (float(max(a[v] - halb, a[0])), float(min(a[b] + halb, a[-1]))) for v, b in stuecke
    )


def _spruenge(teil):
    """(n_a, n_phi): je Zelle die größte Änderung des Teils zu einer Nachbarzelle (längs und
    rundum) – unendlich, wo ein Nachbar kein Teil hat."""
    with np.errstate(invalid="ignore"):
        sprung = np.zeros(teil.shape)
        for nachbar in (np.roll(teil, 1, axis=1), np.roll(teil, -1, axis=1)):
            sprung = np.maximum(sprung, np.abs(nachbar - teil))
        oben = np.vstack([teil[1:], np.full((1, teil.shape[1]), -np.inf)])
        unten = np.vstack([np.full((1, teil.shape[1]), -np.inf), teil[:-1]])
        for nachbar in (oben, unten):
            sprung = np.maximum(sprung, np.abs(nachbar - teil))
    return np.where(np.isfinite(sprung), sprung, np.inf)


class Abtrag:
    """Die Stange eines 4-Achs-Jobs beim Abfahren (abfahren.Abfahrt): was bis zu einer
    Station weg ist. fuer() baut es – nur für Jobs mit runder Stange und „Rundum
    schruppen“ oder „Rundum schlichten“."""

    def __init__(
        self, stange, laengs, radial, stationen, fraeser, aufmass, formen, flaechen=None, fasen=None
    ):
        self.stange = stange
        self.laengs, self.radial = laengs, radial
        # je Station (a, r, φ in Grad, fortlaufend), Operation, gültig – oder dazwischen der
        # Versatz quer q (Plan indexiert).
        if len(stationen) == 6:
            self.a, self.r, self.phi, q, self.operation, self.gueltig = stationen
        else:
            self.a, self.r, self.phi, self.operation, self.gueltig = stationen
            q = np.zeros(len(self.a))
        self._punkte = np.stack([self.a, self.r, self.phi, q], axis=1)
        self.fraeser = fraeser  # je Operation (Nummer in der Abfahrt) Form oder Radius
        self.aufmass = aufmass
        self._formen = formen
        self._teil = None  # teilradien() mit der halben Rasterweite und GENAU, einmal gerechnet
        # Die Nummern der gewählten Flächen (V4) – None: alle; dazu ihre Zellen, einmal gerechnet.
        self.flaechen = flaechen
        self._nur = None
        # „Rundum entgraten“ (V4d): je Operation (Nummer), wie tief ihre Fase ins Teil geht –
        # so tief darf es dort sein, ohne blau zu werden (die Zellen, die sie trifft).
        self.fasen = dict(fasen or {})
        self._erlaubt = np.zeros(stange.r.shape)
        self.bis = 0  # abgetragen bis vor diese Station

    def bis_station(self, index):
        """Trägt ab bis einschließlich Station `index`; zurück rechnet es von vorn."""
        index = min(index, len(self.a) - 1)
        if index + 1 < self.bis:
            self.stange.zuruecksetzen()
            self._erlaubt.fill(0.0)
            self.bis = 0
        k = np.arange(max(self.bis, 1), index + 1)
        fahren = (
            self.gueltig[k - 1] & self.gueltig[k] & (self.operation[k - 1] == self.operation[k])
        )
        k = k[fahren]
        for nummer, fraeser in self.fraeser.items():
            stuecke = k[self.operation[k] == nummer]
            if nummer in self.fasen and len(stuecke):
                vorher = self.stange.r.copy()
                self.stange.fahre_stuecke(self._punkte[stuecke - 1], self._punkte[stuecke], fraeser)
                getroffen = self.stange.r < vorher
                np.maximum(
                    self._erlaubt, np.where(getroffen, self.fasen[nummer], 0.0), out=self._erlaubt
                )
                continue
            self.stange.fahre_stuecke(self._punkte[stuecke - 1], self._punkte[stuecke], fraeser)
        self.bis = max(self.bis, index + 1)

    def vergleich(self):
        """Das Restmaterial gegen das fertige Teil (Vergleich) – die Radien des Teils und, mit
        gewählten Flächen, deren Zellen rechnet es beim ersten Mal."""
        if self._teil is None:
            import Part

            form = self._formen[0] if len(self._formen) == 1 else Part.makeCompound(self._formen)
            netz = vh.vernetze(form)
            self._teil = (
                teilradien(netz, self.laengs, self.radial, self.stange),
                teilradien(netz, self.laengs, self.radial, self.stange, GENAU),
            )
            if self.flaechen:
                from . import vierachs_flaechen as vf

                sicht = vf.sicht(
                    vf.vernetze(form), self.laengs, self.radial, self.stange.a, self.stange.phi
                )
                self._nur = np.isin(sicht.flaeche, sorted(self.flaechen))
        return vergleiche(
            self.stange,
            self._teil[0],
            self.aufmass,
            self._teil[1],
            self._nur,
            self._erlaubt if self.fasen else None,
        )


def fuer(abfahrt, job, am_werkstueck):
    """Das Abtrag für diesen Job – oder None, wenn das Rohteil keine runde Stange ist oder
    keine Operation „Rundum schruppen“ oder „Rundum schlichten“ darin läuft. `am_werkstueck`:
    je Station die Spitze am gedrehten Teil (abfahren.Abfahrt.am_werkstueck). Jede Operation
    trägt mit der Form ihres Fräsers ab; verglichen wird mit dem Aufmaß der letzten."""
    import FreeCAD

    from .vierachs_operation import ist_rundum

    rohteil = getattr(job, "Stock", None)
    if rohteil is None or not hasattr(rohteil, "Radius") or not hasattr(rohteil, "Height"):
        return None
    ops = {o.Label: o for o in getattr(job.Operations, "Group", []) if ist_rundum(o)}
    rundum = [
        k
        for k, op in enumerate(abfahrt.operationen)
        if op.art in operationsarten_rundum() and op.name in ops
    ]
    if not rundum or not abfahrt.stationen:
        return None
    laengs = rohteil.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    erste = ops[abfahrt.operationen[rundum[0]].name]
    radial = FreeCAD.Vector(erste.Werkzeugrichtung)
    a_hinten = rohteil.Placement.Base.dot(laengs)
    stange = Stange(float(rohteil.Radius), a_hinten, a_hinten + float(rohteil.Height))
    l_, u_, v_ = vh.rahmen(laengs, radial)
    punkte = np.array(am_werkstueck, dtype=float).reshape(-1, 3)
    a = punkte @ l_
    # Die Werkzeugachse zeigt aus der Richtung, auf der die Rundachse steht (im Programm
    # −Drehsinn · φ); die Spitze liegt auf ihr (r) oder quer daneben (q, Plan indexiert).
    buchstabe, drehsinn = str(erste.Rundachse), int(erste.Drehsinn) or 1
    phi = -drehsinn * np.array(
        [float(s.rund.get(buchstabe, 0.0)) for s in abfahrt.stationen], dtype=float
    )
    rad = np.radians(phi)
    u_phi = u_[None, :] * np.cos(rad)[:, None] + v_[None, :] * np.sin(rad)[:, None]
    v_phi = v_[None, :] * np.cos(rad)[:, None] - u_[None, :] * np.sin(rad)[:, None]
    r = np.einsum("ij,ij->i", punkte, u_phi)
    q = np.einsum("ij,ij->i", punkte, v_phi)
    operation = np.array([s.operation for s in abfahrt.stationen])
    fraeser = {k: _fraeser(abfahrt.operationen[k].tc) for k in rundum}
    gueltig = np.array(
        [s.stellungen is not None and s.operation in fraeser for s in abfahrt.stationen]
    )
    # Verglichen wird mit dem Aufmaß der letzten Operation, die eins hat („Rundum entgraten“
    # hat keins: es schneidet in die Kanten – so tief darf es dort gehen, Abtrag.fasen).
    from . import vierachs_entgratbahn as ve
    from .vierachs_entgraten import ist_entgraten

    aufmass = next(
        (
            float(ops[abfahrt.operationen[k].name].Aufmass)
            for k in reversed(rundum)
            if hasattr(ops[abfahrt.operationen[k].name], "Aufmass")
        ),
        0.0,
    )
    fasen = {}
    for k in rundum:
        op = ops[abfahrt.operationen[k].name]
        if ist_entgraten(op):
            breite = float(op.Breite)
            form = fraeser[k]
            fasen[k] = breite if isinstance(form, float) else ve.eindringtiefe(form, breite)
    # Haben alle Rundum-Operationen gewählte Flächen, zählt der Vergleich nur auf ihnen (V4).
    from . import vierachs_flaechen as vf
    from .vierachs_operation import flaechen as flaechen_von

    gewaehlt = [flaechen_von(ops[abfahrt.operationen[k].name]) for k in rundum]
    flaechen = set().union(*(vf.nummern(g) for g in gewaehlt)) if all(gewaehlt) else None
    formen = [
        o.Shape
        for o in getattr(job.Model, "Group", [])
        if getattr(o, "Shape", None) is not None and not o.Shape.isNull()
    ]
    if not formen:
        return None
    return Abtrag(
        stange,
        laengs,
        radial,
        (a, r, phi, q, operation, gueltig),
        fraeser,
        aufmass,
        formen,
        flaechen,
        fasen,
    )


def _fraeser(tc):
    """Der Fräser eines Controllers zum Abtragen: seine Form (fraeserform) – kennt das Addon
    sie nicht, ein Schaftfräser mit seinem Durchmesser."""
    from .vierachs_schlichten import form_des_controllers

    form = form_des_controllers(tc)
    if form is not None:
        return form
    return float(tc.Tool.Diameter.getValueAs("mm")) / 2


def operationsarten_rundum():
    """Wie job_schnittwerte.operationsart() „Rundum schruppen“, „Rundum schlichten“, „Plan
    indexiert“ und „Rundum entgraten“ nennt (die Namen ihrer Module)."""
    return ("vierachs_operation", "vierachs_schlichten", "vierachs_plan", "vierachs_entgraten")


# --- Darstellung (ohne Coin: Felder, die gui_abfahren in die Ansicht gibt) ---------------

SCHWERE = {OHNE_TEIL: 0, GRUEN: 1, GELB: 2, ROT: 3, BLAU: 4}  # was in einem Block zählt


def darstellung(stange, zeilen=2, spalten=2):
    """(Punkte, Anzahl längs, Anzahl rundum) fürs Bild: die Oberfläche der Stange im Job, je
    `zeilen` × `spalten` Zellen ein Punkt – der tiefste Radius darin; rundum geschlossen
    (der erste Winkel noch einmal am Ende)."""
    r = _bloecke(stange.r, zeilen, spalten, np.min)
    a = stange.a[: r.shape[0] * zeilen : zeilen]
    phi = stange.phi[: r.shape[1] * spalten : spalten]
    phi = np.append(phi, phi[0] + 2 * math.pi)
    r = np.concatenate([r, r[:, :1]], axis=1)
    return a, phi, r


def farben(vergleich, zeilen=2, spalten=2):
    """Die Farbe je Punkt von darstellung(): die schwerste im Block (Blau vor Rot …)."""
    schwere = np.vectorize(SCHWERE.get)(vergleich.farbe)
    block = _bloecke(schwere, zeilen, spalten, np.max)
    zurueck = {v: k for k, v in SCHWERE.items()}
    farbe = np.vectorize(zurueck.get)(block)
    return np.concatenate([farbe, farbe[:, :1]], axis=1)


def _bloecke(werte, zeilen, spalten, wie):
    n_a = werte.shape[0] // zeilen
    n_phi = werte.shape[1] // spalten
    beschnitten = werte[: n_a * zeilen, : n_phi * spalten]
    return wie(beschnitten.reshape(n_a, zeilen, n_phi, spalten), axis=(1, 3))
