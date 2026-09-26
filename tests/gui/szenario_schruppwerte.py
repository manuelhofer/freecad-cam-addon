# Schruppwerte planen (W-002 Stufe 3): Ø-12-Fräser in C45, Ausgang Vollnut
# (h 0,05). Vorschlag an der Grenze 10 % von D, dann an der Leistungsgrenze
# der Spindel, Vorschub und Drehzahl der Maschine am Anschlag; „Als Einsatz
# übernehmen“ legt eigene Werte für C45 mit der neuen Zeile an.
import FreeCADGui as Gui
from PySide import QtCore, QtGui
from PySide6 import QtTest


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.German, QtCore.QLocale.Germany))

    from camaddon import gui_schruppwerte, gui_werkzeuge
    from camaddon import schruppwerte as sw
    from camaddon import werkzeuge as wz
    from camaddon.gui_teile import GRAU, ROT

    fraeser = wz.Werkzeug(nummer=3, durchmesser=12, schneiden=3, schneidenlaenge=26)
    fraeser.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.VOLLNUT, ae=12, ap=3, vc=120, fz=0.05),
        wz.Einsatz(art=wz.SCHLICHTEN, ae=0.2, ap=25, vc=150, fz=0.06),
    ]
    wz.Bibliothek([fraeser]).speichern()
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    d.waehle_werkstoff("1.0503")
    yield 200
    s = d.schnittwerte
    h.pruefe(s.knopf_planen.isEnabled(), "„Schruppwerte planen“ nicht bedienbar")
    # Gewählt ist die Schlicht-Zeile – der Planer nimmt trotzdem die Vollnut.
    s.tabelle.setCurrentCell(1, 0)

    QtCore.QTimer.singleShot(0, s.knopf_planen.click)
    yield 800
    p = gui_schruppwerte.SchruppDialog.offen
    h.pruefe(p is not None and p.isVisible(), "Planer geht nicht auf")
    if p is None:
        return
    felder = tuple(f.text() for f in (p.feld_vc, p.feld_spandicke, p.feld_ap, p.feld_ae_grenze))
    h.pruefe(felder == ("120", "0,05", "24", "10"), f"vorbelegt: {felder}")
    h.pruefe(not p.beispiel_hinweis.isVisible(), "Beispiel-Hinweis trotz Werten der Zeile")
    h.pruefe(p.knopf_maschine.isHidden(), "„Von der Maschine“ ohne Maschine sichtbar")
    h.pruefe(not p.tabelle.isColumnHidden(gui_schruppwerte.LEISTUNG), "Leistung fehlt trotz kc1.1")
    zeile = p.tabelle.currentRow()
    h.pruefe(p.tabelle.item(zeile, gui_schruppwerte.AE).text() == "1,20", "Vorschlag nicht 1,2")
    text = p.ergebnis.text()
    for teil in (
        "22,9 cm³/min",
        "fz 0,083 mm",
        "Warngrenze von 10 % von D",
        "Vollnut (ae 12 mm, ap 3 mm) schafft 17,2 cm³/min",
        "das 1,3-Fache, mit 24 statt 3 mm Schneide",
    ):
        h.pruefe(teil in text, f"„{teil}“ fehlt: {text!r}")
    h.pruefe("3183 U/min" in p.drehzahl_text.text(), p.drehzahl_text.text())
    h.pruefe(not p.warnung.isVisible(), "Warnung beim Vorschlag")
    h.bild("1_vorschlag", p)
    # Über der Warngrenze: rot, aber wählbar – dann steht die Warnung unter der Tabelle.
    breiter = zeile + 1
    zelle = p.tabelle.item(breiter, gui_schruppwerte.AE)
    hinweis = p.tabelle.item(breiter, gui_schruppwerte.HINWEIS).text()
    h.pruefe(
        zelle.text() == "1,44" and zelle.foreground().color().name() == ROT,
        f"Zeile über der Warngrenze: {zelle.text()!r} {zelle.foreground().color().name()}",
    )
    h.pruefe(hinweis == "mehr als deine Warngrenze (10 % von D)", f"Hinweis: {hinweis!r}")
    p.tabelle.setCurrentCell(breiter, gui_schruppwerte.AE)
    yield 100
    h.pruefe(
        p.warnung.isVisible() and "mehr als deine Warngrenze" in p.warnung.text(),
        f"Warnung: {p.warnung.text()!r}",
    )
    h.pruefe(p.knopf_uebernehmen.isEnabled(), "Zeile über der Warngrenze nicht wählbar")
    h.bild("1b_ueber_warngrenze", p)
    p.tabelle.setCurrentCell(zeile, gui_schruppwerte.AE)
    yield 100
    h.pruefe(not p.warnung.isVisible(), "Warnung bleibt beim Vorschlag")

    # Spindel mit 1,5 kW: Grenze zwischen 6 % und 8 %, genau gesucht.
    p.setze("leistung", "1,5")
    yield 200
    zeile = p.tabelle.currentRow()
    hinweis = p.tabelle.item(zeile, gui_schruppwerte.HINWEIS).text()
    h.pruefe("Spindel voll ausgelastet" in hinweis, f"Hinweis: {hinweis!r}")
    h.pruefe("Spindelleistung nicht" in p.ergebnis.text(), p.ergebnis.text())
    h.bild("2_leistungsgrenze", p)

    # Maschine mit 1000 mm/min und 3000 U/min: Vorschub am Anschlag, vc sinkt.
    p.setze("leistung", "")
    p.setze("vorschub", "1000")
    p.setze("drehzahl", "3000")
    yield 200
    angeschlagen = [
        z
        for z in range(p.tabelle.rowCount())
        if "Vorschub am Anschlag" in p.tabelle.item(z, gui_schruppwerte.HINWEIS).text()
    ]
    h.pruefe(angeschlagen == [0, 1, 2, 3], f"Vorschub am Anschlag in Zeilen {angeschlagen}")
    h.pruefe("113 m/min" in p.drehzahl_text.text(), p.drehzahl_text.text())
    h.bild("3_maschine", p)

    # Ohne Maschinengrenzen übernehmen: eigene Werte für C45 mit der neuen Zeile.
    p.setze("vorschub", "")
    p.setze("drehzahl", "")
    yield 100
    h.pruefe(
        p.knopf_uebernehmen.text() == "Als Einsatz für 1.0503 übernehmen",
        f"Knopf: {p.knopf_uebernehmen.text()!r}",
    )
    p.knopf_uebernehmen.click()
    yield 500
    h.pruefe(gui_schruppwerte.SchruppDialog.offen is None, "Planer nicht geschlossen")
    werkzeug = s.werkzeug
    h.pruefe(werkzeug.hat_eigene("1.0503"), "keine eigenen Werte für C45 angelegt")
    neu = werkzeug.einsaetze("1.0503")[-1]
    h.pruefe(
        (neu.art, neu.ae, neu.ap, neu.vc, neu.fz) == (wz.DYNAMISCH, 1.2, 24, 120, 0.083),
        f"neuer Einsatz: {neu}",
    )
    h.pruefe(len(werkzeug.einsaetze(wz.ALLE)) == 2, "Werte für alle Werkstoffe verändert")
    h.pruefe(s.tabelle.currentRow() == 2, f"neue Zeile nicht gewählt: {s.tabelle.currentRow()}")
    h.pruefe(werkzeug.ae_warngrenze == 10, f"Warngrenze am Werkzeug: {werkzeug.ae_warngrenze}")
    h.bild("4_uebernommen", d)

    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 500
    gespeichert = wz.Bibliothek.laden().werkzeuge[0].einsaetze("1.0503")
    h.pruefe(
        [e.art for e in gespeichert] == [wz.VOLLNUT, wz.SCHLICHTEN, wz.DYNAMISCH],
        f"gespeichert: {[e.art for e in gespeichert]}",
    )
    h.pruefe(sw.AE_GRENZE == 10, "Vorgabe der ae-Grenze geändert – Szenario anpassen")

    # Ohne vc und fz in der Zeile: graue Beispiele für den Schneidstoff, gerechnet wird schon.
    hss = wz.Werkzeug(nummer=4, durchmesser=10, schneiden=4, schneidenlaenge=22)
    hss.schneidstoff = wz.HSS
    p = gui_schruppwerte.SchruppDialog(None, hss, None, None, "1.0503", "Übernehmen")
    p.show()
    yield 300
    grau = GRAU.name()
    felder = (p.feld_vc.text(), p.feld_spandicke.text())
    h.pruefe(felder == ("30", "0,03"), f"Beispiele HSS: {felder}")
    h.pruefe(
        grau in p.feld_vc.styleSheet()
        and grau in p.feld_spandicke.styleSheet()
        and p.beispiel_hinweis.isVisible(),
        "Beispiele nicht grau",
    )
    h.pruefe(p.tabelle.rowCount() > 0, "mit den Beispielen kein Plan")
    h.bild("5_beispielwerte", p)
    p.feld_vc.setFocus()
    p.feld_vc.selectAll()
    QtTest.QTest.keyClicks(p.feld_vc, "35")
    yield 100
    h.pruefe(p.feld_vc.text() == "35" and p.feld_vc.styleSheet() == "", "eigenes vc noch grau")
    h.pruefe(grau in p.feld_spandicke.styleSheet(), "Spandicke nicht mehr grau")
    # Die Warngrenze gehört zum Werkzeug – auch nach Abbrechen.
    p.setze("ae_grenze", "8")
    yield 100
    p.reject()
    gui_schruppwerte.SchruppDialog.offen = None
    h.pruefe(hss.ae_warngrenze == 8, f"Warngrenze nicht am Werkzeug: {hss.ae_warngrenze}")
