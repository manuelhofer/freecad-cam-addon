# Prüft das Einlesen eigener Werkzeugkiste-Dateien (T-007, werkzeugkiste_datei.py): Das Beispiel
# aus beispiele/ liest sich fehlerfrei, Schnittwerte landen als Katalogwerte (vc aus der Reihe,
# fz je Größe, ap/ae als Vielfache von D, fehlende fz als Richtwert, nie schneller als die Datei);
# Dubletten werden exakt erkannt – gleiche Kennung, gleiche Artikelnummer, gleiche Maße ohne
# Nummer – in der Datei selbst, gegen die eingebaute Kiste und zwischen Dateien; zwei
# Artikelnummern mit gleichen Maßen sind zwei Produkte. Eingelesene Dateien liegen im Ordner und
# stehen in werkzeugkiste.reihen(); hinzufuegen() in die eigene Kiste lässt gleiche Maße aus
# (Manuel, 2026-10-10: „3 mal den Schaftfräser 12 von Hoffmann … exakt verglichen“).
import json
import os
import shutil
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import sprache
from camaddon import werkzeuge as wz
from camaddon import werkzeugkiste as wk
from camaddon import werkzeugkiste_datei as wd

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nahe(a, b, toleranz=1e-6):
    return abs(a - b) <= toleranz


def schreibe(pfad, reihen):
    with open(pfad, "w", encoding="utf-8") as datei:
        json.dump({"format": wd.FORMAT, "version": 1, "reihen": reihen}, datei, ensure_ascii=False)
    return pfad


sprache.setze_sprache("de")
tmp = tempfile.mkdtemp()
wd.ordner = lambda: os.path.join(tmp, "werkzeugkiste")
wd.vergessen()
eingebaut = len(wk.eingebaute())

# --- Die mitgelieferte Liste (P-2026-10-16-48): fehlerfrei, nichts doppelt gegen die eingebaute
# Kiste, jedes Werkzeug mit Ø, die nachgelesenen vc darin; in reihen() nach den eingebauten ---------
mitgeliefert = wd.mitgelieferte()
hoffmann = [r for r in mitgeliefert if r.datei == "hoffmann.json"]
pruefe(len(hoffmann) == 77, f"hoffmann.json: {len(hoffmann)} Reihen")
# Die Kataloge der Hersteller (W-042): mehr als 700 Reihen, über 12 000 Größen, alle in reihen().
pruefe(len(mitgeliefert) > 700, f"mitgeliefert: {len(mitgeliefert)} Reihen")
pruefe(sum(r.anzahl for r in mitgeliefert) > 12000, "mitgeliefert: zu wenig Größen")
pruefe(len(wk.reihen()) == eingebaut + len(mitgeliefert), f"reihen(): {len(wk.reihen())}")
# Der Zwischenspeicher (über 40 000 Größen zu prüfen dauerte 5 s): liegt beim Benutzer, liefert
# dieselben Reihen; ein anderer Stand (hier: eine andere Sprache) liest neu.
pruefe(os.path.exists(wd._zwischenspeicher()), "kein Zwischenspeicher")
wd._mitgeliefert = None
wieder = wd.mitgelieferte()
pruefe(
    [(r.kennung, r.anzahl, r.quelle) for r in wieder]
    == [(r.kennung, r.anzahl, r.quelle) for r in mitgeliefert],
    "aus dem Zwischenspeicher anders",
)
pruefe(wd._aus_dem_zwischenspeicher("ein anderer Stand") is None, "fremder Stand angenommen")
# Jede Datei fehlerfrei und ohne Dubletten gegen das, was vor ihr geladen ist.
davor = list(wk.eingebaute())
for name in sorted(n for n in os.listdir(wd.MITGELIEFERT) if n.endswith(".json")):
    p = wd.lesen(os.path.join(wd.MITGELIEFERT, name), list(davor))
    pruefe(not p.fehler and not p.doppelt, f"{name}: {p.fehler[:2]} {p.doppelt[:2]}")
    davor += p.reihen
