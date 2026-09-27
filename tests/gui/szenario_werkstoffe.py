# Werkstoffliste als Fenster und eigene Werkstoffe (W-002): Suche und ISO-
# Filter, „Als eigenen kopieren“, „Neu…“ mit Pflichtfeld, Löschen mit
# Rückfrage (samt eigener Schnittwerte), Wahl wandert in die
# Werkzeugverwaltung, OK speichert.
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

    from camaddon import gui_werkstoffe, gui_werkzeuge
    from camaddon import werkzeuge as wz

    fraeser = wz.Werkzeug(nummer=1, durchmesser=10, schneiden=4, schneidenlaenge=22)
    wz.Bibliothek([fraeser]).speichern()
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    d.waehle_werkstoff("1.2379")
    yield 200

    # Das Fenster ist modal: aus der Ereignisschleife öffnen.
    QtCore.QTimer.singleShot(0, d.knopf_werkstoffe.click)
    yield 800
    f = gui_werkstoffe.WerkstoffDialog.offen
    h.pruefe(f is not None and f.isVisible(), "„Werkstoffe…“ geht nicht auf")
    if f is None:
        return
    h.pruefe(f.gewaehlt.kennung == "1.2379", f"gewählt: {f.gewaehlt.kennung}")
    h.pruefe(not f.knopf_bearbeiten.isEnabled(), "mitgelieferter Werkstoff bearbeitbar")
    h.bild("1_liste", f)

    # Suche und Filter.
    f.suche.setText("1.23")
    yield 200
    # 1.2311, 1.2312, 1.2343 und 1.2379 – die letzten beiden geglüht und gehärtet.
    h.pruefe(f.tabelle.rowCount() == 6, f"„1.23“: {f.tabelle.rowCount()} statt 6 Treffer")
    f.suche.clear()
    f.filter_iso.setCurrentIndex(f.filter_iso.findData("S"))
    yield 200
    h.pruefe(f.tabelle.rowCount() == 3, f"ISO S: {f.tabelle.rowCount()} statt 3")
    h.bild("2_filter_iso_s", f)
    f.filter_iso.setCurrentIndex(0)
    f.waehle("1.2379")
    yield 200

    # Als eigenen kopieren: kursiv oben, bearbeitbar.
    kopie = f.kopieren()
    yield 200
    h.pruefe(kopie.eigen and f.tabelle.currentRow() == 0, "Kopie nicht oben gewählt")
    h.pruefe(f.knopf_bearbeiten.isEnabled(), "Kopie nicht bearbeitbar")

    # Bearbeiten: Härte ändern.
    QtCore.QTimer.singleShot(0, f.bearbeiten)
    yield 500
    b = gui_werkstoffe.WerkstoffBearbeiten.offen
    h.pruefe(b is not None, "Bearbeiten geht nicht auf")
    if b is None:
        return
    h.pruefe(
        b.feld_zusammensetzung.text().startswith("C 1,45–1,60"),
        f"Zusammensetzung im Feld: {b.feld_zusammensetzung.text()!r}",
    )
    b.feld_haerte.setText("≈ 300 HB")
    b.feld_rm.setText("≈ 1000,5")
    b.feld_bekannt.setText("D2 vorvergütet")
    h.bild("3_bearbeiten", b)
    b.accept()
    yield 300
    h.pruefe(kopie.haerte == "≈ 300 HB", f"Härte nach Bearbeiten: {kopie.haerte!r}")
    h.pruefe(kopie.zugfestigkeit == "≈ 1000.5", f"gespeichert mit Punkt: {kopie.zugfestigkeit!r}")
    h.pruefe(kopie.zusammensetzung.startswith("C 1.45–1.60"), f"{kopie.zusammensetzung!r}")

    # Neu: ohne Kurzname kein OK; freie Gruppe bleibt Text.
    QtCore.QTimer.singleShot(0, f.neu)
    yield 500
    b = gui_werkstoffe.WerkstoffBearbeiten.offen
    ok = b.knoepfe.button(QtGui.QDialogButtonBox.Ok)
    h.pruefe(not ok.isEnabled() and b.hinweis.isVisible(), "OK ohne Kurzname möglich")
    b.feld_kurzname.setText("Buche")
    b.feld_gruppe.setEditText("Holz")
    b.feld_iso.setCurrentIndex(b.feld_iso.findData("N"))
    b.feld_haerte.setText("≈ 35 HB")
    b.feld_kc.setText(",")  # noch keine Zahl: OK geht trotzdem, kc bleibt unbekannt
    h.pruefe(ok.isEnabled(), "OK trotz Kurzname gesperrt")
    ok.click()
    yield 300
    holz = f.gewaehlt
    h.pruefe(gui_werkstoffe.WerkstoffBearbeiten.offen is None, "OK schließt mit „,“ nicht")
    h.pruefe(holz.kc11 == 0, f"kc nach „,“: {holz.kc11}")
    h.pruefe(holz.kurzname == "Buche" and holz.gruppe == "Holz", f"neuer Werkstoff: {holz}")

    # Eigene Schnittwerte für die Kopie, dann Kopie löschen – Rückfrage nennt sie.
    fraeser_im_dialog = d.bibliothek.werkzeuge[0]
    fraeser_im_dialog.eigene_anlegen(kopie.kennung)
    f.waehle(kopie.kennung)
    QtCore.QTimer.singleShot(0, f.loeschen)
    yield 500
    frage = h.modal()
    h.pruefe(isinstance(frage, QtGui.QMessageBox), f"keine Rückfrage beim Löschen: {frage}")
    if isinstance(frage, QtGui.QMessageBox):
        h.pruefe("Schnittwerten" in frage.text(), f"Rückfrage ohne Schnittwerte: {frage.text()!r}")
        h.bild("4_loeschen", frage)
        frage.button(QtGui.QMessageBox.Yes).click()
    yield 300
    h.pruefe(kopie not in d.bibliothek.eigene_werkstoffe, "Kopie nicht gelöscht")
    h.pruefe(not fraeser_im_dialog.hat_eigene(kopie.kennung), "Schnittwerte blieben")

    # „Buche“ wählen und schließen: Die Werkzeugverwaltung übernimmt die Wahl.
    f.waehle(holz.kennung)
    f.reject()
    yield 500
    h.pruefe(d.werkstoff == holz.kennung, f"Werkzeugverwaltung zeigt {d.werkstoff!r}")
    h.pruefe("≈ 35 HB" in d.werkstoff_info.text(), f"Info: {d.werkstoff_info.text()!r}")
    h.bild("5_eigener_in_der_verwaltung", d)
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 500
    gespeichert = wz.Bibliothek.laden()
    h.pruefe(
        [w.kurzname for w in gespeichert.eigene_werkstoffe] == ["Buche"],
        f"gespeichert: {[w.kurzname for w in gespeichert.eigene_werkstoffe]}",
    )
