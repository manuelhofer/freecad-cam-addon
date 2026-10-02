# Prüft die Werkzeugkiste der Hersteller ohne Oberfläche (W-007, P-2026-10-02-46): die Reihen
# mit Manuels Größen und den Maßen nach Norm, die Schnittwerte je Werkstoffklasse (Werte für
# 1.4301 gelten für 1.4404), das Hinzufügen mit freien Nummern, ohne Doppelte und ohne die
# Änderungen des Benutzers zu überschreiben – und dass alles Speichern und Laden übersteht.
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import schnittdaten as sd
from camaddon import sprache
from camaddon import werkstoffe as ws
from camaddon import werkzeuge as wz
from camaddon import werkzeugkiste as wk

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nahe(a, b, toleranz=1e-6):
    return abs(a - b) <= toleranz


vorher = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")

# --- Werkstoffklassen ---------------------------------------------------------------------
for kennung, soll in (
    ("1.0038", "P1"), ("1.0503", "P1"), ("1.7131", "P1"), ("1.7225", "P2"), ("1.2379", "P2"),
    ("1.4021", "P2"), ("1.4301", "M"), ("1.4462", "M"), ("0.6025", "K"), ("0.7040", "K"),
    ("3.2315", "N1"), ("3.2381", "N1"), ("2.0401", "N2"), ("2.0060", "N2"), ("POM-C", "N3"),
    ("3.7165", "S"), ("2.4668", "S"), ("1.2343+H", "H"), ("1.2379+H", "H"),
):  # fmt: skip
    pruefe(ws.klasse_von(kennung) == soll, f"Klasse {kennung}: {ws.klasse_von(kennung)!r}")
pruefe(ws.klasse_von("eigen-1") == "", "eigener Werkstoff mit Klasse")
pruefe(
    all(ws.klasse(w) in ws.KLASSEN for w in ws.mitgelieferte()),
    "ein mitgelieferter Werkstoff ohne Klasse",
)
pruefe(
    {ws.klasse_von(k) for k in wk.VERTRETER.values() if k != wz.ALLE} == set(ws.KLASSEN) - {"P1"},
    "die Vertreter decken nicht jede Klasse",
)

# --- die Reihen ----------------------------------------------------------------------------
reihen = wk.reihen()
kennungen = [r.kennung for r in reihen]
pruefe(len(set(kennungen)) == len(kennungen), f"doppelte Kennung: {kennungen}")
arten = {r.art for r in reihen}
pruefe(arten == set(wz.ARTEN), f"ohne Beispiel: {sorted(set(wz.ARTEN) - arten)}")

bohrer = wk.werkzeuge(wk.reihe("ceratizit-classicline-din338"))
durchmesser = [w.durchmesser for w in bohrer]
pruefe(
    durchmesser == [float(d) for d in wk._BOHRER] and len(bohrer) == 32,
    f"Bohrer: {durchmesser}",
)
b85 = next(w for w in bohrer if w.durchmesser == 8.5)
pruefe(
    (b85.schneidenlaenge, b85.gesamtlaenge, b85.schaft, b85.spitzenwinkel) == (75, 117, 8.5, 118),
    f"Ø 8,5 nach DIN 338: {b85.schneidenlaenge}, {b85.gesamtlaenge}",
)
pruefe(b85.hersteller == "Ceratizit" and b85.schneidstoff == wz.HSS, "Ø 8,5: Hersteller")
pruefe(b85.link.startswith("https://") and b85.katalog.startswith("https://"), "Ø 8,5: Links")
stahl = b85.einsaetze(wz.ALLE)
pruefe(len(stahl) == 1 and stahl[0].art == wz.BOHREN, f"Ø 8,5 Einsätze: {stahl}")
# f bei Ø 8,5 zwischen 0,15 (Ø 8) und 0,20 (Ø 12): 0,156 – je Schneide 0,078.
pruefe(stahl[0].vc == 30 and nahe(stahl[0].fz, 0.078), f"Ø 8,5 Stahl: {stahl[0]}")
v2a = b85.einsaetze("1.4301")[0]
pruefe(v2a.vc < stahl[0].vc and v2a.fz < stahl[0].fz, f"Ø 8,5 in 1.4301: {v2a}")
alu = b85.einsaetze("3.2315")[0]
pruefe(alu.vc > stahl[0].vc, f"Ø 8,5 in Alu: {alu}")
pruefe(len(b85.schnittwerte) == len(wk.VERTRETER), f"Tabellen: {list(b85.schnittwerte)}")

