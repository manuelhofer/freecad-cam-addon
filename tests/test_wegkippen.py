# Prüft das Wegkippen (wegkippen.py, 5 Achsen simultan S4; Manuel, 2026-10-04: „Ja, bauen“): eine
# Kavität 50 × 50, 30 tief, senkrechte Ecken R 10, unten eine Rundung R 8 (gewählt), Kugel Ø 6.
# Mit 2 mm Spiel am Halter und 0,5 am Schaft (Manuel: „auf Save gehen“) muss der Fräser senkrecht
# gut 32 mm herausstehen (der Halter über den Rand); bis 30° gekippt reichen mit ER16 höchstens
# 31 mm, mit dem Schrumpffutter Ø 21 höchstens 25,5 mm. Gegenprobe mit den echten Körpern
# (distToShape): der Halter überall mindestens 1,9 mm vom Teil, der Schaft nirgends drin. Dann als
# „3D-Schlichten“ mit „Wegkippen“, das Schrumpffutter, die kürzeste Auskragung und 1 mm dazu:
# Die Achse kippt, wo es nötig ist; „Kollision prüfen“ auf der Tisch/Tisch-Maschine (die rechte
# Seite mit ihren Ecken) findet den Halter senkrecht am Teil, weggekippt nicht – auch nicht zwischen
# zwei Stellen, wo das Maschinenprogramm Punkte mit gemittelter Achse einsetzt.
import math
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import abfahren as ab
from camaddon import beispielmaschine, sprache
from camaddon import fraeserform as ff
from camaddon import halter as hl
from camaddon import job_schnittwerte as js
from camaddon import kollision as kb
from camaddon import reichweite as rw
from camaddon import schlichten3d as s3op
from camaddon import schlichten3d_bahn as s3
from camaddon import uebergabe_werkzeuge as ue
from camaddon import wegkippen as wk
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
R = 3.0

block = Part.makeBox(120, 120, 45)
kav = Part.makeBox(50, 50, 40, V(35, 35, 15))
kav = kav.makeFillet(10.0, [e for e in kav.Edges if e.BoundBox.ZLength > 1])
kav = kav.makeFillet(
    8.0, [e for e in kav.Edges if abs(e.BoundBox.ZMax - 15) < 1e-6 and e.BoundBox.ZLength < 1e-6]
)
teil = block.cut(kav).removeSplitter()
rund = [f"Face{i + 1}" for i in range(len(teil.Faces)) if s3.ist_freiform(teil, f"Face{i + 1}")]
bahn = s3.planen(
    teil, rund, s3.Schlichtwerte(form=ff.kugel(R), oben=45.0, sicher=50.0, grathoehe=0.05)
)
punkte = np.array([(p.x, p.y, p.z) for p in bahn.punkte if not p.eilgang])
print(ascii(f"Bahn: {len(punkte)} Punkte"))

# --- Die kürzeste Auskragung ------------------------------------------------------------------
er16, schrumpf = hl.aus_vorlage("er16"), hl.aus_vorlage("schrumpf_6")
senkrecht = wk.kuerzeste_auskragung(teil, punkte, R, schrumpf, R, winkel_max=0)
mit_er16 = wk.kuerzeste_auskragung(teil, punkte, R, er16, R, winkel_max=30)
mit_schrumpf = wk.kuerzeste_auskragung(teil, punkte, R, schrumpf, R, winkel_max=30)
print(ascii(f"senkrecht {senkrecht:.2f}, ER16 {mit_er16:.2f}, Schrumpffutter {mit_schrumpf:.2f}"))
pruefe(31.5 <= senkrecht <= 33.0, f"senkrecht {senkrecht}")
pruefe(mit_er16 <= 31.0, f"ER16 bis 30° {mit_er16}")
pruefe(mit_schrumpf <= 25.5, f"Schrumpffutter bis 30° {mit_schrumpf}")

# Gegenprobe: an jeder vierten Stelle Halter und Schaft als Körper.
mitten = punkte[::4] + np.array([0.0, 0.0, R])
huelle = wk.Huelle(teil, 10.5 + mit_schrumpf + 10)
koerper = wk.koerper(schrumpf, R, R, mit_schrumpf)
winkel, richtung, geht = wk.noetig(huelle, mitten, koerper, R, 10.5, 30)
pruefe(geht.all(), f"ohne Neigung an {int((~geht).sum())} Stellen")
form_h, lh = hl.form(schrumpf), float(schrumpf.laenge)
halter_weg, schaft_weg = math.inf, math.inf
for c, a in zip(mitten, wk._gekippt(richtung, winkel), strict=True):
    c, a = V(*c), V(*a)
    h = form_h.copy()
    spitze = c - a * R
    h.Placement = FreeCAD.Placement(
        spitze + a * (mit_schrumpf + lh), FreeCAD.Rotation(V(0, 0, 1), a)
    )
    halter_weg = min(halter_weg, teil.distToShape(h)[0])
    schaft = Part.makeCylinder(R - 0.05, mit_schrumpf - 1.6 * R, c + a * (0.6 * R), a)
    schaft_weg = min(schaft_weg, teil.distToShape(schaft)[0])
