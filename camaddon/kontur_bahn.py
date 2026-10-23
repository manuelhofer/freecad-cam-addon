# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Bahn „Kontur“ (W-006 S3, 4.1 Punkt 4): an gewählten Wänden entlang – außen um einen
Zapfen, innen in einer Tasche, oder an einer einzelnen Wand – mit tangentialem Ein- und
Ausfahren, Schruppen in Lagen mit Aufmaß und Schlichten in einem Zug.

- Wände (waende()): senkrechte Flächen des Teils mit waagerechter Unterkante – eben,
  zylindrisch oder Freiform, wenn sie überall senkrecht steht. Ihre Unterkanten verbinden sich
  zu Konturen (konturen()): geschlossen rundum oder offen (eine Wand, ein Absatz). Wo die freie
  Seite liegt, sagt die Außennormale der Wand.
- Je Kontur die Bahnen als Versatz der Unterkanten (Part.Wire.makeOffset2D: Ecken außen werden
  Bögen, innen schneiden sich die Geraden): Schruppen bei Radius + Aufmaß + k · Zeilenabstand,
  von außen her zur Wand hin, so viele, wie neben der Wand Rohteil steht (oder die Breite
  sagt); in Lagen von der Oberkante des Rohteils bis auf die Unterkante (plus „tiefer“). Dann
  das Schlichten bei Radius: in einem Zug über die ganze Höhe, höchstens die Schneidenlänge je
  Zug.
- Gleichlauf (Grundsatz 4): Bei rechtsdrehender Spindel (M3) liegt das Material rechts der
  Fahrtrichtung (wie G41) – um einen Zapfen im Uhrzeigersinn, in einer Tasche gegen ihn.
- Tangential hinein und heraus: eine Gerade (GERADE_ANTEIL · R) und ein Viertelkreis
  (EINFAHRT_ANTEIL · R) auf der freien Seite; passt das nicht (Hüllfläche, oder es käme einer
  Wand der Konturen näher als die Bahn darf – Radius plus Aufmaß), kürzer, zuletzt senkrecht. Im Material über die Rampe (vierachs_bahn._rampe) längs der Bahn, in der Luft
  senkrecht mit dem Eintauchvorschub.
- Die Hüllfläche (hoehenfeld.je_zeile im Raster – das Teil ohne die Wände, ohne die Flächen
  an ihren waagerechten Kanten und ohne die, die an einer senkrechten Kante eine Außenecke
  bilden, ohne_flaechen()) hält jede Bahn vor Absätzen und anderen Wänden an, die zur Bahn hin
  abknicken; wo kein Rohteil liegt, fährt keine Bahn (Grundsatz 5); beim Austritt aus dem Rohteil
  langsamer.
- Mit Materialstand (W-012, materialstand): Was die Operationen davor schon weggenommen haben,
  fräst sie nicht noch einmal. Zeigt er dort, wohin die Stirn kommt, nicht überall das ganze
  Rohteil, fährt jede Schruppbahn je Lage nur, wo ihre Stirn (eine Zelle kleiner) Material über
  der Lage trifft – über eine kurze Lücke im Vorschub –, die Lagen beginnen am höchsten solchen
  Material, und wo beim Eintauchen nichts steht, geht es senkrecht hinab statt über die Rampe.
  Danach fährt sie einmal beim Aufmaß an der Wand ab, über die ganze Höhe (Manuel: „fahr die
  Kontur zumindest einmal auf 0,3 einfach an der Kontur ab“) – einen Rand, schmaler als das
  Raster, sieht der Materialstand nicht; so nimmt das Schlichten nie mehr als das Aufmaß.

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field

import numpy as np

from . import bahn as bn
from . import formteile as ft
from . import hoehenfeld as hf
from . import vierachs_bahn as vb
from . import vierachs_planbahn as vp
from .sprache import tr

SCHRITT = 0.5  # mm – Raster längs der Bahn und für die Hüllfläche
VORSCHAU_SCHRITT = 1.0  # mm – für die Vorschau im Assistenten
EINFAHRT_ANTEIL = 1.0  # vom Fräserradius: der Viertelkreis hinein und heraus
GERADE_ANTEIL = 1.0  # vom Fräserradius: die Gerade vor dem Bogen
AUSTRITT_ANTEIL = 0.5  # vom Vorschub: so langsam beim Austritt aus dem Rohteil
SENKRECHT = 1e-6  # so wenig darf die Normale einer Wand von waagerecht abweichen
NAH = 1e-5  # mm – so nah ist dieselbe Stelle
WANDHOEHE_SCHRITT = 1.0  # mm – so dicht wird die Höhe einer Wand über ihrer Unterkante abgefragt
HOECHSTENS_VERSAETZE = 200  # so viele Schruppbahnen je Kontur höchstens (vom Rohteil her)
WAND_SPIEL = 0.05  # mm – so viel näher an eine Wand darf das Ein- und Ausfahren (Sehnen der Kette)
KNICK = 1e-3  # rad – so weit muss ein Linienzug abknicken, damit der Punkt eine Ecke ist
ABSTAND_STUECK = 2_000_000  # so viele Paare (Stelle, Ecke) rechnet _Huelle.zu_nah auf einmal
REST_SPIEL = 0.02  # mm – so weit muss der kleine Fräser aus dem großen ragen, damit er dort fährt
GLEICH = vb.GLEICH
# Mit Materialstand: So viel muss über einer Lage stehen, damit es als Material zählt. Eine Lücke im
# Weggefrästen, so lang wie höchstens LUECKE Durchmesser (mindestens LUECKE_MIN), fährt die Bahn im
# Vorschub durch, statt abzuheben und wieder einzufahren – wie beim Räumen.
MATERIAL = 0.05  # mm
BOGEN_SEHNE = 0.5  # mm – so lang sind die Sehnen, mit denen _abtragen einen Bogen abträgt
LUECKE = 2.0
LUECKE_MIN = 20.0  # mm


@dataclass(frozen=True)
class Konturwerte:
    """Was die Kontur braucht; Längen in mm, z nach oben im Job."""

    form: object  # fraeserform.Form des Fräsers – mit ebener Stirn
    zustellung: float  # ap: höchstens so tief je Lage beim Schruppen
    zeilenabstand: float  # ae: höchstens so weit liegen die Schruppbahnen auseinander
    aufmass: float  # bleibt beim Schruppen an der Wand stehen – fürs Schlichten
    schlichten: bool  # danach bei Radius in einem Zug
    oben: float  # z der Oberkante: das Rohteil (hier beginnen die Lagen)
    sicher: float  # z für den Eilgang über allem
    rohteil: tuple  # (x_von, x_bis, y_von, y_bis) des Rohteils von oben
    breite: float = 0.0  # so viel Material steht neben der Wand; 0: so viel, wie das Rohteil sagt
    tiefer: float = 0.0  # so viel tiefer als die Unterkante der Wand
    einfahrradius: float = None  # der Viertelkreis hinein und heraus; None: der Vorschlag
    schneidenlaenge: float = 0.0  # 0: unbekannt – das Schlichten in einem Zug
    sicherheit: float = vb.SICHERHEIT  # so weit über dem Material endet der Eilgang hinab
    eintauchwinkel: float = vb.EINTAUCHWINKEL  # Grad, für die Rampe ins Material
    austritt: float = AUSTRITT_ANTEIL
    # (Kontur, x, y) → bool je Stelle: nur dort fahren – None: überall (Restmaterial:
    # nur_wo_der_grosse_nicht_hinkam).
    nur_wo: object = None
    # Das Material rechts der Fahrtrichtung (Gleichlauf bei M3); False: links – Gleichlauf bei
    # rückwärts drehender Spindel (M4, P-2026-10-02-20).
    gleichlauf: bool = True


@dataclass
class Konturbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    konturen: int  # so viele Konturen gefahren
    lagen: int  # Lagen über alle Konturen – Schruppen und Schlichten
    bahnen: int  # Bahnen über alle Konturen und Lagen (je mit Ein- und Ausfahren)
    z_min: float  # die tiefste Spitze (mm)
    laenge: float  # mm im Vorschub
    # Mit Materialstand (W-012): was dort, wohin die Stirn kommt, über dem Teil noch steht und was
    # die Operationen davor dort schon weggenommen haben (mm³), und ihre Namen.
    noch: float = 0.0
    weg: float = 0.0
    davor: list = field(default_factory=list)


@dataclass(frozen=True)
class Wand:
    """Eine gewählte Wand: eine senkrechte Fläche mit waagerechter Unterkante (waende())."""

    name: str  # „Face3“
    nummer: int  # 0 …
    flaeche: object  # Part.Face
    z_unten: float
    z_oben: float
    kanten: tuple  # die Unterkanten (Part.Edge), alle bei z_unten
    # Je Unterkante (_schluessel) ihre Stücke gleicher Höhe (_wandkanten) – einmal gerechnet: Die
    # Wand selbst ist je Form gemerkt (_WAND), die Vorschau fragt je Lauf zehnmal (konturen).
    stuecke: dict = field(default_factory=dict, compare=False, repr=False)


@dataclass
class Kontur:
    """Eine Kette von Unterkanten (konturen()) – geschlossen oder offen."""

    draht: object  # Part.Wire der Unterkanten, bei z_unten
    z_unten: float
    z_oben: float  # die höchste Wand der Kette
    geschlossen: bool
    stelle: tuple  # (x, y) auf der längsten Unterkante
    normale: tuple  # (nx, ny) dort, zur freien Seite (vom Material weg)
    waende: tuple  # die Namen der Wände
    # Je Wand ihre Unterkanten mit ihrer eigenen Höhe: [(x, y, z_oben)] – für den Abstand, den
    # das Ein- und Ausfahren einer anderen Kontur zu ihr hält (P-2026-10-03-34: Die Inselkontur
    # des Testteils galt mit ihren zwei Wänden, die bis zur Stufe durchgehen, überall als 32
    # hoch – die Stufenwand bei z 22 fand neben der Inselkante keinen Eingang und fuhr Rampen).
    wandkanten: tuple = ()


# --- Wände und Konturen -----------------------------------------------------------------------


def ist_wand(flaeche):
    """Steht die Fläche senkrecht – ihre Normale überall waagerecht?"""
    try:
        u0, u1, v0, v1 = flaeche.ParameterRange
        for i in range(3):
            for j in range(3):
                u = u0 + (u1 - u0) * (2 * i + 1) / 6
                v = v0 + (v1 - v0) * (2 * j + 1) / 6
                n = flaeche.normalAt(u, v)
                if n.Length < 0.5 or abs(n.z) > SENKRECHT * n.Length:
                    return False
    except Exception:  # OCC: entartete Fläche
        return False
    return True


def _waagerecht(kante, z):
    if any(abs(v.Point.z - z) > NAH for v in kante.Vertexes):
        return False
    mitte = kante.valueAt((kante.FirstParameter + kante.LastParameter) / 2)
    return abs(mitte.z - z) <= NAH


def waende(form, namen):
    """[Wand] – die Flächen `namen` („Face3“ …) von `form` (Part.Shape), die senkrecht stehen und
    eine waagerechte Unterkante haben; andere zählen nicht. Je Fläche einmal gerechnet (_WAND):
    Der Assistent „Bearbeitung“ fragt je Vorschau über tausendmal nach denselben Flächen
    (P-2026-10-03-28, wie hoehenfeld.ebenen_oben)."""
    from . import vierachs_flaechen as vf

    anzahl = ft.anzahl(form)
    ergebnis = []
    for nummer in vf.nummern(namen):
        if nummer >= anzahl:
            continue
        wand = _wand(form, nummer)
        if wand is not None:
            ergebnis.append(wand)
    return ergebnis


_WAND = {}  # (Prüfsumme der Form, Nummer, Kasten der Fläche) → Wand oder None
_WAND_HOECHSTENS = 20000


def _wand(form, nummer):
    """Die Wand der Fläche `nummer` – oder None, wenn sie keine ist."""
    flaeche = ft.flaeche(form, nummer)
    bb = flaeche.BoundBox
    try:
        # Die Prüfsumme hängt am Speicher – mit dem Kasten der Fläche dazu verwechselt eine neue
        # Form an derselben Stelle ihre Flächen nicht mit den alten (wie hoehenfeld._ebene).
        schluessel = (
            form.hashCode(),
            nummer,
            tuple(round(v, 6) for v in (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)),
        )
    except Exception:  # eine Form ohne Prüfsumme: rechnen
        schluessel = None
    if schluessel is not None and schluessel in _WAND:
        return _WAND[schluessel]
    wand = None
    if ist_wand(flaeche) and bb.ZMax - bb.ZMin > NAH:
        kanten = tuple(k for k in flaeche.Edges if _waagerecht(k, bb.ZMin))
        if kanten:
            wand = Wand(
                f"Face{nummer + 1}", nummer, flaeche, float(bb.ZMin), float(bb.ZMax), kanten
            )
    if schluessel is not None:
        if len(_WAND) >= _WAND_HOECHSTENS:
            _WAND.clear()
        _WAND[schluessel] = wand
    return wand


