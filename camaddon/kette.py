# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Maschine aus einer Assembly lesen: Glieder, Achsen und Meldungen.

Eine Maschine wird in FreeCAD als Assembly gebaut – grobe Körper, verbunden
mit Gelenken. Dieses Modul macht daraus eine *kinematische Kette*:

Glied
    Alle Bauteile, die starr miteinander verbunden sind (Fixed-Gelenke,
    RigidGroups) und sich deshalb gemeinsam bewegen. Das Glied mit dem
    fixierten Bauteil ist das Maschinenbett.

Achse
    Ein Schiebe- (Slider) oder Drehgelenk (Revolute) zwischen zwei Gliedern.
    Die Achsen bilden einen Baum, der beim Bett beginnt: Jede Achse kennt ihr
    Eltern-Glied (zum Bett hin) und ihr Kind-Glied, das sie bewegt.

Meldung
    Alles, was beim Lesen auffällt – ein loser Körper, eine nicht unterstützte
    Gelenkart –, als fertiger Satz für den Benutzer.

Die Assembly wird nur gelesen, nie verändert. Läuft ohne Oberfläche.
"""

from dataclasses import dataclass, field

import FreeCAD

from .sprache import tr

# Arten von Achsen.
LINEAR = "linear"
DREH = "dreh"

# Gelenkarten der Assembly: welche eine Achse sind und welche starr verbinden.
# Alle anderen (Ball, Cylindrical, Distance …) kommen in Maschinen nicht vor
# und werden gemeldet.
ACHSE_ZU_GELENKART = {"Slider": LINEAR, "Revolute": DREH}
STARRE_GELENKARTEN = {"Fixed"}

# Wie ernst eine Meldung ist.
HINWEIS = "hinweis"
WARNUNG = "warnung"


@dataclass
class Meldung:
    """Ein Satz für den Benutzer, z. B. „Der Körper „Deckel“ hängt an keinem Gelenk.“"""

    schwere: str  # HINWEIS oder WARNUNG
    schluessel: str  # Schlüssel des Textes in translations/*.json – für Tests
    text: str  # der fertige Satz in der eingestellten Sprache
    bezug: object = None  # das Objekt, um das es geht; der Dialog springt dorthin


def meldung(schluessel, schwere=WARNUNG, bezug=None, **werte):
    """Baut eine Meldung; `werte` füllen die Platzhalter des Textes."""
    return Meldung(schwere, schluessel, tr(schluessel, **werte), bezug)


@dataclass(eq=False)  # eq=False: Glieder werden nach Identität verglichen und gehasht
class Glied:
    """Starr verbundene Bauteile, die sich gemeinsam bewegen."""

    bauteile: list = field(default_factory=list)
    ist_bett: bool = False

    def namen(self):
        """Die Namen der Bauteile, für die Anzeige: „Bett, Spindelstock“."""
        return ", ".join(b.Label for b in self.bauteile)


@dataclass(eq=False)
class Achse:
    """Ein bewegliches Gelenk der Assembly, eingeordnet in die Kette."""

    gelenk: object  # das Gelenk-Objekt der Assembly
    art: str  # LINEAR oder DREH
    eltern: Glied  # das Glied zum Bett hin
    kind: Glied  # das Glied, das diese Achse bewegt
    richtung: FreeCAD.Vector  # Einheitsvektor in Weltkoordinaten
    ursprung: FreeCAD.Vector  # ein Punkt auf der Achse, in Weltkoordinaten
    minimum: float | None  # Begrenzung am Gelenk in mm bzw. Grad; None = keine
    maximum: float | None


@dataclass
class Kette:
    """Ergebnis von `lies_kette()`."""

    glieder: list  # alle Glieder, auch nicht angebundene
    achsen: list  # nur die im Baum – je Kind-Glied genau eine Achse
    meldungen: list

    def bett(self):
        """Das feste Glied, oder None, wenn kein Bauteil fixiert ist."""
        return next((g for g in self.glieder if g.ist_bett), None)

    def achse_von(self, gelenk):
        """Die Achse zu einem Gelenk-Objekt der Assembly, oder None."""
        return next((a for a in self.achsen if a.gelenk == gelenk), None)

    def glied_von(self, objekt):
        """Das Glied, zu dem ein Bauteil gehört – oder ein Objekt darin, z. B. ein LCS."""
        for glied in self.glieder:
            for bauteil in glied.bauteile:
                if objekt == bauteil or objekt in bauteil.OutListRecursive:
                    return glied
        return None

    def pfad_zum_bett(self, glied):
        """Die Achsen von `glied` bis zum Bett, beim Glied beginnend."""
        achse_zu_kind = {a.kind: a for a in self.achsen}
        pfad = []
        while glied in achse_zu_kind:
            achse = achse_zu_kind[glied]
            pfad.append(achse)
            glied = achse.eltern
        return pfad


def lies_kette(assembly):
    """Liest die kinematische Kette aus einer Assembly.

    Vier Schritte, je eine Funktion unten:

    1. die Gelenke der Assembly sortieren – fixiert, starr, beweglich;
    2. starr verbundene Bauteile zu Gliedern zusammenfassen;
    3. vom Bett aus die Achsen als Baum aufbauen;
    4. melden, was nicht angebunden ist.
    """
    bauteile = _bauteile(assembly)
    gelenke, meldungen = _sortiere_gelenke(assembly, bauteile)
    glieder, glied_von = _bilde_glieder(bauteile, gelenke)

    if not gelenke.fixiert:
        meldungen.append(meldung("kette.kein_festes_teil"))
        return Kette(glieder, [], meldungen)
    bett = glied_von[gelenke.fixiert[0]]
    bett.ist_bett = True

    achsen = _baue_baum(bett, gelenke.beweglich, glied_von, meldungen)
    _melde_nicht_angebundenes(bauteile, gelenke, glieder, achsen, meldungen)
    return Kette(glieder, achsen, meldungen)


# --- Schritt 1: Gelenke sortieren ---------------------------------------------


@dataclass
class _SortierteGelenke:
    """Ergebnis von Schritt 1."""

    fixiert: list = field(default_factory=list)  # fixierte Bauteile (gehören zum Bett)
    starr: list = field(default_factory=list)  # Gruppen starr verbundener Bauteile
    beweglich: list = field(default_factory=list)  # (Gelenk, LINEAR|DREH, Bauteil 1, Bauteil 2)
    angebunden: set = field(default_factory=set)  # Bauteile, an denen irgendein Gelenk hängt


def _bauteile(assembly):
    """Die Bauteile der Assembly – so, wie die Assembly selbst sie bewegt.

    `partsAsSolid=True`: Ein Part mit Körpern und LCS darin zählt als *ein*
    Bauteil, genau wie beim Lösen der Assembly.
    """
    # Erst hier importiert, nicht oben: Sonst lüde schon der Start von FreeCAD
    # (über die Werkzeugleiste des Addons) das ganze Assembly-Modul.
    import UtilsAssembly

    return UtilsAssembly.getMovablePartsWithin(assembly, partsAsSolid=True)


def _gelenk_objekte(assembly):
    """Alle Objekte in der Gelenkgruppe der Assembly."""
    import UtilsAssembly

    gruppe = UtilsAssembly.getJointGroup(assembly)
    return [] if gruppe is None else list(gruppe.Group)


def _sortiere_gelenke(assembly, bauteile):
    """Schritt 1: Jedes Gelenk der Assembly einer Sorte zuordnen."""
    gelenke = _SortierteGelenke()
    meldungen = []
    bekannt = set(bauteile)

    for gelenk in _gelenk_objekte(assembly):
        # „Suppressed“ und RigidGroups gibt es erst ab dem Wochen-Build;
        # getattr/hasattr halten den Code in FreeCAD 1.1 lauffähig.
        if getattr(gelenk, "Suppressed", False):
            continue
        if hasattr(gelenk, "ObjectToGround"):
            if gelenk.ObjectToGround in bekannt:
                gelenke.fixiert.append(gelenk.ObjectToGround)
            continue
        if hasattr(gelenk, "ObjectsToRigidGroup"):
            gruppe = [b for b in gelenk.ObjectsToRigidGroup if b in bekannt]
            gelenke.starr.append(gruppe)
            gelenke.angebunden.update(gruppe)
            continue

        gelenkart = getattr(gelenk, "JointType", None)
        if gelenkart is None:
            continue  # kein Gelenk (z. B. eine Ansicht in der Gelenkgruppe)
        # Reference1/2 halten (Bauteil, [Element]); das Bauteil ist das, was
        # die Assembly bewegt.
        teil1 = gelenk.Reference1[0] if gelenk.Reference1 else None
        teil2 = gelenk.Reference2[0] if gelenk.Reference2 else None
        if teil1 not in bekannt or teil2 not in bekannt:
            meldungen.append(meldung("kette.gelenk_ohne_teile", gelenk=gelenk.Label))
            continue

        gelenke.angebunden.update((teil1, teil2))
        if gelenkart in STARRE_GELENKARTEN:
            gelenke.starr.append([teil1, teil2])
        elif gelenkart in ACHSE_ZU_GELENKART:
            gelenke.beweglich.append((gelenk, ACHSE_ZU_GELENKART[gelenkart], teil1, teil2))
        else:
            meldungen.append(
                meldung("kette.gelenkart_nicht_unterstuetzt", gelenk=gelenk.Label, art=gelenkart)
            )
    return gelenke, meldungen


# --- Schritt 2: Glieder bilden ------------------------------------------------


class _StarreGruppen:
    """Fasst Bauteile zu Gruppen zusammen (Union-Find).

    Jedes Bauteil zeigt auf ein anderes seiner Gruppe; wer auf sich selbst
    zeigt, vertritt die Gruppe. `verbinde` hängt zwei Gruppen aneinander.
    """

    def __init__(self, bauteile):
        self._zeigt_auf = {b: b for b in bauteile}

    def vertreter(self, bauteil):
        while self._zeigt_auf[bauteil] is not bauteil:
            # Unterwegs abkürzen, damit spätere Suchen schneller sind.
            self._zeigt_auf[bauteil] = self._zeigt_auf[self._zeigt_auf[bauteil]]
            bauteil = self._zeigt_auf[bauteil]
        return bauteil

    def verbinde(self, a, b):
        self._zeigt_auf[self.vertreter(a)] = self.vertreter(b)


def _bilde_glieder(bauteile, gelenke):
    """Schritt 2: Starr verbundene Bauteile werden je ein Glied.

    Alle fixierten Bauteile gehören zum Bett – auch wenn sie nicht
    miteinander verbunden sind, stehen sie alle still.
    """
    gruppen = _StarreGruppen(bauteile)
    for gruppe in [*gelenke.starr, gelenke.fixiert]:
        for bauteil in gruppe[1:]:
            gruppen.verbinde(gruppe[0], bauteil)

    glieder = {}  # Vertreter einer Gruppe -> ihr Glied
    for bauteil in bauteile:
        glieder.setdefault(gruppen.vertreter(bauteil), Glied()).bauteile.append(bauteil)
    glied_von = {b: glieder[gruppen.vertreter(b)] for b in bauteile}
    return list(glieder.values()), glied_von


# --- Schritt 3: Achsen als Baum -----------------------------------------------


def _baue_baum(bett, beweglich, glied_von, meldungen):
    """Schritt 3: Vom Bett aus jedes erreichbare Glied über genau eine Achse anhängen.

    Breitensuche über die beweglichen Gelenke. Ein Gelenk zu einem schon
    erreichten Glied passt nicht in einen Baum und wird gemeldet.
    """
    offene_gelenke = []
    for gelenk, art, teil1, teil2 in beweglich:
        glied1, glied2 = glied_von[teil1], glied_von[teil2]
        if glied1 is glied2:
            meldungen.append(meldung("kette.gelenk_im_glied", gelenk=gelenk.Label))
        else:
            offene_gelenke.append((gelenk, art, glied1, glied2))

    achsen = []
    erreicht = {bett}
    warteschlange = [bett]
    while warteschlange:
        glied = warteschlange.pop(0)
        for eintrag in list(offene_gelenke):
            gelenk, art, glied1, glied2 = eintrag
            if glied not in (glied1, glied2):
                continue
            offene_gelenke.remove(eintrag)
            # Die Seite des Gelenks, die am schon erreichten Glied hängt,
            # bestimmt die Richtung der Achse.
            seite, kind = (1, glied2) if glied1 is glied else (2, glied1)

            if kind in erreicht:
                _melde_zweites_gelenk(gelenk, glied, kind, achsen, meldungen)
                continue
            richtung, ursprung = _achsrichtung(gelenk, seite)
            minimum, maximum = _begrenzung(gelenk, art)
            achsen.append(Achse(gelenk, art, glied, kind, richtung, ursprung, minimum, maximum))
            erreicht.add(kind)
            warteschlange.append(kind)
    return achsen


def _melde_zweites_gelenk(gelenk, glied, kind, achsen, meldungen):
    """Ein Gelenk führt zu einem Glied, das schon eine Achse hat.

    Zwischen denselben zwei Gliedern ist das typisch eine Wiege, die in beiden
    Lagerböcken ein Drehgelenk bekommen hat. Das kann die Assembly nicht lösen
    (ausprobiert, Verlauf P-2026-09-25-13) – deshalb eine eigene, genaue
    Meldung. Sonst schließt das Gelenk die Kette zu einem Ring.
    """
    erstes = next((a for a in achsen if a.kind is kind and a.eltern is glied), None)
    if erstes is not None:
        meldungen.append(
            meldung("kette.doppelt_gelagert", gelenk=gelenk.Label, erstes=erstes.gelenk.Label)
        )
    else:
        meldungen.append(meldung("kette.geschlossene_schleife", gelenk=gelenk.Label))


def _achsrichtung(gelenk, seite):
    """Richtung und Ursprung der Achse in Weltkoordinaten.

    Die Achse ist die Z-Richtung des Gelenk-Koordinatensystems auf der
    angegebenen Seite (1 oder 2) des Gelenks.
    """
    import UtilsAssembly

    lage = UtilsAssembly.getJcsGlobalPlc(
        getattr(gelenk, f"Placement{seite}"), getattr(gelenk, f"Reference{seite}")
    )
    richtung = lage.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    richtung.normalize()
    return richtung, lage.Base


def _begrenzung(gelenk, art):
    """Minimum und Maximum aus der Begrenzung des Gelenks (mm bzw. Grad), sonst None."""
    if art == LINEAR:
        schalter, name, einheit = "EnableLength", "Length", "mm"
    else:
        schalter, name, einheit = "EnableAngle", "Angle", "deg"

    def wert(ende):  # ende: "Min" oder "Max"
        if not getattr(gelenk, schalter + ende, False):
            return None
        return float(getattr(gelenk, name + ende).getValueAs(einheit))

    return wert("Min"), wert("Max")


# --- Schritt 4: Nicht Angebundenes melden -------------------------------------


def _melde_nicht_angebundenes(bauteile, gelenke, glieder, achsen, meldungen):
    """Schritt 4: Bauteile ohne Gelenk und Glieder, die nicht am Bett hängen."""
    fixiert = set(gelenke.fixiert)
    lose = [b for b in bauteile if b not in gelenke.angebunden and b not in fixiert]
    for bauteil in lose:
        meldungen.append(meldung("kette.koerper_lose", koerper=bauteil.Label))

    erreicht = {a.kind for a in achsen} | {g for g in glieder if g.ist_bett}
    for glied in glieder:
        # Ein Glied aus lauter losen Bauteilen ist oben schon gemeldet.
        if glied not in erreicht and not all(b in lose for b in glied.bauteile):
            meldungen.append(meldung("kette.glied_haengt_nicht_am_bett", koerper=glied.namen()))
