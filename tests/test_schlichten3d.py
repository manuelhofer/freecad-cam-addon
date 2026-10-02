# Prüft „3D-Schlichten“ (W-006 4.2 Punkt 3): Platte 60 × 60 × 10 mit einer Kuppel (Kugel R 25,
# Mitte (30, 30, −5): Fuß Ø 40 auf z 10, oben z 20). Die Kugelfläche ist eine Freiformfläche, die
# Oberseite der Platte und ihre Seiten nicht. Ein Kugelfräser Ø 6, Grathöhe 0,01: Zeilenabstand
# 0,49; die Spitze nie unter der Platte (z ≥ 10). Im Quader – vorher die Kuppel mit 0,3 Aufmaß –
# liegt danach jede Stelle der Kuppel höchstens 0,04 über ihr und nirgends darunter (nichts ins
# Teil); die Platte daneben bleibt, wie sie war. Mit Aufmaß 0,2 bleiben 0,2 senkrecht zur
# Fläche (auf der Kuppel senkrecht gemessen 0,2 / cos θ). Längs x, längs y, als Spirale und
# entlang der Fläche gerechnet, die schnellste zählt – an der Kuppel entlang der Fläche (die
# Breitenkreise, gleich weit auseinander, flach wie steil: ohne Höhenlinien und Wenden, um 5 %
# schneller als die Spirale), die Spirale schneller als Zeilen; im Quader alle so gut wie die
# Zeilen. Steil/Flach an einer Halbkugel R 15 (am Fuß senkrecht): Mit Höhenlinien, wo es steiler
# ist als 45°, bleibt an der Flanke höchstens 0,035 stehen, entlang der Fläche ebenso, mit Zeilen
# allein mehr als 0,045. Eine Welle am Rand eines Blocks ohne Platte: nirgends ins Teil, auch nicht
# an der Außenkante. Dann die Operation im Job: „3D-Schlichten T3“, Art „schlichten3d“.
import math
import os
import pathlib
import sys
import tempfile
import time

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import job_schnittwerte as js
from camaddon import restmaterial as rm
from camaddon import schlichten3d as s3op
from camaddon import schlichten3d_bahn as s3
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_flaechen as vf
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")

platte = Part.makeBox(60, 60, 10)
kappe = Part.makeSphere(25, V(30, 30, -5)).common(Part.makeBox(60, 60, 15, V(0, 0, 10)))
teil = platte.fuse(kappe).removeSplitter()
kugel = [f"Face{i + 1}" for i, f in enumerate(teil.Faces) if isinstance(f.Surface, Part.Sphere)]
andere = [f"Face{i + 1}" for i, f in enumerate(teil.Faces) if f"Face{i + 1}" not in kugel]
pruefe(len(kugel) >= 1, f"Kugelflächen: {kugel}")
pruefe(all(s3.ist_freiform(teil, n) for n in kugel), "Kuppel keine Freiformfläche")
pruefe(not any(s3.ist_freiform(teil, n) for n in andere), "Platte als Freiformfläche")

form = ff.kugel(3.0)
abstand = s3.zeilenabstand(form, 0.01)
pruefe(abs(abstand - 2 * math.sqrt(2 * 3 * 0.01 - 0.0001)) < 1e-3, f"Abstand {abstand}")


def werte(**weiter):
    grund = {"form": form, "oben": 20.0, "sicher": 25.0, "vorschub": 1000.0, "eintauchen": 300.0}
    grund.update(weiter)
    return s3.Schlichtwerte(**grund)


t0 = time.time()
bahn = s3.planen(teil, kugel, werte())
print(ascii(f"{bahn.zeilen} Zeilen, {bahn.umlaeufe} Umläufe, {bahn.hoehenlinien} Höhen, "
            f"{bahn.zeit:.2f} min"))  # fmt: skip
