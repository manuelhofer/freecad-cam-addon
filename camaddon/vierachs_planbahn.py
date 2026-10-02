# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Bahn „Plan indexiert“ (Spezifikation W-003, Stufe V4c; W-006, 4.3.2): Eine ebene Fläche
längs der Stange wird gefräst wie beim Planfräsen – die Rundachse steht so, dass die Fläche
zum Werkzeug schaut, der Fräser mit ebener Stirn fährt Zeilen längs der Achse und rückt quer
(bei C mit dem Y) um den Zeilenabstand weiter; in Lagen von oben bis auf die Fläche plus
Aufmaß.

Manuel (2026-09-29): „bei einer maschine mit y achse kann man ja auch diese verfahren um
eventuelle stellen besser zu erreichen“ – eine Abflachung, eine Schlüsselfläche, der Boden
einer Nut: Mit dem Fräser auf dem Strahl von der Achse (Spirale, hin und her, Linien) steht
seine Stirn schräg zur Fläche, am Rand und in den Ecken bleibt etwas stehen; so wird sie eben.

- Jede gewählte ebene Fläche, deren Außennormale quer zur Stange von der Achse weg zeigt
  (ebenen()), kommt einmal dran: die Rundachse auf den Winkel ihrer Normale, dann die Lagen.
- Lagen: von dem, was über der Fläche steht (die Stange, oder nach dem Schruppen der Rest), in
  gleichen Schritten von höchstens der Zustellung bis auf ihre Tiefe plus Aufmaß.
- Zeilen je Lage: quer von Rand zu Rand der Fläche – der ebene Teil der Stirn reicht bis an den
  Rand –, höchstens den Zeilenabstand auseinander; eine in der Mitte, wenn die Fläche schmaler
  ist als die Stirn. Zeilen, die in einer Lage nur Luft träfen (neben der Stange), fallen weg.
- Längs reicht eine Zeile über die Fläche hinaus, so weit der Fräser breit ist, plus Überlauf;
  wo die Hüllfläche (vierachs_huelle.je_versatz – das Teil ohne diese Fläche, mit dem Versatz
  der Zeile) höher liegt als die Lage, etwa an einer Wand oder am Zylinder vor der Fläche, hält
  sie an. Über das Ende der Fläche hinaus ragt die Stirn nur, wo nichts höher steht als die
  Fläche selbst – ein Absatz nach unten, das Ende der Stange –, nicht über den Zylinder neben
  der Wand, auch wenn eine Lage ihn gerade noch streifen dürfte (Ø 20, Lage 10: die äußeren
  Zeilen liefen 1,5 mm weiter als die mittlere); der ist Sache der Rundum-Bahnen. Hin und her
  (vierachs_bahn._fahrten): Am Ende einer Zeile geht es in der Tiefe quer zur nächsten, wo die
  dort auch fräst; sonst hebt der Fräser ab.
- Hinein wie beim Schruppen: senkrecht mit dem Eintauchvorschub, wo die Zeile vor der Stange
  beginnt, sonst über die Rampe mit dem Eintauchwinkel längs der Zeile.

- **Nut** (Passfedernut, P-2026-10-02-05): Ist die Fläche der Grund eines Langlochs (zwei
  parallele Wände, an den Enden Halbkreise – nuten()), fräst sie die Bahn „Nut“ des Quaders
  (nut_bahn: in voller Breite mit der Zickzack-Rampe, sonst die Trochoide, zuletzt die Wand
  rundum) – gerechnet im Rahmen der Fläche (x längs, z ihre Normale, y = z × x), zurück mit
  a = x, Höhe = z, Versatz = −y und der Rundachse fest. Mit Zeilen kam der Fräser nicht an die
  Enden (4 mm blieben stehen) und mit dem Fräser so breit wie die Nut gar nicht hinein.

- **Querbohrung** (P-2026-10-02-07): Eine gewählte Bohrung quer zur Stange (eine ganze
  Zylinderfläche, ihre Achse rechtwinklig zur Stange, das Material außen – bohrungen()) fräst
  die Bahn „Bohrung fräsen“ des Quaders (bohrung_bahn: in der Helix hinab, Ringe, die Wand
  rundum) im Rahmen der Bohrung – die Rundachse auf ihre Öffnung, die Spitze längs ihrer Achse,
  quer versetzt mit dem Y, wenn sie nicht durch die Mitte geht. Eine durchgehende von beiden
  Seiten je bis zur Mitte der Stange.

