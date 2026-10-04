# Prüft die Bahn „Rundum schlichten“ (W-003 Stufe V5b): Welle mit Absatz, Kugelfräser –
# die Spitze liegt überall auf der Hüllfläche (gegen den dicht abgetasteten Umriss), auch
# zwischen den Punkten, die nach dem Zusammenfassen bleiben, höchstens um Vernetzung und
# Bahntoleranz darüber; vorne und hinten auf der Tiefe am Ende des Teils, die Spirale endet
# um den Überlauf hinter dem Teil. Torus mit Aufmaß. Dann der Schutz: In einer Nut, die
# schmaler ist als der Schruppfräser, blieb nach dem Schruppen alles stehen – der Kugelfräser
# fährt dort zuerst eine Stufe, höchstens seinen Radius tief, dann bis auf den Grund. Nur
# über der Abflachung einer Welle (V4): Zeilen hin und her, im Eilgang bis knapp über den Rest,
# senkrecht hinein. Linien längs (V4c): auf der Abflachung Linien bei festem Winkel,
# gegenläufig, nur über ihr, die Kugel nie im Teil; rundum auf der Welle mit Absatz jede
# Linie auf der Hüllfläche. An einer Abflachung nah an der Achse auch zwischen den Punkten
# nirgends ins Teil – Spirale und Zeilen.
# Dazu die Zeitgrenze.
import math
import os
import sys
import time
from dataclasses import replace

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import fraeserform as ff
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import vierachs_bahn as vb
from camaddon import vierachs_flaechen as vf
from camaddon import vierachs_huelle as vh
from camaddon import vierachs_rohteil as vr

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
LAENGS, RADIAL = (0, 0, 1), (1, 0, 0)
LUFT = vb.TOLERANZ_SCHLICHTEN + vb.BAHN_TOLERANZ + 2e-3  # so weit über der Hüllfläche


def abgetastet(umriss, schritt=0.002):
    """Punkte (a, x) dicht auf einem Linienzug [(a, x), …]."""
    teile = []
    for (a1, x1), (a2, x2) in zip(umriss, umriss[1:], strict=False):
        anzahl = max(2, int(math.hypot(a2 - a1, x2 - x1) / schritt) + 1)
        t = np.linspace(0.0, 1.0, anzahl)
        teile.append(np.column_stack([a1 + t * (a2 - a1), x1 + t * (x2 - x1)]))
    return np.concatenate(teile)


def im_schnitt(punkte, form, stellen):
    """Die Hüllfläche eines Drehteils im Schnitt durch die Werkzeugachse: an jeder Stelle die
    höchste Stelle x − z(Abstand) des Umrisses."""
    ergebnis = np.full(len(stellen), -math.inf)
    for i, stelle in enumerate(stellen):
        abstand = np.abs(punkte[:, 0] - stelle)
        unter = abstand <= form.radius
        if unter.any():
            ergebnis[i] = np.max(punkte[unter, 1] - form.hoehe(abstand[unter]))
    return ergebnis


def erlaubt(umriss, form, a, soll):
    """So weit darf die Bahn über der Hüllfläche liegen: Vernetzung und Bahntoleranz, der
    Sehnenfehler – und wo die Hüllfläche steil ist, verschiebt das Rechnen mit dem um die
    Vernetzung größeren Fräser sie längs: Toleranz × Steigung. Wo sie an einer Wand springt
    (mehr als 0,05 mm auf 0,01 mm längs), zählt es nicht."""
    davor = im_schnitt(umriss, form, np.clip(a + 0.01, -42.0, 0.0))
    danach = im_schnitt(umriss, form, np.clip(a - 0.01, -42.0, 0.0))
    steigung = np.maximum(np.abs(davor - soll), np.abs(danach - soll)) / 0.01
    grenze = LUFT + vb.SEHNE_HOECHSTENS + vb.TOLERANZ_SCHLICHTEN * steigung
    return np.where(steigung * 0.01 < 0.05, grenze, math.inf)


def stuecke(bahn):
    """Die Stücke der Bahn im Vorschub, zwischen zwei Eilgängen: [[Punkt, …], …]."""
    ergebnis, stueck = [], []
    for punkt in bahn.punkte:
        if punkt.eilgang:
            if stueck:
                ergebnis.append(stueck)
            stueck = []
        else:
            stueck.append(punkt)
    return ergebnis + ([stueck] if stueck else [])


def dicht(bahn, nur=None):
    """Die Vorschubpunkte der Bahn wieder alle 0,5°: (a, r) – so fährt die Steuerung; `nur`:
    nur diese Stücke (stuecke())."""
    a, r = [], []
    for stueck in nur if nur is not None else stuecke(bahn):
        for von, nach in zip(stueck, stueck[1:], strict=False):
            anzahl = max(1, int(round((nach.phi - von.phi) / vb.SCHRITT_PHI_SCHLICHTEN)))
            t = np.arange(anzahl) / anzahl
            a.append(von.a + t * (nach.a - von.a))
            r.append(von.r + t * (nach.r - von.r))
    return np.concatenate(a), np.concatenate(r)


