# SPDX-License-Identifier: LGPL-2.1-or-later
"""Anzeige der Operation „Rundum schruppen“ (Spezifikation W-003, Abschnitt 10,
Stufe V3c): Symbol im Baum, die Bahn zeichnet FreeCAD selbst. Zu bearbeiten
gibt es noch nichts im Fenster – die Werte stehen in den Eigenschaften (Gruppe
„4-Achs“); ein Doppelklick ändert nichts.

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

    def doubleClicked(self, _ansicht):
        return True  # nichts öffnen: Die Werte stehen in den Eigenschaften

    def onDelete(self, _ansicht, _unterelemente):
        return True
