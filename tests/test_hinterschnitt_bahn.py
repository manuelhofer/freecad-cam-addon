# Prüft das Schlichten unter dem Rand (hinterschnitt_bahn.py; Manuel, 2026-10-25: „und dann muss
# mit einem kurgelfräser die wand geschlichtet werden“): Block 80 × 60 × 30, darin eine Tasche,
# unten weiter als oben (die Wände hängen 10° über, Ecken R 6 oben). Die Wände liegen unter dem
# Rand (ueberdeckt), die Oberseite nicht. Eine Kugel R 3 fährt sie in Höhenlinien von oben nach
# unten, die Achse so weit gekippt, dass der Schaft frei bleibt (in den Ecken mehr): Die Kugel
# bleibt R + Aufmaß vom Teil, der Schaft um sein Spiel vom Rand. Die Operation „3D-Schlichten“
# mit „hinterschnitt“: je Satz eine Achse, simultan; aus: keine Achsen. Auf der 5-Achs-Maschine
# Tisch/Tisch geht das Programm.
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

from camaddon import beispielmaschine, sprache
from camaddon import hinterschnitt_bahn as hb
from camaddon import job_schnittwerte as js
from camaddon import reichweite as rw
from camaddon import schlichten3d as s3op
from camaddon import schwenken as sw
from camaddon import simultan_operation as so
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
R = 3.0
D = 20 * math.tan(math.radians(10))


def rundrechteck(b, h, r, z, mx=40.0, my=30.0):
    x0, x1, y0, y1 = mx - b / 2, mx + b / 2, my - h / 2, my + h / 2
    kanten = []
    for (ax, ay), (ex, ey), (cx, cy), w0 in (
        ((x0 + r, y0), (x1 - r, y0), (x1 - r, y0 + r), -90),
        ((x1, y0 + r), (x1, y1 - r), (x1 - r, y1 - r), 0),
        ((x1 - r, y1), (x0 + r, y1), (x0 + r, y1 - r), 90),
        ((x0, y1 - r), (x0, y0 + r), (x0 + r, y0 + r), 180),
    ):
        kanten.append(Part.LineSegment(V(ax, ay, z), V(ex, ey, z)).toShape())
        kreis = Part.Circle(V(cx, cy, z), V(0, 0, 1), r)
        kanten.append(Part.ArcOfCircle(kreis, math.radians(w0), math.radians(w0 + 90)).toShape())
    return Part.Wire(kanten)


unten = rundrechteck(40 + 2 * D, 24 + 2 * D, 6 + D, 10.0)
oben = rundrechteck(40, 24, 6, 30.0)
teil = Part.makeBox(80, 60, 30).cut(Part.makeLoft([unten, oben], True, True)).removeSplitter()
namen = [f"Face{i + 1}" for i in range(len(teil.Faces))]
waende = [
    n
    for n, f in zip(namen, teil.Faces, strict=True)
    if f.BoundBox.ZMin < 10.5
    and f.BoundBox.ZMax > 29.5
    and 1 < f.BoundBox.XMin < f.BoundBox.XMax < 79
]
aussen = next(n for n, f in zip(namen, teil.Faces, strict=True) if f.BoundBox.XMax < 0.1)
oberseite = next(n for n, f in zip(namen, teil.Faces, strict=True) if f.BoundBox.ZMin > 29.9)
pruefe(len(waende) == 8, f"{len(waende)} Wände")
pruefe(all(hb.ueberdeckt(teil, n) for n in waende), "nicht alle Wände unter dem Rand")
pruefe(not hb.ueberdeckt(teil, oberseite), "die Oberseite unter dem Rand")
pruefe(not hb.ueberdeckt(teil, aussen), "die Seite außen unter dem Rand")
alle_unter = hb.ueberdeckte(teil, namen)  # nur die überhängenden und ihre Nachbarn gefragt
pruefe(
    set(waende) <= alle_unter and oberseite not in alle_unter and aussen not in alle_unter,
    f"ueberdeckte: {sorted(alle_unter)}",
)

