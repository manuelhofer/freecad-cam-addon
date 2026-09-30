# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bestückung je Job (W-002 Stufe G, spezifikation_werkzeugverwaltung.md).

Welches Werkzeug auf welchem Revolverplatz steckt, legt jeder Job selbst fest –
Manuel (2026-09-30): „ja jeder job hat seine eigene bestückung und man hat
einfach die maschine die man ablegt und immer wieder laden kann“. Es steht in
seinen Werkzeug-Controllern: Deren Nummer (ToolNumber) ruft das Programm auf,
und an einem Revolver ist sie der Platz – T3 steckt auf P3. Eine zweite Liste
gibt es nicht; so können Programm und Bestückung nicht auseinanderlaufen.

Ein Werkzeug des Jobs (Eintrag) sind alle Controller mit demselben Werkzeug aus
der Werkzeugverwaltung (dieselbe Kennung), sonst mit demselben CAM-Werkzeug.
Unbenutzte fremde Controller – FreeCADs „TC: 5mm Endmill“ in jedem neuen Job –
zählen nicht: Der 4-Achs-Assistent nimmt sie heraus (Durchsicht W-004, D-30).
Ein neues Werkzeug bekommt den Platz, den es im Job schon hat, sonst den seiner
Nummer, wenn der im Job frei ist, sonst den ersten freien (platz_fuer). Umlegen
ändert die Nummer aller seiner Controller; steckt auf dem neuen Platz schon eins,
tauschen die beiden (lege_um).

