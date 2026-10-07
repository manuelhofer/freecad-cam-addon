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


def ergaenzen(
    bahn,
    form,
    namen,
    radius,
    aufmass,
    sicher,
    oben,
    sicherheit,
    vorschub,
    eintauchen,
    schritt=SCHRITT,
):
    """Randzüge ergänzen; Spitze senkrecht gespeichert, die Kugelmitte exakt am Rand."""
    punkte = list(bahn.punkte)
    for name in namen:
        face = form.getElement(name)
        for wire in face.Wires:
            zug = []
            letzter_rand = None
            for edge in wire.OrderedEdges:
                if edge.Length < 1e-9:
                    continue  # analytische Kugelflächen haben am Pol eine entartete Kante
                anzahl = max(2, int(math.ceil(edge.Length / schritt)) + 1)
                orte = edge.discretize(Number=anzahl)
                # discretize folgt der Kurvenparametrisierung, nicht der Orientierung
                # im Draht. Sonst verbinden Geraden gegenüberliegende Randpunkte.
                if edge.Orientation == "Reversed":
                    orte.reverse()
                if letzter_rand is not None and (orte[0] - letzter_rand).Length > 1e-5:
                    raise ValueError(tr("s5p.fehler.rand"))
                for p in orte:
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
                letzter_rand = orte[-1]
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
