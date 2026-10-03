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
- **Spirale** (P-2026-10-01-48): von der Mitte der Flächen nach außen, archimedisch mit dem
  Zeilenabstand je Umlauf, die Spitze auf der Hüllfläche aus dem Raster (bilinear) – ohne
  Wenden, wo die Zeilen an jedem Ende umkehren; gefräst nur, wo die gewählten Flächen die Höhe
  bestimmen und es flacher ist als der Grenzwinkel. Neben längs x und längs y gerechnet – nur mit
  Steil/Flach: Ihr Abstand liegt in der Ebene, an jeder Flanke einer Kuppel quer zur Steigung;
  ohne Höhenlinien blieben dort höhere Grate als bei Zeilen (an der Halbkugel 0,15 statt
  0,056 mm), die schnellere Zeit wäre nicht dasselbe Ergebnis.
- **Richtung:** längs x, längs y und die Spirale gerechnet, die schnellste zählt (Grundsatz 0). Im Zickzack
  Zeile für Zeile hin und zurück; zwischen nahen Enden gleitet er hinüber (LUFT über der
  Hüllfläche beider Zeilen dazwischen), sonst Rückzug im Eilgang. Lücken in einer Zeile, kürzer
  als LUECKE_FAHREN, fährt er auf der Hüllfläche durch.
- Die Punkte längs der Zeile vereinfacht (Douglas-Peucker mit TOLERANZ_GERADE): auf geraden
  Stücken wenige Sätze, in Rundungen so viele, wie die Genauigkeit braucht.
- **Aufmaß:** der Fräser um das Aufmaß größer (Form.mit_aufmass), das Ergebnis um es gehoben –
  so bleibt es auch an steilen Stellen genau.
- **Fläche entlang** (Flowline, W-006 4.2 Punkt 7, P-2026-10-02-03): je gewählter Fläche die
  Kurven gleicher Parameter – längs u oder längs v, beide gerechnet –, quer so dicht, dass ihr
  Abstand im Raum nirgends über dem Zeilenabstand liegt (gemessen an FLUSS_PROBEN Stellen je
  Kurve); die Spitze dort, wo der Fräser die Fläche an der Kurve berührt (die Achse um seine
  Stütze zur Seite der Normale, die Kugel: P + r · n), ihre Höhe aus der Hüllfläche im Raster –
  nie ins Teil. Offene Kurven im Zickzack, geschlossene (ein Kreis um eine Kuppel) immer im
  Gleichlauf. An einer Kuppel sind die Kurven längs u die Breitenkreise: gleich weit
  auseinander auf der Fläche, flach wie steil, ohne Höhenlinien. Im Wettbewerb neben x, y und
  der Spirale – nur mit Steil/Flach, wie die Spirale.
- **Nicht über Kanten rollen** (P-2026-10-02-03): Höhenlinien, Spirale, Fläche entlang und
  Zeilen fahren nur, wo der Fräser eine gewählte Fläche innen berührt (_beruehrt). Im Saum
  dahinter rollt er nur über die Kante – an der Außenkante eines Teils, an einem Absatz –,
  fräst nichts mehr, und die Hüllfläche fällt dort fast senkrecht: aus dem Raster gerechnet
  schnitten Höhenlinien und Spirale in die Kante (an einer Welle ohne Platte 0,05 mm in die
  Seite). Eine Lücke dieser Maske entlang einer Höhenlinie, höchstens R lang, fährt sie durch
  (B-013, P-2026-10-04-12): Am Rand einer Mulde berührt die Kugel an den Ecken der Vernetzung
  die Kante statt der Fläche – der Ring zerfiel in Stücke, jedes mit einem Hub von gut 1 mm.
- **Restschlichten** (W-006 4.2 Punkt 8, P-2026-10-02-01): Mit `davor` (die Form des größeren
  Fräsers, der vorher schlichtete) fährt er nur dort, wo der davor mehr als REST stehen ließ, als
  dieser wegnimmt – in Kehlen, engen Rundungen, Ecken. Beide Flächen, die die Fräser stehen
  lassen, kommen aus ihrer Hüllfläche im Raster: je Stelle die tiefste Unterseite der Stirn über
  alle Lagen der Spitze im Umkreis (`_schnitt`, gleitendes Minimum mit dem Profil der Stirn).
  Was übersteht, ist der Rest; um R + Zeilenabstand erweitert, damit die Bahnen ihn ganz
  überdecken. Zeilen, Höhenlinien und Spirale fahren nur dort.

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
RASTER = 0.25  # mm – das Raster der Hüllfläche für Neigung, Höhenlinien und die Spirale
REST = 0.01  # mm – so viel mehr muss der Fräser davor stehen lassen, damit das Restschlichten fährt
_TIEF = -1e6  # mm – wo die Spitze nichts trifft: für den Schnitt beliebig tief
VORSCHAU_RASTER = 0.5  # mm – im Assistenten
SPIRALE = "spirale"
FLAECHE = "flaeche"  # Richtung: entlang der Fläche (Flowline)
AEQUI = "aequidistant"  # Richtung: Ringe im gleichen Abstand im Raum (3D-Offset)
ABSTAND_RUNDEN = 12  # höchstens so oft hin und zurück, bis das Abstandsfeld steht
GRAT_STEIGUNG = 0.5  # so flach muss ein Grat des Abstandsfelds längs laufen, damit er eine Bahn
# bekommt – an der Ecke eines Rechtecks steigt er mit 0,71 und die Ringe laufen um ihn herum
FLUSS_PROBEN = 64  # so viele Stellen je Kurve, an denen der Abstand quer gemessen wird
FLUSS_FEIN = 400  # so fein wird quer vorgerechnet


