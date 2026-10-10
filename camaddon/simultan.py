# SPDX-License-Identifier: LGPL-2.1-or-later
"""5 Achsen simultan (W-015, Spezifikation Strategien 16) – der Kern S1.

Eine Bahn mit Achse: je Punkt die Spitze und die Werkzeugachse (von der Spitze weg) im
Grundjob. Daraus je Punkt die Rundachsen – stetig entlang der Bahn: die erste Stellung die beste
der Maschine (schwenken.Maschine.loese), jede weitere vom Punkt davor aus nachgeführt
(Gauß-Newton über die Rundachsen, gedämpft: am Pol, wo eine Rundachse die Werkzeugachse nicht
mehr ändert, bleibt sie stehen) – und X, Y, Z, wie eine Steuerung ohne TCPM sie liest
(schwenken.Abbildung, wie „Auf der Maschine prüfen“).

Wie die Bahn entsteht (Kugelfräser angestellt, Flanke …) und ob das Programm TCPM nimmt,
entscheidet Manuel (Spezifikation 16.4); die Rundachsen entlang der Bahn braucht jeder Weg –
auch die Prüfung auf der Maschine. Ohne TCPM fährt die Maschine zwischen zwei Sätzen jede Achse
linear; dreht sich dabei eine Rundachse, wandert die Spitze am Werkstück von der Geraden weg.
programm_ohne_tcpm() setzt deshalb Punkte dazwischen, bis die Spitze in der Mitte jedes Satzes
höchstens `toleranz` neben der Geraden liegt (`verdichtet`). Mit `bezug` bleibt statt der
Spitze ein Punkt so weit die Achse hinauf auf der Geraden – beim Kugelfräser ihre Mitte (der
Kugelfräser angestellt, angestellt.py: Die Kugel fährt die Bahn, die Achse kippt um sie). Läuft
ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import FreeCAD

from . import schwenken as sw
from .sprache import tr

SCHRITT = 1e-4  # Grad – so weit dreht eine Rundachse für die Ableitung der Werkzeugachse
GENAU = 1e-13  # 1 − cos des Winkels zwischen Werkzeugachse und Ziel: genau genug
DAEMPFUNG = 1e-9  # gegen die Singularität am Pol (Anteil an der Spur von JᵀJ)
GROESSTER_SCHRITT = 10.0  # Grad je Rechenschritt – sonst springt es am Pol auf den anderen Ast
KUERZESTE_ZEIT = 1e-3  # s – so kurz dauert ein Satz mit G93 mindestens
# Im Vorschub dreht eine Rundachse höchstens mit diesem Anteil ihrer Geschwindigkeit aus der
# Maschine (ohne Angabe export.VORGABE_DREHGESCHWINDIGKEIT) – bis P-2026-10-04-42 zählte 1° wie
# 1 mm beim Schnittvorschub: Wegkippen in der Kavität dauerte so 3,00 statt 1,50 min (Manuel,
# 2026-10-04: „Ja, mit halber Geschwindigkeit“). Die Spitze fährt nie schneller als der Vorschub.
DREHANTEIL = 0.5
TOLERANZ = 0.005  # mm – so weit darf die Spitze in der Mitte eines Satzes neben der Geraden liegen
TIEFE = 10  # so oft halbiert verdichtet() einen Satz höchstens (1024 Stücke)


@dataclass
class Punkt:
    """Ein Punkt der Bahn: die Spitze und die Werkzeugachse (von der Spitze weg) im Grundjob,
    Eilgang oder Vorschub (mm/s wie FreeCADs Bahnen; 0: wie davor)."""

    spitze: tuple
    achse: tuple
    eilgang: bool = False
    vorschub: float = 0.0
    verbindung: bool = False  # Neu durch ausgelassene Schnittzüge; auch Zwischenpunkte zählen.


def rundachsen_entlang(maschine, achsen):
    """[{Buchstabe: Grad}] – je Werkzeugachse (im Grundjob) die Stellung der Rundachsen von
    `maschine` (schwenken.Maschine), stetig entlang der Bahn. Endlose Achsen laufen über ±180°
    hinaus weiter, statt zu springen. ValueError mit einem Satz, wenn eine Achse nicht zu
    treffen ist oder eine Rundachse über ihre Grenze müsste."""
    rundachsen = maschine.rundachsen
    ergebnis = []
    werte = None
    for nummer, achse in enumerate(achsen, start=1):
        n = FreeCAD.Vector(*achse)
        n.normalize()
        if werte is None:
            loesungen = maschine.loese(n)
            if not loesungen:
                raise ValueError(tr("si.fehler.achse", punkt=nummer))
            werte = [loesungen[0][a.buchstabe] for a in rundachsen]
        else:
            werte = _nachfuehren(maschine, n, werte)
            if werte is None:
                raise ValueError(tr("si.fehler.achse", punkt=nummer))
        rund = {a.buchstabe: sw._rund(w) for a, w in zip(rundachsen, werte, strict=True)}
        for a in rundachsen:
            if not a.erlaubt(rund[a.buchstabe]):
                raise ValueError(
                    tr(
                        "si.fehler.grenze",
                        punkt=nummer,
                        achse=a.buchstabe,
                        wert=f"{rund[a.buchstabe]:.1f}",
                    )
                )
        ergebnis.append(rund)
    return ergebnis


def _nachfuehren(maschine, n, werte):
    """Die Rundachsen (Grad, Liste wie maschine.rundachsen), mit denen die Werkzeugachse `n`
    ist – von `werte` aus gesucht; None, wenn es nicht genau genug geht."""
    import numpy

    rundachsen = maschine.rundachsen
    ziel = numpy.array([n.x, n.y, n.z])

    def richtung(w):
        d = maschine.richtung({a.buchstabe: x for a, x in zip(rundachsen, w, strict=True)})
        return numpy.array([d.x, d.y, d.z])

    werte = [float(w) for w in werte]
    for _ in range(40):
        d = richtung(werte)
        if 1.0 - float(d @ ziel) <= GENAU:
            return werte
        if not rundachsen:
            return None  # Eine feste Achse kann nicht in die nächste Richtung kippen.
        spalten = []
        for i in range(len(werte)):
            versuch = list(werte)
            versuch[i] += SCHRITT
            spalten.append((richtung(versuch) - d) / SCHRITT)
        j = numpy.array(spalten).T
        jtj = j.T @ j
        daempfung = DAEMPFUNG * max(float(numpy.trace(jtj)), 1e-12)
        schritt = numpy.linalg.solve(jtj + daempfung * numpy.eye(len(werte)), j.T @ (ziel - d))
        groesster = float(numpy.max(numpy.abs(schritt)))
        if groesster > GROESSTER_SCHRITT:
            schritt *= GROESSTER_SCHRITT / groesster
        werte = [w + float(s) for w, s in zip(werte, schritt, strict=True)]
    d = richtung(werte)
    grenze = 1.0 - math.cos(math.radians(sw.WINKEL_GENAU))
    return werte if 1.0 - float(d @ ziel) <= grenze else None


def _bezuege(bezug):
    """`bezug` als Tupel: eine Zahl oder mehrere (die erste fährt auf der Geraden, alle zählen
    für die Abweichung – an der Flanke die Spitze und das obere Ende der Schneide)."""
    return tuple(bezug) if isinstance(bezug, (tuple, list)) else (float(bezug or 0.0),)


def bezugspunkt(punkt, bezug=0.0):
    """Der Punkt `bezug` mm die Achse hinauf über der Spitze (beim Kugelfräser mit dem Radius:
    die Mitte der Kugel; mehrere Bezüge: der erste)."""
    b = _bezuege(bezug)[0]
    return tuple(s + b * a for s, a in zip(punkt.spitze, punkt.achse, strict=True))


def abweichung(maschine, von, nach, rund_von, rund_nach, bezug=0.0, tcpm=False):
    """Wie weit (mm) die Spitze am Werkstück – mit `bezug` der Punkt so weit die Achse hinauf –
    in der Mitte des Satzes `von` → `nach` (Punkt) neben der Geraden liegt, wenn die Maschine X,
    Y, Z und die Rundachsen (`rund_…`) linear fährt – ohne TCPM. Mit `tcpm` führt die Steuerung
    die Spitze auf der Geraden und dreht die Rundachsen linear: Abweichen kann nur der Punkt
    `bezug` darüber (die Mitte der Kugel, das obere Ende der Schneide). None, wenn die Maschine an
    einer Stellung keine Abbildung hat."""
    if rund_von == rund_nach:
        return 0.0  # dieselbe Abbildung am Anfang, in der Mitte und am Ende: genau die Gerade
    mitte = {k: (rund_von[k] + rund_nach[k]) / 2 for k in rund_von}
    if tcpm:
        if not any(_bezuege(bezug)):
            return 0.0
        achse = maschine.richtung(mitte)
        spitze = [(u + v) / 2 for u, v in zip(von.spitze, nach.spitze, strict=True)]
        groesste = 0.0
        for b in _bezuege(bezug):
            ist = [spitze[0] + b * achse.x, spitze[1] + b * achse.y, spitze[2] + b * achse.z]
            soll = [
                (u + v) / 2 for u, v in zip(bezugspunkt(von, b), bezugspunkt(nach, b), strict=True)
            ]
            groesste = max(groesste, math.dist(ist, soll))
        return groesste
    a0, a1, am = (maschine.abbildung(r) for r in (rund_von, rund_nach, mitte))
    if a0 is None or a1 is None or am is None:
        return None
    p0, p1 = a0.punkt(von.spitze), a1.punkt(nach.spitze)
    programm = [(u + v) / 2 for u, v in zip(p0, p1, strict=True)]
    d = [programm[i] - am.b[i] for i in range(3)]
    spitze = [sum(am.a[k][i] * d[k] for k in range(3)) for i in range(3)]  # Aᵀ · (P − b)
    achse = maschine.richtung(mitte) if any(_bezuege(bezug)) else None
    groesste = 0.0
    for b in _bezuege(bezug):
        ist = spitze
        if b:
            ist = [spitze[0] + b * achse.x, spitze[1] + b * achse.y, spitze[2] + b * achse.z]
        soll = [(u + v) / 2 for u, v in zip(bezugspunkt(von, b), bezugspunkt(nach, b), strict=True)]
        groesste = max(groesste, math.dist(ist, soll))
    return groesste


def verdichtet(maschine, punkte, rund, toleranz=TOLERANZ, bezug=0.0, eilgaenge=False, tcpm=False):
    """(Punkte, Rundachsen) – zwischen zwei Sätzen im Vorschub so viele Punkte auf der Geraden
    dazu (die Achse dazwischen gemittelt, die Rundachsen von davor aus nachgeführt), bis die
    Spitze – mit `bezug` der Punkt so weit die Achse hinauf – in der Mitte jedes Satzes
    höchstens `toleranz` neben ihr liegt (abweichung); höchstens TIEFE-mal halbiert. Eilgänge
    bleiben, wie sie sind – mit `eilgaenge` auch sie, wenn sich in ihnen die Achse dreht (über
    dem Teil: Die Spitze bleibt auf der Geraden, statt auszuschwingen). `tcpm`: wie abweichung."""
    if not punkte:
        return [], []
    neu_punkte, neu_rund = [punkte[0]], [rund[0]]
    buchstaben = [a.buchstabe for a in maschine.rundachsen]

    def halbieren(von, nach, r_von, r_nach, tiefe):
        fehler = abweichung(maschine, von, nach, r_von, r_nach, bezug, tcpm)
        if fehler is None or fehler <= toleranz or tiefe >= TIEFE:
            neu_punkte.append(nach)
            neu_rund.append(r_nach)
            return
        achse = [(u + v) / 2 for u, v in zip(von.achse, nach.achse, strict=True)]
        n = FreeCAD.Vector(*achse)
        if n.Length < 1e-9:
            neu_punkte.append(nach)
            neu_rund.append(r_nach)
            return
        n.normalize()
        werte = _nachfuehren(maschine, n, [r_von[b] for b in buchstaben])
        if werte is None:
            neu_punkte.append(nach)
            neu_rund.append(r_nach)
            return
        r_mitte = {b: sw._rund(w) for b, w in zip(buchstaben, werte, strict=True)}
        bezug_mitte = [
            (u + v) / 2
            for u, v in zip(bezugspunkt(von, bezug), bezugspunkt(nach, bezug), strict=True)
        ]
        erster = _bezuege(bezug)[0]
        mitte = Punkt(
            (
                bezug_mitte[0] - erster * n.x,
                bezug_mitte[1] - erster * n.y,
                bezug_mitte[2] - erster * n.z,
            ),
            (n.x, n.y, n.z),
            eilgang=nach.eilgang,
            vorschub=nach.vorschub,
            verbindung=nach.verbindung,
        )
        halbieren(von, mitte, r_von, r_mitte, tiefe + 1)
        halbieren(mitte, nach, r_mitte, r_nach, tiefe + 1)

    for i in range(1, len(punkte)):
        if punkte[i].eilgang and not (eilgaenge and rund[i] != rund[i - 1]):
            neu_punkte.append(punkte[i])
            neu_rund.append(rund[i])
        else:
            halbieren(punkte[i - 1], punkte[i], rund[i - 1], rund[i], 0)
    return neu_punkte, neu_rund


def drehgeschwindigkeiten(maschine, anteil=DREHANTEIL):
    """{Buchstabe: °/s} – wie schnell jede Rundachse der Maschine (sw.Maschine) im Vorschub
    höchstens dreht: `anteil` ihrer Geschwindigkeit (U/min) aus der Betriebsart."""
    from . import export
    from . import maschine as m

    betriebsarten = []
    objekt = getattr(getattr(maschine, "pruefung", None), "maschine", None)
    if objekt is not None:
        try:
            betriebsarten = [b for b in m.betriebsarten(objekt) if b.Art == m.ART_POSITIONIEREN]
        except Exception:
            betriebsarten = []
    ergebnis = {}
    for r in getattr(maschine, "rundachsen", []):
        gelenk = getattr(r.achse, "gelenk", None)
        ba = next((b for b in betriebsarten if b.Gelenk == gelenk), None)
        u_min = (
            float(getattr(ba, "Geschwindigkeit", 0.0) or 0.0) or export.VORGABE_DREHGESCHWINDIGKEIT
        )
        ergebnis[r.buchstabe] = u_min * 360.0 / 60.0 * anteil
    return ergebnis


def eilganggeschwindigkeit(maschine):
    """mm/s – der langsamste Eilgang der Linearachsen der Maschine (sw.Maschine); ohne Angabe
    export.VORGABE_EILGANG."""
    from . import export
    from . import maschine as m

    objekt = getattr(getattr(maschine, "pruefung", None), "maschine", None)
    werte = []
    if objekt is not None:
        try:
            werte = [
                float(getattr(b, "Eilgang", 0.0) or 0.0)
                for b in m.betriebsarten(objekt)
                if b.Art == m.ART_LINEAR
            ]
        except Exception:
            werte = []
    werte = [w for w in werte if w > 0]
    return (min(werte) if werte else export.VORGABE_EILGANG) / 60.0


def programm_ohne_tcpm(
    maschine,
    punkte,
    g93=False,
    toleranz=TOLERANZ,
    bezug=0.0,
    eilgaenge=False,
    materialdaten=None,
    verbindungen=None,
):
    """[Path.Command] – die Bahn (Punkt …) mit den Rundachsen je Punkt und X, Y, Z, wie eine
    Steuerung ohne TCPM sie liest. Zwischen zwei Punkten fährt die Maschine jede Achse linear –
    die Spitze bleibt nur nahe der Geraden, wenn die Punkte dicht liegen. `g93`: der Vorschub
    als 1 ÷ Zeit (G93 … G94): je Satz die längere Zeit aus dem Weg der Spitze (mit `bezug` des
    Punkts darüber) am Werkstück und dem Vorschub und aus dem Winkel jeder Rundachse und ihrer
    Geschwindigkeit im Vorschub (drehgeschwindigkeiten); F wie FreeCADs Bahnen ÷ 60 (1 ÷
    Sekunden). `toleranz`: Sätze im Vorschub so dicht, dass die Spitze
    in ihrer Mitte höchstens so weit neben der Geraden liegt (verdichtet; 0 oder None: wie
    gegeben), `bezug` und `eilgaenge` wie dort. Die optionale Liste `materialdaten`
    erhält je NC-Satz (ursprünglicher Eilgang, Schnittvorschub in mm/s), auch nach
    Verdichtung und Umwandlung eines Eilgangs in G1/G93. ValueError mit einem Satz wie
    rundachsen_entlang, oder wenn die Maschine keine drei Linearachsen hat."""
    import Path

    rund = rundachsen_entlang(maschine, [p.achse for p in punkte])
    if toleranz:
        punkte, rund = verdichtet(maschine, punkte, rund, toleranz, bezug, eilgaenge)
    befehle = [Path.Command("G93")] if g93 else []
    if materialdaten is not None:
        materialdaten[:] = [(True, 0.0)] if g93 else []
    if verbindungen is not None:
        verbindungen[:] = [False] if g93 else []
    vorschub, davor = 0.0, None
    drehen = drehgeschwindigkeiten(maschine) if g93 else {}
    # Ein Eilgang, in dem sich eine Rundachse dreht (verdichtet: viele kurze Sätze), als G1 im G93
    # mit der Geschwindigkeit des Eilgangs – an jedem G0 hielte die Maschine an: Beim Wegkippen
    # dauerte der Weg zwischen zwei Bahnen so 3,3 statt 0,3 s.
    eil_dreh = drehgeschwindigkeiten(maschine, 1.0) if g93 else {}
    eil_linear = eilganggeschwindigkeit(maschine) if g93 else 0.0
    abbildungen = {}  # je Stellung einmal gerechnet – die meisten Punkte teilen sie
    for punkt, stellung in zip(punkte, rund, strict=True):
        schluessel = tuple(sorted(stellung.items()))
        if schluessel not in abbildungen:
            abbildungen[schluessel] = maschine.abbildung(stellung)
        abbildung = abbildungen[schluessel]
        if abbildung is None:
            raise ValueError(tr("si.fehler.linear"))
        werte = dict(zip("XYZ", abbildung.punkt(punkt.spitze), strict=True))
        werte.update(stellung)
        if punkt.vorschub > 0:
            vorschub = float(punkt.vorschub)
        if not punkt.eilgang and vorschub > 0:
            if g93:
                zeit = 0.0
                if davor is not None:
                    zeit = math.dist(davor[0], bezugspunkt(punkt, bezug)) / vorschub
                    for k in stellung:
                        winkel = abs(stellung[k] - davor[1][k])
                        zeit = max(zeit, winkel / drehen.get(k, vorschub))  # unbekannt: 1° wie 1 mm
                werte["F"] = 1.0 / max(zeit, KUERZESTE_ZEIT)
            elif punkt.vorschub > 0:
                werte["F"] = vorschub
        drehend = (
            g93
            and punkt.eilgang
            and davor is not None
            and any(abs(stellung[k] - davor[1][k]) > 1e-9 for k in stellung)
        )
        if drehend:
            zeit = math.dist(davor[0], bezugspunkt(punkt, bezug)) / eil_linear
            for k in stellung:
                winkel = abs(stellung[k] - davor[1][k])
                zeit = max(zeit, winkel / eil_dreh.get(k, eil_linear))
            werte["F"] = 1.0 / max(zeit, KUERZESTE_ZEIT)
        befehle.append(Path.Command("G0" if punkt.eilgang and not drehend else "G1", werte))
        if materialdaten is not None:
            materialdaten.append((punkt.eilgang, vorschub))
        if verbindungen is not None:
            verbindungen.append(punkt.verbindung)
        davor = (bezugspunkt(punkt, bezug), stellung)
    if g93:
        befehle.append(Path.Command("G94"))
        if materialdaten is not None:
            materialdaten.append((True, 0.0))
        if verbindungen is not None:
            verbindungen.append(False)
    return befehle


RUECKZUG_RAND = 1.0  # mm – so weit vor der Achsgrenze endet der Rückzug


def rueckzug_z(maschine, hoehe):
    """Z im Programm, auf das die Spitze vor jedem Schwenk der Rundachsen zurückfährt: bis an
    die Grenze der Linearachse, die das Werkzeug vom Werkstück wegführt – so weit die Maschine
    kann –, mindestens `hoehe` (schwenken.schwenkhoehe über dem Rohteil, oder None). Die
    Schwenkhöhe allein sieht nur das Rohteil: An der G550 mit dem Teil flach auf dem Rundtisch
    schwenkte A von 80° zurück auf 0, während die Spindel 58 mm über dem Teil stand – Z-Schlitten
    und Spindel trafen Rundtisch und Wiege (B-015, Manuel, 2026-10-10: „fahr so, dass nichts
    kollidiert“). Ohne Grenze an der Achse bleibt `hoehe`."""
    try:
        loesung, _ = maschine.pruefung.loeser(
            maschine.aufnahme, maschine.laenge, maschine.nullpunkt
        )({})
    except (AttributeError, TypeError, ValueError):
        return hoehe
    if loesung is None:
        return hoehe
    unten, oben = loesung.werte(0.0, 0.0, 0.0), loesung.werte(0.0, 0.0, 1.0)
    ergebnis = hoehe
    for achse, s0, s1 in zip(maschine.linear, unten, oben, strict=True):
        steigung = s1 - s0
        if abs(steigung) < 1e-9:
            continue
        minimum, maximum = maschine.pruefung.verfahren.grenzen(achse)
        grenze = maximum if steigung > 0 else minimum
        if grenze is None:
            continue
        z = (grenze - s0) / steigung - RUECKZUG_RAND
        ergebnis = z if ergebnis is None else max(ergebnis, z)
    return ergebnis


def befehle_auf_maschine(
    maschine,
    punkte,
    rohteil=None,
    bezug=0.0,
    toleranz=TOLERANZ,
    materialdaten=None,
    verbindungen=None,
):
    """Die Sätze einer Bahn mit Achse (Punkt …), wie `maschine` sie fährt: ohne TCPM, die
    Rundachsen je Punkt, der Vorschub in G93, auch Eilgänge mit drehender Achse verdichtet
    (programm_ohne_tcpm) – davor auf die Schwenkhöhe (über dem Raum, den das Rohteil `rohteil`
    beim Schwenken überstreicht; schwenken.schwenkhoehe), geschwenkt und über den ersten Punkt;
    danach wieder hinauf und die Rundachsen auf 0 (wie 3+2 ohne Zyklus; endlose auf das nächste
    Vielfache von 360°). Hinauf heißt bis an die Achsgrenze (rueckzug_z), mindestens die
    Schwenkhöhe. ValueError mit einem Satz wie programm_ohne_tcpm."""
    import Path

    if not punkte:
        return []
    saetze = programm_ohne_tcpm(
        maschine,
        punkte,
        g93=True,
        toleranz=toleranz,
        bezug=bezug,
        eilgaenge=True,
        materialdaten=materialdaten,
        verbindungen=verbindungen,
    )
    if not maschine.rundachsen:
        return saetze  # Feste Werkzeugachse: kein zusätzlicher Schwenkweg in globalem Z.
    bewegt = [b for b in saetze if b.Name in ("G0", "G1")]
    erster, letzter = bewegt[0].Parameters, bewegt[-1].Parameters
    rundachsen = [a.buchstabe for a in maschine.rundachsen]
    rund_anfang = {b: float(erster[b]) for b in rundachsen}
    rund_ende = {b: float(letzter[b]) for b in rundachsen}
    hoehe = None
    if rohteil is not None and not rohteil.isNull():
        hoehe = max(
            sw.schwenkhoehe(rohteil, maschine.abbildung, rund_anfang),
            sw.schwenkhoehe(rohteil, maschine.abbildung, rund_ende),
        )
    hoehe = rueckzug_z(maschine, hoehe)  # vor jedem Schwenk bis an die Achsgrenze (B-015)
    davor = []
    if hoehe is not None:
        davor.append(Path.Command("G0", {"Z": max(hoehe, float(erster["Z"]))}))
    davor.append(Path.Command("G0", dict(rund_anfang)))
    if hoehe is not None:
        davor.append(Path.Command("G0", {"X": float(erster["X"]), "Y": float(erster["Y"])}))
    danach = []
    if hoehe is not None:
        danach.append(Path.Command("G0", {"Z": max(hoehe, float(letzter["Z"]))}))
    danach.append(
        Path.Command(
            "G0",
            {a.buchstabe: _grundstellung(a, rund_ende[a.buchstabe]) for a in maschine.rundachsen},
        )
    )
    if materialdaten is not None:
        materialdaten[:] = [(True, 0.0)] * len(davor) + materialdaten + [(True, 0.0)] * len(danach)
    if verbindungen is not None:
        verbindungen[:] = [False] * len(davor) + verbindungen + [False] * len(danach)
    return davor + saetze + danach


TCPM_EIN = "TCPM_EIN"  # Satz-Namen für den Postprozessor: hier schaltet er TCPM ein bzw. aus
TCPM_AUS = "TCPM_AUS"


def befehle_mit_tcpm(maschine, punkte, rohteil=None, bezug=0.0, toleranz=TOLERANZ, bei_null=False):
    """Die Sätze einer Bahn mit Achse (Punkt …) für eine Steuerung mit TCPM (Siemens TRAORI,
    Fanuc G43.4, Haas G234 – Manuel, 2026-10-03: „TCPM später als Haken“) – Path.Command und
    (Name, Werte) für die Marken TCPM_EIN und TCPM_AUS: wie
    befehle_auf_maschine auf die Schwenkhöhe und geschwenkt, dann TCPM_EIN, die Spitze im
    Werkstück (Grundjob) mit den Rundachsen je Punkt, F in mm/s (kein G93 – die Steuerung führt
    die Spitze mit F), TCPM_AUS, hinauf und die Rundachsen in die Grundstellung. Verdichtet nur,
    wo der Punkt `bezug` über der Spitze zwischen zwei Sätzen weiter als `toleranz` von seiner
    Geraden abwiche (abweichung mit tcpm). Ein Eilgang, in dem sich eine Rundachse dreht, wird G1
    mit der Eilganggeschwindigkeit: Im Eilgang hält keine Steuerung sicher die Spitze (Haas: „Tool
    tip position is not maintained during rapid rotary moves“). `bei_null`: TCPM bei Rundachsen
    auf 0 einschalten (Haas: „The rotary axes must be at 0 before commanding G234“) – davor über
    dem ersten Punkt auf der Schwenkhöhe, danach im G1 auf ihn hinab und auf seine Stellung.
    ValueError mit einem Satz wie rundachsen_entlang."""
    import Path

    if not punkte:
        return []
    rund = rundachsen_entlang(maschine, [p.achse for p in punkte])
    if toleranz:
        punkte, rund = verdichtet(maschine, punkte, rund, toleranz, bezug, True, tcpm=True)
    rundachsen = [a.buchstabe for a in maschine.rundachsen]
    eil = eilganggeschwindigkeit(maschine)  # mm/s
    saetze, vorschub, davor, stellung_davor = [], 0.0, None, None
    for punkt, stellung in zip(punkte, rund, strict=True):
        werte = dict(zip("XYZ", (float(v) for v in punkt.spitze), strict=True))
        werte.update(stellung)
        if punkt.vorschub > 0:
            vorschub = float(punkt.vorschub)
        lage = tuple(round(werte[k], 4) for k in ("X", "Y", "Z", *rundachsen))
        if lage == davor and not punkt.eilgang:
            continue  # dieselbe Spitze, dieselbe Stellung – nichts zu fahren
        davor = lage
        dreht = stellung_davor is not None and any(
            abs(stellung[k] - stellung_davor[k]) > 1e-9 for k in stellung
        )
        stellung_davor = stellung
        if punkt.eilgang and dreht:
            werte["F"] = eil
            saetze.append(Path.Command("G1", werte))
            continue
        if not punkt.eilgang and vorschub > 0:
            werte["F"] = vorschub
        saetze.append(Path.Command("G0" if punkt.eilgang else "G1", werte))
    rund_anfang = {b: float(rund[0][b]) for b in rundachsen}
    rund_ende = {b: float(rund[-1][b]) for b in rundachsen}
    # Ohne TCPM davor und danach: die Lage im Programm wie befehle_auf_maschine sie schreibt.
    erster = _im_programm(maschine, punkte[0], rund[0])
    letzter = _im_programm(maschine, punkte[-1], rund[-1])
    hoehe = None
    if rohteil is not None and not rohteil.isNull():
        hoehe = max(
            sw.schwenkhoehe(rohteil, maschine.abbildung, rund_anfang),
            sw.schwenkhoehe(rohteil, maschine.abbildung, rund_ende),
        )
    hoehe = rueckzug_z(maschine, hoehe)  # vor jedem Schwenk bis an die Achsgrenze (B-015)
    davor = []
    if bei_null:
        # Rundachsen auf 0: die Lage im Programm ist die im Werkstück – über dem ersten Punkt.
        null = dict.fromkeys(rundachsen, 0.0)
        spitze = punkte[0].spitze
        oben = max(hoehe if hoehe is not None else spitze[2], float(spitze[2]))
        davor.append(Path.Command("G0", {"Z": oben}))
        davor.append(Path.Command("G0", null))
        davor.append(Path.Command("G0", {"X": float(spitze[0]), "Y": float(spitze[1])}))
        start = dict(saetze[0].Parameters)
        start["F"] = eil
        saetze[0] = Path.Command("G1", start)  # unter TCPM hinab und auf die Stellung
    else:
        if hoehe is not None:
            davor.append(Path.Command("G0", {"Z": max(hoehe, erster[2])}))
        davor.append(Path.Command("G0", dict(rund_anfang)))
        if hoehe is not None:
            davor.append(Path.Command("G0", {"X": erster[0], "Y": erster[1]}))
    danach = []
    if hoehe is not None:
        danach.append(Path.Command("G0", {"Z": max(hoehe, letzter[2])}))
    danach.append(
        Path.Command(
            "G0",
            {a.buchstabe: _grundstellung(a, rund_ende[a.buchstabe]) for a in maschine.rundachsen},
        )
    )
    # Die Marken als (Name, Werte) – ein Path.Command nimmt nur G-Code; der Postprozessor liest
    # beides (postprozessor._befehl).
    return davor + [(TCPM_EIN, {})] + saetze + [(TCPM_AUS, {})] + danach


def _im_programm(maschine, punkt, stellung):
    """(X, Y, Z) des Punkts im Programm ohne TCPM bei dieser Stellung der Rundachsen."""
    abbildung = maschine.abbildung(stellung)
    if abbildung is None:
        raise ValueError(tr("si.fehler.linear"))
    return tuple(float(v) for v in abbildung.punkt(punkt.spitze))


def _grundstellung(achse, wert):
    """Wohin die Rundachse am Ende zurück soll: 0 – eine endlose Achse (ohne Grenzen) auf das
    Vielfache von 360°, das ihr am nächsten liegt; dort steht sie wie bei 0 (die Flanke dreht C
    rundherum, zurück wäre eine ganze Umdrehung umsonst)."""
    if achse.minimum is None and achse.maximum is None:
        return 360.0 * round(wert / 360.0)
    return 0.0
