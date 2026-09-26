# Prüft „Reicht der Verfahrweg?“ (W-001, Stufe 4a; reichweite.py). Für Punkte im
# Job rechnet die Prüfung die Stellungen aller Achsen; fährt die Maschine
# dorthin, steht die Werkzeugspitze genau auf dem Punkt – an der 3-Achs-Fräse,
# der Drehmaschine (beide Revolverplätze, auch mit schräger Y-Achse), den drei
# 5-Achs-Fräsen mit Rundachsen aus der Bahn und einer Drehmaschine ohne Y (dort
# kommt nicht jeder Punkt in Frage). Dazu Jobs mit eigener Bahn: Geraden,
# Kreise (auch in G18, auch als Vollkreis – die Umkehrstellen zählen),
# Bohrzyklus; eine Achse über ihrer Grenze als Satz; Hinweise zur
# Werkzeuglänge, zu einem fehlenden Revolverplatz, zu einer verkehrt
# herum liegenden Werkzeugaufnahme und zu unbekannten Befehlen; der Nullpunkt
# des Jobs – Vorschlag, eintragen, Speichern und Laden.
import math
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)
sys.path.insert(0, os.path.join(ADDON, "tests"))

import beispielmaschinen
import FreeCAD

from camaddon import beispielmaschine, sprache
from camaddon import maschine as m
from camaddon import reichweite as rw
from camaddon import schraege_achse as sa
from camaddon import verfahren as vf
from camaddon import werkzeuge as wz

sprache.setze_sprache("de")
fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nahe(a, b, genau=1e-6):
    return a is not None and b is not None and abs(a - b) < genau


def namen(pruefung, stellungen):
    return {vf.namen(pruefung.maschine, a): round(s, 6) for a, s in stellungen.items()}


def abstand(pruefung, stellungen, aufnahme, laenge, nullpunkt, punkt):
    """Fährt die Maschine auf `stellungen`, misst den Abstand Spitze – Punkt, fährt zurück."""
    verfahren = vf.Verfahren(pruefung.verfahren.assembly, pruefung.kette)
    for achse, stellung in stellungen.items():
        verfahren.setze(achse, stellung, grenzen=False)
    spitze = m.globale_platzierung(aufnahme.Lcs).multVec(FreeCAD.Vector(0, 0, -laenge))
    job = m.globale_platzierung(pruefung.werkstueckaufnahme.Lcs).multiply(
        FreeCAD.Placement(nullpunkt, FreeCAD.Rotation())
    )
    ziel = job.multVec(FreeCAD.Vector(*punkt))
    verfahren.grundstellung()
    return (spitze - ziel).Length


def trifft(name, pruefung, aufnahme, punkte, laenge=50.0, nullpunkt=None, rund=None):
    """Für jeden Punkt: Stellungen da, und die Spitze steht dort."""
    nullpunkt = nullpunkt or FreeCAD.Vector()
    for punkt in punkte:
        stellungen = pruefung.stellungen(punkt, aufnahme, laenge, nullpunkt, rund)
        if stellungen is None:
            fehler.append(f"{name}: keine Stellungen für {punkt}")
            continue
        weg = abstand(pruefung, stellungen, aufnahme, laenge, nullpunkt, punkt)
        pruefe(weg < 1e-6, f"{name}: Spitze {weg:.6f} mm neben {punkt} {rund or ''}")


def neuer_job(zeilen, name="Teil"):
    """Ein Dokument mit einem Quader 100 × 60 × 20 und einem Job mit eigener Bahn."""
    import Path.Main.Job as PathJob
    import Path.Op.Custom as PathCustom

    doc = FreeCAD.newDocument(name)
    quader = doc.addObject("Part::Box", "Teil")
    quader.Length, quader.Width, quader.Height = 100, 60, 20
    doc.recompute()
    job = PathJob.Create("Job", [quader])
    op = PathCustom.Create("Eigene")
    op.Gcode = zeilen
    doc.recompute()
    return doc, job, op


