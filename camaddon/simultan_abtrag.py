# SPDX-License-Identifier: LGPL-2.1-or-later
"""Materialprüfung für Kugelschlichten auf von oben erreichbaren Flächen im Quader.

Die Kugelmitte bleibt beim Anstellen erhalten. Ihr Schnitt mit einem senkrechten
Materialstrahl wird über die ganze Strecke gerechnet, nicht nur an Bahnpunkten.
Das ist unabhängig vom Planer und verfolgt das Material nach den vorherigen
Operationen. Das Modellraster hat eine eigene, feinere Vernetzung.

Der Höhenquader kann keine Hinterschnitte oder beliebigen Rohteilformen darstellen;
solche Jobs werden ausdrücklich abgewiesen. Rasterwerte sind keine Zertifizierung
einer beliebigen kontinuierlichen CAD-Fläche. Auflösung und Unsicherheit gehören
deshalb zum Ergebnis; die Grathöhe wird durch diese Unsicherheit nicht vergrößert.
"""

import math
from dataclasses import dataclass, field

import numpy as np
import Part

from . import bahn as bn
from . import hoehenfeld as hf
from . import job_schnittwerte as js
from . import pruefstand as ps
from . import restmaterial as rm
from . import vierachs_flaechen as vf
from . import vierachs_schlichten as vs
from . import werkzeuge as wz
from .sprache import tr

RASTER = 0.1  # mm, zusätzlich im Test mit halbem Raster geprüft
NETZ = 0.001  # mm, unabhängig von der Vernetzung der Bahn
SEHNENFEHLER = 0.001  # mm, nur für konservative Zusammenfassung der Prüfkapseln
NC_RESERVE = 0.00011  # mm: Steuerungsglättung 0,0001 plus Reserve für sechs Ausgabestellen


@dataclass
class Messung:
    """Material- und Lastbefunde eines Laufs; Längen in mm, Volumen in mm³."""

    rest: float = math.inf
    einschnitt: float = 0.0
    eilgang_abtrag: float = 0.0
    schnell_abtrag: float = 0.0
    schnellweg: float = 0.0
    luftweg: float = 0.0
    vorschubweg: float = 0.0
    volumen: float = 0.0
    last_max: float = 0.0  # mm², Volumen pro Weg, über 3 mm gemittelt
    eintauchungen: int = 0
    luftzuege: int = 0
    rampenwinkel_max: float = 0.0
    eintritte: list = field(default_factory=list)
    eilgaenge: list = field(default_factory=list)
    raster: float = RASTER
    unsicherheit: float = NETZ
    flaechenzellen: int = 0
    ungedeckt: int = 0
    gruende: list = field(default_factory=list)

    @property
    def luftanteil(self):
        """Anteil des Vorschubwegs, auf dem kein Material abgetragen wurde."""
        return self.luftweg / max(self.vorschubweg, 1e-12)


def kugelschnitt(xs, ys, von, nach, radius):
    """Unterster Schnitt der gesamten Kugelstrecke mit den Strahlen bei xs/ys.

    Minimiert z(t) − sqrt(R² − |xy(t) − xy(Strahl)|²) analytisch über 0 ≤ t ≤ 1.
    Dadurch bleiben zwischen zwei Bahnpunkten keine künstlichen Lücken.
    """
    a, b = np.asarray(von), np.asarray(nach)
    d = b - a
    dx, dy = xs - a[0], ys - a[1]
    quer2 = float(d[0] ** 2 + d[1] ** 2)
    if quer2 < 1e-20:
        innen = radius**2 - dx**2 - dy**2
        return np.where(innen >= 0, min(a[2], b[2]) - np.sqrt(np.maximum(innen, 0)), np.inf)
    t0 = (dx * d[0] + dy * d[1]) / quer2
    rho2 = np.maximum(0.0, dx**2 + dy**2 - t0**2 * quer2)
    innen = radius**2 - rho2
    t = t0 - d[2] * np.sqrt(np.maximum(innen, 0) / (quer2 * float(d @ d)))
    t = np.clip(t, 0.0, 1.0)
    innen = radius**2 - (dx - t * d[0]) ** 2 - (dy - t * d[1]) ** 2
    return np.where(innen >= 0, a[2] + t * d[2] - np.sqrt(np.maximum(innen, 0)), np.inf)


