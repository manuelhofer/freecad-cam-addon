# Die Frage „In welcher Reihenfolge – erst alles schruppen, dann schlichten?“ (W-039; Manuel,
# 2026-10-25: „oder sollen wir alles rausschruppen und dann schlichten“; abends: Bohren, Senken
# und Gewinde zwischen Schruppen und Schlichten). Ein Klotz 120 × 100 × 30 mit einer geschlossenen
# Tasche 60 × 50, 15 tief, und einer Bohrung Ø 16 durch; der Standardfräser (Ø 12) und ein Bohrer
# Ø 12,5. „Alles aus dieser Aufspannung“: Über den Strategien steht die Frage, „Wie vorgeschlagen“
# gewählt; je Weg die Folge als Satz mit den Werkzeugwechseln und eine Zeit – vorgeschlagen kommt
# „Bohrung fräsen“ vor der Kontur, „Erst alles schruppen“ die Kontur davor. Gewählt und
# „Anlegen“: der Job in dieser Folge.
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
    from camaddon import werkzeuge as wz

    bohrer = wz.Werkzeug(nummer=5, name="HSS 12,5", art=wz.BOHRER, durchmesser=12.5, schneiden=2,
                         schneidenlaenge=100.0, spitzenwinkel=118.0, schneidstoff=wz.HSS)  # fmt: skip
    bohrer.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.1)]
    wz.Bibliothek([wz.standardwerkzeug(), bohrer]).speichern()

    doc = FreeCAD.newDocument("Klotz")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Klotz")
    tasche = Part.makeBox(60, 50, 15, V(-45, -25, -15))
    kanten = [k for k in tasche.Edges if abs(k.BoundBox.ZLength - 15.0) < 1e-6]
    tasche = tasche.makeFillet(8.0, kanten)
    loch = Part.makeCylinder(8.0, 30.0, V(40, 30, -30))
    teil.Shape = Part.makeBox(120, 100, 30, V(-60, -50, -30)).cut(tasche).cut(loch).removeSplitter()
    doc.recompute()
    oben = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if abs(f.BoundBox.ZMin) < 1e-6 and abs(f.BoundBox.ZMax) < 1e-6
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, oben)
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    panel.knopf_weiter.click()
    yield 800
    panel.aus_der_aufspannung()
    yield 1500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 600000)
    yield 1000
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 600000)
    frage = panel.frage_reihenfolge
    aktiv = [b.s.kennung for b in panel.aktive_bloecke()]
    h.pruefe(
        frage.widget.isVisible() and frage.knoepfe["vorgeschlagen"].isChecked(),
        f"keine Frage „Reihenfolge“ (angehakt: {aktiv})",
    )
    if not frage.widget.isVisible():
        return
    vorgeschlagen = frage.saetze["vorgeschlagen"].text()
    schruppen = frage.saetze["schruppen"].text()
    zeiten = {k: frage.zeiten[k].text() for k in frage.knoepfe}
    h.pruefe(all("min" in z for z in zeiten.values()), f"Zeiten: {zeiten}")
    h.pruefe("Werkzeugwechsel" in vorgeschlagen and "→" in vorgeschlagen, vorgeschlagen)

    def vor(satz, a, b):
        return a in satz and b in satz and satz.index(a) < satz.index(b)

    h.pruefe(vor(vorgeschlagen, "Bohrung fräsen", "Kontur"), f"vorgeschlagen: {vorgeschlagen}")
    h.pruefe(vor(schruppen, "Kontur", "Bohrung fräsen"), f"schruppen zuerst: {schruppen}")
    h.bild("1_frage", panel.form)

    frage.knoepfe["schruppen"].click()
    yield 1500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 600000)
    yield 1000
    h.pruefe(frage.knoepfe["schruppen"].isChecked(), "„Erst alles schruppen“ nicht gewählt")
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    namen = [o.Label for o in job.Operations.Group]
    kontur = next((i for i, n in enumerate(namen) if n.startswith("Kontur")), None)
    bohrung = next((i for i, n in enumerate(namen) if n.startswith("Bohrung fräsen")), None)
    h.pruefe(
        kontur is not None and bohrung is not None and kontur < bohrung, f"Operationen: {namen}"
    )
