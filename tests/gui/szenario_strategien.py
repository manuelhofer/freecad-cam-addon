# Strategien vergleichen (W-002): Vollnut gegen dynamisches Schruppen am
# Ø-12-Fräser in C45 – Balken, Werte, Urteil mit 2,5-fachem Abtrag und
# 12-mal weniger Schneidenweg, Leistung aus kc1.1.
import FreeCADGui as Gui
from PySide import QtCore


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.German, QtCore.QLocale.Germany))

    from camaddon import gui_strategie, gui_werkzeuge
    from camaddon import werkzeuge as wz

    fraeser = wz.Werkzeug(nummer=3, durchmesser=12, schneiden=3, schneidenlaenge=26)
    fraeser.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.VOLLNUT, ae=12, ap=3, vc=120, fz=0.05),
        wz.Einsatz(art=wz.SCHLICHTEN, ae=0.2, ap=25, vc=150, fz=0.06),
        wz.Einsatz(art=wz.DYNAMISCH, ae=1.2, ap=25, vc=120, fz=0.15),
    ]
    wz.Bibliothek([fraeser]).speichern()
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    d.waehle_werkstoff("1.0503")
    yield 200
    s = d.schnittwerte
    h.pruefe(s.knopf_vergleich.isEnabled(), "„Strategien vergleichen“ nicht bedienbar")

    # Der Vergleich ist modal: aus der Ereignisschleife öffnen, dann prüfen.
    QtCore.QTimer.singleShot(0, s.knopf_vergleich.click)
    yield 800
    v = gui_strategie.StrategieDialog.offen
    h.pruefe(v is not None and v.isVisible(), "Vergleich geht nicht auf")
    if v is None:
        return
    h.pruefe(
        (v.wahl_a.currentText(), v.wahl_b.currentText()) == ("Vollnut", "Schruppen dynamisch"),
        f"Vorwahl {v.wahl_a.currentText()!r} gegen {v.wahl_b.currentText()!r}",
    )
    urteil = v.urteil.text()
    for teil in (
        "2,5-mal so viel",
        "12,2-mal weniger Weg",
        "25 mm statt 3 mm",
        "10 % statt 50 %",
        "kW",
    ):
        h.pruefe(teil in urteil, f"„{teil}“ fehlt im Urteil: {urteil!r}")
    _, wert_a, _, wert_b = v._zeilen["q"]
    h.pruefe((wert_a.text(), wert_b.text()) == ("17,2 cm³/min", "43,0 cm³/min"), "Q-Werte")
    _, wert_a, _, wert_b = v._zeilen["weg"]
    h.pruefe((wert_a.text(), wert_b.text()) == ("3,49 m", "0,29 m"), "Schneidenweg")
    kopf = v.kopf.text()
    h.pruefe("1.0503  C45" in kopf, f"Werkstoffnummer im Kopf verändert: {kopf!r}")
    # Übersicht: drei Zeilen, das meiste Q hat „Schruppen dynamisch“ (fett).
    u = v.uebersicht
    h.pruefe(u.rowCount() == 3, f"Übersicht: {u.rowCount()} Zeilen")
    fett = [u.item(z, gui_strategie.UE_Q).font().bold() for z in range(u.rowCount())]
    h.pruefe(fett == [False, False, True], f"fett in Q: {fett}")
    h.pruefe(u.item(2, gui_strategie.UE_Q).text() == "43,0", f"Q: {u.item(2, 2).text()!r}")
    h.bild("1_vollnut_gegen_dynamisch", v)

    # Klick in der Übersicht nimmt die Zeile als B.
    v.als_b(1)
    yield 100
    h.pruefe(v.wahl_b.currentText() == "Schlichten", f"B: {v.wahl_b.currentText()!r}")
    # Schlichten gegen Vollnut: anderes Urteil, ohne Absturz.
    v.vergleiche(1, 0)
    yield 200
    h.pruefe("Vollnut" in v.urteil.text(), f"Urteil Schlichten/Vollnut: {v.urteil.text()!r}")
    h.bild("2_schlichten_gegen_vollnut", v)
    v.reject()
    yield 300
    d.reject()
