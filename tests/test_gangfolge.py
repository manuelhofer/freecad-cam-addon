# Prüft die Folge der Schlichtgänge (gangfolge, leerfahrt; Manuel, 2026-11-14: „erstes vorschlichten
# ... und danach nochmal erstes vorschlichten .... dann messsen ... dann vertigschlichten ... und
# dann nochmal vertig schlichten ... dann hat man immer 100 % das richtige mass“).
# Eine Platte 80 × 80 × 10 mit einem Klotz 40 × 30 × 10 darauf, ringsum mit 0,3 geschruppt. Der
# Wandzug (Kontur, nur der Schlichtzug) mit dem halben Aufmaß 0,15; daraus die Folge: Leerfahrt,
# Messstopp, derselbe Schnitt auf Maß, Leerfahrt.
# Dann „Bohrung fräsen“ und die Nut, die in einem Gang schruppen und die Wand schlichten: ein Block
# 80 × 60 × 20 mit einer Bohrung Ø 30 (durch) und einer geschlossenen Nut 30 × 16, 8 tief, mit dem
# Ø 12. Helix und Ringe lassen 0,3; der Schlichtzug des ersten Schnitts 0,15, Leerfahrt (nur der
# Schlichtzug), Messstopp (Bohrung Ø 29,7), der Schlichtzug auf Maß (ohne Helix und Ringe),
# Leerfahrt – der Ø nach jedem Schnitt aus der Bahn nachgemessen. Die Nut misst der Taster an ihrer
# Breite: 16 → 15,7 → gemessen 15,7 → 16, quer in Y.
import math
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part
import Path.Main.Job as PathJob
from Path.Tool.camassets import user_asset_store

