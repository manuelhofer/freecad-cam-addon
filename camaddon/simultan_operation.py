# SPDX-License-Identifier: LGPL-2.1-or-later
"""Operationen mit einer Werkzeugachse je Satz (5 Achsen simultan, W-015): der Kugelfräser
angestellt (angestellt.py) und die Flanke (flanke.py). Für „Auf der Maschine prüfen“, die
Kollision und „Programm schreiben“ an einer Stelle: ob eine Operation so eine ist und ihre Sätze
für eine Maschine.

Die gelesene Kinematik entscheidet, ob die gespeicherten Richtungen erreichbar sind –
auch mit einer Rundachse oder einer festen Spindel. Es gibt keine senkrechte Ersatzbahn.

Läuft ohne Oberfläche.
"""

from .sprache import tr


def ist_simultan(op):
    """Hat die Operation eine Werkzeugachse je Satz?"""
    from . import angestellt as an
    from . import entgraten3d as e3op
    from . import flanke as fl

    return an.ist_angestellt(op) or fl.hat_achsen(op) or e3op.hat_achsen(op)


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


def befehle(op, maschine, tcpm=False, bei_null=False):
    """Die gespeicherten Richtungen mit den tatsächlichen Achsen der Maschine rechnen.

    Eine nicht erreichbare Richtung oder ein Anschlag erzeugt ValueError, keine
    ersatzweise senkrechte Bearbeitung. `tcpm`: die Steuerung führt die Spitze.
    """
    from . import angestellt as an
    from . import entgraten3d as e3op
    from . import flanke as fl

    if maschine is None:
        raise ValueError(tr("si.fehler.maschine"))
    if not maschine.rundachsen:
        tcpm = False  # Keine Rundbewegung: die feste Abbildung liefert bereits echte XYZ.
    cache = getattr(op, "_pruefprogramm", None)
    if cache is not None and cache[0] == pruefschluessel(maschine, tcpm, bei_null):
        return list(cache[1])

    if an.ist_angestellt(op):
        return an.befehle(op, maschine, tcpm=tcpm, bei_null=bei_null)
    if e3op.ist_entgraten3d(op):
        return e3op.befehle(op, maschine, tcpm=tcpm, bei_null=bei_null)
    return fl.befehle(op, maschine, tcpm=tcpm, bei_null=bei_null)


def pruefschluessel(maschine, tcpm=False, bei_null=False):
    """Schlüssel eines nur in der unveränderten Variantenansicht gespeicherten Programms.

    Erreichbarkeit und Abfahrt lesen dasselbe Programm; die inverse Kinematik muss
    dafür nicht dreimal gerechnet werden. Reale CAM-Objekte bekommen diesen Cache
    nicht. Werkzeugaufnahme, Einspannung und Nullpunkt sind Teil des Schlüssels.
    """
    from . import reichweite as rw

    einspannung = rw._einspannung(maschine.laenge)
    return (
        id(maschine.pruefung),
        maschine.aufnahme.Name,
        einspannung.laenge,
        repr(einspannung.lage),
        tuple(maschine.nullpunkt),
        tcpm,
        bei_null,
    )
