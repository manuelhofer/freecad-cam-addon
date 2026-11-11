# Neu installiert – keine Maschine, kein Werkzeug (Manuel, 2026-11-11: „ultra easy … ohne gross
# nachzudenken in freecad sein perfektes CAM“): ein Block mit Tasche und zwei Bohrungen Ø 8,
# „Bearbeitung“ ohne Auswahl, die Unterseite angeklickt, „Alles vorschlagen →“. Die Übersicht sagt,
# dass kein Fräser da ist, und bietet „Beispiel-Werkzeuge anlegen“: Danach steht der Vorschlag mit
# Zeiten, die Bohrungen bekommen von selbst den Ø 6 (nicht rot „kleiner als der Fräser“), und
# „Anlegen“ geht.
import FreeCAD
import FreeCADGui as Gui
import Part

NEUES_FENSTER = True


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500
    from camaddon import gui_bearbeitung
    from camaddon import gui_bearbeitung_beta as beta

    V = FreeCAD.Vector
    doc = FreeCAD.newDocument("Teil")
    teil = doc.addObject("Part::Feature", "Block")
    form = Part.makeBox(100, 80, 30).cut(Part.makeBox(60, 40, 12, V(20, 20, 18)))
    for x in (10, 90):
        form = form.cut(Part.makeCylinder(4, 30, V(x, 40, 0)))
    teil.Shape = form
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(isinstance(panel, beta.BetaPanel) and panel.job is None, "kein Fenster in Schritten")
    if panel is None:
        return
    unten = next(
        f"Face{i + 1}" for i, f in enumerate(teil.Shape.Faces) if abs(f.BoundBox.ZMax) < 1e-6
    )
    Gui.Selection.addSelection(doc.Name, teil.Name, unten)
    yield 2500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel.job is not None and panel._beta_unten_klar, "der Klick auf die Unterseite")
    if panel.job is None:
        return
    h.pruefe(panel.knopf_alles.isVisible(), "kein „Alles vorschlagen“")
    panel.knopf_alles.click()
    yield 2000
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    yield 3000
    h.pruefe(panel.seite() == beta.UEBERSICHT, f"Seite {panel.seite()}")
    h.pruefe(panel.beispiel_box.isVisible(), "kein Angebot „Beispiel-Werkzeuge anlegen“")
    h.pruefe(not panel.knopf_fertig.isEnabled(), "„Anlegen“ geht ohne Werkzeug")
    h.pruefe(
        panel.uebersicht_text.text().count("keinen Fräser") == 0,
        "derselbe Satz „kein Fräser“ steht in der Übersicht",
    )
    h.bild("1_ohne_werkzeug", panel.form)
    panel.knopf_beispielwerkzeuge.click()
    yield 2000
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    yield 4000
    text = panel.uebersicht_text.text()
    h.pruefe(not panel.beispiel_box.isVisible(), "das Angebot bleibt nach dem Anlegen stehen")
    h.pruefe(panel.knopf_fertig.isEnabled(), f"„Anlegen“ geht nicht: {text[-300:]!r}")
    for wort in ("Räumen", "Bohrung fräsen", "T3", "Zusammen etwa"):
        h.pruefe(wort in text, f"„{wort}“ fehlt: {text[:400]!r}")
    h.pruefe(float(panel.bohrung.fraeser().durchmesser) == 6.0, "Bohrung fräsen nicht mit dem Ø 6")
    h.pruefe("Nicht dabei" not in text, f"etwas ist nicht dabei: {text[-300:]!r}")
    h.bild("2_mit_beispielwerkzeugen", panel.form)
    panel.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