# --- Welle mit Absatz, Kugelfräser R 3 ----------------------------------------------------
# Ø 40 von −30 bis 0, Ø 30 von −42 bis −30; Stange Ø 50 bis 1 vor dem Teil, Futter bei −60.
welle = Part.makeCylinder(20, 30, V(0, 0, -30)).fuse(Part.makeCylinder(15, 12, V(0, 0, -42)))
netz = vh.vernetze(welle.removeSplitter(), vb.TOLERANZ_SCHLICHTEN)
umriss = abgetastet(
    [(0.0, 0.0), (0.0, 20.0), (-30.0, 20.0), (-30.0, 15.0), (-42.0, 15.0), (-42.0, 0.0)]
)
kugel = ff.kugel(3.0)
werte = vb.Schlichtwerte(
    form=kugel,
    stange_radius=25.0,
    schrittweite=0.35,
    aufmass=0.0,
    a_stange_vorne=1.0,
    a_futter=-60.0,
)
beginn = time.time()
bahn = vb.schlichten(netz, LAENGS, RADIAL, werte)
dauer = time.time() - beginn
# Gleichlauf über die Rundachse (P-2026-10-02-23): mit M3 steigt φ, während die Spirale zum
# Futter rückt; andersherum (M4) fällt es – an der runden Welle dieselbe Bahn gespiegelt.
gegen = vb.schlichten(netz, LAENGS, RADIAL, replace(werte, gleichlauf=False))
im_vorschub = [p for p in bahn.punkte if not p.eilgang]
gegen_vorschub = [p for p in gegen.punkte if not p.eilgang]
pruefe(
    im_vorschub[-1].phi > im_vorschub[0].phi and gegen_vorschub[-1].phi < gegen_vorschub[0].phi,
    f"Winkel: {im_vorschub[0].phi}…{im_vorschub[-1].phi}, "
    f"andersherum {gegen_vorschub[0].phi}…{gegen_vorschub[-1].phi}",
)
pruefe(
    abs(gegen.umdrehungen - bahn.umdrehungen) < 1e-9
    and abs(min(p.r for p in gegen_vorschub) - min(p.r for p in im_vorschub)) < 1e-6
    and abs(len(gegen_vorschub) - len(im_vorschub)) <= 2,
    f"andersherum: {gegen.umdrehungen} Umdrehungen, {len(gegen_vorschub)} Punkte",
)
start = bahn.punkte[0]
pruefe(start.eilgang and start.a == 1.0 + 3.0 + 2.0 and start.r == 27.0, f"Start: {start}")
a_ende = -42.0 - (3.0 + 0.5)  # Überlauf: Radius + 0,5
vorschub = [p for p in bahn.punkte if not p.eilgang]
pruefe(abs(vorschub[-1].a - a_ende) < 0.35 / 720 + 1e-9, f"Ende bei {vorschub[-1].a}")
# … plus eine Umdrehung als Ring am Ende, damit das Ende rund ist (P-2026-10-03-17): Die
# letzten 720 Punkte im Vorschub liegen alle bei a_ende, eine volle Umdrehung.
pruefe(
    abs(bahn.umdrehungen - (6.0 - a_ende) / 0.35 - 1) < 1 / 720, f"{bahn.umdrehungen} Umdrehungen"
)
ring_ende = [p for p in vorschub if abs(p.a - a_ende) < 1e-9]
pruefe(
    len(ring_ende) >= 2 and ring_ende[-1].phi - ring_ende[0].phi >= 359.5 - 1e-6,
    f"Ring am Ende: {len(ring_ende)} Punkte",
)
pruefe(abs(bahn.kammhoehe - (3 - math.sqrt(9 - 0.175**2))) < 1e-12, f"Kammhöhe {bahn.kammhoehe}")
pruefe(bahn.rest_ueber == 0.0 and bahn.hinten_frei == 0.0, "ohne Rest: Rest oder hinten frei")
pruefe(len(stuecke(bahn)) == 1, f"{len(stuecke(bahn))} Stücke ohne Rest")
a, r = dicht(bahn)
soll = im_schnitt(umriss, kugel, np.clip(a, -42.0, 0.0))  # davor und dahinter: am Ende
darueber = r - soll
pruefe(
    darueber.min() >= -1e-3,
    f"Schlichten im Teil: {darueber.min():.4f} (bei a {a[np.argmin(darueber)]:.3f})",
)
zu_hoch = darueber - erlaubt(umriss, kugel, a, soll)
pruefe(zu_hoch.max() <= 0, f"zu hoch: {zu_hoch.max():+.4f} (bei a {a[np.argmax(zu_hoch)]:.3f})")
pruefe(len(bahn.punkte) < 40000, f"{len(bahn.punkte)} Punkte – zu wenig zusammengefasst")
print(ascii(f"Welle mit Absatz: {len(bahn.punkte)} Punkte in {dauer:.1f} s"))

# Torus R 3, Eckradius 1, Aufmaß 0,2: die Hüllfläche des um 0,2 größeren Fräsers, 0,2 höher.
torus = ff.torus(3.0, 1.0)
bahn = vb.schlichten(
    netz,
    LAENGS,
    RADIAL,
    vb.Schlichtwerte(torus, 25.0, 0.8, 0.2, 1.0, -60.0),
)
a, r = dicht(bahn)
soll = im_schnitt(umriss, torus.mit_aufmass(0.2), np.clip(a, -42.0, 0.0)) + 0.2
darueber = r - soll
pruefe(darueber.min() >= -1e-3, f"Torus im Aufmaß: {darueber.min():.4f}")
zu_hoch = darueber - erlaubt(umriss, torus.mit_aufmass(0.2), a, soll - 0.2)
pruefe(
    zu_hoch.max() <= 0, f"Torus zu hoch: {zu_hoch.max():+.4f} (bei a {a[np.argmax(zu_hoch)]:.3f})"
)

# Befehle wie beim Schruppen: X ist der Radius, C dreht, Vorschub nach G93.
befehle = vb.befehle(bahn, LAENGS, RADIAL, "C", 1, 955.0)
pruefe(befehle[3].Name == "G93" and befehle[-1].Name == "G94", "G93 … G94")

try:
    vb.schlichten(netz, LAENGS, RADIAL, vb.Schlichtwerte(kugel, 25.0, 6.5, 0.0, 1.0, -60.0))
    fehler.append("Schrittweite größer als der Fräser ging durch")
except ValueError as grund:
    pruefe("Schrittweite" in str(grund), f"Grund: {grund}")

# --- Schutz: eine Nut, schmaler als der Schruppfräser ---------------------------------------
# Welle Ø 40 von −40 bis 0, dazwischen eine Nut 8 mm breit auf Ø 30 (a −24 … −16). Der
# Schruppfräser Ø 12 kommt nicht hinein: Dort steht nach dem Schruppen Ø 40 plus Aufmaß.
nut = Part.makeCylinder(20, 40, V(0, 0, -40)).cut(
    Part.makeCylinder(25, 8, V(0, 0, -24)).cut(Part.makeCylinder(15, 8, V(0, 0, -24)))
)
schruppen = vb.schruppen(
    vh.vernetze(nut),
    LAENGS,
    RADIAL,
    vb.Schruppwerte(6.0, 25.0, 2.0, 4.8, 0.3, 1.0, -70.0),
)
stange = rm.Stange(25.0, -70.0, 1.0)
for von, nach in zip(schruppen.punkte, schruppen.punkte[1:], strict=False):
    if not nach.eilgang and not von.eilgang:
        stange.fahre((von.a, von.r, von.phi), (nach.a, nach.r, nach.phi), 6.0)
    elif not nach.eilgang:  # vom Eilgang in den Vorschub: der erste Schnitt
        stange.schnitt(nach.a, nach.r, nach.phi, 6.0)
