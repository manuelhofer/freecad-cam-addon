# Prüft Rohteil und Fertigteil in der Simulation (W-003 Stufe V3g, mit der Form des
# Fräsers V5e): Ein Schnitt nimmt unter dem Fräser bis zu seiner Spitze weg, daneben
# nichts; Kugel-, Torus- und Konikfräser genau dort, wo der Strahl seine Stirn trifft (fein
# abgetastet). Eine Spirale auf Radius 38 lässt die Stange überall dort auf 38, wo sie lief.
# Dann „Rundum schruppen“ auf der Beispiel-Drehmaschine (Welle Ø 40 in Ø 50, die Stange
# ragt weit genug heraus): Nach dem Abfahren bleibt rundum etwa das Aufmaß, nirgends fehlt
# etwas im Teil; zurück zu einer früheren Station rechnet von vorn. Mit „Rundum schlichten“
# (Kugelfräser Ø 6) dahinter trägt es mit der Kugel ab und vergleicht mit dessen Aufmaß 0:
# grün, nichts im Teil. Nur über einer Abflachung geschruppt (V4): Ohne Wahl wäre der Mantel
# rot (dort steht die Stange), mit den gewählten Flächen hat er keine Farbe – nur die
# Abflachung zählt; Blau gälte überall. Wo das Teil nicht rund um die Achse liegt (ein Quader
# neben ihr), vergleicht es nicht und sagt, von wo bis wo; ein Rohr schon. An einer scharfen
# Kante und am Ende ist 0,1 mm darunter nicht blau, auf glatter Fläche schon.
import math
import os
import pathlib
import sys
import tempfile
import time

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import abfahren as ab
from camaddon import beispielmaschine as bm
from camaddon import fraeserform as ff
from camaddon import job_schnittwerte as js
from camaddon import reichweite as rw
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_achsen as va
from camaddon import vierachs_bahn as vb
from camaddon import vierachs_flaechen as vf
from camaddon import vierachs_huelle as vh
from camaddon import vierachs_operation as vo
from camaddon import vierachs_rohteil as vr
from camaddon import vierachs_schlichten as vs
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")

# --- Ein Schnitt ------------------------------------------------------------------------
st = rm.Stange(40.0, -50.0, 1.0)
st.schnitt(-20.0, 35.0, 90.0, 6.0)
unter = st.r[np.argmin(np.abs(st.a + 20)), 90]
pruefe(abs(unter - 35.0) < 1e-9, f"unter dem Fräser: {unter}")
daneben = st.r[np.argmin(np.abs(st.a + 20)), 100]  # 10° weiter: 35 · tan 10° > 6
pruefe(daneben == 40.0, f"10° daneben: {daneben}")
laengs = st.r[np.argmin(np.abs(st.a + 27)), 90]  # 7 mm längs daneben: außerhalb des Fräsers
pruefe(laengs == 40.0, f"7 mm längs daneben: {laengs}")
schraeg = st.r[np.argmin(np.abs(st.a + 20)), 95]  # 5°: der Strahl trifft die Stirn weiter außen
pruefe(abs(schraeg - 35.0 / math.cos(math.radians(5))) < 1e-9, f"5° daneben: {schraeg}")
pruefe(st.r[:, 270].min() == 40.0, "gegenüber weggenommen")


def eintritt(form, r_t, d, delta, bis=40.0, schritt=2e-4):
    """Wo der Strahl (d längs, Δ zur Werkzeugachse) den Fräser mit der Spitze auf r_t zuerst
    trifft – fein abgetastet: der erste Punkt, der über der Stirn liegt; `bis`, wenn keiner."""
    rho = np.arange(r_t - 1.0, bis, schritt)
    hoehe = rho * math.cos(delta) - r_t
    quer = np.sqrt(d * d + (rho * math.sin(delta)) ** 2)
    drin = np.flatnonzero(
        (quer <= form.radius) & (hoehe >= form.hoehe(np.minimum(quer, form.radius)))
    )
    return float(rho[drin[0]]) if drin.size else bis


