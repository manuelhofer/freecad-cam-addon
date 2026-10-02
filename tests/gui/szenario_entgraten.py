# „Bearbeitung (Fräsen)“ mit „Entgraten“ (W-006 4.1 Punkt 8): Block 100 × 60 × 20 mit einer Tasche
# 30 × 20 × 5 bei (35…65, 20…40); T1 der Standardfräser Ø 12, T3 ein 90°-Fasenfräser Ø 10. Aufmaß
# oben 0 (die Oberkante ist fertig), die vier Wände der Tasche gewählt: Die Kontur räumt die Tasche
# (vorgeschlagen), Entgraten ist möglich, den Haken setzt man selbst – „→ 1 Kantenzug, etwa …“.
# „Anlegen“: „Kontur T1“, dann „Entgraten T3“ (Endtiefe 19,2: Fase 0,3 und die Spitze 0,5
# tiefer). „Auf der Maschine prüfen“: am Ende nirgends ins Teil – die Fase darf an der Kante ins
# Teil, so tief wie die Spitze.
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
    from camaddon import kontur as ko
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    t3 = wz.Werkzeug(
        nummer=3,
        name="Fase 90",
        art=wz.FASENFRAESER,
        durchmesser=10.0,
        schneiden=2,
        schneidenlaenge=5.0,
        spitzenwinkel=90.0,
        spitzen_d=0.0,
        schneidstoff=wz.VHM,
    )
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=100.0, fz=0.05)]
    wz.Bibliothek([t1, t3]).speichern()

    doc = FreeCAD.newDocument("Entgraten")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    form = Part.makeBox(100, 60, 20).cut(Part.makeBox(30, 20, 5, V(35, 20, 15)))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    waende = [
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if f.BoundBox.ZMax - f.BoundBox.ZMin > 1e-6 and f.BoundBox.ZMin > 14.9
    ]
    if len(waende) != 4:
        h.pruefe(False, f"Wände der Tasche: {waende}")
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, waende[0])
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
    for name in waende[1:]:
        panel.flaeche_umschalten(name)
    panel.felder_rohteil["oben"].setText("0")
    yield from h.warte_auf(lambda: not panel._rohteil_uhr.isActive(), 3000)
    kontur, entgraten = panel.kontur, panel.entgraten
    yield from h.warte_auf(lambda: kontur.vorschau is not None, 120000)
    yield 300
    h.pruefe(abs(job.Stock.Shape.BoundBox.ZMax - 20.0) < 1e-6, "Aufmaß oben nicht 0")
    h.pruefe(kontur.aktiv(), "Kontur ohne Haken")
    h.pruefe(entgraten.moeglich and not entgraten.aktiv(), "Entgraten: nicht möglich oder an")
    h.pruefe(
        entgraten.fraeser() is not None and entgraten.fraeser().nummer == 3,
        "Entgraten: nicht T3",
    )
    entgraten.haken.setChecked(True)
    yield from h.warte_auf(lambda: entgraten.vorschau is not None, 60000)
    yield 300
    h.pruefe(not entgraten.hinweis.text(), f"rot: {entgraten.hinweis.text()!r}")
    text = entgraten.ergebnis.text()
    h.pruefe(text.startswith("→ 1 Kantenzug, etwa "), f"Entgraten: {text!r}")
    h.bild("1_entgraten", panel.form)

    # --- Anlegen: „Kontur T1“, dann „Entgraten T3“ ------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = list(job.Operations.Group)
    h.pruefe(
        [o.Label for o in ops] == ["Kontur T1", "Entgraten T3"]
        and ko.ist_kontur(ops[0])
        and eg.ist_entgraten(ops[1]),
        f"Operationen: {[o.Label for o in ops]}",
    )
    if len(ops) < 2:
        return
    op = ops[1]
    h.pruefe(abs(float(op.FinalDepth) - 19.2) < 1e-6, f"Endtiefe {op.FinalDepth}")
    h.pruefe(op.Ketten == 1 and op.Ausgelassen == 0, f"Ketten {op.Ketten}/{op.Ausgelassen}")
    boegen = [c for c in op.Path.Commands if c.Name in ("G2", "G3")]
    h.pruefe(len(boegen) >= 2, f"{len(boegen)} Bögen")
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
