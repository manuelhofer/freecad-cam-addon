# SPDX-License-Identifier: LGPL-2.1-or-later
"""Räumlicher Materialstand als getrennte Abschnitte auf senkrechten CAD-Strahlen.

Ein Strahl darf Material unter und über einem Hohlraum tragen. Seine ursprünglichen
Abschnitte stammen aus BRep-Schnitten, nicht aus einer Oberflächenvernetzung. Kugeln
und endliche Schaftfräser mit fester Richtung schneiden über die ganze Gerade.
Das XY-Raster bleibt eine Näherung; es ersetzt keine BRep-/NC-Qualitätsprüfung.
"""

import hashlib
import math
from collections import OrderedDict

import numpy as np
import Part
from FreeCAD import Vector

from .sprache import tr

MAX_STRAHLEN = 1000000
MAX_GRENZEN = 8000000
BLOCK = 2048
GENAU = 1e-9
_GEMERKT = OrderedDict()


def _vektor(wert):
    v = np.asarray(tuple(wert), dtype=float)
    if v.shape != (3,) or not np.isfinite(v).all():
        raise ValueError(tr("rm3.fehler.geometrie"))
    return v


class Material:
    """Mehrere Z-Intervalle je Strahl; NaN markiert freie Speicherplätze."""

    def __init__(self, form, schritt=0.5, fortschritt=None):
        box = form.BoundBox
        if (
            not math.isfinite(schritt)
            or schritt <= 0
            or form.isNull()
            or not form.Solids
            or min(box.XLength, box.YLength, box.ZLength) <= 0
        ):
            raise ValueError(tr("rm3.fehler.geometrie"))
        nx, ny = math.ceil(box.XLength / schritt), math.ceil(box.YLength / schritt)
        if nx * ny > MAX_STRAHLEN:
            raise ValueError(tr("rm3.fehler.raster"))
        self.dx, self.dy = box.XLength / nx, box.YLength / ny
        self.x = box.XMin + (np.arange(nx) + 0.5) * self.dx
        self.y = box.YMin + (np.arange(ny) + 0.5) * self.dy
        self.z_von, self.z_bis = box.ZMin, box.ZMax
        self.schritt = max(self.dx, self.dy)
        self.ausgelassen = ()  # Unveränderliche Angaben; auch Materialkopien teilen keine Liste.
        self.bewegungsfehler = 0.0  # Einseitige zusätzliche Schranke des Simultansweeps.
        self.grenzen = np.full((nx, ny, 1, 2), np.nan)
        for start in range(0, nx * ny, BLOCK):
            if fortschritt is not None and not fortschritt(start / (nx * ny)):
                raise ValueError(tr("s5p.fehler.unvollstaendig"))
            ids = np.arange(start, min(nx * ny, start + BLOCK))
            linien = Part.makeCompound(
                [
                    Part.makeLine(
                        Vector(self.x[i // ny], self.y[i % ny], box.ZMin - 1),
                        Vector(self.x[i // ny], self.y[i % ny], box.ZMax + 1),
                    )
                    for i in ids
                ]
            )
            for kante in form.common(linien).Edges:
                bb = kante.BoundBox
                if bb.XLength > GENAU or bb.YLength > GENAU:
                    raise ValueError(tr("rm3.fehler.geometrie"))
                i = int(round((bb.XMin - self.x[0]) / self.dx))
                j = int(round((bb.YMin - self.y[0]) / self.dy))
                if bb.ZLength > GENAU:
                    self._eintragen(i, j, bb.ZMin, bb.ZMax)

    def _platz(self, anzahl):
        if anzahl <= self.grenzen.shape[2]:
            return
        neu = max(anzahl, 2 * self.grenzen.shape[2])
        nx, ny = len(self.x), len(self.y)
        if nx * ny * neu * 2 > MAX_GRENZEN:
            raise ValueError(tr("rm3.fehler.raster"))
        g = np.full((nx, ny, neu, 2), np.nan)
        g[:, :, : self.grenzen.shape[2]] = self.grenzen
        self.grenzen = g

    def _eintragen(self, i, j, unten, oben):
        g = self.grenzen[i, j]
        paare = sorted([tuple(v) for v in g if np.isfinite(v[0])] + [(unten, oben)])
        vereint = []
        for a, b in paare:
            if vereint and a <= vereint[-1][1] + GENAU:
                vereint[-1][1] = max(b, vereint[-1][1])
            else:
                vereint.append([a, b])
        self._platz(len(vereint))
        self.grenzen[i, j] = np.nan
        self.grenzen[i, j, : len(vereint)] = vereint

    def kopie(self):
        """Unabhängiger Materialzweig; Koordinaten werden unverändert geteilt."""
        neu = object.__new__(Material)
        neu.__dict__ = self.__dict__.copy()
        neu.grenzen = self.grenzen.copy()
        return neu

    @property
    def volumen(self):
        """Materialvolumen der Strahlabschnitte mit ihren tatsächlichen XY-Zellflächen."""
        return float(np.nansum(self.grenzen[..., 1] - self.grenzen[..., 0])) * self.dx * self.dy

    def belegt(self, punkte):
        """Material an Punkten (n, 3); vier Nachbarstrahlen gemeinsam für die Vorschau."""
        p = np.asarray(punkte, dtype=float)
        if p.ndim != 2 or p.shape[1] != 3 or not np.isfinite(p).all():
            raise ValueError(tr("rm3.fehler.geometrie"))
        i = np.floor((p[:, 0] - self.x[0]) / self.dx).astype(int)
        j = np.floor((p[:, 1] - self.y[0]) / self.dy).astype(int)
        treffer = np.zeros(len(p), dtype=bool)
        for di, dj in ((0, 0), (0, 1), (1, 0), (1, 1)):
            ix, iy = i + di, j + dj
            drin = (ix >= 0) & (ix < len(self.x)) & (iy >= 0) & (iy < len(self.y))
            g = self.grenzen[ix[drin], iy[drin]]
            z = p[drin, 2, None]
            treffer[drin] |= np.any((z >= g[..., 0] - GENAU) & (z <= g[..., 1] + GENAU), axis=1)
        return treffer

    def _fenster(self, unten, oben):
        ix = np.searchsorted(self.x, [unten[0], oben[0]], side="left")
        iy = np.searchsorted(self.y, [unten[1], oben[1]], side="left")
        return slice(ix[0], min(len(self.x), ix[1] + 1)), slice(iy[0], min(len(self.y), iy[1] + 1))

    def _abtragen(self, fenster, unten, oben):
        g = self.grenzen[fenster]
        a, b = g[..., 0], g[..., 1]
        schnitt_unten, schnitt_oben = unten[..., None], oben[..., None]
        abtrag = np.maximum(0, np.minimum(b, schnitt_oben) - np.maximum(a, schnitt_unten))
        volumen = float(np.nansum(abtrag)) * self.dx * self.dy
        # Nicht getroffene und völlig freie Strahlen unverändert lassen. Zwei
        # Stücke entstehen nur, wenn der Schnitt wirklich innerhalb des Materials liegt.
        trifft = (
            (schnitt_oben > a + GENAU)
            & (schnitt_unten < b - GENAU)
            & (schnitt_oben > schnitt_unten)
        )
        links = np.stack([a, np.where(trifft, np.minimum(b, schnitt_unten), b)], axis=-1)
        rechts = np.stack([np.maximum(a, schnitt_oben), b], axis=-1)
        links[links[..., 1] <= links[..., 0] + GENAU] = np.nan
        rechts[~trifft | (rechts[..., 1] <= rechts[..., 0] + GENAU)] = np.nan
        beide = np.concatenate([links, rechts], axis=2)
        reihenfolge = np.argsort(np.nan_to_num(beide[..., 0], nan=np.inf), axis=2)
        beide = np.take_along_axis(beide, reihenfolge[..., None], axis=2)
        anzahl = max(1, int(np.max(np.sum(np.isfinite(beide[..., 0]), axis=2), initial=0)))
        self._platz(anzahl)
        self.grenzen[fenster] = np.nan
        self.grenzen[fenster][:, :, :anzahl] = beide[:, :, :anzahl]
        return volumen

    def kugel(self, von, nach, radius):
        """Eine Kugel mit MITTE von/nach schneidet ihre ganze Gerade, in jeder Richtung."""
        from .simultan_abtrag import kugelschnitt

        a, b = _vektor(von), _vektor(nach)
        if not math.isfinite(radius) or radius <= 0:
            raise ValueError(tr("rm3.fehler.geometrie"))
        f = self._fenster(np.minimum(a, b) - radius, np.maximum(a, b) + radius)
        x, y = np.meshgrid(self.x[f[0]], self.y[f[1]], indexing="ij")
        unten = kugelschnitt(x, y, a, b, radius)
        oben = -kugelschnitt(x, y, a * (1, 1, -1), b * (1, 1, -1), radius)
        return self._abtragen(f, unten, oben)

    def schaft(self, von, nach, achse, radius, laenge):
        """Endlicher Schaftfräser mit fester Achse von Spitze zum Schaft, kontinuierlich."""
        a, b, u = _vektor(von), _vektor(nach), _vektor(achse)
        if (
            not math.isfinite(radius)
            or not math.isfinite(laenge)
            or min(radius, laenge, np.linalg.norm(u)) <= 0
        ):
            raise ValueError(tr("rm3.fehler.geometrie"))
        u = u / np.linalg.norm(u)
        ecken = np.array([a, b, a + laenge * u, b + laenge * u])
        f = self._fenster(ecken.min(axis=0) - radius, ecken.max(axis=0) + radius)
        x, y = np.meshgrid(self.x[f[0]], self.y[f[1]], indexing="ij")
        unten, oben = schaftschnitt(x, y, a, b, u, radius, laenge)
        return self._abtragen(f, unten, oben)


def _nullstellen(a, b, c):
    """Beide Grenzen a*z²+b*z+c <= 0; lineare und konstante Fälle eingeschlossen."""
    a, b, c = np.broadcast_arrays(a, b, c)
    d = b * b - 4 * a * c
    quadratisch = a > 1e-14
    wurzel = np.sqrt(np.maximum(0, d))
    mit = np.where(quadratisch, 2 * a, 1)
    lo, hi = (-b - wurzel) / mit, (-b + wurzel) / mit
    linear = ~quadratisch & (np.abs(b) > 1e-14)
    z = -c / np.where(linear, b, 1)
    lo = np.where(linear, np.where(b < 0, z, -np.inf), lo)
    hi = np.where(linear, np.where(b > 0, z, np.inf), hi)
    konstant = ~quadratisch & ~linear
    lo = np.where(konstant & (c <= GENAU), -np.inf, lo)
    hi = np.where(konstant & (c <= GENAU), np.inf, hi)
    fehlt = (quadratisch & (d < -GENAU)) | (konstant & (c > GENAU))
    return np.where(fehlt, np.inf, lo), np.where(fehlt, -np.inf, hi)


def schaftschnitt(xs, ys, von, nach, achse, radius, laenge):
    """Z-Intervall eines Strahls im Sweep eines beliebig gerichteten endlichen Zylinders.

    Die zulässigen (z,t) erfüllen einen quadratischen Radialabstand, t in [0,1]
    und eine lineare axiale Grenze. Z-Extrema liegen bei t=0/1, an einer Stirn
    oder am radialen Rand mit verschwindender Ableitung nach t. Alle werden geprüft.
    """
    a, b, u = _vektor(von), _vektor(nach), _vektor(achse)
    if not np.isfinite([radius, laenge]).all() or min(radius, laenge, np.linalg.norm(u)) <= 0:
        raise ValueError(tr("rm3.fehler.geometrie"))
    u = u / np.linalg.norm(u)
    xs, ys = np.broadcast_arrays(np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))
    d = b - a
    w = np.stack(np.broadcast_arrays(xs - a[0], ys - a[1], np.full_like(xs, -a[2])), axis=-1)
    e = np.array([0.0, 0.0, 1.0])
    h0, hd, hz = w @ u, float(d @ u), float(u[2])
    v, dz, vz = w - h0[..., None] * u, d - hd * u, e - hz * u
    unten, oben = np.full(xs.shape, np.inf), np.full(xs.shape, -np.inf)

    def nimm(z, t):
        endlich = np.isfinite(z) & np.isfinite(t)
        z, t = np.where(endlich, z, 0), np.where(endlich, t, 0)
        h = h0 + hz * z - hd * t
        radial = v + z[..., None] * vz - t[..., None] * dz
        gut = (
            endlich
            & (t >= -GENAU)
            & (t <= 1 + GENAU)
            & (h >= -GENAU)
            & (h <= laenge + GENAU)
            & (np.sum(radial * radial, axis=-1) <= radius**2 + GENAU)
        )
        np.minimum(unten, np.where(gut, z, np.inf), out=unten)
        np.maximum(oben, np.where(gut, z, -np.inf), out=oben)

    # Rand der Zeit und gegebenenfalls Schnitte durch die Stirnflächen.
    for t in (0.0, 1.0):
        r = v - t * dz
        lo, hi = _nullstellen(float(vz @ vz), 2 * (r @ vz), np.sum(r * r, axis=-1) - radius**2)
        if abs(hz) > 1e-14:
            stirnen = ((-h0 + hd * t) / hz, (laenge - h0 + hd * t) / hz)
            lo = np.maximum(lo, np.minimum(*stirnen))
            hi = np.minimum(hi, np.maximum(*stirnen))
        nimm(lo, np.full(xs.shape, t))
        nimm(hi, np.full(xs.shape, t))
    for h in (0.0, laenge):
        if abs(hz) > 1e-14:
            z0, zt = (h - h0) / hz, hd / hz
            r, s = v + z0[..., None] * vz, zt * vz - dz
            lo, hi = _nullstellen(float(s @ s), 2 * (r @ s), np.sum(r * r, axis=-1) - radius**2)
            for t in (np.maximum(0, lo), np.minimum(1, hi)):
                z = z0 + np.where(np.isfinite(t), t, 0) * zt
                nimm(np.where(np.isfinite(t), z, np.inf), t)
        elif abs(hd) > 1e-14:
            t = (h0 - h) / hd
            r = v - t[..., None] * dz
            lo, hi = _nullstellen(float(vz @ vz), 2 * (r @ vz), np.sum(r * r, axis=-1) - radius**2)
            nimm(lo, t)
            nimm(hi, t)
    dd = float(dz @ dz)
    if dd > 1e-14:
        t0, tz = (v @ dz) / dd, float(vz @ dz) / dd
        r, s = v - t0[..., None] * dz, vz - tz * dz
        lo, hi = _nullstellen(float(s @ s), 2 * (r @ s), np.sum(r * r, axis=-1) - radius**2)
        nimm(lo, t0 + np.where(np.isfinite(lo), lo, 0) * tz)
        nimm(hi, t0 + np.where(np.isfinite(hi), hi, 0) * tz)
    return unten, oben


def _jobs_vor(job):
    from . import schwenken as sw

    grund = job.Grundjob
    ebenen = sw.ebenen_von(grund)
    if job not in ebenen:
        raise ValueError(tr("rm3.fehler.geometrie"))
    return [grund, *ebenen[: ebenen.index(job)]]


def _simultane_vorbereiten(job):
    """Wirkliche NC und Kinematik der Simultanvorgänger, einmal pro Materialanfrage."""
    from . import maschinenzugang as mz
    from . import materialstand as ms
    from . import simultan_operation as so
    from . import simultan_planung as sp
    from . import werkzeuge as wz

    result = {}
    bib = None
    for davor in _jobs_vor(job):
        for op in ms.operationen_vor(davor):
            if not so.ist_simultan(op):
                continue
            m = mz._maschine(davor, op)
            key = (davor.Name, op.Name)
            if m is None or m is False:
                result[key] = m
                continue
            if bib is None:
                bib = wz.Bibliothek.laden()
            try:
                programm = so.programm(op, m)
            except ValueError:
                result[key] = False
                continue
            result[key] = (m, programm, bib, sp._sicherheitszustand(m.pruefung, bib))
    return result


def kennung(job, schritt=0.5, simultane=None):
    """Rohteil, Richtungen, Werkzeugkörper und vollständige aktive Vorgängerpfade."""
    from . import maschinenzugang as mz
    from . import materialstand as ms
    from . import schwenken as sw

    if simultane is None:
        simultane = _simultane_vorbereiten(job)
    daten = [job.Grundjob.Stock.Shape.exportBrepToString(), schritt]
    for davor in _jobs_vor(job):
        lage = sw.ebene_von(davor)
        daten.append(tuple(lage.toMatrix().A) if lage is not None else None)
        for op in ms.operationen_vor(davor):
            tc = op.ToolController
            daten.append(
                (
                    op.Name,
                    ms._kennung_op(op),
                    str(getattr(tc.Tool, "CuttingEdgeHeight", "")),
                    tuple(tuple(a) for a in getattr(op, "Werkzeugachsen", ())),
                    bool(getattr(op, "Anstellen", False)),
                    bool(getattr(op, "Wegkippen", False)),
                    mz.operation_erreichbar(davor, op),
                )
            )
            vorbereitet = simultane.get((davor.Name, op.Name))
            if vorbereitet is not None and vorbereitet is not False:
                m, programm, _bib, sicherheit = vorbereitet
                daten.append(
                    (
                        tuple(c.toGCode() for c in programm.befehle),
                        programm.materialdaten,
                        tuple(m.nullpunkt),
                        repr(m.laenge),
                        sicherheit,
                    )
                )
    return hashlib.sha256(repr(daten).encode()).hexdigest()


def fuer_ebene(job, schritt=0.5, fortschritt=None):
    """Gemeinsamer Rest vor einer 3+2-Ebene; None bei nicht sicher nachlesbarer Bearbeitung.

    Die Ausgabe ist nur zum Lesen. Ein unbekannter Schnitt darf niemals freie Räume
    vortäuschen. Daher bleiben solche Ebenen beim vollständigen ursprünglichen Rohteil.
    """
    from . import maschinenzugang as mz
    from . import materialstand as ms
    from . import reichweite as rw
    from . import schwenken as sw
    from . import simultan_operation as so
    from . import vierachs_schlichten as vs

    simultane = _simultane_vorbereiten(job)
    key = kennung(job, schritt, simultane)
    if key in _GEMERKT:
        _GEMERKT.move_to_end(key)
        return _GEMERKT[key]
    material = Material(job.Grundjob.Stock.Shape, schritt, fortschritt)
    for davor in _jobs_vor(job):
        lage = sw.ebene_von(davor)
        achse = np.array(tuple(lage.Rotation.multVec(Vector(0, 0, 1)))) if lage else (0, 0, 1)

        def ort(p, lage=lage):
            return np.array(tuple(lage.multVec(Vector(*p)))) if lage else np.asarray(p)

        for op in ms.operationen_vor(davor):
            if mz.operation_erreichbar(davor, op) is False:
                material.ausgelassen += ((op.Label, davor.Label),)
                continue  # Nicht gefahrener Schnitt darf keinen freien Raum vortäuschen.
            if so.ist_simultan(op):
                vorbereitet = simultane.get((davor.Name, op.Name))
                if vorbereitet is None:
                    return None  # Ohne tatsächliche Kinematik kein räumlich gedachter Schnitt.
                if vorbereitet is False:
                    material.ausgelassen += ((op.Label, davor.Label),)
                    continue
                m, programm, bib, _sicherheit = vorbereitet
                from . import abfahren as ab
                from . import raum_bahn as rb
                from .simultan_bereiche import _Ansicht

                # Ausschließlich diese tatsächliche NC: keine anderen Ebenen oder
                # noch einmal die ungekippte Quellbahn in die Materialfolge einführen.
                view = _Ansicht(
                    op,
                    _pruefprogramm=(so.pruefschluessel(m), programm.befehle),
                    _pruefmaterial=programm.materialdaten,
                )
                j = _Ansicht(davor, Operations=_Ansicht(davor.Operations, Group=[view]))
                fahrt = ab.abfahrt(m.pruefung, j, m.nullpunkt, bib)
                tc = op.ToolController
                form = vs.form_des_controllers(tc)
                laenge = float(getattr(tc.Tool, "CuttingEdgeHeight", 0))
                if form is None or not fahrt.stationen:
                    return None
                try:
                    if not rb.abtragen(
                        material, fahrt, programm.materialdaten, form, laenge, fortschritt
                    ):
                        return None
                except ValueError as fehler:
                    if str(fehler) == tr("s5p.fehler.unvollstaendig"):
                        raise
                    return None  # Unbekannte Geometrie/Budget: keinen halben Rest veröffentlichen.
                material.ausgelassen += tuple(
                    (f"{op.Label} – {n}: {grund}", davor.Label) for n, grund in programm.ausgelassen
                )
                continue
            tc = op.ToolController
            form = vs.form_des_controllers(tc)
            laenge = float(getattr(tc.Tool, "CuttingEdgeHeight", 0))
            if (
                form is None
                or not (form.eben or form.nur_kugel)
                or not math.isfinite(laenge)
                or laenge <= (form.radius if form.nur_kugel else 0)
            ):
                return None
            unbekannt = []
            letzter = None
            for s in rw._bahn(op.Path.Commands, unbekannt.append, rueckzug=True):
                if any(abs(v) > 1e-8 for v in s.rund.values()):
                    return None
                radius = form.radius
                if s.art == "bogen":
                    bogen = s.ort
                    anzahl = max(2, int(math.ceil(abs(bogen.winkel) * bogen.radius / 0.5)))
                    punkte = [bogen.bei(k / anzahl) for k in range(1, anzahl + 1)]
                    # Die kleinere Scheibe ist sicher in der tatsächlichen Bogenfahrt.
                    radius -= bogen.radius * (1 - math.cos(abs(bogen.winkel) / (2 * anzahl)))
                else:
                    punkte = [s.ort]
                for p in punkte:
                    jetzt = ort(p)
                    if letzter is not None:
                        if fortschritt is not None and not fortschritt(0.5):
                            raise ValueError(tr("s5p.fehler.unvollstaendig"))
                        u = np.asarray(achse)
                        if form.nur_kugel:
                            volumen = material.kugel(
                                letzter + form.radius * u, jetzt + form.radius * u, radius
                            )
                            volumen += material.schaft(
                                letzter + form.radius * u,
                                jetzt + form.radius * u,
                                u,
                                radius,
                                laenge - form.radius,
                            )
                        else:
                            volumen = material.schaft(letzter, jetzt, u, radius, laenge)
                        if s.eilgang and volumen > 1e-7:
                            return None
                    letzter = jetzt
            if unbekannt:
                return None
    _GEMERKT[key] = material
    while len(_GEMERKT) > 3:
        _GEMERKT.popitem(last=False)
    return material
