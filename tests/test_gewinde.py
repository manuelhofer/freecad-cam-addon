# Prüft „Gewinde bohren“ aus dem Assistenten (W-006 S3g): FreeCADs Gewinde-Operation (Tapping) mit
# einem Gewindebohrer M10 × 1,5 aus der Werkzeugverwaltung. Block 100 × 60 × 20 mit einem
# durchgehenden Kernloch Ø 8,5 bei (25, 30), einem Kernloch Ø 8,5 15 tief bei (60, 30) und einer
# Bohrung Ø 6 bei (85, 30). Das Kernloch (Gewinde-Ø − Steigung), welche Bohrungen passen (Ø 6
# nicht, mit einem Satz), die Tiefe (durchgehend 2 Steigungen hinaus, die Sackbohrung eine
# Steigung über dem Grund), die Bewegungen und ihre Zeit (hinein und heraus mit Steigung ·
# Drehzahl); dann FreeCADs Operation im Job: je Tiefe eine (FreeCAD fährt alle Löcher einer
# Operation bis zu ihrer einen Endtiefe), G84 an den Kernlöchern, R über dem Rohteil,
# „Gewinde M10x1.5 T4“ (nur ASCII: der Name steht als Kommentar im Programm), Art „Tapping“.
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import bohrung_bahn as bb
from camaddon import gewinde as gw
from camaddon import job_schnittwerte as js
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
fraeser = wz.standardwerkzeug()
m10 = wz.Werkzeug(
    nummer=4,
    name="M10",
    art=wz.GEWINDEBOHRER_RECHTS,
    durchmesser=10.0,
    steigung=1.5,
    schneiden=3,
    schneidenlaenge=20.0,
    schneidstoff=wz.HSS,
)
m10.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.GEWINDEBOHREN, vc=8.0)]

teil = Part.makeBox(100, 60, 20)
teil = teil.cut(Part.makeCylinder(4.25, 20, V(25, 30, 0)))  # durchgehend Ø 8,5
teil = teil.cut(Part.makeCylinder(4.25, 15, V(60, 30, 5)))  # Ø 8,5, Grund 5
teil = teil.cut(Part.makeCylinder(3, 20, V(85, 30, 0))).removeSplitter()  # Ø 6
alle = bb.bohrungen(teil)
kern = [b.name for b in alle if abs(b.radius - 4.25) < 1e-6]
klein = [b.name for b in alle if abs(b.radius - 3.0) < 1e-6]
pruefe((len(kern), len(klein)) == (2, 1), f"Bohrungen: {kern}, {klein}")

# --- Kernloch, passende Bohrungen, Tiefe --------------------------------------------------------
pruefe(abs(gw.kernloch(10.0, 1.5) - 8.5) < 1e-9, "Kernloch M10")
pruefe(gw.gewinde_name(10.0, 1.5) == "M10x1.5", f"Name: {gw.gewinde_name(10.0, 1.5)}")
liste = gw.passende(teil, kern, 10.0, 1.5)
pruefe(len(liste) == 2, f"passend: {len(liste)}")
try:
    gw.passende(teil, klein, 10.0, 1.5)
except ValueError as grund:
    satz = str(grund).replace(",", ".")  # „Ø 8,5“ mit dem gewählten Dezimalzeichen
    pruefe("Kernloch Ø 8.5 " in satz and "hat Ø 6." in satz, f"Ø 6: {grund}")
else:
    pruefe(False, "Ø 6: keine Fehlermeldung")
tiefen = sorted(round(gw.tiefe_fuer(b, 1.5), 6) for b in liste)
pruefe(tiefen == [-3.0, 6.5], f"Tiefen: {tiefen}")

# --- Bewegungen und Zeit --------------------------------------------------------------------
n, vf, _s = js.werte(m10, m10.schnittwerte[wz.ALLE][0])
pruefe(abs(vf - n * 1.5) < 1e-6, f"Vorschub {vf} statt {n * 1.5}")
bahn = gw.planen(liste, 1.5, n, 21.0, 26.0)
pruefe(
    bahn.gewinde == 2 and abs(bahn.z_min + 3.0) < 1e-9 and bahn.zeit > 0,
    f"{bahn.gewinde} Gewinde, z_min {bahn.z_min}, {bahn.zeit} min",
)
weg = sum(
    abs(b.z - a.z) for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False) if not b.eilgang
)
pruefe(abs(weg - 2 * ((24.0 + 3.0) + (24.0 - 6.5))) < 1e-6, f"Weg im Vorschub {weg}")
pruefe(bahn.zeit > weg / vf, f"Zeit {bahn.zeit} unter {weg / vf}")
print(f"Gewinde M10: {bahn.zeit:.2f} min, n {n:.0f}, vf {vf:.0f}")

# --- FreeCADs Operation im Job ------------------------------------------------------------------
import Path.Main.Job as PathJob

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([fraeser, m10]))
doc = FreeCAD.newDocument("Gewinde")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 1.0
doc.recompute()
klon = job.Model.Group[0]
namen = [b.name for b in bb.bohrungen(klon.Shape) if abs(b.radius - 4.25) < 1e-6]
tc = js.controller_ohne_transaktion(doc, job, m10, m10.schnittwerte[wz.ALLE][0])
doc.recompute()
pruefe(abs(float(tc.Tool.Pitch) - 1.5) < 1e-9, f"Pitch {getattr(tc.Tool, 'Pitch', None)}")
op = gw.lege_an(job, tc, namen)
doc.recompute()
pruefe(op.Label == "Gewinde M10x1.5 T4" and op in job.Operations.Group, f"{op.Label}")
pruefe(gw.ist_gewinde(op) and js.operationsart(op) == "Tapping", f"Art {js.operationsart(op)}")
# FreeCAD fährt alle Löcher einer Operation bis zu ihrer einen Endtiefe – darum je Tiefe eine
# Operation: die Sackbohrung bis 6,5 (eine Steigung über dem Grund), die durchgehende bis −3.
gewinde_ops = [o for o in job.Operations.Group if gw.ist_gewinde(o)]
zyklen = [c for o in gewinde_ops for c in o.Path.Commands if c.Name in ("G84", "G74")]
pruefe(
    [o.Label for o in gewinde_ops] == ["Gewinde M10x1.5 T4", "Gewinde M10x1.5 T4 (2)"],
    f"Operationen: {[o.Label for o in gewinde_ops]}",
)
tiefe_je_ort = sorted((round(c.Parameters["X"], 3), round(c.Parameters["Z"], 6)) for c in zyklen)
pruefe(tiefe_je_ort == [(25.0, -3.0), (60.0, 6.5)], f"Tiefen je Ort {tiefe_je_ort}")
pruefe(
    len(zyklen) == 2 and all(c.Name == "G84" for c in zyklen),
    f"Zyklen: {[c.Name for c in zyklen]}",
)
pruefe(all(abs(c.Parameters["R"] - 24.0) < 1e-6 for c in zyklen), "R über dem Rohteil")
orte = sorted((round(c.Parameters["X"], 3), round(c.Parameters["Y"], 3)) for c in zyklen)
pruefe(orte == [(25.0, 30.0), (60.0, 30.0)], f"Orte {orte}")
print(ascii(f"Operation: {[c.Name for c in op.Path.Commands]}"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
