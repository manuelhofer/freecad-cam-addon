# Durchmesser ändern (W-002): Ein Ø-12-Fräser mit Einsätzen wird kopiert und
# auf Ø 10 gesetzt – die Werkzeugverwaltung fragt, ob ae und ap umgerechnet
# werden. „Ja“ rechnet sie mal 10/12 um (alle Werkstoffe), vc und fz bleiben;
# „Nein“ ändert nur den Durchmesser.
import FreeCADGui as Gui
from PySide import QtCore, QtGui


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

    fraeser = wz.Werkzeug(nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26)
    fraeser.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.VOLLNUT, ae=12, ap=6, vc=120, fz=0.05),
        wz.Einsatz(art=wz.DYNAMISCH, ae=1.2, ap=24, vc=120, fz=0.15),
    ]
    fraeser.eigene_anlegen("1.4301")[0].vc = 80
    wz.Bibliothek([fraeser]).speichern()
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    kopie = d.werkzeug_kopieren()
    yield 200

    def durchmesser(text):
        d.feld_durchmesser.setText(text)
        d.feld_durchmesser.editingFinished.emit()

    # Die Frage ist modal – aus der Ereignisschleife auslösen, dann beantworten.
    QtCore.QTimer.singleShot(0, lambda: durchmesser("10"))
    yield 500
    frage = h.modal()
    h.pruefe(isinstance(frage, QtGui.QMessageBox), f"keine Frage beim Umrechnen: {frage}")
    if not isinstance(frage, QtGui.QMessageBox):
        return
    h.pruefe("von 12 auf 10 mm" in frage.text(), f"Frage: {frage.text()!r}")
    h.bild("1_frage", frage)
    frage.button(QtGui.QMessageBox.Yes).click()
    yield 300
    alle = kopie.einsaetze(wz.ALLE)
    werte = [(e.ae, e.ap, e.vc, e.fz) for e in alle]
    h.pruefe(werte == [(10, 5, 120, 0.05), (1, 20, 120, 0.15)], f"umgerechnet: {werte}")
    eigene = kopie.einsaetze("1.4301")[0]
    h.pruefe((eigene.ae, eigene.vc) == (10, 80), f"1.4301: {eigene}")
    h.pruefe(fraeser.einsaetze(wz.ALLE)[0].ae == 12, "Original verändert")
    h.bild("2_umgerechnet", d)

    # „Nein“: nur der Durchmesser.
    QtCore.QTimer.singleShot(0, lambda: durchmesser("8"))
    yield 500
    frage = h.modal()
    if isinstance(frage, QtGui.QMessageBox):
        frage.button(QtGui.QMessageBox.No).click()
    yield 300
    h.pruefe(kopie.durchmesser == 8 and alle[0].ae == 10, f"nach „Nein“: {kopie.durchmesser}")

    QtCore.QTimer.singleShot(0, d.reject)
    yield 500
    rueckfrage = h.modal()
    if isinstance(rueckfrage, QtGui.QMessageBox):
        rueckfrage.button(QtGui.QMessageBox.Discard).click()
    yield 300