im_nut = stange.r[(stange.a > -22) & (stange.a < -18)]
pruefe(im_nut.min() > 20.0, f"in der Nut geschruppt: {im_nut.min():.3f}")
netz = vh.vernetze(nut, vb.TOLERANZ_SCHLICHTEN)
ohne = vb.schlichten(netz, LAENGS, RADIAL, vb.Schlichtwerte(kugel, 25.0, 0.35, 0.0, 1.0, -70.0))
mit = vb.schlichten(
    netz,
    LAENGS,
    RADIAL,
    vb.Schlichtwerte(kugel, 25.0, 0.35, 0.0, 1.0, -70.0, rest=(stange.a, stange.phi, stange.r)),
)
a_ohne, r_ohne = dicht(ohne)
tief_ohne = r_ohne[(a_ohne > -21) & (a_ohne < -19)].min()
pruefe(abs(tief_ohne - 15.0) < 0.02, f"ohne Schutz in die Nut: {tief_ohne:.3f}")
# Mit dem Rest nach dem Schruppen: dieselbe eine Spirale (Manuel, 2026-10-03: keine Stufen,
# nicht mittendrin anfangen) – in der Nut nimmt sie in einem Zug, was der Ø 12 nicht
# erreichte: rest_ueber ≈ 5 mm (Ø 40 + Aufmaß 0,3 über dem Grund Ø 30); der Wert steht an der
# Operation, die Bahn ist dieselbe.
pruefe(len(stuecke(mit)) == 1, f"{len(stuecke(mit))} Stücke statt einer Spirale")
pruefe(5.0 <= mit.rest_ueber <= 5.4, f"Rest über der Bahn: {mit.rest_ueber:.3f}")
pruefe(abs(mit.umdrehungen - ohne.umdrehungen) < 1e-9, "mit Rest andere Umdrehungen")
pruefe(ohne.rest_ueber == 0.0, f"ohne Rest: rest_ueber {ohne.rest_ueber}")
a_mit, r_mit = dicht(mit)
tief_mit = r_mit[(a_mit > -21) & (a_mit < -19)].min()
pruefe(abs(tief_mit - 15.0) < 0.02, f"geschlichtet in der Nut: {tief_mit:.3f}")
aussen = (a_mit > -14) & (a_mit < -2)
pruefe(
    float(np.max(np.abs(r_mit[aussen] - 20.0))) < 0.02,
    f"neben der Nut: {r_mit[aussen].min():.3f} … {r_mit[aussen].max():.3f}",
)
# Die Rundachse dreht nie zurück.
winkel = [p.phi for p in mit.punkte]
pruefe(all(b >= a - 1e-9 for a, b in zip(winkel, winkel[1:], strict=False)), "C dreht zurück")
# Ein Kugelfräser Ø 2: ebenso eine Spirale, der Rest derselbe.
klein = vb.schlichten(
    netz,
    LAENGS,
    RADIAL,
    vb.Schlichtwerte(
        ff.kugel(1.0), 25.0, 0.35, 0.0, 1.0, -70.0, rest=(stange.a, stange.phi, stange.r)
    ),
)
pruefe(len(stuecke(klein)) == 1, f"Ø 2: {len(stuecke(klein))} Stücke")
pruefe(5.0 <= klein.rest_ueber <= 5.4, f"Ø 2: Rest über der Bahn {klein.rest_ueber:.3f}")

