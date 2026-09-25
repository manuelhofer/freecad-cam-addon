# Prüft das Rechnen mit Schnittwerten (schnittdaten.py) an Manuels Beispiel –
# Schaftfräser Ø 12, 3 Schneiden, vc 120 m/min – und beim Bohren; fehlende
# Werte ergeben 0 statt eines Fehlers.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import schnittdaten as sd
from camaddon import werkzeuge as wz

fehler = []


def ungefaehr(wert, soll, text, genau=0.05):
    if abs(wert - soll) > genau:
        fehler.append(f"{text}: {wert:.4f} statt {soll}")


fraeser = wz.Werkzeug(durchmesser=12, schneiden=3, schneidenlaenge=26)
vollnut = wz.Einsatz(art=wz.VOLLNUT, ae=12, ap=3, vc=120, fz=0.05)
dynamisch = wz.Einsatz(art=wz.DYNAMISCH, ae=1.2, ap=25, vc=120, fz=0.15)

n, vf, q = sd.rechne(fraeser, vollnut)
ungefaehr(n, 3183.1, "n")
ungefaehr(vf, 477.46, "vf Vollnut")
ungefaehr(q, 17.19, "Q Vollnut", 0.01)
n, vf, q = sd.rechne(fraeser, dynamisch)
ungefaehr(vf, 1432.39, "vf dynamisch")
ungefaehr(q, 42.97, "Q dynamisch", 0.01)

# Bohren: Q aus der Kreisfläche.
bohrer = wz.Werkzeug(art=wz.BOHRER, durchmesser=8.5, schneiden=2)
n, vf, q = sd.rechne(bohrer, wz.Einsatz(art=wz.BOHREN, vc=80, fz=0.1))
ungefaehr(n, 2995.86, "n Bohrer")
ungefaehr(vf, 599.17, "vf Bohrer")
ungefaehr(q, math.pi * 8.5**2 / 4 * 599.17 / 1000, "Q Bohrer", 0.01)

# Fehlt etwas, ist das Ergebnis 0 – „unbekannt“.
for werkzeug, einsatz, text in (
    (wz.Werkzeug(durchmesser=0, schneiden=3), vollnut, "ohne Durchmesser"),
    (fraeser, wz.Einsatz(ae=12, ap=3, vc=0, fz=0.05), "ohne vc"),
    (fraeser, wz.Einsatz(ae=12, ap=3, vc=120, fz=0), "ohne fz"),
):
    n, vf, q = sd.rechne(werkzeug, einsatz)
    if vf != 0 or q != 0:
        fehler.append(f"{text}: vf {vf}, Q {q} statt 0")

# Eingriffswinkel: Vollnut 180°, halber Durchmesser 90°, 10 % von D 36,87°.
ungefaehr(math.degrees(sd.eingriffswinkel(12, 12)), 180, "φ Vollnut")
ungefaehr(math.degrees(sd.eingriffswinkel(20, 12)), 180, "φ ae > D")
ungefaehr(math.degrees(sd.eingriffswinkel(6, 12)), 90, "φ ae = D/2")
ungefaehr(math.degrees(sd.eingriffswinkel(1.2, 12)), 36.87, "φ ae = 10 %")
ungefaehr(sd.eingriffswinkel(0, 12), 0, "φ ohne ae")

# Spandicke: bei 10 % von D nur 60 % von fz; ab D/2 gleich fz.
ungefaehr(sd.spandicke_max(0.15, 1.2, 12), 0.09, "h max dynamisch", 1e-6)
ungefaehr(sd.spandicke_max(0.05, 12, 12), 0.05, "h max Vollnut", 1e-9)
ungefaehr(sd.spandicke_max(0.05, 6, 12), 0.05, "h max ae = D/2", 1e-9)
ungefaehr(sd.spandicke_mittel(0.05, 12, 12), 0.1 / math.pi, "h m Vollnut", 1e-6)
ungefaehr(sd.spandicke_mittel(0.15, 1.2, 12), 0.0466, "h m dynamisch", 1e-4)

# Ausgleich: gewünschte Spandicke 0,09 bei ae 1,2 → fz 0,15; ab D/2 unverändert.
ungefaehr(sd.fz_fuer_spandicke(0.09, 1.2, 12), 0.15, "fz Ausgleich", 1e-6)
ungefaehr(sd.fz_fuer_spandicke(0.05, 8, 12), 0.05, "fz Ausgleich ab D/2", 1e-9)
ungefaehr(sd.fz_fuer_spandicke(0.05, 0, 12), 0, "fz Ausgleich ohne ae", 1e-9)

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
