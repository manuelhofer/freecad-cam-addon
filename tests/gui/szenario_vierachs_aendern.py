# „Rundum schruppen“ nachträglich ändern (Manuel, 2026-09-29: „wenn ich jetzt hier
# nochmal schnittwerte ändern will oder anders werkzeug komme ich nicht mehr in die
# maske rein“). In der Werkzeugverwaltung stehen T1 Ø 12 und T2 Ø 8, beide mit
# „Schruppen“. Welle Ø 60 in die Stange Ø 80, „Rundum schruppen“ mit T1 angelegt.
# Doppelklick auf die Operation: Schritt 2 steht offen, Kopf „„Rundum schruppen T1“
# ändern“, T1 und „Schruppen“ gewählt, die Felder leer (die Werte sind die Vorschläge),
# der Knopf heißt „Übernehmen“. T2 und Aufmaß 0,5 → „Übernehmen“: Die Operation heißt
# „Rundum schruppen T2“, hat den Controller „T2 Schruppen“, Zustellung 1,5 (der
# Vorschlag von T2) – „T1 Schruppen“ ist weg, ein Schritt Rückgängig. Wieder öffnen
# über den Knopf (der Ordner „Operations“ des Jobs gewählt – Manuel, 2026-09-30),
# Zustellung 1 und „Abbrechen“: nichts geändert.
# Noch einmal, Zustellung 1, „Übernehmen“: derselbe Controller. Dann „Zurück“ zu
# Schritt 1: Stange 80, Planaufmaß 1, Abstechbreite 3, Spannlänge 30, Rundachse A, wie
# im Job; Ø 90 → die Stange wächst sofort, „Weiter“, „Übernehmen“: zwei Schritte
# Rückgängig („Stange ändern“, „Rundum schruppen ändern“), mehr Lagen. Ø 100 und
# „Abbrechen“: die Stange bleibt Ø 90. Fünfmal Strg+Z: wieder T1, Zustellung 2, Ø 80.
# Der kleinere T2 braucht hinten 4 mm weniger Platz: Die Stange wird kürzer (V3f).
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
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26)
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=150, fz=0.08)]
    t2 = wz.Werkzeug(nummer=2, durchmesser=8, schneiden=3, schneidenlaenge=20)
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=3.2, ap=1.5, vc=150, fz=0.06)]
    t3 = wz.Werkzeug(nummer=3, art=wz.KUGELFRAESER, durchmesser=10, schneiden=2)
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4, ap=1, vc=150, fz=0.05)]
    wz.Bibliothek([t1, t2, t3]).speichern()

    doc = FreeCAD.newDocument("Welle")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Welle")
    teil.Shape = Part.makeCylinder(30, 100, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0))
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f) and (vr.aussennormale(f) - FreeCAD.Vector(1, 0, 0)).Length < 1e-9
    )
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    # --- Anlegen mit T1 ------------------------------------------------------------------
    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.feld_stange.setText("80")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.accept()  # Weiter
    yield 300
    panel.wahl_fraeser.setCurrentIndex(0)
    yield from h.warte_auf(lambda: panel.vorschau is not None, 15000)
    job = panel.job
    panel.accept()  # Anlegen
    yield 1500
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    h.pruefe(len(ops) == 1, f"Operationen: {[o.Label for o in job.Operations.Group]}")
    if not ops:
        return
    op = ops[0]
    h.pruefe(op.Label == "Rundum schruppen T1", f"Name: {op.Label!r}")
    schritte_vorher = list(doc.UndoNames)

    # --- Doppelklick: Schritt 2 mit den Werten der Operation --------------------------------
    op.ViewObject.Proxy.doubleClicked(op.ViewObject)
    yield 1000
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.zu_aendern is op, "Doppelklick öffnet nichts")
    if panel is None:
        return
    ok = panel.knopf_anlegen()
    h.pruefe(panel.seite == 2 and ok is not None and ok.text() == "Übernehmen", "Seite/Knopf")
    kopf = panel._kopf_text.text()
    h.pruefe("„Rundum schruppen T1“ ändern" in kopf, f"Kopf: {kopf!r}")
    h.pruefe(panel.fraeser() is not None and panel.fraeser().nummer == 1, "T1 nicht gewählt")
    h.pruefe(panel.einsatz() is not None and panel.einsatz().art == wz.SCHRUPPEN, "Einsatz")
    texte = {k: f.text() for k, f in panel.felder_schruppen.items()}
    h.pruefe(not any(texte.values()), f"Felder: {texte}")
    h.pruefe(
        panel.mit_schruppen.isChecked() and not panel.mit_schruppen.isEnabled(), "Haken änderbar"
    )
    h.pruefe(not panel.knopf_zurueck.isHidden(), "„Zurück“ fehlt")
    h.pruefe(panel.hinweis_aendern.isHidden(), f"Hinweis: {panel.hinweis_aendern.text()!r}")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 15000)
    h.pruefe(
        not panel.hinweis_rund.text(), f"Hinweis beim Schaftfräser: {panel.hinweis_rund.text()}"
    )
    h.bild("1_aendern_geoeffnet", panel.form)

    # Ein Kugelfräser schruppt wie ein Schaftfräser; ein Satz sagt, wie hoch Rillen bleiben
    # (Ø 10, 4 mm je Umdrehung: 5 − √21 ≈ 0,42 mm).
    panel.wahl_fraeser.setCurrentIndex(2)
    yield from h.warte_auf(lambda: panel.vorschau is not None, 15000)
    rund = panel.hinweis_rund.text()
    h.pruefe(rund.startswith("Kugelfräser:") and "0,42 mm" in rund, f"Kugelfräser: {rund!r}")
    h.bild("1b_kugelfraeser", panel.form)

    # T2 und Aufmaß 0,5: Die Zustellung folgt dem Vorschlag von T2.
    panel.wahl_fraeser.setCurrentIndex(1)
    panel.felder_schruppen["aufmass"].setText("0,5")
    yield 200
    h.pruefe(
        panel.felder_schruppen["zustellung"].placeholderText() == "1,5",
        f"Vorschlag T2: {panel.felder_schruppen['zustellung'].placeholderText()!r}",
    )
    yield from h.warte_auf(lambda: panel.vorschau is not None, 15000)
    h.bild("2_t2_gewaehlt", panel.form)
    panel.accept()
    yield 1500
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster nach „Übernehmen“ offen")
    labels = [tc.Label for tc in job.Tools.Group]
    h.pruefe(labels == ["T2 Schruppen"], f"Controller: {labels}")
    h.pruefe(op.ToolController is not None and op.ToolController.Label == "T2 Schruppen", "TC")
    h.pruefe(op.Label == "Rundum schruppen T2", f"Name: {op.Label!r}")
    werte = (op.Zustellung.Value, op.VorschubJeUmdrehung.Value, op.Aufmass.Value)
    h.pruefe(werte == (1.5, 3.2, 0.5), f"Werte: {werte}")
    namen = [b.Name for b in op.Path.Commands]
    h.pruefe(op.Lagen > 5 and "G93" in namen, f"Bahn: {op.Lagen} Lagen")
    # T2 ist kleiner: Die Stange ragt 4 mm weniger heraus – ein eigener Schritt davor.
    h.pruefe(
        doc.UndoNames == ["Rundum schruppen ändern", "Stange ändern"] + schritte_vorher,
        f"{doc.UndoNames}",
    )
    h.pruefe(abs(job.Stock.Height.Value - 144.5) < 1e-6, f"Stange mit T2: {job.Stock.Height}")
    tc_t2 = op.ToolController
    schritte_vorher = list(doc.UndoNames)
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("3_bahn_mit_t2")

    # --- Über den Knopf öffnen, ändern, Abbrechen: nichts geändert ---------------------------
    # Gewählt ist der Ordner „Operations“ des Jobs – der Knopf findet „Rundum schruppen“.
    Gui.Selection.addSelection(doc.Name, job.Operations.Name)
    yield 300
    Gui.runCommand("CamAddon_Vierachs")
    yield 1000
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.zu_aendern is op, "Knopf öffnet die Operation nicht")
    if panel is None:
        return
    h.pruefe(panel.fraeser() is not None and panel.fraeser().nummer == 2, "T2 nicht gewählt")
    texte = {k: f.text() for k, f in panel.felder_schruppen.items() if f.text()}
    h.pruefe(texte == {"aufmass": "0,5"}, f"Felder: {texte}")
    panel.felder_schruppen["zustellung"].setText("1")
    yield 200
    panel.reject()
    yield 500
    h.pruefe(op.Zustellung.Value == 1.5, f"Abbrechen ändert: {op.Zustellung}")
    h.pruefe(doc.UndoNames == schritte_vorher, f"Abbrechen: {doc.UndoNames}")

    # --- Nur die Zustellung: derselbe Controller ---------------------------------------------
    op.ViewObject.Proxy.doubleClicked(op.ViewObject)
    yield 1000
    panel = gui_vierachs.VierachsPanel.offen
    if panel is None:
        h.pruefe(False, "zweiter Doppelklick öffnet nichts")
        return
    panel.felder_schruppen["zustellung"].setText("1")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 15000)
    panel.accept()
    yield 1500
    h.pruefe(op.ToolController is tc_t2 and op.Zustellung.Value == 1.0, "neuer Controller")
    h.pruefe([tc.Label for tc in job.Tools.Group] == ["T2 Schruppen"], "Controller danach")

    # --- Schritt 1: Stange Ø 90 statt 80 ------------------------------------------------------
    schritte_vorher = list(doc.UndoNames)
    lagen_vorher = op.Lagen
    op.ViewObject.Proxy.doubleClicked(op.ViewObject)
    yield 1000
    panel = gui_vierachs.VierachsPanel.offen
    if panel is None:
        h.pruefe(False, "dritter Doppelklick öffnet nichts")
        return
    panel.knopf_zurueck.click()
    yield 300
    ok = panel.knopf_anlegen()
    h.pruefe(panel.seite == 1 and ok.text() == "Weiter", f"Schritt 1: {panel.seite}, {ok.text()}")
    felder = (
        panel.feld_stange.text(),
        *(panel.felder_laenge[k].text() for k in ("planaufmass", "abstechbreite", "spannlaenge")),
        panel.feld_drehlage.text(),
    )
    h.pruefe(felder == ("80", "1", "3", "30", ""), f"Schritt 1 wie im Job: {felder}")
    # Die Länge zählt den Platz für T2 hinter dem Teil mit (Überlauf 3,5 + 4 + 5).
    h.pruefe("143,5" in panel.laenge_text.text(), f"Länge: {panel.laenge_text.text()!r}")
    h.pruefe(
        panel.buchstabe() == "A" and panel.wahl_achse.count() == 3,
        f"Rundachse {panel.buchstabe()}, {panel.wahl_achse.count()} Einträge",
    )
    h.pruefe(panel.knopf_mitte_flaeche.isChecked(), "Mitte der Fläche nicht gewählt")
    h.pruefe("Passt" in panel.urteil.text(), f"Urteil: {panel.urteil.text()!r}")
    h.bild("4_schritt1_wie_im_job", panel.form)
    panel.feld_stange.setText("90")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield 300
    h.pruefe(abs(job.Stock.Radius.Value - 45) < 1e-9, f"Stange: {job.Stock.Radius}")
    panel.accept()  # Weiter
    yield 300
    h.pruefe(panel.seite == 2 and ok.text() == "Übernehmen", f"nach Weiter: {ok.text()}")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 15000)
    panel.accept()  # Übernehmen
    yield 1500
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster nach „Übernehmen“ offen")
    neu = ["Rundum schruppen ändern", "Stange ändern"]
    h.pruefe(doc.UndoNames == neu + schritte_vorher, f"Schritte: {doc.UndoNames}")
    h.pruefe(op.Lagen > lagen_vorher, f"Lagen: {op.Lagen} nach {lagen_vorher}")
    ansicht = job.Stock.ViewObject
    h.pruefe(ansicht.Selectable and ansicht.DisplayMode == "Wireframe", "Stange sieht anders aus")

    # Ø 100 und „Abbrechen“: Die Stange bleibt Ø 90.
    op.ViewObject.Proxy.doubleClicked(op.ViewObject)
    yield 1000
    panel = gui_vierachs.VierachsPanel.offen
    if panel is None:
        h.pruefe(False, "vierter Doppelklick öffnet nichts")
        return
    panel.zeige_seite(1)
    panel.feld_stange.setText("100")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield 300
    h.pruefe(abs(job.Stock.Radius.Value - 50) < 1e-9, f"Ø 100 nicht gezeigt: {job.Stock.Radius}")
    panel.reject()
    yield 500
    doc.recompute()
    h.pruefe(abs(job.Stock.Radius.Value - 45) < 1e-9, f"nach Abbrechen: {job.Stock.Radius}")
    h.pruefe(doc.UndoNames == neu + schritte_vorher, f"Abbrechen: {doc.UndoNames}")

    # --- Fünfmal Strg+Z: wieder T1 und Ø 80 --------------------------------------------------
    for _ in range(5):
        doc.undo()
    doc.recompute()
    yield 500
    tc = op.ToolController
    h.pruefe(tc is not None and tc.Label == "T1 Schruppen", f"nach Strg+Z: {tc and tc.Label}")
    h.pruefe(op.Label == "Rundum schruppen T1" and op.Zustellung.Value == 2.0, f"{op.Label}")
    h.pruefe(abs(job.Stock.Radius.Value - 40) < 1e-9, f"Stange nach Strg+Z: {job.Stock.Radius}")
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
