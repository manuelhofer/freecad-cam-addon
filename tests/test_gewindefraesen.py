# Prüft „Gewinde fräsen“ (W-006 S3g): metrische Innengewinde mit einem Gewindefräser Ø 8,
# Steigung 1,5. Platte 60 × 40 × 12 mit einem durchgehenden Kernloch Ø 8,5 bei (15, 20) und einer
# Sackbohrung Ø 8,5 bis z 3 bei (45, 20). Die Tabelle (Ø 8,5 mit 1,5 → M10 × 1,5; Ø 10,2 mit 1,75
# → M12 × 1,75; Ø 10 mit 1,5 passt nicht – der Satz nennt das Kernloch von M10 × 1,5), wie weit
# der Zahn hinausreicht (Mitte der Toleranz 6H: D2 9,116), die Bahn (aus der Mitte im Halbkreis
# hinein, Helix je Umlauf eine Steigung, im Gleichlauf G3 von unten nach oben, im Gegenlauf G2
# von oben, Linksgewinde umgekehrt; durchgehend eine Steigung hinaus, in der Sackbohrung über dem
# Grund), der Vorschub an der Schneide (die Mitte r / (r + R)), ein Fräser mit zehn Zähnen in
# einem Umlauf, die Fehler mit einem Satz, im Quader: das Gewinde bis zur Spitze des Zahns, nicht
# weiter, über dem Grund nichts; dann die Operation im Job (G3 mit Z, F an der Schneide geteilt,
# „Gewinde fräsen T7“, Art „gewindefraesen“) und die Ringe fürs Prüfen: mit ihnen nichts blau,
# ohne sie das Gewinde blau.
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
from camaddon import bohrung_bahn as bb
from camaddon import gewinde_bahn as gb
from camaddon import gewindefraesen as gf
from camaddon import job_schnittwerte as js
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

# --- Die Tabelle --------------------------------------------------------------------------------
for d, p, name in ((8.5, 1.5, "M10x1.5"), (10.2, 1.75, "M12x1.75"), (6.8, 1.25, "M8x1.25")):
    g = gb.gewinde_fuer(d, p)
    pruefe(g is not None and g.name == name, f"Ø {d} mit {p}: {g}")
for d, p in ((5.0, 1.0), (4.2, 0.8), (3.3, 0.7), (2.5, 0.5), (14.0, 2.0), (17.5, 2.5)):
    pruefe(gb.gewinde_fuer(d, p) is not None, f"Ø {d} mit {p}: kein Gewinde")
m10 = gb.gewinde_fuer(8.5, 1.5)
pruefe(abs(m10.flanke - 9.116) < 1e-9, f"D2 von M10x1.5: {m10.flanke}")
pruefe(gb.gewinde_fuer(9.0, 1.5) is None, "Ø 9 mit 1,5 passt")
pruefe(gb.naechstes(10.0, 1.5).name == "M10x1.5", "Ø 10 (Nenn-Ø gezeichnet): nicht M10x1.5")
pruefe(gb.zaehne_fuer(15.0, 1.5) == 10 and gb.zaehne_fuer(1.3, 1.5) == 1, "Zähne")

# --- Die Platte, die Stellen --------------------------------------------------------------------
teil = Part.makeBox(60, 40, 12)
teil = teil.cut(Part.makeCylinder(4.25, 12, V(15, 20, 0)))  # durchgehend
teil = teil.cut(Part.makeCylinder(4.25, 9, V(45, 20, 3))).removeSplitter()  # Grund bei z 3
liste = bb.bohrungen(teil)
durch = next(b for b in liste if b.durch)
sack = next(b for b in liste if not b.durch)
R = 4.0  # Fräserradius


def werte(**weiter):
    return gb.Gewindewerte(
        fraeser_radius=R, steigung=1.5, oben=12.0, sicher=20.0, vorschub=300.0, **weiter
    )


