# SPDX-License-Identifier: LGPL-2.1-or-later
"""Den vorhandenen Rohteil-/Sollteil-Vergleich auch für geprüfte Simultankugeln nutzen.

Die Darstellung bleibt ein Höhenquader. Unterstützt ist derselbe von oben
erreichbare Fall wie beim Simultanvergleich, mit senkrechter Vorbearbeitung.
Die Kugelmitte folgt jedoch der tatsächlichen Maschinenkinematik. Das Bild
ersetzt weder die feinere Qualitätsprüfung noch die Kollisionsprüfung.
"""

import numpy as np

from . import restmaterial as rm
from . import simultan_abtrag as sa


class SimultanRestbild(rm.QuaderAbtrag):
    """Ein Abtrag für den vorhandenen Abspieler, einschließlich Rückwärtsfahren."""

    vorschau_simultan = True

    def bis_station(self, index):
        """Die kontinuierlichen Kugel-/Schaftstrecken bis zur gewünschten Station abtragen."""
        index = min(max(0, index), self.letzte())
        if index + 1 < self.bis:
            self.quader.zuruecksetzen()
            self.bis = 0
        for k in range(max(1, self.bis), index + 1):
            if not (
                self.gueltig[k - 1]
                and self.gueltig[k]
                and self.operation[k - 1] == self.operation[k]
            ):
                continue
            form = self.fraeser[int(self.operation[k])]
            self._strecke(self.punkte[k - 1], self.punkte[k], form)
        self.bis = max(self.bis, index + 1)

    def _strecke(self, a, b, form):
        q = self.quader
        hier = sa._ausschnitt(q, a, b, form.radius)
        xs, ys = np.meshgrid(q.x[hier[0]], q.y[hier[1]], indexing="ij")
        if form.nur_kugel:
            unten = sa.kugelschnitt(
                xs, ys, a + (0, 0, form.radius), b + (0, 0, form.radius), form.radius
            )
        else:
            unten = sa.schaftschnitt(xs, ys, a, b, form.radius)
        np.minimum(q.h[hier], np.maximum(q.z_von, unten), out=q.h[hier])


def fuer(abfahrt, job, spitzen):
    """Materialbild für geprüftes Kugelschlichten; None bei ungeeigneter Bearbeitung."""
    from . import reichweite as rw
    from . import schlichten3d as s3
    from . import schwenken as sw
    from . import vierachs_flaechen as vf
    from . import vierachs_schlichten as vs
    from .kinematik import Kinematik

    if sw.ist_ebene(job) or not abfahrt.stationen:
        return None
    operationen = list(job.Operations.Group)
    if not any(
        o.Active and s3.ist_schlichten3d(o) and float(getattr(o, "BahnGrathoehe", 0)) > 0
        for o in operationen
    ):
        return None
    stock = getattr(getattr(job, "Stock", None), "Shape", None)
    if stock is None or stock.isNull():
        return None
    box = stock.BoundBox
    if abs(stock.Volume - box.XLength * box.YLength * box.ZLength) > 1e-5:
        return None
    formen = [o.Shape for o in job.Model.Group if hasattr(o, "Shape") and not o.Shape.isNull()]
    if len(formen) != 1:
        return None
    original = {o.Label: o for o in operationen}
    fraeser, laenger = {}, {}
    gewaehlt = []
    for i, op in enumerate(abfahrt.operationen):
        if op.tc is None:
            continue
        form = vs.form_des_controllers(op.tc)
        quelle = original.get(op.name)
        if quelle is None or form is None or not (form.nur_kugel or form.eben):
            return None
        if not form.nur_kugel and (getattr(quelle, "Anstellen", False) or op.ebene):
            return None
        fraeser[i] = form
        laenger[i] = Kinematik(
            abfahrt.pruefung, op.aufnahme, rw.Einspannung(op.laenge + 1, op.lage), abfahrt.nullpunkt
        )
        gewaehlt.append(list(getattr(quelle, "Flaechen", ())))
    if not fraeser:
        return None
    punkte = np.asarray(spitzen, dtype=float).copy()
    gueltig = np.zeros(len(abfahrt.stationen), dtype=bool)
    nummern = np.array([s.operation for s in abfahrt.stationen], dtype=int)
    for k, s in enumerate(abfahrt.stationen):
        form = fraeser.get(s.operation)
        if form is None or s.stellungen is None:
            continue
        p = punkte[k].copy()
        q = np.asarray(laenger[s.operation].am_werkstueck(abfahrt.stellungen_an(k)))
        richtung = p - q
        if not form.nur_kugel:
            # Schwenken über dem Rohteil schneidet nichts; dort darf die Richtung wechseln.
            # Einen schrägen Schaft im Material kann der Höhenquader nicht darstellen.
            im_material = (
                p[2] < box.ZMax + form.radius
                and box.XMin - form.radius <= p[0] <= box.XMax + form.radius
                and box.YMin - form.radius <= p[1] <= box.YMax + form.radius
            )
            if im_material and np.linalg.norm(richtung - (0, 0, 1)) > 1e-6:
                return None
        else:
            punkte[k] = p + form.radius * richtung - (0, 0, form.radius)
        gueltig[k] = True
    flaechen = set().union(*(vf.nummern(n) for n in gewaehlt)) if all(gewaehlt) else None
    aufmass = next(
        (float(o.Aufmass) for o in reversed(operationen) if o.Active and hasattr(o, "Aufmass")), 0.0
    )
    quader = rm.Quader(box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax)
    return SimultanRestbild(quader, punkte, nummern, gueltig, fraeser, aufmass, formen, flaechen)
