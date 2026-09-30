# Prüft die CAM-Operation „Rundum schlichten“ (W-003 Stufe V5c): Welle Ø 60 in der Stange
# Ø 80 (Rundachse C), Kugelfräser Ø 6 aus der Werkzeugverwaltung – ohne „Rundum schruppen“
# im Job ein Satz statt einer Bahn; mit ihm die Spirale auf Ø 60 plus Vernetzung, G93 … G94
# und C; Kammhöhe und Umdrehungen stehen an der Operation. Die Form kommt aus dem ToolBit
# des Controllers. „Schnittwerte in den Job“ kennt sie mit dem Einsatz „Schlichten“.
# Ändern (anderer Controller, andere Werte), Speichern und Laden, Postprozessor.
import importlib
import math
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import job_schnittwerte as js
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_achsen as va
from camaddon import vierachs_operation as vo
from camaddon import vierachs_rohteil as vr
from camaddon import vierachs_schlichten as vs
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))

# Die Werkzeugverwaltung: T1 Schaftfräser Ø 12 (Schruppen), T2 Kugelfräser Ø 6 (Schlichten,
# ae 0,3 mm), T3 Torusfräser Ø 10, T4 Formfräser – für CAM ein Schaftfräser –, T5
# Gewindefräser: dessen Form kennt das Addon nicht.
schaft = wz.Werkzeug(nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26)
schaft.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=120, fz=0.05)]
kugel = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)
schlichten = wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=6, vc=150, fz=0.04)
kugel.schnittwerte[wz.ALLE] = [schlichten]
torus = wz.Werkzeug(nummer=3, art=wz.TORUSFRAESER, durchmesser=10, schneiden=4, eckradius=1)
torus.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.5, ap=5, vc=150, fz=0.04)]
form = wz.Werkzeug(nummer=4, art=wz.FORMFRAESER, durchmesser=8, schneiden=2)
form.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.2, ap=3, vc=100, fz=0.03)]
gewinde = wz.Werkzeug(nummer=5, art=wz.GEWINDEFRAESER, durchmesser=8, schneiden=3)
gewinde.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.GEWINDEFRAESEN, vc=100, fz=0.03)]
bibliothek = wz.Bibliothek([schaft, kugel, torus, form, gewinde])
ue.uebergeben(bibliothek)
pruefe(vs.schrittweite_vorschlag(kugel, schlichten) == 0.3, "Schrittweite aus dem Einsatz")
pruefe(abs(vs.schrittweite_vorschlag(kugel, None) - 0.12) < 1e-12, "ohne Einsatz: D/50")

doc = FreeCAD.newDocument("Schlichten")
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
job = vr.richte_ein(doc, welle, lage, vr.Stange(80.0, frei_hinten=17.5), achse, beschriftung="W")
tc1 = js.controller_ohne_transaktion(doc, job, schaft, schaft.einsaetze(wz.ALLE)[0])
tc2 = js.controller_ohne_transaktion(doc, job, kugel, schlichten)
tc3 = js.controller_ohne_transaktion(doc, job, torus, torus.einsaetze(wz.ALLE)[0])
tc4 = js.controller_ohne_transaktion(doc, job, form, form.einsaetze(wz.ALLE)[0])
tc5 = js.controller_ohne_transaktion(doc, job, gewinde, gewinde.einsaetze(wz.ALLE)[0])
doc.recompute()

form2 = vs.form_des_controllers(tc2)
pruefe(form2 is not None and form2.nur_kugel and form2.radius == 3.0, "Form aus dem ToolBit")
form3 = vs.form_des_controllers(tc3)
pruefe(form3 is not None and abs(form3.hoehe(5.0) - 1.0) < 1e-9, "Torus aus dem ToolBit")
pruefe(vs.form_des_controllers(tc4).eben, "Formfräser: für CAM ein Schaftfräser")
pruefe(vs.form_des_controllers(tc5) is None, "Gewindefräser hat eine Form")

