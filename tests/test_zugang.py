# SPDX-License-Identifier: LGPL-2.1-or-later
"""Was in einer Aufspannung erreichbar ist (zugang, Frage 14): am Schwenkteil mit der Unterseite im
Spannmittel alle 27 übrigen Flächen aus drei Richtungen – oben 14 (Oberseite, vier Außenwände mit
dem Mantel, Tasche), die 30°-Schräge 10 (mit ihrer Tasche), die 45°-Fase 3 (mit der Bohrung); auf
den 5-Achs-Beispielen mit den Stellungen der Rundachsen, auf der 3-Achs-Fräse nur oben, der Rest
„Maschine schwenkt nicht so weit“. An einem Block mit Hinterschnitt: die Fläche, die nach unten
zeigt, „ins Spannmittel“; ein Absatz unter einem Überhang „keine freie Sicht“."""

import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
import Part

from camaddon import beispielmaschine as bm
from camaddon import reichweite as rw
from camaddon import schwenken, sprache
from camaddon import zugang as zg

sprache.setze_sprache("de")
V = App.Vector
doc = App.openDocument(str(ROOT / "beispiele/schwenkteil_5achs.FCStd"))
teil = doc.getObject("Schwenkteil").Shape
beginn = time.monotonic()
z = zg.zugang(teil, spannflaeche="Face6")
dauer = time.monotonic() - beginn
achsen = [tuple(round(c, 3) for c in r.achse) for r in z.richtungen]
assert achsen == [(0, 0, 1), (0, -0.5, 0.866), (0.707, 0, 0.707)], achsen
assert [len(r.flaechen) for r in z.richtungen] == [14, 10, 3], [r.flaechen for r in z.richtungen]
assert not z.unerreichbar, z.unerreichbar
assert z.richtung_von("Face13") is z.richtungen[2] and z.richtung_von("Face6") is None
# Senkrechte Außenwände fräst der Mantel von oben, kein Schwenk.
assert {"Face1", "Face2", "Face5", "Face7"} <= set(z.richtungen[0].flaechen)
assert [round(r.neigung) for r in z.richtungen] == [0, 30, 45]
assert dauer < 5, dauer

# Auf den Beispielmaschinen: die Stellungen, wie die Steuerung sie zeigt.
erwartet = {
    bm.TISCH_TISCH: [{"A": 0, "C": 0}, {"A": 30, "C": 0}, {"A": 45, "C": 90}],
    bm.GROB_G550: [{"A": -90, "B": 0}, {"A": -60, "B": 0}, {"A": -45, "B": 90}],
}
for art, soll in erwartet.items():
    asm, ma = bm.BAUPLAENE[art]()
    p = rw.Pruefung(asm, ma)
    m = schwenken.Maschine(p, p.werkzeugaufnahme(1), 125.0, (0, 0, 0))
    mit = zg.zugang(teil, spannflaeche="Face6", maschine=m)
    ist = [{b: round(w) for b, w in r.stellung.items()} for r in mit.richtungen]
    assert ist == soll, (art, ist)
    App.closeDocument(asm.Document.Name)
asm, ma = bm.fraesmaschine()
p = rw.Pruefung(asm, ma)
drei = zg.zugang(
    teil,
    spannflaeche="Face6",
    maschine=schwenken.Maschine(p, p.werkzeugaufnahme(1), 125.0, (0, 0, 0)),
)
assert len(drei.richtungen) == 1 and len(drei.richtungen[0].flaechen) == 14
assert len(drei.unerreichbar) == 13 and set(drei.unerreichbar.values()) == {
    sprache.tr("zg.grund.maschine")
}, drei.unerreichbar
App.closeDocument(asm.Document.Name)

