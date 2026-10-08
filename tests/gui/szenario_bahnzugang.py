# SPDX-License-Identifier: LGPL-2.1-or-later
"""Gewöhnlicher Bahnabschnitt mit fremder Achse bleibt in Programm und Abspieler aus."""

import os
import pathlib

import FreeCAD as App
import FreeCADGui as Gui
import Part
import Path


def schritte(h):
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.accept()
    yield 500
    import Path.Main.Job as PathJob
    from Path.Tool.camassets import user_asset_store
    from PySide import QtGui

    from camaddon import abfahren as ab
    from camaddon import beispielmaschine as bm
    from camaddon import gui_programm as gp
    from camaddon import job_schnittwerte as js
    from camaddon import reichweite as rw
    from camaddon import sprache
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import werkzeuge as wz

    sprache.setze_sprache("de")
    Gui.doCommand("import FreeCADGui as Gui")
    Gui.doCommand("import FreeCAD as App")
    screen = next(
        s
        for s in QtGui.QApplication.screens()
        if s.name() == os.environ["CAMADDON_GROB_BILDSCHIRM"]
    )
    mw = Gui.getMainWindow()
    mw.windowHandle().setScreen(screen)
    mw.setGeometry(screen.availableGeometry())
    mw.showMaximized()
    yield 500
    h.pruefe(screen.availableGeometry().contains(mw.frameGeometry().center()), "Bildschirm")
    w = wz.standardwerkzeug()
    w.gesamtlaenge = 85
    bib = wz.Bibliothek([w])
    bib.speichern()
    user_asset_store.set_dir(profil / "assets")
    ue.uebergeben(bib)
    asm, ma = bm.lade(bm.FRAESE_3)
    file = str(profil / "maschine.FCStd")
    ma.Document.saveAs(file)
    doc = App.newDocument("GemeinsamerBahnzugang")
    obj = doc.addObject("Part::Feature", "Teil")
    obj.Shape = Part.makeBox(20, 20, 10)
    job = PathJob.Create("Job", [obj])
    doc.recompute()
    e = next(e for e in w.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
    tc = js.controller_ohne_transaktion(doc, job, w, e)
    doc.recompute()
    rw.merke_maschine(job, file)
    ops = []
    for name, foreign in (("UnbearbeiteterBereich", True), ("ErreichbarerBereich", False)):
        op = doc.addObject("Path::Feature", name)
        op.addProperty("App::PropertyLink", "ToolController")
        op.ToolController = tc
        op.addProperty("App::PropertyBool", "Active")
        op.Active = True
        target = {"X": 11, "Y": 5, "Z": 25, "F": float(tc.HorizFeed)}
        if foreign:
            target["A"] = 30
        op.Path = Path.Path(
            [Path.Command("G0", {"X": 10, "Y": 5, "Z": 25}), Path.Command("G1", target)]
        )
        ops.append(op)
    job.Operations.Group = ops
    p = rw.Pruefung(asm, ma)
    fahrt = ab.abfahrt(p, job, rw.nullpunkt(job), bib)
    h.pruefe(
        len(fahrt.operationen) == 1 and fahrt.operationen[0].name == ops[1].Label,
        "Abspieler enthält ausgelassenen Bereich",
    )
    h.pruefe(any("unbearbeitet" in t for t in fahrt.hinweise), "Abspieler-Auslassungsgrund fehlt")
    dlg = gp.ProgrammDialog([job], job)
    dlg.show()
    dlg.move(screen.availableGeometry().topLeft())
    yield 500
    h.pruefe(
        "unbearbeitet" in dlg.hinweise.text() and "A" in dlg.hinweise.text(),
        "Gemeinsame Prüfung im Programmfenster fehlt",
    )
    h.pruefe(dlg._programm().saetze > 0, "Andere erreichbare Operation fehlt")
    h.bild("programm", dlg)
    dlg.reject()
