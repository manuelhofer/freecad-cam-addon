# Prüft „Schnittwerte in den Job“ (W-002 Stufe 2) an einem echten CAM-Job:
# Werkstoff des Rohteils → Werkstoff der Werkzeugverwaltung, TC → Werkzeug
# (über die ToolBit-ID der Übergabe und über T-Nummer/Durchmesser),
# vorgeschlagener Einsatz, Setzen in einer Transaktion samt Strg+Z.
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Materials
import Part  # noqa: F401 – lädt das Part-Modul für „Part::Box“
from Path.Main import Job
from Path.Op import Adaptive, Pocket, Profile, Slot
from Path.Tool import Controller
from Path.Tool.camassets import cam_assets, user_asset_store

from camaddon import job_schnittwerte as js
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkstoffe as ws
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def mm_min(wert):
    return float(wert.getValueAs("mm/min"))


vorher_sprache = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")  # der Name des TC ist deutsch
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
fraeser = wz.Werkzeug(nummer=3, durchmesser=12, schneiden=3, schneidenlaenge=26)
fraeser.schnittwerte[wz.ALLE] = [
    wz.Einsatz(art=wz.VOLLNUT, ae=12, ap=3, vc=120, fz=0.05),
    wz.Einsatz(art=wz.DYNAMISCH, ae=1.2, ap=25, vc=120, fz=0.15),
]
fraeser.eigene_anlegen("1.4301")[0].vc = 80
bohrer = wz.Werkzeug(nummer=7, art=wz.BOHRER, durchmesser=8.5, schneiden=2)
bohrer.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=80, fz=0.1)]
bibliothek = wz.Bibliothek([fraeser, bohrer])
ue.uebergeben(bibliothek)

dok = FreeCAD.newDocument("JobSchnittwerte")
dok.UndoMode = 1
quader = dok.addObject("Part::Box", "Quader")
quader.Height = 60  # höher als jede Zustelltiefe: FreeCAD kürzt sie auf die Höhe
dok.recompute()
job = Job.Create("Job", [quader])
job.Stock.ShapeMaterial = Materials.MaterialManager().getMaterial(
    ue.freecad_werkstoffe()["1.4301"][0]
)
# Die Operationen, solange der Job nur seinen ersten TC hat: Mit mehreren
# fragt FreeCAD 1.1.3 beim Anlegen, welcher – ohne Oberfläche ein Fehler.
operationen = {}
for modul, name in ((Adaptive, "Adaptiv"), (Pocket, "Tasche"), (Profile, "Kontur"), (Slot, "Nut")):
    operationen[name] = modul.Create(name, parentJob=job)

# TC 1: Werkzeug aus der Bibliothek „CAM-Addon“ (ToolBit-ID camaddon_…).
bit = cam_assets.get(f"toolbit://camaddon_{fraeser.kennung}").attach_to_doc(doc=dok)
tc1 = Controller.Create("T3 Schruppen dynamisch", tool=bit, toolNumber=3)
job.Proxy.addToolController(tc1)
# TC 2: ein Bohrer von woanders, aber mit T7 und Ø 8,5.
bit2 = cam_assets.get(f"toolbit://camaddon_{bohrer.kennung}").attach_to_doc(doc=dok)
bit2.ToolBitID = "anderswo"
tc2 = Controller.Create("TC Bohrer", tool=bit2, toolNumber=7)
job.Proxy.addToolController(tc2)
dok.recompute()

pruefe(js.jobs(dok) == [job], f"Jobs: {js.jobs(dok)}")
tcs = js.werkzeug_controller(job)
pruefe(tc1 in tcs and tc2 in tcs, f"TCs: {[t.Label for t in tcs]}")
werkstoff = js.werkstoff_des_jobs(job, bibliothek.alle_werkstoffe())
pruefe(werkstoff is not None and werkstoff.kennung == "1.4301", f"Werkstoff: {werkstoff}")
pruefe(js.werkzeug_von(tc1, bibliothek) is fraeser, "TC 1 nicht über die ToolBit-ID gefunden")
pruefe(js.werkzeug_von(tc2, bibliothek) is bohrer, "TC 2 nicht über T-Nummer/Durchmesser gefunden")

