# SPDX-License-Identifier: LGPL-2.1-or-later
"""CAM-Addon für FreeCAD.

Das Paket ist so aufgeteilt, dass alles ohne Oberfläche (Sprache, Maschinen-
modell) auch in FreeCADCmd läuft; nur Module mit ``gui`` im Namen brauchen
FreeCADGui.
"""

import os
import xml.etree.ElementTree as ET

# Wurzel des Addons (der Ordner, der in Mod/ liegt) – Sprachdateien, Hilfe und
# Symbole liegen relativ dazu.
ADDON_ORDNER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _version_aus_package_xml():
    """Die Version steht nur in package.xml – der Addon-Manager liest sie dort
    für die Updates, und eine zweite Angabe im Code würde auseinanderlaufen."""
    try:
        wurzel = ET.parse(os.path.join(ADDON_ORDNER, "package.xml")).getroot()
        return wurzel.find("{*}version").text.strip()
    except (OSError, ET.ParseError, AttributeError):
        return "?"


VERSION = _version_aus_package_xml()

# Einstellungen des Addons im Parameter-System von FreeCAD.
PARAMETER_PFAD = "User parameter:BaseApp/Preferences/Mod/CamAddon"
