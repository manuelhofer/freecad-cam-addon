# SPDX-License-Identifier: LGPL-2.1-or-later
"""Anmeldung des Addons in der FreeCAD-Oberfläche; InitGui.py ruft `starten()` auf.

Das Addon hat keinen eigenen Arbeitsbereich: Die Maschine wird in einer
Assembly gebaut und in CAM benutzt, also hängt eine Werkzeugleiste an genau
diesen beiden Arbeitsbereichen – über die öffentliche Python-Schnittstelle
der Arbeitsbereiche, nichts an FreeCAD wird überschrieben.
"""

import FreeCAD
import FreeCADGui
from PySide import QtGui

from . import (
    VERSION,
    gui_aktualisierung,
    gui_job_schnittwerte,
    gui_maschine,
    gui_sprachwahl,
    gui_werkzeuge,
    symbol,
)
from .sprache import tr

# Arbeitsbereiche, an die die Werkzeugleiste angehängt wird.
ZIEL_ARBEITSBEREICHE = ("AssemblyWorkbench", "CAMWorkbench")

# Befehle der Werkzeugleiste, in Anzeigereihenfolge.
WERKZEUGLEISTE = [
    "CamAddon_MaschineBearbeiten",
    "CamAddon_Werkzeugverwaltung",
    "CamAddon_SchnittwerteJob",
    "CamAddon_Ueber",
]


def starten():
    """Meldet Befehle, Werkzeugleiste und Einstellungsseite an, fragt beim ersten
    Start nach der Sprache und sucht im Hintergrund nach Updates."""
    FreeCADGui.addCommand("CamAddon_MaschineBearbeiten", gui_maschine.BefehlMaschineBearbeiten())
    FreeCADGui.addCommand("CamAddon_Werkzeugverwaltung", gui_werkzeuge.BefehlWerkzeugverwaltung())
    FreeCADGui.addCommand("CamAddon_SchnittwerteJob", gui_job_schnittwerte.BefehlSchnittwerteJob())
    FreeCADGui.addCommand("CamAddon_Ueber", BefehlUeber())
    FreeCADGui.getMainWindow().workbenchActivated.connect(_werkzeugleiste_anhaengen)
    gui_sprachwahl.einstellungsseite_anmelden()
    gui_sprachwahl.beim_ersten_start_fragen()
    gui_aktualisierung.beim_start()
    FreeCAD.Console.PrintLog("CAM-Addon geladen\n")


class BefehlUeber:
    """Zeigt Name, Version und Kurzbeschreibung des Addons."""

    def GetResources(self):
        return {
            "Pixmap": symbol("camaddon.svg"),
            "MenuText": tr("befehl.ueber.titel"),
            "ToolTip": tr("befehl.ueber.tooltip"),
        }

    def IsActive(self):
        return True

    def Activated(self):
        QtGui.QMessageBox.about(
            FreeCADGui.getMainWindow(), tr("befehl.ueber.titel"), tr("ueber.text", version=VERSION)
        )


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
    arbeitsbereich.reloadActive()  # erst danach erscheint die neue Leiste