from camaddon import bohrung as bo
from camaddon import gangfolge as gf
from camaddon import job_schnittwerte as js
from camaddon import kontur as ko
from camaddon import leerfahrt as lf
from camaddon import messen, sprache
from camaddon import messstopp as ms
from camaddon import nut as nu
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
V = FreeCAD.Vector
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
fraeser = wz.standardwerkzeug()
ue.uebergeben(wz.Bibliothek([fraeser]))
doc = FreeCAD.newDocument("Gangfolge")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = (
    Part.makeBox(80, 80, 10).fuse(Part.makeBox(40, 30, 10, V(20, 25, 10))).removeSplitter()
)
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
schruppen = next(e for e in fraeser.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
schlichten = next(e for e in fraeser.einsaetze(wz.ALLE) if e.art == wz.SCHLICHTEN)
tc_r = js.controller_ohne_transaktion(doc, job, fraeser, schruppen)
tc_s = js.controller_ohne_transaktion(doc, job, fraeser, schlichten)
form = job.Model.Group[0].Shape
waende = [
    f"Face{i + 1}"
    for i, f in enumerate(form.Faces)
    if isinstance(f.Surface, Part.Plane)
    and abs(f.normalAt(0.5, 0.5).z) < 1e-6
    and f.BoundBox.ZMin > 9.9
]
pruefe(len(waende) == 4, f"Wände: {waende}")


def fahrten(op):
    return [(b.Name, sorted(b.Parameters.items())) for b in op.Path.Commands if b.Name in lf.FAHREN]


def naechste_wand(op):
    """Der kleinste Abstand der Fräsermitte zum Klotz (x 20 … 60, y 25 … 55) auf der Endtiefe."""
    beste = 1e9
    for b in op.Path.Commands:
        p = b.Parameters
        if b.Name in ("G1", "G01", "G2", "G02", "G3", "G03") and "X" in p and "Y" in p:
            dx = max(20.0 - p["X"], 0.0, p["X"] - 60.0)
            dy = max(25.0 - p["Y"], 0.0, p["Y"] - 55.0)
            beste = min(beste, (dx * dx + dy * dy) ** 0.5)
    return beste


# Schruppen ringsum mit 0,3, dann der erste Schlichtschnitt: nur der Zug an der Wand, 0,15 bleiben.
grob = ko.lege_an(job, tc_r, 10.0, schruppen.ae, aufmass=0.3, schlichten=False, flaechen=waende)
doc.recompute()
halb = gf.halbes_aufmass(0.3)
pruefe(abs(halb - 0.15) < 1e-9, f"halbes Aufmaß {halb}")
pruefe(
    abs(gf.halbes_aufmass(0.5, 0.1) - 0.3) < 1e-9,
    f"halb zwischen 0,5 und 0,1: {gf.halbes_aufmass(0.5, 0.1)}",
)
# Wie „Schlichten danach“: Breite = Aufmaß des Schruppens (nur der Zug an der Wand), dazu der Rest.
vor = ko.lege_an(job, tc_s, 10.0, 0.3, 0.3, True, 0.3, flaechen=waende, rest=halb)
doc.recompute()
pruefe(len(fahrten(vor)) > 4, f"erster Schnitt: {len(fahrten(vor))} Sätze")
pruefe(
    abs(naechste_wand(vor) - (6.0 + halb)) < 0.01, f"erster Schnitt bei {naechste_wand(vor):.3f}"
)

stopps = []


def stopp_anlegen(davor, danach):
    stopps.append((davor.Label, danach.Label))
    return ms.lege_an(job, davor.ToolController, danach.ToolController)


folge = gf.folge(job, [vor], aufmass_ende=0.0, leerfahrt=True, stopp_anlegen=stopp_anlegen)
doc.recompute()
reihe = list(job.Operations.Group)
namen_ = [o.Label for o in reihe]
print("Folge:", namen_)
pruefe(
    len(folge.leer_vor) == 1 and len(folge.fertig) == 1 and len(folge.leer_fertig) == 1,
    f"Folge: {namen_}",
)
erwartet = [grob, vor, folge.leer_vor[0], folge.stopp, folge.fertig[0], folge.leer_fertig[0]]
pruefe([o.Name for o in reihe] == [o.Name for o in erwartet], f"Reihenfolge: {namen_}")
pruefe(folge.stopp is not None and ms.ist_messstopp(folge.stopp), "kein Messstopp dazwischen")
pruefe(stopps == [(folge.leer_vor[0].Label, vor.Label)], f"Messstopp nach der Leerfahrt: {stopps}")
# Die Leerfahrt: derselbe Schnitt, Satz für Satz, mit demselben Werkzeug.
leer = folge.leer_vor[0]
pruefe(lf.ist_leerfahrt(leer) and not lf.ist_leerfahrt(vor), "ist_leerfahrt")
pruefe(fahrten(leer) == fahrten(vor), "Leerfahrt fährt nicht denselben Schnitt")
pruefe(leer.ToolController.Name == vor.ToolController.Name, "Leerfahrt mit anderem Werkzeug")
pruefe(abs(float(leer.Aufmass) - halb) < 1e-9, f"Leerfahrt: Aufmaß {float(leer.Aufmass)}")
pruefe("Leerfahrt" in leer.Label and vor.Label in leer.Label, f"Name: {leer.Label}")
# Der zweite Schnitt: derselbe Zug, 0,15 näher an der Wand – sonst alles gleich.
fertig = folge.fertig[0]
pruefe(
    abs(float(fertig.Schlichtrest)) < 1e-9, f"zweiter Schnitt: Rest {float(fertig.Schlichtrest)}"
)
pruefe(abs(float(fertig.Aufmass) - 0.3) < 1e-9, f"zweiter Schnitt: Aufmass {float(fertig.Aufmass)}")
pruefe(len(fahrten(fertig)) == len(fahrten(vor)), "zweiter Schnitt: andere Zahl Sätze")
pruefe(abs(naechste_wand(fertig) - 6.0) < 0.01, f"zweiter Schnitt bei {naechste_wand(fertig):.3f}")
pruefe(fertig.ToolController.Name == vor.ToolController.Name, "zweiter Schnitt: anderes Werkzeug")
for feld in ("Zustellung", "FinalDepth", "StartDepth"):
    if feld in vor.PropertiesList:
        pruefe(
            abs(float(getattr(vor, feld)) - float(getattr(fertig, feld))) < 1e-9,
            f"zweiter Schnitt: {feld} {getattr(fertig, feld)} statt {getattr(vor, feld)}",
        )
pruefe("auf Maß" in fertig.Label, f"Name: {fertig.Label}")
pruefe(fahrten(folge.leer_fertig[0]) == fahrten(fertig), "Leerfahrt des zweiten Schnitts")
print(f"erster Schnitt {naechste_wand(vor):.3f}, zweiter {naechste_wand(fertig):.3f} mm vor der Wand; "
      f"je {len(fahrten(vor))} / {len(fahrten(fertig))} Sätze")  # fmt: skip

# Ändert sich der Schnitt, fährt die Leerfahrt den neuen (die Verknüpfung rechnet sie mit).
vor.Schlichtrest = 0.2
doc.recompute()
pruefe(
    abs(naechste_wand(leer) - 6.2) < 0.01, f"Leerfahrt nach der Änderung: {naechste_wand(leer):.3f}"
)
pruefe(
    abs(float(leer.Aufmass) - 0.2) < 1e-9, f"Leerfahrt: Aufmaß {float(leer.Aufmass)} nach Änderung"
)
vor.Schlichtrest = halb
doc.recompute()

# Ohne zwei Schnitte: nur die Leerfahrt. Ohne alles: nichts.
nur = gf.folge(job, [fertig], leerfahrt=True)
pruefe(len(nur.alle) == 1 and lf.ist_leerfahrt(nur.alle[0]), f"nur Leerfahrt: {nur.alle}")
pruefe(not gf.folge(job, [fertig]).alle, "ohne Wahl kommt etwas dazu")
# Schon auf Maß: kein zweiter Schnitt, kein Messstopp.
kein = gf.folge(job, [fertig], aufmass_ende=0.0, stopp_anlegen=stopp_anlegen)
pruefe(not kein.alle and len(stopps) == 1, f"schon auf Maß: {kein.alle}")
# Messstopps und Leerfahrten selbst bekommen keine Leerfahrt.
pruefe(gf.schnitte([folge.stopp, leer, vor]) == [vor], "schnitte()")

# Speichern und Laden: Die Leerfahrt kennt ihre Quelle und rechnet wieder.
datei = os.path.join(tempfile.mkdtemp(), "gangfolge.FCStd")
doc.recompute()
doc.saveAs(datei)
name_leer, name_vor = leer.Name, vor.Name
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(datei)
leer, vor = doc.getObject(name_leer), doc.getObject(name_vor)
pruefe(
    lf.ist_leerfahrt(leer) and leer.Quelle is not None and leer.Quelle.Name == name_vor, "geladen"
)
vor.touch()
doc.recompute()
pruefe(fahrten(leer) == fahrten(vor) and len(fahrten(leer)) > 4, "geladen: Leerfahrt rechnet nicht")
# Im Programm steht der Schnitt zweimal hintereinander.
from camaddon import postprozessor as pp

text = pp.programm(pp.abschnitte(doc.Job), pp.steuerung("siemens"), None, "GANGFOLGE").text
pruefe(text.count("M0") >= 1, "kein Halt im Programm")
print(f"Programm: {len(text.splitlines())} Zeilen")
FreeCAD.closeDocument(doc.Name)

# --- „Bohrung fräsen“ und die Nut: zwei gleiche Schnitte nur über den Schlichtzug -------------
doc = FreeCAD.newDocument("GangfolgeBohrung")
objekt = doc.addObject("Part::Feature", "Block")
MX, MY, D = 25.0, 30.0, 30.0  # die Bohrung
NUT_Y, NUT_B = 30.0, 16.0  # die Nut: Mittellinie, Breite (x 51 … 65 zwischen den Rundungen)
nut_form = (
    Part.makeBox(14, NUT_B, 8, V(51, NUT_Y - NUT_B / 2, 12))
    .fuse(Part.makeCylinder(NUT_B / 2, 8, V(51, NUT_Y, 12)))
    .fuse(Part.makeCylinder(NUT_B / 2, 8, V(65, NUT_Y, 12)))
)
objekt.Shape = (
    Part.makeBox(80, 60, 20)
    .cut(Part.makeCylinder(D / 2, 20, V(MX, MY, 0)))
    .cut(nut_form)
    .removeSplitter()
)
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
tc_r = js.controller_ohne_transaktion(doc, job, fraeser, schruppen)
form = job.Model.Group[0].Shape
bohrung_flaeche = next(
    f"Face{i + 1}"
    for i, f in enumerate(form.Faces)
    if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - D / 2) < 1e-6
)
nut_grund = next(
    f"Face{i + 1}"
    for i, f in enumerate(form.Faces)
    if isinstance(f.Surface, Part.Plane) and abs(f.BoundBox.ZMax - 12.0) < 1e-6
    and abs(f.BoundBox.ZMin - 12.0) < 1e-6
)  # fmt: skip