fasen = next((r for r in mitgeliefert if r.kennung == "garant-208080"), None)
fasen_p1 = [e for w in (wk.werkzeuge(fasen) if fasen else []) for e in w.schnittwerte.get("P1", [])]
pruefe(fasen_p1 and all(e.vc == 60 for e in fasen_p1), f"208080 in P1: {fasen_p1[:1]}")
# Für die Prüfungen des Einlesens: ohne die Liste (sonst wäre vieles doppelt).
wd.MITGELIEFERT = os.path.join(tmp, "ohne_liste")
wd._mitgeliefert = None

# --- Das Beispiel – gegen eine leere Kiste gelesen (die eingebaute hat es schon) -------------
p = wd.lesen(wd.BEISPIEL, vorhandene=[])
pruefe(not p.fehler and not p.doppelt, f"Beispiel: {p.fehler} {p.doppelt}")
pruefe(len(p.reihen) >= 2 and p.anzahl >= 3, f"Beispiel: {len(p.reihen)} Reihen, {p.anzahl} Größen")
kugel = next((r for r in p.reihen if r.kennung == "holex-207125"), None)
pruefe(kugel is not None, f"holex-207125 fehlt: {[r.kennung for r in p.reihen]}")
if kugel is not None:
    pruefe(kugel.datei == "werkzeugkiste_beispiel.json" and kugel.marke == "HOLEX", "Datei, Marke")
    pruefe("aus Datei" in kugel.quelle, f"Quelle: {kugel.quelle!r}")
    w6 = next(w for w in wk.werkzeuge(kugel) if w.durchmesser == 6)
    pruefe(
        w6.name == "HOLEX 207125 6" and w6.artikel == "207125 6" and w6.schneiden == 2,
        f"Ø 6: {w6.name!r} {w6.artikel!r} z{w6.schneiden}",
    )
    pruefe(
        w6.hersteller == "Hoffmann Group" and w6.link.endswith("207125-6"), "Ø 6: Hersteller, Link"
    )
    p1 = next(e for e in w6.schnittwerte["P1"] if e.art == wz.SCHLICHTEN)
    pruefe(
        p1.vc == 140 and nahe(p1.fz, 0.037) and nahe(p1.ap, 0.3) and nahe(p1.ae, 0.3),
        f"Ø 6 P1 Schlichten: {p1}",
    )
    m = next(e for e in w6.schnittwerte["M"] if e.art == wz.SCHLICHTEN)
    pruefe(m.vc == 80 and m.fz > 0, f"Ø 6 M Schlichten (fz Richtwert): {m}")
    schruppen = next(e for e in w6.schnittwerte["P1"] if e.art == wz.SCHRUPPEN)
    pruefe(0 < schruppen.vc <= 140, f"Ø 6 P1 Schruppen (Richtwert, nie über 140): {schruppen}")
    pruefe(
        wk.RICHTWERTE not in w6.bezeichnung
        and "TiAlN" in w6.bezeichnung
        and "23.93" in w6.bezeichnung,
        f"Ø 6 Bezeichnung: {w6.bezeichnung!r}",
    )
# Gegen die eingebaute Kiste ist das Beispiel doppelt: dieselben Artikel (HOLEX 207125, 206357).
p = wd.lesen(wd.BEISPIEL)
pruefe(
    not p.reihen and p.doppelt and any("Artikel" in d for d in p.doppelt),
    f"Beispiel gegen die Kiste: {[r.kennung for r in p.reihen]} {p.doppelt[:2]}",
)

