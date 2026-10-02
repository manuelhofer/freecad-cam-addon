# Prüft den Materialstand (W-012 M1, Spezifikation Strategien 12.7) an Manuels Klotz: 100 × 100,
# oben bei z 0 ein Zapfen Ø 30 bei x25 y25, rundum der Boden bei −10, darin eine Nut 20 × 60 längs
# X um x −10 y 0, 15 tief von der Oberkante des Zapfens (Grund −15). Mit dem Standardfräser.
# Zapfen zuerst (Räumen des Bodens, dann die Nut): Über der Nut steht nach dem Räumen das Material
# bei −10; die Nut beginnt dort (ihr erster Vorschub bei −10, nicht bei 0), „noch“ sind 5 mm über
# ihrem Grund, „weg“ hat „Räumen T1“ die 10 mm darüber; sie merkt sich, woraus sie gerechnet hat.
# Nut zuerst (die Folge im Job umgedreht): Ihr Materialstand stimmt nicht mehr – nachrechnen
# rechnet sie neu, jetzt von 0 an, und das Räumen dahinter auch (W-012 M3; Manuel: „wenn ich erst
# die Nut anklicke … und dann den Zapfen will“): Es weiß, dass „Nut T1“ über der Nut schon 10 mm
# weggenommen hat, und ist nicht langsamer als ohne Materialstand; ein zweites Räumen dahinter hat
# nichts mehr zu tun, ein Planfräsen des Bodens danach auch nicht (M4). Ein Körper als Rohteil,
# oben nur am Zapfen bis 0, sonst bis −10 (W-011 S4b): Über der Nut steht es ohne jede Operation
# bei −10, und Räumen und Planfräsen fahren mit 4 mm je Lage nur noch um den Zapfen – ein
# Bruchteil der Zeit. Zweimal 3D-Schruppen an derselben Kuppel: Das zweite nimmt nur noch die
# Treppe, die das erste ließ. Die Kontur am Zapfen nach dem Räumen schlichtet nur noch (ohne
# Schlichten: nichts mehr zu tun); am Guss schruppt sie nur den Rand um den Zapfen.
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

from camaddon import bahn as bn
from camaddon import gui_materialstand as gms
from camaddon import job_schnittwerte as js
from camaddon import kontur as ko
from camaddon import materialstand as mst
from camaddon import nut as nu
from camaddon import planfraesen as pf
from camaddon import raeumen as ra
from camaddon import schruppen3d as r3op
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_schlichten as vs
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
wand = next(f"Face{i + 1}" for i, f in enumerate(teil.Faces)
            if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 15.0) < 1e-6)  # fmt: skip

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
pruefe(neu == [nut_op, raeumen], f"nachgerechnet: {[o.Label for o in neu]}")
pruefe(abs(erster_vorschub(nut_op)) < 0.01, f"Nut zuerst beginnt bei {erster_vorschub(nut_op)}")
pruefe(not gms.nachrechnen(doc), "zweimal nachgerechnet")

# Das Räumen hinter der Nut: Es kennt die Nut – über ihr hat „Nut T1“ die 10 mm bis zum Boden schon
# weggenommen – und ist nicht langsamer als dasselbe Räumen ohne Materialstand.
form = vs.form_des_controllers(tc)


def raeumen_bahn(job, zustellung, stand=None):
    return ra.bahn_fuer(job, job.Model.Group, form, zustellung, einsatz.ae, flaechen=[boden],
                        vorschub=1000.0, stand=stand)  # fmt: skip


uhr = time.time()
mit = raeumen_bahn(job, einsatz.ap, mst.fuer(job, vor=raeumen))
zeit_mit = time.time() - uhr
ohne_r = raeumen_bahn(job, einsatz.ap)
pruefe(mit.davor == ["Nut T1"] and abs(mit.weg / (10.0 * FLAECHE_NUT) - 1.0) < 0.05,
       f"Räumen: {mit.davor}, weg {mit.weg:.0f} mm³ statt {10.0 * FLAECHE_NUT:.0f}")  # fmt: skip
pruefe(mit.zeit <= ohne_r.zeit + 1e-9, f"Räumen {mit.zeit:.2f} min, ohne {ohne_r.zeit:.2f} min")
pruefe(raeumen.Materialstand == mst.kennung_vor(job, raeumen), "Räumen: Kennung nicht gemerkt")

