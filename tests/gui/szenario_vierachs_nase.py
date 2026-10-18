# Die Nase (W-027; Manuel, 2026-10-17, Frage 2: „ja, die Option soll so sein, wichtig ist, dass
# danach die Kugel nicht nochmal alles das fährt, was schon weg ist“). Welle Ø 60 × 120 längs Z
# mit einer Flosse aus fünf ebenen Flächen – zwei Seiten, die Spitze, oben und unten schräg –,
# wie in beispiele/testteil_4achs_nase.FCStd; Stange Ø 90, T1 Schaftfräser Ø 12 (Schruppen und
# Planen), T2 Kugelfräser Ø 6 (Schlichten). Die fünf Flächen angeklickt: „Plan indexiert“ geht an
# (Seiten und Spitze), „Rundum schlichten“ bleibt an, fährt aber nur die zwei schrägen Flächen in
# Linien längs – der Satz darunter sagt es. „Plan indexiert“ aus: die Kugel fährt alle fünf. Nur
# Seiten und Spitze gewählt: „Rundum schlichten“ geht aus („Vorschlag: aus – Plan indexiert macht
# alle gewählten Flächen fertig“); die schrägen wieder dazu: an. „Anlegen“: „Rundum schruppen
# T1“, „Plan indexiert T1“ mit den drei ebenen und der Stirnseite der Welle neben der Spitze (mit
# dem Umfang, Auftrag 2), „Rundum schlichten T2“ mit den zwei schrägen in Linien.
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
    from camaddon import vierachs_bahn as vb
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_plan as vplan
    from camaddon import vierachs_rohteil as vr
    from camaddon import vierachs_schlichten as vs
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26)
    t1.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.PLANEN, ae=8, ap=2, vc=150, fz=0.08),
        wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=150, fz=0.08),
    ]
    t2 = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=6, vc=150, fz=0.04)]
    wz.Bibliothek([t1, t2]).speichern()

    doc = FreeCAD.newDocument("Nase")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Nase")
    welle = Part.makeCylinder(30, 120, V(0, 0, -120), V(0, 0, 1))
    # Die Flosse im Schnitt (x, z): Spitze bei x −5,5 über der Stirn, oben und unten schräg.
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

    def ebene_mit(richtung, hoechstens=None):
        return next(
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if vr.ist_eben(f)
            and (vr.aussennormale(f) - V(*richtung)).Length < 1e-2
            and (hoechstens is None or 100 < f.Area < hoechstens)
        )

    stirn = ebene_mit((0, 0, 1), 2700)  # die Stirn Ø 60 bei z 0 (die Flosse nimmt ein Stück)
    seiten = [ebene_mit((0, -1, 0)), ebene_mit((0, 1, 0))]
    spitze = ebene_mit((1, 0, 0))
    schraeg = [ebene_mit((-0.74, 0, 0.68)), ebene_mit((-0.68, 0, -0.74))]
    eben = sorted(seiten + [spitze], key=lambda n: int(n[4:]))
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
    klon = vr.modell(job)

    def klick(name):
        Gui.Selection.addSelection(doc.Name, klon.Name, name)

    # --- Die fünf Flächen der Flosse -----------------------------------------------------------
    for name in seiten + [spitze] + schraeg:
        klick(name)
        yield 300
    yield 500
    h.pruefe(sorted(panel.flaechen()) == sorted(eben + schraeg), f"gewählt: {panel.flaechen()}")
    h.pruefe(panel.mit_plan.isChecked(), f"Plan indexiert aus: {panel.plan_grund.text()!r}")
    h.pruefe(
        panel.plan_grund.text().startswith("Vorschlag: an"),
        f"Grund Plan: {panel.plan_grund.text()!r}",
    )
    h.pruefe(panel.mit_schlichten.isChecked(), "„Rundum schlichten“ mit den schrägen Flächen aus")
    kugel = sorted(panel._schlicht_flaechen(), key=lambda n: int(n[4:]))
    h.pruefe(kugel == sorted(schraeg, key=lambda n: int(n[4:])), f"für die Kugel: {kugel}")
    text = panel.erklaerung_schlichten.text()
    h.pruefe(
        "Die Kugel fährt nur " in text and "macht „Plan indexiert“ fertig" in text,
        f"Satz unter „Rundum schlichten“: {text!r}",
    )
    h.pruefe(panel.muster() == vb.LINIEN, f"Muster: {panel.muster()}")
    yield from h.warte_auf(
        lambda: panel.vorschau is not None
        and panel.vorschau_schlichten is not None
        and panel.vorschau_plan is not None,
        90000,
    )
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    print("Schruppen:", panel.ergebnis.text())
    print("Plan:", panel.ergebnis_plan.text())
    print("Schlichten:", panel.ergebnis_schlichten.text())
    h.pruefe(
        "Linien längs" in panel.ergebnis_schlichten.text(),
        f"Schlichten: {panel.ergebnis_schlichten.text()!r}",
    )
    # Die Stirnseite der Welle neben der Spitze in derselben Stellung mit dem Umfang (Auftrag 2;
    # Manuel, 2026-10-18: „So bauen, mit Ausspann-Hinweis“) – als Haken, vorbelegt an.
    h.pruefe(
        panel.plan_stirnseite.isVisible()
        and panel.plan_stirnseite_an()
        and "mit dem Umfang" in panel.plan_stirnseite_grund.text(),
        f"Stirnseite: {panel.plan_stirnseite_grund.text()!r}",
    )
    h.bild("1_fuenf_flaechen", panel.form)
    h.bild("1b_fuenf_flaechen_3d")

    # --- „Plan indexiert“ aus: die Kugel fährt alle fünf ------------------------------------------
    panel.mit_plan.setChecked(False)
    yield 300
    alle = sorted(panel._schlicht_flaechen(), key=lambda n: int(n[4:]))
    h.pruefe(alle == sorted(eben + schraeg, key=lambda n: int(n[4:])), f"ohne Plan: {alle}")
    h.pruefe(
        panel.erklaerung_schlichten.text() == tr_text(gui_vierachs, "va.schlichten.text"),
        f"ohne Plan: {panel.erklaerung_schlichten.text()!r}",
    )
    h.pruefe(panel.mit_schlichten.isChecked(), "ohne Plan: „Rundum schlichten“ aus")
    panel.mit_plan.setChecked(True)
    yield 300

    # --- Nur Seiten und Spitze: für die Kugel bleibt nichts – der Haken geht aus ------------------
    for name in schraeg:
        klick(name)  # ein zweiter Klick nimmt die Fläche heraus
        yield 300
    yield 500
    h.pruefe(sorted(panel.flaechen()) == sorted(eben), f"Seiten und Spitze: {panel.flaechen()}")
    h.pruefe(panel.mit_plan.isChecked(), "Plan indexiert für Seiten und Spitze aus")
    h.pruefe(not panel.mit_schlichten.isChecked(), "„Rundum schlichten“ ohne Rest für die Kugel an")
    text = panel.erklaerung_schlichten.text()
    h.pruefe(text.startswith("Vorschlag: aus – „Plan indexiert“ macht"), f"Satz: {text!r}")
    h.bild("2_nur_ebene", panel.form)
    for name in schraeg:
        klick(name)
        yield 300
    yield 500
    h.pruefe(panel.mit_schlichten.isChecked(), "„Rundum schlichten“ mit den schrägen wieder an")
    yield from h.warte_auf(
        lambda: panel.vorschau is not None
        and panel.vorschau_schlichten is not None
        and panel.vorschau_plan is not None,
        90000,
    )

    # --- Anlegen ----------------------------------------------------------------------------------
    panel.accept()
    yield 3000
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster nach „Anlegen“ offen")
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    schruppen = [o for o in ops if vo.ist_schruppen(o)]
    plan = [o for o in ops if vplan.ist_plan(o)]
    # Dazu „Rundum vorschlichten“, wenn die Kugel nach dem Schruppen viel nähme (W-031, seit
    # P-2026-10-18-80 von sich aus angehakt).
    schlichten = [o for o in ops if vs.ist_schlichten(o) and not vs.ist_vorschlichten(o)]
    h.pruefe(
        len(schruppen) == 1 and len(plan) == 1 and len(schlichten) == 1, f"Operationen: {namen}"
    )
    if plan:  # die Operation trägt die Wahl, die ebenen sucht sie sich selbst heraus
        flaechen = sorted(plan[0].Flaechen, key=lambda n: int(n[4:]))
        alle = sorted(eben + schraeg, key=lambda n: int(n[4:]))
        h.pruefe(flaechen == alle, f"Plan indexiert: {flaechen}")
        h.pruefe(plan[0].Zeilen > 0, f"Plan indexiert: {plan[0].Zeilen} Zeilen")
        h.pruefe(
            plan[0].Stirnseite and plan[0].Ebenen == len(eben) + 1,
            f"Plan indexiert: Stirnseite {plan[0].Stirnseite}, {plan[0].Ebenen} Flächen",
        )
    if schlichten:
        flaechen = sorted(schlichten[0].Flaechen, key=lambda n: int(n[4:]))
        h.pruefe(flaechen == sorted(schraeg, key=lambda n: int(n[4:])), f"Schlichten: {flaechen}")
        h.pruefe(schlichten[0].Muster == "Linien", f"Muster: {schlichten[0].Muster}")
        h.pruefe(schlichten[0].Linien > 0, f"Linien: {schlichten[0].Linien}")
    h.bild("3_angelegt")
    FreeCAD.closeDocument(doc.Name)
    yield 300


def tr_text(modul, schluessel):
    return modul.tr(schluessel)
