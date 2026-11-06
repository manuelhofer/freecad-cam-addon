# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prüft flanke_frei: Die Wege durch die Luft gehen schnell, im Material bleibt es langsam, die Wand
selbst bleibt immer im Vorschub. Aufruf: freecadcmd tests/test_flanke_frei.py"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np  # noqa: E402

from camaddon import bahn as bn  # noqa: E402
from camaddon import flanke_frei as fr  # noqa: E402
from camaddon.flanke_bahn import Stelle  # noqa: E402

fehler = []


def pruefe(wahr, text):
    print(ascii(("ok   " if wahr else "FEHLER ") + text))
    if not wahr:
        fehler.append(text)


R, SCHNEIDE = 3.0, 12.0
OBEN = (0.0, 0.0, 1.0)
x = np.arange(-40.0, 40.0, 0.5)
y = np.arange(-40.0, 40.0, 0.5)


def tasche(boden=-30.0, rand=20.0):
    """Ein Quader, Oberkante 0, mit Tasche ±`rand` bis `boden`."""
    h = np.zeros((len(x), len(y)))
    h[np.abs(x)[:, None].repeat(len(y), 1) < rand] = boden
    h[:, np.abs(y) >= rand] = 0.0
    return fr.Gitter.aus_hoehen(x, y, h)


# 1. Das Gitter: voll unter den Höhen, frei darüber, und die Abschnitte tragen Hohlräume.
g = tasche()
pruefe(g.trifft((0, 0, -31.0), OBEN, R, 0.0, 0.5), "unter dem Boden steht Material")
pruefe(not g.trifft((0, 0, -20.0), OBEN, R, 0.0, 5.0), "in der Tasche ist es frei")
pruefe(g.trifft((19.0, 0, -20.0), OBEN, R, 0.0, 5.0), "die Wand trifft es")
grenzen = np.full((len(x), len(y), 2, 2), np.nan)
grenzen[:, :, 0] = (-50.0, -40.0)
grenzen[:, :, 1] = (-10.0, 0.0)
hohl = fr.Gitter.aus_abschnitten(x, y, grenzen)
pruefe(
    not hohl.trifft((0, 0, -30.0), OBEN, R, 0.0, 5.0),
    "der Hohlraum zwischen zwei Abschnitten ist frei",
)
pruefe(hohl.trifft((0, 0, -9.0), OBEN, R, 0.0, 2.0), "der Abschnitt darüber ist voll")
pruefe(
    fr.Gitter.aus_hoehen(x, y, np.full((len(x), len(y)), -np.inf)) is None,
    "ohne Material kein Gitter",
)

# 2. Eintauchen in der geräumten Tasche: im Eilgang bis VORLAUF vors Ende.
anfang = Stelle((0.0, 0.0, 5.0), OBEN, eilgang=True)
unten = Stelle((0.0, 0.0, -25.0), OBEN, eintauchen=True)
aus = fr.ohne_luft([anfang, unten], tasche(), R, SCHNEIDE)
pruefe(
    len(aus) == 3 and aus[1].eilgang and aus[2].eintauchen, "Eintauchen: erst Eilgang, dann langsam"
)
pruefe(
    abs(aus[1].spitze[2] - (-25.0 + fr.VORLAUF)) < 1e-6,
    f"bis VORLAUF vors Ende: {aus[1].spitze[2]}",
)

# 3. Eintauchen ins volle Material: Es bleibt, wie es war, kein Eilgang hinein.
voll = fr.Gitter.aus_hoehen(x, y, np.zeros((len(x), len(y))))
aus = fr.ohne_luft([Stelle((0.0, 0.0, 1.0), OBEN, eilgang=True), unten], voll, R, SCHNEIDE)
pruefe(len(aus) == 2 and aus[1].eintauchen, "ins Volle: nur langsam")
aus = fr.ohne_luft(
    [Stelle((0.0, 0.0, 30.0), OBEN, eilgang=True), unten], tasche(-10.0), R, SCHNEIDE
)
tiefe = aus[1].spitze[2]
pruefe(
    aus[1].eilgang and tiefe >= -10.0 + fr.VORLAUF - fr.SCHRITT,
    f"Eilgang endet vorm Boden: {tiefe}",
)


