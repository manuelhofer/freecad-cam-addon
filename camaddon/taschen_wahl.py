# SPDX-License-Identifier: LGPL-2.1-or-later
"""Gehören die gewählten Flächen zu einer Vertiefung, von der nur ein Teil gewählt ist?

Manuel, 2026-10-30, am 5-Achs-Teil „tief“: „wenn ich jetzt da bloß zwei Wände anklicke, wie willst
du die bearbeiten, ohne alles andere auch ein bisschen mit zu bearbeiten? … Oder ihm darauf
hinweisen, hey, hör zu, du kannst die zwei Wände nicht einzeln bearbeiten. Entweder wir bearbeiten
das ganze Teil, die ganze Tasche oder sowas.“

Eine Vertiefung (Tasche, Nut, Stufe nach innen) sind die Flächen, die über **hohle** Kanten
zusammenhängen: Boden und Wand einer Tasche treffen sich hohl (der Fräser kommt von innen in die
Ecke), die Wand und die Oberseite des Teils dagegen an einer Außenkante. Glatte Übergänge (eine
Rundung zwischen Wand und Boden, B-Spline-Stücke einer Wand) gehören dazu. Von den gewählten
Flächen aus über hohle und glatte Kanten gesammelt, ergibt das die ganze Vertiefung.

Läuft ohne Oberfläche.
"""

import math

HOHL, AUSSEN, GLATT = "hohl", "aussen", "glatt"
GLATT_GRAD = 3.0  # so wenig dürfen die Normalen an einer Kante auseinander liegen, um glatt zu sein
SCHRITT = 0.05  # mm – so weit neben der Kante wird in die Fläche hinein gefragt


def _normale(flaeche, punkt):
    u, v = flaeche.Surface.parameter(punkt)
    n = flaeche.normalAt(u, v)
    return n


def _in_die_flaeche(flaeche, punkt, tangente, normale):
    """Die Richtung von der Kante in die Fläche hinein (senkrecht zur Kante, in der Fläche).

    Gefragt wird die beschnittene Fläche selbst (distToShape): isPartOfDomain kennt nur das
    Rechteck der Parameter – an einer oben abgeschnittenen B-Spline-Wand liegen beide Seiten
    darin, und die Ecke kam zufällig als Außenkante heraus."""
    import Part

    quer = normale.cross(tangente)
    if quer.Length < 1e-9:
        return None
    quer.normalize()
    besser = None
    for richtung in (quer, quer * -1):
        probe = punkt + richtung * SCHRITT
        abstand = flaeche.distToShape(Part.Vertex(probe))[0]
        if besser is None or abstand < besser[0]:
            besser = (abstand, richtung)
    if besser is None or besser[0] > SCHRITT * 0.5:
        return None
    return besser[1]


def kante_art(form, kante, flaeche_a, flaeche_b):
    """HOHL, AUSSEN oder GLATT – wie sich `flaeche_a` und `flaeche_b` an `kante` treffen.

    Gefragt an drei Stellen der Kante; es zählt die Mehrheit (eine Kante, die mal hohl, mal außen
    ist, gibt es an echten Teilen kaum)."""
    del form
    stimmen = []
    erster, letzter = kante.FirstParameter, kante.LastParameter
    for anteil in (0.25, 0.5, 0.75):
        t = erster + (letzter - erster) * anteil
        punkt = kante.valueAt(t)
        try:
            tangente = kante.tangentAt(t)
            na = _normale(flaeche_a, punkt)
            nb = _normale(flaeche_b, punkt)
        except Exception:
            continue
        if na.getAngle(nb) < math.radians(GLATT_GRAD):
            stimmen.append(GLATT)
            continue
        richtung = _in_die_flaeche(flaeche_a, punkt, tangente, na)
        if richtung is None:
            continue
        # Geht es von der Kante in Fläche a hinein auf die Seite, zu der b nach außen zeigt, liegt
        # a vor b: der Winkel im Material ist größer als 180° – die Ecke ist hohl.
        stimmen.append(HOHL if nb.dot(richtung) > 0 else AUSSEN)
    if not stimmen:
        return AUSSEN
    return max((HOHL, AUSSEN, GLATT), key=stimmen.count)


