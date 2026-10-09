# „Bearbeitung (Fräsen)“ an einer Nut (W-006 4.1 Punkt 6) und der Wettbewerb (Grundsatz 0):
# Platte 100 × 60 × 20 mit einem Langloch, 20 breit, 10 tief, Halbkreise um (25, 20) und
# (55, 20); T1 der Standardfräser Ø 12 (ae 1,5, ap 25). Den Grund anklicken: Räumen und Nut
# rechnen beide – Räumen schnitte in der Nut zuerst in voller Breite (mehr als ae) und tritt
# nicht an: Die Nut bekommt den Haken, Räumen sagt „… – in der Nut schnitte es zuerst in voller
# Breite …“ (P-2026-10-01-47). Statt des Grunds eine Wand: Nut gegen Kontur – die Nut (Helix
# hinab, Bögen mit dem Schritt nach der Last, P-2026-10-02-56: „→ 1 Nut, 1 Lage, 31 Bögen,
# etwa …“; die Wand rundum) gegen die Kontur an der Wand; den Haken hat die schnellere, beide
# Zeilen sagen es. Zurück zum Grund, „Anlegen“: nur
# „Nut T1“ mit Endtiefe 10 und G3 (Gleichlauf). „Auf der Maschine prüfen“: am Ende nirgends
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
    from camaddon import kontur as ko
    from camaddon import nut as nu
    from camaddon import raeumen as ra
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    wz.Bibliothek([t1]).speichern()

    doc = FreeCAD.newDocument("Nut")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    nut = Part.makeBox(30, 20, 11, V(25, 10, 10))
    nut = nut.fuse(Part.makeCylinder(10, 11, V(25, 20, 10)))
    nut = nut.fuse(Part.makeCylinder(10, 11, V(55, 20, 10)))
    teil.Shape = Part.makeBox(100, 60, 20).cut(nut).removeSplitter()
    doc.recompute()
    grund = next(
        (
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if abs(f.BoundBox.ZMin - 10) < 1e-6 and abs(f.BoundBox.ZMax - 10) < 1e-6
        ),
        None,
    )
    wand = next(
        (
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if isinstance(f.Surface, Part.Plane)
            and abs(f.BoundBox.YMin - 30) < 1e-6
            and abs(f.BoundBox.YMax - 30) < 1e-6
            and f.BoundBox.ZMin > 9.9
        ),
        None,
    )
    h.pruefe(grund is not None and wand is not None, f"Grund {grund}, Wand {wand}")
    if grund is None or wand is None:
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, grund)
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
    nut_block, raeumen, kontur = panel.nut, panel.raeumen, panel.kontur
    panel.knopf_weiter.click()  # Schritt 2: die Strategien mit ihrer Zeit (für die Bilder)

    # --- Der Grund: Räumen gegen Nut ------------------------------------------------------------
    yield from h.warte_auf(
        lambda: nut_block.vorschau is not None and raeumen.vorschau is not None, 180000
    )
    yield 1500
    text = nut_block.ergebnis.text()
    h.pruefe(nut_block.aktiv() and not raeumen.aktiv(), "Grund: die Nut nicht der Sieger")
    h.pruefe(text.startswith("→ 1 Nut, 1 Lage, 31 Bögen, etwa "), f"Nut am Grund: {text!r}")
    h.pruefe(
        "auf dem Grund der Nut schnitte es zuerst in voller Breite" in raeumen.ergebnis.text(),
        f"Räumen am Grund: {raeumen.ergebnis.text()!r}",
    )
    h.pruefe(not nut_block.hinweis.text(), f"rot: {nut_block.hinweis.text()!r}")
    liste = panel.flaechen_liste.item(0).text() if panel.flaechen_liste.count() else ""
    h.pruefe(liste.endswith("Nut 20 × 50, Grund 10"), f"Liste: {liste!r}")
    h.bild("1_grund", panel.form)

    # --- Eine Wand statt des Grunds: Nut gegen Kontur --------------------------------------------
    panel.flaeche_umschalten(grund)
    panel.flaeche_umschalten(wand)
    yield 300
    yield from h.warte_auf(
        lambda: nut_block.vorschau is not None and kontur.vorschau is not None, 180000
    )
    yield 1500
    text = nut_block.ergebnis.text()
    print(ascii(f"Nut an der Wand: {text}"))
    print(ascii(f"Kontur an der Wand: {kontur.ergebnis.text()}"))
    h.pruefe(nut_block.aktiv() != kontur.aktiv(), "Wand: nicht genau eine angehakt")
    h.pruefe(not raeumen.aktiv(), "Räumen angehakt")
    h.pruefe(text.startswith("→ 1 Nut, 1 Lage, 31 Bögen, etwa "), f"Nut an der Wand: {text!r}")
    sieger, zweite, name = (
        (nut_block, kontur, "Kontur") if nut_block.aktiv() else (kontur, nut_block, "Nut")
    )
    h.pruefe(
        f"die schnellste; {name} wäre" in sieger.ergebnis.text()
        and "% langsamer als " in zweite.ergebnis.text(),
        f"Wand: {sieger.ergebnis.text()!r} / {zweite.ergebnis.text()!r}",
    )
    h.bild("2_wand", panel.form)

    # --- Zurück zum Grund: dort die Nut --------------------------------------------------------
    panel.flaeche_umschalten(wand)
    panel.flaeche_umschalten(grund)
    yield 300
    yield from h.warte_auf(
        lambda: nut_block.vorschau is not None and raeumen.vorschau is not None, 180000
    )
    yield 1500
    h.pruefe(
        nut_block.aktiv() and not kontur.aktiv() and not raeumen.aktiv(),
        f"Grund: Nut {nut_block.aktiv()}, Kontur {kontur.aktiv()}, Räumen {raeumen.aktiv()}",
    )

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 2500
    ops = list(job.Operations.Group)
    nuten = [o for o in ops if nu.ist_nut(o)]
    h.pruefe(
        len(nuten) == 1
        and nuten[0].Label == "Nut T1"
        and not any(ko.ist_kontur(o) or ra.ist_raeumen(o) for o in ops),
        f"Operationen: {[o.Label for o in ops]}",
    )
    if not nuten:
        return
    op = nuten[0]
    h.pruefe(abs(float(op.FinalDepth) - 10.0) < 1e-6, f"Endtiefe {op.FinalDepth}")
    # Derselbe Eintauchwinkel wie in der Vorschau: der am Fräser (P-2026-10-02-65; bis dahin 5°).
    h.pruefe(
        abs(float(op.Eintauchwinkel) - t1.eintauchwinkel) < 1e-6,
        f"Eintauchwinkel {float(op.Eintauchwinkel)} statt {t1.eintauchwinkel}",
    )
    befehle = [c.Name for c in op.Path.Commands]
    h.pruefe("G3" in befehle and "G2" not in befehle, "nicht im Gleichlauf (G3)")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("3_angelegt")

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
