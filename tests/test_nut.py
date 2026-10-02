# Prüft „Nut“ (W-006 4.1 Punkt 6): Platte 100 × 60 × 20 mit zwei Langlöchern – A 20 breit, 10
# tief, Halbkreise um (25, 20) und (55, 20); B 14 breit, durchgehend, um (25, 45) und (75, 45).
# Mit dem Standardfräser Ø 12 (ae 1,5, ap 25): A in Bögen (Radius 10 − 6 − 0,3, P-2026-10-02-53:
# nach der Helix Halbkreise von Wand zu Wand, quer zurück im Schnellvorschub; der Schritt nach
# der Last, P-2026-10-02-56: im Mittel ae, kurz bis 1,7 ae), B in voller Breite mit der
# Zickzack-Rampe (je Fahrt höchstens 3 tiefer, der Vorschub für den dicken Span gesenkt), beide
# zuletzt rundum an der Wand. Im Quader: die Nuten
# leer bis zum Grund (B 0,5 tiefer), daneben nichts angeschnitten; die Bögen im Gleichlauf (G3).
# Ein Fräser Ø 25 passt nicht, ein Ø 6 ist für A zu klein (ein Kern bliebe). Dann die Operation
# im Job: „Nut T1“, Endtiefe −0,5 (B durch), Art „nut“.
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

from camaddon import bahn as bn
from camaddon import fraeserform as ff
from camaddon import job_schnittwerte as js
from camaddon import materialstand as mst
from camaddon import nut as nu
from camaddon import nut_bahn as nb
from camaddon import pruefstand as ps
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


def langloch(a, b, r, z0, hoehe):
    """Ein Langloch als Körper: Quader zwischen den Mittelpunkten und zwei Zylinder."""
    laenge = b[0] - a[0]
    koerper = Part.makeBox(laenge, 2 * r, hoehe, V(a[0], a[1] - r, z0))
    koerper = koerper.fuse(Part.makeCylinder(r, hoehe, V(a[0], a[1], z0)))
    return koerper.fuse(Part.makeCylinder(r, hoehe, V(b[0], b[1], z0)))


platte = Part.makeBox(100, 60, 20)
teil = platte.cut(langloch((25, 20), (55, 20), 10, 10, 11))
teil = teil.cut(langloch((25, 45), (75, 45), 7, -1, 22)).removeSplitter()

boden_a = next(
    f"Face{i + 1}"
    for i, f in enumerate(teil.Faces)
    if abs(f.BoundBox.ZMax - 10) < 1e-6 and abs(f.BoundBox.ZMin - 10) < 1e-6
)
wand_b = next(
    f"Face{i + 1}"
    for i, f in enumerate(teil.Faces)
    if isinstance(f.Surface, Part.Plane)
    and abs(f.BoundBox.YMin - 52) < 1e-6
    and abs(f.BoundBox.YMax - 52) < 1e-6
)
oberseite = next(
    f"Face{i + 1}" for i, f in enumerate(teil.Faces) if abs(f.BoundBox.ZMin - 20) < 1e-6
)

# --- Erkennung ----------------------------------------------------------------------------------
nuten_a = nb.nuten(teil, [boden_a])
pruefe(len(nuten_a) == 1, f"A: {len(nuten_a)} Nuten")
nut_a = nuten_a[0]
pruefe(
    {nut_a.a, nut_a.b} == {(25.0, 20.0), (55.0, 20.0)} and abs(nut_a.radius - 10) < 1e-9,
    f"A: {nut_a.a} {nut_a.b} r {nut_a.radius}",
)
pruefe((nut_a.z_oben, nut_a.z_unten, nut_a.durch) == (20.0, 10.0, False), f"A: {nut_a}")
nuten_b = nb.nuten(teil, [wand_b])
pruefe(len(nuten_b) == 1 and nuten_b[0].durch, f"B: {nuten_b}")
nut_b = nuten_b[0]
pruefe(abs(nut_b.radius - 7) < 1e-9 and nut_b.z_unten == 0.0, f"B: {nut_b}")
pruefe(not nb.ist_nut(teil, oberseite), "Oberseite als Nut erkannt")
pruefe(nb.ist_grund(teil, boden_a) and not nb.ist_grund(teil, wand_b), "Grund falsch")
beide = nb.nuten(teil, [boden_a, wand_b, boden_a])
pruefe(len(beide) == 2, f"beide: {len(beide)}")
# Eine Wand meint die ganze Nut (Assistent: Nut und Kontur treten so gegeneinander an).
ganz = nb.ganze_nuten(teil, [wand_b, oberseite, boden_a])
pruefe(
    ganz == [*nut_b.waende, oberseite, boden_a] and len(nut_b.waende) >= 4,
    f"ganze Nut: {ganz}",
)

