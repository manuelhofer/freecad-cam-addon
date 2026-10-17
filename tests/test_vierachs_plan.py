# Prüft „Plan indexiert“ (W-003 Stufe V4c, W-006 S2): Welle Ø 20 mit einer Abflachung auf
# x = 8 zwischen zwei Wänden (a −30 … −10), Stange Ø 24, Schaftfräser Ø 6, Zustellung 2,
# Zeilenabstand 4 – die Rundachse steht auf 0°, drei Zeilen quer (Y) in zwei Lagen (Ø 24 →
# 10 → 8), die Zeilen enden vor den Wänden, hinein über die Rampe; die Befehle tragen Y und ein
# festes C. Der Abtrag (restmaterial) mit Versatz: über der Abflachung bleibt die Ebene x = 8,
# daneben die Stange; die Kugel versetzt trifft der Strahl, wo sie wirklich liegt. Dann die
# CAM-Operation im Job: angelegt, gerechnet (Ebenen, Lagen, Zeilen), geändert, gespeichert und
# geladen; ohne ebene Fläche oder mit Kugelfräser ein Satz statt einer Bahn. Eine Passfedernut
# (8 breit auf der Welle Ø 30): mit Ø 8 in voller Breite, mit Ø 6 als Trochoide – die Mitte des
# Fräsers im Langloch, bis an die Enden.
import dataclasses
import math
import os
import sys
import tempfile
import types

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import aufloesung as au
from camaddon import fraeserform as ff
from camaddon import job_schnittwerte as js
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_achsen as va
from camaddon import vierachs_bahn as vb
from camaddon import vierachs_huelle as vh
from camaddon import vierachs_operation as vo
from camaddon import vierachs_plan as vplan
from camaddon import vierachs_planbahn as vp
from camaddon import vierachs_rohteil as vr
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
LAENGS, RADIAL = (0, 0, 1), (1, 0, 0)

# --- Die Abflachung: eine ebene Fläche längs der Stange --------------------------------------
flach_welle = (
    Part.makeCylinder(10, 40, V(0, 0, -40))
    .cut(Part.makeBox(10, 30, 20, V(8, -15, -30)))
    .removeSplitter()
)
alle_namen = [f"Face{i + 1}" for i in range(len(flach_welle.Faces))]
abflachung = next(
    f"Face{i + 1}"
    for i, f in enumerate(flach_welle.Faces)
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-6
)
ebenen = vp.ebenen(flach_welle, LAENGS, RADIAL, alle_namen)
pruefe(len(ebenen) == 1 and ebenen[0].name == abflachung, f"Ebenen: {ebenen}")
if ebenen:
    e = ebenen[0]
    pruefe(abs(e.phi) < 1e-6 and abs(e.tiefe - 8.0) < 1e-6, f"Ebene: φ {e.phi}, Tiefe {e.tiefe}")
    pruefe(abs(e.a_von + 30) < 1e-6 and abs(e.a_bis + 10) < 1e-6, f"längs {e.a_von} … {e.a_bis}")
    pruefe(abs(e.q_von + 6) < 1e-3 and abs(e.q_bis - 6) < 1e-3, f"quer {e.q_von} … {e.q_bis}")
pruefe(vp.ebener_radius(ff.scheibe(3.0)) == 3.0, "ebener Radius der Scheibe")
pruefe(vp.ebener_radius(ff.torus(3.0, 1.0)) == 2.0, "ebener Radius des Torus")
pruefe(vp.ebener_radius(ff.kugel(3.0)) == 0.0, "ebener Radius der Kugel")

# --- Die Bahn: zwei Lagen, drei Zeilen, vor den Wänden halt, über die Helix hinein ----------
netz = vp.netz_ohne(flach_welle, [abflachung])
werte = vp.Planwerte(
    form=ff.scheibe(3.0),
    stange_radius=12.0,
    zustellung=2.0,
    zeilenabstand=4.0,
    aufmass=0.0,
    a_stange_vorne=1.0,
    a_futter=-60.0,
)
bahn = vp.planen(netz, LAENGS, RADIAL, werte, ebenen)
pruefe(
    (bahn.flaechen, bahn.lagen, bahn.zeilen) == (1, 2, 6),
    f"Flächen, Lagen, Zeilen: {bahn.flaechen}, {bahn.lagen}, {bahn.zeilen}",
)
pruefe(abs(bahn.r_min - 8.0) < 1e-9, f"tiefste Spitze {bahn.r_min}")
start = bahn.punkte[0]
pruefe(start.eilgang and start.a == 1.0 + 3.0 + 2.0 and start.r == 14.0, f"Start: {start}")
vorschub_alle = [p for p in bahn.punkte if not p.eilgang]
pruefe(all(abs(p.phi) < 1e-9 for p in vorschub_alle), "die Rundachse steht nicht auf 0°")
# Die Zeilen auf ihren Versätzen (0, ± q_soll); die anderen Punkte sind die Helix der Einfahrt
# (P-2026-10-16-53: statt der Rampe hin und her längs der ersten Zeile), im Feld der Zeilen und
# ohne Kehre.
q_soll = 6.0 - 3.0 - vb.TOLERANZ_SCHLICHTEN - vb.RAND - vp.LUFT


def in_zeile(p):
    return abs(p.q) < 1e-9 or abs(abs(p.q) - q_soll) < 1e-6


vorschub = [p for p in vorschub_alle if in_zeile(p)]
helix = [p for p in vorschub_alle if not in_zeile(p)]
pruefe(
    {round(p.q, 3) for p in vorschub} == {0.0, round(q_soll, 3), round(-q_soll, 3)},
    f"Zeilen quer: {sorted({round(p.q, 3) for p in vorschub})}",
)
pruefe(
    helix and all(abs(p.q) <= q_soll + 1e-6 and -27.0 - 1e-6 <= p.a <= -13.0 + 1e-6 for p in helix),
    f"Helix: {len(helix)} Punkte, nicht im Feld",
)
pruefe(vb.kehren(bahn.punkte)[0] == 0, f"Kehren: {vb.kehren(bahn.punkte)}")


def drehsinn(b):
    """Wie die Helix dreht, von oben auf die Ebene gesehen (x = a, y = −q): Summe der
    Kreuzprodukte zweier aufeinanderfolgender Schritte – positiv gegen den Uhrzeigersinn."""
    summe = 0.0
    for p0, p1, p2 in zip(b.punkte, b.punkte[1:], b.punkte[2:], strict=False):
        if p0.eilgang or p1.eilgang or p2.eilgang or in_zeile(p0) or in_zeile(p2):
            continue
        d1 = (p1.a - p0.a, -(p1.q - p0.q))
        d2 = (p2.a - p1.a, -(p2.q - p1.q))
        summe += d1[0] * d2[1] - d1[1] * d2[0]
    return summe


# Im Gleichlauf (M3) dreht die Helix wie die Bohrung: gegen den Uhrzeigersinn; im Gegenlauf mit.
pruefe(drehsinn(bahn) > 0, f"Helix im Gleichlauf: Drehsinn {drehsinn(bahn):.2f}")
gegen = vp.planen(netz, LAENGS, RADIAL, dataclasses.replace(werte, gleichlauf=False), ebenen)
pruefe(drehsinn(gegen) < 0, f"Helix im Gegenlauf: Drehsinn {drehsinn(gegen):.2f}")
pruefe(all(8.0 - 1e-9 <= p.r <= 12.0 + 1e-9 for p in vorschub), "Spitze außerhalb 8 … 12")
pruefe(
    all(-27.0 - 1e-6 <= p.a <= -13.0 + 1e-6 for p in vorschub),
    f"längs über die Wände hinaus: {min(p.a for p in vorschub)} … {max(p.a for p in vorschub)}",
)


# Nur im Gleichlauf (P-2026-10-02-24): jede Zeile für sich von vorne zum Futter (a fällt),
# dazwischen abheben; die Zeilen quer mit M3 von +q nach −q – mit M4 andersherum.
def fahrten_einzeln(b):
    stuecke, jetzt = [], []
    for p in b.punkte:
        if p.eilgang:
            if len(jetzt) > 1:
                stuecke.append(jetzt)
            jetzt = []
        else:
            jetzt.append(p)
    return stuecke


