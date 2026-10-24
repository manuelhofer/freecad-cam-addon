# Prüft das Fertigteil aus dem Materialstand (W-029): Ein Block 20 × 10 × 8 im Raster 0,5 mm mit
# einer Tasche 4 tief, einem Absatz und einem Loch ganz durch – das Netz ist geschlossen, ohne
# nicht-mannigfaltige Kanten, einheitlich ausgerichtet, sein Volumen das des Rasters; der Körper
# ist ein gültiges Solid mit demselben Volumen (bis aufs Vereinfachen), mit wenigen Flächen.
# Mit Teil und Rohteil: genau das Teil plus was stehen blieb; was ins Teil schneidet, zählt
# im_teil. Ohne Material: ValueError. Die Aufspannung: 1 ohne Fertigteil im Rohteil, sonst eins
# mehr. Dazu die Stange (4 Achsen): aus den Radien ihres Abtrags ein geschlossenes Netz, der Körper
# mit dem Teil vereinigt und auf die Stange beschnitten (unten).
import math
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

# --- Die Stange (4 Achsen): aus den Radien des Abtrags ------------------------------------------
# Stange Ø 20 längs X (0 … 40), das Teil mit einer Nut 6 breit bei 15 … 21 auf r 7 rundum und einer
# Abflachung 7 von der Achse ab 30; die Stange genau aufs Teil gefräst (je Strahl sein Radius). Das Netz ist geschlossen und mannigfaltig, das
# Volumen das der Radien; der Körper mit dem Teil vereinigt und auf die Stange beschnitten ist
# gültig, das Teil liegt ganz darin, kaum mehr als das Teil (Raster), wenige Flächen, schnell.
# Nirgends ins Teil; 1 mm zu tief in der Nut zeigt im_teil_radien.
import time  # noqa: E402

from camaddon import restmaterial as rm  # noqa: E402
from camaddon import vierachs_huelle as vh  # noqa: E402

stange = rm.Stange(10.0, 0.0, 40.0)
a, phi = stange.a, stange.phi
laengs, radial = (1, 0, 0), (0, 0, 1)
welle = Part.makeCylinder(10, 40, V(0, 0, 0), V(1, 0, 0))
nut = Part.makeCylinder(10, 6, V(15, 0, 0), V(1, 0, 0)).cut(
    Part.makeCylinder(7, 6, V(15, 0, 0), V(1, 0, 0))
)
welle = welle.cut(nut).cut(Part.makeBox(10, 30, 30, V(30, -15, 7)))
stange_form = Part.makeCylinder(10, 40, V(0, 0, 0), V(1, 0, 0))
teil_r = rm.teilradien(vh.vernetze(welle), laengs, radial, stange, rm.GENAU)
# Genau aufs Teil gefräst: je Strahl der Radius des Teils.
r = np.where(np.isfinite(teil_r) & (teil_r > 0), teil_r, 10.0)
punkte, dreiecke = ft.netz_aus_radien(a, phi, r, laengs, radial)
netz_r = Mesh.Mesh()
netz_r.addFacets([[tuple(punkte[k]) for k in d] for d in dreiecke])
pruefe(netz_r.isSolid() and not netz_r.hasNonManifolds(), "Stangennetz nicht geschlossen")
pruefe(netz_r.Volume > 0, f"Stangennetz nach innen gerichtet: {netz_r.Volume}")
start = time.time()
koerper = ft.koerper_aus_radien(a, phi, r, laengs, radial, welle, teil_r, stange_form)
dauer = time.time() - start
pruefe(koerper.isValid() and len(koerper.Solids) == 1, f"Stange: {koerper.ShapeType}")
pruefe(
    abs(welle.common(koerper).Volume - welle.Volume) < 1e-4 * welle.Volume, "Welle nicht ganz darin"
)
pruefe(
    welle.Volume <= koerper.Volume < 1.005 * welle.Volume,
    f"Stange: {koerper.Volume:.0f} statt {welle.Volume:.0f} mm³",
)
pruefe(len(koerper.Faces) < 1000, f"Stange: {len(koerper.Faces)} Flächen")
pruefe(dauer < 30, f"Stange: {dauer:.1f} s")
pruefe(ft.im_teil_radien(a, phi, r, teil_r) == 0, "Stange: ins Teil")
tiefer = r.copy()
tiefer[(a > 16) & (a < 20), :] = 6.0
flaeche = ft.im_teil_radien(a, phi, tiefer, teil_r)
pruefe(
    abs(flaeche - 2 * math.pi * 7 * 3.5) < 0.1 * 2 * math.pi * 7 * 3.5,
    f"zu tief: {flaeche:.0f} mm²",
)

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
