# „Ringnut fräsen“ (ringnut, ringnut_bahn) am Beispielteil beispiele/ringnut_lagersitz.FCStd: Platte
# 90 × 90 × 30 mit dem Lagersitz Ø 62 und der Sicherungsringnut Ø 65 × 2,15, dazu eine Bohrung Ø 20
# mit O-Ring-Nut Ø 24 × 3. In der Werkzeugverwaltung zuerst nur T1 (der Standardfräser): „Alles
# vorschlagen“ – die Nutflächen sind gewählt (nicht „nicht erreichbar“), „Nicht fertig“ nennt die
# Nuten mit dem Satz, womit es ginge, und dem Knopf „Scheibenfräser Ø 19 × 2,15 anlegen“. Ein Klick:
# „Ringnut fräsen“ ist angehakt, je Nut eine Zeile „Face15: Ø 65 × 2,15, 1,5 tief – 2 Kreise, …“,
# die Bahn ist als Vorschau im Teil zu sehen. „Anlegen“: „Ringnut fräsen T2“ nach „Bohrung fräsen“,
# nur G3. Bilder: 1_vorschlag (mit dem Knopf), 2_ringnut (der Block), 3_vorschau (die Bahn im Teil),
# 4_angelegt.
# ZEITLIMIT: 600
import os

import FreeCAD
import FreeCADGui as Gui

NEUES_FENSTER = True  # „Bearbeitung“ in Schritten


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import camaddon
    from camaddon import bohrung as bo
    from camaddon import gui_bearbeitung
    from camaddon import gui_bearbeitung_beta as beta
    from camaddon import ringnut as rnop
    from camaddon import ringnut_bahn as rnb
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    datei = os.path.join(camaddon.ADDON_ORDNER, "beispiele", "ringnut_lagersitz.FCStd")
    doc = FreeCAD.openDocument(datei)
    doc.UndoMode = 1
    yield 1500
    teil = doc.getObject("Lagerschild")
    nuten = rnb.ringnuten(teil.Shape)
    h.pruefe(len(nuten) == 2, f"Ringnuten im Beispielteil: {[n.name for n in nuten]}")
    flaechen = {f for n in nuten for f in n.flaechen}
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.addSelection(doc.Name, teil.Name, "Face3")  # die Oberseite
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 60000)
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(isinstance(panel, beta.BetaPanel), f"nicht in Schritten: {type(panel).__name__}")
    if panel is None or panel.job is None:
        return
    job = panel.job
    panel.knopf_alles.click()
    yield 1500
    h.pruefe(flaechen <= set(panel.gewaehlte), f"Nutflächen nicht gewählt: {panel.gewaehlte}")

    def fertig_gerechnet():
        return not panel.vorschau_laeuft() and all(
            b.vorschau is not None or not b.aktiv() for b in panel.bloecke
        )

    yield from h.warte_auf(fertig_gerechnet, 300000)
    yield 2000
    # Ohne Nutenfräser: „Nicht fertig“ mit dem Satz und dem Knopf.
    satz = panel.unfertig_satz.text()
    knopf = panel.unfertig_knopf.text()
    h.pruefe("Scheibenfräser" in satz and "höchstens" in satz, f"Satz: {satz!r}")
    h.pruefe(knopf.startswith("Scheibenfräser Ø 19") and knopf.endswith("anlegen"), f"{knopf!r}")
    h.pruefe(not panel.ringnut.aktiv(), "Ringnut fräsen ohne Nutenfräser angehakt")
    h.bild("1_vorschlag", panel.form)

    # Der Knopf legt den Scheibenfräser an – dann fräst „Ringnut fräsen“ beide Nuten.
    panel.unfertig_knopf.click()
    yield 1500
    yield from h.warte_auf(fertig_gerechnet, 300000)
    yield 2000
    block = panel.ringnut
    h.pruefe(block.aktiv(), "Ringnut fräsen nicht angehakt")
    h.pruefe(
        block.fraeser() is not None and block.fraeser().art == wz.NUTENFRAESER,
        f"Fräser: {block.fraeser()}",
    )
    text = block.ergebnis.text()
    h.pruefe(
        all(n.name in text for n in nuten) and "Ø 65 × 2,15, 1,5 tief" in text,
        f"Ergebnis: {text!r}",
    )
    h.pruefe(not block.hinweis.text(), f"rot: {block.hinweis.text()!r}")
    h.pruefe(panel.unfertig.isHidden(), f"noch „Nicht fertig“: {panel.unfertig.text()!r}")
    panel.seite_zeigen(beta.abschnitt(block) + beta.ERSTER_ABSCHNITT)
    yield 800
    h.bild("2_ringnut", panel.form)
    panel._block_zeigen(block)
    yield 1500
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("3_vorschau")

    # „Anlegen“ gibt es nur in der Übersicht.
    panel.seite_zeigen(beta.UEBERSICHT)
    yield 1500
    h.pruefe("Ringnut" in panel.uebersicht_text.text(), "Ringnut fehlt in der Übersicht")
    h.bild("3b_uebersicht", panel.form)
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    yield from h.warte_auf(lambda: not doc.isTouched(), 300000)
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    print("RINGNUT", namen, flush=True)
    ringnut = [o for o in ops if rnop.ist_ringnut(o)]
    h.pruefe(len(ringnut) == 1, f"Operationen: {namen}")
    if ringnut:
        op = ringnut[0]
        h.pruefe(op.Nuten == 2, f"{op.Nuten} Nuten")
        befehle = {b.Name for b in op.Path.Commands}
        h.pruefe("G3" in befehle and "G2" not in befehle, f"Gleichlauf: {sorted(befehle)}")
        bohrung = [i for i, o in enumerate(ops) if bo.ist_bohrungsfraesen(o)]
        h.pruefe(
            not bohrung or ops.index(op) > max(bohrung), f"Ringnut vor Bohrung fräsen: {namen}"
        )
    fertig = beta.FertigFenster.offen
    if fertig is not None:
        yield from h.warte_auf(lambda: fertig.fertig, 120000)
        fertig.close()
    Gui.Selection.clearSelection()
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("4_angelegt")
    FreeCAD.closeDocument(doc.Name)
    yield 300
