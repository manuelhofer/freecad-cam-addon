# Prüft 3+2 (W-014 F1, Spezifikation Strategien 15): die Ebene einer schrägen Fläche, die
# Rundachsen dafür – aus der Kette der drei 5-Achs-Beispielmaschinen und ohne Maschine –, die
# Punkte ins Programm ohne Schwenkzyklus (die Spitze steht am gedrehten Werkstück, wo sie soll)
# und die Winkel für CYCLE800. F2: die Ebene als Job – das Modell mit der Schräge oben, das Rohteil
# des Grundjobs mit gedreht, und das Räumen fräst die Schräge wie jede Fläche nach oben.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part
import Path

from camaddon import beispielmaschine, sprache
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon.kinematik import Kinematik

V = FreeCAD.Vector
fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nahe(a, b, genau=1e-6):
    return abs(a - b) <= genau


def nahe_v(a, b, genau=1e-6):
    return all(abs(x - y) <= genau for x, y in zip(a, b, strict=True))


sprache.setze_sprache("de")

# --- Das Teil: ein Block 100 × 60 × 40 mit einer Schräge vorn oben, 30° gegen die Waagerechte --
NEIGUNG = 30.0
t = math.tan(math.radians(NEIGUNG))
keil = Part.Face(
    Part.makePolygon(
        [V(-1, -1, 25 - t), V(-1, 27, 25 + 27 * t), V(-1, 27, 60), V(-1, -1, 60), V(-1, -1, 25 - t)]
    )
).extrude(V(102, 0, 0))
teil = Part.makeBox(100, 60, 40).cut(keil).removeSplitter()
schraege = next(
    f"Face{i + 1}"
    for i, f in enumerate(teil.Faces)
    if sw.aussennormale(f) is not None and nahe(sw.aussennormale(f).y, -math.sin(math.radians(30)))
)
n_soll = V(0, -math.sin(math.radians(NEIGUNG)), math.cos(math.radians(NEIGUNG)))

# --- Die Ebene -------------------------------------------------------------------------------
e = sw.ebene_aus_flaeche(teil, schraege)
n = sw.normale_der(e)
pruefe(nahe_v(n, n_soll), f"Normale {n}")
x = e.Rotation.multVec(V(1, 0, 0))
pruefe(nahe_v(x, (1, 0, 0)), f"X der Ebene {x}")
flaeche = teil.getElement(schraege)
pruefe(abs((e.Base - flaeche.Vertexes[0].Point).dot(n)) < 1e-9, "Ursprung nicht auf der Ebene")
pruefe(nahe(sw.schwenkwinkel(e), NEIGUNG), f"Schwenkwinkel {sw.schwenkwinkel(e)}")
# Das Teil in der Ebene: die Schräge zeigt nach oben, ihre Punkte liegen auf z 0.
lokal = flaeche.copy()
lokal.Placement = e.inverse().multiply(lokal.Placement)
pruefe(nahe(lokal.BoundBox.ZMin, 0.0) and nahe(lokal.BoundBox.ZMax, 0.0), f"lokal {lokal.BoundBox}")
pruefe(nahe_v(sw.aussennormale(lokal), (0, 0, 1)), "lokal nicht nach oben")
try:
    sw.ebene_aus_flaeche(Part.makeSphere(5), "Face1")
except ValueError as grund:
    pruefe("eben" in str(grund), f"Kugel: {grund}")
else:
    pruefe(False, "Kugel als Ebene")
# Die Wand einer Bohrung: die Achse zum offenen Ende. Schräg (30° gegen Z) in einen Block
# 60 × 40 × 30, 15 tief mit Bohrspitze; senkrecht durch; von unten, sacklochtief.


def wand(form):
    return next(
        f"Face{i + 1}" for i, f in enumerate(form.Faces) if isinstance(f.Surface, Part.Cylinder)
    )


achse = V(math.sin(math.radians(30.0)), 0, math.cos(math.radians(30.0)))
eintritt = V(30, 20, 30)
grund = eintritt - achse * 15.0
bohrung = Part.makeCylinder(3, 35, grund, achse).fuse(
    Part.makeCone(3, 0, 3 / math.tan(math.radians(59.0)), grund, achse * -1)
)
schraeg = Part.makeBox(60, 40, 30).cut(bohrung)
lage = sw.ebene_aus_flaeche(schraeg, wand(schraeg))
pruefe(nahe_v(sw.normale_der(lage), achse, 1e-9), f"schräge Bohrung: {sw.normale_der(lage)}")
pruefe(nahe(sw.schwenkwinkel(lage), 30.0, 1e-6), f"schräge Bohrung: {sw.schwenkwinkel(lage)}°")
pruefe(
    abs((lage.Base - eintritt).dot(achse)) < 3.0 * math.tan(math.radians(30.0)) + 1e-6,
    f"schräge Bohrung: Ebene nicht am Eintritt ({lage.Base})",
)
durch = Part.makeBox(40, 40, 20).cut(Part.makeCylinder(4, 30, V(20, 20, -5)))
lage = sw.ebene_aus_flaeche(durch, wand(durch))
pruefe(nahe_v(sw.normale_der(lage), (0, 0, 1)), f"Durchgangsbohrung: {sw.normale_der(lage)}")
unten = Part.makeBox(40, 40, 20).cut(Part.makeCylinder(4, 15, V(20, 20, -5)))
lage = sw.ebene_aus_flaeche(unten, wand(unten))
pruefe(
    nahe_v(sw.normale_der(lage), (0, 0, -1)) and nahe(lage.Base.z, 0.0),
    f"Bohrung von unten: {sw.normale_der(lage)}, {lage.Base}",
)
# Ebene parallel zu X: X des Grundjobs steht senkrecht – dann Y.
seite = sw.ebene(V(1, 0, 0), V(100, 0, 0))
pruefe(nahe_v(seite.Rotation.multVec(V(1, 0, 0)), (0, 1, 0)), "Seite: X der Ebene nicht Y")
pruefe(nahe_v(seite.Base, (100, 0, 0)), f"Seite: Ursprung {seite.Base}")

