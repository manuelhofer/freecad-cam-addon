# Die Bilder der Werkzeugarten (Spezifikation Werkzeugarten, Stufe 3): Ein
# neues Werkzeug geht in der Werkzeugverwaltung durch alle 26 Arten; jedes
# Mal zeigt das Bild neben den Feldern die Form der Art mit ihren
# Beispielmaßen – alle zusammen in einer Übersicht. Dazu die Auswahl mit den
# kleinen Bildern vor den Namen.
import os

import FreeCADGui as Gui
from PySide import QtCore, QtGui

SPALTEN = 7
BESCHRIFTUNG = 30  # Pixel unter jedem Bild


def gemalt(bild):
    """Wie viele Pixel des Bildes sind nicht Hintergrund?"""
    grund = bild.pixel(0, 0)
    return sum(
        1
        for x in range(0, bild.width(), 2)
        for y in range(0, bild.height(), 2)
        if bild.pixel(x, y) != grund
    )


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300

    from camaddon import gui_werkzeuge
    from camaddon import werkzeuge as wz

    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d is not None, "Werkzeugverwaltung geht nicht auf")
    if d is None:
        return
    d.knopf_neu.click()
    yield 200

    # Die Auswahl: vor jeder Art ihr Bild.
    ohne_bild = [
        d.feld_art.itemText(i)
        for i in range(d.feld_art.count())
        if d.feld_art.itemData(i) is not None and d.feld_art.itemIcon(i).isNull()
    ]
    h.pruefe(not ohne_bild, f"Arten ohne Bild in der Auswahl: {ohne_bild}")
    d.feld_art.showPopup()
    yield 400
    h.bild("1_auswahl_mit_bildern", d.feld_art.view().window())
    d.feld_art.hidePopup()
    yield 100

    # Alle Arten der Reihe nach; das Bild jeder Art in die Übersicht.
    bildbreite, bildhoehe = d.werkzeugbild.width(), d.werkzeugbild.height()
    zeilen = (len(wz.ARTEN) + SPALTEN - 1) // SPALTEN
    zelle_b, zelle_h = bildbreite + 60, bildhoehe + BESCHRIFTUNG
    uebersicht = QtGui.QImage(SPALTEN * zelle_b, zeilen * zelle_h, QtGui.QImage.Format_RGB32)
    uebersicht.fill(QtGui.QColor("white"))
    maler = QtGui.QPainter(uebersicht)
    leer = []
    for i, art in enumerate(wz.ARTEN):
        d.feld_art.setCurrentIndex(d.feld_art.findData(art))
        yield 150
        bild = d.werkzeugbild.grab().toImage()
        if gemalt(bild) < 30:
            leer.append(art)
        x, y = (i % SPALTEN) * zelle_b, (i // SPALTEN) * zelle_h
        maler.drawImage(QtCore.QPointF(x + 30, y), bild)
        maler.drawText(
            QtCore.QRectF(x, y + bildhoehe, zelle_b, BESCHRIFTUNG),
            QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
            wz.art_text(art),
        )
    maler.end()
    uebersicht.save(os.path.join(os.environ["CAMADDON_AUSGABE"], "2_alle_arten.png"))
    h.pruefe(not leer, f"ohne Bild: {leer}")

    # Links ist das Spiegelbild von rechts – beim Drehwerkzeug zu sehen.
    d.feld_art.setCurrentIndex(d.feld_art.findData(wz.DREHWERKZEUG))
    yield 150
    d.feld_ausfuehrung.setCurrentIndex(d.feld_ausfuehrung.findData(wz.LINKS))
    yield 150
    h.bild("3_drehwerkzeug_links", d)
    # Abbrechen fragt „Speichern?“ und blockiert, bis die Frage beantwortet ist.
    QtCore.QTimer.singleShot(0, d.knoepfe.button(QtGui.QDialogButtonBox.Cancel).click)
    yield 500
    frage = h.modal()
    if isinstance(frage, QtGui.QMessageBox):  # „Speichern?“ – nein
        frage.button(QtGui.QMessageBox.Discard).click()
    yield 300
