# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Bahn „Entgraten“ im Quader (W-006 S3, 4.1 Punkt 8): An den Oberkanten gewählter Wände
fährt ein Fasenfräser entlang und bricht sie mit einer Fase – wie „Rundum entgraten“, nur von
oben.

- Kanten (ketten()): die waagerechten Oberkanten der gewählten Wände (kontur_bahn.waende:
  senkrecht, eben, rund oder frei geformt, auch Bohrungen), an denen oben eine ebene Fläche nach
  oben anschließt – dort steht der Grat. Eine gewählte ebene Fläche nach oben gibt die Wände,
  die an ihren Kanten hinab gehen: die Oberseite einer Platte ihre Außenkanten und die Ränder
  ihrer Taschen und Bohrungen. Kanten derselben Höhe verbinden sich zu Ketten – geschlossen
  rundum oder offen, wie die Unterkanten bei der Kontur.
- Die Fase (wie FreeCADs „Deburr“): `breite` auf der Oberseite; der Kegel des Fasenfräsers
  (Spitzenwinkel α, Spitze Ø d) steht breite / tan(α/2) + `tiefer` unter der Kante, seine Achse
  d/2 + tiefer · tan(α/2) neben der Wand – so schneidet der Kegel die Fase genau so breit, und
  die Spitze berührt die Wand nicht.
- Je Kette eine Bahn: der Versatz um diesen Abstand auf der freien Seite (Ecken außen werden
  Bögen), im Gleichlauf – das Material rechts der Fahrtrichtung –, tangential hinein und
  heraus, hinab senkrecht in der Luft neben der Wand; eine geschlossene ab der Mitte der
  längsten Geraden in einem Zug. Die Hüllfläche des Kegels – gegen das Teil ohne die Wände und
  ohne die Flächen an ihren waagerechten Kanten – hält die Bahn vor Absätzen und nicht
  gewählten Wänden an.
- Nie unter die Unterkante der Wand: Ist die Wand niedriger als Fase plus `tiefer`, bleibt die
  Spitze knapp über ihrem Boden; ist sie niedriger als die Fase, bleibt die Kette aus.
- **Gezeichnete Fasen** (fasen()): Hat das Modell die Fase schon – eine schräge Fläche (eben
  oder Kegel), unten an Wänden, oben an einer ebenen Fläche nach oben –, ist ihre Kette die
  Unterkante der Fase, auf die Höhe der Oberseite gehoben (dort läge die Kante ohne Fase);
  Breite und Winkel kommen aus dem Modell. Der Kegel des Fräsers muss ihren Winkel haben
  (±FASE_WINKEL) – dann liegt er genau auf ihr. Eine gewählte ebene Fläche nach oben bringt
  auch die Fasen an ihren Kanten mit.

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field

import numpy as np

from . import bahn as bn
from . import einheiten
from . import hoehenfeld as hf
from . import kontur_bahn as kb
from . import vierachs_bahn as vb
from .sprache import tr

BREITE = 0.3  # mm – die Fasenbreite, wenn nichts anderes gesagt ist (wie „Rundum entgraten“)
TIEFER = 0.5  # mm – so viel tiefer als die Fase steht die Spitze (wie FreeCADs „Deburr“)
EINFAHRT = 2.0  # mm – der Viertelkreis hinein und heraus, wenn nichts anderes gesagt ist
SCHRITT = kb.SCHRITT  # mm – Raster längs der Bahn und für die Hüllfläche
VORSCHAU_SCHRITT = kb.VORSCHAU_SCHRITT
MINDEST_ABSTAND = 0.01  # mm – so nah höchstens fährt die Achse an der Wand (spitzer Fräser)
GLEICH = kb.GLEICH
FASE_WINKEL = 1.0  # Grad – so genau muss der Kegel zu einer gezeichneten Fase passen


@dataclass(frozen=True)
class Entgratwerte:
    """Was das Entgraten braucht; Längen in mm, z nach oben im Job."""

    form: object  # fraeserform.Form des Fasenfräsers
    spitzenwinkel: float  # Grad – der ganze Winkel des Kegels
    spitze: float  # Ø der Spitze (0: spitz)
    breite: float  # so breit wird die Fase auf der Oberseite
    tiefer: float  # so viel tiefer als die Fase steht die Spitze
    sicher: float  # z für den Eilgang über allem
    einfahrradius: float = None  # der Viertelkreis hinein und heraus; None: EINFAHRT
    sicherheit: float = vb.SICHERHEIT  # so weit über der Kante endet der Eilgang hinab


