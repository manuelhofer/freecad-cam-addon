# Prüft „An CAM übergeben“ (W-002 Stufe 2) mit CAMs eigener Asset-Verwaltung in
# einem Temp-Ordner: FreeCAD lädt die Bibliothek „CAM-Addon“ und die Werkzeuge
# mit Nummern und Geometrie; im Wochen-Build kommen die Schnittwerte als
# Presets an, und FreeCADs eigener Vorschlag findet für 1.4301 unsere Werte –
# beim Bohren mit vollem Eintauchvorschub, bei der Reibahle ohne Schneidenzahl
# in CAM trotzdem mit unserem Vorschub. Arten ohne eigene Form nennt der
# Bericht (die Formen aller Arten prüft test_cam_formen). Eine zweite Übergabe
# entfernt gelöschte Werkzeuge, fremde bleiben.
import json
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from Path.Tool.camassets import cam_assets, user_asset_store

from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []
# Die Beispielnamen sind deutsch, egal welche Sprache FreeCAD meldet (1.1.3: Englisch).
vorher = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def mm(wert):
    return float(wert.getValueAs("mm"))


ordner = pathlib.Path(tempfile.mkdtemp())
user_asset_store.set_dir(ordner)  # nur in diesem Lauf; die Einstellung bleibt
fremd = {"version": 2, "name": "Eigenes", "shape": "endmill.fcstd", "shape-type": "Endmill"}
fremd["parameter"] = {"Diameter": "3 mm", "CuttingEdgeHeight": "10 mm", "Length": "40 mm"}
cam_assets.add_raw("toolbit", "eigenes_werkzeug", json.dumps(fremd).encode("utf-8"))

fraeser = wz.Werkzeug(nummer=3, durchmesser=12, schneiden=3, schneidenlaenge=26)
fraeser.schnittwerte[wz.ALLE] = [
    wz.Einsatz(art=wz.VOLLNUT, ae=12, ap=3, vc=120, fz=0.05),
    wz.Einsatz(art=wz.DYNAMISCH, ae=1.2, ap=25, vc=120, fz=0.15),
    wz.Einsatz(art=wz.SCHLICHTEN, ae=0.2, ap=25),  # ohne vc/fz: kein Preset
]
fraeser.eigene_anlegen("1.4301")[0].vc = 80
torus = wz.Werkzeug(
    nummer=5,
    art=wz.TORUSFRAESER,
    durchmesser=10,
    eckradius=1,
    gesamtlaenge=72,
    schaft=8,
    name="Torus VHM 10 R1",
)
bohrer = wz.Werkzeug(nummer=7, art=wz.BOHRER, durchmesser=8.5, schneiden=2, schneidstoff=wz.HSS)
bohrer.spitzenwinkel = 130
bohrer.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25, fz=0.08)]
ohne = wz.Werkzeug(nummer=9)
# Drehwerkzeuge kennt CAM nicht: Sie bleiben draußen und werden genannt.
dreh = wz.Werkzeug(nummer=11, art=wz.DREHWERKZEUG, eckradius=0.8)
# Die Reibahle hat in CAM keine Schneidenzahl; der Gewindebohrer nimmt den
# Vorschub aus der Steigung; den Lollipopfräser gibt es dort als Kugelfräser.
reibahle = wz.Werkzeug(nummer=13, art=wz.REIBAHLE, durchmesser=10, schneiden=6)
reibahle.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.REIBEN, vc=20, fz=0.05)]
gewinde = wz.Werkzeug(nummer=15, art=wz.GEWINDEBOHRER_LINKS, durchmesser=10, steigung=1.5)
gewinde.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.GEWINDEBOHREN, vc=10)]
lolli = wz.Werkzeug(nummer=17, art=wz.LOLLIPOPFRAESER, durchmesser=8, hals_laenge=20)
bibliothek = wz.Bibliothek([fraeser, torus, bohrer, ohne, dreh, reibahle, gewinde, lolli])

