# Der Prüfstand (W-006, Grundsatz 0 – Manuel, 2026-10-01: „die Werkzeugwege müssen sinnvoll
# sein und immer zum kürzesten Bearbeitungsergebnis führen, bei egal welcher Strategie … Finde
# einen Weg, das sicherzustellen … immer den definierten Fräser mit den definierten Werten und
# verschiedene Bahnen durchfahren“): Mit dem Standardfräser (Ø 12, ae 1,5, ap 25, vf 902) wird
# jede 2,5D-Strategie in jeder Variante an den Maßstabsteilen gerechnet und im Quader
# abgefahren – Manuels 50 × 50 mit Zapfen, der Block mit Absatz, der Block mit Tasche 40 × 30,
# die Platte 200 × 200 (Abschnitt 11). Jede Bahn muss bestehen (nirgends ins Teil, nichts
# stehen geblieben, im Eilgang nichts abgetragen, nicht zu viel Luft); jede Strategie nimmt von
# ihren Varianten die schnellste; zwischen den Strategien steht fest, welche gewinnt; und keine
# Bahn darf langsamer werden als ihre Bestmarke in tests/bestmarken.json (schneller immer –
# BESTMARKEN_SCHREIBEN=1 schreibt die Datei neu, der Verlauf sagt, warum). Die Tabelle am Ende
# zeigt je Bahn Zeit, Untergrenze und Wirkungsgrad, Luft, Eilgang, Halte, Eintauchen, Rampen.
import json
import os
import sys
import time

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import kontur_bahn as kb
from camaddon import planfraesen_bahn as pb
from camaddon import pruefstand as ps
from camaddon import raeumen as ra
from camaddon import raeumen_bahn as rb
from camaddon import sprache
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
DATEI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bestmarken.json")
SCHREIBEN = os.environ.get("BESTMARKEN_SCHREIBEN") == "1"
LANGSAMER_ZULAESSIG = 0.02  # so viel über der Bestmarke lässt die Rechnung schwanken
werkzeug = wz.standardwerkzeug()
R = werkzeug.durchmesser / 2
form = ff.scheibe(R)
planen = next(e for e in werkzeug.einsaetze(wz.ALLE) if e.art == wz.PLANEN)
schruppen = next(e for e in werkzeug.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
VF = 902.0  # mm/min bei vc 85, fz 0,1, 4 Schneiden
EINTAUCHEN = VF * 0.3
AE, AP = schruppen.ae, schruppen.ap


def rund_rechteck(x0, y0, x1, y1, r, z):
    kanten = [
        Part.makeLine(V(x0 + r, y0, z), V(x1 - r, y0, z)),
        Part.makeCircle(r, V(x1 - r, y0 + r, z), V(0, 0, 1), -90, 0),
        Part.makeLine(V(x1, y0 + r, z), V(x1, y1 - r, z)),
        Part.makeCircle(r, V(x1 - r, y1 - r, z), V(0, 0, 1), 0, 90),
        Part.makeLine(V(x1 - r, y1, z), V(x0 + r, y1, z)),
        Part.makeCircle(r, V(x0 + r, y1 - r, z), V(0, 0, 1), 90, 180),
        Part.makeLine(V(x0, y1 - r, z), V(x0, y0 + r, z)),
        Part.makeCircle(r, V(x0 + r, y0 + r, z), V(0, 0, 1), 180, 270),
    ]
    return Part.Wire(kanten)


# --- Die Maßstabsteile: (Teil, Rohteil von oben, Oberkante) --------------------------------
def teil_zapfen():
    teil = Part.makeBox(50, 50, 20).fuse(Part.makeCylinder(5, 10, V(25, 25, 20)))
    return teil.removeSplitter(), (-1.0, 51.0, -1.0, 51.0), 30.0


def teil_absatz():
    teil = Part.makeBox(60, 40, 20).fuse(Part.makeBox(10, 40, 5, V(0, 0, 20)))
    return teil.removeSplitter(), (-1.0, 61.0, -1.0, 41.0), 26.0


def teil_tasche():
    tasche = Part.Face(rund_rechteck(30, 15, 70, 45, 6, 5)).extrude(V(0, 0, 20))
    return Part.makeBox(100, 60, 20).cut(tasche).removeSplitter(), (-1.0, 101.0, -1.0, 61.0), 21.0


def teil_platte():
    platte = Part.makeBox(200, 200, 30, V(-100, -100, -30))
    zapfen = Part.makeCylinder(10, 20, V(50, 50, 0))
    tasche = Part.makeCylinder(22.5, 20, V(-50, -50, -20))
    teil = platte.fuse(zapfen).cut(tasche).removeSplitter()
    return teil, (-100.0, 100.0, -100.0, 100.0), 20.0


# --- Die Strategien, je mit dem Standardfräser --------------------------------------------
def ebenen_bei(teil, z):
    return [e for e in hf.ebenen_oben(teil) if abs(e.z - z) < 1e-6]


def waende_bei(teil, z_unten):
    namen = [f"Face{i + 1}" for i in range(len(teil.Faces))]
    return [w.name for w in kb.waende(teil, namen) if abs(w.z_unten - z_unten) < 1e-6]


def planfraesen(teil, z, rohteil, oben, laengs=None):
    ebenen = [
        e for zz in (z if isinstance(z, (list, tuple)) else [z]) for e in ebenen_bei(teil, zz)
    ]
    netz = hf.netze_je_hoehe(teil, ebenen)
    werte = pb.Planwerte(
        form, planen.ap, planen.ae, 0.0, oben, oben + 5.0, rohteil,
        laengs=laengs, vorschub=VF, eintauchen=EINTAUCHEN,
    )  # fmt: skip
    return pb.planen(netz, werte, ebenen)


def raeumen(teil, z, rohteil, oben, variante=None, gleichlauf=True):
    ebenen = [
        e for zz in (z if isinstance(z, (list, tuple)) else [z]) for e in ebenen_bei(teil, zz)
    ]
    netz = hf.netze_je_hoehe(teil, ebenen)
    werte = rb.Raeumwerte(
        form, AP, AE, 0.3, oben, oben + 5.0, rohteil,
        gleichlauf=gleichlauf, variante=variante, schneidenlaenge=werkzeug.schneidenlaenge,
        eintauchwinkel=werkzeug.eintauchwinkel, vorschub=VF, eintauchen=EINTAUCHEN,
    )  # fmt: skip
    return rb.planen(netz, werte, ebenen, ra.konturen_des_teils(teil))


def kontur(teil, waende, rohteil, oben, breite=0.0):
    konturen = kb.konturen(teil, waende)
    netz, fern = hf.netze_ohne(teil, [kb.ohne_flaechen(teil, kb.waende(teil, waende)), waende])
    werte = kb.Konturwerte(
        form, AP, AE, 0.3, True, oben, oben + 5.0, rohteil,
        breite=breite, schneidenlaenge=werkzeug.schneidenlaenge,
        eintauchwinkel=werkzeug.eintauchwinkel,
    )  # fmt: skip
    return kb.planen(netz, werte, konturen, netz_fern=fern)


def lauf(bahn):
    return ps.Bahnlauf(bahn.punkte, VF, EINTAUCHEN)


# --- Messen -----------------------------------------------------------------------------------
gemessen = {}  # Schlüssel → Kennzahlen
varianten = {}  # Schlüssel → {Variante: Minuten}
bestmarken = {}
if os.path.exists(DATEI):
    with open(DATEI, encoding="utf-8") as datei:
        bestmarken = json.load(datei)


def messe(
    schluessel,
    laeufe,
    teil,
    rohteil,
    oben,
    ebenen_z,
    aufmass=0.3,
    zeiten=None,
    tiefe=None,
    vorher=(),
    vergleich=False,
):
    """Misst und urteilt; `vergleich`: eine Folge, die nur zum Vergleich gemessen wird (die Luft
    zählt dann nicht als Fehler)."""
    anfang = time.time()
    k = ps.messen(
        laeufe,
        teil,
        rohteil,
        oben,
        form,
        AE,
        AP,
        ebenen_z=ebenen_z,
        aufmass=aufmass,
        tiefe=tiefe,
        vorher=vorher,
    )
    gemessen[schluessel] = k
    if zeiten:
        varianten[schluessel] = dict(zeiten)
    print(f"{schluessel:26} {ps.zeile(k)}  ({time.time() - anfang:.0f} s)")
    for satz in ps.urteile(k, sicher_nur=vergleich):
        pruefe(False, f"{schluessel}: {satz}")
    return k


# (a) Manuels 50 × 50 mit Zapfen: Planfräsen (beide Richtungen), Räumen (beide Varianten,
#     Gleichlauf und Gegenlauf), die Kontur um den Zapfen vom Rohteil her.
teil, rohteil, oben = teil_zapfen()
plan = planfraesen(teil, 20.0, rohteil, oben)
messe("zapfen/planfraesen", [lauf(plan)], teil, rohteil, oben, [20.0], 0.0,
      {"gewaehlt": plan.zeit, "andere": plan.zeit_andere})  # fmt: skip
pruefe(plan.zeit <= plan.zeit_andere + 1e-9, "Zapfen: Planfräsen nimmt die langsamere Richtung")
raeumt = raeumen(teil, 20.0, rohteil, oben)
messe("zapfen/raeumen", [lauf(raeumt)], teil, rohteil, oben, [20.0], 0.3, raeumt.zeiten)
pruefe(
    abs(raeumt.zeit - min(raeumt.zeiten.values())) < 1e-9,
    "Zapfen: Räumen nimmt die langsamere Variante",
)
gegen = raeumen(teil, 20.0, rohteil, oben, gleichlauf=False)
messe("zapfen/raeumen gegenlauf", [lauf(gegen)], teil, rohteil, oben, [20.0], 0.3, gegen.zeiten)
pruefe(
    abs(gegen.zeit - raeumt.zeit) < 0.1,
    f"Zapfen: Gegenlauf {gegen.zeit:.2f} min, Gleichlauf {raeumt.zeit:.2f}",
)
zapfenwand = waende_bei(teil, 20.0)
pruefe(len(zapfenwand) == 1, f"Zapfen: Wände {zapfenwand}")
kon = kontur(teil, zapfenwand, rohteil, oben)
messe("zapfen/kontur", [lauf(kon)], teil, rohteil, oben, [20.0], 0.0)
nach_raeumen = kontur(teil, zapfenwand, rohteil, oben, breite=0.3)
messe("zapfen/raeumen+kontur", [lauf(raeumt), lauf(nach_raeumen)], teil, rohteil, oben, [20.0], 0.0)
pruefe(
    gemessen["zapfen/raeumen"].zeit < gemessen["zapfen/planfraesen"].zeit
    and gemessen["zapfen/raeumen"].zeit < gemessen["zapfen/kontur"].zeit,
    "Zapfen: Räumen ist nicht die schnellste",
)

# (b) Der Block mit Absatz: hier gewinnt das Planfräsen.
teil, rohteil, oben = teil_absatz()
plan = planfraesen(teil, 20.0, rohteil, oben)
messe("absatz/planfraesen", [lauf(plan)], teil, rohteil, oben, [20.0], 0.0,
      {"gewaehlt": plan.zeit, "andere": plan.zeit_andere})  # fmt: skip
raeumt = raeumen(teil, 20.0, rohteil, oben)
messe("absatz/raeumen", [lauf(raeumt)], teil, rohteil, oben, [20.0], 0.3, raeumt.zeiten)
pruefe(
    abs(raeumt.zeit - min(raeumt.zeiten.values())) < 1e-9,
    "Absatz: Räumen nimmt die langsamere Variante",
)
pruefe(
    gemessen["absatz/planfraesen"].zeit < gemessen["absatz/raeumen"].zeit,
    "Absatz: Planfräsen ist nicht die schnellste",
)

# (c) Der Block mit Tasche 40 × 30: oben Planfräsen und Räumen; die Tasche mit der Kontur
#     allein oder Räumen und danach die Kontur mit Breite = Aufmaß.
teil, rohteil, oben = teil_tasche()
plan = planfraesen(teil, 20.0, rohteil, oben)
messe("tasche/planfraesen oben", [lauf(plan)], teil, rohteil, oben, [20.0], 0.0,
      {"gewaehlt": plan.zeit, "andere": plan.zeit_andere})  # fmt: skip
raeumt = raeumen(teil, 20.0, rohteil, oben)
messe("tasche/raeumen oben", [lauf(raeumt)], teil, rohteil, oben, [20.0], 0.3, raeumt.zeiten)
taschenwaende = waende_bei(teil, 5.0)
pruefe(len(taschenwaende) == 8, f"Tasche: Wände {len(taschenwaende)}")
kon = kontur(teil, taschenwaende, rohteil, oben)
messe("tasche/kontur", [lauf(kon)], teil, rohteil, oben, [5.0], 0.0, tiefe=15.0)
boden = raeumen(teil, 5.0, rohteil, oben)
messe("tasche/raeumen", [lauf(boden)], teil, rohteil, oben, [5.0], 0.3, boden.zeiten, 15.0)
nach_raeumen = kontur(teil, taschenwaende, rohteil, oben, breite=0.3)
messe(
    "tasche/raeumen+kontur",
    [lauf(boden), lauf(nach_raeumen)],
    teil,
    rohteil,
    oben,
    [5.0],
    0.0,
    tiefe=15.0,
)
pruefe(
    gemessen["tasche/raeumen+kontur"].zeit < gemessen["tasche/kontur"].zeit,
    "Tasche: Räumen + Kontur ist nicht schneller als die Kontur allein",
)

# (d) Manuels Platte (Abschnitt 11): oben Planfräsen und Räumen, die Tasche wie in (c), der
#     Zapfen zuletzt mit der Kontur bei Breite = Aufmaß.
teil, rohteil, oben = teil_platte()
plan = planfraesen(teil, 0.0, rohteil, oben)
messe("platte/planfraesen", [lauf(plan)], teil, rohteil, oben, [0.0], 0.0,
      {"gewaehlt": plan.zeit, "andere": plan.zeit_andere})  # fmt: skip
raeumt = raeumen(teil, 0.0, rohteil, oben)
messe("platte/raeumen", [lauf(raeumt)], teil, rohteil, oben, [0.0], 0.3, raeumt.zeiten)
pruefe(
    abs(raeumt.zeit - min(raeumt.zeiten.values())) < 1e-9,
    "Platte: Räumen nimmt die langsamere Variante",
)
pruefe(
    gemessen["platte/raeumen"].zeit < gemessen["platte/planfraesen"].zeit,
    "Platte: Räumen ist nicht die schnellste",
)
taschenwand = waende_bei(teil, -20.0)
zapfenwand = waende_bei(teil, 0.0)
pruefe(len(taschenwand) == 1 and len(zapfenwand) == 1, f"Platte: Wände {taschenwand}, {zapfenwand}")
# Die Tasche zuerst allein mit der Kontur – nach dem Räumen oben (`vorher`: so steht das Rohteil
# im Job da; die Kontur weiß es nicht und beginnt am Rohteil: viel Luft, nur zum Vergleich).
kon = kontur(teil, taschenwand, rohteil, oben)
messe(
    "platte/kontur tasche",
    [lauf(kon)],
    teil,
    rohteil,
    oben,
    [-20.0],
    0.0,
    tiefe=20.0,
    vorher=[lauf(raeumt)],
    vergleich=True,
)
# Dann so, wie der Assistent es anlegt: Räumen über beide Flächen in einer Bahn (die Tasche
# beginnt an ihrer Oberkante, weil die Oberseite in derselben Bahn vorher geräumt ist) und die
# Kontur mit Breite = Aufmaß.
beide = raeumen(teil, [0.0, -20.0], rohteil, oben)
pruefe(
    beide.flaechen == 2 and beide.lagen == 2,
    f"Platte: {beide.flaechen} Flächen, {beide.lagen} Lagen",
)
messe(
    "platte/raeumen oben+tasche",
    [lauf(beide)],
    teil,
    rohteil,
    oben,
    [0.0, -20.0],
    0.3,
    beide.zeiten,
    20.0,
)
# Planfräsen über beide Flächen: Im Taschenboden bleiben die Zeilen in der Tasche (aus einem Netz
# ohne beide Flächen sah der Boden neben sich keine Platte mehr – P-2026-10-01-26).
plan_beide = planfraesen(teil, [0.0, -20.0], rohteil, oben)
messe(
    "platte/planfraesen oben+tasche",
    [lauf(plan_beide)],
    teil,
    rohteil,
    oben,
    [0.0, -20.0],
    0.0,
    {"gewaehlt": plan_beide.zeit},
    20.0,
)
nach_raeumen = kontur(teil, taschenwand, rohteil, oben, breite=0.3)
messe(
    "platte/raeumen+kontur tasche",
    [lauf(nach_raeumen)],
    teil,
    rohteil,
    oben,
    [-20.0],
    0.0,
    tiefe=20.0,
    vorher=[lauf(beide)],
)
pruefe(
    gemessen["platte/raeumen oben+tasche"].zeit
    - gemessen["platte/raeumen"].zeit
    + gemessen["platte/raeumen+kontur tasche"].zeit
    < gemessen["platte/kontur tasche"].zeit,
    "Platte: Räumen + Kontur ist in der Tasche nicht schneller als die Kontur allein",
)
zapfen_kontur = kontur(teil, zapfenwand, rohteil, oben, breite=0.3)
messe(
    "platte/kontur zapfen",
    [lauf(zapfen_kontur)],
    teil,
    rohteil,
    oben,
    [0.0],
    0.0,
    tiefe=20.0,
    vorher=[lauf(beide)],
)
summe = (
    gemessen["platte/raeumen oben+tasche"].zeit
    + gemessen["platte/raeumen+kontur tasche"].zeit
    + gemessen["platte/kontur zapfen"].zeit
)
print(f"Platte gesamt (Raeumen oben und Tasche, Kontur Tasche, Kontur Zapfen): {summe:.1f} min")
pruefe(summe < 40.0, f"Platte: {summe:.1f} min gesamt – Abschnitt 11 verspricht etwa 35")

# --- Die Bestmarken: langsamer darf keine werden ---------------------------------------------
neu = {}
for schluessel, k in gemessen.items():
    neu[schluessel] = {
        "zeit": round(k.zeit, 3),
        "luft": round(k.luftanteil, 3),
        "wirkungsgrad": round(k.wirkungsgrad, 3),
        "halte": k.halte,
        "eintauchen": k.eintauchungen,
        "rampen": k.rampen,
    }
    if schluessel in varianten:
        neu[schluessel]["varianten"] = {n: round(z, 3) for n, z in varianten[schluessel].items()}
    best = bestmarken.get(schluessel)
    if best is None:
        print(f"ohne Bestmarke: {schluessel}")
        pruefe(SCHREIBEN, f"{schluessel}: keine Bestmarke – BESTMARKEN_SCHREIBEN=1 legt sie an")
        continue
    pruefe(
        k.zeit <= best["zeit"] * (1.0 + LANGSAMER_ZULAESSIG) + 1e-6,
        f"{schluessel}: {k.zeit:.2f} min, die Bestmarke ist {best['zeit']:.2f}",
    )
    pruefe(
        k.luftanteil <= best["luft"] + LANGSAMER_ZULAESSIG + 1e-6,
        f"{schluessel}: {k.luftanteil * 100:.0f} % Luft, die Bestmarke ist {best['luft'] * 100:.0f} %",
    )
    if k.zeit < best["zeit"] * (1.0 - LANGSAMER_ZULAESSIG):
        print(
            f"schneller als die Bestmarke: {schluessel} {k.zeit:.2f} statt {best['zeit']:.2f} min"
        )
if SCHREIBEN:
    with open(DATEI, "w", encoding="utf-8") as datei:
        json.dump(neu, datei, indent=2, ensure_ascii=False, sort_keys=True)
        datei.write("\n")
    print(f"Bestmarken geschrieben: {len(neu)}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
