# SPDX-License-Identifier: LGPL-2.1-or-later
"""Stößt beim 4-Achs-Fräsen der Halter ans Teil? – schon im Assistenten, bevor es die Operationen
gibt (Manuel, 2026-10-11, Frage 7: „sehr klar darauf hinweisen das die ausspannlänge des fräsers
nicht ausreicht“; „effektives ziel sollte schon sein das die maschine in die kollisions
überwachung mit einfliest“).

„Kollision prüfen“ fand am Nasen-Testteil mit der CLX550 nach drei Minuten: der Halter von T1
(44 mm heraus) bräuchte 48 mm, der von T2 (18 mm) 31 mm. Hier dieselbe Frage ohne Maschine, aus
den Bahnen der Vorschau: je Satz (a, r, q, φ) die Spitze und die Werkzeugachse im Teil (wie das
Voxelmodell, voxelstange), die Körper über der Schneide längs der Werkzeugachse – Hals, Schaft und
die Abschnitte des Halters, auch beim gewinkelten (dessen Kopf liegt längs der Aufnahme: Wohin er
zeigt, weiß nur die Maschine, ihn prüft „Kollision prüfen“) – als Kapseln gegen das Netz des Teils
(flanke_bahn.halter_an_stellen: etwa jeden Millimeter eine Stelle, für die anstoßenden eine
Halbierung, wie weit heraus es frei wäre). Die Stellen in Stücken auf den Nebenrechnern
(stueck_an; das Teil einmal je Arbeiter, sein Netz dort gemerkt). Läuft ohne Oberfläche.
"""

import copy
import hashlib

import numpy as np

from . import flanke_bahn as fb

VERTEILT_AB = 400  # ausgewählte Stellen: ab so vielen auf den Nebenrechnern
STELLEN_JE_STUECK = 300

_NETZE = {}  # im Arbeiter: Schlüssel des Teils -> sein Netz (nur das letzte)


def _rahmen(laengs, radial):
    l_ = np.array([float(c) for c in laengs], dtype=float)
    u = np.array([float(c) for c in radial], dtype=float)
    l_ /= np.linalg.norm(l_)
    u -= l_ * float(u @ l_)
    u /= np.linalg.norm(u)
    return l_, u, np.cross(l_, u)


def stellen(saetze, eilgang, laengs, radial):
    """(Spitzen, Werkzeugachsen zur Spindel, a) je Satz ohne Eilgang – `saetze` (n, 4): a, r, q,
    φ in Grad (voxelstange.als_feld); im Teil: a längs, die Spitze bei r längs der Werkzeugachse
    unter dem Winkel φ, quer um q versetzt."""
    l_, u_, v_ = _rahmen(laengs, radial)
    s = np.asarray(saetze, dtype=float).reshape(-1, 4)
    s = s[~np.asarray(eilgang, dtype=bool)]
    psi = np.radians(s[:, 3])
    c, sn = np.cos(psi), np.sin(psi)
    y = s[:, 1] * c - s[:, 2] * sn
    z = s[:, 1] * sn + s[:, 2] * c
    spitzen = s[:, 0, None] * l_ + y[:, None] * u_ + z[:, None] * v_
    achsen = c[:, None] * u_ + sn[:, None] * v_
    return spitzen, achsen, s[:, 0]


def koerper(werkzeug, bibliothek):
    """[(von, bis, Radius)] längs der Werkzeugachse ab der Spitze (mm): Hals, Schaft und Halter
    des Werkzeugs der Werkzeugverwaltung wie „Kollision prüfen“ (kollision.werkzeugkapseln) – beim
    gewinkelten Halter seine Abschnitte längs der Werkzeugachse ohne den Kopf. Leer ohne
    Werkzeugverwaltung oder Durchmesser."""
    from . import halter as hl
    from . import kollision as kb
    from . import reichweite as rw

    if bibliothek is None or werkzeug is None or not werkzeug.durchmesser:
        return []
    halter = bibliothek.halter_fuer_pruefung(werkzeug)
    if halter is not None and halter.gewinkelt:
        halter = copy.copy(halter)
        halter.richtung = hl.GERADE  # die Abschnitte auf der Werkzeugachse, ohne den Kopf
    laenge, _quelle = rw.laenge_des_werkzeugs(werkzeug, bibliothek)
    kapseln = kb.werkzeugkapseln(rw.masse_des_werkzeugs(werkzeug), laenge, halter)
    return [
        (p0[2] + laenge, p1[2] + laenge, r)
        for art in (kb.HALS, kb.SCHAFT, kb.HALTER)
        for p0, p1, r, _flach in kapseln.get(art, ())
    ]


