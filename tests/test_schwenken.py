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
    sw.ebene_aus_flaeche(Part.makeCylinder(5, 10), "Face1")
except ValueError as grund:
    pruefe("eben" in str(grund), f"Mantel: {grund}")
else:
    pruefe(False, "Mantel als Ebene")
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
try:
    sw.befehle_ohne_zyklus(saetze, quer)
except ValueError as grund:
    pruefe("Bohr" in str(grund), f"Zyklus quer: {grund}")
else:
    pruefe(False, "Bohrzyklus quer zur Ebene ohne Fehler")

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
FreeCAD.closeDocument(doc.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
