# SPDX-License-Identifier: LGPL-2.1-or-later
# Von FreeCAD beim Start der Oberfläche ausgeführt. FreeCAD führt diese Datei
# in einem eigenen Namensraum aus, in dem sich hier definierte Funktionen
# gegenseitig nicht sehen – deshalb steht die ganze Logik im Paket.

import camaddon.gui_start

camaddon.gui_start.starten()