# --- Die Bahn mit dem Standardfräser -------------------------------------------------------------
t1 = wz.standardwerkzeug()
form = ff.von_werkzeug(t1)
R = 6.0
pruefe(nb.verfahren(nut_a, R, 0.3) == "boegen", "A nicht in Bögen")
pruefe(nb.verfahren(nut_b, R, 0.3) == "vollnut", "B nicht Vollnut")
pruefe(nb.verfahren(nut_a, 12.5) == "zu_schmal", "Ø 25 passt in A?")
pruefe(nb.verfahren(nut_a, 3.0, 0.3) == "zu_breit", "Ø 6 in A kein Kern?")


def werte(**weiter):
    grund = {
        "fraeser_radius": R,
        "zustellung": 25.0,
        "zeilenabstand": 1.5,
        "oben": 20.0,
        "sicher": 25.0,
        "aufmass": 0.3,
        "schneidenlaenge": 26.0,
        "eintauchwinkel": 3.0,
        "vorschub": 902.0,
        "eintauchen": 300.0,
    }
    grund.update(weiter)
    return nb.Nutwerte(**grund)


bahn = nb.planen(werte(), [nut_a, nut_b])
pruefe((bahn.nuten, bahn.vollnut) == (2, 1), f"{bahn.nuten} Nuten, {bahn.vollnut} Vollnut")
pruefe(abs(bahn.z_min + 0.5) < 1e-9, f"z_min {bahn.z_min}")
pruefe(bahn.lagen == 2, f"Lagen {bahn.lagen}")
# A: 30 lang, r_l 3,7 – ae ist die Last (Spezifikation Strategien 12.1 (a)): je Bogen im Mittel
# so viel Material je mm Weg wie auf gerader Bahn mit ae 1,5, der Schritt π r_l ae / (2 (r_l + R)
# − ae) = 0,97 (bis P-2026-10-02-55 der schonende 0,65); bis in den Halbkreis um B 31 Bögen.
r_l = 10 - R - 0.3
schritt = nb._bogenschritt(r_l, R, 1.5)
boegen_a = math.ceil(30.0 / schritt - 1e-9)
pruefe(0.95 < schritt < 1.0 and bahn.boegen == boegen_a == 31, f"Bögen {bahn.boegen}, {schritt}")
print(ascii(f"Zeit {bahn.zeit:.2f} min, {bahn.laenge:.0f} mm, {bahn.boegen} Bögen"))
# Quer zurück über die freie Seite im Schnellvorschub: dort trägt der Prüfstand nichts ab, und
# nirgends geht es ins Teil.
nur_a = nb.planen(werte(), [nut_a])
k_a = ps.messen([ps.Bahnlauf(nur_a.punkte, 902.0, 300.0)], teil, (0, 100, 0, 60), 20.0, form,
                1.5, 25.0, ebenen_z=[10.0], aufmass=0.3)  # fmt: skip
schnell = [p for p in nur_a.punkte if p.anteil > 1.0]
pruefe(len(schnell) == boegen_a - 1, f"quer im Schnellvorschub: {len(schnell)} Sätze")
pruefe(k_a.schnell_abtrag <= 1e-9, f"im Schnellvorschub abgetragen: {k_a.schnell_abtrag:.2f} mm³")
pruefe(k_a.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"A ins Teil: {k_a.einschnitt:.3f}")
print(ascii(f"A: {nur_a.zeit:.2f} min | {ps.zeile(k_a)}"))
# Die Last auf den Bögen, im feinen Raster (der Schritt ist kaum größer als eine Zelle von 0,5):
# in der Mitte jedes Bogens höchstens LAST_KURZ · ae, über LAST_DAUERND · ae nie länger als eine
# Fräserbreite am Stück. Die Helix und der Kreis unten formen das Rohteil – sie zählen nicht
# (ihr Keil ist breit und flach).
erster = next(
    i
    for i, p in enumerate(nur_a.punkte)
    if i and p.bogen is None and not p.eilgang and not p.eintauchen and abs(p.z - 10) < 1e-9
)
k_last = ps.messen([ps.Bahnlauf(nur_a.punkte[erster - 1 :], 902.0, 300.0)], teil,
                   (0, 100, 0, 60), 20.0, form, 1.5, 25.0, ebenen_z=[10.0], aufmass=0.3,
                   vorher=[ps.Bahnlauf(nur_a.punkte[:erster], 902.0, 300.0)], raster=0.1)  # fmt: skip
