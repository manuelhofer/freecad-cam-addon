# Prüft die CAM-Operation „Rundum schruppen“ (W-003 Stufe V3c): Welle Ø 60 in der Stange
# Ø 80 aus dem Assistenten (Rundachse C), Schaftfräser Ø 12 – im Job angelegt ohne
# Rückfrage, fünf Lagen, die Bahn mit G93 … G94 und C; nach Speichern und Laden dieselbe
# Bahn; der Postprozessor (LinuxCNC) schreibt jeden Satz mit F. Dazu die Fehlerfälle:
# Rohteil keine Stange, kein Vorschub. Ändern: anderer Controller, andere Werte. Gewählte
# Flächen (V4): nur der Mantel – die Bahn bleibt über dem Teil; eine Fläche, die es nicht
# gibt, oder nur eine Stirn – ein Satz statt der Bahn.
import importlib
import os
import re
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
# Die Stange ragt so weit heraus, wie der Fräser hinten braucht: Überlauf 6,5 + Fräser 6 +
# Abstand zum Futter 5 (V3f).
stange = vr.Stange(80.0, frei_hinten=17.5)
job = vr.richte_ein(doc, welle, lage, stange, achse, beschriftung="Welle 4 Achsen")
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
# Mit M3 steigt φ (Gleichlauf); nach DIN 66217 ist C = φ (Drehsinn −1).
pruefe(max(b.Parameters["C"] for b in schnitte) > 3600, "C dreht nicht mehrmals herum")
# Über dem Teil (Z −106,3 … 6,3) bleibt X über 30,3: Radius 30 plus Aufmaß.
ueber = [b.Parameters["X"] for b in schnitte if -106.3 <= b.Parameters["Z"] <= 6.3]
pruefe(min(ueber) >= 30.3, f"zu tief: {min(ueber)}")
# Hinten: die Mitte des Fräsers 6,5 mm hinter dem Teil (Überlauf) – das Futter bei −117,5.
pruefe(abs(min(b.Parameters["Z"] for b in schnitte) - (-103.5)) < 1e-9, "hinteres Ende")
pruefe(vo.abstaende(op) == (3.5, 5.0, 2.0), f"Überlauf, Abstand, Sicherheit: {vo.abstaende(op)}")
# Eine Operation aus 0.26 (ohne Überlauf und Abstand zum Futter): Beim Laden bekommt sie
# die Werte, mit denen ihre Bahn bleibt, wie sie war – 2 mm vor dem Futter.
op.removeProperty("Ueberlauf")
op.removeProperty("AbstandFutter")
op.removeProperty("HalterZumFutter")  # bis 0.28: nur der Fräser vor dem Futter
op.Proxy.opOnDocumentRestored(op)
pruefe(vo.abstaende(op) == (3.5, 2.0, 2.0), f"alte Operation: {vo.abstaende(op)}")
pruefe(vo.halter_zum_futter(op) == 0.0, f"alter Halter: {vo.halter_zum_futter(op)}")
op.AbstandFutter = 5.0
# Ein Halter, der 27,5 mm über die Werkzeugachse reicht: Er bleibt 5 mm vor dem Futter
# (−117,5), die Mitte des Fräsers also bei −85 – nicht mehr 6,5 hinter dem Teil.
op.HalterZumFutter = 27.5
doc.recompute()
schnitte = [b for b in op.Path.Commands if b.Name == "G1"]
pruefe(abs(min(b.Parameters["Z"] for b in schnitte) - (-85.0)) < 1e-9, "Ende mit Halter")
op.HalterZumFutter = 0.0
doc.recompute()

# --- Gewählte Flächen (V4) -----------------------------------------------------------------
# Eine Operation aus 0.29 (ohne Flächen und Eintauchwinkel): rundum, Rampe 5°.
op.removeProperty("Flaechen")
op.removeProperty("Eintauchwinkel")
op.Proxy.opOnDocumentRestored(op)
pruefe(vo.flaechen(op) == () and op.Eintauchwinkel.Value == 5.0, "alte Operation: Flächen")
namen_welle = [f"Face{i + 1}" for i in range(len(welle.Shape.Faces))]
mantel = [n for n, f in zip(namen_welle, welle.Shape.Faces, strict=True) if not vr.ist_eben(f)]
stirnen = [n for n, f in zip(namen_welle, welle.Shape.Faces, strict=True) if vr.ist_eben(f)]
# Nur der Mantel: fünf Lagen wie rundum, aber vorne nicht mehr vor der Stange – nur so weit,
# wie der Fräser das Teil berührt (Mitte bis 6 mm vor seiner Stirn bei a = 0).
op.Flaechen = mantel
doc.recompute()
schnitte = [b for b in op.Path.Commands if b.Name == "G1"]
pruefe(op.Lagen == 5, f"nur Mantel: {op.Lagen} Lagen")
vorne = max(b.Parameters["Z"] for b in schnitte)
pruefe(vorne <= 6.0 + 0.3, f"nur Mantel: vorne bis {vorne}")
pruefe(len(schnitte) > 100, "nur Mantel: keine Bahn")
for flaechen_, satz in (
    (["Face99"], sprache.tr("vf.fehler.fehlt", namen="Face99")),
    (stirnen, sprache.tr("vf.fehler.nicht_erreichbar")),
):
    op.Flaechen = flaechen_
    doc.recompute()
    kommentare = [
        b.Name for b in op.Path.Commands if b.Name.startswith("(") and "4-Achs" not in b.Name
    ]
    pruefe(
        op.Lagen == 0 and any(vo._ascii(satz) in k for k in kommentare),
        f"{flaechen_}: {kommentare}",
    )
