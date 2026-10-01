# „Bearbeitung (Fräsen)“ mit „Gewinde bohren“ (W-006 S3g): Block 100 × 60 × 20 mit einem
# durchgehenden Kernloch Ø 8,5 bei (25, 30); T1 der Standardfräser Ø 12, T2 ein Bohrer Ø 8,5, T3
# ein Gewindebohrer M10 × 1,5. Die Wand des Kernlochs anklicken: Bohren mit T2 bekommt den Haken;
# Bohrung fräsen und Kontur gehen nicht (der Fräser Ø 12 passt nicht hinein) – sie verlieren ihren
# Haken, sonst ginge „Anlegen“ nicht. Gewinde bohren ist möglich (T3 – sein Kernloch hat die
# Bohrung), den Haken setzt man selbst: „→ 1 × M10x1.5, etwa 1 min“. „Anlegen“: „Bohren T2“, dann
# „Gewinde M10x1.5 T3“ (G81, G84). „Auf der Maschine prüfen“: am Ende nirgends ins Teil – das
# Gewinde zählt mit seinem Kernloch.
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
    from camaddon import bohren as bh
    from camaddon import bohrung_bahn as bb
    from camaddon import gewinde as gw
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    t2 = wz.Werkzeug(
        nummer=2,
        name="HSS 8.5",
        art=wz.BOHRER,
        durchmesser=8.5,
        schneiden=2,
        schneidenlaenge=60.0,
        spitzenwinkel=118.0,
        schneidstoff=wz.HSS,
    )
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.08)]
    t3 = wz.Werkzeug(
        nummer=3,
        name="M10",
        art=wz.GEWINDEBOHRER_RECHTS,
        durchmesser=10.0,
        steigung=1.5,
        schneiden=3,
        schneidenlaenge=20.0,
        schneidstoff=wz.HSS,
    )
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.GEWINDEBOHREN, vc=8.0)]
    wz.Bibliothek([t1, t2, t3]).speichern()

    doc = FreeCAD.newDocument("Gewinde")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeBox(100, 60, 20).cut(Part.makeCylinder(4.25, 20, V(25, 30, 0)))
    doc.recompute()
    kern = next((b.name for b in bb.bohrungen(teil.Shape)), None)
    if kern is None:
        h.pruefe(False, "keine Bohrung")
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, kern)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    bohren, bohrung, kontur, gewinde = panel.bohren, panel.bohrung, panel.kontur, panel.gewinde
    h.pruefe(bohren.fraeser() is not None and bohren.fraeser().nummer == 2, "Bohren: nicht T2")
    h.pruefe(gewinde.fraeser() is not None and gewinde.fraeser().nummer == 3, "Gewinde: nicht T3")
    yield from h.warte_auf(lambda: bohren.vorschau is not None, 60000)
    yield 1500
    h.pruefe(bohren.aktiv(), "Bohren ohne Haken")
    h.pruefe(
        not bohrung.aktiv() and bool(bohrung.hinweis.text()),
        f"Bohrung fräsen: Haken {bohrung.aktiv()}, {bohrung.hinweis.text()!r}",
    )
    h.pruefe(not kontur.aktiv(), "Kontur mit Haken")
    h.pruefe(gewinde.moeglich and not gewinde.aktiv(), "Gewinde: von selbst angehakt")
    gewinde.haken.setChecked(True)  # wie ein Klick: der Haken von Hand
    yield from h.warte_auf(lambda: gewinde.vorschau is not None, 60000)
    yield 300
    text = gewinde.ergebnis.text()
    h.pruefe(text.startswith("→ 1 × M10x1.5, etwa "), f"Gewinde: {text!r}")
    h.pruefe(not gewinde.hinweis.text(), f"Gewinde rot: {gewinde.hinweis.text()!r}")
    h.bild("1_gewinde", panel.form)

    # --- Anlegen: Bohren, dann Gewinde ------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 2000
    ops = list(job.Operations.Group)
    h.pruefe(
        len(ops) == 2 and bh.ist_bohren(ops[0]) and gw.ist_gewinde(ops[1]),
        f"Operationen: {[o.Label for o in ops]}",
    )
    if len(ops) < 2:
        return
    h.pruefe(
        (ops[0].Label, ops[1].Label) == ("Bohren T2", "Gewinde M10x1.5 T3"),
        f"Namen: {[o.Label for o in ops]}",
    )
    namen = [[c.Name for c in o.Path.Commands if c.Name in ("G81", "G83", "G84")] for o in ops]
    h.pruefe(namen == [["G81"], ["G84"]], f"Zyklen: {namen}")
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
