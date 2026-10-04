# SPDX-License-Identifier: LGPL-2.1-or-later
"""5 Achsen simultan, S2: der Kugelfräser angestellt (W-015, Spezifikation Strategien 16.3;
Manuel, 2026-10-04: „Ja, so bauen“ – nur so viel wie nötig, eine Rundachse).

Senkrecht schneidet ein Kugelfräser auf flachen Stellen mit der Spitze – dort ist die
Schnittgeschwindigkeit 0. Angestellt schneidet er mit dem Umfang. Die Kugel bleibt dabei, wo sie
ist: Nur die Achse kippt um ihre Mitte. Die Bahn des 3D-Schlichtens gilt also weiter, und mit ihr
alles, was sie liest – Restmaterial, Materialstand, das Bild in FreeCAD, ein Programm für eine
3-Achs-Maschine. Die Operation speichert ihre Bahn wie senkrecht und je Satz die Werkzeugachse
(`Werkzeugachsen`, achsen()); erst „Auf der Maschine prüfen“ und das Programm setzen die Spitze
um (Mitte − R · Achse) und rechnen die Rundachsen (befehle(): simultan.programm_ohne_tcpm, die
Mitte der Kugel auf der Geraden, G93).

**Wie weit:** nur so viel wie nötig – zwischen Achse und Flächennormale am Berührpunkt
mindestens `winkel` (WINKEL); ist die Fläche steiler, bleibt die Achse senkrecht. **Wohin:** nur
in einer Ebene – die Achse kippt um X oder um Y des Jobs (`um`), an der Maschine mit einer
Rundachse, die andere steht (kippachse()). An der Kuppel aus dem Versuch 6 % mehr Zeit als
senkrecht; Richtung frei kostete 136 %, fest voreilend 540 % (Spezifikation 16.3). Die Neigung
ändert sich längs der Bahn höchstens um AENDERUNG je mm und bleibt so nah an 0 wie erlaubt
(neigungen()); muss sie schneller, springt sie – die Kugel bleibt stehen, die Achse dreht um
ihre Mitte.

**Eilgänge:** Ein Rückzug nach oben behält die Achse; sonst fährt der Eilgang schon mit der
Achse des nächsten Schnitts – die Achse dreht sich über dem Teil, auf der sicheren Höhe (die
Spitze bleibt dabei auf der Geraden, simultan.verdichtet mit `eilgaenge`). Vor dem ersten Satz
fährt die Maschine auf die Schwenkhöhe, schwenkt und fährt darüber; am Ende wieder hinauf und
die Rundachsen auf 0 – wie 3+2 ohne Zyklus.

Läuft ohne Oberfläche.
"""

import math

import FreeCAD

from . import bahn as bn
from . import simultan as si
from .sprache import tr

WINKEL = 15.0  # Grad – so weit steht die Achse mindestens von der Flächennormale weg
LAENGE = 0.5  # mm – so lang ist ein Satz im Vorschub höchstens (eine Achse je Satz)
AENDERUNG = 2.0  # Grad je mm – so schnell ändert sich die Neigung längs der Bahn höchstens
KONTAKT = 0.05  # mm – so nah muss die Kugel dem Teil sein, damit seine Fläche zählt
UM = ("X", "Y")  # um diese Achse des Jobs kippt die Werkzeugachse
SENKRECHT = (0.0, 0.0, 1.0)
KEINE = (0.0, 0.0, 0.0)  # in `Werkzeugachsen`: ein Satz ohne Bewegung
BEWEGUNG = ("G0", "G00", "G1", "G01")
EILGANG = ("G0", "G00")


# --- Die Bahn ---------------------------------------------------------------------------------


def gerade(punkte, laenge=LAENGE):
    """[bahn.Punkt] – Bögen als Geraden, Vorschubsätze in Stücken von höchstens `laenge`: Ein
    Satz hat eine Werkzeugachse, längs der Bahn ändert sie sich."""
    if not punkte:
        return []
    ergebnis = [punkte[0]]
    for von, nach in zip(punkte, punkte[1:], strict=False):
        if nach.eilgang:
            ergebnis.append(nach)
            continue
        weg = bn.weg(von, nach)
        n = max(1, int(math.ceil(weg / laenge - 1e-9)))
        if nach.bogen is not None:
            mx, my, uhr = nach.bogen
            r = math.hypot(von.x - mx, von.y - my)
            w = bn.winkel(von, nach)
            a0 = math.atan2(von.y - my, von.x - mx)
        for i in range(1, n + 1):
            t = i / n
            if i == n:
                x, y = nach.x, nach.y
            elif nach.bogen is not None:
                a = a0 - w * t if uhr else a0 + w * t
                x, y = mx + r * math.cos(a), my + r * math.sin(a)
            else:
                x, y = von.x + (nach.x - von.x) * t, von.y + (nach.y - von.y) * t
            ergebnis.append(
                bn.Punkt(
                    False,
                    x,
                    y,
                    von.z + (nach.z - von.z) * t,
                    eintauchen=nach.eintauchen,
                    anteil=nach.anteil,
                )
            )
    return ergebnis


