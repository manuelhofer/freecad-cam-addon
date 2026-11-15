# Prüft „Restschlichten“ (W-006 4.2 Punkt 8): das 3D-Schlichten mit einem kleineren Fräser nur
# dort, wo der größere davor nicht hinkam. (a) Platte 60 × 60 × 10 mit einer Kuppel (Kugel R 25,
# Mitte (30, 30, −5), Fuß r 20): erst 3D-Schlichten mit der Kugel Ø 6, dann Restschlichten mit
# der Kugel Ø 2. In der Kehle am Fuß (126,9°) lässt eine Kugel mit Radius r senkrecht über der
# Ecke r · (1 − √0,75) = 0,134 r stehen: nach Ø 6 0,40, nach Ø 2 0,13. Die Bahn bleibt am Fuß
# (r 16 … 21,5), im Quader nach beiden Bahnen dort deutlich weniger als nach Ø 6 allein, nirgends
# ins Teil, oben auf der Kuppel nichts gefahren; schneller als die Kuppel ganz mit Ø 2. (b) Eine
# Kuppel auf einem Zylinder (keine Kehle): Ø 6 erreicht alles – ein Satz. Eine Kuppel, die am
# Teilboden endet: Dort lässt Ø 6 Rest (nie unter den Boden, B-033), Ø 2 fährt nur am Fuß und lässt
# weniger. (c) Die Operation im Job: „Restschlichten T3“ mit Ø und Eckenradius davor, Art
# „schlichten3d“.
import math
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import job_schnittwerte as js
from camaddon import pruefstand as ps
from camaddon import restmaterial as rm
from camaddon import schlichten3d as s3op
from camaddon import schlichten3d_bahn as s3
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_flaechen as vf
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
gross_form, klein_form = ff.kugel(3.0), ff.kugel(1.0)


def werte(form, **weiter):
    grund = {"form": form, "oben": 20.0, "sicher": 25.0, "vorschub": 796.0, "eintauchen": 240.0}
    grund.update(weiter)
    return s3.Schlichtwerte(**grund)


def kugelflaechen(teil):
    return [f"Face{i + 1}" for i, f in enumerate(teil.Faces) if isinstance(f.Surface, Part.Sphere)]


# --- (a) Die Kuppel auf der Platte -----------------------------------------------------------------
platte = Part.makeBox(60, 60, 10)
kappe = Part.makeSphere(25, V(30, 30, -5)).common(Part.makeBox(60, 60, 15, V(0, 0, 10)))
teil = platte.fuse(kappe).removeSplitter()
kuppel = kugelflaechen(teil)
gross = s3.planen(teil, kuppel, werte(gross_form))
rest = s3.planen(teil, kuppel, werte(klein_form, davor=gross_form))
ganz = s3.planen(teil, kuppel, werte(klein_form))
pk = np.array([(p.x, p.y, p.z) for p in rest.punkte if not p.eilgang])
r = np.hypot(pk[:, 0] - 30, pk[:, 1] - 30)
print(ascii(f"Rest: {rest.zeit:.2f} min ({rest.hoehenlinien} Höhenlinien, Spirale {rest.spirale}, "
            f"Fläche entlang {rest.flaeche}, {rest.zeilen} Zeilen), r {r.min():.2f} … "
            f"{r.max():.2f}; ganz mit Ø 2 {ganz.zeit:.2f} min, Ø 6 {gross.zeit:.2f} min"))  # fmt: skip
pruefe(r.min() > 16.0 and r.max() < 21.5, f"Rest: r {r.min():.2f} … {r.max():.2f}")
pruefe(rest.zeit < 0.6 * ganz.zeit, f"Rest {rest.zeit:.2f} min, ganz {ganz.zeit:.2f}")

netz = vf.vernetze(teil, 0.005).netz
q = rm.Quader(0, 60, 0, 60, 0, 20.5, schritt=0.1)
soll = hf.hoehen(netz, q.x, q.y)
q.h[:] = np.minimum(soll + 1.0, 20.5)


def fahre(bahn, form):
    for von, nach in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        stuecke = ps._stuecke(von, nach)
        q.fahre_stuecke([s[0] for s in stuecke], [s[1] for s in stuecke], form)


