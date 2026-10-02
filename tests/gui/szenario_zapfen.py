# Ein Zapfen auf der 3-Achs-Fräse (P-2026-10-02-17): Platte 100 × 80 × 30, oben ein Zapfen
# 40 × 30 × 10; rundum 10 tiefer die Fläche bis an den Rand; T1 der Standardfräser Ø 12.
# Zapfenoberseite, Zapfenwände und die Fläche drumherum anklicken: Räumen oder Planfräsen (die
# schnellere) fräst die ebenen Flächen, die Kontur fährt um den Zapfen – nur das, was davor
# stehen bleibt: „… – nur das Aufmaß an den Wänden: den Boden davor räumt das Räumen“ (oder
# „… den Boden davor fräst das Planfräsen“) mit höchstens 3 Bahnen, nicht alle Bahnen vom Rohteil
# her. „Anlegen“, „Auf der Maschine prüfen“: am Ende nirgends ins Teil.
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
    from camaddon import planfraesen as pf
    from camaddon import raeumen as ra
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()

    doc = FreeCAD.newDocument("Zapfen")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Zapfen")
    form = Part.makeBox(100, 80, 20, V(0, 0, -30)).fuse(Part.makeBox(40, 30, 10, V(30, 25, -10)))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    oben = boden = None
    waende = []
    for i, f in enumerate(teil.Shape.Faces):
        if type(f.Surface).__name__ != "Plane":
            continue
        c, bb = f.CenterOfMass, f.BoundBox
        if abs(c.z) < 1e-6:
            oben = f"Face{i + 1}"
        elif abs(c.z + 10) < 1e-6:
            boden = f"Face{i + 1}"
        elif bb.ZMin > -10 - 1e-6:
            waende.append(f"Face{i + 1}")
    h.pruefe(oben and boden and len(waende) == 4, f"Flächen: {oben}, {boden}, {waende}")
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
    for name in (boden, *waende):
        panel.flaeche_umschalten(name)
    yield 1000
    yield from h.warte_auf(
        lambda: all(b.vorschau is not None or not b.aktiv() for b in panel.bloecke), 300000
    )
    yield 3000
    plan, raeumen, kontur = panel.plan, panel.raeumen, panel.kontur
    h.pruefe(plan.aktiv() != raeumen.aktiv(), "nicht genau eins von Planfräsen und Räumen")
    h.pruefe(kontur.aktiv(), "Kontur: kein Haken")
    rot = [(b.s.kennung, b.hinweis.text()) for b in panel.bloecke if b.aktiv() and b.hinweis.text()]
    h.pruefe(not rot, f"rot angehakt: {rot}")
    text = kontur.ergebnis.text()
    bahnen = re.search(r"(\d+) Bahn", text)
    davor = (
        "nur das Aufmaß an den Wänden: den Boden davor räumt das Räumen"
        if raeumen.aktiv()
        else "nur der Rest an den Wänden: den Boden davor fräst das Planfräsen"
    )
    h.pruefe(
        text.endswith(davor) and bahnen is not None and int(bahnen.group(1)) <= 3,
        f"Kontur: {text!r}",
    )
    h.bild("1_zapfen", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 4000
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    ebene = [o for o in ops if pf.ist_planfraesen(o) or ra.ist_raeumen(o)]
    konturen = [o for o in ops if ko.ist_kontur(o)]
    h.pruefe(
        len(ebene) == 1 and sorted(ebene[0].Flaechen) == sorted([oben, boden]),
        f"Ebene Flächen: {namen} {[list(o.Flaechen) for o in ebene]}",
    )
    h.pruefe(
        len(konturen) == 1
        and sorted(konturen[0].Flaechen) == sorted(waende)
        and 0 < float(konturen[0].Breite) < 3,
        f"Kontur: {namen} {[(list(o.Flaechen), float(o.Breite)) for o in konturen]}",
    )
    h.pruefe(namen.index(ebene[0].Label) < namen.index(konturen[0].Label), f"Folge: {namen}")
    Gui.Selection.clearSelection()
    Gui.activeDocument().activeView().viewIsometric()
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
    spieler.setze_zeit(spieler.abfahrt.dauer)
    yield from h.warte_auf(lambda: spieler.rest.text().startswith("Am Ende"), 300000)
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
