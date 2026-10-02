# Prüft „Restschlichten“ (W-006 4.2 Punkt 8): das 3D-Schlichten mit einem kleineren Fräser nur
# dort, wo der größere davor nicht hinkam. (a) Platte 60 × 60 × 10 mit einer Kuppel (Kugel R 25,
# Mitte (30, 30, −5), Fuß r 20): erst 3D-Schlichten mit der Kugel Ø 6, dann Restschlichten mit
# der Kugel Ø 2. In der Kehle am Fuß (126,9°) lässt eine Kugel mit Radius r senkrecht über der
# Ecke r · (1 − √0,75) = 0,134 r stehen: nach Ø 6 0,40, nach Ø 2 0,13. Die Bahn bleibt am Fuß
# (r 16 … 21,5), im Quader nach beiden Bahnen dort deutlich weniger als nach Ø 6 allein, nirgends
# ins Teil, oben auf der Kuppel nichts gefahren; schneller als die Kuppel ganz mit Ø 2. (b) Eine
# Kuppel ohne Platte (keine Kehle): Ø 6 erreicht alles – ein Satz. (c) Die Operation im Job:
# „Restschlichten T3“ mit Ø und Eckenradius davor, Art „schlichten3d“.
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

from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import job_schnittwerte as js
from camaddon import pruefstand as ps
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
gross_form, klein_form = ff.kugel(3.0), ff.kugel(1.0)


def werte(form, **weiter):
    grund = {"form": form, "oben": 20.0, "sicher": 25.0, "vorschub": 796.0, "eintauchen": 240.0}
    grund.update(weiter)
    return s3.Schlichtwerte(**grund)


def kugelflaechen(teil):
    return [f"Face{i + 1}" for i, f in enumerate(teil.Faces) if isinstance(f.Surface, Part.Sphere)]


# --- (a) Die Kuppel auf der Platte -----------------------------------------------------------------
platte = Part.makeBox(60, 60, 10)
kappe = Part.makeSphere(25, V(30, 30, -5)).common(Part.makeBox(60, 60, 15, V(0, 0, 10)))
teil = platte.fuse(kappe).removeSplitter()
kuppel = kugelflaechen(teil)
gross = s3.planen(teil, kuppel, werte(gross_form))
rest = s3.planen(teil, kuppel, werte(klein_form, davor=gross_form))
ganz = s3.planen(teil, kuppel, werte(klein_form))
pk = np.array([(p.x, p.y, p.z) for p in rest.punkte if not p.eilgang])
r = np.hypot(pk[:, 0] - 30, pk[:, 1] - 30)
print(ascii(f"Rest: {rest.zeit:.2f} min ({rest.hoehenlinien} Höhenlinien, Spirale {rest.spirale}, "
            f"Fläche entlang {rest.flaeche}, {rest.zeilen} Zeilen), r {r.min():.2f} … "
            f"{r.max():.2f}; ganz mit Ø 2 {ganz.zeit:.2f} min, Ø 6 {gross.zeit:.2f} min"))  # fmt: skip
pruefe(r.min() > 16.0 and r.max() < 21.5, f"Rest: r {r.min():.2f} … {r.max():.2f}")
pruefe(rest.zeit < 0.6 * ganz.zeit, f"Rest {rest.zeit:.2f} min, ganz {ganz.zeit:.2f}")

netz = vf.vernetze(teil, 0.005).netz
q = rm.Quader(0, 60, 0, 60, 0, 20.5, schritt=0.1)
soll = hf.hoehen(netz, q.x, q.y)
q.h[:] = np.minimum(soll + 1.0, 20.5)


def fahre(bahn, form):
    for von, nach in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        stuecke = ps._stuecke(von, nach)
        q.fahre_stuecke([s[0] for s in stuecke], [s[1] for s in stuecke], form)


