# Prüft die Eilgänge ALLER 4-Achs-Bahnen gegen Teil, Schutz und stehendes Rohteil (nach B-038 für
# „Plan indexiert“ nun auch Rundum schruppen, schlichten, entgraten und die Querbohrung; Manuel: ein
# Eilgang nie im oder dicht am Material, im Freien schnell).
#
# An der Beispielmaschine „3-Achs-Fräse mit 4. Achse“ (A längs X): Welle Ø 36 hinten, Ø 30 vorn
# (Schulter), oben eine Abflachung, unten eine Mantelnut über 120°, im dünnen Teil eine Querbohrung
# Ø 8 mit Spitze – in der Stange Ø 40, mit und ohne Reitstock; dazu Ø 50/56 in der Stange Ø 60 mit
# Reitstock. Je Job Rundum schruppen (T1 Ø 12), Plan indexiert auf Abflachung und Mantelnut, die
# Querbohrung gefräst (T4 Ø 6) und gebohrt (T5 Bohrer Ø 8), Rundum schlichten (T2 Kugel Ø 6),
# Rundum entgraten an der Abflachung (T3 Fasenfräser Ø 8). Gemessen wird der Weg JEDES Eilgangs
# (nicht nur sein Ende), die Bahnen der Reihe nach:
# - gegen das Material, das dann steht (restmaterial.Stange, die Vorschübe davor abgefahren), und
#   gegen das Teil mit dem Schutz vor dem Reitstock und dem Futter (das Teil im Raster der Stange):
#   der Fräser um den Sicherheitsabstand größer, die Spitze um ihn tiefer – nimmt er etwas weg,
#   fehlt der Abstand;
# - beim Entgraten (der Kegel des Fasenfräsers an der Rundung neben der Kante – dort ist das Raster
#   um bis 0,12 mm vorsichtiger als das Teil) der wahre Abstand des Fräsers (OpenCascade) zum Teil
#   und zum Schutzzylinder vor der Stange.
# Die Funde der eigenen Messung (eilgang4), bis 0.379.2:
# - Mit Reitstock lag die sichere Höhe an der Stange Ø 40 auf 20 + 2 = 22, der Schutz (Pinole
#   r 17,5 + Abstand zum Futter 5) auf 22,5: Schruppen, Schlichten, Entgraten und die Anfahrt der
#   Querbohrung fuhren im Eilgang durch ihn (2,45 mm zu nah).
# - An der Stange Ø 60 tauchten Schruppen und Schlichten vor der Stirn im Eilgang bis auf den
#   Schutz (1,6 bzw. 1,9 mm zu nah).
# - Entgraten tauchte im Eilgang bis den Sicherheitsabstand über die Spitze IN der Kante (um die
#   Fasenbreite tiefer) – die Flanke des Kegels kam der Rundung daneben 0,24 mm zu nah, wo die
#   Mantelnut die Abflachung kreuzt 0,92 mm.
# Dazu: Ohne Reitstock bleibt die sichere Höhe auf der Stange (vierachs_bahn.sicher_radius).
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

from camaddon import beispielmaschine as bm
from camaddon import fraeserform as ff
from camaddon import job_schnittwerte as js
from camaddon import reitstock as rs
from camaddon import restmaterial as rm
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_achsen as va
from camaddon import vierachs_bahn as vb
from camaddon import vierachs_entgratbahn as ve
from camaddon import vierachs_entgraten as vent
from camaddon import vierachs_huelle as vh
from camaddon import vierachs_operation as vo
from camaddon import vierachs_plan as vplan
from camaddon import vierachs_planbahn as vp
from camaddon import vierachs_rohteil as vr
from camaddon import vierachs_schlichten as vs
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
V = FreeCAD.Vector
SPIEL = 0.05  # mm – so viel darf einem Eilgang am Abstand fehlen (Raster, Vernetzung)

schaft = wz.Werkzeug(nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=30)
schaft.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=120, fz=0.05)]
kugel = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)
kugel.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=6, vc=150, fz=0.04)]
fase = wz.Werkzeug(
    nummer=3, art=wz.FASENFRAESER, durchmesser=8, schneiden=2, spitzenwinkel=90, spitzen_d=1
)
fase.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=100, fz=0.03)]
klein = wz.Werkzeug(nummer=4, durchmesser=6, schneiden=3, schneidenlaenge=20)
klein.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=2.4, ap=2, vc=120, fz=0.03)]
bohrer = wz.Werkzeug(nummer=5, art=wz.BOHRER, durchmesser=8.0, spitzenwinkel=118.0)
bohrer.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=60, fz=0.1)]
WERKZEUGE = (schaft, kugel, fase, klein, bohrer)
ue.uebergeben(wz.Bibliothek(list(WERKZEUGE)))


