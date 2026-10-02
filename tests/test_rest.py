# Prüft „Restmaterial“ (W-006 4.1 Punkt 5): Was der Standardfräser Ø 12 in den Ecken einer
# Tasche stehen ließ, holt ein Ø 4. Block 60 × 40 × 20 mit einer Tasche 30 × 20 × 10 mit scharfen
# Ecken bei (15…45, 10…30). Die Maske (nur, wo der Kreis des kleinen aus jedem Kreis des großen
# ragt: vier Stücke an den Ecken, die Mitten der Seiten nicht), die Bahn (vier Läufe je Lage, zwei
# Lagen bei ap 5), im Quader: nach dem großen steht in der Ecke R 6, nach dem kleinen R 2, der
# Boden bleibt bei 10, nichts im Teil; die Fehler (der davor nicht größer, nirgends Rest) mit
# einem Satz; die Operation „Restmaterial T3“ im Job.
import math
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import fraeserform as ff
from camaddon import job_schnittwerte as js
from camaddon import kontur as ko
from camaddon import kontur_bahn as kb
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_bahn as vb
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
gross = wz.standardwerkzeug()
klein = wz.Werkzeug(nummer=3, name="VHM 4", durchmesser=4.0, schneiden=3, schneidenlaenge=12.0)
klein.schnittwerte[wz.ALLE] = [
    wz.Einsatz(art=wz.SCHLICHTEN, ae=0.2, ap=12.0, vc=120.0, fz=0.02),
]

teil = Part.makeBox(60, 40, 20).cut(Part.makeBox(30, 20, 10, V(15, 10, 10))).removeSplitter()
waende = [
    f"Face{i + 1}"
    for i, f in enumerate(teil.Faces)
    if f.BoundBox.ZMax - f.BoundBox.ZMin > 1e-6 and f.BoundBox.ZMin > 9.9
]
pruefe(len(waende) == 4, f"Wände der Tasche: {waende}")
ecken = [(15.0, 10.0), (45.0, 10.0), (45.0, 30.0), (15.0, 30.0)]

# --- Die Maske ----------------------------------------------------------------------------------
kontur = kb.konturen(teil, waende)[0]
nur_wo = kb.nur_wo_der_grosse_nicht_hinkam(6.0, 2.0, 0.01, 0.5)
_seg, proben = kb._versatz(kontur, 2.0, 0.01, 0.5)
maske = nur_wo(kontur, proben.x, proben.y)
erste_luecke = int(np.flatnonzero(~maske)[0])
stuecke = vb._stuecke(np.roll(maske, -erste_luecke))
pruefe(len(stuecke) == 4, f"Stücke an den Ecken: {len(stuecke)}")
zur_ecke = [
    min(math.hypot(x - ex, y - ey) for ex, ey in ecken)
    for x, y in zip(proben.x[maske], proben.y[maske], strict=True)
]
# Der kleine fährt von seiner Ecke (2, 2) bis dorthin, wo der große die Wand berührt (4 mm
# weiter), dazu 2 mm zum Anschließen – höchstens hypot(8, 2) von der Ecke.
pruefe(max(zur_ecke) < math.hypot(8.0, 2.0) + 0.6, f"Maske zu weit: {max(zur_ecke):.2f}")
mitten = [(30.0, 12.0), (43.0, 20.0), (30.0, 28.0), (17.0, 20.0)]
for mx, my in mitten:
    i = int(np.argmin(np.hypot(proben.x - mx, proben.y - my)))
    pruefe(not maske[i], f"Mitte der Seite bei ({mx}, {my}) in der Maske")

