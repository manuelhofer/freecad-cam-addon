# Prüft die Kollision ohne Oberfläche (W-001, Stufe 4c; kollision.py) an der
# Beispiel-Fräse mit zwei Spanneisen und einem Teil 100 × 60 × 20 mit Tasche
# (x 30…70, y 15…45, Boden bei Z 5). Von Hand nachgerechnet:
# - frei in der Tasche: nichts;
# - Schneide 5 mm lang, Schaft so dick wie die Schneide, an der Taschenwand: der
#   Schaft berührt das Teil; mit Schaft Ø 4 bleibt 0,5 mm – eine Warnung;
# - Eilgang quer durchs Teil: Schneide und Schaft berühren es, „im Eilgang“;
# - Eilgang nach einem Vorschub: der Rückzug vom Taschenboden ist kein Befund, der Eilgang
#   hinunter auf den Boden schon;
# - Halter ER16 (Mutter Ø 28) bei 80 mm Länge ab Spindelnase, 1 mm zu tief neben
#   der Tasche: Der Halter berührt das Teil;
# - kurzes Werkzeug (25 mm) neben dem rechten Spanneisen (die Schraube 60 mm hoch, oben bei
#   Z 59): Die Spindel setzt bei Z 34 auf (Berührung), 4 mm darüber nur mit
#   Warnabstand 5 eine Warnung;
# - Paare, die sich in der Grundstellung berühren (Führungen), prüft es nicht,
#   ohne Hinweis, wenn sie an einem Gelenk hängen; Abbrechen geht;
# - die Schneide nach Art: beim Lollipop eine Kugel, der Hals ab ihrer Mitte; beim
#   Nutenfräser so hoch wie die Schneidenbreite (ein Scheibenfräser nur aus CAM: wie
#   das Blatt); sonst ein Drehkörper aus der Stirn (W-003 V5e) – Kugel-, Torus-, Konik-,
#   Fasen-, Radien- und Planfräser, der Kern überall 0,05 mm innen;
# - ein Kugelfräser Ø 5, über die Kante der Tasche gerollt (die Kugel berührt sie nur),
#   fährt nicht ins Teil – der Zylinder mit D stäke dort 0,5 mm darin; 0,5 mm tiefer schon;
# - ein Futter rund um die Achse bewegt sich beim Drehen nicht, eines mit Backen schon.
import math
import os
import sys
from types import SimpleNamespace

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import abfahren as ab
from camaddon import beispielmaschine, sprache
from camaddon import fraeserform as ff
from camaddon import halter as hl
from camaddon import kollision as kb
from camaddon import reichweite as rw
from camaddon import werkzeuge as wz

sprache.setze_sprache("de")
fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


asm, ma = beispielmaschine.fraesmaschine()
p = rw.Pruefung(asm, ma)

import Path.Main.Job as PathJob
import Path.Op.Custom as PathCustom

teil = FreeCAD.newDocument("Teil")
koerper = teil.addObject("Part::Feature", "Taschenteil")
koerper.Shape = Part.makeBox(100, 60, 20).cut(Part.makeBox(40, 30, 15, FreeCAD.Vector(30, 15, 5)))
teil.recompute()
job = PathJob.Create("Job", [koerper])
op = PathCustom.Create("Eigene")
teil.recompute()
nullpunkt = rw.vorschlag_nullpunkt(job)
pruefe(tuple(nullpunkt) == (-50, -30, 1), f"Nullpunkt: {nullpunkt}")


