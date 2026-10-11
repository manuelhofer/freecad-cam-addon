# Prüft „STL als Teil“ (stl_teil.py, W-017, P-2026-10-11-100): ein Netz wird ein Körper aus genau
# seinen Dreiecken – skaliert um die Mitte der Unterseite, repariert (Löcher geschlossen, Dreiecke
# nach innen umgedreht), ab VEREINFACHEN_AB vereinfacht mit nachgemessen höchstens ABWEICHUNG –,
# der Bericht dazu, der Körper im Dokument (verweist aufs Netz), die Rechnung für den Nebenrechner
# (über eine STL-Datei). Dazu im 4-Achs-Assistenten: Die ebene Standfläche liegt „umgedreht“ am
# Futter, vorne das andere Ende, und einstellung() findet sie im Job wieder; und formteile.flaechen
# holt wenige Flächen einzeln, viele auf einmal – dieselben.
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import MeshPart
import Part

from camaddon import formteile as ft
from camaddon import sprache, stl_teil
from camaddon import vierachs_rohteil as vr

sprache.setze_sprache("de")
V = FreeCAD.Vector
fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nahe(a, b, genau=1e-6):
    return abs(a - b) < genau


# Eine Figur: Kegelstumpf mit Kugel als Kopf, unten eben (z = 0), 46 hoch.
figur = Part.makeCone(15, 11, 30, V(0, 0, 0)).fuse(Part.makeSphere(12, V(0, 0, 34)))
figur = figur.removeSplitter()
netz = MeshPart.meshFromShape(Shape=figur, LinearDeflection=0.3, AngularDeflection=0.3)
pruefe(netz.isSolid(), "Testnetz nicht geschlossen")
hoehe = netz.BoundBox.ZLength

# --- vorbereiten: Maßstab um die Mitte der Unterseite, Bericht ---------------------------------
n2, b2 = stl_teil.vorbereiten(netz, 2.0)
bb = n2.BoundBox
pruefe(nahe(bb.ZMin, netz.BoundBox.ZMin, 1e-4), f"Maßstab: Unterseite verschoben ({bb.ZMin})")
pruefe(nahe(bb.ZLength, 2 * hoehe, 1e-3), f"Maßstab: Höhe {bb.ZLength}")
pruefe(nahe(bb.Center.x, netz.BoundBox.Center.x, 1e-4), "Maßstab: seitlich verschoben")
pruefe(b2.massstab == 2.0 and nahe(b2.masse[2], 2 * hoehe, 1e-3), f"Bericht: {b2}")
text = b2.text()
anzahl = f"{n2.CountFacets:,}".replace(",", " ")
pruefe(text.startswith(f"Körper aus {anzahl} Dreiecken.") and "Maßstab 2." in text, text)
for falsch in (0.0, -1.0, float("nan")):
    try:
        stl_teil.vorbereiten(netz, falsch)
        fehler.append(f"Maßstab {falsch} angenommen")
    except ValueError:
        pass

# Offen: 30 Dreiecke weg – die Löcher werden geschlossen, der Bericht sagt es.
offen = netz.copy()
offen.removeFacets(list(range(100, 130)))
pruefe(not offen.isSolid(), "offenes Testnetz ist geschlossen")
n3, b3 = stl_teil.vorbereiten(offen)
pruefe(n3.isSolid() and b3.loecher_geschlossen, f"Löcher nicht geschlossen: {b3}")
pruefe("Löcher sind geschlossen" in b3.text(), b3.text())

# Groß: ab VEREINFACHEN_AB vereinfacht, nachgemessen höchstens ABWEICHUNG.
fein = MeshPart.meshFromShape(Shape=figur, LinearDeflection=0.005, AngularDeflection=0.05)
grenze = stl_teil.VEREINFACHEN_AB
stl_teil.VEREINFACHEN_AB = fein.CountFacets - 1
try:
    n4, b4 = stl_teil.vorbereiten(fein)
finally:
    stl_teil.VEREINFACHEN_AB = grenze
pruefe(b4.vereinfacht and n4.CountFacets < fein.CountFacets, f"nicht vereinfacht: {b4}")
pruefe(0 < b4.abweichung <= stl_teil.ABWEICHUNG, f"Abweichung {b4.abweichung}")
# Die Messung selbst: ein Punkt 0,5 unter der Unterseite, einer 0,5 über dem Kopf – weiter als 1 mm
# sucht sie nicht (unendlich: so weit weg zählt jede Stufe als zu ungenau).
import numpy as np  # noqa: E402

