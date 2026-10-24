# Prüft die Bahn „Fase“ (fase_bahn, W-037): Manuels Messspitzenhalter, vorn – der Bund Ø 15 0,8
# hoch, der Ringgrund bei −0,8 bis Ø 31,8, außen die Fase 45° hinauf bis Ø 33 bei −0,2 (ein Kegel,
# vom Grund zum Mantel). Sie ist eine Fase (45°, 0,6 breit), Grund, Mantel, Bund und Stirn nicht;
# die Stirn streift oben den Mantel. Mit dem Schaftfräser Ø 6 und der Stufe 0,05: 13 Lagen von −0,2
# bis −0,8, in einem Zug (geschlossen), je Lage die Achse 3 innerhalb des Schnitts der Fase, die
# Ecke der Stirn auf der Fase; nirgends ins Teil (Ein- und Ausfahren dazu), im Gleichlauf. Steht
# 1,2 mm darüber Material (Rohteil bis +1), kommt eine Lage über der Fase dazu. Der Fasenfräser 90°:
# eine Runde, die Spitze auf −0,8, die Achse 0,25 neben der Unterkante; 60° bekommt einen Satz.
# Die Drehrichtung: gegen den Uhrzeigersinn (die freie Seite innen, wie in einer Tasche).
# An einem Quader mit gefaster Oberkante (vier ebene Fasen) läuft die Bahn außen herum, Ecken als
# Bögen, die Stirn streift oben die Oberseite. lagen(): oben je Zustellung, auf der Fase je Stufe.
# fraeser_passt(): Ø 6 kommt neben dem Bund an die Fase, Ø 12 nicht; außen am Quader auch Ø 12.
# Die Spitze einer Sackbohrung ist keine Fase.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import fase_bahn as fb
from camaddon import fraeserform as ff
from camaddon import materialstand as mst
from camaddon import sprache

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
V = FreeCAD.Vector

# lagen(): Material bis 0 über der Oberkante −0,2 – keine Lage darüber (0,2 < Zustellung 1).
z = fb.lagen(-0.8, -0.2, 0.0, 0.05, 1.0)
pruefe(len(z) == 13 and abs(z[0] + 0.2) < 1e-9 and abs(z[-1] + 0.8) < 1e-9, f"lagen: {z}")
pruefe(all(a - b <= 0.05 + 1e-9 for a, b in zip(z, z[1:], strict=False)), "Stufe zu groß")
z2 = fb.lagen(-0.8, -0.2, 2.5, 0.05, 1.0)
pruefe(len(z2) == 13 + 2 and abs(z2[0] - 1.6) < 1e-9 and abs(z2[1] - 0.7) < 1e-9, f"darüber: {z2}")

profil = [(4.25, -20.2), (16.5, -20.2), (16.5, -0.2), (15.9, -0.8), (7.5, -0.8), (7.5, 0.0)]
profil += [(4.25, 0.0), (4.25, -20.2)]
flaeche = Part.Face(Part.makePolygon([V(r, 0, z) for r, z in profil]))
teil = Part.Solid(Part.Shell(flaeche.revolve(V(0, 0, 0), V(0, 0, 1), 360).Faces))
namen = [f"Face{i + 1}" for i in range(len(teil.Faces))]
kegel = next(n for n, f in zip(namen, teil.Faces, strict=True) if isinstance(f.Surface, Part.Cone))
mantel = next(
    n
    for n, f in zip(namen, teil.Faces, strict=True)
    if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 16.5) < 1e-6
)
pruefe(fb.ist_fase(teil, kegel), "der Kegel ist keine Fase")
pruefe(not any(fb.ist_fase(teil, n) for n in namen if n != kegel), "anderes gilt als Fase")
(fase,) = fb.fasen(teil, [kegel])
pruefe(abs(fase.winkel - 45) < 1e-6 and abs(fase.breite - 0.6) < 1e-6, f"Fase: {fase}")
pruefe(abs(fase.z_unten + 0.8) < 1e-9 and abs(fase.z_oben + 0.2) < 1e-9, f"Höhen: {fase}")
pruefe([f"Face{i + 1}" for i in fase.oben] == [mantel], f"oben gestreift: {fase.oben}")


def hoehe_teil(rho):
    """Die Oberseite des Messspitzenhalters bei r = rho (−inf: Luft)."""
    if rho < 4.25 or rho > 16.5:
        return -math.inf
    if rho <= 7.5:
        return 0.0
    if rho <= 15.9:
        return -0.8
    return -0.8 + (rho - 15.9)


