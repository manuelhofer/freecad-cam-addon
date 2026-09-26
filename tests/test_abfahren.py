# Prüft das Abfahren (W-001, Stufe 4b; abfahren.py): Aus der Bahn eines Jobs werden
# Stationen mit ihrer Zeit – Vorschubsätze mit F (mm/s), Eilgang je Achse aus der
# Maschine, die langsamste bestimmt; Kreise in 5°-Schritten, nach dem Bohrzyklus
# der Rückzug. Die Zeiten gegen Handrechnung an der Beispiel-Fräse; zwischen zwei
# Stationen fährt die Maschine geradlinig (stellungen_bei); eine Rundachse im
# Vorschub zählt in Grad; ohne F gilt 1000 mm/min mit Hinweis; der Revolver
# schwenkt zwischen zwei Werkzeugen, auch in einem Vorschubsatz ohne Weg; Kreise
# halten auch an den Umkehrstellen der Achsen, sodass jede Überschreitung eine
# Station ist; Punkte, die eine Drehmaschine ohne Y nicht erreicht, lassen sie
# stehen.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)
sys.path.insert(0, os.path.join(ADDON, "tests"))

import beispielmaschinen
import FreeCAD

from camaddon import abfahren as ab
from camaddon import beispielmaschine, sprache
from camaddon import maschine as m
from camaddon import reichweite as rw
from camaddon import verfahren as vf
from camaddon import werkzeuge as wz

sprache.setze_sprache("de")
fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nahe(a, b, genau=1e-6):
    return a is not None and b is not None and abs(a - b) < genau


def neuer_job(ops, name="Teil"):
    """Ein Dokument mit einem Quader und einem Job; `ops`: je Operation (G-Code, T-Nummer)."""
    import Path.Main.Job as PathJob
    import Path.Op.Custom as PathCustom

    doc = FreeCAD.newDocument(name)
    quader = doc.addObject("Part::Box", "Teil")
    quader.Length, quader.Width, quader.Height = 100, 60, 20
    doc.recompute()
    job = PathJob.Create("Job", [quader])
    for i, (zeilen, nummer) in enumerate(ops):
        op = PathCustom.Create(f"Op{i + 1}")
        op.Gcode = zeilen
        if nummer != 1:
            from Path.Tool import Controller

            tc = Controller.Create(f"TC{nummer}", toolNumber=nummer)
            job.Proxy.addToolController(tc)
            op.ToolController = tc
    doc.recompute()
    return doc, job


def namen(maschine, stellungen):
    return {vf.namen(maschine, a): round(s, 6) for a, s in stellungen.items()}


# --- 3-Achs-Fräse: Zeiten gegen Handrechnung ---------------------------------------------
asm, ma = beispielmaschine.fraesmaschine()
p = rw.Pruefung(asm, ma)
bahn = [
    "G0 X0 Y0 Z10",
    "G1 Z-5 F10",  # 15 mm mit 10 mm/s: 1,5 s
    "G1 X100",  # 100 mm: 10 s
    "G2 X120 Y20 I0 J20",  # 270° um (100, 20), r 20: 54 Sehnen zu 5°
    "G0 Z10",  # Z1 15 mm im Eilgang 15 000 mm/min: 0,06 s
    "G81 X50 Y30 Z-8 R3 F5",  # hin (X1 70 mm: 0,21 s), auf R (0,028 s), 11 mm mit 5 mm/s, zurück
    "G80",
]
teil, job = neuer_job([(bahn, 1)])
fahrt = ab.abfahrt(p, job, FreeCAD.Vector())
namen_achsen = [vf.namen(ma, a) for a in fahrt.achsen]
pruefe(namen_achsen == ["Y1", "Z1", "X1"], f"Achsen: {namen_achsen}")
st = fahrt.stationen
pruefe(len(st) == 1 + 1 + 1 + 53 + 1 + 1 + 4, f"Stationen: {len(st)}")
pruefe(nahe(st[1].zeit, 1.5) and nahe(st[2].zeit, 11.5), f"Geraden: {st[1].zeit}, {st[2].zeit}")
sehne = 2 * 20 * math.sin(math.radians(2.5))
ende_kreis = 11.5 + 54 * sehne / 10
pruefe(nahe(st[56].zeit, ende_kreis), f"Kreis: {st[56].zeit} statt {ende_kreis}")
# Satz 6: FreeCAD stellt der Operation „Eigene“ zwei Kommentare voran.
pruefe(st[56].satz == 6 and st[30].satz == 6 and not st[30].eilgang, "Kreis: Satz 6, Vorschub")
pruefe(nahe(st[57].zeit - st[56].zeit, 15 / 250), f"Eilgang Z: {st[57].zeit - st[56].zeit}")
bohren = [round(st[i].zeit - st[i - 1].zeit, 6) for i in range(58, 62)]
pruefe(
    bohren == [round(70 / (20000 / 60), 6), round(7 / 250, 6), 2.2, round(18 / 250, 6)],
    f"Bohrzyklus: {bohren}",
)
pruefe([s.eilgang for s in st[58:62]] == [True, True, False, True], "Bohrzyklus: Eilgang")
pruefe(st[61].punkt == (50, 30, 10), f"Rückzug auf die Ausgangshöhe: {st[61].punkt}")
gesamt = ende_kreis + 15 / 250 + 70 / (20000 / 60) + 7 / 250 + 2.2 + 18 / 250
pruefe(nahe(fahrt.dauer, gesamt), f"Dauer: {fahrt.dauer} statt {gesamt}")
pruefe(fahrt.hinweise == [], f"Hinweise: {fahrt.hinweise}")
op = fahrt.operationen[0]
pruefe(
    op.name == "Op1" and op.erste == 0 and op.saetze == len(job.Operations.Group[0].Path.Commands),
    "",
)

