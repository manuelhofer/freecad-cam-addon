# Flächen wählen im 4-Achs-Assistenten (W-003 Stufe V4, Manuel 2026-09-30: „nur Flächen am
# Mantel anklicken, die ich bearbeiten will … und wenn ich alle anklicke, dann wird komplett
# rings um bearbeitet“). Welle Ø 20 × 40 mit Abflachung, Stange Ø 24, T1 Schaftfräser Ø 6,
# T2 Kugelfräser Ø 4. Schritt 2: grau „Rundum – alle Mantelflächen …“. Ein Klick auf die
# Abflachung: Sie steht in der Liste – „Ebene – erreichbar“, grün –, in der 3D-Ansicht grün,
# der Satz „Nur diese Flächen …“, die Vorschau rechnet. „Alle Mantelflächen“: „… – rundum.“
# „Auswahl leeren“, wieder die Abflachung → „Anlegen“: Beide Operationen haben nur sie, die
# Schruppbahn bleibt in ihrem Bereich, die Welle hat ihre Farben zurück. Doppelklick auf
# „Rundum schruppen T1“: die Abflachung steht in der Liste; ein Klick nimmt sie heraus →
# „Übernehmen“: rundum. Das Muster fürs Schlichten (V4c): mit der Abflachung schlägt der
# Assistent „Linien längs“ vor (grau der Grund), rundum die Spirale; die Operation trägt es.
import math

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
    from camaddon import vierachs_bahn as vb
    from camaddon import vierachs_flaechen as vf
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(nummer=1, durchmesser=6, schneiden=3, schneidenlaenge=16)
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=2.4, ap=2, vc=150, fz=0.04)]
    t2 = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=4, schneiden=2)
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.5, ap=4, vc=150, fz=0.03)]
    wz.Bibliothek([t1, t2]).speichern()

    doc = FreeCAD.newDocument("Abflachung")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Welle")
    welle = Part.makeCylinder(10, 40, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0))
    welle = welle.cut(Part.makeBox(20, 20, 10, FreeCAD.Vector(10, -10, 8)))
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
    panel.feld_stange.setText("24")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.accept()  # Weiter
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    text = panel.flaechen_text.text()
    h.pruefe(text.startswith("Rundum – alle Mantelflächen."), f"ohne Wahl: {text!r}")
    h.pruefe(panel.flaechen_liste.isHidden(), "Liste ohne Wahl sichtbar")
    yield from h.warte_auf(
        lambda: panel.vorschau is not None and panel.vorschau_schlichten is not None, 30000
    )
    lagen_rundum = panel.ergebnis.text()
    h.pruefe(panel.muster() == vb.SPIRALE, f"Muster rundum: {panel.muster()}")
    h.pruefe(
        panel.muster_grund.text() == "Vorschlag: Spirale – es geht rundum.",
        f"Grund rundum: {panel.muster_grund.text()!r}",
    )
    h.bild("1_rundum", panel.form)

    # --- Ein Klick auf die Abflachung --------------------------------------------------------
    job = panel.job
    klon = vr.modell(job)
    farben_vorher = list(klon.ViewObject.DiffuseColor)
    Gui.Selection.addSelection(doc.Name, klon.Name, abflachung)
    yield 500
    h.pruefe(panel.gewaehlte == [abflachung], f"gewählt: {panel.gewaehlte}")
    h.pruefe(not Gui.Selection.getSelectionEx(), "Auswahl nach dem Klick nicht leer")
    h.pruefe(panel.flaechen_liste.count() == 1, f"Liste: {panel.flaechen_liste.count()}")
    if panel.flaechen_liste.count():
        eintrag = panel.flaechen_liste.item(0)
        h.pruefe(
            eintrag.text() == f"{abflachung}  Ebene – erreichbar", f"Eintrag: {eintrag.text()!r}"
        )
        farbe = eintrag.foreground().color().name()
        h.pruefe(farbe == gui_vierachs.GRUEN, f"Farbe in der Liste: {farbe}")
    text = panel.flaechen_text.text()
    h.pruefe(text.startswith("Nur diese Flächen:"), f"mit Wahl: {text!r}")
    nummer = int(abflachung[4:]) - 1
    farben = klon.ViewObject.DiffuseColor
    h.pruefe(
        len(farben) == len(klon.Shape.Faces)
        and abs(farben[nummer][1] - 0x9A / 255) < 0.01
        and abs(farben[nummer][0] - 0x4E / 255) < 0.01,
        f"Farbe im 3D: {farben[nummer] if len(farben) > nummer else farben}",
    )
    yield from h.warte_auf(
        lambda: panel.vorschau is not None and panel.vorschau_schlichten is not None, 30000
    )
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    # Die Abflachung ist ohnehin die tiefste Stelle: gleich viele Lagen wie rundum.
    h.pruefe(panel.ergebnis.text() == lagen_rundum, f"Lagen: {panel.ergebnis.text()!r}")
    # Das Muster: die Abflachung geht nicht rundum – Linien längs, mit dem Grund.
    h.pruefe(panel.muster() == vb.LINIEN, f"Muster mit Abflachung: {panel.muster()}")
    h.pruefe(
        panel.muster_grund.text().startswith("Vorschlag: Linien längs"),
        f"Grund: {panel.muster_grund.text()!r}",
    )
    h.pruefe(
        "Linien längs" in panel.ergebnis_schlichten.text(),
        f"Schlichten: {panel.ergebnis_schlichten.text()!r}",
    )
    h.bild("2_abflachung", panel.form)
    h.bild("2b_abflachung_3d")

    # --- Alle Mantelflächen: rundum; leeren; wieder die Abflachung --------------------------
    panel.alle_mantelflaechen()
    yield 300
    text = panel.flaechen_text.text()
    h.pruefe(text == "Alle Mantelflächen gewählt – rundum.", f"alle: {text!r}")
    h.pruefe(panel.flaechen() == [], f"alle: {panel.flaechen()}")
    h.pruefe(panel.flaechen_liste.count() >= 2, f"alle: {panel.flaechen_liste.count()} Einträge")
    h.pruefe(panel.muster() == vb.SPIRALE, f"Muster mit allen Flächen: {panel.muster()}")
    h.bild("3_alle_mantelflaechen", panel.form)
    panel.flaechen_leeren()
    yield 300
    h.pruefe(panel.gewaehlte == [] and panel.flaechen_liste.isHidden(), "leeren")
    h.pruefe(list(klon.ViewObject.DiffuseColor) == farben_vorher, "Farben nach dem Leeren")
    Gui.Selection.addSelection(doc.Name, klon.Name, abflachung)
    yield 500
    h.pruefe(panel.flaechen() == [abflachung], f"wieder: {panel.flaechen()}")
    yield from h.warte_auf(
        lambda: panel.vorschau is not None and panel.vorschau_schlichten is not None, 30000
    )
    panel.accept()  # Anlegen
    yield 2000
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster nach „Anlegen“ offen")
    h.pruefe(list(klon.ViewObject.DiffuseColor) == farben_vorher, "Farben nach dem Anlegen")
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    h.pruefe(len(ops) == 2, f"Operationen: {[o.Label for o in ops]}")
    for op in ops:
        h.pruefe(list(op.Flaechen) == [abflachung], f"{op.Label}: {list(op.Flaechen)}")
    schlichten_op = next((o for o in ops if not vo.ist_schruppen(o)), None)
    if schlichten_op is not None:
        h.pruefe(schlichten_op.Muster == "Linien", f"Muster der Operation: {schlichten_op.Muster}")
        h.pruefe(schlichten_op.Linien > 0, f"Linien der Operation: {schlichten_op.Linien}")
    schruppen = next((o for o in ops if vo.ist_schruppen(o)), None)
    if schruppen is None:
        return
    # Die Bahn bleibt im Bereich des Fräsers R 3 um die Abflachung: Die Spitze liegt bei
    # a · Stangenachse + r · Werkzeugrichtung, die Rundachse steht auf −Drehsinn · φ.
    laengs, radial = schruppen.Stangenachse, schruppen.Werkzeugrichtung
    bereich = vf.bereich_fuer(klon.Shape, laengs, radial, [abflachung], 3.0)
    buchstabe, drehsinn = schruppen.Rundachse, schruppen.Drehsinn
    a, phi = [], []
    for befehl in schruppen.Path.Commands:
        if befehl.Name != "G1":
            continue
        werte = befehl.Parameters
        spitze = FreeCAD.Vector(werte.get("X", 0.0), werte.get("Y", 0.0), werte.get("Z", 0.0))
        a.append(spitze.dot(laengs))
        phi.append(math.radians(-werte[buchstabe] / drehsinn))
    h.pruefe(len(a) > 20, f"{len(a)} Schnitte")
    drin = bereich.bei(a, phi)
    h.pruefe(bool(drin.all()), f"{int((~drin).sum())} von {len(a)} Schnitten außerhalb")
    h.pruefe(schruppen.Lagen >= 1, f"Lagen: {schruppen.Lagen}")
    h.bild("4_angelegt")

    # --- Ändern: die Abflachung steht in der Liste; heraus → rundum -------------------------
    schruppen.ViewObject.Proxy.doubleClicked(schruppen.ViewObject)
    yield 1000
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.zu_aendern is schruppen, "Doppelklick öffnet nichts")
    if panel is None:
        return
    h.pruefe(panel.gewaehlte == [abflachung], f"beim Ändern: {panel.gewaehlte}")
    h.pruefe(panel.flaechen_liste.count() == 1, "beim Ändern: Liste")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    h.bild("5_aendern", panel.form)
    Gui.Selection.addSelection(doc.Name, klon.Name, abflachung)
    yield 500
    h.pruefe(panel.gewaehlte == [], f"heraus: {panel.gewaehlte}")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    h.pruefe(panel.accept() is True, "„Übernehmen“ ging nicht")
    yield 1500
    h.pruefe(list(schruppen.Flaechen) == [], f"nach dem Ändern: {list(schruppen.Flaechen)}")
    h.pruefe(math.isclose(schruppen.Eintauchwinkel.Value, 5.0), "Eintauchwinkel")
    h.pruefe(list(klon.ViewObject.DiffuseColor) == farben_vorher, "Farben nach dem Ändern")
