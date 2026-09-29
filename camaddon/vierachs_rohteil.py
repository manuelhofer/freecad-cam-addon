# SPDX-License-Identifier: LGPL-2.1-or-later
"""Teil in die Stange: Lage, Mitte und Stange für die 4-Achs-Bearbeitung
(Spezifikation W-003, Abschnitt 5).

Eine ebene Stirnfläche des Teils kommt vorne an eine runde Stange: Ihre
Außennormale wird zur Stangenachse nach vorne, und die Fläche liegt bei
a = 0 – wie Z0 an der Drehmaschine; das Teil liegt bei a ≤ 0. Mittig heißt
wahlweise „Mitte der runden Fläche“ oder „ganzes Teil möglichst mittig“ –
der kleinste Kreis um das Teil, in Achsrichtung gesehen. Wohin die
Stangenachse im Job zeigt, sagt die Maschine (vierachs_achsen) oder der
Buchstabe der Rundachse: A liegt in X, B in Y, C in Z (Abschnitt 4). So legt
FreeCADs Bahnanzeige spätere Bahnen von selbst richtig um das Teil – sie
dreht A um X, B um Y und C um Z.

Teuer ist nur das Vermessen einer Fläche (Tessellierung, Hülle, kleinster
Kreis); vermesse() macht es einmal, lage() rechnet daraus für jede Mitte,
Drehlage und Rundachse sofort – der Assistent ruft es bei jeder Eingabe.

richte_ein() baut daraus einen CAM-Job: Das Teil liegt im Modell-Klon des
Jobs an seiner Stelle, das Original bleibt, wo es ist; das Rohteil ist ein
Zylinder. Die Transaktion hält der Aufrufer (der Assistent in
gui_vierachs.py), damit ein Klick ein Schritt Rückgängig bleibt.

Läuft ohne Oberfläche.
"""

import math
import random
from dataclasses import dataclass

import FreeCAD
import Part

from .sprache import tr

# Rundachse ohne Maschine → (Stangenachse nach vorne, woher das Werkzeug
# kommt), in den Achsen des Jobs.
ACHSEN = {
    "A": (FreeCAD.Vector(1, 0, 0), FreeCAD.Vector(0, 0, 1)),
    "B": (FreeCAD.Vector(0, 1, 0), FreeCAD.Vector(0, 0, 1)),
    "C": (FreeCAD.Vector(0, 0, 1), FreeCAD.Vector(1, 0, 0)),
}

MITTE_AUTO = "auto"  # die runde Fläche, wenn das Teil so passt – sonst das ganze Teil
MITTE_FLAECHE = "flaeche"
MITTE_TEIL = "teil"

# Vorschläge (Spezifikation W-003, Abschnitt 15) – im Assistenten einstellbar.
PLANAUFMASS = 1.0  # mm
ABSTECHBREITE = 3.0  # mm
SPANNLAENGE = 30.0  # mm
RUNDACHSE = "A"

# So tief steckt die Stange im Futter – am Job, damit „Auf der Maschine prüfen“ den
# Nullpunkt so vorschlägt (W-003 V2c); ausgeblendet.
EIGENSCHAFT_SPANNLAENGE = "CamAddonSpannlaenge"

MIN_AUFMASS = 1.0  # mm am Radius, mindestens, beim Vorschlag für den Stangen-Ø
STUFE_MM = 5.0  # Stangen-Ø in 5-mm-Schritten …
STUFE_ZOLL = 25.4 / 8  # … oder in 1/8"
TESSELLIERUNG = 0.01  # mm – so nah folgen die Punkte gekrümmten Flächen
GENAU = 1e-6  # mm – kleiner als das gilt als gleich