# Ein Block 60 × 40 × 30 mit einem Überhang: von oben eine Stufe, darunter seitlich eine Nut, deren
# Decke nach unten zeigt (ins Spannmittel) und deren Boden unter dem Dach liegt (keine Sicht von oben,
# aber von der Seite).
block = Part.makeBox(60, 40, 30)
nut = Part.makeBox(
    20, 20, 8, V(40, 10, 10)
)  # an der Seite x 40 … 60, y 10 … 30, z 10 … 18: nur +X offen
form = block.cut(nut).removeSplitter()
z2 = zg.zugang(
    form,
    spannflaeche=next(
        f"Face{i + 1}"
        for i, f in enumerate(form.Faces)
        if f.Surface.__class__.__name__ == "Plane"
        and f.normalAt(0, 0).z < -0.99
        and abs(f.CenterOfMass.z) < 1e-6
    ),
)
decke = next(
    f"Face{i + 1}"
    for i, f in enumerate(form.Faces)
    if abs(f.CenterOfMass.z - 18) < 1e-6 and f.normalAt(0, 0).z < -0.99
)
boden = next(
    f"Face{i + 1}"
    for i, f in enumerate(form.Faces)
    if abs(f.CenterOfMass.z - 10) < 1e-6 and f.normalAt(0, 0).z > 0.99
)
# Der Nutboden liegt unter dem Dach: von oben keine Sicht – von der Seite (+X) fräst ihn der Mantel.
r_boden = z2.richtung_von(boden)
assert r_boden is not None and tuple(round(c, 3) for c in r_boden.achse) == (1, 0, 0), (r_boden, z2)
# Die Decke der Nut zeigt nach unten: von +X fräst sie auch der Mantel – erreichbar.
assert z2.richtung_von(decke) is not None, z2
# Ein Hinterschnitt, den keine Richtung erreicht: eine Tasche in der Decke der Nut (nach oben).
form3 = form.cut(Part.makeBox(6, 6, 3, V(48, 17, 18)))
z3 = zg.zugang(
    form3,
    spannflaeche="Face"
    + str(
        1
        + next(
            i
            for i, f in enumerate(form3.Faces)
            if f.Surface.__class__.__name__ == "Plane"
            and f.normalAt(0, 0).z < -0.99
            and abs(f.CenterOfMass.z) < 1e-6
        )
    ),
)
taschenboden = next(
    f"Face{i + 1}"
    for i, f in enumerate(form3.Faces)
    if abs(f.CenterOfMass.z - 21) < 1e-6 and f.normalAt(0, 0).z < -0.99
)
assert z3.unerreichbar.get(taschenboden) == sprache.tr("zg.grund.spannmittel"), z3.unerreichbar
# Rundungen am Boden einer Tasche (R 3, Achse waagerecht): Von oben nimmt sie ein Kugel- oder
# Torusfräser – bis 0.329 hieß es „Keine freie Sicht“, weil nur längs der Achse gesucht wurde, und
# dort stehen die Wände. Eine Querbohrung (Achse waagerecht, Normalen rundum) bleibt von oben nichts.
rund = Part.makeBox(100, 80, 40).cut(Part.makeBox(60, 40, 15, V(20, 20, 25)))
kanten = [
    e for e in rund.Edges if abs(e.BoundBox.ZMax - 25) < 1e-6 and abs(e.BoundBox.ZMin - 25) < 1e-6
]
rund = rund.makeFillet(3, kanten)
quer = Part.makeCylinder(4, 100, V(0, 10, 10), V(1, 0, 0))
rund = rund.cut(quer)
z4 = zg.ohne_schwenken(zg.zugang(rund, spannflaeche=zg.spannflaeche_unten(rund)))
rundungen = [
    f"Face{i + 1}"
    for i, f in enumerate(rund.Faces)
    if f.Surface.__class__.__name__ == "Cylinder" and abs(f.Surface.Radius - 3) < 1e-6
]
bohrung = next(
    f"Face{i + 1}"
    for i, f in enumerate(rund.Faces)
    if f.Surface.__class__.__name__ == "Cylinder" and abs(f.Surface.Radius - 4) < 1e-6
)
assert len(rundungen) == 4, rundungen
oben4 = z4.richtung_von(rundungen[0])
assert all(z4.richtung_von(r) is oben4 for r in rundungen) and oben4 is not None, z4.unerreichbar
assert tuple(round(c, 3) for c in oben4.achse) == (0, 0, 1), oben4
assert bohrung in z4.unerreichbar, z4
print(f"Schwenkteil {dauer:.2f} s")
print("OK", os.path.basename(__file__))
