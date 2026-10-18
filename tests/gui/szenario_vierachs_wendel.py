# Der Wendel nach (W-030; Manuel, 2026-10-18 an seinem Wendel-Testteil: „die wendel ist entgegen
# der drehrichtung ... dann muss man vll mal hinten anfangen um die wendel zu fahren ??“ – zum
# Vorschlag „Ja, vorgewählt bei Wendelnut“). Welle Ø 80 × 65 längs Z mit einer runden Nut R 11,
# deren Mitte auf dem Umfang liegt, als Wendel mit 60 mm Steigung – wie sein Teil. Stange Ø 80,
# T1 Schaftfräser Ø 12, T2 Kugelfräser Ø 12. Schritt 2: Das Muster ist „Der Wendel nach“, darunter
# „Vorschlag: der Wendel nach – die Nut läuft eingängig und rechtsgängig mit 60 mm Steigung um …“;
# die Vorschau sagt „→ … Bahnen der Wendel nach, etwa … min“; das Schruppen ist „Der Wendelnut nach“
# angehakt und fräst nur in der Nut, nie über dem Ø 80. Danach bleibt der Kugel wenig: der Satz
# darunter grau, kein Vorschlichten. „Anlegen“: „Rundum schruppen T1“ (Wendel) und „Rundum
# schlichten T2“ mit dem Muster „Wendel“; im Schlichten dreht C (hier A) im ganzen Programm nur in
# eine Richtung.
import FreeCAD
import FreeCADGui as Gui
import Part

V = FreeCAD.Vector