def texte(ergebnis):
    return [u.text() for u in ergebnis.ueberschreitungen]


def bereich(ergebnis, name):
    return next(((b.von, b.bis) for b in ergebnis.bereiche if b.name == name), None)


# --- 3-Achs-Fräse: die Spitze trifft ------------------------------------------------------
asm, ma = beispielmaschine.fraesmaschine()
p = rw.Pruefung(asm, ma)
spindel = p.werkzeugaufnahme(1)
pruefe(spindel is not None and spindel.Bezeichnung == "Spindel", f"Aufnahme: {spindel}")
pruefe(p.werkstueckaufnahme.Bezeichnung == "Tisch", "Werkstückaufnahme Tisch")
trifft("Fräse", p, spindel, [(0, 0, 0), (100, 50, -20), (-30, 20, 5), (7.5, -3.25, 40)])
trifft(
    "Fräse mit Nullpunkt", p, spindel, [(0, 0, 0), (12, 34, -5)], 80, FreeCAD.Vector(-50, -30, 20)
)
# Nullpunkt des Jobs auf der Tischmitte, Werkzeug 50 mm: Die Spindelnase steht 130 mm
# über dem Tisch, also Z1 = −80 für Z 0. X und Y fährt der Tisch: X1 = −X.
st = namen(p, p.stellungen((100, 50, -20), spindel, 50, FreeCAD.Vector()))
pruefe(st == {"X1": -100, "Y1": -50, "Z1": -100}, f"Fräse (100, 50, −20): {st}")
pruefe(p.stellungen((0, 0, 0), spindel, 50, FreeCAD.Vector()) is not None, "Fräse (0, 0, 0)")

# --- Job mit eigener Bahn: Geraden, Kreis, Bohrzyklus ----------------------------------------
bahn = [
    "G0 Z10",  # X und Y noch unbekannt: kein Punkt
    "G0 X0 Y0",
    "G1 Z-5 F100",
    "G1 X150 Y20",
    "G2 X170 Y40 I0 J20",  # 270° im Uhrzeigersinn um (150, 40): links bei X 130, oben bei Y 60
    "G0 Z10",
    "G0 X400 Y0",
    "G81 X400 Y0 Z-8 R3 F100",  # über dem Loch, R-Ebene, Grund
    "G80",
    "G28 X0",  # kennt die Prüfung nicht
]
teil, job, op = neuer_job(bahn)
e = p.pruefe_job(job, FreeCAD.Vector())
pruefe(not e.in_grenzen(), "X 400 bleibt in den Grenzen?")
pruefe(
    texte(e)
    == ["X1 fährt in „Eigene“ bis −400.00 mm, die Grenze ist −250.00 mm (bei X 400, Y 0, Z 10)."],
    f"Überschreitung: {texte(e)}",
)
u = e.ueberschreitungen[0]
pruefe(
    namen(p, u.stellungen) == {"X1": -400, "Y1": 0, "Z1": -70},
    f"Stellungen an der Überschreitung: {namen(p, u.stellungen)}",
)
pruefe(bereich(e, "X1") == (-400.0, 0.0), f"X1: {bereich(e, 'X1')}")
pruefe(bereich(e, "Y1") == (-60.0, 0.0), f"Y1 mit dem Scheitel des Kreises: {bereich(e, 'Y1')}")
pruefe(bereich(e, "Z1") == (-88.0, -70.0), f"Z1 mit dem Grund der Bohrung: {bereich(e, 'Z1')}")
pruefe(
    [b.text() for b in e.bereiche][0]
    == "X1 braucht −400.00 mm … 0.00 mm, die Grenzen sind −250.00 mm … 250.00 mm.",
    f"Bereich als Satz: {[b.text() for b in e.bereiche]}",
)
t1 = rw.werkzeug_text(op.ToolController)  # „T1 „Endmill““ – der Name hängt an FreeCAD
pruefe(t1.startswith("T1 „"), t1)
pruefe(
    e.hinweise
    == [
        f"{t1}: gerechnet mit der Länge des CAM-Werkzeugs, 50.00 mm – ohne Halter. Das "
        "Werkzeug steht nicht in der Werkzeugverwaltung; dort gäbe es die „Länge ab "
        "Spindelnase“.",
        "„Eigene“: Den Befehl G28 kennt die Prüfung nicht – übergangen.",
    ],
    f"Hinweise: {e.hinweise}",
)
# 11 Punkte: G0 Z10 ohne X und Y zählt nicht; der Kreis bringt zwei Umkehrstellen
# (links bei X 130, oben bei Y 60) und sein Ende; der Bohrzyklus drei Höhen.
pruefe(e.punkte == 11, f"Punkte: {e.punkte}")

