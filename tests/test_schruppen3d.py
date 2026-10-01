# Prüft „3D-Schruppen“ (W-006 4.2 Punkt 1) mit dem Standardfräser (Ø 12, ae 1,5, ap 25, vf 902)
# und Aufmaß 0,3. (a) Platte 60 × 60 × 10 mit einer Kuppel (Kugel R 25, Mitte (30, 30, −5): Fuß
# Ø 40 auf z 10, oben z 20), das Rohteil bis z 20: eine Lage mit vollem ap auf 10,3 und
# Zwischenlagen darüber. Im Quader nirgends ins Teil, im Eilgang nichts abgetragen; auf der Platte
# genau das Aufmaß, auf der Kuppel – senkrecht zur Kugel gemessen – mindestens das Aufmaß (bis
# auf die Spitze, wo das Rohteil endet) und höchstens Treppe plus Aufmaß (1,7). Ohne
# Zwischenlagen stünde dort viel mehr. (b) Eine Schale (Kugel R 25 in einen Block 60 × 60 × 20
# gesenkt, Grund z 10): nur Zwischenlagen, je über die Rampe, nirgends ins Teil; in der Höhlung
# bleibt unter der ebenen Stirn mehr stehen (der Bogen unter dem Fräser, 0,7 mm) – bis 2,5.
# (c) Ohne Freiformfläche ein Satz. (d) Die Operation im Job: „3D-Schruppen T1“, Art
# „schruppen3d“ mit dem Einsatz „Schruppen“.
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
werkzeug = wz.standardwerkzeug()
form = ff.scheibe(werkzeug.durchmesser / 2)
VF, EINTAUCHEN = 902.0, 270.0


def werte(oben, **weiter):
    grund = {
        "form": form,
        "zustellung": 25.0,
        "zeilenabstand": 1.5,
        "aufmass": 0.3,
        "oben": oben,
        "sicher": oben + 5.0,
        "rohteil": (0.0, 60.0, 0.0, 60.0),
        "schneidenlaenge": werkzeug.schneidenlaenge,
        "eintauchwinkel": werkzeug.eintauchwinkel,
        "vorschub": VF,
        "eintauchen": EINTAUCHEN,
    }
    grund.update(weiter)
    return rb.Raeumwerte(**grund)


def im_quader(teil, bahn, oben):
    """(Quader nach der Bahn, Sollhöhe je Zelle, x, y) – das Rohteil bis `oben`."""
    q = rm.Quader(0, 60, 0, 60, teil.BoundBox.ZMin - 1.0, oben, 0.25)
    for von, nach in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        stuecke = ps._stuecke(von, nach)
        q.fahre_stuecke([s[0] for s in stuecke], [s[1] for s in stuecke], form)
    soll = hf.hoehen(vf.vernetze(teil, 0.005).netz, q.x, q.y)
    xs, ys = np.meshgrid(q.x, q.y, indexing="ij")
    return q, soll, xs, ys


def gemessen(teil, bahn, oben):
    k = ps.messen([ps.Bahnlauf(bahn.punkte, VF, EINTAUCHEN)], teil, (0, 60, 0, 60), oben, form,
                  1.5, 25.0)  # fmt: skip
    return k


# --- (a) Die Kuppel ---------------------------------------------------------------------------------
platte = Part.makeBox(60, 60, 10)
kappe = Part.makeSphere(25, V(30, 30, -5)).common(Part.makeBox(60, 60, 15, V(0, 0, 10)))
teil = platte.fuse(kappe).removeSplitter()
kugel = [f"Face{i + 1}" for i, f in enumerate(teil.Faces) if isinstance(f.Surface, Part.Sphere)]
t0 = time.time()
bahn = r3.planen(teil, kugel, werte(20.0))
print(ascii(f"Kuppel: {bahn.variante} {bahn.zeit:.2f} min, {bahn.lagen} + {bahn.zwischenlagen} "
            f"Lagen, {bahn.ringe} Ringe, Rechenzeit {time.time() - t0:.1f} s, {bahn.zeiten}"))  # fmt: skip
