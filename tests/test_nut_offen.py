# Prüft offene Nuten (W-006 4.1 Punkt 6, P-2026-10-01-47) mit dem Standardfräser Ø 12 (ae 1,5,
# ap 25, vf 902) und Aufmaß 0,3: Platte 60 × 40 × 20. (a) Eine Nut 16 breit, 8 tief, längs X
# ganz durch – an beiden Enden offen: von einer Wand wie vom Grund aus erkannt, A (0, 20),
# B (60, 20), r 8. Die Bahn beginnt draußen in der Luft: kein Eintauchen, keine Rampe, keine
# Helix; im Quader die Nut leer bis auf den Grund, die Wände fertig, nirgends ins Teil, im
# Eilgang nichts. (b) Eine Nut, an x 0 offen, am anderen Ende ein Halbkreis um (32, 20): A der
# Halbkreis (geschlossen), B offen, 40 lang über alles; ebenso. (c) Eine geschlossene Nut bleibt
# geschlossen (beide Enden zu). (d) Wettbewerb wie im Assistenten: Die Nut ist schneller als die
# Kontur an den Wänden. Räumen auf dem Grund wäre nur scheinbar schneller – es schneidet zuerst
# in voller Breite, schneller als ae · ap · vf erlaubt (Wirkungsgrad über 100 %): Darum tritt es
# an Nutgründen nicht an. (e) In Bögen statt Kreisen (P-2026-10-02-22, Manuels Halbkreis): je
# Bogen im Gleichlauf (G3) von Wand zu Wand, quer zurück im Schnellvorschub (3 × vf) – dabei nichts
# abgetragen; der Schritt nach der Last (P-2026-10-02-56): im Mittel ae, in der Mitte der Bögen
# höchstens 1,7 ae, über 1,25 ae nie länger als eine Fräserbreite. (f) Eine offene Nut 30 breit – früher „zu breit“ (ein Kern bliebe in den
# Kreisen) – geht jetzt in Bögen, ebenso leer und nirgends ins Teil.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import bahn as bn
from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import kontur_bahn as kb
from camaddon import nut_bahn as nb
from camaddon import pruefstand as ps
from camaddon import raeumen_bahn as rb
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import vierachs_flaechen as vf

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
R, AE, AP, VF = 6.0, 1.5, 25.0, 902.0
form = ff.scheibe(R)
platte = Part.makeBox(60, 40, 20)


def waende_und_grund(teil):
    waende, grund = [], []
    for i, f in enumerate(teil.Faces):
        bb = f.BoundBox
        if abs(bb.ZMin - 12.0) < 1e-6 and bb.ZMax - bb.ZMin > 1.0 and kb.ist_wand(f):
            waende.append(f"Face{i + 1}")
        elif abs(bb.ZMax - 12.0) < 1e-6 and bb.ZMax - bb.ZMin < 1e-6:
            grund.append(f"Face{i + 1}")
    return waende, grund


def werte():
    return nb.Nutwerte(
        fraeser_radius=R, zustellung=AP, zeilenabstand=AE, oben=20.0, sicher=25.0, aufmass=0.3,
        schneidenlaenge=26.0, eintauchwinkel=3.0, vorschub=VF, eintauchen=VF * 0.3,
    )  # fmt: skip


