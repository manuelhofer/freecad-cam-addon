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

Ein Grundjob und seine geschwenkten Ebenen (3+2, schwenken.py) sind eine Aufspannung
und ein Programm: Sie teilen die Bestückung – ein Werkzeug hat in allen dieselbe
Nummer, ein Platz ein Werkzeug (aufspannung).
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


def aufspannung(job):
    """Die Jobs, die mit `job` ein Programm sind: sein Grundjob (ist er eine geschwenkte Ebene)
    und dessen Ebenen – ohne Ebenen nur `job`."""
    from . import schwenken as sw

    grund = getattr(job, "Grundjob", None) if sw.ist_ebene(job) else None
    grund = grund or job
    return [grund] + [e for e in sw.ebenen_von(grund) if e is not grund]


def eintraege(job, bibliothek):
    """Die Werkzeuge des Jobs (Eintrag) – mit allen Jobs seiner Aufspannung –, in der
    Reihenfolge ihrer ersten Controller, ohne unbenutzte fremde Controller."""
    jobs = aufspannung(job)
    fremd = set()
    if bibliothek:
        for j in jobs:
            fremd.update(js.unbenutzte_fremde_controller(j, bibliothek))
    nach_schluessel = {}
    for tc in (tc for j in jobs for tc in js.werkzeug_controller(j)):
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


def platz_fuer(job, werkzeug, bibliothek, nummern, vorgemerkt=None, maschine=None):
    """Die Nummer, mit der `werkzeug` (werkzeuge.Werkzeug) in diesem Job aufgerufen wird.

    `nummern`: die Platznummern des Revolvers der Maschine – leer ohne Revolver oder
    ohne Maschine: dann seine Nummer aus der Werkzeugverwaltung (ohne Nummer die, die es im
    Job schon hat, sonst die kleinste freie – W-002 F2). Mit Revolver:
    der Platz, den es im Job schon hat; sonst seine Nummer, wenn der Platz im Job frei
    ist; sonst der erste freie. `vorgemerkt`: {Nummer: Kennung} für Werkzeuge, die gleich
    mit in den Job kommen (Schruppen und Schlichten in einem Schritt). None, wenn alle
    Plätze belegt sind.

    Hat die Maschine des Jobs (oder `maschine`, ihre Datei) ein Magazin (W-002 Stufe H2), gilt
    dessen Nummer (magazin.nummer). Am Revolver der Platz, auf dem es dort beladen ist, wenn
    der im Job frei ist; sonst der erste freie, auf dem kein anderes Werkzeug beladen ist
    (sind alle beladen, der erste freie – dann rüstet der Bediener um).
    """
    from . import magazin as mg

    magazin = mg.des_jobs(job, bibliothek, maschine)
    if magazin is not None and not nummern:
        return mg.nummer(magazin, job, werkzeug, vorgemerkt)
    if not nummern:
        if werkzeug.nummer > 0:
            return werkzeug.nummer
        # Ohne Nummer (W-002 F2): der Platz, den es im Job schon hat, sonst eine freie Nummer.
        eintrag = eintrag_von(job, werkzeug, bibliothek) if job is not None else None
        if eintrag is not None and eintrag.nummern:
            return eintrag.nummer
        belegt = set(vorgemerkt or {}) | {w.nummer for w in bibliothek.werkzeuge}
        if job is not None:
            belegt |= set(auf_plaetzen(job, bibliothek))
        return next(n for n in range(1, len(belegt) + 2) if n not in belegt)
    if job is not None:
        eintrag = eintrag_von(job, werkzeug, bibliothek)
        if eintrag is not None and eintrag.nummern:
            return eintrag.nummer
        belegt = set(auf_plaetzen(job, bibliothek))
    else:
        belegt = set()
    belegt |= {n for n, kennung in (vorgemerkt or {}).items() if kennung != werkzeug.kennung}
    wunsch, beladen = werkzeug.nummer, set()
    if magazin is not None:
        eintrag = magazin.eintrag_von(werkzeug)
        wunsch = eintrag.platz if eintrag is not None else 0
        beladen = {e.platz for e in magazin.eintraege if e.werkzeug != werkzeug.kennung}
    if wunsch in nummern and wunsch not in belegt:
        return wunsch
    frei = [n for n in sorted(nummern) if n not in belegt]
    return next((n for n in frei if n not in beladen), frei[0] if frei else None)


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


def nummern_nach_magazin(eintraege_, magazin, nummern=()):
    """{id(Eintrag): Nummer} – wie „Nummern aus dem Magazin“ (W-002 Stufe H3, E4) die Werkzeuge
    des Jobs nummeriert. An der Fräse (`nummern` leer): die aus dem Magazin; am Revolver
    (`nummern`: seine Plätze) der Platz, auf dem es beladen ist. Die übrigen behalten ihre
    Nummer, wenn sie frei ist und kein Werkzeug des Magazins sie hat (am Revolver: auf dem Platz
    keins beladen ist) – sonst die kleinste solche (am Revolver der erste freie Platz, auf dem
    nichts beladen ist, sonst der erste freie)."""
    ziel = {}
    if nummern:
        reserviert = {e.platz for e in magazin.eintraege if e.platz > 0}
    else:
        reserviert = {e.nummer for e in magazin.eintraege}
    for eintrag in eintraege_:
        im = magazin.eintrag_von(eintrag.werkzeug) if eintrag.werkzeug is not None else None
        if im is None:
            continue
        if not nummern:
            ziel[id(eintrag)] = im.nummer
        elif im.platz > 0 and im.platz in nummern:
            ziel[id(eintrag)] = im.platz
    vergeben = set(ziel.values())
    rest = [e for e in eintraege_ if id(e) not in ziel]
    for eintrag in rest:  # erst die, die ihre Nummer behalten können
        n = eintrag.nummer
        if n > 0 and n not in vergeben and n not in reserviert and (not nummern or n in nummern):
            ziel[id(eintrag)] = n
            vergeben.add(n)
    for eintrag in rest:
        if id(eintrag) in ziel:
            continue
        if nummern:
            frei = [n for n in sorted(nummern) if n not in vergeben]
            n = next((n for n in frei if n not in reserviert), frei[0] if frei else eintrag.nummer)
        else:
            n = 1
            while n in vergeben or n in reserviert:
                n += 1
        ziel[id(eintrag)] = n
        vergeben.add(n)
    return ziel


def nummern_aus_magazin(job, bibliothek, magazin, nummern=()):
    """„Nummern aus dem Magazin“ (E4): die Controller des Jobs (und seiner Aufspannung) nach
    nummern_nach_magazin – ihre Namen folgen („T7 Schruppen“ → „T3 Schruppen“). In der
    Transaktion des Aufrufers; gibt die geänderten Controller zurück."""
    alle = eintraege(job, bibliothek)
    ziel = nummern_nach_magazin(alle, magazin, nummern)
    geaendert = []
    for eintrag in alle:
        geaendert += _nummer_setzen(eintrag.controller, ziel[id(eintrag)])
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
