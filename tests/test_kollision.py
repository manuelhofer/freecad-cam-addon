# Prüft die Kollision ohne Oberfläche (W-001, Stufe 4c; kollision.py) an der
# Beispiel-Fräse mit zwei Spanneisen und einem Teil 100 × 60 × 20 mit Tasche
# (x 30…70, y 15…45, Boden bei Z 5). Von Hand nachgerechnet:
# - frei in der Tasche: nichts;
# - Schneide 5 mm lang, Schaft so dick wie die Schneide, an der Taschenwand: der
#   Schaft berührt das Teil; mit Schaft Ø 4 bleibt 0,5 mm – eine Warnung;
# - Eilgang quer durchs Teil: Schneide und Schaft berühren es, „im Eilgang“;
# - Halter ER16 (Mutter Ø 28) bei 80 mm Länge ab Spindelnase, 1 mm zu tief neben
#   der Tasche: Der Halter berührt das Teil;
# - kurzes Werkzeug (25 mm) neben dem rechten Spanneisen: Die Spindel setzt auf
#   (Berührung), 4 mm darüber nur mit Warnabstand 5 eine Warnung;
# - Paare, die sich in der Grundstellung berühren (Führungen), prüft es nicht,
#   ohne Hinweis, wenn sie an einem Gelenk hängen; Abbrechen geht.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import abfahren as ab
from camaddon import beispielmaschine, sprache
from camaddon import kollision as kb
from camaddon import reichweite as rw
from camaddon import werkzeuge as wz

sprache.setze_sprache("de")
fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


asm, ma = beispielmaschine.fraesmaschine(spanneisen=True)
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


def pruefen(bahn, werkzeug, warnabstand=kb.WARNABSTAND, fortschritt=None):
    """Die Bahn mit diesem Werkzeug (T1 in der Werkzeugverwaltung) abfahren und prüfen."""
    op.Gcode = bahn
    teil.recompute()
    bibliothek = wz.Bibliothek([werkzeug])
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

# --- Eilgang quer durchs Teil ---------------------------------------------------------------
e = pruefen(["G0 X-20 Y30 Z10", "G0 X120"], t1())
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
# Derselbe Weg im Vorschub: Die Schneide schneidet (nicht gemeldet), der Schaft berührt.
e = pruefen(["G0 X-20 Y30 Z10", "G1 X120 F10"], t1())
pruefe(paare(e) == {("der Schaft von T1", "das Teil", True, False)}, f"Vorschub: {paare(e)}")

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
kurz = t1(gesamtlaenge=25.0)
e = pruefen(["G0 X110 Y30 Z40", "G1 Z10 F10", "G1 Z3"], kurz)
pruefe(paare(e) == {("„Spindel“", "„Spanneisen_rechts“", True, False)}, f"Spindel: {paare(e)}")
if e.befunde:
    z = e.befunde[0].punkt["Z"]
    pruefe(3.5 <= z <= 4.0 + 1e-6, f"Spindel setzt bei Z {z} auf (erwartet knapp unter 4)")
# 4 mm darüber: mit Warnabstand 1 nichts, mit 5 eine Warnung (4,00 mm).
e = pruefen(["G0 X110 Y30 Z40", "G1 Z8 F10"], kurz)
pruefe(e.befunde == [], f"4 mm, Warnabstand 1: {paare(e)}")
e = pruefen(["G0 X110 Y30 Z40", "G1 Z8 F10"], kurz, warnabstand=5.0)
pruefe(
    paare(e) == {("„Spindel“", "„Spanneisen_rechts“", False, False)}, f"Warnabstand 5: {paare(e)}"
)
if e.befunde:
    pruefe(abs(e.befunde[0].abstand - 4.0) < 1e-6, f"Abstand: {e.befunde[0].abstand}")

# --- Führungen und Abbrechen ------------------------------------------------------------------
pruefe(not any("Grundstellung" in h for h in e.hinweise), f"Hinweis zu Führungen: {e.hinweise}")
e = pruefen(["G0 X50 Y30 Z30", "G1 Z10 F10"], t1(), fortschritt=lambda _anteil: False)
pruefe(e.abgebrochen and e.befunde == [], "Abbrechen")
pruefe(e.hinweise[-1].startswith("Abgebrochen – geprüft bis 0:00.0 von "), f"{e.hinweise}")

FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)
assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
