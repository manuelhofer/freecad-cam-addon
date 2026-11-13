# Prüft „3D-Schruppen“ (W-006 4.2 Punkt 1) mit dem Standardfräser (Ø 12, ae 1,5, ap 25, vf 902)
# und Aufmaß 0,3. (a) Platte 60 × 60 × 10 mit einer Kuppel (Kugel R 25, Mitte (30, 30, −5): Fuß
# Ø 40 auf z 10, oben z 20), das Rohteil bis z 20: eine Lage mit vollem ap auf 10,3 und
# Zwischenlagen darüber. Im Quader nirgends ins Teil, im Eilgang nichts abgetragen; auf der Platte
# genau das Aufmaß, auf der Kuppel – senkrecht zur Kugel gemessen – mindestens das Aufmaß (bis
# auf die Spitze, wo das Rohteil endet) und höchstens Treppe plus Aufmaß (1,7). Ohne
# Zwischenlagen stünde dort viel mehr. (b) Eine Schale (Kugel R 25 in einen Block 60 × 60 × 20
# gesenkt, Grund z 10): nur Zwischenlagen, je über die Rampe, nirgends ins Teil; in der Höhlung
# bleibt unter der ebenen Stirn mehr stehen (der Bogen unter dem Fräser, 0,7 mm) – bis 2,5.
# (c) Ohne Freiformfläche ein Satz. (d) Die Operation im Job: „3D-Schruppen T1“, Art
# „schruppen3d“ mit dem Einsatz „Schruppen“. (e) Die Zwischenlagen von unten (VON_UNTEN): Kuppel,
# nur darüber, Schale, Schale + 5 – kürzer, die Treppe in derselben Grenze, nichts ins Teil, nichts
# im Eilgang, kein Eintauchen; die Vorschau höchstens 15 % neben der fertigen Zeit; die flache
# Kuppel im gröberen Raster ohne genaue Grenze sicher; zwei Kuppeln mit Spalt nicht schlechter; mit
# Materialstand (die Platte ringsum schon geräumt) kürzer als von oben und nicht unsicherer.
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

from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import job_schnittwerte as js
from camaddon import materialstand as mst
from camaddon import pruefstand as ps
from camaddon import raeumen_bahn as rb
from camaddon import restmaterial as rm
from camaddon import schruppen3d as r3op
from camaddon import schruppen3d_bahn as r3
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
werkzeug = wz.standardwerkzeug()
form = ff.scheibe(werkzeug.durchmesser / 2)
VF, EINTAUCHEN = 902.0, 270.0


def werte(oben, **weiter):
    grund = {
        "form": form,
        "zustellung": 25.0,
        "zeilenabstand": 1.5,
        "aufmass": 0.3,
        "oben": oben,
        "sicher": oben + 5.0,
        "rohteil": (0.0, 60.0, 0.0, 60.0),
        "schneidenlaenge": werkzeug.schneidenlaenge,
        "eintauchwinkel": werkzeug.eintauchwinkel,
        "vorschub": VF,
        "eintauchen": EINTAUCHEN,
    }
    grund.update(weiter)
    return rb.Raeumwerte(**grund)


def im_quader(teil, bahn, oben, start=None):
    """(Quader nach der Bahn, Sollhöhe je Zelle, x, y) – das Rohteil bis `oben`, mit `start(q)`
    vorher geformt."""
    q = rm.Quader(0, 60, 0, 60, teil.BoundBox.ZMin - 1.0, oben, 0.25)
    if start is not None:
        start(q)
    for von, nach in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        stuecke = ps._stuecke(von, nach)
        q.fahre_stuecke([s[0] for s in stuecke], [s[1] for s in stuecke], form)
    soll = hf.hoehen(vf.vernetze(teil, 0.005).netz, q.x, q.y)
    xs, ys = np.meshgrid(q.x, q.y, indexing="ij")
    return q, soll, xs, ys


def gemessen(teil, bahn, oben, start=None, rohteil=(0, 60, 0, 60)):
    k = ps.messen([ps.Bahnlauf(bahn.punkte, VF, EINTAUCHEN)], teil, rohteil, oben, form,
                  1.5, 25.0, start=start)  # fmt: skip
    return k


# --- (a) Die Kuppel ---------------------------------------------------------------------------------
platte = Part.makeBox(60, 60, 10)
kappe = Part.makeSphere(25, V(30, 30, -5)).common(Part.makeBox(60, 60, 15, V(0, 0, 10)))
teil = platte.fuse(kappe).removeSplitter()
kugel = [f"Face{i + 1}" for i, f in enumerate(teil.Faces) if isinstance(f.Surface, Part.Sphere)]
t0 = time.time()
bahn = r3.planen(teil, kugel, werte(20.0))
print(ascii(f"Kuppel: {bahn.variante} {bahn.zeit:.2f} min, {bahn.lagen} + {bahn.zwischenlagen} "
            f"Lagen, {bahn.ringe} Ringe, Rechenzeit {time.time() - t0:.1f} s, {bahn.zeiten}"))  # fmt: skip