abstand = stl_teil._abstaende(np.array([[0.0, 0.0, -0.5], [0.0, 0.0, 46.5], [0, 0, 60.0]]), netz)
pruefe(nahe(abstand[0], 0.5) and nahe(abstand[1], 0.5, 0.05), f"Abstände {abstand}")
pruefe(np.isinf(abstand[2]), f"weit weg: {abstand[2]}")

# --- koerper: Solid aus den Dreiecken, auch wenn sie nach innen zeigen; offen nur die Hülle -----
form = stl_teil.koerper(netz)
pruefe(form.ShapeType == "Solid" and form.Volume > 0, f"Körper: {form.ShapeType}")
pruefe(len(form.Faces) == netz.CountFacets, "nicht genau die Dreiecke")
pruefe(nahe(form.Volume, netz.Volume, 1e-3 * netz.Volume), f"Volumen {form.Volume}")
innen = netz.copy()
innen.flipNormals()
gedreht = stl_teil.koerper(innen)
pruefe(gedreht.ShapeType == "Solid" and gedreht.Volume > 0, f"nach innen: {gedreht.Volume}")
pruefe(stl_teil.koerper(offen).ShapeType != "Solid", "offenes Netz als Solid")
# vorbereiten() dreht ein Netz, dessen Dreiecke einheitlich nach innen zeigen, nach außen.
pruefe(stl_teil._volumen(innen) < 0 < stl_teil._volumen(netz), "Volumen ohne Vorzeichen")
pruefe(stl_teil._volumen(stl_teil.vorbereiten(innen)[0]) > 0, "nach innen bleibt nach innen")

# --- Für den Nebenrechner: über eine STL-Datei, dasselbe Ergebnis --------------------------------
griff, datei = tempfile.mkstemp(suffix=".stl")
os.close(griff)
try:
    netz.write(datei)
    brep, bericht, zuordnung = stl_teil.koerper_rechnen(datei, 1.0)
finally:
    os.remove(datei)
uebertragen = brep.form()
pruefe(uebertragen.ShapeType == "Solid", "über die Datei kein Solid")
pruefe(nahe(uebertragen.Volume, form.Volume, 1e-6 * form.Volume), "über die Datei ein anderes")
pruefe(bericht.dreiecke == netz.CountFacets and bericht.geschlossen, f"Bericht {bericht}")
pruefe(sorted(zuordnung) == list(range(netz.CountFacets)), "Fläche je Dreieck: nicht jede einmal")

# --- Im Dokument: Körper verweist aufs Netz, Name, nur lesen -------------------------------------
dok = FreeCAD.newDocument("StlTeil")
netzobjekt = dok.addObject("Mesh::Feature", "Figur")
netzobjekt.Mesh = netz
pruefe(stl_teil.ist_netz(netzobjekt) and not stl_teil.aus_stl(netzobjekt), "Netz erkannt?")
teil, _bericht = stl_teil.koerper_aus_netz(dok, netzobjekt)
dok.recompute()
pruefe(stl_teil.aus_stl(teil) and not stl_teil.ist_netz(teil), "Körper nicht erkannt")
pruefe(getattr(teil, stl_teil.EIGENSCHAFT_STL) is netzobjekt, "Verweis aufs Netz fehlt")
pruefe("ReadOnly" in teil.getEditorMode(stl_teil.EIGENSCHAFT_STL), "Verweis änderbar")
pruefe(teil.Label == "Figur (Körper)", f"Name {teil.Label!r}")

