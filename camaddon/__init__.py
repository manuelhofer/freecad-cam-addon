# SPDX-License-Identifier: LGPL-2.1-or-later
"""CAM-Addon für FreeCAD.

Das Paket ist so aufgeteilt, dass alles ohne Oberfläche (Sprache, Maschinen-
modell) auch in FreeCADCmd läuft; nur Module mit ``gui`` im Namen brauchen
FreeCADGui.
"""

import os

VERSION = "0.1.0"

# Wurzel des Addons (der Ordner, der in Mod/ liegt) – Sprachdateien, Hilfe und
# Symbole liegen relativ dazu.
ADDON_ORDNER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Einstellungen des Addons im Parameter-System von FreeCAD.
PARAMETER_PFAD = "User parameter:BaseApp/Preferences/Mod/CamAddon"
