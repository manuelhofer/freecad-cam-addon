# Prüft das Erkennen einer Wendelnut und die Abstände der Bahnen quer über sie (vierachs_wendel,
# W-030; Manuel, 2026-10-18: „Ja, vorgewählt bei Wendelnut“). An einer gerechneten Hüllfläche
# Ø 60: eine rechtsgängige Nut mit 60 mm Steigung wird erkannt (Steigung auf 0,2 mm, ein Gang,
# Breite und Tiefe), eine zweigängige linksgängige mit 40 mm Steigung als zwei Gänge, eine Ringnut
# und die glatte Welle nicht. Quer über eine runde Nut R 11 mit der Kugel R 6 (Schnitt längs, wie
# an Manuels Teil): Die Bahnen liegen so, dass zwischen je zwei höchstens die Kammhöhe stehen
# bleibt – in der Rundung enger als auf einer Ebene (zwischen 20 und 40 Bahnen bei 0,02 mm), von
# Kante zu Kante; Bahnen, die nur über die Kante rollen, gibt es nicht.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402, F401 – wie in jeder Prüfdatei: freecadcmd führt sie sonst nicht aus
import numpy as np  # noqa: E402

from camaddon import vierachs_huelle as vh  # noqa: E402
from camaddon import vierachs_wendel as vw  # noqa: E402

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)
        print("FEHLER:", text)


def huelle(steigung, gaenge=1, a0=10.0, halb=4.0, ring=False):
    """Strahlen von der Achse an einer Welle R 30 (a −80 … 0) mit runden Nuten R `halb`."""
    a = vh.raster_a(-79.75, -0.25, vw.SCHRITT_A)
    phi = vh.raster_phi(vw.SCHRITT_PHI)
    r = np.full((len(a), len(phi)), 30.0)
    for g in range(gaenge):
        for j, p in enumerate(np.degrees(phi)):
            mitte = a0 + g * abs(steigung or 40) / gaenge + (0 if ring else steigung * p / 360.0)
            teilung = abs(steigung) if steigung else 1e9
            d = (a - mitte + 0.5 * teilung) % teilung - 0.5 * teilung if steigung else a - mitte
            drin = np.abs(d) < halb
            r[drin, j] = np.minimum(r[drin, j], 30.0 - np.sqrt(halb * halb - d[drin] ** 2))
    return vh.Huelle(a, phi, r)


w = vw.aus_huelle(huelle(60.0))
pruefe(w is not None and abs(w.steigung - 60.0) < 0.2 and w.gaenge == 1, f"eingängig: {w}")
if w is not None:
    pruefe(7.0 < w.breite < 9.0 and 3.5 < w.tiefe < 4.5, f"Breite/Tiefe: {w}")
    pruefe(abs(w.mitte_bei(-40.0, 0.0) - (10.0 - 60.0)) < 0.5, f"Mitte: {w.mitte_bei(-40.0)}")
w2 = vw.aus_huelle(huelle(-40.0, gaenge=2))
pruefe(w2 is not None and abs(w2.steigung + 40.0) < 0.2 and w2.gaenge == 2, f"zweigängig: {w2}")
pruefe(vw.aus_huelle(huelle(0.0, ring=True)) is None, "Ringnut als Wendel erkannt")
glatt = huelle(60.0)
glatt.r[:] = 30.0
pruefe(vw.aus_huelle(glatt) is None, "glatte Welle als Wendel erkannt")

# Quer über die runde Nut R 11 (Mitte auf dem Umfang R 40), Kugel R 6, im Schnitt längs.
u = np.arange(-17.75, 17.76, vw.PROFIL_SCHRITT)
mitte_r = np.empty_like(u)
for i, x in enumerate(u):
    if abs(x) <= 5.0:  # in der Rundung: die Mitte auf dem Kreis R 5 um die Nutmitte
        mitte_r[i] = 40.0 - math.sqrt(25.0 - x * x)
    elif abs(x) < 11.0:  # über die Kante bei ±11 gerollt
        mitte_r[i] = 40.0 + math.sqrt(max(36.0 - (11.0 - abs(x)) ** 2, 0.0))
    else:  # auf dem Umfang daneben
        mitte_r[i] = 46.0
spitze = mitte_r - 6.0
v = vw.versaetze(u, spitze, 6.0, 0.02, True, 0.98, 40.0)
print(f"{len(v)} Bahnen, Abstände {np.round(np.diff(v), 2).tolist()}")
pruefe(20 <= len(v) <= 40, f"{len(v)} Bahnen quer über die Nut")
pruefe(v and v[0] < -4.5 and v[-1] > 4.5, f"nicht von Kante zu Kante: {v[:1]} … {v[-1:]}")
pruefe(v and v[0] > -8.0 and v[-1] < 8.0, f"Bahnen, die nur über die Kante rollen: {v[0]}, {v[-1]}")
mitten = np.column_stack([u, mitte_r])
stellen = [int(round((x - u[0]) / vw.PROFIL_SCHRITT)) for x in v]
hoechstens = max(vw.kamm(mitten, i, j, 6.0) for i, j in zip(stellen, stellen[1:], strict=False))
pruefe(hoechstens <= 0.0201, f"Kamm zwischen zwei Bahnen bis {hoechstens:.4f}")
# Ohne Kugel gleich weit auseinander, mit der Schrittweite.
v_flach = vw.versaetze(u, spitze, 6.0, 0.0, False, 2.0, 40.0)
pruefe(len(v_flach) > 2 and max(np.diff(v_flach)) <= 2.0 + 1e-9, f"flach: {np.diff(v_flach)}")

if fehler:
    print(f"{len(fehler)} Fehler")
    sys.exit(1)
print("OK test_vierachs_wendel")
