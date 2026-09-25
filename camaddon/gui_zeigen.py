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


def koerper_hinter(kette, gelenk):
    """Alle Körper, die sich mit `gelenk` bewegen (auch weiter hinten in der Kette)."""
    ergebnis = []
    for glied in kette.glieder:
        if gelenk in kette.pfad_zum_festen_glied(glied):
            ergebnis += glied.koerper
    return ergebnis


class Wackeln:
    """Bewegt die Körper hinter einem Gelenk einmal hin und her."""

    def __init__(self, assembly, kette, gelenk):
        self.gelenk = gelenk
        self.koerper = koerper_hinter(kette, gelenk)
        self.vorher = {k: FreeCAD.Placement(k.Placement) for k in self.koerper}
        # Achse aus Weltkoordinaten in die der Assembly umrechnen.
        in_assembly = assembly.Placement.inverse()
        self.richtung = in_assembly.Rotation.multVec(gelenk.richtung)
        self.ursprung = in_assembly.multVec(gelenk.ursprung)
        if gelenk.art == LINEAR:
            groesse = max(
                (k.Shape.BoundBox.DiagonalLength for k in self.koerper if hasattr(k, "Shape")),
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
        if self.gelenk.art == LINEAR:
            bewegung = FreeCAD.Placement(self.richtung * wert, FreeCAD.Rotation())
        else:
            bewegung = FreeCAD.Placement(
                FreeCAD.Vector(), FreeCAD.Rotation(self.richtung, wert), self.ursprung
            )
        for koerper, lage in self.vorher.items():
            koerper.Placement = bewegung * lage

    def stopp(self):
        """Anhalten und alles exakt zurückstellen – auch mitten in der Bewegung."""
        self.uhr.stop()
        for koerper, lage in self.vorher.items():
            if koerper.Placement != lage:
                koerper.Placement = lage
