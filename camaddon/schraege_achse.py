# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die schräge Achse (W-001, Abschnitt 7c): Winkel messen und umrechnen.

Bei vielen Schrägbett-Drehmaschinen fährt der Y-Schlitten schräg zum
X-Schlitten. Das NC-Programm bleibt trotzdem rechtwinklig; die Steuerung
rechnet es auf beide Schlitten um (Siemens TRAANG, Fanuc Angular Axis
Control). Für ein Y im Programm fahren dann beide:

    vom Programm zu den Schlitten      von den Schlitten zum Programm
    Y1 = Y / cos α                     Y = Y1 · cos α
    X1 = X − Y · tan α                 X = X1 + Y1 · sin α

α ist der Winkel, um den die schräge Achse (hier Y1) aus dem rechten Winkel
zur ausgleichenden (X1) gekippt ist – positiv, wenn sie zu deren Plus-Seite
kippt. Er steht nur in der Baugruppe, in der Richtung der Gelenke; dieses
Modul misst ihn dort und stellt ihn dort ein (drehe_fuehrung). Im
Maschinenobjekt steht nur, welche Achsen es sind (maschine.Transformation).

Gerechnet wird mit der Richtung, in die das Werkzeug gegenüber dem
Werkstück fährt: Eine Achse im Tisch bewegt das Werkstück, für das Werkzeug
also andersherum.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import FreeCAD

from . import einheiten
from . import kette as kette_modul
from . import maschine as m
from . import verfahren as vf
from .kette import HINWEIS, LINEAR, meldung
from .werkstoffe import mit_dezimalzeichen

# Ab diesem Winkel (Grad) fahren beide Schlitten fast in dieselbe Richtung –
# daraus lässt sich kein rechtwinkliges Y mehr rechnen (cos α → 0).
GROESSTER_WINKEL = 89.0
# Darunter (Grad) stehen zwei Achsen rechtwinklig – Rundungsreste der Baugruppe.
# Ab hier zeigt der Dialog mindestens 0,1°.
RECHTWINKLIG_BIS = 0.05


@dataclass(eq=False)
class Anlegen:
    """Bezug des Hinweises „steht schräg“: Ein Klick darauf legt diese schräge Achse an."""

    schraeg: object  # Betriebsart, die schräg fährt
    ausgleich: object  # Betriebsart, die ausgleicht


def schlitten_aus_programm(alpha, x, y):
    """(x1, y1): wohin die Schlitten fahren, damit das Werkzeug im Programm bei (x, y) steht.

    `alpha` in Grad; x, y, x1, y1 sind Wege ab der Stellung 0 der Gelenke.
    """
    winkel = math.radians(alpha)
    return x - y * math.tan(winkel), y / math.cos(winkel)


def programm_aus_schlitten(alpha, x1, y1):
    """(x, y): wo das Werkzeug im Programm steht, wenn die Schlitten bei (x1, y1) stehen."""
    winkel = math.radians(alpha)
    return x1 + y1 * math.sin(winkel), y1 * math.cos(winkel)


def achsen(kette, trafo):
    """(schräge, ausgleichende) Achse der Kette zur schrägen Achse `trafo` – oder None,
    wenn eine fehlt oder keine Linearachse ist."""
    paar = (_linearachse(kette, trafo.Schraeg), _linearachse(kette, trafo.Ausgleich))
    return None if None in paar else paar


def winkel(kette, maschine, trafo):
    """α der schrägen Achse `trafo` in Grad, gemessen in der Baugruppe.

    None, wenn eine der beiden Achsen fehlt oder keine Linearachse der Kette ist.
    """
    return winkel_zwischen(kette, maschine, trafo.Schraeg, trafo.Ausgleich)


def winkel_zwischen(kette, maschine, schraeg, ausgleich):
    """α zwischen zwei Betriebsarten: wie weit `schraeg` aus dem rechten Winkel zu
    `ausgleich` gekippt ist, in Grad (−90 … 90). None, wenn eine keine Linearachse ist."""
    achsen = [_linearachse(kette, ba) for ba in (schraeg, ausgleich)]
    if None in achsen:
        return None
    rollen = m.rollen(kette, maschine)[0]
    s, a = (_richtung(achse, rollen) for achse in achsen)
    return math.degrees(math.asin(max(-1.0, min(1.0, s.dot(a)))))


