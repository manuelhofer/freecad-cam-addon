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

Eine runde Fläche (Zylinder, Kegel, Kugel, Torus – ein Drehteil, V2b) geht auch: Ihre Achse
wird die Stangenachse, vorne liegt das Ende des Teils, an dem man geklickt hat (`nahe`), und
„Umdrehen“ tauscht die Enden; die Mitte der Fläche ist ihre Achse. Eine ebene Fläche „umgedreht“
liegt am Futter und wird abgestochen – vorne ist das andere Ende (eine Figur auf ihrer
Standfläche, etwa aus einem STL; P-2026-10-11-100).

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
# Die Abstechbreite – am Job, weil die Lücke hinter dem Teil auch größer sein kann (der
# Fräser braucht Platz, V3f): So rechnet einstellung() sie zurück; ausgeblendet.
EIGENSCHAFT_ABSTECHBREITE = "CamAddonAbstechbreite"

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
    rund: bool = False  # eine runde Fläche (V2b): ihre Achse ist die Stangenachse

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
    """Die runde Stange: Ø und die Längen vor und hinter dem Teil (mm).

    Hinter dem Teil bis zur Spannfläche liegt die Lücke: die Abstechbreite – oder
    mehr, wenn ein Fräser dort Platz braucht (`frei_hinten`: Überlauf, Fräserradius
    und Abstand zum Futter, V3f).
    """

    durchmesser: float
    planaufmass: float = PLANAUFMASS
    abstechbreite: float = ABSTECHBREITE
    spannlaenge: float = SPANNLAENGE
    frei_hinten: float = 0.0

    @property
    def luecke(self):
        """Vom hinteren Ende des Teils bis zur Spannfläche (mm)."""
        return max(self.abstechbreite, self.frei_hinten)


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


def achse_der_runden(flaeche):
    """(Punkt auf der Achse, Richtung) einer runden Fläche – Zylinder, Kegel, Kugel, Torus –,
    sonst None."""
    flaeche_ = flaeche.Surface
    if not isinstance(flaeche_, (Part.Cylinder, Part.Cone, Part.Sphere, Part.Toroid)):
        return None
    richtung = FreeCAD.Vector(flaeche_.Axis)
    if richtung.Length < GENAU:
        return None
    richtung.normalize()
    return FreeCAD.Vector(flaeche_.Center), richtung


def vermesse(form, flaeche, nahe=None, umgedreht=False):
    """Vermisst Teil und Stirnfläche (Vermessung) – beide in Weltkoordinaten.

    Eine runde Fläche (achse_der_runden, V2b): ihre Achse wird die Stangenachse, nach vorne
    das Ende des Teils, das `nahe` (der angeklickte Punkt; ohne: die Mitte der Fläche) näher
    liegt – `umgedreht`: das andere. ValueError, wenn die Fläche weder eben noch rund ist.
    """
    if not ist_eben(flaeche):
        rund = achse_der_runden(flaeche)
        if rund is None:
            raise ValueError("Die Stirnfläche ist weder eben noch rund.")
        return _vermesse_rund(form, flaeche, rund, nahe, umgedreht)
    normale = aussennormale(flaeche)
    if umgedreht:  # die Fläche liegt am Futter: Die Stange zeigt von ihr weg nach vorne
        normale = normale * -1
    u, v = _quer(normale)
    punkte = _punkte(form)
    # Umgedreht ist vorne das andere Ende des Teils, sonst die Fläche selbst.
    hoehe = max(p.dot(normale) for p in punkte) if umgedreht else flaeche.CenterOfMass.dot(normale)
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


TEILACHSEN = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}  # statt einer Fläche (W-017)


