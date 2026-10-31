# Prüft die Kataloge als eigenen Download (kataloge.py; Manuel, 2026-10-31: „sollen wir die
# kataloginhalte downloaden um einfach deutlich bessere vorhersagen machen zu können … ja nein“).
# 1. Der Index passt zu den Katalogen im Addon (sonst: scripts/kataloge_index.py vergessen).
# 2. Laden von einem Webserver hier (nicht GitHub) ins Profil: alle Dateien, Summen stimmen; noch
#    einmal: nichts; eine geänderte Datei im Profil wird ersetzt, eine fremde entfernt.
# 3. Ohne Kataloge im Addon (wie aus dem Update-Paket): ordner() zeigt ins Profil, Halter und
#    Werkzeuge kommen von dort – gleich viele wie aus dem Addon.
# 4. Eine falsche Summe beim Laden: OSError, nichts kaputt abgelegt.
import functools
import http.server
import os
import shutil
import sys
import tempfile
import threading

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402

from camaddon import halter_katalog as hk  # noqa: E402
from camaddon import kataloge  # noqa: E402
from camaddon import werkzeugkiste_datei as wd  # noqa: E402

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


# 1. Index
probe = os.path.join(tempfile.mkdtemp(), "index.json")
neu = kataloge.index_schreiben(probe)
pruefe(neu == kataloge.index(), "Index passt nicht – scripts/kataloge_index.py laufen lassen")
pruefe(len(neu) >= 3, f"Index: {len(neu)} Dateien")

# 2. Laden von hier
quelle = tempfile.mkdtemp()
shutil.copytree(kataloge.PAKET, os.path.join(quelle, "camaddon"), dirs_exist_ok=True)
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=quelle)
handler.log_message = lambda *a, **k: None
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
adresse = f"http://127.0.0.1:{server.server_address[1]}/camaddon/"
pruefe(kataloge.profil().startswith(FreeCAD.getUserAppDataDir()), kataloge.profil())
shutil.rmtree(kataloge.profil(), ignore_errors=True)
schritte = []
anzahl = kataloge.laden(lambda f, a, p: schritte.append((f, a, p)), adresse)
print(f"geladen: {anzahl} Dateien, {len(schritte)} Schritte")
pruefe(
    anzahl == len(neu) and not kataloge.fehlend(), f"geladen {anzahl}, offen {kataloge.fehlend()}"
)
pruefe(kataloge.laden(adresse=adresse) == 0, "zweites Laden holt wieder")
halter = os.path.join(kataloge.profil("halter_daten"), "hersteller.json")
with open(halter, "a", encoding="utf-8") as datei:
    datei.write(" ")
fremd = os.path.join(kataloge.profil("halter_daten"), "alt.json")
with open(fremd, "w", encoding="utf-8") as datei:
    datei.write("{}")
pruefe([p for p, _e in kataloge.fehlend()] == ["halter_daten/hersteller.json"], "geändert")
pruefe(kataloge.laden(adresse=adresse) == 1 and not os.path.exists(fremd), "ersetzt/entfernt")

# 3. Ohne Kataloge im Addon
im_addon = len(hk.katalog_reihen())
werkzeuge_addon = len(wd.mitgelieferte())
paket = kataloge.PAKET
kataloge.PAKET = tempfile.mkdtemp()  # leer: wie aus dem Update-Paket
try:
    kataloge.geaendert()
    pruefe(not kataloge.im_addon() and kataloge.vorhanden(), "ohne Addon-Kataloge")
    pruefe(kataloge.ordner("halter_daten") == kataloge.profil("halter_daten"), "ordner()")
    pruefe(
        len(hk.katalog_reihen()) == im_addon, f"Halter aus dem Profil: {len(hk.katalog_reihen())}"
    )
    pruefe(wd.mitgeliefert_ordner() == kataloge.profil("werkzeugkiste_daten"), "Werkzeugordner")
    pruefe(len(wd.mitgelieferte()) == werkzeuge_addon, "Werkzeuge aus dem Profil")
    shutil.rmtree(kataloge.profil(), ignore_errors=True)
    pruefe(not kataloge.vorhanden() and hk.katalog_reihen() == [], "ohne Kataloge")
finally:
    kataloge.PAKET = paket
    kataloge.geaendert()

# 4. Falsche Summe
with open(os.path.join(quelle, "camaddon", "spannmittel_daten", "hersteller.json"), "a") as datei:
    datei.write(" ")
try:
    kataloge.laden(adresse=adresse)
    pruefe(False, "falsche Summe ohne Fehler")
except OSError as grund:
    pruefe("Prüfsumme" in str(grund), str(grund))
pruefe(
    not os.path.exists(os.path.join(kataloge.profil("spannmittel_daten"), "hersteller.json")),
    "die falsche Datei liegt im Profil",
)
server.shutdown()

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