pruefe(bahn.lagen == 1 and bahn.zwischenlagen >= 7, f"Lagen {bahn.lagen} + {bahn.zwischenlagen}")
pruefe(abs(bahn.z_min - 10.3) < 1e-6, f"tiefste Lage {bahn.z_min}")
# 6,1 min: bis P-2026-10-01-48 5,4 – die Ringe der Hauptlage bissen in die Kuppel (Eingriff bis
# 4,8 ae, siebenmal senkrecht ins Material); die Ringe um sie herum (P-2026-10-01-49) nehmen
# höchstens 1,6 ae.
pruefe(bahn.zeit < 6.5, f"Zeit {bahn.zeit:.2f} min")
k = gemessen(teil, bahn, 20.0)
print(ascii(ps.zeile(k)))
pruefe(k.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"Kuppel: ins Teil {k.einschnitt:.3f}")
pruefe(k.eingriff_max < 2.0 and k.voll <= ps.BREIT_WEG, f"Kuppel: Eingriff {ps.zeile(k)}")
pruefe(k.eilgang_abtrag <= 1e-9, f"Kuppel: im Eilgang {k.eilgang_abtrag:.1f} mm³")


def umwege_oben(b):
    """Zwei Eilgänge auf einer Höhe über allen Schnitten nacheinander, die mehr als 1 mm umgehen
    – vor dem Einfahren „von außen“ fuhr das Räumen bis 0.280.8 oben erst über den Anfang des
    Laufs, dann daneben (P-2026-10-24-28; an dieser Kuppel fünfmal)."""
    oben = max(p.z for p in b.punkte if not p.eilgang) + 0.5
    return [
        (p, q, r)
        for p, q, r in zip(b.punkte, b.punkte[1:], b.punkte[2:], strict=False)
        if q.eilgang
        and r.eilgang
        and p.z > oben
        and abs(p.z - q.z) < 1e-9
        and abs(q.z - r.z) < 1e-9
        and math.hypot(q.x - p.x, q.y - p.y) + math.hypot(r.x - q.x, r.y - q.y)
        > math.hypot(r.x - p.x, r.y - p.y) + 1.0
    ]


pruefe(not umwege_oben(bahn), f"Kuppel: {len(umwege_oben(bahn))} Eilgang-Umwege oben")
q, soll, xs, ys = im_quader(teil, bahn, 20.0)
r = np.hypot(xs - 30, ys - 30)
rest = q.h - soll
platte_frei = r > 21.0
pruefe(
    np.all(np.abs(rest[platte_frei] - 0.3) < 0.02),
    f"Platte: {rest[platte_frei].min():.3f} … {rest[platte_frei].max():.3f} statt 0,3",
)
senkrecht = np.sqrt((xs - 30) ** 2 + (ys - 30) ** 2 + (q.h + 5) ** 2) - 25.0
kuppel = r < 19.5
flanke = kuppel & (r > 4.5)  # die Spitze bis r 3,9 liegt keine 0,3 unter dem Rohteil
print(ascii(f"Kuppel senkrecht: {senkrecht[flanke].min():.3f} … {senkrecht[kuppel].max():.3f}"))
pruefe(senkrecht[flanke].min() > 0.25, f"Kuppel: nur {senkrecht[flanke].min():.3f} stehen")
pruefe(senkrecht[kuppel].max() < 1.7, f"Kuppel: Treppe {senkrecht[kuppel].max():.3f}")
# Nur über der Kuppel (Frage 6; Manuel, 2026-10-17: „oder ist rohteil schon fertig so das nurnoch
# die tasche zu fräsen ist“): Ganz gerechnet zählt die Bahn, was rings um die Kuppel steht (über Fuß
# r 20, Fräserradius und Zeilenabstand hinaus: r 27,5). Mit dem Haken gilt es als gefräst – im
# Quader ist es das (bis aufs Aufmaß): nirgends ins Teil, nichts im Eilgang, keine Helix am Rand
# (hinab daneben im Freien); die Kuppel wie oben, und kürzer (3,9 statt 6,1 min).
pruefe(
    bahn.drumherum > r3.DRUMHERUM_AB and not bahn.nur_ueber,
    f"ganz: drumherum {bahn.drumherum:.0f} mm³",
)
nur = r3.planen(teil, kugel, werte(20.0), nur_ueber=True)
print(ascii(f"Kuppel, nur darüber: {nur.zeit:.2f} min (ganz {bahn.zeit:.2f}), {nur.ringe} Ringe, "
            f"drumherum {nur.drumherum:.0f} mm³"))  # fmt: skip