# --- Die Spirale mit der Querachse (V5e, Manuels Y-Gedanke) -------------------------------
# Ein D-Profil: Welle Ø 40 mit einer Abflachung bei x = 6, Kugel Ø 10. Mit `querachse` steht
# die Werkzeugachse längs der Normalen: Auf der Abflachung hält die Rundachse (ψ = 0), die
# Spitze steht bei x = 6 (+ Netz 0,005), der Versatz quer läuft über die Fläche; die Mitte
# der Kugel bleibt überall genau R vom Teil (im Rahmen des Teils gerechnet: Rot(ψ) · (x + R,
# q)); die Rundachse dreht nie zurück; die Bahn ist nicht länger als ohne.
d_profil = (
    Part.makeCylinder(20, 60, V(0, 0, -60))
    .cut(Part.makeBox(40, 60, 80, V(6, -30, -70)))
    .removeSplitter()
)
netz_d = vh.vernetze(d_profil, vb.TOLERANZ_SCHLICHTEN)
kugel_5 = ff.kugel(5.0)
werte_d = vb.Schlichtwerte(kugel_5, 25.0, 1.0, 0.0, 1.0, -80.0)
radial_d = vb.schlichten(netz_d, LAENGS, RADIAL, werte_d)
quer_d = vb.schlichten(netz_d, LAENGS, RADIAL, replace(werte_d, querachse=True))
pruefe(quer_d.querachse and not radial_d.querachse, "querachse am Ergebnis")
pruefe(abs(quer_d.umdrehungen - radial_d.umdrehungen) < 1e-9, "quer: andere Umdrehungen")
im_vorschub = [p for p in quer_d.punkte if not p.eilgang]
psi_d = np.radians([p.phi for p in im_vorschub])
x_d = np.array([p.r for p in im_vorschub])
q_d = np.array([p.q for p in im_vorschub])
a_d = np.array([p.a for p in im_vorschub])
mitte_x = (x_d + 5.0) * np.cos(psi_d) - q_d * np.sin(psi_d)
mitte_y = (x_d + 5.0) * np.sin(psi_d) + q_d * np.cos(psi_d)
w_d = math.sqrt(400.0 - 36.0)  # halbe Breite der Abflachung
ecke = np.minimum(np.hypot(mitte_x - 6.0, mitte_y - w_d), np.hypot(mitte_x - 6.0, mitte_y + w_d))
abstand_d = np.where(
    mitte_x > 6.0,
    np.where(np.abs(mitte_y) <= w_d, mitte_x - 6.0, ecke),
    np.hypot(mitte_x, mitte_y) - 20.0,
)
im_teil = (a_d < -0.5) & (a_d > -59.5)
pruefe(
    abstand_d[im_teil].min() >= 5.0 - 1e-3 and abstand_d[im_teil].max() <= 5.0 + 0.2,
    f"quer: Kugelmitte {abstand_d[im_teil].min():.4f} … {abstand_d[im_teil].max():.4f} vom Teil",
)
auf_ebene = im_teil & (np.abs(mitte_y) < w_d - 5.5) & (mitte_x > 5.9)
psi_ebene = np.degrees(psi_d[auf_ebene]) % 360.0
psi_ebene = np.where(psi_ebene > 180.0, psi_ebene - 360.0, psi_ebene)
pruefe(
    auf_ebene.sum() > 50 and float(np.max(np.abs(psi_ebene))) < 0.02,
    f"auf der Ebene dreht C: ψ bis {float(np.max(np.abs(psi_ebene))):.4f}°",
)
pruefe(
    float(np.max(np.abs(x_d[auf_ebene] - 6.005))) < 1e-3,
    f"auf der Ebene: Spitze {x_d[auf_ebene].min():.4f} … {x_d[auf_ebene].max():.4f}",
)
# Die tiefste Spitze: ihr X – mit leicht geneigter Achse an den Rändern der Ebene Tausendstel
# weniger als 6,005 (die Kugelmitte liegt trotzdem genau).
pruefe(abs(quer_d.r_min - 6.005) < 0.01, f"quer: tiefste Spitze {quer_d.r_min:.4f}")
pruefe(q_d[auf_ebene].min() < -5.0 and q_d[auf_ebene].max() > 5.0, "quer: Y läuft nicht")
schritte_c = np.diff([p.phi for p in quer_d.punkte])
pruefe(
    float(np.min(schritte_c)) >= -1e-9, f"quer: C dreht zurück um {float(np.min(schritte_c)):.3f}°"
)
pruefe(
    len(quer_d.punkte) < 1.5 * len(radial_d.punkte),
    f"quer: {len(quer_d.punkte)} Punkte, radial {len(radial_d.punkte)}",
)
# Die Befehle tragen das Y in jedem Satz, X ist die Spitze längs der Werkzeugachse.
befehle_q = vb.befehle(quer_d, LAENGS, RADIAL, "C", 1, 1000.0)
schnitte_q = [b for b in befehle_q if b.Name == "G1"]
pruefe(all("Y" in b.Parameters for b in schnitte_q), "quer: Satz ohne Y")
dauer_q, dauer_r = vb.dauer(quer_d, 1000.0), vb.dauer(radial_d, 1000.0)
pruefe(
    0.8 * dauer_r <= dauer_q <= 1.3 * dauer_r, f"quer: {dauer_q:.1f} min, radial {dauer_r:.1f} min"
)
# Angestellt (Manuel, 2026-10-04: „als Haken, der aber pauschal angehakt ist“): Die Kugelmitte
# bleibt genau R vom Teil, die Werkzeugachse steht 15° neben der Normalen – in Vorschubrichtung
# (φ wächst, ψ steht weiter) –, C dreht nie zurück, die Zeit fast gleich.
an_d = vb.schlichten(
    netz_d, LAENGS, RADIAL, replace(werte_d, querachse=True, anstellen=vb.ANSTELLEN_QUER)
)
im_vorschub = [p for p in an_d.punkte if not p.eilgang]
psi_a = np.radians([p.phi for p in im_vorschub])
x_a = np.array([p.r for p in im_vorschub])
q_a = np.array([p.q for p in im_vorschub])
a_a = np.array([p.a for p in im_vorschub])
mx_a = (x_a + 5.0) * np.cos(psi_a) - q_a * np.sin(psi_a)
my_a = (x_a + 5.0) * np.sin(psi_a) + q_a * np.cos(psi_a)
auf_flaeche = np.abs(my_a) <= w_d
ecke_y = np.where(my_a > 0, w_d, -w_d)
abstand_a = np.where(
    mx_a > 6.0,
    np.where(auf_flaeche, mx_a - 6.0, np.hypot(mx_a - 6.0, my_a - ecke_y)),
    np.hypot(mx_a, my_a) - 20.0,
)
normale_a = np.where(
    mx_a > 6.0,
    np.where(auf_flaeche, 0.0, np.arctan2(my_a - ecke_y, mx_a - 6.0)),
    np.arctan2(my_a, mx_a),
)
neben = np.degrees(np.angle(np.exp(1j * (psi_a - normale_a))))
im_teil_a = (a_a < -0.5) & (a_a > -59.5)
pruefe(
    abstand_a[im_teil_a].min() >= 5.0 - 1e-3 and abstand_a[im_teil_a].max() <= 5.0 + 0.2,
    f"angestellt: Kugelmitte {abstand_a[im_teil_a].min():.4f} … {abstand_a[im_teil_a].max():.4f}",
)
vorwaerts = np.sign(an_d.punkte[-2].phi - an_d.punkte[1].phi)
# Wo die Normale eindeutig ist – auf dem Rund und mitten auf der Ebene; an den Kanten rollt die
# Kugel, dort ist die Normale geglättet (QUER_GLATT), mit und ohne Anstellen gleich.
eindeutig = im_teil_a & ((mx_a < 5.9) | ((np.abs(my_a) < w_d - 5.5) & (mx_a > 5.9)))
pruefe(
    eindeutig.sum() > 100
    and float(np.max(np.abs(neben[eindeutig] * vorwaerts - vb.ANSTELLEN_QUER))) < 0.15,
    f"angestellt: {eindeutig.sum()} Punkte, neben der Normalen "
    f"{np.percentile(neben[eindeutig] * vorwaerts, [0, 50, 100])}°",
)
schritte_a = np.diff([p.phi for p in an_d.punkte]) * vorwaerts
pruefe(float(np.min(schritte_a)) >= -1e-9, f"angestellt: C zurück {np.min(schritte_a):.3f}°")
dauer_a = vb.dauer(an_d, 1000.0)
pruefe(abs(dauer_a / dauer_q - 1.0) < 0.03, f"angestellt: {dauer_a:.2f} min, quer {dauer_q:.2f}")
# Schaft- und Torusfräser mit der Querachse (P-2026-10-03-22, vierachs_quer): der Plan von der
# Kugel mit ihrem Radius, die Höhe aus ihrer eigenen Hüllfläche. Auf der Abflachung steht C,
# die Stirn liegt flach auf (Spitze bei 6,005), Y fährt; nirgends ins D-Profil (je Stellung:
# kein Punkt des Umrisses unter der Stirn höher als die Stirn dort – bis auf die Vernetzung);
# C dreht nie zurück.
t_um = np.linspace(0.0, 2.0 * math.pi, 20000, endpoint=False)
kreis_d = np.column_stack([20.0 * np.cos(t_um), 20.0 * np.sin(t_um)])
umriss_d = np.vstack(
    [
        kreis_d[kreis_d[:, 0] <= 6.0],
        np.column_stack([np.full(2000, 6.0), np.linspace(-w_d, w_d, 2000)]),
    ]
)
for fr_q, s_q in ((ff.scheibe(6.0), 2.0), (ff.torus(5.0, 1.0), 1.0)):
    flach_q = vb.schlichten(
        netz_d, LAENGS, RADIAL, replace(werte_d, form=fr_q, schrittweite=s_q, querachse=True)
    )
    pts_q = [p for p in flach_q.punkte if not p.eilgang and -59.0 < p.a < -1.0]
    tiefst = -math.inf
    for p in pts_q[::5]:
        c, s = math.cos(math.radians(p.phi)), math.sin(math.radians(p.phi))
        hoch = umriss_d[:, 0] * c + umriss_d[:, 1] * s
        neben = np.abs(umriss_d[:, 1] * c - umriss_d[:, 0] * s - p.q)
        unter = neben <= fr_q.radius
        if unter.any():
            tiefst = max(tiefst, float(np.max(hoch[unter] - (p.r + fr_q.hoehe(neben[unter])))))
    winkel_q = np.array([p.phi for p in pts_q]) % 360.0
    eben_q = [p for p, w_ in zip(pts_q, winkel_q, strict=True) if min(w_, 360.0 - w_) < 1e-6]
    pruefe(
        flach_q.querachse and tiefst <= 0.0 and len(eben_q) > 50
        and all(abs(p.r - 6.005) < 1e-3 for p in eben_q)
        and max(p.q for p in eben_q) > 10.0 and min(p.q for p in eben_q) < -10.0,
        f"R {fr_q.radius}: ins Teil {tiefst:+.4f}, {len(eben_q)} Punkte auf der Ebene",
    )  # fmt: skip
    schritte_q = np.diff([p.phi for p in flach_q.punkte])
    pruefe(float(np.min(schritte_q)) >= -1e-9, f"R {fr_q.radius}: C dreht zurück")
