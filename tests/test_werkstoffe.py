# Prüft die mitgelieferte Werkstoffliste (daten/werkstoffe.json) und ihre
# Anzeige: jeder Eintrag vollständig und eindeutig, Gruppen und Zustände
# übersetzt, Anzeige wie in der Werkstatt, Suche und Dezimalzeichen.
import json
import os
import re
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import sprache
from camaddon import werkstoffe as ws

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


vorher = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")
liste = ws.mitgelieferte()
pruefe(len(liste) >= 40, f"nur {len(liste)} Werkstoffe")

# Die Datei selbst: keine Felder, die das Programm nicht kennt (Tippfehler).
with open(ws.DATEI, encoding="utf-8") as datei:
    roh = json.load(datei)["werkstoffe"]
bekannt = set(ws.Werkstoff("x").als_dict())
for eintrag in roh:
    unbekannt = set(eintrag) - bekannt
    pruefe(not unbekannt, f"{eintrag.get('kennung')}: unbekannte Felder {unbekannt}")

kennungen = [w.kennung for w in liste]
pruefe(len(set(kennungen)) == len(kennungen), "Kennungen doppelt")
for iso in ws.ISO_GRUPPEN:
    pruefe(any(w.iso == iso for w in liste), f"keine Werkstoffe der ISO-Gruppe {iso}")

for w in liste:
    name = w.kennung
    pruefe(w.kurzname and w.gruppe and w.zusammensetzung and w.haerte, f"{name}: Angaben fehlen")
    pruefe(w.iso in ws.ISO_GRUPPEN, f"{name}: ISO-Gruppe {w.iso!r}")
    pruefe(not w.nummer or re.fullmatch(r"\d\.\d{4}", w.nummer), f"{name}: Nummer {w.nummer!r}")
    # Jede Gruppe und jeder Zustand mit Schlüssel hat einen Text – sonst
    # erschiene der Schlüssel selbst („edelstahl_duplex“).
    pruefe(ws.gruppe_text(w.gruppe) != w.gruppe, f"{name}: Gruppe {w.gruppe!r} ohne Text")
    pruefe(
        not w.zustand
        or ws.zustand_text(w.zustand) != w.zustand
        or re.fullmatch(r"[TH]\d+", w.zustand),
        f"{name}: Zustand {w.zustand!r} ohne Text",
    )
    pruefe(w.kc11 >= 0 and 0 <= w.mc < 1, f"{name}: kc1.1 {w.kc11}, mc {w.mc}")
    pruefe((w.kc11 == 0) == (w.mc == 0), f"{name}: kc1.1 und mc nur zusammen")
    # In der Datei steht der Punkt als Dezimalzeichen; die Oberfläche setzt ihres ein.
    zahlen = w.zusammensetzung + w.haerte + w.zugfestigkeit
    pruefe(not re.search(r"\d,\d", zahlen), f"{name}: Komma als Dezimalzeichen in {zahlen!r}")

# Anzeige wie in der Werkstatt.
v2a = ws.finde(liste, "1.4301")
pruefe(
    ws.anzeige(v2a) == "1.4301  X5CrNi18-10 · Edelstahl, austenitisch (V2A, AISI 304)",
    f"Anzeige 1.4301: {ws.anzeige(v2a)!r}",
)
gehaertet = ws.finde(liste, "1.2379+H")
pruefe(
    ws.anzeige(gehaertet) == "1.2379  X153CrMoV12 · Kaltarbeitsstahl, gehärtet (AISI D2)",
    f"Anzeige 1.2379+H: {ws.anzeige(gehaertet)!r}",
)
pom = ws.finde(liste, "POM-C")
pruefe(ws.anzeige(pom).startswith("POM-C · Kunststoff"), f"Anzeige POM-C: {ws.anzeige(pom)!r}")
pruefe(ws.anzeige(ws.finde(liste, "3.2315")).count("T6") == 1, "Zustand T6 fehlt bei 3.2315")

# Englisch: Gruppe übersetzt, Nummer und Kurzname bleiben.
sprache.setze_sprache("en")
pruefe(
    ws.anzeige(v2a) == "1.4301  X5CrNi18-10 · Stainless steel, austenitic (V2A, AISI 304)",
    f"Anzeige englisch: {ws.anzeige(v2a)!r}",
)
sprache.setze_sprache("de")

# Dezimalzeichen: nur zwischen Ziffern, Kurznamen bleiben unberührt.
pruefe(
    ws.mit_dezimalzeichen("C ≤ 0.07 · Cr 17.5–19.5", ",") == "C ≤ 0,07 · Cr 17,5–19,5",
    "Dezimalzeichen",
)
pruefe(ws.mit_dezimalzeichen("Cr 17.5", ".") == "Cr 17.5", "Punkt bleibt Punkt")

# Suche: Nummer, Kurzname, alter Name, Gruppe – jedes Wort muss passen.
for suche in ("1.43", "x5cr", "V2A", "edelstahl austenit", "304"):
    pruefe(ws.passt(v2a, suche), f"„{suche}“ findet 1.4301 nicht")
pruefe(not ws.passt(v2a, "aluminium"), "„aluminium“ findet 1.4301")
pruefe(ws.passt(ws.finde(liste, "0.6025"), "gg-25"), "„gg-25“ findet EN-GJL-250 nicht")

# Sortierung: ISO-Gruppen in Katalogreihenfolge.
reihe = [w.iso for w in ws.sortiert(liste)]
pruefe(reihe == sorted(reihe, key=ws.ISO_GRUPPEN.index), "Sortierung nach ISO-Gruppe")

# Eigene Werkstoffe: freier Text als Gruppe bleibt, neue Kennung ist frei.
eigen = ws.Werkstoff.aus_dict(
    {"kennung": "eigen-1", "kurzname": "Hartholz", "gruppe": "Holz"}, eigen=True
)
pruefe(ws.anzeige(eigen) == "Hartholz · Holz", f"eigener Werkstoff: {ws.anzeige(eigen)!r}")
pruefe(ws.neue_kennung([eigen]) == "eigen-2", "neue Kennung")
pruefe(
    ws.Werkstoff.aus_dict({"kennung": "x", "iso": "Q", "kc11": "abc"}).iso == "P", "ISO unbekannt"
)

sprache.setze_sprache(vorher)

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
