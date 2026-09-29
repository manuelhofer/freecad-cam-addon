# Prüft Rohteil und Fertigteil in der Simulation (W-003 Stufe V3g): Ein Schnitt nimmt
# unter dem Fräser bis zu seiner Spitze weg, daneben nichts; eine Spirale auf Radius 38
# lässt die Stange überall dort auf 38, wo sie lief. Dann „Rundum schruppen“ auf der
# Beispiel-Drehmaschine (Welle Ø 40 in Ø 50, die Stange ragt weit genug heraus): Nach
# dem Abfahren bleibt rundum etwa das Aufmaß, nirgends fehlt etwas im Teil; zurück
# zu einer früheren Station rechnet von vorn.
import math
import os
import sys
import time

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import abfahren as ab
from camaddon import beispielmaschine as bm
from camaddon import reichweite as rw
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import vierachs_achsen as va
from camaddon import vierachs_operation as vo
from camaddon import vierachs_rohteil as vr

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

# --- Rundum schruppen auf der Beispiel-Drehmaschine ---------------------------------------
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
FreeCAD.closeDocument(doc.Name)
FreeCAD.closeDocument(asm.Document.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