for gleichlauf, name in ((True, "M3"), (False, "M4")):
    einzeln = vp.planen(
        netz,
        LAENGS,
        RADIAL,
        dataclasses.replace(werte, nur_gleichlauf=True, gleichlauf=gleichlauf),
        ebenen,
    )
    pruefe(
        (einzeln.lagen, einzeln.zeilen) == (bahn.lagen, bahn.zeilen),
        f"{name}: {einzeln.lagen} Lagen, {einzeln.zeilen} Zeilen",
    )
    stuecke_e = fahrten_einzeln(einzeln)
    pruefe(
        len(stuecke_e) == einzeln.zeilen and all(st[-1].a < st[0].a for st in stuecke_e),
        f"{name}: {len(stuecke_e)} Fahrten, nicht alle zum Futter",
    )
    qs = [round(st[-1].q, 3) for st in stuecke_e]
    je_lage = max(1, einzeln.zeilen // max(einzeln.lagen, 1))
    folge_ok = all(
        all((b < a) == gleichlauf for a, b in zip(teil, teil[1:], strict=False))
        for teil in (qs[i : i + je_lage] for i in range(0, len(qs), je_lage))
    )
    pruefe(folge_ok, f"{name}: Zeilen quer {qs}")


# Jede Zeile reicht bis an die Wände – auch die äußeren in der Lage auf dem Zylinderradius,
# die den Zylinder neben der Wand streifen dürften, aber nicht sollen.
enden = {}
for q in sorted({round(p.q, 3) for p in vorschub}):
    zeile = [p.a for p in vorschub if abs(p.q - q) < 1e-6]
    enden[q] = (round(min(zeile), 6), round(max(zeile), 6))
pruefe(
    all(von < -26.5 and bis > -13.5 for von, bis in enden.values())
    and len(set(enden.values())) == 1,
    f"Zeilenenden je Versatz: {enden}",
)
unten = [p for p in vorschub if abs(p.r - 8.0) < 1e-9]
pruefe(
    len(unten) >= 6 and min(p.a for p in unten) < -26.0 < -14.0 < max(p.a for p in unten), "unten"
)
rampen = 0
for vorher, punkt in zip(bahn.punkte, bahn.punkte[1:], strict=False):
    if vorher.eilgang and not punkt.eilgang:
        pruefe(punkt.eintauchen, f"hinein ohne Eintauchvorschub bei a {punkt.a:.2f}")
        rampen += punkt.r > 8.0 + 1e-9  # erst ans Material, dann die Rampe
pruefe(rampen >= 2, f"nur {rampen} Rampen")
pruefe(vb.dauer(bahn, 500.0) > 0.0, "keine Zeit")
befehle = vb.befehle(bahn, LAENGS, RADIAL, "C", 1, 500.0)
schnitte = [b for b in befehle if b.Name == "G1"]
pruefe(all("Y" in b.Parameters and "X" in b.Parameters for b in schnitte), "G1 ohne Y")
pruefe(all(abs(b.Parameters.get("C", 0.0)) < 1e-9 for b in schnitte), "C dreht")
pruefe(
    abs(max(b.Parameters["Y"] for b in schnitte) - q_soll) < 1e-6
    and abs(min(b.Parameters["Y"] for b in schnitte) + q_soll) < 1e-6,
    "Y nicht bis zum Rand",
)
print(ascii(f"Abflachung geplant: {len(bahn.punkte)} Punkte, {len(schnitte)} Saetze"))

# Mit den Nuten gerechnet bleibt es dieselbe Bahn: Zwischen den Wänden wäre die Abflachung eine
# offene Nut, 20 breit – zu breit für die Bahn „Nut“ mit Ø 6, also Zeilen.
mit_nuten = vp.planen(
    netz, LAENGS, RADIAL, werte, ebenen, nuten_=vp.nuten(flach_welle, LAENGS, RADIAL, ebenen)
)
pruefe(
    (mit_nuten.nuten, mit_nuten.lagen, mit_nuten.zeilen) == (0, 2, 6),
    f"Abflachung mit Nuten: {mit_nuten.nuten}, {mit_nuten.lagen}, {mit_nuten.zeilen}",
)

# Ein Stift Ø 1,2, 2 hoch, zwischen zwei Zeilen auf der Abflachung (P-2026-10-02-30): Die
# Zeilen liegen 2,98 auseinander – geprüft nur auf ihnen, bliebe ein Hindernis dazwischen bis
# 2,98² ÷ (8 · 3) = 0,37 mm unentdeckt; der Schritt quer zwischen zwei Zeilen streifte den Stift
# um 0,1 mm. Jetzt auch dazwischen geprüft: Unter seiner Oberkante kommt die Achse des Fräsers
# der des Stifts nirgends näher als 3 + 0,6.
_l, _u, quer = vh.rahmen(LAENGS, RADIAL)
q_stift = float(np.dot((0.0, 1.49, 0.0), quer))
mit_stift = flach_welle.fuse(Part.makeCylinder(0.6, 2.0, V(8, 1.49, -25), V(1, 0, 0)))
mit_stift = mit_stift.removeSplitter()
flach_stift = max(
    (
        (f"Face{i + 1}", f)
        for i, f in enumerate(mit_stift.Faces)
        if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-6
    ),
    key=lambda nf: nf[1].Area,
)[0]
ebenen_stift = [
    e
    for e in vp.ebenen(
        mit_stift, LAENGS, RADIAL, [f"Face{i + 1}" for i in range(len(mit_stift.Faces))]
    )
    if e.name == flach_stift
]
stift_bahn = vp.planen(vp.netz_ohne(mit_stift, [flach_stift]), LAENGS, RADIAL, werte, ebenen_stift)
am_stift = math.inf
for von, nach in zip(stift_bahn.punkte, stift_bahn.punkte[1:], strict=False):
    if nach.eilgang:
        continue
    for t in np.linspace(0.0, 1.0, 41):
        r = von.r + t * (nach.r - von.r)
        if r < 10.0 - 1e-6:
            a = von.a + t * (nach.a - von.a)
            q = von.q + t * (nach.q - von.q)
            am_stift = min(am_stift, math.hypot(a + 25.0, q - q_stift))
pruefe(am_stift >= 3.6 - 0.06, f"am Stift: Achse {am_stift:.3f} mm von seiner (nötig 3,6)")
print(ascii(f"Abflachung mit Stift: {stift_bahn.zeilen} Zeilen, am Stift {am_stift:.3f} mm"))

# --- Die Passfedernut (P-2026-10-02-05): 8 breit, 30 lang, 4 tief auf der Welle Ø 30 -------
# Ihr Grund ist eine ebene Fläche längs der Stange – mit Zeilen kam der Fräser Ø 8 gar nicht
# hinein (die Wände stehen genau am Rand der Stirn) und Ø 6 nicht an die Enden (4 mm blieben).
# Jetzt die Bahn „Nut“ im Rahmen der Fläche: Ø 8 in voller Breite mit der Rampe (langsamer),
# Ø 6 in Bögen (P-2026-10-02-53) und der Wand rundum; die Mitte des Fräsers bleibt im Langloch.
nutwelle = (
    Part.makeCylinder(15, 80, V(0, 0, -80))
    .cut(
        Part.makeBox(10, 8, 22, V(11, -4, -41))
        .fuse(Part.makeCylinder(4, 10, V(11, 0, -41), V(1, 0, 0)))
        .fuse(Part.makeCylinder(4, 10, V(11, 0, -19), V(1, 0, 0)))
    )
    .removeSplitter()
)
nut_namen = [f"Face{i + 1}" for i in range(len(nutwelle.Faces))]
nut_ebenen = vp.ebenen(nutwelle, LAENGS, RADIAL, nut_namen)
pruefe(len(nut_ebenen) == 1 and abs(nut_ebenen[0].tiefe - 11.0) < 1e-6, f"Nutgrund: {nut_ebenen}")
gefunden = vp.nuten(nutwelle, LAENGS, RADIAL, nut_ebenen)
nut = next(iter(gefunden.values()), [None])[0]
pruefe(
    nut is not None and abs(nut.radius - 4.0) < 1e-6 and not nut.offen,
    f"Passfedernut erkannt: {nut}",
)
nut_netz = vp.netz_ohne(nutwelle, [e.name for e in nut_ebenen])
nut_teilnetz = vh.vernetze(nutwelle, 0.01)
for r_f, erwartet in ((4.0, "voll"), (3.0, "boegen")):
    w_nut = vp.Planwerte(
        form=ff.scheibe(r_f),
        stange_radius=15.0,
        zustellung=2.0,
        zeilenabstand=2.0 * r_f * 0.6,
        aufmass=0.0,
        a_stange_vorne=1.0,
        a_futter=-100.0,
    )
    b = vp.planen(nut_netz, LAENGS, RADIAL, w_nut, nut_ebenen, nuten_=gefunden)
    im_teil = [p for p in b.punkte if not p.eilgang and p.r < 15.0 - 1e-6]
    weit = max(
        math.hypot(max(0.0, -41.0 - p.a, p.a + 19.0), p.q) for p in im_teil
    )  # die Mitte des Fräsers vom Mittelstück der Nut
    unten = [p for p in im_teil if p.r < 11.0 + 1e-6]
    pruefe(b.nuten == 1 and b.r_min > 11.0 - 1e-6, f"Ø {2 * r_f:g}: {b.nuten} Nut, {b.r_min}")
    pruefe(weit < 4.0 - r_f + 1e-3, f"Ø {2 * r_f:g}: die Mitte {weit:.3f} vom Mittelstück")
    # Auf der Stange abgetragen (wie „Auf der Maschine prüfen“): nirgends ins Teil. Die Stange
    # kennt je Strahl nur einen Radius; neben den Wänden läuft der Strahl schräg durch die Wand
    # auf den Grund – bis zum Grund darf weg sein (restmaterial.boden_radien), darunter nicht.
    abtrag = rm.Stange(16.0, -100.0, 1.0)
    abtrag.fahre_stuecke(
        [(p.a, p.r, p.phi, p.q) for p, n in zip(b.punkte, b.punkte[1:], strict=False) if not n.eilgang],
        [(n.a, n.r, n.phi, n.q) for p, n in zip(b.punkte, b.punkte[1:], strict=False) if not n.eilgang],
        ff.scheibe(r_f),
    )  # fmt: skip
    genau = rm.teilradien(nut_teilnetz, LAENGS, RADIAL, abtrag, rm.GENAU)
    boden = rm.boden_radien(
        abtrag, LAENGS, RADIAL, [(e, nutwelle.Faces[int(e.name[4:]) - 1]) for e in nut_ebenen]
    )
    erlaubt = np.where(np.isfinite(boden), np.maximum(genau - boden, 0.0), 0.0)
    teil_r = rm.teilradien(nut_teilnetz, LAENGS, RADIAL, abtrag)
    ohne = rm.vergleiche(abtrag, teil_r, 0.0, genau)
    vergleich = rm.vergleiche(abtrag, teil_r, 0.0, genau, erlaubt=erlaubt)
    pruefe(vergleich.kleinster >= -rm.BLAU_AB, f"Ø {2 * r_f:g}: ins Teil {vergleich.kleinster:.3f}")
    print(ascii(f"  Stange: ohne den Grund {ohne.kleinster:.2f} „ins Teil“ (die Strahlen schräg "
                f"durch die Wand), mit ihm {vergleich.kleinster:.3f}"))  # fmt: skip
    pruefe(
        unten
        and min(p.a for p in unten) < -41.0 - (4.0 - r_f) + 0.03
        and max(p.a for p in unten) > -19.0 + (4.0 - r_f) - 0.03,
        f"Ø {2 * r_f:g}: nicht bis an die Enden",
    )
    if erwartet == "voll":
        pruefe(any(p.anteil < 1.0 for p in im_teil), "Vollnut ohne kleineren Vorschub")
    else:
        pruefe(b.zeilen > 10, f"in Bögen: {b.zeilen} Bögen")
    nut_befehle = [x for x in vb.befehle(b, LAENGS, RADIAL, "C", 1, 500.0) if x.Name == "G1"]
    pruefe(len({round(x.Parameters["C"], 6) for x in nut_befehle}) == 1, "C dreht in der Nut")
    print(ascii(f"Passfedernut Ø {2 * r_f:g}: {b.lagen} Lagen, {b.zeilen} Bögen/Fahrten, "
                f"{vb.dauer(b, 500.0):.2f} min"))  # fmt: skip

# --- Querbohrungen (P-2026-10-02-07): auf der Welle Ø 30 eine Sackbohrung Ø 10, 8 tief (oben),
# eine Ø 10 um 3 quer versetzt (Y) und eine durchgehende Ø 8 quer (längs Y) ----------------------
# Je Seite die Bahn „Bohrung fräsen“ im Rahmen der Bohrung: Helix hinab, die Wand rundum; die
# Mitte des Fräsers Ø 6 nie weiter als 2 von der Achse der Bohrung, nie tiefer als ihr Grund; die
# durchgehende von beiden Seiten je bis zur Mitte. Auf der Stange nirgends ins Teil.
bohrwelle = (
    Part.makeCylinder(15, 100, V(0, 0, -100))
    .cut(Part.makeCylinder(5, 10, V(7, 0, -20), V(1, 0, 0)))
    .cut(Part.makeCylinder(5, 10, V(8, 3, -45), V(1, 0, 0)))
    .cut(Part.makeCylinder(4, 40, V(0, -20, -70), V(0, 1, 0)))
    .removeSplitter()
)
quer_namen = [
    f"Face{i + 1}"
    for i, f in enumerate(bohrwelle.Faces)
    if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 15.0) > 1e-6
]
paare = vp.bohrungen(bohrwelle, LAENGS, RADIAL, quer_namen)
seiten = sorted((round(e.phi), round(b.z_unten, 3), round(b.radius, 3)) for e, b in paare)
pruefe(
    seiten == [(-90, 0.0, 4.0), (0, 7.0, 5.0), (0, 8.0, 5.0), (90, 0.0, 4.0)],
    f"Querbohrungen: {seiten}",
)
versetzt = [e for e, b in paare if abs(b.z_unten - 8.0) < 1e-6]
pruefe(
    versetzt and abs((versetzt[0].q_von + versetzt[0].q_bis) / 2 - 3.0) < 1e-6,
    f"Versatz quer: {versetzt and (versetzt[0].q_von, versetzt[0].q_bis)}",
)
w_bohr = vp.Planwerte(
    form=ff.scheibe(3.0),
    stange_radius=16.0,
    zustellung=2.0,
    zeilenabstand=3.6,
    aufmass=0.0,
    a_stange_vorne=1.0,
    a_futter=-120.0,
)
bohr_bahn = vp.planen(vp.netz_ohne(bohrwelle, []), LAENGS, RADIAL, w_bohr, [], bohrungen_=paare)
pruefe(
    bohr_bahn.bohrungen == 3 and bohr_bahn.flaechen == 3 and bohr_bahn.r_min > -1e-6,
    f"Bohrungen: {bohr_bahn.bohrungen}, Flächen {bohr_bahn.flaechen}",
)
for ebene, b in paare:
    mitte_q = -b.mitte[1]
    an_ihr = [
        p
        for p in bohr_bahn.punkte
        if not p.eilgang
        and abs(p.phi - ebene.phi) < 1e-6
        and p.r < 15.5
        and math.hypot(p.a - b.mitte[0], p.q - mitte_q) < 6.0
    ]
    weit = max((math.hypot(p.a - b.mitte[0], p.q - mitte_q) for p in an_ihr), default=99.0)
    pruefe(
        an_ihr and weit < b.radius - 3.0 + 1e-3 and min(p.r for p in an_ihr) > b.z_unten - 1e-6,
        f"Bohrung φ {ebene.phi:.0f}, Grund {b.z_unten}: Mitte bis {weit:.3f}",
    )
