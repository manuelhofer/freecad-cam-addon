# Prüft die Werkzeugbibliothek ohne Oberfläche: anlegen, kopieren, Nummern,
# Speichern und Laden (mit .bak), eine beschädigte Datei und eigene
# Werkstoffe.
import json
import os
import sys
import tempfile
from pathlib import Path

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import sprache
from camaddon import werkstoffe as ws
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


vorher = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")
ordner = tempfile.mkdtemp()
pfad = os.path.join(ordner, "CamAddon", wz.DATEINAME)

# Ohne Datei: leer.
b = wz.Bibliothek.laden(pfad)
pruefe(b.werkzeuge == [] and b.eigene_werkstoffe == [], "ohne Datei nicht leer")

# Anlegen: nächste freie Nummer, auch mit Lücke.
t1 = b.neues_werkzeug()
t1.durchmesser, t1.schneiden, t1.schneidenlaenge = 12, 3, 26
t2 = b.neues_werkzeug()
t2.nummer = 5
t3 = b.neues_werkzeug()
pruefe((t1.nummer, t3.nummer) == (1, 2), f"Nummern {t1.nummer}, {t3.nummer}")
pruefe(b.naechste_nummer() == 3, f"nächste Nummer {b.naechste_nummer()}")
pruefe(b.mit_nummer(5, ausser=t1) is t2 and b.mit_nummer(5, ausser=t2) is None, "mit_nummer")

# Kopieren: neue Kennung, nächste Nummer, gleiche Werte.
kopie = b.kopiere(t1)
pruefe(kopie.kennung != t1.kennung and kopie.nummer == 3, f"Kopie {kopie}")
pruefe((kopie.durchmesser, kopie.schneidenlaenge) == (12, 26), "Kopie ohne Werte")

# Listenzeile.
pruefe(wz.zeile(t1) == "T1  Schaftfräser Ø 12 · z 3 · VHM", f"Zeile: {wz.zeile(t1)!r}")
t3.durchmesser, t3.art, t3.schneiden = 8.5, wz.BOHRER, 2
pruefe(wz.zeile(t3) == "T2  Bohrer Ø 8.5 · z 2 · VHM", f"Zeile Bohrer: {wz.zeile(t3)!r}")
leer = wz.Werkzeug(nummer=9)
pruefe("Ø ?" in wz.zeile(leer), f"Zeile ohne Durchmesser: {wz.zeile(leer)!r}")

# Eigene Werkstoffe stehen vor den mitgelieferten.
eigen = ws.Werkstoff("eigen-1", kurzname="Hartholz", gruppe="Holz", iso="N", eigen=True)
b.eigene_werkstoffe.append(eigen)
pruefe(b.alle_werkstoffe()[0] is eigen, "eigener Werkstoff nicht vorn")
pruefe(len(b.alle_werkstoffe()) == len(ws.mitgelieferte()) + 1, "Werkstoffe gezählt")

# Speichern und wieder laden: gleicher Inhalt, Werkzeuge nach Nummer sortiert.
b.speichern(pfad)
geladen = wz.Bibliothek.laden(pfad)
pruefe(geladen.gleich(b), "nach Laden nicht gleich")
pruefe([w.nummer for w in geladen.werkzeuge] == [1, 2, 3, 5], "Reihenfolge in der Datei")
pruefe(geladen.eigene_werkstoffe[0].eigen, "eigener Werkstoff nach Laden nicht eigen")
pruefe(not os.path.exists(pfad + ".bak"), ".bak beim ersten Speichern")

# Zweites Speichern: die vorige Fassung bleibt als .bak.
t1.bezeichnung = "Hoffmann 12 mm"
b.speichern(pfad)
alt = json.loads(Path(pfad + ".bak").read_text("utf-8"))
pruefe(alt["werkzeuge"][0]["bezeichnung"] == "", ".bak enthält nicht die vorige Fassung")
pruefe(not os.path.exists(pfad + ".neu"), "Zwischendatei blieb liegen")

# kopie() ist unabhängig; gleich() merkt Änderungen.
k = b.kopie()
k.werkzeuge[0].durchmesser = 99
pruefe(not k.gleich(b) and b.werkzeuge[0].durchmesser == 12, "kopie() nicht unabhängig")

# Unlesbares im Eintrag: Standardwerte statt Absturz.
w = wz.Werkzeug.aus_dict({"nummer": "x", "art": "Hammer", "durchmesser": None, "schneidstoff": 3})
pruefe(
    (w.nummer, w.art, w.durchmesser, w.schneidstoff) == (1, wz.SCHAFTFRAESER, 0.0, wz.VHM), f"{w}"
)

# Beschädigte Datei: wird beiseitegelegt, nichts geht verloren.
Path(pfad).write_text("{kaputt", "utf-8")
try:
    wz.Bibliothek.laden(pfad)
    fehler.append("beschädigte Datei: kein Fehler")
except wz.BeschaedigteDatei as f:
    pruefe(os.path.exists(f.beiseite) and not os.path.exists(pfad), "nicht beiseitegelegt")
    pruefe(Path(f.beiseite).read_text("utf-8") == "{kaputt", "Inhalt verändert")

sprache.setze_sprache(vorher)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