class Programm:
    """X und Y des Programms über einer schrägen Achse – für „Maschine verfahren“.

    Die Stellungen zählen wie an den Gelenken, ab Stellung 0, in mm. X zeigt
    in Richtung der ausgleichenden Achse, Y rechtwinklig dazu; die Schlitten
    fahren nach der Rechnung oben. `verfahren` ist ein verfahren.Verfahren
    derselben Assembly.
    """

    def __init__(self, verfahren, maschine, trafo):
        kette = verfahren.kette
        self.verfahren = verfahren
        self.trafo = trafo
        self.alpha = winkel(kette, maschine, trafo)
        self.schraeg, self.ausgleich = achsen(kette, trafo)

    @staticmethod
    def moeglich(verfahren, maschine, trafo):
        """Lässt sich mit dieser schrägen Achse im Programm fahren – beide Achsen da, α gültig?"""
        alpha = winkel(verfahren.kette, maschine, trafo)
        return alpha is not None and abs(alpha) <= GROESSTER_WINKEL

    def stellung(self):
        """(x, y) im Programm, aus den Stellungen der beiden Schlitten."""
        return programm_aus_schlitten(
            self.alpha,
            self.verfahren.stellung(self.ausgleich),
            self.verfahren.stellung(self.schraeg),
        )

    def schlitten(self):
        """(x1, y1): die Stellungen der ausgleichenden und der schrägen Achse."""
        return self.verfahren.stellung(self.ausgleich), self.verfahren.stellung(self.schraeg)

    def setze(self, x, y):
        """Fährt das Werkzeug auf (x, y) im Programm – so weit die Schlitten kommen.

        Die Schlitten fahren auf der Geraden vom jetzigen Punkt zum Ziel. Stößt
        einer an eine Grenze seines Gelenks, halten beide dort – wie an der
        Maschine. Gibt (x, y, anschlag) zurück: wo das Werkzeug jetzt steht und
        (Achse, Grenze), an der es hielt, sonst None.
        """
        von = self.schlitten()
        nach = schlitten_aus_programm(self.alpha, x, y)
        anteil, anschlag = 1.0, None  # welcher Teil des Wegs geht, und woran es hält
        for achse, start, ziel in zip((self.ausgleich, self.schraeg), von, nach, strict=True):
            if ziel == start:
                continue  # fährt nicht – auch nicht, wenn es schon außerhalb stand
            for grenze in _ueberfahren(achse, ziel):
                t = max((grenze - start) / (ziel - start), 0.0)
                if t < anteil:
                    anteil, anschlag = t, (achse, grenze)
        x1, y1 = (start + anteil * (ziel - start) for start, ziel in zip(von, nach, strict=True))
        self.verfahren.setze(self.ausgleich, x1)
        self.verfahren.setze(self.schraeg, y1)
        return (*self.stellung(), anschlag)

    def bereich(self):
        """((x_min, x_max), (y_min, y_max)) im Programm – so weit die Achsen überhaupt
        kommen; None, wo ein Gelenk keine Grenze hat. Wie weit es gerade geht, hängt
        von der anderen Achse ab (ein Parallelogramm, kein Rechteck)."""
        a = math.radians(self.alpha)
        y1 = (self.schraeg.minimum, self.schraeg.maximum)
        x1 = (self.ausgleich.minimum, self.ausgleich.maximum)
        if None in y1:
            return (None, None), (None, None)
        y = (y1[0] * math.cos(a), y1[1] * math.cos(a))
        quer = sorted(g * math.sin(a) for g in y1)
        x = (
            None if x1[0] is None else x1[0] + quer[0],
            None if x1[1] is None else x1[1] + quer[1],
        )
        return x, y


