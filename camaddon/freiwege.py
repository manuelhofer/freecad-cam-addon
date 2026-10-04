# SPDX-License-Identifier: LGPL-2.1-or-later
"""Im Freien schnell – für jede Strategie (Manuel, 2026-10-04: „wenn es frei ist und da kein
Material ist … muss ich nicht langsam fahren, gib Gas bis kurz davor, bevor es wieder langsam
weiter geht .. bei allen Strategien .. egal was das ist“).

Die Bahn (bahn.Punkt) wird im Materialstand vor der Operation abgefahren (restmaterial.Quader,
wie raeumen_bahn.last). Ein Stück im Vorschub auf gleicher Höhe ist frei, wenn im Umkreis
R + RAND um seinen Weg nichts über der Spitze steht – vorsichtig gerechnet: An einer Wand oder
über einem Aufmaß zählt das Teil selbst als Material, dort bleibt der Schnittvorschub. Freie
Stücke, zusammen mindestens MINDEST mm lang, fahren mit dem Freivorschub (G1 – ein G0 fährt
auf vielen Steuerungen keine Gerade); die letzten VORLAUF mm vor dem nächsten Material bleiben
langsam – das Bremsen davor macht die Vorausschau der Steuerung. Eilgänge, Eintauchen und
Rampen bleiben, wie sie sind; ein Bogen wird nur ganz schnell oder gar nicht.
"""

import math

import numpy as np

from . import bahn as bn
from . import fahrzeit as fz

FREIVORSCHUB = fz.EILGANG  # mm/min – ohne Maschine, wie „Adaptiv – schneller Freivorschub“
VORLAUF = 2.0  # mm vor dem Material bleibt der Schnittvorschub
MINDEST = 5.0  # mm – kürzere freie Stücke lohnen das Beschleunigen nicht
RAND = 1.0  # mm über den Radius hinaus muss es frei sein
SEHNE = 1.0  # mm – so fein wird nachgesehen
GLEICH = 0.05  # mm


def _frei(q, a, b, weite):
    """Steht im Umkreis `weite` um den Weg a → b (die Spitze) nichts über der Spitze?"""
    z = min(a[2], b[2])
    x0, x1 = min(a[0], b[0]) - weite, max(a[0], b[0]) + weite
    y0, y1 = min(a[1], b[1]) - weite, max(a[1], b[1]) + weite
    i0, i1 = np.searchsorted(q.x, x0), np.searchsorted(q.x, x1, side="right")
    j0, j1 = np.searchsorted(q.y, y0), np.searchsorted(q.y, y1, side="right")
    if i1 <= i0 or j1 <= j0:
        return True  # neben dem Rohteil
    h = q.h[i0:i1, j0:j1]
    hoch = h > z + GLEICH
    if not hoch.any():
        return True
    gx, gy = np.meshgrid(q.x[i0:i1], q.y[j0:j1], indexing="ij")
    dx, dy = b[0] - a[0], b[1] - a[1]
    laenge2 = dx * dx + dy * dy
    if laenge2 > 1e-12:
        t = np.clip(((gx - a[0]) * dx + (gy - a[1]) * dy) / laenge2, 0.0, 1.0)
    else:
        t = np.zeros_like(gx)
    abstand = np.hypot(gx - (a[0] + t * dx), gy - (a[1] + t * dy))
    return not bool((hoch & (abstand <= weite)).any())


def _sehnen(von, nach):
    """Die Sehnen von `von` nach `nach` (Bögen gesehnt), je höchstens SEHNE lang."""
    from . import materialstand as mst

    ergebnis = []
    for a, b in mst.sehnen(von, nach):
        n = max(1, int(math.ceil(math.dist(a[:2], b[:2]) / SEHNE)))
        for k in range(n):
            ergebnis.append(
                (
                    tuple(a[i] + (b[i] - a[i]) * k / n for i in range(3)),
                    tuple(a[i] + (b[i] - a[i]) * (k + 1) / n for i in range(3)),
                )
            )
    return ergebnis


