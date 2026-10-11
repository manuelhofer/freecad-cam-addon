# „Alles aus dieser Aufspannung“ (Frage 14; Manuel, 2026-10-11: „ich gebe eine Fläche an, die in
# dem Spannmittel ist .. und dann wird bearbeitet“): das Schwenkteil, unten im Spannmittel, auf der
# 5-Achs-Fräse Tisch/Tisch. Schritt 2, der Knopf: gewählt sind die 14 Flächen von oben, darunter je
# eine Zeile für die 30°-Schräge (10 Flächen) und die 45°-Fase (3), nichts rot; am Teil in ihren
# Farben, darunter grau, dass „Anlegen“ die Ebenen anlegt. „Ebene schwenken …“ der 30°-Zeile öffnet
# das Fenster mit ihrer Fläche. Ohne Maschine (der
# Assistent nimmt eine 3-Achs-Fräse an): nur von oben, 13 Flächen rot – „Die Maschine schwenkt nicht
# so weit.“ Die Beschriftung in Schritt 1 heißt „Unten im Spannmittel“.
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui
from PySide import QtGui

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.TISCH_TISCH)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    asm.Document.saveAs(os.path.join(ordner, "Fuenfachs.FCStd"))
    yield 300
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 500

    def oeffnen(name):
        """Das Schwenkteil (eine Kopie), Face4 oben angeklickt, „Bearbeitung“ offen."""
        datei = os.path.join(ordner, name + ".FCStd")
        shutil.copy(os.path.join(ADDON, "beispiele", "schwenkteil_5achs.FCStd"), datei)
        doc = FreeCAD.openDocument(datei)
        Gui.activateWorkbench("CAMWorkbench")
        Gui.SendMsgToActiveView("ViewFit")
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, "Schwenkteil", "Face4")
        yield 500
        gui_bearbeitung.nullpunkt_vorgeben(None)
        Gui.runCommand("CamAddon_Bearbeitung")
        yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None)
        yield 1500

    # --- Auf der 5-Achs-Fräse ---------------------------------------------------------------
    yield from oeffnen("Teil1")
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    beschriftungen = [w.text() for w in panel.form.findChildren(QtGui.QLabel)]
    h.pruefe("Unten im Spannmittel" in beschriftungen, "Schritt 1: „Unten im Spannmittel“ fehlt")
    h.pruefe(panel._fuenfachs(), f"keine 5-Achs-Fräse gewählt: {panel.wahl_maschine.currentText()}")
    panel.knopf_weiter.click()
    yield 500
    panel.aus_der_aufspannung()
    yield 800
    h.pruefe(len(panel.gewaehlte) == 14, f"von oben: {panel.gewaehlte}")
    zeilen = [
        w.text()
        for w in panel.richtungen_box.findChildren(QtGui.QLabel)
        if w.isVisibleTo(panel.richtungen_box)
    ]
    h.pruefe(
        panel.richtungen_box.isVisible()
        and len(zeilen) == 3
        and zeilen[0].startswith("30° geneigt: 10 Flächen")
        and zeilen[1].startswith("45° geneigt: 3 Flächen")
        and zeilen[2].startswith("Nach „Anlegen“ legt das Addon diese Ebenen an"),
        f"Zeilen: {zeilen}",
    )
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("1_schritt2_alles_aus_der_aufspannung")
    h.bild("2_fenster", panel.form)
    knoepfe = [
        b for b in panel.richtungen_box.findChildren(QtGui.QPushButton) if b.isVisibleTo(panel.form)
    ]
    h.pruefe(len(knoepfe) == 2, f"Knöpfe: {len(knoepfe)}")
    if knoepfe:
        knoepfe[0].click()
        yield from h.warte_auf(lambda: gui_schwenken.SchwenkenPanel.offen is not None)
        yield 1500
        schwenk = gui_schwenken.SchwenkenPanel.offen
        h.pruefe(
            schwenk is not None and schwenk.flaeche == "Face3",
            f"Ebene schwenken mit {getattr(schwenk, 'flaeche', None)!r}",
        )
        h.bild("3_ebene_schwenken_30")
        if schwenk is not None:
            schwenk.reject()
        yield 800
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 800

    # --- Ohne Maschine: nur von oben, der Rest rot ---------------------------------------------
    ms.speichern([])
    yield from oeffnen("Teil2")
    panel = gui_bearbeitung.BearbeitungPanel.offen
    if panel is None or panel.job is None:
        h.pruefe(False, "kein Fenster beim zweiten Teil")
        return
    panel.knopf_weiter.click()
    yield 500
    panel.aus_der_aufspannung()
    yield 800
    rot = [
        w.text()
        for w in panel.richtungen_box.findChildren(QtGui.QLabel)
        if w.isVisibleTo(panel.richtungen_box)
    ]
    h.pruefe(len(panel.gewaehlte) == 14, f"ohne Maschine von oben: {panel.gewaehlte}")
    h.pruefe(
        len(rot) == 1 and rot[0].startswith("Nicht in dieser Aufspannung: ")
        and rot[0].endswith("Die Maschine schwenkt nicht so weit.")
        and rot[0].count("Face") == 13,
        f"rot: {rot}",
    )  # fmt: skip
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("4_ohne_maschine")
    h.bild("5_fenster_ohne_maschine", panel.form)
    panel.reject()
    yield 800
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 300
