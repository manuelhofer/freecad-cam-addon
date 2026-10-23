# Prüft das Fertigteil aus dem Materialstand (W-029): Ein Block 20 × 10 × 8 im Raster 0,5 mm mit
# einer Tasche 4 tief, einem Absatz und einem Loch ganz durch – das Netz ist geschlossen, ohne
# nicht-mannigfaltige Kanten, einheitlich ausgerichtet, sein Volumen das des Rasters; der Körper
# ist ein gültiges Solid mit demselben Volumen (bis aufs Vereinfachen), mit wenigen Flächen.
# Mit Teil und Rohteil: genau das Teil plus was stehen blieb; was ins Teil schneidet, zählt
# im_teil. Ohne Material: ValueError. Die Aufspannung: 1 ohne Fertigteil im Rohteil, sonst eins
# mehr.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import Mesh
import numpy as np

from camaddon import fertigteil as ft
from camaddon import sprache

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")

schritt = 0.5
x = 0.25 + schritt * np.arange(40)  # 0 … 20
y = 0.25 + schritt * np.arange(20)  # 0 … 10
h = np.full((40, 20), 8.0)
h[8:20, 4:16] = 4.0  # Tasche 6 × 6, 4 tief
h[28:40, :] = 6.0  # Absatz am Ende, 2 tiefer
h[30:32, 8:10] = -np.inf  # ein Loch ganz durch
unten = 0.0
punkte, dreiecke = ft.netz_aus_hoehen(x, y, h, unten)
netz = Mesh.Mesh()
netz.addFacets([[tuple(punkte[k]) for k in d] for d in dreiecke])
material = np.isfinite(h) & (h > unten)
soll = float(np.sum(np.where(material, h - unten, 0.0))) * schritt * schritt
pruefe(netz.isSolid(), "Netz nicht geschlossen")
pruefe(not netz.hasNonManifolds(), "Netz nicht mannigfaltig")
pruefe(netz.countNonUniformOrientedFacets() == 0, "Dreiecke uneinheitlich ausgerichtet")
pruefe(abs(netz.Volume - soll) < 1e-6 * soll, f"Netz-Volumen {netz.Volume} statt {soll}")

form = ft.koerper_aus_hoehen(x, y, h, unten)
pruefe(form.ShapeType == "Solid" and form.isValid(), f"Körper: {form.ShapeType}")
pruefe(
    abs(form.Volume - soll) <= ft.VOLUMEN_SPIEL * soll + 1e-6,
    f"Körper-Volumen {form.Volume} statt {soll}",
)
# Oben 3 Höhen, unten der Boden, außen 6 Seiten (2 Stufen), Tasche 4 Wände, Loch 4 Wände, Absatz:
# Die Flächen sind zusammengefasst – kein Dreieck je Zelle.
pruefe(len(form.Faces) < 40, f"{len(form.Faces)} Flächen – nicht zusammengefasst")
bb = form.BoundBox
pruefe(
    abs(bb.XMin) < 1e-6 and abs(bb.XMax - 20) < 1e-6 and abs(bb.ZMax - 8) < 1e-6,
    f"Lage: {bb}",
)

# Mit dem Teil und dem Rohteil: Das Teil ist der Block mit der Tasche (ohne Absatz und Loch),
# stehen geblieben ist über ihm ein Streifen 1 mm (x 18 … 20, bis 9) – das Fertigteil ist das
# Teil plus dieser Streifen, genau (keine halben Zellen an den Wänden), mit wenigen Flächen, im
# Rohteil 20 × 10 × 9. An keiner Stelle schneidet etwas ins Teil; fehlt in der Tasche 1 mm, sagt
# im_teil es (die Ränder nicht mitgezählt).
import FreeCAD  # noqa: E402
import Part  # noqa: E402

V = FreeCAD.Vector
teil = Part.makeBox(20, 10, 8).cut(Part.makeBox(6, 6, 4, V(4, 2, 4))).removeSplitter()
rohteil = Part.makeBox(20, 10, 9)
h2 = np.full((40, 20), 8.0)
h2[8:20, 4:16] = 4.0
h2[36:40, :] = 9.0
form2 = ft.koerper_aus_hoehen(x, y, h2, unten, teil, rohteil)
soll2 = teil.Volume + 2 * 10 * 1
pruefe(form2.isValid() and len(form2.Solids) == 1, f"mit Teil: {form2.ShapeType}")
pruefe(abs(form2.Volume - soll2) < 1e-3 * soll2, f"mit Teil: Volumen {form2.Volume} statt {soll2}")
pruefe(abs(teil.common(form2).Volume - teil.Volume) < 1e-6 * teil.Volume, "Teil nicht ganz darin")
pruefe(len(form2.Faces) <= 16, f"mit Teil: {len(form2.Faces)} Flächen")
pruefe(ft.im_teil(x, y, h2, teil) == 0, f"im Teil: {ft.im_teil(x, y, h2, teil)}")
h3 = h2.copy()
h3[10:18, 6:14] = 3.0  # die Tasche 1 mm zu tief
pruefe(ft.im_teil(x, y, h3, teil) == 8 * 8, f"zu tief: {ft.im_teil(x, y, h3, teil)} Zellen")

try:
    ft.koerper_aus_hoehen(x, y, np.full((40, 20), -np.inf), unten)
    pruefe(False, "ohne Material kein Fehler")
except ValueError as f:
    pruefe("kein Fertigteil" in str(f), f"Fehlertext: {f}")


class _Ding:
    def __init__(self, **werte):
        self.__dict__.update(werte)


pruefe(ft.aufspannung(_Ding(Stock=_Ding(Objects=[]))) == 1, "ohne Körper im Rohteil")
pruefe(ft.aufspannung(_Ding(Stock=None)) == 1, "ohne Rohteil")
fertig1 = _Ding(Aufspannung=1)
pruefe(ft.aufspannung(_Ding(Stock=_Ding(Objects=[fertig1]))) == 2, "nach Aufspannung 1")
pruefe(ft.aufspannung(_Ding(Stock=_Ding(Objects=[_Ding()]))) == 1, "ein anderer Körper")
pruefe(ft._dateiname('Ring: "A/B" – Aufspannung 1.') == "Ring_ _A_B_ – Aufspannung 1", "Dateiname")

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