def nachbarn(form):
    """{Flächennummer (0-basiert): [(Nachbar, Art der Kante)]} über alle Kanten von `form`."""
    flaechen = form.Faces
    index = {}
    for i, f in enumerate(flaechen):
        index.setdefault(f.hashCode(), i)
    ergebnis = {i: [] for i in range(len(flaechen))}
    for kante in form.Edges:
        beteiligt = []
        for f in form.ancestorsOfType(kante, type(flaechen[0])) if flaechen else []:
            i = index.get(f.hashCode())
            if i is not None and i not in beteiligt:
                beteiligt.append(i)
        if len(beteiligt) != 2:
            continue  # Naht einer Fläche mit sich selbst oder eine freie Kante
        a, b = beteiligt
        art = kante_art(form, kante, flaechen[a], flaechen[b])
        ergebnis[a].append((b, art))
        ergebnis[b].append((a, art))
    return ergebnis


def gewoelbt(flaeche):
    """Ist die Fläche nach außen gewölbt (eine Rundung an einer Außenkante, ein Zapfen)? Gefragt an
    einigen Stellen: Liegen Nachbarpunkte der Fläche unter ihrer Tangentialebene (gegen die
    Normale), wölbt sie sich nach außen."""
    u0, u1, v0, v1 = flaeche.ParameterRange
    summe = 0.0
    for a, b in ((0.5, 0.5), (0.3, 0.3), (0.7, 0.7), (0.3, 0.7), (0.7, 0.3)):
        u, v = u0 + (u1 - u0) * a, v0 + (v1 - v0) * b
        if not flaeche.isPartOfDomain(u, v):
            continue
        p = flaeche.valueAt(u, v)
        n = flaeche.normalAt(u, v)
        for du, dv in ((0.05, 0), (-0.05, 0), (0, 0.05), (0, -0.05)):
            uu, vv = u + (u1 - u0) * du, v + (v1 - v0) * dv
            if not flaeche.isPartOfDomain(uu, vv):
                continue
            q = flaeche.valueAt(uu, vv)
            abstand = (q - p).Length
            if abstand > 1e-9:
                summe += n.dot(q - p) / abstand
    return summe < -0.02


def vertiefung(form, gewaehlt, nachbar=None):
    """Die ganze Vertiefung, zu der die Flächen `gewaehlt` („Face12“ …) gehören: ihre Namen,
    sortiert nach Nummer – gesammelt über hohle Kanten und über glatte, solange die nächste Fläche
    nicht nach außen gewölbt ist (sonst wanderte es über eine Rundung am Rand auf die Oberseite)."""
    nachbar = nachbarn(form) if nachbar is None else nachbar
    offen = [int(n[4:]) - 1 for n in gewaehlt if n.startswith("Face")]
    gesehen = set(offen)
    flaechen = form.Faces
    gewoelbte = {}
    while offen:
        i = offen.pop()
        for j, art in nachbar.get(i, ()):
            if j in gesehen or art == AUSSEN:
                continue
            if art == GLATT:
                if j not in gewoelbte:
                    gewoelbte[j] = gewoelbt(flaechen[j])
                if gewoelbte[j]:
                    continue
            gesehen.add(j)
            offen.append(j)
    return [f"Face{i + 1}" for i in sorted(gesehen)]


def fehlende(form, gewaehlt, nachbar=None):
    """Was zur Vertiefung der gewählten Flächen noch gehört, aber nicht gewählt ist."""
    ganz = vertiefung(form, gewaehlt, nachbar)
    return [n for n in ganz if n not in set(gewaehlt)]
