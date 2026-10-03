# Die Werkzeugkiste der Hersteller (W-007, P-2026-10-02-46; Manuel, 2026-10-02: „Ich hätte gerne
# die Werkzeugkiste vorgefüllt … mit Internetseite zum Bestellen, Link und Artikelnummer … wenn
# ich in der Werkzeugkiste etwas verändere oder hinzufüge, sollte es nach dem Neustart noch
# vorhanden sein“): Die leere Werkzeugverwaltung nennt „Werkzeuge der Hersteller …“; das Fenster
# zeigt die Reihen, alle angehakt, der Tooltip sagt, woher Maße und Werte kommen. „Hinzufügen“
# legt alle an, die Rückmeldung sagt wie viele. Der Jongen Ø 12 zeigt Hersteller, Artikel-Nr.,
# Bestellen und Katalog mit „Öffnen“ und je Werkstoffklasse seine fünf Einsätze (seit
# P-2026-10-02-54 mit „Planen“). „Übernehmen“
# speichert; wieder geöffnet (wie nach einem Neustart) ist alles da, und ein zweites Mal kommt
# nichts doppelt. Ein neues Werkzeug bietet „Richtwerte eintragen“ an (P-2026-10-02-47).
import FreeCADGui as Gui
from PySide import QtCore, QtGui


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.German, QtCore.QLocale.Germany))

    from camaddon import gui_werkzeuge
    from camaddon import werkstoffe as ws
    from camaddon import werkzeugkiste as wk

    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d is not None and d.isVisible(), "Werkzeugverwaltung geht nicht auf")
    if d is None:
        return
    h.pruefe(
        d.leer.isVisible() and "Werkzeuge der Hersteller" in d.leer.text(),
        f"leer: {d.leer.text()!r}",
    )
    h.pruefe(d.knopf_kiste.isVisible(), "Knopf „Werkzeuge der Hersteller …“ fehlt")
    d.knopf_kiste.click()
    yield 500
    kiste = getattr(d, "kiste", None)
    h.pruefe(kiste is not None and kiste.isVisible(), "das Fenster der Werkzeugkiste fehlt")
    if kiste is None:
        return
    reihen = wk.reihen()
    gesamt = sum(r.anzahl for r in reihen)
    eintraege = kiste.reihen_eintraege()
    h.pruefe(len(eintraege) == len(reihen), f"{len(eintraege)} Reihen")
    h.pruefe(set(kiste.gewaehlt()) == {r.kennung for r in reihen}, "nicht alle angehakt")
    # Je Werkzeugart eine Gruppe, darin die Reihen, darin die Größen (Manuel, 2026-10-03).
    bohrer = next((e for e in eintraege if e.text(0).startswith("Ceratizit · CoreLine")), None)
    h.pruefe(bohrer is not None, "Reihe Ceratizit fehlt")
    if bohrer is None:
        return
    h.pruefe(
        bohrer.text(0).endswith("(30)") and bohrer.parent().text(0).startswith("Bohrer ("),
        f"Reihe: {bohrer.text(0)!r} unter {bohrer.parent().text(0)!r}",
    )
    h.pruefe("ceratizit.com" in bohrer.toolTip(0), f"Tooltip: {bohrer.toolTip(0)!r}")
    h.pruefe(bohrer.childCount() == 30, f"{bohrer.childCount()} Größen")
    # Einzelne Größen: die Reihe abhaken, eine Größe anhaken – nur sie wird hinzugefügt.
    bohrer.setCheckState(0, QtCore.Qt.Unchecked)
    bohrer.child(3).setCheckState(0, QtCore.Qt.Checked)
    kennung = bohrer.data(0, QtCore.Qt.UserRole)
    gewaehlt = kiste.gewaehlt()
    h.pruefe(
        (kennung, 3) in gewaehlt and kennung not in gewaehlt and len(gewaehlt) == len(reihen),
        f"einzelne Größe: {[g for g in gewaehlt if not isinstance(g, str)]}",
    )
    h.pruefe(bohrer.checkState(0) == QtCore.Qt.PartiallyChecked, f"Reihe: {bohrer.checkState(0)}")
    bohrer.setExpanded(True)
    h.bild("1_kiste", kiste)
    bohrer.setCheckState(0, QtCore.Qt.Checked)
    h.pruefe(set(kiste.gewaehlt()) == {r.kennung for r in reihen}, "wieder alle angehakt")
    kiste.knopf_hinzufuegen.click()
    yield 800
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        h.pruefe(
            meldung.text().startswith(f"{gesamt} Werkzeuge hinzugefügt, 0 gab es schon"),
            f"Rückmeldung: {meldung.text()!r}",
        )
        meldung.accept()
    else:
        h.pruefe(False, f"keine Rückmeldung: {meldung}")
    yield 300
    h.pruefe(
        len(d.liste.eintraege()) == gesamt, f"{len(d.liste.eintraege())} Werkzeuge statt {gesamt}"
    )
    h.pruefe(d.geaendert, "Hinzugefügtes gilt nicht als Änderung")

    def waehle(dialog, name):
        zeile = next(
            (
                i
                for i in range(len(dialog.liste.eintraege()))
                if name in dialog.liste.eintraege()[i].text(0)
            ),
            None,
        )
        h.pruefe(zeile is not None, f"{name} fehlt in der Liste")
        if zeile is not None:
            dialog.liste.setCurrentItem(dialog.liste.eintraege()[zeile])
        return zeile is not None

    if not waehle(d, "494W D12"):
        return
    yield 300
    h.pruefe(
        d.feld_hersteller.text() == "Jongen" and d.feld_artikel.text() == "VU494M12B-HI06",
        f"Jongen Ø 12: {d.feld_hersteller.text()!r}, {d.feld_artikel.text()!r}",
    )
    h.pruefe(
        d.feld_link.text().startswith("https://") and d.knopf_link.isEnabled(),
        f"Bestellen: {d.feld_link.text()!r}",
    )
    h.pruefe(d.knopf_katalog.isEnabled(), "Katalog: „Öffnen“ aus")
    h.pruefe(
        d.feld_durchmesser.text() == "12" and d.feld_schneiden.value() == 4,
        f"Ø {d.feld_durchmesser.text()!r}, z {d.feld_schneiden.value()}",
    )
    zeilen = d.schnittwerte.tabelle.rowCount()
    h.pruefe(zeilen == len(ws.KLASSEN) * 5, f"Schnittwerte: {zeilen} Zeilen")
    h.bild("2_jongen_12", d)
    # Ein einzelner Werkstoff bekommt eigene Werte (P-2026-10-02-50): 1.4404 eine Kopie der
    # Zeilen seiner Klasse M – fünf Zeilen mehr, die erste gewählt.
    h.pruefe(d.schnittwerte.aktion_eigene.isEnabled(), "„Eigene Werte für einen Werkstoff“ aus")
    eigene = d.schnittwerte.eigene_werte("1.4404")
    yield 300
    h.pruefe(
        len(eigene) == 5 and d.schnittwerte.tabelle.rowCount() == zeilen + 5,
        f"eigene Werte 1.4404: {len(eigene)}, {d.schnittwerte.tabelle.rowCount()} Zeilen",
    )
    h.pruefe(d.schnittwerte.gewaehlter_werkstoff == "1.4404", d.schnittwerte.gewaehlter_werkstoff)
    h.bild("2b_eigene_1_4404", d)

    # Speichern, schließen, wieder öffnen – wie nach einem Neustart.
    h.pruefe(d.uebernehmen(), "„Übernehmen“ ging nicht")
    d.reject()
    yield 500
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d2 = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(
        d2 is not None and d2 is not d and len(d2.liste.eintraege()) == gesamt,
        f"wieder geöffnet: {len(d2.liste.eintraege()) if d2 is not None else None}",
    )
    if d2 is None:
        return
    if waehle(d2, "WPC D8,5"):
        yield 300
        h.pruefe(
            d2.feld_durchmesser.text() == "8,5" and d2.feld_hersteller.text() == "Ceratizit",
            f"Bohrer: {d2.feld_durchmesser.text()!r}, {d2.feld_hersteller.text()!r}",
        )
        h.pruefe(
            d2.schnittwerte.tabelle.rowCount() == len(ws.KLASSEN),
            f"Bohrer: {d2.schnittwerte.tabelle.rowCount()} Zeilen",
        )
        h.bild("3_bohrer_8_5", d2)
    bericht = d2.aus_kiste_hinzufuegen([r.kennung for r in reihen])
    yield 500
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        meldung.accept()
    h.pruefe(
        not bericht.neu and len(bericht.schon_da) == gesamt and len(d2.liste.eintraege()) == gesamt,
        f"zweites Mal: {len(bericht.neu)} neu",
    )
    # Ein neues Werkzeug bekommt die Richtwerte mit einem Klick (P-2026-10-02-47).
    d2.knopf_neu.click()
    yield 300
    s = d2.schnittwerte
    h.pruefe(
        s.tabelle.rowCount() == 0 and s.knopf_richtwerte.isVisible() and s.leer_hinweis.isVisible(),
        "neues Werkzeug: „Richtwerte eintragen“ fehlt",
    )
    h.bild("4_neu_leer", d2)
    s.knopf_richtwerte.click()
    yield 300
    h.pruefe(
        s.tabelle.rowCount() == len(ws.KLASSEN) * 5 and not s.knopf_richtwerte.isVisible(),
        f"Richtwerte: {s.tabelle.rowCount()} Zeilen",
    )
    h.bild("5_neu_richtwerte", d2)
    h.pruefe(d2.uebernehmen(), "„Übernehmen“ ging nicht")
    d2.reject()
    yield 300
