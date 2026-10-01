# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Bahn eines Fräsers mit senkrechter Werkzeugachse (W-006 S3, Abschnitt 7): Punkte mit
Geraden und Bögen, Eilgang, Eintauchen, Vorschubanteil je Satz – und daraus die Path-Befehle
mit G0, G1, G2, G3 und F, der Weg und die Zeit. Die eine Stelle für alle 2,5D- und
3D-Strategien; die Rundum-Bahnen haben ihre eigene (vierachs_bahn): dort dreht die Rundachse
mit, und F steht nach G93.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

GLEICH = 1e-9  # mm


@dataclass(frozen=True)
class Punkt:
    """Ein Punkt der Bahn (mm im Job). `eilgang`: im Eilgang hierher. `eintauchen`: hierher mit
    dem Eintauchvorschub (senkrecht ins Material). `bogen`: (mx, my, uhrzeiger) – vom Punkt
    davor hierher auf einem Kreisbogen um (mx, my), im Uhrzeigersinn (G2) oder dagegen (G3);
    z dazwischen linear. `anteil`: so viel vom Vorschub gilt für den Satz hierher (beim
    Austritt aus dem Material weniger)."""

    eilgang: bool
    x: float
    y: float
    z: float
    eintauchen: bool = False
    bogen: tuple = None
    anteil: float = 1.0


def im_uhrzeigersinn(von, nach, durch):
    """Läuft der Bogen von `von` über `durch` nach `nach` (je (x, y)) im Uhrzeigersinn?"""
    kreuz = (nach[0] - von[0]) * (durch[1] - von[1]) - (nach[1] - von[1]) * (durch[0] - von[0])
    return kreuz > 0  # der Bogen liegt links der Sehne: im Uhrzeigersinn


def winkel(von, nach):
    """Der Winkel des Bogens `nach.bogen` von `von` nach `nach` (rad, 0 … 2π); 0 ohne Bogen."""
    if nach.bogen is None:
        return 0.0
    mx, my, uhrzeiger = nach.bogen
    a0 = math.atan2(von.y - my, von.x - mx)
    a1 = math.atan2(nach.y - my, nach.x - mx)
    grad = (a0 - a1) if uhrzeiger else (a1 - a0)
    grad %= 2 * math.pi
    if grad < 1e-12 and (abs(von.x - nach.x) > GLEICH or abs(von.y - nach.y) > GLEICH):
        grad = 2 * math.pi  # numerisch: Anfang und Ende auf demselben Strahl
    return grad


def weg(von, nach):
    """Der Weg der Spitze von einem Punkt zum nächsten (mm) – auf dem Bogen die Bogenlänge."""
    dz = nach.z - von.z
    if nach.bogen is None:
        return math.sqrt((nach.x - von.x) ** 2 + (nach.y - von.y) ** 2 + dz * dz)
    mx, my, _uhrzeiger = nach.bogen
    r = math.hypot(von.x - mx, von.y - my)
    return math.hypot(r * winkel(von, nach), dz)


def dauer(punkte, vorschub, eintauchen=None):
    """So lange fährt die Bahn im Vorschub (Minuten) – ohne Eilgänge; `vorschub` und
    `eintauchen` in mm/min, `eintauchen` für Punkte mit Eintauchvorschub (ohne: `vorschub`)."""
    zeit = 0.0
    for von, nach in zip(punkte, punkte[1:], strict=False):
        if nach.eilgang:
            continue
        f = eintauchen if nach.eintauchen and eintauchen else vorschub
        f *= nach.anteil
        if f > 0:
            zeit += weg(von, nach) / f
    return zeit


