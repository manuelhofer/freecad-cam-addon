# SPDX-License-Identifier: LGPL-2.1-or-later
"""Erreichbare Teilstrecken nur an vorhandenen materialfreien Bahnstellen trennen.

Ein-/Ausfahrten werden außerhalb des ursprünglichen Rohteils konstruiert. Die
vollständige neu kompilierte Maschinenbahn prüft der Aufrufer anschließend mit
simultan_bereiche gegen Grenzen und kontinuierliche BRep-Kollision. Die lokale
Punktprüfung ist nur eine Vorauswahl, keine Freigabe der Verbindung.
"""

from dataclasses import replace

import FreeCAD as App

from . import halter as hl
from . import job_schnittwerte as js
from . import kollision as kb
from . import maschinenzugang as mz
from . import reichweite as rw
from . import simultan as si
from .kinematik import Kinematik
from .sprache import tr

MAX_PUNKTE = 20000
MAX_BEREICHE = 64


def unterteilen(op, job, maschine, punkte, von, bis, bezug, toleranz, bibliothek):
    """Erreichbare Indexpaare mit materialfreien Enden, sonst keine Teilfreigabe.

    Ganze Quellsegmente bleiben erhalten. Unbekannte Werkzeug-/Haltergeometrie oder
    überschrittenes Suchbudget sind ein Fehler, kein angenommener freier Raum.
    """
    if bis - von + 1 > MAX_PUNKTE:
        raise ValueError(tr("sb.fehler.budget"))
    tc = op.ToolController
    w = js.werkzeug_von(tc, bibliothek)
    halter = rw.werkzeughalter(tc, bibliothek)
    if w is None or halter is None or hl.ist_vorschlag(halter) or hl.form(halter) is None:
        raise ValueError(tr("sb.fehler.geometrie"))
    ein = rw._einspannung(maschine.laenge)
    koerper = kb.werkzeugkoerper(rw.werkzeugmasse(tc, bibliothek, ein.laenge), ein.laenge, halter)
    if not koerper:
        raise ValueError(tr("sb.fehler.geometrie"))
    kin = Kinematik(maschine.pruefung, maschine.aufnahme, maschine.laenge, maschine.nullpunkt)
    gesehen = {}

    def lage(states):
        p = maschine.pruefung
        wege = kin._wege(states, rundachsen=True)
        return (
            p._job_lage(maschine.nullpunkt, wege)
            .inverse()
            .multiply(
                p._glied_lage(p._glied(maschine.aufnahme), wege).multiply(
                    p._lage(maschine.aufnahme)
                )
            )
        )

    def stellung(c):
        werte = c.Parameters
        rund = {a.buchstabe: werte[a.buchstabe] for a in maschine.rundachsen}
        return kin.stellungen(tuple(werte[k] for k in "XYZ"), rund)

    def frei(i):
        if i not in gesehen:
            try:
                c = si.programm_ohne_tcpm(maschine, [punkte[i]], toleranz=None)[0]
                if mz.bahn_grund(maschine, [c], op.Label):
                    gesehen[i] = False
                    return False
                states = stellung(c)
                if states is None:
                    gesehen[i] = False
                    return False
                pose = lage(states)
                gesehen[i] = True
                for _art, form in koerper:
                    echt = form.copy()
                    echt.Placement = pose.multiply(form.Placement)
                    if echt.distToShape(job.Stock.Shape)[0] <= kb.WARNABSTAND:
                        gesehen[i] = False
                        break
            except ValueError:
                gesehen[i] = False
        return gesehen[i]

    def schneidet(a, b):
        # Nur verbleibende Luftfahrt ist kein sinnvoller Teilbereich. Eine native
        # Schneide im Rohteil beweist einen Schnitt; die Stichprobe darf nur ablehnen,
        # niemals eine neue Einfahrt im Material freigeben.
        data = []
        nc = si.programm_ohne_tcpm(
            maschine,
            punkte[a : b + 1],
            toleranz=toleranz,
            bezug=bezug,
            eilgaenge=True,
            materialdaten=data,
        )
        s = stellung(nc[0])
        box = job.Stock.Shape.BoundBox
        for c, (eil, _feed) in zip(nc[1:], data[1:], strict=True):
            t = stellung(c)
            if not eil and s is not None and t is not None:
                for stand in (s, {ax: (s[ax] + t[ax]) / 2 for ax in s}, t):
                    pose = lage(stand)
                    for art, form in koerper:
                        if art != kb.SCHNEIDE:
                            continue
                        echt = form.copy()
                        echt.Placement = pose.multiply(form.Placement)
                        bb = echt.BoundBox
                        if (
                            bb.XMax <= box.XMin
                            or bb.XMin >= box.XMax
                            or bb.YMax <= box.YMin
                            or bb.YMin >= box.YMax
                            or bb.ZMax <= box.ZMin
                            or bb.ZMin >= box.ZMax
                        ):
                            continue
                        if echt.common(job.Stock.Shape).Volume > 1e-7:
                            return True
            s = t
        return False

    # Ganze erreichbare Intervalle einmal rechnen. Nur gesperrte Intervalle
    # halbieren: bei langen Bahnen keine inverse Kinematik je Segment neu starten.
    kanten, arbeit = set(), 0

    def pruefen(a, b):
        nonlocal arbeit
        arbeit += b - a + 1
        if arbeit > MAX_PUNKTE * 8:
            raise ValueError(tr("sb.fehler.budget"))
        try:
            nc = si.programm_ohne_tcpm(
                maschine,
                punkte[a : b + 1],
                g93=True,
                toleranz=toleranz,
                bezug=bezug,
                eilgaenge=True,
            )
            gueltig = not mz.bahn_grund(maschine, nc, op.Label)
        except ValueError:
            gueltig = False
        if gueltig:
            kanten.update(range(a + 1, b + 1))
        elif b - a > 1:
            mitte = (a + b) // 2
            pruefen(a, mitte)
            pruefen(mitte, b)

    pruefen(von, bis)
    gruppen, anfang = [], None
    for i in range(von + 1, bis + 1):
        gueltig = i in kanten
        if gueltig and anfang is None:
            anfang = i - 1
        if not gueltig and anfang is not None:
            gruppen.append((anfang, i - 1))
            anfang = None
    if anfang is not None:
        gruppen.append((anfang, bis))
    if len(gruppen) > MAX_BEREICHE:
        raise ValueError(tr("sb.fehler.budget"))
    result = []
    for a, b in gruppen:
        while a < b and not frei(a):
            a += 1
        while b > a and not frei(b):
            b -= 1
        if a < b and schneidet(a, b):
            result.append((a, b))
    return result


def verbindung(von, nach, rohteil):
    """Kandidat für Ausfahren, Umsetzen und Einfahren längs beider Werkzeugachsen.

    Die höchste Rohteilecke in Achsrichtung und der vorhandene Schwenkrand geben
    die Rückzugslänge. Das ist eine Konstruktion, keine Kollisionszusage; selbst
    freie Endpunkte können einen unzulässigen Zwischenweg haben.
    """
    from . import schwenken as sw

    box = rohteil.BoundBox
    ecken = [
        App.Vector(x, y, z)
        for x in (box.XMin, box.XMax)
        for y in (box.YMin, box.YMax)
        for z in (box.ZMin, box.ZMax)
    ]

    def draussen(p):
        tip, achse = App.Vector(*p.spitze), App.Vector(*p.achse)
        achse.normalize()
        weg = max(0.0, max((e - tip).dot(achse) for e in ecken) + sw.SCHWENK_RAND)
        return replace(p, spitze=tuple(tip + weg * achse), eilgang=True, verbindung=True)

    return [
        replace(von, eilgang=True, verbindung=True),
        draussen(von),
        draussen(nach),
        replace(nach, eilgang=True, verbindung=True),
    ]
