# Kommt der Fräser nicht hinein: Hinweis und Knopf statt Tausch (Manuel, 2026-10-17, Frage 1: „ein
# hinweis an den anwender .. und dann mit einem klick kleinen fräser übernehmen klar !!“). Ein Block
# 80 × 40 × 20 mit einer Nut 10 breit, 5 tief; die Werkzeugkiste der Tests (T1 Ø 12, T3 Ø 6 …). Den
# Nutgrund anklicken, „Bearbeitung“, Schritt 2: Das Räumen behält T1 Ø 12, rot steht „… kommt nicht
# in Face… – für Räumen passt T3 …“, darunter der Knopf „„T3 …“ übernehmen“. Geklickt: Das Räumen
# nimmt T3, der rote Satz und der Knopf sind weg.
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

    from camaddon import gui_bearbeitung
    from camaddon import werkzeuge as wz

    wz.Bibliothek(wz.testkiste()).speichern()
    V = FreeCAD.Vector
    doc = FreeCAD.newDocument("Nut")
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeBox(80, 40, 20).cut(Part.makeBox(60, 10, 5, V(10, 15, 15)))
    doc.recompute()
    grund = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if abs(f.BoundBox.ZMin - 15) < 1e-6 and abs(f.BoundBox.ZMax - 15) < 1e-6
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, grund)
    yield 300
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(
        lambda: getattr(gui_bearbeitung.BearbeitungPanel.offen, "job", None) is not None, 20000
    )
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Job")
    if panel is None or panel.job is None:
        return
    panel.knopf_weiter.click()  # Schritt 2
    yield from h.warte_auf(lambda: panel.knopf_passt.isVisible(), 60000)
    raeumen = panel.raeumen
    h.pruefe(
        raeumen.fraeser() is not None and raeumen.fraeser().nummer == 1,
        f"Räumen hat selbst getauscht: {raeumen.fraeser()}",
    )
    text = panel.passt_text.text()
    h.pruefe(
        panel.passt_text.isVisible() and grund in text and "passt T3" in text,
        f"roter Satz: {text!r}",
    )
    h.pruefe(
        panel.knopf_passt.text().startswith("„T3")
        and panel.knopf_passt.text().endswith("übernehmen"),
        f"Knopf: {panel.knopf_passt.text()!r}",
    )
    h.bild("1_hinweis", panel.form)
    panel.knopf_passt.click()
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 120000)
    yield 500
    h.pruefe(
        raeumen.fraeser() is not None and raeumen.fraeser().nummer == 3,
        f"nach dem Klick: {raeumen.fraeser()}",
    )
    h.pruefe(
        not panel.passt_text.isVisible() and not panel.knopf_passt.isVisible(),
        f"nach dem Klick noch: {panel.passt_text.text()!r}",
    )
    h.bild("2_uebernommen", panel.form)
    panel.reject()
    yield 800
