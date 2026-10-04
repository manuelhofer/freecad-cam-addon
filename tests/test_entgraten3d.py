# SPDX-License-Identifier: LGPL-2.1-or-later
# Entgraten in 3D (W-015 S5, entgrat3d_bahn): ein Klotz 60 × 40 × 20 mit 30°-Schräge, einer Nut
# 6 mm breit und einer Bohrung Ø 10. Je Weg (5 Achsen mit Fasenfräser 90°, 5 Achsen mit
# Schaftfräser, 3 Achsen mit Fasenfräser) für jede Stelle:
# - die Geometrie: 5 Achsen – der Kegel liegt an der Fase an (a · nP = sin α), die Fase
#   symmetrisch, die Mantellinie durch ihre Mitte trifft beide Ränder auf dem Kegelmantel
#   (senkrecht zur Kante genau an der Kante gegenüber, um nP gekippt längs der Kante versetzt),
#   bzw. die Enden in der Stirn; 3 Achsen – die Achse senkrecht, die Breite auf der Fläche, die
#   nach oben schaut;
# - unabhängig mit OpenCascade: Der Fräser (0,02 mm längs der Achse zurück) schneidet das Teil
#   nur im Keil an der Kante (auf der Seite der Fase, nahe der Kante) – sonst beschädigte er es.
# Die Nut ist schmaler als der Kegel: Dort fast es nur, wo es passt, und sagt den Rest („eng“).
# Die Enden: An einer Ecke läuft die Fase bis hinein, an einer Wand hört sie vorher auf (Stufe).
# Mit Halter und Spindel kippt der Kegel unten an den senkrechten Kanten nach oben – waagrecht
# käme die Spindel dem Tisch zu nah.
# Schaft, Halter und Spindel (P-2026-10-04-67): ihr Abstand zum Teil und zum Tisch gegen
# OpenCascade; im Job prüft die Kollision an der 5-Achs-Maschine – nichts berührt, nichts kommt
# näher als 1 mm (die Kollisionsprüfung fand am Schwenkteil Spindel und Halter im Rundtisch).
# Ausführen: freecadcmd tests/test_entgraten3d.py

import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import entgrat3d_bahn as e3
from camaddon import sprache

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
V = FreeCAD.Vector

# --- Das Teil ---------------------------------------------------------------------------------
klotz = Part.makeBox(60, 40, 20)
# Die Schräge: rechts von x 40 fällt die Oberseite um 30° (bei x 60 noch 20 − 20 · tan 30°).
keil = Part.makePolygon(
    [
        V(40, -1, 20),
        V(61, -1, 20 - 21 * math.tan(math.radians(30))),
        V(61, -1, 30),
        V(40, -1, 30),
        V(40, -1, 20),
    ]
)
keil = Part.Face(keil).extrude(V(0, 42, 0))
teil = klotz.cut(keil)
teil = teil.cut(Part.makeBox(6, 42, 5, V(17, -1, 15)))  # die Nut quer, 6 breit, 5 tief
teil = teil.cut(Part.makeCylinder(5, 30, V(8, 20, -5)))  # die Bohrung Ø 10
teil = teil.removeSplitter()
pruefe(teil.isValid() and len(teil.Solids) == 1, "Teil kaputt")
namen = [f"Face{i + 1}" for i in range(len(teil.Faces))]
kanten = e3.kanten(teil, namen)
print(ascii(f"{len(kanten)} Kanten zu fasen"))
pruefe(len(kanten) >= 20, f"Kanten: {len(kanten)}")
pruefe(
    all(
        min(v.Point.z for v in k.kante.Vertexes) > 1e-6 or k.kante.BoundBox.ZMax > 1e-6
        for k in kanten
    ),
    "eine Unterkante auf dem Tisch",
)

KEGEL = e3.Fraeser3D(5.0, math.radians(45), 0.25, 10.0)
FLACH = e3.Fraeser3D(5.0, 0.0, 5.0, 20.0)


