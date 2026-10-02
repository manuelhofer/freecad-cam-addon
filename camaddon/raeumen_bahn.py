# SPDX-License-Identifier: LGPL-2.1-or-later
"""2,5D, die Bahn „Räumen mit Versätzen“ (W-006 S3f): eine ebene Fläche nach oben – die
Oberseite eines Teils oder der Boden einer Tasche – wird mit Ringen geräumt, bei vollem ap und
schmalem ae, ohne Wenden, wie ein HSM-Weg (Manuel, 2026-10-01: „von außen kreisend zur Mitte,
immer volle Tiefe, mit ae Zustellung“).

- Die Ringe liegen auf einem Raster (hoehenfeld.je_zeile, wie bei der Kontur): dort, wo die
  Hüllfläche des Teils ohne die Fläche – mit dem Fräser um das Aufmaß vergrößert – nicht höher
  liegt als die Lage, darf die Spitze hin. Was höher steht (Inseln wie ein Zapfen, die Wände
  einer Tasche, Absätze), ist für den Fräser gesperrt; der Abstand D jeder Stelle zum
  Gesperrten ist das Feld, dessen Höhenlinien die Ringe sind (Marching Squares).
- **Offene Fläche** (die Oberseite): Variante „rohteil“ – Ringe vom Rand des Rohteils her nach
  innen, der erste außen in der Luft (Mitte R − ae außerhalb), dann je ae weiter hinein; wo
  eine Insel sie unterbricht, Läufe; zuletzt um jede Insel die Ringe des Feldes D von außen
  nach innen, so viele, wie dort noch etwas steht. Variante „inseln“ – nur die Ringe des
  Feldes D, von weit außen (am Rand des Rohteils) nach innen bis an die Inseln. Alle werden
  gerechnet, die schnellste zählt (Grundsatz 0) – wenn sie die Last hält (siehe „Adaptiv“).
- **Tasche** (eine geschlossene Kontur um die Fläche, die freie Seite innen): die Ringe des
  Feldes D von innen (der Mitte) nach außen bis an die Wände, mit Aufmaß; hinein über die
  Rampe auf dem innersten Ring, nur einmal je Lage. Die Ringe bleiben in der Kontur der Tasche
  – auch wenn das Teil neben ihr tiefer liegt als ihr Boden (eine Tasche auf einer Insel). Die
  Lagen beginnen am Rohteil; hat dieselbe Bahn die Fläche um die Tasche schon geräumt, an der
  Oberkante ihrer Wände.
- **Mehrere Flächen** (Spezifikation Strategien 13.5, T1 – Manuels Testteil mit Platte, Insel
  und oberer Stufe): die offenen Flächen von unten nach oben. Die tiefste zuerst, gleich auf
  ihre ganze Tiefe (so viele Lagen, wie Zustellung und Schneide verlangen); jede höhere danach
  nur, wo über ihr noch Material steht – der Materialstand in der Bahn selbst (_Material) –, in
  Ringen vom Rand dessen her, was noch steht (_Feld._tiefe_vom_material): außen in der Luft
  beginnend, wie am Rand des Rohteils. Die Taschen zuletzt, von oben nach unten. Höhe für Höhe
  von oben räumte jede Fläche alles, was über ihr steht – auch dort, wo eine tiefere danach
  noch einmal hinfuhr: am Testteil 26 statt 12 min.
- **Adaptiv** (Spezifikation Strategien 12.1, Frage 6, und 13.5, T5): als weitere Variante räumt
  FreeCADs Adaptiv-Kern (area.Adaptive2d) jede Lage in Bahnen, die ihren Eingriff halten – von
  außen durch die Luft hinein (in der Tasche über eine Helix), an Wänden entlang ohne quer in
  den Streifen zu fahren, zurück unten durchs Freie statt abzuheben; den schmalen Rand an den
  Wänden nimmt danach der genaue Ring. Die Ringe greifen dort, wo einer an einer Wand beginnt
  oder in die Ecke einer Tasche fährt, kurz mit dem Drei- bis Fünffachen von ae. Darum gewinnt
  die schnellste Variante nur, wenn sie die Last hält (last(): kurz höchstens bahn.LAST_KURZ,
  über bahn.LAST_DAUERND höchstens eine Fräserbreite am Stück); sonst die nächste. An Manuels
  Testteil: adaptiv 10,7 min, 5-mal abgehoben, Last bis 1,4 ae – die Ringe 12,4 min, 56-mal,
  bis 5 ae. Mit der Vorgabe „ringe“ bleibt es bei den Ringen.
- Gleichlauf: das Material rechts der Fahrtrichtung (Spindel rechtsdrehend, M3 – wie G41);
  Gegenlauf wählbar (Grundsatz 4).
- Eintauchen nur, wo schon frei ist: Ein Raster merkt sich je Lage, wo der Fräser war; das
  tangentiale Ein- und Ausfahren (kontur_bahn._anfahrt) darf nur durch Freies oder Luft. Passt
  nichts, geht es über die Rampe längs des Laufs (vierachs_bahn._rampe). Aufeinanderfolgende
  Ringe hängen aneinander, wenn der Weg dazwischen frei ist (die Spirale); sonst Eilgang knapp
  über dem Rohteil.
- Die Zeit je Variante mit bahn.zeit (Vorschub, Eilgang, Beschleunigung, Ecken).
- Mit Materialstand (W-012, materialstand): Was die Operationen davor schon weggenommen haben,
  fräst es nicht noch einmal. Die Lagen beginnen am höchsten Material, das es wegnehmen kann; je
  Lage fahren die Ringe nur, wo ihre Stirn solches Material trifft – eine Lage ohne fällt aus
  (Manuel, 2026-10-02: „wenn ich erst die Nut anklicke … und dann den Zapfen will, denke ich,
  dass er die Nut ebenfalls mit bearbeiten würde“). Der Eilgang hinab endet über dem höchsten
  Material unter der Stirn. Steht über allen Lagen überall noch das volle Rohteil, rechnet es
  wie ohne.

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import dataclasses
import hashlib
import math
from collections import OrderedDict
from dataclasses import dataclass, field

import numpy as np

from . import bahn as bn
from . import hoehenfeld as hf
from . import kontur_bahn as kb
from . import vierachs_bahn as vb
from . import vierachs_planbahn as vp
from .sprache import tr

SCHRITT = 0.5  # mm – das Raster und der Abstand der Stellen auf den Ringen
VORSCHAU_SCHRITT = 1.0  # mm – für die Vorschau im Assistenten
AUSTRITT_ANTEIL = 0.5  # vom Vorschub: so langsam beim Austritt aus dem Rohteil
VARIANTEN = ("rohteil", "morph", "inseln")  # die Ringe – auch die des 3D-Schruppens
ALLE_VARIANTEN = (*VARIANTEN, "adaptiv")  # dazu FreeCADs Adaptiv-Kern (nur das Räumen)
RINGE = "ringe"  # als Vorgabe: nur die Ringe, die schnellste von ihnen – ohne Blick auf die Last
# Der Morph nimmt an seiner breitesten Stelle so viel Eingriff wie ein gerader Schnitt mit
# ae mal diesem Faktor – nicht mehr (Manuels ae ist die Grenze); anderswo weniger.
MORPH_EINGRIFF = 1.0
MORPH_SCHRITTE = 18  # Halbierungen bei der Suche nach dem nächsten Ring
# Ist der Abstand vom ersten Ring zur Insel ringsum so ungleich (kleinster ÷ größter), lohnt der
# Morph nicht: Wo der Spalt schmal ist, lägen die Ringe viel zu eng (die Platte mit dem Zapfen
# außerhalb der Mitte: 66 statt 33 min). Dann wird er gar nicht gerechnet.
MORPH_VERHAELTNIS = 0.4
# Kommt der Morph so oft nacheinander nicht voran (je ein Viertel weiter), endet er – dann nimmt
# der Ring an der Insel den Rest (sonst rechnete er an zwei Inseln fast endlos, P-2026-10-02-02).
MORPH_OHNE_FORTSCHRITT = 12


# Mit Materialstand: So viel muss über einer Lage stehen, damit es als Material zählt, und so viel
# Fläche davon braucht eine Lage – sonst gibt es auf ihr nichts zu tun (wie im 3D-Schruppen).
MATERIAL = 0.05  # mm
MINDESTFLAECHE = 2.0  # mm²
# Eine Lücke im Weggefrästen, so lang wie höchstens LUECKE Durchmesser (mindestens LUECKE_MIN), fährt
# der Ring im Vorschub durch, statt abzuheben und wieder einzufahren – das dauert länger (an Manuels
# Klotz, die Nut zuerst: 25 Ringe über der Nut, je zweimal einfahren, eine Minute mehr).
LUECKE = 2.0
LUECKE_MIN = 20.0  # mm


class _KeinMorph(Exception):
    """Der Morph passt nicht zu dieser Fläche – die Variante entfällt."""


class _KeinAdaptiv(Exception):
    """Der Adaptiv-Kern passt nicht zu dieser Fläche (oder fehlt) – sie bekommt Ringe."""


# Die Variante „adaptiv“ (Spezifikation Strategien 12.1, Frage 6, und 13.5, T5): FreeCADs
# Adaptiv-Kern (area.Adaptive2d) hält den Eingriff – er rückt je Bahn um ADAPTIV_SCHRITT · ae,
# gemessen bleibt die Last damit unter bahn.LAST_DAUERND.
ADAPTIV_SCHRITT = 0.9  # × ae
# So fein rechnet der Kern (mm). Mit 0,1 griff er am Anfang einer Bahn an einer Wand kurz bis
# 2,4 ae; mit 0,05 bleibt er an Manuels Testteil unter 1,9 (0,5 mm über 1,7) und ist nicht langsamer.
ADAPTIV_GENAU = 0.05
ADAPTIV_HALTEN = 3.0  # × D – so weit fährt er unten durchs Freie, statt abzuheben
ADAPTIV_HELIX = 0.8  # × R – der Radius der Helix ins Volle (unter R: in der Mitte bleibt nichts)
ADAPTIV_ECKEN = 0.02  # mm – so genau folgen die Vielecke für den Kern den Höhenlinien
RUECKWEG = 3.0  # × Vorschub: so schnell unten durchs Freie (G1, wie nut_bahn.RUECKWEG)
# Der Kern rechnet bei gleicher Eingabe nicht jedes Mal dieselbe Bahn (an Manuels Platte 33,3 …
# 33,7 min). Damit dieselbe Rechnung in einer Sitzung dieselbe Bahn gibt – die Vorschau, das
# Anlegen, das Nachrechnen –, bleiben seine letzten Ergebnisse je Eingabe gemerkt.
ADAPTIV_GEMERKT = 12
_ADAPTIV = OrderedDict()  # Prüfsumme der Eingabe → [(Start, Mitte der Helix, Stücke)]
FREI_ZULAESSIG = 0.02  # Anteil der Stirn, der auf dem Weg durchs Freie Rohteil treffen darf
# Die Last einer Bahn (last): der Querschnitt, den der Fräser je mm Weg abträgt, durch
# ae · Lagentiefe – über LAST_FENSTER mm gemittelt, in Stücken von LAST_SEHNE; LAST_SPIEL: so
# viel misst das Raster zu viel.
LAST_FENSTER = 3.0  # mm
LAST_SEHNE = 1.0  # mm
LAST_SPIEL = 1.06


GLEICH = vb.GLEICH
_WINZIG = 1e-9


@dataclass(frozen=True)
class Raeumwerte:
    """Was das Räumen braucht; Längen in mm, z nach oben im Job."""

    form: object  # fraeserform.Form des Fräsers – mit ebener Stirn
    zustellung: float  # ap: höchstens so tief je Lage
    zeilenabstand: float  # ae: so weit rücken die Ringe – höchstens der Radius
    aufmass: float  # bleibt an Wänden und Inseln stehen
    oben: float  # z, wo die Lagen beginnen (das Rohteil)
    sicher: float  # z für den Eilgang über allem
    rohteil: tuple  # (x_von, x_bis, y_von, y_bis) des Rohteils von oben
    aufmass_boden: float = 0.0  # bleibt auf der Fläche stehen (0: fertig)
    gleichlauf: bool = True  # das Material rechts der Fahrtrichtung; sonst links (Gegenlauf)
    # „rohteil“, „morph“, „inseln“, „adaptiv“ – oder „ringe“ (RINGE): die schnellste der Ringe;
    # None: alle rechnen, die schnellste, die die Last hält.
    variante: str = None
    einfahrradius: float = None  # der Viertelkreis hinein und heraus; None: der Vorschlag
    schneidenlaenge: float = 0.0  # 0: unbekannt – sonst höchstens so tief je Lage
    sicherheit: float = vb.SICHERHEIT  # so weit über dem Material endet der Eilgang hinab
    eintauchwinkel: float = vb.EINTAUCHWINKEL  # Grad, für die Rampe ins Material
    austritt: float = AUSTRITT_ANTEIL
    vorschub: float = 0.0  # mm/min – für die Zeit; 0: 1000
    eintauchen: float = 0.0  # mm/min senkrecht; 0: wie der Vorschub


@dataclass
class Raeumbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    flaechen: int  # so viele Flächen geräumt
    lagen: int  # Lagen, über alle Flächen
    ringe: int  # Ringe, über alle Flächen und Lagen
    laeufe: int  # Läufe (ein Ring kann in mehreren Läufen gefahren werden)
    z_min: float  # die tiefste Spitze (mm)
    laenge: float  # mm im Vorschub
    zeit: float  # Minuten (bahn.zeit)
    variante: str  # die gerechnete Variante („rohteil“, „morph“, „inseln“, „adaptiv“)
    zeiten: dict = field(default_factory=dict)  # Minuten je gerechneter Variante
    rampen: int = 0  # Läufe über die Rampe ins Material
    einfahrten: int = 0  # Läufe, die im Freien eintauchten und tangential oder quer hineinfuhren
    anschluesse: int = 0  # Läufe, die an den vorigen anschlossen (die Spirale)
    rampen_bei: list = field(default_factory=list)  # je Rampe: (Ring, Zahl der Stellen)
    nachgeholt: int = 0  # Anfangsstücke, die nach den Ringen um die Insel nachkamen
    # Mit Materialstand (W-012): was über den Flächen noch steht und was die Operationen davor
    # dort schon weggenommen haben (mm³), und welche das waren.
    noch: float = 0.0
    weg: float = 0.0
    davor: list = field(default_factory=list)
    # Die Böden von Taschen („Face26“ …), in die der Fräser nicht passt: Dort steht noch
    # Material, aber kein Ring hat Platz – sie bleiben stehen (ein kleinerer Fräser).
    ausgelassen: list = field(default_factory=list)
    # Varianten, die die Last nicht halten: {Variante: größte Last in ae} (bahn.LAST_KURZ,
    # bahn.LAST_DAUERND) – die schneller gewesen wären; hält keine, steht die gewählte dabei.
    ueberlastet: dict = field(default_factory=dict)
    tiefen: dict = field(default_factory=dict)  # {z der Lage: so tief schneidet sie} – für last()
    haelt: bool = True  # die gewählte Variante hält die Last (False: keine hält sie)
    breit: dict = field(default_factory=dict)  # {z einer dünnen Lage: ihr ae} (bahn.DUENN)


# --- Das Raster: Hüllfläche, Rohteil, Freies ---------------------------------------------------


class _Feld:
    """Das Raster über dem Bereich: die Hüllfläche (so tief darf die Spitze), ob der Fräser das
    Rohteil berührt, und – je Lage – wo er schon war (`frei`)."""

    def __init__(
        self, netz, geformt, zugabe, r, x0, x1, y0, y1, schritt, rohteil, rand_eng, roh=None
    ):
        self.schritt = float(schritt)
        self.zugabe = zugabe
        self.r = r
        self.x0 = x0 - schritt
        self.y0 = y0 - schritt
        self.nx = max(3, int(math.ceil((x1 - self.x0) / schritt)) + 2)
        self.ny = max(3, int(math.ceil((y1 - self.y0) / schritt)) + 2)
        self.xs = self.x0 + schritt * np.arange(self.nx)
        self.ys = self.y0 + schritt * np.arange(self.ny)
        if roh is not None and roh.shape == (self.nx, self.ny):
            self.roh = roh  # schon gerechnet (eine andere Variante derselben Fläche)
        elif len(netz.dreiecke):
            self.roh = hf.je_zeile(netz, geformt, self.ys, self.x0, schritt, self.nx, True)
        else:
            self.roh = np.full((self.nx, self.ny), hf.KEIN_TREFFER)
        gx, gy = np.meshgrid(self.xs, self.ys, indexing="ij")
        self.tiefe = _rohteil_tiefe(gx, gy, rohteil)  # so tief liegt die Zelle im Rohteil
        self.beruehrt = kb._im_rohteil(gx, gy, rohteil, r)  # die Stirn trifft das Rohteil
        # Die Mitte höchstens `rand_eng` außerhalb des Rohteils – für die Ringe des Feldes, die
        # sonst bis R in die Luft schnitten.
        self.eng = kb._im_rohteil(gx, gy, rohteil, rand_eng)
        self.frei = np.zeros((self.nx, self.ny), dtype=bool)
        x0r, x1r, y0r, y1r = rohteil
        self.rohteil_zellen = (gx >= x0r) & (gx <= x1r) & (gy >= y0r) & (gy <= y1r)
        m = int(math.ceil((r - 0.01) / schritt))
        dx = np.arange(-m, m + 1)[:, None] * schritt
        dy = np.arange(-m, m + 1)[None, :] * schritt
        self._stempel = (dx * dx + dy * dy) <= (r - 0.01) ** 2
        self._m = m
        self._kern = None  # die Scheibe im Frequenzraum, für eingriff()
        self._ganz = (self.beruehrt, self.eng, self.rohteil_zellen)  # das ganze Rohteil
        self.mit_material = False  # gerade mit Materialstand (material_setzen)
        self._scheiben = {}  # je Radius die Scheibe im Frequenzraum, für aufweiten()
        # In einer Tasche: nur die Knoten in ihrer Kontur (_flaeche) – sonst dürfte die Spitze
        # überall hin, wo das Teil tiefer liegt als ihr Boden.
        self.nur = None
        # Mit Materialstand zählt `tiefe` vom Rand dessen, was noch steht (_tiefe_vom_material).
        self._tiefe_rohteil = self.tiefe
        self.vom_material = False

    def zellen(self, x, y):
        """(i, j) der Zellen, in denen (x, y) liegen – auf das Raster begrenzt."""
        i = np.clip(np.rint((np.asarray(x, dtype=float) - self.x0) / self.schritt), 0, self.nx - 1)
        j = np.clip(np.rint((np.asarray(y, dtype=float) - self.y0) / self.schritt), 0, self.ny - 1)
        return i.astype(int), j.astype(int)

    def im_raster(self, x, y):
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        return (x >= self.xs[0]) & (x <= self.xs[-1]) & (y >= self.ys[0]) & (y <= self.ys[-1])

    def erlaubt_feld(self, lage, ziel):
        """(nx, ny): darf die Spitze auf der Lage in die Zelle? Nicht, wo die Hüllfläche höher
        liegt – es sei denn, nichts steht höher als das Ziel (die Fläche selbst) –, und in einer
        Tasche nur in ihrer Kontur (`nur`)."""
        erlaubt = (self.roh + self.zugabe <= lage + GLEICH) | (self.roh <= ziel + GLEICH)
        return erlaubt if self.nur is None else erlaubt & self.nur

    def bei(self, feld, x, y):
        """Der Wert des Feldes an (x, y) – der strengste der vier Nachbarn bei Wahrheitswerten
        (alle müssen), sonst der nächste Knoten."""
        fx = (np.asarray(x, dtype=float) - self.x0) / self.schritt
        fy = (np.asarray(y, dtype=float) - self.y0) / self.schritt
        i0 = np.clip(np.floor(fx).astype(int), 0, self.nx - 1)
        j0 = np.clip(np.floor(fy).astype(int), 0, self.ny - 1)
        i1 = np.minimum(i0 + 1, self.nx - 1)
        j1 = np.minimum(j0 + 1, self.ny - 1)
        if feld.dtype == bool:
            return feld[i0, j0] & feld[i1, j0] & feld[i0, j1] & feld[i1, j1]
        return feld[
            np.clip(np.rint(fx).astype(int), 0, self.nx - 1),
            np.clip(np.rint(fy).astype(int), 0, self.ny - 1),
        ]

    def ungeschnitten(self, x, y):
        """Je Stelle der Anteil der Stirn, unter dem noch ungeschnittenes Rohteil liegt (0 … 1)."""
        i, j = self.zellen(x, y)
        m = self._m
        roh = self.rohteil_zellen & ~self.frei
        zahl = float(self._stempel.sum())
        ergebnis = np.zeros(len(i))
        for k, (ci, cj) in enumerate(zip(i, j, strict=True)):
            i0, j0 = ci - m, cj - m
            a0, b0 = max(i0, 0), max(j0, 0)
            a1, b1 = min(i0 + 2 * m + 1, self.nx), min(j0 + 2 * m + 1, self.ny)
            if a1 <= a0 or b1 <= b0:
                continue
            fenster = roh[a0:a1, b0:b1] & self._stempel[a0 - i0 : a1 - i0, b0 - j0 : b1 - j0]
            ergebnis[k] = fenster.sum() / zahl
        return ergebnis

    def eingriff(self):
        """(nx, ny): je Zelle der Anteil der Stirn über ungeschnittenem Rohteil, wenn die Mitte
        dort steht – wie ungeschnitten(), für alle Zellen auf einmal (Faltung mit der Scheibe
        über die FFT)."""
        m = self._m
        groesse = (self.nx + 2 * m + 1, self.ny + 2 * m + 1)
        if self._kern is None:
            kern = np.zeros(groesse)
            kern[: 2 * m + 1, : 2 * m + 1] = self._stempel
            self._kern = np.fft.rfft2(kern)
        roh = np.zeros(groesse)
        roh[: self.nx, : self.ny] = self.rohteil_zellen & ~self.frei
        gefaltet = np.fft.irfft2(np.fft.rfft2(roh) * self._kern, s=groesse)
        return gefaltet[m : m + self.nx, m : m + self.ny] / float(self._stempel.sum())

    def aufweiten(self, maske, radius):
        """Die Maske um `radius` weiter: wahr, wo eine Scheibe mit dem Radius um den Knoten
        etwas Wahres trifft (Faltung über die FFT, je Radius die Scheibe einmal)."""
        if radius <= 0:
            return maske.copy()
        m = max(0, int(math.ceil(radius / self.schritt)))
        groesse = (self.nx + 2 * m + 1, self.ny + 2 * m + 1)
        kern = self._scheiben.get((m, round(radius, 6)))
        if kern is None:
            d = np.arange(-m, m + 1) * self.schritt
            scheibe = np.zeros(groesse)
            scheibe[: 2 * m + 1, : 2 * m + 1] = (d[:, None] ** 2 + d[None, :] ** 2) <= radius**2
            kern = self._scheiben[(m, round(radius, 6))] = np.fft.rfft2(scheibe)
        werte = np.zeros(groesse)
        werte[: self.nx, : self.ny] = maske
        gefaltet = np.fft.irfft2(np.fft.rfft2(werte) * kern, s=groesse)
        return gefaltet[m : m + self.nx, m : m + self.ny] > 0.5

    def material_setzen(self, hoehe, naechste, lage, erlaubt):
        """Mit Materialstand (W-012), je Lage: Rohteil ist nur noch, was über der Lage steht
        (`hoehe`: so hoch steht es je Knoten); die Ringe fahren nur, wo ihre Stirn davon trifft,
        was sie hier wegnehmen kann (`naechste`: die Höhe der nächsten Zelle des Materialstands
        – eine Zelle weniger weit als die Stirn vom Erlaubten, wie im 3D-Schruppen: Der Rand am
        Gesperrten, den eine Operation davor stehen ließ, zählt nicht jede Lage). Gibt zurück, ob
        es auf der Lage etwas zu tun gibt."""
        beruehrt, eng, rohteil = self._ganz
        abtragbar = rohteil & (naechste > lage + MATERIAL)
        abtragbar &= self.aufweiten(erlaubt, self.r - self.schritt - 0.01)
        if abtragbar.sum() * self.schritt * self.schritt < MINDESTFLAECHE:
            return False
        um = self.aufweiten(abtragbar, self.r)
        self.rohteil_zellen = rohteil & (hoehe > lage + MATERIAL)
        self.beruehrt = beruehrt & um
        self.eng = eng & um
        self.mit_material = True
        self._tiefe_vom_material()
        return True

    def _tiefe_vom_material(self):
        """Mit Materialstand beginnen die Ringe vom Rohteil her am Rand dessen, was noch steht
        (Spezifikation Strategien 13.5, T1): `tiefe` ist dann außerhalb davon der Abstand zu
        ihm, negativ – wie am Rand des Rohteils. An Manuels Testteil steht nach dem Räumen um die
        Insel über ihr noch ein Klotz mit ihrem Umriss; die Ringe der nächsten Fläche legen sich
        um ihn, statt als Rechtecke des Rohteils durch die Luft zu laufen. Als außen gilt nur,
        wohin der Fräser vom Rand her durch die Luft kommt: Ein Loch im Material (eine Nut, die
        schon gefräst ist) beginnt keine Ringe, die Ringe von außen fahren darüber hinweg. Reicht
        die Luft nirgends ins Rohteil, bleibt es beim Rechteck des Rohteils – genau, mit Bögen."""
        material = self.rohteil_zellen
        rand = np.zeros_like(material)
        rand[0, :] = rand[-1, :] = rand[:, 0] = rand[:, -1] = True
        start = np.where(rand & ~material, 0.0, np.inf)
        aussen = np.isfinite(_geodaetisch(start, ~material, self.schritt))
        luft = aussen & self._ganz[2]
        if luft.sum() * self.schritt * self.schritt < MINDESTFLAECHE:
            self.tiefe, self.vom_material = self._tiefe_rohteil, False
            return
        weit = self.r + 2.0 * self.schritt
        self.tiefe = np.where(aussen, -self._abstand_bis(material, aussen, weit), self.schritt)
        self.vom_material = True

    def _abstand_bis(self, maske, wo, weit):
        """(nx, ny) mm: je Knoten in `wo` sein Abstand zur Maske, höchstens `weit` – sonst
        überall `weit`."""
        abstand = np.full((self.nx, self.ny), float(weit))
        band = wo & self.aufweiten(maske, weit)
        if not band.any():
            return abstand
        innen = np.ones_like(maske)
        innen[1:, :] &= maske[:-1, :]
        innen[:-1, :] &= maske[1:, :]
        innen[:, 1:] &= maske[:, :-1]
        innen[:, :-1] &= maske[:, 1:]
        ri, rj = np.nonzero(maske & ~innen)
        rx, ry = self.xs[ri], self.ys[rj]
        bi, bj = np.nonzero(band)
        block = max(1, 2_000_000 // max(len(rx), 1))
        for a in range(0, len(bi), block):
            i, j = bi[a : a + block], bj[a : a + block]
            dx = self.xs[i][:, None] - rx[None, :]
            dy = self.ys[j][:, None] - ry[None, :]
            abstand[i, j] = np.minimum(np.sqrt((dx * dx + dy * dy).min(axis=1)), weit)
        return abstand

    def ganzes_rohteil(self):
        """Wieder das ganze Rohteil (ohne Materialstand)."""
        self.beruehrt, self.eng, self.rohteil_zellen = self._ganz
        self.mit_material = False
        self.tiefe, self.vom_material = self._tiefe_rohteil, False

    def hoechstes(self, hoehe, x, y, lage):
        """Das höchste Material (`hoehe`) unter der Stirn um (x, y), um eine Zelle größer –
        wo der Fräser auf dieser `lage` schon war (frei), höchstens sie; −inf, wenn keins."""
        m = int(math.ceil(self.r / self.schritt)) + 1
        i, j = self.zellen([x], [y])
        ci, cj = int(i[0]), int(j[0])
        a0, b0 = max(ci - m, 0), max(cj - m, 0)
        a1, b1 = min(ci + m + 1, self.nx), min(cj + m + 1, self.ny)
        if a1 <= a0 or b1 <= b0:
            return -math.inf
        dx = (np.arange(a0, a1) - ci)[:, None] * self.schritt
        dy = (np.arange(b0, b1) - cj)[None, :] * self.schritt
        werte = hoehe[a0:a1, b0:b1]
        werte = np.where(self.frei[a0:a1, b0:b1], np.minimum(werte, lage), werte)
        fenster = werte[dx * dx + dy * dy <= (self.r + self.schritt) ** 2]
        return float(fenster.max()) if fenster.size else -math.inf

    def frei_bei(self, x, y):
        """Ist (x, y) frei: der Fräser war schon da – oder er trifft dort kein Rohteil?"""
        i, j = self.zellen(x, y)
        return self.frei[i, j] | ~self.beruehrt[i, j]

    def merke(self, x, y):
        """Der Fräser ist über (x, y) gefahren: die Zellen unter seiner Stirn sind frei."""
        i, j = self.zellen(x, y)
        m = self._m
        for ci, cj in zip(i, j, strict=True):
            i0, j0 = ci - m, cj - m
            a0, b0 = max(i0, 0), max(j0, 0)
            a1, b1 = min(i0 + 2 * m + 1, self.nx), min(j0 + 2 * m + 1, self.ny)
            if a1 <= a0 or b1 <= b0:
                continue
            self.frei[a0:a1, b0:b1] |= self._stempel[a0 - i0 : a1 - i0, b0 - j0 : b1 - j0]

    def abstand_zu(self, gesperrt):
        """(nx, ny) mm: der Abstand jeder Zelle zum Rand des Gesperrten (`gesperrt`: bool), im
        Gesperrten selbst negativ; +inf, wenn nichts gesperrt ist."""
        if not gesperrt.any():
            return np.full((self.nx, self.ny), np.inf)
        # Der Rand des Gesperrten: gesperrte Zellen mit einem freien Nachbarn (der Rand des
        # Rasters zählt nicht als frei).
        innen = np.ones_like(gesperrt)
        innen[1:, :] &= gesperrt[:-1, :]
        innen[:-1, :] &= gesperrt[1:, :]
        innen[:, 1:] &= gesperrt[:, :-1]
        innen[:, :-1] &= gesperrt[:, 1:]
        rand = gesperrt & ~innen
        ri, rj = np.nonzero(rand)
        if not len(ri):
            ri, rj = np.nonzero(gesperrt)
        rx = self.xs[ri]
        ry = self.ys[rj]
        gx, gy = np.meshgrid(self.xs, self.ys, indexing="ij")
        px, py = gx.ravel(), gy.ravel()
        abstand = np.empty(len(px))
        block = max(1, 2_000_000 // max(len(rx), 1))
        for a in range(0, len(px), block):
            dx = px[a : a + block, None] - rx[None, :]
            dy = py[a : a + block, None] - ry[None, :]
            abstand[a : a + block] = np.sqrt((dx * dx + dy * dy).min(axis=1))
        abstand = abstand.reshape(self.nx, self.ny)
        return np.where(gesperrt, -abstand - self.schritt, abstand)


# --- Höhenlinien (Marching Squares) ------------------------------------------------------------

# Je Fall (Bits: unten links 1, unten rechts 2, oben rechts 4, oben links 8 – über dem Niveau)
# die Kanten, die eine Linie verbindet: 0 unten, 1 rechts, 2 oben, 3 links.
_FAELLE = {
    1: [(3, 0)],
    2: [(0, 1)],
    3: [(3, 1)],
    4: [(1, 2)],
    6: [(0, 2)],
    7: [(3, 2)],
    8: [(2, 3)],
    9: [(0, 2)],
    11: [(1, 2)],
    12: [(1, 3)],
    13: [(0, 1)],
    14: [(3, 0)],
}


def _hoehenlinien(feld, xs, ys, niveau, sperre=None):
    """[(punkte (m, 2), geschlossen)] – die Linien, auf denen `feld` (nx, ny) das Niveau hat;
    Marching Squares mit Interpolation auf den Zellkanten. `sperre` (nx, ny, bool): durch Zellen,
    die eine gesperrte Ecke haben, läuft keine Linie – sie endet davor."""
    f = np.where(np.isfinite(feld), feld, np.where(feld > 0, 1e9, -1e9))
    ueber = f > niveau
    c0 = ueber[:-1, :-1]
    c1 = ueber[1:, :-1]
    c2 = ueber[1:, 1:]
    c3 = ueber[:-1, 1:]
    fall = c0 * 1 + c1 * 2 + c2 * 4 + c3 * 8
    if sperre is not None:
        gesperrt = sperre[:-1, :-1] | sperre[1:, :-1] | sperre[1:, 1:] | sperre[:-1, 1:]
        fall = np.where(gesperrt, 0, fall)
    ii, jj = np.nonzero((fall > 0) & (fall < 15))
    if not len(ii):
        return []
    faelle = fall[ii, jj]
    f00, f10, f11, f01 = f[ii, jj], f[ii + 1, jj], f[ii + 1, jj + 1], f[ii, jj + 1]

    def anteil(a, b):
        d = b - a
        return np.where(
            np.abs(d) > _WINZIG,
            np.clip((niveau - a) / np.where(np.abs(d) > _WINZIG, d, 1.0), 0.0, 1.0),
            0.5,
        )

    sx = xs[1] - xs[0]
    sy = ys[1] - ys[0]
    # Die Schnittpunkte auf den vier Kanten jeder Zelle: unten, rechts, oben, links.
    kante_x = [xs[ii] + sx * anteil(f00, f10), xs[ii + 1], xs[ii] + sx * anteil(f01, f11), xs[ii]]
    kante_y = [ys[jj], ys[jj] + sy * anteil(f10, f11), ys[jj + 1], ys[jj] + sy * anteil(f00, f01)]
    # Die Kennung jeder Kante (gemeinsam für Nachbarzellen): waagerecht (0, i, j), senkrecht (1, i, j).
    kennung = [
        (0, ii, jj),  # unten
        (1, ii + 1, jj),  # rechts
        (0, ii, jj + 1),  # oben
        (1, ii, jj),  # links
    ]
    mitte = (f00 + f10 + f11 + f01) / 4 > niveau
    segmente = []  # (kennung_a, kennung_b, (xa, ya), (xb, yb))
    for nummer in range(len(ii)):
        fall_n = int(faelle[nummer])
        if fall_n == 5:
            paare = [(3, 2), (0, 1)] if mitte[nummer] else [(3, 0), (1, 2)]
        elif fall_n == 10:
            paare = [(0, 1), (2, 3)] if mitte[nummer] else [(0, 3), (1, 2)]
        else:
            paare = _FAELLE[fall_n]
        for a, b in paare:
            ka = (kennung[a][0], int(kennung[a][1][nummer]), int(kennung[a][2][nummer]))
            kb_ = (kennung[b][0], int(kennung[b][1][nummer]), int(kennung[b][2][nummer]))
            segmente.append(
                (
                    ka,
                    kb_,
                    (float(kante_x[a][nummer]), float(kante_y[a][nummer])),
                    (float(kante_x[b][nummer]), float(kante_y[b][nummer])),
                )
            )
    return _verketten(segmente)


def _verketten(segmente):
    """Segmente (Kante, Kante, Punkt, Punkt) zu Linienzügen – geschlossen, wo der Zug zu seiner
    ersten Kante zurückkommt."""
    an_kante = {}
    for nummer, (ka, kb_, _pa, _pb) in enumerate(segmente):
        an_kante.setdefault(ka, []).append(nummer)
        an_kante.setdefault(kb_, []).append(nummer)
    benutzt = [False] * len(segmente)
    ergebnis = []
    for start in range(len(segmente)):
        if benutzt[start]:
            continue
        benutzt[start] = True
        ka, kb_, pa, pb = segmente[start]
        kette = [pa, pb]
        geschlossen = False
        # vorwärts ab kb_, dann rückwärts ab ka
        for richtung in (1, -1):
            kante = kb_ if richtung == 1 else ka
            while True:
                naechste = [n for n in an_kante.get(kante, ()) if not benutzt[n]]
                if not naechste:
                    break
                n = naechste[0]
                benutzt[n] = True
                na, nb, qa, qb = segmente[n]
                if na == kante:
                    punkt, kante = qb, nb
                else:
                    punkt, kante = qa, na
                if richtung == 1:
                    kette.append(punkt)
                else:
                    kette.insert(0, punkt)
                if kante == (ka if richtung == 1 else kb_):
                    geschlossen = True
                    break
            if geschlossen:
                break
        punkte = np.array(kette, dtype=float)
        if geschlossen and len(punkte) > 1 and np.hypot(*(punkte[0] - punkte[-1])) <= _WINZIG:
            punkte = punkte[:-1]
        ergebnis.append((punkte, geschlossen))
    return ergebnis


def _vereinfacht(punkte, toleranz, geschlossen):
    """Douglas–Peucker: so wenige Ecken, dass der Linienzug höchstens `toleranz` abweicht."""
    if len(punkte) < 3:
        return punkte
    if geschlossen:
        # Zwei Hälften, damit das Ende nicht mit dem Anfang verschmilzt.
        h = len(punkte) // 2
        a = _vereinfacht(punkte[: h + 1], toleranz, False)
        b = _vereinfacht(np.vstack([punkte[h:], punkte[:1]]), toleranz, False)
        return np.vstack([a[:-1], b[:-1]])
    behalten = np.zeros(len(punkte), dtype=bool)
    behalten[0] = behalten[-1] = True
    stapel = [(0, len(punkte) - 1)]
    while stapel:
        i, j = stapel.pop()
        if j <= i + 1:
            continue
        p, q = punkte[i], punkte[j]
        d = q - p
        laenge = math.hypot(d[0], d[1])
        zwischen = punkte[i + 1 : j]
        if laenge <= _WINZIG:
            abstand = np.hypot(zwischen[:, 0] - p[0], zwischen[:, 1] - p[1])
        else:
            abstand = (
                np.abs((zwischen[:, 0] - p[0]) * d[1] - (zwischen[:, 1] - p[1]) * d[0]) / laenge
            )
        k = int(np.argmax(abstand))
        if abstand[k] > toleranz:
            behalten[i + 1 + k] = True
            stapel.append((i, i + 1 + k))
            stapel.append((i + 1 + k, j))
    return punkte[behalten]


def _segmente_aus(punkte, geschlossen):
    """[_Strecke] aus einem Linienzug."""
    ergebnis = []
    n = len(punkte)
    for i in range(n if geschlossen else n - 1):
        p, q = punkte[i], punkte[(i + 1) % n]
        if math.hypot(q[0] - p[0], q[1] - p[1]) > _WINZIG:
            ergebnis.append(kb._Strecke((float(p[0]), float(p[1])), (float(q[0]), float(q[1]))))
    return ergebnis


def _umlauf(punkte):
    """Die Fläche des Umlaufs: > 0 gegen den Uhrzeigersinn."""
    x, y = punkte[:, 0], punkte[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _im_vieleck(xs, ys, px, py):
    """(len(xs), len(ys)) – liegt der Knoten (xs[i], ys[j]) im geschlossenen Vieleck mit den
    Ecken (px, py)? Zeile für Zeile: Zwischen dem ersten und zweiten, dem dritten und vierten …
    Schnitt der Zeile mit den Kanten liegt sie innen."""
    px, py = np.asarray(px, dtype=float), np.asarray(py, dtype=float)
    qx, qy = np.roll(px, -1), np.roll(py, -1)
    xs = np.asarray(xs, dtype=float)
    maske = np.zeros((len(xs), len(ys)), dtype=bool)
    for j, y in enumerate(ys):
        kreuzt = (py <= y) != (qy <= y)
        if not kreuzt.any():
            continue
        anteil = (y - py[kreuzt]) / (qy[kreuzt] - py[kreuzt])
        schnitte = np.sort(px[kreuzt] + anteil * (qx[kreuzt] - px[kreuzt]))
        maske[:, j] = np.searchsorted(schnitte, xs) % 2 == 1
    return maske


# --- Die Ringe ------------------------------------------------------------------------------------


@dataclass
class _Ring:
    """Ein Ring: seine Segmente und Proben (kontur_bahn), ob geschlossen; `genau`: aus der
    Geometrie gerechnet (der Versatz einer Insel) – das Raster prüft ihn nicht nach."""

    segmente: list
    proben: object
    geschlossen: bool
    genau: bool = False
    tasche: bool = False  # genau, an der Wand einer Tasche (das Material außen)


def _ring_aus_linie(
    punkte, geschlossen, material_links, feld, niveau, werte, schritt, toleranz, material_hoch=False
):
    """Ein Ring aus einer Höhenlinie des Feldes `werte`: vereinfacht, so gerichtet, dass das
    Material links liegt – oder rechts (Gegenlauf). Das Material liegt, wo das Feld kleiner ist
    (D: näher am Gesperrten) oder, mit `material_hoch`, wo es größer ist (F: tiefer im Rest)."""
    punkte = _vereinfacht(punkte, toleranz, geschlossen)
    if len(punkte) < 2:
        return None
    # Liegt das Material links? Neben der Mitte der längsten Stücke nachsehen – an einer Ecke
    # oder in einer Kerbe trifft die Probe sonst beidseits denselben Knoten.
    n = len(punkte)
    stuecke = range(n if geschlossen else n - 1)
    laengen = [math.hypot(*(punkte[(i + 1) % n] - punkte[i])) for i in stuecke]
    material_ist_links = not material_hoch
    for i in sorted(stuecke, key=lambda k: -laengen[k]):
        p, q = punkte[i], punkte[(i + 1) % n]
        tx, ty = q[0] - p[0], q[1] - p[1]
        laenge = math.hypot(tx, ty) or 1.0
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        weit = 1.5 * schritt
        links = (mx - ty / laenge * weit, my + tx / laenge * weit)
        rechts = (mx + ty / laenge * weit, my - tx / laenge * weit)
        d_links = float(feld.bei(werte, [links[0]], [links[1]])[0])
        d_rechts = float(feld.bei(werte, [rechts[0]], [rechts[1]])[0])
        if abs(d_links - d_rechts) > _WINZIG:
            material_ist_links = (d_links > d_rechts) if material_hoch else (d_links < d_rechts)
            break
    if material_ist_links != material_links:
        punkte = punkte[::-1].copy()
    segmente = _segmente_aus(punkte, geschlossen)
    if not segmente:
        return None
    return _Ring(segmente, kb._abtasten(segmente, schritt, geschlossen), geschlossen)


def _rohteil_tiefe(gx, gy, rohteil):
    """Je Zelle, wie tief sie im Rohteil liegt (mm): drinnen der Abstand zum nächsten Rand,
    draußen der Abstand zum Rohteil, negativ – die Höhenlinien sind die Ringe von
    _rohteil_ring (draußen mit runden Ecken)."""
    x0, x1, y0, y1 = rohteil
    innen = np.minimum(np.minimum(gx - x0, x1 - gx), np.minimum(gy - y0, y1 - gy))
    dx = np.maximum(np.maximum(x0 - gx, 0.0), gx - x1)
    dy = np.maximum(np.maximum(y0 - gy, 0.0), gy - y1)
    return np.where(innen >= 0, innen, -np.hypot(dx, dy))


def _rohteil_ring(rohteil, tiefe, material_links, schritt):
    """Der Ring um das Rohteil, um `tiefe` nach innen gerückt (negativ: außerhalb, die Ecken
    rund mit dem Radius −tiefe); None, wenn er nicht mehr hineinpasst. Gegen den Uhrzeigersinn
    (Material innen = links), sonst umgekehrt."""
    x0, x1, y0, y1 = rohteil
    a0, a1, b0, b1 = x0 + tiefe, x1 - tiefe, y0 + tiefe, y1 - tiefe
    if a1 - a0 <= GLEICH or b1 - b0 <= GLEICH:
        return None
    if tiefe >= 0:
        ecken = [(a0, b0), (a1, b0), (a1, b1), (a0, b1)]
        segmente = [kb._Strecke(ecken[i], ecken[(i + 1) % 4]) for i in range(4)]
    else:
        r = -tiefe
        segmente = [
            kb._Strecke((a0 + r, b0), (a1 - r, b0)),
            kb._Bogen((a1 - r, b0), (a1, b0 + r), (a1 - r, b0 + r), False),
            kb._Strecke((a1, b0 + r), (a1, b1 - r)),
            kb._Bogen((a1, b1 - r), (a1 - r, b1), (a1 - r, b1 - r), False),
            kb._Strecke((a1 - r, b1), (a0 + r, b1)),
            kb._Bogen((a0 + r, b1), (a0, b1 - r), (a0 + r, b1 - r), False),
            kb._Strecke((a0, b1 - r), (a0, b0 + r)),
            kb._Bogen((a0, b0 + r), (a0 + r, b0), (a0 + r, b0 + r), False),
        ]
        segmente = [s for s in segmente if s.laenge > GLEICH]
    if not material_links:
        segmente = [s.umgekehrt() for s in reversed(segmente)]
    return _Ring(segmente, kb._abtasten(segmente, schritt, True), True)


# --- Der Ablauf je Lage -----------------------------------------------------------------------------


@dataclass
class _Stand:
    punkte: list = field(default_factory=list)
    flaechen: int = 0
    lagen: int = 0
    ringe: int = 0
    laeufe: int = 0
    rampen: int = 0  # Läufe, die über die Rampe ins Material gingen
    einfahrten: int = 0  # Läufe, die im Freien eintauchten und tangential hineinfuhren
    seitlich: int = 0  # Läufe, die im Freien eintauchten und quer in die Bahn fuhren
    anschluesse: int = 0  # Läufe, die an den vorigen anschlossen (die Spirale)
    rampen_bei: list = field(default_factory=list)  # je Rampe: (Ring, Zahl der Stellen)
    nachgeholt: int = 0  # Anfangsstücke, die nach den Ringen um die Insel nachkamen
    z_min: float = math.inf
    laenge: float = 0.0
    noch: float = 0.0  # mit Materialstand: was über den Flächen noch steht (mm³)
    weg: float = 0.0  # … und was die Operationen davor dort schon weggenommen haben
    davor: list = field(default_factory=list)  # … und welche das waren
    ausgelassen: list = field(default_factory=list)  # Taschenböden, in die der Fräser nicht passt
    tiefen: dict = field(default_factory=dict)  # {z der Lage: so tief schneidet sie} – für last()
    breit: dict = field(default_factory=dict)  # {z einer dünnen Lage: ihr ae} – für last()

    def dazu(self, teil):
        """Hängt die Bahn einer Fläche (`teil`, ein eigener _Stand) an."""
        self.punkte += teil.punkte
        for z, tiefe in teil.tiefen.items():
            self.tiefen[z] = max(self.tiefen.get(z, 0.0), tiefe)
        self.breit.update(teil.breit)
        self.rampen_bei += teil.rampen_bei
        self.ausgelassen += teil.ausgelassen
        self.davor += [name for name in teil.davor if name not in self.davor]
        self.z_min = min(self.z_min, teil.z_min)
        for zahl in (
            "flaechen", "lagen", "ringe", "laeufe", "rampen", "einfahrten", "seitlich",
            "anschluesse", "nachgeholt", "laenge", "noch", "weg",
        ):  # fmt: skip
            setattr(self, zahl, getattr(self, zahl) + getattr(teil, zahl))


class _Lage:
    """Eine Lage: fährt Ringe als Läufe, merkt sich Freies, hängt Läufe aneinander."""

    # Mit Materialstand (W-012): (nx, ny), bis wohin das Material je Knoten reicht.
    stand_hoehe = None

    def __init__(
        self, st, feld, w, r, r_ein, gerade, lage, vorige, erlaubt, schritt, oben=None, decke=None
    ):
        self.st = st
        self.feld = feld
        self.w = w
        self.r = r
        self.r_ein = r_ein
        self.gerade = gerade
        self.lage = lage
        self.vorige = vorige
        self.erlaubt = erlaubt
        self.schritt = schritt
        # Wo das Material über der Fläche beginnt (in der Tasche ihre Oberkante) – und die Decke:
        # die Oberkante des Rohteils. Über der ersten Lage einer Tasche darf der Eilgang nur bis
        # über die Decke hinab, denn ob jemand das Rohteil darüber schon weggefräst hat, weiß die
        # Bahn nicht (der Prüfstand fand 2034 mm³ im Eilgang, P-2026-10-01-26) – mit
        # Materialstand das höchste Material im Raster.
        self.oben = w.oben if oben is None else oben
        self.decke = w.oben if decke is None else decke
        self.unten = False  # die Spitze steht auf der Lage (am Ende des letzten Laufs)
        self.ort = None  # (x, y) der Spitze dort
        self.knapp = min(w.sicher, self.decke + w.sicherheit)  # Eilgang über dem Rohteil
        # So viel der Stirn darf beim Ein- und Ausfahren über ungeschnittenem Rohteil liegen:
        # anderthalbmal der Streifen ae, den jeder Ring ohnehin nimmt (Kreisabschnitt).
        h = min(w.zeilenabstand, r)
        abschnitt = r * r * math.acos((r - h) / r) - (r - h) * math.sqrt(2 * r * h - h * h)
        self.schwelle = 1.5 * abschnitt / (math.pi * r * r) + 0.02
        self.reste = []  # [(Ring, Stellen)]: Anfangsstücke, die nach den Ringen nachkommen
        self.verschieben = True
        # Was der Fräser auf dieser Lage überhaupt wegnehmen kann: Rohteil, das seine Stirn von
        # einer erlaubten Stelle aus trifft (_schneidet).
        self._abtragbar = None
        # Nach dem Adaptiv-Kern: auf einen ganzen Ring gleitend einschwenken (_schwenke_ein).
        self.einschwenken = False
        self.gedreht = False  # gerade ein ganzer Ring, der anderswo anfängt (_eingang_irgendwo)
        # Die freie Seite der Bahn: links im Gleichlauf (das Material rechts), sonst rechts –
        # dorthin gehen das Einfahren und der Weg quer hinein.
        self.frei_rechts = not w.gleichlauf

    def frei(self, qx, qy):
        """Darf das Ein- und Ausfahren dorthin: im Raster, erlaubt, und unter der Stirn höchstens
        so viel ungeschnittenes Rohteil wie im Streifen ae – bis auf den letzten Punkt, der
        liegt auf der Bahn?"""
        qx, qy = np.asarray(qx, dtype=float), np.asarray(qy, dtype=float)
        if not self.feld.im_raster(qx, qy).all():
            return False
        if not self.feld.bei(self.erlaubt, qx, qy).all():
            return False
        if len(qx) < 2:
            return True
        return bool((self.feld.ungeschnitten(qx[:-1], qy[:-1]) <= self.schwelle).all())

    def ring(self, ring, eng=False, kennung="", nur=None, luft=False):
        """Fährt einen Ring – in Läufen, wo erlaubt und Rohteil ist (`eng`: die Mitte höchstens
        ae außerhalb des Rohteils, sonst bis R; `nur`: je Probe, ob sie überhaupt gefahren
        werden soll; `luft`: auch, wo der Fräser kein Rohteil trifft – ein Ring des Morphs
        bleibt ganz, statt an einer Ecke in der Luft in Läufe zu zerfallen). Gibt die Zahl der
        Läufe."""
        self.kennung = kennung
        proben = ring.proben
        x, y = proben.x, proben.y
        n = len(x)
        if n < 2:
            return 0
        im_rohteil = self.feld.eng if eng else self.feld.beruehrt
        drin = self.feld.im_raster(x, y)
        if not ring.genau:
            drin &= self.feld.bei(self.erlaubt, x, y)
        if nur is not None:
            drin &= nur
        if not luft:
            zellen = self.feld.zellen(x, y)
            ganz = drin & self.feld._ganz[1 if eng else 0][zellen]  # wie ohne Materialstand
            drin &= im_rohteil[zellen]
            if self.feld.mit_material:
                # Über eine kurze Lücke im Weggefrästen im Vorschub hinweg (LUECKE).
                laenge = max(LUECKE * 2.0 * self.r, LUECKE_MIN)
                drin = _luecken_zu(drin, ganz, proben, ring.geschlossen, laenge)
        if not drin.any():
            return 0
        if not self._schneidet(x[drin], y[drin]):
            return 0  # der ganze Ring führe durch die Luft (T1b)
        laeufe = []  # [(Stellen, Austritt hinten)]
        if ring.geschlossen and drin.all():
            start = self._start(x, y)
            if self.einschwenken:
                start = self._schwenke_ein(ring, start)
            laeufe.append((np.arange(start, start + n + 1) % n, False))
        elif ring.geschlossen:
            luecke = int(np.flatnonzero(~drin)[0])
            for von, bis in vb._stuecke(np.roll(drin, -luecke)):
                naechste = (bis + 1 + luecke) % n
                laeufe.append(
                    (
                        (np.arange(von, bis + 1) + luecke) % n,
                        bool(not im_rohteil[self.feld.zellen(x[naechste], y[naechste])]),
                    )
                )
        else:
            for von, bis in vb._stuecke(drin):
                hinten = bis + 1 < n and bool(
                    not im_rohteil[self.feld.zellen(x[bis + 1], y[bis + 1])]
                )
                laeufe.append((np.arange(von, bis + 1), hinten))
        laeufe = [lauf for lauf in laeufe if len(lauf[0]) >= 2]
        if not laeufe:
            return 0
        # Der nächste Lauf: der, dessen Anfang der Spitze am nächsten liegt.
        while laeufe:
            if self.ort is None:
                naechster = 0
            else:
                naechster = min(
                    range(len(laeufe)),
                    key=lambda k: math.hypot(
                        x[laeufe[k][0][0]] - self.ort[0], y[laeufe[k][0][0]] - self.ort[1]
                    ),
                )
            stellen, hinten = laeufe.pop(naechster)
            self._lauf(ring, stellen, hinten, ring.geschlossen and len(stellen) == n + 1)
        self.st.ringe += 1
        return 1

    def _schneidet(self, x, y):
        """Trifft die Stirn an den Stellen (x, y) irgendwo noch Rohteil, das auf dieser Lage weg
        kann und das die Ringe davor nicht schon genommen haben? Die Ringe vom Rand her laufen,
        bis die Mitte des Fräsers die Mitte des Materials erreicht – die letzten (R ÷ ae, beim
        Ø 12 mit ae 1,5 vier) träfen nur noch, was der Ring davor mit seinem Radius schon
        weggenommen hat (Spezifikation Strategien 13.5, T1b; Manuel am Klotz: „effektiv ist da
        nur ein Kreis“)."""
        feld = self.feld
        if self._abtragbar is None:
            # Mit dem ganzen Radius: Der Ring an der Wand nimmt nach dem Adaptiv-Kern nur noch
            # einen Rand, schmaler als eine Zelle – eine Zelle weniger gerechnet, fiele er als
            # „Luft“ aus, und an der Wand bliebe bis 0,9 mm statt des Aufmaßes.
            self._abtragbar = feld.aufweiten(self.erlaubt, max(self.r - 0.01, 0.0))
        roh = feld.rohteil_zellen & ~feld.frei & self._abtragbar
        if not roh.any():
            return False
        return bool(feld.aufweiten(roh, self.r - 0.01)[feld.zellen(x, y)].any())

    def _start(self, x, y):
        """Wo ein ganzer Ring beginnt: der Spitze am nächsten – sonst auf der längsten Geraden."""
        if self.ort is not None:
            return int(np.argmin(np.hypot(x - self.ort[0], y - self.ort[1])))
        return 0

    def _schwenke_ein(self, ring, start):
        """Nach dem Adaptiv-Kern steht der Fräser neben dem Ring an der Wand, davor ein schmaler
        Rand. Quer in ihn hinein hätte er kurz die drei- bis vierfache Breite im Eingriff – er
        schwenkt stattdessen längs des Rings über 2 R gleitend auf ihn ein (wie die Spirale des
        Morphs, _spirale); das Stück, das er dabei überspringt, schneidet der Ring an seinem Ende.
        Gibt die Stelle zurück, an der der Ring dann beginnt – `start`, wenn es nicht passt."""
        if not self.unten or self.ort is None:
            return start
        x, y = ring.proben.x, ring.proben.y
        n = len(x)
        abstand = math.hypot(x[start] - self.ort[0], y[start] - self.ort[1])
        if not _WINZIG < abstand <= 2.0 * self.w.zeilenabstand + self.schritt:
            return start
        stuecke = np.hypot(np.diff(np.append(x, x[0])), np.diff(np.append(y, y[0])))
        weit = 2.0 * self.r
        if float(stuecke.sum()) < 2.0 * weit:
            return start
        folge = (start + np.arange(n)) % n
        weg = np.concatenate([[0.0], np.cumsum(stuecke[folge])])
        k = int(np.searchsorted(weg, weit))
        stellen = folge[: k + 1]
        tx, ty = x[(stellen + 1) % n] - x[stellen], y[(stellen + 1) % n] - y[stellen]
        lang = np.maximum(np.hypot(tx, ty), _WINZIG)
        seite = 1.0 if self.frei_rechts else -1.0
        qx, qy = seite * ty / lang, -seite * tx / lang  # zur freien Seite
        if (self.ort[0] - x[start]) * qx[0] + (self.ort[1] - y[start]) * qy[0] < 0.5 * abstand:
            return start  # der Fräser steht nicht auf der freien Seite
        rest = abstand * (1.0 - weg[: k + 1] / weg[k])
        px, py = x[stellen] + qx * rest, y[stellen] + qy * rest
        if not self.feld.im_raster(px, py).all():
            return start
        punkte = self.st.punkte
        for i in range(1, k + 1):
            punkt = bn.Punkt(False, float(px[i]), float(py[i]), self.lage)
            self.st.laenge += bn.weg(punkte[-1], punkt)
            punkte.append(punkt)
        self.feld.merke(px, py)
        self.ort = (float(x[stellen[-1]]), float(y[stellen[-1]]))
        self.st.anschluesse += 1
        return int(stellen[-1])

    def _lauf(self, ring, stellen, hinten, ganz):
        """Ein Lauf; `ganz`: der ganze geschlossene Ring (die Stellen enden am Anfang)."""
        w, r = self.w, self.r
        proben, segmente = ring.proben, ring.segmente
        x, y = proben.x[stellen], proben.y[stellen]
        p0 = (float(x[0]), float(y[0]))
        p1 = (float(x[-1]), float(y[-1]))
        t0 = kb._einheit(float(x[1] - x[0]), float(y[1] - y[0]))
        punkte = self.st.punkte
        laenge = 0.0
        # Hängt der Lauf an den vorigen an? Kurzer Weg, und der Weg ist frei (die Spirale).
        angehaengt = False
        if self.unten and self.ort is not None:
            weg = math.hypot(p0[0] - self.ort[0], p0[1] - self.ort[1])
            if weg <= 2.0 * w.zeilenabstand + self.schritt and weg > _WINZIG:
                anzahl = max(2, int(math.ceil(weg / self.schritt)) + 1)
                qx = np.linspace(self.ort[0], p0[0], anzahl)
                qy = np.linspace(self.ort[1], p0[1], anzahl)
                if self.frei(qx, qy) or weg <= w.zeilenabstand + self.schritt:
                    punkt = bn.Punkt(False, p0[0], p0[1], self.lage)
                    laenge += bn.weg(punkte[-1], punkt)
                    punkte.append(punkt)
                    angehaengt = True
            elif weg <= _WINZIG:
                angehaengt = True
            if angehaengt:
                self.st.anschluesse += 1
        ein = (
            None
            if angehaengt
            else kb._anfahrt(p0, t0, self.r_ein, self.gerade, self.frei, True, self.frei_rechts)
        )
        seitlich = None if angehaengt or ein is not None else self._seitlich(p0, t0)
        if not angehaengt and ein is None and seitlich is None and ganz and not self.gedreht:
            # Ein ganzer Ring, an dessen Anfang kein Eingang passt: anderswo anfangen, wo einer
            # passt – der Spitze am nächsten (die Zwickel neben einer Insel, P-2026-10-01-26).
            m = self._eingang_irgendwo(proben, stellen)
            if m is not None:
                grund = np.asarray(stellen[:-1])
                gedreht = np.concatenate([np.roll(grund, -m), grund[m : m + 1]])
                self.gedreht = True
                try:
                    return self._lauf(ring, gedreht, hinten, True)
                finally:
                    self.gedreht = False
        if not angehaengt and ein is None and seitlich is None and not ganz and self.verschieben:
            # Kein Eingang am Anfang (dahinter die Insel, daneben noch Material): weiter vorn
            # suchen – das Anfangsstück kommt nach den Ringen um die Insel nach.
            m = self._eingang_voraus(proben, stellen)
            if m is not None:
                self.reste.append((ring, stellen[: m + 1]))
                self.st.nachgeholt += 1
                return self._lauf(ring, stellen[m:], hinten, False)
        if not angehaengt:
            # Senkrecht hinauf (knapp über das Rohteil), hin, hinab bis knapp über die Lage.
            start = ein.aussen if ein is not None else (seitlich if seitlich is not None else p0)
            hoch = self.knapp if self.unten else w.sicher
            if self.unten and self.ort is not None:
                punkte.append(bn.Punkt(True, self.ort[0], self.ort[1], hoch))
            punkte.append(bn.Punkt(True, start[0], start[1], hoch))
            if ein is not None:
                # Eintauchen im Freien oder in der Luft, dann tangential hinein.
                knapp = self._hinab(start, hoch)
                punkte.append(bn.Punkt(True, start[0], start[1], knapp))
                punkte.append(bn.Punkt(False, start[0], start[1], self.lage, True))
                laenge += kb._anfahrt_punkte(punkte, ein, self.lage, hinein=True)
                self.st.einfahrten += 1
            elif seitlich is not None:
                # Eintauchen im Freien neben der Bahn, dann quer hinein (hinter dem Anfang ist
                # Gesperrtes – etwa die Insel, an der der Ring abriss).
                knapp = self._hinab(start, hoch)
                punkte.append(bn.Punkt(True, start[0], start[1], knapp))
                punkte.append(bn.Punkt(False, start[0], start[1], self.lage, True))
                punkt = bn.Punkt(False, p0[0], p0[1], self.lage)
                laenge += bn.weg(punkte[-1], punkt)
                punkte.append(punkt)
                self.st.seitlich += 1
            else:
                # Im Material: über die Rampe hinab – rundum auf einem ganzen Ring (dann der
                # Ring in der Tiefe, ab dort, wo die Rampe ankam), sonst längs des Laufs hin
                # und her.
                oben_hier = self.vorige
                knapp = min(hoch, self._material_oben(p0) + w.sicherheit)
                punkte.append(bn.Punkt(True, p0[0], p0[1], knapp))
                punkte.append(bn.Punkt(False, p0[0], p0[1], oben_hier, True))
                self.st.rampen += 1
                self.st.rampen_bei.append((getattr(self, "kennung", ""), int(len(stellen))))
                if ganz:
                    laenge += self._rampe_rundum(ring, stellen, oben_hier)
                    return self._fertig(ring, laenge, ein)
                laenge += kb._rampe(punkte, None, x, y, self.lage, oben_hier, w, self.schritt)
        laenge += kb._bahnpunkte(
            punkte, segmente, proben, stellen, self.lage, hinten, w.austritt, r
        )
        self._fertig(ring, laenge, ein, x, y, p1)

    def _hinab(self, start, hoch):
        """Bis wohin der Eilgang über `start` hinab darf: knapp über die Lage, wenn unter der
        Stirn nichts mehr steht – sonst nur knapp über das Material (ein wenig ungeschnittenes
        Rohteil darf die Stirn beim Einfahren treffen, aber im Vorschub, nicht im Eilgang; der
        Prüfstand fand 189 mm³ im Eilgang, P-2026-10-01-26)."""
        knapp = min(hoch, self.lage + self.w.sicherheit)
        # Mit einer Zelle Zugabe rundum (das Raster rundet auf Knoten): Streift die Stirn das
        # Rohteil nur am Rand, zählt die Simulation die Randzelle mit (1 mm³ am Absatz,
        # P-2026-10-01-49).
        d = self.schritt
        xs = [start[0], start[0] + d, start[0] - d, start[0], start[0]]
        ys = [start[1], start[1], start[1], start[1] + d, start[1] - d]
        if float(np.max(self.feld.ungeschnitten(xs, ys))) <= 0.0:
            return knapp
        if self.stand_hoehe is not None:  # mit Materialstand: über dem Material unter der Stirn
            oben = self.feld.hoechstes(self.stand_hoehe, start[0], start[1], self.lage)
            return min(hoch, max(knapp, oben + self.w.sicherheit))
        return min(hoch, max(knapp, self._material_oben() + self.w.sicherheit))

    def _material_oben(self, ort=None):
        """Bis wohin das Material über der Spitze reichen kann: die vorige Lage – über der
        ersten Lage die Decke (das Rohteil, auch wenn die Fläche in einer Tasche tiefer
        beginnt). Mit Materialstand auch, was unter der Stirn über `ort` höher steht (ein Rest
        am Gesperrten, den die Lagen nicht nehmen)."""
        oben = self.vorige if self.vorige < self.oben - GLEICH else self.decke
        if self.stand_hoehe is not None and ort is not None:
            oben = max(oben, self.feld.hoechstes(self.stand_hoehe, ort[0], ort[1], self.lage))
        return oben

    def _fertig(self, ring, laenge, ein, x=None, y=None, ende=None):
        """Nach dem Lauf: das Freie merken, wo die Spitze steht, die Zähler."""
        if x is None:
            x, y = ring.proben.x, ring.proben.y
        self.feld.merke(x, y)
        if ein is not None:
            self.feld.merke(
                [ein.aussen[0], ein.bogen_punkt[0]], [ein.aussen[1], ein.bogen_punkt[1]]
            )
        letzter = self.st.punkte[-1]
        self.unten = True
        self.ort = ende if ende is not None else (float(letzter.x), float(letzter.y))
        self.st.laenge += laenge
        self.st.laeufe += 1
        self.st.z_min = min(self.st.z_min, self.lage)

    def _eingang_voraus(self, proben, stellen):
        """Die erste Stelle (Index in `stellen`, ab 1) innerhalb von 3 R, an der ein Eingang
        passt – tangential oder quer; None, wenn keine."""
        x, y = proben.x[stellen], proben.y[stellen]
        weg = 0.0
        for m in range(1, len(stellen) - 1):
            weg += math.hypot(float(x[m] - x[m - 1]), float(y[m] - y[m - 1]))
            if weg > 3.0 * self.r:
                return None
            p = (float(x[m]), float(y[m]))
            t = kb._einheit(float(x[m + 1] - x[m]), float(y[m + 1] - y[m]))
            if (
                kb._anfahrt(p, t, self.r_ein, self.gerade, self.frei, True, self.frei_rechts)
                is not None
            ):
                return m
            if self._seitlich(p, t) is not None:
                return m
        return None

    def _eingang_irgendwo(self, proben, stellen):
        """Die Stelle (Index in `stellen`) auf einem ganzen Ring, an der ein Eingang passt –
        tangential oder quer –, der Spitze am nächsten; None, wenn nirgends."""
        grund = np.asarray(stellen[:-1])
        n = len(grund)
        if n < 3:
            return None
        x, y = proben.x[grund], proben.y[grund]
        if self.ort is None:
            reihenfolge = range(n)
        else:
            reihenfolge = np.argsort(np.hypot(x - self.ort[0], y - self.ort[1]))
        schrittweite = max(1, int(round(1.0 / self.schritt)))  # alle 1 mm nachsehen
        for m in reihenfolge:
            m = int(m)
            if m % schrittweite:
                continue
            p = (float(x[m]), float(y[m]))
            k = (m + 1) % n
            t = kb._einheit(float(x[k] - x[m]), float(y[k] - y[m]))
            if kb._anfahrt(p, t, self.r_ein, self.gerade, self.frei, True, self.frei_rechts):
                return m
            if self._seitlich(p, t) is not None:
                return m
        return None

    def reste_fahren(self):
        """Die liegen gebliebenen Anfangsstücke – jetzt ist rundum geschnitten."""
        self.verschieben = False
        reste, self.reste = self.reste, []
        for ring, stellen in reste:
            if len(stellen) >= 2:
                self._lauf(ring, stellen, False, False)

    def _seitlich(self, p0, t0):
        """Der Punkt neben dem Anfang auf der freien Seite (links im Gleichlauf, rechts im
        Gegenlauf), von dem aus der Fräser quer in die Bahn fährt: so weit wie möglich bis
        R + ae, mindestens ae, und der Weg frei."""
        rechts = (t0[1], -t0[0]) if self.frei_rechts else (-t0[1], t0[0])
        for weite in (self.r + self.w.zeilenabstand, self.r, self.r / 2, self.w.zeilenabstand):
            if weite <= _WINZIG:
                continue
            anzahl = max(2, int(math.ceil(weite / self.schritt)) + 1)
            qx = p0[0] + rechts[0] * np.linspace(weite, 0.0, anzahl)
            qy = p0[1] + rechts[1] * np.linspace(weite, 0.0, anzahl)
            if self.frei(qx, qy):
                return (float(qx[0]), float(qy[0]))
        return None

    def _rampe_rundum(self, ring, stellen, oben_hier):
        """Die Rampe rundum auf einem geschlossenen Ring: mit dem Eintauchwinkel längs des
        Rings hinab, so viele Umläufe, wie es braucht, dann der ganze Ring in der Tiefe von
        dort aus. Gibt die Länge zurück."""
        w = self.w
        proben, segmente = ring.proben, ring.segmente
        n = len(proben.x)
        folge = stellen[:-1]  # ohne den Schlusspunkt (= Anfang)
        steil = math.tan(
            math.radians(w.eintauchwinkel if w.eintauchwinkel > 0 else vb.EINTAUCHWINKEL)
        )
        punkte = self.st.punkte
        laenge = 0.0
        hoehe = oben_hier
        seit = 0.0  # Weg seit dem letzten Satz
        letzte_seg = None
        k = 0
        for _ in range(100000):
            i, j = int(folge[k % len(folge)]), int(folge[(k + 1) % len(folge)])
            weg = math.hypot(proben.x[j] - proben.x[i], proben.y[j] - proben.y[i])
            hoehe -= steil * weg
            seit += weg
            k += 1
            unten = hoehe <= self.lage + GLEICH
            seg = int(proben.segment[j])
            if unten or seg != letzte_seg or seit >= 3.0:
                punkt = bn.Punkt(
                    False, float(proben.x[j]), float(proben.y[j]), max(hoehe, self.lage)
                )
                laenge += bn.weg(punkte[-1], punkt)
                punkte.append(punkt)
                seit = 0.0
                letzte_seg = seg
            if unten:
                break
        # Der ganze Ring in der Tiefe, ab der Stelle, wo die Rampe ankam.
        start = int(folge[k % len(folge)])
        rundum = (np.arange(start, start + n + 1)) % n
        laenge += kb._bahnpunkte(
            punkte, segmente, proben, rundum, self.lage, False, w.austritt, self.r
        )
        return laenge

    def heben(self):
        """Am Ende der Lage: tangential heraus, wo es geht, und hinauf."""
        punkte = self.st.punkte
        if not self.unten or not punkte:
            return
        letzter = punkte[-1]
        punkte.append(bn.Punkt(True, letzter.x, letzter.y, self.w.sicher))
        self.unten = False
        self.ort = None


# --- planen ------------------------------------------------------------------------------------


def planen(netz, werte, ebenen, konturen=(), schritt=SCHRITT, stand=None):
    """Die Bahn „Räumen“ (Raeumbahn) über die Flächen `ebenen` ([hoehenfeld.Ebene]) mit den
    Werten `werte`; `netz` ist das Teil ohne diese Flächen (hoehenfeld.netz_ohne – oder je
    Fläche das ohne die Flächen ihrer Höhe, hoehenfeld.netze_je_hoehe); `konturen`
    ([kontur_bahn.Kontur]) die Unterkanten der Wände des Teils – eine geschlossene um die
    Fläche mit der freien Seite innen macht sie zur Tasche. `stand`: der Materialstand vor dem
    Räumen (materialstand, W-012) – was die Operationen davor weggenommen haben, fräst es nicht
    noch einmal, und die Bahn sagt, was noch zu tun ist. ValueError mit einem Satz, wenn es
    nicht geht."""
    w = werte
    form = w.form
    r = float(form.radius)
    if r <= 0 or vp.ebener_radius(form) <= 0:
        raise ValueError(tr("ra.fehler.form"))
    if w.zustellung <= 0 or w.zeilenabstand <= 0:
        raise ValueError(tr("ra.fehler.werte"))
    if w.zeilenabstand > r + GLEICH:
        raise ValueError(tr("ra.fehler.zeilenabstand"))
    if not ebenen:
        raise ValueError(tr("ra.fehler.keine_ebene"))
    if w.variante == RINGE:
        varianten = VARIANTEN
    else:
        varianten = (w.variante,) if w.variante in ALLE_VARIANTEN else ALLE_VARIANTEN
    taschen = {id(e): _tasche_um(e, konturen) for e in ebenen}
    if all(taschen[id(e)] is not None for e in ebenen) and w.variante != "adaptiv":
        # Nur Taschen: Die Ringe haben dort eine Art, von innen nach außen.
        ringe = w.variante == RINGE or w.variante in VARIANTEN
        varianten = ("inseln",) if ringe else ("inseln", "adaptiv")
    huellen = {}  # je Fläche die Hüllfläche im Raster – für jede Variante dieselbe
    # Die Reihenfolge (Spezifikation Strategien 13.5, T1; Manuels Testteil): die offenen Flächen
    # von unten nach oben – jede Stelle wird einmal gefräst, gleich auf ihre Tiefe, statt Höhe
    # für Höhe über alles hinweg, was darunter noch kommt –, danach die Taschen von oben nach
    # unten (jede beginnt, wo die Fläche um sie schon geräumt ist).
    folge = sorted((e for e in ebenen if taschen[id(e)] is None), key=lambda e: e.z)
    folge += sorted((e for e in ebenen if taschen[id(e)] is not None), key=lambda e: -e.z)
    ergebnisse = {}
    davor = []  # wer vorher an den Flächen weggenommen hat (für den Satz, wenn nichts zu tun ist)
    for variante in varianten:
        st = _Stand()
        # Mehrere Flächen: Jede sieht, was die davor in dieser Bahn schon weggenommen haben.
        material = _Material(w, stand) if len(folge) > 1 else None
        eigen = False  # der Morph oder der Adaptiv-Kern hat an einer Fläche gepasst
        for ebene in folge:
            tasche = taschen[id(ebene)]
            teil = _Stand()
            lauf = (hf.netz_fuer(netz, ebene), w, ebene, tasche, konturen)
            try:
                _flaeche(teil, *lauf, variante, r, schritt, stand, material, huellen)
                eigen |= variante == "adaptiv" or (variante == "morph" and tasche is None)
            except (_KeinMorph, _KeinAdaptiv):
                # Passt nicht zu dieser Fläche: für sie die Ringe vom Rohteil her (in der Tasche
                # die von innen nach außen).
                teil = _Stand()
                _flaeche(teil, *lauf, "rohteil", r, schritt, stand, material, huellen)
            st.dazu(teil)
            if material is not None and teil.punkte:
                material.fahre(teil.punkte)
        if variante in ("morph", "adaptiv") and not eigen:
            if len(varianten) > 1:
                continue  # passt nirgends: die anderen Varianten entscheiden
            variante = "rohteil"  # vorgegeben, passt aber nicht: es waren die Ringe vom Rohteil
        davor = st.davor
        if st.flaechen == 0:
            continue
        zeit = bn.zeit(st.punkte, w.vorschub if w.vorschub > 0 else 1000.0, w.eintauchen or None)
        ergebnisse[variante] = (st, zeit)
    if not ergebnisse:
        if davor:
            from . import materialstand as mst  # erst hier: es bringt den Job mit

            raise mst.schon_weg(davor)
        raise ValueError(tr("ra.fehler.nichts"))
    # Die schnellste gewinnt – aber nur, wenn sie die Last hält (Manuel, 2026-10-02, Frage 6:
    # „das was schneller ist ... gewinnt .. wenn man volle Tiefe fräst muss der ae schon in
    # einem Rahmen bleiben“). Nachgemessen wird der Reihe nach (last), bis eine hält – auch
    # „adaptiv“: In einer Nut, kaum breiter als der Fräser, bleibt dem Kern kein Platz, und er
    # fährt in voller Breite durch. Hält keine, gewinnt die mit der kleinsten Last, und die Bahn
    # sagt es (`haelt`). Ohne den Adaptiv-Kern (oder mit einer Vorgabe) bleibt es bei der Zeit.
    reihe = sorted(ergebnisse, key=lambda v: ergebnisse[v][1])
    variante = reihe[0]
    ueberlastet = {}
    haelt = True
    if "adaptiv" in ergebnisse:
        for variante in reihe:
            groesste, lang = last(ergebnisse[variante][0], w, stand)
            if groesste <= bn.LAST_KURZ * LAST_SPIEL and lang <= 2.0 * r:
                break
            ueberlastet[variante] = groesste
        else:
            variante = min(ueberlastet, key=ueberlastet.get)
            haelt = False
    st, zeit = ergebnisse[variante]
    return Raeumbahn(
        st.punkte,
        st.flaechen,
        st.lagen,
        st.ringe,
        st.laeufe,
        st.z_min if math.isfinite(st.z_min) else 0.0,
        st.laenge,
        zeit,
        variante,
        {v: z for v, (_s, z) in ergebnisse.items()},
        st.rampen,
        st.einfahrten + st.seitlich,
        st.anschluesse,
        st.rampen_bei,
        st.nachgeholt,
        st.noch,
        st.weg,
        st.davor,
        st.ausgelassen,
        ueberlastet,
        st.tiefen,
        haelt,
        st.breit,
    )


def kontur_flaeche(kontur):
    """Das Gesicht (Part.Face) einer geschlossenen Kontur, auf z = 0 gelegt – None, wenn OCC
    keins daraus macht."""
    import FreeCAD
    import Part

    if not kontur.geschlossen:
        return None
    try:
        draht = kontur.draht.copy()
        draht.translate(FreeCAD.Vector(0, 0, -kontur.z_unten))
        return Part.Face(draht)
    except Exception:  # OCC: kein Gesicht aus dem Draht
        return None


def innerhalb(flaeche, x, y):
    """Liegt (x, y) im Gesicht (bei z = 0)?"""
    import FreeCAD

    return bool(flaeche.isInside(FreeCAD.Vector(x, y, 0.0), 1e-6, True))


def ist_tasche(kontur, flaeche):
    """Liegt die freie Seite der Kontur innen – eine Tasche, keine Insel?"""
    return innerhalb(
        flaeche,
        kontur.stelle[0] + kontur.normale[0] * 0.01,
        kontur.stelle[1] + kontur.normale[1] * 0.01,
    )


def taschenboeden(form, waende):
    """Die Namen der Böden der Taschen, deren Wände `waende` („Face6“ …) sind: je geschlossener
    Kontur mit der freien Seite innen die ebene Fläche nach oben auf ihrer Unterkante."""
    if not waende:
        return []
    try:
        konturen = kb.konturen(form, list(waende))
    except ValueError:
        return []
    ebenen = hf.ebenen_oben(form)
    ergebnis = []
    for k in konturen:
        flaeche = kontur_flaeche(k)
        if flaeche is None or not ist_tasche(k, flaeche):
            continue
        for e in ebenen:
            if abs(e.z - k.z_unten) > kb.NAH or e.name in ergebnis:
                continue
            if innerhalb(flaeche, (e.x_von + e.x_bis) / 2, (e.y_von + e.y_bis) / 2):
                ergebnis.append(e.name)
    return ergebnis


def _tasche_um(ebene, konturen):
    """Die geschlossene Kontur um die Fläche mit der freien Seite innen – die Tasche; None."""
    mitte = ((ebene.x_von + ebene.x_bis) / 2, (ebene.y_von + ebene.y_bis) / 2)
    beste = None
    for k in konturen:
        if not k.geschlossen or abs(k.z_unten - ebene.z) > kb.NAH:
            continue
        flaeche = kontur_flaeche(k)
        if flaeche is None or not ist_tasche(k, flaeche):
            continue  # die freie Seite liegt außen: eine Insel
        if not innerhalb(flaeche, mitte[0], mitte[1]):
            continue
        if beste is None or flaeche.Area < beste[1]:
            beste = (k, flaeche.Area)
    return beste[0] if beste else None


def _flaeche(
    st, netz, w, ebene, tasche, konturen, variante, r, schritt, stand=None, material=None,
    huellen=None,
):  # fmt: skip
    """Eine Fläche räumen – alle Lagen, in der Variante. `tasche`: die Kontur um sie, wenn sie
    der Boden einer Tasche ist (_tasche_um). Mit Materialstand nur, was über ihr noch steht:
    `stand` ist der vor der Operation (materialstand), `material` der in dieser Bahn – was die
    Flächen davor schon weggenommen haben (_Material). `huellen`: {Fläche: Hüllfläche im Raster}
    – jede Variante rechnet auf derselben, sie wird nur einmal gerechnet (an Manuels Testteil
    0,8 s je Fläche und Variante)."""
    if tasche is not None and variante != "adaptiv":
        # In der Tasche gibt es von den Ringen nur die von innen nach außen – in jeder Variante,
        # damit alle dieselbe Arbeit tun (sonst „gewann“ eine, die die Tasche ausließ;
        # P-2026-10-01-26).
        variante = "inseln"
    ziel = ebene.z + max(w.aufmass_boden, 0.0)
    # Die Lagen beginnen am Rohteil – ob eine andere Operation es über der Fläche schon
    # weggefräst hat, weiß die Bahn nur aus dem Materialstand (P-2026-10-01-26); mit ihm am
    # höchsten Material, das der Fräser erreicht: in einer Tasche, um die diese Bahn schon
    # geräumt hat, an der Oberkante ihrer Wände.
    oben = w.oben
    if oben <= ziel + GLEICH:
        return
    zustellung = w.zustellung
    if w.schneidenlaenge > 0:
        zustellung = min(zustellung, w.schneidenlaenge)
    x_von, x_bis, y_von, y_bis = w.rohteil
    rand = 3.0 * r + w.zeilenabstand
    if tasche is not None:
        bb = tasche.draht.BoundBox
        x_von, x_bis = max(x_von, bb.XMin - rand), min(x_bis, bb.XMax + rand)
        y_von, y_bis = max(y_von, bb.YMin - rand), min(y_bis, bb.YMax + rand)
    toleranz = netz.toleranz
    zugabe = max(w.aufmass, 0.0) + toleranz + vb.RAND  # mit_aufmass: das Ergebnis heben
    geformt = form_mit_aufmass(w.form, max(w.aufmass, 0.0) + toleranz)
    feld = _Feld(
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
        w.zeilenabstand + schritt,
        None if huellen is None else huellen.get(ebene.name),
    )
    if huellen is not None:
        huellen[ebene.name] = feld.roh
    if tasche is not None:
        # Die Tasche endet an ihren Wänden: Liegt das Teil daneben tiefer als ihr Boden (eine
        # Tasche in einer Insel), dürfte die Spitze sonst auch dorthin – an Manuels Testteil
        # räumte der Boden der kleinen Tasche rund um die Insel, 10 min und 29 Rampen statt
        # 15 s (P-2026-10-02-78).
        feld.nur = _im_vieleck(feld.xs, feld.ys, *kb._kette(tasche, toleranz, schritt))
    hoehe = naechste = None
    decke = w.oben
    if stand is not None or material is not None:
        hoehe, naechste, oben, decke = _mit_stand(st, feld, stand, material, oben, ziel, zugabe, w)
        if oben <= ziel + MATERIAL:
            # Über der Fläche steht nichts mehr, was der Fräser hier wegnehmen kann – steht in
            # der Tasche noch etwas, passt er nicht hinein.
            if tasche is not None and _steht_in_der_tasche(feld, naechste, ziel):
                st.ausgelassen.append(ebene.name)
            return
        if hoehe is not None and variante == "morph":
            raise _KeinMorph()  # der Morph fährt ganze Ringe – auch durch Weggefrästes
    anzahl_lagen = max(1, int(math.ceil((oben - ziel - hf.LAGEN_SPIEL) / zustellung)))
    lagen = oben - (oben - ziel) * np.arange(1, anzahl_lagen + 1) / anzahl_lagen
    r_ein = w.einfahrradius if w.einfahrradius and w.einfahrradius > 0 else kb.EINFAHRT_ANTEIL * r
    gerade = kb.GERADE_ANTEIL * r
    material_links = not w.gleichlauf  # Gleichlauf (M3): das Material rechts
    genaue = inselringe(konturen, ebene, w, r, schritt, toleranz, material_links)
    vorige = oben
    gefahren = False
    w_flaeche = w
    for lage in lagen:
        lage = float(lage)
        erlaubt = feld.erlaubt_feld(lage, ziel)
        if hoehe is not None and not feld.material_setzen(hoehe, naechste, lage, erlaubt):
            vorige = lage  # über der Lage nichts, was der Fräser hier wegnehmen kann
            continue
        feld.frei[:] = False
        # Eine dünne Lage nimmt der Fräser breit, mit ae = R und dem Vorschub, bei dem der Span
        # so dick bleibt (bahn.DUENN): An Manuels Testteil ist der Millimeter über der oberen
        # Stufe in der Hälfte der Zeit weg.
        w, w_lage, anteil = w_flaeche, w_flaeche, 1.0
        if vorige - lage <= bn.DUENN * 2.0 * r + GLEICH and w.zeilenabstand < r - GLEICH:
            w_lage = dataclasses.replace(w, zeilenabstand=r)
            anteil = bn.spanausgleich(w.zeilenabstand, 2.0 * r) / bn.spanausgleich(r, 2.0 * r)
            st.breit[round(lage, 4)] = r
        w = w_lage
        beginn = len(st.punkte)
        ablauf = _Lage(st, feld, w, r, r_ein, gerade, lage, vorige, erlaubt, schritt, oben, decke)
        ablauf.stand_hoehe = hoehe
        gesperrt = ~erlaubt
        # Zur sicheren Seite: das Gesperrte um eine Zelle breiter – auch diagonal, sonst
        # berührt der Ring am Niveau 0 an runden Wänden einen gesperrten Knoten und reißt ab.
        breiter = gesperrt.copy()
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di or dj:
                    breiter |= np.roll(np.roll(gesperrt, di, 0), dj, 1)
        gesperrt = breiter
        D = feld.abstand_zu(
            gesperrt & feld.im_raster(*np.meshgrid(feld.xs, feld.ys, indexing="ij"))
        )
        ringe_vorher = st.ringe
        st.tiefen[round(lage, 4)] = max(st.tiefen.get(round(lage, 4), 0.0), vorige - lage)
        if tasche is None and variante == "inseln" and not np.isfinite(D).any():
            variante = "rohteil"  # keine Insel: nur die Ringe vom Rohteil her
        if variante == "adaptiv":
            # Der Kern räumt bis auf einen Rand vor dem Gesperrten, den nimmt der Ring an der Wand.
            _ringe_adaptiv(ablauf, feld, w, r, D, schritt)
            ablauf.einschwenken = True
            _ringe_um_inseln(ablauf, feld, w, D, material_links, schritt, toleranz, True, genaue)
        elif tasche is None and variante == "rohteil":
            _ringe_vom_rohteil(ablauf, feld, w, r, D, material_links, schritt, toleranz)
            _ringe_um_inseln(ablauf, feld, w, D, material_links, schritt, toleranz, True, genaue)
        elif tasche is None and variante == "morph":
            _ringe_morph(ablauf, feld, w, r, D, material_links, schritt, toleranz, genaue)
            _ringe_um_inseln(ablauf, feld, w, D, material_links, schritt, toleranz, True, genaue)
        else:
            _ringe_um_inseln(ablauf, feld, w, D, material_links, schritt, toleranz, False, genaue)
        ablauf.reste_fahren()
        ablauf.heben()
        if anteil < 1.0:
            st.punkte[beginn:] = [
                p if p.eilgang else dataclasses.replace(p, anteil=p.anteil * anteil)
                for p in st.punkte[beginn:]
            ]
        w = w_flaeche
        if hoehe is not None:
            hoehe[feld.frei] = np.minimum(hoehe[feld.frei], lage)
        if st.ringe > ringe_vorher:
            st.lagen += 1
            gefahren = True
        vorige = lage
    feld.ganzes_rohteil()
    if gefahren:
        st.flaechen += 1
    elif tasche is not None and _steht_in_der_tasche(feld, naechste, ziel):
        st.ausgelassen.append(ebene.name)  # Material, aber kein Ring: der Fräser passt nicht


def _steht_in_der_tasche(feld, naechste, ziel):
    """Steht in der Tasche (feld.nur) über ihrem Boden noch Material – abseits der Wände (zwei
    Zellen: dort sieht das Raster die Wand selbst und das Aufmaß an ihr)? `naechste`: die Höhen
    des Materialstands je Knoten; None: Das Rohteil steht noch ganz."""
    innen = feld.nur & ~feld.aufweiten(~feld.nur, 2.0 * feld.schritt)
    if naechste is not None:
        innen = innen & (naechste > ziel + MATERIAL)
    return innen.sum() * feld.schritt * feld.schritt >= MINDESTFLAECHE


class _Material:
    """Der Materialstand in der Bahn selbst (Spezifikation Strategien 13.5, T1): das Rohteil –
    oder der Stand vor der Operation (`stand`, W-012) –, abgetragen um die Flächen, die diese
    Bahn schon geräumt hat. So fräst jede Fläche nur, was über ihr noch steht: An Manuels
    Testteil räumt erst die Platte außen um die Insel, 23 tief; die Insel oben danach nur noch
    über sich, nicht noch einmal über allem."""

    def __init__(self, w, stand):
        from . import materialstand as mst  # erst hier: es bringt den Job mit
        from . import restmaterial as rm

        if stand is not None:
            self.stand = mst._kopie(stand)
        else:
            x_von, x_bis, y_von, y_bis = w.rohteil
            quader = rm.Quader(x_von, x_bis, y_von, y_bis, w.oben - 1.0, w.oben, mst.SCHRITT)
            self.stand = mst.Materialstand(quader, quader.h.copy())
        self._fraeser = mst._grosszuegig(w.form)
        self._fahre = mst._fahre_punkte

    def fahre(self, punkte):
        """Die Bahn einer Fläche ([bahn.Punkt]) nimmt weg, was sie trifft."""
        self._fahre(self.stand.quader, punkte, self._fraeser)

    def hoehen_an(self, xs, ys, naechste=False):
        """Wie materialstand.Materialstand.hoehen_an."""
        return self.stand.hoehen_an(xs, ys, naechste)


def _mit_stand(st, feld, stand, material, oben, ziel, zugabe, w):
    """Der Materialstand über der Fläche: (Höhen je Knoten, die der nächsten Zelle, wo die
    Lagen beginnen, Decke für den Eilgang) – die Höhen None, wenn über allen Lagen überall noch
    das ganze Rohteil steht (dann wie ohne). Die Höhen kommen aus `material` (was diese Bahn
    schon weggenommen hat, _Material), sonst aus `stand` (vor der Operation, W-012). Mit `stand`
    zählt es dazu, was über der Fläche noch steht und was die Operationen davor dort schon
    weggenommen haben: dort, wohin die Stirn auf ihr kommt."""
    rohteil = feld.rohteil_zellen
    quelle = material if material is not None else stand
    hoehe = np.where(rohteil, quelle.hoehen_an(feld.xs, feld.ys), -np.inf)
    naechste = np.where(rohteil, quelle.hoehen_an(feld.xs, feld.ys, naechste=True), -np.inf)
    if stand is not None:
        bereich = rohteil & feld.aufweiten(feld.erlaubt_feld(ziel, ziel), feld.r)
        maske = stand.maske_aus(feld.xs, feld.ys, bereich)
        noch, weg = stand.volumen(maske, ziel)
        st.noch += noch
        st.weg += weg
        st.davor += [name for name in stand.wer(maske) if name not in st.davor]
    if not (rohteil & (hoehe < oben - GLEICH)).any():
        return None, None, oben, w.oben
    # Die Lagen beginnen am höchsten Material, das der Fräser erreicht: je Knoten, wie tief die
    # Spitze dort darf, das Tiefste ringsum (ein Quadrat statt der Stirn – lieber eine Lage zu
    # viel, die ausfällt, als Material, das stehen bleibt; auch was nur der Rand der Stirn trifft,
    # wie ein Rest an einer Wand).
    spitze = np.where(feld.roh <= ziel + GLEICH, ziel, feld.roh + zugabe)
    if feld.nur is not None:
        spitze = np.where(feld.nur, spitze, np.inf)  # in der Tasche: nur in ihrer Kontur
    tief = _kleinstes_um(spitze, int(max(feld.r - feld.schritt - 0.01, 0.0) / feld.schritt))
    erreicht = rohteil & (naechste > np.maximum(tief, ziel) + MATERIAL)
    if not erreicht.any():
        return hoehe, naechste, ziel, w.oben
    endlich = rohteil & np.isfinite(hoehe)
    decke = min(w.oben, float(hoehe[endlich].max()))
    return hoehe, naechste, min(oben, float(naechste[erreicht].max())), decke


def _kleinstes_um(werte, k):
    """(nx, ny): je Knoten das Kleinste im Quadrat (2k + 1)² um ihn – am Rand, was im Raster
    liegt (je Achse ein gleitendes Minimum)."""
    ergebnis = werte.copy()
    for achse in (0, 1):
        quelle = ergebnis.copy()
        n = quelle.shape[achse]
        for d in range(1, min(k, n - 1) + 1):
            vorn = [slice(None), slice(None)]
            hinten = [slice(None), slice(None)]
            vorn[achse], hinten[achse] = slice(d, None), slice(None, -d)
            vorn, hinten = tuple(vorn), tuple(hinten)
            np.minimum(ergebnis[vorn], quelle[hinten], out=ergebnis[vorn])
            np.minimum(ergebnis[hinten], quelle[vorn], out=ergebnis[hinten])
    return ergebnis


def _luecken_zu(drin, ganz, proben, geschlossen, laenge):
    """`drin` (je Probe des Rings: fahren?) mit den Lücken zwischen zwei Stücken gefüllt, die
    höchstens `laenge` (mm) lang sind und ganz in `ganz` liegen (dort führe der Ring ohne
    Materialstand) – beim geschlossenen Ring auch über den Anfang hinweg."""
    n = len(drin)
    if drin.all() or not drin.any():
        return drin
    ergebnis = drin.copy()
    reihe = np.arange(n)
    if geschlossen:
        reihe = np.roll(reihe, -int(np.flatnonzero(drin)[0]))  # beginnt in einem Stück
    werte = drin[reihe]
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
        luecke = reihe[a:k]
        if not ganz[luecke].all():
            continue
        folge = np.concatenate([[reihe[a - 1]], luecke, [reihe[k % n]]])
        if np.sum(np.hypot(np.diff(proben.x[folge]), np.diff(proben.y[folge]))) <= laenge:
            ergebnis[luecke] = True
    return ergebnis


def form_mit_aufmass(form, aufmass):
    """Die Fräserform um das Aufmaß größer – für die Hüllfläche."""
    return form.mit_aufmass(aufmass)


def _naechster_zuerst(ablauf, ringe, eng, kennung, nur=None, luft=False):
    """Fährt die Ringe – immer den, der der Spitze am nächsten liegt, zuerst."""
    while ringe:
        if ablauf.ort is None:
            naechster = 0
        else:
            naechster = min(
                range(len(ringe)),
                key=lambda k: float(
                    np.min(
                        np.hypot(
                            ringe[k].proben.x - ablauf.ort[0], ringe[k].proben.y - ablauf.ort[1]
                        )
                    )
                ),
            )
        ring = ringe.pop(naechster)
        ablauf.ring(
            ring,
            eng=eng,
            kennung=kennung,
            nur=None if nur is None else nur.get(id(ring)),
            luft=luft,
        )


GEODAETISCH_UMLAEUFE = 16  # höchstens so oft hin und zurück über das Raster
_GROSS = 1e7  # trennt die Abschnitte einer Zeile beim gleitenden Minimum
_UNERREICHT = 1e6


def _geodaetisch(start, frei, schritt):
    """(nx, ny) mm: der kürzeste Weg von den Startwerten `start` (inf: kein Start) zu jeder
    Zelle, nur durch freie Zellen (`frei`) – um Gesperrtes herum; inf, wohin kein Weg führt.
    Achteckig gemessen (gerade `schritt`, schräg √2 · `schritt`): höchstens 8 % länger als der
    gerade Weg – Höhenlinien in gleichem Abstand liegen so höchstens so weit auseinander, eher
    enger. Zeilenweise hin und zurück; in der Zeile das gleitende Minimum je Abschnitt zwischen
    Gesperrtem (numpy, ohne Schleife je Zelle); um Inseln herum braucht es mehrere Umläufe."""
    G = np.where(frei, start, np.inf)
    nx, ny = G.shape
    s, sd = float(schritt), float(schritt) * math.sqrt(2.0)
    weg = np.arange(ny) * s
    gesperrt = ~frei
    abschnitt = np.cumsum(gesperrt, axis=1) * _GROSS
    abschnitt_r = np.cumsum(gesperrt[:, ::-1], axis=1) * _GROSS

    def zeile(i):
        g = np.minimum(G[i], _UNERREICHT)
        lauf = np.minimum.accumulate(g - weg - abschnitt[i]) + weg + abschnitt[i]
        g = np.minimum(g, lauf)[::-1]
        lauf = np.minimum.accumulate(g - weg - abschnitt_r[i]) + weg + abschnitt_r[i]
        g = np.minimum(g, lauf)[::-1]
        G[i] = np.where(frei[i] & (g < _UNERREICHT - 1.0), g, np.inf)

    for _ in range(GEODAETISCH_UMLAEUFE):
        vorher = G.copy()
        for reihen in (range(nx), range(nx - 1, -1, -1)):
            vorige = None
            for i in reihen:
                if vorige is not None:
                    p = G[vorige]
                    kandidat = p + s
                    kandidat[1:] = np.minimum(kandidat[1:], p[:-1] + sd)
                    kandidat[:-1] = np.minimum(kandidat[:-1], p[1:] + sd)
                    G[i] = np.where(frei[i], np.minimum(G[i], kandidat), np.inf)
                zeile(i)
                vorige = i
        if np.array_equal(vorher, G):
            break
    return G


def _vielecke(werte, feld, spiegeln=False):
    """Die geschlossenen Höhenlinien des Feldes `werte` beim Niveau 0 als Vielecke [[x, y], …],
    das erste Eck am Ende noch einmal – für den Adaptiv-Kern. `spiegeln`: an der y-Achse
    gespiegelt."""
    vorzeichen = -1.0 if spiegeln else 1.0
    ergebnis = []
    for punkte, geschlossen in _hoehenlinien(werte, feld.xs, feld.ys, 0.0):
        if not geschlossen or len(punkte) < 3:
            continue
        punkte = _vereinfacht(punkte, ADAPTIV_ECKEN, True)
        if len(punkte) < 3:
            continue
        ecken = [[vorzeichen * float(x), float(y)] for x, y in punkte]
        ergebnis.append([*ecken, ecken[0]])
    return ergebnis


def _dicht(ecken, schritt):
    """(x, y) längs des Linienzugs `ecken` (m, 2) – seine Ecken und dazwischen Stellen, höchstens
    `schritt` auseinander."""
    ecken = np.asarray(ecken, dtype=float).reshape(-1, 2)
    if len(ecken) < 2:
        return ecken[:, 0].copy(), ecken[:, 1].copy()
    weg = np.hypot(np.diff(ecken[:, 0]), np.diff(ecken[:, 1]))
    anzahl = np.maximum(1, np.ceil(weg / schritt)).astype(np.int64)
    stueck = np.repeat(np.arange(len(anzahl)), anzahl)
    vorher = np.repeat(np.cumsum(anzahl) - anzahl, anzahl)
    t = (np.arange(len(stueck)) - vorher + 1) / anzahl[stueck]
    x = ecken[stueck, 0] + t * (ecken[stueck + 1, 0] - ecken[stueck, 0])
    y = ecken[stueck, 1] + t * (ecken[stueck + 1, 1] - ecken[stueck, 1])
    return np.concatenate([ecken[:1, 0], x]), np.concatenate([ecken[:1, 1], y])


def _ringe_adaptiv(ablauf, feld, w, r, D, schritt):
    """Die Variante „adaptiv“ auf einer Lage: FreeCADs Adaptiv-Kern (area.Adaptive2d, der Kern
    der CAM-Operation „Adaptive“) räumt, was der Fräser auf der Lage erreicht – in Bahnen, die
    ihren Eingriff halten: von außen durch die Luft hinein, wo es geht (sonst über eine Helix),
    im Material weiter mit höchstens ADAPTIV_SCHRITT · ae, an Wänden entlang ohne quer
    hineinzufahren, zurück unten durchs Freie statt abzuheben. Manuel, 2026-10-02, zu den
    Ringen, die an einer Insel abreißen: „effektiv ist da nur ein Kreis“ – und zur Last: die
    schnellste Variante gewinnt, wenn sie sie hält. An seinem Testteil hob das Räumen mit den
    Ringen 56-mal ab und fuhr an jeder Wand quer in den Streifen (bis 5 ae); so 6-mal, 11 statt
    12,4 min.

    Der Kern bekommt Vielecke aus dem Raster: das Gebiet, in dem die Schneide sein darf – die
    Höhenlinie 0 des Feldes D (der Abstand zum Gesperrten, das dafür schon um eine Zelle breiter
    ist), nach außen R + ae über das Rohteil hinaus –, und das Material (der Rand des Rohteils
    oder dessen, was noch steht). Den schmalen Rand am Gesperrten nimmt danach der Ring an der
    Wand (_ringe_um_inseln), genau gerechnet. Der Kern fräst im Gleichlauf; für Gegenlauf wird gespiegelt. Geprüft wird
    hier nach: Die Mitte bleibt im Erlaubten, eingetaucht wird im Freien – sonst _KeinAdaptiv,
    und die Fläche bekommt Ringe."""
    try:
        import area  # FreeCADs libarea

        kern = area.Adaptive2d()
        innen = area.AdaptiveOperationType.ClearingInside
        schneiden = area.AdaptiveMotionType.Cutting
        durchs_freie = area.AdaptiveMotionType.LinkClear
    except Exception as fehler:  # ein FreeCAD ohne den Kern
        raise _KeinAdaptiv() from fehler
    ae = w.zeilenabstand
    spiegeln = not w.gleichlauf
    # Das Gebiet im Maß der Schneide (der Kern rückt selbst um R nach innen): so weit die Mitte
    # darf, und R dazu.
    gebiet = feld._tiefe_rohteil + (r + ae) + r
    if np.isfinite(D).any():
        gebiet = np.minimum(gebiet, np.where(np.isfinite(D), D, _UNERREICHT) + r)
    grenzen = _vielecke(gebiet, feld, spiegeln)
    material = _vielecke(feld.tiefe, feld, spiegeln)
    if not grenzen or not material:
        raise _KeinAdaptiv()
    kern.stepOverFactor = ADAPTIV_SCHRITT * ae / (2.0 * r)
    kern.toolDiameter = 2.0 * r
    kern.helixRampDiameter = 2.0 * ADAPTIV_HELIX * r
    kern.keepToolDownDistRatio = ADAPTIV_HALTEN
    kern.stockToLeave = 0.0
    kern.tolerance = ADAPTIV_GENAU
    kern.forceInsideOut = False
    kern.finishingProfile = True
    kern.opType = innen
    eingabe = repr((material, grenzen, kern.stepOverFactor, 2.0 * r, kern.helixRampDiameter))
    schluessel = hashlib.blake2b(eingabe.encode("utf-8"), digest_size=16).hexdigest()
    gebiete = _ADAPTIV.get(schluessel)
    if gebiete is None:
        try:
            ergebnisse = kern.Execute(material, grenzen, lambda _wege: False)
        except Exception as fehler:
            raise _KeinAdaptiv() from fehler
        vorzeichen = -1.0 if spiegeln else 1.0
        gebiete = []
        for ergebnis in ergebnisse:
            stuecke = []
            for art, ecken in ergebnis.AdaptivePaths:
                ecken = np.asarray(ecken, dtype=float).reshape(-1, 2)
                if len(ecken):
                    ecken[:, 0] *= vorzeichen
                    stuecke.append((art == schneiden, art == durchs_freie, ecken))
            start = (vorzeichen * float(ergebnis.StartPoint[0]), float(ergebnis.StartPoint[1]))
            mitte = (
                vorzeichen * float(ergebnis.HelixCenterPoint[0]),
                float(ergebnis.HelixCenterPoint[1]),
            )
            gebiete.append((start, mitte, stuecke))
        _ADAPTIV[schluessel] = gebiete
        while len(_ADAPTIV) > ADAPTIV_GEMERKT:
            _ADAPTIV.popitem(last=False)
    else:
        _ADAPTIV.move_to_end(schluessel)
    gefahren = False
    for start, mitte, stuecke in gebiete:
        gefahren |= _adaptiv_gebiet(ablauf, feld, w, r, schritt, start, mitte, stuecke)
    if not gefahren:
        raise _KeinAdaptiv()


def _adaptiv_gebiet(ablauf, feld, w, r, schritt, start, mitte, stuecke):
    """Fährt ein Gebiet des Adaptiv-Kerns: hinein bei `start` – von außen durch die Luft, oder
    über die Helix um `mitte` –, dann seine Stücke [(schneidet, durchs Freie, Ecken (m, 2))]:
    schneiden im Vorschub, durchs Freie unten mit RUECKWEG · Vorschub, sonst abheben. Merkt sich
    das Freie. Gibt zurück, ob etwas gefahren wurde."""
    schnitte = [ecken for schneidet, _frei, ecken in stuecke if schneidet and len(ecken) >= 2]
    if not schnitte:
        return False
    for ecken in schnitte:  # die Mitte bleibt, wo sie darf
        x, y = _dicht(ecken, schritt)
        if not (feld.im_raster(x, y).all() and feld.bei(ablauf.erlaubt, x, y).all()):
            raise _KeinAdaptiv()
    st, lage = ablauf.st, ablauf.lage
    punkte = st.punkte
    erstes = schnitte[0]
    richtung = kb._einheit(float(erstes[1][0] - erstes[0][0]), float(erstes[1][1] - erstes[0][1]))
    hoch = ablauf.knapp if ablauf.unten else w.sicher
    if ablauf.unten and ablauf.ort is not None:
        punkte.append(bn.Punkt(True, ablauf.ort[0], ablauf.ort[1], hoch))
    laenge = 0.0
    radius = math.hypot(start[0] - mitte[0], start[1] - mitte[1])
    if radius > 0.01:
        laenge += _adaptiv_helix(ablauf, feld, w, start, mitte, radius, richtung, hoch, schritt)
        st.rampen += 1
        st.rampen_bei.append(("adaptiv", 0))
    else:
        ein = _adaptiv_einstieg(ablauf, feld, w, r, start, richtung, schritt)
        punkte.append(bn.Punkt(True, ein[0], ein[1], hoch))
        punkte.append(bn.Punkt(True, ein[0], ein[1], ablauf._hinab(ein, hoch)))
        punkte.append(bn.Punkt(False, ein[0], ein[1], lage, True))
        if math.hypot(ein[0] - start[0], ein[1] - start[1]) > _WINZIG:
            punkt = bn.Punkt(False, start[0], start[1], lage)
            laenge += bn.weg(punkte[-1], punkt)
            punkte.append(punkt)
            feld.merke(*_dicht([ein, start], schritt))
        st.einfahrten += 1
    unten = True
    ort = (float(start[0]), float(start[1]))
    for schneidet, frei, ecken in stuecke:
        if not schneidet:
            weg = np.vstack([[ort], ecken])
            if unten and frei and _weg_frei(ablauf, feld, weg, schritt):
                for x, y in ecken:
                    punkte.append(bn.Punkt(False, float(x), float(y), lage, False, None, RUECKWEG))
                st.anschluesse += 1
            elif unten:
                punkte.append(bn.Punkt(True, ort[0], ort[1], ablauf.knapp))
                unten = False
            ort = (float(ecken[-1][0]), float(ecken[-1][1]))
            continue
        if len(ecken) < 2:
            continue
        anfang = (float(ecken[0][0]), float(ecken[0][1]))
        if not unten:
            # Nach dem Abheben hinab am Anfang des Stücks – dort ist nach dem Kern frei.
            if float(feld.ungeschnitten([anfang[0]], [anfang[1]])[0]) > ablauf.schwelle:
                raise _KeinAdaptiv()
            punkte.append(bn.Punkt(True, anfang[0], anfang[1], ablauf.knapp))
            punkte.append(bn.Punkt(True, anfang[0], anfang[1], ablauf._hinab(anfang, ablauf.knapp)))
            punkte.append(bn.Punkt(False, anfang[0], anfang[1], lage, True))
            unten = True
        elif math.hypot(anfang[0] - ort[0], anfang[1] - ort[1]) > _WINZIG:
            punkt = bn.Punkt(False, anfang[0], anfang[1], lage)
            laenge += bn.weg(punkte[-1], punkt)
            punkte.append(punkt)
        for x, y in ecken[1:]:
            punkt = bn.Punkt(False, float(x), float(y), lage)
            laenge += bn.weg(punkte[-1], punkt)
            punkte.append(punkt)
        feld.merke(*_dicht(ecken, schritt))
        ort = (float(ecken[-1][0]), float(ecken[-1][1]))
        st.ringe += 1
    ablauf.unten = unten
    ablauf.ort = ort if unten else None
    st.laenge += laenge
    st.laeufe += 1
    st.z_min = min(st.z_min, lage)
    return True


def _weg_frei(ablauf, feld, ecken, schritt):
    """Liegt der Weg `ecken` (m, 2) ganz im Freien: die Mitte im Erlaubten, unter der Stirn
    kein Rohteil mehr (bis auf das Rauschen des Rasters)?"""
    x, y = _dicht(ecken, schritt)
    if not (feld.im_raster(x, y).all() and feld.bei(ablauf.erlaubt, x, y).all()):
        return False
    return bool(float(np.max(feld.ungeschnitten(x, y))) <= FREI_ZULAESSIG)


def _adaptiv_einstieg(ablauf, feld, w, r, start, richtung, schritt):
    """Wo der Fräser eintaucht, bevor er von außen ins Gebiet fährt. Der Kern beginnt mit dem
    halben Schritt im Material – dort einzutauchen hieße, einen Saum über die ganze Tiefe
    senkrecht zu nehmen. Rückwärts auf der Geraden seines ersten Stücks liegt die Stirn nach
    wenigen Millimetern ganz in der Luft: dort hinab, dann im Vorschub hinein. Geht das nicht
    (dahinter ist gesperrt), bleibt der Start, wenn unter der Stirn nicht mehr steht, als jeder
    Ring beim Einfahren treffen darf; sonst _KeinAdaptiv."""
    d = schritt
    for k in range(int(math.ceil((2.0 * r + w.zeilenabstand) / schritt)) + 1):
        p = (start[0] - richtung[0] * k * schritt, start[1] - richtung[1] * k * schritt)
        if not feld.im_raster([p[0]], [p[1]]).all():
            break
        if not feld.bei(ablauf.erlaubt, [p[0]], [p[1]]).all():
            break
        xs = [p[0], p[0] + d, p[0] - d, p[0], p[0]]
        ys = [p[1], p[1], p[1], p[1] + d, p[1] - d]
        if float(np.max(feld.ungeschnitten(xs, ys))) <= 0.0:
            return p
    if float(feld.ungeschnitten([start[0]], [start[1]])[0]) <= ablauf.schwelle:
        return (float(start[0]), float(start[1]))
    raise _KeinAdaptiv()


def _adaptiv_helix(ablauf, feld, w, start, mitte, radius, richtung, hoch, schritt):
    """Ins Volle über die Helix um `mitte` (der Kern rechnet mit ihr: Danach ist der Kreis mit
    Radius der Helix + R frei): mit dem Eintauchwinkel in ganzen Umläufen hinab, dann ein Umlauf
    in der Tiefe – Bögen mit z, im Drehsinn des ersten Stücks danach. Gibt die Länge zurück."""
    lage, punkte = ablauf.lage, ablauf.st.punkte
    winkel = math.atan2(start[1] - mitte[1], start[0] - mitte[0])
    kreuz = (start[0] - mitte[0]) * richtung[1] - (start[1] - mitte[1]) * richtung[0]
    uhr = kreuz < 0
    rundum = winkel + np.linspace(0.0, 2.0 * math.pi, max(8, int(2 * math.pi * radius / schritt)))
    kx, ky = mitte[0] + radius * np.cos(rundum), mitte[1] + radius * np.sin(rundum)
    if not (feld.im_raster(kx, ky).all() and feld.bei(ablauf.erlaubt, kx, ky).all()):
        raise _KeinAdaptiv()
    oben_hier = ablauf.vorige
    knapp = min(hoch, ablauf._material_oben(start) + w.sicherheit)
    punkte.append(bn.Punkt(True, start[0], start[1], hoch))
    punkte.append(bn.Punkt(True, start[0], start[1], knapp))
    punkte.append(bn.Punkt(False, start[0], start[1], oben_hier, True))
    steil = math.tan(math.radians(w.eintauchwinkel if w.eintauchwinkel > 0 else vb.EINTAUCHWINKEL))
    je_umlauf = 2.0 * math.pi * radius * steil
    umlaeufe = max(1, int(math.ceil((oben_hier - lage) / je_umlauf - 1e-9)))
    laenge = 0.0
    for viertel in range(1, 4 * (umlaeufe + 1) + 1):
        a = winkel + (-1.0 if uhr else 1.0) * 0.5 * math.pi * viertel
        z = max(lage, oben_hier + (lage - oben_hier) * viertel / (4.0 * umlaeufe))
        punkt = bn.Punkt(
            False,
            mitte[0] + radius * math.cos(a),
            mitte[1] + radius * math.sin(a),
            z,
            False,
            (mitte[0], mitte[1], uhr),
        )
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    feld.merke(kx, ky)
    return laenge


def last(st, w, stand=None):
    """(größte Last, längster Weg am Stück über bahn.LAST_DAUERND in mm) der Bahn `st` (eine
    Raeumbahn oder ihr _Stand: `punkte` und `tiefen`) mit den Werten `w` – die
    Last ist der Querschnitt, den der Fräser je mm Weg abträgt, durch ae · Lagentiefe
    (Spezifikation Strategien 12.1), über LAST_FENSTER mm gemittelt. Die Bahn wird dazu im
    Quader des Rohteils abgefahren (oder im Materialstand `stand`); Eintauchen und Rampen
    tragen ab, zählen aber nicht – ihr Eingriff folgt dem Eintauchwinkel. Die Zellen am Rand
    des Rohteils zählen halb: Sein Rand liegt auf ihren Mitten."""
    from . import materialstand as mst  # erst hier: es bringt den Job mit
    from . import restmaterial as rm

    if stand is not None:
        q = mst._kopie(stand).quader
    else:
        x_von, x_bis, y_von, y_bis = w.rohteil
        q = rm.Quader(x_von, x_bis, y_von, y_bis, w.oben - 1.0, w.oben, mst.SCHRITT)
    gewicht = np.ones(q.h.shape)
    gewicht[0, :] *= 0.5
    gewicht[-1, :] *= 0.5
    gewicht[:, 0] *= 0.5
    gewicht[:, -1] *= 0.5
    sx, sy = float(q.x[1] - q.x[0]), float(q.y[1] - q.y[0])
    zelle = sx * sy
    r = float(w.form.radius)
    rand = r + 2.0 * max(sx, sy)
    nx, ny = q.h.shape
    groesste = lang = ueber = 0.0
    fenster = []  # [(Weg, Volumen)] der letzten Stücke, zusammen ≥ LAST_FENSTER
    for von, nach in zip(st.punkte, st.punkte[1:], strict=False):
        sehnen = []
        for a, b in mst.sehnen(von, nach):
            n = max(1, int(math.ceil(math.dist(a[:2], b[:2]) / LAST_SEHNE)))
            for k in range(n):
                sehnen.append(
                    (
                        tuple(a[i] + (b[i] - a[i]) * k / n for i in range(3)),
                        tuple(a[i] + (b[i] - a[i]) * (k + 1) / n for i in range(3)),
                    )
                )
        eben = not nach.eilgang and not nach.eintauchen and abs(nach.z - von.z) <= GLEICH
        tiefe = st.tiefen.get(round(nach.z, 4)) if eben else None
        ae = getattr(st, "breit", {}).get(round(nach.z, 4), w.zeilenabstand)
        if not tiefe or tiefe <= GLEICH:
            q.fahre_stuecke([s[0] for s in sehnen], [s[1] for s in sehnen], w.form)
            fenster, ueber = [], 0.0
            continue
        for a, b in sehnen:
            i0 = max(int(math.floor((min(a[0], b[0]) - rand - q.x[0]) / sx)), 0)
            i1 = min(int(math.ceil((max(a[0], b[0]) + rand - q.x[0]) / sx)) + 1, nx)
            j0 = max(int(math.floor((min(a[1], b[1]) - rand - q.y[0]) / sy)), 0)
            j1 = min(int(math.ceil((max(a[1], b[1]) + rand - q.y[0]) / sy)) + 1, ny)
            if i1 <= i0 or j1 <= j0:
                continue
            vorher = q.h[i0:i1, j0:j1].copy()
            q.fahre_stuecke([a], [b], w.form)
            gesenkt = np.where(np.isfinite(vorher), vorher - q.h[i0:i1, j0:j1], 0.0)
            volumen = float((gesenkt * gewicht[i0:i1, j0:j1]).sum()) * zelle
            fenster.append((math.dist(a[:2], b[:2]), volumen))
            weg = sum(f[0] for f in fenster)
            while len(fenster) > 1 and weg - fenster[0][0] >= LAST_FENSTER:
                weg -= fenster.pop(0)[0]
            if weg < LAST_FENSTER * 0.999:
                continue
            last = sum(f[1] for f in fenster) / weg / (ae * tiefe)
            groesste = max(groesste, last)
            ueber = ueber + fenster[-1][0] if last > bn.LAST_DAUERND else 0.0
            lang = max(lang, ueber)
    return groesste, lang


def _ringe_vom_rohteil(ablauf, feld, w, r, D, material_links, schritt, toleranz):
    """Die Ringe vom Rohteilrand her: die Höhenlinien des Wegs vom Rand – um Inseln und Wände
    herum gemessen (_geodaetisch) – bei m · ae, der erste R − ae außerhalb, in der Luft. Ohne
    Hindernis ist das das Rechteck mit runden Ecken (analytisch, mit Bögen); trifft er eine
    Insel, legt er sich um sie herum: Jeder Ring nimmt überall höchstens ae, auch hinter der
    Insel, und endet an ihr (die Ringe um die Inseln danach, _ringe_um_inseln mit `nur_rest`,
    nehmen den Rest an ihrer Wand). Früher F = min(Tiefe + R, D + ae): Wo die Insel den Ring
    bestimmte, biss er in sie hinein – mit vollem Material beidseits, auf der Platte 120 mm in
    voller Breite, 20 tief (P-2026-10-01-49). Manuel, 2026-10-01: die Ringe sollen am Ende nur
    noch um den Zapfen fahren."""
    ae = w.zeilenabstand
    gitter = np.meshgrid(feld.xs, feld.ys, indexing="ij")
    gueltig = feld.beruehrt & feld.im_raster(*gitter)
    frei = np.isnan(D) | (D >= 0)  # D < 0: im Gesperrten
    if np.isinf(D).all():
        frei = np.ones_like(frei)
    start = np.where(feld.tiefe <= 0.0, feld.tiefe + r, np.inf)
    G = _geodaetisch(start, frei, schritt)
    if not gueltig.any():
        return
    endlich = gueltig & np.isfinite(G)
    if not endlich.any():
        return
    hoechste = float(G[endlich].max())
    if hoechste < ae:
        return
    sperre = ~frei
    for m in range(1, int(math.floor(hoechste / ae + 1e-9)) + 1):
        niveau = m * ae
        jetzt = []
        for punkte, geschlossen in _hoehenlinien(G, feld.xs, feld.ys, niveau, sperre):
            if len(punkte) < 2:
                continue
            laenge = float(np.sum(np.hypot(*np.diff(punkte, axis=0).T)))
            if geschlossen and laenge < 2 * math.pi * ae:
                continue  # winzig: der Ring davor deckt es ab
            i, j = feld.zellen(punkte[:, 0], punkte[:, 1])
            nur_rand = not feld.vom_material and bool(
                (np.abs(G[i, j] - (feld.tiefe[i, j] + r)) <= schritt).all()
            )
            if nur_rand and geschlossen:
                ring = _rohteil_ring(w.rohteil, niveau - r, material_links, schritt)
            else:
                ring = _ring_aus_linie(
                    punkte, geschlossen, material_links, feld, niveau, G, schritt, toleranz,
                    material_hoch=True,
                )  # fmt: skip
            if ring is not None:
                jetzt.append(ring)
        _naechster_zuerst(ablauf, jetzt, False, f"rohteil {m}")


def _abschnitt(r, h):
    """Die Fläche des Kreisabschnitts der Höhe h im Kreis mit dem Radius r."""
    h = min(max(h, 0.0), 2.0 * r)
    return r * r * math.acos((r - h) / r) - (r - h) * math.sqrt(max(2.0 * r * h - h * h, 0.0))


def _bilinear(werte, feld, x, y):
    """Die Werte des Feldes (nx, ny) an den Stellen (x, y), bilinear zwischen den Knoten."""
    fx = np.clip((np.asarray(x, dtype=float) - feld.x0) / feld.schritt, 0.0, feld.nx - 1.000001)
    fy = np.clip((np.asarray(y, dtype=float) - feld.y0) / feld.schritt, 0.0, feld.ny - 1.000001)
    i0, j0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - i0, fy - j0
    return (
        werte[i0, j0] * (1 - tx) * (1 - ty)
        + werte[i0 + 1, j0] * tx * (1 - ty)
        + werte[i0, j0 + 1] * (1 - tx) * ty
        + werte[i0 + 1, j0 + 1] * tx * ty
    )


def _kreuzpunkte(werte, xs, ys, niveau):
    """(x, y) aller Stellen, an denen die Höhenlinie `niveau` des Feldes eine Kante des Rasters
    kreuzt – die Punkte der Linie ohne ihre Reihenfolge (für die Suche nach dem nächsten Ring)."""
    s = float(xs[1] - xs[0])
    a, b = werte[:-1, :] - niveau, werte[1:, :] - niveau
    ii, jj = np.nonzero((a > 0) != (b > 0))
    t = a[ii, jj] / (a[ii, jj] - b[ii, jj])
    x1, y1 = xs[ii] + t * s, ys[jj]
    a, b = werte[:, :-1] - niveau, werte[:, 1:] - niveau
    ii, jj = np.nonzero((a > 0) != (b > 0))
    t = a[ii, jj] / (a[ii, jj] - b[ii, jj])
    x2, y2 = xs[ii], ys[jj] + t * s
    return np.concatenate([x1, x2]), np.concatenate([y1, y2])


def _harmonisch(wert, unbekannt, start, genau=1e-6, hoechstens=None):
    """u mit Δu = 0 auf den Zellen `unbekannt`, u = `wert` auf allen anderen – rot-schwarz-SOR
    (Überrelaxation), ab der Schätzung `start`. Die Höhenlinien einer solchen Funktion sind
    glatt und schneiden sich nie; in einem Ring zwischen zwei Rändern ist jede eine einzige
    geschlossene Linie (keine Sattelpunkte) – die Grundlage des Morphs (Bieterman & Sandstrom,
    „A Curvilinear Tool-Path Method for Pocket Machining“, 2003)."""
    u = np.where(unbekannt, start, wert).astype(float)
    unbekannt = unbekannt.copy()
    unbekannt[0, :] = unbekannt[-1, :] = unbekannt[:, 0] = unbekannt[:, -1] = False
    nx, ny = u.shape
    n = max(nx, ny)
    omega = 2.0 / (1.0 + math.sin(math.pi / n))
    flach = u.ravel()
    ii, jj = np.nonzero(unbekannt)
    stellen = ii * ny + jj
    farben = [stellen[(ii + jj) % 2 == 0], stellen[(ii + jj) % 2 == 1]]
    hoechstens = hoechstens or 8 * n
    for _ in range(hoechstens):
        groesste = 0.0
        for idx in farben:
            if not len(idx):
                continue
            mittel = 0.25 * (flach[idx - ny] + flach[idx + ny] + flach[idx - 1] + flach[idx + 1])
            d = omega * (mittel - flach[idx])
            flach[idx] += d
            groesste = max(groesste, float(np.abs(d).max()))
        if groesste < genau:
            break
    return u


def inselringe(konturen, ebene, w, r, schritt, toleranz, material_links):
    """Die Ringe an den Wänden der Fläche, genau gerechnet: der Versatz ihrer Unterkante um
    Radius + Aufmaß zur freien Seite (kontur_bahn._versatz – mit Bögen, ein Kreis bleibt ein
    Kreis) – um Inseln (das Material innen) und an der Wand einer Tasche (das Material außen).
    Der Ring aus dem Raster läge eine Zelle weiter weg: In einer Nut blieben 0,75 statt 0,3 mm
    (P-2026-10-01-44)."""
    ergebnis = []
    for k in konturen:
        if not k.geschlossen or abs(k.z_unten - ebene.z) > kb.NAH:
            continue
        flaeche = kontur_flaeche(k)
        if flaeche is None:
            continue
        versatz = kb._versatz(k, r + max(w.aufmass, 0.0), toleranz, schritt)
        if versatz is None:
            continue
        segmente, _proben = versatz  # in Fahrtrichtung der Kontur: das Material rechts
        if material_links:
            segmente = [s.umgekehrt() for s in reversed(segmente)]
        tasche = ist_tasche(k, flaeche)
        proben = kb._abtasten(segmente, schritt, True)
        ergebnis.append(_Ring(segmente, proben, True, True, tasche))
    return ergebnis


def _genau(ring, genaue, schritt):
    """Der genaue Ring (inselringe), der auf dem Ring aus dem Raster liegt – sonst dieser. Der
    aus dem Raster liegt um die Zelle, um die das Gesperrte breiter ist, und die Zugabe der
    Hüllfläche weiter außen (bis etwa 2 Zellen); liegt er weiter weg, stört dort etwas anderes
    (eine zweite Insel, ein Überhang) – dann gilt der aus dem Raster."""
    for genauer in genaue:
        gx, gy = genauer.proben.x, genauer.proben.y
        rx, ry = ring.proben.x, ring.proben.y
        if len(gx) < 2 or len(rx) < 2:
            continue
        abstand = np.hypot(gx[:, None] - rx[None, :], gy[:, None] - ry[None, :]).min(axis=1)
        if float(abstand.max()) <= 2.0 * schritt + 0.25:
            return genauer
    return ring


def _bogenlaengen(x, y, geschlossen):
    """Die Bogenlänge bis zu jeder Probe – geschlossen mit dem Stück zurück zum Anfang am Ende."""
    if geschlossen:
        x, y = np.append(x, x[0]), np.append(y, y[0])
    return np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])


def _auf_ring(x, y, laengen, gesamt, a):
    """Der Punkt bei der Bogenlänge a (modulo gesamt) auf dem geschlossenen Ring."""
    a = a % gesamt
    k = int(np.searchsorted(laengen, a, side="right") - 1)
    k = min(max(k, 0), len(x) - 1)
    stueck = laengen[k + 1] - laengen[k]
    t = 0.0 if stueck <= _WINZIG else (a - laengen[k]) / stueck
    k1 = (k + 1) % len(x)
    return (x[k] + (x[k1] - x[k]) * t, y[k] + (y[k1] - y[k]) * t)


def _spirale(ringe, uebergang, schritt):
    """Die geschlossenen Ringe (von außen nach innen) als eine Spirale: Jeder Ring beginnt, wo
    der vorige ihn erreicht, läuft einmal herum und geht auf seinem letzten Stück (`uebergang`
    mm, höchstens ein Drittel des Rings) gleitend in den nächsten über – kein Schritt quer,
    keine Ecke, der Eingriff wächst dabei langsam an. Der Übergang liegt innerhalb des Rings:
    Sein Streifen wird ganz geschnitten. Gibt die Punkte (m, 2) zurück; sie enden am Anfang des
    letzten Rings, der nicht dazugehört."""
    punkte = []
    start = 0
    for nummer in range(len(ringe) - 1):
        x = np.roll(ringe[nummer].proben.x, -start)
        y = np.roll(ringe[nummer].proben.y, -start)
        laengen = _bogenlaengen(x, y, True)
        gesamt = float(laengen[-1])
        nx_, ny_ = ringe[nummer + 1].proben.x, ringe[nummer + 1].proben.y
        # Wo der nächste Ring anfängt: am nächsten beim Anfang dieses.
        naechster = int(np.argmin(np.hypot(nx_ - x[0], ny_ - y[0])))
        nx_, ny_ = np.roll(nx_, -naechster), np.roll(ny_, -naechster)
        laengen_n = _bogenlaengen(nx_, ny_, True)
        gesamt_n = float(laengen_n[-1])
        weit = min(uebergang, gesamt / 3.0, gesamt_n / 3.0)
        ende = gesamt - weit
        for k in range(int(np.searchsorted(laengen, ende, side="left"))):
            punkte.append((float(x[k]), float(y[k])))
        anzahl = max(2, int(math.ceil(weit / schritt)))
        for i in range(anzahl + 1):
            alpha = i / anzahl
            p = _auf_ring(x, y, laengen, gesamt, ende + alpha * weit)
            q = _auf_ring(nx_, ny_, laengen_n, gesamt_n, -(1.0 - alpha) * weit * gesamt_n / gesamt)
            punkte.append((p[0] * (1 - alpha) + q[0] * alpha, p[1] * (1 - alpha) + q[1] * alpha))
        start = naechster
    zug = []
    for p in punkte:
        if not zug or math.hypot(p[0] - zug[-1][0], p[1] - zug[-1][1]) > _WINZIG:
            zug.append(p)
    return np.array(zug) if zug else np.zeros((0, 2))


def _ringe_morph(ablauf, feld, w, r, D, material_links, schritt, toleranz, genaue=()):
    """Der Morph (Manuel, 2026-10-01: „im Viereck anfangen, aber immer runder werden, so dass
    er am Ende nur um den Zapfen fährt“): Zwischen dem ersten Ring – dem Rechteck R − ae
    außerhalb des Rohteils – und dem Ring um die Inseln (D = 0) liegt das Feld u mit Δu = 0,
    u = 1 außen und 0 an den Inseln (_harmonisch). Seine Höhenlinien sind die Ringe: das
    Rechteck, von Ring zu Ring runder, zuletzt der Kreis um den Zapfen – jede eine geschlossene
    Linie, ohne Knick, keine zerfällt. Wie weit der nächste Ring nach innen rückt, sagt der
    Eingriff: so weit, dass die Stirn an keiner Stelle des Rings mehr ungeschnittenes Rohteil
    unter sich hat als bei einem geraden Schnitt mit ae (MORPH_EINGRIFF) – an den Ecken, wo das
    Material außen herum läuft, darf er dafür weiter rücken. Der letzte Ring ist der genaue
    Versatz der Insel (inselringe). Gibt es keine Insel im Rohteil, oder reicht eine bis an den
    Rand, gibt es keinen Morph: dann die Ringe vom Rohteil her."""
    ae = w.zeilenabstand
    aussen = ae - r  # die Tiefe des ersten Rings im Rohteil (negativ: außerhalb)
    insel = np.isfinite(D) & (D <= 0.0)
    if not insel.any():
        _ringe_vom_rohteil(ablauf, feld, w, r, D, material_links, schritt, toleranz)
        return  # keine Insel: die Ringe vom Rohteil her sind schon rund genug
    if (insel & (feld.tiefe <= aussen + ae)).any():
        raise _KeinMorph()  # die Insel reicht bis an den Rand
    um_inseln = [g for _p, g in _hoehenlinien(D, feld.xs, feld.ys, 0.0) if g]
    if len(um_inseln) > 1:
        raise _KeinMorph()  # mehrere Inseln: der Morph rundet auf eine zu
    erster = _rohteil_ring(w.rohteil, aussen, material_links, schritt)
    if erster is None:
        return
    spalt = feld.bei(D, erster.proben.x, erster.proben.y)
    if float(spalt.min()) < MORPH_VERHAELTNIS * float(spalt.max()):
        raise _KeinMorph()
    frei_vorher = feld.frei.copy()
    stufen = [[erster]]
    feld.merke(erster.proben.x, erster.proben.y)
    innen = feld.tiefe > aussen
    unbekannt = innen & ~insel
    abstand_aussen = np.maximum(feld.tiefe - aussen, 0.0)
    nah = np.where(np.isfinite(D), np.maximum(D, 0.0), 0.0)
    summe = nah + abstand_aussen
    with np.errstate(divide="ignore", invalid="ignore"):
        start = np.where(summe > GLEICH, nah / np.where(summe > GLEICH, summe, 1.0), 0.0)
    u = _harmonisch(np.where(insel, 0.0, 1.0), unbekannt, np.clip(start, 0.0, 1.0))
    grenze = _abschnitt(r, min(ae * MORPH_EINGRIFF, r)) / (math.pi * r * r)
    kx, ky = _kreuzpunkte(D, feld.xs, feld.ys, 0.0)
    if not len(kx):
        feld.frei[:] = frei_vorher
        ablauf.ring(erster, kennung="morph 0", luft=True)
        return
    u_insel = float(_bilinear(u, feld, kx, ky).max())  # darüber liegt jeder Ring außerhalb
    niveau = 1.0
    ohne_fortschritt = 0
    for _nummer in range(1, 100000):
        eingriff = feld.eingriff()
        if float(_bilinear(eingriff, feld, kx, ky).max()) <= grenze + 1e-9:
            break  # der Ring um die Insel ist dran
        if ohne_fortschritt >= MORPH_OHNE_FORTSCHRITT:
            break
        unten, oben_ = u_insel, niveau
        for _ in range(MORPH_SCHRITTE):
            mitte = 0.5 * (unten + oben_)
            px, py = _kreuzpunkte(u, feld.xs, feld.ys, mitte)
            if not len(px) or float(_bilinear(eingriff, feld, px, py).max()) <= grenze + 1e-9:
                oben_ = mitte
            else:
                unten = mitte
        if oben_ >= niveau - 1e-9:
            oben_ = niveau - 0.25 * (niveau - u_insel)  # kein Fortschritt: ein Viertel weiter
            ohne_fortschritt += 1
        else:
            ohne_fortschritt = 0
        niveau = oben_
        ringe = []
        for punkte, geschlossen in _hoehenlinien(u, feld.xs, feld.ys, niveau):
            if len(punkte) < 3:
                continue
            ring = _ring_aus_linie(
                punkte, geschlossen, material_links, feld, niveau, u, schritt, toleranz
            )
            if ring is not None:
                ringe.append(ring)
                feld.merke(ring.proben.x, ring.proben.y)
        if ringe:
            stufen.append(ringe)
    letzte = []
    for punkte, geschlossen in _hoehenlinien(D, feld.xs, feld.ys, 0.0):
        if len(punkte) < 3:
            continue
        ring = _ring_aus_linie(punkte, geschlossen, material_links, feld, 0.0, D, schritt, toleranz)
        if ring is not None:
            letzte.append(_genau(ring, genaue, schritt) if geschlossen else ring)
    feld.frei[:] = frei_vorher  # gefahren und gemerkt wird jetzt, der Reihe nach
    if letzte:
        stufen.append(letzte)
    einzeln = all(len(stufe) == 1 and stufe[0].geschlossen for stufe in stufen)
    if einzeln and len(stufen) >= 2:
        # Eine Spirale: alle Ringe bis auf den letzten in einem Zug, mit gleitenden Übergängen;
        # der letzte (um die Insel, mit Bögen) schließt ohne Absatz an.
        ringe = [stufe[0] for stufe in stufen]
        vorher = ablauf.st.ringe
        zug = _spirale(ringe, 2.0 * r, schritt)
        if len(zug) >= 2:
            segmente = _segmente_aus(zug, False)
            spirale = _Ring(segmente, kb._abtasten(segmente, schritt, False), False)
            ablauf.ring(spirale, kennung="morph", luft=True)
        ablauf.ring(ringe[-1], kennung="morph insel", luft=True)
        ablauf.st.ringe = vorher + len(ringe)  # die Umläufe der Spirale zählen als Ringe
        return
    for nummer, stufe in enumerate(stufen):
        _naechster_zuerst(ablauf, list(stufe), False, f"morph {nummer}", luft=True)


def _ringe_um_inseln(ablauf, feld, w, D, material_links, schritt, toleranz, nur_rest, genaue=()):
    """Die Ringe des Feldes D (Abstand zum Gesperrten) von außen nach innen bis ans Gesperrte –
    alle, oder mit `nur_rest` nur die Stücke, unter deren Stirn noch etwas steht (nach den
    Ringen vom Rohteil her)."""
    if not np.isfinite(D).any() or D[np.isfinite(D)].max() <= 0:
        return
    ae = w.zeilenabstand
    gueltig = feld.beruehrt & feld.im_raster(*np.meshgrid(feld.xs, feld.ys, indexing="ij"))
    if nur_rest:
        # Auch das Band an der Wand, wo die Mitte nicht hin darf, die Stirn aber hinreicht: Enden
        # die Ringe davor (die Ringe vom Rohteil her, um die Insel gemessen), fehlt sonst der
        # letzte Ring an der Wand (P-2026-10-01-49).
        rest = gueltig & ~feld.frei & (D + feld.r >= 0)
        if not rest.any():
            return
        hoechste = max(float(D[rest].max()), 0.0)
    else:
        drin = gueltig & (D >= 0)
        if not drin.any():
            return
        hoechste = float(D[drin].max())
    j = int(math.ceil(hoechste / ae))
    while j >= 0:
        niveau = j * ae
        linien = _hoehenlinien(D, feld.xs, feld.ys, niveau)
        ringe = []
        nur = {}
        for punkte, geschlossen in linien:
            if len(punkte) < 2:
                continue
            laenge = float(np.sum(np.hypot(*np.diff(punkte, axis=0).T)))
            if geschlossen and laenge < 2 * math.pi * ae:
                continue  # winzig: der nächste Ring deckt es ab
            ring = _ring_aus_linie(
                punkte, geschlossen, material_links, feld, niveau, D, schritt, toleranz
            )
            if ring is None:
                continue
            if j == 0 and geschlossen:
                genauer = _genau(ring, genaue, schritt)
                if genauer is not ring and genauer.tasche:
                    # An der Wand einer Tasche nach dem Ring aus dem Raster: Er liegt eine Zelle
                    # weiter innen – der Schritt zum genauen bliebe sonst größer als ae, und
                    # jede Lage bekäme eine Rampe mehr.
                    ringe.append(ring)
                ring = genauer  # um die Insel: der genaue Versatz statt des Rasters
            if nur_rest:
                noetig = feld.ungeschnitten(ring.proben.x, ring.proben.y) > 1e-6
                if not noetig.any():
                    continue
                # Ein Stück rundherum (3 mm), damit kein Lauf an einer Zelle endet.
                breit = max(1, int(round(3.0 / schritt)))
                kern = np.concatenate([noetig[-breit:], noetig, noetig[:breit]])
                nur[id(ring)] = np.convolve(kern, np.ones(2 * breit + 1), "same")[breit:-breit] > 0
            ringe.append(ring)
        _naechster_zuerst(ablauf, ringe, True, f"feld {j}", nur if nur_rest else None)
        j -= 1