def _ausschnitt(q, a, b, radius):
    ix = np.searchsorted(q.x, [min(a[0], b[0]) - radius, max(a[0], b[0]) + radius], side="left")
    iy = np.searchsorted(q.y, [min(a[1], b[1]) - radius, max(a[1], b[1]) + radius], side="left")
    return slice(max(0, ix[0]), min(len(q.x), ix[1] + 1)), slice(
        max(0, iy[0]), min(len(q.y), iy[1] + 1)
    )


def schaftschnitt(xs, ys, von, nach, radius):
    """Kontinuierlicher Schnitt der ebenen Stirn eines senkrechten Schaftfräsers."""
    a, b = np.asarray(von), np.asarray(nach)
    d = b - a
    dx, dy = xs - a[0], ys - a[1]
    quer2 = float(d[0] ** 2 + d[1] ** 2)
    if quer2 < 1e-20:
        return np.where(dx**2 + dy**2 < radius**2 - 1e-8, min(a[2], b[2]), np.inf)
    t0 = (dx * d[0] + dy * d[1]) / quer2
    rho2 = np.maximum(0.0, dx**2 + dy**2 - t0**2 * quer2)
    halb = np.sqrt(np.maximum(0, radius**2 - rho2) / quer2)
    t = np.clip(t0 + (halb if d[2] < 0 else -halb), 0, 1)
    naechster = np.clip(t0, 0, 1)
    drin = (dx - naechster * d[0]) ** 2 + (dy - naechster * d[1]) ** 2 < radius**2 - 1e-8
    return np.where(drin, a[2] + t * d[2], np.inf)


def fahren(q, punkte, form, ae, ap, eintauchwinkel=90.0, fortschritt=None):
    """Material sequenziell abtragen und Vorschub, Last und Eilgang unabhängig messen."""
    m = Messung(raster=q._schritt)
    fenster = []
    zug_volumen, zug_schnittweg = 0.0, 0.0
    for i, (a, b) in enumerate(zip(punkte, punkte[1:], strict=False)):
        _meldung(fortschritt, i, len(punkte))
        von, nach = np.array((a.x, a.y, a.z)), np.array((b.x, b.y, b.z))
        ausschnitt = _ausschnitt(q, von, nach, form.radius)
        vorher = q.h[ausschnitt].copy()
        xs, ys = np.meshgrid(q.x[ausschnitt[0]], q.y[ausschnitt[1]], indexing="ij")
        if form.nur_kugel:
            unten = kugelschnitt(
                xs, ys, von + (0, 0, form.radius), nach + (0, 0, form.radius), form.radius
            )
        elif form.eben:
            unten = schaftschnitt(xs, ys, von, nach, form.radius)
        else:
            raise ValueError(tr("s5p.fehler.abtragform"))
        np.minimum(q.h[ausschnitt], np.maximum(q.z_von, unten), out=q.h[ausschnitt])
        gesenkt = vorher - q.h[ausschnitt]
        volumen = float(gesenkt.sum()) * q._schritt**2
        weg = bn.weg(a, b)
        if b.eilgang:
            if zug_schnittweg > 1e-6 and zug_volumen < 1e-9:
                m.luftzuege += 1
            zug_volumen, zug_schnittweg = 0.0, 0.0
            m.eilgang_abtrag += volumen
            if volumen > 1e-7 and len(m.eilgaenge) < 10:
                m.eilgaenge.append((tuple(von), tuple(nach), volumen))
            fenster.clear()
            continue
        zug_volumen += volumen
        if b.anteil <= 1.0 + 1e-8:
            zug_schnittweg += weg
        if b.anteil > 1.0 + 1e-8:
            m.schnell_abtrag += volumen
            if volumen < 1e-9:
                m.schnellweg += weg
                fenster.clear()
                continue
        m.volumen += volumen
        m.vorschubweg += weg
        if volumen < 1e-9:
            m.luftweg += weg
        if math.hypot(b.x - a.x, b.y - a.y) < 1e-7 and b.z < a.z - 1e-6 and volumen > 1e-9:
            m.eintauchungen += 1
            if len(m.eintritte) < 10:
                m.eintritte.append((tuple(von), tuple(nach), volumen))
        if form.eben and volumen > 1e-7 and b.z < a.z - 1e-7:
            winkel = math.degrees(math.atan2(a.z - b.z, math.hypot(b.x - a.x, b.y - a.y)))
            m.rampenwinkel_max = max(m.rampenwinkel_max, winkel)
        if weg > 1e-9:
            fenster.append((weg, volumen))
            laenge = sum(f[0] for f in fenster)
            while len(fenster) > 1 and laenge - fenster[0][0] >= ps.BREIT_FENSTER:
                laenge -= fenster.pop(0)[0]
            if laenge >= ps.BREIT_FENSTER:
                m.last_max = max(m.last_max, sum(f[1] for f in fenster) / laenge)
    if zug_schnittweg > 1e-6 and zug_volumen < 1e-9:
        m.luftzuege += 1
    if m.luftzuege:
        m.gruende.append(tr("s5p.fehler.luftzug"))
    if m.eilgang_abtrag > 1e-7:
        m.gruende.append(tr("s5p.fehler.eilgang", volumen=f"{m.eilgang_abtrag:.3f}"))
    if m.schnell_abtrag > 1e-7:
        m.gruende.append(tr("s5p.fehler.schnell", volumen=f"{m.schnell_abtrag:.3f}"))
    if m.eintauchungen:
        m.gruende.append(tr("s5p.fehler.eintritt"))
    if m.rampenwinkel_max > eintauchwinkel + 1e-6:
        m.gruende.append(
            tr(
                "s5p.fehler.rampe",
                winkel=f"{m.rampenwinkel_max:.3f}",
                grenze=f"{eintauchwinkel:.3f}",
            )
        )
    if m.last_max > ae * ap + 1e-6:
        m.gruende.append(tr("s5p.fehler.last", last=f"{m.last_max:.3f}", grenze=f"{ae * ap:.3f}"))
    if m.luftanteil > ps.LUFT_ZULAESSIG:
        m.gruende.append(tr("s5p.fehler.luft", anteil=f"{m.luftanteil * 100:.1f}"))
    return m


