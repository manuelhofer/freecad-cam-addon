# Prüft die Beispielmaschine zum Ausprobieren (W-001): Der Löser lässt alle
# Teile, wo sie gebaut sind; X1, Y1, Z1, S1 und beide Aufnahmen sind
# eingerichtet, ohne Warnung; Verfahren bewegt Tisch, Sattel und Kopf in
# Achsrichtung und hält die Grenzen ein.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD as App

from camaddon import beispielmaschine, sprache
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
pruefe(doc.Label == "Beispielmaschine" and ma.Label == "Beispiel-Fräsmaschine", "Namen")

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
sprache.setze_sprache(vorher)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