# --- Die Bahn -----------------------------------------------------------------------------------
bahn = hb.planen(teil, waende, hb.Werte(radius=R, sicher=40.0, grathoehe=0.01, vorschub=1500.0))
print(
    ascii(
        f"Bahn: {bahn.linien} Linien, {len(bahn.punkte)} Punkte, {bahn.neigung:.1f} Grad, "
        f"{bahn.laenge:.0f} mm, {bahn.zeit:.2f} min, {bahn.weggelassen} weggelassen"
    )
)
pruefe(bahn.hinterschnitt and bahn.linien >= 10, f"{bahn.linien} Linien")
# Die Wände hängen 10° über: Die Achse kippt mehr, in den Ecken (zwei Wände) noch mehr.
pruefe(10.0 < bahn.neigung <= 26.0, f"Neigung {bahn.neigung:.1f}°")
pruefe(bahn.anstoesse == 0, f"{bahn.anstoesse} Stellen stoßen an")
pruefe(len(bahn.achsen) == len(bahn.punkte), "nicht je Punkt eine Achse")
# Weg fallen nur Stellen am Boden: Die Kante Wand–Boden ist scharf, die Kugelmitte bleibt R darüber.
am_boden = [m for m in bahn.luecken if m[2] < 10.0 + R + 0.1]
pruefe(
    len(am_boden) == len(bahn.luecken) == bahn.weggelassen,
    f"{bahn.weggelassen} weggelassen, {len(am_boden)} davon am Boden",
)
im_vorschub = [(p, a) for p, a in zip(bahn.punkte, bahn.achsen, strict=True) if not p.eilgang]
schlimmste_kugel = schlimmster_schaft = 99.0
for p, a in im_vorschub[:: max(1, len(im_vorschub) // 150)]:
    mitte = V(p.x, p.y, p.z + R)  # die Punkte: die Spitze der senkrecht gedachten Kugel
    schlimmste_kugel = min(schlimmste_kugel, teil.distToShape(Part.Vertex(mitte))[0] - R)
    # Der Schaft ab 1,5 R über der Spitze (darunter liegt die Kugel selbst an) – als Kapsel um die
    # Achse ab 2,5 R: ihre runde Kappe reicht bis 1,5 R hinab.
    schaft = Part.LineSegment(mitte + V(*a) * (1.5 * R), mitte + V(*a) * 30.0).toShape()
    schlimmster_schaft = min(schlimmster_schaft, teil.distToShape(schaft)[0] - R)
print(ascii(f"Abstand: Kugel {schlimmste_kugel:.4f}, Schaft {schlimmster_schaft:.3f}"))
pruefe(schlimmste_kugel > -0.03, f"Kugel {schlimmste_kugel:.3f} mm im Teil")
pruefe(schlimmste_kugel < 0.05, f"Kugel {schlimmste_kugel:.3f} mm vor der Wand")
pruefe(
    schlimmster_schaft > hb.SPIEL_SCHAFT - hb.NETZ_TOLERANZ - 0.01,
    f"Schaft {schlimmster_schaft:.3f} mm vom Rand",
)
# Eilgänge nur über dem Teil: Ein G0 fährt auf vielen Steuerungen keine Gerade (regelwerk 7a).
tief_im_eilgang = [
    (p, q) for p, q in zip(bahn.punkte, bahn.punkte[1:], strict=False) if q.eilgang and q.z < 30.0
]
pruefe(not tief_im_eilgang, f"{len(tief_im_eilgang)} Eilgänge in die Tasche")
unten_z = min(p.z for p, _a in im_vorschub)
pruefe(unten_z < 10.5, f"tiefste Linie bei z {unten_z:.2f}")

try:
    hb.planen(teil, [], hb.Werte(radius=R, sicher=40.0))
    pruefe(False, "ohne Flächen kein Fehler")
except ValueError as grund:
    pruefe("Keine Fläche" in str(grund), f"ohne Flächen: {grund}")

# --- Der Halter in Stücken: ein langes Schrumpffutter Ø12, das Werkzeug 27 mm heraus -------------
from camaddon import halter as hl

h160 = hl.aus_vorlage(hl.reihe(hl.SCHRUMPF, 12, 160))
masse = rw.Werkzeugmasse(
    durchmesser=12.0, schneide=16.0, hals_d=0.0, hals_laenge=0.0, schaft=12.0, gesamt=73.0
)
koerper = hb.koerper_des_werkzeugs(masse, 160.0 + 27.0, h160)
am_halter = [k for k in koerper if k[0] >= 27.0 - 1e-6]
pruefe(all(b - a <= hb.HALTER_STUECK + 1e-6 for a, b, _r in am_halter), "Stücke länger als 5 mm")
nase = min(am_halter, key=lambda k: k[0])
pruefe(abs(nase[0] - 27.0) < 1e-6 and nase[2] < 12.5, f"die Nase: {nase}")  # Ø 24, nicht 32
pruefe(abs(max(b for _a, b, _r in am_halter) - 187.0) < 1e-6, "bis zur Spindelnase")

# --- Die Operation im Job -----------------------------------------------------------------------
import Path.Main.Job as PathJob

t3 = wz.Werkzeug(
    nummer=3,
    name="Kugel 6",
    art=wz.KUGELFRAESER,
    durchmesser=6.0,
    schneiden=2,
    schneidenlaenge=12.0,
    gesamtlaenge=100.0,
    schneidstoff=wz.VHM,
)
t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([wz.standardwerkzeug(), t3]))
doc = FreeCAD.newDocument("Unterrand")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
tc = js.controller_ohne_transaktion(doc, job, t3, t3.schnittwerte[wz.ALLE][0])
doc.recompute()
op = s3op.lege_an(job, tc, 0.01, flaechen=waende)
s3op.unter_dem_rand(op, True)
doc.recompute()
befehle = list(op.Path.Commands)
achsen = [tuple(a) for a in op.Werkzeugachsen]
gekippt = [a for a in achsen if a[2] < math.cos(math.radians(10))]
print(ascii(f"Operation: {len(befehle)} Saetze, {len(gekippt)} gekippt"))
pruefe(str(op.Richtung) == hb.HINTERSCHNITT, f"Richtung {op.Richtung}")
pruefe(len(achsen) == len(befehle), f"{len(achsen)} Achsen zu {len(befehle)} Sätzen")
pruefe(len(gekippt) > len(befehle) // 2, f"nur {len(gekippt)} Sätze gekippt")
pruefe(so.ist_simultan(op), "nicht simultan")

asm, ma = beispielmaschine.fuenfachs_tisch_tisch()
pruefung = rw.Pruefung(asm, ma)
maschine = sw.Maschine(
    pruefung, pruefung.werkzeugaufnahme(tc.ToolNumber), rw.einspannung(tc, None), rw.nullpunkt(job)
)
saetze = so.befehle(op, maschine)
pruefe(
    any("A" in b.Parameters or "B" in b.Parameters for b in saetze),
    "das Programm schwenkt nicht",
)
print(ascii(f"Maschine: {len(saetze)} Saetze"))

s3op.unter_dem_rand(op, False)
doc.recompute()
pruefe(str(op.Richtung) == "auto", f"aus: Richtung {op.Richtung}")
pruefe(not so.ist_simultan(op), "aus: noch simultan")

FreeCAD.closeDocument(doc.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