def bogen_punkte(op):
    """[(Abstand von der Achse der Bohrung, z, ändert sich z)] je G2/G3 in der Bohrung."""
    ergebnis, z = [], None
    for b in op.Path.Commands:
        p = b.Parameters
        neu_z = p.get("Z", z)
        if b.Name in ("G2", "G02", "G3", "G03"):
            a = math.hypot(p["X"] - MX, p["Y"] - MY)
            if a < D / 2:
                ergebnis.append((a, neu_z, z is not None and abs(neu_z - z) > 1e-6))
        z = neu_z
    return ergebnis


def durchmesser(op):
    """Der Ø, den die Bahn in der Bohrung fräst: der weiteste Bogen und der Fräser."""
    punkte = bogen_punkte(op)
    return 2.0 * (max(a for a, _z, _dz in punkte) + fraeser.durchmesser / 2) if punkte else 0.0


def nut_breite(op):
    """Die Breite, die die Bahn in der Nut fräst: die weiteste Stelle quer zur Mittellinie."""
    quer = [
        abs(b.Parameters["Y"] - NUT_Y)
        for b in op.Path.Commands
        if b.Name in lf.FAHREN[2:] and "Y" in b.Parameters and b.Parameters.get("X", 0.0) > 45.0
    ]
    return 2.0 * (max(quer) + fraeser.durchmesser / 2) if quer else 0.0