# --- Eine eigene Datei mit Dubletten und Fehlern -------------------------------------------
masse_12 = {"durchmesser": 12, "schneidenlaenge": 26, "gesamtlaenge": 83, "schaft": 12}
reihe_a = {
    "kennung": "probe-a",
    "art": "schaftfraeser",
    "hersteller": "Probe GmbH",
    "marke": "PROBE",
    "titel": "Probe VHM",
    "quelle": "Probe, 2026-10-10",
    "gemeinsam": {"schneiden": 4, "schneidstoff": "HM", "beschichtung": "TiAlN"},
    "schnittwerte": {"P1": {"schruppen": {"vc": 200, "f": 0.4}}},
    "groessen": [
        {"durchmesser": 12, "schneidenlaenge": 26, "gesamtlänge": 83, "schaft": 12, "artikel": "P-12"},
        dict(masse_12, artikel="p -12"),  # dieselbe Artikelnummer, anders geschrieben
        dict(masse_12),  # ohne Nummer, exakt dieselben Maße
        dict(masse_12, artikel="P-12-X"),  # andere Nummer, dieselben Maße: ein anderes Produkt
        {"durchmesser": 10, "schneidenlaenge": 22, "gesamtlaenge": 72, "schaft": 10, "artikel": "P-10", "unsinn": 1},
    ],
}  # fmt: skip
reihe_b = dict(reihe_a, titel="Kennung doppelt")
reihe_c = dict(reihe_a, kennung=wk.eingebaute()[0].kennung, titel="Kennung eingebaut")
reihe_d = dict(reihe_a, kennung="probe-d", art="laserschwert")
reihe_e = dict(reihe_a, kennung="Probe_E")
reihe_k = {
    "kennung": "probe-k",
    "art": "konikfraeser",
    "hersteller": "Probe GmbH",
    "titel": "Probe Tonnenfräser konische Form, TiAlN",
    "quelle": "Probe, 2026-10-10",
    "gemeinsam": {"schneiden": 4, "beschichtung": "TiAlN"},
    "groessen": [{"durchmesser": 16, "gesamtlaenge": 90, "schaft": 16, "artikel": "K-16"}],
}  # fmt: skip
reihe_f = {
    "kennung": "probe-f",
    "art": "bohrer",
    "hersteller": "Probe GmbH",
    "titel": "Probe Bohrer",
    "quelle": "Probe, 2026-10-10",
    "groessen": [
        {"durchmesser": 8.5, "schneiden": 2, "gesamtlaenge": 100, "artikel": "B-85", "schneidstoff": "Unobtainium"}
    ],
    "schnittwerte": {"XX": {"bohren": {"vc": 1}}, "P1": {"schruppen": {"vc": 1}, "bohren": {"vc": 80, "f": 0.2}}},
}  # fmt: skip
datei1 = schreibe(
    os.path.join(tmp, "werkzeugkiste_probe.json"),
    [reihe_a, reihe_b, reihe_c, reihe_d, reihe_e, reihe_f, reihe_k],
)
p = wd.lesen(datei1)
pruefe(
    [r.kennung for r in p.reihen] == ["probe-a", "probe-f", "probe-k"],
    f"Reihen: {[r.kennung for r in p.reihen]}",
)
# Der Konikfräser ohne Kegelwinkel mit „Tonnenfräser“ im Titel: zwei Hinweise, die Beschichtung
# steht nicht doppelt in der Bezeichnung (Manuels Agent, 2026-10-10).
pruefe(
    any("kegelwinkel" in h for h in p.hinweise) and any("tonnenfräser" in h for h in p.hinweise),
    f"Konik-Hinweise: {p.hinweise}",
)
wk_k = wk.werkzeuge(p.reihen[2])[0]
pruefe(wk_k.bezeichnung.lower().count("tialn") == 1, f"Beschichtung doppelt: {wk_k.bezeichnung!r}")
pruefe(len(p.fehler) == 4, f"Fehler ({len(p.fehler)}): {p.fehler}")
pruefe(len(p.doppelt) == 2, f"Dubletten ({len(p.doppelt)}): {p.doppelt}")
pruefe(
    any("Artikel" in d for d in p.doppelt) and any("Maße" in d for d in p.doppelt),
    f"Gründe: {p.doppelt}",
)
a = p.reihen[0] if p.reihen else None
if a is not None:
    pruefe(
        a.anzahl == 3 and [g.get("artikel") for g in a.groessen] == ["P-12", "P-12-X", "P-10"],
        f"probe-a: {[g.get('artikel') for g in a.groessen]}",
    )
    pruefe(
        any("gesamtlänge" in h for h in p.hinweise) and any("unsinn" in h for h in p.hinweise),
        f"Hinweise: {p.hinweise}",
    )
    wa = wk.werkzeuge(a)
    pruefe(
        wa[0].gesamtlaenge == 83 and wa[0].name == "PROBE P-12" and "TiAlN" in wa[0].bezeichnung,
        f"P-12: {wa[0]}",
    )
    pruefe(wa[0].schneidstoff == wz.VHM, f"„HM“ nicht als VHM gelesen: {wa[0].schneidstoff!r}")
    s = next(e for e in wa[0].schnittwerte["P1"] if e.art == wz.SCHRUPPEN)
    pruefe(s.vc == 200 and nahe(s.fz, 0.1), f"P-12 Schruppen (f 0,4 bei z 4): {s}")
    pruefe(
        any("XX" in h for h in p.hinweise) and any("schruppen" in h for h in p.hinweise),
        f"Bohrer-Hinweise: {p.hinweise}",
    )
    pruefe(any("Unobtainium" in h for h in p.hinweise), f"Schneidstoff-Hinweis fehlt: {p.hinweise}")
    wf = wk.werkzeuge(p.reihen[1])[0]
    b = wf.schnittwerte["P1"][0]
    pruefe(b.art == wz.BOHREN and b.vc == 80 and nahe(b.fz, 0.1), f"B-85 Bohren: {b}")

