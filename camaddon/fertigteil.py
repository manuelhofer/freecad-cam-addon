# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Fertigteil einer Aufspannung als Rohteil der nächsten (W-029; Manuel, 2026-10-18: „sagen
wir mal wir haben jetzt den C ring ... außen fertig bearbeitet .. und innen und die nut ist auch
fertig ... kann man dann generieren lassen ... ein neues teil im selben ordner mit dem namen ...
aufspannung 1 fertigteil ... so das man das dann nutzen kann als rohteil für die zweite
aufspannung ?“).

Aus dem Materialstand nach allen Operationen eines Jobs (materialstand: je Rasterzelle von oben
die Höhe des Materials) wird ein Körper: oben je Zelle ihre Höhe, unten die Unterkante des
Rohteils, dazwischen senkrechte Wände. Wasserdicht: An jeder Ecke des Rasters werden die Wände an
allen Höhen geteilt, die dort vorkommen – keine T-Stöße (netz_aus_hoehen). Das Netz wird
vereinfacht (ebene Bereiche zu großen Dreiecken, das Volumen bleibt bis auf 0,02 %), dann ein
Solid (stl_teil.koerper), die ebenen Dreiecke zu Flächen zusammengefasst (removeSplitter). Genau
bis aufs Raster des Materialstands
(SCHRITT, 0,5 mm): Schräge Wände und kleine Bohrungen zeigen sich als Treppen.

Im Dokument liegt der Körper dort, wo das Original-Teil liegt – im Job ist das Teil ein Klon, um
Nullpunkt und Aufspannung verschoben (lage). „Bearbeitung“ nimmt ihn dann für die nächste
Aufspannung als „Teil aus dem Dokument“, und sein Klon wandert wie das Teil
(gui_bearbeitung._nullpunkt_setzen). Dazu eine eigene Datei im Ordner des Dokuments
(datei_speichern). Das Fertigteil merkt sich seinen Job (AusJob) und die Aufspannung: Noch einmal
gerechnet, bekommt es die neue Form; der Job, dessen Rohteil es ist, heißt Aufspannung 2.

Der Körper rechnet auf einem Nebenrechner (koerper_rechnen) – am C-Ring rund 17 000 Zellen.

