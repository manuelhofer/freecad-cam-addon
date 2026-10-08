# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das gespeicherte 5-Achs-Beispiel wie den 4-Achs-Materialvergleich bedienen."""

import json
import os
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui


def schritte(h):
    """Materialfarben, Sollteil, Bahn und Zurückspulen im tatsächlichen Prüffenster."""
    profil = Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and Path(App.getUserAppDataDir()).resolve() == profil
    yield 500
    modal = h.modal()
    if modal is not None:
        modal.liste.setCurrentIndex(modal.liste.findData("de"))
        modal.wahl_dezimalzeichen.setCurrentIndex(modal.wahl_dezimalzeichen.findData(","))
        modal.accept()
    fenster = Gui.getMainWindow()
    screens = QtGui.QApplication.screens()
    if len(screens) > 1:
        secondary = next(
            (s for s in screens if s.name() == os.environ.get("CAMADDON_GROB_BILDSCHIRM")),
            next(s for s in screens if s is not QtGui.QApplication.primaryScreen()),
        )
        rect = secondary.availableGeometry()
        fenster.showNormal()
        fenster.windowHandle().setScreen(secondary)
        fenster.setGeometry(rect.x() + 20, rect.y() + 40, 1200, 900)
    from Path.Tool.camassets import user_asset_store

    from camaddon import gui_reichweite as gr
    from camaddon import maschine as m
    from camaddon import reichweite as rw
    from camaddon import simultan_restbild as sb
    from camaddon import sprache
    from camaddon import werkzeuge as wz

    sprache.setze_sprache("de")
    out = Path(__file__).resolve().parents[2] / "beispiele/grob_g550_freiform"
    user_asset_store.set_dir(out / "assets")
    wz.Bibliothek.laden(str(out / "beispiel_werkzeuge.json")).speichern()
    md = App.openDocument(str(out / "g550_winkelaufnahme.FCStd"))
    doc = App.openDocument(str(out / "freiform_5achs.FCStd"))
    rw.merke_maschine(doc.Job, str(out / "g550_winkelaufnahme.FCStd"))
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Job)
    Gui.runCommand("CamAddon_AufMaschinePruefen")
    yield from h.warte_auf(lambda: gr.PruefPanel.offen is not None, 10000)
    panel = gr.PruefPanel.offen
    assert panel is not None
    yield from h.warte_auf(lambda: panel.abfahrt is not None and panel.bild is not None, 120000)
    assert isinstance(panel.bild.abtrag, sb.SimultanRestbild)
    bild = panel.bild
    h.pruefe(
        bild._bahn_operation.getNumChildren() == len(panel.abfahrt.operationen),
        "Keine getrennten Bahnen je Operation",
    )
    for nummer in range(len(panel.abfahrt.operationen)):
        station = next(
            i for i, s in enumerate(panel.abfahrt.stationen) if s.operation == nummer and s.satz
        )
        panel.abspieler.springe_zu_station(station)
        h.pruefe(bild._bahn_operation.whichChild.getValue() == nummer, "Falsche Operationsbahn")
        vorher = bild.bahn_schalter.whichChild.getValue()
        bild.hinsehen()
        h.pruefe(
            bild.bahn_schalter.whichChild.getValue() == vorher,
            "Nahblick lässt die Operationsbahn ausgeblendet",
        )
        linien = bild._bahn_operation.getChild(nummer)
        for k in range(linien.getNumChildren()):
            knoten = linien.getChild(k)
            if knoten.getTypeId().getName() == "SoIndexedLineSet":
                stellen = knoten.coordIndex.getValues()
                for i in range(1, len(stellen), 3):
                    h.pruefe(
                        panel.abfahrt.stationen[stellen[i]].operation == nummer,
                        "Bahn enthält eine andere Operation",
                    )
    panel.abspieler.springe_zu_station(len(panel.abfahrt.stationen) - 1)
    yield 500
    bild = panel.bild
    bild.hinsehen()
    kamera = bild.ansicht.getCameraNode()
    h.pruefe(
        not hasattr(kamera, "height") or kamera.height.getValue() < 200,
        "Home-Werkzeug vergrößert den Materialvergleich",
    )
    h.pruefe(bild._am_ende, "Kein Materialvergleich am Ende")
    h.pruefe(bild.bahn_schalter.whichChild.getValue() == -1, "Bahn verdeckt die Materialfarben")
    h.pruefe(bild._rest_material.diffuseColor.getNum() > 100, "Keine Materialfarben")
    h.pruefe("Materialvorschau" in panel.abspieler.rest.text(), "Vorschau nicht erklärt")
    panel.abspieler.haken_teil.setChecked(False)
    h.pruefe(bild.modell_schalter.whichChild.getValue() == -1, "Sollteil bleibt eingeblendet")
    h.pruefe(bild._rest_material.transparency[0] == 0, "Material nicht deckend")
    panel.abspieler.haken_teil.setChecked(True)
    h.pruefe(bild.modell_schalter.whichChild.getValue() == 0, "Sollteil nicht wieder da")

    # Die native 3D-Ansicht zeigt das Werkstück in seiner tatsächlichen Maschinenstellung.
    md = panel.assembly.Document
    App.setActiveDocument(md.Name)
    fenster.setActiveWindow(Gui.getDocument(md.Name).mdiViewsOfType("Gui::View3DInventor")[0])
    lage = m.globale_platzierung(panel.pruefung.werkstueckaufnahme.Lcs).multiply(
        App.Placement(panel.nullpunkt(), App.Rotation())
    )
    view = bild.ansicht
    for obj in md.Objects:
        if obj.TypeId in ("Assembly::AssemblyObject", "App::Part", "Part::Box", "Part::Cylinder"):
            obj.Visibility = True
    md.getObject("Joints").Visibility = False
    # Für das Detailbild die großen Maschinenkörper ausblenden; das Materialbild bleibt
    # unverändert in der tatsächlichen Maschinenstellung im nativen Coin-Szenengraphen.
    sichtbar = [(o, o.ViewObject.Visibility) for o in md.Objects if hasattr(o, "Shape")]
    for obj, _an in sichtbar:
        obj.ViewObject.hide()
    for _aufnahme, _knoten, _lage, wahl, _werkzeuge in bild._plaetze:
        wahl.whichChild = -1
    view.viewIsometric()
    view.fitAll()
    view.setCameraOrientation((lage.Rotation * view.getCameraOrientation()).Q)
    bild.zeige_stelle(lage.multVec(doc.Job.Stock.Shape.BoundBox.Center))
    view.getCameraNode().height.setValue(75)
    Gui.updateGui()
    yield 600
    ausgabe = Path(os.environ["CAMADDON_AUSGABE"])
    view.saveImage(str(ausgabe / "materialvergleich.png"), 1000, 750, "Current")
    panel.abspieler.haken_teil.setChecked(False)
    Gui.updateGui()
    view.saveImage(str(ausgabe / "materialvergleich_deckend.png"), 1000, 750, "Current")
    panel.abspieler.haken_teil.setChecked(True)
    h.bild("1_fertigteil_materialfarben", panel.form)
    for obj, an in sichtbar:
        obj.ViewObject.Visibility = an
    for _aufnahme, _knoten, _lage, wahl, _werkzeuge in bild._plaetze:
        wahl.whichChild = 0
    screens = QtGui.QApplication.screens()
    if len(screens) > 1:
        secondary = next(
            (s for s in screens if s.name() == os.environ.get("CAMADDON_GROB_BILDSCHIRM")),
            next(s for s in screens if s is not QtGui.QApplication.primaryScreen()),
        )
        h.pruefe(
            secondary.geometry().contains(fenster.frameGeometry().center()), "Falscher Bildschirm"
        )
    (ausgabe / "bildschirm.json").write_text(
        json.dumps({"bildschirm": fenster.windowHandle().screen().name()}), encoding="utf-8"
    )
    panel.abspieler.springe_zu_station(0)
    h.pruefe(not bild._am_ende, "Zurückspulen lässt Endvergleich stehen")
    panel.abspieler.haken_bahn.setChecked(False)
    h.pruefe(bild.bahn_schalter.whichChild.getValue() == -1, "Bahn bleibt sichtbar")
    panel.abspieler.haken_bahn.setChecked(True)
    h.pruefe(bild.bahn_schalter.whichChild.getValue() == 0, "Bahn fehlt am Anfang")
    panel.abspieler.springe_zu_station(len(panel.abfahrt.stationen) - 1)
    yield 300
    panel.reject()
