# Der Materialstand (W-012 M1; Manuel, 2026-10-02: „Ist überhaupt noch viel Material vorhanden,
# was ich wegmachen muss“) an Manuels Klotz: 100 × 100, oben bei z 0 ein Zapfen Ø 30 bei x25 y25,
# rundum der Boden bei −10, darin eine Nut 20 × 60 längs X um x −10 y 0, 15 tief (Grund −15);
# das Rohteil 1 mm größer, oben bei 1. Mit dem Standardfräser. Zapfen zuerst: den Boden anklicken,
# „Bearbeitung“, „Anlegen“ – eine Operation räumt rundum bis −10. Dann die Nut in denselben Job
# und zum Ändern geöffnet: Sie beginnt bei −10, nicht oben am Rohteil; unter ihrem Ergebnis grau
# „noch 5,6 cm³ – … hat „…“ schon weggenommen“. Die Operation davor gelöscht: Die Nut rechnet von
# selbst neu und beginnt oben am Rohteil.
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
    from camaddon import nut as nu
    from camaddon import planfraesen as pf
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
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, boden)
    yield 500

    # --- Zapfen zuerst: der Boden rundum bis −10 ------------------------------------------------
    gui_bearbeitung.nullpunkt_vorgeben(None)  # die Koordinaten wie im Modell
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    panel.knopf_weiter.click()
    yield from h.warte_auf(
        lambda: any(b.vorschau is not None for b in panel.aktive_bloecke()), 180000
    )
    yield 1500
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = list(job.Operations.Group)
    h.pruefe(len(ops) >= 1, f"Operationen: {[o.Label for o in ops]}")
    if not ops:
        return
    davor = ops[0]

    # --- Die Nut dahinter: sie beginnt bei −10 ---------------------------------------------------
    tc = job.Tools.Group[0]
    nut_op = nu.lege_an(job, tc, 25.0, 1.5, flaechen=[grund])
    doc.recompute()
    yield 1500

    def erster_vorschub():
        return next(float(c.Parameters["Z"]) for c in nut_op.Path.Commands
                    if c.Name in ("G1", "G01") and "Z" in c.Parameters)  # fmt: skip

    h.pruefe(abs(erster_vorschub() + 10.0) < 0.01, f"Nut beginnt bei {erster_vorschub()}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("1_nut_ab_minus_10")

    # Zum Ändern geöffnet: grau, was noch zu tun ist und wer schon weggenommen hat.
    gui_bearbeitung.bearbeiten(nut_op)
    yield 1500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None, "Nut nicht zum Ändern offen")
    if panel is None:
        return
    yield from h.warte_auf(lambda: panel.nut.vorschau is not None, 120000)
    yield 1500
    material = panel.nut.material.text()
    print(ascii(f"Nut: {panel.nut.ergebnis.text()} / {material}"))
    h.pruefe(
        material.startswith("noch 5,") and f"„{davor.Label}“ schon weggenommen" in material,
        f"Materialzeile: {material!r}",
    )
    h.bild("2_nut_aendern", panel.form)
    panel.reject()
    yield 1000

    # --- Die Operation davor gelöscht: die Nut rechnet neu, oben am Rohteil ---------------------
    oben = pf.rohteil_von_oben(job)[4]
    doc.removeObject(davor.Name)
    doc.recompute()
    yield from h.warte_auf(lambda: abs(erster_vorschub() - oben) < 0.01, 60000)
    yield 500
    h.pruefe(abs(erster_vorschub() - oben) < 0.01, f"nach dem Löschen ab {erster_vorschub()}")
    FreeCAD.closeDocument(doc.Name)
    yield 300
