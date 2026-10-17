# Prüft den Kinematik-Kern (W-001 Stufe 4e): Rückwärts und vorwärts gehören zusammen –
# stellungen(punkt) und programm(stellungen) geben den Punkt zurück. An der
# Beispiel-Fräse (Werkzeug 50 mm): X1 an der Grenze −250 heißt, die Spitze steht bei
# X 250. An der Beispiel-Drehmaschine mit C (ohne TCPM): programm() bleibt der Punkt,
# am_werkstueck() ist er um −C gedreht, rundachsen() sagt C.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np

from camaddon import beispielmaschine as bm
from camaddon import kinematik as km
from camaddon import reichweite as rw
from camaddon import sprache
from camaddon import verfahren as vf

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nah(a, b, genau=1e-6):
    return max(abs(x - y) for x, y in zip(a, b, strict=True)) < genau


V = FreeCAD.Vector
sprache.setze_sprache("de")

# --- Fräse: hin und zurück, eine Achse an der Grenze --------------------------------------
asm, ma = bm.fraesmaschine()
p = rw.Pruefung(asm, ma)
k = km.Kinematik(p, p.werkzeugaufnahme(1), 50, V())
for punkt in [(0, 0, 0), (100, 50, -20), (-30, 20, 5), (7.5, -3.25, 40)]:
    stellungen = k.stellungen(punkt)
    pruefe(stellungen is not None, f"Fräse {punkt}: nicht erreichbar")
    if stellungen is None:
        continue
    pruefe(nah(k.programm(stellungen), punkt), f"Fräse {punkt}: {k.programm(stellungen)}")
    pruefe(nah(k.am_werkstueck(stellungen), punkt), f"ohne Rundachse am Werkstück {punkt}")
    pruefe(k.rundachsen(stellungen) == {}, f"Rundachsen der Fräse: {k.rundachsen(stellungen)}")
stellungen = k.stellungen((400, 0, 10))
x1 = next(a for a in stellungen if vf.namen(ma, a) == "X1")
pruefe(abs(stellungen[x1] + 400) < 1e-9, f"X1 für X 400: {stellungen[x1]}")
stellungen[x1] = -250.0  # an der Grenze
pruefe(nah(k.programm(stellungen), (250, 0, 10)), f"an der Grenze: {k.programm(stellungen)}")
FreeCAD.closeDocument(asm.Document.Name)

# --- Drehmaschine mit C: ohne TCPM dreht C das Teil unter der Spitze -----------------------
asm, ma = bm.drehmaschine()
p = rw.Pruefung(asm, ma)
k = km.Kinematik(p, p.werkzeugaufnahme(1), 125, V(0, 0, 60))
for punkt, c in [((30, 0, -10), 0.0), ((30, 0, -10), 90.0), ((22.5, 0, -40), -3725.0)]:
    stellungen = k.stellungen(punkt, {"C": c})
    pruefe(stellungen is not None, f"Drehmaschine {punkt}, C {c}: nicht erreichbar")
    if stellungen is None:
        continue
    pruefe(nah(k.programm(stellungen), punkt), f"programm {punkt}, C {c}")
    soll = FreeCAD.Rotation(V(0, 0, 1), -c).multVec(V(*punkt))
    pruefe(
        nah(k.am_werkstueck(stellungen), tuple(soll)),
        f"am Werkstück {k.am_werkstueck(stellungen)} statt {tuple(soll)} (C {c})",
    )
    rund = k.rundachsen(stellungen)
    pruefe(set(rund) == {"C"} and abs(rund["C"] - c) < 1e-9, f"Rundachsen: {rund}")
FreeCAD.closeDocument(asm.Document.Name)

# --- Viele Stationen zugleich (P-2026-10-18-66): am_werkstueck_felder wie am_werkstueck --------
# An jeder Beispielmaschine mit Rundachsen, Stellungen zufällig in den Grenzen, einige Achsen
# ohne Stellung (NaN: Grundstellung wie ein fehlender Schlüssel).
zufall = np.random.default_rng(7)
for bauen in (
    bm.drehmaschine,
    bm.fuenfachs_tisch_tisch,
    bm.fuenfachs_kopf_tisch,
    bm.fuenfachs_kopf_kopf,
    bm.grob_g550,
):
    asm, ma = bauen()
    p = rw.Pruefung(asm, ma)
    aufnahme = p.werkzeugaufnahme(1)
    k = km.Kinematik(p, aufnahme, 80, V(3, -2, 40))
    achsen_ = p.gefahrene_achsen(aufnahme)
    felder = {}
    for achse in achsen_:
        unten = achse.minimum if achse.minimum is not None else -180.0
        oben = achse.maximum if achse.maximum is not None else 180.0
        feld = zufall.uniform(unten, oben, 40)
        feld[zufall.random(40) < 0.2] = np.nan
        felder[achse] = feld
    viele = k.am_werkstueck_felder(felder)
    abweichung = max(
        max(
            abs(a - b)
            for a, b in zip(
                viele[i],
                k.am_werkstueck({a: float(f[i]) for a, f in felder.items() if not np.isnan(f[i])}),
                strict=True,
            )
        )
        for i in range(40)
    )
    pruefe(abweichung < 1e-9, f"{bauen.__name__}: viele Stationen {abweichung:.2e} mm daneben")
    FreeCAD.closeDocument(asm.Document.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
