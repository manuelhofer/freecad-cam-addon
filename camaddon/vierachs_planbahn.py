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
  (nut_bahn: in voller Breite mit der Zickzack-Rampe, sonst in Bögen, zuletzt die Wand
  rundum) – gerechnet im Rahmen der Fläche (x längs, z ihre Normale, y = z × x), zurück mit
  a = x, Höhe = z, Versatz = −y und der Rundachse fest. Mit Zeilen kam der Fräser nicht an die
  Enden (4 mm blieben stehen) und mit dem Fräser so breit wie die Nut gar nicht hinein.

- **Querbohrung** (P-2026-10-02-07): Eine gewählte Bohrung quer zur Stange (eine ganze
  Zylinderfläche, ihre Achse rechtwinklig zur Stange, das Material außen – bohrungen()) fräst
  die Bahn „Bohrung fräsen“ des Quaders (bohrung_bahn: in der Helix hinab, Ringe, die Wand
  rundum) im Rahmen der Bohrung – die Rundachse auf ihre Öffnung, die Spitze längs ihrer Achse,
  quer versetzt mit dem Y, wenn sie nicht durch die Mitte geht. Eine durchgehende von beiden
  Seiten je bis zur Mitte der Stange.
- **Radial bohren** (P-2026-10-02-08): Mit einem Bohrer (Planwerte.bohrer) werden die
  Querbohrungen gebohrt statt gefräst (gebohrt_punkte(): wie „Bohren“ im Quader, tiefer als
  3 × D in Hüben) – mit seinem Durchmesser, eine Sackbohrung nur mit seiner Spitze unten; eine
  durchgehende von beiden Seiten, jede Seite mit der Spitze über die Mitte hinaus (so hat sie
  überall den vollen Durchmesser, und X muss nur um die Länge der Spitze unter null).
- **Nut auf dem Mantel** (P-2026-10-02-09): Ist die gewählte Fläche der Grund einer Nut um die
  Stange (ein Zylinder um die Achse über einen Teil des Umfangs, abgewickelt ein Rechteck –
  mantelnuten()), dreht die Rundachse: in der Mitte in voller Breite eine Zickzack-Rampe wie die
  Vollnut, ist die Nut breiter, Zeilen zu beiden Seiten bis an die Wände (_mantelnut_punkte).
  „Rundum schruppen“ kam mit dem Fräser in Nutbreite gar nicht hinein.

Gerechnet wird in (a, Höhe, Winkel, Versatz) wie vierachs_bahn.Punkt – die Höhe längs der
Werkzeugachse, der Winkel der der Rundachse, der Versatz quer. Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import einheiten
from . import fraeserform as ff
from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_huelle as vh
from .sprache import tr

GERADE = 1e-6  # so wenig darf eine Normale längs der Stange zeigen
LUFT = vb.RING_LUFT  # mm – so weit bleibt eine Zeile vom Rand der Fläche weg (wie der Ring)
UEBERLAUF_LAENGS = vb.UEBERLAUF_ZUGABE  # mm – so weit über Fläche und Fräser hinaus längs
TOLERANZ = vb.TOLERANZ_SCHLICHTEN  # mm – so fein wird das Teil vernetzt: Wände genau
VORSCHAU_TOLERANZ = 0.05  # mm – für die Vorschau im Assistenten
SEHNE = 0.005  # mm – so weit weicht eine Sehne höchstens vom Bogen der Nut ab
NUT_AE_ANTEIL = 0.25  # × D: höchstens dieses ae für die Bögen in der Nut
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
    # (Durchmesser, Spitzenwinkel) eines Bohrers: Die Querbohrungen werden radial gebohrt statt
    # gefräst (gebohrt()), ebene Flächen nicht; None: ein Fräser mit ebener Stirn.
    bohrer: tuple = None
    # Im Gleichlauf für M3 (spindel.fuer_m3): Nut, Bohrung und die Wände der Mantelnut; False –
    # andersherum (M4). P-2026-10-02-23
    gleichlauf: bool = True
    # Die Zeilen auf ebenen Flächen nur im Gleichlauf: jede von vorne zum Futter, danach abheben
    # und von vorne (P-2026-10-02-24); sonst hin und her.
    nur_gleichlauf: bool = False


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
    bohrungen: int = 0  # so viele Bohrungen quer – eine durchgehende einmal, von beiden Seiten
    huebe: int = 0  # mit dem Bohrer: so oft fährt er hinab, über alle Seiten
    seiten: int = 0  # mit dem Bohrer: von so vielen Seiten gebohrt
    mantelnuten: int = 0  # so viele Flächen davon als Nut auf dem Mantel (Rundachse dreht)


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