# --- Die Achse --------------------------------------------------------------------------------


def gekippt(neigung, um):
    """Die Werkzeugachse (x, y, z), um `neigung` Grad um X oder Y des Jobs gekippt."""
    a = math.radians(neigung)
    if um == "Y":
        return (math.sin(a), 0.0, math.cos(a))
    return (0.0, -math.sin(a), math.cos(a))


def verboten(normale, um, winkel=WINKEL):
    """(von, bis) in Grad: Neigungen um `um`, bei denen die Achse der Flächennormale näher steht
    als `winkel` – None, wenn jede passt (die Fläche fällt quer zur Kippebene steil genug)."""
    nx, ny, nz = normale
    quer = nx if um == "Y" else -ny  # die Normale in Richtung des Kippens
    rho = math.hypot(quer, nz)
    c = math.cos(math.radians(winkel))
    if rho <= c:
        return None
    phi = math.degrees(math.atan2(quer, nz))
    delta = math.degrees(math.acos(c / rho))
    return (phi - delta, phi + delta)


def neigungen(wege, verbote, aenderung=AENDERUNG):
    """[Grad] je Stelle: so nah an 0, wie es geht – außerhalb ihres Verbots (`verbote`: (von, bis)
    oder None) und von der Stelle davor (`wege`: mm bis hierher) aus höchstens `aenderung` je mm.
    Geht das nicht, die Grenze des Verbots, die der Neigung davor am nächsten liegt (ein
    Sprung)."""
    ergebnis = []
    davor = 0.0
    for weg, verbot in zip(wege, verbote, strict=True):
        spiel = aenderung * weg
        unten, oben = davor - spiel, davor + spiel
        neigung = min(max(0.0, unten), oben)
        if verbot is not None and verbot[0] < neigung < verbot[1]:
            im_spiel = [g for g in verbot if unten - 1e-9 <= g <= oben + 1e-9]
            if im_spiel:
                neigung = min(im_spiel, key=abs)
            else:
                neigung = min(verbot, key=lambda g: (abs(g - davor), abs(g)))
        ergebnis.append(neigung)
        davor = neigung
    return ergebnis


def normalen(form, spitzen, radius, aufmass=0.0, kontakt=KONTAKT):
    """[(x, y, z) oder None] – je Spitze der Kugel (senkrecht, Radius `radius`) die Normale der
    Fläche, wo sie das Teil `form` berührt; None, wo sie es nicht berührt (mehr als `kontakt`
    weg – über dem Teil). `aufmass`: so viel bleibt stehen, die Kugel berührt um es weiter
    außen."""
    import Part

    ergebnis = []
    for x, y, z in spitzen:
        mitte = FreeCAD.Vector(x, y, z + radius)
        try:
            abstand, paare, _info = form.distToShape(Part.Vertex(mitte))
        except Exception:  # eine Form, mit der OpenCascade nicht rechnen kann: senkrecht
            ergebnis.append(None)
            continue
        if not paare or abstand < 1e-9 or abstand > radius + aufmass + kontakt:
            ergebnis.append(None)
            continue
        n = mitte - paare[0][0]
        n.normalize()
        ergebnis.append((n.x, n.y, n.z))
    return ergebnis


def achsen(befehle, form, radius, aufmass=0.0, um="X", winkel=WINKEL, aenderung=AENDERUNG):
    """[(x, y, z)] je Befehl (Path.Command, senkrecht gerechnet): die Werkzeugachse im Job –
    KEINE bei einem Satz ohne Bewegung. Im Vorschub aus der Fläche am Berührpunkt (verboten,
    neigungen); ein Eilgang nach oben behält die Achse davor, jeder andere nimmt die des nächsten
    Vorschubs."""
    stellen = []  # (Index des Befehls, Punkt, Eilgang)
    stand = [None, None, None]
    for i, befehl in enumerate(befehle):
        name = befehl.Name.upper()
        if name not in BEWEGUNG:
            continue
        werte = befehl.Parameters
        stand = [float(werte[k]) if k in werte else stand[j] for j, k in enumerate("XYZ")]
        if None not in stand:
            stellen.append((i, tuple(stand), name in EILGANG))
    vorschub = [s for s in stellen if not s[2]]
    flaeche = normalen(form, [p for _i, p, _e in vorschub], radius, aufmass)
    wege, davor = [], None
    for _i, p, _e in vorschub:
        wege.append(math.dist(davor, p) if davor is not None else 0.0)
        davor = p
    verbote = [verboten(n, um, winkel) if n is not None else None for n in flaeche]
    je_satz = {
        i: gekippt(w, um)
        for (i, _p, _e), w in zip(vorschub, neigungen(wege, verbote, aenderung), strict=True)
    }
    ergebnis = [KEINE] * len(befehle)
    letzte, punkt_davor = None, None
    naechste = [None] * len(stellen)  # je Stelle die Achse des nächsten Vorschubs
    kommend = None
    for k in range(len(stellen) - 1, -1, -1):
        i, _p, eilgang = stellen[k]
        if not eilgang:
            kommend = je_satz[i]
        naechste[k] = kommend
    for k, (i, p, eilgang) in enumerate(stellen):
        if not eilgang:
            achse = je_satz[i]
        elif letzte is not None and _nach_oben(punkt_davor, p):
            achse = letzte
        else:
            achse = naechste[k] or letzte or SENKRECHT
        ergebnis[i] = achse
        letzte, punkt_davor = achse, p
    return ergebnis


