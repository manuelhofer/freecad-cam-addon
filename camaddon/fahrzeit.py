# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Fahrzeit einer Bahn mit Beschleunigung (W-001, Stufe 4d) – für die Zeit im Prüffenster
(abfahren) und die Schätzung im Assistenten (bahn.zeit).

Je Satz fährt die Maschine mit dem Trapezprofil: beschleunigen mit `a` bis zum Tempo
(Vorschub oder Eilgang), fahren, bremsen. Wo sie anhält, sagt der Übergang: vor und nach
einem Satz mit fester Zeit (ein Eilgang – die Achsen fahren einzeln, jede hält –, ein
Werkzeugwechsel), an einer Ecke (der Richtungswechsel zwischen zwei Sätzen ist ECKE oder
mehr) und am Anfang und Ende. Sonst fährt sie durch, mit dem kleineren der beiden Tempi (Bögen
in 5°-Schritten, Rampen). Ist ein Satz zu kurz, erreicht sie das Tempo nicht (Dreieck). Wie
eine Steuerung mit Vorausschau: erst rückwärts, dann vorwärts die Grenzgeschwindigkeiten je
Übergang.

Die Vorgaben, wenn die Maschine nichts sagt – festgesetzt (Manuel, 2026-10-01: „Eilgang und
Beschleunigung dauerhaft festsetzen“): EILGANG 10 m/min, BESCHLEUNIGUNG 1 m/s², wie eine kleine
oder nachgerüstete Maschine; große fahren schneller, die Zeit ist dann eher zu lang. Ruck
bleibt außen vor. Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

from . import export

EILGANG = export.VORGABE_EILGANG  # mm/min
BESCHLEUNIGUNG = export.VORGABE_BESCHLEUNIGUNG * 1000.0  # mm/s²
ECKE = 15.0  # Grad – ab so viel Richtungswechsel hält die Maschine zwischen zwei Sätzen an
_GLEICH = 1e-12


@dataclass
class Satz:
    """Ein Satz der Bahn: der Weg entlang der Bahn (mm; Rundachsen: Grad), das Tempo (mm/s), die
    Beschleunigung entlang der Bahn (mm/s²), die Richtung am Anfang und am Ende (Einheitsvektor
    beliebiger Länge – None: der Übergang hält an) und `fest`: die Zeit steht schon (Eilgang,
    G93) – davor und danach hält die Maschine."""

    weg: float
    tempo: float
    beschleunigung: float
    richtung_von: tuple = None
    richtung_bis: tuple = None
    fest: float = None


def trapez(weg, v_von, v_bis, tempo, a):
    """Zeit (s) für `weg` (mm) mit dem Trapezprofil: von v_von (mm/s) mit `a` (mm/s²) auf
    höchstens `tempo` beschleunigen, fahren, auf v_bis bremsen – ein Dreieck, wenn der Weg
    dafür nicht reicht. Ohne Beschleunigung (a ≤ 0) weg ÷ tempo."""
    if weg <= _GLEICH:
        return 0.0
    if tempo <= 0:
        return math.inf
    if a <= 0:
        return weg / tempo
    v_von, v_bis = min(max(v_von, 0.0), tempo), min(max(v_bis, 0.0), tempo)
    spitze = math.sqrt(max((2.0 * a * weg + v_von * v_von + v_bis * v_bis) / 2.0, 0.0))
    v = max(min(tempo, spitze), v_von, v_bis)
    weg_hoch = (v * v - v_von * v_von) / (2.0 * a)
    weg_runter = (v * v - v_bis * v_bis) / (2.0 * a)
    rest = max(weg - weg_hoch - weg_runter, 0.0)
    return (v - v_von) / a + (v - v_bis) / a + rest / v


def winkel(a, b):
    """Der Winkel zwischen zwei Richtungen (Grad, 0 … 180); 180, wenn eine keine Länge hat."""
    la = math.sqrt(sum(x * x for x in a))
    lb = math.sqrt(sum(x * x for x in b))
    if la <= _GLEICH or lb <= _GLEICH:
        return 180.0
    cos = sum(x * y for x, y in zip(a, b, strict=True)) / (la * lb)
    return math.degrees(math.acos(min(max(cos, -1.0), 1.0)))


def zeiten(saetze, ecke=ECKE):
    """[s] je Satz – mit den Übergängen: anhalten vor und nach einem festen Satz und an Ecken,
    sonst durchfahren, so schnell, wie beide Sätze erlauben und der Weg zum Bremsen reicht."""
    n = len(saetze)
    if n == 0:
        return []
    grenze = [0.0] * (n + 1)  # Geschwindigkeit am Anfang von Satz i; grenze[n]: am Ende
    for i in range(1, n):
        vorher, jetzt = saetze[i - 1], saetze[i]
        if (
            vorher.fest is not None
            or jetzt.fest is not None
            or vorher.richtung_bis is None
            or jetzt.richtung_von is None
            or winkel(vorher.richtung_bis, jetzt.richtung_von) >= ecke
        ):
            continue
        grenze[i] = max(min(vorher.tempo, jetzt.tempo), 0.0)
    for i in range(n - 1, -1, -1):  # rückwärts: so schnell, dass der Satz noch bremsen kann
        s = saetze[i]
        if s.fest is None and s.beschleunigung > 0:
            grenze[i] = min(
                grenze[i], math.sqrt(grenze[i + 1] ** 2 + 2.0 * s.beschleunigung * s.weg)
            )
    for i in range(n):  # vorwärts: so schnell, wie der Satz beschleunigen kann
        s = saetze[i]
        if s.fest is None and s.beschleunigung > 0:
            grenze[i + 1] = min(
                grenze[i + 1], math.sqrt(grenze[i] ** 2 + 2.0 * s.beschleunigung * s.weg)
            )
    return [
        (
            s.fest
            if s.fest is not None
            else trapez(s.weg, grenze[i], grenze[i + 1], s.tempo, s.beschleunigung)
        )
        for i, s in enumerate(saetze)
    ]


def eilgangzeit(wege, tempi, beschleunigungen):
    """Die Zeit eines Eilgangs (s): jede Achse fährt für sich mit ihrem Eilgang und ihrer
    Beschleunigung vom Stand in den Stand; die langsamste bestimmt."""
    zeit = 0.0
    for weg, tempo, a in zip(wege, tempi, beschleunigungen, strict=True):
        if weg is None:
            continue
        zeit = max(zeit, trapez(abs(weg), 0.0, 0.0, tempo, a))
    return zeit