print(
    ascii(
        f"D-Profil mit Querachse: {len(quer_d.punkte)} Punkte, {dauer_q:.1f} min (radial {dauer_r:.1f})"
    )
)

# --- Zwischen den Punkten (P-2026-10-03-22 und -24) ------------------------------------------
# Die Abflachung nah an der Achse (x = 2): An ihren Rändern steigt die Hüllfläche von der Achse
# aus gesehen steil und biegt – die Gerade zwischen zwei Punkten 0,5° auseinander lag unter
# ihr, der Schaftfräser Ø 12 schnitt 0,04 mm ins Teil, in der Spirale wie in den Zeilen über
# gewählten Flächen. Dicht zwischen den Punkten abgetastet (alle 0,05°): nirgends ins Teil.
d_nah = (
    Part.makeCylinder(20, 60, V(0, 0, -60))
    .cut(Part.makeBox(40, 60, 80, V(2, -30, -70)))
    .removeSplitter()
)
w_nah = math.sqrt(400.0 - 4.0)
umriss_nah = np.vstack(
    [
        kreis_d[kreis_d[:, 0] <= 2.0][::3],
        np.column_stack([np.full(1000, 2.0), np.linspace(-w_nah, w_nah, 1000)]),
    ]
)
sicht_nah = vf.sicht(vf.vernetze(d_nah), LAENGS, RADIAL, vf.raster_a(-65.0, 5.0), vh.raster_phi())
schaft_6 = ff.scheibe(6.0)
werte_nah = replace(werte_d, form=schaft_6, schrittweite=2.0)
bereich_nah = vf.bereich(sicht_nah, vf.mantelflaechen(sicht_nah), 6.0)
netz_nah = vh.vernetze(d_nah, vb.TOLERANZ_SCHLICHTEN)
for name_nah, werte_ in (
    ("Spirale", werte_nah),
    ("Zeilen", replace(werte_nah, bereich=bereich_nah)),
):
    bahn_nah = vb.schlichten(netz_nah, LAENGS, RADIAL, werte_)
    phi_nah, r_nah = [], []
    for von_, nach_ in zip(bahn_nah.punkte, bahn_nah.punkte[1:], strict=False):
        if nach_.eilgang or nach_.eintauchen or not -33.0 < min(von_.a, nach_.a) < -27.0:
            continue
        t_ = np.arange(max(1, math.ceil(abs(nach_.phi - von_.phi) / 0.05)))
        t_ = t_ / len(t_)
        phi_nah.append(np.radians(von_.phi + t_ * (nach_.phi - von_.phi)))
        r_nah.append(von_.r + t_ * (nach_.r - von_.r))
    phi_nah, r_nah = np.concatenate(phi_nah), np.concatenate(r_nah)
    tiefst = -math.inf
    for k in range(0, len(phi_nah), 1000):
        c = np.cos(phi_nah[k : k + 1000])[:, None]
        s = np.sin(phi_nah[k : k + 1000])[:, None]
        hoch = umriss_nah[None, :, 0] * c + umriss_nah[None, :, 1] * s
        neben = np.abs(umriss_nah[None, :, 1] * c - umriss_nah[None, :, 0] * s)
        stirn = r_nah[k : k + 1000, None] + schaft_6.hoehe(np.minimum(neben, 6.0))
        tiefst = max(tiefst, float(np.max(np.where(neben <= 6.0, hoch - stirn, -math.inf))))
    pruefe(
        len(phi_nah) > 10000 and tiefst <= 0.0,
        f"{name_nah} an der Abflachung x = 2: {tiefst:+.4f} mm ins Teil ({len(phi_nah)} Stellen)",
    )

# --- Ringgang vor der Wand (D-42) ----------------------------------------------------------
# Die Welle mit Absatz von oben: Die Wand bei −30 schaut zum Futter. Mit 2 mm je Umdrehung
# liegt die Spirale auf einem Teil des Umfangs 2 mm (die Kante hebt die Kugel) und 4 mm vor
# der Wand – dicht an ihr bleibt viel mehr stehen als die Kehle. Mit Ring hält sie gut
# 3 mm vor der Wand eine Umdrehung an: Dicht an ihr (a −31 … −30,5) bleibt die Kehle der
# Kugel, höchstens 3 − √(9 − 2,5²) ≈ 1,34 mm über Ø 30.
netz_absatz = vh.vernetze(welle.removeSplitter(), vb.TOLERANZ_SCHLICHTEN)