# 4. Zufahrt und Keil: frei im Freivorschub, vor dem Material VORLAUF langsam, die Wand nie.
def strecke(von, bis, z, y=0.0, **art):
    n = int(abs(bis - von) / 0.5)
    return [Stelle((von + (bis - von) * k / n, y, z), OBEN, **art) for k in range(1, n + 1)]


start = Stelle((-15.0, 0.0, -20.0), OBEN)
weg = strecke(-15.0, 10.0, -20.0, zufahrt=True)
aus = fr.ohne_luft([start, *weg], tasche(), R, SCHNEIDE)
pruefe(all(s.frei for s in aus[1:]), "Zufahrt ganz frei: ganz schnell")
wand = strecke(-15.0, 10.0, -20.0)
aus = fr.ohne_luft([start, *wand], tasche(), R, SCHNEIDE)
pruefe(
    not any(s.frei for s in aus), "der Umlauf an der Wand bleibt im Vorschub, auch ohne Material"
)
kurz = strecke(-15.0, -12.0, -20.0, zufahrt=True)
aus = fr.ohne_luft([start, *kurz], tasche(), R, SCHNEIDE)
pruefe(not any(s.frei for s in aus), "kürzer als MINDEST: lohnt nicht")
gitter = tasche()
gitter.voll[np.searchsorted(gitter.x, 5.0) :, :, :] = True  # der Keil ab x = 5
aus = fr.ohne_luft([start, *weg], gitter, R, SCHNEIDE)
schnell = [s.spitze[0] for s in aus if s.frei]
langsam = [s.spitze[0] for s in aus[1:] if not s.frei]
pruefe(
    bool(schnell) and max(schnell) + R + fr.RAND + fr.VORLAUF <= 5.0 + 1.0,
    f"frei bis {max(schnell)}",
)
pruefe(bool(langsam) and min(langsam) > max(schnell), "danach langsam, nichts mehr schnell")
pruefe(
    all(math.dist(s.spitze, w.spitze) < 1e-9 for s, w in zip(aus[1:], weg, strict=True)),
    "die Bahn bleibt",
)

# 5. Abfahren nimmt weg: Der Umlauf davor macht die Zufahrt danach frei.
gitter = tasche()
gitter.voll[np.searchsorted(gitter.x, 5.0) :, :, :] = True
# Zwei Umläufe nebeneinander nehmen den Keil breiter weg, als die Zufahrt Platz braucht.
hin = strecke(-15.0, 11.0, -20.0, y=-1.0)
zurueck = strecke(11.0, -15.0, -20.0, y=1.0)
aus = fr.ohne_luft([start, *hin, *zurueck, start, *weg], gitter, R, SCHNEIDE)
pruefe(sum(s.frei for s in aus) == len(weg), "was die Umläufe davor weggenommen haben, ist frei")

# 6. Unter dem Rand: Der schnelle Weg endet vor dem Keil, der Rest taucht ein.
gitter = tasche()
gitter.voll[:, :, gitter.z < -20.0] = True  # Der Keil steht bis z = −20
punkte = [
    bn.Punkt(True, 0.0, 0.0, 10.0),
    bn.Punkt(False, 0.0, 0.0, -35.0, anteil=20.0),
    bn.Punkt(False, 5.0, 0.0, -35.0),
]
neu, achsen = fr.kugelwege_pruefen(punkte, [OBEN] * 3, gitter, R, SCHNEIDE)
pruefe(len(neu) == 4 and len(achsen) == 4, "der Weg ist geteilt")
pruefe(
    neu[1].anteil == 20.0 and neu[2].anteil == 1.0 and neu[2].eintauchen,
    "erst schnell, dann eintauchen",
)
pruefe(neu[1].z + R - R - fr.RAND >= -20.0, f"schnell nur bis vor den Keil: {neu[1].z}")
offen = tasche()
neu, _achsen = fr.kugelwege_pruefen(
    [punkte[0], bn.Punkt(False, 0.0, 0.0, -25.0, anteil=20.0)], [OBEN] * 2, offen, R, SCHNEIDE
)
pruefe(len(neu) == 2 and neu[1].anteil == 20.0, "frei: unverändert schnell")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
