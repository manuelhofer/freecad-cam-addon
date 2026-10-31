# Prüft die Fähigkeiten der Werkzeuge (Format werkzeugkiste_json.md, Abschnitt 3a; Manuel,
# 2026-10-31: „das wir wissen welche werkzeuge es auf dem markt gibt und was sie können“).
# 1. Eine Datei mit einem Wendeplattenbohrer (bohrfraesen, bohrtiefe_d 3), einem Tauchfräser
#    (Einsatz „tauchfraesen“) und einem Schaftfräser (mittenschneidend je Größe verschieden):
#    Art Bohrer bzw. Schaftfräser, die Fähigkeiten der Reihe und der Größe am Werkzeug,
#    Schneidstoff WSP; eine falsche Fähigkeit (Text statt Ja/Nein) gibt einen Hinweis.
# 2. Speichern und Laden der Bibliothek behält die Fähigkeiten.
import json
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import werkzeuge as wz  # noqa: E402
from camaddon import werkzeugkiste as wk  # noqa: E402
from camaddon import werkzeugkiste_datei as wd  # noqa: E402

fehler = []
daten = {
    "format": "camaddon-werkzeugkiste",
    "version": 1,
    "reihen": [
        {
            "kennung": "probe-wsp-bohrer",
            "art": "wendeplattenbohrer",
            "hersteller": "Probe",
            "titel": "WSP-Bohrer 3xD",
            "quelle": "Probe, 2026-10-31",
            "gemeinsam": {"schneidstoff": "wsp", "bohrfraesen": True, "bohrtiefe_d": 3},
            "groessen": [{"durchmesser": 20, "gesamtlaenge": 120, "artikel": "B20"}],
            "schnittwerte": {"P1": {"bohren": {"vc": 200, "f": 0.1}}},
        },
        {
            "kennung": "probe-tauch",
            "art": "tauchfraeser",
            "hersteller": "Probe",
            "titel": "Tauchfräser",
            "quelle": "Probe, 2026-10-31",
            "gemeinsam": {"schneidstoff": "wsp", "mittenschneidend": "ja"},
            "groessen": [{"durchmesser": 32, "schneiden": 3, "artikel": "T32"}],
            "schnittwerte": {"P1": {"tauchfraesen": {"vc": 180, "fz": 0.12}}},
        },
        {
            "kennung": "probe-schaft",
            "art": "schaftfraeser",
            "hersteller": "Probe",
            "titel": "Schaftfräser",
            "quelle": "Probe, 2026-10-31",
            "gemeinsam": {"einsatzzweck": "HPC-Schruppen", "werkstoffe": ["P1", "M"]},
            "groessen": [
                {"durchmesser": 10, "mittenschneidend": True, "artikel": "S10"},
                {"durchmesser": 12, "mittenschneidend": False, "artikel": "S12"},
            ],
        },
    ],
}
pfad = os.path.join(tempfile.mkdtemp(), "probe.json")
with open(pfad, "w", encoding="utf-8") as datei:
    json.dump(daten, datei)
pruefung = wd.lesen(pfad, vorhandene=[])
if len(pruefung.reihen) != 3:
    fehler.append(f"Reihen: {len(pruefung.reihen)}, Fehler: {pruefung.fehler}")
nach = {r.kennung: r for r in pruefung.reihen}
bohrer = wk.werkzeuge(nach["probe-wsp-bohrer"])[0]
if bohrer.art != wz.BOHRER or bohrer.schneidstoff != wz.WSP:
    fehler.append(f"Wendeplattenbohrer: {bohrer.art} {bohrer.schneidstoff}")
erwartet = {"wendeplatten": True, "bohrfraesen": True, "bohrtiefe_d": 3.0}
if bohrer.faehigkeiten != erwartet:
    fehler.append(f"Bohrer kann: {bohrer.faehigkeiten}")
tauch = wk.werkzeuge(nach["probe-tauch"])[0]
if tauch.art != wz.SCHAFTFRAESER or not tauch.faehigkeiten.get("tauchfraesen"):
    fehler.append(f"Tauchfräser: {tauch.art} {tauch.faehigkeiten}")
if "mittenschneidend" in tauch.faehigkeiten:
    fehler.append("„ja“ als Fähigkeit übernommen")
if not any("mittenschneidend" in h for h in pruefung.hinweise):
    fehler.append(f"kein Hinweis zu „ja“: {pruefung.hinweise}")
werte = tauch.schnittwerte.get("P1") or []
if not any(e.art == wz.SCHRUPPEN and abs(e.vc - 180) < 1e-6 for e in werte):
    fehler.append(f"„tauchfraesen“ nicht als Schruppen: {[(e.art, e.vc) for e in werte]}")
s10, s12 = wk.werkzeuge(nach["probe-schaft"])
if (
    s10.faehigkeiten.get("mittenschneidend") is not True
    or s12.faehigkeiten.get("mittenschneidend") is not False
):
    fehler.append(f"je Größe: {s10.faehigkeiten} {s12.faehigkeiten}")
if s10.faehigkeiten.get("werkstoffe") != ["P1", "M"]:
    fehler.append(f"werkstoffe: {s10.faehigkeiten}")

text = wz.faehigkeiten_text(bohrer)
if "3" not in text or text.count(" · ") != 2:
    fehler.append(f"Text: {text!r}")
if wz.faehigkeiten_text(wz.Werkzeug()):
    fehler.append("ohne Fähigkeiten ein Text")

text = wz.faehigkeiten_text(bohrer)
if "3" not in text or text.count(" · ") != 2:
    fehler.append(f"Text: {text!r}")
if wz.faehigkeiten_text(wz.Werkzeug()):
    fehler.append("ohne Fähigkeiten ein Text")

# 2. Speichern und Laden
bibliothek = wz.Bibliothek([bohrer, s12])
ziel = os.path.join(tempfile.mkdtemp(), "werkzeugverwaltung.json")
bibliothek.speichern(ziel)
geladen = {w.art: w for w in wz.Bibliothek.laden(ziel).werkzeuge}
if (
    geladen[wz.BOHRER].faehigkeiten != bohrer.faehigkeiten
    or geladen[wz.BOHRER].schneidstoff != wz.WSP
):
    fehler.append(f"Bohrer geladen: {geladen[wz.BOHRER]}")
if geladen[wz.SCHAFTFRAESER].faehigkeiten != s12.faehigkeiten:
    fehler.append(f"Schaftfräser geladen: {geladen[wz.SCHAFTFRAESER].faehigkeiten}")

# 3. Aus dem Katalog: Walter D4120 nennt die Brillenbohrung (Kompendium 2024, S. B57).
from camaddon import sprache  # noqa: E402
from camaddon import werkzeugkiste as wk  # noqa: E402
from camaddon import werkzeugkiste_datei as wd  # noqa: E402

sprache.setze_sprache("de")
datei = wd.lesen(os.path.join(wd.mitgeliefert_ordner(), "sandvik_seco_walter.json"), [])
reihe = next((r for r in datei.reihen if "D4120, 3" in r.titel), None)
w = wk.werkzeuge(reihe, mit_werten=False)[0] if reihe is not None else None
if w is None or "brillenbohrung" not in (w.faehigkeiten.get("bohrverwendung") or []):
    fehler.append(f"Walter D4120: {w.faehigkeiten if w else reihe}")
elif "bohrt auch: Brillenbohrung, schräg anbohren" not in wz.faehigkeiten_text(w):
    fehler.append(f"Text: {wz.faehigkeiten_text(w)}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
