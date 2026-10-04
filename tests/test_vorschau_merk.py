# Prüft den Schlüssel, mit dem der Assistent „Bearbeitung“ seine Vorschauen über die Läufe merkt
# (gui_bearbeitung._merk_schluessel, P-2026-10-04-14): Dieselben Eingaben geben denselben
# Schlüssel; ein anderes Feld, eine andere Fläche, ein anderer Materialstand, ein anderes Werkzeug,
# ein verschobenes Teil oder Rohteil einen anderen; ein Wert, der sich nur mit seiner Adresse
# schreiben lässt, keinen (dann wird gerechnet).
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import gui_bearbeitung as ba
from camaddon import sprache
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")

import Path.Main.Job as PathJob  # noqa: E402

doc = FreeCAD.newDocument("Merk")
teil = doc.addObject("Part::Feature", "Block")
teil.Shape = Part.makeBox(40, 30, 20)
doc.recompute()
job = PathJob.Create("Job", [teil])
doc.recompute()

werkzeug = wz.standardwerkzeug()
einsatz = werkzeug.einsaetze(wz.ALLE)[0]


class Stand:
    """Ein Materialstand mit Kennung (wie materialstand.Materialstand)."""

    def __init__(self, kennung):
        self.kennung = kennung


def schluessel(werte=None, flaechen=("Face6",), stand="a", fraeser=werkzeug):
    alle = {"zustellung": 2.0, "zeilenabstand": 1.5, "vorschub": 902.0}
    alle.update(werte or {})
    alle["materialstand"] = Stand(stand)
    return ba._merk_schluessel("plan", job, fraeser, einsatz, alle, list(flaechen))


grund = schluessel()
pruefe(grund is not None, "kein Schlüssel")
pruefe(schluessel() == grund, "dieselben Eingaben, ein anderer Schlüssel")
pruefe(schluessel({"zustellung": 2.5}) != grund, "anderes Feld, derselbe Schlüssel")
pruefe(schluessel(flaechen=("Face5",)) != grund, "andere Fläche, derselbe Schlüssel")
pruefe(schluessel(stand="b") != grund, "anderer Materialstand, derselbe Schlüssel")
anders = wz.standardwerkzeug()
anders.durchmesser = 10.0
pruefe(schluessel(fraeser=anders) != grund, "anderes Werkzeug, derselbe Schlüssel")


class OhneText:
    pass


pruefe(schluessel({"etwas": OhneText()}) is None, "Wert mit Adresse gibt einen Schlüssel")

# Das Teil im Job verschoben (Nullpunkt) – und das Rohteil größer: andere Schlüssel.
from camaddon import vierachs_rohteil as vr  # noqa: E402

doc.recompute()
pruefe(schluessel() == grund, "neu berechnet ohne Änderung, ein anderer Schlüssel")
klon = vr.modell(job)
lage = klon.Placement
lage.Base = FreeCAD.Vector(5, 0, 0)
klon.Placement = lage
doc.recompute()
verschoben = schluessel()
pruefe(verschoben != grund, "Teil verschoben, derselbe Schlüssel")
job.Stock.ExtZpos = 3.0
doc.recompute()
pruefe(schluessel() != verschoben, "Rohteil größer, derselbe Schlüssel")

FreeCAD.closeDocument(doc.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
