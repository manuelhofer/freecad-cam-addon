# Goldene Bahnen (W-006 S1): Für zwei Teile liegt in tests/golden/ fest, welche Bahn die
# Rechnung liefert – Anzahl der Punkte, ein Hash über alle Punkte (auf 1 µm gerundet) und eine
# Stichprobe. Ändert eine Beschleunigung die Bahn, fällt es hier auf; ändert eine Verbesserung
# sie mit Absicht, schreibt GOLDENE_BAHNEN_SCHREIBEN=1 die Dateien neu – und der Verlauf sagt,
# warum. Die Stichprobe nennt den ersten Punkt, der abweicht.
import hashlib
import json
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import fraeserform as ff
from camaddon import vierachs_bahn as vb
from camaddon import vierachs_huelle as vh
from camaddon import vierachs_schlichten as vs

V = FreeCAD.Vector
LAENGS, RADIAL = (0, 0, 1), (1, 0, 0)
ORDNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")
SCHREIBEN = os.environ.get("GOLDENE_BAHNEN_SCHREIBEN") == "1"
STICHPROBE = 97  # jeder so vielte Punkt steht in der Datei
fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def welle():
    return Part.makeCylinder(30, 100, V(0, 0, -100)), 40.0, -117.5


def welle_absatz():
    form = Part.makeCylinder(30, 60, V(0, 0, -60)).fuse(Part.makeCylinder(20, 40, V(0, 0, -100)))
    flach = Part.makeBox(40, 40, 50, V(22, -20, -55))
    return form.cut(flach).removeSplitter(), 40.0, -117.5


def schruppen(bauen):
    form, stange, a_futter = bauen()
    werte = vb.Schruppwerte(
        fraeser_radius=6.0,
        stange_radius=stange,
        zustellung=2.0,
        steigung=4.8,
        aufmass=0.3,
        a_stange_vorne=1.0,
        a_futter=a_futter,
    )
    return vb.schruppen(vh.vernetze(form), LAENGS, RADIAL, werte)


def schlichten(bauen):
    form, stange, a_futter = bauen()
    grob = schruppen(bauen)
    werte = vb.Schlichtwerte(
        form=ff.kugel(3.0),
        stange_radius=stange,
        schrittweite=0.5,
        aufmass=0.0,
        a_stange_vorne=1.0,
        a_futter=a_futter,
        rest=vs.rest_nach([(grob, 6.0, 0.3)], stange, a_futter, 1.0),
        aufmass_schruppen=0.3,
    )
    return vb.schlichten(vh.vernetze(form, vb.TOLERANZ_SCHLICHTEN), LAENGS, RADIAL, werte)


def gerundet(bahn):
    """(n, 4): a, r, φ auf 1 µm bzw. 1 µrad gerundet, Eilgang als 0/1."""
    werte = np.array([(p.a, p.r, p.phi, 1.0 if p.eilgang else 0.0) for p in bahn.punkte])
    return np.round(werte, 6)


def kennzahlen(bahn):
    werte = gerundet(bahn)
    return {
        "anzahl": int(len(werte)),
        "sha256": hashlib.sha256(werte.tobytes()).hexdigest(),
        "stichprobe": werte[::STICHPROBE].tolist(),
    }


def vergleiche(name, bahn):
    pfad = os.path.join(ORDNER, name + ".json")
    ist = kennzahlen(bahn)
    if SCHREIBEN or not os.path.exists(pfad):
        os.makedirs(ORDNER, exist_ok=True)
        with open(pfad, "w", encoding="utf-8") as datei:
            json.dump(ist, datei, indent=0)
        print(f"geschrieben: {pfad} ({ist['anzahl']} Punkte)")
        return
    with open(pfad, encoding="utf-8") as datei:
        soll = json.load(datei)
    if ist["sha256"] == soll["sha256"]:
        return
    grund = f"{name}: {soll['anzahl']} → {ist['anzahl']} Punkte"
    for i, (a, b) in enumerate(zip(soll["stichprobe"], ist["stichprobe"], strict=False)):
        if a != b:
            grund += f"; Stichprobe {i} (Punkt {i * STICHPROBE}): {a} → {b}"
            break
    pruefe(False, grund)


vergleiche("welle_schruppen", schruppen(welle))
vergleiche("welle_absatz_schruppen", schruppen(welle_absatz))
vergleiche("welle_absatz_schlichten", schlichten(welle_absatz))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