def vorschubweg(op):
    """mm im Vorschub (G1, G2, G3 – die Bögen mit ihrem Winkel um I, J)."""
    weg, alt = 0.0, None
    for b in op.Path.Commands:
        p = b.Parameters
        if not {"X", "Y", "Z"} & set(p):
            continue
        neu = {k: p.get(k, (alt or {}).get(k, 0.0)) for k in ("X", "Y", "Z")}
        if alt is not None and b.Name in ("G2", "G02", "G3", "G03"):
            mx, my = alt["X"] + p.get("I", 0.0), alt["Y"] + p.get("J", 0.0)
            a0 = math.atan2(alt["Y"] - my, alt["X"] - mx)
            a1 = math.atan2(neu["Y"] - my, neu["X"] - mx)
            w = (a1 - a0) if b.Name in ("G3", "G03") else (a0 - a1)
            w = w % (2 * math.pi) or 2 * math.pi
            r_ = math.hypot(alt["X"] - mx, alt["Y"] - my)
            weg += math.hypot(r_ * w, neu["Z"] - alt["Z"])
        elif alt is not None and b.Name in ("G1", "G01"):
            weg += math.dist([neu[k] for k in "XYZ"], [alt[k] for k in "XYZ"])
        alt = neu
    return weg


def tiefster_eilgang(op):
    eilgaenge = [
        b.Parameters["Z"]
        for b in op.Path.Commands
        if b.Name in ("G0", "G00") and "Z" in b.Parameters
    ]
    return min(eilgaenge, default=math.inf)


bohrung = bo.lege_an(job, tc_r, 2.0, 1.5, aufmass=0.3, flaechen=[bohrung_flaeche])
nut_op = nu.lege_an(job, tc_r, 4.0, 1.5, aufmass=0.3, schlichten=True, flaechen=[nut_grund])
doc.recompute()
# Ohne die neuen Haken wie bisher: der Schlichtzug auf Maß, gang_feld ist sein Schlichtrest (0).
pruefe(float(bohrung.Schlichtrest) == 0.0 and not bohrung.NurSchlichten, "Vorgaben der Bohrung")
pruefe(lf.gang_feld(bohrung) == "Schlichtrest", f"gang_feld Bohrung: {lf.gang_feld(bohrung)}")
pruefe(lf.gang_feld(nut_op) == "Schlichtrest", f"gang_feld Nut: {lf.gang_feld(nut_op)}")
pruefe(abs(durchmesser(bohrung) - D) < 0.01, f"Bohrung ohne Folge: Ø {durchmesser(bohrung):.3f}")
pruefe(abs(nut_breite(nut_op) - NUT_B) < 0.01, f"Nut ohne Folge: {nut_breite(nut_op):.3f} breit")
weg_ganz, weg_nut_ganz = vorschubweg(bohrung), vorschubweg(nut_op)
stopps.clear()
merkmale = []


