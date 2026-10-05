# Prüft „Bleistift“ (W-006 4.2 Punkt 6) mit einem Kugelfräser Ø 6: (a) Platte 60 × 60 × 10 mit
# einer Kuppel (Kugel R 25, Mitte (30, 30, −5)): Die Kugel berührt Platte und Kuppel zugleich,
# wenn ihre Mitte 3 über der Platte und 28 von der Kugelmitte liegt – die Spitze auf dem Kreis
# r = √(28² − 18²) = 21,45 um (30, 30) bei z 10. Genau eine Kehle, ein Ring. Im Quader (vorher
# Platte und Kuppel mit 0,3 Aufmaß) nirgends ins Teil; am Ring ist die Platte fertig, an der
# Kuppel dort, wo die Kugel sie berührt (r 19,15), auch. (b) Eine Halbkugel R 15 auf der Platte
# (am Fuß senkrecht): der Ring bei r = √(18² − 3²) = 17,75. (c) Eine Kuppel ohne Platte: keine
# Kehle – ein Satz. (d) Die Operation im Job: „Bleistift T3“, Art „bleistift“. (a2) Drei Bahnen je
# Seite: Ringe auf der Platte im Zeilenabstand, an der Kuppel im Raum gleich weit, die Kehle
# zuletzt.
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

from camaddon import bleistift as bsop
from camaddon import bleistift_bahn as bs
from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import job_schnittwerte as js
from camaddon import pruefstand as ps
from camaddon import restmaterial as rm
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
form = ff.kugel(3.0)


def werte(**weiter):
    grund = {"form": form, "oben": 20.0, "sicher": 25.0, "vorschub": 796.0, "eintauchen": 240.0}
    grund.update(weiter)
    return bs.Bleistiftwerte(**grund)


def kugelflaechen(teil):
    return [f"Face{i + 1}" for i, f in enumerate(teil.Faces) if isinstance(f.Surface, Part.Sphere)]


def auf_der_kehle(bahn):
    return np.array([(p.x, p.y, p.z) for p in bahn.punkte if not p.eilgang])


# --- (a) Die Kuppel auf der Platte -----------------------------------------------------------------
platte = Part.makeBox(60, 60, 10)
kappe = Part.makeSphere(25, V(30, 30, -5)).common(Part.makeBox(60, 60, 15, V(0, 0, 10)))
teil = platte.fuse(kappe).removeSplitter()
kuppel = kugelflaechen(teil)
bahn = bs.planen(teil, kuppel, werte())
pk = auf_der_kehle(bahn)
r = np.hypot(pk[:, 0] - 30, pk[:, 1] - 30)
soll_r = math.sqrt(28**2 - 18**2)
print(ascii(f"Kuppel: {bahn.linien} Kehlen ({bahn.ringe} Ringe), {bahn.laenge:.1f} mm, "
            f"{bahn.zeit:.2f} min, r {r.min():.3f} … {r.max():.3f}, z {pk[:, 2].min():.3f} … "
            f"{pk[:, 2].max():.3f}"))  # fmt: skip
pruefe(bahn.linien == 1 and bahn.ringe == 1, f"Kehlen {bahn.linien}, Ringe {bahn.ringe}")
pruefe(np.all(np.abs(r - soll_r) < 0.05), f"r {r.min():.3f} … {r.max():.3f} statt {soll_r:.3f}")
pruefe(np.all(np.abs(pk[:, 2] - 10.0) < 0.02), f"z {pk[:, 2].min():.3f} … {pk[:, 2].max():.3f}")
pruefe(abs(bahn.laenge - 2 * math.pi * soll_r) < 2.0, f"Länge {bahn.laenge:.1f}")

netz = vf.vernetze(teil, 0.005).netz
q = rm.Quader(0, 60, 0, 60, 0, 20.5, schritt=0.25)
soll = hf.hoehen(netz, q.x, q.y)
q.h[:] = np.minimum(soll + 0.3, 20.5)
for von, nach in zip(bahn.punkte, bahn.punkte[1:], strict=False):
    stuecke = ps._stuecke(von, nach)
    q.fahre_stuecke([s[0] for s in stuecke], [s[1] for s in stuecke], form)
xs, ys = np.meshgrid(q.x, q.y, indexing="ij")
rr = np.hypot(xs - 30, ys - 30)
rest = q.h - soll
pruefe(np.min(rest) > -0.02, f"ins Teil: {np.min(rest):.3f}")
am_ring = (rr > soll_r - 0.15) & (rr < soll_r + 0.15)
pruefe(np.max(rest[am_ring]) < 0.05, f"am Ring: {np.max(rest[am_ring]):.3f}")
beruehrt = (rr > 19.05) & (rr < 19.25)  # dort berührt die Kugel die Kuppel
pruefe(np.max(rest[beruehrt]) < 0.1, f"an der Kuppel: {np.max(rest[beruehrt]):.3f}")
fern = rr > soll_r + 3.5
pruefe(np.all(np.abs(rest[fern] - 0.3) < 1e-9), "fern der Kehle angeschnitten")