def rest_an_der_wand(bahn):
    """Wie viel die Bahn dicht an der Wand (a −31,1 … −30,4) über Ø 30 stehen lässt."""
    stange = rm.Stange(25.0, -60.0, 1.0)
    von, nach = [], []
    for vorher, punkt in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        if not punkt.eilgang and not vorher.eilgang:
            von.append((vorher.a, vorher.r, vorher.phi))
            nach.append((punkt.a, punkt.r, punkt.phi))
        elif not punkt.eilgang:
            stange.schnitt(punkt.a, punkt.r, punkt.phi, kugel)
    stange.fahre_stuecke(von, nach, kugel)
    dicht_dran = (stange.a > -31.1) & (stange.a < -30.4)
    return float(stange.r[dicht_dran].max() - 15.0)


grob = vb.Schlichtwerte(kugel, 25.0, 2.0, 0.0, 1.0, -60.0)
ohne_ring = vb.schlichten(netz_absatz, LAENGS, RADIAL, grob)
mit_ring = vb.schlichten(netz_absatz, LAENGS, RADIAL, replace(grob, waende=((-30.0, -1),)))
stelle = -30.0 - (3.0 + netz_absatz.toleranz + vb.RING_LUFT)  # die Kugel streift die Wand nicht
ring = [p for p in mit_ring.punkte if not p.eilgang and abs(p.a - stelle) < 1e-9]
pruefe(len(ring) >= 2 and ring[-1].phi - ring[0].phi >= 359.5 - 1e-6, f"Ring: {len(ring)}")
pruefe(
    abs(mit_ring.umdrehungen - ohne_ring.umdrehungen - 1.0) < 1e-9,
    f"Umdrehungen {ohne_ring.umdrehungen} → {mit_ring.umdrehungen}",
)
rest_ohne, rest_mit = rest_an_der_wand(ohne_ring), rest_an_der_wand(mit_ring)
pruefe(rest_ohne > 3.0, f"ohne Ring an der Wand nur {rest_ohne:.3f} stehen")
pruefe(rest_mit < 1.34 + 0.15, f"mit Ring an der Wand {rest_mit:.3f} stehen")
# Die Ringpunkte liegen auf der Hüllfläche wie die der Spirale – nicht im Teil.
a, r = dicht(mit_ring)
soll = im_schnitt(umriss, kugel, np.clip(a, -42.0, 0.0))
pruefe((r - soll).min() >= -1e-3, f"mit Ring im Teil: {(r - soll).min():.4f}")
print(ascii(f"Wand: an der Wand ohne Ring {rest_ohne:.2f} mm, mit Ring {rest_mit:.2f} mm"))

# --- Nur die Abflachung (V4) ---------------------------------------------------------------
# Welle Ø 20 von −40 bis 0, Abflachung auf x = 8 von −30 bis −10, Stange Ø 24; geschruppt
# mit R 3 nur dort (Aufmaß 0,3), geschlichtet mit der Kugel R 2 in Zeilen hin und her: Jede
# Fahrt beginnt im Eilgang knapp über dem Rest und taucht mit dem Eintauchvorschub ein; die
# Bahn bleibt im Bereich der Kugel, die Rundachse dreht nie ganz herum.
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
sicht_flach = vf.sicht(
    vf.vernetze(flach_welle), LAENGS, RADIAL, vf.raster_a(-45.0, 5.0), vh.raster_phi()
)
schruppen_flach = vb.schruppen(
    vh.vernetze(flach_welle),
    LAENGS,
    RADIAL,
    vb.Schruppwerte(
        3.0, 12.0, 2.0, 2.4, 0.3, 1.0, -60.0, bereich=vf.bereich(sicht_flach, [abflachung], 3.0)
    ),
)
stange = rm.Stange(12.0, -60.0, 1.0)
von, nach = [], []
for vorher, punkt in zip(schruppen_flach.punkte, schruppen_flach.punkte[1:], strict=False):
    if not punkt.eilgang:
        von.append((vorher.a, vorher.r, vorher.phi))
        nach.append((punkt.a, punkt.r, punkt.phi))
stange.fahre_stuecke(von, nach, 3.0)
kugel_klein = ff.kugel(2.0)
bereich_kugel = vf.bereich(sicht_flach, [abflachung], 2.0)
flach = vb.schlichten(
    vh.vernetze(flach_welle, vb.TOLERANZ_SCHLICHTEN),
    LAENGS,
    RADIAL,
    vb.Schlichtwerte(
        kugel_klein,
        12.0,
        0.5,
        0.0,
        1.0,
        -60.0,
        rest=(stange.a, stange.phi, stange.r),
        bereich=bereich_kugel,
    ),
)
im_vorschub = [p for p in flach.punkte if not p.eilgang]
drin = bereich_kugel.bei([p.a for p in im_vorschub], np.radians([p.phi for p in im_vorschub]))
pruefe(drin.all(), f"Schlichten: {int((~drin).sum())} Punkte außerhalb des Bereichs")
teile = stuecke(flach)
pruefe(1 <= len(teile) <= 4, f"Schlichten: {len(teile)} Fahrten")
knapp = 0
for vorher, punkt in zip(flach.punkte, flach.punkte[1:], strict=False):
    if vorher.eilgang and not punkt.eilgang:
        pruefe(punkt.eintauchen, f"hinein ohne Eintauchvorschub bei a {punkt.a:.2f}")
        knapp += vorher.r < 12.0 + 2.0 - 1e-9
        # Knapp: der Sicherheitsabstand über dem Rest, höchstens rest_ueber über der Bahn.
        tief = vorher.r - punkt.r
        pruefe(tief <= 2.0 + flach.rest_ueber + 1e-6, f"taucht {tief:.2f} mm ein")
pruefe(knapp == len(teile), f"nur {knapp} von {len(teile)} Stücken knapp über dem Rest")
winkel = [p.phi for p in flach.punkte[1:]]
pruefe(max(winkel) - min(winkel) < 120.0, f"C dreht von {min(winkel):.0f}° bis {max(winkel):.0f}°")
a_flach, r_flach = zip(*[(p.a, p.r) for p in im_vorschub], strict=True)
pruefe(
    min(a_flach) < -29.0 and max(a_flach) > -11.0, f"Zeilen von {min(a_flach)} bis {max(a_flach)}"
)
print(ascii(f"Abflachung: {len(teile)} Fahrten geschlichtet"))

