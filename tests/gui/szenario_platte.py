# „Bearbeitung (Fräsen)“ an Manuels Platte (Spezifikation Strategien, Abschnitt 11): 200 × 200,
# Zapfen Ø 20 × 20 bei (50, 50), Tasche Ø 45, 20 tief bei (−50, −50); T1 der Standardfräser Ø 12.
# Die Oberseite (z = 0) und die Wand der Tasche anklicken: Das Planfräsen könnte die Oberseite,
# das Räumen die Oberseite und den Taschenboden, die Kontur die Taschenwand. Der Assistent rechnet
# die Folgen (Grundsatz 0): Räumen über alles gegen Planfräsen plus Räumen nur des Bodens –
# Räumen über alles ist schneller, behält den Haken, das Planfräsen verliert ihn; beide Zeilen
# sagen, um wie viel. Die Kontur schlichtet nur noch das Aufmaß („Breite“ = Aufmaß des Räumens).
# „Anlegen“: „Räumen T1“ über beide Flächen und „Kontur T1“ mit Breite 0,3. „Auf der Maschine
# prüfen“: am Ende nirgends ins Teil.
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
    from camaddon import hoehenfeld as hf
    from camaddon import kontur as ko
    from camaddon import kontur_bahn as kb
    from camaddon import raeumen as ra
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    wz.Bibliothek([t1]).speichern()

    doc = FreeCAD.newDocument("Platte")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    platte = Part.makeBox(200, 200, 30, V(-100, -100, -30))
    zapfen = Part.makeCylinder(10, 20, V(50, 50, 0))
    tasche = Part.makeCylinder(22.5, 20, V(-50, -50, -20))
    teil.Shape = platte.fuse(zapfen).cut(tasche).removeSplitter()
    doc.recompute()
    oben = next(e.name for e in hf.ebenen_oben(teil.Shape) if abs(e.z) < 1e-6)
    alle = [f"Face{i + 1}" for i in range(len(teil.Shape.Faces))]
    wand = next(w.name for w in kb.waende(teil.Shape, alle) if abs(w.z_unten + 20.0) < 1e-6)
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, oben)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    panel.flaeche_umschalten(wand)
    h.pruefe(sorted(panel.flaechen()) == sorted([oben, wand]), f"Flächen: {panel.flaechen()}")
    plan, raeumen, kontur = panel.plan, panel.raeumen, panel.kontur
    yield from h.warte_auf(
        lambda: raeumen.vorschau is not None and kontur.vorschau is not None, 120000
    )
    yield 500
    h.pruefe(not raeumen.hinweis.text(), f"rot: {raeumen.hinweis.text()!r}")
    h.pruefe(raeumen.aktiv() and not plan.aktiv(), "Haken: Räumen an, Planfräsen aus")
    h.pruefe(kontur.aktiv(), "Haken: Kontur aus")
    # Die Tasche ist eine runde Sackbohrung – aber ihren Boden räumt das Räumen, die Kontur fährt
    # nur das Aufmaß: „Bohrung fräsen“ tritt dort nicht an.
    h.pruefe(not panel.bohrung.aktiv(), "Haken: Bohrung fräsen an")
    h.pruefe(
        not panel.bohrung.ergebnis.text(), f"Bohrung fräsen: {panel.bohrung.ergebnis.text()!r}"
    )
    text = raeumen.ergebnis.text()
    h.pruefe(text.startswith("→ 2 Flächen: 2 Lagen,"), f"Räumen: {text!r}")
    h.pruefe("über alles die schnellste Folge" in text, f"Räumen: {text!r}")
    text_plan = plan.ergebnis.text()
    h.pruefe("langsamer als Räumen über alles" in text_plan, f"Planfräsen: {text_plan!r}")
    text_kontur = kontur.ergebnis.text()
    h.pruefe("nur das Aufmaß an den Wänden" in text_kontur, f"Kontur: {text_kontur!r}")
    h.bild("1_platte", panel.form)

    # --- Anlegen: „Räumen T1“ und „Kontur T1“ ----------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = list(job.Operations.Group)
    h.pruefe(
        len(ops) == 2 and ra.ist_raeumen(ops[0]) and ko.ist_kontur(ops[1]),
        f"Operationen: {[o.Label for o in ops]}",
    )
    if len(ops) < 2:
        return
    raeumen_op, kontur_op = ops
    h.pruefe(
        sorted(raeumen_op.Flaechen) != [] and len(raeumen_op.Flaechen) == 2,
        f"Räumen: {list(raeumen_op.Flaechen)}",
    )
    h.pruefe(
        (raeumen_op.Ebenen, raeumen_op.Lagen) == (2, 2),
        f"Räumen: {raeumen_op.Ebenen} Ebenen, {raeumen_op.Lagen} Lagen",
    )
    h.pruefe(abs(float(kontur_op.Breite) - 0.3) < 1e-6, f"Kontur: Breite {float(kontur_op.Breite)}")
    h.pruefe(kontur_op.Bahnen == 1, f"Kontur: {kontur_op.Bahnen} Bahnen (nur Schlichten)")
    Gui.Selection.clearSelection()
    Gui.activeDocument().activeView().viewTop()
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
