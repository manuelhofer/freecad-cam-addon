# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tauchfräsen – Entwurf (Plan C2; Manuel, 2026-10-31: „man bohrt ein loch und kaut stechend dann
das zeug mit einem messerkopf raus … alles möglichkeiten die der benutzer haben muss“).

Noch nicht im Assistenten: Eine neue Strategie zeigt Claude erst als Bild mit Zahlen, und sie kommt
mit Manuels Ja (Gedächtnis „Strategiewahl erst besprechen“). Hier stehen die Rechnung und die
Bahn, `docs/bilder/tauchfraesen_entwurf.svg` zeigt sie an einer Tasche.

Der Fräser (ein Tauchfräser oder ein mittenschneidender Schaftfräser mit Wendeplatten) taucht
senkrecht ins Volle, Stelle an Stelle:

- **Wo:** Die Mitte des Fräsers bleibt um Radius + Aufmaß innerhalb des Bodens (makeOffset2D). Darin
  liegen die Stellen in einem Raster (`schritt`, höchstens 0,7 × D – dann bleiben zwischen vier
  Stellen nur kleine Zwickel), dazu Stellen längs der versetzten Kontur im selben Abstand, damit
  die Wände gleichmäßig Aufmaß behalten.
- **Reihenfolge:** von der Mitte (dort wird vorgebohrt) nach außen, jede neue Stelle neben dem
  schon Offenen (von_innen_nach_aussen).
- **Wie:** im Eilgang über die Stelle (knapp über der Oberkante), senkrecht mit dem
  Eintauchvorschub bis auf den Boden + Aufmaß, im Eilgang zurück nach oben, zur nächsten – kein
  Zickzack, kein Rampen.

Läuft ohne Oberfläche.
"""

import math

from . import bahn as bh

SCHRITT_ANTEIL = 0.7  # × D: größter Abstand der Stellen
ABHEBEN = 1.0  # mm über der Oberkante zwischen den Stellen


def stellen(boden, radius, aufmass=0.0, schritt=None):
    """[(x, y)] der Tauchstellen über der ebenen, waagerechten Fläche `boden` (Part.Face), in der
    Reihenfolge des Fräsens – leer, wenn der Fräser nicht hineinpasst."""
    import FreeCAD

    schritt = schritt or SCHRITT_ANTEIL * 2 * radius
    try:
        innen = boden.makeOffset2D(-(radius + aufmass), join=0)
    except Exception:  # Part.OCCError: zu eng für den Fräser
        return []
    if innen.isNull() or not innen.Faces or innen.Area < 1e-6:
        return []
    z = boden.BoundBox.ZMax
    box = innen.BoundBox
    punkte = []
    zeilen = max(1, math.ceil(box.YLength / schritt))
    for zeile in range(zeilen + 1):
        y = box.YMin + min(zeile * box.YLength / zeilen, box.YLength)
        spalten = max(1, math.ceil(box.XLength / schritt))
        for spalte in range(spalten + 1):
            x = box.XMin + spalte * box.XLength / spalten
            if innen.isInside(FreeCAD.Vector(x, y, z), 1e-6, True):
                punkte.append((x, y))
    # Längs der Kontur der versetzten Fläche, damit die Wände gleichmäßig Aufmaß behalten.
    for kante in innen.Edges:
        anzahl = max(1, math.ceil(kante.Length / schritt))
        for i in range(anzahl):
            p = kante.valueAt(
                kante.FirstParameter + i * (kante.LastParameter - kante.FirstParameter) / anzahl
            )
            if all(math.hypot(p.x - a, p.y - b) > 0.5 * schritt for a, b in punkte):
                punkte.append((p.x, p.y))
    mitte = innen.CenterOfMass if innen.isInside(innen.CenterOfMass, 1e-6, True) else None
    return von_innen_nach_aussen(punkte, (mitte.x, mitte.y) if mitte is not None else None)


def von_innen_nach_aussen(punkte, mitte=None):
    """Die Reihenfolge (Manuel, 2026-10-31: „bohrt mittig ein loch und fräst dann“; zum ersten
    Entwurf: „wieso zuickzack bahn ?“): zuerst die Stelle an der Mitte (dort wird vorgebohrt),
    dann immer die, die dem schon Offenen am nächsten liegt – so greift jede neue Stelle neben
    Offenem an und schneidet nur zum Teil ins Volle; bei Gleichstand die nächste zur letzten."""
    if not punkte:
        return []
    if mitte is None:
        mitte = (sum(p[0] for p in punkte) / len(punkte), sum(p[1] for p in punkte) / len(punkte))
    offen = list(punkte)
    erste = min(offen, key=lambda p: math.hypot(p[0] - mitte[0], p[1] - mitte[1]))
    folge = [erste]
    offen.remove(erste)
    while offen:
        letzte = folge[-1]
        naechste = min(
            offen,
            key=lambda p: (
                round(min(math.hypot(p[0] - a, p[1] - b) for a, b in folge), 3),
                math.hypot(p[0] - letzte[0], p[1] - letzte[1]),
            ),
        )
        folge.append(naechste)
        offen.remove(naechste)
    return folge


def bahn(punkte, z_oben, z_unten):
    """[bahn.Punkt]: je Stelle im Eilgang darüber (ABHEBEN über `z_oben`), mit Eintauchvorschub
    auf `z_unten`, im Eilgang zurück."""
    ergebnis = []
    oben = z_oben + ABHEBEN
    for x, y in punkte:
        ergebnis.append(bh.Punkt(True, x, y, oben))
        ergebnis.append(bh.Punkt(False, x, y, z_unten, eintauchen=True))
        ergebnis.append(bh.Punkt(True, x, y, oben))
    return ergebnis


def zeit(punkte, eintauchen, eilgang=None, beschleunigung=None):
    """Minuten für die Bahn (bahn.zeit); `eintauchen`: der Eintauchvorschub (mm/min)."""
    return bh.zeit(punkte, eintauchen, eintauchen, eilgang, beschleunigung)