pruefe(
    1.25 < k_last.eingriff_max <= bn.LAST_KURZ and k_last.last_lang <= 2 * R,
    f"A Last: {ps.zeile(k_last)}",
)
print(ascii(f"A Bögen: {ps.zeile(k_last)}"))

# Die Mitte des Fräsers bleibt in der Nut: höchstens r − R neben der Mittellinie.
punkte = bahn.punkte


def neben(p, nut):
    ax, ay = nut.a
    bx, by = nut.b
    t = ((p.x - ax) * (bx - ax) + (p.y - ay) * (by - ay)) / nut.laenge**2
    t = min(max(t, 0.0), 1.0)
    return math.hypot(p.x - ax - t * (bx - ax), p.y - ay - t * (by - ay))


for p in punkte:
    if p.eilgang or p.z > 19.999:
        continue
    nut = nut_a if p.y < 32 else nut_b
    pruefe(neben(p, nut) <= nut.radius - R + 1e-6, f"außerhalb der Nut: {p}")
# Gleichlauf: alle Bögen gegen den Uhrzeigersinn; Gegenlauf alle im Uhrzeigersinn.
boegen = [p.bogen[2] for p in punkte if p.bogen is not None]
pruefe(boegen and not any(boegen), "Bögen im Uhrzeigersinn bei Gleichlauf")
gegen = nb.planen(werte(gleichlauf=False), [nut_a])
pruefe(all(p.bogen[2] for p in gegen.punkte if p.bogen is not None), "Gegenlauf nicht G2")

# Von Bogen zu Bogen: quer über die freie Seite zurück (2 r_l, links nach rechts der Fahrt in
# +x) und an der rechten Wand um den Schritt vor in den nächsten Bogen.
quer = [
    (a, b)
    for a, b in zip(punkte, punkte[1:], strict=False)
    if b.anteil > 1.0 and abs(a.x - b.x) < 1e-6 and abs(a.y - b.y - 2 * r_l) < 1e-6
]
vor = [
    (a, b)
    for a, b in zip(punkte, punkte[1:], strict=False)
    if not b.eilgang
    and b.bogen is None
    and b.anteil == 1.0
    and abs(a.z - 10) < 1e-9
    and abs(a.y - (20 - r_l)) < 1e-9
    and abs(b.y - (20 - r_l)) < 1e-9
    and 0 < b.x - a.x < schritt + 1e-6
]
pruefe(len(quer) == boegen_a - 1, f"quer zurück: {len(quer)}")
pruefe(len(vor) == boegen_a, f"an der Wand vor: {len(vor)}")
# Kein voller Kreis außer unten an der Helix um A: Die Bögen mit r_l überstreichen um jede andere
# Mitte höchstens 180° (das Schlichten fährt mit r − R = 4).
um = {}
for a, b in zip(punkte, punkte[1:], strict=False):
    if (
        b.bogen is not None
        and abs(a.z - b.z) < 1e-9
        and a.y < 32
        and abs(math.hypot(b.x - b.bogen[0], b.y - b.bogen[1]) - r_l) < 1e-6
    ):
        schluessel = (round(b.bogen[0], 6), round(b.bogen[1], 6))
        um[schluessel] = um.get(schluessel, 0.0) + bn.winkel(a, b)
voll = [m for m, w in um.items() if w > math.pi + 1e-6]
pruefe(voll == [(25.0, 20.0)] and len(um) == boegen_a + 1, f"volle Kreise um {voll}, {len(um)}")

