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

Am Ende der Vergleich mit dem fertigen Teil (vergleiche): seine Radien im selben
Raster (die Hüllfläche einer Scheibe von einer halben Rasterweite, vierachs_huelle),
je Zelle der Rest darüber – grün bis Aufmaß + 0,1 mm, gelb darüber, rot ab Aufmaß
+ 1 mm; verglichen wird mit dem Aufmaß der letzten Bearbeitung. Blau, wo mehr als
0,05 mm im Teil fehlen – das liest es genau auf dem Strahl (Scheibe GENAU): Neben einer
Wand sähe die breitere Scheibe schon die Wand, und was der Kugelfräser dort weg nahm,
fehlte scheinbar im Teil.

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
        """Wie fahre(), für viele Stücke auf einmal: `von` und `nach` je (n, 3). Wie herum
        er sie fährt, ist gleich – weg ist, was irgendein Schritt trifft."""
        von = np.asarray(von, dtype=float).reshape(-1, 3)
        nach = np.asarray(nach, dtype=float).reshape(-1, 3)
        if not len(von):
            return
        bogen = np.abs(np.radians(nach[:, 2] - von[:, 2])) * np.maximum(von[:, 1], nach[:, 1])
        weg = np.maximum(bogen, np.abs(nach[:, :2] - von[:, :2]).max(axis=1))
        anzahl = np.maximum(1, np.ceil(weg / TEILSCHRITT)).astype(np.int64)
        stueck = np.repeat(np.arange(len(von)), anzahl)
        vorher = np.repeat(np.cumsum(anzahl) - anzahl, anzahl)
        t = ((np.arange(len(stueck)) - vorher + 1) / anzahl[stueck])[:, None]
        punkte = von[stueck] + t * (nach[stueck] - von[stueck])
        self.schnitte(punkte[:, 0], punkte[:, 1], punkte[:, 2], fraeser)

    def schnitt(self, a_t, r_t, phi_t_grad, fraeser):
        """Nimmt weg, was der Fräser mit der Spitze bei (a_t, r_t, φ_t) trifft."""
        self.schnitte([a_t], [r_t], [phi_t_grad], fraeser)

    def schnitte(self, a_t, r_t, phi_t_grad, fraeser):
        """Wie schnitt(), an vielen Stellen auf einmal (Folgen gleicher Länge)."""
        form = fraeser if isinstance(fraeser, ff.Form) else None
        radius = form.radius if form is not None else float(fraeser)
        a_t = np.asarray(a_t, dtype=float)
        r_t = np.asarray(r_t, dtype=float)
        phi_t = np.radians(np.asarray(phi_t_grad, dtype=float))
        drin = r_t < self.radius  # darüber trifft er nichts
        if radius <= 0 or not drin.any():
            return
        a_t, r_t, phi_t = a_t[drin], np.maximum(r_t[drin], 1e-6), phi_t[drin]
        weit = np.arctan(radius / r_t)  # weiter weg trifft kein Strahl den Fräser
        zeilen = int(math.ceil(2 * radius / self._schritt_a)) + 2
        spalten = int(math.ceil(2 * float(weit.max()) / self._schritt_phi)) + 3
        je = max(1, ZELLEN_JE_BLOCK // (zeilen * spalten))
        for von in range(0, len(a_t), je):
            stellen = slice(von, von + je)
            self._block(
                a_t[stellen],
                r_t[stellen],
                phi_t[stellen],
                weit[stellen],
                radius,
                form,
                zeilen,
                spalten,
            )

    def _block(self, a_t, r_t, phi_t, weit, radius, form, zeilen, spalten):
        """schnitte() für einen Block von Stellen: je Stelle `zeilen` × `spalten` Zellen um
        ihre Spitze, in denen der Fräser liegen kann."""
        erste_zeile = np.searchsorted(self.a, a_t - radius, "left")
        zeile = erste_zeile[:, None] + np.arange(zeilen)[None, :]
        zeile_da = zeile < len(self.a)
        zeile = np.minimum(zeile, len(self.a) - 1)
        d = self.a[zeile] - a_t[:, None]  # längs von der Spitze
        zeile_da &= np.abs(d) <= radius
        schritt = self._schritt_phi
        erste_spalte = np.floor((phi_t - weit) / schritt).astype(np.int64)
        spalte = erste_spalte[:, None] + np.arange(spalten)[None, :]
        delta = spalte * schritt - phi_t[:, None]
        spalte_da = np.abs(delta) < math.pi / 2 - 1e-9
        zelle = zeile[:, :, None] * len(self.phi) + (spalte % len(self.phi))[:, None, :]
        gueltig = zeile_da[:, :, None] & spalte_da[:, None, :]
        alle = self.r.reshape(-1)
        if form is None or form.eben:
            tan = np.abs(np.tan(delta))
            seitlich = np.sqrt(np.maximum(radius * radius - d * d, 0.0))
            trifft = (r_t[:, None] * tan)[:, None, :] <= seitlich[:, :, None]
            bis_hier = np.where(trifft, (r_t[:, None] / np.cos(delta))[:, None, :], np.inf)
        else:
            bis_hier = _stirn(form, r_t, d, delta, gueltig, alle[zelle])
        da = gueltig & np.isfinite(bis_hier)
        if da.any():  # eine Zelle kann mehrmals vorkommen – at() nimmt das kleinste
            np.minimum.at(alle, zelle[da], bis_hier[da])


def _stirn(form, r_t, d, delta, gueltig, steht):
    """Wo die Strahlen die Stirn des Fräsers (Form) mit der Spitze auf r_t treffen – ihr
    Abstand von der Achse, (Stellen, Zeilen, Spalten); inf, wo keiner trifft oder er nichts
    wegnimmt. `d`: je Stelle und Zeile längs von der Spitze, `delta`: je Stelle und Spalte
    der Winkel zur Werkzeugachse (rad); `gueltig`: die Zellen, die zählen; `steht`: bis wohin
    dort noch Material steht."""
    cos = np.cos(delta)[:, None, :]
    if form.nur_kugel:  # der Strahl trifft die untere Hälfte der Kugel – geschlossen
        mitte = r_t[:, None, None] + form.radius
        innen = form.radius**2 - (d * d)[:, :, None] - (mitte * np.sin(delta)[:, None, :]) ** 2
        return np.where(innen >= 0, mitte * cos - np.sqrt(np.maximum(innen, 0.0)), np.inf)
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
    t2 = np.broadcast_to((np.tan(delta) ** 2)[:, None, :], groesse).ravel()[offen]
    unten = np.broadcast_to(r_t[:, None, None], groesse).ravel()[offen]
    cos = np.broadcast_to(cos, groesse).ravel()[offen]
    steht = steht.ravel()[offen]
    quer = np.sqrt(d2 + unten * unten * t2)
    noch = np.arange(offen.size)
    with np.errstate(invalid="ignore", divide="ignore"):
        for _ in range(SUCHSCHRITTE):
            ell = quer[noch]
            z, steigung = _hoehe(form, ell)
            hoch = unten[noch] + z
            weiter = np.sqrt(d2[noch] + hoch * hoch * t2[noch])  # F(ℓ)
            rho = hoch / cos[noch]
            schneidet = rho < steht[noch]
            g = weiter - ell
            fertig = schneidet & (g <= 1e-9)
            ergebnis[offen[noch[fertig]]] = rho[fertig]
            if form.konvex:
                faellt = 1.0 - hoch * t2[noch] * steigung / weiter  # −g′
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


def teilradien(netz, laengs, radial, stange, radius=SCHRITT_A / 2):
    """Die Radien des fertigen Teils im Raster der Stange – −inf, wo es keins gibt. Die Scheibe
    einer halben Rasterweite fasst, was zwischen den Strahlen liegt; mit `radius` GENAU liest
    es das Teil auf den Strahlen."""
    return vh.schaftfraeser(netz, laengs, radial, radius, stange.a, stange.phi).r


def vergleiche(stange, teil, aufmass, genau=None, nur=None):
    """Das Restmaterial gegen das fertige Teil (`teil`: teilradien()), je Zelle eingefärbt;
    `aufmass`: das Aufmaß, das stehen bleiben soll (mm). `genau`: das Teil auf den Strahlen
    (teilradien() mit GENAU) – nur was dort fehlt, ist blau. `nur`: (n_a, n_phi) die Zellen
    der gewählten Flächen – nur sie bekommen Grün, Gelb oder Rot; Blau gilt überall."""
    da = np.isfinite(teil)
    genau = teil if genau is None else genau
    tief = np.where(da & np.isfinite(genau), stange.r - genau, np.nan)
    if nur is not None:
        da = da & nur
    rest = np.where(da, stange.r - teil, np.nan)
    farbe = np.full(stange.r.shape, OHNE_TEIL, dtype=np.int8)
    farbe[da & (rest <= aufmass + GRUEN_BIS)] = GRUEN
    farbe[da & (rest > aufmass + GRUEN_BIS)] = GELB
    farbe[da & (rest >= aufmass + ROT_AB)] = ROT
    with np.errstate(invalid="ignore"):
        farbe[tief < -BLAU_AB] = BLAU
    kleinster = float(np.nanmin(tief)) if np.isfinite(tief).any() else 0.0
    groesster = float(np.nanmax(rest)) if da.any() else 0.0
    return Vergleich(rest, farbe, kleinster, groesster, nur is not None)


class Abtrag:
    """Die Stange eines 4-Achs-Jobs beim Abfahren (abfahren.Abfahrt): was bis zu einer
    Station weg ist. fuer() baut es – nur für Jobs mit runder Stange und „Rundum
    schruppen“ oder „Rundum schlichten“."""

    def __init__(self, stange, laengs, radial, stationen, fraeser, aufmass, formen, flaechen=None):
        self.stange = stange
        self.laengs, self.radial = laengs, radial
        # je Station (a, r, φ in Grad, fortlaufend), Operation, gültig
        self.a, self.r, self.phi, self.operation, self.gueltig = stationen
        self._punkte = np.stack([self.a, self.r, self.phi], axis=1)
        self.fraeser = fraeser  # je Operation (Nummer in der Abfahrt) Form oder Radius
        self.aufmass = aufmass
        self._formen = formen
        self._teil = None  # teilradien() mit der halben Rasterweite und GENAU, einmal gerechnet
        # Die Nummern der gewählten Flächen (V4) – None: alle; dazu ihre Zellen, einmal gerechnet.
        self.flaechen = flaechen
        self._nur = None
        self.bis = 0  # abgetragen bis vor diese Station

    def bis_station(self, index):
        """Trägt ab bis einschließlich Station `index`; zurück rechnet es von vorn."""
        index = min(index, len(self.a) - 1)
        if index + 1 < self.bis:
            self.stange.zuruecksetzen()
            self.bis = 0
        k = np.arange(max(self.bis, 1), index + 1)
        fahren = (
            self.gueltig[k - 1] & self.gueltig[k] & (self.operation[k - 1] == self.operation[k])
        )
        k = k[fahren]
        for nummer, fraeser in self.fraeser.items():
            stuecke = k[self.operation[k] == nummer]
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
        return vergleiche(self.stange, self._teil[0], self.aufmass, self._teil[1], self._nur)


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
    u, v = punkte @ u_, punkte @ v_
    r = np.hypot(u, v)
    phi = np.degrees(np.unwrap(np.arctan2(v, u)))
    operation = np.array([s.operation for s in abfahrt.stationen])
    fraeser = {k: _fraeser(abfahrt.operationen[k].tc) for k in rundum}
    gueltig = np.array(
        [s.stellungen is not None and s.operation in fraeser for s in abfahrt.stationen]
    )
    aufmass = float(ops[abfahrt.operationen[rundum[-1]].name].Aufmass)
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
        stange, laengs, radial, (a, r, phi, operation, gueltig), fraeser, aufmass, formen, flaechen
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
    """Wie job_schnittwerte.operationsart() „Rundum schruppen“ und „Rundum schlichten“ nennt
    (die Namen ihrer Module)."""
    return ("vierachs_operation", "vierachs_schlichten")


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
