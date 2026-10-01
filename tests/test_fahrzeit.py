# Prüft die Fahrzeit (W-001, Stufe 4d; fahrzeit.py): das Trapezprofil je Satz – vom Stand
# in den Stand L ÷ v + v ÷ a, als Dreieck 2·√(L ÷ a), wenn der Weg nicht reicht –, die
# Übergänge (durchfahren, wo die Richtung bleibt; anhalten an Ecken ab 15°, um Sätze mit
# fester Zeit und am Ende), die Vorausschau (ein kurzer letzter Satz bremst schon den
# davor) und der Eilgang je Achse. Dazu die Vorgaben: 10 m/min und 1 m/s², und bahn.zeit
# mit Eilgängen und Bögen.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import bahn as bn
from camaddon import export
from camaddon import fahrzeit as fz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nahe(a, b, genau=1e-9):
    return abs(a - b) < genau


# --- Vorgaben ------------------------------------------------------------------------------
pruefe(export.VORGABE_EILGANG == 10000.0, f"Eilgang: {export.VORGABE_EILGANG}")
pruefe(export.VORGABE_BESCHLEUNIGUNG == 1.0, f"Beschleunigung: {export.VORGABE_BESCHLEUNIGUNG}")
pruefe(export.VORGABE_DREHBESCHLEUNIGUNG == 1.0, f"drehend: {export.VORGABE_DREHBESCHLEUNIGUNG}")
pruefe(fz.EILGANG == 10000.0 and fz.BESCHLEUNIGUNG == 1000.0 and fz.ECKE == 15.0, "Konstanten")

# --- Trapez und Dreieck ---------------------------------------------------------------------
pruefe(nahe(fz.trapez(100, 0, 0, 10, 1000), 10 + 10 / 1000), "Trapez 100 mm, 10 mm/s")
pruefe(nahe(fz.trapez(15, 0, 0, 250, 3000), 2 * math.sqrt(15 / 3000)), "Dreieck 15 mm")
pruefe(nahe(fz.trapez(100, 10, 10, 10, 1000), 10.0), "durchfahren: nur L ÷ v")
pruefe(nahe(fz.trapez(100, 0, 10, 10, 1000), 10 + 10 / 2000), "nur anfahren: + v ÷ 2a")
pruefe(nahe(fz.trapez(100, 10, 0, 10, 1000), 10 + 10 / 2000), "nur bremsen: + v ÷ 2a")
pruefe(fz.trapez(0, 0, 0, 10, 1000) == 0.0, "ohne Weg")
pruefe(nahe(fz.trapez(100, 0, 0, 10, 0), 10.0), "ohne Beschleunigung: L ÷ v")
pruefe(fz.trapez(100, 0, 0, 0, 1000) == math.inf, "ohne Tempo")
# Grenzgeschwindigkeiten über dem Tempo werden gekappt, nicht negativ gerechnet.
pruefe(nahe(fz.trapez(100, 50, 50, 10, 1000), 10.0), "Grenze über dem Tempo")

# --- Übergänge -------------------------------------------------------------------------------
gerade = fz.Satz(100, 10, 1000, (1, 0, 0), (1, 0, 0))
pruefe(nahe(sum(fz.zeiten([gerade])), 10 + 10 / 1000), "ein Satz: Stand in Stand")
# Zwei Geraden in einer Richtung: wie eine lange – einmal anfahren, einmal bremsen.
pruefe(nahe(sum(fz.zeiten([gerade, gerade])), 20 + 10 / 1000), "zwei in einer Richtung")
# Knick 10°: fährt durch; 20°: Ecke (ab 15°), hält.
schraeg = fz.Satz(
    100, 10, 1000, (math.cos(math.radians(10)), math.sin(math.radians(10)), 0), (1, 0, 0)
)
pruefe(nahe(sum(fz.zeiten([gerade, schraeg])), 20 + 10 / 1000), "10°: durchfahren")
ecke = fz.Satz(
    100, 10, 1000, (math.cos(math.radians(20)), math.sin(math.radians(20)), 0), (1, 0, 0)
)
pruefe(nahe(sum(fz.zeiten([gerade, ecke])), 20 + 2 * 10 / 1000), "20°: anhalten")
quer = fz.Satz(100, 10, 1000, (0, 1, 0), (0, 1, 0))
pruefe(nahe(sum(fz.zeiten([gerade, quer])), 20 + 2 * 10 / 1000), "90°: anhalten")
# Verschiedene Tempi: am Übergang das kleinere.
langsam = fz.Satz(100, 5, 1000, (1, 0, 0), (1, 0, 0))
z = fz.zeiten([gerade, langsam])
# Anfahren oder Bremsen von v0 auf v kostet über L ÷ v hinaus (v − v0)² ÷ (2·a·v).
pruefe(nahe(z[0], 10 + 10 / 2000 + 25 / 20000) and nahe(z[1], 20 + 5 / 2000), f"Tempi: {z}")
# Ein fester Satz (Eilgang) dazwischen: davor und danach hält die Maschine.
fest = fz.Satz(0, 0, 0, fest=0.5)
pruefe(nahe(sum(fz.zeiten([gerade, fest, gerade])), 20 + 2 * 10 / 1000 + 0.5), "fester Satz")
# Ohne Richtung (None): anhalten.
ohne = fz.Satz(100, 10, 1000)
pruefe(nahe(sum(fz.zeiten([gerade, ohne])), 20 + 2 * 10 / 1000), "ohne Richtung")
# Vorausschau: ein kurzer letzter Satz (0,01 mm) kann von 10 mm/s nicht mehr bremsen – der
# davor bremst schon: am Übergang höchstens √(2·a·L) = √20 mm/s.
kurz = fz.Satz(0.01, 10, 1000, (1, 0, 0), (1, 0, 0))
z = fz.zeiten([gerade, kurz])
v_ueber = math.sqrt(2 * 1000 * 0.01)
pruefe(
    nahe(z[0], fz.trapez(100, 0, v_ueber, 10, 1000)) and nahe(z[1], v_ueber / 1000),
    f"Vorausschau: {z}",
)
# Ein kurzer erster Satz beschleunigt nur bis √(2·a·L); der zweite fährt weiter hoch.
z = fz.zeiten([kurz, gerade])
pruefe(
    nahe(z[0], v_ueber / 1000) and nahe(z[1], fz.trapez(100, v_ueber, 0, 10, 1000)), f"Anlauf: {z}"
)
pruefe(fz.zeiten([]) == [], "leer")