@dataclass(frozen=True)
class Kegelgrund:
    """Der Grund einer gebohrten Sackbohrung: die Spitze des Bohrers, ein Kegel – im Rahmen
    ihrer Ebene (a längs, q quer, die Höhe längs der Normale)."""

    a: float  # die Achse der Bohrung, längs
    q: float  # … und quer
    spitze: float  # die Höhe der Spitze
    radius: float  # der Radius der Bohrung
    laenge: float  # so lang ist die Spitze: oben hat sie den Radius


@dataclass(frozen=True)
class Mantelnut:
    """Eine Nut auf dem Mantel (W-006 4.3.4): ihr Grund ein Zylinder um die Stangenachse über
    einen Teil des Umfangs, in der Abwicklung ein Rechteck – längs von a_von bis a_bis, rundum
    von phi_von bis phi_bis (Grad, phi_von < phi_bis); an den Enden Wände in Ebenen durch die
    Achse, längs Wände quer zu ihr (eine Nut, mit Revolution oder Nut in PartDesign gemacht)."""

    name: str
    radius: float  # der Grund
    a_von: float
    a_bis: float
    phi_von: float
    phi_bis: float


def mantelnuten(form, laengs, radial, namen, toleranz=VORSCHAU_TOLERANZ):
    """[Mantelnut] – die Flächen `namen` von `form`, die der Grund einer Nut auf dem Mantel
    sind: ein Zylinder um die Stangenachse, das Material innen (die Normale zeigt von der Achse
    weg), über weniger als den ganzen Umfang, der Rand in der Abwicklung ein Rechteck. Andere
    zählen nicht (der ganze Umfang ist Sache von „Rundum schruppen“)."""
    import Part

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
        mitte = np.array(tuple(zylinder.Center), dtype=float)
        if abs(abs(float(d @ l_)) - 1.0) > 1e-6 or np.linalg.norm(mitte - l_ * (mitte @ l_)) > 1e-4:
            continue  # nicht um die Stangenachse
        radius = float(zylinder.Radius)
        u0, u1, v0, v1 = flaeche.ParameterRange
        p = np.array(tuple(flaeche.valueAt((u0 + u1) / 2, (v0 + v1) / 2)), dtype=float)
        n = np.array(tuple(flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)), dtype=float)
        aussen = p - l_ * (p @ l_)
        if float(n @ aussen) <= 0:
            continue  # das Material außen: eine Bohrung längs, kein Nutgrund
        phi_m = math.atan2(float(p @ v_), float(p @ u_))
        rand = []
        for kante in flaeche.Edges:
            rand.extend(kante.discretize(Deflection=toleranz))
        if not rand:
            continue
        q = np.array([[pt.x, pt.y, pt.z] for pt in rand], dtype=float)
        a = q @ l_
        phi = np.angle(np.exp(1j * (np.arctan2(q @ v_, q @ u_) - phi_m)))
        a_von, a_bis = float(a.min()), float(a.max())
        f_von, f_bis = float(phi.min()), float(phi.max())
        if f_bis - f_von > math.radians(359.0) or a_bis - a_von < 1e-3:
            continue  # rundum
        eng = 2 * toleranz
        am_rand = (
            (np.abs(a - a_von) < eng)
            | (np.abs(a - a_bis) < eng)
            | (np.abs(phi - f_von) * radius < eng)
            | (np.abs(phi - f_bis) * radius < eng)
        )
        if not am_rand.all():
            continue  # in der Abwicklung kein Rechteck
        ergebnis.append(
            Mantelnut(
                f"Face{nummer + 1}",
                radius,
                a_von,
                a_bis,
                math.degrees(phi_m + f_von),
                math.degrees(phi_m + f_bis),
            )
        )
    return ergebnis


