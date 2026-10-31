# Prüft die Empfehlung (empfehlung.py; Manuel, 2026-10-25: „wenn du diese aufnahme / halter nimmst
# und diesen fräser soweit ausspannst .. dann klapts“): Block 80 × 60 × 40, darin eine Tasche
# 30 tief, unten weiter als oben (10°). Ein Kugelfräser Ø 6 (60 lang, Schneide 12) steckt in einem
# ER32-Futter (Mutter Ø 50) – unten in der Tasche stößt die Mutter an den Rand, auch bis 40°
# gekippt, und Ausspannen geht nicht weit genug. Die Empfehlung: ein anderer Halter (eine
# Normreihe, die Ø 6 fasst), so weit heraus, dass an allen Stellen der Prüfung eine Achse frei
# bleibt – das kürzeste Paar ab Spindelnase.
# „So einrichten“ (einrichten): der Halter in der Werkzeugverwaltung, beim Fräser gewählt, die
# Ausspannlänge gesetzt – danach stößt die Bahn nirgends mehr an.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import empfehlung as em
from camaddon import halter as hl
from camaddon import hinterschnitt_bahn as hb
from camaddon import reichweite as rw
from camaddon import sprache
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
R = 3.0
D = 30 * math.tan(math.radians(10))


def rechteck(b, h, z, mx=40.0, my=30.0):
    x0, x1, y0, y1 = mx - b / 2, mx + b / 2, my - h / 2, my + h / 2
    return Part.makePolygon([V(x0, y0, z), V(x1, y0, z), V(x1, y1, z), V(x0, y1, z), V(x0, y0, z)])


unten = rechteck(44 + 2 * D, 30 + 2 * D, 10.0)
oben = rechteck(44, 30, 40.0)
teil = Part.makeBox(80, 60, 40).cut(Part.makeLoft([unten, oben], True, True)).removeSplitter()
waende = [
    f"Face{i + 1}"
    for i, f in enumerate(teil.Faces)
    if f.BoundBox.ZMin < 10.5
    and f.BoundBox.ZMax > 39.5
    and 1 < f.BoundBox.XMin < f.BoundBox.XMax < 79
]
pruefe(len(waende) == 4, f"{len(waende)} Wände")

bib = wz.Bibliothek()
kugel = wz.Werkzeug(
    nummer=4,
    name="Kugel 6",
    art=wz.KUGELFRAESER,
    durchmesser=6.0,
    schneiden=2,
    schneidenlaenge=12.0,
    gesamtlaenge=60.0,
    schneidstoff=wz.VHM,
)
bib.werkzeuge.append(kugel)
er32 = bib.neuer_halter("er32", None, "SK40")
kugel.halter = er32.kennung


def werte(werkzeug):
    laenge = rw.laenge_des_werkzeugs(werkzeug, bib)[0]
    halter = bib.halter_fuer_pruefung(werkzeug)
    koerper = hb.koerper_des_werkzeugs(rw.masse_des_werkzeugs(werkzeug), laenge, halter)
    return (
        hb.Werte(
            radius=R,
            sicher=60.0,
            grathoehe=0.02,
            vorschub=1500.0,
            schritt=1.0,
            koerper=tuple(koerper),
            schneide=12.0,
            oben=40.0,
        ),
        laenge - halter.laenge,
    )


w, heraus = werte(kugel)
try:
    bahn = hb.planen(teil, waende, w)
    pruefung, anstoesse = bahn.pruefung, bahn.anstoesse
except ValueError as grund:
    pruefung, anstoesse = getattr(grund, "daten", {}).get("pruefung"), -1
print(ascii(f"ER32, {heraus:.0f} mm heraus: {anstoesse} Anstoesse"))
pruefe(pruefung is not None and anstoesse != 0, f"mit ER32 stößt nichts an ({anstoesse})")

