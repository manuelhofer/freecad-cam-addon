# Nur ein Loch in einer Schräge fräsen (P-2026-10-10-40; Manuel, 2026-10-10: „Ich will nur dass
# Loch da fräsen“): ein Block 100 × 60 × 40 mit einer 30°-Schräge vorn oben und darin einer
# Bohrung Ø 16, 8 tief, senkrecht zur Schräge; als Maschine nur die 5-Achs-Beispielmaschine
# Tisch/Tisch. Der Boden der Bohrung angeklickt, „Bearbeitung“: Der Job ist neu, trotzdem steht
# unter der Liste „… 30° schräg“ mit dem Knopf „Ebene schwenken (3+2) …“. Der Knopf behält den
# Job ohne Operationen und öffnet „Ebene schwenken“ mit dem Boden; „OK“ legt die Ebene an, der
# Assistent darin räumt das Loch, „Anlegen“ legt nur das an.
import math
import os
import tempfile

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

    from camaddon import beispielmaschine, gui_bearbeitung, gui_schwenken
    from camaddon import maschinenspeicher as ms
    from camaddon import reichweite as rw
    from camaddon import schwenken as sw
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.TISCH_TISCH)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    pfad_maschine = os.path.join(ordner, "fuenfachs.FCStd")
    asm.Document.saveAs(pfad_maschine)
    yield 300
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 500

    # --- Das Teil: Schräge 30°, darin die Bohrung senkrecht zur Schräge --------------------------
    t = math.tan(math.radians(30.0))
    keil = Part.Face(
        Part.makePolygon(
            [V(-1, -1, 25 - t), V(-1, 27, 25 + 27 * t), V(-1, 27, 60), V(-1, -1, 60),
             V(-1, -1, 25 - t)]
        )
    ).extrude(V(102, 0, 0))  # fmt: skip
    normale = V(0, -0.5, math.sqrt(3.0) / 2.0)  # nach außen aus der Schräge
    mitte = V(50, 13, 25 + 13 * t)
    bohrung = Part.makeCylinder(8.0, 9.0, mitte + normale * 1.0, normale * -1.0)
    doc = FreeCAD.newDocument("LochSchraeg")
    doc.UndoMode = 1
    block = doc.addObject("Part::Feature", "Block")
    block.Shape = Part.makeBox(100, 60, 40).cut(keil).cut(bohrung).removeSplitter()
    doc.recompute()
    boden = next(
        f"Face{i + 1}"
        for i, f in enumerate(block.Shape.Faces)
        if f.Surface.TypeId == "Part::GeomPlane"
        and abs(f.Area - math.pi * 64.0) < 1.0
        and abs(f.normalAt(0, 0).dot(normale)) > 0.999
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, block.Name, boden)
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 15000)
    a = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(a is not None and a.job is not None, "kein Assistent oder kein Job")
    if a is None or a.job is None:
        return
    job = a.job
    h.pruefe(a._job_offen, "der Job ist nicht neu")
    h.pruefe(
        getattr(job, rw.EIGENSCHAFT_MASCHINE, "") == pfad_maschine,
        f"Maschine am Job: {getattr(job, rw.EIGENSCHAFT_MASCHINE, '')!r}",
    )
    if boden not in a.gewaehlte:
        a.flaeche_umschalten(boden)
    a.seite_zeigen(1)
    yield 800

    # --- Neuer Job, schräge Fläche: der Knopf ist da ------------------------------------------
    h.pruefe(
        not a.schwenken_zeile.isHidden() and not a.schwenken_knopf.isHidden(),
        "neuer Job: keine Zeile mit „Ebene schwenken (3+2) …“",
    )
    h.pruefe("30° schräg" in a.schwenken_text.text(), f"Zeile: {a.schwenken_text.text()!r}")
    h.pruefe("Anlegen" not in a.schwenken_text.text(), "Zeile verlangt noch „Anlegen“")
    Gui.SendMsgToActiveView("ViewFit")
    yield 300
    h.bild("1_assistent_neuer_job")

    a.schwenken_knopf.click()
    yield from h.warte_auf(lambda: gui_schwenken.SchwenkenPanel.offen is not None, 15000)
    panel = gui_schwenken.SchwenkenPanel.offen
    h.pruefe(panel is not None, "„Ebene schwenken“ öffnet nicht")
    if panel is None:
        return
    h.pruefe(doc.getObject(job.Name) is job, "der Job ist wieder weg")
    h.pruefe(not job.Operations.Group, f"Operationen im Job: {len(job.Operations.Group)}")
    h.pruefe(panel.grundjob is job and panel.flaeche == boden, f"Fenster: {panel.flaeche!r}")
    h.pruefe("30° geschwenkt" in panel.ergebnis.text(), f"Ergebnis: {panel.ergebnis.text()!r}")
    h.bild("2_ebene_schwenken")

    # --- OK: die Ebene, der Assistent darin räumt das Loch -----------------------------------------
    h.pruefe(panel.accept() is True, "„OK“ ging nicht")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 15000)
    ebenen = sw.ebenen_von(job)
    h.pruefe(len(ebenen) == 1, f"Ebenen: {[e.Label for e in ebenen]}")
    if not ebenen:
        return
    ebene = ebenen[0]
    b = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(b is not None and b.job is ebene, "Assistent nicht in der Ebene")
    if b is None:
        return
    h.pruefe(b.gewaehlte == [boden], f"gewählt: {b.gewaehlte}")
    # Erst wenn ein Block angehakt ist, hat der Assistent die Wahl ausgewertet – ohne das wäre
    # „alle Vorschauen da“ bei null Blöcken sofort wahr.
    yield from h.warte_auf(
        lambda: b.aktive_bloecke() and all(k.vorschau is not None for k in b.aktive_bloecke()),
        180000,
    )
    h.pruefe(b.aktive_bloecke(), "in der Ebene ist nichts angehakt")
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("3_assistent_in_der_ebene")
    hinweis = b.hinweis.text()  # nach „Anlegen“ ist das Fenster zu
    h.pruefe(b.accept() is True, f"„Anlegen“ ging nicht ({hinweis!r})")
    yield 2000
    h.pruefe(ebene.Operations.Group, "keine Operation in der Ebene")
    h.pruefe(not job.Operations.Group, "im Grundjob ist doch etwas angelegt")
    Gui.Selection.clearSelection()
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("4_angelegt")
