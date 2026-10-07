# SPDX-License-Identifier: LGPL-2.1-or-later
"""3D-Schlichtbahn und Anstellung gemeinsam für eine konkrete Maschine vergleichen.

Verglichen werden endliche Bahnvarianten mit derselben Kugel und Grathöhe.
Kontaktwinkel und Oberflächen-Stichproben sind Zulassungsbedingungen. Danach
zählt die vollständige Maschinenfahrt, einschließlich An-/Abfahren und weiterer
Operationen des Jobs. Die schnellsten Kandidaten werden nacheinander genau auf
Kollision geprüft. Sobald einer besteht, können langsamere nicht gewinnen.

Alle Varianten sind Python-Ansichten vorhandener Objekte; der Vergleich ändert
weder das Dokument noch eine Werkzeugbibliothek. Nur uebernehmen schreibt, in
einer rückgängig machbaren Transaktion, die geprüften Einstellungen der Operation.
"""

import hashlib
import math
from dataclasses import dataclass, field

import FreeCAD
import numpy as np
import Path

from . import abfahren as ab
from . import angestellt as an
from . import bahn as bn
from . import kollision as kb
from . import namen
from . import reichweite as rw
from . import schlichten3d as s3
from . import schwenken as sw
from . import simultan_operation as so
from . import vierachs_schlichten as vs
from .sprache import tr

RICHTUNGEN = ("x", "y", "spirale", "flaeche", "aequidistant")
ANSTELLUNGEN = ("X", "Y", "frei")
PROBEN = 19  # je Parameterachse einer Fläche; keine vollständige Abtragsprüfung
GENAU = 0.05  # mm zusätzlich zur verlangten Grathöhe, für Vernetzung und Bahninterpolation


class _Ansicht:
    """Eigene Attribute, alles andere vom unveränderten FreeCAD-Objekt lesen."""

    def __init__(self, quelle, **werte):
        self._quelle = quelle
        self.__dict__.update(werte)

    def __getattr__(self, name):
        return getattr(self._quelle, name)


@dataclass
class Variante:
    """Ergebnis einer Bahn-/Anstellungskombination; nur kollision_geprueft ist übernehmbar."""

    richtung: str
    anstellung: str
    sekunden: float = math.inf
    rest: float = math.inf
    schnittwinkel: float = 0.0
    grund: str = ""
    werkzeug: object = field(default=None, repr=False)
    befunde: list = field(default_factory=list)
    kollision_geprueft: bool = False
    operation: object = field(default=None, repr=False)
    job: object = field(default=None, repr=False)
    fahrt: object = field(default=None, repr=False)


@dataclass
class Planung:
    """Die verglichenen Varianten und die schnellste zugelassene davon."""

    varianten: list = field(default_factory=list)
    beste: object = None
    quelle: object = field(default=None, repr=False)
    zustand: str = ""


def _zustand(op):
    """Nur Eingaben vergleichen; berechnete Objektzustände dürfen sich dabei ändern."""
    from . import job_schnittwerte as js

    job = job_von(op)
    eigenschaften = (
        "Flaechen",
        "Grathoehe",
        "Aufmass",
        "Richtung",
        "Grenzwinkel",
        "Winkel",
        "Einseitig",
        "Sicherheitsabstand",
        "DurchmesserDavor",
        "EckenradiusDavor",
        "Anstellen",
        "Anstellwinkel",
        "Kippachse",
        "Wegkippen",
        "Randgang",
        "SafeHeight",
        "ClearanceHeight",
        "StartDepth",
        "FinalDepth",
        "Active",
    )
    werte = tuple((n, str(getattr(op, n, ""))) for n in eigenschaften)
    modelle = [o.Shape.exportBrepToString() for o in job.Model.Group]
    stock = job.Stock.Shape.exportBrepToString()
    controller = []
    for tc in js.werkzeug_controller(job):
        tool = tc.Tool
        controller.append(
            (
                tc.Name,
                tc.ToolNumber,
                float(tc.HorizFeed),
                float(tc.VertFeed),
                str(tc.SpindleSpeed),
                tuple(
                    (n, str(getattr(tool, n, "")))
                    for n in (
                        "ToolBitID",
                        "Diameter",
                        "Length",
                        "CuttingEdgeHeight",
                        "ShankDiameter",
                        "BallRadius",
                    )
                ),
            )
        )
    pfade = [
        (o.Name, bool(o.Active), [c.toGCode() for c in o.Path.Commands])
        for o in job.Operations.Group
        if o != op and hasattr(o, "Path")
    ]
    daten = (
        op.ToolController.Name,
        werte,
        modelle,
        stock,
        controller,
        pfade,
        repr(rw.nullpunkt(job)),
    )
    return hashlib.sha256(repr(daten).encode()).hexdigest()


