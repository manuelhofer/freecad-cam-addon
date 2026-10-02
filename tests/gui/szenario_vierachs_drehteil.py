# Ein Drehteil mit Fräser und Bohrer in einem Durchgang (P-2026-10-02-11): Welle Ø 30 × 80 längs
# X, vorne eine Abflachung (12 von der Achse), in der Mitte eine Nut auf dem Mantel 8 breit,
# 4 tief über 120°, hinten eine durchgehende Querbohrung Ø 8; T1 ein Schaftfräser Ø 8
# („Planen“), T2 ein Bohrer Ø 8 (118°, „Bohren“), beide im Halter „VDI30 angetrieben radial“.
# Die Stirnfläche angeklickt, Stange Ø 32, „Weiter“, „Rundum schruppen“ und „Rundum schlichten“
# aus. Abflachung, Nutgrund und Bohrung angeklickt: „Plan indexiert“ geht an mit T1, darunter
# angehakt „Die Querbohrungen mit … T2 … bohren“; die Vorschau sagt „… – davon 1 als Nut auf dem
# Mantel … Dazu T2: 1 Bohrung gebohrt (von 2 Seiten), 2 Hübe, etwa …“. „Anlegen“: im selben Job
# „Plan indexiert T1“ (Abflachung und Nut) und „Radial bohren T2“ (die Bohrung). „Auf der
# Maschine prüfen“: Achsen in ihren Grenzen, nichts berührt sich, am Ende nirgends ins Teil.

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

    t1 = wz.Werkzeug(nummer=1, durchmesser=8, schneiden=3, schneidenlaenge=20,
                     laenge_spindelnase=125)  # fmt: skip
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.PLANEN, ae=3.2, ap=2, vc=150, fz=0.04)]
    t2 = wz.Werkzeug(nummer=2, art=wz.BOHRER, durchmesser=8, schneiden=2, schneidenlaenge=60,
                     spitzenwinkel=118.0, schneidstoff=wz.HSS,
                     laenge_spindelnase=125)  # fmt: skip
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.1)]
    bibliothek = wz.Bibliothek([t1, t2])
    for werkzeug in (t1, t2):
        werkzeug.halter = bibliothek.neuer_halter("vdi30_radial").kennung
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300

    doc = FreeCAD.newDocument("Drehteil")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Welle")
    x = V(1, 0, 0)
    welle = Part.makeCylinder(15, 80, V(), x)
    welle = welle.cut(Part.makeBox(20, 40, 8, V(60, -20, 12)))  # Abflachung vorne
    ring = Part.makeCylinder(16, 8, V(40, 0, 0), x).cut(Part.makeCylinder(11, 8, V(40, 0, 0), x))
    welle = welle.cut(ring.common(Part.makeCylinder(16, 8, V(40, 0, 0), x, 120)))  # Mantelnut
    welle = welle.cut(Part.makeCylinder(4, 40, V(15, -20, 0), V(0, 1, 0)))  # Querbohrung
    teil.Shape = welle.removeSplitter()
    doc.recompute()
    flaechen = teil.Shape.Faces
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(flaechen)
        if vr.ist_eben(f)
        and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
        and f.CenterOfMass.x > 79
    )
    flach = next(
        f"Face{i + 1}"
        for i, f in enumerate(flaechen)
        if vr.ist_eben(f)
        and (vr.aussennormale(f) - V(0, 0, 1)).Length < 1e-9
        and f.CenterOfMass.z > 11.9  # nicht die Wand der Nut in der Ebene durch die Achse
    )
    nutgrund = next(
        f"Face{i + 1}"
        for i, f in enumerate(flaechen)
        if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 11.0) < 1e-6
    )
    bohrung = next(
        f"Face{i + 1}"
        for i, f in enumerate(flaechen)
        if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 4.0) < 1e-6
    )
    bohrungen = [flach, nutgrund, bohrung]
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.feld_stange.setText("32")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    h.pruefe(panel.buchstabe() == "C", f"Rundachse {panel.buchstabe()}")
    h.pruefe(panel.accept() is False, "„Weiter“ schließt das Fenster")
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    panel.mit_schruppen.setChecked(False)
    panel.mit_schlichten.setChecked(False)
    yield 300

    # --- Abflachung, Nut und Bohrung: der Fräser, daneben der Bohrer -------------------------
    job = panel.job
    klon = vr.modell(job)
    for name in bohrungen:
        Gui.Selection.addSelection(doc.Name, klon.Name, name)
    yield 500
    h.pruefe(sorted(panel.flaechen()) == sorted(bohrungen), f"gewählt: {panel.flaechen()}")
    h.pruefe(panel.mit_plan.isChecked(), "„Plan indexiert“ aus")
    vorschlag = panel.plan_grund.text()
    h.pruefe(
        vorschlag.startswith("Vorschlag: an – ") and "jede so, wie sie es braucht" in vorschlag,
        f"Grund: {vorschlag!r}",
    )
    h.pruefe(panel.planfraeser() is not None and panel.planfraeser().nummer == 1, "nicht T1")
    h.pruefe(
        not panel.mit_planbohrer.isHidden() and panel.mit_planbohrer.isChecked(),
        "kein Haken für den Bohrer",
    )
    h.pruefe("T2" in panel.mit_planbohrer.text(), f"Haken: {panel.mit_planbohrer.text()!r}")
    h.pruefe(panel.bohrer_dazu() is not None and panel.bohrer_dazu().nummer == 2, "nicht T2")
    yield from h.warte_auf(lambda: panel.vorschau_plan is not None, 60000)
    text = panel.ergebnis_plan.text()
    h.pruefe(
        text.startswith("→ 2 Flächen: ")
        and "davon 1 als Nut auf dem Mantel" in text
        and "Dazu T2: 1 Bohrung gebohrt (von 2 Seiten), 2 Hübe, etwa " in text,
        f"Vorschau: {text!r}",
    )
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    from camaddon.gui_teile import blaettere_zu

    blaettere_zu(panel.mit_plan)
    yield 300
    h.bild("1_fraeser_und_bohrer", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    panel.accept()
    yield 2500
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster noch offen")
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    namen = [o.Label for o in ops]
    h.pruefe(namen == ["Plan indexiert T1", "Radial bohren T2"], f"Operationen: {namen}")
    if len(ops) != 2:
        return
    plan, bohren = ops
    h.pruefe(sorted(plan.Flaechen) == sorted([flach, nutgrund]), f"T1: {plan.Flaechen}")
    h.pruefe(list(bohren.Flaechen) == [bohrung], f"T2: {bohren.Flaechen}")
    h.pruefe(plan.Ebenen == 2 and bohren.Huebe == 2, f"{plan.Ebenen} Flächen, {bohren.Huebe} Hübe")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("2_angelegt")

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
    pruef.reject()
    yield 500

    FreeCAD.closeDocument(doc.Name)
    yield 300