# --- Ein Schnitt mit Kugel-, Torus- und Konikfräser: wo der Strahl die Stirn trifft ---------
for name, form in (
    ("Kugel", ff.kugel(6.0)),
    ("Torus", ff.torus(6.0, 2.0)),
    ("Konik", ff.konik(3.0, 10.0, 12.0, 5.0)),
):
    st = rm.Stange(40.0, -50.0, 1.0)
    st.schnitt(-20.0, 35.0, 90.0, form)
    abweichung = 0.0
    for i in np.flatnonzero(np.abs(st.a + 20) <= form.radius):
        for j in range(75, 106):
            soll = eintritt(form, 35.0, st.a[i] + 20.0, math.radians(j - 90.0))
            abweichung = max(abweichung, abs(st.r[i, j] - soll))
    pruefe(abweichung < 0.002, f"{name}: {abweichung:.4f} mm neben der Stirn")
    pruefe(abs(st.r[np.argmin(np.abs(st.a + 20)), 90] - 35.0) < 1e-9, f"{name}: unter der Spitze")
    pruefe(st.r[np.abs(st.a + 20) > form.radius + 0.5].min() == 40.0, f"{name}: längs daneben")
# Die Kugel quer versetzt und um 60° gedreht (die Querachse, angestellt): Ihre Mitte liegt bei 8
# unter φ 0, die Spitze 1 mm unter der Drehmitte – sie nimmt dasselbe weg wie auf dem Strahl
# (a 0,25: zwischen den Zeilen des Rasters, nicht genau am Rand der Kugel).
gerade, gedreht = rm.Stange(20.0, -10.0, 10.0), rm.Stange(20.0, -10.0, 10.0)
gerade.schnitte([0.25], [3.0], [0.0], ff.kugel(5.0))
gedreht.schnitte([0.25], [-1.0], [60.0], ff.kugel(5.0), [-8.0 * math.sin(math.radians(60.0))])
pruefe(
    np.allclose(gerade.r, gedreht.r) and gerade.r.min() < 3.01,
    f"Kugel gedreht: {np.abs(gerade.r - gedreht.r).max():.3f} mm anders",
)

# --- Eine Spirale auf Radius 38 -----------------------------------------------------------
st = rm.Stange(40.0, -120.0, 1.0)
punkte = []
a, phi = 10.0, 0.0
while a > -110:
    punkte.append((a, 38.0, phi))
    a -= 4.8 / 4
    phi += 90.0
beginn = time.time()
for von, nach in zip(punkte, punkte[1:], strict=False):
    st.fahre(von, nach, 6.0)
dauer = time.time() - beginn
mitte = st.r[(st.a > -100) & (st.a < 0)]
pruefe(
    mitte.min() >= 38.0 - 1e-9 and mitte.max() < 38.001, f"Spirale: {mitte.min()} … {mitte.max()}"
)
pruefe(st.r[st.a < -117].min() == 40.0, "hinter dem Fräser weggenommen")
pruefe(dauer < 5.0, f"Spirale dauert {dauer:.1f} s")
# Dieselbe Spirale mit dem Kugelfräser Ø 12: Zwischen zwei Umdrehungen (4,8 mm) bleibt der
# Kamm, 6 − √(36 − 2,4²) = 0,501 mm, über der Spitze.
st = rm.Stange(40.0, -120.0, 1.0)
st.fahre_stuecke(punkte[:-1], punkte[1:], ff.kugel(6.0))
mitte = st.r[(st.a > -100) & (st.a < 0)]
kamm = 6 - math.sqrt(36 - 2.4**2)
pruefe(
    mitte.min() >= 38.0 - 1e-9 and abs(mitte.max() - 38.0 - kamm) < 0.03,
    f"Kugel-Spirale: {mitte.min()} … {mitte.max()} (Kamm {kamm:.3f})",
)

