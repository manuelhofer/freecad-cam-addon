# Die Nummern im Job aus dem Magazin der Maschine (W-002 Stufe H2; Manuel, 2026-10-05: „E3 a ja,
# E7 a ja“): die 3-Achs-Fräse gespeichert, zwei Fräser – VHM 12 als T3, VHM 10 als T2. Im
# Magazin der Fräse steht nur der VHM 10, als T5 beladen auf P3. Ein Block, die Oberseite,
# „Bearbeitung“ mit der Fräse: In „Planfräsen“ steht oben „T5 · P3  VHM 10 …“, darunter
# „–  VHM 12 … – nicht im Magazin“; gewählt der VHM 10, kein gelber Satz. Den VHM 12 gewählt:
# gelb „… steht nicht im Magazin „3-Achs-Fräse“ …“ und der Knopf „Ins Magazin übernehmen“.
# Geklickt: Er steht im Magazin als T1 (die kleinste freie), der Satz ist weg, gespeichert.
# „Anlegen“: Der Controller des VHM 12 hat T1 – die Nummer des Magazins, nicht die T3 der
# Werkzeugverwaltung.
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
    from camaddon import hoehenfeld as hf
    from camaddon import job_schnittwerte as js
    from camaddon import maschinenspeicher as msp
    from camaddon import werkzeuge as wz

    msp.speichern([])
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    pfad_fraese = os.path.join(ordner, "Fraese.FCStd")
    asm.Document.saveAs(pfad_fraese)
    msp.merken_datei(pfad_fraese)
    yield 300
    FreeCAD.closeDocument(asm.Document.Name)
    yield 300
    vhm12 = wz.standardwerkzeug(3)
    vhm10 = wz.standardwerkzeug(2)
    vhm10.name, vhm10.durchmesser = "VHM 10", 10.0
    bibliothek = wz.Bibliothek([vhm12, vhm10])
    magazin = bibliothek.neues_magazin("3-Achs-Fräse", pfad_fraese)
    magazin.hinzufuegen(vhm10, 5).platz = 3
    bibliothek.speichern()

    doc = FreeCAD.newDocument("Teil")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeBox(100, 60, 20)
    doc.recompute()
    oben = next(e.name for e in hf.ebenen_oben(teil.Shape) if abs(e.z - 20.0) < 1e-6)
    Gui.activateWorkbench("CAMWorkbench")
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
    panel.wahl_maschine.setCurrentIndex(panel.wahl_maschine.findData(pfad_fraese))
    yield 500
    h.pruefe(panel.magazin() is not None, "kein Magazin zur Fräse")
    panel.knopf_weiter.click()
    yield 300
    panel.knopf_weiter.click()
    yield 500
    plan = panel.plan
    zeilen = [plan.wahl_fraeser.itemText(i) for i in range(plan.wahl_fraeser.count())]
    h.pruefe(
        len(zeilen) == 2
        and zeilen[0].startswith("T5 · P3  VHM 10")
        and zeilen[1].startswith("–  VHM 12")
        and zeilen[1].endswith("nicht im Magazin"),
        f"Liste: {zeilen}",
    )
    h.pruefe(plan.fraeser() is not None and plan.fraeser().kennung == vhm10.kennung, "VHM 10?")
    h.pruefe(plan.magazin_zeile.isHidden(), f"gelb zu viel: {plan.magazin_satz.text()!r}")

    # Der VHM 12 – nicht im Magazin: gelb, mit dem Knopf.
    plan.wahl_fraeser.setCurrentIndex(1)
    yield 500
    satz = plan.magazin_satz.text()
    h.pruefe(
        not plan.magazin_zeile.isHidden() and "nicht im Magazin „3-Achs-Fräse“" in satz,
        f"gelber Satz: {satz!r}",
    )
    h.bild("1_nicht_im_magazin", panel.form)
    plan.knopf_magazin.click()
    yield 800
    gelesen = wz.Bibliothek.laden().magazin_fuer(pfad_fraese)
    eintrag = gelesen.eintrag_von(vhm12) if gelesen is not None else None
    h.pruefe(eintrag is not None and eintrag.nummer == 1, f"übernommen: {eintrag}")
    h.pruefe(
        plan.fraeser() is not None and plan.fraeser().kennung == vhm12.kennung,
        "nach dem Übernehmen ein anderer Fräser",
    )
    h.pruefe(
        plan.magazin_zeile.isHidden(), f"gelb nach dem Übernehmen: {plan.magazin_satz.text()!r}"
    )
    zeile = plan.wahl_fraeser.currentText()
    h.pruefe(zeile.startswith("T1  VHM 12"), f"Zeile nach dem Übernehmen: {zeile!r}")
    h.bild("2_uebernommen", panel.form)

    # Anlegen: Der Controller ruft den VHM 12 als T1 auf – die Nummer aus dem Magazin.
    job = panel.job
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    nummern = {
        js.werkzeug_von(tc, wz.Bibliothek.laden()).kennung: tc.ToolNumber
        for tc in job.Tools.Group
        if js.werkzeug_von(tc, wz.Bibliothek.laden()) is not None
    }
    h.pruefe(nummern.get(vhm12.kennung) == 1, f"Nummern im Job: {nummern}")
    FreeCAD.closeDocument(doc.Name)
    yield 300
