# Eine Mulde in einer Platte (W-006 4.2, Formenbau): Platte 80 × 80 × 20, darin eine
# Kugelmulde R 30 (12 tief, Rand Ø 48) – T1 der Standardfräser Ø 12, T3 ein Kugelfräser Ø 6.
# Die Mulde anklicken: „3D-Schruppen“ mit T1 und „3D-Schlichten“ mit T3 angehakt, beide „→ …“
# ohne roten Satz (die Mulde ist geschlossen: das Schruppen geht in Treppen von oben nach unten,
# nie ins volle Material in voller Breite). „Anlegen“: „3D-Schruppen T1“ und „3D-Schlichten
# T3“. „Auf der Maschine prüfen“ auf der 3-Achs-Fräse: am Ende „nirgends ins Teil“ – auch am
# Rand der Mulde, wo die Kugel über die Kante zur Oberseite rollt.
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
    from camaddon import schlichten3d as s3op
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

    doc = FreeCAD.newDocument("Mulde")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    teil.Shape = Part.makeBox(80, 80, 20).cut(Part.makeSphere(30, V(40, 40, 38))).removeSplitter()
    doc.recompute()
    mulde = next(
        (
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if isinstance(f.Surface, Part.Sphere)
        ),
        None,
    )
    if mulde is None:
        h.pruefe(False, "keine Kugelfläche")
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, mulde)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    block3d = panel.schlichten3d
    yield from h.warte_auf(lambda: block3d.vorschau is not None, 180000)
    yield 800
    h.pruefe(block3d.aktiv(), "3D-Schlichten ohne Haken")
    h.pruefe(block3d.fraeser() is not None and block3d.fraeser().nummer == 3, "nicht T3")
    text = block3d.ergebnis.text()
    h.pruefe(text.startswith("→ ") and ", Abstand 0,49, etwa " in text, f"3D-Schlichten: {text!r}")
    h.pruefe(not block3d.hinweis.text(), f"rot: {block3d.hinweis.text()!r}")
    # Ohne 5-Achs-Maschine gibt es den Haken „Anstellen“ nicht (er wäre nur Rauschen).
    h.pruefe(block3d.haken_felder["anstellen"].isHidden(), "„Anstellen“ an der 3-Achs-Fräse")
    schruppen = panel.schruppen3d
    yield from h.warte_auf(lambda: schruppen.vorschau is not None, 180000)
    h.pruefe(schruppen.aktiv(), "3D-Schruppen ohne Haken")
    h.pruefe(schruppen.fraeser() is not None and schruppen.fraeser().nummer == 1, "nicht T1")
    text = schruppen.ergebnis.text()
    h.pruefe(text.startswith("→ ") and " Ringe, etwa " in text, f"3D-Schruppen: {text!r}")
    h.pruefe(not schruppen.hinweis.text(), f"rot: {schruppen.hinweis.text()!r}")
    h.bild("1_mulde", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    namen = [o.Label for o in job.Operations.Group]
    h.pruefe(namen == ["3D-Schruppen T1", "3D-Schlichten T3"], f"Operationen: {namen}")
    ops = [o for o in job.Operations.Group if s3op.ist_schlichten3d(o)]
    h.pruefe(ops and len(ops[0].Path.Commands) > 100, "3D-Schlichten ohne Bahn")
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