@dataclass
class Vermessung:
    """Was an Teil und Stirnfläche teuer zu rechnen ist – einmal je Fläche (vermesse())."""

    normale: FreeCAD.Vector  # Außennormale der Fläche = Stangenachse nach vorne
    quer: tuple  # zwei Einheitsvektoren quer zur Achse (u, v)
    hoehe: float  # Lage der Fläche längs der Normale
    kreis: tuple  # (Mitte, Radius) der runden Fläche, oder None
    mitte_flaeche: tuple  # Mitte der Fläche, quer gesehen (x, y)
    mitte_teil: tuple  # Mitte des kleinsten Kreises um das Teil, quer gesehen (x, y)
    noetig: dict  # Ø, den die Stange je Mitte mindestens braucht (mm)
    vorne: float  # a des vordersten Punkts (meist 0)
    hinten: float  # a des hintersten Punkts (negativ)

    @property
    def laenge(self):
        """Länge des Teils längs der Stange."""
        return self.vorne - self.hinten


@dataclass
class Lage:
    """Wo das Teil in der Stange liegt – Ergebnis von lage()."""

    placement: FreeCAD.Placement  # vom Teil (Weltkoordinaten) in den Job
    mitte: str  # MITTE_FLAECHE oder MITTE_TEIL – die, mit der gerechnet wurde
    vermessung: Vermessung

    @property
    def durchmesser(self):
        """Der Ø, den die Stange mit dieser Mitte mindestens braucht."""
        return self.vermessung.noetig[self.mitte]


@dataclass
class Stange:
    """Die runde Stange: Ø und die Längen vor und hinter dem Teil (mm)."""

    durchmesser: float
    planaufmass: float = PLANAUFMASS
    abstechbreite: float = ABSTECHBREITE
    spannlaenge: float = SPANNLAENGE


def ist_eben(flaeche):
    """Ist die Fläche eben? Auch eine eben liegende B-Spline-Fläche zählt."""
    return flaeche.findPlane() is not None


def aussennormale(flaeche):
    """Die Normale der ebenen Fläche, vom Material weg, als Einheitsvektor.

    `normalAt` beachtet die Orientierung der Fläche im Körper – an einer
    Unterseite zeigt sie nach unten (ausprobiert, P-2026-09-26-78).
    """
    u0, u1, v0, v1 = flaeche.ParameterRange
    normale = flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    normale.normalize()
    return normale


def kreis_der_flaeche(flaeche):
    """(Mitte, Radius), wenn die Außenkante der Fläche ein Kreis ist – auch aus
    mehreren Bögen mit gleicher Mitte und gleichem Radius; sonst None."""
    kurven = [kante.Curve for kante in flaeche.OuterWire.Edges]
    if not kurven or not all(isinstance(kurve, Part.Circle) for kurve in kurven):
        return None
    mitte, radius = kurven[0].Center, kurven[0].Radius
    for kurve in kurven[1:]:
        if (kurve.Center - mitte).Length > GENAU or abs(kurve.Radius - radius) > GENAU:
            return None
    return FreeCAD.Vector(mitte), radius


def konvexe_huelle(punkte):
    """Die Ecken der konvexen Hülle ebener Punkte [(x, y), …], gegen den Uhrzeigersinn
    (Monotone Chain). Doppelte Punkte zählen einmal."""
    sortiert = sorted(set(punkte))
    if len(sortiert) <= 2:
        return sortiert

    def links_herum(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]) > 0

    unten, oben = [], []
    for punkt in sortiert:
        while len(unten) >= 2 and not links_herum(unten[-2], unten[-1], punkt):
            unten.pop()
        unten.append(punkt)
    for punkt in reversed(sortiert):
        while len(oben) >= 2 and not links_herum(oben[-2], oben[-1], punkt):
            oben.pop()
        oben.append(punkt)
    return unten[:-1] + oben[:-1]


