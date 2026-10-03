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

Das Rohteil im Quader (W-006 S3d, 2,5D): dieselbe Idee von oben – der Quader als Höhen über
(x, y): h[i, j], wie hoch das Material an der Stelle (x_i, y_j) noch steht (SCHRITT_XY im
Raster). Ein Werkzeug, das senkrecht von oben kommt (die Werkzeugachse zeigt am Werkstück nach
+z), nimmt weg, was in ihm liegt: Steht seine Spitze bei (x_t, y_t, z_t), bleibt in der Zelle
im Abstand ℓ von der Werkzeugachse höchstens z_t + z(ℓ) stehen (dieselbe Stirn z(ℓ) wie
rundum). Jede Operation des Jobs trägt ab – auch FreeCADs eigene –, so weit das Addon die
Form ihres Fräsers kennt, sonst als Schaftfräser mit seinem Durchmesser. Der Vergleich am
Ende: die Oberseite des Teils im selben Raster (hoehenfeld.hoehen – das höchste Dreieck über
der Zelle), je Zelle der Rest darüber, die Farben und die gewählten Flächen wie rundum. Was
unter einem Überhang liegt, kennt ein Höhenfeld nicht – 2,5D von oben.

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
SCHRITT_XY = 0.5  # mm – Raster des Quaders (2,5D)
EILGANG_SCHWELLE = 0.1  # mm – so viel Material darf ein Eilgang (im Raster) streifen
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
FASE_SPIEL = 0.05  # mm – so viel tiefer als die Fase darf „Entgraten“ gehen (Raster)
RING_SPIEL = 0.05  # mm – so viel weiter als die Spitze des Gewindefräsers zählt sein Ring
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
    return vh.schaftfraeser(netz, laengs, radial, radius, stange.a, stange.phi, nur_vorne=True).r


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


def _spruenge(teil, rundum=True):
    """(n_a, n_phi): je Zelle die größte Änderung des Teils zu einer Nachbarzelle (längs und
    rundum) – unendlich, wo ein Nachbar kein Teil hat. `rundum`: die zweite Achse läuft um
    (φ); ohne (der Quader) endet sie wie die erste."""
    with np.errstate(invalid="ignore"):
        sprung = np.zeros(teil.shape)
        if rundum:
            seitlich = (np.roll(teil, 1, axis=1), np.roll(teil, -1, axis=1))
        else:
            rand = np.full((teil.shape[0], 1), -np.inf)
            seitlich = (np.hstack([teil[:, 1:], rand]), np.hstack([rand, teil[:, :-1]]))
        oben = np.vstack([teil[1:], np.full((1, teil.shape[1]), -np.inf)])
        unten = np.vstack([np.full((1, teil.shape[1]), -np.inf), teil[:-1]])
        for nachbar in (*seitlich, oben, unten):
            sprung = np.maximum(sprung, np.abs(nachbar - teil))
    return np.where(np.isfinite(sprung), sprung, np.inf)


