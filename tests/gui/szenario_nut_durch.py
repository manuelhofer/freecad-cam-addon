# Manuels Beispiel (P-2026-10-02-22): eine Nut mitten durch einen Klotz – „im Gleichlauf einen
# Halbkreis fahren, so dass mittig eine Delle entsteht, im Eilgang oder Schnellvorschub wieder auf
# die andere Seite und die nächste Morph-Bahn“. Klotz 80 × 60 × 30, die Nut 30 breit, 12 tief,
# längs X ganz durch; T1 der Standardfräser Ø 12 (ae 1,5, ap 25). Früher war sie „zu breit“ für
# die Nut (in der Mitte der Kreise bliebe ein Kern); jetzt fräst die Nut sie in Bögen. Den Grund
# anklicken: In der Liste „offene Nut 30 × 80, Grund 18“, die Nut ohne Rot, „→ 1 Nut, 1 Lage,
# … Bögen, etwa …“. „Anlegen“: „Nut T1“ mit Bögen, im Gleichlauf (G3), zurück im
# Schnellvorschub (3 × F). „Auf der Maschine prüfen“: am Ende nirgends ins Teil.
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
    from camaddon import nut as nu
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()

    doc = FreeCAD.newDocument("NutDurch")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Klotz")
    teil.Shape = Part.makeBox(80, 60, 30).cut(Part.makeBox(80, 30, 12, V(0, 15, 18)))
    teil.Shape = teil.Shape.removeSplitter()
    doc.recompute()
    grund = next(
        (
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if abs(f.BoundBox.ZMin - 18) < 1e-6 and abs(f.BoundBox.ZMax - 18) < 1e-6
        ),
        None,
    )
    h.pruefe(grund is not None, "kein Grund")
    if grund is None:
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
    nut_block = panel.nut
    yield from h.warte_auf(lambda: nut_block.vorschau is not None, 300000)
    yield 1500
    text = nut_block.ergebnis.text()
    h.pruefe(nut_block.aktiv(), "die Nut nicht angehakt")
    h.pruefe(not nut_block.hinweis.text(), f"rot: {nut_block.hinweis.text()!r}")
    h.pruefe(re.match(r"→ 1 Nut, 1 Lage, \d+ Bögen, etwa ", text), f"Nut: {text!r}")
    liste = panel.flaechen_liste.item(0).text() if panel.flaechen_liste.count() else ""
    h.pruefe(liste.endswith("offene Nut 30 × 80, Grund 18"), f"Liste: {liste!r}")
    andere = [
        (b.s.kennung, b.ergebnis.text()) for b in panel.bloecke if b.aktiv() and b is not nut_block
    ]
    h.pruefe(not andere, f"außer der Nut angehakt: {andere}")
    h.bild("1_grund", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    nuten = [o for o in job.Operations.Group if nu.ist_nut(o)]
    h.pruefe(len(nuten) == 1, f"Operationen: {[o.Label for o in job.Operations.Group]}")
    if not nuten:
        return
    op = nuten[0]
    h.pruefe(op.Boegen > 0, f"Bögen {op.Boegen}")
    befehle = list(op.Path.Commands)
    namen = [c.Name for c in befehle]
    h.pruefe("G3" in namen and "G2" not in namen, "nicht im Gleichlauf (G3)")
    vorschuebe = sorted({round(c.Parameters["F"], 3) for c in befehle if "F" in c.Parameters})
    h.pruefe(
        len(vorschuebe) >= 2 and abs(vorschuebe[-1] / vorschuebe[-2] - 3.0) < 0.01,
        f"kein Rückweg mit 3 × F: {vorschuebe}",
    )
    Gui.Selection.clearSelection()
    Gui.activeDocument().activeView().viewTop()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_angelegt_von_oben")
    Gui.activeDocument().activeView().viewIsometric()
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
    spieler.setze_zeit(spieler.abfahrt.dauer)
    yield from h.warte_auf(lambda: spieler.rest.text().startswith("Am Ende"), 300000)
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