def fraeserkoerper(lage, fraeser):
    """Der Fräser als Körper, 0,02 mm längs der Achse zurück (die Berührung in der Fase)."""
    a = FreeCAD.Vector(*lage.achse)
    zurueck = 0.02 / (math.sin(fraeser.halbwinkel) if fraeser.kegel else 1.0)
    spitze = FreeCAD.Vector(*(lage.spitze + zurueck * lage.achse))
    if fraeser.kegel:
        koerper = Part.makeCone(fraeser.spitze, fraeser.radius, fraeser.kegelhoehe, spitze, a)
        return koerper.fuse(
            Part.makeCylinder(fraeser.radius, e3.SCHAFT, spitze + a * fraeser.kegelhoehe, a)
        )
    return Part.makeCylinder(fraeser.radius, fraeser.hoehe, spitze, a)


def keilpruefung(lage, e, t, schenkel, fraeser, form):
    """Schneidet der Fräser (0,02 mm zurück) das Teil nur im Keil an der Kante? (größte
    Abweichung in mm, 0: ja)"""
    gemeinsam = fraeserkoerper(lage, fraeser).common(form)
    if gemeinsam.isNull() or gemeinsam.Volume < 1e-9:
        return 0.0
    punkte, _d = gemeinsam.tessellate(0.01)
    x = np.array([[p.x, p.y, p.z] for p in punkte] + [[v.X, v.Y, v.Z] for v in gemeinsam.Vertexes])
    ueber = -((x - e) @ lage.normale + lage.tiefe)  # > 0: auf der Seite des Teils
    quer = (x - e) - np.outer((x - e) @ t, t)
    weit = np.linalg.norm(quer, axis=1) - (max(schenkel) + e3.STREIFEN)
    return float(max(np.max(ueber), np.max(weit), 0.0))


