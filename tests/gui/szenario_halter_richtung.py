# Halter mit Richtung (W-002 Stufe E, Manuel 2026-09-30: „wie steht die Werkzeug-Z-Achse
# zur Maschinen-Haupt-Z-Achse“). Werkzeugverwaltung → neues Werkzeug, Gesamtlänge 57 →
# „Halter …“ → „Neu“ → „VDI30 angetrieben radial · ER16“: Richtung „gewinkelt“, Winkel 90,
# Drehung 0, Versatz 55, Kopf-Ø 55; „Kontur ab Bezugspunkt, längs der
# Werkzeugachse:“; „Länge 55,00 mm · größter Ø 50,00 mm · gewinkelt 90°, Versatz
# 55,00 mm“; das Bild zeigt Kopf und Knick. Winkel 45 → das Bild kippt. „gerade“ blendet
# die vier Felder aus, „gewinkelt“ zeigt sie wieder. OK → beim Werkzeug steht „Länge ab
# Bezugspunkt“ mit grau „leer: 92 mit Halter“ (55 + 57 − 20).
import FreeCADGui as Gui
from PySide import QtCore, QtGui
from PySide6 import QtTest


def tippen(feld, text):
    """Feld leeren, `text` Taste für Taste tippen, Enter."""
    feld.setFocus()
    feld.selectAll()
    QtTest.QTest.keyClick(feld, QtCore.Qt.Key_Delete)
    QtTest.QTest.keyClicks(feld, text)
    QtTest.QTest.keyClick(feld, QtCore.Qt.Key_Return)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300

    from camaddon import gui_halter, gui_werkzeuge
    from camaddon import halter as hl

    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d is not None and d.isVisible(), "Werkzeugverwaltung geht nicht auf")
    if d is None:
        return
    d.knopf_neu.click()
    yield 200
    tippen(d.feld_gesamtlaenge, "57")
    yield 200
    beschriftung = d.beschriftung_laenge_spindelnase.text()
    h.pruefe(beschriftung == "Länge ab Spindelnase", f"ohne Halter: {beschriftung!r}")

    QtCore.QTimer.singleShot(0, d.knopf_halter.click)
    yield 500
    f = gui_halter.HalterDialog.offen
    h.pruefe(f is not None and f.isVisible(), "Fenster „Halter“ geht nicht auf")
    if f is None:
        return
    vorlage = next(
        a for a in f.menue_neu.actions() if a.text() == "VDI30 angetrieben radial · ER16"
    )
    vorlage.trigger()
    yield 300
    halter = f.gewaehlt
    h.pruefe(halter is not None and halter.gewinkelt, "Vorlage nicht gewinkelt")
    h.pruefe(f.wahl_richtung.currentData() == hl.GEWINKELT, "Richtung nicht „gewinkelt“")
    werte = {k: e.text() for k, e in f.felder_gewinkelt.items()}
    h.pruefe(
        werte == {"winkel": "90", "drehung": "0", "versatz": "55", "kopf_d": "55"},
        f"Felder: {werte}",
    )
    h.pruefe(all(e.isVisible() for e in f.felder_gewinkelt.values()), "Felder nicht zu sehen")
    h.pruefe(
        f.kontur.text() == "Kontur ab Bezugspunkt, längs der Werkzeugachse:",
        f"Kontur: {f.kontur.text()!r}",
    )
    h.pruefe(
        f.zusammenfassung.text()
        == "Länge 55,00 mm · größter Ø 50,00 mm · gewinkelt 90°, Versatz 55,00 mm",
        f"Zusammenfassung: {f.zusammenfassung.text()!r}",
    )
    h.bild("1_vdi30_radial", f)

    tippen(f.felder_gewinkelt["winkel"], "45")
    yield 200
    h.pruefe(abs(halter.winkel - 45) < 1e-9, f"Winkel: {halter.winkel}")
    h.bild("2_winkel_45", f)
    tippen(f.felder_gewinkelt["winkel"], "90")
    f.wahl_richtung.setCurrentIndex(f.wahl_richtung.findData(hl.GERADE))
    yield 200
    h.pruefe(not halter.gewinkelt, "„gerade“ nicht übernommen")
    h.pruefe(not any(e.isVisible() for e in f.felder_gewinkelt.values()), "Felder bei „gerade“ da")
    h.pruefe(f.kontur.text() == "Kontur ab Spindelnase:", f"Kontur: {f.kontur.text()!r}")
    h.bild("3_gerade", f)
    f.wahl_richtung.setCurrentIndex(f.wahl_richtung.findData(hl.GEWINKELT))
    yield 200
    h.pruefe(halter.gewinkelt and abs(halter.versatz - 55) < 1e-9, "zurück auf gewinkelt")
    f.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 400

    h.pruefe(gui_halter.HalterDialog.offen is None, "Halter-Fenster noch offen")
    beschriftung = d.beschriftung_laenge_spindelnase.text()
    h.pruefe(beschriftung == "Länge ab Bezugspunkt", f"mit gewinkeltem Halter: {beschriftung!r}")
    h.pruefe(
        d.feld_laenge_spindelnase.placeholderText() == "leer: 92 mit Halter",
        f"Platzhalter: {d.feld_laenge_spindelnase.placeholderText()!r}",
    )
    h.bild("4_werkzeug", d)
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()  # speichern: nichts fragt nach
    yield 500
    h.pruefe(gui_werkzeuge.WerkzeugDialog.offen is None, "Werkzeugverwaltung noch offen")
