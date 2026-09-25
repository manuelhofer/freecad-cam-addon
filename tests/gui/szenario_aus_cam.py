# „Aus CAM übernehmen“ (W-002): Werkzeuge aus FreeCADs Bibliothek „Default“
# in die Werkzeugverwaltung – Menü der Bibliotheken, Rückmeldung, Liste,
# gespeichert mit OK.
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

    # T1 gibt es schon – derselbe Fräser wie T1 in „Default“.
    wz.Bibliothek([wz.Werkzeug(nummer=1, durchmesser=3.175, schneiden=4)]).speichern()
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d is not None and d.knopf_aus_cam.isEnabled(), "„Aus CAM übernehmen“ nicht bedienbar")
    if d is None:
        return
    d._menue_aus_cam_fuellen()
    eintraege = {a.text(): a for a in d.menue_aus_cam.actions()}
    h.pruefe("Default (13 Werkzeuge)" in eintraege, f"Menü: {sorted(eintraege)}")
    if "Default (13 Werkzeuge)" not in eintraege:
        return
    eintraege["Default (13 Werkzeuge)"].trigger()
    yield 800
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        text = meldung.text()
        for teil in ("Übernommen: 5 Werkzeuge.", "3.175mm Endmill", "30 Deg. V-Bit"):
            h.pruefe(teil in text, f"„{teil}“ fehlt: {text!r}")
        h.bild("1_meldung", meldung)
        meldung.accept()
    else:
        h.pruefe(False, f"keine Rückmeldung: {meldung}")
    yield 300
    h.pruefe(d.liste.count() == 6, f"{d.liste.count()} Werkzeuge in der Liste statt 6")
    h.pruefe(d.geaendert, "Übernommenes gilt nicht als Änderung")
    h.bild("2_liste", d)
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 500
    gespeichert = wz.Bibliothek.laden().werkzeuge
    h.pruefe(len(gespeichert) == 6, f"{len(gespeichert)} gespeichert statt 6")