# --- Rundum schruppen auf der Beispiel-Drehmaschine ---------------------------------------
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
kugel = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)
kugel.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.5, ap=6, vc=150, fz=0.04)]
ue.uebergeben(wz.Bibliothek([kugel]))
asm, ma = bm.drehmaschine()
achse = va.von_maschine(asm, ma)[0]
doc = FreeCAD.newDocument("Restmaterial")
welle = doc.addObject("Part::Feature", "Welle")
welle.Shape = Part.makeCylinder(20, 30, V(), V(1, 0, 0))
doc.recompute()
stirn = next(
    f
    for f in welle.Shape.Faces
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
)
lage = vr.berechne(welle.Shape, stirn, achse, durchmesser=50)
stange = vr.Stange(50.0, frei_hinten=6.5 + 6 + 5)
job = vr.richte_ein(doc, welle, lage, stange, achse, beschriftung="Welle 4 Achsen")
tc = job.Tools.Group[0]
tc.Tool.Diameter = 12
tc.Tool.Length = 125
tc.HorizFeed = "1500 mm/min"
op = vo.lege_an(job, tc, achse, zustellung=2.5, steigung=6.0, aufmass=0.3)
doc.recompute()
p = rw.Pruefung(asm, ma)
nullpunkt = rw.vorschlag_nullpunkt(job)
fahrt = ab.abfahrt(p, job, nullpunkt)
abtrag = rm.fuer(fahrt, job, fahrt.am_werkstueck())
pruefe(abtrag is not None, "kein Abtrag für den Rundum-Job")
if abtrag is not None:
    beginn = time.time()
    abtrag.bis_station(len(fahrt.stationen) - 1)
    dauer_ab = time.time() - beginn
    beginn = time.time()
    vergleich = abtrag.vergleich()
    dauer_vergleich = time.time() - beginn
    teil = vergleich.farbe != rm.OHNE_TEIL
    gruen = np.count_nonzero(vergleich.farbe == rm.GRUEN) / max(1, np.count_nonzero(teil))
    pruefe(
        vergleich.kleinster > 0.25 and not (vergleich.farbe == rm.BLAU).any(),
        f"ins Teil: kleinster Rest {vergleich.kleinster}",
    )
    pruefe(gruen > 0.9, f"grün nur {gruen:.0%}, größter Rest {vergleich.groesster}")
    print(
        ascii(
            f"Abtrag {dauer_ab:.1f} s, Vergleich {dauer_vergleich:.1f} s; Rest "
            f"{vergleich.kleinster:.3f} … {vergleich.groesster:.3f} mm, grün {gruen:.0%}"
        )
    )
    # Zurück: von vorn gerechnet – vor dem ersten Schnitt ist die Stange ganz.
    abtrag.bis_station(1)
    pruefe(abtrag.stange.r.min() == 25.0, f"zurück am Anfang: {abtrag.stange.r.min()}")
    # Fürs Bild: je 2 × 2 Zellen ein Punkt, rundum geschlossen.
    a, phi, r = rm.darstellung(abtrag.stange)
    pruefe(r.shape == (len(a), len(phi)) and abs(phi[-1] - phi[0] - 2 * math.pi) < 1e-12, "Bild")

# --- Dahinter „Rundum schlichten“ mit dem Kugelfräser Ø 6 ------------------------------------
tc2 = js.controller_ohne_transaktion(doc, job, kugel, kugel.einsaetze(wz.ALLE)[0])
tc2.Tool.Length = 125
tc2.HorizFeed = "1500 mm/min"
schlichten = vs.lege_an(job, tc2, achse, schrittweite=0.5)
doc.recompute()
fahrt = ab.abfahrt(p, job, nullpunkt)
abtrag = rm.fuer(fahrt, job, fahrt.am_werkstueck())
pruefe(abtrag is not None, "kein Abtrag mit dem Schlichten")
if abtrag is not None:
    formen = list(abtrag.fraeser.values())
    pruefe(formen[0] == ff.scheibe(6.0) and formen[1] == ff.kugel(3.0), f"Fräser: {formen}")
    pruefe(abtrag.aufmass == 0.0, f"verglichen mit dem Aufmaß {abtrag.aufmass}")
    beginn = time.time()
    abtrag.bis_station(len(fahrt.stationen) - 1)
    dauer_ab = time.time() - beginn
    vergleich = abtrag.vergleich()
    teil = vergleich.farbe != rm.OHNE_TEIL
    gruen = np.count_nonzero(vergleich.farbe == rm.GRUEN) / max(1, np.count_nonzero(teil))
    pruefe(
        vergleich.kleinster > -rm.BLAU_AB and not (vergleich.farbe == rm.BLAU).any(),
        f"geschlichtet ins Teil: kleinster Rest {vergleich.kleinster}",
    )
    pruefe(
        gruen > 0.95 and vergleich.groesster < 0.1,
        f"geschlichtet grün nur {gruen:.0%}, größter Rest {vergleich.groesster}",
    )
    pruefe(dauer_ab < 10.0, f"Abtrag mit dem Schlichten dauert {dauer_ab:.1f} s")
    print(
        ascii(
            f"Mit Schlichten: Abtrag {dauer_ab:.1f} s; Rest "
            f"{vergleich.kleinster:.3f} … {vergleich.groesster:.3f} mm, grün {gruen:.0%}"
        )
    )
