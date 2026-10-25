# Prüft die Halter ohne Oberfläche (W-002 Stufe D, halter.py): Kontur, Länge und
# Radius eines Halters, Vorlagen, Anlegen, Kopieren und Löschen in der Bibliothek
# (die Werkzeuge verlieren ihren Halter), Speichern und Laden – auch eine alte
# Datei ohne Halter und Unlesbares –, die geschätzte Länge ab Spindelnase mit
# Halter (Halterlänge + Gesamtlänge − Spanntiefe, mindestens bis zur Reichweite).
# Die Richtung (Stufe E, Manuel 2026-09-30): gerade ist die Lage die der Aufnahme;
# „VDI30 angetrieben radial“ kippt das Werkzeug um 90° zur Bezugsrichtung X, 55 mm
# unter der Aufnahme; Drehung und Winkel drehen die Richtung; der Körper hat Kopf und
# Abgang; eine alte Datei ohne Richtung ist gerade. Vorlagen je Aufnahme (W-022): ER32 für HSK-A63
# mit dessen Flansch (26 × Ø 63), Schrumpf Ø12 für BT50 (38 × Ø 100); VDI ohne Aufnahme. Die
# Normreihen: jede Art, Größe und Länge so lang wie A, mit Flansch, Nase und Namen.
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
pruefe(
    er32.bezeichnung
    == "Maße nach der Katalogzeichnung von Hoffmann 300470 32 – mit deinem Halter vergleichen",
    f"Bezeichnung der Vorlage: {er32.bezeichnung}",
)
pruefe(er32.link == "https://www.hoffmann-group.com/DE/de/hom/p/300470-32", f"Link: {er32.link}")
# Nach der Katalogzeichnung (P-2026-10-16-39): Flansch SK40 Ø 63,55 × 19,1 ab der Spindelnase,
# Rundung, Körper Ø 48 bis 34, Kegel auf den Hals Ø 40 (38 … 47), Mutter Ø 50 × 23 – A = 70.
pruefe(nahe(er32.laenge, 70) and nahe(er32.spanntiefe, 40), f"ER32: {er32.laenge}")
pruefe(nahe(er32.groesster_durchmesser, 63.55), "größter Ø")
pruefe(nahe(er32.radius_bei(0), 31.775) and nahe(er32.radius_bei(8), 31.775), "Flansch")
pruefe(nahe(er32.radius_bei(19.1), 31.775), "an der Stufe gilt der größere Radius")
pruefe(nahe(er32.radius_bei(25), 24) and nahe(er32.radius_bei(42), 20), "Körper und Hals")
pruefe(nahe(er32.radius_bei(60), 25) and nahe(er32.radius_bei(70), 25), "Mutter")
pruefe(er32.radius_bei(70.1) == 0 and er32.radius_bei(-1) == 0, "außerhalb 0")
pruefe(er32.aufnahme == "SK40", f"Aufnahme: {er32.aufnahme!r}")