def ohne_flaechen(form, waende_):
    """Die Namen der Flächen, gegen die die Hüllfläche nicht rechnet: die Wände selbst, die
    Flächen an ihren waagerechten Kanten (Boden, Oberseite) und die an einer senkrechten Kante,
    die dort eine Außenecke bilden – der Fräser fährt genau im Abstand seines Radius an der Wand
    entlang und berührt deren Kanten und Ecken; alles andere (Absätze, nicht gewählte Wände,
    die zur Bahn hin abknicken) hält ihn an. Ohne die Außenecken hielt das Raster den Schlichtzug
    gut 3 mm vor dem Ende einer Wand an, wo sie an eine nicht gewählte Außenfläche stößt (Manuels
    Ring: die Schlitzenden blieben mit dem Aufmaß stehen)."""
    import Part

    nummern = ft.nummern(form)
    ergebnis = set()
    for wand in waende_:
        ergebnis.add(wand.name)
        for kante in wand.flaeche.Edges:
            zs = [v.Point.z for v in kante.Vertexes]
            senkrecht = max(zs) - min(zs) > NAH
            for nachbar in form.ancestorsOfType(kante, Part.Face):
                i = nummern.get(nachbar.hashCode())
                if i is None or (senkrecht and not _aussenecke(wand.flaeche, nachbar, kante)):
                    continue
                ergebnis.add(f"Face{i + 1}")
    return sorted(ergebnis, key=lambda n: int(n[4:]))


def _aussenecke(wand, nachbar, kante):
    """Bilden `wand` und `nachbar` an der (senkrechten) `kante` eine Außenecke – geht der Nachbar
    von der Kante weg hinter die Wand, weg von ihrer freien Seite? Dann berührt der Fräser, der
    vor der Wand entlangfährt, ihn höchstens an der Kante. Gemessen in halber Höhe: die Normale
    der Wand dort (aus dem Material) gegen die Richtung, in der der Nachbar von der Kante weg
    liegt."""
    import Part

    if nachbar.isSame(wand):
        return False
    try:
        a, b = kante.ParameterRange
        mitte = kante.valueAt(0.5 * (a + b))
        u, v = wand.Surface.parameter(mitte)
        normale = wand.normalAt(u, v)
        un, vn = nachbar.Surface.parameter(mitte)
        u0, u1, v0, v1 = nachbar.ParameterRange
    except Exception:  # noqa: BLE001 – eine Fläche, die sich so nicht befragen lässt: nicht weg
        return False
    schritt_u, schritt_v = 1e-3 * max(u1 - u0, NAH), 1e-3 * max(v1 - v0, NAH)
    for du, dv in ((schritt_u, 0.0), (-schritt_u, 0.0), (0.0, schritt_v), (0.0, -schritt_v)):
        punkt = nachbar.valueAt(un + du, vn + dv)
        richtung = punkt - mitte
        richtung.z = 0.0
        if richtung.Length < NAH or not nachbar.isInside(punkt, 1e-4, True):
            continue
        if kante.distToShape(Part.Vertex(punkt))[0] < NAH:
            continue
        return richtung.dot(normale) < -NAH * richtung.Length
    return False


def boeden_vor(form, namen):
    """Die Namen der ebenen Flächen nach oben an den Unterkanten der Wände `namen` – der Boden
    vor einem Absatz, in einer Tasche; None, wenn eine Wand unten irgendwo an keinen solchen
    Boden stößt (an die Unterseite des Teils, eine Bohrung): Dort räumt kein Planfräsen und
    kein Räumen, was neben ihr steht (P-2026-10-02-17)."""
    import Part

    waende_ = waende(form, namen)
    if not waende_:
        return None
    ebenen = {e.name for e in hf.ebenen_oben(form)}
    nummern = ft.nummern(form)
    boeden = set()
    for wand in waende_:
        for kante in wand.kanten:
            unten = set()
            for nachbar in form.ancestorsOfType(kante, Part.Face):
                i = nummern.get(nachbar.hashCode())
                if i is not None and f"Face{i + 1}" in ebenen:
                    unten.add(f"Face{i + 1}")
            if not unten:
                return None
            boeden |= unten
    return boeden


def innenrundungen(form, namen):
    """[(Name, Radius)] der gezeichneten Rundungen innen unter den Wänden `namen`: ein Stück
    Zylinder mit senkrechter Achse (keine ganze Bohrung), zur Achse hin frei – die Ecke einer
    Tasche. Ein Fräser mit größerem Radius kommt nicht hinein (P-2026-10-02-19)."""
    import Part

    ergebnis = []
    for wand in waende(form, namen):
        flaeche = wand.flaeche
        zylinder = flaeche.Surface
        if not isinstance(zylinder, Part.Cylinder) or abs(abs(zylinder.Axis.z) - 1.0) > 1e-6:
            continue
        u0, u1, v0, v1 = flaeche.ParameterRange
        if u1 - u0 >= 2 * math.pi - 1e-6:
            continue  # eine ganze Bohrung
        u, v = (u0 + u1) / 2, (v0 + v1) / 2
        punkt, normale = flaeche.valueAt(u, v), flaeche.normalAt(u, v)
        zur_achse = zylinder.Center - punkt
        if normale.x * zur_achse.x + normale.y * zur_achse.y > 0:
            ergebnis.append((wand.name, float(zylinder.Radius)))
    return ergebnis


def _schluessel(kante):
    mitte = kante.valueAt((kante.FirstParameter + kante.LastParameter) / 2)
    return (round(mitte.x, 4), round(mitte.y, 4), round(mitte.z, 4), round(kante.Length, 4))


def _freie_seite(wand, kante):
    """((x, y), (nx, ny)): die Mitte der Unterkante und die Normale der Wand dort, vom Material
    weg (Face.normalAt beachtet die Orientierung im Körper, vierachs_rohteil.aussennormale)."""
    mitte = kante.valueAt((kante.FirstParameter + kante.LastParameter) / 2)
    try:
        u, v = wand.flaeche.Surface.parameter(mitte)
        n = wand.flaeche.normalAt(u, v)
    except Exception:  # OCC: keine Parameter – die Mitte der Fläche
        u0, u1, v0, v1 = wand.flaeche.ParameterRange
        n = wand.flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    laenge = math.hypot(n.x, n.y) or 1.0
    return (float(mitte.x), float(mitte.y)), (float(n.x / laenge), float(n.y / laenge))


def _gleich_hoch(wand):
    """z der Oberkante, wenn die Wand überall gleich hoch ist: Ihr äußerer Rand besteht nur aus
    waagerechten Kanten unten (z_unten) und oben (alle auf einer Höhe) und senkrechten Kanten
    (Löcher in der Wand zählen nicht – eine Senkrechte verlässt sie trotzdem oben). None sonst."""
    try:
        rand = wand.flaeche.OuterWire
        oben = None
        for k in rand.Edges:
            zs = [v.Point.z for v in k.Vertexes]
            bb = k.BoundBox
            if bb.ZLength <= GLEICH:  # waagerecht
                z = zs[0]
                if abs(z - wand.z_unten) <= GLEICH:
                    continue
                if oben is not None and abs(z - oben) > GLEICH:
                    return None
                oben = z if oben is None else max(oben, z)
            elif bb.XLength > GLEICH or bb.YLength > GLEICH:
                return None  # schräg oder gebogen nach oben
        return float(oben) if oben is not None else None
    except Exception:  # noqa: BLE001 – im Zweifel schneiden
        return None


def _hoehen_zusammen(wand, punkte, linien):
    """Je Stelle, wo ihre Senkrechte die Wand verlässt – mit einem Schnitt für alle (an den Wänden
    der Beispiele bitgleich mit einem je Stelle, dreimal so schnell; P-2026-10-11-81). None, wenn
    OpenCascade nicht schneidet."""
    import Part

    try:
        ecken = wand.flaeche.section(Part.makeCompound(linien)).Vertexes
    except Exception:  # noqa: BLE001 – dann je Stelle
        return None
    xy = np.array([(q.x, q.y) for q in punkte], dtype=float)
    hoehen = [None] * len(punkte)
    for v in ecken:
        p = v.Point
        abstand = np.hypot(xy[:, 0] - p.x, xy[:, 1] - p.y)
        i = int(np.argmin(abstand))
        if abstand[i] <= NAH:
            hoehen[i] = p.z if hoehen[i] is None else max(hoehen[i], p.z)
    return [wand.z_oben if h is None else h for h in hoehen]


def _wandkanten(wand, kante):
    """[(x, y, z_oben)] – die Unterkante `kante` der Wand in Stücke gleicher Höhe geteilt: Eine
    Wand kann über ihrer Unterkante verschieden hoch sein (die Rückwand des Testteils: über der
    Insel 22, wo die Stufe aufsitzt 32 – eine Fläche). Die Höhe je Stelle: wo eine senkrechte
    Gerade durch die Stelle die Wand verlässt."""
    import FreeCAD
    import Part

    punkte = kante.discretize(Distance=WANDHOEHE_SCHRITT)
    if len(punkte) < 2:
        punkte = [kante.Vertexes[0].Point, kante.Vertexes[-1].Point]
    oben = _gleich_hoch(wand)
    if oben is not None:
        # Unten, oben und an den Seiten gerade Kanten: Jede Senkrechte verlässt die Wand an der
        # Oberkante – ohne einen Schnitt je Millimeter (P-2026-10-11-81).
        xs = np.array([q.x for q in punkte], dtype=float)
        ys = np.array([q.y for q in punkte], dtype=float)
        return [(xs, ys, oben)]
    linien = [
        Part.makeLine(
            FreeCAD.Vector(q.x, q.y, wand.z_unten - 1.0),
            FreeCAD.Vector(q.x, q.y, wand.z_oben + 1.0),
        )
        for q in punkte
    ]
    hoehen = _hoehen_zusammen(wand, punkte, linien)
    if hoehen is None:
        hoehen = []
        for linie in linien:
            try:
                ecken = wand.flaeche.section(linie).Vertexes
            except Exception:
                ecken = []
            hoehen.append(max((v.Point.z for v in ecken), default=wand.z_oben))
    stuecke = []
    anfang = 0
    for i in range(1, len(punkte) + 1):
        if i == len(punkte) or abs(hoehen[i] - hoehen[anfang]) > 0.01:
            bis = min(i + 1, len(punkte))  # das Stück bis zur ersten Stelle der nächsten Höhe
            xs = np.array([q.x for q in punkte[anfang:bis]], dtype=float)
            ys = np.array([q.y for q in punkte[anfang:bis]], dtype=float)
            if len(xs) >= 2:
                stuecke.append((xs, ys, float(hoehen[anfang])))
            anfang = i
    return stuecke


def konturen(form, namen):
    """[Kontur] – die Unterkanten der Wände `namen` zu Ketten verbunden: Wände mit derselben
    Unterkante, soweit ihre Unterkanten zusammenhängen (Part.sortEdges); die tiefsten zuletzt.
    ValueError, wenn keine der Flächen eine Wand ist."""
    import Part

    alle = waende(form, namen)
    if not alle:
        raise ValueError(tr("ko.fehler.keine_wand"))
    gruppen = []
    for wand in sorted(alle, key=lambda w: w.z_unten):
        if gruppen and abs(gruppen[-1][0].z_unten - wand.z_unten) <= NAH:
            gruppen[-1].append(wand)
        else:
            gruppen.append([wand])
    ergebnis = []
    for gruppe in gruppen:
        kanten, wand_der_kante = [], {}
        for wand in gruppe:
            for kante in wand.kanten:
                kanten.append(kante)
                wand_der_kante[_schluessel(kante)] = wand
        for kette in Part.sortEdges(kanten):
            schluessel = [_schluessel(k) for k in kette]
            beteiligt = [wand_der_kante[s] for s in schluessel if s in wand_der_kante]
            if not beteiligt:
                continue
            laengste = max(kette, key=lambda k: k.Length)
            wand = wand_der_kante.get(_schluessel(laengste), beteiligt[0])
            stelle, normale = _freie_seite(wand, laengste)
            draht = Part.Wire(kette)
            wandkanten = []
            for kante in kette:
                w_ = wand_der_kante.get(_schluessel(kante))
                if w_ is not None:
                    k_ = _schluessel(kante)
                    if k_ not in w_.stuecke:
                        w_.stuecke[k_] = _wandkanten(w_, kante)
                    wandkanten += w_.stuecke[k_]
            ergebnis.append(
                Kontur(
                    draht,
                    float(gruppe[0].z_unten),
                    max(w.z_oben for w in beteiligt),
                    draht.isClosed(),
                    stelle,
                    normale,
                    tuple(sorted({w.name for w in beteiligt}, key=lambda n: int(n[4:]))),
                    tuple(wandkanten),
                )
            )
    return sorted(ergebnis, key=lambda k: -k.z_unten)


# --- Segmente und Proben ----------------------------------------------------------------------


