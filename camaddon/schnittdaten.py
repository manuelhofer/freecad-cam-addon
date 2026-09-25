# SPDX-License-Identifier: LGPL-2.1-or-later
"""Rechnen mit Schnittwerten (W-002): Drehzahl, Vorschub, Zeitspanvolumen, Eingriff.

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


# --- Eingriff und Spandicke (P-2026-09-25-48) --------------------------------

# Dünner als das schneidet eine Schneide kaum noch, sie reibt – Verschleiß
# ohne Abtrag. Grobe Grenze für Hartmetall, nur für einen Hinweis.
MINDEST_SPANDICKE = 0.01  # mm


def eingriffswinkel(ae, durchmesser):
    """Der Winkel φ, über den ein Zahn im Material ist, in Bogenmaß.

    cos φ = 1 − 2 · ae / D; eine Vollnut (ae ≥ D) hat 180°.
    """
    if ae <= 0 or durchmesser <= 0:
        return 0.0
    return math.acos(1.0 - 2.0 * min(ae, durchmesser) / durchmesser)


def spandicke_max(fz, ae, durchmesser):
    """Die größte Spandicke: fz · sin φ bei ae < D/2, sonst fz."""
    phi = eingriffswinkel(ae, durchmesser)
    if phi >= math.pi / 2:
        return fz
    return fz * math.sin(phi)


def spandicke_mittel(fz, ae, durchmesser):
    """Die mittlere Spandicke über den Eingriff: fz · (1 − cos φ) / φ."""
    phi = eingriffswinkel(ae, durchmesser)
    if phi <= 0:
        return 0.0
    return fz * (1.0 - math.cos(phi)) / phi


def fz_fuer_spandicke(spandicke, ae, durchmesser):
    """Das fz, bei dem die größte Spandicke `spandicke` beträgt (Spandickenausgleich)."""
    phi = eingriffswinkel(ae, durchmesser)
    if phi <= 0:
        return 0.0
    if phi >= math.pi / 2:
        return spandicke
    return spandicke / math.sin(phi)
