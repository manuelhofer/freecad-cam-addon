# Tauchfräsen mit Vorbohren (Plan C2; Manuel, 2026-10-31, zum Bild: „ja.. so ists ok“ – „Stelle 1
# in der Mitte (dort vorgebohrt)“). Der Block mit der Tasche aus szenario_beta_schritte, in der
# Werkzeugverwaltung der Fräser Ø 12 und ein Bohrer Ø 10. In der Beta die ganze Tasche, im Schritt
# „Schruppen“ Tauchfräsen angehakt: Das Räumen ist aus, der Satz sagt „Vorgebohrt: 1 Loch Ø 10“;
# „Anlegen“ legt das Vorbohren (FreeCADs Bohren, T3) vor dem Tauchfräsen (T1) an.
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

    from camaddon import gui_bearbeitung_beta as beta
    from camaddon import maschinenspeicher as ms
    from camaddon import werkzeuge as wz

    beta.beta_setzen(True)
    t3 = wz.Werkzeug(
        nummer=3,
        name="Bohrer 10",
        art=wz.BOHRER,
        durchmesser=10.0,
        schneiden=2,
        schneidenlaenge=60.0,
        gesamtlaenge=110.0,
        spitzenwinkel=118.0,
        schneidstoff=wz.HSS,
    )
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.1)]
    wz.Bibliothek([wz.standardwerkzeug(), t3]).speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()

    V = FreeCAD.Vector
    doc = FreeCAD.newDocument("Tasche")
    teil = doc.addObject("Part::Feature", "Block")
    block = Part.makeBox(100, 80, 40)
    form = block.cut(Part.makeBox(60, 40, 15, V(20, 20, 25)))
    unten = [
        e
        for e in form.Edges
        if abs(e.BoundBox.ZMax - 25) < 1e-6 and abs(e.BoundBox.ZMin - 25) < 1e-6
    ]
    teil.Shape = form.makeFillet(3, unten)
    doc.recompute()
    doc.saveAs(os.path.join(ordner, "tasche.FCStd"))
    wand = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if f.Surface.__class__.__name__ == "Plane"
        and abs(f.normalAt(0, 0).z) < 1e-6
        and f.BoundBox.ZMin > 24
        and abs(f.BoundBox.XMin - 80) < 1e-6
        and abs(f.BoundBox.XMax - 80) < 1e-6
    )
    Gui.activateWorkbench("CAMWorkbench")
    yield 500
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, wand)
    yield 500
    Gui.runCommand("CamAddon_BearbeitungBeta")
    yield from h.warte_auf(lambda: beta.BearbeitungPanel.offen is not None, 60000)
    yield 1500
    panel = beta.BearbeitungPanel.offen
    if not isinstance(panel, beta.BetaPanel) or panel.job is None:
        h.pruefe(False, f"kein Beta-Fenster mit Job: {panel!r}")
        return
    panel.wie_modelliert()
    yield 300
    panel.knopf_weiter.click()
    yield 1500
    panel.knopf_tasche_schruppen.click()
    yield 1500
    panel.knopf_weiter.click()  # in den Schritt „Schruppen“
    yield 1500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    tauchen = next(b for b in panel.bloecke if b.s.kennung == "tauchfraesen")
    raeumen = next(b for b in panel.bloecke if b.s.kennung == "raeumen")
    tauchen.haken.setChecked(True)
    yield 500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    yield 800
    satz = tauchen.ergebnis.text()
    print(ascii(f"Tauchfraesen: {satz}"))
    h.pruefe(not raeumen.haken.isChecked(), "Räumen bleibt neben dem Tauchfräsen angehakt")
    h.pruefe("Vorgebohrt: 1 Loch" in satz and "10" in satz, f"Tauchfräsen: {satz!r}")
    h.bild("1_tauchfraesen_vorbohren", panel.form)
    vorher = len(panel.job.Operations.Group)
    panel.accept()
    yield from h.warte_auf(
        lambda: beta.BearbeitungPanel.offen is not panel or panel.geschlossen, 120000
    )
    yield 1500
    neu = list(panel.job.Operations.Group)[vorher:]
    namen = [op.Label for op in neu]
    print(ascii(f"angelegt: {namen}"))
    bohren = next((i for i, n in enumerate(namen) if n.startswith("Vorbohren T3")), None)
    tauch = next((i for i, n in enumerate(namen) if n.startswith("Tauchfräsen T1")), None)
    h.pruefe(
        bohren is not None and tauch is not None and bohren < tauch,
        f"Vorbohren vor dem Tauchfräsen: {namen}",
    )
    if tauch is not None:
        op = neu[tauch]
        h.pruefe(op.Stellen > 0 and op.Path.Size > 0, f"Tauchfräsen ohne Bahn: {op.Stellen}")