# --- CYCLE800: achsweise Z, Y, X -------------------------------------------------------------
punkt, winkel = sw.zyklus_winkel(e)
pruefe(nahe_v(winkel, (0.0, 0.0, NEIGUNG), 1e-6), f"CYCLE800-Winkel {winkel}")
schief = sw.ebene(V(1, 1, 1), V(0, 0, 0))
punkt, (a_z, b_y, c_x) = sw.zyklus_winkel(schief)
nachgebaut = (
    FreeCAD.Rotation(V(0, 0, 1), a_z)
    .multiply(FreeCAD.Rotation(V(0, 1, 0), b_y))
    .multiply(FreeCAD.Rotation(V(1, 0, 0), c_x))
)
pruefe(nachgebaut.isSame(schief.Rotation, 1e-9), f"ZYX nachgebaut: {a_z}, {b_y}, {c_x}")

# --- Ohne Maschine: Tisch/Tisch A, C, Drehpunkt im Ursprung ------------------------------------
rund = sw.rundachsen_ohne_maschine(n)
pruefe(nahe(rund["A"], -NEIGUNG, 1e-6) and nahe(rund["C"], 0.0, 1e-6), f"ohne Maschine: {rund}")
ab = sw.abbildung_ohne_maschine(rund)
pruefe(nahe_v(ab.richtung(n), (0, 0, 1)), f"ohne Maschine: Normale → {ab.richtung(n)}")
schraeg_oben = sw.rundachsen_ohne_maschine(V(1, 1, 1))
ab2 = sw.abbildung_ohne_maschine(schraeg_oben)
pruefe(
    nahe_v(ab2.richtung(V(1, 1, 1).normalize()), (0, 0, 1)),
    f"ohne Maschine (1,1,1): {schraeg_oben}",
)

# --- Mit Maschine: die drei 5-Achs-Beispiele -------------------------------------------------
LAENGE = 60.0
for bauplan in (
    beispielmaschine.fuenfachs_tisch_tisch,
    beispielmaschine.fuenfachs_kopf_tisch,
    beispielmaschine.fuenfachs_kopf_kopf,
):
    asm, ma = bauplan()
    p = rw.Pruefung(asm, ma)
    aufnahme = p.werkzeugaufnahme(1)
    maschine = sw.Maschine(p, aufnahme, LAENGE, V())
    buchstaben = sorted(a.buchstabe for a in maschine.rundachsen)
    pruefe(len(buchstaben) == 2, f"{bauplan.__name__}: Rundachsen {buchstaben}")
    for normale in (n_soll, V(1, 0, 1).normalize(), V(0, 0, 1)):
        loesungen = maschine.loese(normale)
        if not loesungen:
            pruefe(False, f"{bauplan.__name__}: keine Lösung für {normale}")
            continue
        rund = loesungen[0]
        d = maschine.richtung(rund)
        pruefe(d.dot(normale) > math.cos(math.radians(0.01)), f"{bauplan.__name__}: {rund} → {d}")
        pruefe(
            all(a.erlaubt(rund[a.buchstabe]) for a in maschine.rundachsen),
            f"{bauplan.__name__}: {rund} außerhalb der Grenzen",
        )
        if nahe_v(normale, (0, 0, 1)):
            pruefe(
                all(abs(w) < 1e-3 for w in rund.values()), f"{bauplan.__name__}: senkrecht {rund}"
            )
        abb = maschine.abbildung(rund)
        pruefe(abb is not None, f"{bauplan.__name__}: keine Abbildung")
        if abb is None:
            continue
        # Der Kern: Punkt p am Werkstück → Punkt im Programm (ohne TCPM) → Stellungen mit den
        # Rundachsen der Ebene → die Spitze steht am gedrehten Werkstück auf p.
        kin = Kinematik(p, aufnahme, LAENGE, V())
        for punkt in ((0, 0, 0), (50, 10, 30), (80, 0, 25)):
            programm = abb.punkt(punkt)
            st = kin.stellungen(programm, rund)
            if st is None:
                pruefe(False, f"{bauplan.__name__}: {punkt} nicht erreichbar")
                continue
            am = kin.am_werkstueck(st)
            pruefe(nahe_v(am, punkt, 1e-6), f"{bauplan.__name__} {rund}: Spitze {am} statt {punkt}")
        # Tisch/Tisch: das Werkzeug steht im Programm senkrecht – die Ebene liegt in XY.
        if bauplan is beispielmaschine.fuenfachs_tisch_tisch:
            pruefe(
                nahe_v(abb.richtung(normale), (0, 0, 1), 1e-6),
                f"Tisch/Tisch: {abb.richtung(normale)}",
            )
    FreeCAD.closeDocument(asm.Document.Name)