print(ascii(f"Rechenzeit {time.time() - t0:.1f} s"))
nur_zeilen = s3.planen(teil, kugel, werte(grenzwinkel=0.0))
pruefe(70 <= nur_zeilen.zeilen <= 100, f"Zeilen {nur_zeilen.zeilen}")
pruefe(not nur_zeilen.spirale, "ohne Steil/Flach eine Spirale – sie hinterließe an Flanken mehr")
pruefe(bahn.z_min >= 10.0 - 1e-6, f"unter der Platte: {bahn.z_min}")
nur_x = s3.planen(teil, kugel, werte(richtung="x"))
nur_y = s3.planen(teil, kugel, werte(richtung="y"))
spirale = s3.planen(teil, kugel, werte(richtung="spirale"))
flaeche = s3.planen(teil, kugel, werte(richtung="flaeche"))
pruefe(nur_zeilen.hoehenlinien == 0 and spirale.hoehenlinien > 0, "Höhenlinien")
pruefe(nur_x.laengs_x and not nur_y.laengs_x, "Richtung nicht wie verlangt")
pruefe(
    spirale.spirale and not nur_x.spirale and spirale.zeilen == 0 and spirale.umlaeufe > 30,
    f"Spirale: {spirale.spirale}, {spirale.zeilen} Zeilen, {spirale.umlaeufe} Umläufe",
)
# Entlang der Kuppel: die Breitenkreise – der Bogen vom Fuß bis oben (25 · 0,927 = 23,2) durch
# den Abstand 0,49, also etwa 48 Kurven, jede geschlossen und mit dem Material rechts.
pruefe(
    flaeche.flaeche and 40 <= flaeche.zeilen <= 52 and flaeche.hoehenlinien == 0,
    f"entlang der Fläche: {flaeche.flaeche}, {flaeche.zeilen} Kurven",
)
pruefe(
    bahn.zeit <= min(nur_x.zeit, nur_y.zeit, spirale.zeit, flaeche.zeit) + 1e-9,
    "nicht die schnellste",
)
pruefe(bahn.flaeche and flaeche.zeit < 0.95 * spirale.zeit, f"Fläche {flaeche.zeit:.2f} min, "
       f"Spirale {spirale.zeit:.2f}")  # fmt: skip
pruefe(spirale.zeit < 0.95 * nur_x.zeit, f"Spirale {spirale.zeit:.2f}, Zeilen {nur_x.zeit:.2f}")
print(ascii(f"Fläche {flaeche.zeit:.2f} min ({flaeche.zeilen} Kurven), Spirale "
            f"{spirale.zeit:.2f} min ({spirale.umlaeufe} Umläufe), längs x {nur_x.zeit:.2f}"))  # fmt: skip
# Die Kreise im Gleichlauf: um die Kuppel im Uhrzeigersinn (von oben), das Material rechts.
pv = [p for p in flaeche.punkte if not p.eilgang]
drehung = sum(
    (a.x - 30) * (b.y - 30) - (a.y - 30) * (b.x - 30)
    for a, b in zip(pv, pv[1:], strict=False)
    if math.hypot(a.x - b.x, a.y - b.y) < 2.0
)
pruefe(drehung < 0, f"entlang der Fläche gegen den Uhrzeigersinn ({drehung:.0f})")
try:
    s3.planen(teil, andere, werte())
except ValueError as grund:
    pruefe("Keine Freiformfläche" in str(grund), f"ohne Freiform: {grund}")
else:
    pruefe(False, "ohne Freiform: kein Satz")


# --- Im Quader: die Kuppel mit 0,3 Aufmaß, danach fertig ----------------------------------------
netz = vf.vernetze(teil, 0.005).netz


def quader_nach(bahn_, aufmass_vorher=0.3):
    q = rm.Quader(0, 60, 0, 60, 0, 20.5, schritt=0.25)
    soll = hf.hoehen(netz, q.x, q.y)
    q.h[:] = np.minimum(soll + aufmass_vorher, 20.5)
    punkte = bahn_.punkte
    von = [(a.x, a.y, a.z) for a, b in zip(punkte, punkte[1:], strict=False) if not b.eilgang]
    nach = [(b.x, b.y, b.z) for a, b in zip(punkte, punkte[1:], strict=False) if not b.eilgang]
    q.fahre_stuecke(von, nach, form)
    return q, soll


