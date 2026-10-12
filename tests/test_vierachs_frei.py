# Prüft „im Freien schnell“ bei den Rundum-Bahnen (Manuel, 2026-10-05: eine Scheibe Ø 40 × 10 mit
# einem Zapfen Ø 15 × 20, 10 neben der Mitte, in der Stange Ø 40 – „er bearbeitet beim Schruppen
# auch die Ø 40 und beim Schlichten auch“; „nicht pauschalisieren“). Je Punkt gerechnet: beim
# Schruppen frei, wo die Hüllfläche nicht unter der Stange liegt; beim Schlichten, wo der Rest
# nach dem Schruppen unter dem Fräser nirgends über die Bahn reicht. In der Stange Ø 40 ist der
# Weg über die Scheibe frei (Schruppen mehr als die Hälfte, Schlichten fast die Hälfte); die
# Bahn nachgefahren im Modell der Stange (restmaterial.Stange, erst Schruppen, dann Schlichten):
# Kein freier Lauf nimmt etwas weg (beim Schruppen höchstens FREI_REST, P-2026-10-12-150). In der Stange Ø 45 ist das Schruppen nur frei, wo die Lagen davor schon alles nahmen, und das
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


def frei_und_weg(stange, bahn, fraeser, vorne=math.inf):
    """(mm frei, mm im Vorschub, größte Menge, die ein freier Lauf wegnimmt, mm frei ganz vor
    `vorne`) – die Bahn der Reihe nach im Modell der Stange: je Lauf gleicher Art ein Schritt."""
    frei_mm = alle_mm = groesste = vorne_mm = 0.0
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
        lauf.append(((p.a, p.r, p.phi, p.q), (q.a, q.r, q.phi, q.q)))
        weg = vb._weg(p, q)
        alle_mm += weg
        frei_mm += weg if q.frei else 0.0
        vorne_mm += weg if q.frei and min(p.a, q.a) > vorne else 0.0
    fahren(lauf, art)
    return frei_mm, alle_mm, groesste, vorne_mm