def pruefe_bahn(name, teil, nut, halb=8.0):
    bahn = nb.planen(werte(), [nut])
    k = ps.messen([ps.Bahnlauf(bahn.punkte, VF, VF * 0.3)], teil, (0, 60, 0, 40), 20.0, form,
                  AE, AP, ebenen_z=[12.0], aufmass=0.0)  # fmt: skip
    print(ascii(f"{name}: {bahn.boegen} Bögen, {bahn.zeit:.2f} min | {ps.zeile(k)}"))
    pruefe(k.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"{name}: ins Teil {k.einschnitt:.3f}")
    pruefe(k.eilgang_abtrag <= 1e-9, f"{name}: im Eilgang {k.eilgang_abtrag:.1f} mm³")
    pruefe(k.schnell_abtrag <= 1e-9, f"{name}: im Schnellvorschub {k.schnell_abtrag:.1f} mm³")
    pruefe(bahn.boegen > 0, f"{name}: {bahn.boegen} Bögen")
    boegen = [p for p in bahn.punkte if p.bogen is not None]
    pruefe(boegen and not any(p.bogen[2] for p in boegen), f"{name}: nicht im Gleichlauf (G3)")
    schnell = [p for p in bahn.punkte if p.anteil > 1.0]
    pruefe(schnell and all(abs(p.anteil - nb.RUECKWEG) < 1e-9 for p in schnell),
           f"{name}: kein Rückweg im Schnellvorschub")  # fmt: skip
    pruefe(k.eintauchungen == 0 and k.rampen == 0, f"{name}: {k.eintauchungen} Eintauchen, "
           f"{k.rampen} Rampen")  # fmt: skip
    pruefe(k.rest <= ps.REST_ZULAESSIG, f"{name}: Rest {k.rest:.2f} auf dem Grund")
    # Die Wände fertig: im Quader neben ihnen nichts mehr über dem Grund.
    q = rm.Quader(0, 60, 0, 40, 0, 20, 0.25)
    for von, nach in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        stuecke = ps._stuecke(von, nach)
        q.fahre_stuecke([s[0] for s in stuecke], [s[1] for s in stuecke], form)
    soll = hf.hoehen(vf.vernetze(teil, 0.01).netz, q.x, q.y)
    rest = q.h - soll
    xs, ys = np.meshgrid(q.x, q.y, indexing="ij")
    grund = soll < 12.5
    # Eine Zelle Abstand zur Wand: Halb auf der Kante zählte die Zelle die Wandhöhe.
    innen = grund.copy()
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        innen &= np.roll(np.roll(grund, di, 0), dj, 1)
    in_der_nut = (np.abs(ys - 20.0) < halb - 0.5) & innen
    pruefe(np.max(rest[in_der_nut]) < 0.05, f"{name}: in der Nut {np.max(rest[in_der_nut]):.2f}")
    daneben = np.abs(ys - 20.0) > halb + 0.5
    pruefe(np.max(np.abs(rest[daneben])) < 1e-6, f"{name}: daneben angeschnitten")
    # ae ist die Last (Spezifikation Strategien 12.1 (a)), im feinen Raster: in der Mitte der
    # Bögen und beim Einfahren höchstens LAST_KURZ · ae, über LAST_DAUERND · ae nie länger als
    # eine Fräserbreite am Stück.
    k = ps.messen([ps.Bahnlauf(bahn.punkte, VF, VF * 0.3)], teil, (0, 60, 0, 40), 20.0, form,
                  AE, AP, ebenen_z=[12.0], raster=0.1)  # fmt: skip
    print(ascii(f"{name} Last: {ps.zeile(k)}"))
    pruefe(k.eingriff_max <= bn.LAST_KURZ and k.last_lang <= 2 * R, f"{name}: {ps.zeile(k)}")
    return bahn


# --- (a) An beiden Enden offen ----------------------------------------------------------------
ii = platte.cut(Part.makeBox(60, 16, 8, V(0, 12, 12))).removeSplitter()
waende, grund = waende_und_grund(ii)
for wahl in (waende[:1], grund):
    gefunden = nb.nuten(ii, wahl)
    pruefe(len(gefunden) == 1, f"II {wahl}: {len(gefunden)} Nuten")
nut = nb.nuten(ii, grund)[0]
pruefe(nut.offen_a and nut.offen_b, f"II: offen {nut.offen_a}, {nut.offen_b}")
pruefe(abs(nut.radius - 8.0) < 1e-6 and abs(nut.gesamtlaenge - 60.0) < 1e-6, f"II: {nut}")
ends = sorted([nut.a, nut.b])
pruefe(np.allclose(ends, [(0.0, 20.0), (60.0, 20.0)], atol=1e-6), f"II: A {nut.a}, B {nut.b}")
bahn_ii = pruefe_bahn("II", ii, nut)

# --- (b) An einem Ende offen, am anderen der Halbkreis --------------------------------------------
loch = Part.makeBox(32, 16, 8, V(0, 12, 12)).fuse(Part.makeCylinder(8, 8, V(32, 20, 12)))
uu = platte.cut(loch.removeSplitter()).removeSplitter()
waende, grund = waende_und_grund(uu)
nut_u = nb.nuten(uu, waende[:1])
pruefe(len(nut_u) == 1, f"U: {len(nut_u)} Nuten")
nut_u = nut_u[0]
pruefe(not nut_u.offen_a and nut_u.offen_b, f"U: offen {nut_u.offen_a}, {nut_u.offen_b}")
pruefe(np.allclose([nut_u.a, nut_u.b], [(32.0, 20.0), (0.0, 20.0)], atol=1e-6), f"U: {nut_u}")
pruefe(abs(nut_u.gesamtlaenge - 40.0) < 1e-6, f"U: {nut_u.gesamtlaenge}")
pruefe_bahn("U", uu, nut_u)

# --- (c) Geschlossen bleibt geschlossen -----------------------------------------------------------
zu = platte.cut(
    Part.makeBox(20, 16, 8, V(20, 12, 12))
    .fuse(Part.makeCylinder(8, 8, V(20, 20, 12)))
    .fuse(Part.makeCylinder(8, 8, V(40, 20, 12)))
    .removeSplitter()
).removeSplitter()
waende, grund = waende_und_grund(zu)
geschlossen = nb.nuten(zu, grund)
pruefe(len(geschlossen) == 1 and not geschlossen[0].offen, f"zu: {geschlossen}")

# --- (e) Der Schritt der Bögen nach der Last: In der schmalen Nut überstreicht jeder Bogen die
# ganze Breite auf kurzem Weg – der Schritt kleiner als ae; in breiten etwas größer (über
# LAST_DAUERND · ae höchstens eine Fräserbreite am Stück) ------------------------------------------
schmal = nb._bogenschritt(8.0 - R - 0.3, R, AE)
breit = nb._bogenschritt(40.0 - R - 0.3, R, AE)
pruefe(0.55 < schmal < 0.6 and AE < breit < bn.LAST_DAUERND * AE,
       f"Schritt: schmal {schmal:.3f}, breit {breit:.3f}")  # fmt: skip