for name, geprueft in (("auto", bahn), ("längs x", nur_x), ("Spirale", spirale)):
    q, soll = quader_nach(geprueft)
    xs, ys = np.meshgrid(q.x, q.y, indexing="ij")
    r = np.hypot(xs - 30, ys - 30)
    rest = q.h - soll
    kuppel = r < 18.0  # fern vom Fuß
    pruefe(np.max(rest[kuppel]) < 0.04, f"{name}: stehen geblieben {np.max(rest[kuppel]):.3f}")
    pruefe(np.min(rest) > -0.02, f"{name}: ins Teil {np.min(rest):.3f}")
    platte_fern = r > 25.0  # die Platte weit neben der Kuppel: nicht gewählt, nicht gefräst
    pruefe(np.all(np.abs(rest[platte_fern] - 0.3) < 1e-9), f"{name}: Platte angeschnitten")
    print(ascii(f"Kuppel {name}: Rest {np.min(rest[kuppel]):.3f} … {np.max(rest[kuppel]):.3f}"))

# Das Aufmaß gilt senkrecht zur Fläche: auf der Kuppel senkrecht gemessen 0,2 / cos θ, mit
# cos θ = √(25² − r²) / 25 (oben 0,2, bei r 16 schon 0,26).
mit_aufmass = s3.planen(teil, kugel, werte(aufmass=0.2))
q2, _soll = quader_nach(mit_aufmass)
rest2 = q2.h - soll
innen = r < 16.0
erwartet = 0.2 * 25.0 / np.sqrt(625.0 - r[innen] ** 2)
abweichung = rest2[innen] - erwartet
pruefe(
    np.min(abweichung) > -0.02 and np.max(abweichung) < 0.04,
    f"Aufmaß 0,2: {np.min(abweichung):.3f} … {np.max(abweichung):.3f} neben dem Soll",
)

# --- Steil/Flach an der Halbkugel ---------------------------------------------------------------
halb = Part.makeSphere(15, V(30, 30, 10)).common(Part.makeBox(60, 60, 20, V(0, 0, 10)))
teil_h = Part.makeBox(60, 60, 10).fuse(halb).removeSplitter()
kugel_h = [f"Face{i + 1}" for i, f in enumerate(teil_h.Faces) if isinstance(f.Surface, Part.Sphere)]
netz_h = vf.vernetze(teil_h, 0.005).netz
for grenz, richtung in ((0.0, "auto"), (45.0, "x"), (45.0, "flaeche")):
    bahn_h = s3.planen(
        teil_h, kugel_h, werte(grenzwinkel=grenz, richtung=richtung, oben=25.0, sicher=30.0)
    )
    q_h = rm.Quader(0, 60, 0, 60, 0, 25.5, schritt=0.25)
    soll_h = hf.hoehen(netz_h, q_h.x, q_h.y)
    q_h.h[:] = np.minimum(soll_h + 0.3, 25.5)
    pk = bahn_h.punkte
    q_h.fahre_stuecke(
        [(a.x, a.y, a.z) for a, b in zip(pk, pk[1:], strict=False) if not b.eilgang],
        [(b.x, b.y, b.z) for a, b in zip(pk, pk[1:], strict=False) if not b.eilgang],
        form,
    )
    xs_h, ys_h = np.meshgrid(q_h.x, q_h.y, indexing="ij")
    r_h = np.hypot(xs_h - 30, ys_h - 30)
    rest_h = q_h.h - soll_h
    flanke = rest_h[(r_h > 11) & (r_h < 14)]
    # Bis r 14 (69°): nichts ins Teil – näher am senkrechten Fuß misst das Raster nicht genau.
    name = f"{grenz:g}° {richtung}"
    pruefe(np.min(rest_h[r_h < 14]) > -0.02, f"{name}: ins Teil {np.min(rest_h[r_h < 14]):.3f}")
    pruefe(np.max(rest_h[r_h < 9]) < 0.03, f"{name}: oben {np.max(rest_h[r_h < 9]):.3f}")
    if richtung == "flaeche":
        pruefe(np.max(flanke) < 0.035, f"entlang der Fläche: Flanke {np.max(flanke):.3f}")
        pruefe(bahn_h.flaeche and bahn_h.hoehenlinien == 0, "entlang der Fläche: Höhenlinien")
    elif grenz:
        pruefe(np.max(flanke) < 0.035, f"Steil/Flach: Flanke {np.max(flanke):.3f}")
        pruefe(bahn_h.hoehenlinien > 10, f"Höhen {bahn_h.hoehenlinien}")
    else:
        pruefe(np.max(flanke) > 0.045, f"nur Zeilen: Flanke {np.max(flanke):.3f}")
    print(ascii(f"Halbkugel {name}: Flanke {np.max(flanke):.3f}, {bahn_h.zeit:.2f} min"))