del schlichten
FreeCAD.closeDocument(doc.Name)
FreeCAD.closeDocument(asm.Document.Name)

# --- Nur über der Abflachung (V4): verglichen auf den gewählten Flächen ----------------------
# Welle Ø 20 von −40 bis 0, Abflachung auf x = 8 von −30 bis −10, Stange Ø 24, R 3.
flach_welle = (
    Part.makeCylinder(10, 40, V(0, 0, -40))
    .cut(Part.makeBox(10, 30, 20, V(8, -15, -30)))
    .removeSplitter()
)
abflachung = next(
    i
    for i, f in enumerate(flach_welle.Faces)
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-6
)
laengs, radial = (0, 0, 1), (1, 0, 0)
flach_bahn = vb.schruppen(
    vh.vernetze(flach_welle),
    laengs,
    radial,
    vb.Schruppwerte(
        3.0,
        12.0,
        2.0,
        2.4,
        0.3,
        1.0,
        -60.0,
        waende=((-30.0, 1), (-10.0, -1)),
        bereich=vf.bereich_fuer(flach_welle, laengs, radial, [f"Face{abflachung + 1}"], 3.0),
    ),
)
stange = rm.Stange(12.0, -45.0, 1.0)
von, nach = [], []
for vorher, punkt in zip(flach_bahn.punkte, flach_bahn.punkte[1:], strict=False):
    if not punkt.eilgang:
        von.append((vorher.a, vorher.r, vorher.phi))
        nach.append((punkt.a, punkt.r, punkt.phi))
stange.fahre_stuecke(von, nach, 3.0)
netz = vh.vernetze(flach_welle)
teil = rm.teilradien(netz, laengs, radial, stange)
genau = rm.teilradien(netz, laengs, radial, stange, rm.GENAU)
sicht = vf.sicht(vf.vernetze(flach_welle), laengs, radial, stange.a, stange.phi)
nur = sicht.flaeche == abflachung
ohne = rm.vergleiche(stange, teil, 0.3, genau)
mit = rm.vergleiche(stange, teil, 0.3, genau, nur)
pruefe(
    not ohne.nur_gewaehlte and ohne.groesster > 1.9 and (ohne.farbe == rm.ROT).any(),
    f"ohne Wahl: größter Rest {ohne.groesster:.2f}",
)
pruefe(mit.nur_gewaehlte, "mit Wahl: nicht als „nur gewählte“ vermerkt")
pruefe(not (mit.farbe[~nur] == rm.ROT).any(), "mit Wahl: Mantel rot")
pruefe((mit.farbe[~nur & np.isfinite(teil)] == rm.OHNE_TEIL).all(), "mit Wahl: Mantel gefärbt")
pruefe(mit.groesster < 1.3, f"mit Wahl: größter Rest {mit.groesster:.2f}")
pruefe(
    mit.kleinster > -rm.BLAU_AB and not (mit.farbe == rm.BLAU).any(),
    f"ins Teil: {mit.kleinster:.3f}",
)
anteil = np.count_nonzero(mit.farbe[nur] != rm.ROT) / max(1, np.count_nonzero(nur))
pruefe(anteil > 0.95, f"auf der Abflachung nur {anteil:.0%} nicht rot")
print(
    ascii(f"Abflachung: ohne Wahl bis {ohne.groesster:.2f} mm, mit Wahl bis {mit.groesster:.2f} mm")
)

