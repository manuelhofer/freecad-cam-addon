# Prüft die Hilfetexte: jedes Thema auf Deutsch und Englisch vorhanden, jede
# Seite hat eine Überschrift, alle Verweise zwischen Seiten zeigen auf
# vorhandene Dateien, und jedes im Code benutzte Thema gibt es.
import glob
import os
import re
import sys
from pathlib import Path

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import hilfe

fehler = []
for code in ("de", "en"):
    for thema in hilfe.THEMEN:
        pfad = os.path.join(ADDON, "help", code, thema + ".html")
        if not os.path.isfile(pfad):
            fehler.append(f"fehlt: help/{code}/{thema}.html")
            continue
        text = Path(pfad).read_text("utf-8")
        if "<h2>" not in text:
            fehler.append(f"help/{code}/{thema}.html hat keine Überschrift")
        for ziel in re.findall(r'href="([^"#:]+)"', text):
            if not os.path.isfile(os.path.join(ADDON, "help", code, ziel)):
                fehler.append(f"help/{code}/{thema}.html verweist auf fehlende Seite {ziel}")
    ueberzaehlig = {
        os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ADDON, "help", code, "*.html"))
    }
    ueberzaehlig -= set(hilfe.THEMEN)
    if ueberzaehlig:
        fehler.append(f"help/{code}: Seiten ohne Thema in hilfe.THEMEN: {sorted(ueberzaehlig)}")

# Themen, die der Dialog aufruft, müssen in THEMEN stehen.
code = Path(ADDON, "camaddon", "gui_maschine.py").read_text("utf-8")
benutzt = set(re.findall(r'_kopfzeile\([^)]*,\s*"([a-z_]+)"\)', code))
benutzt |= set(re.findall(r'href="([a-z_]+)"', code))
if not benutzt:
    fehler.append("keine Hilfethemen im Dialog gefunden – Suchmuster veraltet?")
if benutzt - set(hilfe.THEMEN):
    fehler.append(f"im Dialog benutzt, aber keine Hilfe: {sorted(benutzt - set(hilfe.THEMEN))}")

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