# --- Sätze ins Programm ohne Zyklus ------------------------------------------------------------
# Ein Quadrat und ein Halbkreis in der Ebene, ohne Maschine (Tisch/Tisch um den Ursprung).
rund = sw.rundachsen_ohne_maschine(n)
schwenkung = sw.Schwenkung(e, rund, sw.abbildung_ohne_maschine(rund))
pruefe(schwenkung.in_xy(), "ohne Maschine: Ebene nicht in XY")
saetze = [
    Path.Command("G0", {"X": 10.0, "Y": 5.0, "Z": 10.0}),
    Path.Command("G1", {"Z": -2.0, "F": 300.0}),
    Path.Command("G1", {"X": 30.0}),
    Path.Command("G2", {"X": 50.0, "Y": 5.0, "I": 10.0, "J": 0.0}),
    Path.Command("G81", {"X": 20.0, "Y": 10.0, "Z": -5.0, "R": 2.0}),
    Path.Command("G0", {"Z": 10.0}),
]
programm = sw.befehle_ohne_zyklus(saetze, schwenkung)
pruefe(
    programm[0].Name == "G0" and nahe(programm[0].Parameters["A"], rund["A"]),
    f"erster Satz: {programm[0].toGCode()}",
)
gesamt = schwenkung.gesamt()
pruefe(
    nahe_v([programm[3].Parameters[k] for k in "XYZ"], gesamt.punkt((30.0, 5.0, -2.0)), 1e-9),
    f"Gerade: {programm[3].toGCode()}",
)
bogen = programm[4]
anfang = gesamt.punkt((30.0, 5.0, -2.0))
mitte = gesamt.punkt((40.0, 5.0, -2.0))
ende = [bogen.Parameters[k] for k in "XYZ"]
pruefe(
    bogen.Name == "G2"
    and nahe(bogen.Parameters["I"], mitte[0] - anfang[0], 1e-9)
    and nahe(bogen.Parameters["J"], mitte[1] - anfang[1], 1e-9)
    and nahe(math.dist(ende[:2], mitte[:2]), 10.0, 1e-9),
    f"Bogen: {bogen.toGCode()}",
)
zyklus = programm[5]
pruefe(
    zyklus.Name == "G81" and nahe(zyklus.Parameters["R"] - zyklus.Parameters["Z"], 7.0, 1e-9),
    f"Bohrzyklus: {zyklus.toGCode()}",
)
# Liegt die Ebene im Programm nicht in XY: der Bogen als Geraden auf dem Kreis, kein Bohrzyklus.
quer = sw.Schwenkung(e, {"B": 30.0}, sw.Abbildung.aus_placement(FreeCAD.Placement()))
pruefe(not quer.in_xy(), "quer in XY?")
geraden = sw.befehle_ohne_zyklus(saetze[:4], quer)
auf_dem_kreis = [c for c in geraden[4:] if c.Name == "G1"]
mitte_job = e.multVec(V(40.0, 5.0, -2.0))
pruefe(
    len(auf_dem_kreis) > 20
    and all(
        nahe(math.dist([c.Parameters[k] for k in "XYZ"], mitte_job), 10.0, 1e-6)
        for c in auf_dem_kreis
    ),
    f"Bogen als Geraden: {len(auf_dem_kreis)} Sätze",
)
# Bohrzyklen quer zur Ebene: ausgeschrieben, die Achse der Ebene entlang. G81 (G98): über dem Loch
# auf der Höhe davor, auf R, im Vorschub auf die Tiefe, zurück auf die Höhe davor.
zurueck_in_ebene = e.inverse()


def in_der_ebene(befehle):
    """[(Befehl, (x, y, z) in der Ebene)] der Sätze mit X, Y, Z."""
    return [
        (c.Name, tuple(round(v, 6) for v in zurueck_in_ebene.multVec(V(*(c.Parameters[k] for k in "XYZ")))))
        for c in befehle
        if all(k in c.Parameters for k in "XYZ")
    ]  # fmt: skip