# Die Werkzeugverwaltung kennt T1 (Ø 5 mm): ihre Gesamtlänge gilt – oder geschätzt. 10 mm
# länger als die 50 des CAM-Werkzeugs: Die Spindel steht 10 mm höher.
bibliothek = wz.Bibliothek([wz.Werkzeug(nummer=1, durchmesser=5.0, gesamtlaenge=60.0)])
e = p.pruefe_job(job, FreeCAD.Vector(), bibliothek)
pruefe(bereich(e, "Z1") == (-78.0, -60.0), f"Z1 mit 60 mm: {bereich(e, 'Z1')}")
pruefe(
    e.hinweise[0]
    == f"{t1}: gerechnet mit der Gesamtlänge 60.00 mm – ohne Halter. Genauer mit der „Länge "
    "ab Spindelnase“ in der Werkzeugverwaltung.",
    f"Hinweis Gesamtlänge: {e.hinweise}",
)
bibliothek.werkzeuge[0].gesamtlaenge = 0.0
e = p.pruefe_job(job, FreeCAD.Vector(), bibliothek)
geschaetzt = wz.geschaetzte_laenge(bibliothek.werkzeuge[0])
pruefe(
    e.hinweise[0]
    == f"{t1}: keine Gesamtlänge eingetragen – gerechnet mit geschätzten {geschaetzt:.2f} mm, "
    "ohne Halter. Genauer mit der „Länge ab Spindelnase“ in der Werkzeugverwaltung.",
    f"Hinweis geschätzt: {e.hinweise}",
)
# Mit der Länge ab Spindelnase (110 mm, mit Halter): Sie gilt, ohne Hinweis zur Länge.
bibliothek.werkzeuge[0].laenge_spindelnase = 110.0
pruefe(rw.werkzeuglaenge(op.ToolController, bibliothek) == (110.0, rw.LAENGE_SPINDELNASE), "")
e = p.pruefe_job(job, FreeCAD.Vector(), bibliothek)
pruefe(bereich(e, "Z1") == (-28.0, -10.0), f"Z1 mit 110 mm: {bereich(e, 'Z1')}")
pruefe(
    not any("Länge" in h for h in e.hinweise), f"Hinweis trotz Länge ab Spindelnase: {e.hinweise}"
)

# Innerhalb der Grenzen: ein Vollkreis (Umkehrstellen in X und Y), G18-Halbkreis.
op.Gcode = [
    "G0 X10 Y0 Z5",
    "G3 X10 Y0 I-10 J0",  # Vollkreis um (0, 0), r 10
    "G18",
    "G1 X10 Y0 Z0",
    "G2 X-10 Z0 I-10 K0",  # Halbkreis in XZ über Z 10 (von +Y aus im Uhrzeigersinn)
    "G17",
]
teil.recompute()
e = p.pruefe_job(job, FreeCAD.Vector())
pruefe(e.in_grenzen() and not e.ueberschreitungen, f"Kreise: {texte(e)}")
pruefe(bereich(e, "X1") == (-10.0, 10.0), f"X1 am Vollkreis: {bereich(e, 'X1')}")
pruefe(bereich(e, "Y1") == (-10.0, 10.0), f"Y1 am Vollkreis: {bereich(e, 'Y1')}")
pruefe(bereich(e, "Z1") == (-80.0, -70.0), f"Z1 mit dem Scheitel in XZ: {bereich(e, 'Z1')}")
pruefe(len(e.hinweise) == 1 and "Länge des CAM-Werkzeugs" in e.hinweise[0], f"{e.hinweise}")

