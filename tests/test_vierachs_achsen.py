# Prüft die Stangenachse für die 4-Achs-Bearbeitung (W-003 Stufe V2a): ohne
# Maschine A/B/C in X/Y/Z; an der Beispiel-Drehmaschine gibt C1 im Tisch die
# Achse vor – C, die Stange längs +Z, vom Futter weg; die 3-Achs-Fräse hat
# keine. Dazu das Geraderücken von Richtungen und die Lage im Job.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import beispielmaschine as bm
from camaddon import vierachs_achsen as va
from camaddon import vierachs_rohteil as vr

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


X, Y, Z = FreeCAD.Vector(1, 0, 0), FreeCAD.Vector(0, 1, 0), FreeCAD.Vector(0, 0, 1)

# Ohne Maschine: wie bisher der Buchstabe.
for buchstabe, soll in (("A", X), ("B", Y), ("C", Z)):
    achse = va.zugewiesen(buchstabe)
    pruefe(
        (achse.buchstabe, achse.maschine) == (buchstabe, "") and achse.laengs == soll,
        f"{buchstabe} ohne Maschine: {achse}",
    )
    pruefe(vr.laengs_von(buchstabe) == vr.laengs_von(achse), f"laengs_von {buchstabe}")

# Geraderücken: fast auf einer Achse → genau darauf, sonst nur normiert.
pruefe(
    va.gerade(FreeCAD.Vector(1e-9, 0, -2)) == -Z,
    f"gerade: {va.gerade(FreeCAD.Vector(1e-9, 0, -2))}",
)
schraeg = va.gerade(FreeCAD.Vector(3, 4, 0))
pruefe(abs(schraeg.Length - 1) < 1e-12 and abs(schraeg.x - 0.6) < 1e-12, f"schräg: {schraeg}")
pruefe(va.achsbuchstabe(Z) == "Z" and va.achsbuchstabe(-X) == "X", "Achsbuchstabe")
pruefe(va.achsbuchstabe(schraeg) == "", "Achsbuchstabe einer schrägen Richtung")

# Vorne ist vom Futter weg (+Z der Werkstückaufnahme); quer dazu wie A in X.
pruefe(va._nach_vorne(-Z) == Z, "-Z nicht nach vorne gedreht")
pruefe(va._nach_vorne(-X) == X, "-X nicht nach vorne gedreht")

# Die Beispiel-Drehmaschine: C1 dreht im Tisch – die Stange liegt längs +Z.
asm, ma = bm.drehmaschine()
achsen = va.von_maschine(asm, ma)
pruefe(
    [(a.buchstabe, a.laengs, a.maschine) for a in achsen] == [("C", Z, ma.Label)],
    f"Drehmaschine: {achsen}",
)
pruefe(va.offene(asm.Document) == achsen, f"offene: {va.offene(asm.Document)}")
FreeCAD.closeDocument(asm.Document.Name)

# Die 3-Achs-Fräse hat keine Rundachse.
asm, ma = bm.fraesmaschine()
pruefe(va.von_maschine(asm, ma) == [], f"3-Achs-Fräse: {va.von_maschine(asm, ma)}")
FreeCAD.closeDocument(asm.Document.Name)

# Die Lage im Job mit der Achse der Maschine ist die mit C: Welle längs X, Stirn bei X 100.
welle = Part.makeCylinder(30, 100, FreeCAD.Vector(), X)
stirn = next(f for f in welle.Faces if vr.ist_eben(f) and (vr.aussennormale(f) - X).Length < 1e-9)
mess = vr.vermesse(welle, stirn)
mit_maschine = vr.lage(mess, va.Stangenachse("C", Z, "Drehmaschine"), durchmesser=80)
mit_c = vr.lage(mess, "C", durchmesser=80)
pruefe(mit_maschine.placement.isSame(mit_c.placement, 1e-9), "Lage mit Maschine ≠ Lage mit C")
stange = vr.Stange(80.0)
platz = vr.stangen_placement(mess, stange, va.Stangenachse("C", Z, "Drehmaschine"))
pruefe(platz.isSame(vr.stangen_placement(mess, stange, "C"), 1e-9), "Stange mit Maschine ≠ C")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
