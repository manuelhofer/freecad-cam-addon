# Schnittwerte in der Werkzeugverwaltung (W-002): Einsätze für alle Werkstoffe
# anlegen, n/vf/Q werden gerechnet; ein Werkstoff ohne eigene Werte zeigt sie
# grau; „Eigene Werte anlegen“ macht eine unabhängige Kopie; Bohrer mit f je
# Umdrehung; OK speichert alles.
import os
import sys

import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui
from PySide6 import QtTest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def zelle(d, zeile, spalte):
    return d.schnittwerte.tabelle.item(zeile, spalte).text()


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.German, QtCore.QLocale.Germany))

    from camaddon import PARAMETER_PFAD, gui_werkzeuge
    from camaddon import gui_schnittwerte as gs
    from camaddon import werkzeuge as wz

    # Ein Fräser liegt schon in der Bibliothek.
    wz.Bibliothek(
        [wz.Werkzeug(nummer=3, durchmesser=12, schneiden=3, schneidenlaenge=26)]
    ).speichern()
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    d.waehle_werkstoff(wz.ALLE)
    yield 200
    s = d.schnittwerte
    h.pruefe(s.isVisible() and s.tabelle.rowCount() == 0, "Schnittwerte fehlen oder nicht leer")

    # Vollnut: ae und ap vorbelegt; ap 3, vc 120, fz 0,05 → n 3183, vf 477, Q 17,2.
    vollnut = s.einsatz_anlegen(wz.VOLLNUT)
    yield 100
    h.pruefe((vollnut.ae, vollnut.ap) == (12, 6), f"Vorlage Vollnut {vollnut}")
    h.pruefe("vc und fz fehlen" in s.hinweis.text(), f"Hinweis vc/fz: {s.hinweis.text()!r}")
    s.setze(0, gs.AP, "3")
    s.setze(0, gs.VC, "120")
    # fz wie ein Benutzer: Zelle öffnen, „0,05“ tippen, Enter.
    s.tabelle.setCurrentCell(0, gs.FZ)
    s.tabelle.editItem(s.tabelle.item(0, gs.FZ))
    yield 200
    # Der Editor ist ein Feld im Innern der Tabelle; unter Xvfb hat kein Fenster den Fokus.
    feld = next(f for f in s.tabelle.findChildren(QtGui.QLineEdit) if f.isVisible())
    QtTest.QTest.keyClicks(feld, "0,05")
    QtTest.QTest.keyClick(feld, QtCore.Qt.Key_Return)
    yield 200
    h.pruefe(d.isVisible(), "Enter in der Tabelle hat den Dialog geschlossen")
    h.pruefe(vollnut.fz == 0.05, f"getipptes fz ergibt {vollnut.fz}")
    h.pruefe(
        (zelle(d, 0, gs.N), zelle(d, 0, gs.VF), zelle(d, 0, gs.Q)) == ("3183", "477", "17,2"),
        f"gerechnet: {zelle(d, 0, gs.N)}, {zelle(d, 0, gs.VF)}, {zelle(d, 0, gs.Q)}",
    )

    # Dynamisch schruppen: schmal und tief.
    s.einsatz_anlegen(wz.DYNAMISCH)
    yield 100
    h.pruefe(zelle(d, 1, gs.AE) == "1,2", f"Vorlage ae {zelle(d, 1, gs.AE)!r}")
    for spalte, text in ((gs.AP, "30"), (gs.VC, "120"), (gs.FZ, "0,15")):
        s.setze(1, spalte, text)
    yield 100
    h.pruefe("länger als die Schneide" in s.hinweis.text(), f"ap > Schneide: {s.hinweis.text()!r}")
    s.setze(1, gs.AP, "25")
    yield 100
    h.pruefe(zelle(d, 1, gs.Q) == "43,0", f"Q dynamisch {zelle(d, 1, gs.Q)!r}")
    h.pruefe(not s.hinweis.isVisible(), f"Hinweis trotz passender Werte: {s.hinweis.text()!r}")
    h.bild("1_alle_werkstoffe", d)

    # Eingriff der gewählten Zeile (dynamisch): Bild, Winkel, Spandicke.
    text = s.eingriff_text.text()
    h.pruefe(s.eingriff.isVisible() and s.bild.isVisible(), "Bild des Eingriffs fehlt")
    for teil in ("Eingriff 37°", "10 % von D", "2,1 × D", "96 % der Schneide", "0,090"):
        h.pruefe(teil in text, f"„{teil}“ fehlt im Eingriff: {text!r}")
    # Je Größe eine Zeile, über dem Bild, was die Hälften zeigen.
    zeilen = text.split("\n")
    h.pruefe(
        zeilen[0].startswith("ae 1,2 mm") and zeilen[1].startswith("ap 25 mm"),
        f"Zeilen: {zeilen}",
    )
    titel = [t.text() for t in s.bild_titel]
    h.pruefe(
        "seitliche Zustellung" in titel[0]
        and "von oben" in titel[0]
        and "Zustelltiefe" in titel[1]
        and "von der Seite" in titel[1],
        f"Überschriften: {titel}",
    )
    h.pruefe(s.ausgleich.isVisible(), "Spandicke ausgleichen fehlt bei ae < D/2")
    h.bild("1b_eingriff_dynamisch", s.eingriff)

    # ae und ap in % von D: umschalten, tippen, zurück – gespeichert wird in mm.
    s.wahl_einheit.setCurrentIndex(s.wahl_einheit.findData(True))
    yield 100
    kopf = s.tabelle.horizontalHeaderItem(gs.AE).text()
    h.pruefe(
        (kopf, zelle(d, 1, gs.AE), zelle(d, 1, gs.AP)) == ("ae\n% D", "10", "208,3"),
        f"in % von D: {kopf!r}, {zelle(d, 1, gs.AE)!r}, {zelle(d, 1, gs.AP)!r}",
    )
    s.setze(1, gs.AE, "20")
    yield 100
    dynamisch = s.werkzeug.einsaetze(wz.ALLE)[1]
    h.pruefe(abs(dynamisch.ae - 2.4) < 1e-9, f"20 % von D ergibt ae {dynamisch.ae}")
    h.pruefe(FreeCAD.ParamGet(PARAMETER_PFAD).GetBool(gs.IN_PROZENT), "Wahl % nicht gemerkt")
    h.bild("1c_in_prozent", d)
    s.setze(1, gs.AE, "10")
    s.wahl_einheit.setCurrentIndex(s.wahl_einheit.findData(False))
    yield 100
    h.pruefe(
        zelle(d, 1, gs.AE) == "1,2" and abs(dynamisch.ae - 1.2) < 1e-9,
        f"zurück in mm: {zelle(d, 1, gs.AE)!r}, ae {dynamisch.ae}",
    )
    h.pruefe(not FreeCAD.ParamGet(PARAMETER_PFAD).GetBool(gs.IN_PROZENT), "Wahl mm nicht gemerkt")
    # Gewünscht 0,1 mm → fz 0,167; übernehmen rechnet die Zeile neu.
    s.feld_spandicke.setText("0,1")
    yield 100
    h.pruefe("0,167" in s.ausgleich_ergebnis.text(), f"Ausgleich: {s.ausgleich_ergebnis.text()!r}")
    s.knopf_ausgleich.click()
    yield 100
    h.pruefe(abs(s.gewaehlt.fz - 0.1667) < 1e-4, f"fz nach Ausgleich {s.gewaehlt.fz}")
    h.pruefe(zelle(d, 1, gs.FZ) == "0,1667", f"fz in der Zelle {zelle(d, 1, gs.FZ)!r}")
    s.setze(1, gs.FZ, "0,15")
    # Vollnut: 180°, kein Ausgleich.
    s.tabelle.setCurrentCell(0, gs.EINSATZ)
    yield 100
    h.pruefe("Eingriff 180°" in s.eingriff_text.text(), f"Vollnut: {s.eingriff_text.text()!r}")
    h.pruefe(not s.ausgleich.isVisible(), "Ausgleich bei Vollnut sichtbar")
    h.bild("1c_eingriff_vollnut", s.eingriff)
    s.tabelle.setCurrentCell(1, gs.EINSATZ)
    yield 100
    h.bild("1d_dialog_mit_eingriff", d)

    # Gewählte Zeile kopieren: direkt darunter, mit Nummer im Namen, gleiche
    # Werte; die Kopie ändern lässt das Original, wie es ist.
    s.tabelle.setCurrentCell(0, gs.EINSATZ)
    h.pruefe(s.aktion_kopieren.isEnabled(), "„Gewählte Zeile kopieren“ nicht bedienbar")
    s.aktion_kopieren.trigger()
    yield 100
    h.pruefe(
        s.tabelle.rowCount() == 3 and s.tabelle.currentRow() == 1,
        f"Kopie: {s.tabelle.rowCount()} Zeilen, gewählt {s.tabelle.currentRow()}",
    )
    h.pruefe(zelle(d, 1, gs.EINSATZ) == "Vollnut 2", f"Name der Kopie {zelle(d, 1, gs.EINSATZ)!r}")
    h.pruefe(zelle(d, 1, gs.Q) == "17,2", f"Q der Kopie {zelle(d, 1, gs.Q)!r}")
    s.setze(1, gs.AP, "6")
    yield 100
    h.pruefe(
        (zelle(d, 0, gs.AP), zelle(d, 1, gs.Q)) == ("3", "34,4"),
        f"Original ap {zelle(d, 0, gs.AP)!r}, Kopie Q {zelle(d, 1, gs.Q)!r}",
    )
    h.bild("1e_kopie", d)
    s.einsatz_entfernen()
    yield 100
    namen = [zelle(d, z, gs.EINSATZ) for z in range(s.tabelle.rowCount())]
    h.pruefe(namen == ["Vollnut", "Schruppen dynamisch"], f"nach dem Löschen: {namen}")
    # Auch „+ Einsatz“ und der Planer (einsatz_hinzufuegen) nummerieren doppelte Namen.
    s.einsatz_anlegen(wz.DYNAMISCH)
    s.einsatz_hinzufuegen(wz.Einsatz(art=wz.DYNAMISCH, ae=1.8, ap=25, vc=120, fz=0.13))
    yield 100
    namen = [zelle(d, z, gs.EINSATZ) for z in range(s.tabelle.rowCount())]
    h.pruefe(
        namen[2:] == ["Schruppen dynamisch 2", "Schruppen dynamisch 3"], f"doppelte Namen: {namen}"
    )
    for _ in range(2):
        s.tabelle.setCurrentCell(2, gs.EINSATZ)
        s.einsatz_entfernen()
    yield 100
    h.pruefe(s.tabelle.rowCount() == 2, f"{s.tabelle.rowCount()} Zeilen nach dem Aufräumen")

    # 1.4301 ohne eigene Werte: grau, nicht bearbeitbar.
    d.waehle_werkstoff("1.4301")
    yield 200
    h.pruefe("gelten die Werte für alle" in s.zustand.text(), f"Zustand: {s.zustand.text()!r}")
    h.pruefe(
        not (s.tabelle.item(0, gs.VC).flags() & QtCore.Qt.ItemIsEditable), "geerbte Werte änderbar"
    )
    h.pruefe(s.knopf_eigene.isVisible() and "1.4301" in s.knopf_eigene.text(), "Knopf „anlegen“")
    h.bild("2_geerbt", d)

    # Eigene Werte: Kopie, unabhängig von „für alle“.
    s.knopf_eigene.click()
    yield 200
    h.pruefe(s.zustand.text() == "Eigene Werte für 1.4301.", f"Zustand: {s.zustand.text()!r}")
    s.setze(0, gs.VC, "80")
    yield 100
    h.pruefe(zelle(d, 0, gs.N) == "2122", f"n bei vc 80: {zelle(d, 0, gs.N)!r}")
    h.bild("3_eigene_werte", d)
    d.waehle_werkstoff("1.0503")
    yield 200
    h.pruefe(zelle(d, 0, gs.VC) == "120", f"C45 zeigt vc {zelle(d, 0, gs.VC)!r} statt 120")
    d.waehle_werkstoff("1.4301")
    yield 200
    h.pruefe(zelle(d, 0, gs.VC) == "80", f"1.4301 zeigt vc {zelle(d, 0, gs.VC)!r} statt 80")

    # Bohrer: f je Umdrehung, ohne ae und ap.
    bohrer = d.werkzeug_anlegen()
    d.feld_art.setCurrentIndex(d.feld_art.findData(wz.BOHRER))
    d.feld_durchmesser.setText("8,5")
    d.feld_durchmesser.editingFinished.emit()
    d.feld_schneiden.setValue(2)
    # Statt des Eintauchwinkels der Spitzenwinkel: leer „üblich: 118“.
    h.pruefe(
        d.zeile_spitzenwinkel.isVisible() and not d.zeile_eintauchwinkel.isVisible(),
        "beim Bohrer nicht Spitzenwinkel statt Eintauchwinkel",
    )
    grau = d.feld_spitzenwinkel.placeholderText()
    h.pruefe(grau == "üblich: 118", f"Spitzenwinkel leer: {grau!r}")
    d.feld_spitzenwinkel.setText("130")
    d.feld_spitzenwinkel.editingFinished.emit()
    h.pruefe(bohrer.spitzenwinkel == 130, f"Spitzenwinkel {bohrer.spitzenwinkel}")
    d.waehle_werkstoff(wz.ALLE)
    yield 200
    s.einsatz_anlegen(wz.BOHREN)
    s.setze(0, gs.VC, "80")
    s.setze(0, gs.FZ, "0,2")
    yield 100
    h.pruefe(
        s.tabelle.isColumnHidden(gs.AE) and s.tabelle.isColumnHidden(gs.AP), "ae/ap beim Bohrer"
    )
    h.pruefe(abs(bohrer.einsaetze(wz.ALLE)[0].fz - 0.1) < 1e-9, "f 0,2 bei z 2 ergibt nicht fz 0,1")
    h.pruefe(
        (zelle(d, 0, gs.N), zelle(d, 0, gs.VF), zelle(d, 0, gs.Q)) == ("2996", "599", "34,0"),
        f"Bohrer: {zelle(d, 0, gs.N)}, {zelle(d, 0, gs.VF)}, {zelle(d, 0, gs.Q)}",
    )
    h.bild("4_bohrer", d)
    # Kopie einer Bohrer-Zeile: gewählt ist vc – ae gibt es beim Bohrer nicht.
    s.einsatz_kopieren()
    yield 100
    h.pruefe(
        (s.tabelle.currentRow(), s.tabelle.currentColumn()) == (1, gs.VC),
        f"Bohrer-Kopie gewählt: {s.tabelle.currentRow()}, {s.tabelle.currentColumn()}",
    )
    h.pruefe(zelle(d, 1, gs.EINSATZ) == "Bohren 2", f"Name der Kopie {zelle(d, 1, gs.EINSATZ)!r}")
    s.einsatz_entfernen()
    yield 100

    # Gewindebohrer: nur „Gewindebohren“ und „eigen“; f ist die Steigung, fest.
    gewinde = d.werkzeug_anlegen()
    d.feld_art.setCurrentIndex(d.feld_art.findData(wz.GEWINDEBOHRER_RECHTS))
    yield 200
    s._menue_fuellen()
    angeboten = [a.text() for a in s.menue_plus.actions() if a.text() and not a.isSeparator()]
    h.pruefe(
        angeboten[:2] == ["Gewindebohren", "Eigener Einsatz"],
        f"Gewindebohrer bietet an: {angeboten}",
    )
    s.einsatz_anlegen(wz.GEWINDEBOHREN)
    s.setze(0, gs.VC, "10")
    yield 100
    fest = not (s.tabelle.item(0, gs.FZ).flags() & QtCore.Qt.ItemIsEditable)
    h.pruefe(
        (zelle(d, 0, gs.FZ), zelle(d, 0, gs.N), zelle(d, 0, gs.VF)) == ("1,5", "318", "477")
        and fest,
        f"Gewindebohrer M10: f {zelle(d, 0, gs.FZ)}, n {zelle(d, 0, gs.N)}, "
        f"vf {zelle(d, 0, gs.VF)}, fest {fest}",
    )
    h.pruefe(gewinde.einsaetze(wz.ALLE)[0].vc == 10, "vc des Gewindebohrers")
    h.bild("4b_gewindebohrer", d)
    # Drehwerkzeug: keine Tabelle, ein Satz dazu.
    d.feld_art.setCurrentIndex(d.feld_art.findData(wz.DREHWERKZEUG))
    yield 200
    h.pruefe(
        not s.inhalt.isVisible() and s.ohne_tabelle.isVisible(),
        "Drehwerkzeug zeigt eine Schnittwert-Tabelle",
    )
    h.bild("4c_drehwerkzeug_ohne_schnittwerte", d)
    d.bibliothek.entferne(gewinde)
    d._liste_aufbauen()
    yield 100

    # OK speichert alles.
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 500
    fraeser = next(w for w in wz.Bibliothek.laden().werkzeuge if w.nummer == 3)
    h.pruefe(fraeser.einsaetze("1.4301")[0].vc == 80, "eigene Werte nicht gespeichert")
    h.pruefe(fraeser.einsaetze(wz.ALLE)[1].ap == 25, "Werte für alle nicht gespeichert")