**Die Stange** (4 Achsen, Rundachse): Ihr Abtrag steht im Fenster „Auf der Maschine prüfen“ als
Radien je Stelle längs und Winkel rundum (restmaterial.Stange, Raster 0,5 mm und 1°). Daraus ein
Netz um die Achse mit je einer Scheibe hinten und vorn (netz_aus_radien), wo das Teil fertig ist
unter seine Oberfläche gerückt (nur_rest_radien), vereinfacht bis aufs Volumen 0,1 % – rund
hält es 0,02 % nie –, mit dem Teil vereinigt und auf die Stange beschnitten (koerper_aus_radien,
auf einem Nebenrechner radien_rechnen).
Läuft ohne Oberfläche.
"""

import math
import os

import numpy as np

from .sprache import tr

# Vereinfachen (Mesh.decimate): so viele Dreiecke weg, der Reihe nach versucht, bis das Volumen
# höchstens VOLUMEN_SPIEL vom Raster abweicht (seine Toleranz hält es nicht: am Testteil nahm es
# mit 99 % das Volumen um 0,4 % zu, mit 95 % um 0,006 %); keine passt: das Netz, wie es ist.
VEREINFACHEN = (0.97, 0.95, 0.9)
VOLUMEN_SPIEL = 2e-4  # Anteil
# Die würfelige Hülle im Raum (blockflaechen) ist fast überall eben: Sie verträgt viel mehr.
VEREINFACHEN_RAUM = (0.995, 0.99, 0.98, 0.95, 0.9)
GLEICH = 1e-6  # mm – so gleich gelten zwei Höhen
UEBER_ECK_RUNDEN = 100  # so oft höchstens wird angehoben (ohne_ueber_eck)
IM_TEIL_SPIEL = 0.05  # mm – so viel tiefer als das Teil zählt noch nicht als „ins Teil“ (im_teil)


def ohne_ueber_eck(h, unten):
    """Die Höhen so angehoben, dass sich nirgends zwei Zellen mit Material nur über Eck berühren:
    In jedem 2 × 2-Block, in dem zwei diagonale Zellen über beiden anderen stehen, kommt die
    höhere der beiden anderen auf die Höhe der niedrigeren diagonalen. Sonst teilten sich vier
    Wände eine senkrechte Kante – das Netz wäre nicht mannigfaltig, und FreeCAD machte daraus nur
    eine Hülle statt eines Körpers (am C-Ring zwischen Schlitz und Bohrung). Nur mehr Material:
    Als Rohteil ist das die sichere Seite (dort fräst es höchstens Luft). −inf wie `unten`; was
    nicht über `unten` steht, kommt als −inf zurück."""
    z = np.where(np.isfinite(h) & (h > unten + GLEICH), h, float(unten))
    for _ in range(UEBER_ECK_RUNDEN):
        a, b, c, d = z[:-1, :-1], z[1:, :-1], z[1:, 1:], z[:-1, 1:]  # im Kreis um die Ecke
        ac_hoch, bd_hoch = np.minimum(a, c), np.minimum(b, d)
        ac_tief, bd_tief = np.maximum(a, c), np.maximum(b, d)
        ac_ueber = ac_hoch > bd_tief + GLEICH
        bd_ueber = bd_hoch > ac_tief + GLEICH
        if not (ac_ueber.any() or bd_ueber.any()):
            break
        neu = z.copy()
        i, j = np.nonzero(ac_ueber)
        b_hoeher = b[i, j] >= d[i, j]  # b: Zelle (i + 1, j), d: (i, j + 1)
        ziel = (np.where(b_hoeher, i + 1, i), np.where(b_hoeher, j, j + 1))
        np.maximum.at(neu, ziel, ac_hoch[i, j])
        i, j = np.nonzero(bd_ueber)
        a_hoeher = a[i, j] >= c[i, j]  # a: Zelle (i, j), c: (i + 1, j + 1)
        ziel = (np.where(a_hoeher, i, i + 1), np.where(a_hoeher, j, j + 1))
        np.maximum.at(neu, ziel, bd_hoch[i, j])
        z = neu
    return np.where(z > unten + GLEICH, z, -np.inf)


def netz_aus_hoehen(x, y, h, unten):
    """(Punkte (n, 3), Dreiecke (m, 3)) – das geschlossene Netz des Materials über dem Raster:
    Zellmitten `x` (n) und `y` (m) im gleichen Abstand, je Zelle die Höhe `h` (−inf oder nicht über
    `unten`: kein Material), unten bei `unten`. Je Zelle mit Material ihr Deckel und ihr Boden,
    zwischen Nachbarn verschiedener Höhe (und zum Rand hin) eine senkrechte Wand – an jeder Ecke
    an allen Höhen geteilt, die dort vorkommen. Außen zeigen alle Dreiecke nach außen. Zellen,
    die sich nur über Eck berührten, sind vorher angehoben (ohne_ueber_eck)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    h = ohne_ueber_eck(np.asarray(h, dtype=float), unten)
    n, m = h.shape
    sx = float(x[1] - x[0]) if n > 1 else 1.0
    sy = float(y[1] - y[0]) if m > 1 else 1.0
    xc = x[0] - 0.5 * sx + sx * np.arange(n + 1)
    yc = y[0] - 0.5 * sy + sy * np.arange(m + 1)
    material = np.isfinite(h) & (h > unten + GLEICH)
    hoehe = np.where(material, h, unten)  # ohne Material: unten (dorthin geht die Wand)

    punkte = []
    index = {}

    def punkt(k, l_, z):
        schluessel = (k, l_, round(float(z), 6))
        i = index.get(schluessel)
        if i is None:
            i = index[schluessel] = len(punkte)
            punkte.append((xc[k], yc[l_], float(z)))
        return i

    dreiecke = []
    # Deckel und Böden: je Zelle zwei Dreiecke, oben gegen den Uhrzeigersinn (von oben gesehen).
    for i, j in zip(*np.nonzero(material), strict=True):
        z = hoehe[i, j]
        a, b, c, d = punkt(i, j, z), punkt(i + 1, j, z), punkt(i + 1, j + 1, z), punkt(i, j + 1, z)
        dreiecke += [(a, b, c), (a, c, d)]
        a, b, c, d = (
            punkt(i, j, unten),
            punkt(i + 1, j, unten),
            punkt(i + 1, j + 1, unten),
            punkt(i, j + 1, unten),
        )
        dreiecke += [(a, c, b), (a, d, c)]

    def hoehe_bei(i, j):
        if 0 <= i < n and 0 <= j < m and material[i, j]:
            return float(hoehe[i, j])
        return float(unten)

    # Die Höhen an jeder Ecke des Rasters: die der Zellen ringsum (unten immer dabei).
    def hoehen_an(k, l_):
        werte = {float(unten)}
        for i in (k - 1, k):
            for j in (l_ - 1, l_):
                werte.add(round(hoehe_bei(i, j), 6))
        return sorted(werte)

    ecken = {}

    def an_ecke(k, l_):
        werte = ecken.get((k, l_))
        if werte is None:
            werte = ecken[(k, l_)] = hoehen_an(k, l_)
        return werte

    def wand(c1, c2, tief, hoch, innen_links):
        """Die Wand auf der Kante c1 → c2 (Ecken (k, l)) von `tief` bis `hoch`, als Leiter an
        beiden Ecken geteilt; `innen_links`: das Material liegt links der Richtung c1 → c2 (von
        oben gesehen) – dann zeigt die Wand nach rechts hinaus."""
        links = [z for z in an_ecke(*c1) if tief - GLEICH <= z <= hoch + GLEICH]
        rechts = [z for z in an_ecke(*c2) if tief - GLEICH <= z <= hoch + GLEICH]
        a = [punkt(*c1, z) for z in links]
        b = [punkt(*c2, z) for z in rechts]
        # Die Leiter von unten nach oben: je Schritt eine Sprosse an der Seite, die tiefer ist.
        i = j = 0
        neu = []
        while i < len(a) - 1 or j < len(b) - 1:
            if j >= len(b) - 1 or (i < len(a) - 1 and links[i + 1] <= rechts[j + 1]):
                neu.append((a[i], b[j], a[i + 1]))
                i += 1
            else:
                neu.append((a[i], b[j], b[j + 1]))
                j += 1
        if not innen_links:
            neu = [(p, r, q) for p, q, r in neu]
        dreiecke.extend(neu)

    # Wände quer zu x: zwischen Zelle (i − 1, j) und (i, j) auf der Linie xc[i], von yc[j] nach
    # yc[j + 1].
    for i in range(n + 1):
        for j in range(m):
            links_h, rechts_h = hoehe_bei(i - 1, j), hoehe_bei(i, j)
            if abs(links_h - rechts_h) <= GLEICH:
                continue
            tief, hoch = min(links_h, rechts_h), max(links_h, rechts_h)
            # Richtung +y: links ist −x. Das Material (die höhere Zelle) links: Wand nach +x.
            wand((i, j), (i, j + 1), tief, hoch, links_h > rechts_h)
    # Wände quer zu y: zwischen Zelle (i, j − 1) und (i, j) auf der Linie yc[j], von xc[i] nach
    # xc[i + 1]; Richtung +x, links ist +y.
    for j in range(m + 1):
        for i in range(n):
            vorne_h, hinten_h = hoehe_bei(i, j - 1), hoehe_bei(i, j)
            if abs(vorne_h - hinten_h) <= GLEICH:
                continue
            tief, hoch = min(vorne_h, hinten_h), max(vorne_h, hinten_h)
            wand((i, j), (i + 1, j), tief, hoch, hinten_h > vorne_h)
    return np.array(punkte, dtype=float).reshape(-1, 3), np.array(dreiecke, dtype=np.int64)


