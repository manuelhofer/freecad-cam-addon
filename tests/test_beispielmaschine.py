# Prüft die Beispielmaschinen zum Ausprobieren (W-001): Der Löser lässt alle
# Teile, wo sie gebaut sind; X1, Y1, Z1, S1 und beide Aufnahmen sind
# eingerichtet, ohne Warnung; Verfahren bewegt Tisch, Sattel und Kopf in
# Achsrichtung und hält die Grenzen ein. Dann alle fünf Bauarten zur Auswahl
# (Drehmaschine, 3-Achs, drei 5-Achs): jede mit ihren Achsen, ohne Warnung,
# jede Achse fährt, und die Auswahl merkt sich die zuletzt geladene. Zuletzt
# die Drehmaschine mit eigenen Maßen („Neue Maschine …“): Name, Wege,
# Bettneigung, Plätze, Drehzahl und die schräge Achse – und ungültige Maße.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD as App

from camaddon import PARAMETER_PFAD, beispielmaschine, schraege_achse, sprache
from camaddon import kette as kette_modul
from camaddon import maschine as m
from camaddon import schruppwerte as sw
from camaddon import verfahren as vf
from camaddon.kette import HINWEIS, LINEAR

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def weg(name):
    """Wie weit ein Teil seit dem Bauen verschoben ist."""
    return doc.getObject(name).Placement.Base - gebaut[name].Base


vorher = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")

asm, ma = beispielmaschine.fraesmaschine()
doc = asm.Document
TEILE = ("Bett", "Staender", "Sattel", "Tisch", "Fraeskopf", "Spindel")
gebaut = {n: App.Placement(doc.getObject(n).Placement) for n in TEILE}
for teil in TEILE:
    doc.getObject(teil).touch()
doc.recompute()
for teil in TEILE:
    pruefe(doc.getObject(teil).Placement.isSame(gebaut[teil], 1e-6), f"{teil} verschoben")
pruefe(doc.Label == "Beispiel 3-Achs-Fräse" and ma.Label == "3-Achs-Fräse", "Namen")

# Eingerichtet und ohne Warnung.
namen = sorted(b.NcName for b in m.betriebsarten(ma))
pruefe(namen == ["S1", "X1", "Y1", "Z1"], f"Betriebsarten: {namen}")
warnungen = [x.text for x in m.pruefe(ma) if x.schwere != HINWEIS]
pruefe(not warnungen, f"Warnungen: {warnungen}")
aufnahmen = {a.Art: a for a in m.aufnahmen(ma)}
werkstueck = m.globale_platzierung(aufnahmen[m.AUFNAHME_WERKSTUECK].Lcs).Base
werkzeug = m.globale_platzierung(aufnahmen[m.AUFNAHME_WERKZEUG].Lcs).Base
pruefe(werkstueck.isEqual(App.Vector(400, 350, 250), 1e-6), f"Werkstückaufnahme {werkstueck}")
pruefe(werkzeug.isEqual(App.Vector(400, 350, 380), 1e-6), f"Werkzeugaufnahme {werkzeug}")
pruefe(sw.grenzen_der_maschine(ma) == (12000, 10000), f"Grenzen {sw.grenzen_der_maschine(ma)}")

# Verfahren: alle Achsen stehen auf 0; X bewegt den Tisch, Y Sattel und
# Tisch, Z Kopf und Spindel – jeweils in Achsrichtung.
v = vf.Verfahren(asm)
achse = {a.gelenk.Name: a for a in v.achsen}
pruefe(sorted(achse) == ["Spindelachse", "X", "Y", "Z"], f"Achsen: {sorted(achse)}")
for name in ("X", "Y", "Z"):
    pruefe(abs(v.stellung(achse[name])) < 1e-9, f"{name} steht nicht auf 0")
v.setze(achse["X"], 100)
v.setze(achse["Y"], 50)
v.setze(achse["Z"], -50)
for teil, soll in (
    ("Tisch", App.Vector(100, 50, 0)),
    ("Sattel", App.Vector(0, 50, 0)),
    ("Fraeskopf", App.Vector(0, 0, -50)),
    ("Spindel", App.Vector(0, 0, -50)),
    ("Staender", App.Vector()),
):
    pruefe(weg(teil).isEqual(soll, 1e-6), f"{teil} um {weg(teil)} statt {soll}")
