# SPDX-License-Identifier: LGPL-2.1-or-later
"""Zeigen, welches Teil gemeint ist (Spezifikation W-001, Abschnitt 11).

Fährt man im Dialog über eine Zeile, leuchtet das Teil in der 3D-Ansicht auf;
bei einem Gelenk bewegt sich außerdem alles, was an ihm hängt, einmal kurz
hin und her – so sieht man Achse und Richtung, ohne etwas zu verstellen.
Danach steht alles wieder exakt wie vorher.
"""

import math

import FreeCAD
import FreeCADGui
from PySide import QtCore

from .kette import LINEAR

# Wie weit und wie lange gewackelt wird.
WINKEL = 15.0  # Grad
WEG_ANTEIL = 0.1  # Anteil der Größe des bewegten Glieds
WEG_MIN, WEG_MAX = 5.0, 50.0  # mm
DAUER_MS = 700
SCHRITTE = 20


def hervorheben(objekte):
    """Markiert die Objekte in der 3D-Ansicht (über die Auswahl)."""
    FreeCADGui.Selection.clearSelection()
    for objekt in objekte:
        if objekt is not None:
            FreeCADGui.Selection.addSelection(objekt)


def bauteile_hinter(kette, achse):
    """Alle Bauteile, die sich mit `achse` bewegen – auch die weiter außen in der Kette."""
    ergebnis = []
    for glied in kette.glieder:
        if achse in kette.pfad_zum_bett(glied):
            ergebnis += glied.bauteile
    return ergebnis


class Wackeln:
    """Bewegt die Bauteile hinter einer Achse einmal hin und her."""

    def __init__(self, assembly, kette, achse):
        self.achse = achse
        self.bauteile = bauteile_hinter(kette, achse)
        self.vorher = {b: FreeCAD.Placement(b.Placement) for b in self.bauteile}
        # Achse aus Weltkoordinaten in die der Assembly umrechnen.
        in_assembly = assembly.Placement.inverse()
        self.richtung = in_assembly.Rotation.multVec(achse.richtung)
        self.ursprung = in_assembly.multVec(achse.ursprung)
        if achse.art == LINEAR:
            groesse = max(
                (b.Shape.BoundBox.DiagonalLength for b in self.bauteile if hasattr(b, "Shape")),
                default=100.0,
            )
            self.weite = min(max(groesse * WEG_ANTEIL, WEG_MIN), WEG_MAX)
        else:
            self.weite = WINKEL
        self.schritt = 0
        self.uhr = QtCore.QTimer()
        self.uhr.setInterval(DAUER_MS // SCHRITTE)
        self.uhr.timeout.connect(self._weiter)

    def start(self):
        self.uhr.start()

    def laeuft(self):
        return self.uhr.isActive()

    def _weiter(self):
        self.schritt += 1
        if self.schritt >= SCHRITTE:
            self.stopp()
            return
        wert = self.weite * math.sin(2 * math.pi * self.schritt / SCHRITTE)
        if self.achse.art == LINEAR:
            bewegung = FreeCAD.Placement(self.richtung * wert, FreeCAD.Rotation())
        else:
            bewegung = FreeCAD.Placement(
                FreeCAD.Vector(), FreeCAD.Rotation(self.richtung, wert), self.ursprung
            )
        for bauteil, lage in self.vorher.items():
            bauteil.Placement = bewegung * lage

    def stopp(self):
        """Anhalten und alles exakt zurückstellen – auch mitten in der Bewegung."""
        self.uhr.stop()
        for bauteil, lage in self.vorher.items():
            if bauteil.Placement != lage:
                bauteil.Placement = lage
