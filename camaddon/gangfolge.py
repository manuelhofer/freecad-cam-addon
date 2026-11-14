# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Folge der Schlichtgänge in „Weiter bearbeiten“ (Manuel, 2026-11-14, Antwort auf die Frage nach
zwei gleichen Schlichtschnitten: „a <-- aber es muss auch die möglichkeit geben das man leerfahrten
eingeben kann … erstes vorschlichten ... und danach nochmal erstes vorschlichten .... dann messsen
... dann vertigschlichten ... und dann nochmal vertig schlichten ... dann hat man immer 100 % das
richtige mass ... aber klar alles als option“).

Aus den Operationen eines Schlichtgangs, die der Assistent gerade angelegt hat, wird die Folge:

    Schnitt mit halbem Aufmaß → [Leerfahrt] → [Messstopp] → derselbe Schnitt auf Maß → [Leerfahrt]

- **Zwei gleiche Schnitte:** Der zweite ist eine Kopie des ersten (FreeCADs „Operation kopieren“)
  mit dem Aufmaß des Endes – derselbe Fräser, dieselbe Tiefe, derselbe Vorschub. Dann drängt es
  beide Male gleich weit ab: Was nach dem ersten gemessen wird, ist, was der zweite ausgleicht.
- **Leerfahrt:** derselbe Schnitt noch einmal ohne Zustellung (leerfahrt.py).
- **Messstopp:** zwischen den beiden Schnitten (messstopp.py; mit Taster und Zyklus misst die
  Maschine selbst) – nach der Leerfahrt des ersten, denn erst dann stimmt, was man misst.

Läuft ohne Oberfläche.
"""

from dataclasses import dataclass, field

from . import leerfahrt as lf
from . import messstopp as ms
from . import namen
from .sprache import tr


@dataclass
class Folge:
    """Was folge() angelegt hat – in der Reihenfolge des Jobs."""

    leer_vor: list = field(default_factory=list)  # Leerfahrten des ersten Schnitts
    stopp: object = None  # der Messstopp dazwischen
    fertig: list = field(default_factory=list)  # der zweite Schnitt (Kopien auf Maß)
    leer_fertig: list = field(default_factory=list)  # seine Leerfahrten

    @property
    def alle(self):
        dazu = [self.stopp] if self.stopp is not None else []
        return [*self.leer_vor, *dazu, *self.fertig, *self.leer_fertig]


def schnitte(ops):
    """Die Operationen aus `ops`, die schneiden – ohne Messstopps und Leerfahrten."""
    return [
        op
        for op in ops
        if getattr(op, "ToolController", None) is not None
        and not ms.ist_messstopp(op)
        and not lf.ist_leerfahrt(op)
    ]


def halbes_aufmass(davor, ende=0.0):
    """Das Aufmaß des ersten von zwei gleichen Schnitten: mitten zwischen dem des Gangs davor und
    dem des Endes (0,3 → 0,15 → 0), auf Tausendstel."""
    davor, ende = max(float(davor), 0.0), max(float(ende), 0.0)
    return round(ende + max(davor - ende, 0.0) / 2.0, 3)


def kopie(job, op, aufmass):
    """Die Operation `op` noch einmal im Job (hinten), mit dem Aufmaß `aufmass` – alles andere
    gleich. Gibt die Kopie zurück."""
    import PathScripts.PathUtils as PathUtils

    neu = job.Document.copyObject([op], False)[0]
    PathUtils.addToJob(neu, job.Name)
    setattr(neu, lf.gang_feld(op), float(aufmass))
    if float(aufmass) <= 1e-9:
        text = tr("gf.auf_mass", name=op.Label)
    else:
        from . import einheiten

        text = tr(
            "gf.auf", name=op.Label, aufmass=einheiten.text(float(aufmass), einheiten.LAENGE, 3)
        )
    neu.Label = namen.eindeutig(job.Document, text, neu)
    return neu


def folge(job, ops, aufmass_ende=None, leerfahrt=False, stopp_anlegen=None):
    """Legt hinter den gerade angelegten Operationen `ops` (ein Schlichtgang) den Rest der Folge
    an – ohne eigene Transaktion. `leerfahrt`: je Schnitt eine Leerfahrt danach. `aufmass_ende`
    (mm, nicht None): zwei gleiche Schnitte – jede Operation mit Aufmaß noch einmal mit diesem
    Aufmaß; davor mit `stopp_anlegen(davor, danach)` (gibt die Messstopp-Operation zurück oder
    None) der Messstopp. Gibt die Folge zurück."""
    ergebnis = Folge()
    erste = schnitte(ops)
    if not erste:
        return ergebnis
    if leerfahrt:
        ergebnis.leer_vor = [lf.lege_an(job, op) for op in erste]
    if aufmass_ende is None:
        return ergebnis
    mit_aufmass = [
        op
        for op in erste
        if lf.gang_feld(op) is not None and lf.gang_aufmass(op) > float(aufmass_ende) + 1e-9
    ]
    if not mit_aufmass:
        return ergebnis
    if stopp_anlegen is not None:
        letzte = (ergebnis.leer_vor or erste)[-1]
        ergebnis.stopp = stopp_anlegen(letzte, mit_aufmass[0])
    ergebnis.fertig = [kopie(job, op, aufmass_ende) for op in mit_aufmass]
    if leerfahrt:
        ergebnis.leer_fertig = [lf.lege_an(job, op) for op in ergebnis.fertig]
    return ergebnis
