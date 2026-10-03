# „Aus CAM übernehmen“ (W-002): Werkzeuge aus FreeCADs Bibliothek „Default“
# in die Werkzeugverwaltung – Menü der Bibliotheken, Rückmeldung, Liste,
# gespeichert mit OK. Seit Stufe 5 der Werkzeugarten kommen alle 13: auch
# Gravierstichel (als Fasenfräser), Säge, Taster und Gewindefräser – mit
# ihren Maßen und ihrem Bild.
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
        for teil in ("Übernommen: 12 Werkzeuge.", "3.175mm Endmill", "5mm Endmill"):
            h.pruefe(teil in text, f"„{teil}“ fehlt: {text!r}")
        h.pruefe("kennt die Werkzeugverwaltung nicht" not in text, f"Formen fehlen: {text!r}")
        h.bild("1_meldung", meldung)
        meldung.accept()
    else:
        h.pruefe(False, f"keine Rückmeldung: {meldung}")
    yield 300
    h.pruefe(
        len(d.liste.eintraege()) == 13,
        f"{len(d.liste.eintraege())} Werkzeuge in der Liste statt 13",
    )
    h.pruefe(d.geaendert, "Übernommenes gilt nicht als Änderung")
    h.bild("2_liste", d)

    # Neu übernehmbar: Gewindefräser, Gravierstichel, Säge – mit Maßen und Bild.
    for name, art, bild in (
        ("5mm-thread-cutter", wz.GEWINDEFRAESER, "3_gewindefraeser"),
        ("30 Deg. V-Bit", wz.FASENFRAESER, "4_gravierstichel"),
        ("Slitting Saw", wz.NUTENFRAESER, "5_saege"),
    ):
        zeile = next(
            (i for i in range(len(d.liste.eintraege())) if name in d.liste.eintraege()[i].text(0)),
            None,
        )
        h.pruefe(zeile is not None, f"{name} fehlt in der Liste")
        if zeile is None:
            continue
        d.liste.setCurrentItem(d.liste.eintraege()[zeile])
        yield 300
        h.pruefe(d.werkzeug.art == art, f"{name}: {d.werkzeug.art}")
        h.bild(bild, d)
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 500
    gespeichert = wz.Bibliothek.laden().werkzeuge
    h.pruefe(len(gespeichert) == 13, f"{len(gespeichert)} gespeichert statt 13")

    # Wieder öffnen, alle Werkzeuge ansehen, Abbrechen: keine Rückfrage –
    # angesehen ist nicht geändert.
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    for zeile in range(len(d.liste.eintraege())):
        d.liste.setCurrentItem(d.liste.eintraege()[zeile])
        yield 50
    h.pruefe(not d.geaendert, "Ansehen gilt als Änderung")
    QtCore.QTimer.singleShot(0, d.reject)  # eine Rückfrage blockierte sonst
    yield 500
    frage = h.modal()
    h.pruefe(frage is None, f"Rückfrage, obwohl nichts geändert ist: {frage}")
    if frage is not None:
        frage.done(0)
