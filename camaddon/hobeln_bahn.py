# SPDX-License-Identifier: LGPL-2.1-or-later
"""Dichtnut hobeln (Spezifikation Strategien 13.10; Manuel, 2026-11-14: „eine nut in einem deckel
die mit einem "stech" oder "scharb" werkzeug sozusagen rausgekratzt wird … da man dadurch unten am
grund auch ne dichtfläche hinbekommen würde und nicht wie beim fräse querrillen in de nut hat“ –
„form muss egal sein wenn ich in einem teil eine nut zeichne soll diese nachgefahren werden ...
(natürlich wenn man spitze ecken hat geht das nicht man braucht schon rundungen sonst klappt das
nicht)“).

Schritt 1 des Bauplans – **die Nut und ihre Mittellinie**:

- **Erkennen** (hobelnuten()): der Grund einer umlaufenden Nut – eine ebene Fläche, die nach oben
  schaut, mit genau zwei Rändern (außen und innen), überall gleich breit. Die Form ist egal:
  Kreisring, Rechteck mit Radien, der Kontur des Deckels nach.
- **Mittellinie:** der äußere Rand um die halbe Breite nach innen versetzt, als Strecken und Bögen
  in Fahrtrichtung (gegen den Uhrzeigersinn) – auf ihr läuft die Schneide, die Spindel folgt
  ihrer Richtung.
- **Maße:** Breite, Tiefe (bis zur niedrigsten Oberkante der Wände), Länge der Mittellinie, der
  kleinste Radius.
- **Was nicht geht, mit Grund** (Hobelnut.grund): eine spitze Ecke in einer Wand (die Klinge kann
  sich dort nicht drehen), wechselnde Breite.
- **Die Klinge** (klinge_pruefen()): Breite höchstens die der Nut, und ihre hintere äußere Ecke
  darf in der engsten Kurve nicht an die Außenwand stoßen – die Schneide vorn auf der
  Mittellinie, der Körper um `laenge` dahinter; mitgerechnet, dass die Spindel nicht genau in
  Fahrtrichtung steht (WINKEL_FEHLER, ein halber Satzschritt). Genau an jeder Stelle der Bahn:
  _klinge_luft().

Schritt 2 – **die Bahn** (planen()): Die Schneide läuft auf der Mittellinie (ist die Klinge schmaler
als die Nut, in mehreren Spuren nebeneinander), in kleinen Schritten (SCHRITT, einstellbar), und die
Spindel steht je Satz so, dass die Klinge in Fahrtrichtung zeigt: Winkel = Richtung der Bahn +
Versatz des Werkzeugs (bei welchem Spindelwinkel die Schneide nach +X zeigt – beim Einrichten
gemessen). Der Winkel steht als Kommentar „(SPINDEL …)“ vor jedem Satz; das Programm (Schritt 5)
macht daraus je Steuerung den Spindelwinkel im Satz. Die Nut ist davor gefräst, bis auf `rest` über
dem Grund: Die Klinge kommt senkrecht nur bis 0,3 über das Material, dann flach in Fahrtrichtung auf
einem geraden Stück hinein (Manuel: „an einem geraden Stück in einer Rampe ins Bauteil“) und mit
stetigem Gefälle durch die Nut, je Umlauf um `zustellung` tiefer, bis auf das Aufmaß; dort ein
ebener Umlauf und die Leerumläufe. Gefahren wird nur vorwärts (die Klinge schneidet nur nach vorn);
mehrere Spuren wechseln sich je Umlauf ab (planen()).

Noch nicht: Nuten mit Enden (Langloch, zum Rand offen) – dort kommt der Hub mit Abheben dazu.
Das Werkzeug, die Operation und das Programm folgen in den Schritten 3 bis 5.

Läuft ohne Oberfläche.
"""

import math
from collections import OrderedDict
from dataclasses import dataclass

from . import bahn as bn
from . import kontur_bahn as kb
from .sprache import tr

BREITE_GLEICH = 0.02  # mm – so gleich muss die Nut überall breit sein
KNICK = math.radians(6.0)  # ab diesem Winkel zwischen zwei Stücken einer Wand: eine Ecke
NETZ = 0.001  # mm – so fein werden Kurven der Wände abgetastet (Ecken von Rundungen trennen)
PROBEN = 0.5  # mm – so dicht wird die Breite an der inneren Wand gemessen
SPIEL = 0.005  # mm – so viel Luft braucht die hintere Ecke der Klinge zur Außenwand
FORMEN_GEMERKT = 8
SCHRITT = 0.5  # mm – so lang ist ein Satz der Hobelbahn (die Spindel dreht je Satz nach)
SPUR_UEBERLAPP = 0.2  # so viel der Klingenbreite überlappen zwei Spuren
# mm – so schmal darf der Rand am Grund je Seite ungehobelt bleiben, sonst eine zweite Spur: Bis
# 14.11. waren es 0,05 – die Klinge 3,5 ließ in der 3,6er Nut je Seite einen Streifen 0,05 × Rest
# stehen, eine Stufe in der O-Ring-Nut. Jetzt laufen die äußeren Spuren bis SPIEL an die Wände.
SPUR_REST = 0.001
SPUR_SCHRAEG = math.radians(2.0)  # so schräg darf die Spur seitlich ausweichen (weich, nicht quer)
SPINDEL = "SPINDEL"  # der Kommentar mit dem Spindelwinkel vor jedem Satz: „(SPINDEL 123.456)“