s = gb.stelle(durch, werte())
h_flanke = (0.75 - 1.5 / 8) / (2 * math.tan(math.radians(30)))
pruefe(abs(s.r_spitze - (9.116 / 2 + h_flanke)) < 1e-9, f"Spitze bei r {s.r_spitze:.4f}")
# Am Flankendurchmesser ist die Lücke halb so breit wie die Steigung (60°, vorn P/8 breit).
breite = 1.5 / 8 + 2 * (s.r_spitze - 9.116 / 2) * math.tan(math.radians(30))
pruefe(abs(breite - 0.75) < 1e-9, f"Lücke am Flankendurchmesser {breite:.4f}")
pruefe(abs(s.r_bahn - (s.r_spitze - R)) < 1e-12, "Radius der Helix")
# Die Mitte des Zahns liegt über der Spitze um die halbe Spitze und seine Höhe bis zum Hals
# (geschätzt 0,7 · Ø) mal tan 30°; die halbe Lücke am Kernloch um die halbe Spitze und die Tiefe
# des Gewindes mal tan 30°. Unten beginnt die Lücke ganz unter der Unterseite, oben endet sie
# ganz über der Oberkante – je 0,1 mm Rand.
tan30 = math.tan(math.radians(30))
mitte_zahn = 1.5 / 16 + (R - 0.7 * R) * tan30
luecke = 1.5 / 16 + (s.r_spitze - 4.25) * tan30
pruefe(abs(s.z_unten + mitte_zahn + luecke - (0.0 - 0.1)) < 1e-9, f"durchgehend unten {s.z_unten}")
pruefe(abs(s.z_oben + mitte_zahn - luecke - (12.0 + 0.1)) < 1e-9, f"oben {s.z_oben}")
print(f"durchgehend: Spitze von {s.z_unten:.3f} bis {s.z_oben:.3f}")
s_sack = gb.stelle(sack, werte())
pruefe(abs(s_sack.z_unten - (3.0 + 0.2 + 0.375)) < 1e-9, f"Sackbohrung: z {s_sack.z_unten}")


# --- Die Bahn -----------------------------------------------------------------------------------
def helix(bahn, mitte):
    """Die Bögen um die Achse (mitte) mit Vorschub: [(von, nach)]."""
    paare = zip(bahn.punkte, bahn.punkte[1:], strict=False)
    return [
        (a, b)
        for a, b in paare
        if b.bogen is not None and abs(b.bogen[0] - mitte[0]) + abs(b.bogen[1] - mitte[1]) < 1e-9
    ]


bahn = gb.planen(werte(), [durch])
bogen = helix(bahn, durch.mitte)
pruefe(bogen and all(not b.bogen[2] for _a, b in bogen), "Gleichlauf: nicht G3")
pruefe(all(b.z > a.z for a, b in bogen), "Rechtsgewinde im Gleichlauf: nicht von unten nach oben")
# Je Umlauf eine Steigung: z steigt mit dem Winkel um P / 2π; kein Bogen über ein Viertel.
steil = [(b.z - a.z) / bn.winkel(a, b) for a, b in bogen]
pruefe(all(abs(k - 1.5 / (2 * math.pi)) < 1e-9 for k in steil), f"Steigung: {steil[:3]}")
pruefe(max(bn.winkel(a, b) for a, b in bogen) <= math.pi / 2 + 1e-9, "Bogen über ein Viertel")
pruefe(abs(bahn.umlaeufe - (s.z_oben - s.z_unten) / 1.5) < 1e-9, f"Umläufe {bahn.umlaeufe}")
pruefe(abs(bahn.z_min - (s.z_unten - 0.375)) < 1e-9, f"z_min {bahn.z_min}")
weit = max(math.hypot(p.x - 15, p.y - 20) for p in bahn.punkte)
pruefe(weit < s.r_bahn + 1e-9, f"über die Helix hinaus: {weit:.4f}")
anteile = sorted({round(p.anteil, 6) for p in bahn.punkte if not p.eilgang})
r = s.r_bahn
soll = sorted({round(r / (r + R), 6), round((r / 2) / (r / 2 + R), 6)})
pruefe(anteile == soll, f"Vorschub-Anteile {anteile}, soll {soll}")
# Hinein: aus der Mitte im Halbkreis, eine Viertel-Steigung tiefer als die Helix beginnt.
start = next(i for i, p in enumerate(bahn.punkte) if not p.eilgang)
vor, ein = bahn.punkte[start - 1], bahn.punkte[start]
pruefe(
    vor.eilgang and (vor.x, vor.y) == durch.mitte and abs(ein.z - vor.z - 0.375) < 1e-9,
    f"hinein: {vor} → {ein}",
)
pruefe(abs(bn.winkel(vor, ein) - math.pi) < 1e-9, "hinein kein Halbkreis")

gegen = gb.planen(werte(gleichlauf=False), [durch])
bogen = helix(gegen, durch.mitte)
pruefe(bogen and all(b.bogen[2] for _a, b in bogen), "Gegenlauf: nicht G2")
pruefe(all(b.z < a.z for a, b in bogen), "Gegenlauf: nicht von oben nach unten")
links = gb.planen(werte(links=True), [durch])
bogen = helix(links, durch.mitte)
pruefe(all(not b.bogen[2] and b.z < a.z for a, b in bogen), "Linksgewinde: nicht G3 hinab")