abtrag_b = rm.Stange(16.0, -120.0, 1.0)
abtrag_b.fahre_stuecke(
    [(p.a, p.r, p.phi, p.q) for p, n in zip(bohr_bahn.punkte, bohr_bahn.punkte[1:], strict=False) if not n.eilgang],
    [(n.a, n.r, n.phi, n.q) for p, n in zip(bohr_bahn.punkte, bohr_bahn.punkte[1:], strict=False) if not n.eilgang],
    ff.scheibe(3.0),
)  # fmt: skip
bohr_netz = vh.vernetze(bohrwelle, 0.01)
genau_b = rm.teilradien(bohr_netz, LAENGS, RADIAL, abtrag_b, rm.GENAU)
boden_b = rm.boden_radien(
    abtrag_b, LAENGS, RADIAL, [vp.boden_der_bohrung(LAENGS, RADIAL, e, b) for e, b in paare]
)
erlaubt_b = np.where(np.isfinite(boden_b), np.maximum(genau_b - boden_b, 0.0), 0.0)
vergleich_b = rm.vergleiche(
    abtrag_b, rm.teilradien(bohr_netz, LAENGS, RADIAL, abtrag_b), 0.0, genau_b, erlaubt=erlaubt_b
)
pruefe(vergleich_b.kleinster >= -rm.BLAU_AB, f"Querbohrungen: ins Teil {vergleich_b.kleinster:.3f}")
print(ascii(f"Querbohrungen: {bohr_bahn.bohrungen} Bohrungen von {len(paare)} Seiten, "
            f"{bohr_bahn.lagen} Lagen, {vb.dauer(bohr_bahn, 500.0):.2f} min, "
            f"ins Teil {vergleich_b.kleinster:.3f}"))  # fmt: skip

