# SPDX-License-Identifier: LGPL-2.1-or-later
"""Operationen mit einer Werkzeugachse je Satz (5 Achsen simultan, W-015): der Kugelfräser
angestellt (angestellt.py) und die Flanke (flanke.py). Für „Auf der Maschine prüfen“, die
Kollision und „Programm schreiben“ an einer Stelle: ob eine Operation so eine ist und ihre Sätze
für eine Maschine.

Ohne Maschine mit zwei Rundachsen fährt der angestellte Kugelfräser senkrecht (dieselbe Bahn der
Kugel) – die Flanke geht dann nicht: Senkrecht gefahren schnitte ihr Fräser falsch.

Läuft ohne Oberfläche.
"""

from .sprache import tr


def ist_simultan(op):
    """Hat die Operation eine Werkzeugachse je Satz?"""
    from . import angestellt as an
    from . import flanke as fl

    return an.ist_angestellt(op) or fl.hat_achsen(op)


def im_job(job):
    """Steht im Job eine aktive Operation mit Werkzeugachse je Satz?"""
    return any(
        getattr(op, "Active", True) and ist_simultan(op)
        for op in getattr(getattr(job, "Operations", None), "Group", [])
    )


def senkrecht_moeglich(op):
    """Gibt die Operation ohne 5-Achs-Maschine eine richtige Bahn (senkrecht gefahren)?"""
    from . import angestellt as an

    return an.ist_angestellt(op)


def befehle(op, maschine, tcpm=False):
    """Die Sätze der Operation für `maschine` (schwenken.Maschine): mit zwei Rundachsen je Punkt
    gerechnet (`tcpm`: für eine Steuerung, die die Spitze führt – simultan.befehle_mit_tcpm); mit
    weniger der angestellte Kugelfräser senkrecht, die Flanke ein ValueError."""
    from . import angestellt as an
    from . import flanke as fl

    if len(getattr(maschine, "rundachsen", ())) < 2:
        if senkrecht_moeglich(op):
            return list(op.Path.Commands)
        raise ValueError(tr("fl.fehler.maschine", operation=op.Label))
    if an.ist_angestellt(op):
        return an.befehle(op, maschine, tcpm=tcpm)
    return fl.befehle(op, maschine, tcpm=tcpm)