def welle(r_hinten, r_vorn, flach_z, nut_r, tief, laenge=100.0, schulter=60.0):
    """Längs X, die Stirn bei x = laenge: hinten r_hinten mit der Abflachung oben (z = flach_z,
    x 10 … schulter − 10) und der Mantelnut unten (210° … 330°, 8 breit, Grund nut_r), vorn r_vorn
    mit der Querbohrung Ø 8 aus −Y, `tief` tief, unten die Spitze 118°."""
    f = Part.makeCylinder(r_hinten, schulter, V(), V(1, 0, 0)).fuse(
        Part.makeCylinder(r_vorn, laenge - schulter, V(schulter, 0, 0), V(1, 0, 0))
    )
    f = f.cut(Part.makeBox(schulter - 20, 3 * r_hinten, r_hinten, V(10, -1.5 * r_hinten, flach_z)))
    nut = Part.makeCylinder(r_hinten + 1, 8, V(schulter - 18, 0, 0), V(1, 0, 0), 120)
    nut = nut.cut(Part.makeCylinder(nut_r, 8, V(schulter - 18, 0, 0), V(1, 0, 0)))
    nut.rotate(V(), V(1, 0, 0), 210)
    f = f.cut(nut)
    xb, lang, boden = schulter + 20, 4.0 / math.tan(math.radians(59.0)), -(r_vorn - tief)
    f = f.cut(Part.makeCylinder(4, r_vorn + 2 + boden, V(xb, -(r_vorn + 2), 0), V(0, 1, 0)))
    return f.cut(Part.makeCone(4, 0, lang, V(xb, boden, 0), V(0, 1, 0))).removeSplitter()


def flaechen_von(form, nut_r):
    flach = bohr = nut = None
    for i, f in enumerate(form.Faces):
        if vr.ist_eben(f) and abs(vr.aussennormale(f).z - 1.0) < 1e-6:
            flach = f"Face{i + 1}"
        elif isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 4.0) < 1e-6:
            bohr = f"Face{i + 1}"
        elif isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - nut_r) < 1e-6:
            nut = f"Face{i + 1}"
    return flach, bohr, nut


# --- Die Bahnen mitschreiben, wie die Operationen sie rechnen ------------------------------------
bahnen = []  # (Art, Bahn, Netz, Werte)


def mitschreiben(modul, name, art):
    echt = getattr(modul, name)

    def neu(netz, laengs, radial, werte, *args, **kw):
        bahn = echt(netz, laengs, radial, werte, *args, **kw)
        bahnen.append((art, bahn, netz, werte))
        return bahn

    setattr(modul, name, neu)
    return echt


echte = {
    (vb, "schruppen"): mitschreiben(vb, "schruppen", "schruppen"),
    (vb, "schlichten"): mitschreiben(vb, "schlichten", "schlichten"),
    (ve, "entgraten"): mitschreiben(ve, "entgraten", "entgraten"),
    (vp, "planen"): mitschreiben(vp, "planen", "plan"),
}


def form_von(w):
    form = getattr(w, "form", None)
    return form if form is not None else ff.scheibe(float(w.fraeser_radius))


class Welt:
    """Das Material, wie es nach den Bahnen davor steht, und das Teil mit dem Schutz vor dem
    Reitstock und dem Futter – im Raster der Stange (restmaterial.Stange)."""

    def __init__(self, form_teil, job, laengs, radial, w):
        self.w = w
        a_vorn, a_futter = float(w.a_stange_vorne), float(w.a_futter)
        anzahl = max(2, int(math.ceil((a_vorn - a_futter) / rm.SCHRITT_A)))
        self.material = rm.Stange(float(w.stange_radius), a_vorn - anzahl * rm.SCHRITT_A, a_vorn)
        netz = rs.mit_schutz(vh.vernetze(form_teil, 0.01), job, laengs, float(w.abstand_futter))
        self.teil = rm.Stange(float(w.stange_radius) + 80.0, self.material.a[0] - 20, a_vorn + 60)
        self.teil.r = rm.teilradien(netz, laengs, radial, self.teil).astype(float)
        futter = self.teil.a <= a_futter
        self.teil.r[futter] = np.maximum(self.teil.r[futter], float(w.stange_radius) + 30.0)