# --- Radial bohren (P-2026-10-02-08): mit dem Bohrer Ø 8 (118°) statt dem Fräser – eine
# durchgehende Ø 8 quer (von beiden Seiten, je mit der Spitze über die Mitte), eine Sackbohrung
# Ø 8, 22 tief mit der Spitze des Bohrers unten (tiefer als 3 × D: in Hüben von 1 × D) und eine
# flache, 10 tief, auch mit Spitze. Jeder Hub genau auf der Achse der Bohrung, die Spitze nie
# tiefer als die gezeichnete; auf der Stange nirgends ins Teil – auch nicht unter dem Ende der
# Wand, wo die Spitze tiefer geht (ihr Grund ist der Kegel, vierachs_planbahn.Kegelgrund). Ein
# Bohrer Ø 6 passt nicht, ein ebener Grund geht nicht: je ein Satz.
lang = 4.0 / math.tan(math.radians(59.0))
bohrwelle2 = (
    Part.makeCylinder(15, 100, V(0, 0, -100))
    .cut(Part.makeCylinder(4, 27, V(-7, 0, -30), V(1, 0, 0)))
    .cut(Part.makeCone(4, 0, lang, V(-7, 0, -30), V(-1, 0, 0)))
    .cut(Part.makeCylinder(4, 40, V(0, -20, -70), V(0, 1, 0)))
    .cut(Part.makeCylinder(4, 12, V(0, 5, -50), V(0, 1, 0)))
    .cut(Part.makeCone(4, 0, lang, V(0, 5, -50), V(0, -1, 0)))
    .removeSplitter()
)
namen2 = [
    f"Face{i + 1}"
    for i, f in enumerate(bohrwelle2.Faces)
    if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 4.0) < 1e-6
]
paare2 = vp.bohrungen(bohrwelle2, LAENGS, RADIAL, namen2)
bohrer = vplan.bohrer_von(
    wz.Werkzeug(nummer=2, art=wz.BOHRER, durchmesser=8.0, spitzenwinkel=118.0)
)
pruefe(bohrer == (8.0, 118.0), f"Bohrer: {bohrer}")
pruefe(vplan.bohrer_von(wz.Werkzeug(nummer=1, durchmesser=8.0)) is None, "Fräser als Bohrer")
pruefe(vp.bohrer_passt(paare2, bohrer), f"Bohrer passt nicht: {[(e.phi, b) for e, b in paare2]}")
pruefe(not vp.bohrer_passt(paare2, (6.0, 118.0)), "Ø 6 passt zu Ø 8")
pruefe(not vp.bohrer_passt(paare, bohrer), "Bohrer bei ebenem Grund")
w_bohrer = vp.Planwerte(
    form=vplan.form_des_bohrers(bohrer),
    stange_radius=16.0,
    zustellung=2.0,
    zeilenabstand=3.6,
    aufmass=0.0,
    a_stange_vorne=1.0,
    a_futter=-120.0,
    bohrer=bohrer,
)
bb2 = vp.planen(vp.netz_ohne(bohrwelle2, []), LAENGS, RADIAL, w_bohrer, [], bohrungen_=paare2)
pruefe(
    bb2.bohrungen == 3 and bb2.seiten == 4 and bb2.huebe == 7,
    f"Bohrungen {bb2.bohrungen}, Seiten {bb2.seiten}, Hübe {bb2.huebe}",
)
pruefe(abs(bb2.r_min - (-7.0 - lang)) < 1e-6, f"tiefste Spitze {bb2.r_min:.3f}")
for ebene, b in paare2:
    mitte_q = -b.mitte[1]
    an_ihr = [
        p
        for p in bb2.punkte
        if not p.eilgang and abs(p.phi - ebene.phi) < 1e-6 and abs(p.a - b.mitte[0]) < 6.0
    ]
    abseits = max((math.hypot(p.a - b.mitte[0], p.q - mitte_q) for p in an_ihr), default=99.0)
    spitze = b.z_unten - lang  # eine durchgehende: z_unten 0, die Mitte
    pruefe(
        an_ihr and abseits < 1e-6 and min(p.r for p in an_ihr) > spitze - 1e-6,
        f"Bohrung φ {ebene.phi:.0f}: abseits {abseits:.3f}, Spitze {min(p.r for p in an_ihr):.3f}",
    )
abtrag_r = rm.Stange(16.0, -120.0, 1.0)
abtrag_r.fahre_stuecke(
    [(p.a, p.r, p.phi, p.q) for p, n in zip(bb2.punkte, bb2.punkte[1:], strict=False) if not n.eilgang],
    [(n.a, n.r, n.phi, n.q) for p, n in zip(bb2.punkte, bb2.punkte[1:], strict=False) if not n.eilgang],
    vplan.form_des_bohrers(bohrer),
)  # fmt: skip
netz_r = vh.vernetze(bohrwelle2, 0.01)
genau_r = rm.teilradien(netz_r, LAENGS, RADIAL, abtrag_r, rm.GENAU)
namen_r = [e.name for e, _b in paare2]
boden_r = rm.boden_radien(
    abtrag_r,
    LAENGS,
    RADIAL,
    [
        vp.boden_der_bohrung(LAENGS, RADIAL, e, b, bohrer, namen_r.count(e.name) > 1)
        for e, b in paare2
    ],
)
erlaubt_r = np.where(np.isfinite(boden_r), np.maximum(genau_r - boden_r, 0.0), 0.0)
vergleich_r = rm.vergleiche(
    abtrag_r, rm.teilradien(netz_r, LAENGS, RADIAL, abtrag_r), 0.0, genau_r, erlaubt=erlaubt_r
)
pruefe(vergleich_r.kleinster >= -rm.BLAU_AB, f"Radial bohren: ins Teil {vergleich_r.kleinster:.3f}")
scheiben = rm.boden_radien(
    abtrag_r, LAENGS, RADIAL, [vp.boden_der_bohrung(LAENGS, RADIAL, e, b) for e, b in paare2]
)
erlaubt_s = np.where(np.isfinite(scheiben), np.maximum(genau_r - scheiben, 0.0), 0.0)
vergleich_s = rm.vergleiche(
    abtrag_r, rm.teilradien(netz_r, LAENGS, RADIAL, abtrag_r), 0.0, genau_r, erlaubt=erlaubt_s
)
print(ascii(f"  mit der Scheibe statt der Spitze: ins Teil {vergleich_s.kleinster:.3f}"))
w_falsch = vp.Planwerte(
    form=vplan.form_des_bohrers((6.0, 118.0)),
    stange_radius=16.0,
    zustellung=2.0,
    zeilenabstand=3.6,
    aufmass=0.0,
    a_stange_vorne=1.0,
    a_futter=-120.0,
    bohrer=(6.0, 118.0),
)
for werte_b, welle_b, paare_b, text in (
    (w_falsch, bohrwelle2, paare2, "Bohrer Ø 6"),
    (
        dataclasses.replace(
            w_falsch, form=vplan.form_des_bohrers((10.0, 118.0)), bohrer=(10.0, 118.0)
        ),
        bohrwelle,
        [(e, b) for e, b in paare if abs(b.radius - 5.0) < 1e-6],
        "ebener Grund",
    ),
):
    try:
        vp.planen(vp.netz_ohne(welle_b, []), LAENGS, RADIAL, werte_b, [], bohrungen_=paare_b)
        pruefe(False, f"{text}: keine Meldung")
    except ValueError as meldung:
        satz = str(meldung)
        erwartet = ("Ø 6", "Ø 8") if text == "Bohrer Ø 6" else ("Ø 10", "ebenen Grund")
        pruefe(all(teil in satz for teil in erwartet), f"{text}: {satz}")
print(ascii(f"Radial bohren: {bb2.bohrungen} Bohrungen von {bb2.seiten} Seiten, {bb2.huebe} Huebe, "
            f"{vb.dauer(bb2, 400.0, 400.0):.2f} min, ins Teil {vergleich_r.kleinster:.3f}"))  # fmt: skip


# --- Nut auf dem Mantel (P-2026-10-02-09): auf der Welle Ø 30 eine Nut 8 breit, 4 tief über
# 120° (der Grund ein Zylinder R 11, die Enden Ebenen durch die Achse) und eine 12 breit, 3 tief
# über 90°. „Rundum schruppen“ kam mit dem Fräser Ø 8 gar nicht in die 8 breite hinein (4 mm
# blieben stehen). Jetzt: die Rundachse dreht, Ø 8 fährt die schmale in voller Breite mit der
# Zickzack-Rampe hinab, die breite dazu in Zeilen bis an die Wände; der Grund danach eben (rund),
# an den Enden nichts in den Wänden, auf der Stange nirgends ins Teil.
def _umfangsnut(z, breite, tiefe, winkel):
    ring = Part.makeCylinder(16, breite, V(0, 0, z)).cut(
        Part.makeCylinder(15 - tiefe, breite, V(0, 0, z))
    )
    return ring.common(Part.makeCylinder(16, breite, V(0, 0, z), V(0, 0, 1), winkel))


mantelwelle = (
    Part.makeCylinder(15, 100, V(0, 0, -100))
    .cut(_umfangsnut(-50, 8, 4, 120))
    .cut(_umfangsnut(-80, 12, 3, 90))
    .removeSplitter()
)
mantel_namen = [
    f"Face{i + 1}"
    for i, f in enumerate(mantelwelle.Faces)
    if isinstance(f.Surface, Part.Cylinder) and f.Surface.Radius < 14.0
]
mantel = sorted(vp.mantelnuten(mantelwelle, LAENGS, RADIAL, mantel_namen), key=lambda n: n.a_von)
pruefe(
    [(round(n.radius, 3), round(n.a_von, 2), round(n.a_bis, 2), round(n.phi_bis - n.phi_von, 1))
     for n in mantel] == [(12.0, -80.0, -68.0, 90.0), (11.0, -50.0, -42.0, 120.0)],
    f"Mantelnuten: {mantel}",
)  # fmt: skip
w_mantel = vp.Planwerte(
    form=ff.scheibe(4.0),
    stange_radius=16.0,
    zustellung=2.0,
    zeilenabstand=3.2,
    aufmass=0.0,
    a_stange_vorne=1.0,
    a_futter=-120.0,
)
mb = vp.planen(vp.netz_ohne(mantelwelle, []), LAENGS, RADIAL, w_mantel, [], mantelnuten_=mantel)
pruefe(mb.mantelnuten == 2 and mb.flaechen == 2, f"Mantelnuten gefräst: {mb.mantelnuten}")
pruefe(abs(mb.r_min - 11.0) < 1e-6, f"tiefste Spitze {mb.r_min}")
abtrag_m = rm.Stange(16.0, -120.0, 1.0)
abtrag_m.fahre_stuecke(
    [(p.a, p.r, p.phi, p.q) for p, n in zip(mb.punkte, mb.punkte[1:], strict=False) if not n.eilgang],
    [(n.a, n.r, n.phi, n.q) for p, n in zip(mb.punkte, mb.punkte[1:], strict=False) if not n.eilgang],
    ff.scheibe(4.0),
)  # fmt: skip
netz_m = vh.vernetze(mantelwelle, 0.01)
genau_m = rm.teilradien(netz_m, LAENGS, RADIAL, abtrag_m, rm.GENAU)
vergleich_m = rm.vergleiche(abtrag_m, rm.teilradien(netz_m, LAENGS, RADIAL, abtrag_m), 0.0, genau_m)
pruefe(vergleich_m.kleinster >= -rm.BLAU_AB, f"Mantelnut: ins Teil {vergleich_m.kleinster:.3f}")
grad = np.degrees(abtrag_m.phi) % 360.0
for nut in mantel:
    # der Grund: längs innen, rundum so weit, wie die Stirn an die Enden kommt
    rand = math.degrees(math.asin(4.01 / nut.radius)) + 2.0
    zeilen_m = (abtrag_m.a > nut.a_von + 0.3) & (abtrag_m.a < nut.a_bis - 0.3)
    drin = (grad - nut.phi_von) % 360.0
    spalten_m = (drin > rand) & (drin < nut.phi_bis - nut.phi_von - rand)
    rest_m = (abtrag_m.r - genau_m)[np.ix_(zeilen_m, spalten_m)]
    hoechst = float(np.nanmax(rest_m)) if rest_m.size else math.inf
    pruefe(hoechst < 0.05, f"Grund R {nut.radius}: Rest {hoechst:.3f}")
