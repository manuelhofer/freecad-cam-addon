# Vorschlichten (W-031; Manuel, 2026-10-18: „das man hier vll noch die möglichkeit dann gibt
# "vorschlichten" als hacken anzubieten .. aber über dem schlichten das ganze ... zwischen schruppen
# und schlichten“). Welle Ø 60 × 120 längs Z mit der Flosse der Nase (schräg oben und unten), Stange
# Ø 90; T1 Schaftfräser Ø 12 schruppt in Lagen von 2 mm, T2 Kugelfräser Ø 6 schlichtet (Einsätze
# „Schlichten“ und „Schruppen“). Nach dem Schruppen stehen an den schrägen Flächen Treppen: Der Satz
# unter dem Schlichten ist gelb („greift die Kugel stellenweise …“) und sagt „Vorschlichten ist
# darum angehakt.“, darunter grau „→ Kugel T2 auf 0,3 Aufmaß, Schrittweite …, X … mm: … Umdrehungen,
# etwa … min“ und, was die Kugel danach beim Schlichten höchstens nimmt. „Anlegen“: „Rundum schruppen
# T1“, „Rundum vorschlichten T2“ (nur das Stück längs, mit dem Einsatz „Schruppen“), „Rundum
# schlichten T2“ – in dieser Reihenfolge.
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

    from camaddon import gui_vierachs
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import vierachs_schlichten as vs
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26)
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=150, fz=0.08)]
    t2 = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)
    t2.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=6, vc=150, fz=0.04),
        wz.Einsatz(art=wz.SCHRUPPEN, ae=1.0, ap=1.5, vc=120, fz=0.05),
    ]
    wz.Bibliothek([t1, t2]).speichern()

    doc = FreeCAD.newDocument("Vorschlichten")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Nase")
    welle = Part.makeCylinder(30, 120, V(0, 0, -120), V(0, 0, 1))
    umriss = Part.makePolygon(
        [V(-42.7, -10, -30.2), V(-5.5, -10, 10.1), V(-5.5, -10, -56.2), V(-14.5, -10, -56.2)]
        + [V(-42.7, -10, -30.2)]
    )
    flosse = Part.Face(umriss).extrude(V(0, 20, 0))
    teil.Shape = welle.fuse(flosse).removeSplitter()
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f)
        and (vr.aussennormale(f) - V(0, 0, 1)).Length < 1e-2
        and 100 < f.Area < 2700
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
    panel.feld_stange.setText("90")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.accept()  # Weiter
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    job = panel.job
    if panel.mit_plan.isChecked():
        panel.mit_plan.setChecked(False)
    h.pruefe(panel.mit_schruppen.isChecked() and panel.mit_schlichten.isChecked(), "Haken aus")
    h.pruefe(panel.vorschlichten.isVisible(), "kein Haken „Vorschlichten“")
    yield from h.warte_auf(
        lambda: panel.vorschau is not None and panel.vorschau_schlichten is not None, 90000
    )
    yield from h.warte_auf(lambda: panel._rest_auftrag is None, 120000)
    rest = panel.rest_schlichten.text()
    print("Rest:", rest)
    h.pruefe(
        "greift die Kugel stellenweise" in rest and "Vorschlichten ist darum angehakt." in rest,
        f"Rest: {rest!r}",
    )
    h.pruefe(panel.vorschlichten.isChecked(), "Vorschlichten nicht vorgeschlagen")
    bereich = panel._vorschlicht_bereich
    h.pruefe(bereich is not None and bereich[0] < bereich[1], f"Stück längs: {bereich}")
    yield from h.warte_auf(
        lambda: panel._vor_auftrag is None and panel._vor_rest_auftrag is None, 120000
    )
    vor = panel.ergebnis_vorschlichten.text()
    print("Vorschlichten:", vor)
    h.pruefe(
        vor.startswith("→ Kugel T2 auf 0,3 Aufmaß, Schrittweite ")
        and "X " in vor  # die Stange liegt im Job längs X
        and ("Umdrehungen" in vor or "Linien" in vor)
        and "beim Schlichten" in vor,
        f"Vorschlichten: {vor!r}",
    )
    h.pruefe(panel.ergebnis_vorschlichten.isVisible(), "Satz zum Vorschlichten nicht zu sehen")
    h.bild("1_vorschlichten", panel.form)

    yield from h.warte_auf(lambda: panel.knopf_fertig.isEnabled(), 30000)
    panel.knopf_fertig.click()  # Anlegen
    yield 3000
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster nach „Anlegen“ offen")
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    namen = [o.Label for o in ops]
    h.pruefe(
        namen == ["Rundum schruppen T1", "Rundum vorschlichten T2", "Rundum schlichten T2"],
        f"Operationen: {namen}",
    )
    if len(ops) < 3:
        return
    vor_op, schlicht_op = ops[1], ops[2]
    h.pruefe(vs.ist_vorschlichten(vor_op) and not vs.ist_vorschlichten(schlicht_op), "erkannt?")
    h.pruefe(
        bool(vor_op.NurStueck)
        and abs(vor_op.StueckVon.Value - bereich[0]) < 1e-6
        and abs(vor_op.StueckBis.Value - bereich[1]) < 1e-6,
        f"Stück: {vor_op.NurStueck} {vor_op.StueckVon} {vor_op.StueckBis}",
    )
    h.pruefe(abs(vor_op.Aufmass.Value - 0.3) < 1e-9, f"Aufmaß: {vor_op.Aufmass}")
    h.pruefe(
        vor_op.Schrittweite.Value > schlicht_op.Schrittweite.Value,
        f"Schrittweite {vor_op.Schrittweite} gegen {schlicht_op.Schrittweite}",
    )
    h.pruefe(
        vor_op.ToolController.Label == "T2 Schruppen", f"Controller: {vor_op.ToolController.Label}"
    )
    # Die Spitze bleibt im Stück längs (X: die Stangenachse im Job; A dreht, Z ist der Radius).
    h.pruefe(tuple(vor_op.Stangenachse) == (1.0, 0.0, 0.0), f"Achse: {vor_op.Stangenachse}")
    z_vorschub = [
        b.Parameters["X"] for b in vor_op.Path.Commands if b.Name == "G1" and "X" in b.Parameters
    ]
    h.pruefe(len(z_vorschub) > 10, f"Vorschlichten ohne Bahn: {len(z_vorschub)} Sätze")
    if z_vorschub:
        h.pruefe(
            min(z_vorschub) >= bereich[0] - 1.0 and max(z_vorschub) <= bereich[1] + 1.0,
            f"X {min(z_vorschub):.1f} … {max(z_vorschub):.1f}, Stück {bereich}",
        )
