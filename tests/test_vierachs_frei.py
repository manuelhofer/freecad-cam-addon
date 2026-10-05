# Prüft „im Freien schnell“ bei den Rundum-Bahnen (Manuel, 2026-10-05: eine Scheibe Ø 40 × 10 mit
# einem Zapfen Ø 15 × 20, 10 neben der Mitte, in der Stange Ø 40 – „er bearbeitet beim Schruppen
# auch die Ø 40 und beim Schlichten auch“; „nicht pauschalisieren“). Je Punkt gerechnet: beim
# Schruppen frei, wo die Hüllfläche nicht unter der Stange liegt; beim Schlichten, wo der Rest
# nach dem Schruppen unter dem Fräser nirgends über die Bahn reicht. In der Stange Ø 40 ist der
# Weg über die Scheibe frei (Schruppen mehr als die Hälfte, Schlichten fast die Hälfte); die
# Bahn nachgefahren im Modell der Stange (restmaterial.Stange, erst Schruppen, dann Schlichten):
# Kein freier Lauf nimmt etwas weg. In der Stange Ø 45 bleibt das Schruppen, wie es war, und das
# Schlichten fährt den Ø 40. Die Befehle: frei mit dem Freivorschub, sonst mit dem Vorschub.
import math
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import beispielmaschine as bm
from camaddon import fraeserform as ff
from camaddon import job_schnittwerte as js
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_achsen as va
from camaddon import vierachs_bahn as vb
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
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
kugel = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)
kugel.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.5, ap=6, vc=150, fz=0.04)]
ue.uebergeben(wz.Bibliothek([kugel]))
asm, ma = bm.drehmaschine()
achse = va.von_maschine(asm, ma)[0]
teil_form = Part.makeCylinder(20, 10, V(0, 0, 0), V(0, 0, 1)).fuse(
    Part.makeCylinder(7.5, 20, V(10, 0, 10), V(0, 0, 1))
)
teil_form = teil_form.removeSplitter()


def frei_und_weg(stange, bahn, fraeser):
    """(mm frei, mm im Vorschub, größte Menge, die ein freier Lauf wegnimmt) – die Bahn der Reihe
    nach im Modell der Stange: je Lauf gleicher Art ein Schritt."""
    frei_mm = alle_mm = groesste = 0.0
    lauf, art = [], None

    def fahren(lauf, frei):
        nonlocal groesste
        if not lauf:
            return
        vorher = stange.r.copy()
        von = np.array([s[0] for s in lauf])
        nach = np.array([s[1] for s in lauf])
        stange.fahre_stuecke(von, nach, fraeser)
        if frei:
            groesste = max(groesste, float(np.max(vorher - stange.r)))

    for p, q in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        if q.eilgang:
            continue
        if art is not None and bool(q.frei) != art:
            fahren(lauf, art)
            lauf = []
        art = bool(q.frei)
        lauf.append(((p.a, p.r, p.phi), (q.a, q.r, q.phi)))
        weg = vb._weg(p, q)
        alle_mm += weg
        frei_mm += weg if q.frei else 0.0
    fahren(lauf, art)
    return frei_mm, alle_mm, groesste


