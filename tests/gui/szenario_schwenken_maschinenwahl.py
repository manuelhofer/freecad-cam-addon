# SPDX-License-Identifier: LGPL-2.1-or-later
"""Jobmaschine behalten, echte Grenzen zeigen und veraltete Freigaben sperren."""

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
    from PySide import QtGui

    from camaddon import beispielmaschine as bm
    from camaddon import gui_schwenken as gs
    from camaddon import reichweite as rw
    from camaddon import simultan_planung as sp
    from camaddon import sprache
    from camaddon import vierachs_rohteil as vr

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
    asm3, ma3 = bm.lade(bm.FRAESE_3)
    pfad3 = str(profil / "dreiachs.FCStd")
    ma3.Document.saveAs(pfad3)
    bm.lade(bm.GROB_G550)  # darf keine fehlenden Achsen der Jobmaschine ersetzen
    doc = App.newDocument("Maschinenwahl")
    doc.UndoMode = 1
    obj = doc.addObject("Part::Feature", "Teil")
    obj.Shape = Part.makeBox(20, 20, 10)
    grund = PathJob.Create("Job", [obj])
    doc.recompute()
    vorher_form = sp._geometrie(vr.modell(grund).Shape)
    rw.merke_maschine(grund, pfad3)
    m, name = gs.maschine_fuer(grund)
    h.pruefe(
        m.pruefung.maschine is ma3 and name == ma3.Label and not m.rundachsen,
        "3-Achs-Maschine durch offene G550 ersetzt",
    )
    panel = gs.SchwenkenPanel(grund)
    Gui.Control.showDialog(panel)
    yield 300
    panel.feld_neigung.setValue(30)
    panel.winkel_nehmen()
    h.pruefe(panel.lage is None, "3-Achs-Fräse schwenkt fiktiv")
    ok = panel._knoepfe.button(QtGui.QDialogButtonBox.Ok)
    h.pruefe(not ok.isEnabled(), "OK bei unerreichbarer Richtung frei")
    h.pruefe("Feste Spindelrichtung" in panel.grenzen_text.text(), "Feste Richtung fehlt")
    h.bild("1_dreiachs", panel.form)
    panel.feld_neigung.setValue(0)
    panel.winkel_nehmen()
    h.pruefe(
        panel.lage is not None and panel.rund == {} and ok.isEnabled(),
        "Feste passende Richtung nicht frei",
    )
    h.pruefe(panel.vorhanden is grund, "Parallele Bearbeitung erzeugt fiktiven Schwenkjob")
    panel.haken_bearbeiten.setChecked(False)
    h.pruefe(panel.accept(), "Grundjob nicht verwendet")
    yield 300
    h.pruefe(
        not any(hasattr(o, "Grundjob") for o in doc.Objects),
        "Fiktive Ebene an 3-Achs-Fräse angelegt",
    )

    asm4, ma4 = bm.lade(bm.DREHMASCHINE)
    pfad4 = str(profil / "vierachs.FCStd")
    ma4.Document.saveAs(pfad4)
    rw.merke_maschine(grund, pfad4)
    m, _name = gs.maschine_fuer(grund)
    h.pruefe(m.pruefung.maschine is ma4, "Dreh-/4-Achs-Maschine ersetzt")
    for a in m.rundachsen:
        h.pruefe(
            (a.minimum, a.maximum) == m.pruefung.verfahren.grenzen(a.achse), "Andere Gelenkgrenzen"
        )

    asm5, ma5 = bm.lade(bm.TISCH_TISCH)
    pfad5 = str(profil / "fuenfachs.FCStd")
    ma5.Document.saveAs(pfad5)
    rw.merke_maschine(grund, pfad5)
    panel = gs.SchwenkenPanel(grund)
    Gui.Control.showDialog(panel)
    yield 300
    panel.feld_neigung.setValue(30)
    panel.feld_richtung.setValue(90)
    panel.winkel_nehmen()
    h.pruefe(
        panel.lage is not None and panel._knoepfe.button(QtGui.QDialogButtonBox.Ok).isEnabled(),
        "5-Achs-Richtung nicht frei",
    )
    h.pruefe(panel.feld_neigung.maximum() == 180, "Pauschale 120°-Neigung geblieben")
    a = next(a for a in panel.maschine.rundachsen if a.buchstabe == "A")
    a.achse.gelenk.EnableAngleMin, a.achse.gelenk.AngleMin = True, -10
    a.achse.gelenk.EnableAngleMax, a.achse.gelenk.AngleMax = True, 10
    vorher = len(doc.Objects)
    panel.haken_bearbeiten.setChecked(False)
    h.pruefe(not panel.accept(), "Veraltete Anschlagfreigabe übernommen")
    h.pruefe(
        len(doc.Objects) == vorher and panel.lage is None, "Halben Job nach neuem Anschlag angelegt"
    )
    h.pruefe(
        "−10°" in panel.grenzen_text.text() and "10°" in panel.grenzen_text.text(),
        "Aktuelle Anschläge fehlen",
    )
    h.pruefe(
        not panel._knoepfe.button(QtGui.QDialogButtonBox.Ok).isEnabled(),
        "OK nach Anschlagänderung frei",
    )
    h.bild("2_anschlag", panel.form)
    panel.reject()
    yield 300
    setattr(grund, rw.EIGENSCHAFT_MASCHINE, str(profil / "nicht_vorhanden.FCStd"))
    m, _name = gs.maschine_fuer(grund)
    h.pruefe(m is None, "Unlesbare Jobmaschine durch offene Maschine ersetzt")
    panel = gs.SchwenkenPanel(grund)
    Gui.Control.showDialog(panel)
    yield 300
    panel.feld_neigung.setValue(30)
    panel.winkel_nehmen()
    h.pruefe(panel.lage is None and not panel.accept(), "Ohne lesbare Maschine fiktiv geplant")
    h.bild("3_ohne_maschine", panel.form)
    panel.reject()
    yield 300
    setattr(grund, rw.EIGENSCHAFT_MASCHINE, "")
    m, _name = gs.maschine_fuer(grund)
    h.pruefe(m is None, "Unter mehreren offenen Maschinen willkürlich gewählt")
    h.pruefe(
        abs(vr.modell(grund).Shape.Volume - 4000) < 1e-8,
        f"Teilvolumen geändert: {vr.modell(grund).Shape.Volume}",
    )
    h.pruefe(
        sp._geometrie(vr.modell(grund).Shape) == vorher_form, "Teil beim Richtungsprüfen geändert"
    )
