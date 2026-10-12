# Der Job dreht um eine Rundachse, die die Maschine nicht hat (P-2026-10-12-138; Manuel,
# 2026-10-12: den Job ohne Maschine angelegt – die Stange längs X, A –, dann die CLX550 mit C; in
# „Auf der Maschine prüfen“ lag die Stange quer auf dem Tisch, beide Operationen ausgelassen):
# Eine Welle als 4-Achs-Job auf A mit „Rundum schruppen“, die Beispiel-Drehmaschine (C). Das
# Prüffenster sagt es in einer Zeile mit dem Knopf „Auf C umstellen“; danach liegt die Stange
# längs Z, die Operation dreht C, und nichts fällt mehr aus.
import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtCore


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine as bm
    from camaddon import gui_reichweite
    from camaddon import vierachs_achsen as va
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    asm, _maschine = bm.lade(bm.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document, 10000)

    doc = FreeCAD.newDocument("Welle")
    doc.UndoMode = 1
    welle = doc.addObject("Part::Feature", "Welle")
    welle.Shape = Part.makeCylinder(15, 60, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0))
    doc.recompute()
    stirn = next(
        f
        for f in welle.Shape.Faces
        if vr.ist_eben(f) and (vr.aussennormale(f) - FreeCAD.Vector(1, 0, 0)).Length < 1e-9
    )
    achse = va.zugewiesen("A")  # ohne Maschine angelegt
    lage = vr.berechne(welle.Shape, stirn, achse, durchmesser=40)
    job = vr.richte_ein(doc, welle, lage, vr.Stange(40.0, frei_hinten=17.5), achse)
    tc = job.Tools.Group[0]
    tc.Tool.Diameter = 12
    tc.HorizFeed = "1500 mm/min"
    tc.VertFeed = "500 mm/min"
    doc.recompute()
    op = vo.lege_an(job, tc, achse, zustellung=2.0, steigung=4.8, aufmass=0.3)
    doc.recompute()
    h.pruefe(op.Rundachse == "A", f"Operation dreht {op.Rundachse}")

    FreeCAD.setActiveDocument(doc.Name)
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 20000)
    panel = gui_reichweite.PruefPanel.offen
    h.pruefe(panel is not None, "„Auf der Maschine prüfen“ öffnet nicht")
    if panel is None:
        return
    yield from h.warte_auf(lambda: not panel.rechnet(), 60000)
    yield 500
    h.pruefe(not panel.achse_anders.isHidden(), "keine Zeile „andere Rundachse“")
    h.pruefe(
        "um A" in panel.achse_satz.text() and "um C" in panel.achse_satz.text(),
        f"Satz: {panel.achse_satz.text()!r}",
    )
    h.pruefe(panel.knopf_achse.text() == "Auf C umstellen", f"Knopf: {panel.knopf_achse.text()}")
    h.bild("1_andere_achse", panel.form)
    h.bild("1b_quer_auf_dem_tisch")

    panel.knopf_achse.click()
    yield from h.warte_auf(lambda: not panel.rechnet(), 60000)
    yield 800
    h.pruefe(op.Rundachse == "C", f"nach dem Umstellen dreht die Operation {op.Rundachse}")
    e = vr.einstellung(job)
    h.pruefe(
        e is not None and (e.laengs - FreeCAD.Vector(0, 0, 1)).Length < 1e-9,
        f"Stange nicht längs Z: {e and e.laengs}",
    )
    h.pruefe(panel.achse_anders.isHidden(), "die Zeile bleibt nach dem Umstellen")
    hinweise = panel.abspieler.hinweise.text()
    h.pruefe("Rundachsen nicht" not in hinweise, f"noch ausgelassen: {hinweise!r}")
    h.pruefe(
        panel.abspieler.abfahrt is not None and panel.abspieler.abfahrt.stationen,
        "nichts abzufahren",
    )
    h.bild("2_umgestellt", panel.form)
    h.bild("2b_im_futter")
    h.pruefe(doc.UndoNames[:1] == ["Auf C umstellen"], f"Rückgängig: {doc.UndoNames[:2]}")
    panel.accept()
    yield 800
