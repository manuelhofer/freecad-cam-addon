# Prüft den Export in die CAM-Maschinendefinition: Achsen mit Richtung,
# Grenzen, Geschwindigkeit, Tisch/Kopf und Kette, Spindel, Bericht über das,
# was CAM nicht kennt, und dass CAM die Maschine danach findet.
import os
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))
sys.path.insert(0, HIER)

import beispielmaschinen
import FreeCAD as App

from camaddon import export, sprache
from camaddon import maschine as m

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def parallel(v, x, y, z):
    return abs(abs(v.dot(App.Vector(x, y, z))) - 1) < 1e-6


def pruefe_export():
    from Machine.models.machine import AxisRole, MachineFactory

    # Der Bericht wird unten auf deutsche Sätze geprüft.
    sprache_vorher = sprache.gewaehlte_sprache()
    sprache.setze_sprache("de")
    # Nicht in den echten CAM-Ordner des Benutzers schreiben.
    MachineFactory.set_config_directory(tempfile.mkdtemp())

    asm, ma = beispielmaschinen.drehmaschine_komplett()
    pruefe(
        m.pruefe(ma) == [], f"Beispielmaschine nicht vollständig: {[x.text for x in m.pruefe(ma)]}"
    )
    bericht = export.exportiere(ma)
    pruefe(bericht.datei is not None and bericht.datei.is_file(), "keine .fcm-Datei geschrieben")
    pruefe(bericht.datei.name == "Testdrehmaschine.fcm", f"Dateiname: {bericht.datei.name}")

    cam = MachineFactory.load_configuration(bericht.datei)
    pruefe(sorted(cam.linear_axes) == ["X1", "Z1"], f"Linearachsen: {sorted(cam.linear_axes)}")
    pruefe(sorted(cam.rotary_axes) == ["C4"], f"Drehachsen: {sorted(cam.rotary_axes)}")
    pruefe(
        [t.name for t in cam.toolheads] == ["S4"] and cam.toolheads[0].max_rpm == 4000,
        f"Spindeln: {[(t.name, t.max_rpm) for t in cam.toolheads]}",
    )

    x1, z1, c4 = cam.linear_axes.get("X1"), cam.linear_axes.get("Z1"), cam.rotary_axes.get("C4")
    if x1 and z1 and c4:
        pruefe(parallel(x1.direction_vector, 1, 0, 0), "X1: Richtung X erwartet")
        pruefe(
            (x1.min_limit, x1.max_limit) == (0, 200), f"X1: Grenzen {x1.min_limit}/{x1.max_limit}"
        )
        pruefe(x1.max_velocity == 24000, f"X1: Eilgang {x1.max_velocity}")
        pruefe(x1.parent == "Z1", f"X1 hängt an {x1.parent!r} statt Z1")
        pruefe(z1.parent is None, f"Z1 hängt an {z1.parent!r}")
        pruefe(
            x1.role == AxisRole.HEAD_LINEAR and z1.role == AxisRole.HEAD_LINEAR,
            "X1/Z1 nicht im Kopf",
        )
        pruefe(c4.role == AxisRole.TABLE_ROTARY, "C4 nicht im Tisch")
        pruefe(parallel(c4.rotation_vector, 0, 0, 1), "C4: Drehachse Z erwartet")
        pruefe(c4.max_velocity == 36000, f"C4: {c4.max_velocity} °/min statt 36000 (100 U/min)")
    pruefe(cam.validate_kinematic_chain() == [], f"Kette: {cam.validate_kinematic_chain()}")

    uebertragen = " ".join(bericht.uebertragen)
    zu_pruefen = " ".join(bericht.zu_pruefen)
    nicht_uebertragen = " ".join(bericht.nicht_uebertragen)
    pruefe(
        "„Z1“ hat am Gelenk keine Begrenzung" in zu_pruefen,
        "fehlende Grenzen an Z1 nicht unter „Bitte prüfen“",
    )
    pruefe("Drehachse C4, bis 100 U/min" in uebertragen, "C4 nicht in U/min berichtet")
    pruefe(
        "Beschleunigung von „X1“" in nicht_uebertragen,
        "Beschleunigung von X1 nicht als nicht übertragen berichtet",
    )
    pruefe("Revolver „T“ mit 12 Plätzen" in nicht_uebertragen, "Revolver nicht berichtet")
    pruefe(
        "{" not in uebertragen + zu_pruefen + nicht_uebertragen,
        "Platzhalter im Bericht nicht gefüllt",
    )

    # CAM findet die Maschine; zweiter Export überschreibt statt zu verdoppeln.
    pruefe(
        "Testdrehmaschine" in MachineFactory.list_configurations(),
        f"CAM kennt die Maschine nicht: {MachineFactory.list_configurations()}",
    )
    export.exportiere(ma)
    anzahl = len([n for n in MachineFactory.list_configurations() if n == "Testdrehmaschine"])
    pruefe(anzahl == 1, f"nach zweitem Export {anzahl}× in der Liste")

    # Fehlt ein Pflichtwert, steht das unter „Bitte prüfen“ (B-001).
    betriebsart = {ba.NcName: ba for ba in m.betriebsarten(ma)}
    betriebsart["X1"].Eilgang = 0
    betriebsart["C4"].Geschwindigkeit = 0
    betriebsart["S4"].Drehzahl = 0
    _cam, bericht = export.baue_cam_maschine(ma)
    uebertragen = " ".join(bericht.uebertragen)
    zu_pruefen = " ".join(bericht.zu_pruefen)
    for satz in (
        "„X1“ hat keinen Eilgang – CAM bekommt FreeCADs Vorgabe von 10000 mm/min",
        "„C4“ hat keine Geschwindigkeit – CAM bekommt FreeCADs Vorgabe von 100 U/min",
        "„S4“ hat keine größte Drehzahl – CAM begrenzt die Spindeldrehzahl dann nicht",
    ):
        pruefe(satz in zu_pruefen, f"fehlender Pflichtwert nicht unter „Bitte prüfen“: {satz}")
    pruefe(
        "Spindel S4, ohne größte Drehzahl" in uebertragen and "bis 0 U/min" not in uebertragen,
        f"Spindel ohne Drehzahl: {uebertragen}",
    )

    # Nur eine Begrenzung am Gelenk: auch das steht unter „Bitte prüfen“ (B-002).
    gelenk_z = asm.Document.getObject("Z")
    gelenk_z.EnableLengthMax, gelenk_z.LengthMax = True, 500
    cam, bericht = export.baue_cam_maschine(ma)
    zu_pruefen = " ".join(bericht.zu_pruefen)
    pruefe(
        "„Z1“ hat am Gelenk nur eine Begrenzung" in zu_pruefen
        and "„Z1“ hat am Gelenk keine Begrenzung" not in zu_pruefen,
        f"eine fehlende Begrenzung an Z1: {zu_pruefen}",
    )
    z1 = cam.linear_axes["Z1"]
    pruefe(
        (z1.min_limit, z1.max_limit) == (-export.OHNE_GRENZE_MM, 500),
        f"Z1: Grenzen {z1.min_limit}/{z1.max_limit}",
    )
    App.closeDocument(asm.Document.Name)
    sprache.setze_sprache(sprache_vorher or "")


if not export.verfuegbar():
    # FreeCAD 1.1.x hat keine CAM-Maschinendefinition – dort erklärt der
    # Dialog das; geprüft wird es in szenario_uebergeben.
    print(
        "UEBERSPRUNGEN",
        os.path.basename(__file__) + ": keine CAM-Maschinendefinition in dieser FreeCAD-Version",
    )
else:
    pruefe_export()
    assert not fehler, "\n".join(fehler)
    print("OK", os.path.basename(__file__))
