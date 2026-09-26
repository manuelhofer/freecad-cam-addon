# Prüft die Halter ohne Oberfläche (W-002 Stufe D, halter.py): Kontur, Länge und
# Radius eines Halters, Vorlagen, Anlegen, Kopieren und Löschen in der Bibliothek
# (die Werkzeuge verlieren ihren Halter), Speichern und Laden – auch eine alte
# Datei ohne Halter und Unlesbares –, die geschätzte Länge ab Spindelnase mit
# Halter (Halterlänge + Gesamtlänge − Spanntiefe, mindestens bis zur Reichweite).
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import halter as hl
from camaddon import sprache
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nahe(a, b):
    return abs(a - b) < 1e-9


vorher = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")

# --- Ein Halter: Länge, Radius, Kontur ---------------------------------------------------
er32 = hl.aus_vorlage("er32")
pruefe(er32.name == "Spannzangenfutter ER32 · SK40", f"Name: {er32.name}")
pruefe(er32.bezeichnung == "Beispielmaße – nach Katalog prüfen", "Bezeichnung der Vorlage")
pruefe(nahe(er32.laenge, 70) and nahe(er32.spanntiefe, 40), f"ER32: {er32.laenge}")
pruefe(nahe(er32.groesster_durchmesser, 63), "größter Ø")
pruefe(nahe(er32.radius_bei(0), 31.5) and nahe(er32.radius_bei(8), 31.5), "Flansch")
pruefe(nahe(er32.radius_bei(16), 31.5), "an der Stufe gilt der größere Radius")
pruefe(nahe(er32.radius_bei(40), 25) and nahe(er32.radius_bei(70), 25), "Körper")
pruefe(er32.radius_bei(70.1) == 0 and er32.radius_bei(-1) == 0, "außerhalb 0")
pruefe(er32.kontur() == [(0, 31.5), (16, 31.5), (16, 25), (70, 25)], f"{er32.kontur()}")
schrumpf = hl.aus_vorlage("schrumpf_12")
pruefe(nahe(schrumpf.radius_bei(16 + 32), (32 + 24) / 4), "Kegel: in der Mitte der Mittelwert")
for schluessel in hl.VORLAGEN:
    h = hl.aus_vorlage(schluessel)
    pruefe(h.laenge > 0 and h.name and h.abschnitte, f"Vorlage {schluessel}")
leer = hl.Halter(abschnitte=[hl.Abschnitt(40, 30, 30)])
pruefe(hl.text(leer) == "Halter, 40 mm lang", f"ohne Namen: {hl.text(leer)}")

# --- In der Bibliothek ------------------------------------------------------------------
b = wz.Bibliothek()
a = b.neuer_halter("er32")
a2 = b.neuer_halter("er32")
pruefe(a2.name == "Spannzangenfutter ER32 · SK40 (2)", f"zweiter aus derselben Vorlage: {a2.name}")
k = b.kopiere_halter(a)
pruefe(k.name == "Spannzangenfutter ER32 · SK40 (3)" and k.kennung != a.kennung, "Kopie")
k.abschnitte[1].laenge = 80
pruefe(nahe(a.laenge, 70), "Kopie teilt Abschnitte")
n = b.neuer_halter()
pruefe(n.name == "" and n.abschnitte == [], "leerer Halter")

t1 = b.neues_werkzeug()
t1.durchmesser, t1.schneidenlaenge, t1.gesamtlaenge = 12, 26, 83
t2 = b.neues_werkzeug()
t1.halter = t2.halter = a.kennung
pruefe(b.halter_von(t1) is a and b.halter_von(b.neues_werkzeug()) is None, "halter_von")
pruefe(b.benutzt_von(a) == [t1, t2], f"benutzt von: {b.benutzt_von(a)}")

# Länge ab Spindelnase: gemessen, sonst mit Halter geschätzt, ohne Halter 0.
pruefe(nahe(wz.laenge_mit_halter(t1, a), 70 + 83 - 40), f"geschätzt: {wz.laenge_mit_halter(t1, a)}")
pruefe(nahe(b.laenge_ab_spindelnase(t1), 113), "Länge ab Spindelnase mit Halter")
t1.laenge_spindelnase = 120
pruefe(nahe(b.laenge_ab_spindelnase(t1), 120), "gemessen gilt")
t1.laenge_spindelnase = 0
kurz = wz.Werkzeug(durchmesser=12, schneidenlaenge=26, gesamtlaenge=40)
pruefe(nahe(wz.laenge_mit_halter(kurz, a), 70 + 26), "mindestens bis zur Reichweite")
pruefe(b.laenge_ab_spindelnase(wz.Werkzeug(gesamtlaenge=83)) == 0, "ohne Halter 0")

# --- Speichern und Laden ----------------------------------------------------------------
pfad = os.path.join(tempfile.mkdtemp(), "CamAddon", wz.DATEINAME)
b.speichern(pfad)
g = wz.Bibliothek.laden(pfad)
pruefe(len(g.halter) == 4, f"Halter nach Laden: {len(g.halter)}")
ga = next(h for h in g.halter if h.kennung == a.kennung)
pruefe(ga.als_dict() == a.als_dict(), "Halter nach Laden gleich")
gt1 = next(w for w in g.werkzeuge if w.kennung == t1.kennung)
pruefe(g.halter_von(gt1) is ga, "Zuordnung nach Laden")
pruefe(g.gleich(b), "gleich nach Laden")
pruefe(
    [hl.text(h) for h in g.sortierte_halter()][0] == "Halter, 0 mm lang",
    "sortiert nach Name",
)

# Eine alte Datei ohne Halter; Unlesbares wird zum Standardwert.
alt = b.als_dict()
del alt["halter"]
for w in alt["werkzeuge"]:
    del w["halter"]
o = wz.Bibliothek.aus_dict(alt)
pruefe(o.halter == [] and all(w.halter == "" for w in o.werkzeuge), "alte Datei")
pruefe(wz.Bibliothek.aus_dict({**alt, "halter": 5}).halter == [], "Halter kein Array")
u = hl.Halter.aus_dict(
    {"spanntiefe": "x", "abschnitte": [{"laenge": -5, "d_oben": "12"}, "Unsinn"]}
)
pruefe(u.spanntiefe == 0 and len(u.abschnitte) == 1, f"unlesbarer Halter: {u}")
pruefe((u.abschnitte[0].laenge, u.abschnitte[0].d_oben) == (0, 12), f"{u.abschnitte[0]}")

# Löschen: Die Werkzeuge verlieren ihren Halter.
b.entferne_halter(a)
pruefe(a not in b.halter and t1.halter == "" and t2.halter == "", "entfernen")

sprache.setze_sprache(vorher)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
