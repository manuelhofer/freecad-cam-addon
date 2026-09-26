# Prüft die Umrisse der Werkzeugarten ohne Oberfläche (werkzeugform.py): Jede
# der 26 Arten ergibt mit ihren Beispielmaßen ein Bild; Zentrierbohrer und
# Bohrer sind spitz, der Kugelfräser rund, links ist das Spiegelbild von
# rechts, der Taster hat seine Kugel.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import einheiten, sprache
from camaddon import werkzeuge as wz
from camaddon import werkzeugform as wf

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def muster(art, **werte):
    """Ein Werkzeug der Art mit ihren Beispielmaßen, dazu `werte`."""
    w = wz.Werkzeug(art=art)
    wz.beispielwerte_setzen(w, neu=True)
    for feld, wert in werte.items():
        setattr(w, feld, wert)
    return w


def schneide(w):
    return next(t for t in wf.teile(w) if t.stoff == wf.SCHNEIDE)


vorher = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")
vorher_mass = einheiten.gewaehltes_masssystem()
einheiten.setze_masssystem(einheiten.METRISCH)

# Jede Art: ein Bild mit Schneide, endliche Punkte, echte Größe.
for art in wz.ARTEN:
    teile = wf.teile(muster(art))
    pruefe(teile, f"{art}: kein Bild")
    if not teile:
        continue
    punkte = [p for t in teile for p in t.punkte]
    pruefe(all(math.isfinite(x) and math.isfinite(y) for x, y in punkte), f"{art}: Punkt")
    x0, y0, x1, y1 = wf.grenzen(teile)
    pruefe(x1 - x0 > 0.5 and y1 - y0 > 0.5, f"{art}: zu klein ({x1 - x0} × {y1 - y0})")
    stoffe = {t.stoff for t in teile}
    pruefe(stoffe & {wf.SCHNEIDE, wf.KUGEL}, f"{art}: keine Schneide")

# Ohne Durchmesser nichts – das Bild nimmt dann die Beispiele.
pruefe(wf.teile(wz.Werkzeug()) == [], "Schaftfräser ohne D gezeichnet")


def unten(teil):
    """Die Punkte auf der Höhe der Spitze (kleinstes y)."""
    tiefst = min(y for _x, y in teil.punkte)
    return {round(x, 6) for x, y in teil.punkte if abs(y - tiefst) < 1e-9}


# Spitz: an der Spitze nur ein Punkt auf der Achse (Manuel: „der
# Zentrierbohrer ist eher spitz“); ein Schaftfräser ist unten flach.
for art in (wz.ZENTRIERBOHRER, wz.BOHRER, wz.NC_ANBOHRER):
    pruefe(unten(schneide(muster(art))) == {0.0}, f"{art} nicht spitz")
pruefe(len(unten(schneide(muster(wz.SCHAFTFRAESER)))) > 1, "Schaftfräser nicht flach")
# Der Zentrierbohrer wird über der Senkung so breit wie sein Körper-Ø.
zentrier = muster(wz.ZENTRIERBOHRER)
x0, _y0, x1, _y1 = wf.grenzen([schneide(zentrier)])
pruefe(abs((x1 - x0) - zentrier.schaft) < 1e-6, f"Zentrierbohrer: Körper {x1 - x0}")
# Kugelfräser: knapp über der Spitze schon fast so breit wie die Kugel an der Stelle.
kugel = schneide(muster(wz.KUGELFRAESER))
r = 6.0
hoehe = r * (1 - math.cos(math.radians(30)))
breite = max(x for x, y in kugel.punkte if abs(y - hoehe) < 0.01)
pruefe(abs(breite - r * math.sin(math.radians(30))) < 0.01, f"Kugel: {breite}")

# Links ist das Spiegelbild von rechts.
rechts = wf.grenzen(wf.teile(muster(wz.DREHWERKZEUG)))
links = wf.grenzen(wf.teile(muster(wz.DREHWERKZEUG, ausfuehrung=wz.LINKS)))
pruefe(
    all(
        abs(a - b) < 1e-9
        for a, b in zip((-rechts[2], rechts[1], -rechts[0]), links[:3], strict=True)
    ),
    f"Drehwerkzeug links {links} statt Spiegelbild von {rechts}",
)
# Der Einstellwinkel dreht die Platte: bei 90° steht die Hauptschneide senkrecht.
platte = schneide(muster(wz.DREHWERKZEUG, einstellwinkel=90.0)).punkte
pruefe(abs(platte[3][0]) < 1e-9, f"Hauptschneide bei 90°: {platte[3]}")
# Gewindebohrer: die Wendel zeigt, ob rechts- oder linksgängig.
pruefe(schneide(muster(wz.GEWINDEBOHRER_RECHTS)).wendel == wf.WENDEL_RECHTS, "Wendel rechts")
pruefe(schneide(muster(wz.GEWINDEBOHRER_LINKS)).wendel == wf.WENDEL_LINKS, "Wendel links")
# Taster: eine Kugel mit dem Durchmesser.
tastkugel = next(t for t in wf.teile(muster(wz.TASTER)) if t.stoff == wf.KUGEL)
x0, y0, x1, y1 = wf.grenzen([tastkugel])
pruefe(abs((x1 - x0) - 4) < 0.01 and abs(y0) < 1e-9, f"Tastkugel {x0, y0, x1, y1}")
# Gestrichelt, was nur Beispiel ist; eingetragen durchgezogen.
pruefe(schneide(muster(wz.SCHAFTFRAESER, beispiel=set())).geschaetzt is False, "eingetragen")
pruefe(
    all(t.geschaetzt for t in wf.teile(muster(wz.SCHAFTFRAESER), {"durchmesser"})),
    "Beispiel nicht gestrichelt",
)

einheiten.setze_masssystem(vorher_mass)
sprache.setze_sprache(vorher)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
