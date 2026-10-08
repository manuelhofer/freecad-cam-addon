# SPDX-License-Identifier: LGPL-2.1-or-later
"""Räumlichen Rest aus der geprüften 3+2-Gegenprobe sichtbar neben dem Rohteil zeigen."""

import json
import os
import pathlib
import re
import runpy

import FreeCAD as App
import FreeCADGui as Gui


def schritte(h):
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.accept()
    yield 500
    import Mesh
    import numpy as np
    from Path.Tool.camassets import user_asset_store
    from PySide import QtGui

    from camaddon import raum_material as raum
    from camaddon import schwenken as sw

    screens = QtGui.QApplication.screens()
    if len(screens) > 1:
        screen = next(
            (s for s in screens if s.name() == os.environ.get("CAMADDON_GROB_BILDSCHIRM")),
            next(s for s in screens if s != QtGui.QApplication.primaryScreen()),
        )
        mw = Gui.getMainWindow()
        mw.windowHandle().setScreen(screen)
        mw.setGeometry(screen.availableGeometry())
        mw.showMaximized()
        yield 500
        h.pruefe(screen.availableGeometry().contains(mw.frameGeometry().center()), "Bildschirm")
    pfad = os.environ.get("CAMADDON_RAUM_DATEN")
    if pfad is None:
        # Auch der reguläre GUI-Prüfläufer muss das Szenario ohne einen privaten
        # vorbereiteten Datenordner ausführen können.
        Gui.doCommand("import FreeCADGui as Gui")
        Gui.doCommand("import FreeCAD as App")
        runpy.run_path(
            str(pathlib.Path(__file__).resolve().parents[1] / "test_raum_material.py"),
            run_name="raum_fixture",
        )
    daten = pathlib.Path(pfad) if pfad is not None else profil
    user_asset_store.set_dir(daten / "assets")
    doc = App.openDocument(str(daten / "raeumlicher_materialstand.FCStd"))
    job = sw.ebenen_von(doc.Job)[1]
    vorher = raum.Material(doc.Job.Stock.Shape, 0.5)
    nachher = raum.fuer_ebene(job, 0.5)
    h.pruefe(nachher is not None, "Räumlicher Rest fehlt")
    h.pruefe(
        nachher.belegt([[5, 13, 10], [5, 13, 2], [5, 13, 18]]).tolist() == [False, True, True],
        "Dach/Boden/Hohlraum",
    )
    ansicht = App.newDocument("RaeumlicherRest")
    # Eine Hälfte in Y zeigt den Hohlraum. Alle Boxen entsprechen tatsächlichen
    # Materialabschnitten, ohne sie für die Anzeige zu einem Höhenfeld aufzufüllen.
    for stand, name, versatz, farbe in (
        (vorher, "Rohteil mit Hohlraum", 0, (0.75, 0.75, 0.78)),
        (nachher, "Rest nach Seitenschnitt", 72, (0.95, 0.65, 0.2)),
    ):
        dreiecke = []
        for i, x in enumerate(stand.x):
            for j, y in enumerate(stand.y):
                if y > 13:
                    continue
                for unten, oben in stand.grenzen[i, j]:
                    if not np.isfinite(unten):
                        continue
                    ecken = [
                        (x + versatz + sx * stand.dx / 2, y + sy * stand.dy / 2, z)
                        for z in (unten, oben)
                        for sy in (-1, 1)
                        for sx in (-1, 1)
                    ]
                    for a, b, c, d in (
                        (0, 1, 3, 2),
                        (4, 6, 7, 5),
                        (0, 4, 5, 1),
                        (2, 3, 7, 6),
                        (0, 2, 6, 4),
                        (1, 5, 7, 3),
                    ):
                        dreiecke.extend(
                            [(ecken[a], ecken[c], ecken[b]), (ecken[a], ecken[d], ecken[c])]
                        )
        obj = ansicht.addObject("Mesh::Feature", "Material")
        obj.Label = name
        obj.Mesh = Mesh.Mesh(dreiecke)
        obj.ViewObject.ShapeColor = farbe
        obj.ViewObject.Visibility = True
    ansicht.recompute()
    h.pruefe(
        len(ansicht.Objects) == 2 and ansicht.Objects[1].Mesh.BoundBox.XMax == 132,
        "Beide Materialmodelle vollständig",
    )
    Gui.activateWorkbench("PartWorkbench")
    yield 500
    Gui.activeDocument().activeView().viewIsometric()
    Gui.activeDocument().activeView().fitAll()
    yield 500
    view = Gui.activeDocument().activeView()
    # Native Mesh-Ansichten starten hier mit focalDistance=1: fitAll setzt die
    # Kamera in die Szene. Den bekannten Vergleichsrahmen mit der öffentlichen
    # Kamera-API vollständig umfassen, ohne einen Ausschnitt nachträglich zu bearbeiten.
    rueck = view.getCameraOrientation().multVec(App.Vector(0, 0, 1))
    position = App.Vector(66, 6.5, 10) + rueck * 200
    kamera = view.getCamera()
    for feld, wert in (
        ("position", f"{position.x} {position.y} {position.z}"),
        ("focalDistance", "200"),
        ("nearDistance", "1"),
        ("farDistance", "1000"),
        ("height", "90"),
    ):
        kamera = re.sub(rf"(?m)^\s*{feld}[^\n]*", f"  {feld} {wert}", kamera)
    view.setCamera(kamera)
    yield 500
    daten_ansicht = {
        "aktiv": App.ActiveDocument.Name,
        "kamera": Gui.activeDocument().activeView().getCamera(),
        "objekte": [
            {
                "name": o.Name,
                "facetten": o.Mesh.CountFacets,
                "bbox": str(o.Mesh.BoundBox),
                "sichtbar": o.ViewObject.Visibility,
                "farbe": list(o.ViewObject.ShapeColor),
            }
            for o in ansicht.Objects
        ],
    }
    (pathlib.Path(os.environ["CAMADDON_AUSGABE"]) / "lage.json").write_text(
        json.dumps(daten_ansicht, indent=2)
    )
    Gui.activeDocument().activeView().saveImage(
        str(pathlib.Path(os.environ["CAMADDON_AUSGABE"]) / "material.png"), 1280, 760, "Current"
    )
    h.bild("fenster")
