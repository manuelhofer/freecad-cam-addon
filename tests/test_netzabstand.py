# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Netzschranke (netzabstand, Spezifikation Strategien 16.5 Hebel 2): Punkte und Strecken
gegen das Netz eines Teils mit Tasche, Zapfen und Kugel – nie weiter als der wahre Abstand
(OpenCascade), nahe der Oberfläche höchstens um die Vernetzungstoleranz zu klein; die Kapseln
eines Werkzeugs (kollision.werkzeugkapseln) enthalten seine Körper. Sekunden."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import FreeCAD
import numpy as np
import Part

from camaddon import halter as hl
from camaddon import kollision as kb
from camaddon import netzabstand as na
from camaddon import reichweite as rw

rng = np.random.default_rng(1)
form = Part.makeBox(100, 60, 20).cut(Part.makeBox(40, 30, 15, FreeCAD.Vector(30, 15, 5)))
form = form.fuse(Part.makeCylinder(8, 30, FreeCAD.Vector(85, 45, 20)))
form = form.fuse(Part.makeSphere(10, FreeCAD.Vector(15, 45, 20))).removeSplitter()
TOLERANZ = 0.02
netz = na.Netz(form, toleranz=TOLERANZ)
assert len(netz.ecken) > 1000 and netz.zelle >= na.ZELLE_MINDESTENS


def innen(p):
    return form.isInside(FreeCAD.Vector(*p), 1e-6, True)


# Punkte außerhalb: Schranke ≤ wahr, nahe der Oberfläche um höchstens 2 · Toleranz kleiner.
punkte = rng.uniform([-10, -10, -10], [110, 70, 60], size=(400, 3))
punkte = np.array([p for p in punkte if not innen(p)])
schranke = netz.abstand(punkte)
wahr = np.array([Part.Vertex(FreeCAD.Vector(*p)).distToShape(form)[0] for p in punkte])
assert np.all(schranke <= wahr + 1e-9), float((schranke - wahr).max())
nah = wahr < netz.zelle - 2 * TOLERANZ
assert nah.sum() > 20
assert np.all(schranke[nah] >= wahr[nah] - 2 * TOLERANZ), float((wahr - schranke)[nah].max())
# Weit weg sagt das Netz „mindestens eine Zelle“.
fern = wahr > netz.zelle
assert np.allclose(schranke[fern], netz.zelle - TOLERANZ)

# Strecken (Kapseln ohne Radius): dasselbe; eine Strecke mit einem Ende im Teil schneidet die
# Oberfläche – Schranke ≤ 0. Beide Enden im Teil sieht ein Netz nicht (Doku), ausgelassen.
von = rng.uniform([-10, -10, -5], [110, 70, 60], size=(300, 3))
richtung = rng.normal(size=(300, 3))
richtung /= np.linalg.norm(richtung, axis=1)[:, None]
nach = von + richtung * rng.uniform(0.0, 30.0, size=(300, 1))
nach[:20] = von[:20]  # Punkte als Strecken der Länge 0
behalten = np.array([not (innen(a) and innen(b)) for a, b in zip(von, nach, strict=True)])
von, nach = von[behalten], nach[behalten]
schranke = netz.kapseln(von, nach)
wahr = []
for a, b in zip(von, nach, strict=True):
    if innen(a) or innen(b):
        wahr.append(0.0)
    elif np.allclose(a, b):
        wahr.append(Part.Vertex(FreeCAD.Vector(*a)).distToShape(form)[0])
    else:
        strecke = Part.LineSegment(FreeCAD.Vector(*a), FreeCAD.Vector(*b)).toShape()
        wahr.append(strecke.distToShape(form)[0])
wahr = np.array(wahr)
assert np.all(schranke <= wahr + 1e-9), float((schranke - wahr).max())
nah = wahr < netz.zelle - 2 * TOLERANZ
assert nah.sum() > 30
assert np.all(schranke[nah] >= wahr[nah] - 2 * TOLERANZ), float((wahr - schranke)[nah].max())

# Die Kapseln eines Kugelfräsers (Spitze 110 mm unter der Spindelnase, Halter 70 mm lang)
# mit Halter enthalten seine Körper: jeder Punkt der Form liegt
# in einer Kapsel seiner Art (Abstand zur Strecke ≤ Radius).
masse = rw.Werkzeugmasse(
    durchmesser=6.0, schneide=10.0, hals_d=5.0, hals_laenge=8.0, schaft=6.0, gesamt=60.0
)
from camaddon import fraeserform as ff

