# Zeigen in der 3D-Ansicht: Überfahren einer Achse hebt alles hervor, was an
# ihr hängt, und bewegt es kurz hin und her – danach steht alles exakt wie
# vorher. Auch OK mitten in der Bewegung hinterlässt nichts Verschobenes.
import os
import sys

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def eintrag_daten(baum, text_anfang):
    it = QtGui.QTreeWidgetItemIterator(baum)
    while it.value():
        if it.value().text(0).lstrip("↔⟳ ").startswith(text_anfang):
            return it.value().data(0, 0x0100)
        it += 1
    return None


def lagen(doc, namen):
    return {n: App.Placement(doc.getObject(n).Placement) for n in namen}


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.accept()
    yield 300

    import beispielmaschinen
    from camaddon import gui_maschine

    asm = beispielmaschinen.drehmaschine()
    doc = asm.Document
    Gui.activateWorkbench("AssemblyWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(asm)
    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield 1500
    panel = gui_maschine.MaschinenPanel.offen

    beweglich = ["XSchlitten", "Revolver"]
    fest = ["Bett", "ZSchlitten", "Hauptspindel"]
    vorher = lagen(doc, beweglich + fest)

    panel._zeige(eintrag_daten(panel.achsen, "X"))
    yield 180
    h.bild("1_x_wackelt")
    mitten = lagen(doc, beweglich + fest)
    for name in beweglich:
        h.pruefe(not mitten[name].isSame(vorher[name], 1e-9), f"{name} bewegt sich beim Zeigen auf X nicht")
    for name in fest:
        h.pruefe(mitten[name].isSame(vorher[name], 1e-9), f"{name} bewegt sich, obwohl es nicht an X hängt")
    gewaehlt = sorted(o.Name for o in Gui.Selection.getSelection())
    h.pruefe(gewaehlt == sorted(beweglich), f"hervorgehoben: {gewaehlt}, erwartet {sorted(beweglich)}")

    yield 1200
    danach = lagen(doc, beweglich + fest)
    for name in beweglich + fest:
        h.pruefe(danach[name].isSame(vorher[name], 1e-12), f"{name} steht nach dem Zeigen nicht wie vorher")

    # Glied zeigen: nur hervorheben, nichts bewegt sich.
    glied_zeile = next(panel.glieder.item(i) for i in range(panel.glieder.count())
                       if "Hauptspindel" in panel.glieder.item(i).text())
    panel._zeige(glied_zeile.data(0x0100))
    yield 300
    gewaehlt = sorted(o.Name for o in Gui.Selection.getSelection())
    h.pruefe(gewaehlt == ["Futter", "Hauptspindel"], f"Glied hervorgehoben: {gewaehlt}")
    h.bild("2_glied_spindel")

    # Drehachse zeigen, dann mitten in der Bewegung OK.
    panel._zeige(eintrag_daten(panel.achsen, "Revolverachse"))
    yield 150
    h.pruefe(not doc.getObject("Revolver").Placement.isSame(vorher["Revolver"], 1e-9),
             "Revolver dreht sich beim Zeigen nicht")
    panel.accept()
    yield 500
    h.pruefe(doc.getObject("Revolver").Placement.isSame(vorher["Revolver"], 1e-12),
             "OK mitten in der Bewegung lässt den Revolver verdreht zurück")
