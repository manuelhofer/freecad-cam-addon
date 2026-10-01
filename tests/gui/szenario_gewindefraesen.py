# „Bearbeitung (Fräsen)“ mit „Gewinde fräsen“ (W-006 S3g): Platte 100 × 60 × 12 mit zwei
# durchgehenden Kernlöchern Ø 8,5 bei (25, 30) und (75, 30); T1 der Standardfräser Ø 12, T2 ein
# Bohrer Ø 8,5, T4 ein Gewindebohrer M10 × 1,5, T7 ein Gewindefräser Ø 8 mit Steigung 1,5 und
# 15 mm Zähnen (zehn übereinander). Beide Wände anklicken: Bohren mit T2 bekommt den Haken;
# Gewinde bohren (T4) und Gewinde fräsen (T7) sind möglich, ohne Haken. Gewinde bohren anhaken,
# dann Gewinde fräsen: Gewinde bohren verliert den Haken (zwei Gänge in einer Bohrung gingen
# nicht). „→ 2 × M10x1.5, 2 Umläufe, etwa …“ – ein Umlauf je Gewinde, die Zähne fräsen alle
# Gänge auf einmal. „Anlegen“: „Bohren T2“, „Gewinde fräsen T7“ (G3 mit Z, der Vorschub der
# Mitte ein Fünftel von dem an der Schneide). Doppelklick: Gegenlauf – G2. „Auf der Maschine
# prüfen“: am Ende nirgends ins Teil – das Gewinde darf in seinem Ring ins Teil.
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
    from camaddon import gewindefraesen as gf
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    t2 = wz.Werkzeug(
        nummer=2,
        name="HSS 8.5",
        art=wz.BOHRER,
        durchmesser=8.5,
        schneiden=2,
        schneidenlaenge=60.0,
        spitzenwinkel=118.0,
        schneidstoff=wz.HSS,
    )
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.08)]
    t4 = wz.Werkzeug(
        nummer=4,
        name="M10",
        art=wz.GEWINDEBOHRER_RECHTS,
        durchmesser=10.0,
        steigung=1.5,
        schneiden=3,
        schneidenlaenge=20.0,
        schneidstoff=wz.HSS,
    )
    t4.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.GEWINDEBOHREN, vc=8.0)]
    t7 = wz.Werkzeug(
        nummer=7,
        name="GF 8 P1.5",
        art=wz.GEWINDEFRAESER,
        durchmesser=8.0,
        schneiden=3,
        steigung=1.5,
        schneidenlaenge=15.0,
        hals_d=6.0,
        hals_laenge=10.0,
        schaft=8.0,
        schneidstoff=wz.VHM,
    )
    t7.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.GEWINDEFRAESEN, vc=80.0, fz=0.05)]
    wz.Bibliothek([t1, t2, t4, t7]).speichern()

    doc = FreeCAD.newDocument("Gewindefraesen")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    form = Part.makeBox(100, 60, 12)
    for x in (25.0, 75.0):
        form = form.cut(Part.makeCylinder(4.25, 12, V(x, 30, 0)))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    kerne = [b.name for b in bb.bohrungen(teil.Shape)]
    if len(kerne) != 2:
        h.pruefe(False, f"Kernlöcher: {kerne}")
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, kerne[0])
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    panel.flaeche_umschalten(kerne[1])
    bohren, gewinde, fraesen = panel.bohren, panel.gewinde, panel.gewindefraesen
    yield from h.warte_auf(lambda: bohren.vorschau is not None, 60000)
    yield 1500
    h.pruefe(bohren.aktiv() and bohren.fraeser().nummer == 2, "Bohren: nicht an oder nicht T2")
    h.pruefe(gewinde.moeglich and not gewinde.aktiv(), "Gewinde bohren: nicht möglich oder an")
    h.pruefe(fraesen.moeglich and not fraesen.aktiv(), "Gewinde fräsen: nicht möglich oder an")
    h.pruefe(fraesen.fraeser() is not None and fraesen.fraeser().nummer == 7, "nicht T7")

    # Gewinde bohren an, dann Gewinde fräsen: nur eins von beiden.
    gewinde.haken.setChecked(True)
    yield from h.warte_auf(lambda: gewinde.vorschau is not None, 60000)
    fraesen.haken.setChecked(True)
    yield from h.warte_auf(lambda: fraesen.vorschau is not None, 60000)
    yield 300
    h.pruefe(fraesen.aktiv() and not gewinde.aktiv(), "Gewinde bohren behält den Haken")
    h.pruefe(not fraesen.hinweis.text(), f"rot: {fraesen.hinweis.text()!r}")
    text = fraesen.ergebnis.text()
    h.pruefe(
        text.startswith("→ 2 × M10x1.5, 2 Umläufe, etwa ") and " – " not in text,
        f"Gewinde fräsen: {text!r}",
    )
    h.bild("1_gewindefraesen", panel.form)

    # --- Anlegen: Bohren, dann Gewinde fräsen -----------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 2500
    ops = list(job.Operations.Group)
    h.pruefe(
        [o.Label for o in ops] == ["Bohren T2", "Gewinde fräsen T7"]
        and bh.ist_bohren(ops[0])
        and gf.ist_gewindefraesen(ops[1]),
        f"Operationen: {[o.Label for o in ops]}",
    )
    if len(ops) < 2:
        return
    op = ops[1]
    h.pruefe(op.Gewinde == "2 × M10x1.5" and op.Zaehne == 10, f"{op.Gewinde!r}, {op.Zaehne}")
    befehle = [c for c in op.Path.Commands if c.Name in ("G2", "G3")]
    h.pruefe(
        befehle and all(c.Name == "G3" for c in befehle), f"{sorted({c.Name for c in befehle})}"
    )
    vf = float(op.ToolController.HorizFeed.getValueAs("mm/min"))
    f_helix = max(c.Parameters["F"] for c in befehle) * 60.0
    h.pruefe(0.15 * vf < f_helix < 0.25 * vf, f"Helix F {f_helix:.0f} bei vf {vf:.0f}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_angelegt")

    # --- Ändern: Doppelklick, Gegenlauf ------------------------------------------------------
    op.ViewObject.Proxy.doubleClicked(op.ViewObject)
    yield 1000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.zu_aendern is op, "Doppelklick öffnet nichts")
    if panel is None:
        return
    fraesen = panel.gewindefraesen
    h.pruefe(panel.block_zu_aendern is fraesen, "beim Ändern: nicht der Block Gewinde fräsen")
    yield from h.warte_auf(lambda: fraesen.vorschau is not None, 30000)
    fraesen.haken_felder["gleichlauf"].setChecked(False)
    yield from h.warte_auf(lambda: fraesen.vorschau is not None, 30000)
    h.pruefe(panel.accept() is True, "„Übernehmen“ ging nicht")
    yield 1500
    namen = {c.Name for c in op.Path.Commands}
    h.pruefe(
        op.Gleichlauf is False and "G2" in namen and "G3" not in namen,
        f"nach dem Ändern: Gleichlauf {op.Gleichlauf}, {sorted(namen)}",
    )

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
    h.bild("3_pruefen_farben")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
