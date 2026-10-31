"""Schreibt camaddon/kataloge_index.json neu (Größe und SHA-256 je Katalogdatei) – nach jeder
Änderung an werkzeugkiste_daten, halter_daten oder spannmittel_daten aufrufen; test_kataloge
prüft, dass er passt. Läuft mit normalem Python (ohne FreeCAD)."""

import os
import sys

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# kataloge.py importiert relativ (ADDON_ORDNER) – hier nur index_schreiben, darum als Text.
with open(os.path.join(HIER, "camaddon", "kataloge.py"), encoding="utf-8") as datei:
    quelle = datei.read()
quelle = quelle.replace("from . import ADDON_ORDNER", "ADDON_ORDNER = None")
modul = type(sys)("kataloge_ohne_paket")
modul.__file__ = os.path.join(HIER, "camaddon", "kataloge.py")
exec(compile(quelle, modul.__file__, "exec"), modul.__dict__)
dateien = modul.index_schreiben()
print(f"{len(dateien)} Dateien, {sum(d['groesse'] for d in dateien.values()) / 1e6:.1f} MB")