print(ascii(f"Mantelnut: {mb.mantelnuten} Nuten, {mb.lagen} Lagen, {mb.zeilen} Fahrten, "
            f"{vb.dauer(mb, 500.0):.2f} min, ins Teil {vergleich_m.kleinster:.3f}"))  # fmt: skip

# Rampe in einer Richtung (P-2026-10-18-57, wie die Vollnut im Quader, P-29): Kommt die Rampe am
# Eintauchwinkel auf der Länge der Nut eine ganze Zustellung tief (hier mit 15°: die kürzere, 11 mm
# lang, · tan 15° ≥ 2 mm), je Lage hin hinab und eben zurück – keine Kehre, nicht mehr Fahrten als das Zickzack, nichts
# ins Teil. Mit 5° bleibt es beim Zickzack (die Nut ist dafür zu kurz).
mb_ein = vp.planen(
    vp.netz_ohne(mantelwelle, []), LAENGS, RADIAL,
    dataclasses.replace(w_mantel, eintauchwinkel=15.0), [], mantelnuten_=mantel,
)  # fmt: skip
kehren_ein, _rampen = vb.kehren(mb_ein.punkte)
kehren_zz, _rampen = vb.kehren(mb.punkte)
pruefe(kehren_ein == 0, f"Mantelnut mit 15°: {kehren_ein} Kehren")
pruefe(kehren_zz > 0, f"Mantelnut mit 5°: {kehren_zz} Kehren – kein Zickzack mehr?")
pruefe(mb_ein.zeilen <= mb.zeilen, f"Mantelnut einweg: {mb_ein.zeilen} statt {mb.zeilen} Fahrten")
abtrag_e = rm.Stange(16.0, -120.0, 1.0)
abtrag_e.fahre_stuecke(
    [(p.a, p.r, p.phi, p.q) for p, n in zip(mb_ein.punkte, mb_ein.punkte[1:], strict=False) if not n.eilgang],
    [(n.a, n.r, n.phi, n.q) for p, n in zip(mb_ein.punkte, mb_ein.punkte[1:], strict=False) if not n.eilgang],
    ff.scheibe(4.0),
)  # fmt: skip
vergleich_e = rm.vergleiche(abtrag_e, rm.teilradien(netz_m, LAENGS, RADIAL, abtrag_e), 0.0, genau_m)
pruefe(
    vergleich_e.kleinster >= -rm.BLAU_AB, f"Mantelnut einweg: ins Teil {vergleich_e.kleinster:.3f}"
)
print(
    ascii(f"Mantelnut einweg: {mb_ein.zeilen} Fahrten (Zickzack {mb.zeilen}), Kehren {kehren_ein}")
)


# Die Zeilen an den Wänden im Gleichlauf (P-2026-10-02-23): Liegt das Material vorn (die Zeile
# längs vor der Mitte), fällt φ für M3, hinten steigt es; andersherum (M4) umgekehrt – gleich
# viele Fahrten.
def wandzeilen(bahn, nut):
    mitte = (nut.a_von + nut.a_bis) / 2
    ergebnis = []
    for p, q in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        if q.eilgang or abs(q.a - p.a) > 1e-9 or abs(q.r - nut.radius) > 1e-6:
            continue
        if abs(q.a - mitte) < 1e-6 or not nut.a_von < q.a < nut.a_bis or abs(q.phi - p.phi) < 1e-9:
            continue
        ergebnis.append((q.a > mitte, q.phi > p.phi))
    return ergebnis


zeilen_w = wandzeilen(mb, mantel[0])
pruefe(zeilen_w and all(steigt != vorn for vorn, steigt in zeilen_w), f"Wände M3: {zeilen_w}")
mb_gegen = vp.planen(
    vp.netz_ohne(mantelwelle, []),
    LAENGS,
    RADIAL,
    dataclasses.replace(w_mantel, gleichlauf=False),
    [],
    mantelnuten_=mantel,
)
zeilen_g = wandzeilen(mb_gegen, mantel[0])
pruefe(zeilen_g and all(steigt == vorn for vorn, steigt in zeilen_g), f"Wände M4: {zeilen_g}")
pruefe(mb_gegen.zeilen == mb.zeilen, f"M4: {mb_gegen.zeilen} statt {mb.zeilen} Fahrten")
w_breit = dataclasses.replace(w_mantel, form=ff.scheibe(4.5))
try:
    vp.planen(vp.netz_ohne(mantelwelle, []), LAENGS, RADIAL, w_breit, [], mantelnuten_=mantel)
    pruefe(False, "Fräser Ø 9 in der Nut 8: keine Meldung")
except ValueError as meldung:
    pruefe("Ø 9" in str(meldung) and "8" in str(meldung), f"Fräser Ø 9: {meldung}")

# Ohne ebene Fläche, ohne ebene Stirn, Zeilenabstand zu groß: ein Satz.
for werte_falsch, flaechen_falsch, text in (
    (werte, [], "keine Fläche"),
    (vp.Planwerte(ff.kugel(3.0), 12.0, 2.0, 1.0, 0.0, 1.0, -60.0), ebenen, "Kugel"),
    (vp.Planwerte(ff.scheibe(3.0), 12.0, 2.0, 7.0, 0.0, 1.0, -60.0), ebenen, "Zeilenabstand"),
):
    try:
        vp.planen(netz, LAENGS, RADIAL, werte_falsch, flaechen_falsch)
    except ValueError as grund:
        pruefe(len(str(grund)) > 10, f"{text}: kein Satz")
    else:
        pruefe(False, f"{text}: keine Fehlermeldung")

# --- Der Abtrag mit Versatz quer (restmaterial) ----------------------------------------------
stange = rm.Stange(12.0, -60.0, 1.0)
von, nach = [], []
for vorher, punkt in zip(bahn.punkte, bahn.punkte[1:], strict=False):
    if not punkt.eilgang:
        von.append((vorher.a, vorher.r, vorher.phi, vorher.q))
        nach.append((punkt.a, punkt.r, punkt.phi, punkt.q))
stange.fahre_stuecke(von, nach, 3.0)
i20 = int(np.argmin(np.abs(stange.a + 20.0)))


def rest_bei(grad):
    return float(stange.r[i20, int(round(grad)) % len(stange.phi)])


for grad, soll in (
    (0, 8.0),
    (20, 8.0 / math.cos(math.radians(20))),
    (36, 8.0 / math.cos(math.radians(36))),
):
    pruefe(
        abs(rest_bei(grad) - soll) < 0.02,
        f"Rest bei {grad}°: {rest_bei(grad):.3f}, soll {soll:.3f}",
    )
pruefe(rest_bei(45) == 12.0, f"Rest bei 45°: {rest_bei(45)} – neben der Abflachung weggenommen")
pruefe(rest_bei(180) == 12.0, "gegenüber weggenommen")
i33 = int(np.argmin(np.abs(stange.a + 33.0)))
pruefe(float(stange.r[i33, 0]) == 12.0, f"hinter der Wand weggenommen: {stange.r[i33, 0]}")