ergebnis = {}
for durchmesser in (40.0, 45.0):
    doc = FreeCAD.newDocument("Zapfen")
    teil = doc.addObject("Part::Feature", "Teil")
    teil.Shape = teil_form
    doc.recompute()
    mit_zapfen = next(
        f
        for f in teil.Shape.Faces
        if isinstance(f.Surface, Part.Plane) and abs(f.BoundBox.ZMin - 10) < 1e-6
    )
    lage = vr.berechne(teil.Shape, mit_zapfen, achse, durchmesser=durchmesser)
    pruefe(vr.aufmass(lage, durchmesser) >= 0, f"Ø {durchmesser}: passt nicht")
    job = vr.richte_ein(doc, teil, lage, vr.Stange(durchmesser, frei_hinten=40.0), achse)
    tc = job.Tools.Group[0]
    tc.Tool.Diameter = 12
    tc.HorizFeed = "1000 mm/min"
    schruppen = vo.lege_an(job, tc, achse, zustellung=2.5, steigung=6.0, aufmass=0.3)
    tc2 = js.controller_ohne_transaktion(doc, job, kugel, kugel.schnittwerte[wz.ALLE][0])
    schlichten = vs.lege_an(job, tc2, achse, 0.5, aufmass=0.0)
    doc.recompute()
    b1 = vo.rechne(schruppen, job, job.Model.Group, 6.0)
    b2 = vs.rechne(schlichten, job, job.Model.Group)
    # Die Stange, wo sie steht: ihre Länge längs der Achse.
    bb = job.Stock.Shape.BoundBox
    ecken = [
        V(x, y, z).dot(achse.laengs)
        for x in (bb.XMin, bb.XMax)
        for y in (bb.YMin, bb.YMax)
        for z in (bb.ZMin, bb.ZMax)
    ]
    stange = rm.Stange(durchmesser / 2, min(ecken), max(ecken))
    s_frei, s_alle, s_weg = frei_und_weg(stange, b1, 6.0)
    l_frei, l_alle, l_weg = frei_und_weg(stange, b2, ff.kugel(3.0))
    ergebnis[durchmesser] = (s_frei, s_alle, l_frei, l_alle)
    pruefe(s_weg < 0.01, f"Ø {durchmesser}: ein freier Lauf beim Schruppen nimmt {s_weg:.3f} weg")
    pruefe(l_weg < 0.01, f"Ø {durchmesser}: ein freier Lauf beim Schlichten nimmt {l_weg:.3f} weg")
    print(
        ascii(
            f"Ø {durchmesser}: Schruppen frei {s_frei:.0f} von {s_alle:.0f} mm, "
            f"{vb.dauer(b1, 1000.0):.2f} -> {vb.dauer(b1, 1000.0, freivorschub=10000.0):.2f} min; "
            f"Schlichten frei {l_frei:.0f} von {l_alle:.0f} mm"
        )
    )
    if durchmesser == 40.0:
        # Die Befehle: frei schneller (G93: F = 1 ÷ Zeit, je Satz der Weg ÷ F).
        befehle = vb.befehle(
            b1, achse.laengs, va.radial(achse), "C", 1, 1000.0, freivorschub=10000.0
        )
        ohne = vb.befehle(b1, achse.laengs, va.radial(achse), "C", 1, 1000.0)
        zeit = sum(1.0 / c.Parameters["F"] for c in befehle if c.Name == "G1") / 60.0
        zeit_ohne = sum(1.0 / c.Parameters["F"] for c in ohne if c.Name == "G1") / 60.0
        pruefe(
            math.isclose(zeit, vb.dauer(b1, 1000.0, freivorschub=10000.0), rel_tol=0.02)
            and zeit < 0.6 * zeit_ohne,
            f"Befehle: {zeit:.2f} statt {zeit_ohne:.2f} min",
        )
    FreeCAD.closeDocument(doc.Name)

s_frei, s_alle, l_frei, l_alle = ergebnis[40.0]
pruefe(s_frei > 0.5 * s_alle, f"Ø 40: Schruppen nur {s_frei:.0f} von {s_alle:.0f} mm frei")
pruefe(l_frei > 0.4 * l_alle, f"Ø 40: Schlichten nur {l_frei:.0f} von {l_alle:.0f} mm frei")
s_frei, _s_alle, l_frei, l_alle = ergebnis[45.0]
pruefe(s_frei == 0.0, f"Ø 45: Schruppen {s_frei:.0f} mm frei")
pruefe(l_frei < 0.01 * l_alle, f"Ø 45: Schlichten {l_frei:.0f} mm frei – der Ø 40 gehört dazu")

FreeCAD.closeDocument(asm.Document.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