def _eindringen(stange, von, nach, gross, s):
    vorher = stange.r.copy()
    v, n = np.array(von, dtype=float), np.array(nach, dtype=float)
    v[1] -= s
    n[1] -= s
    stange.fahre_stuecke(v[None, :], n[None, :], gross)
    weg = vorher - stange.r
    stange.r = vorher
    weg = weg[np.isfinite(weg)]
    return float(weg.max()) if weg.size else 0.0


def im_raster(welt, punkte, form, sicherheit, teil_auch=True):
    """(mm, Punkt): wie weit der um den Sicherheitsabstand größere Fräser auf dem Weg eines
    Eilgangs höchstens ins Material (oder ins Teil) eindränge; die Vorschübe tragen ab."""
    s = float(sicherheit) - SPIEL
    gross = form.mit_aufmass(s)
    schlimmst, vorschub = (0.0, None), []

    def abtragen():
        if vorschub:
            welt.material.fahre_stuecke(
                np.array([x[0] for x in vorschub]), np.array([x[1] for x in vorschub]), form
            )
            vorschub.clear()

    for k in range(1, len(punkte)):
        p0, p1 = punkte[k - 1], punkte[k]
        von, nach = (p0.a, p0.r, p0.phi, p0.q), (p1.a, p1.r, p1.phi, p1.q)
        if not p1.eilgang:
            vorschub.append((von, nach))
            continue
        abtragen()
        quer = math.hypot(p1.a - p0.a, p1.q - p0.q) + abs(p1.phi - p0.phi)
        if quer > 1e-6 or p1.r < p0.r - 1e-9:  # senkrecht hinauf ist frei
            tief = _eindringen(welt.material, von, nach, gross, s)
            if teil_auch:
                tief = max(tief, _eindringen(welt.teil, von, nach, gross, s))
            if tief > schlimmst[0]:
                schlimmst = (tief, k)
        welt.material.fahre_stuecke(np.array([von]), np.array([nach]), form)
    abtragen()
    return schlimmst


def koerper(form, laenge=40.0, n=24):
    """Der Fräser als Körper, die Spitze im Ursprung, die Achse längs +Z."""
    rho = np.linspace(0.0, float(form.radius), n)
    ecken = [V(0, 0, 0)] + [V(float(x), 0, float(form.hoehe(float(x)))) for x in rho[1:]]
    ecken += [V(float(form.radius), 0, laenge), V(0, 0, laenge), V(0, 0, 0)]
    return Part.Face(Part.makePolygon(ecken)).revolve(V(), V(0, 0, 1), 360.0)


def genau(punkte, form, ziel, laengs, radial, schritt=2.0):
    """(mm, Punkt): der kleinste wahre Abstand (OpenCascade) des Fräsers zu `ziel` auf dem Weg
    der Eilgänge – alle `schritt` mm eine Stelle und das Ende; senkrecht hinauf zählt nicht."""
    l_, u_, v_ = vh.rahmen(laengs, radial)
    werkzeug = koerper(form)
    naechster = (math.inf, None)
    for k in range(1, len(punkte)):
        p0, p1 = punkte[k - 1], punkte[k]
        if not p1.eilgang:
            continue
        quer = abs(p1.a - p0.a) + abs(p1.q - p0.q) + abs(p1.phi - p0.phi)
        if quer < 1e-9 and p1.r >= p0.r:
            continue
        bogen = math.radians(abs(p1.phi - p0.phi)) * max(p0.r, p1.r)
        weg = math.hypot(p1.a - p0.a, p1.q - p0.q, p1.r - p0.r, bogen)
        for t in np.linspace(0.0, 1.0, max(2, int(math.ceil(weg / schritt)) + 1))[1:]:
            phi = math.radians(p0.phi + t * (p1.phi - p0.phi))
            d = math.cos(phi) * u_ + math.sin(phi) * v_
            e = -math.sin(phi) * u_ + math.cos(phi) * v_
            spitze = (
                (p0.a + t * (p1.a - p0.a)) * l_
                + (p0.r + t * (p1.r - p0.r)) * d
                + (p0.q + t * (p1.q - p0.q)) * e
            )
            stueck = werkzeug.copy()
            stueck.Placement = FreeCAD.Placement(V(*spitze), FreeCAD.Rotation(V(0, 0, 1), V(*d)))
            naechster = min(naechster, (float(stueck.distToShape(ziel)[0]), k))
    return naechster


