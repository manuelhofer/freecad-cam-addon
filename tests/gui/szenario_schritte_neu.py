# Neu installiert – keine Maschine, kein Werkzeug (Manuel, 2026-11-11: „ultra easy … ohne gross
# nachzudenken in freecad sein perfektes CAM“): ein Block mit Tasche und zwei Bohrungen Ø 8,
# „Bearbeitung“ ohne Auswahl und ohne Klick ins Teil, „Alles vorschlagen →“. Die Übersicht sagt,
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
    # Ein Teil im Dokument: kein Klick ins Teil nötig – „Alles vorschlagen“ nimmt es, wie es
    # modelliert ist, und legt den Job an.
    h.pruefe(panel.knopf_alles.isVisible(), "kein „Alles vorschlagen“ ohne Auswahl")
    h.pruefe(
        "Alles vorschlagen" in panel.anleitung.text(), f"Anleitung: {panel.anleitung.text()!r}"
    )
    h.bild("0_ohne_auswahl", panel.form)
    panel.knopf_alles.click()
    yield 2500
    h.pruefe(panel.job is not None and panel._beta_unten_klar, "kein Job nach „Alles vorschlagen“")
    if panel.job is None:
        return
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
    for wort in ("Räumen", "Bohrung fräsen", "T3", "Zusammen"):
        h.pruefe(wort in text, f"„{wort}“ fehlt: {text[:400]!r}")
    h.pruefe(float(panel.bohrung.fraeser().durchmesser) == 6.0, "Bohrung fräsen nicht mit dem Ø 6")
    h.pruefe("Nicht dabei" not in text, f"etwas ist nicht dabei: {text[-300:]!r}")
    h.bild("2_mit_beispielwerkzeugen", panel.form)
    # „▶ Abspielen“: ein Werkzeug fährt die Wege im Teil ab; noch ein Klick hält es an.
    h.pruefe(panel.knopf_abspielen.isVisible(), "kein „Abspielen“ in der Übersicht")
    panel.knopf_abspielen.click()
    yield 5500  # mitten im Räumen: das Werkzeug steht über der Tasche
    spieler = panel._beta_spieler
    h.pruefe(spieler is not None and spieler.laeuft(), "„Abspielen“ läuft nicht")
    h.pruefe(panel.knopf_abspielen.text() == "■ Anhalten", panel.knopf_abspielen.text())
    h.bild("2b_abspielen", None)
    panel.knopf_abspielen.click()
    yield 200
    h.pruefe(
        not spieler.laeuft()
        and spieler.wurzel is None
        and panel.knopf_abspielen.text() == "▶ Abspielen",
        f"„Anhalten“ hält nicht an: {panel.knopf_abspielen.text()!r}",
    )
    # „Anlegen“ – und das Fenster „Angelegt“ sagt rot, dass der Ø 6 für die 30 mm tiefe Bohrung zu
    # kurz heraussteht (das stand sonst erst im Kopf des Programms).
    job = panel.job
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    yield from h.warte_auf(lambda: beta.FertigFenster.offen is not None, 30000)
    fertig = beta.FertigFenster.offen
    h.pruefe(fertig is not None, "kein Fenster „Angelegt“")
    if fertig is not None:
        namen = [o.Label for o in job.Operations.Group]
        h.pruefe("Bohrung fräsen T3" in namen, f"Operationen: {namen}")
        text = fertig.warnung.text()
        h.pruefe(
            fertig.knapp_box.isVisible() and "T3" in text and "heraus" in text,
            f"keine Warnung zur Auskragung: {text!r}",
        )
        yield from h.warte_auf(lambda: fertig.fertig, 120000)
        h.bild("3_angelegt_mit_warnung", fertig)
        # Der nächste Schritt ist ein Knopf: „T3 auf … mm ausspannen“ behebt es.
        knoepfe = [k.text() for k in fertig.knapp_knoepfe]
        h.pruefe(any(k.startswith("T3 auf ") for k in knoepfe), f"Knöpfe: {knoepfe}")
        for _ in range(4):  # je Werkzeug einer – nach jedem Klick baut das Fenster sie neu
            if not fertig.knapp_knoepfe:
                break
            fertig.knapp_knoepfe[0].click()
            yield 300
        h.pruefe(
            not fertig.knapp_box.isVisible() and not fertig.warnung.text(),
            f"Warnung bleibt nach dem Ausspannen: {fertig.warnung.text()!r}",
        )
        h.bild("4_angelegt_ausgespannt", fertig)
        h.pruefe(
            not fertig.knopf_weiter.isVisible(),
            "„Weiter bearbeiten“ steht da, obwohl alles Vorgeschlagene angelegt ist",
        )
        # Eine Zeile anklicken wählt die Operation (FreeCAD hebt dann ihre Bahn hervor).
        op, zeile = fertig._zeilen[1]
        fertig.liste.itemClicked.emit(zeile, 0)
        yield 200
        gewaehlt = [o.Name for o in Gui.Selection.getSelection()]
        h.pruefe(gewaehlt == [op.Name], f"Auswahl nach dem Klick auf die Zeile: {gewaehlt}")
        fertig.close()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
