# Hilfe im Dialog: Der Knopf (?) bei „Achsen“ öffnet die ausführliche Hilfe,
# der Verweis darin führt zu „Beschleunigung ermitteln“, und bei einer
# linearen Betriebsart steht der Verweis direkt unter den Feldern.
import os
import sys

import FreeCADGui as Gui
from PySide import QtCore, QtGui

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300

    import beispielmaschinen

    from camaddon import gui_hilfe, gui_maschine
    from camaddon import maschine as m

    asm = beispielmaschinen.drehmaschine()
    doc = asm.Document
    Gui.activateWorkbench("AssemblyWorkbench")
    Gui.Selection.addSelection(asm)
    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield 1500
    panel = gui_maschine.MaschinenPanel.offen

    knopf = panel.form.findChild(QtGui.QToolButton, "hilfe_achsen")
    h.pruefe(knopf is not None, "Hilfe-Knopf bei „Achsen“ fehlt")
    for thema in ("aufnahmen", "glieder"):
        h.pruefe(
            panel.form.findChild(QtGui.QToolButton, "hilfe_" + thema) is not None,
            f"Hilfe-Knopf bei „{thema}“ fehlt",
        )
    knopf.click()
    yield 500
    fenster = gui_hilfe.HilfeFenster.offen
    h.pruefe(fenster is not None and fenster.isVisible(), "Hilfefenster öffnet sich nicht")
    text = fenster.browser.toPlainText()
    h.pruefe(
        "Achsen und Betriebsarten" in text and "S4" in text, f"falsche Hilfeseite: {text[:80]!r}"
    )
    h.bild("1_hilfe_achsen", fenster)

    fenster.browser.setSource(QtCore.QUrl("beschleunigung.html"))
    yield 300
    text = fenster.browser.toPlainText()
    h.pruefe("4 · s ÷ t²" in text, "Verweis auf „Beschleunigung ermitteln“ führt nicht zur Seite")
    h.bild("2_hilfe_beschleunigung", fenster)
    fenster.close()

    # Verweis direkt bei den Feldern einer linearen Betriebsart.
    ba = m.neue_betriebsart(panel.maschine, doc.getObject("X"), m.ART_LINEAR, "X1")
    panel.neu_aufbauen(auswahl=ba)
    yield 300
    verweise = [w for w in panel.details.findChildren(QtGui.QLabel) if "beschleunigung" in w.text()]
    h.pruefe(
        len(verweise) == 1, f"{len(verweise)} Verweise auf die Beschleunigung im Detail statt 1"
    )
    if verweise:
        verweise[0].linkActivated.emit("beschleunigung")
        yield 500
        text = gui_hilfe.HilfeFenster.offen.browser.toPlainText()
        h.pruefe("Beschleunigung ermitteln" in text, "Verweis im Detail öffnet die falsche Seite")
        gui_hilfe.HilfeFenster.offen.close()
    panel.reject()
