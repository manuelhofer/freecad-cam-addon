# Prüft die N-Eck-Stange im Schraubstock (n_eck.py, W-018): ein Teil (Quader 30 × 20 × 50, die
# Hochachse längs der Stange) im Grundjob – die Spitze 1 mm hinter der Stirn bei x 0, der Querschnitt
# mittig auf der X-Achse –, die 8-Eck-Stange darum (Schlüsselweite aufgerundet, Länge bis in den
# Schraubstock), die Aufspannungen 2 … 8 als Jobs mit „Umspannen“: keine geschwenkten Ebenen (eigene
# Programme, keine Rundachsen), aber für das Restmaterial der Reihe nach hinter dem Grundjob; je
# Aufspannung zeigt die gedrehte Richtung nach oben, und der Satz fürs Einrichten nennt die Flächen
# an den Backen.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402
import numpy as np  # noqa: E402

from camaddon import n_eck as ne  # noqa: E402
from camaddon import reichweite as rw  # noqa: E402
from camaddon import schwenken as sw  # noqa: E402
from camaddon import sprache  # noqa: E402

sprache.setze_sprache("de")
V = FreeCAD.Vector
fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nahe(a, b, eps=1e-6):
    return abs(a - b) < eps


# --- N: gerade, ab 4 ----------------------------------------------------------------------
for falsch in (3, 5, 7):
    try:
        ne.pruefe_n(falsch)
        pruefe(False, f"N = {falsch} angenommen")
    except ValueError as grund:
        pruefe("gerade" in str(grund), f"Satz zu N = {falsch}: {grund}")
pruefe(
    ne.pruefe_n(6) == 6 and ne.backenflaechen(8, 1) == (1, 5) and ne.backenflaechen(8, 3) == (3, 7),
    "Backen",
)

# --- Das Teil im Grundjob ----------------------------------------------------------------------
dok = FreeCAD.newDocument("NEck")
teil = dok.addObject("Part::Box", "Teil")
teil.Length, teil.Width, teil.Height = 30, 20, 50
dok.recompute()
punkte = np.array([(v.X, v.Y, v.Z) for v in teil.Shape.Vertexes])
job, stange = ne.richte_ein(dok, teil, punkte, n=8, achse="Z")
klon = job.Model.Group[0].Shape.BoundBox
pruefe(nahe(klon.XMin, ne.ZUGABE) and nahe(klon.XLength, 50), f"längs: {klon.XMin} … {klon.XMax}")
pruefe(nahe(klon.YMin, -klon.YMax) and nahe(klon.ZMin, -klon.ZMax), f"quer nicht mittig: {klon}")
# Die Spitze (oben, z 50 im Teil) liegt an der Stirn: der Punkt mit dem kleinsten x hat z 50.
lage = job.Model.Group[0].Placement
spitze = lage.multVec(V(15, 10, 50))
pruefe(nahe(spitze.x, ne.ZUGABE), f"Spitze bei x {spitze.x}")
quer = math.hypot(15, 10)  # halbe Diagonale des Querschnitts 30 × 20
pruefe(stange.schluesselweite == math.ceil(2 * (quer + ne.ZUGABE)), f"SW {stange.schluesselweite}")
pruefe(nahe(stange.laenge, ne.ZUGABE + 50 + ne.ABSTAND + ne.SPANNLAENGE), f"Länge {stange.laenge}")
rohteil = job.Stock.Shape
flaeche = 8 * (stange.schluesselweite / 2) ** 2 * math.tan(math.pi / 8)  # Achteck, Inkreis SW/2
pruefe(nahe(rohteil.Volume / (flaeche * stange.laenge), 1.0, 1e-9), f"Volumen {rohteil.Volume}")
pruefe(rohteil.isInside(V(10, 0, 0), 1e-6, True), "Achse nicht im Rohteil")
# Fläche 1 zeigt nach +Y: Der Punkt mitten auf ihr liegt bei y = SW/2.
pruefe(
    rohteil.isInside(V(10, stange.schluesselweite / 2 - 0.01, 0), 1e-6, True),
    "Fläche 1 nicht bei +Y",
)
pruefe(
    not rohteil.isInside(V(10, stange.schluesselweite / 2 + 0.01, 0), 1e-6, True),
    "Fläche 1 zu weit",
)
pruefe(teil.Shape.BoundBox.ZLength == 50, "das Original verschoben")