pruefe(nur.nur_ueber and abs(nur.drumherum - bahn.drumherum) < 1.0, f"nur: {nur.drumherum}")
pruefe(nur.zeit < bahn.zeit, f"nur darüber nicht kürzer: {nur.zeit:.2f} min")
netz_teil = vf.vernetze(teil, 0.005).netz


def ringsum_gefraest(q):
    soll_q = hf.hoehen(netz_teil, q.x, q.y)
    gx, gy = np.meshgrid(q.x, q.y, indexing="ij")
    aussen = (np.hypot(gx - 30, gy - 30) > 26.5) & np.isfinite(soll_q)
    q.h[aussen] = np.minimum(q.h[aussen], soll_q[aussen] + 0.3)


k_nur = gemessen(teil, nur, 20.0, ringsum_gefraest)
print(ascii(ps.zeile(k_nur)))
pruefe(k_nur.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"nur darüber: ins Teil {k_nur.einschnitt:.3f}")
pruefe(k_nur.eilgang_abtrag <= 1e-9, f"nur darüber: im Eilgang {k_nur.eilgang_abtrag:.1f} mm³")
# Die Ringe vom Rand des Klotzes her (wie das Räumen mit Materialstand): am letzten Ringschritt
# 2,6 ae auf 2 mm – der Biss beim Schritt zum nächsten Ring (ein Kreisabschnitt 1,7 mm hoch, 85
# mm³ bei 9,7 Tiefe), den jeder Ringschritt hat (70 mm³ bei 1,5); das 3-mm-Fenster des Prüfstands
# sieht ihn nur hier, weil davor ein kurzer Satz steht statt eines langen, der ihn mittelt.
pruefe(
    k_nur.eingriff_max < 3.0 and k_nur.last_lang <= 20.0 and k_nur.voll <= ps.BREIT_WEG,
    f"nur darüber: {ps.zeile(k_nur)}",
)
pruefe(k_nur.rampen == 0 and k_nur.kehren == 0, f"nur darüber: {ps.zeile(k_nur)}")
q_nur, soll_nur, xs_nur, ys_nur = im_quader(teil, nur, 20.0, ringsum_gefraest)
r_nur = np.hypot(xs_nur - 30, ys_nur - 30)
rest_nur = q_nur.h - soll_nur
ring = (r_nur > 21.0) & (r_nur < 26.0)
pruefe(
    np.all(np.abs(rest_nur[ring] - 0.3) < 0.02),
    f"nur darüber, um die Kuppel: {rest_nur[ring].min():.3f} … {rest_nur[ring].max():.3f}",
)
kuppel_nur = r_nur < 19.5
senk_nur = np.sqrt((xs_nur - 30) ** 2 + (ys_nur - 30) ** 2 + (q_nur.h + 5) ** 2) - 25.0
pruefe(senk_nur[kuppel_nur].max() < 1.7, f"nur darüber: Treppe {senk_nur[kuppel_nur].max():.3f}")
ohne = r3.planen(teil, kugel, werte(20.0), zwischen=0.0)
pruefe(ohne.zwischenlagen == 0, f"ohne Zwischenlagen: {ohne.zwischenlagen}")
q0, _soll, _xs, _ys = im_quader(teil, ohne, 20.0)
senkrecht0 = np.sqrt((xs - 30) ** 2 + (ys - 30) ** 2 + (q0.h + 5) ** 2) - 25.0
pruefe(senkrecht0[kuppel].max() > 5.0, f"ohne Zwischenlagen nur {senkrecht0[kuppel].max():.2f}")
gegen = r3.planen(teil, kugel, werte(20.0, gleichlauf=False))
pruefe(abs(gegen.zeit - bahn.zeit) < 0.5, f"Gegenlauf {gegen.zeit:.2f}, Gleichlauf {bahn.zeit:.2f}")

# --- (b) Die Schale ---------------------------------------------------------------------------------
block = Part.makeBox(60, 60, 20)
schale = block.cut(Part.makeSphere(25, V(30, 30, 35))).removeSplitter()
innen = [f"Face{i + 1}" for i, f in enumerate(schale.Faces) if isinstance(f.Surface, Part.Sphere)]
bahn_s = r3.planen(schale, innen, werte(20.0))
print(ascii(f"Schale: {bahn_s.zeit:.2f} min, {bahn_s.lagen} + {bahn_s.zwischenlagen} Lagen, "
            f"{bahn_s.ringe} Ringe, {bahn_s.rampen} Rampen"))  # fmt: skip
