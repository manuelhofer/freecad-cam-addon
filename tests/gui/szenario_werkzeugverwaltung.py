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
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.German, QtCore.QLocale.Germany))

    from camaddon import gui_werkzeugbild, gui_werkzeuge
    from camaddon import werkzeuge as wz
    from camaddon.gui_teile import GRAU

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

    # Ein Werkzeug anlegen: graue Beispielwerte (Ø 12), gültig; das Bild zeigt die Form.
    d.knopf_neu.click()
    yield 200
    farbe_grau = GRAU.name()
    h.pruefe(
        d.feld_durchmesser.text() == "12" and farbe_grau in d.feld_durchmesser.styleSheet(),
        f"Beispiel-Durchmesser: {d.feld_durchmesser.text()!r} {d.feld_durchmesser.styleSheet()!r}",
    )
    h.pruefe(
        d.focusWidget() is d.feld_durchmesser and d.feld_durchmesser.selectedText() == "12",
        "Durchmesser nicht markiert",
    )
    h.pruefe(d.beispiel_hinweis.isVisible() and not d.hinweis.isVisible(), "Hinweis Beispiel")
    h.bild("5_neu_beispielwerte", d)
    # Durchmesser leeren: Hinweis; das Bild zeigt die Form mit dem Beispiel-Ø.
    tippen(d.feld_durchmesser, "")
    yield 200
    h.pruefe(
        d.hinweis.isVisible() and "Durchmesser" in d.hinweis.text(), "Hinweis Durchmesser fehlt"
    )
    h.pruefe(d.feld_durchmesser.styleSheet() == "", "leerer Durchmesser noch grau")
    muster, fremd = gui_werkzeugbild.mit_beispielmassen(d.werkzeug)
    h.pruefe(muster.durchmesser == 12 and "durchmesser" in fremd, f"Bild ohne Ø: {muster}")
    h.bild("5_neu_ohne_durchmesser", d)
    # Enter im Feld schließt den Dialog nicht.
    tippen(d.feld_durchmesser, "12")
    yield 200
    h.pruefe(d.isVisible(), "Enter im Feld hat den Dialog geschlossen")
    tippen(d.feld_schneidenlaenge, "26")
    yield 100
    # Eingetippt ist eigen, auch wenn es der Beispielwert war; z 3 blieb unberührt.
    h.pruefe(d.werkzeug.beispiel == {"schneiden"}, f"noch Beispiel: {d.werkzeug.beispiel}")
    h.pruefe(farbe_grau in d.feld_schneiden.styleSheet(), "Schneidenzahl nicht mehr grau")
    d.feld_schneiden.setValue(4)
    d.feld_schneiden.setValue(3)
    yield 100
    h.pruefe(
        not d.werkzeug.beispiel and not d.beispiel_hinweis.isVisible(), "Beispiel-Hinweis bleibt"
    )
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
    # Länge ab Spindelnase (für „Auf der Maschine prüfen“): bei jeder Art; leer grau die
    # Gesamtlänge, eingetragen am Werkzeug.
    h.pruefe(d.feld_laenge_spindelnase.isVisible(), "Länge ab Spindelnase fehlt")
    grau = d.feld_laenge_spindelnase.placeholderText()
    h.pruefe(grau == "leer: Gesamtlänge 50", f"Länge ab Spindelnase leer: {grau!r}")
    tippen(d.feld_laenge_spindelnase, "115")
    yield 100
    h.pruefe(d.werkzeug.laenge_spindelnase == 115, f"eingetragen: {d.werkzeug.laenge_spindelnase}")
    h.bild("5b_laenge_spindelnase", d)
    tippen(d.feld_laenge_spindelnase, "")
    yield 100
    h.pruefe(d.werkzeug.laenge_spindelnase == 0, "Länge ab Spindelnase leeren")

    # Name wie in der Steuerung: leer grau der Beispielname, eingetragen in der Liste.
    grau = d.feld_name.placeholderText()
    h.pruefe(grau.endswith("Schaftfräser T1 VHM D12 L26"), f"Beispielname: {grau!r}")
    tippen(d.feld_name, "Fraeser VHM 12")  # QTest tippt nur ASCII
    yield 100
    h.pruefe(d.werkzeug.name == "Fraeser VHM 12", f"Name: {d.werkzeug.name!r}")
    h.pruefe(
        d.liste.item(0).text().startswith("T1  Fraeser VHM 12 · Schaftfräser"),
        f"Listenzeile mit Name: {d.liste.item(0).text()!r}",
    )
    h.bild("5c_name", d)

    # Zweites Werkzeug: Torusfräser zeigt den Eckradius; doppelte Nummer wird gemeldet.
    d.knopf_neu.click()
    yield 200
    h.pruefe(not d.zeile_eckradius.isVisible(), "Eckradius beim Schaftfräser sichtbar")
    d.feld_art.setCurrentIndex(d.feld_art.findData(wz.TORUSFRAESER))
    yield 100
    # Die Beispiele der neuen Art: 4 Schneiden, Eckradius 1 – grau.
    h.pruefe(
        (d.feld_schneiden.value(), d.feld_eckradius.text()) == (4, "1")
        and farbe_grau in d.feld_eckradius.styleSheet(),
        f"Torus-Beispiel: z {d.feld_schneiden.value()}, R {d.feld_eckradius.text()!r}",
    )
    h.bild("5d_torus_beispiel", d)
    tippen(d.feld_durchmesser, "10,5")
    tippen(d.feld_eckradius, "0.5")  # Punkt geht auch, wenn das Komma eingestellt ist
    d.feld_nummer.setValue(1)
    yield 200
    h.pruefe(d.zeile_eckradius.isVisible(), "Eckradius beim Torusfräser fehlt")
    h.pruefe("T1 ist schon vergeben" in d.hinweis.text(), f"doppelte Nummer: {d.hinweis.text()!r}")
    h.bild("6_nummer_doppelt", d)
    d.feld_nummer.setValue(2)
    yield 100
    h.pruefe(d.werkzeug.durchmesser == 10.5 and d.werkzeug.eckradius == 0.5, f"{d.werkzeug}")
    # Derselbe Name wie T1 (groß/klein egal): Hinweis, aber erlaubt.
    tippen(d.feld_name, "fraeser vhm 12")
    yield 100
    h.pruefe("heißt auch T1" in d.hinweis.text(), f"doppelter Name: {d.hinweis.text()!r}")
    tippen(d.feld_name, "")
    yield 100
    h.pruefe(d.werkzeug.name == "" and not d.hinweis.isVisible(), "Name leeren")

    # Die Arten nach Gruppen (Spezifikation Werkzeugarten); jede zeigt ihre
    # Felder. Zurück beim Torusfräser ist alles wie vorher.
    d.feld_art.showPopup()
    yield 400
    h.bild("6b_arten_auswahl", d.feld_art.view().window())
    d.feld_art.hidePopup()
    yield 100
    art = d.feld_art
    koepfe = [art.itemText(i) for i in range(art.count()) if art.itemData(i) is None]
    h.pruefe(koepfe == ["Fräsen", "Bohren", "Drehen", "Antasten"], f"Gruppen: {koepfe}")
    art.setCurrentIndex(art.findData(wz.GEWINDEBOHRER_RECHTS))
    yield 200
    h.pruefe(
        d.zeile_steigung.isVisible() and not d.zeile_eckradius.isVisible(),
        "Gewindebohrer: Steigung fehlt oder Eckradius da",
    )
    h.pruefe(
        (d.beschriftung_schneidenlaenge.text(), d.feld_steigung.text()) == ("Gewindelänge", "1,5")
        and farbe_grau in d.feld_steigung.styleSheet(),
        f"Gewindebohrer: {d.beschriftung_schneidenlaenge.text()!r}, P {d.feld_steigung.text()!r}",
    )
    # Gewindebohrer haben keine Schneidenzahl (Manuel); Pflicht sind D und Steigung.
    h.pruefe(not d.zeile_schneiden.isVisible(), "Gewindebohrer mit Schneidenzahl")
    h.pruefe(
        d.beschriftung_steigung.font().bold() and d.beschriftung_durchmesser.font().bold(),
        f"Gewindebohrer fett: Steigung {d.beschriftung_steigung.font().bold()}, "
        f"D {d.beschriftung_durchmesser.font().bold()}, "
        f"Gewicht {d.beschriftung_steigung.font().weight()} / "
        f"{d.beschriftung_durchmesser.font().weight()}, "
        f"Stil {d.beschriftung_steigung.styleSheet()!r}",
    )
    h.bild("6c_gewindebohrer", d)
    art.setCurrentIndex(art.findData(wz.ZENTRIERBOHRER))
    yield 200
    h.pruefe(
        d.beschriftung_durchmesser.text() == "Zapfen-Ø"
        and d.feld_spitzenwinkel.placeholderText() == "üblich: 60",
        f"Zentrierbohrer: {d.beschriftung_durchmesser.text()!r}, "
        f"{d.feld_spitzenwinkel.placeholderText()!r}",
    )
    h.bild("6d_zentrierbohrer", d)
    art.setCurrentIndex(art.findData(wz.DREHWERKZEUG))
    yield 200
    h.pruefe(
        not d.zeile_durchmesser.isVisible()
        and d.zeile_eckradius.isVisible()
        and d.beschriftung_eckradius.text() == "Eckenradius"
        and d.feld_ausfuehrung.currentData() == wz.RECHTS,
        "Drehwerkzeug: Felder",
    )
    h.bild("6e_drehwerkzeug", d)
    art.setCurrentIndex(art.findData(wz.TORUSFRAESER))
    yield 200
    w = d.werkzeug
    h.pruefe(
        (w.durchmesser, w.eckradius, w.schneiden, w.steigung, w.ausfuehrung)
        == (10.5, 0.5, 4, 0, ""),
        f"zurück beim Torusfräser: {w}",
    )

    # OK speichert und schließt – auch wenn in einem Feld noch keine Zahl steht (nur „,“):
    # Dort bleibt der alte Wert.
    d._zahlenfelder["eckradius"].setText(",")
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 500
    h.pruefe(gui_werkzeuge.WerkzeugDialog.offen is None, "OK hat nicht geschlossen")
    gespeichert = wz.Bibliothek.laden()
    h.pruefe(
        [(w.nummer, w.durchmesser, w.art) for w in gespeichert.sortierte_werkzeuge()]
        == [(1, 12, wz.SCHAFTFRAESER), (2, 10.5, wz.TORUSFRAESER)],
        f"gespeichert: {gespeichert.als_dict()['werkzeuge']}",
    )
    h.pruefe(gespeichert.mit_nummer(1).name == "Fraeser VHM 12", "Name nicht gespeichert")
    h.pruefe(gespeichert.mit_nummer(2).eckradius == 0.5, "Eckenradius nach „,“ nicht mehr 0,5")

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

    # Der erste Einsatz eines neuen Werkzeugs, oben 1.4301 (D-12): „+ Einsatz“ geht, der
    # Einsatz gilt für alle Werkstoffe, oben steht dann „Alle Werkstoffe“.
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d is not None and d.werkstoff == "1.4301", "Werkstoff beim dritten Öffnen")
    if d is None:
        return
    d.knopf_neu.click()
    yield 200
    s = d.schnittwerte
    h.pruefe(s.knopf_plus.isEnabled(), "„+ Einsatz“ beim neuen Werkzeug gesperrt")
    h.pruefe(
        s.zustand.text().startswith("Dieses Werkzeug hat noch keine Schnittwerte."),
        f"ohne Einsatz: {s.zustand.text()!r}",
    )
    h.bild("9_neu_ohne_einsatz", d)
    einsatz = s.einsatz_anlegen(wz.VOLLNUT)
    yield 200
    h.pruefe(einsatz is not None and d.werkstoff == wz.ALLE, f"Werkstoff: {d.werkstoff!r}")
    h.pruefe(d.werkzeug.schnittwerte.get(wz.ALLE) == [einsatz], "nicht für alle Werkstoffe")
    h.pruefe(
        s.zustand.text().startswith("Der erste Einsatz gilt für alle Werkstoffe")
        and "1.4301" in s.zustand.text(),
        f"Satz dazu: {s.zustand.text()!r}",
    )
    h.bild("9b_erster_einsatz", d)
    QtCore.QTimer.singleShot(0, d.reject)
    yield 500
    frage = h.modal()
    if isinstance(frage, QtGui.QMessageBox):
        frage.button(QtGui.QMessageBox.Discard).click()
    yield 500
