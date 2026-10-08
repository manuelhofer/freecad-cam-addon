# SPDX-License-Identifier: LGPL-2.1-or-later
"""3D-Schnitte entlang der ersten Schnittstrecke anfahren, statt ins Material zu tauchen.

Die Anfahrt folgt derselben geprüften Hüllfläche mit abnehmender Höhe. Wenn die
erste Strecke kurz ist, fährt sie zurück und wieder vor. Am Ende zurück zum
Anfang schlichten, damit auch unter der Rampe das fertige Teil entsteht.
Der unabhängige Materialprüfer kontrolliert danach auch diese Bewegungen.
"""

import math
from dataclasses import replace

import numpy as np

from . import bahn as bn
from . import fraeserform as ff
from . import freiwege as fw
from . import job_schnittwerte as js
from . import materialstand as ms
from . import simultan_abtrag as sa
from . import werkzeuge as wz
from .sprache import tr


def ergaenzen(bahn, job, operation, radius, vorschub, eintauchen):
    """Jeden Schnittbeginn über dem tatsächlichen Materialstand vorbereiten."""
    # Die nächste Ansicht kann bereits selbst im Variantenjob stehen. Erst dann
    # zur Quelle gehen, wenn sie dort fehlt; sonst würden die eigene alte Bahn
    # oder sogar das Schlichten schon als Vorbearbeitung gezählt.
    vor = operation
    while vor is not None and not any(vor is o for o in job.Operations.Group):
        vor = getattr(vor, "_quelle", None)
    if vor is None:
        raise ValueError(tr("s5p.fehler.operation"))
    stand = ms.fuer(job, vor)
    # Eigener Materialstand innerhalb dieser Operation; eine Rückkehr darf nicht wieder
    # mit dem ursprünglichen Rohteil gerechnet werden.
    from . import restmaterial as rm

    box = job.Stock.Shape.BoundBox
    q = rm.Quader(box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax, schritt=0.1)
    if stand is not None:
        q.h[:] = np.maximum(box.ZMin, stand.hoehen_an(q.x, q.y))
    anfang = q.h.copy() if getattr(operation, "Rampenanlauf", False) else None
    stand = ms.Materialstand(q, q.h.copy())
    toolform = ff.kugel(radius)
    werkzeug = js.werkzeug_von(operation.ToolController, wz.Bibliothek.laden())
    winkel = float(werkzeug.eintauchwinkel) if werkzeug is not None else 0.0
    if getattr(operation, "Rampenanlauf", False):
        winkel = min(winkel, float(operation.Eintauchwinkel))
    if winkel <= 0:
        raise ValueError(tr("s5p.fehler.rampenwinkel"))
    if getattr(operation, "Rampenanlauf", False):
        from . import vierachs_schlichten as vs

        toolform = vs.form_des_controllers(operation.ToolController)
    stock_oben = job.Stock.Shape.BoundBox.ZMax
    punkte = []
    for p in bahn.punkte:
        if punkte:
            a = punkte[-1]
            if (
                not p.eilgang
                and not a.eilgang
                and math.hypot(p.x - a.x, p.y - a.y) < 1e-8
                and abs(p.z - a.z) > 1e-6
            ):
                # Gleiche XY-Punkte auf die tiefere Hülllage reduzieren: die vorherige Strecke kommt
                # tangential auf der Fläche an. Die ganze neue Strecke muss danach
                # unabhängig gegen BRep und Material geprüft werden.
                punkte[-1] = p if p.z < a.z else a
                continue
        punkte.append(p)
    if getattr(operation, "Rampenanlauf", False):
        from . import angestellt as an

        punkte = an.gerade(punkte, laenge=0.5)
    ergebnis = []
    i = 0
    while i < len(punkte):
        if punkte[i].eilgang:
            ergebnis.append(punkte[i])
            i += 1
            continue
        ende = i + 1
        while ende < len(punkte) and not punkte[ende].eilgang:
            ende += 1
        zug = punkte[i:ende]
        while len(zug) > 1 and math.hypot(zug[1].x - zug[0].x, zug[1].y - zug[0].y) < 1e-8:
            zug = zug[1:]
        erster = zug[0]
        beginn = len(ergebnis)
        ausschnitt = sa._ausschnitt(
            q, (erster.x, erster.y, erster.z), (erster.x, erster.y, erster.z), radius
        )
        xs, ys = np.meshgrid(q.x[ausschnitt[0]], q.y[ausschnitt[1]], indexing="ij")
        rho2 = (xs - erster.x) ** 2 + (ys - erster.y) ** 2
        drin = rho2 < radius**2 - 1e-10
        profil = radius - np.sqrt(np.maximum(0, radius**2 - rho2)) if toolform.nur_kugel else 0
        fehlt = np.where(drin, q.h[ausschnitt] - erster.z - profil, -np.inf)
        abtrag = float(np.max(fehlt)) if fehlt.size else 0.0
        # Ein bereits geräumter Boden braucht keine zusätzliche 0,1-mm-Rampe mit
        # Rückkehr und erneutem Abfahren desselben Anfangsstücks.
        hoch = max(0.0, abtrag + 0.1) if fehlt.size else 0.0
        if anfang is not None and abtrag <= 1e-7:
            hoch = 0.0
        schon_geschnitten = -1
        if hoch > 0 and len(zug) > 1:
            start = bn.Punkt(
                True,
                erster.x,
                erster.y,
                max(erster.z + hoch + 2.0, ergebnis[-1].z if ergebnis else stock_oben + 3),
            )
            if ergebnis:
                ergebnis[-1] = start
            else:
                ergebnis.append(start)
            ergebnis.append(bn.Punkt(True, erster.x, erster.y, erster.z + hoch + 2.0))
            ergebnis.append(
                bn.Punkt(
                    False,
                    erster.x,
                    erster.y,
                    erster.z + hoch,
                    anteil=max(1.0, fw.freivorschub_fuer(job) / max(vorschub, 1e-9)),
                )
            )
            rampe, schon_geschnitten = _rampe(zug, hoch, winkel, toolform.eben)
            if getattr(operation, "Rampenanlauf", False) and vorschub > 0:
                markiert = []
                a = ergebnis[-1]
                for b in rampe:
                    hier = sa._ausschnitt(q, (a.x, a.y, a.z), (b.x, b.y, b.z), radius + 0.1)
                    material = q.h[hier]
                    frei = not material.size or float(np.max(material)) < min(a.z, b.z) - 0.05
                    markiert.append(
                        replace(b, anteil=max(1, fw.freivorschub_fuer(job) / vorschub))
                        if frei
                        else b
                    )
                    a = b
                rampe = markiert
            ergebnis.extend(rampe)
        if getattr(operation, "Rampenanlauf", False) and vorschub > 0:
            schnell = min(10000.0, fw.freivorschub_fuer(job)) / vorschub
            markiert = [zug[0]]
            for nummer, (a, b) in enumerate(zip(zug, zug[1:], strict=False), start=1):
                hier = sa._ausschnitt(q, (a.x, a.y, a.z), (b.x, b.y, b.z), radius + 0.1)
                material = q.h[hier]
                frei = (
                    nummer <= schon_geschnitten
                    or not material.size
                    or float(np.max(material)) < min(a.z, b.z) - 0.05
                )
                markiert.append(
                    replace(b, anteil=max(1.0, schnell), eintauchen=False) if frei else b
                )
            zug = markiert
        ergebnis.extend(zug)
        # Der folgende Schnittbeginn sieht das, was diese Strecke wirklich weggenommen hat.
        messung = sa.fahren(
            stand.quader,
            ergebnis[max(0, len(ergebnis) - len(zug) - 1) :],
            toolform,
            math.inf,
            math.inf,
        )
        if getattr(operation, "Rampenanlauf", False) and messung.volumen < 1e-9 and len(zug) > 1:
            # Ein kompletter Zug ohne Abtrag ist kein Schlicht-/Schruppschritt.
            # Die Anfahrt über der ganzen Rohteilhöhe bleibt für den folgenden Zug sicher.
            del ergebnis[beginn:]
            if ergebnis:
                a = ergebnis[-1]
                ergebnis[-1] = bn.Punkt(True, a.x, a.y, max(stock_oben + 3, a.z))
        i = ende
    if anfang is not None:
        # Auch mit Rampenanlauf gelten die gemeinsamen freien Verbindungen und der
        # Freivorschub. Dafür vom Material vor der Operation ausgehen, nicht vom
        # bereits vollständig abgefahrenen Quader.
        q.h[:] = anfang
        ergebnis, _schnell = fw.schneller(
            ergebnis, toolform, q, vorschub, fw.freivorschub_fuer(job)
        )
    bahn.punkte = ergebnis
    bahn.laenge = sum(
        bn.weg(a, b) for a, b in zip(ergebnis, ergebnis[1:], strict=False) if not b.eilgang
    )
    bahn.zeit = bn.zeit(ergebnis, vorschub, eintauchen)
    return bahn