@dataclass
class Schlichtwerte:
    """Was das 3D-Schlichten braucht; Längen in mm, z nach oben im Job."""

    form: object  # fraeserform.Form des Fräsers
    oben: float  # z, über dem nichts mehr steht (das Rohteil)
    sicher: float  # z für den Eilgang über allem
    grathoehe: float = GRATHOEHE
    aufmass: float = 0.0  # bleibt auf den Flächen stehen
    richtung: str = (
        "auto"  # „auto“ (die schnellste), „x“, „y“, „spirale“, „flaeche“, „aequidistant“
    )
    grenzwinkel: float = GRENZWINKEL  # Grad – steiler: Höhenlinien; 0: nur Zeilen
    gleichlauf: bool = True  # Höhenlinien mit dem Material rechts (M3)
    sicherheit: float = vb.SICHERHEIT
    schritt: float = SCHRITT
    raster: float = RASTER
    vorschub: float = 0.0  # mm/min – für die Zeit; 0: 1000
    eintauchen: float = 0.0
    davor: object = (
        None  # fraeserform.Form des größeren Fräsers davor: nur der Rest (Restschlichten)
    )
    rest: float = REST


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
    spirale: bool = False  # eine Spirale statt Zeilen (dann `zeilen` 0)
    umlaeufe: int = 0  # die Umläufe der Spirale
    flaeche: bool = False  # entlang der Fläche (dann `zeilen` die Kurven)
    aequidistant: bool = False  # Ringe im gleichen Abstand (dann `zeilen` die Ringe)


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
    """(das ganze Teil, das Teil ohne die Flächen `namen`) als vierachs_huelle.Netz und die
    gewählten Flächen allein (Punkte, Dreiecke, Fläche je Dreieck) – einmal vernetzt."""
    from . import vierachs_flaechen as vf

    fnetz = vf.vernetze(form_teil, toleranz)
    bleibt = ~np.isin(fnetz.flaeche, np.asarray(vf.nummern(namen), dtype=np.int64))
    dreiecke = fnetz.netz.dreiecke[bleibt]
    benutzt = np.unique(dreiecke)
    neu = np.full(len(fnetz.netz.punkte), -1, dtype=np.int64)
    neu[benutzt] = np.arange(len(benutzt))
    rest = vh.Netz(fnetz.netz.punkte[benutzt], neu[dreiecke], toleranz)
    gewaehlt = (fnetz.netz.punkte, fnetz.netz.dreiecke[~bleibt], fnetz.flaeche[~bleibt])
    return fnetz.netz, rest, gewaehlt


def _beruehrt(gewaehlt, form, xs, ys):
    """Maske im Raster (xs, ys): wo die Spitze steht, wenn der Fräser `form` eine der gewählten
    Flächen innen berührt. Jedes Dreieck wird verschoben – jeder Punkt um die Stütze des
    Fräsers (Form.stuetze) zur Seite seiner Normale (gemittelt über die Dreiecke derselben
    Fläche; die Kugel: um r · n) – und ins Raster gelegt. Was fehlt, ist der Saum, in dem er nur
    noch über eine Kante rollt (an der Außenkante eines Teils, an einem Absatz): Dort fräst er an
    den Flächen nichts mehr, und die Hüllfläche fällt fast senkrecht – aus dem Raster gerechnet,
    schnitte er dort in die Kante (an einer Welle ohne Platte 0,05 mm in die Seite)."""
    punkte, dreiecke, flaeche = gewaehlt
    beruehrt = np.zeros((len(xs), len(ys)), dtype=bool)
    for nummer in np.unique(flaeche):
        d = dreiecke[flaeche == nummer]
        a, b, c = punkte[d[:, 0]], punkte[d[:, 1]], punkte[d[:, 2]]
        n = np.cross(b - a, c - a)  # so lang wie die doppelte Fläche: gewichtet
        if float(np.sum(n[:, 2])) < 0:
            n = -n  # die Fläche andersherum vernetzt
        laenge = np.linalg.norm(n, axis=1)
        nach_oben = n[:, 2] >= NACH_OBEN * np.maximum(laenge, 1e-300)
        d, n = d[nach_oben], n[nach_oben]
        if not len(d):
            continue
        normale = np.zeros_like(punkte)
        for ecke in range(3):
            np.add.at(normale, d[:, ecke], n)
        benutzt = np.unique(d)
        nb = normale[benutzt]
        nb /= np.maximum(np.linalg.norm(nb, axis=1), 1e-300)[:, None]
        seitlich = np.hypot(nb[:, 0], nb[:, 1])
        rho, _z = form.stuetze(np.arctan2(seitlich, np.maximum(nb[:, 2], 0.0)))
        weit = np.where(seitlich > 1e-9, rho / np.maximum(seitlich, 1e-9), 0.0)
        verschoben = np.zeros((len(benutzt), 3))
        verschoben[:, 0] = punkte[benutzt, 0] + weit * nb[:, 0]
        verschoben[:, 1] = punkte[benutzt, 1] + weit * nb[:, 1]
        neu = np.full(len(punkte), -1, dtype=np.int64)
        neu[benutzt] = np.arange(len(benutzt))
        flach = vh.Netz(verschoben, neu[d], 0.0)
        beruehrt |= hf.hoehen(flach, xs, ys) > hf.KEIN_TREFFER / 2
    return beruehrt


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
    innen: np.ndarray = None  # der Fräser berührt die gewählten Flächen innen (_beruehrt)

    def index(self, x, y):
        sx = self.xs[1] - self.xs[0]
        sy = self.ys[1] - self.ys[0]
        i = np.clip(np.rint((np.asarray(x, dtype=float) - self.xs[0]) / sx), 0, len(self.xs) - 1)
        j = np.clip(np.rint((np.asarray(y, dtype=float) - self.ys[0]) / sy), 0, len(self.ys) - 1)
        return i.astype(int), j.astype(int)

    def bei(self, feld, x, y):
        i, j = self.index(x, y)
        return feld[i, j]