@dataclass(frozen=True)
class Hobelnut:
    """Eine umlaufende Nut, deren Grund sich hobeln lässt (oder warum nicht: `grund`)."""

    name: str  # die Fläche des Grunds („Face12“)
    flaechen: tuple  # Grund und Wände
    breite: float
    z_boden: float
    z_oben: float  # die niedrigste Oberkante der Wände
    segmente: tuple  # die Mittellinie: kontur_bahn._Strecke / _Bogen, gegen den Uhrzeigersinn
    laenge: float  # der Mittellinie (mm)
    r_min: float  # ihr kleinster Radius; inf: nur Geraden
    geschlossen: bool = True
    grund: str = ""  # warum sie nicht geht – leer: geht

    @property
    def tiefe(self):
        return self.z_oben - self.z_boden

    def text(self):
        """„3 breit, 2 tief, 223 lang, kleinster Radius 10“ – die Zeile im Assistenten."""
        from . import einheiten

        radius = (
            ""
            if not math.isfinite(self.r_min)
            else tr("hn.radius", r=einheiten.text(self.r_min, einheiten.LAENGE))
        )
        return tr(
            "hn.text",
            breite=einheiten.text(self.breite, einheiten.LAENGE),
            tiefe=einheiten.text(self.tiefe, einheiten.LAENGE),
            laenge=einheiten.text(self.laenge, einheiten.LAENGE, 0),
            radius=radius,
        )


# --- Erkennen ---------------------------------------------------------------------------------------

_NUTEN = OrderedDict()  # hashCode → (Form, [Hobelnut])


def alle_hobelnuten(form):
    """[Hobelnut] – alle umlaufenden Nuten der Form, auch die nicht hobelbaren (Hobelnut.grund)."""
    kennung = form.hashCode()
    eintrag = _NUTEN.get(kennung)
    if eintrag is not None and eintrag[0].isSame(form):
        return eintrag[1]
    ergebnis = _nuten(form)
    _NUTEN[kennung] = (form, ergebnis)
    while len(_NUTEN) > FORMEN_GEMERKT:
        _NUTEN.popitem(last=False)
    return ergebnis


def hobelnuten(form, namen=None):
    """[Hobelnut] – die hobelbaren Nuten der Form; mit `namen` nur die, zu denen eine dieser
    Flächen gehört (der Grund oder eine Wand)."""
    gesucht = set(namen) if namen is not None else None
    return [
        n
        for n in alle_hobelnuten(form)
        if not n.grund and (gesucht is None or gesucht & set(n.flaechen))
    ]


def _ist_grund(flaeche):
    """Eine ebene Fläche, die nach oben schaut, mit genau zwei Rändern?"""
    import Part

    if not isinstance(flaeche.Surface, Part.Plane) or len(flaeche.Wires) != 2:
        return False
    # Nicht über den Kasten: Mit Freiformrändern ist er um Hundertstel zu hoch.
    if abs(abs(flaeche.Surface.Axis.z) - 1.0) > 1e-9:
        return False
    u0, u1, v0, v1 = flaeche.ParameterRange
    return flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2).z > 1.0 - 1e-6


def _nuten(form):

    alle = form.Faces
    ergebnis = []
    for nummer, flaeche in enumerate(alle):
        if not _ist_grund(flaeche):
            continue
        aussen = flaeche.OuterWire
        innen = next(w for w in flaeche.Wires if not w.isSame(aussen))
        waende, z_oben = _waende(form, alle, flaeche)
        z_boden = float(flaeche.Surface.Position.z)
        if not waende or z_oben <= z_boden + kb.NAH:
            continue  # kein Grund zwischen zwei Wänden: eine Stufe, ein Absatz
        name = f"Face{nummer + 1}"
        breite, schwankung = _breite(aussen, innen)
        grund = ""
        segmente, laenge, r_min = (), 0.0, math.inf
        if schwankung > BREITE_GLEICH:
            grund = tr(
                "hn.grund.breite",
                von=_mm(breite - schwankung / 2),
                bis=_mm(breite + schwankung / 2),
            )
        else:
            ecke = _ecke(aussen) or _ecke(innen)
            if ecke is not None:
                grund = tr("hn.grund.ecke", x=_mm(ecke[0]), y=_mm(ecke[1]))
            else:
                segmente = _mittellinie(aussen, breite)
                if not segmente:
                    grund = tr("hn.grund.mittellinie")
                else:
                    laenge = sum(s.laenge for s in segmente)
                    r_min = _kleinster_radius(segmente)
        ergebnis.append(
            Hobelnut(
                name, (name, *waende), breite, z_boden, z_oben, tuple(segmente), laenge, r_min,
                True, grund,
            )  # fmt: skip
        )
    return ergebnis


def _mm(wert):
    from . import einheiten

    return einheiten.text(wert, einheiten.LAENGE)


def _waende(form, alle, grund):
    """(Namen der Wände am Rand des Grunds, die niedrigste Oberkante) – Wände stehen senkrecht
    und steigen vom Grund auf. Fehlt an einer Kante die Wand, ist es keine Nut: ([], 0)."""
    import Part

    namen, oben = [], math.inf
    z = float(grund.Surface.Position.z)
    for kante in grund.Edges:
        wand = None
        for nachbar in form.ancestorsOfType(kante, Part.Face):
            if nachbar.isSame(grund):
                continue
            hoehen = [float(v.Point.z) for v in nachbar.Vertexes]  # genau, anders als der Kasten
            if kb.ist_wand(nachbar) and max(hoehen) > z + kb.NAH and min(hoehen) > z - kb.NAH:
                wand = nachbar
        if wand is None:
            return [], 0.0
        oben = min(oben, max(float(v.Point.z) for v in wand.Vertexes))
        for k, f in enumerate(alle):
            if f.isSame(wand):
                if f"Face{k + 1}" not in namen:
                    namen.append(f"Face{k + 1}")
                break
    return namen, oben


