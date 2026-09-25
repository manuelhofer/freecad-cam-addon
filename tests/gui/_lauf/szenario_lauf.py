# Führt ein Oberflächen-Szenario in einer echten (unsichtbaren) FreeCAD-
# Oberfläche aus. Ein Szenario ist eine Datei tests/gui/szenario_*.py mit einer
# Generator-Funktion schritte(h): Jedes `yield ms` wartet so lange und lässt
# FreeCAD dabei weiterlaufen – so erscheinen Dialoge, und modale Dialoge
# blockieren das Szenario nicht.
import importlib.util
import os
import traceback

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

AUSGABE = os.environ["CAMADDON_AUSGABE"]


class Helfer:
    def __init__(self):
        self.fehler = []

    def bild(self, name, widget=None):
        """Screenshot von `widget` (Standard: Hauptfenster) nach AUSGABE/name.png."""
        QtGui.QApplication.processEvents()
        widget = widget or FreeCADGui.getMainWindow()
        widget.grab().save(os.path.join(AUSGABE, name + ".png"))

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

    # Erst loslegen, wenn das Hauptfenster steht.
    QtCore.QTimer.singleShot(3000, weiter)
    FreeCAD.Console.PrintLog("Szenario geladen: " + pfad + "\n")
