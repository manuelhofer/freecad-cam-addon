# Prüft das Einrichtblatt (einrichtblatt.py, W-019; Manuel, 2026-10-12: „fräser und deren
# ausspannlängen zum halter … der halter mit abmessungen … das spannwerkzeug … das rohteil … der
# nullpunkt … die einzelnen arbeitsschritte“; „für JEDE bearbeitung“). Ein Kugelfräser Ø 6 im
# Schrumpffutter, 27 mm Ausspannlänge eingetragen: im Blatt mit Halter, Ausspannlänge 27 und
# Länge ab Spindelnase, nicht „geschätzt“; der tiefe Schritt (26 mm) steht als „knapp“ unter
# den Hinweisen. Ein Schritt mit 1000 mm in F 10 mm/s braucht gut 1,67 min. Quader 5 mm von unten
# gespannt, Nullpunkt Mitte oben; ein stehender Zylinder im Dreibackenfutter; Rundstange und
# N-Kant-Stange in Worten. Eine 3+2-Ebene: ihre Schritte in der Aufspannung des Grundjobs, unter
# einer Zwischenzeile mit den Rundachsen. Die Beispiele: jede aktive Operation ein Schritt mit Zeit.
import os
import pathlib
import sys
import tempfile
import types

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import einrichtblatt as eb
from camaddon import halter as hl
from camaddon import job_schnittwerte as js
from camaddon import n_eck, spannung, sprache
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_rohteil as vr
from camaddon import werkzeuge as wz
from camaddon.sprache import tr

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")

import Path.Main.Job as PathJob  # noqa: E402
import Path.Main.Stock as PathStock  # noqa: E402
import Path.Op.Custom as PathCustom  # noqa: E402

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
kugel = wz.Werkzeug(
    nummer=3,
    name="Kugel 6",
    art=wz.KUGELFRAESER,
    durchmesser=6.0,
    schneiden=2,
    schneidenlaenge=12.0,
    gesamtlaenge=60.0,
    schneidstoff=wz.VHM,
)
kugel.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
bibliothek = wz.Bibliothek([kugel])
schrumpf = hl.aus_vorlage("schrumpf_6")
schrumpf.kennung = "halter-schrumpf-blatt"
bibliothek.halter.append(schrumpf)
kugel.halter = schrumpf.kennung
kugel.laenge_spindelnase = float(schrumpf.laenge) + 27.0
bibliothek.speichern()
ue.uebergeben(bibliothek)


def laenge(mm):
    return f"{mm:g}"


def minuten_text(m):
    return f"{m:.2f} min"


# --- Ein Quader-Job mit zwei Schritten -----------------------------------------------------------
doc = FreeCAD.newDocument("Einrichtblatt")
teil = doc.addObject("Part::Feature", "Teil")
teil.Shape = Part.makeBox(50, 40, 30, FreeCAD.Vector(-25, -20, -30))
doc.recompute()
job = PathJob.Create("Job", [teil])
for name in ("ExtXneg", "ExtXpos", "ExtYneg", "ExtYpos"):
    setattr(job.Stock, name, 2.0)
job.Stock.ExtZpos = 0.0
job.Stock.ExtZneg = 3.0
spannung.setze(job, 5.0)
doc.recompute()
for name, gcode in (
    ("Lang", ["G0 X-10 Y0 Z5", "G1 Z-1 F10", "G1 X990 F10", "G0 Z5"]),
    ("Tief", ["G0 X10 Y10 Z5", "G1 Z-26 F10", "G1 X20 F10", "G0 Z5"]),
):
    op = PathCustom.Create(name)
    op.Gcode = gcode
tc = js.controller_ohne_transaktion(doc, job, kugel, kugel.schnittwerte[wz.ALLE][0])
for op in job.Operations.Group:
    op.ToolController = tc
doc.recompute()

b = eb.blatt(job, "2026-10-16", "0.0.0", bibliothek)
pruefe(len(b.werkzeuge) == 1, f"Werkzeuge: {b.werkzeuge}")
w = b.werkzeuge[0] if b.werkzeuge else None
if w is not None:
    pruefe(w.nummer == 3 and w.name == "Kugel 6", f"Werkzeug: {w}")
    pruefe(abs(w.ausspannlaenge - 27.0) < 1e-6, f"Ausspannlänge {w.ausspannlaenge}")
    pruefe(abs(w.laenge - (schrumpf.laenge + 27.0)) < 1e-6, f"Länge {w.laenge}")
    pruefe(w.halter == schrumpf.name and "Spanntiefe" in w.halter_masse, f"Halter: {w}")
    pruefe(w.halter_link.endswith("/p/302235-6"), f"Link des Halters: {w.halter_link!r}")
    pruefe(not w.geschaetzt, "eingetragene Länge als geschätzt")
