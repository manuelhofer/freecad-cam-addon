# Prüft die Flächenwahl der 4-Achs-Bearbeitung (W-003 Stufe V4): Welle Ø 20 mit Abflachung –
# ein Strahl von außen trifft zuerst die Abflachung oder den Mantel, beide schauen nach außen
# und sind ganz erreichbar, Stirnflächen und Wände quer zur Achse trifft kein Strahl; der
# Bereich des Fräsers reicht um seinen Radius über die Abflachung hinaus. Welle mit Überhang:
# Die Innenseite des Kragens ist nicht erreichbar, der Mantel darunter nur zum Teil. Dazu die
# Namen der Flächen, die Sätze, wenn es nicht geht, und die Beschreibung für die Liste.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import vierachs_flaechen as vf
from camaddon import vierachs_huelle as vh
from camaddon import vierachs_rohteil as vr
from camaddon.reichweite import weg_text
from camaddon.sprache import tr

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
LAENGS, RADIAL = (0, 0, 1), (1, 0, 0)


def flaechen_mit(form, bedingung):
    return [i for i, f in enumerate(form.Faces) if bedingung(f)]


def eben_mit_normale(richtung):
    return lambda f: vr.ist_eben(f) and (vr.aussennormale(f) - V(*richtung)).Length < 1e-6


def zylinder(radius):
    return lambda f: isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - radius) < 1e-6


# --- Welle Ø 20 von a = 0 bis 40, Abflachung auf x = 8 von a = 10 bis 30 --------------------
welle = Part.makeCylinder(10, 40).cut(Part.makeBox(10, 30, 20, V(8, -15, 10))).removeSplitter()
flach = flaechen_mit(welle, eben_mit_normale((1, 0, 0)))
mantel = flaechen_mit(welle, zylinder(10))
stirn = flaechen_mit(welle, eben_mit_normale((0, 0, 1))) + flaechen_mit(
    welle, eben_mit_normale((0, 0, -1))
)
pruefe(len(flach) == 1 and mantel and len(stirn) == 4, f"Flächen: {flach} {mantel} {stirn}")

fnetz = vf.vernetze(welle)
ganz = welle.copy().tessellate(vh.TOLERANZ)
pruefe(
    len(fnetz.netz.dreiecke) == len(ganz[1]),
    f"{len(fnetz.netz.dreiecke)} Dreiecke je Fläche, {len(ganz[1])} im Ganzen",
)
pruefe(
    set(fnetz.flaeche.tolist()) == set(range(len(welle.Faces)))
    and fnetz.anzahl == len(welle.Faces),
    "jede Fläche hat Dreiecke",
)
# Die Dreiecke zeigen nach außen – auch die der umgekehrten Flächen.
punkte, dreiecke = fnetz.netz.punkte, fnetz.netz.dreiecke
normale = np.cross(
    punkte[dreiecke[:, 1]] - punkte[dreiecke[:, 0]], punkte[dreiecke[:, 2]] - punkte[dreiecke[:, 0]]
)
mitte = punkte[dreiecke].mean(axis=1)
am_mantel = np.isin(fnetz.flaeche, mantel)
nach_aussen = np.einsum("ij,ij->i", normale[am_mantel][:, :2], mitte[am_mantel][:, :2]) > 0
pruefe(nach_aussen.all(), f"Mantel: {int((~nach_aussen).sum())} Dreiecke zeigen nach innen")
am_flach = fnetz.flaeche == flach[0]
pruefe((normale[am_flach][:, 0] > 0).all(), "Abflachung: Dreiecke zeigen nach innen")

a_werte = vf.raster_a(-5.0, 45.0)
phi_werte = vh.raster_phi(1.0)
sicht = vf.sicht(fnetz, LAENGS, RADIAL, a_werte, phi_werte)
i20 = int(np.searchsorted(a_werte, 20.0))
pruefe(sicht.flaeche[i20, 0] == flach[0], f"a 20, 0°: Fläche {sicht.flaeche[i20, 0]}")
pruefe(abs(sicht.r[i20, 0] - 8.0) < 1e-6, f"a 20, 0°: Radius {sicht.r[i20, 0]}")
pruefe(sicht.flaeche[i20, 180] in mantel, f"a 20, 180°: Fläche {sicht.flaeche[i20, 180]}")
pruefe(9.97 < sicht.r[i20, 180] <= 10.0 + 1e-9, f"a 20, 180°: Radius {sicht.r[i20, 180]}")
pruefe(sicht.flaeche[int(np.searchsorted(a_werte, 5.0)), 0] in mantel, "a 5, 0°: Mantel")
pruefe((sicht.flaeche[a_werte < -0.1] == -1).all(), "vor der Welle: kein Treffer")
pruefe(set(vf.mantelflaechen(sicht)) == set(flach + mantel), f"Mantel: {vf.mantelflaechen(sicht)}")
for nummer in flach + mantel:
    anteil = vf.erreichbar(sicht, nummer)
    pruefe(anteil >= vf.GANZ, f"Fläche {nummer}: zu {anteil} erreichbar")
