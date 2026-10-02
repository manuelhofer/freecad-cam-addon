# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Prüfstand für Werkzeugwege (W-006, Grundsatz 0 – Manuel, 2026-10-01: „die Werkzeugwege
müssen sinnvoll sein und natürlich immer zum kürzesten Bearbeitungsergebnis führen, bei egal
welcher Strategie … Finde einen Weg, das sicherzustellen“).

Jede Bahn wird mit demselben Fräser und denselben Werten an Teil und Rohteil gemessen – die
Simulation im Quader (restmaterial.Quader) fährt sie Satz für Satz ab:
- sicher: nirgends ins Teil, im Eilgang nichts abgetragen;
- vollständig: auf den Flächen bleibt nichts stehen (bis auf das Aufmaß an Wänden);
- sinnvoll: wenig Vorschub in der Luft, wenig Eintauchen und Rampen im Material, wenig Halte;
- schonend: die Breite im Eingriff (der Querschnitt im Schnitt durch die Schnitttiefe) – nie in
  voller Breite durchs volle Material, das ist nur scheinbar schnell; wie weit sie über ae geht
  (in Ecken, in der Mitte eines Bogens) und wie lange am Stück über bahn.LAST_DAUERND · ae,
  steht in der Zeile (P-2026-10-01-49, P-2026-10-02-56);
- kurz: die Zeit gegen die Untergrenze – das Volumen durch das Zeitspanvolumen ae · ap · vf,
  als wäre der Fräser nie aus dem Eingriff – ergibt den Wirkungsgrad.
`messen()` gibt die Kennzahlen, `urteile()` die Sätze, wo eine Bahn durchfällt. Die Prüfung
`tests/test_pruefstand.py` misst damit alle Strategien an den Maßstabsteilen und vergleicht
mit den Bestmarken (`tests/bestmarken.json`): langsamer darf keine Änderung werden. Läuft ohne
Oberfläche.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import bahn as bn
from . import fahrzeit as fz
from . import restmaterial as rm
from . import vierachs_huelle as vh

SCHRITT = rm.SCHRITT_XY  # mm – das Raster des Quaders
BOGENSCHRITT = 0.5  # mm – so lang sind die Sehnen auf einem Bogen
REST_ZULAESSIG = 0.05  # mm – mehr auf der Fläche ist ein Rest
EINSCHNITT_ZULAESSIG = 0.05  # mm – tiefer ins Teil ist ein Einschnitt
LUFT_ZULAESSIG = 0.30  # Anteil des Vorschubwegs ohne Abtrag – mehr ist unsinnig
NAHE_WAND = 0.75  # mm – so weit um Höheres zählt die Fläche nicht (das Aufmaß kommt dazu)
# Die Breite im Eingriff: das abgetragene Volumen je mm Weg durch die Schnitttiefe (die größte
# Absenkung, die der Satz bewirkt), gemittelt über BREIT_FENSTER mm – das Raster des Quaders
# zählt eine Zelle erst, wenn der Fräser ihre Mitte überstreicht. Bögen zählen je Sehne
# (BOGENSCHRITT): Auf den Bögen der Nut wächst die Breite von der Wand bis in die Mitte – über den
# ganzen Bogen gemittelt sähe der Prüfstand die Spitze nicht. Rampen (der Fräser sinkt)
# zählen nicht: Ihr Eingriff folgt dem Eintauchwinkel des Werkzeugs; dünne Schnitte (weniger
# als MIN_TIEFE) auch nicht. Mehr als VOLL_ANTEIL des Durchmessers breit und dabei mehr
# Querschnitt als ae · ap über BREIT_WEG mm im Vorschub ist ein Vollschnitt – breit und flach
# (Planen 1 mm tief) ist keine Last; die größte Breite, gemessen in ae, steht in der Zeile (in
# den Ecken einer Tasche mehr als ae), dazu der längste Weg am Stück mit mehr als
# bahn.LAST_DAUERND · ae (Spezifikation Strategien 12.1: höchstens eine Fräserbreite).
VOLL_ANTEIL = 0.75
BREIT_FENSTER = 3.0  # mm
BREIT_WEG = 5.0  # mm
MIN_TIEFE = 1.0  # mm
_NICHTS = 1e-9