xs, ys = np.meshgrid(q.x, q.y, indexing="ij")
rr = np.hypot(xs - 30, ys - 30)
ecke = (rr > 20.0) & (rr < 20.05)  # über der Kehle, auf der Platte
fahre(gross, gross_form)
nach_gross = q.h.copy()
fahre(rest, klein_form)
vorher = float(np.median((nach_gross - soll)[ecke]))
nachher = float(np.median((q.h - soll)[ecke]))
print(ascii(f"In der Kehle: nach Ø 6 {vorher:.3f}, nach dem Rest mit Ø 2 {nachher:.3f} mm "
            f"(gerechnet 0,40 und 0,13); ins Teil {np.min(q.h - soll):.3f}"))  # fmt: skip
pruefe(vorher > 0.35, f"nach Ø 6 nur {vorher:.3f} in der Kehle")
pruefe(nachher < 0.25, f"nach dem Rest {nachher:.3f} in der Kehle")
pruefe(np.min(q.h - soll) > -0.02, f"ins Teil: {np.min(q.h - soll):.3f}")
oben = rr < 12.0
pruefe(np.all(np.abs(q.h - nach_gross)[oben] < 1e-9), "oben auf der Kuppel gefahren")

# --- (b) Ohne Kehle kein Rest ----------------------------------------------------------------------
# Eine Kuppel auf einem Zylinder gleichen Fußes (der Teilboden 5 mm darunter, eine Außenkante statt
# einer Kehle): Ø 6 erreicht alles.
auf_zylinder = (
    Part.makeSphere(25, V(30, 30, -15))
    .common(Part.makeBox(60, 60, 10, V(0, 0, 0)))
    .fuse(Part.makeCylinder(20, 5, V(30, 30, -5)))
    .removeSplitter()
)
for raster in (s3.RASTER, s3.VORSCHAU_RASTER):
    try:
        s3.planen(auf_zylinder, kugelflaechen(auf_zylinder), werte(
            klein_form, davor=gross_form, oben=10.0, sicher=15.0, raster=raster))  # fmt: skip
    except ValueError as grund:
        pruefe("Kein Rest" in str(grund), f"ohne Kehle: {grund}")
    else:
        pruefe(False, f"ohne Kehle (Raster {raster}): eine Bahn")

# --- (b2) Die Kuppel endet am Teilboden: der Rest an der Unterkante (B-033) ---------------------
# Fuß r 20, dort 53° steil (n_z 0,6). Unter den Boden fährt keine Kugel; die Kugel r berührt die
# Fläche zuletzt bei z = r (1 − 0,6) ÷ (1 + r/25): Ø 6 bis 1,07 mm, Ø 2 bis 0,38. Bis 0.372.1 rollte
# Ø 6 über die Kante (kein Rest), danach maß das Restschlichten den Rest ohne den Boden und fuhr
# dort nicht. Jetzt: Es fährt nur am Fuß, nie unter den Boden, und im Quader steht am Fuß danach
# weniger als nach Ø 6 – neben dem Teil nichts unter dem Boden.
allein = Part.makeSphere(25, V(30, 30, -15)).common(Part.makeBox(60, 60, 10, V(0, 0, 0)))
flaechen_allein = kugelflaechen(allein)
gross_a = s3.planen(allein, flaechen_allein, werte(gross_form, oben=10.0, sicher=15.0))
rest_a = s3.planen(allein, flaechen_allein, werte(klein_form, davor=gross_form, oben=10.0,
                                                  sicher=15.0))  # fmt: skip
uk_g, uk_k = gross_a.unterkante, rest_a.unterkante
print(ascii(f"Unterkante: nach Ø 6 {uk_g.hoehe if uk_g else None}, nach dem Rest mit Ø 2 "
            f"{uk_k.hoehe if uk_k else None} (gerechnet 1,07 und 0,38)"))  # fmt: skip