Gerechnet wird in (a, Höhe, Winkel, Versatz) wie vierachs_bahn.Punkt – die Höhe längs der
Werkzeugachse, der Winkel der der Rundachse, der Versatz quer. Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import fraeserform as ff
from . import vierachs_bahn as vb
from . import vierachs_huelle as vh
from .sprache import tr

GERADE = 1e-6  # so wenig darf eine Normale längs der Stange zeigen
LUFT = vb.RING_LUFT  # mm – so weit bleibt eine Zeile vom Rand der Fläche weg (wie der Ring)
UEBERLAUF_LAENGS = vb.UEBERLAUF_ZUGABE  # mm – so weit über Fläche und Fräser hinaus längs
TOLERANZ = vb.TOLERANZ_SCHLICHTEN  # mm – so fein wird das Teil vernetzt: Wände genau
VORSCHAU_TOLERANZ = 0.05  # mm – für die Vorschau im Assistenten
SEHNE = 0.005  # mm – so weit weicht eine Sehne höchstens vom Bogen der Nut ab
NUT_AE_ANTEIL = 0.25  # × D: so weit rückt die Trochoide in der Nut höchstens je Kreis vor
NUT_LUFT = 0.01  # mm – so weit bleibt der Fräser in der Nut von den Enden und Wänden weg


@dataclass(frozen=True)
class Ebene:
    """Eine ebene Fläche längs der Stange: wohin sie schaut und wo sie liegt – längs (a) und
    quer (q) in ihrem Rahmen: die Höhe längs ihrer Normale, quer = längs × Normale."""

    name: str  # „Face3“
    phi: float  # Grad – der Winkel der Außennormale: dorthin stellt die Rundachse die Fläche
    tiefe: float  # mm – ihr Abstand von der Achse: die Höhe der Spitze auf ihr
    a_von: float
    a_bis: float
    q_von: float
    q_bis: float


def ebenen(form, laengs, radial, namen, toleranz=VORSCHAU_TOLERANZ):
    """[Ebene] – die Flächen `namen` („Face3“ …) von `form` (Part.Shape), die eben sind und
    deren Außennormale quer zur Stangenachse von der Achse weg zeigt. Andere zählen nicht:
    Zylinder, eine Stirn oder ein Absatz quer zur Achse, eine Ebene, die zur Achse schaut. Die
    Ausdehnung längs und quer kommt aus der Vernetzung der Fläche (`toleranz`)."""
    from . import vierachs_flaechen as vf
    from . import vierachs_rohteil as vr

    l_, u_, v_ = vh.rahmen(laengs, radial)
    ergebnis = []
    for nummer in vf.nummern(namen):
        if nummer >= len(form.Faces):
            continue
        flaeche = form.Faces[nummer]
        if not vr.ist_eben(flaeche):
            continue
        normale = vr.aussennormale(flaeche)
        n = np.array([normale.x, normale.y, normale.z], dtype=float)
        if abs(float(n @ l_)) > GERADE:
            continue
        punkte, _dreiecke = flaeche.copy().tessellate(toleranz)
        if not punkte:
            continue
        p = np.array([[pt.x, pt.y, pt.z] for pt in punkte], dtype=float)
        tiefe = float(np.mean(p @ n))
        if tiefe <= GERADE:
            continue  # schaut zur Achse hin: von außen nicht zu fräsen
        a = p @ l_
        q = p @ np.cross(l_, n)
        phi = math.degrees(math.atan2(float(n @ v_), float(n @ u_)))
        ergebnis.append(
            Ebene(
                f"Face{nummer + 1}",
                phi,
                tiefe,
                float(a.min()),
                float(a.max()),
                float(q.min()),
                float(q.max()),
            )
        )
    return ergebnis


def netz_ohne(form, namen, toleranz=TOLERANZ):
    """Das Netz des Teils ohne die Flächen `namen` (vierachs_huelle.Netz): Dagegen rechnet die
    Hüllfläche – die Fläche selbst gibt die Tiefe vor, das Netz nur, was sonst im Weg ist."""
    from . import vierachs_flaechen as vf

    fnetz = vf.vernetze(form, toleranz)
    bleibt = ~np.isin(fnetz.flaeche, np.asarray(vf.nummern(namen), dtype=np.int64))
    return vh.Netz(fnetz.netz.punkte, fnetz.netz.dreiecke[bleibt], toleranz)