# Eine Werkzeugaufnahme, deren Z zum Werkstück zeigt: Hinweis.
lcs = spindel.Lcs
lcs.Placement = FreeCAD.Placement(
    lcs.Placement.Base, FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 180)
)
asm.Document.recompute()
e = rw.Pruefung(asm, ma).pruefe_job(job, FreeCAD.Vector())
pruefe(
    any(
        h.startswith("Die Z-Achse der Werkzeugaufnahme „Spindel“ zeigt zum Werkstück")
        for h in e.hinweise
    ),
    f"Z verkehrt: {e.hinweise}",
)

# Der Nullpunkt des Jobs: Vorschlag, eintragen, speichern.
vorschlag = rw.vorschlag_nullpunkt(job)
box = job.Stock.Shape.BoundBox
pruefe(
    vorschlag.isEqual(FreeCAD.Vector(-box.Center.x, -box.Center.y, -box.ZMin), 1e-9),
    f"Vorschlag: {vorschlag}",
)
pruefe(rw.eingetragener_nullpunkt(job) == {}, "nichts eingetragen")
rw.setze_nullpunkt(job, {"Z": 25.0})
pruefe(rw.nullpunkt(job).isEqual(FreeCAD.Vector(vorschlag.x, vorschlag.y, 25), 1e-9), "Z 25")
pfad = os.path.join(tempfile.mkdtemp(), "teil.FCStd")
teil.saveAs(pfad)
FreeCAD.closeDocument(teil.Name)
teil = FreeCAD.openDocument(pfad)
job = next(o for o in teil.Objects if o.Name == "Job")
pruefe(rw.eingetragener_nullpunkt(job) == {"Z": 25.0}, "Nullpunkt nach dem Laden")
rw.setze_nullpunkt(job, {})
pruefe(rw.eingetragener_nullpunkt(job) == {}, "Nullpunkt gelöscht")
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)

# --- Drehmaschine: Revolverplätze, Futter als Job -------------------------------------------
asm, ma = beispielmaschine.drehmaschine()
p = rw.Pruefung(asm, ma)
p1, p2 = p.werkzeugaufnahme(1), p.werkzeugaufnahme(2)
pruefe(m.name_von(p1) == "P1" and m.name_von(p2) == "P2", "Plätze P1 und P2")
pruefe(p.werkzeugaufnahme(20) is None, "Platz P20 gibt es nicht")
drehpunkte = [(20, 0, 30), (35.5, -12, 60), (0, 0, 10)]
trifft("Drehmaschine P1", p, p1, drehpunkte, 40)
trifft("Drehmaschine P2", p, p2, drehpunkte, 40)
st = p.stellungen((20, 0, 30), p2, 40, FreeCAD.Vector())
revolver = next(a for a in st if vf.namen(ma, a) == "T")
platz2 = dict(vf.platzstellungen(p.verfahren, ma, revolver))["P2"]
pruefe(nahe(st[revolver], platz2), f"Revolver auf P2: {st[revolver]} statt {platz2}")
c1 = next(a for a in st if vf.namen(ma, a) == "C1")
pruefe(nahe(st[c1], 0), f"C ohne Angabe auf 0: {st[c1]}")
# X im Job zeigt wie X1: Ein größeres X fährt nur X1.
a = p.stellungen((20, 0, 30), p1, 40, FreeCAD.Vector())
b = p.stellungen((30, 0, 30), p1, 40, FreeCAD.Vector())
aenderung = {vf.namen(ma, k): round(b[k] - a[k], 6) for k in a if abs(b[k] - a[k]) > 1e-9}
pruefe(aenderung == {"X1": 10}, f"X 20 → 30 fährt: {aenderung}")
teil, job, op = neuer_job(["G0 X40 Y0 Z80", "G1 X20 Z-10", "G1 X0"], "Drehteil")
e = p.pruefe_job(job)  # Nullpunkt: Rohteil mittig auf dem Futter
pruefe(not any("zeigt zum Werkstück" in h for h in e.hinweise), f"Drehmaschine Z: {e.hinweise}")
op.ToolController.ToolNumber = 20
teil.recompute()
e = p.pruefe_job(job)
pruefe(
    e.hinweise == ["„Eigene“: Für T20 gibt es am Revolver T keinen Platz P20 – übergangen."],
    f"Platz fehlt: {e.hinweise}",
)
pruefe(e.punkte == 0 and not e.bereiche, "ohne Platz keine Punkte")
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)

