# „Auf der Maschine prüfen“ mit einem großen Job im Takt (P-2026-10-11-41): Manuels Nasen-Testteil
# (330 000 Schritte) auf der Beispiel-Drehmaschine mit Y. Beim Öffnen rechnet das Fenster Reichweite
# und Abfahren Schritt für Schritt aus der Ereignisschleife – oben grau „Rechnet …“, Abspieler und
# „Kollision prüfen“ warten; eine Uhr des Fensters zählt mit, wie lange es am Stück stand (bis dahin
# 6,5 s). Eine Eingabe im Nullpunkt mitten im Lauf beginnt von vorn; am Ende stehen alle Stationen
# da und alles ist wieder bedienbar.
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
    from camaddon import beispielmaschine, gui_reichweite
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
    beginn = time.perf_counter()
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 120000, 10)
    panel = gui_reichweite.PruefPanel.offen
    h.pruefe(panel is not None, "kein Prüffenster")
    if panel is None:
        return
    h.pruefe(panel.rechnet(), "der große Job rechnet nicht im Takt")
    h.pruefe(
        not panel.abspieler.isEnabled() and not panel.kollision.knopf.isEnabled(),
        "Abspieler oder „Kollision prüfen“ während des Rechnens bedienbar",
    )
    yield 300
    h.bild("1_rechnet", panel.form)
    # Mitten im Lauf eine Eingabe: Er beginnt von vorn (die Uhr des Fensters, dann pruefe()).
    panel.felder_nullpunkt["Z"].setText("1")
    yield from h.warte_auf(lambda: not panel.rechnet() and not panel._uhr.isActive(), 300000)
    dauer = time.perf_counter() - beginn
    uhr.stop()
    pausen = [b - a for a, b in zip(takte, takte[1:], strict=False)]
    laengste = max(pausen or [0.0])
    with open(os.path.join(os.environ["CAMADDON_AUSGABE"], "takt.txt"), "w") as f:
        f.write(f"bis fertig {dauer:.1f} s, Takte {len(takte)}, längste Pause {laengste:.2f} s\n")
    h.pruefe(len(takte) > 20, f"die Ereignisschleife kam in {dauer:.1f} s kaum dran: {len(takte)}")
    h.pruefe(laengste < 3.0, f"das Fenster stand {laengste:.1f} s am Stück")
    h.pruefe(
        panel.abfahrt is not None and len(panel.abfahrt.stationen) > 300000,
        f"Stationen: {len(panel.abfahrt.stationen) if panel.abfahrt else None}",
    )
    h.pruefe(
        panel.abspieler.isEnabled() and panel.kollision.knopf.isEnabled(),
        "nach dem Rechnen nicht bedienbar",
    )
    h.pruefe("Rechnet" not in panel.urteil.text(), f"oben: {panel.urteil.text()!r}")
    yield 500
    h.bild("2_fertig", panel.form)
    panel.reject()
    yield 800
    FreeCAD.closeDocument(teil.Name)
    yield 300
