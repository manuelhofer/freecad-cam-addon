# SPDX-License-Identifier: LGPL-2.1-or-later
"""Teilabschnitte eines einzelnen Schnittzugs, neue Verbindungen und unbearbeitetes Material."""

import json
import os
import pathlib
import re
import runpy

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui


def schritte(h):
    """Native Teilbahn im Prüffenster abspielen und dieselben Auslassungen exportieren."""
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    yield 500
    modal = h.modal()
    if modal is not None:
        modal.liste.setCurrentIndex(modal.liste.findData("de"))
        modal.accept()
    yield 500
    screen = next(
        (
            s
            for s in QtGui.QApplication.screens()
            if s.name() == os.environ.get("CAMADDON_BILDSCHIRM", "DP-1")
        ),
        QtGui.QApplication.primaryScreen(),
    )
    mw = Gui.getMainWindow()
    mw.showNormal()
    mw.windowHandle().setScreen(screen)
    mw.setGeometry(screen.availableGeometry())
    mw.showMaximized()
    Gui.doCommand("import FreeCADGui as Gui")
    Gui.doCommand("import FreeCAD as App")
    fixture = runpy.run_path(
        str(pathlib.Path(__file__).parents[1] / "test_simultan_schnittbereiche.py"),
        run_name="schnittbereiche_fixture",
    )
    doc, job, op, bib, m = fixture["aufbauen"](profil)
    from camaddon import gui_programm as gp
    from camaddon import gui_reichweite as gr
    from camaddon import reichweite as rw
    from camaddon import simultan_restbild as sr

    md = m.pruefung.maschine.Document
    datei = str(profil / "maschine.FCStd")
    md.saveAs(datei)
    rw.merke_maschine(job, datei)
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    Gui.runCommand("CamAddon_AufMaschinePruefen")
    yield from h.warte_auf(lambda: gr.PruefPanel.offen is not None, 10000)
    panel = gr.PruefPanel.offen
    yield from h.warte_auf(lambda: panel.abfahrt is not None and panel.bild is not None, 15000)
    h.pruefe(len(panel.abfahrt.operationen) == 1, "Erreichbare Schnittzüge fehlen")
    h.pruefe(any("Bahnpunkt" in t for t in panel.abfahrt.hinweise), "Teilbereichsgrund fehlt")
    bild = panel.bild
    h.pruefe(
        isinstance(bild.abtrag, sr.SimultanRestbild), "Tatsächliche Teilbahn ohne Materialbild"
    )
    panel.abspieler.springe_zu_station(len(panel.abfahrt.stationen) - 1)
    yield 400
    h.pruefe(
        bild._am_ende and bild.bahn_schalter.whichChild.getValue() == -1, "Endvergleich verdeckt"
    )
    q = bild.abtrag.quader
    heights = [float(q.h[abs(q.x - 20).argmin(), abs(q.y - y).argmin()]) for y in (10, 30, 50)]
    h.pruefe(
        heights[0] < 11.2 and heights[1] == 11.2 and heights[2] < 11.2,
        "Fehlender Schnitt wird abgetragen",
    )
    App.setActiveDocument(md.Name)
    mw.setActiveWindow(Gui.getDocument(md.Name).mdiViewsOfType("Gui::View3DInventor")[0])
    for obj in md.Objects:
        if hasattr(obj, "Shape"):
            obj.ViewObject.hide()
    for _aufnahme, _knoten, _lage, wahl, _werkzeuge in bild._plaetze:
        wahl.whichChild = -1
    panel.abspieler.haken_teil.setChecked(False)
    view = bild.ansicht
    view.viewIsometric()
    from camaddon import maschine as mm

    lage = mm.globale_platzierung(panel.pruefung.werkstueckaufnahme.Lcs).multiply(
        App.Placement(panel.nullpunkt(), App.Rotation())
    )
    center = lage.multVec(job.Stock.Shape.BoundBox.Center)
    bild.zeige_stelle(center)
    camera = view.getCamera()
    back = view.getCameraOrientation().multVec(App.Vector(0, 0, 1))
    pos = center + back * 200
    for field, value in (
        ("position", f"{pos.x} {pos.y} {pos.z}"),
        ("focalDistance", "200"),
        ("nearDistance", "1"),
        ("farDistance", "1000"),
        ("height", "80"),
    ):
        camera = re.sub(rf"(?m)^\s*{field}[^\n]*", f"  {field} {value}", camera)
    view.setCamera(camera)
    yield 500
    out = pathlib.Path(os.environ["CAMADDON_AUSGABE"])
    view.saveImage(str(out / "material.png"), 1000, 750, "Current")
    h.bild("prueffenster", panel.form)
    panel.abspieler.springe_zu_station(0)
    h.pruefe((q.h == 11.2).all(), "Zurückspulen verliert unbearbeiteten Rest")
    panel.reject()
    dlg = gp.ProgrammDialog([job], job)
    dlg.show()
    dlg.windowHandle().setScreen(screen)
    dlg.move(screen.availableGeometry().topLeft())
    yield 500
    h.pruefe(
        "Bahnpunkt" in dlg.hinweise.text() and "unbearbeitet" in dlg.hinweise.text(),
        "Programm ohne Restbericht",
    )
    h.pruefe(dlg._programm().saetze > 0, "Alle Schnittzüge ausgelassen")
    h.bild("programm", dlg)
    h.pruefe(
        screen.availableGeometry().contains(mw.frameGeometry().center()), "Falscher Bildschirm"
    )
    (out / "material.json").write_text(
        json.dumps({"hoehen": heights, "bildschirm": mw.windowHandle().screen().name()})
    )
    dlg.reject()
