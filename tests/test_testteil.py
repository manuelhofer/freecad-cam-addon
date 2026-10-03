# Prüft den Weg an Manuels Testteil für die 3-Achs-Fräse (W-013, Spezifikation Strategien,
# Abschnitt 13; Manuel, 2026-10-02: „das muss sinnvoll bearbeitet werden auch mit mehreren
# arbeitsschritten“): beispiele/testteil_3achs_fraese.FCStd – Platte 100 × 100 × 10, darauf eine
# Insel (z 10 … 22), auf ihr eine obere Stufe (z 22 … 32) mit einer dreieckigen Tasche (Boden
# z 27), in der Insel eine Kugelmulde. Rohteil 102 × 102 × 34, der Standardfräser Ø 12.
# Räumen über die drei offenen Höhen (T1): die tiefste Fläche zuerst – außen um die Insel, 23 tief
# in einer Lage –, die Insel oben danach nur noch über sich, um das, was noch steht, die obere
# Stufe zuletzt; ohne Rest, nirgends ins Teil. Mit den Ringen 12,4 min (jede Fläche für sich vom
# Rohteil her: 26 min), 56-mal abgehoben, und wo ein Ring an einer Wand beginnt, fährt der Fräser
# quer in den Streifen – bis 5 ae. Die schnellste, die die Last hält, ist „adaptiv“ (T5): unter
# 11,5 min, höchstens 10-mal abgehoben. Ohne Vorgabe gewinnt aber Manuels Räumen („stiche“,
# Spezifikation Strategien 14, P-2026-10-03-31/-32): Stiche von außen nach innen, Ringe um
# die Insel, an der Stufe wieder Stiche – lesbar, überall Gleichlauf, die Last
# gehalten; es hat den Vorzug, solange es höchstens 25 % langsamer ist (12,4 min; die Rückläufe
# zählen im Zeitmodell mit Halt vor und nach jedem Eilgang). Der Boden der kleinen Tasche: Der Ø 12 passt
# nicht hinein – ein Satz statt einer Bahn rund um die Insel (B-006); mit den anderen Flächen
# zusammen fällt sie aus, und die Bahn nennt sie (B-007).
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


def werte_fuer(variante=None):
    return rb.Raeumwerte(
        form, AP, AE, 0.3, OBEN, OBEN + 5.0, ROHTEIL, variante=variante,
        schneidenlaenge=werkzeug.schneidenlaenge, eintauchwinkel=werkzeug.eintauchwinkel,
        vorschub=VF, eintauchen=VF * 0.3,
    )  # fmt: skip


def raeumen(*hoehen, variante=None):
    ebenen = ebenen_bei(*hoehen)
    netz = hf.netze_je_hoehe(teil, ebenen)
    return rb.planen(netz, werte_fuer(variante), ebenen, ra.konturen_des_teils(teil))


def abgehoben(bahn):
    """So oft hebt die Bahn ab: Eilgänge nach einem Satz im Vorschub."""
    return sum(
        1 for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False) if b.eilgang and not a.eilgang
    )


def vorschub_je_hoehe(bahn):
    """{z: mm im Vorschub auf dieser Höhe} – ohne die Wege durchs Freie – und die Höhen in der
    Reihenfolge der Bahn."""
    weg, folge = {}, []
    for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        if b.eilgang or abs(b.z - a.z) > 1e-9 or b.anteil > 1.0:
            continue
        z = round(b.z, 3)
        weg[z] = weg.get(z, 0.0) + bn.weg(a, b)
        if not folge or folge[-1] != z:
            folge.append(z)
    return weg, folge


pruefe(len(ebenen_bei(PLATTE, INSEL, STUFE, TASCHE)) == 4, "die vier ebenen Flächen")
TASCHENBODEN = ebenen_bei(TASCHE)[0].name