# --- Linien längs (V4c) ----------------------------------------------------------------------
# Dieselbe Abflachung mit der Kugel R 2 in Linien längs: jede Linie bei festem Winkel, von
# Linie zu Linie wechselt die Richtung, die Linien liegen höchstens 0,5 mm ÷ r_max auseinander
# (r_max = 10 + Vernetzung: 2,86°) und nur über der Abflachung; die Kugel bleibt überall aus dem
# Teil (Ebene x = 8, Mantel Ø 20, die Kante dazwischen) und liegt über der Ebene auf ihr.
netz_flach = vh.vernetze(flach_welle, vb.TOLERANZ_SCHLICHTEN)
linien_werte = vb.Schlichtwerte(
    kugel_klein,
    12.0,
    0.5,
    0.0,
    1.0,
    -60.0,
    rest=(stange.a, stange.phi, stange.r),
    bereich=bereich_kugel,
    muster=vb.LINIEN,
)
linien = vb.schlichten(netz_flach, LAENGS, RADIAL, linien_werte)
im_vorschub = [p for p in linien.punkte if not p.eilgang]
drin = bereich_kugel.bei([p.a for p in im_vorschub], np.radians([p.phi for p in im_vorschub]))
pruefe(drin.all(), f"Linien: {int((~drin).sum())} Punkte außerhalb des Bereichs")
weit = math.degrees(0.5 / (10.0 + vb.TOLERANZ_SCHLICHTEN))
pruefe(2 <= linien.linien <= 360.0 / weit, f"{linien.linien} Linien")
# An den Wänden ließ das Schruppen hier (ohne Ringgang) einen schmalen Streifen stehen – den
# nehmen die Linien in einem Zug; rest_ueber sagt, wie hoch er ist.
pruefe(0.0 < linien.rest_ueber < 4.0, f"Linien: Rest über der Bahn {linien.rest_ueber:.3f}")


def linien_von(stueck):
    """[[Punkt, …], …] – die Linien eines Stücks: Punkte bei demselben Winkel."""
    ergebnis = []
    for punkt in stueck:
        if ergebnis and abs(punkt.phi - ergebnis[-1][-1].phi) < 1e-9:
            ergebnis[-1].append(punkt)
        else:
            ergebnis.append([punkt])
    return [z for z in ergebnis if len(z) > 1]


# Die Hauptfahrt (die Stufen davor sind kurz): alle Linien am Stück – auch über die Naht bei
# 0° hinweg, die Abflachung liegt beiderseits –, gegenläufig, im Winkelabstand.
alle_stuecke = stuecke(linien)
haupt = max(alle_stuecke, key=len)
zeilen = linien_von(haupt)
pruefe(
    len(zeilen) == linien.linien, f"{len(zeilen)} Linien in der Hauptfahrt, {linien.linien} gezählt"
)
richtungen = [np.sign(z[-1].a - z[0].a) for z in zeilen]
pruefe(all(r != 0 for r in richtungen), "eine Linie ohne Länge")
pruefe(
    all(x == -y for x, y in zip(richtungen, richtungen[1:], strict=False)),
    "die Richtung wechselt nicht von Linie zu Linie",
)
for z1, z2 in zip(zeilen, zeilen[1:], strict=False):
    pruefe(
        abs(z2[0].phi - z1[-1].phi) <= weit + 1e-6,
        f"Linien {abs(z2[0].phi - z1[-1].phi):.3f}° auseinander",
    )
    pruefe(abs(z2[0].a - z1[-1].a) < 1e-9, "die Drehung zur nächsten Linie fährt längs")


def abstand_zum_teil(x, y):
    """Abstand eines Punkts im Querschnitt zum Teil (Kreis R 10, bei x ≤ 8): Ebene, Mantel
    oder Kante – das Teil ist konvex."""
    if x <= 8.0 and math.hypot(x, y) <= 10.0:
        return 0.0
    moeglich = [math.hypot(x - 8.0, abs(y) - 6.0)]
    if x >= 8.0 and abs(y) <= 6.0:
        moeglich.append(x - 8.0)
    if x / max(math.hypot(x, y), 1e-9) <= 0.8:
        moeglich.append(math.hypot(x, y) - 10.0)
    return min(moeglich)


# Zwischen den Punkten (eine Linie über der Ebene ist zu zwei Punkten zusammengefasst) alle
# 0,5 mm: die Kugel nie im Teil; in der Hauptfahrt, wo sie ganz über der Ebene steht, auf ihr.
zu_tief, auf_der_ebene, ueber_der_ebene = 0.0, 0, 0
for stueck in alle_stuecke:
    for von, nach in zip(stueck, stueck[1:], strict=False):
        anzahl = max(1, int(round(abs(nach.a - von.a) / 0.5)))
        for t in np.arange(anzahl) / anzahl:
            a_p, r_p = von.a + t * (nach.a - von.a), von.r + t * (nach.r - von.r)
            phi_p = math.radians(von.phi + t * (nach.phi - von.phi))
            if not -26.5 < a_p < -13.5:
                continue  # dicht an den Wänden hebt die Kante die Kugel, davor liegt die Stufe
            mitte = r_p + 2.0
            x, y = mitte * math.cos(phi_p), mitte * math.sin(phi_p)
            zu_tief = max(zu_tief, 2.0 - abstand_zum_teil(x, y))
            if stueck is haupt and abs(y) <= 4.0:  # die Kugel steht ganz über der Ebene
                ueber_der_ebene += 1
                auf_der_ebene += abs(x - 10.0) <= LUFT + vb.SEHNE_HOECHSTENS
pruefe(zu_tief <= 1e-3, f"Linien: die Kugel {zu_tief:.4f} mm im Teil")
pruefe(ueber_der_ebene > 20, f"nur {ueber_der_ebene} Punkte über der Ebene")
pruefe(
    auf_der_ebene == ueber_der_ebene,
    f"{ueber_der_ebene - auf_der_ebene} Punkte nicht auf der Ebene",
)
print(ascii(f"Abflachung in Linien laengs: {linien.linien} Linien, {len(stuecke(linien))} Fahrten"))