pruefe(
    bahn_s.zwischenlagen >= 5 and bahn_s.rampen == bahn_s.zwischenlagen,
    f"Schale: {bahn_s.zwischenlagen} Zwischenlagen, {bahn_s.rampen} Rampen",
)
k = gemessen(schale, bahn_s, 20.0)
print(ascii(ps.zeile(k)))
pruefe(k.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"Schale: ins Teil {k.einschnitt:.3f}")
pruefe(k.eilgang_abtrag <= 1e-9, f"Schale: im Eilgang {k.eilgang_abtrag:.1f} mm³")
q, soll, xs, ys = im_quader(schale, bahn_s, 20.0)
r = np.hypot(xs - 30, ys - 30)
abstand = 25.0 - np.sqrt((xs - 30) ** 2 + (ys - 30) ** 2 + (q.h - 35) ** 2)  # über der Schale
mitte = r < 16.0
print(ascii(f"Schale senkrecht: {abstand[mitte].min():.3f} … {abstand[mitte].max():.3f}"))
pruefe(abstand[mitte].min() > 0.25, f"Schale: nur {abstand[mitte].min():.3f} stehen")
pruefe(abstand[mitte].max() < 2.5, f"Schale: Treppe {abstand[mitte].max():.3f}")
# Das Rohteil steht 5 mm über dem Teil: Die Lagen über dem ganzen Teil (nichts gesperrt) fahren mit –
# als eine Lage, Ringe vom Rand her. Bis 0.366.5 fielen sie aus: Der Eilgang zur ersten Lage darunter
# endete 1,9 mm im Material (217 mm³), dann ging es senkrecht mit voller Stirn hinein, und über einer
# Kuppel blieb die Säule Rohteil stehen (Sicherheitsprüfung, nachgestellt am 2026-11-13).
bahn_s5 = r3.planen(schale, innen, werte(25.0))
k5 = gemessen(schale, bahn_s5, 25.0)
print(ascii(f"Schale, Rohteil 5 darüber: {bahn_s5.zeit:.2f} min – {ps.zeile(k5)}"))
pruefe(k5.eilgang_abtrag <= 1e-9, f"Schale + 5: im Eilgang {k5.eilgang_abtrag:.1f} mm³")
# Zwei Einfahrten streifen beim Hinabfahren die Kante der Stufe darüber (je 0,1 mm³ – so auch
# schon mit 1 mm Rohteil darüber); mit voller Stirn ins Volle (225 mm³) taucht keine mehr.
pruefe(k5.eintauchungen <= 2, f"Schale + 5: {k5.eintauchungen}-mal senkrecht ins Material")
pruefe(k5.voll <= ps.BREIT_WEG, f"Schale + 5: {k5.voll:.0f} mm in voller Breite")
pruefe(k5.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"Schale + 5: ins Teil {k5.einschnitt:.3f}")
q5, _soll5, xs5, ys5 = im_quader(schale, bahn_s5, 25.0)
rand5 = (np.hypot(xs5 - 30, ys5 - 30) > 27.0) & (xs5 > 1) & (xs5 < 59) & (ys5 > 1) & (ys5 < 59)
pruefe(
    float(q5.h[rand5].max()) < 21.2,
    f"Schale + 5: über dem Rand steht noch bis {float(q5.h[rand5].max()):.2f} (Teil 20)",
)
pruefe(bahn_s5.zeit < 6.0, f"Schale + 5: {bahn_s5.zeit:.2f} min (eine Lage für die 5 mm: etwa 5)")
bahn5 = r3.planen(teil, kugel, werte(25.0))
qk, _sollk, xk, yk = im_quader(teil, bahn5, 25.0)
spitze = np.hypot(xk - 30, yk - 30) < 4.0
pruefe(
    float(qk.h[spitze].max()) < 21.5,
    f"Kuppel + 5: über der Spitze steht bis {float(qk.h[spitze].max()):.2f} (Spitze 20)",
)

# --- (e) Zwischenlagen von unten (Frage 4, VON_UNTEN) ---------------------------------------------
# Je Zwischenlage ein Streifen an der Wand mit voller Tiefe, eine Lage erst, wo die Stufe sonst
# breiter als STUFE würde: kürzer als von oben, die Treppe auf der Kuppel in derselben Grenze,
# nichts ins Teil, nichts im Eilgang, nie senkrecht ins Material, keine Rampe (hinein von der
# freien Seite).
bahn_u = r3.planen(teil, kugel, werte(20.0), von_unten=True)
k_u = gemessen(teil, bahn_u, 20.0)
print(ascii(f"Kuppel von unten: {bahn_u.zeit:.2f} min (von oben {bahn.zeit:.2f}), {bahn_u.lagen} + "
            f"{bahn_u.zwischenlagen} Lagen – {ps.zeile(k_u)}"))  # fmt: skip
