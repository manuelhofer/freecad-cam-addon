# „Rundum entgraten“ im 4-Achs-Assistenten (W-003 Stufe V4d; W-006 S2). Welle Ø 20 × 40 mit
# einer Abflachung auf x = 8 zwischen zwei Wänden, Stange Ø 24, T1 Schaftfräser Ø 6 (Einsatz
# Schruppen), T3 Fasenfräser Ø 8, 90° (Einsatz Fasen). Schritt 2: der Haken „Rundum entgraten“
# ist vorgeschlagen (Außenkanten der Abflachung und der Fasenfräser sind da), grau der Grund,
# die Vorschau sagt „→ 2 Kanten, etwa …“. „Anlegen“ (ohne „Plan indexiert“, das T1 auch
# könnte): zwei Operationen, „Rundum entgraten T3“ mit 2 Kanten, die Sätze mit fester Rundachse
# je Kante und der Spitze 9,72 von der Achse. Doppelklick darauf öffnet den Assistenten mit der
# Fasenbreite; „Übernehmen“ mit 0,5 mm rechnet sie neu – tiefer.
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
    from camaddon import vierachs_entgraten as vent
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(nummer=1, durchmesser=6, schneiden=3, schneidenlaenge=16)
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=2.4, ap=2, vc=150, fz=0.04)]
    t3 = wz.Werkzeug(
        nummer=3, art=wz.FASENFRAESER, durchmesser=8, schneiden=2, spitzenwinkel=90, spitzen_d=1
    )
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=100, fz=0.03)]
    wz.Bibliothek([t1, t3]).speichern()

    doc = FreeCAD.newDocument("Entgraten")
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

    # --- Rundum: alle Außenkanten, vorgeschlagen mit dem Fasenfräser ----------------------
    h.pruefe(
        panel.mit_entgraten.isEnabled() and panel.mit_entgraten.isChecked(), "Entgraten nicht an"
    )
    text = panel.entgrat_grund.text()
    h.pruefe(text.startswith("Vorschlag: an – 6 Außenkanten"), f"Grund: {text!r}")
    h.pruefe(panel.entgratfraeser() is not None and panel.entgratfraeser().nummer == 3, "Fräser T3")
    einsatz = panel.entgrateinsatz()
    h.pruefe(einsatz is not None and einsatz.art == wz.FASEN, "Einsatz Fasen vorgewählt")
    h.pruefe(not panel.mit_plan.isChecked(), "Plan ohne ebene Fläche an")
    yield from h.warte_auf(lambda: panel.vorschau_entgraten is not None, 30000)
    text = panel.ergebnis_entgraten.text()
    h.pruefe(text.startswith("→ 6 Kanten, etwa"), f"Vorschau rundum: {text!r}")

    # --- Die Abflachung: ihre zwei Kanten ---------------------------------------------------
    job = panel.job
    klon = vr.modell(job)
    Gui.Selection.addSelection(doc.Name, klon.Name, abflachung)
    yield 500
    h.pruefe(panel.flaechen() == [abflachung], f"gewählt: {panel.flaechen()}")
    text = panel.entgrat_grund.text()
    h.pruefe(text.startswith("Vorschlag: an – 2 Außenkanten"), f"Grund: {text!r}")
    # „Plan indexiert“ (T1 mit Einsatz Schruppen könnte es) hier nicht – nur Schruppen und
    # Entgraten.
    panel.mit_plan.setChecked(False)
    yield 300
    yield from h.warte_auf(lambda: panel.vorschau_entgraten is not None, 30000)
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    text = panel.ergebnis_entgraten.text()
    h.pruefe(text.startswith("→ 2 Kanten, etwa"), f"Vorschau: {text!r}")
    from camaddon.gui_teile import blaettere_zu

    blaettere_zu(panel.mit_entgraten)
    yield 300
    h.bild("1_entgraten_vorgeschlagen", panel.form)

    # --- Anlegen: zwei Operationen, „Rundum entgraten T3“ -----------------------------------
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    panel.accept()  # Anlegen
    yield 2500
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster nach „Anlegen“ offen")
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    h.pruefe(len(ops) == 2, f"Operationen: {[o.Label for o in ops]}")
    entgraten = next((o for o in ops if vent.ist_entgraten(o)), None)
    h.pruefe(
        entgraten is not None and entgraten.Label == "Rundum entgraten T3",
        f"Entgraten: {entgraten and entgraten.Label}",
    )
    if entgraten is None:
        return
    h.pruefe(
        (entgraten.Kanten, entgraten.Ausgelassen) == (2, 0),
        f"{entgraten.Kanten}, {entgraten.Ausgelassen}",
    )
    h.pruefe(list(entgraten.Flaechen) == [abflachung], f"Flächen: {list(entgraten.Flaechen)}")
    # Welche Achse die Spitze radial führt und welche das Teil dreht, sagt die Operation (an
    # der gewählten Maschine die Stange längs X, die A-Achse dreht).
    richtung = entgraten.Werkzeugrichtung
    radial = "XYZ"[max(range(3), key=lambda i: abs(richtung[i]))]
    rund = str(entgraten.Rundachse)
    schnitte = [b for b in entgraten.Path.Commands if b.Name == "G1"]
    h.pruefe(len(schnitte) >= 4 and all(radial in b.Parameters for b in schnitte), "Sätze")
    h.pruefe(
        len({round(b.Parameters.get(rund, 0.0), 3) for b in schnitte}) == 2,
        f"{rund} steht nicht je Kante",
    )
    r_werte = [b.Parameters[radial] for b in schnitte]
    h.pruefe(all(9.69 <= r <= 9.73 for r in r_werte), f"{radial} {min(r_werte)} … {max(r_werte)}")
    for op in ops:
        if op is not entgraten:
            op.ViewObject.Visibility = False
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("2_angelegt")

    # --- Ändern: Doppelklick öffnet den Assistenten mit der Fasenbreite ---------------------
    entgraten.ViewObject.Proxy.doubleClicked(entgraten.ViewObject)
    yield 1000
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.zu_aendern is entgraten, "Doppelklick öffnet nichts")
    if panel is None:
        return
    h.pruefe(
        panel.mit_entgraten.isChecked() and panel.mit_schruppen.isHidden(), "beim Ändern: Haken"
    )
    h.pruefe(
        panel.entgratfraeser() is not None and panel.entgratfraeser().nummer == 3,
        "beim Ändern: Fräser",
    )
    yield from h.warte_auf(lambda: panel.vorschau_entgraten is not None, 30000)
    h.bild("3_aendern", panel.form)
    panel.felder_entgraten["breite"].setText("0,5")
    yield from h.warte_auf(lambda: panel.vorschau_entgraten is not None, 30000)
    h.pruefe(panel.accept() is True, "„Übernehmen“ ging nicht")
    yield 1500
    r_werte = [b.Parameters[radial] for b in entgraten.Path.Commands if b.Name == "G1"]
    h.pruefe(all(9.49 <= r <= 9.53 for r in r_werte), f"nach dem Ändern: {radial} {min(r_werte)}")
    FreeCAD.closeDocument(doc.Name)
    yield 300