beide = gb.planen(werte(), liste)
pruefe(beide.gewinde == [("M10x1.5", 2)] and beide.bohrungen == 2, f"{beide.gewinde}")
tief_sack = min(p.z for p in beide.punkte if math.hypot(p.x - 45, p.y - 20) < 6)
pruefe(abs(tief_sack - 3.2) < 1e-9, f"Sackbohrung: am tiefsten {tief_sack}")
zehn = gb.planen(werte(zaehne=10), liste)
pruefe(abs(zehn.umlaeufe - 2.0) < 1e-9, f"zehn Zähne: {zehn.umlaeufe} Umläufe")
pruefe(zehn.zeit < beide.zeit / 4, f"zehn Zähne: {zehn.zeit:.2f} min, einer {beide.zeit:.2f}")
print(f"Gewinde: einer {beide.zeit:.2f} min, zehn Zaehne {zehn.zeit:.2f} min")

# --- Die Fehler ---------------------------------------------------------------------------------
fall = (
    ("zu groß", durch, {"fraeser_radius": 4.2}, "zu groß"),
    ("Hals", durch, {"hals_radius": 3.3}, "Hals"),
    ("Reichweite", durch, {"reichweite": 10.0}, "reicht nur"),
    ("Steigung", durch, {"steigung": 1.25}, "kein Kernloch"),
)
for titel, b, anders, satzteil in fall:
    w = werte()
    for k, v in anders.items():
        setattr(w, k, v)
    try:
        gb.stelle(b, w)
    except ValueError as grund:
        pruefe(satzteil in str(grund), f"{titel}: {grund}")
    else:
        pruefe(False, f"{titel}: kein Fehler")
flach = bb.Bohrung("F", (0.0, 0.0), 4.25, 12.0, 11.8, False)
try:
    gb.stelle(flach, werte())
except ValueError as grund:
    pruefe("zu flach" in str(grund), f"flach: {grund}")
else:
    pruefe(False, "flach: kein Fehler")

# --- Im Quader: bis zur Spitze des Zahns, nicht weiter ------------------------------------------
quader = rm.Quader(0, 60, 0, 40, -3, 12, schritt=0.1)
for b in liste:  # die Kernlöcher, wie gebohrt
    quader.fahre((*b.mitte, 20.0), (*b.mitte, b.z_unten - (3 if b.durch else 0)), 4.25)


def fein(punkte):
    """Die Bögen in kurze Geraden – fahre() kennt nur Geraden."""
    ergebnis = [punkte[0]]
    for a, b in zip(punkte, punkte[1:], strict=False):
        if b.bogen is None:
            ergebnis.append(b)
            continue
        mx, my, _uhr = b.bogen
        r_b = math.hypot(a.x - mx, a.y - my)
        w0 = math.atan2(a.y - my, a.x - mx)
        weit = bn.winkel(a, b) * (-1 if b.bogen[2] else 1)
        n = max(2, int(abs(weit) / math.radians(5)))
        for i in range(1, n + 1):
            t = i / n
            w = w0 + weit * t
            ergebnis.append(
                bn.Punkt(
                    False, mx + r_b * math.cos(w), my + r_b * math.sin(w), a.z + (b.z - a.z) * t
                )
            )
    return ergebnis


punkte = fein(beide.punkte)
for a, b in zip(punkte, punkte[1:], strict=False):
    quader.fahre((a.x, a.y, a.z), (b.x, b.y, b.z), R)


def hoehe(x, y):
    i = int(np.argmin(np.abs(quader.x - x)))
    j = int(np.argmin(np.abs(quader.y - y)))
    return float(quader.h[i, j])


spitze = s.r_spitze
for (mx, my), unten in (((15.0, 20.0), s.z_unten), ((45.0, 20.0), s_sack.z_unten)):
    abstand = np.hypot(quader.x[:, None] - mx, quader.y[None, :] - my)
    ring = (abstand > spitze - 0.3) & (abstand < spitze - 0.05)
    tiefste = float(quader.h[ring].min())
    # Am tiefsten im Halbkreis hinein (eine Viertel-Steigung unter dem Anfang der Helix).
    pruefe(unten - 0.375 - 1e-9 <= tiefste <= unten, f"({mx}, {my}): Ring bis {tiefste:.3f}")
    # Bei jedem Winkel geht der Ring mindestens bis eine Steigung über den Anfang der Helix.
    pruefe(float(quader.h[ring].max()) <= unten + 1.5 + 0.05, f"({mx}, {my}): Ring nicht ganz")
    hinter = (abstand > spitze + 0.06) & (abstand < spitze + 2.0)
    pruefe(float(quader.h[hinter].min()) == 12.0, f"({mx}, {my}): hinter der Spitze gefräst")
