# Maßsystem inch (Stufe B): Beim ersten Start sind „Zoll“ und „Punkt“
# gewählt. Werkzeugverwaltung: Ein neues Werkzeug hat ½" (0.5 in), neben den
# Feldern steht „in“, die Liste zeigt „Ø 0.5“; getippt wird in Zoll,
# gespeichert in mm. Schnittwerte in in, SFM, ipm und in³/min. Der Umschalter
# „mm / inch“ zeigt dasselbe Werkzeug in mm. Der Planer rechnet in SFM und
# ipm, „Maschine verfahren“ fährt die Beispielmaschine in inch.
import FreeCADGui as Gui
from PySide import QtCore, QtGui
from PySide6 import QtTest


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
        erster.wahl_masssystem.setCurrentIndex(erster.wahl_masssystem.findData("zoll"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData("."))
        erster.accept()
    yield 300

    from camaddon import (
        beispielmaschine,
        einheiten,
        gui_maschine,
        gui_schruppwerte,
        gui_verfahren,
        gui_werkzeuge,
    )
    from camaddon import gui_schnittwerte as gs
    from camaddon import verfahren as vf
    from camaddon import werkzeuge as wz

    h.pruefe(einheiten.masssystem() == einheiten.ZOLL, "Zoll beim ersten Start nicht gespeichert")

    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d is not None, "Werkzeugverwaltung geht nicht auf")
    if d is None:
        return
    h.pruefe(d.wahl_masssystem.currentData() == einheiten.ZOLL, "Umschalter steht nicht auf inch")

    # Neues Werkzeug: ½" mit 1" Schneide, Einheit „in“.
    d.knopf_neu.click()
    yield 200
    einheit = d.feld_durchmesser.parentWidget().einheit.text()
    h.pruefe(
        (d.feld_durchmesser.text(), d.feld_schneidenlaenge.text(), einheit) == ("0.5", "1", "in"),
        f"neu in Zoll: {d.feld_durchmesser.text()!r} {d.feld_schneidenlaenge.text()!r} {einheit!r}",
    )
    h.pruefe(
        d.liste.item(0).text() == "T1  Schaftfräser Ø 0.5 · z 3 · VHM",
        f"Listenzeile: {d.liste.item(0).text()!r}",
    )
    tippen(d.feld_durchmesser, "0.375")
    yield 100
    h.pruefe(abs(d.werkzeug.durchmesser - 9.525) < 1e-9, f"3/8 in: {d.werkzeug.durchmesser} mm")

    # Schnittwerte: Vollnut mit 400 SFM und 0.002 in je Zahn.
    s = d.schnittwerte
    s.einsatz_anlegen(wz.VOLLNUT)
    yield 100
    s.setze(0, gs.VC, "400")
    s.setze(0, gs.FZ, "0.002")
    yield 100
    vollnut = s.werkzeug.einsaetze(wz.ALLE)[0]
    h.pruefe(
        abs(vollnut.vc - 121.92) < 1e-9 and abs(vollnut.fz - 0.0508) < 1e-9,
        f"gespeichert: vc {vollnut.vc} m/min, fz {vollnut.fz} mm",
    )
    koepfe = [
        s.tabelle.horizontalHeaderItem(sp).text() for sp in (gs.AE, gs.VC, gs.FZ, gs.VF, gs.Q)
    ]
    h.pruefe(koepfe == ["ae\nin", "vc\nSFM", "fz\nin", "vf\nipm", "Q\nin³/min"], f"Köpfe: {koepfe}")
    zeile = [s.tabelle.item(0, sp).text() for sp in (gs.AE, gs.VC, gs.FZ, gs.N, gs.VF)]
    h.pruefe(zeile == ["0.375", "400", "0.002", "4074", "24.4"], f"Zeile in Zoll: {zeile}")
    h.bild("1_werkzeug_in_zoll", d)

    # Der Planer: vc in SFM, Spandicke in in, Vorschlag in ipm.
    s.tabelle.setCurrentCell(0, gs.EINSATZ)
    QtCore.QTimer.singleShot(0, s.knopf_planen.click)
    yield 800
    p = gui_schruppwerte.SchruppDialog.offen
    h.pruefe(p is not None, "Planer geht nicht auf")
    if p is not None:
        felder = (p.feld_vc.text(), p.feld_spandicke.text())
        h.pruefe(felder == ("400", "0.002"), f"Planer in Zoll: {felder}")
        h.pruefe("ipm" in p.ergebnis.text(), f"Vorschlag: {p.ergebnis.text()!r}")
        h.bild("2_planer_in_zoll", p)
        p.reject()
        gui_schruppwerte.SchruppDialog.offen = None
    yield 300

    # Umschalter auf mm: dasselbe Werkzeug in mm.
    d.wahl_masssystem.setCurrentIndex(d.wahl_masssystem.findData(einheiten.METRISCH))
    yield 200
    einheit = d.feld_durchmesser.parentWidget().einheit.text()
    h.pruefe(
        (d.feld_durchmesser.text(), einheit) == ("9.525", "mm"),
        f"in mm: {d.feld_durchmesser.text()!r} {einheit!r}",
    )
    kopf = s.tabelle.horizontalHeaderItem(gs.VC).text()
    h.pruefe(kopf == "vc\nm/min" and s.tabelle.item(0, gs.VC).text() == "121.92", f"vc: {kopf!r}")
    h.bild("3_umgeschaltet_mm", d)
    d.wahl_masssystem.setCurrentIndex(d.wahl_masssystem.findData(einheiten.ZOLL))
    yield 200
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 500
    gespeichert = wz.Bibliothek.laden().werkzeuge[0]
    h.pruefe(abs(gespeichert.durchmesser - 9.525) < 1e-9, "in der Datei nicht in mm")

    # Maschine verfahren: die Beispielmaschine, X in inch.
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_MaschineVerfahren"))
    yield 800
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        laden = next(k for k in meldung.buttons() if k.text() == "Beispielmaschine laden …")
        laden.click()
    # Aus der Auswahl die 3-Achs-Fräse.
    yield from h.warte_auf(lambda: gui_maschine.BeispielAuswahl.offen is not None)
    auswahl = gui_maschine.BeispielAuswahl.offen
    if auswahl is not None:
        auswahl.liste.setCurrentRow(beispielmaschine.ARTEN.index(beispielmaschine.FRAESE_3))
        auswahl.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield from h.warte_auf(lambda: gui_verfahren.VerfahrPanel.offen is not None)
    panel = gui_verfahren.VerfahrPanel.offen
    h.pruefe(panel is not None, "„Maschine verfahren“ öffnet sich nicht")
    if panel is None:
        return
    x = panel.achse("X1")
    _regler, feld = panel.zeilen[x]
    h.pruefe(
        feld.suffix() == " in" and abs(feld.maximum() - 250 / 25.4) < 1e-3,
        f"X in Zoll: {feld.suffix()!r} bis {feld.maximum()}",
    )
    feld.setValue(5)
    yield 300
    stellung = vf.gelenkstellung(x.gelenk, x.art)
    h.pruefe(abs(stellung - 127) < 1e-6, f"X 5 in steht auf {stellung} mm statt 127")
    h.bild("4_verfahren_in_zoll")
    panel.reject()
    yield 300