class Pruefstand:
    """Unabhängiger Höhenquader für die Materialfolge vor einer Schlichtoperation."""

    def __init__(self, job, operation, bibliothek, raster=RASTER, fortschritt=None):
        form = vs._teil(job.Model.Group)
        stock = job.Stock.Shape
        box = stock.BoundBox
        if abs(stock.Volume - box.XLength * box.YLength * box.ZLength) > 1e-5:
            raise ValueError(tr("s5p.fehler.abtragform"))
        self.quader = rm.Quader(box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax, raster)
        self.form = form
        self.fortschritt = fortschritt
        # Eine sehr dünne Randzelle kann bei grober Vernetzung eine falsche Normale
        # erhalten. Feinere Vernetzung muss sie auflösen; nie eine Zelle still verwerfen.
        for toleranz in (NETZ, NETZ / 2, NETZ / 4):
            fnetz = vf.vernetze(form, toleranz)
            gewaehlt = np.isin(fnetz.flaeche, vf.nummern(list(operation.Flaechen)))
            self.dreiecke = fnetz.netz.punkte[fnetz.netz.dreiecke[gewaehlt]]
            n = np.cross(
                self.dreiecke[:, 1] - self.dreiecke[:, 0], self.dreiecke[:, 2] - self.dreiecke[:, 0]
            )
            if len(n) and not np.any(np.abs(n[:, 2]) < 0.05 * np.linalg.norm(n, axis=1)):
                break
        else:
            raise ValueError(tr("s5p.fehler.abtragform"))
        self.unsicherheit = toleranz
        self.soll = hf.hoehen(fnetz.netz, self.quader.x, self.quader.y)
        from . import vierachs_huelle as vh

        nur = vh.Netz(fnetz.netz.punkte, fnetz.netz.dreiecke[gewaehlt], toleranz)
        self.nur = hf.hoehen(nur, self.quader.x, self.quader.y) > hf.KEIN_TREFFER / 2
        self.vorher = []
        aktive = [o for o in job.Operations.Group if getattr(o, "Active", True)]
        if not aktive or aktive[-1] != operation:
            raise ValueError(tr("s5p.fehler.letzte"))
        for op in job.Operations.Group:
            if op == operation:
                break
            if not getattr(op, "Active", True):
                continue
            if getattr(op, "Anstellen", False) or getattr(op, "Wegkippen", False):
                raise ValueError(tr("s5p.fehler.abtragform"))
            toolform = vs.form_des_controllers(op.ToolController)
            einsatz = einsatz_von(op.ToolController, bibliothek)
            if toolform is None or einsatz is None:
                raise ValueError(tr("s5p.fehler.einsatz"))
            punkte = _pfad(op)
            w = js.werkzeug_von(op.ToolController, bibliothek)
            messung = fahren(
                self.quader,
                punkte,
                toolform,
                einsatz.ae,
                einsatz.ap,
                eintauchwinkel=w.eintauchwinkel,
                fortschritt=fortschritt,
            )
            self.vorher.append((op.Label, messung))
        self.start = self.quader.h.copy()

    def messen(self, punkte, toolform, einsatz, grathoehe, aufmass=0.0):
        """Vom tatsächlichen Materialstand starten; Rest überall und Einschnitt am Modell."""
        self.quader.h[:] = self.start
        m = fahren(
            self.quader, punkte, toolform, einsatz.ae, einsatz.ap, fortschritt=self.fortschritt
        )
        m.unsicherheit = self.unsicherheit
        rest = self.quader.h - self.soll
        da = self.soll > hf.KEIN_TREFFER / 2
        m.einschnitt = float(np.min(rest[da])) if da.any() else -math.inf
        m.rest = float(np.max(rest[self.nur])) if self.nur.any() else math.inf
        # Vernetzungsunsicherheit verbraucht einen Teil der Vorgabe; sie erhöht sie nicht.
        if m.rest + m.unsicherheit > grathoehe + aufmass:
            m.gruende.append(tr("s5p.fehler.rest", rest=f"{m.rest + m.unsicherheit:.4f}"))
        if m.einschnitt < -self.unsicherheit:
            m.gruende.append(tr("s5p.fehler.einschnitt", tiefe=f"{-m.einschnitt:.4f}"))
        m.flaechenzellen = len(self.dreiecke)
        m.ungedeckt = deckung(
            self.dreiecke,
            punkte,
            toolform.radius,
            grathoehe + aufmass,
            unsicherheit=self.unsicherheit,
            fortschritt=self.fortschritt,
        )
        if m.ungedeckt:
            m.gruende.append(tr("s5p.fehler.deckung", anzahl=m.ungedeckt))
        return m