def _raster(netz_alle, netz_rest, geformt, box, w, gewaehlt_netz=None):
    """Die Hüllfläche im Raster über `box` ± R, mit und ohne die gewählten Flächen – beim
    Restschlichten ± dem größeren Radius (der Fräser davor braucht seine Lagen am Rand). Mit
    `gewaehlt_netz` (aus _netze) gilt als gewählt nur, wo der Fräser die Flächen innen berührt
    (_beruehrt), eine Zelle weiter."""
    davor = getattr(w, "davor", None)  # auch der Bleistift rechnet hier, ohne Fräser davor
    R = max(w.form.radius, davor.radius if davor is not None else 0.0)
    x0, x1 = box[0] - R, box[1] + R
    y0, y1 = box[2] - R, box[3] + R
    nx = max(3, int(math.ceil((x1 - x0) / w.raster - 1e-9)) + 1)
    ny = max(3, int(math.ceil((y1 - y0) / w.raster - 1e-9)) + 1)
    xs, ys = np.linspace(x0, x1, nx), np.linspace(y0, y1, ny)
    sx, sy = float(xs[1] - xs[0]), float(ys[1] - ys[0])
    alle = hf.je_zeile(netz_alle, geformt, ys, x0, sx, nx, True)
    rest = hf.je_zeile(netz_rest, geformt, ys, x0, sx, nx, True)
    gewaehlt = np.isfinite(alle) & (alle > rest + MASKE)
    innen = None
    if gewaehlt_netz is not None:
        innen = _erweitert(_beruehrt(gewaehlt_netz, geformt, xs, ys), 1.01 * max(sx, sy), sx, sy)
        gewaehlt &= innen
    endlich = np.where(np.isfinite(alle), alle, np.nan)
    gx, gy = np.gradient(endlich, sx, sy)
    neigung = np.arctan(np.hypot(gx, gy))
    return _Raster(xs, ys, alle + max(w.aufmass, 0.0), gewaehlt, neigung, innen)


def _verschoben(d, n):
    """(Ziel, Quelle) als slices: Ziel[k] = Quelle[k + d] in einer Achse der Länge n."""
    return slice(max(0, -d), n - max(0, d)), slice(max(0, d), n - max(0, -d))


def _schnitt(t, form, sx, sy):
    """(nx, ny) mm: die Fläche, die der Fräser `form` stehen lässt, wenn seine Spitze überall auf
    der Hüllfläche `t` fährt (−inf: trifft nichts) – je Stelle die tiefste Unterseite der Stirn
    über alle Lagen der Spitze im Umkreis R (gleitendes Minimum mit dem Profil)."""
    R = float(form.radius)
    tief = np.where(np.isfinite(t), t, _TIEF)
    nx, ny = tief.shape
    flaeche = tief.copy()
    ni, nj = int(R / sx + 1e-9), int(R / sy + 1e-9)
    for di in range(-ni, ni + 1):
        ziel_i, quelle_i = _verschoben(di, nx)
        for dj in range(-nj, nj + 1):
            rho = math.hypot(di * sx, dj * sy)
            if (di == 0 and dj == 0) or rho > R + 1e-9:
                continue
            h = float(form.hoehe(min(rho, R)))
            ziel_j, quelle_j = _verschoben(dj, ny)
            ziel = flaeche[ziel_i, ziel_j]
            np.minimum(ziel, tief[quelle_i, quelle_j] + h, out=ziel)
    return flaeche


def _erweitert(maske, weite, sx, sy):
    """`maske` um `weite` (mm) erweitert – rund, im Raster."""
    ergebnis = maske.copy()
    nx, ny = maske.shape
    ni, nj = int(weite / sx + 1e-9), int(weite / sy + 1e-9)
    for di in range(-ni, ni + 1):
        ziel_i, quelle_i = _verschoben(di, nx)
        for dj in range(-nj, nj + 1):
            if math.hypot(di * sx, dj * sy) > weite + 1e-9:
                continue
            ziel_j, quelle_j = _verschoben(dj, ny)
            ziel = ergebnis[ziel_i, ziel_j]
            np.logical_or(ziel, maske[quelle_i, quelle_j], out=ziel)
    return ergebnis


def _rest(raster, netz_alle, w, abstand):
    """(Maske, Rest) im Raster: wo der Fräser davor (`w.davor`) mehr als `w.rest` stehen ließ,
    als dieser wegnimmt – die Maske um R + Zeilenabstand erweitert; der Rest in mm."""
    xs, ys = raster.xs, raster.ys
    sx, sy = float(xs[1] - xs[0]), float(ys[1] - ys[0])
    x0, nx = float(xs[0]), len(xs)
    flaeche_davor = _schnitt(hf.je_zeile(netz_alle, w.davor, ys, x0, sx, nx, True), w.davor, sx, sy)
    flaeche = _schnitt(hf.je_zeile(netz_alle, w.form, ys, x0, sx, nx, True), w.form, sx, sy)
    gueltig = (flaeche_davor > _TIEF / 2) & (flaeche > _TIEF / 2)
    # Nur über dem Teil: Neben seinem Rand liegt die Hülle des größeren Fräsers, der um die Kante
    # rollt, höher – in der Luft, kein Rest (an einer Kuppel ohne Platte 0,08 mm).
    gueltig &= hf.hoehen(netz_alle, xs, ys, innen=True) > hf.KEIN_TREFFER / 2
    # Am Rand des Rasters fehlen dem Fräser davor die Lagen draußen: dort kein Rest.
    ki = int(math.ceil(float(w.davor.radius) / sx - 1e-9))
    kj = int(math.ceil(float(w.davor.radius) / sy - 1e-9))
    gueltig[:ki, :] = gueltig[-ki:, :] = False
    gueltig[:, :kj] = gueltig[:, -kj:] = False
    rest = np.where(gueltig, flaeche_davor - flaeche, 0.0)
    # Zwischen zwei Rasterpunkten bleibt unter der kleinen Stirn ein Grat (Raster² ÷ 8 r): Was
    # darunter liegt, ist Rechnung, kein Rest – doppelt genommen (im groben Raster der Vorschau
    # sonst 0,02 mm „Rest“ an einer Kuppel ohne Kehle).
    schwelle = max(w.rest, max(sx, sy) ** 2 / (4.0 * max(float(w.form.radius), GLEICH)))
    return _erweitert(rest > schwelle, w.form.radius + abstand, sx, sy), rest


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


