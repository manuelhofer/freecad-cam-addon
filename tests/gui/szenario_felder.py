# Eingaben in den Feldern des Dialogs, getippt wie von einem Benutzer:
# - Enter bestätigt nur das Feld; der Dialog bleibt offen (B-005).
# - Deutsches Zahlenformat (B-004): FreeCAD stellt es auf einem deutschen
#   System ein. Die Felder zeigen keine Tausenderpunkte, und ein geleertes
#   Feld heißt „unbekannt“. Getippt gilt „35.000“ als 35000, „2.5“ als 2,5.
import os
import sys

import FreeCADGui as Gui
from PySide import QtCore
from PySide6 import QtTest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def enter(widget):
    QtTest.QTest.keyClick(widget, QtCore.Qt.Key_Return)


def eingeben(widget, text):
    """Feld leeren, `text` Taste für Taste tippen, Enter."""
    widget.selectAll()
    QtTest.QTest.keyClick(widget, QtCore.Qt.Key_Delete)
    QtTest.QTest.keyClicks(widget, text)
    enter(widget)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300
    # So stellt FreeCAD das Zahlenformat auf einem deutschen System ein
    # (ausprobiert mit LANG=de_DE in 1.1.3 und im Wochen-Build).
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.German, QtCore.QLocale.Germany))

    import beispielmaschinen

    from camaddon import gui_maschine
    from camaddon import maschine as m

    asm = beispielmaschinen.drehmaschine()
    doc = asm.Document
    x1 = m.neue_betriebsart(m.lege_maschine_an(asm), doc.getObject("X"), m.ART_LINEAR, "X1")
    x1.Eilgang, x1.Beschleunigung = 30000, 2.5
    Gui.Selection.addSelection(asm)
    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield 1500
    panel = gui_maschine.MaschinenPanel.offen
    panel.neu_aufbauen(auswahl=x1)
    yield 300
    eilgang, beschleunigung = panel.details.feld(1), panel.details.feld(3)
    h.pruefe(eilgang.text() == "30000", f"Eilgang zeigt {eilgang.text()!r} statt '30000'")
    h.pruefe(
        beschleunigung.text() == "2,5",
        f"Beschleunigung zeigt {beschleunigung.text()!r} statt '2,5'",
    )
    h.bild("1_deutsches_format")

    # Enter ohne Änderung lässt den Wert, wie er ist – und den Dialog offen.
    enter(eilgang)
    yield 200
    if panel.geschlossen:
        h.pruefe(False, "Enter im Feld hat den Dialog geschlossen (B-005)")
        return
    h.pruefe(x1.Eilgang == 30000, f"Enter ohne Änderung ergibt Eilgang {x1.Eilgang}")

    # Mit Komma als Dezimalzeichen ist der Punkt in „35.000“ ein Tausenderpunkt
    # (B-004) – in „2.5“ aber ein Dezimalpunkt.
    eingeben(eilgang, "35.000")
    h.pruefe(x1.Eilgang == 35000, f"„35.000“ getippt ergibt {x1.Eilgang} statt 35000")
    h.pruefe(not panel.geschlossen, "Enter nach dem Tippen hat den Dialog geschlossen")
    eingeben(beschleunigung, "2.5")
    h.pruefe(x1.Beschleunigung == 2.5, f"„2.5“ getippt ergibt {x1.Beschleunigung}")
    eingeben(beschleunigung, "3,5")
    h.pruefe(x1.Beschleunigung == 3.5, f"„3,5“ getippt ergibt {x1.Beschleunigung}")

    # Ein geleertes Feld heißt „unbekannt“; beim Eilgang (Pflicht) folgt ein Hinweis.
    eingeben(eilgang, "")
    yield 300
    h.pruefe(x1.Eilgang == 0, f"geleertes Feld: Eilgang bleibt {x1.Eilgang}")
    texte = [panel.hinweise.item(i).text() for i in range(panel.hinweise.count())]
    h.pruefe(
        any("X1" in t and "Eilgang" in t for t in texte), f"fehlender Eilgang: Hinweise {texte}"
    )
    h.bild("2_eilgang_geleert")
    panel.reject()
