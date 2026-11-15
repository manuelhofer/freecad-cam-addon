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
- **„Bohrung fräsen“ und die Nut**, die in einem Gang schruppen und die Wand schlichten: Der erste
  Schnitt ist ihr Schlichtzug mit dem halben Aufmaß ihres Schruppens (0,3 → 0,15, teilen()), der
  zweite nur noch der Schlichtzug auf Maß (NurSchlichten) – Helix, Ringe und Bögen noch einmal
  gingen durch die Luft. Gemessen wird am Ø, also an der Wand.
- **Leerfahrt:** derselbe Schnitt noch einmal ohne Zustellung (leerfahrt.py) – bei Bohrung und Nut
  nur ihr Schlichtzug.
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


def schruppt_mit(op):
    """Schruppt `op` und schlichtet im selben Gang die Wand („Bohrung fräsen“, Nut mit Schlichten,
    nicht NurSchlichten)? Dann ist ihr Schlichtzug der Schnitt, der zweimal kommt."""
    return lf.nur_schlichtzug(op) and "Schlichtrest" in getattr(op, "PropertiesList", ())


def teilen(op, ende=0.0):
    """Der erste von zwei gleichen Schnitten bei einer Operation, die schruppt und schlichtet
    (schruppt_mit): Ihr Schlichtzug lässt die Hälfte zwischen ihrem Aufmaß und `ende` stehen
    (0,3 → 0,15) – nur, wenn er noch auf das Ende geht (sonst hat ihn schon jemand gesetzt). Gibt
    True zurück, wenn sie geteilt ist."""
    if not schruppt_mit(op) or lf.gang_aufmass(op) > float(ende) + 1e-9:
        return False
    halb = halbes_aufmass(float(op.Aufmass), ende)
    if halb <= float(ende) + 1e-9:
        return False
    op.Schlichtrest = halb
    return True


