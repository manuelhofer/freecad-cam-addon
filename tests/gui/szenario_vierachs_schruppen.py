# „4-Achs-Bearbeitung“ mit „Rundum schruppen“ (W-003 Stufe V3d, Manuels Wunsch
# 2026-09-27: „was willste machen .. schruppen“). Die Beispiel-Drehmaschine ist
# offen, in der Werkzeugverwaltung steht ein Schaftfräser T1 Ø 12 mit dem Einsatz
# „Schruppen“ (ae 4,8, ap 2). Welle Ø 60, Stirnfläche angeklickt, Stange Ø 80:
# Unten heißt der Knopf „Weiter“. Danach Schritt 2 „Was willst du machen?“ –
# „Rundum schruppen“ angehakt, T1 und „Schruppen“ vorgewählt, grau „→ 5 Lagen
# (Ø 80,0 mm → Ø 60,…)“; der Knopf heißt „Anlegen“. „Anlegen“: Im Job stehen der
# Controller „T1 Schruppen“ (FreeCADs Vorgabe-Controller ist weg) und „Rundum
# schruppen T1“ mit fünf Lagen und G93. Das erste Strg+Z nimmt Controller und
# Operation zurück, das zweite Job und Stange.
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

    from camaddon import beispielmaschine, gui_vierachs
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    fraeser = wz.Werkzeug(nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26)
    fraeser.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=150, fz=0.08)]
    wz.Bibliothek([fraeser]).speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300

    doc = FreeCAD.newDocument("Welle")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Welle")
    teil.Shape = Part.makeCylinder(30, 100, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0))
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f) and (vr.aussennormale(f) - FreeCAD.Vector(1, 0, 0)).Length < 1e-9
    )
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.feld_stange.setText("80")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    ok = panel.knopf_anlegen()
    h.pruefe(ok is not None and ok.text() == "Weiter", f"Knopf in Schritt 1: {ok and ok.text()!r}")
    h.pruefe(panel.buchstabe() == "C", f"Rundachse {panel.buchstabe()}")

    # --- Weiter: Schritt 2 ------------------------------------------------------------
    h.pruefe(panel.accept() is False, "„Weiter“ schließt das Fenster")
    yield 300
    h.pruefe(panel.seite == 2 and panel.seiten.currentIndex() == 1, f"Seite {panel.seite}")
    h.pruefe("Schritt 2" in panel._kopf_text.text(), f"Kopf: {panel._kopf_text.text()!r}")
    h.pruefe(ok.text() == "Anlegen", f"Knopf in Schritt 2: {ok.text()!r}")
    h.pruefe(panel.mit_schruppen.isChecked(), "„Rundum schruppen“ nicht angehakt")
    h.pruefe(panel.fraeser() is not None and panel.fraeser().nummer == 1, "T1 nicht gewählt")
    h.pruefe(panel.einsatz() is not None and panel.einsatz().art == wz.SCHRUPPEN, "Schruppen fehlt")
    h.pruefe(
        panel.felder_schruppen["zustellung"].placeholderText() == "2"
        and panel.felder_schruppen["steigung"].placeholderText() == "4,8",
        "Vorschläge: "
        + ", ".join(f"{k}={f.placeholderText()!r}" for k, f in panel.felder_schruppen.items()),
    )
    yield from h.warte_auf(lambda: panel.vorschau is not None, 15000)
    ergebnis = panel.ergebnis.text()
    h.pruefe(ergebnis.startswith("→ 5 Lagen (Ø 80,0 mm → Ø 60,"), f"Vorschau: {ergebnis!r}")
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"Hinweis: {panel.hinweis_bearbeitung.text()!r}")
    h.pruefe(ok.isEnabled(), "„Anlegen“ gesperrt")
    h.pruefe(not panel.radius_hinweis.isHidden(), "Hinweis „X ist der Radius“ fehlt")
    h.bild("1_was_willst_du_machen", panel.form)

    # Zurück und wieder vor: Die Wahl bleibt.
    panel.zeige_seite(1)
    yield 200
    h.pruefe(ok.text() == "Weiter" and panel.seite == 1, "Zurück geht nicht")
    panel.zeige_seite(2)
    yield 200
    h.pruefe(panel.fraeser() is not None and panel.fraeser().nummer == 1, "T1 nach Zurück weg")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 15000)

    # --- Anlegen -------------------------------------------------------------------------
    job = panel.job
    panel.accept()
    yield 1500
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster noch offen")
    controller = job.Tools.Group
    h.pruefe(
        [tc.Label for tc in controller] == ["T1 Schruppen"],
        f"Controller: {[tc.Label for tc in controller]}",
    )
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    h.pruefe(len(ops) == 1, f"Operationen: {[o.Label for o in job.Operations.Group]}")
    if ops:
        op = ops[0]
        namen = [b.Name for b in op.Path.Commands]
        h.pruefe(op.Label == "Rundum schruppen T1", f"Name: {op.Label!r}")
        h.pruefe(op.Lagen == 5 and "G93" in namen and namen[-1] == "G94", f"Bahn: {op.Lagen}")
        h.pruefe(op.ToolController is controller[0], "Operation ohne den neuen Controller")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("2_bahn_um_die_welle")

    # Zwei Schritte Rückgängig: zuerst Controller und Operation, dann Job und Stange.
    h.pruefe(
        doc.UndoNames == ["Rundum schruppen anlegen", "4-Achs-Bearbeitung"],
        f"Rückgängig-Schritte: {doc.UndoNames}",
    )
    doc.undo()
    doc.recompute()
    yield 300
    h.pruefe(
        not [o for o in doc.Objects if vo.ist_rundum(o)]
        and [tc.Label for tc in job.Tools.Group] != ["T1 Schruppen"],
        f"nach einem Strg+Z: {[tc.Label for tc in job.Tools.Group]}",
    )
    doc.undo()
    doc.recompute()
    yield 300
    uebrig = [o.Name for o in doc.Objects if o.Name != teil.Name]
    h.pruefe(not uebrig, f"nach zwei Strg+Z noch da: {uebrig}")
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