# --- Job, Bahnen ------------------------------------------------------------------------------
import Path.Main.Job as PathJob

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([gross, klein]))
doc = FreeCAD.newDocument("Rest")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
form_gross, form_klein = ff.von_werkzeug(gross), ff.von_werkzeug(klein)
schruppen = next(e for e in gross.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
bahn_gross = ko.bahn_fuer(
    job, job.Model.Group, form_gross, schruppen.ap, schruppen.ae, 0.0, True, waende
)
bahn_rest = ko.bahn_fuer(
    job, job.Model.Group, form_klein, 5.0, 2.0, 0.0, False, waende, breite=0.01, radius_davor=6.0
)
pruefe(
    (bahn_rest.lagen, bahn_rest.bahnen) == (2, 8),
    f"Rest: {bahn_rest.lagen} Lagen, {bahn_rest.bahnen} Läufe",
)
print(f"Rest: {bahn_rest.bahnen} Laeufe, {bahn_rest.laenge:.0f} mm im Vorschub")

# --- Im Quader ----------------------------------------------------------------------------------
quader = rm.Quader(0, 60, 0, 40, 0, 20, schritt=0.1)


def fahre(bahn, form):
    for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        quader.fahre((a.x, a.y, a.z), (b.x, b.y, b.z), form)


def hoehe(x, y):
    i = int(np.argmin(np.abs(quader.x - x)))
    j = int(np.argmin(np.abs(quader.y - y)))
    return float(quader.h[i, j])


fahre(bahn_gross, form_gross)
pruefe(abs(hoehe(15.8, 10.8) - 20.0) < 0.05, f"nach dem großen: {hoehe(15.8, 10.8):.2f}")
pruefe(abs(hoehe(30.0, 20.0) - 10.0) < 0.05, f"Boden nach dem großen: {hoehe(30.0, 20.0):.2f}")
fahre(bahn_rest, form_klein)
for ex, ey in ecken:
    sx = 1.0 if ex < 30 else -1.0
    sy = 1.0 if ey < 20 else -1.0
    weg = hoehe(ex + sx * 0.8, ey + sy * 0.8)
    bleibt = hoehe(ex + sx * 0.3, ey + sy * 0.3)
    pruefe(abs(weg - 10.0) < 0.05, f"Ecke {ex, ey}: 0,8 neben der Ecke noch {weg:.2f}")
    pruefe(abs(bleibt - 20.0) < 0.05, f"Ecke {ex, ey}: R 2 bleibt nicht ({bleibt:.2f})")
im_teil = (quader.x[:, None] < 14.9) | (quader.x[:, None] > 45.1)
im_teil = im_teil | (quader.y[None, :] < 9.9) | (quader.y[None, :] > 30.1)
pruefe(float(quader.h[im_teil].min()) > 20.0 - 1e-6, "ins Teil außerhalb der Tasche")
pruefe(float(quader.h.min()) > 10.0 - 1e-6, f"unter den Boden: {quader.h.min():.2f}")

# --- Fehler -------------------------------------------------------------------------------------
for davor, satzteil in ((2.0, "größer sein"), (4.0, None)):
    try:
        ko.bahn_fuer(
            job,
            job.Model.Group,
            form_klein,
            5.0,
            2.0,
            0.0,
            False,
            waende,
            breite=0.01,
            radius_davor=davor,
        )
    except ValueError as grund:
        pruefe(satzteil is not None and satzteil in str(grund), f"davor {davor}: {grund}")
    else:
        pruefe(satzteil is None, f"davor {davor}: keine Fehlermeldung")
aussen = [
    f"Face{i + 1}"
    for i, f in enumerate(teil.Faces)
    if f.BoundBox.ZMax - f.BoundBox.ZMin > 1e-6 and f.BoundBox.ZMin < 0.1
]
try:
    ko.bahn_fuer(
        job, job.Model.Group, form_klein, 5.0, 2.0, 0.0, False, aussen, breite=0.01, radius_davor=6
    )
except ValueError as grund:
    pruefe("überall hin" in str(grund), f"außen: {grund}")
else:
    pruefe(False, "außen: keine Fehlermeldung (Ecken außen lassen nichts stehen)")

# --- Die Operation im Job -----------------------------------------------------------------------
tc = js.controller_ohne_transaktion(doc, job, klein, klein.schnittwerte[wz.ALLE][0])
doc.recompute()
op = ko.lege_an(job, tc, 5.0, 2.0, 0.0, False, 0.01, flaechen=waende, radius_davor=6.0)
doc.recompute()
pruefe(op.Label == "Restmaterial T3" and ko.ist_rest(op), f"{op.Label}")
pruefe((op.Lagen, op.Bahnen) == (2, 8), f"Operation: {op.Lagen} Lagen, {op.Bahnen} Läufe")
pruefe(js.operationsart(op) == "kontur", f"Art {js.operationsart(op)}")
print(ascii(f"Operation: {len(op.Path.Commands)} Befehle"))

# --- Gezeichnete Rundungen innen (P-2026-10-02-19): danach hakt der Assistent „Restmaterial“ an.
# Eine Tasche 50 × 30 × 10 mit den senkrechten Ecken R 4: vier Rundungen innen; ein Zapfen mit
# denselben Ecken: außen, keine; eine Bohrung Ø 8: ganz rund, keine.
tasche = Part.makeBox(50, 30, 10, V(25, 15, -10))
senkrecht = [k for k in tasche.Edges if abs(k.BoundBox.ZMax - k.BoundBox.ZMin) > 1]
platte = Part.makeBox(100, 60, 20, V(0, 0, -20)).cut(tasche.makeFillet(4, senkrecht))
platte = platte.cut(Part.makeCylinder(4, 20, V(10, 10, -20))).removeSplitter()
alle = [f"Face{i + 1}" for i in range(len(platte.Faces))]
innen = kb.innenrundungen(platte, alle)
pruefe(
    len(innen) == 4 and all(abs(r - 4.0) < 1e-6 for _n, r in innen),
    f"Tasche mit R 4: {innen}",
)
zapfen = Part.makeBox(100, 60, 20, V(0, 0, -20)).fuse(
    tasche.makeFillet(4, senkrecht).translate(V(0, 0, 10))
)
zapfen = zapfen.removeSplitter()
aussen = kb.innenrundungen(zapfen, [f"Face{i + 1}" for i in range(len(zapfen.Faces))])
pruefe(aussen == [], f"Zapfen mit R 4: {aussen}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
