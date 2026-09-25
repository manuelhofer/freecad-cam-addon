# SPDX-License-Identifier: LGPL-2.1-or-later
"""Liest aus einer Assembly die kinematische Kette einer Maschine.

Ergebnis ist eine `Kette`: die Glieder (starr verbundene Körper), die
beweglichen Gelenke dazwischen (Slider, Revolute) als Baum vom festen Glied
aus, und Meldungen über alles, was dabei auffällt.

Läuft ohne Oberfläche. Die Assembly wird nur gelesen, nie verändert.
"""

from dataclasses import dataclass, field

import FreeCAD

from .sprache import tr

# Gelenkarten der Assembly, die für eine Maschine eine Achse sind.
LINEAR = "linear"
DREH = "dreh"
BEWEGLICH = {"Slider": LINEAR, "Revolute": DREH}

# Diese verbinden Körper starr zu einem Glied.
STARR = {"Fixed"}

# Schwere einer Meldung.
HINWEIS = "hinweis"
WARNUNG = "warnung"

@dataclass
class Meldung:
    schwere: str
    schluessel: str
    text: str
    bezug: object = None  # Objekt, auf das sich die Meldung bezieht (für den Dialog)


def meldung(schluessel, schwere=WARNUNG, bezug=None, **werte):
    return Meldung(schwere, schluessel, tr(schluessel, **werte), bezug)


@dataclass(eq=False)
class Glied:
    nummer: int
    koerper: list = field(default_factory=list)
    fest: bool = False

    def namen(self):
        return ", ".join(k.Label for k in self.koerper)


@dataclass(eq=False)
class Gelenk:
    objekt: object
    art: str  # LINEAR oder DREH
    eltern: Glied = None  # Seite zum festen Glied hin
    kind: Glied = None
    richtung: FreeCAD.Vector = None  # Einheitsvektor, global
    ursprung: FreeCAD.Vector = None  # Punkt auf der Achse, global
    minimum: float = None  # mm bzw. Grad; None = keine Begrenzung
    maximum: float = None


@dataclass
class Kette:
    glieder: list
    gelenke: list  # nur die im Baum, je Kind-Glied genau eins
    meldungen: list

    def festes_glied(self):
        return next((g for g in self.glieder if g.fest), None)

    def glied_von(self, objekt):
        """Das Glied, zu dem ein Körper (oder ein Objekt darin) gehört."""
        for glied in self.glieder:
            for koerper in glied.koerper:
                if objekt == koerper or objekt in koerper.OutListRecursive:
                    return glied
        return None

    def pfad_zum_festen_glied(self, glied):
        """Gelenke von `glied` bis zum festen Glied, vom Glied aus gesehen."""
        nach_kind = {g.kind: g for g in self.gelenke}
        pfad = []
        while glied in nach_kind:
            gelenk = nach_kind[glied]
            pfad.append(gelenk)
            glied = gelenk.eltern
        return pfad


def _komponenten(assembly):
    """Die Bauteile der Assembly, so wie die Assembly sie bewegt."""
    import UtilsAssembly

    return UtilsAssembly.getMovablePartsWithin(assembly, partsAsSolid=True)


def _gelenke(assembly):
    import UtilsAssembly

    gruppe = UtilsAssembly.getJointGroup(assembly)
    return [] if gruppe is None else list(gruppe.Group)


def _ist_unterdrueckt(objekt):
    return bool(getattr(objekt, "Suppressed", False))


def _achse(gelenk_objekt, seite):
    """Richtung und Ursprung der Gelenkachse (Z des Gelenk-Koordinatensystems)."""
    import UtilsAssembly

    referenz = getattr(gelenk_objekt, f"Reference{seite}")
    platzierung = getattr(gelenk_objekt, f"Placement{seite}")
    global_ = UtilsAssembly.getJcsGlobalPlc(platzierung, referenz)
    richtung = global_.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    richtung.normalize()
    return richtung, global_.Base


def _grenzen(gelenk_objekt, art):
    def wert(schalter, name, einheit):
        if not getattr(gelenk_objekt, schalter, False):
            return None
        return float(getattr(gelenk_objekt, name).getValueAs(einheit))

    if art == LINEAR:
        return wert("EnableLengthMin", "LengthMin", "mm"), wert("EnableLengthMax", "LengthMax", "mm")
    return wert("EnableAngleMin", "AngleMin", "deg"), wert("EnableAngleMax", "AngleMax", "deg")


class _Vereinigung:
    """Union-Find über Körper, um starr verbundene zu Gliedern zu sammeln."""

    def __init__(self, elemente):
        self.vater = {e: e for e in elemente}

    def wurzel(self, e):
        while self.vater[e] is not e:
            self.vater[e] = self.vater[self.vater[e]]
            e = self.vater[e]
        return e

    def verbinde(self, a, b):
        self.vater[self.wurzel(a)] = self.wurzel(b)


