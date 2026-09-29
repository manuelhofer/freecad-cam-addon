# Prüft „Rundum schruppen“ auf der Beispiel-Drehmaschine (W-003 Stufe V3e): Welle Ø 40
# in der Stange Ø 50, Rundachse C von der Maschine, T1 auf dem radialen Platz P1. Das
# Prüffenster rechnet ohne TCPM – die Linearachsen stehen wie mit C auf 0, C dreht
# darunter –, die Zeit folgt G93, kein Hinweis zur Werkzeuglage. Die Kollisionsprüfung
# findet mit 125 mm Werkzeuglänge nichts (auch nicht beim Rückzug nach der Lage und
# 2 mm vor dem Futter); mit 50 mm stößt der Revolver ans Futter – das Teil ragt nur
# um den Abstich heraus. Mit T2 (axial auf P2) sagt ein Hinweis, dass die Bahn ein
# radiales Werkzeug aus +X braucht.
import math
import os
import sys
import time

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import abfahren as ab
from camaddon import beispielmaschine as bm
from camaddon import kollision as kb
from camaddon import reichweite as rw
from camaddon import sprache
from camaddon import verfahren as vf
from camaddon import vierachs_achsen as va
from camaddon import vierachs_bahn as vb
from camaddon import vierachs_operation as vo
from camaddon import vierachs_rohteil as vr
from camaddon import werkzeuge as wz
from camaddon.kette import LINEAR

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
VORSCHUB = 1500.0  # mm/min

asm, ma = bm.drehmaschine()
achsen = va.von_maschine(asm, ma)
pruefe(len(achsen) == 1 and achsen[0].buchstabe == "C", f"Rundachsen: {achsen}")
achse = achsen[0]

doc = FreeCAD.newDocument("Rundum")
welle = doc.addObject("Part::Feature", "Welle")
welle.Shape = Part.makeCylinder(20, 30, V(), V(1, 0, 0))
doc.recompute()
stirn = next(
    f
    for f in welle.Shape.Faces
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
)
lage = vr.berechne(welle.Shape, stirn, achse, durchmesser=50)
job = vr.richte_ein(doc, welle, lage, vr.Stange(50.0), achse, beschriftung="Welle 4 Achsen")
tc = job.Tools.Group[0]
tc.Tool.Diameter = 12
tc.HorizFeed = f"{VORSCHUB} mm/min"
tc.ToolNumber = 1
op = vo.lege_an(job, tc, achse, zustellung=2.5, steigung=6.0, aufmass=0.3)
doc.recompute()
pruefe(op.Lagen == 2, f"Lagen: {op.Lagen}")

p = rw.Pruefung(asm, ma)
nullpunkt = rw.vorschlag_nullpunkt(job)
ergebnis = p.pruefe_job(job, nullpunkt)
hinweise = " | ".join(ergebnis.hinweise)
pruefe("radial aus" not in hinweise, f"Hinweis zur Lage trotz P1: {hinweise}")
pruefe("längs Z gerechnet" not in hinweise, f"Hinweis für 3-Achs-Bahnen: {hinweise}")
pruefe("rundachse" not in hinweise.lower(), f"Hinweis zur Rundachse: {hinweise}")
pruefe(
    not ergebnis.ueberschreitungen,
    f"über der Grenze: {[u.text() for u in ergebnis.ueberschreitungen]}",
)