# Vollnut B: je Fahrt höchstens 3 tiefer (min(ap, D/2) / 2), Vorschub für den dicken Span.
rampe = [
    (a, b)
    for a, b in zip(punkte, punkte[1:], strict=False)
    if not b.eilgang
    and b.bogen is None
    and abs(a.y - 45) < 1e-9
    and abs(b.y - 45) < 1e-9
    and abs(b.x - a.x) > 49
]
pruefe(rampe and all(a.z - b.z <= 3 + 1e-9 for a, b in rampe), "Rampe zu steil")
pruefe(
    all(abs(b.anteil - 2 * math.sqrt(0.125 * 0.875)) < 1e-9 for _a, b in rampe),
    f"Anteil {[b.anteil for _a, b in rampe][:2]}",
)
pruefe(min(b.z for _a, b in rampe) == -0.5, "Rampe nicht bis −0,5")


# --- Im Quader: die Nuten leer, daneben nichts angeschnitten ------------------------------------
def fein(punkte_):
    """Die Bögen in kurze Geraden – fahre() kennt nur Geraden."""
    ergebnis = [punkte_[0]]
    for a, b in zip(punkte_, punkte_[1:], strict=False):
        if b.bogen is None:
            ergebnis.append(b)
            continue
        mx, my, uhr = b.bogen
        r = math.hypot(a.x - mx, a.y - my)
        w0 = math.atan2(a.y - my, a.x - mx)
        weit = bn.winkel(a, b) * (-1 if uhr else 1)
        n = max(2, int(abs(weit) / math.radians(3)))
        for i in range(1, n + 1):
            w = w0 + weit * i / n
            z = a.z + (b.z - a.z) * i / n
            ergebnis.append(bn.Punkt(False, mx + r * math.cos(w), my + r * math.sin(w), z))
    return ergebnis


q = rm.Quader(0, 100, 0, 60, -1, 20, schritt=0.25)
q.h[:] = 20.0
fein_ = fein(punkte)
for a, b in zip(fein_, fein_[1:], strict=False):
    q.fahre((a.x, a.y, a.z), (b.x, b.y, b.z), form)
xs, ys = np.meshgrid(q.x, q.y, indexing="ij")


def abstand_nut(nut):
    ax, ay = nut.a
    bx, by = nut.b
    t = np.clip(((xs - ax) * (bx - ax) + (ys - ay) * (by - ay)) / nut.laenge**2, 0.0, 1.0)
    return np.hypot(xs - ax - t * (bx - ax), ys - ay - t * (by - ay))


for nut, grund in ((nut_a, 10.0), (nut_b, -0.5)):
    d = abstand_nut(nut)
    innen = d < nut.radius - 0.3  # bis aufs Aufmaß: dort muss alles weg sein
    pruefe(np.all(np.abs(q.h[innen] - grund) < 1e-6), f"Nut {nut.radius}: nicht leer")
    wand = (d > nut.radius - 0.2) & (d < nut.radius - 0.05)  # das Schlichten nahm das Aufmaß
    pruefe(np.all(q.h[wand] < grund + 1e-6), f"Nut {nut.radius}: Aufmaß an der Wand")
aussen = (abstand_nut(nut_a) > 10.05) & (abstand_nut(nut_b) > 7.05)
pruefe(np.all(q.h[aussen] >= 20.0 - 1e-9), "neben den Nuten angeschnitten")

# --- Die Eintauchstelle gewählt (W-012 E1): in der Mitte, in jeder Lage dort --------------------
mitte = nb.stelle(nut_a, 0.5)
bei = nb.planen(werte(zustellung=6.0, eintauchen_bei={nb.schluessel(nut_a): 0.5}), [nut_a])
helix = [
    b for a, b in zip(bei.punkte, bei.punkte[1:], strict=False) if b.bogen is not None and b.z < a.z
]  # die Bögen abwärts: die Helix
pruefe(
    bei.lagen == 2 and helix and all(abs(p.bogen[0] - mitte[0]) < 1e-9 for p in helix),
    f"Mitte: {bei.lagen} Lagen, Helix um {sorted({(p.bogen[0], p.bogen[1]) for p in helix})}",
)
pruefe(
    [st[:3] for st in bei.stellen] == [(nb.schluessel(nut_a), 0.5, False)],
    f"Stellen: {bei.stellen}",
)
q2 = rm.Quader(0, 100, 0, 60, -1, 20, schritt=0.25)
q2.h[:] = 20.0
fein_ = fein(bei.punkte)
for a, b in zip(fein_, fein_[1:], strict=False):
    q2.fahre((a.x, a.y, a.z), (b.x, b.y, b.z), form)
