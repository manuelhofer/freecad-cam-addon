# „Bearbeitung (Fräsen)“ mit „Bohren“ (W-006 S3g): FreeCADs Bohr-Operation mit einem Bohrer aus der
# Werkzeugverwaltung, im Wettbewerb mit „Bohrung fräsen“ und „Kontur“ (Grundsatz 0). Block
# 100 × 60 × 20 mit einer durchgehenden Bohrung Ø 20 bei (25, 30) und einer Sackbohrung Ø 34 × 10;
# T1 der Standardfräser Ø 12, T2 ein Bohrer Ø 20. Die Wand der durchgehenden Bohrung anklicken:
# Bohren (mit T2 – dem Bohrer mit ihrem Durchmesser), Bohrung fräsen und Kontur rechnen alle drei –
# Bohren ist am schnellsten, behält den Haken und sagt es; die beiden anderen verlieren ihn: „… –
# N % langsamer als Bohren“. Die Sackbohrung dazu: Bohren bleibt für die durchgehende (die
# Sackbohrung mit ebenem Grund kann ein Bohrer nicht), Bohrung fräsen bekommt den Haken für die
# Sackbohrung, die Kontur nicht (P-2026-10-02-12). Wieder nur die durchgehende: „Anlegen“ legt
# FreeCADs Bohren an – „Bohren T2“ mit G81. „Auf der Maschine prüfen“: am Ende nirgends ins Teil.
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
    from camaddon import bohrung_bahn as bb
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    t2 = wz.Werkzeug(
        nummer=2,
        name="HSS 20",
        art=wz.BOHRER,
        durchmesser=20.0,
        schneiden=2,
        schneidenlaenge=140.0,
        spitzenwinkel=118.0,
        schneidstoff=wz.HSS,
    )
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.1)]
    wz.Bibliothek([t1, t2]).speichern()

    doc = FreeCAD.newDocument("Bohren")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    form = Part.makeBox(100, 60, 20)
    form = form.cut(Part.makeCylinder(10, 20, V(25, 30, 0)))
    form = form.cut(Part.makeCylinder(17, 10, V(70, 30, 10)))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    namen = {round(b.radius, 6): b.name for b in bb.bohrungen(teil.Shape)}
    durch, sack = namen.get(10.0), namen.get(17.0)
    if durch is None or sack is None:
        h.pruefe(False, f"Bohrungen: {namen}")
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, durch)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    bohren, bohrung, kontur = panel.bohren, panel.bohrung, panel.kontur
    h.pruefe(bohren.fraeser() is not None and bohren.fraeser().nummer == 2, "Bohren: nicht T2")
    h.pruefe(bohrung.fraeser() is not None and bohrung.fraeser().nummer == 1, "Bohrung: nicht T1")
    yield from h.warte_auf(
        lambda: bohren.vorschau is not None
        and bohrung.vorschau is not None
        and kontur.vorschau is not None,
        60000,
    )
    yield 300
    h.pruefe(not bohren.hinweis.text(), f"rot: {bohren.hinweis.text()!r}")
    h.pruefe(
        bohren.aktiv() and not bohrung.aktiv() and not kontur.aktiv(),
        "Haken: Bohren an, Bohrung fräsen und Kontur aus",
    )
    text = bohren.ergebnis.text()
    h.pruefe(text.startswith("→ 1 Bohrung, 1 Hub, "), f"Bohren: {text!r}")
    h.pruefe("– die schnellste; Bohrung fräsen wäre" in text, f"Bohren: {text!r}")
    for block in (bohrung, kontur):
        h.pruefe(
            block.ergebnis.text().endswith("% langsamer als Bohren"),
            f"{block.s.titel()}: {block.ergebnis.text()!r}",
        )
    h.bild("1_bohren", panel.form)

    # Die Sackbohrung dazu: Bohren bleibt für die durchgehende, Bohrung fräsen bekommt den Haken
    # für die Sackbohrung, die Kontur nicht.
    panel.flaeche_umschalten(sack)
    yield from h.warte_auf(
        lambda: bohrung.vorschau is not None and bohren.vorschau is not None, 60000
    )
    yield 300
    h.pruefe(bohren.moeglich and bohren.aktiv(), "mit Sackbohrung: Bohren ohne Haken")
    h.pruefe(bohrung.aktiv(), "mit Sackbohrung: Bohrung fräsen ohne Haken")
    h.pruefe(not kontur.aktiv(), "mit Sackbohrung: Kontur mit Haken")
    h.pruefe(
        panel._flaechen(bohren, vr.modell(job).Shape) == [durch]
        and panel._flaechen(bohrung, vr.modell(job).Shape) == [sack],
        "mit Sackbohrung: Bohrungen nicht aufgeteilt",
    )
    text = bohrung.ergebnis.text()
    h.pruefe(text.startswith("→ 1 Bohrung"), f"Bohrung fräsen: {text!r}")
    h.bild("2_mit_sackbohrung", panel.form)
    panel.flaeche_umschalten(sack)
    yield from h.warte_auf(lambda: bohren.vorschau is not None, 60000)
    yield 300
    h.pruefe(bohren.aktiv() and not bohrung.aktiv(), "wieder ohne Sackbohrung: Haken")

    # --- Anlegen: FreeCADs „Bohren T2“ ------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 2000
    ops = list(job.Operations.Group)
    h.pruefe(len(ops) == 1 and bh.ist_bohren(ops[0]), f"Operationen: {[o.Label for o in ops]}")
    if not ops:
        return
    op = ops[0]
    h.pruefe(op.Label == "Bohren T2", f"Name: {op.Label}")
    zyklen = [c for c in op.Path.Commands if c.Name in ("G81", "G83")]
    h.pruefe(len(zyklen) == 1 and zyklen[0].Name == "G81", f"Zyklen: {[c.Name for c in zyklen]}")
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
