# Spannmittel und Halter mit eigenem Knopf (W-042; Manuel, 2026-10-31: „die halter oder aufnahmen
# einen eigenen knopf … genau so spannmittel ... eine übersicht … gut vorgefüllt … wie er auf dem
# tisch aufgespannt ist“).
# 1. „Spannmittel …“: die Sammlung ist leer und sagt, wo es Spannmittel gibt („Katalog …“).
# 2. „Katalog …“: je Art die Reihen der Hersteller, nichts angehakt. Je eine Größe eines
#    Schraubstocks, eines Zentrischspanners und eines Nullpunktspannsystems anhaken → „Übernehmen“:
#    drei in der Sammlung, je mit Maßen, Link und Quelle, das Bild mit Beispiel-Rohteil.
# 3. Seite „Aufspannung im Job“: der Schraubstock auf dem Nullpunktspannsystem, bei X 0, Y −50, um
#    90° gedreht, 6 mm gespannt. Darunter, wo der Nullpunkt dann liegt; das Bild auf dem Tisch.
# 4. OK: Am Job steht die Aufspannung; spannung.schraubstock gibt den Körper, „von unten gespannt“
#    sind 6 mm, der Nullpunkt-Vorschlag folgt, das Einrichtblatt nennt das Spannmittel.
# 5. „Halter und Aufnahmen …“ ohne Werkzeugverwaltung: „Katalog …“ zeigt die Reihen je Aufnahme;
#    eine Größe übernehmen → ein Halter mit Flansch und Kontur, mit OK gespeichert.
import os

import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui

AUSGABE = os.environ["CAMADDON_AUSGABE"]


