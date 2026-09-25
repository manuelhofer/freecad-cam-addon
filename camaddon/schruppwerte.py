# SPDX-License-Identifier: LGPL-2.1-or-later
"""Schruppwerte planen (W-002, Stufe 3): so viel Span, wie Werkzeug und Maschine hergeben.

Der Gedanke ist der des dynamischen Fräsens: die ganze Schneide nutzen
(großes ap), schmal zustellen (kleines ae) und fz so weit anheben, dass der
Span trotzdem so dick wird wie gewünscht (Spandickenausgleich). Die Schneide
ist dann nur kurz im Material, der Verschleiß verteilt sich auf ihre ganze
Länge, und der Abtrag ist ein Vielfaches einer Vollnut.

Bei gleicher Spandicke wächst Q mit ae. Wie breit es wird, begrenzen deshalb
das Werkzeug – eine Obergrenze in % von D, wie sie die Hersteller für die
volle Schneidenlänge angeben – und die Maschine: Spindelleistung, höchste
Drehzahl, höchster Vorschub. `plane()` rechnet eine Reihe von ae durch, prüft
jede gegen diese Grenzen und schlägt die mit dem größten Q vor, die alle
einhält.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field

import FreeCAD

from . import maschine as maschine_modul
from . import schnittdaten as sd
from . import werkzeuge as wz

# ae in % von D, die der Planer durchrechnet; dazu die Grenze selbst.
STUFEN = (2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50)
# Übliche Obergrenze für ae bei voller Schneidenlänge, in % von D. Die
# Hersteller nennen meist 5 … 15 % – in Aluminium mehr, in Edelstahl, Titan
# und gehärtetem Stahl weniger.
AE_GRENZE = 10.0
# Anteil der Spindelleistung, der an der Schneide ankommt.
WIRKUNGSGRAD = 0.8
# Genauigkeit, mit der plane() das ae an der Leistungsgrenze sucht.
AE_SCHRITT = 0.01  # mm

# Werkzeuge, für die der Planer taugt: zylindrisch, am Umfang schneidend.
ARTEN = (wz.SCHAFTFRAESER, wz.TORUSFRAESER)

# Warum der Vorschlag nicht breiter ist – Schlüssel für die Oberfläche.
GRUND_AE = "ae"  # die Grenze in % von D
GRUND_LEISTUNG = "leistung"  # die Spindelleistung
GRUND_ENDE = "ende"  # die Reihe endet bei D/2 – breiter ist kein dynamisches Fräsen mehr


@dataclass
class Grenzen:
    """Was Werkzeug und Maschine erlauben; 0 heißt „keine Grenze bekannt“."""

    ae_prozent: float = AE_GRENZE  # ae höchstens so viel % von D, 0 = bis D/2
    drehzahl: float = 0.0  # U/min
    vorschub: float = 0.0  # mm/min, Bearbeitungsvorschub
    leistung: float = 0.0  # kW, Nennleistung der Spindel


@dataclass
class Stufe:
    """Eine Zeile des Plans: ein ae mit allem, was daraus folgt."""

    ae: float  # mm
    prozent: float  # ae in % von D
    fz: float  # mm – ausgeglichen, beim Vorschub-Anschlag gesenkt
    vf: float  # mm/min
    q: float  # cm³/min
    spandicke: float  # größte Spandicke, die sich tatsächlich ergibt, mm
    leistung: float = 0.0  # kW an der Schneide, 0 = unbekannt (kein kc1.1)
    drehmoment: float = 0.0  # Nm, 0 = unbekannt
    vorschub_begrenzt: bool = False  # vf auf den Höchstvorschub gesenkt, der Span wird dünner
    ueber_ae: bool = False  # breiter als die Grenze in % von D
    ueber_leistung: bool = False  # braucht mehr, als die Spindel hergibt
    an_grenze: bool = False  # keine feste Stufe: genau an der Grenze gesucht

    @property
    def erlaubt(self):
        return not self.ueber_ae and not self.ueber_leistung


@dataclass
class Plan:
    """Das Ergebnis von plane()."""

    n: float  # U/min, für alle Stufen gleich
    vc: float  # m/min, die sich ergibt – kleiner als gewünscht, wenn die Drehzahl begrenzt
    drehzahl_begrenzt: bool
    stufen: list = field(default_factory=list)
    beste: int = -1  # Index der vorgeschlagenen Stufe, -1 = keine
    grund: str = ""  # GRUND_…: warum nicht breiter

    @property
    def vorschlag(self):
        return self.stufen[self.beste] if self.beste >= 0 else None


def moeglich(werkzeug):
    """Taugt der Planer für dieses Werkzeug? Braucht einen Fräser mit D und z."""
    return werkzeug.art in ARTEN and werkzeug.durchmesser > 0 and werkzeug.schneiden > 0


# Einsätze, deren Werte der Planer als Ausgang nimmt – in dieser Reihenfolge.
SCHRUPP_ARTEN = (wz.DYNAMISCH, wz.VOLLNUT, wz.SCHRUPPEN)


def ausgangszeile(einsaetze, gewaehlt=None):
    """Die Zeile, aus der der Planer vorbelegt, oder None.

    Die gewählte, wenn sie schruppt und vc und fz hat – sonst die erste
    solche Zeile, dynamisches Schruppen vor Vollnut vor Schruppen. Eine
    Schlicht-Zeile hat eine Spandicke, die zum Schruppen nicht taugt.
    """

    def taugt(einsatz):
        return (
            einsatz is not None
            and einsatz.art in SCHRUPP_ARTEN
            and einsatz.vc > 0
            and einsatz.fz > 0
        )

    if taugt(gewaehlt):
        return gewaehlt
    for art in SCHRUPP_ARTEN:
        for einsatz in einsaetze:
            if einsatz.art == art and taugt(einsatz):
                return einsatz
    return gewaehlt


def vorgaben(werkzeug, einsatz):
    """(vc, Spandicke, ap) zum Vorbelegen des Planers aus einer Zeile der Tabelle.

    Die Spandicke ist die größte, die die Zeile tatsächlich ergibt – bei
    einer Vollnut fz, bei schmalem ae weniger. ap: bei einem dynamischen
    Einsatz das der Zeile, sonst die Vorlage für dynamisches Schruppen.
    """
    d = werkzeug.durchmesser
    vc = einsatz.vc if einsatz is not None else 0.0
    h = sd.spandicke_max(einsatz.fz, einsatz.ae, d) if einsatz is not None else 0.0
    if einsatz is not None and einsatz.art == wz.DYNAMISCH and einsatz.ap > 0:
        ap = einsatz.ap
    else:
        ap = wz.vorlage(werkzeug, wz.DYNAMISCH).ap
    return vc, round(h, 4), ap


def _stufe(werkzeug, ae, ap, h, n, grenzen, werkstoff):
    d, z = werkzeug.durchmesser, werkzeug.schneiden
    fz = sd.fz_fuer_spandicke(h, ae, d)
    vf = sd.vorschub(n, z, fz)
    begrenzt = grenzen.vorschub > 0 and vf > grenzen.vorschub
    if begrenzt:
        vf = grenzen.vorschub
        fz = vf / (n * z)
    q = sd.zeitspanvolumen(ae, ap, vf)
    stufe = Stufe(
        ae=ae,
        prozent=ae / d * 100.0,
        fz=fz,
        vf=vf,
        q=q,
        spandicke=sd.spandicke_max(fz, ae, d),
        vorschub_begrenzt=begrenzt,
    )
    if werkstoff is not None and werkstoff.kc11 > 0:
        kc = sd.spezifische_schnittkraft(
            sd.spandicke_mittel(fz, ae, d), werkstoff.kc11, werkstoff.mc
        )
        stufe.leistung = sd.schnittleistung(q, kc)
        stufe.drehmoment = stufe.leistung * 9550.0 / n
    stufe.ueber_ae = grenzen.ae_prozent > 0 and stufe.prozent > grenzen.ae_prozent + 1e-9
    stufe.ueber_leistung = grenzen.leistung > 0 and (
        stufe.leistung > grenzen.leistung * WIRKUNGSGRAD + 1e-9
    )
    return stufe


def plane(werkzeug, vc, spandicke, ap, grenzen, werkstoff=None):
    """Rechnet die Stufen durch und schlägt die mit dem größten Q vor, die alle Grenzen einhält.

    `werkstoff` (mit kc1.1) braucht es nur für Leistung und Drehmoment; ohne
    ihn bleibt die Spindelleistung unberücksichtigt. Liegt die Leistungsgrenze
    zwischen zwei Stufen, sucht plane() das ae genau an ihr und fügt es als
    eigene Stufe ein – so wird die Spindel ausgenutzt, nicht nur die nächste
    kleinere Stufe.
    """
    d = werkzeug.durchmesser
    n = sd.drehzahl(vc, d)
    begrenzt = grenzen.drehzahl > 0 and n > grenzen.drehzahl
    if begrenzt:
        n = grenzen.drehzahl
    plan = Plan(n=n, vc=n * math.pi * d / 1000.0, drehzahl_begrenzt=begrenzt)
    if not moeglich(werkzeug) or n <= 0 or spandicke <= 0 or ap <= 0:
        return plan

    prozente = set(STUFEN)
    if 0 < round(grenzen.ae_prozent, 2) < max(STUFEN):
        prozente.add(round(grenzen.ae_prozent, 2))
    for prozent in sorted(prozente):
        plan.stufen.append(
            _stufe(werkzeug, d * prozent / 100.0, ap, spandicke, n, grenzen, werkstoff)
        )
    _an_leistungsgrenze(plan, werkzeug, ap, spandicke, n, grenzen, werkstoff)

    erlaubt = [i for i, s in enumerate(plan.stufen) if s.erlaubt]
    if erlaubt:
        plan.beste = max(erlaubt, key=lambda i: plan.stufen[i].q)
    naechste = plan.beste + 1
    if naechste >= len(plan.stufen):
        plan.grund = GRUND_ENDE
    elif plan.stufen[naechste].ueber_ae:
        plan.grund = GRUND_AE
    else:
        plan.grund = GRUND_LEISTUNG
    return plan


def _an_leistungsgrenze(plan, werkzeug, ap, h, n, grenzen, werkstoff):
    """Fügt die Stufe genau an der Leistungsgrenze ein, wenn sie zwischen zwei Stufen liegt."""
    stufen = plan.stufen
    for i in range(1, len(stufen)):
        unten, oben = stufen[i - 1], stufen[i]
        if unten.ueber_leistung or not oben.ueber_leistung:
            continue
        # Die Leistung wächst mit ae: halbieren, bis das ae auf AE_SCHRITT genau ist.
        a, b = unten.ae, oben.ae
        while b - a > AE_SCHRITT / 2:
            mitte = (a + b) / 2
            if _stufe(werkzeug, mitte, ap, h, n, grenzen, werkstoff).ueber_leistung:
                b = mitte
            else:
                a = mitte
        ae = _abgerundet(a, AE_SCHRITT)  # bleibt sicher unter der Grenze
        stufe = _stufe(werkzeug, ae, ap, h, n, grenzen, werkstoff)
        # Nur, wenn sie den Vorschlag verbessern kann – nicht jenseits der ae-Grenze.
        if ae > unten.ae + AE_SCHRITT / 2 and stufe.erlaubt:
            stufe.an_grenze = True
            stufen.insert(i, stufe)
        return


def _abgerundet(wert, schritt):
    """`wert` auf ein Vielfaches von `schritt` abgerundet – so bleibt jede Grenze eingehalten."""
    return math.floor(wert / schritt + 1e-9) * schritt


def als_einsatz(plan, stufe, ap):
    """Die Stufe als neuer Einsatz „Schruppen dynamisch“, mit dem vc, das sich ergibt.

    Gerundet, wie man es eintippen würde – und zwar ab: Aufgerundet läge ein
    Wert über der Grenze, an der er gerade noch liegt (Drehzahl, Vorschub, ae).
    """
    return wz.Einsatz(
        art=wz.DYNAMISCH,
        ae=round(_abgerundet(stufe.ae, 0.01), 2),
        ap=round(ap, 2),
        vc=round(_abgerundet(plan.vc, 0.1), 1),
        fz=round(_abgerundet(stufe.fz, 0.001), 3),
    )


# --- Grenzen der Maschine (W-001) -------------------------------------------------


def grenzen_der_maschine(maschine):
    """(höchste Drehzahl in U/min, höchster Vorschub in mm/min) einer Maschine; 0 = unbekannt.

    Drehzahl: die der Spindeln, die ein Werkzeug antreiben (Werkzeugaufnahme
    mit Spindel) – an einer Drehmaschine dreht die Hauptspindel das
    Werkstück, nicht den Fräser. Fehlt diese Zuordnung, die größte Drehzahl
    aller Spindeln. Vorschub: der kleinste Bearbeitungsvorschub der
    Linearachsen – die langsamste Achse bremst die Bahn.
    """
    arten = maschine_modul.betriebsarten(maschine)
    spindeln = [b for b in arten if b.Art == maschine_modul.ART_SPINDEL and b.Drehzahl > 0]
    antreibend = {
        a.Spindel.Name
        for a in maschine_modul.aufnahmen(maschine)
        if a.Art == maschine_modul.AUFNAHME_WERKZEUG and a.Spindel is not None
    }
    werkzeugspindeln = [b for b in spindeln if b.Name in antreibend] or spindeln
    drehzahl = max((b.Drehzahl for b in werkzeugspindeln), default=0.0)
    vorschuebe = [
        b.VorschubMax for b in arten if b.Art == maschine_modul.ART_LINEAR and b.VorschubMax > 0
    ]
    return drehzahl, min(vorschuebe, default=0.0)


def maschinen():
    """Die Maschinen (W-001) in allen offenen Dokumenten, die Drehzahl oder Vorschub kennen.

    Liste von (Beschriftung, Drehzahl, Vorschub); die Beschriftung nennt das
    Dokument, wenn mehrere Dokumente offen sind.
    """
    gefunden = []
    dokumente = list(FreeCAD.listDocuments().values())
    for dokument in dokumente:
        for objekt in dokument.Objects:
            if getattr(objekt, "Typ", None) != maschine_modul.TYP_MASCHINE:
                continue
            drehzahl, vorschub = grenzen_der_maschine(objekt)
            if drehzahl <= 0 and vorschub <= 0:
                continue
            name = objekt.Label
            if len(dokumente) > 1:
                name = f"{name} ({dokument.Label})"
            gefunden.append((name, drehzahl, vorschub))
    return gefunden
