# „Bearbeitung (Fräsen)“ mit „Bohrung fräsen“ (W-006 S3g) und dem Wettbewerb gegen die Kontur
# (Grundsatz 0): Block 100 × 60 × 20 mit einer durchgehenden Bohrung Ø 20 bei (25, 30) und einer
# Sackbohrung Ø 34, 10 tief, bei (70, 30); T1 der Standardfräser Ø 12 (ae 1,5, ap 25). Die Wand
# der durchgehenden Bohrung anklicken, den Knopf drücken, die der Sackbohrung dazunehmen: In der
# Liste steht „Bohrung Ø 20, durchgehend“ und „Bohrung Ø 34, Grund 10“. Bohrung fräsen und Kontur
# rechnen beide – Bohrung fräsen (Helix hinab, Ringe, die Wand in einem Zug) ist schneller,
# behält den Haken und sagt es; die Kontur verliert ihn: „… – N % langsamer als Bohrung
# fräsen“. „Anlegen“: nur „Bohrung fräsen T1“ mit G3 (Gleichlauf: in der Bohrung gegen den
# Uhrzeigersinn). Doppelklick öffnet das Fenster nur mit diesem Block; ohne Haken „Gleichlauf“
# und „Übernehmen“: G2. Dann „Auf der Maschine prüfen“: am Ende nirgends ins Teil.
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
    from camaddon import bohrung as bo
    from camaddon import bohrung_bahn as bb
    from camaddon import kontur as ko
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    wz.Bibliothek([t1]).speichern()

    doc = FreeCAD.newDocument("Bohrungen")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    form = Part.makeBox(100, 60, 20)
    form = form.cut(Part.makeCylinder(10, 20, V(25, 30, 0)))
    form = form.cut(Part.makeCylinder(17, 10, V(70, 30, 10)))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    namen = {round(b.radius, 6): b.name for b in bb.bohrungen(teil.Shape)}
    durch, sack = namen.get(10.0), namen.get(17.0)
    h.pruefe(durch is not None and sack is not None, f"Bohrungen: {namen}")
    if durch is None or sack is None:
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, durch)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    panel.flaeche_umschalten(sack)
    h.pruefe(sorted(panel.flaechen()) == sorted([durch, sack]), f"Flächen: {panel.flaechen()}")
    eintraege = [panel.flaechen_liste.item(i).text() for i in range(panel.flaechen_liste.count())]
    h.pruefe(
        any("Bohrung Ø 20, durchgehend" in t for t in eintraege)
        and any("Bohrung Ø 34, Grund 10" in t for t in eintraege),
        f"Liste: {eintraege}",
    )
    bohrung, kontur, plan, raeumen = panel.bohrung, panel.kontur, panel.plan, panel.raeumen
    h.pruefe(not plan.aktiv() and not raeumen.aktiv(), "Planfräsen oder Räumen angehakt")
    h.pruefe(bohrung.fraeser() is not None and bohrung.fraeser().nummer == 1, "Fräser T1")
    einsatz = bohrung.einsatz()
    h.pruefe(einsatz is not None and einsatz.art == wz.SCHRUPPEN, "Einsatz Schruppen")
    h.pruefe(
        bohrung.haken_felder["gleichlauf"].isChecked()
        and bohrung.haken_felder["schlichten"].isChecked(),
        "Gleichlauf und Schlichten vorgewählt",
    )
    yield from h.warte_auf(
        lambda: bohrung.vorschau is not None and kontur.vorschau is not None, 60000
    )
    yield 300
    h.pruefe(not bohrung.hinweis.text(), f"rot: {bohrung.hinweis.text()!r}")
    h.pruefe(bohrung.aktiv() and not kontur.aktiv(), "Haken: Bohrung fräsen an, Kontur aus")
    text = bohrung.ergebnis.text()
    h.pruefe(text.startswith("→ 2 Bohrungen, 2 Lagen, "), f"Bohrung fräsen: {text!r}")
    h.pruefe("– die schnellste; Kontur wäre" in text and "% langsamer" in text, f"{text!r}")
    text_kontur = kontur.ergebnis.text()
    h.pruefe(text_kontur.endswith("% langsamer als Bohrung fräsen"), f"Kontur: {text_kontur!r}")
    h.bild("1_bohrung", panel.form)

    # --- Anlegen: nur „Bohrung fräsen T1“ ----------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 2000
    h.pruefe(gui_bearbeitung.BearbeitungPanel.offen is None, "Fenster nach „Anlegen“ offen")
    ops = list(job.Operations.Group)
    h.pruefe(
        len(ops) == 1 and bo.ist_bohrungsfraesen(ops[0]), f"Operationen: {[o.Label for o in ops]}"
    )
    h.pruefe(not any(ko.ist_kontur(o) for o in ops), "Kontur wurde angelegt")
    if not ops:
        return
    op = ops[0]
    h.pruefe(op.Label == "Bohrung fräsen T1", f"Name: {op.Label}")
    h.pruefe((op.Bohrungen, op.Lagen) == (2, 2), f"{op.Bohrungen} Bohrungen, {op.Lagen} Lagen")
    befehle = {b.Name for b in op.Path.Commands}
    h.pruefe("G3" in befehle and "G2" not in befehle, f"Gleichlauf: {sorted(befehle)}")
    Gui.Selection.clearSelection()
    Gui.activeDocument().activeView().viewTop()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_angelegt")

    # --- Ändern: Doppelklick öffnet das Fenster nur mit dem Block Bohrung fräsen -------------
    op.ViewObject.Proxy.doubleClicked(op.ViewObject)
    yield 1000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.zu_aendern is op, "Doppelklick öffnet nichts")
    if panel is None:
        return
    bohrung = panel.bohrung
    h.pruefe(panel.block_zu_aendern is bohrung, "beim Ändern: nicht der Block Bohrung fräsen")
    h.pruefe(not panel.kontur.widget.isVisible(), "beim Ändern: der Block Kontur ist sichtbar")
    yield from h.warte_auf(lambda: bohrung.vorschau is not None, 30000)
    text = bohrung.ergebnis.text()
    h.pruefe(text.startswith("→ 2 Bohrungen, ") and "schnellste" not in text, f"{text!r}")
    h.bild("3_aendern", panel.form)
    bohrung.haken_felder["gleichlauf"].setChecked(False)
    yield from h.warte_auf(lambda: bohrung.vorschau is not None, 30000)
    h.pruefe(panel.accept() is True, "„Übernehmen“ ging nicht")
    yield 1500
    befehle = {b.Name for b in op.Path.Commands}
    h.pruefe(
        op.Gleichlauf is False and "G2" in befehle and "G3" not in befehle,
        f"nach dem Ändern: Gleichlauf {op.Gleichlauf}, {sorted(befehle)}",
    )

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
    h.bild("4_pruefen_farben")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
