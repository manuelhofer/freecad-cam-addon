# Führt ein Oberflächen-Szenario in einer echten (unsichtbaren) FreeCAD-
# Oberfläche aus. Ein Szenario ist eine Datei tests/gui/szenario_*.py mit einer
# Generator-Funktion schritte(h): Jedes `yield ms` wartet so lange und lässt
# FreeCAD dabei weiterlaufen – so erscheinen Dialoge, und modale Dialoge
# blockieren das Szenario nicht.
import importlib.util
import os
import sys
import threading
import time
import traceback

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

AUSGABE = os.environ["CAMADDON_AUSGABE"]

# Erst loslegen, wenn das Hauptfenster steht.
START_NACH_MS = 3000
# Die Lag-Sonde: Steht die Ereignisschleife länger als so viele Sekunden, hält ein Wachhund fest,
# was im Hauptthread gerade rechnet (pausen.txt; Manuel: „das Fenster darf nie laggen“).
PAUSE_AB = 0.3


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


def _verschachtelt():
    """Läuft der Aufrufer (weiter) mitten in Python-Code statt aus Qts Ereignisschleife – und
    ohne modales Fenster, das seine eigene Schleife hat? Wie camaddon.uhren.verschachtelt."""
    try:
        sys._getframe(2)
    except ValueError:  # nichts darunter: aus der Ereignisschleife
        return False
    return QtGui.QApplication.activeModalWidget() is None


class _Sonde:
    """Eine Uhr im Hauptthread (alle 20 ms) und ein Wachhund daneben: Tickt die Uhr länger als
    PAUSE_AB nicht, sieht er alle 50 ms in den Python-Stapel des Hauptthreads – je Pause der
    Auslöser (die äußersten Rahmen aus Addon oder Szenario) und wo es darin am meisten rechnete; je
    Auslöser die längste Pause. Rechnet der Hauptthread in C++ (OpenCascade) ohne die GIL
    freizugeben, sieht der Wachhund die Stelle erst danach – meist noch dieselbe Funktion."""

    def __init__(self):
        self.zuletzt = time.perf_counter()
        self.laengste = 0.0
        self.stellen = {}  # Auslöser -> [längste Pause, wie viele Pausen, wo es darin rechnete]
        self.uhr = QtCore.QTimer()
        self.uhr.setInterval(20)
        self.uhr.timeout.connect(self._tick)
        self.uhr.start()
        self._haupt = threading.main_thread().ident
        self._aus = False
        threading.Thread(target=self._wachen, daemon=True).start()

    def _tick(self):
        jetzt = time.perf_counter()
        self.laengste = max(self.laengste, jetzt - self.zuletzt)
        self.zuletzt = jetzt

    def _wachen(self):
        pause = None  # [Beginn, Auslöser → [Proben], innen → Proben]
        while not self._aus:
            time.sleep(0.05)
            stehen = time.perf_counter() - self.zuletzt
            if stehen < PAUSE_AB:
                if pause is not None:
                    self._pause_fertig(pause)
                    pause = None
                continue
            rahmen = sys._current_frames().get(self._haupt)
            if rahmen is None:
                continue
            zeilen = [
                f"{os.path.basename(f.filename)}:{f.lineno} {f.name}"
                for f in traceback.extract_stack(rahmen)
                if "camaddon" in f.filename or "szenario_" in f.filename
            ]
            if pause is None or pause[0] != self.zuletzt:
                if pause is not None:
                    self._pause_fertig(pause)
                pause = [self.zuletzt, {}, {}]
            # Auslöser: die äußersten zwei Rahmen aus Addon oder Szenario; innen: der innerste.
            ausloeser = " → ".join(zeilen[:2]) or "(außerhalb des Addons)"
            innen = zeilen[-1] if zeilen else "(außerhalb des Addons)"
            pause[1][ausloeser] = pause[1].get(ausloeser, 0) + 1
            pause[2][innen] = pause[2].get(innen, 0) + 1
            pause.append(stehen)

    def _pause_fertig(self, pause):
        dauer = max(pause[3:], default=0.0) + 0.05
        ausloeser = max(pause[1], key=pause[1].get)
        innen = sorted(pause[2].items(), key=lambda e: -e[1])[:4]
        eintrag = self.stellen.setdefault(ausloeser, [0.0, 0, []])
        if dauer > eintrag[0]:
            eintrag[0] = dauer
            eintrag[2] = innen
        eintrag[1] += 1

    def schreiben(self):
        self._aus = True
        self.uhr.stop()
        zeilen = [f"längste Pause: {self.laengste:.2f} s"]
        for ausloeser, (dauer, wie_oft, innen) in sorted(
            self.stellen.items(), key=lambda e: -e[1][0]
        ):
            zeilen.append(f"{dauer:6.2f} s ({wie_oft:2d}×)  {ausloeser}")
            for stelle, proben in innen:
                zeilen.append(f"            {proben:4d} Proben  {stelle}")
        with open(os.path.join(AUSGABE, "pausen.txt"), "w", encoding="utf-8") as datei:
            datei.write("\n".join(zeilen) + "\n")