def kleinster_kreis(punkte):
    """(x, y, r): der kleinste Kreis um ebene Punkte [(x, y), …].

    Welzl als Schleife statt Rekursion (Python stieße bei vielen Punkten an
    seine Rekursionsgrenze), in fester zufälliger Reihenfolge – dasselbe Teil
    gibt immer dasselbe Ergebnis. Für viele Punkte vorher konvexe_huelle():
    der Kreis ist derselbe, die Rechnung viel kürzer.
    """
    folge = list(punkte)
    if not folge:
        return 0.0, 0.0, 0.0
    random.Random(1).shuffle(folge)
    kreis = (folge[0][0], folge[0][1], 0.0)
    for i in range(1, len(folge)):
        if _im_kreis(kreis, folge[i]):
            continue
        kreis = (folge[i][0], folge[i][1], 0.0)
        for j in range(i):
            if _im_kreis(kreis, folge[j]):
                continue
            kreis = _kreis_durch_zwei(folge[i], folge[j])
            for k in range(j):
                if not _im_kreis(kreis, folge[k]):
                    kreis = _kreis_durch_drei(folge[i], folge[j], folge[k])
    return kreis


def _im_kreis(kreis, punkt):
    return math.hypot(punkt[0] - kreis[0], punkt[1] - kreis[1]) <= kreis[2] + GENAU


def _kreis_durch_zwei(a, b):
    """Der Kreis mit der Strecke a–b als Durchmesser."""
    x, y = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    return x, y, math.hypot(a[0] - x, a[1] - y)


def _kreis_durch_drei(a, b, c):
    """Der Umkreis dreier Punkte; liegen sie auf einer Geraden, der Kreis um die beiden
    äußersten."""
    bx, by = b[0] - a[0], b[1] - a[1]
    cx, cy = c[0] - a[0], c[1] - a[1]
    nenner = 2 * (bx * cy - by * cx)
    if abs(nenner) < 1e-12:
        return max(
            (_kreis_durch_zwei(*paar) for paar in ((a, b), (a, c), (b, c))),
            key=lambda kreis: kreis[2],
        )
    b2, c2 = bx * bx + by * by, cx * cx + cy * cy
    x = (cy * b2 - by * c2) / nenner
    y = (bx * c2 - cx * b2) / nenner
    return a[0] + x, a[1] + y, math.hypot(x, y)


def _quer(achse):
    """Zwei Einheitsvektoren quer zur Achse und rechtwinklig zueinander."""
    hilfe = FreeCAD.Vector(1, 0, 0) if abs(achse.x) < 0.9 else FreeCAD.Vector(0, 1, 0)
    u = achse.cross(hilfe)
    u.normalize()
    v = achse.cross(u)
    v.normalize()
    return u, v


def vermesse(form, flaeche):
    """Vermisst Teil und Stirnfläche (Vermessung) – beide in Weltkoordinaten.

    ValueError, wenn die Fläche nicht eben ist: Nur eine ebene Fläche liegt
    vorne an der Stange an.
    """
    if not ist_eben(flaeche):
        raise ValueError("Die Stirnfläche ist nicht eben.")
    normale = aussennormale(flaeche)
    u, v = _quer(normale)
    # Die Tessellierung enthält Ecken und Kanten – für den Umriss reicht das.
    punkte, _dreiecke = form.tessellate(TESSELLIERUNG)
    punkte = list(punkte) + [ecke.Point for ecke in form.Vertexes]
    hoehe = flaeche.CenterOfMass.dot(normale)
    laengs = [p.dot(normale) - hoehe for p in punkte]
    # Der weiteste Punkt von einer Mitte liegt immer auf der Hülle.
    huelle = konvexe_huelle([(p.dot(u), p.dot(v)) for p in punkte])
    kreis = kreis_der_flaeche(flaeche)
    mitte = kreis[0] if kreis else flaeche.CenterOfMass
    mitte_flaeche = (mitte.dot(u), mitte.dot(v))
    x, y, r = kleinster_kreis(huelle)
    weitester = max(math.hypot(p[0] - mitte_flaeche[0], p[1] - mitte_flaeche[1]) for p in huelle)
    return Vermessung(
        normale=normale,
        quer=(u, v),
        hoehe=hoehe,
        kreis=kreis,
        mitte_flaeche=mitte_flaeche,
        mitte_teil=(x, y),
        noetig={MITTE_FLAECHE: 2 * weitester, MITTE_TEIL: 2 * r},
        vorne=max(laengs),
        hinten=min(laengs),
    )