bohr = [s for s in in_der_ebene(sw.befehle_ohne_zyklus(saetze, quer)) if s[1][:2] == (20.0, 10.0)]
pruefe(
    bohr == [("G0", (20, 10, -2)), ("G0", (20, 10, 2)), ("G1", (20, 10, -5)), ("G0", (20, 10, -2)),
             ("G0", (20, 10, 10))],
    f"G81 ausgeschrieben: {bohr}",
)  # fmt: skip
# G83 mit G99 in Hüben von 4: zwischen ihnen auf R, wieder hinab bis 0,5 über die letzte Tiefe;
# danach auf R – und ein „G0 X Y“ ohne Z fährt dort, nicht auf der Tiefe.
tief = [
    Path.Command("G0", {"X": 0.0, "Y": 0.0, "Z": 10.0}),
    Path.Command("G99"),
    Path.Command("G83", {"X": 5.0, "Y": 5.0, "Z": -9.0, "R": 2.0, "Q": 4.0, "F": 1.0}),
    Path.Command("G83", {"X": 15.0, "Y": 5.0, "Z": -9.0, "R": 2.0, "Q": 4.0, "F": 1.0}),
    Path.Command("G80"),
    Path.Command("G0", {"X": 30.0, "Y": 5.0}),
]
gebohrt = sw.befehle_ohne_zyklus(tief, quer)
hoehen = [p[2] for _n, p in in_der_ebene(gebohrt) if p[:2] == (5.0, 5.0)]
pruefe(hoehen == [10, 2, -2, 2, -1.5, -6, 2, -5.5, -9, 2], f"G83 erstes Loch: {hoehen}")
hoehen = [p[2] for _n, p in in_der_ebene(gebohrt) if p[:2] == (15.0, 5.0)]
pruefe(hoehen == [2, -2, 2, -1.5, -6, 2, -5.5, -9, 2], f"G83 zweites Loch: {hoehen}")
pruefe(
    in_der_ebene(gebohrt)[-1] == ("G0", (30, 5, 2)), f"nach dem Zyklus: {in_der_ebene(gebohrt)[-1]}"
)
pruefe(
    not any(c.Name in ("G80", "G83", "G99") for c in gebohrt)
    and all(c.Parameters.get("F") == 1.0 for c in gebohrt if c.Name == "G1"),
    f"G83 ausgeschrieben: {[c.toGCode() for c in gebohrt]}",
)
try:
    sw.befehle_ohne_zyklus([Path.Command("G86", {"X": 1.0, "Y": 1.0, "Z": -3.0, "R": 2.0})], quer)
except ValueError as grund:
    pruefe("Bohr" in str(grund), f"G86 quer: {grund}")
else:
    pruefe(False, "G86 quer zur Ebene ohne Fehler")
# Beginnt die Ebene mit „G0 Z…“ ohne X, Y (wie jede Operation in FreeCAD): kein erfundener Punkt
# X0 Y0 der Ebene – auf der Schwenkhöhe über den ersten bekannten Punkt, dann hinunter.
hoch = sw.Schwenkung(e, rund, sw.abbildung_ohne_maschine(rund), hoehe=120.0)
anfang = sw.befehle_ohne_zyklus(
    [
        Path.Command("G0", {"Z": 10.0}),
        Path.Command("G0", {"X": 10.0, "Y": 5.0}),
        Path.Command("G1", {"Z": -2.0, "F": 300.0}),
    ],
    hoch,
)
wege = [[c.Parameters.get(k) for k in "XYZ"] for c in anfang if "A" not in c.Parameters]
soll = gesamt.punkt((10.0, 5.0, 10.0))
pruefe(
    len(wege) == 4
    and wege[0] == [None, None, 120.0]
    and nahe_v(wege[1], (soll[0], soll[1], 120.0), 1e-9)
    and nahe_v(wege[2], soll, 1e-9),
    f"Anfang der Ebene: {[c.toGCode() for c in anfang]}",
)

# --- F2: die Ebene als Job ----------------------------------------------------------------------
import Path.Main.Job as PathJob  # noqa: E402

from camaddon import job_schnittwerte as js  # noqa: E402
from camaddon import materialstand as mst  # noqa: E402
from camaddon import pruefstand as ps  # noqa: E402
from camaddon import raeumen as ra  # noqa: E402
from camaddon import uebergabe_werkzeuge as ue  # noqa: E402
from camaddon import vierachs_rohteil as vr  # noqa: E402
from camaddon import werkzeuge as wz  # noqa: E402

