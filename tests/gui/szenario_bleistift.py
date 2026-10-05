# „Bearbeitung (Fräsen)“ mit „Bleistift“ (W-006 4.2 Punkt 6): Platte 60 × 60 × 10 mit einer Kuppel
# (Kugel R 25, Fuß Ø 40, oben z 20); T1 der Standardfräser Ø 12, T3 ein Kugelfräser Ø 6. Die
# Kuppel anklicken: „3D-Schruppen“ und „3D-Schlichten“ angehakt, „Bleistift“ nicht – den Haken
# setzt man selbst. Angehakt: T3 vorgewählt, „→ 1 Kehle, 135 mm lang, etwa … min“ (der Ring am
# Fuß der Kuppel, wo die Kugel Platte und Kuppel zugleich berührt). „Anlegen“: „3D-Schruppen T1“,
# „3D-Schlichten T3“, „Bleistift T3“. „Auf der Maschine prüfen“: am Ende nirgends ins Teil.
# Mit „Breite je Seite“ 1,5: vier Bahnen je Seite neben der Kehle, neun Ringe.
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
    from camaddon import bleistift as bsop
    from camaddon import werkzeuge as wz

    t3 = wz.Werkzeug(
        nummer=3,
        name="Kugel 6",
        art=wz.KUGELFRAESER,
        durchmesser=6.0,
        schneiden=2,
        schneidenlaenge=12.0,
        schneidstoff=wz.VHM,
    )
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
    wz.Bibliothek([wz.standardwerkzeug(), t3]).speichern()

    doc = FreeCAD.newDocument("Kehle")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    kappe = Part.makeSphere(25, V(30, 30, -5)).common(Part.makeBox(60, 60, 15, V(0, 0, 10)))
    teil.Shape = Part.makeBox(60, 60, 10).fuse(kappe).removeSplitter()
    doc.recompute()
    kuppel = next(
        (
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if isinstance(f.Surface, Part.Sphere)
        ),
        None,
    )
    if kuppel is None:
        h.pruefe(False, "keine Kugelfläche")
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, kuppel)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    for block in (panel.schruppen3d, panel.schlichten3d):
        yield from h.warte_auf(lambda b=block: b.vorschau is not None, 180000)
    bleistift = panel.bleistift
    h.pruefe(
        panel.schruppen3d.aktiv() and panel.schlichten3d.aktiv() and not bleistift.aktiv(),
        "Haken: 3D-Schruppen und 3D-Schlichten von sich aus, Bleistift nicht",
    )
    bleistift.haken.setChecked(True)  # wie ein Klick: der Haken von Hand
    yield from h.warte_auf(lambda: bleistift.vorschau is not None, 180000)
    yield 800
    h.pruefe(bleistift.fraeser() is not None and bleistift.fraeser().nummer == 3, "nicht T3")
    text = bleistift.ergebnis.text()
    h.pruefe(text.startswith("→ 1 Kehle, 13") and " mm lang, etwa " in text, f"Bleistift: {text!r}")
    h.pruefe(not bleistift.hinweis.text(), f"rot: {bleistift.hinweis.text()!r}")
    h.bild("1_bleistift", panel.form)
    # Breite je Seite 1,5 mm: vier Bahnen je Seite im Abstand 0,49 (Grat 0,01) – neun Ringe.
    bleistift.felder["breite"].setText("1,5")
    yield from h.warte_auf(lambda: bleistift.ergebnis.text() != text, 180000)
    yield from h.warte_auf(lambda: bleistift.vorschau is not None, 180000)
    yield 800
    breit = bleistift.vorschau
    h.pruefe(
        breit is not None and breit.bahnen == 9 and breit.laenge > 8 * 130.0,
        f"Breite 1,5: {breit and breit.bahnen} Bahnen, {breit and breit.laenge:.0f} mm – "
        f"{bleistift.ergebnis.text()!r}",
    )
    h.bild("1b_bleistift_breit", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = list(job.Operations.Group)
    h.pruefe(
        [o.Label for o in ops] == ["3D-Schruppen T1", "3D-Schlichten T3", "Bleistift T3"]
        and bsop.ist_bleistift(ops[-1]),
        f"Operationen: {[o.Label for o in ops]}",
    )
    if ops:
        h.pruefe(
            ops[-1].Linien == 1 and ops[-1].BahnenJeSeite == 4,
            f"Kehlen: {ops[-1].Linien}, je Seite {ops[-1].BahnenJeSeite}",
        )
    Gui.Selection.clearSelection()
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
    fahrt = spieler.abfahrt
    spieler.setze_zeit(fahrt.dauer)
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
