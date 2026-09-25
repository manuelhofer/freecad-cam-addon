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

# --- Strategien vergleichen ------------------------------------------------
ungefaehr(sd.schneidenweg_je_cm3(12, 3, 0.05, 3, 12), 3.4907, "Schneidenweg Vollnut", 1e-3)
ungefaehr(sd.schneidenweg_je_cm3(1.2, 25, 0.15, 3, 12), 0.2860, "Schneidenweg dynamisch", 1e-3)
ungefaehr(sd.schneidenweg_je_cm3(0, 25, 0.15, 3, 12), 0, "Schneidenweg ohne ae", 1e-9)

a = sd.kennzahlen(fraeser, vollnut)
b = sd.kennzahlen(fraeser, dynamisch)
ungefaehr(a.zeit, 100 / 17.19, "Zeit Vollnut", 0.01)
ungefaehr(a.eingriff, 0.5, "Eingriff Vollnut", 1e-9)
ungefaehr(b.eingriff, 36.87 / 360, "Eingriff dynamisch", 1e-4)
if a.leistung or b.leistung:
    fehler.append("Leistung ohne Werkstoff")

saetze = dict(sd.urteil(a, b, "A", "B"))
ungefaehr(saetze.get("wv.urteil.q", {}).get("faktor", 0), 2.5, "Urteil Q-Faktor")
ungefaehr(saetze.get("wv.urteil.weg_weniger", {}).get("faktor", 0), 12.2, "Urteil Weg", 0.05)
if saetze.get("wv.urteil.q", {}).get("schnell") != "B":
    fehler.append(f"schneller ist B, das Urteil sagt {saetze.get('wv.urteil.q')}")
if saetze.get("wv.urteil.ap") != {"ap_viel": 25, "ap_wenig": 3}:
    fehler.append(f"Urteil ap: {saetze.get('wv.urteil.ap')}")
if "wv.urteil.eingriff" not in saetze or "wv.urteil.leistung" in saetze:
    fehler.append(f"Urteil Eingriff/Leistung: {sorted(saetze)}")
# Umgekehrt gefragt, dasselbe Urteil.
if dict(sd.urteil(b, a, "B", "A")).get("wv.urteil.q", {}).get("schnell") != "B":
    fehler.append("Urteil hängt von der Reihenfolge ab")

# Mit kc1.1 (C45): Leistung = Q · kc / 60 000, kc aus der mittleren Spandicke.
c45 = type("W", (), {"kc11": 2220.0, "mc": 0.14})()
k = sd.kennzahlen(fraeser, vollnut, c45)
kc = 2220.0 * sd.spandicke_mittel(0.05, 12, 12) ** -0.14
ungefaehr(k.leistung, 17.19 * kc / 60000, "Leistung Vollnut C45", 0.01)
ungefaehr(k.drehmoment, k.leistung * 9550 / 3183.1, "Drehmoment", 0.01)
if "wv.urteil.leistung" not in dict(sd.urteil(k, sd.kennzahlen(fraeser, dynamisch, c45), "A", "B")):
    fehler.append("Urteil ohne Leistung trotz kc1.1")

# Fehlen Werte, sagt das Urteil nur das.
leer = sd.kennzahlen(fraeser, wz.Einsatz(ae=12, ap=3))
if sd.urteil(leer, b, "A", "B") != [("wv.urteil.unvollstaendig", {})]:
    fehler.append("Urteil mit fehlenden Werten")

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