def schneller(punkte, form, quader, vorschub, freivorschub=FREIVORSCHUB):
    """(Punkte, Weg in mm, der jetzt schnell fährt): die Bahn `punkte` mit dem Freivorschub
    (mm/min) auf den freien Stücken – `quader` (restmaterial.Quader, wird verändert) ist das
    Material vor der Operation, `vorschub` ihr Schnittvorschub (mm/min)."""
    if vorschub <= 0 or freivorschub <= vorschub * 1.01 or len(punkte) < 2:
        return list(punkte), 0.0
    anteil_frei = freivorschub / vorschub
    weite = float(form.radius) + RAND
    # 1. Abfahren: je Satz seine Sehnen, je Sehne (Länge, frei, kommt in Frage).
    saetze = []
    for von, nach in zip(punkte, punkte[1:], strict=False):
        sehnen = _sehnen(von, nach)
        frage = not nach.eilgang and not nach.eintauchen and abs(nach.z - von.z) <= GLEICH
        # Schon schneller als der Vorschub (ein Rückweg durchs Freie, den die Strategie geprüft
        # hat – raeumen_bahn, nut_bahn: RUECKWEG): frei.
        schon = frage and float(nach.anteil) > 1.0 + 1e-9
        # Je Satz gegen das Material vor ihm geprüft (was er selbst wegnimmt, zählt noch – das
        # ist vorsichtiger), dann auf einmal abgetragen.
        eintraege = [
            [a, b, math.dist(a[:2], b[:2]), frage and (schon or _frei(quader, a, b, weite))]
            for a, b in sehnen
        ]
        if not nach.eilgang and sehnen:
            quader.fahre_stuecke([a for a, _b in sehnen], [b for _a, b in sehnen], form)
        saetze.append((frage, eintraege))
    # 2. Rückwärts: wie weit bis zum nächsten Material (ein Eilgang beendet die Fahrt); vorwärts:
    # wie lang das freie Stück ist, in dem eine Sehne liegt.
    flach = [e for _f, eintraege in saetze for e in eintraege]
    grenze = []
    for (_f, eintraege), nach in zip(saetze, punkte[1:], strict=True):
        grenze.extend([nach.eilgang] * len(eintraege))
    bis = [0.0] * len(flach)
    weiter = math.inf
    for k in range(len(flach) - 1, -1, -1):
        if grenze[k]:
            weiter = math.inf
        elif not flach[k][3]:
            weiter = 0.0
        bis[k] = weiter
        if not grenze[k] and flach[k][3]:
            weiter += flach[k][2]
    lauf = [0.0] * len(flach)
    k = 0
    while k < len(flach):
        if not flach[k][3]:
            k += 1
            continue
        m = k
        while m < len(flach) and flach[m][3]:
            m += 1
        summe = sum(e[2] for e in flach[k:m])
        for i in range(k, m):
            lauf[i] = summe
        k = m
    schnell_flags = [
        flach[i][3] and lauf[i] >= MINDEST and bis[i] >= VORLAUF for i in range(len(flach))
    ]
    # 3. Neue Punkte: ein Satz, wo schnell und langsam wechseln, geteilt (Geraden); ein Bogen
    # nur ganz.
    neu = [punkte[0]]
    schnell_weg = 0.0
    k = 0
    for (frage, eintraege), nach in zip(saetze, punkte[1:], strict=True):
        flags = schnell_flags[k : k + len(eintraege)]
        k += len(eintraege)
        if not frage or not any(flags):
            neu.append(nach)
            continue
        if nach.bogen is not None:
            if all(flags):
                anteil = max(anteil_frei, float(nach.anteil))
                neu.append(bn.Punkt(False, nach.x, nach.y, nach.z, False, nach.bogen, anteil))
                schnell_weg += sum(e[2] for e in eintraege)
            else:
                neu.append(nach)
            continue
        for i, (_a, b, _laenge, _ist_frei) in enumerate(eintraege):
            letzte = i == len(eintraege) - 1
            if not letzte and flags[i] == flags[i + 1]:
                continue
            anteil = max(anteil_frei, float(nach.anteil)) if flags[i] else float(nach.anteil)
            neu.append(bn.Punkt(False, b[0], b[1], nach.z, False, None, anteil))
        schnell_weg += sum(e[2] for e, f in zip(eintraege, flags, strict=True) if f)
    return neu, schnell_weg


def fuer_operation(job, op, punkte, vorschub, form=None, freivorschub=None):
    """schneller() für die Operation `op` im Job: das Material vor ihr (materialstand), ihr
    Fräser – unverändert ohne Rohteil im Quader oder ohne Form."""
    from . import materialstand as mst
    from . import vierachs_schlichten as vs

    if form is None:
        form = vs.form_des_controllers(getattr(op, "ToolController", None))
    stand = mst.fuer(job, vor=op) if form is not None else None
    if stand is None:
        return list(punkte), 0.0
    quader = mst._kopie(stand).quader
    return schneller(punkte, form, quader, vorschub, freivorschub or FREIVORSCHUB)
