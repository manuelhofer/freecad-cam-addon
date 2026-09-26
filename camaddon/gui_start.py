# SPDX-License-Identifier: LGPL-2.1-or-later
"""Anmeldung des Addons in der FreeCAD-Oberfläche; InitGui.py ruft `starten()` auf.

Das Addon hat keinen eigenen Arbeitsbereich: Die Maschine wird in einer
Assembly gebaut und in CAM benutzt, also hängt eine Werkzeugleiste an genau
diesen beiden Arbeitsbereichen – über die öffentliche Python-Schnittstelle
der Arbeitsbereiche, nichts an FreeCAD wird überschrieben.
"""

import html

import FreeCAD
import FreeCADGui
from PySide import QtGui

from . import (
    VERSION,
    gui_aktualisierung,
    gui_job_schnittwerte,
    gui_maschine,
    gui_neue_maschine,
    gui_sprachwahl,
    gui_verfahren,
    gui_werkzeuge,
    sprache,
    symbol,
)
from .sprache import tr

# Arbeitsbereiche, an die die Werkzeugleiste angehängt wird.
ZIEL_ARBEITSBEREICHE = ("AssemblyWorkbench", "CAMWorkbench")

# Die Werkzeugleiste heißt in jeder Sprache gleich: An ihrem Namen erkennt
# _werkzeugleiste_anhaengen(), dass sie schon hängt – auch nach einer Sprachwahl.
WERKZEUGLEISTE_NAME = "CAM-Addon"

# Befehle der Werkzeugleiste, in Anzeigereihenfolge.
WERKZEUGLEISTE = [
    "CamAddon_NeueMaschine",
    "CamAddon_MaschineBearbeiten",
    "CamAddon_MaschineVerfahren",
    "CamAddon_Werkzeugverwaltung",
    "CamAddon_SchnittwerteJob",
    "CamAddon_Ueber",
    "CamAddon_UpdateSuchen",
]


def starten():
    """Meldet Befehle, Werkzeugleiste und Einstellungsseite an, fragt beim ersten
    Start nach der Sprache und sucht nach Updates, falls das eingeschaltet ist."""
    BEFEHLE.update(
        {
            "CamAddon_NeueMaschine": gui_neue_maschine.BefehlNeueMaschine(),
            "CamAddon_MaschineBearbeiten": gui_maschine.BefehlMaschineBearbeiten(),
            "CamAddon_MaschineVerfahren": gui_verfahren.BefehlMaschineVerfahren(),
            "CamAddon_Werkzeugverwaltung": gui_werkzeuge.BefehlWerkzeugverwaltung(),
            "CamAddon_SchnittwerteJob": gui_job_schnittwerte.BefehlSchnittwerteJob(),
            "CamAddon_Ueber": BefehlUeber(),
            "CamAddon_UpdateSuchen": gui_aktualisierung.BefehlUpdateSuchen(),
        }
    )
    for name, befehl in BEFEHLE.items():
        FreeCADGui.addCommand(name, befehl)
    _TEXTE["gelesen_in"] = sprache.aktuelle_sprache()
    gui_sprachwahl.NACH_SPRACHWAHL.append(befehle_beschriften)
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


BEFEHLE = {}  # Name → Befehl, in Anzeigereihenfolge
# In welcher Sprache FreeCAD die Texte der Befehle gelesen hat, und ob sie seither
# umgeschrieben wurden.
_TEXTE = {"gelesen_in": None, "umgeschrieben": False}


def befehle_beschriften():
    """Schreibt die Texte der Befehle in der gewählten Sprache an ihre Knöpfe.

    FreeCAD liest Name und Tooltip eines Befehls nur einmal, beim Anmelden –
    beim ersten Start also vor der Sprachwahl. Ohne das stünden bis zum
    Neustart die Texte in der alten Sprache da.
    """
    if _TEXTE["gelesen_in"] is None:
        return
    if sprache.aktuelle_sprache() == _TEXTE["gelesen_in"] and not _TEXTE["umgeschrieben"]:
        return  # stimmen schon – FreeCADs eigene Tooltips bleiben unberührt
    _TEXTE["umgeschrieben"] = True
    for name, befehl in BEFEHLE.items():
        daten = befehl.GetResources()
        freecad_befehl = FreeCADGui.Command.get(name)
        for aktion in freecad_befehl.getAction() if freecad_befehl is not None else []:
            aktion.setText(daten["MenuText"])
            aktion.setToolTip(_tooltip(daten["MenuText"], daten["ToolTip"], name))
            aktion.setStatusTip(daten["ToolTip"])


def _tooltip(titel, text, name):
    """Tooltip wie bei FreeCAD: Titel fett, Text, Befehlsname kursiv."""
    return (
        f"<p style='white-space:pre; margin-bottom:0.5em;'><b>{html.escape(titel)}</b></p>"
        f"<p style='margin:0;'>{html.escape(text)}</p>"
        f"<p style='white-space:pre; margin-top:0.5em;'><i>{html.escape(name)}</i></p>"
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
    if WERKZEUGLEISTE_NAME not in arbeitsbereich.listToolbars():
        arbeitsbereich.appendToolbar(WERKZEUGLEISTE_NAME, WERKZEUGLEISTE)
        arbeitsbereich.reloadActive()  # erst danach erscheint die neue Leiste
    # Neue Knöpfe legt FreeCAD mit den Texten vom Start an.
    befehle_beschriften()