# Dazwischen geradlinig: Mitten auf der Geraden X 0 → 100 steht X1 auf −50.
mitte = namen(ma, fahrt.stellungen_bei(1.5 + 5.0))
pruefe(mitte == {"X1": -50, "Y1": 0, "Z1": -85}, f"Mitte der Geraden: {mitte}")
pruefe(fahrt.index_bei(0) == 0 and fahrt.index_bei(1.5) == 1, "index_bei")
pruefe(fahrt.index_bei(-1) == 0 and fahrt.index_bei(1e9) == len(st) - 1, "index_bei außerhalb")
anfang = namen(ma, fahrt.stellungen_bei(0))
pruefe(anfang == {"X1": 0, "Y1": 0, "Z1": -70}, f"Anfang: {anfang}")
# Jede Station trifft: dieselben Stellungen wie die Reichweite für ihren Punkt.
spindel = p.werkzeugaufnahme(1)
for i in (0, 20, 57, 60):
    erwartet = namen(ma, p.stellungen(st[i].punkt, spindel, 50, FreeCAD.Vector()))
    pruefe(namen(ma, fahrt.stellungen_bei(st[i].zeit)) == erwartet, f"Station {i}")
    pruefe(namen(ma, fahrt.stellungen_an(i)) == erwartet, f"stellungen_an({i})")

# Ohne F: 1000 mm/min, mit Hinweis.
op2 = job.Operations.Group[0]
op2.Gcode = ["G0 X0 Y0 Z10", "G1 Z0"]
teil.recompute()
fahrt = ab.abfahrt(p, job, FreeCAD.Vector())
pruefe(nahe(fahrt.dauer, 10 / (1000 / 60)), f"ohne F: {fahrt.dauer}")
pruefe(
    fahrt.hinweise
    == [
        "„Op1“ hat keinen Vorschub – abgefahren mit 1000 mm/min. Den Vorschub setzt der "
        "Werkzeug-Controller (oder „Schnittwerte in den Job“)."
    ],
    f"Hinweis ohne F: {fahrt.hinweise}",
)

# Die Umkehrstellen eines Kreises sind Stationen, auch abseits der 5°-Schritte: Jede
# Überschreitung der Reichweite liegt genau auf einer Station (dorthin springt ein Klick
# im Fenster). Vollkreis um (−240, 3) mit r = √109 ≈ 10,44: ganz links X −250,44, also
# X1 250,44 – über der Grenze 250.
op2.Gcode = ["G0 X-230 Y0 Z10", "G2 X-230 Y0 I-10 J3 F10"]
teil.recompute()
fahrt = ab.abfahrt(p, job, FreeCAD.Vector())
pruefe(len(fahrt.stationen) == 1 + 71 + 4 + 1, f"Vollkreis, Stationen: {len(fahrt.stationen)}")
ueber = p.pruefe_job(job, FreeCAD.Vector()).ueberschreitungen
pruefe([u.name for u in ueber] == ["X1"], f"Vollkreis, Überschreitungen: {ueber}")
index = fahrt.station_von(ueber[0]) if ueber else None
pruefe(
    index is not None and nahe(fahrt.stationen[index].punkt[0], -240 - math.sqrt(109)),
    f"Station der Überschreitung: {index}",
)
anschlag = fahrt.stellungen_bei(fahrt.stationen[index].zeit) if index is not None else {}
x1 = next(a for a in fahrt.achsen if vf.namen(ma, a) == "X1")
pruefe(nahe(anschlag.get(x1), 240 + math.sqrt(109)), f"X1 dort: {anschlag.get(x1)}")
# So fährt der Abspieler: alle Achsen auf einmal, jede höchstens bis zu ihrer Grenze –
# zurück kommen die, die an einer Grenze halten.
y1 = next(a for a in fahrt.achsen if vf.namen(ma, a) == "Y1")
angehalten = p.verfahren.setze_alle(anschlag)
pruefe(angehalten == [x1], f"setze_alle, angehalten: {angehalten}")
pruefe(
    nahe(p.verfahren.stellung(x1), 250) and nahe(p.verfahren.stellung(y1), anschlag[y1]),
    f"setze_alle: X1 {p.verfahren.stellung(x1)}, Y1 {p.verfahren.stellung(y1)}",
)
p.verfahren.grundstellung()
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)