# --- (a2) Drei Bahnen je Seite: auf der Platte Ringe im Abstand nach außen, an der Kuppel im Raum
# gleich weit hinauf; von außen zur Kehle, die Kehle zuletzt; nirgends ins Teil.
abstand3 = bs.sb.zeilenabstand(form, bs.GRATHOEHE)
bahn3 = bs.planen(teil, kuppel, werte(bahnen=3))
pruefe(
    bahn3.linien == 1 and bahn3.bahnen == 7 and bahn3.ringe == 7,
    f"drei je Seite: {bahn3.linien} Kehlen, {bahn3.bahnen} Bahnen, {bahn3.ringe} Ringe",
)
laeufe, lauf = [], []
for p in bahn3.punkte:
    if p.eilgang:
        if lauf:
            laeufe.append(np.array(lauf))
        lauf = []
    else:
        lauf.append((p.x, p.y, p.z))
radien = [float(np.median(np.hypot(lf[:, 0] - 30, lf[:, 1] - 30))) for lf in laeufe]
hoehen = [float(np.median(lf[:, 2])) for lf in laeufe]
pruefe(len(laeufe) == 7 and abs(radien[-1] - soll_r) < 0.05, f"Kehle zuletzt: r {radien}")
auf_platte = sorted(r_ for r_, z_ in zip(radien, hoehen, strict=True) if r_ > soll_r + 0.1)
pruefe(
    len(auf_platte) == 3
    and all(abs(r_ - (soll_r + k * abstand3)) < 0.05 for k, r_ in enumerate(auf_platte, 1)),
    f"auf der Platte r {auf_platte} statt Schritten von {abstand3:.3f}",
)
an_kuppel = sorted(
    ((r_, z_) for r_, z_ in zip(radien, hoehen, strict=True) if r_ < soll_r - 0.1), reverse=True
)
schritte = [
    math.dist(a_, b_) for a_, b_ in zip([(soll_r, 10.0)] + an_kuppel, an_kuppel, strict=False)
]
pruefe(
    len(an_kuppel) == 3 and all(abs(s_ - abstand3) < 0.2 * abstand3 for s_ in schritte),
    f"an der Kuppel im Raum {[round(s_, 3) for s_ in schritte]} statt {abstand3:.3f}",
)
pruefe(max(radien[0], radien[1]) > soll_r + 2.5 * abstand3 or min(radien[0], radien[1]) < r.min() - 1.0,
       f"nicht von außen begonnen: {radien[:2]}")  # fmt: skip
q3 = rm.Quader(0, 60, 0, 60, 0, 20.5, schritt=0.25)
q3.h[:] = np.minimum(soll + 0.3, 20.5)
for von, nach in zip(bahn3.punkte, bahn3.punkte[1:], strict=False):
    stuecke = ps._stuecke(von, nach)
    q3.fahre_stuecke([s_[0] for s_ in stuecke], [s_[1] for s_ in stuecke], form)
rest3 = q3.h - soll
pruefe(np.min(rest3) > -0.02, f"drei je Seite ins Teil: {np.min(rest3):.3f}")
breiter = (rr > soll_r + 0.2) & (rr < soll_r + 2.5 * abstand3)  # neben der Kehle auf der Platte
pruefe(np.max(rest3[breiter]) < 0.05, f"neben der Kehle: {np.max(rest3[breiter]):.3f}")
print(
    ascii(
        f"drei je Seite: {bahn3.zeit:.2f} min (eine: {bahn.zeit:.2f}), r {[round(x, 2) for x in radien]}"
    )
)

# --- (b) Die Halbkugel: am Fuß senkrecht ----------------------------------------------------------
halb = Part.makeSphere(15, V(30, 30, 10)).common(Part.makeBox(60, 60, 20, V(0, 0, 10)))
teil_h = Part.makeBox(60, 60, 10).fuse(halb).removeSplitter()
bahn_h = bs.planen(teil_h, kugelflaechen(teil_h), werte(oben=25.0, sicher=30.0))
pk = auf_der_kehle(bahn_h)
r = np.hypot(pk[:, 0] - 30, pk[:, 1] - 30)
soll_h = math.sqrt(18**2 - 3**2)
print(ascii(f"Halbkugel: {bahn_h.linien} Kehlen, r {r.min():.3f} … {r.max():.3f}"))
pruefe(bahn_h.linien == 1 and bahn_h.ringe == 1, f"Halbkugel: {bahn_h.linien} Kehlen")
pruefe(np.all(np.abs(r - soll_h) < 0.05), f"Halbkugel: r {r.min():.3f} … {r.max():.3f}")

# --- (c) Ohne Nachbarin keine Kehle ---------------------------------------------------------------
allein = Part.makeSphere(25, V(30, 30, -15)).common(Part.makeBox(60, 60, 10, V(0, 0, 0)))
try:
    bs.planen(allein, kugelflaechen(allein), werte())
except ValueError as grund:
    pruefe("keine Kehle" in str(grund), f"ohne Kehle: {grund}")
else:
    pruefe(False, "ohne Kehle: kein Satz")

# --- (d) Die Operation im Job ---------------------------------------------------------------------
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
op = bsop.lege_an(job, tc, flaechen=kuppel)
doc.recompute()
pruefe(op.Label == "Bleistift T3", f"Name {op.Label}")
pruefe(op.Linien == 1, f"Linien {op.Linien}")
pruefe(js.operationsart(op) == "bleistift", f"Art {js.operationsart(op)}")
print(ascii(f"Operation: {len(op.Path.Commands)} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