pruefe(uk_g is not None and 0.9 < uk_g.hoehe < 1.3, f"Unterkante nach Ø 6: {uk_g}")
pruefe(uk_k is not None and uk_k.hoehe < 0.6, f"Unterkante nach dem Rest: {uk_k}")
pa = np.array([(p.x, p.y, p.z) for p in rest_a.punkte if not p.eilgang])
ra = np.hypot(pa[:, 0] - 30, pa[:, 1] - 30)
pruefe(pa[:, 2].min() >= -1e-6, f"Rest unter dem Boden: {pa[:, 2].min():.3f}")
pruefe(ra.min() > 16.5 and pa[:, 2].max() < 3.5, f"Rest nicht am Fuß: r {ra.min():.2f}, "
       f"z bis {pa[:, 2].max():.2f}")  # fmt: skip
netz_a = vf.vernetze(allein, 0.005).netz
qa = rm.Quader(0, 60, 0, 60, -3.0, 10.5, schritt=0.1)
soll_a = hf.hoehen(netz_a, qa.x, qa.y)
draussen = ~np.isfinite(soll_a)
qa.h[:] = np.where(draussen, 1.0, np.minimum(soll_a + 1.0, 10.5))  # 1 mm Aufmaß, auch daneben
for bahn_, form_ in ((gross_a, gross_form), (rest_a, klein_form)):
    for von, nach in zip(bahn_.punkte, bahn_.punkte[1:], strict=False):
        stuecke = ps._stuecke(von, nach)
        qa.fahre_stuecke([s[0] for s in stuecke], [s[1] for s in stuecke], form_)
    if bahn_ is gross_a:
        nach_gross_a = qa.h.copy()
xa, ya = np.meshgrid(qa.x, qa.y, indexing="ij")
fuss = (np.hypot(xa - 30, ya - 30) > 19.4) & ~draussen  # die letzten 0,6 mm vor der Unterkante
vorher_a = float(np.max((nach_gross_a - soll_a)[fuss]))
nachher_a = float(np.max((qa.h - soll_a)[fuss]))
mittel_v = float(np.mean((nach_gross_a - soll_a)[fuss]))
mittel_n = float(np.mean((qa.h - soll_a)[fuss]))
print(ascii(f"Am Fuß: nach Ø 6 bis {vorher_a:.3f} (im Mittel {mittel_v:.3f}), nach dem Rest bis "
            f"{nachher_a:.3f} ({mittel_n:.3f}) mm; daneben tiefstens {qa.h[draussen].min():.3f}, "
            f"ins Teil {np.min((qa.h - soll_a)[~draussen]):.3f}"))  # fmt: skip
# Die letzte Kurve der kleinen Kugel liegt bis einen Zeilenabstand über der tiefsten Lage: an
# einzelnen Stellen bis 0,32 statt 0,14 mm (gemessen 2026-11-15).
pruefe(
    nachher_a < 0.7 * vorher_a and mittel_n < 0.5 * mittel_v,
    f"am Fuß nach dem Rest {nachher_a:.3f} ({mittel_n:.3f}), davor {vorher_a:.3f} ({mittel_v:.3f})",
)
pruefe(qa.h[draussen].min() >= -1e-6, f"neben dem Teil unter dem Boden: {qa.h[draussen].min()}")
pruefe(np.min((qa.h - soll_a)[~draussen]) > -0.02, "ins Teil")
# Nach dem Restschlichten ein paar Linienzüge um den Rest, nicht viele Flecken (Zweifler 2026-11-15:
# mit dem Radius der kleinen Kugel geschlossen 27, mit dem der großen 10).
pruefe(uk_k is None or len(uk_k.linien) <= 12, f"nach dem Rest {len(uk_k.linien)} Linienzüge")

# --- (b3) Womit der Rest an der Unterkante kleiner wird: Hals, Schaft und Halter frei -----------
# Eine Kuppel R 20, unten bei z 0 abgeschnitten, Mitte bei z −2: am Fuß 84° steil. Eine Kugel Ø 3
# mit dem Schaft Ø 6 ihres Vorbilds ab 4,5 mm über der Spitze (wie „Kugel anlegen“ bis b290a573
# kopierte) stößt senkrecht an – gerechnet: Spitze am Fuß bei r 21,15, z 0,31, die Innenkante des
# Schafts bei r 18,15, dort steht die Kuppel bis z 6,40 – 1,6 mm über der Unterseite des Schafts
# (der Zweifler maß längs der Bahn mit distToShape 0,78; die Kugel um die Achse statt der Scheibe).
# Ein Schaft so dick wie die Kugel bleibt frei; die Kugel wie für die Ecken (Hals Ø 2,9 bis
# 13,5 mm, dann Schaft Ø 6) auch.
from camaddon import empfehlung as em