@dataclass(frozen=True)
class Planwerte:
    """Was „Plan indexiert“ braucht; Längen in mm, a längs der Stangenachse im Job."""

    form: object  # fraeserform.Form des Fräsers – mit ebener Stirn (Schaft-, Torus-, Planfräser)
    stange_radius: float
    zustellung: float  # ap: höchstens so tief je Lage, längs der Flächennormale
    zeilenabstand: float  # ae: höchstens so weit rücken die Zeilen quer
    aufmass: float  # bleibt auf der Fläche stehen (0: fertig)
    a_stange_vorne: float
    a_futter: float
    sicherheit: float = vb.SICHERHEIT
    ueberlauf: float = None  # längs über die Fläche hinaus (Mitte des Fräsers); None: Vorschlag
    abstand_futter: float = vb.ABSTAND_FUTTER
    halter: float = 0.0  # wie bei vierachs_bahn.Schruppwerte
    eintauchwinkel: float = vb.EINTAUCHWINKEL  # Grad, für die Rampe ins Material
    rest: tuple = None  # (a, φ rad, r) nach dem Schruppen (restmaterial.Stange); None: Stange


@dataclass
class Planbahn:
    """Ergebnis von planen()."""

    punkte: list  # [vierachs_bahn.Punkt], der erste ist der Start (Eilgang, vor der Stange)
    flaechen: int  # so viele Flächen
    lagen: int  # Lagen, über alle Flächen
    zeilen: int  # Zeilen, über alle Flächen und Lagen
    r_min: float  # die tiefste Spitze: Höhe längs der Werkzeugachse (mm)
    hinten_frei: float = 0.0  # wie bei vierachs_bahn.Bahn
    nuten: int = 0  # so viele Flächen davon als Nut (nut_bahn)
    bohrungen: int = 0  # so viele Bohrungen quer (bohrung_bahn), je Seite gezählt


def ebener_radius(form):
    """Der Radius des ebenen Teils der Stirn (mm): der Schaftfräser ganz, der Torusfräser bis
    zum Eckradius, der Planfräser bis zu den Platten – 0 bei Kugel- und Kegelspitze."""
    erstes = form.stuecke[0]
    return float(erstes.rho_bis) if erstes.art == ff.EBEN else 0.0


def nuten(form, laengs, radial, flaechen):
    """{Name: [nut_bahn.Nut]} – die Ebenen `flaechen` (ebenen()), die der Grund einer Nut sind:
    im Rahmen der Ebene (_rahmen) erkennt nut_bahn das Langloch wie im Quader."""
    from . import nut_bahn as nb

    ergebnis = {}
    for ebene in flaechen:
        lokal = form.copy()
        lokal.transformShape(_rahmen(laengs, radial, ebene))
        gefunden = nb.nuten(lokal, [ebene.name])
        if gefunden:
            ergebnis[ebene.name] = gefunden
    return ergebnis


def bohrungen(form, laengs, radial, namen):
    """[(Ebene, bohrung_bahn.Bohrung)] – die Flächen `namen` von `form`, die eine Bohrung quer zur
    Stange sind: eine ganze Zylinderfläche, ihre Achse rechtwinklig zur Stange, das Material
    außen. Je Seite, von der sie gefräst wird, ein Paar: die Ebene (φ zur Öffnung, die Tiefe ihr
    Grund, längs und quer ihr Umriss) und die Bohrung im Rahmen der Ebene (_rahmen) – eine
    durchgehende von beiden Seiten, je bis zur Mitte der Stange."""
    import dataclasses

    import Part

    from . import bohrung_bahn as bb
    from . import vierachs_flaechen as vf

    l_, u_, v_ = vh.rahmen(laengs, radial)
    ergebnis = []
    for nummer in vf.nummern(namen):
        if nummer >= len(form.Faces):
            continue
        flaeche = form.Faces[nummer]
        zylinder = flaeche.Surface
        if not isinstance(zylinder, Part.Cylinder):
            continue
        d = np.array(tuple(zylinder.Axis), dtype=float)
        if abs(float(d @ l_)) > GERADE:
            continue  # längs der Stange: keine Querbohrung
        mitte = np.array(tuple(zylinder.Center), dtype=float)
        punkte, _dreiecke = flaeche.copy().tessellate(VORSCHAU_TOLERANZ)
        if not punkte:
            continue
        p = np.array([[pt.x, pt.y, pt.z] for pt in punkte], dtype=float)
        t = (p - mitte) @ d
        enden = (mitte + d * float(t.min()), mitte + d * float(t.max()))
        weit = [float(np.linalg.norm(e - l_ * float(e @ l_))) for e in enden]
        richtungen = []
        for ende, gegen in ((0, 1), (1, 0)):
            if weit[ende] >= weit[gegen] - VORSCHAU_TOLERANZ:
                n = enden[ende] - enden[gegen]
                n = n - l_ * float(n @ l_)
                richtungen.append(n / np.linalg.norm(n))
        durch = len(richtungen) == 2
        for n in richtungen:
            phi = math.degrees(math.atan2(float(n @ v_), float(n @ u_)))
            name = f"Face{nummer + 1}"
            vorlaeufig = Ebene(name, phi, 0.0, 0.0, 0.0, 0.0, 0.0)
            lokal = form.copy()
            lokal.transformShape(_rahmen(laengs, radial, vorlaeufig))
            gefunden = bb.bohrungen(lokal, [name])
            if not gefunden:
                continue
            b = gefunden[0]
            if durch or b.durch:
                # durchgehend: von dieser Seite bis zur Mitte der Stange (die andere fräst den Rest)
                b = dataclasses.replace(b, z_unten=max(b.z_unten, 0.0), durch=False, spitze=0.0)
            if b.z_oben <= b.z_unten + vb.GLEICH:
                continue
            ebene = Ebene(
                name,
                phi,
                b.z_unten,
                b.mitte[0] - b.radius,
                b.mitte[0] + b.radius,
                -b.mitte[1] - b.radius,
                -b.mitte[1] + b.radius,
            )
            ergebnis.append((ebene, b))
    return ergebnis