def ins_teil(punkte, r):
    """Wie tief eine ebene Stirn (Radius r) an den Sätzen im Vorschub höchstens ins Teil geht –
    Bögen in Sehnen (materialstand.sehnen)."""
    tiefste = 0.0
    for a, b in zip(punkte, punkte[1:], strict=False):
        if b.eilgang:
            continue
        for von, nach in mst.sehnen(a, b, 0.2):
            for t in (0.0, 0.5, 1.0):
                x, y, zz = (von[i] + t * (nach[i] - von[i]) for i in range(3))
                mitte = math.hypot(x, y)
                for k in range(41):
                    rho = max(mitte - r + k * 2 * r / 40, 0.0)
                    tiefste = max(tiefste, hoehe_teil(rho) - zz)
    return tiefste


# Wer an die Fase kommt (fraeser_passt): Ø 6 neben dem Bund ja (8,4 breit), Ø 12 nicht.
pruefe(fb.fraeser_passt(teil, [fase], 3.0), "Ø 6 passt nicht an die Fase")
pruefe(not fb.fraeser_passt(teil, [fase], 6.0), "Ø 12 passt an die Fase (der Bund steht im Weg)")

netz_nah, netz_fern = fb.netze(teil, [fase])
werte = fb.Fasenwerte(form=ff.scheibe(3.0), sicher=10.0, oben=0.0)
bahn = fb.planen(teil, netz_nah, netz_fern, werte, [fase])
pruefe(bahn.fasen == 1 and bahn.lagen == 13 and bahn.bahnen == 1, f"Bahn: {bahn}")
pruefe(abs(bahn.z_min + 0.8) < 1e-9, f"tiefste {bahn.z_min}")
for lage in fb.lagen(-0.8, -0.2, 0.0, 0.05, 1.0):
    radien = [math.hypot(p.x, p.y) for p in bahn.punkte if not p.eilgang and abs(p.z - lage) < 1e-9]
    soll = 15.9 + (lage + 0.8) - 3.0
    pruefe(radien and abs(max(radien) - soll) < 0.02, f"Lage {lage:.2f}: r {max(radien or [0])}")
tiefe = ins_teil(bahn.punkte, 3.0)
pruefe(tiefe < 0.01, f"ins Teil: {tiefe:.3f}")
pruefe(sum(1 for p in bahn.punkte if p.eilgang) <= 4, "mehr als ein Zug")
# Im Gleichlauf um den Ring innen an der Fase (Material außen, rechts der Fahrt): gegen den
# Uhrzeigersinn, wie in einer Tasche – die Bögen auf einer Lage.
auf = [p for p in bahn.punkte if not p.eilgang and abs(p.z + 0.5) < 1e-9 and p.bogen]
pruefe(auf and not any(p.bogen[2] for p in auf), f"nicht gegen den Uhrzeigersinn: {auf}")

# Rohteil bis +1: eine Lage über der Fase (1,2 mm darüber, Zustellung 1 → bei 0,4).
hoch = fb.planen(
    teil, netz_nah, netz_fern, fb.Fasenwerte(form=ff.scheibe(3.0), sicher=10.0, oben=1.0), [fase]
)
pruefe(
    hoch.lagen == 14 and any(abs(p.z - 0.4) < 1e-9 for p in hoch.punkte), f"darüber: {hoch.lagen}"
)

# Mit Materialstand, der nach der Nut an der Fase nichts mehr zeigt (sein Raster ist gröber als die
# Fase): trotzdem alle 13 Lagen; zeigt er 3 mm darüber Material, zwei Lagen mehr (je 1 mm, die
# dritte ist die Oberkante der Fase).


class _Stand:
    schritt = 0.5

    def __init__(self, hoehe):
        self.hoehe = hoehe

    def hoechste_um(self, x, y, radius):
        return self.hoehe


nach_nut = fb.planen(teil, netz_nah, netz_fern, werte, [fase], stand=_Stand(-0.8))
pruefe(nach_nut.lagen == 13, f"nach der Nut: {nach_nut.lagen} Lagen")
dick = fb.planen(
    teil,
    netz_nah,
    netz_fern,
    fb.Fasenwerte(form=ff.scheibe(3.0), sicher=10.0, oben=5.0),
    [fase],
    stand=_Stand(2.8),
)
pruefe(dick.lagen == 15, f"3 mm darüber: {dick.lagen} Lagen")

