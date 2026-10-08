# SPDX-License-Identifier: LGPL-2.1-or-later
"""Ein gerades und ein gewinkeltes Jobwerkzeug ändern den realen Maschinenzugang."""

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
    from camaddon import gui_schwenken as gs
    from camaddon import halter as hl
    from camaddon import job_schnittwerte as js
    from camaddon import reichweite as rw
    from camaddon import sprache
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import werkzeuge as wz

    sprache.setze_sprache("de")
    Gui.doCommand("import FreeCADGui as Gui")
    Gui.doCommand("import FreeCAD as App")
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
    user_asset_store.set_dir(profil / "assets")
    gerade = wz.standardwerkzeug()
    gerade.gesamtlaenge = 85
    h1 = hl.aus_vorlage("er25")
    gerade.halter = h1.kennung
    gewinkelt = wz.Werkzeug.aus_dict(gerade.als_dict())
    gewinkelt.kennung, gewinkelt.nummer, gewinkelt.name = "winkelhalter12", 8, "VHM 12 gewinkelt"
    h8 = hl.aus_vorlage("vdi30_radial")
    gewinkelt.halter = h8.kennung
    bib = wz.Bibliothek([gerade, gewinkelt])
    bib.halter = [h1, h8]
    bib.speichern()
    ue.uebergeben(bib)
    asm, ma = bm.lade(bm.FRAESE_3)
    datei = str(profil / "maschine3.FCStd")
    ma.Document.saveAs(datei)
    doc = App.newDocument("Werkzeugzugang")
    doc.UndoMode = 1
    obj = doc.addObject("Part::Feature", "Teil")
    obj.Shape = Part.makeBox(20, 20, 10)
    job = PathJob.Create("Job", [obj])
    doc.recompute()
    einsatz = next(e for e in gerade.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
    tc1 = js.controller_ohne_transaktion(doc, job, gerade, einsatz)
    tc8 = js.controller_ohne_transaktion(doc, job, gewinkelt, einsatz)
    doc.recompute()
    rw.merke_maschine(job, datei)
    panel = gs.SchwenkenPanel(job)
    Gui.Control.showDialog(panel)
    yield 300
    panel.werkzeugwahl.setCurrentIndex(panel.werkzeugwahl.findData(tc1.Name))
    panel.feld_neigung.setValue(0)
    panel.winkel_nehmen()
    h.pruefe(
        panel.lage is not None and panel.rund == {}, "Gerades Werkzeug nicht senkrecht erreichbar"
    )
    panel.werkzeugwahl.setCurrentIndex(panel.werkzeugwahl.findData(tc8.Name))
    h.pruefe(
        panel.lage is None and not panel._knoepfe.button(QtGui.QDialogButtonBox.Ok).isEnabled(),
        "Gewinkelter Halter behält falsche Z-Freigabe",
    )
    h.pruefe(
        (panel.maschine.richtung({}) - rw.einspannung(tc8, bib).achse()).Length < 1e-8,
        "Halterlage nicht gelesen",
    )
    panel.feld_neigung.setValue(90)
    panel.feld_richtung.setValue(180)
    panel.winkel_nehmen()
    h.pruefe(
        panel.lage is not None and panel.rund == {},
        "Reale seitliche Werkzeugrichtung nicht erreichbar",
    )
    h.bild("1_gewinkeltes_werkzeug", panel.form)
    # Eine Änderung außerhalb des Dokuments invalidiert ebenfalls die Freigabe.
    h8.drehung = 90
    bib.speichern()
    vorher = len(doc.Objects)
    panel.haken_bearbeiten.setChecked(False)
    h.pruefe(not panel.accept() and len(doc.Objects) == vorher, "Veraltete Halterlage übernommen")
    h.pruefe(panel.lage is None, "Freigabe nach Halteränderung geblieben")
    h.bild("2_halter_geaendert", panel.form)
    panel.reject()
    yield 300
    # Die gültige seitliche Lage muss auch einen echten, rücknehmbaren Job anlegen.
    h8.drehung = 0
    bib.speichern()
    panel = gs.SchwenkenPanel(job)
    Gui.Control.showDialog(panel)
    yield 300
    panel.werkzeugwahl.setCurrentIndex(panel.werkzeugwahl.findData(tc8.Name))
    panel.feld_neigung.setValue(90)
    panel.feld_richtung.setValue(180)
    panel.winkel_nehmen()
    panel.haken_bearbeiten.setChecked(False)
    vorher = len(doc.Objects)
    namen_vorher = [o.Name for o in doc.Objects]
    h.pruefe(panel.accept(), "Gültige gewinkelte Lage nicht übernommen")
    from camaddon import schwenken as sw

    ebenen = sw.ebenen_von(job)
    h.pruefe(
        len(ebenen) == 1
        and sw.normale_der(ebenen[0].Ebene).dot(App.Vector(-1, 0, 0)) > 1 - 1e-8
        and not sw.rundachsen_von(ebenen[0]),
        "Seitlicher Job hat falsche Richtung oder erfundene Rundachsen",
    )
    doc.undo()
    doc.recompute()
    pathlib.Path(os.environ["CAMADDON_AUSGABE"], "uebernahme.json").write_text(
        json.dumps(
            {
                "vorher": namen_vorher,
                "nachher": [o.Name for o in doc.Objects],
                "ebenen": [e.Name for e in sw.ebenen_von(job)],
                "undo": doc.UndoMode,
            },
            indent=2,
        )
    )
    h.pruefe(not sw.ebenen_von(job) and js.jobs(doc) == [job], "Rücknahme des Ebenenjobs")
    yield 300
    asm4, ma4 = bm.lade(bm.DREHMASCHINE)
    datei4 = str(profil / "maschine4.FCStd")
    ma4.Document.saveAs(datei4)
    rw.merke_maschine(job, datei4)
    m, _name = gs.maschine_fuer(job, tc8)
    h.pruefe(
        m is not None and m.aufnahme.Platz == 8, "Werkzeugnummer 8 benutzt fälschlich Aufnahme 1"
    )
    m1, _name = gs.maschine_fuer(job, tc1)
    h.pruefe(
        m1 is not None and m1.aufnahme.Platz == 1 and m1.aufnahme is not m.aufnahme,
        "Verschiedene Revolverplätze vermischt",
    )
    # Entfernte Werkzeuge oder ein leerer Job sind keine nominelle Ersatzspindel.
    job.Tools.Group = []
    panel = gs.SchwenkenPanel(job)
    Gui.Control.showDialog(panel)
    yield 300
    panel.feld_neigung.setValue(90)
    panel.winkel_nehmen()
    h.pruefe(
        panel.lage is None and "Werkzeug" in panel.ergebnis.text() and not panel.accept(),
        "Ohne Werkzeug fiktiv geplant",
    )
    panel.reject()
