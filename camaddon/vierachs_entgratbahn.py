# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Bahn „Rundum entgraten“ (Spezifikation W-003, Stufe V4d; W-006, 4.1 Punkt 8 und 4.3.3):
An den Außenkanten der gewählten Flächen fährt ein Fasenfräser entlang – oder ein Kugelfräser
als Kantenbruch –, die Rundachse dreht mit (Manuel: „Und Entgraten nicht vergessen“).

- Kanten (kanten()): jede Kante, an der eine gewählte Fläche mit einer anderen – gewählt oder
  nicht – einen Knick nach außen bildet. Keine Innenkante (dort gibt es keinen Grat, und der
  Fräser käme nicht hin), keine Rundung, die tangential übergeht, keine Nahtkante eines
  Zylinders, und keine Kante an den Enden des Teils: Die Stirn vorne nimmt später das Planen,
  hinten das Abstechen – diese Kanten gibt es im Job noch nicht.
- Je Punkt der Kante steht die Rundachse so, dass er zum Werkzeug schaut; der Fräser sinkt auf
  dem Strahl von der Achse, bis er das Teil berührt (die Hüllfläche, vierachs_huelle.je_winkel
  mit seiner Form, gegen das ganze Teil) – an einer Außenkante ist das die Kante selbst –, und
  um die Eindringtiefe tiefer (eindringtiefe()): die Fasenbreite beim Fasenfräser, beim
  Kugelfräser so viel, dass der Kantenbruch so breit wird. Berührt er vorher etwas anderes (die
  Kante liegt im Schatten: hinter einem Absatz, in einer Nut, die enger ist als der Fräser),
  lässt er den Punkt aus – eine Kante ganz ohne Punkte zählt als ausgelassen.
- Im Gleichlauf (P-2026-10-02-25): Je Kante liegt das Material dort, wohin die beiden Flächen
  von ihr weg zeigen (kanten(): `material`, im Rahmen an der Kante – radial, quer, längs);
  spindel.ist_gleichlauf sagt, ob die Fahrt in der Reihe ihrer Punkte für M3 Gleichlauf ist –
  sonst fährt jedes Stück andersherum (mit M4 umgekehrt). Die Richtung steht damit fest.
- Von Stück zu Stück im Eilgang auf dem Sicherheitsradius, immer zu dem, das am nächsten
  liegt, von seinem Anfang an (ohne feste Richtung: von dem Ende, das näher liegt); beginnt eines, wo das vorige endet (die Naht des
  Zylinders teilt einen Bogen), geht es ohne Abheben weiter. Hinein mit dem Eintauchvorschub
  senkrecht auf den ersten Punkt. Ein Ring rundum wird ganz gefahren und endet, wo er begann
  (die Rundachse dreht eine Umdrehung). Was gerade weitergeht, fasst die Bahn zusammen
  (vierachs_bahn._zusammengefasst), höchstens HOECHSTENS_GRAD Drehung je Satz.
- Längs reicht die Bahn so weit wie die anderen Rundum-Bahnen: nicht näher ans Futter, als
  Fräser oder Halter mit Abstand erlauben (vierachs_bahn._ende).

Gerechnet in (a, r, φ) wie vierachs_bahn.Punkt, ohne Versatz quer. Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_huelle as vh
from .sprache import tr

BREITE = 0.3  # mm – die Fasenbreite, wenn nichts anderes gesagt ist (W-003 V4d)
SCHRITT = vh.SCHRITT_A  # mm – so dicht liegen die Punkte auf einer Kante
VORSCHAU_SCHRITT = 1.0  # mm – für die Vorschau im Assistenten
TOLERANZ = vh.TOLERANZ  # mm – so fein wird das Teil vernetzt
VORSCHAU_TOLERANZ = 0.05  # mm – für die Vorschau im Assistenten
MINDEST_KNICK = 10.0  # Grad – flacher gilt der Übergang als Rundung ohne Grat
SCHATTEN = 0.05  # mm – so viel höher als die Kante darf die Berührung liegen (Vernetzung)
ENDE_RAND = 1e-3  # mm – so nah an einem Ende des Teils liegt eine Kante auf seiner Stirn
_PROBE = 0.05  # mm – so weit neben der Kante prüft kanten(), ob der Knick nach außen geht
_GLEICH = 1e-6  # mm


