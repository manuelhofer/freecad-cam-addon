# Prüft „stößt der Halter an?“ beim 4-Achs-Fräsen (vierachs_halter, P-2026-10-11-51; Manuel,
# Frage 7: „sehr klar darauf hinweisen das die ausspannlänge des fräsers nicht ausreicht“): eine
# Welle Ø 40 (a −40 … 0) mit einem Bund Ø 60 dahinter (a −45 … −40); die Kugel Ø 6 fährt rundum
# bei a −35 auf der Welle, ihr Halter Ø 30 beginnt 5 mm über der Spitze. Er reicht längs bis
# a −50 und steht dort 25 mm von der Achse – im Bund (Radius 30). Frei wäre er ab 10 mm über der
# Spitze (20 + 10 = 30). Ohne den Bund stößt nichts an. Dazu die Lage von Spitze und Achse je
# Satz: bei φ 90° liegt die Spitze auf V, quer versetzt gegen U.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import vierachs_halter as vhalter

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
LAENGS, RADIAL = (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)

# Spitze und Achse: a = z, φ = 90° – die Werkzeugachse längs V = L × U = +y, q quer gegen U.
spitzen, achsen, a = vhalter.stellen([(-5.0, 20.0, 2.0, 90.0)], [False], LAENGS, RADIAL)
pruefe(
    np.allclose(spitzen[0], (-2.0, 20.0, -5.0)) and np.allclose(achsen[0], (0.0, 1.0, 0.0)),
    f"Spitze {spitzen[0]}, Achse {achsen[0]}",
)
leer = vhalter.stellen([(0.0, 20.0, 0.0, 0.0)], [True], LAENGS, RADIAL)
pruefe(len(leer[0]) == 0, "ein Eilgang zählt")

welle = Part.makeCylinder(20, 40, V(0, 0, -40))
bund = welle.fuse(Part.makeCylinder(30, 5, V(0, 0, -45))).removeSplitter()
phi = np.arange(0.0, 360.0, 2.0)
saetze = np.column_stack(
    [np.full(len(phi), -35.0), np.full(len(phi), 20.0), np.zeros(len(phi)), phi]
)
eilgang = [False] * len(phi)
koerper = [(5.0, 30.0, 15.0)]
befund = vhalter.pruefen(bund, saetze, eilgang, LAENGS, RADIAL, koerper, 3.0)
pruefe(befund is not None, "am Bund stößt nichts an")
if befund is not None:
    stellen, heraus, mindestens, a_von, a_bis = befund
    pruefe(stellen > 10 and heraus == 5.0, f"Stellen {stellen}, heraus {heraus}")
    pruefe(9.9 < mindestens < 10.6, f"mindestens {mindestens:.2f} (soll gut 10)")
    pruefe(math.isclose(a_von, -35.0) and math.isclose(a_bis, -35.0), f"a {a_von} … {a_bis}")
pruefe(
    vhalter.pruefen(welle, saetze, eilgang, LAENGS, RADIAL, koerper, 3.0) is None,
    "ohne Bund stößt etwas an",
)
# Nur Körper, die dicker sind als die Schneide, zählen: ein Schaft wie sie liegt nur an.
pruefe(
    vhalter.pruefen(bund, saetze, eilgang, LAENGS, RADIAL, [(5.0, 30.0, 3.0)], 3.0) is None,
    "der Schaft wie die Schneide zählt",
)

# Auf den Nebenrechnern, die Stellen reihum verteilt (P-2026-10-24-16): eine Spirale von a −38 bis
# −6, acht Umdrehungen – nahe am Bund stößt der Halter an, weiter vorn nicht. Dieselben Stellen und
# dieselben Längen wie in einem Zug gerechnet.
from camaddon import flanke_bahn as fb  # noqa: E402
from camaddon import netzabstand as na  # noqa: E402

phi_s = np.arange(0.0, 8 * 360.0, 2.0)
saetze_s = np.column_stack(
    [-38.0 + 32.0 * phi_s / phi_s[-1], np.full(len(phi_s), 20.0), np.zeros(len(phi_s)), phi_s]
)
sp, ac, _a = vhalter.stellen(saetze_s, [False] * len(phi_s), LAENGS, RADIAL)
w = fb.ausgewaehlt(sp)
sp, ac = sp[w], ac[w]
teile = fb.dickere_koerper(koerper, 3.0)
verteilt = vhalter._verteilt(bund, sp, ac, teile)
pruefe(len(sp) >= vhalter.VERTEILT_AB and verteilt is not None, f"nicht verteilt: {len(sp)} Stellen")
if verteilt is not None:
    an_v, weiter_v = verteilt
    an_e, weiter_e = fb.noetig_weiter(na.Netz(bund, fb.HALTER_NETZ), sp, ac, teile)
    ordnung = np.argsort(an_v)
    pruefe(
        0 < len(an_e) < len(sp) and np.array_equal(an_v[ordnung], an_e),
        f"anstoßend verteilt {len(an_v)}, in einem Zug {len(an_e)} von {len(sp)}",
    )
    pruefe(np.allclose(weiter_v[ordnung], weiter_e), "weiter verteilt anders")
    print(f"verteilt: {len(an_v)} von {len(sp)} Stellen stoßen an")

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
