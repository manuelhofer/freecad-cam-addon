# Frage 7 (Manuel, 2026-10-17: „Automatisch Ebene A−90“, „aber im progromm muss das natürlich dann
# auch ausgegeben werden“): An der GROB G550 steht die Spindel waagerecht – ein Job „von oben“
# fräst dort nur in einer geschwenkten Ebene. Ein Block 80 × 60 × 30 mit einer Tasche oben, ihr
# Boden angeklickt, Maschine G550, „Bearbeitung“, Schritt 2: Die Zeile sagt „kommt in der Ebene
# „von oben“ dran“, darunter der Satz zur waagerechten Spindel, keine Blöcke angehakt. „Anlegen“:
# Die Ebene („… (A90 B0)“ oder „(A−90 B0)“, wie die Steuerung) entsteht, der Assistent dort räumt
# die Tasche; „Anlegen“. „Auf der Maschine prüfen“: Achsen in ihren Grenzen, kein „passt sie nicht
# zum Teil“; „Programm schreiben …“: ohne Hinweis, der Tisch schwenkt vor der Tasche und am Ende
# zurück (programm.txt im Ausgabeordner).
# ZEITLIMIT: 600
import os
import tempfile

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

    from camaddon import beispielmaschine, gui_bearbeitung
    from camaddon import maschinenspeicher as ms
    from camaddon import schwenken as sw
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.GROB_G550)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    asm.Document.saveAs(os.path.join(ordner, "G550.FCStd"))
    yield 300
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 500
    # Eine Liste von vorher: der Eintrag ohne „Spindel quer“ – der Assistent rechnet es nach.
    eintraege = ms.laden()
    h.pruefe(len(eintraege) == 1, f"Maschinenliste: {eintraege}")
    for e in eintraege:
        e.spindel_quer = None
    ms.speichern(eintraege)

    V = FreeCAD.Vector
    doc = FreeCAD.newDocument("Oben")
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeBox(80, 60, 30).cut(Part.makeBox(40, 24, 8, V(20, 18, 22)))
    doc.recompute()
    boden = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if abs(f.BoundBox.ZMin - 22) < 1e-6 and abs(f.BoundBox.ZMax - 22) < 1e-6
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, boden)
    yield 300
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(
        lambda: getattr(gui_bearbeitung.BearbeitungPanel.offen, "job", None) is not None, 20000
    )
    yield 1000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel._fuenfachs(), f"keine 5-Achs-Fräse: {panel.wahl_maschine.currentText()}")
    h.pruefe(panel._spindel_quer(), "Spindel der G550 nicht waagerecht erkannt")
    h.pruefe(ms.laden()[0].spindel_quer is True, f"Eintrag nicht nachgerechnet: {ms.laden()[0]}")
    h.pruefe(FreeCAD.ActiveDocument is doc, f"aktiv: {FreeCAD.ActiveDocument.Name}")
    panel.knopf_weiter.click()
    yield 800

    def zeilen(p):
        return [p.flaechen_liste.item(i).text() for i in range(p.flaechen_liste.count())]

    h.pruefe(panel.gewaehlte == [boden], f"gewählt: {panel.gewaehlte} statt {boden}")
    liste = zeilen(panel)
    h.pruefe(
        len(liste) == 1 and "kommt in der Ebene „von oben“ dran" in liste[0],
        f"Liste: {liste}",
    )
    h.pruefe(
        panel.schwenken_zeile.isVisible() and "waagerecht" in panel.schwenken_text.text(),
        f"Zeile: {panel.schwenken_text.text()!r}",
    )
    h.pruefe(
        not panel.aktive_bloecke(), f"angehakt: {[b.s.kennung for b in panel.aktive_bloecke()]}"
    )
    h.pruefe(panel._kann_anlegen(), "„Anlegen“ geht nicht")
    h.bild("1_schritt2", panel.form)
    grundjob = panel.job
    panel.accept()
    yield from h.warte_auf(
        lambda: gui_bearbeitung.BearbeitungPanel.offen not in (None, panel)
        and gui_bearbeitung.BearbeitungPanel.offen.job is not None,
        30000,
    )
    yield 1500
    ebene_panel = gui_bearbeitung.BearbeitungPanel.offen
    meldung = h.modal()
    h.pruefe(
        ebene_panel is not None and ebene_panel is not panel,
        f"kein Assistent in der Ebene – {getattr(meldung, 'text', lambda: '')()!r}",
    )
    if ebene_panel is None or ebene_panel is panel:
        return
    ebene = ebene_panel.job
    h.pruefe(sw.ist_ebene(ebene) and ebene.Grundjob == grundjob, f"keine Ebene: {ebene.Label}")
    h.pruefe(
        ebene.Label.endswith(("Ebene von oben (A90 B0)", "Ebene von oben (A−90 B0)")),
        f"Name der Ebene: {ebene.Label!r}",
    )
    h.pruefe(not ebene_panel._spindel_quer(), "in der Ebene noch einmal geschwenkt")
    h.pruefe(ebene_panel.gewaehlte == [boden], f"in der Ebene gewählt: {ebene_panel.gewaehlte}")
    h.pruefe(ebene_panel.raeumen.aktiv(), "Räumen in der Ebene nicht angehakt")
    h.pruefe("von oben" in ebene_panel.dazu_text.text(), f"Satz: {ebene_panel.dazu_text.text()!r}")
    h.bild("2_ebene", ebene_panel.form)
    ebene_panel.accept()
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not ebene_panel, 60000)
    yield 1500
    h.pruefe(bool(list(ebene.Operations.Group)), "in der Ebene nichts angelegt")
    h.pruefe(not list(grundjob.Operations.Group), "im Grundjob angelegt")

    from PySide import QtCore, QtGui

    from camaddon import gui_reichweite

    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(grundjob)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 60000)
    pruefung = gui_reichweite.PruefPanel.offen
    h.pruefe(pruefung is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruefung is None:
        return
    yield 2000
    h.pruefe(
        pruefung.urteil.text().startswith("Alle Achsen bleiben"),
        f"Achsen: {pruefung.urteil.text()!r}",
    )
    hinweise = pruefung.form.findChildren(QtGui.QLabel)
    h.pruefe(
        not any("passt sie nicht zum Teil" in w.text() for w in hinweise),
        "Hinweis „passt sie nicht zum Teil“",
    )
    h.bild("3_pruefen", pruefung.form)
    dialog = pruefung.programm_schreiben()
    yield 2000
    programm = dialog._programm()
    with open(os.path.join(os.environ["CAMADDON_AUSGABE"], "programm.txt"), "w") as d:
        d.write(f"Steuerung: {dialog.steuerung().name}\nHinweise: {programm.hinweise}\n\n")
        d.write(programm.text)
    h.pruefe(not programm.hinweise, f"Hinweise zum Programm: {programm.hinweise}")
    stellung = [z for z in programm.text.splitlines() if z.startswith("G0 A") or "CYCLE800(" in z]
    h.pruefe(
        len(stellung) >= 2
        and "90" in stellung[0]
        and stellung[-1].replace(" ", "").startswith(("G0A0.000", "CYCLE800()")),
        f"Schwenken im Programm: {stellung}",
    )
    h.bild("4_programm", dialog)
    dialog.close()
    pruefung.reject()
    yield 500

    # --- Nichts angeklickt: die Oberseite kommt auch in die Ebene „von oben“ --------------------
    # Ohne Wahl nimmt der Assistent die Oberseite (Planfräsen); an der G550 geht auch sie in die
    # Ebene: der Satz zur waagerechten Spindel, keine Blöcke angehakt, „Anlegen“ – in der Ebene ist
    # die Oberseite gewählt und angehakt, im Grundjob nichts.
    platte_doc = FreeCAD.newDocument("Platte")
    platte = platte_doc.addObject("Part::Feature", "Platte")
    platte.Shape = Part.makeBox(70, 50, 20)
    platte_doc.recompute()
    oben = [
        f"Face{i + 1}"
        for i, f in enumerate(platte.Shape.Faces)
        if abs(f.BoundBox.ZMin - 20) < 1e-6 and abs(f.BoundBox.ZMax - 20) < 1e-6
    ]
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(platte_doc.Name, platte.Name)
    yield 300
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(
        lambda: getattr(gui_bearbeitung.BearbeitungPanel.offen, "job", None) is not None
        and gui_bearbeitung.BearbeitungPanel.offen.doc is platte_doc,
        20000,
    )
    yield 1000
    ohne = gui_bearbeitung.BearbeitungPanel.offen
    ohne.knopf_weiter.click()
    yield 800
    h.pruefe(not ohne.gewaehlte, f"ohne Wahl gewählt: {ohne.gewaehlte}")
    h.pruefe(
        ohne.schwenken_zeile.isVisible() and "waagerecht" in ohne.schwenken_text.text(),
        f"ohne Wahl, Zeile: {ohne.schwenken_text.text()!r}",
    )
    h.pruefe(
        not ohne.aktive_bloecke(),
        f"ohne Wahl angehakt: {[b.s.kennung for b in ohne.aktive_bloecke()]}",
    )
    h.pruefe(ohne._kann_anlegen(), "ohne Wahl: „Anlegen“ geht nicht")
    h.bild("5_ohne_wahl", ohne.form)
    platte_grund = ohne.job
    ohne.accept()
    yield from h.warte_auf(
        lambda: gui_bearbeitung.BearbeitungPanel.offen not in (None, ohne)
        and gui_bearbeitung.BearbeitungPanel.offen.job is not None,
        30000,
    )
    yield 1500
    oben_panel = gui_bearbeitung.BearbeitungPanel.offen
    if oben_panel is None or oben_panel is ohne:
        h.pruefe(False, "ohne Wahl: kein Assistent in der Ebene")
        return
    h.pruefe(
        sw.ist_ebene(oben_panel.job) and oben_panel.job.Label.endswith(("(A90 B0)", "(A−90 B0)")),
        f"ohne Wahl, Ebene: {oben_panel.job.Label!r}",
    )
    h.pruefe(sorted(oben_panel.gewaehlte) == sorted(oben), f"in der Ebene: {oben_panel.gewaehlte}")
    h.pruefe(bool(oben_panel.aktive_bloecke()), "in der Ebene nichts angehakt")
    oben_panel.accept()
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not oben_panel, 60000)
    yield 1500
    h.pruefe(bool(list(oben_panel.job.Operations.Group)), "ohne Wahl: in der Ebene nichts angelegt")
    h.pruefe(not list(platte_grund.Operations.Group), "ohne Wahl: im Grundjob angelegt")
