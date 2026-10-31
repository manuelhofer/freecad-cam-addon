# SPDX-License-Identifier: LGPL-2.1-or-later
"""Anmeldung des Addons in der FreeCAD-Oberfläche; InitGui.py ruft `starten()` auf.

Das Addon hat keinen eigenen Arbeitsbereich: Die Maschine wird in einer
Assembly gebaut und in CAM benutzt, also hängen eine Werkzeugleiste und ein
Menü an genau diesen beiden Arbeitsbereichen – über die öffentliche
Python-Schnittstelle der Arbeitsbereiche, nichts an FreeCAD wird überschrieben.
"""

import contextlib
import html

import FreeCAD
import FreeCADGui
from PySide import QtGui

from . import (
    VERSION,
    aufraeumen,
    gui_aktualisierung,
    gui_bearbeitung,
    gui_beispiele,
    gui_bestueckung,
    gui_einrichtblatt,
    gui_fertigteil,
    gui_halter,
    gui_hilfe,
    gui_job_schnittwerte,
    gui_maschine,
    gui_maschinen,
    gui_materialstand,
    gui_neue_maschine,
    gui_programm,
    gui_reichweite,
    gui_schwenken,
    gui_simultan_planung,
    gui_spannmittel,
    gui_sprachwahl,
    gui_verfahren,
    gui_vierachs,
    gui_werkzeuge,
    klone_speichern,
    sprache,
    stl_anzeige,
    symbol,
)
from .sprache import tr

# Arbeitsbereiche, an die die Werkzeugleiste angehängt wird.
ZIEL_ARBEITSBEREICHE = ("AssemblyWorkbench", "CAMWorkbench")

# Werkzeugleiste und Menü heißen in jeder Sprache gleich: An ihrem Namen erkennt
# _werkzeugleiste_anhaengen(), dass sie schon hängen – auch nach einer Sprachwahl.
WERKZEUGLEISTE_NAME = "CAM-Addon"
MENUE_NAME = "CAM-Addon"

# Die Arbeitsbefehle – in der Werkzeugleiste, in Anzeigereihenfolge.
WERKZEUGLEISTE = [
    "CamAddon_NeueMaschine",
    "CamAddon_MaschineBearbeiten",
    "CamAddon_MaschineVerfahren",
    "CamAddon_Werkzeugverwaltung",
    "CamAddon_Halter",
    "CamAddon_Spannmittel",
    "CamAddon_SchnittwerteJob",
    "CamAddon_Bestueckung",
    "CamAddon_AufMaschinePruefen",
    "CamAddon_Vierachs",
    "CamAddon_Bearbeitung",
    "CamAddon_Schwenken",
    "CamAddon_SimultanPlanen",
    "CamAddon_ProgrammSchreiben",
]
# Das Menü: oben „So geht’s“ (D-54), dann alle Befehle mit Text – auch „Nach Updates
# suchen“ und „Über“, die in der Werkzeugleiste nur Platz kosteten (Durchsicht W-004, D-13).
MENUE = [
    "CamAddon_SoGehts",
    "Separator",
    "CamAddon_Maschinen",
    "CamAddon_NeueMaschine",
    "CamAddon_MaschineBearbeiten",
    "CamAddon_MaschineVerfahren",
    "Separator",
    "CamAddon_Werkzeugverwaltung",
    "CamAddon_Halter",
    "CamAddon_Spannmittel",
    "CamAddon_SchnittwerteJob",
    "CamAddon_Bestueckung",
    "CamAddon_AufMaschinePruefen",
    "CamAddon_Vierachs",
    "CamAddon_Bearbeitung",
    "CamAddon_Schwenken",
    "CamAddon_SimultanPlanen",
    "CamAddon_ProgrammSchreiben",
    "CamAddon_Einrichtblatt",
    "CamAddon_Fertigteil",
    "Separator",
    "CamAddon_BeispieleLaden",
    "CamAddon_UpdateSuchen",
    "CamAddon_Ueber",
]