def zeit(punkte, vorschub, eintauchen=None, eilgang=None, beschleunigung=None):
    """So lange dauert die Bahn (Minuten) – Vorschub und Eilgang, mit Beschleunigung
    (fahrzeit: Trapezprofil, anhalten an Ecken und um Eilgänge). `vorschub` und `eintauchen`
    wie bei dauer(); `eilgang` (mm/min) und `beschleunigung` (mm/s²) ohne Angabe die
    Vorgaben, 10 m/min und 1 m/s²."""
    from . import fahrzeit as fz

    schnell = (eilgang or fz.EILGANG) / 60.0
    a = fz.BESCHLEUNIGUNG if beschleunigung is None else beschleunigung
    saetze = []
    for von, nach in zip(punkte, punkte[1:], strict=False):
        if nach.eilgang:
            wege = (nach.x - von.x, nach.y - von.y, nach.z - von.z)
            fest = fz.eilgangzeit(wege, (schnell, schnell, schnell), (a, a, a))
            saetze.append(fz.Satz(0.0, schnell, a, fest=fest))
            continue
        f = (eintauchen if nach.eintauchen and eintauchen else vorschub) * nach.anteil / 60.0
        saetze.append(
            fz.Satz(weg(von, nach), f, a, _richtung(von, nach, True), _richtung(von, nach, False))
        )
    return sum(fz.zeiten(saetze)) / 60.0


def _richtung(von, nach, anfang):
    """Die Fahrtrichtung am Anfang oder Ende des Satzes von `von` nach `nach` – auf dem Bogen
    die Tangente dort, mit der Steigung in z."""
    dz = nach.z - von.z
    if nach.bogen is None:
        return (nach.x - von.x, nach.y - von.y, dz)
    mx, my, uhrzeiger = nach.bogen
    punkt = von if anfang else nach
    rx, ry = punkt.x - mx, punkt.y - my
    tx, ty = (ry, -rx) if uhrzeiger else (-ry, rx)
    laenge_xy = math.hypot(rx, ry) * winkel(von, nach)
    norm = math.hypot(tx, ty) or 1.0
    return (tx / norm * laenge_xy, ty / norm * laenge_xy, dz)


def laenge(punkte):
    """Der Weg im Vorschub (mm), ohne Eilgänge."""
    return sum(
        weg(von, nach) for von, nach in zip(punkte, punkte[1:], strict=False) if not nach.eilgang
    )


def befehle(punkte, vorschub, eintauchen=None, kommentar=None):
    """Die Bahn als Path-Befehle: G0 im Eilgang (zum ersten Punkt erst in Z, dann in X und Y),
    G1 auf der Geraden, G2/G3 auf dem Bogen mit I und J zur Mitte, F je Satz. CAM führt F in
    mm/s, der Postprozessor schreibt ×60 – deshalb F ÷ 60. `vorschub` und `eintauchen` in
    mm/min wie bei dauer(). `kommentar`: ein Satz vorweg."""
    import Path

    ergebnis = [Path.Command(f"({kommentar})")] if kommentar else []
    if not punkte:
        return ergebnis
    start = punkte[0]
    ergebnis.append(Path.Command("G0", {"Z": float(start.z)}))
    ergebnis.append(Path.Command("G0", {"X": float(start.x), "Y": float(start.y)}))
    vorher = start
    for punkt in punkte[1:]:
        werte = {"X": float(punkt.x), "Y": float(punkt.y), "Z": float(punkt.z)}
        if punkt.eilgang:
            ergebnis.append(Path.Command("G0", werte))
        else:
            if weg(vorher, punkt) < 1e-6:
                continue
            f = eintauchen if punkt.eintauchen and eintauchen else vorschub
            werte["F"] = float(f) * punkt.anteil / 60.0
            if punkt.bogen is None:
                ergebnis.append(Path.Command("G1", werte))
            else:
                mx, my, uhrzeiger = punkt.bogen
                werte["I"] = float(mx - vorher.x)
                werte["J"] = float(my - vorher.y)
                ergebnis.append(Path.Command("G2" if uhrzeiger else "G3", werte))
        vorher = punkt
    return ergebnis