# --- Einlesen in den Ordner: in reihen(), nochmal ersetzt, zweite Datei mit Dublette ------
p = wd.einlesen(datei1)
pruefe(p.ziel and os.path.isfile(p.ziel) and not p.ersetzt, f"einlesen: {p.ziel!r} {p.ersetzt}")
pruefe(
    wk.reihe("probe-a") is not None and wk.reihe("probe-a").datei == "werkzeugkiste_probe.json",
    "nicht in der Kiste",
)
pruefe(len(wk.reihen()) == eingebaut + 3, f"Reihen: {len(wk.reihen())} statt {eingebaut + 3}")
p = wd.einlesen(datei1)
pruefe(
    sorted(p.ersetzt) == ["probe-a", "probe-f", "probe-k"]
    and len(p.doppelt) == 2
    and len(p.reihen) == 3,
    f"nochmal: {p.ersetzt} {p.doppelt}",
)
pruefe(len(wk.reihen()) == eingebaut + 3, "nochmal: Reihen doppelt")
reihe_g = {
    "kennung": "probe-g",
    "art": "schaftfraeser",
    "hersteller": "Probe GmbH",
    "marke": "PROBE",
    "titel": "Probe VHM, noch einmal",
    "quelle": "Probe, 2026-10-10",
    "gemeinsam": {"schneiden": 4},
    "groessen": [
        dict(masse_12, artikel="P-12"),
        {"durchmesser": 16, "schneidenlaenge": 32, "gesamtlaenge": 92, "schaft": 16, "artikel": "P-16"},
    ],
}  # fmt: skip
datei2 = schreibe(os.path.join(tmp, "werkzeugkiste_probe2.json"), [reihe_g, reihe_a])
p = wd.einlesen(datei2)
pruefe(
    len(p.reihen) == 1 and p.reihen[0].anzahl == 1 and len(p.doppelt) == 1 and len(p.fehler) == 1,
    f"zweite Datei: {p.doppelt} {p.fehler}",
)
pruefe(p.fehler and "werkzeugkiste_probe.json" in p.fehler[0], f"belegt durch: {p.fehler}")
pruefe(len(wk.reihen()) == eingebaut + 4, f"Reihen: {len(wk.reihen())}")
wd.vergessen()  # wie nach einem Neustart: der Ordner wird neu gelesen
pruefe(
    [r.kennung for r in wd.eingelesene()] == ["probe-a", "probe-f", "probe-k", "probe-g"],
    f"neu gelesen: {[r.kennung for r in wd.eingelesene()]}",
)
pruefe(wd.entfernen("werkzeugkiste_probe2.json") and len(wk.reihen()) == eingebaut + 3, "entfernen")
pruefe(not wd.entfernen("gibt_es_nicht.json"), "entfernen ohne Datei")
vorlage = wd.vorlage_schreiben(os.path.join(tmp, "vorlage.json"))
with open(vorlage, encoding="utf-8") as datei:
    pruefe(json.load(datei)["format"] == wd.FORMAT, "Vorlage")