def durchgehen(werte, titel, stichproben=6, grob=None):
    """Je Kante einige Stellen (und einige gekippte): Geometrie und Keil; gibt (Kanten mit Fase,
    eng in mm, gekippte Stellen)."""
    wolke = e3.wolke(teil, kanten, werte.fraeser.hoehe + werte.fraeser.radius)
    gefast, eng, gekippt = 0, 0.0, 0
    schlimmste = 0.0
    for k in kanten:
        stellen = e3._stellen_der_kante(k, werte, wolke, e3.SCHRITT, grob)
        mit = [(p, lage) for p, lage, _g in stellen if lage is not None]
        schritt = k.kante.Length / max(len(stellen) - 1, 1)
        eng += schritt * sum(1 for _p, lage, g in stellen if g == e3.ENG)
        if mit:
            gefast += 1
        # Dazu die gekippten (um nP, nicht senkrecht zur Kante) – sie sind selten.
        schief = [
            (p, lage)
            for p, lage in mit
            if werte.art == e3.FUENF and abs(lage.achse @ e3._geometrie(k, p)[1]) > 1e-6
        ]
        gekippt += len(schief)
        auswahl = mit[:: max(1, len(mit) // stichproben)] + schief[:: max(1, len(schief) // 3)]
        for p, lage in auswahl:
            e, t, n1, n2, u1, u2 = e3._geometrie(k, p)
            a = lage.achse
            if werte.art == e3.FUENF:
                pruefe(
                    abs(lage.schenkel[0] - werte.breite) < 1e-9
                    and abs(lage.schenkel[1] - werte.breite) < 1e-9,
                    f"{titel} {k.name}: Schenkel {lage.schenkel}",
                )
                q = [e + lage.schenkel[0] * u1, e + lage.schenkel[1] * u2]
                n_p = lage.normale
                mitte, quer_ = 0.5 * (q[0] + q[1]), (q[1] - q[0]) / np.linalg.norm(q[1] - q[0])
                if werte.fraeser.kegel:
                    sin_a = math.sin(werte.fraeser.halbwinkel)
                    pruefe(
                        abs(float(a @ n_p) - sin_a) < 1e-6,
                        f"{titel} {k.name}: Kegel liegt nicht an ({a @ n_p:.4f})",
                    )
                    mantel = a - (a @ n_p) * n_p
                    mantel /= np.linalg.norm(mantel)
                for qi in q:
                    if werte.fraeser.kegel:
                        # Wo die Mantellinie durch die Mitte den Rand der Fase trifft.
                        qi = mitte + float((qi - mitte) @ quer_) / float(mantel @ quer_) * mantel
                    rel = qi - lage.spitze
                    h = float(rel @ a)
                    radial = float(np.linalg.norm(rel - h * a))
                    if werte.fraeser.kegel:
                        soll = float(werte.fraeser.radius_bei(np.array([h]))[0])
                        pruefe(
                            abs(radial - soll) < 1e-6 and -1e-9 <= h <= werte.fraeser.kegelhoehe,
                            f"{titel} {k.name}: Fase nicht am Mantel {radial} {soll} (h {h:.3f})",
                        )
                    else:
                        pruefe(
                            abs(h) < 1e-6 and radial <= werte.fraeser.spitze + 1e-9,
                            f"{titel} {k.name}: Fase nicht in der Stirn (h {h:.2e}, r {radial:.3f})",
                        )
            else:
                pruefe(np.allclose(a, (0, 0, 1)), f"{titel}: Achse nicht senkrecht")
                oben = 0 if n1[2] >= n2[2] else 1
                pruefe(
                    abs(lage.schenkel[oben] - werte.breite) < 1e-9,
                    f"{titel} {k.name}: oben {lage.schenkel}",
                )
            tief = keilpruefung(lage, e, t, lage.schenkel, werte.fraeser, teil)
            schlimmste = max(schlimmste, tief)
            pruefe(tief < 0.03, f"{titel} {k.name}: beschädigt das Teil um {tief:.3f} mm")
    print(
        ascii(
            f"{titel}: {gefast} Kanten mit Fase, eng {eng:.0f} mm, schlimmstens {schlimmste:.3f} mm,"
            f" {gekippt} Stellen gekippt"
        )
    )
    return gefast, eng, gekippt


fuenf_kegel = durchgehen(e3.Werte3D(KEGEL, 0.5, e3.FUENF, sicher=40.0), "5 Achsen Kegel")
fuenf_flach = durchgehen(e3.Werte3D(FLACH, 0.5, e3.FUENF, sicher=40.0), "5 Achsen flach")
drei = durchgehen(e3.Werte3D(KEGEL, 0.5, e3.DREI, sicher=40.0), "3 Achsen Kegel")
pruefe(
    fuenf_kegel[0] >= 15 and fuenf_flach[0] >= 12 and drei[0] >= 8,
    f"zu wenig Kanten: {fuenf_kegel}, {fuenf_flach}, {drei}",
)
pruefe(fuenf_kegel[1] > 0, "die Nut ist schmaler als der Kegel – nirgends eng?")

# Die ganze Bahn: Punkte mit Achse, Eintauchen längs der Achse, Ergebnis mit Gründen.
bahn = e3.planen(teil, namen, e3.Werte3D(KEGEL, 0.5, e3.FUENF, sicher=40.0, vorschub=600.0))
print(
    ascii(
        f"Bahn: {bahn.kanten} Kanten, {bahn.laenge:.0f} mm, ohne {bahn.ausgelassen:.0f} mm {bahn.gruende}, Neigung {bahn.neigung:.0f}"
    )
)
pruefe(bahn.punkte and bahn.punkte[0].eilgang and bahn.laenge > 300, f"Bahn: {bahn.laenge}")
pruefe(
    all(abs(np.linalg.norm(p.achse) - 1.0) < 1e-9 for p in bahn.punkte),
    "Achse nicht normiert",
)
eintauchen = [p for p in bahn.punkte if p.eintauchen]
pruefe(len(eintauchen) >= bahn.kanten, f"Eintauchen: {len(eintauchen)}")
pruefe(
    set(bahn.gruende) <= {e3.ENG, e3.STEIL, e3.KEINE_STELLUNG, e3.ANFAHRT, e3.TISCH, e3.HALTER},
    f"{bahn.gruende}",
)
# 3 Achsen mit einem Fräser mit ebener Stirn geht nicht; ohne Kanten auch nicht.
for werte, text in (
    (e3.Werte3D(FLACH, 0.5, e3.DREI), "3 Achsen flach"),
    (e3.Werte3D(KEGEL, 0.0, e3.FUENF), "Breite 0"),
):
    try:
        e3.planen(teil, namen, werte)
        pruefe(False, f"{text}: kein Fehler")
    except ValueError:
        pass

# --- Die Enden: an einer Ecke bis hinein, an einer Wand davor -----------------------------------
# Eine Stufe: unten 60 × 40 × 10, rechts darauf ein Block 20 × 40 × 10. Die vordere Oberkante
# der unteren Stufe endet links an einer Ecke (die Fase läuft durch, das Dreieck jenseits der
# Fasenebene geht aus der linken Seite) und rechts an der Wand des Blocks (dort hört sie vorher
# auf – der Block bleibt unberührt, unabhängig mit OpenCascade).
block = Part.makeBox(20, 40, 10, V(40, 0, 10))
stufe = Part.makeBox(60, 40, 10).fuse(block).removeSplitter()
unten_oben = next(
    f"Face{i + 1}"
    for i, f in enumerate(stufe.Faces)
    if abs(f.BoundBox.ZMin - 10) < 1e-6 and abs(f.BoundBox.ZMax - 10) < 1e-6
)
stufen_kanten = e3.kanten(stufe, [unten_oben])
pruefe(len(stufen_kanten) == 3, f"Stufe: {len(stufen_kanten)} Kanten (ohne die Innenkante)")
vorn = next(
    k
    for k in stufen_kanten
    if k.kante.BoundBox.YMax < 1e-6 and abs(k.kante.BoundBox.ZMin - 10) < 1e-6
)
for werte, titel in (
    (e3.Werte3D(KEGEL, 0.5, e3.FUENF, sicher=40.0), "Stufe 5 Achsen Kegel"),
    (e3.Werte3D(FLACH, 0.5, e3.FUENF, sicher=40.0), "Stufe 5 Achsen flach"),
    (e3.Werte3D(KEGEL, 0.5, e3.DREI, sicher=40.0), "Stufe 3 Achsen Kegel"),
):
    wolke_stufe = e3.wolke(stufe, stufen_kanten, werte.fraeser.hoehe + werte.fraeser.radius)
    mit = [(p, lage) for p, lage, _g in e3._stellen_der_kante(vorn, werte, wolke_stufe) if lage]
    xs = [float(e3._geometrie(vorn, p)[0][0]) for p, _lage in mit]
    pruefe(
        mit and min(xs) < 0.01 and 30.0 < max(xs) < 40.0 - 0.5,
        f"{titel}: Fase von x {min(xs, default=-1):.2f} bis {max(xs, default=-1):.2f}",
    )
    schlimmste = 0.0
    for p, lage in mit[:3] + mit[-6:]:
        e, t, *_rest = e3._geometrie(vorn, p)
        schlimmste = max(schlimmste, keilpruefung(lage, e, t, lage.schenkel, werte.fraeser, stufe))
        im_block = fraeserkoerper(lage, werte.fraeser).common(block).Volume
        pruefe(im_block < 1e-6, f"{titel}: schneidet in den Block ({im_block:.2e} mm³)")
    pruefe(schlimmste < 0.03, f"{titel}: außerhalb der Fase {schlimmste:.3f} mm")
    print(ascii(f"{titel}: Fase x {min(xs):.2f} .. {max(xs):.2f}, schlimmstens {schlimmste:.3f}"))

# --- Schaft, Halter, Spindel gegen OpenCascade --------------------------------------------------
from camaddon import halter as hl  # noqa: E402

halter = hl.vorschlag(10.0)
aufbau = e3.aufbau(halter, 5.0, 12.0, KEGEL)
pruefe(
    aufbau.stuecke[0] == (KEGEL.schneidhoehe, 12.0, 5.0, 5.0)
    and abs(aufbau.kopf - 12.0 - halter.laenge) < 1e-9
    and abs(aufbau.stuecke[-1][1] - aufbau.kopf) < 1e-9,
    f"Aufbau {aufbau}",
)
mit_aufbau = e3.Werte3D(KEGEL, 0.5, e3.FUENF, sicher=40.0, tisch=0.0, aufbau=aufbau)
grob = e3.wolke(teil, kanten, 300.0, e3.GROB, e3.RASTER_GROB)
weit_unten = Part.makePlane(800, 800, V(-400, -400, -500))


def drehkoerper(spitze, achse, stuecke):
    a = V(*achse)
    teile = []
    for h0, h1, r0, r1 in stuecke:
        p = V(*(spitze + h0 * achse))
        if abs(r0 - r1) > 1e-9:
            teile.append(Part.makeCone(r0, r1, h1 - h0, p, a))
        else:
            teile.append(Part.makeCylinder(r0, h1 - h0, p, a))
    return Part.makeCompound(teile)


rng = np.random.default_rng(7)
falsch, nah_dran = [], 0
for _ in range(60):
    spitze = rng.uniform((-20.0, -20.0, 2.0), (80.0, 60.0, 45.0))
    achse = rng.normal(size=3)
    achse[2] = abs(achse[2])
    achse /= np.linalg.norm(achse)
    koerper = drehkoerper(spitze, achse, aufbau.stuecke)
    drin = any(koerper.common(teil).Volume > 1e-6 for koerper in koerper.Solids)
    abstand = 0.0 if drin else koerper.distToShape(teil)[0]
    tief = e3._aufbau_im_teil(spitze, achse, mit_aufbau, grob)
    nah_dran += abstand < e3.ABSTAND
    if (abstand > e3.ABSTAND + 0.1 and tief > 0) or (abstand < e3.ABSTAND - 0.1 and tief <= 0):
        falsch.append((np.round(spitze, 1), np.round(achse, 2), round(abstand, 2), round(tief, 2)))
    # Der Tisch (z 0): der tiefste Punkt von Schneide, Schaft, Halter und Spindel.
    kegel = [
        (0.0, KEGEL.kegelhoehe, KEGEL.spitze, KEGEL.radius),
        (KEGEL.kegelhoehe, KEGEL.schneidhoehe, KEGEL.radius, KEGEL.radius),
    ]
    kopf = [(aufbau.kopf, aufbau.kopf + e3.KOPF_LAENGE, e3.KOPF_RADIUS, e3.KOPF_RADIUS)]
    ganz = drehkoerper(spitze, achse, kegel + list(aufbau.stuecke) + kopf)
    tiefste = -500.0 + ganz.distToShape(weit_unten)[0]
    soll = max(0.0, e3.ABSTAND - tiefste)
    if abs(e3._tisch(spitze, achse, mit_aufbau) - soll) > 1e-3:
        falsch.append(("Tisch", np.round(achse, 2), round(soll, 3)))
pruefe(not falsch, f"Aufbau gegen OpenCascade: {falsch[:4]}")
pruefe(0 < nah_dran < 60, f"Stichproben am Teil: {nah_dran}")
print(ascii(f"Aufbau: 60 Stichproben, {nah_dran} am Teil, {len(falsch)} falsch"))
# Mit Halter und Spindel: unten an den senkrechten Kanten kippt der Kegel nach oben (waagrecht
# käme die Spindel dem Tisch zu nah) – die Fase bleibt dieselbe, das Teil heil.
mit_halter = durchgehen(mit_aufbau, "5 Achsen Kegel mit Halter", grob=grob)
pruefe(mit_halter[2] > 0, "unten an den senkrechten Kanten nicht gekippt?")

# --- Die Operation im Job ----------------------------------------------------------------------
import pathlib  # noqa: E402
import tempfile  # noqa: E402

import Path.Main.Job as PathJob  # noqa: E402
from Path.Tool.camassets import user_asset_store  # noqa: E402

from camaddon import abfahren as ab  # noqa: E402
from camaddon import beispielmaschine  # noqa: E402
from camaddon import entgraten3d as e3op  # noqa: E402
from camaddon import job_schnittwerte as js  # noqa: E402
from camaddon import kollision as kb  # noqa: E402
from camaddon import postprozessor as pp  # noqa: E402
from camaddon import reichweite as rw  # noqa: E402
from camaddon import schwenken as sw  # noqa: E402
from camaddon import simultan_operation as so  # noqa: E402
from camaddon import uebergabe_werkzeuge as ue  # noqa: E402
from camaddon import werkzeuge as wz  # noqa: E402

fase = wz.Werkzeug(
    nummer=3,
    name="Fase 90",
    art=wz.FASENFRAESER,
    durchmesser=10.0,
    schneiden=2,
    schneidenlaenge=5.0,
    spitzenwinkel=90.0,
    spitzen_d=0.5,
    schneidstoff=wz.VHM,
)
fase.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=100.0, fz=0.05)]
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
bibliothek = wz.Bibliothek([wz.standardwerkzeug(), fase])
bibliothek.speichern()  # die Operation liest Halter und Länge daraus (wie die Kollision)
ue.uebergeben(bibliothek)
doc = FreeCAD.newDocument("Entgraten3D")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
tc = js.controller_ohne_transaktion(doc, job, fase, fase.schnittwerte[wz.ALLE][0])
doc.recompute()
op = e3op.lege_an(job, tc, flaechen=namen)
doc.recompute()
pruefe(op.Label == "Entgraten 3D T3", f"Name {op.Label}")
# Mit Halter und Spindel bleiben unten am Tisch zwei Kanten ohne Fase (13 statt 15).
pruefe(op.Kanten >= 12 and len(op.Werkzeugachsen) == len(op.Path.Commands), f"Kanten {op.Kanten}")
pruefe(so.ist_simultan(op) and js.operationsart(op) == "entgraten3d", "nicht simultan / Art")
asm, ma = beispielmaschine.fuenfachs_tisch_tisch()
pruefung = rw.Pruefung(asm, ma)
maschine = sw.Maschine(
    pruefung, pruefung.werkzeugaufnahme(tc.ToolNumber), rw.einspannung(tc, None), rw.nullpunkt(job)
)
saetze = so.befehle(op, maschine)
pruefe(any("A" in b.Parameters for b in saetze if b.Name == "G1"), "keine Rundachse im Programm")
ergebnis = pruefung.pruefe_job(job)
pruefe(
    not any("Entgraten 3D" in str(h) for h in ergebnis.hinweise),
    f"auf der Maschine: {[str(h) for h in ergebnis.hinweise]}",
)
mit = pp.abschnitte(job, maschine)
info5 = pp.maschineninfo_dokument(asm.Document)
for kennung in pp.STEUERUNGEN:
    for aenderung in ({}, {"tcpm": True}):
        s = pp.steuerung(kennung, aenderung)
        befunde, _saetze = pp.nachlesen(pp.programm(mit, s, info5, "E"), s, info5)
        pruefe(not befunde, f"{kennung} {aenderung}: {[(b.art, b.satz) for b in befunde[:3]]}")
# Die Kollision an der Maschine: nichts berührt, nichts kommt näher als 1 mm – Schaft, Halter und
# Spindel inbegriffen, auch beim Anfahren und zwischen den Kanten.
fahrt = ab.abfahrt(pruefung, job, rw.nullpunkt(job), bibliothek)
kollision = kb.kollision(fahrt, job, rw.nullpunkt(job), bibliothek)
pruefe(not kollision.befunde, f"Kollision: {[b.text() for b in kollision.befunde[:3]]}")
print(ascii(f"Job: {op.Kanten} Kanten, {len(fahrt.stationen)} Stationen, Kollision frei"))
# Mit 3 Achsen: die Achse senkrecht, keine Simultan-Operation.
op.FuenfAchsen = False
doc.recompute()
pruefe(
    op.Kanten >= 8
    and not so.ist_simultan(op)
    and all(abs(a.z - 1.0) < 1e-9 for a in op.Werkzeugachsen if a.Length > 0),
    f"3 Achsen: {op.Kanten} Kanten",
)
FreeCAD.closeDocument(doc.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