@dataclass
class Kante:
    """Eine Außenkante einer gewählten Fläche (kanten())."""

    name: str  # „Edge7“
    flaechen: tuple  # („Face3“, „Face1“): die gewählte Fläche und die andere
    laenge: float  # mm
    geschlossen: bool  # ein Ring: Anfang und Ende sind derselbe Punkt
    knick: float  # Grad zwischen den Normalen beider Flächen (90 an einer rechten Kante)
    punkte: np.ndarray  # (n, 3) im Job, der Reihe nach, etwa `schritt` auseinander
    # In der Mitte der Kante im Rahmen dort (radial, quer, längs): wohin sie in der Reihe der
    # Punkte läuft und wo das Material liegt – für den Gleichlauf; None: unbekannt.
    fahrt: tuple = None
    material: tuple = None


def kanten(form, laengs, radial, namen, schritt=SCHRITT, mindest_knick=MINDEST_KNICK):
    """[Kante] – die Außenkanten der Flächen `namen` („Face3“ …; leer: alle) von `form`
    (Part.Shape), jede einmal: wo eine gewählte Fläche mit einer anderen um mindestens
    `mindest_knick` Grad nach außen knickt. Nicht dabei: Innenkanten, tangentiale Übergänge,
    Nähte, und Kanten auf den Stirnen des Teils (vorne nimmt sie das Planen, hinten das
    Abstechen). `laengs` und `radial` wie in vierachs_huelle."""
    import Part

    from . import vierachs_flaechen as vf

    l_, _u, _v = vh.rahmen(laengs, radial)
    flaechen = form.Faces
    gewaehlt = set(vf.nummern(namen)) if namen else set(range(len(flaechen)))
    if not form.Vertexes:
        return []
    a_ecken = np.array([[v.X, v.Y, v.Z] for v in form.Vertexes], dtype=float) @ l_
    a_vorne, a_hinten = float(a_ecken.max()), float(a_ecken.min())
    an_kante = {}  # Kante (hashCode) -> Nummern der Flächen, zu denen sie gehört
    for nummer, flaeche in enumerate(flaechen):
        for kante in flaeche.Edges:
            an_kante.setdefault(kante.hashCode(), set()).add(nummer)
    ergebnis = []
    for i, kante in enumerate(form.Edges):
        nummern = sorted(an_kante.get(kante.hashCode(), ()))
        if len(nummern) != 2 or not any(n in gewaehlt for n in nummern):
            continue  # Naht, offene Kante – oder keine gewählte Fläche daran
        if kante.Length < schritt / 2:
            continue
        mitte = (kante.FirstParameter + kante.LastParameter) / 2
        p = kante.valueAt(mitte)
        e = kante.tangentAt(mitte)
        if e.Length < _GLEICH:
            continue
        e.normalize()
        normalen, hinein = [], []
        for nummer in nummern:
            flaeche = flaechen[nummer]
            normale = flaeche.normalAt(*flaeche.Surface.parameter(p))
            if normale.Length < _GLEICH:
                break
            normale.normalize()
            t = normale.cross(e)  # in der Fläche, quer zur Kante – welche Seite, sagt die Probe
            if t.Length < _GLEICH:
                break
            t.normalize()
            if (
                flaeche.distToShape(Part.Vertex(p - t * _PROBE))[0]
                < flaeche.distToShape(Part.Vertex(p + t * _PROBE))[0]
            ):
                t = -t
            normalen.append(normale)
            hinein.append(t)
        if len(normalen) != 2:
            continue
        knick = math.degrees(math.acos(max(-1.0, min(1.0, normalen[0].dot(normalen[1])))))
        if knick < mindest_knick:
            continue  # eine Rundung, die übergeht
        summe = hinein[0] + hinein[1]
        if summe.Length < _GLEICH:
            continue
        summe.normalize()
        if not form.isInside(p + summe * _PROBE, _GLEICH, True):
            continue  # Innenkante: zwischen den Flächen ist Luft
        punkte = np.array([[q.x, q.y, q.z] for q in kante.discretize(Distance=schritt)])
        if len(punkte) < 2:
            continue
        a = punkte @ l_
        if np.all(np.abs(a - a_vorne) < ENDE_RAND) or np.all(np.abs(a - a_hinten) < ENDE_RAND):
            continue  # auf der Stirn: die gibt es im Job noch nicht
        eigene = next(n for n in nummern if n in gewaehlt)
        andere = next(n for n in nummern if n != eigene)
        fahrt = material = None
        ort = np.array([p.x, p.y, p.z], dtype=float)
        quer_zur_achse = ort - l_ * float(ort @ l_)
        if np.linalg.norm(quer_zur_achse) > _GLEICH:
            e_r = quer_zur_achse / np.linalg.norm(quer_zur_achse)
            e_q = np.cross(l_, e_r)
            rahmen = (e_r, e_q, l_)
            fahrt = tuple(float(np.dot([e.x, e.y, e.z], achse)) for achse in rahmen)
            material = tuple(float(np.dot([summe.x, summe.y, summe.z], achse)) for achse in rahmen)
        ergebnis.append(
            Kante(
                f"Edge{i + 1}",
                (f"Face{eigene + 1}", f"Face{andere + 1}"),
                float(kante.Length),
                bool(kante.isClosed()),
                knick,
                punkte,
                fahrt,
                material,
            )
        )
    return ergebnis