# Die Kugel um 2 quer versetzt: Der Strahl durch ihre Mitte trifft sie dort, wo sie liegt.
kugel = rm.Stange(40.0, -50.0, 1.0)
kugel.schnitte([-20.0], [8.0], [0.0], ff.kugel(3.0), [2.0])
i_k = int(np.argmin(np.abs(kugel.a + 20.0)))
mitte = math.hypot(11.0, 2.0)
pruefe(
    abs(float(kugel.r[i_k, 10]) - (mitte - 3.0)) < 0.01,
    f"Kugel versetzt bei 10°: {kugel.r[i_k, 10]}",
)
pruefe(float(kugel.r[i_k, 350]) == 40.0, "Kugel versetzt: gegenüber des Versatzes weggenommen")
# Bei 0° geht der Strahl 2 mm an der Mitte vorbei: er trifft die Kugel bei 11 − √(9 − 4).
pruefe(
    abs(float(kugel.r[i_k, 0]) - (11.0 - math.sqrt(5.0))) < 0.01,
    f"Kugel versetzt bei 0°: {kugel.r[i_k, 0]}",
)
# Ohne Versatz wie vorher: unter der Spitze 8, 10° daneben höher.
ohne = rm.Stange(40.0, -50.0, 1.0)
ohne.schnitte([-20.0], [8.0], [0.0], ff.kugel(3.0))
pruefe(
    abs(float(ohne.r[i_k, 0]) - 8.0) < 1e-9 and float(ohne.r[i_k, 10]) > 8.0, "Kugel ohne Versatz"
)
print("Abtrag mit Versatz ok")

# --- Die CAM-Operation im Job ---------------------------------------------------------------
schaft = wz.Werkzeug(nummer=1, durchmesser=6, schneiden=3, schneidenlaenge=16)
schaft.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.PLANEN, ae=4, ap=2, vc=120, fz=0.05)]
kugelfraeser = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)
kugelfraeser.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=6, vc=150, fz=0.04)]
bibliothek = wz.Bibliothek([schaft, kugelfraeser])
ue.uebergeben(bibliothek)
pruefe(
    vplan.zeilenabstand_vorschlag(schaft, schaft.einsaetze(wz.ALLE)[0]) == 4.0,
    "ae als Zeilenabstand",
)
pruefe(abs(vplan.zeilenabstand_vorschlag(schaft, None) - 3.6) < 1e-9, "ohne Einsatz: 60 % von D")

doc = FreeCAD.newDocument("Plan")
doc.UndoMode = 1
welle = doc.addObject("Part::Feature", "Welle")
welle.Shape = (
    Part.makeCylinder(10, 40, V(), V(1, 0, 0))
    .cut(Part.makeBox(20, 20, 20, V(10, 8, -10)))
    .removeSplitter()
)
doc.recompute()
stirn = next(
    f
    for f in welle.Shape.Faces
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
)
achse = va.zugewiesen("C")
lage = vr.berechne(welle.Shape, stirn, achse, durchmesser=24)
job = vr.richte_ein(doc, welle, lage, vr.Stange(24.0, frei_hinten=17.5), achse, beschriftung="W")
tc1 = js.controller_ohne_transaktion(doc, job, schaft, schaft.einsaetze(wz.ALLE)[0])
tc2 = js.controller_ohne_transaktion(doc, job, kugelfraeser, kugelfraeser.einsaetze(wz.ALLE)[0])
doc.recompute()
klon = vr.modell(job)
flach_im_job = next(
    f"Face{i + 1}"
    for i, f in enumerate(klon.Shape.Faces)
    if vr.ist_eben(f) and abs(vr.aussennormale(f).dot(V(0, 0, 1))) < 1e-6
)
stirn_im_job = next(
    f"Face{i + 1}"
    for i, f in enumerate(klon.Shape.Faces)
    if vr.ist_eben(f) and abs(vr.aussennormale(f).dot(V(0, 0, 1)) - 1.0) < 1e-6
)

op = vplan.lege_an(job, tc1, achse, zustellung=2.0, zeilenabstand=4.0, flaechen=[flach_im_job])
doc.recompute()
# Die Auflösung (T-009, aufloesung.py): Eigenschaft `Raster` da (0 = Vorschlag); gesetzt rechnet
# die Operation damit, 0 wieder genau die bisherige.


def _raster_bahn():
    return [(c.Name, tuple(sorted(c.Parameters.items()))) for c in op.Path.Commands]


_raster_vorgabe = _raster_bahn()
assert au.EIGENSCHAFT in op.PropertiesList and float(op.Raster) == 0.0, "Raster fehlt"
au.setze(op, 0.05)
doc.recompute()
au.setze(op, 0)
doc.recompute()
assert _raster_bahn() == _raster_vorgabe, "Raster 0 ist nicht die Vorgabe"
pruefe(op.Label == "Plan indexiert T1" and op in job.Operations.Group, f"{op.Label}")
pruefe(vo.ist_rundum(op) and vplan.ist_plan(op) and not vo.ist_schruppen(op), "Art")
pruefe(js.operationsart(op) == "vierachs_plan", f"Art: {js.operationsart(op)}")
pruefe(js.EINSATZ_NACH_OPERATION["vierachs_plan"][0] == wz.PLANEN, "Einsatz Planen")
pruefe(
    (op.Ebenen, op.Lagen, op.Zeilen) == (1, 2, 6),
    f"Operation: {op.Ebenen}, {op.Lagen}, {op.Zeilen}",
)
befehle = op.Path.Commands
namen = [b.Name for b in befehle]
pruefe(namen[2:5] == ["G0", "G0", "G93"] and namen[-1] == "G94", f"Befehle: {namen[:6]}")
schnitte = [b for b in befehle if b.Name == "G1"]
pruefe(all("Y" in b.Parameters for b in schnitte), "G1 ohne Y in der Operation")
c_werte = {round(b.Parameters["C"], 6) for b in schnitte}
pruefe(len(c_werte) == 1, f"C steht nicht: {sorted(c_werte)[:4]}")
x_werte = [b.Parameters["X"] for b in schnitte]
pruefe(
    abs(min(x_werte) - 8.0) < 1e-6 and max(x_werte) <= 12.0 + 1e-6,
    f"X {min(x_werte)} … {max(x_werte)}",
)
tief = [b.Parameters["Z"] for b in schnitte if b.Parameters["X"] < 10.0 - 1e-6]
pruefe(
    min(tief) >= -27.0 - 1e-6 and max(tief) <= -13.0 + 1e-6,
    f"unten längs {min(tief)} … {max(tief)}",
)
pruefe(op.getEditorMode("Lagen") == ["ReadOnly"], "Lagen änderbar")

# Ändern: feiner, mit Aufmaß – vier Lagen bis 8,5, drei Zeilen je Lage.
vplan.aendere(op, tc1, zustellung=1.0, zeilenabstand=3.0, aufmass=0.5)
doc.recompute()
pruefe((op.Lagen, op.Zeilen) == (4, 12), f"geändert: {op.Lagen} Lagen, {op.Zeilen} Zeilen")
x_werte = [b.Parameters["X"] for b in op.Path.Commands if b.Name == "G1"]
pruefe(abs(min(x_werte) - 8.5) < 1e-6, f"mit Aufmaß: {min(x_werte)}")

# Der Kugelfräser, die Stirn allein: ein Satz statt der Bahn.
vplan.aendere(op, tc2, zustellung=1.0, zeilenabstand=3.0, aufmass=0.0)
doc.recompute()
pruefe("ebener Stirn" in op.Path.Commands[1].Name, f"Kugelfräser: {op.Path.Commands[1].Name}")
vplan.aendere(op, tc1, zustellung=2.0, zeilenabstand=4.0, aufmass=0.0, flaechen=[stirn_im_job])
doc.recompute()
# Wortlaut seit der Textdurchsicht (P-2026-10-05-30): „… ist nichts, was ‚Plan indexiert‘ fräsen kann“.
pruefe("ist nichts, was" in op.Path.Commands[1].Name, f"nur die Stirn: {op.Path.Commands[1].Name}")
vplan.aendere(op, tc1, zustellung=2.0, zeilenabstand=4.0, aufmass=0.0, flaechen=[flach_im_job])
doc.recompute()
pruefe(op.Lagen == 2, "zurück: Lagen")

# Speichern und Laden: dieselbe Bahn.
anzahl = len(op.Path.Commands)
pfad = os.path.join(tempfile.mkdtemp(), "plan.FCStd")
doc.saveAs(pfad)
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(pfad)
op = next(o for o in doc.Objects if vplan.ist_plan(o))
op.touch()
doc.recompute()
pruefe(len(op.Path.Commands) == anzahl, f"nach dem Laden {len(op.Path.Commands)} statt {anzahl}")
pruefe(op.getEditorMode("Zeilen") == ["ReadOnly"], "Zeilen nach dem Laden")
print(ascii(f"Operation: {anzahl} Befehle"))