def _breite(aussen, innen):
    """(Breite, Schwankung): der Abstand der inneren Wand zur äußeren, an Stellen alle PROBEN mm
    – der Mittelwert und der Unterschied zwischen größtem und kleinstem."""
    import Part

    anzahl = max(24, int(innen.Length / PROBEN))
    abstaende = [aussen.distToShape(Part.Vertex(p))[0] for p in innen.discretize(Number=anzahl)]
    kleinste, groesste = min(abstaende), max(abstaende)
    return (kleinste + groesste) / 2.0, groesste - kleinste


def _richtung_am_ende(segment, anfang):
    """Die Fahrtrichtung (Winkel) am Anfang oder Ende eines Stücks."""
    if segment.bogen is None:
        return math.atan2(segment.nach[1] - segment.von[1], segment.nach[0] - segment.von[0])
    p = segment.von if anfang else segment.nach
    radial = math.atan2(p[1] - segment.mitte[1], p[0] - segment.mitte[0])
    return radial - math.pi / 2 if segment.uhr else radial + math.pi / 2


def _knick(a, b):
    """Der Winkel (0 … π) zwischen dem Ende von `a` und dem Anfang von `b`."""
    d = (_richtung_am_ende(b, True) - _richtung_am_ende(a, False)) % (2 * math.pi)
    return min(d, 2 * math.pi - d)


def _ecke(draht):
    """Die erste Ecke im Rand `draht` – (x, y), wo zwei Stücke mit einem Knick aneinanderstoßen;
    None, wenn alles gerundet ist."""
    segmente = kb._segmente(draht, NETZ)
    for a, b in zip(segmente, segmente[1:] + segmente[:1], strict=True):
        if _knick(a, b) > KNICK:
            return a.nach
    return None


def _mittellinie(aussen, breite):
    """Die Mittellinie als Strecken und Bögen, gegen den Uhrzeigersinn – der äußere Rand um die
    halbe Breite nach innen; [] wenn der Versatz nicht ein geschlossener Zug wird."""
    try:
        draehte = kb._versatz_draehte(aussen, -breite / 2.0, False)
    except Exception:  # noqa: BLE001 – OpenCascade: kein Versatz
        return []
    if len(draehte) != 1 or not draehte[0].isClosed():
        return []
    segmente = kb._segmente(draehte[0], NETZ)
    if not segmente:
        return []
    # Gegen den Uhrzeigersinn: die umlaufene Fläche (Gaußsche Trapezformel über die Stellen) > 0.
    proben = kb._abtasten(segmente, 0.5, True)
    x, y = proben.x, proben.y
    flaeche = 0.5 * float(
        (x * (y[list(range(1, len(y))) + [0]]) - y * x[list(range(1, len(x))) + [0]]).sum()
    )
    if flaeche < 0:
        segmente = [s.umgekehrt() for s in reversed(segmente)]
    return segmente


def _kleinster_radius(segmente):
    """Der kleinste Radius der Mittellinie: der der Bögen; bei Linienzügen (eine Freiformkurve)
    der Umkreis dreier Stellen nacheinander."""
    kleinster = math.inf
    for a, b in zip(segmente, segmente[1:] + segmente[:1], strict=True):
        if a.bogen is not None:
            kleinster = min(kleinster, a.radius)
        elif b.bogen is None:
            winkel = _knick(a, b)
            if winkel > 1e-4:  # zwei Sehnen einer Kurve: R ≈ mittlere Sehne ÷ Winkel
                kleinster = min(kleinster, 0.5 * (a.laenge + b.laenge) / winkel)
    return kleinster


# --- Die Klinge -------------------------------------------------------------------------------------
#
# Die Klinge ist ein Rechteck: die Schneide vorn (`breite` quer) auf dem Punkt der Bahn, der Körper
# `laenge` dahinter; sie dreht um den Punkt. Sie steht nie genau in Fahrtrichtung (Gegenprüfung vom
# 14.11.):
# - Steuerungen, die den Winkel VOR dem Satz stellen (Heidenhain Zyklus 13 + M19, LinuxCNC/Haas
#   M19 R, Fanuc/Mach M19 S), drehen am alten Punkt schon für den nächsten Satz. Das Programm gibt
#   ihnen die Mitte zweier Winkel (postprozessor) – sie steht dann bis zu einem halben Satzschritt
#   (Schritt ÷ 2R) neben der Fahrtrichtung. Mit dem Winkel des nächsten Punkts waren es am Deckel
#   (b 3,5 × 1,1, R 12) 0,032 mm hinter der Wand, bei R 3 mit 2,6 × 2 0,18 mm.
# - Fanuc stellt in ganzen Grad (M19 S, ± 0,5°); auch sonst steht eine Spindel nicht genauer:
#   WINKEL_FEHLER.
# Beides rechnen kleinster_radius_fuer() (für den Vorschlag und die erste Prüfung) und, genau an
# jeder Stelle der Bahn, _klinge_luft().

WINKEL_FEHLER = math.radians(0.5)
PROBE = 0.04  # mm – so dicht wird die Mittellinie für _klinge_luft() abgetastet (Fehler < 0,0002)