# --- 4 Achsen: die Standfläche am Futter, vorne der Kopf; wiedergefunden im Job ------------------
form = teil.Shape
standflaeche = next(
    f"Face{i}"
    for i, f in enumerate(form.Faces, 1)
    if abs(f.CenterOfMass.z) < 1e-6 and vr.aussennormale(f).z < -0.99
)
mess = vr.vermesse(form, form.getElement(standflaeche), None, True)
pruefe((mess.normale - V(0, 0, 1)).Length < 1e-9, f"Normale am Futter {mess.normale}")
pruefe(nahe(mess.vorne, 0) and nahe(mess.hinten, -hoehe, 1e-4), f"{mess.vorne} … {mess.hinten}")
vorne = vr.vermesse(form, form.getElement(standflaeche))  # nicht umgedreht: die Fläche vorne
pruefe((vorne.normale - V(0, 0, -1)).Length < 1e-9, f"nicht umgedreht: {vorne.normale}")
pruefe(nahe(vorne.vorne, 0) and nahe(vorne.hinten, -hoehe, 1e-4), "nicht umgedreht: Länge")
lage = vr.lage(mess, "A", vr.MITTE_AUTO, 0.0, 40)
stange = vr.Stange(40.0, 1.0, 3.0, 25.0)
job = vr.richte_ein(dok, teil, lage, stange, "A")
dok.recompute()
klon = vr.modell(job)
a = [e.Point.x for e in klon.Shape.Vertexes]
pruefe(nahe(max(a), 0, 1e-4) and nahe(min(a), -hoehe, 1e-4), f"Klon längs {min(a)} … {max(a)}")
e = vr.einstellung(job)
pruefe(e is not None and e.umgedreht and e.flaeche == standflaeche, f"Einstellung {e}")
pruefe(e is not None and e.stange == stange and e.mitte == vr.MITTE_TEIL, f"Einstellung {e}")

# Statt der Standfläche eine Achse des Teils (vermesse_achse): X längs der Stange, Plus-Ende vorne
# – wiedergefunden im Job als „X“; umgedreht das Minus-Ende vorne.
achse_x = vr.vermesse_achse(form, "X")
pruefe((achse_x.normale - V(1, 0, 0)).Length < 1e-12, f"Achse X: {achse_x.normale}")
breite = form.BoundBox.XLength
pruefe(nahe(achse_x.vorne, 0) and nahe(achse_x.hinten, -breite, 1e-3), "Achse X: Länge")
dok_x = FreeCAD.newDocument("StlAchse")
netz_x = dok_x.addObject("Mesh::Feature", "Figur")
netz_x.Mesh = netz
teil_x, _b = stl_teil.koerper_aus_netz(dok_x, netz_x)
dok_x.recompute()
for umgedreht in (False, True):
    mess_x = vr.vermesse_achse(teil_x.Shape, "X", umgedreht)
    job_x = vr.richte_ein(dok_x, teil_x, vr.lage(mess_x, "A", vr.MITTE_AUTO, 0.0, 40), stange, "A")
    dok_x.recompute()
    e_x = vr.einstellung(job_x)
    pruefe(
        e_x is not None and e_x.flaeche == "X" and e_x.umgedreht == umgedreht,
        f"Achse X (umgedreht {umgedreht}) nicht wiedergefunden: {e_x}",
    )
FreeCAD.closeDocument(dok_x.Name)

# Vernetzen (vierachs_huelle.vernetze): Körper und Klon bringen die Dreiecke des Netzes mit, in
# ihrer Lage – ohne OpenCascade; eine kleine Form, die keiner ist, vernetzt OCC wie bisher.
from camaddon import vierachs_huelle as vh  # noqa: E402

pruefe(getattr(teil, stl_teil.EIGENSCHAFT_NETZ).CountFacets == netz.CountFacets, "Netz am Körper")
pruefe(netz.CountFacets >= stl_teil.NETZ_AB, f"Testnetz zu klein: {netz.CountFacets}")
pruefe(stl_teil.netz_fuer(klon.Shape) is not None, "Klon nicht als Körper aus einem STL erkannt")
for name, objekt in (("Körper", teil), ("Klon", klon)):
    vernetzt = vh.vernetze(objekt.Shape)
    kasten = objekt.Shape.BoundBox
    pruefe(len(vernetzt.dreiecke) == netz.CountFacets, f"{name}: {len(vernetzt.dreiecke)} Dreiecke")
    unten, oben = vernetzt.punkte.min(axis=0), vernetzt.punkte.max(axis=0)
    pruefe(
        abs(unten[0] - kasten.XMin) < 1e-3 and abs(oben[2] - kasten.ZMax) < 1e-3,
        f"{name}: Netz liegt woanders ({unten}, {oben}; {kasten})",
    )