# --- Schräg zur Achse (P-2026-10-03-09, Manuels D-Profil): eine Abflachung, die längs um 10°
# fällt – vorne 8 mm über der Achse, 40 mm weiter hinten 8 − 40 · tan 10° = 0,95 mm. Die Zeilen
# folgen ihr, nie unter die Fläche plus das, was die schräge Stirn bergauf braucht (R · tan α);
# zuletzt eine Schlichtlage mit dem Zeilenabstand für höchstens 0,01 mm Grat.
neigung = math.radians(10.0)
keil = Part.makeBox(20, 40, 60, V(0, -20, -50))
keil.rotate(V(0, 0, 0), V(0, 1, 0), 10.0)  # dreht die Unterseite x = 0 um die Querachse
keil.translate(V(8, 0, 0))
schraeg_welle = Part.makeCylinder(15, 45, V(0, 0, -45)).cut(keil).removeSplitter()
schraeg_namen = [f"Face{i + 1}" for i in range(len(schraeg_welle.Faces))]
schraeg = vp.ebenen(schraeg_welle, LAENGS, RADIAL, schraeg_namen)
pruefe(len(schraeg) == 1, f"schräge Ebenen: {schraeg}")
if schraeg:
    s = schraeg[0]
    pruefe(
        abs(s.neigung - 10.0) < 0.01 and abs(s.hoehe(0.0) - 8.0) < 0.01,
        f"schräg: Neigung {s.neigung:.3f}°, vorne {s.hoehe(0.0):.3f}",
    )
    w_schraeg = dataclasses.replace(werte, stange_radius=17.0, zeilenabstand=4.0, a_futter=-80.0)
    sb = vp.planen(vp.netz_ohne(schraeg_welle, [s.name]), LAENGS, RADIAL, w_schraeg, schraeg)
    hub = 3.0 * math.tan(neigung)
    im_bereich = [p for p in sb.punkte if not p.eilgang and s.a_von <= p.a <= s.a_bis]
    knapp = min(p.r - (s.hoehe(p.a) + hub) for p in im_bereich)
    pruefe(-1e-6 <= knapp < 0.05, f"schräg: knappste Spitze {knapp:.4f} über Fläche + R·tan α")
    fein = vp.grat_zeilenabstand(s, 3.0)
    pruefe(fein is not None and 0.5 < fein < 4.0, f"feiner Zeilenabstand {fein}")
    unten = sorted({round(p.q, 6) for p in im_bereich if p.r - (s.hoehe(p.a) + hub) < 1e-6})
    abstaende = np.diff(unten) if len(unten) > 1 else np.array([0.0])
    pruefe(
        len(unten) > 3 and float(np.max(abstaende)) <= fein + 1e-6,
        f"Schlichtlage: {len(unten)} Zeilen, größter Abstand {float(np.max(abstaende)):.3f}",
    )
    print(ascii(f"Schraeg 10 Grad: {sb.lagen} Lagen, {sb.zeilen} Zeilen, fein {fein:.2f} mm"))

# --- Zur Achse hin (Manuel, 2026-10-11, Frage 10): ein Klotz neben der Achse (x 5 … 12) wie die
# Nase seines Testteils; seine Seite x = 5 schaut zur Achse, davor ist frei. Ohne `zur_achse`
# zählt sie nicht, mit ihr (der Vorgabe) steht die Spitze 5 unter der Mitte (φ 180°, Tiefe −5) –
# nie tiefer. Ein zweiter Klotz gegenüber (x −12 … −5) steht davor: Dann zählen die beiden
# Innenseiten nicht – wie die Wände einer Nut.
nase = Part.makeBox(7, 10, 20, V(5, -5, -30))
nase_namen = [f"Face{i + 1}" for i in range(len(nase.Faces))]
innen = next(
    f"Face{i + 1}"
    for i, f in enumerate(nase.Faces)
    if (vr.aussennormale(f) - V(-1, 0, 0)).Length < 1e-6
)
pruefe(
    innen not in [e.name for e in vp.ebenen(nase, LAENGS, RADIAL, nase_namen, zur_achse=False)],
    "zur Achse hin ohne zur_achse angenommen",
)
zur_achse = vp.ebenen(nase, LAENGS, RADIAL, [innen])
zwei = nase.fuse(Part.makeBox(7, 10, 20, V(-12, -5, -30)))
zwei_namen = [f"Face{i + 1}" for i in range(len(zwei.Faces))]
gegenueber = [
    e.name for e in vp.ebenen(zwei, LAENGS, RADIAL, zwei_namen) if e.hoechste <= vp.GERADE
]
pruefe(not gegenueber, f"Innenseiten gegenüber angenommen: {gegenueber}")
pruefe(len(zur_achse) == 1, f"zur Achse hin: {zur_achse}")
if zur_achse:
    z = zur_achse[0]
    pruefe(abs(abs(z.phi) - 180.0) < 1e-6 and abs(z.tiefe + 5.0) < 1e-6, f"innen: {z}")
    nb = vp.planen(
        vp.netz_ohne(nase, [innen]),
        LAENGS,
        RADIAL,
        dataclasses.replace(werte, stange_radius=15.0, a_futter=-60.0),
        zur_achse,
    )
    im_vorschub = [p for p in nb.punkte if not p.eilgang]
    pruefe(
        nb.flaechen == 1 and abs(nb.r_min + 5.0) < 1e-9,
        f"innen: {nb.flaechen} Flächen, tiefste Spitze {nb.r_min}",
    )
    pruefe(min(p.r for p in im_vorschub) >= -5.0 - 1e-9, "innen: Spitze tiefer als die Fläche")
    pruefe(
        vp.schaft_lage(nase, z, LAENGS, RADIAL, 15.0) is None, "die Innenseite als Seite genommen"
    )

# --- Seiten mit dem Schaft (Frage 10, „beide variationen anbieten“): die Seite y = 5 des Klotzes.
# Die Werkzeugachse liegt in ihr (C auf 0°, längs +x), der Umfang 3 + Rand vor ihr, in Lagen bis
# an ihre Unterkante x = 5 – die Schneide muss 10 lang sein (Stange 15 − 5); mit 8 nicht.
seite = next(
    f"Face{i + 1}"
    for i, f in enumerate(nase.Faces)
    if (vr.aussennormale(f) - V(0, 1, 0)).Length < 1e-6
)
e_seite = vp.ebenen(nase, LAENGS, RADIAL, [seite])[0]
lage = vp.schaft_lage(nase, e_seite, LAENGS, RADIAL, 15.0)
pruefe(lage is not None and abs(lage[2] - 10.0) < 1e-6, f"Schaft: Weg {lage and lage[2]}")
virt = vp.mit_dem_schaft(nase, e_seite, LAENGS, RADIAL, 15.0, 3.0, 0.0, 20.0, vp.TOLERANZ)
q_soll = 5.0 + 3.0 + vp.TOLERANZ + vb.RAND
pruefe(
    virt is not None
    and abs(virt.phi) < 1e-6
    and abs(virt.tiefe - 5.0) < 1e-6
    and abs(virt.q_von - q_soll) < 1e-6,
    f"Schaft: {virt}",
)
pruefe(
    vp.mit_dem_schaft(nase, e_seite, LAENGS, RADIAL, 15.0, 3.0, 0.0, 8.0, vp.TOLERANZ) is None,
    "Schaft mit zu kurzer Schneide",
)
# So tief reicht der Fräser hinunter: Schneide und Hals (die Auskragung N) – die Lagen darüber hat
# die Schneide schon fertig, am Hals ist Platz (P-2026-10-17-37).
_T = types.SimpleNamespace
pruefe(
    abs(vplan.reicht_hinab(_T(Tool=_T(CuttingEdgeHeight=8.0, NeckHeight=4.0)), 2.0) - 12.0) < 1e-9
    and abs(vplan.schneidenlaenge(_T(Tool=_T(CuttingEdgeHeight=8.0, NeckHeight=4.0))) - 8.0) < 1e-9
    and vplan.reicht_hinab(_T(Tool=None), 2.0) == 0.0
    # Zustellung über die Schneide hinaus: zwischen den Lagen bliebe ein Band – nur die Schneide
    and abs(vplan.reicht_hinab(_T(Tool=_T(CuttingEdgeHeight=8.0, NeckHeight=4.0)), 9.0) - 8.0)
    < 1e-9
    and abs(
        vplan.reicht_werkzeug(
            wz.Werkzeug(nummer=9, durchmesser=6, schneidenlaenge=8, hals_laenge=4), 2.0
        )
        - 12.0
    )
    < 1e-9,
    "reicht_hinab: Schneide und Hals",
)
pruefe(
    vp.mit_dem_schaft(nase, e_seite, LAENGS, RADIAL, 15.0, 3.0, 0.0, 8.0 + 2.0, vp.TOLERANZ)
    is not None,
    "Schaft mit Schneide 8 und Hals 2 (reicht 10)",
)
if virt is not None:
    sb = vp.planen(
        vp.netz_ohne(nase, [seite]),
        LAENGS,
        RADIAL,
        dataclasses.replace(werte, stange_radius=15.0, a_futter=-60.0),
        [virt],
    )
    vor = [p for p in sb.punkte if not p.eilgang]
    pruefe(
        bool(vor) and all(abs(p.phi) < 1e-6 and abs(p.q - q_soll) < 1e-6 for p in vor),
        f"Schaft: C oder q daneben {sorted({(round(p.phi, 3), round(p.q, 3)) for p in vor})}",
    )
    pruefe(
        bool(vor) and 5.0 - 1e-9 <= min(p.r for p in vor) < 5.0 + 0.1,
        f"Schaft: tiefste Spitze {min((p.r for p in vor), default=None)}",
    )
    pruefe(sb.lagen >= 5, f"Schaft: {sb.lagen} Lagen")

