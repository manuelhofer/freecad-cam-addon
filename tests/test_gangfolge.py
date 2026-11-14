# Prüft die Folge der Schlichtgänge (gangfolge, leerfahrt; Manuel, 2026-11-14: „erstes vorschlichten
# ... und danach nochmal erstes vorschlichten .... dann messsen ... dann vertigschlichten ... und
# dann nochmal vertig schlichten ... dann hat man immer 100 % das richtige mass“).
# Eine Platte 80 × 80 × 10 mit einem Klotz 40 × 30 × 10 darauf, ringsum mit 0,3 geschruppt. Der
# Wandzug (Kontur, nur der Schlichtzug) mit dem halben Aufmaß 0,15; daraus die Folge: Leerfahrt,
# Messstopp, derselbe Schnitt auf Maß, Leerfahrt.
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part
import Path.Main.Job as PathJob
from Path.Tool.camassets import user_asset_store

from camaddon import gangfolge as gf
from camaddon import job_schnittwerte as js
from camaddon import kontur as ko
from camaddon import leerfahrt as lf
from camaddon import messstopp as ms
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
V = FreeCAD.Vector
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
fraeser = wz.standardwerkzeug()
ue.uebergeben(wz.Bibliothek([fraeser]))
doc = FreeCAD.newDocument("Gangfolge")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = (
    Part.makeBox(80, 80, 10).fuse(Part.makeBox(40, 30, 10, V(20, 25, 10))).removeSplitter()
)
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
schruppen = next(e for e in fraeser.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
schlichten = next(e for e in fraeser.einsaetze(wz.ALLE) if e.art == wz.SCHLICHTEN)
tc_r = js.controller_ohne_transaktion(doc, job, fraeser, schruppen)
tc_s = js.controller_ohne_transaktion(doc, job, fraeser, schlichten)
form = job.Model.Group[0].Shape
waende = [
    f"Face{i + 1}"
    for i, f in enumerate(form.Faces)
    if isinstance(f.Surface, Part.Plane)
    and abs(f.normalAt(0.5, 0.5).z) < 1e-6
    and f.BoundBox.ZMin > 9.9
]
pruefe(len(waende) == 4, f"Wände: {waende}")


def fahrten(op):
    return [(b.Name, sorted(b.Parameters.items())) for b in op.Path.Commands if b.Name in lf.FAHREN]


def naechste_wand(op):
    """Der kleinste Abstand der Fräsermitte zum Klotz (x 20 … 60, y 25 … 55) auf der Endtiefe."""
    beste = 1e9
    for b in op.Path.Commands:
        p = b.Parameters
        if b.Name in ("G1", "G01", "G2", "G02", "G3", "G03") and "X" in p and "Y" in p:
            dx = max(20.0 - p["X"], 0.0, p["X"] - 60.0)
            dy = max(25.0 - p["Y"], 0.0, p["Y"] - 55.0)
            beste = min(beste, (dx * dx + dy * dy) ** 0.5)
    return beste


# Schruppen ringsum mit 0,3, dann der erste Schlichtschnitt: nur der Zug an der Wand, 0,15 bleiben.
grob = ko.lege_an(job, tc_r, 10.0, schruppen.ae, aufmass=0.3, schlichten=False, flaechen=waende)
doc.recompute()
halb = gf.halbes_aufmass(0.3)
pruefe(abs(halb - 0.15) < 1e-9, f"halbes Aufmaß {halb}")
pruefe(
    abs(gf.halbes_aufmass(0.5, 0.1) - 0.3) < 1e-9,
    f"halb zwischen 0,5 und 0,1: {gf.halbes_aufmass(0.5, 0.1)}",
)
# Wie „Schlichten danach“: Breite = Aufmaß des Schruppens (nur der Zug an der Wand), dazu der Rest.
vor = ko.lege_an(job, tc_s, 10.0, 0.3, 0.3, True, 0.3, flaechen=waende, rest=halb)
doc.recompute()
pruefe(len(fahrten(vor)) > 4, f"erster Schnitt: {len(fahrten(vor))} Sätze")
pruefe(
    abs(naechste_wand(vor) - (6.0 + halb)) < 0.01, f"erster Schnitt bei {naechste_wand(vor):.3f}"
)

stopps = []


def stopp_anlegen(davor, danach):
    stopps.append((davor.Label, danach.Label))
    return ms.lege_an(job, davor.ToolController, danach.ToolController)


folge = gf.folge(job, [vor], aufmass_ende=0.0, leerfahrt=True, stopp_anlegen=stopp_anlegen)
doc.recompute()
reihe = list(job.Operations.Group)
namen_ = [o.Label for o in reihe]
print("Folge:", namen_)
pruefe(
    len(folge.leer_vor) == 1 and len(folge.fertig) == 1 and len(folge.leer_fertig) == 1,
    f"Folge: {namen_}",
)
erwartet = [grob, vor, folge.leer_vor[0], folge.stopp, folge.fertig[0], folge.leer_fertig[0]]
pruefe([o.Name for o in reihe] == [o.Name for o in erwartet], f"Reihenfolge: {namen_}")
pruefe(folge.stopp is not None and ms.ist_messstopp(folge.stopp), "kein Messstopp dazwischen")
pruefe(stopps == [(folge.leer_vor[0].Label, vor.Label)], f"Messstopp nach der Leerfahrt: {stopps}")
# Die Leerfahrt: derselbe Schnitt, Satz für Satz, mit demselben Werkzeug.
leer = folge.leer_vor[0]
pruefe(lf.ist_leerfahrt(leer) and not lf.ist_leerfahrt(vor), "ist_leerfahrt")
pruefe(fahrten(leer) == fahrten(vor), "Leerfahrt fährt nicht denselben Schnitt")
pruefe(leer.ToolController.Name == vor.ToolController.Name, "Leerfahrt mit anderem Werkzeug")
pruefe(abs(float(leer.Aufmass) - halb) < 1e-9, f"Leerfahrt: Aufmaß {float(leer.Aufmass)}")
pruefe("Leerfahrt" in leer.Label and vor.Label in leer.Label, f"Name: {leer.Label}")
# Der zweite Schnitt: derselbe Zug, 0,15 näher an der Wand – sonst alles gleich.
fertig = folge.fertig[0]
pruefe(
    abs(float(fertig.Schlichtrest)) < 1e-9, f"zweiter Schnitt: Rest {float(fertig.Schlichtrest)}"
)
pruefe(abs(float(fertig.Aufmass) - 0.3) < 1e-9, f"zweiter Schnitt: Aufmass {float(fertig.Aufmass)}")
pruefe(len(fahrten(fertig)) == len(fahrten(vor)), "zweiter Schnitt: andere Zahl Sätze")
pruefe(abs(naechste_wand(fertig) - 6.0) < 0.01, f"zweiter Schnitt bei {naechste_wand(fertig):.3f}")
pruefe(fertig.ToolController.Name == vor.ToolController.Name, "zweiter Schnitt: anderes Werkzeug")
for feld in ("Zustellung", "FinalDepth", "StartDepth"):
    if feld in vor.PropertiesList:
        pruefe(
            abs(float(getattr(vor, feld)) - float(getattr(fertig, feld))) < 1e-9,
            f"zweiter Schnitt: {feld} {getattr(fertig, feld)} statt {getattr(vor, feld)}",
        )
pruefe("auf Maß" in fertig.Label, f"Name: {fertig.Label}")
pruefe(fahrten(folge.leer_fertig[0]) == fahrten(fertig), "Leerfahrt des zweiten Schnitts")
print(f"erster Schnitt {naechste_wand(vor):.3f}, zweiter {naechste_wand(fertig):.3f} mm vor der Wand; "
      f"je {len(fahrten(vor))} / {len(fahrten(fertig))} Sätze")  # fmt: skip

# Ändert sich der Schnitt, fährt die Leerfahrt den neuen (die Verknüpfung rechnet sie mit).
vor.Schlichtrest = 0.2
doc.recompute()
pruefe(
    abs(naechste_wand(leer) - 6.2) < 0.01, f"Leerfahrt nach der Änderung: {naechste_wand(leer):.3f}"
)
pruefe(
    abs(float(leer.Aufmass) - 0.2) < 1e-9, f"Leerfahrt: Aufmaß {float(leer.Aufmass)} nach Änderung"
)
vor.Schlichtrest = halb
doc.recompute()

# Ohne zwei Schnitte: nur die Leerfahrt. Ohne alles: nichts.
nur = gf.folge(job, [fertig], leerfahrt=True)
pruefe(len(nur.alle) == 1 and lf.ist_leerfahrt(nur.alle[0]), f"nur Leerfahrt: {nur.alle}")
pruefe(not gf.folge(job, [fertig]).alle, "ohne Wahl kommt etwas dazu")
# Schon auf Maß: kein zweiter Schnitt, kein Messstopp.
kein = gf.folge(job, [fertig], aufmass_ende=0.0, stopp_anlegen=stopp_anlegen)
pruefe(not kein.alle and len(stopps) == 1, f"schon auf Maß: {kein.alle}")
# Messstopps und Leerfahrten selbst bekommen keine Leerfahrt.
pruefe(gf.schnitte([folge.stopp, leer, vor]) == [vor], "schnitte()")

# Speichern und Laden: Die Leerfahrt kennt ihre Quelle und rechnet wieder.
datei = os.path.join(tempfile.mkdtemp(), "gangfolge.FCStd")
doc.recompute()
doc.saveAs(datei)
name_leer, name_vor = leer.Name, vor.Name
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(datei)
leer, vor = doc.getObject(name_leer), doc.getObject(name_vor)
pruefe(
    lf.ist_leerfahrt(leer) and leer.Quelle is not None and leer.Quelle.Name == name_vor, "geladen"
)
vor.touch()
doc.recompute()
pruefe(fahrten(leer) == fahrten(vor) and len(fahrten(leer)) > 4, "geladen: Leerfahrt rechnet nicht")
# Im Programm steht der Schnitt zweimal hintereinander.
from camaddon import postprozessor as pp

text = pp.programm(pp.abschnitte(doc.Job), pp.steuerung("siemens"), None, "GANGFOLGE").text
pruefe(text.count("M0") >= 1, "kein Halt im Programm")
print(f"Programm: {len(text.splitlines())} Zeilen")
FreeCAD.closeDocument(doc.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