# Zweimal räumen: nichts mehr zu tun.
zweites = ra.lege_an(job, tc, einsatz.ap, einsatz.ae, flaechen=[boden])
doc.recompute()
try:
    ra.rechne(zweites, job, job.Model.Group)
except ValueError as grund_text:
    pruefe("nichts mehr zu tun" in str(grund_text) and "Räumen T1" in str(grund_text),
           f"zweites Räumen: {grund_text}")  # fmt: skip
else:
    pruefe(False, "zweites Räumen: kein Satz")
doc.removeObject(zweites.Name)
doc.recompute()

# Planfräsen danach am selben Boden (M4): Das Räumen hat ihn schon fertig – nichts mehr zu tun.
plan = pf.lege_an(job, tc, einsatz.ap, einsatz.ae, flaechen=[boden])
doc.recompute()
try:
    pf.rechne(plan, job, job.Model.Group)
except ValueError as grund_text:
    pruefe("nichts mehr zu tun" in str(grund_text) and "Räumen T1" in str(grund_text),
           f"Planfräsen danach: {grund_text}")  # fmt: skip
else:
    pruefe(False, "Planfräsen danach: kein Satz")
pruefe(plan.Materialstand == mst.kennung_vor(job, plan), "Planfräsen: Kennung nicht gemerkt")
doc.removeObject(plan.Name)
doc.recompute()


def kontur_zeit(bahn):
    return bn.zeit(bahn.punkte, 1000.0, 300.0)


# Die Kontur am Zapfen danach (M4): Das Räumen hat den Boden bis aufs Aufmaß an der Wand geräumt –
# sie schlichtet nur noch; ohne Materialstand schruppte sie den ganzen Boden noch einmal.
kontur_op = ko.lege_an(job, tc, einsatz.ap, einsatz.ae, flaechen=[wand])
doc.recompute()
kontur_mit = ko.rechne(kontur_op, job, job.Model.Group)
kontur_ohne = ko.bahn_fuer(job, job.Model.Group, form, einsatz.ap, einsatz.ae, flaechen=[wand])
pruefe(kontur_mit.bahnen == 1 and kontur_mit.davor[-1:] == ["Räumen T1"]
       and kontur_zeit(kontur_mit) < 0.1 * kontur_zeit(kontur_ohne),
       f"Kontur nach dem Räumen: {kontur_mit.bahnen} Bahnen, {kontur_zeit(kontur_mit):.2f} min "
       f"statt {kontur_zeit(kontur_ohne):.2f}, davor {kontur_mit.davor}")  # fmt: skip
pruefe(kontur_op.Materialstand == mst.kennung_vor(job, kontur_op), "Kontur: Kennung nicht gemerkt")
try:
    ko.bahn_fuer(job, job.Model.Group, form, einsatz.ap, einsatz.ae, schlichten=False,
                 flaechen=[wand], stand=mst.fuer(job, vor=kontur_op))  # fmt: skip
except ValueError as grund_text:
    pruefe("nichts mehr zu tun" in str(grund_text), f"Kontur ohne Schlichten: {grund_text}")
else:
    pruefe(False, "Kontur ohne Schlichten: kein Satz")
