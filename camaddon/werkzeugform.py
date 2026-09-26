# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Umriss eines Werkzeugs aus seinen Maßen – für sein Bild (Spezifikation Werkzeugarten, 4).

Je Art ein paar Teile – Schaft, Schneide, Hals, Wendeplatte, Tastkugel – als
Vielecke in mm: x quer zur Achse, y von der Spitze (0) zum Schaft. Rundes
(Kugel, Eckradius, Radienprofil) ist fein unterteilt. Was ein Feld nicht
hergibt, wird geschätzt (werkzeuge.mass(): ein Anteil von D je Art,
Schneidenlänge 2 × D, Gesamtlänge ab dem Ende des Halses) – dieselben Maße
bekommt CAM (uebergabe_werkzeuge), damit es dasselbe Werkzeug zeigt. Die Halter der
Drehwerkzeuge haben feste Maße, denn dafür gibt es keine Felder.

Läuft ohne Oberfläche; gemalt wird in gui_werkzeugbild.
"""

import math
from dataclasses import dataclass

from . import werkzeuge as wz

# Woraus ein Teil ist – davon hängt die Farbe ab.
SCHAFT, SCHNEIDE, KUGEL = "schaft", "schneide", "kugel"
# Spannuten andeuten: rechtsgängig, linksgängig, gerade.
WENDEL_RECHTS, WENDEL_LINKS, WENDEL_GERADE = "rechts", "links", "gerade"

# Drehwerkzeuge: Halter 20 mm breit (im Bild 60 mm lang, sonst wäre die Platte
# winzig), Wendeplatte 12 mm Kantenlänge; sie steht an der Ecke über.
HALTER_BREITE = 20.0
HALTER_LAENGE = 60.0
PLATTE = 12.0
UEBERSTAND = PLATTE * 0.45

# Felder, die nur Schaft und Länge betreffen – sie machen die Schneide nicht unsicher.
_NICHT_SCHNEIDE = {"schneiden", "gesamtlaenge", "schaft", "ausfuehrung"}


@dataclass
class Teil:
    """Ein Teil des Bildes: geschlossenes Vieleck in mm, gestrichelt, wenn geschätzt."""

    stoff: str  # SCHAFT, SCHNEIDE oder KUGEL
    punkte: list
    geschaetzt: bool = False
    wendel: str = ""  # Spannuten andeuten: WENDEL_…, leer = keine


def teile(werkzeug, fremd=frozenset()):
    """Die Teile des Werkzeugs, in der Reihenfolge zum Malen (was hinten liegt, zuerst).

    `fremd`: Felder, die nicht eingetragen, sondern Beispiel oder geschätzt
    sind – deren Teile sind gestrichelt. Leer, wenn es nichts zu zeichnen gibt.
    """
    w = werkzeug
    daten = wz.artdaten(w.art)
    zeichner = _ZEICHNER.get(w.art, _schaftfraeser)
    if "durchmesser" in daten.felder and w.durchmesser <= 0:
        return []
    felder = set(daten.felder)
    unsicher = bool(set(fremd) - _NICHT_SCHNEIDE) or (
        "schneidenlaenge" in felder and not w.schneidenlaenge
    )
    schaft_unsicher = bool(fremd) or (
        {"gesamtlaenge", "schaft"} <= felder and not (w.gesamtlaenge and w.schaft)
    )
    return [t for t in zeichner(w, unsicher, schaft_unsicher) if len(t.punkte) >= 3]


def konus(werkzeug):
    """(Schneidenlänge, Kegelwinkel je Seite, Radius oben) des Konikfräsers.

    Der Kegel berührt die Kugel an der Spitze und endet mit der Schneide.
    """
    w = werkzeug
    r = w.durchmesser / 2
    lc = max(wz.mass(w, "schneidenlaenge"), r)
    winkel = min(max(w.kegelwinkel, 0.0), 45.0)
    alpha = math.radians(winkel)
    return lc, winkel, r / math.cos(alpha) + (lc - r) * math.tan(alpha)


def kegel(werkzeug):
    """(Spitzen-Ø, Höhe des Kegels, Spitzenwinkel) des Fasenfräsers und Kegelsenkers."""
    w = werkzeug
    winkel = min(max(wz.wert(w, "spitzenwinkel"), 1.0), 179.0)
    spitze = min(wz.mass(w, "spitzen_d"), w.durchmesser * 0.9)
    return spitze, (w.durchmesser - spitze) / 2 / _tan(winkel / 2), winkel


def radienprofil(werkzeug):
    """(Profilradius, Spitzen-Ø, Höhe des Bogens) des Radienfräsers.

    Wie in CAM: Der Bogen beginnt am Rand der Spitze, sein Mittelpunkt liegt
    auf ihrer Höhe. Leer ist die Spitze D − 2 × Radius – ein Viertelkreis;
    ist sie breiter, endet der Bogen früher.
    """
    w = werkzeug
    r = w.durchmesser / 2
    e = min(wz.mass(w, "profilradius"), r * 0.95)
    spitze = max(wz.mass(w, "spitzen_d"), w.durchmesser - 2 * e)
    mitte = spitze / 2 + e
    return e, spitze, math.sqrt(max(e * e - (mitte - r) ** 2, 0.0))


def grenzen(liste):
    """(x_min, y_min, x_max, y_max) über alle Teile."""
    xs = [x for teil in liste for x, _ in teil.punkte]
    ys = [y for teil in liste for _, y in teil.punkte]
    return min(xs), min(ys), max(xs), max(ys)


# --- Bausteine ------------------------------------------------------------------


def _rechteck(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _symmetrisch(rechts):
    """Geschlossener Umriss aus seiner rechten Hälfte (Punkte von oben zur Spitze)."""
    return rechts + [(-x, y) for x, y in reversed(rechts)]


def _bogen(mx, my, radius, von, bis, schritte=12):
    """Punkte auf einem Kreisbogen; Winkel in Grad, 0° = +x, gegen den Uhrzeigersinn."""
    return [
        (
            mx + radius * math.cos(math.radians(von + (bis - von) * i / schritte)),
            my + radius * math.sin(math.radians(von + (bis - von) * i / schritte)),
        )
        for i in range(schritte + 1)
    ]


def _zacken(radius, tiefe, oben, unten, steigung):
    """Gewindezähne an der rechten Seite, von oben nach unten: Spitze, Grund, Spitze …"""
    anzahl = max(int((oben - unten) / (steigung / 2)), 2)
    return [
        (radius if i % 2 == 0 else radius - tiefe, oben - (oben - unten) * i / anzahl)
        for i in range(anzahl + 1)
    ]


def _schaft(w, unten, halb, unsicher):
    """Der Schaft von `unten` bis zur Gesamtlänge, `halb` breit je Seite."""
    oben = max(wz.laenge_fuer_cam(w), unten)
    return Teil(SCHAFT, _rechteck(-halb, unten, halb, oben), unsicher)


def _masse(w):
    """(Radius, Schneidenlänge, halber Schaft) – eingetragen oder geschätzt."""
    return w.durchmesser / 2, wz.mass(w, "schneidenlaenge"), wz.mass(w, "schaft") / 2


def _tan(grad):
    return math.tan(math.radians(min(max(grad, 1.0), 179.0)))


# --- Fräsen ---------------------------------------------------------------------


def _schaftfraeser(w, unsicher, schaft_unsicher):
    r, lc, s = _masse(w)
    schneide = Teil(SCHNEIDE, _symmetrisch([(r, lc), (r, 0), (0, 0)]), unsicher, WENDEL_RECHTS)
    return [_schaft(w, lc, s, schaft_unsicher), schneide]


def _kugelfraeser(w, unsicher, schaft_unsicher):
    r, lc, s = _masse(w)
    lc = max(lc, r)
    rechts = [(r, lc)] + _bogen(0, r, r, 0, -90)
    return [
        _schaft(w, lc, s, schaft_unsicher),
        Teil(SCHNEIDE, _symmetrisch(rechts), unsicher, WENDEL_RECHTS),
    ]


def _torusfraeser(w, unsicher, schaft_unsicher):
    r, lc, s = _masse(w)
    e = min(wz.mass(w, "eckradius"), r)
    rechts = [(r, max(lc, e))] + _bogen(r - e, e, e, 0, -90) + [(0, 0)]
    return [
        _schaft(w, max(lc, e), s, schaft_unsicher),
        Teil(SCHNEIDE, _symmetrisch(rechts), unsicher, WENDEL_RECHTS),
    ]


def _konikfraeser(w, unsicher, schaft_unsicher):
    """Kugel an der Spitze, darüber der Kegel – je Seite um den Kegelwinkel weiter."""
    r, _lc, s = _masse(w)
    lc, winkel, oben = konus(w)
    rechts = [(oben, lc)] + _bogen(0, r, r, -winkel, -90)
    return [
        _schaft(w, lc, max(s, oben), schaft_unsicher),
        Teil(SCHNEIDE, _symmetrisch(rechts), unsicher, WENDEL_RECHTS),
    ]


def _schwalbenschwanz(w, unsicher, schaft_unsicher):
    """Unten breit, die Flanken steigen um den Flankenwinkel nach innen; darüber der Hals."""
    r, h, s = _masse(w)
    oben = max(r - h / _tan(wz.wert(w, "flankenwinkel")), r * 0.15)
    hals = wz.mass(w, "hals_d") / 2
    hals_oben = h + wz.mass(w, "hals_laenge")
    return [
        _schaft(w, hals_oben, s, schaft_unsicher),
        Teil(SCHAFT, _rechteck(-hals, h, hals, hals_oben), unsicher),
        Teil(SCHNEIDE, _symmetrisch([(oben, h), (r, 0), (0, 0)]), unsicher),
    ]


def _lollipop(w, unsicher, schaft_unsicher):
    """Eine Kugel am langen, dünnen Hals."""
    r, _lc, s = _masse(w)
    hals = wz.mass(w, "hals_d") / 2
    hals_oben = r + wz.mass(w, "hals_laenge")
    return [
        _schaft(w, hals_oben, s, schaft_unsicher),
        Teil(SCHAFT, _rechteck(-hals, r, hals, hals_oben), unsicher),
        Teil(SCHNEIDE, _bogen(0, r, r, 0, 360, 36)[:-1], unsicher),
    ]


def _fasenfraeser(w, unsicher, schaft_unsicher):
    """Kegel mit dem Spitzenwinkel, unten der Spitzen-Ø (0 = spitz)."""
    r, lc, s = _masse(w)
    spitze, h, _winkel = kegel(w)
    oben = max(lc, h)
    rechts = [(r, oben), (r, h), (spitze / 2, 0), (0, 0)]
    return [_schaft(w, oben, s, schaft_unsicher), Teil(SCHNEIDE, _symmetrisch(rechts), unsicher)]


def _radienfraeser(w, unsicher, schaft_unsicher):
    """Hohlkehle: Die äußere untere Ecke fehlt als Bogen mit dem Profilradius."""
    r, lc, s = _masse(w)
    e, spitze, hoehe = radienprofil(w)
    mitte = spitze / 2 + e
    oben = max(lc, hoehe)
    ende = math.degrees(math.atan2(hoehe, r - mitte))
    rechts = [(r, oben)] + _bogen(mitte, 0, e, ende, 180) + [(0, 0)]
    return [_schaft(w, oben, s, schaft_unsicher), Teil(SCHNEIDE, _symmetrisch(rechts), unsicher)]


def _planfraeser(w, unsicher, schaft_unsicher):
    """Flacher, breiter Körper; die Platten schneiden unten mit dem Einstellwinkel."""
    r, ap, s = _masse(w)
    kappa = wz.wert(w, "einstellwinkel") or 90.0
    innen = ap / _tan(kappa) if kappa < 89.9 else 0.0
    laenge = max(wz.laenge_fuer_cam(w), ap * 2)
    koerper = ap + (laenge - ap) * 0.6
    return [
        _schaft(w, koerper, min(s, r), schaft_unsicher),
        Teil(SCHAFT, _rechteck(-r, ap, r, koerper), schaft_unsicher),
        Teil(SCHNEIDE, _symmetrisch([(r, ap), (max(r - innen, 0), 0), (0, 0)]), unsicher),
    ]


def _nutenfraeser(w, unsicher, schaft_unsicher):
    """Eine Scheibe mit der Schneidenbreite am Hals."""
    r, _lc, s = _masse(w)
    b = wz.mass(w, "schneidenbreite")
    hals = wz.mass(w, "hals_d") / 2
    hals_oben = b + wz.mass(w, "hals_laenge")
    return [
        _schaft(w, hals_oben, min(s, r), schaft_unsicher),
        Teil(SCHAFT, _rechteck(-hals, b, hals, hals_oben), unsicher),
        Teil(SCHNEIDE, _rechteck(-r, 0, r, b), unsicher),
    ]


def _formfraeser(w, unsicher, schaft_unsicher):
    """Schneide mit einem Profil – angedeutet als Kerbe in der Seite."""
    r, lc, s = _masse(w)
    rechts = [(r, lc), (r, lc * 0.7), (r * 0.6, lc * 0.5), (r, lc * 0.3), (r, 0), (0, 0)]
    return [_schaft(w, lc, s, schaft_unsicher), Teil(SCHNEIDE, _symmetrisch(rechts), unsicher)]


def _gewindefraeser(w, unsicher, schaft_unsicher):
    """Zähne mit der Steigung über die Schneidenlänge, darüber der Hals."""
    r, lc, s = _masse(w)
    p = w.steigung or w.durchmesser * 0.15
    tiefe = min(p * 0.6, r * 0.3)
    rechts = _zacken(r, tiefe, lc, 0, p) + [(0, 0)]
    hals = wz.mass(w, "hals_d") / 2
    hals_oben = lc + wz.mass(w, "hals_laenge")
    return [
        _schaft(w, hals_oben, s, schaft_unsicher),
        Teil(SCHAFT, _rechteck(-hals, lc, hals, hals_oben), unsicher),
        Teil(SCHNEIDE, _symmetrisch(rechts), unsicher),
    ]


# --- Bohren ---------------------------------------------------------------------


def _bohrer(w, unsicher, schaft_unsicher):
    """Spitze mit dem Spitzenwinkel (Bohrer 118°, NC-Anbohrer 90° …)."""
    r, lc, s = _masse(w)
    h = min(r / _tan(wz.wert(w, "spitzenwinkel") / 2), lc)
    rechts = [(r, lc), (r, h), (0, 0)]
    return [
        _schaft(w, lc, s, schaft_unsicher),
        Teil(SCHNEIDE, _symmetrisch(rechts), unsicher, WENDEL_RECHTS),
    ]


def _zentrierbohrer(w, unsicher, schaft_unsicher):
    """Spitzer Zapfen (118°), darüber die Senkung mit dem Spitzenwinkel (60°) zum Körper."""
    r1 = w.durchmesser / 2
    r2 = max(wz.mass(w, "schaft") / 2, r1)
    zapfen = wz.mass(w, "schneidenlaenge")
    spitze = r1 / _tan(wz.SPITZENWINKEL_BOHRER / 2)
    senkung = (r2 - r1) / _tan(wz.wert(w, "spitzenwinkel") / 2)
    oben = zapfen + senkung
    rechts = [(r2, oben), (r1, zapfen), (r1, min(spitze, zapfen)), (0, 0)]
    return [_schaft(w, oben, r2, schaft_unsicher), Teil(SCHNEIDE, _symmetrisch(rechts), unsicher)]


def _gewindebohrer(w, unsicher, schaft_unsicher):
    """Gewindezähne mit der Steigung, unten der Anschnitt; die Wendel zeigt rechts oder links."""
    r, lg, s = _masse(w)
    p = w.steigung or w.durchmesser * 0.15
    tiefe = min(p * 0.6, r * 0.2)
    anschnitt = min(3 * p, lg / 2)
    rechts = _zacken(r, tiefe, lg, anschnitt, p) + [(max(r - 2.5 * tiefe, r * 0.5), 0), (0, 0)]
    wendel = WENDEL_LINKS if w.art == wz.GEWINDEBOHRER_LINKS else WENDEL_RECHTS
    return [
        _schaft(w, lg, s, schaft_unsicher),
        Teil(SCHNEIDE, _symmetrisch(rechts), unsicher, wendel),
    ]


def _kegelsenker(w, unsicher, schaft_unsicher):
    """Kegel mit dem Senkwinkel, darüber ein kurzer Zylinder."""
    r, _lc, s = _masse(w)
    spitze, h, _winkel = kegel(w)
    oben = h + w.durchmesser * 0.15
    rechts = [(r, oben), (r, h), (spitze / 2, 0), (0, 0)]
    return [_schaft(w, oben, s, schaft_unsicher), Teil(SCHNEIDE, _symmetrisch(rechts), unsicher)]


def _flachsenker(w, unsicher, schaft_unsicher):
    """Flach schneidender Kopf, darunter der Führungszapfen."""
    r, lc, s = _masse(w)
    fuehrung = min(wz.mass(w, "spitzen_d") / 2, r)
    zapfen = max(w.durchmesser * 0.35, 1.0)
    return [
        _schaft(w, lc, s, schaft_unsicher),
        Teil(SCHAFT, _rechteck(-fuehrung, -zapfen, fuehrung, 0), unsicher),
        Teil(SCHNEIDE, _symmetrisch([(r, lc), (r, 0), (0, 0)]), unsicher, WENDEL_RECHTS),
    ]


def _reibahle(w, unsicher, schaft_unsicher):
    """Langer Zylinder mit geraden Nuten und kleiner Fase an der Spitze."""
    r, lc, s = _masse(w)
    fase = max(w.durchmesser * 0.04, 0.2)
    rechts = [(r, lc), (r, fase), (r - fase, 0), (0, 0)]
    return [
        _schaft(w, lc, s, schaft_unsicher),
        Teil(SCHNEIDE, _symmetrisch(rechts), unsicher, WENDEL_GERADE),
    ]


def _bohrstange(w, unsicher, schaft_unsicher):
    """Dünne Stange über die Ausladung, unten seitlich die Schneidplatte bis zum Radius."""
    r, lc, s = _masse(w)
    stange = r * 0.6
    platte = [(stange * 0.2, 0), (r, 0), (stange * 0.2, w.durchmesser * 0.3)]
    return [
        _schaft(w, lc, max(min(s, r), stange), schaft_unsicher),
        Teil(SCHAFT, _rechteck(-stange, 0, stange, lc), unsicher),
        Teil(SCHNEIDE, platte, unsicher),
    ]


def _ausspindelwerkzeug(w, unsicher, schaft_unsicher):
    """Feinbohrkopf mit Stange darunter; unten die Schneide bis zum Radius."""
    r, lc, s = _masse(w)
    stange = r * 0.4
    kopf_unten = lc * 0.6
    platte = [(stange * 0.2, 0), (r, 0), (stange * 0.2, w.durchmesser * 0.25)]
    return [
        _schaft(w, lc, min(s, r * 0.8), schaft_unsicher),
        Teil(SCHAFT, _rechteck(-r * 1.1, kopf_unten, r * 1.1, lc), unsicher),
        Teil(SCHAFT, _rechteck(-stange, 0, stange, kopf_unten), unsicher),
        Teil(SCHNEIDE, platte, unsicher),
    ]


# --- Drehen ---------------------------------------------------------------------


def _gespiegelt(liste, ausfuehrung):
    """Links ist das Spiegelbild von rechts."""
    if ausfuehrung != wz.LINKS:
        return liste
    return [Teil(t.stoff, [(-x, y) for x, y in t.punkte], t.geschaetzt, t.wendel) for t in liste]


def _richtung(grad):
    return math.cos(math.radians(grad)), math.sin(math.radians(grad))


def _drehwerkzeug(w, unsicher, _schaft_unsicher):
    """Halter mit Wendeplatte: Die Hauptschneide steht im Einstellwinkel zur Vorschubrichtung
    (nach links, zum Futter), die Platte hat den Plattenwinkel an der Spitze."""
    epsilon = wz.wert(w, "plattenwinkel") or 80.0
    if w.ausfuehrung == wz.NEUTRAL:
        erste, zweite = 90 + epsilon / 2, 90 - epsilon / 2
        halter = _rechteck(-HALTER_BREITE / 2, PLATTE * 0.6, HALTER_BREITE / 2, HALTER_LAENGE)
    else:
        kappa = wz.wert(w, "einstellwinkel") or 95.0
        erste = 180.0 - kappa
        zweite = erste - epsilon
        halter = _rechteck(UEBERSTAND, UEBERSTAND, UEBERSTAND + HALTER_BREITE, HALTER_LAENGE)
    ax, ay = _richtung(erste)
    bx, by = _richtung(zweite)
    platte = [(0, 0), (PLATTE * bx, PLATTE * by)]
    platte += [(PLATTE * (ax + bx), PLATTE * (ay + by)), (PLATTE * ax, PLATTE * ay)]
    teile = [Teil(SCHAFT, halter), Teil(SCHNEIDE, platte, unsicher)]
    return _gespiegelt(teile, w.ausfuehrung)


def _einstechwerkzeug(w, unsicher, _schaft_unsicher):
    """Schmale Klinge mit der Stechbreite unter dem Halter, so tief wie die Stechtiefe."""
    b = w.schneidenbreite or 3.0
    tiefe = w.stechtiefe or 10.0
    unten_halter = tiefe + 3.0
    if w.ausfuehrung == wz.NEUTRAL:
        links = -b / 2
        halter = _rechteck(-HALTER_BREITE / 2, unten_halter, HALTER_BREITE / 2, HALTER_LAENGE)
    else:
        links = 0.0
        halter = _rechteck(0, unten_halter, HALTER_BREITE, HALTER_LAENGE)
    spitze = min(3.0, tiefe)
    teile = [
        Teil(SCHAFT, halter),
        Teil(SCHAFT, _rechteck(links, spitze, links + b, unten_halter)),
        Teil(SCHNEIDE, _rechteck(links, 0, links + b, spitze), unsicher),
    ]
    return _gespiegelt(teile, w.ausfuehrung)


def _gewindedrehwerkzeug(w, unsicher, _schaft_unsicher):
    """Dreieckige Platte mit dem Flankenwinkel an der Spitze unter dem Halter."""
    halb = math.tan(math.radians(wz.wert(w, "flankenwinkel") / 2))
    hoehe = PLATTE * 0.6
    platte = [(0, 0), (hoehe * halb, hoehe), (-hoehe * halb, hoehe)]
    if w.ausfuehrung == wz.NEUTRAL:
        halter = _rechteck(-HALTER_BREITE / 2, hoehe * 0.7, HALTER_BREITE / 2, HALTER_LAENGE)
    else:
        halter = _rechteck(-hoehe * halb, hoehe * 0.7, HALTER_BREITE, HALTER_LAENGE)
    teile = [Teil(SCHAFT, halter), Teil(SCHNEIDE, platte, unsicher)]
    return _gespiegelt(teile, w.ausfuehrung)


# --- Antasten -------------------------------------------------------------------


def _taster(w, unsicher, schaft_unsicher):
    """Tastkugel am Taststift, oben der Körper des Tasters."""
    r = w.durchmesser / 2
    stift = max(wz.mass(w, "schaft") / 2, r * 0.1)
    laenge = max(wz.laenge_fuer_cam(w), 4 * r)
    koerper = laenge * 0.65
    breite = max(3 * stift, 1.5 * w.durchmesser, 6.0)
    return [
        Teil(SCHAFT, _rechteck(-breite, koerper, breite, laenge), schaft_unsicher),
        Teil(SCHAFT, _rechteck(-stift, r, stift, koerper), schaft_unsicher),
        Teil(KUGEL, _bogen(0, r, r, 0, 360, 36)[:-1], unsicher),
    ]


_ZEICHNER = {
    wz.SCHAFTFRAESER: _schaftfraeser,
    wz.KUGELFRAESER: _kugelfraeser,
    wz.TORUSFRAESER: _torusfraeser,
    wz.KONIKFRAESER: _konikfraeser,
    wz.SCHWALBENSCHWANZFRAESER: _schwalbenschwanz,
    wz.LOLLIPOPFRAESER: _lollipop,
    wz.FASENFRAESER: _fasenfraeser,
    wz.RADIENFRAESER: _radienfraeser,
    wz.PLANFRAESER: _planfraeser,
    wz.NUTENFRAESER: _nutenfraeser,
    wz.FORMFRAESER: _formfraeser,
    wz.GEWINDEFRAESER: _gewindefraeser,
    wz.BOHRER: _bohrer,
    wz.ZENTRIERBOHRER: _zentrierbohrer,
    wz.NC_ANBOHRER: _bohrer,
    wz.GEWINDEBOHRER_RECHTS: _gewindebohrer,
    wz.GEWINDEBOHRER_LINKS: _gewindebohrer,
    wz.KEGELSENKER: _kegelsenker,
    wz.FLACHSENKER: _flachsenker,
    wz.REIBAHLE: _reibahle,
    wz.BOHRSTANGE: _bohrstange,
    wz.AUSSPINDELWERKZEUG: _ausspindelwerkzeug,
    wz.DREHWERKZEUG: _drehwerkzeug,
    wz.EINSTECHWERKZEUG: _einstechwerkzeug,
    wz.GEWINDEDREHWERKZEUG: _gewindedrehwerkzeug,
    wz.TASTER: _taster,
}
