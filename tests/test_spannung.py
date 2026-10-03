# Prüft „von unten gespannt“ (spannung.py; Spezifikation Strategien S3h, Manuel 2026-10-01: „so
# viel steckt im Schraubstock – die Prüfung … meldet jede Bahn darunter“): ein Block 40 × 30 × 20,
# Rohteil 1 mm rundum (unten Z −1), 5 mm gespannt (bis Z 4). Eine Kontur außen um das Rohteil bis
# Z 2 ragt dort neben das Rohteil – gemeldet; eine Tasche innen bis Z 2 nicht; ein Bohrzyklus bis
# Z −3 fährt unter das Rohteil – gemeldet als „unter“; ein Bogen, dessen Enden innen liegen, der
# aber in der Mitte hinausragt, zählt. Ohne Eintrag: nichts. „Auf der Maschine prüfen“ nennt die
# Sätze unter den Hinweisen.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import beispielmaschine, spannung, sprache
from camaddon import reichweite as rw

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")

import Path.Main.Job as PathJob  # noqa: E402
import Path.Op.Custom as PathCustom  # noqa: E402

doc = FreeCAD.newDocument("Spannung")
teil = doc.addObject("Part::Feature", "Block")
teil.Shape = Part.makeBox(40, 30, 20)
doc.recompute()
job = PathJob.Create("Job", [teil])
doc.recompute()
box = job.Stock.Shape.BoundBox
pruefe(abs(box.ZMin + 1.0) < 1e-6 and abs(box.XMin + 1.0) < 1e-6, f"Rohteil {box}")


def operation(name, gcode):
    op = PathCustom.Create(name)
    op.Gcode = gcode
    return op


r = float(getattr(job.Tools.Group[0].Tool.Diameter, "Value", 5.0)) / 2
kontur = operation(
    "Kontur",
    ["G0 X-5 Y-5 Z25", f"G1 X{-1 - r + 0.5} Y-5 Z2", "G1 X45 Y-5", "G0 Z25"],
)
tasche = operation("Tasche", ["G0 X20 Y15 Z25", "G1 Z2", "G1 X25", "G0 Z25"])
bohren = operation("Bohren", ["G0 X20 Y15 Z25", "G81 X20 Y15 Z-3 R3 F100", "G80", "G0 Z25"])
# Ein Halbkreis um (20, 15) mit Radius 16: Anfang und Ende bei y 15 innen, oben bei y 31 + r draußen.
bogen = operation("Bogen", ["G0 X4 Y15 Z25", "G1 Z3", "G2 X36 Y15 I16 J0", "G0 Z25"])
doc.recompute()

pruefe(spannung.pruefen(job) == [], f"ohne Eintrag: {spannung.pruefen(job)}")
spannung.setze(job, 5.0)
pruefe(abs(spannung.gespannt(job) - 5.0) < 1e-9, f"gespannt: {spannung.gespannt(job)}")
saetze = spannung.pruefen(job)
print("\n".join(ascii(s) for s in saetze))
pruefe(any("„Kontur“" in s and "neben dem Rohteil" in s and "Z 2" in s for s in saetze), "Kontur")
pruefe(not any("„Tasche“" in s for s in saetze), "Tasche innen gemeldet")
pruefe(any("„Bohren“" in s and "unter das Rohteil" in s and "Z −3" in s for s in saetze), "Bohren")
pruefe(any("„Bogen“" in s and "neben dem Rohteil" in s for s in saetze), "Bogen")
pruefe(len(saetze) == 3, f"{len(saetze)} Sätze")

# Im Fenster „Auf der Maschine prüfen“: unter den Hinweisen.
asm, ma = beispielmaschine.fraesmaschine()
ergebnis = rw.Pruefung(asm, ma).pruefe_job(job)
pruefe(all(s in ergebnis.hinweise for s in saetze), f"Hinweise der Prüfung: {ergebnis.hinweise}")

# Wieder 0: nichts mehr.
spannung.setze(job, 0.0)
pruefe(spannung.pruefen(job) == [], "nach 0 noch Sätze")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
