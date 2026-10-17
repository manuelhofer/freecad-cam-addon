# Prüft den Abtrag mit schräg stehendem Werkzeug (schraeg_abtrag.py; legros im Forum, 2026-10-10:
# ein Kegel mit „Flanke“ auf der Beispielmaschine 5-Achs Tisch/Tisch, der Abspieler trug nichts ab;
# Manuel, 2026-10-11: „dann muss man das ändern“). Ein Kegel Ø 50 → Ø 30, 30 hoch, auf einer Platte
# 80 × 80 × 10, das Rohteil ein Kasten; „Flanke“ mit einem Schaftfräser Ø 10 (35 mm Schneide: ein
# Umlauf; 12 mm: drei Lagen). Bisher kein Abtrag (restmaterial, simultan_restbild: None); jetzt
# steht auf dem Mantel noch der Kegel, unten am Fuß ist ein Ring bis auf die Platte weg, in der Ecke
# steht das Rohteil. Dazu tiefste() an einem schrägen Zylinder und einer Kapsel nachgerechnet. Und
# der Halter (flanke_bahn.halter_pruefen): mit 12 mm Schneide steht der ER16 32 mm von der Spitze,
# in den unteren Lagen im Kegel – frei wäre er ab gut 41 mm; mit 35 mm Schneide ist er frei.
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
import Path.Main.Job as PathJob
from Path.Tool.camassets import user_asset_store

from camaddon import abfahren as ab
from camaddon import beispielmaschine, simultan_restbild, sprache
from camaddon import flanke as flop
from camaddon import flanke_bahn as fb
from camaddon import halter as hl
from camaddon import job_schnittwerte as js
from camaddon import nebenrechner as nr
from camaddon import reichweite as rw
from camaddon import restmaterial as rm
from camaddon import schraeg_abtrag as sa
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")

# --- tiefste(): ein schräger Zylinder und eine Kapsel, Punkt für Punkt nachgerechnet -------------
achse = np.array([math.sin(math.radians(30)), 0.0, math.cos(math.radians(30))])
# Das Raster neben den Kanten (genau auf ihnen träfe die Abtastung den Berührpunkt nicht).
xs, ys = np.meshgrid(np.linspace(-7.93, 20.07, 57), np.linspace(-7.97, 8.03, 33), indexing="ij")
for kugel in (False, True):
    z = sa.tiefste(xs, ys, (0.0, 0.0, 0.0), achse, 5.0, 20.0, kugel)
    for (i, j), zz in np.ndenumerate(z):
        # Die Senkrechte durch die Zelle, fein abgetastet: der tiefste Punkt im Körper – der
        # Zylinder über der Grundfläche bis 20 mm, mit Kugel die Halbkugel um 5 mm über der Spitze.
        hoehen = np.linspace(-6.0, 25.0, 31001)
        punkte = np.stack(
            [np.full_like(hoehen, xs[i, j]), np.full_like(hoehen, ys[i, j]), hoehen], 1
        )
        t = punkte @ achse
        abstand = np.linalg.norm(punkte - t[:, None] * achse, axis=1)
        drin = (abstand <= 5.0) & (t >= (5.0 if kugel else 0.0)) & (t <= 20.0)
        if kugel:
            drin |= np.linalg.norm(punkte - 5.0 * achse, axis=1) <= 5.0
        soll = hoehen[drin].min() if drin.any() else math.inf
        if not (abs(zz - soll) < 2e-3 or (math.isinf(zz) and math.isinf(soll))):
            pruefe(
                False,
                f"tiefste kugel={kugel} bei ({xs[i, j]:.1f}, {ys[i, j]:.1f}): {zz} statt {soll}",
            )
            break

# --- Der Kegel mit „Flanke“ auf der 5-Achs-Maschine ---------------------------------------------
platte = Part.makeBox(80, 80, 10)
kegel = Part.makeCone(25, 15, 30, V(40, 40, 10))
teil = platte.fuse(kegel).removeSplitter()
mantel = [f"Face{i + 1}" for i in range(len(teil.Faces)) if fb.ist_wand(teil, f"Face{i + 1}")]
pruefe(len(mantel) == 1, f"Wände: {mantel}")

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
asm, ma = beispielmaschine.fuenfachs_tisch_tisch()
pruefung = rw.Pruefung(asm, ma)


def abtrag_mit(schneide):
    werkzeug = wz.Werkzeug(
        nummer=5,
        name=f"VHM 10 – {schneide:g}",
        art=wz.SCHAFTFRAESER,
        durchmesser=10.0,
        schneiden=4,
        schneidenlaenge=schneide,
        schneidstoff=wz.VHM,
    )
    werkzeug.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=20.0, vc=150.0, fz=0.04)
    ]
    # Mit kurzer Schneide prüft die Flanke den Halter (ohne: „ohne Halter geprüft“) – ein ER16.
    bibliothek = wz.Bibliothek([wz.standardwerkzeug(), werkzeug])
    halter = hl.aus_vorlage("er16")
    werkzeug.halter = halter.kennung
    werkzeug.gesamtlaenge = schneide + 40.0
    bibliothek.halter = [halter]
    bibliothek.speichern()
    ue.uebergeben(bibliothek)
    doc = FreeCAD.newDocument("Kegel")
    objekt = doc.addObject("Part::Feature", "Teil")
    objekt.Shape = teil
    doc.recompute()
    job = PathJob.Create("Job", [objekt])
    job.Stock.ExtZpos = 0.0
    doc.recompute()
    tc = js.controller_ohne_transaktion(doc, job, werkzeug, werkzeug.schnittwerte[wz.ALLE][0])
    doc.recompute()
    op = flop.lege_an(job, tc, flaechen=mantel)
    doc.recompute()
    fahrt = ab.abfahrt(pruefung, job, rw.nullpunkt(job), bibliothek)
    spitzen = fahrt.am_werkstueck()
    return doc, job, op, fahrt, spitzen, werkzeug, bibliothek


