# „Einrichtblatt …“ (W-019; Manuel, 2026-10-12: „eine einrichtblatt zum drucken/als pdf“; „für
# JEDE bearbeitung“): Manuels C-Ring mit seinem Job, im Menü „CAM-Addon“ steht „Einrichtblatt …“.
# Ohne Auswahl nimmt es den einzigen Job. Das Fenster zeigt die Werkzeuge (T1 mit Ø), die
# Aufspannung mit Rohteil, Spannmittel und Nullpunkt, ein Bild des Teils und den Schritt
# „Räumen T1“ mit Zeit. „Als PDF speichern“ schreibt eine PDF-Datei, „Als HTML speichern“ eine
# Seite mit denselben Schritten.
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
    from camaddon import gui_einrichtblatt

    ordner = tempfile.mkdtemp()
    datei = os.path.join(ordner, "cring.FCStd")
    shutil.copy(os.path.join(ADDON, "beispiele", "c_ring_nut_3achs.FCStd"), datei)
    doc = FreeCAD.openDocument(datei)
    yield 1000
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.clearSelection()
    yield 500
    menue = next(
        (
            m
            for m in Gui.getMainWindow().menuBar().findChildren(QtGui.QMenu)
            if m.title() == "CAM-Addon"
        ),
        None,
    )
    texte = [a.text() for a in menue.actions()] if menue is not None else []
    h.pruefe("Einrichtblatt …" in texte, f"Menü: {texte}")
    Gui.runCommand("CamAddon_Einrichtblatt")
    yield from h.warte_auf(lambda: gui_einrichtblatt.EinrichtblattDialog.offen is not None, 30000)
    yield 1000
    dialog = gui_einrichtblatt.EinrichtblattDialog.offen
    h.pruefe(dialog is not None, "kein Fenster")
    if dialog is None:
        return
    text = dialog.vorschau.toPlainText()
    for soll in ("Werkzeuge", "T1", "Aufspannung 1", "Rohteil", "Spannmittel", "Nullpunkt",
                 "Räumen T1", "min"):  # fmt: skip
        h.pruefe(soll in text, f"„{soll}“ fehlt: {text[:400]!r}")
    a = dialog.blatt.aufspannungen[0]
    h.pruefe(bool(a.bild) and os.path.exists(a.bild), f"kein Bild: {a.bild!r}")
    h.pruefe("," in a.rohteil, f"Dezimalkomma im Rohteil: {a.rohteil!r}")
    h.bild("1_einrichtblatt", dialog)
    pdf = dialog.als_pdf(os.path.join(ordner, "blatt.pdf"))
    yield 500
    groesse = os.path.getsize(pdf) if pdf and os.path.exists(pdf) else 0
    h.pruefe(groesse > 5000, f"PDF: {groesse} Bytes")
    with open(pdf, "rb") as f:
        h.pruefe(f.read(5) == b"%PDF-", "keine PDF-Datei")
    seite = dialog.als_html(os.path.join(ordner, "blatt.html"))
    with open(seite, encoding="utf-8") as f:
        h.pruefe("Räumen T1" in f.read(), "HTML ohne Schritt")
    if os.environ.get("AUSGABE"):
        shutil.copy(pdf, os.path.join(os.environ["AUSGABE"], "einrichtblatt.pdf"))
    dialog.reject()
    yield 500
    h.pruefe(gui_einrichtblatt.EinrichtblattDialog.offen is None, "Fenster nicht zu")
    FreeCAD.closeDocument(doc.Name)