def vermesse_achse(form, achse, umgedreht=False):
    """Vermisst das Teil, das mit seiner Achse `achse` („X“, „Y“, „Z“ – TEILACHSEN) längs der
    Stange liegt, ihr Plus-Ende vorne (`umgedreht`: das Minus-Ende) – ohne eine Fläche (Manuel,
    2026-10-11, zu einem STL: „X, Y oder Z zur Wahl – beides ja“). Vorne ist das vorderste Ende
    des Teils; die Mitte ist die des ganzen Teils."""
    normale = FreeCAD.Vector(*TEILACHSEN[achse])
    if umgedreht:
        normale = normale * -1
    u, v = _quer(normale)
    punkte = _punkte(form)
    hoehe = max(p.dot(normale) for p in punkte)
    laengs = [p.dot(normale) - hoehe for p in punkte]
    huelle = konvexe_huelle([(p.dot(u), p.dot(v)) for p in punkte])
    x, y, r = kleinster_kreis(huelle)
    return Vermessung(
        normale=normale,
        quer=(u, v),
        hoehe=hoehe,
        kreis=None,
        mitte_flaeche=(x, y),
        mitte_teil=(x, y),
        noetig={MITTE_FLAECHE: 2 * r, MITTE_TEIL: 2 * r},
        vorne=max(laengs),
        hinten=min(laengs),
    )


def zylinder_um(form, oben=0.0, seite=0.0, unten=0.0):
    """(Mitte x, Mitte y, Radius, z unten, Höhe) des stehenden Zylinders um das Teil – der
    kleinste Kreis um seinen Umriss von oben, mit Aufmaß `seite` am Umfang, `oben` und `unten` in
    der Höhe (W-021; Manuel, 2026-10-12: „ich kann auch auf der fräsmaschine ein dreibacken futter
    einspannen und somit runde rohteile haben“)."""
    punkte = _punkte(form)
    x, y, r = kleinster_kreis(konvexe_huelle([(p.x, p.y) for p in punkte]))
    bb = form.BoundBox
    return x, y, r + seite, bb.ZMin - unten, bb.ZLength + oben + unten


def _vernetzt(form):
    """(Punkte, Dreiecke) der Form mit TESSELLIERUNG – an einer Kopie: tessellate am Original
    hängt das feine Netz an das Teil, und wer es danach gröber vernetzt (Zugang, Voxel), bekäme
    dieses statt seines eigenen – je nachdem, was davor lief, ein anderes Ergebnis (wie die drei
    Simultan-Tests nach P-2026-10-17-22, P-2026-10-18-68)."""
    return form.copy(False, False).tessellate(TESSELLIERUNG)


def _punkte(form):
    """Punkte des Teils für Umriss und Länge: die Tessellierung mit Ecken und Kanten – für den
    Umriss reicht das. Ein Körper aus einem STL hat sie schon (stl_teil.netz_fuer): genau, ohne
    68.242 Flächen zu vernetzen (2,4 s beim Anklicken, P-2026-10-11-100)."""
    from . import stl_teil

    aus_stl = stl_teil.netz_fuer(form)
    if aus_stl is not None:
        return [FreeCAD.Vector(*q) for q in aus_stl[0]]
    punkte, _dreiecke = _vernetzt(form)
    return list(punkte) + [ecke.Point for ecke in form.Vertexes]


