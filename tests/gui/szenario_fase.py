# „Bearbeitung (Fräsen)“ an gezeichneten Fasen: Platte 70 × 40 × 10 mit einem Zapfen 20 × 20 × 10
# bei (10…30, 10…30), oben rundum eine Fase 1 × 45° gezeichnet. T1 der Standardfräser Ø 12, T3 ein
# Fasenfräser Ø 10 mit 90°. Die Oberseite des Zapfens anklicken: Entgraten mit T3 bekommt von
# selbst den Haken (das Modell hat die Fase) – „→ 1 Kantenzug, etwa … – die Fase wie gezeichnet:
# 1 mm breit“. Ein Fasenfräser mit 60° gewählt: rot „braucht einen Fasenfräser mit 90°“.
# „Anlegen“: unter den Operationen „Entgraten T3“ mit Endtiefe 18,5 (Fase 1 + 0,5 tiefer). „Auf
# der Maschine prüfen“: am Ende nirgends ins Teil.
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
    from camaddon import entgraten as eg
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()

    def fasenfraeser(nummer, winkel):
        w = wz.Werkzeug(
            nummer=nummer,
            name=f"Fase {winkel:g}",
            art=wz.FASENFRAESER,
            durchmesser=10.0,
            schneiden=2,
            schneidenlaenge=5.0,
            spitzenwinkel=winkel,
            spitzen_d=0.0,
            schneidstoff=wz.VHM,
        )
        w.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=100.0, fz=0.05)]
        return w

    wz.Bibliothek([t1, fasenfraeser(3, 90.0), fasenfraeser(4, 60.0)]).speichern()

    doc = FreeCAD.newDocument("Fase")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    form = Part.makeBox(70, 40, 10).fuse(Part.makeBox(20, 20, 10, V(10, 10, 10))).removeSplitter()
    oben = [
        k
        for k in form.Edges
        if abs(k.BoundBox.ZMin - 20) < 1e-6 and abs(k.BoundBox.ZMax - 20) < 1e-6
    ]
    teil.Shape = form.makeChamfer(1.0, oben)
    doc.recompute()
    deckel = next(
        (
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if abs(f.BoundBox.ZMin - 20) < 1e-6 and abs(f.BoundBox.ZMax - 20) < 1e-6
        ),
        None,
    )
    if deckel is None:
        h.pruefe(False, "keine Oberseite am Zapfen")
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, deckel)
    yield 500

    # Die Koordinaten dieses Szenarios gelten im Modell – nicht an der Mitte oben, die neue
    # Vorgabe (P-2026-10-02-49).
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    entgraten = panel.entgraten
    yield from h.warte_auf(lambda: entgraten.vorschau is not None, 120000)
    yield 1000
    h.pruefe(entgraten.aktiv(), "Entgraten ohne Haken – die Fase ist gezeichnet")
    h.pruefe(entgraten.fraeser() is not None and entgraten.fraeser().nummer == 3, "nicht T3")
    text = entgraten.ergebnis.text()
    h.pruefe(
        text.startswith("→ 1 Kantenzug, etwa ")
        and text.endswith(" – die Fase wie gezeichnet: 1 mm breit"),
        f"Entgraten: {text!r}",
    )
    h.pruefe(not entgraten.hinweis.text(), f"rot: {entgraten.hinweis.text()!r}")
    h.bild("1_fase", panel.form)

    # Der 60°-Fräser passt nicht zur 45°-Fase.
    entgraten.wahl_fraeser.setCurrentIndex(1)
    yield from h.warte_auf(lambda: bool(entgraten.hinweis.text()), 60000)
    rot = entgraten.hinweis.text()
    h.pruefe("braucht einen Fasenfräser mit 90°" in rot, f"60°: {rot!r}")
    entgraten.wahl_fraeser.setCurrentIndex(0)
    yield from h.warte_auf(lambda: entgraten.vorschau is not None, 120000)
    yield 500

    # --- Anlegen ----------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 2500
    ops = list(job.Operations.Group)
    fasen = [o for o in ops if eg.ist_entgraten(o)]
    h.pruefe(
        len(fasen) == 1 and fasen[0].Label == "Entgraten T3",
        f"Operationen: {[o.Label for o in ops]}",
    )
    if not fasen:
        return
    h.pruefe(abs(float(fasen[0].FinalDepth) - 18.5) < 1e-6, f"Endtiefe {fasen[0].FinalDepth}")
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
    yield from h.warte_auf(lambda: spieler.rest.text().startswith("Am Ende"), 240000)
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
