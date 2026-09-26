# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Maschine fährt die Bahn eines Jobs ab (W-001, Stufe 4b) – der Rechenkern.

Aus der Bahn werden Stationen: je Punkt die Zeit seit Beginn des Jobs, die
Operation und der Satz, der Punkt im Programm und die Stellungen aller Achsen
dort – gerechnet wie in reichweite.py. Zwischen zwei Stationen fährt die
Maschine geradlinig in ihren Achsen; stellungen_bei(zeit) liefert sie zu jeder
Zeit. Dafür sind die Stationen dichter als in der Reichweite: Kreise in
Schritten von höchstens KREIS_SCHRITT, nach einem Bohrzyklus der Rückzug.

Zeit (spezifikation_simulation.md, 4b): Vorschubsätze mit F aus der Bahn –
FreeCAD schreibt mm/s –, ohne F mit VORSCHUB_ERSATZ und einem Hinweis;
Eilgang je Achse aus der Maschine, die langsamste Achse bestimmt.
Beschleunigung kommt mit 4d.

Läuft ohne Oberfläche.
"""

import bisect
import math
from dataclasses import dataclass, field

from . import einheiten, export
from . import maschine as m
from . import reichweite as rw
from .kette import LINEAR
from .sprache import tr

KREIS_SCHRITT = 5.0  # Grad je Station auf einem Kreisbogen
VORSCHUB_ERSATZ = 1000.0  # mm/min, wenn die Bahn keinen Vorschub hat
# Fehlt ein Kennwert der Maschine: wie bei der Übergabe an CAM.
EILGANG_ERSATZ = export.VORGABE_EILGANG  # mm/min
DREH_ERSATZ = export.VORGABE_DREHGESCHWINDIGKEIT  # U/min
REVOLVER_ERSATZ = 0.5  # s für eine halbe Umdrehung ohne eingetragene Schaltzeit


@dataclass
class Station:
    """Ein Punkt der Bahn mit seiner Zeit."""

    zeit: float  # s seit Beginn des Jobs
    operation: int  # Index in Abfahrt.operationen
    satz: int  # der wievielte Befehl der Operation (ab 1)
    punkt: tuple  # (x, y, z) im Job
    rund: dict  # Rundachsen im Programm: {"A": …, "B": …, "C": …}
    # Je Achse in Abfahrt.achsen die Stellung – None, wo die Achse hier nicht
    # mitfährt. Das Ganze None: Die Linearachsen erreichen den Punkt nicht.
    stellungen: tuple | None
    eilgang: bool  # die Bewegung hierher


@dataclass
class OperationAbfahrt:
    """Was zu einer Operation gehört: Werkzeug, Aufnahme, Länge, ihre Stationen."""

    name: str
    tc: object  # Werkzeug-Controller
    aufnahme: object  # Werkzeugaufnahme
    laenge: float  # mm, von der Aufnahme bis zur Spitze
    erste: int  # Index ihrer ersten Station
    saetze: int  # Befehle ihrer Bahn


@dataclass
class Abfahrt:
    """Die Stationen eines Jobs auf einer Maschine – abfahrt() baut sie."""

    pruefung: object  # reichweite.Pruefung
    achsen: list  # die Achsen, die sich bewegen, in der Reihenfolge der Kette
    stationen: list = field(default_factory=list)
    operationen: list = field(default_factory=list)
    hinweise: list = field(default_factory=list)
    _zeiten: list = field(default_factory=list, repr=False)
    _wirksam: list = field(default_factory=list, repr=False)

    @property
    def dauer(self):
        """Die ganze Zeit in s."""
        return self.stationen[-1].zeit if self.stationen else 0.0

    def index_bei(self, zeit):
        """Die letzte Station, deren Zeit höchstens `zeit` ist (0 davor)."""
        return max(bisect.bisect_right(self._zeiten, zeit) - 1, 0)

    def wirksam(self, index):
        """Die Stellungen an Station `index`, wie die Maschine dort steht: Wo eine Achse
        nicht mitfährt oder der Punkt nicht erreichbar ist, gilt die Stellung davor
        (None: noch keine)."""
        return self._wirksam[index]

    def stellungen_bei(self, zeit):
        """{Achse: Stellung} zur Zeit `zeit`, zwischen zwei Stationen geradlinig."""
        if not self.stationen:
            return {}
        i = self.index_bei(zeit)
        von = self._wirksam[i]
        if i + 1 >= len(self.stationen):
            werte = von
        else:
            nach = self._wirksam[i + 1]
            t0, t1 = self.stationen[i].zeit, self.stationen[i + 1].zeit
            anteil = min(max((zeit - t0) / (t1 - t0), 0.0), 1.0) if t1 > t0 else 1.0
            werte = [
                a if b is None else b if a is None else a + anteil * (b - a)
                for a, b in zip(von, nach, strict=True)
            ]
        return {achse: w for achse, w in zip(self.achsen, werte, strict=True) if w is not None}

    def _fertig(self):
        """Zeiten für die Suche und die wirksamen Stellungen je Station."""
        self._zeiten = [s.zeit for s in self.stationen]
        letzte = (None,) * len(self.achsen)
        self._wirksam = []
        for station in self.stationen:
            if station.stellungen is not None:
                letzte = tuple(
                    alt if neu is None else neu
                    for alt, neu in zip(letzte, station.stellungen, strict=True)
                )
            self._wirksam.append(letzte)


def abfahrt(pruefung, job, nullpunkt_des_jobs=None, bibliothek=None):
    """Die Stationen aller aktiven Operationen des Jobs auf der Maschine der Prüfung.

    Operationen, die die Prüfung übergeht (kein Werkzeug-Controller, kein
    Platz am Revolver, zu viele Linearachsen), fehlen – das sagt schon die
    Reichweite (reichweite.Pruefung.pruefe_job).
    """
    if nullpunkt_des_jobs is None:
        nullpunkt_des_jobs = rw.nullpunkt(job)
    ergebnis = Abfahrt(pruefung, achsen=[])
    if pruefung.werkstueckaufnahme is None:
        return ergebnis
    vorbereitet = []
    bewegt = set()  # die Achsen, die für eine der benutzten Werkzeugaufnahmen fahren
    for op in rw._operationen(job):
        tc = getattr(op, "ToolController", None)
        aufnahme = pruefung.werkzeugaufnahme(getattr(tc, "ToolNumber", 0)) if tc else None
        if aufnahme is None:
            continue
        linear, _drehachsen = pruefung.achsen_fuer(aufnahme)
        if len(linear) > 3:
            continue
        laenge, _quelle = rw.werkzeuglaenge(tc, bibliothek)
        vorbereitet.append((op, tc, aufnahme, laenge, linear))
        bewegt.update(pruefung.gefahrene_achsen(aufnahme))
    ergebnis.achsen = [a for a in pruefung.kette.achsen if a in bewegt]
    index = {a: i for i, a in enumerate(ergebnis.achsen)}
    tempo = _tempo(pruefung.maschine, ergebnis.achsen)

    vorher = None  # (Punkt, Rundachsen, wirksame Stellungen) der letzten Station
    zeit = 0.0
    for op, tc, aufnahme, laenge, linear in vorbereitet:
        loesung = pruefung.loeser(aufnahme, laenge, nullpunkt_des_jobs)
        nummer = len(ergebnis.operationen)
        ergebnis.operationen.append(
            OperationAbfahrt(
                op.Label, tc, aufnahme, laenge, len(ergebnis.stationen), len(op.Path.Commands)
            )
        )
        ohne_vorschub = False
        for schritt in rw._bahn(op.Path.Commands, lambda _name: None, rueckzug=True):
            for punkt, rund in _punkte(schritt):
                geloest, dreh = loesung(rund)
                stellungen = _stellungen(geloest, dreh, punkt, linear, index)
                wirksam = _wirksam(vorher, stellungen, len(index))
                if vorher is not None:
                    if schritt.eilgang:
                        zeit += _eilgangzeit(vorher[2], wirksam, tempo)
                    else:
                        vorschub = schritt.vorschub * 60.0  # mm/min
                        if vorschub <= 0:
                            ohne_vorschub = True
                            vorschub = VORSCHUB_ERSATZ
                        zeit += _vorschubzeit(vorher, punkt, rund, vorschub)
                ergebnis.stationen.append(
                    Station(zeit, nummer, schritt.satz, punkt, rund, stellungen, schritt.eilgang)
                )
                vorher = (punkt, rund, wirksam)
        if ohne_vorschub:
            gezeigt = f"{einheiten.gerundet(VORSCHUB_ERSATZ, einheiten.VORSCHUB):g}"
            ergebnis.hinweise.append(
                tr(
                    "ab.ohne_vorschub",
                    operation=op.Label,
                    vorschub=f"{gezeigt} {einheiten.einheit(einheiten.VORSCHUB)}",
                )
            )
    ergebnis._fertig()
    return ergebnis


def _punkte(schritt):
    """Die Punkte eines Schritts: ein Punkt – oder die Stationen auf einem Kreisbogen,
    ohne sein Ende (das kommt als eigener Schritt)."""
    if schritt.art == "punkt":
        yield schritt.ort, schritt.rund
        return
    bogen = schritt.ort
    anzahl = max(1, math.ceil(abs(math.degrees(bogen.winkel)) / KREIS_SCHRITT))
    for k in range(1, anzahl):
        yield bogen.bei(k / anzahl), schritt.rund


def _stellungen(geloest, dreh, punkt, linear, index):
    """Die Stellungen als Tupel je Achse – None, wenn die Linearachsen nicht hinkommen."""
    if geloest is None or not geloest.erreichbar(*punkt):
        return None
    werte = [None] * len(index)
    for achse, wert in zip(linear, geloest.werte(*punkt), strict=True):
        werte[index[achse]] = wert
    for achse, wert in dreh.items():
        if achse in index:
            werte[index[achse]] = wert
    return tuple(werte)


def _wirksam(vorher, stellungen, anzahl):
    """Wie die Maschine an dieser Station steht (siehe Abfahrt.wirksam)."""
    alt = vorher[2] if vorher is not None else (None,) * anzahl
    if stellungen is None:
        return alt
    return tuple(a if n is None else n for a, n in zip(alt, stellungen, strict=True))


def _eilgangzeit(von, nach, tempo):
    """Jede Achse fährt mit ihrem Eilgang; die langsamste bestimmt die Zeit."""
    zeit = 0.0
    for a, b, schnell in zip(von, nach, tempo, strict=True):
        if a is not None and b is not None:
            zeit = max(zeit, abs(b - a) / schnell)
    return zeit


def _vorschubzeit(vorher, punkt, rund, vorschub):
    """Weg durch Vorschub (mm/min); dreht sich nur eine Rundachse, zählt ihr Winkel."""
    weg = math.dist(vorher[0], punkt)
    drehweg = math.sqrt(sum((rund[b] - vorher[1].get(b, 0.0)) ** 2 for b in rw.RUNDACHSEN))
    return max(weg, drehweg) / (vorschub / 60.0)


def _tempo(maschine, achsen):
    """Je Achse, wie schnell sie im Eilgang fährt: mm/s bzw. Grad/s."""
    betriebsarten = m.betriebsarten(maschine)
    ergebnis = []
    for achse in achsen:
        eigene = {b.Art: b for b in betriebsarten if b.Gelenk == achse.gelenk}
        if achse.art == LINEAR:
            ba = eigene.get(m.ART_LINEAR)
            ergebnis.append(((ba.Eilgang if ba else 0) or EILGANG_ERSATZ) / 60.0)
        elif m.ART_REVOLVER in eigene:
            schaltzeit = eigene[m.ART_REVOLVER].Schaltzeit or REVOLVER_ERSATZ
            ergebnis.append(180.0 / schaltzeit)
        else:
            ba = eigene.get(m.ART_POSITIONIEREN)
            ergebnis.append(((ba.Geschwindigkeit if ba else 0) or DREH_ERSATZ) * 6.0)
    return ergebnis