def koerper_aus_hoehen(x, y, h, unten, teil=None, rohteil=None):
    """Der Körper (Part.Shape, ein Solid wenn möglich) aus dem Raster wie netz_aus_hoehen –
    vereinfacht (VEREINFACHEN, bis aufs VOLUMEN_SPIEL), ebene Dreiecke zu Flächen
    zusammengefasst; mit `teil` (das Teil in denselben Koordinaten) mit ihm vereinigt
    (mit_teil, nur_rest), mit `rohteil` aufs Rohteil beschnitten (im_rohteil)."""
    if teil is not None:
        h = nur_rest(x, y, h, teil)
    punkte, dreiecke = netz_aus_hoehen(x, y, h, unten)
    if not len(dreiecke):
        if teil is not None:
            return teil.Solids[0] if len(teil.Solids) == 1 else teil
        raise ValueError(tr("ft.fehler.leer"))
    return im_rohteil(_aus_dem_netz(punkte, dreiecke, teil), rohteil)


def _aus_dem_netz(punkte, dreiecke, teil, spiel=None, stufen=None):
    """Der Körper aus dem Netz – vereinfacht (der Reihe nach `stufen`, ohne: VEREINFACHEN), bis das
    Volumen höchstens `spiel` (Anteil; ohne: VOLUMEN_SPIEL) abweicht und das Netz geschlossen
    bleibt, ebene Dreiecke zu Flächen, mit `teil` vereinigt."""
    import Mesh

    from . import stl_teil

    netz = Mesh.Mesh()
    netz.addFacets([[tuple(punkte[k]) for k in d] for d in dreiecke])
    voll = float(netz.Volume)
    for anteil in stufen or VEREINFACHEN:
        kopie = netz.copy()
        with _ohne_fehler():
            kopie.decimate(0.001, anteil)
            # Auch geschlossen und mannigfaltig: An einer dünnen Haut (1 mm Rohteil über dem
            # Schwenkteil) ließ 97 % das Volumen stehen, aber das Netz war offen – kein Körper.
            if (
                abs(float(kopie.Volume) - voll) <= (spiel or VOLUMEN_SPIEL) * abs(voll)
                and kopie.isSolid()
                and not kopie.hasNonManifolds()
            ):
                netz = kopie
                break
    form = stl_teil.koerper(netz)
    with _ohne_fehler():
        zusammen = form.removeSplitter()
        if zusammen is not None and not zusammen.isNull():
            form = zusammen
    return mit_teil(form, teil) if teil is not None else form


def im_rohteil(form, rohteil):
    """Der Körper aufs Rohteil beschnitten: Das Raster reicht eine halbe Zelle über dessen Rand
    hinaus (am runden Rohteil in Stufen) – danach ist der Rand genau. Geht es nicht (OCC), der
    Körper, wie er war."""
    if rohteil is None:
        return form
    with _ohne_fehler():
        innen = form.common(rohteil).removeSplitter()
        if len(innen.Solids) == 1 and innen.isValid():
            return innen.Solids[0]
    return form


def nur_rest(x, y, h, teil):
    """Die Höhen ohne das fertige Teil: Wo eine Zelle das Teil trägt und nicht höher steht als
    seine Oberkante (bis IM_TEIL_SPIEL), reicht sie nur noch bis zur Unterkante des Teils dort –
    das Teil selbst kommt aus mit_teil, genau. Sonst stünde an jeder fertigen Wand die halbe
    Zelle über, deren Mitte gerade drinnen lag: am C-Ring lauter Stufen an den Wänden. Wo mehr
    steht als das Teil (Aufmaß, noch nicht gefräst), bleibt die Zelle, wie sie ist."""
    from . import hoehenfeld as hf
    from . import vierachs_huelle as vh

    oben = hf.hoehen(vh.vernetze(teil), x, y)
    gespiegelt = teil.mirror(_vektor(0, 0, 0), _vektor(0, 0, 1))
    unterkante = -hf.hoehen(vh.vernetze(gespiegelt), x, y)
    h = np.array(h, dtype=float)
    fertig = np.isfinite(oben) & np.isfinite(h) & (h <= oben + IM_TEIL_SPIEL)
    h[fertig] = np.where(np.isfinite(unterkante[fertig]), unterkante[fertig], -np.inf)
    return h


def _vektor(x, y, z):
    import FreeCAD

    return FreeCAD.Vector(x, y, z)


def mit_teil(form, teil):
    """Der Körper aus dem Raster mit dem Teil vereinigt: Was gefräst ist, enthält das Teil
    immer ganz – so sind seine Flächen genau, nicht die Stufen des Rasters, und an keiner Wand
    fehlt die halbe Zelle, deren Mitte gerade draußen lag (am C-Ring 1,7 % des Teils). Stufen
    bleiben nur im Material, das stehen blieb. Geht es nicht (OCC), der Körper, wie er war."""
    with _ohne_fehler():
        vereint = form.fuse(teil).removeSplitter()
        if len(vereint.Solids) == 1 and vereint.isValid():
            return vereint.Solids[0]
    return form


