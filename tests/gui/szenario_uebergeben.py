# „An CAM übergeben“: Die fertig beschriebene Drehmaschine wird aus dem
# Dialog übergeben; das Berichtsfenster nennt, was angekommen ist und was nur
# in der Maschine bleibt, und CAM listet die Maschine.
import os
import sys
import tempfile

import FreeCADGui as Gui

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.accept()
    yield 300

    from Machine.models.machine import MachineFactory

    import beispielmaschinen
    from camaddon import gui_maschine

    MachineFactory.set_config_directory(tempfile.mkdtemp())
    asm, _ma = beispielmaschinen.drehmaschine_komplett()
    Gui.activateWorkbench("AssemblyWorkbench")
    Gui.Selection.addSelection(asm)
    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield 1500
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(panel.knopf_uebergeben.isEnabled(), "„An CAM übergeben“ nicht bedienbar")

    bericht = panel._uebergeben(nachfragen=False)
    yield 500
    h.pruefe(bericht is not None, "Übergabe fehlgeschlagen")
    fenster = getattr(panel, "bericht_fenster", None)
    h.pruefe(fenster is not None and fenster.isVisible(), "Berichtsfenster erscheint nicht")
    if fenster:
        text = fenster.text.toPlainText()
        h.pruefe("„Testdrehmaschine“ steht jetzt in CAM zur Auswahl" in text, f"Bericht: {text[:120]!r}")
        h.pruefe("Linearachse X1" in text and "Spindel S4" in text, "Bericht nennt X1/S4 nicht")
        h.pruefe("Revolver „T“ mit 12 Plätzen" in text, "Bericht nennt den Revolver nicht")
        h.bild("1_bericht", fenster)
    h.pruefe("Testdrehmaschine" in MachineFactory.list_configurations(), "CAM listet die Maschine nicht")
    panel.accept()