pruefe(not ue.schon_uebergeben(), "schon_uebergeben vor der ersten Übergabe")
bericht = ue.uebergeben(bibliothek)
pruefe((bericht.werkzeuge, bericht.ohne_durchmesser) == (6, 1), f"Bericht: {bericht}")
pruefe(bericht.ohne_form == ["T11 Drehwerkzeug"], f"ohne Form: {bericht.ohne_form}")
pruefe(
    bericht.naeherungen == [("T17 Lollipopfräser", "Kugelfräser")],
    f"Näherungen: {bericht.naeherungen}",
)
pruefe(bericht.presets == 7, f"{bericht.presets} Presets statt 7")
pruefe(
    not bericht.werkstoffe_ohne_freecad,
    f"ohne FreeCAD-Werkstoff: {bericht.werkstoffe_ohne_freecad}",
)

# FreeCAD lädt Bibliothek und Werkzeuge.
bib = cam_assets.get("toolbitlibrary://camaddon")
nummern = sorted(bib._bit_nos)  # die T-Nummern der Bibliothek
pruefe(
    bib.label == "CAM-Addon" and nummern == [3, 5, 7, 13, 15, 17],
    f"Bibliothek {bib.label}: {nummern}",
)
tb = cam_assets.get(f"toolbit://camaddon_{fraeser.kennung}")
pruefe(mm(tb.obj.Diameter) == 12 and int(tb.obj.Flutes) == 3, f"Fräser: {tb.obj.Diameter}")
pruefe(mm(tb.obj.CuttingEdgeHeight) == 26, f"Schneidenlänge {tb.obj.CuttingEdgeHeight}")
pruefe(tb.obj.Material == "Carbide" and mm(tb.obj.Chipload) == 0.05, "Schneidstoff, Chipload")
t5 = cam_assets.get(f"toolbit://camaddon_{torus.kennung}")
# In CAM heißt das Werkzeug wie eingetragen, sonst nach dem Beispielnamen.
pruefe(str(t5.label) == "Torus VHM 10 R1", f"Name in CAM: {t5.label!r}")
pruefe(str(tb.label) == "Schaftfräser T3 VHM D12 L26", f"Beispielname in CAM: {tb.label!r}")
pruefe(mm(t5.obj.CornerRadius) == 1, f"Eckradius {t5.obj.CornerRadius}")
# Eingetragen gilt, sonst geschätzt: 26 + 2 · 12 = 50 mm, Schaft = D.
pruefe((mm(t5.obj.Length), mm(t5.obj.ShankDiameter)) == (72, 8), "Länge/Schaft eingetragen")
pruefe((mm(tb.obj.Length), mm(tb.obj.ShankDiameter)) == (50, 12), "Länge/Schaft geschätzt")
t7 = cam_assets.get(f"toolbit://camaddon_{bohrer.kennung}")
pruefe(t7.obj.Material == "HSS" and mm(t7.obj.Diameter) == 8.5, "Bohrer")
spitze = float(t7.obj.TipAngle.getValueAs("deg"))
pruefe(abs(spitze - 130) < 1e-9, f"Spitzenwinkel in CAM: {spitze}")