d = abstand_nut(nut_a)
pruefe(np.all(np.abs(q2.h[d < nut_a.radius - 0.3] - 10.0) < 1e-6), "Mitte: Nut nicht leer")
pruefe(np.all(q2.h[d > 10.05] >= 20.0 - 1e-9), "Mitte: neben der Nut angeschnitten")
# Der Vorschlag: Kreuzt eine Bohrung Ø 10 bis zum Grund die Nut bei x 32,5 (ein Viertel von A),
# taucht die Helix dort ein; ohne Bohrung abwechselnd an den Enden (None).
stand = mst.Materialstand(rm.Quader(0, 100, 0, 60, -1, 20), None)
stand.quader.h[:] = 20.0
stand.voll = stand.quader.h.copy()
pruefe(nb.vorschlag_bei(nut_a, werte(), stand, r_l) is None, "Vorschlag ohne Bohrung")
stand.quader.fahre((32.5, 20.0, 25.0), (32.5, 20.0, 10.0), 5.0)
vorschlag = nb.vorschlag_bei(nut_a, werte(), stand, r_l)
pruefe(vorschlag is not None and abs(vorschlag - 0.25) < 0.05, f"Vorschlag {vorschlag}")
mit_bohrung = nb.planen(werte(), [nut_a], stand)
pruefe(
    mit_bohrung.stellen
    and mit_bohrung.stellen[0][2]
    and abs(mit_bohrung.stellen[0][1] - 0.25) < 0.05,
    f"Stellen mit Bohrung: {mit_bohrung.stellen}",
)

# --- Werte, die nicht gehen ---------------------------------------------------------------------
for titel, w_, satz in (
    ("Ø 25", werte(fraeser_radius=12.5), "breit, der Fräser Ø 25"),
    ("Ø 6", werte(fraeser_radius=3.0), "bliebe ein Kern"),
):
    try:
        nb.planen(w_, [nut_a])
    except ValueError as grund:
        pruefe(satz in str(grund), f"{titel}: {grund}")
    else:
        pruefe(False, f"{titel}: kein Satz")

# --- Die Operation im Job -----------------------------------------------------------------------
import Path.Main.Job as PathJob

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([t1]))
doc = FreeCAD.newDocument("Nut")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
einsatz = next(e for e in t1.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
tc = js.controller_ohne_transaktion(doc, job, t1, einsatz)
doc.recompute()
op = nu.lege_an(job, tc, 25.0, 1.5, flaechen=[boden_a, wand_b])
doc.recompute()
pruefe(op.Label == "Nut T1" and op.Nuten == 2, f"{op.Label}, {op.Nuten} Nuten")
pruefe(abs(float(op.FinalDepth) + 0.5) < 1e-6, f"Endtiefe {float(op.FinalDepth)}")
pruefe(js.operationsart(op) == "nut", f"Art {js.operationsart(op)}")
pruefe(op.Boegen == boegen_a and op.Lagen == 2, f"Bögen {op.Boegen}, Lagen {op.Lagen}")
befehle = [c.Name for c in op.Path.Commands]
pruefe("G3" in befehle and "G2" not in befehle, "Bögen nicht G3")
# Der Eintauchwinkel des Fräsers kommt in die Operation – ihre Bahn ist die der Vorschau
# (P-2026-10-02-65; bis dahin rechnete die Operation mit 5°, die Vorschau mit dem Winkel am Fräser).
nu.aendere(op, tc, 25.0, 1.5, nu.AUFMASS, eintauchwinkel=3.0)
doc.recompute()
gewaehlt = [boden_a, wand_b]
vorschau = nu.vorschau(
    job, job.Model.Group, 6.0, 25.0, 1.5, nu.AUFMASS, gewaehlt, eintauchwinkel=3.0
)
gerechnet = nu.rechne(op, job, job.Model.Group)
pruefe(
    abs(float(op.Eintauchwinkel) - 3.0) < 1e-9 and len(gerechnet.punkte) == len(vorschau.punkte),
    f"Eintauchwinkel {float(op.Eintauchwinkel)}: {len(gerechnet.punkte)} statt "
    f"{len(vorschau.punkte)} Punkte",
)
print(ascii(f"Operation: {len(befehle)} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