doc.removeObject(kontur_op.Name)
doc.recompute()

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
    # Das Räumen des Bodens mit 4 mm je Lage: über dem Boden steht nur noch der Rand um den
    # Zapfen (Ø 32 statt 30) – je Lage ein, zwei Ringe statt des ganzen Bodens.
    guss_mit = raeumen_bahn(job2, 4.0, stand2)
    guss_ohne = raeumen_bahn(job2, 4.0)
    pruefe(guss_mit.lagen == 3 and guss_mit.ringe <= 6 and guss_mit.zeit < 0.2 * guss_ohne.zeit,
           f"Guss: {guss_mit.lagen} Lagen, {guss_mit.ringe} Ringe, {guss_mit.zeit:.2f} min "
           f"statt {guss_ohne.zeit:.2f} min")  # fmt: skip
    # Ebenso das Planfräsen des Bodens: nur die Zeilen am Rand um den Zapfen.
    plan_mit, plan_ohne = (
        pf.bahn_fuer(job2, job2.Model.Group, form, 4.0, einsatz.ae, flaechen=[boden],
                     vorschub=1000.0, stand=stand)
        for stand in (stand2, None)
    )  # fmt: skip
    pruefe(0 < plan_mit.zeit < 0.12 * plan_ohne.zeit and plan_mit.weg == 0.0,
           f"Guss, Planfräsen: {plan_mit.zeit:.2f} min statt {plan_ohne.zeit:.2f} min, "
           f"weg {plan_mit.weg:.0f}")  # fmt: skip
    # Die Kontur am Zapfen: nur der Rand, je Lage eine Bahn, und das Schlichten.
    kontur_guss, kontur_guss_ohne = (
        ko.bahn_fuer(job2, job2.Model.Group, form, 4.0, einsatz.ae, flaechen=[wand], stand=stand)
        for stand in (stand2, None)
    )
    pruefe(kontur_guss.lagen == 4 and kontur_guss.bahnen == 4
           and kontur_zeit(kontur_guss) < 0.1 * kontur_zeit(kontur_guss_ohne),
           f"Guss, Kontur: {kontur_guss.lagen} Lagen, {kontur_guss.bahnen} Bahnen, "
           f"{kontur_zeit(kontur_guss):.2f} min statt {kontur_zeit(kontur_guss_ohne):.2f}")  # fmt: skip
    print(ascii(f"Guss: Räumen {guss_mit.zeit:.2f} statt {guss_ohne.zeit:.2f} min, Planfräsen "
                f"{plan_mit.zeit:.2f} statt {plan_ohne.zeit:.2f} min, Kontur "
                f"{kontur_zeit(kontur_guss):.2f} statt {kontur_zeit(kontur_guss_ohne):.2f} "
                f"min"))  # fmt: skip

# --- 3D-Schruppen (M4): zweimal dieselbe Kuppel ------------------------------------------------
platte3d = Part.makeBox(60, 60, 10)
kappe = Part.makeSphere(25, V(30, 30, -5)).common(Part.makeBox(60, 60, 15, V(0, 0, 10)))
kuppel_teil = platte3d.fuse(kappe).removeSplitter()
kugel = [f"Face{i + 1}" for i, f in enumerate(kuppel_teil.Faces)
         if isinstance(f.Surface, Part.Sphere)]  # fmt: skip
kuppel = doc.addObject("Part::Feature", "Kuppel")
kuppel.Shape = kuppel_teil
doc.recompute()
job3 = PathJob.Create("Job", [kuppel])
job3.Stock.ExtZpos = 0.0
doc.recompute()
tc3 = js.controller_ohne_transaktion(doc, job3, fraeser, einsatz)
doc.recompute()
erstes = r3op.lege_an(job3, tc3, 25.0, 1.5, 0.3, flaechen=kugel)
zweites = r3op.lege_an(job3, tc3, 25.0, 1.5, 0.3, flaechen=kugel)
doc.recompute()
bahn_3d = r3op.rechne(erstes, job3, job3.Model.Group, 1000.0)
try:
    rest_3d = r3op.rechne(zweites, job3, job3.Model.Group, 1000.0)
    zeit_rest = rest_3d.zeit
    pruefe(rest_3d.zeit < 0.3 * bahn_3d.zeit and rest_3d.davor == [erstes.Label],
           f"zweites 3D-Schruppen: {rest_3d.zeit:.2f} min nach {bahn_3d.zeit:.2f}, "
           f"davor {rest_3d.davor}")  # fmt: skip
except ValueError as grund_text:
    zeit_rest = 0.0
    pruefe("nichts mehr zu tun" in str(grund_text), f"zweites 3D-Schruppen: {grund_text}")
pruefe(zweites.Materialstand == mst.kennung_vor(job3, zweites), "3D: Kennung nicht gemerkt")
print(ascii(f"3D-Schruppen: {bahn_3d.zeit:.2f} min, das zweite danach {zeit_rest:.2f} min"))

print(ascii(f"Kontur nach dem Räumen: {kontur_zeit(kontur_mit):.2f} statt "
            f"{kontur_zeit(kontur_ohne):.2f} min"))  # fmt: skip
print(ascii(f"Räumen {zeit_raeumen:.1f} s, Materialstand {zeit_stand:.2f} s, "
            f"Nut {bahn.zeit:.2f} min statt {ohne.zeit:.2f} min, Räumen nach der Nut "
            f"{zeit_mit:.1f} s, {mit.zeit:.2f} min statt {ohne_r.zeit:.2f} min"))  # fmt: skip
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