masse.stirn = ff.kugel(3.0)
h = hl.aus_vorlage("er25")
kapseln = kb.werkzeugkapseln(masse, 110.0, h)
assert set(kapseln) >= {kb.SCHNEIDE, kb.KERN, kb.HALS, kb.SCHAFT, kb.HALTER}, kapseln
assert kapseln[kb.KERN][0][2] == kapseln[kb.SCHNEIDE][0][2] - kb.EINDRINGEN
assert not kapseln[kb.KERN][0][3] and kapseln[kb.SCHAFT][0][3]  # Kugel nicht flach, Schaft flach


def enthalten(masse, laenge, halter):
    """Jeder Körper aus werkzeugkoerper() liegt in den Kapseln seiner Art."""
    kapseln = kb.werkzeugkapseln(masse, laenge, halter)
    for art, koerper in kb.werkzeugkoerper(masse, laenge, halter, mit_kern=True):
        strecken = kapseln[art]
        ecken, _ = koerper.tessellate(0.05)
        p = np.array([(v.x, v.y, v.z) for v in ecken])
        drin = np.zeros(len(p), dtype=bool)
        for p0, p1, r, _flach in strecken:
            a, b = np.array(p0), np.array(p1)
            d = na.segment_segment_abstand(
                p, p, np.broadcast_to(a, p.shape), np.broadcast_to(b, p.shape)
            )
            drin |= d <= r + 1e-6
        assert drin.all(), (art, p[~drin][0] if (~drin).any() else None)


enthalten(masse, 110.0, h)
# Ohne Kugel: Schneide und Kern als Zylinder, ohne Halter bis zur Gesamtlänge.
flach = rw.Werkzeugmasse(
    durchmesser=10.0, schneide=20.0, hals_d=0, hals_laenge=0, schaft=10.0, gesamt=70.0
)
k2 = kb.werkzeugkapseln(flach, 60.0, None)
assert k2[kb.SCHNEIDE] == (((0.0, 0.0, -60.0), (0.0, 0.0, -40.0), 5.0, True),) and k2[
    kb.SCHAFT
] == (
    ((0.0, 0.0, -40.0), (0.0, 0.0, 0.0), 5.0, True),
)
assert k2[kb.KERN] == (
    ((0.0, 0.0, -60.0 + kb.EINDRINGEN), (0.0, 0.0, -40.0), 5.0 - kb.EINDRINGEN, True),
)
# Gewinkelt (P-2026-10-10-59): Werkzeug und Abschnitte gekippt wie die Körper, der Kopf längs der
# Aufnahmeachse – auch so liegt jeder Körper in seinen Kapseln (Manuels „VDI40 angetrieben
# radial“: 90°).
gewinkelt = hl.aus_vorlage("er25")
gewinkelt.richtung = hl.GEWINKELT
gewinkelt.winkel, gewinkelt.versatz, gewinkelt.kopf_d = 90.0, 70.0, 70.0
k3 = kb.werkzeugkapseln(flach, 110.0, gewinkelt)
assert set(k3) >= {kb.SCHNEIDE, kb.KERN, kb.SCHAFT, kb.HALTER}, k3
enthalten(flach, 110.0, gewinkelt)
enthalten(masse, 110.0, gewinkelt)
# Flacher Zylinder über dem Taschenboden (z = 5): Kern r 2,45 mit der Stirn 0,05 darüber – die
# Kapsel allein sagt −2,4, mit der Stirnebene 0,05 (minus Toleranz); die Kugel bleibt bei der Kapsel.
von = np.array([[50.0, 30.0, 5.05]])
nach = np.array([[50.0, 30.0, 15.05]])
r = np.array([2.45])
kapsel = netz.kapseln(von, nach, 5.0, r, np.array([False]))[0]
zylinder = netz.kapseln(von, nach, 5.0, r, np.array([True]))[0]
assert kapsel < 0 and abs(zylinder - (0.05 - TOLERANZ)) < 1e-6, (kapsel, zylinder)
# Ein Zylinder neben der Taschenwand (x = 30): die Stirnebene hilft nicht, die Kapsel gilt.
von = np.array([[32.5, 30.0, 8.0]])
nach = np.array([[32.5, 30.0, 18.0]])
wand = netz.kapseln(von, nach, 5.0, np.array([2.0]), np.array([True]))[0]
assert abs(wand - (0.5 - TOLERANZ)) < 2 * TOLERANZ, wand
print("OK", pathlib.Path(__file__).name)