xs, ys = np.meshgrid(q.x, q.y, indexing="ij")
rr = np.hypot(xs - 30, ys - 30)
ecke = (rr > 20.0) & (rr < 20.05)  # über der Kehle, auf der Platte
fahre(gross, gross_form)
nach_gross = q.h.copy()
fahre(rest, klein_form)
vorher = float(np.median((nach_gross - soll)[ecke]))
nachher = float(np.median((q.h - soll)[ecke]))
print(ascii(f"In der Kehle: nach Ø 6 {vorher:.3f}, nach dem Rest mit Ø 2 {nachher:.3f} mm "
            f"(gerechnet 0,40 und 0,13); ins Teil {np.min(q.h - soll):.3f}"))  # fmt: skip
pruefe(vorher > 0.35, f"nach Ø 6 nur {vorher:.3f} in der Kehle")
pruefe(nachher < 0.25, f"nach dem Rest {nachher:.3f} in der Kehle")
pruefe(np.min(q.h - soll) > -0.02, f"ins Teil: {np.min(q.h - soll):.3f}")
oben = rr < 12.0
pruefe(np.all(np.abs(q.h - nach_gross)[oben] < 1e-9), "oben auf der Kuppel gefahren")

# --- (b) Ohne Kehle kein Rest ----------------------------------------------------------------------
allein = Part.makeSphere(25, V(30, 30, -15)).common(Part.makeBox(60, 60, 10, V(0, 0, 0)))
for raster in (s3.RASTER, s3.VORSCHAU_RASTER):
    try:
        s3.planen(allein, kugelflaechen(allein), werte(klein_form, davor=gross_form, oben=10.0,
                                                       sicher=15.0, raster=raster))  # fmt: skip
    except ValueError as grund:
        pruefe("Kein Rest" in str(grund), f"ohne Kehle: {grund}")
    else:
        pruefe(False, f"ohne Kehle (Raster {raster}): eine Bahn")

# --- (c) Die Operation im Job ---------------------------------------------------------------------
pruefe(s3op.eckenradius(ff.kugel(3.0)) == 3.0, "Eckenradius Kugel")
pruefe(abs(s3op.eckenradius(ff.torus(3.0, 1.0)) - 1.0) < 1e-9, "Eckenradius Torus")
pruefe(s3op.eckenradius(ff.scheibe(3.0)) == 0.0, "Eckenradius Schaftfräser")
import Path.Main.Job as PathJob

t3 = wz.Werkzeug(
    nummer=3,
    name="Kugel 2",
    art=wz.KUGELFRAESER,
    durchmesser=2.0,
    schneiden=2,
    schneidenlaenge=6.0,
    schneidstoff=wz.VHM,
)
t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.1, ap=0.1, vc=120.0, fz=0.03)]
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
op = s3op.lege_an(job, tc, s3.GRATHOEHE, flaechen=kuppel, davor=(6.0, 3.0))
doc.recompute()
pruefe(op.Label == "Restschlichten T3", f"Name {op.Label}")
pruefe(s3op.ist_restschlichten(op) and s3op.ist_schlichten3d(op), "ist_restschlichten")
davor = s3op.form_davor(op)
pruefe(davor is not None and davor.nur_kugel and abs(davor.radius - 3.0) < 1e-9, "Form davor")
pruefe(js.operationsart(op) == "schlichten3d", f"Art {js.operationsart(op)}")
befehle = len(op.Path.Commands)
pruefe(
    befehle > 100 and op.Hoehenlinien + op.Zeilen > 0,
    f"Operation: {befehle} Befehle, {op.Hoehenlinien} Höhen, {op.Zeilen} Zeilen",
)
s3op.aendere(op, tc, s3.GRATHOEHE, flaechen=kuppel, davor=(0.0, 0.0))
doc.recompute()
pruefe(op.Label == "3D-Schlichten T3" and not s3op.ist_restschlichten(op), f"ganz: {op.Label}")
print(ascii(f"Operation: {befehle} Befehle als Rest, {len(op.Path.Commands)} ganz"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