# --- Drehmaschine mit schräger Y-Achse (30°): dieselben Zahlen wie „wie im Programm“ ----------
masse = beispielmaschine.DrehmaschinenMasse(y_winkel=30)
asm, ma = beispielmaschine.drehmaschine(masse)
p = rw.Pruefung(asm, ma)
p1 = p.werkzeugaufnahme(1)
trifft("schräge Y-Achse", p, p1, [(20, 0, 30), (25, 10, 40), (15, -20, 5)], 40)
a = p.stellungen((20, 0, 30), p1, 40, FreeCAD.Vector())
b = p.stellungen((20, 10, 30), p1, 40, FreeCAD.Vector())
aenderung = {vf.namen(ma, k): b[k] - a[k] for k in a if abs(b[k] - a[k]) > 1e-9}
x1, y1 = sa.schlitten_aus_programm(30, 0, 10)
pruefe(
    set(aenderung) == {"X1", "Y1"}
    and nahe(abs(aenderung["Y1"]), abs(y1))
    and nahe(abs(aenderung["X1"]), abs(x1)),
    f"Y 0 → 10 bei 30°: {aenderung} statt ±{x1}, ±{y1}",
)
FreeCAD.closeDocument(asm.Document.Name)

# --- 5-Achs-Fräsen: Rundachsen aus der Bahn -------------------------------------------------
for bauplan in (
    beispielmaschine.fuenfachs_tisch_tisch,
    beispielmaschine.fuenfachs_kopf_tisch,
    beispielmaschine.fuenfachs_kopf_kopf,
):
    asm, ma = bauplan()
    p = rw.Pruefung(asm, ma)
    aufnahme = p.werkzeugaufnahme(1)
    buchstaben = sorted(
        m.programmname(b) for b in m.betriebsarten(ma) if b.Art == m.ART_POSITIONIEREN
    )
    for rund in ({}, dict(zip(buchstaben, (30.0, -45.0), strict=True))):
        trifft(bauplan.__name__, p, aufnahme, [(0, 0, 0), (40, -25, 10)], 60, rund=rund)
        st = p.stellungen((0, 0, 0), aufnahme, 60, FreeCAD.Vector(), rund)
        for buchstabe, grad in rund.items():
            achse = next(a for a in st if vf.namen(ma, a) == f"{buchstabe}1")
            pruefe(
                nahe(st[achse], grad), f"{bauplan.__name__}: {buchstabe} {st[achse]} statt {grad}"
            )
    FreeCAD.closeDocument(asm.Document.Name)

# Eine Rundachse über ihrer Grenze (A1: −120 … 120), in Schritten gedreht.
asm, ma = beispielmaschine.fuenfachs_tisch_tisch()
p = rw.Pruefung(asm, ma)
teil, job, op = neuer_job(["G0 X0 Y0 Z50 A0", "G1 A130 F500", "G0 A0"], "Schwenkteil")
e = p.pruefe_job(job, FreeCAD.Vector())
a1 = [u for u in e.ueberschreitungen if u.name == "A1"]
pruefe(
    len(a1) == 1
    and nahe(a1[0].stellung, 130)
    and a1[0].text().endswith("die Grenze ist 120.0° (bei X 0, Y 0, Z 50, A 130).")
    and bereich(e, "A1") == (0.0, 130.0),
    f"A 130: {texte(e)} {bereich(e, 'A1')}",
)
pruefe(e.punkte == 1 + 130 + 130, f"A in 1°-Schritten: {e.punkte}")
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)

