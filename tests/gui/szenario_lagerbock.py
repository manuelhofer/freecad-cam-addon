# Ein Lagerbock auf der 3-Achs-Fräse (P-2026-10-02-15): Block 100 × 50 × 30, Lagerbohrung Ø 30
# durch, zwei Senkungen für M8 (Ø 14 × 8,5 über Ø 9 durch); T1 der Standardfräser Ø 12, T2 ein
# Bohrer Ø 9. Oberseite, Lagerbohrung, Senkungen (Wand und Grund) und die Bohrungen darunter
# anklicken: „Bohren“ bohrt die zwei Ø 9; die Wände Ø 14 und Ø 30 fräst die Kontur oder „Bohrung
# fräsen“ (die schnellere); die Oberseite und die Gründe der Senkungen Planfräsen oder Räumen.
# Früher hatte die Kontur auch die gebohrten Ø 9 in ihrer Liste. „Anlegen“, „Auf der Maschine
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
    from camaddon import bohren as bh
    from camaddon import bohrung as bo
    from camaddon import bohrung_bahn as bb
    from camaddon import kontur as ko
    from camaddon import werkzeuge as wz

    t2 = wz.Werkzeug(nummer=2, art=wz.BOHRER, durchmesser=9.0, schneiden=2, schneidenlaenge=60.0,
                     spitzenwinkel=118.0, schneidstoff=wz.HSS)  # fmt: skip
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.1)]
    wz.Bibliothek([wz.standardwerkzeug(), t2]).speichern()

    doc = FreeCAD.newDocument("Lagerbock")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Lagerbock")
    form = Part.makeBox(100, 50, 30, V(0, 0, -30)).cut(Part.makeCylinder(15, 30, V(50, 25, -30)))
    for x in (15, 85):
        form = form.cut(Part.makeCylinder(7, 8.5, V(x, 25, -8.5)))
        form = form.cut(Part.makeCylinder(4.5, 30, V(x, 25, -30)))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    loecher = [b.name for b in bb.bohrungen(teil.Shape) if abs(b.radius - 4.5) < 1e-6]
    h.pruefe(len(loecher) == 2, f"Bohrungen Ø 9: {loecher}")
    auswahl = []
    for i, f in enumerate(teil.Shape.Faces):
        art = type(f.Surface).__name__
        z = f.CenterOfMass.z
        if art == "Cylinder" or (art == "Plane" and (abs(z) < 1e-6 or abs(z + 8.5) < 1e-6)):
            auswahl.append(f"Face{i + 1}")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, auswahl[0])
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    for name in auswahl[1:]:
        panel.flaeche_umschalten(name)
    yield 1000
    bohren, bohrung, kontur = panel.bohren, panel.bohrung, panel.kontur
    yield from h.warte_auf(
        lambda: all(b.vorschau is not None or not b.aktiv() for b in panel.bloecke), 300000
    )
    yield 3000
    h.pruefe(bohren.aktiv() and bohren.fraeser().nummer == 2, "Bohren: kein Haken oder nicht T2")
    h.pruefe(bohrung.aktiv() != kontur.aktiv(), "Wände: nicht genau eins von Bohrung/Kontur")
    h.pruefe(panel.raeumen.aktiv() or panel.plan.aktiv(), "Oberseite: kein Haken")
    rot = [(b.s.kennung, b.hinweis.text()) for b in panel.bloecke if b.aktiv() and b.hinweis.text()]
    h.pruefe(not rot, f"rot angehakt: {rot}")
    text = bohren.ergebnis.text()
    h.pruefe(text.startswith("→ 2 Bohrungen"), f"Bohren: {text!r}")
    h.bild("1_lagerbock", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 4000
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    h.pruefe(any(bh.ist_bohren(o) for o in ops), f"kein Bohren: {namen}")
    waende = [o for o in ops if bo.ist_bohrungsfraesen(o) or ko.ist_kontur(o)]
    h.pruefe(len(waende) == 1, f"Wände: {namen}")
    h.pruefe(
        all(name not in list(o.Flaechen) for o in waende for name in loecher),
        f"Wände mit den gebohrten Ø 9: {[list(o.Flaechen) for o in waende]}",
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
