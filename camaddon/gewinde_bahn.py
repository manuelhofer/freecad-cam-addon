# SPDX-License-Identifier: LGPL-2.1-or-later
"""2,5D, die Bahn „Gewinde fräsen“ (W-006 S3g): metrische Innengewinde mit einem Gewindefräser in
Bohrungen, deren Durchmesser das Kernloch eines Gewindes mit der Steigung des Fräsers ist.

- **Welches Gewinde** (gewinde_fuer()): Die Tabelle daten/gewinde_6H.csv (ISO 965, Toleranz 6H –
  dieselbe wie bei FreeCADs Gewindefräsen, Data/Threads/metric-internal-6H.csv) nennt je Gewinde
  den erlaubten Kerndurchmesser D1. Liegt die Bohrung darin und hat das Gewinde die Steigung des
  Fräsers, ist es dieses: Ø 8,5 mit Steigung 1,5 → M10 × 1,5 (D1 8,376 … 8,676).
- **Wie weit hinaus**: Der Zahn ist ein Dreieck mit dem Flankenwinkel (60°), vorn abgeflacht
  (P/8, so breit wie der Grund des Innengewindes). Gefräst wird auf die Mitte der Toleranz des
  Flankendurchmessers D2 (M10 × 1,5: 9,026 … 9,206 → 9,116): Die Spitze des Zahns reicht dann
  D2/2 + (P/2 − Spitze) / (2 · tan 30°) von der Achse. „Korrektur“ macht das Gewinde um so viel
  größer (am Durchmesser) – nach der Lehre.
- **Die Bahn je Bohrung**: im Eilgang in die Mitte der Bohrung hinab, im Halbkreis hinaus (dabei
  P/4 in z – so steil wie die Helix, kein Absatz im Gewinde), die Helix mit einer Steigung je
  Umlauf, im Halbkreis zurück in die Mitte (wieder P/4), im Eilgang hinauf. Gleichlauf (M3, das
  Material rechts): gegen den Uhrzeigersinn (G3) – ein Rechtsgewinde damit von unten nach oben;
  Gegenlauf im Uhrzeigersinn von oben nach unten; ein Linksgewinde umgekehrt.
- **Wie weit in z**: Die Spitze des Fräsers ist das untere Ende des Zahns; seine Mitte liegt
  um die halbe Spitze und die Höhe des Zahns (von der Spitze bis zum Hals) mal tan 30° höher.
  Durch eine durchgehende Bohrung geht er so weit hinaus, dass die Lücke des untersten Gangs
  ganz unter der Unterseite beginnt – sonst bliebe dort ein Rest, an dem die Schraube hängt (Ø 8
  für M10 × 1,5: etwa 1,3 mm). Oben ebenso: Die Lücke endet ganz über der Oberkante, sonst ginge
  die Schraube nicht hinein. In einer Sackbohrung bleibt die Spitze FREI_GRUND über dem Grund.
  Ein Fräser mit mehreren Zähnen übereinander fräst so viele Gänge auf einmal: Er braucht nur so
  viele Umläufe, bis sein oberster Zahn oben ist – mindestens einen.
- **Der Vorschub gilt an der Schneide**: Auf der kleinen Kreisbahn in der Bohrung läuft die
  Schneide außen viel weiter als die Mitte des Fräsers (M10 mit Ø 8: fast fünfmal). Die Mitte
  bekommt r / (r + Fräserradius) vom Vorschub (bahn.Punkt.anteil), in den Halbkreisen mit deren
  Radius – sonst bräche der Fräser.
- **Durchgänge** > 1: radial in Stufen gleicher Spanfläche (wie FreeCAD), jede mit Hin- und
  Rückweg.
- Die Bohrungen in der Reihenfolge des kürzesten Wegs, die Zeit mit bahn.zeit.

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import csv
import math
import os
from dataclasses import dataclass, field

from . import ADDON_ORDNER, einheiten
from . import bahn as bn
from . import vierachs_bahn as vb
from .sprache import tr

GLEICH = 1e-6
TABELLE = os.path.join(ADDON_ORDNER, "daten", "gewinde_6H.csv")
KERN_TOLERANZ = 0.02  # mm – so weit darf die Bohrung neben dem Kerndurchmesser D1 liegen
LUFT = 0.1  # mm je Seite – so viel kleiner als die Bohrung muss der Fräser sein (Eintauchen)
HALS_LUFT = 0.05  # mm – so viel Luft bleibt zwischen dem Hals und den Spitzen des Gewindes
RAND = 0.1  # mm – so weit geht die Lücke des Gewindes über Ober- und Unterseite hinaus
FREI_GRUND = 0.2  # mm – so weit bleibt die Spitze über dem Grund einer Sackbohrung
HALS_ANTEIL = 0.7  # vom Fräser-Ø: so dick ist der Hals, wenn ihn niemand eingetragen hat
FLANKENWINKEL = 60.0  # Grad – metrisch
SPITZE = 1 / 8  # × Steigung: so breit ist der Zahn vorn – der Grund des Innengewindes
EINFAHRT = 0.25  # × Steigung: so weit in z laufen die Halbkreis hinein und hinaus
BOGEN_TEIL = math.pi / 2  # höchstens so weit je Bogen (G2/G3 mit Z: je ein Viertel)


@dataclass(frozen=True)
class Gewinde:
    """Ein metrisches Innengewinde der Tabelle (mm)."""

    name: str  # „M10x1.5“ – ASCII wie gewinde.gewinde_name(): es steht auch im Programm
    nenn: float  # D
    steigung: float  # P
    kern_min: float  # D1
    kern_max: float
    flanke_min: float  # D2
    flanke_max: float

    @property
    def flanke(self):
        """Die Mitte der Toleranz des Flankendurchmessers – darauf fräst es."""
        return (self.flanke_min + self.flanke_max) / 2


_tabelle = None


def tabelle():
    """[Gewinde] – die metrischen Innengewinde (6H) aus daten/gewinde_6H.csv; leer, wenn die
    Datei fehlt."""
    global _tabelle
    if _tabelle is None:
        liste = []
        try:
            with open(TABELLE, encoding="utf-8", newline="") as datei:
                for zeile in csv.DictReader(datei):
                    try:
                        steigung = float(zeile["pitch"])
                        nenn = float(zeile["dMajorMin"])
                        liste.append(
                            Gewinde(
                                f"M{nenn:g}x{steigung:g}",
                                nenn,
                                steigung,
                                float(zeile["dMinorMin"]),
                                float(zeile["dMinorMax"]),
                                float(zeile["dPitchMin"]),
                                float(zeile["dPitchMax"]),
                            )
                        )
                    except (KeyError, TypeError, ValueError):
                        continue
        except OSError:
            liste = []
        _tabelle = liste
    return _tabelle


def gewinde_fuer(durchmesser, steigung):
    """Das Gewinde mit der Steigung `steigung`, dessen Kernloch die Bohrung Ø `durchmesser` ist –
    None, wenn keins passt. Passen mehrere, das mit dem Nenn-Ø am nächsten an Ø + Steigung."""
    passend = [
        g
        for g in tabelle()
        if abs(g.steigung - steigung) <= 1e-6
        and g.kern_min - KERN_TOLERANZ <= durchmesser <= g.kern_max + KERN_TOLERANZ
    ]
    return min(passend, key=lambda g: abs(g.nenn - (durchmesser + steigung)), default=None)


def naechstes(durchmesser, steigung):
    """Das Gewinde mit dieser Steigung, das die Bohrung wohl meint – für den Satz, wenn keins
    passt: eins mit ihrem Durchmesser als Nenn-Ø (das Gewinde gezeichnet, nicht sein Kernloch),
    sonst das, dessen Kernloch ihr am nächsten kommt; None, wenn kein Gewinde diese Steigung
    hat."""
    mit = [g for g in tabelle() if abs(g.steigung - steigung) <= 1e-6]
    nenn = [g for g in mit if abs(g.nenn - durchmesser) <= 0.05]
    if nenn:
        return nenn[0]
    return min(mit, key=lambda g: abs((g.kern_min + g.kern_max) / 2 - durchmesser), default=None)


def zaehne_fuer(schneidenlaenge, steigung):
    """Wie viele Zähne ein Gewindefräser übereinander hat – aus der Schneidenlänge: so viele
    Steigungen passen hinein, mindestens einer (unbekannt: einer, dann Gang für Gang)."""
    if steigung <= 0 or schneidenlaenge <= 0:
        return 1
    return max(1, int(schneidenlaenge / steigung + 1e-6))


def _mm(wert):
    return f"{einheiten.text(wert, einheiten.LAENGE)} {einheiten.einheit(einheiten.LAENGE)}"


def _d(wert):
    return einheiten.text(wert, einheiten.LAENGE)


@dataclass
class Gewindewerte:
    """Was das Gewindefräsen braucht; Längen in mm, z nach oben im Job."""

    fraeser_radius: float
    steigung: float
    oben: float  # z, wo das Material beginnt (das Rohteil)
    sicher: float  # z für den Eilgang über allem
    zaehne: int = 1  # Zähne übereinander (1: ein Zahn, Gang für Gang)
    flankenwinkel: float = FLANKENWINKEL
    spitze: float = 0.0  # mm – so breit ist der Zahn vorn; 0: P/8
    hals_radius: float = 0.0  # 0: unbekannt
    reichweite: float = 0.0  # mm von der Spitze bis zum Schaft; 0: unbekannt
    gleichlauf: bool = True
    links: bool = False  # Linksgewinde
    durchgaenge: int = 1
    korrektur: float = 0.0  # mm am Flankendurchmesser: so viel größer
    sicherheit: float = vb.SICHERHEIT
    vorschub: float = 0.0  # mm/min an der Schneide – für die Zeit; 0: 1000


@dataclass(frozen=True)
class Stelle:
    """Ein Gewinde in einer Bohrung, so wie es gefräst wird (mm)."""

    bohrung: object  # bohrung_bahn.Bohrung
    gewinde: Gewinde
    r_spitze: float  # so weit reicht die Spitze des Zahns von der Achse
    r_bahn: float  # der Radius der Helix (die Mitte des Fräsers)
    z_unten: float  # die Spitze unten – ohne den Halbkreis
    z_oben: float  # die Spitze oben – ohne den Halbkreis


@dataclass
class Gewindefraesbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    bohrungen: int
    gewinde: list  # [(Name, Anzahl)] in der Reihenfolge des ersten Auftretens
    umlaeufe: float  # Umläufe der Helix, über alle Bohrungen und Durchgänge
    z_min: float
    laenge: float  # mm im Vorschub
    zeit: float  # Minuten (bahn.zeit)
    ringe: list = field(default_factory=list)  # [(x, y, r_spitze)] – fürs Prüfen

    def gewinde_text(self):
        """„2 × M10x1.5, 1 × M12x1.5“."""
        return ", ".join(f"{n} × {name}" for name, n in self.gewinde)


def stelle(b, w):
    """Wie das Gewinde in der Bohrung `b` (bohrung_bahn.Bohrung) mit den Werten `w` gefräst wird
    (Stelle). ValueError mit einem Satz, wenn es nicht geht."""
    d = 2 * b.radius
    p = w.steigung
    gw = gewinde_fuer(d, p)
    if gw is None:
        beispiel = naechstes(d, p)
        if beispiel is None:
            raise ValueError(tr("gf.fehler.steigung_unbekannt", steigung=_d(p)))
        raise ValueError(
            tr(
                "gf.fehler.kein_gewinde",
                durchmesser=_d(d),
                steigung=_d(p),
                gewinde=beispiel.name,
                von=_d(beispiel.kern_min),
                bis=_d(beispiel.kern_max),
            )
        )
    rt = w.fraeser_radius
    hoechstens = d - 2 * LUFT
    if 2 * rt > hoechstens + GLEICH:
        raise ValueError(
            tr(
                "gf.fehler.zu_gross",
                fraeser=_d(2 * rt),
                durchmesser=_d(d),
                hoechstens=_d(hoechstens),
            )
        )
    spitze = w.spitze if w.spitze > 0 else SPITZE * p
    halb = math.radians(min(max(w.flankenwinkel or FLANKENWINKEL, 10.0), 170.0) / 2)
    r_spitze = (gw.flanke + w.korrektur) / 2 + max(p / 2 - spitze, 0.0) / (2 * math.tan(halb))
    r_bahn = r_spitze - rt
    if r_spitze <= b.radius + GLEICH or r_bahn <= GLEICH:
        raise ValueError(tr("gf.fehler.korrektur", gewinde=gw.name))
    if w.hals_radius > 0 and w.hals_radius + r_bahn > b.radius - HALS_LUFT + GLEICH:
        raise ValueError(
            tr(
                "gf.fehler.hals",
                hals=_d(2 * w.hals_radius),
                gewinde=gw.name,
                hoechstens=_d(max(2 * (b.radius - HALS_LUFT - r_bahn), 0.0)),
            )
        )
    einfahrt = EINFAHRT * p
    tan = math.tan(halb)
    gewinde_tief = r_spitze - b.radius  # so tief schneidet der Zahn in die Wand
    hals = w.hals_radius if w.hals_radius > 0 else HALS_ANTEIL * rt
    h_mitte = spitze / 2 + max(rt - hals, gewinde_tief) * tan  # von der Spitze zur Zahnmitte
    luecke = spitze / 2 + gewinde_tief * tan  # die halbe Lücke des Gewindes am Kernloch
    if b.durch:
        z_unten = b.z_unten - (h_mitte + luecke + RAND)
    else:
        z_unten = b.z_unten + FREI_GRUND + einfahrt
    kante = min(b.z_oben, w.oben)
    if kante < z_unten + GLEICH:
        raise ValueError(
            tr(
                "gf.fehler.flach",
                durchmesser=_d(d),
                tiefe=_mm(FREI_GRUND + einfahrt + GLEICH),
            )
        )
    zaehne = max(int(w.zaehne or 1), 1)
    z_oben = max(z_unten + p, kante + luecke + RAND - h_mitte - (zaehne - 1) * p)
    tiefe = kante - (z_unten - einfahrt)
    if w.reichweite > 0 and tiefe > w.reichweite + GLEICH:
        raise ValueError(tr("gf.fehler.reichweite", reichweite=_mm(w.reichweite), tiefe=_mm(tiefe)))
    return Stelle(b, gw, r_spitze, r_bahn, z_unten, z_oben)


def _bogen(punkte, mitte, radius, von, bis, z_von, z_bis, uhr, anteil):
    """Bögen um `mitte` von Winkel `von` nach `bis` (rad, in Fahrtrichtung), z linear, in Stücken
    von höchstens einem Viertel, mit dem Anteil des Vorschubs. Gibt die Länge zurück."""
    anzahl = max(1, int(math.ceil(abs(bis - von) / BOGEN_TEIL - 1e-9)))
    laenge = 0.0
    for i in range(1, anzahl + 1):
        t = i / anzahl
        winkel = von + (bis - von) * t
        punkt = bn.Punkt(
            False,
            mitte[0] + radius * math.cos(winkel),
            mitte[1] + radius * math.sin(winkel),
            z_von + (z_bis - z_von) * t,
            bogen=(mitte[0], mitte[1], uhr),
            anteil=anteil,
        )
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge


def _halbkreis(punkte, von, nach, z, uhr, anteil):
    """Ein Halbkreis von `von` nach `nach` (der Durchmesser), z linear bis `z`."""
    mitte = ((von[0] + nach[0]) / 2, (von[1] + nach[1]) / 2)
    punkt = bn.Punkt(False, nach[0], nach[1], z, bogen=(mitte[0], mitte[1], uhr), anteil=anteil)
    laenge = bn.weg(punkte[-1], punkt)
    punkte.append(punkt)
    return laenge


def richtung(gleichlauf, links):
    """(uhr, rauf): G2 (im Uhrzeigersinn) oder G3, und ob die Helix von unten nach oben läuft.
    Gleichlauf in der Bohrung ist G3 (das Material rechts); ein Rechtsgewinde steigt gegen den
    Uhrzeigersinn, ein Linksgewinde im Uhrzeigersinn."""
    uhr = not gleichlauf
    return uhr, uhr == bool(links)


def _gewinde(punkte, s, w):
    """Eine Bohrung: je Durchgang in der Mitte hinab, im Halbkreis hinaus, die Helix, im
    Halbkreis zurück. Gibt (Länge, Umläufe, z_min)."""
    b, p, rt = s.bohrung, w.steigung, w.fraeser_radius
    uhr, rauf = richtung(w.gleichlauf, w.links)
    if rauf:
        z_a, z_e, dz = s.z_unten, s.z_oben, 1.0
    else:
        z_a, z_e, dz = s.z_oben, s.z_unten, -1.0
    einfahrt = EINFAHRT * p
    mitte = b.mitte
    r_kern = max(b.radius - rt, 0.0)
    anzahl = max(int(w.durchgaenge or 1), 1)
    radien = [r_kern + (s.r_bahn - r_kern) * math.sqrt((i + 1) / anzahl) for i in range(anzahl)]
    drehung = -1.0 if uhr else 1.0
    umlaeufe = abs(z_e - z_a) / p
    punkte.append(bn.Punkt(True, mitte[0], mitte[1], w.sicher))
    punkte.append(bn.Punkt(True, mitte[0], mitte[1], min(w.sicher, w.oben + w.sicherheit)))
    laenge = 0.0
    for r in radien:
        punkte.append(bn.Punkt(True, mitte[0], mitte[1], z_a - dz * einfahrt))
        halb = (r / 2) / (r / 2 + rt)
        rand = (mitte[0] + r, mitte[1])
        laenge += _halbkreis(punkte, mitte, rand, z_a, uhr, halb)
        ende = drehung * 2 * math.pi * umlaeufe
        laenge += _bogen(punkte, mitte, r, 0.0, ende, z_a, z_e, uhr, r / (r + rt))
        rand = (mitte[0] + r * math.cos(ende), mitte[1] + r * math.sin(ende))
        laenge += _halbkreis(punkte, rand, mitte, z_e + dz * einfahrt, uhr, halb)
    punkte.append(bn.Punkt(True, mitte[0], mitte[1], w.sicher))
    return laenge, umlaeufe * anzahl, min(s.z_unten, s.z_oben) - einfahrt


def planen(werte, liste):
    """Die Bahn „Gewinde fräsen“ (Gewindefraesbahn) für die Bohrungen `liste`
    ([bohrung_bahn.Bohrung]) mit den Werten `werte`. ValueError mit einem Satz, wenn es nicht
    geht – auch, wenn eine Bohrung nicht passt."""
    w = werte
    if w.fraeser_radius <= 0:
        raise ValueError(tr("gf.fehler.fraeser"))
    if w.steigung <= 0:
        raise ValueError(tr("gf.fehler.steigung"))
    if not liste:
        raise ValueError(tr("gf.fehler.keine"))
    stellen = [stelle(b, w) for b in liste]
    # Die kürzeste Reihenfolge: immer zur nächsten.
    offen = list(stellen)
    folge = []
    ort = offen[0].bohrung.mitte
    while offen:
        naechste = min(
            offen,
            key=lambda s: math.hypot(s.bohrung.mitte[0] - ort[0], s.bohrung.mitte[1] - ort[1]),
        )
        offen.remove(naechste)
        folge.append(naechste)
        ort = naechste.bohrung.mitte
    punkte = []
    laenge = umlaeufe = 0.0
    z_min = math.inf
    anzahl = {}
    for s in folge:
        stueck, n, z = _gewinde(punkte, s, w)
        laenge += stueck
        umlaeufe += n
        z_min = min(z_min, z)
        anzahl[s.gewinde.name] = anzahl.get(s.gewinde.name, 0) + 1
    zeit = bn.zeit(punkte, w.vorschub if w.vorschub > 0 else 1000.0)
    ringe = [(s.bohrung.mitte[0], s.bohrung.mitte[1], s.r_spitze) for s in folge]
    return Gewindefraesbahn(
        punkte, len(folge), list(anzahl.items()), umlaeufe, z_min, laenge, zeit, ringe
    )
