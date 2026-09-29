# Prüft die CAM-Operation „Rundum schruppen“ (W-003 Stufe V3c): Welle Ø 60 in der Stange
# Ø 80 aus dem Assistenten (Rundachse C), Schaftfräser Ø 12 – im Job angelegt ohne
# Rückfrage, fünf Lagen, die Bahn mit G93 … G94 und C; nach Speichern und Laden dieselbe
# Bahn; der Postprozessor (LinuxCNC) schreibt jeden Satz mit F. Dazu die Fehlerfälle:
# Rohteil keine Stange, kein Vorschub. Ändern: anderer Controller, andere Werte.
import importlib
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import job_schnittwerte as js
from camaddon import sprache
from camaddon import vierachs_achsen as va
from camaddon import vierachs_operation as vo
from camaddon import vierachs_rohteil as vr

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")

doc = FreeCAD.newDocument("Rundum")
doc.UndoMode = 1
welle = doc.addObject("Part::Feature", "Welle")
welle.Shape = Part.makeCylinder(30, 100, V(), V(1, 0, 0))
doc.recompute()
stirn = next(
    f
    for f in welle.Shape.Faces
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
)
achse = va.zugewiesen("C")
lage = vr.berechne(welle.Shape, stirn, achse, durchmesser=80)
job = vr.richte_ein(doc, welle, lage, vr.Stange(80.0), achse, beschriftung="Welle 4 Achsen")
tc = job.Tools.Group[0]
tc.Tool.Diameter = 12
tc.HorizFeed = "1500 mm/min"
doc.recompute()

op = vo.lege_an(job, tc, achse, zustellung=2.0, steigung=4.8, aufmass=0.3)
doc.recompute()
pruefe(op in job.Operations.Group, "nicht im Job")
pruefe(op.ToolController is tc and op.Label == "Rundum schruppen T1", f"{op.Label}")
pruefe(vo.ist_rundum(op) and js.operationsart(op) == "vierachs_operation", "Art")
pruefe(js.EINSATZ_NACH_OPERATION.get("vierachs_operation"), "Schnittwerte kennen sie nicht")
pruefe(op.Lagen == 5, f"Lagen: {op.Lagen}")
befehle = op.Path.Commands
namen = [b.Name for b in befehle]
pruefe(namen[0] == f"({op.Label})" and namen[1].startswith("(4-Achs"), f"Anfang: {namen[:3]}")
pruefe(namen[2:5] == ["G0", "G0", "G93"] and namen[-1] == "G94", f"Befehle: {namen[:6]}")
pruefe(befehle[2].Parameters == {"X": 42.0}, f"zuerst radial: {befehle[2].Parameters}")
# Die Stange: vorne bei a = 1 (Planaufmaß), die Spitze beginnt Fräserradius + 2 davor.
pruefe(
    befehle[3].Parameters == {"X": 42.0, "Y": 0.0, "Z": 9.0, "C": 0.0},
    f"Start: {befehle[3].Parameters}",
)
schnitte = [b for b in befehle if b.Name == "G1"]
pruefe(all("F" in b.Parameters and b.Parameters["F"] > 0 for b in schnitte), "G1 ohne F")
pruefe(min(b.Parameters["C"] for b in schnitte) < -3600, "C dreht nicht mehrmals herum")
# Über dem Teil (Z −106,3 … 6,3) bleibt X über 30,3: Radius 30 plus Aufmaß.
ueber = [b.Parameters["X"] for b in schnitte if -106.3 <= b.Parameters["Z"] <= 6.3]
pruefe(min(ueber) >= 30.3, f"zu tief: {min(ueber)}")
# Hinten: der Rand des Fräsers 2 mm vor dem Futter (Stange hinten bei −133, Spannlänge 30).
pruefe(abs(min(b.Parameters["Z"] for b in schnitte) - (-103 + 2 + 6)) < 1e-9, "hinteres Ende")

# --- Ändern: anderer Controller, andere Werte; der vorgeschlagene Name folgt dem Werkzeug --
from Path.Tool import Controller

