# „3D-Schlichten“ an der Außenkante (P-2026-10-02-03): Ein Block 60 × 40, oben eine Welle
# (B-Spline, z 15 ± 4), ohne Platte daneben – T1 der Standardfräser Ø 12, T3 ein Kugelfräser
# Ø 6. Die Welle anklicken: „3D-Schlichten“ mit T3 angehakt, „→ …“ ohne roten Satz. Dort, wo
# die Kugel nur noch über die Außenkante rollt, fällt die Hüllfläche fast senkrecht; früher
# schnitten Höhenlinien und Spirale dort 0,05 mm in die Seite. „Anlegen“, die Richtung der
# Operation auf „spirale“ gestellt (die schnitt früher hinein), dann „Auf der Maschine prüfen“
# auf der 3-Achs-Fräse: am Ende „nirgends ins Teil“.
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

    doc = FreeCAD.newDocument("Welle")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    pole = [
        [V(i * 10.0, j * 10.0, 15.0 + 4.0 * math.sin(i * math.pi / 3) * math.cos(j * math.pi / 4))
         for j in range(5)]
        for i in range(7)
    ]  # fmt: skip
    flaeche = Part.BSplineSurface()
    flaeche.interpolate(pole)
    block = flaeche.toShape().extrude(V(0, 0, -30)).common(Part.makeBox(60, 40, 40))
    teil.Shape = block.removeSplitter()
    doc.recompute()
    welle = next(
        (
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if isinstance(f.Surface, Part.BSplineSurface)
        ),
        None,
    )
    if welle is None:
        h.pruefe(False, "keine B-Spline-Fläche")
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, welle)
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
    h.bild("1_welle", panel.form)

    # --- Anlegen, dann die Spirale --------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = [o for o in job.Operations.Group if s3op.ist_schlichten3d(o)]
    h.pruefe(len(ops) == 1, f"Operationen: {[o.Label for o in job.Operations.Group]}")
    if not ops:
        return
    op = ops[0]
    op.Richtung = "spirale"
    doc.recompute()
    yield 1000
    h.pruefe(op.Umlaeufe > 10 and len(op.Path.Commands) > 100, f"Spirale: {op.Umlaeufe}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_spirale")

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
