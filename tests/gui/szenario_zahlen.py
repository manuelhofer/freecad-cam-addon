# Zahlenfelder im deutschen Zahlenformat (B-004). FreeCAD stellt auf einem
# deutschen System das deutsche Format ein. Die Felder zeigen dann keine
# Tausenderpunkte, jede Eingabe ist eindeutig, und ein geleertes Feld heißt
# „unbekannt“. Getippt wird Taste für Taste – nur so greift die Prüfung der
# Eingabe, die einen Punkt auf Deutsch gar nicht erst annimmt.
import os
import sys

import FreeCADGui as Gui
from PySide import QtCore, QtGui
from PySide6 import QtTest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def feld(panel, zeile):
    return panel.detail_aufbau.itemAt(zeile, QtGui.QFormLayout.FieldRole).widget()


def bestaetigen(widget):
    """Wie Enter im Feld: QLineEdit meldet „fertig“ nur, wenn die Prüfung die Eingabe annimmt.

    Echtes Enter geht hier nicht: Darauf schließt FreeCADs Aufgabenfenster den
    ganzen Dialog mit OK (B-005).
    """
    if widget.hasAcceptableInput():
        widget.editingFinished.emit()


def eingeben(widget, text):
    """Feld leeren, `text` Taste für Taste tippen, bestätigen."""
    widget.selectAll()
    QtTest.QTest.keyClick(widget, QtCore.Qt.Key_Delete)
    QtTest.QTest.keyClicks(widget, text)
    bestaetigen(widget)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
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
    panel._fuelle_alles(auswahl=x1)
    yield 300
    eilgang, beschleunigung = feld(panel, 1), feld(panel, 3)
    h.pruefe(eilgang.text() == "30000", f"Eilgang zeigt {eilgang.text()!r} statt '30000'")
    h.pruefe(
        beschleunigung.text() == "2,5",
        f"Beschleunigung zeigt {beschleunigung.text()!r} statt '2,5'",
    )
    h.bild("1_deutsches_format")

    # Bestätigen ohne Änderung lässt den Wert, wie er ist.
    bestaetigen(eilgang)
    h.pruefe(x1.Eilgang == 30000, f"Bestätigen ohne Änderung ergibt Eilgang {x1.Eilgang}")

    # Auf Deutsch ist der Punkt kein Dezimalzeichen: Das Feld nimmt ihn nicht an.
    eingeben(eilgang, "35.000")
    h.pruefe(x1.Eilgang == 35000, f"„35.000“ getippt ergibt {x1.Eilgang} statt 35000")
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