def stopp_bohrung(davor, danach):
    stopps.append((davor.Label, danach.Label))
    merkmale.append(gf.messmerkmal(form, [bohrung_flaeche], davor))
    return ms.lege_an(job, davor.ToolController, danach.ToolController, merkmale[-1])


folge = gf.folge(job, [bohrung, nut_op], 0.0, leerfahrt=True, stopp_anlegen=stopp_bohrung)
doc.recompute()
namen_ = [o.Label for o in job.Operations.Group]
print("Folge Bohrung/Nut:", namen_)
pruefe(
    len(folge.leer_vor) == 2 and len(folge.fertig) == 2 and len(folge.leer_fertig) == 2,
    f"Folge: {namen_}",
)
pruefe(abs(float(bohrung.Schlichtrest) - 0.15) < 1e-9, f"erster: Rest {bohrung.Schlichtrest}")
pruefe(abs(float(nut_op.Schlichtrest) - 0.15) < 1e-9, f"Nut erster: Rest {nut_op.Schlichtrest}")
if len(folge.fertig) == 2 and len(folge.leer_vor) == 2 and len(folge.leer_fertig) == 2:
    leer_b, leer_n = folge.leer_vor
    fertig_b, fertig_n = folge.fertig
    leer2_b, leer2_n = folge.leer_fertig
    d_ = [durchmesser(o) for o in (bohrung, leer_b, fertig_b, leer2_b)]
    print(f"Bohrung Ø nach jedem Schnitt: {d_[0]:.3f} → Leerfahrt {d_[1]:.3f} → Messstopp → "
          f"{d_[2]:.3f} → Leerfahrt {d_[3]:.3f}")  # fmt: skip
    pruefe(abs(d_[0] - (D - 0.3)) < 0.01, f"erster Schnitt: Ø {d_[0]:.3f}")
    pruefe(abs(d_[1] - (D - 0.3)) < 0.01, f"Leerfahrt: Ø {d_[1]:.3f}")
    pruefe(abs(d_[2] - D) < 0.01, f"zweiter Schnitt: Ø {d_[2]:.3f}")
    pruefe(abs(d_[3] - D) < 0.01, f"Leerfahrt des zweiten: Ø {d_[3]:.3f}")
    pruefe(fertig_b.NurSchlichten and abs(float(fertig_b.Schlichtrest)) < 1e-9, "zweiter: Werte")
    pruefe(abs(float(fertig_b.Aufmass) - 0.3) < 1e-9, f"zweiter: Aufmass {fertig_b.Aufmass}")
    pruefe(abs(float(leer_b.Aufmass) - 0.15) < 1e-9, f"Leerfahrt: Aufmass {leer_b.Aufmass}")
    # Nur der Schlichtzug: keine Helix (G2/G3 mit z), keine Ringe – nur Bögen an der Wand oder in
    # die Mitte (dort enden die Halbkreise hinein und heraus).
    r_f = D / 2 - fraeser.durchmesser / 2
    for name, op, rest in (
        ("Leerfahrt", leer_b, 0.15), ("zweiter", fertig_b, 0.0), ("Leerfahrt 2", leer2_b, 0.0),
    ):  # fmt: skip
        punkte = bogen_punkte(op)
        pruefe(punkte and not any(dz for _a, _z, dz in punkte), f"{name}: Helix in {punkte[:4]}")
        ringe = [a for a, _z, _dz in punkte if a > 0.01 and abs(a - (r_f - rest)) > 0.01]
        pruefe(not ringe, f"{name}: Ringe bei {ringe[:4]}")
    weg_zug = vorschubweg(fertig_b)
    print(f"Vorschub: ganze Bohrung {weg_ganz:.0f} mm, zweiter Schnitt {weg_zug:.0f} mm, "
          f"Leerfahrt {vorschubweg(leer_b):.0f} mm; im Eilgang hinab bis z "
          f"{tiefster_eilgang(fertig_b):.2f} / {tiefster_eilgang(leer_b):.2f}")  # fmt: skip
    pruefe(weg_zug < 0.5 * weg_ganz, f"zweiter Schnitt {weg_zug:.0f} von {weg_ganz:.0f} mm")
    # Die Leerfahrt fährt den Schlichtzug 0,15 weiter innen: 2 mm kürzer (gemessen 85 / 87 mm).
    pruefe(
        weg_zug - 5.0 < vorschubweg(leer_b) <= weg_zug,
        f"Leerfahrt {vorschubweg(leer_b):.0f} statt Schlichtzug {weg_zug:.0f} mm",
    )
    # Im geräumten Kern im Eilgang hinab (der Materialstand sieht ihn frei), nicht im Vorschub.
    pruefe(tiefster_eilgang(fertig_b) < 5.0, f"zweiter: Eilgang bis {tiefster_eilgang(fertig_b)}")
    pruefe(tiefster_eilgang(leer_b) < 5.0, f"Leerfahrt: Eilgang bis {tiefster_eilgang(leer_b)}")
    # Der Messstopp misst die Bohrung am Ø nach dem ersten Schnitt (nach ihrer Leerfahrt). Hier
    # steht er hinter der Leerfahrt der Nut, die zuletzt schnitt: Seit 0.381 misst er dort die Nut
    # (15,7) – bis 0.380 kannte er keine und nahm die Bohrung aus den Flächen des Jobs.
    m_b = gf.messmerkmal(form, [bohrung_flaeche], leer_b)
    pruefe(
        m_b is not None and m_b.art == messen.BOHRUNG and abs(m_b.durchmesser - (D - 0.3)) < 1e-6,
        f"Messmerkmal Bohrung: {m_b}",
    )
    m_ = merkmale[0] if merkmale else None
    pruefe(
        m_ is not None and m_.art == messen.NUT and abs(m_.breite - (NUT_B - 0.3)) < 1e-6,
        f"Messmerkmal hinter der Nut: {m_}",
    )
    pruefe(len(stopps) == 1 and stopps[0][0] == leer_n.Label, f"Messstopp: {stopps}")
    # Die Nut ebenso: erst 0,15, dann auf Maß; die Leerfahrt und der zweite nur der Schlichtgang.
    b_ = [nut_breite(o) for o in (nut_op, leer_n, fertig_n, leer2_n)]
    w_ = [vorschubweg(o) for o in (nut_op, leer_n, fertig_n, leer2_n)]
    print(f"Nut breit nach jedem Schnitt: {' → '.join(f'{b:.3f}' for b in b_)}; "
          f"Vorschub {' / '.join(f'{w:.0f}' for w in w_)} mm")  # fmt: skip
    pruefe(abs(b_[0] - (NUT_B - 0.3)) < 0.01, f"Nut erster: {b_[0]:.3f}")
    pruefe(abs(b_[1] - (NUT_B - 0.3)) < 0.01, f"Nut Leerfahrt: {b_[1]:.3f}")
    pruefe(abs(b_[2] - NUT_B) < 0.01 and abs(b_[3] - NUT_B) < 0.01, f"Nut zweiter: {b_[2:]}")
    pruefe(fertig_n.NurSchlichten, "Nut zweiter: nicht nur der Schlichtgang")
    pruefe(max(w_[1:]) < 0.5 * w_[0], f"Nut: Leerfahrt/zweiter so lang wie die ganze: {w_}")
    # Nach allem ist die Bohrung im Materialstand auf Maß – in ihr steht nichts mehr.
    from camaddon import materialstand as mst

    rest_h = mst.fuer(job).hoechste_bei(MX, MY, D / 2 - 0.4)
    pruefe(rest_h < 0.5, f"in der Bohrung steht noch Material bis z {rest_h:.2f}")
    # Die Leerfahrten der Nut gehen in der eben geräumten Nut im Eilgang bis knapp über den Zug
    # (z 12), nicht im Vorschub von der Oberkante z 20 (Gegenprüfung 2026-11-14: 8 mm Luft).
    for name, op in (("Nut Leerfahrt", leer_n), ("Nut Leerfahrt 2", leer2_n)):
        pruefe(tiefster_eilgang(op) < 15.0, f"{name}: Eilgang nur bis z {tiefster_eilgang(op)}")
    # Ein Messstopp „davor“ misst nicht nach „Bohrung fräsen“ und ihrer Leerfahrt (die misst man
    # zwischen ihren zwei Schnitten) und nicht nach einem Messstopp – er misst nach dem, was die
    # Wände zuletzt geschnitten hat.
    pruefe(gf.davor_messen([nut_op, bohrung, leer_b]) is nut_op, "davor_messen: nach der Bohrung")
    pruefe(gf.davor_messen([bohrung, leer_b]) is None, "davor_messen: nur die Bohrung")
    pruefe(gf.davor_messen([nut_op, folge.stopp]) is nut_op, "davor_messen: nach einem Messstopp")
    pruefe(gf.ist_bohrungsgang(leer_b) and not gf.ist_bohrungsgang(leer_n), "ist_bohrungsgang")
    # Gemessen wird die Nut an ihrer Breite (messen.NUT, seit 0.381): 16 → 15,7 nach dem ersten
    # Schnitt und seiner Leerfahrt → gemessen 15,7 → 16 nach dem zweiten. Quer zur Mittellinie
    # (sie läuft in X): in Y, in der Mitte (58, 30), auf halber Wand z 16 – auch wenn am Job
    # noch die Bohrung gemerkt ist (die Nut misst an ihren eigenen Flächen).
    breiten = []
    for op in (nut_op, leer_n, fertig_n, leer2_n):
        m_n = gf.messmerkmal(form, [bohrung_flaeche, nut_grund], op)
        breiten.append(None if m_n is None else round(m_n.breite, 3))
        pruefe(
            m_n is not None
            and m_n.art == messen.NUT
            and m_n.achse == "Y"
            and abs(m_n.x - 58.0) < 1e-6
            and abs(m_n.y - NUT_Y) < 1e-6
            and abs(m_n.z_mess - 16.0) < 1e-6,
            f"Nut-Messmerkmal nach {op.Label}: {m_n}",
        )
    print(f"Nut gemessen nach jedem Schnitt: {breiten}")
    pruefe(breiten == [15.7, 15.7, 16.0, 16.0], f"Nut gemessen: {breiten}")
    # Der Messstopp zwischen den Schnitten der Nut allein (gangfolge.folge): misst 15,7.
    nut_allein = nu.lege_an(job, tc_r, 4.0, 1.5, aufmass=0.3, schlichten=True, flaechen=[nut_grund])
    doc.recompute()
    gemerkt = []

    def stopp_nut(davor, danach):
        gemerkt.append(gf.messmerkmal(form, [nut_grund], davor))
        return ms.lege_an(job, davor.ToolController, danach.ToolController, gemerkt[-1])

    folge_n = gf.folge(job, [nut_allein], 0.0, leerfahrt=True, stopp_anlegen=stopp_nut)
    zeile_n = ms.merkmal_von(list(folge_n.stopp.Gcode)) if folge_n.stopp is not None else None
    print(f"Messstopp der Nut: {zeile_n}")
    pruefe(
        zeile_n is not None
        and zeile_n[0].art == messen.NUT
        and abs(zeile_n[0].breite - 15.7) < 1e-6
        and zeile_n[0].achse == "Y",
        f"Messstopp der Nut: {zeile_n}",
    )

    # Nach „Schlichten danach“ (eine Kontur an den Wänden der Nut, Rest 0,15) misst er die Nut
    # über die am Job gemerkten Flächen – ihren Grund (bis 0.380: kein Merkmal, Halt ohne Soll).
    class KonturZug:
        PropertiesList = ["Aufmass", "Schlichten", "Schlichtrest"]
        Aufmass, Schlichten, Schlichtrest = 0.3, True, 0.15
        ToolController = tc_r

    m_k = gf.messmerkmal(form, [nut_grund], KonturZug())
    pruefe(
        m_k is not None and m_k.art == messen.NUT and abs(m_k.breite - 15.7) < 1e-6,
        f"nach der Kontur: {m_k}",
    )