for schneide, lagen in ((35.0, 1), (12.0, 3)):
    doc, job, op, fahrt, spitzen, werkzeug, bibliothek = abtrag_mit(schneide)
    # Der Halter (flanke_bahn.halter_pruefen): mit 12 mm Schneide steht der ER16 in den unteren
    # Lagen im Kegel – die Bahn sagt es und wie weit das Werkzeug herausstehen müsste.
    koerper = flop.koerper_ueber_der_schneide(werkzeug, bibliothek)
    bahn = flop.bahn_fuer(job, job.Model.Group, 5.0, schneide, mantel, koerper=koerper)
    anstoss = bahn.anstoss
    print(ascii(f"Schneide {schneide}: Koerper {koerper}, Anstoss {anstoss}"))
    if lagen == 1:
        pruefe(anstoss is None, f"Schneide {schneide}: Halter stößt an: {anstoss}")
    else:
        pruefe(
            anstoss is not None
            and abs(anstoss.heraus - 32.0) < 1e-6
            and 40.0 < anstoss.mindestens < 44.0,
            f"Schneide {schneide}: Anstoß {anstoss}",
        )
    pruefe(op.Lagen == lagen, f"Schneide {schneide}: {op.Lagen} Lagen statt {lagen}")
    pruefe(rm.fuer(fahrt, job, spitzen) is None, "restmaterial trägt schon ab?")
    pruefe(simultan_restbild.fuer(fahrt, job, spitzen) is None, "simultan_restbild trägt schon ab?")
    abtrag = sa.fuer(fahrt, job, spitzen)
    pruefe(abtrag is not None, f"Schneide {schneide}: kein Abtrag")
    if abtrag is None:
        FreeCAD.closeDocument(doc.Name)
        continue
    abtrag.bis_station(abtrag.letzte())
    q = abtrag.quader

    def hoehe(x, y, q=q):
        return float(q.h[np.argmin(np.abs(q.x - x)), np.argmin(np.abs(q.y - y))])

    oben = q.z_bis
    for winkel in range(0, 360, 30):
        w = math.radians(winkel)
        # Auf dem Mantel (r 20 → z 25): der Kegel steht, kaum mehr.
        mantel_z = hoehe(40 + 20 * math.cos(w), 40 + 20 * math.sin(w))
        pruefe(
            24.5 < mantel_z < 25.6,
            f"Schneide {schneide}, {winkel}°: auf dem Mantel {mantel_z:.2f} statt 25",
        )
        # Am Fuß außen (r 28): weg bis auf die Stirn des Fräsers – schräg wie seine Achse, am Fuß
        # auf der Platte, 3 mm weiter außen 1 mm höher (tan 18,4°).
        fuss_z = hoehe(40 + 28 * math.cos(w), 40 + 28 * math.sin(w))
        pruefe(
            10.5 < fuss_z < 11.3, f"Schneide {schneide}, {winkel}°: am Fuß {fuss_z:.2f} statt 11"
        )
        # Weiter draußen (r 37) reicht er nicht hin: das Rohteil.
        aussen_z = hoehe(40 + 37 * math.cos(w), 40 + 37 * math.sin(w))
        pruefe(aussen_z == oben, f"Schneide {schneide}, {winkel}°: außen {aussen_z:.2f}")
    pruefe(hoehe(3, 3) == oben, f"Schneide {schneide}: in der Ecke {hoehe(3, 3):.2f} statt {oben}")
    # Zurück an den Anfang: das Rohteil ganz; wieder vor: dasselbe.
    vorher = q.h.copy()
    abtrag.bis_station(0)
    pruefe(np.all(q.h == oben), "zurück an den Anfang: nicht das ganze Rohteil")
    abtrag.bis_station(abtrag.letzte())
    pruefe(np.array_equal(q.h, vorher), "noch einmal abgefahren: anders")
    # Auf den Nebenrechnern in Stücken (P-2026-10-17-39): dieselben Höhen wie allein (das
    # Minimum je Zelle hängt nicht von der Reihenfolge ab) – und sie haben wirklich gerechnet.
    alt_ab = sa.VERTEILT_AB_STATIONEN
    sa.VERTEILT_AB_STATIONEN = 1
    try:
        abtrag.bis_station(0)
        abtrag.bis_station(abtrag.letzte())
        pruefe(nr.pool().arbeiter > 0, "Stücke nicht auf den Nebenrechnern")
        pruefe(np.allclose(q.h, vorher, atol=1e-9), "verteilt anders als allein")
        sa.VERTEILT_AB_STATIONEN = 10**9
        abtrag.bis_station(0)
        abtrag.bis_station(abtrag.letzte())
        pruefe(np.array_equal(q.h, vorher), "allein (im Takt) anders")
    finally:
        sa.VERTEILT_AB_STATIONEN = alt_ab
    vergleich = abtrag.vergleich()
    pruefe(vergleich is not None, "kein Vergleich am Ende")
    FreeCAD.closeDocument(doc.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