def laengs_von(achse):
    """Die Stangenachse nach vorne, in den Achsen des Jobs: aus dem Buchstaben A, B, C
    (ohne Maschine), aus einer vierachs_achsen.Stangenachse oder die Richtung selbst."""
    if isinstance(achse, str):
        return ACHSEN[achse][0]
    if isinstance(achse, FreeCAD.Vector):
        return achse
    return achse.laengs


def welche_mitte(vermessung, mitte=MITTE_AUTO, durchmesser=0.0):
    """Die Mitte, mit der gerechnet wird. MITTE_AUTO: die runde Fläche, wenn es eine ist
    und das Teil so in eine Stange mit `durchmesser` passt (0: noch keiner gewählt) –
    sonst das ganze Teil."""
    if mitte != MITTE_AUTO:
        return mitte
    passt = durchmesser <= 0 or vermessung.noetig[MITTE_FLAECHE] <= durchmesser + GENAU
    return MITTE_FLAECHE if vermessung.kreis and passt else MITTE_TEIL


def lage(vermessung, achse, mitte=MITTE_AUTO, drehlage=0.0, durchmesser=0.0):
    """Die Lage des Teils in der Stange (Lage) für die Rundachse `achse` – ein Buchstabe
    (A, B, C) oder eine Stangenachse der Maschine (laengs_von).

    Die Stirnfläche kommt auf a = 0, die gewählte Mitte auf die Achse, die
    Normale auf die Stangenachse nach vorne; `drehlage` dreht das Teil um sie
    (Grad).
    """
    gewaehlt = welche_mitte(vermessung, mitte, durchmesser)
    x, y = vermessung.mitte_flaeche if gewaehlt == MITTE_FLAECHE else vermessung.mitte_teil
    u, v = vermessung.quer
    auf_der_achse = u * x + v * y + vermessung.normale * vermessung.hoehe
    laengs = laengs_von(achse)
    drehung = FreeCAD.Rotation(laengs, drehlage).multiply(
        FreeCAD.Rotation(vermessung.normale, laengs)
    )
    placement = FreeCAD.Placement(drehung.multVec(auf_der_achse) * -1, drehung)
    return Lage(placement, gewaehlt, vermessung)


def berechne(form, flaeche, achse, mitte=MITTE_AUTO, drehlage=0.0, durchmesser=0.0):
    """vermesse() und lage() in einem – für einmalige Rechnungen."""
    return lage(vermesse(form, flaeche), achse, mitte, drehlage, durchmesser)


def aufmass(lage_, durchmesser):
    """So viel bleibt rundum mindestens stehen (mm); negativ: das Teil passt nicht."""
    return (durchmesser - lage_.durchmesser) / 2


def vorschlag_durchmesser(noetig, zoll=False):
    """Vorschlag für den Stangen-Ø in mm: der nächste 5-mm-Schritt (in Zoll 1/8"), der
    rundum mindestens MIN_AUFMASS lässt."""
    stufe = STUFE_ZOLL if zoll else STUFE_MM
    return math.ceil((noetig + 2 * MIN_AUFMASS) / stufe - 1e-9) * stufe


def stangenlaenge(vermessung, stange):
    """Länge der Stange: Planaufmaß, Teil, Abstechbreite und Spannlänge."""
    return vermessung.laenge + stange.planaufmass + stange.abstechbreite + stange.spannlaenge