# --- Drehmaschine ohne Y: nur Punkte in der Ebene von X und Z --------------------------------
asm, ma = beispielmaschinen.drehmaschine_komplett()
p = rw.Pruefung(asm, ma)
platz = p.werkzeugaufnahme(1)
achsen = {vf.namen(ma, a): a for a in p.kette.achsen}
# Wo steht die Spitze, wenn X1 um 10 und Z1 um 20 fährt (C4 auf 0, wie ohne C in der
# Bahn)? Diesen Punkt im Job erreicht sie.
verfahren = vf.Verfahren(asm, p.kette)
verfahren.setze(achsen["X1"], verfahren.stellung(achsen["X1"]) + 10)
verfahren.setze(achsen["Z1"], verfahren.stellung(achsen["Z1"]) + 20)
verfahren.setze(achsen["C4"], 0.0, grenzen=False)
spitze = m.globale_platzierung(platz.Lcs).multVec(FreeCAD.Vector(0, 0, -30))
job_lage = m.globale_platzierung(p.werkstueckaufnahme.Lcs)
verfahren.grundstellung()
punkt = tuple(job_lage.inverse().multVec(spitze))
st = p.stellungen(punkt, platz, 30, FreeCAD.Vector())
pruefe(
    st is not None
    and nahe(st[achsen["X1"]], verfahren.start[achsen["X1"]] + 10)
    and nahe(st[achsen["Z1"]], verfahren.start[achsen["Z1"]] + 20),
    f"ohne Y, erreichbar: {st and namen(p, st)}",
)
# Quer zu X1 und Z1 kommt das Werkzeug nicht hin.
quer = achsen["X1"].richtung.cross(achsen["Z1"].richtung)
quer = job_lage.Rotation.inverted().multVec(quer)
daneben = tuple(FreeCAD.Vector(*punkt) + quer * 5)
pruefe(
    p.stellungen(daneben, platz, 30, FreeCAD.Vector()) is None, "ohne Y: 5 mm daneben erreichbar?"
)
zeilen = [
    "G0 X{:.4f} Y{:.4f} Z{:.4f}".format(*punkt),
    "G1 X{:.4f} Y{:.4f} Z{:.4f}".format(*daneben),
]
teil, job, op = neuer_job(zeilen, "OhneY")
e = p.pruefe_job(job, FreeCAD.Vector())
pruefe(
    any(
        h.startswith("In „Eigene“ kommt das Werkzeug nicht überall hin") and "1 von 2 Punkten" in h
        for h in e.hinweise
    ),
    f"ohne Y, Hinweis: {e.hinweise}",
)
pruefe(e.punkte == 1, f"ohne Y, Punkte: {e.punkte}")
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)

# --- Texte ---------------------------------------------------------------------------------------
pruefe(
    rw.punkt_text({"X": 450, "Y": 0, "Z": -5.5, "A": 0, "B": 0, "C": 0}) == "X 450, Y 0, Z −5.5", ""
)
pruefe(
    rw.punkt_text({"X": 1.234, "Y": -0.004, "Z": 0, "A": 0, "B": 90, "C": 0})
    == "X 1.23, Y 0, Z 0, B 90",
    "",
)
pruefe(rw.weg_text(-5.773) == "−5.77 mm", rw.weg_text(-5.773))
pruefe(rw.winkel_text(-0.04) == "0.0°", rw.winkel_text(-0.04))
pruefe(math.isclose(rw.DREH_SCHRITT, 1.0), "1°-Schritte")

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
