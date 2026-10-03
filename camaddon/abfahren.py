# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Maschine fährt die Bahn eines Jobs ab (W-001, Stufe 4b) – der Rechenkern.

Aus der Bahn werden Stationen: je Punkt die Zeit seit Beginn des Jobs, die
Operation und der Satz, der Punkt im Programm und die Stellungen aller Achsen
dort – gerechnet wie in reichweite.py. Zwischen zwei Stationen fährt die
Maschine geradlinig in ihren Achsen; stellungen_bei(zeit) liefert sie zu jeder
Zeit. Dafür sind die Stationen dichter als in der Reichweite: Kreise in
Schritten von höchstens KREIS_SCHRITT, nach einem Bohrzyklus der Rückzug.

Zeit (spezifikation_simulation.md, 4b): Vorschubsätze mit F aus der Bahn –
FreeCAD schreibt mm/s –, ohne F mit VORSCHUB_ERSATZ und einem Hinweis; nach G93
ist F 1 ÷ Zeit des Satzes (vierachs_bahn);
Eilgang je Achse aus der Maschine, die langsamste Achse bestimmt; Beschleunigung je Achse
aus der Maschine (4d, fahrzeit: Trapezprofil, anhalten um Eilgänge und an Ecken, sonst
durchfahren) – fehlt sie, 1 m/s² bzw. 1 U/s².

