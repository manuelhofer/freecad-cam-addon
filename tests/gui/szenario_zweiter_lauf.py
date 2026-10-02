# Ein Teil, ein Job (W-012 M2; Manuel, 2026-10-02: „ein komplexes Teil durch Anklicken
# verschiedener Flächen bearbeiten“, Frage 1: a) an Manuels Klotz: 100 × 100, oben bei z 0 ein
# Zapfen Ø 30 bei x25 y25, rundum der Boden bei −10, darin eine Nut 20 × 60 um x −10 y 0, Grund −15.
# Erster Lauf: den Boden anklicken, „Bearbeitung“, „Anlegen“ – ein Job, eine Operation. Zweiter
# Lauf: den Grund der Nut am Teil im Job anklicken, „Bearbeitung“: Schritt 1 sagt „In den Job „…“ –
# 1 Operation: …“, Maschine und Rohteil grau; in Schritt 2 hat die Nut den Haken und sagt grau
# „noch … – … schon weggenommen“; „Anlegen“: weiter ein Job, jetzt mit beiden, die Nut ab −10.
# Dritter Lauf: „Neuer Job …“ öffnet den Assistenten mit einem neuen Job; „Abbrechen“ nimmt ihn
# zurück.
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

    from camaddon import gui_bearbeitung
    from camaddon import job_schnittwerte as js
    from camaddon import nut as nu
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()

    doc = FreeCAD.newDocument("Klotz")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Klotz")
    klotz = Part.makeBox(100, 100, 20, V(-50, -50, -30))
    klotz = klotz.fuse(Part.makeCylinder(15, 10, V(25, 25, -10)))
    nut = Part.makeBox(40, 20, 6, V(-30, -10, -15))
    nut = nut.fuse(Part.makeCylinder(10, 6, V(-30, 0, -15)))
    nut = nut.fuse(Part.makeCylinder(10, 6, V(10, 0, -15)))
    teil.Shape = klotz.cut(nut).removeSplitter()
    doc.recompute()

    def flaeche(z):
        return next(
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if abs(f.BoundBox.ZMin - z) < 1e-6 and abs(f.BoundBox.ZMax - z) < 1e-6
        )

    boden, grund = flaeche(-10.0), flaeche(-15.0)
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    gui_bearbeitung.nullpunkt_vorgeben(None)  # die Koordinaten wie im Modell

    def oeffnen(objekt, name):
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, objekt.Name, name)
        yield 500
        Gui.runCommand("CamAddon_Bearbeitung")
        yield 2000

    # --- Erster Lauf: der Boden um den Zapfen ----------------------------------------------------
    yield from oeffnen(teil, boden)
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    h.pruefe(not panel.dazu_zeile.isVisible(), "erster Lauf: „In den Job“ sichtbar")
    panel.knopf_weiter.click()
    yield from h.warte_auf(
        lambda: any(b.vorschau is not None for b in panel.aktive_bloecke()), 180000
    )
    yield 1500
    h.pruefe(panel.accept() is True, "erster Lauf: „Anlegen“ ging nicht")
    yield 3000
    erste = [o.Label for o in job.Operations.Group]
    h.pruefe(len(erste) == 1, f"erster Lauf: {erste}")

    # --- Zweiter Lauf: die Nut am Teil im Job -----------------------------------------------------
    yield from oeffnen(vr.modell(job), grund)
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is job, "zweiter Lauf: nicht im Job des ersten")
    if panel is None or panel.job is not job:
        return
    text = panel.dazu_text.text()
    h.pruefe(
        panel.dazu_zeile.isVisible()
        and text.startswith(f"In den Job „{job.Label}“ – 1 Operation: "),
        f"Zeile: {text!r}",
    )
    h.pruefe(not panel.wahl_maschine.isEnabled(), "Maschine änderbar")
    h.pruefe(not panel.knopf_rohteil_quader.isEnabled(), "Rohteil änderbar")
    h.pruefe(
        panel.anleitung.text().startswith("Das Teil hat schon einen Job"),
        f"Anleitung: {panel.anleitung.text()!r}",
    )
    h.bild("1_in_den_job", panel.form)
    panel.knopf_weiter.click()
    yield from h.warte_auf(lambda: panel.nut.vorschau is not None, 180000)
    yield 1500
    material = panel.nut.material.text()
    h.pruefe(panel.nut.aktiv(), "die Nut nicht angehakt")
    # Nur die Operation des ersten Laufs hat weggenommen – Planfräsen und Räumen treten hier am
    # Grund der Nut gegen sie an und kommen nicht davor.
    h.pruefe(
        material.startswith("noch 5,") and material.endswith(f"hat „{erste[0]}“ schon weggenommen"),
        f"Materialzeile: {material!r}",
    )
    h.bild("2_nut_mit_materialstand", panel.form)
    h.pruefe(panel.accept() is True, "zweiter Lauf: „Anlegen“ ging nicht")
    yield 3000
    jobs = js.jobs(doc)
    ops = list(job.Operations.Group)
    h.pruefe(len(jobs) == 1 and len(ops) == 2, f"Jobs {len(jobs)}, {[o.Label for o in ops]}")
    nuten = [o for o in ops if nu.ist_nut(o)]
    if nuten:
        z = next(float(c.Parameters["Z"]) for c in nuten[0].Path.Commands
                 if c.Name in ("G1", "G01") and "Z" in c.Parameters)  # fmt: skip
        h.pruefe(abs(z + 10.0) < 0.01, f"Nut beginnt bei {z}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("3_ein_job_zwei_operationen")

    # --- Dritter Lauf: „Neuer Job …“ – eine zweite Aufspannung ----------------------------------
    yield from oeffnen(vr.modell(job), boden)
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is job, "dritter Lauf: nicht im Job")
    if panel is None:
        return
    panel.knopf_neuer_job.click()
    yield from h.warte_auf(
        lambda: (
            gui_bearbeitung.BearbeitungPanel.offen is not None
            and gui_bearbeitung.BearbeitungPanel.offen is not panel
            and gui_bearbeitung.BearbeitungPanel.offen.job is not None
        ),
        20000,
    )
    yield 1500
    neu = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(
        neu is not None and neu.job is not job and not neu.dazu_zeile.isVisible(),
        "„Neuer Job …“: kein neuer Job",
    )
    h.pruefe(len(js.jobs(doc)) == 2, f"mit dem neuen: {len(js.jobs(doc))} Jobs")
    if neu is not None:
        neu.reject()
    yield 1500
    h.pruefe(len(js.jobs(doc)) == 1, f"nach „Abbrechen“: {len(js.jobs(doc))} Jobs")
    FreeCAD.closeDocument(doc.Name)
    yield 300
