# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Auflösung je Strategie (T-009, aufloesung.py): Jede Operation mit einem Raster trägt die
Eigenschaft `Raster` (0 = Vorschlag); gesetzt rechnet sie ihre Bahn damit – gröber wie feiner
eine andere Bahn –, und 0 ist genau die bisherige Bahn. 3D-Schlichten mit der
Kugel Ø 6 an der Kuppel 20 × 16, Sekunden."""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import FreeCAD
import Part
import Path.Main.Job as PathJob

from camaddon import aufloesung as au
from camaddon import job_schnittwerte as js
from camaddon import schlichten3d as s3
from camaddon import schlichten3d_bahn as sb
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

sprache.setze_sprache("de")
profil = os.environ.get("FREECAD_USER_HOME")
assert profil and os.path.isdir(profil), "eigenes Testprofil nötig (Werkzeugverwaltung)"

doc = FreeCAD.newDocument("Aufloesung")
teil = doc.addObject("Part::Feature", "Kuppel")
V = FreeCAD.Vector
kappe = Part.makeSphere(40, V(10, 8, -25)).common(Part.makeBox(20, 16, 20, V(0, 0, 6)))
teil.Shape = Part.makeBox(20, 16, 6).fuse(kappe).removeSplitter()
doc.recompute()
job = PathJob.Create("Job", [teil])
w = wz.standardwerkzeug()
kugel = wz.Werkzeug.aus_dict(w.als_dict())
kugel.kennung, kugel.nummer, kugel.name = "aufloesung_kugel6", 2, "Kugel 6"
kugel.art, kugel.durchmesser, kugel.eckradius = wz.KUGELFRAESER, 6, 3
bib = wz.Bibliothek([w, kugel])
bib.speichern()
ue.uebergeben(bib)
einsatz = next(e for e in kugel.schnittwerte[wz.ALLE] if e.art == wz.SCHLICHTEN)
tc = js.controller_ohne_transaktion(doc, job, kugel, einsatz)
faces = [
    f"Face{i + 1}" for i, f in enumerate(teil.Shape.Faces) if isinstance(f.Surface, Part.Sphere)
]
op = s3.lege_an(job, tc, 0.02, flaechen=faces)
doc.recompute()
assert au.EIGENSCHAFT in op.PropertiesList, "3D-Schlichten ohne Eigenschaft Raster"
assert float(op.Raster) == 0.0 and au.wert(op, sb.SCHRITT) == sb.SCHRITT


def bahn():
    return [
        (c.Name, tuple(round(float(v), 6) for _k, v in sorted(c.Parameters.items())))
        for c in op.Path.Commands
    ]


vorgabe = bahn()
assert len(vorgabe) > 50, len(vorgabe)
# Gesetzt: gröber und feiner geben je eine andere Bahn (die Zahl der Sätze sagt nichts – grob
# abgetastet lässt das Vereinfachen mehr Punkte stehen); 0 ist wieder genau die Vorgabe.
au.setze(op, 2.0)
doc.recompute()
grob = bahn()
au.setze(op, 0.1)
doc.recompute()
fein = bahn()
au.setze(op, 0)
doc.recompute()
assert grob != vorgabe and fein != vorgabe and grob != fein, "das Raster ändert die Bahn nicht"
assert min(len(grob), len(fein)) > 50, (len(grob), len(vorgabe), len(fein))
assert bahn() == vorgabe, "Raster 0 ist nicht die Vorgabe"
# Eine Operation ohne die Eigenschaft bekommt sie beim Nachrüsten – mit 0.
op.removeProperty(au.EIGENSCHAFT)
assert au.eigenschaft(op, s3.GRUPPE) and float(op.Raster) == 0.0
assert not au.eigenschaft(op, s3.GRUPPE)
FreeCAD.closeDocument(doc.Name)
print("OK", os.path.basename(__file__))
