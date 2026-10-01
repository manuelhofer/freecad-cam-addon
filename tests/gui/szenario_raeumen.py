# „Bearbeitung (Fräsen)“ mit dem Räumen und dem Wettbewerb der Strategien (W-006 S3f, Grundsatz
# 0). Manuels Beispiel: Block 50 × 50 × 20 mit einem Zapfen Ø 10, 10 hoch in der Mitte; T1 der
# Standardfräser Ø 12 (ae 1,5, ap 25). Die Oberseite bei z = 20 anklicken, den Knopf drücken:
# Der Job entsteht, Planfräsen und Räumen rechnen beide – Räumen ist schneller (eine Lage, Ringe
# von außen nach innen, zuletzt um den Zapfen, keine Rampe), bekommt den Haken und sagt es: „… – die schnellste;
# Planfräsen wäre N % langsamer“; beim Planfräsen steht „… – N % langsamer als Räumen“, sein
# Haken ist weg. „Anlegen“: nur „Räumen T1“, mit Bögen. Doppelklick darauf öffnet das Fenster nur
# mit dem Block Räumen; ohne Haken „Gleichlauf“ und „Übernehmen“ steht Gleichlauf False in der
# Operation. Dann „Auf der Maschine prüfen“ mit der Beispiel-Fräse: am Ende nirgends ins Teil
# geschnitten und auf der Fläche nichts stehen geblieben.
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
    from camaddon import planfraesen as pf
    from camaddon import raeumen as ra
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    wz.Bibliothek([t1]).speichern()

    doc = FreeCAD.newDocument("Zapfen")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = (
        Part.makeBox(50, 50, 20).fuse(Part.makeCylinder(5, 10, V(25, 25, 20)))
    ).removeSplitter()
    doc.recompute()
    flaeche = next(e.name for e in hf.ebenen_oben(teil.Shape) if abs(e.z - 20.0) < 1e-6)
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, flaeche)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    h.pruefe(
        abs(job.Stock.Shape.BoundBox.ZMax - 31.0) < 1e-6, f"Rohteil {job.Stock.Shape.BoundBox}"
    )
    h.pruefe(panel.flaechen() == [flaeche], f"Flächen: {panel.flaechen()}")
    raeumen, plan = panel.raeumen, panel.plan
    h.pruefe(raeumen.fraeser() is not None and raeumen.fraeser().nummer == 1, "Räumen: Fräser T1")
    einsatz = raeumen.einsatz()
    h.pruefe(einsatz is not None and einsatz.art == wz.SCHRUPPEN, "Räumen: Einsatz Schruppen")
    h.pruefe(raeumen.haken_felder["gleichlauf"].isChecked(), "Gleichlauf vorgewählt")
    yield from h.warte_auf(
        lambda: raeumen.vorschau is not None and plan.vorschau is not None, 60000
    )
    yield 300
    h.pruefe(not raeumen.hinweis.text(), f"rot: {raeumen.hinweis.text()!r}")
    # Der Wettbewerb: Räumen ist schneller und bekommt den Haken, das Planfräsen verliert ihn.
    h.pruefe(raeumen.aktiv() and not plan.aktiv(), "Haken: Räumen an, Planfräsen aus")
    h.pruefe(not panel.kontur.aktiv(), "Haken: Kontur an")
    text = raeumen.ergebnis.text()
    h.pruefe(text.startswith("→ 1 Lage, ") and " Ringe, etwa 3 min" in text, f"Räumen: {text!r}")
    h.pruefe("– die schnellste; Planfräsen wäre" in text and "% langsamer" in text, f"{text!r}")
    text_plan = plan.ergebnis.text()
    h.pruefe(text_plan.startswith("→ 1 Lage, 44 Zeilen, etwa 5 min"), f"Planfräsen: {text_plan!r}")
    h.pruefe(text_plan.endswith("% langsamer als Räumen"), f"Planfräsen: {text_plan!r}")
    h.pruefe("Zeilen längs X" in text_plan, f"Planfräsen ohne Richtung: {text_plan!r}")
    h.bild("1_wettbewerb", panel.form)

    # --- Anlegen: nur „Räumen T1“ ------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 2000
    h.pruefe(gui_bearbeitung.BearbeitungPanel.offen is None, "Fenster nach „Anlegen“ offen")
    ops = list(job.Operations.Group)
    h.pruefe(len(ops) == 1 and ra.ist_raeumen(ops[0]), f"Operationen: {[o.Label for o in ops]}")
    h.pruefe(not any(pf.ist_planfraesen(o) for o in ops), "Planfräsen wurde angelegt")
    if not ops:
        return
    op = ops[0]
    h.pruefe(op.Label == "Räumen T1", f"Name: {op.Label}")
    h.pruefe(
        (op.Ebenen, op.Lagen) == (1, 1) and 15 <= op.Ringe <= 20,
        f"{op.Ebenen}, {op.Lagen}, {op.Ringe}",
    )
    ringe_vorher = op.Ringe
    h.pruefe(op.Gerechnet.startswith("morph "), f"Gerechnet: {op.Gerechnet!r}")
    h.pruefe(list(op.Flaechen) == [flaeche], f"Flächen: {list(op.Flaechen)}")
    namen = {b.Name for b in op.Path.Commands}
    h.pruefe("G2" in namen or "G3" in namen, f"keine Bögen: {namen}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("2_angelegt")

    # --- Ändern: Doppelklick öffnet das Fenster nur mit dem Block Räumen --------------------
    op.ViewObject.Proxy.doubleClicked(op.ViewObject)
    yield 1000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.zu_aendern is op, "Doppelklick öffnet nichts")
    if panel is None:
        return
    raeumen = panel.raeumen
    h.pruefe(panel.block_zu_aendern is raeumen, "beim Ändern: nicht der Block Räumen")
    h.pruefe(not panel.plan.widget.isVisible(), "beim Ändern: der Block Planfräsen ist sichtbar")
    h.pruefe(raeumen.fraeser() is not None and raeumen.fraeser().nummer == 1, "beim Ändern: Fräser")
    h.pruefe(raeumen.haken_felder["gleichlauf"].isChecked(), "beim Ändern: Gleichlauf")
    yield from h.warte_auf(lambda: raeumen.vorschau is not None, 30000)
    text = raeumen.ergebnis.text()
    h.pruefe(text.startswith("→ 1 Lage, ") and "schnellste" not in text, f"{text!r}")
    h.bild("3_aendern", panel.form)
    raeumen.haken_felder["gleichlauf"].setChecked(False)
    yield from h.warte_auf(lambda: raeumen.vorschau is not None, 30000)
    h.pruefe(panel.accept() is True, "„Übernehmen“ ging nicht")
    yield 1500
    h.pruefe(op.Gleichlauf is False, "nach dem Ändern: Gleichlauf")
    h.pruefe(op.Ringe == ringe_vorher, f"nach dem Ändern: {op.Ringe} statt {ringe_vorher} Ringe")

    # --- Auf der Maschine prüfen: der Quader wird abgetragen, am Ende Farben -----------------
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 500
    FreeCAD.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400  # siehe szenario_reichweite.py: 1.1.3 verarbeitet die Auswahl verzögert
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruef is None:
        return
    yield 800
    abtrag = getattr(getattr(pruef, "bild", None), "abtrag", None)
    h.pruefe(abtrag is not None and hasattr(abtrag, "quader"), f"Abtrag: {type(abtrag).__name__}")
    spieler = pruef.abspieler
    fahrt = spieler.abfahrt
    stationen = [s for s in fahrt.stationen if not s.eilgang]
    h.pruefe(len(stationen) > 50, f"{len(stationen)} Stationen im Vorschub")
    if stationen:
        spieler.setze_zeit(stationen[len(stationen) // 2].zeit)
        spieler.knopf_hinsehen.click()
        yield 500
        h.bild("4_pruefen_mittendrin")
    spieler.setze_zeit(fahrt.dauer)
    yield 500
    rest = spieler.rest.text()
    h.pruefe(
        rest.startswith("Am Ende bleiben")
        and "nirgends ins Teil" in rest
        and "gewählten Flächen" in rest,
        f"{rest!r}",
    )
    Gui.SendMsgToActiveView("ViewFit")
    spieler.knopf_hinsehen.click()
    yield 500
    h.bild("5_pruefen_farben")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
