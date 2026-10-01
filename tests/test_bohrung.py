# Prüft „Bohrung fräsen“ (W-006 S3g) mit Manuels Standardfräser Ø 12 (ae 1,5, ap 25, Rampe 3°,
# Schneidenlänge 26): Block 100 × 60 × 20 mit einer durchgehenden Bohrung Ø 20 bei (25, 30), einer
# Sackbohrung Ø 34, 10 tief, bei (70, 30) und einer kleinen Bohrung Ø 8 bei (50, 52); dazu ein
# Zapfen, der keine Bohrung ist. Die Bohrungen erkannt (Radius, Grund, durchgehend), die Bahn:
# Helix hinab mit G2/G3 und Z, in der großen Bohrung Ringe nach außen, Schlichten bei Radius;
# Gleichlauf gegen den Uhrzeigersinn (Spindel M3: das Material rechts), Gegenlauf mit ihm; die
# durchgehende 0,5 mm tiefer. Die Simulation im Quader: in den Bohrungen nichts stehen
# geblieben, daneben nichts angeschnitten. Schneller als die Kontur in denselben Bohrungen.
# Fehler mit einem Satz; dann die CAM-Operation im Job: angelegt, gerechnet, geändert,
# gespeichert und geladen.
import math
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import bahn as bn
from camaddon import bohrung as bo
from camaddon import bohrung_bahn as bb
from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import job_schnittwerte as js
from camaddon import kontur_bahn as kb
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
werkzeug = wz.standardwerkzeug()
R = werkzeug.durchmesser / 2
form = ff.scheibe(R)
schruppen = next(e for e in werkzeug.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
VF = 902.0  # mm/min bei vc 85, fz 0,1, 4 Schneiden

teil = Part.makeBox(100, 60, 20)
teil = teil.cut(Part.makeCylinder(10, 20, V(25, 30, 0)))  # durchgehend Ø 20
teil = teil.cut(Part.makeCylinder(17, 10, V(70, 30, 10)))  # Sackbohrung Ø 34, Grund 10
teil = teil.cut(Part.makeCylinder(4, 20, V(50, 52, 0)))  # Ø 8 – kleiner als der Fräser
teil = teil.fuse(Part.makeCylinder(5, 5, V(50, 10, 20))).removeSplitter()  # Zapfen: keine Bohrung

# --- Die Bohrungen ------------------------------------------------------------------------------
alle = bb.bohrungen(teil)
nach_radius = {round(b.radius, 6): b for b in alle}
pruefe(sorted(nach_radius) == [4.0, 10.0, 17.0], f"Bohrungen: {sorted(nach_radius)}")
durch, sack, klein = nach_radius.get(10.0), nach_radius.get(17.0), nach_radius.get(4.0)
if durch is None or sack is None or klein is None:
    raise AssertionError("\n".join(fehler))
pruefe(
    durch.durch and abs(durch.z_unten) < 1e-6 and abs(durch.z_oben - 20.0) < 1e-6,
    f"durchgehend: {durch}",
)
pruefe(
    not sack.durch and abs(sack.z_unten - 10.0) < 1e-6 and abs(sack.z_oben - 20.0) < 1e-6,
    f"Sackbohrung: {sack}",
)
pruefe(
    abs(durch.mitte[0] - 25.0) < 1e-6 and abs(durch.mitte[1] - 30.0) < 1e-6,
    f"Mitte: {durch.mitte}",
)
zapfen = [
    f"Face{i + 1}"
    for i, f in enumerate(teil.Faces)
    if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 5.0) < 1e-6
]
pruefe(len(zapfen) == 1 and not bb.ist_bohrung(teil, zapfen[0]), f"Zapfen als Bohrung: {zapfen}")
pruefe(bb.ist_bohrung(teil, durch.name), "ist_bohrung")
print("Bohrungen ok")


def werte_fuer(gleichlauf=True, schlichten=True, aufmass=0.3):
    return bb.Bohrwerte(
        fraeser_radius=R,
        zustellung=schruppen.ap,
        zeilenabstand=schruppen.ae,
        aufmass=aufmass,
        oben=21.0,
        sicher=26.0,
        schlichten=schlichten,
        gleichlauf=gleichlauf,
        schneidenlaenge=werkzeug.schneidenlaenge,
        eintauchwinkel=werkzeug.eintauchwinkel,
        vorschub=VF,
        eintauchen=VF * 0.3,
    )