def _rampe(zug, hoch, winkel, eben):
    # Bei ebener Stirn gilt der Winkel gegen XY, bei der Kugel relativ zur Hüllfläche.
    laenge = sum(
        math.hypot(b.x - a.x, b.y - a.y) if eben else bn.weg(a, b)
        for a, b in zip(zug, zug[1:], strict=False)
    )
    if laenge < 1e-6:
        return [], -1
    ergebnis = []
    i, richtung, rest = 0, 1, hoch
    while rest > 1e-9:
        j = i + richtung
        if not 0 <= j < len(zug):
            richtung = -richtung
            j = i + richtung
        a, b = zug[i], zug[j]
        weg = math.hypot(b.x - a.x, b.y - a.y) if eben else bn.weg(a, b)
        senken = weg * math.tan(math.radians(winkel)) + (b.z - a.z if eben else 0)
        anteil = min(1.0, rest / senken) if senken > 1e-12 else 1.0
        rest = max(0.0, rest - anteil * senken)
        ergebnis.append(
            bn.Punkt(
                False,
                a.x + anteil * (b.x - a.x),
                a.y + anteil * (b.y - a.y),
                a.z + anteil * (b.z - a.z) + rest,
            )
        )
        if rest <= 1e-9:
            # Auf derselben Hülllinie zum Anfang zurück, diesmal ohne Höhenversatz.
            bis = i if richtung > 0 else j
            ergebnis.extend(bn.Punkt(False, p.x, p.y, p.z) for p in reversed(zug[: bis + 1]))
            break
        i = j
    return ergebnis, bis
