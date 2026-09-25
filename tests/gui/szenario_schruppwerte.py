# Schruppwerte planen (W-002 Stufe 3): Ø-12-Fräser in C45, Ausgang Vollnut
# (h 0,05). Vorschlag an der Grenze 10 % von D, dann an der Leistungsgrenze
# der Spindel, Vorschub und Drehzahl der Maschine am Anschlag; „Als Einsatz
# übernehmen“ legt eigene Werte für C45 mit der neuen Zeile an.
import FreeCAD
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

    from camaddon import PARAMETER_PFAD, gui_schruppwerte, gui_werkzeuge
    from camaddon import schruppwerte as sw
    from camaddon import werkzeuge as wz

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
    h.pruefe(p.knopf_maschine.isHidden(), "„Von der Maschine“ ohne Maschine sichtbar")
    h.pruefe(not p.tabelle.isColumnHidden(gui_schruppwerte.LEISTUNG), "Leistung fehlt trotz kc1.1")
    zeile = p.tabelle.currentRow()
    h.pruefe(p.tabelle.item(zeile, gui_schruppwerte.AE).text() == "1,20", "Vorschlag nicht 1,2")
    text = p.ergebnis.text()
    for teil in ("22,9 cm³/min", "fz 0,083 mm", "Grenze von 10 % von D"):
        h.pruefe(teil in text, f"„{teil}“ fehlt: {text!r}")
    h.pruefe("3183 U/min" in p.drehzahl_text.text(), p.drehzahl_text.text())
    h.bild("1_vorschlag", p)

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
    parameter = FreeCAD.ParamGet(PARAMETER_PFAD)
    h.pruefe(parameter.GetFloat("PlanerAeGrenze", -1) == 10, "ae-Grenze nicht gemerkt")
    h.bild("4_uebernommen", d)

    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 500
    gespeichert = wz.Bibliothek.laden().werkzeuge[0].einsaetze("1.0503")
    h.pruefe(
        [e.art for e in gespeichert] == [wz.VOLLNUT, wz.SCHLICHTEN, wz.DYNAMISCH],
        f"gespeichert: {[e.art for e in gespeichert]}",
    )
    h.pruefe(sw.AE_GRENZE == 10, "Vorgabe der ae-Grenze geändert – Szenario anpassen")
