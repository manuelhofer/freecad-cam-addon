# „Plan indexiert“ im 4-Achs-Assistenten (W-003 Stufe V4c; W-006 S2). Welle Ø 20 × 40 mit
# einer Abflachung auf x = 8 zwischen zwei Wänden, Stange Ø 24, T1 Schaftfräser Ø 6 (Einsätze
# Planen und Schruppen), T2 Kugelfräser Ø 4 (Schlichten). Schritt 2 ohne Flächen: der Haken
# „Plan indexiert“ gesperrt, grau der Grund. Ein Klick auf die Abflachung: der Haken geht an
# (Vorschlag mit Grund), die Vorschau sagt „→ 2 Lagen, 6 Zeilen“. „Anlegen“: drei Operationen,
# „Plan indexiert T1“ mit 2 Lagen und 6 Zeilen, die Sätze mit Y und festem C. Doppelklick
# darauf öffnet den Assistenten mit ihren Werten; „Übernehmen“ mit 1 mm Zustellung rechnet
# sie neu – mehr Lagen.
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

    from camaddon import gui_vierachs
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_plan as vplan
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(nummer=1, durchmesser=6, schneiden=3, schneidenlaenge=16)
    t1.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.PLANEN, ae=4, ap=2, vc=150, fz=0.04),
        wz.Einsatz(art=wz.SCHRUPPEN, ae=2.4, ap=2, vc=150, fz=0.04),
    ]
    t2 = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=4, schneiden=2)
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.5, ap=4, vc=150, fz=0.03)]
    wz.Bibliothek([t1, t2]).speichern()

    doc = FreeCAD.newDocument("Abflachung")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Welle")
    teil.Shape = (
        Part.makeCylinder(10, 40, FreeCAD.Vector(0, 0, -40))
        .cut(Part.makeBox(10, 30, 20, FreeCAD.Vector(8, -15, -30)))
        .removeSplitter()
    )
    doc.recompute()
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f) and (vr.aussennormale(f) - FreeCAD.Vector(0, 0, 1)).Length < 1e-6
    )
    abflachung = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f) and (vr.aussennormale(f) - FreeCAD.Vector(1, 0, 0)).Length < 1e-6
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.feld_stange.setText("24")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.accept()  # Weiter
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")

    # --- Ohne Flächen (rundum): mit dem Y angeboten, ohne Haken (P-2026-10-03-09) -----------
    h.pruefe(
        panel.mit_plan.isEnabled() and not panel.mit_plan.isChecked(), "Plan rundum nicht angeboten"
    )
    text = panel.plan_grund.text()
    h.pruefe(text.startswith("Mit der Querachse geht Face"), f"Grund: {text!r}")
    h.pruefe(panel._schlicht_flaechen() == [], "rundum ohne Haken: Schlichten nicht rundum")
    yield from h.warte_auf(
        lambda: panel.vorschau is not None and panel.vorschau_schlichten is not None, 30000
    )

    # --- Die Abflachung: der Haken geht an, die Vorschau ------------------------------------
    job = panel.job
    klon = vr.modell(job)
    Gui.Selection.addSelection(doc.Name, klon.Name, abflachung)
    yield 500
    h.pruefe(panel.flaechen() == [abflachung], f"gewählt: {panel.flaechen()}")
    h.pruefe(panel.mit_plan.isEnabled() and panel.mit_plan.isChecked(), "Plan mit Abflachung aus")
    text = panel.plan_grund.text()
    h.pruefe(
        text.startswith("Vorschlag: an – eben längs der Stange: " + abflachung), f"Grund: {text!r}"
    )
    h.pruefe(panel.planfraeser() is not None and panel.planfraeser().nummer == 1, "Fräser für Plan")
    einsatz = panel.planeinsatz()
    h.pruefe(einsatz is not None and einsatz.art == wz.PLANEN, "Einsatz Planen vorgewählt")
    yield from h.warte_auf(lambda: panel.vorschau_plan is not None, 30000)
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    text = panel.ergebnis_plan.text()
    h.pruefe(text.startswith("→ 2 Lagen, 6 Zeilen, etwa"), f"Vorschau: {text!r}")
    from camaddon.gui_teile import blaettere_zu

    blaettere_zu(panel.mit_plan)
    yield 300
    h.bild("1_plan_vorgeschlagen", panel.form)

    # --- Anlegen: drei Operationen, „Plan indexiert T1“ mit Y -------------------------------
    yield from h.warte_auf(
        lambda: panel.vorschau is not None and panel.vorschau_schlichten is not None, 30000
    )
    panel.accept()  # Anlegen
    yield 2500
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster nach „Anlegen“ offen")
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    h.pruefe(len(ops) == 3, f"Operationen: {[o.Label for o in ops]}")
    plan = next((o for o in ops if vplan.ist_plan(o)), None)
    h.pruefe(plan is not None and plan.Label == "Plan indexiert T1", f"Plan: {plan and plan.Label}")
    if plan is None:
        return
    h.pruefe(
        (plan.Ebenen, plan.Lagen, plan.Zeilen) == (1, 2, 6),
        f"{plan.Ebenen}, {plan.Lagen}, {plan.Zeilen}",
    )
    h.pruefe(list(plan.Flaechen) == [abflachung], f"Flächen: {list(plan.Flaechen)}")
    schnitte = [b for b in plan.Path.Commands if b.Name == "G1"]
    h.pruefe(len(schnitte) > 10 and all("Y" in b.Parameters for b in schnitte), "Sätze ohne Y")
    h.pruefe(len({round(b.Parameters.get("C", 0.0), 6) for b in schnitte}) == 1, "C dreht")
    for op in ops:
        if op is not plan:
            op.ViewObject.Visibility = False
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("2_angelegt")

    # --- Ändern: Doppelklick öffnet den Assistenten mit den Werten --------------------------
    plan.ViewObject.Proxy.doubleClicked(plan.ViewObject)
    yield 1000
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.zu_aendern is plan, "Doppelklick öffnet nichts")
    if panel is None:
        return
    h.pruefe(panel.mit_plan.isChecked() and panel.mit_schruppen.isHidden(), "beim Ändern: Haken")
    h.pruefe(
        panel.planfraeser() is not None and panel.planfraeser().nummer == 1, "beim Ändern: Fräser"
    )
    yield from h.warte_auf(lambda: panel.vorschau_plan is not None, 30000)
    h.bild("3_aendern", panel.form)
    panel.felder_plan["zustellung_plan"].setText("1")
    yield from h.warte_auf(lambda: panel.vorschau_plan is not None, 30000)
    h.pruefe(panel.accept() is True, "„Übernehmen“ ging nicht")
    yield 1500
    # Die Lagen beginnen auf dem Rest nach dem Schruppen (gut Ø 20,6): mit 1 mm mehr als zwei.
    h.pruefe(plan.Lagen >= 3, f"nach dem Ändern: {plan.Lagen} Lagen")
    FreeCAD.closeDocument(doc.Name)
    yield 300