def job_von(operation):
    """Der CAM-Job einer Operation, über deren Operationsgruppe."""
    for gruppe in operation.InList:
        for job in [gruppe, *gruppe.InList]:
            if operation in getattr(getattr(job, "Operations", None), "Group", []):
                return job
    return None


def _job_mit(job, op, variante):
    ansicht = _Ansicht(job)
    gruppe = _Ansicht(
        job.Operations, Group=[variante if o == op else o for o in job.Operations.Group]
    )
    ansicht.Operations = gruppe
    gruppe.InList = [ansicht]
    variante.InList = [gruppe]
    return ansicht


def _oberflaechenproben(form, namen):
    punkte = []
    for name in namen:
        flaeche = form.getElement(name)
        u0, u1, v0, v1 = flaeche.ParameterRange
        for u in np.linspace(u0, u1, PROBEN):
            for v in np.linspace(v0, v1, PROBEN):
                p = flaeche.valueAt(float(u), float(v))
                if flaeche.isInside(p, 1e-6, True):
                    punkte.append((p.x, p.y, p.z))
    if not punkte:
        raise ValueError(tr("s5p.fehler.proben"))
    return np.array(punkte)


def oberflaeche(punkte, bahn, radius):
    """Größter Abstand einer Oberflächenprobe zur überstrichenen Kugelhülle im Vorschub."""
    strecken = [(a, b) for a, b in zip(bahn, bahn[1:], strict=False) if not b.eilgang]
    if not strecken:
        return math.inf
    von = np.array([an_mitte(a, radius) for a, _b in strecken])
    nach = np.array([an_mitte(b, radius) for _a, b in strecken])
    weg = nach - von
    quadrat = np.maximum(np.sum(weg * weg, axis=1), 1e-15)
    rest = []
    for k in range(0, len(punkte), 64):
        differenz = punkte[k : k + 64, None, :] - von[None, :, :]
        anteil = np.clip(np.sum(differenz * weg[None, :, :], axis=2) / quadrat, 0.0, 1.0)
        abstand = np.linalg.norm(differenz - anteil[..., None] * weg[None, :, :], axis=2)
        rest.extend(np.min(abstand, axis=1) - radius)
    return float(max(rest))


def an_mitte(punkt, radius):
    """Kugelmitte einer senkrecht gespeicherten Bahn."""
    return (punkt.x, punkt.y, punkt.z + radius)


def kontaktwinkel(form, punkte, radius, aufmass, cache=None):
    """Kleinster Kontaktwinkel an Vorschubpunkten und den Mitten ihrer Verbindungen."""
    stellen, richtungen = [], []
    for a, b in zip(punkte, punkte[1:], strict=False):
        if b.eilgang:
            continue
        stellen.append(
            tuple(b.spitze[i] + radius * b.achse[i] - (radius if i == 2 else 0) for i in range(3))
        )
        richtungen.append(b.achse)
        if not a.eilgang:
            mitte = tuple(
                (a.spitze[i] + radius * a.achse[i] + b.spitze[i] + radius * b.achse[i]) / 2
                - (radius if i == 2 else 0)
                for i in range(3)
            )
            richtung = np.array(a.achse) + np.array(b.achse)
            richtung /= np.linalg.norm(richtung)
            stellen.append(mitte)
            richtungen.append(tuple(richtung))
    normalen = an.normalen(form, stellen, radius, aufmass, cache=cache)
    winkel = [
        math.degrees(math.acos(float(np.clip(np.dot(n, a), -1.0, 1.0))))
        for n, a in zip(normalen, richtungen, strict=True)
        if n is not None
    ]
    return min(winkel) if winkel else 0.0


