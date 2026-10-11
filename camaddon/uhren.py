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

import contextlib
import functools
import sys
import time

# atmen(): höchstens so oft (s) arbeitet eine lange Rechnung im Hauptprozess die Ereignisse ab.
ATMEN_ALLE = 0.1
_GEATMET = [0.0]
_ATMEND = [0]  # wie tief in atmend()


@contextlib.contextmanager
def atmend():
    """Darin arbeitet atmen() Ereignisse ab – nur wo der Aufrufer weiß, dass dazwischen nichts
    dieselben Daten anfasst (das Anlegen im Assistenten „Bearbeitung“). Sonst nicht: Im Abspieler
    liefe sein eigener Takt mitten in den Abtrag hinein."""
    _ATMEND[0] += 1
    try:
        yield
    finally:
        _ATMEND[0] -= 1


def atmen():
    """Für lange Rechnungen im Hauptprozess (die Bahn einer Operation beim Anlegen, das
    5-Achs-Programm): höchstens alle ATMEN_ALLE s arbeitet Qt seine Ereignisse ab – ohne Maus und
    Tastatur, wie beim Warten auf die Nebenrechner (nebenrechner.ereignisse_ohne_eingaben): Das
    Fenster zeichnet sich neu, nimmt aber keinen Klick an. Die Uhren des Addons laufen dabei nicht
    (aus_der_schleife). Nur in atmend(); ohne Oberfläche (Nebenrechner, Prüfdateien) nichts
    (P-2026-10-11-67)."""
    if not _ATMEND[0]:
        return
    jetzt = time.monotonic()
    if jetzt - _GEATMET[0] < ATMEN_ALLE:
        return
    _GEATMET[0] = jetzt
    try:
        from PySide import QtCore, QtGui
    except ImportError:
        return
    if isinstance(QtGui.QApplication.instance(), QtGui.QApplication):
        QtGui.QApplication.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)


def atmend_rechnen(methode):
    """Für `opExecute` der Operationen des Addons: Ihre Bahn rechnet in atmend() – bei jedem
    Neuberechnen (eine Eigenschaft geändert, „Neu berechnen“), nicht nur beim Anlegen im
    Assistenten. Sonst stand das Fenster, solange sie rechnete (3D-Schlichten 2,3 s, Räumen am
    Testteil 6 s; unter Windows meldet es nach 5 s „Keine Rückmeldung“; P-2026-10-11-78). Die
    Uhren des Addons laufen dabei nicht (aus_der_schleife, gleich)."""

    @functools.wraps(methode)
    def gehuellt(*args, **kwargs):
        with atmend():
            return methode(*args, **kwargs)

    return gehuellt


def gleich(slot):
    """Wie `QTimer.singleShot(0, slot)` – aber nicht mitten in einer Rechnung (verschachtelt):
    Dann kommt `slot`, wenn sie fertig ist. Für Rückrufe, die Dokumente anfassen (eine
    angeklickte Fläche)."""
    from PySide import QtCore

    def abgelaufen():  # direkt von Qt gerufen: kein Python-Rahmen darunter, außer in einer Rechnung
        if verschachtelt():
            QtCore.QTimer.singleShot(ATMEN_ALLE * 1000, abgelaufen)
            return
        slot()

    QtCore.QTimer.singleShot(0, abgelaufen)


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
