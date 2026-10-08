# SPDX-License-Identifier: LGPL-2.1-or-later
"""Programmfenster behält feste/einzelne reale Achsen und zeigt unbearbeitete Operationen."""

import json
import os
import pathlib

import FreeCAD as App
import FreeCADGui as Gui
import Part


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

    from camaddon import beispielmaschine as bm
    from camaddon import gui_programm as gp
    from camaddon import job_schnittwerte as js
    from camaddon import postprozessor as pp
    from camaddon import reichweite as rw
    from camaddon import schlichten3d as s3
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
    user_asset_store.set_dir(profil / "assets")
    kugel = wz.standardwerkzeug()
    kugel.kennung = "gui_richtungskugel12"
    kugel.art = wz.KUGELFRAESER
    kugel.eckradius = kugel.durchmesser / 2
    kugel.gesamtlaenge = 85
    bib = wz.Bibliothek([kugel])
    bib.speichern()
    ue.uebergeben(bib)
    asm, ma = bm.lade(bm.FRAESE_3)
    datei = str(profil / "maschine3.FCStd")
    ma.Document.saveAs(datei)
    doc = App.newDocument("Maschinenrichtungen")
    obj = doc.addObject("Part::Feature", "Teil")
    kappe = Part.makeSphere(30, App.Vector(10, 10, -17)).common(
        Part.makeBox(20, 20, 10, App.Vector(0, 0, 5))
    )
    obj.Shape = Part.makeBox(20, 20, 5).fuse(kappe).removeSplitter()
    job = PathJob.Create("Job", [obj])
    doc.recompute()
    einsatz = next(e for e in kugel.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
    tc = js.controller_ohne_transaktion(doc, job, kugel, einsatz)
    doc.recompute()
    faces = [
        f"Face{i+1}"
        for i, f in enumerate(job.Model.Group[0].Shape.Faces)
        if isinstance(f.Surface, Part.Sphere)
    ]
    op = s3.lege_an(job, tc, 0.02, flaechen=faces)
    op.Anstellen = True
    doc.recompute()
    h.pruefe(
        any(c.Name == "G1" for c in op.Path.Commands) and bool(op.Werkzeugachsen),
        "Native Anstelloperation ohne Schnittbahn",
    )
    rw.merke_maschine(job, datei)
    m = gp._maschine_je_operation(job, ma.Document)(op)
    h.pruefe(m is not None and not m.rundachsen, "Programm verliert feste reale Maschine")
    abschnitte = gp.abschnitte_mit_maschine(job, (ma.Label, datei, ma.Document))
    pathlib.Path(os.environ["CAMADDON_AUSGABE"], "diagnose.json").write_text(
        json.dumps(
            {
                "anstellen": op.Anstellen,
                "winkel": float(op.Anstellwinkel),
                "achsen": [list(a) for a in op.Werkzeugachsen],
                "quelle": [c.toGCode() for c in op.Path.Commands],
                "abschnitte": [
                    {"hinweis": a.hinweis, "befehle": [c.toGCode() for c in a.befehle]}
                    for a in abschnitte
                ],
            },
            indent=2,
        )
    )
    h.pruefe(
        len(abschnitte) == 1
        and not abschnitte[0].befehle
        and "unbearbeitet" in abschnitte[0].hinweis,
        "Senkrechte Ersatzbahn im Programm",
    )
    dlg = gp.ProgrammDialog([job], job)
    dlg.windowHandle().setScreen(screen) if dlg.windowHandle() is not None else None
    dlg.show()
    dlg.move(screen.availableGeometry().topLeft())
    yield 500
    h.pruefe("unbearbeitet" in dlg.hinweise.text(), "Auslassung im Fenster fehlt")
    h.pruefe(dlg._programm().saetze == 0, "Ausgelassene Operation erzeugt Bewegungssätze")
    h.bild("1_unbearbeitet", dlg)
    dlg.reject()
    yield 300
    asm4, ma4 = bm.lade(bm.DREHMASCHINE)
    datei4 = str(profil / "maschine4.FCStd")
    ma4.Document.saveAs(datei4)
    m4 = gp._maschine_je_operation(job, ma4.Document)(op)
    h.pruefe(
        m4 is not None and len(m4.rundachsen) == 1,
        "Programm verliert tatsächliche einzelne Rundachse",
    )
    # Ein zulässiges senkrechtes Werkzeug wird ausdrücklich so eingestellt, nie als Fehlerersatz.
    op.Anstellwinkel = 0
    op.recompute()
    out, hint = pp._simultan(op, m4)
    h.pruefe(bool(out) and not hint, f"Reale einrundachsige Richtung nicht ausgegeben: {hint}")
    h.pruefe(not any(set(c.Parameters) & set("AB") for c in out), "Fiktive A/B-Achse im Programm")