@dataclass(frozen=True)
class Kette:
    """Oberkanten mit Grat, zu einer Kette verbunden (ketten())."""

    kontur: object  # kontur_bahn.Kontur: der Draht der Oberkanten, z_unten = z_oben = z_kante
    z_kante: float
    z_boden: float  # die tiefste Unterkante der Wände der Kette
    breite: float = 0.0  # gezeichnete Fase: so breit (mm); 0 – die Breite der Operation
    winkel: float = 0.0  # gezeichnete Fase: ihr Winkel zur Senkrechten (Grad); 0 – keine


@dataclass(frozen=True)
class Fase:
    """Eine gezeichnete Fase an einer Oberkante (_fase())."""

    nummer: int  # die schräge Fläche, 0 …
    z_unten: float  # ihre Unterkante – oben an den Wänden
    z_oben: float  # ihre Oberkante – an der Fläche nach oben
    winkel: float  # Grad zur Senkrechten
    unten: tuple  # ((Kante, [Nummer der Wand, …]), …) – die Unterkanten
    oben: tuple  # die Nummern der Flächen nach oben an der Oberkante

    @property
    def breite(self):
        return (self.z_oben - self.z_unten) * math.tan(math.radians(self.winkel))


@dataclass
class Entgratbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    ketten: int  # so viele Ketten gefahren
    ausgelassen: int  # so viele nicht: zu niedrig, oder der Fräser kommt nirgends hin
    bahnen: int  # Läufe über alle Ketten (je mit Ein- und Ausfahren)
    z_min: float  # die tiefste Spitze (mm)
    laenge: float  # mm im Vorschub
    modell: tuple = ()  # die Breiten der gefahrenen gezeichneten Fasen (mm), aufsteigend


@dataclass
class _Stand:
    punkte: list = field(default_factory=list)
    ketten: int = 0
    ausgelassen: int = 0
    bahnen: int = 0
    z_min: float = math.inf
    laenge: float = 0.0
    modell: set = field(default_factory=set)


# --- Kanten und Ketten ------------------------------------------------------------------------


def _nach_oben(flaeche):
    """Ist die Fläche eben, waagerecht und schaut nach oben?"""
    bb = flaeche.BoundBox
    if bb.ZMax - bb.ZMin > kb.NAH:
        return False
    try:
        u0, u1, v0, v1 = flaeche.ParameterRange
        n = flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    except Exception:  # OCC: keine Parameter
        return False
    return n.z > 1.0 - 1e-6


def waende(form, namen):
    """[kontur_bahn.Wand] – die gewählten Wände (`namen`: „Face3“ …) und die, die an den Kanten
    gewählter ebener Flächen nach oben hinab gehen."""
    import Part

    from . import vierachs_flaechen as vf

    flaechen = form.Faces
    index = {f.hashCode(): i for i, f in enumerate(flaechen)}
    nummern = set()
    for fase in _gewaehlte_fasen(form, namen, index):
        for _kante, unter in fase.unten:
            nummern.update(unter)
    for nummer in vf.nummern(namen):
        if nummer >= len(flaechen):
            continue
        flaeche = flaechen[nummer]
        if kb.ist_wand(flaeche):
            nummern.add(nummer)
            continue
        if not _nach_oben(flaeche):
            continue
        z = flaeche.BoundBox.ZMax
        for kante in flaeche.Edges:
            for nachbar in form.ancestorsOfType(kante, Part.Face):
                i = index.get(nachbar.hashCode())
                if i is None or i == nummer or i in nummern:
                    continue
                if abs(flaechen[i].BoundBox.ZMax - z) <= kb.NAH and kb.ist_wand(flaechen[i]):
                    nummern.add(i)
    return kb.waende(form, [f"Face{i + 1}" for i in sorted(nummern)])


def _oberkanten(form, wand, index):
    """Die waagerechten Oberkanten der Wand, an denen oben eine ebene Fläche nach oben anschließt
    – dort steht der Grat."""
    import Part

    flaechen = form.Faces
    ergebnis = []
    for kante in wand.flaeche.Edges:
        if not kb._waagerecht(kante, wand.z_oben):
            continue
        for nachbar in form.ancestorsOfType(kante, Part.Face):
            i = index.get(nachbar.hashCode())
            if i is not None and i != wand.nummer and _nach_oben(flaechen[i]):
                ergebnis.append(kante)
                break
    return ergebnis