def _pfad(op):
    """CAM-Pfad als kurze Geraden; die Originaloperation bleibt unverändert."""
    from . import reichweite as rw

    ergebnis = []
    unbekannt = []
    for s in rw._bahn(op.Path.Commands, unbekannt.append, rueckzug=True):
        if any(abs(w) > 1e-8 for w in s.rund.values()):
            raise ValueError(tr("s5p.fehler.abtragform"))
        if s.art == "bogen":
            anzahl = max(2, int(math.ceil(abs(s.ort.winkel) * s.ort.radius / 0.1)))
            orte = [s.ort.bei(k / anzahl) for k in range(1, anzahl + 1)]
        else:
            orte = [s.ort]
        anteil = s.vorschub / max(float(op.ToolController.HorizFeed), 1e-12)
        ergebnis.extend(bn.Punkt(s.eilgang, *p, anteil=anteil) for p in orte)
    if unbekannt:
        raise ValueError(tr("s5p.fehler.abtragform"))
    return ergebnis


def einsatz_von(tc, bibliothek):
    """Die tatsächlichen Einsatzgrenzen aus der Werkzeugverwaltung, keine Ersatzwerte."""
    gemerkt = js.gemerkter_einsatz(tc)
    w = js.werkzeug_von(tc, bibliothek) if bibliothek is not None else None
    if gemerkt is None or w is None:
        return None
    return next(
        (
            e
            for e in w.schnittwerte.get(gemerkt.werkstoff or wz.ALLE, [])
            if e.art == gemerkt.art and e.name == gemerkt.name
        ),
        None,
    )


def einschnitt(form, punkte, radius, grenze=0.00025, fortschritt=None):
    """Kleinster BRep-Abstand der ganzen Kugelstrecken zum gesamten fertigen Teil."""
    kleinster = math.inf
    from FreeCAD import Vector

    def abstand(a, b):
        von, nach = Vector(*a), Vector(*b)
        linie = Part.Vertex(von) if von.distanceToPoint(nach) < 1e-9 else Part.makeLine(von, nach)
        return form.distToShape(linie)[0] - radius

    strecken = _pruefstrecken(punkte, radius, mit_original=True)
    for i, (a, b, original) in enumerate(strecken):
        _meldung(fortschritt, i, len(strecken))
        schranke = abstand(a, b) - SEHNENFEHLER
        if schranke < grenze:
            # Keine Freigabe aus einer ungenauen Schranke: hier alle Originalstrecken exakt.
            schranke = min(abstand(u, v) for u, v in zip(original, original[1:], strict=False))
        kleinster = min(kleinster, schranke)
        if kleinster < grenze:
            break
    return kleinster


