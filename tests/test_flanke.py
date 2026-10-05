# Prüft die Flanke (flanke_bahn.py, flanke.py; 5 Achsen simultan S3, Manuel 2026-10-04: „Ja, so
# bauen“): Block 80 × 60 × 30, darin eine Tasche 40 × 24, 20 tief, mit 10° Formschräge – die Ecken
# R 6 unten (Kegel), dazu dieselbe mit scharfen Ecken, ein Zapfen mit Formschräge und eine kurze
# Schneide. Ein Schaftfräser Ø 10 legt den Mantel an die Wand: ein Umlauf, die Achse 10° geneigt,
# kein Fräser im Teil, die Wand bis 0,002 mm getroffen; an scharfen Innenecken bleibt er so weit
# weg, wie sein Radius verlangt (jede Wand ein Umlauf); am Zapfen im Gleichlauf außen herum; mit
# 12 mm Schneide zwei Lagen. Die Operation im Job: je Satz eine Achse; auf der 5-Achs-Maschine
# Tisch/Tisch steht A auf −10°, C dreht einmal herum, unter einer Minute; an der 3-Achs-Fräse ein
# Satz, dass es nicht geht; „Programm schreiben“ ohne Maschine schreibt sie nicht.
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

from camaddon import abfahren as ab
from camaddon import beispielmaschine, sprache
from camaddon import flanke as flop
from camaddon import flanke_bahn as fb
from camaddon import job_schnittwerte as js
from camaddon import postprozessor as pp
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import simultan_operation as so
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
R = 5.0
D = 20 * math.tan(math.radians(10))


def rundrechteck(b, h, r, z, mx=40.0, my=30.0):
    x0, x1, y0, y1 = mx - b / 2, mx + b / 2, my - h / 2, my + h / 2
    if r <= 0:
        return Part.makePolygon(
            [V(x0, y0, z), V(x1, y0, z), V(x1, y1, z), V(x0, y1, z), V(x0, y0, z)]
        )
    kanten = []
    for (ax, ay), (ex, ey), (cx, cy), w0 in (
        ((x0 + r, y0), (x1 - r, y0), (x1 - r, y0 + r), -90),
        ((x1, y0 + r), (x1, y1 - r), (x1 - r, y1 - r), 0),
        ((x1 - r, y1), (x0 + r, y1), (x0 + r, y1 - r), 90),
        ((x0, y1 - r), (x0, y0 + r), (x0 + r, y0 + r), 180),
    ):
        kanten.append(Part.LineSegment(V(ax, ay, z), V(ex, ey, z)).toShape())
        kreis = Part.Circle(V(cx, cy, z), V(0, 0, 1), r)
        kanten.append(Part.ArcOfCircle(kreis, math.radians(w0), math.radians(w0 + 90)).toShape())
    return Part.Wire(kanten)


def tasche(r):
    unten = rundrechteck(40, 24, r, 10.0)
    oben = rundrechteck(40 + 2 * D, 24 + 2 * D, r + D if r > 0 else 0, 30.0)
    return Part.makeBox(80, 60, 30).cut(Part.makeLoft([unten, oben], True, True)).removeSplitter()


def zapfen():
    unten = rundrechteck(40 + 2 * D, 24 + 2 * D, 6 + D, 10.0)
    oben = rundrechteck(40, 24, 6, 30.0)
    return Part.makeBox(80, 60, 10).fuse(Part.makeLoft([unten, oben], True, True)).removeSplitter()


def waende(teil):
    return [f"Face{i + 1}" for i in range(len(teil.Faces)) if fb.ist_wand(teil, f"Face{i + 1}")]


def werte(schneide=30.0):
    return fb.Flankenwerte(
        radius=R, schneide=schneide, oben=30.0, sicher=40.0, vorschub=1000.0, eintauchen=300.0
    )


def im_teil(teil, bahn, schneide=30.0):
    """An wie vielen Stellen im Vorschub der Fräser (0,003 kleiner) das Teil berührt."""
    zahl = 0
    for p in bahn.punkte:
        if p.eilgang:
            continue
        zylinder = Part.makeCylinder(R - 0.003, min(schneide, 25.0), V(*p.spitze), V(*p.achse))
        zahl += teil.distToShape(zylinder)[0] < 1e-9
    return zahl


# --- Welche Flächen -----------------------------------------------------------------------------
teil_a = tasche(6)
namen_a = waende(teil_a)
pruefe(len(namen_a) == 8, f"Tasche R 6: {len(namen_a)} Wände")
oben = next(f"Face{i + 1}" for i, f in enumerate(teil_a.Faces) if f.BoundBox.ZMin > 29.99)
boden = next(
    f"Face{i + 1}"
    for i, f in enumerate(teil_a.Faces)
    if abs(f.BoundBox.ZMax - 10.0) < 1e-6 and f.BoundBox.ZLength < 1e-6
)
seite = next(
    f"Face{i + 1}"
    for i, f in enumerate(teil_a.Faces)
    if abs(f.BoundBox.XMin) < 1e-6 and f.BoundBox.XLength < 1e-6
)
pruefe(not any(fb.ist_wand(teil_a, n) for n in (oben, boden, seite)), "Oberseite, Boden, Seite")