# --- Vorlagen je Aufnahme (W-022): der Flansch der Aufnahme statt SK40, der Körper bleibt -------
hsk = hl.aus_vorlage("er32", aufnahme="HSK-A63")
pruefe(hsk.name == "Spannzangenfutter ER32 · HSK-A63", f"Name: {hsk.name}")
pruefe(hsk.aufnahme == "HSK-A63", f"Aufnahme: {hsk.aufnahme!r}")
flansch = hsk.abschnitte[0]
pruefe(nahe(flansch.laenge, 26) and nahe(flansch.d_oben, 63), f"Flansch HSK-A63: {flansch}")
pruefe(nahe(hsk.laenge, 26 + 50.9) and hsk.abschnitte[1:] == er32.abschnitte[1:], "Körper")
pruefe("300470 32 (SK40), Flansch HSK-A63" in hsk.bezeichnung, f"{hsk.bezeichnung}")
pruefe(
    hsk.link.endswith("search?search=ER-Spannzangenfutter%20HSK-A%2063%20ER32"),
    f"an HSK die Suche: {hsk.link}",
)
bt50 = hl.aus_vorlage("schrumpf_12", aufnahme="BT50")
pruefe(nahe(bt50.abschnitte[0].d_oben, 100) and nahe(bt50.abschnitte[0].laenge, 38), "BT50")
pruefe(bt50.name == "Schrumpffutter Ø12 · BT50", f"Name: {bt50.name}")
pruefe(hl.aus_vorlage("er16", aufnahme="gibt es nicht").aufnahme == "SK40", "unbekannt: SK40")
vdi = hl.aus_vorlage("vdi_radial_er16", vdi=40, aufnahme="HSK-A63")
pruefe(vdi.aufnahme == "" and "HSK" not in vdi.name, f"VDI ohne Aufnahme: {vdi.name}")
pruefe(vdi.link == "" and vdi.bezeichnung == "Beispielmaße – nach Katalog prüfen", "VDI ohne Link")
pruefe(hl.Halter.aus_dict(hsk.als_dict()).aufnahme == "HSK-A63", "Aufnahme nicht gespeichert")
pruefe(hl.Halter.aus_dict(hsk.als_dict()).link == hsk.link, "Link nicht gespeichert")
pruefe(hl.Halter.aus_dict({"name": "alt"}).aufnahme == "", "alte Datei ohne Aufnahme")
pruefe(len(hl.AUFNAHMEN) >= 25 and "Capto C6" in hl.AUFNAHMEN and "KM63" in hl.AUFNAHMEN, "Liste")
# Das Bild (W-022 Punkt 3): der Flansch in der gemessenen Form seiner Familie, die Spannmutter mit
# der Fase vorn – nie dicker als der Abschnitt; radius_bei (Reichweite, Wegkippen) bleibt beim
# vollen. SK40: vorn der Kegel (Ø 44,5), Rille mit Grund Ø 56,4; HSK-A63: Rille bei 16,9 … 19,3.
kontur = er32.kontur()
pruefe(nahe(kontur[-1][0], 70) and max(r for _a, r in kontur) <= 31.775 + 1e-9, f"{kontur}")
pruefe(abs(kontur[0][1] - 22.24) < 0.01, f"SK40: vorn der Kegel: {kontur[0]}")
rille = min(r for a, r in kontur if 3.2 < a < 19.0)
pruefe(abs(rille - 28.2) < 0.01, f"Greiferrille SK40: {rille}")
grund = [a for a, r in kontur if nahe(r, rille)]
pruefe(len(grund) == 4 and abs(grund[-1] - grund[0] - 2.7) < 0.01, f"SK40-Rille: {grund}")
pruefe(abs(kontur[-1][1] - 19.37) < 0.01 and nahe(kontur[-2][1], 25), f"Mutter: {kontur[-2:]}")
hsk_grund = [a for a, r in hsk.kontur() if nahe(r, 0.875 * 31.5)]
pruefe(
    len(hsk_grund) == 4 and abs(hsk_grund[0] - 16.9) < 0.01 and abs(hsk_grund[-1] - 19.3) < 0.01,
    f"HSK-A63: Rille {hsk_grund}",
)
pruefe(hl.flanschfamilie("BT40") == "bt" and hl.flanschfamilie("Capto C6") == "hsk", "Familien")
arten = [a.art for a in er32.abschnitte]
pruefe(arten == [hl.FLANSCH, "", "", "", "", hl.MUTTER], f"Arten der Vorlage: {arten}")
wieder = hl.Halter.aus_dict(er32.als_dict())
pruefe([a.art for a in wieder.abschnitte] == arten, "Art gespeichert")
alt = hl.Halter.aus_dict(
    {"abschnitte": [{"laenge": 26, "d_oben": 63, "d_unten": 63}, {"laenge": 9, "d_oben": 40}]}
)
pruefe([a.art for a in alt.abschnitte] == [hl.FLANSCH, ""], "alte Datei: Flansch erkannt")
alt_sk40 = hl.Halter.aus_dict({"abschnitte": [{"laenge": 16, "d_oben": 63, "d_unten": 63}]})
pruefe(alt_sk40.abschnitte[0].art == hl.FLANSCH, "alte Vorlage SK40 (16 × 63): Flansch")
eigen = hl.Halter.aus_dict({"abschnitte": [{"laenge": 16, "d_oben": 63, "d_unten": 63, "art": ""}]})
pruefe(eigen.abschnitte[0].art == "", "ausdrücklich ohne Art bleibt ohne")
kurz = hl.Halter(abschnitte=[hl.Abschnitt(2, 63, 63, hl.FLANSCH)])
pruefe(hl.profil(kurz) == [(2, 63, 63)], f"zu kurz für die Rille: {hl.profil(kurz)}")
schrumpf = hl.aus_vorlage("schrumpf_12")
pruefe(nahe(schrumpf.laenge, 80), f"Schrumpf A = 80: {schrumpf.laenge}")
pruefe(nahe(schrumpf.radius_bei((32.4 + 80) / 2), (31.5 + 24) / 4), "Kegel: in der Mitte")
# VDI30 axial mit ER25 nach HOLEX 319512 25 (A = 57), an VDI40 gestreckt und die Suche verlinkt.
vdi30 = hl.aus_vorlage("vdi_er25", vdi=30)
pruefe(nahe(vdi30.laenge, 57) and vdi30.link.endswith("/p/319512-25"), f"VDI30: {vdi30.link}")
vdi40 = hl.aus_vorlage("vdi_er25", vdi=40)
pruefe(
    vdi40.link.endswith("search=ER-Spannzangenhalter%20VDI%2040%20ER25")
    and "auf VDI40 gestreckt" in vdi40.bezeichnung
    and nahe(vdi40.abschnitte[-1].d_oben, 41.8),
    f"VDI40: {vdi40.link} {vdi40.bezeichnung}",
)
for schluessel, a_soll in (("er16", 70), ("er25", 70), ("er40", 70), ("weldon_20", 63)):
    h = hl.aus_vorlage(schluessel)
    pruefe(abs(h.laenge - a_soll) < 1e-6 and h.link, f"{schluessel}: A {h.laenge}, {h.link}")