def boden_der_bohrung(laengs, radial, ebene, bohrung):
    """(Ebene, Part.Face): der Grund der Bohrung als Kreisscheibe im Job – für den Vergleich auf
    der Stange (restmaterial.boden_radien)."""
    import FreeCAD
    import Part

    l_, u_, v_ = vh.rahmen(laengs, radial)
    phi = math.radians(ebene.phi)
    n = u_ * math.cos(phi) + v_ * math.sin(phi)
    quer = np.cross(l_, n)
    x, y = bohrung.mitte
    mitte = l_ * x + quer * (-y) + n * bohrung.z_unten
    kreis = Part.makeCircle(
        bohrung.radius, FreeCAD.Vector(*(float(c) for c in mitte)), FreeCAD.Vector(*n)
    )
    return ebene, Part.Face(Part.Wire(kreis))


def _bohrung_punkte(bohrung, ebene, w, oben, sicher):
    """([vierachs_bahn.Punkt], bohrung_bahn.Bohrbahn) – die Bohrung mit der Bahn „Bohrung
    fräsen“ (Helix, Ringe, die Wand rundum), zurück in den Rahmen der Stange wie die Nut."""
    from . import bohrung_bahn as bb

    radius = float(w.form.radius)
    werte = bb.Bohrwerte(
        fraeser_radius=radius,
        zustellung=w.zustellung,
        zeilenabstand=min(w.zeilenabstand, NUT_AE_ANTEIL * 2.0 * radius),
        aufmass=0.0,
        oben=oben,
        sicher=sicher,
        eintauchwinkel=w.eintauchwinkel,
        sicherheit=w.sicherheit,
    )
    bahn = bb.planen(werte, [_bohrung_eingeengt(bohrung, radius)])
    return _zurueck(bahn.punkte, ebene), bahn


def _bohrung_eingeengt(bohrung, radius):
    """Die Bohrung um NUT_LUFT enger, wo sie breiter ist als der Fräser – wie bei der Nut."""
    import dataclasses

    enger = min(NUT_LUFT, max(bohrung.radius - radius, 0.0))
    return dataclasses.replace(bohrung, radius=bohrung.radius - enger)


def _zurueck(punkte_lokal, ebene):
    """[vierachs_bahn.Punkt] – Punkte im Rahmen der Ebene (bahn.Punkt) zurück: a = x, die Höhe
    = z, q = −y, die Rundachse fest auf der Ebene; Bögen in Sehnen."""
    punkte = []
    vorher = None
    for p in punkte_lokal:
        if vorher is not None and p.bogen is not None and not p.eilgang:
            for x, y, z in _sehnen(vorher, p):
                punkte.append(vb.Punkt(False, x, z, ebene.phi, p.eintauchen, -y, p.anteil))
        else:
            punkte.append(vb.Punkt(p.eilgang, p.x, p.z, ebene.phi, p.eintauchen, -p.y, p.anteil))
        vorher = p
    return punkte