def pruefen(bahn, werkzeug, warnabstand=kb.WARNABSTAND, fortschritt=None, vorschlagen=False):
    """Die Bahn mit diesem Werkzeug (T1 in der Werkzeugverwaltung) abfahren und prüfen. Ohne
    `vorschlagen` das Werkzeug allein, wenn es keinen Halter hat (nicht im vorgeschlagenen)."""
    op.Gcode = bahn
    teil.recompute()
    bibliothek = wz.Bibliothek([werkzeug])
    bibliothek.halter_vorschlagen = vorschlagen
    if werkzeug.halter:
        halter = wz.Bibliothek().neuer_halter("er16")
        halter.kennung = werkzeug.halter
        bibliothek.halter.append(halter)
    fahrt = ab.abfahrt(p, job, nullpunkt, bibliothek)
    return kb.kollision(fahrt, job, nullpunkt, bibliothek, warnabstand, fortschritt)


def paare(ergebnis):
    return {(b.a, b.b, b.beruehrung, b.eilgang) for b in ergebnis.befunde}


def t1(**masse):
    """T1 wie das Werkzeug des Jobs (Ø 5): Schneide 5 mm, Gesamtlänge 50 mm – oder anders."""
    werte = {"nummer": 1, "durchmesser": 5.0, "schneidenlaenge": 5.0, "gesamtlaenge": 50.0}
    werte.update(masse)
    return wz.Werkzeug(**werte)


# --- Frei in der Tasche: nichts ------------------------------------------------------------
e = pruefen(["G0 X50 Y30 Z30", "G1 Z10 F10", "G0 Z30"], t1())
pruefe(e.befunde == [], f"frei: {[b.text() for b in e.befunde]}")
pruefe(
    e.hinweise
    == [
        "T1: ohne Halter geprüft – den Halter wählst du beim Werkzeug in der " "Werkzeugverwaltung."
    ],
    f"Hinweise: {e.hinweise}",
)
pruefe(e.stellen < 200, f"zu viele Stellen für drei Sätze: {e.stellen}")
# Ohne gewählten Halter prüft sie mit dem vorgeschlagenen (D-23): Schaft Ø 5 → ER16, das
# Werkzeug steht Auskragung 5 + 5 mm heraus – 10 mm über Z10 ist die Mutter noch frei.
e = pruefen(["G0 X50 Y30 Z30", "G1 Z10 F10", "G0 Z30"], t1(), vorschlagen=True)
pruefe(
    len(e.hinweise) == 1
    and e.hinweise[0].startswith("T1: mit dem vorgeschlagenen Halter")
    and "ER16" in e.hinweise[0],
    f"Hinweise mit Vorschlag: {e.hinweise}",
)
print(ascii(f"mit Vorschlag: {sorted(paare(e))}"))

# --- An der Taschenwand: der Schaft --------------------------------------------------------
e = pruefen(["G0 X50 Y30 Z30", "G1 Z8 F10", "G1 X67.5"], t1())
pruefe(paare(e) == {("der Schaft von T1", "das Teil", True, False)}, f"Wand: {paare(e)}")
if e.befunde:
    b = e.befunde[0]
    pruefe(b.satz == 5 and abs(b.punkt["X"] - 67.5) < 1e-6, f"Stelle: Satz {b.satz}, {b.punkt}")
    pruefe(
        b.text() == "In „Eigene“ berühren sich der Schaft von T1 und das Teil (Satz 5, bei "
        "X 67.5, Y 30, Z 8).",
        f"Satz: {b.text()!r}",
    )
    # Die Stelle in Koordinaten der Assembly: Der Tisch hat die Wand unter die Spindel
    # (x 400) gefahren – sie steht 2,5 mm rechts der Werkzeugachse.
    pruefe(b.stelle is not None and abs(b.stelle.x - 402.5) < 1e-6, f"Kontaktstelle: {b.stelle}")
e = pruefen(["G0 X50 Y30 Z30", "G1 Z8 F10", "G1 X67.5"], t1(schaft=4.0))
pruefe(paare(e) == {("der Schaft von T1", "das Teil", False, False)}, f"Schaft Ø4: {paare(e)}")
if e.befunde:
    pruefe(abs(e.befunde[0].abstand - 0.5) < 1e-6, f"Abstand: {e.befunde[0].abstand}")
    pruefe("kommen sich der Schaft von T1 und das Teil auf 0.50 mm nahe" in e.befunde[0].text(), "")

