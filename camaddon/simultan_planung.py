# SPDX-License-Identifier: LGPL-2.1-or-later
"""3D-Schlichtbahn und Anstellung gemeinsam für eine konkrete Maschine vergleichen.

Verglichen werden endliche Bahnvarianten mit derselben Kugel und Grathöhe.
Kontaktwinkel, Materialstand und vollständige Flächenzellen sind Zulassungsbedingungen. Danach
zählt die vollständige Maschinenfahrt, einschließlich An-/Abfahren und weiterer
Operationen des Jobs. Die schnellsten Kandidaten werden nacheinander genau auf
Kollision geprüft. Sobald einer besteht, können langsamere nicht gewinnen.

Alle Varianten sind Python-Ansichten vorhandener Objekte; der Vergleich ändert
weder das Dokument noch eine Werkzeugbibliothek. Nur uebernehmen schreibt, in
einer rückgängig machbaren Transaktion, die geprüften Einstellungen der Operation.
"""

import hashlib
import math
import re
from dataclasses import dataclass, field
from types import SimpleNamespace

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
from . import simultan_abtrag as sa
from . import simultan_operation as so
from . import vierachs_schlichten as vs
from .sprache import tr

RICHTUNGEN = ("x", "y", "spirale", "flaeche", "aequidistant")
ANSTELLUNGEN = ("X", "Y", "frei", "frei_gesamt")
# Ohne „Alle Kombinationen“ (P-2026-10-09-04): Runden je Kugel – die größte zuerst, sie ist mit
# den weitesten Zeilen die schnellste, wenn sie überall hinkommt –, erst entlang der Fläche mit
# den beiden freien Anstellungen, dann die übrigen Richtungen frei, dann die festen Anstellungen;
# die nächste Kugel erst, wenn nichts zugelassen wird. Am Freiformbeispiel 2 statt 60 Varianten
# (Manuel, 2026-10-09: „Ja, mach das so“); an der Kuppel des Szenarios schneidet „entlang der
# Fläche“ ins Teil, die zweite Stufe findet Zeilen X frei.
SINNVOLL_RICHTUNG = "flaeche"
VORGABE_FEINHEIT = 0.25  # Anteil der Grathöhe, für den die Bahn ohne Angabe gerechnet wird
SINNVOLL_ANSTELLUNGEN = ("frei", "frei_gesamt")


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
    material_geprueft: bool = False
    material: object = field(default=None, repr=False)
    bahngrathoehe: float = 0.0
    operation: object = field(default=None, repr=False)
    job: object = field(default=None, repr=False)
    fahrt: object = field(default=None, repr=False)
    zwischenlagen: float = 0.0
    schruppoperation: object = field(default=None, repr=False)


@dataclass
class Planung:
    """Die verglichenen Varianten und die schnellste zugelassene davon."""

    varianten: list = field(default_factory=list)
    beste: object = None
    quelle: object = field(default=None, repr=False)
    zustand: str = ""
    pruefung: object = field(default=None, repr=False)
    sicherheitszustand: str = ""
    schruppen: object = field(default=None, repr=False)
    vollstaendig: bool = True


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
        "BahnGrathoehe",
        "SafeHeight",
        "ClearanceHeight",
        "StartDepth",
        "FinalDepth",
        "Active",
    )
    werte = tuple((n, str(getattr(op, n, ""))) for n in eigenschaften)
    modelle = [_geometrie(o.Shape) for o in job.Model.Group]
    stock = _geometrie(job.Stock.Shape)
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
        (
            o.Name,
            bool(o.Active),
            [c.toGCode() for c in o.Path.Commands],
            tuple(
                (n, str(getattr(o, n, "")))
                for n in (
                    "Zustellung",
                    "Zeilenabstand",
                    "Zwischenlagen",
                    "Aufmass",
                    "Flaechen",
                    "Gleichlauf",
                    "Rampenanlauf",
                    "Eintauchwinkel",
                    "Sicherheitsabstand",
                    "SafeHeight",
                    "ClearanceHeight",
                    "ToolController",
                )
            ),
        )
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


