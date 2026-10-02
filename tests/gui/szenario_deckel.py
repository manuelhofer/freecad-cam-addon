# Ein Deckel auf der 3-Achs-Fräse (P-2026-10-02-13): Platte 120 × 80 × 15, in der Mitte eine
# Tasche 80 × 40 × 8 mit Ecken R 6, in den Ecken vier Bohrungen Ø 6,6 durch; T1 der
# Standardfräser Ø 12, T2 ein Bohrer Ø 6,6. Alle Flächen außer der Unterseite anklicken. Früher
# blieb „Bohrung fräsen“ rot angehakt („Ø 6,6 kleiner als der Fräser“), obwohl „Bohren“ die vier
# Bohrungen bohrt – „Anlegen“ ging nicht. Jetzt verliert es den Haken (der rote Satz erklärt,
# warum); „Räumen“ (Oberseite und Taschenboden), „Bohren“ und „Kontur“ sind angehakt. „Anlegen“:
# „Räumen T1“, „Bohren T2“, „Kontur T1“. „Auf der Maschine prüfen“: am Ende nirgends ins Teil.
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

    t2 = wz.Werkzeug(nummer=2, art=wz.BOHRER, durchmesser=6.6, schneiden=2, schneidenlaenge=60.0,
                     spitzenwinkel=118.0, schneidstoff=wz.HSS)  # fmt: skip
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.1)]
    wz.Bibliothek([wz.standardwerkzeug(), t2]).speichern()

    doc = FreeCAD.newDocument("Deckel")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Deckel")
    tasche = Part.makeBox(80, 40, 8, V(20, 20, -8))
    senkrecht = [k for k in tasche.Edges if abs(k.Vertexes[0].Z - k.Vertexes[1].Z) > 1]
    form = Part.makeBox(120, 80, 15, V(0, 0, -15)).cut(tasche.makeFillet(6, senkrecht))
    for x, y in ((8, 8), (112, 8), (8, 72), (112, 72)):
        form = form.cut(Part.makeCylinder(3.3, 15, V(x, y, -15)))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    loecher = [b.name for b in bb.bohrungen(teil.Shape) if abs(b.radius - 3.3) < 1e-6]
    h.pruefe(len(loecher) == 4, f"Bohrungen: {loecher}")
    flaechen = teil.Shape.Faces
    auswahl = [
        f"Face{i + 1}"
        for i, f in enumerate(flaechen)
        if not (abs(f.CenterOfMass.z + 15) < 1e-6 and f.normalAt(0, 0).z < 0)
    ]
    oben = auswahl[0]
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
    for name in auswahl[1:]:
        panel.flaeche_umschalten(name)
    yield 1000
    bohren, bohrung, kontur = panel.bohren, panel.bohrung, panel.kontur
    yield from h.warte_auf(
        lambda: all(b.vorschau is not None or not b.aktiv() for b in panel.bloecke), 300000
    )
    yield 3000
    h.pruefe(bohren.aktiv() and bohren.fraeser().nummer == 2, "Bohren: kein Haken oder nicht T2")
    h.pruefe(not bohrung.aktiv(), "Bohrung fräsen: rot angehakt")
    h.pruefe(kontur.aktiv(), "Kontur: kein Haken")
    h.pruefe(panel.raeumen.aktiv() or panel.plan.aktiv(), "Oberseite: kein Haken")
    rot = [(b.s.kennung, b.hinweis.text()) for b in panel.bloecke if b.aktiv() and b.hinweis.text()]
    h.pruefe(not rot, f"rot angehakt: {rot}")
    text = bohren.ergebnis.text()
    h.pruefe(text.startswith("→ 4 Bohrungen, 4 Hübe, "), f"Bohren: {text!r}")
    h.bild("1_deckel", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 4000
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    h.pruefe(any(bh.ist_bohren(o) for o in ops), f"kein Bohren: {namen}")
    h.pruefe(not any(bo.ist_bohrungsfraesen(o) for o in ops), f"Bohrung fräsen: {namen}")
    h.pruefe(any(ko.ist_kontur(o) for o in ops), f"keine Kontur: {namen}")
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
