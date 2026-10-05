# Wege zwischen den Fenstern (Manuel, 2026-10-05: „irgendwas zum Erleichtern der Bedienung“): ein
# Klotz, zwei Jobs („Seite 1“, „Seite 2“ – zwei Aufspannungen) mit „Planfräsen“ auf der
# gespeicherten 3-Achs-Fräse. Zuletzt gearbeitet an „Seite 2“, eine Fläche des Klotzes angeklickt
# (sie steckt in beiden): „Programm schreiben“ zeigt „Seite 2“, nicht den ersten Job. Gespeichert
# in einen anderen Ordner: „Ordner öffnen“ ist da; beim nächsten Mal steht dieselbe Datei im
# Feld, für „Seite 1“ derselbe Ordner (die Maschine). „Auf der Maschine prüfen“ ohne Auswahl:
# der Job, an dem zuletzt gearbeitet wurde; sein Knopf „Programm schreiben …“ öffnet das
# Programm desselben Jobs.
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtCore


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import Path.Main.Job as PathJob

    from camaddon import beispielmaschine, gui_programm, gui_reichweite
    from camaddon import job_schnittwerte as js
    from camaddon import planfraesen as pf
    from camaddon import reichweite as rw
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import werkzeuge as wz

    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    pfad_maschine = os.path.join(ordner, "fraese.FCStd")
    asm.Document.saveAs(pfad_maschine)
    yield 300
    t1 = wz.standardwerkzeug(1)
    bibliothek = wz.Bibliothek([t1])
    bibliothek.speichern()
    ue.uebergeben(bibliothek)
    doc = FreeCAD.newDocument("Klotz")
    teil = doc.addObject("Part::Feature", "Klotz")
    teil.Shape = Part.makeBox(60, 40, 20)
    doc.recompute()
    FreeCAD.setActiveDocument(doc.Name)
    oben = next(
        f"Face{i + 1}" for i, f in enumerate(teil.Shape.Faces) if abs(f.BoundBox.ZMin - 20) < 1e-6
    )
    jobs = []
    for name in ("Seite 1", "Seite 2"):
        job = PathJob.Create(name, [teil])
        job.Label = name
        tc = js.controller_ohne_transaktion(doc, job, t1, t1.einsaetze(wz.ALLE)[0])
        pf.lege_an(job, tc, 1.0, 8.0, flaechen=[oben])
        rw.merke_maschine(job, pfad_maschine)
        jobs.append(job)
    doc.recompute()
    doc.saveAs(os.path.join(ordner, "klotz.FCStd"))
    seite1, seite2 = jobs
    yield 300

    # Zuletzt an „Seite 2“ gearbeitet (wie nach „Anlegen“ im Assistenten), eine Fläche angeklickt.
    gui_reichweite.job_merken(seite2)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, oben)
    yield 400
    Gui.runCommand("CamAddon_ProgrammSchreiben")
    yield 1500
    d = gui_programm.ProgrammDialog.offen
    h.pruefe(d is not None and d.job is seite2, f"Programm für {d and d.job.Label!r}")
    if d is None:
        return
    h.pruefe(not d.knopf_ordner.isVisible(), "„Ordner öffnen“ vor dem Speichern")
    ziel = os.path.join(ordner, "maschine_freigabe")
    os.makedirs(ziel)
    d.feld_datei.setText(os.path.join(ziel, "KLOTZ_S2.ngc"))
    d._datei_geaendert()
    pfad = d.speichern()
    yield 500
    h.pruefe(pfad and os.path.exists(pfad), f"nicht gespeichert: {pfad}")
    h.pruefe(d.knopf_ordner.isVisible(), "kein „Ordner öffnen“ nach dem Speichern")
    h.bild("1_gespeichert", d)
    d.reject()
    yield 500

    # Beim nächsten Mal: dieselbe Datei; für „Seite 1“ derselbe Ordner.
    Gui.runCommand("CamAddon_ProgrammSchreiben")
    yield 1500
    d = gui_programm.ProgrammDialog.offen
    h.pruefe(
        d is not None and d.feld_datei.text() == os.path.join(ziel, "KLOTZ_S2.ngc"),
        f"wieder: {d and d.feld_datei.text()!r}",
    )
    if d is None:
        return
    d.wahl_job.setCurrentIndex(d.jobs.index(seite1))
    yield 1000
    h.pruefe(
        os.path.dirname(d.feld_datei.text()) == ziel,
        f"Seite 1 nicht im Ordner der Maschine: {d.feld_datei.text()!r}",
    )
    d.reject()  # zuletzt gearbeitet: „Seite 1“ (das Fenster hat ihn gezeigt)
    yield 500

    # „Auf der Maschine prüfen“ ohne Auswahl: „Seite 1“; dort „Programm schreiben …“.
    Gui.Selection.clearSelection()
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 60000)
    yield 1000
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None and pruef.job() is seite1, f"geprüft: {pruef and pruef.job().Label}")
    if pruef is None:
        return
    dialog = pruef.programm_schreiben()
    yield 1500
    h.pruefe(dialog.job is seite1, f"Programm aus dem Prüffenster für {dialog.job.Label!r}")
    h.bild("2_pruefen_programm", pruef.form)
    dialog.reject()
    yield 300
    pruef.reject()
    yield 800
    FreeCAD.closeDocument(doc.Name)
    yield 300