pruefe(len(b.aufspannungen) == 1, f"Aufspannungen: {len(b.aufspannungen)}")
a = b.aufspannungen[0]
pruefe([s.name for s in a.schritte] == ["Lang", "Tief"], f"Schritte: {a.schritte}")
pruefe(all(s.werkzeug == "T3 Kugel 6" and not s.lage for s in a.schritte), f"{a.schritte}")
lang = a.schritte[0].minuten
pruefe(1.67 < lang < 1.75, f"1000 mm in F 10 mm/s: {lang:.3f} min")
pruefe(a.schritte[0].werte.startswith("S "), f"Werte: {a.schritte[0].werte}")
pruefe(
    a.rohteil == "Quader 54 × 44 × 33 mm (Aufmaß oben 0, seitlich 2, unten 3 mm)",
    f"Rohteil: {a.rohteil}",
)
pruefe(a.spannung == "Schraubstock, 5 mm von unten gespannt", f"Spannung: {a.spannung}")
pruefe(a.nullpunkt == "Mitte oben des Rohteils", f"Nullpunkt: {a.nullpunkt}")
# Das Nullpunkt-Register des Jobs (CAM: Fixtures), die Kühlung je Schritt (ohne: leer), der
# Werkstoff im Kopf (ohne Werkstoff am Rohteil: „nicht eingetragen“).
pruefe(a.register == "G54", f"Register: {a.register!r}")
job.Operations.Group[0].CoolantMode = "Flood"
b2 = eb.blatt(job, "2026-10-16", "0.0.0", bibliothek)
pruefe(
    [s.kuehlung for s in b2.aufspannungen[0].schritte] == ["Flut", ""],
    f"Kühlung: {[s.kuehlung for s in b2.aufspannungen[0].schritte]}",
)
job.Operations.Group[0].CoolantMode = "None"
pruefe(b.werkstoff == "nicht eingetragen", f"Werkstoff: {b.werkstoff!r}")
pruefe(
    any("„Tief“" in h and "knapp" not in h and "26" in h for h in b.hinweise),
    f"Hinweise: {b.hinweise}",
)
seite = eb.html(b, tr, laenge, minuten_text)
for text in ("T3", "Kugel 6", "<b>27</b>", "Mitte oben", "Lang", "Tief", "Summe", "G54",
             "Werkstoff: nicht eingetragen", "Kühlung",
             "<a href='https://www.hoffmann-group.com/DE/de/hom/p/302235-6'>im Katalog</a>"):  # fmt: skip
    pruefe(text in seite, f"„{text}“ fehlt auf der Seite")


def mit_rohteil(box):
    return types.SimpleNamespace(Stock=types.SimpleNamespace(Shape=box))


# Nullpunkt an einer Ecke, an einer Kante, dann irgendwo.
for box, erwartet in (
    (Part.makeBox(54, 44, 33), "Ecke links vorne unten des Rohteils"),
    (
        Part.makeBox(54, 44, 33, FreeCAD.Vector(-54, -22, -33)),
        "Kante rechts oben, Mitte des Rohteils",
    ),
    (
        Part.makeBox(54, 44, 33, FreeCAD.Vector(-7, -2, -33)),
        "X 7 mm von links · Y 2 mm von vorne · Z oben",
    ),
):
    text = eb.nullpunkt_text(mit_rohteil(box), tr)
    pruefe(text.startswith(erwartet), f"Nullpunkt: {text!r} statt {erwartet!r}")

# Eine geschwenkte Ebene (3+2) gehört zur Aufspannung des Grundjobs: ihre Schritte unter einer
# Zwischenzeile mit den Rundachsen.
ebene = PathJob.Create("Ebene", [teil])
for name, art in (("Grundjob", "App::PropertyLink"), ("Ebene", "App::PropertyPlacement"),
                  ("Rundachsen", "App::PropertyString")):  # fmt: skip
    ebene.addProperty(art, name, "CAM-Addon")
ebene.Grundjob = job
ebene.Rundachsen = "A-30 C90"
ebene.Label = "Seite rechts"
op = PathCustom.Create("Schräg", parentJob=ebene)
op.Gcode = ["G0 X0 Y0 Z5", "G1 Z-1 F10", "G1 X10 F10", "G0 Z5"]
op.ToolController = tc
doc.recompute()
pruefe(sw.ist_ebene(ebene) and eb.grundjob(ebene) is job, "Ebene nicht erkannt")
b = eb.blatt(ebene, "2026-10-16", "0.0.0", bibliothek)
pruefe(len(b.aufspannungen) == 1, f"mit Ebene: {len(b.aufspannungen)} Aufspannungen")
lagen = [(s.name, s.lage) for s in b.aufspannungen[0].schritte]
pruefe(
    lagen == [("Lang", "Ohne Schwenken"), ("Tief", "Ohne Schwenken"),
              ("Schräg", "Ebene „Seite rechts“ – A-30 C90")],  # fmt: skip
    f"Lagen: {lagen}",
)
seite = eb.html(b, tr, laenge, minuten_text)
pruefe(seite.count("class='lage'") == 2, "Zwischenzeilen der Lagen")
doc.removeObject(op.Name)
doc.removeObject(ebene.Name)
doc.recompute()