@dataclass(frozen=True)
class _Strecke:
    von: tuple
    nach: tuple

    @property
    def laenge(self):
        return math.hypot(self.nach[0] - self.von[0], self.nach[1] - self.von[1])

    @property
    def bogen(self):
        return None

    def umgekehrt(self):
        return _Strecke(self.nach, self.von)

    def bei(self, t):
        return (
            self.von[0] + (self.nach[0] - self.von[0]) * t,
            self.von[1] + (self.nach[1] - self.von[1]) * t,
        )


@dataclass(frozen=True)
class _Bogen:
    von: tuple
    nach: tuple
    mitte: tuple
    uhr: bool  # im Uhrzeigersinn (G2)

    @property
    def radius(self):
        return math.hypot(self.von[0] - self.mitte[0], self.von[1] - self.mitte[1])

    @property
    def winkel(self):
        a0 = math.atan2(self.von[1] - self.mitte[1], self.von[0] - self.mitte[0])
        a1 = math.atan2(self.nach[1] - self.mitte[1], self.nach[0] - self.mitte[0])
        grad = ((a0 - a1) if self.uhr else (a1 - a0)) % (2 * math.pi)
        if grad < 1e-12 and not _nah(self.von, self.nach):
            grad = 2 * math.pi
        return grad

    @property
    def laenge(self):
        return self.radius * self.winkel

    @property
    def bogen(self):
        return (self.mitte[0], self.mitte[1], self.uhr)

    def umgekehrt(self):
        return _Bogen(self.nach, self.von, self.mitte, not self.uhr)

    def bei(self, t):
        a0 = math.atan2(self.von[1] - self.mitte[1], self.von[0] - self.mitte[0])
        a = a0 - t * self.winkel if self.uhr else a0 + t * self.winkel
        r = self.radius
        return (self.mitte[0] + r * math.cos(a), self.mitte[1] + r * math.sin(a))


def _nah(p, q):
    return abs(p[0] - q[0]) <= NAH and abs(p[1] - q[1]) <= NAH


def _geteilt(bogen):
    """Ein Bogen über mehr als einen Halbkreis in zwei – so hat jeder Satz G2/G3 einen klaren
    Weg."""
    if bogen.winkel <= math.pi + 1e-9:
        return [bogen]
    halb = bogen.bei(0.5)
    return [
        _Bogen(bogen.von, halb, bogen.mitte, bogen.uhr),
        _Bogen(halb, bogen.nach, bogen.mitte, bogen.uhr),
    ]


def _segmente(draht, toleranz):
    """Die Kanten des Drahts in seiner Reihenfolge als Strecken und Bögen – andere Kurven als
    Linienzug (discretize). Die Richtung jeder Kante folgt aus dem Anschluss an die Nachbarn."""
    import Part

    kanten = draht.OrderedEdges
    ergebnis = []
    ende = None
    for nummer, kante in enumerate(kanten):
        ecken = [(float(v.Point.x), float(v.Point.y)) for v in kante.Vertexes]
        a, b = ecken[0], ecken[-1]
        umgekehrt = False
        if len(ecken) > 1:
            if ende is None:
                if len(kanten) > 1:
                    naechste = [(v.Point.x, v.Point.y) for v in kanten[nummer + 1].Vertexes]
                    if any(_nah(a, e) for e in naechste) and not any(_nah(b, e) for e in naechste):
                        umgekehrt = True
            elif _nah(ende, b) and not _nah(ende, a):
                umgekehrt = True
        if umgekehrt:
            a, b = b, a
        kurve = kante.Curve
        f, g = kante.FirstParameter, kante.LastParameter
        if isinstance(kurve, (Part.Line, Part.LineSegment)):
            if not _nah(a, b):
                ergebnis.append(_Strecke(a, b))
        elif isinstance(kurve, Part.Circle):
            mitte = (float(kurve.Center.x), float(kurve.Center.y))
            halb = kante.valueAt((f + g) / 2)
            halb = (float(halb.x), float(halb.y))
            if _nah(a, b):  # der ganze Kreis: zwei Hälften
                viertel = kante.valueAt(f + (g - f) / 4)
                uhr = bn.im_uhrzeigersinn(a, halb, (viertel.x, viertel.y))
                ergebnis.extend((_Bogen(a, halb, mitte, uhr), _Bogen(halb, a, mitte, uhr)))
            else:
                ergebnis.extend(_geteilt(_Bogen(a, b, mitte, bn.im_uhrzeigersinn(a, b, halb))))
        else:
            punkte = [(float(p.x), float(p.y)) for p in kante.discretize(Deflection=toleranz)]
            if umgekehrt:
                punkte.reverse()
            ergebnis.extend(
                _Strecke(p, q) for p, q in zip(punkte, punkte[1:], strict=False) if not _nah(p, q)
            )
        ende = b
    return ergebnis


@dataclass
class _Proben:
    """Die Bahn abgetastet: Stellen höchstens `schritt` auseinander, je Stelle ihr Segment."""

    x: np.ndarray
    y: np.ndarray
    segment: np.ndarray  # (N,) Nummer des Segments
    a: np.ndarray  # (N,) Weg bis zur Stelle


def _abtasten(segmente, schritt, geschlossen):
    xs, ys, nummern = [], [], []
    for nummer, s in enumerate(segmente):
        anzahl = max(1, int(math.ceil(s.laenge / schritt - 1e-9)))
        for i in range(anzahl):
            p = s.bei(i / anzahl)
            xs.append(p[0])
            ys.append(p[1])
            nummern.append(nummer)
    if not geschlossen and segmente:
        p = segmente[-1].nach
        xs.append(p[0])
        ys.append(p[1])
        nummern.append(len(segmente) - 1)
    x, y = np.array(xs, dtype=float), np.array(ys, dtype=float)
    a = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
    return _Proben(x, y, np.array(nummern, dtype=int), a)


def _einzelne_strecke(draht):
    import Part

    if len(draht.Edges) != 1:
        return None
    kante = draht.Edges[0]
    if not isinstance(kante.Curve, (Part.Line, Part.LineSegment)) or len(kante.Vertexes) < 2:
        return None
    a, b = kante.Vertexes[0].Point, kante.Vertexes[-1].Point
    return _Strecke((float(a.x), float(a.y)), (float(b.x), float(b.y)))


def _parallel(strecke, d):
    tx, ty = strecke.nach[0] - strecke.von[0], strecke.nach[1] - strecke.von[1]
    laenge = math.hypot(tx, ty) or 1.0
    nx, ny = -ty / laenge * d, tx / laenge * d
    return _Strecke(
        (strecke.von[0] + nx, strecke.von[1] + ny), (strecke.nach[0] + nx, strecke.nach[1] + ny)
    )


def _versaetze(kontur, d, toleranz, schritt, material_rechts=True):
    """[(Segmente, Proben)] – alle Schleifen des Versatzes um `d` auf der freien Seite, die nahe
    der Kontur (_versatz) zuerst. Verengt sich die freie Seite (am C-Ring der Schlitz, schmaler
    als der Fräser), zerfällt der Versatz: Außen um den Ring eine Schleife, in der Bohrung eine
    zweite – bis P-2026-10-16-15 fiel die zweite still weg, und die Bohrung blieb voll."""
    import FreeCAD

    erste = _versatz(kontur, d, toleranz, schritt, material_rechts)
    if erste is None or not kontur.geschlossen:
        return [] if erste is None else [erste]
    ziel = (kontur.stelle[0] + kontur.normale[0] * d, kontur.stelle[1] + kontur.normale[1] * d)
    draht = kontur.draht.copy()
    draht.translate(FreeCAD.Vector(0, 0, -kontur.z_unten))
    ergebnis = [erste]
    for vorzeichen in (1.0, -1.0):
        try:
            gerechnet = draht.makeOffset2D(vorzeichen * d, 0, False, False, False)
        except Exception:  # OCC: „offset result has no wires“
            continue
        schleifen = []
        for teil in gerechnet.Wires:
            segmente = _segmente(teil, toleranz)
            if segmente:
                schleifen.append((segmente, _abtasten(segmente, schritt, True)))
        if not any(
            np.hypot(p.x - ziel[0], p.y - ziel[1]).min() <= max(schritt, 0.01 * d)
            for _s, p in schleifen
        ):
            continue  # die andere Seite
        for segmente, proben in schleifen:
            if np.hypot(proben.x - ziel[0], proben.y - ziel[1]).min() <= max(schritt, 0.01 * d):
                continue  # die erste
            weg = _kette_abstand(kontur, proben)
            if weg is None or abs(weg - d) > max(2 * schritt, 0.02 * d):
                continue  # keine Bahn im Abstand d von der Kontur
            ergebnis.append(
                _in_fahrtrichtung(
                    segmente, proben, 0, _normale_bei(kontur, proben, 0), schritt, True,
                    material_rechts,
                )
            )  # fmt: skip
        break
    return ergebnis


def _schleife_zu(zug, schrupp, weitere):
    """Die Schruppbahnen (eine Schleife, _versaetze) zum Schlichtzug `zug` – die mit dem
    nächsten Schwerpunkt; [] ohne."""
    _d, _s, p = zug
    mitte = (float(p.x.mean()), float(p.y.mean()))
    kandidaten = [schleife for schleife in (schrupp, *weitere) if schleife]
    if not kandidaten:
        return []
    return min(
        kandidaten,
        key=lambda schleife: math.hypot(
            float(schleife[0][2].x.mean()) - mitte[0], float(schleife[0][2].y.mean()) - mitte[1]
        ),
    )


def _zuordnen(weitere, d, schleifen):
    """Hängt die Schleifen des Versatzes `d` an die weiteren Schleifen davor (je die mit dem
    nächsten Schwerpunkt, höchstens gut zwei Schritte des Versatzes entfernt) – oder beginnt eine
    neue."""
    for segmente, proben in schleifen:
        mitte = (float(proben.x.mean()), float(proben.y.mean()))
        beste, abstand = None, math.inf
        for schleife in weitere:
            _d, _s, p = schleife[-1]
            a = math.hypot(float(p.x.mean()) - mitte[0], float(p.y.mean()) - mitte[1])
            if a < abstand and schleife[-1][0] < d:
                beste, abstand = schleife, a
        if beste is not None and abstand <= 2.0 * (d - beste[-1][0]) + 1.0:
            beste.append((d, segmente, proben))
        else:
            weitere.append([(d, segmente, proben)])