def _luecken_gefuellt(punkte, geschlossen, behalten, laenge):
    """`behalten` mit den Lücken gefüllt, die zwischen zwei behaltenen Ecken liegen und entlang
    des Linienzugs höchstens `laenge` (mm) lang sind – beim geschlossenen über den Anfang
    hinweg."""
    n = len(punkte)
    if n < 3 or behalten.all() or not behalten.any():
        return behalten
    ergebnis = behalten.copy()
    reihe = np.arange(n)
    if geschlossen:
        reihe = np.roll(reihe, -int(np.flatnonzero(behalten)[0]))  # beginnt bei einer behaltenen
    werte = behalten[reihe]
    k = 0
    while k < n:
        if werte[k]:
            k += 1
            continue
        a = k
        while k < n and not werte[k]:
            k += 1
        if not geschlossen and (a == 0 or k == n):
            continue  # am offenen Ende: keine Lücke zwischen zwei Stücken
        folge = reihe[a - 1 : k + 1] if k < n else np.concatenate([reihe[a - 1 :], reihe[:1]])
        if np.sum(np.hypot(*np.diff(punkte[folge, :2], axis=0).T)) <= laenge:
            ergebnis[reihe[a:k]] = True
    return ergebnis


def _gerichtet(punkte, geschlossen, raster, gleichlauf):
    """Der Linienzug so gerichtet, dass das Material (die höhere Hüllfläche) rechts liegt –
    im Gegenlauf links."""
    rechts_hoeher = _material_rechts(punkte, geschlossen, raster)
    if rechts_hoeher is not None and rechts_hoeher != gleichlauf:
        return punkte[::-1].copy()
    return punkte


def _material_rechts(punkte, geschlossen, raster):
    """True, wenn rechts des Linienzugs `punkte` ([(x, y)]) die Hüllfläche höher liegt (das
    Material), False links, None, wo beide Seiten gleich hoch sind."""
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
    return rechts_hoeher


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
            # Kurze Lücken der Maske (am Rand einer Mulde berührt die Kugel an den Ecken der
            # Vernetzung die Kante statt der Fläche) zerteilten den Ring – jede kostete einen
            # Hub. Entlang der Höhenlinie bleibt die Spitze auf der Hüllfläche: durchfahren.
            behalten = _luecken_gefuellt(linie, geschlossen, behalten, w.form.radius)
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
    if raster is not None:
        uu, vv = np.meshgrid(u_werte, v_werte)  # (Zeilen, Stellen)
        xx, yy = (uu, vv) if laengs_x else (vv, uu)
        if w.grenzwinkel > 0:
            neigung = raster.bei(raster.neigung, xx, yy)
            with np.errstate(invalid="ignore"):
                steil = neigung >= math.radians(w.grenzwinkel + UEBERLAPP)
            maske &= ~steil
        if raster.innen is not None:
            maske &= raster.bei(raster.innen, xx, yy)  # nicht über Kanten rollen
        if w.davor is not None:
            maske &= raster.bei(raster.gewaehlt, xx, yy)  # nur der Rest

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


def _bilinear(raster, x, y):
    """Die Hüllfläche aus dem Raster an (x, y), bilinear zwischen den vier Knoten – nan, wo einer
    nichts trifft oder (x, y) außerhalb liegt."""
    xs, ys, z = raster.xs, raster.ys, raster.z
    sx, sy = float(xs[1] - xs[0]), float(ys[1] - ys[0])
    fx = (np.asarray(x, dtype=float) - xs[0]) / sx
    fy = (np.asarray(y, dtype=float) - ys[0]) / sy
    drin = (fx >= 0) & (fy >= 0) & (fx <= len(xs) - 1) & (fy <= len(ys) - 1)
    i0 = np.clip(np.floor(fx).astype(int), 0, len(xs) - 2)
    j0 = np.clip(np.floor(fy).astype(int), 0, len(ys) - 2)
    tx, ty = fx - i0, fy - j0
    ecken = (z[i0, j0], z[i0 + 1, j0], z[i0, j0 + 1], z[i0 + 1, j0 + 1])
    endlich = np.all([np.isfinite(e) for e in ecken], axis=0) & drin
    with np.errstate(invalid="ignore"):
        wert = (
            ecken[0] * (1 - tx) * (1 - ty)
            + ecken[1] * tx * (1 - ty)
            + ecken[2] * (1 - tx) * ty
            + ecken[3] * tx * ty
        )
    return np.where(endlich, wert, np.nan)


