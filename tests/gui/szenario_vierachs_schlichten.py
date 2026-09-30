# „Rundum schlichten“ im Assistenten (W-003 Stufe V5d, Manuel 2026-09-30: „es darf ja
# nicht nur Schuppen geben auch schlichten ist wichtig“). In der Werkzeugverwaltung stehen
# T1 Schaftfräser Ø 12 („Schruppen“) und T2 Kugelfräser Ø 6 („Schlichten“, ae 0,3 mm).
# Welle Ø 60 mit Absatz auf Ø 40, Stange Ø 80, ohne Maschine. Schritt 2: „Rundum
# schlichten“ ist angehakt (T2 hat einen Einsatz „Schlichten“), T2 und „Schlichten“
# vorgewählt, grau „0,3“ als Schrittweite (ae aus der Werkzeugtabelle), „→ Kammhöhe
# 0,004 mm“ und „→ … Umdrehungen, etwa … min“; unter „Abstände“ grau „Radius + 0,5“; die
# Stange ragt so weit heraus, wie T1 braucht. Erst nur schruppen (Haken aus) → „Anlegen“.
# Doppelklick auf „Rundum schruppen T1“: „Rundum schlichten“ ist frei, „Haken setzen: …“ –
# Haken, „Übernehmen“: Im Job stehen jetzt auch „T2 Schlichten“ und „Rundum schlichten
# T2“, ein Schritt Rückgängig. Doppelklick auf „Rundum schlichten T2“: Kopf „„Rundum
# schlichten T2“ ändern“, das Schruppen ist ausgeblendet; Schrittweite 0,5 → „Übernehmen“:
# die Operation hat 0,5, ein Schritt Rückgängig „Rundum schlichten ändern“.
import FreeCAD
import FreeCADGui as Gui
import Part


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import gui_vierachs
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import vierachs_schlichten as vs
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26)
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=150, fz=0.08)]
    t2 = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=6, vc=150, fz=0.04)]
    wz.Bibliothek([t1, t2]).speichern()

    doc = FreeCAD.newDocument("Welle")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Welle")
    welle = Part.makeCylinder(30, 60, FreeCAD.Vector(40, 0, 0), FreeCAD.Vector(1, 0, 0))
    welle = welle.fuse(Part.makeCylinder(20, 40, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0)))
    teil.Shape = welle.removeSplitter()
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f)
        and (vr.aussennormale(f) - FreeCAD.Vector(1, 0, 0)).Length < 1e-9
        and f.Area > 2000  # die Stirn Ø 60 vorne, nicht die Schulter
    )
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    # --- Anlegen: Schritt 2 mit beiden Haken ------------------------------------------------
    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.feld_stange.setText("80")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.accept()  # Weiter
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    h.pruefe(panel.mit_schruppen.isChecked(), "„Rundum schruppen“ nicht angehakt")
    h.pruefe(panel.mit_schlichten.isChecked(), "„Rundum schlichten“ nicht angehakt")
    h.pruefe(panel.fraeser() is not None and panel.fraeser().nummer == 1, "Schruppen: nicht T1")
    schlicht = panel.schlichtfraeser()
    h.pruefe(schlicht is not None and schlicht.nummer == 2, "Schlichten: nicht T2")
    einsatz = panel.schlichteinsatz()
    h.pruefe(einsatz is not None and einsatz.art == wz.SCHLICHTEN, "Einsatz nicht „Schlichten“")
    grau = panel.felder_schlichten["schrittweite"].placeholderText()
    h.pruefe(grau == "0,3", f"Schrittweite grau: {grau!r}")
    grau = panel.felder_schruppen["ueberlauf"].placeholderText()
    h.pruefe(grau == "Radius + 0,5", f"Überlauf grau: {grau!r}")
    yield from h.warte_auf(
        lambda: panel.vorschau is not None and panel.vorschau_schlichten is not None, 30000
    )
    kamm = panel.kammhoehe.text()
    h.pruefe(kamm == "→ Kammhöhe 0,004 mm", f"Kammhöhe: {kamm!r}")
    ergebnis = panel.ergebnis_schlichten.text()
    h.pruefe(
        ergebnis.startswith("→ ") and "Umdrehungen, etwa" in ergebnis and "min" in ergebnis,
        f"Ergebnis Schlichten: {ergebnis!r}",
    )
    ausspannen = panel.ausspannen.text()
    h.pruefe(
        "Überlauf 6,5 + Fräserradius 6,0 + Abstand zum Futter 5,0" in ausspannen,
        f"Ausspannen: {ausspannen!r}",
    )
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    h.bild("1_schruppen_und_schlichten", panel.form)

    # Nur schruppen – das Schlichten kommt nachträglich.
    panel.mit_schlichten.setChecked(False)
    yield from h.warte_auf(lambda: panel.vorschau is not None, 15000)
    job = panel.job
    panel.accept()  # Anlegen
    yield 1500
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster nach „Anlegen“ offen")
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    h.pruefe([o.Label for o in ops] == ["Rundum schruppen T1"], f"Operationen: {ops}")
    if not ops:
        return
    schruppen = ops[0]

    # --- Doppelklick aufs Schruppen: Schlichten dazunehmen ----------------------------------
    schritte_vorher = len(doc.UndoNames)
    schruppen.ViewObject.Proxy.doubleClicked(schruppen.ViewObject)
    yield 1000
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.zu_aendern is schruppen, "Doppelklick öffnet nichts")
    if panel is None:
        return
    h.pruefe(
        panel.mit_schlichten.isEnabled() and not panel.mit_schlichten.isChecked(),
        "„Rundum schlichten“ nicht frei",
    )
    text = panel.erklaerung_schlichten.text()
    h.pruefe(text.startswith("Haken setzen:"), f"Satz beim Schlichten: {text!r}")
    panel.mit_schlichten.setChecked(True)
    yield from h.warte_auf(
        lambda: panel.vorschau is not None and panel.vorschau_schlichten is not None, 30000
    )
    h.bild("2_schlichten_dazunehmen", panel.form)
    h.pruefe(panel.accept() is True, "„Übernehmen“ ging nicht")
    yield 1500
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    namen = [o.Label for o in ops]
    h.pruefe(namen == ["Rundum schruppen T1", "Rundum schlichten T2"], f"Operationen: {namen}")
    labels = [tc.Label for tc in job.Tools.Group]
    h.pruefe(labels == ["T1 Schruppen", "T2 Schlichten"], f"Controller: {labels}")
    h.pruefe(len(doc.UndoNames) == schritte_vorher + 1, f"Rückgängig: {doc.UndoNames[:3]}")
    schlichten = next((o for o in ops if vs.ist_schlichten(o)), None)
    if schlichten is None:
        return
    h.pruefe(schlichten.Umdrehungen > 100, f"Umdrehungen: {schlichten.Umdrehungen}")
    # In der Innenecke am Absatz ließ die Schruppspirale Keile stehen: Schlichten fährt dort
    # vorher in Stufen, je höchstens den Radius des Kugelfräsers tief.
    h.pruefe(schlichten.Vorstufen >= 1, f"Vorstufen: {schlichten.Vorstufen}")
    h.pruefe(abs(schlichten.Schrittweite.Value - 0.3) < 1e-9, f"{schlichten.Schrittweite}")

    # --- Doppelklick aufs Schlichten: ändern --------------------------------------------------
    schlichten.ViewObject.Proxy.doubleClicked(schlichten.ViewObject)
    yield 1000
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.zu_aendern is schlichten, "Doppelklick öffnet nichts")
    if panel is None:
        return
    kopf = panel._kopf_text.text()
    h.pruefe("„Rundum schlichten T2“ ändern" in kopf, f"Kopf: {kopf!r}")
    h.pruefe(panel.mit_schruppen.isHidden() and panel.schruppfelder.isHidden(), "Schruppen da")
    h.pruefe(
        panel.mit_schlichten.isChecked() and not panel.mit_schlichten.isEnabled(), "Haken frei"
    )
    h.pruefe(panel.schlichtfraeser() is not None and panel.schlichtfraeser().nummer == 2, "T2?")
    texte = {k: f.text() for k, f in panel.felder_schlichten.items()}
    h.pruefe(not any(texte.values()), f"Felder: {texte}")
    panel.felder_schlichten["schrittweite"].setText("0,5")
    yield from h.warte_auf(lambda: panel.vorschau_schlichten is not None, 30000)
    h.pruefe(panel.kammhoehe.text() == "→ Kammhöhe 0,010 mm", f"{panel.kammhoehe.text()!r}")
    h.bild("3_schlichten_aendern", panel.form)
    schritte_vorher = len(doc.UndoNames)
    h.pruefe(panel.accept() is True, "„Übernehmen“ ging nicht")
    yield 1500
    h.pruefe(abs(schlichten.Schrittweite.Value - 0.5) < 1e-9, f"{schlichten.Schrittweite}")
    h.pruefe(schlichten.ToolController.Label == "T2 Schlichten", "Controller gewechselt")
    h.pruefe(len(doc.UndoNames) == schritte_vorher + 1, "mehr als ein Schritt Rückgängig")
    h.pruefe(doc.UndoNames[0] == "Rundum schlichten ändern", f"Schritt: {doc.UndoNames[0]!r}")