ergebnis = {}
quer_schruppen = {}
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
    # Mit allen Lagen: Hier geht es um die freien Wege (das Kürzen der Folgelagen, P-2026-10-11-57,
    # nähme die frei laufenden mit weg und änderte ihren Anteil) – gekürzt nie länger, unten.
    schruppen = vo.lege_an(
        job, tc, achse, zustellung=2.5, steigung=6.0, aufmass=0.3, nur_noetig=False
    )
    tc2 = js.controller_ohne_transaktion(doc, job, kugel, kugel.schnittwerte[wz.ALLE][0])
    schlichten = vs.lege_an(job, tc2, achse, 0.5, aufmass=0.0)
    doc.recompute()
    b1 = vo.rechne(schruppen, job, job.Model.Group, 6.0)
    schruppen.NurNoetig = True
    gekuerzt = vo.rechne(schruppen, job, job.Model.Group, 6.0)
    schruppen.NurNoetig = False
    pruefe(
        vb.dauer(gekuerzt, 1000.0, freivorschub=10000.0)
        <= vb.dauer(b1, 1000.0, freivorschub=10000.0) + 1e-6,
        f"Ø {durchmesser}: gekürzt länger",
    )
    # Schruppen mit der Querachse (P-2026-10-11-04): dieselbe Prüfung – danach wieder wie
    # angelegt, das Schlichten rechnet seinen Rest aus diesem Schruppen.
    wie_angelegt = schruppen.Querachse
    schruppen.Querachse = True
    b1q = vo.rechne(schruppen, job, job.Model.Group, 6.0)
    schruppen.Querachse = wie_angelegt
    schlichten.Querachse = False
    b2 = vs.rechne(schlichten, job, job.Model.Group)
    # Mit der Querachse (Manuels CLX mit Y): dieselbe Prüfung (P-2026-10-10-56).
    schlichten.Querachse = True
    b3 = vs.rechne(schlichten, job, job.Model.Group)
    # Die Stange, wo sie steht: ihre Länge längs der Achse.
    bb = job.Stock.Shape.BoundBox
    ecken = [
        V(x, y, z).dot(achse.laengs)
        for x in (bb.XMin, bb.XMax)
        for y in (bb.YMin, bb.YMax)
        for z in (bb.ZMin, bb.ZMax)
    ]
    stange = rm.Stange(durchmesser / 2, min(ecken), max(ecken))
    sq_frei, sq_alle, sq_weg, _vorne = frei_und_weg(stange, b1q, 6.0)
    pruefe(any(abs(p.q) > 1e-6 for p in b1q.punkte), f"Ø {durchmesser}: Schruppen ohne Querachse")
    # Frei auch, wo die Lagen davor schon alles genommen haben (P-2026-10-12-150): Dort darf der
    # Rest im Raster der Stange um vierachs_bahn.FREI_REST über der Stirn liegen (wo der Fräser an
    # einer Flanke anliegt) – so viel nimmt ein freier Lauf dann höchstens.
    schrupp_frei_grenze = vb.FREI_REST + 0.01
    pruefe(
        sq_weg < schrupp_frei_grenze,
        f"Ø {durchmesser}: freier Lauf beim Schruppen quer nimmt {sq_weg:.3f} weg",
    )
    stange = rm.Stange(durchmesser / 2, min(ecken), max(ecken))
    s_frei, s_alle, s_weg, _vorne = frei_und_weg(stange, b1, 6.0)
    nach_schruppen = stange.r.copy()
    # Ganz vor der Stange (die Kugel erreicht ihre Stirn nicht mehr) ist es immer frei.
    vor_der_stange = max(ecken) + 3.0
    l_frei, l_alle, l_weg, l_vorne = frei_und_weg(stange, b2, ff.kugel(3.0), vor_der_stange)
    stange.r = nach_schruppen
    q_frei, q_alle, q_weg, _vorne = frei_und_weg(stange, b3, ff.kugel(3.0), vor_der_stange)
    ergebnis[durchmesser] = (s_frei, s_alle, l_frei - l_vorne, l_alle, q_frei, q_alle)
    quer_schruppen[durchmesser] = (sq_frei, sq_alle)
    pruefe(b3.querachse, f"Ø {durchmesser}: Schlichten ohne Querachse")
    pruefe(q_weg < 0.01, f"Ø {durchmesser}: ein freier Lauf mit Querachse nimmt {q_weg:.3f} weg")
    pruefe(
        s_weg < schrupp_frei_grenze,
        f"Ø {durchmesser}: ein freier Lauf beim Schruppen nimmt {s_weg:.3f} weg",
    )
    pruefe(l_weg < 0.01, f"Ø {durchmesser}: ein freier Lauf beim Schlichten nimmt {l_weg:.3f} weg")
    print(
        ascii(
            f"Ø {durchmesser}: Schruppen frei {s_frei:.0f} von {s_alle:.0f} mm, "
            f"{vb.dauer(b1, 1000.0):.2f} -> {vb.dauer(b1, 1000.0, freivorschub=10000.0):.2f} min; "
            f"Schlichten frei {l_frei:.0f} von {l_alle:.0f} mm, mit Querachse {q_frei:.0f} von "
            f"{q_alle:.0f} mm"
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

s_frei, s_alle, l_frei, l_alle, q_frei, q_alle = ergebnis[40.0]
pruefe(s_frei > 0.5 * s_alle, f"Ø 40: Schruppen nur {s_frei:.0f} von {s_alle:.0f} mm frei")
sq_frei, sq_alle = quer_schruppen[40.0]
pruefe(sq_frei > 0.3 * sq_alle, f"Ø 40: Schruppen quer nur {sq_frei:.0f} von {sq_alle:.0f} mm frei")
print(
    ascii(
        f"Schruppen quer frei: Ø 40 {sq_frei:.0f} von {sq_alle:.0f} mm, Ø 45 {quer_schruppen[45.0][0]:.0f} von {quer_schruppen[45.0][1]:.0f} mm"
    )
)
pruefe(l_frei > 0.4 * l_alle, f"Ø 40: Schlichten nur {l_frei:.0f} von {l_alle:.0f} mm frei")
pruefe(q_frei > 0.3 * q_alle, f"Ø 40: mit Querachse nur {q_frei:.0f} von {q_alle:.0f} mm frei")
s_frei, _s_alle, l_frei, l_alle, _q_frei, _q_alle = ergebnis[45.0]
# Ø 45: Außerhalb der Stange liegt nichts – frei nur, wo die Lagen davor schon alles nahmen
# (P-2026-10-12-150; hier alle Lagen, ungekürzt); was ein freier Lauf dort höchstens wegnimmt,
# prüft frei_und_weg oben (FREI_REST). Nicht alles frei.
pruefe(s_frei < 0.9 * _s_alle, f"Ø 45: Schruppen {s_frei:.0f} von {_s_alle:.0f} mm frei")
pruefe(l_frei < 0.01 * l_alle, f"Ø 45: Schlichten {l_frei:.0f} mm frei – der Ø 40 gehört dazu")

# In 3D nachgerechnet (P-2026-10-11-27): Manuels Nasen-Testteil, die Stange als Voxel – erst das
# Schruppen, dann das Schlichten mit und ohne Querachse. Kein freier Satz nimmt etwas weg. Bis
# dahin hielt das Schlichten Ecken vorne an der Platte für leer, die das Schruppen stehen ließ
# (das Restmodell, ein Radius je Strahl, sieht sie nicht): bei 1 mm Voxeln 102 Sätze.
from camaddon import vierachs_vorschau as vv  # noqa: E402
from camaddon import voxelstange as vx  # noqa: E402
from camaddon.voxelstange import Voxelstange  # noqa: E402

nase = FreeCAD.openDocument(os.path.join(ADDON, "beispiele", "testteil_4achs_nase.FCStd"))
job = nase.getObject("Job")
rop, sop = nase.getObject("RundumSchruppen"), nase.getObject("RundumSchlichten")
laengs = rop.Stangenachse
bb = job.Stock.Shape.BoundBox
ecken = [
    V(x, y, z).dot(laengs)
    for x in (bb.XMin, bb.XMax)
    for y in (bb.YMin, bb.YMax)
    for z in (bb.ZMin, bb.ZMax)
]
stange_radius = vs._stange(job, laengs)[1]
schruppbahn = vo.rechne(rop, job, job.Model.Group, float(rop.ToolController.Tool.Diameter) / 2)
nach_schruppen = Voxelstange(stange_radius, min(ecken), max(ecken), h=1.0)
weg = nach_schruppen.fahre(schruppbahn.punkte, float(rop.ToolController.Tool.Diameter) / 2, False)
frei = np.array([bool(p.frei) for p in schruppbahn.punkte])
schneiden = int(np.sum(frei & (weg > 0)))
pruefe(schneiden == 0, f"Nase, Schruppen: {schneiden} freie Sätze schneiden Material")
# „C dreht nicht zurück“ auch beim Schruppen mit der Querachse (Frage 11, P-2026-10-11-47): in
# älteren Operationen angehakt; in keiner Lage dreht C zurück (vorher 266-mal, 3741°).
pruefe(bool(rop.Stetig) and bool(rop.Querachse), "Nase: Schruppen nicht stetig mit Querachse")
zurueck, lage = 0.0, []
for p in schruppbahn.punkte + [vb.Punkt(True, 0.0, 0.0, 0.0)]:
    if p.eilgang:
        if len(lage) > 1:
            schritte = np.diff(lage) * np.sign(lage[-1] - lage[0])
            zurueck += float(-schritte[schritte < 0].sum())
        lage = []
    else:
        lage.append(p.phi)
pruefe(zurueck < 1e-6, f"Nase, Schruppen: C dreht {zurueck:.0f}° zurück")
# Das fertige Teil als Voxel (übers Netz, P-2026-10-11-42): so groß wie das Teil, und das
# Schruppen nahm nichts davon weg.
fertig = nach_schruppen.teil(vs._teil(job.Model.Group), laengs, rop.Werkzeugrichtung)
volumen = float(fertig.sum()) * nach_schruppen.h**3
pruefe(
    abs(volumen / vs._teil(job.Model.Group).Volume - 1) < 0.02,
    f"Nase: das Teil als Voxel {volumen:.0f} mm³",
)
pruefe(bool(nach_schruppen.material[fertig].all()), "Nase: das Schruppen schneidet ins Teil")
kugel_radius = vs.form_des_controllers(sop.ToolController).radius
for quer in (True, False):
    sop.Querachse = quer
    bahn = vs.rechne(sop, job, job.Model.Group)
    stange = Voxelstange(stange_radius, min(ecken), max(ecken), h=1.0)
    stange.material = nach_schruppen.material.copy()
    weg = stange.fahre(bahn.punkte, kugel_radius, True)
    frei = np.array([bool(p.frei) for p in bahn.punkte])
    schneiden = int(np.sum(frei & (weg > 0)))
    pruefe(schneiden == 0, f"Nase, Querachse {quer}: {schneiden} freie Sätze schneiden Material")
    pruefe(frei.any(), f"Nase, Querachse {quer}: kein freier Satz mehr")
    if quer:
        # „C dreht nicht zurück“ (Stetig, in älteren Operationen angehakt; P-2026-10-11-37): Die
        # Rundachse läuft längs der Spirale nie zurück – bis dahin 741-mal, 22 000°.
        winkel = np.array([p.phi for p in bahn.punkte if not p.eilgang])
        schritte = np.diff(winkel) * np.sign(winkel[-1] - winkel[0])
        pruefe(bool(sop.Stetig), "Nase: „C dreht nicht zurück“ nicht angehakt")
        pruefe(
            float(schritte.min()) > -1e-6,
            f"Nase: C dreht {float(-schritte[schritte < 0].sum()):.0f}° zurück",
        )
# Der Rest für die Kugel (Frage 8, P-2026-10-11-44) wie im Assistenten: Die Kugel nimmt nach dem
# Schruppen insgesamt rund 12 cm³, höchstens wenige mm² Eingriff je mm Weg – am Morgen des 11.10.
# standen hier 408, weil der Weg quer (Y) nicht mitzählte.
sop.Querachse = True
schlichtbahn = vs.rechne(sop, job, job.Model.Group)


def _saetze(b):
    return vx.als_feld(b.punkte), [bool(p.eilgang) for p in b.punkte]


rest = vv.rest(
    nase,
    job.Name,
    tuple(laengs),
    _saetze(schruppbahn),
    vs.form_des_controllers(rop.ToolController),
    _saetze(schlichtbahn),
    vs.form_des_controllers(sop.ToolController),
    1.0,
)
pruefe(
    # 12,8 cm³ – seit „Folgelagen nur, wo nötig“ (P-2026-10-11-57) 14,1: die Kämme der zweiten Lage
    rest is not None and 1.0 < rest["hoechstens"] < 10.0 and 10000 < rest["volumen"] < 16000,
    f"Nase, Rest für die Kugel: {rest}",
)
FreeCAD.closeDocument(nase.Name)

FreeCAD.closeDocument(asm.Document.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