op.Flaechen = []
doc.recompute()
pruefe(op.Lagen == 5, f"wieder rundum: {op.Lagen} Lagen")

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

# Die Postprozessoren, die die Hilfe nennt (vierachs.html, „Im Programm“; Manuel 2026-09-30:
# „Funktionieren die so wie wir das hier bauen??“): In jedem Vorschubsatz zwischen G93 und G94
# steht F – auch bei Fanuc und UCCNC, die ein F weglassen, das dem vorigen gleicht: Zwei gleiche
# folgen nie aufeinander (P-2026-09-30-39) –, und die Rundachse C bleibt. Gezählt wie die
# Steuerung liest: Ein Satz ohne G-Wort fährt wie der davor.
from Path.Post.Processor import PostProcessorFactory  # noqa: E402


def vorschubsaetze(text):
    """Die Sätze zwischen G93 und G94, die mit G1 fahren – auch modal ohne „G1“."""
    saetze, drin, modus = [], False, None
    for zeile in text.splitlines():
        satz = re.sub(r"^N\d+\s*", "", re.sub(r"\(.*?\)|;.*$", "", zeile).strip().upper())
        if re.search(r"(?<![A-Z0-9.])G93(?!\d)", satz):
            drin = True
            continue
        if drin and re.search(r"(?<![A-Z0-9.])G94(?!\d)", satz):
            break
        wechsel = re.findall(r"(?<![A-Z])G0?([01])(?![0-9.])", satz)
        if wechsel:
            modus = wechsel[-1]
        if drin and modus == "1" and re.search(r"(?<![A-Z])[XYZABC]-?[\d.]", satz):
            saetze.append(satz)
    return saetze


job = next(o for o in doc.Objects if hasattr(o, "Operations"))
for namen in (
    ("linuxcnc", "linuxcnc_legacy"),
    ("mach3_mach4", "mach3_mach4_legacy"),
    ("fanuc", "fanuc_legacy"),
    ("uccnc", "uccnc_legacy"),
):
    job.PostProcessorArgs = "--no-show-editor"
    abschnitte = None
    for name in namen:
        post = PostProcessorFactory.get_post_processor(job, name)
        if hasattr(post, "export"):  # sonst None (1.1.3) oder ein CAMError (26.3): gibt es nicht
            abschnitte = post.export()
            break
    pruefe(abschnitte, f"{namen[0]}: keine Ausgabe")
    saetze = vorschubsaetze("\n".join(str(g or "") for _, g in abschnitte or ()))
    ohne_f = [z for z in saetze if not re.search(r"(?<![A-Z])F[\d.]", z)]
    mit_c = [z for z in saetze if re.search(r"(?<![A-Z])C-?[\d.]", z)]
    pruefe(
        len(saetze) > 100 and not ohne_f,
        f"{namen[0]}: {len(ohne_f)} von {len(saetze)} ohne F, etwa {ohne_f[:1]}",
    )
    pruefe(len(mit_c) > 0.9 * len(saetze), f"{namen[0]}: C in {len(mit_c)} von {len(saetze)}")

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

# --- Wände für den Ringgang (D-42) -----------------------------------------------------------
# Planflächen quer zur Achse zwischen den Enden: ein Absatz, die Flanken einer Nut – nicht die
# Stirn vorn und hinten, nicht die Mantelflächen.
V = FreeCAD.Vector
pruefe(vo.waende(Part.makeCylinder(20, 40, V(0, 0, -40)), (0, 0, 1)) == (), "Zylinder: Wände")
absatz = Part.makeCylinder(25, 25, V(0, 0, -25)).fuse(Part.makeCylinder(18, 15, V(0, 0, -40)))
pruefe(vo.waende(absatz.removeSplitter(), (0, 0, 1)) == ((-25.0, -1),), "Absatz zum Futter")
pruefe(vo.waende(absatz.removeSplitter(), (0, 0, -1)) == ((25.0, 1),), "andersherum")
nut = Part.makeCylinder(20, 40, V(0, 0, -40)).cut(
    Part.makeCylinder(25, 8, V(0, 0, -24)).cut(Part.makeCylinder(15, 8, V(0, 0, -24)))
)
pruefe(vo.waende(nut, (0, 0, 1)) == ((-24.0, 1), (-16.0, -1)), f"Nut: {vo.waende(nut, (0, 0, 1))}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
