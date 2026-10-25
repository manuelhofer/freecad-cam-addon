# Die Frage „Wo der Fräser ins Volle eintauchen muss – erst vorbohren?“ (W-039; Manuel,
# 2026-10-25: „hey wie willst du vorgehen sollen wir erst vorborhren … oder sollen wir alles
# rausschruppen und dann schlichten“ – „weg 1 ist so und so [vorschau button] weg 2 ist so und so
# [vorschau button]“). Ein Klotz 120 × 100 × 30 mit einer geschlossenen Tasche 60 × 50, 15 tief;
# der Standardfräser (Ø 12) und ein Bohrer Ø 12,5. Den Boden der Tasche wählen, „Weiter“: Über den
# Strategien steht die Frage, „Erst vorbohren“ gewählt (wie der Haken im Räumen), beide Wege mit
# ihrer Zeit, der Satz nennt das Loch. „Vorschau“ zeigt die Wege im 3D. „Schraubend eintauchen“
# nimmt den Haken „Vorbohren“ ab, die Frage bleibt, „Anlegen“ legt kein Vorbohren an.
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
    tasche = Part.makeBox(60, 50, 15, V(-30, -25, -15))
    kanten = [k for k in tasche.Edges if abs(k.BoundBox.ZLength - 15.0) < 1e-6]
    tasche = tasche.makeFillet(8.0, kanten)
    teil.Shape = Part.makeBox(120, 100, 30, V(-60, -50, -30)).cut(tasche).removeSplitter()
    doc.recompute()
    boden = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if abs(f.BoundBox.ZMin + 15.0) < 1e-6 and abs(f.BoundBox.ZMax + 15.0) < 1e-6
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, boden)
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
    yield 1500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    yield 1000
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    frage = panel.frage_eintauchen
    haken = panel.raeumen.haken_felder["vorbohren"]

    def zeiten():
        return {k: frage.zeiten[k].text() for k in frage.knoepfe}

    h.pruefe(panel.raeumen.aktiv(), "das Räumen nicht angehakt")
    h.pruefe(frage.widget.isVisible(), "keine Frage „Eintauchen“")
    h.pruefe(frage.knoepfe["vorbohren"].isChecked() and haken.isChecked(), "nicht vorgebohrt")
    h.pruefe(all("min" in z for z in zeiten().values()), f"Zeiten: {zeiten()}")
    satz = frage.saetze["vorbohren"].text()
    h.pruefe("1 Loch" in satz and "12,5" in satz, f"Satz: {satz}")
    h.bild("1_frage", panel.form)

    frage.vorschau_knoepfe["vorbohren"].click()
    yield 1000
    gezeigt = getattr(panel._bahnvorschau, "kennung", None)
    h.pruefe(gezeigt == ("eintauchen", "vorbohren"), f"im 3D: {gezeigt}")
    h.bild("2_vorschau_vorbohren")
    frage.vorschau_knoepfe["vorbohren"].click()  # noch ein Klick: weg
    yield 500
    h.pruefe(panel._bahnvorschau.kennung is None, "die Vorschau blieb")

    frage.knoepfe["helix"].click()
    yield 1500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    yield 1000
    h.pruefe(not haken.isChecked(), "„Vorbohren“ blieb angehakt")
    h.pruefe(getattr(panel.raeumen.vorschau, "vorbohren", None) is None, "noch vorgebohrt")
    h.pruefe(frage.widget.isVisible() and frage.knoepfe["helix"].isChecked(), "Frage weg")
    h.pruefe(all("min" in z for z in zeiten().values()), f"Zeiten danach: {zeiten()}")
    h.bild("3_schraubend", panel.form)

    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    namen = [o.Label for o in job.Operations.Group]
    h.pruefe(namen and not any("Vorbohren" in n for n in namen), f"Operationen: {namen}")
