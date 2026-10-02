# Das Räumen auf dem Materialstand (W-012 M3; Manuel, 2026-10-02: „wenn ich erst die Nut anklicke
# … und wenn ich dann den Zapfen will, denke ich, dass er die Nut ebenfalls mit bearbeiten würde“)
# an Manuels Klotz: 100 × 100, oben bei z 0 ein Zapfen Ø 30 bei x25 y25, rundum der Boden bei −10,
# darin eine Nut 20 × 60 um x −10 y 0, Grund −15. Nut zuerst: den Grund der Nut anklicken,
# „Bearbeitung“, „Anlegen“ – die Nut von oben bis −15. Dann den Boden um den Zapfen am Teil im Job:
# Das Räumen sagt grau „noch … – … hat „Nut T1“ schon weggenommen“, und „Weg müssen …“ darüber ist
# um die Nut kleiner als beim ersten Mal (W-012 M4a); „Anlegen“: ein Job mit beiden, das Räumen
# merkt sich, woraus es gerechnet hat.
import re

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
    from camaddon import materialstand as mst
    from camaddon import nut as nu
    from camaddon import raeumen as ra
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()

    doc = FreeCAD.newDocument("Klotz")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Klotz")
    klotz = Part.makeBox(100, 100, 20, V(-50, -50, -30))
    klotz = klotz.fuse(Part.makeCylinder(15, 10, V(25, 25, -10)))
    nut = Part.makeBox(40, 20, 6, V(-30, -10, -15))
    nut = nut.fuse(Part.makeCylinder(10, 6, V(-30, 0, -15)))
    nut = nut.fuse(Part.makeCylinder(10, 6, V(10, 0, -15)))
    teil.Shape = klotz.cut(nut).removeSplitter()
    doc.recompute()

    def flaeche(z):
        return next(
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if abs(f.BoundBox.ZMin - z) < 1e-6 and abs(f.BoundBox.ZMax - z) < 1e-6
        )

    boden, grund = flaeche(-10.0), flaeche(-15.0)
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    gui_bearbeitung.nullpunkt_vorgeben(None)  # die Koordinaten wie im Modell

    def weg_muessen(panel):  # „Weg müssen 120,9 cm³. …“ → 120.9
        treffer = re.search(r"Weg müssen ([0-9.,]+) cm³", panel.ziel_text.text())
        return float(treffer.group(1).replace(",", ".")) if treffer else None

    def oeffnen(objekt, name):
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, objekt.Name, name)
        yield 500
        Gui.runCommand("CamAddon_Bearbeitung")
        yield 2000

    # --- Nut zuerst: der Grund der Nut ---------------------------------------------------------
    yield from oeffnen(teil, grund)
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    panel.knopf_weiter.click()
    yield from h.warte_auf(lambda: panel.nut.vorschau is not None, 180000)
    yield 1500
    h.pruefe(panel.nut.aktiv(), "die Nut nicht angehakt")
    vorher = weg_muessen(panel)
    h.pruefe(panel.accept() is True, "Nut: „Anlegen“ ging nicht")
    yield 3000
    nuten = [o for o in job.Operations.Group if nu.ist_nut(o)]
    h.pruefe(len(nuten) == 1, f"nach der Nut: {[o.Label for o in job.Operations.Group]}")
    if not nuten:
        return
    nut_op = nuten[0]

    # --- Dann der Boden um den Zapfen: das Räumen weiß von der Nut ------------------------------
    yield from oeffnen(vr.modell(job), boden)
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is job, "Boden: nicht im Job der Nut")
    if panel is None or panel.job is not job:
        return
    panel.knopf_weiter.click()
    yield from h.warte_auf(lambda: panel.raeumen.vorschau is not None, 180000)
    yield 1500
    material = panel.raeumen.material.text()
    print(ascii(f"Räumen: {panel.raeumen.ergebnis.text()} / {material}"))
    h.pruefe(panel.raeumen.aktiv(), "das Räumen nicht angehakt")
    # Die Nut ist weg: 40 × 20 + π · 10², von oben (+1) bis −15 – rund 17,8 cm³ weniger.
    nachher = weg_muessen(panel)
    print(ascii(f"Weg müssen: vorher {vorher}, nachher {nachher}"))
    h.pruefe(
        vorher is not None and nachher is not None and 15.0 < vorher - nachher < 21.0,
        f"Weg müssen: vorher {vorher}, nachher {nachher}",
    )
    h.pruefe(
        material.startswith("noch ")
        and material.endswith(f"hat „{nut_op.Label}“ schon weggenommen"),
        f"Materialzeile: {material!r}",
    )
    h.bild("1_raeumen_kennt_die_nut", panel.form)
    h.pruefe(panel.accept() is True, "Räumen: „Anlegen“ ging nicht")
    yield 3000
    ops = list(job.Operations.Group)
    raeumen = [o for o in ops if ra.ist_raeumen(o)]
    h.pruefe(len(raeumen) == 1, f"im Job: {[o.Label for o in ops]}")
    if raeumen:
        h.pruefe(
            raeumen[0].Materialstand == mst.kennung_vor(job, raeumen[0]),
            "Räumen: woraus gerechnet nicht gemerkt",
        )
    Gui.Selection.clearSelection()
    Gui.ActiveDocument.ActiveView.viewTop()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_nut_und_raeumen_von_oben")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("3_nut_und_raeumen")
    FreeCAD.closeDocument(doc.Name)
    yield 300