# --- Eilgang nach dem Vorschub: der Rückzug vom Boden ist keiner, der Weg hinunter schon ----
for bahn in (
    ["G0 X50 Y30 Z30", "G1 Z5 F10", "G0 Z30"],
    ["G0 X50 Y30 Z30", "G1 Z5.3 F10", "G0 Z30"],
):
    e = pruefen(bahn, t1())
    pruefe(e.befunde == [], f"Rückzug nach {bahn[1]}: {[b.text() for b in e.befunde]}")
e = pruefen(["G0 X50 Y30 Z30", "G1 Z10 F10", "G0 Z5"], t1())
pruefe(
    paare(e) == {("die Schneide von T1", "das Teil", True, True)},
    f"im Eilgang auf den Boden: {paare(e)}",
)

# --- Eilgang quer durchs Teil ---------------------------------------------------------------
# 80 mm lang: Die Spindel bleibt weit über den Spanneisen (mit 50 mm käme sie ihnen auf
# 1 mm nahe – das meldete die Prüfung zu Recht).
lang = t1(gesamtlaenge=80.0)
e = pruefen(["G0 X-20 Y30 Z10", "G0 X120"], lang)
pruefe(
    paare(e)
    == {
        ("die Schneide von T1", "das Teil", True, True),
        ("der Schaft von T1", "das Teil", True, True),
    },
    f"Eilgang: {paare(e)}",
)
if e.befunde:
    pruefe("berühren sich im Eilgang" in e.befunde[0].text(), f"{e.befunde[0].text()!r}")
    pruefe(abs(e.befunde[0].punkt["X"] + 2.5) < 0.6, f"erste Berührung bei X {e.befunde[0].punkt}")
# Derselbe Weg im Vorschub durchs volle Material des fertigen Teils: Die Schneide fährt ins
# Teil (Manuels Test, 2026-09-27 – bis dahin galt „im Vorschub schneidet sie“), der Schaft
# berührt.
e = pruefen(["G0 X-20 Y30 Z10", "G1 X120 F10"], lang)
pruefe(
    paare(e)
    == {
        ("die Schneide von T1", "das Teil", True, False),
        ("der Schaft von T1", "das Teil", True, False),
    },
    f"Vorschub: {paare(e)}",
)
ins_teil = [b for b in e.befunde if b.ins_teil]
pruefe(
    len(ins_teil) == 1
    and ins_teil[0].text().startswith("In „Eigene“ fährt die Schneide von T1 ins fertige Teil"),
    f"ins fertige Teil: {[b.text() for b in ins_teil]}",
)
# Schneidet die Schneide nur an der Wand entlang (Abstand 0), fährt sie nicht ins Teil.
e = pruefen(["G0 X50 Y30 Z30", "G1 Z8 F10", "G1 X67.5"], t1(schaft=4.0))
pruefe(not any(b.ins_teil for b in e.befunde), f"an der Wand: {[b.text() for b in e.befunde]}")
# Entgraten darf ins Teil – die Fase steht selten im Modell.
op.Gcode = ["G0 X-20 Y30 Z10", "G1 X120 F10"]
teil.recompute()
fahrt = ab.abfahrt(p, job, nullpunkt, wz.Bibliothek([lang]))
fahrt.operationen[0].art = "Deburr"
e = kb.kollision(fahrt, job, nullpunkt, wz.Bibliothek([lang]))
pruefe(not any(b.ins_teil for b in e.befunde), f"Entgraten: {[b.text() for b in e.befunde]}")