# Wochen-Build: Presets am Werkzeug, und FreeCADs Vorschlag nimmt sie.
if ue.presets_moeglich():
    from Path.Tool.FeedsSpeeds import MaterialContext, OpContext, ToolContext, get_presets, resolve

    presets = get_presets(tb.obj)
    pruefe(len(presets) == 4, f"{len(presets)} Presets am Fräser statt 4")
    arten = sorted(p["op_type_hint"] for p in presets)
    pruefe(arten == ["adaptive", "adaptive", "slot", "slot"], f"Bearbeitungsarten {arten}")
    uuid, _name = ue.freecad_werkstoffe()["1.4301"]
    werkzeug = ToolContext(diameter=12, flutes=3, presets=tuple(presets), shape_id="endmill")
    vorschlag = resolve(werkzeug, MaterialContext(uuid=uuid), OpContext("slot"))
    pruefe(vorschlag.surface_speed == 80, f"Vorschlag für 1.4301/Nut: vc {vorschlag.surface_speed}")
    vorschlag = resolve(werkzeug, MaterialContext(name="C45"), OpContext("slot"))
    pruefe(
        vorschlag.surface_speed == 120,
        f"Vorschlag für andere Werkstoffe: {vorschlag.surface_speed}",
    )
    pruefe(abs(vorschlag.spindle_speed - 3183.1) < 1, f"Drehzahl {vorschlag.spindle_speed}")

    # Bohren: senkrecht der volle Vorschub, wie „Schnittwerte in den Job“.
    pruefe(
        [p["vert_feed_ratio"] for p in get_presets(t7.obj)] == [1.0],
        f"Bohrer: {get_presets(t7.obj)}",
    )
    # Die Reibahle zählt in CAM eine Schneide: Chipload ist f je Umdrehung, und
    # FreeCAD schlägt denselben Vorschub vor wie das Addon (n · 6 · 0,05).
    t13 = cam_assets.get(f"toolbit://camaddon_{reibahle.kennung}")
    presets = get_presets(t13.obj)
    pruefe([p["chipload"] for p in presets] == [0.3], f"Reibahle: {presets}")
    pruefe(abs(mm(t13.obj.Chipload) - 0.3) < 1e-9, f"Reibahle Chipload {t13.obj.Chipload}")
    werkzeug = ToolContext(diameter=10, flutes=None, presets=tuple(presets), shape_id="reamer")
    vorschlag = resolve(werkzeug, MaterialContext(name="C45"), OpContext("drill"))
    n = 20 * 1000 / (3.141592653589793 * 10)
    pruefe(abs(vorschlag.vert_feed - n * 6 * 0.05) < 0.01, f"Reibahle vf {vorschlag.vert_feed}")
    # Gewindebohrer: kein Chipload – den Vorschub nimmt CAM aus der Steigung.
    t15 = cam_assets.get(f"toolbit://camaddon_{gewinde.kennung}")
    presets = get_presets(t15.obj)
    pruefe([p["chipload"] for p in presets] == [None], f"Gewindebohrer: {presets}")

# Zweite Übergabe ohne den Torusfräser: er verschwindet, das fremde Werkzeug bleibt.
bibliothek.entferne(torus)
bericht = ue.uebergeben(bibliothek)
pruefe(bericht.entfernt == 1, f"entfernt: {bericht.entfernt}")
bits = {u.asset_id for u in cam_assets.list_assets(asset_type="toolbit", store="local")}
pruefe(f"camaddon_{torus.kennung}" not in bits, "Torusfräser nicht entfernt")
pruefe("eigenes_werkzeug" in bits, "fremdes Werkzeug entfernt")
nummern = sorted(cam_assets.get("toolbitlibrary://camaddon")._bit_nos)
pruefe(nummern == [3, 7, 13, 15, 17], f"Bibliothek danach: {nummern}")

# Einmal übergeben: Die Bibliothek steht in CAM, OK und Übernehmen ziehen sie mit (D-27).
pruefe(ue.schon_uebergeben(), "schon_uebergeben nach der Übergabe falsch")

# Die Drehrichtung am Werkzeug geht als SpindleDirection nach CAM (P-2026-10-02-40).
for art, drehrichtung, soll in (
    (wz.SCHAFTFRAESER, "", "Forward"),
    (wz.SCHAFTFRAESER, wz.LINKS, "Reverse"),
    (wz.GEWINDEBOHRER_LINKS, "", "Reverse"),
    (wz.TASTER, "", "None"),
):
    ist = ue.drehrichtung(wz.Werkzeug(art=art, drehrichtung=drehrichtung))
    pruefe(ist == soll, f"{art} {drehrichtung!r}: {ist}")

sprache.setze_sprache(vorher)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
