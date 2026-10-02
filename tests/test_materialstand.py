# Prüft den Materialstand (W-012 M1, Spezifikation Strategien 12.7) an Manuels Klotz: 100 × 100,
# oben bei z 0 ein Zapfen Ø 30 bei x25 y25, rundum der Boden bei −10, darin eine Nut 20 × 60 längs
# X um x −10 y 0, 15 tief von der Oberkante des Zapfens (Grund −15). Mit dem Standardfräser.
# Zapfen zuerst (Räumen des Bodens, dann die Nut): Über der Nut steht nach dem Räumen das Material
# bei −10; die Nut beginnt dort (ihr erster Vorschub bei −10, nicht bei 0), „noch“ sind 5 mm über
# ihrem Grund, „weg“ hat „Räumen T1“ die 10 mm darüber; sie merkt sich, woraus sie gerechnet hat.
# Nut zuerst (die Folge im Job umgedreht): Ihr Materialstand stimmt nicht mehr – nachrechnen
# rechnet sie neu, jetzt von 0 an. Ein Körper als Rohteil, oben nur am Zapfen bis 0, sonst bis −10
# (W-011 S4b): Über der Nut steht es ohne jede Operation bei −10.
import math
import os
import pathlib
import sys
import tempfile
import time

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part
import Path.Main.Job as PathJob
import Path.Main.Stock as PathStock
from Path.Tool.camassets import user_asset_store

from camaddon import gui_materialstand as gms
from camaddon import job_schnittwerte as js
from camaddon import materialstand as mst
from camaddon import nut as nu
from camaddon import raeumen as ra
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
A, B, R_NUT = (-30.0, 0.0), (10.0, 0.0), 10.0
FLAECHE_NUT = 2 * R_NUT * (B[0] - A[0]) + math.pi * R_NUT * R_NUT

# --- Manuels Klotz ------------------------------------------------------------------------------
klotz = Part.makeBox(100, 100, 20, V(-50, -50, -30))
klotz = klotz.fuse(Part.makeCylinder(15, 10, V(25, 25, -10)))
nut = Part.makeBox(B[0] - A[0], 2 * R_NUT, 6, V(A[0], A[1] - R_NUT, -15))
nut = nut.fuse(Part.makeCylinder(R_NUT, 6, V(A[0], A[1], -15)))
nut = nut.fuse(Part.makeCylinder(R_NUT, 6, V(B[0], B[1], -15)))
teil = klotz.cut(nut).removeSplitter()


def flaeche(z):
    """Die ebene Fläche nach oben auf der Höhe z."""
    for i, f in enumerate(teil.Faces):
        bb = f.BoundBox
        if abs(bb.ZMin - z) < 1e-6 and abs(bb.ZMax - z) < 1e-6:
            return f"Face{i + 1}"
    raise AssertionError(f"keine Fläche bei z {z}")


