# „Bearbeitung“ öffnet die Schritte (Manuel, 2026-11-07: „definitiv“ – die Schritte als Standard, das
# alte Fenster als Option in den Einstellungen). Ein Block, eine Fläche angeklickt, „Bearbeitung“:
# das Fenster in Schritten. Mit dem Haken „Altes Fenster“: das Fenster auf einer Seite. „Weiter
# bearbeiten“ und „Neue Aufspannung“ stehen in der gewohnten Leiste, die Leiste „Beta“ ist leer.
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part

NEUES_FENSTER = True  # der Läufer stellt sonst das alte Fenster ein


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_bearbeitung, gui_start
    from camaddon import gui_bearbeitung_beta as beta
    from camaddon import maschinenspeicher as ms

    h.pruefe(not beta.altes_fenster(), "Vorgabe: altes Fenster")
    h.pruefe("CamAddon_WeiterBearbeitenBeta" in gui_start.WERKZEUGLEISTE, "Weiter bearbeiten fehlt")
    h.pruefe("CamAddon_NeueAufspannungBeta" in gui_start.MENUE, "Neue Aufspannung fehlt im Menü")
    h.pruefe(not beta.WERKZEUGLEISTE, f"Beta-Leiste: {beta.WERKZEUGLEISTE}")
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    asm.Document.saveAs(os.path.join(ordner, "Fraese.FCStd"))
    yield 300

    doc = FreeCAD.newDocument("Standard")
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeBox(80, 60, 30)
    doc.recompute()
    doc.saveAs(os.path.join(ordner, "standard.FCStd"))
    oben = next(
        f"Face{i + 1}" for i, f in enumerate(teil.Shape.Faces) if abs(f.BoundBox.ZMin - 30) < 1e-6
    )
    yield 300

    def oeffnen():
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, teil.Name, oben)
        Gui.runCommand("CamAddon_Bearbeitung")

    for alt in (False, True):
        beta.altes_fenster_setzen(alt)
        FreeCAD.setActiveDocument(doc.Name)
        oeffnen()
        yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 60000)
        yield 1500
        panel = gui_bearbeitung.BearbeitungPanel.offen
        h.pruefe(panel is not None, f"kein Fenster (altes Fenster {alt})")
        if panel is None:
            return
        schritte_ = isinstance(panel, beta.BetaPanel)
        h.pruefe(schritte_ != alt, f"altes Fenster {alt}: {type(panel).__name__}")
        h.bild("2_alt" if alt else "1_schritte", panel.form)
        panel.reject()
        yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is None, 30000)
        yield 800
    beta.altes_fenster_setzen(False)
    FreeCAD.closeDocument(doc.Name)
    yield 300