@dataclass(frozen=True)
class Entgratwerte:
    """Was „Rundum entgraten“ braucht; Längen in mm, a längs der Stangenachse im Job."""

    form: object  # fraeserform.Form des Fräsers – Fasenfräser (Kegel) oder Kugel
    stange_radius: float
    breite: float  # die Fasenbreite (mm); beim Kugelfräser die Breite des Kantenbruchs
    a_stange_vorne: float
    a_futter: float
    sicherheit: float = vb.SICHERHEIT
    ueberlauf: float = None  # längs über das Teil hinaus; None: Vorschlag
    abstand_futter: float = vb.ABSTAND_FUTTER
    halter: float = 0.0  # wie bei vierachs_bahn.Schruppwerte
    gleichlauf: bool = True  # im Gleichlauf für M3 (spindel.fuer_m3); False: andersherum


@dataclass
class Entgratbahn:
    """Ergebnis von entgraten()."""

    punkte: list  # [vierachs_bahn.Punkt], der erste ist der Start (Eilgang, vor der Stange)
    kanten: int  # so viele Kanten fährt sie (ganz oder zum Teil)
    ausgelassen: int  # so viele Kanten erreicht der Fräser nirgends
    laenge: float  # mm im Vorschub an den Kanten
    hinten_frei: float = 0.0  # wie bei vierachs_bahn.Bahn


def eindringtiefe(form, breite):
    """So weit sinkt die Spitze unter die Berührung (mm): die Fasenbreite – beim Kugelfräser so
    viel, dass der Kantenbruch an einer rechten Kante `breite` breit wird (höchstens der
    Kugelradius)."""
    kugel = form.kugel
    if kugel > 0:
        if breite >= kugel:
            return kugel
        return kugel - math.sqrt(kugel * kugel - breite * breite)
    return breite