einsaetze = fraeser.einsaetze("1.4301")
pruefe(js.vorgeschlagener_einsatz(tc1, einsaetze, job) == 1, "Einsatz aus dem Namen des TC")
pruefe(js.vorgeschlagener_einsatz(tc2, bohrer.einsaetze("1.4301"), job) == 0, "erste Zeile")
pruefe(js.vorgeschlagener_einsatz(tc2, [], job) == -1, "ohne Zeilen")

vorher = (tc1.SpindleSpeed, mm_min(tc1.HorizFeed))
gesetzt = js.setze(
    dok,
    [
        (tc1, fraeser, einsaetze[0]),
        (tc2, bohrer, bohrer.einsaetze("1.4301")[0]),
        (tc2, fraeser, wz.Einsatz(vc=0, fz=0)),
    ],
)
pruefe(gesetzt == js.Gesetzt(2, []), f"{gesetzt} statt 2 TC (ohne vc/fz nichts)")
pruefe(
    tc1.SpindleSpeed == 2122 and round(mm_min(tc1.HorizFeed)) == 318,
    f"TC 1: {tc1.SpindleSpeed}, {tc1.HorizFeed}",
)
pruefe(round(mm_min(tc1.VertFeed)) == 105, f"TC 1 senkrecht: {tc1.VertFeed}")
pruefe(
    tc2.SpindleSpeed == 2996 and round(mm_min(tc2.VertFeed)) == 599,
    f"TC 2: {tc2.SpindleSpeed}, {tc2.VertFeed}",
)
dok.undo()
pruefe((tc1.SpindleSpeed, mm_min(tc1.HorizFeed)) == vorher, "Strg+Z nimmt nicht alles zurück")

# Operationen: Adaptiv bekommt vom dynamischen Einsatz ae als Schrittweite und
# ap als Zustelltiefe; die Tasche nicht (dynamisch nur ins Adaptive), die
# Kontur nie, die Nut nur von der Vollnut.
for operation in operationen.values():
    operation.ToolController = tc1
dok.recompute()
adaptiv, nut = operationen["Adaptiv"], operationen["Nut"]
schritt = "StepOverPercent" if hasattr(adaptiv, "StepOverPercent") else "StepOver"


def tiefen():
    return {n: float(o.StepDown.getValueAs("mm")) for n, o in operationen.items()}


vorher = tiefen()
gesetzt = js.setze(dok, [(tc1, fraeser, einsaetze[1])], job)
pruefe(gesetzt == js.Gesetzt(1, ["Adaptiv"]), f"mit Operationen: {gesetzt}")
pruefe(getattr(adaptiv, schritt) == 10, f"Adaptiv {schritt}: {getattr(adaptiv, schritt)}")
nachher = tiefen()
pruefe(nachher["Adaptiv"] == 25, f"Adaptiv Zustelltiefe: {nachher['Adaptiv']}")
pruefe(
    all(nachher[n] == vorher[n] for n in ("Tasche", "Kontur", "Nut")),
    f"andere Operationen verändert: {vorher} → {nachher}",
)
pruefe(js.zustellung(nut, fraeser, einsaetze[0]) == {"StepDown": 3}, "Nut mit Vollnut")
pruefe(js.zustellung(operationen["Kontur"], fraeser, einsaetze[1]) == {}, "Kontur bekommt etwas")
# Der Eintauchwinkel des Werkzeugs geht als Helixwinkel ins Adaptiv.
fraeser.eintauchwinkel = 3
helix = js.zustellung(adaptiv, fraeser, einsaetze[1])
pruefe(
    helix.get("HelixMaxRampAngle", helix.get("HelixAngle")) == 3,
    f"Helixwinkel: {helix}",
)
pruefe("HelixMaxRampAngle" not in js.zustellung(nut, fraeser, einsaetze[0]), "Nut mit Helix")
fraeser.eintauchwinkel = 0
# 0,88 mm von Ø 12 sind 7,33 %: abgerundet – in 1.1.3 ganze Prozent.
schmal = js.zustellung(adaptiv, fraeser, wz.Einsatz(art=wz.DYNAMISCH, ae=0.88, ap=24))
soll = 7.3 if schritt == "StepOverPercent" else 7
pruefe(schmal.get(schritt) == soll, f"Schrittweite bei 0,88 mm: {schmal}")


