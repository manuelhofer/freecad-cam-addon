# Prüft das Messen eines Halters aus einer CAD-Datei (W-022 Punkt 3, halter_datei.py): Ein
# Drehkörper wie ein ER32-Futter an SK40 – Steilkegel, Flansch mit V-Rille, Stufe zum Körper,
# Mutter mit Fase – als STEP und als STL, einmal längs Z, einmal längs X und außer der Mitte.
# Gemessen ab der Spindelnase (der Plananlage des Flanschs): die Abschnitte wie gebaut, auf 0,15 mm
# genau; die Stufe zum Körper bleibt eine Stufe, kein Kegel über einen Schritt.
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402
import Mesh  # noqa: E402
import Part  # noqa: E402

from camaddon import halter_datei as hd  # noqa: E402

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


# (r, z) – der Steilkegel 0 … 68, ab 68 der Flansch (Ø 63, V-Rille bis Ø 56), ab 84 der Körper
# Ø 50, die Mutter vorn mit 1,5 mm Fase; vorn bei 131,5.
UMRISS = [
    (0, 0), (12, 0), (22, 68), (31.5, 68), (31.5, 74), (28, 76), (31.5, 78), (31.5, 84),
    (25, 84), (25, 130), (23.5, 131.5), (0, 131.5),
]  # fmt: skip
ERWARTET = [(6, 63, 63), (2, 63, 56), (2, 56, 63), (6, 63, 63), (46, 50, 50), (1.5, 50, 47)]


def drehkoerper(lage):
    punkte = [FreeCAD.Vector(r, 0, z) for r, z in UMRISS] + [FreeCAD.Vector(0, 0, 0)]
    flaeche = Part.Face(Part.makePolygon(punkte))
    koerper = flaeche.revolve(FreeCAD.Vector(), FreeCAD.Vector(0, 0, 1), 360)
    return koerper.transformGeometry(lage.toMatrix()) if lage else koerper


def nahe(a, b, toleranz):
    return abs(a - b) <= toleranz


ordner = tempfile.mkdtemp()
quer = FreeCAD.Placement(FreeCAD.Vector(5, -7, 3), FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), 90))
for name, lage in (("z", None), ("x", quer)):
    koerper = drehkoerper(lage)
    step = os.path.join(ordner, f"halter_{name}.step")
    koerper.exportStep(step)
    stl = os.path.join(ordner, f"halter_{name}.stl")
    Mesh.Mesh(koerper.tessellate(0.01)).write(stl)
    for pfad in (step, stl):
        punkte, dreiecke = hd.netz(pfad)
        i, _mitte, unrund = hd.achse(punkte)
        pruefe(i == (2 if name == "z" else 0) and unrund < 0.01, f"{pfad}: Achse {i}, {unrund}")
        stellen, r, _i = hd.kontur(punkte, dreiecke)
        pruefe(nahe(stellen[-1], 131.5, 0.1), f"{pfad}: Länge {stellen[-1]}")
        von, bis = 68.0, 131.5  # gedreht um Y um +90° wird Z zu X: der Kegel bleibt vorn
        teile = hd.abschnitte(stellen, r, von, bis)
        gleich = len(teile) == len(ERWARTET) and all(
            nahe(a[0], b[0], 0.15) and nahe(a[1], b[1], 0.1) and nahe(a[2], b[2], 0.1)
            for a, b in zip(teile, ERWARTET, strict=True)
        )
        pruefe(gleich, f"{pfad}: {teile}")
        pruefe(nahe(sum(t[0] for t in teile), 63.5, 0.15), f"{pfad}: A {sum(t[0] for t in teile)}")
        # Von hinten gelesen: dieselben Abschnitte von der Nase zur Spindel – gespiegelt.
        rueck = [(t[0], t[2], t[1]) for t in reversed(hd.abschnitte(stellen, r, bis, von))]
        gleich = len(rueck) == len(teile) and all(
            all(nahe(x, y, 0.02) for x, y in zip(a, b, strict=True))
            for a, b in zip(rueck, teile, strict=True)
        )
        pruefe(gleich, f"{pfad}: rückwärts {rueck}")
        # Die Spindelseite: der Steilkegel bei 0, die Spindelnase an seinem Ende (68); gespiegelt
        # dieselbe von der anderen Seite.
        seite = hd.spindelseite(stellen, r)
        pruefe(seite is not None and nahe(seite[0], 68, 0.3) and seite[1], f"{pfad}: Seite {seite}")
        gespiegelt = hd.spindelseite(stellen[-1] - stellen[::-1], r[::-1])
        pruefe(
            gespiegelt is not None and nahe(gespiegelt[0], 131.5 - 68, 0.3) and not gespiegelt[1],
            f"{pfad}: gespiegelt {gespiegelt}",
        )
        sprung = [s for s, r0, r1 in hd.stufen(stellen, r) if r0 > 30 and r1 < 26]
        pruefe(len(sprung) == 1 and nahe(sprung[0], 84, 0.15), f"{pfad}: Stufe {sprung}")

pruefe(hd.kreisfehler(31.5) <= hd.NETZ_TOLERANZ + 1e-9, "Sehne innen am Kreis")
# Ein Zylinder hat keine Seite, die wie eine Aufnahme aussieht.
walze = os.path.join(ordner, "walze.step")
Part.makeCylinder(20, 100).exportStep(walze)
punkte, dreiecke = hd.netz(walze)
stellen, r, _i = hd.kontur(punkte, dreiecke)
pruefe(hd.spindelseite(stellen, r) is None, "Zylinder: keine Spindelseite")

# Die Ausgabe von OpenCASCADE endet nicht immer mit einem Zeilenende: das Ergebnis auf eine
# eigene Zeile.
print()
if fehler:
    print("FEHLER test_halter_datei:")
    for f in fehler:
        print("  -", f)
else:
    print("OK test_halter_datei")