Läuft ohne Oberfläche.
"""

import bisect
import math
from dataclasses import dataclass, field

from . import einheiten, export
from . import fahrzeit as fz
from . import job_schnittwerte as js
from . import maschine as m
from . import reichweite as rw
from .kette import LINEAR
from .sprache import tr
from .werkstoffe import mit_dezimalzeichen

KREIS_SCHRITT = 5.0  # Grad je Station auf einem Kreisbogen
VORSCHUB_ERSATZ = 1000.0  # mm/min, wenn die Bahn keinen Vorschub hat
# Fehlt ein Kennwert der Maschine: wie bei der Übergabe an CAM.
EILGANG_ERSATZ = export.VORGABE_EILGANG  # mm/min
DREH_ERSATZ = export.VORGABE_DREHGESCHWINDIGKEIT  # U/min
BESCHLEUNIGUNG_ERSATZ = export.VORGABE_BESCHLEUNIGUNG  # m/s²
DREHBESCHLEUNIGUNG_ERSATZ = export.VORGABE_DREHBESCHLEUNIGUNG  # U/s²
REVOLVER_BESCHLEUNIGUNG = 1e9  # Grad/s² – die Schaltzeit steckt schon im Tempo
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
    # Eine Fahrt der Maschine, die nicht im Programm steht (Spezifikation Simulation 13):
    # HOME zum Home-Punkt oder von ihm weg, WECHSEL zum Werkzeugwechselpunkt; "" die Bahn.
    ziel: str = ""


HOME = "home"
WECHSEL = "wechsel"


@dataclass
class OperationAbfahrt:
    """Was zu einer Operation gehört: Werkzeug, Aufnahme, Länge, ihre Stationen."""

    name: str
    tc: object  # Werkzeug-Controller
    aufnahme: object  # Werkzeugaufnahme
    laenge: float  # mm, vom Bezugspunkt (gerader Halter: der Aufnahme) bis zur Spitze
    erste: int  # Index ihrer ersten Station
    saetze: int  # Befehle ihrer Bahn
    art: str = ""  # die Art der CAM-Operation: „Adaptive“, „Deburr“ … (js.operationsart)
    lage: object = None  # Lage des Bezugspunkts in der Aufnahme (halter.lage); None: gerade
    ebene: str = ""  # in einer geschwenkten Ebene (3+2): ihre Rundachsen („A−30 C0“)

    @property
    def einspannung(self):
        """Wie das Werkzeug in der Aufnahme sitzt (reichweite.Einspannung)."""
        return rw.Einspannung(self.laenge, self.lage)


@dataclass
class Abfahrt:
    """Die Stationen eines Jobs auf einer Maschine – abfahrt() baut sie."""

    pruefung: object  # reichweite.Pruefung
    achsen: list  # die Achsen, die sich bewegen, in der Reihenfolge der Kette
    stationen: list = field(default_factory=list)
    operationen: list = field(default_factory=list)
    hinweise: list = field(default_factory=list)
    nullpunkt: object = None  # Vector von der Werkstückaufnahme zum Nullpunkt des Jobs
    _zeiten: list = field(default_factory=list, repr=False)
    _wirksam: list = field(default_factory=list, repr=False)
    _kinematiken: dict = field(default_factory=dict, repr=False)

    def kinematik(self, operation):
        """Die Kinematik (kinematik.Kinematik) für das Werkzeug der Operation mit diesem
        Index – Spitze und Achsen ineinander umrechnen."""
        from .kinematik import Kinematik

        if operation not in self._kinematiken:
            op = self.operationen[operation]
            self._kinematiken[operation] = Kinematik(
                self.pruefung, op.aufnahme, op.einspannung, self.nullpunkt
            )
        return self._kinematiken[operation]

    @property
    def dauer(self):
        """Die ganze Zeit in s."""
        return self.stationen[-1].zeit if self.stationen else 0.0

    def anteile(self):
        """(Vorschub, Eilgang) in s – wie viel der Zeit die Maschine im Vorschub fährt und wie
        viel im Eilgang (Manuel, 2026-10-03: „die Bearbeitung dauert rechnerisch … min“)."""
        vorschub = eilgang = 0.0
        for davor, station in zip(self.stationen, self.stationen[1:], strict=False):
            dauer = station.zeit - davor.zeit
            if station.eilgang:
                eilgang += dauer
            else:
                vorschub += dauer
        return vorschub, eilgang

    def dauer_je_operation(self):
        """[(Name, s)] je Operation in ihrer Reihenfolge – die Fahrt zu ihr (Home, Wechselpunkt)
        zählt zu ihr."""
        zeiten = [0.0] * len(self.operationen)
        for davor, station in zip(self.stationen, self.stationen[1:], strict=False):
            if 0 <= station.operation < len(zeiten):
                zeiten[station.operation] += station.zeit - davor.zeit
        return [(op.name, zeit) for op, zeit in zip(self.operationen, zeiten, strict=True)]

    def index_bei(self, zeit):
        """Die letzte Station, deren Zeit höchstens `zeit` ist (0 davor)."""
        return max(bisect.bisect_right(self._zeiten, zeit) - 1, 0)

    def wirksam(self, index):
        """Die Stellungen an Station `index`, wie die Maschine dort steht: Wo eine Achse
        nicht mitfährt oder der Punkt nicht erreichbar ist, gilt die Stellung davor
        (None: noch keine)."""
        return self._wirksam[index]

    def stellungen_an(self, index):
        """{Achse: Stellung} an Station `index`, wie die Maschine dort steht."""
        return {
            achse: w
            for achse, w in zip(self.achsen, self._wirksam[index], strict=True)
            if w is not None
        }

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

    def station_von(self, ueberschreitung):
        """Die Station an der Stelle einer Überschreitung der Reichweite
        (reichweite.Ueberschreitung) – oder None."""
        punkt = ueberschreitung.punkt
        ziel = (punkt["X"], punkt["Y"], punkt["Z"])
        for nummer, op in enumerate(self.operationen):
            if op.name != ueberschreitung.operation:
                continue
            naechste = self.operationen[nummer + 1 :]
            ende = naechste[0].erste if naechste else len(self.stationen)
            for index in range(op.erste, ende):
                station = self.stationen[index]
                if math.dist(station.punkt, ziel) < 1e-6 and all(
                    abs(station.rund.get(b, 0.0) - punkt[b]) < 1e-6 for b in rw.RUNDACHSEN
                ):
                    return index
        return None

    def am_werkstueck(self):
        """Je Station, wo die Spitze am Werkstück steht, in Koordinaten des Jobs: ihr Punkt –
        mit Rundachsen um sie gedreht (ohne TCPM, kinematik.Kinematik.am_werkstueck). So
        zeigt FreeCAD die Bahn: um das Teil herum, und sie dreht sich mit ihm."""
        ergebnis = []
        for i, station in enumerate(self.stationen):
            if not any(station.rund.values()) or station.stellungen is None:
                ergebnis.append(station.punkt)
                continue
            ergebnis.append(self.kinematik(station.operation).am_werkstueck(self.stellungen_an(i)))
        return ergebnis

    def spitze(self, index, stellungen):
        """Wo die Spitze bei `stellungen` ({Achse: Stellung}, etwa so, wie die Maschine an
        Station `index` wirklich steht) im Programm steht: {"X": …, "Y": …, "Z": …} und die
        Rundachsen – für den Abspieler (4e)."""
        kinematik = self.kinematik(self.stationen[index].operation)
        x, y, z = kinematik.programm(stellungen)
        werte = {"X": x, "Y": y, "Z": z}
        werte.update(kinematik.rundachsen(stellungen))
        return werte

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
    ergebnis = Abfahrt(pruefung, achsen=[], nullpunkt=nullpunkt_des_jobs)
    if pruefung.werkstueckaufnahme is None:
        return ergebnis
    vorbereitet = []
    bewegt = set()  # die Achsen, die für eine der benutzten Werkzeugaufnahmen fahren
    for op, ebene in rw.operationen_mit_ebene(job):
        tc = getattr(op, "ToolController", None)
        aufnahme = pruefung.werkzeugaufnahme(getattr(tc, "ToolNumber", 0)) if tc else None
        if aufnahme is None:
            continue
        linear, _drehachsen = pruefung.achsen_fuer(aufnahme)
        if len(linear) > 3:
            continue
        eingespannt = rw.einspannung(tc, bibliothek)
        try:
            # In einer geschwenkten Ebene die Sätze ohne Schwenkzyklus (3+2, schwenken).
            befehle = pruefung.befehle(op, ebene, aufnahme, eingespannt, nullpunkt_des_jobs)
        except ValueError:
            continue  # die Reichweite sagt, warum
        vorbereitet.append((op, tc, aufnahme, eingespannt, linear, befehle, ebene))
        bewegt.update(pruefung.gefahrene_achsen(aufnahme))
    ergebnis.achsen = [a for a in pruefung.kette.achsen if a in bewegt]
    index = {a: i for i, a in enumerate(ergebnis.achsen)}
    tempo = _tempo(pruefung.maschine, ergebnis.achsen)
    beschleunigung = _beschleunigung(pruefung.maschine, ergebnis.achsen)
    linear_achsen = [a.art == LINEAR for a in ergebnis.achsen]

    vorher = None  # (Punkt, Rundachsen, wirksame Stellungen) der letzten Station
    saetze = []  # fahrzeit.Satz je Station nach der ersten – die Zeiten kommen zum Schluss
    # Home- und Wechselpunkt der Maschine (Spezifikation Simulation 13): Mit einem Home-Punkt
    # beginnt und endet das Abfahren dort, vor jedem Werkzeugwechsel fährt die Maschine zum
    # Wechselpunkt – zuerst die Achse, die das Werkzeug vom Teil wegzieht, und zurück zuerst
    # die anderen.
    home = _heimat(pruefung.maschine, ergebnis.achsen, "Home")
    # Der Wechselpunkt in MKS (wie der Verfahrweg; leer: der Home-Punkt) – oder in WKS: die
    # Spitze des Werkzeugs, ab dem Nullpunkt des Jobs, je Achse mit eigenem Wechselpunkt; die
    # anderen bleiben stehen (Manuel, 2026-10-03: „sollte MKS sein … oder wechselbar“).
    wechsel_wks = {}
    if m.wechsel_bezug(pruefung.maschine) == m.WECHSEL_WKS:
        wechsel_wks = _wechsel_wks(pruefung.maschine, ergebnis.achsen)
        wechsel = (None,) * len(ergebnis.achsen)
    else:
        wechsel = tuple(
            w if w is not None else h
            for w, h in zip(
                _heimat(pruefung.maschine, ergebnis.achsen, "Wechsel"), home, strict=True
            )
        )
    zuerst = _rueckzug(pruefung.maschine, ergebnis.achsen)

    def anfahren(stellungen, nummer, ziel):
        """Eine Station außerhalb des Programms: die Maschine im Eilgang auf `stellungen`
        (None: die Achse bleibt), ihr Punkt im Programm aus der Kinematik der Operation."""
        nonlocal vorher
        wirksam = _wirksam(vorher, stellungen, len(index))
        if vorher is not None:
            saetze.append(
                fz.Satz(0.0, 0.0, 0.0, fest=_eilgangzeit(vorher[2], wirksam, tempo, beschleunigung))
            )
        werte = {a: w for a, w in zip(ergebnis.achsen, wirksam, strict=True) if w is not None}
        punkt = tuple(ergebnis.kinematik(nummer).programm(werte))
        rund = vorher[1] if vorher is not None else dict.fromkeys(rw.RUNDACHSEN, 0.0)
        ergebnis.stationen.append(Station(0.0, nummer, 0, punkt, rund, stellungen, True, ziel))
        vorher = (punkt, rund, wirksam)

    def zurueckziehen(nach, nummer, ziel):
        """Zum Wechsel- oder Home-Punkt: erst die Achse, die wegzieht, dann alle."""
        if not any(n is not None for n in nach):
            return
        erst = tuple(n if z else None for n, z in zip(nach, zuerst, strict=True))
        if any(n is not None for n in erst):  # hat die wegziehende Achse keinen Wert: gleich alle
            anfahren(erst, nummer, ziel)
        anfahren(nach, nummer, ziel)

    anflug = False  # die nächste Station kommt vom Home- oder Wechselpunkt
    vorheriger_tc = None
    davor = None  # (Lösung, Linearachsen) der Operation davor – für den Wechselpunkt in WKS
    for op, tc, aufnahme, eingespannt, linear, befehle, ebene in vorbereitet:
        geschwenkt = ebene is not None
        loesung = pruefung.loeser(aufnahme, eingespannt, nullpunkt_des_jobs)
        nummer = len(ergebnis.operationen)
        if nummer and tc is not vorheriger_tc:
            ziel = _wechsel_ziel(wechsel, wechsel_wks, vorher, davor, index)
            if any(w is not None for w in ziel):
                zurueckziehen(ziel, nummer - 1, WECHSEL)
                anflug = True
        vorheriger_tc = tc
        davor = (loesung, linear)
        ergebnis.operationen.append(
            OperationAbfahrt(
                op.Label,
                tc,
                aufnahme,
                eingespannt.laenge,
                len(ergebnis.stationen),
                len(befehle),
                js.operationsart(op),
                eingespannt.lage,
                getattr(ebene, "Rundachsen", "") if geschwenkt else "",
            )
        )
        if nummer == 0 and any(h is not None for h in home):
            anfahren(home, nummer, HOME)
            anflug = True
        ohne_vorschub = False
        # In einer Ebene beginnt die Operation dort, wo die davor endete: hoch auf die
        # Schwenkhöhe, schwenken – das fährt die Maschine mit, und die Kollision prüft es.
        start = vorher[:2] if geschwenkt and vorher is not None else None
        for schritt in rw._bahn(befehle, lambda _name: None, rueckzug=True, start=start):
            for punkt, rund in _punkte(schritt, loesung(schritt.rund)[0]):
                geloest, dreh = loesung(rund)
                stellungen = _stellungen(geloest, dreh, punkt, linear, index)
                if anflug and stellungen is not None:
                    # Vom Home- oder Wechselpunkt: erst die anderen Achsen über den Punkt, die
                    # wegziehende bleibt oben.
                    anfahren(
                        tuple(None if z else s for s, z in zip(stellungen, zuerst, strict=True)),
                        nummer,
                        HOME if nummer == 0 else WECHSEL,
                    )
                anflug = False
                wirksam = _wirksam(vorher, stellungen, len(index))
                if vorher is not None:
                    eilgang = _eilgangzeit(vorher[2], wirksam, tempo, beschleunigung)
                    if schritt.eilgang:
                        saetze.append(fz.Satz(0.0, 0.0, 0.0, fest=eilgang))
                    elif schritt.invers and schritt.vorschub > 0:
                        # G93: F = 1 ÷ Zeit des Satzes in Minuten, FreeCAD führt es ÷ 60 –
                        # der Satz dauert 1 ÷ F Sekunden, jeder Schritt seinen Anteil; schneller
                        # als im Eilgang fährt keine Achse. Nicht vom Stand in den Stand: Die
                        # Sätze einer Spirale gehen ineinander über – so gerechnet dauerte sie
                        # siebenmal so lang (test_vierachs_pruefen, P-2026-10-01-34).
                        hoechstens = _eilgangzeit(
                            vorher[2], wirksam, tempo, [0.0] * len(beschleunigung)
                        )
                        fest = max(schritt.anteil / schritt.vorschub, hoechstens)
                        saetze.append(fz.Satz(0.0, 0.0, 0.0, fest=fest))
                    else:
                        vorschub = schritt.vorschub * 60.0  # mm/min
                        if vorschub <= 0:
                            ohne_vorschub = True
                            vorschub = VORSCHUB_ERSATZ
                        saetze.append(
                            _vorschubsatz(
                                vorher,
                                punkt,
                                rund,
                                wirksam,
                                vorschub,
                                eilgang,
                                tempo,
                                beschleunigung,
                                linear_achsen,
                            )
                        )
                ergebnis.stationen.append(
                    Station(0.0, nummer, schritt.satz, punkt, rund, stellungen, schritt.eilgang)
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
    if ergebnis.operationen:
        zurueckziehen(home, len(ergebnis.operationen) - 1, HOME)
    zeit = 0.0
    for station, dauer in zip(ergebnis.stationen[1:], fz.zeiten(saetze), strict=True):
        zeit += dauer
        station.zeit = zeit
    ergebnis._fertig()
    return ergebnis


def dauer_text(sekunden):
    """Eine Dauer, wie man sie sagt: „2 h 40 min“, „12 min“, „2,5 min“, „45 s“."""
    s = max(sekunden, 0.0)
    zeichen = einheiten.gewaehltes_dezimalzeichen() or einheiten.PUNKT
    if s >= 3600.0:
        stunden, rest = divmod(round(s / 60.0), 60)
        return tr("zeit.stunden", h=int(stunden), min=int(rest))
    if s >= 600.0:
        return tr("zeit.minuten", min=f"{s / 60.0:.0f}")
    if s >= 60.0:
        return tr("zeit.minuten", min=mit_dezimalzeichen(f"{s / 60.0:.1f}", zeichen))
    return tr("zeit.sekunden", s=f"{s:.0f}")


def zeit_text(sekunden):
    """„1:05,3“ – Minuten und Sekunden mit einer Nachkommastelle."""
    minuten, rest = divmod(max(sekunden, 0.0), 60.0)
    zeichen = einheiten.gewaehltes_dezimalzeichen() or einheiten.PUNKT
    return mit_dezimalzeichen(f"{int(minuten)}:{rest:04.1f}", zeichen)


def _punkte(schritt, geloest):
    """Die Punkte eines Schritts: ein Punkt – oder die Stationen auf einem Kreisbogen, ohne
    sein Ende (das kommt als eigener Schritt): in Schritten von höchstens KREIS_SCHRITT und
    dort, wo eine Achse umkehrt. An diesen Stellen misst die Reichweite, wie weit eine
    Achse fährt; so ist jede Überschreitung auch eine Station."""
    if schritt.art == "punkt":
        yield schritt.ort, schritt.rund
        return
    bogen = schritt.ort
    anzahl = max(1, math.ceil(abs(math.degrees(bogen.winkel)) / KREIS_SCHRITT))
    anteile = [k / anzahl for k in range(1, anzahl)]
    if geloest is not None:
        for t in bogen.anteile(geloest.s):
            if all(abs(t - schon) > 1e-9 for schon in anteile):
                anteile.append(t)
    for t in sorted(anteile):
        yield bogen.bei(t), schritt.rund


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


def _eilgangzeit(von, nach, tempo, beschleunigung):
    """Jede Achse fährt mit ihrem Eilgang und ihrer Beschleunigung vom Stand in den Stand;
    die langsamste bestimmt die Zeit."""
    wege = [
        b - a if a is not None and b is not None else None for a, b in zip(von, nach, strict=True)
    ]
    return fz.eilgangzeit(wege, tempo, beschleunigung)


def _vorschubsatz(vorher, punkt, rund, wirksam, vorschub, eilgang, tempo, beschleunigung, linear):
    """Der Satz im Vorschub für fahrzeit: der Weg der Spitze (dreht sich nur eine Rundachse,
    ihr Winkel), das Tempo aus dem Vorschub (mm/min) – schneller als im Eilgang fährt keine
    Achse –, die Beschleunigung der langsamsten Achse, die mitfährt, und die Richtung in den
    Achsen. Ohne Weg (ein Revolver, der zwischen zwei Operationen schwenkt) kostet der Satz
    die Zeit des Eilgangs."""
    weg = math.dist(vorher[0], punkt)
    drehweg = math.sqrt(sum((rund[b] - vorher[1].get(b, 0.0)) ** 2 for b in rw.RUNDACHSEN))
    strecke = max(weg, drehweg)
    if strecke <= 1e-9:
        return fz.Satz(0.0, 0.0, 0.0, fest=eilgang)
    richtung = tuple(
        (b - a) if a is not None and b is not None else 0.0
        for a, b in zip(vorher[2], wirksam, strict=True)
    )
    faehrt = [abs(d) > 1e-9 for d in richtung]
    langsamste = max(
        (abs(d) / schnell for d, schnell, mit in zip(richtung, tempo, faehrt, strict=True) if mit),
        default=0.0,
    )
    schnell = vorschub / 60.0
    if langsamste > 0:
        schnell = min(schnell, strecke / langsamste)
    a_bahn = min(
        (a for a, mit, lin in zip(beschleunigung, faehrt, linear, strict=True) if mit and lin),
        default=None,
    )
    if a_bahn is None:  # nur Rundachsen – oder keine Achse (der Punkt ist nicht erreichbar)
        a_bahn = min((a for a, mit in zip(beschleunigung, faehrt, strict=True) if mit), default=0.0)
    return fz.Satz(
        strecke,
        schnell,
        a_bahn,
        richtung if any(faehrt) else None,
        richtung if any(faehrt) else None,
    )


def _heimat(maschine, achsen, eigenschaft):
    """Je Achse die Stellung des Home-Punkts (`eigenschaft` "Home") oder des Wechselpunkts
    ("Wechsel") aus der Betriebsart Linear – None, wo keiner eingetragen ist."""
    betriebsarten = m.betriebsarten(maschine)
    ergebnis = []
    for achse in achsen:
        ba = next(
            (b for b in betriebsarten if b.Gelenk == achse.gelenk and b.Art == m.ART_LINEAR),
            None,
        )
        gesetzt = achse.art == LINEAR and ba is not None and getattr(ba, eigenschaft + "An", False)
        ergebnis.append(float(getattr(ba, eigenschaft)) if gesetzt else None)
    return tuple(ergebnis)


def _wechsel_wks(maschine, achsen):
    """{Achse: (Index im Programmpunkt X/Y/Z, Wert)} der Linearachsen mit eigenem Wechselpunkt,
    wenn er in WKS zählt – der Wert die Stelle der Spitze im Programm (mm; X der Drehmaschine
    als Radius, wie gespeichert)."""
    betriebsarten = m.betriebsarten(maschine)
    ergebnis = {}
    for achse in achsen:
        ba = next(
            (b for b in betriebsarten if b.Gelenk == achse.gelenk and b.Art == m.ART_LINEAR),
            None,
        )
        if achse.art != LINEAR or ba is None or not getattr(ba, "WechselAn", False):
            continue
        buchstabe = m.programmname(ba)[:1].upper()
        if buchstabe in "XYZ":
            ergebnis[achse] = ("XYZ".index(buchstabe), float(ba.Wechsel))
    return ergebnis


def _wechsel_ziel(mks, wks, vorher, davor, index):
    """Die Stellungen zum Werkzeugwechsel: in MKS `mks`; in WKS (`wks` nicht leer) der Punkt der
    Spitze, an dem die Operation davor endete, mit den Werten des Wechselpunkts, gelöst mit
    ihrem Werkzeug – nur die Achsen mit eigenem Wechselpunkt fahren."""
    if not wks or vorher is None or davor is None:
        return mks
    loesung, linear = davor
    punkt = list(vorher[0])
    for stelle, wert in wks.values():
        punkt[stelle] = wert
    geloest, _dreh = loesung(vorher[1])
    if geloest is None:
        return mks
    werte = list(mks)
    for achse, wert in zip(linear, geloest.werte(*punkt), strict=True):
        if achse in wks and achse in index:
            werte[index[achse]] = wert
    return tuple(werte)


def _rueckzug(maschine, achsen):
    """Je Achse, ob sie zum Wechsel- und Home-Punkt zuerst fährt: an der Fräse Z – das Werkzeug
    hoch –, an der Drehmaschine (X im Durchmesser) X – das Werkzeug vom Teil weg."""
    buchstabe = "X" if m.x_im_durchmesser(maschine) else "Z"
    betriebsarten = m.betriebsarten(maschine)
    ergebnis = []
    for achse in achsen:
        ba = next(
            (b for b in betriebsarten if b.Gelenk == achse.gelenk and b.Art == m.ART_LINEAR),
            None,
        )
        name = (ba.NcName or "").strip().upper() if ba is not None else ""
        ergebnis.append(achse.art == LINEAR and name.startswith(buchstabe))
    return tuple(ergebnis)


def _beschleunigung(maschine, achsen):
    """Je Achse ihre Beschleunigung: mm/s² bzw. Grad/s² – aus der Maschine (m/s², U/s²), fehlt
    sie, die Vorgabe; der Revolver praktisch sofort (seine Schaltzeit steckt im Tempo)."""
    betriebsarten = m.betriebsarten(maschine)
    ergebnis = []
    for achse in achsen:
        eigene = {b.Art: b for b in betriebsarten if b.Gelenk == achse.gelenk}
        if achse.art == LINEAR:
            ba = eigene.get(m.ART_LINEAR)
            ergebnis.append(((ba.Beschleunigung if ba else 0) or BESCHLEUNIGUNG_ERSATZ) * 1000.0)
        elif m.ART_REVOLVER in eigene:
            ergebnis.append(REVOLVER_BESCHLEUNIGUNG)
        else:
            ba = eigene.get(m.ART_POSITIONIEREN)
            ergebnis.append(((ba.Beschleunigung if ba else 0) or DREHBESCHLEUNIGUNG_ERSATZ) * 360.0)
    return ergebnis


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
