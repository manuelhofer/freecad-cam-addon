# Prüft Rohteil und Fertigteil im Quader (W-006 S3d, 2,5D): Die Oberseite eines Netzes im
# Raster (hoehenfeld.hoehen) – über dem Block 20, über dem Absatz 25, auf der Kante das
# Höhere, daneben nichts; mit `innen` zählt die Kante zu keiner Fläche. Ein Schnitt des
# Schaftfräsers nimmt unter sich bis zur Spitze weg, daneben nichts; der Kugelfräser lässt
# daneben die Kugel stehen; ein Stück fährt zwischen zwei Punkten durch. Dann „Planfräsen“
# auf der Beispiel-Fräse: Der Abtrag ist der Quader (nicht die Stange), nach dem Abfahren ist
# die gewählte Fläche grün, nirgends fehlt etwas im Teil, der Absatz hat keine Farbe (nur die
# gewählte Fläche zählt); zurück zu einer früheren Station rechnet von vorn; fürs Bild die
# Punkte und Farben. Ein Zylinder als Rohteil gibt keinen Quader.
import math
import os
import pathlib
import sys
import tempfile
import time

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import abfahren as ab
from camaddon import beispielmaschine as bm
from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import job_schnittwerte as js
from camaddon import planfraesen as pf
from camaddon import reichweite as rw
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_huelle as vh
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")

# --- Die Oberseite eines Netzes im Raster ---------------------------------------------------
block = Part.makeBox(60, 40, 20).fuse(Part.makeBox(10, 40, 5, V(0, 0, 20))).removeSplitter()
netz = vh.vernetze(block)
x = -1.0 + 0.5 * np.arange(125)  # −1 … 61
y = -1.0 + 0.5 * np.arange(85)  # −1 … 41
z = hf.hoehen(netz, x, y)
ix = {
    wert: int(np.argmin(np.abs(x - wert)))
    for wert in (-1.0, 0.0, 5.0, 10.0, 10.5, 30.0, 60.0, 61.0)
}
iy = int(np.argmin(np.abs(y - 20.0)))
pruefe(z[ix[-1.0], iy] == hf.KEIN_TREFFER and z[ix[61.0], iy] == hf.KEIN_TREFFER, "neben dem Teil")
pruefe(abs(z[ix[5.0], iy] - 25.0) < 1e-9, f"über dem Absatz: {z[ix[5.0], iy]}")
pruefe(abs(z[ix[30.0], iy] - 20.0) < 1e-9, f"über der Fläche: {z[ix[30.0], iy]}")
pruefe(abs(z[ix[10.0], iy] - 25.0) < 1e-9, f"auf der Kante das Höhere: {z[ix[10.0], iy]}")
pruefe(abs(z[ix[0.0], iy] - 25.0) < 1e-9 and abs(z[ix[60.0], iy] - 20.0) < 1e-9, "am Rand")
pruefe(np.isfinite(z[ix[0.0] : ix[60.0] + 1, :]).sum() == 121 * 81, "das Teil füllt sein Raster")
# Nur die Fläche bei 20 (ohne die Kante zum Absatz): die Zellen der gewählten Flächen.
from camaddon import vierachs_flaechen as vf

fnetz = vf.vernetze(block)
nummer = next(
    i
    for i, f in enumerate(block.Faces)
    if abs(f.CenterOfMass.z - 20.0) < 1e-9 and abs(f.normalAt(0, 0).z - 1.0) < 1e-9
)
nur_netz = vh.Netz(fnetz.netz.punkte, fnetz.netz.dreiecke[fnetz.flaeche == nummer], 0.02)
innen = np.isfinite(hf.hoehen(nur_netz, x, y, innen=True))
pruefe(innen[ix[30.0], iy] and innen[ix[10.5], iy], "Fläche innen")
pruefe(not innen[ix[10.0], iy] and not innen[ix[60.0], iy] and not innen[ix[5.0], iy], "Rand")
print(ascii(f"Oberseite: {np.count_nonzero(innen)} Zellen der Fläche bei 20"))

