# Prüft die Kurvennut im Mantel (vierachs_planbahn.kurvennuten, _kurvennut_punkte; Manuel,
# 2026-11-15, nach einem Bild aus dem Discord: ein Rohr mit einer gewundenen, durchgehenden Nut –
# „mit einer fräser fröse heist wenn die nur 12 ist .. ein 12 fräser mittig fertrig .. udn wenn
# man nen 8 fräser nimmt muss er das ja als kontur fahren können“).
# Rohr Ø 60 / Ø 50 × 120 längs X; die Nut 12 breit, ihre Mitte läuft über 200° des Umfangs weich
# von x 45 nach x 85, durch die Wand. Geschnitten ist sie im Testteil mit dem Fräser selbst
# (radiale Zylinder Ø 12 längs der Mitte) – so ist „Ø 12 mittig“ genau die fertige Nut.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import fraeserform as ff
from camaddon import spindel as sp
from camaddon import sprache
from camaddon import vierachs_planbahn as vp

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
V = FreeCAD.Vector
RA, RI, LANG = 30.0, 25.0, 120.0
BREITE, WINKEL, A0, A1 = 12.0, 200.0, 45.0, 85.0
LAENGS, RADIAL = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)


def mitte(phi_grad):
    return A0 + (A1 - A0) * 0.5 * (1.0 - math.cos(math.pi * phi_grad / WINKEL))


def strahl(phi_grad):
    p = math.radians(phi_grad)
    return V(0, math.cos(p), math.sin(p))


def quer(phi_grad):
    p = math.radians(phi_grad)
    return V(0, -math.sin(p), math.cos(p))


def fraeser(a, r, phi_grad, q, radius, lang=20.0):
    """Der Fräser als Zylinder: die Spitze bei a längs, r hoch auf seiner Achse, q quer."""
    fuss = V(a, 0, 0) + strahl(phi_grad) * r + quer(phi_grad) * q
    return Part.makeCylinder(radius, lang, fuss, strahl(phi_grad))


rohr = Part.makeCylinder(RA, LANG, V(), V(1, 0, 0)).cut(
    Part.makeCylinder(RI, LANG, V(), V(1, 0, 0))
)
schnitte = [
    fraeser(mitte(f), RI - 3.0, f, 0.0, BREITE / 2.0, 11.0) for f in np.linspace(0.0, WINKEL, 101)
]
teil = rohr.cut(schnitte[0].fuse(schnitte[1:]))
pruefe(teil.isValid() and len(teil.Solids) == 1, "das Testteil ist kein gültiger Körper")
alle = [f"Face{i + 1}" for i in range(len(teil.Faces))]
print(f"Testteil: {len(teil.Faces)} Flächen, {rohr.Volume - teil.Volume:.0f} mm3 Nut")

# --- Erkennen: aus allen Flächen des Teils nur die Wände der Nut ---------------------------------
nuten = vp.kurvennuten(teil, LAENGS, RADIAL, alle)
pruefe(len(nuten) == 1, f"Kurvennuten: {len(nuten)}")
if not nuten:
    raise AssertionError("\n".join(fehler))
nut = nuten[0]
m = np.array(nut.mitte)
abweichung = max(abs(a - mitte(f)) for a, f in nut.mitte)
print(ascii(f"Kurvennut: {nut.breite:.3f} breit, von {m[0, 1]:.1f} bis {m[-1, 1]:.1f} Grad, "
            f"{len(nut.mitte)} Stellen, Mitte bis {abweichung:.3f} mm daneben, durch {nut.durch}, "
            f"Spitze bis r {nut.radius}, {len(nut.namen)} Wandflächen"))  # fmt: skip
pruefe(abs(nut.breite - BREITE) < 0.1, f"Breite {nut.breite}")
pruefe(abweichung < 0.15, f"Mittellinie {abweichung:.3f} mm neben der Nut")
pruefe(
    abs(min(m[0, 1], m[-1, 1])) < 1.0 and abs(max(m[0, 1], m[-1, 1]) - WINKEL) < 1.0,
    f"Enden bei {m[0, 1]:.2f} und {m[-1, 1]:.2f} Grad",
)
pruefe(nut.durch and abs(nut.radius - (RI - vp.DURCH_TIEFER)) < 1e-6, f"Tiefe: {nut.radius}")
pruefe(abs(nut.r_aussen - RA) < 1e-6 and len(nut.namen) > 50, "Rand und Wände")
# Die Mantelflächen des Rohrs und die Stirnseiten allein sind keine Nut; mantelnuten() bringt sie mit.
ohne = [n for n in alle if n not in nut.namen]
pruefe(not vp.kurvennuten(teil, LAENGS, RADIAL, ohne), "Mantel und Stirn gelten als Kurvennut")
pruefe(vp.mantelnuten(teil, LAENGS, RADIAL, list(nut.namen)) == nuten, "mantelnuten() ohne sie")
# Ein Klick auf irgendeine Wand bringt die ganze Nut mit (201 Streifen klickt niemand einzeln).
eine = vp.kurvennuten(teil, LAENGS, RADIAL, [nut.namen[40]])
pruefe(
    len(eine) == 1 and set(eine[0].namen) == set(nut.namen), "eine Wand bringt die Nut nicht mit"
)