steil = Part.makeSphere(20, V(30, 30, -2)).common(Part.makeBox(60, 60, 18, V(0, 0, 0)))
steil_f = kugelflaechen(steil)
uk_s = s3.planen(steil, steil_f, werte(gross_form, raster=s3.VORSCHAU_RASTER)).unterkante
pruefe(uk_s is not None and uk_s.stellen is not None and len(uk_s.stellen) > 100, f"{uk_s}")
schaft_6 = s3.koerper_an_der_unterkante(steil, uk_s, 1.5, [(4.5, 60.0, 3.0)])
schaft_3 = s3.koerper_an_der_unterkante(steil, uk_s, 1.5, [(4.5, 60.0, 1.5)])
mit_hals = s3.koerper_an_der_unterkante(steil, uk_s, 1.5, [(4.5, 13.5, 1.45), (13.5, 60.0, 3.0)])
print(ascii(f"Unterkante 84°: Schaft Ø 6 ab 4,5 {schaft_6:+.3f}, Ø 3 {schaft_3}, mit Hals "
            f"{mit_hals:+.3f} mm im Teil"))  # fmt: skip
pruefe(1.4 < schaft_6 < 2.0, f"Schaft Ø 6 ab 4,5: {schaft_6}")
pruefe(schaft_3 == -math.inf, f"Schaft wie die Kugel: {schaft_3}")
pruefe(mit_hals < -s3.KOERPER_LUFT, f"mit Hals: {mit_hals}")


def kugel_wz(nummer, d, **masse):
    k = wz.Werkzeug(nummer=nummer, name=f"Kugel {d:g}", art=wz.KUGELFRAESER, durchmesser=d,
                    schneiden=2, schneidstoff=wz.VHM, **masse)  # fmt: skip
    k.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.06)]
    return k


k6 = kugel_wz(3, 6.0, schneidenlaenge=9.0, schaft=6.0, gesamtlaenge=60.0)
# Nur die Ø 6: eine neue Kugel Ø 3 wie für die Ecken – Schaft Ø 6 mit Hals, frei.
v = em.unterkante_vorschlag(steil, uk_s, k6, 3.0, wz.Bibliothek([k6]))
neu = wz.Werkzeug.aus_dict(v.werkzeug_neu) if v is not None and v.werkzeug_neu else None
print(
    ascii(
        f"Vorschlag nur Ø 6: {v and (v.d, v.werkzeug, round(v.luft, 2))}, neu "
        f"{neu and (neu.durchmesser, neu.schaft, neu.hals_d, neu.hals_laenge, neu.gesamtlaenge)}"
    )
)
pruefe(
    neu is not None and neu.durchmesser == 3.0 and neu.schaft == 6.0
    and abs(neu.hals_d - 2.9) < 1e-9 and neu.hals_laenge == 9.0 and v.luft >= s3.KOERPER_LUFT
    and abs(neu.schnittwerte[wz.ALLE][0].fz - 0.03) < 1e-9,
    f"neue Kugel: {v}",
)  # fmt: skip
# Eine Ø 3 mit Schaft Ø 6 ohne Hals in der Werkzeugverwaltung: stößt an – nicht sie, die neue.
k3_kurz = kugel_wz(4, 3.0, schneidenlaenge=4.5, schaft=6.0, gesamtlaenge=50.0)
v = em.unterkante_vorschlag(steil, uk_s, k6, 3.0, wz.Bibliothek([k6, k3_kurz]))
pruefe(v is not None and not v.werkzeug and v.werkzeug_neu, f"Ø 3 ohne Hals angeboten: {v}")
# Eine Ø 3 mit Schaft Ø 3, 30 mm ausgespannt: frei – die aus der Werkzeugverwaltung. (Ohne
# Ausspannlänge geschätzt 14 mm heraus: Die Mutter ER16 stieße 2,6 mm in die 18 mm hohe Kuppel.)
k3 = kugel_wz(5, 3.0, schneidenlaenge=9.0, gesamtlaenge=60.0, ausspannlaenge=30.0)
v = em.unterkante_vorschlag(steil, uk_s, k6, 3.0, wz.Bibliothek([k6, k3_kurz, k3]))
pruefe(v is not None and v.werkzeug == k3.kennung, f"Ø 3 mit Schaft Ø 3 nicht angeboten: {v}")
# Ein Torus Ø 10 mit r 1 macht den Rest mit r 1: eine Kugel Ø 4 (r 2) hilft nicht – erst Ø 1.
torus = wz.Werkzeug(nummer=6, name="Torus", art=wz.TORUSFRAESER, durchmesser=10.0, schneiden=4,
                    eckradius=1.0)  # fmt: skip
