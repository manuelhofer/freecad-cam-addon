# SPDX-License-Identifier: LGPL-2.1-or-later
"""Erreichbare vollständige Schnittzüge behalten; neue Verbindungen ausdrücklich prüfen.

Getrennt wird an vorhandenen Eilgängen oder nachweislich materialfreien Bahnstellen.
Keine Einfahrt im Material und keine Begrenzung einer Werkzeugrichtung. Die Kollisionsprüfung sieht
die wirklichen verdichteten NC-Sätze, einschließlich drehender G93-Eilfahrten.
Die Quelle bleibt unverändert; ohne Rohteil, Halter oder sichere Verbindung wird
kein Teilprogramm freigegeben. Läuft ohne Oberfläche.
"""

from dataclasses import replace
from types import SimpleNamespace

import Path

from . import angestellt as an
from . import maschinenzugang as mz
from . import simultan as si
from .sprache import tr


class _Ansicht:
    """Lokale Attribute vor der unveränderten CAM-Quelle lesen."""

    def __init__(self, quelle, **werte):
        self._quelle = quelle
        self.__dict__.update(werte)

    def __getattr__(self, name):
        return getattr(self._quelle, name)


def _zuege(punkte):
    """Indexpaare vom letzten Eilpunkt vor bis zum ersten Eilpunkt nach jedem Schnitt."""
    result, anfang = [], None
    for i, p in enumerate(punkte):
        if not p.eilgang and anfang is None:
            if i == 0:
                raise ValueError(tr("sb.fehler.trennung"))
            anfang = i - 1
        elif p.eilgang and anfang is not None:
            result.append((anfang, i))
            anfang = None
    if anfang is not None or not result:
        raise ValueError(tr("sb.fehler.trennung"))
    return result


def _punkte(op):
    from . import flanke as fl

    cmds = list(op.Path.Commands)
    achsen = [tuple(a) for a in op.Werkzeugachsen]
    if len(cmds) != len(achsen):
        raise ValueError(tr("an.fehler.veraltet", operation=op.Label))
    # Die gespeicherten Adapter unterstützen hier absolute Geraden. Andere Modi
    # dürfen bei einer Unterteilung nicht unbemerkt ihren Modalzustand verlieren.
    if any(
        c.Name.upper() not in ("G0", "G00", "G1", "G01") and not c.Name.startswith("(")
        for c in cmds
    ):
        raise ValueError(tr("sb.fehler.trennung"))
    if an.ist_angestellt(op):
        radius = an.radius_von(op)
        if radius is None:
            raise ValueError(tr("an.fehler.kugel", operation=op.Label))
        pts, bezug = an.punkte(cmds, achsen, radius), radius
    else:
        schneide = float(getattr(op, "Schneide", 0) or 0)
        pts, bezug = fl.punkte(cmds, achsen), (0.0, schneide) if schneide else 0.0
    # Auch ein Vorschubwechsel im später ausgelassenen Zug ist modal wirksam.
    # Jeder behaltene Punkt muss seinen tatsächlichen ursprünglichen Vorschub tragen.
    vorschub, result = 0.0, []
    for p in pts:
        vorschub = p.vorschub if p.vorschub > 0 else vorschub
        result.append(replace(p, vorschub=vorschub))
    return result, bezug


def _verbindungen(cmds, flags):
    """Exakte NC-Abschnitte neuer Eilfahrten, mit ihrem vollständigen Anfangszustand."""
    stand, gruppe = {}, []
    for c, neu in zip(cmds, flags, strict=True):
        if not neu and gruppe:
            yield gruppe + [Path.Command("G94")]
            gruppe = []
        if neu and not gruppe:
            if not all(k in stand for k in "XYZ"):
                raise ValueError(tr("sb.fehler.trennung"))
            gruppe = [Path.Command("G0", dict(stand)), Path.Command("G93")]
        if neu:
            gruppe.append(c)
        if c.Name in ("G0", "G1"):
            stand.update({k: v for k, v in c.Parameters.items() if k in "XYZABC"})
    if gruppe:
        yield gruppe + [Path.Command("G94")]


def _verbindung_pruefen(op, job, maschine, cmds, bibliothek):
    """Bestehende kontinuierliche BRep-Prüfung auf Rohteil und komplette Maschine anwenden."""
    from . import abfahren as ab
    from . import kollision as kb
    from . import simultan_operation as so

    view = _Ansicht(op, _pruefprogramm=(so.pruefschluessel(maschine), cmds))
    j = _Ansicht(
        job,
        Operations=SimpleNamespace(Group=[view]),
        Model=SimpleNamespace(Group=[SimpleNamespace(Shape=job.Stock.Shape)]),
    )
    fahrt = ab.abfahrt(maschine.pruefung, j, maschine.nullpunkt, bibliothek)
    if not fahrt.operationen or fahrt.hinweise:
        raise ValueError(tr("sb.fehler.verbindung"))
    # G93 wandelt drehende G0 in G1 um. Hier ist trotzdem jede Bewegung Eilgang:
    # auch die Schneide muss das ganze ursprüngliche Rohteil freihalten.
    for s in fahrt.stationen:
        s.eilgang = True
    k = kb.kollision(fahrt, j, maschine.nullpunkt, bibliothek)
    if k.abgebrochen or k.hinweise or k.befunde:
        grund = (
            str(k.hinweise[0])
            if k.hinweise
            else (k.befunde[0].text() if k.befunde else tr("sb.fehler.verbindung"))
        )
        raise ValueError(grund)
    return fahrt.dauer


