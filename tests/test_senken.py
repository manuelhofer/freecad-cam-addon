# Prüft „Zentrieren“ und „Senken“ aus dem Assistenten (W-006 S3g): FreeCADs Bohr-Operation mit
# einem NC-Anbohrer und einem Kegelsenker. Platte 100 × 60 × 10 mit einer Durchgangsbohrung
# Ø 6,6 bei (25, 30) und einer 90°-Senkung Ø 12,4 darüber, einer Bohrung Ø 8,5 bei (60, 30) und
# einer Sackbohrung Ø 10 × 5 bei (85, 30). Die Senkung wird erkannt (Ø, Winkel, Bohrung darunter),
# die Tiefen ((D − d) / 2 / tan(α/2)), beim Zentrieren zählt die Oberkante der Senkung; ein
# Senker mit anderem Winkel oder zu klein mit einem Satz; dann FreeCADs Operationen im Job: je
# Tiefe eine, G81 an den richtigen Stellen und Tiefen, „Zentrieren T5“, „Senken T6“.
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import bohren as bh
from camaddon import bohrung_bahn as bb
from camaddon import job_schnittwerte as js
from camaddon import senken as sk
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
anbohrer = wz.Werkzeug(
    nummer=5,
    name="NC 10",
    art=wz.NC_ANBOHRER,
    durchmesser=10.0,
    schneiden=2,
    schneidenlaenge=20.0,
    spitzenwinkel=90.0,
    schneidstoff=wz.VHM,
)
anbohrer.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.ZENTRIEREN, vc=60.0, fz=0.05)]
senker = wz.Werkzeug(
    nummer=6,
    name="KS 20",
    art=wz.KEGELSENKER,
    durchmesser=20.0,
    schneiden=3,
    spitzenwinkel=90.0,
    spitzen_d=4.0,
    schneidstoff=wz.HSS,
)
senker.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SENKEN, vc=20.0, fz=0.08)]

teil = Part.makeBox(100, 60, 10)
teil = teil.cut(Part.makeCylinder(3.3, 10, V(25, 30, 0)))
teil = teil.cut(Part.makeCone(3.3, 6.2, 2.9, V(25, 30, 7.1)))
teil = teil.cut(Part.makeCylinder(4.25, 10, V(60, 30, 0)))
teil = teil.cut(Part.makeCylinder(5, 5, V(85, 30, 5))).removeSplitter()

# --- Senkungen ------------------------------------------------------------------------------
liste = sk.senkungen(teil)
pruefe(len(liste) == 1, f"Senkungen: {liste}")
senkung = liste[0] if liste else None
bohrungen = {round(2 * b.radius, 2): b for b in bb.bohrungen(teil)}
pruefe(sorted(bohrungen) == [6.6, 8.5, 10.0], f"Bohrungen: {sorted(bohrungen)}")
if senkung is not None:
    pruefe(
        abs(senkung.durchmesser - 12.4) < 1e-6
        and abs(senkung.winkel - 90.0) < 1e-6
        and abs(senkung.z_oben - 10.0) < 1e-6
        and senkung.bohrung == bohrungen[6.6].name,
        f"Senkung: {senkung}",
    )
    pruefe(sk.ist_senkung(teil, senkung.name), "ist_senkung")
pruefe(not sk.ist_senkung(teil, bohrungen[8.5].name), "eine Bohrung ist keine Senkung")

# --- Tiefen -------------------------------------------------------------------------------------
pruefe(abs(sk.tiefe_fuer(12.4, 90.0) - 6.2) < 1e-9, "Tiefe spitz")
pruefe(abs(sk.tiefe_fuer(12.4, 90.0, 4.0) - 4.2) < 1e-9, "Tiefe mit Spitze Ø 4")
namen = [bohrungen[d].name for d in (6.6, 8.5)]
stellen = {round(2 * b.radius, 2): (k, z) for b, k, z in sk.zentrierstellen(teil, namen, 10.0, 90)}
# Unter der Senkung zählt ihre Oberkante (10), nicht die der Bohrung (7,1): oben Ø 7,0 → 3,5 tief.
pruefe(stellen.get(6.6) == (10.0, 6.5), f"Zentrieren Ø 6,6: {stellen.get(6.6)}")
k, z = stellen.get(8.5, (0, 0))
pruefe(abs(k - 10.0) < 1e-9 and abs(z - 5.55) < 1e-9, f"Zentrieren Ø 8,5: {(k, z)}")
# Größer als 0,9 × Ø des Anbohrers schneidet er oben nicht: Ø 10 mit einem Ø 6 – oben Ø 5,4.
k, z = sk.zentrierstellen(teil, [bohrungen[10.0].name], 6.0, 90)[0][1:]
pruefe(abs(k - 10.0) < 1e-9 and abs(z - (10.0 - 2.7)) < 1e-9, f"Anbohrer Ø 6: {(k, z)}")

