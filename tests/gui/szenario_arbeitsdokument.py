# Das Dokument der Auswahl (P-2026-10-12-137; Manuel, 2026-10-12: nach „Auf der Maschine prüfen“
# war die CLX550 aktiv, der Geist in „Unbenannt“ gewählt – „4-Achs-Bearbeitung“ legte den
# Werkzeug-Controller in der Maschine an und scheiterte mit „PropertyLink does not support
# external object“): Ein Block in „Teil“, die Beispiel-Drehmaschine in einem eigenen Dokument und
# aktiv, der Block gewählt. „4-Achs-Bearbeitung“ öffnet sich mit dem Dokument „Teil“ und macht es
# aktiv; „Bearbeitung“ ebenso. Ohne Auswahl, die Maschine aktiv: auch „Teil“ (das einzige andere).
import FreeCAD
import FreeCADGui as Gui
import Part


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine as bm
    from camaddon import gui_bearbeitung, gui_vierachs
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    doc = FreeCAD.newDocument("Teil")
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeCylinder(15, 60)
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    asm, _maschine = bm.lade(bm.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document, 10000)
    h.pruefe(FreeCAD.ActiveDocument is asm.Document, "die Maschine ist nicht aktiv")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name)
    yield 300

    Gui.runCommand("CamAddon_Vierachs")
    yield from h.warte_auf(lambda: gui_vierachs.VierachsPanel.offen is not None, 10000)
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None, "„4-Achs-Bearbeitung“ öffnet nicht")
    if panel is not None:
        h.pruefe(panel.doc is doc, f"4 Achsen im Dokument {panel.doc.Name}")
        h.pruefe(FreeCAD.ActiveDocument is doc, f"aktiv: {FreeCAD.ActiveDocument.Name}")
        h.bild("1_vierachs_im_teil")
        panel.reject()
        yield 800

    # Ohne Auswahl, die Maschine wieder aktiv: das einzige andere Dokument.
    FreeCAD.setActiveDocument(asm.Document.Name)
    Gui.Selection.clearSelection()
    yield 300
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(
        lambda: gui_bearbeitung.BearbeitungPanel.offen is not None or h.modal() is not None, 10000
    )
    dialog = h.modal()
    if dialog is not None:  # „kein Teil gewählt“ – dann wenigstens im richtigen Dokument
        dialog.reject()
        yield 300
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(FreeCAD.ActiveDocument is doc, f"ohne Auswahl aktiv: {FreeCAD.ActiveDocument.Name}")
    if panel is not None:
        h.pruefe(panel.doc is doc, f"Bearbeitung im Dokument {panel.doc.Name}")
        panel.reject()
        yield 500