def _rahmen(laengs, radial, ebene):
    """FreeCAD.Matrix: vom Job in den Rahmen der Ebene – x längs, z ihre Normale (zum
    Werkzeug), y = z × x; der Ursprung auf der Achse. Dort ist a = x, die Höhe = z, q = −y."""
    import FreeCAD

    l_, u_, v_ = vh.rahmen(laengs, radial)
    phi = math.radians(ebene.phi)
    n = u_ * math.cos(phi) + v_ * math.sin(phi)
    y = np.cross(n, l_)
    zeilen = [float(c) for zeile in (l_, y, n) for c in (*zeile, 0.0)]
    return FreeCAD.Matrix(*zeilen, 0.0, 0.0, 0.0, 1.0)


def _sehnen(von, nach):
    """[(x, y, z)] – der Bogen von `von` nach `nach` (bahn.Punkt mit `bogen`) in Sehnen, die
    höchstens SEHNE vom Bogen abweichen; der letzte Punkt ist `nach`."""
    from . import bahn as bn

    mx, my, uhr = nach.bogen
    r = math.hypot(von.x - mx, von.y - my)
    winkel = bn.winkel(von, nach)
    schritt = 2.0 * math.acos(max(-1.0, 1.0 - SEHNE / r)) if r > SEHNE else math.pi / 8
    n = max(2, int(math.ceil(winkel / max(schritt, 1e-3))))
    a0 = math.atan2(von.y - my, von.x - mx)
    ergebnis = []
    for i in range(1, n + 1):
        t = i / n
        a = a0 - t * winkel if uhr else a0 + t * winkel
        ergebnis.append((mx + r * math.cos(a), my + r * math.sin(a), von.z + (nach.z - von.z) * t))
    return ergebnis


def _als_nut(liste, radius):
    """Die Nuten aus `liste`, die die Bahn „Nut“ mit dem Fräser `radius` fräst: in voller Breite
    oder mit der Trochoide – eine zu schmale auch (sie sagt es); eine zu breite (eine Abflachung
    zwischen zwei Wänden) fährt Zeilen."""
    from . import nut_bahn as nb

    return [n for n in liste if nb.verfahren(n, radius) != "zu_breit"]


def _eingeengt(nut, radius):
    """Die Nut um NUT_LUFT kürzer an jedem geschlossenen Ende und, wo sie breiter ist als der
    Fräser `radius`, um so viel schmaler: Läge der Fräser genau an, sähe ihn der Abtrag auf der
    Stange (Raster 0,5 mm × 1°), wo ein Punkt genau auf dem Ende liegt, 4 mm in der Wand."""
    import dataclasses

    ux, uy = nut.b[0] - nut.a[0], nut.b[1] - nut.a[1]
    laenge = math.hypot(ux, uy)
    if laenge <= 2 * NUT_LUFT:
        return nut
    ux, uy = ux / laenge * NUT_LUFT, uy / laenge * NUT_LUFT
    a = nut.a if nut.offen_a else (nut.a[0] + ux, nut.a[1] + uy)
    b = nut.b if nut.offen_b else (nut.b[0] - ux, nut.b[1] - uy)
    enger = min(NUT_LUFT, max(nut.radius - radius, 0.0))
    return dataclasses.replace(nut, a=a, b=b, radius=nut.radius - enger)


def _nut_punkte(liste, ebene, w, oben, sicher):
    """([vierachs_bahn.Punkt], nut_bahn.Nutbahn) – die Nuten `liste` mit der Bahn „Nut“
    (nut_bahn.planen: in voller Breite die Zickzack-Rampe, sonst die Trochoide, zuletzt die Wand
    rundum), zurück in den Rahmen der Stange: a = x, die Höhe = z, q = −y, die Rundachse fest
    auf der Ebene; Bögen in Sehnen."""
    from . import nut_bahn as nb

    radius = float(w.form.radius)
    werte = nb.Nutwerte(
        fraeser_radius=radius,
        zustellung=w.zustellung,
        zeilenabstand=min(w.zeilenabstand, NUT_AE_ANTEIL * 2.0 * radius),
        oben=oben,
        sicher=sicher,
        eintauchwinkel=w.eintauchwinkel,
        sicherheit=w.sicherheit,
    )
    bahn = nb.planen(werte, [_eingeengt(n, radius) for n in liste])
    return _zurueck(bahn.punkte, ebene), bahn


