# „Bearbeitung (Fräsen)“ mit „Restschruppen“ (W-006 4.2 Punkt 2): Platte 66 × 40 × 10 mit zwei
# Kuppeln (Kugel R 12, Fuß Ø 20,8, oben z 16) bei x 20 und x 46 – zwischen den Füßen 5,2 mm; T1
# der Standardfräser Ø 12, T5 ein Schaftfräser Ø 6. Beide Kuppeln anklicken: „3D-Schruppen“ mit
# T1 angehakt, „Restschruppen“ nicht – den Haken setzt man selbst (das 3D-Schlichten nehmen wir
# hier heraus). Angehakt: T5 vorgewählt (der größte, der kleiner ist als T1), „Fräser davor Ø“
# leer mit „wie beim 3D-Schruppen“, die Vorschau „→ …“ ohne roten Satz. „Anlegen“: „3D-Schruppen
# T1“ und „Restschruppen T5“ mit Ø 12 und Eckenradius 0 davor.
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
    from camaddon import schruppen3d as r3op
    from camaddon import werkzeuge as wz

    t5 = wz.Werkzeug(
        nummer=5,
        name="Schaft 6",
        art=wz.SCHAFTFRAESER,
        durchmesser=6.0,
        schneiden=3,
        schneidenlaenge=18.0,
        schneidstoff=wz.VHM,
    )
    t5.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=0.75, ap=12.0, vc=85.0, fz=0.05)]
    wz.Bibliothek([wz.standardwerkzeug(), t5]).speichern()

    doc = FreeCAD.newDocument("Kuppeln")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    form = Part.makeBox(66, 40, 10)
    for x in (20.0, 46.0):
        kappe = Part.makeSphere(12, V(x, 20, 4)).common(Part.makeBox(66, 40, 10, V(0, 0, 10)))
        form = form.fuse(kappe)
    teil.Shape = form.removeSplitter()
    doc.recompute()
    kuppeln = [
        f"Face{i + 1}" for i, f in enumerate(teil.Shape.Faces) if isinstance(f.Surface, Part.Sphere)
    ]
    h.pruefe(len(kuppeln) == 2, f"Kuppeln: {kuppeln}")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    for name in kuppeln:
        Gui.Selection.addSelection(doc.Name, teil.Name, name)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    schruppen = panel.schruppen3d
    panel.schlichten3d.haken.setChecked(False)  # hier nur schruppen
    yield from h.warte_auf(lambda: schruppen.vorschau is not None, 180000)
    rest = panel.restschruppen
    h.pruefe(schruppen.aktiv() and not rest.aktiv(), "Haken: 3D-Schruppen ja, Restschruppen nein")
    h.pruefe(schruppen.fraeser() is not None and schruppen.fraeser().nummer == 1, "nicht T1")
    rest.haken.setChecked(True)  # wie ein Klick: der Haken von Hand
    yield from h.warte_auf(lambda: rest.vorschau is not None, 180000)
    yield 800
    h.pruefe(rest.fraeser() is not None and rest.fraeser().nummer == 5, "Rest: nicht T5")
    h.pruefe(
        not rest.felder["davor"].text() and rest.felder["davor"].placeholderText()
        == "wie beim 3D-Schruppen",
        f"davor: {rest.felder['davor'].text()!r} / {rest.felder['davor'].placeholderText()!r}",
    )  # fmt: skip
    text = rest.ergebnis.text()
    h.pruefe(text.startswith("→ ") and " Ringe, etwa " in text, f"Restschruppen: {text!r}")
    h.pruefe(not rest.hinweis.text(), f"rot: {rest.hinweis.text()!r}")
    h.bild("1_restschruppen", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = list(job.Operations.Group)
    h.pruefe(
        [o.Label for o in ops] == ["3D-Schruppen T1", "Restschruppen T5"],
        f"Operationen: {[o.Label for o in ops]}",
    )
    op = ops[-1] if ops else None
    if op is None or not r3op.ist_restschruppen(op):
        h.pruefe(False, "kein Restschruppen")
        return
    h.pruefe(
        abs(float(op.DurchmesserDavor) - 12.0) < 1e-9 and float(op.EckenradiusDavor) < 1e-9,
        f"davor: {float(op.DurchmesserDavor)}, {float(op.EckenradiusDavor)}",
    )
    h.pruefe(op.Ringe > 0 and len(op.Path.Commands) > 20, f"Bahn: {op.Ringe} Ringe")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_angelegt")
    FreeCAD.closeDocument(doc.Name)
    yield 300
