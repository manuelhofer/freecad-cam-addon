# Prüft die schräge Achse (W-001, Abschnitt 7c; schraege_achse.py und die
# Transformation in maschine.py): der Winkel aus der Baugruppe – 0° an der
# Beispiel-Drehmaschine, ±30° mit gekippter Y-Führung –, die Rechnung in
# beide Richtungen, der Vorschlag für eine neue schräge Achse, die Meldungen,
# dass der Eintrag Speichern und Laden übersteht – und „Winkel eintragen,
# die Baugruppe folgt“: Die Teile bleiben, wo sie sind, ein Schlitten
# außerhalb von 0 bleibt auf seiner Stellung, Rückgängig stellt zurück.
import math
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)
sys.path.insert(0, os.path.join(ADDON, "tests"))

import beispielmaschinen
import FreeCAD

from camaddon import beispielmaschine, einheiten, sprache
from camaddon import kette as kette_modul
from camaddon import maschine as m
from camaddon import schraege_achse as sa
from camaddon import verfahren as vf

sprache.setze_sprache("de")
fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nahe(a, b, genau=1e-6):
    return a is not None and b is not None and abs(a - b) < genau


def schluessel(meldungen):
    return [x.schluessel for x in meldungen]


# --- Rechnung ---------------------------------------------------------------------
x1, y1 = sa.schlitten_aus_programm(30, 0, 10)
pruefe(nahe(y1, 10 / math.cos(math.radians(30))), f"Y1 bei 30°: {y1}")
pruefe(nahe(y1, 11.547005), f"Y1 bei 30°: {y1}")
pruefe(nahe(x1, -5.773503), f"X1 bei 30°: {x1}")
x, y = sa.programm_aus_schlitten(30, x1, y1)
pruefe(nahe(x, 0) and nahe(y, 10), f"zurück bei 30°: {x}, {y}")
x1, y1 = sa.schlitten_aus_programm(-30, 40, 10)
pruefe(nahe(x1, 40 + 5.773503) and nahe(y1, 11.547005), f"−30°: {x1}, {y1}")
pruefe(sa.schlitten_aus_programm(0, 12, -7) == (12, -7), "0°: Schlitten = Programm")
for alpha in (-60, -12.5, 0, 17, 45, 80):
    x, y = sa.programm_aus_schlitten(alpha, *sa.schlitten_aus_programm(alpha, 33.3, -21.7))
    pruefe(nahe(x, 33.3) and nahe(y, -21.7), f"hin und zurück bei {alpha}°: {x}, {y}")

# --- Beispiel-Drehmaschine: Y rechtwinklig zu X ---------------------------------------
asm, ma = beispielmaschine.drehmaschine()
doc = asm.Document
kette = kette_modul.lies_kette(asm)
ba = {b.NcName: b for b in m.betriebsarten(ma)}
pruefe(
    [m.name_von(b) for b in sa.linearachsen(ma, kette)] == ["X1", "Y1", "Z1"],
    f"Linearachsen: {[m.name_von(b) for b in sa.linearachsen(ma, kette)]}",
)
pruefe(sa.vorschlag(ma, kette) == (ba["Y1"], ba["X1"]), "Vorschlag: Y1 schräg, X1 gleicht aus")
pruefe(not sa.ohne_eintrag(ma, kette), "rechtwinklige Achsen gelten als schräg")
pruefe(not sa.pruefe(ma, kette), "rechtwinklige Maschine: Meldung ohne Eintrag")
pruefe(nahe(sa.winkel_zwischen(kette, ma, ba["Y1"], ba["X1"]), 0), "Y1/X1 nicht rechtwinklig")
pruefe(nahe(sa.winkel_zwischen(kette, ma, ba["Z1"], ba["X1"]), 0), "Z1/X1 nicht rechtwinklig")
pruefe(sa.winkel_zwischen(kette, ma, ba["C1"], ba["X1"]) is None, "C1 ist keine Linearachse")

