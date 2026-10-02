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


def fuer_m3(gleichlauf, tc):
    """Was eine Bahn, die mit M3 rechnet, als „Gleichlauf“ braucht, damit mit der Drehrichtung
    von `tc` gleichlaufend (`gleichlauf`) oder gegenlaufend gefräst wird."""
    return bool(gleichlauf) != rueckwaerts(tc)