def _ueberstand(r, breite, laenge, schritt, r_mitte=None):
    """(außen, innen): so weit ragt die Klinge über die halbe Schneidenbreite neben ihrer Spur
    hinaus – auf einem Bogen, auf dem die Spur den Radius `r` hat (inf: auf einer Geraden), wenn
    sie bis zu einem halben Satzschritt (Schritt ÷ 2 · `r_mitte`, der Radius der Mittellinie) und
    WINKEL_FEHLER neben der Fahrtrichtung steht. Außen: die hintere äußere Ecke (dreht sie voraus);
    innen: die innere Flanke (bleibt sie zurück), dazu die Höhe der Sehne zwischen zwei Sätzen."""
    b2, lg = breite / 2.0, max(laenge, 0.0)
    if not math.isfinite(r):
        d = WINKEL_FEHLER
        seite = lg * math.sin(d) + b2 * math.cos(d) - b2
        return max(seite, 0.0), max(seite, 0.0)
    rm = r if r_mitte is None else r_mitte
    d = min(schritt / (2.0 * max(rm, 1e-9)) + WINKEL_FEHLER, math.pi / 4)
    c, s = math.cos(d), math.sin(d)
    vorn = r * r + 2 * r * b2 * c + b2 * b2
    hinten = r * r + lg * lg + b2 * b2 + 2 * r * b2 * c + 2 * r * lg * s
    aussen = math.sqrt(max(vorn, hinten)) - (r + b2)
    if r * s <= lg:  # der Punkt der Flanke, der der Mitte am nächsten kommt
        innen_r = r * c - b2
    else:
        innen_r = math.sqrt(max(r * r + lg * lg + b2 * b2 - 2 * r * lg * s - 2 * r * b2 * c, 0.0))
    # Zwischen zwei Sätzen fährt sie die Sehne: in der Mitte um ihre Höhe (s² ÷ 8R) nach innen.
    sehne = schritt * schritt / (8.0 * max(rm, 1e-9))
    return max(aussen, 0.0), max((r - b2) - innen_r, 0.0) + sehne


def kleinster_radius_fuer(nut_breite, breite, laenge, schritt=SCHRITT):
    """Der kleinste Radius der Mittellinie, den eine Klinge (`breite` breit, der Körper `laenge`
    hinter der Schneide) in einer Nut der Breite `nut_breite` fahren kann: Sie ragt dort nach
    keiner Seite weiter als bis SPIEL vor die Wand (_ueberstand). 0: jede Kurve; inf: die Klinge
    ist zu breit, oder sie stößt schon auf einer Geraden an (WINKEL_FEHLER)."""
    luft = (nut_breite - breite) / 2.0 - SPIEL
    if luft < 0:
        return math.inf

    def geht(r):
        return max(_ueberstand(r, breite, laenge, schritt)) <= luft + 1e-12

    if not geht(math.inf):
        return math.inf
    unten, oben = 0.0, max(breite, 1.0)
    while not geht(oben):
        oben *= 2.0
        if oben > 1e6:
            return math.inf
    for _ in range(60):
        mitte = (unten + oben) / 2.0
        if geht(mitte):
            oben = mitte
        else:
            unten = mitte
    return oben if unten > 0 or not geht(1e-9) else 0.0


def klinge_pruefen(nut, breite, laenge, schritt=SCHRITT):
    """ "" wenn die Klinge die Nut fahren kann – sonst der Satz, warum nicht (zu breit; der
    Radius, den sie bräuchte)."""
    if breite <= 0:
        return tr("hn.grund.klinge_breite_fehlt")
    if breite > nut.breite - 2 * SPIEL + 1e-9:
        return tr("hn.grund.klinge_breit", b=_mm(breite), breite=_mm(nut.breite))
    noetig = kleinster_radius_fuer(nut.breite, breite, laenge, schritt)
    if nut.r_min < noetig - 1e-9:
        return tr(
            "hn.grund.klinge_radius", r=_mm(nut.r_min), noetig=_mm(noetig), laenge=_mm(laenge)
        )
    return ""


def _klinge_luft(nut, reihe, breite, laenge):
    """Je Stelle der Spur `reihe` ([(x, y, Richtung)], geschlossen) die kleinste Luft der Klinge
    zur Wand, weniger SPIEL (< 0: zu nah), und die Seite (+1 links, −1 rechts), an der es am
    engsten ist – genau gerechnet gegen die Mittellinie (die Wände liegen ± Breite/2 neben ihr),
    in jeder Stellung, die eine Steuerung fährt: am Punkt mit seinem Winkel (Siemens, SPOS im
    Satz); mit der Mitte aus dem Winkel davor und seinem am Punkt davor, unterwegs und am Punkt
    (die Steuerungen, die vor dem Satz drehen); jeweils ± WINKEL_FEHLER."""
    import numpy as np

    proben = kb._abtasten(nut.segmente, PROBE, True)
    mx, my = proben.x, proben.y
    anzahl_m = len(mx)
    tx, ty = np.roll(mx, -1) - np.roll(mx, 1), np.roll(my, -1) - np.roll(my, 1)
    lang = np.hypot(tx, ty)
    tx, ty = tx / lang, ty / lang
    n = len(reihe)
    px = np.array([p[0] for p in reihe])
    py = np.array([p[1] for p in reihe])
    pr = np.unwrap(np.array([p[2] for p in reihe]))
    # Je Stelle die nächste Probe der Mittellinie (in Stücken: n × Proben wäre zu groß).
    naechste = np.empty(n, dtype=int)
    for k in range(0, n, 256):
        d2 = (px[k : k + 256, None] - mx[None]) ** 2 + (py[k : k + 256, None] - my[None]) ** 2
        naechste[k : k + 256] = d2.argmin(axis=1)
    vor = np.roll(np.arange(n), 1)
    dr = (pr - pr[vor] + math.pi) % (2 * math.pi) - math.pi
    mitte_r = pr[vor] + dr / 2.0
    e = WINKEL_FEHLER
    # Stellungen: (x, y, Winkel, Stelle, nächste Probe)
    teile = []
    for sx, sy, sr, sk in (
        (px, py, pr + e, naechste),
        (px, py, pr - e, naechste),
        (px[vor], py[vor], mitte_r + e, naechste[vor]),
        (px[vor], py[vor], mitte_r - e, naechste[vor]),
        ((px + px[vor]) / 2, (py + py[vor]) / 2, mitte_r + e, naechste),
        ((px + px[vor]) / 2, (py + py[vor]) / 2, mitte_r - e, naechste),
        (px, py, mitte_r + e, naechste),
        (px, py, mitte_r - e, naechste),
    ):
        teile.append((sx, sy, sr, np.arange(n), sk))
    sx = np.concatenate([t[0] for t in teile])
    sy = np.concatenate([t[1] for t in teile])
    sr = np.concatenate([t[2] for t in teile])
    stelle = np.concatenate([t[3] for t in teile])
    start = np.concatenate([t[4] for t in teile])
    b2, lg = breite / 2.0, max(laenge, 0.0)
    lokal = [(0.0, b2), (0.0, -b2)]
    for t in (0.25, 0.5, 0.75, 1.0):
        lokal += [(-lg * t, b2), (-lg * t, -b2)]
    lu = np.array([u for u, _v in lokal])
    lv = np.array([v for _u, v in lokal])
    fenster = int(math.ceil((lg + b2 + 0.3) / PROBE)) + 2
    versatz = np.arange(-fenster, fenster + 1)
    erlaubt = nut.breite / 2.0 - SPIEL
    luft = np.full(len(sx), np.inf)
    seite = np.zeros(len(sx))
    for k in range(0, len(sx), 256):
        sl = slice(k, k + 256)
        c, s = np.cos(sr[sl])[:, None], np.sin(sr[sl])[:, None]
        qx = sx[sl][:, None] + c * lu[None] - s * lv[None]  # (Stellungen, Punkte der Klinge)
        qy = sy[sl][:, None] + s * lu[None] + c * lv[None]
        idx = (start[sl][:, None] + versatz[None]) % anzahl_m  # (Stellungen, Fenster)
        fx, fy = mx[idx][:, None, :], my[idx][:, None, :]
        d2 = (qx[:, :, None] - fx) ** 2 + (qy[:, :, None] - fy) ** 2
        wo = d2.argmin(axis=2)
        nah = np.take_along_axis(idx[:, None, :].repeat(len(lu), 1), wo[:, :, None], 2)[:, :, 0]
        kreuz = tx[nah] * (qy - my[nah]) - ty[nah] * (qx - mx[nah])
        abstand = np.sqrt(np.take_along_axis(d2, wo[:, :, None], 2)[:, :, 0]) * np.sign(kreuz)
        l_je = erlaubt - np.abs(abstand)
        schlimm = l_je.argmin(axis=1)
        luft[sl] = l_je[np.arange(len(schlimm)), schlimm]
        seite[sl] = np.sign(abstand[np.arange(len(schlimm)), schlimm])
    je_stelle = np.full(n, np.inf)
    seite_je = np.zeros(n)
    for i in np.argsort(-luft):  # zuletzt die engste: sie bleibt stehen
        if luft[i] <= je_stelle[stelle[i]]:
            je_stelle[stelle[i]] = luft[i]
            seite_je[stelle[i]] = seite[i] or 1.0
    return je_stelle, seite_je


