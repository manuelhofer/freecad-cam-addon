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

Der Grund der Dialoge und Aufgabenfenster ist je Version ein anderer: „FreeCAD Dark“ malt ihn
`lighten(PrimaryColor, 80)` – in 1.1 #2d2d2d, in 26.3.0RC1 #5a5a5a (dort ist PrimaryColor #323232;
P-2026-10-10-48). Darauf erreichten Grau und Rot nur 3,3 und 2,7 : 1. Darum wird im dunklen Theme
der Grund an einem Dialog gemessen und jede Farbe so weit zu Weiß gemischt, bis sie sich mit
MINDESTKONTRAST abhebt – wo sie das schon tut (1.1), bleibt sie, wie sie ist. Das helle Theme
bleibt unberührt.

Nur Text – Flächen, die das Addon selbst malt (Bilder von Werkzeug und Eingriff), nehmen ihren
Grund aus der Palette.
"""

MINDESTKONTRAST = 4.5  # WCAG für Text

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


def grund():
    """Der Grund der Dialoge und Aufgabenfenster, wie das Theme ihn malt – (r, g, b) an einem
    polierten QDialog (dieselbe Regel `DialogBackgroundColor` wie der Inhalt der Aufgaben-
    fenster); ohne Oberfläche None."""
    try:
        import FreeCADGui
        from PySide import QtGui

        fenster = FreeCADGui.getMainWindow()
        if fenster is None:
            return None
        probe = QtGui.QDialog(fenster)
        probe.ensurePolished()
        farbe = probe.palette().color(QtGui.QPalette.Window)
        probe.deleteLater()
        return farbe.red(), farbe.green(), farbe.blue()
    except Exception:  # FreeCADCmd: keine Oberfläche, kein Hauptfenster
        return None


def kontrast(a, b):
    """Kontrastverhältnis zweier Farben (r, g, b) nach WCAG, 1 … 21."""

    def leucht(rgb):
        def kanal(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        r, g, b = (kanal(c) for c in rgb)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    hell, dunkel_ = sorted((leucht(a), leucht(b)), reverse=True)
    return (hell + 0.05) / (dunkel_ + 0.05)


def heller(farbe, auf):
    """Die Farbe (#rrggbb), so wenig wie nötig zu Weiß gemischt, dass sie sich mit
    MINDESTKONTRAST vom dunklen Grund `auf` (r, g, b) abhebt."""
    rgb = tuple(int(farbe[i : i + 2], 16) for i in (1, 3, 5))
    for schritt in range(51):
        neu = tuple(round(c + (255 - c) * schritt / 50) for c in rgb)
        if kontrast(neu, auf) >= MINDESTKONTRAST:
            return "#" + "".join(f"{c:02x}" for c in neu)
    return "#ffffff"


def _waehle():
    if not dunkel():
        return {name: paar[0] for name, paar in _FARBEN.items()}
    gewaehlt = {name: paar[1] for name, paar in _FARBEN.items()}
    auf = grund()
    # Nur auf dunklem Grund: Hätte das Theme den Dialog noch nicht gefärbt, wäre er hell.
    if auf is None or sum(auf) / 3 >= 128:
        return gewaehlt
    return {name: heller(farbe, auf) for name, farbe in gewaehlt.items()}


_GEWAEHLT = _waehle()
GRAU = _GEWAEHLT["GRAU"]
ROT = _GEWAEHLT["ROT"]
GRUEN = _GEWAEHLT["GRUEN"]
GELB = _GEWAEHLT["GELB"]