def im_teil(x, y, h, teil, anfang=None):
    """So viele Zellen des Rasters stehen tiefer als die Oberkante des Teils (mehr als
    IM_TEIL_SPIEL) – ohne die am Rand des Teils, deren Mitte mal knapp drinnen, mal draußen
    liegt, und mit `anfang` (die Höhen des Rohteils im Materialstand) ohne die, die schon dort
    fehlten (materialstand._eingezogen zieht ein rundes Rohteil um eine Zelle ein). Mehr als 0: Die Bahnen schneiden ins Teil (am C-Ring „Wände schlichten T1“ in der
    Nut, W-029) – das Fertigteil hat dort das Teil (mit_teil), der Befehl sagt es."""
    from . import hoehenfeld as hf
    from . import vierachs_huelle as vh

    oben = hf.hoehen(vh.vernetze(teil), x, y)
    with np.errstate(invalid="ignore"):  # −inf − (−inf) neben dem Teil: kein Rand, nicht gleich
        return _im_teil(oben, h, anfang)


def _im_teil(oben, h, anfang):
    rest = np.where(np.isfinite(h), h, -np.inf)
    unter = np.isfinite(oben) & (rest < oben - IM_TEIL_SPIEL)
    if anfang is not None:
        unter &= np.where(np.isfinite(anfang), anfang, -np.inf) >= oben - IM_TEIL_SPIEL
    gleich = np.zeros_like(unter)
    gleich[1:-1, 1:-1] = (
        (np.abs(oben[2:, 1:-1] - oben[1:-1, 1:-1]) < IM_TEIL_SPIEL)
        & (np.abs(oben[:-2, 1:-1] - oben[1:-1, 1:-1]) < IM_TEIL_SPIEL)
        & (np.abs(oben[1:-1, 2:] - oben[1:-1, 1:-1]) < IM_TEIL_SPIEL)
        & (np.abs(oben[1:-1, :-2] - oben[1:-1, 1:-1]) < IM_TEIL_SPIEL)
    )
    return int(np.sum(unter & gleich))


class _ohne_fehler:
    """Ein Schritt, der nur verschönert: Scheitert er (OCC), bleibt es, wie es war."""

    def __enter__(self):
        return self

    def __exit__(self, art, fehler, spur):
        return art is not None and issubclass(art, Exception)


def koerper_rechnen(x, y, h, unten, teil=None, anfang=None, rohteil=None):
    """Auf einem Nebenrechner: (koerper_aus_hoehen() als nebenrechner.Form, im_teil()) – das
    Teil kommt als nebenrechner.Form und ist hier wieder eine Form."""
    from . import nebenrechner as nr

    form = koerper_aus_hoehen(x, y, h, unten, teil, rohteil)
    return nr.Form.von(form), (im_teil(x, y, h, teil, anfang) if teil is not None else 0)


# --- Die Stange (4 Achsen) ---------------------------------------------------------------------

R_MINDESTENS = 0.2  # mm – kleiner wird kein Radius im Netz (an der Achse träfen sich die Dreiecke)
EINZUG = 1.0  # mm – so weit unter das fertige Teil rückt ein Radius, wo es fertig ist
# Vereinfachen am runden Netz: Mit 0,02 % behielt es am Prüfteil alle 58.320 Dreiecke, und die
# Vereinigung mit dem Teil rechnete Minuten; mit 0,1 % blieben 2.916 – 2,4 s.
VOLUMEN_SPIEL_STANGE = 1e-3


def netz_aus_radien(a, phi, r, laengs, radial):
    """(Punkte, Dreiecke) des Netzes um die Stange: je Stelle längs a[i] und Winkel phi[j] (rad,
    cos φ · U + sin φ · V wie vierachs_huelle.rahmen) der Punkt im Abstand r[i, j] von der Achse
    (nie unter R_MINDESTENS), dazu hinten und vorn je eine Scheibe um die Achse. Geschlossen und
    nach außen gerichtet."""
    from . import vierachs_huelle as vh

    l_, u_, v_ = vh.rahmen(laengs, radial)
    a = np.asarray(a, dtype=float)
    phi = np.asarray(phi, dtype=float)
    r = np.asarray(r, dtype=float)
    r = np.maximum(np.where(np.isfinite(r), r, R_MINDESTENS), R_MINDESTENS)
    na, nphi = r.shape
    richtung = np.cos(phi)[:, None] * u_ + np.sin(phi)[:, None] * v_
    punkte = (a[:, None, None] * l_ + r[:, :, None] * richtung[None, :, :]).reshape(-1, 3)
    hinten, vorn = len(punkte), len(punkte) + 1
    punkte = np.vstack([punkte, a[0] * l_, a[-1] * l_])

    def k(i, j):
        return i * nphi + (j % nphi)

    i, j = np.meshgrid(np.arange(na - 1), np.arange(nphi), indexing="ij")
    i, j = i.ravel(), j.ravel()
    p00, p01, p11, p10 = k(i, j), k(i, j + 1), k(i + 1, j + 1), k(i + 1, j)
    # Nach außen: (i, j) → (i, j+1) → (i+1, j+1) – längs mal rundum zeigte zur Achse.
    mantel = np.concatenate([np.stack([p00, p01, p11], axis=1), np.stack([p00, p11, p10], axis=1)])
    jj = np.arange(nphi)
    scheibe_hinten = np.stack([np.full(nphi, hinten), k(0, jj + 1), k(0, jj)], axis=1)
    scheibe_vorn = np.stack([np.full(nphi, vorn), k(na - 1, jj), k(na - 1, jj + 1)], axis=1)
    return punkte, np.vstack([mantel, scheibe_hinten, scheibe_vorn]).astype(np.int64)


