# FreeCAD 1.1.4 mit Python 3.14 stürzt ab, wenn eine 3D-Ansicht zugeht, deren Viewer Python einmal
# geholt hat (`ansicht.getViewer()`): „Hinsehen“ im Fenster „Auf der Maschine prüfen“ oder in der
# Bestückung, danach das Dokument schließen – und FreeCAD war weg (B-011). Das Addon holt den
# Viewer deshalb nirgends; den Ausschnitt für `viewAll` rechnet gui_abfahren.ausschnitt aus der
# Größe der Ansicht. Die Szenarien szenario_abfahren, szenario_bestueckung und
# szenario_rundum_drehmaschine schließen nach „Hinsehen“ das Dokument und laufen weiter – in
# FreeCAD 1.1.3 stürzte dabei nichts ab; dort hält nur diese Prüfung fest, dass es so bleibt.
import ast
import os

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

fehler = []
dateien = 0
for ordner, _unter, namen in os.walk(os.path.join(ADDON, "camaddon")):
    for name in sorted(namen):
        if not name.endswith(".py"):
            continue
        pfad = os.path.join(ordner, name)
        dateien += 1
        with open(pfad, encoding="utf-8") as datei:
            baum = ast.parse(datei.read(), pfad)
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.Attribute) and knoten.attr == "getViewer":
                fehler.append(f"{os.path.relpath(pfad, ADDON)}:{knoten.lineno}")

assert dateien > 50, f"nur {dateien} Dateien in camaddon/ gefunden"
assert not fehler, "getViewer() lässt FreeCAD 1.1.4 beim Schließen abstürzen: " + ", ".join(fehler)
print("OK", os.path.basename(__file__))