for nummer in stirn:
    pruefe(vf.erreichbar(sicht, nummer) is None, f"Stirn {nummer}: {vf.erreichbar(sicht, nummer)}")

# Der Bereich eines Fräsers R 3 über der Abflachung: längs 3 mm über ihre Enden hinaus, rundum
# bis dort, wo er ihre Kante (unter 36,87° auf dem Radius 10) noch berührt.
bereich = vf.bereich(sicht, flach, 3.0)
spalte = bereich.drin[:, 0]
pruefe(
    abs(a_werte[spalte].min() - 7.0) <= 0.25 and abs(a_werte[spalte].max() - 33.0) <= 0.25,
    f"längs: {a_werte[spalte].min()} … {a_werte[spalte].max()}",
)
zeile = np.degrees(phi_werte[bereich.drin[i20]])
zeile = np.where(zeile > 180, zeile - 360, zeile)
kante = math.degrees(math.atan2(6, 8))
weiter = math.degrees(math.asin(3.0 / 10.0))
pruefe(
    kante + weiter - 2.0 <= zeile.max() <= kante + weiter + 1.0 and zeile.min() == -zeile.max(),
    f"rundum: {zeile.min()} … {zeile.max()} (Kante {kante:.2f} + {weiter:.2f})",
)
pruefe(not bereich.drin[:, 180].any(), "gegenüber: im Bereich")
pruefe(
    bereich.bei([20.0, 20.0, 50.0], [0.0, math.pi, 0.0]).tolist() == [True, False, False],
    "Bereich.bei",
)
pruefe(vf.bereich(sicht, (), 3.0).drin.sum() == 0, "ohne Flächen: ein Bereich")
pruefe(
    (vf.bereich(sicht, flach, 0.0).drin == (sicht.flaeche == flach[0])).all(),
    "Radius 0: genau die Fläche",
)

# --- Welle mit Überhang: Kragen Ø 32 innen Ø 24 von a = 20 bis 30, an einer Scheibe ----------
kragen = (
    Part.makeCylinder(10, 40)
    .fuse(Part.makeCylinder(16, 2, V(0, 0, 18)))
    .fuse(Part.makeCylinder(16, 10, V(0, 0, 20)).cut(Part.makeCylinder(12, 10, V(0, 0, 20))))
    .removeSplitter()
)
innen = flaechen_mit(kragen, zylinder(12))
unter = [
    i
    for i in flaechen_mit(kragen, zylinder(10))
    if kragen.Faces[i].BoundBox.ZMax > 30 and kragen.Faces[i].BoundBox.ZMin > 19
]
pruefe(len(innen) == 1 and len(unter) == 1, f"Kragen: {innen} {unter}")
sicht_kragen = vf.sicht(vf.vernetze(kragen), LAENGS, RADIAL, a_werte, phi_werte)
pruefe(vf.erreichbar(sicht_kragen, innen[0]) == 0.0, "Innenseite des Kragens erreichbar")
pruefe(innen[0] not in vf.mantelflaechen(sicht_kragen), "Innenseite des Kragens: Mantel")
anteil = vf.erreichbar(sicht_kragen, unter[0])
pruefe(0.4 < anteil < 0.6, f"Mantel unter dem Kragen: zu {anteil} erreichbar (etwa die Hälfte)")
pruefe(unter[0] in vf.mantelflaechen(sicht_kragen), "Mantel unter dem Kragen: kein Mantel")

# --- Namen, Bereich für die Operationen, Sätze -------------------------------------------------
pruefe(vf.nummern(["Face3", "Face1", "Edge2", "Face0", "Face3"]) == (0, 2), "nummern")
pruefe(vf.namen((2, 0)) == ["Face1", "Face3"], "namen")
pruefe(vf.bereich_fuer(welle, LAENGS, RADIAL, [], 3.0) is None, "ohne Flächen: nicht rundum")
fuer = vf.bereich_fuer(welle, LAENGS, RADIAL, vf.namen(flach), 3.0)
pruefe(
    fuer is not None and fuer.bei([20.0], [0.0])[0] and not fuer.bei([20.0], [math.pi])[0], "fuer"
)
try:
    vf.bereich_fuer(welle, LAENGS, RADIAL, ["Face99"], 3.0)
    pruefe(False, "Face99: kein Fehler")
