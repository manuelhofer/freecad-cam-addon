# „Bearbeitung (Fräsen)“ mit „3D-Schlichten“ (W-006 4.2 Punkt 3): Platte 60 × 60 × 10 mit einer
# Kuppel (Kugel R 25, Fuß Ø 40, oben z 20); T1 der Standardfräser Ø 12, T3 ein Kugelfräser Ø 6.
# Die Kuppel anklicken: In der Liste „Freiform, unten 10“, „3D-Schlichten“ angehakt mit T3 (der
# Kugelfräser ist vorgewählt), „→ N Höhenlinien und M Zeilen längs X, Abstand 0,49, etwa … min“
# (Steil/Flach: am Fuß ist die Kuppel steiler als 45°); Planfräsen und Räumen ohne Haken. „Anlegen“: „3D-Schlichten T3“. „Auf der Maschine prüfen“: am Ende nirgends
# ins Teil.
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

    from camaddon import beispielmaschine, gui_bearbeitung, gui_reichweite
    from camaddon import schlichten3d as s3op
    from camaddon import werkzeuge as wz

    t3 = wz.Werkzeug(
        nummer=3,
        name="Kugel 6",
        art=wz.KUGELFRAESER,
        durchmesser=6.0,
        schneiden=2,
        schneidenlaenge=12.0,
        schneidstoff=wz.VHM,
    )
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
    wz.Bibliothek([wz.standardwerkzeug(), t3]).speichern()

    doc = FreeCAD.newDocument("Kuppel")
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
    block = panel.schlichten3d
    yield from h.warte_auf(lambda: block.vorschau is not None, 180000)
    yield 800
    liste = panel.flaechen_liste.item(0).text() if panel.flaechen_liste.count() else ""
    h.pruefe(liste.endswith("Freiform, unten 10"), f"Liste: {liste!r}")
    h.pruefe(block.aktiv(), "3D-Schlichten ohne Haken")
    h.pruefe(block.fraeser() is not None and block.fraeser().nummer == 3, "nicht T3")
    h.pruefe(not panel.plan.aktiv() and not panel.raeumen.aktiv(), "Planfräsen/Räumen angehakt")
    text = block.ergebnis.text()
    h.pruefe(
        text.startswith("→ ")
        and " Höhenlinien und " in text
        and " Zeilen längs " in text
        and ", Abstand 0,49, etwa " in text,
        f"3D-Schlichten: {text!r}",
    )
    h.pruefe(not block.hinweis.text(), f"rot: {block.hinweis.text()!r}")
    h.bild("1_kuppel", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = list(job.Operations.Group)
    h.pruefe(
        len(ops) == 1 and s3op.ist_schlichten3d(ops[0]) and ops[0].Label == "3D-Schlichten T3",
        f"Operationen: {[o.Label for o in ops]}",
    )
    if ops:
        h.pruefe(ops[0].Zeilen > 50, f"Zeilen: {ops[0].Zeilen}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_angelegt")

    # --- Auf der Maschine prüfen ------------------------------------------------------------
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 500
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
    spieler = pruef.abspieler
    fahrt = spieler.abfahrt
    spieler.setze_zeit(fahrt.dauer)
    yield from h.warte_auf(lambda: spieler.rest.text().startswith("Am Ende"), 300000)
    rest = spieler.rest.text()
    h.pruefe(rest.startswith("Am Ende bleiben") and "nirgends ins Teil" in rest, f"{rest!r}")
    Gui.SendMsgToActiveView("ViewFit")
    spieler.knopf_hinsehen.click()
    yield 800
    h.bild("3_pruefen_farben")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