# --- Abfahren: ohne TCPM, Zeit nach G93 --------------------------------------------------
beginn = time.time()
fahrt = ab.abfahrt(p, job, nullpunkt)
dauer_abfahren = time.time() - beginn
aufnahme = p.werkzeugaufnahme(1)
laenge = fahrt.operationen[0].laenge
c1 = next(a for a in fahrt.achsen if vf.namen(ma, a) == "C1")
gedreht = [
    i
    for i, s in enumerate(fahrt.stationen)
    if abs(s.rund.get("C", 0.0)) > 1.0 and s.stellungen is not None
]
pruefe(len(gedreht) > 100, f"Stationen mit C: {len(gedreht)}")
# Am Werkstück (so zeigt das Fenster die Bahn): der Punkt um −C gedreht, wie in FreeCAD.
am_teil = fahrt.am_werkstueck()
for i in gedreht[:: max(1, len(gedreht) // 7)]:
    station = fahrt.stationen[i]
    ohne = p.stellungen(station.punkt, aufnahme, laenge, nullpunkt)
    werte = dict(zip(fahrt.achsen, station.stellungen, strict=True))
    linear = [a for a in ohne if a.art == LINEAR]
    pruefe(
        all(abs(werte[a] - ohne[a]) < 1e-6 for a in linear),
        f"Linearachsen hängen an C (TCPM?) bei {station.punkt}, C {station.rund['C']}",
    )
    pruefe(abs(werte[c1] - station.rund["C"]) < 1e-6, f"C1 {werte[c1]}, C {station.rund['C']}")
    soll = FreeCAD.Rotation(V(0, 0, 1), -station.rund["C"]).multVec(V(*station.punkt))
    pruefe(
        (V(*am_teil[i]) - soll).Length < 1e-6,
        f"am Werkstück {am_teil[i]} statt {tuple(soll)} (C {station.rund['C']})",
    )
bahn = vo.rechne(op, job, job.Model.Group, 6.0)
# C dreht fortlaufend (endlos) – am Ende so weit, wie die Spiralen zusammen drehen.
tiefstes_c = min(s.rund.get("C", 0.0) for s in fahrt.stationen)
pruefe(
    abs(tiefstes_c + bahn.punkte[-1].phi) < 1e-6, f"C bis {tiefstes_c}, Bahn {bahn.punkte[-1].phi}"
)
im_vorschub = vb.dauer(bahn, VORSCHUB) * 60.0
pruefe(
    im_vorschub <= fahrt.dauer <= im_vorschub + 30.0,
    f"Dauer {fahrt.dauer:.1f} s, im Vorschub {im_vorschub:.1f} s",
)
print(ascii(f"Abfahren: {len(fahrt.stationen)} Stationen in {dauer_abfahren:.1f} s"))

# --- Kollision: mit 125 mm nichts -------------------------------------------------------------
# Eine Lage mit der größten Steigung (D) – weniger Stationen, dieselben Stellen: vorne
# hinein, rundum am Teil, 2 mm vor dem Futter, Rückzug im Eilgang.
op.Zustellung = 5.0
op.VorschubJeUmdrehung = 12.0
tc.Tool.Length = 125.0
doc.recompute()
pruefe(op.Lagen == 1, f"Lagen: {op.Lagen}")
fahrt = ab.abfahrt(p, job, nullpunkt)
beginn = time.time()
kollision = kb.kollision(fahrt, job, nullpunkt, wz.Bibliothek())
dauer_kollision = time.time() - beginn
pruefe(not kollision.befunde, f"Befunde: {[b.text() for b in kollision.befunde][:3]}")
# Je Station kaum mehr als zwei Stellen: Futter und Welle sind rund um C, sie bewegen sich
# beim Drehen nicht (P-2026-09-27-50).
pruefe(
    kollision.stellen < 3 * len(fahrt.stationen),
    f"{kollision.stellen} Stellen für {len(fahrt.stationen)} Stationen",
)
print(
    ascii(
        f"Kollision: {len(fahrt.stationen)} Stationen, {kollision.stellen} Stellen in "
        f"{dauer_kollision:.1f} s"
    )
)

# --- Mit 50 mm: Der Revolver stößt ans Futter ----------------------------------------------
tc.Tool.Length = 50.0
doc.recompute()
fahrt = ab.abfahrt(p, job, nullpunkt)
anfang = ab.Abfahrt(p, fahrt.achsen, fahrt.stationen[:20], fahrt.operationen)
anfang._fertig()
paare = {(b.a, b.b) for b in kb.kollision(anfang, job, nullpunkt, wz.Bibliothek()).beruehrungen}
pruefe(("„Revolver“", "„Spindel“") in paare, f"Revolver am Futter: {paare}")

# --- T2 sitzt axial: Hinweis ------------------------------------------------------------------
tc.ToolNumber = 2
doc.recompute()
hinweise = " | ".join(rw.Pruefung(asm, ma).pruefe_job(job, nullpunkt).hinweise)
pruefe(
    "radial aus +X zur Achse zeigt – T2 sitzt auf" in hinweise,
    f"kein Hinweis für T2 auf P2: {hinweise}",
)
pruefe(math.isfinite(fahrt.dauer), "Dauer")

FreeCAD.closeDocument(doc.Name)
FreeCAD.closeDocument(asm.Document.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
