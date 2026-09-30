# Prüft die Bahn „Rundum schlichten“ (W-003 Stufe V5b): Welle mit Absatz, Kugelfräser –
# die Spitze liegt überall auf der Hüllfläche (gegen den dicht abgetasteten Umriss), auch
# zwischen den Punkten, die nach dem Zusammenfassen bleiben, höchstens um Vernetzung und
# Bahntoleranz darüber; vorne und hinten auf der Tiefe am Ende des Teils, die Spirale endet
# um den Überlauf hinter dem Teil. Torus mit Aufmaß. Dann der Schutz: In einer Nut, die
# schmaler ist als der Schruppfräser, blieb nach dem Schruppen alles stehen – der Kugelfräser
# schneidet dort höchstens seinen Radius tief, der Rest wird gemeldet. Dazu die Zeitgrenze.
import math
import os
import sys
import time

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import fraeserform as ff
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import vierachs_bahn as vb
from camaddon import vierachs_huelle as vh

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
LAENGS, RADIAL = (0, 0, 1), (1, 0, 0)
LUFT = vb.TOLERANZ_SCHLICHTEN + vb.BAHN_TOLERANZ + 2e-3  # so weit über der Hüllfläche


def abgetastet(umriss, schritt=0.002):
    """Punkte (a, x) dicht auf einem Linienzug [(a, x), …]."""
    teile = []
    for (a1, x1), (a2, x2) in zip(umriss, umriss[1:], strict=False):
        anzahl = max(2, int(math.hypot(a2 - a1, x2 - x1) / schritt) + 1)
        t = np.linspace(0.0, 1.0, anzahl)
        teile.append(np.column_stack([a1 + t * (a2 - a1), x1 + t * (x2 - x1)]))
    return np.concatenate(teile)


def im_schnitt(punkte, form, stellen):
    """Die Hüllfläche eines Drehteils im Schnitt durch die Werkzeugachse: an jeder Stelle die
    höchste Stelle x − z(Abstand) des Umrisses."""
    ergebnis = np.full(len(stellen), -math.inf)
    for i, stelle in enumerate(stellen):
        abstand = np.abs(punkte[:, 0] - stelle)
        unter = abstand <= form.radius
        if unter.any():
            ergebnis[i] = np.max(punkte[unter, 1] - form.hoehe(abstand[unter]))
    return ergebnis


def erlaubt(umriss, form, a, soll):
    """So weit darf die Bahn über der Hüllfläche liegen: Vernetzung und Bahntoleranz, der
    Sehnenfehler – und wo die Hüllfläche steil ist, verschiebt das Rechnen mit dem um die
    Vernetzung größeren Fräser sie längs: Toleranz × Steigung. Wo sie an einer Wand springt
    (mehr als 0,05 mm auf 0,01 mm längs), zählt es nicht."""
    davor = im_schnitt(umriss, form, np.clip(a + 0.01, -42.0, 0.0))
    danach = im_schnitt(umriss, form, np.clip(a - 0.01, -42.0, 0.0))
    steigung = np.maximum(np.abs(davor - soll), np.abs(danach - soll)) / 0.01
    grenze = LUFT + vb.SEHNE_HOECHSTENS + vb.TOLERANZ_SCHLICHTEN * steigung
    return np.where(steigung * 0.01 < 0.05, grenze, math.inf)


def dicht(bahn):
    """Die Vorschubpunkte der Bahn wieder alle 0,5°: (a, r) – so fährt die Steuerung."""
    vorschub = [p for p in bahn.punkte if not p.eilgang]
    a, r = [], []
    for von, nach in zip(vorschub, vorschub[1:], strict=False):
        anzahl = max(1, int(round((nach.phi - von.phi) / vb.SCHRITT_PHI_SCHLICHTEN)))
        t = np.arange(anzahl) / anzahl
        a.append(von.a + t * (nach.a - von.a))
        r.append(von.r + t * (nach.r - von.r))
    return np.concatenate(a), np.concatenate(r)