def boegen(bahn):
    return [p for p in bahn.punkte if not p.eilgang and p.bogen is not None]


# --- Die Bahn ---------------------------------------------------------------------------------
bahn = bb.planen(werte_fuer(), [durch, sack])
pruefe(bahn.bohrungen == 2 and bahn.lagen == 2, f"{bahn.bohrungen} Bohrungen, {bahn.lagen} Lagen")
pruefe(abs(bahn.z_min - (0.0 - bb.TIEFER)) < 1e-9, f"z_min {bahn.z_min}")
pruefe(bahn.umlaeufe > 5, f"Umläufe {bahn.umlaeufe}")
pruefe(bahn.punkte[0].eilgang and bahn.punkte[-1].eilgang, "Anfang und Ende im Eilgang")
pruefe(
    abs(bahn.punkte[0].z - 26.0) < 1e-9 and abs(bahn.punkte[-1].z - 26.0) < 1e-9,
    "Anfang und Ende oben",
)
# Gleichlauf: alle Bögen gegen den Uhrzeigersinn (G3) – das Material rechts der Fahrtrichtung.
alle_boegen = boegen(bahn)
pruefe(
    len(alle_boegen) > 40 and not any(p.bogen[2] for p in alle_boegen),
    f"Gleichlauf: {sum(1 for p in alle_boegen if p.bogen[2])} von {len(alle_boegen)} im Uhrzeigersinn",
)
# Die Helix: Bögen mit Z – in der durchgehenden Bohrung um die Mitte mit Radius 10 − 6 − 0,3.
helix = [
    (a, b)
    for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False)
    if b.bogen is not None and not b.eilgang and b.z < a.z - 1e-9
]
pruefe(len(helix) > 20, f"Helix: {len(helix)} Bögen mit Z")
r_helix = {
    round(math.hypot(b.x - b.bogen[0], b.y - b.bogen[1]), 6)
    for a, b in helix
    if abs(b.bogen[0] - 25.0) < 1e-6 and abs(b.bogen[1] - 30.0) < 1e-6
}
pruefe(r_helix == {3.7}, f"Helix in der durchgehenden: Radius {r_helix}")
# Steigung je Umlauf: 2π · 3,7 · tan 3°.
schraeg = [
    (a, b)
    for a, b in helix
    if abs(b.bogen[0] - 25.0) < 1e-6 and abs(math.hypot(b.x - 25.0, b.y - 30.0) - 3.7) < 1e-6
]
steigung = sum(a.z - b.z for a, b in schraeg) / max(
    sum(bn.winkel(a, b) for a, b in schraeg) / (2 * math.pi), 1e-9
)
soll = 2 * math.pi * 3.7 * math.tan(math.radians(werkzeug.eintauchwinkel))
pruefe(abs(steigung - soll) < 0.01, f"Steigung {steigung:.3f} statt {soll:.3f}")
# In der großen Bohrung Ringe nach außen bis Radius 17 − 6 − 0,3 = 10,7, Schlichten bei 11.
radien_sack = {
    round(math.hypot(p.x - 70.0, p.y - 30.0), 3)
    for p in alle_boegen
    if abs(p.bogen[0] - 70.0) < 1e-6 and abs(p.bogen[1] - 30.0) < 1e-6
}
pruefe(
    5.4 in radien_sack and 10.7 in radien_sack and 11.0 in radien_sack and max(radien_sack) <= 11.0,
    f"Sackbohrung: Radien {sorted(radien_sack)}",
)
radien_durch = {
    round(math.hypot(p.x - 25.0, p.y - 30.0), 3)
    for p in alle_boegen
    if abs(p.bogen[0] - 25.0) < 1e-6 and abs(p.bogen[1] - 30.0) < 1e-6
}
pruefe(
    max(radien_durch) <= 4.0 + 1e-9 and 4.0 in radien_durch,
    f"durchgehend: Radien {sorted(radien_durch)}",
)
# Gegenlauf: alle Bögen im Uhrzeigersinn.
gegen = bb.planen(werte_fuer(gleichlauf=False), [durch, sack])
pruefe(all(p.bogen[2] for p in boegen(gegen)), "Gegenlauf: nicht alle Bögen im Uhrzeigersinn")
pruefe(abs(gegen.zeit - bahn.zeit) < 1e-6, f"Gegenlauf: {gegen.zeit} statt {bahn.zeit}")