def nur_rest_radien(r, teil_r, spiel=IM_TEIL_SPIEL):
    """Die Radien ohne das fertige Teil (wie nur_rest): Wo ein Strahl das Teil vor der Achse trägt
    (`teil_r`, restmaterial.teilradien) und nicht weiter draußen endet als das Teil (bis `spiel`),
    rückt er EINZUG darunter – das Teil selbst kommt aus mit_teil, genau. Wo mehr steht (Aufmaß,
    noch nicht gefräst), bleibt er."""
    r = np.array(r, dtype=float)
    teil_r = np.asarray(teil_r, dtype=float)
    with np.errstate(invalid="ignore"):
        fertig = np.isfinite(teil_r) & (teil_r > 0) & (r <= teil_r + spiel)
    r[fertig] = np.maximum(teil_r[fertig] - EINZUG, R_MINDESTENS)
    return r


def koerper_aus_radien(a, phi, r, laengs, radial, teil=None, teil_r=None, rohteil=None):
    """Der Körper aus den Radien der Stange (netz_aus_radien) – vereinfacht bis aufs
    VOLUMEN_SPIEL_STANGE; mit `teil` und `teil_r` (seine Radien auf denselben Strahlen) nur der
    Rest (nur_rest_radien) und mit dem Teil vereinigt, mit `rohteil` auf die Stange beschnitten."""
    if teil is not None and teil_r is not None:
        r = nur_rest_radien(r, teil_r)
    punkte, dreiecke = netz_aus_radien(a, phi, r, laengs, radial)
    form = _aus_dem_netz(punkte, dreiecke, teil, VOLUMEN_SPIEL_STANGE)
    return im_rohteil(form, rohteil)


def erste_stelle(a, teil, laengs):
    """Der Index der ersten Stelle längs (a, aufsteigend), die nicht hinter dem Teil liegt – dort
    wird die Stange abgestochen gedacht (die Rückseite des Teils, eine Stelle des Rasters davor,
    wenn sie zwischen zwei Stellen fällt)."""
    from . import vierachs_huelle as vh

    l_ = np.asarray(laengs, dtype=float)
    l_ = l_ / np.linalg.norm(l_)
    punkte = vh.vernetze(teil).punkte
    hinten = float(np.min(np.asarray(punkte, dtype=float) @ l_))
    a = np.asarray(a, dtype=float)
    return max(0, int(np.searchsorted(a, hinten + 1e-6, side="right")) - 1)


def im_teil_radien(a, phi, r, teil_r):
    """Die Fläche (mm², auf dem Teil gemessen), auf der die Stange tiefer als das Teil liegt –
    mehr als IM_TEIL_SPIEL (wie im_teil)."""
    a = np.asarray(a, dtype=float)
    teil_r = np.asarray(teil_r, dtype=float)
    with np.errstate(invalid="ignore"):
        tief = np.isfinite(teil_r) & (teil_r > 0) & (np.asarray(r) < teil_r - IM_TEIL_SPIEL)
    if not tief.any() or len(a) < 2 or len(phi) < 2:
        return 0.0
    schritt_a = float(a[1] - a[0])
    schritt_phi = float(phi[1] - phi[0])
    return float(np.sum(teil_r[tief]) * schritt_a * schritt_phi)


def radien_rechnen(a, phi, r, laengs, radial, teil=None, teil_r=None, rohteil=None):
    """Auf einem Nebenrechner: (koerper_aus_radien() als nebenrechner.Form, im_teil_radien()) –
    Teil und Stange kommen als nebenrechner.Form."""
    from . import nebenrechner as nr

    form = koerper_aus_radien(a, phi, r, laengs, radial, teil, teil_r, rohteil)
    flaeche = im_teil_radien(a, phi, r, teil_r) if teil_r is not None else 0.0
    return nr.Form.von(form), flaeche


# --- Räumlich (3+2, raum_material) -------------------------------------------------------------
#
# Der Rest nach allen Ebenen einer Aufspannung als Abschnitte auf senkrechten Strahlen
# (raum_material.Material.grenzen, je Strahl mehrere – unter einem Überhang): daraus Voxel in
# Schichten so dick wie das Raster, ihre würfelige Hülle (blockflaechen: dicht, jede Kante an zwei
# Dreiecken). Wo das Teil fertig ist, rückt sie EINZUG unter seine Oberfläche (nur_rest_raum), dann
# vereinfacht (VEREINFACHEN_RAUM), mit dem Teil vereinigt und aufs Rohteil beschnitten.


def schichten(z_von, z_bis, schritt):
    """Die Mitten der Schichten von z_von bis z_bis, je `schritt` dick."""
    anzahl = max(1, int(math.ceil((z_bis - z_von) / schritt - 1e-9)))
    dz = (z_bis - z_von) / anzahl
    return z_von + (np.arange(anzahl) + 0.5) * dz


def belegung_raum(grenzen, z):
    """(nx, ny, nz) bool: steht auf dem Strahl an der Höhe z (Mitte der Schicht) Material?"""
    unten = grenzen[..., 0][..., None]
    oben = grenzen[..., 1][..., None]
    with np.errstate(invalid="ignore"):
        return ((z >= unten) & (z <= oben)).any(axis=2)


