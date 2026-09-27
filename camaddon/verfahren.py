# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Maschine von Hand verfahren (W-001, Stufe 3) – Grundlage der Simulation.

Jede Achse der Kette hat eine Stellung: mm bei Linear-, Grad bei Drehachsen,
gezählt wie die Begrenzung am Gelenk – als Lage von Seite 2 des Gelenks
gegenüber Seite 1. So passen Anzeige und Grenzen zu dem, was im Gelenk steht.

Verfahren heißt: alle Bauteile hinter der Achse verschieben bzw. drehen – ihr
Glied und alles, was weiter außen hängt. Dann halten alle Gelenke, und die
Assembly lässt die Stellung stehen, auch beim Neuberechnen (in 1.1.3 und im
Wochen-Build ausprobiert). Ihre Grenzen setzt die Assembly selbst nicht
durch – das tut `setze()`.

Gerechnet wird immer vom Ausgang aus, der Lage beim Öffnen: Jede Achse sitzt
fest an ihrem Eltern-Glied, also ist die Lage eines Bauteils

    Lage = B1(w1) · B2(w2) · … · Lage im Ausgang

mit den Achsen vom Bett nach außen, jede so, wie sie im Ausgang lag, und wi
dem Weg seit dem Ausgang. So summieren sich keine Rundungsfehler auf, egal
wie oft ein Regler bewegt wird.

