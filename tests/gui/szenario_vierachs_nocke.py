# Nockenwelle auf der Drehmaschine mit C (W-006 4.3 Punkt 5: „rundum schruppen kann es;
# schlichten mit … Grathöhe – prüfen“). Die Beispiel-Drehmaschine ist offen; in der
# Werkzeugverwaltung T1 Schaftfräser Ø 12 („Schruppen“) und T2 Kugelfräser Ø 6 („Schlichten“,
# ae 0,3), beide im Halter „VDI30 angetrieben radial“. Welle Ø 30 × 100 längs X mit einem
# Nocken in der Mitte: Scheibe Ø 44, 20 lang, 6 mm außermittig (reicht bis 28 mm von der
# Achse). Die Stirnfläche angeklickt, Stange Ø 60, „Weiter“: „Rundum schruppen“ und „Rundum
# schlichten“ angehakt, T1 und T2 vorgewählt, die Vorschau „→ … Lagen“ und „→ … Umdrehungen,
# etwa … min“ ohne roten Satz. „Anlegen“: „Rundum schruppen T1“ und „Rundum schlichten T2“.
# „Auf der Maschine prüfen“: „Alle Achsen bleiben in ihren Grenzen.“, „Kollision prüfen“ →
# „Nichts berührt sich …“; am Ende „Am Ende bleiben …“ und „nirgends ins Teil“ – auch am
# Nocken, wo C mit der Höhe der Kurve wechselt.
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

    from camaddon import beispielmaschine, gui_reichweite, gui_vierachs
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26,
                     laenge_spindelnase=125)  # fmt: skip
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=150, fz=0.08)]
    t2 = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2,
                     schneidenlaenge=12, laenge_spindelnase=125)  # fmt: skip
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=6, vc=150, fz=0.04)]
    bibliothek = wz.Bibliothek([t1, t2])
    for werkzeug in (t1, t2):
        werkzeug.halter = bibliothek.neuer_halter("vdi30_radial").kennung
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300

    doc = FreeCAD.newDocument("Nockenwelle")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Nockenwelle")
    welle = Part.makeCylinder(15, 100, V(), V(1, 0, 0))
    nocke = Part.makeCylinder(22, 20, V(40, 6, 0), V(1, 0, 0))
    teil.Shape = welle.fuse(nocke).removeSplitter()
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f)
        and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
        and f.Area < 1000  # die Stirn der Welle Ø 30 hinten, nicht die Seite des Nockens
        and f.CenterOfMass.x > 99
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
    panel.feld_stange.setText("60")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    h.pruefe(panel.buchstabe() == "C", f"Rundachse {panel.buchstabe()}")
    h.pruefe(panel.accept() is False, "„Weiter“ schließt das Fenster")
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    h.pruefe(panel.mit_schruppen.isChecked(), "„Rundum schruppen“ nicht angehakt")
    h.pruefe(panel.mit_schlichten.isChecked(), "„Rundum schlichten“ nicht angehakt")
    h.pruefe(panel.fraeser() is not None and panel.fraeser().nummer == 1, "Schruppen: nicht T1")
    schlicht = panel.schlichtfraeser()
    h.pruefe(schlicht is not None and schlicht.nummer == 2, "Schlichten: nicht T2")
    yield from h.warte_auf(
        lambda: panel.vorschau is not None and panel.vorschau_schlichten is not None, 60000
    )
    ergebnis = panel.ergebnis.text()
    h.pruefe(ergebnis.startswith("→ ") and " Lagen (Ø 60,0 mm → Ø " in ergebnis, f"{ergebnis!r}")
    schlichten_text = panel.ergebnis_schlichten.text()
    h.pruefe(
        schlichten_text.startswith("→ ") and "Umdrehungen, etwa" in schlichten_text,
        f"Ergebnis Schlichten: {schlichten_text!r}",
    )
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    h.bild("1_was_willst_du_machen", panel.form)

    # --- Anlegen -------------------------------------------------------------------------
    job = panel.job
    panel.accept()
    yield 2000
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster noch offen")
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    namen = [o.Label for o in ops]
    h.pruefe(namen == ["Rundum schruppen T1", "Rundum schlichten T2"], f"Operationen: {namen}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("2_bahnen_um_die_nocke")

    # --- Auf der Maschine prüfen -----------------------------------------------------------
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
    h.pruefe(
        pruef.urteil.text() == "Alle Achsen bleiben in ihren Grenzen.",
        f"Urteil: {pruef.urteil.text()!r}",
    )
    k = pruef.kollision
    pruef.urteil_kollision.linkActivated.emit("kollision:pruefen")
    yield from h.warte_auf(lambda: not k.laeuft and k.ergebnis is not None, 300000)
    yield 300
    h.pruefe(
        k.urteil.text().startswith("Nichts berührt sich"),
        f"Kollision: {k.urteil.text()!r} {[b.text() for b in k.ergebnis.befunde][:2]}",
    )
    spieler = pruef.abspieler
    spieler.setze_zeit(spieler.abfahrt.dauer)
    yield from h.warte_auf(lambda: spieler.rest.text().startswith("Am Ende"), 300000)
    rest = spieler.rest.text()
    h.pruefe(rest.startswith("Am Ende bleiben") and "nirgends ins Teil" in rest, f"{rest!r}")
    Gui.SendMsgToActiveView("ViewFit")
    spieler.knopf_hinsehen.click()
    yield 800
    h.bild("3_am_ende_farben")
    h.bild("3b_pruefen_fenster", pruef.form)
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