@dataclass
class Bahnlauf:
    """Eine Bahn in der Folge: ihre Punkte (bahn.Punkt) und ihre Vorschübe (mm/min)."""

    punkte: list
    vorschub: float
    eintauchen: float = 0.0  # 0: wie der Vorschub


@dataclass
class Kennzahlen:
    """Was der Prüfstand an einer Bahn (oder einer Folge von Bahnen) misst."""

    zeit: float = 0.0  # min – mit Eilgang und Beschleunigung (bahn.zeit)
    vorschubweg: float = 0.0  # mm
    eilgangweg: float = 0.0  # mm
    luftweg: float = 0.0  # mm Vorschub, der nichts abträgt
    volumen: float = 0.0  # mm³ abgetragen
    untergrenze: float = 0.0  # min – Volumen ÷ (ae · ap · vf): der Fräser nie aus dem Eingriff
    rest: float = 0.0  # mm – das meiste, was auf den Flächen stehen blieb (fern der Wände)
    einschnitt: float = 0.0  # mm – das tiefste ins Teil (negativ)
    eilgang_abtrag: float = 0.0  # mm³ – im Eilgang abgetragen (muss 0 sein)
    schnell_abtrag: float = 0.0  # mm³ – im Schnellvorschub (mehr als vf) abgetragen (muss 0 sein)
    schnellweg: float = (
        0.0  # mm im Schnellvorschub durchs Freie – ein Weg, kein Vorschub in der Luft
    )
    eintauchungen: int = 0  # senkrechte Fahrten mit Eintauchvorschub, die Material trafen
    rampen: int = 0  # schräge Fahrten hinab im Vorschub, die Material trafen (Stücke)
    halte: int = 0  # Stopps: Ecken ab 15°, um Eilgänge, am Anfang und Ende
    voll: float = 0.0  # mm Vorschub mit mehr als VOLL_ANTEIL · D im Eingriff (Vollschnitt)
    eingriff_max: float = 0.0  # die größte Breite im Eingriff, als Vielfaches von ae
    last_lang: float = 0.0  # mm – der längste Weg am Stück mit mehr als LAST_DAUERND · ae

    @property
    def luftanteil(self):
        return self.luftweg / self.vorschubweg if self.vorschubweg > 0 else 0.0

    @property
    def wirkungsgrad(self):
        return self.untergrenze / self.zeit if self.zeit > 0 else 0.0


def _stuecke(von, nach):
    """Die Teilstücke eines Satzes als (x, y, z)-Paare – ein Bogen in Sehnen."""
    if nach.bogen is None:
        return [((von.x, von.y, von.z), (nach.x, nach.y, nach.z))]
    n = max(2, int(math.ceil(bn.weg(von, nach) / BOGENSCHRITT)))
    mx, my, uhr = nach.bogen
    a0 = math.atan2(von.y - my, von.x - mx)
    bogen = bn.winkel(von, nach)
    r = math.hypot(von.x - mx, von.y - my)
    vorher = (von.x, von.y, von.z)
    stuecke = []
    for i in range(1, n + 1):
        t = i / n
        a = a0 - t * bogen if uhr else a0 + t * bogen
        jetzt = (mx + r * math.cos(a), my + r * math.sin(a), von.z + (nach.z - von.z) * t)
        stuecke.append((vorher, jetzt))
        vorher = jetzt
    return stuecke