# Nur im Gleichlauf (P-2026-10-02-28): jede Linie eine Fahrt für sich – senkrecht hinein, am
# Ende hinaus –, mit M3 von hinten nach vorn (a steigt: das Material der nächsten Linie, bei
# größerem Winkel, liegt dann rechts der Fahrt), mit M4 andersherum. Dieselben Linien wie hin
# und her, die Hauptfahrt mit wachsendem Winkel.
for gleichlauf, vor in ((True, 1.0), (False, -1.0)):
    einzeln = vb.schlichten(
        netz_flach,
        LAENGS,
        RADIAL,
        replace(linien_werte, nur_gleichlauf=True, gleichlauf=gleichlauf),
    )
    fahrten = stuecke(einzeln)
    pruefe(
        einzeln.linien == linien.linien and einzeln.rest_ueber == linien.rest_ueber,
        f"nur Gleichlauf: {einzeln.linien} Linien, Rest {einzeln.rest_ueber}",
    )
    pruefe(
        all(max(p.phi for p in f) - min(p.phi for p in f) < 1e-9 for f in fahrten),
        "nur Gleichlauf: eine Fahrt über mehr als eine Linie",
    )
    # Eine Stufe nur an einer Stelle längs ist hinein und gleich wieder hinaus – ohne Richtung.
    falsch = [f for f in fahrten if np.any(vor * np.diff([p.a for p in f]) < -1e-9)]
    pruefe(not falsch, f"nur Gleichlauf (vor {vor:+}): {len(falsch)} Linien andersherum")
    pruefe(
        all(vor * (f[-1].a - f[0].a) > 0 for f in fahrten[-einzeln.linien :]),
        "nur Gleichlauf: eine Linie der Hauptfahrt ohne Länge",
    )
    haupt_phi = [f[0].phi for f in fahrten[-einzeln.linien :]]
    pruefe(
        all(0 < y - x <= weit + 1e-6 for x, y in zip(haupt_phi, haupt_phi[1:], strict=False)),
        f"nur Gleichlauf: Winkel der Hauptfahrt {haupt_phi[:4]} …",
    )
    pruefe(
        len(fahrten) >= einzeln.linien and einzeln.umdrehungen < linien.umdrehungen + 1e-9,
        f"nur Gleichlauf: {len(fahrten)} Fahrten, {einzeln.umdrehungen:.3f} Umdrehungen",
    )
print(ascii(f"Abflachung nur im Gleichlauf: {len(fahrten)} Fahrten"))

# Rundum in Linien längs auf der Welle mit Absatz: 360 Linien (0,35 mm ÷ 20,005), jede auf
# der Hüllfläche – nie im Teil, höchstens den Sehnenfehler darüber –, eine Fahrt für alles.
linien_rundum = vb.schlichten(
    vh.vernetze(welle.removeSplitter(), vb.TOLERANZ_SCHLICHTEN),
    LAENGS,
    RADIAL,
    replace(werte, muster=vb.LINIEN),
)
pruefe(linien_rundum.linien == 360, f"rundum: {linien_rundum.linien} Linien")
pruefe(len(stuecke(linien_rundum)) == 1, f"rundum: {len(stuecke(linien_rundum))} Fahrten")
a, r = [], []
for stueck in stuecke(linien_rundum):
    for von, nach in zip(stueck, stueck[1:], strict=False):
        anzahl = max(1, int(round(abs(nach.a - von.a) / 0.5)))  # alle 0,5 mm längs
        t = np.arange(anzahl) / anzahl
        a.append(von.a + t * (nach.a - von.a))
        r.append(von.r + t * (nach.r - von.r))
a, r = np.concatenate(a), np.concatenate(r)
soll = im_schnitt(umriss, kugel, np.clip(a, -42.0, 0.0))
darueber = r - soll
pruefe(
    darueber.min() >= -1e-3,
    f"Linien im Teil: {darueber.min():.4f} (bei a {a[np.argmin(darueber)]:.3f})",
)
zu_hoch = darueber - erlaubt(umriss, kugel, a, soll)
pruefe(
    zu_hoch.max() <= 0, f"Linien zu hoch: {zu_hoch.max():+.4f} (bei a {a[np.argmax(zu_hoch)]:.3f})"
)
winkel = [p.phi for p in linien_rundum.punkte[1:]]
pruefe(max(winkel) - min(winkel) <= 360.0 + 1e-6, f"rundum dreht {max(winkel) - min(winkel):.1f}°")
print(ascii(f"Welle mit Absatz in Linien laengs: {len(linien_rundum.punkte)} Punkte"))

# --- Zeitgrenze: Kugelfräser Ø 6 auf der Welle Ø 60 × 100 mit Nocken, 0,35 mm ------------
teil = (
    Part.makeCylinder(30, 100, V(0, 0, -100))
    .fuse(Part.makeCylinder(12, 20, V(24, 0, -40)))
    .cut(Part.makeBox(10, 8, 30, V(25, -4, -90)))
)
beginn = time.time()
bahn = vb.schlichten(
    vh.vernetze(teil, vb.TOLERANZ_SCHLICHTEN),
    LAENGS,
    RADIAL,
    vb.Schlichtwerte(kugel, 40.0, 0.35, 0.0, 1.0, -130.0),
)
dauer = time.time() - beginn
print(ascii(f"Welle mit Nocken: {len(bahn.punkte)} Punkte in {dauer:.1f} s"))
pruefe(dauer < 30.0, f"zu langsam: {dauer:.1f} s")

# --- Der Rand der Stirn berührt nur (P-2026-10-03-30) -----------------------------------------
# Hinter a −10 steht die Stange noch ganz (40), davor ist alles weg. Die Kugel R 5 bei a −5 reicht
# mit ihrem Rand genau bis −10 – sie berührt die Stange dort ohne Volumen. Mitgezählt meldete das
# Schlichten an Manuels Teil 35 mm Rest hinter dem Teil.
rest_a = np.arange(-30.0, 0.25, 0.5)
rest_phi = vh.raster_phi(1.0)
rest_r = np.where(rest_a[:, None] < -10.0 + 1e-9, 40.0, 0.0) + np.zeros((1, len(rest_phi)))
oben_rand = vb._nicht_tiefer(
    (rest_a, rest_phi, rest_r), ff.kugel(5.0), 0.0, np.array([-5.0]), np.zeros(1)
)
pruefe(float(oben_rand[0]) < 1.0, f"Rand der Kugel zählt als Rest: {float(oben_rand[0]):.2f}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