def _mantelnut_punkte(nut, w, oben, sicher):
    """([vierachs_bahn.Punkt], Lagen, Fahrten) – die Nut auf dem Mantel: Die Rundachse dreht,
    der Fräser fährt längs der Nut rundum. Erst in der Mitte in voller Breite eine Zickzack-Rampe
    hinab wie die Vollnut im Quader (nut_bahn._vollnut: je Fahrt höchstens ap / 2, der Vorschub
    so viel kleiner, dass der Span so dick ist wie beim Einsatz mit ae), unten einmal hinüber;
    ist die Nut breiter, dann Zeilen zu beiden Seiten in voller Tiefe, höchstens ae auseinander,
    bis an die Wände. An den Enden bleibt die Stirn – am Grund am breitesten – vor den Wänden
    durch die Achse. ValueError mit einem Satz, wenn der Fräser nicht hineinpasst."""
    from . import nut_bahn as nb

    radius = float(w.form.radius)
    breite = nut.a_bis - nut.a_von
    breit_text = einheiten.text(breite, einheiten.LAENGE)
    if 2 * radius > breite + 2 * NUT_LUFT + bh_gleich():
        fraeser = einheiten.text(2 * radius, einheiten.LAENGE)
        raise ValueError(tr("vp.fehler.mantel_breit", fraeser=fraeser, breite=breit_text))
    halb = math.degrees(math.asin(min(1.0, (radius + NUT_LUFT) / nut.radius)))
    f_von, f_bis = nut.phi_von + halb, nut.phi_bis - halb
    if f_bis < f_von:
        raise ValueError(tr("vp.fehler.mantel_kurz", breite=breit_text))
    a_mitte = (nut.a_von + nut.a_bis) / 2
    frei = max(breite / 2 - radius - NUT_LUFT, 0.0)
    zeilen = []
    if frei > vb.GLEICH:
        anzahl = max(1, int(math.ceil(frei / max(w.zeilenabstand, vb.GLEICH) - 1e-9)))
        for k in range(1, anzahl + 1):
            zeilen.extend((a_mitte + frei * k / anzahl, a_mitte - frei * k / anzahl))
    z_ende = nut.radius + w.aufmass
    ap = w.zustellung if w.zustellung > vb.GLEICH else 2 * radius
    ap = min(ap, nb.VOLLNUT_AP * 2 * radius)
    laenge = nut.radius * math.radians(max(f_bis - f_von, 0.0))
    stufe = min(laenge * math.tan(math.radians(max(w.eintauchwinkel, 0.1))), ap / 2)
    stufe = max(stufe, nb.MIN_RAMPE)
    k = min(max(w.zeilenabstand, vb.GLEICH) / (2 * radius), 0.5)
    anteil = 2 * math.sqrt(k * (1 - k))
    punkte = [
        vb.Punkt(True, a_mitte, sicher, f_von),
        vb.Punkt(True, a_mitte, oben + w.sicherheit, f_von),
        vb.Punkt(False, a_mitte, oben, f_von, True),  # bis ans Material, in der Luft
    ]
    z, dort, fahrten = oben, f_von, 0
    while z > z_ende + vb.GLEICH:
        z = max(z - stufe, z_ende)
        dort = f_bis if dort == f_von else f_von
        punkte.append(vb.Punkt(False, a_mitte, z, dort, anteil=anteil))
        fahrten += 1
    dort = f_bis if dort == f_von else f_von
    punkte.append(vb.Punkt(False, a_mitte, z_ende, dort, anteil=anteil))
    fahrten += 1

    # Die Zeilen an den Wänden im Gleichlauf (P-2026-10-02-23): Liegt das Material längs vorn
    # (+), muss die Rundachse für M3 mit fallendem φ fahren, hinten mit steigendem – je Paar
    # zuerst die Zeile, die dort beginnt, wo der Fräser steht; zurück die andere.
    def steigt(seite):
        return sp.ist_gleichlauf((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, seite)) == bool(
            w.gleichlauf
        )

    for paar in range(0, len(zeilen), 2):
        reihe = [(a, 1.0 if a > a_mitte else -1.0) for a in zeilen[paar : paar + 2]]
        reihe.sort(key=lambda zeile: steigt(zeile[1]) != (dort == f_von))
        for a, seite in reihe:
            anfang, ende = (f_von, f_bis) if steigt(seite) else (f_bis, f_von)
            if dort != anfang:  # am Ende der Nut quer hinüber (in ihr)
                punkte.append(vb.Punkt(False, punkte[-1].a, z_ende, anfang))
            punkte.append(vb.Punkt(False, a, z_ende, anfang))
            punkte.append(vb.Punkt(False, a, z_ende, ende))
            dort = ende
            fahrten += 1
    punkte.append(vb.Punkt(True, punkte[-1].a, sicher, dort))
    lagen = max(1, int(math.ceil((oben - z_ende) / ap - 1e-9)))
    return punkte, lagen, fahrten