def _ausschnitt(q, stuecke, radius):
    """Der Ausschnitt (zwei Slices) des Quaders, den die Stücke mit dem Fräser treffen können."""
    xs = [p[0] for s in stuecke for p in s]
    ys = [p[1] for s in stuecke for p in s]
    sx, sy = q.x[1] - q.x[0], q.y[1] - q.y[0]
    rand = radius + 2 * max(sx, sy)
    nx, ny = q.h.shape
    i0 = max(int(math.floor((min(xs) - rand - q.x[0]) / sx)), 0)
    i1 = min(int(math.ceil((max(xs) + rand - q.x[0]) / sx)) + 1, nx)
    j0 = max(int(math.floor((min(ys) - rand - q.y[0]) / sy)), 0)
    j1 = min(int(math.ceil((max(ys) + rand - q.y[0]) / sy)) + 1, ny)
    return slice(i0, max(i1, i0)), slice(j0, max(j1, j0))


def halte(punkte):
    """So oft hält die Maschine auf der Bahn: an Ecken ab fahrzeit.ECKE, vor und nach jedem
    Eilgang und Eintauchen, am Anfang und am Ende – wie fahrzeit.zeiten es rechnet."""
    saetze = []
    for von, nach in zip(punkte, punkte[1:], strict=False):
        if nach.eilgang:
            saetze.append(None)
        else:
            saetze.append((bn._richtung(von, nach, True), bn._richtung(von, nach, False)))
    if not saetze:
        return 0
    anzahl = 1  # am Ende
    for vorher, jetzt in zip(saetze, saetze[1:], strict=False):
        if vorher is None or jetzt is None or fz.winkel(vorher[1], jetzt[0]) >= fz.ECKE:
            anzahl += 1
    return anzahl + 1  # am Anfang