def an_mitte(punkt, radius):
    """Kugelmitte einer senkrecht gespeicherten Bahn, unabhängig von der Anstellung."""
    from FreeCAD import Vector

    return Vector(punkt.x, punkt.y, punkt.z + radius)


def deckung(dreiecke, punkte, radius, hoehe, unsicherheit=NETZ, fortschritt=None):
    """Zählt Flächenzellen, deren Toleranzfläche nicht vollständig im Kugelschnitt liegt.

    Jede Zelle wird als GANZES geprüft: ihre drei um die erlaubte Höhe versetzten
    Ecken müssen in derselben Kapsel liegen. Kapseln sind konvex, damit auch alle
    Punkte dazwischen. Die kleinere Prüfkugel reserviert die Vernetzungsunsicherheit.
    Das ist konservativ: Eine Zelle, die mehrere Schnitte gemeinsam abdecken,
    kann durchfallen; eine bloße Probe in der Zellenmitte genügt niemals.
    """
    strecken = _pruefstrecken(punkte, radius)
    if not strecken:
        return len(dreiecke)
    von = np.array([a for a, _b in strecken])
    nach = np.array([b for _a, b in strecken])
    weg = nach - von
    quadrat = np.maximum(np.sum(weg * weg, axis=1), 1e-20)
    breite = max(radius, 1.0)
    index = {}
    for i, (a, b) in enumerate(zip(von, nach, strict=True)):
        unten = np.floor((np.minimum(a[:2], b[:2]) - radius) / breite).astype(int)
        oben = np.floor((np.maximum(a[:2], b[:2]) + radius) / breite).astype(int)
        for x in range(unten[0], oben[0] + 1):
            for y in range(unten[1], oben[1] + 1):
                index.setdefault((x, y), []).append(i)
    ursprung = np.arange(len(dreiecke))
    schlecht = set()
    grenze = max(0, radius - unsicherheit - SEHNENFEHLER) ** 2
    for tiefe in range(7):
        gruppen = {}
        for i, ort in enumerate(np.floor(np.mean(dreiecke[:, :, :2], axis=1) / breite).astype(int)):
            gruppen.setdefault(tuple(ort), []).append(i)
        teilen = []
        for nummer, (ort, zellen) in enumerate(gruppen.items()):
            if fortschritt is not None and not fortschritt(nummer / max(1, len(gruppen))):
                raise ValueError(tr("s5p.fehler.unvollstaendig"))
            saetze = np.asarray(index.get(ort, []), dtype=int)
            if not len(saetze):
                schlecht.update(ursprung[zellen])
                continue
            for start in range(0, len(zellen), 32):
                teil = np.asarray(zellen[start : start + 32])
                ecken = dreiecke[teil] + (0, 0, hoehe)
                delta = ecken[:, None, :, :] - von[None, saetze, None, :]
                t = np.clip(
                    np.sum(delta * weg[None, saetze, None, :], axis=3)
                    / quadrat[None, saetze, None],
                    0,
                    1,
                )
                dist2 = np.sum((delta - t[..., None] * weg[None, saetze, None, :]) ** 2, axis=3)
                offen = np.min(np.max(dist2, axis=2), axis=1) > grenze
                ecke_fehlt = np.max(np.min(dist2, axis=1), axis=1) > grenze
                schlecht.update(ursprung[teil[offen & ecke_fehlt]])
                teilen.extend(teil[offen & ~ecke_fehlt])
        if not teilen:
            break
        teilen = np.asarray([i for i in teilen if ursprung[i] not in schlecht], dtype=int)
        if not len(teilen):
            break
        if tiefe == 6:
            schlecht.update(ursprung[teilen])  # unbewiesen bleibt abgewiesen
            break
        a, b, c = (dreiecke[teilen, i] for i in range(3))
        ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        dreiecke = np.stack(
            [
                np.stack([a, ab, ca], axis=1),
                np.stack([ab, b, bc], axis=1),
                np.stack([ca, bc, c], axis=1),
                np.stack([ab, bc, ca], axis=1),
            ],
            axis=1,
        ).reshape(-1, 3, 3)
        ursprung = np.repeat(ursprung[teilen], 4)
    return len(schlecht)


