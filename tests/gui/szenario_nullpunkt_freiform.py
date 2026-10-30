# Nullpunkt „Mitte oben“ an einem Teil mit Freiformflächen (P-2026-10-30-04; Manuels tiefe Tasche,
# 2026-10-30: „Entgraten 3D T1: Final depth is above start depth“). Ein Block 80 × 80 × 40 mit einer
# gelofteten Tasche aus drei Rechtecken; das oberste liegt über dem Block – die B-Spline-Flächen
# der Wände sind oben abgeschnitten, ihr grober Hüllquader (BoundBox ohne Netz) reicht aber bis
# z 45. Der Nullpunkt kam daraus: Z0 lag 5 mm über dem Rohteil. Jetzt: das Rohteil oben in Z0, das
# Teil 1 mm darunter (Aufmaß oben 1). Dazu „Entgraten 3D“ im Job – FreeCADs Endtiefe ohne Base kam
# aus demselben groben Quader und lag über der Starttiefe; jetzt rechnet es ohne Fehler.
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part


def _teil():
    v = FreeCAD.Vector

    def rechteck(b, h, z):
        ecken = [v(-b / 2, -h / 2, z), v(b / 2, -h / 2, z), v(b / 2, h / 2, z), v(-b / 2, h / 2, z)]
        return Part.Wire(Part.makePolygon([*ecken, ecken[0]]))

    tasche = Part.makeLoft([rechteck(30, 20, 5), rechteck(44, 34, 30), rechteck(40, 30, 45)], True)
    return Part.makeBox(80, 80, 40, v(-40, -40, 0)).cut(tasche).removeSplitter()


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_bearbeitung
    from camaddon import entgraten3d as e3op
    from camaddon import maschinenspeicher as ms
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    asm.Document.saveAs(os.path.join(ordner, "Fraese.FCStd"))
    yield 300
    doc = FreeCAD.newDocument("Freiform")
    teil = doc.addObject("Part::Feature", "Teil")
    teil.Shape = _teil()
    doc.recompute()
    doc.saveAs(os.path.join(ordner, "freiform.FCStd"))
    grob = teil.Shape.copy(False, False).BoundBox.ZMax
    h.pruefe(grob > 44.0, f"der grobe Hüllquader reicht nicht über das Teil: {grob}")
    oben = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if f.Surface.__class__.__name__ == "Plane" and abs(f.BoundBox.ZMin - 40.0) < 1e-6
    )
    yield 500
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, oben)
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben((0, 0, 1))
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None)
    yield 1500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    h.pruefe(panel.nullpunkt() == (0, 0, 1), f"Nullpunkt: {panel.nullpunkt()}")
    job = panel.job
    doc.recompute()
    yield 500
    roh = job.Stock.Shape.BoundBox
    genau = job.Model.Group[0].Shape.optimalBoundingBox(False, False)
    h.pruefe(abs(roh.ZMax) < 0.05, f"Rohteil oben bei {roh.ZMax:.3f} statt 0")
    h.pruefe(abs(genau.ZMax + 1.0) < 0.05, f"Teil oben bei {genau.ZMax:.3f} statt −1")
    h.pruefe(abs(roh.XMin + roh.XMax) < 0.05 and abs(roh.YMin + roh.YMax) < 0.05, f"{roh}")

    # Entgraten 3D ohne Flächen: die Endtiefe unter der Starttiefe, kein Fehler beim Rechnen.
    tc = job.Tools.Group[0]
    op = e3op.lege_an(job, tc, flaechen=[])
    doc.recompute()
    yield 300
    h.pruefe(
        float(op.FinalDepth) < float(op.StartDepth),
        f"Entgraten 3D: Ende {op.FinalDepth} über Start {op.StartDepth}",
    )
    h.bild("1_einstellungen", panel.form)