# „Bohrung fräsen“ ohne Schlichtzug: Die Helix fräst auf Maß – es bleibt 0 an der Wand, gemessen
# wird Ø 30 (bis 0.379: Ø 29,4 aus ihrem Aufmaß 0,3), und zwei Schnitte gibt es dort nicht (die
# ganze Helix noch einmal ginge durch die Luft).
ohne = bo.lege_an(job, tc_r, 2.0, 1.5, aufmass=0.3, schlichten=False, flaechen=[bohrung_flaeche])
pruefe(lf.gang_feld(ohne) is None, f"ohne Schlichtzug: gang_feld {lf.gang_feld(ohne)}")
pruefe(lf.gang_aufmass(ohne) == 0.0, f"ohne Schlichtzug: gang_aufmass {lf.gang_aufmass(ohne)}")
pruefe(gf.wand_rest(ohne) == 0.0, f"ohne Schlichtzug: wand_rest {gf.wand_rest(ohne)}")
m_ohne = gf.messmerkmal(form, [bohrung_flaeche], ohne)
pruefe(m_ohne is not None and abs(m_ohne.durchmesser - D) < 1e-6, f"ohne Schlichtzug: {m_ohne}")
stopps.clear()
keine = gf.folge(job, [ohne], 0.0, stopp_anlegen=stopp_bohrung)
pruefe(not keine.alle and not stopps, f"ohne Schlichtzug: Folge {[o.Label for o in keine.alle]}")
pruefe(not gf.teilen(ohne, 0.0), "ohne Schlichtzug geteilt")
print(f"Bohrung ohne Schlichtzug: Soll {m_ohne}")
FreeCAD.closeDocument(doc.Name)