# --- Stiche von der offenen Seite (P-2026-10-12-146) ------------------------------------------
# Eine Abflachung, die vorne offen ausläuft (x = 8, a −30 … 0, die Stange 1 mm weiter): das
# 3-Achs-Räumen im Rahmen der Fläche statt der Zeilen – aus der Luft vor der Stange hinein, die
# Rundachse fest, nicht ins Teil, über der Fläche nichts übrig. Eine Fläche zwischen zwei Wänden
# (oben, eine Tasche) fährt weiter Zeilen.
offen_welle = (
    Part.makeCylinder(10, 40, V(0, 0, -40))
    .cut(Part.makeBox(10, 30, 31, V(8, -15, -30)))
    .removeSplitter()
)
offen_ebenen = vp.ebenen(
    offen_welle, LAENGS, RADIAL, [f"Face{i + 1}" for i in range(len(offen_welle.Faces))]
)
pruefe(len(offen_ebenen) == 1, f"offen: Ebenen {offen_ebenen}")
offen_netz = vp.netz_ohne(offen_welle, [e.name for e in offen_ebenen])
offen_werte = vp.Planwerte(
    form=ff.scheibe(3.0),
    stange_radius=12.0,
    zustellung=2.0,
    zeilenabstand=2.5,
    aufmass=0.0,
    a_stange_vorne=1.0,
    a_futter=-60.0,
)
offen_teilnetz = vh.vernetze(offen_welle, 0.01)
zeilen_vor = []  # die Sätze der Zeilen, gegen die Stiche
for weg in (vp.WEG_ZEILEN, vp.WEG_STICHE_GLEICHLAUF, vp.WEG_STICHE_GEGENLAUF):
    b = vp.planen(
        offen_netz,
        LAENGS,
        RADIAL,
        dataclasses.replace(offen_werte, weg=weg),
        offen_ebenen,
        form_teil=offen_welle,
    )
    vor = [p for p, n in zip(b.punkte, b.punkte[1:], strict=False) if not n.eilgang]
    pruefe(all(abs(p.phi) < 1e-6 for p in b.punkte[1:]), f"{weg}: C dreht")
    abtrag = rm.Stange(12.0, -60.0, 1.0)
    abtrag.fahre_stuecke(
        [(p.a, p.r, p.phi, p.q) for p, n in zip(b.punkte, b.punkte[1:], strict=False) if not n.eilgang],
        [(n.a, n.r, n.phi, n.q) for p, n in zip(b.punkte, b.punkte[1:], strict=False) if not n.eilgang],
        ff.scheibe(3.0),
    )  # fmt: skip
    vergleich = rm.vergleiche(
        abtrag,
        rm.teilradien(offen_teilnetz, LAENGS, RADIAL, abtrag),
        0.0,
        rm.teilradien(offen_teilnetz, LAENGS, RADIAL, abtrag, rm.GENAU),
    )
    pruefe(vergleich.kleinster >= -rm.BLAU_AB, f"{weg}: ins Teil {vergleich.kleinster:.3f}")
    a_raster = abtrag.a[:, None] + 0 * abtrag.phi[None, :]
    phi_raster = np.degrees(np.angle(np.exp(1j * abtrag.phi)))[None, :] + 0 * abtrag.a[:, None]
    ueber = (a_raster > -28.0) & (a_raster < -2.0) & (np.abs(phi_raster) < 30.0)
    rest = np.nanmax(np.where(ueber, vergleich.rest, np.nan))
    pruefe(rest < 0.3, f"{weg}: über der Fläche bleiben {rest:.2f} mm")
    if weg != vp.WEG_ZEILEN:
        # Aus der Luft hinein: Der erste Satz im Vorschub auf der Höhe einer Lage liegt vor der
        # Stange (a > 1 + Fräserradius); keiner taucht senkrecht ins Material.
        lage_hinein = [n for p, n in zip(b.punkte, b.punkte[1:], strict=False) if not n.eilgang]
        pruefe(
            bool(lage_hinein) and lage_hinein[0].a > 1.0 + 3.0 - 1e-6,
            f"{weg}: beginnt bei a {lage_hinein[0].a if lage_hinein else None}",
        )
        pruefe(
            [round(p.r, 6) for p in vor] != [round(p.r, 6) for p in zeilen_vor],
            f"{weg}: dieselbe Bahn wie die Zeilen",
        )
        print(
            ascii(f"  {weg}: {b.lagen} Lagen, {b.zeilen} Stiche, {len(vor)} Sätze, Rest {rest:.2f}")
        )
    else:
        zeilen_vor = vor
        print(
            ascii(
                f"  Zeilen: {b.lagen} Lagen, {b.zeilen} Zeilen, {len(vor)} Sätze, Rest {rest:.2f}"
            )
        )
# Zwischen zwei Wänden ist das Feld geschlossen: Die Stiche fahren in der Rampe im Kreis hinab,
# bleiben im Feld der Zeilen (längs bis a_bis + R + Überlauf) und fahren nicht ins Teil.
tasche = vp.planen(
    netz, LAENGS, RADIAL, dataclasses.replace(werte, weg=vp.WEG_STICHE_GLEICHLAUF), ebenen,
    form_teil=flach_welle,
)  # fmt: skip
tasche_vor = [n for p, n in zip(tasche.punkte, tasche.punkte[1:], strict=False) if not n.eilgang]
pruefe(
    bool(tasche_vor) and max(p.a for p in tasche_vor) <= -10.0 + 3.0 + vp.UEBERLAUF_LAENGS + 1e-6,
    f"Tasche: vorne bis a {max((p.a for p in tasche_vor), default=None)}",
)
abtrag = rm.Stange(12.0, -60.0, 1.0)
abtrag.fahre_stuecke(
    [(p.a, p.r, p.phi, p.q) for p, n in zip(tasche.punkte, tasche.punkte[1:], strict=False) if not n.eilgang],
    [(n.a, n.r, n.phi, n.q) for p, n in zip(tasche.punkte, tasche.punkte[1:], strict=False) if not n.eilgang],
    ff.scheibe(3.0),
)  # fmt: skip
flach_teilnetz = vh.vernetze(flach_welle, 0.01)
vergleich = rm.vergleiche(
    abtrag,
    rm.teilradien(flach_teilnetz, LAENGS, RADIAL, abtrag),
    0.0,
    rm.teilradien(flach_teilnetz, LAENGS, RADIAL, abtrag, rm.GENAU),
)
pruefe(vergleich.kleinster >= -rm.BLAU_AB, f"Tasche: ins Teil {vergleich.kleinster:.3f}")

# --- Die Nase: nirgends über die Rampe hinein (P-2026-10-12-165) --------------------------------
# Manuel (2026-10-12, mit Bild): „einfach von außen einfahren“ – die Zeilen an den Seiten der Nase
# beginnen vor der Stange in der Luft; die dicht an der Flosse, vorn von ihr verdeckt, fahren in
# der geräumten Zeile daneben hinab und quer hinein. Keine Rampe, nirgends ins Teil.
nase_doc = FreeCAD.openDocument(
    os.path.join(os.path.dirname(__file__), "..", "beispiele", "testteil_4achs_nase.FCStd"), True
)
nase_job = nase_doc.getObject("Job")
nase_op = next(o for o in nase_job.Operations.Group if vo.ist_schruppen(o))
nase_l, nase_r = FreeCAD.Vector(nase_op.Stangenachse), FreeCAD.Vector(nase_op.Werkzeugrichtung)
for seite in ("Face4", "Face6"):
    nase_bahn = vplan.bahn_fuer(
        nase_job, nase_job.Model.Group, nase_l, nase_r, ff.scheibe(6.0), 5.0, 5.4, 0.3,
        vo.vorgeschlagene_abstaende(6.0, nase_job), flaechen=[seite],
    )  # fmt: skip
    nase_rampen = sum(
        1
        for p, n in zip(nase_bahn.punkte, nase_bahn.punkte[1:], strict=False)
        if p.eintauchen and not n.eilgang and n.r < p.r - 1e-6
    )
    pruefe(nase_rampen == 0, f"Nase {seite}: {nase_rampen} Rampen")
    radius_n, a_hinten_n, a_vorne_n = vo.stange(nase_job, nase_l)
    nase_abtrag = rm.Stange(radius_n, a_hinten_n, a_vorne_n)
    paare = list(zip(nase_bahn.punkte, nase_bahn.punkte[1:], strict=False))
    nase_abtrag.fahre_stuecke(
        [(p.a, p.r, p.phi, p.q) for p, n in paare if not n.eilgang],
        [(n.a, n.r, n.phi, n.q) for p, n in paare if not n.eilgang],
        ff.scheibe(6.0),
    )
    nase_netz = vh.vernetze(nase_job.Model.Group[0].Shape, 0.05)
    nase_vergleich = rm.vergleiche(
        nase_abtrag, rm.teilradien(nase_netz, nase_l, nase_r, nase_abtrag), 0.0
    )
    pruefe(
        nase_vergleich.kleinster >= -rm.BLAU_AB,
        f"Nase {seite}: ins Teil {nase_vergleich.kleinster:.3f}",
    )
    print(
        ascii(
            f"Nase {seite}: {nase_rampen} Rampen, kleinster Abstand {nase_vergleich.kleinster:.2f}"
        )
    )
FreeCAD.closeDocument(nase_doc.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