def blockflaechen(voll, x, y, z):
    """(Punkte (m, 3), Dreiecke (t, 3)) der würfeligen Hülle der vollen Voxel mit den Mitten x, y,
    z: je Grenze zwischen vollem und leerem Voxel ein Viereck auf den Zellgrenzen, nach außen
    gerichtet, mit gemeinsamen Ecken – dicht. Ebene Bereiche fasst das Vereinfachen fast ohne
    Volumenfehler zusammen, removeSplitter danach zu großen Flächen: am Schwenkteil (332 000
    Dreiecke) 99,5 % weniger, der Körper in 0,1 s, mit dem Teil vereinigt in 0,2 s – die runde Hülle
    (Surface Nets, P-2026-10-24-19) brauchte 55 s, und stark vereinfacht war sie nicht mehr dicht.
    """

    def grenzen(c):
        h = float(c[1] - c[0]) if len(c) > 1 else 1.0
        innen = (c[:-1] + c[1:]) / 2
        aussen = np.concatenate([[c[0] - h / 2], innen, [c[-1] + h / 2]])
        return np.concatenate([[aussen[0] - h], aussen, [aussen[-1] + h]])  # dazu der Rand

    xs, ys, zs = grenzen(np.asarray(x)), grenzen(np.asarray(y)), grenzen(np.asarray(z))
    v = np.pad(voll, 1)
    nx, ny, nz = v.shape

    def nummer(i, j, k):  # die Ecke (i, j, k) bei xs[i], ys[j], zs[k]
        return (i * (ny + 1) + j) * (nz + 1) + k

    vierecke = []
    for achse in range(3):
        a = [slice(None)] * 3
        b = [slice(None)] * 3
        a[achse], b[achse] = slice(None, -1), slice(1, None)
        va, vb = v[tuple(a)], v[tuple(b)]
        i, j, k = np.nonzero(va != vb)
        innen = va[i, j, k]  # innen am Anfang: außen liegt in +achse
        if achse == 0:
            g = i + 1
            q = (nummer(g, j, k), nummer(g, j + 1, k), nummer(g, j + 1, k + 1), nummer(g, j, k + 1))
        elif achse == 1:
            g = j + 1
            q = (nummer(i, g, k), nummer(i, g, k + 1), nummer(i + 1, g, k + 1), nummer(i + 1, g, k))
        else:
            g = k + 1
            q = (nummer(i, j, g), nummer(i + 1, j, g), nummer(i + 1, j + 1, g), nummer(i, j + 1, g))
        q = np.stack(q, axis=1)
        vierecke.append(np.where(innen[:, None], q, q[:, ::-1]))
    q = np.concatenate(vierecke) if vierecke else np.zeros((0, 4), dtype=np.int64)
    benutzt, neu = np.unique(q.ravel(), return_inverse=True)
    q = neu.reshape(-1, 4)
    k = benutzt % (nz + 1)
    j = (benutzt // (nz + 1)) % (ny + 1)
    i = benutzt // ((nz + 1) * (ny + 1))
    punkte = np.stack([xs[i], ys[j], zs[k]], axis=1)
    return punkte, np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])


def _nachbarn(maske, n, wachsen):
    """Die Maske n Voxel weiter (wachsen) bzw. enger – je Schritt über die sechs Nachbarn."""
    m = maske.copy()
    for _ in range(max(0, int(n))):
        p = np.pad(m, 1, constant_values=not wachsen)
        teile = (
            p[2:, 1:-1, 1:-1], p[:-2, 1:-1, 1:-1], p[1:-1, 2:, 1:-1],
            p[1:-1, :-2, 1:-1], p[1:-1, 1:-1, 2:], p[1:-1, 1:-1, :-2],
        )  # fmt: skip
        for t in teile:
            m = (m | t) if wachsen else (m & t)
    return m


GUT_VERBUNDEN_RUNDEN = 20  # so oft höchstens füllt gut_verbunden() nach


def gut_verbunden(voll):
    """Die Voxel ohne Stellen, an denen sich zwei nur an einer Kante oder Ecke berühren: Dort
    gäben Surface Nets eine Kante an vier Dreiecken (nicht mannigfaltig, kein Solid). Je
    2 × 2-Quadrat mit nur einem diagonalen Paar kommt ein Voxel dazu, je 2 × 2 × 2-Würfel mit nur
    zwei gegenüberliegenden Ecken ebenso – lieber Material, wo keins ist (wie hoehen()). Gefunden
    am Rest in den runden Ecken einer Tasche, nachdem nur_rest_raum die Schale geleert hatte."""
    v = voll.copy()
    for _ in range(GUT_VERBUNDEN_RUNDEN):
        dazu = False
        for p, q in ((0, 1), (0, 2), (1, 2)):
            w = np.moveaxis(v, (p, q), (0, 1))  # eine Sicht: was hier gesetzt wird, steht in v
            a, b, c, d = w[:-1, :-1], w[1:, :-1], w[:-1, 1:], w[1:, 1:]
            eins = a & d & ~b & ~c
            zwei = b & c & ~a & ~d
            if eins.any() or zwei.any():
                dazu = True
                w[1:, :-1] |= eins
                w[:-1, :-1] |= zwei
        e = [v[i : v.shape[0] - 1 + i, j : v.shape[1] - 1 + j, k : v.shape[2] - 1 + k]
             for i in (0, 1) for j in (0, 1) for k in (0, 1)]  # fmt: skip
        gesetzt = sum(x.astype(np.int8) for x in e)
        for m, n in ((0, 7), (1, 6), (2, 5), (3, 4)):  # die vier Raumdiagonalen
            nur = (gesetzt == 2) & e[m] & e[n]
            if nur.any():
                dazu = True
                nachbar = m ^ 4  # die Ecke daneben längs x
                v[nachbar >> 2 : v.shape[0] - 1 + (nachbar >> 2),
                  (nachbar >> 1) & 1 : v.shape[1] - 1 + ((nachbar >> 1) & 1),
                  nachbar & 1 : v.shape[2] - 1 + (nachbar & 1)] |= nur  # fmt: skip
        if not dazu:
            break
    return v