def planen(
    netz, laengs, radial, werte, flaechen, schritt_a=vh.SCHRITT_A, nuten_=None, bohrungen_=()
):
    """Die Bahn „Plan indexiert“ (Planbahn) über die Flächen `flaechen` ([Ebene], ebenen())
    mit den Werten `werte`; `netz` ist das Teil ohne diese Flächen (netz_ohne()), `laengs` und
    `radial` wie in vierachs_huelle; `nuten_` ({Name: [nut_bahn.Nut]}, nuten()): diese Flächen
    als Nut; `bohrungen_` ([(Ebene, Bohrung)], bohrungen()): Querbohrungen. ValueError mit einem
    Satz, wenn es nicht geht."""
    w = werte
    form = w.form
    radius = form.radius
    r_eben = ebener_radius(form)
    if r_eben <= 0:
        raise ValueError(tr("vp.fehler.form"))
    if w.zustellung <= 0 or w.zeilenabstand <= 0:
        raise ValueError(tr("vp.fehler.werte"))
    if w.zeilenabstand > 2 * r_eben:
        raise ValueError(tr("vp.fehler.zeilenabstand"))
    if not flaechen and not bohrungen_:
        raise ValueError(tr("vp.fehler.keine_ebene"))
    teil_vorne, teil_hinten = _enden(
        netz, laengs, radial, list(flaechen) + [e for e, _b in bohrungen_]
    )
    ueberlauf = vb.ueberlauf_vorschlag(radius) if w.ueberlauf is None else w.ueberlauf
    a_anfang = w.a_stange_vorne + radius + w.sicherheit
    a_ende = vb._ende(teil_hinten, ueberlauf, radius, w)
    if a_ende >= teil_vorne + radius:
        raise ValueError(vb._kein_platz(radius, w))
    hinten_frei = max(0.0, a_ende - radius - teil_hinten)
    # Die Hüllfläche: der um die Vernetzung größere Fräser, das Ergebnis um sie und den Rand
    # gehoben – so bleibt er überall aus dem Teil; die Fläche selbst liegt nicht im Netz.
    zugabe = netz.toleranz + vb.RAND
    geformt = form.mit_aufmass(netz.toleranz)
    sicher = w.stange_radius + w.sicherheit
    punkte = [vb.Punkt(True, a_anfang, sicher, 0.0)]
    lagen_gesamt = zeilen_gesamt = flaechen_gefraest = nuten_gefraest = bohrungen_gefraest = 0
    r_min = math.inf
    gebohrt = set()  # Namen: eine durchgehende zählt einmal, auch von beiden Seiten gefräst
    for ebene, bohrung in sorted(bohrungen_, key=lambda eb: eb[0].phi):
        oben = _material_ueber(w, ebene, radius)
        if oben <= bohrung.z_unten + vb.GLEICH:
            continue  # steht nichts mehr drüber
        stueck, bohrbahn = _bohrung_punkte(bohrung, ebene, w, oben, sicher)
        punkte.extend(stueck)
        letzter = punkte[-1]
        punkte.append(vb.Punkt(True, letzter.a, sicher, ebene.phi, q=letzter.q))
        if ebene.name not in gebohrt:
            flaechen_gefraest += 1
            bohrungen_gefraest += 1
        gebohrt.add(ebene.name)
        lagen_gesamt += bohrbahn.lagen
        zeilen_gesamt += max(1, int(math.ceil(bohrbahn.umlaeufe)))
        r_min = min(r_min, bohrbahn.z_min)
    for ebene in sorted(flaechen, key=lambda e: e.phi):
        ziel = ebene.tiefe + w.aufmass
        oben = _material_ueber(w, ebene, radius)
        if oben <= ziel + vb.GLEICH:
            continue  # steht nichts mehr drüber
        als_nut = _als_nut(nuten_.get(ebene.name, []) if nuten_ else [], radius)
        if als_nut:
            stueck, nut = _nut_punkte(als_nut, ebene, w, oben, sicher)
            punkte.extend(stueck)
            letzter = punkte[-1]
            punkte.append(vb.Punkt(True, letzter.a, sicher, ebene.phi, q=letzter.q))
            flaechen_gefraest += 1
            nuten_gefraest += nut.nuten
            lagen_gesamt += nut.lagen
            zeilen_gesamt += nut.kreise + nut.vollnut
            r_min = min(r_min, nut.z_min)
            continue
        anzahl_lagen = max(1, int(math.ceil((oben - ziel) / w.zustellung - 1e-9)))
        lagen = oben - (oben - ziel) * np.arange(1, anzahl_lagen + 1) / anzahl_lagen
        q_zeilen = _zeilen_quer(ebene, r_eben + zugabe + LUFT, w.zeilenabstand)
        a_von = max(a_ende, ebene.a_von - radius - UEBERLAUF_LAENGS)
        a_bis = min(a_anfang, ebene.a_bis + radius + UEBERLAUF_LAENGS)
        if a_bis <= a_von + vb.GLEICH:
            continue
        anzahl = max(2, int(math.ceil((a_bis - a_von) / schritt_a - 1e-9)) + 1)
        a_stellen = np.linspace(a_von, a_bis, anzahl)
        schritt = float(a_stellen[1] - a_stellen[0])
        rad = math.radians(ebene.phi)
        huelle = vh.je_versatz(netz, laengs, radial, geformt, rad, a_von, schritt, anzahl, q_zeilen)
        roh = huelle.T  # (Zeilen, Stellen); −inf, wo er nichts trifft
        hoehe = roh + zugabe
        # Wo die Stirn über das Ende der Fläche ragt, nur, wenn dort nichts höher steht als
        # die Fläche selbst – nicht über den Zylinder neben der Wand, den eine Lage auf seinem
        # Radius gerade noch streifen dürfte.
        ragt = (a_stellen < ebene.a_von + radius + vb.GLEICH) | (
            a_stellen > ebene.a_bis - radius - vb.GLEICH
        )
        frei = ~ragt[None, :] | (roh <= ziel + vb.GLEICH)
        flaechen_gefraest += 1
        vorige = oben
        for lage in lagen:
            lage = float(lage)
            # Zeilen, deren ebene Stirn in dieser Lage noch die Stange trifft.
            w_lage = math.sqrt(max(w.stange_radius**2 - lage * lage, 0.0))
            zeilen_da = np.abs(q_zeilen) - r_eben < w_lage - vb.GLEICH
            drin = (hoehe <= lage + vb.GLEICH) & frei & zeilen_da[:, None]
            if not drin.any():
                vorige = lage
                continue
            mit_luecke = np.zeros((len(q_zeilen), anzahl + 2), dtype=bool)
            mit_luecke[:, 1:-1] = drin
            for fahrt in vb._fahrten(mit_luecke):
                a, q, m = _folge(fahrt, a_stellen, q_zeilen)
                offen = float(a[0]) - radius >= w.a_stange_vorne  # vor der Stange: nur Luft
                _einfahrt(punkte, a, q, lage, ebene.phi, vorige, offen, w, sicher)
                for i in _knicke(a, q):
                    punkte.append(vb.Punkt(False, float(a[i]), lage, ebene.phi, q=float(q[i])))
                punkte.append(vb.Punkt(True, float(a[-1]), sicher, ebene.phi, q=float(q[-1])))
                zeilen_gesamt += len(set(m[m >= 0].tolist()))
            lagen_gesamt += 1
            vorige = lage
            r_min = min(r_min, lage)
    if flaechen_gefraest == 0:
        raise ValueError(tr("vp.fehler.nichts"))
    letzter = punkte[-1]
    _eilgang(punkte, a_anfang, sicher, letzter.phi, 0.0)
    return Planbahn(
        punkte,
        flaechen_gefraest,
        lagen_gesamt,
        zeilen_gesamt,
        r_min if math.isfinite(r_min) else 0.0,
        hinten_frei,
        nuten_gefraest,
        bohrungen_gefraest,
    )