# Nie über r: Bei großem ae umschlingt der Fräser die Delle höchstens wie eine gerade Wand mit R.
r_l = 10.0 - R - 0.3
gross = nb._bogenschritt(r_l, R, R)
pruefe(abs(gross * gross + 2 * r_l * gross - 2 * r_l * R) < 1e-9, f"Schritt bei ae = R: {gross}")

# --- (f) Breiter als zwei Fräser: früher zu breit, jetzt in Bögen ---------------------------------
weit = platte.cut(Part.makeBox(60, 30, 8, V(0, 5, 12))).removeSplitter()
waende, grund = waende_und_grund(weit)
nut_w = nb.nuten(weit, grund)
pruefe(len(nut_w) == 1 and abs(nut_w[0].radius - 15.0) < 1e-6, f"30 breit: {nut_w}")
if nut_w:
    pruefe(nb.verfahren(nut_w[0], R, 0.3) == "boegen", "30 breit: nicht in Bögen")
    pruefe_bahn("30 breit", weit, nut_w[0], halb=15.0)

# --- (d) Der Wettbewerb wie im Assistenten --------------------------------------------------------
waende, grund = waende_und_grund(ii)
ebenen = hf.ebenen_oben(ii, grund)
raeumen = rb.planen(
    hf.netze_je_hoehe(ii, ebenen, hf.TOLERANZ),
    rb.Raeumwerte(form=form, zustellung=AP, zeilenabstand=AE, aufmass=0.3, oben=20.0,
                  sicher=25.0, rohteil=(0, 60, 0, 40), schneidenlaenge=26.0,
                  eintauchwinkel=3.0, vorschub=VF, eintauchen=VF * 0.3),
    ebenen,
    kb.konturen(ii, [f"Face{i + 1}" for i in range(len(ii.Faces))]),
)  # fmt: skip
netz, fern = hf.netze_ohne(ii, [kb.ohne_flaechen(ii, kb.waende(ii, waende)), waende])
kontur = kb.planen(
    netz,
    kb.Konturwerte(form, AP, AE, 0.3, True, 20.0, 25.0, (0, 60, 0, 40), schneidenlaenge=26.0,
                   eintauchwinkel=3.0),
    kb.konturen(ii, waende),
    netz_fern=fern,
)  # fmt: skip
zeit_kontur = ps.messen([ps.Bahnlauf(kontur.punkte, VF, VF * 0.3)], ii, (0, 60, 0, 40), 20.0,
                        form, AE, AP).zeit  # fmt: skip
k_raeumen = ps.messen([ps.Bahnlauf(raeumen.punkte, VF, VF * 0.3)], ii, (0, 60, 0, 40), 20.0,
                      form, AE, 8.0, ebenen_z=[12.0], aufmass=0.3)  # fmt: skip
print(ascii(f"Wettbewerb: Nut {bahn_ii.zeit:.2f}, Räumen {raeumen.zeit:.2f} (Wirkungsgrad "
            f"{k_raeumen.wirkungsgrad * 100:.0f} %), Kontur {zeit_kontur:.2f} min"))  # fmt: skip
pruefe(bahn_ii.zeit < zeit_kontur, f"Nut {bahn_ii.zeit:.2f} nicht schneller als die Kontur")
# Das Räumen ohne Vorgabe: adaptiv – es hält die Last auch in der Nut (keine volle Breite mehr),
# ist aber langsamer als die Bögen der Nut. Mit den Ringen schnitte es in voller Breite (mehr
# Abtrag, als ae · ap erlaubt: ein Wirkungsgrad über 100 %) – nur scheinbar schnell.
pruefe(
    raeumen.variante == "adaptiv" and k_raeumen.wirkungsgrad < 1.0 and bahn_ii.zeit < raeumen.zeit,
    f"Räumen in der Nut: {raeumen.variante}, {raeumen.zeit:.2f} min, Wirkungsgrad "
    f"{k_raeumen.wirkungsgrad * 100:.0f} %",
)
ringe = rb.planen(
    hf.netze_je_hoehe(ii, ebenen, hf.TOLERANZ),
    rb.Raeumwerte(form=form, zustellung=AP, zeilenabstand=AE, aufmass=0.3, oben=20.0,
                  sicher=25.0, rohteil=(0, 60, 0, 40), variante=rb.RINGE, schneidenlaenge=26.0,
                  eintauchwinkel=3.0, vorschub=VF, eintauchen=VF * 0.3),
    ebenen,
    kb.konturen(ii, [f"Face{i + 1}" for i in range(len(ii.Faces))]),
)  # fmt: skip
k_ringe = ps.messen([ps.Bahnlauf(ringe.punkte, VF, VF * 0.3)], ii, (0, 60, 0, 40), 20.0,
                    form, AE, 8.0, ebenen_z=[12.0], aufmass=0.3)  # fmt: skip
pruefe(k_ringe.wirkungsgrad > 1.0, "Ringe in der Nut nicht in voller Breite?")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
