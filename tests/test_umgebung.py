# Prüft die Testumgebung selbst: FreeCAD startet ohne Fenster, die
# CAM-Workbench lässt sich laden und Rückgängig über Transaktionen
# funktioniert – das, worauf alle späteren Prüfungen aufbauen.
import os

import FreeCAD
import Part  # noqa: F401 – lädt das Part-Modul, damit es den Objekttyp „Part::Box“ gibt
from Path.Main import Job  # noqa: F401 – der Import selbst ist die Prüfung

print("FreeCAD", ".".join(FreeCAD.Version()[:3]), FreeCAD.Version()[3])

dok = FreeCAD.newDocument("Pruefung")
dok.UndoMode = 1
dok.openTransaction("Würfel anlegen")
wuerfel = dok.addObject("Part::Box", "Wuerfel")
dok.commitTransaction()
dok.recompute()
assert dok.getObject("Wuerfel") is not None
dok.undo()
assert dok.getObject("Wuerfel") is None, "Rückgängig hat den Würfel nicht entfernt"
FreeCAD.closeDocument(dok.Name)

print("OK", os.path.basename(__file__))