def _kette_abstand(kontur, proben):
    """Der kleinste Abstand der Proben zur Kontur (ihre Unterkanten) – None ohne Kanten."""
    import FreeCAD
    import Part

    try:
        punkte = [FreeCAD.Vector(float(x), float(y), kontur.z_unten) for x, y in zip(
            proben.x[:: max(1, len(proben.x) // 24)], proben.y[:: max(1, len(proben.y) // 24)],
            strict=True,
        )]  # fmt: skip
        return min(kontur.draht.distToShape(Part.Vertex(p))[0] for p in punkte)
    except Exception:  # OCC
        return None


def _normale_bei(kontur, proben, i):
    """Die Richtung von der Kontur zur Probe `i` (waagerecht) – die freie Seite dort."""
    import FreeCAD
    import Part

    p = FreeCAD.Vector(float(proben.x[i]), float(proben.y[i]), kontur.z_unten)
    _d, paare, _info = kontur.draht.distToShape(Part.Vertex(p))
    naechster = paare[0][0]
    return _einheit(p.x - naechster.x, p.y - naechster.y)


def _versatz(kontur, d, toleranz, schritt, material_rechts=True):
    """(Segmente, Proben) des Versatzes um `d` auf der freien Seite der Kontur, in Fahrtrichtung
    (Material rechts, `material_rechts` False: links); None, wenn es ihn nicht gibt (zu groß für
    die Tasche)."""
    import FreeCAD

    ziel = (kontur.stelle[0] + kontur.normale[0] * d, kontur.stelle[1] + kontur.normale[1] * d)
    draht = kontur.draht.copy()
    draht.translate(FreeCAD.Vector(0, 0, -kontur.z_unten))  # makeOffset2D will z = 0
    einzeln = _einzelne_strecke(draht)  # eine Gerade allein spannt keine Ebene auf
    kandidaten = []
    for vorzeichen in (1.0, -1.0):
        if einzeln is not None:
            kandidaten.append([_parallel(einzeln, vorzeichen * d)])
            continue
        try:
            ergebnis = draht.makeOffset2D(vorzeichen * d, 0, False, not kontur.geschlossen, False)
        except Exception:  # OCC: „offset result has no wires“
            continue
        for teil in ergebnis.Wires:
            segmente = _segmente(teil, toleranz)
            if segmente:
                kandidaten.append(segmente)
    for segmente in kandidaten:
        proben = _abtasten(segmente, schritt, kontur.geschlossen)
        abstand = np.hypot(proben.x - ziel[0], proben.y - ziel[1])
        if abstand.min() <= max(schritt, 0.01 * d):
            return _in_fahrtrichtung(
                segmente,
                proben,
                int(abstand.argmin()),
                kontur.normale,
                schritt,
                kontur.geschlossen,
                material_rechts,
            )
    return None


def _in_fahrtrichtung(segmente, proben, nahe, normale, schritt, geschlossen, material_rechts=True):
    """Gleichlauf (M3): das Material rechts, die freie Seite (die Normale) links – mit
    `material_rechts` False andersherum (M4). Liegt sie an der Stelle `nahe` auf der falschen
    Seite der Fahrtrichtung, dreht sich die Bahn um."""
    n = len(proben.x)
    j = (nahe + 1) % n if geschlossen else min(nahe + 1, n - 1)
    i = nahe if j != nahe else nahe - 1
    tx, ty = proben.x[j] - proben.x[i], proben.y[j] - proben.y[i]
    if (-ty * normale[0] + tx * normale[1] < 0) == bool(material_rechts):
        segmente = [s.umgekehrt() for s in reversed(segmente)]
        proben = _abtasten(segmente, schritt, geschlossen)
    return segmente, proben


def _startstelle(segmente, proben):
    """Die Stelle, an der eine geschlossene Bahn beginnt: die Mitte der längsten Geraden – dort
    ist Platz zum Ein- und Ausfahren."""
    strecken = [(s.laenge, i) for i, s in enumerate(segmente) if isinstance(s, _Strecke)]
    if not strecken:
        return 0
    _laenge, nummer = max(strecken)
    mitte = segmente[nummer].bei(0.5)
    stellen = np.flatnonzero(proben.segment == nummer)
    if not len(stellen):
        return 0
    abstand = np.hypot(proben.x[stellen] - mitte[0], proben.y[stellen] - mitte[1])
    return int(stellen[abstand.argmin()])


def _kette(kontur, toleranz, schritt):
    """(x, y) der Unterkanten der Kontur, höchstens `schritt` auseinander – für das Band der
    Hüllfläche."""
    import FreeCAD

    draht = kontur.draht.copy()
    draht.translate(FreeCAD.Vector(0, 0, -kontur.z_unten))
    proben = _abtasten(_segmente(draht, toleranz), schritt, kontur.geschlossen)
    return proben.x, proben.y


def _im_rohteil(x, y, rohteil, r):
    """Trifft die Stirn (Radius r) an (x, y) das Rohteil (von oben ein Rechteck)?"""
    x_von, x_bis, y_von, y_bis = rohteil
    dx = np.maximum(np.maximum(x_von - x, x - x_bis), 0.0)
    dy = np.maximum(np.maximum(y_von - y, y - y_bis), 0.0)
    return np.hypot(dx, dy) < r - GLEICH


# --- Hüllfläche im Raster ---------------------------------------------------------------------


class _Huelle:
    """Die Hüllfläche (hoehenfeld.je_zeile) im Raster über einem Rechteck – abgefragt an jeder
    Stelle der Bahn mit dem höchsten der vier Nachbarn, so bleibt die Seite der Sicherheit.

    Zwei Netze: Nahe an der Wand (im `band` um die Kette) zählt `netz_nah` – das Teil ohne die
    Wände und ohne die Flächen an ihren waagerechten Kanten, denn der Fräser fährt genau im
    Abstand seines Radius an der Wand entlang und berührt deren Kanten; weiter weg zählt
    `netz_fern` – nur ohne die Wände –, damit die Oberseite hinter einer Wand und der Boden
    vor ihr die Bahn dort anhalten, wo sie hingehören."""

    def __init__(
        self,
        netz_nah,
        netz_fern,
        geformt,
        zugabe,
        x0,
        x1,
        y0,
        y1,
        schritt,
        kette=None,
        band=0.0,
        waende=(),
    ):
        self.schritt = schritt
        self.zugabe = zugabe
        self.waende = list(waende)  # [(x, y, geschlossen, z_oben)] der Unterkanten der Konturen
        self.x0 = x0 - schritt
        self.y0 = y0 - schritt
        self.nx = max(2, int(math.ceil((x1 - self.x0) / schritt)) + 2)
        self.ny = max(2, int(math.ceil((y1 - self.y0) / schritt)) + 2)
        self.ys = self.y0 + schritt * np.arange(self.ny)
        self.roh = self._raster(netz_nah, geformt)
        if netz_fern is not None and netz_fern is not netz_nah and kette is not None:
            nah = self._nahe(kette, band)
            self.roh = np.where(nah, self.roh, self._raster(netz_fern, geformt))

    def _raster(self, netz, geformt):
        if not len(netz.dreiecke):
            return np.full((self.nx, self.ny), hf.KEIN_TREFFER)
        return hf.je_zeile(netz, geformt, self.ys, self.x0, self.schritt, self.nx, True)

    def _nahe(self, kette, band):
        """(nx, ny): liegt der Knoten höchstens `band` von der Kette (x, y der Unterkanten)?"""
        kx, ky = kette
        xs = self.x0 + self.schritt * np.arange(self.nx)
        nah = np.zeros((self.nx, self.ny), dtype=bool)
        if not len(kx):
            return nah
        dx2 = (xs[:, None] - kx[None, :]) ** 2
        for j, y in enumerate(self.ys):
            d2 = dx2 + ((y - ky) ** 2)[None, :]
            nah[:, j] = d2.min(axis=1) <= band * band
        return nah

    def roh_bei(self, x, y):
        fx = (np.asarray(x, dtype=float) - self.x0) / self.schritt
        fy = (np.asarray(y, dtype=float) - self.y0) / self.schritt
        i0 = np.clip(np.floor(fx).astype(int), 0, self.nx - 1)
        j0 = np.clip(np.floor(fy).astype(int), 0, self.ny - 1)
        i1 = np.minimum(i0 + 1, self.nx - 1)
        j1 = np.minimum(j0 + 1, self.ny - 1)
        return np.maximum(
            np.maximum(self.roh[i0, j0], self.roh[i1, j0]),
            np.maximum(self.roh[i0, j1], self.roh[i1, j1]),
        )

    def erlaubt(self, x, y, lage, ziel):
        """Darf die Spitze auf der Lage dorthin? Ja, wo die Hüllfläche nicht höher liegt – und
        wo nichts höher steht als das Ziel (die Unterkante der Wand)."""
        roh = self.roh_bei(x, y)
        return (roh + self.zugabe <= lage + GLEICH) | (roh <= ziel + GLEICH)

    def zu_nah(self, x, y, lage, mindest):
        """Je Stelle: liegt sie näher als `mindest` an einer Wand der Konturen, die über die Lage
        hinaufreicht – quer zu ihr oder an einer ihrer inneren Ecken (_abstand_ohne_enden)?
        Gerechnet nur nahe der Wand (ihr Umriss plus `mindest`) und in Stücken – eine lange
        Kontur gäbe sonst eine Matrix aus Stellen mal Ecken."""
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        nah = np.zeros(len(x), dtype=bool)
        for kx, ky, geschlossen, z_oben in self.waende:
            if z_oben <= lage + GLEICH or len(kx) < 2:
                continue
            kx = np.asarray(kx, dtype=float)
            ky = np.asarray(ky, dtype=float)
            dort = np.flatnonzero(
                ~nah
                & (x > kx.min() - mindest)
                & (x < kx.max() + mindest)
                & (y > ky.min() - mindest)
                & (y < ky.max() + mindest)
            )
            stueck = max(1, ABSTAND_STUECK // len(kx))
            for von in range(0, len(dort), stueck):
                i = dort[von : von + stueck]
                nah[i] |= _abstand_ohne_enden(x[i], y[i], kx, ky, geschlossen) < mindest
        return nah

    def abstand_zur_wand(self, x, y, lage):
        """So weit (mm) ist jede Stelle von der nächsten Wand der Konturen entfernt, die über
        die Lage hinaufreicht – unendlich, wo keine ist. Die Hüllfläche blendet diese Wände
        nahe der Bahn aus (der Fräser fährt im Abstand seines Radius an ihnen entlang); das
        Ein- und Ausfahren muss sie trotzdem meiden."""
        ergebnis = np.full(len(x), np.inf)
        for kx, ky, geschlossen, z_oben in self.waende:
            if z_oben > lage + GLEICH and len(kx) > 1:
                ergebnis = np.minimum(ergebnis, _abstand_polylinie(x, y, kx, ky, geschlossen))
        return ergebnis


def nur_wo_der_grosse_nicht_hinkam(r_gross, r_klein, toleranz, schritt):
    """Für Konturwerte.nur_wo – das Restmaterial (W-006 4.1 Punkt 5): je Stelle der Bahn des
    kleinen Fräsers (Radius r_klein), ob sein Kreis dort aus jedem Kreis des großen herausragt
    (Radius r_gross, seine Bahn im Abstand r_gross an denselben Wänden): Abstand zu dessen Bahn
    größer als r_gross − r_klein. Dort ließ der große Material stehen – in Ecken innen, in
    Nuten, schmaler als er. Um r_klein längs der Bahn verlängert, damit der kleine sauber
    anschließt. Gibt es die Bahn des großen nicht (zu groß für die Tasche), überall."""
    bahnen = {}
    grenze = r_gross - r_klein + REST_SPIEL
    weiter = max(1, int(math.ceil(r_klein / schritt)))

    def nur_wo(k, x, y):
        if id(k) not in bahnen:
            gross = _versatz(k, r_gross, toleranz, schritt)
            bahnen[id(k)] = None if gross is None else (gross[1].x, gross[1].y)
        bahn = bahnen[id(k)]
        if bahn is None:
            return np.ones(len(x), dtype=bool)
        maske = _abstand_polylinie(x, y, bahn[0], bahn[1], k.geschlossen) > grenze
        breiter = maske.copy()
        for schieben in range(1, weiter + 1):
            if k.geschlossen:
                breiter |= np.roll(maske, schieben) | np.roll(maske, -schieben)
            else:
                breiter[schieben:] |= maske[:-schieben]
                breiter[:-schieben] |= maske[schieben:]
        return breiter

    return nur_wo


def _abstand_polylinie(qx, qy, kx, ky, geschlossen):
    """Der Abstand jedes Punkts (qx, qy) zum Linienzug (kx, ky), geschlossen oder offen."""
    ax, ay = np.asarray(kx, dtype=float), np.asarray(ky, dtype=float)
    bx, by = np.roll(ax, -1), np.roll(ay, -1)
    if not geschlossen:
        ax, ay, bx, by = ax[:-1], ay[:-1], bx[:-1], by[:-1]
    dx, dy = bx - ax, by - ay
    laenge2 = dx * dx + dy * dy
    qx = np.asarray(qx, dtype=float)[:, None]
    qy = np.asarray(qy, dtype=float)[:, None]
    t = ((qx - ax) * dx + (qy - ay) * dy) / np.where(laenge2 > 0, laenge2, 1.0)
    t = np.clip(t, 0.0, 1.0)
    return np.hypot(qx - (ax + t * dx), qy - (ay + t * dy)).min(axis=1)


def _abstand_ohne_enden(qx, qy, kx, ky, geschlossen):
    """Wie _abstand_polylinie, an einem offenen Linienzug aber ohne seine beiden Enden: nur quer
    zu einer Strecke (der Fußpunkt auf ihr) und zu den Ecken dazwischen, an denen er abknickt
    (KNICK – die Punkte, mit denen eine gerade Wand abgetastet ist, sind keine Ecken). Am Ende
    geht die Wand um eine Ecke weiter – eine andere Wand oder keine –, der Abstand zum Endpunkt
    sagt nicht, ob der Fräser in sie fährt (am Testteil begann die Kontur T1 sonst 2 mm zu spät:
    5,3 mm vom Ende der Inselwand, die dort nach außen abbiegt; an Manuels Ring von vorn maß sie
    zum Punkt 1 mm vor dem Ende einer 3 mm kurzen Schlitzwand und zerlegte die Bahn um sie)."""
    ax, ay = np.asarray(kx, dtype=float), np.asarray(ky, dtype=float)
    bx, by = np.roll(ax, -1), np.roll(ay, -1)
    vx, vy = np.roll(ax, 1), np.roll(ay, 1)  # die Punkte davor
    knick = np.abs(np.arctan2((ax - vx) * (by - ay) - (ay - vy) * (bx - ax),
                              (ax - vx) * (bx - ax) + (ay - vy) * (by - ay)))  # fmt: skip
    ecke = knick > KNICK
    if not geschlossen:
        ecke[0] = ecke[-1] = False
    ecken_x, ecken_y = ax[ecke], ay[ecke]
    if not geschlossen:
        ax, ay, bx, by = ax[:-1], ay[:-1], bx[:-1], by[:-1]
    dx, dy = bx - ax, by - ay
    laenge2 = dx * dx + dy * dy
    qx = np.asarray(qx, dtype=float)[:, None]
    qy = np.asarray(qy, dtype=float)[:, None]
    t = ((qx - ax) * dx + (qy - ay) * dy) / np.where(laenge2 > 0, laenge2, 1.0)
    quer = np.where(
        (t >= 0.0) & (t <= 1.0) & (laenge2 > 0),
        np.hypot(qx - (ax + t * dx), qy - (ay + t * dy)),
        np.inf,
    )
    ergebnis = quer.min(axis=1) if quer.shape[1] else np.full(len(qx), np.inf)
    if len(ecken_x):
        ergebnis = np.minimum(ergebnis, np.hypot(qx - ecken_x, qy - ecken_y).min(axis=1))
    return ergebnis


# --- Die Bahn ---------------------------------------------------------------------------------


@dataclass
class _Stand:
    punkte: list = field(default_factory=list)
    konturen: int = 0
    lagen: int = 0
    bahnen: int = 0
    z_min: float = math.inf
    laenge: float = 0.0
    bereich: object = None  # mit Materialstand: die Zellen, wohin die Stirn kommt
    ziel: float = math.inf  # die tiefste Unterkante dabei
    mit_material: bool = False  # eine Kontur fuhr nur, wo Material steht
    ausgelassen: int = 0  # Läufe, die nur im Zickzack hineinkämen (_lauf)


@dataclass(frozen=True)
class _MitStand:
    """Der Materialstand an einer Kontur (W-012), wenn er dort nicht überall das ganze Rohteil
    zeigt."""

    stand: object  # materialstand.Materialstand
    innen: float  # mm: so weit trifft die Stirn sicher (eine Zelle kleiner)
    luecke: float  # mm: so lange Lücken fährt die Bahn im Vorschub durch

    def trifft(self, lage, proben_je):
        """Je Bahn (ihre Proben): wo ihre Stirn Material über der Lage trifft."""
        x = np.concatenate([p.x for p in proben_je])
        y = np.concatenate([p.y for p in proben_je])
        alle = self.stand.trifft(lage, self.innen, x, y)
        return np.split(alle, np.cumsum([len(p.x) for p in proben_je])[:-1])

    def drin(self, drin, ganz, proben, geschlossen):
        """`drin` mit den kurzen Lücken gefüllt, die ganz in `ganz` liegen (raeumen_bahn)."""
        from . import raeumen_bahn as rb  # erst hier: es braucht dieses Modul

        return rb._luecken_zu(drin, ganz, proben, geschlossen, self.luecke)


@dataclass(frozen=True)
class _Anfahrt:
    """Ein tangentiales Ein- oder Ausfahren: die Gerade außen (`aussen` … `bogen_punkt`), der
    Viertelkreis um `mitte` zwischen `bogen_punkt` und dem Punkt auf der Bahn."""

    aussen: tuple
    bogen_punkt: tuple
    bahn_punkt: tuple
    mitte: tuple
    uhr: bool
    r_e: float
    laenge_gerade: float


def planen(netz, werte, konturen_, schritt=SCHRITT, netz_fern=None, stand=None):
    """Die Bahn „Kontur“ (Konturbahn) an den Konturen `konturen_` ([Kontur]) mit den Werten
    `werte`; `netz` ist das Teil ohne die Wände und ihre Nachbarn (hoehenfeld.netz_ohne mit
    ohne_flaechen()), `netz_fern` das Teil nur ohne die Wände – es zählt weiter weg von der Wand
    (_Huelle). Mit `stand` (materialstand, W-012) nur, was die Operationen davor übrig ließen.
    ValueError mit einem Satz, wenn es nicht geht."""
    w = werte
    form = w.form
    r = float(form.radius)
    if r <= 0 or vp.ebener_radius(form) <= 0:
        raise ValueError(tr("ko.fehler.form"))
    if w.zustellung <= 0 or w.zeilenabstand <= 0:
        raise ValueError(tr("ko.fehler.werte"))
    if w.zeilenabstand > 2 * r + GLEICH:
        raise ValueError(tr("ko.fehler.zeilenabstand"))
    if not konturen_:
        raise ValueError(tr("ko.fehler.keine_wand"))
    r_ein = w.einfahrradius if w.einfahrradius and w.einfahrradius > 0 else EINFAHRT_ANTEIL * r
    gerade = GERADE_ANTEIL * r
    zugabe = netz.toleranz + vb.RAND
    geformt = form.mit_aufmass(netz.toleranz)
    # Die Unterkanten aller Konturen: das Band der Hüllfläche je Kontur und der Abstand, den
    # das Ein- und Ausfahren zu jeder Wand hält.
    ketten = [(k, _kette(k, netz.toleranz, 2 * schritt)) for k in konturen_]
    # Je Wand mit ihrer eigenen Höhe (Kontur.wandkanten); ohne die Angabe die ganze Kette mit
    # ihrer höchsten Wand.
    waende = []
    for k, (kx, ky) in ketten:
        if k.wandkanten:
            waende += [(wx, wy, False, z_oben) for wx, wy, z_oben in k.wandkanten]
        else:
            waende.append((kx, ky, k.geschlossen, k.z_oben))
    st = _Stand()
    # Mehrere Wandzüge teilen sich oft eine Tasche (Manuels Ring: die Bögen der Öffnung und die
    # Schlitzwände). Jeder sieht, was die davor schon geräumt haben – eine eigene Kopie des
    # Materialstands, nach jedem Zug abgetragen; sonst schruppte der nächste dort durch Luft und
    # tauchte mit der Helix durch das Geräumte (am Ring 46 % des Vorschubs in der Luft).
    eigen = _eigener_stand(stand) if stand is not None and len(ketten) > 1 else stand
    for nummer, (kontur, kette) in enumerate(ketten):
        bis_hier = len(st.punkte)
        _kontur(
            st,
            kontur,
            w,
            r,
            r_ein,
            gerade,
            netz,
            netz_fern,
            geformt,
            zugabe,
            schritt,
            kette,
            waende,
            eigen,
        )
        if eigen is not stand and nummer < len(ketten) - 1:
            _abtragen(eigen, st.punkte[max(bis_hier - 1, 0) :], form)
    noch, weg, davor = 0.0, 0.0, []
    if stand is not None and st.bereich is not None:
        # Über dem Teil: An der Wand trifft die Stirn auch Zellen im Teil – sie zählen nicht.
        boden = hf.hoehen(
            netz_fern if netz_fern is not None else netz, stand.quader.x, stand.quader.y
        )
        noch, weg = stand.volumen(st.bereich, st.ziel, boden)
        davor = stand.wer(st.bereich)
    if st.mit_material and st.bahnen == 0 and davor:
        from . import materialstand as mst  # erst hier: es bringt den Job mit

        raise mst.schon_weg(davor)
    if st.konturen == 0:
        raise ValueError(tr("ko.fehler.nichts"))
    return Konturbahn(
        st.punkte,
        st.konturen,
        st.lagen,
        st.bahnen,
        st.z_min if math.isfinite(st.z_min) else 0.0,
        st.laenge,
        noch,
        weg,
        davor,
    )


def _eigener_stand(stand):
    """Eine Kopie des Materialstands, deren Höhen die Kontur selbst senken darf (_abtragen) –
    der Materialstand des Jobs bleibt, wie er ist."""
    import copy
    import dataclasses

    quader = copy.copy(stand.quader)
    quader.h = stand.quader.h.copy()
    return dataclasses.replace(stand, quader=quader)


def _abtragen(stand, punkte, form):
    """Senkt im Materialstand, was die Vorschubsätze `punkte` (bahn.Punkt) wegnehmen – ein Bogen
    in Sehnen von höchstens BOGEN_SEHNE mm; Eilgänge nehmen nichts."""
    von, nach = [], []
    for a, b in zip(punkte, punkte[1:], strict=False):
        if b.eilgang:
            continue
        if b.bogen is None:
            von.append((a.x, a.y, a.z))
            nach.append((b.x, b.y, b.z))
            continue
        mx, my, uhr = b.bogen
        bogen = bn.winkel(a, b)
        a0 = math.atan2(a.y - my, a.x - mx)
        rb = math.hypot(a.x - mx, a.y - my)
        n = max(2, int(math.ceil(bn.weg(a, b) / BOGEN_SEHNE)))
        vorher = (a.x, a.y, a.z)
        for i in range(1, n + 1):
            t = i / n
            wi = a0 - t * bogen if uhr else a0 + t * bogen
            jetzt = (mx + rb * math.cos(wi), my + rb * math.sin(wi), a.z + (b.z - a.z) * t)
            von.append(vorher)
            nach.append(jetzt)
            vorher = jetzt
    if von:
        stand.quader.fahre_stuecke(von, nach, form)


def _kontur(
    st, k, w, r, r_ein, gerade, netz, netz_fern, geformt, zugabe, schritt, kette, waende, stand=None
):
    """Eine Kontur: die Versätze fürs Schruppen (so viele, wie Rohteil neben der Wand steht),
    der fürs Schlichten, die Hüllfläche über allem, dann die Lagen – mit `stand` (W-012) nur,
    wo noch Material steht."""
    ziel = k.z_unten - max(w.tiefer, 0.0)
    oben = w.oben
    if w.breite > 0:
        # Mit der Breite sagt man: Daneben ist schon geräumt (eine Tasche, das Räumen davor) –
        # dann auch über der Oberkante der Wände; die Lagen beginnen dort, nicht am Rohteil
        # (sonst fährt jede Bahn ihre Rampe durch Luft – auf der Platte 20 mm, P-2026-10-01-26).
        oben = min(oben, k.z_oben)
    if oben <= ziel + GLEICH:
        return
    aufmass = max(w.aufmass, 0.0)
    toleranz = netz.toleranz
    if w.breite > 0:
        # Zu schruppen ist nur, was über das Aufmaß hinaus steht: bei Breite = Aufmaß nichts –
        # dann bleibt allein das Schlichten.
        dick = w.breite - aufmass
        if dick > GLEICH:
            anzahl = max(1, int(math.ceil(dick / w.zeilenabstand - 1e-9)))
            abstaende = [r + aufmass + i * dick / anzahl for i in range(anzahl)]
        else:
            abstaende = []
    else:
        abstaende = [r + aufmass + i * w.zeilenabstand for i in range(HOECHSTENS_VERSAETZE)]
    schrupp = []  # [(d, Segmente, Proben)] von der Wand nach außen – die erste Schleife
    weitere = []  # [[(d, Segmente, Proben)] …] je weitere Schleife (_versaetze), ebenso
    erste_aus = False  # die erste Schleife liegt nicht mehr im Rohteil
    for d in abstaende:
        versaetze = _versaetze(k, d, toleranz, schritt, w.gleichlauf)
        if not versaetze:
            break
        (segmente, proben), *andere = versaetze
        if not erste_aus and _im_rohteil(proben.x, proben.y, w.rohteil, r).any():
            schrupp.append((d, segmente, proben))
        else:
            erste_aus = True
        andere = [v for v in andere if _im_rohteil(v[1].x, v[1].y, w.rohteil, r).any()]
        _zuordnen(weitere, d, andere)
        if erste_aus and not andere:
            break
    schlicht, schlichte_weitere = None, []
    if w.schlichten:
        versaetze = [
            v for v in _versaetze(k, r, toleranz, schritt, w.gleichlauf)
            if _im_rohteil(v[1].x, v[1].y, w.rohteil, r).any()
        ]  # fmt: skip
        if versaetze:
            schlicht = (r, *versaetze[0])
            schlichte_weitere = [(r, *v) for v in versaetze[1:]]
    alle = (
        schrupp
        + [e for schleife in weitere for e in schleife]
        + ([schlicht] if schlicht is not None else [])
        + schlichte_weitere
    )
    if not alle:
        return
    rand = r_ein + gerade + r + schritt
    huelle = _Huelle(
        netz,
        netz_fern,
        geformt,
        zugabe,
        min(p.x.min() for _d, _s, p in alle) - rand,
        max(p.x.max() for _d, _s, p in alle) + rand,
        min(p.y.min() for _d, _s, p in alle) - rand,
        max(p.y.max() for _d, _s, p in alle) + rand,
        schritt,
        kette,
        r + aufmass + 2 * schritt,
        waende,
    )
    st.konturen += 1
    bahnen_vorher = st.bahnen
    mit_stand, oben_schruppen, oben_schlichten = None, oben, oben
    if stand is not None:
        mit_stand, oben_schruppen, oben_schlichten = _mit_stand(
            st,
            stand,
            schrupp + [e for schleife in weitere for e in schleife] + schlichte_weitere,
            schlicht,
            oben,
            ziel,
            r,
        )
    if mit_stand is not None:
        oben = oben_schruppen  # die Lagen beginnen am höchsten Material, das sie erreichen
    anzahl_lagen = max(1, int(math.ceil((oben - ziel - hf.LAGEN_SPIEL) / w.zustellung)))
    lagen = oben - (oben - ziel) * np.arange(1, anzahl_lagen + 1) / anzahl_lagen
    if oben <= ziel + GLEICH:
        lagen = []  # nichts mehr zu schruppen
    vorige = oben
    einmal = False  # der innerste Versatz ist schon ganz gefahren, in einer Lage bis aufs Ziel
    schleifen = [schleife for schleife in (schrupp, *weitere) if schleife]
    for lage in lagen:
        lage = float(lage)
        gefahren = False
        for schleife in schleifen:  # je Schleife von außen zur Wand
            # (von, bis): so nah und so fern von der Wand ist diese Lage schon geräumt
            geraeumt = (math.inf, 0.0)
            masken = [None] * len(schleife)
            if mit_stand is not None:
                masken = mit_stand.trifft(lage, [p for _d, _s, p in schleife])
            for (d, segmente, proben), maske in zip(
                reversed(schleife), reversed(masken), strict=True
            ):
                if _bahnen(
                    st,
                    k,
                    d,
                    segmente,
                    proben,
                    lage,
                    vorige,
                    geraeumt,
                    huelle,
                    ziel,
                    w,
                    r,
                    r_ein,
                    gerade,
                    schritt,
                    mit_stand,
                    maske,
                ):
                    gefahren = True
                    geraeumt = (min(geraeumt[0], d - r), max(geraeumt[1], d + r))
                    innerster = schleife is schrupp and proben is schrupp[0][2]
                    if innerster and (maske is None or maske.all()):
                        einmal = len(lagen) == 1
        if gefahren:
            st.lagen += 1
            st.z_min = min(st.z_min, lage)
        vorige = lage
    # Der Zug beim Aufmaß wäre dieselbe Bahn noch einmal, wenn die eine Lage den innersten Versatz
    # schon ganz gefahren hat und die Schneide über die Höhe reicht (B-012: eine Runde Luft).
    hoehe = oben_schlichten - ziel
    doppelt = einmal and not 0 < w.schneidenlaenge < hoehe - GLEICH
    if mit_stand is not None and not doppelt:
        # Einmal beim Aufmaß an der Wand ab (Manuel, 2026-10-02: „wenn's heißt 0,3 ist
        # Schlichtaufmaß .. fahr die Kontur zumindest einmal auf 0,3 einfach an der Kontur ab“).
        for schleife in schleifen:
            _ein_zug(
                st, k, w, r, r_ein, gerade, schritt, schleife[0], schleife, oben_schlichten, ziel,
                huelle, mit_stand,
            )  # fmt: skip
    for zug in ([schlicht] if schlicht is not None else []) + schlichte_weitere:
        _ein_zug(
            st, k, w, r, r_ein, gerade, schritt, zug, _schleife_zu(zug, schrupp, weitere),
            oben_schlichten, ziel, huelle, mit_stand,
        )  # fmt: skip
    if mit_stand is not None and st.bahnen == bahnen_vorher:
        st.konturen -= 1  # hier war nichts mehr zu tun


def _ein_zug(st, k, w, r, r_ein, gerade, schritt, bahn, schrupp, oben, ziel, huelle, mit_stand):
    """Ein Versatz (`bahn`: d, Segmente, Proben) in einem Zug über die ganze Höhe, höchstens die
    Schneidenlänge je Zug – das Schlichten bei Radius, mit Materialstand vorher der beim
    Aufmaß."""
    d, segmente, proben = bahn
    hoehe = oben - ziel
    if hoehe <= GLEICH:
        return
    anzahl = 1
    if 0 < w.schneidenlaenge < hoehe - GLEICH:
        anzahl = max(1, int(math.ceil((hoehe - hf.LAGEN_SPIEL) / w.schneidenlaenge)))
    geraeumt = (schrupp[0][0] - r, schrupp[-1][0] + r) if schrupp else (math.inf, 0.0)
    for lage in oben - hoehe * np.arange(1, anzahl + 1) / anzahl:
        if _bahnen(
            st,
            k,
            d,
            segmente,
            proben,
            float(lage),
            oben,
            geraeumt,
            huelle,
            ziel,
            w,
            r,
            r_ein,
            gerade,
            schritt,
            mit_stand,
        ):
            st.lagen += 1
            st.z_min = min(st.z_min, float(lage))


def _mit_stand(st, stand, schrupp, schlicht, oben, ziel, r):
    """Der Materialstand an der Kontur (W-012): (_MitStand, wo die Lagen des Schruppens beginnen,
    wo das Schlichten beginnt) – (None, oben, oben), wenn dort, wohin die Stirn kommt, noch
    überall das Rohteil bis über `oben` steht (dann wie ohne). Merkt sich die Zellen fürs
    „noch“."""
    alle = schrupp + ([schlicht] if schlicht is not None else [])
    x = np.concatenate([p.x for _d, _s, p in alle])
    y = np.concatenate([p.y for _d, _s, p in alle])
    bereich = stand.maske_um_punkte(x, y, r)
    st.bereich = bereich if st.bereich is None else st.bereich | bereich
    st.ziel = min(st.ziel, ziel)
    with np.errstate(invalid="ignore"):
        voll = stand.quader.h[bereich] >= oben - MATERIAL  # −inf (kein Rohteil) zählt als tiefer
    if voll.all():
        return None, oben, oben
    st.mit_material = True
    # Was die Schruppbahnen wegnehmen können: was ihre Stirn trifft, eine Zelle kleiner – so
    # zählt die Wand nicht und auch nicht das Aufmaß an ihr, das eine Operation davor ließ.
    innen = max(r - stand.schritt, 0.5 * r)
    oben_schruppen = ziel
    if schrupp:
        hoch = stand.hoechste_um(
            np.concatenate([p.x for _d, _s, p in schrupp]),
            np.concatenate([p.y for _d, _s, p in schrupp]),
            innen,
        )
        if hoch is not None:
            oben_schruppen = min(oben, hoch)
    # Das Schlichten beginnt am höchsten Material an der Wand – auch im Teil, eine Zelle weiter:
    # lieber zu hoch als zu tief.
    oben_schlichten = oben
    if schlicht is not None:
        hoch = stand.hoechste_um(schlicht[2].x, schlicht[2].y, r + stand.schritt)
        oben_schlichten = min(oben, max(hoch, oben_schruppen)) if hoch is not None else ziel
    luecke = max(LUECKE * 2 * r, LUECKE_MIN)
    return _MitStand(stand, innen, luecke), oben_schruppen, oben_schlichten


def _bahnen(
    st,
    k,
    d,
    segmente,
    proben,
    lage,
    vorige,
    geraeumt,
    huelle,
    ziel,
    w,
    r,
    r_ein,
    gerade,
    schritt,
    mit_stand=None,
    maske=None,
):
    """Eine Bahn (ein Versatz) auf einer Lage: wo die Hüllfläche es erlaubt und Rohteil liegt –
    mit `maske` (Materialstand) nur, wo ihre Stirn Material trifft, über kurze Lücken hinweg –,
    geschlossen in einem Zug ab der Mitte der längsten Geraden, sonst in Läufen. Gibt die Zahl
    der Läufe zurück."""
    x, y = proben.x, proben.y
    n = len(x)
    if n < 2:
        return 0
    erlaubt = huelle.erlaubt(x, y, lage, ziel)
    # Nicht näher an eine Wand der Konturen als den Radius: Die Hüllfläche blendet alle gewählten
    # Wände aus – stehen zwei einander enger gegenüber als der Fräser, führe die Bahn an der einen
    # durch die andere (am C-Ring „Wände schlichten T1“ Ø 12 in der 10 mm breiten Nut: beide Stege
    # 5 mm tief weg, vom Fertigteil gefunden, W-029). Nur der Radius, nicht dazu das Aufmaß: Ein
    # Schruppgang, der vom Aufmaß der Gegenwand nimmt, schneidet nicht ins Teil, ihr Schlichtgang
    # kommt ohnehin – sonst zerfielen die Bahnen in Schlitzen knapp über 2 · (R + Aufmaß) in kurze
    # Läufe, die im Zickzack einstiegen (Manuels Ring von vorn, T2 Ø 10, szenario_ring_vorn).
    # Spiel: die Sehnen der Kette (alle 2 · schritt) an einer runden Wand innen, höchstens
    # (2 · schritt)² / 8r.
    spiel = WAND_SPIEL + (2 * schritt) ** 2 / (8 * r)
    eng = huelle.zu_nah(x, y, lage, r - spiel)
    erlaubt &= ~eng
    im_rohteil = _im_rohteil(x, y, w.rohteil, r)
    drin = erlaubt & im_rohteil
    if w.nur_wo is not None:
        drin = drin & np.asarray(w.nur_wo(k, x, y), dtype=bool)
    if maske is not None:
        drin = mit_stand.drin(drin & maske, drin, proben, k.geschlossen)
    if not drin.any():
        return 0
    laeufe = []  # [(Stellen, Austritt hinten)]
    if k.geschlossen and drin.all():
        start = _startstelle(segmente, proben)
        laeufe.append((np.arange(start, start + n + 1) % n, False))
    elif k.geschlossen:
        luecke = int(np.flatnonzero(~drin)[0])
        for von, bis in vb._stuecke(np.roll(drin, -luecke)):
            naechste = (bis + 1 + luecke) % n
            laeufe.append(
                (
                    (np.arange(von, bis + 1) + luecke) % n,
                    bool(erlaubt[naechste] and not im_rohteil[naechste]),
                )
            )
    else:
        for von, bis in vb._stuecke(drin):
            hinten = bis + 1 < n and bool(erlaubt[bis + 1] and not im_rohteil[bis + 1])
            laeufe.append((np.arange(von, bis + 1), hinten))
    anzahl = 0
    for stellen, hinten in laeufe:
        if len(stellen) < 2:
            continue
        # Grenzt der Lauf an eine Stelle, an der der Fräser nicht weiter passt (eng)?
        vorn, danach = int(stellen[0]) - 1, int(stellen[-1]) + 1
        if k.geschlossen:
            vorn, danach = vorn % n, danach % n
        am_engpass = bool((0 <= vorn < n and eng[vorn]) or (0 <= danach < n and eng[danach]))
        _lauf(
            st,
            d,
            segmente,
            proben,
            stellen,
            hinten,
            lage,
            vorige,
            geraeumt,
            huelle,
            ziel,
            w,
            r,
            r_ein,
            gerade,
            schritt,
            mit_stand,
            am_engpass,
        )
        anzahl += 1
    return anzahl


def _einheit(dx, dy):
    laenge = math.hypot(dx, dy)
    return (dx / laenge, dy / laenge) if laenge > 0 else (1.0, 0.0)


def _lauf(
    st,
    d,
    segmente,
    proben,
    stellen,
    hinten,
    lage,
    vorige,
    geraeumt,
    huelle,
    ziel,
    w,
    r,
    r_ein,
    gerade,
    schritt,
    mit_stand=None,
    am_engpass=False,
):
    """Ein Lauf: Eilgang über den Anfang, hinab – in der Luft senkrecht, im Material über die
    Rampe –, tangential hinein, die Bahn, tangential heraus, hinauf. `geraeumt`: (von, bis) –
    so nah und so fern von der Wand haben die Bahnen davor diese Lage schon geräumt; mit
    `mit_stand` (Materialstand) dazu, was die Operationen davor weggenommen haben."""
    x, y = proben.x[stellen], proben.y[stellen]
    geschlossen = len(stellen) > 2 and int(stellen[0]) == int(stellen[-1])
    p0 = (float(x[0]), float(y[0]))
    p1 = (float(x[-1]), float(y[-1]))
    t0 = _einheit(x[1] - x[0], y[1] - y[0])
    t1 = _einheit(x[-1] - x[-2], y[-1] - y[-2])

    # Hinein und heraus nicht näher an eine Wand als die Bahn selbst darf: beim Schruppen
    # Radius + Aufmaß, beim Schlichten der Radius (die Hüllfläche sieht diese Wände nicht) –
    # und nicht näher, als die Bahn an ihren Enden ohnehin ist: An einer Ecke, wo eine offene
    # Wand auf eine höhere trifft, liegt der Versatz am Ende ein paar Hundertstel näher an der
    # Ecke als am Rest; sonst fände das Einfahren dort nie Platz (Testteil, die Stufenwand an
    # der Inselkante: drei Rampen von 194 mm statt eines Bogens, P-2026-10-03-34).
    mindest = min(d, r + max(w.aufmass, 0.0)) - WAND_SPIEL
    an_den_enden = huelle.abstand_zur_wand(np.array([p0[0], p1[0]]), np.array([p0[1], p1[1]]), lage)
    mindest = min(mindest, float(an_den_enden.min()) - GLEICH)

    def frei(qx, qy):
        return bool(huelle.erlaubt(qx, qy, lage, ziel).all()) and bool(
            (huelle.abstand_zur_wand(qx, qy, lage) >= mindest).all()
        )

    ein = _anfahrt(p0, t0, r_ein, gerade, frei, hinein=True, frei_rechts=not w.gleichlauf)
    aus = _anfahrt(p1, t1, r_ein, gerade, frei, hinein=False, frei_rechts=not w.gleichlauf)
    start = ein.aussen if ein is not None else p0
    reichweite = d + (ein.r_e + ein.laenge_gerade if ein is not None else 0.0)
    # Wie nah kommt die Stirn am Einfahrpunkt der Wand – gemessen, nicht geschätzt: In einer
    # kleinen runden Bohrung biegt das Einfahren zur Wand zurück, und der Eilgang hinab streifte
    # den Ring, den die Bahn erst noch nimmt (vom Prüfstand gefunden, P-2026-10-01-29).
    abstand = float(huelle.abstand_zur_wand(np.array([start[0]]), np.array([start[1]]), lage)[0])
    nah = min(abstand, reichweite) - r
    frei_von, frei_bis = geraeumt
    material = (
        vorige > lage + GLEICH
        and bool(_im_rohteil(np.array([start[0]]), np.array([start[1]]), w.rohteil, r)[0])
        and (reichweite + r > frei_bis + GLEICH or nah < frei_von - GLEICH)
        # Mit der Breite steht weiter weg von der Wand nichts mehr: Dort taucht er im Freien ein.
        and (w.breite <= 0 or nah < w.breite - GLEICH)
    )
    oben_hier = vorige if material else lage
    if mit_stand is not None and material:
        # Steht unter der Stirn (eine Zelle weiter) nichts mehr über der Lage, taucht er dort
        # senkrecht ein; sonst endet der Eilgang über dem höchsten Material unter ihr.
        ms = mit_stand.stand
        if ms.hoechste_bei(start[0], start[1], r + ms.schritt) <= lage + MATERIAL:
            material, oben_hier = False, lage
        else:
            oben_hier = max(oben_hier, ms.hoechste_bei(start[0], start[1], r))

    def luft_bei(qx, qy, rand):
        """Je Punkt: steht dort (die Stirn mit Radius `rand`) nichts mehr über der Lage?"""
        luft = ~_im_rohteil(qx, qy, w.rohteil, max(rand, 2 * GLEICH))  # 0: der Punkt
        dq = huelle.abstand_zur_wand(qx, qy, lage)
        luft |= (dq - rand >= frei_von - GLEICH) & (dq + rand <= frei_bis + GLEICH)
        if mit_stand is not None:
            ms = mit_stand.stand
            luft |= np.array(
                [ms.hoechste_bei(x, y, rand + ms.schritt) <= lage + MATERIAL
                 for x, y in zip(qx, qy, strict=True)]
            )  # fmt: skip
        return luft

    neben = None
    if material:
        # Steht die Stirn am Anfang nur zum Teil im Material (am Rand des Rohteils, neben dem
        # schon Geräumten): daneben in der Luft hinab und quer hinein – nicht im Kreis außerhalb
        # des Rohteils hinab (Manuel, 2026-10-12, am Ring: „du bist hier auserhalb vom rohteil
        # ... warum zirkulierst du da nach unten“; T4 streifte das Rohteil dort mit 0,3 mm) – nur,
        # wenn der Weg quer hinein und das Einfahren die Last halten (_haelt_last).
        neben = _luft_daneben(start, r, frei, luft_bei)
        if neben is not None and not _haelt_last(
            _einfahrweg(neben, start, ein, (x, y), 2 * r), None, 0.0, r, w.zeilenabstand, luft_bei
        ):
            neben = None
        if neben is not None:
            material, oben_hier = False, lage
    helix = _helix_radius(start, r, frei) if material else None
    if (
        material
        and am_engpass
        and helix is None
        and not geschlossen
        and not _rampe_reicht(ein, x, y, vorige - lage, w)
    ):
        # Ins Material, ohne Platz für eine Helix, offen, zu kurz für eine Rampe in eine Richtung
        # – die Rampe ginge im Zickzack hin und her (Manuel, 2026-10-18: „alle Zickzack einfahren
        # weg“) –, und gleich daneben passt der Fräser nicht weiter (`am_engpass`, _Huelle
        # .zu_nah): Dort steht, was schon das Schruppen nicht erreichte (an Manuels Ring von vorn
        # die Kerben, die zur Bohrung hin schmaler werden als Ø 10). Der Lauf fällt weg; was
        # stehen bleibt, zeigt das Abfahren. Ein Schrupplauf mitten im Material fällt nie weg:
        # Sonst nähme der nächste mehr als ae.
        st.ausgelassen += 1
        return
    hinab = neben if neben is not None else start
    punkte = st.punkte
    punkte.append(bn.Punkt(True, hinab[0], hinab[1], w.sicher))
    knapp = min(w.sicher, oben_hier + w.sicherheit)
    if knapp < w.sicher - GLEICH:
        punkte.append(bn.Punkt(True, hinab[0], hinab[1], knapp))
    laenge = 0.0
    mitte = start
    if helix is not None and not _haelt_last(
        _einfahrweg(mitte, start, ein, (x, y), 2 * r),
        mitte,
        helix + r,
        r,
        w.zeilenabstand,
        luft_bei,
    ):
        # Nach der Helix fährt die Stirn auf der Lage zum Anfang und das Einfahren entlang; ginge
        # das durch Material, das sie nicht gebohrt hat, schnitte sie dort in voller Breite
        # (Prüfstand, Tasche: 12 mm, seit P-2026-10-12-162) – dann die Rampe längs der Bahn
        # (Manuel: „wenns irgendwie geht auf eine Helix“; Grundsatz: nie in voller Breite).
        helix, mitte = None, start
    if helix is not None:
        # Eine Helix statt der Rampe im Zickzack (Manuel, 2026-10-12: „selbst da würde ich wenns
        # irgendwie geht auf eine helix setzten“; Spezifikation Strategien, Abschnitt 5) – ab dem
        # höchsten Material unter ihrem Kreis (Materialstand), nicht von der vorigen Lage durch
        # die Luft, die die Operationen davor schon geräumt haben (Manuels Ring: 1,9 m Helix in
        # den vom Planfräsen geräumten Nuten).
        oben_helix = _oben_unter_helix(mit_stand, mitte, helix, r, vorige, lage)
        laenge += _helix_hinab(
            punkte, mitte, helix, min(knapp, oben_helix + w.sicherheit), oben_helix, lage, w
        )
        if mitte is not start:  # aus dem Loch zum Anfang
            punkt = bn.Punkt(False, start[0], start[1], lage)
            laenge += bn.weg(punkte[-1], punkt)
            punkte.append(punkt)
    elif material and geschlossen:
        # Eine geschlossene Kontur (Bohrung, Tasche, Platte rundum): auf der vorigen Lage an die
        # Kontur, dann in Fahrtrichtung rundum hinab – eine Wendel längs der Kontur, nie hin und
        # her (Manuel, 2026-10-16: „das auch wirklich alle zickzack fahrten weg sind“; am
        # Prüfstand fuhr die Kontur in den Bohrungen 66, in der Tasche 8 Rampen im Zickzack).
        punkte.append(bn.Punkt(False, start[0], start[1], vorige, True))
        if ein is not None:
            laenge += _anfahrt_punkte(punkte, ein, vorige, hinein=True)
            ein = None  # schon auf der Kontur
        laenge += _wendel(punkte, segmente, proben, stellen, lage, vorige, w, r)
    elif material:
        punkte.append(bn.Punkt(False, start[0], start[1], vorige, True))  # bis ans Material
        laenge += _rampe(punkte, ein, x, y, lage, vorige, w, schritt)
    else:
        punkte.append(bn.Punkt(False, hinab[0], hinab[1], lage, True))
        if neben is not None:  # quer hinein zum Anfang
            punkt = bn.Punkt(False, start[0], start[1], lage)
            laenge += bn.weg(punkte[-1], punkt)
            punkte.append(punkt)
    if ein is not None:
        laenge += _anfahrt_punkte(punkte, ein, lage, hinein=True)
    laenge += _bahnpunkte(punkte, segmente, proben, stellen, lage, hinten, w.austritt, r)
    if aus is not None:
        laenge += _anfahrt_punkte(punkte, aus, lage, hinein=False)
    letzter = punkte[-1]
    punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
    st.laenge += laenge
    st.bahnen += 1


def _anfahrt(p, t, r_ein, gerade, frei, hinein, frei_rechts=False):
    """Das Ein- (`hinein`) oder Ausfahren am Punkt `p` der Bahn mit der Fahrtrichtung `t`: der
    Viertelkreis liegt auf der freien Seite – links (Gleichlauf, das Material rechts) oder
    rechts (`frei_rechts`: Gegenlauf) –, die Gerade davor bzw. danach quer von der Wand
    weg. Passt es nicht (`frei` sagt nein), ohne Gerade, dann halb und viertel so groß; None,
    wenn gar nichts passt – dann senkrecht."""
    rechts = (t[1], -t[0]) if frei_rechts else (-t[1], t[0])
    richtung = -1.0 if hinein else 1.0
    for r_e, lang in ((r_ein, gerade), (r_ein, 0.0), (r_ein / 2, 0.0), (r_ein / 4, 0.0)):
        if r_e <= GLEICH:
            continue
        c = (p[0] + rechts[0] * r_e, p[1] + rechts[1] * r_e)
        a = (c[0] + richtung * t[0] * r_e, c[1] + richtung * t[1] * r_e)
        b = (a[0] + rechts[0] * lang, a[1] + rechts[1] * lang)
        xs, ys = list(np.linspace(b[0], a[0], 5)), list(np.linspace(b[1], a[1], 5))
        bogen_x, bogen_y = [], []
        for s in np.linspace(0.0, 1.0, 9):
            ex, ey = _einheit(
                (1 - s) * (a[0] - c[0]) + s * (p[0] - c[0]),
                (1 - s) * (a[1] - c[1]) + s * (p[1] - c[1]),
            )
            bogen_x.append(c[0] + ex * r_e)
            bogen_y.append(c[1] + ey * r_e)
        if not frei(np.array(xs + bogen_x), np.array(ys + bogen_y)):
            continue
        durch = (bogen_x[4], bogen_y[4])
        uhr = bn.im_uhrzeigersinn(a, p, durch) if hinein else bn.im_uhrzeigersinn(p, a, durch)
        return _Anfahrt(b, a, p, c, uhr, r_e, lang)
    return None


def _anfahrt_punkte(punkte, an, lage, hinein):
    """Die Sätze des Ein- oder Ausfahrens auf der Lage; gibt die Länge zurück."""
    laenge = 0.0
    if hinein:
        folge = [(an.bogen_punkt, None), (an.bahn_punkt, (an.mitte[0], an.mitte[1], an.uhr))]
    else:
        folge = [(an.bogen_punkt, (an.mitte[0], an.mitte[1], an.uhr)), (an.aussen, None)]
    for (px, py), bogen in folge:
        punkt = bn.Punkt(False, px, py, lage, bogen=bogen)
        if bn.weg(punkte[-1], punkt) < 1e-9:
            continue
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge


HELIX_PROBEN = 24  # so viele Punkte auf dem Kreis prüft _helix_radius
LAST_PROBEN = 12  # so viele Punkte je Kreis prüft _haelt_last
EINFAHRWEG_SCHRITT = 0.5  # mm – so dicht tastet _haelt_last den Einfahrweg ab
LUFT_ANTEIL = 1 / 3  # so viel des Umfangs am Anfang muss in Luft sein für _luft_daneben


def _oben_unter_helix(mit_stand, mitte, radius, r, vorige, lage):
    """Bis wohin unter der Helix um `mitte` (die Stirn mit Radius `r` auf ihrem Kreis) noch
    Material steht – höchstens die vorige Lage; ohne Materialstand die vorige Lage."""
    if mit_stand is None:
        return vorige
    ms = mit_stand.stand
    winkel = np.linspace(0.0, 2 * math.pi, 8, endpoint=False)
    hoehen = [ms.hoechste_bei(mitte[0], mitte[1], r + ms.schritt)]
    hoehen += [
        ms.hoechste_bei(
            mitte[0] + radius * math.cos(t), mitte[1] + radius * math.sin(t), r + ms.schritt
        )
        for t in winkel
    ]
    return min(vorige, max(max(hoehen), lage + MATERIAL))


def _einfahrweg(von, start, ein, bahn=None, weiter=0.0, schritt=EINFAHRWEG_SCHRITT):
    """Die Punkte (x, y), über die die Mitte auf der Lage fährt: von `von` zum Anfang `start`,
    dann das Einfahren `ein` (die Gerade, der Bogen) bis auf die Bahn und auf ihr (`bahn`: x, y)
    noch `weiter` mm – je höchstens `schritt` mm auseinander."""
    stuecke = [(von, start)]
    if ein is not None:
        stuecke.append((ein.aussen, ein.bogen_punkt))
    xs, ys = [], []
    for a, b in stuecke:
        n = max(1, int(math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / schritt)))
        for i in range(n + 1):
            xs.append(a[0] + (b[0] - a[0]) * i / n)
            ys.append(a[1] + (b[1] - a[1]) * i / n)
    if ein is not None:
        bogen = _Bogen(ein.bogen_punkt, ein.bahn_punkt, ein.mitte, ein.uhr)
        n = max(1, int(math.ceil(bogen.laenge / schritt)))
        for i in range(1, n + 1):
            px, py = bogen.bei(i / n)
            xs.append(px)
            ys.append(py)
    if bahn is not None and weiter > 0:
        bx, by = bahn
        gefahren = 0.0
        for i in range(1, len(bx)):
            a, b = (float(bx[i - 1]), float(by[i - 1])), (float(bx[i]), float(by[i]))
            lang = math.hypot(b[0] - a[0], b[1] - a[1])
            n = max(1, int(math.ceil(lang / schritt)))
            for j in range(1, n + 1):
                xs.append(a[0] + (b[0] - a[0]) * j / n)
                ys.append(a[1] + (b[1] - a[1]) * j / n)
            gefahren += lang
            if gefahren >= weiter:
                break
    return np.array(xs), np.array(ys)


def _haelt_last(weg, bohr_mitte, bohr_radius, r, ae, luft_bei):
    """Hält die Stirn auf dem Weg (`weg`: x, y) die Last? Material darf sie nur in ihrem äußeren
    Ring treffen, höchstens bahn.LAST_DAUERND · ae tief – innen nichts, außer im gebohrten Loch
    (`bohr_mitte`, `bohr_radius`; None: keins) oder wo `luft_bei` Luft sagt."""
    innen = r - bn.LAST_DAUERND * ae
    if innen <= GLEICH:
        return True
    wx, wy = weg
    winkel = np.linspace(0.0, 2 * math.pi, LAST_PROBEN, endpoint=False)
    rx = np.concatenate(([0.0], innen * np.cos(winkel), 0.5 * innen * np.cos(winkel)))
    ry = np.concatenate(([0.0], innen * np.sin(winkel), 0.5 * innen * np.sin(winkel)))
    qx = (wx[:, None] + rx[None, :]).ravel()
    qy = (wy[:, None] + ry[None, :]).ravel()
    frei = np.zeros(len(qx), dtype=bool)
    if bohr_mitte is not None:
        frei |= np.hypot(qx - bohr_mitte[0], qy - bohr_mitte[1]) <= bohr_radius - GLEICH
    rest = ~frei
    if rest.any():
        frei[rest] = luft_bei(qx[rest], qy[rest], 0.0)
    return bool(frei.all())


def _luft_daneben(start, r, frei, luft_bei):
    """Ein Punkt bis zwei Fräserradien neben `start`, an dem die ganze Stirn in der Luft steht
    (`luft_bei(x, y, Radius)`) und von dem der Weg quer zu `start` frei ist (`frei(x, y)`) – nur,
    wenn am Anfang wenigstens LUFT_ANTEIL des Umfangs in der Luft liegt (sonst würde quer hinein
    ein Stoß in voller Breite: dann die Helix). None, wenn keiner passt."""
    winkel = np.linspace(0.0, 2 * math.pi, HELIX_PROBEN, endpoint=False)
    umfang = luft_bei(start[0] + r * np.cos(winkel), start[1] + r * np.sin(winkel), 0.0)
    if np.mean(umfang) < LUFT_ANTEIL:
        return None
    for weite in (0.5 * r, r, 1.5 * r, 2 * r):
        qx = start[0] + weite * np.cos(winkel)
        qy = start[1] + weite * np.sin(winkel)
        luft = luft_bei(qx, qy, r)
        for i in np.flatnonzero(luft):
            anzahl = max(2, int(math.ceil(weite / 0.25)) + 1)
            wx = np.linspace(qx[i], start[0], anzahl)
            wy = np.linspace(qy[i], start[1], anzahl)
            if frei(wx, wy):
                return (float(qx[i]), float(qy[i]))
    return None


def _helix_radius(mitte, r, frei):
    """Der Radius der Helix um `mitte` (die Mitte des Fräsers läuft darauf), wenn der Kreis
    überall frei ist (`frei(x, y)`: nicht ins Teil, weit genug von der Wand) – wie beim Bohrung
    fräsen bohrung_bahn.KERN_ANTEIL des Fräserradius, sonst die Hälfte; None, wenn keiner passt."""
    from . import bohrung_bahn as bb

    winkel = np.linspace(0.0, 2 * math.pi, HELIX_PROBEN, endpoint=False)
    for anteil in (bb.KERN_ANTEIL, bb.KERN_ANTEIL / 2):
        radius = anteil * r
        qx = mitte[0] + radius * np.cos(winkel)
        qy = mitte[1] + radius * np.sin(winkel)
        if frei(qx, qy):
            return radius
    return None


def _helix_hinab(punkte, mitte, radius, knapp, oben, lage, w):
    """Über dem Material auf den Kreis, bis ans Material, in der Helix (bohrung_bahn._helix, mit
    dem Eintauchwinkel) hinab auf die Lage, zurück in die Mitte. Gibt die Länge zurück."""
    from . import bohrung_bahn as bb

    uhr = not w.gleichlauf
    anfang = (mitte[0] + radius, mitte[1])
    punkte.append(bn.Punkt(True, anfang[0], anfang[1], knapp))
    punkt = bn.Punkt(False, anfang[0], anfang[1], oben, True)
    laenge = bn.weg(punkte[-1], punkt)
    punkte.append(punkt)
    steigung = max(
        2 * math.pi * radius * math.tan(math.radians(max(w.eintauchwinkel, 0.1))), bb.MIN_STEIGUNG
    )
    stueck, _winkel, _umlaeufe = bb._helix(punkte, mitte, radius, 0.0, oben, lage, steigung, uhr)
    laenge += stueck
    punkt = bn.Punkt(False, mitte[0], mitte[1], lage)
    laenge += bn.weg(punkte[-1], punkt)
    punkte.append(punkt)
    return laenge


# So klein darf die Schleife der Kontur (ihr Radius: Umfang / 2π) für die Wendel höchstens sein
# – sonst geht es senkrecht hinab (Eintauchen): Am Testteil (Dreieckstasche, Ø 12 mit 0,2 mm
# Spiel) kreiste die Kontur 57-mal auf einem Dreieck von 0,35 mm Seite 5 mm hinab – ein Wackeln,
# kein Weg (der Prüfstand zählte eine Kehre). Die Wendel selbst ist nicht langsamer, je kleiner
# die Schleife: Ihr Weg ist Tiefe ÷ tan(Eintauchwinkel), und an der Wand einer Bohrung schneidet
# sie dabei – darum nur ein kleines Maß (nicht ein Zehntel des Durchmessers: In Bohrungen bis
# Ø 14,4 mit Ø 12 fuhr die Kontur dann durch das gebohrte Loch hinab, am Prüfstand 12 statt 9 %
# Luft).
WENDEL_MIN_RADIUS = 0.5  # mm


def _wendel(punkte, segmente, proben, stellen, lage, vorige, w, r):
    """Hinab längs der geschlossenen Kontur (der Lauf `stellen`; die letzte Stelle ist die erste)
    in ihrer Fahrtrichtung, mit dem Eintauchwinkel, rundum, bis die Lage erreicht ist – dann auf
    ihr weiter bis zum Anfang. Nie zurück. Je Segmentgrenze ein Satz wie in _bahnpunkte, ein Bogen
    als Bogen mit fallendem Z (eine Wendel): Über die Abtastpunkte als Geraden hielt die Maschine
    in einer kleinen Bohrung an jeder Ecke (am Prüfstand 2185 Halte). Gibt die Länge zurück."""
    steil = math.tan(math.radians(w.eintauchwinkel if w.eintauchwinkel > 0 else vb.EINTAUCHWINKEL))
    x, y, seg = proben.x, proben.y, proben.segment
    idx = [int(i) for i in stellen]
    m = len(idx) - 1
    stuecke = np.hypot(np.diff(x[idx]), np.diff(y[idx]))
    laenge = 0.0
    if m < 2 or float(stuecke.sum()) < WENDEL_MIN_RADIUS * 2.0 * math.pi:
        punkt = bn.Punkt(False, float(x[idx[0]]), float(y[idx[0]]), lage, True)  # senkrecht
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
        return laenge
    hoehe = vorige
    unten = False
    pos = 0
    while True:
        weiter = pos + 1
        h, i = idx[pos], idx[weiter]
        satz = seg[i] != seg[h] or weiter == m  # eine Segmentgrenze oder der Anfang
        if not unten:
            hoehe -= steil * float(stuecke[pos])
            if hoehe <= lage + GLEICH:
                hoehe, unten, satz = lage, True, True  # unten: hier ein Satz
        if satz:
            punkt = bn.Punkt(
                False, float(x[i]), float(y[i]), hoehe, bogen=segmente[int(seg[h])].bogen
            )
            if bn.weg(punkte[-1], punkt) > 1e-9:
                laenge += bn.weg(punkte[-1], punkt)
                punkte.append(punkt)
        pos = weiter % m
        if unten and pos == 0:
            return laenge


def _rampe_reicht(ein, x, y, tiefe, w):
    """Kommt die Rampe (_rampe: längs des Einfahrens und der Bahn x, y) um `tiefe` hinab, ohne
    umzukehren?"""
    weg = 0.0
    if ein is not None:
        weg += math.hypot(ein.bogen_punkt[0] - ein.aussen[0], ein.bogen_punkt[1] - ein.aussen[1])
        weg += _Bogen(ein.bogen_punkt, ein.bahn_punkt, ein.mitte, ein.uhr).laenge
    xs, ys = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    weg += float(np.sum(np.hypot(np.diff(xs), np.diff(ys))))
    winkel = w.eintauchwinkel if w.eintauchwinkel > 0 else vb.EINTAUCHWINKEL
    return weg * math.tan(math.radians(winkel)) >= tiefe - GLEICH


def _rampe(punkte, ein, x, y, lage, vorige, w, schritt):
    """Die Rampe ins Material längs des Einfahrens und der Bahn (vierachs_bahn._rampe): hinab
    mit dem Eintauchwinkel, dann auf der Lage zurück zum Anfang. Gibt die Länge zurück."""
    xs, ys = [], []
    if ein is not None:
        for von, nach in ((ein.aussen, ein.bogen_punkt),):
            laenge = math.hypot(nach[0] - von[0], nach[1] - von[1])
            anzahl = max(1, int(math.ceil(laenge / schritt - 1e-9)))
            for i in range(anzahl):
                xs.append(von[0] + (nach[0] - von[0]) * i / anzahl)
                ys.append(von[1] + (nach[1] - von[1]) * i / anzahl)
        bogen = _Bogen(ein.bogen_punkt, ein.bahn_punkt, ein.mitte, ein.uhr)
        anzahl = max(1, int(math.ceil(bogen.laenge / schritt - 1e-9)))
        for i in range(anzahl):
            px, py = bogen.bei(i / anzahl)
            xs.append(px)
            ys.append(py)
    xs.extend(float(v) for v in x)
    ys.extend(float(v) for v in y)
    px, py = np.array(xs), np.array(ys)
    a = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(px), np.diff(py)))])
    if len(a) < 2 or a[-1] <= GLEICH:
        punkt = bn.Punkt(False, float(px[0]), float(py[0]), lage, True)
        punkte.append(punkt)
        return 0.0
    tiefe = np.full(len(a), lage)
    still = np.zeros(len(a))
    laenge = 0.0
    for stelle_a, stelle_z, _phi in vb._rampe(a, tiefe, still, 0, len(a) - 1, vorige, w):
        m = int(np.searchsorted(a, stelle_a))
        m = min(max(m, 0), len(a) - 1)
        punkt = bn.Punkt(False, float(px[m]), float(py[m]), float(stelle_z))
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge


