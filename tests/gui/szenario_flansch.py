# Ein Flansch auf der 3-Achs-Fräse (P-2026-10-02-12): Scheibe Ø 100 × 15, Mittelbohrung Ø 40, sechs
# Bohrungen Ø 9 auf dem Lochkreis Ø 70; T1 der Standardfräser Ø 12, T2 ein Bohrer Ø 9. Oberseite,
# Außenwand, Mittelbohrung und alle sechs Lochkreisbohrungen anklicken. Früher bot der Assistent
# „Bohren“ gar nicht an (der Bohrer bohrt die Ø 40 nicht), und „Bohrung fräsen“ stand rot („Ø 9
# kleiner als der Fräser“) – „Anlegen“ ging nicht. Jetzt teilen sie sich die Bohrungen: „Bohren“
# mit T2 die sechs Ø 9, „Bohrung fräsen“ mit T1 die Ø 40, die Kontur die Außenwand, Planfräsen oder
# Räumen die Oberseite – kein roter Satz. „Anlegen“ legt sie alle an; „Auf der Maschine prüfen“:
# am Ende nirgends ins Teil.
import math

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
    from camaddon import hoehenfeld as hf
    from camaddon import kontur as ko
    from camaddon import werkzeuge as wz

    t2 = wz.Werkzeug(nummer=2, art=wz.BOHRER, durchmesser=9.0, schneiden=2, schneidenlaenge=60.0,
                     spitzenwinkel=118.0, schneidstoff=wz.HSS)  # fmt: skip
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.1)]
    wz.Bibliothek([wz.standardwerkzeug(), t2]).speichern()

    doc = FreeCAD.newDocument("Flansch")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Flansch")
    form = Part.makeCylinder(50, 15, V(0, 0, -15)).cut(Part.makeCylinder(20, 15, V(0, 0, -15)))
    for k in range(6):
        w = math.radians(60 * k)
        form = form.cut(Part.makeCylinder(4.5, 15, V(35 * math.cos(w), 35 * math.sin(w), -15)))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    loecher = [b.name for b in bb.bohrungen(teil.Shape) if abs(b.radius - 4.5) < 1e-6]
    mitte = next(b.name for b in bb.bohrungen(teil.Shape) if abs(b.radius - 20.0) < 1e-6)
    oben = next(e.name for e in hf.ebenen_oben(teil.Shape) if abs(e.z) < 1e-6)
    aussen = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 50.0) < 1e-6
    )
    h.pruefe(len(loecher) == 6, f"Lochkreis: {loecher}")
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
    for name in [aussen, mitte, *loecher]:
        panel.flaeche_umschalten(name)
    yield 1000
    bohren, bohrung, kontur = panel.bohren, panel.bohrung, panel.kontur
    yield from h.warte_auf(
        lambda: all(b.vorschau is not None for b in (bohren, bohrung, kontur)), 240000
    )
    yield 2000
    h.pruefe(bohren.aktiv() and bohren.fraeser().nummer == 2, "Bohren: kein Haken oder nicht T2")
    h.pruefe(bohrung.aktiv() and bohrung.fraeser().nummer == 1, "Bohrung fräsen: kein Haken")
    h.pruefe(kontur.aktiv(), "Kontur: kein Haken")
    h.pruefe(panel.plan.aktiv() or panel.raeumen.aktiv(), "Oberseite: kein Haken")
    rot = [(b.s.kennung, b.hinweis.text()) for b in panel.bloecke if b.aktiv() and b.hinweis.text()]
    h.pruefe(not rot, f"rot: {rot}")
    text = bohren.ergebnis.text()
    h.pruefe(text.startswith("→ 6 Bohrungen, 6 Hübe, "), f"Bohren: {text!r}")
    text = bohrung.ergebnis.text()
    h.pruefe(text.startswith("→ 1 Bohrung"), f"Bohrung fräsen: {text!r}")
    h.bild("1_flansch", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 4000
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    h.pruefe(any(bh.ist_bohren(o) for o in ops), f"kein Bohren: {namen}")
    fraesen = [o for o in ops if bo.ist_bohrungsfraesen(o)]
    h.pruefe(fraesen and list(fraesen[0].Flaechen) == [mitte], f"Bohrung fräsen: {namen}")
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
