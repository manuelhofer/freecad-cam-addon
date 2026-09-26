# Prüft „Aus CAM übernehmen“ (werkzeuge_aus_cam.py) an FreeCADs mitgelieferter
# Bibliothek „Default“: welche Formen übernommen werden und mit welchen Werten,
# was schon da ist, was eine neue Nummer bekommt – und dass die eigene
# Bibliothek „CAM-Addon“ nicht angeboten wird.
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
    == ["45 Deg. Chamfer", "5mm Drill", "5mm Endmill", "6 mm Bull Nose", "6mm Ball End"],
    f"übernommen: {sorted(neu)}",
)
pruefe(bericht.schon_da == ["3.175mm Endmill"], f"schon da: {bericht.schon_da}")
pruefe(bericht.neue_nummer == [("5mm Endmill", 2, 14)], f"neue Nummer: {bericht.neue_nummer}")
pruefe(len(bericht.andere_form) == 7, f"andere Formen: {bericht.andere_form}")
pruefe("30 Deg. V-Bit" in bericht.andere_form and "Probe" in bericht.andere_form, "V-Bit, Taster")
pruefe(len(bibliothek.werkzeuge) == 7, f"{len(bibliothek.werkzeuge)} Werkzeuge statt 7")
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
kugel = neu.get("6mm Ball End")
pruefe(kugel is not None and kugel.art == wz.RADIUSFRAESER, "Radiusfräser")
fase = neu.get("45 Deg. Chamfer")
pruefe(fase is not None and fase.art == wz.FASENFRAESER, "Fasenfräser")

# Eine Bibliothek, die sich nicht lesen lässt, versteckt die anderen nicht.
from Path.Tool.camassets import cam_assets  # noqa: E402

cam_assets.add_raw("toolbitlibrary", "kaputt", b"{kein json")
namen = [name for _a, name, _n in aus_cam.bibliotheken()]
pruefe(namen == ["Default"], f"mit kaputter Bibliothek: {namen}")

# Noch einmal: alles schon da.
bericht = aus_cam.uebernehmen(bibliothek, adresse)
pruefe(not bericht.neu and len(bericht.schon_da) == 6, f"zweites Mal: {bericht}")

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
# Sechs Werkzeuge in „Default“ haben eine bekannte Form, ohne den Bohrer fünf.
pruefe(len(bericht.neu) == 5 and len(leer.werkzeuge) == 5, f"trotzdem übernommen: {bericht.neu}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