def entgraten(netz, laengs, radial, werte, kanten_):
    """Die Bahn „Rundum entgraten“ (Entgratbahn) an den Kanten `kanten_` ([Kante]) mit den
    Werten `werte`; `netz` ist das ganze Teil (vierachs_huelle.vernetze), `laengs` und `radial`
    wie in vierachs_huelle. ValueError mit einem Satz, wenn es nicht geht."""
    w = werte
    form = w.form
    radius = form.radius
    if w.breite <= 0:
        raise ValueError(tr("ve.fehler.breite"))
    if not kanten_:
        raise ValueError(tr("ve.fehler.keine_kanten"))
    l_, u_, v_ = vh.rahmen(laengs, radial)
    a_teil = netz.punkte @ l_
    teil_vorne, teil_hinten = float(a_teil.max()), float(a_teil.min())
    ueberlauf = vb.ueberlauf_vorschlag(radius) if w.ueberlauf is None else w.ueberlauf
    a_anfang = w.a_stange_vorne + radius + w.sicherheit
    a_ende = vb._ende(teil_hinten, ueberlauf, radius, w)
    if a_ende >= teil_vorne + radius:
        raise ValueError(vb._kein_platz(radius, w))
    hinten_frei = max(0.0, a_ende - radius - teil_hinten)
    tiefe = eindringtiefe(form, w.breite)
    geformt = form.mit_aufmass(netz.toleranz)
    sicher = w.stange_radius + w.sicherheit
    # Alle Punkte aller Kanten auf einmal: wo berührt der Fräser dort das Teil?
    alle = np.concatenate([k.punkte for k in kanten_])
    a = alle @ l_
    x = alle @ u_
    y = alle @ v_
    r_kante = np.hypot(x, y)
    phi = np.arctan2(y, x)
    beruehrt = vh.je_winkel(netz, laengs, radial, geformt, a, 1.0, 1, phi)[0] + netz.toleranz
    with np.errstate(invalid="ignore"):
        gut = (
            (a >= a_ende - vb.GLEICH)
            & (a <= a_anfang + vb.GLEICH)
            & np.isfinite(beruehrt)
            & (beruehrt <= r_kante + SCHATTEN)
            & (beruehrt - tiefe > vb.GLEICH)
        )
    punkte = [vb.Punkt(True, a_anfang, sicher, 0.0)]
    stuecke = []  # (a, r, φ in Grad) je Stück, das der Fräser fährt
    gefahren = ausgelassen = 0
    anfang = 0
    for kante in kanten_:
        ende = anfang + len(kante.punkte)
        eigene = _stuecke(
            gut[anfang:ende], a[anfang:ende], beruehrt[anfang:ende] - tiefe, phi[anfang:ende], kante
        )
        richtung = _richtung(kante, w.gleichlauf)
        if richtung is not None:  # fest: in der Reihe der Punkte (True) oder andersherum
            eigene = [
                (sa, sr, sg, True) if richtung else (sa[::-1], sr[::-1], sg[::-1], True)
                for sa, sr, sg, _fest in eigene
            ]
        anfang = ende
        if eigene:
            gefahren += 1
            stuecke += eigene
        else:
            ausgelassen += 1
    if gefahren == 0:
        raise ValueError(tr("ve.fehler.nichts"))
    laenge = _fahrten(punkte, stuecke, sicher, w.sicherheit)
    letzter = punkte[-1]
    vb._eilgang(punkte, a_anfang, sicher, letzter.phi)
    return Entgratbahn(punkte, gefahren, ausgelassen, laenge, hinten_frei)


def _richtung(kante, gleichlauf):
    """Fährt der Fräser die Kante in der Reihe ihrer Punkte im Gleichlauf (True), andersherum
    (False) – oder ist es unbekannt (None)? Das Werkzeug zeigt radial zur Achse."""
    if kante.fahrt is None or kante.material is None:
        return None
    return sp.ist_gleichlauf((-1.0, 0.0, 0.0), kante.fahrt, kante.material) == bool(gleichlauf)


def _stuecke(gut, a, r, phi, kante):
    """[(a, r, φ in Grad, fortlaufend, fest)] – die Stücke der Kante, die der Fräser fährt: die
    zusammenhängenden guten Punkte, mindestens zwei. Ein Ring, der ganz geht, ist ein Stück und
    endet, wo er begann; mit Lücke beginnt er hinter einer."""
    n = len(gut)
    if kante.geschlossen and n > 2:
        if gut.all():
            return [(a, r, np.degrees(np.unwrap(phi)), False)]
        # Ohne den doppelten Endpunkt, und so gedreht, dass es hinter einer Lücke beginnt.
        gut, a, r, phi = gut[:-1], a[:-1], r[:-1], phi[:-1]
        erste_luecke = int(np.flatnonzero(~gut)[0])
        reihe = (np.arange(len(gut)) + erste_luecke + 1) % len(gut)
        gut, a, r, phi = gut[reihe], a[reihe], r[reihe], phi[reihe]
    ergebnis = []
    for von, bis in _laeufe(gut):
        if bis - von < 2:
            continue  # ein Punkt allein
        k = slice(von, bis)
        ergebnis.append((a[k], r[k], np.degrees(np.unwrap(phi[k])), False))
    return ergebnis


def _laeufe(gut):
    """[(von, bis)] – die Läufe aufeinanderfolgender guter Punkte, `bis` ausschließlich."""
    if not len(gut):
        return []
    wechsel = np.flatnonzero(np.diff(gut.astype(np.int8)))
    anfaenge = np.concatenate([[0], wechsel + 1])
    enden = np.concatenate([wechsel + 1, [len(gut)]])
    return [(int(von), int(bis)) for von, bis in zip(anfaenge, enden, strict=True) if gut[von]]