empfehlung = em.empfehlen(teil, pruefung, kugel, bib, "SK40")
pruefe(isinstance(empfehlung, em.Empfehlung), f"keine Empfehlung: {empfehlung}")
if isinstance(empfehlung, em.Empfehlung):
    print(
        ascii(
            f"Empfehlung: {empfehlung.werkzeug_text} in {empfehlung.halter.name}, "
            f"{empfehlung.heraus:.0f} mm heraus, {empfehlung.laenge:.0f} ab Spindelnase"
        )
    )
    pruefe(empfehlung.halter_neu and empfehlung.halter.aufnahme == "SK40", empfehlung.halter.name)
    pruefe(12.0 < empfehlung.heraus <= 54.0, f"heraus {empfehlung.heraus}")
    werkzeug = em.einrichten(empfehlung, bib)
    pruefe(werkzeug is kugel and kugel.halter != er32.kennung, "nicht eingerichtet")
    neu = bib.halter_von(kugel)
    pruefe(neu is not None and neu.name == empfehlung.halter.name, f"Halter {neu}")
    pruefe(abs(kugel.ausspannlaenge - empfehlung.heraus) < 1e-6, f"{kugel.ausspannlaenge}")
    w2, heraus2 = werte(kugel)
    bahn2 = hb.planen(teil, waende, w2)
    print(
        ascii(
            f"danach: {heraus2:.0f} mm heraus, {bahn2.anstoesse} Anstoesse, {bahn2.neigung:.0f} Grad"
        )
    )
    pruefe(bahn2.anstoesse == 0, f"danach {bahn2.anstoesse} Anstöße")
    # Noch einmal einrichten legt den Halter nicht doppelt an.
    vorher = len(bib.halter)
    em.einrichten(empfehlung, bib)
    pruefe(len(bib.halter) == vorher, "Halter doppelt")

# Ein Fräser, den es noch nicht gibt: Eine Kugel Ø 16 lässt unten an der Kante zum Boden Lücken –
# vorgeschlagen ein kleinerer Kugelfräser (Vorschlag) mit Halter; einrichten legt ihn an.
gross = wz.Werkzeug(
    nummer=6,
    name="Kugel 16",
    art=wz.KUGELFRAESER,
    durchmesser=16.0,
    schneidenlaenge=24.0,
    gesamtlaenge=120.0,
    schneidstoff=wz.VHM,
)
gross.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.4, ap=0.4, vc=200.0, fz=0.1)]
bib.werkzeuge.append(gross)
bahn16 = hb.planen(teil, waende, hb.Werte(radius=8.0, sicher=60.0, grathoehe=0.02, schritt=1.0))
print(ascii(f"Kugel 16: Ecken bis R {bahn16.ecken_radius}, {bahn16.weggelassen} weg"))
pruefe(bahn16.ecken is not None and 0 < bahn16.ecken_radius < 8.0, f"Ecken {bahn16.ecken_radius}")
neu = em.neue_kugel(teil, bahn16.ecken, gross, bib, "SK40")
pruefe(isinstance(neu, em.Empfehlung) and neu.werkzeug_neu, f"neue Kugel: {neu}")
if isinstance(neu, em.Empfehlung):
    d = float(neu.werkzeug_neu["durchmesser"])
    print(ascii(f"neu: {neu.werkzeug_text} in {neu.halter.name}, {neu.heraus:.0f} mm heraus"))
    pruefe(d <= 2.0 * bahn16.ecken_radius + 1e-6 and "(Vorschlag)" in neu.werkzeug_text, f"Ø {d}")
    pruefe(all(w.durchmesser != d for w in bib.werkzeuge), "die Kopie trug ihn schon ein")
    angelegt = em.einrichten(neu, bib)
    pruefe(
        angelegt is not None
        and angelegt in bib.werkzeuge
        and angelegt.nummer not in (4, 6)
        and bib.halter_von(angelegt) is not None
        and abs(angelegt.ausspannlaenge - neu.heraus) < 1e-6,
        f"angelegt: {angelegt}",
    )
    einsatz = angelegt.schnittwerte[wz.ALLE][0]
    pruefe(abs(einsatz.fz - 0.1 * d / 16.0) < 1e-9, f"fz {einsatz.fz}")

