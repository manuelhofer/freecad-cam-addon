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

# Themen, die die Oberfläche aufruft, müssen in THEMEN stehen: die Knöpfe (?)
# in den Überschriften – kopfzeile(tr("…"), "thema") – und Verweise wie
# href="beschleunigung". Findet eines der Muster nichts, ist es veraltet.
code = "".join(p.read_text("utf-8") for p in sorted(Path(ADDON, "camaddon").glob("gui_*.py")))
knoepfe = set(re.findall(r'\bkopfzeile\(tr\("[^"]*"\),\s*"([a-z_]+)"\)', code))
verweise = set(re.findall(r'href="([a-z_]+)"', code))
if not knoepfe or not verweise:
    fehler.append(f"Suchmuster veraltet? Knöpfe {knoepfe}, Verweise {verweise}")
benutzt = knoepfe | verweise
if benutzt - set(hilfe.THEMEN):
    fehler.append(f"benutzt, aber keine Hilfe: {sorted(benutzt - set(hilfe.THEMEN))}")

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
