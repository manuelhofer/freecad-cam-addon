# SPDX-License-Identifier: LGPL-2.1-or-later
"""2,5D, die Bahn „Ringnut fräsen“ (Spezifikation Strategien 13.8, „Hinter der Kante“): eine Nut
in einer Bohrung – Sicherungsring (DIN 472), O-Ring, Freistich –, die von oben überdeckt ist.
Kein Schaftfräser erreicht sie; in der Werkstatt fräst man sie mit einem Scheiben- oder
T-Nutenfräser (werkzeuge.NUTENFRAESER): mittig in der Bohrung im Eilgang auf Nuthöhe, auf einem
Halbkreis tangential an die Wand, ein voller Kreis auf Tiefe, auf einem Halbkreis zurück zur Mitte,
mittig heraus. Anlass: das Lagerschild einer Pumpe mit der Sicherungsringnut Ø 65,1 × 2,13 breit,
1,55 tief in der Lagerbohrung Ø 62 – bis 0.371 blieb sie im Assistenten unbearbeitet.

- **Erkennen** (ringnuten()): eine senkrechte Zylinderfläche mit Material außen (die Wand einer
  Bohrung), ganz herum – auch aus mehreren Teilflächen (ein STEP teilt Zylinder in zwei Hälften;
  fehlt Wand, muss dort Luft sein: eine Querbohrung) –, deren Radius R größer ist als der kleinste
  Radius r_zugang der Bohrungsabschnitte über ihr bis zur Oberkante (dort öffnet sich die Bohrung
  nach oben). Darunter eine kleinere Bohrung (durch oder mit Boden) oder ein Boden (Hinterstich am
  Grund) – nach unten offen ist sie eine Senkung von unten, keine Ringnut. Ragt zwischen Nut und
  Oberkante innerhalb der Abschnitte etwas hinein, das nicht rund um die Achse ist (ein Steg, eine
  Nase), oder ist die Bohrung oben zu, ist die Nut nicht erreichbar – mit Grund (Ringnut.grund).
- **Werkzeug** (werkzeug_pruefen, waehlen): Die Scheibe muss mittig durch die Bohrung passen, der
  Hals darf am Rand nicht anstoßen, wenn die Scheibe auf R steht, die Scheibe nicht breiter sein
  als die Nut, und was dicker ist als der Hals (Schaft, Halter), bleibt über der Oberkante –
  nachgerechnet mit dem Profil des Werkzeugs im Schnitt r–z (pruefe_lage). Von mehreren der größte Ø.
- **Bahn** (planen): je Nut ihre Höhen (ist sie breiter als die Scheibe, mehrere, die sich
  überlappen – von oben nach unten), je Höhe radiale Stufen bis knapp vor R und ein Kreis auf Maß;
  Gleichlauf (Spindel M3: das Material rechts, in der Bohrung gegen den Uhrzeigersinn, G3) wie
  bohrung_bahn. Vollkreise wie dort in Vierteln (G2/G3 mit I, J). Mittig hinab im Eilgang nur mit
  Materialstand und 1 mm Luft, bis 2 mm über die Nut (_hinab). Der Vorschub der Mitte ist um
  e ÷ (e + D/2) kleiner (Innenkreis: an der Schneide gilt der Vorschub des Einsatzes).
- **Eigene Prüfung** (pruefen): Alle Höhenfeld-Prüfer des Addons sehen das Teil von oben und kennen
  keinen Überhang – eine Scheibe unter dem Rand gilt dort als „im Teil“. Darum rechnet die Ringnut
  selbst nach, im Schnitt r–z um die Achse der Bohrung: an jedem Punkt der Bahn jedes Stück des
  Werkzeugs gegen die Abschnitte der Bohrung (und über der Oberkante gegen das, was dort steht).

Nicht Teil dieser Strategie (spätere Erweiterung): Außennuten an Wellen und Zapfen, T-Nuten an
geraden Wänden, Rückwärtssenken (nach unten offene Erweiterungen einer Bohrung).

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import math
from collections import OrderedDict
from dataclasses import dataclass, field, replace

from . import bahn as bn
from . import bohrung_bahn as bb
from . import einheiten
from . import vierachs_bahn as vb
from .sprache import tr

GLEICH = 1e-6
ACHSE_GLEICH = 1e-4  # mm – so nah liegen zwei Achsen, die als dieselbe gelten
RADIUS_GLEICH = (
    1e-4  # mm – so nah gelten zwei Radien als gleich (eine Nut ist mindestens 0,01 tief)
)
# mm je Seite: so viel Luft bleibt zwischen Werkzeug und Bohrung, wo es nicht schneidet – beim
# Einfahren mittig und am Hals, wenn die Scheibe auf R steht. Die Bohrung ist fertig gefräst (sie
# kommt vorher), 0,3 mm decken ihr Toleranzfeld und das Rundlaufen eines langen, dünnen Halses.
SPIEL = 0.3
SPIEL_OBEN = 0.5  # mm – so weit über dem, was über der Oberkante steht, bleibt der Schaft
# mm – so viel Luft rundum braucht der Eilgang mittig hinab, sonst Vorschub: wie der Warnabstand
# von „Kollision prüfen“ (kollision.WARNABSTAND, test_ringnut vergleicht beide).
EILGANG_LUFT = 1.0
STUFE_ANTEIL = 0.1  # ae je radialer Stufe höchstens 0,1 · Scheiben-Ø (ohne brauchbaren Einsatz)
# mm radial – so viel bleibt vor dem letzten Kreis stehen: Sicherungsringnuten sind toleriert
# (DIN 472, d2 H12/H13), der Kreis auf Maß schneidet mit kleinem, gleichem Eingriff.
SCHLICHT_REST = 0.1
UEBERLAPP_ANTEIL = 0.2  # zwei Höhen in einer breiten Nut überlappen um so viel der Scheibenbreite
# mm – so viel dürfen sich zwei Stücke senkrecht überdecken, ohne dass es zählt (die Scheibe
# genau so breit wie die Nut liegt mit ihrer Oberseite an der Kante darüber)
UEBERDECKT = 1e-3
BREITE_GLEICH = 1e-4  # mm – so viel breiter als die Nut darf die Scheibe sein (Rundung)
NASE_TOLERANZ = 0.01  # mm – so weit innen beginnt die Suche nach etwas, das hineinragt
NASE_VOLUMEN = 1e-3  # mm³ – so viel Material im Querschnitt der Bohrung ist eine Nase
# Übliche Scheiben-Ø für den Vorschlag (Scheibenfräser DIN 885, T-Nuten- und Keilnutfräser).
DURCHMESSER_REIHE = (6, 8, 10, 12, 13, 16, 19, 20, 22, 25, 28, 32, 40, 50, 63, 80, 100)
SCHAFT_REIHE = (6, 8, 10, 12, 16, 20, 25, 32, 40)
VORSCHLAG_HALS_ANTEIL = 0.5  # Hals höchstens so dick (von D) – steif, aber mit Luft am Rand
VORSCHLAG_HALS_RESERVE = 2.0  # mm – so viel länger als nötig ist der vorgeschlagene Hals

DURCH, BODEN, GRUND, BOHRUNG = "durch", "boden", "grund", "bohrung"
SCHEIBE, HALS, SCHAFT, HALTER = "scheibe", "hals", "schaft", "halter"


@dataclass(frozen=True)
class Wand:
    """Die Wand einer Bohrung: eine senkrechte Zylinderfläche (oder mehrere Teilflächen) mit
    Material außen, ganz herum."""

    namen: tuple  # die Flächen („Face15“, …)
    mitte: tuple  # (x, y) der Achse
    radius: float
    z_unten: float
    z_oben: float
    # Ganz herum – sonst unterbricht etwas die Wand (eine Nase, ein Schlitz): Über einer Nut gehört
    # sie trotzdem zur Bohrung, die Nase findet _versperrt; eine Nut selbst ist nur ganz eine.
    ganz: bool = True


@dataclass(frozen=True)
class Ringnut:
    """Eine Ringnut in einer Bohrung, von oben überdeckt."""

    name: str  # die (erste) Zylinderfläche der Nut
    zylinder: tuple  # alle Zylinderflächen der Nut (ein STEP teilt sie)
    ringe: tuple  # die ebenen Ringflächen oben und unten (und der Boden am Grund)
    mitte: tuple
    radius: float  # R
    z_unten: float
    z_oben: float
    r_zugang: float  # der kleinste Radius über ihr bis zur Oberkante
    z_kante: float  # die Oberkante: dort öffnet sich die Bohrung nach oben
    # (z_unten, z_oben, Radius) der Bohrung, frei um die Achse, von unten nach oben – die Nut
    # selbst mit R; unter dem untersten: Radius 0 (ein Boden) oder unendlich (durchgehend).
    profil: tuple
    unten: str  # DURCH, BODEN (eine Bohrung mit Boden darunter), GRUND (die Nut am Grund), BOHRUNG
    z_boden: float  # der Boden darunter; −inf, wenn durchgehend
    r_innen: float  # so weit steht die Bohrung auf Nuthöhe vor dem Fräsen (Radius darüber)
    grund: str = ""  # warum sie nicht erreichbar ist – leer: erreichbar

    @property
    def breite(self):
        return self.z_oben - self.z_unten

    @property
    def tiefe(self):
        """Radial, von der engsten Stelle über ihr bis R."""
        return self.radius - self.r_zugang

    @property
    def frei_unter(self):
        """So weit ist unter der Nut frei (bis zum Boden; unendlich, wenn durchgehend)."""
        return self.z_unten - self.z_boden

    @property
    def flaechen(self):
        """Alle Flächen der Nut – die mit der Operation fertig sind."""
        return tuple(self.zylinder) + tuple(self.ringe)

    def text(self):
        """„Ø 65 × 2,15, 1,5 tief“ – die Zeile im Assistenten."""
        return tr(
            "rn.nut.text",
            d=einheiten.text(2 * self.radius, einheiten.LAENGE),
            breite=einheiten.text(self.breite, einheiten.LAENGE),
            tiefe=einheiten.text(self.tiefe, einheiten.LAENGE),
        )


# --- Die Wände der Bohrungen, je Form gemerkt ---------------------------------------------------

_WAENDE = OrderedDict()  # hashCode → (Form, [Wand]) – die Form festgehalten (wie bohrung_bahn)
_NUTEN = OrderedDict()  # hashCode → (Form, [Ringnut] mit gesperrten)
FORMEN_GEMERKT = 8


def _gemerkt(speicher, form, rechnen):
    try:
        kennung = form.hashCode()
    except Exception:  # noqa: BLE001 – keine Form, die sich merken lässt
        return rechnen()
    eintrag = speicher.get(kennung)
    if eintrag is not None and eintrag[0].isSame(form):
        speicher.move_to_end(kennung)
        return eintrag[1]
    ergebnis = rechnen()
    speicher[kennung] = (form, ergebnis)
    while len(speicher) > FORMEN_GEMERKT:
        speicher.popitem(last=False)
    return ergebnis


def waende(form):
    """[Wand] – die Wände aller senkrechten Bohrungen der Form, Teilflächen zusammengefasst."""
    return _gemerkt(_WAENDE, form, lambda: _waende(form))


def _waende(form):
    import FreeCAD
    import Part

    stuecke = []  # [(Name, Mitte, Radius, z_unten, z_oben, Winkel)]
    for nummer, flaeche in enumerate(form.Faces):
        flaeche_ = flaeche.Surface
        if not isinstance(flaeche_, Part.Cylinder):
            continue
        achse = flaeche_.Axis
        if abs(abs(achse.z) - 1.0) > 1e-6:
            continue
        u0, u1, v0, v1 = flaeche.ParameterRange
        mitte = flaeche_.Center
        punkt = flaeche.valueAt((u0 + u1) / 2, (v0 + v1) / 2)
        normale = flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        zur_achse = FreeCAD.Vector(mitte.x - punkt.x, mitte.y - punkt.y, 0)
        if normale.x * zur_achse.x + normale.y * zur_achse.y <= 0:
            continue  # ein Zapfen, keine Bohrung
        bbox = flaeche.BoundBox
        stuecke.append(
            (
                f"Face{nummer + 1}",
                (float(mitte.x), float(mitte.y)),
                float(flaeche_.Radius),
                float(bbox.ZMin),
                float(bbox.ZMax),
                float(u1 - u0),
            )
        )
    gruppen = []  # [[Namen, Mitte, Radius, z_unten, z_oben, Winkel]]
    for name, mitte, radius, z0, z1, winkel in stuecke:
        for g in gruppen:
            if (
                abs(g[1][0] - mitte[0]) < ACHSE_GLEICH
                and abs(g[1][1] - mitte[1]) < ACHSE_GLEICH
                and abs(g[2] - radius) < RADIUS_GLEICH
                and abs(g[3] - z0) < 1e-6
                and abs(g[4] - z1) < 1e-6
            ):
                g[0].append(name)
                g[5] += winkel
                break
        else:
            gruppen.append([[name], mitte, radius, z0, z1, winkel])
    # Ganz herum auch aus zwei Hälften eines STEP.
    return [Wand(tuple(g[0]), g[1], g[2], g[3], g[4], g[5] >= 2 * math.pi - 1e-6) for g in gruppen]


def _koaxial(a, b):
    return (
        abs(a.mitte[0] - b.mitte[0]) < ACHSE_GLEICH and abs(a.mitte[1] - b.mitte[1]) < ACHSE_GLEICH
    )


def _nut_der_wand(form, mitte, radius, z_oben):
    probe = Wand((), (float(mitte[0]), float(mitte[1])), float(radius), 0.0, float(z_oben))
    return next(
        (
            n
            for n in alle_ringnuten(form)
            if _koaxial(n, probe)
            and abs(n.radius - radius) < RADIUS_GLEICH
            and abs(n.z_oben - z_oben) < 1e-6
        ),
        None,
    )


def unter_dem_rand(form, mitte, radius, z_oben):
    """Ist die Bohrungswand (Achse `mitte`, `radius`, Oberkante `z_oben`) die Wand einer Ringnut
    (alle_ringnuten, auch einer gesperrten)? Dann kommt kein Werkzeug von oben längs der Achse an
    sie heran – bohrung_bahn.bohrungen nimmt sie nicht. Eine Senkung von unten (darunter offen)
    ist keine Ringnut: Sie bleibt eine Bohrung wie bis 0.371."""
    return _nut_der_wand(form, mitte, radius, z_oben) is not None


def grund_unter(form, mitte, radius, z_unten):
    """Der Boden (z) einer Ringnut am Grund (GRUND), die direkt unter der Bohrungswand (Achse
    `mitte`, `radius`, Unterkante `z_unten`) liegt – sonst None. „Bohrung fräsen“ fräst diese Wand
    dann als Sackbohrung bis auf ihn: Sonst bliebe der Kern innerhalb der Bohrung zwischen Boden
    und Wand stehen, den keine Strategie mehr nimmt (Freistich Ø 24 × 2 am Grund einer Ø 20)."""
    probe = Wand((), (float(mitte[0]), float(mitte[1])), float(radius), 0.0, 0.0)
    for n in alle_ringnuten(form):
        if (
            n.unten == GRUND
            and _koaxial(n, probe)
            and abs(n.z_oben - z_unten) < 1e-6
            and abs(n.r_innen - radius) < RADIUS_GLEICH
        ):
            return n.z_boden
    return None


# --- Erkennen -----------------------------------------------------------------------------------


def waende_ueber(form, nut):
    """Die Namen der Bohrungswände über der Nut bis zur Oberkante – durch sie kommt die Scheibe.
    Für die Frage ohne Materialstand, ob eine Operation davor sie gefräst hat (ringnut.rechne)."""
    namen = []
    for wand in waende(form):
        gleich = (
            abs(wand.mitte[0] - nut.mitte[0]) < ACHSE_GLEICH
            and abs(wand.mitte[1] - nut.mitte[1]) < ACHSE_GLEICH
        )
        if gleich and wand.z_unten >= nut.z_oben - 1e-6 and wand.z_oben <= nut.z_kante + 1e-6:
            namen.extend(wand.namen)
    return tuple(namen)


def alle_ringnuten(form):
    """[Ringnut] – alle Ringnuten der Form, auch die nicht erreichbaren (Ringnut.grund)."""
    return _gemerkt(_NUTEN, form, lambda: _ringnuten(form))


def ringnuten(form, namen=None):
    """[Ringnut] – die erreichbaren Ringnuten der Form; mit `namen` nur die, zu denen eine dieser
    Flächen gehört (eine Zylinder- oder eine ihrer Ringflächen)."""
    gesucht = set(namen) if namen is not None else None
    return [
        n
        for n in alle_ringnuten(form)
        if not n.grund and (gesucht is None or gesucht & set(n.flaechen))
    ]


def ringnut_von(form, name):
    """Die Ringnut (auch eine gesperrte), zu der die Fläche `name` gehört – oder None."""
    return next((n for n in alle_ringnuten(form) if name in n.flaechen), None)


def ist_ringnut_flaeche(form, name):
    """Gehört die Fläche `name` zu einer Ringnut (auch einer, die nicht erreichbar ist)? Solche
    Flächen nimmt keine Strategie von oben – sie lägen unter dem Rand."""
    try:
        return ringnut_von(form, name) is not None
    except Exception:  # noqa: BLE001 – keine Form mit Flächen
        return False


def _ringnuten(form):
    alle = waende(form)
    ergebnis = []
    for wand in alle:
        nut = _als_nut(form, wand, [w for w in alle if w is not wand and _koaxial(w, wand)])
        if nut is not None:
            ergebnis.append(nut)
    return ergebnis


def _als_nut(form, wand, achse):
    # Hinauf: die Abschnitte über der Wand, einer auf den anderen, bis zur Oberkante.
    oben = []
    z = wand.z_oben
    while True:
        weiter = [w for w in achse if abs(w.z_unten - z) < 1e-6 and w not in oben]
        if not weiter:
            break
        naechste = min(weiter, key=lambda w: w.radius)
        oben.append(naechste)
        z = naechste.z_oben
    if not oben:
        return None
    r_zugang = min(w.radius for w in oben)
    if r_zugang >= wand.radius - RADIUS_GLEICH:
        return None  # über ihr ist es nirgends enger: eine Bohrung, die man von oben fräst
    if not wand.ganz and not _kanal_frei(form, wand, oben[0].radius):
        # Nicht ganz herum und im Ring der Nut steht Material (ein Steg): keine Ringnut. Fehlt
        # nur Wand, wo Luft ist (eine Querbohrung, eine Passfedernut kreuzt sie), ist sie eine.
        return None
    z_kante = z
    # Hinab: die Abschnitte darunter, bis zum Boden oder durch.
    unten_liste = []
    z = wand.z_unten
    while True:
        weiter = [w for w in achse if abs(w.z_oben - z) < 1e-6 and w not in unten_liste]
        if not weiter:
            break
        naechste = min(weiter, key=lambda w: w.radius)
        unten_liste.append(naechste)
        z = naechste.z_unten
    if unten_liste and unten_liste[0].radius >= wand.radius - RADIUS_GLEICH:
        return None  # darunter ist es nicht enger: eine Stufe einer Bohrung von unten
    if not unten_liste and not _material_unter(form, wand.mitte, wand.radius, wand.z_unten):
        # Nach unten offen, die Wand endet an einer Außenfläche: eine Senkung oder ein Lagersitz
        # von unten (rückwärts senken – spätere Erweiterung), keine Ringnut. Die Fläche bleibt
        # „unerreichbar“, wie bis 0.371: Umspannen fräst sie von unten.
        return None
    if unten_liste:
        letzte = unten_liste[-1]
        boden = bb._boden_unter(form, _vektor(letzte.mitte), letzte.radius, letzte.z_unten)
        art = BOHRUNG
        z_boden = letzte.z_unten if boden else -math.inf
        unter = 0.0 if boden else math.inf
    else:
        boden = _material_unter(form, wand.mitte, wand.radius, wand.z_unten)
        art = GRUND if boden else DURCH
        z_boden = wand.z_unten if boden else -math.inf
        unter = 0.0 if boden else math.inf
    if art == BOHRUNG and z_boden == -math.inf:
        art_text = DURCH
    elif art == BOHRUNG:
        art_text = BODEN
    else:
        art_text = art
    profil = [(-math.inf, (unten_liste[-1].z_unten if unten_liste else wand.z_unten), unter)]
    for w in reversed(unten_liste):
        profil.append((w.z_unten, w.z_oben, w.radius))
    profil.append((wand.z_unten, wand.z_oben, wand.radius))
    for w in oben:
        profil.append((w.z_unten, w.z_oben, w.radius))
    nut = Ringnut(
        name=wand.namen[0],
        zylinder=tuple(wand.namen),
        ringe=_ringflaechen(form, wand),
        mitte=wand.mitte,
        radius=wand.radius,
        z_unten=wand.z_unten,
        z_oben=wand.z_oben,
        r_zugang=r_zugang,
        z_kante=z_kante,
        profil=tuple(profil),
        unten=art_text,
        z_boden=z_boden,
        r_innen=oben[0].radius,
    )
    grund = _versperrt(form, nut)
    return replace(nut, grund=grund) if grund else nut


def _vektor(mitte, z=0.0):
    import FreeCAD

    return FreeCAD.Vector(float(mitte[0]), float(mitte[1]), float(z))


def _material_unter(form, mitte, radius, z):
    """Steht knapp unter z innerhalb des Radius Material – rundum und auf der Achse geprüft (die
    Nut am Grund einer Sackbohrung: darunter der Boden)?"""
    import FreeCAD

    for anteil in (0.0, 0.5, 0.95):
        r = anteil * radius
        for i in range(8 if r > 0 else 1):
            w = i * math.pi / 4
            punkt = FreeCAD.Vector(mitte[0] + r * math.cos(w), mitte[1] + r * math.sin(w), z - 0.05)
            if form.isInside(punkt, 1e-6, True):
                return True
    return False


def _kanal_frei(form, wand, r_innen):
    """Ist der Ring der Nut – zwischen der Bohrung darüber (`r_innen`) und R, über die Breite der
    Nut – frei von Material? Für eine Wand, die nicht ganz herum geht (eine Querbohrung Ø 6 teilt
    die Wand der Nut Ø 24 in zwei Stücke zu je 2,67 rad)."""
    import Part

    hoehe = wand.z_oben - wand.z_unten - 2 * NASE_TOLERANZ
    if hoehe <= 0 or wand.radius - NASE_TOLERANZ <= r_innen:
        return False
    unten = _vektor(wand.mitte, wand.z_unten + NASE_TOLERANZ)
    ring = Part.makeCylinder(wand.radius - NASE_TOLERANZ, hoehe, unten).cut(
        Part.makeCylinder(max(r_innen - NASE_TOLERANZ, 0.01), hoehe, unten)
    )
    return _gemeinsam(form, ring) <= NASE_VOLUMEN


def _ringflaechen(form, wand):
    """Die ebenen Flächen an den Kreiskanten oben und unten an der Wand (die Ringflächen der Nut
    und, am Grund, ihr Boden) – nur, was ganz im Kreis R um die Achse liegt: nie eine Außenfläche
    des Teils (sie wäre mit der Operation sonst „fertig“)."""
    import Part

    alle = form.Faces
    namen = []
    for name in wand.namen:
        flaeche = alle[int(name[4:]) - 1]
        for kante in flaeche.Edges:
            kb = kante.BoundBox
            if kb.ZMax - kb.ZMin > 1e-6:
                continue  # eine Naht, keine Kreiskante oben oder unten
            for nachbar in form.ancestorsOfType(kante, Part.Face):
                if not isinstance(nachbar.Surface, Part.Plane):
                    continue
                bb_ = nachbar.BoundBox
                rand = wand.radius + 1e-3
                if (
                    bb_.XMin < wand.mitte[0] - rand
                    or bb_.XMax > wand.mitte[0] + rand
                    or bb_.YMin < wand.mitte[1] - rand
                    or bb_.YMax > wand.mitte[1] + rand
                ):
                    continue
                for k, f in enumerate(alle):
                    if f.isSame(nachbar):
                        neu = f"Face{k + 1}"
                        if neu not in namen:
                            namen.append(neu)
                        break
    return tuple(namen)


def _versperrt(form, nut):
    """Warum die Nut nicht erreichbar ist – oben zu, oder etwas ragt hinein, das nicht rund um die
    Achse ist; "" sonst."""
    import Part

    z_max = form.BoundBox.ZMax
    r_oben = nut.profil[-1][2]
    if z_max > nut.z_kante + 1e-6:
        hoehe = z_max + 1.0 - nut.z_kante
        zylinder = Part.makeCylinder(
            max(r_oben - NASE_TOLERANZ, 0.01), hoehe, _vektor(nut.mitte, nut.z_kante + 1e-3)
        )
        if _gemeinsam(form, zylinder) > NASE_VOLUMEN:
            return tr("rn.grund.oben_zu")
    for z0, z1, r in nut.profil[1:]:
        if z1 - z0 <= 2 * NASE_TOLERANZ:
            continue
        zylinder = Part.makeCylinder(
            r - NASE_TOLERANZ, z1 - z0 - 2 * NASE_TOLERANZ, _vektor(nut.mitte, z0 + NASE_TOLERANZ)
        )
        if z0 < nut.z_unten - GLEICH:
            continue  # unter der Nut fährt nichts hin
        if _gemeinsam(form, zylinder) > NASE_VOLUMEN:
            return tr("rn.grund.nase", z=einheiten.text(0.5 * (z0 + z1), einheiten.LAENGE))
    return ""


def _gemeinsam(form, koerper):
    try:
        return float(form.common(koerper).Volume)
    except Exception:  # noqa: BLE001 – OpenCascade: lieber versperrt als ins Teil
        return math.inf


# --- Über der Oberkante ---------------------------------------------------------------------------

_UEBER = OrderedDict()  # (hashCode, Achse, z_kante, ρ) → z
UEBER_GEMERKT = 4096


def ueber_der_kante(form, nut):
    """Eine Funktion ρ → z: so hoch steht über der Oberkante der Nut höchstens Material innerhalb
    des Radius ρ um ihre Achse (die Oberkante selbst, wenn dort nichts steht). Je ρ (auf 0,01 mm) einmal
    mit OpenCascade gerechnet und gemerkt."""
    import Part

    if form is None:
        return lambda _rho: nut.z_kante
    z_max = form.BoundBox.ZMax
    try:
        kennung = form.hashCode()
    except Exception:  # noqa: BLE001
        kennung = id(form)

    def hoehe(rho):
        rho = math.ceil(max(rho, 0.01) * 100.0) / 100.0
        schluessel = (kennung, nut.mitte, round(nut.z_kante, 6), rho)
        if schluessel in _UEBER and _UEBER[schluessel][0].isSame(form):
            return _UEBER[schluessel][1]
        if z_max <= nut.z_kante + 1e-6:
            z = nut.z_kante
        else:
            zylinder = Part.makeCylinder(
                rho, z_max + 1.0 - nut.z_kante, _vektor(nut.mitte, nut.z_kante + 1e-3)
            )
            try:
                schnitt = form.common(zylinder)
                z = float(schnitt.BoundBox.ZMax) if schnitt.Volume > NASE_VOLUMEN else nut.z_kante
            except Exception:  # noqa: BLE001
                z = z_max
            z = max(z, nut.z_kante)
        _UEBER[schluessel] = (form, z)
        while len(_UEBER) > UEBER_GEMERKT:
            _UEBER.popitem(last=False)
        return z

    return hoehe


# --- Das Werkzeug im Schnitt r–z ------------------------------------------------------------------


@dataclass(frozen=True)
class Stueck:
    """Ein Stück des Werkzeugs: von z_von bis z_bis über der Unterkante der Scheibe, Radius."""

    art: str
    z_von: float
    z_bis: float
    radius: float


def _eingetragen(werkzeug, feld):
    """Das Maß, wie es eingetragen ist – 0, wenn nicht (keine Schätzung, werkzeuge.mass)."""
    from . import werkzeuge as wz

    if not wz.hat_feld(werkzeug, feld):
        return 0.0
    return float(getattr(werkzeug, feld, 0.0) or 0.0)


def _hals_fehlt(werkzeug):
    """Fehlt die Halslänge eines Fräsers, dessen Hals dünner sein kann als der Schaft? Dann rechnet
    die Ringnut ohne Hals (der Schaft direkt über der Scheibe) – und sagt es im Grund."""
    hals_d, schaft = _eingetragen(werkzeug, "hals_d"), _eingetragen(werkzeug, "schaft")
    if _eingetragen(werkzeug, "hals_laenge") > 0:
        return False
    return hals_d <= 0 or schaft <= 0 or hals_d < schaft - GLEICH


def mass_fehlt(nut, werkzeug, halter=None, laenge=0.0, ueber=()):
    """Scheitert der Nutenfräser an der Nut nur, weil ein Maß nicht eingetragen ist (die Breite
    der Scheibe, die Halslänge)? Dann der Satz dazu, sonst "" – für den Knopf, der das Werkzeug
    öffnet, statt ein zweites vorzuschlagen."""
    from . import werkzeuge as wz

    if werkzeug is None or werkzeug.art != wz.NUTENFRAESER or werkzeug.durchmesser <= 0:
        return ""
    grund = werkzeug_pruefen(nut, werkzeug, halter, laenge, ueber)
    fehlt = _eingetragen(werkzeug, "schneidenbreite") <= 0 or (
        _hals_fehlt(werkzeug) and grund == tr("rn.grund.hals_fehlt", art=_stueck_text(SCHAFT))
    )
    fehlt = fehlt or (
        _hals_fehlt(werkzeug) and grund == tr("rn.grund.hals_fehlt", art=_stueck_text(HALTER))
    )
    return grund if grund and fehlt else ""


def profil(werkzeug, halter=None, laenge=0.0):
    """[Stueck] des Nutenfräsers (werkzeuge.Werkzeug) von der Scheibe nach oben: Scheibe, Hals,
    Schaft – mit einem geraden Halter (halter.Halter) und der Länge ab Spindelnase `laenge` auch
    der Halter, je Abschnitt ein Zylinder mit dem größeren Ø. Nur eingetragene Maße, nichts
    geschätzt (werkzeuge.mass schätzt den Hals 0,3 · D × 0,25 · D): Ein Keyway aus FreeCAD mit Hals
    Ø 6 × 3 und Schaft Ø 16 hieß mit der Schätzung (4,75 lang) passend, der Schaft lag 1 mm im Rand
    (Zweifler 14.11.). Ohne Halslänge kein Hals – der Schaft gleich über der Scheibe; ohne Hals-Ø
    so dick wie der Schaft; ohne Schaft-Ø so dick wie die Scheibe. Die Breite der Scheibe ohne
    Eintrag geschätzt – werkzeug_pruefen lehnt sie dann ab."""
    from . import werkzeuge as wz

    d = float(werkzeug.durchmesser)
    b = _eingetragen(werkzeug, "schneidenbreite") or float(wz.mass(werkzeug, "schneidenbreite"))
    schaft = _eingetragen(werkzeug, "schaft") or d
    hals_d = _eingetragen(werkzeug, "hals_d") or schaft
    hals_l = _eingetragen(werkzeug, "hals_laenge")
    stuecke = [Stueck(SCHEIBE, 0.0, b, d / 2)]
    oben = b
    if hals_l > 0:
        stuecke.append(Stueck(HALS, oben, oben + hals_l, hals_d / 2))
        oben += hals_l
    gerade = halter is not None and not halter.gewinkelt and laenge > 0
    ende = laenge - halter.laenge if gerade else max(float(wz.laenge_fuer_cam(werkzeug)), oben)
    if ende > oben + GLEICH:
        stuecke.append(Stueck(SCHAFT, oben, ende, schaft / 2))
    if gerade:
        z = 0.0
        for abschnitt in halter.abschnitte:
            if abschnitt.laenge <= 0:
                continue
            r = max(abschnitt.d_oben, abschnitt.d_unten) / 2
            stuecke.append(Stueck(HALTER, laenge - z - abschnitt.laenge, laenge - z, r))
            z += abschnitt.laenge
    return stuecke


@dataclass
class Befund:
    """Das Engste an einer Stelle: wie viel Luft bleibt (negativ: es stößt an)."""

    reserve: float  # mm – radial in der Bohrung, senkrecht über der Oberkante
    art: str = ""  # welches Stück
    oben: bool = False  # über der Oberkante (dort zählt die Höhe)
    z: float = 0.0  # wo


def pruefe_lage(nut, stuecke, e, zb, ueber=None, absenken=False):
    """Befund für das Werkzeug mit der Unterkante der Scheibe auf `zb`, die Achse `e` neben der
    Achse der Bohrung – das Engste über alle Stücke: in der Bohrung e + r ≤ Radius − SPIEL (die
    Scheibe in der Nut ohne Spiel, sie schneidet dort), über der Oberkante über dem, was dort
    innerhalb von e + r steht (`ueber`, ueber_der_kante), um SPIEL_OBEN. `absenken`: das Werkzeug
    kam mittig von oben hierher – jedes Stück auch gegen alle Abschnitte über ihm."""
    hoehe = ueber or (lambda _rho: nut.z_kante)
    schlimmste = Befund(math.inf)
    for s in stuecke:
        a, b = zb + s.z_von, zb + s.z_bis
        for z0, z1, r_b in nut.profil:
            unten = max(a, z0)
            oben_ = min(b, z1, nut.z_kante)
            if absenken:
                if z1 <= a + GLEICH:
                    continue
            elif oben_ - unten <= UEBERDECKT:
                continue
            in_der_nut = abs(z0 - nut.z_unten) < GLEICH and abs(z1 - nut.z_oben) < GLEICH
            noetig = 0.0 if (s.art == SCHEIBE and in_der_nut) else SPIEL
            reserve = r_b - (e + s.radius) - noetig
            if reserve < schlimmste.reserve:
                schlimmste = Befund(reserve, s.art, False, max(unten, z0))
        if b > nut.z_kante + UEBERDECKT:
            unten = max(a, nut.z_kante)
            reserve = unten - (hoehe(e + s.radius) + SPIEL_OBEN)
            if hoehe(e + s.radius) <= nut.z_kante + GLEICH:
                reserve = math.inf  # über der Oberkante steht nichts
            if reserve < schlimmste.reserve:
                schlimmste = Befund(reserve, s.art, True, unten)
    return schlimmste


def hoehen(nut, b):
    """Die Höhen der Scheibenunterkante in der Nut, von oben nach unten: eine, wenn die Scheibe so
    breit ist wie die Nut; sonst so viele, dass sich zwei um UEBERLAPP_ANTEIL der Breite überlappen.
    Von oben: Jede weitere Höhe schneidet nur noch unten und am Umfang, die Späne fallen in die
    Bohrung darunter."""
    w = nut.breite
    if b >= w - BREITE_GLEICH:
        return [nut.z_unten]
    schritt = b * (1.0 - UEBERLAPP_ANTEIL)
    anzahl = int(math.ceil((w - b) / schritt - 1e-9)) + 1
    return [nut.z_oben - b - (w - b) * i / (anzahl - 1) for i in range(anzahl)]


# --- Passt das Werkzeug? --------------------------------------------------------------------------


def werkzeug_pruefen(nut, werkzeug, halter=None, laenge=0.0, ueber=None):
    """ "" wenn der Nutenfräser `werkzeug` die Nut fräsen kann – sonst ein Satz, warum nicht (zu
    groß für die Bohrung, Hals zu dick, Scheibe zu breit, Hals zu kurz …)."""
    from . import werkzeuge as wz

    if werkzeug is None or werkzeug.art != wz.NUTENFRAESER or werkzeug.durchmesser <= 0:
        return tr("rn.grund.art")
    if _eingetragen(werkzeug, "schneidenbreite") <= 0:
        # Geschätzt (0,1 · D) wäre die Scheibe vielleicht breiter als die Nut – sie schnitte in
        # die fertigen Ringflächen.
        return tr("rn.grund.breite_fehlt")
    stuecke = profil(werkzeug, halter, laenge)
    d = stuecke[0].radius * 2
    b = stuecke[0].z_bis
    if b > nut.breite + BREITE_GLEICH:
        return tr("rn.grund.zu_breit", b=_mm(b), breite=_mm(nut.breite))
    if d / 2 > nut.r_zugang - SPIEL + GLEICH:
        return tr("rn.grund.zu_gross", d=_mm(d), bohrung=_mm(2 * nut.r_zugang))
    e = nut.radius - d / 2
    lagen = hoehen(nut, b)
    unten = pruefe_lage(nut, stuecke, 0.0, min(lagen), ueber, absenken=True)
    if unten.reserve < -GLEICH:
        return _grund_aus(unten, stuecke, nut, werkzeug)
    for zb in lagen:
        befund = pruefe_lage(nut, stuecke, e, zb, ueber)
        if befund.reserve < -GLEICH:
            return _grund_aus(befund, stuecke, nut, werkzeug)
    return ""


def _grund_aus(befund, stuecke, nut, werkzeug=None):
    hals = next((s for s in stuecke if s.art == HALS), None)
    if befund.art in (SCHAFT, HALTER) and werkzeug is not None and _hals_fehlt(werkzeug):
        return tr("rn.grund.hals_fehlt", art=_stueck_text(befund.art))
    if befund.art == SCHEIBE:
        return tr("rn.grund.zu_gross", d=_mm(2 * stuecke[0].radius), bohrung=_mm(2 * nut.r_zugang))
    if befund.art == HALS and not befund.oben:
        return tr("rn.grund.hals_dick", hals=_mm(2 * hals.radius), tiefe=_mm(nut.tiefe))
    if befund.art == HALS:
        return tr("rn.grund.oben_im_weg", z=_mm(befund.z))
    lang = hals.z_bis - hals.z_von if hals is not None else 0.0
    return tr("rn.grund.hals_kurz", lang=_mm(lang), art=_stueck_text(befund.art))


def _stueck_text(art):
    """„der Schaft“ – das Stück in einem Satz (die Schlüssel wörtlich, für die Sprachprüfung)."""
    return {
        SCHEIBE: tr("rn.stueck.scheibe"),
        HALS: tr("rn.stueck.hals"),
        SCHAFT: tr("rn.stueck.schaft"),
        HALTER: tr("rn.stueck.halter"),
    }.get(art, art)


def _mm(wert):
    return einheiten.text(wert, einheiten.LAENGE)


def waehlen(nuten, werkzeuge, halter_von=None, ueber_von=None):
    """(Werkzeug oder None, {Kennung: Grund}) – von den Nutenfräsern `werkzeuge` der, der die
    meisten Nuten `nuten` fräsen kann, bei gleich vielen der größte Ø (steifer, weniger Versatz).
    `halter_von(werkzeug)`: (Halter, Länge ab Spindelnase) oder (None, 0); `ueber_von(nut)`:
    ueber_der_kante. Der Grund je Werkzeug für die erste Nut, die es nicht kann."""
    gruende = {}
    beste, rang = None, None
    for w in werkzeuge:
        halter, laenge = halter_von(w) if halter_von is not None else (None, 0.0)
        anzahl = 0
        for nut in nuten:
            grund = werkzeug_pruefen(nut, w, halter, laenge, ueber_von(nut) if ueber_von else None)
            if grund:
                gruende.setdefault(w.kennung, grund)
            else:
                anzahl += 1
        if anzahl == 0:
            continue
        hals = float(w.hals_d or 0.0)
        wert = (anzahl, float(w.durchmesser), hals)
        if rang is None or wert > rang:
            beste, rang = w, wert
    return beste, gruende


# --- Womit es ginge (kein passendes Werkzeug) ----------------------------------------------------


@dataclass
class Grenzen:
    """Womit die Nuten gingen: Scheibe höchstens d, höchstens b breit; für eine Scheibe Ø
    `fuer_d` mit Schaft Ø `schaft` der Hals höchstens hals_d dick und mindestens hals_laenge lang
    – beides hängt an diesen Ø (Zweifler 14.11.: 14,4 galt für Ø 19, nicht für die genannten
    19,4; die 9 mm nur für den Schaft Ø 10)."""

    d: float
    b: float
    hals_d: float
    hals_laenge: float
    fuer_d: float = 0.0
    schaft: float = 0.0

    def text(self):
        return tr(
            "rn.fehlt",
            d=_mm(self.d),
            b=_mm(self.b),
            fuer=_mm(self.fuer_d or self.d),
            hals=_mm(self.hals_d),
            lang=_mm(self.hals_laenge),
            schaft=_mm(self.schaft),
        )


def grenzen(nuten, ueber_von=None):
    """Grenzen für einen Nutenfräser, der alle `nuten` kann – oder None, wenn keiner das kann
    (dann je Nut einzeln fragen)."""
    if not nuten:
        return None
    d_max = min(2 * (n.r_zugang - SPIEL) for n in nuten)
    b_max = min(n.breite for n in nuten)
    vorschlag = vorschlag_werkzeug(nuten, ueber_von)
    if vorschlag is None:
        return None
    hals_max = min(_hals_max(n, vorschlag.durchmesser) for n in nuten)
    return Grenzen(
        d_max,
        b_max,
        hals_max,
        float(vorschlag.hals_laenge) - VORSCHLAG_HALS_RESERVE,
        float(vorschlag.durchmesser),
        float(vorschlag.schaft),
    )


def _hals_max(nut, d):
    """So dick darf der Hals einer Scheibe Ø d höchstens sein, damit er am Rand nicht anstößt, wenn
    die Scheibe auf R steht: über die ganze Höhe bis zur Oberkante der engste Abschnitt."""
    e = nut.radius - d / 2
    engste = min(r for z0, z1, r in nut.profil if z0 >= nut.z_oben - GLEICH)
    return 2 * (engste - SPIEL - e)


def vorschlag_werkzeug(nuten, ueber_von=None):
    """Ein Nutenfräser (werkzeuge.Werkzeug, Nummer 0), der alle `nuten` fräst: der größte übliche
    Ø (DURCHMESSER_REIHE), der durch die engste Bohrung passt, die Scheibe so breit wie die
    schmalste Nut, der Hals so dick, wie es geht (höchstens die Hälfte von D) und lang genug, der
    Schaft der nächste übliche – None, wenn es keinen gibt."""
    from . import werkzeuge as wz

    if not nuten:
        return None
    d_max = min(2 * (n.r_zugang - SPIEL) for n in nuten)
    b = min(n.breite for n in nuten)
    for d in sorted((x for x in DURCHMESSER_REIHE if x <= d_max + GLEICH), reverse=True):
        hals = min(_hals_max(n, d) for n in nuten)
        hals = math.floor(min(hals, VORSCHLAG_HALS_ANTEIL * d) * 2.0) / 2.0
        if hals < max(2.0, 0.15 * d):
            continue  # der Hals würde zu dünn – lieber eine kleinere Scheibe
        schaft = next((s for s in SCHAFT_REIHE if s >= hals - GLEICH), hals)
        werkzeug = wz.Werkzeug(
            nummer=0,
            name=tr("rn.vorschlag.name", d=f"{d:g}", b=_mm(b)),
            art=wz.NUTENFRAESER,
            durchmesser=float(d),
            schneiden=12 if d >= 40 else 6,
            schneidenbreite=round(b, 3),
            hals_d=float(hals),
            schaft=float(schaft),
            schneidstoff=wz.HSS if d >= 25 else wz.VHM,
        )
        lang = 0.0
        for n in nuten:
            ueber = ueber_von(n) if ueber_von else None
            e = n.radius - d / 2
            rho = e + schaft / 2
            hoch = (ueber(rho) if ueber else n.z_kante) + SPIEL_OBEN
            lang = max(lang, hoch - n.z_oben)
        werkzeug.hals_laenge = float(math.ceil(lang + VORSCHLAG_HALS_RESERVE))
        werkzeug.gesamtlaenge = float(math.ceil(b + werkzeug.hals_laenge + 3 * schaft + 10))
        if all(not werkzeug_pruefen(n, werkzeug, ueber=ueber_von(n) if ueber_von else None)
               for n in nuten):  # fmt: skip
            return werkzeug
    return None


def aus_dem_katalog(nuten, katalog, ueber_von=None, hoechstens=3):
    """[werkzeuge.Werkzeug] – Nutenfräser aus dem Katalog der Hersteller (werkzeugwahl.
    katalog_werkzeuge), die alle `nuten` fräsen, der größte Ø zuerst; den Hals, den der Katalog
    selten nennt, geschätzt (werkzeuge.mass)."""
    from . import werkzeuge as wz

    gefunden = []
    for k in katalog:
        if k.art != wz.NUTENFRAESER or float(k.durchmesser) <= 0:
            continue
        w = wz.Werkzeug(
            nummer=0,
            art=wz.NUTENFRAESER,
            durchmesser=float(k.durchmesser),
            schneidenbreite=float(getattr(k, "schneidenbreite", 0.0) or 0.0),
            hals_d=float(k.hals_d or 0.0),
            hals_laenge=float(k.hals_laenge or 0.0),
            schaft=float(k.schaft or 0.0),
            gesamtlaenge=float(k.gesamtlaenge or 0.0),
            name=" ".join(t for t in (k.hersteller, k.name or k.artikel) if t),
            hersteller=k.hersteller,
            artikel=k.artikel,
            link=k.link,
        )
        if w.schneidenbreite <= 0:
            continue
        if all(not werkzeug_pruefen(n, w, ueber=ueber_von(n) if ueber_von else None)
               for n in nuten):  # fmt: skip
            gefunden.append(w)
    gefunden.sort(key=lambda w: (-w.durchmesser, -w.hals_d))
    return gefunden[:hoechstens]


# --- Die Bahn -------------------------------------------------------------------------------------


@dataclass
class Ringnutwerte:
    """Was die Ringnut braucht; Längen in mm, z nach oben im Job."""

    werkzeug: object  # werkzeuge.Werkzeug – der Nutenfräser
    zustellung: float  # ae: so weit je radialer Stufe
    sicher: float  # z für den Eilgang über allem
    sicherheit: float = vb.SICHERHEIT  # so weit über der Oberkante endet der Eilgang hinab, …
    gleichlauf: bool = True
    schlichten: bool = True  # zuletzt ein Kreis auf Maß, davor bleibt `rest`
    rest: float = SCHLICHT_REST
    vorschub: float = 0.0  # mm/min an der Schneide – für die Zeit; 0: 1000
    eintauchen: float = 0.0
    halter: object = None  # halter.Halter – für die Prüfung von Schaft und Halter
    laenge: float = 0.0  # mm ab Spindelnase


@dataclass
class Ringnutbahn:
    """Ergebnis von planen()."""

    punkte: list
    nuten: int  # so viele gefräst
    kreise: int  # volle Kreise über alle Nuten (Stufen und Kreise auf Maß)
    hoehen: int  # über alle Nuten
    z_min: float
    laenge: float  # mm im Vorschub
    zeit: float  # Minuten (bahn.zeit)
    namen: tuple = ()  # die Flächen der gefrästen Nuten
    # ((Name der Nut, Grund), …): die das Werkzeug nicht kann – sie bleiben unfertig.
    nicht_passend: tuple = ()
    je_nut: list = field(default_factory=list)  # [{name, kreise, stufen, hoehen, zeit, reserve}]
    reserve: float = math.inf  # die eigene Prüfung: das Engste über alle Punkte (mm)
    hals_rand: float = math.inf  # davon: der kleinste Abstand Hals – Rand (mm)


def _stufen(nut, d, ae, rest, schlichten):
    """Die Radien der Scheibenschneide von innen nach außen: Stufen um höchstens ae bis R − rest,
    dann R (ohne Schlichten: in Stufen bis R)."""
    r_ziel = nut.radius - (rest if schlichten else 0.0)
    r_von = min(nut.r_innen, r_ziel)
    weg = r_ziel - r_von
    anzahl = max(1, int(math.ceil(weg / max(ae, GLEICH) - 1e-9))) if weg > GLEICH else 0
    radien = [r_von + weg * (i + 1) / anzahl for i in range(anzahl)]
    if schlichten or not radien:
        radien.append(nut.radius)
    return radien


def _anteil(radius_bahn, d):
    """Vorschub der Mitte je Vorschub an der Schneide auf einem Bogen um die Achse: r ÷ (r + D/2)
    (beim Innenkreis läuft die Schneide schneller als die Mitte – an der Lagernut Ø 65 mit Ø 58
    7,3-mal). Höchstens 1."""
    if radius_bahn <= GLEICH:
        return 1.0
    return min(1.0, radius_bahn / (radius_bahn + d / 2))


def _halbkreis(punkte, von, nach, z, uhr, d):
    mx, my = (von[0] + nach[0]) / 2, (von[1] + nach[1]) / 2
    r = math.hypot(nach[0] - mx, nach[1] - my)
    punkt = bn.Punkt(False, nach[0], nach[1], z, bogen=(mx, my, uhr), anteil=_anteil(r, d))
    laenge = bn.weg(punkte[-1], punkt)
    punkte.append(punkt)
    return laenge


def _kreis(punkte, mitte, e, winkel, z, uhr, d):
    """Ein voller Kreis um die Achse mit der Mitte des Werkzeugs auf `e` ab `winkel` – in Vierteln
    (bohrung_bahn._bogen_punkte). Gibt (Länge, Winkel am Ende)."""
    richtung = -1.0 if uhr else 1.0
    vorher = len(punkte)
    laenge = bb._bogen_punkte(punkte, mitte, e, winkel, winkel + richtung * 2 * math.pi, z, z, uhr)
    anteil = _anteil(e, d)
    for i in range(vorher, len(punkte)):
        punkte[i] = replace(punkte[i], anteil=anteil)
    return laenge, winkel + richtung * 2 * math.pi


def _nut_fraesen(punkte, nut, w, d, b):
    """Eine Nut, die Mitte des Werkzeugs schon auf der Achse in der Bohrung auf der ersten Höhe.
    Gibt (Länge, Kreise, Stufen je Höhe, Höhen)."""
    uhr = not w.gleichlauf  # Gleichlauf: das Material (außen) rechts – gegen den Uhrzeigersinn
    mitte = nut.mitte
    ae = w.zustellung if w.zustellung > 0 else STUFE_ANTEIL * d
    radien = _stufen(nut, d, ae, w.rest, w.schlichten)
    laenge = 0.0
    kreise = 0
    lagen = hoehen(nut, b)
    for k, zb in enumerate(lagen):
        if k:
            # Mittig hinab auf die nächste Höhe im Vorschub: Die unterste liegt am Grund auf dem
            # Boden – im Eilgang führe die Scheibe auf ihn (0,0 mm, Zweifler 14.11.).
            punkte.append(bn.Punkt(False, mitte[0], mitte[1], zb))
        winkel = 0.0
        e = radien[0] - d / 2
        ziel = bb._auf_kreis(mitte, e, winkel)
        if e > GLEICH:
            laenge += _halbkreis(punkte, mitte, ziel, zb, uhr, d)
        else:
            punkt = bn.Punkt(False, ziel[0], ziel[1], zb)
            laenge += bn.weg(punkte[-1], punkt)
            punkte.append(punkt)
        stueck, winkel = _kreis(punkte, mitte, e, winkel, zb, uhr, d)
        laenge += stueck
        kreise += 1
        for r_neu in radien[1:]:
            e_neu = r_neu - d / 2
            hier = bb._auf_kreis(mitte, e, winkel)
            dort = bb._auf_kreis(mitte, e_neu, winkel + math.pi)
            laenge += _halbkreis(punkte, hier, dort, zb, uhr, d)  # wächst über einen halben Umlauf
            winkel += math.pi
            stueck, winkel = _kreis(punkte, mitte, e_neu, winkel, zb, uhr, d)
            laenge += stueck
            kreise += 1
            e = e_neu
        hier = bb._auf_kreis(mitte, e, winkel)
        if e > GLEICH:
            laenge += _halbkreis(punkte, hier, mitte, zb, uhr, d)  # tangential ab, zur Mitte
    return laenge, kreise, len(radien), len(lagen)


def _folge(nuten):
    """Die Nuten in der Reihenfolge: je Bohrung (Achse) von oben nach unten, die Bohrungen in der
    Folge des kürzesten Wegs von einer zur nächsten."""
    gruppen = []
    for n in nuten:
        for g in gruppen:
            if (
                abs(g[0].mitte[0] - n.mitte[0]) < ACHSE_GLEICH
                and abs(g[0].mitte[1] - n.mitte[1]) < ACHSE_GLEICH
            ):
                g.append(n)
                break
        else:
            gruppen.append([n])
    for g in gruppen:
        g.sort(key=lambda n: -n.z_oben)
    folge = []
    ort = gruppen[0][0].mitte if gruppen else (0.0, 0.0)
    while gruppen:
        g = min(gruppen, key=lambda g: math.hypot(g[0].mitte[0] - ort[0], g[0].mitte[1] - ort[1]))
        gruppen.remove(g)
        folge.append(g)
        ort = g[0].mitte
    return folge


def planen(werte, nuten, form=None, stand=None):
    """Die Bahn „Ringnut fräsen“ (Ringnutbahn) für die Nuten `nuten` ([Ringnut]) mit dem
    Nutenfräser aus `werte`. Nuten, die er nicht kann, bleiben (Ringnutbahn.nicht_passend).
    `form`: das Teil – für das, was über der Oberkante steht; `stand` (materialstand): Steht in
    der Bohrung noch Material über der Nut, ist sie nicht fertig – dann geht es nicht. Jede Bahn
    prüft pruefen() nach. ValueError mit einem Satz, wenn es nicht geht."""
    w = werte
    from . import werkzeuge as wz

    if w.werkzeug is None or w.werkzeug.art != wz.NUTENFRAESER or w.werkzeug.durchmesser <= 0:
        raise ValueError(tr("rn.fehler.werkzeug"))
    if not nuten:
        raise ValueError(tr("rn.fehler.keine"))
    stuecke = profil(w.werkzeug, w.halter, w.laenge)
    d = 2 * stuecke[0].radius
    b = stuecke[0].z_bis
    passend, nicht = [], []
    uebers = {}
    for n in nuten:
        uebers[n.name] = ueber_der_kante(form, n)
        grund = werkzeug_pruefen(n, w.werkzeug, w.halter, w.laenge, uebers[n.name])
        if not grund and stand is not None:
            grund = _bohrung_offen(n, d, stand)
        if grund:
            nicht.append((n.name, grund))
        else:
            passend.append(n)
    if not passend:
        raise ValueError(nicht[0][1])
    punkte = []
    laenge = 0.0
    kreise = hoehen_ = 0
    z_min = math.inf
    je_nut = []
    for gruppe in _folge(passend):
        mitte = gruppe[0].mitte
        punkte.append(bn.Punkt(True, mitte[0], mitte[1], w.sicher))
        knapp = min(w.sicher, gruppe[0].z_kante + w.sicherheit)
        if knapp < w.sicher - GLEICH:
            punkte.append(bn.Punkt(True, mitte[0], mitte[1], knapp))
        for nut in gruppe:
            anfang = len(punkte)
            lagen = hoehen(nut, b)
            vorher = bn.zeit(punkte, w.vorschub or 1000.0, w.eintauchen or None)
            _hinab(punkte, nut, stuecke, lagen[0], w, stand, uebers[nut.name])
            stueck, n_kreise, n_stufen, n_hoehen = _nut_fraesen(punkte, nut, w, d, b)
            laenge += stueck
            kreise += n_kreise
            hoehen_ += n_hoehen
            z_min = min(z_min, min(lagen))
            je_nut.append(
                {
                    "name": nut.name,
                    "nut": nut,
                    "von": anfang,
                    "bis": len(punkte),
                    "kreise": n_kreise,
                    "stufen": n_stufen,
                    "hoehen": n_hoehen,
                    "zeit": bn.zeit(punkte, w.vorschub or 1000.0, w.eintauchen or None) - vorher,
                }
            )
        punkte.append(bn.Punkt(True, mitte[0], mitte[1], w.sicher))  # mittig heraus
    zeit = bn.zeit(punkte, w.vorschub if w.vorschub > 0 else 1000.0, w.eintauchen or None)
    bahn = Ringnutbahn(
        punkte=punkte,
        nuten=len(passend),
        kreise=kreise,
        hoehen=hoehen_,
        z_min=z_min,
        laenge=laenge,
        zeit=zeit,
        namen=tuple(f for n in passend for f in n.flaechen),
        nicht_passend=tuple(nicht),
        je_nut=je_nut,
    )
    reserve, hals_rand = pruefen(bahn, stuecke, uebers)
    bahn.reserve, bahn.hals_rand = reserve, hals_rand
    if reserve < -GLEICH:
        raise ValueError(tr("rn.fehler.pruefung", mm=_mm(-reserve)))
    return bahn


def _hinab(punkte, nut, stuecke, zb, w, stand, ueber):
    """Mittig hinab bis auf die Höhe `zb` der Scheibenunterkante. Im Eilgang nur, wenn der
    Materialstand (`stand`) zeigt, dass die Bohrung offen ist (_bohrung_offen, in planen), und
    rundum mindestens EILGANG_LUFT bleibt – sonst im Vorschub: Ohne Stand (eine Simultan-Operation
    davor) weiß die Ringnut nicht, ob die Bohrung fertig ist; mit 0,3 mm Spiel (Ø 19 in Ø 20)
    meldete „Kollision prüfen“ jede Ringnut (Warnabstand 1 mm). Der Eilgang endet `sicherheit` über
    der Nuthöhe, den Rest fährt der Vorschub – wie bohrung_bahn (am Grund läge die Scheibe sonst im
    Eilgang auf dem Boden)."""
    mx, my = nut.mitte
    luft = pruefe_lage(nut, stuecke, 0.0, zb, ueber, absenken=True).reserve + SPIEL
    zuletzt = punkte[-1].z if punkte else math.inf
    if stand is not None and luft >= EILGANG_LUFT - GLEICH:
        knapp = zb + w.sicherheit
        if knapp < zuletzt - GLEICH:
            punkte.append(bn.Punkt(True, mx, my, knapp))
    punkte.append(bn.Punkt(False, mx, my, zb))


def _bohrung_offen(nut, d, stand):
    """ "" wenn in der Bohrung über der Nut nichts mehr steht (der Materialstand vor der Operation,
    von oben) – sonst der Satz: erst die Bohrung fertig fräsen. Geprüft im ganzen Radius, den die
    Scheibe mit SPIEL mittig braucht: Mit 0,5 mm Wandaufmaß in der Bohrung Ø 20 (offen bis r 9,5)
    lag die Scheibe Ø 19,4 im Eilgang 0,2 mm in der Wand, solange nur der Kern bis d/2 − 2 Zellen
    zählte (Zweifler 14.11.)."""
    # Höchstens bis 0,05 vor die Wand der fertigen Bohrung: Eine Zelle genau auf ihr hätte im
    # Höhenfeld noch die Höhe des Teils. Die Scheibe bleibt so 0,25 mm von einem Aufmaß weg.
    rand = min(d / 2 + SPIEL, nut.r_zugang - 0.05)
    hoch = stand.hoechste_bei(nut.mitte[0], nut.mitte[1], rand)
    if hoch > nut.z_unten + 0.05:
        return tr("rn.grund.bohrung_voll", z=_mm(hoch))
    return ""


def pruefen(bahn, stuecke, uebers=None, schritt_grad=5.0):
    """Die eigene Prüfung im Schnitt r–z (siehe oben): je Nut jeden Punkt ihrer Bahn – Bögen in
    Schritten von `schritt_grad` – mit dem Werkzeug (`stuecke`, profil) gegen ihre Bohrung
    (pruefe_lage). Gibt (das Engste über alles, der kleinste Abstand Hals – Rand) in mm; negativ:
    es stößt an. Die Eilgänge mittig hinab prüft sie mit (absenken)."""
    uebers = uebers or {}
    engste = math.inf
    hals_rand = math.inf
    hals = [s for s in stuecke if s.art == HALS]
    for eintrag in bahn.je_nut:
        nut = eintrag["nut"]
        ueber = uebers.get(nut.name)
        punkte = bahn.punkte[max(eintrag["von"] - 1, 0) : eintrag["bis"]]
        for zb, e in _stellen(punkte, nut, schritt_grad):
            befund = pruefe_lage(nut, stuecke, e, zb, ueber, absenken=e < GLEICH)
            engste = min(engste, befund.reserve)
            if hals:
                h = pruefe_lage(nut, hals, e, zb)
                if not h.oben:
                    hals_rand = min(hals_rand, h.reserve + SPIEL)
    return engste, hals_rand


def _stellen(punkte, nut, schritt_grad):
    """(z der Scheibenunterkante, Abstand e von der Achse) entlang der Bahn – Bögen fein."""
    mx, my = nut.mitte
    for von, nach in zip(punkte, punkte[1:], strict=False):
        if nach.bogen is None:
            for t in (0.0, 0.5, 1.0):
                x = von.x + t * (nach.x - von.x)
                y = von.y + t * (nach.y - von.y)
                z = von.z + t * (nach.z - von.z)
                yield z, math.hypot(x - mx, y - my)
            continue
        bx, by, uhr = nach.bogen
        a0 = math.atan2(von.y - by, von.x - bx)
        weit = bn.winkel(von, nach)
        r = math.hypot(von.x - bx, von.y - by)
        n = max(2, int(math.ceil(math.degrees(weit) / schritt_grad)))
        for i in range(n + 1):
            t = i / n
            a = a0 - t * weit if uhr else a0 + t * weit
            x, y = bx + r * math.cos(a), by + r * math.sin(a)
            yield von.z + t * (nach.z - von.z), math.hypot(x - mx, y - my)