def _vereinfacht3d(punkte):
    """Douglas-Peucker im Raum mit TOLERANZ_GERADE – die Indizes, die bleiben."""
    n = len(punkte)
    if n <= 2:
        return list(range(n))
    behalten = np.zeros(n, dtype=bool)
    behalten[0] = behalten[-1] = True
    stapel = [(0, n - 1)]
    while stapel:
        a, b = stapel.pop()
        if b - a < 2:
            continue
        p, q = punkte[a], punkte[b]
        d = q - p
        laenge = float(np.linalg.norm(d))
        innen = punkte[a + 1 : b]
        if laenge < GLEICH:
            abstand = np.linalg.norm(innen - p, axis=1)
        else:
            abstand = np.linalg.norm(np.cross(innen - p, d), axis=1) / laenge
        k = int(np.argmax(abstand))
        if abstand[k] > TOLERANZ_GERADE:
            m = a + 1 + k
            behalten[m] = True
            stapel.append((a, m))
            stapel.append((m, b))
    return list(np.flatnonzero(behalten))


def _spirale(raster, w, abstand, vorweg):
    """Die Bahn als Spirale von der Mitte der gewählten Flächen nach außen – nach den
    Höhenlinien `vorweg`; None, wo nichts zu fräsen ist."""
    maske_raster = raster.gewaehlt.copy()
    if w.grenzwinkel > 0:
        with np.errstate(invalid="ignore"):
            maske_raster &= ~(raster.neigung >= math.radians(w.grenzwinkel + UEBERLAPP))
    zellen = np.argwhere(maske_raster)
    if not len(zellen):
        return None
    gx, gy = raster.xs[zellen[:, 0]], raster.ys[zellen[:, 1]]
    mitte = (float(gx.mean()), float(gy.mean()))
    weite = float(np.max(np.hypot(gx - mitte[0], gy - mitte[1]))) + float(
        raster.xs[1] - raster.xs[0]
    )
    b = abstand / (2 * math.pi)  # r = b · θ
    winkel = [0.0]
    theta = 0.0
    while b * theta < weite:
        theta += w.schritt / math.hypot(b * theta, b)
        winkel.append(theta)
    theta = np.array(winkel)
    x = mitte[0] + b * theta * np.cos(theta)
    y = mitte[1] + b * theta * np.sin(theta)
    z = _bilinear(raster, x, y) + 0.0  # das Aufmaß steckt schon im Raster
    maske = raster.bei(maske_raster, x, y) & np.isfinite(z)
    laeufe = _laeufe(maske, z, w.schritt)
    if not laeufe:
        return None
    punkte, laenge, hoehen, z_min = list(vorweg[0]), vorweg[1], vorweg[2], vorweg[3]
    for anfang, ende in laeufe:
        idx = np.arange(anfang, ende + 1)
        raum = np.column_stack([x[idx], y[idx], z[idx]])
        behalten = _vereinfacht3d(raum)
        x0, y0, z0 = (float(v) for v in raum[behalten[0]])
        laenge += _verbinden(punkte, x0, y0, z0, w, raster)
        for i in behalten[1:]:
            punkt = bn.Punkt(False, float(raum[i, 0]), float(raum[i, 1]), float(raum[i, 2]))
            laenge += bn.weg(punkte[-1], punkt)
            punkte.append(punkt)
        z_min = min(z_min, float(np.min(raum[:, 2])))
    letzter = punkte[-1]
    punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
    zeit = bn.zeit(punkte, w.vorschub if w.vorschub > 0 else 1000.0, w.eintauchen or None)
    # Die Umläufe, in denen gefräst wird – beim Restschlichten liegt innen oft nichts.
    gefraest = float(theta[laeufe[-1][1]] - theta[laeufe[0][0]])
    umlaeufe = max(1, int(math.ceil(gefraest / (2 * math.pi) - 1e-9)))
    return Schlichtbahn(punkte, 0, True, abstand, z_min, laenge, zeit, hoehen, True, umlaeufe)


def _fluss_gitter(f, laengs_u, ss, tt):
    """[len(tt), len(ss), 3] – die Punkte der Fläche `f` an den Parametern längs `ss` und quer
    `tt` (längs u: u = s, v = t)."""
    if laengs_u:
        return np.array([[tuple(f.valueAt(s, t)) for s in ss] for t in tt])
    return np.array([[tuple(f.valueAt(t, s)) for s in ss] for t in tt])


def _fluss_kurven(f, laengs_u, abstand):
    """[t] – die Werte des Querparameters der Kurven einer Fläche `f` (längs u: v je Kurve),
    so dicht, dass zwei Nachbarn im Raum nirgends weiter als `abstand` auseinander liegen.
    Quer erst grob, dann so fein vorgerechnet, dass auf einen Abstand vier Schritte kommen."""
    u0, u1, v0, v1 = f.ParameterRange
    s0, s1, t0, t1 = (u0, u1, v0, v1) if laengs_u else (v0, v1, u0, u1)
    ss = np.linspace(s0, s1, FLUSS_PROBEN)
    grob = _fluss_gitter(f, laengs_u, ss, np.linspace(t0, t1, 17))
    quer = float(np.linalg.norm(np.diff(grob, axis=0), axis=2).max(axis=1).sum())
    fein = int(min(FLUSS_FEIN, max(16, math.ceil(4.0 * quer / abstand))))
    tt = np.linspace(t0, t1, fein + 1)
    P = _fluss_gitter(f, laengs_u, ss, tt)
    schritte = np.linalg.norm(np.diff(P, axis=0), axis=2).max(axis=1)
    weg = np.concatenate([[0.0], np.cumsum(schritte)])
    if weg[-1] <= GLEICH:
        return np.array([t0])
    anzahl = max(1, int(math.ceil(weg[-1] / abstand - 1e-9)))
    return np.interp(np.linspace(0.0, weg[-1], anzahl + 1), weg, tt)


