# „4-Achs-Bearbeitung“ mit Maschine (W-003 Stufe V2a, Manuels Test 2026-09-27; „Maschine
# zuerst“, V3f): Die Beispiel-Drehmaschine ist offen, eine Welle liegt quer im Raum
# (längs X). Ihre Stirnfläche angeklickt: Oben unter „Maschine“ steht die
# Beispiel-Drehmaschine, darunter „Linearachsen X1, Y1, Z1 · Rundachse für die Stange: C ·
# 12 Werkzeugplätze“, die Rundachse „C – Stange längs Z“ (die einzige, nicht wählbar);
# die Stange liegt im Job längs Z. Mit A (ohne Maschine) liegt sie längs X, zurück auf
# die Maschine wieder längs Z. „Anlegen“, dann „Auf der Maschine prüfen“: Die Stange
# liegt parallel zur C-Achse im Futter, nicht quer – genau auf ihrer Achse und mit der
# Spannlänge (30 mm) im Futter (V2c). Zuletzt die gemerkte Maschine: gespeichert und
# geschlossen steht sie mit ihrem Namen aus der Liste „Maschinen …“ (W-011) als „„Drehmaschine
# mit Y-Achse“ öffnen (zuletzt benutzt)“ zur Wahl – gewählt öffnet sie sich, die Welle bleibt
# vorn, C gilt.
import os
import tempfile

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

    from camaddon import beispielmaschine, gui_reichweite, gui_vierachs
    from camaddon import maschine as m
    from camaddon import reichweite as rw
    from camaddon import vierachs_rohteil as vr
    from camaddon.kette import LINEAR

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    name_maschine = _maschine.Label  # bleibt, wenn die Datei zu ist
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300

    doc = FreeCAD.newDocument("Welle")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Welle")
    teil.Shape = Part.makeCylinder(30, 100, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0))
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    # Die Stirnfläche bei X 100, Außennormale +X.
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
    h.pruefe(
        panel.wahl_maschine.currentText() == name_maschine,
        f"Maschine: {panel.wahl_maschine.currentText()!r}",
    )
    kann = panel.maschine_text.text()
    h.pruefe(
        kann == "Linearachsen X1, Y1, Z1 · Rundachse für die Stange: C · 12 Werkzeugplätze",
        f"Was die Maschine kann: {kann!r}",
    )
    h.pruefe(
        panel.wahl_achse.count() == 1
        and panel.wahl_achse.itemText(0) == "C – Stange längs Z"
        and not panel.wahl_achse.isEnabled(),
        f"Rundachse: {[panel.wahl_achse.itemText(i) for i in range(panel.wahl_achse.count())]}",
    )
    h.pruefe(panel.buchstabe() == "C", f"Rundachse {panel.buchstabe()}")
    rohteil = panel.job.Stock

    def laengs(bb):
        """Die längste Seite des Rohteils: „X“, „Y“ oder „Z“."""
        return max(zip((bb.XLength, bb.YLength, bb.ZLength), "XYZ", strict=True))[1]

    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    h.pruefe(
        laengs(rohteil.Shape.BoundBox) == "Z", f"Stange mit Maschine: {rohteil.Shape.BoundBox}"
    )
    h.bild("1_fenster", panel.form)

    # Ohne Maschine, A: längs X; zurück auf die Maschine: längs Z.
    panel.waehle_rundachse("A")
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    h.pruefe(laengs(rohteil.Shape.BoundBox) == "X", f"Stange bei A: {rohteil.Shape.BoundBox}")
    h.pruefe(panel.wahl_maschine.currentText() == "ohne Maschine", "A ohne Maschine?")
    panel.wahl_maschine.setCurrentIndex(0)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    h.pruefe(
        laengs(rohteil.Shape.BoundBox) == "Z", f"wieder die Maschine: {rohteil.Shape.BoundBox}"
    )
    # „Weiter“, dann ohne „Rundum schruppen“ „Anlegen“: nur Job und Stange.
    panel.accept()
    yield 300
    panel.mit_schruppen.setChecked(False)
    panel.accept()
    yield 800
    job = next(o for o in doc.Objects if type(getattr(o, "Proxy", None)).__name__ == "ObjectJob")

    # Auf der Maschine prüfen: die Stange parallel zur C-Achse, nicht quer im Futter.
    FreeCAD.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 15000)
    pruefen = gui_reichweite.PruefPanel.offen
    h.pruefe(pruefen is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruefen is None:
        return
    yield 800
    pruefung = pruefen.pruefung
    lcs = m.globale_platzierung(pruefung.werkstueckaufnahme.Lcs)
    stange = lcs.Rotation.multVec(FreeCAD.Vector(0, 0, 1))  # die Stangenachse des Jobs, Welt
    c = next(
        a
        for a in pruefung.kette.achsen
        if a.art != LINEAR and rw._programmbuchstabe(pruefung.maschine, a) == "C"
    )
    h.pruefe(abs(abs(stange.dot(c.richtung)) - 1) < 1e-6, f"Stange {stange} quer zu C {c.richtung}")
    # Hinten liegt die Stange bei Z −133 (Teil 100, Abstich 3, Spannlänge 30): 103 heißt
    # 30 mm im Futter; X und Y genau 0.
    vorschlag = [pruefen.felder_nullpunkt[a].placeholderText() for a in ("X", "Y", "Z")]
    h.pruefe(vorschlag == ["0", "0", "103"], f"Nullpunkt-Vorschlag: {vorschlag}")
    Gui.SendMsgToActiveView("ViewFit")
    yield 300
    h.bild("2_im_futter")
    pruefen.reject()
    yield 500

    # --- Die zuletzt benutzte Maschine, gespeichert und geschlossen: zum Öffnen in der Liste.
    from camaddon import PARAMETER_PFAD

    pfad = os.path.join(tempfile.mkdtemp(), "drehmaschine.FCStd")
    asm.Document.saveAs(pfad)
    FreeCAD.ParamGet(PARAMETER_PFAD).SetString(rw.ZULETZT_MASCHINE, pfad)
    FreeCAD.closeDocument(asm.Document.Name)
    FreeCAD.setActiveDocument(doc.Name)
    yield 500
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 300
    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None, "zweites Fenster fehlt")
    if panel is None:
        return
    eintraege = [panel.wahl_maschine.itemText(i) for i in range(panel.wahl_maschine.count())]
    h.pruefe(
        eintraege == [f"„{name_maschine}“ öffnen (zuletzt benutzt)", "ohne Maschine"]
        and panel.wahl_maschine.currentIndex() == 1,
        f"Maschinen: {eintraege}, gewählt {panel.wahl_maschine.currentIndex()}",
    )
    panel.wahl_maschine.setCurrentIndex(0)
    yield from h.warte_auf(
        lambda: panel.maschinenwahl() is not None and not isinstance(panel.maschinenwahl(), str),
        15000,
    )
    yield 500
    h.pruefe(
        panel.wahl_maschine.currentText() == name_maschine and panel.buchstabe() == "C",
        f"geöffnet: {panel.wahl_maschine.currentText()!r}, {panel.buchstabe()}",
    )
    h.pruefe(FreeCAD.ActiveDocument is doc, f"vorn: {FreeCAD.ActiveDocument.Name}")
    h.bild("3_zuletzt_benutzt_geoeffnet", panel.form)
    panel.reject()
    yield 500
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