# Lang und schlank (2026-10-24): so weit reichen sie, vorn so dünn wie das Vorbild.
for schluessel, a_soll, vorn in (
    ("schrumpf_6_lang", 200, 21.0),
    ("schrumpf_12_lang", 200, 24.0),
    ("spannzange_schlank", 160, 12.9),
    ("er16_lang", 160, 28.0),
    ("er25_lang", 160, 42.0),
):
    h = hl.aus_vorlage(schluessel)
    pruefe(
        abs(h.laenge - a_soll) < 1e-6 and nahe(h.abschnitte[-1].d_unten, vorn) and h.link,
        f"{schluessel}: A {h.laenge}, vorn {h.abschnitte[-1].d_unten}, {h.link}",
    )
for schluessel in hl.VORLAGEN:
    h = hl.aus_vorlage(schluessel)
    pruefe(h.laenge > 0 and h.name and h.abschnitte, f"Vorlage {schluessel}")
leer = hl.Halter(abschnitte=[hl.Abschnitt(40, 30, 30)])
pruefe(hl.text(leer) == "Halter, 40 mm lang", f"ohne Namen: {hl.text(leer)}")

# --- Die Richtung --------------------------------------------------------------------------
import FreeCAD  # noqa: E402

V = FreeCAD.Vector


def spitze_zeigt(lage):
    return lage.Rotation.multVec(V(0, 0, -1))


