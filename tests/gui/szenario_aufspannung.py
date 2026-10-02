# Die Aufspannung im Assistenten „Bearbeitung (Fräsen)“ (P-2026-10-02-43; Manuel, 2026-10-02:
# „man klickt auf eine Fläche, welche dann sozusagen unten ist, und man da dann ein Rohteil
# rausbekommt. Fehlt somit nur noch die X- und Y-Achse – aber das muss sein“): eine Platte
# 200 × 100 × 30 mit Zapfen Ø 20, 20 hoch – modelliert auf der Seite stehend (die Dicke längs X,
# der Zapfen zeigt nach +X). Ein Klick auf eine Fläche nimmt sie zur Bearbeitung dazu; erst nach
# „Fläche anklicken …“ macht er sie zur Unterseite – die Fläche bei x = 0: Das Teil im Job
# dreht sich so, dass sie unten liegt – flach, 50 hoch mit dem Zapfen, der nach oben zeigt; das
# Rohteil folgt. „↺ 90°“ dreht X: Länge und Breite tauschen. „Wie modelliert“ dreht zurück. In
# Schritt 2 gilt die Oberseite in der neuen Lage (Höhe 30 über der Unterseite).
import FreeCAD
import FreeCADGui as Gui
import Part

V = FreeCAD.Vector


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import gui_bearbeitung
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()

    doc = FreeCAD.newDocument("Aufspannung")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    platte = Part.makeBox(30, 200, 100)
    zapfen = Part.makeCylinder(10, 20, V(30, 150, 50), V(1, 0, 0))
    teil.Shape = platte.fuse(zapfen).removeSplitter()
    doc.recompute()
    unten = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if abs(f.BoundBox.XMax) < 1e-6 and abs(f.BoundBox.XMin) < 1e-6
    )
    oben_im_modell = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if abs(f.BoundBox.ZMin - 100) < 1e-6 and f.BoundBox.ZLength < 1e-6
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, oben_im_modell)
    yield 500
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    klon = vr.modell(panel.job)
    vorher = klon.Shape.BoundBox
    h.pruefe(abs(vorher.ZLength - 100) < 1e-6, f"modelliert: {vorher.ZLength}")
    # Ohne den Knopf nimmt ein Klick die Fläche zur Bearbeitung dazu – das Teil bleibt liegen.
    h.pruefe(panel.seite() == 0, f"Schritt {panel.seite() + 1}")
    panel.angeklickt(teil.Name, unten)
    yield 300
    h.pruefe(abs(klon.Shape.BoundBox.ZLength - 100) < 1e-6, "ohne Knopf gedreht")
    panel.flaeche_umschalten(unten)  # wieder heraus
    # „Fläche anklicken …“, dann die Fläche: sie liegt unten.
    panel.knopf_unten_waehlen.click()
    panel.angeklickt(teil.Name, unten)
    yield 800
    bb = klon.Shape.BoundBox
    h.pruefe(abs(bb.ZLength - 50) < 1e-6, f"liegt nicht flach: Höhe {bb.ZLength:.3f}")
    h.pruefe(unten in panel.unten_text.text(), f"Unten: {panel.unten_text.text()!r}")
    h.pruefe(unten not in panel.flaechen(), "die Unterseite ist gewählt")
    zapfen_oben = max(f.BoundBox.ZMax for f in klon.Shape.Faces)
    h.pruefe(abs(zapfen_oben - bb.ZMax) < 1e-6, "der Zapfen zeigt nicht nach oben")
    stock = panel.job.Stock.Shape.BoundBox
    h.pruefe(
        abs(stock.ZLength - 52) < 1e-6 and abs(stock.XLength - bb.XLength - 2) < 1e-6,
        f"Rohteil folgt nicht: {stock.XLength:.1f} × {stock.YLength:.1f} × {stock.ZLength:.1f}",
    )
    laenge, breite = bb.XLength, bb.YLength
    h.bild("1_unten_gewaehlt", panel.form)
    h.bild("1b_flach")
    # X um 90° drehen: Länge und Breite tauschen.
    panel.knopf_x_links.click()
    yield 800
    bb = klon.Shape.BoundBox
    h.pruefe(
        abs(bb.XLength - breite) < 1e-6 and abs(bb.YLength - laenge) < 1e-6,
        f"X gedreht: {bb.XLength:.1f} × {bb.YLength:.1f}",
    )
    h.pruefe("90" in panel.x_text.text(), f"X: {panel.x_text.text()!r}")
    h.bild("2_x_gedreht")
    # Schritt 2: die Oberseite in der neuen Lage.
    panel.knopf_weiter.click()
    yield 300
    panel.oberseite_waehlen()
    yield from h.warte_auf(lambda: panel.raeumen.vorschau is not None, 120000)
    yield 500
    zeile = panel.flaechen_liste.item(0).text() if panel.flaechen_liste.count() else ""
    h.pruefe("eben nach oben" in zeile, f"Oberseite: {zeile!r}")
    h.pruefe(not panel.raeumen.hinweis.text(), f"rot: {panel.raeumen.hinweis.text()!r}")
    h.bild("3_was_soll_weg", panel.form)
    # Zurück und „Wie modelliert“: wieder hochkant.
    panel.knopf_zurueck.click()
    yield 300
    panel.knopf_unten_modell.click()
    panel.knopf_x_rechts.click()
    yield 800
    bb = klon.Shape.BoundBox
    h.pruefe(abs(bb.ZLength - 100) < 1e-6, f"zurück: Höhe {bb.ZLength:.3f}")
    panel.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