# --- Halter ER16: 1 mm zu tief neben der Tasche ---------------------------------------------
halter = "halter-er16"
e = pruefen(["G0 X60 Y30 Z40", "G1 Z12 F10", "G1 Z9"], t1(laenge_spindelnase=80.0, halter=halter))
name = "der Halter von T1 („Spannzangenfutter ER16 · SK40“)"
pruefe(paare(e) == {(name, "das Teil", True, False)}, f"Halter: {paare(e)}")
if e.befunde:
    pruefe(e.befunde[0].satz == 5, f"Halter: Satz {e.befunde[0].satz}")
    z = e.befunde[0].punkt["Z"]
    pruefe(9 <= z <= 10.1, f"Halter berührt bei Z {z}")
pruefe(not any("ohne Halter" in h for h in e.hinweise), f"Hinweise: {e.hinweise}")

# --- Kurzes Werkzeug neben dem Spanneisen: die Spindel --------------------------------------
# Das Spanneisen liegt flach auf dem Tisch, die Innenseite 100 mm neben der Mitte des
# Spannplatzes (X 150 im Job), die Schraube 45 mm weiter draußen, oben bei 60 mm über dem
# Tisch: Bei X 150 reicht die Spindel (Ø 90) bis über die Schraube und setzt mit der Nase
# darauf; das Werkzeug selbst fährt über dem Eisen (16 mm) vorbei.
kurz = t1(gesamtlaenge=25.0)
e = pruefen(["G0 X150 Y30 Z70", "G1 Z20 F10"], kurz)
pruefe(paare(e) == {("„Spindel“", "„Spanneisen_rechts“", True, False)}, f"Spindel: {paare(e)}")
if e.befunde:
    z = e.befunde[0].punkt["Z"]
    pruefe(33.5 <= z <= 34.0 + 1e-6, f"Spindel setzt bei Z {z} auf (erwartet knapp unter 34)")
    pruefe(e.befunde[0].satz == 4, f"Spindel: Satz {e.befunde[0].satz}")
# 4 mm darüber: mit Warnabstand 1 nichts, mit 5 eine Warnung (4,00 mm).
e = pruefen(["G0 X150 Y30 Z70", "G1 Z38 F10"], kurz)
pruefe(e.befunde == [], f"4 mm, Warnabstand 1: {paare(e)}")
e = pruefen(["G0 X150 Y30 Z70", "G1 Z38 F10"], kurz, warnabstand=5.0)
pruefe(
    paare(e) == {("„Spindel“", "„Spanneisen_rechts“", False, False)}, f"Warnabstand 5: {paare(e)}"
)
if e.befunde:
    pruefe(abs(e.befunde[0].abstand - 4.0) < 1e-6, f"Abstand: {e.befunde[0].abstand}")


# --- Die Schneide nach Art ---------------------------------------------------------------------
def koerper(werkzeug, laenge=60.0):
    """{Art: Form} der Körper von T1 ohne Halter, die Spitze bei Z −laenge."""
    masse = rw.werkzeugmasse(job.Tools.Group[0], wz.Bibliothek([werkzeug]), laenge)
    return dict(kb.werkzeugkoerper(masse, laenge, None))


def z_von_bis(form):
    return round(form.BoundBox.ZMin, 3), round(form.BoundBox.ZMax, 3)


# Lollipop Ø 5: eine Kugel an der Spitze (Z −60 … −55); der Hals (geschätzt Ø 3, 10 mm)
# beginnt in ihrer Mitte, darüber der Schaft bis zur Gesamtlänge 50.
k = koerper(t1(art=wz.LOLLIPOPFRAESER))
pruefe(set(k) == {kb.SCHNEIDE, kb.HALS, kb.SCHAFT}, f"Lollipop: {set(k)}")
if set(k) == {kb.SCHNEIDE, kb.HALS, kb.SCHAFT}:
    kugel = k[kb.SCHNEIDE]
    pruefe(abs(kugel.Volume - 4 / 3 * math.pi * 2.5**3) < 1e-3, f"Kugel: {kugel.Volume}")
    pruefe(abs(kugel.BoundBox.ZMin + 60) < 1e-2, f"Kugel: {z_von_bis(kugel)}")
    pruefe(z_von_bis(k[kb.HALS]) == (-57.5, -47.5), f"Lollipop, Hals: {z_von_bis(k[kb.HALS])}")
    pruefe(
        z_von_bis(k[kb.SCHAFT]) == (-47.5, -10.0), f"Lollipop, Schaft: {z_von_bis(k[kb.SCHAFT])}"
    )