# Die Flanke: ein Schaftfräser Ø 10 (Schneide 20) im ER32 – die Mutter führt in die Wand. 45 mm
# lang geht es mit keinem Halter (die Wand ist 30 hoch, jeder bräuchte rund 39 mm heraus, höchstens
# 35 gehen); 60 mm lang empfohlen ein anderer Halter, mit dem es an allen Stellen der Bahn geht
# (flanke_bahn.halter_an_stellen).
from camaddon import flanke as flop  # noqa: E402
from camaddon import flanke_bahn as fb  # noqa: E402

schaft = wz.Werkzeug(
    nummer=7,
    name="VHM 10",
    art=wz.SCHAFTFRAESER,
    durchmesser=10.0,
    schneiden=4,
    schneidenlaenge=20.0,
    gesamtlaenge=45.0,
    schneidstoff=wz.VHM,
)
bib.werkzeuge.append(schaft)
schaft.halter = er32.kennung
fl_bahn = fb.planen(
    teil,
    waende,
    fb.Flankenwerte(radius=5.0, schneide=20.0, oben=40.0, sicher=60.0, vorschub=1000.0),
)
fl_stellen = flop._stellen_fuer_empfehlung(fl_bahn, 5.0)
kurz = em.empfehlen_flanke(teil, fl_stellen, schaft, bib, "SK40")
pruefe(kurz == em.KEINE, f"Ø10 × 45: doch {getattr(getattr(kurz, 'halter', None), 'name', '')}")
# Das ER11-Futter aus der Werkzeugverwaltung spannt höchstens Ø 7 – nicht für den Schaft Ø 10.
# (Seit die Empfehlung auch den Katalog fragt, legt die Kugel oben ein 3°-Schrumpffutter an, kein
# ER11 – dann hier eins.)
er11 = next((h for h in bib.halter if "ER11" in h.name), None) or bib.halter_dazu(
    hl.aus_vorlage(hl.reihe(hl.ER, "ER11", hl.REIHE_LAENGEN[hl.ER][0]), aufnahme="SK40")
)
pruefe(not em._fasst(er11, 10.0) and em._fasst(er11, 6.0), "ER11 fasst Ø10")
# Ein Schrumpffutter aus dem Katalog spannt genau seinen Ø (Halter.spann_d) – „d6 A80“ sagt es
# dem Namen nach nicht; bis 0.328 bot die Flanke es dem Schaft Ø 10 an.
d6 = next((h for h in bib.halter if h.spann_d), None)
pruefe(d6 is not None and em._fasst(d6, 6.0) and not em._fasst(d6, 10.0), f"Katalog: {d6}")
schaft.gesamtlaenge = 60.0
fl = em.empfehlen_flanke(teil, fl_stellen, schaft, bib, "SK40")
name = fl.halter.name if isinstance(fl, em.Empfehlung) else fl
print(ascii(f"Flanke: {name}, {getattr(fl, 'heraus', 0):.0f} mm"))
pruefe(isinstance(fl, em.Empfehlung) and fl.halter_neu and fl.heraus <= 50.0, f"Flanke: {fl}")
if isinstance(fl, em.Empfehlung):
    em.einrichten(fl, bib)
    kapseln = flop.koerper_ueber_der_schneide(schaft, bib)
    rest = fb.halter_pruefen(teil, fl_bahn, kapseln, 5.0)
    pruefe(rest is None, f"Flanke eingerichtet: stößt noch an {rest}")

# Ein Halter, mit dem nichts geht, wird nicht empfohlen: ohne Normreihen und eigene Halter KEINE.
leer = wz.Bibliothek()
fest = wz.Werkzeug(nummer=5, art=wz.KUGELFRAESER, durchmesser=7.0, gesamtlaenge=20.0)
leer.werkzeuge.append(fest)
pruefe(em.empfehlen(teil, pruefung, fest, leer, "SK40") == em.KEINE, "Ø7 kurz: doch etwas")
print(ascii(f"Normhalter fuer 6: {len(em._normhalter(6.0, 'SK40'))}"))
pruefe(hl.aus_vorlage(hl.reihe(hl.SCHRUMPF, 6, 80)).name.startswith("Schrumpffutter Ø6"), "Name")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