def vergleichen(
    op,
    pruefung,
    bibliothek=None,
    richtungen=RICHTUNGEN,
    anstellungen=ANSTELLUNGEN,
    fortschritt=None,
    controller=None,
):
    """Planung erzeugen; Generator liefert (Planung, aktuelle Variante) für eine lebendige UI.

    Keine globale Optimalitätsbehauptung: die schnellste zugelassene Kombination
    unter diesen Varianten, für diesen Job, diese Maschine und dieses Werkzeug.
    """
    job = job_von(op)
    if job is None or not s3.ist_schlichten3d(op) or sw.ist_ebene(job):
        raise ValueError(tr("s5p.fehler.operation"))
    from . import job_schnittwerte as js

    controller = list(controller) if controller is not None else js.werkzeug_controller(job)
    controller = [
        tc for tc in controller if an.radius_von(_Ansicht(op, ToolController=tc)) is not None
    ]
    if not controller:
        raise ValueError(tr("s5p.fehler.kugel"))
    nullpunkt = rw.nullpunkt(job)
    form = vs._teil(job.Model.Group)
    namen = list(op.Flaechen)
    proben = _oberflaechenproben(form, namen)
    plan = Planung(quelle=op, zustand=_zustand(op))
    normalen_cache = {}
    for tc in controller:
        radius = an.radius_von(_Ansicht(op, ToolController=tc))
        aufnahme = pruefung.werkzeugaufnahme(tc.ToolNumber)
        if aufnahme is None:
            raise ValueError(tr("s5p.fehler.aufnahme"))
        maschine = sw.Maschine(pruefung, aufnahme, rw.einspannung(tc, bibliothek), nullpunkt)
        if len(maschine.rundachsen) != 2:
            raise ValueError(tr("s5p.fehler.maschine"))
        for richtung in richtungen:
            quelle = _Ansicht(op, Richtung=richtung, ToolController=tc, Randgang=True)
            try:
                bahn = s3.rechne(
                    quelle, job, job.Model.Group, float(tc.HorizFeed) * 60, float(tc.VertFeed) * 60
                )
                dicht = an.gerade(bahn.punkte)
                befehle = bn.befehle(dicht, float(tc.HorizFeed) * 60, float(tc.VertFeed) * 60)
                # FreeCADs ObjectOp hängt nach opExecute den Rückzug auf ClearanceHeight an.
                # Diese Bewegung muss schon im geprüften Kandidaten enthalten sein.
                befehle.append(Path.Command("G0", {"Z": float(op.ClearanceHeight)}))
                rest = oberflaeche(proben, dicht, radius)
            except (ValueError, RuntimeError) as fehler:
                for um in anstellungen:
                    variante = Variante(richtung, um, grund=str(fehler), werkzeug=tc)
                    plan.varianten.append(variante)
                    yield plan, variante
                continue
            for um in anstellungen:
                variante = Variante(richtung, um, rest=rest, werkzeug=tc)
                plan.varianten.append(variante)
                try:
                    if rest > float(op.Grathoehe) + float(op.Aufmass) + GENAU:
                        raise ValueError(tr("s5p.fehler.rest", rest=f"{rest:.3f}"))
                    achsen = an.achsen(
                        befehle,
                        form,
                        radius,
                        float(op.Aufmass),
                        um,
                        float(op.Anstellwinkel),
                        vorausschau=True,
                        normalen_cache=normalen_cache,
                    )
                    virtuell = _Ansicht(
                        op,
                        ToolController=tc,
                        Path=Path.Path(befehle),
                        Anstellen=True,
                        Wegkippen=False,
                        Werkzeugachsen=[FreeCAD.Vector(*a) for a in achsen],
                        Richtung=richtung,
                        Kippachse=um,
                        Randgang=True,
                    )
                    variante.operation = virtuell
                    variante.job = _job_mit(job, op, virtuell)
                    punkte = an.punkte(befehle, achsen, radius)
                    variante.schnittwinkel = kontaktwinkel(
                        form, punkte, radius, float(op.Aufmass), normalen_cache
                    )
                    if variante.schnittwinkel < float(op.Anstellwinkel) - 0.05:
                        raise ValueError(
                            tr("s5p.fehler.winkel", winkel=f"{variante.schnittwinkel:.2f}")
                        )
                    # Explizit rechnen: abfahrt übergeht eine Operation, die nicht erreichbar ist.
                    so.befehle(virtuell, maschine)
                    grenzen = pruefung.pruefe_job(variante.job, nullpunkt, bibliothek)
                    if grenzen.ueberschreitungen:
                        raise ValueError(tr("s5p.fehler.grenzen"))
                    variante.fahrt = ab.abfahrt(pruefung, variante.job, nullpunkt, bibliothek)
                    if not variante.fahrt.stationen or len(variante.fahrt.operationen) != len(
                        rw._operationen(variante.job)
                    ):
                        raise ValueError(tr("s5p.fehler.leer"))
                    variante.sekunden = variante.fahrt.dauer
                except (ValueError, RuntimeError) as fehler:
                    variante.grund = str(fehler)
                yield plan, variante
    for variante in sorted((v for v in plan.varianten if not v.grund), key=lambda v: v.sekunden):
        ergebnis = kb.kollision(
            variante.fahrt,
            variante.job,
            nullpunkt,
            bibliothek,
            fortschritt=fortschritt,
            rohteil=True,
        )
        if ergebnis.abgebrochen or ergebnis.hinweise:
            variante.grund = tr("s5p.fehler.unvollstaendig")
        elif ergebnis.befunde:
            variante.befunde = ergebnis.befunde
            erster = ergebnis.befunde[0]
            variante.grund = (
                tr("s5p.fehler.kollision")
                + " "
                + erster.a
                + " / "
                + erster.b
                + f" ({erster.abstand:.3f} mm)"
            )
        else:
            variante.kollision_geprueft = True
            plan.beste = variante
        yield plan, variante
        if plan.beste is not None:
            break


def uebernehmen(op, plan):
    """Die gewinnende Einstellung speichern; keine unvollständig geprüfte Bahn übernehmen."""
    beste = plan.beste if plan is not None else None
    if beste is None or beste.grund or not beste.kollision_geprueft:
        raise ValueError(tr("s5p.fehler.keine"))
    if plan.quelle != op or plan.zustand != _zustand(op):
        raise ValueError(tr("s5p.fehler.veraltet"))
    doc = op.Document
    doc.openTransaction(tr("s5p.uebernehmen"))
    try:
        automatisch = op.Label == s3._name(op.ToolController, float(op.DurchmesserDavor))
        op.ToolController = beste.werkzeug
        op.OpToolDiameter = beste.werkzeug.Tool.Diameter
        if automatisch:
            op.Label = namen.eindeutig(
                doc, s3._name(beste.werkzeug, float(op.DurchmesserDavor)), op
            )
        op.Richtung = beste.richtung
        op.Kippachse = beste.anstellung
        op.Anstellen = True
        op.Wegkippen = False
        op.Randgang = True
        op.touch()
        doc.recompute()
        if not op.Path.Commands or not op.Werkzeugachsen:
            raise ValueError(tr("s5p.fehler.leer"))
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