k4 = kugel_wz(7, 4.0)
v = em.unterkante_vorschlag(steil, uk_s, torus, 1.0, wz.Bibliothek([torus, k4]))
pruefe(v is not None and not v.werkzeug and not v.werkzeug_neu and v.d == 1.0, f"Torus: {v}")
k1 = kugel_wz(8, 1.0, schneidenlaenge=1.5, schaft=6.0, hals_d=0.9, hals_laenge=20.0,
              gesamtlaenge=60.0, ausspannlaenge=30.0)  # fmt: skip
v = em.unterkante_vorschlag(steil, uk_s, torus, 1.0, wz.Bibliothek([torus, k4, k1]))
pruefe(v is not None and v.werkzeug == k1.kennung, f"Torus mit Kugel Ø 1: {v}")

# --- (c) Die Operation im Job ---------------------------------------------------------------------
pruefe(s3op.eckenradius(ff.kugel(3.0)) == 3.0, "Eckenradius Kugel")
pruefe(abs(s3op.eckenradius(ff.torus(3.0, 1.0)) - 1.0) < 1e-9, "Eckenradius Torus")
pruefe(s3op.eckenradius(ff.scheibe(3.0)) == 0.0, "Eckenradius Schaftfräser")
import Path.Main.Job as PathJob

t3 = wz.Werkzeug(
    nummer=3,
    name="Kugel 2",
    art=wz.KUGELFRAESER,
    durchmesser=2.0,
    schneiden=2,
    schneidenlaenge=6.0,
    schneidstoff=wz.VHM,
)
t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.1, ap=0.1, vc=120.0, fz=0.03)]
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([wz.standardwerkzeug(), t3]))
doc = FreeCAD.newDocument("Kuppel")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
tc = js.controller_ohne_transaktion(doc, job, t3, t3.schnittwerte[wz.ALLE][0])
doc.recompute()
op = s3op.lege_an(job, tc, s3.GRATHOEHE, flaechen=kuppel, davor=(6.0, 3.0))
doc.recompute()
pruefe(op.Label == "Restschlichten T3", f"Name {op.Label}")
pruefe(s3op.ist_restschlichten(op) and s3op.ist_schlichten3d(op), "ist_restschlichten")
davor = s3op.form_davor(op)
pruefe(davor is not None and davor.nur_kugel and abs(davor.radius - 3.0) < 1e-9, "Form davor")
pruefe(js.operationsart(op) == "schlichten3d", f"Art {js.operationsart(op)}")
befehle = len(op.Path.Commands)
pruefe(
    befehle > 100 and op.Hoehenlinien + op.Zeilen > 0,
    f"Operation: {befehle} Befehle, {op.Hoehenlinien} Höhen, {op.Zeilen} Zeilen",
)
s3op.aendere(op, tc, s3.GRATHOEHE, flaechen=kuppel, davor=(0.0, 0.0))
doc.recompute()
pruefe(op.Label == "3D-Schlichten T3" and not s3op.ist_restschlichten(op), f"ganz: {op.Label}")
print(ascii(f"Operation: {befehle} Befehle als Rest, {len(op.Path.Commands)} ganz"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