tc5 = Controller.Create("T5", tool=tc.Tool, toolNumber=5)
job.Proxy.addToolController(tc5)
tc5.HorizFeed = "1500 mm/min"
vo.aendere(op, tc5, zustellung=1.5, steigung=4.0, aufmass=0.5)
doc.recompute()
pruefe(op.ToolController is tc5 and op.Label == "Rundum schruppen T5", f"geändert: {op.Label}")
werte = (op.Zustellung.Value, op.VorschubJeUmdrehung.Value, op.Aufmass.Value)
pruefe(werte == (1.5, 4.0, 0.5), f"Werte: {werte}")
pruefe(op.Lagen > 5, f"Lagen mit Zustellung 1,5: {op.Lagen}")
op.Label = "Meine Welle"
vo.aendere(op, tc, zustellung=2.0, steigung=4.8, aufmass=0.3)
pruefe(op.Label == "Meine Welle" and op.ToolController is tc, f"eigener Name: {op.Label}")
op.Label = "Rundum schruppen T1"
js.controller_weg(doc, [tc5])
doc.recompute()
pruefe(op.Lagen == 5 and tc.Tool is not None, f"zurück: {op.Lagen}")

# --- Speichern und Laden: dieselbe Bahn --------------------------------------------------
anzahl = len(befehle)
pfad = os.path.join(tempfile.mkdtemp(), "rundum.FCStd")
doc.saveAs(pfad)
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(pfad)
op = next(o for o in doc.Objects if vo.ist_rundum(o))
op.touch()
doc.recompute()
pruefe(len(op.Path.Commands) == anzahl, f"nach dem Laden {len(op.Path.Commands)} statt {anzahl}")
pruefe(op.Lagen == 5 and op.Zustellung.Value == 2.0, "Werte nach dem Laden")
pruefe(op.getEditorMode("Lagen") == ["ReadOnly"], f"Lagen: {op.getEditorMode('Lagen')}")

# --- Postprozessor: jeder Satz zwischen G93 und G94 mit F --------------------------------
post = None
for name in ("linuxcnc_legacy_post", "linuxcnc_post"):
    try:
        modul = importlib.import_module(f"Path.Post.scripts.{name}")
    except ImportError:
        continue
    if hasattr(modul, "export"):
        post = modul
        break
pruefe(post is not None, "kein LinuxCNC-Postprozessor mit export()")
if post is not None:
    text = post.export([op], "-", "--no-show-editor") or ""
    zeilen = [z.strip() for z in text.splitlines()]
    g93 = next((i for i, z in enumerate(zeilen) if z.startswith("G93")), None)
    g94 = next((i for i, z in enumerate(zeilen) if z.startswith("G94")), None)
    pruefe(g93 is not None and g94 is not None and g93 < g94, f"G93/G94: {g93}, {g94}")
    if g93 is not None and g94 is not None:
        saetze = [z for z in zeilen[g93 + 1 : g94] if z.startswith("G1")]
        pruefe(saetze and all(" F" in z for z in saetze), "Satz ohne F")
        pruefe(all(" C" in z or "C" in z.split()[1:] for z in saetze[:5]), f"ohne C: {saetze[:3]}")
        print(ascii(f"Postprozessor {post.__name__}: {len(saetze)} Sätze, etwa {saetze[1]}"))

# --- Fehler: Rohteil keine Stange, kein Vorschub -------------------------------------------
job = next(o for o in doc.Objects if hasattr(o, "Operations"))
tc = job.Tools.Group[0]
tc.HorizFeed = 0
op.touch()
doc.recompute()
pruefe(op.Lagen == 0 and len(op.Path.Commands) == 2, f"ohne Vorschub: {op.Path.Commands}")
pruefe("Vorschub" in op.Path.Commands[1].Name, f"Kommentar: {op.Path.Commands[1].Name}")
tc.HorizFeed = "1500 mm/min"
import Path.Main.Stock as PathStock

alt = job.Stock
job.Stock = PathStock.CreateBox(job)
doc.removeObject(alt.Name)
op.touch()
doc.recompute()
pruefe(op.Lagen == 0 and "Stange" in op.Path.Commands[1].Name, f"Quader: {op.Path.Commands}")
FreeCAD.closeDocument(doc.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
