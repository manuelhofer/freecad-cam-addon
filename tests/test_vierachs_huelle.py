# Prüft die Hüllfläche des Schaftfräsers für die 4-Achs-Bearbeitung (W-003 Stufe V3a)
# gegen die Formel: Zylinder, Exzenter und Sechskant längs Z, weit weg von ihren Enden
# (dort zählt nur der Querschnitt), dazu die Welle mit Absatz, die Enden, das sichere
# Raster und eine Zeitgrenze.
import math
import os
import sys
import time

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import vierachs_huelle as vh

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
R = 6.0  # Fräserradius
TOL = 0.02  # Vernetzung: das Netz liegt höchstens so weit innerhalb der Oberfläche
LAENGS, RADIAL = (0, 0, 1), (1, 0, 0)  # Rundachse C: Stange längs Z, Werkzeug aus X
PHI = vh.raster_phi(1.0)


def werkzeugsicht(x, y, phi):
    """Punkt (x, y) des Querschnitts, vom Werkzeug unter phi aus: (radial, seitlich)."""
    return x * math.cos(phi) + y * math.sin(phi), y * math.cos(phi) - x * math.sin(phi)


def soll_kreis(mitte_x, radius, phi):
    """Höchste Stelle eines Kreises (Mitte auf der X-Achse) unter der Stirn: der Scheitel,
    wenn er seitlich innerhalb R liegt, sonst der Rand der Stirn auf dem Kreis."""
    x, y = werkzeugsicht(mitte_x, 0.0, phi)
    seitlich = abs(y) - R
    if seitlich <= 0:
        return x + radius
    if seitlich > radius:
        return -math.inf
    return x + math.sqrt(radius * radius - seitlich * seitlich)


def soll_vieleck(ecken, phi):
    """Höchste Stelle eines Vielecks unter der Stirn: Ecken und Schnitte der Kanten mit
    dem Streifen |seitlich| ≤ R."""
    punkte = [werkzeugsicht(x, y, phi) for x, y in ecken]
    beste = -math.inf
    for i, (x1, y1) in enumerate(punkte):
        x2, y2 = punkte[(i + 1) % len(punkte)]
        kandidaten = [(x1, y1), (x2, y2)]
        if y1 != y2:
            for rand in (-R, R):
                t = (rand - y1) / (y2 - y1)
                if 0 <= t <= 1:
                    kandidaten.append((x1 + t * (x2 - x1), rand))
        beste = max([beste] + [x for x, y in kandidaten if abs(y) <= R + 1e-9])
    return beste


def mitte_vergleichen(name, form, soll):
    """Weit weg von den Enden (a = −50) ist die Hüllfläche die des Querschnitts: höchstens
    TOL darunter (das Netz liegt innen), nie darüber. Nur wo das Werkzeug vor der Achse
    steht – dahinter zählt nicht (vierachs_bahn sperrt die Achse)."""
    netz = vh.vernetze(form, TOL)
    a = vh.raster_a(-60, -40, 0.25)
    h = vh.schaftfraeser(netz, LAENGS, RADIAL, R, a, PHI)
    i = int(np.argmin(np.abs(a + 50)))
    schlimmste = 0.0
    for j, phi in enumerate(PHI):
        erwartet = soll(phi)
        if erwartet <= R:
            continue
        ist = h.r[i, j]
        abweichung = erwartet - ist
        if not (-1e-6 <= abweichung <= TOL + 1e-6):
            fehler.append(f"{name} bei {math.degrees(phi):.0f}°: {ist:.4f} statt {erwartet:.4f}")
            return
        schlimmste = max(schlimmste, abweichung)
    print(ascii(f"{name}: höchstens {schlimmste:.4f} mm unter der Formel"))


# --- Querschnitte ---------------------------------------------------------------------------
mitte_vergleichen(
    "Zylinder Ø 60",
    Part.makeCylinder(30, 100, V(0, 0, -100)),
    lambda phi: soll_kreis(0.0, 30.0, phi),
)
mitte_vergleichen(
    "Exzenter Ø 20, 15 mm außermittig",
    Part.makeCylinder(10, 100, V(15, 0, -100)),
    lambda phi: soll_kreis(15.0, 10.0, phi),
)
# Sechskant SW 50: Flächen nach 0°, 60° …, Ecken bei 30°, 90° …
ecken = [
    (
        50 / math.sqrt(3) * math.cos(math.radians(30 + 60 * k)),
        50 / math.sqrt(3) * math.sin(math.radians(30 + 60 * k)),
    )
    for k in range(6)
]
umriss = Part.makePolygon([V(x, y, -100) for x, y in ecken] + [V(ecken[0][0], ecken[0][1], -100)])
mitte_vergleichen(
    "Sechskant SW 50",
    Part.Face(umriss).extrude(V(0, 0, 100)),
    lambda phi: soll_vieleck(ecken, phi),
)
netz = vh.vernetze(Part.Face(umriss).extrude(V(0, 0, 100)), TOL)
h = vh.schaftfraeser(netz, LAENGS, RADIAL, R, vh.raster_a(-50, -50, 0.25), PHI)
pruefe(abs(h.r[0, 0] - 25.0) < 1e-6, f"Sechskant auf der Fläche: {h.r[0, 0]}")
pruefe(abs(h.r[0, 30] - 50 / math.sqrt(3)) < 1e-6, f"Sechskant auf der Ecke: {h.r[0, 30]}")

