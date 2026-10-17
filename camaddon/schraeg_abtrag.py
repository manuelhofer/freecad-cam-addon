# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Abtrag im Quader beim Abfahren, auch mit schräg stehendem Werkzeug – Flanke, 3+2, 5 Achsen
simultan (legros im Forum, 2026-10-10: ein Kegel mit „Flanke“ auf der Beispielmaschine 5-Achs
Tisch/Tisch, das Rohteil blieb im Abspieler ganz; Manuel, 2026-10-11: „dann muss man das ändern“).

Wie restmaterial.QuaderAbtrag ein Höhenfeld über (x, y) des Jobs: je Zelle, bis wohin das Material
von oben weg ist. Steht das Werkzeug zwischen zwei Stationen senkrecht, trägt es mit seiner Form ab
wie dort (Quader.fahre_stuecke); steht es schräg, mit seinem Körper über die Länge der Schneide –
ein Zylinder, beim Kugelfräser eine Kapsel (Halbkugel unten) –, je Zelle der tiefste Punkt, den es
dort erreicht (`tiefste`). Andere Formen (Torus, Fase, Bohrer) zählen schräg als Zylinder mit ihrem
Radius. Zwischen zwei Stationen fährt es so fein, dass weder die Spitze noch das Ende der Schneide
mehr als restmaterial.TEILSCHRITT springen.

Ein Höhenfeld kennt keine Hinterschnitte: Es zeigt, was von oben zu sehen ist. Kommt das Werkzeug
im Material flacher als FLACHSTE_ACHSE von der Seite oder von unten, baut fuer() keinen Abtrag (der
Abspieler zeigt das Rohteil dann wie bisher). Das Bild ersetzt nicht die Kollisionsprüfung: Was der
Schaft oder der Halter trifft, meldet „Kollision prüfen“.