pruefe(abs(vf.gelenkstellung(achse["Z"].gelenk, LINEAR) + 50) < 1e-6, "Z steht nicht auf −50")
# Grenzen: X ±250, Y −150 … 120, Z −100 … 250.
for name, soll, grenze in (("X", 400, 250), ("Y", -400, -150), ("Z", 400, 250)):
    pruefe(v.setze(achse[name], soll) == grenze, f"{name} fährt über die Grenze {grenze}")
v.grundstellung()
pruefe(all(weg(t).Length < 1e-6 for t in TEILE), "Grundstellung")

App.closeDocument(doc.Name)

# Alle Bauarten zur Auswahl.
ACHSEN = {
    beispielmaschine.DREHMASCHINE: ["C1", "S1", "S3", "T", "X1", "Y1", "Z1"],
    beispielmaschine.FRAESE_3: ["S1", "X1", "Y1", "Z1"],
    beispielmaschine.TISCH_TISCH: ["A1", "C1", "S1", "X1", "Y1", "Z1"],
    beispielmaschine.KOPF_KOPF: ["A1", "B1", "S1", "X1", "Y1", "Z1"],
    beispielmaschine.KOPF_TISCH: ["B1", "C1", "S1", "X1", "Y1", "Z1"],
}
pruefe(list(ACHSEN) == list(beispielmaschine.ARTEN), f"Bauarten {beispielmaschine.ARTEN}")
# lade() merkt sich die Bauart in den Einstellungen – danach wie vorher.
einstellungen = App.ParamGet(PARAMETER_PFAD)
zuletzt_vorher = einstellungen.GetString(beispielmaschine._ZULETZT, "")
KOERPER = ("Part::Box", "Part::Cylinder", "App::Part")
for art in beispielmaschine.ARTEN:
    asm, ma = beispielmaschine.lade(art)
    doc = asm.Document
    pruefe(beispielmaschine.zuletzt_gewaehlt() == art, f"{art}: nicht gemerkt")
    pruefe(ma.Label == beispielmaschine.titel(art), f"{art}: Maschine heißt {ma.Label}")
    namen = sorted(b.NcName for b in m.betriebsarten(ma))
    pruefe(namen == ACHSEN[art], f"{art}: Betriebsarten {namen}")
    warnungen = [x.text for x in m.pruefe(ma) if x.schwere != HINWEIS]
    pruefe(not warnungen, f"{art}: Warnungen {warnungen}")
    arten = sorted(a.Art for a in m.aufnahmen(ma))
    pruefe(m.AUFNAHME_WERKSTUECK in arten and m.AUFNAHME_WERKZEUG in arten, f"{art}: {arten}")
    # Der Löser lässt jedes Teil, wo es gebaut ist.
    teile = [o for o in doc.Objects if o.TypeId in KOERPER]
    gebaut = {o.Name: App.Placement(o.Placement) for o in teile}
    for o in teile:
        o.touch()
    doc.recompute()
    verschoben = [o.Name for o in teile if not o.Placement.isSame(gebaut[o.Name], 1e-6)]
    pruefe(not verschoben, f"{art}: verschoben {verschoben}")
    # Jede Achse fährt (30 mm oder 30°, höchstens bis zur Grenze), Grundstellung zurück.
    v = vf.Verfahren(asm)
    for achse in v.achsen:
        erreicht = v.setze(achse, 30)
        ist = vf.gelenkstellung(achse.gelenk, achse.art)
        pruefe(
            abs(erreicht) > 1 and abs(v.stellung(achse) - erreicht) < 1e-6,
            f"{art}: {achse.gelenk.Name} auf {erreicht}, steht auf {v.stellung(achse)} ({ist})",
        )
    v.grundstellung()
    zurueck = [o.Name for o in teile if not o.Placement.isSame(gebaut[o.Name], 1e-6)]
    pruefe(not zurueck, f"{art}: nach der Grundstellung nicht zurück: {zurueck}")
    if art == beispielmaschine.DREHMASCHINE:
        # Zwölf Revolverplätze; P1 und P2 tragen die angetriebenen Werkzeuge an S3.
        plaetze = [a for a in m.aufnahmen(ma) if a.Art == m.AUFNAHME_WERKZEUG]
        angetrieben = sorted(a.Label for a in plaetze if getattr(a.Spindel, "NcName", "") == "S3")
        pruefe(len(plaetze) == 12, f"Revolverplätze: {len(plaetze)}")
        pruefe(len(angetrieben) == 2, f"angetrieben: {angetrieben}")
    App.closeDocument(doc.Name)