# --- Simulation im Quader --------------------------------------------------------------------
def simuliert(bahn_):
    q = rm.Quader(-1.0, 101.0, -1.0, 61.0, -5.0, 21.0, 0.5)
    von, nach = [], []
    for a, b in zip(bahn_.punkte, bahn_.punkte[1:], strict=False):
        if b.bogen is None:
            von.append((a.x, a.y, a.z))
            nach.append((b.x, b.y, b.z))
            continue
        n = max(2, int(math.ceil(bn.weg(a, b) / 0.25)))
        mx, my, uhr = b.bogen
        a0 = math.atan2(a.y - my, a.x - mx)
        winkel = bn.winkel(a, b)
        rad = math.hypot(a.x - mx, a.y - my)
        vorher = (a.x, a.y, a.z)
        for i in range(1, n + 1):
            t = i / n
            w = a0 - t * winkel if uhr else a0 + t * winkel
            jetzt = (mx + rad * math.cos(w), my + rad * math.sin(w), a.z + (b.z - a.z) * t)
            von.append(vorher)
            nach.append(jetzt)
            vorher = jetzt
    q.fahre_stuecke(von, nach, R)
    return q


q = simuliert(bahn)
gx, gy = np.meshgrid(q.x, q.y, indexing="ij")
d_durch = np.hypot(gx - 25.0, gy - 30.0)
d_sack = np.hypot(gx - 70.0, gy - 30.0)
d_klein = np.hypot(gx - 50.0, gy - 52.0)
innen_durch = d_durch < 10.0 - 0.1
innen_sack = d_sack < 17.0 - 0.1
pruefe(
    float(q.h[innen_durch].max()) <= -bb.TIEFER + 1e-6,
    f"durchgehend: bis {float(q.h[innen_durch].max()):.3f} stehen geblieben",
)
pruefe(
    float(np.abs(q.h[innen_sack] - 10.0).max()) <= 0.01,
    f"Sackbohrung: Grund {float(q.h[innen_sack].min()):.3f} … {float(q.h[innen_sack].max()):.3f}",
)
draussen = (d_durch > 10.0 + 0.1) & (d_sack > 17.0 + 0.1) & (d_klein > 4.5)
pruefe(
    float(q.h[draussen].min()) >= 21.0 - 1e-9,
    f"daneben angeschnitten: bis {float(q.h[draussen].min()):.3f}",
)
print("Simulation ok")

# --- Gegen die Kontur in denselben Bohrungen ---------------------------------------------------
waende = [durch.name, sack.name]
netz, netz_fern = hf.netze_ohne(
    teil, [kb.ohne_flaechen(teil, kb.waende(teil, waende)), list(waende)]
)
kontur = kb.planen(
    netz,
    kb.Konturwerte(
        form=form,
        zustellung=schruppen.ap,
        zeilenabstand=schruppen.ae,
        aufmass=0.3,
        schlichten=True,
        oben=21.0,
        sicher=26.0,
        rohteil=(-1.0, 101.0, -1.0, 61.0),
        schneidenlaenge=werkzeug.schneidenlaenge,
        eintauchwinkel=werkzeug.eintauchwinkel,
    ),
    kb.konturen(teil, waende),
    netz_fern=netz_fern,
)
zeit_kontur = bn.zeit(kontur.punkte, VF, VF * 0.3)
pruefe(bahn.zeit < zeit_kontur, f"Bohrung {bahn.zeit:.2f} min, Kontur {zeit_kontur:.2f} min")
print(f"Bohrung fraesen {bahn.zeit:.2f} min, Kontur {zeit_kontur:.2f} min")

