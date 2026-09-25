# Werkzeugverwaltung (W-002): Werkstoff suchen und wählen, Werkzeuge anlegen,
# Hinweise am Feld, OK speichert, Wiederöffnen zeigt denselben Stand,
# Abbrechen mit Änderungen fragt nach und verwirft.
import os

import FreeCADGui as Gui
from PySide import QtCore, QtGui
from PySide6 import QtTest

AUSGABE = os.environ["CAMADDON_AUSGABE"]


def bildschirm(name):
    """Der ganze (unsichtbare) Bildschirm – mit aufgeklappten Listen, die eigene Fenster sind."""
    QtGui.QApplication.processEvents()
    bild = QtGui.QApplication.primaryScreen().grabWindow(0)
    bild.save(os.path.join(AUSGABE, name + ".png"))


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
        erster.accept()
    yield 300
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.German, QtCore.QLocale.Germany))

    from camaddon import gui_werkzeuge
    from camaddon import werkzeuge as wz

    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d is not None and d.isVisible(), "Werkzeugverwaltung geht nicht auf")
    if d is None:
        return
    h.pruefe(d.leer.isVisible(), "leere Liste: Hinweis „Neu …“ fehlt")
    h.pruefe(d.werkstoff == wz.ALLE, f"Start mit Werkstoff {d.werkstoff!r} statt „Alle“")
    h.bild("1_leer", d)

    # Werkstoff suchen: „1.43“ tippen, erster Vorschlag, Enter.
    zeile = d.wahl_werkstoff.lineEdit()
    zeile.setFocus()
    zeile.selectAll()
    QtTest.QTest.keyClicks(zeile, "1.43")
    yield 400
    vorschlaege = d.wahl_werkstoff.completer().popup()
    h.pruefe(vorschlaege.isVisible(), "Suche zeigt keine Vorschläge")
    bildschirm("2_suche_1_43")
    QtTest.QTest.keyClick(vorschlaege, QtCore.Qt.Key_Down)
    QtTest.QTest.keyClick(vorschlaege, QtCore.Qt.Key_Return)
    yield 300
    h.pruefe(d.werkstoff == "1.4301", f"gewählt: {d.werkstoff!r} statt 1.4301")
    info = d.werkstoff_info.text()
    h.pruefe("Cr 17,5–19,5" in info and "≤ 215 HB" in info, f"Info zu 1.4301: {info!r}")
    h.bild("3_werkstoff_1_4301", d)

    # Die ganze Liste mit den ISO-Farben.
    d.wahl_werkstoff.showPopup()
    yield 400
    bildschirm("4_werkstoffliste")
    d.wahl_werkstoff.hidePopup()
    yield 200

    # Ein Werkzeug anlegen; Enter im Feld schließt den Dialog nicht.
    d.knopf_neu.click()
    yield 200
    h.pruefe(
        d.hinweis.isVisible() and "Durchmesser" in d.hinweis.text(), "Hinweis Durchmesser fehlt"
    )
    h.bild("5_neu_ohne_durchmesser", d)
    tippen(d.feld_durchmesser, "12")
    yield 200
    h.pruefe(d.isVisible(), "Enter im Feld hat den Dialog geschlossen")
    d.feld_schneiden.setValue(3)
    tippen(d.feld_schneidenlaenge, "26")
    tippen(d.feld_bezeichnung, "Hoffmann 12 mm")  # QTest tippt nur ASCII
    yield 200
    h.pruefe(
        d.liste.item(0).text() == "T1  Schaftfräser Ø 12 · z 3 · VHM",
        f"Listenzeile: {d.liste.item(0).text()!r}",
    )
    h.pruefe(not d.hinweis.isVisible(), f"Hinweis trotz vollständiger Werte: {d.hinweis.text()!r}")
    h.pruefe(d.werkzeugbild.werkzeug is d.werkzeug, "Werkzeugbild zeigt nicht das gewählte")
    # Gesamtlänge und Schaft leer: grau steht, was CAM stattdessen bekommt.
    grau = (d.feld_gesamtlaenge.placeholderText(), d.feld_schaft.placeholderText())
    h.pruefe(grau == ("geschätzt: 50", "wie D: 12"), f"Schätzung: {grau}")
    tippen(d.feld_gesamtlaenge, "20")
    yield 100
    h.pruefe("kürzer als die Schneide" in d.hinweis.text(), f"Hinweis: {d.hinweis.text()!r}")
    h.bild("5b_gesamtlaenge_zu_kurz", d)
    tippen(d.feld_gesamtlaenge, "")
    yield 100
    h.pruefe(d.werkzeug.gesamtlaenge == 0 and not d.hinweis.isVisible(), "Gesamtlänge leeren")

    # Zweites Werkzeug: Torusfräser zeigt den Eckradius; doppelte Nummer wird gemeldet.
    d.knopf_neu.click()
    yield 200
    h.pruefe(not d.zeile_eckradius.isVisible(), "Eckradius beim Schaftfräser sichtbar")
    d.feld_art.setCurrentIndex(d.feld_art.findData(wz.TORUSFRAESER))
    tippen(d.feld_durchmesser, "10,5")
    tippen(d.feld_eckradius, "0,5")
    d.feld_nummer.setValue(1)
    yield 200
    h.pruefe(d.zeile_eckradius.isVisible(), "Eckradius beim Torusfräser fehlt")
    h.pruefe("T1 ist schon vergeben" in d.hinweis.text(), f"doppelte Nummer: {d.hinweis.text()!r}")
    h.bild("6_nummer_doppelt", d)
    d.feld_nummer.setValue(2)
    yield 100
    h.pruefe(d.werkzeug.durchmesser == 10.5 and d.werkzeug.eckradius == 0.5, f"{d.werkzeug}")

    # OK speichert und schließt.
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 500
    h.pruefe(gui_werkzeuge.WerkzeugDialog.offen is None, "OK hat nicht geschlossen")
    gespeichert = wz.Bibliothek.laden()
    h.pruefe(
        [(w.nummer, w.durchmesser, w.art) for w in gespeichert.sortierte_werkzeuge()]
        == [(1, 12, wz.SCHAFTFRAESER), (2, 10.5, wz.TORUSFRAESER)],
        f"gespeichert: {gespeichert.als_dict()['werkzeuge']}",
    )

    # Wieder öffnen: derselbe Werkstoff, dieselben Werkzeuge.
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d.werkstoff == "1.4301", f"Werkstoff nach Wiederöffnen: {d.werkstoff!r}")
    h.pruefe(d.liste.count() == 2, f"{d.liste.count()} Werkzeuge nach Wiederöffnen")
    # Suche: nur der Torusfräser; das gewählte Werkzeug folgt.
    d.suche.setText("torus")
    yield 100
    sichtbar = [d.liste.item(z).text() for z in range(2) if not d.liste.item(z).isHidden()]
    h.pruefe(len(sichtbar) == 1 and "Torus" in sichtbar[0], f"Suche „torus“: {sichtbar}")
    h.pruefe(d.werkzeug is not None and d.werkzeug.art == wz.TORUSFRAESER, "Auswahl folgt nicht")
    h.bild("7a_suche", d)
    d.suche.clear()
    yield 100
    d.liste.setCurrentRow(0)
    yield 200
    h.bild("7_wieder_offen", d)

    # Ändern und abbrechen: Rückfrage, „Verwerfen“ lässt die Datei, wie sie war.
    tippen(d.feld_durchmesser, "16")
    QtCore.QTimer.singleShot(0, d.reject)  # die Rückfrage blockiert, bis sie beantwortet ist
    yield 500
    frage = h.modal()
    h.pruefe(isinstance(frage, QtGui.QMessageBox), f"keine Rückfrage beim Abbrechen: {frage}")
    if isinstance(frage, QtGui.QMessageBox):
        h.bild("8_rueckfrage", frage)
        frage.button(QtGui.QMessageBox.Discard).click()
    yield 500
    h.pruefe(gui_werkzeuge.WerkzeugDialog.offen is None, "nach „Verwerfen“ noch offen")
    h.pruefe(
        wz.Bibliothek.laden().sortierte_werkzeuge()[0].durchmesser == 12,
        "verworfen, aber gespeichert",
    )
