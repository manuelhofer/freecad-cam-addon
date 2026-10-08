# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tatsächliche getrennte Materialabschnitte vor/nach bewegter Schneide sichtbar prüfen."""

import json
import os
import pathlib
import re
import runpy

import FreeCAD as App
import FreeCADGui as Gui


def schritte(h):
    """Native Mesh-Ansicht der gemessenen räumlichen Materialintervalle."""
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    yield 500
    modal = h.modal()
    if modal is not None:
        modal.liste.setCurrentIndex(modal.liste.findData("de"))
        modal.accept()
    import Mesh
    import numpy as np
    from PySide import QtGui

    Gui.doCommand("import FreeCADGui as Gui")
    Gui.doCommand("import FreeCAD as App")
    datei = os.environ.get("CAMADDON_RAUMBAHN_DATEN")
    if datei is None:
        fixture = runpy.run_path(
            str(pathlib.Path(__file__).parents[1] / "test_raum_bahn.py"),
            run_name="raumbahn_fixture",
        )
        fixture["pruefen"]()
        datei = str(profil / "raum_bahn_daten.npz")
    data = np.load(datei)
    screen = next(
        s
        for s in QtGui.QApplication.screens()
        if s.name() == os.environ["CAMADDON_GROB_BILDSCHIRM"]
    )
    mw = Gui.getMainWindow()
    mw.showNormal()
    mw.windowHandle().setScreen(screen)
    mw.setGeometry(screen.availableGeometry())
    mw.showMaximized()
    doc = App.newDocument("RestNachSchwenkbewegung")
    for name, key, offset, color in (
        ("Rohteil mit Hohlraum", "vorher", 0, (0.75, 0.75, 0.78)),
        ("Rest nach bewegter Schneide", "nachher", 38, (0.95, 0.65, 0.2)),
    ):
        tris = []
        for i, x in enumerate(data["x"]):
            for j, y in enumerate(data["y"]):
                if y < 12:
                    continue
                for low, high in data[key][i, j]:
                    if not np.isfinite(low):
                        continue
                    points = [
                        (x + offset + sx * float(data["dx"]) / 2, y + sy * float(data["dy"]) / 2, z)
                        for z in (low, high)
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
                        tris.extend(
                            ((points[a], points[c], points[b]), (points[a], points[d], points[c]))
                        )
        obj = doc.addObject("Mesh::Feature", "Material")
        obj.Label = name
        obj.Mesh = Mesh.Mesh(tris)
        obj.ViewObject.ShapeColor = color
        h.pruefe(obj.Mesh.CountFacets > 100, "Materialkörper fehlt")
    doc.recompute()
    Gui.activateWorkbench("PartWorkbench")
    App.setActiveDocument(doc.Name)
    mw.setActiveWindow(Gui.getDocument(doc.Name).mdiViewsOfType("Gui::View3DInventor")[0])
    view = Gui.getDocument(doc.Name).activeView()
    view.viewIsometric()
    back = view.getCameraOrientation().multVec(App.Vector(0, 0, 1))
    pos = App.Vector(34, 18, 10) + back * 200
    camera = view.getCamera()
    for field, value in (
        ("position", f"{pos.x} {pos.y} {pos.z}"),
        ("focalDistance", "200"),
        ("nearDistance", "1"),
        ("farDistance", "1000"),
        ("height", "64"),
    ):
        camera = re.sub(rf"(?m)^\s*{field}[^\n]*", f"  {field} {value}", camera)
    view.setCamera(camera)
    yield 500
    out = pathlib.Path(os.environ["CAMADDON_AUSGABE"])
    view.saveImage(str(out / "raumvergleich.png"), 1280, 760, "Current")
    h.pruefe(screen.availableGeometry().contains(mw.frameGeometry().center()), "Bildschirm")
    (out / "ansicht.json").write_text(
        json.dumps(
            {
                "bildschirm": mw.windowHandle().screen().name(),
                "fenster": [mw.x(), mw.y(), mw.width(), mw.height()],
                "objekte": [o.Label for o in doc.Objects],
            }
        )
    )