def _geometrie(form):
    """CAD-Geometrie ohne veränderliche Darstellungs- und Berechnungsnetze vergleichen."""
    brep = form.cleaned().exportBrepToString()
    # OCCT schreibt vor jedem Unterformverweis sieben Statusbits. Checked (Bit 3)
    # wird schon durch tessellate geändert, obwohl die Geometrie gleich bleibt.
    # Nur dieses Prüfmerkmal normalisieren; Kurven, Flächen, Toleranzen und Lage bleiben.
    return re.sub(r"(?m)^([01]{2})[01]([01]{4})(?=\n[+*\-])", r"\g<1>0\g<2>", brep)


def job_von(operation):
    """Der CAM-Job einer Operation, über deren Operationsgruppe."""
    for gruppe in operation.InList:
        for job in [gruppe, *gruppe.InList]:
            if operation in getattr(getattr(job, "Operations", None), "Group", []):
                return job
    return None


def _sicherheitszustand(pruefung, bibliothek):
    """Auch Maschinengeometrie, Achsgrenzen und externe Werkzeug-/Halterdaten schützen."""
    werte = []
    for obj in pruefung.maschine.Document.Objects:
        eigenschaften = []
        for name in obj.PropertiesList:
            if name in (
                "Proxy",
                "ExpressionEngine",
                "Label",
                "Label2",
                "Visibility",
                "ShapeMaterial",  # Darstellungsfarben werden beim ersten Anzeigen aufgebaut
                "_Part_ShapeCache",  # abgeleitete Anzeigeform eines App::Part
            ):
                continue
            wert = getattr(obj, name)
            if name == "Shape":
                wert = _geometrie(wert)
            eigenschaften.append((name, str(wert)))
        werte.append((obj.Name, eigenschaften))
    daten = (
        werte,
        (
            type(bibliothek).aus_dict(bibliothek.als_dict()).als_dict()
            if bibliothek is not None
            else None
        ),
    )
    return hashlib.sha256(repr(daten).encode()).hexdigest()


def _job_mit(job, op, variante):
    ansicht = _Ansicht(job)
    gruppe = _Ansicht(
        job.Operations, Group=[variante if o == op else o for o in job.Operations.Group]
    )
    ansicht.Operations = gruppe
    gruppe.InList = [ansicht]
    variante.InList = [gruppe]
    return ansicht


def kontaktwinkel(form, punkte, radius, aufmass, cache=None, fortschritt=None):
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
    normalen = an.normalen(form, stellen, radius, aufmass, cache=cache, fortschritt=fortschritt)
    winkel = [
        math.degrees(math.acos(float(np.clip(np.dot(n, a), -1.0, 1.0))))
        for n, a in zip(normalen, richtungen, strict=True)
        if n is not None
    ]
    if winkel and max(winkel) > 85:
        raise ValueError(tr("s5p.fehler.halbkugel"))
    return min(winkel) if winkel else 0.0


def _runden(controller, radius_von, richtungen, anstellungen, alle):
    """Die Runden des Vergleichs: je Runde (Werkzeuge, Richtungen, Anstellungen). Mit `alle`
    eine Runde mit allem. Sonst je Kugel, die größte zuerst, drei Stufen: SINNVOLL_RICHTUNG
    (fehlt sie unter `richtungen`, die erste) mit den SINNVOLL_ANSTELLUNGEN unter `anstellungen`
    (keine dabei: alle gegebenen), dann die übrigen Richtungen damit, dann alle Richtungen mit den
    übrigen Anstellungen; vergleichen() hört nach der ersten Runde mit einer zugelassenen Variante
    auf und überspringt eine Kugel, die den Flächenrand nicht erreicht."""
    richtungen, anstellungen = tuple(richtungen), tuple(anstellungen)
    if alle:
        yield list(controller), richtungen, anstellungen
        return
    erste = (SINNVOLL_RICHTUNG,) if SINNVOLL_RICHTUNG in richtungen else richtungen[:1]
    frei = tuple(a for a in anstellungen if a in SINNVOLL_ANSTELLUNGEN) or anstellungen
    stufen = [(erste, frei)]
    uebrige = tuple(r for r in richtungen if r not in erste)
    if uebrige:
        stufen.append((uebrige, frei))
    fest = tuple(a for a in anstellungen if a not in frei)
    if fest:
        stufen.append((richtungen, fest))
    for tc in sorted(controller, key=lambda t: -float(radius_von(t))):
        for r_liste, a_liste in stufen:
            yield [tc], r_liste, a_liste