# --- A: Tasche mit Kegel-Ecken ----------------------------------------------------------------
bahn = fb.planen(teil_a, namen_a, werte())
print(ascii(f"A: {bahn.umlaeufe} Umlauf, {bahn.laenge:.0f} mm, {bahn.zeit:.2f} min"))
pruefe(bahn.umlaeufe == 1 and bahn.lagen == 1 and bahn.weggelassen == 0, f"A: {bahn}")
pruefe(abs(bahn.neigung - 10.0) < 1e-6, f"A: Neigung {bahn.neigung}")
pruefe(im_teil(teil_a, bahn) == 0, "A: Fräser im Teil")
# Die Wände getroffen: Punkte darauf je kleinster Abstand zur Achse minus R.
# Die Maschine fährt zwischen zwei Stellen durch: alle 0,2 mm eine Lage des Fräsers dazwischen.
vorschub = [p for p in bahn.punkte if not p.eilgang and not p.eintauchen]
spitzen, achsen = [], []
for p, q in zip(vorschub, vorschub[1:], strict=False):
    a, b = np.array(p.spitze), np.array(q.spitze)
    n = max(1, int(np.linalg.norm(b - a) / 0.2))
    for k in range(n):
        spitzen.append(a + (b - a) * k / n)
        achse = np.array(p.achse) * (1 - k / n) + np.array(q.achse) * (k / n)
        achsen.append(achse / np.linalg.norm(achse))
spitzen, achsen = np.array(spitzen), np.array(achsen)
proben = []
for name in namen_a:
    flaeche = teil_a.getElement(name)
    u0, u1, v0, v1 = flaeche.ParameterRange
    for a in np.linspace(u0, u1, 30):
        for b in np.linspace(v0, v1, 20):
            p = flaeche.valueAt(a, b)
            if flaeche.isInside(p, 1e-6, True) and p.z > 10.05:
                proben.append((p.x, p.y, p.z))
Q = np.array(proben)
kleinste = np.full(len(Q), np.inf)
for k in range(0, len(spitzen), 100):
    d = Q[None, :, :] - spitzen[k : k + 100][:, None, :]
    t = np.clip(np.sum(d * achsen[k : k + 100][:, None, :], axis=2), 0, 30.0)
    weg = np.linalg.norm(d - t[..., None] * achsen[k : k + 100][:, None, :], axis=2) - R
    kleinste = np.minimum(kleinste, weg.min(axis=0))
print(ascii(f"A: Wand {kleinste.min():.4f} ... {kleinste.max():.4f} mm"))
pruefe(
    kleinste.min() > -0.002 and kleinste.max() < 0.002,
    f"A: Wand {kleinste.min()}, {kleinste.max()}",
)
# Gleichlauf: in der Tasche gegen den Uhrzeigersinn (von oben) – an der vorderen Wand nach +X.
vorn = [p for p in vorschub if p.spitze[1] < 25.0 and 30.0 < p.spitze[0] < 50.0]
pruefe(len(vorn) >= 2 and vorn[1].spitze[0] > vorn[0].spitze[0], "A: nicht im Gleichlauf")

# --- B: scharfe Ecken -------------------------------------------------------------------------
teil_b = tasche(0)
bahn_b = fb.planen(teil_b, waende(teil_b), werte())
print(ascii(f"B: {bahn_b.umlaeufe} Umläufe, {bahn_b.weggelassen} Stellen weggelassen"))
pruefe(
    bahn_b.umlaeufe == 4 and bahn_b.weggelassen > 0, f"B: {bahn_b.umlaeufe}, {bahn_b.weggelassen}"
)
pruefe(abs(bahn_b.neigung - 10.0) < 1e-6, f"B: Neigung {bahn_b.neigung}")
pruefe(im_teil(teil_b, bahn_b) == 0, "B: Fräser im Teil")
# An der vorderen Wand bis an die linke Wand heran: Auf Höhe der Spitze (z 10,87) steht die linke
# Wand bei x 20 − 0,87 · tan 10° = 19,85 – der Fräser R davor.
vorn_b = [p.spitze[0] for p in bahn_b.punkte if not p.eilgang and abs(p.spitze[1] - 22.92) < 0.1]
soll_b = 20.0 - 0.868 * math.tan(math.radians(10)) + R
pruefe(vorn_b and abs(min(vorn_b) - soll_b) < 0.01, f"B: vorn bis x {min(vorn_b, default=None)}")

