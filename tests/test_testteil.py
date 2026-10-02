# Prüft den Weg an Manuels Testteil für die 3-Achs-Fräse (W-013, Spezifikation Strategien,
# Abschnitt 13; Manuel, 2026-10-02: „das muss sinnvoll bearbeitet werden auch mit mehreren
# arbeitsschritten“): beispiele/testteil_3achs_fraese.FCStd – Platte 100 × 100 × 10, darauf eine
# Insel (z 10 … 22), auf ihr eine obere Stufe (z 22 … 32) mit einer dreieckigen Tasche (Boden
# z 27), in der Insel eine Kugelmulde. Rohteil 102 × 102 × 34, der Standardfräser Ø 12.
# Räumen über die drei offenen Höhen (T1): die tiefste Fläche zuerst – außen um die Insel, 23 tief
# in einer Lage –, die Insel oben danach nur noch über sich, in Ringen um das, was noch steht, die
# obere Stufe zuletzt; zusammen höchstens 13 min (jede Fläche für sich vom Rohteil her: 26 min),
# ohne Rest, nirgends ins Teil. Der Boden der kleinen Tasche: Der Ø 12 passt nicht hinein – ein
# Satz statt einer Bahn rund um die Insel (B-006).
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD

from camaddon import bahn as bn
from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import pruefstand as ps
from camaddon import raeumen as ra
from camaddon import raeumen_bahn as rb
from camaddon import sprache
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
werkzeug = wz.standardwerkzeug()
R = werkzeug.durchmesser / 2
form = ff.scheibe(R)
schruppen = next(e for e in werkzeug.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
VF = 902.0  # mm/min bei vc 85, fz 0,1, 4 Schneiden
AE, AP = schruppen.ae, schruppen.ap

dokument = FreeCAD.openDocument(os.path.join(ADDON, "beispiele", "testteil_3achs_fraese.FCStd"))
teil = dokument.getObject("Body").Shape.copy()
FreeCAD.closeDocument(dokument.Name)
ROHTEIL = (-51.0, 51.0, -51.0, 51.0)  # 1 mm rundum, wie der Assistent es anlegt
OBEN = 33.0
PLATTE, INSEL, TASCHE, STUFE = 10.0, 22.0, 27.0, 32.0
pruefe(
    abs(teil.BoundBox.ZMax - STUFE) < 1e-6 and abs(teil.BoundBox.XLength - 100.0) < 1e-6,
    f"das Testteil: {teil.BoundBox}",
)


def ebenen_bei(*hoehen):
    return [e for z in hoehen for e in hf.ebenen_oben(teil) if abs(e.z - z) < 1e-6]


def raeumen(*hoehen):
    ebenen = ebenen_bei(*hoehen)
    werte = rb.Raeumwerte(
        form, AP, AE, 0.3, OBEN, OBEN + 5.0, ROHTEIL,
        schneidenlaenge=werkzeug.schneidenlaenge, eintauchwinkel=werkzeug.eintauchwinkel,
        vorschub=VF, eintauchen=VF * 0.3,
    )  # fmt: skip
    netz = hf.netze_je_hoehe(teil, ebenen)
    return rb.planen(netz, werte, ebenen, ra.konturen_des_teils(teil))


def vorschub_je_hoehe(bahn):
    """{z: mm im Vorschub auf dieser Höhe} und die Höhen in der Reihenfolge der Bahn."""
    weg, folge = {}, []
    for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        if b.eilgang or abs(b.z - a.z) > 1e-9:
            continue
        z = round(b.z, 3)
        weg[z] = weg.get(z, 0.0) + bn.weg(a, b)
        if not folge or folge[-1] != z:
            folge.append(z)
    return weg, folge


pruefe(len(ebenen_bei(PLATTE, INSEL, STUFE, TASCHE)) == 4, "die vier ebenen Flächen")

# --- Räumen über die drei offenen Höhen ---------------------------------------------------------
bahn = raeumen(PLATTE, INSEL, STUFE)
weg, folge = vorschub_je_hoehe(bahn)
pruefe(bahn.flaechen == 3 and bahn.lagen == 3, f"{bahn.flaechen} Flächen, {bahn.lagen} Lagen")
# Die tiefste zuerst, jede Höhe einmal – außen um die Insel 23 mm in einer Lage.
pruefe(folge == [PLATTE, INSEL, STUFE], f"Reihenfolge der Höhen: {folge}")
pruefe(bahn.zeit < 13.0, f"Räumen über drei Höhen: {bahn.zeit:.1f} min – das Ziel sind 8")
# Die Insel oben und die obere Stufe nur noch über sich: vom Rohteil her wären es 8,8 und 8,5 m.
pruefe(weg[INSEL] < 3200.0, f"Insel oben: {weg[INSEL]:.0f} mm im Vorschub")
pruefe(weg[STUFE] < 1300.0, f"obere Stufe: {weg[STUFE]:.0f} mm im Vorschub")
# Im Quader abgefahren: nirgends ins Teil, auf den drei Flächen bleibt nichts stehen.
k = ps.messen(
    [ps.Bahnlauf(bahn.punkte, VF, VF * 0.3)], teil, ROHTEIL, OBEN, form, AE, AP,
    ebenen_z=[PLATTE, INSEL, STUFE], aufmass=0.3,
)  # fmt: skip
for satz in ps.urteile(k, sicher_nur=True):
    pruefe(False, f"Räumen über drei Höhen: {satz}")
print(f"Raeumen ueber drei Hoehen: {bahn.zeit:.2f} min ({bahn.zeiten}) – {ps.zeile(k)}")

# Jede Fläche für sich vom Rohteil her (so rechnete es bis 0.123.1): zusammen gut das Doppelte.
einzeln = sum(raeumen(z).zeit for z in (PLATTE, INSEL, STUFE))
pruefe(bahn.zeit < 0.6 * einzeln, f"zusammen {bahn.zeit:.1f} min, einzeln {einzeln:.1f} min")
print(f"jede Flaeche fuer sich: {einzeln:.2f} min")

# --- Der Boden der kleinen Tasche: Der Ø 12 passt nicht hinein (B-006) ----------------------------
try:
    raeumen(TASCHE)
except ValueError as grund:
    pruefe(len(str(grund)) > 10, "Tasche: kein Satz")
else:
    pruefe(False, "Tasche: eine Bahn, obwohl der Ø 12 nicht hineinpasst")
# Mit den anderen zusammen fällt sie aus; die drei offenen Flächen bleiben, wie sie sind.
alle = raeumen(PLATTE, INSEL, STUFE, TASCHE)
pruefe(
    alle.flaechen == 3 and abs(alle.zeit - bahn.zeit) < 0.05,
    f"mit der Tasche: {alle.flaechen} Flächen, {alle.zeit:.2f} min",
)

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
