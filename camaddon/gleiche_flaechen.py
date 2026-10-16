# SPDX-License-Identifier: LGPL-2.1-or-later
"""Gleiche Flächen zur angeklickten finden – fürs Anwählen auf einmal.

Manuel, 2026-10-16, an einer Tasche mit gerundetem Boden: „wenn ich nun aber die radien unten auch
mit gemacht haben will muss ich die alle anklicken .... was sehr müsam ist .. vll anklicken und
schauen ok was ist es ist es ein radius gibts auf gleicher höhe auch noch andere radien gleiche
radien wenn ja fragen "alle anwählen" das selbe für fasen oder sowas“.

Gleich heißt: dieselbe Art, dasselbe Maß, dieselbe Höhe (von – bis):
- RUNDUNG: Zylinder oder Torus, gleicher Radius (beim Torus der kleine). Eine Kehle (liegender
  Zylinder, Torus) und ein Eckradius einer Wand (Zylinder mit senkrechter Achse) sind zweierlei –
  auch bei gleichem Radius.
- FASE: eine schräge Ebene oder ein Kegel mit senkrechter Achse, gleiche Neigung.
- BODEN: eine ebene Fläche nach oben, auf derselben Höhe.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

RUNDUNG, ECKRADIUS, FASE, BODEN = "rundung", "eckradius", "fase", "boden"
TOLERANZ = 0.01  # mm – so genau müssen Maß und Höhe übereinstimmen
WINKEL_TOLERANZ = 0.5  # Grad
# Grad Neigung gegen die Waagerechte: dazwischen ist eine Ebene schräg.
FASE_VON, FASE_BIS = 5.0, 85.0
SENKRECHT = 1e-6  # so wenig darf eine Achse von Z abweichen, um senkrecht zu sein


@dataclass(frozen=True)
class Art:
    """Was eine Fläche ist: `art` (RUNDUNG, ECKRADIUS, FASE, BODEN), `mass` (Radius in mm, Neigung
    in Grad, beim Boden die Höhe) und die Höhe von `unten` bis `oben`."""

    art: str
    mass: float
    unten: float
    oben: float

    def gleich(self, andere):
        if andere is None or andere.art != self.art:
            return False
        toleranz = WINKEL_TOLERANZ if self.art == FASE else TOLERANZ
        return (
            abs(self.mass - andere.mass) <= toleranz
            and abs(self.unten - andere.unten) <= TOLERANZ
            and abs(self.oben - andere.oben) <= TOLERANZ
        )


def art(flaeche):
    """Die Art einer Fläche (Part.Face) – None, wenn sie keine der drei ist."""
    try:
        flaeche_ = flaeche.Surface
        box = flaeche.BoundBox
    except Exception:  # noqa: BLE001 – eine kaputte Fläche: keine Art
        return None
    typ = type(flaeche_).__name__
    if typ == "Cylinder":
        senkrecht = abs(abs(flaeche_.Axis.z) - 1.0) < SENKRECHT
        return Art(ECKRADIUS if senkrecht else RUNDUNG, flaeche_.Radius, box.ZMin, box.ZMax)
    if typ == "Toroid":
        return Art(RUNDUNG, flaeche_.MinorRadius, box.ZMin, box.ZMax)
    if typ == "Cone":
        if abs(abs(flaeche_.Axis.z) - 1.0) >= SENKRECHT:
            return None
        neigung = 90.0 - abs(math.degrees(flaeche_.SemiAngle))
        return Art(FASE, neigung, box.ZMin, box.ZMax)
    if typ == "Plane":
        try:
            u, v = flaeche_.parameter(flaeche.CenterOfMass)
            normale = flaeche.normalAt(u, v)
        except Exception:  # noqa: BLE001
            return None
        neigung = math.degrees(math.acos(min(abs(normale.z), 1.0)))
        if neigung < 1e-3 and normale.z > 0:
            return Art(BODEN, box.ZMax, box.ZMin, box.ZMax)
        if FASE_VON < neigung < FASE_BIS:
            return Art(FASE, neigung, box.ZMin, box.ZMax)
    return None


def gleiche(form, name):
    """(Art der Fläche `name` („Face12“), die Namen der anderen Flächen von `form` mit gleicher
    Art, Maß und Höhe) – (None, []), wenn die Fläche keine der Arten ist."""
    flaechen = form.Faces
    nummer = int(name[4:]) - 1 if name.startswith("Face") and name[4:].isdigit() else -1
    if not 0 <= nummer < len(flaechen):
        return None, []
    gesucht = art(flaechen[nummer])
    if gesucht is None:
        return None, []
    return gesucht, [
        f"Face{k + 1}"
        for k, flaeche in enumerate(flaechen)
        if k != nummer and gesucht.gleich(art(flaeche))
    ]