def stangen_placement(vermessung, stange, achse):
    """Die Lage des Zylinders im Job. CAM baut ihn ab seinem Ursprung entlang +Z – hier
    gedreht auf die Stangenachse, mit dem Ursprung hinter der Spannlänge."""
    laengs = laengs_von(achse)
    hinten = vermessung.hinten - stange.abstechbreite - stange.spannlaenge
    return FreeCAD.Placement(laengs * hinten, FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), laengs))


def original(objekt):
    """Das Teil hinter einem Modell-Klon eines Jobs – sonst das Objekt selbst."""
    if getattr(objekt, "PathResource", "") == "Model" and getattr(objekt, "Objects", None):
        return objekt.Objects[0]
    return objekt


def modell(job):
    """Der Modell-Klon des Jobs – das Teil, wie es im Job liegt."""
    return job.Model.Group[0]


def richte_ein(dokument, teil, lage_, stange, achse, job=None, beschriftung=None):
    """Legt einen CAM-Job an (oder nimmt `job`) und legt das Teil in die Stange.

    Das Teil liegt danach im Modell-Klon des Jobs an seiner Stelle; das
    Original bleibt, wo es ist. Gerechnet wird immer vom Original aus
    (Klon = Lage · Original), so häufen sich Änderungen nicht an – der Klon
    liegt beim Anlegen genau wie das Original (ausprobiert in 1.1.3 und im
    Wochen-Build, P-2026-09-26-78). Das Rohteil wird ein Zylinder, wie ihn
    FreeCADs Job-Dialog anlegt. Keine eigene Transaktion. Gibt den Job zurück.
    """
    import Path.Main.Job as PathJob
    import Path.Main.Stock as PathStock

    # Job.Create und CreateCylinder legen im aktiven Dokument an.
    FreeCAD.setActiveDocument(dokument.Name)
    if job is None:
        job = PathJob.Create("Job", [teil])
    if beschriftung:
        job.Label = beschriftung
    modell(job).Placement = lage_.placement.multiply(teil.Placement)

    laenge = stangenlaenge(lage_.vermessung, stange)
    platz = stangen_placement(lage_.vermessung, stange, achse)
    rohteil = job.Stock
    if (
        rohteil is not None
        and PathStock.StockType.FromStock(rohteil) == PathStock.StockType.CreateCylinder
    ):
        rohteil.Radius = stange.durchmesser / 2
        rohteil.Height = laenge
        rohteil.Placement = platz
    else:
        neu = PathStock.CreateCylinder(job, stange.durchmesser / 2, laenge, platz)
        # Wie FreeCADs Job-Dialog (StockEdit.setStock): erst das alte weg, dann das neue.
        if rohteil is not None:
            dokument.removeObject(rohteil.Name)
        job.Stock = neu
    _merke_spannlaenge(job, stange.spannlaenge)
    dokument.recompute()
    return job


@dataclass
class Einstellung:
    """Wie der Assistent einen Job eingerichtet hat – aus dem Job zurückgerechnet
    (einstellung())."""

    teil: object  # das Original
    flaeche: str  # „FaceN“ – die Stirnfläche
    vermessung: Vermessung
    laengs: FreeCAD.Vector  # die Stangenachse nach vorne, in den Achsen des Jobs
    mitte: str  # MITTE_FLAECHE oder MITTE_TEIL
    drehlage: float  # Grad, 0 … 360
    stange: Stange