def wendelteil(doc):
    """Ø 80 × 65 (z 0 … 65) mit einer runden Nut R 11 als Wendel, Steigung 60, wie Manuels Teil:
    PartDesign, Kreis auf der XZ-Ebene, Subtraktive Wendel um Z (mit Part schneidet das Rohr der
    Wendel die Welle nicht – OpenCascade lässt sie unverändert)."""
    import Sketcher  # noqa: F401 – lädt die Skizzen

    body = doc.addObject("PartDesign::Body", "Koerper")
    ursprung = {f.Role: f for f in body.Origin.OriginFeatures}

    def skizze(name, ebene, mitte, radius):
        sk = body.newObject("Sketcher::SketchObject", name)
        if "AttachmentSupport" in sk.PropertiesList:
            sk.AttachmentSupport = [(ursprung[ebene], "")]
        else:
            sk.Support = [(ursprung[ebene], "")]
        sk.MapMode = "FlatFace"
        sk.addGeometry(Part.Circle(mitte, V(0, 0, 1), radius))
        return sk

    pad = body.newObject("PartDesign::Pad", "Welle")
    pad.Profile = skizze("SkizzeWelle", "XY_Plane", V(0, 0, 0), 40)
    pad.Length = 65
    nut = body.newObject("PartDesign::SubtractiveHelix", "Wendel")
    nut.Profile = skizze("SkizzeNut", "XZ_Plane", V(40, 76, 0), 11)
    nut.ReferenceAxis = (ursprung["Z_Axis"], [""])
    nut.Pitch = 60
    nut.Height = 100
    nut.Reversed = True
    doc.recompute()
    return body


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
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import vierachs_schlichten as vs
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(nummer=1, durchmesser=12, schneiden=4, schneidenlaenge=26)
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=5.4, ap=6, vc=150, fz=0.07)]
    t2 = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=12, schneiden=2)
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.6, ap=0.3, vc=140, fz=0.09)]
    wz.Bibliothek([t1, t2]).speichern()

    doc = FreeCAD.newDocument("Wendel")
    doc.UndoMode = 1
    teil = wendelteil(doc)
    h.pruefe(teil.Shape.isValid() and teil.Shape.Volume < 0.95 * 3.1416 * 40**2 * 65, "keine Nut")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f)
        and (vr.aussennormale(f) - V(0, 0, 1)).Length < 1e-2
        and f.CenterOfMass.z > 60
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
    panel.feld_stange.setText("80")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.accept()  # Weiter
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    job = panel.job
    if panel.mit_plan.isChecked():
        panel.mit_plan.setChecked(False)
    yield from h.warte_auf(lambda: panel._wendel is not None, 60000)
    w = panel._wendel
    h.pruefe(
        w is not None and abs(abs(w.steigung) - 60) < 0.5 and w.gaenge == 1,
        f"Wendel: {w}",
    )
    grund = panel.muster_grund.text()
    h.pruefe(panel.muster() == vb.WENDEL, f"Muster: {panel.muster()}")
    h.pruefe(
        grund.startswith("Vorschlag: der Wendel nach – die Nut läuft eingängig und ")
        and "mit 60 mm Steigung" in grund,
        f"Grund: {grund!r}",
    )
    h.pruefe(panel.schlichten_querachse.isEnabled(), "Querachse mit der Wendel gesperrt")
    # Das Schruppen der Wendelnut nach: zu sehen und angehakt (Manuel: „zum schruppen is das
    # definitv schöner .. so will ichs haben“).
    h.pruefe(
        panel.schruppen_wendel.isVisible() and panel.schruppen_wendel_an(),
        "„Der Wendelnut nach“ beim Schruppen nicht angehakt",
    )
    yield from h.warte_auf(lambda: panel.vorschau_schlichten is not None, 120000)
    ergebnis = panel.ergebnis_schlichten.text()
    print("Schlichten:", ergebnis)
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    bahnen = getattr(panel.vorschau_schlichten, "wendel_bahnen", 0)
    h.pruefe(
        ergebnis.startswith("→ ") and "Bahnen der Wendel nach, etwa" in ergebnis,
        f"Ergebnis: {ergebnis!r}",
    )
    h.pruefe(10 <= bahnen <= 45, f"{bahnen} Bahnen")
    h.pruefe(
        "Bahnen der Wendelnut nach" in panel.ergebnis.text(),
        f"Schruppen: {panel.ergebnis.text()!r}",
    )
    yield from h.warte_auf(lambda: panel._rest_auftrag is None, 120000)
    yield from h.warte_auf(
        lambda: panel._vor_auftrag is None and panel._vor_rest_auftrag is None, 120000
    )
    rest = panel.rest_schlichten.text()
    h.pruefe(
        rest.startswith("Rest für die Kugel nach dem Schruppen")
        and not panel.vorschlichten.isChecked(),
        f"Rest: {rest!r}",
    )
    h.bild("1_wendel", panel.form)

    yield from h.warte_auf(lambda: panel.knopf_fertig.isEnabled(), 30000)
    panel.knopf_fertig.click()  # Anlegen
    yield 3000
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster nach „Anlegen“ offen")
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    namen = [o.Label for o in ops]
    # Der Wendelnut nach geschruppt bleibt der Kugel wenig (an Manuels Teil 5,2 statt 20,1 mm²):
    # kein Vorschlichten.
    h.pruefe(namen == ["Rundum schruppen T1", "Rundum schlichten T2"], f"Operationen: {namen}")
    if len(ops) < 2:
        return
    op = ops[1]
    h.pruefe(op.Muster == "Wendel", f"Muster: {op.Muster}")
    schrupp = ops[0]
    h.pruefe(bool(getattr(schrupp, "Wendel", False)), "Rundum schruppen ohne „Wendel“")
    # Die Stange ist Ø 80 wie das Teil: Das Schruppen fräst nur in der Nut, nie über dem Ø 80.
    radius_x = [
        b.Parameters["Z"]
        for b in schrupp.Path.Commands
        if b.Name == "G1" and "Z" in b.Parameters and b.Parameters.get("F", 1) > 0
    ]
    h.pruefe(
        radius_x and max(radius_x) <= 40.0 + 0.3 + 0.05,
        f"Schruppen über dem Ø 80: bis r {max(radius_x, default=0):.2f}",
    )
    h.pruefe(not vs.ist_vorschlichten(op), "das Schlichten gilt als Vorschlichten")
    befehle = op.Path.Commands
    h.pruefe(sum(1 for b in befehle if b.Name == "G1") > 200, f"{len(befehle)} Befehle")
    # C (an dieser Stange A) dreht im ganzen Programm nur in eine Richtung – auch zwischen den
    # Bahnen (Manuel: „C dreht nicht zurück“).
    rund = [b.Parameters[k] for b in befehle for k in ("A", "B", "C") if k in b.Parameters]
    schritte_rund = [b - a for a, b in zip(rund, rund[1:], strict=False) if abs(b - a) > 1e-6]
    h.pruefe(
        schritte_rund and (all(s > 0 for s in schritte_rund) or all(s < 0 for s in schritte_rund)),
        f"Rundachse dreht zurück: {sum(1 for s in schritte_rund if s > 0)} vor, "
        f"{sum(1 for s in schritte_rund if s < 0)} zurück",
    )
