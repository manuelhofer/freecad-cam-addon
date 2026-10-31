# Fehlt das Werkzeug für eine Bohrung, nennt der Block eins aus dem Katalog der Hersteller
# (Gedächtnis „Empfehlen über das Magazin hinaus“). Ein Klotz 80 × 60 × 30 mit einer Sackbohrung
# Ø 6,75, 20 tief (das Kernloch von M8 nach gewinde.kernloch: 8 − 1,25); in der
# Werkzeugverwaltung nur der Standardfräser. Die Bohrung wählen, „Weiter“: „Gewinde bohren“ und
# „Bohren“ passen nicht – darunter „Im Katalog der Hersteller …“ mit Gewindebohrern M8 × 1,25 bzw.
# Bohrern Ø 6,75 als Links (der Katalog wird im Faden gelesen, die Sätze kommen danach). Dann die
# durchgehende Bohrung Ø 8 gewählt: „Reiben“ nennt Reibahlen Ø 8 aus dem Katalog. „Gewinde fräsen“
# nennt für Ø 6,75 Gewindefräser, deren Steigung ein M8 daraus macht.
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

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    doc = FreeCAD.newDocument("Klotz")
    teil = doc.addObject("Part::Feature", "Klotz")
    loch = Part.makeCylinder(3.375, 20, V(0, 0, -20))
    durch = Part.makeCylinder(4.0, 40, V(25, 0, -35))  # Ø 8 durchgehend: zum Reiben
    teil.Shape = Part.makeBox(80, 60, 30, V(-40, -30, -30)).cut(loch).cut(durch).removeSplitter()
    doc.recompute()

    def zylinder(radius):
        return next(
            f"Face{i + 1}"
            for i, f in enumerate(teil.Shape.Faces)
            if f.Surface.__class__.__name__ == "Cylinder" and abs(f.Surface.Radius - radius) < 1e-6
        )

    wand = zylinder(3.375)
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, wand)
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.knopf_weiter.click()
    yield 1500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)

    def zeile(block):
        return getattr(block, "katalog_zeile", "")

    yield from h.warte_auf(lambda: zeile(panel.gewinde) and zeile(panel.bohren), 90000)
    gewinde, bohren = zeile(panel.gewinde), zeile(panel.bohren)
    print(ascii(f"Gewinde: {gewinde}"))
    print(ascii(f"Bohren: {bohren}"))
    h.pruefe(not panel.gewinde.moeglich and not panel.bohren.moeglich, "passt doch")
    h.pruefe("Im Katalog" in gewinde and "M8 × 1,25" in gewinde and "<a href" in gewinde, gewinde)
    h.pruefe("Im Katalog" in bohren and "6,75" in bohren, bohren)
    h.pruefe("Im Katalog" in panel.gewinde.kurz.text(), panel.gewinde.kurz.text())
    yield from h.warte_auf(lambda: zeile(panel.gewindefraesen), 30000)
    fraesen = zeile(panel.gewindefraesen)
    print(ascii(f"Gewinde fraesen: {fraesen}"))
    h.pruefe("Im Katalog" in fraesen and "M8" in fraesen, fraesen)
    panel.passt_nicht_knopf.click()  # die Blöcke, die nicht passen, aufklappen
    yield 500
    h.bild("1_katalog_bohrung", panel.form)
    # Die Bohrung Ø 8 (durch): „Reiben“ nennt Reibahlen Ø 8 aus dem Katalog.
    panel.flaechen_leeren()  # ein Klick auf eine Fläche nimmt sie sonst dazu
    yield 500
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, zylinder(4.0))
    yield 1500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    yield from h.warte_auf(lambda: zeile(panel.reiben), 60000)
    reiben = zeile(panel.reiben)
    print(ascii(f"Reiben: {reiben}"))
    h.pruefe("Im Katalog" in reiben and "Ø 8)" in reiben, reiben)
    panel.reject()
