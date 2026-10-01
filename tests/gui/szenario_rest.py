# „Bearbeitung (Fräsen)“ mit „Restmaterial“ (W-006 4.1 Punkt 5): Block 100 × 60 × 20 mit einer
# Tasche 30 × 20 × 10 mit scharfen Ecken bei (35…65, 20…40); T1 der Standardfräser Ø 12, T3 ein
# Schaftfräser Ø 4 (Schlichten, ap 5). Aufmaß oben 0, die vier Wände der Tasche gewählt: Die
# Kontur mit T1 räumt die Tasche (vorgeschlagen); „Restmaterial“ ist möglich, ohne Haken, T3
# vorgewählt (der größte unter Ø 12), „Fräser davor Ø“ grau „wie bei der Kontur“. Angehakt:
# „→ 4 Stellen, 2 Lagen, etwa …“. „Anlegen“: „Kontur T1“, dann „Restmaterial T3“. „Auf der
# Maschine prüfen“: am Ende nirgends ins Teil.
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
    from camaddon import kontur as ko
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    t3 = wz.Werkzeug(nummer=3, name="VHM 4", durchmesser=4.0, schneiden=3, schneidenlaenge=12.0)
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.2, ap=5.0, vc=120.0, fz=0.02)]
    wz.Bibliothek([t1, t3]).speichern()

    doc = FreeCAD.newDocument("Rest")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    form = Part.makeBox(100, 60, 20).cut(Part.makeBox(30, 20, 10, V(35, 20, 10)))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    waende = [
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if f.BoundBox.ZMax - f.BoundBox.ZMin > 1e-6 and f.BoundBox.ZMin > 9.9
    ]
    if len(waende) != 4:
        h.pruefe(False, f"Wände der Tasche: {waende}")
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, waende[0])
    yield 500

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
    kontur, rest = panel.kontur, panel.rest
    yield from h.warte_auf(lambda: kontur.vorschau is not None, 120000)
    yield 300
    h.pruefe(kontur.aktiv() and kontur.fraeser().nummer == 1, "Kontur: nicht an oder nicht T1")
    h.pruefe(rest.moeglich and not rest.aktiv(), "Restmaterial: nicht möglich oder an")
    h.pruefe(rest.fraeser() is not None and rest.fraeser().nummer == 3, "Restmaterial: nicht T3")
    davor = rest.felder["davor"]
    h.pruefe(
        not davor.text() and davor.placeholderText() == "wie bei der Kontur",
        f"Fräser davor: {davor.text()!r} / {davor.placeholderText()!r}",
    )
    rest.haken.setChecked(True)
    yield from h.warte_auf(lambda: rest.vorschau is not None, 60000)
    yield 300
    h.pruefe(not rest.hinweis.text(), f"rot: {rest.hinweis.text()!r}")
    text = rest.ergebnis.text()
    h.pruefe(text.startswith("→ 4 Stellen, 2 Lagen, etwa "), f"Restmaterial: {text!r}")
    h.bild("1_restmaterial", panel.form)

    # --- Anlegen: „Kontur T1“, dann „Restmaterial T3“ ----------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = list(job.Operations.Group)
    h.pruefe(
        [o.Label for o in ops] == ["Kontur T1", "Restmaterial T3"]
        and not ko.ist_rest(ops[0])
        and ko.ist_rest(ops[1]),
        f"Operationen: {[o.Label for o in ops]}",
    )
    if len(ops) < 2:
        return
    h.pruefe(abs(float(ops[1].RadiusDavor) - 6.0) < 1e-9, f"Radius davor {ops[1].RadiusDavor}")
    h.pruefe((ops[1].Lagen, ops[1].Bahnen) == (2, 8), f"{ops[1].Lagen} Lagen, {ops[1].Bahnen}")
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
    rest_text = spieler.rest.text()
    h.pruefe(
        rest_text.startswith("Am Ende bleiben") and "nirgends ins Teil" in rest_text,
        f"{rest_text!r}",
    )
    Gui.SendMsgToActiveView("ViewFit")
    spieler.knopf_hinsehen.click()
    yield 800
    h.bild("3_pruefen_farben")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