# --- Fehler mit einem Satz --------------------------------------------------------------------
for werte_falsch, liste, text in (
    (werte_fuer(), [klein], "zu klein"),
    (werte_fuer(), [], "keine"),
    (bb.Bohrwerte(0.0, 25.0, 1.5, 0.3, 21.0, 26.0), [durch], "Fräser"),
    (bb.Bohrwerte(R, 0.0, 1.5, 0.3, 21.0, 26.0), [durch], "Werte"),
    (bb.Bohrwerte(R, 25.0, 1.5, 0.3, 0.0, 26.0), [sack], "nichts darüber"),
):
    try:
        bb.planen(werte_falsch, liste)
    except ValueError as grund:
        pruefe(len(str(grund)) > 10, f"{text}: kein Satz")
        if text == "zu klein":
            pruefe("Ø 8 " in str(grund), f"zu klein: {grund}")
    else:
        pruefe(False, f"{text}: keine Fehlermeldung")
print("Fehler ok")

# --- Die CAM-Operation im Job ---------------------------------------------------------------
import Path.Main.Job as PathJob

ue.uebergeben(wz.Bibliothek([werkzeug]))
doc = FreeCAD.newDocument("Bohrung")
doc.UndoMode = 1
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 1.0
doc.recompute()
tc1 = js.controller_ohne_transaktion(doc, job, werkzeug, schruppen)
doc.recompute()
klon = job.Model.Group[0]
im_job = {round(b.radius, 6): b.name for b in bb.bohrungen(klon.Shape)}
op = bo.lege_an(
    job,
    tc1,
    zustellung=schruppen.ap,
    zeilenabstand=schruppen.ae,
    flaechen=[im_job[10.0], im_job[17.0]],
)
doc.recompute()
pruefe(op.Label == "Bohrung fräsen T1" and op in job.Operations.Group, f"{op.Label}")
pruefe(bo.ist_bohrungsfraesen(op), "Art")
pruefe(js.operationsart(op) == "bohrung", f"Art: {js.operationsart(op)}")
pruefe(js.EINSATZ_NACH_OPERATION["bohrung"][0] == wz.SCHRUPPEN, "Einsatz Schruppen")
pruefe(
    abs(float(op.FinalDepth) + bb.TIEFER) < 1e-6,
    f"Endtiefe {float(op.FinalDepth)}",
)
pruefe(
    (op.Bohrungen, op.Lagen) == (2, 2) and op.Umlaeufe > 5,
    f"Operation: {op.Bohrungen} Bohrungen, {op.Lagen} Lagen, {op.Umlaeufe} Umläufe",
)
befehle = op.Path.Commands
namen = [b.Name for b in befehle]
pruefe(
    "G3" in namen and "G2" not in namen,
    f"Gleichlauf: G3 {namen.count('G3')}, G2 {namen.count('G2')}",
)
helix_befehle = [b for b in befehle if b.Name == "G3" and "Z" in b.Parameters]
pruefe(len(helix_befehle) > 20, f"Helix: {len(helix_befehle)} G3 mit Z")
z_werte = sorted({round(b.Parameters["Z"], 6) for b in befehle if "Z" in b.Parameters})
pruefe(abs(min(z_werte) + bb.TIEFER) < 1e-6, f"Z ab {min(z_werte)}")
pruefe(op.getEditorMode("Umlaeufe") == ["ReadOnly"], "Umläufe änderbar")

# Ändern: Gegenlauf, ohne Schlichten – G2 statt G3.
bo.aendere(op, tc1, schruppen.ap, schruppen.ae, 0.0, schlichten=False, gleichlauf=False)
doc.recompute()
namen = [b.Name for b in op.Path.Commands]
pruefe(
    "G2" in namen and "G3" not in namen,
    f"Gegenlauf: G2 {namen.count('G2')}, G3 {namen.count('G3')}",
)
pruefe(op.Schlichten is False and op.Gleichlauf is False, "geändert")
bo.aendere(op, tc1, schruppen.ap, schruppen.ae, 0.3)
doc.recompute()

# Speichern und Laden: dieselbe Bahn.
anzahl = len(op.Path.Commands)
pfad = os.path.join(tempfile.mkdtemp(), "bohrung.FCStd")
doc.saveAs(pfad)
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(pfad)
op = next(o for o in doc.Objects if bo.ist_bohrungsfraesen(o))
op.touch()
doc.recompute()
pruefe(len(op.Path.Commands) == anzahl, f"nach dem Laden {len(op.Path.Commands)} statt {anzahl}")
pruefe(op.getEditorMode("Umlaeufe") == ["ReadOnly"], "Umläufe nach dem Laden")
print(ascii(f"Operation: {anzahl} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