def drehe_fuehrung(assembly, kette, maschine, trafo, alpha):
    """Stellt die schräge Achse `trafo` auf `alpha` Grad – die Baugruppe folgt.

    Die Führung ihres Schiebegelenks dreht sich in der Ebene beider Achsen:
    Beide Koordinatensysteme des Gelenks drehen sich gleich, so behalten der
    Schlitten und alles darauf ihre Lage – der Revolver bleibt gerade –, nur
    die Fahrrichtung ändert sich (ausprobiert in 1.1.3 und im Wochen-Build,
    P-2026-09-26-65). Steht der Schlitten nicht auf 0, bleibt er auf seiner
    Stellung, nun entlang der neuen Richtung.

    Gibt die neu gelesene Kette zurück. ValueError, wenn `alpha` außerhalb von
    ±GROESSTER_WINKEL liegt oder eine der Achsen fehlt.
    """
    if abs(alpha) > GROESSTER_WINKEL:
        raise ValueError(f"Winkel {alpha} außerhalb von ±{GROESSTER_WINKEL}")
    vorher = winkel(kette, maschine, trafo)
    if vorher is None:
        raise ValueError("schräge Achse ohne zwei Linearachsen")
    schraeg, ausgleich = achsen(kette, trafo)
    rollen = m.rollen(kette, maschine)[0]
    # Um die Normale der Ebene beider Achsen; positiv kippt die schräge zur ausgleichenden hin.
    normale = _richtung(schraeg, rollen).cross(_richtung(ausgleich, rollen))
    normale.normalize()
    drehung = FreeCAD.Rotation(normale, alpha - vorher)

    stellung = vf.gelenkstellung(schraeg.gelenk, LINEAR)
    verschoben = abs(stellung) > 1e-9
    if verschoben:
        vf.Verfahren(assembly, kette).setze(schraeg, 0.0, grenzen=False)
    _drehe_gelenk(assembly, schraeg.gelenk, drehung)
    kette = kette_modul.lies_kette(assembly)
    if verschoben:
        vf.Verfahren(assembly, kette).setze(
            kette.achse_von(schraeg.gelenk), stellung, grenzen=False
        )
    return kette


def _drehe_gelenk(assembly, gelenk, drehung):
    """Dreht beide Koordinatensysteme eines Gelenks um `drehung`, jedes um seinen Ursprung.

    Der Versatz (Offset1/2) sitzt rechts am Koordinatensystem aus der Fläche:
    global = ohne Versatz · Versatz. Jede Änderung am Versatz löst vorab – mit
    einer Seite schon gedreht, der anderen noch nicht, rückt FreeCAD Teile
    (wie beim Bauen der Beispielmaschinen). Deshalb kommen sie jedes Mal zurück.
    """
    import UtilsAssembly

    teile = [
        o for o in assembly.Group if hasattr(o, "Placement") and o.TypeId != "Assembly::JointGroup"
    ]
    lagen = {teil: FreeCAD.Placement(teil.Placement) for teil in teile}
    for seite in (1, 2):
        jetzt = UtilsAssembly.getJcsGlobalPlc(
            getattr(gelenk, f"Placement{seite}"), getattr(gelenk, f"Reference{seite}")
        )
        ohne_versatz = jetzt * getattr(gelenk, f"Offset{seite}").inverse()
        ziel = FreeCAD.Placement(jetzt.Base, drehung.multiply(jetzt.Rotation))
        setattr(gelenk, f"Offset{seite}", ohne_versatz.inverse() * ziel)
        for teil, lage in lagen.items():
            teil.Placement = lage
    assembly.Document.recompute()


def linearachsen(maschine, kette):
    """Die Betriebsarten der Art Linear mit gültiger Achse in der Kette, nach NC-Namen."""
    return sorted(
        (ba for ba in m.betriebsarten(maschine) if _linearachse(kette, ba) is not None),
        key=lambda ba: m.name_von(ba).upper(),
    )


def vorschlag(maschine, kette):
    """Die Achsen für eine neue schräge Achse: (schräg, ausgleichend) – oder None, wenn
    es keine zwei Linearachsen gibt.

    Zuerst ein Paar, das schräg zueinander steht und noch keinen Eintrag hat
    (ohne_eintrag); sonst die ersten beiden Linearachsen. Ausgleichend ist
    die, deren Name im Alphabet vorn steht (X1 vor Y1).
    """
    offen = ohne_eintrag(maschine, kette)
    if offen:
        schraeg, ausgleich, _alpha = offen[0]
        return schraeg, ausgleich
    linear = linearachsen(maschine, kette)
    if len(linear) < 2:
        return None
    return linear[1], linear[0]


