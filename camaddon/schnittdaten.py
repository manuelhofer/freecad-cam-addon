# SPDX-License-Identifier: LGPL-2.1-or-later
"""Rechnen mit Schnittwerten (W-002): Drehzahl, Vorschub, Zeitspanvolumen.

Eingegeben werden vc und fz – so stehen sie im Katalog des Herstellers –,
Drehzahl und Vorschub rechnet das Addon. Alle Längen in mm, vc in m/min,
Ergebnisse in U/min, mm/min und cm³/min. Fehlt ein Wert (0), ist das
Ergebnis 0 – „unbekannt“, wie überall im Addon.

Läuft ohne Oberfläche.
"""

import math

from . import werkzeuge as wz


def drehzahl(vc, durchmesser):
    """n = vc · 1000 / (π · D), in U/min."""
    if vc <= 0 or durchmesser <= 0:
        return 0.0
    return vc * 1000.0 / (math.pi * durchmesser)


def vorschub(n, schneiden, fz):
    """vf = n · z · fz, in mm/min."""
    return n * schneiden * fz


def zeitspanvolumen(ae, ap, vf):
    """Q = ae · ap · vf / 1000 beim Fräsen, in cm³/min."""
    return ae * ap * vf / 1000.0


def zeitspanvolumen_bohren(durchmesser, vf):
    """Q = π · D² / 4 · vf / 1000 beim Bohren ins Volle, in cm³/min."""
    return math.pi * durchmesser**2 / 4.0 * vf / 1000.0


def rechne(werkzeug, einsatz):
    """(n, vf, Q) für einen Einsatz dieses Werkzeugs; fehlt etwas, sind die Werte 0."""
    n = drehzahl(einsatz.vc, werkzeug.durchmesser)
    vf = vorschub(n, werkzeug.schneiden, einsatz.fz)
    if werkzeug.art == wz.BOHRER:
        q = zeitspanvolumen_bohren(werkzeug.durchmesser, vf)
    else:
        q = zeitspanvolumen(einsatz.ae, einsatz.ap, vf)
    return n, vf, q