def kopie(job, op, aufmass):
    """Die Operation `op` noch einmal im Job (hinten), mit dem Aufmaß `aufmass` – alles andere
    gleich; schruppt `op` mit (schruppt_mit), nur ihr Schlichtzug. Gibt die Kopie zurück."""
    import PathScripts.PathUtils as PathUtils

    feld = lf.gang_feld(op)
    nur_schlichtzug = schruppt_mit(op)
    neu = job.Document.copyObject([op], False)[0]
    PathUtils.addToJob(neu, job.Name)
    if nur_schlichtzug:
        neu.NurSchlichten = True
    setattr(neu, feld, float(aufmass))
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
    Aufmaß (die, die schruppt und schlichtet, vorher geteilt: teilen()); davor mit
    `stopp_anlegen(davor, danach)` (gibt die Messstopp-Operation zurück oder None) der Messstopp.
    Gibt die Folge zurück."""
    ergebnis = Folge()
    erste = schnitte(ops)
    if not erste:
        return ergebnis
    if aufmass_ende is not None:
        for op in erste:
            teilen(op, aufmass_ende)  # gerechnet wird mit dem Rest der Folge (der Aufrufer)
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


def wand_rest(op):
    """So viel lässt `op` an der Wand stehen (mm) – was ein Taster nach ihr misst: der Schlichtrest
    ihres Schlichtzugs, sonst ihr Aufmaß; eine Leerfahrt wie ihre Quelle (ihr „Aufmass“ ist das
    des Gangs, beim Räumen das am Boden)."""
    if op is None:
        return 0.0
    if lf.ist_leerfahrt(op) and getattr(op, "Quelle", None) is not None:
        return wand_rest(op.Quelle)
    feld = lf.gang_feld(op)
    if feld is None and lf.gang_aufmass(op) is not None:
        return 0.0  # „Bohrung fräsen“ ohne Schlichtzug: die Helix auf Maß
    feld = "Schlichtrest" if feld == "Schlichtrest" else "Aufmass"
    wert = getattr(op, feld, 0.0)
    return max(0.0, float(getattr(wert, "Value", wert) or 0.0))


def ist_bohrungsgang(op):
    """„Bohrung fräsen“ oder ihre Leerfahrt? Ihr Gang ist der der Bohrung (gemessen am Ø
    zwischen ihren zwei Schnitten), nicht der der Wände."""
    from . import bohrung as bo

    if lf.ist_leerfahrt(op):
        op = getattr(op, "Quelle", None)
    return bo.ist_bohrungsfraesen(op)


def davor_messen(ops):
    """Nach welcher der Operationen `ops` (in der Folge des Jobs) ein Messstopp „davor“ die Wände
    misst: die letzte mit Werkzeug, die schneidet – kein Messstopp, nicht „Bohrung fräsen“ und
    ihre Leerfahrt (ist_bohrungsgang; sonst maß der Messstopp beim Schlichten nach den Löchern
    die fertige Bohrung Ø 30 statt der Tasche 39,4 × 19,4, Gegenprüfung 2026-11-14). None, wenn
    keine."""
    return next(
        (
            op
            for op in reversed(list(ops))
            if getattr(op, "ToolController", None) is not None
            and not ms.ist_messstopp(op)
            and not ist_bohrungsgang(op)
        ),
        None,
    )


def _quelle(op):
    """`op`, bei einer Leerfahrt ihre Quelle."""
    if op is not None and lf.ist_leerfahrt(op):
        return getattr(op, "Quelle", None)
    return op


def ist_nutgang(op):
    """Eine Nut (auch nur ihr Schlichtgang) oder ihre Leerfahrt? Nach ihr misst der Taster die
    Breite der Nut (messen.nut_merkmal)."""
    from . import nut as nu

    return nu.ist_nut(_quelle(op))


def mess_flaechen(op, flaechen):
    """Die Flächen, an denen nach `op` gemessen wird: bei „Bohrung fräsen“ und der Nut (auch ihrer
    Leerfahrt) ihre Flächen – gemessen wird der Ø bzw. die Breite; sonst `flaechen` (die am Job
    gemerkten)."""
    from . import bohrung as bo

    op = _quelle(op)
    gang = op is not None and (bo.ist_bohrungsfraesen(op) or ist_nutgang(op))
    if gang and list(getattr(op, "Flaechen", []) or []):
        return list(op.Flaechen)
    return list(flaechen)


def messmerkmal(form, flaechen, davor):
    """Was ein Taster nach der Operation `davor` misst (messen.Merkmal mit dem Soll): das Merkmal
    der Flächen (mess_flaechen) – nach einer Nut ihre Breite (messen.nut_merkmal; ihre Flächen
    können auch nur eine Wand der Ringnut sein, die sonst als Bohrung gälte) –, um den Rest an der
    Wand (wand_rest) – None, wenn sie keins ergeben."""
    from . import messen

    namen_ = mess_flaechen(davor, flaechen)
    if not namen_:
        return None
    try:
        if davor is not None and ist_nutgang(davor):
            m = messen.nut_merkmal(form, namen_)
        else:
            m = messen.merkmal(form, namen_)
    except Exception:  # noqa: BLE001 – Part.OCCError: ein Name passt nicht mehr zum Modell
        return None
    return None if m is None else messen.soll(m, wand_rest(davor))


def direkt_dahinter(gruppe, quellen, folge_ops):
    """Die Reihenfolge der Operationen `gruppe`, in der die Folge `folge_ops` (Leerfahrt, Messstopp,
    zweiter Schnitt …) direkt hinter der letzten ihrer `quellen` steht statt hinten am Job – bei den
    Löchern vor Senken und Gewinde (Manuel, 2026-11-15, Frage 3: „Empfehlung: (b)“: die Bohrung ist
    fertig und gemessen, bevor gesenkt wird). Die übrige Reihenfolge bleibt."""
    folge_namen = {o.Name for o in folge_ops}
    quellen_namen = {o.Name for o in quellen}
    rest = [o for o in gruppe if o.Name not in folge_namen]
    folge = [o for o in gruppe if o.Name in folge_namen]
    stellen = [i for i, o in enumerate(rest) if o.Name in quellen_namen]
    if not folge or not stellen:
        return list(gruppe)
    hinter = stellen[-1] + 1
    return rest[:hinter] + folge + rest[hinter:]
