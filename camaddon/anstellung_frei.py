# SPDX-License-Identifier: LGPL-2.1-or-later
"""Kugel anstellen, ohne die Kippbewegung auf eine Ebene zu beschränken.

Die vorige Richtung bleibt, solange der Mindestwinkel zur Kontaktfläche reicht.
Sonst wird sie auf den Rand des erlaubten Kegels projiziert. Die Kugelmitte
bleibt unverändert. Das ist ein Kandidat für den Vergleich, kein Nachweis
über Halterfreiheit oder Erreichbarkeit; das prüft simultan_planung separat.
"""

import math

import numpy as np

from . import angestellt as an


def richtungen(normalen, winkel=an.WINKEL):
    """Stetig möglichst wenig von der vorigen Richtung abweichen, Kontaktwinkel einhalten."""
    c, s = math.cos(math.radians(winkel)), math.sin(math.radians(winkel))
    davor = np.array(an.SENKRECHT)
    ergebnis = []
    for normale in normalen:
        if normale is not None:
            n = np.array(normale, dtype=float)
            n /= np.linalg.norm(n)
            skalar = float(davor @ n)
            if skalar > c:
                quer = davor - skalar * n
                if np.linalg.norm(quer) < 1e-9:
                    basis = np.array([0.0, -1.0, 0.0])
                    if abs(float(basis @ n)) > 0.9:
                        basis = np.array([1.0, 0.0, 0.0])
                    quer = basis - float(basis @ n) * n
                quer /= np.linalg.norm(quer)
                davor = c * n + s * quer
        ergebnis.append(tuple(float(a) for a in davor))
    return ergebnis


def achsen(
    befehle,
    form,
    radius,
    aufmass=0.0,
    winkel=an.WINKEL,
    normalen_cache=None,
    fortschritt=None,
    *,
    gesamt=False,
):
    """Werkzeugachsen je Satz; Eilgänge heben mit der bisherigen Richtung ab."""
    stellen, stand = [], [None, None, None]
    for i, befehl in enumerate(befehle):
        name = befehl.Name.upper()
        if name not in an.BEWEGUNG:
            continue
        stand = [
            float(befehl.Parameters.get(k, stand[j])) if k in befehl.Parameters else stand[j]
            for j, k in enumerate("XYZ")
        ]
        if None not in stand:
            stellen.append((i, tuple(stand), name in an.EILGANG))
    schnitte = [s for s in stellen if not s[2]]
    normalen = an.vorausblick(
        an.normalen(
            form,
            [p for _i, p, _e in schnitte],
            radius,
            aufmass,
            cache=normalen_cache,
            fortschritt=fortschritt,
        )
    )
    if gesamt:
        from . import anstellung_gesamt

        folge = anstellung_gesamt.richtungen(normalen, winkel, fortschritt)
    else:
        # Ein kleiner Winkelvorrat für die Interpolation zwischen Kontaktpunkten.
        folge = richtungen(normalen, winkel + 2.0)
    je_satz = dict(zip((i for i, _p, _e in schnitte), folge, strict=True))
    naechste, kommend = {}, None
    for i, _p, eilgang in reversed(stellen):
        if not eilgang:
            kommend = je_satz[i]
        naechste[i] = kommend
    ergebnis = [an.KEINE] * len(befehle)
    davor, punkt = None, None
    for i, p, eilgang in stellen:
        if not eilgang:
            neu = je_satz[i]
        elif davor is not None and an._nach_oben(punkt, p):
            neu = davor
        else:
            neu = naechste[i] or davor or an.SENKRECHT
        ergebnis[i], davor, punkt = neu, neu, p
    return ergebnis
