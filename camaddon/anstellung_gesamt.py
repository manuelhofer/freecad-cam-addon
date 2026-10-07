# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die freie Werkzeugrichtung über die gesamte bekannte Bahn voraussehen.

Ein kürzester Weg durch endliche Richtungen minimiert die Summe der Winkeländerungen.
Diese geometrische Zielfunktion ist kein Maschinenzeitmodell. Der Simultanvergleich
bewertet diesen zusätzlichen Kandidaten danach mit der wirklichen Maschinenfahrt und
denselben unabhängigen Sicherheits-/Qualitätsprüfungen wie die örtliche freie Richtung.
"""

import math

import numpy as np

from . import angestellt as an
from . import anstellung_frei as af
from .sprache import tr


def kandidaten(normalen, winkel):
    """Acht Kegelrichtungen, freie Vor-/Rückfolge und erlaubte Senkrechte je Stelle."""
    n = np.asarray(normalen, dtype=float).copy()
    n /= np.linalg.norm(n, axis=1)[:, None]
    basis = np.tile((1.0, 0.0, 0.0), (len(n), 1))
    basis[np.abs(n[:, 0]) > 0.9] = (0.0, 1.0, 0.0)
    u = basis - np.sum(basis * n, axis=1)[:, None] * n
    u /= np.linalg.norm(u, axis=1)[:, None]
    v = np.cross(n, u)
    phi = np.arange(8) * (math.tau / 8)
    c, s = math.cos(math.radians(winkel + 2)), math.sin(math.radians(winkel + 2))
    kegel = c * n[:, None, :] + s * (
        np.cos(phi)[None, :, None] * u[:, None, :] + np.sin(phi)[None, :, None] * v[:, None, :]
    )
    vorwaerts = np.asarray(af.richtungen(n, winkel + 2))[:, None, :]
    rueckwaerts = np.asarray(af.richtungen(n[::-1], winkel + 2))[::-1, None, :]
    senkrecht = np.tile(an.SENKRECHT, (len(n), 1, 1))
    return np.concatenate((kegel, vorwaerts, rueckwaerts, senkrecht), axis=1)


def verbindungen(vorher, danach, normale_vor, normale_nach, winkel):
    """Winkelkosten; unerlaubte Kontaktwinkel in der interpolierten Mitte kosten unendlich."""
    kosten = np.arccos(np.clip(vorher @ danach.T, -1, 1))
    mitte = vorher[:, None, :] + danach[None, :, :]
    laenge = np.linalg.norm(mitte, axis=2)
    n = normale_vor + normale_nach
    if np.linalg.norm(n) < 1e-9:
        return np.full(kosten.shape, math.inf)
    n /= np.linalg.norm(n)
    skalar = np.sum(mitte * n, axis=2) / np.maximum(laenge, 1e-12)
    # Der genaue CAD-Kontakt zwischen den Punkten bleibt eine unabhängige Zulassung.
    erlaubt = (
        (laenge > 1e-9)
        & (skalar <= math.cos(math.radians(winkel + 0.5)))
        & (skalar >= math.cos(math.radians(85)))
    )
    return np.where(erlaubt, kosten, math.inf)


def kuerzester_weg(knoten, normalen, winkel, fortschritt=None):
    """Indexfolge und Winkelaufwand des global kürzesten Wegs in diesem Richtungsgraphen."""
    erlaubte = np.sum(knoten * normalen[:, None, :], axis=2)
    erlaubte = (erlaubte <= math.cos(math.radians(winkel))) & (
        erlaubte >= math.cos(math.radians(85))
    )
    kosten = np.arccos(np.clip(knoten[0, :, 2], -1, 1))
    kosten[~erlaubte[0]] = math.inf
    vorgaenger = np.zeros(knoten.shape[:2], dtype=np.uint8)
    for i in range(1, len(knoten)):
        matrix = kosten[:, None] + verbindungen(
            knoten[i - 1], knoten[i], normalen[i - 1], normalen[i], winkel
        )
        vorgaenger[i] = np.argmin(matrix, axis=0)
        kosten = np.min(matrix, axis=0)
        kosten[~erlaubte[i]] = math.inf
        if fortschritt is not None and i % 256 == 0 and not fortschritt(i / len(knoten)):
            raise ValueError(tr("s5p.fehler.unvollstaendig"))
    kosten += np.arccos(np.clip(knoten[-1, :, 2], -1, 1))
    ende = int(np.argmin(kosten))
    if not math.isfinite(float(kosten[ende])):
        raise ValueError(tr("s5p.fehler.richtungsfolge"))
    folge = np.empty(len(knoten), dtype=np.uint8)
    folge[-1] = ende
    for i in range(len(knoten) - 1, 0, -1):
        folge[i - 1] = vorgaenger[i, folge[i]]
    return folge, float(kosten[ende])


def richtungen(normalen, winkel=an.WINKEL, fortschritt=None):
    """Die ganze Richtungsfolge gemeinsam planen; fehlende Luftnormalen weiterführen."""
    if len(normalen) == 0:
        return []
    n, davor = [], an.SENKRECHT
    for normale in an.vorausblick(normalen):
        if normale is not None:
            davor = normale
        n.append(davor)
    n = np.asarray(n, dtype=float)
    n /= np.linalg.norm(n, axis=1)[:, None]
    k = kandidaten(n, winkel)
    folge, _kosten = kuerzester_weg(k, n, winkel, fortschritt)
    return [tuple(a) for a in k[np.arange(len(k)), folge]]