class Abtrag:
    """Die Stange eines 4-Achs-Jobs beim Abfahren (abfahren.Abfahrt): was bis zu einer
    Station weg ist. fuer() baut es – nur für Jobs mit runder Stange und „Rundum
    schruppen“ oder „Rundum schlichten“."""

    def __init__(
        self,
        stange,
        laengs,
        radial,
        stationen,
        fraeser,
        aufmass,
        formen,
        flaechen=None,
        fasen=None,
        boeden=None,
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
        # „Plan indexiert“: [(vierachs_planbahn.Ebene, Part.Face)] – die Gründe, bis auf die der
        # Fräser je Strahl darf; dazu ihre Radien je Zelle, einmal gerechnet (_boden_radien).
        self.boeden = list(boeden or [])
        self._boden = None
        self.bis = 0  # abgetragen bis vor diese Station

    def letzte(self):
        """Der Index der letzten Station."""
        return len(self.a) - 1

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
        erlaubt = self._erlaubt if self.fasen else None
        if self.boeden:
            # Die Stange kennt je Strahl nur einen Radius: Neben den Wänden einer Nut läuft der
            # Strahl schräg durch die Wand, dann durch die Nut auf ihren Grund – weg ist auf ihm
            # alles bis zum Grund, und das ist richtig. Bis dorthin ist es nicht blau.
            if self._boden is None:
                self._boden = self._boden_radien()
            with np.errstate(invalid="ignore"):
                mehr = np.where(
                    np.isfinite(self._boden), np.maximum(self._teil[1] - self._boden, 0.0), 0.0
                )
            erlaubt = mehr if erlaubt is None else np.maximum(erlaubt, mehr)
        return vergleiche(
            self.stange,
            self._teil[0],
            self.aufmass,
            self._teil[1],
            self._nur,
            erlaubt,
        )

    def _boden_radien(self):
        """boden_radien() für diese Stange und Gründe."""
        return boden_radien(self.stange, self.laengs, self.radial, self.boeden)


def boden_radien(stange, laengs, radial, boeden):
    """(n_a, n_phi): je Zelle der Stange, wo der Strahl einen der Gründe `boeden`
    ([(vierachs_planbahn.Ebene, Part.Face)], „Plan indexiert“) innerhalb der Fläche trifft,
    sein Abstand von der Achse; sonst nan. Statt der Fläche auch die Spitze einer gebohrten
    Sackbohrung (vierachs_planbahn.Kegelgrund)."""
    import FreeCAD

    from . import vierachs_planbahn as vp

    radien = np.full(stange.r.shape, np.nan)
    l_, u_, v_ = vh.rahmen(laengs, radial)
    for ebene, flaeche in boeden:
        phi0 = math.radians(ebene.phi)
        n = u_ * math.cos(phi0) + v_ * math.sin(phi0)
        quer = np.cross(l_, n)
        delta = np.angle(np.exp(1j * (stange.phi - phi0)))
        if isinstance(flaeche, vp.Kegelgrund):
            _kegel_radien(radien, stange, flaeche, delta)
            continue
        zeilen = np.flatnonzero((stange.a >= ebene.a_von - 1e-6) & (stange.a <= ebene.a_bis + 1e-6))
        for i in zeilen:
            # Schräg zur Stange (P-2026-10-03-09) liegt die Fläche je Stelle anders hoch.
            tiefe = float(ebene.hoehe(stange.a[i]))
            with np.errstate(invalid="ignore"):
                q = tiefe * np.tan(delta)
            spalten = np.flatnonzero(
                (np.abs(delta) < math.radians(80))
                & (q >= ebene.q_von - 1e-6)
                & (q <= ebene.q_bis + 1e-6)
            )
            for j in spalten:
                p = l_ * stange.a[i] + n * tiefe + quer * q[j]
                if flaeche.isInside(FreeCAD.Vector(*(float(c) for c in p)), 1e-3, True):
                    r = tiefe / math.cos(float(delta[j]))
                    radien[i, j] = r if np.isnan(radien[i, j]) else min(radien[i, j], r)
    return radien


def _kegel_radien(radien, stange, kegel, delta):
    """Trägt in `radien` ein, wo der Strahl je Zelle die Spitze `kegel`
    (vierachs_planbahn.Kegelgrund) trifft: r mit r·cos δ = Spitze + Steigung · Abstand von der
    Achse der Bohrung – halbiert, je Zelle; Strahlen, die daneben gehen, bleiben."""
    zeilen = np.flatnonzero(np.abs(stange.a - kegel.a) <= kegel.radius + 1e-6)
    spalten = np.flatnonzero(np.abs(delta) < math.radians(80))
    if not len(zeilen) or not len(spalten):
        return
    a = (stange.a[zeilen] - kegel.a)[:, None]
    c = np.cos(delta[spalten])[None, :]
    s = np.sin(delta[spalten])[None, :]
    steigung = kegel.laenge / kegel.radius

    def f(r):
        return r * c - kegel.spitze - steigung * np.hypot(a, r * s - kegel.q)

    unten = np.zeros((len(zeilen), len(spalten)))
    oben = np.broadcast_to((max(kegel.spitze + kegel.laenge, 0.0) + 1.0) / c, unten.shape).copy()
    geht = (f(unten) <= 0) & (f(oben) >= 0)
    for _ in range(40):
        mitte = (unten + oben) / 2
        drueber = f(mitte) >= 0
        oben = np.where(drueber, mitte, oben)
        unten = np.where(drueber, unten, mitte)
    r = (unten + oben) / 2
    geht &= np.hypot(a, r * s - kegel.q) <= kegel.radius + 1e-6
    for i, j in zip(*np.nonzero(geht), strict=True):
        alt = radien[zeilen[i], spalten[j]]
        radien[zeilen[i], spalten[j]] = r[i, j] if np.isnan(alt) else min(alt, r[i, j])


def fuer(abfahrt, job, am_werkstueck):
    """Der Abtrag für diesen Job: die Stange (fuer_rundum) oder der Quader (fuer_quader) –
    oder None, wenn keins von beiden geht. `am_werkstueck`: je Station die Spitze am gedrehten
    Teil (abfahren.Abfahrt.am_werkstueck)."""
    abtrag = fuer_rundum(abfahrt, job, am_werkstueck)
    if abtrag is None:
        abtrag = fuer_quader(abfahrt, job, am_werkstueck)
    return abtrag


def fuer_rundum(abfahrt, job, am_werkstueck):
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
        _boeden(job, [ops[abfahrt.operationen[k].name] for k in rundum], laengs, radial),
    )


