# SPDX-License-Identifier: LGPL-2.1-or-later
"""3D, die Bahn „3D-Schruppen“ (W-006 4.2 Punkt 1, Schruppen ebenenweise): das Rohteil über
Freiformflächen – Kuppeln, Rundungen, Schrägen – in Lagen von oben wegräumen, mit dem Kern des
Räumens (raeumen_bahn): Ringe bei vollem ap und schmalem ae, im Gleichlauf, ohne Wenden, hinein
aus dem Freien oder über die Rampe.

- **Hauptlagen** vom Rohteil bis auf den tiefsten Punkt der gewählten Flächen plus Aufmaß, je
  höchstens ap (und die Schneidenlänge): Gesperrt ist, wo die Hüllfläche des ganzen Teils – der
  Fräser um das Aufmaß größer – über der Lage liegt; der Rest wird geräumt wie beim Räumen (die
  Varianten „rohteil“, „morph“ und „inseln“ gerechnet, die schnellste zählt).
- **Zwischenlagen:** Über einer Freiformfläche ließe jede Hauptlage eine Treppe bis ap hoch
  stehen. Darum nach jeder Hauptlage Zwischenlagen im Abstand ZWISCHEN hinauf bis zur vorigen
  Hauptlage, von oben nach unten – sie räumen nur, wo über der Lage noch Material steht, das der
  Fräser dort erreicht. Ein Raster merkt sich je Zelle, bis wohin das Material noch reicht
  (gesenkt, wo die Stirn darüber fuhr); die Ringe laufen von außen bis an die Fläche, nur wo
  unter der Stirn Material ist. Bei der kleinen Tiefe dürfen die Ringe weiter auseinander: so
  viel Material je mm wie in der Hauptlage (ae · ap gleich), höchstens der Radius.
- Der Eilgang hinab endet über dem höchsten Material unter der Stirn (das Raster).
- **Restschruppen** (W-006 4.2 Punkt 2, P-2026-10-02-02): Mit `davor` (die Form des größeren
  Fräsers, der vorher schruppte) beginnt das Raster nicht mit dem vollen Rohteil, sondern mit
  dem, was der große stehen ließ: je Zelle die tiefste Lage seiner ebenen Stirn über ihr – so
  tief, wie seine Hüllfläche ihn lässt, gleitend über seine Scheibe (`_nach_davor`; ohne die
  Treppe seiner Lagen, die nimmt das Schlichten). Dann räumt jede Lage wie eine Zwischenlage:
  nur wo darüber Material steht, das dieser erreicht – in engen Lücken, Ecken, Kehlen.

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import dataclasses
import math
from dataclasses import dataclass, field

import numpy as np

from . import bahn as bn
from . import hoehenfeld as hf
from . import kontur_bahn as kb
from . import raeumen_bahn as rb
from . import schlichten3d_bahn as sb
from . import vierachs_bahn as vb
from . import vierachs_planbahn as vp
from .sprache import tr

ZWISCHEN = 1.0  # mm – Vorschlag: so weit liegen die Zwischenlagen auseinander (0: keine)
SCHRITT = rb.SCHRITT  # mm – das Raster
VORSCHAU_SCHRITT = rb.VORSCHAU_SCHRITT
MATERIAL = 0.05  # mm – so viel muss über der Lage stehen, damit es als Material zählt
MINDESTFLAECHE = 2.0  # mm² – weniger Material auf einer Zwischenlage: nichts zu tun
# So weit dürfen die Ringe vom Linienzug aus dem Raster abweichen (Anteil des Rasters): Die
# Höhenlinien des Abstands laufen in kleinen Zacken (die Zellen des Gesperrten), an denen die
# Maschine hielte. Zum Teil hin bleibt das Gesperrte um eine Zelle breiter – sicher.
GLAETTEN = 0.4
GLEICH = rb.GLEICH


@dataclass
class Schruppbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    lagen: int  # Hauptlagen mit Schnitt
    zwischenlagen: int  # Zwischenlagen mit Schnitt
    ringe: int
    laeufe: int
    z_min: float  # die tiefste Spitze (mm)
    laenge: float  # mm im Vorschub
    zeit: float  # Minuten (bahn.zeit)
    variante: str  # die Variante der Hauptlagen
    zeiten: dict = field(default_factory=dict)  # Minuten je gerechneter Variante
    rampen: int = 0


class _Lage3D(rb._Lage):
    """Eine Lage, die weiß, bis wohin das Material steht: Der Eilgang hinab endet über dem
    höchsten Material unter der Stirn – auch über einem Rest, den das Raster der Ringe nicht
    sieht."""

    hoehe = None  # (nx, ny): bis wohin das Material je Zelle reicht
    stempel = None  # (Maske, m): die Stirn um eine Zelle größer, für _hoechstes

    def _hinab(self, start, hoch):
        knapp = min(hoch, self.lage + self.w.sicherheit)
        oben = _hoechstes(self.feld, self.hoehe, self.stempel, start[0], start[1])
        return min(hoch, max(knapp, oben + self.w.sicherheit))


def _scheibe(radius, schritt):
    """(Maske, m): die Zellen einer Scheibe mit dem Radius um die Mitte (2m + 1)²."""
    m = max(0, int(math.ceil(radius / schritt)))
    d = np.arange(-m, m + 1) * schritt
    return (d[:, None] ** 2 + d[None, :] ** 2) <= radius * radius + 1e-12, m


def _hoechstes(feld, hoehe, stempel, x, y):
    """Das höchste Material unter dem Stempel um (x, y) – −inf, wenn keins."""
    maske, m = stempel
    i, j = feld.zellen([x], [y])
    ci, cj = int(i[0]), int(j[0])
    a0, b0 = max(ci - m, 0), max(cj - m, 0)
    a1, b1 = min(ci + m + 1, feld.nx), min(cj + m + 1, feld.ny)
    if a1 <= a0 or b1 <= b0:
        return -math.inf
    fenster = hoehe[a0:a1, b0:b1][maske[a0 - ci + m : a1 - ci + m, b0 - cj + m : b1 - cj + m]]
    return float(fenster.max()) if fenster.size else -math.inf


class _Aufweiten:
    """Masken um einen Radius aufweiten (Faltung mit der Scheibe über die FFT), je Radius die
    Scheibe im Frequenzraum einmal."""

    def __init__(self, feld):
        self.feld = feld
        self._kerne = {}

    def __call__(self, maske, radius):
        if radius <= 0:
            return maske.copy()
        feld = self.feld
        scheibe, m = _scheibe(radius, feld.schritt)
        groesse = (feld.nx + 2 * m + 1, feld.ny + 2 * m + 1)
        schluessel = (m, round(radius, 6))
        if schluessel not in self._kerne:
            kern = np.zeros(groesse)
            kern[: 2 * m + 1, : 2 * m + 1] = scheibe
            self._kerne[schluessel] = np.fft.rfft2(kern)
        feld_g = np.zeros(groesse)
        feld_g[: feld.nx, : feld.ny] = maske
        gefaltet = np.fft.irfft2(np.fft.rfft2(feld_g) * self._kerne[schluessel], s=groesse)
        return gefaltet[m : m + feld.nx, m : m + feld.ny] > 0.5


def _breiter(gesperrt):
    """Das Gesperrte um eine Zelle breiter, auch diagonal (wie raeumen_bahn._flaeche)."""
    breiter = gesperrt.copy()
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di or dj:
                breiter |= np.roll(np.roll(gesperrt, di, 0), dj, 1)
    return breiter


def _ringe_zwischen(ablauf, feld, w, D, material, material_links, schritt, toleranz, aufweiten):
    """Die Ringe einer Zwischenlage: Höhenlinien des Abstands D zum Gesperrten, von außen nach
    innen bis an die Fläche. Der erste so weit draußen, dass er gerade ae vom äußersten Material
    nimmt (kein Ring für einen Span am Rand), die übrigen gleich weit bis D = 0, je höchstens
    1,1 · ae; jeder nur, wo unter seiner Stirn Material (`material`) ist – 3 mm Zugabe, damit
    kein Lauf an einer Zelle endet."""
    ae = w.zeilenabstand
    werte = D[material & np.isfinite(D)]
    if not werte.size:
        return
    erster = float(werte.max()) + feld.r - ae
    if erster <= 0:
        niveaus = [0.0]
    else:
        anzahl = max(1, int(math.ceil(erster / (1.1 * ae) - 1e-9)))
        niveaus = [erster * (anzahl - k) / anzahl for k in range(anzahl + 1)]
    breit = max(1, int(round(3.0 / schritt)))
    for nummer, niveau in enumerate(niveaus):
        ringe, nur = [], {}
        unter_stirn = aufweiten(material & ~feld.frei, feld.r - 0.01)
        for punkte, geschlossen in rb._hoehenlinien(D, feld.xs, feld.ys, niveau):
            if len(punkte) < 2:
                continue
            laenge = float(np.sum(np.hypot(*np.diff(punkte, axis=0).T)))
            if geschlossen and laenge < 2 * math.pi * min(ae, 1.0):
                continue  # winzig
            ring = rb._ring_aus_linie(
                punkte, geschlossen, material_links, feld, niveau, D, schritt, toleranz
            )
            if ring is None:
                continue
            noetig = unter_stirn[feld.zellen(ring.proben.x, ring.proben.y)]
            if not noetig.any():
                continue
            if geschlossen:
                kern = np.concatenate([noetig[-breit:], noetig, noetig[:breit]])
                nur[id(ring)] = np.convolve(kern, np.ones(2 * breit + 1), "same")[breit:-breit] > 0
            else:
                nur[id(ring)] = np.convolve(noetig, np.ones(2 * breit + 1), "same") > 0
            ringe.append(ring)
        rb._naechster_zuerst(ablauf, ringe, True, f"zwischen {nummer}", nur)


def _nach_davor(feld, netz, davor, aufmass, toleranz, ziel):
    """(nx, ny) mm: bis wohin das Material reicht, nachdem der größere Fräser `davor` (Form mit
    ebener Stirn) überall so tief fuhr, wie er kann – je Zelle die tiefste Lage seiner ebenen
    Stirn über ihr (gleitendes Minimum über die Scheibe); wo ihn nichts hält, bis aufs Ziel."""
    geformt = rb.form_mit_aufmass(davor, aufmass + toleranz)
    roh = hf.je_zeile(netz, geformt, feld.ys, feld.x0, feld.schritt, feld.nx, True)
    zugabe = aufmass + toleranz + vb.RAND
    spitze = np.where(roh <= ziel + GLEICH, ziel, np.maximum(roh + zugabe, ziel))
    radius = max(float(vp.ebener_radius(davor)) - 0.01, feld.schritt)
    m = int(radius / feld.schritt + 1e-9)
    hoehe = spitze.copy()
    for di in range(-m, m + 1):
        ziel_i, quelle_i = sb._verschoben(di, feld.nx)
        for dj in range(-m, m + 1):
            if (di == 0 and dj == 0) or math.hypot(di, dj) * feld.schritt > radius + 1e-9:
                continue
            ziel_j, quelle_j = sb._verschoben(dj, feld.ny)
            teil = hoehe[ziel_i, ziel_j]
            np.minimum(teil, spitze[quelle_i, quelle_j], out=teil)
    return hoehe


def _lagen(oben, ziel, zustellung, zwischen):
    """([(z, ist_zwischenlage, vorige)], ap der Hauptlagen) – die Hauptlagen von oben bis
    `ziel`, je höchstens `zustellung` und gleich weit, nach jeder die Zwischenlagen darüber bis
    zur vorigen Hauptlage, von oben nach unten; `vorige`: bis wohin das Material über der Lage
    höchstens reicht."""
    anzahl = max(1, int(math.ceil((oben - ziel - hf.LAGEN_SPIEL) / zustellung)))
    folge = []
    oberkante = oben
    for k in range(1, anzahl + 1):
        lage = oben - (oben - ziel) * k / anzahl
        folge.append((lage, False, oberkante))
        if zwischen > 0:
            teile = int(math.ceil((oberkante - lage) / zwischen - 1e-9))
            vorige = oberkante
            for m in range(teile - 1, 0, -1):
                z = lage + (oberkante - lage) * m / teile
                folge.append((z, True, vorige))
                vorige = z
        oberkante = lage
    return folge, (oben - ziel) / anzahl


def _schruppen(st, netz, w, z_unten, variante, r, schritt, zwischen, davor=None):
    """Alle Lagen in der Variante (die der Hauptlagen); gibt (Hauptlagen, Zwischenlagen) mit
    Schnitt zurück. Mit `davor` (Form des größeren Fräsers davor) nur der Rest: jede Lage wie
    eine Zwischenlage, das Material aus _nach_davor."""
    aufmass = max(w.aufmass, 0.0)
    ziel = z_unten + aufmass
    oben = w.oben
    if oben <= ziel + GLEICH:
        return 0, 0
    zustellung = w.zustellung
    if w.schneidenlaenge > 0:
        zustellung = min(zustellung, w.schneidenlaenge)
    x_von, x_bis, y_von, y_bis = w.rohteil
    ae = w.zeilenabstand
    rand = 3.0 * r + ae
    toleranz = netz.toleranz
    glatt = max(toleranz, GLAETTEN * schritt)  # für die Ringe
    zugabe = aufmass + toleranz + vb.RAND
    geformt = rb.form_mit_aufmass(w.form, aufmass + toleranz)
    feld = rb._Feld(
        netz,
        geformt,
        zugabe,
        r,
        x_von - rand,
        x_bis + rand,
        y_von - rand,
        y_bis + rand,
        schritt,
        w.rohteil,
        ae + schritt,
    )
    rechteck = (feld.rohteil_zellen, feld.beruehrt, feld.eng)
    hoehe = np.where(feld.rohteil_zellen, oben, -np.inf)
    if davor is not None:
        nach = _nach_davor(feld, netz, davor, aufmass, toleranz, ziel)
        hoehe = np.where(feld.rohteil_zellen, np.minimum(oben, nach), -np.inf)
    aufweiten = _Aufweiten(feld)
    stempel = _scheibe(r, schritt)
    gx, gy = np.meshgrid(feld.xs, feld.ys, indexing="ij")
    im_raster = feld.im_raster(gx, gy)
    r_ein = w.einfahrradius if w.einfahrradius and w.einfahrradius > 0 else kb.EINFAHRT_ANTEIL * r
    gerade = kb.GERADE_ANTEIL * r
    material_links = not w.gleichlauf  # Gleichlauf (M3): das Material rechts
    haupt = zwischenlagen = 0
    folge, ap_haupt = _lagen(oben, ziel, zustellung, zwischen)
    for lage, zwischenlage, vorige in folge:
        erlaubt = feld.erlaubt_feld(lage, z_unten)
        gesperrt = _breiter(~erlaubt)
        werte = w
        ist_zwischen = zwischenlage or davor is not None  # der Rest: nur, wo Material steht
        if ist_zwischen:
            # Die Ringe nur für das, was über der Lage steht und der Fräser hier erreicht – eine
            # Zelle weniger weit als die Stirn vom Freien, damit der Rand am Gesperrten (den der
            # Ring bei D = 0 nicht nimmt) nicht jede Lage zählt. Für das Einfahren zählt alles
            # Material, das die Stirn treffen kann.
            ueber = hoehe > lage + MATERIAL
            material = ueber & aufweiten(~gesperrt, r - schritt - 0.01)
            if material.sum() * schritt * schritt < MINDESTFLAECHE:
                continue
            # So viel Material je mm Weg wie in der Hauptlage (ae · ap), höchstens der Radius.
            weiter = min(r, max(ae, ae * ap_haupt / max(vorige - lage, GLEICH)))
            werte = dataclasses.replace(w, zeilenabstand=weiter)
            feld.rohteil_zellen = ueber & aufweiten(erlaubt, r - 0.01)
            feld.beruehrt = aufweiten(feld.rohteil_zellen, r)
            feld.eng = aufweiten(feld.rohteil_zellen, weiter + schritt)
        else:
            feld.rohteil_zellen, feld.beruehrt, feld.eng = rechteck
        feld.frei[:] = False
        ablauf = _Lage3D(st, feld, werte, r, r_ein, gerade, lage, vorige, erlaubt, schritt, oben)
        ablauf.hoehe = hoehe
        ablauf.stempel = stempel
        if ist_zwischen:
            # Einfahren wie in der Hauptlage: unter der Stirn höchstens so viel Material wie im
            # Streifen ae der Hauptlage – nicht die breiteren Ringe der Zwischenlage.
            ablauf.schwelle = _Lage3D(
                st, feld, w, r, r_ein, gerade, lage, vorige, erlaubt, schritt, oben
            ).schwelle
        D = feld.abstand_zu(gesperrt & im_raster)
        vorher = st.ringe
        if ist_zwischen:
            if np.isfinite(D).any():
                _ringe_zwischen(
                    ablauf, feld, werte, D, material, material_links, schritt, glatt, aufweiten
                )
        else:
            art = variante
            if art == "inseln" and not np.isfinite(D).any():
                art = "rohteil"  # keine Insel: nur die Ringe vom Rohteil her
            if art == "rohteil":
                rb._ringe_vom_rohteil(ablauf, feld, w, r, D, material_links, schritt, glatt)
                rb._ringe_um_inseln(ablauf, feld, w, D, material_links, schritt, glatt, True)
            elif art == "morph":
                rb._ringe_morph(ablauf, feld, w, r, D, material_links, schritt, glatt)
                rb._ringe_um_inseln(ablauf, feld, w, D, material_links, schritt, glatt, True)
            else:
                rb._ringe_um_inseln(ablauf, feld, w, D, material_links, schritt, glatt, False)
        ablauf.reste_fahren()
        ablauf.heben()
        hoehe[feld.frei] = np.minimum(hoehe[feld.frei], lage)
        if st.ringe > vorher:
            if zwischenlage:
                zwischenlagen += 1
            else:
                haupt += 1
    feld.rohteil_zellen, feld.beruehrt, feld.eng = rechteck
    return haupt, zwischenlagen


def bereich(form_teil, namen):
    """(Namen der Freiformflächen unter `namen`, ihr tiefster Punkt z) – ValueError mit einem
    Satz, wenn keine darunter ist."""
    from . import vierachs_flaechen as vf

    flaechen = sb.freiformflaechen(form_teil, namen)
    if not flaechen:
        raise ValueError(tr("r3.fehler.keine"))
    z_unten = min(form_teil.Faces[n].BoundBox.ZMin for n in vf.nummern(flaechen))
    return flaechen, z_unten


def planen(
    form_teil, namen, werte, zwischen=ZWISCHEN, toleranz=hf.TOLERANZ, schritt=SCHRITT, davor=None
):
    """Die Bahn „3D-Schruppen“ (Schruppbahn) über den Freiformflächen `namen` von `form_teil`
    mit den Werten `werte` (raeumen_bahn.Raeumwerte; `aufmass` gilt überall, auch unten) – mit
    `davor` (Form des größeren Fräsers davor, ebene Stirn) nur der Rest, den er ließ.
    ValueError mit einem Satz, wenn es nicht geht."""
    from . import vierachs_flaechen as vf

    w = werte
    r = float(w.form.radius)
    if r <= 0 or vp.ebener_radius(w.form) <= 0:
        raise ValueError(tr("ra.fehler.form"))
    if w.zustellung <= 0 or w.zeilenabstand <= 0:
        raise ValueError(tr("ra.fehler.werte"))
    if w.zeilenabstand > r + GLEICH:
        raise ValueError(tr("ra.fehler.zeilenabstand"))
    _flaechen, z_unten = bereich(form_teil, namen)
    netz = vf.vernetze(form_teil, toleranz).netz
    if davor is not None and vp.ebener_radius(davor) <= 0:
        raise ValueError(tr("ra.fehler.form"))
    varianten = (w.variante,) if w.variante in rb.VARIANTEN else rb.VARIANTEN
    if davor is not None:
        varianten = ("rohteil",)  # jede Lage wie eine Zwischenlage: keine Varianten
    ergebnisse = {}
    for variante in varianten:
        st = rb._Stand()
        try:
            haupt, zwischenlagen = _schruppen(
                st, netz, w, z_unten, variante, r, schritt, zwischen, davor
            )
        except rb._KeinMorph:
            continue
        if st.ringe == 0:
            continue
        zeit = bn.zeit(st.punkte, w.vorschub if w.vorschub > 0 else 1000.0, w.eintauchen or None)
        ergebnisse[variante] = (st, zeit, haupt, zwischenlagen)
    if not ergebnisse and davor is not None:
        raise ValueError(tr("r3.fehler.kein_rest"))
    if not ergebnisse:
        raise ValueError(tr("r3.fehler.nichts"))
    variante = min(ergebnisse, key=lambda v: ergebnisse[v][1])
    st, zeit, haupt, zwischenlagen = ergebnisse[variante]
    return Schruppbahn(
        st.punkte,
        haupt,
        zwischenlagen,
        st.ringe,
        st.laeufe,
        st.z_min if math.isfinite(st.z_min) else 0.0,
        st.laenge,
        zeit,
        variante,
        {v: e[1] for v, e in ergebnisse.items()},
        st.rampen,
    )