pruefe(bahn.lagen == 1 and bahn.zwischenlagen >= 7, f"Lagen {bahn.lagen} + {bahn.zwischenlagen}")
pruefe(abs(bahn.z_min - 10.3) < 1e-6, f"tiefste Lage {bahn.z_min}")
# 6,1 min: bis P-2026-10-01-48 5,4 – die Ringe der Hauptlage bissen in die Kuppel (Eingriff bis
# 4,8 ae, siebenmal senkrecht ins Material); die Ringe um sie herum (P-2026-10-01-49) nehmen
# höchstens 1,6 ae.
pruefe(bahn.zeit < 6.5, f"Zeit {bahn.zeit:.2f} min")
k = gemessen(teil, bahn, 20.0)
print(ascii(ps.zeile(k)))
pruefe(k.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"Kuppel: ins Teil {k.einschnitt:.3f}")
pruefe(k.eingriff_max < 2.0 and k.voll <= ps.BREIT_WEG, f"Kuppel: Eingriff {ps.zeile(k)}")
pruefe(k.eilgang_abtrag <= 1e-9, f"Kuppel: im Eilgang {k.eilgang_abtrag:.1f} mm³")
q, soll, xs, ys = im_quader(teil, bahn, 20.0)
r = np.hypot(xs - 30, ys - 30)
rest = q.h - soll
platte_frei = r > 21.0
pruefe(
    np.all(np.abs(rest[platte_frei] - 0.3) < 0.02),
    f"Platte: {rest[platte_frei].min():.3f} … {rest[platte_frei].max():.3f} statt 0,3",
)
senkrecht = np.sqrt((xs - 30) ** 2 + (ys - 30) ** 2 + (q.h + 5) ** 2) - 25.0
kuppel = r < 19.5
flanke = kuppel & (r > 4.5)  # die Spitze bis r 3,9 liegt keine 0,3 unter dem Rohteil
print(ascii(f"Kuppel senkrecht: {senkrecht[flanke].min():.3f} … {senkrecht[kuppel].max():.3f}"))
pruefe(senkrecht[flanke].min() > 0.25, f"Kuppel: nur {senkrecht[flanke].min():.3f} stehen")
pruefe(senkrecht[kuppel].max() < 1.7, f"Kuppel: Treppe {senkrecht[kuppel].max():.3f}")
ohne = r3.planen(teil, kugel, werte(20.0), zwischen=0.0)
pruefe(ohne.zwischenlagen == 0, f"ohne Zwischenlagen: {ohne.zwischenlagen}")
q0, _soll, _xs, _ys = im_quader(teil, ohne, 20.0)
senkrecht0 = np.sqrt((xs - 30) ** 2 + (ys - 30) ** 2 + (q0.h + 5) ** 2) - 25.0
pruefe(senkrecht0[kuppel].max() > 5.0, f"ohne Zwischenlagen nur {senkrecht0[kuppel].max():.2f}")
gegen = r3.planen(teil, kugel, werte(20.0, gleichlauf=False))
pruefe(abs(gegen.zeit - bahn.zeit) < 0.5, f"Gegenlauf {gegen.zeit:.2f}, Gleichlauf {bahn.zeit:.2f}")

# --- (b) Die Schale ---------------------------------------------------------------------------------
block = Part.makeBox(60, 60, 20)
schale = block.cut(Part.makeSphere(25, V(30, 30, 35))).removeSplitter()
innen = [f"Face{i + 1}" for i, f in enumerate(schale.Faces) if isinstance(f.Surface, Part.Sphere)]
bahn_s = r3.planen(schale, innen, werte(20.0))
print(ascii(f"Schale: {bahn_s.zeit:.2f} min, {bahn_s.lagen} + {bahn_s.zwischenlagen} Lagen, "
            f"{bahn_s.ringe} Ringe, {bahn_s.rampen} Rampen"))  # fmt: skip
pruefe(
    bahn_s.zwischenlagen >= 5 and bahn_s.rampen == bahn_s.zwischenlagen,
    f"Schale: {bahn_s.zwischenlagen} Zwischenlagen, {bahn_s.rampen} Rampen",
)
k = gemessen(schale, bahn_s, 20.0)
print(ascii(ps.zeile(k)))
pruefe(k.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"Schale: ins Teil {k.einschnitt:.3f}")
pruefe(k.eilgang_abtrag <= 1e-9, f"Schale: im Eilgang {k.eilgang_abtrag:.1f} mm³")
q, soll, xs, ys = im_quader(schale, bahn_s, 20.0)
r = np.hypot(xs - 30, ys - 30)
abstand = 25.0 - np.sqrt((xs - 30) ** 2 + (ys - 30) ** 2 + (q.h - 35) ** 2)  # über der Schale
mitte = r < 16.0
print(ascii(f"Schale senkrecht: {abstand[mitte].min():.3f} … {abstand[mitte].max():.3f}"))
pruefe(abstand[mitte].min() > 0.25, f"Schale: nur {abstand[mitte].min():.3f} stehen")
pruefe(abstand[mitte].max() < 2.5, f"Schale: Treppe {abstand[mitte].max():.3f}")

# --- (c) Ohne Freiformfläche ----------------------------------------------------------------------
andere = [f"Face{i + 1}" for i in range(len(teil.Faces)) if f"Face{i + 1}" not in kugel]
try:
    r3.planen(teil, andere, werte(20.0))
except ValueError as grund:
    pruefe("Keine Freiformfläche" in str(grund), f"ohne Freiform: {grund}")
else:
    pruefe(False, "ohne Freiform: kein Satz")

# --- (d) Die Operation im Job ---------------------------------------------------------------------
import Path.Main.Job as PathJob

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([werkzeug]))
doc = FreeCAD.newDocument("Kuppel")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
einsatz = next(e for e in werkzeug.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
tc = js.controller_ohne_transaktion(doc, job, werkzeug, einsatz)
doc.recompute()
op = r3op.lege_an(job, tc, 25.0, 1.5, 0.3, flaechen=kugel)
doc.recompute()
pruefe(op.Label == "3D-Schruppen T1", f"Name {op.Label}")
pruefe(op.Lagen == 1 and op.Zwischen >= 7, f"Operation: {op.Lagen} + {op.Zwischen} Lagen")
pruefe(abs(float(op.FinalDepth) - 10.3) < 1e-6, f"Endtiefe {float(op.FinalDepth)}")
pruefe(js.operationsart(op) == "schruppen3d", f"Art {js.operationsart(op)}")
print(ascii(f"Operation: {len(op.Path.Commands)} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
