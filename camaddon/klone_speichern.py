# SPDX-License-Identifier: LGPL-2.1-or-later
"""Schwere Modellklone speichern ihre Form nicht mit (W-017).

Ein Teil aus einem STL liegt in jedem Job als Klon (Draft) im Modell – am Geist je 51,5 MB BREP,
in der 8-Eck-Kette achtmal. FreeCAD schrieb beim Speichern jede dieser Formen mit: am Geist mit
einem Job 6,2 statt 3,6 s, in denen das Fenster stand, 38,7 statt 22,9 MB; Öffnen 1,1 statt
0,7 s. Die Form eines solchen Klons ist genau die seines Vorbilds an seiner eigenen Lage
(nebenrechner.schwere_klone). Darum ist seine Eigenschaft „Shape“ für die Dauer des Speicherns
„Transient“ – das merkt sich die Datei –, und nach dem Öffnen bekommt er die Form aus dem Vorbild
zurück (nebenrechner.klone_herstellen, wie in den Arbeitern); das Dokument gilt danach als
unverändert.

Ohne das Addon geöffnet ist so ein Klon leer (sein Vorbild ist im Dokument, nur ausgeblendet);
„Neu berechnen“ am Klon stellt ihn wieder her. Abschaltbar in den Einstellungen (an()).
"""

import contextlib

import FreeCAD

from . import PARAMETER_PFAD

EINSTELLUNG = "KloneOhneForm"
NACHSEHEN_MS = 100  # so oft schaut es nach, ob FreeCAD mit dem Öffnen fertig ist
_BEOBACHTER = []


def an():
    """Speichern schwere Klone ihre Form nicht mit? (Einstellung, vorbelegt an)"""
    return FreeCAD.ParamGet(PARAMETER_PFAD).GetBool(EINSTELLUNG, True)


def setzen(wert):
    FreeCAD.ParamGet(PARAMETER_PFAD).SetBool(EINSTELLUNG, bool(wert))


def ohne_form(klone):
    """Die Klone speichern ihre Form nicht (bis form_wieder)."""
    for klon in klone:
        klon.setPropertyStatus("Shape", "Transient")


def form_wieder(klone):
    for klon in klone:
        with contextlib.suppress(Exception):  # inzwischen gelöscht
            klon.setPropertyStatus("Shape", "-Transient")


def nach_dem_oeffnen(dokument):
    """Gibt den Klonen im Dokument, die ohne Form gespeichert sind, ihre Form zurück – das
    Dokument gilt danach als so unverändert wie vorher. Gibt die Zahl zurück."""
    from . import nebenrechner as nr

    offen = [
        o
        for o in dokument.Objects
        if "Shape" in o.PropertiesList and "Transient" in o.getPropertyStatus("Shape")
    ]
    if not offen:
        return 0
    ansicht = _ansicht(dokument)
    geaendert = getattr(ansicht, "Modified", None)
    hergestellt = nr.klone_herstellen(dokument)
    form_wieder([o for o in offen if not o.Shape.isNull()])
    if ansicht is not None and geaendert is not None:
        with contextlib.suppress(Exception):
            ansicht.Modified = geaendert
    return hergestellt


def _ansicht(dokument):
    try:
        import FreeCADGui

        return FreeCADGui.getDocument(dokument.Name)
    except Exception:  # noqa: BLE001 – ohne Oberfläche
        return None


class _Beobachter:
    def __init__(self):
        self._gesetzt = {}  # Dokument (Name) -> die Klone, die beim Speichern ohne Form sind

    def slotStartSaveDocument(self, dokument, _datei):
        if not an():
            return
        from . import nebenrechner as nr

        try:
            klone = nr.schwere_klone(dokument)
        except Exception:  # noqa: BLE001 – im Zweifel speichert FreeCAD alles
            return
        ohne_form(klone)
        self._gesetzt[dokument.Name] = klone

    def slotFinishSaveDocument(self, dokument, _datei):
        klone = self._gesetzt.pop(dokument.Name, [])
        if klone:
            _nach_dem_speichern(dokument.Name, klone)

    def slotCreatedDocument(self, dokument):
        # Beim Öffnen liest FreeCAD danach erst die Objekte – nachsehen, wenn es fertig ist.
        _spaeter(dokument.Name)


def _nach_dem_speichern(name, klone):
    """Die Klone speichern wieder mit – erst wenn FreeCAD mit dem Speichern fertig ist: Den Status
    einer Eigenschaft zu ändern, zählt in der Oberfläche als Änderung; mitten im Speichern stand das
    Dokument danach als „geändert“ da. Der Merker bleibt, wie FreeCAD ihn gesetzt hat."""
    try:
        from PySide import QtCore, QtGui

        mit_oberflaeche = QtGui.QApplication.instance() is not None
    except ImportError:
        mit_oberflaeche = False
    if not mit_oberflaeche:
        form_wieder(klone)
        return

    def wieder():
        dokument = FreeCAD.listDocuments().get(name)
        ansicht = _ansicht(dokument) if dokument is not None else None
        geaendert = getattr(ansicht, "Modified", None)
        form_wieder(klone)
        if ansicht is not None and geaendert is not None:
            with contextlib.suppress(Exception):
                ansicht.Modified = geaendert

    QtCore.QTimer.singleShot(0, wieder)


def _spaeter(name):
    from PySide import QtCore

    def nachsehen():
        dokument = FreeCAD.listDocuments().get(name)
        if dokument is None:
            return
        if getattr(dokument, "Restoring", False):
            QtCore.QTimer.singleShot(NACHSEHEN_MS, nachsehen)
            return
        try:
            nach_dem_oeffnen(dokument)
        except Exception as fehler:  # noqa: BLE001 – ein Fehler hier darf das Öffnen nicht stören
            FreeCAD.Console.PrintWarning(f"CAM-Addon: Klone nach dem Öffnen: {fehler}\n")

    QtCore.QTimer.singleShot(0, nachsehen)


def beobachten():
    """Meldet den Beobachter einmal an (gui_start.starten)."""
    if not _BEOBACHTER:
        _BEOBACHTER.append(_Beobachter())
        FreeCAD.addDocumentObserver(_BEOBACHTER[0])