# Ohne „Rundum schruppen“ im Job: ein Satz statt einer Bahn.
op = vs.lege_an(job, tc2, achse, schrittweite=0.3)
doc.recompute()
pruefe(op.Label == "Rundum schlichten T2" and op in job.Operations.Group, f"{op.Label}")
pruefe(vo.ist_rundum(op) and vs.ist_schlichten(op) and not vo.ist_schruppen(op), "Art")
pruefe(js.operationsart(op) == "vierachs_schlichten", f"Art: {js.operationsart(op)}")
pruefe(js.EINSATZ_NACH_OPERATION["vierachs_schlichten"] == (wz.SCHLICHTEN,), "Einsatz")
pruefe(vo.abstaende(op) == (3.5, 5.0, 2.0), f"Abstände: {vo.abstaende(op)}")
namen = [b.Name for b in op.Path.Commands]
pruefe(len(namen) == 2 and "Rundum schruppen" in namen[1], f"ohne Schruppen: {namen}")
pruefe(op.Umdrehungen == 0.0, f"Umdrehungen ohne Bahn: {op.Umdrehungen}")

# Mit „Rundum schruppen“ davor: die Spirale.
schruppen = vo.lege_an(job, tc1, achse, zustellung=2.0, steigung=4.8, aufmass=0.3)
op.touch()
doc.recompute()
befehle = op.Path.Commands
namen = [b.Name for b in befehle]
pruefe(namen[2:5] == ["G0", "G0", "G93"] and namen[-1] == "G94", f"Befehle: {namen[:6]}")
schnitte = [b for b in befehle if b.Name == "G1"]
pruefe(all(b.Parameters.get("F", 0) > 0 for b in schnitte), "G1 ohne F")
pruefe(min(b.Parameters["C"] for b in schnitte) < -3600 * 30, "C dreht nicht oft genug")
ueber = [b.Parameters["X"] for b in schnitte if -100 <= b.Parameters["Z"] <= 0]
pruefe(min(ueber) >= 29.999 and max(ueber) <= 30.01, f"über dem Teil: {min(ueber)} … {max(ueber)}")
# Hinten: die Mitte des Kugelfräsers 3,5 mm hinter dem Teil (Überlauf Radius + 0,5).
pruefe(abs(min(b.Parameters["Z"] for b in schnitte) - (-103.5)) < 0.001, "hinteres Ende")
kamm = 3 - math.sqrt(9 - 0.15**2)
pruefe(abs(op.Kammhoehe.Value - kamm) < 1e-9, f"Kammhöhe {op.Kammhoehe}")
pruefe(abs(op.Umdrehungen - (1 + 3 + 2 + 103.5) / 0.3) < 0.1, f"Umdrehungen {op.Umdrehungen}")
pruefe(op.Vorstufen == 0, f"Vorstufen: {op.Vorstufen}")
pruefe(op.getEditorMode("Kammhoehe") == ["ReadOnly"], "Kammhöhe änderbar")

# --- Ändern: der Torus T3, andere Werte; der vorgeschlagene Name folgt dem Werkzeug ------
vs.aendere(op, tc3, schrittweite=0.5, aufmass=0.1, abstaende=(5.5, 5.0, 2.0))
doc.recompute()
pruefe(op.Label == "Rundum schlichten T3" and op.ToolController is tc3, f"geändert: {op.Label}")
schnitte = [b for b in op.Path.Commands if b.Name == "G1"]
ueber = [b.Parameters["X"] for b in schnitte if -100 <= b.Parameters["Z"] <= 0]
pruefe(30.099 <= min(ueber) <= 30.11, f"Torus mit Aufmaß 0,1: {min(ueber)}")
pruefe(op.Kammhoehe.Value == 0.0, f"Torus-Kammhöhe unter der Scheibe: {op.Kammhoehe}")
vs.aendere(op, tc5, schrittweite=0.2, aufmass=0.0)
doc.recompute()
pruefe("Form" in op.Path.Commands[1].Name, f"Gewindefräser: {op.Path.Commands[1].Name}")
vs.aendere(op, tc2, schrittweite=0.3, aufmass=0.0, abstaende=(3.5, 5.0, 2.0))
doc.recompute()

# --- Speichern und Laden: dieselbe Bahn --------------------------------------------------
anzahl = len(op.Path.Commands)
pfad = os.path.join(tempfile.mkdtemp(), "schlichten.FCStd")
doc.saveAs(pfad)
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(pfad)
op = next(o for o in doc.Objects if vs.ist_schlichten(o))
op.touch()
doc.recompute()
pruefe(len(op.Path.Commands) == anzahl, f"nach dem Laden {len(op.Path.Commands)} statt {anzahl}")
pruefe(op.getEditorMode("Umdrehungen") == ["ReadOnly"], "Umdrehungen nach dem Laden")

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
        print(ascii(f"Postprozessor {post.__name__}: {len(saetze)} Sätze, etwa {saetze[1]}"))
FreeCAD.closeDocument(doc.Name)
del schruppen

if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
