# Die Zielzeit (Manuel, 2026-10-02): erst das Volumen, das weg muss, dann die Zeit, die ein
# Fräser mit seinen Werten dafür mindestens braucht – mit dem ap, das die Stelle hergibt. Seine
# zwei Beispiele: 1000 × 1000, 5 mm ab – viel Volumen, aber nur ap 5 (ein Fünftel des
# Zeitspanvolumens); 100 × 100, 25 mm ab – der Fräser voll genutzt. Dazu Lagen, der Rest in
# Ecken, die enger sind als der Fräser, und der Vergleich der Fräser einer Werkzeugkiste
# (werkzeuge.testkiste) – und die Zielzeit der Maßstabsteile des Prüfstands neben ihren
# Bestmarken.
import json
import math
import os
import sys
import time

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import werkzeuge as wz
from camaddon import zielzeit as zz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nah(a, b, anteil=0.01):
    return abs(a - b) <= anteil * abs(b)


V = FreeCAD.Vector
standard = wz.standardwerkzeug()
schruppen = next(e for e in standard.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
AE, AP, VF = zz.werte(standard, schruppen)
pruefe(nah(VF, 901.96, 0.001) and AE == 1.5 and AP == 25.0, f"Standardwerte: {AE} {AP} {VF}")

# --- Manuels Beispiele ------------------------------------------------------------------------
# 1000 × 1000, 5 mm ab: 5 dm³, eine Lage mit ap 5 – 1000² ÷ (1,5 · 902) = 739 min.
platte = Part.makeBox(1000, 1000, 20)
beginn = time.time()
m = zz.material(platte, (0, 1000, 0, 1000), 25.0)
z = zz.ziel(m, 6.0, AE, AP, VF)
dauer = time.time() - beginn
pruefe(nah(m.volumen, 5e6), f"1000 × 1000: {m.volumen / 1e6:.3f} dm³")
pruefe(nah(z.zeit, 1e6 / (AE * VF)), f"1000 × 1000: {z.zeit:.1f} min")
pruefe(nah(z.ap_wirksam, 5.0) and z.rest < 1e-6 * m.volumen, f"ap {z.ap_wirksam}, Rest {z.rest}")
pruefe(nah(z.zeitspanvolumen, z.zeitspanvolumen_voll / 5), f"Q {z.zeitspanvolumen:.2f} cm³/min")
pruefe(dauer < 20.0, f"1000 × 1000 gerechnet in {dauer:.1f} s")
print(
    ascii(
        f"1000 x 1000, 5 mm: {m.volumen / 1000:.0f} cm3, Ziel {z.zeit:.0f} min, ap {z.ap_wirksam}"
        f", Q {z.zeitspanvolumen:.1f} von {z.zeitspanvolumen_voll:.1f} cm3/min ({dauer:.1f} s)"
    )
)
# 100 × 100, 25 mm ab: eine Lage mit dem ganzen ap – 100² ÷ (1,5 · 902) = 7,4 min.
klotz = Part.makeBox(100, 100, 20)
m = zz.material(klotz, (0, 100, 0, 100), 45.0)
z = zz.ziel(m, 6.0, AE, AP, VF)
pruefe(nah(m.volumen, 2.5e5) and nah(z.zeit, 1e4 / (AE * VF)), f"100 × 100: {z.zeit:.2f} min")
pruefe(nah(z.zeitspanvolumen, z.zeitspanvolumen_voll), f"100 × 100: Q {z.zeitspanvolumen:.2f}")
# 30 mm ab: zwei Lagen je 15 – doppelt so lange wie 25 mm.
m = zz.material(klotz, (0, 100, 0, 100), 50.0)
z = zz.ziel(m, 6.0, AE, AP, VF)
pruefe(nah(z.zeit, 2e4 / (AE * VF)) and nah(z.ap_wirksam, 15.0), f"30 mm: {z.zeit:.2f} min")
# Nach einer Operation davor (Materialstand, W-012): Über der linken Hälfte steht nur noch bis 30
# – links muss eine Lage weg (10 mm), rechts weiter zwei (30 mm).
links = np.where(m.x[:, None] < 50.0, 30.0, np.inf) + np.zeros((1, len(m.y)))
halb = m.unter(links)
z = zz.ziel(halb, 6.0, AE, AP, VF)
pruefe(nah(halb.volumen, 2e5) and nah(z.zeit, 1.5e4 / (AE * VF)),
       f"nach der Operation davor: {halb.volumen:.0f} mm³, {z.zeit:.2f} min")  # fmt: skip

# --- Der Rest in Ecken, die enger sind als der Fräser ---------------------------------------
# Tasche 40 × 30, Ecken R 6, 15 tief im Block 100 × 60 × 20, Rohteil 1 mm darüber. Ø 12 kommt
# überall hin; Ø 20 lässt in jeder Ecke (R² − π R²/4) − (r² − π r²/4) = 13,7 mm² × 15 stehen;
# Ø 50 kommt nicht hinein – die ganze Tasche bleibt.
rund = Part.Face(
    Part.Wire(
        [
            Part.makeLine(V(36, 15, 5), V(64, 15, 5)),
            Part.makeCircle(6, V(64, 21, 5), V(0, 0, 1), -90, 0),
            Part.makeLine(V(70, 21, 5), V(70, 39, 5)),
            Part.makeCircle(6, V(64, 39, 5), V(0, 0, 1), 0, 90),
            Part.makeLine(V(64, 45, 5), V(36, 45, 5)),
            Part.makeCircle(6, V(36, 39, 5), V(0, 0, 1), 90, 180),
            Part.makeLine(V(30, 39, 5), V(30, 21, 5)),
            Part.makeCircle(6, V(36, 21, 5), V(0, 0, 1), 180, 270),
        ]
    )
)
tasche = Part.makeBox(100, 60, 20).cut(rund.extrude(V(0, 0, 20))).removeSplitter()
m = zz.material(tasche, (0, 100, 0, 60), 21.0, schritt=0.5)
in_der_tasche = (1200 - 4 * (36 - math.pi * 9)) * 15
pruefe(nah(m.volumen, 6000 + in_der_tasche, 0.01), f"Tasche: {m.volumen:.0f} mm³")
z12 = zz.ziel(m, 6.0, AE, AP, VF)
pruefe(z12.rest < 0.002 * m.volumen, f"Ø 12 in der Tasche: Rest {z12.rest:.0f} mm³")
z20 = zz.ziel(m, 10.0, 2.0, 30.0, 649.4)
ecken = 4 * ((100 - math.pi * 25) - (36 - math.pi * 9)) * 15
pruefe(0.7 * ecken < z20.rest < 1.3 * ecken, f"Ø 20: Rest {z20.rest:.0f}, erwartet {ecken:.0f}")
z50 = zz.ziel(m, 25.0, 35.0, 2.0, 954.9)
pruefe(nah(z50.rest, in_der_tasche, 0.05), f"Ø 50: Rest {z50.rest:.0f} von {in_der_tasche:.0f}")
print(
    ascii(
        f"Tasche: Rest Oe 12 {z12.rest:.0f}, Oe 20 {z20.rest:.0f} (Ecken {ecken:.0f}), "
        f"Oe 50 {z50.rest:.0f} mm3"
    )
)

# --- Die Werkzeugkiste ------------------------------------------------------------------------
# Auf der Platte 1000 × 1000 gewinnt der Planfräser Ø 50 (drei Lagen ap 1,67, ae 35) weit vor
# dem Ø 12 (eine Lage ap 5, ae 1,5); in der Tasche räumt Ø 20 vor, Ø 12 macht die Ecken – oder
# Ø 12 allein, je nachdem, was schneller ist; Ø 50 nur oben, die Tasche danach ein kleinerer.
kiste = wz.testkiste()
angebote = zz.vergleiche(zz.material(platte, (0, 1000, 0, 1000), 25.0), kiste)
namen = [a.werkzeug.name for a in angebote]
pruefe(namen[0] == "Plan 50", f"Platte: {namen}")
pruefe(nah(angebote[0].zeit, 1e6 * 3 / (35 * 954.93), 0.01), f"Plan 50: {angebote[0].zeit:.1f}")
for a in angebote:
    print(
        ascii(f"  Platte 1000: {a.werkzeug.name:8} {a.zeit:7.1f} min, ap {a.ziel.ap_wirksam:.2f}")
    )
angebote = zz.vergleiche(m, kiste)
for a in angebote:
    danach = f" + {a.danach.werkzeug.name} {a.danach.zeit:.2f}" if a.danach else ""
    print(ascii(f"  Tasche: {a.werkzeug.name:8} {a.ziel.zeit:6.2f} min{danach}"))
    pruefe(
        a.danach is None or a.danach.werkzeug.durchmesser < a.werkzeug.durchmesser,
        f"Tasche: nach {a.werkzeug.name} ein größerer",
    )
plan = next(a for a in angebote if a.werkzeug.name == "Plan 50")
pruefe(plan.danach is not None, "Tasche: nach dem Planfräser niemand für die Tasche")
pruefe(all(a.zeit >= angebote[0].zeit for a in angebote), f"Tasche: nicht sortiert {angebote[0]}")

# --- Die Maßstabsteile des Prüfstands: Ziel mit dem Standardfräser neben den Bestmarken -----
# Wie im Prüfstand: neben dem Teil bis zur Oberseite des Blocks (z 20) – die Außenwände fährt
# dort keine Strategie; „unter der Oberseite“: ohne den Millimeter darüber (die Strategien in
# der Tasche, den Bohrungen laufen nach dem Planfräsen oben).
DATEI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bestmarken.json")
with open(DATEI, encoding="utf-8") as datei:
    bestmarken = json.load(datei)
zapfen = Part.makeBox(50, 50, 20).fuse(Part.makeCylinder(5, 10, V(25, 25, 20))).removeSplitter()
absatz = Part.makeBox(60, 40, 20).fuse(Part.makeBox(10, 40, 5, V(0, 0, 20))).removeSplitter()
bohrungen = Part.makeBox(100, 60, 20)
bohrungen = bohrungen.cut(Part.makeCylinder(10, 20, V(25, 30, 0)))
bohrungen = bohrungen.cut(Part.makeCylinder(17, 10, V(70, 30, 10))).removeSplitter()
manuel = (
    Part.makeBox(200, 200, 30, V(-100, -100, -30))
    .fuse(Part.makeCylinder(10, 20, V(50, 50, 0)))
    .cut(Part.makeCylinder(22.5, 20, V(-50, -50, -20)))
    .removeSplitter()
)
teile = {
    "zapfen": (zapfen, (-1.0, 51.0, -1.0, 51.0), 30.0, 20.0),
    "absatz": (absatz, (-1.0, 61.0, -1.0, 41.0), 26.0, 20.0),
    "tasche": (tasche, (-1.0, 101.0, -1.0, 61.0), 21.0, 20.0),
    "bohrungen": (bohrungen, (-1.0, 101.0, -1.0, 61.0), 21.0, 20.0),
    "platte": (manuel, (-100.0, 100.0, -100.0, 100.0), 20.0, None),
}
for name, (teil, rohteil, oben, unten) in teile.items():
    m = zz.material(teil, rohteil, oben, unten)
    z = zz.ziel(m, 6.0, AE, AP, VF)
    darunter = zz.ziel(zz.material(teil, rohteil, teil.BoundBox.ZMax, unten), 6.0, AE, AP, VF)
    beste = zz.vergleiche(m, kiste)[0]
    marken = {k.split("/", 1)[1]: v["zeit"] for k, v in bestmarken.items() if k.startswith(name)}
    schnellste = min(marken.items(), key=lambda kv: kv[1]) if marken else ("–", math.nan)
    print(
        ascii(
            f"{name:10} {m.volumen / 1000:7.1f} cm3  Ziel Oe 12 {z.zeit:6.2f} min (ap "
            f"{z.ap_wirksam:4.1f}, Rest {z.rest / 1000:5.2f} cm3, unter der Oberseite "
            f"{darunter.zeit:5.2f})  schnellste Bahn "
            f"{schnellste[1]:6.2f} ({schnellste[0]})  Kiste: {beste.werkzeug.name} "
            f"{beste.zeit:6.2f}" + (f" + {beste.danach.werkzeug.name}" if beste.danach else "")
        )
    )
    pruefe(z.zeit > 0 and z.ap_wirksam <= AP + 1e-9, f"{name}: Ziel {z.zeit}, ap {z.ap_wirksam}")
    # Keine Bahn ist schneller als ihr Ziel – sonst rechnet das Ziel falsch (Grundsatz 0).
    for strategie, minuten in marken.items():
        ziel = min(z.zeit, darunter.zeit)
        print(ascii(f"    {strategie:24} {minuten:6.2f} min = {minuten / ziel:4.2f} x Ziel"))
        pruefe(
            minuten >= 0.98 * ziel or "kontur" in strategie,
            f"{name}/{strategie}: {minuten:.2f} min unter dem Ziel {ziel:.2f}",
        )
z_platte = zz.ziel(zz.material(manuel, teile["platte"][1], 20.0), 6.0, AE, AP, VF)
pruefe(29.5 < z_platte.zeit < 31.5, f"Manuels Platte: Ziel {z_platte.zeit:.1f} min (Spez.: 30,5)")

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK test_zielzeit.py")
