# Halter (W-002 Stufe D): In der Werkzeugverwaltung ein Werkzeug mit 83 mm
# Gesamtlänge; neben der Länge ab Spindelnase „Halter – ohne –“ und „Halter …“.
# Das Fenster „Halter“ ist leer; „Neu“ → „Spannzangenfutter ER32 · SK40“: die
# Kontur Flansch Ø63 × 16, Körper Ø50 × 54, „Länge 70,00 mm · größter Ø
# 63,00 mm“, das Bild zeigt Halter und Werkzeug, über OK „OK: T1 bekommt den
# Halter …“. Ein Abschnitt dazu (10 mm, Ø 42) macht ihn 80 mm lang, wieder weg
# 70 mm; Name „SK40 ER32 A70“. OK → das Werkzeug hat den Halter, im leeren Feld
# steht grau „leer: 113 mit Halter“ (70 + 83 − 40). Abbrechen im Halter-Fenster
# verwirft einen neuen Halter. Speichern und neu laden: Halter und Zuordnung
# sind da. Löschen fragt und nennt T1; danach ist T1 ohne Halter.
import os

import FreeCADGui as Gui
from PySide import QtCore, QtGui
from PySide6 import QtTest

AUSGABE = os.environ["CAMADDON_AUSGABE"]


def tippen(feld, text):
    """Feld leeren, `text` Taste für Taste tippen, Enter."""
    feld.setFocus()
    feld.selectAll()
    QtTest.QTest.keyClick(feld, QtCore.Qt.Key_Delete)
    QtTest.QTest.keyClicks(feld, text)
    QtTest.QTest.keyClick(feld, QtCore.Qt.Key_Return)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300

    from camaddon import gui_halter, gui_werkzeuge
    from camaddon import werkzeuge as wz

    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d is not None and d.isVisible(), "Werkzeugverwaltung geht nicht auf")
    if d is None:
        return
    d.knopf_neu.click()
    yield 200
    tippen(d.feld_gesamtlaenge, "83")
    yield 200
    h.pruefe(d.feld_halter.count() == 1, f"Halter-Auswahl: {d.feld_halter.count()} Einträge")
    h.pruefe(d.feld_halter.currentText() == "– ohne –", f"Halter: {d.feld_halter.currentText()}")
    h.pruefe(
        d.feld_laenge_spindelnase.placeholderText() == "leer: Gesamtlänge 83",
        f"Platzhalter ohne Halter: {d.feld_laenge_spindelnase.placeholderText()!r}",
    )

    # --- Das Fenster „Halter“: leer, dann aus der Vorlage ER32 ------------------------------
    QtCore.QTimer.singleShot(0, d.knopf_halter.click)
    yield 500
    f = gui_halter.HalterDialog.offen
    h.pruefe(f is not None and f.isVisible(), "Fenster „Halter“ geht nicht auf")
    if f is None:
        return
    h.pruefe(f.leer.isVisible() and not f.rahmen.isVisible(), "leer: Hinweis „Neu“ fehlt")
    h.pruefe(f.ok_hinweis.text() == "OK: T1 bleibt ohne Halter.", f"{f.ok_hinweis.text()!r}")
    h.bild("1_halter_leer", f)
    vorlage = next(a for a in f.menue_neu.actions() if a.text() == "Spannzangenfutter ER32 · SK40")
    vorlage.trigger()
    yield 300
    halter = f.gewaehlt
    h.pruefe(halter is not None and f.liste.count() == 1, "Vorlage legt keinen Halter an")
    h.pruefe(f.tabelle.rowCount() == 2, f"Kontur: {f.tabelle.rowCount()} Abschnitte")
    zellen = [f.tabelle.item(0, s).text() for s in range(3)]
    h.pruefe(zellen == ["16", "63", "63"], f"Flansch: {zellen}")
    h.pruefe(
        f.zusammenfassung.text() == "Länge 70,00 mm · größter Ø 63,00 mm",
        f"Zusammenfassung: {f.zusammenfassung.text()!r}",
    )
    h.pruefe(
        f.ok_hinweis.text() == "OK: T1 bekommt den Halter „Spannzangenfutter ER32 · SK40“.",
        f"{f.ok_hinweis.text()!r}",
    )
    h.pruefe(f.bild.halter is halter and f.bild.laenge == 113, f"Bild: {f.bild.laenge}")
    h.bild("2_er32", f)

    # Ein Abschnitt dazu und wieder weg; ein Name.
    f.tabelle.setCurrentCell(1, 0)
    f.abschnitt_dazu()
    f.tabelle.item(2, 0).setText("10")
    f.tabelle.item(2, 2).setText("42")
    yield 200
    h.pruefe(abs(halter.laenge - 80) < 1e-9, f"mit Abschnitt: {halter.laenge}")
    h.pruefe(f.tabelle.item(2, 1).text() == "50", "neuer Abschnitt nicht so dick wie der davor")
    h.bild("3_abschnitt", f)
    f.tabelle.setCurrentCell(2, 0)
    f.abschnitt_weg()
    h.pruefe(abs(halter.laenge - 70) < 1e-9, f"Abschnitt weg: {halter.laenge}")
    tippen(f.feld_name, "SK40 ER32 A70")
    yield 200
    h.pruefe(f.liste.item(0).text() == "SK40 ER32 A70", f"Liste: {f.liste.item(0).text()}")
    f.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 400

    # --- Zurück beim Werkzeug: der Halter ist gewählt, die Länge geschätzt -------------------
    h.pruefe(gui_halter.HalterDialog.offen is None, "Halter-Fenster noch offen")
    h.pruefe(d.feld_halter.currentText() == "SK40 ER32 A70", f"{d.feld_halter.currentText()}")
    h.pruefe(
        d.feld_laenge_spindelnase.placeholderText() == "leer: 113 mit Halter",
        f"Platzhalter mit Halter: {d.feld_laenge_spindelnase.placeholderText()!r}",
    )
    h.bild("4_werkzeug_mit_halter", d)

    # Abbrechen verwirft: ein neuer Halter kommt nicht an.
    QtCore.QTimer.singleShot(0, d.knopf_halter.click)
    yield 500
    f = gui_halter.HalterDialog.offen
    if f is not None:
        f.neu()
        f.knoepfe.button(QtGui.QDialogButtonBox.Cancel).click()
    yield 300
    h.pruefe(len(d.bibliothek.halter) == 1, f"Abbrechen verwirft nicht: {len(d.bibliothek.halter)}")
    h.pruefe(d.feld_halter.count() == 2, "Auswahl nach Abbrechen")

    # --- Speichern und laden -----------------------------------------------------------------
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 500
    gespeichert = wz.Bibliothek.laden()
    h.pruefe([x.name for x in gespeichert.halter] == ["SK40 ER32 A70"], "Halter nicht gespeichert")
    werkzeug = gespeichert.werkzeuge[0] if gespeichert.werkzeuge else None
    h.pruefe(
        werkzeug is not None and gespeichert.halter_von(werkzeug) is gespeichert.halter[0],
        "Zuordnung nicht gespeichert",
    )

    # --- Löschen: Rückfrage nennt T1, danach ist T1 ohne Halter ------------------------------
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d.feld_halter.currentText() == "SK40 ER32 A70", "nach dem Laden kein Halter gewählt")
    QtCore.QTimer.singleShot(0, d.knopf_halter.click)
    yield 500
    f = gui_halter.HalterDialog.offen
    QtCore.QTimer.singleShot(0, f.loeschen)
    yield 500
    frage = h.modal()
    h.pruefe(isinstance(frage, QtGui.QMessageBox), f"keine Rückfrage beim Löschen: {frage}")
    if isinstance(frage, QtGui.QMessageBox):
        h.pruefe("T1" in frage.text(), f"Rückfrage ohne T1: {frage.text()!r}")
        h.bild("5_loeschen", frage)
        frage.button(QtGui.QMessageBox.Yes).click()
    yield 300
    h.pruefe(f.liste.count() == 0 and f.leer.isVisible(), "nicht gelöscht")
    f.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 300
    h.pruefe(d.feld_halter.currentText() == "– ohne –", "T1 hat noch einen Halter")
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 500
    gespeichert = wz.Bibliothek.laden()
    h.pruefe(gespeichert.halter == [], "Halter nach Löschen noch gespeichert")
    h.pruefe(gespeichert.werkzeuge[0].halter == "", "T1 nennt den gelöschten Halter")