# --- Drehmaschine mit eigenen Maßen („Neue Maschine …“) ----------------------------------
masse = beispielmaschine.DrehmaschinenMasse(
    name="Meine Drehmaschine / 2",
    bettneigung=30,
    y_winkel=30,
    weg_x=(-80, 120),
    weg_y=(-40, 50),
    weg_z=(-50, 400),
    plaetze=8,
    drehzahl=4000,
)
pruefe(not masse.fehler(), f"gültige Maße: {masse.fehler()}")
asm, ma = beispielmaschine.lade(beispielmaschine.DREHMASCHINE, masse)
doc = asm.Document
kette = kette_modul.lies_kette(asm)
achsen = {a.gelenk.Label: a for a in kette.achsen}
pruefe(ma.Label == "Meine Drehmaschine / 2", f"Maschine: {ma.Label}")
pruefe(doc.Label == "Meine Drehmaschine - 2", f"Dokument: {doc.Label}")
for gelenk, weg_soll in (("X", (-80, 120)), ("Y", (-40, 50)), ("Z", (-50, 400))):
    ist = (achsen[gelenk].minimum, achsen[gelenk].maximum)
    pruefe(ist == weg_soll, f"Weg {gelenk}: {ist}")
# Das Bett ist 30° geneigt: X fährt 30° gegen die Waagrechte.
steigung = abs(math.degrees(math.asin(achsen["X"].richtung.z)))
pruefe(abs(steigung - 30) < 1e-6, f"X steigt um {steigung}°")
plaetze = [a for a in m.aufnahmen(ma) if a.Art == m.AUFNAHME_WERKZEUG]
pruefe(len(plaetze) == 8, f"Revolverplätze: {len(plaetze)}")
s1 = next(b for b in m.betriebsarten(ma) if b.NcName == "S1")
pruefe(s1.Drehzahl == 4000, f"S1: {s1.Drehzahl}")
trafos = m.transformationen(ma)
pruefe(len(trafos) == 1, f"schräge Achse: {len(trafos)}")
if trafos:
    alpha = schraege_achse.winkel(kette, ma, trafos[0])
    pruefe(alpha is not None and abs(alpha - 30) < 1e-6, f"Y-Winkel: {alpha}")
warnungen = [x.text for x in m.pruefe(ma, kette) if x.schwere != HINWEIS]
pruefe(not warnungen, f"eigene Maße, Warnungen: {warnungen}")
hinweise = [x.schluessel for x in m.pruefe(ma, kette) if x.schluessel.startswith("maschine.trafo")]
pruefe(not hinweise, f"eigene Maße, Hinweise zur schrägen Achse: {hinweise}")
App.closeDocument(doc.Name)

# Ohne Y-Winkel keine schräge Achse; die Vorgaben sind die des Beispiels.
asm, ma = beispielmaschine.lade(
    beispielmaschine.DREHMASCHINE, beispielmaschine.DrehmaschinenMasse()
)
pruefe(not m.transformationen(ma), "Vorgabe mit schräger Achse")
pruefe(asm.Document.Label == "Beispiel Drehmaschine", f"Vorgabe-Name: {asm.Document.Label}")
App.closeDocument(asm.Document.Name)

# Ungültige Maße: je Feld ein Satz.
falsch = beispielmaschine.DrehmaschinenMasse(
    bettneigung=70,
    y_winkel=-61,
    weg_x=(10, 100),
    weg_y=(-5, -5),
    weg_z=(-2000, 10),
    plaetze=3,
    drehzahl=0,
)
felder = [feld for feld, _schluessel in falsch.fehler()]
pruefe(
    felder == ["bettneigung", "y_winkel", "weg_x", "weg_y", "weg_z", "plaetze", "drehzahl"],
    f"ungültige Maße: {felder}",
)

if zuletzt_vorher:
    einstellungen.SetString(beispielmaschine._ZULETZT, zuletzt_vorher)
else:
    einstellungen.RemString(beispielmaschine._ZULETZT)
sprache.setze_sprache(vorher)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
