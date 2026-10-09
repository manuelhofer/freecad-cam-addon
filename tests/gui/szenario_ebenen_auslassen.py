# SPDX-License-Identifier: LGPL-2.1-or-later
"""Ausgelassene Ebenen im Programm und tatsächlich stehen gebliebenes Material zeigen."""

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
    from PySide import QtGui

    from camaddon import gui_programm as gp
    from camaddon import sprache

    sprache.setze_sprache("de")
    Gui.doCommand("import FreeCADGui as Gui")
    Gui.doCommand("import FreeCAD as App")
    # Der zweite Bildschirm (CAMADDON_GROB_BILDSCHIRM), wenn es ihn gibt – sonst der erste
    # (unter Xvfb gibt es nur einen).
    screen = next(
        (
            s
            for s in QtGui.QApplication.screens()
            if s.name() == os.environ.get("CAMADDON_GROB_BILDSCHIRM")
        ),
        QtGui.QApplication.primaryScreen(),
    )
    mw = Gui.getMainWindow()
    mw.windowHandle().setScreen(screen)
    mw.setGeometry(screen.availableGeometry())
    mw.showMaximized()
    yield 500
    h.pruefe(screen.availableGeometry().contains(mw.frameGeometry().center()), "Bildschirm")
    fixture = runpy.run_path(
        str(pathlib.Path(__file__).resolve().parents[1] / "test_ebenen_auslassen.py"),
        run_name="ebenen_fixture",
    )
    daten, (doc, ma, grund, gefraest, ungefraest) = fixture["gegenprobe"](profil, behalten=True)
    ansicht = App.newDocument("UnbearbeiteteBereiche")
    # Native Meshes aus denselben getrennten Materialintervallen. Rot ist ausschließlich
    # der tatsächliche Unterschied zum bearbeitbaren Fall; Dach und Boden bleiben grau.
    for stand, versatz in ((gefraest, 0), (ungefraest, 72)):
        grau, rot = [], []
        for i, x in enumerate(stand.x):
            for j, y in enumerate(stand.y):
                if y > 13:
                    continue
                vorher = gefraest.grenzen[i, j]
                for u, v in stand.grenzen[i, j]:
                    if not np.isfinite(u):
                        continue
                    cuts = sorted(
                        {
                            float(u),
                            float(v),
                            *(float(z) for z in vorher.ravel() if np.isfinite(z) and u < z < v),
                        }
                    )
                    for low, high in zip(cuts, cuts[1:], strict=False):
                        middle = (low + high) / 2
                        belegt = any(a <= middle <= b for a, b in vorher if np.isfinite(a))
                        out = rot if versatz and not belegt else grau
                        corners = [
                            (x + versatz + sx * stand.dx / 2, y + sy * stand.dy / 2, z)
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
                            out.extend(
                                [
                                    (corners[a], corners[c], corners[b]),
                                    (corners[a], corners[d], corners[c]),
                                ]
                            )
        for tris, name, color in (
            (
                grau,
                "Rest bei weitem Schwenkbereich" if not versatz else "Rest bei A ±10°",
                (0.75, 0.75, 0.78),
            ),
            (rot, "Unbearbeitet – Seitenschnitt ausgelassen", (0.95, 0.3, 0.12)),
        ):
            if not tris:
                continue
            obj = ansicht.addObject("Mesh::Feature", "Material")
            obj.Label = name
            obj.Mesh = Mesh.Mesh(tris)
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.Visibility = True
    ansicht.recompute()
    Gui.activateWorkbench("PartWorkbench")
    App.setActiveDocument(ansicht.Name)
    mdi = mw.findChild(QtGui.QMdiArea)
    fenster = (
        next((w for w in mdi.subWindowList() if ansicht.Name in w.windowTitle()), None)
        if mdi is not None
        else None
    )
    if fenster is not None:
        mdi.setActiveSubWindow(fenster)
    yield 500
    view = Gui.getDocument(ansicht.Name).activeView()
    view.viewIsometric()
    view.fitAll()
    yield 500
    rueck = view.getCameraOrientation().multVec(App.Vector(0, 0, 1))
    pos = App.Vector(66, 6.5, 10) + rueck * 200
    camera = view.getCamera()
    for field, value in (
        ("position", f"{pos.x} {pos.y} {pos.z}"),
        ("focalDistance", "200"),
        ("nearDistance", "1"),
        ("farDistance", "1000"),
        ("height", "90"),
    ):
        camera = re.sub(rf"(?m)^\s*{field}[^\n]*", f"  {field} {value}", camera)
    view.setCamera(camera)
    yield 500
    out = pathlib.Path(os.environ["CAMADDON_AUSGABE"])
    ansicht.saveAs(str(out / "unbearbeitet.FCStd"))
    (out / "ansicht.json").write_text(
        json.dumps(
            {
                "aktiv": App.ActiveDocument.Name,
                "vergleich": ansicht.Name,
                "objekte": [
                    {"name": o.Label, "bbox": str(o.Mesh.BoundBox), "facetten": o.Mesh.CountFacets}
                    for o in ansicht.Objects
                ],
            },
            indent=2,
        )
    )
    view.saveImage(str(out / "unbearbeitet.png"), 1280, 760, "Current")
    h.pruefe(
        len(ansicht.Objects) == 3 and ansicht.Objects[-1].Mesh.CountFacets > 0,
        "Unbearbeitetes Material nicht separat dargestellt",
    )
    h.pruefe(fenster is not None, "Vergleichsfenster nicht sichtbar ausgewählt")
    (out / "material.json").write_text(json.dumps(daten, indent=2, ensure_ascii=False))
    dlg = gp.ProgrammDialog([grund], grund)
    dlg.show()
    dlg.move(screen.availableGeometry().topLeft())
    yield 500
    h.pruefe(
        "unbearbeitet" in dlg.hinweise.text(),
        "Ausgelassener Ebenenbereich im Programmfenster fehlt",
    )
    h.pruefe(dlg._programm().saetze > 0, "Andere erreichbare Ebene fehlt im Programm")
    h.bild("programm", dlg)
    dlg.reject()
