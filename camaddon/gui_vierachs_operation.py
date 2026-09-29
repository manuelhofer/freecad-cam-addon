# SPDX-License-Identifier: LGPL-2.1-or-later
"""Anzeige der Operation „Rundum schruppen“ (Spezifikation W-003, Abschnitt 10,
Stufe V3c): Symbol im Baum, die Bahn zeichnet FreeCAD selbst. Doppelklick oder
„Bearbeiten“ im Kontextmenü öffnet den Assistenten „4-Achs-Bearbeitung“ mit
ihren Werten (Manuel, 2026-09-29: „komme ich nicht mehr in die maske rein … muss
irgendwie gelöst werden das man im nachhinein noch sachen ändern kann“).

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben.
"""

from . import symbol


class Ansicht:
    """Proxy der Anzeige (ViewObject.Proxy)."""

    def __init__(self, ansicht):
        ansicht.Proxy = self
        self.Object = ansicht.Object

    def attach(self, ansicht):
        self.Object = ansicht.Object

    def getIcon(self):
        return symbol("vierachs.svg")

    def dumps(self):
        return None

    def loads(self, _zustand):
        return None

    def doubleClicked(self, ansicht):
        from . import gui_vierachs

        gui_vierachs.bearbeiten(ansicht.Object)
        return True

    def setupContextMenu(self, ansicht, menue):
        from PySide import QtGui

        from . import gui_vierachs
        from .sprache import tr

        aktion = QtGui.QAction(tr("vo.bearbeiten"), menue)
        aktion.triggered.connect(lambda _an=False: gui_vierachs.bearbeiten(ansicht.Object))
        menue.addAction(aktion)

    def onDelete(self, _ansicht, _unterelemente):
        return True
