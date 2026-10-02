# Die Eintauchstelle der Nut (W-012 E1; Manuel, 2026-10-02: „an einer von mir aus wählbaren
# Position in der Nut … aber natürlich mit Vorschlag“, Frage 2: a): Platte 100 × 60 × 20 mit
# einem Langloch, 20 breit, 10 tief, Halbkreise um (25, 20) und (55, 20); der Standardfräser.
# Den Grund anklicken, „Bearbeitung“, bis zu den Einstellungen: Unter der Nut „Eintauchen bei“ mit
# „Vorschlag: abwechselnd an den Enden“, den Enden X 25 und X 55 und der Mitte X 40. Die Mitte
# gewählt: Die Helix taucht dort ein. „Im Bild wählen …“ und bei x 32,5 in die Nut geklickt:
# „angeklickt X 32,5 Y 20“. „Anlegen“: Die Operation merkt sich die Stelle, ihre Helix dreht um
# (32,5, 20); zum Ändern geöffnet steht die Stelle wieder in der Liste.
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
    from camaddon import nut as nu
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()

    doc = FreeCAD.newDocument("Nut")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    nut = Part.makeBox(30, 20, 11, V(25, 10, 10))
    nut = nut.fuse(Part.makeCylinder(10, 11, V(25, 20, 10)))
    nut = nut.fuse(Part.makeCylinder(10, 11, V(55, 20, 10)))
    teil.Shape = Part.makeBox(100, 60, 20).cut(nut).removeSplitter()
    doc.recompute()
    grund = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if abs(f.BoundBox.ZMin - 10) < 1e-6 and abs(f.BoundBox.ZMax - 10) < 1e-6
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, grund)
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)  # die Koordinaten wie im Modell
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    block = panel.nut
    panel.knopf_weiter.click()
    yield from h.warte_auf(lambda: block.vorschau is not None, 180000)
    yield 1500
    h.pruefe(block.aktiv(), "die Nut nicht angehakt")
    panel.knopf_weiter.click()
    yield 800

    def zeile():
        return next(iter(block._stellen_zeilen.values()), None)

    teile = zeile()
    h.pruefe(teile is not None and block.stellen_box.isVisible(), "keine Zeile „Eintauchen bei“")
    if teile is None:
        return
    wahl = teile["wahl"]
    texte = [wahl.itemText(i) for i in range(wahl.count())]
    h.pruefe(
        texte == ["Vorschlag: abwechselnd an den Enden", "Ende X 25 Y 20", "Ende X 55 Y 20",
                  "Mitte X 40 Y 20"],
        f"Liste: {texte}",
    )  # fmt: skip
    h.bild("1_eintauchen_vorschlag", panel.form)

    # --- Die Mitte gewählt -------------------------------------------------------------------
    wahl.setCurrentIndex(3)
    yield from h.warte_auf(
        lambda: block.vorschau is not None and block.vorschau.stellen[0][1] == 0.5, 60000
    )
    yield 800
    stelle = block.vorschau.stellen[0]
    h.pruefe(stelle[1] == 0.5 and not stelle[2], f"Mitte: {stelle[:3]}")

    # --- Im Bild gewählt: bei x 32,5 in die Nut geklickt --------------------------------------
    teile["im_bild"].click()
    yield 300
    h.pruefe(block.stelle_waehlt is not None, "„Im Bild wählen …“ wartet nicht auf einen Klick")
    panel.angeklickt(vr.modell(job).Name, grund, (32.5, 20.0, 10.0))
    yield from h.warte_auf(
        lambda: block.vorschau is not None
        and abs((block.vorschau.stellen[0][1] or 0) - 0.25) < 1e-6,
        60000,
    )
    yield 800
    text = teile["wahl"].currentText()
    h.pruefe(text == "angeklickt X 32,5 Y 20", f"angeklickt: {text!r}")
    h.pruefe(not teile["im_bild"].isChecked(), "„Im Bild wählen …“ noch gedrückt")
    h.bild("2_eintauchen_angeklickt", panel.form)

    # --- Anlegen: die Operation merkt sich die Stelle -----------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = [o for o in job.Operations.Group if nu.ist_nut(o)]
    h.pruefe(len(ops) == 1, f"Operationen: {[o.Label for o in job.Operations.Group]}")
    if not ops:
        return
    op = ops[0]
    stellen = nu.eintauchstellen(op)
    h.pruefe(list(stellen.values()) == [0.25], f"Eintauchstellen: {list(op.Eintauchstellen)}")
    mitten = helix_mitten(op)
    h.pruefe((32.5, 20.0) in mitten, f"Helix um {sorted(mitten)[:5]}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("3_angelegt")

    # Zum Ändern geöffnet: die Stelle steht wieder in der Liste.
    gui_bearbeitung.bearbeiten(op)
    yield 1500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    if panel is not None:
        yield from h.warte_auf(lambda: panel.nut.vorschau is not None, 120000)
        yield 800
        teile = next(iter(panel.nut._stellen_zeilen.values()), None)
        text = teile["wahl"].currentText() if teile else ""
        h.pruefe(text == "angeklickt X 32,5 Y 20", f"beim Ändern: {text!r}")
        panel.reject()
        yield 800
    FreeCAD.closeDocument(doc.Name)
    yield 300


def helix_mitten(op):
    """Die Mitten der Bögen (G2/G3), auf denen z fällt – die Helix."""
    x = y = z = None
    mitten = set()
    for c in op.Path.Commands:
        p = c.Parameters
        faellt = z is not None and "Z" in p and float(p["Z"]) < float(z) - 1e-9
        if c.Name in ("G2", "G3", "G02", "G03") and x is not None and faellt:
            mitten.add((round(x + float(p.get("I", 0.0)), 3), round(y + float(p.get("J", 0.0)), 3)))
        x, y, z = p.get("X", x), p.get("Y", y), p.get("Z", z)
    return mitten