def _erste_groesse(dialog, art_text):
    """Hakt die erste Größe der ersten Reihe in der Gruppe `art_text` an; ihr Text oder None."""
    for i in range(dialog.baum.topLevelItemCount()):
        gruppe = dialog.baum.topLevelItem(i)
        if gruppe.text(0).startswith(art_text) and gruppe.childCount():
            reihe = gruppe.child(0)
            groesse = reihe.child(0)
            groesse.setCheckState(0, QtCore.Qt.Checked)
            reihe.setExpanded(True)
            gruppe.setExpanded(True)
            return groesse.text(0)
    return None


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300

    from Path.Main import Job as PathJob

    from camaddon import einrichtblatt, gui_halter, gui_katalog, gui_spannmittel, spannung
    from camaddon import reichweite as rw
    from camaddon import spannmittel as sm
    from camaddon import werkzeuge as wz

    teil = FreeCAD.newDocument("Spannen")
    quader = teil.addObject("Part::Box", "Quader")
    quader.Length, quader.Width, quader.Height = 100, 60, 30
    teil.recompute()
    job = PathJob.Create("Job", [quader])
    teil.recompute()
    yield 500
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)

    # 1. Leer
    Gui.runCommand("CamAddon_Spannmittel")
    yield 800
    d = gui_spannmittel.SpannmittelDialog.offen
    h.pruefe(d is not None and d.isVisible(), "„Spannmittel …“ geht nicht auf")
    if d is None:
        return
    d.seiten.setCurrentIndex(0)
    yield 200
    h.pruefe(d.leer.isVisible() and "Katalog" in d.leer.text(), f"leer: {d.leer.text()!r}")
    h.bild("1_leer", d)

    # 2. Katalog
    QtCore.QTimer.singleShot(0, d.knopf_katalog.click)
    yield from h.warte_auf(lambda: gui_katalog.KatalogDialog.offen is not None, 10000)
    k = gui_katalog.KatalogDialog.offen
    h.pruefe(k is not None, "der Katalog geht nicht auf")
    if k is None:
        return
    yield 300
    gruppen = [k.baum.topLevelItem(i).text(0) for i in range(k.baum.topLevelItemCount())]
    print(ascii(f"Gruppen: {gruppen}"))
    h.pruefe(len(k.reihen_eintraege()) >= 10, f"nur {len(k.reihen_eintraege())} Reihen im Katalog")
    h.pruefe(not k.gewaehlt(), "im Katalog ist schon etwas angehakt")
    gewaehlt = [
        _erste_groesse(k, sm.art_text(art)) for art in (sm.SCHRAUBSTOCK, sm.ZENTRISCH, sm.NULLPUNKT)
    ]
    print(ascii(f"angehakt: {gewaehlt}"))
    h.pruefe(all(gewaehlt), f"nicht je Art eine Größe: {gewaehlt}")
    yield 200
    h.bild("2_katalog", k)
    k.accept()
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 10000)
    meldung = h.modal()
    if meldung is not None:
        h.pruefe("3 Spannmittel übernommen" in meldung.text(), f"Bericht: {meldung.text()!r}")
        meldung.accept()
    yield 300
    h.pruefe(len(d.sammlung.spannmittel) == 3, f"Sammlung: {len(d.sammlung.spannmittel)}")
    schraubstock = next((s for s in d.sammlung.spannmittel if s.art == sm.SCHRAUBSTOCK), None)
    modul = next((s for s in d.sammlung.spannmittel if s.art == sm.NULLPUNKT), None)
    if schraubstock is None or modul is None:
        h.pruefe(False, "Schraubstock oder Nullpunktspannsystem fehlt")
        return
    d.waehle(schraubstock)
    yield 300
    h.pruefe(d.feld_name.text() == schraubstock.name, f"Name: {d.feld_name.text()!r}")
    h.pruefe(d.quelle.text().startswith("Woher die Maße kommen"), f"Quelle: {d.quelle.text()!r}")
    h.pruefe(schraubstock.link.startswith("http"), f"Link: {schraubstock.link!r}")
    h.pruefe(len(d._massfelder) == len(sm.FELDER[sm.SCHRAUBSTOCK]), "Maßfelder fehlen")
    h.bild("3_schraubstock", d)
    zentrisch = next(s for s in d.sammlung.spannmittel if s.art == sm.ZENTRISCH)
    d.waehle(zentrisch)
    yield 300
    h.bild("3b_zentrisch", d)

    # 3. Aufspannung
    d.seiten.setCurrentIndex(1)
    yield 300
    d.wahl_spannmittel.setCurrentIndex(d.wahl_spannmittel.findData(schraubstock.kennung))
    d.wahl_unterbau.setCurrentIndex(d.wahl_unterbau.findData(modul.kennung))
    d.feld_y.setText("-50")
    d.feld_y.editingFinished.emit()
    d.wahl_drehung.setCurrentIndex(d.wahl_drehung.findData(90))
    d.feld_tiefe.setText("6")
    d.feld_tiefe.editingFinished.emit()
    yield 300
    auf = d.aufspannung
    h.pruefe(auf is not None and auf.unterbau is not None, "Aufspannung nicht gelesen")
    h.pruefe(auf is not None and auf.drehung == 90 and auf.y == -50, f"Lage: {auf}")
    h.pruefe("Nullpunkt des Jobs auf dem Tisch" in d.auf_nullpunkt.text(), d.auf_nullpunkt.text())
    print(ascii(f"Hinweis: {d.auf_hinweis.text()} | {d.auf_nullpunkt.text()}"))
    h.bild("4_aufspannung", d)

    # 4. OK
    d.accept()
    yield 500
    auf = sm.aufspannung(job)
    h.pruefe(auf is not None and auf.spannmittel.name == schraubstock.name, "nicht am Job")
    h.pruefe(spannung.schraubstock(job) is not None, "kein Körper für die Kollision")
    h.pruefe(abs(spannung.gespannt(job) - 6.0) < 1e-6, f"gespannt: {spannung.gespannt(job)}")
    box = job.Stock.Shape.BoundBox
    erwartet = sm.nullpunkt_vorschlag(auf, box)
    vorschlag = rw.vorschlag_nullpunkt(job)
    h.pruefe(abs(vorschlag.z - erwartet[2]) < 1e-6, f"Nullpunkt Z: {vorschlag.z} statt {erwartet}")
    from camaddon.sprache import tr

    text = einrichtblatt.spannung_text(job, tr)
    h.pruefe(schraubstock.name in text, f"Einrichtblatt: {text!r}")
    h.pruefe(os.path.exists(sm.datei_pfad()), "die Sammlung ist nicht gespeichert")

    # 5. Halter ohne Werkzeugverwaltung
    vorher = len(wz.Bibliothek.laden().halter)
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_Halter"))
    yield from h.warte_auf(lambda: gui_halter.HalterDialog.offen is not None, 10000)
    f = gui_halter.HalterDialog.offen
    h.pruefe(f is not None, "„Halter und Aufnahmen …“ geht nicht auf")
    if f is None:
        return
    yield 300
    QtCore.QTimer.singleShot(0, f.knopf_katalog.click)
    yield from h.warte_auf(lambda: gui_katalog.KatalogDialog.offen is not None, 10000)
    k = gui_katalog.KatalogDialog.offen
    h.pruefe(k is not None, "der Halter-Katalog geht nicht auf")
    if k is None:
        return
    yield 300
    gruppen = [k.baum.topLevelItem(i).text(0) for i in range(k.baum.topLevelItemCount())]
    print(ascii(f"Aufnahmen: {gruppen}"))
    h.pruefe(gruppen and gruppen[0].startswith("SK40"), f"oben nicht SK40: {gruppen[:2]}")
    erste = _erste_groesse(k, "SK40")
    h.pruefe(erste is not None, "keine Größe an SK40")
    yield 200
    h.bild("5_halter_katalog", k)
    k.accept()
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 10000)
    meldung = h.modal()
    if meldung is not None:
        h.pruefe("1 Halter übernommen" in meldung.text(), f"Bericht: {meldung.text()!r}")
        meldung.accept()
    yield 300
    halter = f.gewaehlt
    h.pruefe(halter is not None and halter.abschnitte[0].art == "flansch", "kein Flansch")
    h.pruefe(halter is not None and halter.laenge > 40, f"Länge: {halter and halter.laenge}")
    h.bild("6_halter", f)
    f.accept()
    yield 500
    nachher = len(wz.Bibliothek.laden().halter)
    h.pruefe(nachher == vorher + 1, f"Halter gespeichert: {vorher} → {nachher}")