asm, ma = bm.fraese_vierte_achse()
achse = va.von_maschine(asm, ma)[0]
laengs, radial = tuple(achse.laengs), tuple(va.radial(achse))
FAELLE = (
    # Name, (r hinten, r vorn, Abflachung z, Grund der Mantelnut, Tiefe der Bohrung), Stange Ø,
    # mit Reitstock
    ("Ø 40", (18.0, 15.0, 14.0, 16.0, 6.0), 40.0, False),
    ("Ø 40", (18.0, 15.0, 14.0, 16.0, 6.0), 40.0, True),
    ("Ø 60", (28.0, 25.0, 24.0, 26.0, 8.0), 60.0, True),
)
for name, masse, d_stange, mit in FAELLE:
    form_teil = welle(*masse)
    doc = FreeCAD.newDocument("Eilgang")
    teil = doc.addObject("Part::Feature", "Teil")
    teil.Shape = form_teil
    doc.recompute()
    stirn = next(
        f
        for f in form_teil.Faces
        if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
    )
    lage = vr.berechne(form_teil, stirn, achse, durchmesser=d_stange)
    stange = vr.Stange(d_stange, frei_hinten=20.0, reitstock=mit)
    job = vr.richte_ein(doc, teil, lage, stange, achse)
    tcs = [js.controller_ohne_transaktion(doc, job, w, w.einsaetze(wz.ALLE)[0]) for w in WERKZEUGE]
    doc.recompute()
    flach, bohr, mnut = flaechen_von(form_teil, masse[3])
    pruefe(flach and bohr and mnut, f"{name}: Flächen {flach}, {bohr}, {mnut}")
    bahnen.clear()
    ops = [
        vo.lege_an(job, tcs[0], achse, 5.0, 4.8, 0.3),
        vplan.lege_an(job, tcs[3], achse, 2.0, 4.0, aufmass=0.0, flaechen=[flach, mnut]),
        vplan.lege_an(job, tcs[3], achse, 2.0, 4.0, aufmass=0.0, flaechen=[bohr]),
        vplan.lege_an(job, tcs[4], achse, 2.0, 4.0, aufmass=0.0, flaechen=[bohr]),
        vs.lege_an(job, tcs[1], achse, schrittweite=0.3),
        vent.lege_an(job, tcs[2], achse, breite=0.3, flaechen=[flach]),
    ]
    for op in ops:
        op.recompute()
        pruefe(len(op.Path.Commands) > 5, f"{name}, {op.Label}: keine Bahn")
    arten = [art for art, *_rest in bahnen]
    pruefe(
        arten == ["schruppen", "plan", "plan", "plan", "schlichten", "entgraten"],
        f"{name}: Bahnen {arten}",
    )
    modell = vr.modell(job).Shape
    welt = Welt(modell, job, laengs, radial, bahnen[0][3])
    a_stange = float(bahnen[0][3].a_stange_vorne)
    ziel = modell
    schutz = rs.schutz_radius(float(bahnen[0][3].abstand_futter))
    if mit:  # der Schutz vor der Stirn der Stange, wie reitstock.mit_schutz ihn baut
        zylinder = Part.makeCylinder(schutz, rs.SCHUTZ_VORN, V(a_stange, 0, 0), V(1, 0, 0))
        ziel = Part.makeCompound([modell, zylinder])
    for art, bahn, _netz, w in bahnen:
        form = form_von(w)
        vorn = [p.r for p in bahn.punkte if p.eilgang and 0 < p.a - a_stange < rs.SCHUTZ_VORN]
        sicher = min(vorn, default=math.inf)
        if art == "entgraten":
            tief = im_raster(welt, bahn.punkte, form, w.sicherheit, teil_auch=False)
            nah = genau(bahn.punkte, form, ziel, laengs, radial)
            pruefe(
                nah[0] >= float(w.sicherheit) - SPIEL,
                f"{name}, Reitstock {mit}, {art}: Eilgang {nah[0]:.3f} mm am Teil (Punkt {nah[1]})",
            )
        else:
            tief = im_raster(welt, bahn.punkte, form, w.sicherheit)
            nah = (math.nan, None)
        zeit = vb.dauer(bahn, 1000.0, 300.0)
        print(
            ascii(
                f"{name}, Reitstock {mit}, {art} R {form.radius:g}: Eilgang zu nah {tief[0]:.3f} mm"
                f" (Punkt {tief[1]}), wahrer Abstand {nah[0]:.3f} (Punkt {nah[1]}); vor der Stange "
                f"im Eilgang ab r {sicher:.2f}; Vorschub {zeit:.3f} min (F 1000)"
            )
        )
        pruefe(
            tief[0] <= SPIEL,
            f"{name}, Reitstock {mit}, {art}: Eilgang {tief[0]:.3f} mm zu nah (Punkt {tief[1]})",
        )
        if mit:  # vor der Stange über dem Schutz
            pruefe(
                sicher >= schutz + float(w.sicherheit) - SPIEL,
                f"{name}, {art}: vor der Stange im Eilgang auf r {sicher:.2f}, Schutz {schutz}",
            )
    FreeCAD.closeDocument(doc.Name)