# --- C: Zapfen, D: kurze Schneide ---------------------------------------------------------------
teil_c = zapfen()
bahn_c = fb.planen(teil_c, waende(teil_c), werte())
pruefe(bahn_c.umlaeufe == 1 and im_teil(teil_c, bahn_c) == 0, f"C: {bahn_c.umlaeufe}")
vorn_c = [
    p for p in bahn_c.punkte if not p.eilgang and p.spitze[1] < 12.0 and 30 < p.spitze[0] < 50
]
pruefe(len(vorn_c) >= 2 and vorn_c[1].spitze[0] < vorn_c[0].spitze[0], "C: nicht im Gleichlauf")
bahn_d = fb.planen(teil_a, namen_a, werte(12.0))
pruefe(bahn_d.lagen == 2 and bahn_d.umlaeufe == 2, f"D: {bahn_d.lagen} Lagen")
pruefe(im_teil(teil_a, bahn_d, 12.0) == 0, "D: Fräser im Teil")

# --- Die Operation im Job ---------------------------------------------------------------------
import Path.Main.Job as PathJob  # noqa: E402

t5 = wz.Werkzeug(
    nummer=5,
    name="VHM 10 lang",
    art=wz.SCHAFTFRAESER,
    durchmesser=10.0,
    schneiden=4,
    schneidenlaenge=30.0,
    schneidstoff=wz.VHM,
)
t5.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=20.0, vc=150.0, fz=0.04)]
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([wz.standardwerkzeug(), t5]))
doc = FreeCAD.newDocument("Flanke")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil_a
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
tc = js.controller_ohne_transaktion(doc, job, t5, t5.schnittwerte[wz.ALLE][0])
doc.recompute()
op = flop.lege_an(job, tc, flaechen=namen_a)
doc.recompute()
pruefe(op.Label == "Flanke T5", f"Name {op.Label}")
pruefe(op.Umlaeufe == 1 and op.Lagen == 1, f"Umläufe {op.Umlaeufe}, Lagen {op.Lagen}")
pruefe(abs(float(op.Schneide) - 30.0) < 1e-6, f"Schneide {op.Schneide}")
pruefe(len(op.Werkzeugachsen) == len(op.Path.Commands), "Achsen und Sätze")
pruefe(so.ist_simultan(op) and not so.senkrecht_moeglich(op), "nicht simultan")
pruefe(js.operationsart(op) == "flanke", f"Art {js.operationsart(op)}")

asm, ma = beispielmaschine.fuenfachs_tisch_tisch()
pruefung = rw.Pruefung(asm, ma)
null = rw.nullpunkt(job)
maschine = sw.Maschine(
    pruefung, pruefung.werkzeugaufnahme(tc.ToolNumber), rw.einspannung(tc, None), null
)
saetze = so.befehle(op, maschine)
bewegt = [b for b in saetze if b.Name == "G1"]
a_werte = [float(b.Parameters["A"]) for b in bewegt]
c_werte = [float(b.Parameters["C"]) for b in bewegt]
print(
    ascii(
        f"Maschine: A {min(a_werte):.3f} ... {max(a_werte):.3f}, C {min(c_werte):.1f} ... {max(c_werte):.1f}"
    )
)
pruefe(
    max(a_werte) - min(a_werte) < 1e-3 and abs(abs(a_werte[0]) - 10.0) < 1e-3,
    "A steht nicht auf 10°",
)
pruefe(abs(max(c_werte) - min(c_werte) - 360.0) < 1.0, f"C dreht {max(c_werte) - min(c_werte)}°")
ergebnis = rw.Pruefung(asm, ma).pruefe_job(job)
pruefe(
    not any("Flanke T5" in str(h) for h in ergebnis.hinweise),
    f"{[str(h) for h in ergebnis.hinweise]}",
)
zeit = ab.abfahrt(pruefung, job, null).stationen[-1].zeit / 60.0
print(ascii(f"Zeit auf der Maschine: {zeit:.2f} min"))
pruefe(0.1 < zeit < 1.0, f"Zeit {zeit:.2f} min")

# An der 3-Achs-Fräse: ein Satz; ohne Maschine schreibt das Programm sie nicht.
asm3, ma3 = beispielmaschine.fraesmaschine()
drei = rw.Pruefung(asm3, ma3).pruefe_job(job)
pruefe(
    any("Flanke T5" in str(h) and "zwei Rundachsen" in str(h) for h in drei.hinweise),
    "3-Achs ohne Satz",
)
ohne = pp.abschnitte(job)
pruefe(len(ohne) == 1 and ohne[0].befehle == [] and ohne[0].hinweis, "ohne Maschine geschrieben")
mit = pp.abschnitte(job, maschine)
pruefe(
    len(mit) == 1 and any("A" in dict(b.Parameters) for b in mit[0].befehle), "mit Maschine ohne A"
)
# Nachgelesen wie an der Steuerung (programm_pruefen): an jeder Steuerung, mit und ohne G93,
# nichts – Länge, Spindel, F (in G93 1 ÷ Zeit) in allen Sätzen.
info5 = pp.maschineninfo_dokument(asm.Document)
for kennung in pp.STEUERUNGEN:
    for aenderung in ({}, {"g93": False}):
        s = pp.steuerung(kennung, aenderung)
        befunde, _saetze = pp.nachlesen(pp.programm(mit, s, info5, "Flanke"), s, info5)
        pruefe(not befunde, f"{kennung} {aenderung}: {[(b.art, b.satz) for b in befunde[:3]]}")
