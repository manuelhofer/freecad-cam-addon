# Prüft „Restschruppen“ (W-006 4.2 Punkt 2): das 3D-Schruppen mit einem kleineren Fräser nur
# dort, wo der größere davor Material stehen ließ. Platte 66 × 40 × 10 mit zwei Kuppeln (Kugel
# R 12, Mitte z 4, Fuß Ø 20,8, oben z 16) bei x 20 und x 46 – zwischen den Füßen 5,2 mm: Der
# Standardfräser Ø 12 kommt dort nicht hinunter, ein Schaftfräser Ø 6 schon. Erst 3D-Schruppen
# mit Ø 12, dann Restschruppen mit Ø 6 (davor Ø 12, Eckenradius 0). Die Restbahn bleibt im Tal
# zwischen den Kuppeln; im Quader steht dort danach deutlich weniger, nirgends ins Teil, im
# Eilgang nichts. Ohne Lücke (eine Kuppel allein): „Kein Rest“. Die Operation im Job:
# „Restschruppen T5“, Art „schruppen3d“.
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
from camaddon import raeumen_bahn as rb
from camaddon import restmaterial as rm
from camaddon import schruppen3d as r3op
from camaddon import schruppen3d_bahn as r3
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
OBEN = 17.0
gross_form, klein_form = ff.scheibe(6.0), ff.scheibe(3.0)


def teil_mit(mitten):
    teil = Part.makeBox(66, 40, 10)
    for x in mitten:
        kappe = Part.makeSphere(12, V(x, 20, 4)).common(Part.makeBox(66, 40, 10, V(0, 0, 10)))
        teil = teil.fuse(kappe)
    return teil.removeSplitter()


def kugelflaechen(teil):
    return [f"Face{i + 1}" for i, f in enumerate(teil.Faces) if isinstance(f.Surface, Part.Sphere)]


def werte(form, ae, ap):
    return rb.Raeumwerte(form=form, zustellung=ap, zeilenabstand=ae, aufmass=0.3, oben=OBEN,
                         sicher=OBEN + 5.0, rohteil=(0.0, 66.0, 0.0, 40.0), schneidenlaenge=30.0,
                         eintauchwinkel=3.0, vorschub=902.0, eintauchen=270.0)  # fmt: skip


# --- Zwei Kuppeln mit einer Lücke --------------------------------------------------------------
teil = teil_mit((20.0, 46.0))
kuppeln = kugelflaechen(teil)
gross = r3.planen(teil, kuppeln, werte(gross_form, 1.5, 25.0))
rest = r3.planen(teil, kuppeln, werte(klein_form, 0.75, 12.0), davor=gross_form)
pk = np.array([(p.x, p.y, p.z) for p in rest.punkte if not p.eilgang])
print(ascii(f"Ø 12: {gross.zeit:.2f} min, Rest mit Ø 6: {rest.zeit:.2f} min, {rest.lagen} + "
            f"{rest.zwischenlagen} Lagen, {rest.ringe} Ringe; x {pk[:, 0].min():.1f} … "
            f"{pk[:, 0].max():.1f}, y {pk[:, 1].min():.1f} … {pk[:, 1].max():.1f}"))  # fmt: skip
pruefe(rest.ringe > 0 and rest.zeit < gross.zeit, f"Rest: {rest.ringe} Ringe, {rest.zeit:.2f} min")
pruefe(pk[:, 0].min() > 22.0 and pk[:, 0].max() < 44.0, "Rest außerhalb des Tals")

netz = vf.vernetze(teil, 0.005).netz
q = rm.Quader(0, 66, 0, 40, 0, OBEN, schritt=0.25)
soll = hf.hoehen(netz, q.x, q.y)


def fahre(bahn, form):
    for von, nach in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        stuecke = ps._stuecke(von, nach)
        q.fahre_stuecke([s[0] for s in stuecke], [s[1] for s in stuecke], form)


xs, ys = np.meshgrid(q.x, q.y, indexing="ij")
tal = (np.abs(xs - 33.0) < 3.0) & (np.abs(ys - 20.0) < 4.0)
zelle = 0.25 * 0.25  # das Raster des Quaders


def volumen():
    """mm³ im Tal über dem Teil mit Aufmaß."""
    return float(np.clip(q.h - soll - 0.35, 0.0, None)[tal].sum()) * zelle


fahre(gross, gross_form)
vorher, v_vorher = float(np.max((q.h - soll)[tal])), volumen()
fahre(rest, klein_form)
nachher, v_nachher = float(np.max((q.h - soll)[tal])), volumen()
print(ascii(f"Im Tal über dem Teil: nach Ø 12 {vorher:.2f} mm ({v_vorher:.0f} mm³), nach dem Rest "
            f"{nachher:.2f} mm ({v_nachher:.0f} mm³)"))  # fmt: skip
pruefe(vorher > 3.0 and nachher < vorher - 1.5, f"im Tal: {vorher:.2f} → {nachher:.2f}")
pruefe(v_nachher < 0.5 * v_vorher, f"im Tal: {v_vorher:.0f} → {v_nachher:.0f} mm³")
k = ps.messen(
    [ps.Bahnlauf(gross.punkte, 902.0, 270.0), ps.Bahnlauf(rest.punkte, 902.0, 270.0)],
    teil, (0, 66, 0, 40), OBEN, klein_form, 0.75, 12.0,
)  # fmt: skip
print(ascii(ps.zeile(k)))
pruefe(k.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"ins Teil: {k.einschnitt:.3f}")
pruefe(k.eilgang_abtrag <= 1e-9, f"im Eilgang {k.eilgang_abtrag:.1f} mm³")

# --- Ohne Lücke kein Rest ----------------------------------------------------------------------
allein = teil_mit((33.0,))
try:
    r3.planen(allein, kugelflaechen(allein), werte(klein_form, 0.75, 12.0), davor=gross_form)
except ValueError as grund:
    pruefe("Kein Rest" in str(grund), f"ohne Lücke: {grund}")
else:
    pruefe(False, "ohne Lücke: eine Bahn")

# --- Die Operation im Job ---------------------------------------------------------------------
import Path.Main.Job as PathJob

t5 = wz.Werkzeug(
    nummer=5,
    name="Schaft 6",
    art=wz.SCHAFTFRAESER,
    durchmesser=6.0,
    schneiden=3,
    schneidenlaenge=18.0,
    schneidstoff=wz.VHM,
)
t5.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=0.75, ap=12.0, vc=85.0, fz=0.05)]
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([wz.standardwerkzeug(), t5]))
doc = FreeCAD.newDocument("Kuppeln")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
tc = js.controller_ohne_transaktion(doc, job, t5, t5.schnittwerte[wz.ALLE][0])
doc.recompute()
op = r3op.lege_an(job, tc, 12.0, 0.75, 0.3, flaechen=kuppeln, davor=(12.0, 0.0))
doc.recompute()
pruefe(op.Label == "Restschruppen T5", f"Name {op.Label}")
pruefe(r3op.ist_restschruppen(op) and r3op.ist_schruppen3d(op), "ist_restschruppen")
davor = r3op.form_davor(op)
pruefe(davor is not None and davor.eben and abs(davor.radius - 6.0) < 1e-9, "Form davor")
pruefe(js.operationsart(op) == "schruppen3d", f"Art {js.operationsart(op)}")
pruefe(op.Ringe > 0 and len(op.Path.Commands) > 20, f"Operation: {op.Ringe} Ringe")
print(ascii(f"Operation: {len(op.Path.Commands)} Befehle, {op.Lagen} + {op.Zwischen} Lagen"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
