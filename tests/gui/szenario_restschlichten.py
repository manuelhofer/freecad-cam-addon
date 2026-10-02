# „Bearbeitung (Fräsen)“ mit „Restschlichten“ (W-006 4.2 Punkt 8): Platte 60 × 60 × 10 mit einer
# Kuppel (Kugel R 25, Fuß Ø 40, oben z 20); T1 der Standardfräser Ø 12, T3 ein Kugelfräser Ø 6, T4
# ein Kugelfräser Ø 2. Die Kuppel anklicken: „3D-Schruppen“ und „3D-Schlichten“ (T3) angehakt,
# „Restschlichten“ nicht – den Haken setzt man selbst. Angehakt: T4 vorgewählt (der größte, der
# kleiner ist als T3), „Fräser davor Ø“ leer mit „wie beim 3D-Schlichten“, die Vorschau „→ N
# Höhenlinien und …“ (der Rest liegt am Fuß der Kuppel, wo die Kugel Ø 6 nicht in die Kehle kam).
# „Anlegen“: „3D-Schruppen T1“, „3D-Schlichten T3“, „Restschlichten T4“ – mit Ø 6 und Eckenradius
# 3 davor. Doppelklick auf „Restschlichten T4“ öffnet nur seinen Block, „Fräser davor Ø“ zeigt 6.
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
    from camaddon import schlichten3d as s3op
    from camaddon import werkzeuge as wz

    def kugel(nummer, durchmesser):
        w = wz.Werkzeug(
            nummer=nummer,
            name=f"Kugel {durchmesser:g}",
            art=wz.KUGELFRAESER,
            durchmesser=durchmesser,
            schneiden=2,
            schneidenlaenge=3 * durchmesser,
            schneidstoff=wz.VHM,
        )
        w.schnittwerte[wz.ALLE] = [
            wz.Einsatz(art=wz.SCHLICHTEN, ae=0.05 * durchmesser, ap=0.05 * durchmesser, vc=150.0,
                       fz=0.01 * durchmesser)
        ]  # fmt: skip
        return w

    wz.Bibliothek([wz.standardwerkzeug(), kugel(3, 6.0), kugel(4, 2.0)]).speichern()

    doc = FreeCAD.newDocument("Rest")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    kappe = Part.makeSphere(25, V(30, 30, -5)).common(Part.makeBox(60, 60, 15, V(0, 0, 10)))
    teil.Shape = Part.makeBox(60, 60, 10).fuse(kappe).removeSplitter()
    doc.recompute()
    kuppel = next(
        (
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if isinstance(f.Surface, Part.Sphere)
        ),
        None,
    )
    if kuppel is None:
        h.pruefe(False, "keine Kugelfläche")
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, kuppel)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    schlichten = panel.schlichten3d
    for i in range(schlichten.wahl_fraeser.count()):
        if schlichten._fraeser[i].nummer == 3:
            schlichten.wahl_fraeser.setCurrentIndex(i)  # der große Kugelfräser zuerst
    for block in (panel.schruppen3d, schlichten):
        yield from h.warte_auf(lambda b=block: b.vorschau is not None, 180000)
    rest = panel.restschlichten
    h.pruefe(
        panel.schruppen3d.aktiv() and schlichten.aktiv() and not rest.aktiv(),
        "Haken: 3D-Schruppen und 3D-Schlichten von sich aus, Restschlichten nicht",
    )
    h.pruefe(schlichten.fraeser() is not None and schlichten.fraeser().nummer == 3, "nicht T3")
    rest.haken.setChecked(True)  # wie ein Klick: der Haken von Hand
    yield from h.warte_auf(lambda: rest.vorschau is not None, 180000)
    yield 800
    h.pruefe(rest.fraeser() is not None and rest.fraeser().nummer == 4, "Rest: nicht T4")
    h.pruefe(
        not rest.felder["davor"].text() and rest.felder["davor"].placeholderText()
        == "wie beim 3D-Schlichten",
        f"davor: {rest.felder['davor'].text()!r} / {rest.felder['davor'].placeholderText()!r}",
    )  # fmt: skip
    text = rest.ergebnis.text()
    h.pruefe(text.startswith("→ ") and "Höhenlinien" in text, f"Restschlichten: {text!r}")
    h.pruefe(not rest.hinweis.text(), f"rot: {rest.hinweis.text()!r}")
    h.bild("1_restschlichten", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = list(job.Operations.Group)
    h.pruefe(
        [o.Label for o in ops] == ["3D-Schruppen T1", "3D-Schlichten T3", "Restschlichten T4"],
        f"Operationen: {[o.Label for o in ops]}",
    )
    op = ops[-1] if ops else None
    if op is None or not s3op.ist_restschlichten(op):
        h.pruefe(False, "kein Restschlichten")
        return
    h.pruefe(
        abs(float(op.DurchmesserDavor) - 6.0) < 1e-9 and abs(float(op.EckenradiusDavor) - 3.0) < 1e-9,
        f"davor: {float(op.DurchmesserDavor)}, {float(op.EckenradiusDavor)}",
    )  # fmt: skip
    h.pruefe(op.Hoehenlinien > 0 and len(op.Path.Commands) > 50, f"Bahn: {op.Hoehenlinien}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_angelegt")

    # --- Ändern: Doppelklick öffnet nur den Block Restschlichten -----------------------------
    op.ViewObject.Proxy.doubleClicked(op.ViewObject)
    yield 1000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.zu_aendern is op, "Doppelklick öffnet nichts")
    if panel is None:
        return
    rest = panel.restschlichten
    h.pruefe(panel.block_zu_aendern is rest, "beim Ändern: nicht der Block Restschlichten")
    h.pruefe(not panel.schlichten3d.widget.isVisible(), "beim Ändern: 3D-Schlichten sichtbar")
    h.pruefe(rest.felder["davor"].text() == "6", f"davor: {rest.felder['davor'].text()!r}")
    yield from h.warte_auf(lambda: rest.vorschau is not None, 180000)
    h.pruefe(not rest.hinweis.text(), f"beim Ändern rot: {rest.hinweis.text()!r}")
    h.bild("3_aendern", panel.form)
    h.pruefe(panel.accept() is True, "„Übernehmen“ ging nicht")
    yield 2000
    h.pruefe(abs(float(op.EckenradiusDavor) - 3.0) < 1e-9, "Eckenradius davor verloren")
    FreeCAD.closeDocument(doc.Name)
    yield 300