# Nutenfräser Ø 5: die Scheibe so hoch wie die Schneidenbreite (geschätzt 0,5 mm), der Hals
# (geschätzt Ø 1,5, 1,25 mm), dann der Schaft – nicht 2 × D Schneide.
k = koerper(t1(art=wz.NUTENFRAESER))
pruefe(set(k) == {kb.SCHNEIDE, kb.HALS, kb.SCHAFT}, f"Nutenfräser: {set(k)}")
if set(k) == {kb.SCHNEIDE, kb.HALS, kb.SCHAFT}:
    pruefe(z_von_bis(k[kb.SCHNEIDE]) == (-60.0, -59.5), f"Scheibe: {z_von_bis(k[kb.SCHNEIDE])}")
    pruefe(z_von_bis(k[kb.HALS]) == (-59.5, -58.25), f"Nutenfräser, Hals: {z_von_bis(k[kb.HALS])}")
    pruefe(abs(k[kb.HALS].BoundBox.XLength - 1.5) < 1e-6, "Nutenfräser, Hals-Ø")
# Nur in CAM, nicht in der Werkzeugverwaltung: ein Scheibenfräser so hoch wie das Blatt.
saege = SimpleNamespace(
    Tool=SimpleNamespace(Diameter=50.0, BladeThickness=3.0, ShankDiameter=10.0, Length=40.0),
    ToolNumber=7,
)
m = rw.werkzeugmasse(saege, None, 60.0)
pruefe((m.schneide, m.schaft, m.gesamt, m.kugel) == (3.0, 10.0, 40.0, False), f"Säge: {m}")
pruefe(m.stirn is None, f"Säge ohne ToolBit: Stirn {m.stirn}")

# Die Stirn als Drehkörper: Kugelfräser Ø 5 – Halbkugel und Zylinder bis zur Schneidenlänge 5.
k = koerper(t1(art=wz.KUGELFRAESER))
if kb.SCHNEIDE in k:
    soll = 2 / 3 * math.pi * 2.5**3 + math.pi * 2.5**2 * 2.5
    pruefe(abs(k[kb.SCHNEIDE].Volume - soll) < 1e-6, f"Kugelfräser: {k[kb.SCHNEIDE].Volume}")
    pruefe(z_von_bis(k[kb.SCHNEIDE]) == (-60.0, -55.0), f"Kugelfräser: {z_von_bis(k[kb.SCHNEIDE])}")
# Jede Form: die Schneide gültig von der Spitze bis zur Schneidenlänge, der Kern darin und
# 0,05 mm von ihrer Stirn und Seite entfernt (oben schließt er mit ihr ab).
formen = {
    "Kugel": ff.kugel(2.5),
    "Torus": ff.torus(5.0, 1.0),
    "Konik": ff.konik(2.0, 5.0, 12.0, 3.0),
    "Fase": ff.kegel(0.0, 5.0, 5.0),
    "Radien": ff.radien(2.0, 2.0, 4.0),
    "Plan": ff.kegel(20.0, 25.0, 5.0),
}
for name, stirn in formen.items():
    masse = rw.Werkzeugmasse(2 * stirn.radius, 12.0, 0.0, 0.0, 2 * stirn.radius, 50.0, stirn=stirn)
    k = dict(kb.werkzeugkoerper(masse, 60.0, None, mit_kern=True))
    schneide, kern = k[kb.SCHNEIDE], k[kb.KERN]
    pruefe(schneide.isValid() and kern.isValid(), f"{name}: nicht gültig")
    pruefe(z_von_bis(schneide) == (-60.0, -48.0), f"{name}: {z_von_bis(schneide)}")
    pruefe(abs(schneide.common(kern).Volume - kern.Volume) < 1e-6, f"{name}: Kern steht heraus")
    stirnseite = [f for f in schneide.Faces if f.BoundBox.ZMin < -48.0 - 1e-6]  # ohne Deckel
    abstand = min(kern.distToShape(f)[0] for f in stirnseite)
    pruefe(0.048 <= abstand <= 0.0501, f"{name}: Kern {abstand:.4f} mm innen")
    pruefe(not kern.isInside(FreeCAD.Vector(0, 0, -60.02), 1e-7, True), f"{name}: Kern unten")