# --- Die Bahn ---------------------------------------------------------------------------------------

# Manuel, 2026-11-14: „Die Einfahrt muss flach passieren also an einem geraden Stück in einer
# Rampe ins Bauteil also 0.3 mm vor Oberkante anfangen und in Richtung der Nut fahren“ – und: „man
# kann die Zustellung auch über die komplette Nut machen ist sinnvoller ja auch die erste Zustellung
# einfach so machen .... Das es sozusagen eine stetiges gefallen durch die Nut geht“.
UEBER_MATERIAL = 0.3  # mm – so hoch über dem Material endet das senkrechte Hinab
GERADE_MIN = 2.0  # mm – so lang muss ein gerades Stück der Mittellinie sein, um dort anzufangen
LUFT_BOGEN = 5.0  # mm – ohne gerades Stück: so lang die Rampe in der Luft vor dem Material


@dataclass(frozen=True)
class Hobelwerte:
    """Was das Hobeln braucht; Längen in mm, Winkel in Grad, z nach oben im Job."""

    breite: float  # der Klinge (quer zur Fahrt)
    laenge: float  # der Klinge hinter der Schneide
    versatz: float  # bei diesem Spindelwinkel zeigt die Schneide nach +X
    zustellung: float  # je Umlauf tiefer (Horn: höchstens 0,3 je Hub)
    rest: float  # so viel steht nach dem Fräsen noch über dem Grund
    sicher: float  # z für den Eilgang über allem
    vorschub: float  # mm/min – die Schnittgeschwindigkeit
    eintauchen: float = 0.0  # mm/min – hinab bis über das Material; 0: wie der Vorschub
    aufmass: float = 0.0  # bleibt auf dem Grund stehen
    leerumlaeufe: int = 1  # Umläufe auf Endtiefe ohne Zustellung
    sicherheit: float = 2.0  # so weit über der Oberkante endet der Eilgang hinab
    schritt: float = SCHRITT


@dataclass
class Hobelbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], je Satz der Spindelwinkel als Notiz „SPINDEL …“
    winkel: list  # je Punkt der Spindelwinkel (Grad, fortlaufend) – None im Eilgang
    spuren: int
    umlaeufe: int  # je Spur, mit den Leerumläufen
    laenge: float  # mm im Vorschub
    zeit: float  # Minuten
    spur: list = None  # je Punkt die Spur (0 …), None außerhalb eines Umlaufs
    stelle: list = None  # je Punkt die Stelle der Spur (0: wo die Klinge ins Material kommt)
    gerade: bool = True  # angefangen auf einem geraden Stück (sonst an der flachsten Stelle)


def _stellen_je_stueck(nut, schritt):
    """[(x, y, Richtung rad, Nummer des Stücks)] längs der Mittellinie, höchstens `schritt`
    auseinander, der erste Punkt am Anfang, ohne Wiederholung am Ende (geschlossen)."""
    ergebnis = []
    for nummer, s in enumerate(nut.segmente):
        anzahl = max(1, int(math.ceil(s.laenge / schritt - 1e-9)))
        for i in range(anzahl):
            t = i / anzahl
            x, y = s.bei(t)
            if s.bogen is None:
                richtung = math.atan2(s.nach[1] - s.von[1], s.nach[0] - s.von[0])
            else:
                radial = math.atan2(y - s.mitte[1], x - s.mitte[0])
                richtung = radial - math.pi / 2 if s.uhr else radial + math.pi / 2
            ergebnis.append((float(x), float(y), richtung, nummer))
    return ergebnis