def _bahnpunkte(punkte, segmente, proben, stellen, lage, hinten, austritt, r, anteile=None):
    """Die Sätze der Bahn über die Stellen: je Segmentgrenze ein Satz – Gerade oder Bogen (G2/G3)
    –, der letzte bis zum Ende des Laufs. Endet der Lauf, weil das Rohteil endet (`hinten`),
    fahren die letzten 2 R mit dem Austritts-Anteil des Vorschubs. `anteile`: je Probe ein
    Vorschubanteil (≤ 1) – ein Satz fährt mit dem kleinsten seiner Proben. Gibt die Länge
    zurück."""
    x, y, seg = proben.x, proben.y, proben.segment
    langsam_ab = None
    if hinten:
        weg = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x[stellen]), np.diff(y[stellen])))])
        langsam_ab = int(np.flatnonzero(weg[-1] - weg <= 2 * r + GLEICH)[0])
    laenge = 0.0
    satz_ab = 0  # die erste Stelle des laufenden Satzes
    for pos in range(1, len(stellen)):
        i, h = int(stellen[pos]), int(stellen[pos - 1])
        letzte = pos == len(stellen) - 1
        if seg[i] == seg[h] and not letzte and pos != langsam_ab:
            continue
        langsam = langsam_ab is not None and (pos > langsam_ab or langsam_ab == 0)
        anteil = austritt if langsam else 1.0
        if anteile is not None:
            anteil = min(anteil, float(np.min(anteile[stellen[satz_ab : pos + 1]])))
        satz_ab = pos
        punkt = bn.Punkt(
            False,
            float(x[i]),
            float(y[i]),
            lage,
            bogen=segmente[int(seg[h])].bogen,
            anteil=anteil,
        )
        if bn.weg(punkte[-1], punkt) < 1e-9:
            continue
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge
