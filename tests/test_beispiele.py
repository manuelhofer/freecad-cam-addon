# Prüft „Beispiele laden …“ (beispiele.py; Manuel, 2026-10-16: alle Testteile ins Repository, beim
# Laden aber wählbar): daten/beispiele.json nennt genau die Dateien in beispiele/, die das Update
# nicht mitlädt (export-ignore), mit Größe und Prüfsumme – sonst scripts/beispiele_liste.py laufen
# lassen. Die Werkzeugkisten-Dateien, die die Hilfe nennt, bleiben im Update. Laden mit einer
# Quelle, die aus dem Repository liest statt von GitHub: alle kommen an, mit Unterordnern; ein
# zweites Mal ist alles „schon da“; eine falsche Prüfsumme schreibt nichts.
import importlib.util
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import beispiele as bsp

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


spec = importlib.util.spec_from_file_location(
    "beispiele_liste", os.path.join(ADDON, "scripts", "beispiele_liste.py")
)
skript = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skript)

liste = bsp.liste()
erwartet = [(p, b, s) for p, b, s in skript.dateien()]
pruefe(
    [(b.pfad, b.bytes, b.sha256) for b in liste] == erwartet,
    "daten/beispiele.json passt nicht zu beispiele/ – scripts/beispiele_liste.py laufen lassen",
)
namen = {b.pfad for b in liste}
pruefe("beispiele/c_ring_nut_3achs.FCStd" in namen, "der C-Ring fehlt")
pruefe("beispiele/testteil_3achs_fraese.FCStd" in namen, "das 3-Achs-Testteil fehlt")
pruefe(
    not any(n.startswith("beispiele/werkzeugkiste_") or n == "beispiele/README.md" for n in namen),
    "Werkzeugkisten oder Beschreibung gehören ins Update",
)


def aus_dem_repository(adresse, _zeitlimit):
    pfad = adresse.split("/main/", 1)[1]
    with open(os.path.join(ADDON, *pfad.split("/")), "rb") as quelle:
        return quelle.read()


wohin = tempfile.mkdtemp()
klein = [b for b in liste if b.bytes < 300_000][:6] + [
    b for b in liste if b.pfad.startswith("beispiele/grob_g550_simultan/assets/")
]
geladen, da, fehlgeschlagen = bsp.laden(klein, wohin, aus_dem_repository)
pruefe(len(geladen) == len(klein) and not da and not fehlgeschlagen, f"geladen {len(geladen)}")
pruefe(all(bsp.schon_da(b, wohin) for b in klein), "nicht alle im Ordner")
geladen, da, fehlgeschlagen = bsp.laden(klein, wohin, aus_dem_repository)
pruefe(not geladen and len(da) == len(klein), "zweites Mal nicht „schon da“")
os.remove(bsp.ziel(klein[0], wohin))
geladen, da, fehlgeschlagen = bsp.laden(klein[:1], wohin, lambda _a, _z: b"kaputt")
pruefe(
    not geladen and len(fehlgeschlagen) == 1 and not os.path.exists(bsp.ziel(klein[0], wohin)),
    "falsche Prüfsumme geschrieben",
)
pruefe(
    bsp.adresse(klein[0]).startswith(
        "https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/beispiele/"
    ),
    bsp.adresse(klein[0]),
)
print(f"{len(liste)} Beispiele, {sum(b.bytes for b in liste) / 1e6:.1f} MB")

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
