# SPDX-License-Identifier: LGPL-2.1-or-later
"""Uhren (QTimer) des Addons, die nicht mitten in eine Rechnung fallen.

FreeCAD 26.3 zeigt den Fortschritt boolescher Operationen von Part (Schnitt, Vereinigung …) und
arbeitet dabei Qt-Ereignisse ab (SequencerBar → processEvents). Eingaben sperrt es so lange,
Uhren nicht: Eine Uhr des Addons lief damit mitten in einer Rechnung, die selbst noch nicht
fertig war – im Wochen-Build schloss das Szenario „Ebene schwenken“ seine Dokumente, während der
Assistent im Job der Ebene noch rechnete, und FreeCAD stürzte ab (P-2026-10-10-45). 1.1.3 rechnet
boolesche Operationen ohne Fortschritt; dort ändert sich nichts.

Mitten in einer Rechnung heißt: Qt ruft den Slot aus Python-Code heraus auf, nicht aus seiner
Ereignisschleife – dann liegt unter ihm noch ein Python-Rahmen. Die Uhr läuft dann noch einmal,
der Slot kommt, wenn die Rechnung darunter fertig ist.
"""

import sys


def verschachtelt(tiefe=2):
    """Liegt unter dem Aufrufer von verschachtelt() (`tiefe` 2: unter dem, der ihn rief) noch
    Python-Code – und kein modales Fenster offen? Aus Qts Ereignisschleife gerufen liegt nichts
    darunter (sie ist C++); ein modales Fenster (QDialog.exec aus Python) hat seine eigene
    Schleife, darin laufen die Uhren wie bisher."""
    try:
        sys._getframe(tiefe)
    except ValueError:  # so tief reicht der Stapel nicht: nichts darunter
        return False
    try:
        from PySide import QtGui

        return QtGui.QApplication.activeModalWidget() is None
    except Exception:  # ohne Oberfläche: keine Uhren
        return False


def aus_der_schleife(uhr, slot):
    """Für `uhr.timeout.connect(...)`: ruft `slot`, wenn Qt die Uhr aus seiner Ereignisschleife
    auslöst; mitten in einer Rechnung startet es die Uhr neu (mit ihrem Takt)."""

    def abgelaufen():
        if verschachtelt():
            uhr.start()
            return
        slot()

    return abgelaufen
