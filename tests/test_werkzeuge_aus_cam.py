# Prüft „Aus CAM übernehmen“ (werkzeuge_aus_cam.py) an FreeCADs mitgelieferter
# Bibliothek „Default“: Jede ihrer Formen hat jetzt eine Art (Gravierstichel,
# Säge, Taster, Gewindefräser …) – mit welchen Werten, was schon da ist, was
# eine neue Nummer bekommt, und dass die eigene Bibliothek „CAM-Addon“ nicht
# angeboten wird. Dazu fremde Werkzeuge: Gewindebohrer links und in Zoll,
# Konikfräser – und eine eigene Form, die draußen bleibt.
import json
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from Path.Tool.camassets import user_asset_store

from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz
from camaddon import werkzeuge_aus_cam as aus_cam

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


# Ein leerer Speicher bekommt, wie in CAM, zuerst FreeCADs Bibliothek „Default“.
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
bibliotheken = aus_cam.bibliotheken()
namen = [name for _adresse, name, _anzahl in bibliotheken]
pruefe(namen == ["Default"], f"Bibliotheken: {namen}")
adresse = bibliotheken[0][0] if bibliotheken else ""

# Die eigene Bibliothek „CAM-Addon“ wird nicht angeboten.
ue.uebergeben(wz.Bibliothek([wz.Werkzeug(nummer=40, durchmesser=8)]))
pruefe([name for _a, name, _n in aus_cam.bibliotheken()] == ["Default"], "„CAM-Addon“ angeboten")

# Hier gibt es schon T1 (gleicher Fräser wie in „Default“) und T2 (ein anderer).
t1 = wz.Werkzeug(nummer=1, durchmesser=3.175, schneiden=4)
t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.VOLLNUT, ae=3.175, ap=1.5, vc=100, fz=0.02)]
t2 = wz.Werkzeug(nummer=2, durchmesser=12)
bibliothek = wz.Bibliothek([t1, t2])
bericht = aus_cam.uebernehmen(bibliothek, adresse)

neu = {w.name: w for w in bericht.neu}
pruefe(all(not w.bezeichnung for w in bericht.neu), "Name aus CAM steht in der Bezeichnung")
pruefe(
    sorted(neu)
    == [
        "30 Deg. V-Bit",
        "45 Deg. Chamfer",
        "45 Deg. V-Bit",
        "5mm Drill",
        "5mm Endmill",
        "5mm-thread-cutter",
        "6 mm Bull Nose",
        "60 Deg. V-Bit",
        "6mm Ball End",
        "90 Deg. V-Bit",
        "Probe",
        "Slitting Saw",
    ],
    f"übernommen: {sorted(neu)}",
)
pruefe(bericht.schon_da == ["3.175mm Endmill"], f"schon da: {bericht.schon_da}")
pruefe(bericht.neue_nummer == [("5mm Endmill", 2, 14)], f"neue Nummer: {bericht.neue_nummer}")
pruefe(not bericht.andere_form, f"andere Formen: {bericht.andere_form}")
pruefe(len(bibliothek.werkzeuge) == 14, f"{len(bibliothek.werkzeuge)} Werkzeuge statt 14")
pruefe(bibliothek.werkzeuge[0].einsaetze(wz.ALLE), "T1 hat seine Schnittwerte verloren")

torus = neu.get("6 mm Bull Nose")
if torus is not None:
    werte = (
        torus.nummer,
        torus.art,
        torus.durchmesser,
        torus.schneiden,
        torus.schneidenlaenge,
        torus.gesamtlaenge,
        torus.schaft,
        torus.eckradius,
        torus.schneidstoff,
    )
    pruefe(werte == (5, wz.TORUSFRAESER, 6, 4, 40, 50, 3, 1.5, wz.HSS), f"Torusfräser: {werte}")
bohrer = neu.get("5mm Drill")
if bohrer is not None:
    pruefe((bohrer.art, bohrer.nummer, bohrer.schneiden) == (wz.BOHRER, 3, 2), f"{bohrer}")
    # Der Spitzenwinkel kommt mit (FreeCADs Beispielbohrer: um die 118°).
    pruefe(90 <= bohrer.spitzenwinkel <= 140, f"Spitzenwinkel {bohrer.spitzenwinkel}")
kugel = neu.get("6mm Ball End")
pruefe(kugel is not None and kugel.art == wz.KUGELFRAESER, "Kugelfräser")
fase = neu.get("45 Deg. Chamfer")
pruefe(fase is not None and fase.art == wz.FASENFRAESER, "Fasenfräser")
if fase is not None:
    werte = (fase.spitzenwinkel, fase.spitzen_d, fase.schneidenlaenge)
    pruefe(werte == (45, 5, 6.35), f"Fasenfräser: {werte}")


def pruefe_werte(name, art, **erwartet):
    """Das übernommene Werkzeug `name` hat die Art und diese Werte."""
    w = neu.get(name)
    if w is None or w.art != art:
        pruefe(False, f"{name}: {w}")
        return
    for feld, wert in erwartet.items():
        pruefe(abs(getattr(w, feld) - wert) < 1e-4, f"{name}: {feld} {getattr(w, feld)}")