def _boeden(job, operationen, laengs, radial):
    """[(vierachs_planbahn.Ebene, Part.Face)] – die Flächen der „Plan indexiert“ unter
    `operationen`: ihr Grund, bis auf den der Fräser je Strahl darf (Abtrag.vergleich)."""
    from . import vierachs_planbahn as vp
    from .vierachs_operation import flaechen as flaechen_von
    from .vierachs_plan import bohrer_des_controllers, ist_plan
    from .vierachs_schlichten import _teil

    plaene = [op for op in operationen if ist_plan(op)]
    if not plaene:
        return []
    try:
        form = _teil(getattr(job.Model, "Group", []))
    except ValueError:
        return []
    l_ = tuple(float(c) for c in laengs)
    u_ = tuple(float(c) for c in radial)
    ergebnis = []
    for op in plaene:
        bohrer = bohrer_des_controllers(getattr(op, "ToolController", None))
        if bohrer is None:  # ein Bohrer fräst keine Fläche
            for ebene in vp.ebenen(form, l_, u_, flaechen_von(op)):
                ergebnis.append((ebene, form.Faces[int(ebene.name[4:]) - 1]))
        paare = vp.bohrungen(form, l_, u_, flaechen_von(op))
        namen = [e.name for e, _b in paare]
        for ebene, bohrung in paare:
            durch = namen.count(ebene.name) > 1
            ergebnis.append(vp.boden_der_bohrung(l_, u_, ebene, bohrung, bohrer, durch))
    return ergebnis


def _fraeser(tc):
    """Der Fräser eines Controllers zum Abtragen: seine Form (fraeserform) – kennt das Addon
    sie nicht, ein Schaftfräser mit seinem Durchmesser; ein Gewindebohrer mit dem Kernloch
    (Ø − Steigung): Das Gewinde steht nicht im Modell, die Bohrung hat dort ihr Kernloch – mit
    dem Nenn-Ø wäre jedes Gewinde „im Teil“."""
    from .vierachs_schlichten import form_des_controllers

    form = form_des_controllers(tc)
    if form is not None:
        return form
    kegel = _kegel(tc)
    if kegel is not None:
        return kegel
    durchmesser = float(tc.Tool.Diameter.getValueAs("mm"))
    steigung = float(getattr(tc.Tool, "Pitch", 0.0) or 0.0)
    if 0 < steigung < durchmesser:
        return (durchmesser - steigung) / 2
    return durchmesser / 2


def _kegel(tc):
    """Die Form eines Bohrers, NC-Anbohrers oder Kegelsenkers – ein Kegel mit seinem
    Spitzenwinkel (und der Spitze des Senkers); None bei anderen Werkzeugen. Als Zylinder
    gerechnet, schnitte der Anbohrer oben einen flachen Kreis von seinem ganzen Ø ins Teil."""
    from . import werkzeuge as wz
    from .werkzeuge_aus_cam import vom_controller

    werkzeug = vom_controller(tc)
    vorgabe = {wz.BOHRER: 118.0, wz.NC_ANBOHRER: 90.0, wz.KEGELSENKER: 90.0}
    if werkzeug is None or werkzeug.art not in vorgabe or werkzeug.durchmesser <= 0:
        return None
    r = werkzeug.durchmesser / 2
    winkel = werkzeug.spitzenwinkel if 0 < (werkzeug.spitzenwinkel or 0) < 180 else 0.0
    winkel = winkel or vorgabe[werkzeug.art]
    spitze = min(max(werkzeug.spitzen_d or 0.0, 0.0), 1.8 * r)
    if werkzeug.art != wz.KEGELSENKER:
        spitze = 0.0
    return ff.kegel(spitze / 2, r, (r - spitze / 2) / math.tan(math.radians(winkel / 2)))


def _zentrier_fase(op):
    """So tief (mm) geht die Fase, die „Zentrieren“ an der Bohrung lässt (ihre Eigenschaft
    „Fase“, senken.FASE breit) – 0 bei anderen Operationen. Das Modell hat dort eine scharfe
    Kante. Der NC-Anbohrer kommt aus FreeCAD als Bohrer zurück; der Winkel ist seiner."""
    from .werkzeuge_aus_cam import vom_controller

    fase = float(getattr(op, "Fase", 0.0) or 0.0)
    if fase <= 0:
        return 0.0
    werkzeug = vom_controller(getattr(op, "ToolController", None))
    winkel = getattr(werkzeug, "spitzenwinkel", 0.0) or 0.0
    winkel = winkel if 0 < winkel < 180 else 90.0
    return fase / math.tan(math.radians(winkel / 2))


def operationsarten_rundum():
    """Wie job_schnittwerte.operationsart() „Rundum schruppen“, „Rundum schlichten“, „Plan
    indexiert“ und „Rundum entgraten“ nennt (die Namen ihrer Module)."""
    return ("vierachs_operation", "vierachs_schlichten", "vierachs_plan", "vierachs_entgraten")