# --- Die Aufspannungen 2 … 8 -------------------------------------------------------------------
jobs = ne.aufspannungen_anlegen(job)
pruefe(len(jobs) == 7, f"{len(jobs)} Aufspannungen")
pruefe(all(sw.ist_umspannen(j) and not sw.ist_ebene(j) for j in jobs), "nicht als Umspannen")
pruefe(sw.ebenen_von(job) == [] and sw.aufspannungen_von(job) == jobs, "Ebenen/Aufspannungen")
pruefe(all(j.Rundachsen == "" for j in jobs), "Rundachsen gesetzt")
pruefe(all(rw.grundjob_von(j) is j for j in jobs), "Prüfung nimmt den Grundjob")
pruefe(sw.folge_vor(jobs[2]) == [job, jobs[0], jobs[1]], "Folge fürs Restmaterial")
pruefe(
    [op for op, _e in rw.operationen_mit_ebene(job)] == [],
    "Grundjob mit Operationen der Aufspannungen",
)
for k, j in enumerate(jobs, start=2):
    oben = sw.lage_im_grundjob(j).Rotation.multVec(V(0, 0, 1))
    soll = ne.werkzeugachse(8, k)
    pruefe((oben - soll).Length < 1e-9, f"Aufspannung {k}: oben {oben} statt {soll}")
    laengs = sw.lage_im_grundjob(j).Rotation.multVec(V(1, 0, 0))
    pruefe((laengs - V(1, 0, 0)).Length < 1e-9, f"Aufspannung {k}: Stange nicht längs X")
    pruefe(j.Label.endswith(f"Aufspannung {k} von 8"), f"Name: {j.Label}")
# Aufspannung 3 (90° gedreht): Was im Grundjob nach −Y zeigte, zeigt nach oben – im Job der
# Aufspannung steht die Mitte der Fläche an −Y (Fläche 7) oben auf z = SW/2.
j3 = jobs[1]
mitte_unten = V(10, -stange.schluesselweite / 2, 0)
im_job = sw.lage_im_grundjob(j3).inverse().multVec(mitte_unten)
pruefe(nahe(im_job.z, stange.schluesselweite / 2) and nahe(im_job.y, 0), f"Aufspannung 3: {im_job}")
satz = ne.einrichten_text(j3)
pruefe(
    satz.startswith(
        "Aufspannung 3 von 8: Stange um 90° gegen die erste gedreht, die Flächen 3 und 7"
    ),
    f"Einrichten: {satz!r}",
)
pruefe(ne.einrichten_text(job).startswith("Aufspannung 1 von 8"), "Einrichten Grundjob")

# --- Das Programm: je Aufspannung ein eigenes, ohne Schwenken ----------------------------------
import Path.Op.Custom as PathCustom  # noqa: E402

from camaddon import postprozessor as pp  # noqa: E402

for j, name in ((job, "Oben"), (jobs[0], "Zweite")):
    FreeCAD.setActiveDocument(dok.Name)
    op = PathCustom.Create(name, parentJob=j)
    op.Gcode = ["G0 X10 Y0 Z30", "G1 Z20 F300", "G1 X40", "G0 Z30"]
dok.recompute()
grund_teile = pp.abschnitte(job)
pruefe([a.name for a in grund_teile] == ["Oben"], f"Grundjob: {[a.name for a in grund_teile]}")
teile = pp.abschnitte(jobs[0])
pruefe(
    [a.name for a in teile] == ["Zweite"] and all(a.schwenkung is None for a in teile),
    f"Aufspannung 2: {[(a.name, a.schwenkung) for a in teile]}",
)
programm = pp.programm(
    teile, pp.steuerung("siemens"), pp.Maschineninfo("3-Achs"), "A2",
    einrichten=ne.einrichten_text(jobs[0]),
)  # fmt: skip
zeilen = programm.zeilen
pruefe(
    any("Aufspannung 2 von 8" in z for z in zeilen[:12])
    and programm.hinweise[0].startswith("Aufspannung 2 von 8"),
    f"Einrichten nicht im Kopf: {zeilen[:12]} / {programm.hinweise[:2]}",
)
pruefe(not any("CYCLE800" in z for z in zeilen), "Aufspannung mit CYCLE800")
saetze = [z for z in zeilen if z.strip() and not z.lstrip().startswith((";", "("))]
pruefe(
    not any(w[0] in "ABC" and w[1:2] in "-0123456789" for z in saetze for w in z.split()),
    f"Rundachse im Programm: {saetze}",
)
pruefe(any("X40" in z for z in saetze), f"Bahn fehlt: {saetze}")

# Ein verschobenes und gedrehtes Teil liegt genauso in der Stange (die Punkte im Dokument).
schief = dok.addObject("Part::Box", "Schief")
schief.Length, schief.Width, schief.Height = 30, 20, 50
schief.Placement = FreeCAD.Placement(V(100, -40, 7), FreeCAD.Rotation(V(1, 2, 3), 33))
dok.recompute()
punkte = np.array([(v.X, v.Y, v.Z) for v in schief.Shape.Vertexes])
job2, _stange2 = ne.richte_ein(dok, schief, punkte, n=6, achse="Z")
kasten = job2.Model.Group[0].Shape.BoundBox
pruefe(
    nahe(kasten.XMin, ne.ZUGABE)
    and nahe(kasten.YMin, -kasten.YMax)
    and nahe(kasten.ZMin, -kasten.ZMax),
    f"verschobenes Teil nicht in der Stange: {kasten}",
)
FreeCAD.closeDocument(dok.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK test_n_eck.py")
