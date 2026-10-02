# Querbohrungen auf der Drehmaschine mit C und Y (P-2026-10-02-07): Welle Ø 30 × 80 längs X,
# oben eine Sackbohrung Ø 10, 8 tief, weiter hinten eine durchgehende Ø 8 quer; die
# Beispiel-Drehmaschine ist offen, T1 ein Schaftfräser Ø 6 (Einsätze „Planen“ und „Schruppen“) im
# Halter „VDI30 angetrieben radial“. Die Stirnfläche angeklickt, Stange Ø 32, „Weiter“; „Rundum
# schruppen“ und „Rundum schlichten“ aus. Ein Klick auf beide Bohrungen: „Plan indexiert“ geht an
# mit „Vorschlag: an – quer zur Stange gebohrt: …“, die Vorschau sagt „– davon 2 als Bohrung quer
# zur Stange …“ (die durchgehende von beiden Seiten). „Anlegen“: „Plan indexiert T1“. „Auf der
# Maschine prüfen“: „Alle Achsen bleiben in ihren Grenzen.“, am Ende „nirgends ins Teil“.
import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtCore

V = FreeCAD.Vector


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_reichweite, gui_vierachs
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_plan as vplan
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(nummer=1, durchmesser=6, schneiden=3, schneidenlaenge=20,
                     laenge_spindelnase=125)  # fmt: skip
    t1.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.PLANEN, ae=3.6, ap=2, vc=150, fz=0.04),
        wz.Einsatz(art=wz.SCHRUPPEN, ae=2.4, ap=2, vc=150, fz=0.04),
    ]
    bibliothek = wz.Bibliothek([t1])
    t1.halter = bibliothek.neuer_halter("vdi30_radial").kennung
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300

    doc = FreeCAD.newDocument("Querbohrung")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Welle")
    welle = Part.makeCylinder(15, 80, V(), V(1, 0, 0))
    welle = welle.cut(Part.makeCylinder(5, 10, V(30, 0, 7)))  # Sackbohrung oben, 8 tief
    welle = welle.cut(Part.makeCylinder(4, 40, V(55, -20, 0), V(0, 1, 0)))  # durchgehend quer
    teil.Shape = welle.removeSplitter()
    doc.recompute()
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
    )
    bohrungen = [
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if isinstance(f.Surface, Part.Cylinder) and f.Surface.Radius < 6.0
    ]
    h.pruefe(len(bohrungen) == 2, f"Bohrungen: {bohrungen}")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.feld_stange.setText("32")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    h.pruefe(panel.buchstabe() == "C", f"Rundachse {panel.buchstabe()}")
    h.pruefe(panel.accept() is False, "„Weiter“ schließt das Fenster")
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    panel.mit_schruppen.setChecked(False)
    panel.mit_schlichten.setChecked(False)
    yield 300

    # --- Die beiden Bohrungen: „Plan indexiert“ als Querbohrung ------------------------------
    job = panel.job
    klon = vr.modell(job)
    for name in bohrungen:
        Gui.Selection.addSelection(doc.Name, klon.Name, name)
    yield 500
    h.pruefe(sorted(panel.flaechen()) == sorted(bohrungen), f"gewählt: {panel.flaechen()}")
    h.pruefe(panel.mit_plan.isChecked(), "„Plan indexiert“ mit den Bohrungen aus")
    grund = panel.plan_grund.text()
    h.pruefe(grund.startswith("Vorschlag: an – quer zur Stange gebohrt: "), f"Grund: {grund!r}")
    h.pruefe(panel.planfraeser() is not None and panel.planfraeser().nummer == 1, "nicht T1")
    yield from h.warte_auf(lambda: panel.vorschau_plan is not None, 60000)
    text = panel.ergebnis_plan.text()
    h.pruefe(
        text.startswith("→ ") and "davon 2 als Bohrung quer zur Stange" in text,
        f"Vorschau: {text!r}",
    )
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    from camaddon.gui_teile import blaettere_zu

    blaettere_zu(panel.mit_plan)
    yield 300
    h.bild("1_querbohrung", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    panel.accept()
    yield 2500
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster noch offen")
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    plan = next((o for o in ops if vplan.ist_plan(o)), None)
    h.pruefe(plan is not None and plan.Label == "Plan indexiert T1", f"Operationen: {ops}")
    if plan is None:
        return
    schnitte = [b for b in plan.Path.Commands if b.Name == "G1"]
    h.pruefe(len(schnitte) > 20, f"{len(schnitte)} Sätze")
    c_werte = {round(b.Parameters.get("C", 0.0), 3) for b in schnitte}
    h.pruefe(len(c_werte) == 3, f"C je Seite fest: {sorted(c_werte)}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("2_angelegt")

    # --- Auf der Maschine prüfen -----------------------------------------------------------
    FreeCAD.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400  # 1.1.3 verarbeitet die Auswahl verzögert
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 120000)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruef is None:
        return
    yield 1000
    h.pruefe(
        pruef.urteil.text() == "Alle Achsen bleiben in ihren Grenzen.",
        f"Urteil: {pruef.urteil.text()!r}",
    )
    spieler = pruef.abspieler
    spieler.setze_zeit(spieler.abfahrt.dauer)
    yield from h.warte_auf(lambda: spieler.rest.text().startswith("Am Ende"), 300000)
    rest = spieler.rest.text()
    h.pruefe(rest.startswith("Am Ende bleiben") and "nirgends ins Teil" in rest, f"{rest!r}")
    Gui.SendMsgToActiveView("ViewFit")
    spieler.knopf_hinsehen.click()
    yield 800
    h.bild("3_am_ende_farben")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