def _vermesse_rund(form, flaeche, rund, nahe, umgedreht):
    """vermesse() für eine runde Fläche mit der Achse `rund` (Punkt, Richtung)."""
    auf_der_achse, achse = rund
    punkte, _dreiecke = _vernetzt(form)
    punkte = list(punkte) + [ecke.Point for ecke in form.Vertexes]
    t = [(p - auf_der_achse).dot(achse) for p in punkte]
    bezug = FreeCAD.Vector(nahe) if nahe is not None else flaeche.CenterOfMass
    vorne_plus = (bezug - auf_der_achse).dot(achse) >= (min(t) + max(t)) / 2
    normale = achse if vorne_plus != bool(umgedreht) else achse * -1
    u, v = _quer(normale)
    hoehe = max(p.dot(normale) for p in punkte)  # das vordere Ende des Teils
    laengs = [p.dot(normale) - hoehe for p in punkte]
    huelle = konvexe_huelle([(p.dot(u), p.dot(v)) for p in punkte])
    mitte_flaeche = (auf_der_achse.dot(u), auf_der_achse.dot(v))
    x, y, r = kleinster_kreis(huelle)
    weitester = max(math.hypot(p[0] - mitte_flaeche[0], p[1] - mitte_flaeche[1]) for p in huelle)
    eigene, _ = _vernetzt(flaeche)
    radius = max(
        ((p - auf_der_achse) - normale * (p - auf_der_achse).dot(normale)).Length
        for p in list(eigene) + [ecke.Point for ecke in flaeche.Vertexes]
    )
    return Vermessung(
        normale=normale,
        quer=(u, v),
        hoehe=hoehe,
        kreis=(auf_der_achse + normale * (hoehe - auf_der_achse.dot(normale)), radius),
        mitte_flaeche=mitte_flaeche,
        mitte_teil=(x, y),
        noetig={MITTE_FLAECHE: 2 * weitester, MITTE_TEIL: 2 * r},
        vorne=max(laengs),
        hinten=min(laengs),
        rund=True,
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
    """So viel bleibt rundum mindestens stehen (mm); negativ: das Teil passt nicht. Reste der
    Rechnung (das Teil braucht 40,00000000000001) zählen nicht: genau so groß passt (Manuel,
    2026-10-05: Scheibe Ø 40 in der Stange Ø 40 – „passt nicht“)."""
    rest = (durchmesser - lage_.durchmesser) / 2
    return 0.0 if abs(rest) < GENAU else rest


def vorschlag_durchmesser(noetig, zoll=False):
    """Vorschlag für den Stangen-Ø in mm: der nächste 5-mm-Schritt (in Zoll 1/8"), der
    rundum mindestens MIN_AUFMASS lässt."""
    stufe = STUFE_ZOLL if zoll else STUFE_MM
    return math.ceil((noetig + 2 * MIN_AUFMASS) / stufe - 1e-9) * stufe


def stangenlaenge(vermessung, stange):
    """Länge der Stange: Planaufmaß, Teil, Lücke (Stange.luecke) und Spannlänge."""
    return ausspannlaenge(vermessung, stange) + stange.spannlaenge


def ausspannlaenge(vermessung, stange):
    """So weit ragt die Stange aus dem Futter: Planaufmaß, Teil und Lücke."""
    return stange.planaufmass + vermessung.laenge + stange.luecke


def stangen_placement(vermessung, stange, achse):
    """Die Lage des Zylinders im Job. CAM baut ihn ab seinem Ursprung entlang +Z – hier
    gedreht auf die Stangenachse, mit dem Ursprung hinter der Spannlänge."""
    laengs = laengs_von(achse)
    hinten = vermessung.hinten - stange.luecke - stange.spannlaenge
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
    _merke(job, EIGENSCHAFT_SPANNLAENGE, stange.spannlaenge, tr("va.eigenschaft.spannlaenge"))
    _merke(job, EIGENSCHAFT_ABSTECHBREITE, stange.abstechbreite, tr("va.eigenschaft.abstechbreite"))
    dokument.recompute()
    return job


def auf_achse_umstellen(job, achse):
    """Legt das Teil eines Jobs des Assistenten für eine andere Rundachse `achse`
    (vierachs_achsen.Stangenachse) neu in die Stange – Lage und Rohteil wie richte_ein, mit
    derselben Stirnfläche, Mitte, Drehlage und Stange –, und die 4-Achs-Operationen des Jobs
    bekommen die Achse (vierachs_operation.setze_achse). Keine eigene Transaktion. ValueError mit
    einem Satz, wenn der Job nicht so aussieht, wie der Assistent ihn anlegt.

    Manuel (2026-10-12): den Job ohne Maschine angelegt (die Stange längs X, A), die CLX550
    danach geladen – „Auf der Maschine prüfen“ legte die Stange quer auf den Tisch und ließ beide
    Operationen aus („Die Maschine hat diese Rundachsen nicht: A“)."""
    from . import vierachs_operation as vo

    e = einstellung(job)
    if e is None:
        raise ValueError(tr("vr.umstellen.fehler"))
    neu = lage(e.vermessung, achse, e.mitte, e.drehlage, e.stange.durchmesser)
    richte_ein(job.Document, e.teil, neu, e.stange, achse, job=job)
    for op in job.Operations.Group:
        if vo.ist_rundum(op) and "Rundachse" in op.PropertiesList:
            vo.setze_achse(op, achse)
    job.Document.recompute()


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
    umgedreht: bool = False  # eine runde Fläche (V2b): mit „Umdrehen“ vermessen


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
    aus_netz = _ebenen_aus_netz(form, platz, laengs)
    if aus_netz:  # ein Körper aus einem STL: über sein Netz, nicht Fläche für Fläche
        flaeche, umgedreht = aus_netz
        vermessung = vermesse(form, form.getElement(flaeche), None, umgedreht)
    elif aus_netz is False:  # aus einem STL, ohne passende ebene Fläche: eine Achse des Teils
        gefunden = _teilachse_laengs(form, platz, laengs)
        if gefunden is None:
            return None
        flaeche, vermessung, umgedreht = gefunden
    elif (flaeche := _stirnflaeche(form, platz, laengs)) is not None:
        umgedreht = False
        vermessung = vermesse(form, form.getElement(flaeche))
    else:  # ein Drehteil ohne ebene Stirnfläche vorne (V2b): die runde Fläche längs
        gefunden = (
            _runde_laengs(form, platz, laengs)
            or _ebene_am_futter(form, platz, laengs)
            or _teilachse_laengs(form, platz, laengs)
        )
        if gefunden is None:
            return None
        flaeche, vermessung, umgedreht = gefunden
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
    luecke = round(vermessung.hinten - a_hinten - spann, 6)
    if mitte is None or planaufmass < -GENAU or luecke < -GENAU:
        return None
    # Ohne gemerkte Abstechbreite (Jobs bis 0.26) ist die ganze Lücke die Abstechbreite.
    abstechbreite = float(getattr(job, EIGENSCHAFT_ABSTECHBREITE, luecke))
    stange = Stange(
        round(2 * float(rohteil.Radius), 6),
        round(max(0.0, planaufmass), 6),
        round(max(0.0, min(abstechbreite, luecke)), 6),
        spann,
        luecke if luecke > abstechbreite + GENAU else 0.0,
    )
    return Einstellung(teil, flaeche, vermessung, laengs, mitte, drehlage, stange, umgedreht)


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


def _ebenen_aus_netz(form, platz, laengs):
    """(„FaceN“, umgedreht) für einen Körper aus einem STL – die ebene Fläche am Futter
    (Außennormale gegen die Stange, am hinteren Ende), sonst die vorne (längs, bei a = 0) –,
    gefunden in seinem Netz (stl_teil.netz_fuer) und nur ihr Name von OpenCascade: am Geist 0,1
    statt 17 s Fläche für Fläche. None, wenn es kein solcher Körper ist; False, wenn keine passt."""
    import numpy as np
    import Part

    from . import stl_teil

    aus_stl = stl_teil.netz_fuer(form)
    if aus_stl is None:
        return None
    punkte, dreiecke = aus_stl
    matrix = np.array(platz.toMatrix().A, dtype=float).reshape(4, 4)
    im_job = punkte @ matrix[:3, :3].T + matrix[:3, 3]
    l_ = np.array(tuple(laengs), dtype=float)
    a = im_job @ l_
    p0, p1, p2 = (im_job[dreiecke[:, k]] for k in range(3))
    normalen = np.cross(p1 - p0, p2 - p0)
    laenge = np.linalg.norm(normalen, axis=1)
    quer = np.where(laenge > 1e-12, (normalen @ l_) / np.maximum(laenge, 1e-300), 0.0)
    mitte = (p0 + p1 + p2) @ l_ / 3.0
    toleranz = max(1e-6 * max(1.0, form.BoundBox.DiagonalLength), TESSELLIERUNG)
    for umgedreht, richtung, wo in ((True, -1.0, float(a.min())), (False, 1.0, 0.0)):
        passend = np.flatnonzero((np.abs(quer - richtung) < 1e-6) & (np.abs(mitte - wo) < toleranz))
        for k in passend[:3]:
            ecken = [FreeCAD.Vector(*punkte[i]) for i in dreiecke[k]]
            dreieck = Part.Face(Part.makePolygon([*ecken, ecken[0]]))
            gefunden = form.findSubShapesWithSharedVertex(
                dreieck, needName=True, checkGeometry=False
            )
            if gefunden:
                return gefunden[0][0], umgedreht
    return False


def _teilachse_laengs(form, platz, laengs):
    """(„X“/„Y“/„Z“, Vermessung, umgedreht), wenn nach `platz` eine Achse des Teils längs der
    Stange liegt (vermesse_achse) – oder None."""
    im_teil = platz.Rotation.inverted().multVec(laengs)
    for achse, richtung in TEILACHSEN.items():
        anteil = im_teil.dot(FreeCAD.Vector(*richtung))
        if abs(abs(anteil) - 1) < 1e-9:
            return achse, vermesse_achse(form, achse, anteil < 0), anteil < 0
    return None


def _ebene_am_futter(form, platz, laengs):
    """(„FaceN“, Vermessung, True) der ebenen Fläche, die nach `platz` hinten am Futter liegt –
    Außennormale gegen die Stange, am hinteren Ende des Teils („Umdrehen“ an einer ebenen
    Fläche) –, oder None."""
    punkte, _dreiecke = _vernetzt(form)
    hinten = min(platz.multVec(p).dot(laengs) for p in punkte)
    toleranz = 1e-6 * max(1.0, form.BoundBox.DiagonalLength)
    for nummer, flaeche in enumerate(form.Faces, start=1):
        if not ist_eben(flaeche):
            continue
        normale = platz.Rotation.multVec(aussennormale(flaeche))
        if (normale + laengs).Length < 1e-6 and abs(
            platz.multVec(flaeche.CenterOfMass).dot(laengs) - hinten
        ) < max(toleranz, TESSELLIERUNG):
            return f"Face{nummer}", vermesse(form, flaeche, None, True), True
    return None


def _runde_laengs(form, platz, laengs):
    """(„FaceN“, Vermessung, umgedreht) der ersten runden Fläche, deren Achse nach `platz` längs
    der Stange liegt und vermessen nach vorne zeigt – oder None."""
    for nummer, flaeche in enumerate(form.Faces, start=1):
        rund = achse_der_runden(flaeche)
        if rund is None or abs(abs(platz.Rotation.multVec(rund[1]).dot(laengs)) - 1) > 1e-6:
            continue
        for umgedreht in (False, True):
            vermessung = vermesse(form, flaeche, None, umgedreht)
            if (platz.Rotation.multVec(vermessung.normale) - laengs).Length < 1e-6:
                return f"Face{nummer}", vermessung, umgedreht
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


def abstechbreite(job):
    """Die Abstechbreite des Jobs (mm) – ohne gemerkte die Vorgabe."""
    return float(getattr(job, EIGENSCHAFT_ABSTECHBREITE, ABSTECHBREITE) or ABSTECHBREITE)


def spannlaenge(job):
    """Wie tief die Stange eines Jobs aus dem Assistenten im Futter steckt (mm), sonst 0."""
    return float(getattr(job, EIGENSCHAFT_SPANNLAENGE, 0.0) or 0.0)


def _merke(job, eigenschaft, wert, text):
    """Merkt `wert` (mm) am Job in der ausgeblendeten Eigenschaft `eigenschaft`."""
    if eigenschaft not in job.PropertiesList:
        job.addProperty("App::PropertyFloat", eigenschaft, "CAM-Addon", text)
        job.setEditorMode(eigenschaft, 2)  # ausgeblendet – das Addon nutzt sie
    if getattr(job, eigenschaft) != float(wert):
        setattr(job, eigenschaft, float(wert))