pruefe(bahn_u.zeit < bahn.zeit - 0.3, f"von unten: {bahn_u.zeit:.2f} statt {bahn.zeit:.2f} min")
pruefe(k_u.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"von unten: ins Teil {k_u.einschnitt:.3f}")
pruefe(k_u.eilgang_abtrag <= 1e-9, f"von unten: im Eilgang {k_u.eilgang_abtrag:.1f} mm³")
pruefe(k_u.eintauchungen == 0 and k_u.rampen == 0, f"von unten: {ps.zeile(k_u)}")
pruefe(k_u.eingriff_max < 2.0 and k_u.voll <= ps.BREIT_WEG, f"von unten: {ps.zeile(k_u)}")
q_u, _soll_u, xs_u, ys_u = im_quader(teil, bahn_u, 20.0)
senk_u = np.sqrt((xs_u - 30) ** 2 + (ys_u - 30) ** 2 + (q_u.h + 5) ** 2) - 25.0
print(ascii(f"Kuppel von unten senkrecht: {senk_u[flanke].min():.3f} … {senk_u[kuppel].max():.3f}"))
pruefe(senk_u[flanke].min() > 0.25, f"von unten: nur {senk_u[flanke].min():.3f} stehen")
pruefe(senk_u[kuppel].max() < 1.7, f"von unten: Treppe {senk_u[kuppel].max():.3f}")
pruefe(
    np.all(np.abs((q_u.h - _soll_u)[platte_frei] - 0.3) < 0.02),
    "von unten: auf der Platte nicht 0,3",
)
# Die Vorschau des Assistenten (gröberes Raster, ohne genaue Grenze: _RUECKFALL) zeigt eine
# ähnliche Zeit (höchstens 15 % daneben) und fährt nirgends im Eilgang ins Material.
grob_u = r3.planen(teil, kugel, werte(20.0), toleranz=hf.VORSCHAU_TOLERANZ,
                   schritt=r3.VORSCHAU_SCHRITT, von_unten=True)  # fmt: skip
k_grob_u = gemessen(teil, grob_u, 20.0)
print(ascii(f"Kuppel von unten, Vorschau: {grob_u.zeit:.2f} min (fertig {bahn_u.zeit:.2f}) – "
            f"{ps.zeile(k_grob_u)}"))  # fmt: skip
pruefe(abs(grob_u.zeit - bahn_u.zeit) <= 0.15 * bahn_u.zeit, f"Vorschau {grob_u.zeit:.2f} min")
pruefe(k_grob_u.eilgang_abtrag <= 1e-9, f"Vorschau: im Eilgang {k_grob_u.eilgang_abtrag:.1f} mm³")
pruefe(k_grob_u.eintauchungen == 0, f"Vorschau: {k_grob_u.eintauchungen}-mal senkrecht")
# Die flache Kuppel (Kugel R 60 über einer Platte 80 × 80): im gröberen Raster der Operation (0,75
# und 1,0, ohne genaue Grenze) nichts im Eilgang und nicht öfter senkrecht ins Material als von
# oben – vor _RUECKFALL im Raster 1,0 2,4 mm³ im Eilgang und fünfmal senkrecht (Gegenprüfer,
# 2026-11-13); die Vorschau höchstens 15 % neben der fertigen Bahn (vorher +16 %).
roh_f = (0.0, 80.0, 0.0, 80.0)
flach = (
    Part.makeBox(80, 80, 5)
    .fuse(Part.makeSphere(60, V(40, 40, -45)).common(Part.makeBox(80, 80, 10, V(0, 0, 5))))
    .removeSplitter()
)
kugel_f = [f"Face{i + 1}" for i, f in enumerate(flach.Faces) if isinstance(f.Surface, Part.Sphere)]
for schritt in (0.75, 1.0):
    alt_f = r3.planen(flach, kugel_f, werte(15.0, rohteil=roh_f), schritt=schritt)
    neu_f = r3.planen(flach, kugel_f, werte(15.0, rohteil=roh_f), schritt=schritt, von_unten=True)
    k_alt_f = gemessen(flach, alt_f, 15.0, rohteil=roh_f)
    k_neu_f = gemessen(flach, neu_f, 15.0, rohteil=roh_f)
    print(ascii(f"Flache Kuppel, Raster {schritt}: von unten {neu_f.zeit:.2f} min (von oben "
                f"{alt_f.zeit:.2f}, {k_alt_f.eintauchungen}-mal senkrecht) – "
                f"{ps.zeile(k_neu_f)}"))  # fmt: skip
    pruefe(k_neu_f.eilgang_abtrag <= 1e-9, f"flach {schritt}: Eilgang {k_neu_f.eilgang_abtrag:.1f}")
    pruefe(
        k_neu_f.eintauchungen <= k_alt_f.eintauchungen,
        f"flach {schritt}: {k_neu_f.eintauchungen}-mal senkrecht (oben {k_alt_f.eintauchungen})",
    )
    pruefe(k_neu_f.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"flach {schritt}: {k_neu_f.einschnitt}")
    pruefe(neu_f.zeit < alt_f.zeit, f"flach {schritt}: {neu_f.zeit:.2f} statt {alt_f.zeit:.2f} min")