print(ascii(f"Gegenprobe: Halter {halter_weg:.2f} mm, Schaft {schaft_weg:.3f} mm weg"))
pruefe(halter_weg >= 1.9, f"Halter nur {halter_weg:.2f} mm vom Teil")
pruefe(schaft_weg > 1e-6, f"Schaft im Teil ({schaft_weg})")

# --- Als Operation, mit „Kollision prüfen“ --------------------------------------------------------
import Path.Main.Job as PathJob  # noqa: E402

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
t3 = wz.Werkzeug(
    nummer=3,
    name="Kugel 6",
    art=wz.KUGELFRAESER,
    durchmesser=6.0,
    schneiden=2,
    schneidenlaenge=12.0,
    gesamtlaenge=60.0,
    schneidstoff=wz.VHM,
)
t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
bibliothek = wz.Bibliothek([t3])
schrumpf.kennung = "halter-schrumpf-test"
bibliothek.halter.append(schrumpf)
t3.halter = schrumpf.kennung
auskragung_soll = math.ceil(mit_schrumpf) + 1.0  # die kürzeste und 1 mm dazu, auf ganze mm
t3.laenge_spindelnase = float(schrumpf.laenge) + auskragung_soll
bibliothek.speichern()
ue.uebergeben(bibliothek)
doc = FreeCAD.newDocument("Wegkippen")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
tc = js.controller_ohne_transaktion(doc, job, t3, t3.schnittwerte[wz.ALLE][0])
doc.recompute()
# Die rechte Seite – ihre Rundung und die beiden Ecken (dort stieß der Halter zuerst an, zwischen
# zwei Stellen, deren Kipprichtung sprang); die ganze Kavität kostete zwei Läufe à 10 min.
rechts = [n for n in rund if teil.getElement(n).BoundBox.Center.x > 70.0]
pruefe(len(rechts) >= 3, f"rechts: {rechts}")
op = s3op.lege_an(job, tc, 0.05, flaechen=rechts)
halter_e, schaft_e, auskragung = wk.einspannung(tc)
pruefe(
    abs(auskragung - auskragung_soll) < 1e-6 and halter_e.kennung == schrumpf.kennung, "Einspannung"
)
op.Wegkippen = True
op.recompute()
achsen = np.array([tuple(v) for v in op.Werkzeugachsen])
bewegt = np.linalg.norm(achsen, axis=1) > 0.5
neigung = np.degrees(np.arccos(np.clip(achsen[bewegt, 2], -1, 1)))
print(
    ascii(
        f"Operation: {len(achsen)} Sätze, gekippt {int((neigung > 0.5).sum())}, bis {neigung.max():.0f}°"
    )
)
pruefe(len(achsen) == len(op.Path.Commands), "Achsen je Satz")
pruefe((neigung > 0.5).sum() > 20 and neigung.max() <= 30.0 + 1e-6, f"Neigung bis {neigung.max()}")

asm, ma = beispielmaschine.fuenfachs_tisch_tisch()
pruefung = rw.Pruefung(asm, ma)
null = rw.nullpunkt(job)


def halter_am_teil():
    fahrt = ab.abfahrt(pruefung, job, null, bibliothek)
    c = [float(st.rund.get("C", 0.0)) for st in fahrt.stationen if not st.ziel]
    print(ascii(f"C {min(c):.0f} ... {max(c):.0f}"))
    befunde = kb.kollision(fahrt, job, null, bibliothek).befunde
    return [b for b in befunde if "Halter" in b.a and b.b == "das Teil"]


gekippt = halter_am_teil()
op.Wegkippen = False
op.recompute()
gerade = halter_am_teil()
print(ascii(f"Halter am Teil: weggekippt {len(gekippt)}, senkrecht {len(gerade)}"))
pruefe(not gekippt, f"weggekippt: {[b.text() for b in gekippt]}")
pruefe(gerade, "senkrecht stößt der Halter nicht an – der Versuch zeigt nichts")

FreeCAD.closeDocument(doc.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