for (modul, name), echt in echte.items():
    setattr(modul, name, echt)
FreeCAD.closeDocument(asm.Document.Name)
print(ascii(f"Befunde der Bahnen: {fehler}"))

# --- Die sichere Höhe (vierachs_bahn.sicher_radius, mit_netz_hoehe) -------------------------------
# Ohne Reitstock bleibt sie auf der Stange; steht das Netz höher (der Schutz r 22,5 vor der Stange
# Ø 40), liegt sie den Sicherheitsabstand darüber.
w40 = vb.Schruppwerte(
    fraeser_radius=6.0, stange_radius=20.0, zustellung=5.0, steigung=4.8, aufmass=0.3,
    a_stange_vorne=1.0, a_futter=-100.0,
)  # fmt: skip
welle_netz = vh.vernetze(Part.makeCylinder(15.0, 100.0, V(-100, 0, 0), V(1, 0, 0)))
gleich = vb.mit_netz_hoehe(w40, welle_netz, laengs, radial)
pruefe(
    gleich is w40 and vb.sicher_radius(gleich) == 22.0, f"ohne Schutz: {vb.sicher_radius(gleich)}"
)
hoch = vh.vernetze(Part.makeCylinder(22.5, 30.0, V(1, 0, 0), V(1, 0, 0)))
mit_hoch = vb.mit_netz_hoehe(w40, hoch, laengs, radial)
pruefe(
    abs(mit_hoch.netz_hoehe - 22.5) < 1e-6 and abs(vb.sicher_radius(mit_hoch) - 24.5) < 1e-6,
    f"über dem Schutz: {mit_hoch.netz_hoehe}, sicher {vb.sicher_radius(mit_hoch)}",
)
pruefe(
    vb.mit_netz_hoehe(vp.Planwerte(form=ff.scheibe(3), stange_radius=20.0, zustellung=2.0,
                                   zeilenabstand=4.0, aufmass=0.0, a_stange_vorne=1.0,
                                   a_futter=-100.0), hoch, laengs, radial).netz_hoehe > 22.4,
    "Planwerte ohne Netzhöhe",
)  # fmt: skip
# Die Prüfung der Eilgänge gegen das Netz: hinab über den Schutz bis 24,5 im Eilgang, der Rest im
# Vorschub; auf der sicheren Höhe fragt sie nichts (oben).
roh = [vb.Punkt(True, 10.0, 30.0, 0.0), vb.Punkt(True, 10.0, 23.0, 0.0)]
gesichert, anzahl = vb.eilgaenge_am_teil(roh, hoch, laengs, radial, ff.scheibe(6.0), 2.0)
pruefe(
    anzahl == 1
    and len(gesichert) == 3
    and gesichert[1].eilgang
    and abs(gesichert[1].r - (22.5 + 2.0 - vb.EILGANG_SPIEL)) < 0.02
    and not gesichert[2].eilgang
    and gesichert[2].eintauchen,
    f"hinab über dem Schutz: {gesichert}",
)
_tiefst, oben = vb.eilgang_tiefst(hoch, laengs, radial, ff.scheibe(6.0), 2.0)
pruefe(abs(oben - (22.5 + 2.0 - vb.EILGANG_SPIEL)) < 1e-6, f"oben {oben}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