# --- Welche Senkungen ein Senker kann -----------------------------------------------------------
if senkung is not None:
    pruefe(len(sk.passende_senkungen(teil, [senkung.name], 20.0, 90.0)) == 1, "passt")
    for d, winkel, satzteil in ((20.0, 60.0, "60°"), (10.0, 90.0, "Ø 10 ist kleiner")):
        try:
            sk.passende_senkungen(teil, [senkung.name], d, winkel)
        except ValueError as grund:
            pruefe(satzteil in str(grund), f"{d}/{winkel}: {grund}")
        else:
            pruefe(False, f"{d}/{winkel}: keine Fehlermeldung")

# --- Bewegungen und Zeit --------------------------------------------------------------------
bahn = sk.planen([(25.0, 30.0, 10.0, 6.5), (60.0, 30.0, 10.0, 5.55)], 11.0, 16.0, 300.0)
pruefe(bahn.stellen == 2 and abs(bahn.tiefe - 4.45) < 1e-9 and bahn.zeit > 0, f"{bahn}")
weg = sum(
    abs(b.z - a.z) for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False) if not b.eilgang
)
pruefe(abs(weg - ((14.0 - 6.5) + (14.0 - 5.55))) < 1e-9, f"Weg im Vorschub {weg}")

# --- FreeCADs Operationen im Job ----------------------------------------------------------------
import Path.Main.Job as PathJob

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([fraeser, anbohrer, senker]))
doc = FreeCAD.newDocument("Senken")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 1.0
doc.recompute()
klon = job.Model.Group[0]
im_job = {round(2 * b.radius, 2): b.name for b in bb.bohrungen(klon.Shape)}
tc5 = js.controller_ohne_transaktion(doc, job, anbohrer, anbohrer.schnittwerte[wz.ALLE][0])
op = sk.zentrieren_anlegen(job, tc5, [im_job[6.6], im_job[8.5]])
doc.recompute()
# Je Tiefe eine Operation; die zweite heißt „… (2)“ – nicht „Zentrieren T001“, wie FreeCAD einen
# doppelten Namen sonst eindeutig macht.
zentrieren = [o for o in job.Operations.Group if o.Label.startswith("Zentrieren T5")]
namen_z = [o.Label for o in zentrieren]
pruefe(namen_z == ["Zentrieren T5", "Zentrieren T5 (2)"], f"Namen: {namen_z}")
pruefe(all(bh.ist_bohren(o) for o in zentrieren), "Zentrieren: nicht FreeCADs Bohren")
zyklen = sorted(
    (round(c.Parameters["X"], 3), round(c.Parameters["Z"], 3), c.Name)
    for o in zentrieren
    for c in o.Path.Commands
    if c.Name in ("G81", "G82", "G83")
)
pruefe(zyklen == [(25.0, 6.5, "G81"), (60.0, 5.55, "G81")], f"Zentrieren: {zyklen}")
senkung_im_job = sk.senkungen(klon.Shape)
tc6 = js.controller_ohne_transaktion(doc, job, senker, senker.schnittwerte[wz.ALLE][0])
op = sk.senken_anlegen(job, tc6, [s.name for s in senkung_im_job])
doc.recompute()
zyklen = [
    (round(c.Parameters["X"], 3), round(c.Parameters["Y"], 3), round(c.Parameters["Z"], 3))
    for c in op.Path.Commands
    if c.Name == "G81"
]
pruefe(op.Label == "Senken T6" and zyklen == [(25.0, 30.0, 5.8)], f"Senken: {op.Label} {zyklen}")
pruefe(js.operationsart(op) == "Drilling", f"Art: {js.operationsart(op)}")
print(ascii(f"Senken: {zyklen}"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