def _mantel_ueber(w, nut, radius):
    """So hoch steht über der Nut noch Material: die Stange – oder nach dem Schruppen der Rest
    über ihr und so weit daneben, wie der Fräser reicht."""
    if w.rest is None:
        return float(w.stange_radius)
    rest_a, rest_phi, rest_r = w.rest
    laengs = (rest_a >= nut.a_von - radius) & (rest_a <= nut.a_bis + radius)
    mitte = math.radians((nut.phi_von + nut.phi_bis) / 2)
    weit = math.radians((nut.phi_bis - nut.phi_von) / 2) + radius / nut.radius
    quer = np.abs(np.angle(np.exp(1j * (rest_phi - mitte)))) <= weit
    if not laengs.any() or not quer.any():
        return float(w.stange_radius)
    return min(float(w.stange_radius), float(np.max(rest_r[np.ix_(laengs, quer)])))


def bh_gleich():
    """So genau muss der Fräser zur Breite der Nut passen (mm) – wie der Bohrer zur Bohrung."""
    from . import bohren as bh

    return bh.GLEICH_D


def boden_der_bohrung(laengs, radial, ebene, bohrung, bohrer=None, durch=False):
    """(Ebene, Part.Face): der Grund der Bohrung als Kreisscheibe im Job – für den Vergleich auf
    der Stange (restmaterial.boden_radien). Mit `bohrer` ((Durchmesser, Spitzenwinkel), radial
    gebohrt) ist der Grund einer Sackbohrung die Spitze des Bohrers: (Ebene, Kegelgrund); eine
    durchgehende (`durch`) behält die Scheibe in der Mitte."""
    import FreeCAD
    import Part

    if bohrer is not None and not durch:
        from . import bohren as bh

        lang = bh.spitze(*bohrer)
        x, y = bohrung.mitte
        return ebene, Kegelgrund(x, -y, bohrung.z_unten - lang, bohrung.radius, lang)
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
        gleichlauf=w.gleichlauf,
    )
    bahn = bb.planen(werte, [_bohrung_eingeengt(bohrung, radius)])
    return _zurueck(bahn.punkte, ebene), bahn


def _bohrung_eingeengt(bohrung, radius):
    """Die Bohrung um NUT_LUFT enger, wo sie breiter ist als der Fräser – wie bei der Nut."""
    import dataclasses

    enger = min(NUT_LUFT, max(bohrung.radius - radius, 0.0))
    return dataclasses.replace(bohrung, radius=bohrung.radius - enger)


def bohrer_passt(paare, bohrer):
    """Bohrt der Bohrer `bohrer` ((Durchmesser, Spitzenwinkel)) alle Querbohrungen `paare`
    ([(Ebene, Bohrung)], bohrungen()) – mit seinem Durchmesser, eine Sackbohrung mit seiner
    Spitze unten? So prüft auch gebohrt_punkte(); False ohne Bohrung."""
    from . import bohren as bh

    if not paare or not bohrer:
        return False
    durchmesser, winkel = bohrer
    seiten = {}
    for ebene, _b in paare:
        seiten[ebene.name] = seiten.get(ebene.name, 0) + 1
    for ebene, b in paare:
        if abs(2 * b.radius - durchmesser) > bh.GLEICH_D:
            return False
        if seiten[ebene.name] < 2 and (b.spitze <= 0 or abs(b.spitze - winkel) > bh.GLEICH_WINKEL):
            return False
    return True


