# Führt ein Oberflächen-Szenario in einer echten (unsichtbaren) FreeCAD-
# Oberfläche aus. Ein Szenario ist eine Datei tests/gui/szenario_*.py mit einer
# Generator-Funktion schritte(h): Jedes `yield ms` wartet so lange und lässt
# FreeCAD dabei weiterlaufen – so erscheinen Dialoge, und modale Dialoge
# blockieren das Szenario nicht.
import importlib.util
import os
import sys
import traceback

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

AUSGABE = os.environ["CAMADDON_AUSGABE"]

# Erst loslegen, wenn das Hauptfenster steht.
START_NACH_MS = 3000


class Helfer:
    def __init__(self):
        self.fehler = []

    def bild(self, name, widget=None):
        """Screenshot von `widget` (Standard: Hauptfenster) nach AUSGABE/name.png."""
        QtGui.QApplication.processEvents()
        widget = widget or FreeCADGui.getMainWindow()
        widget.grab().save(os.path.join(AUSGABE, name + ".png"))

    def warte_auf(self, bedingung, hoechstens_ms=20000, schritt_ms=250):
        """Wartet (mit `yield from`), bis `bedingung()` wahr ist – höchstens so lange.

        Statt fester Wartezeiten: Lädt FreeCAD etwas Großes, dauert es auf
        einem langsamen Rechner länger. Prüft das Szenario zu früh, endet es,
        und der Lauf schließt die Dokumente, während FreeCAD noch lädt – so
        gesehen bei der Beispielmaschine (P-2026-09-26-57).
        """
        gewartet = 0
        while not bedingung() and gewartet < hoechstens_ms:
            yield schritt_ms
            gewartet += schritt_ms

    def modal(self):
        return QtGui.QApplication.activeModalWidget()

    def pruefe(self, bedingung, text):
        if not bedingung:
            self.fehler.append(text)


def _ende(helfer, fehler=None):
    if fehler:
        helfer.fehler.append(fehler)
    with open(os.path.join(AUSGABE, "ergebnis.txt"), "w", encoding="utf-8") as datei:
        datei.write("\n".join(helfer.fehler) if helfer.fehler else "OK")
    # Offene modale Dialoge zuerst schließen, sonst beendet quit() nicht.
    while QtGui.QApplication.activeModalWidget():
        QtGui.QApplication.activeModalWidget().done(0)
    # Offenes Aufgabenfenster und geänderte Dokumente schließen – sonst fragt
    # FreeCAD beim Beenden „Änderungen speichern?“ und wartet, bis das
    # Zeitlimit des Skripts greift.
    FreeCADGui.Control.closeDialog()
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    QtGui.QApplication.quit()


def starten():
    # Bei einem Absturz von FreeCAD selbst (Segfault) wenigstens den Python-
    # Stack festhalten, sonst sieht man nur „Segmentation fault“.
    import faulthandler

    # Bleibt bis zum Ende offen – faulthandler schreibt erst beim Absturz hinein.
    starten.absturz = open(os.path.join(AUSGABE, "absturz.txt"), "w")  # noqa: SIM115
    faulthandler.enable(starten.absturz)
    pfad = os.environ["CAMADDON_SZENARIO"]
    spec = importlib.util.spec_from_file_location("szenario", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    helfer = Helfer()
    ablauf = modul.schritte(helfer)
    # Eine Ausnahme in einem Qt-Slot (etwa beim Umschalten eines Hakens) läuft an keinem
    # Schritt vorbei – FreeCAD druckt sie nur in den Bericht, das Szenario ginge durch.
    # Hier zählt sie als Fehler (P-2026-09-30-17).
    vorher = sys.excepthook

    def ausnahme(art, wert, verlauf):
        text = "".join(traceback.format_exception(art, wert, verlauf))
        helfer.fehler.append("Ausnahme in der Oberfläche:\n" + text)
        vorher(art, wert, verlauf)

    sys.excepthook = ausnahme

    def weiter():
        try:
            warten = next(ablauf)
        except StopIteration:
            _ende(helfer)
            return
        except Exception:
            _ende(helfer, traceback.format_exc())
            return
        QtCore.QTimer.singleShot(int(warten), weiter)

    QtCore.QTimer.singleShot(START_NACH_MS, weiter)
    FreeCAD.Console.PrintLog("Szenario geladen: " + pfad + "\n")
