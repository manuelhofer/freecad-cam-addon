# SPDX-License-Identifier: LGPL-2.1-or-later
"""3D, die Bahn „3D-Schlichten“ (W-006 4.2 Punkt 3, Schlichten in Zeilen): Freiformflächen –
weder eben nach oben noch senkrecht, keine gezeichnete Fase: Kuppeln, Rundungen, Schrägen –
mit einem Kugel-, Torus- oder Schaftfräser in parallelen Zeilen. Die Spitze fährt auf der
Hüllfläche des ganzen Teils (hoehenfeld.je_zeile): Der Fräser berührt das Teil, schneidet nie
hinein, auch nicht an Nachbarflächen.

- **Wo:** genau dort, wo die gewählten Flächen die Höhe des Fräsers bestimmen – die Hüllfläche
  mit dem ganzen Teil liegt dort höher als die ohne sie (zwei Rechnungen je Zeile). So endet
  die Zeile am Fuß einer Kuppel, wo der Fräser die Platte daneben berührt; nicht gewählte
  Flächen bleiben, wie sie sind.
- **Zeilenabstand** aus der Grathöhe (fraeserform.Form.kammhoehe – die Kugel Ø 6 bei 0,01 mm:
  0,49 mm), gemessen auf ebener Fläche; an steilen Stellen lägen die Zeilen im Raum weiter
  auseinander, die Grate würden höher.
- **Steil/Flach** (W-006 4.2 Punkt 4): Darum fahren die Zeilen nur, wo es flacher ist als der
  Grenzwinkel (45°); wo es steiler ist, fährt er **Höhenlinien** – die Spitze auf fester Höhe
  rund um die Fläche, in z so weit auseinander wie die Zeilen in der Ebene, von oben nach unten,
  im Gleichlauf (das Material rechts, M3). Beide überlappen an der Grenze um UEBERLAPP. Die
  Neigung und die Höhenlinien kommen aus der Hüllfläche im Raster (RASTER): ihr Gradient, ihre
  Linien gleicher Höhe (Marching Squares, raeumen_bahn).
- **Richtung:** längs x und längs y gerechnet, die schnellere zählt (Grundsatz 0). Im Zickzack
  Zeile für Zeile hin und zurück; zwischen nahen Enden gleitet er hinüber (LUFT über der
  Hüllfläche beider Zeilen dazwischen), sonst Rückzug im Eilgang. Lücken in einer Zeile, kürzer
  als LUECKE_FAHREN, fährt er auf der Hüllfläche durch.
- Die Punkte längs der Zeile vereinfacht (Douglas-Peucker mit TOLERANZ_GERADE): auf geraden
  Stücken wenige Sätze, in Rundungen so viele, wie die Genauigkeit braucht.
- **Aufmaß:** der Fräser um das Aufmaß größer (Form.mit_aufmass), das Ergebnis um es gehoben –
  so bleibt es auch an steilen Stellen genau.

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import bahn as bn
from . import hoehenfeld as hf
from . import vierachs_bahn as vb
from . import vierachs_huelle as vh
from .sprache import tr

GLEICH = 1e-9
GRATHOEHE = 0.01  # mm – Vorschlag
SCHRITT = 0.2  # mm – Raster längs der Zeile
VORSCHAU_SCHRITT = 0.5  # mm – im Assistenten
TOLERANZ_NETZ = 0.01  # mm – so fein wird das Teil vernetzt
VORSCHAU_TOLERANZ = 0.05  # mm – im Assistenten
MASKE = 0.002  # mm – so viel höher muss die Hüllfläche mit den gewählten Flächen liegen
LUFT = 0.1  # mm – so hoch gleitet er zwischen zwei Zeilen über der Hüllfläche
LUECKE_FAHREN = 10.0  # mm – kürzere Lücken in einer Zeile fährt er auf der Hüllfläche durch
TOLERANZ_GERADE = 0.002  # mm – so weit darf ein ausgelassener Punkt von der Geraden liegen
NACH_OBEN = 0.05  # so weit muss eine Normale nach oben zeigen (n_z) – sonst sieht er nichts
GRENZWINKEL = 45.0  # Grad – steiler: Höhenlinien, flacher: Zeilen; 0: nur Zeilen
UEBERLAPP = 3.0  # Grad – so weit überlappen Zeilen und Höhenlinien an der Grenze
RASTER = 0.25  # mm – das Raster der Hüllfläche für Neigung und Höhenlinien
VORSCHAU_RASTER = 0.5  # mm – im Assistenten


@dataclass
class Schlichtwerte:
    """Was das 3D-Schlichten braucht; Längen in mm, z nach oben im Job."""

    form: object  # fraeserform.Form des Fräsers
    oben: float  # z, über dem nichts mehr steht (das Rohteil)
    sicher: float  # z für den Eilgang über allem
    grathoehe: float = GRATHOEHE
    aufmass: float = 0.0  # bleibt auf den Flächen stehen
    richtung: str = "auto"  # „auto“ (die schnellere), „x“ oder „y“
    grenzwinkel: float = GRENZWINKEL  # Grad – steiler: Höhenlinien; 0: nur Zeilen
    gleichlauf: bool = True  # Höhenlinien mit dem Material rechts (M3)
    sicherheit: float = vb.SICHERHEIT
    schritt: float = SCHRITT
    raster: float = RASTER
    vorschub: float = 0.0  # mm/min – für die Zeit; 0: 1000
    eintauchen: float = 0.0


@dataclass
class Schlichtbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    zeilen: int  # Zeilen mit Schnitt
    laengs_x: bool
    abstand: float  # der Zeilenabstand (mm)
    z_min: float
    laenge: float  # mm im Vorschub
    zeit: float  # Minuten (bahn.zeit)
    hoehenlinien: int = 0  # Höhen mit Höhenlinien (Steil/Flach)


# --- Flächen --------------------------------------------------------------------------------


def ist_freiform(form, name):
    """Ist die Fläche `name` eine Freiformfläche fürs 3D-Schlichten – nach oben gewandt, aber
    weder eben nach oben noch eine senkrechte Wand, keine gezeichnete Fase oder Rundung (die
    fräst „Entgraten“ genau) und keine Senkung (die senkt „Senken“)?"""
    from . import entgrat_bahn as eb
    from . import kontur_bahn as kb
    from . import vierachs_flaechen as vf

    nummern = vf.nummern([name])
    if not nummern or nummern[0] >= len(form.Faces):
        return False
    flaeche = form.Faces[nummern[0]]
    if hf.ebenen_oben(form, [name]) or kb.ist_wand(flaeche):
        return False
    try:
        u0, u1, v0, v1 = flaeche.ParameterRange
        oben = False
        for i in range(4):
            for j in range(4):
                n = flaeche.normalAt(u0 + (u1 - u0) * (i + 0.5) / 4, v0 + (v1 - v0) * (j + 0.5) / 4)
                oben = oben or n.z > NACH_OBEN * max(n.Length, 1e-12)
    except Exception:  # OCC: keine Parameter
        return False
    if not oben:
        return False
    from . import senken as sk

    return not eb.ist_fase(form, name) and not sk.ist_senkung(form, name)


def freiformflaechen(form, namen):
    """Die Namen unter `namen`, die Freiformflächen sind (ist_freiform)."""
    return [n for n in namen if ist_freiform(form, n)]


def zeilenabstand(form, grathoehe):
    """Der größte Abstand zweier Zeilen, bei dem auf ebener Fläche höchstens `grathoehe` stehen
    bleibt (Form.kammhoehe) – nie mehr als 90 % des Durchmessers."""
    hoechstens = 1.8 * form.radius
    if form.kammhoehe(hoechstens) <= grathoehe:
        return hoechstens
    unten, oben = 0.0, hoechstens
    for _ in range(60):
        mitte = (unten + oben) / 2
        if form.kammhoehe(mitte) <= grathoehe:
            unten = mitte
        else:
            oben = mitte
    return max(unten, 0.01)


def _netze(form_teil, namen, toleranz):
    """(das ganze Teil, das Teil ohne die Flächen `namen`) als vierachs_huelle.Netz – einmal
    vernetzt."""
    from . import vierachs_flaechen as vf

    fnetz = vf.vernetze(form_teil, toleranz)
    bleibt = ~np.isin(fnetz.flaeche, np.asarray(vf.nummern(namen), dtype=np.int64))
    dreiecke = fnetz.netz.dreiecke[bleibt]
    benutzt = np.unique(dreiecke)
    neu = np.full(len(fnetz.netz.punkte), -1, dtype=np.int64)
    neu[benutzt] = np.arange(len(benutzt))
    rest = vh.Netz(fnetz.netz.punkte[benutzt], neu[dreiecke], toleranz)
    return fnetz.netz, rest


# --- Bahn -----------------------------------------------------------------------------------


def _vereinfacht(u, z):
    """Die Stellen (Indizes) einer Zeile, die bleiben: Douglas-Peucker auf (u, z) mit
    TOLERANZ_GERADE."""
    n = len(u)
    if n <= 2:
        return list(range(n))
    behalten = np.zeros(n, dtype=bool)
    behalten[0] = behalten[-1] = True
    stapel = [(0, n - 1)]
    while stapel:
        a, b = stapel.pop()
        if b - a < 2:
            continue
        du, dz = u[b] - u[a], z[b] - z[a]
        laenge = math.hypot(du, dz)
        innen = np.arange(a + 1, b)
        if laenge < GLEICH:
            abstand = np.hypot(u[innen] - u[a], z[innen] - z[a])
        else:
            abstand = np.abs((u[innen] - u[a]) * dz - (z[innen] - z[a]) * du) / laenge
        k = int(np.argmax(abstand))
        if abstand[k] > TOLERANZ_GERADE:
            m = int(innen[k])
            behalten[m] = True
            stapel.append((a, m))
            stapel.append((m, b))
    return list(np.flatnonzero(behalten))


def _laeufe(maske, z, schritt):
    """[(von, bis)] – die Stücke einer Zeile, wo gefräst wird (Indizes, `bis` eingeschlossen),
    je um eine Stelle verlängert; Lücken kürzer als LUECKE_FAHREN über festem Grund zu einem
    Stück verbunden."""
    n = len(maske)
    stellen = np.flatnonzero(maske)
    if not len(stellen):
        return []
    laeufe = []
    von = bis = int(stellen[0])
    for i in stellen[1:]:
        i = int(i)
        if i == bis + 1:
            bis = i
            continue
        luecke = z[bis + 1 : i]
        if (i - bis - 1) * schritt < LUECKE_FAHREN and np.all(np.isfinite(luecke)):
            bis = i
            continue
        laeufe.append((von, bis))
        von = bis = i
    laeufe.append((von, bis))
    ergebnis = []
    for von, bis in laeufe:
        if von > 0 and np.isfinite(z[von - 1]):
            von -= 1
        if bis < n - 1 and np.isfinite(z[bis + 1]):
            bis += 1
        ergebnis.append((von, bis))
    return ergebnis


@dataclass
class _Raster:
    """Die Hüllfläche im Raster (x längs Achse 0, y längs Achse 1) – für Neigung und
    Höhenlinien."""

    xs: np.ndarray
    ys: np.ndarray
    z: np.ndarray  # die Spitze (mit Aufmaß); −inf, wo der Fräser nichts trifft
    gewaehlt: np.ndarray  # die gewählten Flächen bestimmen die Höhe
    neigung: np.ndarray  # rad; nan, wo es keine gibt

    def index(self, x, y):
        sx = self.xs[1] - self.xs[0]
        sy = self.ys[1] - self.ys[0]
        i = np.clip(np.rint((np.asarray(x, dtype=float) - self.xs[0]) / sx), 0, len(self.xs) - 1)
        j = np.clip(np.rint((np.asarray(y, dtype=float) - self.ys[0]) / sy), 0, len(self.ys) - 1)
        return i.astype(int), j.astype(int)

    def bei(self, feld, x, y):
        i, j = self.index(x, y)
        return feld[i, j]


def _raster(netz_alle, netz_rest, geformt, box, w):
    """Die Hüllfläche im Raster über `box` ± R, mit und ohne die gewählten Flächen."""
    R = w.form.radius
    x0, x1 = box[0] - R, box[1] + R
    y0, y1 = box[2] - R, box[3] + R
    nx = max(3, int(math.ceil((x1 - x0) / w.raster - 1e-9)) + 1)
    ny = max(3, int(math.ceil((y1 - y0) / w.raster - 1e-9)) + 1)
    xs, ys = np.linspace(x0, x1, nx), np.linspace(y0, y1, ny)
    sx, sy = float(xs[1] - xs[0]), float(ys[1] - ys[0])
    alle = hf.je_zeile(netz_alle, geformt, ys, x0, sx, nx, True)
    rest = hf.je_zeile(netz_rest, geformt, ys, x0, sx, nx, True)
    gewaehlt = np.isfinite(alle) & (alle > rest + MASKE)
    endlich = np.where(np.isfinite(alle), alle, np.nan)
    gx, gy = np.gradient(endlich, sx, sy)
    neigung = np.arctan(np.hypot(gx, gy))
    return _Raster(xs, ys, alle + max(w.aufmass, 0.0), gewaehlt, neigung)


def _stuecke(punkte, geschlossen, behalten):
    """[(punkte, geschlossen)] – die Teile eines Linienzugs, deren Ecken `behalten` sind."""
    n = len(punkte)
    if behalten.all():
        return [(punkte, geschlossen)]
    if not behalten.any():
        return []
    if geschlossen:
        k = int(np.flatnonzero(~behalten)[0])
        punkte = np.roll(punkte, -k, axis=0)
        behalten = np.roll(behalten, -k)
    ergebnis = []
    i = 0
    while i < n:
        if not behalten[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and behalten[j + 1]:
            j += 1
        if j > i:
            ergebnis.append((punkte[i : j + 1], False))
        i = j + 1
    return ergebnis


def _gerichtet(punkte, geschlossen, raster, gleichlauf):
    """Der Linienzug so gerichtet, dass das Material (die höhere Hüllfläche) rechts liegt –
    im Gegenlauf links."""
    n = len(punkte)
    stuecke = range(n if geschlossen else n - 1)
    laengen = [math.hypot(*(punkte[(i + 1) % n] - punkte[i])) for i in stuecke]
    weit = 2.0 * float(raster.xs[1] - raster.xs[0])
    rechts_hoeher = None
    for i in sorted(stuecke, key=lambda k: -laengen[k]):
        p, q = punkte[i], punkte[(i + 1) % n]
        tx, ty = q[0] - p[0], q[1] - p[1]
        laenge = math.hypot(tx, ty) or 1.0
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        links = raster.bei(raster.z, mx - ty / laenge * weit, my + tx / laenge * weit)
        rechts = raster.bei(raster.z, mx + ty / laenge * weit, my - tx / laenge * weit)
        if abs(float(links) - float(rechts)) > 1e-6:
            rechts_hoeher = float(rechts) > float(links)
            break
    if rechts_hoeher is not None and rechts_hoeher != gleichlauf:
        return punkte[::-1].copy()
    return punkte


def _verbinden(punkte, x, y, z, w, raster=None):
    """Zum Punkt (x, y, z) weiter: nah (2 R) mit dem Raster gleitend (LUFT über der
    Hüllfläche dazwischen), sonst im Eilgang über sicherer Höhe und hinab bis über das Rohteil.
    Ohne Punkt davor: hinein. Gibt die Länge im Vorschub zurück."""
    if not punkte:
        knapp = min(w.sicher, max(z, w.oben) + w.sicherheit)
        punkte.append(bn.Punkt(True, x, y, w.sicher))
        punkte.append(bn.Punkt(True, x, y, knapp))
        punkte.append(bn.Punkt(False, x, y, z, True))
        return bn.weg(punkte[-2], punkte[-1])
    jetzt = punkte[-1]
    d = math.hypot(x - jetzt.x, y - jetzt.y)
    if raster is not None and d <= 2 * w.form.radius:
        anzahl = max(2, int(math.ceil(d / float(raster.xs[1] - raster.xs[0]))) + 1)
        t = np.linspace(0.0, 1.0, anzahl)
        unter = raster.bei(raster.z, jetzt.x + (x - jetzt.x) * t, jetzt.y + (y - jetzt.y) * t)
        if np.all(np.isfinite(unter)):
            hoch = max(float(np.max(unter)), jetzt.z, z) + LUFT
            laenge = 0.0
            for px, py, pz in ((jetzt.x, jetzt.y, hoch), (x, y, hoch), (x, y, z)):
                punkt = bn.Punkt(False, px, py, pz)
                laenge += bn.weg(punkte[-1], punkt)
                punkte.append(punkt)
            return laenge
    punkte.append(bn.Punkt(True, jetzt.x, jetzt.y, w.sicher))
    punkte.append(bn.Punkt(True, x, y, w.sicher))
    punkte.append(bn.Punkt(True, x, y, min(w.sicher, max(z, w.oben) + w.sicherheit)))
    punkte.append(bn.Punkt(False, x, y, z, True))
    return bn.weg(punkte[-2], punkte[-1])


def _hoehenlinien(raster, w, abstand_z):
    """Die Höhenlinien, wo es steiler ist als der Grenzwinkel: ([bahn.Punkt], Länge, Höhen,
    z_min) – ohne den Rückzug am Ende."""
    from . import raeumen_bahn as rb

    grenze = math.radians(max(w.grenzwinkel - UEBERLAPP, 0.0))
    with np.errstate(invalid="ignore"):
        steil = raster.gewaehlt & (raster.neigung >= grenze)
    punkte = []
    if not steil.any():
        return punkte, 0.0, 0, math.inf
    z_steil = raster.z[steil]
    oben, unten = float(np.max(z_steil)), float(np.min(z_steil))
    anzahl = max(1, int(math.ceil((oben - unten) / abstand_z - 1e-9)))
    laenge = 0.0
    hoehen = 0
    z_min = math.inf
    for k in range(1, anzahl + 1):
        z = oben - (oben - unten) * k / anzahl
        stuecke = []
        for linie, geschlossen in rb._hoehenlinien(raster.z, raster.xs, raster.ys, z):
            behalten = raster.bei(steil, linie[:, 0], linie[:, 1])
            for teil, zu in _stuecke(linie, geschlossen, behalten):
                teil = rb._vereinfacht(teil, TOLERANZ_GERADE, zu)
                if len(teil) >= 2:
                    stuecke.append((_gerichtet(teil, zu, raster, w.gleichlauf), zu))
        if not stuecke:
            continue
        hoehen += 1
        z_min = min(z_min, z)
        while stuecke:
            if punkte:
                ort = (punkte[-1].x, punkte[-1].y)
            else:
                ort = (stuecke[0][0][0][0], stuecke[0][0][0][1])

            def naechster(s, ort=ort):
                teil, zu = s
                if zu:
                    return float(np.min(np.hypot(teil[:, 0] - ort[0], teil[:, 1] - ort[1])))
                return math.hypot(teil[0][0] - ort[0], teil[0][1] - ort[1])

            nummer = min(range(len(stuecke)), key=lambda i: naechster(stuecke[i]))
            teil, zu = stuecke.pop(nummer)
            if zu:
                i = int(np.argmin(np.hypot(teil[:, 0] - ort[0], teil[:, 1] - ort[1])))
                teil = np.vstack([np.roll(teil, -i, axis=0), np.roll(teil, -i, axis=0)[:1]])
            laenge += _verbinden(punkte, float(teil[0][0]), float(teil[0][1]), z, w, raster)
            for px, py in teil[1:]:
                punkt = bn.Punkt(False, float(px), float(py), z)
                laenge += bn.weg(punkte[-1], punkt)
                punkte.append(punkt)
    return punkte, laenge, hoehen, z_min


def _eine_richtung(netz_alle, netz_rest, box, w, laengs_x, abstand, geformt, raster, vorweg):
    """Die Bahn mit den Zeilen längs x (`laengs_x`) oder längs y – nach den Höhenlinien
    `vorweg` ([bahn.Punkt], Länge, Höhen, z_min); None, wo nichts zu fräsen ist. `box`: (x_von,
    x_bis, y_von, y_bis) der gewählten Flächen; mit `raster` die Zeilen nur, wo es flacher ist
    als der Grenzwinkel."""
    R = w.form.radius
    if laengs_x:
        u_von, u_bis, v_von, v_bis = box
    else:
        v_von, v_bis, u_von, u_bis = box
    v0, v1 = v_von - R, v_bis + R
    anzahl_v = max(2, int(math.ceil((v1 - v0) / abstand - 1e-9)) + 1)
    v_werte = np.linspace(v0, v1, anzahl_v)
    u0, u1 = u_von - R, u_bis + R
    anzahl_u = max(2, int(math.ceil((u1 - u0) / w.schritt - 1e-9)) + 1)
    u_werte = np.linspace(u0, u1, anzahl_u)
    schritt = float(u_werte[1] - u_werte[0])
    alle = hf.je_zeile(netz_alle, geformt, v_werte, u0, schritt, anzahl_u, laengs_x).T
    rest = hf.je_zeile(netz_rest, geformt, v_werte, u0, schritt, anzahl_u, laengs_x).T
    z = alle + max(w.aufmass, 0.0)
    maske = np.isfinite(alle) & (alle > rest + MASKE)
    if raster is not None and w.grenzwinkel > 0:
        uu, vv = np.meshgrid(u_werte, v_werte)  # (Zeilen, Stellen)
        xx, yy = (uu, vv) if laengs_x else (vv, uu)
        neigung = raster.bei(raster.neigung, xx, yy)
        with np.errstate(invalid="ignore"):
            steil = neigung >= math.radians(w.grenzwinkel + UEBERLAPP)
        maske &= ~steil

    def xy(u, v):
        return (u, v) if laengs_x else (v, u)

    punkte, laenge, hoehen, z_min = list(vorweg[0]), vorweg[1], vorweg[2], vorweg[3]
    zeilen = 0
    vorher = None  # (Zeile, Index am Ende) des vorigen Laufs
    rueckwaerts = False
    for k in range(anzahl_v):
        laeufe = _laeufe(maske[k], z[k], schritt)
        if not laeufe:
            continue
        zeilen += 1
        if rueckwaerts:
            laeufe = [(bis, von) for von, bis in reversed(laeufe)]
        for anfang, ende in laeufe:
            schritt_i = 1 if ende >= anfang else -1
            idx = np.arange(anfang, ende + schritt_i, schritt_i)
            behalten = [int(idx[i]) for i in _vereinfacht(u_werte[idx], z[k, idx])]
            x0, y0 = xy(float(u_werte[behalten[0]]), float(v_werte[k]))
            z0 = float(z[k, behalten[0]])
            if vorher is None:
                laenge += _verbinden(punkte, x0, y0, z0, w, raster)
            else:
                laenge += _hinueber(punkte, vorher, (k, behalten[0]), z, u_werte, v_werte, w, xy)
            for i in behalten[1:]:
                x, y = xy(float(u_werte[i]), float(v_werte[k]))
                punkt = bn.Punkt(False, x, y, float(z[k, i]))
                laenge += bn.weg(punkte[-1], punkt)
                punkte.append(punkt)
            z_min = min(z_min, float(np.min(z[k, idx])))
            vorher = (k, behalten[-1])
        rueckwaerts = not rueckwaerts
    if not punkte:
        return None
    letzter = punkte[-1]
    punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
    zeit = bn.zeit(punkte, w.vorschub if w.vorschub > 0 else 1000.0, w.eintauchen or None)
    return Schlichtbahn(punkte, zeilen, laengs_x, abstand, z_min, laenge, zeit, hoehen)


def _hinueber(punkte, von, nach, z, u_werte, v_werte, w, xy):
    """Vom Ende (Zeile, Index) `von` zum Anfang `nach`: in der Nachbarzeile und nah gleitend
    (LUFT über der Hüllfläche beider Zeilen dazwischen), sonst im Eilgang über sicherer Höhe.
    Gibt die Länge im Vorschub zurück."""
    k0, i0 = von
    k1, i1 = nach
    x0, y0 = xy(float(u_werte[i0]), float(v_werte[k0]))
    x1, y1 = xy(float(u_werte[i1]), float(v_werte[k1]))
    z1 = float(z[k1, i1])
    a, b = min(i0, i1), max(i0, i1)
    zwischen = np.concatenate((z[k0, a : b + 1], z[k1, a : b + 1]))
    nah = abs(k1 - k0) == 1 and abs(float(u_werte[i1] - u_werte[i0])) <= 2 * w.form.radius
    if nah and np.all(np.isfinite(zwischen)):
        hoch = float(np.max(zwischen)) + LUFT
        laenge = 0.0
        for x, y, zz in ((x0, y0, hoch), (x1, y1, hoch), (x1, y1, z1)):
            punkt = bn.Punkt(False, x, y, zz)
            laenge += bn.weg(punkte[-1], punkt)
            punkte.append(punkt)
        return laenge
    punkte.append(bn.Punkt(True, x0, y0, w.sicher))
    punkte.append(bn.Punkt(True, x1, y1, w.sicher))
    punkte.append(bn.Punkt(True, x1, y1, min(w.sicher, max(z1, w.oben) + w.sicherheit)))
    punkte.append(bn.Punkt(False, x1, y1, z1, True))
    return bn.weg(punkte[-2], punkte[-1])


def planen(form_teil, namen, werte, toleranz=TOLERANZ_NETZ):
    """Die Bahn „3D-Schlichten“ (Schlichtbahn) über die Flächen `namen` von `form_teil` mit den
    Werten `werte`. ValueError mit einem Satz, wenn es nicht geht."""
    w = werte
    if w.form is None or w.form.radius <= 0:
        raise ValueError(tr("s3.fehler.form"))
    if w.grathoehe <= 0:
        raise ValueError(tr("s3.fehler.grathoehe"))
    flaechen = freiformflaechen(form_teil, namen)
    if not flaechen:
        raise ValueError(tr("s3.fehler.keine"))
    from . import vierachs_flaechen as vf

    box = None
    for nummer in vf.nummern(flaechen):
        bb = form_teil.Faces[nummer].BoundBox
        teil = (bb.XMin, bb.XMax, bb.YMin, bb.YMax)
        if box is None:
            box = teil
        else:
            box = (
                min(box[0], teil[0]),
                max(box[1], teil[1]),
                min(box[2], teil[2]),
                max(box[3], teil[3]),
            )
    netz_alle, netz_rest = _netze(form_teil, flaechen, toleranz)
    geformt = w.form.mit_aufmass(max(w.aufmass, 0.0))
    abstand = zeilenabstand(w.form, w.grathoehe)
    raster = None
    vorweg = ([], 0.0, 0, math.inf)
    if 0 < w.grenzwinkel < 90:
        raster = _raster(netz_alle, netz_rest, geformt, box, w)
        vorweg = _hoehenlinien(raster, w, abstand)
    richtungen = {"x": (True,), "y": (False,)}.get(w.richtung, (True, False))
    beste = None
    for laengs_x in richtungen:
        bahn = _eine_richtung(
            netz_alle, netz_rest, box, w, laengs_x, abstand, geformt, raster, vorweg
        )
        if bahn is not None and (beste is None or bahn.zeit < beste.zeit):
            beste = bahn
    if beste is None:
        raise ValueError(tr("s3.fehler.nichts"))
    return beste
