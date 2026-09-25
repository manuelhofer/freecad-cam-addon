# Prüft das Sprachsystem und die Sprachdateien: gleiche Schlüssel in Deutsch
# und Englisch, jeder im Code benutzte Schlüssel vorhanden, keine Leichen,
# gleiche Platzhalter in allen Sprachen, Rückfall auf Englisch.
import glob
import json
import os
import re
import string
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import sprache

fehler = []


def lade(code):
    with open(os.path.join(ADDON, "translations", code + ".json"), encoding="utf-8") as datei:
        return json.load(datei)


def platzhalter(text):
    return {teil[1] for teil in string.Formatter().parse(text) if teil[1] is not None}


de, en = lade("de"), lade("en")
if set(de) != set(en):
    fehler.append(f"nur in de.json: {sorted(set(de) - set(en))}")
    fehler.append(f"nur in en.json: {sorted(set(en) - set(de))}")

# Jede weitere Sprache darf unvollständig sein, aber nichts Fremdes enthalten.
for pfad in glob.glob(os.path.join(ADDON, "translations", "*.json")):
    code = os.path.basename(pfad)[:-5]
    daten = lade(code)
    fremd = set(daten) - set(de)
    if fremd:
        fehler.append(f"{code}.json: Schlüssel, die de.json nicht kennt: {sorted(fremd)}")
    for schluessel, text in daten.items():
        if schluessel in de and platzhalter(text) != platzhalter(de[schluessel]):
            fehler.append(f"{code}.json: Platzhalter weichen ab bei {schluessel}")

# Schlüssel stehen im Code immer als fester Text in tr("...") oder
# meldung("..."), nie zusammengesetzt – sonst könnte diese Prüfung sie nicht
# finden.
benutzt = set()
for pfad in glob.glob(os.path.join(ADDON, "camaddon", "**", "*.py"), recursive=True):
    with open(pfad, encoding="utf-8") as datei:
        benutzt |= set(re.findall(r"""\b(?:tr|meldung)\(\s*["']([^"']+)["']""", datei.read()))
fehlt = benutzt - set(de)
if fehlt:
    fehler.append(f"im Code benutzt, aber nicht in de.json: {sorted(fehlt)}")
unbenutzt = set(de) - benutzt - {"_sprache"}
if unbenutzt:
    fehler.append(f"in de.json, aber nirgends benutzt: {sorted(unbenutzt)}")

# Rückfall: unbekannte Sprache -> Englisch; bekannte Sprache -> ihr Text.
if sprache.tr("_sprache", sprache="xx") != "English":
    fehler.append("Rückfall auf Englisch greift nicht")
if sprache.tr("_sprache", sprache="de") != "Deutsch":
    fehler.append("deutscher Text wird nicht gefunden")
if sprache.verfuegbare_sprachen().get("de") != "Deutsch":
    fehler.append("verfuegbare_sprachen() kennt Deutsch nicht")

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