# Ein Gravierstichel ist ein spitzer Fasenfräser.
pruefe_werte("30 Deg. V-Bit", wz.FASENFRAESER, durchmesser=10, spitzenwinkel=30, spitzen_d=0.1)
pruefe_werte(
    "Slitting Saw", wz.NUTENFRAESER, durchmesser=76.2, schneidenbreite=3, hals_d=19.05, schneiden=20
)
pruefe_werte("Probe", wz.TASTER, durchmesser=6, schaft=4, gesamtlaenge=50)
# Der Gewindefräser hat in CAM einen Zahn: (5 − 3) · tan 30° + 0,1 hoch, der Hals
# reicht bis 20 mm.
zahn = 2 * 0.5773502691896257 + 0.1
pruefe_werte(
    "5mm-thread-cutter",
    wz.GEWINDEFRAESER,
    durchmesser=5,
    flankenwinkel=60,
    hals_d=3,
    schneidenlaenge=round(zahn, 4),
    hals_laenge=round(20 - round(zahn, 4), 4),
)

# Eine Bibliothek, die sich nicht lesen lässt, versteckt die anderen nicht.
from Path.Tool.camassets import cam_assets  # noqa: E402

cam_assets.add_raw("toolbitlibrary", "kaputt", b"{kein json")
namen = [name for _a, name, _n in aus_cam.bibliotheken()]
pruefe(namen == ["Default"], f"mit kaputter Bibliothek: {namen}")

# Noch einmal: alles schon da.
bericht = aus_cam.uebernehmen(bibliothek, adresse)
pruefe(not bericht.neu and len(bericht.schon_da) == 13, f"zweites Mal: {bericht}")

# Ein Werkzeug, das sich nicht lesen lässt, hält die anderen nicht auf.
original = aus_cam.werkzeug_aus


def werkzeug_aus_mit_fehler(bit, nummer):
    if str(bit.label) == "5mm Drill":
        raise ValueError("kaputt")
    return original(bit, nummer)


aus_cam.werkzeug_aus = werkzeug_aus_mit_fehler
leer = wz.Bibliothek()
bericht = aus_cam.uebernehmen(leer, adresse)
aus_cam.werkzeug_aus = original
pruefe(bericht.unlesbar == ["5mm Drill"], f"unlesbar: {bericht.unlesbar}")
# Alle 13 Werkzeuge in „Default“ haben eine Art, ohne den Bohrer 12.
pruefe(len(bericht.neu) == 12 and len(leer.werkzeuge) == 12, f"trotzdem: {bericht.neu}")

# Fremde Werkzeuge: Gewindebohrer links (CAM dreht ihn rückwärts) und in Zoll,
# ein Konikfräser (Kegelwinkel je Seite = halber TaperAngle) – und eine eigene
# Form, die die Werkzeugverwaltung nicht kennt.
fremde = {
    "fremd_links": {
        "name": "M8 links",
        "shape": "tap.fcstd",
        "shape-type": "Tap",
        "parameter": {
            "CuttingEdgeLength": "24 mm",
            "Diameter": "8 mm",
            "Length": "79 mm",
            "Pitch": "1.25 mm",
            "ShankDiameter": "6 mm",
        },
        "attribute": {"SpindleDirection": "Reverse"},
    },
    "fremd_zoll": {
        "name": "3/8-16",
        "shape": "tap.fcstd",
        "shape-type": "tap",
        "parameter": {"Diameter": '0.375 "', "Pitch": "0.0625 in", "Length": '2.5 "'},
    },
    "fremd_konik": {
        "name": "Konik 3",
        "shape": "taperedballnose.fcstd",
        "shape-type": "TaperedBallNose",
        "parameter": {
            "Diameter": "2 mm",
            "TaperAngle": "6 °",
            "TaperDiameter": "6 mm",
            "CuttingEdgeHeight": "25 mm",
            "Flutes": 2,
            "Length": "60 mm",
            "ShankDiameter": "6 mm",
        },
    },
    "fremd_eigene": {
        "name": "Eigene Form",
        "shape": "meine_form.fcstd",
        "shape-type": "Custom",
        "parameter": {"Diameter": "6 mm"},
    },
}
for kennung, daten in fremde.items():
    cam_assets.add_raw("toolbit", kennung, json.dumps({"version": 2, **daten}).encode("utf-8"))
tools = [{"nr": i + 1, "path": f"{kennung}.fctb"} for i, kennung in enumerate(fremde)]
fremd = {"label": "Fremd", "tools": tools, "version": 1}
cam_assets.add_raw("toolbitlibrary", "fremd", json.dumps(fremd).encode("utf-8"))
adresse = next(a for a, name, _n in aus_cam.bibliotheken() if name == "Fremd")
leer = wz.Bibliothek()
bericht = aus_cam.uebernehmen(leer, adresse)
neu = {w.name: w for w in bericht.neu}
# Eine Form, die FreeCAD nicht findet, lädt es als „Missing Tool (…)“ – ohne Art.
pruefe(len(bericht.andere_form) == 1, f"eigene Form: {bericht.andere_form}")
pruefe_werte(
    "M8 links",
    wz.GEWINDEBOHRER_LINKS,
    durchmesser=8,
    steigung=1.25,
    schneidenlaenge=24,
    schaft=6,
    gesamtlaenge=79,
)
pruefe_werte("3/8-16", wz.GEWINDEBOHRER_RECHTS, durchmesser=9.525, steigung=1.5875)
pruefe_werte("Konik 3", wz.KONIKFRAESER, durchmesser=2, kegelwinkel=3, schneidenlaenge=25)

if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
