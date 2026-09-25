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
from Path.Tool import Controller
from Path.Tool.camassets import cam_assets, user_asset_store

from camaddon import job_schnittwerte as js
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
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
dok.recompute()
job = Job.Create("Job", [quader])
job.Stock.ShapeMaterial = Materials.MaterialManager().getMaterial(
    ue.freecad_werkstoffe()["1.4301"][0]
)

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
pruefe(gesetzt == 2, f"{gesetzt} gesetzt statt 2 (ohne vc/fz nichts)")
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

FreeCAD.closeDocument(dok.Name)
sprache.setze_sprache(vorher_sprache)
if fehler:
    raise AssertionError("\n".join(fehler))
# FreeCADCmd 1.1.3 schreibt beim Neuberechnen einen Fortschrittsbalken ohne
# Zeilenende – „OK“ muss auf einer eigenen Zeile stehen (scripts/tests_ausfuehren.sh).
print()
print("OK", os.path.basename(__file__))
