# Eine Tasche mit kleinen Ecken auf der 3-Achs-Fräse (P-2026-10-02-19): Platte 100 × 60 × 20,
# Tasche 50 × 30 × 10, die senkrechten Ecken R 4 – kleiner als der Standardfräser Ø 12 (R 6); in
# der Werkzeugverwaltung dazu T3, ein Schaftfräser Ø 6. Taschenboden und Taschenwände anklicken:
# Räumen und Kontur mit T1 – und, weil gezeichnete Rundungen innen kleiner sind als sein Radius,
# hakt der Assistent „Restmaterial“ mit T3 selbst an (Manuel: „Ja“; vorher blieb R 6 in den
# Ecken, den Haken musste man kennen). Von Hand abgehakt bleibt er ab. „Anlegen“: „Restmaterial
# T3“ nach der Kontur; „Auf der Maschine prüfen“: am Ende nirgends ins Teil.
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
    from camaddon import werkzeuge as wz

    t3 = wz.Werkzeug(nummer=3, durchmesser=6.0, schneiden=3, schneidenlaenge=20.0,
                     laenge_spindelnase=100.0)  # fmt: skip
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=0.75, ap=12.0, vc=150.0, fz=0.03)]
    wz.Bibliothek([wz.standardwerkzeug(), t3]).speichern()

    doc = FreeCAD.newDocument("Ecken")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Ecken")
    tasche = Part.makeBox(50, 30, 10, V(25, 15, -10))
    senkrecht = [k for k in tasche.Edges if abs(k.BoundBox.ZMax - k.BoundBox.ZMin) > 1]
    form = Part.makeBox(100, 60, 20, V(0, 0, -20)).cut(tasche.makeFillet(4, senkrecht))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    boden = None
    waende = []
    for i, f in enumerate(teil.Shape.Faces):
        bb = f.BoundBox
        if not (bb.XMin > 1 and bb.XMax < 99 and bb.YMin > 1 and bb.YMax < 59):
            continue
        if bb.ZMax - bb.ZMin < 1e-6:
            boden = f"Face{i + 1}"
        else:
            waende.append(f"Face{i + 1}")
    h.pruefe(boden is not None and len(waende) == 8, f"Flächen: {boden}, {waende}")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, boden)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    for name in waende:
        panel.flaeche_umschalten(name)
    yield 1000
    yield from h.warte_auf(
        lambda: all(b.vorschau is not None or not b.aktiv() for b in panel.bloecke), 300000
    )
    yield 3000
    kontur, rest = panel.kontur, panel.rest
    h.pruefe(panel.raeumen.aktiv() or panel.plan.aktiv(), "Boden: kein Haken")
    h.pruefe(kontur.aktiv() and kontur.fraeser().nummer == 1, "Kontur: kein Haken oder nicht T1")
    h.pruefe(rest.aktiv() and not rest.von_hand, "Restmaterial: nicht von selbst angehakt")
    h.pruefe(rest.fraeser() is not None and rest.fraeser().nummer == 3, "Restmaterial: nicht T3")
    rot = [(b.s.kennung, b.hinweis.text()) for b in panel.bloecke if b.aktiv() and b.hinweis.text()]
    h.pruefe(not rot, f"rot angehakt: {rot}")
    text = rest.ergebnis.text()
    h.pruefe(text.startswith("→ "), f"Restmaterial: {text!r}")
    h.bild("1_ecken", panel.form)

    # Von Hand abgehakt bleibt er ab – auch wenn sich die Wahl ändert.
    rest.haken.click()
    yield 300
    panel.flaeche_umschalten(waende[0])
    yield 300
    panel.flaeche_umschalten(waende[0])
    yield 1000
    h.pruefe(not rest.aktiv() and rest.von_hand, "von Hand abgehakt: der Haken kam wieder")
    rest.haken.click()
    yield 300
    yield from h.warte_auf(
        lambda: all(b.vorschau is not None or not b.aktiv() for b in panel.bloecke), 300000
    )
    yield 1000

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 4000
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    konturen = [o for o in ops if ko.ist_kontur(o) and not ko.ist_rest(o)]
    reste = [o for o in ops if ko.ist_rest(o)]
    h.pruefe(len(konturen) == 1 and len(reste) == 1, f"Kontur und Restmaterial: {namen}")
    h.pruefe(
        reste and reste[0].Label == "Restmaterial T3",
        f"Restmaterial: {[o.Label for o in reste]}",
    )
    h.pruefe(
        konturen and reste and namen.index(konturen[0].Label) < namen.index(reste[0].Label),
        f"Folge: {namen}",
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
