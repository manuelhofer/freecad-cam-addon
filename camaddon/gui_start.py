# SPDX-License-Identifier: LGPL-2.1-or-later
"""Anmeldung des Addons in der FreeCAD-Oberfläche.

Das Addon hat keinen eigenen Arbeitsbereich: Die Maschine wird in einer
Assembly gebaut und in CAM benutzt, also hängt eine Werkzeugleiste an genau
diesen beiden Arbeitsbereichen (über die öffentliche Python-Schnittstelle der
Arbeitsbereiche – nichts an FreeCAD wird überschrieben).
"""

import os

import FreeCAD
import FreeCADGui

from . import ADDON_ORDNER
from .sprache import tr

SYMBOL_ORDNER = os.path.join(ADDON_ORDNER, "resources", "icons")

# Arbeitsbereiche, an die die Werkzeugleiste angehängt wird.
ZIEL_ARBEITSBEREICHE = ("AssemblyWorkbench", "CAMWorkbench")

# Befehle der Werkzeugleiste, in Anzeigereihenfolge.
WERKZEUGLEISTE = ["CamAddon_MaschineBearbeiten", "CamAddon_Ueber"]


def symbol(name):
    return os.path.join(SYMBOL_ORDNER, name)


class BefehlUeber:
    """Zeigt Name, Version und Kurzbeschreibung des Addons."""

    def GetResources(self):
        return {
            "Pixmap": symbol("camaddon.svg"),
            "MenuText": tr("befehl.ueber.titel"),
            "ToolTip": tr("befehl.ueber.tooltip"),
        }

    def Activated(self):
        from PySide import QtGui

        from . import VERSION

        QtGui.QMessageBox.about(
            FreeCADGui.getMainWindow(),
            tr("befehl.ueber.titel"),
            tr("ueber.text", version=VERSION),
        )

    def IsActive(self):
        return True


def _werkzeugleiste_anhaengen(name_arbeitsbereich):
    """Hängt die Werkzeugleiste an, sobald ein Ziel-Arbeitsbereich aktiv wird.

    Ein WorkbenchManipulator kann nur an vorhandene Werkzeugleisten anhängen,
    keine neue anlegen (ausprobiert, P-2026-09-25-12) – deshalb der Weg über
    appendToolbar des Arbeitsbereichs, einmal je Arbeitsbereich.
    """
    if name_arbeitsbereich not in ZIEL_ARBEITSBEREICHE:
        return
    arbeitsbereich = FreeCADGui.getWorkbench(name_arbeitsbereich)
    name = tr("werkzeugleiste.name")
    if name in arbeitsbereich.listToolbars():
        return
    arbeitsbereich.appendToolbar(name, WERKZEUGLEISTE)
    # Erst nach dem Neuladen erscheint die neue Leiste.
    arbeitsbereich.reloadActive()


def starten():
    from . import gui_maschine

    FreeCADGui.addCommand("CamAddon_MaschineBearbeiten", gui_maschine.BefehlMaschineBearbeiten())
    FreeCADGui.addCommand("CamAddon_Ueber", BefehlUeber())
    FreeCADGui.getMainWindow().workbenchActivated.connect(_werkzeugleiste_anhaengen)

    from . import gui_sprachwahl

    gui_sprachwahl.einstellungsseite_anmelden()
    gui_sprachwahl.beim_ersten_start_fragen()
    FreeCAD.Console.PrintLog("CAM-Addon geladen\n")
