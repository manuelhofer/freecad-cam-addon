# „Bearbeitung (Fräsen)“ an einer offenen Nut (W-006 4.1 Punkt 6, P-2026-10-01-47): Platte
# 60 × 40 × 20 mit einer Nut 16 breit, 8 tief, längs X ganz durch – an beiden Enden offen; T1 der
# Standardfräser Ø 12 (ae 1,5, ap 25). Eine Wand anklicken: In der Liste „offene Nut 16 × 60,
# Grund 12“; Nut gegen Kontur – seit den Bögen (P-2026-10-02-22) ist hier die Kontur etwas
# schneller: Die Bögen rücken in der schmalen Nut nur 0,4 mm vor, damit der Fräser die Delle
# nicht weiter umschlingt als eine gerade Wand mit ae („→ 1 Nut, 1 Lage, … Bögen, etwa … – N %
# langsamer als Kontur“). Den Grund dazu: Räumen schnitte in der Nut in voller Breite und tritt
# nicht an – die Nut fräst ihn. „Anlegen“: nur „Nut T1“ mit Endtiefe 12. „Auf der Maschine
# prüfen“: am Ende nirgends ins Teil.
import re

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

    doc = FreeCAD.newDocument("NutOffen")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    teil.Shape = Part.makeBox(60, 40, 20).cut(Part.makeBox(60, 16, 8, V(0, 12, 12)))
    teil.Shape = teil.Shape.removeSplitter()
    doc.recompute()
    grund = next(
        (
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if abs(f.BoundBox.ZMin - 12) < 1e-6 and abs(f.BoundBox.ZMax - 12) < 1e-6
        ),
        None,
    )
    wand = next(
        (
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if isinstance(f.Surface, Part.Plane)
            and abs(f.BoundBox.YMin - 28) < 1e-6
            and abs(f.BoundBox.YMax - 28) < 1e-6
            and f.BoundBox.ZMin > 11.9
        ),
        None,
    )
    h.pruefe(grund is not None and wand is not None, f"Grund {grund}, Wand {wand}")
    if grund is None or wand is None:
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, wand)
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

    # --- Eine Wand: Nut gegen Kontur -------------------------------------------------------------
    yield from h.warte_auf(
        lambda: nut_block.vorschau is not None and kontur.vorschau is not None, 180000
    )
    yield 1500
    text = nut_block.ergebnis.text()
    # Die Bögen rücken in der schmalen Nut nur 0,4 mm vor (der Fräser umschlingt die Delle):
    # Die Kontur – in voller Breite mit kleinerer Zustellung – ist hier etwas schneller.
    h.pruefe(kontur.aktiv() and not nut_block.aktiv(), "Wand: Kontur nicht der Sieger")
    h.pruefe(
        re.match(r"→ 1 Nut, 1 Lage, \d+ Bögen, etwa ", text) and "langsamer als Kontur" in text,
        f"Nut an der Wand: {text!r}",
    )
    h.pruefe(not nut_block.hinweis.text(), f"rot: {nut_block.hinweis.text()!r}")
    liste = panel.flaechen_liste.item(0).text() if panel.flaechen_liste.count() else ""
    h.pruefe(liste.endswith("offene Nut 16 × 60, Grund 12"), f"Liste: {liste!r}")
    h.bild("1_wand", panel.form)

    # --- Der Grund statt der Wand: Räumen tritt nicht an ---------------------------------------
    panel.flaeche_umschalten(wand)
    panel.flaeche_umschalten(grund)
    yield 300
    yield from h.warte_auf(
        lambda: nut_block.vorschau is not None and raeumen.vorschau is not None, 180000
    )
    yield 1500
    h.pruefe(nut_block.aktiv() and not raeumen.aktiv(), "Grund: die Nut nicht der Sieger")
    h.pruefe(
        "in der Nut schnitte es zuerst in voller Breite" in raeumen.ergebnis.text(),
        f"Räumen am Grund: {raeumen.ergebnis.text()!r}",
    )
    h.bild("2_grund", panel.form)

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
    h.pruefe(abs(float(op.FinalDepth) - 12.0) < 1e-6, f"Endtiefe {op.FinalDepth}")
    h.pruefe(op.Boegen > 0, f"Bögen {op.Boegen}")
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
