# G550 wählen, bauen und die getrennten Bewegungen der horizontalen Spindel und
# des Hubtisches zeigen. A=−90 (an der Steuerung) stellt die Spannfläche zur Spindel.
import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500
    from camaddon import beispielmaschine as bm
    from camaddon import gui_maschine, gui_neue_maschine, gui_verfahren, maschine

    Gui.activateWorkbench("AssemblyWorkbench")
    yield 300
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_NeueMaschine"))
    yield from h.warte_auf(lambda: gui_neue_maschine.NeueMaschineDialog.offen is not None)
    d = gui_neue_maschine.NeueMaschineDialog.offen
    h.pruefe(d is not None, "Auswahl öffnet nicht")
    if d is None:
        return
    d.liste.setCurrentRow(bm.ARTEN.index(bm.GROB_G550))
    yield 200
    h.pruefe(d.masse() == bm.FuenfachsMasse.vorgabe(bm.GROB_G550), "G550: falsche Vorbelegung")
    h.pruefe("Y hebt und senkt" in d.beschreibung.text(), "G550: Hubtisch nicht erklärt")
    h.pruefe(not d.feld_bett.isVisible(), "G550: Drehmaschinenfelder sichtbar")
    h.pruefe(
        d._schwenk_zeilen[0].isVisible() and not d._schwenk_zeilen[1].isVisible(),
        "G550: A-Bereich fehlt oder B begrenzt",
    )
    h.bild("1_auswahl", d)
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield from h.warte_auf(lambda: gui_maschine.MaschinenPanel.offen is not None)
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(panel is not None, "G550: Maschine bearbeiten öffnet nicht")
    if panel is None:
        return
    asm = maschine.assembly_von(panel.maschine)
    doc = asm.Document
    h.pruefe(doc.Label == "Beispiel GROB G550", f"G550: Dokument {doc.Label}")
    panel.accept()
    yield 300
    Gui.activeDocument().activeView().viewIsometric()
    Gui.activeDocument().activeView().fitAll()
    h.bild("2_grundstellung")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(panel.maschine)
    Gui.runCommand("CamAddon_MaschineVerfahren")
    yield from h.warte_auf(lambda: gui_verfahren.VerfahrPanel.offen is not None)
    fahren = gui_verfahren.VerfahrPanel.offen
    h.pruefe(fahren is not None, "G550: Maschine verfahren öffnet nicht")
    if fahren is None:
        return
    vorher = {n: App.Placement(doc.getObject(n).Placement) for n in ("Spindel", "Rundtisch")}
    for name, wert in (("X1", 200), ("Z1", 200), ("Y1", -200)):
        fahren.zeilen[fahren.achse(name)][1].setValue(wert)
    h.pruefe(
        (doc.getObject("Spindel").Placement.Base - vorher["Spindel"].Base).isEqual(
            App.Vector(200, -200, 0), 1e-6
        ),
        "G550: Spindel bewegt sich falsch",
    )
    h.pruefe(
        (doc.getObject("Rundtisch").Placement.Base - vorher["Rundtisch"].Base).isEqual(
            App.Vector(0, 0, 200), 1e-6
        ),
        "G550: Y hebt den Tisch nicht",
    )
    yield 300
    h.bild("3_tisch_angehoben_spindel_zurueck")
    fahren.grundstellung()
    for name, wert in (("A1", -90), ("B1", -45)):
        fahren.zeilen[fahren.achse(name)][1].setValue(wert)
    spann = next(
        a for a in maschine.aufnahmen(panel.maschine) if a.Art == maschine.AUFNAHME_WERKSTUECK
    )
    normal = maschine.globale_platzierung(spann.Lcs).Rotation.multVec(App.Vector(0, 0, 1))
    h.pruefe(normal.isEqual(App.Vector(0, -1, 0), 1e-6), "G550: Spannfläche nicht zur Spindel")
    yield 300
    h.bild("4_a_minus90_b_minus45")
    fahren.reject()
    yield 300
    # Die gleiche Baugruppe als direkt öffnbares Beispiel, mit den Farben der Oberfläche.
    Gui.activateWorkbench("PartWorkbench")
    Gui.Selection.clearSelection()
    Gui.activeDocument().activeView().fitAll()
    doc.saveAs(os.path.join(os.environ["CAMADDON_AUSGABE"], "grob_g550.FCStd"))
    yield 300
    h.bild("5_beispielmaschine")
    for name in list(App.listDocuments()):
        App.closeDocument(name)
    yield 300