# --- Winkel und Eilgang ------------------------------------------------------------------------
pruefe(
    nahe(fz.winkel((1, 0, 0), (0, 1, 0)), 90.0) and nahe(fz.winkel((2, 0), (1, 0)), 0.0), "Winkel"
)
pruefe(fz.winkel((0, 0, 0), (1, 0, 0)) == 180.0, "Winkel ohne Länge")
# Eilgang: jede Achse für sich, die langsamste bestimmt – hier X (70 mm) vor Y (30 mm, Dreieck).
t = fz.eilgangzeit((70, -30, None), (333.0, 333.0, 250.0), (3000.0, 3000.0, 3000.0))
pruefe(nahe(t, max(70 / 333 + 333 / 3000, 2 * math.sqrt(30 / 3000))), f"Eilgang: {t}")
pruefe(fz.eilgangzeit((None, None), (1, 1), (1, 1)) == 0.0, "Eilgang ohne Achse")

# --- bahn.zeit: Vorschub, Eilgang und Bögen mit den Vorgaben -----------------------------------


def P(x, y, z, eilgang=False, **mehr):
    return bn.Punkt(eilgang, x, y, z, **mehr)


# 100 mm hin, Ecke, 50 mm quer, Eilgang 20 mm hoch: alles vom Stand in den Stand.
punkte = [P(0, 0, 0), P(100, 0, 0), P(100, 50, 0), P(100, 50, 20, eilgang=True)]
v = 600 / 60.0
soll = (100 / v + v / 1000) + (50 / v + v / 1000) + 2 * math.sqrt(20 / 1000)
pruefe(nahe(bn.zeit(punkte, 600.0) * 60, soll, 1e-9), f"bahn.zeit: {bn.zeit(punkte, 600.0) * 60}")
pruefe(bn.zeit(punkte, 600.0) > bn.dauer(punkte, 600.0), "mit Beschleunigung länger als ohne")
# Gerade in einen Halbkreis: die Tangente am Anfang zeigt wie die Gerade – durchfahren; am
# Ende des Bogens zeigt sie zurück, die nächste Gerade geht weiter nach +x: Ecke.
bogen = [P(0, 0, 0), P(100, 0, 0), P(100, 20, 0, bogen=(100, 10, False)), P(200, 20, 0)]
z = bn.zeit(bogen, 600.0) * 60
weg_bogen = math.pi * 10
soll = (100 + weg_bogen) / v + v / 1000 + 100 / v + v / 1000
pruefe(nahe(z, soll, 1e-9), f"Bogen: {z} statt {soll}")
# Eintauchen mit eigenem Vorschub: 10 mm senkrecht mit 100 mm/min, dann Ecke.
tauch = [P(0, 0, 10), P(0, 0, 0, eintauchen=True), P(50, 0, 0)]
z = bn.zeit(tauch, 600.0, 100.0) * 60
ve = 100 / 60.0
pruefe(nahe(z, 10 / ve + ve / 1000 + 50 / v + v / 1000, 1e-9), f"Eintauchen: {z}")
# Eigener Eilgang und eigene Beschleunigung.
z = bn.zeit(punkte, 600.0, eilgang=20000.0, beschleunigung=3000.0) * 60
soll = (100 / v + v / 3000) + (50 / v + v / 3000) + 2 * math.sqrt(20 / 3000)
pruefe(nahe(z, soll, 1e-9), f"eigene Werte: {z} statt {soll}")

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