fertig_f = r3.planen(flach, kugel_f, werte(15.0, rohteil=roh_f), von_unten=True)
grob_f = r3.planen(flach, kugel_f, werte(15.0, rohteil=roh_f), toleranz=hf.VORSCHAU_TOLERANZ,
                   schritt=r3.VORSCHAU_SCHRITT, von_unten=True)  # fmt: skip
k_grob_f = gemessen(flach, grob_f, 15.0, rohteil=roh_f)
print(ascii(f"Flache Kuppel, Vorschau: {grob_f.zeit:.2f} min (fertig {fertig_f.zeit:.2f}) – "
            f"{ps.zeile(k_grob_f)}"))  # fmt: skip
pruefe(abs(grob_f.zeit - fertig_f.zeit) <= 0.15 * fertig_f.zeit, f"Vorschau {grob_f.zeit:.2f}")
pruefe(k_grob_f.eilgang_abtrag <= 1e-9, f"Vorschau flach: Eilgang {k_grob_f.eilgang_abtrag:.1f}")
# Zwei Kuppeln mit einem Spalt, der sich erst über der Hauptlage öffnet (_spalt): Von unten käme
# der erste Ring mitten in den vollen Spalt (6,1 statt 3,3 ae, 3,87 statt 3,48 min) – der Abschnitt
# bleibt von oben: Eingriff und Zeit nicht über dem Weg von oben.
roh_s = (0.0, 66.0, 0.0, 40.0)
zwei = Part.makeBox(66, 40, 10)
for mx in (18.0, 48.0):
    zwei = zwei.fuse(
        Part.makeSphere(18, V(mx, 20, -3)).common(Part.makeBox(66, 40, 10, V(0, 0, 10)))
    )
zwei = zwei.removeSplitter()
kugeln = [f"Face{i + 1}" for i, f in enumerate(zwei.Faces) if isinstance(f.Surface, Part.Sphere)]
alt_s = r3.planen(zwei, kugeln, werte(15.0, rohteil=roh_s))
neu_s = r3.planen(zwei, kugeln, werte(15.0, rohteil=roh_s), von_unten=True)
k_alt_s = gemessen(zwei, alt_s, 15.0, rohteil=roh_s)
k_neu_s = gemessen(zwei, neu_s, 15.0, rohteil=roh_s)
print(ascii(f"Spalt von unten: {neu_s.zeit:.2f} min (von oben {alt_s.zeit:.2f}, Eingriff bis "
            f"{k_alt_s.eingriff_max:.2f} ae) – {ps.zeile(k_neu_s)}"))  # fmt: skip
pruefe(
    k_neu_s.eingriff_max <= k_alt_s.eingriff_max + 0.05,
    f"Spalt: Eingriff {k_neu_s.eingriff_max:.2f} statt {k_alt_s.eingriff_max:.2f} ae",
)
pruefe(neu_s.zeit <= alt_s.zeit + 1e-6, f"Spalt: {neu_s.zeit:.2f} statt {alt_s.zeit:.2f} min")
# Nur über der Kuppel: wie oben, von unten.
nur_u = r3.planen(teil, kugel, werte(20.0), nur_ueber=True, von_unten=True)
k_nur_u = gemessen(teil, nur_u, 20.0, ringsum_gefraest)
print(ascii(f"Kuppel, nur darüber, von unten: {nur_u.zeit:.2f} min – {ps.zeile(k_nur_u)}"))
pruefe(nur_u.zeit < nur.zeit, f"nur darüber von unten: {nur_u.zeit:.2f} statt {nur.zeit:.2f} min")
pruefe(k_nur_u.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"nur, von unten: {k_nur_u.einschnitt:.3f}")
pruefe(k_nur_u.eilgang_abtrag <= 1e-9, f"nur, von unten: Eilgang {k_nur_u.eilgang_abtrag:.1f}")
# Mit Materialstand (MIT_STAND): Ein Räumen davor hat die Platte ringsum schon bis aufs Aufmaß
# genommen. Bis 0.370.0 liefen die Zwischenlagen dann von oben (3,42 min) – jetzt von unten: kürzer
# (2,95 min), nichts ins Teil, nichts im Eilgang, nicht öfter senkrecht und nicht breiter im
# Eingriff als von oben, der Prüfstand nicht strenger.
q_stand = rm.Quader(0, 60, 0, 60, -1.0, 20.0, mst.SCHRITT)
voll_stand = q_stand.h.copy()
ringsum_gefraest(q_stand)
stand = mst.Materialstand(q_stand, voll_stand, ["Räumen T1"], [q_stand.h < voll_stand - 1e-9])
stand_o = r3.planen(teil, kugel, werte(20.0), stand=stand)
stand_u = r3.planen(teil, kugel, werte(20.0), stand=stand, von_unten=True)
k_stand_o = gemessen(teil, stand_o, 20.0, ringsum_gefraest)
k_stand_u = gemessen(teil, stand_u, 20.0, ringsum_gefraest)
print(ascii(f"Kuppel mit Materialstand: von unten {stand_u.zeit:.2f} min (von oben "
            f"{stand_o.zeit:.2f}), {stand_u.lagen} + {stand_u.zwischenlagen} Lagen – "
            f"{ps.zeile(k_stand_u)}"))  # fmt: skip
