# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Drehrichtung der Spindel am Werkzeug-Controller – und was sie für den Gleichlauf heißt.

Die Bahnen rechnen mit rechtsdrehender Spindel (M3, FreeCADs „Forward“): Im Gleichlauf liegt
das Material rechts der Fahrtrichtung. Dreht die Spindel rückwärts (M4, „Reverse“ – ein links
schneidender Fräser), liegt es links; dann rechnen sie mit dem Gegenteil (Manuel, 2026-10-02:
die Spindel kann beide Richtungen; P-2026-10-02-20). FreeCADs eigene Operationen fragen danach
nicht.
"""


def rueckwaerts(tc):
    """Dreht die Spindel des Controllers `tc` rückwärts (M4)?"""
    return str(getattr(tc, "SpindleDir", "Forward")) == "Reverse"


def ist_gleichlauf(achse, fahrt, material):
    """Fräst ein Fräser mit M3 so im Gleichlauf? Drei Richtungen in einem Koordinatensystem,
    gleich welchem (meist dem des Teils): `achse` – die Werkzeugachse vom Halter zur Spitze;
    `fahrt` – wohin der Fräser sich gegenüber dem Teil bewegt; `material` – wo neben ihm das
    Material liegt, das er abträgt. M3 dreht von der Spindel aus gesehen im Uhrzeigersinn:
    Gleichlauf, wenn das Material – von der Spindel aus gesehen – rechts der Fahrt liegt,
    (fahrt × −achse) · material > 0. Das gilt für jede Maschine und jede Lage des Fräsers:
    senkrecht über dem Tisch, radial am Mantel (die Fahrt macht dann die Rundachse), längs an
    der Stirn. Mit M4 umgekehrt (fuer_m3, P-2026-10-02-23)."""
    ax, ay, az = (-float(x) for x in achse)
    fx, fy, fz = (float(x) for x in fahrt)
    rechts = (fy * az - fz * ay, fz * ax - fx * az, fx * ay - fy * ax)
    return sum(r * float(m) for r, m in zip(rechts, material, strict=True)) > 0


def fuer_m3(gleichlauf, tc):
    """Was eine Bahn, die mit M3 rechnet, als „Gleichlauf“ braucht, damit mit der Drehrichtung
    von `tc` gleichlaufend (`gleichlauf`) oder gegenlaufend gefräst wird."""
    return bool(gleichlauf) != rueckwaerts(tc)