def _stellen(nut, schritt):
    """[(x, y, Richtung rad)] längs der Mittellinie (_stellen_je_stueck)."""
    return [s[:3] for s in _stellen_je_stueck(nut, schritt)]


def _weg(punkte):
    """Die Längen von Punkt zu Punkt einer geschlossenen Folge [(x, y, …)]: [i] von i−1 nach i."""
    return [math.hypot(punkte[i][0] - punkte[i - 1][0], punkte[i][1] - punkte[i - 1][1])
            for i in range(len(punkte))]  # fmt: skip


def _anfang(nut, stellen):
    """(Stelle, an der die Klinge ins Material kommt; wie viele Stellen davor die Rampe in der Luft
    beginnt; auf einer Geraden?) – Manuel: „an einem geraden Stück in einer Rampe ins Bauteil“. Das
    längste gerade Stück der Mittellinie (Strecken ohne Knick hintereinander, wenigstens
    GERADE_MIN): die Rampe in der Luft über seine erste Hälfte, in der Mitte ins Material – die
    Spindel steht dort fest. Ohne gerades Stück (Kreis, Ellipse) die flachste Stelle (am
    wenigsten Drehung auf ±2 mm), die Rampe LUFT_BOGEN davor."""
    seg = nut.segmente
    n_seg = len(seg)
    beste, beste_laenge = None, 0.0
    if any(s.bogen is not None for s in seg):
        # Bei einem Stück anfangen, vor dem keine Gerade ohne Knick liegt.
        erster = next(
            i for i in range(n_seg)
            if not (seg[i].bogen is None and seg[i - 1].bogen is None
                    and _knick(seg[i - 1], seg[i]) < 1e-6)
        )  # fmt: skip
        i = 0
        while i < n_seg:
            k = (erster + i) % n_seg
            if seg[k].bogen is not None:
                i += 1
                continue
            laenge, j = 0.0, i
            while j < n_seg:
                kk = (erster + j) % n_seg
                vorher = (erster + j - 1) % n_seg
                if seg[kk].bogen is not None or (j > i and _knick(seg[vorher], seg[kk]) >= 1e-6):
                    break
                laenge += seg[kk].laenge
                j += 1
            if laenge > beste_laenge:
                beste, beste_laenge = k, laenge
            i = max(j, i + 1)
    n = len(stellen)
    weg = _weg(stellen)
    if beste is not None and beste_laenge >= GERADE_MIN:
        s0 = next(i for i, p in enumerate(stellen) if p[3] == beste)
        luft, m = 0.0, 0
        while luft < beste_laenge / 2.0 - 1e-9 and m < n - 1:
            m += 1
            luft += weg[(s0 + m) % n]
        return (s0 + m) % n, m, True
    # Die flachste Stelle: am wenigsten Drehung der Richtung auf ±2 mm.
    dreh = [((stellen[i][2] - stellen[i - 1][2] + math.pi) % (2 * math.pi)) - math.pi
            for i in range(n)]  # fmt: skip
    fenster = max(1, int(round(2.0 / max(sum(weg) / n, 1e-9))))
    summe = [abs(sum(dreh[(i + k) % n] for k in range(-fenster, fenster + 1))) for i in range(n)]
    c = min(range(n), key=lambda i: (round(summe[i], 9), i))
    luft_soll = min(LUFT_BOGEN, sum(weg) / 8.0)
    luft, m = 0.0, 0
    while luft < luft_soll - 1e-9 and m < n - 1:
        luft += weg[(c - m) % n]
        m += 1
    return c, m, False


def _spuren(nut, breite):
    """Die Versätze der Spuren quer zur Mittellinie (mm, + nach links): eine, wenn die Klinge die
    Nut füllt; sonst so viele, dass sie mit SPUR_UEBERLAPP überlappen und die äußeren an den
    Wänden laufen."""
    frei = max(nut.breite - breite - 2 * SPIEL, 0.0) / 2.0
    if frei <= SPUR_REST + 1e-9:
        return [0.0]
    abstand = breite * (1.0 - SPUR_UEBERLAPP)
    anzahl = int(math.ceil(2 * frei / abstand - 1e-9)) + 1
    return [-frei + 2 * frei * k / (anzahl - 1) for k in range(anzahl)]


def _kruemmung(stellen, laenge):
    """Je Stelle der kleinste Krümmungsradius (mit Vorzeichen: + Linkskurve) über die Länge der
    Klinge dahinter – dort schwenkt ihre hintere Ecke aus; inf auf Geraden."""
    n = len(stellen)
    radien = []
    for i in range(n):
        x0, y0, r0 = stellen[i - 1][:3]
        x1, y1, r1 = stellen[i][:3]
        ds = math.hypot(x1 - x0, y1 - y0)
        dr = (r1 - r0 + math.pi) % (2 * math.pi) - math.pi
        radien.append(ds / dr if abs(dr) > 1e-9 else math.inf)
    ergebnis = []
    for i in range(n):
        kleinster, weg, k = math.inf, 0.0, i
        while weg <= laenge + 1e-9 and k > i - n:
            r = radien[k % n]
            if abs(r) < abs(kleinster):
                kleinster = r
            x0, y0 = stellen[(k - 1) % n][:2]
            x1, y1 = stellen[k % n][:2]
            weg += math.hypot(x1 - x0, y1 - y0)
            k -= 1
        ergebnis.append(kleinster)
    return ergebnis