def einstellung(job):
    """Rechnet aus einem Job des Assistenten zurück, wie er eingerichtet ist (Einstellung) –
    None, wenn er nicht (mehr) so aussieht, wie richte_ein() ihn anlegt: kein Zylinder,
    Klon verschoben, Stirnfläche nicht vorne.

    Am Job gemerkt ist nur die Spannlänge; alles andere steht im Job selbst: Der
    Klon liegt bei Lage · Original, die Stirnfläche bei a = 0 mit der
    Außennormale längs, der Zylinder reicht vom Futter bis vor das Planaufmaß.
    So gilt, was im Job steht – auch für Jobs aus älteren Versionen.
    """
    rohteil = getattr(job, "Stock", None)
    spann = spannlaenge(job)
    if rohteil is None or not hasattr(rohteil, "Radius") or spann <= 0:
        return None
    try:
        klon = modell(job)
    except (AttributeError, IndexError):
        return None
    teil = original(klon)
    form = getattr(teil, "Shape", None)
    if teil is klon or form is None or form.isNull():
        return None
    laengs = rohteil.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    platz = klon.Placement.multiply(teil.Placement.inverse())  # Welt → Job
    flaeche = _stirnflaeche(form, platz, laengs)
    if flaeche is None:
        return None
    vermessung = vermesse(form, form.getElement(flaeche))
    drehlage = _drehlage(platz, vermessung.normale, laengs)
    if drehlage is None:
        return None
    groesse = max(1.0, form.BoundBox.DiagonalLength)
    mitte = next(
        (
            m
            for m in (MITTE_FLAECHE, MITTE_TEIL)
            if (lage(vermessung, laengs, m, drehlage).placement.Base - platz.Base).Length
            < 1e-7 * groesse
        ),
        None,
    )
    a_hinten = rohteil.Placement.Base.dot(laengs)
    planaufmass = a_hinten + float(rohteil.Height) - vermessung.vorne
    abstechbreite = vermessung.hinten - a_hinten - spann
    if mitte is None or planaufmass < -GENAU or abstechbreite < -GENAU:
        return None
    stange = Stange(
        round(2 * float(rohteil.Radius), 6),
        round(max(0.0, planaufmass), 6),
        round(max(0.0, abstechbreite), 6),
        spann,
    )
    return Einstellung(teil, flaeche, vermessung, laengs, mitte, drehlage, stange)


def _stirnflaeche(form, platz, laengs):
    """„FaceN“ der ebenen Fläche, die nach `platz` vorne an der Stange liegt – Außennormale
    längs, bei a = 0 –, oder None."""
    for nummer, flaeche in enumerate(form.Faces, start=1):
        if not ist_eben(flaeche):
            continue
        normale = platz.Rotation.multVec(aussennormale(flaeche))
        if (normale - laengs).Length < 1e-6 and abs(
            platz.multVec(flaeche.CenterOfMass).dot(laengs)
        ) < 1e-6 * max(1.0, form.BoundBox.DiagonalLength):
            return f"Face{nummer}"
    return None


def _drehlage(platz, normale, laengs):
    """Um wie viel Grad lage() das Teil um die Stangenachse gedreht hat (0 … 360) – None,
    wenn die Drehung von `platz` nicht so zustande kommt."""
    rest = platz.Rotation.multiply(FreeCAD.Rotation(normale, laengs).inverted())
    if (rest.multVec(laengs) - laengs).Length > 1e-6:
        return None
    quer = _quer(laengs)[0]
    gedreht = rest.multVec(quer)
    winkel = math.degrees(math.atan2(quer.cross(gedreht).dot(laengs), quer.dot(gedreht)))
    winkel = round(winkel % 360.0, 6)
    return 0.0 if winkel >= 360.0 else winkel


def spannlaenge(job):
    """Wie tief die Stange eines Jobs aus dem Assistenten im Futter steckt (mm), sonst 0."""
    return float(getattr(job, EIGENSCHAFT_SPANNLAENGE, 0.0) or 0.0)


def _merke_spannlaenge(job, laenge):
    if EIGENSCHAFT_SPANNLAENGE not in job.PropertiesList:
        job.addProperty(
            "App::PropertyFloat",
            EIGENSCHAFT_SPANNLAENGE,
            "CAM-Addon",
            tr("va.eigenschaft.spannlaenge"),
        )
        job.setEditorMode(EIGENSCHAFT_SPANNLAENGE, 2)  # ausgeblendet – das Addon nutzt sie
    setattr(job, EIGENSCHAFT_SPANNLAENGE, float(laenge))