class _Bahnen:
    """Merkt sich die Bahn jeder CAM-Operation, die neu rechnet (eine Kopie, billig) – am Ende
    zählt _kehren_schreiben darin die Rampen hin und her (Manuel, 2026-10-16: „schau dir alle
    szenarien und bahngeneratoren nochmal genauer an das auch wirklich alle zickzack fahrten weg
    sind“). Gezählt wird erst am Ende: Die Lag-Sonde soll davon nichts merken."""

    def __init__(self):
        self.je_operation = {}  # „Dokument/Label“ → Path.Path

    def slotRecomputedObject(self, obj):
        try:
            if "Path" not in obj.PropertiesList or "ToolController" not in obj.PropertiesList:
                return
            self.je_operation[f"{obj.Document.Name}/{obj.Label}"] = obj.Path.copy()
        except Exception:  # noqa: BLE001 – ein Objekt im Abbau
            return


def _kehren_schreiben():
    """kehren.txt: je Operation Kehren und Rampen, die mit Kehren zuerst."""
    bahnen = getattr(starten, "bahnen", None)
    if bahnen is None:
        return
    try:
        from camaddon import pruefstand as ps
    except Exception:  # noqa: BLE001
        return
    zeilen = []
    for name, bahn in sorted(bahnen.je_operation.items()):
        orte = []
        try:
            ergebnis = ps.kehren_im_programm(bahn.Commands, orte)
        except Exception as fehler:  # noqa: BLE001
            zeilen.append((-1, f"{name}: nicht gezählt ({fehler})"))
            continue
        if ergebnis is None:
            zeilen.append((-1, f"{name}: Rundachse – nicht gezählt"))
            continue
        kehren, rampen = ergebnis
        if kehren:  # zum Nachsehen: das Programm der Operation
            datei_name = "".join(c if c.isalnum() else "_" for c in name) + ".nc"
            with open(os.path.join(AUSGABE, datei_name), "w", encoding="utf-8") as programm:
                programm.write(bahn.toGCode())
        wo = "; ".join(f"X{x:.2f} Y{y:.2f} Z{z:.2f}" for x, y, z in orte[:3])
        zeilen.append(
            (
                kehren,
                f"Kehren {kehren:3d}  Rampen {rampen:3d}  {name}" + (f"  bei {wo}" if wo else ""),
            )
        )
    zeilen.sort(key=lambda z: -z[0])
    with open(os.path.join(AUSGABE, "kehren.txt"), "w", encoding="utf-8") as datei:
        datei.write("\n".join(z[1] for z in zeilen) + ("\n" if zeilen else ""))


def _ende(helfer, fehler=None):
    if fehler:
        helfer.fehler.append(fehler)
    sonde = getattr(starten, "sonde", None)
    if sonde is not None:
        sonde.schreiben()
    _kehren_schreiben()
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
    starten.sonde = _Sonde()
    starten.bahnen = _Bahnen()
    FreeCAD.addDocumentObserver(starten.bahnen)

    def weiter():
        # Mitten in einer Rechnung des Addons (FreeCAD 26.3 arbeitet in booleschen Operationen
        # Ereignisse ab) noch nicht – ein Mensch kann dann auch nicht klicken (P-2026-10-10-45).
        if _verschachtelt():
            QtCore.QTimer.singleShot(50, weiter)
            return
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