def _enden(netz, laengs, radial, flaechen):
    """(vorne, hinten) des Teils längs: aus dem Netz, und den Flächen, falls das Netz ohne sie
    leer ist."""
    l_, _u, _v = vh.rahmen(laengs, radial)
    vorne = max(e.a_bis for e in flaechen)
    hinten = min(e.a_von for e in flaechen)
    if len(netz.punkte):
        a_teil = netz.punkte @ l_
        vorne, hinten = max(vorne, float(a_teil.max())), min(hinten, float(a_teil.min()))
    return vorne, hinten


def _material_ueber(w, ebene, radius):
    """So hoch steht über der Fläche noch Material (die Höhe der Spitze dort): die Stange –
    oder nach dem Schruppen der Rest (w.rest) über der Fläche und so weit daneben, wie der
    Fräser reicht; nie mehr als die Stange."""
    if w.rest is None:
        return float(w.stange_radius)
    rest_a, rest_phi, rest_r = w.rest
    laengs = (rest_a >= ebene.a_von - radius) & (rest_a <= ebene.a_bis + radius)
    breit = max(abs(ebene.q_von), abs(ebene.q_bis)) + radius
    weit = math.atan2(breit, ebene.tiefe)
    abstand = np.angle(np.exp(1j * (rest_phi - math.radians(ebene.phi))))
    quer = np.abs(abstand) <= weit
    if not laengs.any() or not quer.any():
        return float(w.stange_radius)
    return min(float(w.stange_radius), float(np.max(rest_r[np.ix_(laengs, quer)])))