def nur_rest_raum(voll, im_teil, schritt):
    """Die Voxel ohne das fertige Teil: im Teil bis EINZUG unter seiner Oberfläche leer – außer,
    wo daneben Rest steht (Aufmaß, nicht gefräst); das Teil selbst kommt aus mit_teil, genau.
    Sonst stünde an jeder fertigen Fläche die halbe Schicht über (wie nur_rest)."""
    n = max(1, int(math.ceil(EINZUG / schritt)))
    rest = voll & ~im_teil
    schale = im_teil & ~_nachbarn(im_teil, n, False)
    nah = _nachbarn(rest, n + 1, True)
    return voll & ~(schale & ~nah)


def raum_im_teil(voll, im_teil, schritt, x, y):
    """Die Fläche (mm², von oben), unter der Voxel im Teil fehlen – tiefer als eine Schicht unter
    seiner Oberfläche (wie im_teil): Die Bahnen schnitten ins Teil."""
    innen = _nachbarn(im_teil, 1, False)
    fehlt = (innen & ~voll).any(axis=2)
    return float(fehlt.sum()) * float(x[1] - x[0]) * float(y[1] - y[0])


def koerper_aus_abschnitten(
    grenzen, x, y, z_von, z_bis, schritt, teil_grenzen=None, teil=None, rohteil=None
):
    """(Körper, Fläche ins Teil in mm²) aus dem räumlichen Rest (raum_material.Material.grenzen auf
    den Strahlen x, y): Voxel, Surface Nets, vereinfacht bis aufs Volumen VOLUMEN_SPIEL_STANGE; mit
    `teil_grenzen` (das Teil auf denselben Strahlen, raum_material.abschnitte) und `teil` unter das
    fertige Teil gerückt und mit ihm vereinigt, aufs Rohteil beschnitten. ValueError ohne Rest."""
    z = schichten(z_von, z_bis, schritt)
    voll = belegung_raum(grenzen, z)
    if not voll.any():
        raise ValueError(tr("ft.fehler.keine_operation"))
    flaeche = 0.0
    if teil_grenzen is not None:
        im_teil = belegung_raum(teil_grenzen, z)
        flaeche = raum_im_teil(voll, im_teil, schritt, x, y)
        voll = nur_rest_raum(voll, im_teil, schritt)
    punkte, dreiecke = blockflaechen(gut_verbunden(voll), x, y, z)
    form = _aus_dem_netz(punkte, dreiecke, teil, VOLUMEN_SPIEL_STANGE, VEREINFACHEN_RAUM)
    return im_rohteil(form, rohteil), flaeche


def abschnitte_rechnen(
    grenzen, x, y, z_von, z_bis, schritt, teil_grenzen=None, teil=None, rohteil=None
):
    """Auf einem Nebenrechner: koerper_aus_abschnitten(), der Körper als nebenrechner.Form."""
    from . import nebenrechner as nr

    form, flaeche = koerper_aus_abschnitten(
        grenzen, x, y, z_von, z_bis, schritt, teil_grenzen, teil, rohteil
    )
    return nr.Form.von(form), flaeche


def anfang_des_jobs(job):
    """Die Höhen des Rohteils im Materialstand (vor der ersten Operation) – für im_teil."""
    from . import materialstand as mst

    ops = list(job.Operations.Group)
    stand = mst.fuer(job, vor=ops[0]) if ops else None
    return None if stand is None else stand.quader.h


def stand_des_jobs(job):
    """Der Materialstand nach allen Operationen des Jobs (materialstand.fuer) – ValueError mit
    einem Satz, wenn es keinen gibt (kein Rohteil, eine Rundachse dreht) oder nichts gefräst
    ist."""
    from . import materialstand as mst

    stand = mst.fuer(job)
    if stand is None:
        raise ValueError(tr("ft.fehler.kein_stand"))
    if not stand.namen:
        raise ValueError(tr("ft.fehler.keine_operation"))
    return stand


def hoehen(job, stand):
    """Die Höhen des Fertigteils im Raster des Materialstands: seine – am Rand eines nicht
    eckigen Rohteils ergänzt. Der Materialstand zieht dort eine Zelle ein
    (materialstand._eingezogen: sonst räumte es durch die Luft); als Rohteil der nächsten
    Aufspannung lieber mehr Material als weniger – am C-Ring aus Rundmaterial Ø 60 (Aufmaß 0)
    fehlte rundum ein halber Millimeter. Dieser Saum und die Zellen gleich außerhalb (ihre Mitte
    liegt draußen, ihre Fläche reicht noch ins Rohteil) bekommen die Höhe des Materials neben
    ihnen, höchstens die des Rohteils; beschnitten aufs Rohteil (im_rohteil) ist der Rand dann
    genau. Wo daneben nichts mehr steht, bleiben sie leer."""
    from . import hoehenfeld as hf
    from . import materialstand as mst
    from . import vierachs_flaechen as vf

    q = stand.quader
    h = np.array(q.h, dtype=float)
    rohteil = getattr(job, "Stock", None)
    if rohteil is None or mst._ist_quader(rohteil):
        return h
    voll = hf.hoehen(vf.vernetze(rohteil.Shape, hf.VORSCHAU_TOLERANZ).netz, q.x, q.y)
    drin = np.isfinite(voll)
    saum = drin & ~np.isfinite(mst._eingezogen(voll)) & ~np.isfinite(h)
    daneben = _hoechster_nachbar(h)
    saum &= np.isfinite(daneben)
    h[saum] = np.minimum(daneben[saum], voll[saum])
    daneben = _hoechster_nachbar(h)
    draussen = ~drin & ~np.isfinite(h) & np.isfinite(daneben)
    h[draussen] = daneben[draussen]
    return h