# Ein gewinkelter Halter (W-002 Stufe E, „VDI30 angetrieben radial“) kippt das Werkzeug:
# Die Spitze liegt 80 mm vom Bezugspunkt (55 mm unter der Aufnahme) längs +X, die Schneide
# Ø 5 × 5 davor, der Schaft bis zur Nase des Halters (55 mm); der Halter hat Kopf und Abgang.
radial = hl.aus_vorlage("vdi30_radial")
masse = rw.Werkzeugmasse(5.0, 5.0, 0.0, 0.0, 5.0, 50.0)
k = dict(kb.werkzeugkoerper(masse, 80.0, radial))
box = k[kb.SCHNEIDE].BoundBox
pruefe(
    abs(box.XMax - 80) < 1e-6 and abs(box.XMin - 75) < 1e-6 and abs(box.ZMin + 57.5) < 1e-6,
    f"Schneide mit gewinkeltem Halter: {box}",
)
pruefe(
    abs(k[kb.HALTER].BoundBox.ZMin + 82.5) < 1e-6 and abs(k[kb.SCHAFT].BoundBox.XMin - 55) < 1e-6,
    f"Halter {k[kb.HALTER].BoundBox}, Schaft {k[kb.SCHAFT].BoundBox}",
)
# Ist die Gesamtlänge (geschätzt 50) kürzer als das, was aus dem Halter ragt (125 − 55), reicht
# der Schaft trotzdem bis zur Nase – der Fräser schwebte sonst vor dem Halter (Manuel,
# 2026-09-30), gerade wie gewinkelt.
k = dict(kb.werkzeugkoerper(masse, 125.0, radial))
pruefe(
    abs(k[kb.SCHAFT].BoundBox.XMin - 55) < 1e-6 and abs(k[kb.SCHAFT].BoundBox.XMax - 120) < 1e-6,
    f"kurzer Fräser, gewinkelt: Schaft {k[kb.SCHAFT].BoundBox}",
)
gerade = hl.aus_vorlage("er32")
k = dict(kb.werkzeugkoerper(masse, 125.0, gerade))
pruefe(
    z_von_bis(k[kb.SCHAFT]) == (-120.0, -gerade.laenge),
    f"kurzer Fräser, gerade: Schaft {z_von_bis(k[kb.SCHAFT])}, Halter {gerade.laenge}",
)

# Kugelfräser über die Kante der Tasche (x 30, oben Z 20) gerollt: die Mitte 1,5 mm über der
# Tasche und 2 mm über der Kante – genau 2,5 mm von ihr –, die Spitze bei Z 19,5.
kugelfraeser = t1(art=wz.KUGELFRAESER, schaft=4.0)
e = pruefen(["G0 X31.5 Y30 Z30", "G1 Z19.5 F10", "G1 Y20"], kugelfraeser)
pruefe(e.befunde == [], f"Kugel an der Kante: {[b.text() for b in e.befunde]}")
e = pruefen(["G0 X31.5 Y30 Z30", "G1 Z19 F10", "G1 Y20"], kugelfraeser)
pruefe(
    [b.a for b in e.befunde if b.ins_teil] == ["die Schneide von T1"],
    f"Kugel 0,5 mm tiefer: {[b.text() for b in e.befunde]}",
)

