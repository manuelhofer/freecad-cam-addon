# „Plan indexiert“ im 4-Achs-Assistenten (W-003 Stufe V4c; W-006 S2). Welle Ø 20 × 40 mit
# einer Abflachung auf x = 8 zwischen zwei Wänden, Stange Ø 24, T1 Schaftfräser Ø 6 (Einsätze
# Planen und Schruppen), T2 Kugelfräser Ø 4 (Schlichten). Schritt 2 ohne Flächen: rundum
# „Plan indexiert“ angehakt mit T1, dem Fräser des Schruppens, das Schlichten ohne die Ebene. Ein
# Klick auf die Abflachung: der Haken geht an, „Rundum schlichten“ aus (W-027: die Kugel führe
# die Abflachung nur noch einmal)
# (Vorschlag mit Grund), die Vorschau sagt „→ 2 Lagen, 9 Zeilen“ (vom Rest nach dem Schruppen).
# „Anlegen“: zwei Operationen,
# „Plan indexiert T1“ mit 2 Lagen und 6–9 Zeilen, die Sätze mit Y und festem C. Doppelklick
# darauf öffnet den Assistenten mit ihren Werten; „Übernehmen“ mit 1 mm Zustellung rechnet
# sie neu – vom Rest nach dem Schruppen aus, feiner.
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

    # --- Ohne Flächen (rundum): vorbelegt an, mit dem Fräser des Schruppens (Manuel, 2026-10-11,
    # Frage 10; bis dahin nur angeboten, P-2026-10-03-09) – das Schlichten lässt die Ebene aus.
    h.pruefe(
        panel.mit_plan.isEnabled() and panel.mit_plan.isChecked(), "Plan rundum nicht vorbelegt"
    )
    text = panel.plan_grund.text()
    h.pruefe(text.startswith("Vorschlag: an – Face"), f"Grund: {text!r}")
    h.pruefe(
        panel.planfraeser() is not None and panel.planfraeser() is panel.fraeser(),
        "Plan rundum: nicht der Fräser des Schruppens",
    )
    schlicht = panel._schlicht_flaechen()
    h.pruefe(
        bool(schlicht) and abflachung not in schlicht,
        f"rundum mit Plan: Schlichten über {schlicht}",
    )
    # Mit den übrigen Flächen: die Spirale rundum mit Y, über der Ebene angehoben im Freivorschub
    # (Frage 12, Manuel 2026-10-11) – der Haken frei und vorgeschlagen, der Grund sagt es.
    h.pruefe(
        panel.schlichten_querachse.isEnabled()
        and panel.schlichten_querachse.isChecked()
        and panel.querachse_grund.text().startswith("Mit Flächen fährt die Spirale rundum"),
        f"Querachse beim Schlichten: {panel.querachse_grund.text()!r}",
    )
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
    # „Rundum schlichten“ geht aus: Plan indexiert macht die Abflachung fertig, die Kugel führe
    # sie nur noch einmal (W-027; Manuel, 2026-10-17).
    h.pruefe(not panel.mit_schlichten.isChecked(), "„Rundum schlichten“ neben Plan indexiert an")
    text = panel.erklaerung_schlichten.text()
    h.pruefe(
        text
        == "Vorschlag: aus – „Plan indexiert“ macht alle gewählten Flächen fertig ("
        + abflachung
        + "); „Rundum schlichten“ führe sie nur noch einmal.",
        f"Satz unter „Rundum schlichten“: {text!r}",
    )
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
    # Vom Rest nach dem Schruppen aus wie die Operation (P-2026-10-11-52) – mit den kurzen Zeilen
    # in der oberen Lage, die der Rest neben der Wand braucht (bis dahin von der Stange: 6).
    h.pruefe(text.startswith("→ 2 Lagen, 9 Zeilen, etwa"), f"Vorschau: {text!r}")
    from camaddon.gui_teile import blaettere_zu

    blaettere_zu(panel.mit_plan)
    yield 300
    h.bild("1_plan_vorgeschlagen", panel.form)

    # --- Anlegen: zwei Operationen, „Plan indexiert T1“ mit Y – kein Schlichten (W-027) -----
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    panel.accept()  # Anlegen
    yield 2500
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster nach „Anlegen“ offen")
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    h.pruefe(len(ops) == 2, f"Operationen: {[o.Label for o in ops]}")
    plan = next((o for o in ops if vplan.ist_plan(o)), None)
    h.pruefe(plan is not None and plan.Label == "Plan indexiert T1", f"Plan: {plan and plan.Label}")
    if plan is None:
        return
    # Mit dem Rest nach dem Schruppen (seit P-2026-10-03-17 mit der ganzen Stirn gerechnet):
    # zwei Lagen; dicht an den Wänden ließ die Schruppspirale einen Keil (ihr Ring kommt mit
    # der runden Stirn dort nur schmal hin), den nehmen in der oberen Lage zwei kurze Zeilen
    # mehr – 9 statt 6.
    h.pruefe(
        plan.Ebenen == 1 and plan.Lagen == 2 and 6 <= plan.Zeilen <= 9,
        f"{plan.Ebenen}, {plan.Lagen}, {plan.Zeilen}",
    )
    h.pruefe(list(plan.Flaechen) == [abflachung], f"Flächen: {list(plan.Flaechen)}")
    h.pruefe(plan.Weg == "Zeilen", f"Weg ohne Wahl: {plan.Weg!r}")
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
    # Stiche von der offenen Seite (P-2026-10-12-146): „nur Gleichlauf“ gilt dann nicht.
    from camaddon import vierachs_planbahn as vp

    panel.wahl_plan_weg.setCurrentIndex(panel.wahl_plan_weg.findData(vp.WEG_STICHE_GLEICHLAUF))
    yield 300
    h.pruefe(
        not panel.plan_nur_gleichlauf.isEnabled(), "„nur Gleichlauf“ bei den Stichen bedienbar"
    )
    yield from h.warte_auf(lambda: panel.vorschau_plan is not None, 30000)
    h.pruefe(
        not panel.hinweis_bearbeitung.text(), f"Stiche rot: {panel.hinweis_bearbeitung.text()!r}"
    )
    h.bild("3b_stiche", panel.form)
    h.pruefe(panel.accept() is True, "„Übernehmen“ ging nicht")
    yield 1500
    # Die Lagen beginnen auf dem Rest nach dem Schruppen (Aufmaß 0,3 über Ø 16, dazu der Keil
    # an den Wänden bis gut 9,4): mit 1 mm Zustellung zwei Lagen, feiner als vorher die zwei
    # mit 2 mm – mehr Zeilen.
    h.pruefe(plan.Weg == "Stiche im Gleichlauf", f"Weg nach dem Ändern: {plan.Weg!r}")
    # Die Stiche beginnen am höchsten Rest, den die Mitte des Fräsers erreicht (wie das Räumen,
    # raeumen_bahn._mit_stand) – der schmale Keil an den Wänden zählt nicht: eine Lage.
    h.pruefe(plan.Lagen >= 1, f"nach dem Ändern: {plan.Lagen} Lagen, {plan.Zeilen} Stiche")
    schnitte = [b for b in plan.Path.Commands if b.Name == "G1"]
    h.pruefe(len({round(b.Parameters.get("C", 0.0), 6) for b in schnitte}) == 1, "Stiche: C dreht")
    FreeCAD.closeDocument(doc.Name)
    yield 300
