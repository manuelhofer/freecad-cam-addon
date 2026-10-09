# Rohteil aus einem konstruierten Teil (W-011 S4; Manuel, 2026-10-02: „Rohteil kann auch ein
# konstruiertes Teil sein“): Ein Block 100 × 60 × 20 und daneben im Dokument ein Körper
# „Rohteil“ 104 × 64 × 25 bei (−2, −2, 0) – rundum 2 mm, oben 5 mm mehr. Die Oberseite des
# Blocks angeklickt, „Bearbeitung“: In Schritt 1 „Teil aus dem Dokument“ – die Liste hat das
# Rohteil, nicht den Block. Gewählt: Das Rohteil des Jobs ist ein Klon des Körpers (−2 … 102,
# −2 … 62, oben 25), Schritt 2 sagt „Rohteil: Rohteil · …“. Zurück zum Quader: wieder der Quader
# mit Aufmaß; wieder der Körper. Nullpunkt „Mitte oben“: Teil und Rohteil wandern zusammen – die
# Mitte oben des Körpers liegt im Ursprung. „Anlegen“: Planfräsen oder Räumen (die Zeit
# entscheidet, 3 % auseinander), das Rohteil bleibt der Körper.
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
    from camaddon import hoehenfeld as hf
    from camaddon import planfraesen as pf
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()

    doc = FreeCAD.newDocument("Guss")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeBox(100, 60, 20)
    rohteil = doc.addObject("Part::Box", "Rohteil")
    rohteil.Length, rohteil.Width, rohteil.Height = 104, 64, 25
    rohteil.Placement = FreeCAD.Placement(V(-2, -2, 0), FreeCAD.Rotation())
    doc.recompute()
    rohteil.ViewObject.Transparency = 70
    oben = next(e.name for e in hf.ebenen_oben(teil.Shape) if abs(e.z - 20.0) < 1e-6)
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, oben)
    yield 500

    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job

    def kasten():
        return tuple(round(w, 6) for w in pf.rohteil_von_oben(job))

    def warten():
        yield from h.warte_auf(lambda: not panel._rohteil_uhr.isActive(), 5000)
        yield 500

    h.pruefe(hasattr(job.Stock, "ExtZpos"), "am Anfang kein Quader mit Aufmaß")

    # --- „Teil aus dem Dokument“: das Rohteil ist ein Klon des Körpers ------------------------
    panel.knopf_rohteil_teil.setChecked(True)
    yield from warten()
    liste = [panel.wahl_rohteil.itemText(i) for i in range(panel.wahl_rohteil.count())]
    h.pruefe(liste == ["Rohteil"], f"zur Wahl: {liste}")
    h.pruefe(
        rohteil in (getattr(job.Stock, "Objects", None) or []),
        f"Rohteil des Jobs: {job.Stock.Label}",
    )
    h.pruefe(kasten() == (-2.0, 102.0, -2.0, 62.0, 25.0), f"Kasten: {kasten()}")
    h.pruefe(not rohteil.ViewObject.Visibility, "das Original des Rohteils noch sichtbar")
    h.pruefe(
        panel.rohteil_koerper.isVisible() and not panel.rohteilfelder.isVisible(),
        "Felder für den Körper nicht gezeigt",
    )
    h.bild("1_rohteil_aus_dem_dokument", panel.form)

    # Zurück zum Quader und wieder zum Körper.
    panel.knopf_rohteil_quader.setChecked(True)
    yield from warten()
    h.pruefe(hasattr(job.Stock, "ExtZpos"), f"nicht wieder der Quader: {job.Stock.Label}")
    h.pruefe(kasten() == (-1.0, 101.0, -1.0, 61.0, 21.0), f"Quader: {kasten()}")
    h.pruefe(rohteil.ViewObject.Visibility, "das Original nach dem Quader nicht wieder da")
    panel.knopf_rohteil_teil.setChecked(True)
    yield from warten()
    h.pruefe(rohteil in (getattr(job.Stock, "Objects", None) or []), "nicht wieder der Körper")

    # --- Nullpunkt „Mitte oben“: Teil und Rohteil wandern zusammen -----------------------------
    index = panel.wahl_nullpunkt.findText("Mitte oben")
    h.pruefe(index > 0, "kein Nullpunkt „Mitte oben“")
    panel.wahl_nullpunkt.setCurrentIndex(max(index, 0))
    yield from h.warte_auf(lambda: not panel._nullpunkt_uhr.isActive(), 5000)
    yield 800
    h.pruefe(kasten() == (-52.0, 52.0, -32.0, 32.0, 0.0), f"Kasten nach Mitte oben: {kasten()}")
    bb = vr.modell(job).Shape.BoundBox
    h.pruefe(
        abs(bb.XMin + 50) < 1e-6 and abs(bb.YMin + 30) < 1e-6 and abs(bb.ZMax + 5) < 1e-6,
        f"Teil im Job: {bb}",
    )
    panel.knopf_weiter.click()
    yield 500
    kurz = panel.rohteil_kurz.text()
    h.pruefe(kurz.startswith("Rohteil: Rohteil · "), f"Schritt 2: {kurz!r}")
    yield from h.warte_auf(lambda: panel.plan.vorschau is not None, 120000)
    yield 1000
    h.bild("2_schritt2", panel.form)

    # --- Anlegen: das Rohteil bleibt der Körper -------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    h.pruefe(
        rohteil in (getattr(job.Stock, "Objects", None) or []),
        f"nach dem Anlegen: {job.Stock.Label}",
    )
    ops = [o.Label for o in job.Operations.Group]
    # Die Zeit entscheidet (Grundsatz 0): Planfräsen und Räumen liegen hier 3 % auseinander,
    # der Adaptiv-Kern streut ±1,5 % – beides ist richtig; geprüft wird das Rohteil.
    h.pruefe(any(o.startswith(("Planfräsen", "Räumen")) for o in ops), f"Operationen: {ops}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("3_angelegt")
    FreeCAD.closeDocument(doc.Name)
    yield 300
