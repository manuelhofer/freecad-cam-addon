# SPDX-License-Identifier: LGPL-2.1-or-later
"""Operationen mit einer Werkzeugachse je Satz (5 Achsen simultan, W-015): der Kugelfräser
angestellt (angestellt.py) und die Flanke (flanke.py). Für „Auf der Maschine prüfen“, die
Kollision und „Programm schreiben“ an einer Stelle: ob eine Operation so eine ist und ihre Sätze
für eine Maschine.

Die gelesene Kinematik entscheidet, ob die gespeicherten Richtungen erreichbar sind –
auch mit einer Rundachse oder einer festen Spindel. Es gibt keine senkrechte Ersatzbahn.

Läuft ohne Oberfläche.
"""

from dataclasses import dataclass

from .sprache import tr


@dataclass
class Programm:
    """Tatsächlich gefahrene Sätze und ausdrücklich unbearbeitete vollständige Schnittzüge."""

    befehle: list
    ausgelassen: tuple = ()
    materialdaten: tuple = ()  # Ursprünglicher Eilgang und Schnittvorschub je wirklichem NC-Satz.

    @property
    def hinweis(self):
        """Auslassungsgründe für Programm und Abspieler, leer bei vollständiger Bahn."""
        return "; ".join(tr("sb.hinweis.ausgelassen", zug=n, grund=g) for n, g in self.ausgelassen)


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
    return programm(op, maschine, tcpm, bei_null).befehle


def programm(op, maschine, tcpm=False, bei_null=False):
    """NC und Restbericht; bei Fehlern nur sicher getrennte vollständige Schnittzüge behalten."""
    from . import angestellt as an
    from . import entgraten3d as e3op
    from . import flanke as fl
    from . import maschinenzugang as mz
    from . import simultan_bereiche as sb

    if maschine is None:
        raise ValueError(tr("si.fehler.maschine"))
    if not maschine.rundachsen:
        tcpm = False  # Keine Rundbewegung: die feste Abbildung liefert bereits echte XYZ.
    cache = getattr(op, "_pruefprogramm", None)
    if cache is not None and cache[0] == pruefschluessel(maschine, tcpm, bei_null):
        return Programm(
            list(cache[1]), materialdaten=tuple(getattr(op, "_pruefmaterial", ()) or ())
        )

    adapter = an if an.ist_angestellt(op) else e3op if e3op.ist_entgraten3d(op) else fl
    if tcpm:
        # Dieselbe tatsächliche Erreichbarkeit/Teilbereichswahl wie ohne TCPM.
        # Sonst könnte ein im Grundprogramm ausgelassener Linearanschlag unter
        # TCPM wieder als vollständige unbearbeitbare Bahn auftauchen.
        kontrolliert = programm(op, maschine)
        if kontrolliert.ausgelassen:
            raise ValueError(tr("sb.fehler.tcpm"))
        return Programm(adapter.befehle(op, maschine, tcpm=True, bei_null=bei_null))
    try:
        daten = []
        view = sb._Ansicht(op, _pruefmaterial=daten)
        nc = adapter.befehle(view, maschine, rohteil=an.rohteil_von(op))
        if isinstance(getattr(op, "_pruefmaterial", None), list):
            op._pruefmaterial[:] = daten
        grund = mz.bahn_grund(maschine, nc, op.Label)
        if grund:
            raise ValueError(grund)
        return Programm(nc, materialdaten=tuple(daten))
    except ValueError as fehler:
        # Dieselbe Herkunftsliste auch nach dem Auslassen und Verdichten erzeugen.
        daten = []
        view = sb._Ansicht(op, _pruefmaterial=daten)
        try:
            nc, rest = sb.teilen(view, maschine, str(fehler))
        except ValueError:
            if not maschine.rundachsen:
                # Ohne Rundachsen bleibt kein Zug: ein Satz, der es sagt (statt „Punkt 1 der
                # Bahn: keine Stellung der Rundachsen“).
                raise ValueError(tr("so.fehler.ohne_rundachsen")) from fehler
            raise
        if isinstance(getattr(op, "_pruefmaterial", None), list):
            op._pruefmaterial[:] = daten
        return Programm(nc, rest, tuple(daten))


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