p = wd.lesen(os.path.join(tmp, "kaputt.json"))
pruefe(len(p.fehler) == 1 and not p.reihen, f"fehlende Datei: {p.fehler}")

# --- In die eigene Werkzeugkiste: exakt verglichen -----------------------------------------
bibliothek = wz.Bibliothek([])
bericht = wk.hinzufuegen(bibliothek, ["probe-a"])
pruefe(len(bericht.neu) == 3 and not bericht.schon_da, f"hinzufuegen: {len(bericht.neu)}")
nochmal = wk.hinzufuegen(bibliothek, ["probe-a"])
pruefe(not nochmal.neu and len(nochmal.schon_da) == 3, f"nochmal: {nochmal}")
if bibliothek.werkzeuge:
    gleich = wz.Werkzeug.aus_dict(bibliothek.werkzeuge[0].als_dict())
    gleich.name, gleich.artikel, gleich.kennung = "ganz anders", "", "x"
    pruefe(
        wk.gleiche_masse(bibliothek.werkzeuge[0], gleich) and wk._schon_da(bibliothek, gleich),
        "gleiche Maße ohne Nummer nicht erkannt",
    )
    gleich.artikel = "ANDERS"
    pruefe(not wk._schon_da(bibliothek, gleich), "andere Artikelnummer gilt als dasselbe Werkzeug")
    gleich.artikel = ""
    gleich.schneidenlaenge += 0.5
    pruefe(
        not wk.gleiche_masse(bibliothek.werkzeuge[0], gleich),
        "andere Schneidenlänge gilt als gleich",
    )

# --- „ae max“ (P-2026-10-11-40): ae_max_d und ae_max kommen als Grenze in den Einsatz -----------
datei_max = schreibe(
    os.path.join(tmp, "werkzeugkiste_aemax.json"),
    [
        {
            "kennung": "probe-kugel-aemax",
            "art": "kugelfraeser",
            "hersteller": "Probe",
            "titel": "Kugelfräser mit Grenze",
            "quelle": "Prüfung, 2026-10-11",
            "gemeinsam": {"schneiden": 2, "schneidstoff": "vhm"},
            "schnittwerte": {"N1": {"schlichten": {"vc": 300, "fz": 0.05, "ae_max_d": 0.05}}},
            "groessen": [
                {"durchmesser": 8.0, "artikel": "PROBE-8", "gesamtlaenge": 63.0},
                {
                    "durchmesser": 10.0,
                    "artikel": "PROBE-10",
                    "gesamtlaenge": 72.0,
                    "schnittwerte": {"N1": {"schlichten": {"ae_max": 0.7}}},
                },
            ],
        }
    ],
)
p = wd.lesen(datei_max, vorhandene=[])
pruefe(
    not p.fehler and not any("ae_max" in h for h in p.hinweise), f"ae max: {p.fehler} {p.hinweise}"
)
if p.reihen:
    grenzen = {}
    for w in wk.werkzeuge(p.reihen[0]):
        schlicht = next((e for e in w.schnittwerte.get("N1", []) if e.art == wz.SCHLICHTEN), None)
        grenzen[w.durchmesser] = schlicht.ae_max if schlicht is not None else None
    pruefe(
        nahe(grenzen.get(8.0) or 0, 0.4) and nahe(grenzen.get(10.0) or 0, 0.7),
        f"ae max je Größe: {grenzen}",
    )
    # In der Werkzeugverwaltung gespeichert und wieder gelesen: dieselbe Grenze.
    zurueck = wz.Einsatz.aus_dict(wz.Einsatz(art=wz.SCHLICHTEN, ae_max=0.4).als_dict())
    pruefe(nahe(zurueck.ae_max, 0.4), f"ae max gespeichert: {zurueck.ae_max}")
    pruefe("ae_max" not in wz.Einsatz(art=wz.SCHLICHTEN).als_dict(), "ae max 0 wird gespeichert")

shutil.rmtree(tmp, ignore_errors=True)
wd.vergessen()
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