# --- Welle mit Absatz: Ø 60 von −50 bis 0, Ø 40 von −100 bis −50 --------------------------
welle = Part.makeCylinder(30, 50, V(0, 0, -50)).fuse(Part.makeCylinder(20, 50, V(0, 0, -100)))
netz = vh.vernetze(welle, TOL)
a = vh.raster_a(-120, 20, 0.25)
h = vh.schaftfraeser(netz, LAENGS, RADIAL, R, a, PHI)


def bei(stelle, j=0):
    return h.r[int(np.argmin(np.abs(a - stelle))), j]


pruefe(20 - TOL <= bei(-75) <= 20, f"dünner Teil: {bei(-75)}")
# Die Stirn (Radius 6) reicht bis −50,25: noch nicht am Absatz; bis −50: am Absatz.
pruefe(20 - TOL <= bei(-56.25) <= 20, f"vor dem Absatz: {bei(-56.25)}")
pruefe(30 - TOL <= bei(-56.0) <= 30, f"am Absatz: {bei(-56.0)}")
# Vorne endet das Teil bei a = 0: Bis a = R trifft die Stirn noch, danach nicht mehr.
pruefe(30 - TOL <= bei(6.0) <= 30, f"vorne am Rand: {bei(6.0)}")
pruefe(bei(6.25) == vh.KEIN_TREFFER, f"vor dem Teil: {bei(6.25)}")
pruefe(bei(-106.25) == vh.KEIN_TREFFER, f"hinter dem Teil: {bei(-106.25)}")

# Sicher: nie unter dem Raster, und rundum der höchste Nachbar.
sicher = h.sicher()
pruefe(bool(np.all(sicher.r >= h.r)), "sicher liegt unter dem Raster")
i = int(np.argmin(np.abs(a + 56.0)))
pruefe(sicher.r[i - 1, 0] == h.r[i - 1, 0], "sicher: am Absatz längs geglättet")
# bei(): der höhere der beiden Rasterpunkte daneben.
zwischen = float(sicher.bei(-56.1, 0))
pruefe(zwischen == max(sicher.r[i - 1, 0], sicher.r[i, 0]), f"bei −56,1: {zwischen}")
pruefe(float(sicher.bei(200.0, 0)) == vh.KEIN_TREFFER, "bei außerhalb des Rasters")

# Dieselbe Welle längs X (wie bei Rundachse A): Um Y gedreht wird Z zu X und X zu −Z –
# mit diesen Achsen rechnet die Hüllfläche genau dasselbe.
gedreht = welle.copy()
gedreht.rotate(V(), V(0, 1, 0), 90)
h_a = vh.schaftfraeser(vh.vernetze(gedreht, TOL), (1, 0, 0), (0, 0, -1), R, a, PHI)
getroffen = np.isfinite(h.r)
pruefe(
    bool(np.all(getroffen == np.isfinite(h_a.r)))
    and float(np.max(np.abs(h.r[getroffen] - h_a.r[getroffen]))) < 1e-6,
    "längs X gerechnet anders als längs Z",
)

# --- Zeitgrenze: Welle Ø 60 × 100 mit Nocken und Abflachung --------------------------------
teil = (
    Part.makeCylinder(30, 100, V(0, 0, -100))
    .fuse(Part.makeCylinder(12, 20, V(24, 0, -40)))
    .cut(Part.makeBox(10, 8, 30, V(25, -4, -90)))
)
beginn = time.time()
h = vh.schaftfraeser(vh.vernetze(teil, TOL), LAENGS, RADIAL, R, vh.raster_a(-110, 10), PHI)
dauer = time.time() - beginn
print(ascii(f"Welle mit Nocken: {h.r.shape[0]} × {h.r.shape[1]} Punkte in {dauer:.2f} s"))
pruefe(dauer < 10.0, f"zu langsam: {dauer:.1f} s")
# Der Nocken reicht bis 36 mm von der Achse; unter ihm kommt die Stirn nicht tiefer.
pruefe(36 - TOL <= float(np.max(h.r)) <= 36, f"höchste Stelle: {np.max(h.r)}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