def lies_kette(assembly):
    komponenten = _komponenten(assembly)
    meldungen = []
    vereinigung = _Vereinigung(komponenten)
    geerdet = set()
    beweglich = []
    verbunden = set()

    for objekt in _gelenke(assembly):
        if _ist_unterdrueckt(objekt):
            continue
        if hasattr(objekt, "ObjectToGround"):
            if objekt.ObjectToGround in vereinigung.vater:
                geerdet.add(objekt.ObjectToGround)
            continue
        if hasattr(objekt, "ObjectsToRigidGroup"):
            teile = [t for t in objekt.ObjectsToRigidGroup if t in vereinigung.vater]
            for teil in teile[1:]:
                vereinigung.verbinde(teile[0], teil)
            verbunden.update(teile)
            continue
        art_assembly = getattr(objekt, "JointType", None)
        if art_assembly is None:
            continue
        teil1 = objekt.Reference1[0] if objekt.Reference1 else None
        teil2 = objekt.Reference2[0] if objekt.Reference2 else None
        if teil1 not in vereinigung.vater or teil2 not in vereinigung.vater:
            meldungen.append(meldung("kette.gelenk_ohne_teile", gelenk=objekt.Label))
            continue
        verbunden.update((teil1, teil2))
        if art_assembly in STARR:
            vereinigung.verbinde(teil1, teil2)
        elif art_assembly in BEWEGLICH:
            beweglich.append((objekt, BEWEGLICH[art_assembly], teil1, teil2))
        else:
            meldungen.append(
                meldung("kette.gelenkart_nicht_unterstuetzt", gelenk=objekt.Label, art=art_assembly)
            )

    # Alle geerdeten Körper gehören zum Maschinenbett, auch wenn sie nicht
    # per Fixed verbunden sind.
    geerdet = list(geerdet)
    for teil in geerdet[1:]:
        vereinigung.verbinde(geerdet[0], teil)

    glieder = {}
    for teil in komponenten:
        wurzel = vereinigung.wurzel(teil)
        if wurzel not in glieder:
            glieder[wurzel] = Glied(len(glieder) + 1)
        glieder[wurzel].koerper.append(teil)
    glied_von = {teil: glieder[vereinigung.wurzel(teil)] for teil in komponenten}

    if not geerdet:
        meldungen.append(meldung("kette.kein_festes_teil"))
        return Kette(list(glieder.values()), [], meldungen)
    festes = glied_von[geerdet[0]]
    festes.fest = True

    lose = [t for t in komponenten if t not in verbunden and t not in geerdet]
    for teil in lose:
        meldungen.append(meldung("kette.koerper_lose", koerper=teil.Label))

    # Baum vom festen Glied aus aufbauen (Breitensuche).
    kanten = []
    for objekt, art, teil1, teil2 in beweglich:
        a, b = glied_von[teil1], glied_von[teil2]
        if a is b:
            meldungen.append(meldung("kette.gelenk_im_glied", gelenk=objekt.Label))
            continue
        kanten.append((objekt, art, teil1, teil2, a, b))

    gelenke = []
    erreicht = {festes}
    offen = [festes]
    while offen:
        glied = offen.pop(0)
        for kante in list(kanten):
            objekt, art, _teil1, _teil2, a, b = kante
            if glied not in (a, b):
                continue
            kanten.remove(kante)
            seite, kind = (1, b) if a is glied else (2, a)
            if kind in erreicht:
                # Zweites Gelenk zwischen denselben Gliedern – typisch: Wiege in
                # zwei Lagerböcken. Der Löser der Assembly scheitert daran
                # (ausprobiert, P-2026-09-25-13), also gezielt darauf hinweisen.
                vorhanden = next((g for g in gelenke if g.kind is kind and g.eltern is glied), None)
                if vorhanden:
                    meldungen.append(
                        meldung(
                            "kette.doppelt_gelagert", gelenk=objekt.Label, erstes=vorhanden.objekt.Label
                        )
                    )
                else:
                    meldungen.append(meldung("kette.geschlossene_schleife", gelenk=objekt.Label))
                continue
            richtung, ursprung = _achse(objekt, seite)
            minimum, maximum = _grenzen(objekt, art)
            gelenke.append(Gelenk(objekt, art, glied, kind, richtung, ursprung, minimum, maximum))
            erreicht.add(kind)
            offen.append(kind)

    for glied in glieder.values():
        # Einzelne lose Körper sind oben schon gemeldet.
        if glied not in erreicht and not all(k in lose for k in glied.koerper):
            meldungen.append(meldung("kette.glied_haengt_nicht_am_bett", koerper=glied.namen()))

    return Kette(list(glieder.values()), gelenke, meldungen)