def messen(
    laeufe,
    teil,
    rohteil,
    oben,
    form,
    ae,
    ap,
    ebenen_z=(),
    aufmass=0.0,
    unten=None,
    tiefe=None,
    vorher=(),
    raster=SCHRITT,
):
    """Misst die Bahnen `laeufe` ([Bahnlauf], in dieser Reihenfolge) am Teil (Part-Form) im
    Rohteil (x_von, x_bis, y_von, y_bis bis `oben`) mit dem Fräser `form` (fraeserform.Form
    oder Radius): die Kennzahlen. `ae`, `ap`: der Einsatz, für die Untergrenze; `ebenen_z`:
    die z der Flächen, auf denen nichts stehen bleiben darf (bis `aufmass` + NAHE_WAND neben
    Höherem); `unten`: der Boden des Quaders (None: unter dem Teil); `tiefe`: so hoch steht das
    Material über der Fläche (None: von `oben` bis zur tiefsten Fläche) – für die Untergrenze,
    in einer Tasche die Höhe ihrer Wände; `vorher`: Bahnen ([Bahnlauf]), die davor liefen –
    sie formen das Rohteil, zählen aber nicht (die Oberseite vor der Tasche); `raster`: so fein
    der Quader (mm) – feiner für die Breite im Eingriff bei kleinen Schritten (die Bögen der Nut
    rücken weniger als eine Zelle vor)."""
    x_von, x_bis, y_von, y_bis = rohteil
    if unten is None:
        unten = teil.BoundBox.ZMin - 1.0
    q = rm.Quader(x_von, x_bis, y_von, y_bis, unten, oben, raster)
    zelle = raster * raster
    for lauf in vorher:
        for von, nach in zip(lauf.punkte, lauf.punkte[1:], strict=False):
            stuecke = _stuecke(von, nach)
            q.fahre_stuecke([s[0] for s in stuecke], [s[1] for s in stuecke], form)
    vorher_h = q.h.copy()  # was die Bahnen davor stehen ließen – davon zählt das Volumen
    k = Kennzahlen()
    vorschub = 0.0
    radius = float(getattr(form, "radius", form))
    fenster = []  # [(Weg, Abtrag, Weg · Tiefe)] der letzten Stücke, zusammen ≥ BREIT_FENSTER
    ueber = 0.0  # mm am Stück mit mehr als LAST_DAUERND · ae
    for lauf in laeufe:
        punkte = lauf.punkte
        if not punkte:
            continue
        vorschub = vorschub or lauf.vorschub
        k.zeit += bn.zeit(punkte, lauf.vorschub, lauf.eintauchen or None)
        k.halte += halte(punkte)
        in_rampe = False
        for von, nach in zip(punkte, punkte[1:], strict=False):
            stuecke = _stuecke(von, nach)
            zaehlt = not (nach.eilgang or nach.eintauchen or nach.z < von.z - _NICHTS)
            if not zaehlt:
                fenster = []  # Eintauchen und Rampen zählen für sich
                ueber = 0.0
            # Ein Bogen je Sehne, damit das Fenster die Spitze in seiner Mitte sieht.
            gruppen = [[s] for s in stuecke] if zaehlt and nach.bogen is not None else [stuecke]
            abtrag = 0.0
            for gruppe in gruppen:
                ausschnitt = _ausschnitt(q, gruppe, radius)
                vorher = q.h[ausschnitt].copy()
                q.fahre_stuecke([s[0] for s in gruppe], [s[1] for s in gruppe], form)
                gesenkt = vorher - q.h[ausschnitt]
                hier = float(gesenkt.sum()) * zelle
                abtrag += hier
                if not zaehlt:
                    continue
                a, b = gruppe[0][0], gruppe[-1][1]
                waagerecht = math.hypot(b[0] - a[0], b[1] - a[1])
                tiefe_hier = float(gesenkt.max()) if gesenkt.size else 0.0
                fenster.append((waagerecht, hier, waagerecht * tiefe_hier))
                summe = sum(f[0] for f in fenster)
                while len(fenster) > 1 and summe - fenster[0][0] >= BREIT_FENSTER:
                    summe -= fenster.pop(0)[0]
                flaeche = sum(f[2] for f in fenster)
                if summe < BREIT_FENSTER or flaeche < MIN_TIEFE * summe:
                    ueber = 0.0
                    continue
                breite = sum(f[1] for f in fenster) / flaeche
                if ae > 0:
                    k.eingriff_max = max(k.eingriff_max, breite / ae)
                    ueber = ueber + waagerecht if breite > bn.LAST_DAUERND * ae else 0.0
                    k.last_lang = max(k.last_lang, ueber)
                querschnitt = breite * flaeche / summe
                if breite > VOLL_ANTEIL * 2.0 * radius and querschnitt > ae * ap:
                    k.voll += waagerecht
            weg = bn.weg(von, nach)
            if nach.eilgang:
                k.eilgangweg += weg
                k.eilgang_abtrag += abtrag
                in_rampe = False
                continue
            trifft = abtrag > _NICHTS
            if nach.anteil > 1.0 + 1e-9:
                # Quer zurück über die freie Seite (nut_bahn), unten durchs Freie (das Räumen
                # „adaptiv“): Das ist ein Weg wie der Eilgang, kein Vorschub in der Luft.
                k.schnell_abtrag += abtrag
                if not trifft:
                    k.schnellweg += weg
                    in_rampe = False
                    continue
            k.vorschubweg += weg
            if not trifft:
                k.luftweg += weg
            hinab = nach.z < von.z - _NICHTS
            if nach.eintauchen:
                if trifft and hinab:
                    k.eintauchungen += 1
                in_rampe = False
            elif hinab and trifft:
                if not in_rampe:
                    k.rampen += 1
                in_rampe = True
            else:
                in_rampe = False
    k.volumen = float((vorher_h - q.h).sum()) * zelle
    if tiefe is None:
        tiefe = max(oben - min(ebenen_z), _NICHTS) if ebenen_z else ap
    tiefe = min(ap, tiefe)
    if ae > 0 and tiefe > 0 and vorschub > 0:
        k.untergrenze = k.volumen / (ae * tiefe * vorschub)
    teilhoehe = rm.teilhoehen(vh.vernetze(teil), q)
    da = np.isfinite(teilhoehe)
    if da.any():
        unterschied = np.where(da, q.h - teilhoehe, np.nan)
        # Neben einer Kante (Wand, Zapfen) zählt der Einschnitt nicht: Die Zelle liegt halb auf
        # der Kante, das Netz hat die runde Wand als Vieleck – der Fräser, der genau an der
        # Wand entlangfährt, meldete dort die ganze Wandhöhe.
        hoehen = np.where(da, teilhoehe, np.nan)
        kante = np.zeros_like(da)
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nachbar = np.roll(np.roll(hoehen, di, 0), dj, 1)
            kante |= np.abs(nachbar - hoehen) > 0.01
            kante |= np.isnan(nachbar)  # daneben kein Teil: der Rand einer durchgehenden Bohrung
        innen = da & ~kante
        if innen.any():
            k.einschnitt = min(0.0, float(np.nanmin(unterschied[innen])))
        m = int(math.ceil((max(aufmass, 0.0) + NAHE_WAND) / raster))
        for z in ebenen_z:
            flaeche = da & (np.abs(teilhoehe - z) < 0.01)
            hoch = da & (teilhoehe > z + 0.01)
            nah = np.zeros_like(hoch)
            for di in range(-m, m + 1):
                for dj in range(-m, m + 1):
                    if di * di + dj * dj <= m * m:
                        nah |= np.roll(np.roll(hoch, di, 0), dj, 1)
            weit = flaeche & ~nah
            if weit.any():
                k.rest = max(k.rest, float(np.nanmax(unterschied[weit])))
    return k