def formel(operation):
    return dict(operation.ExpressionEngine).get("StepDown")


pruefe(formel(adaptiv) is None, f"Formel an der Zustelltiefe: {formel(adaptiv)}")
dok.undo()
dok.recompute()
pruefe(tiefen() == vorher, f"Strg+Z nimmt die Zustelltiefe nicht zurück: {tiefen()}")
pruefe(formel(adaptiv) is not None, "Strg+Z bringt die Formel nicht zurück")
# Ohne Job bleiben die Operationen, wie sie sind.
js.setze(dok, [(tc1, fraeser, einsaetze[1])])
pruefe(tiefen() == vorher, "ohne Job trotzdem Operationen gesetzt")

# Neuer Werkzeug-Controller: benannt nach dem Einsatz, Werkzeug aus der
# Bibliothek, n und vf gesetzt; Strg+Z nimmt ihn samt Werkzeug zurück.
objekte_vorher = len(dok.Objects)
tc3 = js.lege_controller_an(dok, job, fraeser, einsaetze[0])
pruefe((tc3.Label, tc3.ToolNumber) == ("T3 Vollnut", 3), f"neuer TC: {tc3.Label}, {tc3.ToolNumber}")
pruefe(tc3 in js.werkzeug_controller(job), "neuer TC nicht im Job")
pruefe(js.werkzeug_von(tc3, bibliothek) is fraeser, "Werkzeug des neuen TC")
pruefe(
    tc3.SpindleSpeed == 2122 and round(mm_min(tc3.HorizFeed)) == 318,
    f"Werte des neuen TC: {tc3.SpindleSpeed}, {tc3.HorizFeed}",
)
pruefe(js.vorgeschlagener_einsatz(tc3, einsaetze, job) == 0, "Einsatz am Namen nicht erkannt")
dok.undo()
pruefe(len(dok.Objects) == objekte_vorher, f"Strg+Z: {len(dok.Objects)} statt {objekte_vorher}")

# Werkstoff am Rohteil eintragen: C45 statt 1.4301, Strg+Z zurück; ohne
# FreeCAD-Karte mit dieser Nummer geht es nicht.
werkstoffe = bibliothek.alle_werkstoffe()
c45 = next(w for w in werkstoffe if w.nummer == "1.0503")
pruefe(js.nummer_am_rohteil(job) == "1.4301", f"Rohteil vorher: {js.nummer_am_rohteil(job)!r}")
name = js.setze_werkstoff_am_rohteil(dok, job, c45)
pruefe(name is not None and js.nummer_am_rohteil(job) == "1.0503", f"C45 am Rohteil: {name}")
pruefe(js.werkstoff_des_jobs(job, werkstoffe) is c45, "Werkstoff des Jobs danach nicht C45")
dok.undo()
pruefe(js.nummer_am_rohteil(job) == "1.4301", "Strg+Z bringt 1.4301 nicht zurück")
fantasie = ws.Werkstoff("eigen-9", nummer="9.9999", kurzname="Fantasie", eigen=True)
pruefe(js.karte_fuer(fantasie) is None, "Karte für eine Nummer, die FreeCAD nicht kennt")
pruefe(js.setze_werkstoff_am_rohteil(dok, job, fantasie) is None, "ohne Karte gesetzt")

FreeCAD.closeDocument(dok.Name)
sprache.setze_sprache(vorher_sprache)
if fehler:
    raise AssertionError("\n".join(fehler))
# FreeCADCmd 1.1.3 schreibt beim Neuberechnen einen Fortschrittsbalken ohne
# Zeilenende – „OK“ muss auf einer eigenen Zeile stehen (scripts/tests_ausfuehren.sh).
print()
print("OK", os.path.basename(__file__))