def _fahrten(punkte, stuecke, sicher, sicherheit):
    """Die Stücke an die Bahn, immer das nächste zuerst: im Eilgang über das nähere Ende,
    knapp über die Berührung, mit dem Eintauchvorschub hinein, an der Kante entlang – ohne
    Abheben weiter, wo ein Stück beginnt, wo das vorige endet –, am Ende radial hinaus. Gibt
    die Länge im Vorschub an den Kanten zurück (mm)."""
    offen = list(stuecke)
    laenge = 0.0
    unten = False  # die Spitze steht an der Kante (noch nicht abgehoben)
    while offen:
        vorher = punkte[-1]
        # Das Stück, das am nächsten liegt – und von welchem Ende (beim Ring: welchem Punkt).
        beste = None
        for i, (a, r, grad, fest) in enumerate(offen):
            abstaende = _abstand(vorher, a, r, grad)
            ring = _ist_ring(a, r, grad)
            enden = abstaende[[0]] if fest else abstaende[[0, -1]]  # fest: nur vom Anfang
            k = int(np.argmin(abstaende[:-1] if ring else enden))
            weit = float((abstaende[:-1] if ring else enden)[k])
            if beste is None or weit < beste[0]:
                beste = (weit, i, k, ring)
        weit, i, k, ring = beste
        a, r, grad, _fest = offen.pop(i)
        if ring:
            a, r, grad = a[:-1], r[:-1], grad[:-1]
            reihe = (np.arange(len(a)) + k) % len(a)
            a, r, grad = a[reihe], r[reihe], np.degrees(np.unwrap(np.radians(grad[reihe])))
            schluss = grad[0] + math.copysign(360.0, (grad[-1] - grad[0]) or 1.0)
            a, r, grad = np.append(a, a[0]), np.append(r, r[0]), np.append(grad, schluss)
        elif k == 1:
            a, r, grad = a[::-1], r[::-1], grad[::-1]
        # Der Winkel fortlaufend: so nah an dem, wo die Bahn steht, wie es geht.
        grad = grad + 360.0 * round((vorher.phi - grad[0]) / 360.0)
        # Zusammenfassen, wo es gerade weitergeht – höchstens HOECHSTENS_GRAD Drehung je Satz.
        schritt = float(np.abs(np.diff(grad)).max()) if len(grad) > 1 else 0.0
        hoechstens = max(1, int(vb.HOECHSTENS_GRAD / schritt)) if schritt > 1e-9 else len(a)
        bleibt = vb._zusammengefasst(r, vb.BAHN_TOLERANZ, hoechstens)
        a0, r0, phi0 = float(a[0]), float(r[0]), float(grad[0])
        anschluss = unten and weit < SCHRITT and abs(r0 - vorher.r) < vb.BAHN_TOLERANZ
        if not anschluss:
            if unten:
                punkte.append(vb.Punkt(True, vorher.a, sicher, vorher.phi))
            vb._eilgang(punkte, a0, sicher, phi0)
            knapp = min(sicher, r0 + sicherheit)
            if knapp < sicher:
                punkte.append(vb.Punkt(True, a0, knapp, phi0))
            punkte.append(vb.Punkt(False, a0, r0, phi0, True))
        for i in bleibt[1:]:
            punkt = vb.Punkt(False, float(a[i]), float(r[i]), float(grad[i]))
            laenge += vb._weg(punkte[-1], punkt)
            punkte.append(punkt)
        unten = True
    letzter = punkte[-1]
    punkte.append(vb.Punkt(True, letzter.a, sicher, letzter.phi))
    return laenge


def _ist_ring(a, r, grad):
    """Endet das Stück, wo es begann, eine Umdrehung weiter?"""
    return (
        len(a) > 2
        and abs(a[0] - a[-1]) < _GLEICH
        and abs(r[0] - r[-1]) < _GLEICH
        and abs(abs(grad[-1] - grad[0]) - 360.0) < 1e-6
    )


def _abstand(punkt, a, r, grad):
    """Wie weit (mm, grob) die Stellen (a, r, φ) von `punkt` (vierachs_bahn.Punkt) liegen: längs
    plus der Bogen auf dem Radius – um ganze Umdrehungen bereinigt."""
    dphi = np.radians((grad - punkt.phi + 180.0) % 360.0 - 180.0)
    return np.abs(a - punkt.a) + np.abs(dphi) * np.maximum(r, 1.0)