# --- Räumen über die drei offenen Höhen ---------------------------------------------------------
bahn = raeumen(PLATTE, INSEL, STUFE)
weg, folge = vorschub_je_hoehe(bahn)
pruefe(bahn.flaechen == 3 and bahn.lagen == 3, f"{bahn.flaechen} Flächen, {bahn.lagen} Lagen")
pruefe(bahn.ausgelassen == [], f"ohne die Tasche ausgelassen: {bahn.ausgelassen}")
# Die tiefste zuerst, jede Höhe einmal – außen um die Insel 23 mm in einer Lage.
pruefe(folge == [PLATTE, INSEL, STUFE], f"Reihenfolge der Höhen: {folge}")
# Die schnellste Variante, die die Last hält: adaptiv – schneller als die Ringe, und es hebt kaum
# noch ab (mit den Ringen 56-mal). Den Vorzug hat Manuels Räumen („stiche“), bis 25 % langsamer.
pruefe(
    bahn.variante == rb.STICHE
    and bahn.zeiten["adaptiv"] < min(bahn.zeiten["rohteil"], 11.5)
    and bahn.zeit <= rb.STICHE_VORZUG * bahn.zeiten["adaptiv"]
    and bahn.zeit < 13.0,
    f"Räumen über drei Höhen: {bahn.variante}, {bahn.zeiten} – das Ziel sind 8 min",
)
# Um die Insel kehren die Stiche unten außen um das Rohteil zurück (Eilgang auf der Lage); auf
# der Insel oben (die Stufe als Wand am Rand) liegt zwischen dem Ende eines Stichs und dem
# Anfang des nächsten die Insel – dort hebt es ab (knapp über das Rohteil): rund 25-mal.
hinauf = sum(
    1
    for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False)
    if b.eilgang and not a.eilgang and b.z > a.z + 1.0
)
pruefe(hinauf <= 30, f"Räumen über drei Höhen: {hinauf}-mal hinaufgehoben")
pruefe(
    bahn.rampen == 0 and bahn.haelt,
    f"Räumen über drei Höhen: {bahn.rampen} Rampen, hält {bahn.haelt}",
)
groesste, lang = rb.last(bahn, werte_fuer())
pruefe(
    groesste <= bn.LAST_KURZ * rb.LAST_SPIEL and lang <= 2 * R,
    f"Last bis {groesste:.2f} ae, {lang:.1f} mm am Stück über {bn.LAST_DAUERND} ae",
)
# Die Insel oben und die obere Stufe nur noch über sich: vom Rohteil her wären es 8,8 und 8,5 m.
pruefe(weg[INSEL] < 3200.0, f"Insel oben: {weg[INSEL]:.0f} mm im Vorschub")
pruefe(weg[STUFE] < 1300.0, f"obere Stufe: {weg[STUFE]:.0f} mm im Vorschub")
# Im Quader abgefahren: nirgends ins Teil, auf den drei Flächen bleibt nichts stehen, wenig Luft.
k = ps.messen(
    [ps.Bahnlauf(bahn.punkte, VF, VF * 0.3)], teil, ROHTEIL, OBEN, form, AE, AP,
    ebenen_z=[PLATTE, INSEL, STUFE], aufmass=0.3,
)  # fmt: skip
for satz in ps.urteile(k):
    pruefe(False, f"Räumen über drei Höhen: {satz}")
print(
    f"Raeumen ueber drei Hoehen: {bahn.variante} {bahn.zeit:.2f} min ({bahn.zeiten}), {hinauf}-mal "
    f"hinauf, {abgehoben(bahn)} Rücklaeufe, Last bis {groesste:.2f} ae – {ps.zeile(k)}"
)
# Die Ringe (so rechnete es bis 0.125.5): langsamer, und sie halten die Last nicht.
ringe = raeumen(PLATTE, INSEL, STUFE, variante=rb.RINGE)
last_ringe, _lang = rb.last(ringe, werte_fuer(rb.RINGE))
pruefe(ringe.zeit < 13.0 and abgehoben(ringe) > 30, f"Ringe: {ringe.zeit:.1f} min")
pruefe(last_ringe > 2.0, f"Ringe: Last bis {last_ringe:.2f} ae – halten sie jetzt?")
print(
    f"mit den Ringen: {ringe.zeit:.2f} min, {abgehoben(ringe)}-mal abgehoben, Last bis {last_ringe:.2f} ae"
)

# Jede Fläche für sich vom Rohteil her (so rechnete es bis 0.123.1): zusammen gut das Doppelte.
einzeln = sum(raeumen(z).zeit for z in (PLATTE, INSEL, STUFE))
pruefe(bahn.zeit < 0.65 * einzeln, f"zusammen {bahn.zeit:.1f} min, einzeln {einzeln:.1f} min")
print(f"jede Flaeche fuer sich: {einzeln:.2f} min")

# --- Der Boden der kleinen Tasche: Der Ø 12 passt nicht hinein (B-006) ----------------------------
try:
    raeumen(TASCHE)
except ValueError as grund:
    pruefe(len(str(grund)) > 10, "Tasche: kein Satz")
else:
    pruefe(False, "Tasche: eine Bahn, obwohl der Ø 12 nicht hineinpasst")
# Mit den anderen zusammen fällt sie aus – und die Bahn sagt es (B-007); die drei offenen Flächen
# bleiben, wie sie sind.
alle = raeumen(PLATTE, INSEL, STUFE, TASCHE)
pruefe(
    alle.flaechen == 3 and abs(alle.zeit - bahn.zeit) < 0.05,
    f"mit der Tasche: {alle.flaechen} Flächen, {alle.zeit:.2f} min",
)
pruefe(alle.ausgelassen == [TASCHENBODEN], f"ausgelassen: {alle.ausgelassen}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