def _fluss_kurve(f, laengs_u, t, schritt, form):
    """(x, y) der Spitze längs einer Kurve der Fläche `f` (Querparameter `t`), etwa `schritt`
    auseinander: dort, wo der Fräser `form` die Fläche an der Kurve berührt – seine Achse um
    den Abstand der Stütze (Form.stuetze) von P weg, zur Seite, zu der die Normale zeigt (die
    Kugel: P + r · n). Stellen, an denen die Fläche nicht nach oben schaut, fallen weg (nan)."""
    u0, u1, v0, v1 = f.ParameterRange
    s0, s1 = (u0, u1) if laengs_u else (v0, v1)
    grob = np.linspace(s0, s1, FLUSS_PROBEN)
    pg = _fluss_gitter(f, laengs_u, grob, [t])[0]
    weg = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pg, axis=0), axis=1))])
    anzahl = max(2, int(math.ceil(weg[-1] / schritt - 1e-9)) + 1)
    ss = np.interp(np.linspace(0.0, weg[-1], anzahl), weg, grob)
    p = np.full((anzahl, 3), np.nan)
    n = np.full((anzahl, 3), np.nan)
    for k, s in enumerate(ss):
        u, v = (s, t) if laengs_u else (t, s)
        try:
            normale = f.normalAt(u, v)
        except Exception:  # an einem Pol hat die Fläche keine Normale
            continue
        if normale.z < NACH_OBEN:
            continue
        p[k] = tuple(f.valueAt(u, v))
        n[k] = tuple(normale)
    seitlich = np.hypot(n[:, 0], n[:, 1])
    with np.errstate(invalid="ignore"):
        neigung = np.arctan2(seitlich, n[:, 2])
        rho, _z = form.stuetze(np.nan_to_num(neigung))
        weit = np.where(seitlich > 1e-9, rho / np.where(seitlich > 1e-9, seitlich, 1.0), 0.0)
    return p[:, 0] + weit * n[:, 0], p[:, 1] + weit * n[:, 1]


def _geschlossen(x, y, schritt):
    """Ob die Kurve dort endet, wo sie beginnt (ein Kreis um eine Kuppel)."""
    if not (np.isfinite(x[0]) and np.isfinite(x[-1])):
        return False
    return math.hypot(x[-1] - x[0], y[-1] - y[0]) <= schritt


def _flaeche_entlang(form_teil, flaechen, raster, w, abstand, laengs_u, geformt):
    """Die Bahn entlang der Flächen (Flowline): je Fläche die Kurven längs u (`laengs_u`) oder
    längs v (_fluss_kurven), die Spitze auf der Hüllfläche aus dem Raster, nur wo die gewählten
    Flächen die Höhe bestimmen. Offene Kurven im Zickzack, geschlossene immer mit dem Material
    rechts (im Gegenlauf links) – von einer zur nächsten nur ein Schritt quer. None, wo nichts
    zu fräsen ist."""
    from . import vierachs_flaechen as vf

    punkte = []
    laenge = 0.0
    kurven = 0
    z_min = math.inf
    rueckwaerts = False
    for nummer in vf.nummern(flaechen):
        f = form_teil.Faces[nummer]
        for t in _fluss_kurven(f, laengs_u, abstand):
            x, y = _fluss_kurve(f, laengs_u, float(t), w.schritt, geformt)
            zu = _geschlossen(x, y, w.schritt)
            if zu:
                gueltig = np.isfinite(x)
                rechts = _material_rechts(np.column_stack([x[gueltig], y[gueltig]]), True, raster)
                umkehren = rechts is not None and rechts != w.gleichlauf
            else:
                umkehren = rueckwaerts
            if umkehren:
                x, y = x[::-1], y[::-1]
            with np.errstate(invalid="ignore"):
                z = _bilinear(raster, x, y)
                maske = np.isfinite(x) & np.isfinite(z)
            if maske.any():
                maske &= raster.bei(raster.gewaehlt, np.nan_to_num(x), np.nan_to_num(y))
            laeufe = _laeufe(maske, np.where(np.isfinite(x), z, np.nan), w.schritt)
            if not laeufe:
                continue
            kurven += 1
            if not zu:
                rueckwaerts = not rueckwaerts
            for anfang, ende in laeufe:
                idx = np.arange(anfang, ende + 1)
                idx = idx[np.isfinite(x[idx]) & np.isfinite(z[idx])]
                if len(idx) < 2:
                    continue
                raum = np.column_stack([x[idx], y[idx], z[idx]])
                behalten = _vereinfacht3d(raum)
                x0, y0, z0 = (float(v) for v in raum[behalten[0]])
                laenge += _verbinden(punkte, x0, y0, z0, w, raster)
                for i in behalten[1:]:
                    punkt = bn.Punkt(False, float(raum[i, 0]), float(raum[i, 1]), float(raum[i, 2]))
                    laenge += bn.weg(punkte[-1], punkt)
                    punkte.append(punkt)
                z_min = min(z_min, float(np.min(raum[:, 2])))
    if not punkte:
        return None
    letzter = punkte[-1]
    punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
    zeit = bn.zeit(punkte, w.vorschub if w.vorschub > 0 else 1000.0, w.eintauchen or None)
    return Schlichtbahn(
        punkte, kurven, laengs_u, abstand, z_min, laenge, zeit, 0, False, 0, flaeche=True
    )