Läuft ohne Oberfläche.
"""

import math

import FreeCAD

from . import kette as kette_modul
from . import maschine as m
from .kette import LINEAR

Z = FreeCAD.Vector(0, 0, 1)
X = FreeCAD.Vector(1, 0, 0)


def gelenkstellung(gelenk, art):
    """Die Stellung eines Gelenks: Seite 2 gegenüber Seite 1, in mm bzw. Grad.

    Linear: der Abstand der Ursprünge entlang der Z-Achse von Seite 1.
    Dreh: der Winkel von der X-Achse der Seite 1 zur X-Achse der Seite 2 um Z.
    """
    import UtilsAssembly

    seite1 = UtilsAssembly.getJcsGlobalPlc(gelenk.Placement1, gelenk.Reference1)
    seite2 = UtilsAssembly.getJcsGlobalPlc(gelenk.Placement2, gelenk.Reference2)
    z1 = seite1.Rotation.multVec(Z)
    if art == LINEAR:
        return (seite2.Base - seite1.Base).dot(z1)
    x1, x2 = seite1.Rotation.multVec(X), seite2.Rotation.multVec(X)
    return math.degrees(math.atan2(x1.cross(x2).dot(z1), x1.dot(x2)))


class Verfahren:
    """Die Stellungen der Achsen einer Assembly; `setze()` bewegt die Bauteile."""

    def __init__(self, assembly, kette=None):
        self.assembly = assembly
        self.kette = kette or kette_modul.lies_kette(assembly)
        self.achsen = list(self.kette.achsen)
        self.ausgang = {
            b: FreeCAD.Placement(b.Placement) for g in self.kette.glieder for b in g.bauteile
        }
        # Die Achsen in Koordinaten der Assembly – darin liegen die Bauteile.
        in_assembly = assembly.Placement.inverse()
        self._lage = {
            a: (in_assembly.Rotation.multVec(a.richtung), in_assembly.multVec(a.ursprung))
            for a in self.achsen
        }
        self.start = {a: gelenkstellung(a.gelenk, a.art) for a in self.achsen}
        self._vorzeichen = {a: _vorzeichen(a) for a in self.achsen}
        self.weg = dict.fromkeys(self.achsen, 0.0)  # seit dem Ausgang, in Achsrichtung
        self._platz_lage = {}  # Revolverplatz -> Lage beim Öffnen
        # Je Bauteil die Achsen vom Bett nach außen.
        self._pfad = {}
        for glied in self.kette.glieder:
            pfad = list(reversed(self.kette.pfad_zum_bett(glied)))
            for bauteil in glied.bauteile:
                self._pfad[bauteil] = pfad

    def platz_lagen(self, plaetze):
        """Wo die Plätze (Aufnahmen mit LCS) beim Öffnen lagen – Punkte in Weltkoordinaten."""
        lagen = []
        for platz in plaetze:
            if platz not in self._platz_lage:
                self._platz_lage[platz] = m.globale_platzierung(platz.Lcs).Base
            lagen.append(self._platz_lage[platz])
        return lagen

    def stellung(self, achse):
        """Die Stellung der Achse in mm bzw. Grad, gezählt wie am Gelenk."""
        return self.start[achse] + self._vorzeichen[achse] * self.weg[achse]

    def grenzen(self, achse):
        """(Minimum, Maximum) aus der Begrenzung des Gelenks; None = keine."""
        return achse.minimum, achse.maximum

    def begrenzt(self, achse, stellung):
        """Die Stellung, auf die Grenzen des Gelenks gesetzt."""
        if achse.minimum is not None:
            stellung = max(stellung, achse.minimum)
        if achse.maximum is not None:
            stellung = min(stellung, achse.maximum)
        return stellung

    def setze(self, achse, stellung, grenzen=True):
        """Fährt die Achse auf `stellung` (höchstens bis zu ihren Grenzen); gibt die Stellung zurück.

        `grenzen=False` fährt auch darüber hinaus – etwa auf Stellung 0, um die
        Führung einer schrägen Achse zu drehen (schraege_achse.drehe_fuehrung).
        """
        if grenzen:
            stellung = self.begrenzt(achse, stellung)
        self.weg[achse] = (stellung - self.start[achse]) * self._vorzeichen[achse]
        self._bewege()
        return stellung

    def setze_alle(self, stellungen):
        """Fährt mehrere Achsen auf einmal ({Achse: Stellung}), jede höchstens bis zu ihren
        Grenzen; die Bauteile bewegen sich einmal. Gibt die Achsen zurück, die an einer
        Grenze halten."""
        angehalten = []
        for achse, stellung in stellungen.items():
            ziel = self.begrenzt(achse, stellung)
            if abs(ziel - stellung) > 1e-9:
                angehalten.append(achse)
            self.weg[achse] = (ziel - self.start[achse]) * self._vorzeichen[achse]
        self._bewege()
        return angehalten

    def grundstellung(self):
        """Alle Achsen zurück in die Stellung beim Öffnen."""
        for achse in self.achsen:
            self.weg[achse] = 0.0
        self._bewege()

    def weg_bei(self, achse, stellung):
        """Der Weg seit dem Ausgang, in Achsrichtung, bei dem die Achse auf `stellung` steht."""
        return (stellung - self.start[achse]) * self._vorzeichen[achse]

    def stellung_bei(self, achse, weg):
        """Die Stellung der Achse nach `weg` seit dem Ausgang – umgekehrt zu weg_bei()."""
        return self.start[achse] + self._vorzeichen[achse] * weg

    def bewegung(self, achse, weg):
        """Die Bewegung der Achse um `weg` seit dem Ausgang, in Koordinaten der Assembly."""
        richtung, ursprung = self._lage[achse]
        if achse.art == LINEAR:
            return FreeCAD.Placement(richtung * weg, FreeCAD.Rotation())
        return FreeCAD.Placement(FreeCAD.Vector(), FreeCAD.Rotation(richtung, weg), ursprung)

    def pfad(self, glied):
        """Die Achsen vom Bett bis zu `glied`, beim Bett beginnend."""
        return list(reversed(self.kette.pfad_zum_bett(glied)))

    def _bewege(self):
        bewegung = {a: self.bewegung(a, self.weg[a]) for a in self.achsen}
        for bauteil, lage in self.ausgang.items():
            gesamt = FreeCAD.Placement()
            for achse in self._pfad.get(bauteil, []):
                gesamt = gesamt * bewegung[achse]
            neu = gesamt * lage
            if not neu.isSame(bauteil.Placement, 1e-9):
                bauteil.Placement = neu


def platzstellungen(verfahren, maschine, achse):
    """Für eine Revolverachse: [(Platzname, Stellung)] – die Stellung, in der der Platz dort steht,
    wo beim Öffnen P1 stand. Leer, wenn die Achse kein Revolver mit Plätzen ist.

    Gerechnet aus der Lage der Plätze beim Öffnen: ihr Winkel um die Achse,
    von P1 aus gezählt. Der Revolver dreht um den kürzesten Weg. Einmal vor
    dem ersten Verfahren aufrufen – dann merkt sich `verfahren` die Lagen.
    """
    if maschine is None or achse.art == LINEAR:
        return []
    revolver = next(
        (
            b
            for b in m.betriebsarten(maschine)
            if b.Art == m.ART_REVOLVER and b.Gelenk == achse.gelenk
        ),
        None,
    )
    if revolver is None:
        return []
    plaetze = m.plaetze(maschine, verfahren.kette, revolver)
    if not plaetze:
        return []
    richtung, ursprung = achse.richtung, achse.ursprung
    lagen = verfahren.platz_lagen(plaetze)

    def quer(punkt):
        """Der Punkt von der Achse aus, senkrecht zu ihr."""
        abstand = punkt - ursprung
        return abstand - richtung * abstand.dot(richtung)

    erster = quer(lagen[0])
    ergebnis = []
    for platz, lage in zip(plaetze, lagen, strict=True):
        jetzt = quer(lage)
        winkel = math.degrees(math.atan2(erster.cross(jetzt).dot(richtung), erster.dot(jetzt)))
        weg = -winkel  # so weit zurückdrehen, dann steht der Platz, wo P1 stand
        weg = (weg + 180.0) % 360.0 - 180.0
        stellung = verfahren.start[achse] + verfahren._vorzeichen[achse] * weg
        ergebnis.append((m.name_von(platz), stellung))
    return ergebnis


def plusrichtung(achse):
    """Wohin das Kind-Glied einer Linearachse fährt, wenn ihre Stellung wächst – in
    Weltkoordinaten. Das ist die Plus-Richtung der Achse, wie sie im Fenster zählt."""
    return achse.richtung * _vorzeichen(achse)


def _vorzeichen(achse):
    """+1, wenn ein Weg in Achsrichtung die Stellung am Gelenk wachsen lässt, sonst −1.

    Die Achsrichtung ist die Z-Achse der Seite am Eltern-Glied. Bewegt sich
    Seite 2, wächst die Stellung mit der Z-Achse von Seite 1; bewegt sich
    Seite 1, schrumpft sie.
    """
    import UtilsAssembly

    gelenk = achse.gelenk
    seite1 = UtilsAssembly.getJcsGlobalPlc(gelenk.Placement1, gelenk.Reference1)
    z1 = seite1.Rotation.multVec(Z)
    gleich = achse.richtung.dot(z1)
    kind_ist_seite2 = _seite_des_kinds(achse) == 2
    return 1.0 if (gleich >= 0) == kind_ist_seite2 else -1.0


def _seite_des_kinds(achse):
    """Auf welcher Seite des Gelenks (1 oder 2) das Kind-Glied hängt.

    Reference1/2 halten (Bauteil, [Element]) – wie beim Lesen der Kette.
    """
    referenz2 = achse.gelenk.Reference2
    return 2 if referenz2 and referenz2[0] in achse.kind.bauteile else 1


def fensterreihenfolge(maschine, achsen):
    """Die Achsen, wie man sie liest: Linearachsen nach Namen (X, Y, Z …), dann
    Rundachsen, die positionieren (A, B, C – auch C an der Hauptspindel), dann
    Spindeln und noch Unbenanntes, zuletzt der Revolver."""

    def schluessel(achse):
        arten = {
            b.Art
            for b in (m.betriebsarten(maschine) if maschine is not None else [])
            if b.Gelenk == achse.gelenk
        }
        if achse.art == LINEAR:
            gruppe = 0
        elif m.ART_REVOLVER in arten:
            gruppe = 3
        elif m.ART_POSITIONIEREN in arten:
            gruppe = 1
        else:
            gruppe = 2
        return gruppe, namen(maschine, achse)

    return sorted(achsen, key=schluessel)


def namen(maschine, achse):
    """Wie die Achse im Fenster heißt: die NC-Namen ihrer Betriebsarten, sonst das Gelenk."""
    if maschine is None:
        return achse.gelenk.Label
    nc = [
        b.NcName
        for b in m.betriebsarten(maschine)
        if b.Gelenk == achse.gelenk and b.NcName and b.Art != m.ART_SPINDEL
    ]
    return " / ".join(nc) if nc else achse.gelenk.Label
