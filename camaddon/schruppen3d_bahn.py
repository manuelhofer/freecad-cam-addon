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
- **Materialstand** (W-012, materialstand): Mit `stand` beginnt das Raster mit dem, was die
  Operationen davor im Job übrig ließen. Steht über den Lagen nicht überall das volle Rohteil,
  räumt jede Lage wie beim Restschruppen nur, wo Material steht (die Varianten fallen dann
  weg), und die Lagen beginnen am höchsten Material, das der Fräser erreicht.

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import dataclasses
import math
from dataclasses import dataclass, field

import numpy as np

from . import bahn as bn
from . import formteile as ft
from . import hoehenfeld as hf
from . import kontur_bahn as kb
from . import raeumen_bahn as rb
from . import ringgrenze as rg
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
# Der Ring an der Wand aus der genauen Grenze (ringgrenze, Spezifikation Strategien 13.6) statt
# aus den Zellen – abschaltbar für den Vergleich.
GENAUE_GRENZE = True
# Nur im Raster der fertigen Bahn: Im gröberen der Vorschau (1 mm) hält die genaue Grenze auf
# keiner Lage (gemessen vom Gegenprüfer, 2026-11-13: 19 von 19 Lagen zurück) – sie kostete dort nur
# Rechenzeit (0,5 → 2,0 s und 0,6 → 4,3 s). Mit einem um (1 ÷ 0,5)² weiter ins Freie gerückten Ring
# hielte sie auch dort, kostete am Geist aber 74 statt 2 s für die Vorschau (2026-11-13).
GENAU_BIS_RASTER = 0.5  # mm
# An der genauen Grenze zählt auf einer Zwischenlage als Material, was die Stirn des Rings an der
# Wand trifft (statt was die des Rings aus dem Raster träfe) – abschaltbar für den Vergleich.
RAND_ZAEHLT = True
# Zwischenlagen von unten nach oben (Frage 4, Manuel am 2026-11-13: „a“; am 12.10. lieber „mit der
# ganzen Schneide“ als dünne Schichten): Jede Zwischenlage fräst nur den schmalen Streifen an der
# Wand, der über ihr noch steht, mit voller Tiefe bis zur Oberkante der Hauptlage – statt von oben
# je eine 1 mm dünne Scheibe über die ganze Breite (am Geist 69 Lagen, 19,2 m Vorschub für 11 % des
# Materials). Vorschlag für neue Operationen; gespeicherte behalten die alte Reihenfolge.
VON_UNTEN = True
# So breit darf die Stufe werden (mm, waagrecht, an der genauen Grenze gemessen): Eine Zwischenlage
# kommt erst dort, wo die Stufe seit der zuletzt gefrästen Lage sonst breiter würde – an steilen
# Wänden fällt so die Mehrzahl der Lagen weg, an flachen bleibt es bei jeder.
STUFE = 1.0
# Örtlich fährt der Ring nur, wo die Stufe mindestens so breit ist (kein Ring für 0,2 mm); was
# dort stehen bleibt, nimmt eine höhere Lage, sobald es breit genug ist.
STUFE_ORT = 0.5 * STUFE
# Ein Ring weiter draußen (die Stufe breiter als ae) fährt nur, wo er mehr als diesen Anteil von ae
# nimmt – den Rest nimmt der Ring dahinter mit.
STUFE_AUSSEN = 0.25
# _RUECKFALL – von unten ohne genaue Grenze (im Raster über GENAU_BIS_RASTER: die Vorschau, eine
# gröbere Auflösung; oder auf einer Lage, auf der ein Ring beim Nachrechnen nicht hält): Das Raster
# weiß je Zellmitte, bis wohin Material steht – was eine Lage stehen lässt, ist oft schmaler als
# eine Zelle. An der flachen Kuppel im Raster 1,0 endete der Eilgang hinab darum im Material
# (2,4 mm³: die Zelle galt als gefräst, ihr Rand stand noch), und das Einfahren von der freien
# Seite sah unter der Stirn nur einen dünnen Rand (Anteil 0,04, erlaubt wie im Streifen ae) statt
# der Säule bis zur Oberkante: fünfmal senkrecht ins Material (Gegenprüfer, 2026-11-13). Dort
# zählt zum Einfahren eine Zelle mehr Material, hinab und hinein geht es nur, wo nichts unter der
# Stirn steht, der Eilgang endet über dem, was sicher noch steht (`sicher`: gesenkt nur, wo auch
# die Nachbarn der Zelle gefräst sind), und die Stufe zählt eine Zelle schmaler (das Raster sieht
# sie bis eine Zelle zu breit: an der flachen Kuppel sonst zwei Ringe je Lage statt einem, die
# Vorschau 7,25 statt 6,71 min). Gemessen in der Vorschau: flache Kuppel 6,71 (fertig 6,22),
# Kuppel 4,25 (4,93), Kuppel + 5 4,74 (5,41) min – nichts im Eilgang, nie senkrecht ins Material.


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
    # Mit Materialstand (W-012): was über den Flächen noch steht und was die Operationen davor
    # dort schon weggenommen haben (mm³), und welche das waren.
    noch: float = 0.0
    weg: float = 0.0
    davor: list = field(default_factory=list)
    # Was rings um die Flächen noch über dem Teil steht (mm³, _nur_ueber) – mit `nur_ueber` gilt
    # es als schon gefräst, sonst nimmt die Bahn es mit weg.
    drumherum: float = 0.0
    nur_ueber: bool = False


class _Lage3D(rb._Lage):
    """Eine Lage, die weiß, bis wohin das Material steht: Der Eilgang hinab endet über dem
    höchsten Material unter der Stirn – auch über einem Rest, den das Raster der Ringe nicht
    sieht."""

    hoehe = None  # (nx, ny): bis wohin das Material je Zelle reicht
    stempel = None  # (Maske, m): die Stirn um eine Zelle größer, für _hoechstes
    # Eine Zwischenlage von unten (_ringe_streifen): Wo ein Ring fährt, ist schon an der genauen
    # Grenze entschieden – der Streifen ist oft schmaler als eine Zelle, das Raster sähe ihn nicht.
    streifen = False

    def _schneidet(self, x, y, streng=False):
        if self.streifen:
            return True
        return super()._schneidet(x, y, streng)

    def _hinab(self, start, hoch):
        knapp = min(hoch, self.lage + self.w.sicherheit)
        oben = _hoechstes(self.feld, self.hoehe, self.stempel, start[0], start[1])
        return min(hoch, max(knapp, oben + self.w.sicherheit))

    def _material_oben(self, ort=None):
        """Wie im Räumen – dazu, was unter der Stirn über `ort` wirklich noch höher steht (ein
        Rest, den die Lage darüber nicht nahm): Der Eilgang hinab endet auch vor Rampe und Helix
        darüber."""
        oben = super()._material_oben(ort)
        if ort is not None and self.hoehe is not None:
            oben = max(oben, _hoechstes(self.feld, self.hoehe, self.stempel, ort[0], ort[1]))
        return oben

    def _rampe_ab(self, x, y):
        """Das höchste Material unter der Stirn längs der Rampe – höchstens die vorige Lage."""
        hoch = self.lage
        for a, b in zip(x, y, strict=False):
            hoch = max(hoch, _hoechstes(self.feld, self.hoehe, self.stempel, a, b))
        return min(self.vorige, hoch)


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
        if niveau <= 0.0 and feld.grenze is not None:
            # Die Ringe an der Wand: aus der genauen Grenze (ringgrenze), schon nachgerechnet.
            linien = [(None, ring) for ring in feld.grenze.ringe]
        else:
            linien = rb._hoehenlinien(D, feld.xs, feld.ys, niveau)
        for punkte, geschlossen in linien:
            if punkte is None:
                ring = geschlossen
            else:
                if len(punkte) < 2:
                    continue
                laenge = float(np.sum(np.hypot(*np.diff(punkte, axis=0).T)))
                if geschlossen and laenge < 2 * math.pi * min(ae, 1.0):
                    continue  # winzig
                ring = rb._ring_des_feldes(
                    punkte, geschlossen, material_links, feld, niveau, D, schritt, toleranz
                )
            if ring is None:
                continue
            noetig = unter_stirn[feld.zellen(ring.proben.x, ring.proben.y)]
            if not noetig.any():
                continue
            nur[id(ring)] = rb.verbreitert(noetig, breit, ring.geschlossen)
            ringe.append(ring)
        rb._naechster_zuerst(ablauf, ringe, True, f"zwischen {nummer}", nur)


