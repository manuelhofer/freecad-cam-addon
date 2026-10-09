# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Auflösung einer Operation: das Raster (mm), in dem sie ihre Bahn rechnet (T-009).

Jede Strategie hat dafür einen festen Vorschlag – das Raster der Hüllfläche, der Schritt längs
der Zeilen (Räumen, Kontur, Entgraten, 3D-Schruppen 0,5 mm; Planfräsen und Bleistift 0,25 mm;
3D-Schlichten 0,2 mm längs der Zeile). Feiner ist genauer und dauert länger, gröber schneller. Manuel, 2026-10-09:
„die Auflösung bei jeder Strategie einstellbar … in mm, immer mit verständlicher Erklärung“.
Darum trägt jede dieser Operationen die Eigenschaft `Raster` (0: der Vorschlag) – im Assistenten
„Bearbeitung“ das Feld „Auflösung“ je Block, im Eigenschaftseditor direkt. Läuft ohne Oberfläche.
"""

from .sprache import tr

EIGENSCHAFT = "Raster"


def eigenschaft(obj, gruppe):
    """Legt die Eigenschaft `Raster` an, wenn sie fehlt (ältere Dokumente); 0 = Vorschlag."""
    if EIGENSCHAFT not in obj.PropertiesList:
        obj.addProperty("App::PropertyLength", EIGENSCHAFT, gruppe, tr("au.eigenschaft.raster"))
        setattr(obj, EIGENSCHAFT, 0.0)
        return True
    return False


def wert(obj, vorgabe):
    """Das Raster der Operation (mm): ihr `Raster`, wenn > 0, sonst `vorgabe`."""
    eigen = float(getattr(obj, EIGENSCHAFT, 0.0) or 0.0)
    return eigen if eigen > 0 else vorgabe


def setze(obj, raster):
    """Schreibt das Raster (0 oder None: der Vorschlag) an die Operation, wenn sie eins hat."""
    if EIGENSCHAFT in obj.PropertiesList:
        setattr(obj, EIGENSCHAFT, float(raster or 0.0))