def _pruefstrecken(punkte, radius, mit_original=False):
    """Kurze Prüfkapseln zusammenfassen; der maximale Fehler verkleinert ihren Radius.

    Jeder Originalabschnitt liegt innerhalb SEHNENFEHLER der Ersatzstrecke. Wegen
    der stetigen Projektion von Anfang bis Ende gilt die Schranke auch zurück zur
    Originalbahn: die verkleinerte Prüfkapsel liegt sicher in deren Kugelsweep.
    Eilgänge und Grenzen zwischen Schnittzügen werden niemals überbrückt.
    """
    zuege, zug = [], []
    for a, b in zip(punkte, punkte[1:], strict=False):
        if b.eilgang:
            if zug:
                zuege.append(np.array(zug))
                zug = []
            continue
        if not zug:
            zug.append(tuple(an_mitte(a, radius)))
        zug.append(tuple(an_mitte(b, radius)))
    if zug:
        zuege.append(np.array(zug))
    strecken = []
    for zug in zuege:
        behalten = {0, len(zug) - 1}
        offen = [(0, len(zug) - 1)]
        while offen:
            i, j = offen.pop()
            if j <= i + 1:
                continue
            d = zug[j] - zug[i]
            delta = zug[i + 1 : j] - zug[i]
            t = np.clip(delta @ d / max(float(d @ d), 1e-20), 0, 1)
            dist2 = np.sum((delta - t[:, None] * d) ** 2, axis=1)
            k = int(np.argmax(dist2))
            if dist2[k] > SEHNENFEHLER**2:
                k += i + 1
                behalten.add(k)
                offen.extend([(i, k), (k, j)])
        indizes = sorted(behalten)
        for i, j in zip(indizes, indizes[1:], strict=False):
            strecken.append((zug[i], zug[j], zug[i : j + 1]) if mit_original else (zug[i], zug[j]))
    return strecken


def maschinenbahn(fahrt, operation, radius, mit_achsen=False, fortschritt=None, materialdaten=None):
    """Kugelmitten aus wirklichen Achsstellungen, mit Zwischenstellungen jedes NC-Satzes.

    Auch Schwenken, An-/Abfahren und Werkzeugwechsel gehören zur Prüfung. Die
    Werkzeugrichtung kommt aus derselben Vorwärtskinematik wie die Simulation.
    """
    from . import reichweite as rw
    from .kinematik import Kinematik

    op = fahrt.operationen[operation]
    kin = fahrt.kinematik(operation)
    laenger = Kinematik(
        fahrt.pruefung, op.aufnahme, rw.Einspannung(op.laenge + 1, op.lage), fahrt.nullpunkt
    )

    def kugel(stellungen, eilgang, anteil):
        p = np.asarray(kin.am_werkstueck(stellungen))
        q = np.asarray(laenger.am_werkstueck(stellungen))
        mitte = p - radius * (q - p)
        achsen.append(tuple(p - q))
        return bn.Punkt(eilgang, mitte[0], mitte[1], mitte[2] - radius, anteil=anteil)

    punkte = []
    achsen = []
    letzte = None
    for i, station in enumerate(fahrt.stationen):
        _meldung(fortschritt, i, len(fahrt.stationen))
        if station.operation != operation:
            continue
        eilgang, anteil = station.eilgang, 1.0
        if materialdaten is not None and station.satz:
            if station.satz > len(materialdaten):
                raise ValueError(tr("s5p.fehler.unvollstaendig"))
            urspruenglich_eil, feed = materialdaten[station.satz - 1]
            eilgang = eilgang or urspruenglich_eil
            anteil = feed / max(float(op.tc.HorizFeed), 1e-12)
        stellungen = fahrt.stellungen_an(i)
        if letzte is not None:
            mitte = {a: (letzte[a] + stellungen[a]) / 2 for a in stellungen}
            punkte.append(kugel(mitte, eilgang, anteil))
        punkte.append(kugel(stellungen, eilgang, anteil))
        letzte = stellungen
    return (punkte, achsen) if mit_achsen else punkte


def _meldung(fortschritt, i, anzahl):
    if fortschritt is not None and i % 256 == 0 and not fortschritt(i / max(1, anzahl)):
        raise ValueError(tr("s5p.fehler.unvollstaendig"))