pruefe(not er32.gewinkelt and hl.lage(er32).isIdentity(), "gerade: die Lage der Aufnahme")
pruefe(hl.lage(None).isIdentity(), "ohne Halter: die Lage der Aufnahme")
radial = hl.aus_vorlage("vdi30_radial")
pruefe(radial.name == "VDI30 angetrieben radial · ER16", f"Name: {radial.name}")
pruefe(
    radial.gewinkelt
    and (radial.winkel, radial.drehung, radial.versatz, radial.kopf_d) == (90, 0, 55, 55),
    f"radial: {radial}",
)
lage = hl.lage(radial)
pruefe((spitze_zeigt(lage) - V(1, 0, 0)).Length < 1e-12, f"radial zeigt {spitze_zeigt(lage)}")
pruefe((lage.Base - V(0, 0, -55)).Length < 1e-12, f"Bezugspunkt {lage.Base}")
spitze = lage.multVec(V(0, 0, -100))  # 100 mm ab Bezugspunkt
pruefe((spitze - V(100, 0, -55)).Length < 1e-9, f"Spitze {spitze}")
radial.drehung = 90
pruefe((spitze_zeigt(hl.lage(radial)) - V(0, 1, 0)).Length < 1e-12, "um 90° gedreht")
radial.drehung, radial.winkel = 0, 45
s = 2**-0.5
pruefe((spitze_zeigt(hl.lage(radial)) - V(s, 0, -s)).Length < 1e-12, "um 45° gekippt")
radial.winkel = 90
koerper = hl.form(radial)
box = koerper.BoundBox
pruefe(
    all(
        nahe(round(wert, 9), soll)
        for wert, soll in ((box.XMin, -27.5), (box.XMax, 55), (box.ZMin, -82.5), (box.ZMax, 0))
    ),
    f"Kopf und Abgang: {box}",
)
pruefe(nahe(radial.laenge, 55) and nahe(radial.spanntiefe, 20), "Abgang 55 mm")
axial = hl.aus_vorlage("vdi30_axial")
pruefe(not axial.gewinkelt and hl.lage(axial).isIdentity(), "axial: gerade")
# Die VDI-Vorlagen nennen keine Größe (Manuel, 2026-09-30: „also reicht VDI halter aus“): ohne
# Angabe die Maße für VDI 30 und ein Name ohne Zahl; mit der Größe der Maschine wachsen die Ø
# mit, die Längen nicht. Die alten Schlüssel „vdi30_…“ heißen VDI 30.
ohne = hl.aus_vorlage("vdi_radial")
pruefe(
    ohne.name == "VDI angetrieben radial · ER16" and nahe(ohne.kopf_d, 55), f"ohne Größe: {ohne}"
)
gross = hl.aus_vorlage("vdi_radial", vdi=40)
pruefe(gross.name == "VDI40 angetrieben radial · ER16", f"VDI 40: {gross.name}")
pruefe(
    nahe(gross.versatz, 55 * 40 / 30)
    and nahe(gross.kopf_d, 55 * 40 / 30)
    and nahe(gross.abschnitte[0].d_oben, 50 * 40 / 30)
    and nahe(gross.abschnitte[0].laenge, 35)
    and nahe(gross.spanntiefe, 20),
    f"VDI 40 Maße: {gross}",
)
pruefe(
    hl.vorlage_text("vdi_axial") == "VDI angetrieben axial · ER16"
    and hl.vorlage_text("vdi_axial", 50) == "VDI50 angetrieben axial · ER16"
    and hl.vorlage_text("er32", 50) == hl.vorlage_text("er32"),
    "Vorlagentext mit Größe",
)
# Angetrieben je Spannzange (Manuel, 2026-10-02: „warum bekomme ich bei dem VDI angetrieben radial
# und axial nur ER16?“): radial und axial je ER16, ER20, ER25, ER32. Die Spannmutter hat ihr Maß
# von der Spannzange und wächst nicht mit der VDI-Größe, der Körper schon.
pruefe(
    list(hl.GRUPPEN) == ["vdi_radial", "vdi_axial"]
    and all(list(g) == ["ER16", "ER20", "ER25", "ER32"] for g in hl.GRUPPEN.values())
    and all(v in hl.VORLAGEN for g in hl.GRUPPEN.values() for v in g.values()),
    f"Gruppen: {hl.GRUPPEN}",
)
pruefe(
    hl.gruppe_text("vdi_radial") == "VDI angetrieben radial"
    and hl.gruppe_text("vdi_axial", 40) == "VDI40 angetrieben axial",
    "Titel der Untermenüs",
)
radial_er25 = hl.aus_vorlage(hl.GRUPPEN["vdi_radial"]["ER25"], vdi=40)
pruefe(
    radial_er25.name == "VDI40 angetrieben radial · ER25"
    and radial_er25.gewinkelt
    and nahe(radial_er25.spanntiefe, 28)
    and nahe(radial_er25.abschnitte[0].d_oben, 50 * 40 / 30)
    and nahe(radial_er25.abschnitte[-1].d_oben, 42),
    f"radial ER25 an VDI 40: {radial_er25}",
)
axial_er32 = hl.aus_vorlage(hl.GRUPPEN["vdi_axial"]["ER32"])
pruefe(
    axial_er32.name == "VDI angetrieben axial · ER32"
    and not axial_er32.gewinkelt
    and nahe(axial_er32.abschnitte[-1].d_oben, 50),
    f"axial ER32: {axial_er32}",
)
pruefe(
    nahe(gross.abschnitte[-1].d_oben, 28),
    f"ER16 an VDI 40: Mutter {gross.abschnitte[-1].d_oben}",
)
kopf = hl.aus_vorlage("winkelkopf_90")
pruefe(kopf.gewinkelt and nahe(kopf.versatz, 110), f"Winkelkopf: {kopf}")
# Seitlich über die Werkzeugachse (fürs Futter bei Rundum): der halbe größte Ø, beim
# gewinkelten auch der Kopf – er endet um seinen Radius hinter der Werkzeugachse.
for halter, soll in ((radial, 27.5), (kopf, 40.0), (er32, 31.775), (axial, 27.5), (None, 0.0)):
    pruefe(nahe(hl.seitlich(halter), soll), f"seitlich {halter and halter.name}: {soll}")
# Die Länge ab Bezugspunkt geschätzt wie ab Spindelnase: Abgang + Gesamtlänge − Spanntiefe.
fraeser = wz.Werkzeug(durchmesser=6, gesamtlaenge=57)
pruefe(nahe(wz.laenge_mit_halter(fraeser, radial), 55 + 57 - 20), "Länge ab Bezugspunkt")
# Gespeichert und gelesen; eine alte Angabe ohne Richtung ist gerade, Unlesbares Standard.
wieder = hl.Halter.aus_dict(radial.als_dict())
pruefe(wieder.als_dict() == radial.als_dict(), "Richtung nach Laden gleich")
ohne = radial.als_dict()
for schluessel in ("richtung", "winkel", "drehung", "versatz", "kopf_d"):
    del ohne[schluessel]