# --- Zwischenlagen von unten (VON_UNTEN) ---------------------------------------------------------


def _naechste(punkte, frage):
    """(Abstand, Index) je Stelle in `frage` (n, 2) zum nächsten der `punkte` (m, 2), m > 0."""
    try:
        from scipy.spatial import cKDTree
    except ImportError:
        cKDTree = None
    if cKDTree is not None:
        abstand, index = cKDTree(punkte).query(frage)
        return np.asarray(abstand, dtype=float), np.asarray(index, dtype=int)
    abstand = np.empty(len(frage))
    index = np.empty(len(frage), dtype=int)
    block = max(1, 2_000_000 // max(len(punkte), 1))
    for a in range(0, len(frage), block):
        d2 = ((frage[a : a + block, None, :] - punkte[None, :, :]) ** 2).sum(axis=2)
        index[a : a + block] = d2.argmin(axis=1)
        abstand[a : a + block] = np.sqrt(d2.min(axis=1))
    return abstand, index


def _wandlinien(feld, lage, z_unten, grenze):
    """[(Punkte (m, 2), geschlossen)]: wo die Spitze auf der Lage an die Wand kommt – die Proben der
    Ringe an der genauen Grenze (ringgrenze, 0,015 mm davor), ohne sie die Höhenlinie der
    Hüllfläche aus dem Raster, zwischen den Knoten linear (zum Messen der Stufe, nicht zum Fahren:
    an einer senkrechten Wand bis eine halbe Zelle daneben)."""
    if grenze is not None:
        return [
            (np.column_stack([ring.proben.x, ring.proben.y]), ring.geschlossen)
            for ring in grenze.ringe
            if len(ring.proben.x) >= 2
        ]
    # Erlaubt wie feld.erlaubt_feld: die Hüllfläche nicht über der Lage, oder nichts über dem Ziel.
    # Nach unten begrenzt: Wo der Fräser das Teil nicht trifft (KEIN_TREFFER), läge die Linie
    # sonst am Knoten daneben.
    f = np.maximum(feld.roh + feld.zugabe - lage, -2.0)
    f = np.where(feld.roh <= z_unten + GLEICH, np.minimum(f, -GLEICH), f)
    return [(p, g) for p, g in rb._hoehenlinien(f, feld.xs, feld.ys, 0.0) if len(p) >= 2]


class _Treppe:
    """Von unten nach oben: bis wohin die Spitze seit der letzten Hauptlage an der Wand war (Punkte
    auf den Wandlinien der gefrästen Lagen, _wandlinien). Die Stufe an einer Stelle der Wand einer
    höheren Lage ist ihr Abstand zum nächsten dieser Punkte – so breit ist der Streifen, der dort
    über der Lage noch steht (die Stirn reicht an beiden Stellen gleich weit zur Wand hin)."""

    def __init__(self):
        self.punkte = np.zeros((0, 2))

    def leer(self):
        return not len(self.punkte)

    def setze(self, linien):
        self.punkte = np.zeros((0, 2))
        self.dazu([p for p, _g in linien])

    def dazu(self, stuecke):
        stuecke = [np.asarray(p, dtype=float).reshape(-1, 2) for p in stuecke]
        stuecke = [p for p in stuecke if len(p)]
        if stuecke:
            self.punkte = np.vstack([self.punkte, *stuecke])

    def breite(self, punkte):
        """Je Stelle (m, 2) die Stufe (mm) – inf ohne Punkte."""
        punkte = np.asarray(punkte, dtype=float).reshape(-1, 2)
        if self.leer() or not len(punkte):
            return np.full(len(punkte), np.inf)
        return _naechste(self.punkte, punkte)[0]


def _stufe(p, treppe, erreichbar, voll, steht, feld, r, schritt, fehler=0.0):
    """Je Punkt der Wand (m, 2) die Stufe (mm): der Abstand zur Treppe – höchstens so breit, wie das
    Raster unter der Stirn Material sieht (`voll`: Knoten (k, 2) über der Lage in Reichweite der
    Wand), plus eine Zelle (ein Streifen schmaler als sie ist im Raster nicht zu sehen); mindestens,
    was es eine Zelle weniger weit sieht (`erreichbar`); 0, wo nichts über der Lage steht
    (`steht`); beide Schranken um `fehler` schmaler (_RUECKFALL). Die Grenze nach oben: Die
    Treppe weiß nicht, was andere Operationen davor nahmen (Materialstand) – in der Mulde des
    Testteils öffnete sich auf −22,2 ein Absatz, den das Räumen schon geräumt hatte, die Treppe
    maß dort 33 mm."""
    b = treppe.breite(p)
    oben = np.full(len(p), schritt)
    if len(voll):
        oben = np.maximum(oben, r + schritt - fehler - _naechste(voll, p)[0])
    b = np.minimum(b, oben)
    if len(erreichbar):
        b = np.maximum(b, r - 0.5 * schritt - fehler - _naechste(erreichbar, p)[0])
    return np.where(steht[feld.zellen(p[:, 0], p[:, 1])], b, 0.0)


def _hauptlinien(feld, lage, z_unten, grenze):
    """Die Wandlinien einer Hauptlage für die Treppe: die der genauen Grenze, dazu die aus dem
    Raster, wo keine genaue in der Nähe liegt (die genaue hat Ringe nur, wo der Fräser das Rohteil
    trifft – fehlte eine Wand, sähe die Lage darüber dort eine viel zu breite Stufe). Nur aus dem
    Raster läge die Linie an einer senkrechten Wand bis eine halbe Zelle neben der genauen der
    Lagen darüber – das sähe aus wie eine Stufe (in der Mulde des Testteils ein Ring ums ganze
    Teil)."""
    raster = _wandlinien(feld, lage, z_unten, None)
    if grenze is None:
        return raster
    genau = _wandlinien(feld, lage, z_unten, grenze)
    if not genau:
        return raster
    alle = np.vstack([p for p, _g in genau])
    dazu = []
    for p, _g in raster:
        weit = _naechste(alle, p)[0] > 2.0 * feld.schritt
        if weit.any():
            dazu.append((p[weit], False))
    return genau + dazu


def _ringe_streifen(ablauf, feld, w, D, wand, breite, fahren, material_links, schritt, toleranz):
    """Die Ringe einer Zwischenlage von unten: an der Wand (D = 0) nur, wo `fahren` (je Punkt der
    Wandlinien `wand`, schon verbreitert); ist die Stufe (`breite`, je Punkt) breiter als ae, davor
    Ringe auf den Höhenlinien von D, je gleich weit bis höchstens 1,1 · ae (wie _ringe_zwischen),
    jeder nur, wo hinter ihm die Stufe weiter reicht als er (mehr als STUFE_AUSSEN · ae). Je Probe
    zählt der nächste Punkt der Wand."""
    ae = w.zeilenabstand
    alle = np.vstack([p for p, _g in wand])
    b = np.concatenate(breite)
    f = np.concatenate(fahren)
    if not f.any():
        return
    endlich = np.isfinite(D)
    erster = float(b[f].max()) - ae
    if endlich.any():
        erster = min(erster, float(D[endlich].max()))
    if erster <= 0:
        niveaus = [0.0]
    else:
        anzahl = max(1, int(math.ceil(erster / (1.1 * ae) - 1e-9)))
        niveaus = [erster * (anzahl - k) / anzahl for k in range(anzahl + 1)]
    breit = max(1, int(round(3.0 / schritt)))
    for nummer, niveau in enumerate(niveaus):
        ringe, nur = [], {}
        if niveau <= 0.0 and feld.grenze is not None:
            linien = [(None, ring) for ring in feld.grenze.ringe]
        else:
            linien = rb._hoehenlinien(D, feld.xs, feld.ys, niveau)
        for punkte, geschlossen in linien:
            if punkte is None:
                ring = geschlossen
            else:
                if len(punkte) < 2:
                    continue
                laenge = float(np.sum(np.hypot(*np.diff(punkte, axis=0).T)))
                if geschlossen and laenge < 2 * math.pi * min(ae, 1.0):
                    continue  # winzig
                ring = rb._ring_des_feldes(
                    punkte, geschlossen, material_links, feld, niveau, D, schritt, toleranz
                )
            if ring is None or len(ring.proben.x) < 2:
                continue
            _abstand, k = _naechste(alle, np.column_stack([ring.proben.x, ring.proben.y]))
            noetig = f[k]
            if niveau > 0.0:
                noetig = noetig & (b[k] - niveau > STUFE_AUSSEN * ae)
            if not noetig.any():
                continue
            nur[id(ring)] = rb.verbreitert(noetig, breit, ring.geschlossen)
            ringe.append(ring)
        # Nicht „eng“: Der Streifen ist schmaler als R − ae, die Mitte des Fräsers liegt weiter als
        # ae neben dem Material – „eng“ ließe jeden Ring an der Wand aus.
        rb._naechster_zuerst(ablauf, ringe, False, f"zwischen {nummer}", nur)


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


def _mit_genauer_grenze(schritt):
    """Rechnet eine Bahn in diesem Raster mit der genauen Grenze (ringgrenze)?"""
    return GENAUE_GRENZE and schritt <= GENAU_BIS_RASTER + 1e-9


def _lagen(oben, ziel, zustellung, zwischen, von_unten=False):
    """([(z, ist_zwischenlage, vorige)], ap der Hauptlagen) – die Hauptlagen von oben bis
    `ziel`, je höchstens `zustellung` und gleich weit, nach jeder die Zwischenlagen darüber bis
    zur vorigen Hauptlage, von oben nach unten (`von_unten`: von unten nach oben, dann reicht das
    Material über jeder bis zur Oberkante der Hauptlage); `vorige`: bis wohin das Material über
    der Lage höchstens reicht."""
    anzahl = max(1, int(math.ceil((oben - ziel - hf.LAGEN_SPIEL) / zustellung)))
    folge = []
    oberkante = oben
    for k in range(1, anzahl + 1):
        lage = oben - (oben - ziel) * k / anzahl
        folge.append((lage, False, oberkante))
        if zwischen > 0:
            teile = int(math.ceil((oberkante - lage) / zwischen - 1e-9))
            vorige = oberkante
            if von_unten:
                for m in range(1, teile):
                    folge.append((lage + (oberkante - lage) * m / teile, True, oberkante))
            else:
                for m in range(teile - 1, 0, -1):
                    z = lage + (oberkante - lage) * m / teile
                    folge.append((z, True, vorige))
                    vorige = z
        oberkante = lage
    return folge, (oben - ziel) / anzahl


def _hoehlung(feld, lage, hoehen, z_unten, im_raster):
    """Öffnet sich auf einer der Höhen `hoehen` (die Zwischenlagen über der Hauptlage `lage`) eine
    Höhlung – ein Stück des Erlaubten, das nichts vom Erlaubten der Hauptlage enthält?"""
    from scipy import ndimage

    unten = feld.erlaubt_feld(lage, z_unten) & im_raster
    for z in hoehen:
        oben = feld.erlaubt_feld(z, z_unten) & im_raster
        stuecke, anzahl = ndimage.label(oben)
        if anzahl and np.setdiff1d(np.arange(1, anzahl + 1), stuecke[unten & oben]).size:
            return True
    return False


def _spalt(feld, lage, hoehen, z_unten, im_raster, hoehe, r):
    """Öffnet sich auf einer der Höhen `hoehen` über der Hauptlage `lage` ein Spalt zwischen zwei
    Wänden – Erlaubtes, das die Hauptlage nicht erreichte, mittendrin gleich weit von zwei
    getrennten Stücken des Gesperrten und weiter als R von ihrem Erlaubten, mit Material darüber?
    Von unten käme der erste Ring dort mitten in den vollen Spalt (zwei Kuppeln, der Spalt öffnet
    sich 1,9 mm über der Hauptlage: 6,1 statt 3,3 ae, 3,87 statt 3,48 min; Gegenprüfer)."""
    from scipy import ndimage

    unten = feld.erlaubt_feld(lage, z_unten) & im_raster
    # So weit (mm) liegt jede Zelle vom Erlaubten der Hauptlage – von dort ginge ein Ring hinein.
    vom_freien = ndimage.distance_transform_edt(~unten) * feld.schritt
    for z in hoehen:
        erlaubt = feld.erlaubt_feld(z, z_unten) & im_raster
        neu = erlaubt & ~unten & (vom_freien > r) & (hoehe > z + MATERIAL)
        if not neu.any():
            continue
        stuecke, anzahl = ndimage.label(~erlaubt & im_raster)
        if anzahl < 2:
            continue
        # Je Zelle das nächste Stück des Gesperrten; wo zwei Nachbarn verschiedene haben, liegt
        # die Mitte zwischen ihnen.
        naechstes = ndimage.distance_transform_edt(
            stuecke == 0, return_distances=False, return_indices=True
        )
        welches = stuecke[naechstes[0], naechstes[1]]
        mitte = np.zeros_like(neu)
        mitte[1:, :] |= welches[1:, :] != welches[:-1, :]
        mitte[:, 1:] |= welches[:, 1:] != welches[:, :-1]
        if (mitte & neu).any():
            return True
    return False


def _von_oben(folge, ab):
    """Die Zwischenlagen in `folge` ab Stelle `ab` bis zur nächsten Hauptlage wieder von oben nach
    unten (wie _lagen ohne `von_unten`), an Ort und Stelle."""
    bis = ab
    while bis < len(folge) and folge[bis][1]:
        bis += 1
    if bis == ab:
        return
    vorige = folge[ab][2]  # von unten: die Oberkante des Abschnitts
    for k, z in enumerate(sorted((folge[i][0] for i in range(ab, bis)), reverse=True)):
        folge[ab + k] = (z, True, vorige)
        vorige = z


def _schruppen(
    st,
    netz,
    w,
    z_unten,
    variante,
    r,
    schritt,
    zwischen,
    davor=None,
    stand=None,
    nur=None,
    von_unten=False,
):
    """Alle Lagen in der Variante (die der Hauptlagen); gibt (Hauptlagen, Zwischenlagen) mit
    Schnitt zurück. Mit `davor` (Form des größeren Fräsers davor) nur der Rest: jede Lage wie
    eine Zwischenlage, das Material aus _nach_davor. Mit `stand` (Materialstand) ebenso, wenn
    er nicht überall das volle Rohteil zeigt. Mit `nur` (_Nur) zählt es, was rings um die Flächen
    noch steht (`st.drumherum`), und gilt `nur.an`, dort schon als gefräst: nur über den Flächen,
    jede Lage wie eine Zwischenlage. Mit `von_unten` die Zwischenlagen von unten nach oben, je ein
    Streifen an der Wand mit voller Tiefe (VON_UNTEN, _ringe_streifen) – nicht im Rest und nicht
    mit Materialstand (dann wie bisher von oben)."""
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
    mit_stand = False
    if stand is not None:
        hoehe, oben, mit_stand = _mit_stand(
            st, feld, netz, stand, hoehe, oben, ziel, z_unten, zugabe
        )
        if oben <= ziel + MATERIAL:
            return 0, 0  # über den Flächen steht nichts mehr, was der Fräser erreicht
        if mit_stand and variante != "rohteil":
            raise rb._KeinMorph()  # jede Lage wie eine Zwischenlage: keine Varianten
    vom_material = False  # die Hauptlagen: Ringe vom Rand dessen her, was noch steht
    if nur is not None:
        hoehe, oben, vom_material = _nur_ueber(st, feld, nur, hoehe, oben, ziel, z_unten, zugabe, w)
        if vom_material:
            if oben <= ziel + MATERIAL:
                return 0, 0
            if variante != "rohteil":
                raise rb._KeinMorph()
    aufweiten = _Aufweiten(feld)
    stempel = _scheibe(r, schritt)
    gx, gy = np.meshgrid(feld.xs, feld.ys, indexing="ij")
    im_raster = feld.im_raster(gx, gy)
    r_ein = w.einfahrradius if w.einfahrradius and w.einfahrradius > 0 else kb.EINFAHRT_ANTEIL * r
    gerade = kb.GERADE_ANTEIL * r
    material_links = not w.gleichlauf  # Gleichlauf (M3): das Material rechts
    haupt = zwischenlagen = 0
    # Nicht im Rest (davor: dort steht kein Streifen an einer Wand, sondern was der große Fräser in
    # Ecken und Kehlen ließ) und nicht mit Materialstand: Die Treppe weiß nicht, was Operationen
    # davor an den Wänden nahmen oder stehen ließen – in der Mulde des Testteils fuhr sonst ein Ring
    # ums ganze Teil (1,32 statt 1,29 min, 948 statt 158 Halte, Eingriff bis 3,6 ae).
    von_unten = bool(von_unten) and davor is None and not mit_stand
    genau = GENAUE_GRENZE and schritt <= GENAU_BIS_RASTER + 1e-9
    nachrechner = rg.Nachrechner(feld, netz, geformt) if genau else None
    folge, ap_haupt = _lagen(oben, ziel, zustellung, zwischen, von_unten)
    stehen_bis = None  # bis hierhin steht Material über einer Zwischenlage, die ausfiel
    treppe = _Treppe()  # von unten: bis wohin die Spitze an der Wand war
    waende = {}  # von unten: je Lage (erlaubt, genaue Grenze, Wandlinien) – für den Blick voraus

    def wand_bei(z):
        """(erlaubt, Grenze oder None, Wandlinien) der Lage z – einmal gerechnet."""
        schluessel = round(z, 9)
        if schluessel not in waende:
            erl = feld.erlaubt_feld(z, z_unten)
            grenze = None
            if nachrechner is not None:
                wo = (rechteck[1] | rechteck[2]) & aufweiten(hoehe > z + MATERIAL, r + schritt)
                grenze = nachrechner.grenze(z, z_unten, erl, material_links, schritt, wo)
            waende[schluessel] = (erl, grenze, _wandlinien(feld, z, z_unten, grenze))
        return waende[schluessel]

    unten = von_unten  # in diesem Abschnitt (bis zur nächsten Hauptlage) von unten
    # Von unten ohne genaue Grenze (_RUECKFALL): bis wohin das Material je Zelle sicher noch reicht
    # – gesenkt nur, wo die ganze Zelle gefräst ist. Für den Eilgang hinab; `hoehe` für die Ringe.
    sicher = None
    for nummer, (lage, zwischenlage, vorige) in enumerate(folge):
        if not zwischenlage:
            stehen_bis = None
            waende.clear()
            if sicher is not None:
                hoehe = np.maximum(hoehe, sicher)  # auch die Lagen darunter rechnen damit
                sicher = None
            unten = von_unten
            if von_unten:
                # Bis an die Wand der Hauptlage ist danach alles frei – auch wenn sie ausfällt.
                treppe.setze(_hauptlinien(feld, lage, z_unten, wand_bei(lage)[1]))
                hoehen = []
                for z, ist, _v in folge[nummer + 1 :]:
                    if not ist:
                        break
                    hoehen.append(z)
                if (
                    treppe.leer()
                    or _hoehlung(feld, lage, hoehen, z_unten, im_raster)
                    or _spalt(feld, lage, hoehen, z_unten, im_raster, hoehe, r)
                ):
                    # Öffnet sich über der Hauptlage eine Höhlung, die nicht an ihr Freies grenzt:
                    # Von unten ginge die erste Lage darin mit voller Tiefe über die Rampe, der
                    # erste Ring um die Mitte in voller Breite (an der Schale 4,4 ae auf 50 mm). In
                    # diesem Abschnitt wie bisher von oben, je über die Rampe der dünnen Lage –
                    # ebenso ein Spalt zwischen zwei Wänden (_spalt).
                    unten = False
                    _von_oben(folge, nummer + 1)
        elif stehen_bis is not None and not unten:
            # Fiel die Zwischenlage darüber aus, steht ihr Material noch: Die Einfahrt rechnet
            # mit der Höhe davor, nicht mit der ausgefallenen Lage (sonst endet der Eilgang hinab
            # im Material – an der Schale mit 5 mm Rohteil darüber 1,9 mm tief, 217 mm³;
            # Sicherheitsprüfung, nachgestellt am 2026-11-13).
            vorige = max(vorige, stehen_bis)
        erlaubt = feld.erlaubt_feld(lage, z_unten)
        gesperrt = _breiter(~erlaubt)
        werte = w
        # Der Rest (davor, Materialstand, nur über den Flächen): nur, wo Material steht.
        ist_zwischen = zwischenlage or davor is not None or mit_stand
        # Eine Lage über dem ganzen Teil (nichts gesperrt): Das Rohteil steht über dem Teil. Sie
        # fährt wie ein Klotz im Freien – Ringe vom Rand des Materials her (wie `vom_material`).
        # Bis 0.366.5 fiel sie aus (die Ringe der Zwischenlage folgen dem Gesperrten): Über einer
        # Kuppel blieb die Säule Rohteil stehen, in der Schale tauchte die erste Lage darunter
        # senkrecht mit voller Stirn ein.
        ueber_allem = ist_zwischen and not bool((gesperrt & im_raster).any())
        # Von unten nach oben nimmt die unterste Lage über dem ganzen Teil alles darüber mit (bis
        # zur Oberkante der Hauptlage, nie tiefer als die Zustellung) – die darüber finden nichts.
        if (
            ueber_allem
            and zwischenlage
            and not unten
            and nummer + 1 < len(folge)
            and folge[nummer + 1][1]
        ):
            # Ist auch die Zwischenlage darunter noch über dem ganzen Teil, nimmt die das Material
            # mit – eine Lage mit voller Tiefe statt mehrerer dünner (an der Schale mit 5 mm
            # darüber 16 statt 4 min), solange es nicht tiefer wird als die Zustellung.
            tiefer = folge[nummer + 1][0]
            hoch = float(hoehe[np.isfinite(hoehe)].max()) if np.isfinite(hoehe).any() else lage
            frei_darunter = not bool(
                (_breiter(~feld.erlaubt_feld(tiefer, z_unten)) & im_raster).any()
            )
            if frei_darunter and hoch - tiefer <= zustellung + GLEICH:
                if bool((hoehe > lage + MATERIAL).any()):
                    stehen_bis = vorige if stehen_bis is None else max(stehen_bis, vorige)
                continue
        streifen = unten and zwischenlage and not ueber_allem and not treppe.leer()
        if streifen:
            # Von unten nach oben (VON_UNTEN): nur der Streifen an der Wand, mit voller Tiefe.
            ueber = hoehe > lage + MATERIAL
            if not ueber.any():
                continue
            erlaubt, grenze, wand = wand_bei(lage)
            gesperrt = _breiter(~erlaubt)
            D = grenze.abstand if grenze is not None else feld.abstand_zu(gesperrt & im_raster)
            # Material steht, wo die Stirn an der Wand etwas trifft, das höher reicht als die
            # Lage (der Streifen selbst ist oft schmaler als eine Zelle, die Säule dahinter nicht).
            steht = aufweiten(ueber, r + schritt)
            # Was das Raster in Reichweite der Wand selbst als Material sieht: Ein Spalt, der sich
            # erst über der Hauptlage öffnet, hat keine Wand der Hauptlage in sich – die Treppe
            # mäße zur Wand daneben, und der Spalt bliebe voll. Eine Zelle weniger weit als die
            # Stirn (wie die Zwischenlage von oben): Der Rand an einer senkrechten Wand zählte sonst
            # jede Lage (in der Mulde des Testteils ein Ring ums ganze Teil, Eingriff 3,6 ae).
            erreichbar = np.argwhere(ueber & (-(r - schritt - 0.01) < D) & im_raster)
            erreichbar = np.column_stack([feld.xs[erreichbar[:, 0]], feld.ys[erreichbar[:, 1]]])
            voll = np.argwhere(ueber & (-(r - 0.01) < D) & im_raster)
            voll = np.column_stack([feld.xs[voll[:, 0]], feld.ys[voll[:, 1]]])
            # Material weiter als R von jeder Wand der Lage – über einer Fläche, die mit dieser
            # Lage auf einmal frei wird (ein Absatz): Dort fährt kein Streifen; es räumt wie die
            # Zwischenlage von oben, von außen nach innen (am Geist blieben sonst an beiden Enden
            # 20 mm über dem Teil stehen).
            frei_material = ueber & aufweiten(~gesperrt, r - schritt - 0.01) & im_raster
            if wand and frei_material.any():
                ij = np.argwhere(frei_material)
                xy = np.column_stack([feld.xs[ij[:, 0]], feld.ys[ij[:, 1]]])
                nah = _naechste(np.vstack([p for p, _g in wand]), xy)[0] <= r
                frei_material[ij[nah, 0], ij[nah, 1]] = False
            absatz = frei_material.sum() * schritt * schritt >= MINDESTFLAECHE

            # _RUECKFALL: Das Raster sieht die Stufe bis eine Zelle zu breit.
            fehler = 0.0 if grenze is not None else schritt

            def stufe(p, treppe=treppe, erreichbar=erreichbar, voll=voll, steht=steht, f=fehler):
                return _stufe(p, treppe, erreichbar, voll, steht, feld, r, schritt, f)

            breite, fahren = [], []
            for p, geschlossen in wand:
                b = stufe(p)
                breite.append(b)
                fahren.append(
                    rb.verbreitert(b >= STUFE_ORT, max(1, int(round(3.0 / schritt))), geschlossen)
                    & (b > 0.0)
                )
            breitest = max((float(b.max()) for b in breite), default=0.0)
            if breitest < STUFE_ORT and not absatz:
                continue
            # Der Blick voraus: Würde die Stufe bis zur nächsten Lage (oder bis zur Oberkante der
            # Hauptlage) breiter als STUFE, kommt diese Lage – sonst fällt sie aus.
            if breitest < STUFE - GLEICH and not absatz:
                naechste = folge[nummer + 1] if nummer + 1 < len(folge) else None
                if naechste is not None and naechste[1]:
                    voraus = wand_bei(naechste[0])[2]
                else:
                    voraus = _wandlinien(feld, vorige, z_unten, None)
                weiter_breit = max((float(stufe(p).max()) for p, _g in voraus), default=0.0)
                if weiter_breit <= STUFE + GLEICH:
                    continue
            # So viel Material je mm Weg wie in der Hauptlage (ae · ap), höchstens der Radius.
            weiter = min(r, max(ae, ae * ap_haupt / max(vorige - lage, GLEICH)))
            werte = dataclasses.replace(w, zeilenabstand=weiter)
            feld.grenze = grenze
            # Rohteil ist, was über der Lage steht und die Stirn von der Wand aus trifft – für das
            # Einfahren (ungeschnitten); berührt (für die Läufe) auch die Säule dahinter.
            feld.rohteil_zellen = ueber & (-(r - 0.01) < D)
            if grenze is None:
                # _RUECKFALL: zum Einfahren eine Zelle mehr Material, auch hinter der Stirn.
                feld.rohteil_zellen = _breiter(ueber) & (-(r + schritt) < D)
            feld.beruehrt = aufweiten(ueber & aufweiten(erlaubt, r + schritt), r + schritt)
            feld.eng = feld.beruehrt
            feld.frei[:] = False
            ablauf = _Lage3D(
                st, feld, werte, r, r_ein, gerade, lage, vorige, erlaubt, schritt, oben
            )
            ablauf.hoehe = hoehe
            if grenze is None:  # _RUECKFALL: hinab nur bis über das, was sicher noch steht
                if sicher is None:
                    sicher = hoehe.copy()
                ablauf.hoehe = sicher
            ablauf.stempel = stempel
            ablauf.streifen = True
            ablauf.schwelle = _Lage3D(
                st, feld, w, r, r_ein, gerade, lage, vorige, erlaubt, schritt, oben
            ).schwelle
            if grenze is None:
                # _RUECKFALL: Unter der Stirn stünde kein dünner Rand (wie im Streifen ae), sondern
                # die Säule bis zur Oberkante – hinab und hinein nur, wo nichts darunter steht.
                ablauf.schwelle = 0.0
            vorher = st.ringe
            if absatz and np.isfinite(D).any():
                _ringe_zwischen(
                    ablauf, feld, werte, D, frei_material, material_links, schritt, glatt, aufweiten
                )
            if wand and breitest >= STUFE_ORT:
                _ringe_streifen(
                    ablauf, feld, werte, D, wand, breite, fahren, material_links, schritt, glatt
                )
            ablauf.reste_fahren()
            ablauf.heben()
            if sicher is not None:
                # _RUECKFALL: sicher gefräst nur, wo auch die Nachbarn der Zelle frei sind.
                ganz = feld.frei if grenze is not None else ~_breiter(~feld.frei)
                sicher[ganz] = np.minimum(sicher[ganz], lage)
            hoehe[feld.frei] = np.minimum(hoehe[feld.frei], lage)
            if st.ringe > vorher:
                zwischenlagen += 1
                treppe.dazu([p[f] for (p, _g), f in zip(wand, fahren, strict=True)])
            continue
        if ueber_allem:
            if not feld.material_setzen(hoehe, hoehe, lage, erlaubt):
                if zwischenlage and bool((hoehe > lage + MATERIAL).any()):
                    stehen_bis = vorige if stehen_bis is None else max(stehen_bis, vorige)
                continue
            # Die Schicht ist dünner als die Hauptlage: die Ringe so weit auseinander, dass je mm
            # Weg so viel Material fällt wie dort (ae · ap), höchstens 0,8 · Radius – wie in den
            # Zwischenlagen darunter (dort bis zum Radius). Mit ae blieb es bei 6 Ringen (470 mm
            # Weg) für 2,4 mm über einer Kuppel von 20 × 16 mm.
            dick = float(hoehe[np.isfinite(hoehe)].max()) - lage
            # Nicht ganz der Radius: Der letzte Ring muss die Mitte sicher decken, auch wenn die
            # Höhenlinie dort zu klein für einen Ring ist.
            breit = max(ae, min(0.8 * r, r - 2.0 * schritt))
            weiter = min(breit, max(ae, ae * ap_haupt / max(dick, GLEICH)))
            werte = dataclasses.replace(w, zeilenabstand=weiter)
        elif ist_zwischen:
            # Die Ringe nur für das, was über der Lage steht und der Fräser hier erreicht – eine
            # Zelle weniger weit als die Stirn vom Freien, damit der Rand am Gesperrten (den der
            # Ring bei D = 0 nicht nimmt) nicht jede Lage zählt. Für das Einfahren zählt alles
            # Material, das die Stirn treffen kann.
            ueber = hoehe > lage + MATERIAL
            material = ueber & aufweiten(~gesperrt, r - schritt - 0.01)
            if material.sum() * schritt * schritt < MINDESTFLAECHE:
                if zwischenlage and bool(ueber.any()):
                    stehen_bis = vorige if stehen_bis is None else max(stehen_bis, vorige)
                continue
            # So viel Material je mm Weg wie in der Hauptlage (ae · ap), höchstens der Radius.
            weiter = min(r, max(ae, ae * ap_haupt / max(vorige - lage, GLEICH)))
            werte = dataclasses.replace(w, zeilenabstand=weiter)
            feld.rohteil_zellen = ueber & aufweiten(erlaubt, r - 0.01)
            feld.beruehrt = aufweiten(feld.rohteil_zellen, r)
            feld.eng = aufweiten(feld.rohteil_zellen, weiter + schritt)
        elif vom_material:
            # Nur über den Flächen, ringsum gefräst: ein Klotz im Freien. Die Ringe vom Rohteil
            # her beginnen an seinem Rand, hinab geht es daneben, quer hinein mit vollem ap – wie
            # das Räumen mit Materialstand (raeumen_bahn._Feld.material_setzen). Als Zwischenlage
            # führe die Hauptlage per Helix am Rand hinab (Kuppel: 3,6 statt 3,4 min).
            if not feld.material_setzen(hoehe, hoehe, lage, erlaubt):
                continue
        else:
            feld.rohteil_zellen, feld.beruehrt, feld.eng = rechteck
        feld.frei[:] = False
        ablauf = _Lage3D(st, feld, werte, r, r_ein, gerade, lage, vorige, erlaubt, schritt, oben)
        ablauf.hoehe = hoehe
        ablauf.stempel = stempel
        if (vom_material and not ist_zwischen) or ueber_allem:
            ablauf.stand_hoehe = hoehe
        if ist_zwischen:
            # Einfahren wie in der Hauptlage: unter der Stirn höchstens so viel Material wie im
            # Streifen ae der Hauptlage – nicht die breiteren Ringe der Zwischenlage.
            ablauf.schwelle = _Lage3D(
                st, feld, w, r, r_ein, gerade, lage, vorige, erlaubt, schritt, oben
            ).schwelle
        # Die Grenze zwischen den Knoten, aus der Hüllfläche selbst (ringgrenze): Der Ring an der
        # Wand folgt ihr statt den Zellen, die Ringe davor ihrem Abstand. Hält sie nicht (ein Ring
        # träfe beim Nachrechnen das Teil), bleibt es auf dieser Lage beim Raster.
        feld.grenze = None
        if nachrechner is not None and not ueber_allem:  # über dem ganzen Teil: keine Grenze
            # Nur die Linien, an denen ein Ring fahren kann: wo die Stirn das Rohteil trifft – auf
            # einer Zwischenlage nur nahe dem Material, das sie nimmt (die anderen Ringe fallen in
            # _ringe_zwischen ohnehin weg; am Testteil die halbe Rechenzeit).
            wo = feld.beruehrt | feld.eng
            if ist_zwischen:
                wo &= aufweiten(material, r + schritt)
            feld.grenze = nachrechner.grenze(lage, z_unten, erlaubt, material_links, schritt, wo)
        if feld.grenze is not None:
            D = feld.grenze.abstand
            if ist_zwischen and RAND_ZAEHLT:
                # Der Ring an der genauen Grenze reicht weiter an die Wand als der aus dem Raster:
                # Material ist, was seine Stirn trifft (wieder eine Zelle weniger) – sonst fiele
                # er aus, wo nur der Rand an der Wand steht (im Tal zwischen zwei Kuppeln blieben
                # 0,7 mm mehr stehen als aus dem Raster).
                material = ueber & (-(r - schritt - 0.01) < D)
        else:
            D = feld.abstand_zu(gesperrt & im_raster)
        vorher = st.ringe
        if ueber_allem:
            rb._ringe_vom_rohteil(ablauf, feld, werte, r, D, material_links, schritt, glatt)
        elif ist_zwischen:
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
        if feld.mit_material:
            feld.ganzes_rohteil()
        hoehe[feld.frei] = np.minimum(hoehe[feld.frei], lage)
        if st.ringe > vorher:
            stehen_bis = None
            if zwischenlage:
                zwischenlagen += 1
            else:
                haupt += 1
        elif zwischenlage and bool((hoehe > lage + MATERIAL).any()):
            stehen_bis = vorige if stehen_bis is None else max(stehen_bis, vorige)
        if unten and zwischenlage and st.ringe > vorher and treppe.leer():
            # Die erste Zwischenlage, die etwas nahm, wo die Hauptlage nichts fand (eine Höhlung):
            # Bis an ihre Wand war die Spitze.
            treppe.setze(_hauptlinien(feld, lage, z_unten, feld.grenze))
    feld.rohteil_zellen, feld.beruehrt, feld.eng = rechteck
    feld.grenze = None
    return haupt, zwischenlagen


@dataclass
class _Nur:
    """Für _schruppen: die Freiformflächen als Dreiecke (_flaechen_netze – für den Bereich über
    ihnen; eine Form ginge nicht an einen Nebenrechner) und ob dort nur geschruppt wird („Nur über
    den gewählten Flächen“); `maske` merkt den Bereich für die Varianten (dasselbe Raster)."""

    netze: list
    an: bool = False
    maske: object = None


def _flaechen_netze(form_teil, namen, schritt):
    """[(Punkte (n, 2) in x, y, Dreiecke (m, 3))] je Fläche `namen` – vernetzt so fein wie das
    Raster `schritt` (mindestens 0,05 mm); eine Fläche ohne Netz fehlt."""
    from . import vierachs_flaechen as vf

    netze = []
    for nummer in vf.nummern(namen):
        try:
            # Eine Kopie vernetzen: tessellate am Original ersetzt dessen Netz, und alles danach
            # (Simultanschlichten, Materialstand) rechnete mit anderen Dreiecken (P-2026-10-18-64).
            flaeche = ft.flaeche(form_teil, nummer).copy()
            punkte, dreiecke = flaeche.tessellate(max(schritt, 0.05))
        except Exception:  # noqa: BLE001 – eine Fläche ohne Netz: ohne sie
            continue
        if not punkte or not dreiecke:
            continue
        netze.append(
            (
                np.array([(q.x, q.y) for q in punkte], dtype=float),
                np.asarray(dreiecke, dtype=np.int64).reshape(-1, 3),
            )
        )
    return netze


# So viel Rohteil (mm³) muss rings um die Flächen stehen, damit der Assistent davon spricht.
DRUMHERUM_AB = 1000.0


def _nur_ueber(st, feld, nur, hoehe, oben, ziel, z_unten, zugabe, w):
    """„Nur über den gewählten Flächen“ (Manuel, 2026-10-17, Frage 6: „hey schau mal du das
    rohteil ist dort noch komplett voll mit material .. wir müssen erst die schräge fläche
    wegplanen und dann können wir die tasche fräsen oder ist rohteil schon fertig so das nurnoch
    die tasche zu fräsen ist“): Der Bereich über den Flächen, bis Radius und Zeilenabstand darüber
    hinaus (sonst bliebe ihr Rand stehen, und am Fuß einer Kuppel hat ein Ring Platz). Was
    außerhalb noch über dem Teil steht, zählt `st.drumherum` (mm³) – für den Satz im Assistenten.
    Mit `nur.an` gilt es als schon gefräst (etwa in einem anderen Job): Die Höhen dort sind frei,
    die Lagen beginnen am höchsten Material im Bereich. Gibt (Höhen, oben, ob nur dort) zurück."""
    if nur.maske is None or nur.maske.shape != hoehe.shape:
        nur.maske = feld.aufweiten(_ueber_den_flaechen(feld, nur.netze), feld.r + w.zeilenabstand)
    bereich = nur.maske
    spitze = np.where(feld.roh <= z_unten + GLEICH, z_unten, feld.roh + zugabe)
    boden = np.maximum(spitze, ziel)
    draussen = feld.rohteil_zellen & ~bereich & (hoehe > boden + MATERIAL)
    st.drumherum = float(np.sum((hoehe - boden)[draussen])) * feld.schritt * feld.schritt
    if not nur.an:
        return hoehe, oben, False
    hoehe = np.where(bereich, hoehe, -np.inf)
    tief = rb._kleinstes_um(spitze, int(max(feld.r - feld.schritt - 0.01, 0.0) / feld.schritt))
    erreicht = bereich & (hoehe > np.maximum(tief, ziel) + MATERIAL)
    if not erreicht.any():
        return hoehe, ziel, True
    return hoehe, min(oben, float(hoehe[erreicht].max())), True


def _ueber_den_flaechen(feld, netze):
    """(nx, ny): Knoten, über denen von oben gesehen eine der Flächen liegt – aus ihren Netzen
    (_flaechen_netze), je Dreieck die Knoten darin (und die nächsten an seinen Ecken: ein steiles,
    schmales Dreieck trifft sonst keinen)."""
    maske = np.zeros((feld.nx, feld.ny), dtype=bool)
    xs, ys = np.asarray(feld.xs), np.asarray(feld.ys)
    for p, dreiecke in netze:
        i = np.clip(np.rint((p[:, 0] - xs[0]) / feld.schritt).astype(int), 0, feld.nx - 1)
        j = np.clip(np.rint((p[:, 1] - ys[0]) / feld.schritt).astype(int), 0, feld.ny - 1)
        maske[i, j] = True
        for a, b, c in p[dreiecke]:
            i0, i1 = np.searchsorted(xs, min(a[0], b[0], c[0])), np.searchsorted(
                xs, max(a[0], b[0], c[0]), side="right"
            )
            j0, j1 = np.searchsorted(ys, min(a[1], b[1], c[1])), np.searchsorted(
                ys, max(a[1], b[1], c[1]), side="right"
            )
            if i0 >= i1 or j0 >= j1:
                continue
            gx, gy = np.meshgrid(xs[i0:i1], ys[j0:j1], indexing="ij")
            d1 = (gx - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (gy - b[1])
            d2 = (gx - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (gy - c[1])
            d3 = (gx - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (gy - a[1])
            negativ = (d1 < 0) | (d2 < 0) | (d3 < 0)
            positiv = (d1 > 0) | (d2 > 0) | (d3 > 0)
            maske[i0:i1, j0:j1] |= ~(negativ & positiv)
    return maske


def _mit_stand(st, feld, netz, stand, hoehe, oben, ziel, z_unten, zugabe):
    """Der Materialstand im Raster (W-012): (Höhen, wo die Lagen beginnen, ob er gilt) – die
    Höhen nicht über dem, was der Stand zeigt; gilt er (nicht überall das volle Rohteil über den
    Lagen), beginnen die Lagen am höchsten Material, das der Fräser erreicht. Zählt dazu, was
    über dem Teil noch steht und was die Operationen davor dort schon weggenommen haben."""
    rohteil = feld.rohteil_zellen
    vom_stand = np.where(rohteil, stand.hoehen_an(feld.xs, feld.ys), -np.inf)
    bereich = rohteil & feld.aufweiten(feld.erlaubt_feld(ziel, z_unten), feld.r)
    maske = stand.maske_aus(feld.xs, feld.ys, bereich)
    wer = stand.wer(maske)
    if wer:  # nur dann steht die Zeile darunter: über dem Teil, nicht über seinem Tiefsten
        teil = hf.hoehen(netz, stand.quader.x, stand.quader.y)
        noch, weg = stand.volumen(maske, ziel, np.where(np.isfinite(teil), teil, ziel))
        st.noch += noch
        st.weg += weg
        st.davor += [name for name in wer if name not in st.davor]
    if not (rohteil & (vom_stand < oben - GLEICH)).any():
        return hoehe, oben, False
    hoehe = np.where(rohteil, np.minimum(hoehe, vom_stand), -np.inf)
    spitze = np.where(feld.roh <= z_unten + GLEICH, z_unten, feld.roh + zugabe)
    tief = rb._kleinstes_um(spitze, int(max(feld.r - feld.schritt - 0.01, 0.0) / feld.schritt))
    erreicht = rohteil & (hoehe > np.maximum(tief, ziel) + MATERIAL)
    if not erreicht.any():
        return hoehe, ziel, True
    return hoehe, min(oben, float(hoehe[erreicht].max())), True


def bereich(form_teil, namen):
    """(Namen der Freiformflächen unter `namen`, ihr tiefster Punkt z) – ValueError mit einem
    Satz, wenn keine darunter ist."""
    from . import vierachs_flaechen as vf

    flaechen = sb.freiformflaechen(form_teil, namen)
    if not flaechen:
        raise ValueError(tr("r3.fehler.keine"))
    from . import stl_teil

    daten = stl_teil.daten(form_teil)
    if daten is not None:  # ein Körper aus einem STL: alle Dreiecke auf einmal
        z_unten = daten.kasten(daten.nummern(flaechen))[4]
    else:
        z_unten = min(ft.flaeche(form_teil, n).BoundBox.ZMin for n in vf.nummern(flaechen))
    return flaechen, z_unten


def variante_rechnen(
    netz, w, z_unten, r, schritt, zwischen, davor, stand, nur, variante, von_unten=False
):
    """Auch im Nebenrechner: alle Lagen in einer Variante – (_Stand, Hauptlagen, Zwischenlagen),
    None, wo es die Variante nicht gibt (_KeinMorph)."""
    st = rb._Stand()
    try:
        haupt, zwischenlagen = _schruppen(
            st, netz, w, z_unten, variante, r, schritt, zwischen, davor, stand, nur, von_unten
        )
    except rb._KeinMorph:
        return None
    return st, haupt, zwischenlagen


def _varianten_verteilt(argumente, varianten):
    """{Variante: was variante_rechnen ergab} – die Varianten je auf einem Nebenrechner,
    gleichzeitig (sie hängen nicht voneinander ab; vorher nacheinander im Fenster, W-036). Das
    Fenster zeichnet beim Warten neu; in einem Nebenrechner (die Vorschau) als Unteraufträge. Leer
    mit einer Variante oder ohne Nebenrechner; was ein Arbeiter nicht lieferte, fehlt – das
    rechnet planen() selbst, mit genau seinem Fehler."""
    import secrets

    if len(varianten) < 2:
        return {}
    try:
        from . import nebenrechner as nr
    except ImportError:
        return {}
    netz, w, z_unten, r, schritt, zwischen, davor, stand, nur, von_unten = argumente
    auftraege, schluessel = {}, []
    try:
        pool = nr.pool()
        if not pool.verfuegbar():
            return {}
        gemeinsam = []
        for name, wert in (("netz", netz), ("stand", stand), ("nur", nur)):
            if wert is None:
                gemeinsam.append(None)
                continue
            kennung = f"schruppen3d-{name}-{secrets.token_hex(8)}"
            schluessel.append(kennung)
            gemeinsam.append(pool.gemeinsam(kennung, wert))
        for v in varianten:
            auftraege[v] = pool.auftrag(
                "schruppen3d_bahn",
                "variante_rechnen",
                gemeinsam[0],
                w,
                z_unten,
                r,
                schritt,
                zwischen,
                davor,
                gemeinsam[1],
                gemeinsam[2],
                v,
                von_unten,
            )
        pool.warten(list(auftraege.values()), zwischendurch=nr.ereignisse_ohne_eingaben)
    except nr.Fehler:
        for a in auftraege.values():  # was fertig ist, gilt; den Rest rechnet planen() selbst
            if not a.fertig:
                a.abbrechen()
    finally:
        for kennung in schluessel:
            pool.vergessen(kennung)
    return {
        v: a.ergebnis
        for v, a in auftraege.items()
        if a.fertig and a.fehler is None and not a.abgebrochen
    }


def planen(
    form_teil,
    namen,
    werte,
    zwischen=ZWISCHEN,
    toleranz=hf.TOLERANZ,
    schritt=SCHRITT,
    davor=None,
    stand=None,
    nachbereiten=None,
    nur_ueber=False,
    von_unten=False,
    _nur_diese=False,
):
    """Die Bahn „3D-Schruppen“ (Schruppbahn) über den Freiformflächen `namen` von `form_teil`
    mit den Werten `werte` (raeumen_bahn.Raeumwerte; `aufmass` gilt überall, auch unten) – mit
    `davor` (Form des größeren Fräsers davor, ebene Stirn) nur der Rest, den er ließ; mit
    `stand` (materialstand, W-012) nur, was die Operationen davor im Job übrig ließen; mit
    `nur_ueber` gilt das Rohteil rings um die Freiformflächen als schon gefräst: nur über ihnen
    (nicht an einem Teil aus einem STL, nicht im Rest); mit `von_unten` die Zwischenlagen von unten
    nach oben, je ein Streifen an der Wand mit voller Tiefe (VON_UNTEN; nicht im Rest). ValueError
    mit einem Satz, wenn es nicht geht."""
    from . import vierachs_flaechen as vf

    if von_unten and not _nur_diese and davor is None and not _mit_genauer_grenze(schritt):
        # Ohne genaue Grenze (die Vorschau, eine Auflösung gröber als GENAU_BIS_RASTER) fährt der
        # Weg von unten vorsichtig (_RUECKFALL) – an dünnen Wänden viel langsamer als von oben
        # (Zweifler, zweite Runde: ein Ring mit 1,5 mm Wand im Raster 1,0 11,3 statt 5,4 min, 52 %
        # des Vorschubwegs in der Luft). Dort beide Reihenfolgen, die schnellere gilt: nie
        # langsamer als von oben.
        gemeinsam = (form_teil, namen, werte, zwischen, toleranz, schritt, davor, stand)
        unten = planen(*gemeinsam, nachbereiten, nur_ueber, True, True)
        oben = planen(*gemeinsam, nachbereiten, nur_ueber, False)
        return unten if unten.zeit <= oben.zeit else oben
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
    from . import stl_teil

    # Ein Teil aus einem STL: jedes Dreieck eine Fläche – ohne „nur über den Flächen“.
    nur = None
    if davor is None and stl_teil.daten(form_teil) is None:
        nur = _Nur(_flaechen_netze(form_teil, _flaechen, schritt), bool(nur_ueber))
    if davor is not None and vp.ebener_radius(davor) <= 0:
        raise ValueError(tr("ra.fehler.form"))
    varianten = (w.variante,) if w.variante in rb.VARIANTEN else rb.VARIANTEN
    if davor is not None:
        varianten = ("rohteil",)  # jede Lage wie eine Zwischenlage: keine Varianten
    ergebnisse = {}
    wer_davor = []  # wer vorher dort weggenommen hat (für den Satz, wenn nichts zu tun ist)
    argumente = (netz, w, z_unten, r, schritt, zwischen, davor, stand, nur, bool(von_unten))
    verteilt = _varianten_verteilt(argumente, varianten)
    for variante in varianten:
        if variante in verteilt:
            gerechnet = verteilt[variante]
        else:
            gerechnet = variante_rechnen(*argumente[:-1], variante, argumente[-1])
        if gerechnet is None:
            continue
        st, haupt, zwischenlagen = gerechnet
        wer_davor = st.davor
        if st.ringe == 0:
            continue
        zeit = bn.zeit(st.punkte, w.vorschub if w.vorschub > 0 else 1000.0, w.eintauchen or None)
        bahn = Schruppbahn(
            st.punkte,
            haupt,
            zwischenlagen,
            st.ringe,
            st.laeufe,
            st.z_min if math.isfinite(st.z_min) else 0.0,
            st.laenge,
            zeit,
            variante,
            rampen=st.rampen,
            noch=st.noch,
            weg=st.weg,
            davor=st.davor,
            drumherum=getattr(st, "drumherum", 0.0),
            nur_ueber=bool(nur is not None and nur.an),
        )
        if nachbereiten is not None:
            # Rampen und freie Verbindungen gehören zur gefahrenen Zeit: erst
            # danach vergleichen, statt den Sieger der Rohbahn zu verändern.
            nachbereiten(bahn)
        ergebnisse[variante] = bahn
    if not ergebnisse and wer_davor:
        from . import materialstand as mst  # erst hier: es bringt den Job mit

        raise mst.schon_weg(wer_davor)
    if not ergebnisse and davor is not None:
        raise ValueError(tr("r3.fehler.kein_rest"))
    if not ergebnisse:
        from . import materialstand as mst

        # Nichts zu tun: Der Assistent nimmt dem Block den Haken (wie bei „schon weg“) – in einer
        # Ebene der Kette hat oft die Ebene davor alles genommen, und „Anlegen“ ging sonst nicht.
        raise mst.SchonWeg(tr("r3.fehler.nichts"))
    bahn = min(ergebnisse.values(), key=lambda b: b.zeit)
    bahn.zeiten = {v: b.zeit for v, b in ergebnisse.items()}
    return bahn