trafo = m.neue_schraege_achse(ma, ba["Y1"], ba["X1"])
doc.recompute()
pruefe(m.ist_transformation(trafo) and m.transformationen(ma) == [trafo], "Eintrag fehlt")
pruefe((trafo.NameSchraeg, trafo.NameAusgleich) == ("Y", "X"), "Namen im Programm")
pruefe(trafo.Label == "Y · Schräge Achse", f"Beschriftung: {trafo.Label!r}")
pruefe(nahe(sa.winkel(kette, ma, trafo), 0), f"Winkel: {sa.winkel(kette, ma, trafo)}")
pruefe(not sa.pruefe(ma, kette), f"Meldungen: {schluessel(sa.pruefe(ma, kette))}")
pruefe(not [x for x in m.pruefe(ma, kette) if x.bezug is trafo], "m.pruefe meldet den Eintrag")
pruefe(m.programmname(ba["C1"]) == "C", "Programmname C1")
ohne_ziffer = m.neue_betriebsart(ma, None, m.ART_LINEAR, "U")
pruefe(m.programmname(ohne_ziffer) == "U", "Programmname ohne Ziffer")
ziffern = m.neue_betriebsart(ma, None, m.ART_LINEAR, "12")
pruefe(m.programmname(ziffern) == "12", "Programmname nur Ziffern")
for b in (ohne_ziffer, ziffern):
    doc.removeObject(b.Name)

# Ein Paar ist vergeben: Der Vorschlag bleibt beim ersten Paar, wenn keines schräg steht.
pruefe(sa.vorschlag(ma, kette) == (ba["Y1"], ba["X1"]), "Vorschlag nach dem ersten Eintrag")

# --- Meldungen ------------------------------------------------------------------------
trafo.Schraeg = None
pruefe(schluessel(sa.pruefe(ma, kette)) == ["maschine.trafo_achse_fehlt"], "Achse fehlt")
trafo.Schraeg = ba["X1"]
pruefe(schluessel(sa.pruefe(ma, kette)) == ["maschine.trafo_gleiche_achse"], "gleiche Achse")
trafo.Schraeg = ba["C1"]
meldungen = sa.pruefe(ma, kette)
pruefe(schluessel(meldungen) == ["maschine.trafo_nicht_linear"], "nicht linear")
pruefe(meldungen and "„C1“" in meldungen[0].text, f"Text: {meldungen[0].text if meldungen else ''}")
trafo.Schraeg = ba["Y1"]
pruefe(not sa.pruefe(ma, kette), "wieder in Ordnung")

# --- Y-Führung schräg: 30° zur Plus-Seite von X1, dann −30° -----------------------------
achsen = {a.gelenk.Label: a for a in kette.achsen}
beispielmaschinen.kippe_fuehrung(achsen["Y"], 30, zu=vf.plusrichtung(achsen["X"]))
kette = kette_modul.lies_kette(asm)
pruefe(nahe(sa.winkel(kette, ma, trafo), 30), f"Winkel +30°: {sa.winkel(kette, ma, trafo)}")
pruefe(not sa.pruefe(ma, kette), f"Meldungen bei 30°: {schluessel(sa.pruefe(ma, kette))}")
# Tauscht man die Rollen, steht X1 ebenso 30° schräg zu Y1.
pruefe(nahe(sa.winkel_zwischen(kette, ma, ba["X1"], ba["Y1"]), 30), "X1 zu Y1")

# Jetzt steht ein Paar schräg: Ohne Eintrag schlägt der Vorschlag genau dieses vor,
# und ein Hinweis sagt es – sein Bezug legt die schräge Achse an.
doc.removeObject(trafo.Name)
pruefe(sa.vorschlag(ma, kette) == (ba["Y1"], ba["X1"]), "Vorschlag bei schrägem Paar")
offen = sa.ohne_eintrag(ma, kette)
pruefe(
    len(offen) == 1 and offen[0][:2] == (ba["Y1"], ba["X1"]) and nahe(offen[0][2], 30),
    f"ohne Eintrag: {offen}",
)
einheiten.setze_dezimalzeichen(",")
meldungen = sa.pruefe(ma, kette)
einheiten.setze_dezimalzeichen(None)
pruefe(
    schluessel(meldungen) == ["maschine.trafo_schraeg_erkannt"],
    f"Erkennung: {schluessel(meldungen)}",
)
if meldungen:
    hinweis = meldungen[0]
    pruefe(hinweis.schwere == "hinweis", "Erkennung ist kein Hinweis")
    pruefe(hinweis.text.startswith("Y1 steht 30,0° schräg zu X1."), f"Text: {hinweis.text}")
    pruefe("„Y“" in hinweis.text, f"Name im Programm fehlt: {hinweis.text}")
    bezug = hinweis.bezug
    pruefe(
        isinstance(bezug, sa.Anlegen) and (bezug.schraeg, bezug.ausgleich) == (ba["Y1"], ba["X1"]),
        f"Bezug: {bezug}",
    )