o = hl.Halter.aus_dict(ohne)
pruefe(not o.gewinkelt and (o.winkel, o.drehung, o.versatz) == (90, 0, 0), f"alt: {o}")
u = hl.Halter.aus_dict({"richtung": "schraeg", "winkel": 400, "drehung": "x", "versatz": -3})
pruefe(not u.gewinkelt and (u.winkel, u.drehung, u.versatz) == (180, 0, 0), f"unlesbar: {u}")

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
# Wie weit es aus dem Halter schaut (P-2026-10-12-113): Halterlänge + Ausspannlänge, je Werkzeug –
# die Spanntiefe des Halters zählt dann nicht; gemessen gilt weiter vor allem.
t1.ausspannlaenge = 25
pruefe(
    nahe(b.laenge_ab_spindelnase(t1), 70 + 25), f"mit Ausspannlänge: {b.laenge_ab_spindelnase(t1)}"
)
t1.laenge_spindelnase = 120
pruefe(nahe(b.laenge_ab_spindelnase(t1), 120), "gemessen vor Ausspannlänge")
t1.laenge_spindelnase, t1.ausspannlaenge = 0, 0
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

# Normreihen (Manuel, 2026-10-25: „halterdatenbank deutlichst erweitern“): jede Art, Größe und
# Länge an SK40 und HSK-A63 – so lang wie A, vorn die Nase der Norm, der Flansch der Aufnahme.
anzahl = 0
namen = set()
for aufnahme in ("SK40", "HSK-A63", "BT30"):
    for art in hl.REIHEN:
        for groesse in hl.REIHE_GROESSEN[art]:
            for laenge in hl.REIHE_LAENGEN[art]:
                schluessel = hl.reihe(art, groesse, laenge)
                r = hl.aus_vorlage(schluessel, aufnahme=aufnahme)
                anzahl += 1
                namen.add(r.name)
                pruefe(nahe(r.laenge, laenge), f"{r.name}: {r.laenge:.2f} statt A {laenge:g}")
                pruefe(r.abschnitte[0].art == hl.FLANSCH, f"{r.name}: ohne Flansch")
                pruefe(
                    nahe(r.abschnitte[0].d_oben, hl.AUFNAHMEN[aufnahme][1]),
                    f"{r.name}: Flansch {r.abschnitte[0].d_oben}",
                )
                pruefe(r.spanntiefe > 0 and r.link and "DIN" in r.bezeichnung, f"{r.name}")
                pruefe(
                    all(a.laenge > 0 and a.d_oben > 0 and a.d_unten > 0 for a in r.abschnitte),
                    f"{r.name}: {r.abschnitte}",
                )
pruefe(len(namen) == anzahl, f"{anzahl} Normhalter, {len(namen)} Namen")
s12 = hl.aus_vorlage(hl.reihe(hl.SCHRUMPF, 12, 200))
pruefe(s12.name == "Schrumpffutter Ø12 · A 200 lang · SK40", s12.name)
pruefe(nahe(s12.abschnitte[-1].d_unten, 24.0) and nahe(s12.spanntiefe, 46.0), f"{s12}")
# 4,5° je Seite an der Nase, dahinter schlank (32 mm), am Flansch dicker
nase = s12.abschnitte[-1]
pruefe(abs((nase.d_oben - nase.d_unten) / 2 / nase.laenge - 0.0787) < 1e-4, f"Nase {nase}")
pruefe(nahe(s12.abschnitte[-2].d_oben, 32.0), f"schlank {s12.abschnitte[-2]}")
lang = hl.aus_vorlage(hl.reihe(hl.SCHRUMPF, 6, 300), aufnahme="HSK-A63")
pruefe(lang.name == "Schrumpffutter Ø6 · A 300 extra lang · HSK-A63", lang.name)
er25 = hl.aus_vorlage(hl.reihe(hl.ER, "ER25", 160))
pruefe(
    er25.name == "Spannzangenfutter ER25 · A 160 lang · SK40"
    and er25.abschnitte[-1].art == hl.MUTTER
    and nahe(er25.abschnitte[-1].d_unten, 42.0),
    f"{er25.name}: {er25.abschnitte[-1]}",
)
print(f"Normreihen: {anzahl} Halter an drei Aufnahmen")

sprache.setze_sprache(vorher)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
