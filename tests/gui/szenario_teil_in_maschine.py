# B-020 (Manuel, 2026-10-12: „Konnte nicht anlegen: PropertyLink does not support external object“ –
# eine neue 3-Achs-Fräse als eigenes Dokument offen, im Baum ein halber Job „Body – Fräsen“ und ein
# loses „TC: 5mm Endmill“): Ein Block in „Teil“, die Beispiel-Fräse in einem eigenen Dokument, darin
# ein Link auf den Block (wie in eine Baugruppe eingelegt). Eine Fläche am Link angeklickt,
# „Bearbeitung“: Der Assistent arbeitet im Dokument „Teil“ – der Job dort mit dem Block selbst, kein
# roter Satz, in der Maschine kommt nichts dazu. Dann ohne Auswahl, die Maschine aktiv und ein
# drittes Dokument offen (der Assistent beginnt in der Maschine): eine Fläche am Block in „Teil“
# angeklickt – der Job entsteht in „Teil“. „4-Achs-Bearbeitung“ mit der Fläche am Link ebenso im
# Dokument „Teil“.
import os

import FreeCAD
import FreeCADGui as Gui
import Part

AUSGABE = os.environ["CAMADDON_AUSGABE"]


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine as bm
    from camaddon import gui_bearbeitung
    from camaddon import hoehenfeld as hf
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    doc = FreeCAD.newDocument("Teil")
    teil = doc.addObject("Part::Feature", "Body")
    teil.Shape = Part.makeBox(60, 40, 20)
    doc.recompute()
    doc.saveAs(os.path.join(AUSGABE, "Teil.FCStd"))  # ein Link in ein anderes braucht die Datei
    oben = next(e.name for e in hf.ebenen_oben(teil.Shape) if abs(e.z - 20.0) < 1e-6)
    Gui.activateWorkbench("CAMWorkbench")
    asm, _maschine = bm.lade(bm.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document, 10000)
    mdoc = asm.Document
    mdoc.saveAs(os.path.join(AUSGABE, "Maschine.FCStd"))
    link = mdoc.addObject("App::Link", "Body")
    link.LinkedObject = teil
    mdoc.recompute()
    vorher = {o.Name for o in mdoc.Objects}
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(mdoc.Name, link.Name, oben)
    yield 300

    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 10000)
    yield 1500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None, "„Bearbeitung“ öffnet nicht")
    if panel is None:
        return
    h.pruefe(panel.doc is doc, f"Bearbeitung im Dokument {panel.doc.Name}")
    h.pruefe(
        panel.job is not None and panel.job.Document is doc,
        f"Job: {panel.job and panel.job.Document}",
    )
    h.pruefe(panel.teil is teil, f"Teil: {panel.teil and panel.teil.FullName}")
    h.pruefe("Konnte nicht" not in panel.hinweis.text(), f"rot: {panel.hinweis.text()!r}")
    dazu = sorted({o.Name for o in mdoc.Objects} - vorher)
    h.pruefe(not dazu, f"in der Maschine dazugekommen: {dazu}")
    h.bild("1_link_in_der_maschine")
    panel.reject()
    yield 800

    # Ebenso „4-Achs-Bearbeitung“ mit der Fläche am Link: im Dokument „Teil“.
    from camaddon import gui_vierachs

    FreeCAD.setActiveDocument(mdoc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(mdoc.Name, link.Name, oben)
    yield 300
    Gui.runCommand("CamAddon_Vierachs")
    yield from h.warte_auf(lambda: gui_vierachs.VierachsPanel.offen is not None, 10000)
    yield 1000
    vierachs = gui_vierachs.VierachsPanel.offen
    h.pruefe(vierachs is not None, "„4-Achs-Bearbeitung“ öffnet nicht")
    if vierachs is not None:
        h.pruefe(vierachs.doc is doc, f"4 Achsen im Dokument {vierachs.doc.Name}")
        dazu = sorted({o.Name for o in mdoc.Objects} - vorher)
        h.pruefe(not dazu, f"4 Achsen: in der Maschine dazugekommen: {dazu}")
        vierachs.reject()
        yield 800

    # Ohne Auswahl, die Maschine aktiv, ein drittes Dokument offen: Der Assistent beginnt in der
    # Maschine; die Fläche am Block in „Teil“ angeklickt – der Job entsteht in „Teil“.
    FreeCAD.newDocument("Anderes")
    FreeCAD.setActiveDocument(mdoc.Name)
    Gui.Selection.clearSelection()
    yield 300
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(
        lambda: gui_bearbeitung.BearbeitungPanel.offen is not None or h.modal() is not None, 10000
    )
    dialog = h.modal()
    if dialog is not None:
        dialog.reject()
        yield 300
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None, "„Bearbeitung“ ohne Auswahl öffnet nicht")
    if panel is None:
        return
    jobs_vorher = len([o for o in doc.Objects if hasattr(o, "Operations")])
    Gui.Selection.addSelection(doc.Name, teil.Name, oben)
    # Das Fenster schließt und öffnet sich im Dokument „Teil“ neu (ein Aufgabenfenster gehört zu
    # seinem Dokument).
    yield from h.warte_auf(
        lambda: getattr(gui_bearbeitung.BearbeitungPanel.offen, "job", None) is not None, 10000
    )
    yield 1000
    panel = gui_bearbeitung.BearbeitungPanel.offen or panel
    h.pruefe(
        panel.job is not None and panel.job.Document is doc,
        f"Job nach dem Klick: {panel.job and panel.job.Document.Name}",
    )
    h.pruefe(panel.doc is doc, f"danach im Dokument {panel.doc.Name}")
    h.pruefe(
        len([o for o in doc.Objects if hasattr(o, "Operations")]) == jobs_vorher + 1,
        "kein neuer Job in „Teil“",
    )
    dazu = sorted({o.Name for o in mdoc.Objects} - vorher)
    h.pruefe(not dazu, f"in der Maschine dazugekommen: {dazu}")
    h.bild("2_klick_im_anderen_dokument")
    panel.reject()
    yield 800
