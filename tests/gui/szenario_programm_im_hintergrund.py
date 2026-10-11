# „Programm schreiben“ mit einem großen Job auf einem Nebenrechner (P-2026-10-11-50): Manuels
# Nasen-Testteil (über 200 000 Sätze) auf der Beispiel-Drehmaschine mit Y. Beim Öffnen steht in
# der Vorschau „Rechnet auf einem Nebenrechner …“, bis der Arbeiter das Programm gerechnet hat;
# „Speichern“ rechnet dort Programm und Nachlesen, schreibt die Datei und sagt, was gespeichert
# ist. Eine Uhr des Fensters zählt mit, wie lange es am Stück stand (bis dahin 2,1 s beim Öffnen,
# 2,3 s beim Speichern).
import os
import tempfile
import time

import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import camaddon
    from camaddon import beispielmaschine, gui_programm
    from camaddon import maschinenspeicher as msp
    from camaddon import reichweite as rw

    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    pfad_maschine = os.path.join(ordner, "drehmaschine_y.FCStd")
    asm.Document.saveAs(pfad_maschine)
    msp.merken_datei(pfad_maschine)
    teil = FreeCAD.openDocument(
        os.path.join(camaddon.ADDON_ORDNER, "beispiele", "testteil_4achs_nase.FCStd")
    )
    job = teil.getObject("Job")
    rw.merke_maschine(job, pfad_maschine)
    yield 1500
    FreeCAD.setActiveDocument(teil.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400

    takte = []
    uhr = QtCore.QTimer()
    uhr.setInterval(20)
    uhr.timeout.connect(lambda: takte.append(time.perf_counter()))
    uhr.start()

    def laengste():
        pausen = [b - a for a, b in zip(takte, takte[1:], strict=False)]
        return max(pausen or [0.0])

    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_ProgrammSchreiben"))
    yield from h.warte_auf(lambda: gui_programm.ProgrammDialog.offen is not None, 60000, 10)
    d = gui_programm.ProgrammDialog.offen
    h.pruefe(d is not None, "„Programm schreiben“ öffnet kein Fenster")
    if d is None:
        return
    h.pruefe(d.rechnet(), "der große Job rechnet nicht auf einem Nebenrechner")
    h.pruefe(d.vorschau.toPlainText().startswith("Rechnet"), f"{d.vorschau.toPlainText()[:60]!r}")
    yield 200
    h.bild("1_rechnet", d)
    yield from h.warte_auf(lambda: not d.rechnet(), 120000)
    oeffnen = laengste()
    text = d.vorschau.toPlainText()
    h.pruefe(not text.startswith("Rechnet") and len(text.splitlines()) > 20, f"{text[:80]!r}")
    yield 300
    h.bild("2_vorschau", d)

    takte.clear()
    ziel = os.path.join(ordner, "nase.mpf")
    d.feld_datei.setText(ziel)
    h.pruefe(d.speichern() is None and d.rechnet(), "Speichern rechnet nicht im Hintergrund")
    h.pruefe(not d.knopf_speichern.isEnabled(), "„Speichern“ während des Rechnens frei")
    yield from h.warte_auf(lambda: not d.rechnet(), 120000)
    speichern = laengste()
    uhr.stop()
    with open(os.path.join(os.environ["CAMADDON_AUSGABE"], "takt.txt"), "w") as f:
        f.write(f"längste Pause: öffnen {oeffnen:.2f} s, speichern {speichern:.2f} s\n")
    h.pruefe(os.path.isfile(ziel) and os.path.getsize(ziel) > 1000000, "keine Datei geschrieben")
    h.pruefe("Gespeichert" in d.ergebnis.text(), f"Ergebnis: {d.ergebnis.text()!r}")
    h.pruefe(d.knopf_speichern.isEnabled(), "„Speichern“ danach gesperrt")
    h.pruefe(oeffnen < 1.0 and speichern < 1.0, f"stand {oeffnen:.2f} / {speichern:.2f} s")
    # Dasselbe Programm wie im Fenster selbst gerechnet (auf der Kopie des Dokuments).
    with open(ziel, encoding="utf-8") as f:
        geschrieben = f.read()
    h.pruefe(geschrieben == d._programm().text, "die Datei ist anders als im Fenster gerechnet")
    yield 300
    h.bild("3_gespeichert", d)
    d.reject()
    yield 500
    FreeCAD.closeDocument(teil.Name)
    yield 300