pruefe(abs(hoehe(45.0, 20.0) - 3.0) < 1e-9, f"Grund der Sackbohrung: {hoehe(45.0, 20.0):.2f}")

# --- Die Operation im Job -----------------------------------------------------------------------
import Path.Main.Job as PathJob

t7 = wz.Werkzeug(
    nummer=7,
    name="GF M10",
    art=wz.GEWINDEFRAESER,
    durchmesser=8.0,
    steigung=1.5,
    schneiden=3,
    schneidenlaenge=1.3,
    hals_d=6.0,
    hals_laenge=20.0,
    schaft=8.0,
)
t7.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.GEWINDEFRAESEN, vc=80.0, fz=0.05)]
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([wz.standardwerkzeug(), t7]))
doc = FreeCAD.newDocument("Gewindefraesen")
objekt = doc.addObject("Part::Feature", "Platte")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
tc = js.controller_ohne_transaktion(doc, job, t7, t7.schnittwerte[wz.ALLE][0])
doc.recompute()
pruefe(gf.zaehne_von(t7) == 1, f"Zähne von T7: {gf.zaehne_von(t7)}")
vorschau = gf.vorschau(job, t7, [b.name for b in liste], vorschub=300.0)
op = gf.lege_an(job, tc, 1.5, gf.zaehne_von(t7), flaechen=[b.name for b in liste])
doc.recompute()
pruefe(op.Label == "Gewinde fräsen T7", f"Name {op.Label!r}")
pruefe(js.operationsart(op) == "gewindefraesen", f"Art {js.operationsart(op)}")
pruefe(op.Gewinde == "2 × M10x1.5" and op.Bohrungen == 2, f"{op.Gewinde!r}, {op.Bohrungen}")
pruefe(abs(float(op.FinalDepth) - vorschau.z_min) < 1e-6, f"Endtiefe {float(op.FinalDepth)}")
befehle = op.Path.Commands
g3 = [c for c in befehle if c.Name == "G3" and "Z" in c.Parameters]
pruefe(len(g3) > 40, f"G3 mit Z: {len(g3)}")
pruefe(not [c for c in befehle if c.Name == "G2"], "G2 im Gleichlauf")
vf = float(tc.HorizFeed.getValueAs("mm/min"))
f_helix = max(c.Parameters["F"] for c in g3) * 60.0
pruefe(abs(f_helix - vf * r / (r + R)) < 0.5, f"F der Helix {f_helix:.1f}, vf {vf:.0f}")
pruefe(abs(op.Umlaeufe - vorschau.umlaeufe) < 0.01, f"Umläufe {op.Umlaeufe}")
print(ascii(f"Operation: {len(befehle)} Befehle, vf {vf:.0f}, Helix {f_helix:.1f} mm/min"))
ringe = gf.ringe(op, job)
pruefe(len(ringe) == 2 and all(abs(rr - spitze) < 1e-9 for _x, _y, rr in ringe), f"Ringe {ringe}")

# --- Prüfen: mit den Ringen nichts blau, ohne sie das Gewinde ------------------------------------
abtrag_punkte = []
for b in liste:
    abtrag_punkte += [
        (*b.mitte, 20.0),
        (*b.mitte, b.z_unten - (3 if b.durch else 0)),
        (*b.mitte, 20.0),
    ]
bohr = len(abtrag_punkte)
abtrag_punkte += [(p.x, p.y, p.z) for p in punkte]
operation = np.array([0] * bohr + [1] * (len(abtrag_punkte) - bohr))
gueltig = np.ones(len(abtrag_punkte), dtype=bool)
for mit_ringen in (True, False):
    abtrag = rm.QuaderAbtrag(
        rm.Quader(0, 60, 0, 40, -3, 12),
        abtrag_punkte,
        operation,
        gueltig,
        {0: 4.25, 1: R},
        0.0,
        [teil],
        ringe={1: ringe} if mit_ringen else None,
    )
    abtrag.bis_station(abtrag.letzte())
    blau = int((abtrag.vergleich().farbe == rm.BLAU).sum())
    pruefe((blau == 0) == mit_ringen, f"Ringe {mit_ringen}: {blau} Zellen blau")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