# Offene Nut, hinter deren Ende noch Rohteil steht (10 mm): Die Nut geht dort wie geschlossen
# hinein – ihre Leerfahrt auch, nicht draußen im Eilgang ins Rohteil (ohne den Materialstand
# G0 bis z 14 bei x 87, nachgestellt 2026-11-14).
doc = FreeCAD.newDocument("GangfolgeNutOffen")
objekt = doc.addObject("Part::Feature", "Block")
offen_form = Part.makeBox(40, 16, 8, V(51, 22, 12)).fuse(Part.makeCylinder(8, 8, V(51, 30, 12)))
objekt.Shape = Part.makeBox(80, 60, 20).cut(offen_form).removeSplitter()
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
job.Stock.ExtXpos = 10.0
doc.recompute()
tc_r = js.controller_ohne_transaktion(doc, job, fraeser, schruppen)
form = job.Model.Group[0].Shape
grund = next(
    f"Face{i + 1}"
    for i, f in enumerate(form.Faces)
    if isinstance(f.Surface, Part.Plane) and abs(f.BoundBox.ZMax - 12.0) < 1e-6
    and abs(f.BoundBox.ZMin - 12.0) < 1e-6
)  # fmt: skip
offen = nu.lege_an(job, tc_r, 4.0, 1.5, aufmass=0.3, schlichten=True, flaechen=[grund])
doc.recompute()
leer_offen = lf.lege_an(job, offen)
doc.recompute()