def stueck(ecken, schluessel, spitzen, achsen, teile):
    """Auch im Nebenrechner: (Indizes der Stellen, die anstoßen, so viel weiter heraus wäre es
    dort frei) – flanke_bahn.noetig_weiter am Teil, dessen Dreiecke `ecken` sind
    (netzabstand.dreiecke). Sein Netz bleibt für die nächsten Stücke gemerkt (`schluessel`)."""
    from . import netzabstand as na

    netz = _NETZE.get(schluessel)
    if netz is None:
        _NETZE.clear()
        netz = _NETZE[schluessel] = na.Netz(None, fb.HALTER_NETZ, ecken=ecken)
    return fb.noetig_weiter(
        netz, np.asarray(spitzen, dtype=float), np.asarray(achsen, dtype=float), teile
    )


def _verteilt(form, spitzen, achsen, teile):
    """stueck() in Stücken auf den Nebenrechnern – (Indizes, weiter) über alle; None ohne sie,
    bei wenigen Stellen oder wenn sie scheitern."""
    try:
        from . import nebenrechner as nr
    except ImportError:
        return None
    from . import netzabstand as na

    if len(spitzen) < VERTEILT_AB:
        return None
    try:
        pool = nr.pool()
        if not pool.verfuegbar() or pool.anzahl < 2:
            return None
        # Einmal hier vernetzt, die Dreiecke an alle (P-2026-10-11-100): Bis dahin bekam jeder
        # Nebenrechner die Form und vernetzte sie selbst – am Geist aus einem STL (68.242 Flächen)
        # je 1,5 GB, 24-mal.
        ecken = na.dreiecke(form, fb.HALTER_NETZ)
        schluessel = "vh-teil-" + hashlib.sha1(np.ascontiguousarray(ecken).tobytes()).hexdigest()
        teil = pool.gemeinsam(schluessel, ecken)
        bereiche = nr.stuecke(
            len(spitzen), pool.anzahl, je_arbeiter=3, mindestens=STELLEN_JE_STUECK
        )
        auftraege = [
            pool.auftrag(
                "vierachs_halter", "stueck", teil, schluessel, spitzen[v:b], achsen[v:b], teile
            )
            for v, b in bereiche
        ]
        ergebnisse = pool.warten(auftraege, zwischendurch=nr.ereignisse_ohne_eingaben)
        pool.vergessen(schluessel)
    except nr.Fehler:
        return None
    an = np.concatenate([idx + v for (idx, _w), (v, _b) in zip(ergebnisse, bereiche, strict=True)])
    weiter = np.concatenate([w for _idx, w in ergebnisse])
    return an.astype(np.int64), weiter


def pruefen(form, saetze, eilgang, laengs, radial, koerper_, radius):
    """(Stellen, heraus, mindestens, a von, a bis) oder None: Stoßen die Körper über der Schneide
    (`koerper_`, koerper()) irgendwo längs der Bahn (die Sätze ohne Eilgang) ans Teil `form`? –
    `heraus`: so weit steht das Werkzeug heraus (bis zum ersten dickeren Körper), `mindestens`:
    so weit müsste es, damit nichts anstößt; a von … bis: wo längs. Etwa jeden Millimeter eine
    Stelle (flanke_bahn.ausgewaehlt), in Stücken auf den Nebenrechnern."""
    from . import netzabstand as na

    teile = fb.dickere_koerper(koerper_, radius)
    if not teile:
        return None
    spitzen, achsen, a = stellen(saetze, eilgang, laengs, radial)
    if not len(spitzen):
        return None
    waehle = fb.ausgewaehlt(spitzen)
    spitzen, achsen, a = spitzen[waehle], achsen[waehle], a[waehle]
    ergebnis = _verteilt(form, spitzen, achsen, teile)
    if ergebnis is None:
        ergebnis = fb.noetig_weiter(na.Netz(form, fb.HALTER_NETZ), spitzen, achsen, teile)
    an, weiter = ergebnis
    if not len(an):
        return None
    heraus = min(t[0] for t in teile)
    wo = a[an]
    return (len(an), heraus, heraus + float(weiter.max()), float(wo.min()), float(wo.max()))