def _abstandsfeld(raster, maske):
    """mm je Knoten: der kürzeste Weg auf der Hüllfläche – im Raum gemessen, über die Nachbarn
    bis zum Rösselsprung (16 Richtungen: höchstens 2,7 % zu lang, die Ringe also eher enger) –
    von außerhalb der `maske` (dort 0). Zeile für Zeile hin und zurück, bis sich nichts mehr
    ändert; in einer Zeile entlang mit der laufenden Summe der Schritte (der Weg längs der Zeile
    ist ihre Summe: das Minimum über alle Anfänge in einem Zug)."""
    xs, ys = raster.xs, raster.ys
    sx, sy = float(xs[1] - xs[0]), float(ys[1] - ys[0])
    z = np.where(np.isfinite(raster.z), raster.z, np.nan)
    nx, ny = z.shape
    d = np.where(maske, np.inf, 0.0)

    def schritt(z1, z2, di, dj):
        dz = np.nan_to_num(z2 - z1, nan=0.0)  # neben dem Teil: eben
        return np.sqrt((di * sx) ** 2 + (dj * sy) ** 2 + dz * dz)

    laengs = schritt(z[:, :-1], z[:, 1:], 0, 1)
    summe = np.concatenate([np.zeros((nx, 1)), np.cumsum(laengs, axis=1)], axis=1)
    nachbarn = ((1, 0), (1, 1), (1, -1), (1, 2), (1, -2), (2, 1), (2, -1))
    for _runde in range(ABSTAND_RUNDEN):
        vorher = d.copy()
        for vor in (1, -1):
            for i in range(nx) if vor == 1 else range(nx - 1, -1, -1):
                zeile = d[i]
                for di, dj in nachbarn:
                    k = i - vor * di
                    if not 0 <= k < nx:
                        continue
                    ziel, quelle = _verschoben(dj, ny)  # (i, j) von (k, j + dj)
                    kandidat = d[k, quelle] + schritt(z[i, ziel], z[k, quelle], di, dj)
                    np.minimum(zeile[ziel], kandidat, out=zeile[ziel])
                c = summe[i]
                np.minimum(zeile, c + np.minimum.accumulate(zeile - c), out=zeile)
                r = c[-1] - c
                np.minimum(zeile, r + np.minimum.accumulate((zeile - r)[::-1])[::-1], out=zeile)
        if np.array_equal(vorher, d):
            break
    return d


def _aequidistant(raster, w, abstand):
    """Die Bahn äquidistant (3D-Offset): Ringe vom Rand der gewählten Flächen nach innen, im
    Raum überall `abstand` auseinander – die Linien gleichen Abstands vom Rand
    (_abstandsfeld, Marching Squares), die Spitze auf der Hüllfläche aus dem Raster; flach wie
    steil derselbe Abstand, ohne Höhenlinien. Im Gleichlauf (das Material rechts), von Ring zu
    Ring der nächste Anfang. Der innerste Ring liegt höchstens einen halben Abstand unter dem
    höchsten Wert. None, wo nichts zu fräsen ist."""
    from . import raeumen_bahn as rb

    maske = raster.gewaehlt
    if not maske.any():
        return None
    feld = _abstandsfeld(raster, maske)
    zelle = float(max(raster.xs[1] - raster.xs[0], raster.ys[1] - raster.ys[0]))
    hoechst = float(np.max(feld[maske]))
    erste = min(0.6 * zelle, 0.5 * hoechst)
    letzte = max(erste, hoechst - 0.5 * abstand)
    anzahl = int(math.ceil((letzte - erste) / abstand - 1e-9)) + 1
    punkte = []
    laenge = 0.0
    ringe = 0
    z_min = math.inf
    for stufe in np.linspace(erste, letzte, anzahl):
        stuecke = []
        for linie, geschlossen in rb._hoehenlinien(feld, raster.xs, raster.ys, float(stufe)):
            behalten = raster.bei(maske, linie[:, 0], linie[:, 1])
            for teil, zu in _stuecke(linie, geschlossen, behalten):
                if len(teil) >= 2:
                    stuecke.append((_gerichtet(teil, zu, raster, w.gleichlauf), zu))
        if not stuecke:
            continue
        ringe += 1
        while stuecke:
            ort = (punkte[-1].x, punkte[-1].y) if punkte else tuple(stuecke[0][0][0])
            abstaende = [
                (
                    float(np.min(np.hypot(t[:, 0] - ort[0], t[:, 1] - ort[1])))
                    if zu
                    else math.hypot(t[0][0] - ort[0], t[0][1] - ort[1])
                )
                for t, zu in stuecke
            ]
            teil, zu = stuecke.pop(int(np.argmin(abstaende)))
            if zu:
                i = int(np.argmin(np.hypot(teil[:, 0] - ort[0], teil[:, 1] - ort[1])))
                teil = np.vstack([np.roll(teil, -i, axis=0), np.roll(teil, -i, axis=0)[:1]])
            with np.errstate(invalid="ignore"):
                z = _bilinear(raster, teil[:, 0], teil[:, 1])
            gut = np.isfinite(z)
            for anfang, ende in _laeufe(gut, z, w.schritt):
                raum = np.column_stack([teil[anfang : ende + 1], z[anfang : ende + 1]])
                raum = raum[np.isfinite(raum[:, 2])]
                if len(raum) < 2:
                    continue
                behalten = _vereinfacht3d(raum)
                x0, y0, z0 = (float(v) for v in raum[behalten[0]])
                laenge += _verbinden(punkte, x0, y0, z0, w, raster)
                for k in behalten[1:]:
                    punkt = bn.Punkt(False, float(raum[k, 0]), float(raum[k, 1]), float(raum[k, 2]))
                    laenge += bn.weg(punkte[-1], punkt)
                    punkte.append(punkt)
                z_min = min(z_min, float(np.min(raum[:, 2])))
    # Die Grate: Wo die Ringe beider Seiten an einem flachen Grat des Abstandsfelds enden (die
    # Mitte eines Rechtecks), liegt der letzte Ring um feld − Stufe neben dem Grat – mehr als ein
    # halber Abstand, und zwischen beiden Seiten bliebe mehr als ein Abstand. Dort einmal den
    # Grat entlang.
    for x, y in _grate(feld, maske, raster, np.linspace(erste, letzte, anzahl), abstand):
        with np.errstate(invalid="ignore"):
            z = _bilinear(raster, x, y)
        raum = np.column_stack([x, y, z])
        raum = raum[np.isfinite(raum[:, 2])]
        if len(raum) < 2:
            continue
        behalten = _vereinfacht3d(raum)
        x0, y0, z0 = (float(v) for v in raum[behalten[0]])
        laenge += _verbinden(punkte, x0, y0, z0, w, raster)
        for k in behalten[1:]:
            punkt = bn.Punkt(False, float(raum[k, 0]), float(raum[k, 1]), float(raum[k, 2]))
            laenge += bn.weg(punkte[-1], punkt)
            punkte.append(punkt)
        z_min = min(z_min, float(np.min(raum[:, 2])))
    if not punkte:
        return None
    letzter = punkte[-1]
    punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
    zeit = bn.zeit(punkte, w.vorschub if w.vorschub > 0 else 1000.0, w.eintauchen or None)
    return Schlichtbahn(
        punkte, ringe, True, abstand, z_min, laenge, zeit, 0, False, 0, aequidistant=True
    )


