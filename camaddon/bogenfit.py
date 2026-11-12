# SPDX-License-Identifier: LGPL-2.1-or-later
"""Kurze Geraden zu Bögen und längeren Geraden fassen – fürs Programm (postprozessor, Haken
„boegen“).

Runde Bahnen kommen aus den Rastern und aus FreeCADs Adaptiv-Kern als Ketten kurzer Geraden: Am
Testteil schrieb das Räumen 19 623 Sätze von im Mittel 0,5 mm (931 kB), das 3D-Schlichten 3 040
von 0,25 mm (gemessen 2026-11-12). Eine Steuerung mit kleinem Programmspeicher nimmt das nicht,
über DNC tröpfelt es, und an jeder Ecke zwischen zwei Sätzen rechnet sie neu. `zusammenfassen`
legt in eine Kette so wenige Geraden und Kreisbögen (G2/G3 in der Ebene XY), dass die neue Bahn
höchstens `toleranz` neben der alten liegt – am Testteil mit 0,005 mm 77 % weniger Sätze im
Räumen, 82 % im 3D-Schlichten.

- Eine **Gerade** ersetzt eine Folge, wenn jeder Punkt dazwischen höchstens `toleranz` neben ihr
  liegt (im Raum) und die Kette nicht zurückläuft.
- Ein **Bogen** ersetzt mindestens MIN_STUECKE Geraden auf gleicher Höhe: Anfang und Ende sind
  Punkte der Kette (beide gleich weit von der Mitte – die Steuerung prüft das), die Mitte liegt
  auf ihrer Mittelsenkrechten, so dass die Punkte dazwischen im Mittel auf dem Kreis liegen. Er
  gilt, wenn jede alte Gerade höchstens `toleranz` vom Kreis abweicht (ihre Enden und die Stelle,
  an der sie der Mitte am nächsten kommt), die Kette nur in einer Richtung um die Mitte läuft und
  höchstens WEIT dreht.
- Gesucht wird je Stück das längste, das passt (in Sprüngen, dann halbiert); ist ein Bogen länger
  als die Gerade, gewinnt er.

`befehle_gefasst` wendet das auf die Befehle einer Operation an: Ketten von G1 mit gleichem
Vorschub, nur X, Y, Z. Alles andere bleibt, wie es ist.

Läuft ohne Oberfläche; numpy gehört zu FreeCAD.
"""

import math

import numpy as np

TOLERANZ = 0.005  # mm – so weit darf die gefasste Bahn neben der alten liegen
R_MIN = 0.2  # mm – kleinere Bögen bleiben Geraden
R_MAX = 1000.0  # mm – flachere sind Geraden
WEIT = 1.5 * math.pi  # so weit dreht ein Bogen höchstens (ein Vollkreis hätte kein Ende)
MIN_STUECKE = 3  # ein Bogen ersetzt mindestens so viele Geraden
SEHNE_MIN = 0.1  # mm – kürzer wird kein Bogen (gerundet stünden Anfang und Ende gleich)
EBEN = 1e-6  # mm – so gleich müssen die Höhen eines Bogens sein
STELLEN = 3  # Nachkommastellen im Programm (postprozessor.STELLEN)
_GLEICH_F = 1e-9
GERADE = ("G1", "G01")
FAHREN = ("G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03")
# Mit diesen Befehlen oder Adressen fasst befehle_gefasst nichts: inkrementell, eine andere
# Ebene, Vorschub in G93, Rundachsen.
NICHT_MIT = ("G91", "G18", "G19", "G93")
NICHT_ADRESSEN = ("A", "B", "C", "U", "V", "W")


def _gerade_passt(p, i, j, tol):
    if j <= i + 1:
        return True
    a, b = p[i], p[j]
    d = b - a
    l2 = float(d @ d)
    q = p[i + 1 : j] - a
    if l2 < 1e-18:
        return bool((np.einsum("ij,ij->i", q, q) <= tol * tol).all())
    t = q @ d / l2
    if t[0] < -1e-9 or t[-1] > 1.0 + 1e-9 or (np.diff(t) < -1e-9).any():
        return False  # die Kette läuft zurück
    lot = q - np.outer(t, d)
    return bool((np.einsum("ij,ij->i", lot, lot) <= tol * tol).all())


