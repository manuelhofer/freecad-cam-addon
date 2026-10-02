# Die Kontur auf dem Materialstand (W-012 M4; Manuel, 2026-10-02: „Ist überhaupt noch viel
# Material vorhanden, was ich wegmachen muss“) an Manuels Klotz ohne Nut: 100 × 100, oben bei z 0
# ein Zapfen Ø 30 bei x25 y25, rundum der Boden bei −10. Zuerst den Boden: „Bearbeitung“,
# „Anlegen“ – das Räumen nimmt rundum alles bis aufs Aufmaß an der Wand. Dann die Wand des Zapfens
# am Teil im Job: Die Kontur sagt „→ 1 Lage, 1 Bahn“ – sie schlichtet nur noch – und grau
# „noch … – … hat „Räumen T1“ schon weggenommen“; „Anlegen“: ein Job mit beiden, die Kontur merkt
# sich, woraus sie gerechnet hat.
import FreeCAD
import FreeCADGui as Gui
import Part

V = FreeCAD.Vector


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import gui_bearbeitung
    from camaddon import kontur as ko
    from camaddon import materialstand as mst
    from camaddon import raeumen as ra
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()

    doc = FreeCAD.newDocument("Klotz")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Klotz")
    klotz = Part.makeBox(100, 100, 20, V(-50, -50, -30))
    teil.Shape = klotz.fuse(Part.makeCylinder(15, 10, V(25, 25, -10))).removeSplitter()
    doc.recompute()
    boden = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if abs(f.BoundBox.ZMin + 10.0) < 1e-6 and abs(f.BoundBox.ZMax + 10.0) < 1e-6
    )
    wand = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 15.0) < 1e-6
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    gui_bearbeitung.nullpunkt_vorgeben(None)  # die Koordinaten wie im Modell

    def oeffnen(objekt, name):
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, objekt.Name, name)
        yield 500
        Gui.runCommand("CamAddon_Bearbeitung")
        yield 2000

    # --- Zuerst der Boden: das Räumen ----------------------------------------------------------
    yield from oeffnen(teil, boden)
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    panel.knopf_weiter.click()
    yield from h.warte_auf(lambda: panel.raeumen.vorschau is not None, 180000)
    yield 1500
    h.pruefe(panel.raeumen.aktiv(), "das Räumen nicht angehakt")
    h.pruefe(panel.accept() is True, "Räumen: „Anlegen“ ging nicht")
    yield 3000
    raeumen = [o for o in job.Operations.Group if ra.ist_raeumen(o)]
    h.pruefe(len(raeumen) == 1, f"nach dem Räumen: {[o.Label for o in job.Operations.Group]}")
    if not raeumen:
        return

    # --- Dann die Wand des Zapfens: die Kontur weiß vom Räumen ---------------------------------
    yield from oeffnen(vr.modell(job), wand)
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is job, "Wand: nicht im Job des Räumens")
    if panel is None or panel.job is not job:
        return
    panel.knopf_weiter.click()
    yield from h.warte_auf(lambda: panel.kontur.vorschau is not None, 180000)
    yield 1500
    ergebnis, material = panel.kontur.ergebnis.text(), panel.kontur.material.text()
    print(ascii(f"Kontur: {ergebnis} / {material}"))
    h.pruefe(panel.kontur.aktiv(), "die Kontur nicht angehakt")
    h.pruefe("1 Lage, 1 Bahn" in ergebnis, f"Kontur schruppt noch: {ergebnis!r}")
    h.pruefe(
        material.startswith("noch ")
        and material.endswith(f"hat „{raeumen[0].Label}“ schon weggenommen"),
        f"Materialzeile: {material!r}",
    )
    h.bild("1_kontur_kennt_das_raeumen", panel.form)
    h.pruefe(panel.accept() is True, "Kontur: „Anlegen“ ging nicht")
    yield 3000
    ops = list(job.Operations.Group)
    konturen = [o for o in ops if ko.ist_kontur(o)]
    h.pruefe(len(konturen) == 1 and len(ops) == 2, f"im Job: {[o.Label for o in ops]}")
    if konturen:
        h.pruefe(
            konturen[0].Materialstand == mst.kennung_vor(job, konturen[0]),
            "Kontur: woraus gerechnet nicht gemerkt",
        )
        h.pruefe(konturen[0].Bahnen == 1, f"Kontur im Job: {konturen[0].Bahnen} Bahnen")
    Gui.Selection.clearSelection()
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_raeumen_und_kontur")
    FreeCAD.closeDocument(doc.Name)
    yield 300