Die Plätze kommen von der Maschine (reichweite.Pruefung.platznummern); ohne
Revolver gilt wie bisher die Nummer aus der Werkzeugverwaltung. Läuft ohne
Oberfläche.
"""

import re
from dataclasses import dataclass, field

from . import job_schnittwerte as js
from . import werkzeuge as wz


@dataclass(eq=False)
class Eintrag:
    """Ein Werkzeug des Jobs mit seinen Controllern."""

    schluessel: str  # Kennung aus der Werkzeugverwaltung, sonst Name des CAM-Werkzeugs
    werkzeug: object = None  # werkzeuge.Werkzeug – None, wenn nicht aus der Werkzeugverwaltung
    controller: list = field(default_factory=list)

    @property
    def nummern(self):
        """Die Plätze seiner Controller – meist einer; mehrere, wenn jemand sie verschieden
        gesetzt hat."""
        return sorted({int(getattr(tc, "ToolNumber", 0)) for tc in self.controller})

    @property
    def nummer(self):
        """Der Platz, auf dem es steckt (bei mehreren der erste)."""
        nummern = self.nummern
        return nummern[0] if nummern else 0


def schluessel(tc, bibliothek):
    """Woran zwei Controller dasselbe Werkzeug erkennen: die Kennung aus der
    Werkzeugverwaltung, sonst das CAM-Werkzeug (ToolBit) im Dokument."""
    werkzeug = js.werkzeug_von(tc, bibliothek) if bibliothek is not None else None
    return _schluessel(tc, werkzeug)


def _schluessel(tc, werkzeug):
    if werkzeug is not None:
        return "wz:" + werkzeug.kennung
    bit = getattr(tc, "Tool", None)
    return "cam:" + (bit.Name if bit is not None else tc.Name)


def eintraege(job, bibliothek):
    """Die Werkzeuge des Jobs (Eintrag), in der Reihenfolge ihrer ersten Controller –
    ohne unbenutzte fremde Controller."""
    fremd = set(js.unbenutzte_fremde_controller(job, bibliothek)) if bibliothek else set()
    nach_schluessel = {}
    for tc in js.werkzeug_controller(job):
        if tc in fremd:
            continue
        werkzeug = js.werkzeug_von(tc, bibliothek) if bibliothek is not None else None
        schluessel = _schluessel(tc, werkzeug)
        eintrag = nach_schluessel.get(schluessel)
        if eintrag is None:
            eintrag = nach_schluessel[schluessel] = Eintrag(schluessel, werkzeug)
        eintrag.controller.append(tc)
    return list(nach_schluessel.values())


def auf_plaetzen(job, bibliothek, schon=None):
    """{Platznummer: [Eintrag, …]} – welche Werkzeuge des Jobs auf welcher Nummer stecken.
    `schon`: die Einträge, wenn der Aufrufer sie schon hat – dann sind es dieselben Objekte."""
    ergebnis = {}
    for eintrag in schon if schon is not None else eintraege(job, bibliothek):
        for nummer in eintrag.nummern:
            ergebnis.setdefault(nummer, []).append(eintrag)
    return ergebnis


def doppelt(job, bibliothek):
    """[(Platznummer, [Eintrag, …])] – Plätze, auf denen im Job mehr als ein Werkzeug
    steckt: Die Maschine nähme nur eines."""
    return sorted((n, e) for n, e in auf_plaetzen(job, bibliothek).items() if len(e) > 1)


def eintrag_von(job, werkzeug, bibliothek):
    """Der Eintrag des Werkzeugs (werkzeuge.Werkzeug) im Job, oder None."""
    schluessel = "wz:" + werkzeug.kennung
    return next((e for e in eintraege(job, bibliothek) if e.schluessel == schluessel), None)


def platz_fuer(job, werkzeug, bibliothek, nummern, vorgemerkt=None):
    """Die Nummer, mit der `werkzeug` (werkzeuge.Werkzeug) in diesem Job aufgerufen wird.

    `nummern`: die Platznummern des Revolvers der Maschine – leer ohne Revolver oder
    ohne Maschine: dann seine Nummer aus der Werkzeugverwaltung (0 ohne). Mit Revolver:
    der Platz, den es im Job schon hat; sonst seine Nummer, wenn der Platz im Job frei
    ist; sonst der erste freie. `vorgemerkt`: {Nummer: Kennung} für Werkzeuge, die gleich
    mit in den Job kommen (Schruppen und Schlichten in einem Schritt). None, wenn alle
    Plätze belegt sind.
    """
    if not nummern:
        return werkzeug.nummer
    if job is not None:
        eintrag = eintrag_von(job, werkzeug, bibliothek)
        if eintrag is not None and eintrag.nummern:
            return eintrag.nummer
        belegt = set(auf_plaetzen(job, bibliothek))
    else:
        belegt = set()
    belegt |= {n for n, kennung in (vorgemerkt or {}).items() if kennung != werkzeug.kennung}
    if werkzeug.nummer in nummern and werkzeug.nummer not in belegt:
        return werkzeug.nummer
    return next((n for n in sorted(nummern) if n not in belegt), None)


def lege_um(job, eintrag, nummer, bibliothek):
    """Legt das Werkzeug `eintrag` auf den Platz `nummer`: Alle seine Controller bekommen
    die Nummer, ihr Name folgt („T3 Schruppen“ → „T5 Schruppen“). Steckt dort schon ein
    anderes, bekommt es den bisherigen Platz von `eintrag` – die beiden tauschen. In der
    Transaktion des Aufrufers; gibt die geänderten Controller zurück."""
    alt = eintrag.nummer
    geaendert = []
    for anderer in auf_plaetzen(job, bibliothek).get(nummer, []):
        if anderer is not eintrag and anderer.schluessel != eintrag.schluessel:
            geaendert += _nummer_setzen(anderer.controller, alt)
    geaendert += _nummer_setzen(eintrag.controller, nummer)
    return geaendert


def _nummer_setzen(controller, nummer):
    geaendert = []
    for tc in controller:
        alt = int(getattr(tc, "ToolNumber", 0))
        if alt == nummer:
            continue
        tc.ToolNumber = nummer
        name = umbenannt(tc.Label, alt, nummer)
        if name != tc.Label:
            tc.Label = name
        geaendert.append(tc)
    return geaendert


def umbenannt(name, alt, neu):
    """Der Name eines Controllers mit der neuen Nummer: „T3 Schruppen“ → „T5 Schruppen“ –
    nur, wenn er mit der alten beginnt, wie ihn das Addon benennt (controller_name)."""
    return re.sub(rf"^T{alt}(?=\s|$)", f"T{neu}", name, count=1)


def text(eintrag):
    """Wie das Werkzeug in der Bestückung heißt, ohne Nummer: „Schaftfräser Ø 12 · z 3 ·
    VHM“, mit eigenem Namen davor; nicht aus der Werkzeugverwaltung wie in CAM. Zahlen mit
    Punkt (die Oberfläche setzt ihr Dezimalzeichen ein)."""
    werkzeug = eintrag.werkzeug
    if werkzeug is None:
        tc = eintrag.controller[0]
        return getattr(getattr(tc, "Tool", None), "Label", "") or tc.Label
    teile = [wz.art_text(werkzeug.art) + " " + " · ".join(wz.merkmale(werkzeug))]
    if werkzeug.name:
        teile.insert(0, werkzeug.name)
    return " · ".join(t.strip() for t in teile)


def kurz(eintrag):
    """Für Sätze: „Schaftfräser Ø 12“ (Art und Durchmesser, ohne Nummer – die sagt der Platz);
    nicht aus der Werkzeugverwaltung wie in CAM. Zahlen mit Punkt."""
    if eintrag.werkzeug is not None:
        return wz.kurz(eintrag.werkzeug)
    tc = eintrag.controller[0]
    return getattr(getattr(tc, "Tool", None), "Label", "") or tc.Label