def _kreis(a, m, b):
    """Die Mitte des Kreises durch drei Punkte (x, y) – None, wenn sie auf einer Geraden liegen."""
    ax, ay = a
    bx, by = m
    cx, cy = b
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return None
    a2, b2, c2 = ax * ax + ay * ay, bx * bx + by * by, cx * cx + cy * cy
    return (
        (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / d,
        (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d,
    )


def _bogen_passt(p, i, j, tol):
    """(mx, my, uhrzeiger) eines Bogens von p[i] nach p[j] auf gleicher Höhe, von dem keine der
    alten Geraden mehr als `tol` abweicht – sonst None."""
    if j - i < MIN_STUECKE:
        return None
    z = p[i : j + 1, 2]
    if float(np.abs(z - z[0]).max()) > EBEN:
        return None
    q = p[i : j + 1, :2]
    a, b = q[0], q[-1]
    sehne = float(np.hypot(*(b - a)))
    if sehne < SEHNE_MIN:
        return None
    mitte = _kreis(a, q[len(q) // 2], b)
    if mitte is None:
        return None
    # Die Mitte auf der Mittelsenkrechten von a–b so schieben, dass die Abweichung der Punkte
    # im Mittel verschwindet (sie ist fast linear im Schub: drei Schritte genügen).
    m0 = 0.5 * (a + b)
    n = np.array([-(b - a)[1], (b - a)[0]]) / sehne
    t = float((np.array(mitte) - m0) @ n)

    def abweichung(t_):
        c_ = m0 + t_ * n
        return np.hypot(q[:, 0] - c_[0], q[:, 1] - c_[1]) - math.hypot(*(a - c_))

    for _ in range(3):
        d0 = abweichung(t)
        dt = 1e-3 * max(1.0, abs(t))
        g = (abweichung(t + dt) - d0) / dt
        nenner = float(g @ g)
        if nenner < 1e-18:
            break
        t -= float(g @ d0) / nenner
    c = m0 + t * n
    r = math.hypot(*(a - c))
    if not (R_MIN <= r <= R_MAX):
        return None
    aussen = np.hypot(q[:, 0] - c[0], q[:, 1] - c[1])
    if float(np.abs(aussen - r).max()) > tol:
        return None
    # Jede alte Gerade: wo sie der Mitte am nächsten kommt (ihr Fußpunkt, auf sie begrenzt).
    von, d = q[:-1], q[1:] - q[:-1]
    l2 = np.maximum(np.einsum("ij,ij->i", d, d), 1e-18)
    s = np.clip(np.einsum("ij,ij->i", c - von, d) / l2, 0.0, 1.0)
    fuss = von + d * s[:, None]
    if float(np.abs(np.hypot(fuss[:, 0] - c[0], fuss[:, 1] - c[1]) - r).max()) > tol:
        return None
    winkel = np.unwrap(np.arctan2(q[:, 1] - c[1], q[:, 0] - c[0]))
    gesamt = float(winkel[-1] - winkel[0])
    if abs(gesamt) > WEIT or abs(gesamt) < 1e-9:
        return None
    if (np.diff(winkel) * math.copysign(1.0, gesamt) < -1e-9).any():
        return None  # dreht zwischendurch zurück
    return float(c[0]), float(c[1]), gesamt < 0.0


def _weitest(passt, i, n):
    """Das größte j > i, für das passt(j) gilt – in Sprüngen gesucht, dann halbiert; i + 1, wenn
    schon i + 2 nicht passt."""
    gut, schritt = i + 1, 1
    while True:
        j = min(gut + schritt, n - 1)
        if j == gut:
            return gut
        if not passt(j):
            schlecht = j
            break
        gut = j
        schritt *= 2
    while schlecht - gut > 1:
        mitte = (gut + schlecht) // 2
        if passt(mitte):
            gut = mitte
        else:
            schlecht = mitte
    return gut


def zusammenfassen(punkte, toleranz=TOLERANZ):
    """[(Index, Bogen)]: die Punkte der Kette `punkte` ([(x, y, z)], der erste ist der Start), die
    bleiben – `Index` in `punkte`, `Bogen` None (eine Gerade dorthin) oder (mx, my, uhrzeiger).
    Der Start steht nicht in der Liste, der letzte Punkt immer."""
    return list(stuecke(punkte, toleranz))


def stuecke(punkte, toleranz=TOLERANZ):
    """zusammenfassen Stück für Stück (ein Generator), vom Anfang der Kette her."""
    p = np.asarray(punkte, dtype=float)
    n = len(p)
    i = 0
    while i < n - 1:
        j_gerade = _weitest(lambda j, i=i: _gerade_passt(p, i, j, toleranz), i, n)
        boegen = {}

        def bogen_passt(j, i=i, boegen=boegen):
            if j - i < MIN_STUECKE:
                return True  # noch zu kurz für einen Bogen: weiter suchen
            bogen = _bogen_passt(p, i, j, toleranz)
            if bogen is not None:
                boegen[j] = bogen
            return bogen is not None

        j_bogen = _weitest(bogen_passt, i, n)
        if j_bogen > j_gerade and j_bogen in boegen:
            yield j_bogen, boegen[j_bogen]
            i = j_bogen
        else:
            yield j_gerade, None
            i = j_gerade


def mitte_gerundet(start, ende, mitte, stellen=STELLEN):
    """(I, J) – der Weg vom Anfang zur Mitte eines Bogens, so auf `stellen` gerundet, dass Anfang
    und Ende, selbst gerundet, gleich weit von ihr liegen. Die Steuerung liest gerundete Zahlen
    und prüft genau das (Siemens: Alarm „Kreisendpunktfehler“); einzeln gerundet lägen die
    Abstände bis 0,003 mm auseinander. Die Mitte kommt dazu erst auf die Mittelsenkrechte der
    gerundeten Enden, dann gewinnt von den neun Nachbarn im Raster der beste."""
    q = 10.0 ** (-stellen)
    xs, ys = round(start[0], stellen), round(start[1], stellen)
    xe, ye = round(ende[0], stellen), round(ende[1], stellen)
    dx, dy = xe - xs, ye - ys
    sehne = math.hypot(dx, dy)
    mx, my = mitte
    if sehne > 1e-12:
        nx, ny = -dy / sehne, dx / sehne
        hx, hy = 0.5 * (xs + xe), 0.5 * (ys + ye)
        t = (mx - hx) * nx + (my - hy) * ny
        mx, my = hx + t * nx, hy + t * ny
    i0, j0 = round(mx - xs, stellen), round(my - ys, stellen)
    beste = None
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            i, j = round(i0 + di * q, stellen), round(j0 + dj * q, stellen)
            fehler = abs(math.hypot(i, j) - math.hypot(dx - i, dy - j))
            # Bei gleichem Fehler die Mitte, die am wenigsten verschoben ist.
            rang = (round(fehler, stellen + 3), abs(di) + abs(dj))
            if beste is None or rang < beste[0]:
                beste = (rang, i, j)
    return beste[1], beste[2]


def befehle_gefasst(befehle, toleranz=TOLERANZ, stellen=STELLEN):
    """Die Befehle [(Name, {Adresse: Wert})] einer Operation, jede Kette von G1 mit gleichem
    Vorschub (nur X, Y, Z, F; der Ort davor bekannt) in wenige G1/G2/G3 gefasst (zusammenfassen).
    Unverändert, wenn die Operation inkrementell fährt, in einer anderen Ebene als XY, in G93 oder
    mit Rundachsen – und jede Kette, bei der nichts zu gewinnen ist. `stellen`: so viele
    Nachkommastellen schreibt das Programm (mitte_gerundet)."""
    return list(gefasst(befehle, toleranz, stellen))


def gefasst(befehle, toleranz=TOLERANZ, stellen=STELLEN):
    """befehle_gefasst Stück für Stück (ein Generator): Wer nur den Anfang braucht – die Vorschau
    im Fenster –, rechnet nur den Anfang."""
    for name, werte in befehle:
        if name.upper() in NICHT_MIT or any(a in werte for a in NICHT_ADRESSEN):
            yield from befehle
            return
    ort = {"X": None, "Y": None, "Z": None}
    f_gilt = None
    kette = []  # die Befehle der laufenden Kette
    punkte = []  # ihr Start und je Befehl sein Ziel
    f_kette = None

    def geschlossen():
        if len(kette) < MIN_STUECKE:
            yield from kette
            return
        vorher = 0
        for index, bogen in stuecke(punkte, toleranz):
            if bogen is None and index == vorher + 1:
                yield kette[vorher]  # nichts gefasst: der Satz, wie er war
            else:
                x, y, z = punkte[index]
                werte = {"X": x, "Y": y, "Z": z}
                name = "G1"
                if bogen is not None:
                    mx, my, uhrzeiger = bogen
                    name = "G2" if uhrzeiger else "G3"
                    werte["I"], werte["J"] = mitte_gerundet(
                        punkte[vorher], punkte[index], (mx, my), stellen
                    )
                if f_kette is not None:
                    werte["F"] = f_kette
                yield name, werte
            vorher = index

    for name, werte in befehle:
        gross = name.upper()
        f = werte.get("F", f_gilt) if gross in FAHREN else f_gilt
        ziel = {a: (float(werte[a]) if a in werte else ort[a]) for a in ort}
        passt = (
            gross in GERADE
            and set(werte) <= {"X", "Y", "Z", "F"}
            and None not in ort.values()
            and (f is None or float(f) > 0.0)
            and any(abs(ziel[a] - ort[a]) > 1e-9 for a in ort)
        )
        if kette and not (passt and _gleich(f, f_kette)):
            yield from geschlossen()
            kette, punkte = [], []
        if passt:
            if not kette:
                punkte = [(ort["X"], ort["Y"], ort["Z"])]
                f_kette = f
            kette.append((name, werte))
            punkte.append((ziel["X"], ziel["Y"], ziel["Z"]))
        else:
            yield name, werte
        if gross in FAHREN:
            ort = ziel
            f_gilt = f
        elif any(a in werte for a in ort):
            ort = {"X": None, "Y": None, "Z": None}  # ein Zyklus: wo er endet, sagt er nicht
    if kette:
        yield from geschlossen()


def _gleich(f, g):
    if f is None or g is None:
        return f is None and g is None
    return abs(float(f) - float(g)) <= _GLEICH_F