boden = flaeche(-10.0)
grund = flaeche(-15.0)

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
fraeser = wz.standardwerkzeug()
ue.uebergeben(wz.Bibliothek([fraeser]))
einsatz = next(e for e in fraeser.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
doc = FreeCAD.newDocument("Klotz")
objekt = doc.addObject("Part::Feature", "Klotz")
objekt.Shape = teil
doc.recompute()


def neuer_job():
    job = PathJob.Create("Job", [objekt])
    job.Stock.ExtZpos = 0.0
    doc.recompute()
    tc = js.controller_ohne_transaktion(doc, job, fraeser, einsatz)
    doc.recompute()
    return job, tc


def erster_vorschub(op):
    """z des ersten Vorschubs (G1) der Bahn."""
    return next(float(c.Parameters["Z"]) for c in op.Path.Commands
                if c.Name in ("G1", "G01") and "Z" in c.Parameters)  # fmt: skip


# --- Zapfen zuerst: das Räumen um den Zapfen, dann die Nut --------------------------------------
job, tc = neuer_job()
uhr = time.time()
raeumen = ra.lege_an(job, tc, einsatz.ap, einsatz.ae, flaechen=[boden])
doc.recompute()
zeit_raeumen = time.time() - uhr
uhr = time.time()
stand = mst.fuer(job)
zeit_stand = time.time() - uhr
maske = stand.maske_um(A, B, R_NUT)
pruefe(abs(stand.hoechste(maske) + 10.0) < 0.01, f"über der Nut: {stand.hoechste(maske)}")
zapfen = stand.maske_um((25, 25), (25, 25), 14.0)
pruefe(abs(stand.hoechste(zapfen)) < 0.01, f"Zapfen: {stand.hoechste(zapfen)}")
pruefe(stand.wer(maske) == ["Räumen T1"], f"weggenommen von {stand.wer(maske)}")

nut_op = nu.lege_an(job, tc, einsatz.ap, einsatz.ae, flaechen=[grund])
doc.recompute()
pruefe(nut_op.Nuten == 1 and nut_op.Lagen == 1, f"Nut: {nut_op.Nuten} Nuten, {nut_op.Lagen} Lagen")
pruefe(abs(erster_vorschub(nut_op) + 10.0) < 0.01, f"Nut beginnt bei {erster_vorschub(nut_op)}")
pruefe(nut_op.Materialstand == mst.kennung_vor(job, nut_op), "Kennung nicht gemerkt")
bahn = nu.rechne(nut_op, job, job.Model.Group)
noch, weg = bahn.noch / FLAECHE_NUT, bahn.weg / FLAECHE_NUT  # mm über dem Grund
pruefe(abs(noch - 5.0) < 0.15 and abs(weg - 10.0) < 0.3, f"noch {noch:.2f}, weg {weg:.2f} mm")
pruefe(bahn.davor == ["Räumen T1"], f"davor: {bahn.davor}")
# Ohne Materialstand begänne sie bei 0 – mit ihm fällt die Helix durch 10 mm Luft weg: so viele
# Umläufe, wie die Steigung (Eintauchwinkel der Operation) auf 15 statt 5 mm braucht.
ohne = nu.bahn_fuer(
    job,
    job.Model.Group,
    6.0,
    einsatz.ap,
    einsatz.ae,
    flaechen=[grund],
    eintauchwinkel=float(nut_op.Eintauchwinkel),
)
r_helix = R_NUT - 6.0 - float(nut_op.Aufmass)
steigung = 2 * math.pi * r_helix * math.tan(math.radians(float(nut_op.Eintauchwinkel)))
umlaeufe = math.ceil(15.0 / steigung - 1e-9) - math.ceil(5.0 / steigung - 1e-9)
luft = umlaeufe * 2 * math.pi * r_helix
pruefe(
    ohne.punkte[2].z > -1e-6 and abs(ohne.laenge - bahn.laenge - luft) < 1.0,
    f"ohne: ab {ohne.punkte[2].z}, {ohne.laenge:.0f} mm; mit {bahn.laenge:.0f} mm, Luft {luft:.0f}",
)

# Nichts mehr zu tun: eine zweite Nut dahinter – die erste hat alles genommen.
zweite = nu.lege_an(job, tc, einsatz.ap, einsatz.ae, flaechen=[grund])
doc.recompute()
try:
    nu.rechne(zweite, job, job.Model.Group)
except ValueError as grund_text:
    pruefe("nichts mehr zu tun" in str(grund_text) and "Nut T1" in str(grund_text),
           f"zweite Nut: {grund_text}")  # fmt: skip
else:
    pruefe(False, "zweite Nut: kein Satz")
doc.removeObject(zweite.Name)
doc.recompute()

# --- Nut zuerst: die Folge umgedreht – nachrechnen rechnet die Nut neu, von 0 an ------------------
job.Operations.Group = [nut_op, raeumen]
doc.recompute()
pruefe(nut_op.Materialstand != mst.kennung_vor(job, nut_op), "Kennung stimmt nach dem Umdrehen?")
neu = gms.nachrechnen(doc)
pruefe(neu == [nut_op], f"nachgerechnet: {[o.Label for o in neu]}")
pruefe(abs(erster_vorschub(nut_op)) < 0.01, f"Nut zuerst beginnt bei {erster_vorschub(nut_op)}")
pruefe(not gms.nachrechnen(doc), "zweimal nachgerechnet")

# --- Ein Körper als Rohteil: oben nur am Zapfen bis 0 (W-011 S4b) --------------------------------
guss = Part.makeBox(102, 102, 21, V(-51, -51, -31)).fuse(Part.makeCylinder(16, 10, V(25, 25, -10)))
koerper = doc.addObject("Part::Feature", "Guss")
koerper.Shape = guss
doc.recompute()
job2, _tc2 = neuer_job()
klon = PathJob.createResourceClone(job2, koerper, "Stock", "Stock")
PathStock.SetupStockObject(klon, PathStock.StockType.Unknown)
klon.Proxy.execute(klon)
alt = job2.Stock
job2.Stock = klon
doc.removeObject(alt.Name)
doc.recompute()
stand2 = mst.fuer(job2)
pruefe(stand2 is not None, "kein Materialstand mit dem Körper")
if stand2 is not None:
    oben_nut = stand2.hoechste(stand2.maske_um(A, B, R_NUT))
    oben_zapfen = stand2.hoechste(stand2.maske_um((25, 25), (25, 25), 14.0))
    pruefe(abs(oben_nut + 10.0) < 0.01 and abs(oben_zapfen) < 0.01,
           f"Körper: über der Nut {oben_nut}, am Zapfen {oben_zapfen}")  # fmt: skip
    pruefe(not math.isfinite(stand2.quader.h[0, 0]) or stand2.quader.h[0, 0] <= -10.0 + 1e-6,
           f"Ecke {stand2.quader.h[0, 0]}")  # fmt: skip

print(ascii(f"Räumen {zeit_raeumen:.1f} s, Materialstand {zeit_stand:.2f} s, "
            f"Nut {bahn.zeit:.2f} min statt {ohne.zeit:.2f} min"))  # fmt: skip
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