meldungen = m.pruefe(ma, kette)
pruefe(
    [x.schluessel for x in meldungen if x.schluessel.startswith("maschine.trafo")]
    == ["maschine.trafo_schraeg_erkannt"],
    "m.pruefe gibt die Erkennung nicht weiter",
)
trafo = m.neue_schraege_achse(ma, ba["Y1"], ba["X1"])
doc.recompute()
pruefe(not sa.ohne_eintrag(ma, kette), "mit Eintrag noch offen")
pruefe(not sa.pruefe(ma, kette), f"mit Eintrag: {schluessel(sa.pruefe(ma, kette))}")
# Auch mit vertauschten Rollen deckt der Eintrag das Paar ab.
trafo.Schraeg, trafo.Ausgleich = ba["X1"], ba["Y1"]
pruefe(not sa.ohne_eintrag(ma, kette), "vertauscht noch offen")
trafo.Schraeg, trafo.Ausgleich = ba["Y1"], ba["X1"]

achsen = {a.gelenk.Label: a for a in kette.achsen}
beispielmaschinen.kippe_fuehrung(achsen["Y"], 60, zu=vf.plusrichtung(achsen["X"]) * -1)
kette = kette_modul.lies_kette(asm)
pruefe(nahe(sa.winkel(kette, ma, trafo), -30), f"Winkel −30°: {sa.winkel(kette, ma, trafo)}")

# Fast parallel: 89,5° – daraus lässt sich kein Y mehr rechnen.
achsen = {a.gelenk.Label: a for a in kette.achsen}
beispielmaschinen.kippe_fuehrung(achsen["Y"], 119.5, zu=vf.plusrichtung(achsen["X"]))
kette = kette_modul.lies_kette(asm)
pruefe(nahe(sa.winkel(kette, ma, trafo), 89.5), f"Winkel 89,5°: {sa.winkel(kette, ma, trafo)}")
meldungen = sa.pruefe(ma, kette)
pruefe(schluessel(meldungen) == ["maschine.trafo_parallel"], f"parallel: {schluessel(meldungen)}")
pruefe(meldungen and "„Y“" in meldungen[0].text, "parallel: Name im Programm fehlt im Satz")

# Eine Achse im Tisch bewegt das Werkstück – für das Werkzeug zählt sie andersherum;
# ohne Rolle (noch keine Aufnahmen) wie eine im Kopf.
achsen = {a.gelenk.Label: a for a in kette.achsen}
x = achsen["X"]
pruefe((sa._richtung(x, {x.gelenk: m.TISCH}) + vf.plusrichtung(x)).Length < 1e-9, "Tisch")
pruefe((sa._richtung(x, {x.gelenk: m.KOPF}) - vf.plusrichtung(x)).Length < 1e-9, "Kopf")
pruefe((sa._richtung(x, {}) - vf.plusrichtung(x)).Length < 1e-9, "ohne Rolle")

beispielmaschinen.kippe_fuehrung(achsen["Y"], -89.5, zu=vf.plusrichtung(achsen["X"]))
kette = kette_modul.lies_kette(asm)
pruefe(nahe(sa.winkel(kette, ma, trafo), 0), f"zurück auf 0°: {sa.winkel(kette, ma, trafo)}")

# --- Speichern und Laden ----------------------------------------------------------------
achsen = {a.gelenk.Label: a for a in kette.achsen}
beispielmaschinen.kippe_fuehrung(achsen["Y"], 30, zu=vf.plusrichtung(achsen["X"]))
trafo.NameSchraeg = "YP"
m.beschrifte(trafo)
pfad = os.path.join(tempfile.mkdtemp(), "schraeg.FCStd")
doc.saveAs(pfad)
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(pfad)
asm = next(o for o in doc.Objects if o.TypeId == "Assembly::AssemblyObject")
ma = m.finde_maschine(asm)
kette = kette_modul.lies_kette(asm)
geladen = m.transformationen(ma)
pruefe(len(geladen) == 1, f"nach dem Laden: {len(geladen)} Transformationen")
if geladen:
    t = geladen[0]
    pruefe(t.Art == m.TRAFO_SCHRAEGE_ACHSE, f"Art: {t.Art}")
    pruefe(m.name_von(t.Schraeg) == "Y1" and m.name_von(t.Ausgleich) == "X1", "Achsen")
    pruefe((t.NameSchraeg, t.NameAusgleich) == ("YP", "X"), "Namen nach dem Laden")
    pruefe(nahe(sa.winkel(kette, ma, t), 30), f"Winkel nach dem Laden: {sa.winkel(kette, ma, t)}")
