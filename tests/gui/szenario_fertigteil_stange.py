# „Fertigteil als Rohteil“ an der Stange (W-029, 4 Achsen): Welle Ø 40 × 40 mit Abflachung (16 von
# der Achse), Stange Ø 44, auf der Beispiel-Drehmaschine, T1 Schaftfräser Ø 12 radial. „Rundum
# schruppen“ über alles (Aufmaß 0,3), sonst nichts. Der Befehl im Menü verweist für diesen Job aufs
# Prüffenster – mit dem Knopf „Auf der Maschine prüfen“. Dort vor dem Ende kein Knopf
# „Fertigteil als Rohteil …“; am Ende steht er da. Geklickt: „Welle – Aufspannung 1 – Fertigteil“
# im Dokument, gültig, ein Körper; die Welle liegt ganz darin; an ihrer Rückseite abgestochen
# (nicht länger als sie und das Planaufmaß – die Stange war 107 lang); kleiner als die Stange, kaum
# größer als die Welle (Aufmaß 0,3, vorn 1 mm Planaufmaß); über der Abflachung steht nichts mehr;
# die Meldung nennt das Raster der Stange und das Abstechen.
# ZEITLIMIT: 900
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_fertigteil, gui_reichweite, gui_vierachs
    from camaddon import fertigteil as ft
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    bibliothek = wz.Bibliothek()
    halter = bibliothek.neuer_halter("vdi30_radial")
    t1 = bibliothek.neues_werkzeug()
    t1.nummer, t1.durchmesser, t1.schneiden, t1.schneidenlaenge = 1, 12.0, 3, 26.0
    t1.laenge_spindelnase, t1.halter = 125.0, halter.kennung
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=150, fz=0.08)]
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300

    doc = FreeCAD.newDocument("Abflachung")
    doc.saveAs(os.path.join(tempfile.mkdtemp(), "welle.FCStd"))
    teil = doc.addObject("Part::Feature", "Welle")
    welle = Part.makeCylinder(20, 40, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0))
    welle = welle.cut(Part.makeBox(24, 40, 10, FreeCAD.Vector(8, -20, 16)))
    teil.Shape = welle.removeSplitter()
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f) and (vr.aussennormale(f) - FreeCAD.Vector(1, 0, 0)).Length < 1e-9
    )
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500
    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.feld_stange.setText("44")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.accept()  # Weiter
    yield 300
    panel.mit_schlichten.setChecked(False)
    for haken in ("mit_plan", "mit_entgraten"):
        kasten = getattr(panel, haken, None)
        if kasten is not None:
            kasten.setChecked(False)
    yield 500
    yield from h.warte_auf(lambda: panel.vorschau is not None and not panel.rechnet_noch(), 120000)
    job = panel.job
    panel.accept()  # Anlegen
    yield 1500
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    h.pruefe(len(ops) == 1, f"Operationen: {[o.Label for o in job.Operations.Group]}")

    # Der Befehl im Menü verweist für die Stange aufs Prüffenster – mit dem Knopf dorthin.
    FreeCAD.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_Fertigteil"))
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 10000)
    meldung = h.modal()
    text = meldung.text() if isinstance(meldung, QtGui.QMessageBox) else ""
    knoepfe = meldung.buttons() if isinstance(meldung, QtGui.QMessageBox) else []
    pruefen = next((k for k in knoepfe if k.text() == "Auf der Maschine prüfen"), None)
    h.pruefe("Auf der Maschine prüfen" in text and pruefen is not None, f"Verweis: {text!r}")
    h.bild("1_verweis", meldung)
    if pruefen is not None:
        pruefen.click()
    elif isinstance(meldung, QtGui.QMessageBox):
        meldung.reject()
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 60000)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "der Knopf öffnet „Auf der Maschine prüfen“ nicht")
    if pruef is None:
        return
    yield from h.warte_auf(lambda: pruef.abspieler.abfahrt is not None, 120000)
    yield 800
    spieler = pruef.abspieler
    knopf = spieler.knopf_fertigteil
    h.pruefe(not knopf.isVisible(), "„Fertigteil als Rohteil“ schon vor dem Ende")
    spieler.setze_zeit(spieler.abfahrt.dauer)
    yield from h.warte_auf(
        lambda: not pruef.bild.abtrag_rechnet() and "rechnet" not in spieler.rest.text(), 300000
    )
    yield 800
    h.pruefe(knopf.isVisible(), f"am Ende kein Knopf: {spieler.rest.text()!r}")
    h.bild("2_am_ende", pruef.form)
    QtCore.QTimer.singleShot(0, knopf.click)
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 120000)
    meldung = h.modal()
    text = meldung.text() if isinstance(meldung, QtGui.QMessageBox) else ""
    h.bild("3_fertig", meldung)
    for soll in ("Welle – Aufspannung 1 – Fertigteil", "Raster 0,5 mm längs und 1° rundum"):
        h.pruefe(soll in text, f"„{soll}“ fehlt: {text!r}")
    h.pruefe("Achtung" not in text, f"ins Teil: {text[:200]!r}")
    if isinstance(meldung, QtGui.QMessageBox):
        meldung.accept()
    yield 500
    fertig = ft.vorhanden(job)
    h.pruefe(fertig is not None, "kein Fertigteil im Dokument")
    if fertig is not None:
        form = fertig.Shape
        innen = teil.Shape.common(form).Volume
        stange = Part.makeCylinder(22, 40, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0)).Volume
        print(
            ascii(
                f"Fertigteil: {form.Volume:.0f} mm³, Welle {teil.Shape.Volume:.0f}, Stange {stange:.0f}, {len(form.Faces)} Flächen"
            )
        )
        h.pruefe(form.isValid() and len(form.Solids) == 1, f"Körper: {form.ShapeType}")
        h.pruefe(innen > 0.999 * teil.Shape.Volume, f"Welle nicht ganz darin: {innen:.0f}")
        # Abgestochen an der Rückseite der Welle: nicht länger als sie (+ 1 Planaufmaß vorn).
        h.pruefe(form.BoundBox.XLength < 41.5, f"länger als die Welle: {form.BoundBox.XLength:.1f}")
        h.pruefe(
            teil.Shape.Volume < form.Volume < min(1.15 * teil.Shape.Volume, stange),
            f"Volumen {form.Volume:.0f}",
        )
        # Über der Mitte der Abflachung (16 von der Achse, Aufmaß 0,3) ist nichts mehr.
        mitte = FreeCAD.Vector(20, 0, 17.5)
        h.pruefe(not form.isInside(mitte, 0.01, True), "über der Abflachung steht noch Stange")
        h.pruefe(
            form.isInside(FreeCAD.Vector(20, 0, 15.5), 0.01, True), "unter der Abflachung fehlt"
        )
        h.pruefe(
            os.path.exists(os.path.join(os.path.dirname(doc.FileName), fertig.Label + ".FCStd")),
            "keine Datei",
        )
    pruef.reject()
    yield 800
    if fertig is not None:
        # Fürs Bild: nur die Welle und das Fertigteil darum, schräg von oben.
        FreeCAD.setActiveDocument(doc.Name)
        for o in doc.Objects:
            if o.ViewObject is not None:
                o.ViewObject.Visibility = o in (teil, fertig)
        Gui.getDocument(doc.Name).activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.Selection.clearSelection()
        yield 800
        h.bild("4_fertigteil_3d")
    del gui_fertigteil