# --- Welle mit Absatz, Kugelfräser R 3 ----------------------------------------------------
# Ø 40 von −30 bis 0, Ø 30 von −42 bis −30; Stange Ø 50 bis 1 vor dem Teil, Futter bei −60.
welle = Part.makeCylinder(20, 30, V(0, 0, -30)).fuse(Part.makeCylinder(15, 12, V(0, 0, -42)))
netz = vh.vernetze(welle.removeSplitter(), vb.TOLERANZ_SCHLICHTEN)
umriss = abgetastet(
    [(0.0, 0.0), (0.0, 20.0), (-30.0, 20.0), (-30.0, 15.0), (-42.0, 15.0), (-42.0, 0.0)]
)
kugel = ff.kugel(3.0)
werte = vb.Schlichtwerte(
    form=kugel,
    stange_radius=25.0,
    schrittweite=0.35,
    aufmass=0.0,
    a_stange_vorne=1.0,
    a_futter=-60.0,
)
beginn = time.time()
bahn = vb.schlichten(netz, LAENGS, RADIAL, werte)
dauer = time.time() - beginn
start = bahn.punkte[0]
pruefe(start.eilgang and start.a == 1.0 + 3.0 + 2.0 and start.r == 27.0, f"Start: {start}")
a_ende = -42.0 - (3.0 + 0.5)  # Überlauf: Radius + 0,5
vorschub = [p for p in bahn.punkte if not p.eilgang]
pruefe(abs(vorschub[-1].a - a_ende) < 0.35 / 720 + 1e-9, f"Ende bei {vorschub[-1].a}")
pruefe(abs(bahn.umdrehungen - (6.0 - a_ende) / 0.35) < 1 / 720, f"{bahn.umdrehungen} Umdrehungen")
pruefe(abs(bahn.kammhoehe - (3 - math.sqrt(9 - 0.175**2))) < 1e-12, f"Kammhöhe {bahn.kammhoehe}")
pruefe(bahn.stehen == 0.0 and bahn.hinten_frei == 0.0, "ohne Rest: nichts bleibt stehen")
a, r = dicht(bahn)
soll = im_schnitt(umriss, kugel, np.clip(a, -42.0, 0.0))  # davor und dahinter: am Ende
darueber = r - soll
pruefe(
    darueber.min() >= -1e-3,
    f"Schlichten im Teil: {darueber.min():.4f} (bei a {a[np.argmin(darueber)]:.3f})",
)
zu_hoch = darueber - erlaubt(umriss, kugel, a, soll)
pruefe(zu_hoch.max() <= 0, f"zu hoch: {zu_hoch.max():+.4f} (bei a {a[np.argmax(zu_hoch)]:.3f})")
pruefe(len(bahn.punkte) < 40000, f"{len(bahn.punkte)} Punkte – zu wenig zusammengefasst")
print(ascii(f"Welle mit Absatz: {len(bahn.punkte)} Punkte in {dauer:.1f} s"))

# Torus R 3, Eckradius 1, Aufmaß 0,2: die Hüllfläche des um 0,2 größeren Fräsers, 0,2 höher.
torus = ff.torus(3.0, 1.0)
bahn = vb.schlichten(
    netz,
    LAENGS,
    RADIAL,
    vb.Schlichtwerte(torus, 25.0, 0.8, 0.2, 1.0, -60.0),
)
a, r = dicht(bahn)
soll = im_schnitt(umriss, torus.mit_aufmass(0.2), np.clip(a, -42.0, 0.0)) + 0.2
darueber = r - soll
pruefe(darueber.min() >= -1e-3, f"Torus im Aufmaß: {darueber.min():.4f}")
zu_hoch = darueber - erlaubt(umriss, torus.mit_aufmass(0.2), a, soll - 0.2)
pruefe(
    zu_hoch.max() <= 0, f"Torus zu hoch: {zu_hoch.max():+.4f} (bei a {a[np.argmax(zu_hoch)]:.3f})"
)

# Befehle wie beim Schruppen: X ist der Radius, C dreht, Vorschub nach G93.
befehle = vb.befehle(bahn, LAENGS, RADIAL, "C", 1, 955.0)
pruefe(befehle[3].Name == "G93" and befehle[-1].Name == "G94", "G93 … G94")

try:
    vb.schlichten(netz, LAENGS, RADIAL, vb.Schlichtwerte(kugel, 25.0, 6.5, 0.0, 1.0, -60.0))
    fehler.append("Schrittweite größer als der Fräser ging durch")