# Mit TCPM (Haken; Manuel: „TCPM später als Haken“): die Spitze im Werkstück, F in mm/min, kein
# G93 dazwischen; der erste Satz im Vorschub ist genau die Spitze der Bahn; nicht mehr Sätze.
erster_g1 = next(c for c in op.Path.Commands if c.Name in ("G1", "G01"))
ohne_tcpm = pp.programm(mit, pp.steuerung("siemens"), info5, "Flanke")
for kennung, ein, aus in (
    ("siemens", "TRAORI", "TRAFOOF"),
    ("fanuc", "G43.4 H5", "G49"),
    ("haas", "G234 H5", "G49"),
):
    s = pp.steuerung(kennung, {"tcpm": True})
    p_t = pp.programm(mit, s, info5, "Flanke")
    z_t = p_t.zeilen
    k0 = z_t.index(ein) if ein in z_t else -1
    k1 = z_t.index(aus, k0) if k0 >= 0 and aus in z_t[k0:] else -1
    innen = z_t[k0:k1]
    # Der erste Satz im Schnittvorschub (an Haas davor der Weg unter TCPM hinab, im Eilgang-F).
    g1 = next((x for x in innen if x.startswith("G1") and float(x.split("F")[-1]) < 5000), "")
    pruefe(
        k0 >= 0 and k1 > k0 and not any("G93" in x for x in innen) and " F" in g1,
        f"{kennung} TCPM: {z_t[max(k0, 0):max(k0, 0) + 6]}",
    )
    werte = {w[0]: float(w[1:]) for w in g1.split()[1:] if w[0] in "XYZ"}
    soll = {k: float(erster_g1.Parameters[k]) for k in "XYZ" if k in erster_g1.Parameters}
    pruefe(
        werte and all(abs(werte[k] - soll[k]) < 1e-3 for k in soll),
        f"{kennung} TCPM: erster Satz {g1!r}, Bahn {soll}",
    )
    befunde, _saetze = pp.nachlesen(p_t, s, info5)
    pruefe(not befunde, f"{kennung} TCPM nachgelesen: {[(b.art, b.satz) for b in befunde[:3]]}")

    # Unter TCPM dreht kein Eilgang (die Spitze hielte keine Steuerung sicher): Ein G0 trägt die
    # Rundachsen des Satzes davor. Haas: G234 erst bei Rundachsen auf 0.
    def rund_von(zeile):
        # „A-10.000“ (Fanuc, Haas), „A1=-10.000“ oder an einer Moduloachse „C=ACP(10.000)“
        # (Siemens, P-2026-10-05-11) – je Achse der Wert.
        werte_r = {}
        for w in zeile.split():
            if w[:1] in ("A", "C") and len(w) > 1 and (w[1] in "-.0123456789=" or w[1:3] == "1="):
                wert = w.split("=")[-1] if "=" in w else w[1:]
                werte_r[w[0]] = float(wert.split("(")[-1].rstrip(")"))
        return werte_r

    vorher = {}
    for zeile in innen[1:]:
        if zeile.startswith("G0 ") and vorher and rund_von(zeile) != vorher:
            pruefe(False, f"{kennung}: Eilgang dreht unter TCPM: {zeile!r} nach {vorher}")
            break
        if zeile.startswith(("G0", "G1")) and rund_von(zeile):
            vorher = rund_von(zeile)
    if kennung == "haas":
        davor = [x for x in z_t[:k0] if rund_von(x)]
        pruefe(
            davor and all(v == 0.0 for v in rund_von(davor[-1]).values()),
            f"Haas: Rundachsen vor G234 nicht auf 0: {davor[-1:]}",
        )
    if kennung == "siemens":
        print(ascii(f"Flanke: {ohne_tcpm.saetze} Saetze ohne TCPM, {p_t.saetze} mit"))
        # Gerade Wände, die Achse hält: ohne TCPM war nichts zu verdichten – nicht mehr Sätze.
        pruefe(p_t.saetze <= ohne_tcpm.saetze, f"TCPM {p_t.saetze} Sätze, ohne {ohne_tcpm.saetze}")

FreeCAD.closeDocument(doc.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