Läuft ohne Oberfläche.
"""

import math

import numpy as np

from . import restmaterial as rm

FLACHSTE_ACHSE = 0.2  # z-Anteil der Werkzeugachse (zur Spindel), flacher im Material: kein Bild
SENKRECHT = 1e-9  # so wenig darf die Achse von +z abweichen, um senkrecht zu zählen
SCHNEIDE_ERSATZ = 3.0  # ohne Schneidenlänge am Werkzeug: so viele Durchmesser
VERTEILT_AB_STATIONEN = 300  # schräge Stationen sind teuer: ab so vielen die Nebenrechner
STATIONEN_JE_SCHRITT = 500  # Stationen zwischen zwei yield in bis_station_schritte()


def tiefste(xs, ys, spitze, achse, radius, laenge, kugel=False):
    """Je Zelle (xs, ys, gleich geformt) der tiefste Punkt (z) des Werkzeugs mit der Spitze
    `spitze` und der Achse `achse` (Einheitsvektor von der Spitze zur Spindel, z > 0) – inf, wo es
    die Zelle nicht trifft. `laenge`: die Schneide; `kugel`: unten eine Halbkugel mit `radius`."""
    if kugel:
        mitte = np.asarray(spitze, dtype=float) + radius * np.asarray(achse, dtype=float)
        r2 = (xs - mitte[0]) ** 2 + (ys - mitte[1]) ** 2
        unten = np.where(
            r2 <= radius * radius,
            mitte[2] - np.sqrt(np.maximum(radius * radius - r2, 0.0)),
            np.inf,
        )
        schaft = _zylinder(xs, ys, mitte, achse, radius, max(laenge - radius, 0.0))
        return np.minimum(unten, schaft)
    return _zylinder(xs, ys, spitze, achse, radius, laenge)


def _zylinder(xs, ys, fuss, achse, radius, laenge):
    """tiefste() für einen Zylinder vom Mittelpunkt seiner Grundfläche `fuss` die Achse entlang:
    Je Zelle ist die Senkrechte (x, y, z) im Zylinder, wo ihr Abstand zur Achse höchstens der
    Radius ist (eine quadratische Ungleichung in z) und ihr Stück auf der Achse zwischen 0 und
    `laenge` liegt (linear in z)."""
    dx, dy, dz = (float(v) for v in achse)
    wx, wy = xs - fuss[0], ys - fuss[1]
    s0 = wx * dx + wy * dy  # das Stück auf der Achse auf Höhe des Fußes
    von = -s0 / dz  # z − Fuß, ab dem die Senkrechte über der Grundfläche liegt …
    bis = (laenge - s0) / dz  # … und bis zu dem unter der Deckfläche
    quer = wx * wx + wy * wy - s0 * s0 - radius * radius
    a = 1.0 - dz * dz
    if a < 1e-12:  # senkrecht: in der Zelle die ganze Grundfläche
        return np.where(quer <= 0.0, fuss[2] + von, np.inf)
    b = -2.0 * dz * s0
    diskriminante = b * b - 4.0 * a * quer
    wurzel = np.sqrt(np.maximum(diskriminante, 0.0))
    unten = np.maximum((-b - wurzel) / (2.0 * a), von)
    oben = np.minimum((-b + wurzel) / (2.0 * a), bis)
    return np.where((diskriminante >= 0.0) & (unten <= oben), fuss[2] + unten, np.inf)


class SchraegAbtrag(rm.QuaderAbtrag):
    """QuaderAbtrag mit der Achse des Werkzeugs je Station (`achsen`, Einheitsvektoren zur
    Spindel) und je Operation dem Werkzeug: `fraeser` wie dort (Form oder Radius, für senkrechte
    Stücke), `koerper` (Radius, Schneidenlänge, Kugel?) für schräge."""

    def __init__(
        self, quader, punkte, achsen, operation, gueltig, fraeser, koerper, aufmass, formen
    ):
        super().__init__(quader, punkte, operation, gueltig, fraeser, aufmass, formen)
        self.achsen = np.asarray(achsen, dtype=float).reshape(-1, 3)
        self.koerper = koerper

    def bis_station(self, index):
        """Trägt ab bis einschließlich Station `index`; zurück rechnet es von vorn."""
        for _ in self.bis_station_schritte(index):
            pass

    def bis_station_schritte(self, index, je=STATIONEN_JE_SCHRITT):
        """bis_station() als Generator (der Abspieler rechnet im Takt): nach je `je` Stationen
        ein `yield`. Viele Stationen auf einmal (ab VERTEILT_AB_STATIONEN) rechnen die
        Nebenrechner in Stücken (stueck, restmaterial.verteilt_abtragen) – am Schwenkteil stand
        der Sprung im Abspieler sonst 0,8 s auf einem Kern (Manuel, 2026-10-17: „immer daran
        denken, dass alle Rechenkerne auch genutzt werden“)."""
        index = min(max(0, index), self.letzte())
        if index + 1 < self.bis:
            self.quader.zuruecksetzen()
            self.bis = 0
        start = max(self.bis, 1)
        if index + 1 - start >= VERTEILT_AB_STATIONEN and rm.verteilt_abtragen(
            self.quader, start, index, "schraeg_abtrag", "stueck",
            self.punkte, self.achsen, self.operation, self.gueltig, self.fraeser, self.koerper,
        ):  # fmt: skip
            self.bis = index + 1
            return
        while start <= index:
            ende = min(index + 1, start + je)
            _abtragen(
                self.quader, self.punkte, self.achsen, self.operation, self.gueltig,
                self.fraeser, self.koerper, np.arange(start, ende),
            )  # fmt: skip
            self.bis = max(self.bis, ende)
            start = ende
            yield
        self.bis = max(self.bis, index + 1)


def stueck(gitter, punkte, achsen, operation, gueltig, fraeser, koerper):
    """Auch im Nebenrechner: die Stationen 1 … n − 1 (`punkte` (n, 3), die erste nur als Anfang)
    auf einem leeren Quader mit dem Raster `gitter` (restmaterial.Quader.gitter()) – gibt sein
    Höhenfeld zurück (restmaterial.verteilt_abtragen)."""
    q = rm.Quader(*gitter)
    punkte = np.asarray(punkte, dtype=float).reshape(-1, 3)
    achsen = np.asarray(achsen, dtype=float).reshape(-1, 3)
    _abtragen(
        q, punkte, achsen, np.asarray(operation), np.asarray(gueltig, dtype=bool), fraeser,
        koerper, np.arange(1, len(punkte)),
    )  # fmt: skip
    return q.h


def _abtragen(quader, punkte, achsen, operation, gueltig, fraeser, koerper, k):
    """Die Stationen `k` (je von k − 1 nach k) auf `quader`: senkrechte Stücke mit der Form des
    Fräsers (Quader.fahre_stuecke), schräge mit seinem Körper (_schraeg)."""
    k = k[gueltig[k - 1] & gueltig[k] & (operation[k - 1] == operation[k])]
    senkrecht = (achsen[k - 1, 2] >= 1.0 - SENKRECHT) & (achsen[k, 2] >= 1.0 - SENKRECHT)
    for nummer, form in fraeser.items():
        stuecke = k[senkrecht & (operation[k] == nummer)]
        if len(stuecke):
            quader.fahre_stuecke(punkte[stuecke - 1], punkte[stuecke], form)
    for i in k[~senkrecht]:
        _schraeg(quader, punkte, achsen, i, koerper[int(operation[i])])


def _schraeg(q, punkte, achsen, i, koerper):
    """Das Stück von Station i − 1 nach i mit schräger Achse, in Teilschritten."""
    radius, laenge, kugel = koerper
    a, b = punkte[i - 1], punkte[i]
    da, db = achsen[i - 1], achsen[i]
    winkel = math.acos(float(np.clip(np.dot(da, db), -1.0, 1.0)))
    schritte = max(1, math.ceil(max(np.linalg.norm(b - a), laenge * winkel) / rm.TEILSCHRITT))
    for t in np.arange(1, schritte + 1) / schritte:
        spitze = a + t * (b - a)
        achse = da + t * (db - da)
        achse = achse / np.linalg.norm(achse)
        ende = spitze + laenge * achse
        x_von, x_bis = min(spitze[0], ende[0]) - radius, max(spitze[0], ende[0]) + radius
        y_von, y_bis = min(spitze[1], ende[1]) - radius, max(spitze[1], ende[1]) + radius
        ix = slice(np.searchsorted(q.x, x_von), np.searchsorted(q.x, x_bis, "right"))
        iy = slice(np.searchsorted(q.y, y_von), np.searchsorted(q.y, y_bis, "right"))
        if ix.start >= ix.stop or iy.start >= iy.stop:
            continue
        xs, ys = np.meshgrid(q.x[ix], q.y[iy], indexing="ij")
        unten = tiefste(xs, ys, spitze, achse, radius, laenge, kugel)
        np.minimum(q.h[ix, iy], np.maximum(q.z_von, unten), out=q.h[ix, iy])


def koerper_von(tc):
    """(Radius, Schneidenlänge, Kugel?) des Werkzeugs am Controller – für schräge Stücke."""
    from .vierachs_schlichten import form_des_controllers

    form = form_des_controllers(tc)
    durchmesser = float(tc.Tool.Diameter.getValueAs("mm"))
    radius = form.radius if form is not None else durchmesser / 2
    laenge = 0.0
    hoehe = getattr(tc.Tool, "CuttingEdgeHeight", None)
    if hoehe is not None:
        laenge = float(hoehe.getValueAs("mm") if hasattr(hoehe, "getValueAs") else hoehe)
    if laenge <= 0.0:
        laenge = SCHNEIDE_ERSATZ * 2 * radius
    return radius, laenge, bool(form is not None and form.nur_kugel)


def fuer(abfahrt, job, spitzen):
    """Der Abtrag für den Job, wenn sein Rohteil (im Grundjob) ein Kasten ist und jedes Werkzeug
    im Material von oben kommt – senkrecht oder schräg; sonst None. `spitzen`: je Station die
    Spitze am Werkstück (abfahren.Abfahrt.am_werkstueck)."""
    from . import reichweite as rw
    from .kinematik import Kinematik

    grund = rw.grundjob_von(job)
    rohteil = getattr(grund, "Stock", None)
    form = getattr(rohteil, "Shape", None)
    if form is None or form.isNull() or hasattr(rohteil, "Radius"):
        return None
    box = form.BoundBox
    volumen = box.XLength * box.YLength * box.ZLength
    if volumen <= 0 or abs(form.Volume - volumen) > 1e-6 * volumen:
        return None
    if not abfahrt.stationen or not abfahrt.operationen:
        return None
    formen = [
        o.Shape
        for o in getattr(grund.Model, "Group", [])
        if getattr(o, "Shape", None) is not None and not o.Shape.isNull()
    ]
    if not formen:
        return None
    fraeser, koerper, laenger = {}, {}, {}
    for k, op in enumerate(abfahrt.operationen):
        if op.tc is None or getattr(op.tc, "Tool", None) is None:
            continue
        fraeser[k] = rm._fraeser(op.tc)
        koerper[k] = koerper_von(op.tc)
        laenger[k] = Kinematik(
            abfahrt.pruefung,
            op.aufnahme,
            rw.Einspannung(op.laenge + 1.0, op.lage),
            abfahrt.nullpunkt,
        )
    if not fraeser:
        return None
    punkte = np.asarray(spitzen, dtype=float).reshape(-1, 3)
    achsen = np.zeros_like(punkte)
    achsen[:, 2] = 1.0
    gueltig = np.zeros(len(abfahrt.stationen), dtype=bool)
    operation = np.array([s.operation for s in abfahrt.stationen], dtype=int)
    gemerkt = {}  # (Operation, Rundachsen) → Achse: In einer Ebene (3+2) bleibt sie gleich
    schraeg = False
    for i, s in enumerate(abfahrt.stationen):
        if s.operation not in fraeser or s.stellungen is None:
            continue
        schluessel = (s.operation, tuple(sorted((b, round(w, 9)) for b, w in s.rund.items())))
        achse = gemerkt.get(schluessel)
        if achse is None:
            laenger_hier = np.asarray(laenger[s.operation].am_werkstueck(abfahrt.stellungen_an(i)))
            achse = punkte[i] - laenger_hier
            achse = achse / np.linalg.norm(achse)
            gemerkt[schluessel] = achse
        im_material = (
            punkte[i][2] < box.ZMax
            and box.XMin - 1.0 <= punkte[i][0] <= box.XMax + 1.0
            and box.YMin - 1.0 <= punkte[i][1] <= box.YMax + 1.0
        )
        if im_material and achse[2] < FLACHSTE_ACHSE:
            return None  # von der Seite oder von unten: das zeigt kein Höhenfeld
        schraeg = schraeg or achse[2] < 1.0 - SENKRECHT
        achsen[i] = achse
        gueltig[i] = True
    if not schraeg:
        return None  # alles senkrecht: das kann restmaterial.fuer_quader genauer
    aufmass = next(
        (
            float(o.Aufmass)
            for o in reversed(list(getattr(job.Operations, "Group", [])))
            if getattr(o, "Active", True) and hasattr(o, "Aufmass")
        ),
        0.0,
    )
    quader = rm.Quader(box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax)
    return SchraegAbtrag(
        quader, punkte, achsen, operation, gueltig, fraeser, koerper, aufmass, formen
    )