def _hoechster_nachbar(h):
    """Je Zelle die höchste der acht Nachbarn (−inf am Rand des Rasters)."""
    n, m = h.shape
    rand = np.pad(h, 1, constant_values=-np.inf)
    ergebnis = np.full_like(h, -np.inf)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di or dj:
                ergebnis = np.maximum(ergebnis, rand[1 + di : 1 + di + n, 1 + dj : 1 + dj + m])
    return ergebnis


def lage(job):
    """Die Lage (FreeCAD.Placement), die einen Körper in den Koordinaten des Jobs dorthin legt,
    wo das Original des Teils liegt – Original · Klon⁻¹ (der Klon ist das Teil, um Nullpunkt und
    Aufspannung verschoben)."""
    from . import vierachs_rohteil as vr

    klon = vr.modell(job)
    teil = vr.original(klon)
    return teil.Placement.multiply(klon.Placement.inverse())


def aufspannung(job):
    """Die wievielte Aufspannung der Job ist: 1 – oder eins mehr als die des Fertigteils, aus dem
    sein Rohteil stammt (das Rohteil ist ein Klon des Körpers, Objects[0]). Zwei Jobs mit
    verschiedenem Rohteil für dieselbe erste Aufspannung (der C-Ring aus Platte und aus Rundmaterial)
    sind beide 1."""
    rohteil = getattr(job, "Stock", None)
    quellen = getattr(rohteil, "Objects", None) or []
    vorher = getattr(quellen[0], "Aufspannung", None) if quellen else None
    return int(vorher) + 1 if vorher else 1


# So heißt ein Körper, den niemand benannt hat (FreeCAD zählt hinten weiter: „Body001“) – dann
# nennt das Fertigteil das Dokument (am C-Ring „Körper – Aufspannung 1 …“ sagte nichts).
OHNE_NAMEN = ("Body", "Körper", "Part", "Teil", "Feature", "Solid", "Fusion", "Clone")


def name_fuer(job):
    """„<Teil> – Aufspannung N – Fertigteil“ (aufspannung) – ist das Teil nicht benannt
    (OHNE_NAMEN), statt seiner das Dokument."""
    from . import vierachs_rohteil as vr

    teil = vr.original(vr.modell(job))
    name = teil.Label
    if name.rstrip("0123456789 ") in OHNE_NAMEN:
        name = job.Document.Label or name
    return tr("ft.name", teil=name, nummer=aufspannung(job))


def vorhanden(job):
    """Das Fertigteil, das schon aus diesem Job gerechnet wurde – oder None."""
    return next((o for o in job.Document.Objects if getattr(o, "AusJob", None) == job.Name), None)


def anlegen(job, form, name=None):
    """Legt das Fertigteil (`form` in den Koordinaten des Jobs) als Part::Feature ins Dokument –
    an die Stelle des Original-Teils (lage). Gibt es schon eins aus diesem Job (vorhanden), bekommt
    es die neue Form: Ein Job, dessen Rohteil es ist, folgt ihm. Gibt das Objekt zurück; ohne
    eigene Transaktion."""
    objekt = vorhanden(job)
    if objekt is None:
        objekt = job.Document.addObject("Part::Feature", "Fertigteil")
        objekt.addProperty(
            "App::PropertyString", "AusJob", "CAM-Addon", "Der Job, aus dem es gerechnet ist"
        )
        objekt.addProperty(
            "App::PropertyInteger", "Aufspannung", "CAM-Addon", "Nach der wievielten Aufspannung"
        )
        objekt.AusJob = job.Name
    objekt.Aufspannung = aufspannung(job)
    objekt.Label = name or name_fuer(job)
    objekt.Shape = form
    objekt.Placement = lage(job).multiply(form.Placement)
    return objekt


def datei_speichern(objekt):
    """Speichert das Fertigteil als eigene Datei im Ordner seines Dokuments
    („<Label>.FCStd“) – gibt den Pfad zurück, oder None, wenn das Dokument noch keinen Ordner hat
    (nie gespeichert)."""
    import FreeCAD

    ordner = os.path.dirname(objekt.Document.FileName or "")
    if not ordner:
        return None
    pfad = os.path.join(ordner, _dateiname(objekt.Label) + ".FCStd")
    aktiv = FreeCAD.ActiveDocument
    # Unsichtbar (ohne Fenster): Sonst ginge kurz ein zweites auf und wieder zu, und danach
    # hätte die Oberfläche kein aktives Dokument mehr.
    neu = FreeCAD.newDocument(_dateiname(objekt.Label).replace(" ", "_"), hidden=True)
    try:
        kopie = neu.addObject("Part::Feature", "Fertigteil")
        kopie.Label = objekt.Label
        kopie.Shape = objekt.Shape
        neu.recompute()
        neu.saveAs(pfad)
    finally:
        FreeCAD.closeDocument(neu.Name)
        if aktiv is not None:
            FreeCAD.setActiveDocument(aktiv.Name)
    return pfad


def _dateiname(text):
    """Ein Dateiname aus dem Label: ohne Zeichen, die Dateisysteme nicht mögen."""
    verboten = '<>:"/\\|?*'
    name = "".join("_" if c in verboten else c for c in text).strip().rstrip(".")
    return name or "Fertigteil"


def zellen(stand):
    """So viele Zellen hat der Materialstand (für die Ansage, wie lange es dauert)."""
    return int(math.prod(stand.quader.h.shape))
