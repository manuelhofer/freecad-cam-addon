# „Maschine verfahren“ (W-001 Stufe 3) an der fertig beschriebenen
# Beispiel-Drehmaschine: je Achse ein Regler (C4, Z1, X1, T), X1 bleibt an
# seiner Grenze 200 mm stehen, C4 dreht das Futter; Abbrechen fährt alles
# zurück, OK behält die Stellung als einen Schritt Rückgängig.
import os
import sys

import FreeCAD
import FreeCADGui as Gui

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.accept()
    yield 500

    import beispielmaschinen

    from camaddon import gui_verfahren
    from camaddon import verfahren as vf

    asm, _maschine = beispielmaschinen.drehmaschine_komplett()
    doc = asm.Document
    doc.UndoMode = 1
    Gui.activateWorkbench("AssemblyWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(asm)
    lagen = {o.Name: FreeCAD.Placement(o.Placement) for o in asm.Group if hasattr(o, "Placement")}
    yield 500

    Gui.runCommand("CamAddon_MaschineVerfahren")
    yield 1000
    panel = gui_verfahren.VerfahrPanel.offen
    h.pruefe(panel is not None, "Fenster öffnet sich nicht")
    if panel is None:
        return
    namen = sorted(vf.namen(panel.maschine, a) for a in panel.zeilen)
    h.pruefe(namen == ["C4", "T", "X1", "Z1"], f"Achsen: {namen}")

    x = panel.achse("X1")
    regler_x, feld_x = panel.zeilen[x]
    feld_x.setValue(500)  # das Feld lässt nur bis zur Grenze zu
    yield 200
    h.pruefe(feld_x.value() == 200 and regler_x.value() == 2000, f"X1: {feld_x.value()}")
    h.pruefe(abs(vf.gelenkstellung(x.gelenk, x.art) - 200) < 1e-6, "X1 steht nicht auf 200")
    c = panel.achse("C4")
    regler_c, feld_c = panel.zeilen[c]
    regler_c.setValue(900)  # 90°
    yield 200
    h.pruefe(abs(feld_c.value() - 90) < 1e-9, f"C4 im Feld: {feld_c.value()}")
    h.pruefe(abs(vf.gelenkstellung(c.gelenk, c.art) - 90) < 1e-6, "C4 steht nicht auf 90°")
    Gui.SendMsgToActiveView("ViewFit")
    h.bild("1_verfahren")

    # Abbrechen: alles wie vorher.
    panel.reject()
    yield 500
    anders = [n for n, lage in lagen.items() if not doc.getObject(n).Placement.isSame(lage, 1e-7)]
    h.pruefe(not anders, f"nach Abbrechen verschoben: {anders}")

    # OK: die Stellung bleibt – ein Strg+Z nimmt sie zurück.
    Gui.Selection.addSelection(asm)
    Gui.runCommand("CamAddon_MaschineVerfahren")
    yield 1000
    panel = gui_verfahren.VerfahrPanel.offen
    h.pruefe(panel is not None, "Fenster öffnet sich kein zweites Mal")
    if panel is None:
        return
    x = panel.achse("X1")
    panel.zeilen[x][1].setValue(100)
    yield 200
    panel.knopf_grundstellung.click()
    yield 200
    h.pruefe(panel.zeilen[x][1].value() == 0, "Grundstellung: X1 nicht auf 0")
    panel.zeilen[x][1].setValue(100)
    yield 200
    panel.accept()
    yield 500
    h.pruefe(abs(vf.gelenkstellung(x.gelenk, x.art) - 100) < 1e-6, "OK behält X1 = 100 nicht")
    doc.undo()
    yield 300
    h.pruefe(abs(vf.gelenkstellung(x.gelenk, x.art)) < 1e-6, "Strg+Z fährt X1 nicht zurück")