FreeCAD.closeDocument(doc.Name)

# --- Winkel eintragen: die Baugruppe folgt ----------------------------------------------
asm, ma = beispielmaschine.drehmaschine()
doc = asm.Document
doc.UndoMode = 1
kette = kette_modul.lies_kette(asm)
ba = {b.NcName: b for b in m.betriebsarten(ma)}
trafo = m.neue_schraege_achse(ma, ba["Y1"], ba["X1"])
doc.recompute()
teile = {o.Label: o for o in doc.Objects if o.TypeId in ("Part::Box", "App::Part")}
anfang = {name: FreeCAD.Placement(o.Placement) for name, o in teile.items()}


def bewegt():
    return sorted(n for n, o in teile.items() if not o.Placement.isSame(anfang[n], 1e-7))


doc.openTransaction("Winkel 30")
kette = sa.drehe_fuehrung(asm, kette, ma, trafo, 30)
doc.commitTransaction()
pruefe(nahe(sa.winkel(kette, ma, trafo), 30), f"eingetragen 30°: {sa.winkel(kette, ma, trafo)}")
pruefe(not bewegt(), f"30° eingetragen, bewegt: {bewegt()}")
doc.recompute()
pruefe(not bewegt(), f"nach dem Neuberechnen bewegt: {bewegt()}")

# Rückgängig stellt die Führung zurück.
doc.undo()
doc.recompute()
kette = kette_modul.lies_kette(asm)
pruefe(nahe(sa.winkel(kette, ma, trafo), 0), f"nach Rückgängig: {sa.winkel(kette, ma, trafo)}")
pruefe(not bewegt(), f"nach Rückgängig bewegt: {bewegt()}")
doc.redo()
doc.recompute()
kette = kette_modul.lies_kette(asm)
pruefe(nahe(sa.winkel(kette, ma, trafo), 30), f"nach Wiederholen: {sa.winkel(kette, ma, trafo)}")

# Der Schlitten steht auf 20 mm: Er bleibt auf 20 mm, nun entlang der neuen Richtung.
achse_y = next(a for a in kette.achsen if a.gelenk.Label == "Y")
vf.Verfahren(asm, kette).setze(achse_y, 20)
bei_20 = FreeCAD.Placement(teile["YSchlitten"].Placement)
revolver = FreeCAD.Placement(teile["Revolver"].Placement)
kette = sa.drehe_fuehrung(asm, kette, ma, trafo, -15)
achse_y = next(a for a in kette.achsen if a.gelenk.Label == "Y")
pruefe(nahe(sa.winkel(kette, ma, trafo), -15), f"eingetragen −15°: {sa.winkel(kette, ma, trafo)}")
stellung = vf.gelenkstellung(achse_y.gelenk, achse_y.art)
pruefe(nahe(stellung, 20), f"Stellung nach dem Drehen: {stellung}")
ziel = anfang["YSchlitten"].Base + vf.plusrichtung(achse_y) * 20
pruefe((teile["YSchlitten"].Placement.Base - ziel).Length < 1e-6, "Schlitten nicht auf 20 mm")
pruefe(not teile["YSchlitten"].Placement.isSame(bei_20, 1e-6), "Schlitten ist nicht mitgefahren")
pruefe(
    teile["Revolver"].Placement.Rotation.isSame(revolver.Rotation, 1e-9),
    "Revolver hat sich gedreht",
)
doc.recompute()
stellung = vf.gelenkstellung(achse_y.gelenk, achse_y.art)
pruefe(nahe(stellung, 20), f"Stellung nach dem Neuberechnen: {stellung}")

# Zurück auf 0° und Stellung 0: alles wie gebaut.
kette = sa.drehe_fuehrung(asm, kette, ma, trafo, 0)
achse_y = next(a for a in kette.achsen if a.gelenk.Label == "Y")
vf.Verfahren(asm, kette).setze(achse_y, 0)
pruefe(nahe(sa.winkel(kette, ma, trafo), 0), f"zurück auf 0°: {sa.winkel(kette, ma, trafo)}")
pruefe(not bewegt(), f"zurück auf 0°, bewegt: {bewegt()}")