def ohne_eintrag(maschine, kette):
    """Linearachsen, die schräg zueinander stehen und noch keine schräge Achse haben:
    [(schräg, ausgleichend, α in Grad), …].

    Schräg heißt: weder rechtwinklig noch (fast) parallel. Ausgleichend ist die
    Achse, deren Name im Alphabet vorn steht (X1 vor Y1).
    """
    linear = linearachsen(maschine, kette)
    vergeben = {frozenset((t.Schraeg, t.Ausgleich)) for t in m.transformationen(maschine)}
    ergebnis = []
    for i, ausgleich in enumerate(linear):
        for schraeg in linear[i + 1 :]:
            if frozenset((schraeg, ausgleich)) in vergeben:
                continue
            alpha = winkel_zwischen(kette, maschine, schraeg, ausgleich)
            if RECHTWINKLIG_BIS <= abs(alpha) <= GROESSTER_WINKEL:
                ergebnis.append((schraeg, ausgleich, alpha))
    return ergebnis


def pruefe(maschine, kette):
    """Die Meldungen zu den schrägen Achsen, als fertige Sätze.

    Was an einer Betriebsart selbst nicht stimmt (Gelenk fehlt, falsche
    Gelenkart), meldet schon maschine.pruefe – hier nur, was die schräge
    Achse betrifft. Dazu ein Hinweis je Paar, das schräg steht und noch
    keinen Eintrag hat; ein Klick darauf legt ihn an (Bezug: Anlegen).
    """
    meldungen = []
    for schraeg, ausgleich, alpha in ohne_eintrag(maschine, kette):
        meldungen.append(
            meldung(
                "maschine.trafo_schraeg_erkannt",
                HINWEIS,
                bezug=Anlegen(schraeg, ausgleich),
                schraeg=m.name_von(schraeg),
                ausgleich=m.name_von(ausgleich),
                winkel=_winkel_text(alpha),
                name=m.programmname(schraeg),
            )
        )
    for trafo in m.transformationen(maschine):
        name = m.name_von(trafo)
        schraeg, ausgleich = trafo.Schraeg, trafo.Ausgleich
        if schraeg is None or ausgleich is None:
            meldungen.append(meldung("maschine.trafo_achse_fehlt", bezug=trafo, name=name))
            continue
        if schraeg == ausgleich:
            meldungen.append(
                meldung(
                    "maschine.trafo_gleiche_achse",
                    bezug=trafo,
                    name=name,
                    achse=m.name_von(schraeg),
                )
            )
            continue
        falsch = [ba for ba in (schraeg, ausgleich) if not _ist_linear(ba)]
        for ba in falsch:
            meldungen.append(
                meldung("maschine.trafo_nicht_linear", bezug=trafo, name=name, achse=m.name_von(ba))
            )
        if falsch:
            continue
        alpha = winkel(kette, maschine, trafo)
        if alpha is not None and abs(alpha) > GROESSTER_WINKEL:
            meldungen.append(
                meldung(
                    "maschine.trafo_parallel",
                    bezug=trafo,
                    name=name,
                    schraeg=m.name_von(schraeg),
                    ausgleich=m.name_von(ausgleich),
                )
            )
    return meldungen


def _ueberfahren(achse, ziel):
    """Die Grenzen der Achse, über die `ziel` hinausgeht (keine, eine)."""
    if achse.maximum is not None and ziel > achse.maximum:
        return [achse.maximum]
    if achse.minimum is not None and ziel < achse.minimum:
        return [achse.minimum]
    return []


def _winkel_text(alpha):
    """„30,0°“ mit dem gewählten Dezimalzeichen – für Sätze, die ohne Oberfläche entstehen."""
    zeichen = einheiten.gewaehltes_dezimalzeichen() or einheiten.PUNKT
    return mit_dezimalzeichen(f"{round(alpha, 1) + 0.0:.1f}°", zeichen)


def _ist_linear(ba):
    return m.ist_betriebsart(ba) and ba.Art == m.ART_LINEAR


def _linearachse(kette, ba):
    """Die Linearachse der Kette zu einer Betriebsart der Art Linear, sonst None."""
    if ba is None or not _ist_linear(ba) or ba.Gelenk is None:
        return None
    achse = kette.achse_von(ba.Gelenk)
    return achse if achse is not None and achse.art == LINEAR else None


def _richtung(achse, rollen):
    """Wohin das Werkzeug gegenüber dem Werkstück fährt, wenn die Stellung wächst.

    Eine Achse im Tisch bewegt das Werkstück – für das Werkzeug andersherum.
    Ohne Rolle (noch keine Aufnahmen) zählt sie wie eine im Kopf.
    """
    richtung = vf.plusrichtung(achse)
    return richtung * -1.0 if rollen.get(achse.gelenk) == m.TISCH else richtung
