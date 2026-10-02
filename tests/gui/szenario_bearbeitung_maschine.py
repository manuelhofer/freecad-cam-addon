# Die Maschine in Schritt 1 (W-011 S2; Manuel, 2026-10-02: „Immer wenn ich ein Teil lade,
# sollte ich die Maschine auswählen … wenn ich das Teil dann woanders bearbeite, kann ich das noch
# mal laden“): Die Beispiel-Drehmaschine und die 3-Achs-Fräse gespeichert – beide stehen in der
# Liste. Ein Block, die Oberseite angeklickt, „Bearbeitung“: Schritt 1 zeigt oben „Maschine“ mit
# beiden; vorgewählt die erste (noch keine zuletzt benutzt), der Job hat sie. Die Fräse gewählt:
# Der Job merkt sie sich, Schritt 2 sagt „Maschine: 3-Achs-Fräse · …“. „Anlegen“, die Fräse ist
# zu: „Auf der Maschine prüfen“ öffnet sie ohne Frage. Ein zweites Teil: vorgewählt die Fräse
# (zuletzt benutzt). Ohne Maschine in der Liste: „– keine Maschine –“ und der Satz, was der
# Assistent dann annimmt.
import os
import shutil
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

    from camaddon import beispielmaschine, gui_bearbeitung, gui_reichweite
    from camaddon import hoehenfeld as hf
    from camaddon import maschinenspeicher as ms
    from camaddon import reichweite as rw
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    dateien = {}
    for art, name in ((beispielmaschine.DREHMASCHINE, "Drehmaschine"),
                      (beispielmaschine.FRAESE_3, "Fraese")):  # fmt: skip
        asm, _maschine = beispielmaschine.lade(art)
        yield from h.warte_auf(lambda asm=asm: FreeCAD.ActiveDocument is asm.Document)
        asm.Document.saveAs(os.path.join(ordner, name + ".FCStd"))
        dateien[name] = asm.Document.FileName
        yield 300
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 500

    def block(name):
        """Ein Block 100 × 60 × 20, die Oberseite gewählt, „Bearbeitung“ offen. Gibt das
        Fenster zurück (über `fenster`)."""
        doc = FreeCAD.newDocument(name)
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
        fenster.clear()
        fenster.append(gui_bearbeitung.BearbeitungPanel.offen)

    fenster = []

    # --- Erstes Teil: beide Maschinen zur Wahl, die erste vorgewählt ----------------------------
    yield from block("Teil1")
    panel = fenster[0]
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    wahl = panel.wahl_maschine
    texte = [wahl.itemText(i) for i in range(wahl.count())]
    h.pruefe(
        texte == ["Drehmaschine mit Y-Achse – Drehmaschine mit Revolver (12 Plätze), C, Y",
                  "3-Achs-Fräse"],
        f"zur Wahl: {texte}",
    )  # fmt: skip
    h.pruefe(
        getattr(job, rw.EIGENSCHAFT_MASCHINE, "") == dateien["Drehmaschine"],
        f"am Job: {getattr(job, rw.EIGENSCHAFT_MASCHINE, '')!r}",
    )
    h.pruefe(not panel.maschine_hinweis.isVisible(), "Hinweis bei gewählter Maschine")

    # Die Fräse gewählt: Der Job merkt sie sich, Schritt 2 sagt es.
    wahl.setCurrentIndex(1)
    yield 300
    h.pruefe(
        getattr(job, rw.EIGENSCHAFT_MASCHINE, "") == dateien["Fraese"],
        f"Fräse nicht am Job: {getattr(job, rw.EIGENSCHAFT_MASCHINE, '')!r}",
    )
    h.bild("1_schritt1_maschine", panel.form)
    panel.knopf_weiter.click()
    yield 500
    kurz = panel.rohteil_kurz.text()
    h.pruefe(kurz.startswith("Maschine: 3-Achs-Fräse · "), f"Schritt 2: {kurz!r}")
    h.bild("2_schritt2", panel.form)

    # --- Anlegen; „Auf der Maschine prüfen“ öffnet die Fräse ohne Frage -----------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400  # 1.1.3 verarbeitet die Auswahl verzögert
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(
        lambda: gui_reichweite.PruefPanel.offen is not None or h.modal() is not None, 120000
    )
    yield 1000
    meldung = h.modal()
    h.pruefe(meldung is None, f"Frage statt Fenster: {meldung}")
    if meldung is not None:
        meldung.reject()
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(
        pruef is not None and ms.gleiche_datei(pruef.assembly.Document.FileName, dateien["Fraese"]),
        "nicht auf der Fräse des Jobs",
    )
    if pruef is not None:
        Gui.SendMsgToActiveView("ViewFit")
        yield 500
        h.bild("3_pruefen_auf_der_fraese")
        pruef.reject()
        yield 800

    # --- Ein zweites Teil: vorgewählt die Fräse (zuletzt benutzt) ------------------------------
    yield from block("Teil2")
    panel = fenster[0]
    h.pruefe(
        panel is not None and panel.wahl_maschine.currentData() == dateien["Fraese"],
        f"vorgewählt: {panel and panel.wahl_maschine.currentText()!r}",
    )
    if panel is not None:
        panel.reject()
    yield 800

    # --- Ohne Maschine in der Liste: „keine“ und der Satz dazu ---------------------------------
    ms.speichern([])
    yield from block("Teil3")
    panel = fenster[0]
    if panel is not None:
        wahl = panel.wahl_maschine
        h.pruefe(
            wahl.count() == 1 and wahl.currentText() == "– keine Maschine –",
            f"ohne Liste: {[wahl.itemText(i) for i in range(wahl.count())]}",
        )
        h.pruefe(
            panel.maschine_hinweis.isVisible()
            and panel.maschine_hinweis.text().startswith("Noch keine Maschine gewählt"),
            f"Hinweis: {panel.maschine_hinweis.text()!r}",
        )
        h.bild("4_ohne_maschine", panel.form)
        panel.reject()
    yield 800
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 300
    shutil.rmtree(ordner, ignore_errors=True)