def _nach_oben(von, nach):
    """Fährt der Satz `von` → `nach` nur hinauf (X, Y bleiben)?"""
    return (
        von is not None
        and abs(von[0] - nach[0]) < 1e-6
        and abs(von[1] - nach[1]) < 1e-6
        and nach[2] >= von[2]
    )


def kippachse(maschine):
    """„X“ oder „Y“: um welche Achse des Jobs die Werkzeugachse an `maschine` (schwenken.Maschine)
    mit einer Rundachse kippt – die erste, die das Werkzeug aus der Senkrechten neigt. None,
    wenn keine es tut (keine 5-Achs-Maschine)."""
    loesungen = maschine.loese(FreeCAD.Vector(*SENKRECHT))
    if not loesungen:
        return None
    grund = dict(loesungen[0])
    for achse in maschine.rundachsen:
        versuch = dict(grund)
        versuch[achse.buchstabe] = grund[achse.buchstabe] + 1.0
        d = maschine.richtung(versuch)
        if math.hypot(d.x, d.y) > 1e-3:
            return "X" if abs(d.y) >= abs(d.x) else "Y"
    return None


# --- Die Operation ----------------------------------------------------------------------------


def ist_angestellt(op):
    """Hat die Operation Werkzeugachsen (eine Bahn mit angestelltem Kugelfräser)?"""
    return bool(getattr(op, "Anstellen", False)) and bool(getattr(op, "Werkzeugachsen", None))


def radius_von(op):
    """Der Radius des Kugelfräsers der Operation – None, wenn er keiner ist."""
    from . import vierachs_operation as vo

    tc = getattr(op, "ToolController", None)
    form = vo.form_des_controllers(tc) if tc is not None else None
    if form is None or not form.nur_kugel:
        return None
    return float(form.radius)


def punkte(befehle, achsen_je_satz, radius):
    """[simultan.Punkt] – die Sätze (senkrecht gerechnet) mit ihren Achsen: die Spitze um die
    Mitte der Kugel gekippt (Mitte − R · Achse). Sätze, bevor X, Y und Z bekannt sind (der übliche
    erste „G0 Z…“), fallen weg – davor fährt die Maschine auf die Schwenkhöhe."""
    ergebnis = []
    stand = [None, None, None]
    achse = SENKRECHT
    for befehl, neu in zip(befehle, achsen_je_satz, strict=True):
        name = befehl.Name.upper()
        if name not in BEWEGUNG:
            continue
        werte = befehl.Parameters
        stand = [float(werte[k]) if k in werte else stand[j] for j, k in enumerate("XYZ")]
        if tuple(neu) != KEINE:
            achse = tuple(neu)
        if None in stand:
            continue
        mitte = (stand[0], stand[1], stand[2] + radius)
        spitze = tuple(m - radius * a for m, a in zip(mitte, achse, strict=True))
        ergebnis.append(
            si.Punkt(spitze, achse, eilgang=name in EILGANG, vorschub=float(werte.get("F", 0.0)))
        )
    return ergebnis


def befehle(op, maschine, rohteil=None):
    """Die Sätze der Operation, wie `maschine` (schwenken.Maschine) sie fährt: die Spitze um die
    Mitte der Kugel gekippt (punkte), die Mitte auf der Geraden (simultan.befehle_auf_maschine
    mit dem Radius als Bezug; `rohteil` ohne: das des Jobs). ValueError mit einem Satz, wenn es
    nicht geht."""
    if rohteil is None:
        rohteil = rohteil_von(op)
    radius = radius_von(op)
    if radius is None:
        raise ValueError(tr("an.fehler.kugel", operation=op.Label))
    alle = list(op.Path.Commands)
    achsen_je_satz = [tuple(v) for v in op.Werkzeugachsen]
    if len(achsen_je_satz) != len(alle):
        raise ValueError(tr("an.fehler.veraltet", operation=op.Label))
    return si.befehle_auf_maschine(maschine, punkte(alle, achsen_je_satz, radius), rohteil, radius)


def rohteil_von(op):
    """Die Form des Rohteils im Job der Operation – None ohne."""
    for gruppe in op.InList:
        for job in [gruppe, *gruppe.InList]:
            operationen = getattr(job, "Operations", None)
            if operationen is not None and op in getattr(operationen, "Group", []):
                return getattr(getattr(job, "Stock", None), "Shape", None)
    return None