def _grate(feld, maske, raster, stufen, abstand):
    """[(x, y)] – die Linien längs der flachen Grate des Abstandsfelds `feld`, an denen der
    nächste Ring darunter mehr als einen halben `abstand` entfernt liegt: der Grat (in einer der
    vier Richtungen nicht niedriger als beide Nachbarn), längs flacher als GRAT_STEIGUNG, zu
    Linien verkettet wie beim Bleistift."""
    from . import bleistift_bahn as bb

    xs, ys = raster.xs, raster.ys
    sx, sy = float(xs[1] - xs[0]), float(ys[1] - ys[0])
    f = np.where(maske, feld, -np.inf)
    kamm = np.zeros(f.shape, dtype=bool)
    for di, dj in bb.RICHTUNGEN:
        vor = np.nan_to_num(bb._verschoben(f, di, dj), nan=-np.inf)
        zurueck = np.nan_to_num(bb._verschoben(f, -di, -dj), nan=-np.inf)
        kamm |= (f >= vor) & (f >= zurueck) & ((f > vor) | (f > zurueck))
    unter = stufen[np.clip(np.searchsorted(stufen, feld, side="right") - 1, 0, len(stufen) - 1)]
    gx, gy = np.gradient(np.where(maske, feld, 0.0), sx, sy)
    grat = kamm & maske & (feld - unter > 0.5 * abstand) & (np.hypot(gx, gy) < GRAT_STEIGUNG)
    linien = []
    for zellen, _zu in bb._linien(grat):
        if len(zellen) < 2:
            continue
        ij = np.array(zellen)
        linien.append((xs[ij[:, 0]], ys[ij[:, 1]]))
    return linien


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
    netz_alle, netz_rest, netz_gewaehlt = _netze(form_teil, flaechen, toleranz)
    geformt = w.form.mit_aufmass(max(w.aufmass, 0.0))
    abstand = zeilenabstand(w.form, w.grathoehe)
    raster = None
    vorweg = ([], 0.0, 0, math.inf)
    steil_flach = 0 < w.grenzwinkel < 90
    richtungen = {
        "x": (True,),
        "y": (False,),
        SPIRALE: (SPIRALE,),
        FLAECHE: (FLAECHE,),
        AEQUI: (AEQUI,),
    }.get(w.richtung, (True, False, SPIRALE, FLAECHE, AEQUI) if steil_flach else (True, False))
    if steil_flach or {SPIRALE, FLAECHE, AEQUI} & set(richtungen) or w.davor is not None:
        raster = _raster(netz_alle, netz_rest, geformt, box, w, netz_gewaehlt)
    if w.davor is not None:
        maske, _rest_mm = _rest(raster, netz_alle, w, abstand)
        raster.gewaehlt = raster.gewaehlt & maske
        if not raster.gewaehlt.any():
            raise ValueError(tr("s3.fehler.kein_rest"))
    if steil_flach and set(richtungen) - {FLAECHE, AEQUI}:  # die beiden ohne Höhenlinien
        vorweg = _hoehenlinien(raster, w, abstand)
    beste = None
    for richtung in richtungen:
        if richtung == SPIRALE:
            bahn = _spirale(raster, w, abstand, vorweg)
        elif richtung == AEQUI:
            bahn = _aequidistant(raster, w, abstand)
        elif richtung == FLAECHE:
            # Entlang der Fläche liegen die Kurven im Raum gleich weit auseinander, flach wie
            # steil – ohne Höhenlinien; längs u und längs v, die schnellere.
            bahn = None
            for laengs_u in (True, False):
                kandidat = _flaeche_entlang(
                    form_teil, flaechen, raster, w, abstand, laengs_u, geformt
                )
                if kandidat is not None and (bahn is None or kandidat.zeit < bahn.zeit):
                    bahn = kandidat
        else:
            bahn = _eine_richtung(
                netz_alle, netz_rest, box, w, richtung, abstand, geformt, raster, vorweg
            )
        if bahn is not None and (beste is None or bahn.zeit < beste.zeit):
            beste = bahn
    if beste is None:
        raise ValueError(tr("s3.fehler.nichts"))
    return beste
