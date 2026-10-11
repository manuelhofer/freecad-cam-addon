# SPDX-License-Identifier: LGPL-2.1-or-later
"""Was in einer Aufspannung erreichbar ist – und aus welcher Richtung (Frage 14; Manuel,
2026-10-11: „ich gebe eine Fläche an, die in dem Spannmittel ist .. und dann wird bearbeitet …
Flächen anklicken im zweiten Auswahlfenster, welche man bearbeitet haben will“).

Jede Fläche des Teils außer der im Spannmittel bekommt eine Richtung der Werkzeugachse (von der
Spitze weg, in Koordinaten des Jobs):

- eine ebene Fläche ihre Normale (die Stirn fräst sie) – oder eine gewählte Richtung, längs der
  sie steht (der Mantel fräst sie: senkrechte Wände von oben, ohne Schwenk);
- eine Zylinder- oder Kegelfläche (Bohrung, Ecke einer Tasche, Zapfen) ihre Achse;
- jede andere (Freiform) eine Richtung, gegen die keine ihrer Normalen zeigt (kein Hinterschnitt).

Nie ins Spannmittel: Keine Richtung zeigt zu ihm hin. Jede Fläche braucht freie Sicht längs der
Achse – Strahlen von Punkten der Fläche gegen das vernetzte Teil, alle zugleich mit numpy. Gewählt
wird oben zuerst (kein Schwenk), dann die Richtung, die die meisten übrigen Flächen nimmt, bei
Gleichstand die weniger geneigte. Eine Wand, die der Mantel fräst, geht danach zu der Richtung, in
der eine Nachbarfläche mit der Stirn gefräst wird (der Boden ihrer Tasche), wenn die sie auch
fräst – die Tasche in der Schräge bleibt beisammen. Mit einer Maschine (schwenken.Maschine) bleiben nur Richtungen,
in die sie mit ihren Anschlägen schwenkt; die Stellung der Rundachsen steht dabei, wie die
Steuerung sie zeigt.

Nicht geprüft: ob ein Fräser in eine Tasche passt und lang genug ist – das entscheiden die
Strategien in der Ebene wie heute. Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field

import numpy as np
from FreeCAD import Vector

from . import formteile as ft
from .sprache import tr

GENAU = 1e-6  # so nah an 0 gilt ein Skalarprodukt als 0 (senkrecht)
GLEICH = 1e-4  # so nah gelten zwei Einheitsvektoren als dieselbe Richtung
SICHT = 1000.0  # mm – so weit muss längs der Achse nichts im Weg sein
ABSTAND = 0.2  # mm – so weit über der Fläche beginnt ein Strahl (Vernetzung 0,05)
VERNETZUNG = 0.05  # mm
PROBEN = (0.2, 0.5, 0.8)  # je Parameterrichtung, im Inneren der Fläche

EBENE, ACHSE, FREI = "ebene", "achse", "frei"


@dataclass
class Richtung:
    """Eine Richtung der Werkzeugachse und die Flächen, die aus ihr gefräst werden."""

    achse: tuple  # (x, y, z), Einheitsvektor, von der Spitze weg
    flaechen: list = field(default_factory=list)  # ["Face4", …]
    stellung: dict = None  # Rundachsen an der Steuerung ({"A": −30.0, …}); None ohne Maschine
    stirn: str = (
        None  # die erste ebene Fläche, deren Normale die Richtung ist („Face3“), sonst None
    )

    @property
    def neigung(self):
        """Grad gegen „oben“ (+Z des Jobs)."""
        return math.degrees(math.acos(max(-1.0, min(1.0, self.achse[2]))))


@dataclass
class Zugang:
    """Das Ergebnis: die Richtungen in der Reihenfolge der Wahl, was nicht geht (Name → Grund)
    und die Fläche im Spannmittel."""

    richtungen: list
    unerreichbar: dict
    spannflaeche: str = None

    def richtung_von(self, name):
        """Die Richtung, aus der die Fläche `name` gefräst wird, oder None."""
        return next((r for r in self.richtungen if name in r.flaechen), None)


@dataclass
class _Flaeche:
    nummer: int
    name: str
    art: str
    achse: Vector  # Normale (EBENE) bzw. Achse (ACHSE); None bei FREI
    punkte: np.ndarray  # (n, 3) Proben auf der Fläche
    normalen: np.ndarray  # (n, 3) die Normalen dort, nach außen


def _gleich(a, b):
    return (a - b).Length < GLEICH


def _flaeche(nummer, f):
    """Art, Achse und Proben einer Fläche."""
    name = f"Face{nummer + 1}"
    typ = f.Surface.__class__.__name__
    u0, u1, v0, v1 = f.ParameterRange
    punkte, normalen = [], []
    for su in PROBEN:
        for sv in PROBEN:
            u, v = u0 + su * (u1 - u0), v0 + sv * (v1 - v0)
            p = f.valueAt(u, v)
            if not f.isInside(p, 1e-4, True):
                continue
            n = f.normalAt(u, v)
            punkte.append(tuple(p))
            normalen.append(tuple(n))
    if not punkte:  # schmale Fläche: wenigstens ihre Mitte
        p = f.CenterOfMass
        u, v = f.Surface.parameter(p)
        punkte.append(tuple(f.valueAt(u, v)))
        normalen.append(tuple(f.normalAt(u, v)))
    if typ == "Plane":
        n = Vector(*normalen[0])
        n.normalize()
        return _Flaeche(nummer, name, EBENE, n, np.array(punkte), np.array(normalen))
    if typ in ("Cylinder", "Cone"):
        a = Vector(f.Surface.Axis)
        a.normalize()
        return _Flaeche(nummer, name, ACHSE, a, np.array(punkte), np.array(normalen))
    return _Flaeche(nummer, name, FREI, None, np.array(punkte), np.array(normalen))


def _nachbarn(form):
    """{Nummer einer Fläche: {Nummer eines Nachbarn: eine gemeinsame Kante}}."""
    an_kante = {}
    for n in range(ft.anzahl(form)):
        for kante in ft.flaeche(form, n).Edges:
            an_kante.setdefault(kante.hashCode(), (kante, set()))[1].add(n)
    nachbarn = {}
    for kante, flaechen in an_kante.values():
        for n in flaechen:
            for m in flaechen - {n}:
                nachbarn.setdefault(n, {})[m] = kante
    return nachbarn


def _innen(form, wand, nachbar, kante):
    """Bilden die Wand (_Flaeche) und ihr Nachbar an der Kante eine Innenkante (wie Wand und Boden
    einer Tasche) oder gehen glatt ineinander über (die Ecke einer Tasche)? An einer Außenkante
    liegt der Nachbar hinter der Wand."""
    p = kante.valueAt((kante.FirstParameter + kante.LastParameter) / 2)
    flaeche = ft.flaeche(form, nachbar.nummer)
    hin = flaeche.CenterOfMass - p
    if hin.Length < 1e-9:
        return True
    hin.normalize()
    q = flaeche.valueAt(*flaeche.Surface.parameter(p + hin * 0.5))
    u, v = ft.flaeche(form, wand.nummer).Surface.parameter(p)
    n = ft.flaeche(form, wand.nummer).normalAt(u, v)
    return (q - p).dot(n) >= -1e-6


def _stirn(fl, k):
    """Fräst die Richtung `k` die Fläche mit der Stirn bzw. längs ihrer Achse (nicht mit dem
    Mantel einer Wand)?"""
    if fl.art == EBENE:
        return _gleich(fl.achse, k)
    if fl.art == ACHSE:
        return fl.achse.cross(k).Length < GLEICH
    return False


class _Strahlen:
    """Das vernetzte Teil, gegen das Strahlen laufen (Möller-Trumbore, alle zugleich)."""

    def __init__(self, form):
        punkte, dreiecke = form.tessellate(VERNETZUNG)
        p = np.array([tuple(q) for q in punkte], dtype=float)
        d = np.array(dreiecke, dtype=int).reshape(-1, 3)
        self.a = p[d[:, 0]]
        self.e1 = p[d[:, 1]] - self.a
        self.e2 = p[d[:, 2]] - self.a

    def frei(self, starts, richtung, laenge=SICHT):
        """Je Strahl von `starts` (n, 3) längs `richtung`: trifft er nichts bis `laenge`?"""
        d = np.asarray(richtung, dtype=float)
        h = np.cross(d, self.e2)  # (T, 3)
        det = np.einsum("tj,tj->t", self.e1, h)
        brauchbar = np.abs(det) > 1e-12
        e1, e2, a, h, det = (x[brauchbar] for x in (self.e1, self.e2, self.a, h, det))
        inv = 1.0 / det
        ergebnis = np.ones(len(starts), dtype=bool)
        for i, s in enumerate(np.asarray(starts, dtype=float)):
            sv = s - a
            u = np.einsum("tj,tj->t", sv, h) * inv
            q = np.cross(sv, e1)
            v = (q @ d) * inv
            t = np.einsum("tj,tj->t", e2, q) * inv
            treffer = (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-9) & (t < laenge)
            ergebnis[i] = not treffer.any()
        return ergebnis


def _deckt(fl, k, strahlen, merken):
    """Fräst die Richtung `k` die Fläche: Stirn, Mantel längs k, Bohrung – mit freier Sicht?"""
    schluessel = (fl.name, round(k.x, 6), round(k.y, 6), round(k.z, 6))
    if schluessel in merken:
        return merken[schluessel]
    kv = np.array(tuple(k))
    if fl.art == EBENE:
        passt = _gleich(fl.achse, k) or abs(fl.achse.dot(k)) < GENAU
    elif fl.art == ACHSE:
        passt = fl.achse.cross(k).Length < GLEICH
    else:  # Freiform: keine Normale gegen die Richtung
        passt = bool(np.all(fl.normalen @ kv >= -GENAU))
    if passt:
        starts = fl.punkte + ABSTAND * fl.normalen + ABSTAND * kv
        passt = bool(strahlen.frei(starts, kv).all())
    merken[schluessel] = passt
    return passt


def zugang(form, unten=(0.0, 0.0, -1.0), spannflaeche=None, maschine=None):
    """Zugang (siehe oben) für die Form in Koordinaten des Jobs: `unten` zeigt ins Spannmittel
    (nach dem „Unten im Spannmittel“ des Assistenten −Z), `spannflaeche` („Face6“) liegt dort und
    wird nicht gefräst; `maschine` (schwenken.Maschine) streicht, wohin sie nicht schwenkt."""
    u = Vector(*unten)
    u.normalize()
    oben = -u
    from . import stl_teil

    daten = stl_teil.daten(form)
    if daten is not None:  # ein Körper aus einem STL: je Richtung ein Höhenfeld, nicht je Fläche
        return _zugang_stl(daten, u, spannflaeche, maschine)
    flaechen = []
    for n in range(ft.anzahl(form)):
        if f"Face{n + 1}" != spannflaeche:
            flaechen.append(_flaeche(n, ft.flaeche(form, n)))
    strahlen = _Strahlen(form)
    # Kandidaten: oben, jede Normale und jede Achse, die nicht ins Spannmittel zeigt.
    kandidaten = [oben]
    for fl in flaechen:
        if fl.achse is None:
            continue
        for k in (fl.achse, -fl.achse) if fl.art == ACHSE else (fl.achse,):
            if k.dot(u) <= GENAU and not any(_gleich(k, c) for c in kandidaten):
                kandidaten.append(Vector(k))
    stellungen = {}
    if maschine is not None:
        stellungen = {id(k): _stellung(maschine, k) for k in kandidaten}
    erlaubt = [k for k in kandidaten if maschine is None or stellungen[id(k)] is not None]
    merken = {}
    offen = {fl.name: fl for fl in flaechen}
    richtungen = []
    rest = list(erlaubt)
    while offen and rest:

        def wert(k):
            n = sum(1 for fl in offen.values() if _deckt(fl, k, strahlen, merken))
            return (n, k.dot(oben))

        k = rest[0] if not richtungen and rest[0] is oben else max(rest, key=wert)
        gedeckt = [fl.name for fl in offen.values() if _deckt(fl, k, strahlen, merken)]
        rest.remove(k)
        if not gedeckt:
            if richtungen or k is not oben:
                break
            continue  # oben deckt nichts – weiter mit den anderen
        richtungen.append(
            Richtung(
                achse=(k.x, k.y, k.z),
                flaechen=sorted(gedeckt, key=lambda s: int(s[4:])),
                stellung=stellungen.get(id(k)),
            )
        )
        for name in gedeckt:
            del offen[name]
    nachbarn = _nachbarn(form)
    _waende_zu_ihrer_tasche(form, nachbarn, flaechen, richtungen, strahlen, merken)
    unerreichbar = {}
    for name, fl in offen.items():
        if any(_deckt(fl, k, strahlen, merken) for k in kandidaten if k not in erlaubt):
            unerreichbar[name] = tr("zg.grund.maschine")
        elif fl.achse is not None and fl.art == EBENE and fl.achse.dot(u) > GENAU:
            unerreichbar[name] = tr("zg.grund.spannmittel")
        else:
            unerreichbar[name] = tr("zg.grund.sicht")
    _waende_mit_ihrer_tasche_weg(form, nachbarn, flaechen, richtungen, unerreichbar)
    for r in richtungen:
        k = Vector(*r.achse)
        r.stirn = next(
            (
                f.name
                for f in flaechen
                if f.name in r.flaechen and f.art == EBENE and _gleich(f.achse, k)
            ),
            None,
        )
    return Zugang(richtungen, unerreichbar, spannflaeche)


STL_RASTER = 0.25  # mm – so fein das Höhenfeld je Richtung (_zugang_stl)
STL_TOLERANZ = 0.05  # mm – so weit darf ein Dreieck unter dem Höhenfeld liegen und gilt als gesehen
STL_NEIGUNGEN = (45.0, 90.0)  # Grad – geschwenkt an einer Maschine, die schwenkt, je vier Seiten


def _zugang_stl(daten, u, spannflaeche, maschine):
    """zugang() für einen Körper aus einem STL (stl_teil.Dreiecksdaten): Jedes Dreieck ist eine
    Fläche. Richtungen: oben, und an einer Maschine (die schwenkt) dazu je STL_NEIGUNGEN zu den
    vier Seiten. Aus einer Richtung k gesehen ist ein Dreieck, das zu ihr schaut und dessen
    Schwerpunkt längs k nicht unter dem niedrigsten der vier Rasterpunkte um ihn liegt – das
    Höhenfeld des ganzen Netzes längs k (hoehenfeld.hoehen); liegt ein Überhang darüber, sind
    alle vier höher. Gewählt wie sonst: oben zuerst, dann die Richtung, die die meisten übrigen
    nimmt. Die Dreiecke, die ins Spannmittel schauen, fräst keine (die Standfläche)."""
    from . import hoehenfeld as hf
    from . import vierachs_huelle as vh

    oben = -u
    kandidaten = [oben]
    e1, e2 = _quer_zu(oben)
    for neigung in STL_NEIGUNGEN:
        s, c = math.sin(math.radians(neigung)), math.cos(math.radians(neigung))
        for seite in (e1, -e1, e2, -e2):
            k = oben * c + seite * s
            k.normalize()
            if k.dot(u) <= GENAU:
                kandidaten.append(k)
    stellungen = {}
    if maschine is not None:
        stellungen = {id(k): _stellung(maschine, k) for k in kandidaten}
        kandidaten = [k for k in kandidaten if stellungen[id(k)] is not None or k is oben]
    ins_spannmittel = daten.normale @ np.array(tuple(u)) >= 1.0 - GLEICH
    offen = ~ins_spannmittel
    sichtbar = {}
    for k in kandidaten:
        sichtbar[id(k)] = _sichtbar_stl(daten, k, hf, vh) & offen
    richtungen = []
    rest = list(kandidaten)
    while offen.any() and rest:
        k = (
            rest[0]
            if not richtungen and rest[0] is oben
            else max(rest, key=lambda k_: (int((sichtbar[id(k_)] & offen).sum()), k_.dot(oben)))
        )
        rest.remove(k)
        gedeckt = np.flatnonzero(sichtbar[id(k)] & offen)
        if not len(gedeckt):
            if richtungen or k is not oben:
                break
            continue
        richtungen.append(
            Richtung(
                achse=(k.x, k.y, k.z),
                flaechen=[f"Face{n + 1}" for n in gedeckt],
                stellung=stellungen.get(id(k)),
            )
        )
        offen[gedeckt] = False
    grund = tr("zg.grund.sicht")
    unerreichbar = {f"Face{n + 1}": grund for n in np.flatnonzero(offen)}
    grund = tr("zg.grund.spannmittel")
    for n in np.flatnonzero(ins_spannmittel):
        if f"Face{n + 1}" != spannflaeche:
            unerreichbar[f"Face{n + 1}"] = grund
    return Zugang(richtungen, unerreichbar, spannflaeche)


def _quer_zu(achse):
    """Zwei Einheitsvektoren quer zu `achse` (und zueinander) – möglichst die x- und y-Achse."""
    for hilfe in (Vector(1, 0, 0), Vector(0, 1, 0)):
        e1 = hilfe - achse * hilfe.dot(achse)
        if e1.Length > 0.5:
            e1.normalize()
            e2 = achse.cross(e1)
            e2.normalize()
            return e1, e2
    return Vector(1, 0, 0), Vector(0, 1, 0)


def _sichtbar_stl(daten, k, hf, vh):
    """Maske je Fläche (Dreieck): aus der Richtung k zu sehen (_zugang_stl)."""
    kv = np.array(tuple(k), dtype=float)
    e1, e2 = _quer_zu(k)
    drehung = np.array([tuple(e1), tuple(e2), tuple(k)], dtype=float)  # Zeilen: neue Achsen
    p = daten.punkte @ drehung.T
    zeigt = daten.normale @ kv > 1e-3
    lo, hi = p[:, :2].min(axis=0), p[:, :2].max(axis=0)
    xs = np.arange(lo[0] - STL_RASTER, hi[0] + 2 * STL_RASTER, STL_RASTER)
    ys = np.arange(lo[1] - STL_RASTER, hi[1] + 2 * STL_RASTER, STL_RASTER)
    hoehe = hf.hoehen(vh.Netz(p, daten.dreiecke, 0.0), xs, ys)
    # Je Fläche ihr Schwerpunkt (die Dreiecke in der Reihenfolge der Flächen).
    mitte = p[daten.dreiecke[daten.dreieck]].mean(axis=1)
    i = np.clip(np.searchsorted(xs, mitte[:, 0]) - 1, 0, len(xs) - 2)
    j = np.clip(np.searchsorted(ys, mitte[:, 1]) - 1, 0, len(ys) - 2)
    um = np.minimum(
        np.minimum(hoehe[i, j], hoehe[i + 1, j]), np.minimum(hoehe[i, j + 1], hoehe[i + 1, j + 1])
    )
    return zeigt & (mitte[:, 2] >= um - STL_TOLERANZ)


def _waende_mit_ihrer_tasche_weg(form, nachbarn, flaechen, richtungen, unerreichbar):
    """Eine Wand, die der Mantel fräst, deren Boden (Nachbar an einer Innenkante) aber nicht
    erreichbar ist und deren Richtung keinen Boden mit der Stirn fräst, gehört zu dieser Tasche:
    unerreichbar wie er (an der 3-Achs-Fräse die Seitenwände der Tasche in der Schräge)."""
    nach_nummer = {fl.nummer: fl for fl in flaechen}
    for r in richtungen:
        k = Vector(*r.achse)
        for name in list(r.flaechen):
            fl = next(f for f in flaechen if f.name == name)
            if _stirn(fl, k):
                continue
            innen = [
                nach_nummer[n]
                for n, kante in nachbarn.get(fl.nummer, {}).items()
                if n in nach_nummer and _innen(form, fl, nach_nummer[n], kante)
            ]
            weg = [nb for nb in innen if nb.name in unerreichbar]
            if not weg or any(nb.name in r.flaechen and _stirn(nb, k) for nb in innen):
                continue
            r.flaechen.remove(name)
            unerreichbar[name] = unerreichbar[weg[0].name]
    richtungen[:] = [r for r in richtungen if r.flaechen]


def _waende_zu_ihrer_tasche(form, nachbarn, flaechen, richtungen, strahlen, merken):
    """Eine Wand, die der Mantel fräst, in die Richtung, in der ein Nachbar mit der Stirn gefräst
    wird und die sie auch fräst – unter mehreren die am wenigsten geneigte."""
    nach_nummer = {fl.nummer: fl for fl in flaechen}
    richtung_von = {name: r for r in richtungen for name in r.flaechen}
    for fl in flaechen:
        r = richtung_von.get(fl.name)
        if r is None or _stirn(fl, Vector(*r.achse)):
            continue
        innen = [
            nach_nummer[n]
            for n, kante in nachbarn.get(fl.nummer, {}).items()
            if n in nach_nummer and _innen(form, fl, nach_nummer[n], kante)
        ]
        moegliche = []
        for nachbar in innen:
            r_n = richtung_von.get(nachbar.name)
            if r_n is None or r_n is r:
                continue
            k = Vector(*r_n.achse)
            if _stirn(nachbar, k) and _deckt(fl, k, strahlen, merken):
                moegliche.append(r_n)
        if not moegliche or any(
            richtung_von.get(nachbar.name) is r and _stirn(nachbar, Vector(*r.achse))
            for nachbar in innen
        ):
            continue  # kein Boden woanders – oder einer schon aus ihrer Richtung
        ziel = max(moegliche, key=lambda x: x.achse[2])
        r.flaechen.remove(fl.name)
        ziel.flaechen.append(fl.name)
        ziel.flaechen.sort(key=lambda s: int(s[4:]))
        richtung_von[fl.name] = ziel
    richtungen[:] = [r for r in richtungen if r.flaechen]


def ohne_schwenken(zugang_, oben=(0.0, 0.0, 1.0)):
    """Der Zugang einer Maschine, die nicht schwenkt: nur die Richtung `oben` bleibt, die Flächen
    der anderen sind unerreichbar – „die Maschine schwenkt nicht so weit“."""
    k = Vector(*oben)
    bleibt = [r for r in zugang_.richtungen if _gleich(Vector(*r.achse), k)]
    unerreichbar = dict(zugang_.unerreichbar)
    for r in zugang_.richtungen:
        if r not in bleibt:
            unerreichbar.update(dict.fromkeys(r.flaechen, tr("zg.grund.maschine")))
    return Zugang(bleibt, unerreichbar, zugang_.spannflaeche)


def spannflaeche_unten(form, unten=(0.0, 0.0, -1.0)):
    """Die Fläche, die im Spannmittel liegt, wenn keine gewählt ist: die unterste ebene, die nach
    `unten` zeigt – oder None."""
    u = Vector(*unten)
    from . import stl_teil

    daten = stl_teil.daten(form)
    if daten is not None:  # ein Körper aus einem STL: das unterste Dreieck, das nach unten schaut
        uv = np.array(tuple(u), dtype=float)
        unten_ = np.flatnonzero(daten.normale @ uv >= 1.0 - GLEICH)
        if not len(unten_):
            return None
        tiefe = (daten.unten[unten_] + daten.oben[unten_]) / 2 @ uv
        return f"Face{int(unten_[int(np.argmax(tiefe))]) + 1}"
    beste = None
    for n in range(ft.anzahl(form)):
        f = ft.flaeche(form, n)
        if f.Surface.__class__.__name__ != "Plane":
            continue
        u0, u1, v0, v1 = f.ParameterRange
        if not _gleich(f.normalAt((u0 + u1) / 2, (v0 + v1) / 2), u):
            continue
        tiefe = f.CenterOfMass.dot(u)
        if beste is None or tiefe > beste[0] + GENAU:
            beste = (tiefe, f"Face{n + 1}")
    return beste[1] if beste else None


def _stellung(maschine, k):
    """Die Rundachsen, mit denen die Maschine die Werkzeugachse auf `k` stellt, wie die Steuerung
    sie zeigt – oder None, wenn sie das mit ihren Anschlägen nicht kann."""
    from . import verfahren as vf

    loesungen = [
        r for r in maschine.loese(k) if all(a.erlaubt(r[a.buchstabe]) for a in maschine.rundachsen)
    ]
    if not loesungen:
        return None
    kette = maschine.pruefung.verfahren.kette
    zeichen = {a.buchstabe: vf.programm_vorzeichen(a.achse, kette) for a in maschine.rundachsen}
    return {b: round(w * zeichen[b], 3) + 0.0 for b, w in loesungen[0].items()}