# --- Am Rand ohne Platte: nicht über die Kante rollen --------------------------------------------
# Ein Block 60 × 40, oben eine Welle (B-Spline, z 15 ± 4), ohne Platte daneben: Wo die Kugel
# nur noch über die Außenkante rollt, fällt die Hüllfläche fast senkrecht – aus dem Raster
# gerechnet, schnitten Höhenlinien und Spirale dort 0,05 mm in die Seite (an der Kante 0,32
# senkrecht gemessen). Jetzt fahren sie nur, wo der Fräser die Welle innen berührt: in jeder
# Richtung nirgends ins Teil, die Welle fertig.
pole = [
    [V(i * 10.0, j * 10.0, 15.0 + 4.0 * math.sin(i * math.pi / 3) * math.cos(j * math.pi / 4))
     for j in range(5)]
    for i in range(7)
]  # fmt: skip
welle_flaeche = Part.BSplineSurface()
welle_flaeche.interpolate(pole)
block = welle_flaeche.toShape().extrude(V(0, 0, -30)).common(Part.makeBox(60, 40, 40))
block = block.removeSplitter()
welle = [
    f"Face{i + 1}" for i, f in enumerate(block.Faces) if isinstance(f.Surface, Part.BSplineSurface)
]
netz_w = vf.vernetze(block, 0.005).netz
for richtung in ("auto", "spirale", "x"):
    bahn_w = s3.planen(block, welle, werte(richtung=richtung))
    q_w = rm.Quader(0, 60, 0, 40, 0, 20.5, schritt=0.2)
    soll_w = hf.hoehen(netz_w, q_w.x, q_w.y)
    q_w.h[:] = np.minimum(soll_w + 0.3, 20.5)
    pw = bahn_w.punkte
    q_w.fahre_stuecke(
        [(a.x, a.y, a.z) for a, b in zip(pw, pw[1:], strict=False) if not b.eilgang],
        [(b.x, b.y, b.z) for a, b in zip(pw, pw[1:], strict=False) if not b.eilgang],
        form,
    )
    rest_w = q_w.h - soll_w
    innen_w = rest_w[5:-5, 5:-5]  # 1 mm vom Rand: dort darf die Kugel nicht hin (Radius 3)
    pruefe(np.min(rest_w) > -0.02, f"Welle {richtung}: ins Teil {np.min(rest_w):.3f}")
    pruefe(np.percentile(innen_w, 99) < 0.03, f"Welle {richtung}: Rest {np.max(innen_w):.3f}")
    print(ascii(f"Welle {richtung}: {bahn_w.zeit:.2f} min, ins Teil {np.min(rest_w):.3f}, Rest "
                f"bis {np.percentile(innen_w, 99):.3f} (99 %)"))  # fmt: skip

# --- Die Operation im Job -----------------------------------------------------------------------
import Path.Main.Job as PathJob

t3 = wz.Werkzeug(
    nummer=3,
    name="Kugel 6",
    art=wz.KUGELFRAESER,
    durchmesser=6.0,
    schneiden=2,
    schneidenlaenge=12.0,
    schneidstoff=wz.VHM,
)
t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([wz.standardwerkzeug(), t3]))
doc = FreeCAD.newDocument("Kuppel")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
tc = js.controller_ohne_transaktion(doc, job, t3, t3.schnittwerte[wz.ALLE][0])
doc.recompute()
op = s3op.lege_an(job, tc, 0.01, flaechen=kugel)
doc.recompute()
pruefe(op.Label == "3D-Schlichten T3", f"Name {op.Label}")
pruefe(
    op.Zeilen == bahn.zeilen and op.Umlaeufe == bahn.umlaeufe,
    f"Zeilen {op.Zeilen}, Umläufe {op.Umlaeufe} statt {bahn.zeilen}, {bahn.umlaeufe}",
)
pruefe(abs(float(op.FinalDepth) - 10.0) < 1e-6, f"Endtiefe {float(op.FinalDepth)}")
pruefe(js.operationsart(op) == "schlichten3d", f"Art {js.operationsart(op)}")
print(ascii(f"Operation: {len(op.Path.Commands)} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
