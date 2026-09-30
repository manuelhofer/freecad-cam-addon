# SPDX-License-Identifier: LGPL-2.1-or-later
"""Misst, was die Bahnrechnung kostet – Zeit und Spitzenspeicher je Schritt (W-006, S1).

    FreeCADCmd scripts/bahn_messen.py

Drei Teile: die Welle Ø 60 × 100 aus den Tests, eine Welle mit Absatz und Abflachung, ein
großes Teil Ø 200 × 300. Je Teil: Vernetzen, Hüllfläche des Schaftfräsers, Schruppbahn,
Rest nach dem Schruppen, Schlichtbahn (Kugel), Path-Befehle. Die Tabelle steht am Ende
und in der Datei aus BAHN_MESSEN_AUSGABE (Markdown), sonst nur auf der Konsole. Die
Zahlen gehören in docs/spezifikation_strategien.md, Abschnitt 8 – erst messen, dann
beschleunigen; die Bahn darf sich dabei nicht ändern (goldene Bahnen).
"""

import os
import sys
import time
import tracemalloc

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402
import Part  # noqa: E402

from camaddon import fraeserform as ff  # noqa: E402
from camaddon import vierachs_bahn as vb  # noqa: E402
from camaddon import vierachs_huelle as vh  # noqa: E402
from camaddon import vierachs_schlichten as vs  # noqa: E402

V = FreeCAD.Vector
LAENGS, RADIAL = (0, 0, 1), (1, 0, 0)
R_SCHRUPPEN = 6.0  # Schaftfräser Ø 12
R_SCHLICHTEN = 3.0  # Kugelfräser Ø 6


def welle():
    """Welle Ø 60 × 100 – wie in test_vierachs_bahn."""
    return Part.makeCylinder(30, 100, V(0, 0, -100)), 40.0


def welle_absatz():
    """Welle Ø 60 × 100 mit Absatz auf Ø 40 (40 mm) und einer Abflachung."""
    form = Part.makeCylinder(30, 60, V(0, 0, -60)).fuse(Part.makeCylinder(20, 40, V(0, 0, -100)))
    flach = Part.makeBox(40, 40, 50, V(22, -20, -55))
    return form.cut(flach).removeSplitter(), 40.0


def gross():
    """Großes Teil: Ø 200 × 300 mit Absatz auf Ø 140."""
    form = Part.makeCylinder(100, 180, V(0, 0, -180)).fuse(
        Part.makeCylinder(70, 120, V(0, 0, -300))
    )
    return form.removeSplitter(), 110.0


TEILE = [
    ("Welle Ø 60 × 100", welle),
    ("Welle mit Absatz und Abflachung", welle_absatz),
    ("Groß Ø 200 × 300", gross),
]


def messe(name, funktion, zeilen):
    """Ruft `funktion()` und merkt Zeit (s) und Spitzenspeicher (MB) unter `name`."""
    tracemalloc.start()
    beginn = time.perf_counter()
    ergebnis = funktion()
    dauer = time.perf_counter() - beginn
    _jetzt, spitze = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    zeilen.append((name, dauer, spitze / 1e6))
    return ergebnis


def teil_messen(titel, bauen):
    zeilen = []
    form, stange_radius = bauen()
    a_min = min(v.Point.z for v in form.Vertexes)
    a_futter = a_min - 17.5
    netz = messe("Vernetzen (Schruppen)", lambda: vh.vernetze(form), zeilen)
    netz_fein = messe(
        "Vernetzen (Schlichten)", lambda: vh.vernetze(form, vb.TOLERANZ_SCHLICHTEN), zeilen
    )
    a_werte = vh.raster_a(a_min - R_SCHRUPPEN - 7, 1.0 + R_SCHRUPPEN + 2)
    messe(
        "Hülle Schaftfräser",
        lambda: vh.schaftfraeser(netz, LAENGS, RADIAL, R_SCHRUPPEN, a_werte, vh.raster_phi()),
        zeilen,
    )
    werte = vb.Schruppwerte(
        fraeser_radius=R_SCHRUPPEN,
        stange_radius=stange_radius,
        zustellung=2.0,
        steigung=4.8,
        aufmass=0.3,
        a_stange_vorne=1.0,
        a_futter=a_futter,
    )
    bahn = messe("Schruppbahn", lambda: vb.schruppen(netz, LAENGS, RADIAL, werte), zeilen)
    befehle = messe(
        "Befehle Schruppen", lambda: vb.befehle(bahn, LAENGS, RADIAL, "C", 1, 955.0), zeilen
    )
    rest = messe(
        "Rest nach dem Schruppen",
        lambda: vs.rest_nach([(bahn, R_SCHRUPPEN, 0.3)], stange_radius, a_futter, 1.0),
        zeilen,
    )
    schlicht = vb.Schlichtwerte(
        form=ff.kugel(R_SCHLICHTEN),
        stange_radius=stange_radius,
        schrittweite=0.5,
        aufmass=0.0,
        a_stange_vorne=1.0,
        a_futter=a_futter,
        rest=rest,
        aufmass_schruppen=0.3,
    )
    bahn2 = messe(
        "Schlichtbahn (Kugel Ø 6)",
        lambda: vb.schlichten(netz_fein, LAENGS, RADIAL, schlicht),
        zeilen,
    )
    befehle2 = messe(
        "Befehle Schlichten", lambda: vb.befehle(bahn2, LAENGS, RADIAL, "C", 1, 716.0), zeilen
    )
    return zeilen, {
        "Dreiecke": len(netz.dreiecke),
        "Punkte Schruppen": len(bahn.punkte),
        "Sätze Schruppen": len(befehle),
        "Punkte Schlichten": len(bahn2.punkte),
        "Sätze Schlichten": len(befehle2),
    }


def tabelle(titel, zeilen, zahlen):
    aus = [f"### {titel}", "", "| Schritt | Zeit (s) | Spitze (MB) |", "|---|---:|---:|"]
    for name, dauer, mb in zeilen:
        aus.append(f"| {name} | {dauer:.2f} | {mb:.1f} |")
    aus.append(f"| **zusammen** | **{sum(z[1] for z in zeilen):.2f}** | |")
    aus.append("")
    aus.append("; ".join(f"{k}: {v}" for k, v in zahlen.items()))
    aus.append("")
    return "\n".join(aus)


berichte = [f"## Bahn messen – FreeCAD {'.'.join(FreeCAD.Version()[:3])}", ""]
for titel, bauen in TEILE:
    zeilen, zahlen = teil_messen(titel, bauen)
    berichte.append(tabelle(titel, zeilen, zahlen))
text = "\n".join(berichte)
ausgabe = os.environ.get("BAHN_MESSEN_AUSGABE")
if ausgabe:
    with open(ausgabe, "w", encoding="utf-8") as datei:
        datei.write(text + "\n")
# FreeCADCmd schreibt auf die Konsole nur ASCII – was es nicht kennt, wird ersetzt.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    text = text.encode("ascii", "replace").decode("ascii")
print()
print(text)
if ausgabe:
    print("->", ausgabe)
