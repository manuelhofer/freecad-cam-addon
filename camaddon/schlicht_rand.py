# SPDX-License-Identifier: LGPL-2.1-or-later
"""Genauer Randgang an Freiformflächen: die Kugel berührt die BRep-Fläche am Rand.

Das Flächenraster erreicht einen offenen Rand nicht immer bis zur verlangten
Grathöhe. Hier kommt die Kugelmitte aus Punkt + Radius mal Flächennormale,
unabhängig vom Raster. Eine Gegenfläche, die die Kugel dabei schneidet, führt
zu einem Fehler; ein zu großer Fräser wird nicht durch Hochsetzen beschönigt.
"""

import math

import Part

from . import bahn as bn
from .sprache import tr

SCHRITT = 0.2


def ergaenzen(bahn, form, namen, radius, aufmass, sicher, oben, sicherheit, vorschub, eintauchen):
    """Randzüge ergänzen; Spitze senkrecht gespeichert, die Kugelmitte exakt am Rand."""
    punkte = list(bahn.punkte)
    for name in namen:
        face = form.getElement(name)
        for wire in face.Wires:
            zug = []
            for edge in wire.OrderedEdges:
                anzahl = max(2, int(math.ceil(edge.Length / SCHRITT)) + 1)
                for p in edge.discretize(Number=anzahl):
                    u, v = face.Surface.parameter(p)
                    n = face.normalAt(u, v)
                    if n.z < 0:
                        n = -n
                    if n.z < 1e-5:
                        raise ValueError(tr("s5p.fehler.rand"))
                    n.normalize()
                    mitte = p + (radius + aufmass) * n
                    if (
                        form.isInside(mitte, 1e-7, False)
                        or form.distToShape(Part.Vertex(mitte))[0] < radius + aufmass - 0.003
                    ):
                        raise ValueError(tr("s5p.fehler.rand"))
                    punkt = bn.Punkt(False, mitte.x, mitte.y, mitte.z - radius)
                    if not zug or bn.weg(zug[-1], punkt) > 1e-6:
                        zug.append(punkt)
            if len(zug) < 2:
                continue
            erster = zug[0]
            if punkte:
                letzter = punkte[-1]
                punkte.append(bn.Punkt(True, letzter.x, letzter.y, sicher))
            punkte.append(bn.Punkt(True, erster.x, erster.y, sicher))
            punkte.append(
                bn.Punkt(True, erster.x, erster.y, min(sicher, max(oben, erster.z) + sicherheit))
            )
            punkte.extend(zug)
            letzter = punkte[-1]
            punkte.append(bn.Punkt(True, letzter.x, letzter.y, sicher))
            bahn.umlaeufe += 1
    bahn.punkte = punkte
    bahn.laenge = sum(
        bn.weg(a, b) for a, b in zip(punkte, punkte[1:], strict=False) if not b.eilgang
    )
    bahn.zeit = bn.zeit(punkte, vorschub, eintauchen)
    return bahn