# --- Ein Schnitt ----------------------------------------------------------------------------
q = rm.Quader(-1.0, 61.0, -1.0, 41.0, -1.0, 26.0)
pruefe(q.h.shape == (125, 85) and q.h.min() == 26.0, f"Quader {q.h.shape}")
q.schnitt(30.0, 20.0, 22.0, 5.0)
mitte = q.h[ix[30.0], iy]
pruefe(abs(mitte - 22.0) < 1e-9, f"unter dem Fräser: {mitte}")
rand = q.h[int(np.argmin(np.abs(x - 34.5))), iy]  # 4,5 mm daneben: noch unter dem Fräser
pruefe(abs(rand - 22.0) < 1e-9, f"4,5 mm daneben: {rand}")
daneben = q.h[int(np.argmin(np.abs(x - 35.5))), iy]  # 5,5 mm: außerhalb
pruefe(daneben == 26.0, f"5,5 mm daneben: {daneben}")
pruefe(q.h[ix[5.0], iy] == 26.0, "weit weg weggenommen")
kugel = ff.kugel(3.0)
q.schnitt(10.0, 10.0, 22.0, kugel)
iy10 = int(np.argmin(np.abs(y - 10.0)))
pruefe(abs(q.h[ix[10.0], iy10] - 22.0) < 1e-9, f"Kugel in der Mitte: {q.h[ix[10.0], iy10]}")
seitlich = q.h[int(np.argmin(np.abs(x - 12.0))), iy10]  # 2 mm daneben: 3 − √(9 − 4) höher
pruefe(abs(seitlich - (22.0 + 3.0 - math.sqrt(5.0))) < 1e-6, f"Kugel 2 mm daneben: {seitlich}")
# Ein Stück von (20, 30) nach (50, 30) auf 24 mit R 5: dazwischen überall 24.
q.fahre((20.0, 30.0, 24.0), (50.0, 30.0, 24.0), 5.0)
iy30 = int(np.argmin(np.abs(y - 30.0)))
dazwischen = q.h[ix[30.0] : int(np.argmin(np.abs(x - 50.0))) + 1, iy30]
pruefe(
    (np.abs(dazwischen - 24.0) < 1e-9).all(), f"das Stück: {dazwischen.min()} … {dazwischen.max()}"
)
pruefe(q.h[ix[30.0], int(np.argmin(np.abs(y - 36.0)))] == 26.0, "6 mm neben dem Stück")
q.zuruecksetzen()
pruefe(q.h.min() == 26.0, "zurückgesetzt")

