# SPDX-License-Identifier: LGPL-2.1-or-later
"""Anzeige der Operationen des Addons (Spezifikation W-003, Abschnitt 10, Stufe V3c):
Symbol im Baum, die Bahn zeichnet FreeCAD selbst. Doppelklick oder „Bearbeiten“ im
Kontextmenü öffnet den Assistenten mit ihren Werten (Manuel, 2026-09-29: „komme ich nicht
mehr in die maske rein … muss irgendwie gelöst werden das man im nachhinein noch sachen
ändern kann“) – „4-Achs-Bearbeitung“ für die Rundum-Operationen, „Bearbeitung (Fräsen)“ für
„Planfräsen“ und „Kontur“ (W-006 S3c, S3e).

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben.
"""

from . import symbol


def _ist_eben(objekt):
    """Eine 2,5D-Operation (Planfräsen, Kontur) – ihr Assistent ist „Bearbeitung (Fräsen)“."""
    from . import kontur as ko
    from . import planfraesen as pf
    from . import raeumen as ra

    return pf.ist_planfraesen(objekt) or ko.ist_kontur(objekt) or ra.ist_raeumen(objekt)


def bearbeiten(objekt):
    """Öffnet den Assistenten, der zu dieser Operation gehört, zum Ändern."""
    if _ist_eben(objekt):
        from . import gui_bearbeitung

        gui_bearbeitung.bearbeiten(objekt)
    else:
        from . import gui_vierachs

        gui_vierachs.bearbeiten(objekt)


class Ansicht:
    """Proxy der Anzeige (ViewObject.Proxy)."""

    def __init__(self, ansicht):
        ansicht.Proxy = self
        self.Object = ansicht.Object

    def attach(self, ansicht):
        self.Object = ansicht.Object

    def getIcon(self):
        return symbol("bearbeitung.svg" if _ist_eben(self.Object) else "vierachs.svg")

    def dumps(self):
        return None

    def loads(self, _zustand):
        return None

    def doubleClicked(self, ansicht):
        bearbeiten(ansicht.Object)
        return True

    def setupContextMenu(self, ansicht, menue):
        from PySide import QtGui

        from .sprache import tr

        aktion = QtGui.QAction(tr("vo.bearbeiten"), menue)
        aktion.triggered.connect(lambda _an=False: bearbeiten(ansicht.Object))
        menue.addAction(aktion)

    def onDelete(self, _ansicht, _unterelemente):
        return True
