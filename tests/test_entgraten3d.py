# SPDX-License-Identifier: LGPL-2.1-or-later
# Entgraten in 3D (W-015 S5, entgrat3d_bahn): ein Klotz 60 × 40 × 20 mit 30°-Schräge, einer Nut
# 6 mm breit und einer Bohrung Ø 10. Je Weg (5 Achsen mit Fasenfräser 90°, 5 Achsen mit
# Schaftfräser, 3 Achsen mit Fasenfräser) für jede Stelle:
# - die Geometrie: 5 Achsen – die Achse senkrecht zur Kante, die Fase symmetrisch, ihre Enden auf
#   dem Kegelmantel bzw. in der Stirn; 3 Achsen – die Achse senkrecht, die Breite auf der Fläche,
#   die nach oben schaut;
# - unabhängig mit OpenCascade: Der Fräser (0,02 mm längs der Achse zurück) schneidet das Teil
#   nur im Keil an der Kante (auf der Seite der Fase, nahe der Kante) – sonst beschädigte er es.
# Die Nut ist schmaler als der Kegel: Dort fast es nur, wo es passt, und sagt den Rest („eng“).
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


def keilpruefung(lage, e, t, schenkel, fraeser, form):
    """Schneidet der Fräser (0,02 mm zurück) das Teil nur im Keil an der Kante? (größte
    Abweichung in mm, 0: ja)"""
    a = FreeCAD.Vector(*lage.achse)
    zurueck = 0.02 / (math.sin(fraeser.halbwinkel) if fraeser.kegel else 1.0)
    spitze = FreeCAD.Vector(*(lage.spitze + zurueck * lage.achse))
    if fraeser.kegel:
        koerper = Part.makeCone(fraeser.spitze, fraeser.radius, fraeser.kegelhoehe, spitze, a)
        koerper = koerper.fuse(
            Part.makeCylinder(fraeser.radius, e3.SCHAFT, spitze + a * fraeser.kegelhoehe, a)
        )
    else:
        koerper = Part.makeCylinder(fraeser.radius, fraeser.hoehe, spitze, a)
    gemeinsam = koerper.common(form)
    if gemeinsam.isNull() or gemeinsam.Volume < 1e-9:
        return 0.0
    punkte, _d = gemeinsam.tessellate(0.01)
    x = np.array([[p.x, p.y, p.z] for p in punkte] + [[v.X, v.Y, v.Z] for v in gemeinsam.Vertexes])
    ueber = -((x - e) @ lage.normale + lage.tiefe)  # > 0: auf der Seite des Teils
    quer = (x - e) - np.outer((x - e) @ t, t)
    weit = np.linalg.norm(quer, axis=1) - (max(schenkel) + e3.STREIFEN)
    return float(max(np.max(ueber), np.max(weit), 0.0))


def durchgehen(werte, titel, stichproben=6):
    """Je Kante einige Stellen: Geometrie und Keil; gibt (Kanten mit Fase, eng in mm)."""
    wolke = e3.wolke(teil, kanten, werte.fraeser.hoehe + werte.fraeser.radius)
    gefast, eng = 0, 0.0
    schlimmste = 0.0
    for k in kanten:
        stellen = e3._stellen_der_kante(k, werte, wolke)
        mit = [(p, lage) for p, lage, _g in stellen if lage is not None]
        schritt = k.kante.Length / max(len(stellen) - 1, 1)
        eng += schritt * sum(1 for _p, lage, g in stellen if g == e3.ENG)
        if mit:
            gefast += 1
        for p, lage in mit[:: max(1, len(mit) // stichproben)]:
            e, t, n1, n2, u1, u2 = e3._geometrie(k, p)
            a = lage.achse
            if werte.art == e3.FUENF:
                pruefe(
                    abs(float(a @ t)) < 1e-6, f"{titel} {k.name}: Achse nicht ⟂ Kante ({a @ t:.2e})"
                )
                pruefe(
                    abs(lage.schenkel[0] - werte.breite) < 1e-9
                    and abs(lage.schenkel[1] - werte.breite) < 1e-9,
                    f"{titel} {k.name}: Schenkel {lage.schenkel}",
                )
                q = [e + lage.schenkel[0] * u1, e + lage.schenkel[1] * u2]
                for qi in q:
                    rel = qi - lage.spitze
                    h = float(rel @ a)
                    radial = float(np.linalg.norm(rel - h * a))
                    if werte.fraeser.kegel:
                        soll = float(werte.fraeser.radius_bei(np.array([h]))[0])
                        pruefe(
                            abs(radial - soll) < 1e-6,
                            f"{titel} {k.name}: Fase nicht am Mantel {radial} {soll}",
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
            f"{titel}: {gefast} Kanten mit Fase, eng {eng:.0f} mm, schlimmstens {schlimmste:.3f} mm"
        )
    )
    return gefast, eng


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
pruefe(set(bahn.gruende) <= {e3.ENG, e3.STEIL, e3.KEINE_STELLUNG, e3.ANFAHRT}, f"{bahn.gruende}")
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

# --- Die Operation im Job ----------------------------------------------------------------------
import pathlib  # noqa: E402
import tempfile  # noqa: E402

import Path.Main.Job as PathJob  # noqa: E402
from Path.Tool.camassets import user_asset_store  # noqa: E402

from camaddon import beispielmaschine  # noqa: E402
from camaddon import entgraten3d as e3op  # noqa: E402
from camaddon import job_schnittwerte as js  # noqa: E402
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
ue.uebergeben(wz.Bibliothek([wz.standardwerkzeug(), fase]))
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
pruefe(op.Kanten >= 15 and len(op.Werkzeugachsen) == len(op.Path.Commands), f"Kanten {op.Kanten}")
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
