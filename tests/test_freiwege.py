# Prüft „im Freien schnell“ (freiwege; Manuel, 2026-10-04: „wenn es frei ist und da kein Material
# ist … gib Gas bis kurz davor, bevor es wieder langsam weiter geht .. bei allen Strategien“).
# Ein Quader 0 … 40 × 0 … 40, oben z 10; der Fräser Ø 10 fährt auf z 5 von x −40 durch die Luft
# hinein und hindurch: draußen mit dem Freivorschub, die letzten 2 mm vor dem Material (die Stirn
# ab x −6, also bis x −8 schnell) langsam, im Material der Schnittvorschub; dahinter wieder
# schnell. Ein freies Stück unter 5 mm bleibt langsam, ein Eilgang bleibt Eilgang. Schon schnelle
# Rückwege (Anteil 3) werden noch schneller. Am Zapfen (Planfräsen, 50 × 50) wird die Bahn
# schneller, und wo sie schnell fährt, trägt sie nichts ab.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import bahn as bn
from camaddon import fraeserform as ff
from camaddon import freiwege as fw
from camaddon import hoehenfeld as hf
from camaddon import materialstand as mst
from camaddon import planfraesen_bahn as pb
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
V = FreeCAD.Vector
VF = 600.0
SCHNELL = fw.FREIVORSCHUB / VF


def quader():
    return rm.Quader(0.0, 40.0, 0.0, 40.0, 0.0, 10.0, mst.SCHRITT)


form = ff.scheibe(5.0)
P = bn.Punkt
bahn = [P(True, -40, 20, 20), P(True, -40, 20, 5), P(False, 60, 20, 5), P(True, 60, 20, 20)]
neu, weg = fw.schneller(bahn, form, quader(), VF)
saetze = [(round(p.x, 3), round(p.anteil, 3)) for p in neu if not p.eilgang]
print("Durch den Quader:", saetze, f"schnell {weg:.1f} mm")
schnell = [p for p in neu if not p.eilgang and math.isclose(p.anteil, SCHNELL)]
pruefe(schnell and min(p.x for p in schnell) <= -8.0 + 1.01, f"draußen nicht schnell: {saetze}")
# Der erste schnelle Satz endet 2 mm (± eine Sehne) vor x −6, wo die Stirn ans Material kommt.
erster = next((p for p in neu if not p.eilgang and math.isclose(p.anteil, SCHNELL)), None)
pruefe(erster is not None and -9.01 <= erster.x <= -7.99, f"vor dem Material: {saetze}")
im_material = [p for p in neu if not p.eilgang and 0 < p.x <= 40]
pruefe(all(p.anteil <= 1.0 for p in im_material), f"im Material schnell: {saetze}")
pruefe(any(p.x > 46 and math.isclose(p.anteil, SCHNELL) for p in neu), f"dahinter: {saetze}")
pruefe(30.0 <= weg <= 50.0, f"schneller Weg {weg:.1f} mm")
# Kurz (frei nur von x −10 bis −7, wo R + 1 mm bis ans Material reicht): bleibt langsam.
kurz = [P(True, -10, 20, 20), P(True, -10, 20, 5), P(False, 10, 20, 5), P(True, 10, 20, 20)]
neu_kurz, weg_kurz = fw.schneller(kurz, form, quader(), VF)
pruefe(weg_kurz == 0.0 and len(neu_kurz) == len(kurz), f"kurz: {weg_kurz}, {neu_kurz}")
# Schon schneller Rückweg (Anteil 3) unten durchs Freie: noch schneller.
rueck = [P(True, -40, 20, 20), P(True, -40, 20, 5), P(False, -40, 60, 5, False, None, 3.0)]
neu_rueck, _w = fw.schneller(rueck, form, quader(), VF)
pruefe(math.isclose(neu_rueck[-1].anteil, SCHNELL), f"Rückweg: {neu_rueck[-1]}")
# Ohne Vorschub oder mit einem Freivorschub nicht über dem Vorschub: unverändert.
pruefe(fw.schneller(bahn, form, quader(), 0.0)[0] == bahn, "ohne Vorschub verändert")

# --- Am Zapfen: Planfräsen --------------------------------------------------------------------
werkzeug = wz.standardwerkzeug()
R = werkzeug.durchmesser / 2
fraeser = ff.scheibe(R)
schruppen = next(e for e in werkzeug.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
teil = Part.makeBox(50, 50, 20).fuse(Part.makeCylinder(5, 10, V(25, 25, 20))).removeSplitter()
ROHTEIL, OBEN = (-1.0, 51.0, -1.0, 51.0), 30.0
ebenen = [e for e in hf.ebenen_oben(teil) if abs(e.z - 20.0) < 1e-6]
werte = pb.Planwerte(
    fraeser, schruppen.ap, schruppen.ae, 0.0, OBEN, OBEN + 5.0, ROHTEIL,
    eintauchwinkel=werkzeug.eintauchwinkel, vorschub=902.0, eintauchen=270.0,
)  # fmt: skip
plan = pb.planen(hf.netz_ohne(teil, [e.name for e in ebenen]), werte, ebenen)


def zapfen_quader():
    return rm.Quader(*ROHTEIL, 0.0, OBEN, mst.SCHRITT)


neu, weg = fw.schneller(plan.punkte, fraeser, zapfen_quader(), 902.0)
vorher, nachher = bn.zeit(plan.punkte, 902.0, 270.0), bn.zeit(neu, 902.0, 270.0)
print(f"Zapfen: {vorher:.2f} → {nachher:.2f} min, schnell {weg / 1000:.2f} m")
pruefe(nachher < vorher - 0.2, f"Zapfen nicht schneller: {vorher:.2f} → {nachher:.2f}")
q = zapfen_quader()
zelle = (q.x[1] - q.x[0]) * (q.y[1] - q.y[0])
abtrag = 0.0
for von, nach in zip(neu, neu[1:], strict=False):
    for a, b in fw._sehnen(von, nach):
        vor = q.h.copy()
        if not nach.eilgang:
            q.fahre_stuecke([a], [b], fraeser)
        if not nach.eilgang and nach.anteil > 1.0 + 1e-9:
            abtrag += float((vor - q.h).clip(min=0).sum()) * zelle
pruefe(abtrag < 1e-6, f"im Schnellen abgetragen: {abtrag:.3f} mm³")

# --- Der Freivorschub aus der Maschine (Manuel: „wenn nichts drinnen steht .. dann halt 10 m/min“)
from camaddon import PARAMETER_PFAD  # noqa: E402
from camaddon import maschinenspeicher as msp  # noqa: E402
from camaddon import reichweite as rw  # noqa: E402

datei = os.path.join(os.path.dirname(msp.datei_pfad()), "freiwege_maschine.FCStd")
for hoechst, soll in ((6000.0, 6000.0), (0.0, fw.FREIVORSCHUB)):
    msp.speichern([msp.Eintrag("Fräse", datei, vorschub=hoechst)])
    FreeCAD.ParamGet(PARAMETER_PFAD).SetString(rw.ZULETZT_MASCHINE, datei)
    pruefe(
        fw.freivorschub_fuer(None) == soll,
        f"Freivorschub {fw.freivorschub_fuer(None)} statt {soll}",
    )
FreeCAD.ParamGet(PARAMETER_PFAD).SetString(rw.ZULETZT_MASCHINE, "")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