def hat_oberkanten(form, name):
    """Hat die Fläche `name` Oberkanten mit Grat – als Wand, oder als ebene Fläche nach oben mit
    Wänden, die an ihren Kanten hinab gehen?"""
    index = {f.hashCode(): i for i, f in enumerate(form.Faces)}
    return any(_oberkanten(form, w, index) for w in waende(form, [name]))


def ketten(form, namen):
    """[Kette] – die Oberkanten mit Grat an den Wänden aus waende(), je Höhe zu Ketten verbunden
    (Part.sortEdges), die höchsten zuerst. ValueError mit einem Satz, wenn es keine gibt."""
    import Part

    index = {f.hashCode(): i for i, f in enumerate(form.Faces)}
    gruppen = []  # [(z, [(Kante, Wand)])]
    for wand in waende(form, namen):
        for kante in _oberkanten(form, wand, index):
            z = wand.z_oben
            gruppe = next((g for g in gruppen if abs(g[0] - z) <= kb.NAH), None)
            if gruppe is None:
                gruppe = (z, [])
                gruppen.append(gruppe)
            gruppe[1].append((kante, wand))
    ergebnis = []
    for z, paare in gruppen:
        wand_der_kante = {kb._schluessel(k): w for k, w in paare}
        for kette in Part.sortEdges([k for k, _w in paare]):
            beteiligt = [
                wand_der_kante[s] for s in (kb._schluessel(k) for k in kette) if s in wand_der_kante
            ]
            if not beteiligt:
                continue
            laengste = max(kette, key=lambda k: k.Length)
            wand = wand_der_kante.get(kb._schluessel(laengste), beteiligt[0])
            stelle, normale = kb._freie_seite(wand, laengste)
            draht = Part.Wire(kette)
            namen_der_waende = sorted({w.name for w in beteiligt}, key=lambda n: int(n[4:]))
            kontur = kb.Kontur(
                draht, z, z, draht.isClosed(), stelle, normale, tuple(namen_der_waende)
            )
            ergebnis.append(Kette(kontur, float(z), min(w.z_unten for w in beteiligt)))
    ergebnis.extend(fasen(form, namen))
    if not ergebnis:
        raise ValueError(tr("eg.fehler.keine"))
    return sorted(ergebnis, key=lambda k: -k.z_kante)


# --- Gezeichnete Fasen ------------------------------------------------------------------------


def _fase(form, nummer, index):
    """Die Fläche `nummer` als gezeichnete Fase (Fase) – schräg nach oben (eben oder Kegel),
    unten an Wänden, oben an einer ebenen Fläche nach oben; None, wenn sie keine ist."""
    import Part

    flaeche = form.Faces[nummer]
    if not isinstance(flaeche.Surface, (Part.Plane, Part.Cone)):
        return None
    bb = flaeche.BoundBox
    if bb.ZMax - bb.ZMin <= kb.NAH or kb.ist_wand(flaeche):
        return None
    try:
        u0, u1, v0, v1 = flaeche.ParameterRange
        n = flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    except Exception:  # OCC: keine Parameter
        return None
    if not 0.02 < n.z < 0.98:
        return None
    unten, oben = [], set()
    for kante in flaeche.Edges:
        kbb = kante.BoundBox
        if kbb.ZMax - kbb.ZMin > kb.NAH:
            continue  # eine schräge Kante: das Ende der Fase
        nachbarn = [index.get(f.hashCode()) for f in form.ancestorsOfType(kante, Part.Face)]
        nachbarn = [i for i in nachbarn if i is not None and i != nummer]
        if abs(kbb.ZMax - bb.ZMin) <= kb.NAH:
            waende_ = [i for i in nachbarn if kb.ist_wand(form.Faces[i])]
            if waende_:
                unten.append((kante, waende_))
        elif abs(kbb.ZMin - bb.ZMax) <= kb.NAH:
            oben.update(i for i in nachbarn if _nach_oben(form.Faces[i]))
    if not unten or not oben:
        return None
    winkel = math.degrees(math.asin(min(max(n.z, -1.0), 1.0)))
    return Fase(nummer, bb.ZMin, bb.ZMax, winkel, tuple(unten), tuple(sorted(oben)))


def hat_fasen(form, name):
    """Bringt die Fläche `name` gezeichnete Fasen mit – sie ist eine, oder eine ebene Fläche nach
    oben mit Fasen an ihren Kanten?"""
    return bool(_gewaehlte_fasen(form, [name]))