gewinde = wk.werkzeuge(wk.reihe("guehring-5596"))
pruefe(
    [w.durchmesser for w in gewinde]
    == [2, 2.5, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 27, 30],
    f"Gewindebohrer: {[w.durchmesser for w in gewinde]}",
)
m10 = next(w for w in gewinde if w.durchmesser == 10)
pruefe(
    m10.art == wz.GEWINDEBOHRER_RECHTS and m10.steigung == 1.5 and m10.artikel == "5596 10,000",
    f"M10: {m10.art}, P {m10.steigung}, {m10.artikel!r}",
)
pruefe("Kernloch Ø 8.5" in m10.bezeichnung, f"M10: {m10.bezeichnung!r}")
pruefe(next(w for w in gewinde if w.durchmesser == 12).artikel == "", "M12 mit erfundener Nummer")
n, vf, _ = sd.rechne(m10, m10.einsaetze(wz.ALLE)[0])
pruefe(nahe(vf, n * 1.5, 1e-6) and n > 0, f"M10: n {n}, vf {vf}")

# Jongen 494W nach dem Katalog 11/2025 (seit P-2026-10-02-91): Ø 6–20 scharfkantig, Ø 4 und 5
# nur mit Eckenradius (als Torusfräser), Ø 3 gibt es nicht.
fraeser = wk.werkzeuge(wk.reihe("jongen-494w"))
pruefe([w.durchmesser for w in fraeser] == [6, 8, 10, 12, 16, 20], "Jongen: Größen")
mit_radius = wk.werkzeuge(wk.reihe("jongen-494w-r"))
pruefe(
    [(w.durchmesser, w.eckradius, w.art) for w in mit_radius]
    == [(4, 0.4, wz.TORUSFRAESER), (5, 0.5, wz.TORUSFRAESER)],
    f"Jongen mit Radius: {[(w.durchmesser, w.eckradius) for w in mit_radius]}",
)
f12 = next(w for w in fraeser if w.durchmesser == 12)
pruefe(
    (f12.schneiden, f12.schneidenlaenge, f12.gesamtlaenge, f12.schaft) == (4, 26, 84, 12)
    and (f12.hals_d, f12.hals_laenge) == (11.2, 10),
    f"Jongen Ø 12: z {f12.schneiden}, {f12.schneidenlaenge}/{f12.gesamtlaenge}, Hals {f12.hals_d}",
)
pruefe(f12.artikel == "VU494M12B-HI06", f"Jongen Ø 12: {f12.artikel!r}")
pruefe(f12.katalog.endswith(".pdf") and "VU494M12B-HI06" in f12.link, f"Links: {f12.link!r}")
# Die Werte des Katalogs: Eckfräsen in Baustahl vc 210, fz 0,07, ap 22,2, ae 5,4; in 1.4301
# (INOX austenitisch) vc 115, fz 0,05.
eck = next(e for e in f12.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
pruefe((eck.vc, eck.fz, eck.ap, eck.ae) == (210, 0.07, 22.2, 5.4), f"Ø 12 Eckfräsen: {eck}")
eck_m = next(e for e in f12.einsaetze("1.4301") if e.art == wz.SCHRUPPEN)
pruefe((eck_m.vc, eck_m.fz) == (115, 0.05), f"Ø 12 Eckfräsen in 1.4301: {eck_m}")
arten_12 = [e.art for e in f12.einsaetze(wz.ALLE)]
pruefe(
    arten_12 == [wz.VOLLNUT, wz.SCHRUPPEN, wz.DYNAMISCH, wz.SCHLICHTEN, wz.PLANEN],
    f"Ø 12: {arten_12}",
)
# Planen am Schaftfräser (P-2026-10-02-54): 0,7 D breit, 0,1 D tief, vc und fz wie Schruppen.
planen_12 = next(e for e in f12.einsaetze(wz.ALLE) if e.art == wz.PLANEN)
schruppen_12 = next(e for e in f12.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
pruefe(
    (planen_12.ae, planen_12.ap) == (8.4, 1.2)
    and (planen_12.vc, planen_12.fz) == (schruppen_12.vc, schruppen_12.fz),
    f"Ø 12 Planen: {planen_12}",
)
dynamisch = next(e for e in f12.einsaetze(wz.ALLE) if e.art == wz.DYNAMISCH)
pruefe(
    (dynamisch.vc, dynamisch.fz) == (250, 0.06)
    and nahe(dynamisch.ae, 2.4)
    and nahe(dynamisch.ap, 24.7),
    f"Ø 12 trochoidal: {dynamisch}",
)
# Je Klasse eine Tabelle; was keine eigene hat, nimmt die seiner Klasse – sonst „alle“.
pruefe(f12.einsaetze("1.4404") is f12.schnittwerte["1.4301"], "1.4404 nicht wie 1.4301")
pruefe(f12.einsaetze("1.6582") is f12.schnittwerte["1.7225"], "1.6582 nicht wie 1.7225")
pruefe(f12.einsaetze("2.4668") is f12.schnittwerte["3.7165"], "Inconel nicht wie Titan")
pruefe(f12.einsaetze("1.0570") is f12.schnittwerte[wz.ALLE], "St 52 nicht wie „alle“")
pruefe(f12.einsaetze("eigen-1") is f12.schnittwerte[wz.ALLE], "eigener nicht wie „alle“")
pruefe(f12.verwandter("1.4404") == "1.4301", f"verwandt: {f12.verwandter('1.4404')!r}")
pruefe(f12.verwandter("1.4301") is None, "1.4301 hat eigene Werte")
# Trotzdem eigene Werte je Werkstoff (P-2026-10-02-50; Manuel: „dennoch die Möglichkeit, für
# die einzelnen Werkstoffe auch unterschiedliche Werte zu setzen“): 1.4404 bekommt eine Kopie
# der Zeilen von 1.4301; ändert man sie, bleibt 1.4301, wie es war, und 1.4571 nimmt weiter 1.4301.
v4a = f12.eigene_anlegen("1.4404")
pruefe(
    [e.art for e in v4a] == [e.art for e in f12.schnittwerte["1.4301"]]
    and v4a[0] is not f12.schnittwerte["1.4301"][0],
    f"eigene für 1.4404: {v4a}",
)
v4a[0].vc = 55.0
pruefe(f12.einsaetze("1.4404")[0].vc == 55.0, "1.4404: eigene Werte gelten nicht")
pruefe(f12.schnittwerte["1.4301"][0].vc != 55.0, "1.4301 mit verändert")
pruefe(f12.einsaetze("1.4571") is f12.schnittwerte["1.4301"], "1.4571 nicht mehr wie 1.4301")
pruefe(f12.eigene_anlegen("1.4404") is v4a, "zweites Anlegen überschreibt")
del f12.schnittwerte["1.4404"]
gehaertet = next(e for e in f12.einsaetze("1.2379+H") if e.art == wz.SCHRUPPEN)
weich = next(e for e in f12.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
pruefe(0 < gehaertet.vc < weich.vc and 0 < gehaertet.fz < weich.fz, "gehärtet nicht langsamer")

planfraeser = wk.werkzeuge(wk.reihe("sandvik-coromill-345"))[0]
planen = planfraeser.einsaetze(wz.ALLE)[0]
pruefe(
    planfraeser.schneiden == 4 and planen.art == wz.PLANEN and planen.vc == 280,
    f"Messerkopf: z {planfraeser.schneiden}, {planen}",
)
pruefe(nahe(planen.ae, 35) and nahe(planen.fz, 0.2), f"Messerkopf: {planen}")

entgrater = wk.werkzeuge(wk.reihe("garant-208165"))
pruefe(
    [w.artikel for w in entgrater] == [f"208165 {d}" for d in (6, 8, 10, 12, 16)]
    and all(w.art == wz.FASENFRAESER and w.spitzenwinkel == 60 for w in entgrater),
    f"Garant: {[(w.artikel, w.spitzenwinkel) for w in entgrater]}",
)
# Laut Datenblatt: Ø 12 L 83, in Stahl bis 750 N/mm² vc 115, fz 0,08; in Titan vc 50.
g12 = next(w for w in entgrater if w.durchmesser == 12)
fase = g12.einsaetze(wz.ALLE)[0]
pruefe(
    g12.gesamtlaenge == 83 and (fase.vc, fase.fz) == (115, 0.08) and g12.katalog.endswith(".pdf"),
    f"Garant Ø 12: L {g12.gesamtlaenge}, {fase}, {g12.katalog!r}",
)
pruefe(g12.einsaetze("3.7165")[0].vc == 50, f"Garant Ø 12 in Titan: {g12.einsaetze('3.7165')}")

platten = wk.werkzeuge(wk.reihe("iso-wendeplatten"))
pruefe(
    [w.artikel[0] for w in platten] == list("CDVWTSR")
    and all(w.art == wz.DREHWERKZEUG and not w.schnittwerte for w in platten),
    f"Wendeplatten: {[w.artikel for w in platten]}",
)
pruefe(next(w for w in platten if w.artikel.startswith("V")).plattenwinkel == 35, "V nicht 35°")

# Jedes Werkzeug jeder Reihe übersteht Speichern und Laden – und hat, wo es Schnittwerte
# gibt, je Einsatz vc und (außer beim Gewindebohrer) fz.
for r in reihen:
    for w in wk.werkzeuge(r):
        pruefe(wz.Werkzeug.aus_dict(w.als_dict()) == w, f"{r.kennung} {w.name}: nicht gleich")
        if not r.schnittwerte:
            continue
        for kennung, liste in w.schnittwerte.items():
            pruefe(bool(liste), f"{r.kennung} {w.name} {kennung}: leer")
            for e in liste:
                ohne_fz = wz.gewindebohrer(w.art)
                pruefe(
                    e.vc > 0 and (e.fz > 0 or ohne_fz),
                    f"{r.kennung} {w.name} {kennung} {e.art}: vc {e.vc}, fz {e.fz}",
                )

# --- Richtwerte für ein neues Werkzeug (P-2026-10-02-47) --------------------------------------
neu = wz.Werkzeug(art=wz.SCHAFTFRAESER, durchmesser=10.0, schneiden=3, schneidenlaenge=22.0)
pruefe(wk.richtwerte_moeglich(neu), "Ø 10 ohne Richtwerte")
pruefe(wk.richtwerte_eintragen(neu) == len(wk.VERTRETER), f"Richtwerte: {list(neu.schnittwerte)}")
schruppen = next(e for e in neu.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
pruefe(schruppen.vc == 180 and nahe(schruppen.fz, 0.05), f"Ø 10 Schruppen: {schruppen}")
pruefe(len(neu.einsaetze("1.4404")) == 5, "Ø 10: Edelstahl ohne Zeilen")
# Was schon da ist, bleibt; nur fehlende Klassen kommen dazu.
eigen = wz.Werkzeug(art=wz.SCHAFTFRAESER, durchmesser=10.0)
eigen.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=1, ap=10, vc=85, fz=0.1)]
pruefe(wk.richtwerte_eintragen(eigen) == len(wk.VERTRETER) - 1, "eigene Zeilen überschrieben?")
pruefe(eigen.schnittwerte[wz.ALLE][0].vc == 85 and len(eigen.schnittwerte[wz.ALLE]) == 1, "„alle“")
pruefe(wk.richtwerte_eintragen(eigen) == 0, "zweimal eingetragen")
pruefe(not wk.richtwerte_moeglich(wz.Werkzeug(art=wz.SCHAFTFRAESER)), "ohne Ø möglich")
pruefe(not wk.richtwerte_moeglich(wz.Werkzeug(art=wz.DREHWERKZEUG)), "Drehwerkzeug möglich")

# --- in die eigene Werkzeugkiste -----------------------------------------------------------
eigene = wz.standardwerkzeug(1)
bibliothek = wz.Bibliothek([eigene])
bericht = wk.hinzufuegen(bibliothek, kennungen)
gesamt = sum(r.anzahl for r in reihen)
pruefe(len(bericht.neu) == gesamt and not bericht.schon_da, f"neu {len(bericht.neu)}/{gesamt}")
nummern = sorted(w.nummer for w in bibliothek.werkzeuge)
pruefe(nummern == list(range(1, gesamt + 2)), f"Nummern: {nummern[:5]} … {nummern[-3:]}")
pruefe(bibliothek.mit_nummer(1) is eigene, "T1 nicht mehr das eigene")
# Was der Benutzer ändert, bleibt; ein zweites Mal kommt nichts doppelt.
jongen_12 = next(w for w in bibliothek.werkzeuge if w.name == "494W D12")
jongen_12.schnittwerte[wz.ALLE][0].vc = 99.0
nochmal = wk.hinzufuegen(bibliothek, kennungen)
pruefe(not nochmal.neu and len(nochmal.schon_da) == gesamt, f"doppelt: {len(nochmal.neu)}")
pruefe(jongen_12.schnittwerte[wz.ALLE][0].vc == 99.0, "Änderung überschrieben")
# Nach dem Neustart noch da: speichern, laden, gleich.
pfad = os.path.join(tempfile.mkdtemp(), "CamAddon", wz.DATEINAME)
bibliothek.speichern(pfad)
geladen = wz.Bibliothek.laden(pfad)
pruefe(geladen.gleich(bibliothek), "nach Speichern und Laden anders")
wieder = next(w for w in geladen.werkzeuge if w.name == "494W D12")
pruefe(
    wieder.hersteller == "Jongen" and wieder.link == jongen_12.link and wieder.katalog,
    f"geladen: {wieder.hersteller!r}, {wieder.link!r}",
)
pruefe(wieder.einsaetze("1.4571") == wieder.schnittwerte["1.4301"], "geladen: Klasse M")
pruefe("Jongen" in wz.zeile(wieder), f"Zeile ohne Hersteller: {wz.zeile(wieder)!r}")
pruefe(wz.passt(wieder, "jongen 494w"), "Suche findet den Hersteller nicht")
groesse = os.path.getsize(pfad)
print(f"Werkzeugkiste: {gesamt} Werkzeuge, Datei {groesse // 1024} KB")
pruefe(groesse < 2_000_000, f"Datei zu groß: {groesse}")

sprache.setze_sprache(vorher)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