except ValueError as grund:
    pruefe("Schrittweite" in str(grund), f"Grund: {grund}")

# --- Schutz: eine Nut, schmaler als der Schruppfräser ---------------------------------------
# Welle Ø 40 von −40 bis 0, dazwischen eine Nut 8 mm breit auf Ø 30 (a −24 … −16). Der
# Schruppfräser Ø 12 kommt nicht hinein: Dort steht nach dem Schruppen Ø 40 plus Aufmaß.
nut = Part.makeCylinder(20, 40, V(0, 0, -40)).cut(
    Part.makeCylinder(25, 8, V(0, 0, -24)).cut(Part.makeCylinder(15, 8, V(0, 0, -24)))
)
schruppen = vb.schruppen(
    vh.vernetze(nut),
    LAENGS,
    RADIAL,
    vb.Schruppwerte(6.0, 25.0, 2.0, 4.8, 0.3, 1.0, -70.0),
)
stange = rm.Stange(25.0, -70.0, 1.0)
for von, nach in zip(schruppen.punkte, schruppen.punkte[1:], strict=False):
    if not nach.eilgang and not von.eilgang:
        stange.fahre((von.a, von.r, von.phi), (nach.a, nach.r, nach.phi), 6.0)
    elif not nach.eilgang:  # vom Eilgang in den Vorschub: der erste Schnitt
        stange.schnitt(nach.a, nach.r, nach.phi, 6.0)
im_nut = stange.r[(stange.a > -22) & (stange.a < -18)]
pruefe(im_nut.min() > 20.0, f"in der Nut geschruppt: {im_nut.min():.3f}")
netz = vh.vernetze(nut, vb.TOLERANZ_SCHLICHTEN)
ohne = vb.schlichten(netz, LAENGS, RADIAL, vb.Schlichtwerte(kugel, 25.0, 0.35, 0.0, 1.0, -70.0))
mit = vb.schlichten(
    netz,
    LAENGS,
    RADIAL,
    vb.Schlichtwerte(
        kugel,
        25.0,
        0.35,
        0.0,
        1.0,
        -70.0,
        rest=(stange.a, stange.phi, stange.r),
        aufmass_schruppen=0.3,
    ),
)
a_ohne, r_ohne = dicht(ohne)
a_mit, r_mit = dicht(mit)
tief_ohne = r_ohne[(a_ohne > -21) & (a_ohne < -19)].min()
tief_mit = r_mit[(a_mit > -21) & (a_mit < -19)].min()
pruefe(abs(tief_ohne - 15.0) < 0.02, f"ohne Schutz in die Nut: {tief_ohne:.3f}")
pruefe(mit.grenze == 3.0, f"Grenze {mit.grenze}")
# Stehen blieb Ø 40 + Aufmaß: höchstens 3 mm darunter, also nicht unter 17,3 mm.
pruefe(17.2 <= tief_mit <= 17.45, f"mit Schutz in der Nut: {tief_mit:.3f}")
pruefe(2.0 <= mit.stehen <= 2.4, f"es bleiben {mit.stehen:.3f} mm stehen")
aussen = (a_mit > -14) & (a_mit < -2)
pruefe(
    float(np.max(np.abs(r_mit[aussen] - 20.0))) < 0.02,
    f"neben der Nut: {r_mit[aussen].min():.3f} … {r_mit[aussen].max():.3f}",
)

# --- Zeitgrenze: Kugelfräser Ø 6 auf der Welle Ø 60 × 100 mit Nocken, 0,35 mm ------------
teil = (
    Part.makeCylinder(30, 100, V(0, 0, -100))
    .fuse(Part.makeCylinder(12, 20, V(24, 0, -40)))
    .cut(Part.makeBox(10, 8, 30, V(25, -4, -90)))
)
beginn = time.time()
bahn = vb.schlichten(
    vh.vernetze(teil, vb.TOLERANZ_SCHLICHTEN),
    LAENGS,
    RADIAL,
    vb.Schlichtwerte(kugel, 40.0, 0.35, 0.0, 1.0, -130.0),
)
dauer = time.time() - beginn
print(ascii(f"Welle mit Nocken: {len(bahn.punkte)} Punkte in {dauer:.1f} s"))
pruefe(dauer < 30.0, f"zu langsam: {dauer:.1f} s")

if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