# --- Das Teil nicht rund um die Achse (Manuels Testteil, P-2026-09-30-44) --------------------
# Längs z: ein Rohr (Ø 30 / Ø 20, z −100 … −70), nichts, ein Quader 0,2 mm neben der Achse
# (y 0,2 … 25,2 wie das D-Profil hinten an Manuels Teil, z −60 … −40), ein Quader um die
# Achse (z −40 … −10). Das Rohr hat jeder Strahl aus der Achse vor sich, den Quader daneben
# nur manche – die anderen sehen ihn hinter der Achse (negativer Radius) oder gar nicht: Dort
# kennt die Stange je Strahl nur einen Radius, und ein Fräser nah an der Achse sähe aus wie
# ein Schnitt ins Teil. Dort vergleicht es nicht und sagt, von wo bis wo; am Rohr schon – ein
# Schnitt ins Rohr ist blau.
rohr = Part.makeCylinder(15, 30, V(0, 0, -100)).cut(Part.makeCylinder(10, 30, V(0, 0, -100)))
daneben = Part.makeBox(70, 25, 20, V(-35, 0.2, -60))
um_die_achse = Part.makeBox(20, 20, 30, V(-10, -10, -40))
st = rm.Stange(30.0, -100.0, -10.0)
teile = Part.makeCompound([rohr, daneben.fuse(um_die_achse)])
teil = rm.teilradien(vh.vernetze(teile), (0, 0, 1), (1, 0, 0), st)
genau = rm.teilradien(vh.vernetze(teile), (0, 0, 1), (1, 0, 0), st, rm.GENAU)
st.r[:] = np.where(np.isfinite(teil), teil + 0.3, 2.0)
im_rohr = (st.a > -95.0) & (st.a < -75.0)
neben = (st.a > -59.0) & (st.a < -41.0)
pruefe(
    ((teil[neben] > 0).any(axis=1) & (teil[neben] < 0).any(axis=1)).all(),
    "neben der Achse: manche Strahlen sehen den Quader vor, andere hinter der Achse",
)
st.r[neben] = 2.0  # der Fräser nah an der Achse: hier sähe es aus wie 20 mm im Teil
v = rm.vergleiche(st, teil, 0.3, genau)
pruefe(
    len(v.ohne_vergleich) == 1
    and abs(v.ohne_vergleich[0][0] + 60.0) < 0.3
    and abs(v.ohne_vergleich[0][1] + 40.0) < 0.3,
    f"nicht verglichen: {v.ohne_vergleich}",
)
pruefe((v.farbe[neben] == rm.OHNE_TEIL).all(), "neben der Achse gefärbt")
pruefe(not (v.farbe == rm.BLAU).any() and v.kleinster > 0.2, f"blau: {v.kleinster}")
pruefe((v.farbe[im_rohr] == rm.GRUEN).all(), "Rohr nicht grün")
st.r[im_rohr, 90] = 12.0  # 3 mm ins Rohr
v = rm.vergleiche(st, teil, 0.3, genau)
pruefe(
    (v.farbe[im_rohr, 90] == rm.BLAU).all() and abs(v.kleinster + 3.0) < 0.01,  # Netz
    f"ins Rohr: {v.kleinster}",
)
# Drei Stücke: jedes für sich, bis an den Rand der Zellen, höchstens bis ans Ende der Stange.
st = rm.Stange(30.0, -20.0, 0.0)
teil = np.full(st.r.shape, 20.0)
teil[:3, 180:] = -np.inf
teil[20:22, :90] = -np.inf
teil[30, 200:] = -5.0  # jeder Strahl sieht Teil, manche nur hinter der Achse (Manuels Teil)
v = rm.vergleiche(st, teil, 0.0)
pruefe(
    v.ohne_vergleich == ((-20.0, -18.75), (-10.25, -9.25), (-5.25, -4.75)),
    f"Stücke: {v.ohne_vergleich}",
)
pruefe(rm.vergleiche(st, np.full(st.r.shape, 20.0), 0.0).ohne_vergleich == (), "überall")
# An einer scharfen Kante (das Teil springt rundum von 30 auf 35) und am Ende des Teils sagt
# das Raster nicht genau, wo es liegt: 0,1 mm darunter ist dort nicht blau – auf glatter
# Fläche schon.
st = rm.Stange(40.0, -20.0, 0.0)
teil = np.full(st.r.shape, 30.0)
teil[:, :10] = 35.0  # die Kante zwischen φ 9° und 10°
teil[-1] = -np.inf  # a = 0: kein Teil mehr, die Zeile davor ist das Ende
st.r[:] = teil + 0.3
mitte = len(st.a) // 2
st.r[mitte, 9] = 34.9  # an der Kante
st.r[-2, 50] = 29.9  # am Ende
glatt = rm.vergleiche(st, teil, 0.3)
pruefe(not (glatt.farbe == rm.BLAU).any() and glatt.kleinster >= -rm.BLAU_AB, "Kante: blau")
st.r[mitte, 50] = 29.9  # auf glatter Fläche
ins_teil = rm.vergleiche(st, teil, 0.3)
pruefe(
    ins_teil.farbe[mitte, 50] == rm.BLAU and abs(ins_teil.kleinster + 0.1) < 1e-9,
    f"glatt: {ins_teil.farbe[mitte, 50]} {ins_teil.kleinster}",
)

if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
