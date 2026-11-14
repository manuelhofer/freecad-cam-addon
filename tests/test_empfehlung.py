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
# Die Teile 1–8 prüfen den Weg mit Fräsern der Werkzeugverwaltung; die Fräser aus dem Katalog der
# Hersteller (empfehlung._katalog_fraeser, seit 0.346.0) prüft Teil 9 mit einem festen Katalog.
_katalog_fraeser = em._katalog_fraeser
em._katalog_fraeser = lambda *_a: []
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
# lang geht es mit keinem Normhalter (die Wand ist 30 hoch, jeder bräuchte rund 39 mm heraus,
# höchstens 35 gehen); 60 mm lang empfohlen ein anderer Halter, mit dem es an allen Stellen der Bahn geht
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
# Ohne den Katalog der Hersteller (nur Normreihen und eigene Halter): Mit ihm gibt es seit 0.344.2
# ein schlankeres Futter (HAIMER Mini Shrink extra slim, vorn Ø 13), mit dem es geht – geprüft wird
# hier der Weg „nichts geht“, nicht der Inhalt des Katalogs.
mit_katalog = em._katalog_halter
em._katalog_halter = lambda *_a: []
try:
    kurz = em.empfehlen_flanke(teil, fl_stellen, schaft, bib, "SK40")
finally:
    em._katalog_halter = mit_katalog
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

# 9. Fräser aus dem Katalog (Manuel, 2026-11-06: der Sinn der Kataloge sind bessere Vorschläge):
#    Ist die Kugel Ø6 zu kurz (35 mm: höchstens 29 heraus, gebraucht sind rund 38), nimmt die
#    Empfehlung eine längere Ø6 aus dem Katalog, mit ihrem Hals; „So einrichten“ legt sie in der
#    Werkzeugverwaltung an. Eine Ø6 anderer Art bleibt außen vor.
from camaddon import werkzeugwahl as ww  # noqa: E402

kurze_bib = wz.Bibliothek()
kurz6 = wz.Werkzeug(
    nummer=6, name="Kugel 6 kurz", art=wz.KUGELFRAESER, durchmesser=6.0, schneiden=2,
    schneidenlaenge=12.0, gesamtlaenge=35.0, schneidstoff=wz.VHM,
)  # fmt: skip
kurze_bib.werkzeuge.append(kurz6)
kurz6.halter = kurze_bib.neuer_halter("er32", None, "SK40").kennung
lang6 = ww._Katalogwerkzeug(
    (wz.KUGELFRAESER, 6.0, 6.0, 80.0, 0.0, 0.0, {}, "Kugel lang", "Probe", "K6-80", "", 6.0, 5.6,
     45.0, 0.0, 0.0)
)  # fmt: skip
schaft6 = ww._Katalogwerkzeug(
    (wz.SCHAFTFRAESER, 6.0, 13.0, 80.0, 0.0, 0.0, {}, "Schaft", "Probe", "S6", "", 6.0, 0.0, 0.0, 0.0,
     0.0)
)  # fmt: skip
mit_katalog_w, mit_norm, mit_katalog_h = ww.katalog_werkzeuge, em._normhalter, em._katalog_halter
ww.katalog_werkzeuge = lambda: [lang6, schaft6]
# Nur der ER32 der Werkzeugverwaltung: Mit einem schlanken Schrumpffutter aus dem Katalog ginge es
# auch mit der kurzen Kugel (MAPAL 3°) – hier soll der längere Fräser helfen.
em._normhalter = em._katalog_halter = lambda *_a: []
em._katalog_fraeser = _katalog_fraeser
try:
    kandidaten = [w.artikel for w in em._katalog_fraeser(kurz6)]
    pruefe(kandidaten == ["K6-80"], f"Katalog: {kandidaten}")
    aus_katalog = em.empfehlen(teil, pruefung, kurz6, kurze_bib, "SK40")
finally:
    ww.katalog_werkzeuge, em._normhalter, em._katalog_halter = (
        mit_katalog_w,
        mit_norm,
        mit_katalog_h,
    )
