# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Textfarben der Fenster des Addons – lesbar im hellen wie im dunklen Theme von FreeCAD.

Manuel, 2026-10-10, in FreeCAD 26.3 mit dunklem Theme: „Man kann die Schrift nicht lesen im
dunkel Modus .... Sollte man standardmäßig ändern“ – die grauen Sätze unter den Feldern und die
roten Hinweise waren für weißen Grund gewählt (#6d6d6d, #c0392b) und standen auf Dunkelgrau
(P-2026-10-10-42).

Hell oder dunkel liest das Modul am Hauptfenster von FreeCAD: Das Theme färbt es per Stylesheet,
die Palette der Anwendung bleibt dabei hell (gemessen in 1.1.3 und im Wochen-Build: Hauptfenster
#191919, Anwendung #efefef). Gelesen wird einmal, wenn ein Fenster des Addons das Modul zuerst
braucht – nach einem Wechsel des Themes gelten die neuen Farben nach dem Neustart von FreeCAD.
Ohne Oberfläche (FreeCADCmd) gelten die hellen.

Nur Text – Flächen, die das Addon selbst malt (Bilder von Werkzeug und Eingriff), nehmen ihren
Grund aus der Palette.
"""

# Je Farbe: (auf hellem Grund, auf dunklem Grund)
_FARBEN = {
    "GRAU": ("#6d6d6d", "#b4b4b4"),  # gerechnete oder geerbte Werte, Erklärsätze
    "ROT": ("#c0392b", "#ff7b72"),  # was fehlt oder nicht passt
    "GRUEN": ("#2e7d32", "#8ae234"),  # passt
    "GELB": ("#b9770e", "#f2c94c"),  # Warnung
}


def dunkel():
    """Ist das Theme von FreeCAD dunkel? Am Grund des Hauptfensters gemessen; ohne Oberfläche
    nein."""
    try:
        import FreeCADGui
        from PySide import QtGui

        fenster = FreeCADGui.getMainWindow()
        if fenster is None:
            return False
        # Das Stylesheet des Themes kommt erst beim Polieren in die Palette des Fensters – beim
        # ersten Start lädt das Addon (Sprachwahl), bevor Qt das von selbst getan hat.
        fenster.ensurePolished()
        return fenster.palette().color(QtGui.QPalette.Window).lightness() < 128
    except Exception:  # FreeCADCmd: keine Oberfläche, kein Hauptfenster
        return False


def _waehle():
    stelle = 1 if dunkel() else 0
    return {name: paar[stelle] for name, paar in _FARBEN.items()}


_GEWAEHLT = _waehle()
GRAU = _GEWAEHLT["GRAU"]
ROT = _GEWAEHLT["ROT"]
GRUEN = _GEWAEHLT["GRUEN"]
GELB = _GEWAEHLT["GELB"]