# --- Rund um die Achse: dreht sich, ohne sich zu bewegen (W-003 V3e) --------------------------
# Ein Futter aus zwei Zylindern um die Achse ist rund; um 5 mm verschoben oder mit drei Backen
# nicht – dann zählt beim Drehen sein Abstand von der Achse.
achse, auf_der_achse = FreeCAD.Vector(1, 0, 0), FreeCAD.Vector(0, 0, 0)


def gebaut(form):
    return kb.Koerper("„Futter“", kb.MASCHINE, form, None, FreeCAD.Placement())


futter = Part.makeCompound(
    [
        Part.makeCylinder(110, 100, FreeCAD.Vector(380, 0, 0), achse),
        Part.makeCylinder(140, 90, FreeCAD.Vector(480, 0, 0), achse),
    ]
)
pruefe(kb._rund_um(gebaut(futter), achse, auf_der_achse), "Futter nicht rund")
daneben = gebaut(Part.makeCylinder(140, 90, FreeCAD.Vector(480, 5, 0), achse))
pruefe(not kb._rund_um(daneben, achse, auf_der_achse), "außermittig rund")
backen = Part.makeCylinder(140, 90, FreeCAD.Vector(480, 0, 0), achse)
for winkel in (0, 120, 240):
    backe = Part.makeBox(40, 30, 60, FreeCAD.Vector(570, -15, 30))
    backe.rotate(FreeCAD.Vector(), achse, winkel)
    backen = backen.fuse(backe)
pruefe(not kb._rund_um(gebaut(backen), achse, auf_der_achse), "Futter mit Backen rund")

# --- Führungen und Abbrechen ------------------------------------------------------------------
pruefe(not any("Grundstellung" in h for h in e.hinweise), f"Hinweis zu Führungen: {e.hinweise}")
e = pruefen(["G0 X50 Y30 Z30", "G1 Z10 F10"], t1(), fortschritt=lambda _anteil: False)
pruefe(e.abgebrochen and e.befunde == [], "Abbrechen")
pruefe(e.hinweise[-1].startswith("Abgebrochen – geprüft bis 0:00.0 von "), f"{e.hinweise}")

# --- Werkzeugwechsel ohne Wechselpunkt: Die Maschine wechselt, wo sie steht ----------------------
# T1 (50 mm) endet 2 mm über dem Teil, T2 ist 10 mm länger: Seine Schneide steckt nach dem
# Wechsel 8 mm im Teil – der Befund sagt, dass es am Wechsel liegt und was hilft. Ist T2 kürzer,
# stößt nichts an.
from Path.Tool import Controller  # noqa: E402

FreeCAD.setActiveDocument(teil.Name)
op.Gcode = ["G0 X10 Y30 Z30", "G0 Z22"]
tc2 = Controller.Create("T2", tool=op.ToolController.Tool, toolNumber=2)
job.Proxy.addToolController(tc2)
zweite = PathCustom.Create("Zweite")
zweite.ToolController = tc2
zweite.Gcode = ["G0 Z30", "G0 X50 Y30 Z30"]
teil.recompute()
for laenge, soll in ((60.0, "T2"), (45.0, None)):
    bibliothek = wz.Bibliothek([t1(), t1(nummer=2, gesamtlaenge=laenge)])
    bibliothek.halter_vorschlagen = False
    fahrt = ab.abfahrt(p, job, nullpunkt, bibliothek)
    e = kb.kollision(fahrt, job, nullpunkt, bibliothek)
    if soll is None:
        pruefe(e.befunde == [], f"T2 kürzer: {[b.text() for b in e.befunde]}")
        continue
    pruefe(
        e.befunde
        and all(
            b.wechsel == "T2"
            and b.operation == "Zweite"
            and "kein Wechselpunkt eingetragen" in b.text()
            for b in e.befunde
        ),
        f"am Wechsel: {[b.text() for b in e.befunde]}",
    )
teil.removeObject(zweite.Name)

FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)
assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