print(ascii(f"aus dem Katalog: {getattr(aus_katalog, 'werkzeug_text', aus_katalog)}, "
            f"{getattr(aus_katalog, 'heraus', 0):.0f} mm heraus"))  # fmt: skip
pruefe(
    isinstance(aus_katalog, em.Empfehlung)
    and aus_katalog.werkzeug.startswith(em.KATALOG)
    and aus_katalog.werkzeug_neu
    and not aus_katalog.im_magazin,
    f"aus dem Katalog: {aus_katalog}",
)
if isinstance(aus_katalog, em.Empfehlung):
    neu_w = em.einrichten(aus_katalog, kurze_bib)
    pruefe(
        neu_w is not None
        and neu_w.artikel == "K6-80"
        and neu_w.nummer > 0
        and abs(neu_w.hals_laenge - 45.0) < 1e-9
        and neu_w in kurze_bib.werkzeuge,
        f"eingerichtet: {neu_w}",
    )

# 10. Erst mit dem Vorhandenen (Manuel, 2026-11-06: „erst die Werkzeugliste, die vorhanden ist …
#     wenn nicht, muss man halt sagen, okay, hey, jetzt du musst was bestellen“): Mit einer eigenen
#     langen Kugel Ø6 im eigenen ER32 ist die Empfehlung diese (nicht bestellen); was mit Neuem
#     ginge, steht nur daneben (`besser`, mindestens BESSER_UM kürzer). Ohne sie: bestellen.
eigene_bib = wz.Bibliothek()
eigen6 = wz.Werkzeug(
    nummer=7, name="Kugel 6 kurz", art=wz.KUGELFRAESER, durchmesser=6.0, schneiden=2,
    schneidenlaenge=12.0, gesamtlaenge=35.0, schneidstoff=wz.VHM,
)  # fmt: skip
lang_eigen = wz.Werkzeug(
    nummer=8, name="Kugel 6 lang", art=wz.KUGELFRAESER, durchmesser=6.0, schneiden=2,
    schneidenlaenge=12.0, gesamtlaenge=100.0, schneidstoff=wz.VHM,
)  # fmt: skip
eigene_bib.werkzeuge += [eigen6, lang_eigen]
er32_eigen = eigene_bib.neuer_halter("er32", None, "SK40")
eigen6.halter = lang_eigen.halter = er32_eigen.kennung
zweistufig = em.empfehlen(teil, pruefung, eigen6, eigene_bib, "SK40")
besser = getattr(zweistufig, "besser", None)
print(
    ascii(
        f"vorhanden: {getattr(zweistufig, 'werkzeug_text', zweistufig)} "
        f"{getattr(zweistufig, 'laenge', 0):.0f} mm, bestellen {getattr(zweistufig, 'bestellen', None)}"
        f" | besser: {getattr(besser, 'werkzeug_text', None)} {getattr(besser, 'laenge', 0):.0f} mm"
    )
)
pruefe(
    isinstance(zweistufig, em.Empfehlung)
    and zweistufig.werkzeug == lang_eigen.kennung
    and not zweistufig.bestellen
    and not zweistufig.halter_neu,
    f"erst das Vorhandene: {zweistufig}",
)
pruefe(
    besser is None
    or (besser.bestellen and besser.laenge < zweistufig.laenge - em.BESSER_UM + 1e-6),
    f"besser: {besser}",
)
frische_bib = wz.Bibliothek()  # nur die kurze Kugel im ER32 – in `bib` steht inzwischen ein ER11
nur6 = wz.Werkzeug.aus_dict(eigen6.als_dict())
frische_bib.werkzeuge.append(nur6)
nur6.halter = frische_bib.neuer_halter("er32", None, "SK40").kennung
nur_neu = em.empfehlen(teil, pruefung, nur6, frische_bib, "SK40")
pruefe(isinstance(nur_neu, em.Empfehlung) and nur_neu.bestellen, f"ohne Vorhandenes: {nur_neu}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
