# „Speichern und an CAM übergeben“ (W-002 Stufe 2): Der Knopf speichert,
# schreibt die Bibliothek „CAM-Addon“ in CAMs Werkzeugsammlung und sagt in
# einem Fenster, was übergeben wurde und wie es weitergeht.
import FreeCADGui as Gui
from PySide import QtCore, QtGui


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.German, QtCore.QLocale.Germany))

    from camaddon import gui_werkzeuge
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import werkzeuge as wz

    fraeser = wz.Werkzeug(nummer=3, durchmesser=12, schneiden=3, schneidenlaenge=26)
    fraeser.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.VOLLNUT, ae=12, ap=3, vc=120, fz=0.05)]
    fraeser.eigene_anlegen("1.4301")[0].vc = 80
    wz.Bibliothek([fraeser]).speichern()
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d.knopf_cam.isEnabled(), "„An CAM übergeben“ gesperrt")
    d.feld_bezeichnung.setText("Hoffmann 12")
    d.feld_bezeichnung.textEdited.emit("Hoffmann 12")
    h.bild("1_werkzeugverwaltung", d)

    QtCore.QTimer.singleShot(0, d.knopf_cam.click)
    yield 1500
    meldung = h.modal()
    h.pruefe(isinstance(meldung, QtGui.QMessageBox), f"keine Rückmeldung: {meldung}")
    if isinstance(meldung, QtGui.QMessageBox):
        text = meldung.text()
        h.pruefe("Übergeben: 1" in text and "CAM-Addon" in text, f"Rückmeldung: {text!r}")
        if ue.presets_moeglich():
            h.pruefe("Vorschläge dazu: 2" in text, f"Presets in der Rückmeldung: {text!r}")
        else:
            h.pruefe("noch nicht an den Werkzeugen" in text, f"1.1.3-Hinweis: {text!r}")
        h.bild("2_rueckmeldung", meldung)
        meldung.accept()
    yield 300

    # Gespeichert und in CAM angekommen.
    h.pruefe(wz.Bibliothek.laden().werkzeuge[0].bezeichnung == "Hoffmann 12", "nicht gespeichert")
    from Path.Tool.camassets import cam_assets

    bibliothek = cam_assets.get("toolbitlibrary://camaddon")
    h.pruefe(
        sorted(bibliothek._bit_nos) == [3], f"Bibliothek in CAM: {sorted(bibliothek._bit_nos)}"
    )
    d.reject()