# --- Der Quader (W-006 S3d) ----------------------------------------------------------------


def _raster(von, bis, schritt):
    anzahl = max(2, int(math.ceil((bis - von) / schritt - 1e-9)) + 1)
    return von + schritt * np.arange(anzahl)


class Quader:
    """Die Höhen des Materials über (x, y) – anfangs der ganze Quader (das Rohteil als Kasten
    im Job: x_von … x_bis, y_von … y_bis, z_von … z_bis)."""

    def __init__(self, x_von, x_bis, y_von, y_bis, z_von, z_bis, schritt=SCHRITT_XY):
        self.x = _raster(float(x_von), float(x_bis), schritt)
        self.y = _raster(float(y_von), float(y_bis), schritt)
        self.z_von, self.z_bis = float(z_von), float(z_bis)
        self.h = np.full((len(self.x), len(self.y)), self.z_bis)
        self._schritt = float(schritt)

    def zuruecksetzen(self):
        self.h.fill(self.z_bis)

    def fahre(self, von, nach, fraeser):
        """Der Fräser fährt von `von` nach `nach` – je (x, y, z) der Spitze im Job – und nimmt
        weg, was er dabei trifft (den Anfang nicht: der kam mit dem Stück davor). `fraeser`:
        seine Form (fraeserform.Form) oder der Radius eines Schaftfräsers."""
        self.fahre_stuecke([von], [nach], fraeser)

    def fahre_stuecke(self, von, nach, fraeser):
        """Wie fahre(), für viele Stücke auf einmal: `von` und `nach` je (n, 3). Blockweise
        wie Stange.fahre_stuecke – weg ist, was irgendein Teilschritt trifft."""
        von = np.asarray(von, dtype=float).reshape(-1, 3)
        nach = np.asarray(nach, dtype=float).reshape(-1, 3)
        if not len(von):
            return
        weg = np.linalg.norm(nach - von, axis=1)
        anzahl = np.maximum(1, np.ceil(weg / TEILSCHRITT)).astype(np.int64)
        summe = np.cumsum(anzahl)
        start = 0
        while start < len(von):
            ziel = summe[start] - anzahl[start] + TEILSCHRITTE_JE_BLOCK
            ende = max(int(np.searchsorted(summe, ziel, "right")), start + 1)
            stueck = np.repeat(np.arange(start, ende), anzahl[start:ende])
            vorher = np.repeat(
                np.cumsum(anzahl[start:ende]) - anzahl[start:ende], anzahl[start:ende]
            )
            t = ((np.arange(len(stueck)) - vorher + 1) / anzahl[stueck])[:, None]
            punkte = von[stueck] + t * (nach[stueck] - von[stueck])
            self.schnitte(punkte[:, 0], punkte[:, 1], punkte[:, 2], fraeser)
            start = ende

    def schnitt(self, x_t, y_t, z_t, fraeser):
        """Nimmt weg, was der Fräser mit der Spitze bei (x_t, y_t, z_t) trifft."""
        self.schnitte([x_t], [y_t], [z_t], fraeser)

    def schnitte(self, x_t, y_t, z_t, fraeser):
        """Wie schnitt(), an vielen Stellen auf einmal (Folgen gleicher Länge): In der Zelle
        im Abstand ℓ von der Werkzeugachse bleibt höchstens z_t + z(ℓ) stehen – die Stirn des
        Fräsers (fraeserform), beim Schaftfräser z = 0."""
        x_t = np.asarray(x_t, dtype=float).ravel()
        y_t = np.asarray(y_t, dtype=float).ravel()
        z_t = np.asarray(z_t, dtype=float).ravel()
        if not len(x_t):
            return
        form = fraeser if isinstance(fraeser, ff.Form) else None
        radius = form.radius if form is not None else float(fraeser)
        if radius <= 0:
            return
        m = int(math.ceil(radius / self._schritt + 1e-9))
        breite = 2 * m + 1
        je_block = max(1, ZELLEN_JE_BLOCK // (breite * breite))
        versatz = np.arange(-m, m + 1)
        n_x, n_y = self.h.shape
        for start in range(0, len(x_t), je_block):
            xs, ys, zs = (v[start : start + je_block] for v in (x_t, y_t, z_t))
            ii = np.rint((xs - self.x[0]) / self._schritt).astype(np.int64)[:, None] + versatz
            jj = np.rint((ys - self.y[0]) / self._schritt).astype(np.int64)[:, None] + versatz
            drin_i = (ii >= 0) & (ii < n_x)
            drin_j = (jj >= 0) & (jj < n_y)
            ii = np.clip(ii, 0, n_x - 1)
            jj = np.clip(jj, 0, n_y - 1)
            dx = self.x[ii] - xs[:, None]  # (K, w)
            dy = self.y[jj] - ys[:, None]
            l2 = dx[:, :, None] ** 2 + dy[:, None, :] ** 2  # (K, w, w)
            if form is None or form.eben:
                tiefe = np.where(l2 <= radius * radius + 1e-9, zs[:, None, None], np.inf)
            else:
                z, _steigung = _hoehe(form, np.sqrt(l2))
                tiefe = zs[:, None, None] + z
            zellen_i = np.broadcast_to(ii[:, :, None], l2.shape)
            zellen_j = np.broadcast_to(jj[:, None, :], l2.shape)
            drin = drin_i[:, :, None] & drin_j[:, None, :] & np.isfinite(tiefe)
            drin &= tiefe < self.h[zellen_i, zellen_j]
            if drin.any():
                np.minimum.at(self.h, (zellen_i[drin], zellen_j[drin]), tiefe[drin])


def teilhoehen(netz, quader):
    """Die Oberseite des fertigen Teils im Raster des Quaders – −inf, wo es keins gibt
    (hoehenfeld.hoehen: das höchste Dreieck über der Zelle). Ein Knoten genau auf einer Kante
    zählt nicht (`innen`): Auf der Linie einer Wand gehört er zur Oberseite wie zum Boden – die
    Kontur führt den Fräser genau bis an die Wand, und der Vergleich meldete dort 15 mm „ins
    Teil“ (W-006 S3e). Seine Nachbarn bekommen damit die Schwelle der Außenkante (_spruenge)."""
    from . import hoehenfeld as hf

    return hf.hoehen(netz, quader.x, quader.y, innen=True)


def teilhoehen_kanten(netz, quader):
    """(teil, erlaubt) für den Vergleich im Quader: die Oberseite des Teils je Zelle – dicht an
    einer Kante (näher als zweimal die Toleranz des Netzes) die höchste Fläche dort – und je
    Zelle, wie tief es dort ins Teil darf, ohne blau zu werden: 0, nur dicht an einer Kante bis
    auf die tiefste Fläche dort (eine Wand: bis auf ihren Boden; der Rand des Teils: beliebig).
    Das Netz ist ein Vieleck in der runden Wand – der Fräser, der genau bis an den Kreis fährt,
    nimmt eine Zelle auf dem Kreis weg, die nach dem Netz noch zur Oberseite gehört: auf Manuels
    Platte „20 mm im Teil“ am Rand der Tasche. Und umgekehrt (B-008, Manuels Testteil): Eine
    Zelle, deren Mitte um ein Haar neben der Wand liegt (0,007 mm), erreicht der Fräser, der
    genau an der Wand entlangfährt, gerade nicht – „12 mm stehen geblieben“ auf einer einzigen
    Zelle. So dicht an der Kante gilt deshalb beides: stehen darf es bis zur höheren Fläche, weg
    sein bis zur tieferen. Mit `innen` allein fiel dagegen eine Zelle auf einer inneren Kante
    der Vernetzung – zwei Dreiecke derselben Fläche – durch die Fläche auf die nächste darunter
    (dort die Unterseite: „bis 51 mm stehen geblieben“ mitten auf der Oberseite;
    P-2026-10-01-27)."""
    from . import hoehenfeld as hf

    alle = hf.hoehen(netz, quader.x, quader.y)
    nah = 2.0 * max(float(getattr(netz, "toleranz", hf.TOLERANZ)), 0.005)
    tiefste = alle.copy()
    hoechste = alle.copy()
    for dx, dy in ((nah, 0.0), (-nah, 0.0), (0.0, nah), (0.0, -nah)):
        daneben = hf.hoehen(netz, quader.x + dx, quader.y + dy)
        tiefste = np.minimum(tiefste, daneben)
        hoechste = np.maximum(hoechste, daneben)
    # Neben dem Teil bleibt „kein Teil“ – was dort vom Rohteil steht, ist kein Rest.
    teil = np.where(np.isfinite(alle), hoechste, alle)
    kante = np.isfinite(teil) & (tiefste < teil - 1e-6)
    erlaubt = np.zeros(alle.shape)
    erlaubt[kante] = teil[kante] - tiefste[kante]
    return teil, erlaubt


def vergleiche_quader(quader, teil, aufmass, nur=None, erlaubt=None):
    """Das Restmaterial im Quader gegen das fertige Teil (`teil`: teilhoehen()), je Zelle
    eingefärbt – wie vergleiche(), von oben: der Rest ist h − Teil. `nur`: (n_x, n_y) die
    Zellen der gewählten Flächen; `erlaubt`: (n_x, n_y) mm, so tief darf es je Zelle ins
    Teil, ohne blau zu werden."""
    da = np.isfinite(teil)
    tief = np.where(da, quader.h - teil, np.nan)
    if nur is not None:
        da = da & nur
    rest = np.where(da, quader.h - teil, np.nan)
    farbe = np.full(quader.h.shape, OHNE_TEIL, dtype=np.int8)
    farbe[da & (rest <= aufmass + GRUEN_BIS)] = GRUEN
    farbe[da & (rest > aufmass + GRUEN_BIS)] = GELB
    farbe[da & (rest >= aufmass + ROT_AB)] = ROT
    schwelle = BLAU_AB + 0.5 * _spruenge(teil, rundum=False)
    if erlaubt is not None:
        schwelle = schwelle + erlaubt
    with np.errstate(invalid="ignore"):
        blau = tief < -schwelle
        farbe[blau] = BLAU
        tief = np.where(blau, tief, np.maximum(tief, -BLAU_AB))
    kleinster = float(np.nanmin(tief)) if np.isfinite(tief).any() else 0.0
    groesster = float(np.nanmax(rest)) if da.any() else 0.0
    return Vergleich(rest, farbe, kleinster, groesster, nur is not None, ())


class QuaderAbtrag:
    """Das Rohteil eines Jobs im Quader beim Abfahren (abfahren.Abfahrt): was bis zu einer
    Station weg ist. fuer_quader() baut es – für Jobs mit einem Kasten als Rohteil, deren
    Werkzeuge senkrecht von oben kommen."""

    def __init__(
        self,
        quader,
        punkte,
        operation,
        gueltig,
        fraeser,
        aufmass,
        formen,
        flaechen=None,
        fasen=None,
        ringe=None,
    ):
        self.quader = quader
        self.punkte = np.asarray(punkte, dtype=float).reshape(-1, 3)  # je Station die Spitze
        self.operation, self.gueltig = operation, gueltig
        self.fraeser = fraeser  # je Operation (Nummer in der Abfahrt) Form oder Radius
        self.aufmass = aufmass
        self._formen = formen
        self._teil = None  # teilhoehen_kanten(), einmal gerechnet
        self._erlaubt = None
        # Die Nummern der gewählten Flächen – None: alle; dazu ihre Zellen, einmal gerechnet.
        self.flaechen = flaechen
        self._nur = None
        # „Entgraten“: je Operation (Nummer), wie tief ihre Fase unter die Kante geht – so tief
        # darf es in den Zellen, die sie trifft, ins Teil gehen, ohne blau zu werden (wie
        # „Rundum entgraten“ bei der Stange).
        self.fasen = dict(fasen or {})
        self._fasen_erlaubt = np.zeros(quader.h.shape)
        # „Gewinde fräsen“: je Operation (Nummer) die Kreise [(x, y, r)] um die Bohrungen, bis zu
        # denen die Spitze des Zahns reicht – dort darf sie ins Teil (das Gewinde steht nicht im
        # Modell), daneben nicht.
        self.ringe = {k: list(v) for k, v in (ringe or {}).items() if v}
        self._ring_zellen = {}
        self.bis = 0  # abgetragen bis vor diese Station

    def letzte(self):
        """Der Index der letzten Station."""
        return len(self.punkte) - 1

    def bis_station(self, index):
        """Trägt ab bis einschließlich Station `index`; zurück rechnet es von vorn."""
        index = min(index, len(self.punkte) - 1)
        if index + 1 < self.bis:
            self.quader.zuruecksetzen()
            self._fasen_erlaubt.fill(0.0)
            self.bis = 0
        k = np.arange(max(self.bis, 1), index + 1)
        fahren = (
            self.gueltig[k - 1] & self.gueltig[k] & (self.operation[k - 1] == self.operation[k])
        )
        k = k[fahren]
        for nummer, fraeser in self.fraeser.items():
            stuecke = k[self.operation[k] == nummer]
            if not len(stuecke):
                continue
            merken = nummer in self.fasen or nummer in self.ringe
            vorher = self.quader.h.copy() if merken else None
            self.quader.fahre_stuecke(self.punkte[stuecke - 1], self.punkte[stuecke], fraeser)
            if vorher is not None:
                getroffen = self.quader.h < vorher - 1e-9
                if nummer in self.fasen:
                    np.maximum(
                        self._fasen_erlaubt,
                        np.where(getroffen, self.fasen[nummer], 0.0),
                        out=self._fasen_erlaubt,
                    )
                if nummer in self.ringe:
                    self._fasen_erlaubt[getroffen & self._in_ringen(nummer)] = np.inf
        self.bis = max(self.bis, index + 1)

    def eilgaenge_ins_material(self, eilgang, schwelle=EILGANG_SCHWELLE):
        """[(Station, Tiefe in mm, (x, y))] – die Eilgänge, die Material wegnähmen, das dort noch
        steht: der Reihe nach abgefahren, auf einer eigenen Kopie des Quaders – die Vorschübe
        zwischen zwei Eilgängen gebündelt, jeder Eilgang für sich mit der Form seines Fräsers.
        `eilgang`: je Station, ob die Maschine sie im Eilgang anfährt. Senkt ein Eilgang das
        Höhenfeld irgendwo um mehr als `schwelle`, fährt er durchs Material (die Kollision kennt
        das Rohteil sonst nicht)."""
        import copy

        quader = copy.deepcopy(self.quader)
        quader.zuruecksetzen()
        vorschub = []  # Stationen, deren Stück im Vorschub noch zu fahren ist
        ergebnis = []

        def vorschub_fahren():
            if not vorschub:
                return
            stationen = np.asarray(vorschub)
            for nummer, fraeser in self.fraeser.items():
                k = stationen[self.operation[stationen] == nummer]
                if len(k):
                    quader.fahre_stuecke(self.punkte[k - 1], self.punkte[k], fraeser)
            vorschub.clear()

        for k in range(1, len(self.punkte)):
            if not (
                self.gueltig[k - 1]
                and self.gueltig[k]
                and self.operation[k - 1] == self.operation[k]
            ):
                continue
            if not eilgang[k]:
                vorschub.append(k)
                continue
            vorschub_fahren()
            vorher = quader.h.copy()
            fraeser = self.fraeser[int(self.operation[k])]
            quader.fahre_stuecke(self.punkte[k - 1 : k], self.punkte[k : k + 1], fraeser)
            weg = vorher - quader.h
            tiefe = float(weg.max()) if weg.size else 0.0
            if tiefe > schwelle:
                i, j = np.unravel_index(int(np.argmax(weg)), weg.shape)
                ergebnis.append((k, tiefe, (float(quader.x[i]), float(quader.y[j]))))
        return ergebnis

    def _in_ringen(self, nummer):
        """Die Zellen in den Kreisen der Operation `nummer` (ringe) – einmal gerechnet."""
        zellen = self._ring_zellen.get(nummer)
        if zellen is None:
            zellen = np.zeros(self.quader.h.shape, dtype=bool)
            x, y = self.quader.x[:, None], self.quader.y[None, :]
            for mx, my, r in self.ringe[nummer]:
                zellen |= (x - mx) ** 2 + (y - my) ** 2 <= (r + RING_SPIEL) ** 2
            self._ring_zellen[nummer] = zellen
        return zellen

    def vergleich(self):
        """Das Restmaterial gegen das fertige Teil (Vergleich) – die Oberseite des Teils und,
        mit gewählten Flächen, deren Zellen rechnet es beim ersten Mal."""
        if self._teil is None:
            import Part

            from . import hoehenfeld as hf
            from . import vierachs_flaechen as vf

            form = self._formen[0] if len(self._formen) == 1 else Part.makeCompound(self._formen)
            fnetz = vf.vernetze(form)
            self._teil, self._erlaubt = teilhoehen_kanten(fnetz.netz, self.quader)
            if self.flaechen:
                drin = np.isin(fnetz.flaeche, sorted(self.flaechen))
                nur = vh.Netz(fnetz.netz.punkte, fnetz.netz.dreiecke[drin], fnetz.netz.toleranz)
                self._nur = np.isfinite(hf.hoehen(nur, self.quader.x, self.quader.y, innen=True))
        erlaubt = self._erlaubt
        if self.fasen or self.ringe:
            erlaubt = np.maximum(erlaubt, self._fasen_erlaubt)
        return vergleiche_quader(self.quader, self._teil, self.aufmass, self._nur, erlaubt=erlaubt)


def _werkzeug_von_oben(abfahrt, nummer):
    """Kommt das Werkzeug der Operation `nummer` am Werkstück senkrecht von oben – die Spitze
    unten, der Halter in +z des Jobs? Gelesen an der ersten erreichbaren Station: Wäre das
    Werkzeug 1 mm länger, rückte die Spitze um 1 mm vom Halter weg – von oben nach −z."""
    from . import reichweite as rw
    from .kinematik import Kinematik

    op = abfahrt.operationen[nummer]
    index = next(
        (
            i
            for i, s in enumerate(abfahrt.stationen)
            if s.operation == nummer and s.stellungen is not None
        ),
        None,
    )
    if index is None:
        return False
    stellungen = abfahrt.stellungen_an(index)
    laenger = Kinematik(
        abfahrt.pruefung, op.aufnahme, rw.Einspannung(op.laenge + 1.0, op.lage), abfahrt.nullpunkt
    )
    spitze = np.array(abfahrt.kinematik(nummer).am_werkstueck(stellungen))
    richtung = np.array(laenger.am_werkstueck(stellungen)) - spitze
    return richtung[2] < -1.0 + 1e-6


def fuer_quader(abfahrt, job, am_werkstueck):
    """Der Abtrag im Quader für diesen Job – oder None, wenn das Rohteil kein Kasten ist (aus
    dem Modell oder mit Maßen), eine Rundachse fährt, oder ein Werkzeug nicht senkrecht von
    oben kommt. Jede Operation mit Werkzeug trägt mit dessen Form ab; verglichen wird mit dem
    Aufmaß der letzten, die eins hat, und – haben alle Operationen gewählte Flächen – nur
    auf ihnen."""
    rohteil = getattr(job, "Stock", None)
    form = getattr(rohteil, "Shape", None)
    if form is None or form.isNull() or hasattr(rohteil, "Radius"):
        return None
    if not (hasattr(rohteil, "ExtZpos") or hasattr(rohteil, "Length")):
        return None
    if not abfahrt.stationen or not abfahrt.operationen:
        return None
    if any(any(s.rund.values()) for s in abfahrt.stationen):
        return None
    fraeser = {}
    for k, op in enumerate(abfahrt.operationen):
        if op.tc is None or getattr(op.tc, "Tool", None) is None:
            continue
        if not any(s.operation == k and s.stellungen is not None for s in abfahrt.stationen):
            # Fährt nichts ab – ein Messstopp hebt nur Z – und trägt nichts ab. Bis 0.126.0 hieß
            # das „nicht von oben“: Mit einem Messstopp im Job blieb das Rohteil stehen.
            continue
        if not _werkzeug_von_oben(abfahrt, k):
            return None
        fraeser[k] = _fraeser(op.tc)
    if not fraeser:
        return None
    ops = {o.Label: o for o in getattr(job.Operations, "Group", [])}
    operation = np.array([s.operation for s in abfahrt.stationen])
    gueltig = np.array(
        [s.stellungen is not None and s.operation in fraeser for s in abfahrt.stationen]
    )
    aufmass = next(
        (
            float(ops[abfahrt.operationen[k].name].Aufmass)
            for k in sorted(fraeser, reverse=True)
            if hasattr(ops.get(abfahrt.operationen[k].name), "Aufmass")
        ),
        0.0,
    )
    from . import vierachs_flaechen as vf
    from .vierachs_operation import flaechen as flaechen_von

    formen = [
        o.Shape
        for o in getattr(job.Model, "Group", [])
        if getattr(o, "Shape", None) is not None and not o.Shape.isNull()
    ]
    if not formen:
        return None
    # Verglichen wird auf den gewählten ebenen Flächen nach oben – hat eine Operation nur
    # Wände (Kontur), zählt sie wie eine ohne Wahl: dann überall.
    gewaehlt = [
        (
            _ebene_namen(formen[0], flaechen_von(ops[abfahrt.operationen[k].name]))
            if abfahrt.operationen[k].name in ops
            else ()
        )
        for k in sorted(fraeser)
    ]
    flaechen = set().union(*(vf.nummern(g) for g in gewaehlt)) if all(gewaehlt) else None
    box = form.BoundBox
    quader = Quader(box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax)
    from .entgraten import eindringtiefe, ist_entgraten
    from .gewindefraesen import ist_gewindefraesen
    from .gewindefraesen import ringe as gewinde_ringe

    fasen = {}
    ringe = {}
    for k in fraeser:
        op = ops.get(abfahrt.operationen[k].name)
        if op is not None and ist_entgraten(op):
            fasen[k] = eindringtiefe(op) + FASE_SPIEL
        elif op is not None and _zentrier_fase(op) > 0:
            fasen[k] = _zentrier_fase(op) + FASE_SPIEL
        elif op is not None and ist_gewindefraesen(op):
            ringe[k] = gewinde_ringe(op, job)
    return QuaderAbtrag(
        quader, am_werkstueck, operation, gueltig, fraeser, aufmass, formen, flaechen, fasen, ringe
    )


def _ebene_namen(form, namen):
    """Die Namen aus `namen` („Face3“ …), die ebene Flächen nach oben sind."""
    from . import hoehenfeld as hf

    return tuple(e.name for e in hf.ebenen_oben(form, list(namen))) if namen else ()


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


def darstellung_quader(quader, zeilen=1, spalten=1):
    """(x, y, h) fürs Bild: die Oberseite des Quaders im Job, je `zeilen` × `spalten` Zellen
    ein Punkt – die tiefste Höhe darin."""
    h = _bloecke(quader.h, zeilen, spalten, np.min)
    x = quader.x[: h.shape[0] * zeilen : zeilen]
    y = quader.y[: h.shape[1] * spalten : spalten]
    return x, y, h


def farben_quader(vergleich, zeilen=1, spalten=1):
    """Die Farbe je Punkt von darstellung_quader(): die schwerste im Block."""
    schwere = np.vectorize(SCHWERE.get)(vergleich.farbe)
    block = _bloecke(schwere, zeilen, spalten, np.max)
    zurueck = {v: k for k, v in SCHWERE.items()}
    return np.vectorize(zurueck.get)(block)