def _weich(stellen, versaetze, d_spur):
    """Die Versätze je Stelle so geglättet, dass die Spur höchstens um SPUR_SCHRAEG seitlich
    ausweicht – nur in die sichere Richtung (weiter weg von d_spur), nie zurück: Sonst spränge die
    Klinge am Anfang einer Kurve quer (am Rechteck R 10 um 19°)."""
    n = len(versaetze)
    s = [d - d_spur for d in versaetze]
    k = math.tan(SPUR_SCHRAEG)
    wege = _weg(stellen)
    for _ in range(4 * n):
        geaendert = False
        for i in list(range(n)) + list(range(n - 1, -1, -1)):
            for j, weg in ((i - 1, wege[i]), ((i + 1) % n, wege[(i + 1) % n])):
                nachbar = s[j % n]
                grenze = abs(nachbar) - k * weg
                if grenze > abs(s[i]) + 1e-12 and (s[i] == 0 or (s[i] > 0) == (nachbar > 0)):
                    s[i] = math.copysign(grenze, nachbar)
                    geaendert = True
        if not geaendert:
            break
    return [d_spur + v for v in s]


def _versatz_erlaubt(nut, breite, laenge, radius, schritt=SCHRITT):
    """So weit darf die Spur in einer Kurve mit `radius` (der Mittellinie) zur Außenwand hin liegen,
    damit die Klinge dort (_ueberstand, außen) vor ihr bleibt – −inf: nirgends."""
    r = abs(radius)
    if not math.isfinite(r):
        return math.inf
    wand = r + nut.breite / 2.0 - SPIEL

    def luft(d):
        aussen, _innen = _ueberstand(r + d, breite, laenge, schritt, r)
        return wand - (r + d + breite / 2.0) - aussen

    unten, oben = -nut.breite / 2.0, nut.breite / 2.0
    if luft(unten) < 0:
        return -math.inf
    if luft(oben) >= 0:
        return oben
    for _ in range(40):
        mitte = (unten + oben) / 2.0
        if luft(mitte) >= 0:
            unten = mitte
        else:
            oben = mitte
    return unten


def _spur_lage(stellen, versaetze):
    """[(x, y, Richtung)] der Spur: die Stellen um ihren Versatz quer verschoben."""
    return [
        (x + d * -math.sin(richtung), y + d * math.cos(richtung), richtung)
        for (x, y, richtung, *_n), d in zip(stellen, versaetze, strict=True)
    ]


def _spur_planen(nut, w, stellen, d_spur, kruemmung, mehrere):
    """[(x, y, Richtung)] einer Spur, die Klinge an jeder Stelle ganz im Grund (_klinge_luft): In
    der Kurve rückt die Spur zur Mitte (am Rechteck R 10 mit der Klinge 2,6 × 2 sonst 0,11 mm² über
    die Wand), wo es danach noch eng ist, weiter – bei der Ellipse mit zwei Spuren lag die Klinge
    sonst 0,015 mm in der Wand. ValueError, wenn es nicht geht."""
    reihe = [d_spur] * len(stellen)
    if mehrere:
        for i, radius in enumerate(kruemmung):
            erlaubt = _versatz_erlaubt(nut, w.breite, w.laenge, radius, w.schritt)
            if radius > 0:  # Linkskurve: die Außenwand liegt rechts (−)
                reihe[i] = max(reihe[i], -erlaubt)
            elif radius < 0:
                reihe[i] = min(reihe[i], erlaubt)
        reihe = _weich(stellen, reihe, d_spur)
    for _versuch in range(12):
        lage = _spur_lage(stellen, reihe)
        luft, seite = _klinge_luft(nut, lage, w.breite, w.laenge)
        zu_nah = [i for i in range(len(lage)) if luft[i] < -1e-4]
        if not zu_nah:
            return lage
        if not mehrere:
            break
        n = len(reihe)
        for i in zu_nah:  # weg von der Wand, an der es eng ist – auch der Punkt davor (er dreht)
            schub = -seite[i] * (-luft[i] + 0.002)
            for k in (i, (i - 1) % n):
                reihe[k] += schub
        reihe = _weich(stellen, reihe, d_spur)
    i = min(range(len(lage)), key=lambda k: luft[k])
    raise ValueError(
        tr("hn.grund.klinge_wand", x=_mm(lage[i][0]), y=_mm(lage[i][1]), mm=_mm(-luft[i]),
           laenge=_mm(w.laenge))
    )  # fmt: skip