fraeser = wz.standardwerkzeug()
ue.uebergeben(wz.Bibliothek([fraeser]))
einsatz = next(e for e in fraeser.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
doc = FreeCAD.newDocument("Schraege")
objekt = doc.addObject("Part::Feature", "Block")
objekt.Shape = teil
doc.recompute()
grundjob = PathJob.Create("Job", [objekt])
grundjob.Stock.ExtZpos = 1.0
doc.recompute()
rohteil_grund = grundjob.Stock.Shape.copy()
planjob = sw.lege_an(grundjob, schraege)
pruefe(sw.ist_ebene(planjob) and not sw.ist_ebene(grundjob), "Ebene am Job")
pruefe(planjob.Grundjob == grundjob and planjob.Flaeche == schraege, "Grundjob, Fläche")
pruefe(sw.rundachsen_von(planjob) == {"A": -NEIGUNG, "C": 0.0}, f"Rundachsen {planjob.Rundachsen}")
pruefe(planjob.Ebene.isSame(e, 1e-9), "Ebene am Job nicht die der Fläche")
# Ohne Fläche, aus Winkeln: 15° geneigt, der Kopf nach +Y – die Ebene durch den Nullpunkt.
schief_job = sw.lege_an(grundjob, None, winkel=(15.0, 90.0))
pruefe(
    schief_job.Flaeche == ""
    and sw.rundachsen_von(schief_job) == {"A": 15.0, "C": 0.0}
    and "15° nach 90°" in schief_job.Label
    and nahe_v(sw.normale_der(schief_job.Ebene), sw.normale_aus_winkeln(15.0, 90.0))
    and nahe_v(sw.normale_aus_winkeln(15.0, 90.0), (0, math.sin(math.radians(15)), math.cos(math.radians(15))))
    and nahe_v(schief_job.Ebene.Base, (0, 0, 0)),
    f"aus Winkeln: {schief_job.Label}, {schief_job.Rundachsen}, {schief_job.Ebene}",
)  # fmt: skip
doc.removeObject(schief_job.Name)
# Im Job der Ebene zeigt die Schräge nach oben und liegt auf z 0.
klon = vr.modell(planjob)
lokal = klon.Shape.getElement(schraege)
pruefe(
    nahe(lokal.BoundBox.ZMin, 0.0)
    and nahe(lokal.BoundBox.ZMax, 0.0)
    and nahe_v(sw.aussennormale(lokal), (0, 0, 1)),
    f"Schräge im Job der Ebene: {lokal.BoundBox}",
)
# Das Rohteil ist das des Grundjobs, mit gedreht – gleich groß, an derselben Stelle am Teil.
rohteil_ebene = planjob.Stock.Shape
pruefe(nahe(rohteil_ebene.Volume, rohteil_grund.Volume, 1e-6), "Rohteil: anderes Volumen")
zurueck = rohteil_ebene.copy()
zurueck.Placement = e.multiply(zurueck.Placement)
pruefe(
    all(
        min(math.dist(v.Point, w.Point) for w in rohteil_grund.Vertexes) < 1e-6
        for v in zurueck.Vertexes
    ),
    "Rohteil der Ebene nicht das des Grundjobs",
)
pruefe(not mst._ist_quader(planjob.Stock), "gedrehtes Rohteil als Kasten")
stand = mst.fuer(planjob)
pruefe(stand is not None, "kein Materialstand in der Ebene")
if stand is not None:
    # Über der Mitte der Schräge steht das Rohteil so hoch wie die Ecke des Blocks über der
    # Schräge – plus 1 mm Aufmaß oben, schräg gemessen.
    mitte = lokal.CenterOfMass
    hoehe = float(stand.hoehen_an([mitte.x], [mitte.y])[0][0])
    pruefe(5.0 < hoehe < 20.0, f"Rohteil über der Schräge: {hoehe:.2f} mm")

# Räumen auf der Schräge – wie auf jeder Fläche nach oben.
tc = js.controller_ohne_transaktion(doc, planjob, fraeser, einsatz)
doc.recompute()
op = ra.lege_an(planjob, tc, einsatz.ap, einsatz.ae, flaechen=[schraege])
doc.recompute()
pruefe(
    op.Ebenen == 1 and len(op.Path.Commands) > 20, f"Räumen: {op.Ebenen} Flächen, {op.Gerechnet}"
)
bahn = ra.rechne(op, planjob, planjob.Model.Group, 902.0, 270.0)
bb = rohteil_ebene.BoundBox
k = ps.messen(
    [ps.Bahnlauf(bahn.punkte, 902.0, 270.0)], klon.Shape, (bb.XMin, bb.XMax, bb.YMin, bb.YMax),
    bb.ZMax, ra.vs.form_des_controllers(tc), einsatz.ae, einsatz.ap, ebenen_z=[0.0],
    aufmass=0.3,
)  # fmt: skip
pruefe(k.einschnitt > -0.02, f"Räumen der Schräge schneidet ins Teil: {ps.zeile(k)}")
pruefe(k.rest < 0.5, f"Räumen der Schräge lässt stehen: {ps.zeile(k)}")
print(f"Räumen auf der Schräge: {bahn.zeit:.2f} min, {bahn.variante} – {ps.zeile(k)}")

# --- F3: das Programm ----------------------------------------------------------------------------
from camaddon import postprozessor as pp  # noqa: E402

teile = pp.abschnitte(grundjob)
pruefe(
    len(teile) == 1 and teile[0].schwenkung is not None and teile[0].name == op.Label,
    f"Abschnitte des Grundjobs: {[(a.name, a.schwenkung) for a in teile]}",
)
pruefe(pp.abschnitte(grundjob, mit_ebenen=False) == [], "Grundjob ohne Ebenen nicht leer")
pruefe(len(pp.abschnitte(planjob)) == 1, "Job der Ebene allein")
info = pp.Maschineninfo("5-Achs")
# Siemens: CYCLE800 mit dem Ursprung der Ebene und den Winkeln achsweise Z, Y, X; die Sätze in
# Koordinaten der Ebene, wie die Operation sie hat; am Ende zurück.
siemens = pp.programm(teile, pp.steuerung("siemens"), info, "Block").zeilen
x0, y0, z0 = (f"{v:.3f}" for v in e.Base)
zyklus = f'CYCLE800(1,"",0,27,{x0},{y0},{z0},0.000,0.000,30.000,0,0,0,-1,0,1)'
pruefe(zyklus in siemens, f"kein {zyklus}: {[z for z in siemens if 'CYCLE' in z]}")
pruefe(
    siemens.index(zyklus) < next(i for i, z in enumerate(siemens) if z.startswith("M3")),
    "CYCLE800 nach dem Spindelstart",
)
pruefe("CYCLE800()" in siemens[-5:], f"Ende: {siemens[-6:]}")
pruefe("; Ebene geschwenkt: A-30 C0" in siemens, "Kommentar zur Ebene")
erster = next(c for c in op.Path.Commands if c.Name in ("G1", "G01"))
pruefe(
    any(z.startswith("G1") and f"X{erster.Parameters['X']:.3f}" in z for z in siemens),
    "Siemens: Sätze nicht in Koordinaten der Ebene",
)
pruefe(not any(" A" in z or "C=" in z for z in siemens if z.startswith("G")), "Siemens: Rundachsen")
# Ohne Zyklus (LinuxCNC; Siemens mit Haken aus): die Rundachsen und gerechnete X, Y, Z.
schwenkung = teile[0].schwenkung
gesamt = schwenkung.gesamt()
for s in (pp.steuerung("linuxcnc"), pp.steuerung("siemens", {"schwenkzyklus": False})):
    zeilen = pp.programm(teile, s, info, "Block").zeilen
    pruefe(not any("CYCLE800" in z for z in zeilen), f"{s.name} ohne Zyklus: CYCLE800")
    ein = next((z for z in zeilen if z.startswith("G0 A")), "")
    pruefe(ein.startswith("G0 A-30.000 C0.000"), f"{s.name}: Rundachsen {ein!r}")
    pruefe(zeilen.count("G0 A0.000 C0.000") == 1, f"{s.name}: Rundachsen nicht zurück")
    # Vor jedem Schwenken hoch genug, dass sich das Rohteil frei dreht – auch ohne Wechselpunkt.
    for k, z in enumerate(zeilen):
        if z.startswith("G0 A"):
            davor = zeilen[k - 1]
            hoch = float(davor.split("Z")[1]) if davor.startswith("G0 Z") else -math.inf
            pruefe(
                hoch >= schwenkung.hoehe - 1e-3 and hoch > rohteil_grund.BoundBox.ZMax + 10.0,
                f"{s.name}: vor {z!r} nicht hoch genug: {davor!r}",
            )
    soll = gesamt.punkt([float(erster.Parameters.get(k, 0.0)) for k in "XYZ"])
    pruefe(
        any(z.startswith("G1") and f"X{soll[0]:.3f}" in z for z in zeilen),
        f"{s.name}: erster Satz nicht gerechnet ({soll})",
    )

# --- F4: auf der Maschine prüfen – an allen drei 5-Achs-Beispielen ---------------------------------
from camaddon import abfahren as ab  # noqa: E402

for bauplan, schwenkachse in (
    (beispielmaschine.fuenfachs_tisch_tisch, "A1"),
    (beispielmaschine.fuenfachs_kopf_tisch, "B1"),
    (beispielmaschine.fuenfachs_kopf_kopf, "A1"),
):
    name = bauplan.__name__
    asm, ma = bauplan()
    p = rw.Pruefung(asm, ma)
    null = rw.nullpunkt(grundjob)
    pruefe(rw.nullpunkt(planjob) == null, "Nullpunkt der Ebene nicht der des Grundjobs")
    pruefe(rw.grundjob_von(planjob) is grundjob, "grundjob_von")
    ergebnis = p.pruefe_job(planjob, null)
    pruefe(
        not [h for h in ergebnis.hinweise if "Ebene" in h or "Rundachsen" in h],
        f"{name}: Prüfen der Ebene: {ergebnis.hinweise}",
    )
    schwenk = [b for b in ergebnis.bereiche if b.name == schwenkachse]
    pruefe(
        schwenk and nahe(max(abs(schwenk[0].von), abs(schwenk[0].bis)), NEIGUNG, 1e-4),
        f"{name}: {[(b.name, b.von, b.bis) for b in ergebnis.bereiche]}",
    )
    fahrt = ab.abfahrt(p, grundjob, null)
    nummer = next(i for i, o in enumerate(fahrt.operationen) if o.name == op.Label)
    punkte = fahrt.am_werkstueck()
    zurueck_in_ebene = e.inverse()
    tiefste = math.inf
    anzahl = 0
    for station, am in zip(fahrt.stationen, punkte, strict=True):
        if station.operation != nummer or station.ziel or station.eilgang:
            continue
        if station.stellungen is None:
            continue
        lokal = zurueck_in_ebene.multVec(V(*am))
        tiefste = min(tiefste, lokal.z)
        anzahl += 1
    pruefe(anzahl > 50, f"{name}: {anzahl} Stationen im Vorschub")
    pruefe(tiefste > -1e-6, f"{name}: die Spitze {tiefste:.4f} mm unter der Schräge")
    # Der erste Satz im Vorschub der Operation: am gedrehten Werkstück genau dort, wo die Bahn
    # der Ebene ihn hat – durch den Grundjob, die Rundachsen und die Linearachsen ohne TCPM.
    erster_lokal = [float(erster.Parameters.get(k, 0.0)) for k in "XYZ"]
    soll = e.multVec(V(*erster_lokal))
    pruefe(
        any(math.dist(am, soll) < 1e-5 for am in punkte),
        f"{name}: erster Satz am Werkstück nicht bei {soll}",
    )
    FreeCAD.closeDocument(asm.Document.Name)
FreeCAD.closeDocument(doc.Name)

# --- F6: was der Grundjob weggefräst hat, kennt die Ebene ------------------------------------------
doc = FreeCAD.newDocument("Vorher")
objekt = doc.addObject("Part::Feature", "Block")
objekt.Shape = teil
doc.recompute()
grundjob = PathJob.Create("Job", [objekt])
grundjob.Stock.ExtZpos = 3.0
doc.recompute()
planjob = sw.lege_an(grundjob, schraege)
tc = js.controller_ohne_transaktion(doc, planjob, fraeser, einsatz)
doc.recompute()
op_ebene = ra.lege_an(planjob, tc, einsatz.ap, einsatz.ae, flaechen=[schraege])
doc.recompute()
vorher = mst.fuer(planjob, vor=op_ebene)  # vor dem Räumen der Schräge
zeit_vorher = ra.rechne(op_ebene, planjob, planjob.Model.Group, 902.0, 270.0).zeit
# Der Grundjob räumt die Oberseite (z 40): Über der Schräge fehlen dann 3 mm Rohteil.
oben = next(
    f"Face{i + 1}"
    for i, f in enumerate(vr.modell(grundjob).Shape.Faces)
    if sw.aussennormale(f) is not None
    and nahe(f.BoundBox.ZMin, 40.0)
    and nahe(f.BoundBox.ZMax, 40.0)
)
tc_g = js.controller_ohne_transaktion(doc, grundjob, fraeser, einsatz)
doc.recompute()
ra.lege_an(grundjob, tc_g, einsatz.ap, einsatz.ae, flaechen=[oben])
doc.recompute()
stand_grund = mst.fuer(grundjob)
nachher = mst.fuer(planjob, vor=op_ebene)
pruefe(nachher is not None and nachher.kennung != vorher.kennung, "Kennung der Ebene gleich")
if nachher is not None and stand_grund is not None:
    endlich = np.isfinite(nachher.quader.h) & np.isfinite(vorher.quader.h)
    pruefe(
        np.all(nachher.quader.h[endlich] <= vorher.quader.h[endlich] + 1e-9),
        "die Ebene sieht mehr Material als vorher",
    )
    weniger = float(np.max(vorher.quader.h[endlich] - nachher.quader.h[endlich]))
    pruefe(weniger > 1.0, f"die Ebene sieht nicht, was der Grundjob weggeräumt hat: {weniger:.2f}")
    # Stichprobe: knapp unter der Oberkante der Ebene steht im Grundjob Material, darüber nicht
    # (2,5 mm: Am Rand des Rasters zählt die nächste Zelle mit – lieber Material sehen; an der
    # Stirnseite des Rohteils liegt „darüber“ schräg vor ihm).
    xs, ys = np.meshgrid(nachher.quader.x, nachher.quader.y, indexing="ij")
    wahl = np.flatnonzero(np.isfinite(nachher.quader.h).ravel())[::97]
    unter = über = 0
    for k in wahl:
        x_, y_, h_ = xs.ravel()[k], ys.ravel()[k], nachher.quader.h.ravel()[k]
        for dz, zaehle in ((-0.5, "unter"), (2.5, "über")):
            p_ = e.multVec(V(x_, y_, h_ + dz))
            drin = mst._im_stand(stand_grund, np.array([[p_.x, p_.y, p_.z]]))[0]
            if zaehle == "unter" and drin:
                unter += 1
            if zaehle == "über" and not drin:
                über += 1
    pruefe(unter >= 0.95 * len(wahl), f"unter der Oberkante: {unter} von {len(wahl)} im Material")
    pruefe(über >= 0.95 * len(wahl), f"über der Oberkante: {über} von {len(wahl)} frei")
zeit_nachher = ra.rechne(op_ebene, planjob, planjob.Model.Group, 902.0, 270.0).zeit
pruefe(
    zeit_nachher < zeit_vorher, f"Räumen der Schräge: {zeit_vorher:.2f} → {zeit_nachher:.2f} min"
)
print(f"Räumen der Schräge nach dem Grundjob: {zeit_vorher:.2f} → {zeit_nachher:.2f} min")
FreeCAD.closeDocument(doc.Name)

# --- Bohren auf der Schräge: FreeCADs Bohr-Operation im Job der Ebene ----------------------------
from camaddon import bohren as bh  # noqa: E402
from camaddon import bohrung_bahn as bb  # noqa: E402

ORT = V(50.0, 13.0, 0.0)  # in der Ebene
loch = Part.makeCylinder(4.25, 30.0, V(ORT.x, ORT.y, -15.0)).fuse(
    Part.makeCone(
        0.0,
        4.25,
        4.25 / math.tan(math.radians(59.0)),
        V(ORT.x, ORT.y, -15.0 - 4.25 / math.tan(math.radians(59.0))),
    )
)
loch.Placement = e.multiply(loch.Placement)
mit_loch = teil.cut(loch).removeSplitter()
b85 = wz.Werkzeug(
    nummer=2, name="HSS 8,5", art=wz.BOHRER, durchmesser=8.5, schneiden=2, schneidenlaenge=60.0,
    spitzenwinkel=118.0, schneidstoff=wz.HSS,
)  # fmt: skip
b85.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.1)]
ue.uebergeben(wz.Bibliothek([fraeser, b85]))
doc = FreeCAD.newDocument("Bohren")
objekt = doc.addObject("Part::Feature", "Block")
objekt.Shape = mit_loch
doc.recompute()
grundjob = PathJob.Create("Job", [objekt])
grundjob.Stock.ExtZpos = 1.0
doc.recompute()
pruefe(not bb.bohrungen(vr.modell(grundjob).Shape), "die schräge Bohrung im Grundjob als Bohrung")
planjob = sw.lege_an(grundjob, schraege)
klon = vr.modell(planjob)
bohrungen = bb.bohrungen(klon.Shape)
pruefe(len(bohrungen) == 1, f"Bohrungen in der Ebene: {[b.name for b in bohrungen]}")
if bohrungen:
    tc = js.controller_ohne_transaktion(doc, planjob, b85, b85.schnittwerte[wz.ALLE][0])
    bohr_op = bh.lege_an(planjob, tc, [bohrungen[0].name])
    doc.recompute()
    zyklen = [c for c in bohr_op.Path.Commands if c.Name in ("G81", "G83")]
    pruefe(
        len(zyklen) == 1
        and nahe(zyklen[0].Parameters["X"], ORT.x, 1e-3)
        and nahe(zyklen[0].Parameters["Y"], ORT.y, 1e-3)
        and zyklen[0].Parameters["Z"] < -15.0,
        f"Bohren in der Ebene: {[c.toGCode() for c in zyklen]}",
    )
    teile = pp.abschnitte(grundjob)
    lcnc = pp.programm(teile, pp.steuerung("linuxcnc"), pp.Maschineninfo("5-Achs"), "B").zeilen
    soll = teile[0].schwenkung.gesamt().punkt((ORT.x, ORT.y, float(zyklen[0].Parameters["Z"])))
    pruefe(
        any(z.startswith(("G81", "G83")) and f"X{soll[0]:.3f} Y{soll[1]:.3f}" in z for z in lcnc),
        f"LinuxCNC: Bohrzyklus nicht gerechnet ({soll}): {[z for z in lcnc if z.startswith('G8')]}",
    )
    # Am Schwenkkopf (Kopf/Kopf) liegt die Ebene im Programm nicht in XY: der Bohrzyklus
    # ausgeschrieben. Mit der Maschine je Werkzeug (seine Länge) stehen im Programm dieselben
    # Sätze, die „Auf der Maschine prüfen“ fährt – und die Spitze erreicht am gedrehten
    # Werkstück den Grund der Bohrung.
    asm, ma = beispielmaschine.fuenfachs_kopf_kopf()
    p = rw.Pruefung(asm, ma)
    null = rw.nullpunkt(grundjob)
    bib = wz.Bibliothek([fraeser, b85])

    def je_op(o):
        t = o.ToolController
        return sw.Maschine(p, p.werkzeugaufnahme(t.ToolNumber), rw.einspannung(t, bib), null)

    teile_kopf = pp.abschnitte(grundjob, je_op)
    abschnitt = next(t for t in teile_kopf if t.name == bohr_op.Label)
    pruefe(not abschnitt.schwenkung.in_xy(), "Kopf/Kopf: die Ebene im Programm in XY")
    kopf = pp.programm(teile_kopf, pp.steuerung("linuxcnc"), pp.Maschineninfo("5-Achs"), "B")
    pruefe(
        not any(z.startswith(("G81", "G83")) for z in kopf.zeilen)
        and not any("Bohr" in h for h in kopf.hinweise),
        f"Kopf/Kopf: {kopf.hinweise}, {[z for z in kopf.zeilen if z.startswith('G8')]}",
    )
    im_programm = sw.befehle_ohne_zyklus(abschnitt.befehle, abschnitt.schwenkung)
    gefahren = p.befehle(bohr_op, planjob, p.werkzeugaufnahme(2), rw.einspannung(tc, bib), null)
    pruefe(
        [c.Name for c in im_programm] == [c.Name for c in gefahren]
        and all(
            nahe(a.Parameters.get(k, 0.0), b.Parameters.get(k, 0.0), 1e-9)
            for a, b in zip(im_programm, gefahren, strict=True)
            for k in "XYZAC"
        ),
        "Kopf/Kopf: Programm und Prüfen fahren verschieden",
    )
    fahrt = ab.abfahrt(p, grundjob, null, bib)
    nummer = next(i for i, o in enumerate(fahrt.operationen) if o.name == bohr_op.Label)
    grund = e.multVec(V(ORT.x, ORT.y, float(zyklen[0].Parameters["Z"])))
    am_teil = [
        am for s, am in zip(fahrt.stationen, fahrt.am_werkstueck(), strict=True)
        if s.operation == nummer
    ]  # fmt: skip
    pruefe(
        am_teil and min(math.dist(am, grund) for am in am_teil) < 1e-4,
        f"Kopf/Kopf: die Spitze nicht am Grund {grund}",
    )
    FreeCAD.closeDocument(asm.Document.Name)
# Statt der Schräge die Wand der Bohrung angeklickt: dieselbe Ebene, die Bohrung darin senkrecht.
wand_im_grundjob = wand(vr.modell(grundjob).Shape)
ueber_wand = sw.lege_an(grundjob, wand_im_grundjob)
doc.recompute()
pruefe(
    ueber_wand.Ebene.isSame(planjob.Ebene, 1e-6) and ueber_wand.Rundachsen == planjob.Rundachsen,
    f"über die Wand: {ueber_wand.Ebene} statt {planjob.Ebene}",
)
pruefe(len(bb.bohrungen(vr.modell(ueber_wand).Shape)) == 1, "über die Wand: keine Bohrung")
FreeCAD.closeDocument(doc.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
