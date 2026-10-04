# Prüft Sprungmarken und Kopf im Programm (D-4; Manuel, 2026-10-04: „um es später im Programm
# leichter zu finden … Sprungpunkte setzen … oben im Kommentar des Programms schon gut Infos, was
# man anspringen kann“; zur Frage, ob jede Marke ein vollständiger Einstieg ist: „Ja, jede Marke
# vollständig“). Ein Kugelfräser Ø 6 im Schrumpffutter, 27 mm Auskragung, in zwei Bearbeitungen
# hintereinander: 10 und 26 mm tief. Siemens: im Kopf die Marken mit ihrer Bearbeitung, das
# Werkzeug mit Auskragung und Halter, „knapp“ nur für die tiefe (26 > 27 − 2); vor jeder
# Bearbeitung ihre Marke und danach ein vollständiger Einstieg – Wechselpunkt, T3 M6, Spindel
# –, auch beim zweiten Mal mit demselben Werkzeug. Ohne den Haken einmal T3 M6. Fanuc: N1, N2 –
# mit Satznummern nicht nummeriert. Die Namen der Marken: groß, ohne Umlaute, zwei Buchstaben
# vorn, höchstens 32 Zeichen, jeder nur einmal.
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import halter as hl
from camaddon import job_schnittwerte as js
from camaddon import postprozessor as pp
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")

# --- Die Namen der Marken ------------------------------------------------------------------------
vergeben = set()
namen = [pp.markenname(n, vergeben) for n in ("Räumen T1", "Räumen T1", "3D-Schruppen", "x" * 40)]
pruefe(
    namen[:3] == ["RAEUMEN_T1", "RAEUMEN_T1_2", "OP_3D_SCHRUPPEN"] and len(namen[3]) == 32,
    f"Marken: {namen}",
)

# --- Ein Job mit zwei Bearbeitungen desselben Werkzeugs -----------------------------------------
import Path.Main.Job as PathJob  # noqa: E402
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
schrumpf.kennung = "halter-schrumpf-kopf"
bibliothek.halter.append(schrumpf)
kugel.halter = schrumpf.kennung
kugel.laenge_spindelnase = float(schrumpf.laenge) + 27.0
bibliothek.speichern()
ue.uebergeben(bibliothek)

doc = FreeCAD.newDocument("Programmkopf")
teil = doc.addObject("Part::Feature", "Teil")
teil.Shape = Part.makeBox(50, 50, 30)
doc.recompute()
job = PathJob.Create("Job", [teil])
job.Stock.ExtZpos = 0.0
doc.recompute()
oben = float(job.Stock.Shape.BoundBox.ZMax)
ops = []
for name, tiefe in (("Flach", 10.0), ("Tief", 26.0)):
    op = PathCustom.Create(name)  # vor dem eigenen Controller: mit zweien fragte FreeCAD nach
    op.Gcode = [
        f"G0 X10 Y10 Z{oben + 5}",
        f"G1 Z{oben - tiefe} F100",
        "G1 X20 F100",
        f"G0 Z{oben + 5}",
    ]
    ops.append(op)
tc = js.controller_ohne_transaktion(doc, job, kugel, kugel.schnittwerte[wz.ALLE][0])
for op in ops:
    op.ToolController = tc
doc.recompute()
teile = pp.abschnitte(job)
pruefe(len(teile) == 2, f"Abschnitte: {[t.name for t in teile]}")
info = pp.Maschineninfo("Fräse", wechselpunkt={"Z": 250.0})
zeilen = pp.programm(teile, pp.steuerung("siemens"), info, "Kopf").zeilen
text = "\n".join(zeilen)
print(text[:1200])
pruefe(
    "; Sprungmarken" in text and ";   FLACH – Flach" in text and ";   TIEF – Tief" in text,
    "Marken im Kopf",
)
pruefe(
    any("T3 Kugel 6 – Auskragung 27 mm, Schrumpffutter" in z for z in zeilen),
    f"Werkzeug im Kopf: {[z for z in zeilen if z.startswith(';   T')]}",
)
knapp = [z for z in zeilen if "knapp" in z]
pruefe(len(knapp) == 1 and "„Tief“" in knapp[0] and "26.0" in knapp[0], f"knapp: {knapp}")
pruefe(zeilen.count("FLACH:") == 1 and zeilen.count("TIEF:") == 1, "Marken fehlen")
pruefe(zeilen.count("T3 M6") == 2, f"vollständiger Einstieg: {zeilen.count('T3 M6')}-mal T3 M6")
i_tief = zeilen.index("TIEF:")
nach = zeilen[i_tief : i_tief + 8]
pruefe(
    any(z.startswith("G0 SUPA") for z in nach)
    and "T3 M6" in nach
    and any(z.startswith("M3 S") for z in nach),
    f"nach TIEF: {nach}",
)
ohne = pp.programm(teile, pp.steuerung("siemens", {"marken": False}), info, "Kopf").zeilen
pruefe(ohne.count("T3 M6") == 1 and "TIEF:" not in ohne, "ohne Haken: Marken oder T3 M6")
fanuc = pp.programm(teile, pp.steuerung("fanuc", {"satznummern": True}), info, "Kopf").zeilen
pruefe(
    "N1" in fanuc and "N2" in fanuc,
    f"Fanuc: {[z for z in fanuc if z.startswith('N') and ' ' not in z]}",
)

FreeCAD.closeDocument(doc.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