def ist_fase(form, name):
    """Ist die Fläche `name` eine gezeichnete Fase an einer Oberkante?"""
    from . import vierachs_flaechen as vf

    index = {f.hashCode(): i for i, f in enumerate(form.Faces)}
    return any(
        _fase(form, nummer, index) is not None
        for nummer in vf.nummern([name])
        if nummer < len(form.Faces)
    )


def _gewaehlte_fasen(form, namen, index=None):
    """[Fase] – die gewählten gezeichneten Fasen und die an den Kanten gewählter ebener Flächen
    nach oben."""
    import Part

    from . import vierachs_flaechen as vf

    flaechen = form.Faces
    if index is None:
        index = {f.hashCode(): i for i, f in enumerate(flaechen)}
    kandidaten = set()
    for nummer in vf.nummern(namen):
        if nummer >= len(flaechen):
            continue
        kandidaten.add(nummer)
        if _nach_oben(flaechen[nummer]):
            for kante in flaechen[nummer].Edges:
                for nachbar in form.ancestorsOfType(kante, Part.Face):
                    i = index.get(nachbar.hashCode())
                    if i is not None and i != nummer:
                        kandidaten.add(i)
    fasen_ = (_fase(form, i, index) for i in sorted(kandidaten))
    return [f for f in fasen_ if f is not None]


def fasen(form, namen):
    """[Kette] – die gezeichneten Fasen (_gewaehlte_fasen): ihre Unterkanten je Höhe und Winkel zu
    Ketten verbunden, auf die Höhe der Oberseite gehoben – dort läge die Kante ohne Fase; Breite
    und Winkel aus dem Modell."""
    import FreeCAD
    import Part

    index = {f.hashCode(): i for i, f in enumerate(form.Faces)}
    gruppen = {}  # (z_unten, z_oben, winkel) → [(Kante, Wand)]
    for fase in _gewaehlte_fasen(form, namen, index):
        schluessel = (round(fase.z_unten, 4), round(fase.z_oben, 4), round(fase.winkel, 2))
        for kante, unter in fase.unten:
            wand = next(iter(kb.waende(form, [f"Face{unter[0] + 1}"])), None)
            if wand is not None:
                gruppen.setdefault(schluessel, []).append((kante, wand))
    ergebnis = []
    for (z_unten, z_oben, winkel), paare in gruppen.items():
        wand_der_kante = {kb._schluessel(k): w for k, w in paare}
        for kette in Part.sortEdges([k for k, _w in paare]):
            beteiligt = [
                wand_der_kante[s] for s in (kb._schluessel(k) for k in kette) if s in wand_der_kante
            ]
            if not beteiligt:
                continue
            laengste = max(kette, key=lambda k: k.Length)
            wand = wand_der_kante.get(kb._schluessel(laengste), beteiligt[0])
            stelle, normale = kb._freie_seite(wand, laengste)
            draht = Part.Wire(kette)
            draht.translate(FreeCAD.Vector(0, 0, z_oben - z_unten))
            namen_der_waende = sorted({w.name for w in beteiligt}, key=lambda n: int(n[4:]))
            kontur = kb.Kontur(
                draht, z_oben, z_oben, draht.isClosed(), stelle, normale, tuple(namen_der_waende)
            )
            breite = (z_oben - z_unten) * math.tan(math.radians(winkel))
            ergebnis.append(
                Kette(
                    kontur,
                    float(z_oben),
                    min(w.z_unten for w in beteiligt),
                    float(breite),
                    float(winkel),
                )
            )
    return ergebnis


# --- Die Fase ---------------------------------------------------------------------------------


def masse(breite, tiefer, spitzenwinkel, spitze, radius):
    """(Tiefe der Fase an der Wand, tiefer, so weit schneidet der Kegel hinauf) für den
    Fasenfräser: Die Fase reicht breite / tan(α/2) an der Wand hinab; `tiefer` höchstens so
    viel, dass der Kegel noch über die Kante reicht. ValueError, wenn die Fase breiter ist,
    als der Kegel schneidet."""
    if not 0 < spitzenwinkel < 180:
        raise ValueError(tr("eg.fehler.form"))
    tan = math.tan(math.radians(spitzenwinkel / 2))
    kegel = (radius - min(max(spitze, 0.0), 2 * radius) / 2) / tan
    fase = breite / tan
    if fase > kegel - 1e-6:
        hoechstens = (
            f"{einheiten.text(kegel * tan, einheiten.LAENGE)} {einheiten.einheit(einheiten.LAENGE)}"
        )
        raise ValueError(tr("eg.fehler.zu_breit", hoechstens=hoechstens))
    return fase, min(max(tiefer, 0.0), kegel - fase), kegel