# Der Fasenfräser 90° Ø 10, Spitze Ø 0,5: eine Runde auf −0,8, die Achse auf r 15,65.
kegelform = ff.kegel(0.25, 5.0, 4.75)
mit_kegel = fb.planen(
    teil,
    *fb.netze(teil, [fase]),
    fb.Fasenwerte(form=kegelform, sicher=10.0, oben=0.0, spitzenwinkel=90.0, spitze=0.5),
    [fase],
)
tief = [p for p in mit_kegel.punkte if not p.eilgang and abs(p.z + 0.8) < 1e-9]
pruefe(mit_kegel.lagen == 1 and mit_kegel.bahnen == 1, f"Fasenfräser: {mit_kegel}")
pruefe(
    tief and abs(max(math.hypot(p.x, p.y) for p in tief) - 15.65) < 0.02, "Achse nicht bei 15,65"
)
try:
    fb.planen(
        teil,
        netz_nah,
        netz_fern,
        fb.Fasenwerte(form=ff.kegel(0.25, 5.0, 2.74), sicher=10.0, oben=0.0, spitzenwinkel=60.0),
        [fase],
    )
    pruefe(False, "60° ohne Satz")
except ValueError as f:
    pruefe("90°" in str(f) and "60°" in str(f), f"Satz: {f}")

# Ein Quader 20 × 10 × 5, oben rundum 1 × 45° gefast: vier ebene Fasen, außen herum in einem Zug.
klotz = Part.makeBox(20, 10, 5)
oben_kanten = [
    k for k in klotz.Edges if abs(k.BoundBox.ZMin - 5) < 1e-9 and abs(k.BoundBox.ZMax - 5) < 1e-9
]
klotz = klotz.makeChamfer(1.0, oben_kanten)
k_namen = [f"Face{i + 1}" for i in range(len(klotz.Faces))]
k_fasen = fb.fasen(klotz, k_namen)
oberseite = next(
    n for n, f in zip(k_namen, klotz.Faces, strict=True) if abs(f.BoundBox.ZMin - 5) < 1e-9
)
pruefe(len(k_fasen) == 4, f"{len(k_fasen)} Fasen am Quader")
pruefe(fb.fraeser_passt(klotz, k_fasen, 6.0), "Ø 12 passt außen nicht an den Quader")
pruefe(
    all([f"Face{i + 1}" for i in f.oben] == [oberseite] for f in k_fasen),
    "oben: nicht die Oberseite",
)
k_bahn = fb.planen(
    klotz,
    *fb.netze(klotz, k_fasen),
    fb.Fasenwerte(form=ff.scheibe(3.0), sicher=12.0, oben=5.0),
    k_fasen,
)
pruefe(k_bahn.fasen == 1 and k_bahn.bahnen == 1 and k_bahn.lagen == 21, f"Quader: {k_bahn}")
auf_halb = [p for p in k_bahn.punkte if not p.eilgang and abs(p.z - 4.5) < 1e-9]
bb = (
    min(p.x for p in auf_halb),
    max(p.x for p in auf_halb),
    min(p.y for p in auf_halb),
    max(p.y for p in auf_halb),
)
pruefe(
    abs(bb[0] + 2.5) < 0.02 and abs(bb[1] - 22.5) < 0.02 and abs(bb[2] + 2.5) < 0.02,
    f"bei 4,5: {bb}",
)
pruefe(any(p.bogen for p in auf_halb), "Ecken ohne Bögen")
# Die Stirn ragt nirgends über die Fase hinein: Auf 4,5 liegt die Achse überall mindestens 3 vom
# Schnitt der Fase (das Rechteck 0,5 … 19,5 × 0,5 … 9,5).
for p in auf_halb:
    dx = max(0.5 - p.x, p.x - 19.5, 0.0)
    dy = max(0.5 - p.y, p.y - 9.5, 0.0)
    pruefe(math.hypot(dx, dy) >= 3.0 - 0.02, f"zu nah an der Fase: {p}")

# Die Spitze einer Sackbohrung (ein Kegel bis in die Spitze) ist keine Fase – an Manuels echtem
# Messspitzenhalter hielt der Block die Spitzen der Ø 2,5 dafür (die Spitze zählte als Kante).
platte = Part.makeBox(20, 20, 10)
bohrung = Part.makeCylinder(1.25, 6, V(10, 10, 5)).fuse(
    Part.makeCone(0, 1.25, 0.455, V(10, 10, 4.545))
)
platte = platte.cut(bohrung)
spitze = [f"Face{i + 1}" for i, f in enumerate(platte.Faces) if isinstance(f.Surface, Part.Cone)]
pruefe(spitze and not any(fb.ist_fase(platte, n) for n in spitze), f"Bohrspitze als Fase: {spitze}")

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
