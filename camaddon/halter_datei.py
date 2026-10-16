# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Kontur eines Halters aus einer CAD-Datei (W-022 Punkt 3).

Manuel, 2026-10-16: „wenn du die stl oder step dateien nur zum messen nimmst und in freecad die
halter nachbaust ... ist das effektv nichts dagegen zu sagen !“ Ein Halter ist ein Drehkörper:
Hier wird seine Hüllkontur gemessen – je Stelle längs der Drehachse der größte Radius – und in
Abschnitte (Länge, Ø oben, Ø unten) gefasst, wie halter.Halter sie hat. Die Datei selbst bleibt,
wo sie ist; heraus kommen nur Längen und Durchmesser.

Die Drehachse ist die längste Seite der Box um das Modell, durch die Mitte der Box quer dazu
(Kataloge legen die Halter auf eine Achse). Gemessen wird am Dreiecksnetz: je Kante, die eine
Stelle kreuzt, der Punkt auf ihr – sein Abstand zur Achse. Der größte je Stelle ist die Hülle
(eine Kante des Netzes liegt innen an der Fläche, um höchstens die Toleranz des Netzes).

Läuft ohne Oberfläche.
"""

import math
import os

import numpy as np

SCHRITT = 0.1  # mm längs der Achse
TOLERANZ = 0.1  # mm – so genau folgen die Abschnitte der Kontur (das Netz streut um 0,05)
STUFE_STEIL = 10.0  # mm quer je mm längs: steiler ist eine Stufe, kein Kegel
NETZ_TOLERANZ = 0.02  # mm – so fein wird eine STEP-Datei in Dreiecke zerlegt
NETZ_ENDUNGEN = (".stl", ".obj", ".ply", ".off", ".ast", ".bms")


def netz(pfad):
    """(Punkte (n, 3), Dreiecke (m, 3)) des Modells in `pfad`: STL und andere Netze, wie sie
    sind; STEP, IGES und BREP in Dreiecke zerlegt (NETZ_TOLERANZ)."""
    if os.path.splitext(pfad)[1].lower() in NETZ_ENDUNGEN:
        import Mesh

        punkte, dreiecke = Mesh.Mesh(pfad).Topology
    else:
        import Part

        form = Part.Shape()
        form.read(pfad)
        punkte, dreiecke = form.tessellate(NETZ_TOLERANZ)
    punkte = np.array([(p.x, p.y, p.z) for p in punkte], dtype=float).reshape(-1, 3)
    return punkte, np.array(dreiecke, dtype=np.int64).reshape(-1, 3)


def achse(punkte):
    """(Index der Achse 0/1/2, Mitte quer dazu (2,), Unrundheit): die längste Seite der Box,
    durch ihre Mitte. Unrundheit: wie verschieden die beiden Seiten quer sind (Anteil) – ein
    Drehkörper hat 0."""
    unten, oben = punkte.min(axis=0), punkte.max(axis=0)
    seiten = oben - unten
    i = int(np.argmax(seiten))
    quer = [k for k in range(3) if k != i]
    mitte = (unten[quer] + oben[quer]) / 2
    a, b = seiten[quer]
    return i, mitte, abs(a - b) / max(a, b, 1e-9)


def kontur(punkte, dreiecke, schritt=SCHRITT):
    """(Stellen längs der Achse ab dem einen Ende, größter Radius je Stelle, Index der Achse)."""
    i, mitte, _unrund = achse(punkte)
    quer = [k for k in range(3) if k != i]
    z = punkte[:, i] - punkte[:, i].min()
    q = punkte[:, quer] - mitte
    kanten = np.sort(
        np.concatenate([dreiecke[:, [0, 1]], dreiecke[:, [1, 2]], dreiecke[:, [2, 0]]])
    )
    kanten = np.unique(kanten, axis=0)
    a, b = kanten[:, 0], kanten[:, 1]
    lang = float(z.max())
    stellen = np.arange(0.0, lang + schritt / 2, schritt)
    r = np.zeros(len(stellen))
    # Die Ecken selbst …
    np.maximum.at(r, np.clip(np.rint(z / schritt).astype(np.int64), 0, len(r) - 1), np.hypot(*q.T))
    # … und je Kante jede Stelle, die sie kreuzt.
    za, zb = z[a], z[b]
    lo, hi = np.minimum(za, zb), np.maximum(za, zb)
    i0 = np.ceil(lo / schritt - 1e-9).astype(np.int64)
    i1 = np.floor(hi / schritt + 1e-9).astype(np.int64)
    zaehl = np.maximum(i1 - i0 + 1, 0)
    zaehl[hi - lo < 1e-12] = 0
    kante = np.repeat(np.arange(len(kanten)), zaehl)
    if len(kante):
        anfang = np.repeat(np.cumsum(zaehl) - zaehl, zaehl)
        stelle = i0[kante] + np.arange(len(kante)) - anfang
        t = (stelle * schritt - za[kante]) / (zb[kante] - za[kante])
        p = q[a[kante]] + t[:, None] * (q[b[kante]] - q[a[kante]])
        np.maximum.at(r, np.clip(stelle, 0, len(r) - 1), np.hypot(p[:, 0], p[:, 1]))
    return stellen, r, i


def vereinfacht(stellen, r, toleranz=TOLERANZ):
    """Die Ecken der Kontur (Indizes): so wenige, dass keine Stelle weiter als `toleranz` von
    der Linie zwischen ihnen liegt (Douglas-Peucker, quer gemessen)."""
    behalten = np.zeros(len(r), dtype=bool)
    behalten[[0, -1]] = True
    stapel = [(0, len(r) - 1)]
    while stapel:
        von, bis = stapel.pop()
        if bis - von < 2:
            continue
        mitte = np.arange(von + 1, bis)
        anteil = (stellen[mitte] - stellen[von]) / (stellen[bis] - stellen[von])
        abweichung = np.abs(r[mitte] - (r[von] + anteil * (r[bis] - r[von])))
        k = int(np.argmax(abweichung))
        if abweichung[k] > toleranz:
            behalten[mitte[k]] = True
            stapel += [(von, mitte[k]), (mitte[k], bis)]
    return np.flatnonzero(behalten)


def abschnitte(stellen, r, von, bis, toleranz=TOLERANZ):
    """Die Kontur von der Stelle `von` (die Spindelnase) bis `bis` (die Nase des Halters) als
    Abschnitte [(Länge, Ø oben, Ø unten)], gerundet auf 0,01 mm; `von` > `bis`: von hinten
    gelesen."""
    if von > bis:
        stellen, r = stellen[-1] - stellen[::-1], r[::-1]
        von, bis = stellen[-1] - von, stellen[-1] - bis
    drin = (stellen >= von - 1e-9) & (stellen <= bis + 1e-9)
    s, rr = stellen[drin], r[drin]
    if len(s) < 2:
        return []
    ecken = vereinfacht(s, rr, toleranz)
    stuecke = [[s[k0], s[k1], rr[k0], rr[k1]] for k0, k1 in zip(ecken, ecken[1:], strict=False)]
    # Eine Stufe (Flansch, Bund, Mutter) ist im Raster ein steiler Kegel über einen Schritt: Sie
    # wird eine Stufe, wo der größere Ø endet – an einer Stufe gilt er (Halter.radius_bei); so
    # liest man von beiden Seiten dieselben Längen.
    schritt = float(np.min(np.diff(s))) if len(s) > 1 else SCHRITT
    stufe = [
        k
        for k, (s0, s1, r0, r1) in enumerate(stuecke)
        if len(stuecke) > 1 and s1 - s0 <= 1.5 * schritt and abs(r1 - r0) > STUFE_STEIL * (s1 - s0)
    ]
    for k in reversed(stufe):
        s0, s1, r0, r1 = stuecke[k]
        if k == 0:  # am Anfang (die Spindelnase direkt vor dem Flansch): der nächste ab dort
            stuecke[1][0] = s0
        elif k == len(stuecke) - 1:  # am Ende: der davor bis dort
            stuecke[k - 1][1] = s1
        elif r0 > r1:
            stuecke[k - 1][1], stuecke[k + 1][0] = s0, s0
        else:
            stuecke[k - 1][1], stuecke[k + 1][0] = s1, s1
        del stuecke[k]
    # Zwei Zylinder gleich dick hintereinander (das Netz streut dazwischen): einer.
    zusammen = []
    for stueck in stuecke:
        davor = zusammen[-1] if zusammen else None
        if (
            davor is not None
            and abs(davor[2] - davor[3]) <= toleranz
            and abs(stueck[2] - stueck[3]) <= toleranz
            and abs(davor[3] - stueck[2]) <= toleranz
        ):
            davor[1] = stueck[1]
        else:
            zusammen.append(list(stueck))
    return [
        (round(float(s1 - s0), 2), round(float(2 * r0), 2), round(float(2 * r1), 2))
        for s0, s1, r0, r1 in zusammen
    ]


# Die Spindelseite: Dort steckt der Kegel (SK, BT, CAT: 7:24; HSK: 1:10) – ein gerader Kegel,
# lang genug, und gleich dahinter (KEGEL_BIS_FLANSCH) der Flansch, das Dickste. Auf der Seite des
# Werkzeugs liegt vor dem Flansch der Körper (beim Schrumpffutter auch ein Kegel, aber weit weg).
KEGEL_MIN = 20.0  # mm
KEGEL_ABWEICHUNG = 0.15  # mm – so weit darf die Kontur von der Geraden des Kegels abweichen
KEGEL_STEIGUNG = (0.02, 0.25)  # Radius je mm längs
KEGEL_BIS_FLANSCH = 6.0  # mm
FLANSCH_ANTEIL = 0.97  # so dick wie das Dickste: der Flansch


def _kegel_ende(stellen, r):
    """Wie weit ab der Stelle 0 die Kontur ein gerader Kegel ist (mm; 0: keiner) – die Gerade
    durch die ersten Millimeter (ohne die Fase am Ende)."""
    schritt = float(stellen[1] - stellen[0]) if len(stellen) > 1 else SCHRITT
    von, bis = int(round(1.0 / schritt)), int(round(10.0 / schritt))
    if len(r) <= bis:
        return 0.0
    steigung, achsabschnitt = np.polyfit(stellen[von:bis], r[von:bis], 1)
    if not KEGEL_STEIGUNG[0] <= steigung <= KEGEL_STEIGUNG[1]:
        return 0.0
    weg = np.abs(r - (achsabschnitt + steigung * stellen)) > KEGEL_ABWEICHUNG
    weg[:von] = False
    ende = int(np.argmax(weg)) if weg.any() else len(r)
    return float(stellen[max(ende - 1, 0)])


def spindelseite(stellen, r):
    """(Spindelnase in mm ab Stelle 0, liegt die Spindel bei 0?) – oder None, wenn keine Seite
    wie eine Aufnahme aussieht. Die Spindelnase ist das Ende des Kegels."""
    dick = FLANSCH_ANTEIL * float(r.max())
    lang = float(stellen[-1])
    gefunden = []
    for vorn in (True, False):
        s_, r_ = (stellen, r) if vorn else (lang - stellen[::-1], r[::-1])
        kegel = _kegel_ende(s_, r_)
        flansch = float(s_[int(np.argmax(r_ >= dick))])
        if kegel >= KEGEL_MIN and 0 <= flansch - kegel <= KEGEL_BIS_FLANSCH:
            gefunden.append((kegel if vorn else lang - kegel, vorn))
    return gefunden[0] if len(gefunden) == 1 else None


def stufen(stellen, r, ab=0.5):
    """Die Stellen, an denen der Radius springt (mehr als `ab` mm auf einem Schritt) – Kanten
    von Flansch, Bund und Mutter; zum Finden der Spindelnase."""
    sprung = np.flatnonzero(np.abs(np.diff(r)) > ab)
    return [(float(stellen[k]), float(r[k]), float(r[k + 1])) for k in sprung]


def halter_aus_datei(pfad, aufnahme=""):
    """(Halter, Spindelseite erkannt?) aus der CAD-Datei `pfad`: die Kontur ab der Spindelnase
    (spindelseite) bis zur Nase des Halters, an der Aufnahme `aufnahme`, benannt nach der Datei.
    Ohne erkannte Spindelseite vom einen Ende der Datei an – dann gehören die Abschnitte bis zur
    Spindelnase weg. Die Spanntiefe kennt die Datei nicht. ValueError, wenn nichts darin ist."""
    from . import halter as hl
    from .sprache import tr

    punkte, dreiecke = netz(pfad)
    if len(punkte) == 0 or len(dreiecke) == 0:
        raise ValueError(tr("halter.datei_leer"))
    stellen, r, _i = kontur(punkte, dreiecke)
    seite = spindelseite(stellen, r)
    nase, vorn = seite if seite is not None else (0.0, True)
    teile = abschnitte(stellen, r, nase, float(stellen[-1]) if vorn else 0.0)
    datei = os.path.basename(pfad)
    halter = hl.Halter(
        name=os.path.splitext(datei)[0],
        bezeichnung=tr("halter.aus_datei", datei=datei),
        aufnahme=aufnahme,
        abschnitte=[hl.Abschnitt(*teil) for teil in teile if teil[0] > 0],
    )
    return halter, seite is not None


def masse(pfad):
    """Für die Werkstatt und die Prüfung: (Stellen, Radien, Unrundheit, Länge) des Modells."""
    punkte, dreiecke = netz(pfad)
    _i, _mitte, unrund = achse(punkte)
    stellen, r, _achse = kontur(punkte, dreiecke)
    return stellen, r, unrund, float(stellen[-1]) if len(stellen) else 0.0


def kreisfehler(radius, toleranz=NETZ_TOLERANZ):
    """Wie weit eine Sehne des Netzes höchstens innen am Kreis liegt (mm) – für die Prüfung."""
    if radius <= toleranz:
        return radius
    n = math.ceil(math.pi / math.acos(1 - toleranz / radius))
    return radius * (1 - math.cos(math.pi / n))