pruefe(
    stand_u.zeit < stand_o.zeit - 0.3,
    f"Materialstand: von unten {stand_u.zeit:.2f} statt {stand_o.zeit:.2f} min",
)
pruefe(k_stand_u.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"Stand: ins Teil {k_stand_u.einschnitt}")
pruefe(k_stand_u.eilgang_abtrag <= 1e-9, f"Stand: im Eilgang {k_stand_u.eilgang_abtrag:.1f} mm³")
pruefe(
    k_stand_u.eintauchungen <= k_stand_o.eintauchungen
    and k_stand_u.eingriff_max <= k_stand_o.eingriff_max + 0.05,
    f"Stand: {ps.zeile(k_stand_u)} (von oben {ps.zeile(k_stand_o)})",
)
pruefe(
    set(ps.urteile(k_stand_u)) <= set(ps.urteile(k_stand_o)),
    f"Stand: {ps.urteile(k_stand_u)} (von oben {ps.urteile(k_stand_o)})",
)
# Die Schale (eine Höhlung: die erste Lage über die Rampe, dann je hinein vom Freien in der Mitte)
# und die Schale mit 5 mm Rohteil darüber (die unterste Lage über dem ganzen Teil nimmt alles
# darüber mit).
schale_u = r3.planen(schale, innen, werte(20.0), von_unten=True)
k_su = gemessen(schale, schale_u, 20.0)
print(ascii(f"Schale von unten: {schale_u.zeit:.2f} min (von oben {bahn_s.zeit:.2f}), "
            f"{schale_u.rampen} Rampen – {ps.zeile(k_su)}"))  # fmt: skip