def vergleichen(
    op,
    pruefung,
    bibliothek=None,
    richtungen=RICHTUNGEN,
    anstellungen=ANSTELLUNGEN,
    fortschritt=None,
    controller=None,
    zeitgrenze=math.inf,
    alle=False,
    feinheit=None,
):
    """Planung erzeugen; Generator liefert (Planung, aktuelle Variante) für eine lebendige UI.

    Keine globale Optimalitätsbehauptung: die schnellste zugelassene Kombination
    unter diesen Varianten, für diesen Job, diese Maschine und dieses Werkzeug.
    `alle`: jede Kugel mit jeder Richtung und Anstellung in einer Runde; sonst die Runden aus
    _runden (die größte Kugel zuerst, entlang der Fläche frei, dann die übrigen Richtungen, dann
    die festen Anstellungen – bis eine Variante zugelassen ist).
    `feinheit`: die Grathöhe (mm), für die die Bahn gerechnet wird – feiner als die verlangte,
    damit die Prüfung mit ihren Reserven die verlangte annimmt. Ohne Angabe die `BahnGrathoehe`
    der Operation, wenn sie eine hat (ein früherer Vergleich oder die Eingabe im
    Eigenschaftseditor), sonst VORGABE_FEINHEIT der Grathöhe.
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
    material = sa.Pruefstand(job, op, bibliothek, fortschritt=fortschritt)
    for name, messung in material.vorher:
        if messung.gruende:
            raise ValueError(name + ": " + "; ".join(messung.gruende))
    plan = Planung(
        quelle=op,
        zustand=_zustand(op),
        pruefung=pruefung,
        sicherheitszustand=_sicherheitszustand(pruefung, bibliothek),
    )
    feinheit = bahnfeinheit(op, feinheit)
    normalen_cache = {}

    def werkzeug(tc, richtungen, anstellungen):
        """Die Varianten eines Werkzeugs: gerechnet, am Material und an der Maschine geprüft."""
        radius = an.radius_von(_Ansicht(op, ToolController=tc))
        aufnahme = pruefung.werkzeugaufnahme(tc.ToolNumber)
        if aufnahme is None:
            raise ValueError(tr("s5p.fehler.aufnahme"))
        maschine = sw.Maschine(pruefung, aufnahme, rw.einspannung(tc, bibliothek), nullpunkt)
        from . import schlicht_rand

        try:
            schlicht_rand.ergaenzen(
                SimpleNamespace(punkte=[], umlaeufe=0),
                form,
                list(op.Flaechen),
                radius,
                float(op.Aufmass),
                float(op.SafeHeight),
                job.Stock.Shape.BoundBox.ZMax,
                float(op.Sicherheitsabstand),
                float(tc.HorizFeed) * 60,
                float(tc.VertFeed) * 60,
            )
        except ValueError as fehler:
            rand_versagt.add(tc.Name)
            for richtung in richtungen:
                for um in anstellungen:
                    variante = Variante(richtung, um, grund=str(fehler), werkzeug=tc)
                    plan.varianten.append(variante)
                    yield plan, variante
            return
        for richtung in richtungen:
            quelle = _Ansicht(
                op, Richtung=richtung, ToolController=tc, Randgang=True, BahnGrathoehe=feinheit
            )
            try:
                bahn = s3.rechne(
                    quelle, job, job.Model.Group, float(tc.HorizFeed) * 60, float(tc.VertFeed) * 60
                )
                dicht = an.gerade(bahn.punkte)
                befehle = bn.befehle(dicht, float(tc.HorizFeed) * 60, float(tc.VertFeed) * 60)
                # FreeCADs ObjectOp hängt nach opExecute den Rückzug auf ClearanceHeight an.
                # Diese Bewegung muss schon im geprüften Kandidaten enthalten sein.
                befehle.append(Path.Command("G0", {"Z": float(op.ClearanceHeight)}))
                einsatz = sa.einsatz_von(tc, bibliothek)
                if einsatz is None:
                    raise ValueError(tr("s5p.fehler.einsatz"))
                messung = material.messen(
                    dicht,
                    vs.form_des_controllers(tc),
                    einsatz,
                    float(op.Grathoehe) - sa.NC_RESERVE,
                    float(op.Aufmass),
                )
                rest = messung.rest + messung.unsicherheit
                if messung.gruende:
                    raise ValueError("; ".join(messung.gruende))
            except (ValueError, RuntimeError) as fehler:
                for um in anstellungen:
                    variante = Variante(richtung, um, grund=str(fehler), werkzeug=tc)
                    plan.varianten.append(variante)
                    yield plan, variante
                continue
            for um in anstellungen:
                variante = Variante(
                    richtung, um, rest=rest, werkzeug=tc, material=messung, bahngrathoehe=feinheit
                )
                plan.varianten.append(variante)
                try:
                    if rest > float(op.Grathoehe) + float(op.Aufmass):
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
                        fortschritt=fortschritt,
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
                        BahnGrathoehe=feinheit,
                        _pruefmaterial=[],
                    )
                    variante.operation = virtuell
                    variante.job = _job_mit(job, op, virtuell)
                    punkte = an.punkte(befehle, achsen, radius)
                    variante.schnittwinkel = kontaktwinkel(
                        form, punkte, radius, float(op.Aufmass), normalen_cache, fortschritt
                    )
                    if variante.schnittwinkel < float(op.Anstellwinkel) - 1e-6:
                        raise ValueError(
                            tr("s5p.fehler.winkel", winkel=f"{variante.schnittwinkel:.2f}")
                        )
                    # Explizit rechnen: abfahrt übergeht eine Operation, die nicht erreichbar ist.
                    teilprogramm = so.programm(virtuell, maschine)
                    if teilprogramm.ausgelassen:
                        # Dieser Vergleich verspricht vollständige Fertigbearbeitung.
                        # Eine kürzere Teilbahn darf kein vollständiger Gewinner werden.
                        raise ValueError(teilprogramm.hinweis)
                    programm = teilprogramm.befehle
                    virtuell._pruefprogramm = (so.pruefschluessel(maschine), tuple(programm))
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

    def zulassen(kandidaten):
        """Die Zulassung der schnellsten Kandidaten: Kugelschnitt am Teil, Maschinenbahn,
        Kontaktwinkel, Material und Kollision – bis die erste ganz besteht (plan.beste)."""
        for variante in sorted((v for v in kandidaten if not v.grund), key=lambda v: v.sekunden):
            # Eine bereits zugelassene Gesamtfolge bildet die obere Schranke. Die
            # feste Maschinenfahrt dieses Kandidaten ist schon vollständig gerechnet;
            # eine weitere Zulassungsprüfung kann sie nicht schneller machen.
            if variante.sekunden >= zeitgrenze:
                break
            # Der kontinuierliche Kugelschnitt darf auch zwischen Rasterstrahlen nicht ins Teil.
            dicht = sa._pfad(variante.operation)
            radius = an.radius_von(variante.operation)
            abstand_reserve = 0.00025 + sa.NC_RESERVE
            tiefste = sa.einschnitt(
                form, dicht, radius, grenze=abstand_reserve, fortschritt=fortschritt
            )
            if tiefste < abstand_reserve:
                variante.grund = tr("s5p.fehler.brep", abstand=f"{tiefste:.5f}")
                yield plan, variante
                continue
            operation_index = next(
                i for i, o in enumerate(rw._operationen(variante.job)) if o is variante.operation
            )
            wirklich, werkzeugachsen = sa.maschinenbahn(
                variante.fahrt,
                operation_index,
                radius,
                mit_achsen=True,
                fortschritt=fortschritt,
                materialdaten=variante.operation._pruefmaterial,
            )
            kontakt = [
                (p, a) for p, a in zip(wirklich, werkzeugachsen, strict=True) if not p.eilgang
            ]
            normalen = an.normalen(
                form,
                [(p.x, p.y, p.z) for p, _a in kontakt],
                radius,
                float(op.Aufmass),
                cache=normalen_cache,
                fortschritt=fortschritt,
            )
            winkel = [
                math.degrees(math.acos(float(np.clip(np.dot(n, a), -1, 1))))
                for n, (_p, a) in zip(normalen, kontakt, strict=True)
                if n is not None
            ]
            if not winkel or min(winkel) < float(op.Anstellwinkel) - 1e-6 or max(winkel) > 85:
                variante.grund = tr(
                    "s5p.fehler.winkel", winkel=f"{min(winkel) if winkel else 0:.2f}"
                )
                yield plan, variante
                continue
            variante.schnittwinkel = min(winkel)
            einsatz = sa.einsatz_von(variante.werkzeug, bibliothek)
            messung = material.messen(
                wirklich,
                vs.form_des_controllers(variante.werkzeug),
                einsatz,
                float(op.Grathoehe) - sa.NC_RESERVE,
                float(op.Aufmass),
            )
            if messung.gruende:
                variante.grund = "; ".join(messung.gruende)
                yield plan, variante
                continue
            variante.material = messung
            variante.rest = messung.rest + messung.unsicherheit
            variante.material_geprueft = True
            ergebnis = kb.kollision_parallel(
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

    rand_versagt = set()
    for werkzeuge, r_liste, a_liste in _runden(
        controller,
        lambda tc: an.radius_von(_Ansicht(op, ToolController=tc)),
        richtungen,
        anstellungen,
        alle,
    ):
        davor = len(plan.varianten)
        for tc in werkzeuge:
            if tc.Name not in rand_versagt:
                yield from werkzeug(tc, r_liste, a_liste)
        yield from zulassen(plan.varianten[davor:])
        if plan.beste is not None:
            break


def bahnfeinheit(op, feinheit=None):
    """Die Grathöhe (mm), für die der Vergleich die Bahn rechnet: `feinheit`, wenn angegeben
    (> 0); sonst die BahnGrathoehe der Operation (> 0); sonst VORGABE_FEINHEIT der verlangten
    Grathöhe. Nie mehr als die verlangte Grathöhe."""
    grathoehe = float(op.Grathoehe)
    wert = float(feinheit or 0.0)
    if wert <= 0:
        wert = float(getattr(op, "BahnGrathoehe", 0.0) or 0.0)
    if wert <= 0:
        # Vorgabe ein Viertel, nicht die geeichten 75 % (bahn_grathoehe): Die Eichung galt der
        # ebenen Fläche; die Kuppel nimmt 75 % an, die Freiform mit ihrer gewölbten Erhebung
        # erst 25 bis 40 % (P-2026-10-09-14: Rest 0,026 mm bei 0,015). Bis der Vergleich von
        # selbst verfeinert, bleibt die sichere Vorgabe.
        wert = grathoehe * VORGABE_FEINHEIT
    return min(wert, grathoehe)


def uebernehmen(op, plan):
    """Die gewinnende Einstellung speichern; keine unvollständig geprüfte Bahn übernehmen."""
    beste = plan.beste if plan is not None else None
    if (
        beste is None
        or beste.grund
        or not beste.kollision_geprueft
        or not beste.material_geprueft
        or not plan.vollstaendig
    ):
        raise ValueError(tr("s5p.fehler.keine"))
    if plan.quelle != op or plan.zustand != _zustand(op):
        raise ValueError(tr("s5p.fehler.veraltet"))
    from . import werkzeuge as wz

    if plan.sicherheitszustand != _sicherheitszustand(plan.pruefung, wz.Bibliothek.laden()):
        raise ValueError(tr("s5p.fehler.veraltet"))
    doc = op.Document
    doc.openTransaction(
        tr("s5f.uebernehmen") if plan.schruppen is not None else tr("s5p.uebernehmen")
    )
    try:
        if plan.schruppen is not None:
            plan.schruppen.Zwischenlagen = beste.zwischenlagen
            plan.schruppen.Rampenanlauf = True
            plan.schruppen.touch()
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
        op.BahnGrathoehe = beste.bahngrathoehe
        op.touch()
        doc.recompute()
        if plan.schruppen is not None:
            wirklich = [c.toGCode() for c in plan.schruppen.Path.Commands]
            erwartet = [c.toGCode() for c in beste.schruppoperation.Path.Commands]
            if wirklich != erwartet:
                raise ValueError(tr("s5p.fehler.bahnveraendert"))
        if not op.Path.Commands or not op.Werkzeugachsen:
            raise ValueError(tr("s5p.fehler.leer"))
        radius = an.radius_von(op)
        aktuell = an.punkte(list(op.Path.Commands), [tuple(a) for a in op.Werkzeugachsen], radius)
        erwartet = an.punkte(
            list(beste.operation.Path.Commands),
            [tuple(a) for a in beste.operation.Werkzeugachsen],
            radius,
        )
        if len(aktuell) != len(erwartet) or any(
            a.eilgang != b.eilgang
            or abs(a.vorschub - b.vorschub) > 1e-6
            or max(
                abs(x - y)
                for x, y in zip((*a.spitze, *a.achse), (*b.spitze, *b.achse), strict=True)
            )
            > 1e-6
            for a, b in zip(aktuell, erwartet, strict=False)
        ):
            raise ValueError(tr("s5p.fehler.bahnveraendert"))
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