pruefe(stl_teil.netz_fuer(Part.makeBox(1, 2, 3)) is None, "ein Quader gilt als STL")
# Je Fläche vernetzt (vierachs_flaechen.vernetze): die Dreiecke mit der Nummer ihrer Fläche –
# makeShapeFromMesh ordnet die Flächen anders als die Dreiecke.
from camaddon import vierachs_flaechen as vfl  # noqa: E402

fnetz = vfl._vernetze(klon.Shape, 0.01)
pruefe(len(fnetz.flaeche) == netz.CountFacets and fnetz.anzahl == netz.CountFacets, "Flächennetz")
for j in (1, len(fnetz.flaeche) // 3, len(fnetz.flaeche) - 1):
    ecken = sorted(
        tuple(round(c, 4) for c in v.Point)
        for v in klon.Shape.getElement(f"Face{fnetz.flaeche[j] + 1}").Vertexes
    )
    soll = sorted(tuple(round(c, 4) for c in q) for q in fnetz.netz.punkte[fnetz.netz.dreiecke[j]])
    pruefe(ecken == soll, f"Dreieck {j} gehört nicht zu Face{fnetz.flaeche[j] + 1}")
schieben = FreeCAD.Matrix()
schieben.move(V(0, 0, 1))
anders = teil.Shape.transformGeometry(schieben)  # verschoben in der Geometrie, nicht in der Lage
pruefe(stl_teil.netz_fuer(anders) is None, "verschobene Geometrie ohne Lage erkannt")
bewegt = teil.Shape.copy()
bewegt.Placement = FreeCAD.Placement(V(5, 0, 0), FreeCAD.Rotation(V(0, 1, 0), 30))
gefunden = stl_teil.netz_fuer(bewegt)
pruefe(
    gefunden is not None and abs(gefunden[0][:, 0].min() - bewegt.BoundBox.XMin) < 1e-3,
    "bewegte Form (Lage) nicht erkannt",
)

# --- Kollision (P-2026-10-11-101): genau, aber nur mit den Flächen in der Nähe -------------------
import types  # noqa: E402

from camaddon import kollision as kb  # noqa: E402

verbund = Part.makeCompound([klon.Shape.copy()])  # wie kollision._teil_form
stl_daten = stl_teil.flaechennetz_fuer(verbund)
pruefe(stl_daten is not None, "Verbund aus dem Klon nicht als STL erkannt")
if stl_daten is not None:
    teil_k = kb.Koerper("Teil", kb.TEIL, verbund, None, FreeCAD.Placement(), stl=stl_daten)
    welt = types.SimpleNamespace(_fehler=set(), ergebnis=None)
    kasten = verbund.BoundBox
    for name, quader in (
        ("nah", Part.makeBox(4, 4, 4, V(kasten.XMin + 20, kasten.YMax + 2, -2))),
        ("weit", Part.makeBox(4, 4, 4, V(kasten.XMin + 20, kasten.YMax + 60, -2))),
        ("drin", Part.makeBox(4, 4, 4, V(kasten.XMin + 20, -2, -2))),
    ):
        anderer = kb.Koerper(name, kb.MASCHINE, quader, None, FreeCAD.Placement())
        ist, _stelle = kb._Welt._abstand(welt, teil_k, anderer)
        wahr = verbund.distToShape(quader)[0]
        if name == "weit":
            pruefe(kb.AUSSCHNITT_RAND <= ist <= wahr + 1e-9, f"weit: {ist} (wahr {wahr})")
        else:
            pruefe(abs(ist - wahr) < 1e-6, f"{name}: {ist} statt {wahr}")
    pruefe(teil_k.netz() is not None and teil_k.netz().toleranz > 0, "Netz des Teils fehlt")

# --- formteile.flaechen: wenige einzeln, viele auf einmal – dieselben ------------------------
wenige = ft.flaechen(form, [0, 5, len(form.Faces), -1, 7])
pruefe([n for n, _f in wenige] == [0, 5, 7], f"wenige: {[n for n, _f in wenige]}")
alle = list(range(len(form.Faces)))
viele = ft.flaechen(form, alle)
pruefe(len(viele) == len(form.Faces) > ft.EINZELN_BIS, "viele: Anzahl")
pruefe(
    all(f.isSame(form.getElement(f"Face{n + 1}")) for n, f in viele[:: max(1, len(viele) // 50)]),
    "viele: andere Flächen",
)
FreeCAD.closeDocument(dok.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK test_stl_teil.py")
