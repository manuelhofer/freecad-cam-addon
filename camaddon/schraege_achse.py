# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die schräge Achse (W-001, Abschnitt 7c): Winkel messen und umrechnen.

Bei vielen Schrägbett-Drehmaschinen fährt der Y-Schlitten schräg zum
X-Schlitten. Das NC-Programm bleibt trotzdem rechtwinklig; die Steuerung
rechnet es auf beide Schlitten um (Siemens TRAANG, Fanuc Angular Axis
Control). Für ein Y im Programm fahren dann beide:

    vom Programm zu den Schlitten      von den Schlitten zum Programm
    Y1 = Y / cos α                     Y = Y1 · cos α
    X1 = X − Y · tan α                 X = X1 + Y1 · sin α

α ist der Winkel, um den die schräge Achse (hier Y1) aus dem rechten Winkel
zur ausgleichenden (X1) gekippt ist – positiv, wenn sie zu deren Plus-Seite
kippt. Er steht nur in der Baugruppe, in der Richtung der Gelenke; dieses
Modul misst ihn dort. Im Maschinenobjekt steht nur, welche Achsen es sind
(maschine.Transformation).

Gerechnet wird mit der Richtung, in die das Werkzeug gegenüber dem
Werkstück fährt: Eine Achse im Tisch bewegt das Werkstück, für das Werkzeug
also andersherum.

Läuft ohne Oberfläche.
"""

import math

from . import maschine as m
from . import verfahren as vf
from .kette import LINEAR, meldung

# Ab diesem Winkel (Grad) fahren beide Schlitten fast in dieselbe Richtung –
# daraus lässt sich kein rechtwinkliges Y mehr rechnen (cos α → 0).
GROESSTER_WINKEL = 89.0
# Darunter (Grad) stehen zwei Achsen rechtwinklig – Rundungsreste der Baugruppe.
RECHTWINKLIG_BIS = 0.01


def schlitten_aus_programm(alpha, x, y):
    """(x1, y1): wohin die Schlitten fahren, damit das Werkzeug im Programm bei (x, y) steht.

    `alpha` in Grad; x, y, x1, y1 sind Wege ab der Stellung 0 der Gelenke.
    """
    winkel = math.radians(alpha)
    return x - y * math.tan(winkel), y / math.cos(winkel)


def programm_aus_schlitten(alpha, x1, y1):
    """(x, y): wo das Werkzeug im Programm steht, wenn die Schlitten bei (x1, y1) stehen."""
    winkel = math.radians(alpha)
    return x1 + y1 * math.sin(winkel), y1 * math.cos(winkel)


def winkel(kette, maschine, trafo):
    """α der schrägen Achse `trafo` in Grad, gemessen in der Baugruppe.

    None, wenn eine der beiden Achsen fehlt oder keine Linearachse der Kette ist.
    """
    return winkel_zwischen(kette, maschine, trafo.Schraeg, trafo.Ausgleich)


def winkel_zwischen(kette, maschine, schraeg, ausgleich):
    """α zwischen zwei Betriebsarten: wie weit `schraeg` aus dem rechten Winkel zu
    `ausgleich` gekippt ist, in Grad (−90 … 90). None, wenn eine keine Linearachse ist."""
    achsen = [_linearachse(kette, ba) for ba in (schraeg, ausgleich)]
    if None in achsen:
        return None
    rollen = m.rollen(kette, maschine)[0]
    s, a = (_richtung(achse, rollen) for achse in achsen)
    return math.degrees(math.asin(max(-1.0, min(1.0, s.dot(a)))))


def linearachsen(maschine, kette):
    """Die Betriebsarten der Art Linear mit gültiger Achse in der Kette, nach NC-Namen."""
    return sorted(
        (ba for ba in m.betriebsarten(maschine) if _linearachse(kette, ba) is not None),
        key=lambda ba: m.name_von(ba).upper(),
    )


def vorschlag(maschine, kette):
    """Die Achsen für eine neue schräge Achse: (schräg, ausgleichend) – oder None, wenn
    es keine zwei Linearachsen gibt.

    Zuerst ein Paar, das schräg zueinander steht und noch keinen Eintrag hat;
    sonst die ersten beiden Linearachsen. Ausgleichend ist die, deren Name im
    Alphabet vorn steht (X1 vor Y1).
    """
    linear = linearachsen(maschine, kette)
    paare = [(a, s) for i, a in enumerate(linear) for s in linear[i + 1 :]]
    if not paare:
        return None
    vergeben = {frozenset((t.Schraeg, t.Ausgleich)) for t in m.transformationen(maschine)}
    for ausgleich, schraeg in paare:
        alpha = winkel_zwischen(kette, maschine, schraeg, ausgleich)
        if frozenset((schraeg, ausgleich)) in vergeben:
            continue
        if RECHTWINKLIG_BIS < abs(alpha) <= GROESSTER_WINKEL:
            return schraeg, ausgleich
    ausgleich, schraeg = paare[0]
    return schraeg, ausgleich


def pruefe(maschine, kette):
    """Die Meldungen zu den schrägen Achsen, als fertige Sätze.

    Was an einer Betriebsart selbst nicht stimmt (Gelenk fehlt, falsche
    Gelenkart), meldet schon maschine.pruefe – hier nur, was die schräge
    Achse betrifft.
    """
    meldungen = []
    for trafo in m.transformationen(maschine):
        name = m.name_von(trafo)
        schraeg, ausgleich = trafo.Schraeg, trafo.Ausgleich
        if schraeg is None or ausgleich is None:
            meldungen.append(meldung("maschine.trafo_achse_fehlt", bezug=trafo, name=name))
            continue
        if schraeg == ausgleich:
            meldungen.append(
                meldung(
                    "maschine.trafo_gleiche_achse",
                    bezug=trafo,
                    name=name,
                    achse=m.name_von(schraeg),
                )
            )
            continue
        falsch = [ba for ba in (schraeg, ausgleich) if not _ist_linear(ba)]
        for ba in falsch:
            meldungen.append(
                meldung("maschine.trafo_nicht_linear", bezug=trafo, name=name, achse=m.name_von(ba))
            )
        if falsch:
            continue
        alpha = winkel(kette, maschine, trafo)
        if alpha is not None and abs(alpha) > GROESSTER_WINKEL:
            meldungen.append(
                meldung(
                    "maschine.trafo_parallel",
                    bezug=trafo,
                    name=name,
                    schraeg=m.name_von(schraeg),
                    ausgleich=m.name_von(ausgleich),
                )
            )
    return meldungen


def _ist_linear(ba):
    return m.ist_betriebsart(ba) and ba.Art == m.ART_LINEAR


def _linearachse(kette, ba):
    """Die Linearachse der Kette zu einer Betriebsart der Art Linear, sonst None."""
    if ba is None or not _ist_linear(ba) or ba.Gelenk is None:
        return None
    achse = kette.achse_von(ba.Gelenk)
    return achse if achse is not None and achse.art == LINEAR else None


def _richtung(achse, rollen):
    """Wohin das Werkzeug gegenüber dem Werkstück fährt, wenn die Stellung wächst.

    Eine Achse im Tisch bewegt das Werkstück – für das Werkzeug andersherum.
    Ohne Rolle (noch keine Aufnahmen) zählt sie wie eine im Kopf.
    """
    richtung = vf.plusrichtung(achse)
    return richtung * -1.0 if rollen.get(achse.gelenk) == m.TISCH else richtung