# Ohne Werkzeugverwaltung: das Werkzeug heißt wie in CAM (ohne „T3 “ vorn); kein Halter.
ohne = eb.blatt(job, "2026-10-16", "0.0.0", wz.Bibliothek([]))
pruefe(
    ohne.werkzeuge
    and ohne.werkzeuge[0].name == tc.Tool.Label.removeprefix("T3 ")
    and not ohne.werkzeuge[0].halter,
    f"ohne Werkzeugverwaltung: {ohne.werkzeuge}",
)

# --- Stehender Zylinder im Dreibackenfutter ------------------------------------------------------
lage = FreeCAD.Placement(FreeCAD.Vector(0, 0, -33), FreeCAD.Rotation())
neu = PathStock.CreateCylinder(job, 32.0, 33.0, lage)
alt = job.Stock
job.Stock = neu
doc.removeObject(alt.Name)
doc.recompute()
pruefe(eb.rohteil_text(job, tr) == "Zylinder Ø 64 × 33 mm, stehend", f"{eb.rohteil_text(job, tr)}")
pruefe(
    eb.spannung_text(job, tr)
    == "Dreibackenfutter Ø 125 (hebt das Teil um 66 mm), 5 mm von unten gespannt",
    f"{eb.spannung_text(job, tr)}",
)
FreeCAD.closeDocument(doc.Name)

# --- Rundstange (4-Achs) und N-Kant-Stange in Worten ---------------------------------------------
stange = types.SimpleNamespace(
    Radius=20.0,
    Height=120.0,
    Placement=FreeCAD.Placement(FreeCAD.Vector(), FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), 90)),
    Shape=Part.makeCylinder(20, 120),
)
stange.Objects = []
vierachs = types.SimpleNamespace(Stock=stange, **{vr.EIGENSCHAFT_SPANNLAENGE: 30.0})
pruefe(
    eb.rohteil_text(vierachs, tr) == "Rundstange Ø 40 × 120 mm, Achse X",
    f"Stange: {eb.rohteil_text(vierachs, tr)}",
)
pruefe(eb.spannung_text(vierachs, tr) == "Futter der Rundachse, 30 mm gespannt", "Stange spannen")
pruefe(eb.nullpunkt_text(vierachs, tr).startswith("auf der Achse der Stange"), "Stange Nullpunkt")
sechskant = types.SimpleNamespace(
    Stock=types.SimpleNamespace(Shape=Part.makeBox(80, 24, 27.7)),
    **{n_eck.EIGENSCHAFT_N: 6, n_eck.EIGENSCHAFT_AUFSPANNUNG: 2, n_eck.EIGENSCHAFT_SPANNLAENGE: 15},
)
pruefe(
    eb.rohteil_text(sechskant, tr) == "6-Kant-Stange, Schlüsselweite 24 × 80 mm",
    f"N-Kant: {eb.rohteil_text(sechskant, tr)}",
)
pruefe(
    eb.spannung_text(sechskant, tr) == "Schraubstock am Ende der Stange, 15 mm gespannt",
    f"N-Kant spannen: {eb.spannung_text(sechskant, tr)}",
)
pruefe(
    eb.nullpunkt_text(sechskant, tr).startswith("Aufspannung 2 von 6"),
    f"N-Kant Nullpunkt: {eb.nullpunkt_text(sechskant, tr)}",
)

# --- Die Beispiele ------------------------------------------------------------------------------
for datei in (
    "c_ring_nut_3achs.FCStd",
    "platte_zapfen_tasche.FCStd",
    "ring_4achs_planbearbeitung.FCStd",
    "testteil_4achs_nase.FCStd",
):
    beispiel = FreeCAD.openDocument(os.path.join(ADDON, "beispiele", datei), True)
    jobs = [o for o in beispiel.Objects if hasattr(o, "Operations") and eb.grundjob(o) is o]
    pruefe(jobs, f"{datei}: kein Job")
    for job in jobs:
        b = eb.blatt(job, "2026-10-16", "0.0.0", wz.Bibliothek([]))
        erwartet = []
        for aufjob in [job, *sw.aufspannungen_von(job)]:
            erwartet += [op.Label for op, _e in rw.operationen_mit_ebene(aufjob)]
        namen = [s.name for a in b.aufspannungen for s in a.schritte]
        pruefe(namen == erwartet, f"{datei}: Schritte {namen} statt {erwartet}")
        seite = eb.html(b, tr, laenge, minuten_text)
        pruefe(all(eb._e(n) in seite for n in namen), f"{datei}: Schritt fehlt auf der Seite")
        ebenen = {s.lage for a in b.aufspannungen for s in a.schritte if s.lage}
        zeiten = [s.minuten for a in b.aufspannungen for s in a.schritte]
        print(
            f"{datei} {job.Label}: {len(namen)} Schritte, {len(b.werkzeuge)} Werkzeuge, "
            f"{len(ebenen)} Lagen, {sum(zeiten):.1f} min, ohne Zeit {zeiten.count(0.0)}; "
            f"{b.aufspannungen[0].rohteil} | {b.aufspannungen[0].nullpunkt}"
        )
        for a in b.aufspannungen:
            for s in a.schritte:
                print(f"   {s.nummer} {s.name}: {s.minuten:.2f} min, {s.werte}")
    FreeCAD.closeDocument(beispiel.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