pruefe(k_su.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"Schale von unten: ins Teil {k_su.einschnitt}")
pruefe(k_su.eilgang_abtrag <= 1e-9, f"Schale von unten: im Eilgang {k_su.eilgang_abtrag:.1f} mm³")
# Eine Höhlung (über der Hauptlage öffnet sich Erlaubtes ohne Verbindung zu ihrem Freien): Von
# unten ginge die erste Lage darin mit voller Tiefe über die Rampe, der erste Ring in voller Breite
# (4,4 ae) – sie bleibt bei der Reihenfolge von oben.
pruefe(
    schale_u.rampen == bahn_s.rampen and abs(schale_u.zeit - bahn_s.zeit) < 1e-6,
    f"Schale von unten: {schale_u.rampen} Rampen, {schale_u.zeit:.2f} min",
)
q_su, _s, xs_su, ys_su = im_quader(schale, schale_u, 20.0)
abst_u = 25.0 - np.sqrt((xs_su - 30) ** 2 + (ys_su - 30) ** 2 + (q_su.h - 35) ** 2)
mitte_u = np.hypot(xs_su - 30, ys_su - 30) < 16.0
print(
    ascii(f"Schale von unten senkrecht: {abst_u[mitte_u].min():.3f} … {abst_u[mitte_u].max():.3f}")
)
pruefe(abst_u[mitte_u].min() > 0.25, f"Schale von unten: nur {abst_u[mitte_u].min():.3f}")
pruefe(abst_u[mitte_u].max() < 2.5, f"Schale von unten: Treppe {abst_u[mitte_u].max():.3f}")
schale5_u = r3.planen(schale, innen, werte(25.0), von_unten=True)
k5u = gemessen(schale, schale5_u, 25.0)
print(ascii(f"Schale + 5 von unten: {schale5_u.zeit:.2f} min – {ps.zeile(k5u)}"))
pruefe(k5u.eilgang_abtrag <= 1e-9, f"Schale + 5 von unten: im Eilgang {k5u.eilgang_abtrag:.1f}")
pruefe(k5u.eintauchungen <= 2, f"Schale + 5 von unten: {k5u.eintauchungen}-mal senkrecht")
pruefe(k5u.einschnitt > -ps.EINSCHNITT_ZULAESSIG, f"Schale + 5 von unten: {k5u.einschnitt:.3f}")
q5u, _s5, xs5u, ys5u = im_quader(schale, schale5_u, 25.0)
rand5u = (
    (np.hypot(xs5u - 30, ys5u - 30) > 27.0) & (xs5u > 1) & (xs5u < 59) & (ys5u > 1) & (ys5u < 59)
)
pruefe(float(q5u.h[rand5u].max()) < 21.2, f"Schale + 5 von unten: {float(q5u.h[rand5u].max()):.2f}")
pruefe(schale5_u.zeit < 6.0, f"Schale + 5 von unten: {schale5_u.zeit:.2f} min")
# Dünne Wände ohne genaue Grenze: ein Ring mit 1,5 mm Wand und eine Spitze. Der vorsichtige Weg von
# unten brauchte im Raster 1,0 11,3 statt 5,4 min (74 Rampen, 52 % des Vorschubwegs in der Luft –
# Gegenprüfer, zweite Runde). Ohne genaue Grenze gilt deshalb die schnellere der beiden
# Reihenfolgen: nie langsamer als von oben, und der Prüfstand hat nichts auszusetzen.
ring_r = Part.makeCone(20, 19, 15, V(30, 30, 5)).cut(Part.makeCone(18.5, 18, 15.01, V(30, 30, 5)))
rippe = (
    Part.makeBox(60, 60, 5)
    .fuse(ring_r)
    .fuse(Part.makeCone(2.5, 0.5, 15, V(30, 30, 5)))
    .removeSplitter()
)
kegel_r = [f"Face{i + 1}" for i, f in enumerate(rippe.Faces) if isinstance(f.Surface, Part.Cone)]
for schritt_r in (1.0,):
    oben_r = r3.planen(rippe, kegel_r, werte(20.0), schritt=schritt_r)
    unten_r = r3.planen(rippe, kegel_r, werte(20.0), schritt=schritt_r, von_unten=True)
    k_r = gemessen(rippe, unten_r, 20.0)
    print(ascii(f"Rippe, Raster {schritt_r}: von unten {unten_r.zeit:.2f} min (von oben "
                f"{oben_r.zeit:.2f}) – {ps.zeile(k_r)}"))  # fmt: skip
    pruefe(
        unten_r.zeit <= oben_r.zeit + 1e-6,
        f"Rippe, Raster {schritt_r}: von unten {unten_r.zeit:.2f} statt {oben_r.zeit:.2f} min",
    )
    pruefe(k_r.eilgang_abtrag <= 1e-9, f"Rippe: im Eilgang {k_r.eilgang_abtrag:.1f} mm³")
    pruefe(k_r.luftanteil <= ps.LUFT_ZULAESSIG, f"Rippe: {k_r.luftanteil * 100:.0f} % Luft")

# --- (c) Ohne Freiformfläche ----------------------------------------------------------------------
andere = [f"Face{i + 1}" for i in range(len(teil.Faces)) if f"Face{i + 1}" not in kugel]
try:
    r3.planen(teil, andere, werte(20.0))
except ValueError as grund:
    pruefe("Keine Freiformfläche" in str(grund), f"ohne Freiform: {grund}")
else:
    pruefe(False, "ohne Freiform: kein Satz")

# --- (d) Die Operation im Job ---------------------------------------------------------------------
import Path.Main.Job as PathJob

user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([werkzeug]))
doc = FreeCAD.newDocument("Kuppel")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
einsatz = next(e for e in werkzeug.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
tc = js.controller_ohne_transaktion(doc, job, werkzeug, einsatz)
doc.recompute()
op = r3op.lege_an(job, tc, 25.0, 1.5, 0.3, flaechen=kugel)
doc.recompute()
pruefe(op.Label == "3D-Schruppen T1", f"Name {op.Label}")
pruefe(op.ZwischenlagenVonUnten, "neu angelegt: Zwischenlagen nicht von unten")
pruefe(op.Lagen == 1 and op.Zwischen >= 7, f"Operation: {op.Lagen} + {op.Zwischen} Lagen")
pruefe(abs(float(op.FinalDepth) - 10.3) < 1e-6, f"Endtiefe {float(op.FinalDepth)}")
pruefe(js.operationsart(op) == "schruppen3d", f"Art {js.operationsart(op)}")
print(ascii(f"Operation: {len(op.Path.Commands)} Befehle"))

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
