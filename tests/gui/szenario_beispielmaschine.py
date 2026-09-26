# Beispielmaschine zum Ausprobieren (W-001): „Maschine bearbeiten“ ohne
# Baugruppe meldet das mit dem Knopf „Beispielmaschine laden“; der Knopf
# öffnet die fertig eingerichtete Fräsmaschine und gleich den Dialog.
# Genauso bei „Maschine verfahren“ in einem leeren Dokument – dort fahren X
# und Z, und man sieht die Maschine sich bewegen.
import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui


def knopf(meldung, text):
    return next((k for k in meldung.buttons() if k.text() == text), None)


def meldung_mit_beispiel(h, befehl, bild, offen):
    """Ruft den Befehl auf, prüft die Meldung und klickt „Beispielmaschine laden“;
    wartet dann, bis `offen()` – der Dialog nach dem Laden ist da."""
    # Die Meldung blockiert, bis sie beantwortet ist.
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand(befehl))
    yield 800
    meldung = h.modal()
    h.pruefe(isinstance(meldung, QtGui.QMessageBox), f"{befehl}: keine Meldung ({meldung})")
    if not isinstance(meldung, QtGui.QMessageBox):
        return
    laden = knopf(meldung, "Beispielmaschine laden")
    h.pruefe(laden is not None, f"{befehl}: Knopf „Beispielmaschine laden“ fehlt")
    h.pruefe("Beispielmaschine laden" in meldung.text(), f"Meldung: {meldung.text()!r}")
    h.bild(bild, meldung)
    if laden is not None:
        laden.click()
    yield from h.warte_auf(offen)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import gui_maschine, gui_verfahren
    from camaddon import verfahren as vf

    # Ohne Dokument: „Maschine bearbeiten“.
    yield from meldung_mit_beispiel(
        h,
        "CamAddon_MaschineBearbeiten",
        "1_meldung_bearbeiten",
        lambda: gui_maschine.MaschinenPanel.offen is not None,
    )
    doc = FreeCAD.ActiveDocument
    h.pruefe(doc is not None and doc.Label == "Beispielmaschine", "Beispielmaschine nicht geladen")
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(panel is not None, "„Maschine bearbeiten“ öffnet sich nicht nach dem Laden")
    if panel is None:
        return
    h.bild("2_bearbeiten")
    # Ohne Revolver gibt es kein Feld „Revolverplatz“ (Manuel: „hier ist noch
    # kein Revolver zu sehen, also wieso Revolverplatz?“).
    spindel = panel.aufnahmen.findItems("Spindel", QtCore.Qt.MatchStartsWith)
    h.pruefe(bool(spindel), "Werkzeugaufnahme „Spindel“ fehlt in der Liste")
    if spindel:
        panel.aufnahmen.setCurrentItem(spindel[0])
        yield 200
        zeilen = panel.details.formular.rowCount()
        h.pruefe(zeilen == 3, f"Spindel: {zeilen} Felder statt 3 (ohne Revolverplatz)")
        h.bild("2b_spindel_ohne_revolverplatz")
    panel.reject()
    yield 500

    # In einem leeren Dokument: „Maschine verfahren“ – noch eine Beispielmaschine.
    FreeCAD.newDocument("Leer")
    yield 300
    yield from meldung_mit_beispiel(
        h,
        "CamAddon_MaschineVerfahren",
        "3_meldung_verfahren",
        lambda: gui_verfahren.VerfahrPanel.offen is not None,
    )
    panel = gui_verfahren.VerfahrPanel.offen
    h.pruefe(panel is not None, "„Maschine verfahren“ öffnet sich nicht nach dem Laden")
    if panel is None:
        return
    namen = sorted(vf.namen(panel.maschine, a) for a in panel.zeilen)
    h.pruefe(namen == ["Spindelachse", "X1", "Y1", "Z1"], f"Achsen: {namen}")
    h.bild("4_verfahren_grundstellung")
    for name, stellung in (("X1", 200), ("Y1", -100), ("Z1", -80)):
        achse = panel.achse(name)
        _regler, feld = panel.zeilen[achse]
        feld.setValue(stellung)
        yield 300
        ist = vf.gelenkstellung(achse.gelenk, achse.art)
        h.pruefe(abs(ist - stellung) < 1e-6, f"{name} steht auf {ist} statt {stellung}")
    h.bild("5_verfahren_x200_y-100_z-80")
    panel.reject()
    yield 500
