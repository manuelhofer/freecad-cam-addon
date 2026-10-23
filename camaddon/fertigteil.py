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


def _aus_dem_netz(punkte, dreiecke, teil):
    import Mesh

    from . import stl_teil

    netz = Mesh.Mesh()
    netz.addFacets([[tuple(punkte[k]) for k in d] for d in dreiecke])
    voll = float(netz.Volume)
    for anteil in VEREINFACHEN:
        kopie = netz.copy()
        with _ohne_fehler():
            kopie.decimate(0.001, anteil)
            if abs(float(kopie.Volume) - voll) <= VOLUMEN_SPIEL * abs(voll):
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