def planen(nut, werte):
    """Die Hobelbahn (Hobelbahn) für die Nut `nut` (Hobelnut) mit den Werten `werte`
    (Hobelwerte). ValueError mit einem Satz, wenn es nicht geht.

    Der Ablauf: Über dem Anfang (_anfang: auf dem längsten geraden Stück, sonst an der flachsten
    Stelle) dreht die Spindel in Richtung, im Eilgang hinab bis über die Nut, im Eintauchvorschub
    senkrecht nur bis UEBER_MATERIAL über das Material (Grund + Rest), dann in Fahrtrichtung flach
    bis auf das Material und von dort mit stetigem Gefälle durch die Nut – je Umlauf um die
    Zustellung (Zustellung ÷ Länge des Umlaufs je mm), bis auf das Aufmaß; dort ein ebener Umlauf
    und die Leerumläufe. Das Material: `rest` über dem Grund – aus dem Vollen die Oberkante des
    Teils oder Rohteils über der Nut, vorgefräst der Rest.

    Ist die Klinge schmaler als die Nut, fährt sie mehrere Spuren, jede eine eigene schmale Nut von
    oben bis unten (Manuel, 2026-11-14: „das man die schmale Nut fährt auf der einen Seite und dann
    wieder oben anfängt und dann an der anderen Seite entlang die selbe Nut fährt“): Spur 1 an der
    einen Wand ganz hinab, dann hinauf auf UEBER_MATERIAL über alles, zurück an den Anfang der
    Geraden und die nächste Spur wie beim ersten Mal (ohne Gerade über dem Teil, weil die Spindel
    dreht); sie überlappen um SPUR_UEBERLAPP der Klingenbreite."""
    w = werte
    grund = klinge_pruefen(nut, w.breite, w.laenge, w.schritt)
    if grund:
        raise ValueError(grund)
    if w.zustellung <= 0 or w.vorschub <= 0:
        raise ValueError(tr("hn.fehler.werte"))
    z_ende = nut.z_boden + max(w.aufmass, 0.0)
    z_oben_material = nut.z_boden + max(w.rest, 0.0)  # aus dem Vollen auch über der Nut (Rohteil)
    if z_oben_material < z_ende:
        z_oben_material = z_ende
    stellen = _stellen_je_stueck(nut, max(w.schritt, 0.05))
    c, m, gerade = _anfang(nut, stellen)
    stellen = stellen[c:] + stellen[:c]  # die Stelle, an der die Klinge ins Material kommt, zuerst
    n = len(stellen)
    hoch = max(nut.z_oben, z_oben_material + UEBER_MATERIAL) + w.sicherheit
    spuren = _spuren(nut, w.breite)
    kruemmung = _kruemmung(stellen, w.laenge) if len(spuren) > 1 else None
    reihen = [_spur_planen(nut, w, stellen, d, kruemmung, len(spuren) > 1) for d in spuren]
    punkte, winkel_, spur_, stelle_ = [], [], [], []
    letzter_winkel = None

    def winkel_bei(richtung):
        """Der Spindelwinkel (Grad) zur Fahrtrichtung, fortlaufend – ohne Sprung um 360°."""
        nonlocal letzter_winkel
        wert = math.degrees(richtung) + w.versatz
        if letzter_winkel is not None:
            wert += 360.0 * round((letzter_winkel - wert) / 360.0)
        letzter_winkel = wert
        return wert

    def setze(punkt, winkel, spur=None, stelle=None):
        notiz = None if winkel is None else f"{SPINDEL} {winkel:.3f}"
        punkte.append(bn.Punkt(punkt[0], punkt[1], punkt[2], punkt[3], punkt[4], None, 1.0, notiz))
        winkel_.append(winkel)
        spur_.append(spur)
        stelle_.append(stelle)

    tiefe = z_oben_material - z_ende
    umlaeufe = max(1, int(math.ceil(tiefe / w.zustellung - 1e-9))) if tiefe > 1e-9 else 0
    gesamt = umlaeufe + 1 + max(int(w.leerumlaeufe), 0)
    wege = []  # je Spur: der Weg vom Anfang (Stelle 0) bis zur Stelle i, [n] = ein Umlauf
    for reihe in reihen:
        weg, summe = [0.0], 0.0
        for i in range(1, n + 1):
            summe += math.hypot(
                reihe[i % n][0] - reihe[i - 1][0], reihe[i % n][1] - reihe[i - 1][1]
            )
            weg.append(summe)
        wege.append(weg)

    def z_bei(j, u):
        """z der Spur j nach dem Weg u ab dem Anfang: das stetige Gefälle, nicht unter z_ende."""
        if tiefe <= 1e-9:
            return z_ende
        return max(z_ende, z_oben_material - w.zustellung * u / wege[j][n])

    lage = None  # wo die Klinge gerade ist (x, y, z) – None: oben
    for j, reihe in enumerate(reihen):
        for k in range(1, gesamt + 1):
            weg = wege[j]
            umlauf = weg[n]
            luft_weg = umlauf - weg[n - m]
            if k == 1:
                # Einfahren: senkrecht bis UEBER_MATERIAL über das Material am Anfang der Rampe,
                # dann in Fahrtrichtung flach bis auf das Material an Stelle 0.
                x0, y0, r0 = reihe[(n - m) % n]
                material = z_oben_material if k == 1 else z_bei(j, (k - 1) * umlauf - luft_weg)
                oben = material + UEBER_MATERIAL
                if lage is not None and gerade:
                    ueber_allem = z_oben_material + UEBER_MATERIAL
                    setze((True, lage[0], lage[1], ueber_allem, False), None)
                    # in der Nut zurück an den Anfang der Geraden – über allem, die Spindel steht
                    setze((False, x0, y0, ueber_allem, False), winkel_bei(r0))
                    if oben < ueber_allem - 1e-9:
                        setze((False, x0, y0, oben, True), winkel_bei(r0))
                else:
                    if lage is not None:
                        setze((True, lage[0], lage[1], w.sicher, False), None)
                    a0 = winkel_bei(r0)
                    setze((True, x0, y0, w.sicher, False), a0)
                    setze((True, x0, y0, hoch, False), None)
                    setze((False, x0, y0, oben, True), a0)
                z_anfang = z_bei(j, (k - 1) * umlauf)
                for i in range(n - m + 1, n + 1):
                    x, y, richtung = reihe[i % n]
                    t = (weg[i] - weg[n - m]) / luft_weg if luft_weg > 1e-12 else 1.0
                    setze((False, x, y, oben + (z_anfang - oben) * t, False), winkel_bei(richtung))
            for i in range(1, n + 1):
                x, y, richtung = reihe[i % n]
                z = z_bei(j, (k - 1) * umlauf + weg[i])
                setze((False, x, y, z, False), winkel_bei(richtung), j, i % n)
            lage = (reihe[0][0], reihe[0][1], z_bei(j, k * umlauf))
    setze((True, lage[0], lage[1], w.sicher, False), None)  # senkrecht hinaus
    laenge = bn.laenge(punkte)
    zeit = bn.zeit(punkte, w.vorschub, w.eintauchen or None)
    return Hobelbahn(punkte, winkel_, len(spuren), gesamt, laenge, zeit, spur_, stelle_, gerade)