def urteile(k, sicher_nur=False):
    """Die Sätze, mit denen eine Bahn durchfällt – leer, wenn sie besteht. `sicher_nur`: nur
    Sicherheit und Ergebnis (ins Teil, stehen geblieben, im Eilgang abgetragen), nicht die Luft –
    für Folgen, die nur zum Vergleich gemessen werden."""
    saetze = []
    if k.einschnitt < -EINSCHNITT_ZULAESSIG:
        saetze.append(f"schneidet {-k.einschnitt:.2f} mm ins Teil")
    if k.rest > REST_ZULAESSIG:
        saetze.append(f"lässt {k.rest:.2f} mm auf der Fläche stehen")
    if k.eilgang_abtrag > _NICHTS:
        saetze.append(f"trägt im Eilgang ab ({k.eilgang_abtrag:.1f} mm³)")
    if k.schnell_abtrag > _NICHTS:
        saetze.append(f"trägt im Schnellvorschub ab ({k.schnell_abtrag:.1f} mm³)")
    if not sicher_nur and k.luftanteil > LUFT_ZULAESSIG:
        saetze.append(f"fährt {k.luftanteil * 100:.0f} % des Vorschubwegs in der Luft")
    if not sicher_nur and k.voll > BREIT_WEG:
        saetze.append(f"schneidet auf {k.voll:.0f} mm in voller Breite")
    return saetze


def zeile(k):
    """Die Kennzahlen in einer Zeile – für Berichte und die Prüfung."""
    return (
        f"{k.zeit:6.2f} min  Untergrenze {k.untergrenze:5.2f} ({k.wirkungsgrad * 100:3.0f} %)  "
        f"Luft {k.luftanteil * 100:3.0f} %  Eilgang {k.eilgangweg / 1000:5.2f} m  "
        f"Halte {k.halte:4d}  Eintauchen {k.eintauchungen:2d}  Rampen {k.rampen:2d}  "
        f"Rest {k.rest:.2f}  Einschnitt {k.einschnitt:.2f}  "
        f"Eingriff bis {k.eingriff_max:.1f} ae, über {bn.LAST_DAUERND:g} ae {k.last_lang:.0f} mm "
        f"am Stück, voll {k.voll:.0f} mm"
    )
