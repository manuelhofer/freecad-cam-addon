# SPDX-License-Identifier: LGPL-2.1-or-later
"""CAM-Addon für FreeCAD.

Module ohne „gui“ im Namen laufen auch ohne Oberfläche (FreeCADCmd) und
werden so getestet; nur die gui_*-Module brauchen FreeCADGui. Welches Modul
wofür zuständig ist, steht in docs/aufbau.md.
"""

import logging
import os
import xml.etree.ElementTree as ET

# Diese Logger schreiben Debug-Zeilen, die CAM selbst nie zeigen will (cam_protokoll_leiser).
LEISE_LOGGER = ("Path.Tool.assets", "asyncio")


def cam_protokoll_leiser():
    """CAMs Werkzeugverwaltung (`Path.Tool.assets`) schreibt bei jedem Zugriff Debug-Zeilen über
    Pythons logging, asyncio dazu „Using selector“. CAM will davon nur Fehler sehen (manager.py:
    `logging.basicConfig(level=ERROR)`) – das wirkt aber nur, wenn noch niemand das Logging
    eingestellt hat. Hat ein anderes Addon es auf DEBUG gestellt, kommt jede Zeile als roter
    Fehler ins Ausgabefenster und als Popup – über hundert beim Wechsel nach CAM und beim
    Anlegen eines Jobs (Herbert im Forum, 2026-10-11; nachgestellt: 101 Zeilen). Ohne das Addon
    sah er sie nicht: Es lädt CAMs Werkzeugverwaltung schon beim Start mit (seine Operationen
    importieren `Path.Op.Base`). Diese Logger bleiben darum bei Warnungen – gleich hier, vor
    jedem Import aus CAM; außer jemand hat sie ausdrücklich eingestellt (P-2026-10-12-116)."""
    for name in LEISE_LOGGER:
        logger = logging.getLogger(name)
        if logger.level == logging.NOTSET:
            logger.setLevel(logging.WARNING)


cam_protokoll_leiser()

# Der Ordner des Addons, also der, der in Mod/ liegt. Sprachdateien, Hilfe
# und Symbole liegen relativ dazu.
ADDON_ORDNER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Die Einstellungen des Addons im Parameter-System von FreeCAD.
PARAMETER_PFAD = "User parameter:BaseApp/Preferences/Mod/CamAddon"

SYMBOL_ORDNER = os.path.join(ADDON_ORDNER, "resources", "icons")


def symbol(name):
    """Pfad zu einem Symbol aus resources/icons, z. B. symbol("maschine.svg")."""
    return os.path.join(SYMBOL_ORDNER, name)


def version_aus_xml(text):
    """Die Version aus dem Inhalt einer package.xml, oder „?“."""
    try:
        return ET.fromstring(text).find("{*}version").text.strip()
    except (ET.ParseError, AttributeError):
        return "?"


def _eigene_version():
    # Die Version steht nur in package.xml: Der Addon-Manager liest sie dort,
    # und eine zweite Angabe im Code liefe irgendwann auseinander.
    try:
        with open(os.path.join(ADDON_ORDNER, "package.xml"), encoding="utf-8") as datei:
            return version_aus_xml(datei.read())
    except OSError:
        return "?"


VERSION = _eigene_version()