def _neue_verbindung(op, job, maschine, von, nach, bezug, toleranz, bibliothek):
    """Die schnellere geprüfte direkte oder achsparallele Verbindung verwenden."""
    from . import simultan_schnittbereiche as schnitt

    direkt = [replace(p, eilgang=True, verbindung=True) for p in (von, nach)]
    moeglich, fehler = [], []
    for route in (direkt, schnitt.verbindung(von, nach, job.Stock.Shape)):
        try:
            nc = si.programm_ohne_tcpm(
                maschine, route, g93=True, toleranz=toleranz, bezug=bezug, eilgaenge=True
            )
            grund = mz.bahn_grund(maschine, nc, op.Label)
            if grund:
                raise ValueError(grund)
            dauer = _verbindung_pruefen(op, job, maschine, nc, bibliothek)
            moeglich.append((dauer, route))
        except ValueError as e:
            fehler.append(str(e))
    if not moeglich:
        raise ValueError("; ".join(dict.fromkeys(fehler)))
    return min(moeglich, key=lambda x: x[0])[1]


def teilen(op, maschine, ursache):
    """(NC-Sätze, ausgelassene Schnittzüge): nur mit vollständig geprüften neuen Verbindungen.

    Nicht materialfrei trennbare Bereiche bleiben stehen. Fehlt eine zulässige Verbindung,
    wird das Teilprogramm als Ganzes zurückgewiesen. Keine Dokumentmutation.
    """
    from . import simultan_planung as sp
    from . import werkzeuge as wz

    quelle = op
    while hasattr(quelle, "_quelle"):
        quelle = quelle._quelle
    job = sp.job_von(quelle)
    if job is None or getattr(getattr(job, "Stock", None), "Shape", None) is None:
        raise ValueError(ursache)
    pts, bezug = _punkte(op)
    zuege = _zuege(pts)
    tol = min(si.TOLERANZ, 0.00025) if float(getattr(op, "BahnGrathoehe", 0)) > 0 else si.TOLERANZ
    behalten, ausgelassen = [], []
    bib = None
    for nummer, (a, b) in enumerate(zuege, 1):
        try:
            nc = si.programm_ohne_tcpm(
                maschine, pts[a : b + 1], g93=True, toleranz=tol, bezug=bezug, eilgaenge=True
            )
            grund = mz.bahn_grund(maschine, nc, op.Label)
            if grund:
                raise ValueError(grund)
            behalten.append((a, b))
        except ValueError as fehler:
            from . import simultan_schnittbereiche as schnitt

            if bib is None:
                bib = wz.Bibliothek.laden()
            try:
                teile = schnitt.unterteilen(op, job, maschine, pts, a, b, bezug, tol, bib)
            except ValueError as einfahrt:
                teile = []
                fehler = ValueError(f"{fehler}; {einfahrt}")
            if not teile:
                ausgelassen.append((nummer, str(fehler)))
                continue
            behalten.extend(teile)
            ende = a
            for c, d in [*teile, (b, b)]:
                if c > ende:
                    ausgelassen.append(
                        (tr("sb.zug.teil", zug=nummer, von=ende + 1, bis=c + 1), str(fehler))
                    )
                ende = d
    if not behalten or not ausgelassen:
        raise ValueError("; ".join(g for _n, g in ausgelassen) or ursache)
    # Anfang und Ende der ursprünglichen Operation erhalten: keine unqualifizierte
    # neue globale Schwenkhöhe oder Werkzeugwechselposition konstruieren.
    ids = set(range(zuege[0][0] + 1)) | set(range(zuege[-1][1], len(pts)))
    for a, b in behalten:
        ids.update(range(a, b + 1))
    schnittkanten = {i for a, b in behalten for i in range(a + 1, b + 1)}
    zugkanten = {i for a, b in zuege for i in range(a + 1, b + 1)}
    neu, letzter = [], None
    for i in sorted(ids):
        p = pts[i]
        luecke = letzter is not None and (
            i > letzter + 1 or (i in zugkanten and i not in schnittkanten)
        )
        if luecke and not (pts[letzter].eilgang and p.eilgang):
            route = _neue_verbindung(op, job, maschine, pts[letzter], p, bezug, tol, bib)
            # Der vorherige Zustand ist schon vorhanden. Der Wiedereintrittspunkt
            # kommt als Eilgang; jeder folgende Quellpunkt trägt seinen modalen F.
            neu.extend(route[1:])
        else:
            neu.append(replace(p, verbindung=luecke))
        letzter = i
    flags = []
    nc = si.befehle_auf_maschine(
        maschine,
        neu,
        job.Stock.Shape,
        bezug,
        toleranz=tol,
        materialdaten=getattr(op, "_pruefmaterial", None),
        verbindungen=flags,
    )
    grund = mz.bahn_grund(maschine, nc, op.Label)
    if grund:
        raise ValueError(grund)
    if bib is None:
        bib = wz.Bibliothek.laden()
    for verbindung in _verbindungen(nc, flags):
        _verbindung_pruefen(op, job, maschine, verbindung, bib)
    return nc, tuple(ausgelassen)
