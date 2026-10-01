# Prüfen nur auf den gewählten Flächen (W-003 Stufe V4e) auf der Beispiel-Drehmaschine: Welle
# Ø 40 × 40 mit Abflachung, Stange Ø 44, T1 Schaftfräser Ø 12 im Halter „VDI30 angetrieben
# radial“. Im Assistenten nur die Abflachung gewählt, nur „Rundum schruppen“ (Plan indexiert
# und Entgraten, die er dafür vorschlägt, aus) → „Anlegen“ →
# „Auf der Maschine prüfen“ → ans Ende: Der Satz unter dem Abspieler sagt „Verglichen auf den
# gewählten Flächen …“; der Mantel, der Stange bleibt, ist nicht rot, nirgends fehlt etwas im
# Teil.
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
    from camaddon import restmaterial as rm
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
    teil = doc.addObject("Part::Feature", "Welle")
    welle = Part.makeCylinder(20, 40, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0))
    welle = welle.cut(Part.makeBox(24, 40, 10, FreeCAD.Vector(8, -20, 16)))
    teil.Shape = welle.removeSplitter()
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")

    def ebene_mit(richtung):
        return next(
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if vr.ist_eben(f) and (vr.aussennormale(f) - FreeCAD.Vector(*richtung)).Length < 1e-9
        )

    stirn = ebene_mit((1, 0, 0))
    abflachung = ebene_mit((0, 0, 1))
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
    klon = vr.modell(panel.job)
    Gui.Selection.addSelection(doc.Name, klon.Name, abflachung)
    yield 500
    h.pruefe(panel.flaechen() == [abflachung], f"gewählt: {panel.flaechen()}")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    # Nur „Rundum schruppen“: Für die Abflachung schlägt der Assistent auch „Plan indexiert“ und
    # „Rundum entgraten“ vor (V4c, V4d) – hier aus.
    panel.mit_plan.setChecked(False)
    panel.mit_entgraten.setChecked(False)
    yield 500
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    job = panel.job
    panel.accept()  # Anlegen
    yield 1500
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    h.pruefe(len(ops) == 1 and list(ops[0].Flaechen) == [abflachung], f"Operationen: {ops}")

    FreeCAD.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400  # siehe szenario_reichweite.py: 1.1.3 verarbeitet die Auswahl verzögert
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruef is None:
        return
    yield 800
    spieler = pruef.abspieler
    spieler.setze_zeit(spieler.abfahrt.dauer)
    yield 800
    rest = spieler.rest.text()
    h.pruefe("Verglichen auf den gewählten Flächen" in rest, f"Satz: {rest!r}")
    h.pruefe("nirgends ins Teil" in rest, f"ins Teil? {rest!r}")
    abtrag = getattr(getattr(pruef, "bild", None), "abtrag", None)
    h.pruefe(abtrag is not None, "kein Abtrag")
    if abtrag is not None:
        vergleich = abtrag.vergleich()
        h.pruefe(vergleich.nur_gewaehlte, "nicht nur auf den gewählten Flächen verglichen")
        h.pruefe(not (vergleich.farbe == rm.BLAU).any(), "blau: im Teil")
        gefaerbt = vergleich.farbe != rm.OHNE_TEIL
        h.pruefe(
            0 < int(gefaerbt.sum()) < 0.5 * gefaerbt.size,
            f"gefärbt {int(gefaerbt.sum())} von {gefaerbt.size} Zellen",
        )
    Gui.SendMsgToActiveView("ViewFit")
    spieler.knopf_hinsehen.click()
    yield 500
    h.bild("1_am_ende_nur_abflachung")
    h.bild("1b_pruefen_fenster", pruef.form)
    pruef.reject()
    yield 500