# --- Planfräsen auf der Beispiel-Fräse ---------------------------------------------------------
import Path.Main.Job as PathJob

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
schaft = wz.standardwerkzeug()  # Ø 12, Planen mit ae 8,4 und ap 1,2: 5 Lagen zu 6 Zeilen
planen = next(e for e in schaft.einsaetze(wz.ALLE) if e.art == wz.PLANEN)
ue.uebergeben(wz.Bibliothek([schaft]))
asm, ma = bm.fraesmaschine()
doc = FreeCAD.newDocument("Quader")
teil = doc.addObject("Part::Feature", "Teil")
teil.Shape = block
doc.recompute()
job = PathJob.Create("Job", [teil])
tc1 = js.controller_ohne_transaktion(doc, job, schaft, planen)
doc.recompute()
klon = job.Model.Group[0]
flaeche = next(e.name for e in hf.ebenen_oben(klon.Shape) if abs(e.z - 20.0) < 1e-6)
op = pf.lege_an(job, tc1, zustellung=planen.ap, zeilenabstand=planen.ae, flaechen=[flaeche])
doc.recompute()
pruefe(op.Lagen == 5 and op.Zeilen == 30, f"Planfräsen: {op.Lagen} Lagen, {op.Zeilen} Zeilen")
p = rw.Pruefung(asm, ma)
nullpunkt = rw.vorschlag_nullpunkt(job)
fahrt = ab.abfahrt(p, job, nullpunkt)
pruefe(len(fahrt.stationen) > 50, f"{len(fahrt.stationen)} Stationen")
abtrag = rm.fuer(fahrt, job, fahrt.am_werkstueck())
pruefe(isinstance(abtrag, rm.QuaderAbtrag), f"Abtrag: {type(abtrag).__name__}")
if isinstance(abtrag, rm.QuaderAbtrag):
    box = job.Stock.Shape.BoundBox
    pruefe(
        abs(abtrag.quader.z_bis - box.ZMax) < 1e-9 and abs(abtrag.quader.x[0] - box.XMin) < 1e-9,
        f"Quader {abtrag.quader.x[0]} … {abtrag.quader.z_bis}, Rohteil {box}",
    )
    pruefe(abtrag.flaechen == {int(flaeche[4:]) - 1}, f"gewählte Flächen: {abtrag.flaechen}")
    beginn = time.time()
    abtrag.bis_station(abtrag.letzte())
    dauer_ab = time.time() - beginn
    beginn = time.time()
    vergleich = abtrag.vergleich()
    dauer_vergleich = time.time() - beginn
    pruefe(vergleich.nur_gewaehlte, "nicht als „nur gewählte“ vermerkt")
    nur = abtrag._nur
    pruefe(
        nur is not None and nur.sum() > 7000,
        f"Zellen der Fläche: {None if nur is None else nur.sum()}",
    )
    if nur is not None:
        auf_der_flaeche = vergleich.farbe[nur]
        gruen = np.count_nonzero(auf_der_flaeche == rm.GRUEN) / max(1, len(auf_der_flaeche))
        pruefe(gruen > 0.99, f"grün nur {gruen:.1%}, größter Rest {vergleich.groesster:.3f}")
        pruefe((vergleich.farbe[~nur] == rm.OHNE_TEIL).all(), "Farbe neben der gewählten Fläche")
    pruefe(
        vergleich.kleinster > -rm.BLAU_AB and not (vergleich.farbe == rm.BLAU).any(),
        f"ins Teil: kleinster Rest {vergleich.kleinster:.3f}",
    )
    pruefe(vergleich.groesster <= rm.GRUEN_BIS + 1e-9, f"größter Rest {vergleich.groesster:.3f}")
    # Über dem Absatz steht das Rohteil noch (26), über der Fläche nicht mehr (20).
    qx, qy = abtrag.quader.x, abtrag.quader.y
    h_absatz = abtrag.quader.h[int(np.argmin(np.abs(qx - 5.0))), int(np.argmin(np.abs(qy - 20.0)))]
    h_flaeche = abtrag.quader.h[
        int(np.argmin(np.abs(qx - 30.0))), int(np.argmin(np.abs(qy - 20.0)))
    ]
    pruefe(abs(h_absatz - 26.0) < 1e-9 and abs(h_flaeche - 20.0) < 1e-9, f"{h_absatz}, {h_flaeche}")
    print(
        ascii(
            f"Abtrag {dauer_ab:.1f} s, Vergleich {dauer_vergleich:.1f} s; Rest "
            f"{vergleich.kleinster:.3f} ... {vergleich.groesster:.3f} mm, gruen {gruen:.1%}"
        )
    )
    # Zurück: von vorn gerechnet – vor dem ersten Schnitt ist der Quader ganz.
    abtrag.bis_station(1)
    pruefe(
        abtrag.quader.h.min() == abtrag.quader.z_bis, f"zurück am Anfang: {abtrag.quader.h.min()}"
    )
    # Fürs Bild: Punkte und Farben im selben Raster.
    bx, by, bh = rm.darstellung_quader(abtrag.quader)
    pruefe(bh.shape == (len(bx), len(by)) == abtrag.quader.h.shape, "Bild")
    pruefe(rm.farben_quader(vergleich).shape == abtrag.quader.h.shape, "Farben fürs Bild")

# --- Ein Zylinder als Rohteil ist kein Quader --------------------------------------------------
from Path.Main import Stock as PathStock

zylinder = PathStock.CreateCylinder(job, radius=40.0, height=30.0)
alt = job.Stock
job.Stock = zylinder
doc.recompute()
pruefe(rm.fuer_quader(fahrt, job, fahrt.am_werkstueck()) is None, "Zylinder als Quader")
job.Stock = alt
doc.recompute()

FreeCAD.closeDocument(doc.Name)
if asm is not None:
    FreeCAD.closeDocument(asm.Document.Name)

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
