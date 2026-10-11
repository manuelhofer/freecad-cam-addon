# SPDX-License-Identifier: LGPL-2.1-or-later
"""Operationen mit einer Werkzeugachse je Satz (5 Achsen simultan, W-015): der Kugelfräser
angestellt (angestellt.py) und die Flanke (flanke.py). Für „Auf der Maschine prüfen“, die
Kollision und „Programm schreiben“ an einer Stelle: ob eine Operation so eine ist und ihre Sätze
für eine Maschine.

Die gelesene Kinematik entscheidet, ob die gespeicherten Richtungen erreichbar sind –
auch mit einer Rundachse oder einer festen Spindel. Es gibt keine senkrechte Ersatzbahn.

Läuft ohne Oberfläche.
"""

import collections
from dataclasses import dataclass

from .sprache import tr

# Programme echter Operationen, je Inhalt gemerkt (_inhalt): Der Beobachter des Materialstands,
# das Prüffenster und „Programm schreiben“ fragen dieselbe 5-Achs-Bahn mit einer jedes Mal neu
# gebauten Prüfung – an der Bahn des Szenarios „Wegkippen“ je 20 s (P-2026-10-11-66).
_PROGRAMME = collections.OrderedDict()
PROGRAMME_HOECHSTENS = 8


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
    """NC und Restbericht; bei Fehlern nur sicher getrennte vollständige Schnittzüge behalten.
    Je Inhalt (Bahn, Achsen je Satz, Fräser, Rohteil, Maschine, Einspannung, Nullpunkt) gemerkt –
    höchstens PROGRAMME_HOECHSTENS; was nicht geht (ValueError), nicht."""
    schluessel = _inhalt(op, maschine, tcpm, bei_null)
    gemerkt = _PROGRAMME.get(schluessel) if schluessel is not None else None
    if gemerkt is None:
        gemerkt = _programm_rechnen(op, maschine, tcpm, bei_null)
        if schluessel is not None:
            _PROGRAMME[schluessel] = Programm(
                list(gemerkt.befehle), tuple(gemerkt.ausgelassen), tuple(gemerkt.materialdaten)
            )
            while len(_PROGRAMME) > PROGRAMME_HOECHSTENS:
                _PROGRAMME.popitem(last=False)
        return gemerkt
    _PROGRAMME.move_to_end(schluessel)
    if isinstance(getattr(op, "_pruefmaterial", None), list):
        op._pruefmaterial[:] = list(gemerkt.materialdaten)
    return Programm(list(gemerkt.befehle), gemerkt.ausgelassen, gemerkt.materialdaten)


def merken(schluessel, befehle, ausgelassen=(), materialdaten=()):
    """Ein Programm, das ein Nebenrechner gerechnet hat (programm_im_arbeiter: die Sätze als
    (Name, Parameter)), unter `schluessel` (_inhalt) in den Speicher – das Prüffenster fragt danach
    mit derselben Maschine (P-2026-10-11-70)."""
    import Path

    _PROGRAMME[schluessel] = Programm(
        [Path.Command(name, dict(parameter)) for name, parameter in befehle],
        tuple(ausgelassen),
        tuple(materialdaten),
    )
    while len(_PROGRAMME) > PROGRAMME_HOECHSTENS:
        _PROGRAMME.popitem(last=False)


def programm_im_arbeiter(dokument, op_name, maschine_dok, maschine, aufnahme, laenge, lage, null):
    """Im Nebenrechner: programm() der Operation `op_name` aus der Kopie des Jobs `dokument` – mit
    der Maschine aus ihrer Kopie (`maschine`: kollision.Maschinendaten), der Werkzeugaufnahme
    `aufnahme`, der Einspannung (`laenge`, `lage` wie kollision.lage_als_daten) und dem Nullpunkt
    `null`. Gibt (Sätze als (Name, Parameter), ausgelassen, Materialdaten) zurück."""
    import FreeCAD

    from . import kollision as kb
    from . import reichweite as rw
    from . import schwenken as sw

    pruefung = kb._pruefung_fuer(maschine_dok, maschine)
    einspannung = rw.Einspannung(float(laenge), kb._lage_aus_daten(lage))
    m = sw.Maschine(pruefung, maschine_dok.getObject(aufnahme), einspannung, FreeCAD.Vector(*null))
    ergebnis = programm(dokument.getObject(op_name), m)
    return (
        [(c.Name, dict(c.Parameters)) for c in ergebnis.befehle],
        tuple(ergebnis.ausgelassen),
        tuple(ergebnis.materialdaten),
    )


def _inhalt(op, maschine, tcpm, bei_null):
    """Der Schlüssel für _PROGRAMME – alles, was die Umrechnung liest: Bahn und Achsen je Satz
    (als Prüfsumme), Grathöhe, Schneide, Fräser, Rohteil, die Kinematik (reichweite.Pruefung.
    kennung), Aufnahme, Einspannung und Nullpunkt. None, wenn sich einer nicht lesen lässt (dann
    rechnet es jedes Mal) – und für die Ansichten der Varianten (die haben ihren eigenen
    Speicher)."""
    import hashlib

    import numpy as np

    from . import angestellt as an
    from . import reichweite as rw
    from . import restmaterial as rm

    if maschine is None or getattr(op, "_pruefprogramm", None) is not None:
        return None
    try:
        h = hashlib.blake2b(digest_size=16)
        h.update(op.Path.toGCode().encode("utf-8"))
        achsen = [tuple(v) for v in getattr(op, "Werkzeugachsen", ())]
        h.update(np.asarray(achsen, dtype=float).tobytes())
        for name in ("BahnGrathoehe", "Schneide"):
            h.update(repr(getattr(op, name, None)).encode("utf-8"))
        h.update(repr(rm._fraeser(op.ToolController)).encode("utf-8"))
        rohteil = an.rohteil_von(op)
        if rohteil is not None and not rohteil.isNull():
            bb = rohteil.BoundBox
            h.update(
                repr((round(rohteil.Volume, 6), tuple(bb.getPoint(i) for i in (0, 6)))).encode()
            )
        einspannung = rw._einspannung(maschine.laenge)
        return (
            op.Name,
            h.hexdigest(),
            maschine.pruefung.kennung(),
            maschine.aufnahme.Name,
            float(einspannung.laenge),
            repr(einspannung.lage),
            tuple(maschine.nullpunkt),
            bool(tcpm),
            bool(bei_null),
        )
    except Exception:  # noqa: BLE001 – ohne Schlüssel eben ohne Speicher
        return None


def _programm_rechnen(op, maschine, tcpm, bei_null):
    """programm() ohne den Speicher."""
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
