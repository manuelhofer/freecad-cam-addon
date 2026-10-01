# „Bearbeitung (Fräsen)“ – der Assistent für ein Teil im Quader (W-006 S3c). Block 60 × 40 × 20
# mit einem 5 mm höheren Absatz an der linken Seite, T1 Schaftfräser Ø 10 (Einsatz Planen).
# Die Fläche bei z = 20 anklicken, den Knopf drücken: Der Job mit dem Rohteil (1 mm Aufmaß)
# entsteht sofort, die Fläche steht grün in der Liste, die Vorschau sagt „→ 3 Lagen, 30
# Zeilen“. „Anlegen“: „Planfräsen T1“ mit 3 Lagen und 30 Zeilen, Sätze mit Bögen. Doppelklick
# darauf öffnet das Fenster mit ihren Werten; „Übernehmen“ mit 1,5 mm Zustellung rechnet sie
# neu – vier Lagen. Dann „Auf der Maschine prüfen“ mit der Beispiel-Fräse (W-006 S3d): Der
# Quader wird beim Abspielen abgetragen, am Ende steht die gewählte Fläche grün da, nirgends
# ins Teil, der Absatz ohne Farbe.
import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtCore


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
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(nummer=1, durchmesser=10, schneiden=3, schneidenlaenge=20)
    t1.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.PLANEN, ae=4, ap=2, vc=150, fz=0.05),
        wz.Einsatz(art=wz.SCHRUPPEN, ae=4, ap=5, vc=150, fz=0.05),
    ]
    wz.Bibliothek([t1]).speichern()

    doc = FreeCAD.newDocument("Block")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = (
        Part.makeBox(60, 40, 20).fuse(Part.makeBox(10, 40, 5, FreeCAD.Vector(0, 0, 20)))
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
        abs(job.Stock.Shape.BoundBox.ZMax - 26.0) < 1e-6, f"Rohteil {job.Stock.Shape.BoundBox}"
    )
    h.pruefe(panel.flaechen() == [flaeche], f"Flächen: {panel.flaechen()}")
    h.pruefe(panel.fraeser() is not None and panel.fraeser().nummer == 1, "Fräser T1")
    einsatz = panel.einsatz()
    h.pruefe(einsatz is not None and einsatz.art == wz.PLANEN, "Einsatz Planen vorgewählt")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    h.pruefe(not panel.hinweis.text(), f"rot: {panel.hinweis.text()!r}")
    text = panel.ergebnis.text()
    h.pruefe(text.startswith("→ 3 Lagen, 30 Zeilen, etwa"), f"Vorschau: {text!r}")
    zeile = panel.flaechen_liste.item(0).text() if panel.flaechen_liste.count() else ""
    h.pruefe(zeile.startswith(flaeche) and "eben nach oben" in zeile, f"Liste: {zeile!r}")
    h.bild("1_bearbeitung", panel.form)

    # Mehr Aufmaß oben: eine Lage mehr.
    panel.felder_rohteil["oben"].setText("3")
    yield from h.warte_auf(lambda: not panel._rohteil_uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    h.pruefe(abs(job.Stock.Shape.BoundBox.ZMax - 28.0) < 1e-6, "Rohteil folgt dem Feld nicht")
    text = panel.ergebnis.text()
    h.pruefe(text.startswith("→ 4 Lagen"), f"Vorschau mit 3 mm: {text!r}")
    panel.felder_rohteil["oben"].setText("")
    yield from h.warte_auf(lambda: not panel._rohteil_uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)

    # --- Anlegen: „Planfräsen T1“ ------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 2000
    h.pruefe(gui_bearbeitung.BearbeitungPanel.offen is None, "Fenster nach „Anlegen“ offen")
    ops = [o for o in job.Operations.Group if pf.ist_planfraesen(o)]
    h.pruefe(len(ops) == 1, f"Operationen: {[o.Label for o in job.Operations.Group]}")
    if not ops:
        return
    op = ops[0]
    h.pruefe(op.Label == "Planfräsen T1", f"Name: {op.Label}")
    h.pruefe(
        (op.Ebenen, op.Lagen, op.Zeilen) == (1, 3, 30), f"{op.Ebenen}, {op.Lagen}, {op.Zeilen}"
    )
    h.pruefe(list(op.Flaechen) == [flaeche], f"Flächen: {list(op.Flaechen)}")
    namen = {b.Name for b in op.Path.Commands}
    h.pruefe("G2" in namen or "G3" in namen, f"keine Bögen: {namen}")
    h.pruefe(teil.ViewObject.Visibility is False, "das Original ist noch sichtbar")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("2_angelegt")

    # --- Ändern: Doppelklick öffnet das Fenster mit den Werten --------------------------------
    op.ViewObject.Proxy.doubleClicked(op.ViewObject)
    yield 1000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.zu_aendern is op, "Doppelklick öffnet nichts")
    if panel is None:
        return
    h.pruefe(panel.fraeser() is not None and panel.fraeser().nummer == 1, "beim Ändern: Fräser")
    h.pruefe(not panel.rohteilfelder.isEnabled(), "Rohteil beim Ändern änderbar")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    h.bild("3_aendern", panel.form)
    panel.felder["zustellung"].setText("1,5")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    h.pruefe(panel.accept() is True, "„Übernehmen“ ging nicht")
    yield 1500
    h.pruefe(op.Lagen == 4, f"nach dem Ändern: {op.Lagen} Lagen")

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
        satz = spieler.rest.text()
        h.pruefe(satz.startswith("Das Rohteil wird beim Abspielen abgetragen"), f"{satz!r}")
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
    h.bild("5b_pruefen_fenster", pruef.form)
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
