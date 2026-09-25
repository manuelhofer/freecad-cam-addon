# „An CAM übergeben“: Die fertig beschriebene Drehmaschine wird aus dem
# Dialog übergeben; das Berichtsfenster nennt, was angekommen ist und was nur
# in der Maschine bleibt, und CAM listet die Maschine. Hat die FreeCAD-Version
# keine Maschinendefinition (1.1.x), muss stattdessen eine Erklärung kommen.
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

    import beispielmaschinen
    from camaddon import export, gui_maschine

    if export.verfuegbar():
        from Machine.models.machine import MachineFactory

        MachineFactory.set_config_directory(tempfile.mkdtemp())
    asm, _ma = beispielmaschinen.drehmaschine_komplett()
    Gui.activateWorkbench("AssemblyWorkbench")
    Gui.Selection.addSelection(asm)
    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield 1500
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(panel.knopf_uebergeben.isEnabled(), "„An CAM übergeben“ nicht bedienbar")

    if not export.verfuegbar():
        # FreeCAD 1.1.x: statt eines Fehlers ein Satz, was fehlt und wo es das gibt.
        h.pruefe(panel._uebergeben(nachfragen=False) is None, "Übergabe ohne Maschinendefinition")
        yield 500
        hinweis = h.modal()
        text = hinweis.text() if hinweis is not None else ""
        h.pruefe("kennt noch keine Maschinendefinition" in text and "Wochen-Build" in text,
                 f"Erklärung fehlt oder falsch: {text!r}")
        if hinweis is not None:
            h.bild("1_nicht_verfuegbar", hinweis)
            hinweis.done(0)
        panel.accept()
        return

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