def werte(d, **mehr):
    grund = {"form": ff.scheibe(d / 2.0), "stange_radius": RA, "zustellung": 0.5 * d,
             "zeilenabstand": 0.25 * d, "aufmass": 0.0, "a_stange_vorne": LANG, "a_futter": -20.0}  # fmt: skip
    grund.update(mehr)
    return vp.Planwerte(**grund)


def im_teil(p, radius):
    """So viel nimmt der Fräser an der Stelle `p` vom fertigen Teil weg (mm³)."""
    return teil.common(fraeser(p.a, p.r, p.phi, p.q, radius)).Volume


# --- Fräser so breit wie die Nut: mittig, vorwärts und rückwärts, fertig -------------------------
punkte, lagen, fahrten = vp._kurvennut_punkte(nut, werte(12.0), RA, RA + 5.0)
schnitt = [p for p in punkte if not p.eilgang]
print(
    f"D12: {len(punkte)} Punkte, {lagen} Lagen, {fahrten} Fahrten, tiefste Spitze r {min(p.r for p in schnitt):.2f}"
)
pruefe(all(abs(p.q) < 1e-9 for p in punkte), "Ø 12: Querachse bewegt sich")
pruefe(max(abs(p.a - mitte(p.phi)) for p in schnitt) < 0.15, "Ø 12: nicht auf der Mittellinie")
pruefe(abs(min(p.r for p in schnitt) - (RI - vp.DURCH_TIEFER)) < 1e-6, "Ø 12: nicht durch")
wenden = sum(
    1
    for a, b, c in zip(schnitt, schnitt[1:], schnitt[2:], strict=False)
    if (b.phi - a.phi) * (c.phi - b.phi) < 0
)
pruefe(fahrten >= 2 and wenden >= 1, f"Ø 12: {fahrten} Fahrten, {wenden} Wenden")
unten = [p for p in schnitt if p.r < RI - vp.DURCH_TIEFER + 1e-6]
pruefe(
    abs(max(p.phi for p in unten) - min(p.phi for p in unten) - WINKEL) < 1.5,
    "Ø 12: unten nicht durch die ganze Nut",
)
weg12 = max(im_teil(p, 6.0) for p in unten[:: max(1, len(unten) // 12)])
pruefe(weg12 < 0.5, f"Ø 12: nimmt {weg12:.3f} mm3 vom fertigen Teil")

# --- Kleinerer Fräser: die Kontur an beiden Wänden, im Gleichlauf --------------------------------
punkte8, lagen8, fahrten8 = vp._kurvennut_punkte(nut, werte(8.0), RA, RA + 5.0)
kontur = [p for p in punkte8 if not p.eilgang and abs(p.q) > 1e-6]
print(f"D8: {len(punkte8)} Punkte, {fahrten8} Fahrten, davon {len(kontur)} Punkte an den Wänden")
pruefe(len(kontur) > 100, f"Ø 8: keine Kontur ({len(kontur)} Punkte)")
# Die letzte Runde liegt an den Wänden: nichts im Teil, und die Flanke liegt an (≤ 0,05 mm).
letzte = [p for p in punkte8 if not p.eilgang and abs(p.r - nut.radius) < 1e-6][
    -len(nut.mitte) * 2 :
]
stichprobe = [p for p in letzte if abs(p.q) > 1.0][:: max(1, len(letzte) // 14)]
weg8 = max(im_teil(p, 4.0) for p in stichprobe)
abstand8 = max(teil.distToShape(fraeser(p.a, p.r, p.phi, p.q, 4.0))[0] for p in stichprobe)
print(f"D8 an der Wand: nimmt bis {weg8:.3f} mm3 vom Teil, Abstand zur Wand bis {abstand8:.3f} mm")
pruefe(weg8 < 0.5, f"Ø 8: nimmt {weg8:.3f} mm3 vom fertigen Teil")
pruefe(abstand8 < 0.06, f"Ø 8: bleibt {abstand8:.3f} mm vor der Wand")
# An beiden Wänden: links und rechts der Mittellinie.
seiten = {1 if p.a > mitte(p.phi) else -1 for p in letzte if abs(p.a - mitte(p.phi)) > 0.5}
pruefe(seiten == {1, -1}, f"Ø 8: nur eine Wand ({seiten})")


def ort(p):
    return V(p.a, 0, 0) + strahl(p.phi) * p.r + quer(p.phi) * p.q


gleich = []
for a, b in list(zip(letzte, letzte[1:], strict=False))[5::25]:
    fahrt = ort(b) - ort(a)
    if fahrt.Length < 1e-6 or abs(a.q) < 1.0:
        continue
    zur_wand = ort(a) - (V(mitte(a.phi), 0, 0) + strahl(a.phi) * a.r)
    achse = strahl(a.phi) * -1.0  # vom Halter zur Spitze
    gleich.append(sp.ist_gleichlauf(tuple(achse), tuple(fahrt), tuple(zur_wand)))
pruefe(len(gleich) >= 3 and all(gleich), f"Ø 8: Gleichlauf {gleich}")
gegen = vp._kurvennut_punkte(nut, werte(8.0, gleichlauf=False), RA, RA + 5.0)[0]
pruefe([p.q for p in gegen] != [p.q for p in punkte8], "Ø 8: Gegenlauf fährt dieselbe Runde")

# --- Vorarbeiten mit Aufmaß, dann Leerdurchfahrten (Manuel, 2026-11-15: „vorarbeiten auf 0.3
# (einstellbar wenn der fräser ausreichend platz lässt) und leer durchfahrten je arbeitsgang“) ---
vor = vp._kurvennut_punkte(nut, werte(8.0, aufmass=0.3), RA, RA + 5.0)[0]
vor_letzte = [p for p in vor if not p.eilgang and abs(p.r - nut.radius) < 1e-6][
    -len(nut.mitte) * 2 :
]
an_wand = [p for p in vor_letzte if abs(p.q) > 1e-6 and abs(p.a - mitte(p.phi)) > 0.5]
stichprobe = an_wand[:: max(1, len(an_wand) // 14)]
luft = min(teil.distToShape(fraeser(p.a, p.r, p.phi, p.q, 4.0))[0] for p in stichprobe)
print(f"D8 mit 0,3 Aufmaß: kleinster Abstand zur Wand {luft:.3f} mm")
pruefe(abs(luft - 0.3) < 0.06, f"Aufmaß 0,3: {luft:.3f} mm zur Wand")
# Ø 12 in der Nut 12 lässt keinen Platz für ein Aufmaß an den Wänden: Satz, keine Bahn.
try:
    vp._kurvennut_punkte(nut, werte(12.0, aufmass=0.3), RA, RA + 5.0)
    pruefe(False, "Ø 12 mit Aufmaß 0,3 in der Nut 12")
except ValueError as e:
    pruefe("Aufmaß" in str(e), f"Ø 12 mit Aufmaß: {e}")
# Leerdurchfahrten: der letzte Umlauf noch einmal, Satz für Satz derselbe, ohne Zustellung.
ohne, _l, f_ohne = vp._kurvennut_punkte(nut, werte(8.0), RA, RA + 5.0)
mit, _l, f_mit = vp._kurvennut_punkte(nut, werte(8.0, leerfahrten=2), RA, RA + 5.0)
runde = len([p for p in ohne if not p.eilgang and abs(p.q) > 1e-9]) // 2  # zwei Kontur-Runden
dazu = len(mit) - len(ohne)
print(f"Leerdurchfahrten: {f_ohne} → {f_mit} Fahrten, {dazu} Punkte mehr")
pruefe(f_mit == f_ohne + 2 and dazu > 0, f"Leerfahrten: {f_ohne} → {f_mit}, {dazu} Punkte")
pruefe(min(p.r for p in mit if not p.eilgang) >= nut.radius - 1e-9, "Leerfahrt stellt zu")
mit12, _l, f12 = vp._kurvennut_punkte(nut, werte(12.0, leerfahrten=1), RA, RA + 5.0)
pruefe(f12 == 3 and all(abs(p.q) < 1e-9 for p in mit12), f"Ø 12 mit Leerfahrt: {f12} Fahrten")

# --- Zu breiter Fräser ---------------------------------------------------------------------------
try:
    vp._kurvennut_punkte(nut, werte(14.0), RA, RA + 5.0)
    pruefe(False, "Ø 14 passt in die Nut 12")
except ValueError as e:
    pruefe("breiter" in str(e), f"Ø 14: {e}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