def abstand_zur_wand(tiefer, spitzenwinkel, spitze):
    """So weit (mm) steht die Achse neben der Wand: d/2 + tiefer · tan(α/2) – dann berührt der
    Kegel die Wand genau am unteren Rand der Fase."""
    tan = math.tan(math.radians(spitzenwinkel / 2))
    return max(spitze / 2 + tiefer * tan, MINDEST_ABSTAND)


# --- Die Bahn ---------------------------------------------------------------------------------


def planen(netz, werte, ketten_, schritt=SCHRITT, netz_fern=None):
    """Die Bahn „Entgraten“ (Entgratbahn) an den Ketten `ketten_` ([Kette]) mit den Werten
    `werte`; `netz` ist das Teil ohne die Wände und ihre Nachbarn an waagerechten Kanten
    (hoehenfeld.netz_ohne mit kontur_bahn.ohne_flaechen()), `netz_fern` das Teil nur ohne die
    Wände – es zählt weiter weg von der Kante. ValueError mit einem Satz, wenn es nicht geht."""
    w = werte
    if not ketten_:
        raise ValueError(tr("eg.fehler.keine"))
    if w.breite <= 0 and any(k.breite <= 0 for k in ketten_):
        raise ValueError(tr("eg.fehler.breite"))
    radius = float(w.form.radius)
    for k in ketten_:
        if k.winkel > 0 and abs(k.winkel - w.spitzenwinkel / 2) > FASE_WINKEL:
            raise ValueError(
                tr(
                    "eg.fehler.winkel",
                    fase=f"{2 * k.winkel:.0f}",
                    fraeser=f"{w.spitzenwinkel:.0f}",
                )
            )
    r_ein = w.einfahrradius if w.einfahrradius and w.einfahrradius > 0 else EINFAHRT
    zugabe = netz.toleranz + vb.RAND
    geformt = w.form.mit_aufmass(netz.toleranz)
    toleranz = netz.toleranz
    mit_kette = [(k, kb._kette(k.kontur, toleranz, 2 * schritt)) for k in ketten_]
    alle_waende = [(kx, ky, k.kontur.geschlossen, k.z_kante) for k, (kx, ky) in mit_kette]
    st = _Stand()
    for k, kette in mit_kette:
        breite = k.breite if k.breite > 0 else w.breite
        fase, tiefer, _kegel = masse(breite, w.tiefer, w.spitzenwinkel, w.spitze, radius)
        # Nie unter die Unterkante der Wand: Unter ihr liegt ein Boden, den die Hüllfläche nahe
        # der Kante nicht sieht.
        tiefe = min(fase + tiefer, k.z_kante - k.z_boden - 2 * zugabe)
        if tiefe < fase - 1e-6:
            st.ausgelassen += 1
            continue
        abstand = abstand_zur_wand(max(tiefe - fase, 0.0), w.spitzenwinkel, w.spitze)
        lage = k.z_kante - tiefe
        versatz = kb._versatz(k.kontur, abstand, toleranz, schritt)
        if versatz is None:
            st.ausgelassen += 1
            continue
        segmente, proben = versatz
        rand = 2 * r_ein + abstand + radius + schritt
        huelle = kb._Huelle(
            netz,
            netz_fern,
            geformt,
            zugabe,
            float(proben.x.min()) - rand,
            float(proben.x.max()) + rand,
            float(proben.y.min()) - rand,
            float(proben.y.max()) + rand,
            schritt,
            kette,
            abstand + breite + 2 * schritt,
            alle_waende,
        )
        if _bahnen(st, k, segmente, proben, lage, huelle, abstand, r_ein, w):
            st.ketten += 1
            st.z_min = min(st.z_min, lage)
            if k.winkel > 0:
                st.modell.add(round(k.breite, 3))
        else:
            st.ausgelassen += 1
    if st.ketten == 0:
        raise ValueError(tr("eg.fehler.nichts"))
    return Entgratbahn(
        st.punkte,
        st.ketten,
        st.ausgelassen,
        st.bahnen,
        st.z_min,
        st.laenge,
        tuple(sorted(st.modell)),
    )