def _zeilen_quer(ebene, rand, abstand):
    """Die Versätze der Zeilen quer: von q_von + rand bis q_bis − rand gleich weit auseinander,
    höchstens `abstand`; eine in der Mitte, wenn die Fläche dafür zu schmal ist."""
    breite = ebene.q_bis - ebene.q_von
    if breite <= 2 * rand + vb.GLEICH:
        return np.array([(ebene.q_von + ebene.q_bis) / 2])
    anzahl = int(math.ceil((breite - 2 * rand) / abstand - 1e-9)) + 1
    return np.linspace(ebene.q_von + rand, ebene.q_bis - rand, anzahl)


def _folge(fahrt, a_stellen, q_zeilen):
    """Die Punkte einer Fahrt (vierachs_bahn._fahrten mit Zeile = Zeile quer, Winkelschritt =
    Stelle längs, mit der Lücke an beiden Enden): (a, q, Zeile) – Zeile −1 auf dem Schritt quer
    zur nächsten."""
    teile = []
    for art, m, js in fahrt:
        if art == "zeile":
            k = np.asarray(js) - 1
            teile.append((a_stellen[k], np.full(len(k), q_zeilen[m]), np.full(len(k), m)))
            continue
        k = int(js) - 1
        teile.append((a_stellen[[k]], np.array([q_zeilen[m + 1]]), np.array([-1])))
    return tuple(np.concatenate([t[i] for t in teile]) for i in range(3))


def _knicke(a, q):
    """Die Punkte, die bleiben: Anfang, Ende und wo die Fahrt die Richtung längs wechselt oder
    quer rückt – dazwischen liegt sie gerade."""
    n = len(a)
    if n <= 2:
        return range(n)
    da = np.diff(a)
    dq = np.diff(q)
    bleibt = np.ones(n, dtype=bool)
    bleibt[1:-1] = (
        (da[:-1] * da[1:] <= 0) | (np.abs(dq[:-1]) > vb.GLEICH) | (np.abs(dq[1:]) > vb.GLEICH)
    )
    return np.flatnonzero(bleibt)


def _eilgang(punkte, a, r, phi, q):
    """Im Eilgang nach (a, r, φ, q) – eine lange Drehung in Schritten von höchstens
    HOECHSTENS_GRAD, wie vierachs_bahn._eilgang."""
    vorher = punkte[-1]
    schritte = max(1, int(math.ceil(abs(phi - vorher.phi) / vb.HOECHSTENS_GRAD - 1e-9)))
    for m in range(1, schritte + 1):
        t = m / schritte
        punkt = vb.Punkt(
            True,
            vorher.a + t * (a - vorher.a),
            vorher.r + t * (r - vorher.r),
            vorher.phi + t * (phi - vorher.phi),
            q=vorher.q + t * (q - vorher.q),
        )
        if punkt != punkte[-1]:
            punkte.append(punkt)


def _einfahrt(punkte, a, q, lage, phi, oben, offen, w, sicher):
    """Über den Anfang der Fahrt, im Eilgang bis knapp über `oben` (höher steht dort nichts),
    hinein: senkrecht mit dem Eintauchvorschub, wo die Zeile vor der Stange beginnt (`offen`)
    oder für eine Rampe zu kurz ist – sonst über die Rampe mit dem Eintauchwinkel längs der
    ersten Zeile, hin und her, bis sie unten ist, und auf ihr zurück zum Anfang."""
    a0, q0 = float(a[0]), float(q[0])
    _eilgang(punkte, a0, sicher, phi, q0)
    knapp = min(sicher, oben + w.sicherheit)
    if knapp < sicher:
        punkte.append(vb.Punkt(True, a0, knapp, phi, q=q0))
    wechsel = np.flatnonzero(np.abs(q - q0) > vb.GLEICH)  # wo die Fahrt quer rückt
    erste = int(wechsel[0]) - 1 if len(wechsel) else len(a) - 1  # das Ende der ersten Zeile
    laenge = abs(float(a[erste]) - a0)
    if offen or laenge < vb.RAMPE_MINDESTENS or lage >= oben - vb.GLEICH:
        punkte.append(vb.Punkt(False, a0, lage, phi, True, q0))
        return
    punkte.append(vb.Punkt(False, a0, oben, phi, True, q0))  # bis ans Material
    r = np.full(len(a), lage)
    winkel = np.full(len(a), phi)
    for stelle_a, stelle_r, _phi in vb._rampe(a, r, winkel, 0, erste, oben, w):
        punkte.append(vb.Punkt(False, stelle_a, stelle_r, phi, q=q0))
