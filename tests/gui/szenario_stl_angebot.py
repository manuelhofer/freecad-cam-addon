# STL ohne Auswahl und ein verwaister Beobachter (P-2026-10-12-139; Manuel, 2026-10-12: „den Geist
# geöffnet … auf 4-Achs gedrückt … jetzt kann ich nix anklicken, weil ich erst den Geist anklicken
# muss … frag ich mal, ob er das will“; dazu „Cannot access attribute ‚Name‘ of deleted object“).
# Ein Netz (ein Würfel als STL) im Dokument, nichts gewählt: „4-Achs-Bearbeitung“ fragt, ob es das
# sein soll – „Ja“, „STL als Teil“, der Assistent mit dem Körper. Dann das Dokument zu, ohne den
# Assistenten zu schließen: Im nächsten Dokument lässt sich eine Kante anklicken (keine Sperre
# mehr), und der alte Beobachter ruft nicht ins Leere.
import FreeCAD
import FreeCADGui as Gui
import Mesh
import Part
from PySide import QtCore, QtGui


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import gui_stl, gui_vierachs, stl_teil

    doc = FreeCAD.newDocument("Netz")
    netz = doc.addObject("Mesh::Feature", "Wuerfel")
    netz.Mesh = Mesh.createBox(20, 20, 40)
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.clearSelection()
    yield 300

    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_Vierachs"))
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 5000)
    frage = h.modal()
    h.pruefe(isinstance(frage, QtGui.QMessageBox), "keine Frage nach dem STL")
    if not isinstance(frage, QtGui.QMessageBox):
        return
    h.pruefe("„Wuerfel“" in frage.text(), f"Frage: {frage.text()!r}")
    h.bild("1_frage", frage)
    frage.button(QtGui.QMessageBox.Yes).click()
    yield from h.warte_auf(lambda: gui_stl.StlDialog.offen is not None, 5000)
    dialog = gui_stl.StlDialog.offen
    h.pruefe(dialog is not None, "„STL als Teil“ öffnet nicht")
    if dialog is None:
        return
    dialog.accept()
    yield from h.warte_auf(lambda: gui_vierachs.VierachsPanel.offen is not None, 30000)
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None, "Assistent nicht offen")
    h.pruefe(any(stl_teil.aus_stl(o) for o in doc.Objects), "kein Körper aus dem Netz")
    yield 500

    # Das Dokument zu, der Assistent bleibt stehen (wie nach dem Schließen eines Dokuments).
    FreeCAD.closeDocument(doc.Name)
    yield 800
    if Gui.Control.activeDialog():
        Gui.Control.closeDialog()
        yield 500
    neu = FreeCAD.newDocument("Danach")
    kasten = neu.addObject("Part::Feature", "Kasten")
    kasten.Shape = Part.makeBox(10, 10, 10)
    neu.recompute()
    yield 300
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(neu.Name, kasten.Name, "Edge1")
    yield 500
    h.pruefe(
        any(
            "Edge1" in s for a in Gui.Selection.getSelectionEx(neu.Name) for s in a.SubElementNames
        ),
        "Kante lässt sich nicht wählen – die Sperre des alten Assistenten hängt noch",
    )
    Gui.Selection.addSelection(neu.Name, kasten.Name, "Face1")
    yield 500