def _erlaubt(huelle, x, y, lage):
    """Darf die Spitze dort auf `lage`? Nur, wo die Hüllfläche mit Zugabe darunter liegt – ohne
    die Ausnahme der Kontur für Stellen auf dem Ziel (dort ist die Unterkante der Wand das Ziel,
    hier liegt die Spitze darüber)."""
    return huelle.erlaubt(x, y, lage, -math.inf)


def _bahnen(st, k, segmente, proben, lage, huelle, abstand, r_ein, w):
    """Die Bahn einer Kette: wo die Hüllfläche es erlaubt – geschlossen in einem Zug ab der Mitte
    der längsten Geraden, sonst in Läufen. Gibt die Zahl der Läufe zurück."""
    x, y = proben.x, proben.y
    n = len(x)
    if n < 2:
        return 0
    drin = _erlaubt(huelle, x, y, lage)
    if not drin.any():
        return 0
    laeufe = []
    if k.kontur.geschlossen and drin.all():
        start = kb._startstelle(segmente, proben)
        laeufe.append(np.arange(start, start + n + 1) % n)
    elif k.kontur.geschlossen:
        luecke = int(np.flatnonzero(~drin)[0])
        for von, bis in vb._stuecke(np.roll(drin, -luecke)):
            laeufe.append((np.arange(von, bis + 1) + luecke) % n)
    else:
        for von, bis in vb._stuecke(drin):
            laeufe.append(np.arange(von, bis + 1))
    anzahl = 0
    for stellen in laeufe:
        if len(stellen) < 2:
            continue
        _lauf(st, k, segmente, proben, stellen, lage, huelle, abstand, r_ein, w)
        anzahl += 1
    return anzahl


def _lauf(st, k, segmente, proben, stellen, lage, huelle, abstand, r_ein, w):
    """Ein Lauf: Eilgang über den Anfang, knapp über die Kante, senkrecht hinab in der Luft
    neben der Wand, tangential hinein, die Kante entlang, tangential heraus, hinauf."""
    x, y = proben.x[stellen], proben.y[stellen]
    p0 = (float(x[0]), float(y[0]))
    p1 = (float(x[-1]), float(y[-1]))
    t0 = kb._einheit(x[1] - x[0], y[1] - y[0])
    t1 = kb._einheit(x[-1] - x[-2], y[-1] - y[-2])
    mindest = abstand - kb.WAND_SPIEL

    def frei(qx, qy):
        return bool(_erlaubt(huelle, qx, qy, lage).all()) and bool(
            (huelle.abstand_zur_wand(qx, qy, lage) >= mindest).all()
        )

    ein = kb._anfahrt(p0, t0, r_ein, r_ein, frei, hinein=True)
    aus = kb._anfahrt(p1, t1, r_ein, r_ein, frei, hinein=False)
    start = ein.aussen if ein is not None else p0
    punkte = st.punkte
    punkte.append(bn.Punkt(True, start[0], start[1], w.sicher))
    knapp = min(w.sicher, k.z_kante + w.sicherheit)
    if knapp < w.sicher - 1e-9:
        punkte.append(bn.Punkt(True, start[0], start[1], knapp))
    laenge = abs(knapp - lage)
    punkte.append(bn.Punkt(False, start[0], start[1], lage, True))
    if ein is not None:
        laenge += kb._anfahrt_punkte(punkte, ein, lage, hinein=True)
    laenge += kb._bahnpunkte(punkte, segmente, proben, stellen, lage, False, 1.0, abstand)
    if aus is not None:
        laenge += kb._anfahrt_punkte(punkte, aus, lage, hinein=False)
    letzter = punkte[-1]
    punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
    st.laenge += laenge
    st.bahnen += 1


def netze(form, flaechen, toleranz=hf.TOLERANZ):
    """(netz_nah, netz_fern) für planen(): das Teil ohne die Wände und ihre Nachbarn an
    waagerechten Kanten, und nur ohne die Wände."""
    waende_ = waende(form, flaechen)
    fasen_ = _gewaehlte_fasen(form, flaechen)
    schraeg = {f"Face{f.nummer + 1}" for f in fasen_}
    oben = {f"Face{i + 1}" for f in fasen_ for i in f.oben}
    nah = set(kb.ohne_flaechen(form, waende_)) | schraeg | oben
    fern = {w.name for w in waende_} | schraeg
    return hf.netze_ohne(form, [_sortiert(nah), _sortiert(fern)], toleranz)


def _sortiert(namen):
    return sorted(namen, key=lambda n: int(n[4:]))