# Über ±89° geht es nicht.
for grad in (89.5, -90, 120):
    try:
        sa.drehe_fuehrung(asm, kette, ma, trafo, grad)
        pruefe(False, f"{grad}° angenommen")
    except ValueError:
        pass
pruefe(nahe(sa.winkel(kette, ma, trafo), 0), "ein abgelehnter Winkel hat etwas gedreht")
FreeCAD.closeDocument(doc.Name)

# --- Verfahren wie im Programm (schraege_achse.Programm) ---------------------------------
asm, ma = beispielmaschine.drehmaschine()
doc = asm.Document
kette = kette_modul.lies_kette(asm)
ba = {b.NcName: b for b in m.betriebsarten(ma)}
trafo = m.neue_schraege_achse(ma, ba["Y1"], ba["X1"])
kette = sa.drehe_fuehrung(asm, kette, ma, trafo, 30)
v = vf.Verfahren(asm, kette)
pruefe(sa.Programm.moeglich(v, ma, trafo), "Programm nicht möglich")
prog = sa.Programm(v, ma, trafo)
pruefe(nahe(prog.alpha, 30), f"α im Programm: {prog.alpha}")
pruefe(prog.stellung() == (0.0, 0.0) or all(nahe(w, 0) for w in prog.stellung()), "Start nicht 0")
x, y, anschlag = prog.setze(0, 10)
pruefe(nahe(x, 0) and nahe(y, 10) and anschlag is None, f"Y 10: {x}, {y}, {anschlag}")
x1, y1 = prog.schlitten()
pruefe(nahe(x1, -5.773503) and nahe(y1, 11.547005), f"Schlitten bei Y 10: {x1}, {y1}")
pruefe(nahe(v.stellung(prog.ausgleich), x1), "Verfahren kennt X1 nicht")

# Bereich: Y1 −60 … 60 → Y höchstens ±51,96; X1 −170 … 150 → X von −200 bis 180.
(xu, xo), (yu, yo) = prog.bereich()
pruefe(nahe(yu, -51.961524) and nahe(yo, 51.961524), f"Y-Bereich: {yu} … {yo}")
pruefe(nahe(xu, -200) and nahe(xo, 180), f"X-Bereich: {xu} … {xo}")

# X auf 140, dann Y auf −40: X1 bräuchte 140 + 40·tan 30° = 163,1 > 150 – es hält bei
# X1 = 150, Y bleibt bei −17,32 stehen (wie in der Spezifikation).
x, y, anschlag = prog.setze(140, 0)
pruefe(nahe(x, 140) and nahe(y, 0) and anschlag is None, f"X 140: {x}, {y}, {anschlag}")
x, y, anschlag = prog.setze(140, -40)
pruefe(anschlag is not None and anschlag[0] is prog.ausgleich, f"Anschlag: {anschlag}")
pruefe(anschlag is not None and nahe(anschlag[1], 150), f"Grenze: {anschlag}")
pruefe(nahe(y, -17.320508, 1e-5) and nahe(x, 140, 1e-5), f"gehalten bei: {x}, {y}")
pruefe(nahe(prog.schlitten()[0], 150), f"X1 am Anschlag: {prog.schlitten()[0]}")
# Y1 an seiner Grenze: Y auf 70 geht nur bis 51,96 (Y1 = 60).
prog.setze(0, 0)
x, y, anschlag = prog.setze(0, 70)
pruefe(anschlag is not None and anschlag[0] is prog.schraeg, f"Anschlag Y1: {anschlag}")
pruefe(nahe(y, 51.961524, 1e-5) and nahe(prog.schlitten()[1], 60), f"Y1 am Anschlag: {y}")
# Zurück in die Mitte, und die Grundstellung stimmt.
prog.setze(0, 0)
pruefe(all(nahe(w, 0) for w in prog.schlitten()), f"zurück: {prog.schlitten()}")
v.grundstellung()
pruefe(all(nahe(w, 0) for w in prog.stellung()), "Grundstellung")
# Ohne gültigen Winkel geht es nicht.
trafo.Ausgleich = None
pruefe(not sa.Programm.moeglich(v, ma, trafo), "Programm ohne ausgleichende Achse möglich")
FreeCAD.closeDocument(doc.Name)

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