def gebohrt_punkte(bohrung, ebene, w, oben, sicher, durch):
    """([vierachs_bahn.Punkt], Hübe, tiefste Spitze) – die Bohrung radial mit dem Bohrer
    `w.bohrer` gebohrt, im Rahmen ihrer Ebene wie „Bohren“ (bohren.planen): über der Bohrung auf
    die Ebene R knapp über dem Material, im Vorschub hinab – tiefer als 3 × D in Hüben von 1 × D,
    je Hub zurück auf R und im Eilgang bis knapp über den Grund davor –, zuletzt auf die sichere
    Höhe. Die Spitze geht um ihre Länge unter den Grund der Wand: bis dort hat die Bohrung den
    vollen Durchmesser. `durch`: die Seite einer durchgehenden (bis zur Mitte; bohrungen()) –
    sonst eine Sackbohrung, die unten die Spitze des Bohrers haben muss. ValueError mit einem
    Satz, wenn der Bohrer nicht passt."""
    from . import bahn as bn
    from . import bohren as bh

    durchmesser, winkel = w.bohrer
    soll = einheiten.text(2 * bohrung.radius, einheiten.LAENGE)
    if abs(2 * bohrung.radius - durchmesser) > bh.GLEICH_D:
        bohrer = einheiten.text(durchmesser, einheiten.LAENGE)
        raise ValueError(tr("bh.fehler.durchmesser", bohrer=bohrer, durchmesser=soll))
    if not durch and bohrung.spitze <= 0:
        raise ValueError(tr("vp.fehler.sack", durchmesser=soll))
    if not durch and abs(bohrung.spitze - winkel) > bh.GLEICH_WINKEL:
        raise ValueError(
            tr(
                "bh.fehler.spitze",
                durchmesser=soll,
                spitze=f"{bohrung.spitze:.0f}",
                winkel=f"{winkel:.0f}",
            )
        )
    unten = bohrung.z_unten - bh.spitze(durchmesser, winkel)
    r_ebene = min(oben + w.sicherheit, sicher)
    hub = bh.hub_fuer(oben - unten, durchmesser)
    x, y = bohrung.mitte
    punkte = [bn.Punkt(True, x, y, sicher), bn.Punkt(True, x, y, r_ebene)]
    tiefe = r_ebene
    huebe = 0
    while tiefe > unten + 1e-9:
        if hub > 0 and tiefe < r_ebene - 1e-9:
            punkte.append(bn.Punkt(True, x, y, min(r_ebene, tiefe + bh.ABSTAND_HUB)))
        ziel = max(unten, tiefe - hub) if hub > 0 else unten
        punkte.append(bn.Punkt(False, x, y, ziel, True))
        huebe += 1
        tiefe = ziel
        if hub > 0 and tiefe > unten + 1e-9:
            punkte.append(bn.Punkt(True, x, y, r_ebene))
    punkte.append(bn.Punkt(True, x, y, sicher))
    return _zurueck(punkte, ebene), huebe, unten


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
    oder in Bögen – eine zu schmale auch (sie sagt es); eine zu breite (eine Abflachung
    zwischen zwei Wänden) fährt Zeilen."""
    from . import nut_bahn as nb

    return [n for n in liste if nb.verfahren(n, radius, offen_breit=False) != "zu_breit"]


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
    (nut_bahn.planen: in voller Breite die Zickzack-Rampe, sonst in Bögen, zuletzt die Wand
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
        gleichlauf=w.gleichlauf,
    )
    bahn = nb.planen(werte, [_eingeengt(n, radius) for n in liste])
    return _zurueck(bahn.punkte, ebene), bahn


def planen(
    netz,
    laengs,
    radial,
    werte,
    flaechen,
    schritt_a=vh.SCHRITT_A,
    nuten_=None,
    bohrungen_=(),
    mantelnuten_=(),
):
    """Die Bahn „Plan indexiert“ (Planbahn) über die Flächen `flaechen` ([Ebene], ebenen())
    mit den Werten `werte`; `netz` ist das Teil ohne diese Flächen (netz_ohne()), `laengs` und
    `radial` wie in vierachs_huelle; `nuten_` ({Name: [nut_bahn.Nut]}, nuten()): diese Flächen
    als Nut; `bohrungen_` ([(Ebene, Bohrung)], bohrungen()): Querbohrungen; `mantelnuten_`
    ([Mantelnut], mantelnuten()): Nuten auf dem Mantel. ValueError mit einem Satz, wenn es nicht
    geht."""
    w = werte
    form = w.form
    radius = form.radius
    if w.bohrer is not None:
        flaechen = []  # ein Bohrer fräst keine Fläche
        mantelnuten_ = ()
        if not bohrungen_:
            raise ValueError(tr("vp.fehler.keine_bohrung"))
        r_eben = radius
    else:
        r_eben = ebener_radius(form)
        if r_eben <= 0:
            raise ValueError(tr("vp.fehler.form"))
        if w.zustellung <= 0 or w.zeilenabstand <= 0:
            raise ValueError(tr("vp.fehler.werte"))
        if w.zeilenabstand > 2 * r_eben:
            raise ValueError(tr("vp.fehler.zeilenabstand"))
    if not flaechen and not bohrungen_ and not mantelnuten_:
        raise ValueError(tr("vp.fehler.keine_ebene"))
    teil_vorne, teil_hinten = _enden(
        netz, laengs, radial, list(flaechen) + [e for e, _b in bohrungen_] + list(mantelnuten_)
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
    seiten = {}
    for ebene, _b in bohrungen_:
        seiten[ebene.name] = seiten.get(ebene.name, 0) + 1
    huebe = seiten_gebohrt = 0
    for ebene, bohrung in sorted(bohrungen_, key=lambda eb: eb[0].phi):
        oben = _material_ueber(w, ebene, radius)
        if oben <= bohrung.z_unten + vb.GLEICH:
            continue  # steht nichts mehr drüber
        if w.bohrer is not None:
            # von beiden Seiten: eine durchgehende – jede Seite bis über die Mitte
            stueck, hub_zahl, z_min = gebohrt_punkte(
                bohrung, ebene, w, oben, sicher, seiten[ebene.name] > 1
            )
            huebe += hub_zahl
            seiten_gebohrt += 1
        else:
            stueck, bohrbahn = _bohrung_punkte(bohrung, ebene, w, oben, sicher)
            lagen_gesamt += bohrbahn.lagen
            zeilen_gesamt += max(1, int(math.ceil(bohrbahn.umlaeufe)))
            z_min = bohrbahn.z_min
        punkte.extend(stueck)
        letzter = punkte[-1]
        punkte.append(vb.Punkt(True, letzter.a, sicher, ebene.phi, q=letzter.q))
        if ebene.name not in gebohrt:
            flaechen_gefraest += 1
            bohrungen_gefraest += 1
        gebohrt.add(ebene.name)
        r_min = min(r_min, z_min)
    mantel_gefraest = 0
    for nut in sorted(mantelnuten_, key=lambda n: n.phi_von):
        oben = _mantel_ueber(w, nut, radius)
        if oben <= nut.radius + w.aufmass + vb.GLEICH:
            continue  # steht nichts mehr drüber
        stueck, lagen, fahrten = _mantelnut_punkte(nut, w, oben, sicher)
        punkte.extend(stueck)
        flaechen_gefraest += 1
        mantel_gefraest += 1
        lagen_gesamt += lagen
        zeilen_gesamt += fahrten
        r_min = min(r_min, nut.radius + w.aufmass)
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
            zeilen_gesamt += nut.boegen + nut.vollnut
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
        # Zwischen weit auseinanderliegenden Zeilen auch dazwischen prüfen – der Schritt quer am
        # Ende einer Zeile prüfte sonst nur die beiden Zeilen (P-2026-10-02-30).
        zw_q, zw_von = vb._zwischen(q_zeilen, radius)
        if len(zw_q):
            roh_zw = vh.je_versatz(
                netz, laengs, radial, geformt, rad, a_von, schritt, anzahl, zw_q
            ).T
        else:
            roh_zw = np.zeros((0, anzahl))
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
            erlaubt_zw = (roh_zw + zugabe <= lage + vb.GLEICH) & (
                ~ragt[None, :] | (roh_zw <= ziel + vb.GLEICH)
            )
            zwischen = np.ones((max(len(q_zeilen) - 1, 0), anzahl), dtype=bool)
            for k, m in enumerate(zw_von):
                zwischen[m] &= erlaubt_zw[k]
            if w.nur_gleichlauf:
                # Jede Zeile von vorne zum Futter (fallendes a, beginnt vor der Stange in der
                # Luft); die Zeilen quer in der Folge, in der das Material dafür auf der Seite
                # des Gleichlaufs liegt – im Rahmen der Fläche: a = x, q = −y, zum Fräser z.
                aufsteigend = sp.ist_gleichlauf(
                    (0.0, 0.0, -1.0), (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0)
                ) == bool(w.gleichlauf)
                fahrten = vb._einzeln(mit_luecke, False, absteigend=not aufsteigend)
            else:
                fahrten = vb._geteilt(vb._fahrten(mit_luecke), zwischen)
            for fahrt in fahrten:
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
        huebe,
        seiten_gebohrt,
        mantel_gefraest,
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