except ValueError as satz:
    pruefe(str(satz) == tr("vf.fehler.fehlt", namen="Face99"), f"Face99: {satz}")
try:
    vf.bereich_fuer(kragen, LAENGS, RADIAL, vf.namen(innen), 3.0)
    pruefe(False, "nur die Innenseite: kein Fehler")
except ValueError as satz:
    pruefe(str(satz) == tr("vf.fehler.nicht_erreichbar"), f"Innenseite: {satz}")

pruefe(vf.beschreibung(welle.Faces[flach[0]], LAENGS) == tr("vf.art.ebene"), "Ebene")
pruefe(
    vf.beschreibung(welle.Faces[mantel[0]], LAENGS)
    == tr("vf.art.zylinder_mittig", d=weg_text(20.0)),
    f"Mantel: {vf.beschreibung(welle.Faces[mantel[0]], LAENGS)}",
)
exzenter = Part.makeCylinder(5, 10, V(8, 0, 0))
seite = flaechen_mit(exzenter, zylinder(5))[0]
pruefe(
    vf.beschreibung(exzenter.Faces[seite], LAENGS)
    == tr("vf.art.zylinder_aussermittig", d=weg_text(10.0), versatz=weg_text(8.0)),
    f"Exzenter: {vf.beschreibung(exzenter.Faces[seite], LAENGS)}",
)
quer = Part.makeCylinder(5, 10, V(0, 0, 0), V(1, 0, 0))
pruefe(
    vf.beschreibung(quer.Faces[flaechen_mit(quer, zylinder(5))[0]], LAENGS)
    == tr("vf.art.zylinder_quer", d=weg_text(10.0)),
    "quer",
)

# --- Rundum umsonst (Manuels Messspitzenhalter, 2026-10-18): vor der Stirn oder gar nichts ---
# Vorn ein Bund Ø 15, Ringgrund 0,8 tief, außen eine Fase 45° bis Ø 33 bei a −0,2.
profil = [(4.25, -20.2), (16.5, -20.2), (16.5, -0.2), (15.9, -0.8), (7.5, -0.8), (7.5, 0.0)]
profil += [(4.25, 0.0), (4.25, -20.2)]
halter = Part.Face(Part.makePolygon([V(r, 0, a) for r, a in profil]))
halter = Part.Solid(Part.Shell(halter.revolve(V(0, 0, 0), V(0, 0, 1), 360).Faces))


class _Punkt:
    def __init__(self, a, r, eilgang=False, frei=False):
        self.a, self.r, self.q, self.eilgang, self.frei, self.phi = a, r, 0.0, eilgang, frei, 0.0


class _Bahn:
    def __init__(self, punkte):
        self.punkte = punkte


# Die 0,2 mm vor der Fase und dem Ringgrund (a −0,2 … 0, r 7,6 … 16,4): vor der Stirn.
vorn = _Bahn([_Punkt(8.0, 18.0, eilgang=True)] + [
    _Punkt(a, r) for a in (-0.15, -0.05) for r in np.linspace(7.6, 16.4, 30)
])  # fmt: skip
pruefe(vf.nur_vor_stirn(halter, V(*LAENGS), V(*RADIAL), vorn, 16.5), "vor der Stirn: nein")
pruefe(not vf.rundum_nichts(vorn, 16.5), "vor der Stirn: nimmt nichts")
# Die Spirale nur in der Luft (r ≥ Stange): nimmt nichts.
luft = _Bahn([_Punkt(8.0, 18.0, eilgang=True)] + [_Punkt(a, 16.52) for a in (0.0, -5.0, -15.0)])
pruefe(vf.rundum_nichts(luft, 16.5), "in der Luft: nimmt doch etwas")
# Eine Nut im Mantel (a −10 … −8, bis r 14): hinter ihr schaut eine Wand nach vorn, vor ihr liegt
# aber das Teil – Rundum.
welle_nut = Part.makeCylinder(16.5, 20.2, V(0, 0, -20.2)).cut(
    Part.makeCylinder(16.5, 2.0, V(0, 0, -10)).cut(Part.makeCylinder(14.0, 2.0, V(0, 0, -10)))
)
mantel_nut = _Bahn([_Punkt(a, r) for a in (-9.5, -9.0, -8.5) for r in (14.2, 15.0, 16.0)])
pruefe(
    not vf.nur_vor_stirn(welle_nut, V(*LAENGS), V(*RADIAL), mantel_nut, 16.5),
    "Nut im Mantel: vor der Stirn",
)

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
