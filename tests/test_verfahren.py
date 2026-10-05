# Prüft „Maschine verfahren“ (verfahren.py) an den Beispielmaschinen: Stellung
# gezählt wie am Gelenk – C4 der Drehmaschine wie an der Steuerung nach DIN 66217, gegen ihr
# Gelenk: +90° drehen das Futter am Gelenk um −90° –, Grenzen, mehrere Achsen hintereinander (auch C auf
# der Schwenkbrücke A), die Stellung bleibt beim Neuberechnen, die
# Grundstellung ist exakt – und ein Gelenk, dessen bewegtes Teil auf Seite 1
# steht, zählt trotzdem richtig herum.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)
sys.path.insert(0, os.path.join(ADDON, "tests"))

import beispielmaschinen
import FreeCAD

from camaddon import maschine as m
from camaddon import verfahren as vf

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nahe(a, b, genau=1e-6):
    return abs(a - b) < genau


def stellungen(achsen):
    return {name: vf.gelenkstellung(a.gelenk, a.art) for name, a in achsen.items()}


# --- Drehmaschine: C4, Z1, X1 (0 … 200 mm), T -----------------------------------
asm, ma = beispielmaschinen.drehmaschine_komplett()
doc = asm.Document
v = vf.Verfahren(asm)
achsen = {vf.namen(ma, a): a for a in v.achsen}
pruefe(sorted(achsen) == ["C4", "T", "X1", "Z1"], f"Namen: {sorted(achsen)}")
# Im Fenster: erst die Linearachsen nach Namen, dann C, zuletzt der Revolver.
reihe = [vf.namen(ma, a) for a in vf.fensterreihenfolge(ma, v.achsen)]
pruefe(reihe == ["X1", "Z1", "C4", "T"], f"Reihenfolge im Fenster: {reihe}")
x, z, c, t = (achsen[n] for n in ("X1", "Z1", "C4", "T"))
pruefe(v.grenzen(x) == (0.0, 200.0) and v.grenzen(c) == (None, None), "Grenzen")

revolver = doc.getObject("Revolver")
futter = doc.getObject("Futter")
revolver_vorher = FreeCAD.Placement(revolver.Placement)
futter_vorher = FreeCAD.Placement(futter.Placement)
pruefe(v.setze(x, 150) == 150, "X1 auf 150")
weg = (revolver.Placement.Base - revolver_vorher.Base).dot(x.richtung)
pruefe(nahe(weg, 150), f"Der Revolver fährt nicht mit X1: {weg}")
pruefe(v.setze(x, 500) == 200, "X1 über die Grenze")
pruefe(nahe(vf.gelenkstellung(x.gelenk, x.art), 200), "X1 steht nicht auf 200")
pruefe(v.setze(x, -20) == 0, "X1 unter die Grenze")

soll = {"X1": 120, "Z1": 80, "T": 45, "C4": 90}
for name, wert in soll.items():
    v.setze(achsen[name], wert)
pruefe(nahe(v.stellung(c), 90), f"C4 im Fenster: {v.stellung(c)}")
soll["C4"] = -90  # am Gelenk
ist = stellungen(achsen)
pruefe(all(nahe(ist[n], s) for n, s in soll.items()), f"mehrere Achsen: {ist}")
drehung = futter.Placement.Rotation.multiply(futter_vorher.Rotation.inverted())
gedreht = math.degrees(drehung.Angle) * (1 if drehung.Axis.dot(c.richtung) > 0 else -1)
gedreht = (gedreht + 180.0) % 360.0 - 180.0
pruefe(nahe(gedreht, -90), f"Futter um die Achse gedreht um {gedreht}")

# Die Assembly lässt die Stellung stehen.
asm.solve()
doc.recompute()
ist = stellungen(achsen)
pruefe(all(nahe(ist[n], s) for n, s in soll.items()), f"nach dem Neuberechnen: {ist}")

v.grundstellung()
pruefe(
    all(b.Placement.isSame(lage, 1e-9) for b, lage in v.ausgang.items()),
    "Grundstellung nicht exakt",
)

# Revolver: Platz P4 an die Stelle von P1 – 12 Plätze, also 90° zurück.
plaetze = vf.platzstellungen(v, ma, t)
pruefe([n for n, _s in plaetze] == [f"P{i}" for i in range(1, 13)], f"Plätze: {plaetze}")
pruefe(vf.platzstellungen(v, ma, x) == [], "Linearachse mit Plätzen")
if len(plaetze) == 12:
    pruefe(nahe(plaetze[0][1], v.stellung(t)), f"P1: {plaetze[0][1]}")
    pruefe(nahe(abs(plaetze[3][1] - v.stellung(t)), 90), f"P4: {plaetze[3][1]}")
    revolver_ba = next(b for b in m.betriebsarten(ma) if b.Art == m.ART_REVOLVER)
    aufnahmen = m.plaetze(ma, v.kette, revolver_ba)
    p1_vorher = m.globale_platzierung(aufnahmen[0].Lcs).Base
    v.setze(t, plaetze[3][1])
    p4_jetzt = m.globale_platzierung(aufnahmen[3].Lcs).Base
    pruefe(p4_jetzt.distanceToPoint(p1_vorher) < 1e-6, f"P4 steht nicht, wo P1 stand: {p4_jetzt}")
    v.grundstellung()
FreeCAD.closeDocument(doc.Name)

# --- Fünfachser: C sitzt auf der Wiege A ---------------------------------------
asm5 = beispielmaschinen.fuenfachser(zweites_lager=False)
v5 = vf.Verfahren(asm5)
achsen5 = {a.gelenk.Label: a for a in v5.achsen}
pruefe({"A", "C", "Z", "S"} <= set(achsen5), f"Achsen Fünfachser: {sorted(achsen5)}")
v5.setze(achsen5["C"], 45)
v5.setze(achsen5["A"], 30)
ist = stellungen(achsen5)
pruefe(nahe(ist["C"], 45) and nahe(ist["A"], 30), f"A 30°, C 45°: {ist}")
v5.setze(achsen5["A"], -30)
ist = stellungen(achsen5)
pruefe(nahe(ist["C"], 45) and nahe(ist["A"], -30), f"A −30°, C 45°: {ist}")
FreeCAD.closeDocument(asm5.Document.Name)

# --- Bewegtes Teil auf Seite 1 des Gelenks --------------------------------------
b = beispielmaschinen.Baukasten("SeiteEins")
bett = b.quader("Bett", 300, 100, 20)
tisch = b.quader("Tisch", 100, 100, 20, z=20)
b.fixieren(bett)
gelenk = b.gelenk("Y", "Slider", tisch, "Face5", bett, "Face6")
asm1 = b.fertig()
v1 = vf.Verfahren(asm1)
pruefe(len(v1.achsen) == 1, f"{len(v1.achsen)} Achsen statt 1")
if v1.achsen:
    y = v1.achsen[0]
    start = v1.stellung(y)
    v1.setze(y, start + 25)
    stellung = vf.gelenkstellung(gelenk, y.art)
    pruefe(nahe(stellung, start + 25), f"Seite 1: {stellung} statt {start + 25}")
    pruefe(vf.namen(None, y) == "Y", "ohne Maschine: Name des Gelenks")
FreeCAD.closeDocument(asm1.Document.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
