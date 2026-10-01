# „Bearbeitung (Fräsen)“ mit „Reiben“ (W-006 4.1 Punkt 7): Block 60 × 40 × 20 mit einer
# durchgehenden Bohrung Ø 10 bei (20, 20); T1 der Standardfräser Ø 12, T2 ein Bohrer Ø 10, T3 ein
# Bohrer Ø 9,8, T4 eine Reibahle Ø 10. Die Wand anklicken: Bohren mit T2 (ihr Durchmesser), Reiben
# ohne Haken, die Reibahle T4 vorgewählt. Reiben anhaken: Bohren nimmt T3 (0,2 kleiner – die
# Reibzugabe), Bohrung fräsen tritt nicht an und sagt warum, Reiben: „→ 1 Bohrung, etwa …“.
# „Anlegen“: „Bohren T3“ (G81) und „Reiben T4“ (G85, bis 1 mm unter den Grund), in dieser
# Reihenfolge. „Auf der Maschine prüfen“: am Ende nirgends ins Teil.
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
    from camaddon import reiben as rbn
    from camaddon import werkzeuge as wz

    def bohrer(nummer, d):
        w = wz.Werkzeug(
            nummer=nummer,
            name=f"HSS {d:g}",
            art=wz.BOHRER,
            durchmesser=d,
            schneiden=2,
            schneidenlaenge=60.0,
            spitzenwinkel=118.0,
            schneidstoff=wz.HSS,
        )
        w.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.1)]
        return w

    t4 = wz.Werkzeug(
        nummer=4,
        name="Reibahle 10",
        art=wz.REIBAHLE,
        durchmesser=10.0,
        schneiden=6,
        schneidenlaenge=30.0,
        schneidstoff=wz.VHM,
    )
    t4.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.REIBEN, vc=20.0, fz=0.05)]
    wz.Bibliothek([wz.standardwerkzeug(), bohrer(2, 10.0), bohrer(3, 9.8), t4]).speichern()

    doc = FreeCAD.newDocument("Reiben")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeBox(60, 40, 20).cut(Part.makeCylinder(5, 20, V(20, 20, 0)))
    doc.recompute()
    liste = bb.bohrungen(teil.Shape)
    if len(liste) != 1:
        h.pruefe(False, f"Bohrungen: {liste}")
        return
    wand = liste[0].name
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, wand)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    bohren, bohrung, reiben = panel.bohren, panel.bohrung, panel.reiben
    yield from h.warte_auf(lambda: bohren.vorschau is not None, 60000)
    yield 500
    h.pruefe(bohren.fraeser() is not None and bohren.fraeser().nummer == 2, "Bohren: nicht T2")
    h.pruefe(reiben.moeglich and not reiben.aktiv(), "Reiben: nicht möglich oder angehakt")
    h.pruefe(reiben.fraeser() is not None and reiben.fraeser().nummer == 4, "Reiben: nicht T4")

    # --- Reiben anhaken: kleiner vorbohren ------------------------------------------------------
    reiben.haken.setChecked(True)
    yield from h.warte_auf(
        lambda: reiben.vorschau is not None and bohren.vorschau is not None, 60000
    )
    yield 800
    h.pruefe(bohren.fraeser() is not None and bohren.fraeser().nummer == 3, "Vorbohren: nicht T3")
    h.pruefe(bohren.aktiv() and not bohren.hinweis.text(), f"Bohren: {bohren.hinweis.text()!r}")
    zeile = bohren.ergebnis.text()
    h.pruefe(zeile.endswith("– vorgebohrt fürs Reiben, mit Ø 9,8"), f"Bohren: {zeile!r}")
    h.pruefe(not bohrung.moeglich and not bohrung.aktiv(), "Bohrung fräsen tritt an")
    h.pruefe("gerieben" in bohrung.erklaerung.text(), f"{bohrung.erklaerung.text()!r}")
    text = reiben.ergebnis.text()
    h.pruefe(text.startswith("→ 1 Bohrung, etwa "), f"Reiben: {text!r}")
    h.pruefe(not reiben.hinweis.text(), f"rot: {reiben.hinweis.text()!r}")
    h.bild("1_reiben", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 2500
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    h.pruefe(namen == ["Bohren T3", "Reiben T4"], f"Operationen: {namen}")
    gerieben = [o for o in ops if rbn.ist_reiben(o)]
    gebohrt = [o for o in ops if bh.ist_bohren(o) and not rbn.ist_reiben(o)]
    if gerieben and gebohrt:
        zyklen = [c.Name for c in gerieben[0].Path.Commands if c.Name.startswith("G8")]
        h.pruefe("G85" in zyklen, f"Reiben: {zyklen}")
        h.pruefe(abs(float(gerieben[0].FinalDepth) + 1.0) < 1e-6, f"{gerieben[0].FinalDepth}")
        zyklen = [c.Name for c in gebohrt[0].Path.Commands if c.Name.startswith("G8")]
        h.pruefe("G81" in zyklen and "G85" not in zyklen, f"Bohren: {zyklen}")
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
