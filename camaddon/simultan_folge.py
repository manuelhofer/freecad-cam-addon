# SPDX-License-Identifier: LGPL-2.1-or-later
"""Schrupp-Zwischenlagen mit der anschließenden Simultanbearbeitung gemeinsam wählen.

Jeder Schruppzweig erhält seine eigene unverändernde Jobansicht und seinen eigenen
Materialstand. Die vorhandene Schlichtplanung prüft Werkzeug, Bahn, Anstellung und
die gesamte Maschinenfahrt. Nur ihre vollständig zugelassenen Sieger konkurrieren.
Das Minimum gilt für den angegebenen endlichen Suchraum; weder zusätzliche
Aufspannungen noch beliebige räumliche Rohteile sind dadurch automatisch geplant.
"""

import math

import Path

from . import bahn as bn
from . import schruppen3d as r3
from . import simultan_planung as sp
from .sprache import tr


def schruppen_vor(operation):
    """Direkt vorhergehendes gewöhnliches 3D-Schruppen, sonst None."""
    job = sp.job_von(operation)
    if job is None:
        return None
    aktive = [o for o in job.Operations.Group if getattr(o, "Active", True)]
    if operation not in aktive or aktive.index(operation) == 0:
        return None
    op = aktive[aktive.index(operation) - 1]
    return op if r3.ist_schruppen3d(op) and not r3.ist_restschruppen(op) else None


def zwischenlagen(von, bis, schritt, aktuell):
    """Endlichen Bereich einschließlich Endwert und aktueller Einstellung erzeugen."""
    werte = (von, bis, schritt, aktuell)
    if not all(math.isfinite(float(v)) and float(v) > 0 for v in werte) or bis < von:
        raise ValueError(tr("s5f.fehler.bereich"))
    anzahl = int(math.floor((bis - von) / schritt + 1e-9))
    if anzahl > 100:
        raise ValueError(tr("s5f.fehler.anzahl"))
    return tuple(sorted({round(von + i * schritt, 9) for i in range(anzahl + 1)} | {bis, aktuell}))


def vergleichen(
    operation,
    pruefung,
    bibliothek,
    lagen,
    richtungen=sp.RICHTUNGEN,
    anstellungen=sp.ANSTELLUNGEN,
    fortschritt=None,
    controller=None,
    alle=False,
    feinheit=None,
):
    """Alle angegebenen Zwischenlagen samt Schlichtvergleich unverändernd auswerten. `alle` und
    `feinheit` wie bei simultan_planung.vergleichen (jede Kugel, Richtung und Anstellung; die
    Grathöhe, für die die Bahn gerechnet wird)."""
    grob = schruppen_vor(operation)
    if grob is None:
        raise ValueError(tr("s5f.fehler.schruppen"))
    lagen = tuple(sorted({float(v) for v in lagen} | {float(grob.Zwischenlagen)}))
    if not lagen or not all(math.isfinite(v) and v > 0 for v in lagen) or len(lagen) > 102:
        raise ValueError(tr("s5f.fehler.bereich"))
    controller = list(controller) if controller is not None else None
    job = sp.job_von(operation)
    plan = sp.Planung(
        quelle=operation,
        zustand=sp._zustand(operation),
        pruefung=pruefung,
        sicherheitszustand=sp._sicherheitszustand(pruefung, bibliothek),
        schruppen=grob,
        vollstaendig=False,
    )
    # Die aktuelle Einstellung zuerst vollständig zulassen: danach brauchen
    # nachweislich langsamere Maschinenfahrten keine erneute genaue Kollision.
    aktuell = float(grob.Zwischenlagen)
    for lage in (aktuell, *(v for v in lagen if v != aktuell)):
        if fortschritt is not None and not fortschritt(0):
            raise ValueError(tr("s5p.fehler.unvollstaendig"))
        schruppen = sp._Ansicht(grob, Zwischenlagen=lage, Rampenanlauf=True)
        kandidat = sp._job_mit(job, grob, schruppen)
        schlicht = sp._Ansicht(operation)
        kandidat = sp._job_mit(kandidat, operation, schlicht)
        try:
            vf = float(grob.ToolController.HorizFeed) * 60
            ve = float(grob.ToolController.VertFeed) * 60
            bahn = r3.rechne(schruppen, kandidat, kandidat.Model.Group, vf, ve)
            # Der öffentliche ObjectOp-Vertrag enthält Label/Kommentar vor der
            # Bahn und den Rückzug danach. Auch diese Wörter gehören zum echten
            # Export, nicht nur die Bewegungspunkte aus rechne().
            befehle = [Path.Command(f"({grob.Label})")]
            if grob.Comment:
                befehle.append(Path.Command(f"({grob.Comment})"))
            befehle.extend(bn.befehle(bahn.punkte, vf, ve))
            befehle.append(Path.Command("G0", {"Z": float(grob.ClearanceHeight)}))
            schruppen.Path = Path.Path(befehle)
            teilplan = None
            for aktueller_plan, variante in sp.vergleichen(
                schlicht,
                pruefung,
                bibliothek,
                richtungen,
                anstellungen,
                fortschritt=fortschritt,
                controller=controller,
                zeitgrenze=plan.beste.sekunden if plan.beste is not None else math.inf,
                alle=alle,
                feinheit=feinheit,
            ):
                teilplan = aktueller_plan
                variante.zwischenlagen = lage
                variante.schruppoperation = schruppen
                if not any(v is variante for v in plan.varianten):
                    plan.varianten.append(variante)
                if fortschritt is not None and not fortschritt(0):
                    raise ValueError(tr("s5p.fehler.unvollstaendig"))
                yield plan, variante
            if (
                teilplan is not None
                and teilplan.beste is not None
                and (plan.beste is None or teilplan.beste.sekunden < plan.beste.sekunden)
            ):
                plan.beste = teilplan.beste
        except (ValueError, RuntimeError) as fehler:
            if fortschritt is not None and not fortschritt(0):
                raise ValueError(tr("s5p.fehler.unvollstaendig")) from fehler
            variante = sp.Variante(
                "",
                "",
                grund=str(fehler),
                werkzeug=grob.ToolController,
                zwischenlagen=lage,
                schruppoperation=schruppen,
            )
            plan.varianten.append(variante)
            yield plan, variante
        # Die Tabelle braucht nur Messwerte/Befunde. Maschinenstationen und
        # virtuelle Pfade langsamerer Zweige nicht über den ganzen Suchraum
        # behalten; nur der übernehmbare Sieger benötigt seine vollständige Bahn.
        for v in plan.varianten:
            if v is not plan.beste:
                v.fahrt = v.operation = v.job = v.schruppoperation = None
    plan.vollstaendig = True