# --- Rundachse im Vorschub: Grad durch F ---------------------------------------------------
asm, ma = beispielmaschine.fuenfachs_tisch_tisch()
p = rw.Pruefung(asm, ma)
teil, job = neuer_job([(["G0 X0 Y0 Z50 A0", "G1 A90 F10"], 1)], "Schwenkteil")
fahrt = ab.abfahrt(p, job, FreeCAD.Vector())
pruefe(len(fahrt.stationen) == 1 + 90, f"A in 1°-Schritten: {len(fahrt.stationen)}")
pruefe(nahe(fahrt.dauer, 9.0), f"A 90° mit 10 °/s: {fahrt.dauer}")
halb = namen(ma, fahrt.stellungen_bei(4.5))
pruefe(nahe(halb["A1"], 45) and nahe(halb["C1"], 0), f"halb geschwenkt: {halb}")
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)

# --- Drehmaschine: der Revolver schwenkt zwischen zwei Werkzeugen --------------------------
asm, ma = beispielmaschine.drehmaschine()
p = rw.Pruefung(asm, ma)
teil, job = neuer_job([(["G0 X40 Y0 Z80"], 1), (["G0 X40 Y0 Z80"], 2)], "Drehteil")
fahrt = ab.abfahrt(p, job)
revolver = next(a for a in fahrt.achsen if vf.namen(ma, a) == "T")
plaetze = dict(vf.platzstellungen(p.verfahren, ma, revolver))
k = fahrt.achsen.index(revolver)
t = [s.stellungen[k] for s in fahrt.stationen]
pruefe(nahe(t[0], plaetze["P1"]) and nahe(t[1], plaetze["P2"]), f"Revolver: {t} statt {plaetze}")
pruefe([o.name for o in fahrt.operationen] == ["Op1", "Op2"], "zwei Operationen")
pruefe(fahrt.operationen[1].erste == 1 and fahrt.stationen[1].operation == 1, "zweite beginnt")
# Die Schaltzeit von T (0,25 s für 180°) bremst den Wechsel mindestens auf 30°/720°/s.
pruefe(fahrt.dauer >= 30 / 720 - 1e-9, f"Wechsel: {fahrt.dauer}")
# Auch im Vorschub: G1 auf denselben Punkt ist kein Weg, aber der Revolver schwenkt.
job.Operations.Group[1].Gcode = ["G1 X40 Y0 Z80 F10"]
teil.recompute()
fahrt = ab.abfahrt(p, job)
pruefe(
    fahrt.dauer >= 30 / 720 - 1e-9 and not fahrt.stationen[1].eilgang,
    f"Wechsel im Vorschub: {fahrt.dauer}",
)
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)

# --- Drehmaschine ohne Y: ein Punkt quer daneben lässt die Maschine stehen ------------------
asm, ma = beispielmaschinen.drehmaschine_komplett()
p = rw.Pruefung(asm, ma)
platz = p.werkzeugaufnahme(1)
achsen = {vf.namen(ma, a): a for a in p.kette.achsen}
# Ein erreichbarer Punkt: wo die Spitze steht, wenn X1 um 10 und Z1 um 20 fährt (C4 auf 0,
# wie ohne C in der Bahn) – und einer 5 mm quer zu X1 und Z1.
verfahren = vf.Verfahren(asm, p.kette)
verfahren.setze(achsen["X1"], verfahren.stellung(achsen["X1"]) + 10)
verfahren.setze(achsen["Z1"], verfahren.stellung(achsen["Z1"]) + 20)
verfahren.setze(achsen["C4"], 0.0, grenzen=False)
spitze = m.globale_platzierung(platz.Lcs).multVec(FreeCAD.Vector(0, 0, -30))
job_lage = m.globale_platzierung(p.werkstueckaufnahme.Lcs)
verfahren.grundstellung()
punkt = job_lage.inverse().multVec(spitze)
quer = job_lage.Rotation.inverted().multVec(achsen["X1"].richtung.cross(achsen["Z1"].richtung))
daneben = punkt + quer * 5
teil, job = neuer_job(
    [
        (
            [
                f"G0 X{punkt.x:.6f} Y{punkt.y:.6f} Z{punkt.z:.6f}",
                f"G1 X{daneben.x:.6f} Y{daneben.y:.6f} Z{daneben.z:.6f} F10",
            ],
            1,
        )
    ],
    "OhneY",
)
# Mit 30 mm Werkzeuglänge wie beim Messen oben – über die Werkzeugverwaltung (Ø 5 mm wie
# das CAM-Werkzeug, T1).
bibliothek = wz.Bibliothek([wz.Werkzeug(nummer=1, durchmesser=5.0, laenge_spindelnase=30.0)])
fahrt = ab.abfahrt(p, job, FreeCAD.Vector(), bibliothek)
pruefe(len(fahrt.stationen) == 2, f"ohne Y, Stationen: {len(fahrt.stationen)}")
pruefe(fahrt.stationen[0].stellungen is not None, "ohne Y: erster Punkt nicht erreichbar")
pruefe(fahrt.stationen[1].stellungen is None, "ohne Y: Punkt quer daneben erreichbar?")
pruefe(fahrt.wirksam(1) == fahrt.wirksam(0), "ohne Y: Maschine bleibt nicht stehen")
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