def eilgang_im_rohteil(op):
    """Eilgänge, bei denen der Fräser rechts vom Teil (dort steht Rohteil bis x 90) unter z 20
    steht."""
    funde, x, y, z = [], None, None, None
    for b in op.Path.Commands:
        p = b.Parameters
        x, y, z = p.get("X", x), p.get("Y", y), p.get("Z", z)
        drin = None not in (x, y, z) and x + fraeser.durchmesser / 2 > 80.0 and z < 20.0 - 1e-6
        if b.Name in ("G0", "G00") and drin:
            funde.append((round(x, 2), round(y, 2), round(z, 2)))
    return funde


pruefe(len(fahrten(leer_offen)) > 4, f"offene Nut: Leerfahrt {len(fahrten(leer_offen))} Sätze")
pruefe(not eilgang_im_rohteil(offen), f"offene Nut: Eilgang im Rohteil {eilgang_im_rohteil(offen)}")
pruefe(
    not eilgang_im_rohteil(leer_offen),
    f"offene Nut: Leerfahrt im Eilgang ins Rohteil {eilgang_im_rohteil(leer_offen)}",
)
FreeCAD.closeDocument(doc.Name)


# Frage 3 (b): die Folge der Bohrung direkt hinter „Bohrung fräsen“, vor Senken und Gewinde.
class _Op:
    def __init__(self, name):
        self.Name = name


_b, _s, _g, _l, _m, _z = (
    _Op(n) for n in ("Bohrung", "Senken", "Gewinde", "Leer", "Stopp", "Zweit")
)
_r = gf.direkt_dahinter([_b, _s, _g, _l, _m, _z], [_b], [_l, _m, _z])
pruefe([o.Name for o in _r] == ["Bohrung", "Leer", "Stopp", "Zweit", "Senken", "Gewinde"],
       f"direkt dahinter: {[o.Name for o in _r]}")  # fmt: skip
pruefe(gf.direkt_dahinter([_b, _s], [], [_l]) == [_b, _s], "ohne Quelle unverändert")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
