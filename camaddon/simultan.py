# SPDX-License-Identifier: LGPL-2.1-or-later
"""5 Achsen simultan (W-015, Spezifikation Strategien 16) – der Kern S1.

Eine Bahn mit Achse: je Punkt die Spitze und die Werkzeugachse (von der Spitze weg) im
Grundjob. Daraus je Punkt die Rundachsen – stetig entlang der Bahn: die erste Stellung die beste
der Maschine (schwenken.Maschine.loese), jede weitere vom Punkt davor aus nachgeführt
(Gauß-Newton über die Rundachsen, gedämpft: am Pol, wo eine Rundachse die Werkzeugachse nicht
mehr ändert, bleibt sie stehen) – und X, Y, Z, wie eine Steuerung ohne TCPM sie liest
(schwenken.Abbildung, wie „Auf der Maschine prüfen“).

Wie die Bahn entsteht (Kugelfräser angestellt, Flanke …) und ob das Programm TCPM nimmt,
entscheidet Manuel (Spezifikation 16.4); die Rundachsen entlang der Bahn braucht jeder Weg –
auch die Prüfung auf der Maschine. Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import FreeCAD

from . import schwenken as sw
from .sprache import tr

SCHRITT = 1e-4  # Grad – so weit dreht eine Rundachse für die Ableitung der Werkzeugachse
GENAU = 1e-13  # 1 − cos des Winkels zwischen Werkzeugachse und Ziel: genau genug
DAEMPFUNG = 1e-9  # gegen die Singularität am Pol (Anteil an der Spur von JᵀJ)
GROESSTER_SCHRITT = 10.0  # Grad je Rechenschritt – sonst springt es am Pol auf den anderen Ast
KUERZESTE_ZEIT = 1e-3  # s – so kurz dauert ein Satz mit G93 mindestens


@dataclass
class Punkt:
    """Ein Punkt der Bahn: die Spitze und die Werkzeugachse (von der Spitze weg) im Grundjob,
    Eilgang oder Vorschub (mm/s wie FreeCADs Bahnen; 0: wie davor)."""

    spitze: tuple
    achse: tuple
    eilgang: bool = False
    vorschub: float = 0.0


def rundachsen_entlang(maschine, achsen):
    """[{Buchstabe: Grad}] – je Werkzeugachse (im Grundjob) die Stellung der Rundachsen von
    `maschine` (schwenken.Maschine), stetig entlang der Bahn. Endlose Achsen laufen über ±180°
    hinaus weiter, statt zu springen. ValueError mit einem Satz, wenn eine Achse nicht zu
    treffen ist oder eine Rundachse über ihre Grenze müsste."""
    rundachsen = maschine.rundachsen
    ergebnis = []
    werte = None
    for nummer, achse in enumerate(achsen, start=1):
        n = FreeCAD.Vector(*achse)
        n.normalize()
        if werte is None:
            loesungen = maschine.loese(n)
            if not loesungen:
                raise ValueError(tr("si.fehler.achse", punkt=nummer))
            werte = [loesungen[0][a.buchstabe] for a in rundachsen]
        else:
            werte = _nachfuehren(maschine, n, werte)
            if werte is None:
                raise ValueError(tr("si.fehler.achse", punkt=nummer))
        rund = {a.buchstabe: sw._rund(w) for a, w in zip(rundachsen, werte, strict=True)}
        for a in rundachsen:
            if not a.erlaubt(rund[a.buchstabe]):
                raise ValueError(
                    tr(
                        "si.fehler.grenze",
                        punkt=nummer,
                        achse=a.buchstabe,
                        wert=f"{rund[a.buchstabe]:.1f}",
                    )
                )
        ergebnis.append(rund)
    return ergebnis


def _nachfuehren(maschine, n, werte):
    """Die Rundachsen (Grad, Liste wie maschine.rundachsen), mit denen die Werkzeugachse `n`
    ist – von `werte` aus gesucht; None, wenn es nicht genau genug geht."""
    import numpy

    rundachsen = maschine.rundachsen
    ziel = numpy.array([n.x, n.y, n.z])

    def richtung(w):
        d = maschine.richtung({a.buchstabe: x for a, x in zip(rundachsen, w, strict=True)})
        return numpy.array([d.x, d.y, d.z])

    werte = [float(w) for w in werte]
    for _ in range(40):
        d = richtung(werte)
        if 1.0 - float(d @ ziel) <= GENAU:
            return werte
        spalten = []
        for i in range(len(werte)):
            versuch = list(werte)
            versuch[i] += SCHRITT
            spalten.append((richtung(versuch) - d) / SCHRITT)
        j = numpy.array(spalten).T
        jtj = j.T @ j
        daempfung = DAEMPFUNG * max(float(numpy.trace(jtj)), 1e-12)
        schritt = numpy.linalg.solve(jtj + daempfung * numpy.eye(len(werte)), j.T @ (ziel - d))
        groesster = float(numpy.max(numpy.abs(schritt)))
        if groesster > GROESSTER_SCHRITT:
            schritt *= GROESSTER_SCHRITT / groesster
        werte = [w + float(s) for w, s in zip(werte, schritt, strict=True)]
    d = richtung(werte)
    grenze = 1.0 - math.cos(math.radians(sw.WINKEL_GENAU))
    return werte if 1.0 - float(d @ ziel) <= grenze else None


def programm_ohne_tcpm(maschine, punkte, g93=False):
    """[Path.Command] – die Bahn (Punkt …) mit den Rundachsen je Punkt und X, Y, Z, wie eine
    Steuerung ohne TCPM sie liest. Zwischen zwei Punkten fährt die Maschine jede Achse linear –
    die Spitze bleibt nur nahe der Geraden, wenn die Punkte dicht liegen. `g93`: der Vorschub
    als 1 ÷ Zeit (G93 … G94): je Satz die Zeit aus dem Weg der Spitze am Werkstück und dem
    Vorschub – dreht sich nur die Achse, zählt der größte Winkel in Grad wie mm; F wie
    FreeCADs Bahnen ÷ 60 (1 ÷ Sekunden). ValueError mit einem Satz wie rundachsen_entlang, oder
    wenn die Maschine keine drei Linearachsen hat."""
    import Path

    rund = rundachsen_entlang(maschine, [p.achse for p in punkte])
    befehle = [Path.Command("G93")] if g93 else []
    vorschub, davor = 0.0, None
    for punkt, stellung in zip(punkte, rund, strict=True):
        abbildung = maschine.abbildung(stellung)
        if abbildung is None:
            raise ValueError(tr("si.fehler.linear"))
        werte = dict(zip("XYZ", abbildung.punkt(punkt.spitze), strict=True))
        werte.update(stellung)
        if punkt.vorschub > 0:
            vorschub = float(punkt.vorschub)
        if not punkt.eilgang and vorschub > 0:
            if g93:
                weg = 0.0
                if davor is not None:
                    weg = max(
                        math.dist(davor[0], punkt.spitze),
                        max(abs(stellung[k] - davor[1][k]) for k in stellung),
                    )
                werte["F"] = 1.0 / max(weg / vorschub, KUERZESTE_ZEIT)
            elif punkt.vorschub > 0:
                werte["F"] = vorschub
        befehle.append(Path.Command("G0" if punkt.eilgang else "G1", werte))
        davor = (punkt.spitze, stellung)
    if g93:
        befehle.append(Path.Command("G94"))
    return befehle
