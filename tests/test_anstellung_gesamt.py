# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die ganze Richtungsfolge gegen vollständiges Auszählen prüfen, örtliche Sackgasse zeigen."""

import itertools
import math
import os
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from camaddon import anstellung_frei as af
from camaddon import anstellung_gesamt as ag


def winkel(a, b):
    """Winkel zwischen zwei Einheitsvektoren in Radiant."""
    return math.acos(float(np.clip(np.dot(a, b), -1, 1)))


def aufwand(richtungen):
    """Unabhängige Summe vom und zum senkrechten Werkzeug, einschließlich aller Übergänge."""
    r = [(0, 0, 1), *richtungen, (0, 0, 1)]
    return sum(winkel(a, b) for a, b in zip(r, r[1:], strict=False))


def pruefung():
    n = np.array([(0, -math.sin(math.radians(w)), math.cos(math.radians(w))) for w in (0, 8.5, 17)])
    k = ag.kandidaten(n, 15)
    folge, kosten = ag.kuerzester_weg(k, n, 15)
    vollstaendig = math.inf
    for indices in itertools.product(range(k.shape[1]), repeat=len(n)):
        r = [k[i, j] for i, j in enumerate(indices)]
        if any(
            not 15 - 1e-9 <= math.degrees(winkel(a, b)) <= 85 + 1e-9
            for a, b in zip(r, n, strict=True)
        ):
            continue
        erlaubt = True
        for i in range(1, len(r)):
            achse = r[i - 1] + r[i]
            achse /= np.linalg.norm(achse)
            normale = n[i - 1] + n[i]
            normale /= np.linalg.norm(normale)
            if not 15.5 - 1e-9 <= math.degrees(winkel(achse, normale)) <= 85 + 1e-9:
                erlaubt = False
                break
        if erlaubt:
            vollstaendig = min(vollstaendig, aufwand(r))
    assert math.isfinite(vollstaendig)
    assert abs(kosten - vollstaendig) < 1e-10, (kosten, vollstaendig)
    ist = ag.richtungen(list(n), 15)
    assert np.allclose(ist, k[np.arange(len(n)), folge])
    oertlich = af.richtungen(n, 17)
    assert aufwand(ist) < 0.6 * aufwand(oertlich), "Keine Voraussicht in der örtlichen Sackgasse"
    assert np.allclose(np.linalg.norm(ist, axis=1), 1)
    assert ag.richtungen([], 15) == []
    mit_luft = ag.richtungen([None, *n, None], 15)
    assert len(mit_luft) == len(n) + 2 and np.all(np.isfinite(mit_luft))
    gesperrt = ag.verbindungen(k[0], k[0], n[0], -n[0], 15)
    assert np.all(np.isinf(gesperrt)), "Gegenläufige Normalen nicht abgewiesen"
    try:
        ag.richtungen([n[0]] * 300, 15, fortschritt=lambda _anteil: False)
    except ValueError:
        pass
    else:
        raise AssertionError("Abbrechen der Richtungsplanung ignoriert")
    print("WINKELAUFWAND", math.degrees(aufwand(oertlich)), math.degrees(kosten), flush=True)


pruefung()
print("OK", os.path.basename(__file__))