def starten():
    """Meldet Befehle, Werkzeugleiste und Einstellungsseite an, fragt beim ersten
    Start nach der Sprache und sucht nach Updates, falls das eingeschaltet ist."""
    BEFEHLE.update(
        {
            "CamAddon_SoGehts": gui_hilfe.BefehlSoGehts(),
            "CamAddon_Maschinen": gui_maschinen.BefehlMaschinen(),
            "CamAddon_NeueMaschine": gui_neue_maschine.BefehlNeueMaschine(),
            "CamAddon_MaschineBearbeiten": gui_maschine.BefehlMaschineBearbeiten(),
            "CamAddon_MaschineVerfahren": gui_verfahren.BefehlMaschineVerfahren(),
            "CamAddon_Werkzeugverwaltung": gui_werkzeuge.BefehlWerkzeugverwaltung(),
            "CamAddon_Halter": gui_halter.BefehlHalter(),
            "CamAddon_Spannmittel": gui_spannmittel.BefehlSpannmittel(),
            "CamAddon_SchnittwerteJob": gui_job_schnittwerte.BefehlSchnittwerteJob(),
            "CamAddon_Bestueckung": gui_bestueckung.BefehlBestueckung(),
            "CamAddon_AufMaschinePruefen": gui_reichweite.BefehlAufMaschinePruefen(),
            "CamAddon_Vierachs": gui_vierachs.BefehlVierachs(),
            "CamAddon_Bearbeitung": gui_bearbeitung.BefehlBearbeitung(),
            "CamAddon_Schwenken": gui_schwenken.BefehlSchwenken(),
            "CamAddon_SimultanPlanen": gui_simultan_planung.BefehlSimultanPlanen(),
            "CamAddon_ProgrammSchreiben": gui_programm.BefehlProgrammSchreiben(),
            "CamAddon_Einrichtblatt": gui_einrichtblatt.BefehlEinrichtblatt(),
            "CamAddon_Fertigteil": gui_fertigteil.BefehlFertigteil(),
            "CamAddon_Ueber": BefehlUeber(),
            "CamAddon_UpdateSuchen": gui_aktualisierung.BefehlUpdateSuchen(),
            "CamAddon_BeispieleLaden": gui_beispiele.BefehlBeispieleLaden(),
        }
    )
    from . import gui_bearbeitung_beta

    # Die Beta (Manuel, 2026-10-30: „dass wir erstmal das Alte behalten …, und wir noch einen
    # Beta-Bereich reinmachen“): angemeldet immer, in Leiste und Menü nur, wenn eingeschaltet.
    BEFEHLE.update({name: klasse() for name, klasse in gui_bearbeitung_beta.BEFEHLE.items()})
    for name, befehl in BEFEHLE.items():
        FreeCADGui.addCommand(name, befehl)
    _TEXTE["gelesen_in"] = sprache.aktuelle_sprache()
    gui_sprachwahl.NACH_SPRACHWAHL.append(befehle_beschriften)
    FreeCADGui.getMainWindow().workbenchActivated.connect(_werkzeugleiste_anhaengen)
    gui_sprachwahl.einstellungsseite_anmelden()
    gui_maschinen.beobachten()  # gespeicherte Maschinen kommen in die Liste (W-011)
    gui_materialstand.beobachten()  # Operationen mit Materialstand rechnen nach (W-012)
    aufraeumen.beobachten()  # verwaiste Klone nach einem Rückgängig (B-016)
    klone_speichern.beobachten()  # schwere Modellklone ohne ihre Form speichern (W-017)
    stl_anzeige.beobachten()  # ein Teil aus einem STL als Netz (W-017)
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


def beta_umgeschaltet():
    """Die Beta in den Einstellungen ein- oder ausgeschaltet: gleich im aktiven Arbeitsbereich."""
    with contextlib.suppress(Exception):
        _werkzeugleiste_anhaengen(FreeCADGui.activeWorkbench().name())


def _werkzeugleiste_anhaengen(name_arbeitsbereich):
    """Hängt Werkzeugleiste und Menü an, sobald ein Ziel-Arbeitsbereich aktiv wird.

    Ein WorkbenchManipulator kann nur an vorhandene Werkzeugleisten anhängen,
    keine neue anlegen (ausprobiert, P-2026-09-25-12) – deshalb der Weg über
    appendToolbar und appendMenu des Arbeitsbereichs, einmal je Arbeitsbereich.
    """
    if name_arbeitsbereich not in ZIEL_ARBEITSBEREICHE:
        return
    arbeitsbereich = FreeCADGui.getWorkbench(name_arbeitsbereich)
    neu = False
    if WERKZEUGLEISTE_NAME not in arbeitsbereich.listToolbars():
        arbeitsbereich.appendToolbar(WERKZEUGLEISTE_NAME, WERKZEUGLEISTE)
        neu = True
    if MENUE_NAME not in arbeitsbereich.listMenus():
        arbeitsbereich.appendMenu(MENUE_NAME, MENUE)
        neu = True
    from . import gui_bearbeitung_beta

    if gui_bearbeitung_beta.leiste_anhaengen(arbeitsbereich):
        neu = True
    if neu:
        arbeitsbereich.reloadActive()  # erst danach erscheinen Leiste und Menü
    # Neue Knöpfe legt FreeCAD mit den Texten vom Start an.
    befehle_beschriften()
