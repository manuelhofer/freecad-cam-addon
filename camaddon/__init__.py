# SPDX-License-Identifier: LGPL-2.1-or-later
"""CAM-Addon für FreeCAD.

Module ohne „gui“ im Namen laufen auch ohne Oberfläche (FreeCADCmd) und
werden so getestet; nur die gui_*-Module brauchen FreeCADGui. Welches Modul
wofür zuständig ist, steht in docs/aufbau.md.
"""

import os
import xml.etree.ElementTree as ET

# Der Ordner des Addons, also der, der in Mod/ liegt. Sprachdateien, Hilfe
# und Symbole liegen relativ dazu.
ADDON_ORDNER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Die Einstellungen des Addons im Parameter-System von FreeCAD.
PARAMETER_PFAD = "User parameter:BaseApp/Preferences/Mod/CamAddon"


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
