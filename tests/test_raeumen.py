# Prüft „Räumen“ (W-006 S3f): Manuels Standardfräser Ø 12 (ae 1,5, ap 25) räumt vier Teile –
# Block 50 × 50 × 20 mit Zapfen Ø 10 in der Mitte (Manuels Beispiel), Block 60 × 40 × 20 mit
# Absatz (test_planfraesen), Block 100 × 60 × 20 mit Tasche 40 × 30 R 6 (test_kontur) und
# Manuels Platte 200 × 200 mit Zapfen und Tasche. Je Teil: die Ringe und Läufe, Eintauchen nur
# im Freien oder in der Luft (Rampen nur, wo nichts frei ist), die Simulation im Quader –
# nirgends ins Teil, auf der Fläche bleibt nichts stehen außer dem Aufmaß an Wänden –, die
# Varianten und ihre Zeit: auf der Platte schlägt Räumen das Planfräsen, in der Tasche die
# Kontur; Gleichlauf (M3: im Uhrzeigersinn auf der Oberseite) und Gegenlauf; Fehler mit
# einem Satz; dann die CAM-Operation im Job: angelegt, gerechnet, geändert, gespeichert und
# geladen.
import math
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import bahn as bn
from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import job_schnittwerte as js
from camaddon import kontur_bahn as kb
from camaddon import planfraesen_bahn as pb
from camaddon import pruefstand as ps
from camaddon import raeumen as ra
from camaddon import raeumen_bahn as rb
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_huelle as vh
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
werkzeug = wz.standardwerkzeug()
R = werkzeug.durchmesser / 2
form = ff.scheibe(R)
schruppen = next(e for e in werkzeug.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
VF = 902.0  # mm/min bei vc 85, fz 0,1, 4 Schneiden


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


def werte_fuer(rohteil, oben, aufmass=0.3, variante=rb.RINGE, gleichlauf=True):
    """Die Werte – ohne Angabe für die Ringe (die schnellste Variante von ihnen): Die Abschnitte
    (a) bis (g) prüfen die Ringe; die Wahl mit dem Adaptiv-Kern prüft (h) mit `variante=None`."""
    return rb.Raeumwerte(
        form,
        schruppen.ap,
        schruppen.ae,
        aufmass,
        oben,
        oben + 5.0,
        rohteil,
        gleichlauf=gleichlauf,
        variante=variante,
        schneidenlaenge=werkzeug.schneidenlaenge,
        eintauchwinkel=werkzeug.eintauchwinkel,
        vorschub=VF,
        eintauchen=VF * 0.3,
    )


def raeumen(teil, flaeche_z, werte):
    ebenen = [e for e in hf.ebenen_oben(teil) if abs(e.z - flaeche_z) < 1e-6]
    netz = hf.netz_ohne(teil, [e.name for e in ebenen])
    return rb.planen(netz, werte, ebenen, ra.konturen_des_teils(teil))


def simuliert(bahn, teil, rohteil, oben, flaeche_z, aufmass):
    """(größter Rest auf der Fläche abseits der Wände, tiefster Einschnitt ins Teil) nach der
    Simulation aller Sätze – auch der Eilgänge – im Quader des Rohteils."""
    x0, x1, y0, y1 = rohteil
    q = rm.Quader(x0, x1, y0, y1, -100.0, oben, 0.5)
    von, nach = [], []
    for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        if b.bogen is None:
            von.append((a.x, a.y, a.z))
            nach.append((b.x, b.y, b.z))
            continue
        n = max(2, int(math.ceil(bn.weg(a, b) / 0.5)))
        mx, my, uhr = b.bogen
        a0 = math.atan2(a.y - my, a.x - mx)
        winkel = bn.winkel(a, b)
        rad = math.hypot(a.x - mx, a.y - my)
        vorher = (a.x, a.y, a.z)
        for i in range(1, n + 1):
            t = i / n
            w = a0 - t * winkel if uhr else a0 + t * winkel
            jetzt = (mx + rad * math.cos(w), my + rad * math.sin(w), a.z + (b.z - a.z) * t)
            von.append(vorher)
            nach.append(jetzt)
            vorher = jetzt
    q.fahre_stuecke(von, nach, R)
    teilhoehe = rm.teilhoehen(vh.vernetze(teil), q)
    da = np.isfinite(teilhoehe)
    unterschied = np.where(da, q.h - teilhoehe, np.nan)
    hoch = da & (teilhoehe > flaeche_z + 0.01)
    flaeche = da & (np.abs(teilhoehe - flaeche_z) < 0.01)
    nah = np.zeros_like(hoch)
    m = int(math.ceil((aufmass + 0.75) / 0.5))
    for di in range(-m, m + 1):
        for dj in range(-m, m + 1):
            if di * di + dj * dj <= m * m:
                nah |= np.roll(np.roll(hoch, di, 0), dj, 1)
    weit = flaeche & ~nah
    rest = float(np.nanmax(unterschied[weit])) if weit.any() else 0.0
    einschnitt = float(np.nanmin(unterschied)) if da.any() else 0.0
    return rest, einschnitt


def umlauf(punkte):
    summe = 0.0
    for (x0, y0), (x1, y1) in zip(punkte, punkte[1:] + punkte[:1], strict=False):
        summe += x0 * y1 - x1 * y0
    return summe / 2


def erster_ring(bahn, lage):
    """(x, y) des ersten Laufs in der Tiefe – vom ersten Eintauchen bis zum nächsten Eilgang."""
    punkte = []
    drin = False
    for p in bahn.punkte:
        if p.eintauchen and not drin:
            drin = True
            continue
        if drin and p.eilgang:
            break
        if drin and abs(p.z - lage) < 1e-9:
            punkte.append((p.x, p.y))
    return punkte


# --- (a) Manuels Beispiel: 50 × 50 × 20, Zapfen Ø 10 × 10 in der Mitte ----------------------
teil_a = Part.makeBox(50, 50, 20).fuse(Part.makeCylinder(5, 10, V(25, 25, 20))).removeSplitter()
rohteil_a = (-1.0, 51.0, -1.0, 51.0)
bahn_a = raeumen(teil_a, 20.0, werte_fuer(rohteil_a, 30.0))
# Der Morph gewinnt (Manuel: „im Viereck anfangen, aber immer runder werden, so dass er am Ende
# nur um den Zapfen fährt“): eine Spirale ohne Absetzen, schneller als die Ringe um den Rest.
pruefe(bahn_a.variante == "morph", f"Zapfen: Variante {bahn_a.variante} {bahn_a.zeiten}")
pruefe(set(bahn_a.zeiten) == {"rohteil", "morph", "inseln"}, f"Zapfen: Varianten {bahn_a.zeiten}")
pruefe(
    bahn_a.zeiten["rohteil"] < bahn_a.zeiten["inseln"]
    and abs(bahn_a.zeit - min(bahn_a.zeiten.values())) < 1e-9,
    f"Zapfen: Zeiten {bahn_a.zeiten}",
)
# Der Morph (Manuel: „im Viereck anfangen, aber immer runder werden“): eine Spirale ohne
# Absetzen – ein Eingang, keine Rampe, sonst nur Anschlüsse.
bahn_m = raeumen(teil_a, 20.0, werte_fuer(rohteil_a, 30.0, variante="morph"))
pruefe(
    bahn_m.rampen == 0 and bahn_m.einfahrten == 1 and bahn_m.anschluesse == bahn_m.laeufe - 1,
    f"morph: {bahn_m.rampen} Rampen, {bahn_m.einfahrten} Einfahrten, {bahn_m.anschluesse} Anschlüsse, {bahn_m.laeufe} Läufe",
)
pruefe(bahn_m.zeit < bahn_a.zeit * 1.15, f"morph: {bahn_m.zeit} min, rohteil {bahn_a.zeit}")
rest, einschnitt = simuliert(bahn_m, teil_a, rohteil_a, 30.0, 20.0, 0.3)
pruefe(rest <= 0.05 and einschnitt >= -0.05, f"morph: Rest {rest}, Einschnitt {einschnitt}")
# Vom Rand des Rohteils her bis an den Zapfen: etwa 15 Umläufe – die Spirale in einem Zug, dann
# der Ring um den Zapfen, der ohne Absatz anschließt.
pruefe(
    (bahn_a.flaechen, bahn_a.lagen) == (1, 1) and 12 <= bahn_a.ringe <= 18,
    f"Zapfen: {bahn_a.flaechen} Flächen, {bahn_a.lagen} Lagen, {bahn_a.ringe} Ringe",
)
pruefe(
    (bahn_a.laeufe, bahn_a.einfahrten, bahn_a.anschluesse, bahn_a.rampen) == (2, 1, 1, 0),
    f"Zapfen: {bahn_a.laeufe} Läufe, {bahn_a.einfahrten} Einfahrten, "
    f"{bahn_a.anschluesse} Anschlüsse, {bahn_a.rampen} Rampen – {bahn_a.rampen_bei}",
)
# Der letzte Ring ist der genaue Kreis um den Zapfen (Radius 5 + R + Aufmaß), mit Bögen; vor
# ihm wird die Spirale von Umlauf zu Umlauf runder: Das Verhältnis der Ecke zur Seite (Abstand
# zur Mitte auf der Diagonalen ÷ auf der Achse) fällt von √2 zum Kreis hin auf 1.
kreis = [
    p for p in bahn_a.punkte if not p.eilgang and abs(math.hypot(p.x - 25, p.y - 25) - 11.3) < 0.01
]
pruefe(len(kreis) >= 2, f"Zapfen: {len(kreis)} Punkte auf dem Kreis um den Zapfen")
pruefe(
    any(p.bogen is not None for p in kreis),
    "Zapfen: der Kreis um den Zapfen ohne Bögen",
)
spirale = []
for a, b in zip(bahn_a.punkte, bahn_a.punkte[1:], strict=False):
    if b.eilgang or abs(a.z - 20) > 1e-9 or abs(b.z - 20) > 1e-9:
        continue
    if b.bogen is None:
        spirale.append((b.x - 25, b.y - 25))
        continue
    mx, my, uhr = b.bogen  # Bögen dicht abtasten – der Kreis um den Zapfen hat nur zwei
    a0, rad, bogen = math.atan2(a.y - my, a.x - mx), math.hypot(a.x - mx, a.y - my), bn.winkel(a, b)
    for i in range(1, 65):
        w_ = a0 - bogen * i / 64 if uhr else a0 + bogen * i / 64
        spirale.append((mx + rad * math.cos(w_) - 25, my + rad * math.sin(w_) - 25))


# Entlang der Bahn den Winkel um die Mitte abwickeln und bei jedem Achtel den Radius nehmen:
# Achse (0°, 90° …) und die folgende Diagonale gehören zum selben Umlauf. Je Umlauf zählt das
# größte Verhältnis – im Viertel, in dem die Spirale zum nächsten Ring gleitet, fällt der Radius
# um einen ganzen Schritt.
winkel = [math.atan2(spirale[0][1], spirale[0][0])]
for (x1, y1), (x2, y2) in zip(spirale, spirale[1:], strict=False):
    winkel.append(
        winkel[-1] + (math.atan2(y2, x2) - math.atan2(y1, x1) + math.pi) % (2 * math.pi) - math.pi
    )
radien = [math.hypot(x, y) for x, y in spirale]
kreuzungen = []  # (Vielfaches von 45°, Radius) in der Reihenfolge der Bahn
for i in range(len(winkel) - 1):
    a, b = winkel[i], winkel[i + 1]
    if abs(b - a) < 1e-12:
        continue
    for m in range(math.ceil(min(a, b) / (math.pi / 4)), math.floor(max(a, b) / (math.pi / 4)) + 1):
        if kreuzungen and kreuzungen[-1][0] == m:
            continue
        t = (m * math.pi / 4 - a) / (b - a)
        kreuzungen.append((m, radien[i] + t * (radien[i + 1] - radien[i])))
je_umlauf = {}
for (m1, r1), (m2, r2) in zip(kreuzungen, kreuzungen[1:], strict=False):
    if m1 % 2 == 0 and abs(m2 - m1) == 1:
        je_umlauf[m1 // 8] = max(je_umlauf.get(m1 // 8, 0.0), r2 / r1)
verhaeltnisse = [round(je_umlauf[k], 3) for k in sorted(je_umlauf, reverse=winkel[-1] < winkel[0])]
pruefe(
    len(verhaeltnisse) >= 8
    and verhaeltnisse[0] > 1.25
    and verhaeltnisse[-1] < 1.05
    and all(a >= b - 0.03 for a, b in zip(verhaeltnisse, verhaeltnisse[1:], strict=False)),
    f"Zapfen: die Spirale wird nicht runder: {verhaeltnisse}",
)
pruefe(abs(bahn_a.z_min - 20.0) < 1e-9, f"Zapfen: z_min {bahn_a.z_min}")
# Der erste Ring liegt außen in der Luft (Mitte R − ae = 4,5 außerhalb des Rohteils), im
# Gleichlauf im Uhrzeigersinn (Spindel rechtsdrehend, M3: das Material rechts); der Fräser
# taucht im Freien ein und fährt tangential
# hinein (kein Punkt zwischen den Lagen = keine Rampe).
ring = erster_ring(bahn_a, 20.0)
pruefe(len(ring) > 8 and umlauf(ring) < 0, f"Zapfen: erster Ring {len(ring)} Punkte, Umlauf")
pruefe(
    min(p[0] for p in ring) <= -5.5 + 1e-6 and max(p[0] for p in ring) >= 55.5 - 1e-6,
    f"Zapfen: erster Ring x {min(p[0] for p in ring)} … {max(p[0] for p in ring)}",
)
zwischen = [p for p in bahn_a.punkte if not p.eilgang and 20.0 + 1e-6 < p.z < 30.0 - 1e-6]
pruefe(not zwischen, f"Zapfen: {len(zwischen)} Punkte zwischen den Lagen (Rampe)")
rest, einschnitt = simuliert(bahn_a, teil_a, rohteil_a, 30.0, 20.0, 0.3)
pruefe(rest <= 0.05, f"Zapfen: Rest {rest}")
pruefe(einschnitt >= -0.05, f"Zapfen: Einschnitt {einschnitt}")
pruefe(bahn_a.punkte[0].eilgang and bahn_a.punkte[-1].eilgang, "Zapfen: Anfang und Ende")
pruefe(
    abs(bahn_a.punkte[0].z - 35.0) < 1e-9 and abs(bahn_a.punkte[-1].z - 35.0) < 1e-9,
    "Zapfen: Anfang und Ende oben",
)
befehle = bn.befehle(bahn_a.punkte, VF, VF * 0.3)
pruefe({"G0", "G1"} <= {b.Name for b in befehle}, "Zapfen: Befehle")
# Gegenlauf: der erste Ring gegen den Uhrzeigersinn.
bahn_g = raeumen(teil_a, 20.0, werte_fuer(rohteil_a, 30.0, gleichlauf=False))
ring_g = erster_ring(bahn_g, 20.0)
pruefe(len(ring_g) > 8 and umlauf(ring_g) > 0, "Gegenlauf: erster Ring gegen den Uhrzeigersinn")
pruefe(abs(bahn_g.zeit - bahn_a.zeit) < 0.5, f"Gegenlauf: Zeit {bahn_g.zeit} statt {bahn_a.zeit}")
# Die Variante vorgegeben: nur sie wird gerechnet.
bahn_i = raeumen(teil_a, 20.0, werte_fuer(rohteil_a, 30.0, variante="inseln"))
pruefe(
    bahn_i.variante == "inseln" and set(bahn_i.zeiten) == {"inseln"}, f"nur inseln: {bahn_i.zeiten}"
)
rest, einschnitt = simuliert(bahn_i, teil_a, rohteil_a, 30.0, 20.0, 0.3)
pruefe(rest <= 0.05 and einschnitt >= -0.05, f"inseln: Rest {rest}, Einschnitt {einschnitt}")
# Zum Vergleich das Planfräsen mit denselben Werten – die Zeit entscheidet im Assistenten.
ebenen_a = [e for e in hf.ebenen_oben(teil_a) if abs(e.z - 20.0) < 1e-6]
plan_a = pb.planen(
    hf.netz_ohne(teil_a, [e.name for e in ebenen_a]),
    pb.Planwerte(
        form,
        schruppen.ap,
        schruppen.ae,
        0.0,
        30.0,
        35.0,
        rohteil_a,
        vorschub=VF,
        eintauchen=VF * 0.3,
    ),
    ebenen_a,
)
print(
    f"Zapfen 50x50: Raeumen {bahn_a.zeit:.2f} min ({bahn_a.zeiten}), Planfraesen {plan_a.zeit:.2f} min"
)
print("Zapfen ok")

# --- (b) Block mit Absatz: der Absatz ist gesperrt, die Ringe halten davor an ----------------
teil_b = Part.makeBox(60, 40, 20).fuse(Part.makeBox(10, 40, 5, V(0, 0, 20))).removeSplitter()
rohteil_b = (-1.0, 61.0, -1.0, 41.0)
bahn_b = raeumen(teil_b, 20.0, werte_fuer(rohteil_b, 26.0))
pruefe(
    bahn_b.flaechen == 1 and bahn_b.lagen == 1 and bahn_b.ringe >= 15,
    f"Absatz: {bahn_b.ringe} Ringe",
)
pruefe(bahn_b.rampen <= 1, f"Absatz: {bahn_b.rampen} Rampen – {bahn_b.rampen_bei}")
# Die Spitze bleibt R + Aufmaß vom Absatz (x 0 … 10, y 0 … 40) weg – auch um seine Ecken.
drin = [p for p in bahn_b.punkte if not p.eilgang and abs(p.z - 20.0) < 1e-9]
abstand = min(
    math.hypot(max(0.0 - p.x, 0.0, p.x - 10.0), max(0.0 - p.y, 0.0, p.y - 40.0)) for p in drin
)
pruefe(abstand >= R + 0.3 - 0.3, f"Absatz: Abstand {abstand}")
rest, einschnitt = simuliert(bahn_b, teil_b, rohteil_b, 26.0, 20.0, 0.3)
pruefe(rest <= 0.05 and einschnitt >= -0.05, f"Absatz: Rest {rest}, Einschnitt {einschnitt}")
print("Absatz ok")

# --- (c) Die Tasche 40 × 30 R 6, 15 tief: von innen nach außen, eine Rampe rundum ------------
tasche = Part.Face(rund_rechteck(30, 15, 70, 45, 6, 5)).extrude(V(0, 0, 20))
teil_c = Part.makeBox(100, 60, 20).cut(tasche).removeSplitter()
rohteil_c = (-1.0, 101.0, -1.0, 61.0)
namen_c = [f"Face{i + 1}" for i in range(len(teil_c.Faces))]
boden_c = next(e.name for e in hf.ebenen_oben(teil_c) if abs(e.z - 5.0) < 1e-6)
waende_c = [w.name for w in kb.waende(teil_c, namen_c) if abs(w.z_unten - 5.0) < 1e-6]
pruefe(
    rb.taschenboeden(teil_c, waende_c) == [boden_c],
    f"Taschenboden: {rb.taschenboeden(teil_c, waende_c)}",
)
aussen_c = [w.name for w in kb.waende(teil_c, namen_c) if abs(w.z_unten) < 1e-6]
pruefe(rb.taschenboeden(teil_c, aussen_c) == [], "Außenwände sind keine Tasche")
bahn_c = raeumen(teil_c, 5.0, werte_fuer(rohteil_c, 21.0))
pruefe(bahn_c.variante == "inseln" and set(bahn_c.zeiten) == {"inseln"}, f"Tasche: {bahn_c.zeiten}")
# Die Lagen beginnen an der Oberkante der Wände (20), nicht am Rohteil (21): 15 mm, eine Lage.
pruefe(
    bahn_c.lagen == 1 and abs(bahn_c.z_min - 5.0) < 1e-9,
    f"Tasche: {bahn_c.lagen} Lagen, z_min {bahn_c.z_min}",
)
pruefe(
    5 <= bahn_c.ringe <= 7 and bahn_c.laeufe == bahn_c.ringe,
    f"Tasche: {bahn_c.ringe} Ringe, {bahn_c.laeufe} Läufe",
)
pruefe(
    bahn_c.rampen == 1 and bahn_c.anschluesse == bahn_c.ringe - 1,
    f"Tasche: {bahn_c.rampen} Rampen, {bahn_c.anschluesse} Anschlüsse",
)
# Alle Punkte in der Tasche: höchstens R + Aufmaß vor den Wänden; die Rampe beginnt unter 20.
in_tasche = [p for p in bahn_c.punkte if not p.eilgang]
pruefe(
    all(
        30 + R + 0.3 - 0.3 <= p.x <= 70 - R - 0.3 + 0.3 and 15 + R <= p.y <= 45 - R
        for p in in_tasche
    ),
    f"Tasche: x {min(p.x for p in in_tasche)} … {max(p.x for p in in_tasche)}, "
    f"y {min(p.y for p in in_tasche)} … {max(p.y for p in in_tasche)}",
)
# Allein gewählt, beginnt die Tasche am Rohteil (21): Ob die Oberseite darüber schon geräumt
# ist, weiß die Bahn nicht (P-2026-10-01-26).
pruefe(
    max(p.z for p in in_tasche) <= 21.0 + 1e-9,
    f"Tasche: Vorschub bis {max(p.z for p in in_tasche)}",
)
# Die Rampe rundum: Punkte zwischen 20 und 5, kein Zickzack (die x-y-Folge läuft in einer
# Richtung um die Tasche: der Umlauf der Rampe ist gegen den Uhrzeigersinn wie der Ring).
rampe = [(p.x, p.y) for p in in_tasche if 5.0 + 1e-6 < p.z < 20.0 - 1e-6]
pruefe(len(rampe) > 10 and umlauf(rampe) > 0, f"Tasche: Rampe {len(rampe)} Punkte, Umlauf")
rest, einschnitt = simuliert(bahn_c, teil_c, rohteil_c, 21.0, 5.0, 0.3)
pruefe(rest <= 0.05 and einschnitt >= -0.05, f"Tasche: Rest {rest}, Einschnitt {einschnitt}")
# Gegen die Kontur mit denselben Werten (Versätze in Lagen, je mit Rampe): Räumen ist schneller.
konturen_c = kb.konturen(teil_c, waende_c)
netz_nah, netz_fern = hf.netze_ohne(
    teil_c, [kb.ohne_flaechen(teil_c, kb.waende(teil_c, waende_c)), waende_c]
)
kontur_c = kb.planen(
    netz_nah,
    kb.Konturwerte(
        form,
        schruppen.ap,
        schruppen.ae,
        0.3,
        False,
        21.0,
        26.0,
        rohteil_c,
        schneidenlaenge=26.0,
        eintauchwinkel=3.0,
    ),
    konturen_c,
    netz_fern=netz_fern,
)
zeit_kontur = bn.zeit(kontur_c.punkte, VF, VF * 0.3)
pruefe(bahn_c.zeit < zeit_kontur, f"Tasche: Räumen {bahn_c.zeit} min, Kontur {zeit_kontur} min")
print(f"Tasche: Raeumen {bahn_c.zeit:.2f} min, Kontur (ohne Schlichten) {zeit_kontur:.2f} min")
print("Tasche ok")

# --- (d) Manuels Platte: Räumen schlägt das Planfräsen, die Tasche die Kontur -------------------
platte = Part.makeBox(200, 200, 30, V(-100, -100, -30))
zapfen = Part.makeCylinder(10, 20, V(50, 50, 0))
tasche_d = Part.makeCylinder(22.5, 20, V(-50, -50, -20))
teil_d = platte.fuse(zapfen).cut(tasche_d).removeSplitter()
rohteil_d = (-100.0, 100.0, -100.0, 100.0)
bahn_d = raeumen(teil_d, 0.0, werte_fuer(rohteil_d, 20.0))
ebenen_d = [e for e in hf.ebenen_oben(teil_d) if abs(e.z) < 1e-6]
plan_d = pb.planen(
    hf.netz_ohne(teil_d, [e.name for e in ebenen_d]),
    pb.Planwerte(
        form,
        schruppen.ap,
        schruppen.ae,
        0.0,
        20.0,
        25.0,
        rohteil_d,
        vorschub=VF,
        eintauchen=VF * 0.3,
    ),
    ebenen_d,
)
print(
    f"Platte oben: Raeumen {bahn_d.zeit:.1f} min ({bahn_d.zeiten}), Planfraesen {plan_d.zeit:.1f} min"
)
pruefe(bahn_d.variante == "rohteil", f"Platte: Variante {bahn_d.variante} {bahn_d.zeiten}")
# Seit das Planfräsen Zelle für Zelle fährt (P-2026-10-03-29: 35,2 statt 41,9 min), liegt das
# Räumen nur noch 4 % davor (33,8 min) – es schlägt es, mehr nicht.
pruefe(
    bahn_d.zeit < plan_d.zeit,
    f"Platte: Räumen {bahn_d.zeit} min, Planfräsen {plan_d.zeit} min",
)
pruefe(bahn_d.zeit < 36.0, f"Platte: {bahn_d.zeit} min (Abschnitt 11: etwa 33)")
pruefe(
    bahn_d.rampen <= 1 and bahn_d.lagen == 1,
    f"Platte: {bahn_d.rampen} Rampen, {bahn_d.lagen} Lagen",
)
rest, einschnitt = simuliert(bahn_d, teil_d, rohteil_d, 20.0, 0.0, 0.3)
pruefe(rest <= 0.05 and einschnitt >= -0.05, f"Platte: Rest {rest}, Einschnitt {einschnitt}")
# Die Tasche allein: vom Rohteil (20) bis −20, zwei Lagen, je eine Rampe rundum.
bahn_e = raeumen(teil_d, -20.0, werte_fuer(rohteil_d, 20.0))
pruefe(
    bahn_e.variante == "inseln" and bahn_e.lagen == 2 and bahn_e.rampen == 2,
    f"Platte Tasche: {bahn_e.zeiten}, {bahn_e.lagen} Lagen, {bahn_e.rampen} Rampen",
)
pruefe(bahn_e.zeit < 3.0, f"Platte Tasche: {bahn_e.zeit} min")
rest, einschnitt = simuliert(bahn_e, teil_d, rohteil_d, 20.0, -20.0, 0.3)
pruefe(rest <= 0.05 and einschnitt >= -0.05, f"Platte Tasche: Rest {rest}, Einschnitt {einschnitt}")
print(f"Platte Tasche: Raeumen {bahn_e.zeit:.2f} min")
# Oberseite und Tasche in einer Bahn: Die Tasche beginnt an ihrer Oberkante (0), eine Lage.
ebenen_f = [e for e in hf.ebenen_oben(teil_d) if abs(e.z) < 1e-6 or abs(e.z + 20.0) < 1e-6]
bahn_f = rb.planen(
    hf.netze_je_hoehe(teil_d, ebenen_f),
    werte_fuer(rohteil_d, 20.0),
    ebenen_f,
    ra.konturen_des_teils(teil_d),
)
pruefe(
    bahn_f.flaechen == 2 and bahn_f.lagen == 2 and abs(bahn_f.z_min + 20.0) < 1e-9,
    f"Platte beide: {bahn_f.flaechen} Flächen, {bahn_f.lagen} Lagen, z_min {bahn_f.z_min}",
)
pruefe(
    bahn_f.zeit < bahn_d.zeit + 1.6,
    f"Platte beide: {bahn_f.zeit:.2f} min, oben {bahn_d.zeit:.2f} min",
)
rest, einschnitt = simuliert(bahn_f, teil_d, rohteil_d, 20.0, -20.0, 0.3)
pruefe(rest <= 0.05 and einschnitt >= -0.05, f"Platte beide: Rest {rest}, Einschnitt {einschnitt}")
print(f"Platte beide: Raeumen {bahn_f.zeit:.2f} min")
print("Platte ok")

# --- (e) Eine Tasche in einer Insel: daneben liegt das Teil tiefer als ihr Boden ---------------
# Manuels Testteil (2026-10-02): Der Boden der kleinen Tasche oben auf der Insel räumte rund um
# die Insel – überall, wo das Teil tiefer liegt als der Boden. Die Tasche endet an ihren Wänden.
insel_e = Part.makeBox(50, 40, 15, V(25, 10, 20))  # die Insel von z 20 bis 35
tasche_e = Part.Face(rund_rechteck(35, 17, 65, 43, 7, 30)).extrude(V(0, 0, 5))  # Boden bei 30
teil_e = Part.makeBox(100, 60, 20).fuse(insel_e).cut(tasche_e).removeSplitter()
rohteil_e = (-1.0, 101.0, -1.0, 61.0)
bahn_t = raeumen(teil_e, 30.0, werte_fuer(rohteil_e, 36.0))
in_tasche = [p for p in bahn_t.punkte if not p.eilgang]
pruefe(
    all(35 + R <= p.x <= 65 - R and 17 + R <= p.y <= 43 - R for p in in_tasche),
    f"Tasche in der Insel: x {min(p.x for p in in_tasche):.2f} … {max(p.x for p in in_tasche):.2f}, "
    f"y {min(p.y for p in in_tasche):.2f} … {max(p.y for p in in_tasche):.2f}",
)
pruefe(
    bahn_t.variante == "inseln" and bahn_t.rampen == 1 and bahn_t.zeit < 0.6,
    f"Tasche in der Insel: {bahn_t.zeiten}, {bahn_t.rampen} Rampen",
)
rest, einschnitt = simuliert(bahn_t, teil_e, rohteil_e, 36.0, 30.0, 0.3)
pruefe(rest <= 0.05 and einschnitt >= -0.05, f"Tasche in der Insel: Rest {rest}, {einschnitt}")
# Schmaler als der Fräser: Dann geht es nicht – mit einem Satz, statt um die Insel zu fahren.
schmal_e = Part.makeBox(10, 26, 5, V(45, 17, 30))
teil_s = Part.makeBox(100, 60, 20).fuse(insel_e).cut(schmal_e).removeSplitter()
try:
    raeumen(teil_s, 30.0, werte_fuer(rohteil_e, 36.0))
except ValueError as grund:
    pruefe(len(str(grund)) > 10, "schmale Tasche: kein Satz")
else:
    pruefe(False, "schmale Tasche in der Insel: eine Bahn, obwohl der Fräser nicht hineinpasst")
# Mit der Platte zusammen: Die Platte wird geräumt, die schmale Tasche fällt aus – und die Bahn
# nennt sie (B-007: bisher ohne ein Wort).
ebenen_s = [e for e in hf.ebenen_oben(teil_s) if round(e.z) in (20, 30)]
bahn_s = rb.planen(
    hf.netze_je_hoehe(teil_s, ebenen_s),
    werte_fuer(rohteil_e, 36.0),
    ebenen_s,
    ra.konturen_des_teils(teil_s),
)
boden_s = next(e.name for e in ebenen_s if round(e.z) == 30)
pruefe(
    bahn_s.flaechen == 1 and bahn_s.ausgelassen == [boden_s],
    f"schmale Tasche: {bahn_s.flaechen} Flächen, ausgelassen {bahn_s.ausgelassen}",
)
pruefe(bahn_t.ausgelassen == [], f"Tasche in der Insel: ausgelassen {bahn_t.ausgelassen}")
print(f"Tasche in der Insel: Raeumen {bahn_t.zeit:.2f} min")

# --- (f) Mehrere Höhen in einer Bahn: die tiefste zuerst, jede Stelle einmal --------------------
# Dasselbe Teil: die Platte (z 20), die Insel oben (z 35) und der Boden der Tasche (z 30); das
# Rohteil reicht bis 36. Erst die Platte außen um die Insel, 16 tief in einer Lage; dann die
# Insel oben – nur noch über ihr, 1 mm, in Ringen um das, was noch steht; zuletzt die Tasche, von
# der geräumten Oberseite an (Spezifikation Strategien 13.5, T1).
ebenen_h = [e for e in hf.ebenen_oben(teil_e) if e.z > 19.0]
pruefe(sorted(round(e.z) for e in ebenen_h) == [20, 30, 35], f"Höhen: {ebenen_h}")
bahn_h = rb.planen(
    hf.netze_je_hoehe(teil_e, ebenen_h),
    werte_fuer(rohteil_e, 36.0),
    ebenen_h,
    ra.konturen_des_teils(teil_e),
)
folge_h, weg_h = [], {}
for a, b in zip(bahn_h.punkte, bahn_h.punkte[1:], strict=False):
    if b.eilgang or abs(b.z - a.z) > 1e-9:
        continue
    weg_h[b.z] = weg_h.get(b.z, 0.0) + bn.weg(a, b)
    if not folge_h or folge_h[-1] != b.z:
        folge_h.append(b.z)
pruefe(folge_h == [20.0, 35.0, 30.0], f"mehrere Höhen: Reihenfolge {folge_h}")
pruefe(
    bahn_h.flaechen == 3 and bahn_h.lagen == 3,
    f"mehrere Höhen: {bahn_h.flaechen} Flächen, {bahn_h.lagen} Lagen",
)
# Die Insel oben nur über sich: 50 × 40 mm bei ae 1,5 sind gut 1,3 m – nicht die 4 m über das
# ganze Rohteil; und nirgends weiter draußen als der erste Ring neben der Insel samt Einfahren.
oben_h = [p for p in bahn_h.punkte if not p.eilgang and abs(p.z - 35.0) < 1e-9]
pruefe(weg_h[35.0] < 2200.0, f"mehrere Höhen: Insel oben {weg_h[35.0]:.0f} mm im Vorschub")
pruefe(
    all(25 - 3 * R <= p.x <= 75 + 3 * R and 10 - 3 * R <= p.y <= 50 + 3 * R for p in oben_h),
    "mehrere Höhen: die Insel oben fährt über das ganze Rohteil",
)
# Die Tasche beginnt an der geräumten Oberseite der Insel (35), nicht am Rohteil (36).
in_tasche_h = [
    p for p in bahn_h.punkte if not p.eilgang and 35 + R <= p.x <= 65 - R and p.z < 35.0 - 1e-9
]
# Keine Lage über der Insel: waagerecht fährt der Vorschub nirgends höher als 35 (eine Rampe von
# der Oberkante des Rohteils hinab gehört zur Lage – seit 0.128.0 beginnt die dünne Lage über der
# Insel, breit genommen, in der Mitte mit einer).
vorschub_h = [
    b
    for a, b in zip(bahn_h.punkte, bahn_h.punkte[1:], strict=False)
    if not b.eilgang and not b.eintauchen and abs(b.z - a.z) < 1e-9
]
pruefe(max(p.z for p in vorschub_h) <= 35.0 + 1e-9, "mehrere Höhen: Vorschub über der Insel")
pruefe(len(in_tasche_h) > 10, "mehrere Höhen: die Tasche fehlt")
einzeln_h = sum(
    rb.planen(
        hf.netze_je_hoehe(teil_e, [e]),
        werte_fuer(rohteil_e, 36.0),
        [e],
        ra.konturen_des_teils(teil_e),
    ).zeit
    for e in ebenen_h
)
# Zusammen deutlich schneller als jede für sich. Seit 0.128.0 nimmt auch die einzelne Insel ihren
# Millimeter über dem ganzen Rohteil breit (bahn.DUENN) – der Abstand ist kleiner als vorher
# (0,80 statt 0,73).
pruefe(
    bahn_h.zeit < 0.85 * einzeln_h,
    f"mehrere Höhen: zusammen {bahn_h.zeit:.2f} min, jede für sich {einzeln_h:.2f} min",
)
for hoehe_h in (20.0, 35.0, 30.0):
    rest, einschnitt = simuliert(bahn_h, teil_e, rohteil_e, 36.0, hoehe_h, 0.3)
    pruefe(
        rest <= 0.05 and einschnitt >= -0.05,
        f"mehrere Höhen, z {hoehe_h}: Rest {rest}, Einschnitt {einschnitt}",
    )
print(f"mehrere Hoehen: Raeumen {bahn_h.zeit:.2f} min, jede fuer sich {einzeln_h:.2f} min")

# --- (g) Kein Ring ganz in der Luft (T1b) -----------------------------------------------------
# Ein Streifen 100 × 20 ohne Insel, 6 mm über der Oberseite: Die Ringe vom Rand her nehmen je
# 1,5 mm; nach dem siebten oder achten steht nichts mehr (11 mm bis zur Mitte des Rohteils).
# Bis 0.125.2 liefen sie weiter, bis die Mitte des Fräsers die Mitte des Rohteils erreichte –
# elf Ringe, die letzten drei ganz in der Luft: 27 % des Vorschubwegs, 2,78 statt 2,18 min.
teil_g = Part.makeBox(100, 20, 20)
rohteil_g = (-1.0, 101.0, -1.0, 21.0)
bahn_g = raeumen(teil_g, 20.0, werte_fuer(rohteil_g, 26.0, variante="rohteil"))
pruefe(7 <= bahn_g.ringe <= 9, f"Streifen: {bahn_g.ringe} Ringe")
pruefe(bahn_g.zeit < 2.3, f"Streifen: {bahn_g.zeit:.2f} min")
rest, einschnitt = simuliert(bahn_g, teil_g, rohteil_g, 26.0, 20.0, 0.3)
pruefe(rest <= 0.05 and einschnitt >= -0.05, f"Streifen: Rest {rest}, Einschnitt {einschnitt}")
k_g = ps.messen(
    [ps.Bahnlauf(bahn_g.punkte, VF, VF * 0.3)], teil_g, rohteil_g, 26.0, form, schruppen.ae,
    schruppen.ap, ebenen_z=[20.0], aufmass=0.3,
)  # fmt: skip
pruefe(
    k_g.luftanteil < 0.10, f"Streifen: {k_g.luftanteil * 100:.0f} % des Vorschubwegs in der Luft"
)
for satz in ps.urteile(k_g, sicher_nur=True):
    pruefe(False, f"Streifen: {satz}")
print(f"Streifen: {bahn_g.ringe} Ringe, {bahn_g.zeit:.2f} min, Luft {k_g.luftanteil * 100:.0f} %")

# --- (h) Die schnellste Variante, die die Last hält – mit FreeCADs Adaptiv-Kern (T5) -----------
# Manuel, 2026-10-02: „das was schneller ist ... gewinnt .. wenn man volle Tiefe fräst muss der
# ae schon in einem Rahmen bleiben der nicht das Doppelte ist“. Ohne Vorgabe rechnen die Ringe
# und „adaptiv“. Am Zapfen ist adaptiv die schnellste (2,45 gegen 2,70 min mit dem Morph), hebt
# höchstens zweimal ab und hält die Last. In der Tasche wären die Ringe schneller (0,78 gegen
# 1,31 min), greifen in ihren Ecken aber mit dem Vierfachen – sie fallen durch, adaptiv gewinnt
# und sagt es (`ueberlastet`). Mit der Vorgabe „ringe“ bleibt es bei den Ringen.


def abgehoben(bahn):
    """So oft hebt die Bahn ab: Eilgänge nach einem Satz im Vorschub."""
    return sum(
        1 for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False) if b.eilgang and not a.eilgang
    )


def drehsinn(bahn, anzahl=400):
    """> 0: Die ersten Sätze im Vorschub drehen gegen den Uhrzeigersinn."""
    p = [(q.x, q.y) for q in bahn.punkte if not q.eilgang and not q.eintauchen][:anzahl]
    summe = 0.0
    for a, b, c in zip(p, p[1:], p[2:], strict=False):
        summe += (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
    return summe


werte_h = werte_fuer(rohteil_a, 30.0, variante=None)
bahn_h = raeumen(teil_a, 20.0, werte_h)
# Manuels Räumen („stiche“, Abschnitt (j)) rechnet nur auf Vorgabe mit (Manuel, 2026-10-03:
# „wir lassen adaptiv“).
pruefe(
    bahn_h.variante == "adaptiv"
    and set(bahn_h.zeiten) == {"rohteil", "morph", "inseln", "adaptiv"},
    f"Zapfen, ohne Vorgabe: {bahn_h.variante} {bahn_h.zeiten}",
)
pruefe(bahn_h.zeit < bahn_a.zeit and not bahn_h.ueberlastet, f"Zapfen adaptiv: {bahn_h.zeit} min")
pruefe(abgehoben(bahn_h) <= 3, f"Zapfen adaptiv: {abgehoben(bahn_h)}-mal abgehoben")
rest, einschnitt = simuliert(bahn_h, teil_a, rohteil_a, 30.0, 20.0, 0.3)
pruefe(
    rest <= 0.05 and einschnitt >= -0.05, f"Zapfen adaptiv: Rest {rest}, Einschnitt {einschnitt}"
)
last_h, lang_h = rb.last(bahn_h, werte_h)
pruefe(
    last_h <= bn.LAST_KURZ * rb.LAST_SPIEL and lang_h <= 2 * R,
    f"Zapfen adaptiv: Last bis {last_h:.2f} ae, {lang_h:.1f} mm am Stück über {bn.LAST_DAUERND} ae",
)
k_h = ps.messen(
    [ps.Bahnlauf(bahn_h.punkte, VF, VF * 0.3)], teil_a, rohteil_a, 30.0, form, schruppen.ae,
    schruppen.ap, ebenen_z=[20.0], aufmass=0.3,
)  # fmt: skip
for satz in ps.urteile(k_h):
    pruefe(False, f"Zapfen adaptiv: {satz}")
# Der letzte Ring ist auch hier der genaue Kreis um den Zapfen.
kreis_h = [
    p
    for p in bahn_h.punkte
    if not p.eilgang and p.bogen is not None and abs(math.hypot(p.x - 25, p.y - 25) - 11.3) < 0.01
]
pruefe(len(kreis_h) >= 2, f"Zapfen adaptiv: {len(kreis_h)} Bögen auf dem Kreis um den Zapfen")
# Gegenlauf: gespiegelt gerechnet – der Drehsinn kehrt sich um, das Ergebnis bleibt.
bahn_hg = raeumen(teil_a, 20.0, werte_fuer(rohteil_a, 30.0, variante="adaptiv", gleichlauf=False))
pruefe(drehsinn(bahn_h) * drehsinn(bahn_hg) < 0, "adaptiv im Gegenlauf: derselbe Drehsinn")
rest, einschnitt = simuliert(bahn_hg, teil_a, rohteil_a, 30.0, 20.0, 0.3)
pruefe(rest <= 0.05 and einschnitt >= -0.05, f"adaptiv Gegenlauf: Rest {rest}, {einschnitt}")
# Die Ringe am Zapfen halten die Last – sie fielen nicht durch, sie sind nur langsamer.
last_a, lang_a = rb.last(bahn_a, werte_fuer(rohteil_a, 30.0))
pruefe(last_a <= bn.LAST_KURZ * rb.LAST_SPIEL, f"Zapfen, Morph: Last bis {last_a:.2f} ae")
print(
    f"Zapfen adaptiv: {bahn_h.zeit:.2f} min, Last bis {last_h:.2f} ae, "
    f"{abgehoben(bahn_h)}-mal abgehoben; Morph Last bis {last_a:.2f} ae"
)
# Die Tasche 40 × 30: Die Ringe wären schneller, halten die Last aber nicht.
werte_ht = werte_fuer(rohteil_c, 21.0, variante=None)
bahn_ht = raeumen(teil_c, 5.0, werte_ht)
pruefe(
    bahn_ht.variante == "adaptiv" and bahn_ht.zeiten["inseln"] < bahn_ht.zeiten["adaptiv"],
    f"Tasche, ohne Vorgabe: {bahn_ht.variante} {bahn_ht.zeiten}",
)
pruefe(
    bahn_ht.ueberlastet.get("inseln", 0.0) > 2.0,
    f"Tasche: die Ringe überlasten nicht? {bahn_ht.ueberlastet}",
)
pruefe(bahn_ht.rampen == 1, f"Tasche adaptiv: {bahn_ht.rampen} Rampen (die Helix)")
rest, einschnitt = simuliert(bahn_ht, teil_c, rohteil_c, 21.0, 5.0, 0.3)
pruefe(
    rest <= 0.05 and einschnitt >= -0.05, f"Tasche adaptiv: Rest {rest}, Einschnitt {einschnitt}"
)
last_ht, lang_ht = rb.last(bahn_ht, werte_ht)
pruefe(
    last_ht <= bn.LAST_KURZ * rb.LAST_SPIEL and lang_ht <= 2 * R,
    f"Tasche adaptiv: Last bis {last_ht:.2f} ae, {lang_ht:.1f} mm am Stück",
)
print(
    f"Tasche adaptiv: {bahn_ht.zeit:.2f} min, Last bis {last_ht:.2f} ae; die Ringe "
    f"{bahn_ht.zeiten['inseln']:.2f} min, Last bis {bahn_ht.ueberlastet.get('inseln', 0):.2f} ae"
)

# --- (j) Manuels Räumen: Stiche und Ringe (Spezifikation Strategien 14, 2026-10-03) ------------
# Am Zapfen: erst die Stiche – die Versätze des Zapfens von außen nach innen, jeder nur, wo in
# seinem Streifen noch Material steht, zurück unten außen um das Rohteil herum im Eilgang –,
# dann die Ringe um den Zapfen Band für Band bis zum genauen Kreis, ohne Rampe und ohne quer in
# den Streifen zu fahren (gleitend auf den nächsten Ring). Im Uhrzeiger um den Zapfen: Material
# rechts, Gleichlauf. Die Last hält (an engen Linksbögen weniger Vorschub); nichts bleibt
# stehen, nichts ins Teil.
werte_s = werte_fuer(rohteil_a, 30.0, variante=rb.STICHE)
bahn_s = raeumen(teil_a, 20.0, werte_s)
pruefe(
    bahn_s.variante == rb.STICHE and set(bahn_s.zeiten) == {rb.STICHE},
    f"Zapfen Stiche: {bahn_s.variante} {bahn_s.zeiten}",
)
pruefe(
    bahn_s.rampen == 0 and bahn_s.haelt,
    f"Zapfen Stiche: {bahn_s.rampen} Rampen, hält {bahn_s.haelt}",
)
pruefe(
    bahn_s.punkte
    and all(
        p.bogen[2]
        for p in bahn_s.punkte
        if p.bogen is not None and abs(math.hypot(p.x - 25, p.y - 25) - 11.3) < 0.01
    ),
    "Zapfen Stiche: der Kreis um den Zapfen nicht im Uhrzeiger (G2)",
)
rest, einschnitt = simuliert(bahn_s, teil_a, rohteil_a, 30.0, 20.0, 0.3)
pruefe(rest <= 0.05 and einschnitt >= -0.05, f"Zapfen Stiche: Rest {rest}, Einschnitt {einschnitt}")
last_s, lang_s = rb.last(bahn_s, werte_s)
pruefe(
    last_s <= bn.LAST_KURZ * rb.LAST_SPIEL and lang_s <= 2 * R,
    f"Zapfen Stiche: Last bis {last_s:.2f} ae, {lang_s:.1f} mm am Stück über {bn.LAST_DAUERND} ae",
)
kreis_s = [
    p
    for p in bahn_s.punkte
    if not p.eilgang and p.bogen is not None and abs(math.hypot(p.x - 25, p.y - 25) - 11.3) < 0.01
]
pruefe(len(kreis_s) >= 2, f"Zapfen Stiche: {len(kreis_s)} Bögen auf dem Kreis um den Zapfen")
# Die Stiche in den Ecken des Rohteils kehren unten außen herum zurück (Eilgang auf der Lage),
# die Ringe um den Zapfen hängen aneinander: hinauf geht es nur am Ende.
hinauf = sum(
    1
    for a, b in zip(bahn_s.punkte, bahn_s.punkte[1:], strict=False)
    if b.eilgang and not a.eilgang and b.z > a.z + 1.0
)
pruefe(hinauf <= 1, f"Zapfen Stiche: {hinauf}-mal hinaufgehoben")
pruefe(abgehoben(bahn_s) >= 10, f"Zapfen Stiche: {abgehoben(bahn_s)} Rückläufe unten")
k_s = ps.messen(
    [ps.Bahnlauf(bahn_s.punkte, VF, VF * 0.3)], teil_a, rohteil_a, 30.0, form, schruppen.ae,
    schruppen.ap, ebenen_z=[20.0], aufmass=0.3,
)  # fmt: skip
for satz in ps.urteile(k_s, sicher_nur=True):
    pruefe(False, f"Zapfen Stiche: {satz}")
print(
    f"Zapfen Stiche: {bahn_s.zeit:.2f} min, Last bis {last_s:.2f} ae, {hinauf}-mal hinauf, "
    f"{abgehoben(bahn_s)} Rücklaeufe, {bahn_s.ringe} Ringe, {bahn_s.laeufe} Läufe, "
    f"Luft {k_s.luftanteil * 100:.0f} %"
)

# --- (i) Eine dünne Lage breit (T2) -----------------------------------------------------------
# Der Block 60 × 40 mit 1 mm Rohteil über der Oberseite: Die Lage ist dünner als 0,1 D – der
# Fräser nimmt sie mit ae = R statt 1,5 und mit 66 % des Vorschubs, bei dem der Span so dick
# bleibt wie mit ae 1,5 (bahn.spanausgleich): 1,0 statt 2,7 min. Die Fläche ist danach eben, und
# die Last – gemessen mit ae = R – hält.
teil_duenn = Part.makeBox(60, 40, 20)
rohteil_duenn = (-1.0, 61.0, -1.0, 41.0)
werte_duenn = werte_fuer(rohteil_duenn, 21.0, variante="rohteil")
bahn_duenn = raeumen(teil_duenn, 20.0, werte_duenn)
pruefe(bahn_duenn.breit == {20.0: R}, f"dünne Lage: {bahn_duenn.breit}")
anteile_duenn = {
    round(p.anteil, 3) for p in bahn_duenn.punkte if not p.eilgang and abs(p.z - 20.0) < 1e-9
}
soll_duenn = round(bn.spanausgleich(schruppen.ae, 2 * R), 3)
pruefe(
    soll_duenn in anteile_duenn and max(anteile_duenn) <= soll_duenn + 1e-9,
    f"dünne Lage, Vorschub: {anteile_duenn}, {soll_duenn}",
)
pruefe(bahn_duenn.zeit < 1.2, f"dünne Lage: {bahn_duenn.zeit:.2f} min (mit ae 1,5: 2,72)")
rest, einschnitt = simuliert(bahn_duenn, teil_duenn, rohteil_duenn, 21.0, 20.0, 0.3)
pruefe(rest <= 0.05 and einschnitt >= -0.05, f"dünne Lage: Rest {rest}, Einschnitt {einschnitt}")
last_duenn, _lang = rb.last(bahn_duenn, werte_duenn)
pruefe(last_duenn <= bn.LAST_KURZ * rb.LAST_SPIEL, f"dünne Lage: Last bis {last_duenn:.2f} ae")
print(f"duenne Lage: {bahn_duenn.zeit:.2f} min, Last bis {last_duenn:.2f}")

# --- Fehler mit einem Satz --------------------------------------------------------------------
netz_a = hf.netz_ohne(teil_a, [e.name for e in ebenen_a])
for werte_falsch, ebenen_falsch, text in (
    (rb.Raeumwerte(ff.kugel(R), 25.0, 1.5, 0.3, 30.0, 35.0, rohteil_a), ebenen_a, "Kugel"),
    (rb.Raeumwerte(form, 25.0, 7.0, 0.3, 30.0, 35.0, rohteil_a), ebenen_a, "Abstand"),
    (rb.Raeumwerte(form, 0.0, 1.5, 0.3, 30.0, 35.0, rohteil_a), ebenen_a, "Werte"),
    (rb.Raeumwerte(form, 25.0, 1.5, 0.3, 20.0, 35.0, rohteil_a), ebenen_a, "nichts drüber"),
    (rb.Raeumwerte(form, 25.0, 1.5, 0.3, 30.0, 35.0, rohteil_a), [], "keine Fläche"),
):
    try:
        rb.planen(netz_a, werte_falsch, ebenen_falsch, ra.konturen_des_teils(teil_a))
    except ValueError as grund:
        pruefe(len(str(grund)) > 10, f"{text}: kein Satz")
    else:
        pruefe(False, f"{text}: keine Fehlermeldung")
print("Fehler ok")

# --- Die CAM-Operation im Job ---------------------------------------------------------------
import Path.Main.Job as PathJob

ue.uebergeben(wz.Bibliothek([werkzeug]))
doc = FreeCAD.newDocument("Raeumen")
doc.UndoMode = 1
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil_a
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0  # das Rohteil endet oben am Zapfen (30)
doc.recompute()
tc1 = js.controller_ohne_transaktion(doc, job, werkzeug, schruppen)
doc.recompute()
pruefe(
    abs(job.Stock.Shape.BoundBox.ZMax - 30.0) < 1e-6,
    f"Rohteil oben {job.Stock.Shape.BoundBox.ZMax}",
)
klon = job.Model.Group[0]
oben_im_job = next(e.name for e in hf.ebenen_oben(klon.Shape) if abs(e.z - 20.0) < 1e-6)
op = ra.lege_an(
    job, tc1, zustellung=schruppen.ap, zeilenabstand=schruppen.ae, flaechen=[oben_im_job]
)
doc.recompute()
pruefe(op.Label == "Räumen T1" and op in job.Operations.Group, f"{op.Label}")
pruefe(ra.ist_raeumen(op), "Art")
pruefe(js.operationsart(op) == "raeumen", f"Art: {js.operationsart(op)}")
pruefe(js.EINSATZ_NACH_OPERATION["raeumen"][0] == wz.SCHRUPPEN, "Einsatz Schruppen")
pruefe(
    abs(float(op.StartDepth) - 30.0) < 1e-6 and abs(float(op.FinalDepth) - 20.0) < 1e-6,
    f"Tiefen {float(op.StartDepth)} … {float(op.FinalDepth)}",
)
pruefe(
    (op.Ebenen, op.Lagen, op.Ringe, op.Laeufe) == (1, 1, bahn_h.ringe, bahn_h.laeufe),
    f"Operation: {op.Ebenen}, {op.Lagen}, {op.Ringe}, {op.Laeufe}",
)
pruefe(
    op.Gerechnet.startswith("adaptiv ") and "morph" in op.Gerechnet and "inseln" in op.Gerechnet,
    f"Gerechnet: {op.Gerechnet!r}",
)
pruefe(op.Gleichlauf is True and str(op.Variante) == "automatisch", "Vorgaben")
befehle = op.Path.Commands
namen_befehle = [b.Name for b in befehle]
pruefe(
    namen_befehle[1] == "G0" and namen_befehle[-1] == "G0",
    f"Befehle: {namen_befehle[:3]} … {namen_befehle[-1]}",
)
schnitte = [b for b in befehle if b.Name in ("G1", "G2", "G3")]
pruefe(any(b.Name in ("G2", "G3") for b in schnitte), "Bögen (die runden Ecken des ersten Rings)")
z_werte = sorted({round(b.Parameters["Z"], 6) for b in schnitte if "Z" in b.Parameters})
pruefe(min(z_werte) >= 20.0 - 1e-6 and 20.0 in z_werte, f"Z {z_werte[:5]}")
pruefe(op.getEditorMode("Ringe") == ["ReadOnly"], "Ringe änderbar")

# Ändern: Gegenlauf, Aufmaß am Boden 0,5 – die Endtiefe folgt; Variante „inseln“ vorgegeben.
ra.aendere(op, tc1, schruppen.ap, schruppen.ae, 0.3, aufmass_boden=0.5, gleichlauf=False)
doc.recompute()
pruefe(
    abs(float(op.FinalDepth) - 20.5) < 1e-6 and op.Gleichlauf is False,
    f"geändert: {float(op.FinalDepth)}",
)
z_werte = sorted(
    {
        round(b.Parameters["Z"], 6)
        for b in op.Path.Commands
        if b.Name in ("G1", "G2", "G3") and "Z" in b.Parameters
    }
)
pruefe(min(z_werte) >= 20.5 - 1e-6, f"Aufmaß am Boden: Z ab {min(z_werte)}")
op.Variante = "inseln"
doc.recompute()
pruefe(
    op.Gerechnet.startswith("inseln ") and "rohteil" not in op.Gerechnet,
    f"nur inseln: {op.Gerechnet!r}",
)
op.Variante = "ringe"  # die schnellste der Ringe, ohne Blick auf die Last
doc.recompute()
pruefe("adaptiv" not in op.Gerechnet and "morph" in op.Gerechnet, f"nur Ringe: {op.Gerechnet!r}")
ra.aendere(op, tc1, schruppen.ap, schruppen.ae, 0.3)
op.Variante = "automatisch"
doc.recompute()

# Speichern und Laden: dieselbe Bahn.
anzahl = len(op.Path.Commands)
befehle_bisher = [(b.Name, dict(b.Parameters)) for b in op.Path.Commands]
# Eine Datei wie vor der neuen Wahl: kein Freivorschub, nur die bisherigen Enum-Einträge.
op.Variante = list(ra.VARIANTEN[:-1])
op.Variante = "automatisch"
op.removeProperty("Freivorschub")
pfad = os.path.join(tempfile.mkdtemp(), "raeumen.FCStd")
doc.saveAs(pfad)
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(pfad)
op = next(o for o in doc.Objects if ra.ist_raeumen(o))
op.touch()
doc.recompute()
pruefe(len(op.Path.Commands) == anzahl, f"nach dem Laden {len(op.Path.Commands)} statt {anzahl}")
pruefe(op.getEditorMode("Ringe") == ["ReadOnly"], "Ringe nach dem Laden")
pruefe(str(op.Variante) == "automatisch", "alte Datei: Variante geändert")
pruefe(ra.ADAPTIV_FREI in op.getEnumerationsOfProperty("Variante"), "alte Datei: neue Wahl fehlt")
pruefe(
    [(b.Name, dict(b.Parameters)) for b in op.Path.Commands] == befehle_bisher,
    "alte Datei: Bahn oder Vorschübe geändert",
)
print(ascii(f"Operation: {anzahl} Befehle"))

# Neue Wahl: ausschließlich freie Vorschübe ändern; Vorgabe speichern, neu laden und rechnen.
ra.aendere(op, op.ToolController, schruppen.ap, schruppen.ae, 0.3,
           variante=ra.ADAPTIV_FREI, freivorschub=5000.0)  # fmt: skip
doc.recompute()
befehle_frei = [(b.Name, dict(b.Parameters)) for b in op.Path.Commands]
pruefe(len(befehle_frei) == len(befehle_bisher), "Freivorschub: andere Anzahl Befehle")
geaendert = 0
for (alt_name, alt), (neu_name, neu) in zip(befehle_bisher, befehle_frei, strict=False):
    pruefe(alt_name == neu_name and {k: v for k, v in alt.items() if k != "F"}
           == {k: v for k, v in neu.items() if k != "F"},
           "Freivorschub: Geometrie geändert")  # fmt: skip
    if alt.get("F", 0.0) <= VF / 60.0 or alt_name not in ("G1", "G2", "G3"):
        pruefe(neu == alt, "Freivorschub: Schnitt oder Eilgang geändert")
    elif neu.get("F") != alt.get("F"):
        geaendert += 1
    pruefe(neu.get("F", 0.0) <= 5000.0 / 60.0 + 1e-6, "Freivorschub über Vorgabe")
pruefe(geaendert > 0, "Freivorschub: kein freier Satz geändert")
doc.saveAs(pfad)
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(pfad)
op = next(o for o in doc.Objects if ra.ist_raeumen(o))
op.touch()
doc.recompute()
pruefe(str(op.Variante) == ra.ADAPTIV_FREI, "Freivorschub: Wahl nach Laden verloren")
pruefe(abs(float(op.Freivorschub) * 60.0 - 5000.0) < 1e-6, "Freivorschub: Wert verloren")
pruefe([(b.Name, dict(b.Parameters)) for b in op.Path.Commands] == befehle_frei,
       "Freivorschub: andere Bahn nach Laden")  # fmt: skip
ra.aendere(op, op.ToolController, schruppen.ap, schruppen.ae, 0.3, variante="automatisch")
doc.recompute()
pruefe([(b.Name, dict(b.Parameters)) for b in op.Path.Commands] == befehle_bisher,
       "zurück auf bisherig: andere Bahn")  # fmt: skip
try:
    ra.bahn_fuer(op.Proxy.job, op.Proxy.job.Model.Group, form, schruppen.ap, schruppen.ae,
                variante=ra.ADAPTIV_FREI, freivorschub=0)  # fmt: skip
except ValueError:
    pass
else:
    pruefe(False, "Freivorschub 0 akzeptiert")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
