# Ein Absatz auf der 3-Achs-Fräse (P-2026-10-02-17): Block 80 × 50 × 30, vorn ein Absatz 15
# breit und 10 tief über die ganze Länge (offen an drei Seiten); T1 der Standardfräser Ø 12.
# Oberseite, Absatzboden und Absatzwand anklicken. Seit P-2026-10-17-18 (Manuel: Planfräsen
# bringt die Oberseite auf Maß, eine Kontur herausarbeiten ist Konturfräsen) nimmt das Planfräsen
# nur die Oberseite; der Absatzboden heißt „Absatz – Räumen“. Die schnellere Folge hat die Haken
# (hier Planfräsen der Oberseite und die Kontur, die den Absatz an der Wand herausarbeitet).
# „Anlegen“, „Auf der Maschine prüfen“: am Ende nirgends ins Teil.

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
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()

    doc = FreeCAD.newDocument("Absatz")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Absatz")
    form = Part.makeBox(80, 50, 30, V(0, 0, -30)).cut(Part.makeBox(80, 15, 10, V(0, 0, -10)))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    oben = boden = wand = None
    for i, f in enumerate(teil.Shape.Faces):
        if type(f.Surface).__name__ != "Plane":
            continue
        c = f.CenterOfMass
        if abs(c.z) < 1e-6:
            oben = f"Face{i + 1}"
        elif abs(c.z + 10) < 1e-6:
            boden = f"Face{i + 1}"
        elif abs(c.y - 15) < 1e-6:
            wand = f"Face{i + 1}"
    h.pruefe(None not in (oben, boden, wand), f"Flächen: {oben}, {boden}, {wand}")
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
    for name in (boden, wand):
        panel.flaeche_umschalten(name)
    yield 1000
    yield from h.warte_auf(
        lambda: not panel.vorschau_laeuft()
        and all(b.vorschau is not None or not b.aktiv() for b in panel.bloecke),
        300000,
    )
    yield 3000
    plan, raeumen, kontur = panel.plan, panel.raeumen, panel.kontur
    # Planfräsen bringt nur die Oberseite auf Maß (Manuel, 2026-10-17: „planfräsen ... ist für mich
    # wenn ich ein bauteil habe das in z 4 mm aufmass hat“) – der Absatz hat an einer Seite eine
    # Wand: Er heißt in der Liste „Absatz – Räumen“, das Planfräsen nimmt ihn nicht.
    form = vr.modell(job).Shape
    h.pruefe(
        plan.s.flaechen_fuer(form, panel.gewaehlte) == [oben],
        f"Planfräsen nimmt: {plan.s.flaechen_fuer(form, panel.gewaehlte)}",
    )
    liste = [panel.flaechen_liste.item(i).text() for i in range(panel.flaechen_liste.count())]
    h.pruefe(any(boden in z and "Absatz" in z for z in liste), f"Liste: {liste}")
    # Die schnellere Folge hat die Haken: Planfräsen der Oberseite und die Kontur, die den Absatz
    # an der Wand herausarbeitet – oder Räumen über beides und die Kontur nur das Aufmaß.
    h.pruefe(plan.aktiv() != raeumen.aktiv(), "Planfräsen und Räumen: beide oder keins angehakt")
    h.pruefe(kontur.aktiv(), "Kontur: kein Haken")
    zeiten = f"Planfräsen {plan.zeit} min, Räumen {raeumen.zeit} min"
    h.pruefe(bool(plan.zeit) and bool(raeumen.zeit), zeiten)
    panel.seite_zeigen(1)
    yield 300
    h.bild("1_absatz", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    mit_plan = plan.aktiv()
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 4000
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    planops = [o for o in ops if pf.ist_planfraesen(o)]
    konturen = [o for o in ops if ko.ist_kontur(o)]
    if mit_plan:
        h.pruefe(
            len(planops) == 1 and list(planops[0].Flaechen) == [oben],
            f"Planfräsen: {namen} {[list(o.Flaechen) for o in planops]}",
        )
    else:
        h.pruefe(not planops, f"Planfräsen angelegt: {namen}")
    h.pruefe(
        len(konturen) == 1 and list(konturen[0].Flaechen) == [wand],
        f"Kontur: {namen} {[list(o.Flaechen) for o in konturen]}",
    )
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
