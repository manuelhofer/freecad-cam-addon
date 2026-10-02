# SPDX-License-Identifier: LGPL-2.1-or-later
"""2,5D, die Bahn „Nut“ (W-006 4.1 Punkt 6): Langlöcher – zwei gerade, parallele Wände, an den
Enden Halbkreise – mit einem Schaftfräser, der nicht breiter ist als sie; mit Rampe oder in
Bögen statt Vollschnitt.

- **Erkennung** (nuten()): Eine Wand der Nut bringt die ganze Runde mit, ihr Grund die Wände an
  seinem Rand (_waende_der_nut). Die Unterkanten werden eine Kontur (kontur_bahn.konturen);
  geschlossen, die freie Seite innen, zwei Halbkreise mit gleichem Radius und dazwischen zwei
  Geraden: eine Nut mit den Mittelpunkten A und B der Halbkreise und der halben Breite r. Ohne
  Material unter dem Grund geht sie durch.
- **In Bögen** (die Regel; Spezifikation Strategien 12.2, P-2026-10-02-53): je Lage (ap) eine
  Helix an einem Ende hinab, unten einmal rundum – der Kreis um das Ende ist dann frei –, dann
  Bögen wie in der offenen Nut (unten) bis in den Halbkreis am anderen Ende: je Bogen ein
  Halbkreis mit dem Radius r − R − Aufmaß im Gleichlauf von der einen Wand nach vorn durchs
  Material zur anderen (M3: gegen den Uhrzeigersinn), quer zurück über die freie Seite im
  Schnellvorschub, an der Wand vor in den nächsten – mit dem Schritt nach der Last
  (_bogenschritt, unten). Bis P-2026-10-02-52 volle Kreise (Trochoide), die hinten durch schon
  freie Luft liefen: je Schritt gut ein Zehntel länger. Die nächste Lage zurück.
- **Vollnut** (ist die Nut kaum breiter als der Fräser – die Bögen hätten einen Radius unter
  VOLLNUT_ANTEIL · R): in einer Zickzack-Rampe längs der Mittellinie hinab, unten einmal eben
  hinüber. Je Fahrt höchstens so viel tiefer, dass der Fräser nie mehr als ap und nie mehr als
  VOLLNUT_AP · D in voller Breite schneidet (die Rampe hin und zurück schneidet zweimal die
  Stufe); der Vorschub so, dass der Span so dick bleibt wie beim Einsatz mit ae (dünner Span
  bei kleinem ae – in voller Breite nicht).
- **Schlichten**: zuletzt die Wand bei r − R einmal rundum im Gleichlauf, mit Halbkreisen aus
  der Mitte eines Endes hinein und wieder heraus – in Zügen von höchstens der Schneidenlänge.
  Die Vollnut fährt diese Runde immer (sonst bliebe die Nut zu schmal).
- Durchgehende Nuten um `tiefer` unter den Grund; mehrere in der Reihenfolge des kürzesten
  Wegs; die Zeit mit bahn.zeit.
- **Offene Nuten** (P-2026-10-01-47): zum Rand hin offen – an einem Ende (ein Halbkreis und
  zwei Geraden, die am Rand enden) oder an beiden (zwei parallele Wände, die freien Seiten
  zueinander, der Grund dazwischen). Hinter einem offenen Ende ist Luft (geprüft): Dort fährt
  der Fräser im Eilgang hinab und von außen hinein – keine Helix. Die Bögen (unten) beginnen
  draußen und laufen bis ans andere Ende; dort hinaus ins Freie oder, am Halbkreis, hinauf und
  die nächste Lage wieder von außen. Die Vollnut in Lagen von außen geradeaus. Das Schlichten der Wände im Gleichlauf: an der einen Wand hinein, außen
  (oder um den Halbkreis) hinüber, an der anderen heraus.
- **Bögen statt Kreisen** in offenen Nuten (P-2026-10-02-22, Manuels Halbkreis): Je Schritt nur
  der Halbkreis, der schneidet – im Gleichlauf von der einen Wand nach vorn durchs Material zur
  anderen, so dass in der Mitte eine Delle entsteht –, dann quer über die freie Seite zurück
  im Schnellvorschub (RUECKWEG × Vorschub, G1: im Eilgang fährt nicht jede Steuerung gerade)
  und an der Wand vor in den nächsten Bogen. Der Eingriff wächst auf jedem Bogen von 0 an der
  Wand bis in die Mitte und fällt wieder. ae ist die Last (Spezifikation Strategien 12.1 (a),
  P-2026-10-02-56; _bogenschritt): Je Bogen nimmt der Fräser im Mittel so viel Material je mm
  Weg wie auf gerader Bahn mit ae, in der Mitte kurz bis 1,7 ae, über 1,25 ae nie länger als
  eine Fräserbreite Weg, und er umschlingt das Material nie mehr als zur Hälfte – mit dem Ø 12
  und ae 1,5 in der Nut 20 rückt er um 0,97 mm vor (bis P-2026-10-02-55 der schonende Schritt,
  0,65: in der Mitte nicht mehr Umschlingung als an einer geraden Wand mit ae). Am Anfang
  morphen die Bögen vom geraden Rand zum Halbkreis: Die Enden bleiben an der Wand stehen, die
  Mitte rückt je Bogen um den Schritt vor – keiner schneidet in der Luft. Jede Lage beginnt
  draußen am offenen Ende (keine Helix): So hat eine offene Nut keine Grenze in der Breite – in
  ihrer Mitte bleibt kein Kern.

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, replace

from . import bahn as bn
from . import einheiten
from . import kontur_bahn as kb
from . import vierachs_bahn as vb
from .sprache import tr

GLEICH = 1e-6
TIEFER = 0.5  # mm – so weit unter den Grund einer durchgehenden Nut
VOLLNUT_ANTEIL = 0.25  # × R: kleiner der Radius der Bögen, dann die Vollnut mit Rampe
KERN_ANTEIL = 0.9  # × R: größer der Radius der Helix, dann bliebe in ihrer Mitte ein Kern
VOLLNUT_AP = 0.5  # × D: so tief schneidet der Fräser in voller Breite höchstens
MIN_SCHRITT = 0.05  # mm – kürzer rücken die Bögen nicht vor
MIN_STEIGUNG = 0.05  # mm je Umlauf – flacher wird keine Helix
MIN_RAMPE = 0.01  # mm je Fahrt – flacher wird die Rampe der Vollnut nicht
DURCH_PRUEFEN = 0.05  # mm unter dem Grund wird nach Material gesehen
RUECKWEG = 3.0  # × Vorschub: so schnell quer zurück über die freie Seite (G1, nicht G0)
# × D: so lang am Stück rechnet _bogenschritt die Last über bahn.LAST_DAUERND · ae höchstens
# (erlaubt ist eine Fräserbreite) – der Fräser greift vor seiner Mitte ein, so verteilt sich die
# Last auf dem Bogen etwas breiter als gerechnet (der Prüfstand misst bis 6 % mehr).
UEBER_WEG = 0.8
MATERIAL_SPIEL = 0.01  # mm – so wenig über dem Grund gilt im Materialstand als nichts mehr
# Die Eintauchstelle (W-012 E1): So fein sucht der Vorschlag längs der Nut; liegt an einer Stelle
# so viel weniger Material im Kreis der Helix als an den Enden (eine Bohrung, eine Tasche kreuzt
# die Nut), taucht er dort ein.
EINTAUCH_RASTER = 1.0  # mm
EINTAUCH_WENIGER = 0.8  # × das Material an den Enden


@dataclass(frozen=True)
class Nut:
    """Ein Langloch im Teil."""

    waende: tuple  # die Namen der Wände („Face7“ …)
    a: tuple  # (x, y) – Mittelpunkt des einen Halbkreises
    b: tuple  # (x, y) – des anderen
    radius: float  # die halbe Breite
    z_oben: float  # Oberkante der Wände
    z_unten: float  # Grund
    durch: bool  # unter dem Grund ist kein Material
    offen_a: bool = False  # das Ende A liegt am Rand: dahinter ist Luft, kein Halbkreis
    offen_b: bool = False

    @property
    def laenge(self):
        """Der Abstand von A nach B (mm) – an jedem geschlossenen Ende kommt r dazu."""
        return math.hypot(self.b[0] - self.a[0], self.b[1] - self.a[1])

    @property
    def gesamtlaenge(self):
        """So lang ist die Nut über alles (mm): an geschlossenen Enden die Halbkreise dazu."""
        return self.laenge + self.radius * ((not self.offen_a) + (not self.offen_b))

    @property
    def offen(self):
        return self.offen_a or self.offen_b


@dataclass
class Nutwerte:
    """Was die Nut braucht; Längen in mm, z nach oben im Job."""

    fraeser_radius: float
    zustellung: float  # ap je Lage
    zeilenabstand: float  # ae: daraus der Schritt der Bögen (_bogenschritt)
    oben: float  # z, wo das Material beginnt (das Rohteil)
    sicher: float  # z für den Eilgang über allem
    aufmass: float = 0.0  # bleibt beim Schruppen an der Wand – fürs Schlichten
    schlichten: bool = True  # danach die Wand einmal rundum
    gleichlauf: bool = True
    tiefer: float = TIEFER  # nur bei durchgehenden Nuten
    schneidenlaenge: float = 0.0  # 0: unbekannt
    eintauchwinkel: float = vb.EINTAUCHWINKEL  # Grad – Rampe und Helix
    sicherheit: float = vb.SICHERHEIT
    vorschub: float = 0.0  # mm/min – für die Zeit; 0: 1000
    eintauchen: float = 0.0
    # Die gewählten Eintauchstellen (W-012 E1): je Nut (schluessel) der Anteil 0 … 1 von A nach
    # B; ohne Eintrag der Vorschlag.
    eintauchen_bei: dict = None


@dataclass
class Nutbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    nuten: int
    lagen: int  # Lagen in Bögen über alle Nuten (eine Vollnut zählt 1)
    boegen: int  # Bögen über alle Nuten und Lagen
    vollnut: int  # so viele Nuten in voller Breite mit Rampe
    z_min: float
    laenge: float  # mm im Vorschub
    zeit: float  # Minuten (bahn.zeit)
    # Mit Materialstand (W-012): was über den Gründen noch steht und was die Operationen davor
    # dort schon weggenommen haben (mm³), und welche das waren; ohne 0, 0, [].
    noch: float = 0.0
    weg: float = 0.0
    davor: list = None
    # Je geschlossene Nut: (schluessel, Anteil oder None – abwechselnd an den Enden,
    # vorgeschlagen?, A, B) – für die Zeile „Eintauchen bei“ im Assistenten.
    stellen: list = None


# --- Erkennung --------------------------------------------------------------------------------


def _ist_boden(flaeche):
    """Eine ebene Fläche, die nach oben schaut?"""
    bb = flaeche.BoundBox
    if bb.ZMax - bb.ZMin > kb.NAH:
        return False
    try:
        u0, u1, v0, v1 = flaeche.ParameterRange
        return flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2).z > 1.0 - 1e-6
    except Exception:  # OCC: keine Parameter
        return False


def _waende_der_nut(form, nummer, index):
    """Die Nummern der Wände rundum, die mit der Wand oder dem Grund `nummer` zusammenhängen –
    über gemeinsame Kanten, alle mit derselben Unterkante."""
    import Part

    flaechen = form.Faces
    start = flaechen[nummer]
    offen = []
    if kb.ist_wand(start):
        z = start.BoundBox.ZMin
        offen.append(nummer)
    elif _ist_boden(start):
        z = start.BoundBox.ZMax
        for kante in start.Edges:
            for nachbar in form.ancestorsOfType(kante, Part.Face):
                i = index.get(nachbar.hashCode())
                if i is None or i in offen or not kb.ist_wand(flaechen[i]):
                    continue
                if abs(flaechen[i].BoundBox.ZMin - z) <= kb.NAH:
                    offen.append(i)
    else:
        return ()
    gesehen = set(offen)
    ergebnis = []
    while offen:
        i = offen.pop()
        ergebnis.append(i)
        for kante in flaechen[i].Edges:
            for nachbar in form.ancestorsOfType(kante, Part.Face):
                j = index.get(nachbar.hashCode())
                if j is None or j in gesehen or not kb.ist_wand(flaechen[j]):
                    continue
                if abs(flaechen[j].BoundBox.ZMin - z) <= kb.NAH:
                    gesehen.add(j)
                    offen.append(j)
    return tuple(sorted(ergebnis))


def _langloch(kontur):
    """(A, B, r): die Mittelpunkte der Halbkreise und ihr Radius, wenn die Unterkanten der Kontur
    zwei Halbkreise mit gleichem Radius und zwei Geraden dazwischen sind – sonst None. Halbkreise
    und Geraden dürfen in Stücken kommen."""
    import Part

    kreise = {}
    geraden = []
    for kante in kontur.draht.Edges:
        kurve = kante.Curve
        if isinstance(kurve, Part.Circle):
            mitte = (round(kurve.Center.x, 4), round(kurve.Center.y, 4))
            eintrag = kreise.setdefault(mitte, [float(kurve.Radius), 0.0])
            if abs(eintrag[0] - kurve.Radius) > 1e-4:
                return None
            eintrag[1] += abs(kante.LastParameter - kante.FirstParameter)
        elif isinstance(kurve, (Part.Line, Part.LineSegment)):
            p0, p1 = kante.Vertexes[0].Point, kante.Vertexes[-1].Point
            geraden.append(((p0.x, p0.y), (p1.x, p1.y)))
        else:
            return None
    if len(kreise) != 2 or not geraden:
        return None
    (a, (r_a, w_a)), (b, (r_b, w_b)) = kreise.items()
    if abs(r_a - r_b) > 1e-4 or abs(w_a - math.pi) > 1e-3 or abs(w_b - math.pi) > 1e-3:
        return None
    laenge = math.hypot(b[0] - a[0], b[1] - a[1])
    if laenge < 1e-3:
        return None
    ux, uy = (b[0] - a[0]) / laenge, (b[1] - a[1]) / laenge
    seiten = {1: 0.0, -1: 0.0}  # die Länge der Geraden links und rechts der Mittellinie
    for p0, p1 in geraden:
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        if abs(dx * uy - dy * ux) > 1e-4 * max(math.hypot(dx, dy), 1.0):
            return None  # nicht parallel zur Mittellinie
        abstand = (p0[0] - a[0]) * -uy + (p0[1] - a[1]) * ux
        if abs(abs(abstand) - r_a) > 1e-3:
            return None
        seiten[1 if abstand > 0 else -1] += math.hypot(dx, dy)
    if any(abs(s - laenge) > 1e-3 for s in seiten.values()):
        return None
    return (float(a[0]), float(a[1])), (float(b[0]), float(b[1])), float(r_a)


def _durch(form, a, b, r, z_unten):
    """Ist unter dem Grund kein Material – knapp innerhalb der Wände an beiden Enden und in der
    Mitte geprüft (wie bei Bohrungen: unter einer Stufe liegt am Rand ihr Boden)?"""
    import FreeCAD

    laenge = math.hypot(b[0] - a[0], b[1] - a[1])
    ux, uy = (b[0] - a[0]) / laenge, (b[1] - a[1]) / laenge
    innen = max(r - min(0.02, 0.25 * r), 0.0)
    mitte = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    stellen = [
        (a[0] - ux * innen, a[1] - uy * innen),
        (b[0] + ux * innen, b[1] + uy * innen),
    ]
    for p in (a, mitte, b):
        stellen.append((p[0] - uy * innen, p[1] + ux * innen))
        stellen.append((p[0] + uy * innen, p[1] - ux * innen))
    z = z_unten - DURCH_PRUEFEN
    return not any(form.isInside(FreeCAD.Vector(x, y, z), 1e-6, True) for x, y in stellen)


OFFEN_PRUEFEN = 0.5  # mm hinter einem offenen Ende wird nach Luft gesehen
FREI_VOR = 1.0  # mm – so weit hinter einem offenen Ende bleibt der Rand des Fräsers


def _waende_offen(form, nummer, index):
    """Die Nummern der Wände einer offenen Nut zur Wand oder zum Grund `nummer`: von einer Wand
    über ihren Grund (die ebene Fläche nach oben an ihrer Unterkante) zu allen Wänden an seinem
    Rand – die gegenüberliegende Wand hängt nicht an ihr."""
    import Part

    flaechen = form.Faces
    start = flaechen[nummer]
    if _ist_boden(start):
        return _waende_der_nut(form, nummer, index)
    if not kb.ist_wand(start):
        return ()
    z = start.BoundBox.ZMin
    for kante in start.Edges:
        bb = kante.BoundBox
        if abs(bb.ZMax - z) > kb.NAH or abs(bb.ZMin - z) > kb.NAH:
            continue  # keine Unterkante
        for nachbar in form.ancestorsOfType(kante, Part.Face):
            i = index.get(nachbar.hashCode())
            if i is None or i == nummer:
                continue
            if _ist_boden(flaechen[i]) and abs(flaechen[i].BoundBox.ZMax - z) <= kb.NAH:
                return _waende_der_nut(form, i, index)
    return ()


def _gerade(kontur):
    """((x0, y0), (ux, uy), s_von, s_bis) – wenn alle Unterkanten der Kontur auf einer Geraden
    liegen; sonst None."""
    import Part

    punkte = []
    for kante in kontur.draht.Edges:
        if not isinstance(kante.Curve, (Part.Line, Part.LineSegment)):
            return None
        punkte.extend((v.Point.x, v.Point.y) for v in kante.Vertexes)
    p0 = punkte[0]
    fern = max(punkte, key=lambda p: math.hypot(p[0] - p0[0], p[1] - p0[1]))
    laenge = math.hypot(fern[0] - p0[0], fern[1] - p0[1])
    if laenge < 1e-3:
        return None
    ux, uy = (fern[0] - p0[0]) / laenge, (fern[1] - p0[1]) / laenge
    for p in punkte:
        if abs((p[0] - p0[0]) * -uy + (p[1] - p0[1]) * ux) > 1e-4:
            return None
    s = [(p[0] - p0[0]) * ux + (p[1] - p0[1]) * uy for p in punkte]
    return p0, (ux, uy), min(s), max(s)


def _frei_hinter(form, ende, t, v, r, z_unten, z_oben):
    """Ist hinter dem Ende `ende` (in Richtung t, quer v) Luft – quer über die Breite und mehr,
    knapp über dem Grund und unter der Oberkante?"""
    import FreeCAD

    for z in (z_unten + 0.1, (z_unten + z_oben) / 2, z_oben - 0.1):
        for k in (-1.5, -1.0, 0.0, 1.0, 1.5):
            x = ende[0] + t[0] * OFFEN_PRUEFEN + v[0] * k * r
            y = ende[1] + t[1] * OFFEN_PRUEFEN + v[1] * k * r
            if form.isInside(FreeCAD.Vector(x, y, z), 1e-6, True):
                return False
    return True


def _offene_nut(form, konturen):
    """Die offene Nut aus den Konturen ihrer Wände – None, wenn es keine ist: eine Kontur aus
    einem Halbkreis und zwei Geraden, die am Rand enden (an einem Ende offen), oder zwei
    gerade Wände, parallel, die freien Seiten zueinander (an beiden Enden offen)."""
    import Part

    if not konturen or any(k.geschlossen for k in konturen):
        return None
    z_unten = float(konturen[0].z_unten)
    z_oben = max(float(k.z_oben) for k in konturen)
    waende = tuple(sorted({w for k in konturen for w in k.waende}, key=lambda n: int(n[4:])))
    if len(konturen) == 2:
        g1, g2 = _gerade(konturen[0]), _gerade(konturen[1])
        if g1 is None or g2 is None:
            return None
        (p1, u, *_), (p2, u2, *_) = g1, g2
        if abs(u[0] * u2[1] - u[1] * u2[0]) > 1e-4:
            return None  # nicht parallel
        v = (-u[1], u[0])
        abstand = (p2[0] - p1[0]) * v[0] + (p2[1] - p1[1]) * v[1]
        if abs(abstand) < 1e-3:
            return None
        # Die freien Seiten zeigen zueinander.
        for k, zu in ((konturen[0], abstand), (konturen[1], -abstand)):
            if (k.normale[0] * v[0] + k.normale[1] * v[1]) * zu <= 0:
                return None
        r = abs(abstand) / 2
        mitte = (p1[0] + v[0] * abstand / 2, p1[1] + v[1] * abstand / 2)
        s = []
        for p, _u, s_von, s_bis in (g1, g2):
            versatz = (p[0] - p1[0]) * u[0] + (p[1] - p1[1]) * u[1]
            s.extend((versatz + s_von, versatz + s_bis))
        a = (mitte[0] + u[0] * min(s), mitte[1] + u[1] * min(s))
        b = (mitte[0] + u[0] * max(s), mitte[1] + u[1] * max(s))
        if not (
            _frei_hinter(form, a, (-u[0], -u[1]), v, r, z_unten, z_oben)
            and _frei_hinter(form, b, u, v, r, z_unten, z_oben)
        ):
            return None
        if _durch(form, a, b, r, z_unten):
            return None
        return Nut(waende, a, b, r, z_oben, z_unten, False, True, True)
    if len(konturen) != 1:
        return None
    kreise, geraden = [], []
    for kante in konturen[0].draht.Edges:
        kurve = kante.Curve
        if isinstance(kurve, Part.Circle):
            kreise.append(
                (
                    (kurve.Center.x, kurve.Center.y),
                    float(kurve.Radius),
                    abs(kante.LastParameter - kante.FirstParameter),
                )
            )
        elif isinstance(kurve, (Part.Line, Part.LineSegment)):
            geraden.append([(p.Point.x, p.Point.y) for p in kante.Vertexes])
        else:
            return None
    if not kreise or not geraden:
        return None
    mitte, r, _w = kreise[0]
    if any(
        math.hypot(m[0] - mitte[0], m[1] - mitte[1]) > 1e-4 or abs(rr - r) > 1e-4
        for m, rr, _w in kreise
    ):
        return None
    if abs(sum(w for _m, _r, w in kreise) - math.pi) > 1e-3:
        return None
    # Die Geraden laufen von den Enden des Halbkreises weg, zum offenen Ende.
    fern = max(
        (p for g in geraden for p in g),
        key=lambda p: math.hypot(p[0] - mitte[0], p[1] - mitte[1]),
    )
    laenge = math.hypot(fern[0] - mitte[0], fern[1] - mitte[1])
    if laenge < 1e-3:
        return None
    # Die Richtung: längs der Geraden (nicht zum fernsten Punkt – der liegt um r daneben).
    g = geraden[0]
    dx, dy = g[1][0] - g[0][0], g[1][1] - g[0][1]
    lg = math.hypot(dx, dy)
    if lg < 1e-6:
        return None
    u = (dx / lg, dy / lg)
    if (fern[0] - mitte[0]) * u[0] + (fern[1] - mitte[1]) * u[1] < 0:
        u = (-u[0], -u[1])
    v = (-u[1], u[0])
    s_max = 0.0
    for g in geraden:
        for p in g:
            quer = (p[0] - mitte[0]) * v[0] + (p[1] - mitte[1]) * v[1]
            if abs(abs(quer) - r) > 1e-3:
                return None
            s_max = max(s_max, (p[0] - mitte[0]) * u[0] + (p[1] - mitte[1]) * u[1])
    b = (mitte[0] + u[0] * s_max, mitte[1] + u[1] * s_max)
    if s_max < 1e-3 or not _frei_hinter(form, b, u, v, r, z_unten, z_oben):
        return None
    flaeche_innen = (mitte[0] + u[0] * s_max / 2, mitte[1] + u[1] * s_max / 2)
    if (
        konturen[0].normale[0] * (flaeche_innen[0] - konturen[0].stelle[0])
        + konturen[0].normale[1] * (flaeche_innen[1] - konturen[0].stelle[1])
        <= 0
    ):
        return None  # die freie Seite liegt außen: ein Zapfen, keine Nut
    if _durch(form, mitte, b, r, z_unten):
        return None
    return Nut(
        waende, (float(mitte[0]), float(mitte[1])), b, r, z_oben, z_unten, False, False, True
    )


_GEMERKT = {}  # (Form, Fläche) → Nut oder None – der Assistent fragt oft dieselbe Fläche
_GEMERKT_HOECHSTENS = 1024


def _schluessel(form):
    """Was eine Form wiedererkennt: ihr Kern (hashCode), die Zahl der Flächen, ihre Box."""
    bb = form.BoundBox
    box = tuple(round(v, 6) for v in (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax))
    return (form.hashCode(), len(form.Faces), *box)


def _nut_der_flaeche(form, name, schluessel, index):
    """Die Nut, zu der die Fläche `name` gehört – oder None; gemerkt je Form und Fläche."""
    from . import raeumen_bahn as rb
    from . import vierachs_flaechen as vf

    eintrag = (schluessel, name)
    if eintrag in _GEMERKT:
        return _GEMERKT[eintrag]
    gefunden = None
    nummern = vf.nummern([name])
    waende = ()
    if nummern and nummern[0] < len(form.Faces):
        if not index:
            index.update({f.hashCode(): i for i, f in enumerate(form.Faces)})
        waende = _waende_der_nut(form, nummern[0], index)
    try:
        konturen = kb.konturen(form, [f"Face{i + 1}" for i in waende]) if waende else []
    except ValueError:
        konturen = []
    for k in konturen:
        if not k.geschlossen:
            continue
        langloch = _langloch(k)
        if langloch is None:
            continue
        flaeche = rb.kontur_flaeche(k)
        if flaeche is None or not rb.ist_tasche(k, flaeche):
            continue  # ein Langloch als Zapfen: die Kontur fährt außen
        a, b, r = langloch
        durch = _durch(form, a, b, r, float(k.z_unten))
        gefunden = Nut(k.waende, a, b, r, float(k.z_oben), float(k.z_unten), durch)
        break
    if gefunden is None and nummern and nummern[0] < len(form.Faces):
        offen = _waende_offen(form, nummern[0], index)
        try:
            konturen = kb.konturen(form, [f"Face{i + 1}" for i in offen]) if offen else []
        except ValueError:
            konturen = []
        gefunden = _offene_nut(form, konturen)
    if len(_GEMERKT) >= _GEMERKT_HOECHSTENS:
        _GEMERKT.clear()
    _GEMERKT[eintrag] = gefunden
    return gefunden


def nuten(form, namen):
    """[Nut] – die Langlöcher, zu denen die Flächen `namen` gehören (eine Wand, der Grund)."""
    schluessel = _schluessel(form)
    index = {}
    ergebnis = []
    for name in namen:
        nut = _nut_der_flaeche(form, name, schluessel, index)
        if nut is not None and not any(n.waende == nut.waende for n in ergebnis):
            ergebnis.append(nut)
    return ergebnis


def ist_nut(form, name):
    """Gehört die Fläche `name` zu einer Nut (nuten())?"""
    return bool(nuten(form, [name]))


def ganze_nuten(form, namen):
    """Die Flächen `namen` („Face7“ …), jede Wand einer Nut ersetzt durch alle Wände dieser Nut –
    eine angeklickte Wand meint die Nut; ihr Grund und alles andere bleibt, wie es ist."""
    ergebnis = []
    for name in namen:
        neu = [name]
        if not ist_grund(form, name):
            gefunden = nuten(form, [name])
            if gefunden:
                neu = list(gefunden[0].waende)
        ergebnis.extend(n for n in neu if n not in ergebnis)
    return ergebnis


def ist_grund(form, name):
    """Ist die Fläche `name` eine ebene Fläche nach oben (der Grund einer Nut, wenn ist_nut)?"""
    from . import vierachs_flaechen as vf

    nummern = vf.nummern([name])
    return bool(nummern) and nummern[0] < len(form.Faces) and _ist_boden(form.Faces[nummern[0]])


# --- Bahn ---------------------------------------------------------------------------------


def _hin(punkte, x, y, z, bogen=None, anteil=1.0):
    """Ein Satz im Vorschub nach (x, y, z); gibt seine Länge zurück."""
    punkt = bn.Punkt(False, float(x), float(y), float(z), False, bogen, anteil)
    laenge = bn.weg(punkte[-1], punkt)
    punkte.append(punkt)
    return laenge


def _bogen(punkte, mitte, radius, von, bis, z_von, z_bis, uhr, anteil=1.0):
    """Bögen um `mitte` von Winkel `von` nach `bis` (rad, in Fahrtrichtung), z linear, in Stücken
    von höchstens einem Viertel, mit dem Anteil `anteil` am Vorschub. Gibt die Länge zurück."""
    anzahl = max(1, int(math.ceil(abs(bis - von) / (math.pi / 2) - 1e-9)))
    laenge = 0.0
    for i in range(1, anzahl + 1):
        t = i / anzahl
        winkel = von + (bis - von) * t
        laenge += _hin(
            punkte,
            mitte[0] + radius * math.cos(winkel),
            mitte[1] + radius * math.sin(winkel),
            z_von + (z_bis - z_von) * t,
            bogen=(mitte[0], mitte[1], uhr),
            anteil=anteil,
        )
    return laenge


def _richtung(von, nach):
    dx, dy = nach[0] - von[0], nach[1] - von[1]
    laenge = math.hypot(dx, dy)
    return dx / laenge, dy / laenge


def _geschlossene_lagen(punkte, nut, w, r_l, oben, z_ende, uhr, bei=None):
    """Die Lagen einer geschlossenen Nut in Bögen (Spezifikation Strategien 12.2): je Lage am
    einen Ende die Helix hinab, unten noch einmal rundum – der Kreis um das Ende ist dann frei –
    und weiter bis an die Wand, an der die Bögen beginnen; dann die Bögen (_boegen) bis in den
    Halbkreis am anderen Ende. Die nächste Lage zurück. Beginnt hinten am Kreis um A (der Punkt
    davor liegt dort). Mit `bei` (W-012 E1) an dieser Stelle (_lagen_bei). Gibt (Länge, Lagen,
    Bögen, das Ende, an dem sie aufhört) zurück."""
    if bei is not None:
        return _lagen_bei(punkte, nut, w, r_l, oben, z_ende, uhr, bei)
    R = w.fraeser_radius
    ap = w.zustellung if w.zustellung > GLEICH else 2 * R
    if w.schneidenlaenge > 0:
        ap = min(ap, w.schneidenlaenge)
    tiefe = oben - z_ende
    anzahl = max(1, int(math.ceil(tiefe / ap - 1e-9)))
    schritt = _bogenschritt(r_l, R, min(max(w.zeilenabstand, MIN_SCHRITT), R))
    drehung = -1.0 if uhr else 1.0
    seite = -drehung  # wie in _boegen: Gleichlauf beginnt an der Wand rechts der Fahrt
    steigung = max(
        2 * math.pi * r_l * math.tan(math.radians(max(w.eintauchwinkel, 0.1))), MIN_STEIGUNG
    )
    weg = 0.0
    boegen = 0
    start, ziel = nut.a, nut.b
    z_vorher = oben
    for lage in range(1, anzahl + 1):
        z = oben - tiefe * lage / anzahl
        u = _richtung(start, ziel)
        wand = math.atan2(u[1], u[0]) + seite * math.pi / 2
        jetzt = punkte[-1]
        winkel = math.atan2(jetzt.y - start[1], jetzt.x - start[0])
        # Die Helix ganz herum (am Ende derselbe Winkel), unten noch einmal, dann an die Wand.
        umlaeufe = max(1, int(math.ceil((z_vorher - z) / steigung - 1e-9)))
        ende = winkel + drehung * 2 * math.pi * umlaeufe
        weg += _bogen(punkte, start, r_l, winkel, ende, z_vorher, z, uhr)
        rest = (drehung * (wand - winkel)) % (2 * math.pi)
        weg += _bogen(punkte, start, r_l, ende, ende + drehung * (2 * math.pi + rest), z, z, uhr)
        stueck, n = _boegen(punkte, start, u, r_l, R, schritt, nut.laenge, z, uhr, s_anfang=0.0)
        weg += stueck
        boegen += n
        z_vorher = z
        start, ziel = ziel, start
    return weg, anzahl, boegen, start


def _lagen_bei(punkte, nut, w, r_l, oben, z_ende, uhr, bei):
    """Die Lagen mit fester Eintauchstelle P (Anteil `bei` von A nach B): je Lage die Helix um
    P hinab, unten rundum, die Bögen von P bis in den Halbkreis bei B, im Schnellvorschub durch
    die freie Nut zurück an P und die Bögen bis A; die nächste Lage wieder an P. Wer die Stelle
    wählt, hat einen Grund – vorgebohrt, eine dünne Wand am Ende –, also gilt sie für jede Lage.
    Beginnt hinten am Kreis um P. Gibt (Länge, Lagen, Bögen, das Ende, an dem sie aufhört)
    zurück."""
    R = w.fraeser_radius
    ap = w.zustellung if w.zustellung > GLEICH else 2 * R
    if w.schneidenlaenge > 0:
        ap = min(ap, w.schneidenlaenge)
    tiefe = oben - z_ende
    anzahl = max(1, int(math.ceil(tiefe / ap - 1e-9)))
    schritt = _bogenschritt(r_l, R, min(max(w.zeilenabstand, MIN_SCHRITT), R))
    drehung = -1.0 if uhr else 1.0
    seite = -drehung  # wie in _boegen: Gleichlauf beginnt an der Wand rechts der Fahrt
    steigung = max(
        2 * math.pi * r_l * math.tan(math.radians(max(w.eintauchwinkel, 0.1))), MIN_STEIGUNG
    )
    p = stelle(nut, bei)
    nach_b, nach_a = _richtung(nut.a, nut.b), _richtung(nut.b, nut.a)
    laufe = [
        (nach_b, math.hypot(nut.b[0] - p[0], nut.b[1] - p[1]), nut.b),
        (nach_a, math.hypot(nut.a[0] - p[0], nut.a[1] - p[1]), nut.a),
    ]
    laufe = [lauf for lauf in laufe if lauf[1] > GLEICH]
    weg = 0.0
    boegen = 0
    ende = nut.a
    z_vorher = oben
    for lage in range(1, anzahl + 1):
        z = oben - tiefe * lage / anzahl
        if lage > 1:  # durch die freie Nut zurück an den Kreis um P (auf der Seite des Endes)
            ux, uy = _richtung(p, ende)
            weg += _hin(punkte, p[0] + r_l * ux, p[1] + r_l * uy, z_vorher, anteil=RUECKWEG)
        jetzt = punkte[-1]
        winkel = math.atan2(jetzt.y - p[1], jetzt.x - p[0])
        u = laufe[0][0]
        wand = math.atan2(u[1], u[0]) + seite * math.pi / 2
        umlaeufe = max(1, int(math.ceil((z_vorher - z) / steigung - 1e-9)))
        unten = winkel + drehung * 2 * math.pi * umlaeufe
        weg += _bogen(punkte, p, r_l, winkel, unten, z_vorher, z, uhr)
        rest = (drehung * (wand - winkel)) % (2 * math.pi)
        weg += _bogen(punkte, p, r_l, unten, unten + drehung * (2 * math.pi + rest), z, z, uhr)
        for nummer, (u, laenge, ziel) in enumerate(laufe):
            if nummer:  # zurück an die Wand bei P, an der die Bögen in diese Richtung beginnen
                wand = math.atan2(u[1], u[0]) + seite * math.pi / 2
                ort = (p[0] + r_l * math.cos(wand), p[1] + r_l * math.sin(wand))
                weg += _hin(punkte, ort[0], ort[1], z, anteil=RUECKWEG)
            stueck, n = _boegen(punkte, p, u, r_l, R, schritt, laenge, z, uhr, s_anfang=0.0)
            weg += stueck
            boegen += n
            ende = ziel
        z_vorher = z
    return weg, anzahl, boegen, ende


def _vollnut(punkte, nut, w, oben, z_ende):
    """Zickzack-Rampe längs der Mittellinie hinab, unten einmal eben hinüber. Beginnt an A (der
    Punkt davor liegt dort). Gibt (Länge, das Ende, an dem sie aufhört) zurück."""
    R = w.fraeser_radius
    ap = w.zustellung if w.zustellung > GLEICH else 2 * R
    ap = min(ap, VOLLNUT_AP * 2 * R)
    if w.schneidenlaenge > 0:
        ap = min(ap, w.schneidenlaenge)
    # Hin und zurück schneidet die Rampe zweimal die Stufe: je Fahrt höchstens ap / 2.
    stufe = min(nut.laenge * math.tan(math.radians(max(w.eintauchwinkel, 0.1))), ap / 2)
    stufe = max(stufe, MIN_RAMPE)
    # Der Span in voller Breite so dick wie beim Einsatz mit ae (bahn.Punkt.anteil).
    k = min(max(w.zeilenabstand, GLEICH) / (2 * R), 0.5)
    anteil = 2 * math.sqrt(k * (1 - k))
    z = oben
    dort = nut.b
    weg = 0.0
    while z > z_ende + GLEICH:
        z = max(z - stufe, z_ende)
        weg += _hin(punkte, dort[0], dort[1], z, anteil=anteil)
        dort = nut.a if dort == nut.b else nut.b
    weg += _hin(punkte, dort[0], dort[1], z_ende, anteil=anteil)
    return weg, dort


def _rundum(punkte, nut, r_w, z, ende, uhr):
    """Einmal rundum an der Wand (die Mitte des Fräsers r_w neben der Mittellinie): aus der Mitte
    des Endes `ende` im Halbkreis hinaus, die Runde, im Halbkreis zurück. Der Punkt davor liegt
    in der Mitte des Endes. Gibt die Länge zurück."""
    anderes = nut.b if ende == nut.a else nut.a
    ux, uy = _richtung(ende, anderes)
    drehung = -1.0 if uhr else 1.0
    # Gegen den Uhrzeigersinn (Gleichlauf) beginnt die Runde rechts der Mittellinie.
    qx, qy = drehung * uy, -drehung * ux
    seite = math.atan2(qy, qx)
    rand = (ende[0] + r_w * qx, ende[1] + r_w * qy)
    halb = ((ende[0] + rand[0]) / 2, (ende[1] + rand[1]) / 2, uhr)
    weg = _hin(punkte, rand[0], rand[1], z, bogen=halb)
    weg += _hin(punkte, anderes[0] + r_w * qx, anderes[1] + r_w * qy, z)
    weg += _bogen(punkte, anderes, r_w, seite, seite + drehung * math.pi, z, z, uhr)
    weg += _hin(punkte, ende[0] - r_w * qx, ende[1] - r_w * qy, z)
    gegen = seite + math.pi
    weg += _bogen(punkte, ende, r_w, gegen, gegen + drehung * math.pi, z, z, uhr)
    weg += _hin(punkte, ende[0], ende[1], z, bogen=halb)
    return weg


def _schlichten(punkte, nut, w, r_w, oben, z_ende, ende, uhr):
    """Die Wand rundum in Zügen von höchstens der Schneidenlänge, von oben. Gibt die Länge
    zurück."""
    hoehe = min(oben, nut.z_oben) - z_ende
    anzahl = 1
    if 0 < w.schneidenlaenge < hoehe - GLEICH:
        anzahl = max(1, int(math.ceil(hoehe / w.schneidenlaenge - 1e-9)))
    weg = 0.0
    for i in range(1, anzahl + 1):
        z = min(oben, nut.z_oben) - hoehe * i / anzahl
        weg += _hin(punkte, ende[0], ende[1], z)
        weg += _rundum(punkte, nut, r_w, z, ende, uhr)
    return weg


def _vor_dem_ende(punkte, nut, ende, z, w, knapp):
    """Bringt den Fräser vor das offene Ende `ende` (FREI_VOR hinter dem Rand) auf die Höhe z –
    steht er schon dort, nur hinab (in der Luft); sonst hinauf, hin und im Eilgang bis knapp
    über z. Gibt (den Punkt draußen, die Länge im Vorschub) zurück."""
    anderes = nut.b if ende == nut.a else nut.a
    ux, uy = _richtung(anderes, ende)
    weit = w.fraeser_radius + FREI_VOR
    draussen = (ende[0] + ux * weit, ende[1] + uy * weit)
    letzter = punkte[-1] if punkte else None
    dort = (
        letzter is not None
        and abs(letzter.x - draussen[0]) < GLEICH
        and abs(letzter.y - draussen[1]) < GLEICH
    )
    if not dort:
        if letzter is not None:
            punkte.append(bn.Punkt(True, letzter.x, letzter.y, knapp))
        punkte.append(bn.Punkt(True, draussen[0], draussen[1], knapp))
        punkte.append(bn.Punkt(True, draussen[0], draussen[1], z + w.sicherheit))
    return draussen, _hin(punkte, draussen[0], draussen[1], z)


def _offen_bei(nut, ende):
    return nut.offen_a if ende == nut.a else nut.offen_b


def _bogenschritt(r_l, R, ae):
    """So weit rücken die Bögen vor (mm) – ae ist die Last (Spezifikation Strategien 12.1 (a);
    Manuel, 2026-10-02: „im Mittel … Sogar 25 %, solange es noch über r geht“).

    Je Bogen nimmt der Fräser (Radius R, seine Mitte auf dem Bogen mit dem Radius r_l) den
    Streifen zwischen zwei Dellen (Radius ρ = r_l + R) im Abstand s: 2 ρ s auf π r_l + s Weg
    (der Halbkreis, das Stück an der Wand; quer zurück fährt er in der Luft). Im Mittel so viel
    je mm wie auf gerader Bahn mit ae: s = π r_l ae / (2 ρ − ae). Auf dem Bogen wächst die
    Breite im Eingriff von 0 an der Wand bis in die Mitte und fällt wieder – im Winkel θ vom
    Scheitel t (2 ρ − t) / (2 r_l) mit t = s cos θ, in der Mitte etwa π/2 · ae. Dort höchstens
    bahn.LAST_KURZ · ae; über bahn.LAST_DAUERND · ae höchstens UEBER_WEG Fräserbreiten Weg am
    Stück – das begrenzt den Schritt in breiten Nuten, wo die Bögen lang sind. Nie über r: In
    der Delle umschlingt der Fräser das Material höchstens wie eine gerade Wand mit ae = R
    (Eingriffswinkel 90°) – aus den Kreisen um die alte und die neue Mitte der Delle:
    s² + 2 r_l s ≤ 2 r_l R."""
    if r_l <= GLEICH:
        return MIN_SCHRITT
    rho = r_l + R

    def bis(last, cos):
        # So groß darf s sein, damit die Breite bei cos θ höchstens `last` ist.
        rest = rho * rho - 2.0 * last * r_l
        if rest < 0.0 or cos <= GLEICH:
            return math.inf
        return (rho - math.sqrt(rest)) / cos

    schritt = math.pi * r_l * ae / (2.0 * rho - ae)
    schritt = min(schritt, bis(bn.LAST_KURZ * ae, 1.0))
    halb = UEBER_WEG * R / r_l  # der halbe Weg über LAST_DAUERND, als Winkel auf dem Bogen
    if halb < math.pi / 2:
        schritt = min(schritt, bis(bn.LAST_DAUERND * ae, math.cos(halb)))
    schritt = min(schritt, -r_l + math.sqrt(r_l * r_l + 2.0 * r_l * R))
    return max(MIN_SCHRITT, schritt)


def _boegen(punkte, start, u, r_l, R, schritt, s_bis, z, uhr, s_anfang=None):
    """Die Bögen einer Lage vom Ende `start` in Richtung `u` bis zum Halbkreis um die Mitte bei
    s_bis (die Mitte des Fräsers r_l neben der Mittellinie an den Wänden): je Bogen im
    Gleichlauf von der einen Wand nach vorn durchs Material zur anderen, quer über die freie
    Seite zurück im Schnellvorschub, an der Wand vor in den nächsten. Ohne `s_anfang` (offenes
    Ende) liegt der Punkt davor draußen vor dem Ende, in der Luft, und zuerst morphen die Bögen
    vom geraden Rand zum Halbkreis: ihre Enden bei −R (der Fräser berührt den Rand gerade), ihre
    Mitte je Bogen um `schritt` weiter. Mit `s_anfang` (geschlossene Nut) ist der Kreis um die
    Mitte bei s_anfang schon frei (die Helix), der Fräser steht dort an der Wand, an der die
    Bögen beginnen: gleich Halbkreise, der erste einen Schritt weiter. Gibt (Länge, Bögen)
    zurück."""
    drehung = -1.0 if uhr else 1.0
    v = (-u[1], u[0])  # links der Fahrt
    seite = -drehung  # Gleichlauf (gegen den Uhrzeigersinn): von der Wand rechts nach links
    richtung = math.atan2(u[1], u[0])

    def ort(s, q):
        return (start[0] + u[0] * s + v[0] * q, start[1] + u[1] * s + v[1] * q)

    if s_anfang is None:
        s_w = -R
        weg = _hin(punkte, *ort(s_w, seite * r_l), z)  # draußen an die Wand, in der Luft
        tiefen = []
        b = schritt
        while b < r_l - GLEICH:
            tiefen.append(b)
            b += schritt
        tiefen.append(r_l)
    else:
        s_w = min(s_anfang + schritt, s_bis)
        weg = _hin(punkte, *ort(s_w, seite * r_l), z)  # an der Wand vor
        tiefen = [r_l]
    boegen = 0
    while True:
        for b in tiefen:
            # Der Bogen durch die Enden an den Wänden und die Mitte b vor ihnen.
            rho = (r_l * r_l + b * b) / (2.0 * b)
            mitte = ort(s_w + b - rho, 0.0)
            winkel = math.atan2(seite * r_l, rho - b)
            weg += _bogen(punkte, mitte, rho, richtung + winkel, richtung - winkel, z, z, uhr)
            boegen += 1
            if s_w >= s_bis - GLEICH and b >= r_l - GLEICH:
                return weg, boegen
            # Quer zurück über die freie Seite, im Schnellvorschub.
            weg += _hin(punkte, *ort(s_w, seite * r_l), z, anteil=RUECKWEG)
        # Nur noch Halbkreise: an der Wand um `schritt` vor.
        tiefen = [r_l]
        s_w = min(s_w + schritt, s_bis) if s_w < s_bis - GLEICH else s_bis
        weg += _hin(punkte, *ort(s_w, seite * r_l), z)


def _offene_lagen(punkte, nut, w, vollnut, r_l, oben, z_ende, uhr, knapp):
    """Die Lagen einer offenen Nut: jede von einem offenen Ende im Freien hinab und hinein – in
    Bögen (_boegen) oder geradeaus in voller Breite –, am anderen Ende hinaus ins Freie; vor
    einem Halbkreis hinauf und die nächste Lage wieder von außen. Gibt (Länge, Lagen, Bögen, das
    Ende, an dem sie aufhört) zurück."""
    R = w.fraeser_radius
    ap = w.zustellung if w.zustellung > GLEICH else 2 * R
    if vollnut:
        ap = min(ap, VOLLNUT_AP * 2 * R)
    if w.schneidenlaenge > 0:
        ap = min(ap, w.schneidenlaenge)
    tiefe = oben - z_ende
    anzahl = max(1, int(math.ceil(tiefe / ap - 1e-9)))
    schritt = _bogenschritt(r_l, R, min(max(w.zeilenabstand, MIN_SCHRITT), R))
    # Der Span in voller Breite so dick wie beim Einsatz mit ae (wie _vollnut).
    k = min(max(w.zeilenabstand, GLEICH) / (2 * R), 0.5)
    anteil = 2 * math.sqrt(k * (1 - k))
    start = nut.a if nut.offen_a else nut.b
    weg = 0.0
    boegen = 0
    for lage in range(1, anzahl + 1):
        z = oben - tiefe * lage / anzahl
        if not _offen_bei(nut, start):
            start = nut.b if start == nut.a else nut.a  # zurück zum offenen Ende, von außen
        ziel = nut.b if start == nut.a else nut.a
        u = _richtung(start, ziel)
        _draussen, stueck = _vor_dem_ende(punkte, nut, start, z, w, knapp)
        weg += stueck
        if vollnut:
            weg += _hin(punkte, start[0], start[1], z, anteil=anteil)
        else:
            stueck, n = _boegen(punkte, start, u, r_l, R, schritt, nut.laenge, z, uhr)
            weg += stueck
            boegen += n
        if _offen_bei(nut, ziel):
            weit = R + FREI_VOR
            if vollnut:
                weg += _hin(punkte, ziel[0], ziel[1], z, anteil=anteil)
            weg += _hin(punkte, ziel[0] + u[0] * weit, ziel[1] + u[1] * weit, z)
        elif vollnut:
            weg += _hin(punkte, ziel[0], ziel[1], z, anteil=anteil)
        start = ziel
    return weg, anzahl, boegen, start


def _offen_schlichten(punkte, nut, w, r_w, oben, z_ende, uhr, knapp):
    """Die Wände einer offenen Nut im Gleichlauf (das Material rechts): vom offenen Ende an der
    einen Wand hinein, außen hinüber oder um den Halbkreis, an der anderen heraus – in Zügen von
    höchstens der Schneidenlänge, von oben. Gibt die Länge zurück."""
    hoehe = min(oben, nut.z_oben) - z_ende
    anzahl = 1
    if 0 < w.schneidenlaenge < hoehe - GLEICH:
        anzahl = max(1, int(math.ceil(hoehe / w.schneidenlaenge - 1e-9)))
    start = nut.a if nut.offen_a else nut.b
    ziel = nut.b if start == nut.a else nut.a
    ux, uy = _richtung(start, ziel)
    vx, vy = -uy, ux  # links der Fahrt von start nach ziel
    weit = w.fraeser_radius + FREI_VOR
    # Gleichlauf: hinein mit der Wand rechts – auf der Seite −v; Gegenlauf auf +v.
    seite = 1.0 if uhr else -1.0
    weg = 0.0
    for i in range(1, anzahl + 1):
        z = min(oben, nut.z_oben) - hoehe * i / anzahl
        aussen = (start[0] - ux * weit, start[1] - uy * weit)
        hin = (aussen[0] + seite * vx * r_w, aussen[1] + seite * vy * r_w)
        letzter = punkte[-1]
        if abs(letzter.x - hin[0]) > GLEICH or abs(letzter.y - hin[1]) > GLEICH:
            punkte.append(bn.Punkt(True, letzter.x, letzter.y, knapp))
            punkte.append(bn.Punkt(True, hin[0], hin[1], knapp))
            punkte.append(bn.Punkt(True, hin[0], hin[1], z + w.sicherheit))
        weg += _hin(punkte, hin[0], hin[1], z)
        if _offen_bei(nut, ziel):
            draussen = (ziel[0] + ux * weit, ziel[1] + uy * weit)
            weg += _hin(punkte, draussen[0] + seite * vx * r_w, draussen[1] + seite * vy * r_w, z)
            weg += _hin(punkte, draussen[0] - seite * vx * r_w, draussen[1] - seite * vy * r_w, z)
        else:
            weg += _hin(punkte, ziel[0] + seite * vx * r_w, ziel[1] + seite * vy * r_w, z)
            von = math.atan2(seite * vy, seite * vx)
            drehung = -1.0 if uhr else 1.0
            weg += _bogen(punkte, ziel, r_w, von, von + drehung * math.pi, z, z, uhr)
        weg += _hin(punkte, aussen[0] - seite * vx * r_w, aussen[1] - seite * vy * r_w, z)
    return weg


def verfahren(nut, fraeser_radius, aufmass=0.0, offen_breit=True):
    """Wie der Fräser mit dem Radius die Nut fräst: „boegen“, „vollnut“ – oder „zu_schmal“ (er
    passt nicht hinein), „zu_breit“ (in der Mitte der Helix bliebe ein Kern; in offenen Nuten
    nicht – ihre Bögen kommen von außen –, außer `offen_breit` ist aus: Plan indexiert fräst
    eine breite Abflachung in Zeilen)."""
    R = fraeser_radius
    if nut.radius < R - 1e-3:
        return "zu_schmal"
    r_l = nut.radius - R - max(aufmass, 0.0)
    if r_l > KERN_ANTEIL * R + GLEICH and not (nut.offen and offen_breit):
        return "zu_breit"
    return "vollnut" if r_l < VOLLNUT_ANTEIL * R else "boegen"


def schluessel(nut):
    """Woran man die Nut wiedererkennt (ihre Eintauchstelle merkt sich die Operation so): der
    Name ihrer ersten Wand."""
    return nut.waende[0] if nut.waende else f"{nut.a[0]:.3f},{nut.a[1]:.3f}"


def stelle(nut, anteil):
    """Der Punkt (x, y) auf der Mittellinie beim Anteil `anteil` (0: A, 1: B)."""
    return (
        nut.a[0] + (nut.b[0] - nut.a[0]) * anteil,
        nut.a[1] + (nut.b[1] - nut.a[1]) * anteil,
    )


def anteil_bei(nut, x, y):
    """Der Anteil der Stelle auf der Mittellinie, die (x, y) am nächsten liegt (0 … 1)."""
    dx, dy = nut.b[0] - nut.a[0], nut.b[1] - nut.a[1]
    laenge2 = dx * dx + dy * dy
    if laenge2 < GLEICH:
        return 0.0
    return min(1.0, max(0.0, ((x - nut.a[0]) * dx + (y - nut.a[1]) * dy) / laenge2))


def vorschlag_bei(nut, w, stand, r_l):
    """Der Vorschlag für die Eintauchstelle (W-012 E1; Manuel: „an einer von mir aus wählbaren
    Position in der Nut … aber natürlich mit Vorschlag“): Längs der Mittellinie (alle
    EINTAUCH_RASTER) das Material im Kreis des Fräsers über dem Grund – dort taucht er ein, die
    Helix um r_l räumt danach rundum; liegt eine Stelle um EINTAUCH_WENIGER unter dem an den
    Enden – eine Bohrung oder Tasche kreuzt die Nut –, dort. Sonst None: abwechselnd an den
    Enden, wie bisher (die Lagen ohne Weg zurück). Im Kreis der ganzen Helix (r_l + R) fiele eine
    Bohrung kleiner als der Fräser kaum ins Gewicht."""
    if stand is None or nut.laenge < GLEICH or r_l <= GLEICH:
        return None
    grund = nut.z_unten - max(w.tiefer, 0.0) if nut.durch else nut.z_unten
    anzahl = max(1, int(math.ceil(nut.laenge / EINTAUCH_RASTER)))
    werte = []
    for i in range(anzahl + 1):
        anteil = i / anzahl
        q = stelle(nut, anteil)
        noch, _weg = stand.volumen(stand.maske_um(q, q, w.fraeser_radius), grund)
        werte.append((noch, anteil))
    an_den_enden = min(werte[0][0], werte[-1][0])
    wenigste = min(werte)
    if wenigste[0] < EINTAUCH_WENIGER * an_den_enden:
        return wenigste[1]
    return None


def _maske(nut, w, stand):
    """Wo der Fräser in und an der Nut fährt – die Maske im Materialstand: die Nut selbst;
    an einer offenen Nut dazu der Weg draußen vor dem offenen Ende, wo er hinab fährt."""
    if not nut.offen:
        return stand.maske_um(nut.a, nut.b, nut.radius)
    return stand.maske_um(nut.a, nut.b, nut.radius + 2.0 * w.fraeser_radius + kb.NAH + 1.0)


def _oben(nut, w, stand, z_ende):
    """Wo die Lagen der Nut beginnen: am Rohteil (w.oben) – mit Materialstand (W-012) am
    höchsten Material, das in ihr noch steht; z_ende, wenn dort nichts mehr steht."""
    if stand is None:
        return w.oben
    hoechste = stand.hoechste(_maske(nut, w, stand))
    if hoechste is None or hoechste <= z_ende + MATERIAL_SPIEL:
        return z_ende
    return min(w.oben, hoechste)


def _nut(punkte, nut, w, stand=None, bei=None):
    """Eine Nut: in Bögen oder als Vollnut, dann rundum. Gibt (Länge, Lagen, Bögen, vollnut,
    z_min) zurück; (0, 0, 0, False, inf), wenn über ihr nichts steht. `stand`: der
    Materialstand (materialstand) – die Lagen beginnen dann, wo in der Nut noch Material ist.
    `bei`: die Eintauchstelle (Anteil von A nach B) – die geschlossene Nut taucht in jeder Lage
    dort ein; die Vollnut beginnt ihre Rampe am Ende, das ihr am nächsten liegt."""
    R = w.fraeser_radius
    aufmass = max(w.aufmass, 0.0) if w.schlichten else 0.0
    art = verfahren(nut, R, aufmass)
    breite = einheiten.text(2 * nut.radius, einheiten.LAENGE)
    if art == "zu_schmal":
        fraeser = einheiten.text(2 * R, einheiten.LAENGE)
        raise ValueError(tr("nt.fehler.zu_schmal", breite=breite, fraeser=fraeser))
    if art == "zu_breit":
        raise ValueError(tr("nt.fehler.zu_breit", breite=breite))
    r_w = max(nut.radius - R, 0.0)  # die Mitte des Fräsers an der Wand
    r_l = nut.radius - R - aufmass  # … auf den Bögen
    z_ende = nut.z_unten - max(w.tiefer, 0.0) if nut.durch else nut.z_unten
    oben = _oben(nut, w, stand, z_ende)
    if oben <= z_ende + GLEICH:
        return 0.0, 0, 0, False, math.inf
    uhr = not w.gleichlauf  # Gleichlauf in der Nut: gegen den Uhrzeigersinn (G3)
    vollnut = art == "vollnut"
    knapp = min(w.sicher, oben + w.sicherheit)
    if nut.offen:
        start = nut.a if nut.offen_a else nut.b
        punkte.append(bn.Punkt(True, start[0], start[1], w.sicher))
        weg, lagen, boegen, _ende = _offene_lagen(
            punkte, nut, w, vollnut, r_l, oben, z_ende, uhr, knapp
        )
        if r_w > GLEICH and (w.schlichten or vollnut):
            weg += _offen_schlichten(punkte, nut, w, r_w, oben, z_ende, uhr, knapp)
        letzter = punkte[-1]
        punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
        return weg, (1 if vollnut else lagen), boegen, vollnut, z_ende
    if vollnut and bei is not None and bei > 0.5:
        nut = replace(nut, a=nut.b, b=nut.a)  # die Rampe beginnt am Ende bei der Stelle
    if vollnut:
        start = nut.a
    else:
        ux, uy = _richtung(nut.a, nut.b)
        mitte = stelle(nut, bei) if bei is not None else nut.a
        start = (mitte[0] - r_l * ux, mitte[1] - r_l * uy)  # hinten am Kreis um die Stelle
    punkte.append(bn.Punkt(True, start[0], start[1], w.sicher))
    punkte.append(bn.Punkt(True, start[0], start[1], knapp))
    punkte.append(bn.Punkt(False, start[0], start[1], oben, True))
    weg = bn.weg(punkte[-2], punkte[-1])
    if vollnut:
        stueck, ende = _vollnut(punkte, nut, w, oben, z_ende)
        lagen, boegen = 1, 0
    else:
        stueck, lagen, boegen, ende = _geschlossene_lagen(
            punkte, nut, w, r_l, oben, z_ende, uhr, bei
        )
    weg += stueck
    if r_w > GLEICH and (w.schlichten or vollnut):
        weg += _schlichten(punkte, nut, w, r_w, oben, z_ende, ende, uhr)
    letzter = punkte[-1]
    punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
    return weg, lagen, boegen, vollnut, z_ende


def planen(werte, liste, stand=None):
    """Die Bahn „Nut“ (Nutbahn) für die Nuten `liste` ([Nut]) mit den Werten `werte`.
    `stand`: der Materialstand vor der Nut (W-012) – jede Nut beginnt dann, wo in ihr noch
    Material steht, und die Bahn sagt, was noch zu tun ist. ValueError mit einem Satz, wenn es
    nicht geht."""
    w = werte
    if w.fraeser_radius <= 0:
        raise ValueError(tr("nt.fehler.form"))
    if w.zustellung <= 0 or w.zeilenabstand <= 0:
        raise ValueError(tr("nt.fehler.werte"))
    if not liste:
        raise ValueError(tr("nt.fehler.keine"))
    # Die kürzeste Reihenfolge: immer zur nächsten.
    offen = list(liste)
    folge = []
    ort = offen[0].a
    while offen:
        naechste = min(offen, key=lambda n: math.hypot(n.a[0] - ort[0], n.a[1] - ort[1]))
        offen.remove(naechste)
        folge.append(naechste)
        ort = naechste.b
    punkte = []
    laenge = 0.0
    lagen = boegen = vollnut = gefraest = 0
    z_min = math.inf
    noch = weg = 0.0
    davor = []
    stellen = []
    for nut in folge:
        if stand is not None:
            maske = stand.maske_um(nut.a, nut.b, nut.radius)
            grund = nut.z_unten - max(w.tiefer, 0.0) if nut.durch else nut.z_unten
            n_noch, n_weg = stand.volumen(maske, grund)
            noch += n_noch
            weg += n_weg
            davor += [name for name in stand.wer(maske) if name not in davor]
        bei, vorgeschlagen = _bei(nut, w, stand)
        if not nut.offen:
            stellen.append((schluessel(nut), bei, vorgeschlagen, nut.a, nut.b))
        stueck, n_lagen, n_boegen, ist_voll, z = _nut(punkte, nut, w, stand, bei)
        if not n_lagen:
            continue
        gefraest += 1
        laenge += stueck
        lagen += n_lagen
        boegen += n_boegen
        vollnut += int(ist_voll)
        z_min = min(z_min, z)
    if not gefraest:
        if davor:
            from . import materialstand as mst  # erst hier: es bringt den Job mit

            raise mst.schon_weg(davor)
        raise ValueError(tr("nt.fehler.nichts"))
    zeit = bn.zeit(punkte, w.vorschub if w.vorschub > 0 else 1000.0, w.eintauchen or None)
    return Nutbahn(
        punkte, gefraest, lagen, boegen, vollnut, z_min, laenge, zeit, noch, weg, davor, stellen
    )


def _bei(nut, w, stand):
    """(Anteil oder None, vorgeschlagen?) – die gewählte Eintauchstelle der Nut, sonst der
    Vorschlag; offene Nuten tauchen draußen ein (None)."""
    if nut.offen:
        return None, True
    gewaehlt = (w.eintauchen_bei or {}).get(schluessel(nut))
    if gewaehlt is not None:
        return min(1.0, max(0.0, float(gewaehlt))), False
    aufmass = max(w.aufmass, 0.0) if w.schlichten else 0.0
    r_l = nut.radius - w.fraeser_radius - aufmass
    return vorschlag_bei(nut, w, stand, max(r_l, 0.0)), True
