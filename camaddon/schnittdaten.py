# SPDX-License-Identifier: LGPL-2.1-or-later
"""Rechnen mit Schnittwerten (W-002): Drehzahl, Vorschub, Zeitspanvolumen, Eingriff.

Eingegeben werden vc und fz – so stehen sie im Katalog des Herstellers –,
Drehzahl und Vorschub rechnet das Addon. Alle Längen in mm, vc in m/min,
Ergebnisse in U/min, mm/min und cm³/min. Fehlt ein Wert (0), ist das
Ergebnis 0 – „unbekannt“, wie überall im Addon.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

from . import einheiten
from . import werkzeuge as wz


def drehzahl(vc, durchmesser):
    """n = vc · 1000 / (π · D), in U/min."""
    if vc <= 0 or durchmesser <= 0:
        return 0.0
    return vc * 1000.0 / (math.pi * durchmesser)


def vorschub(n, schneiden, fz):
    """vf = n · z · fz, in mm/min."""
    return n * schneiden * fz


def zeitspanvolumen(ae, ap, vf):
    """Q = ae · ap · vf / 1000 beim Fräsen, in cm³/min."""
    return ae * ap * vf / 1000.0


def zeitspanvolumen_bohren(durchmesser, vf):
    """Q = π · D² / 4 · vf / 1000 beim Bohren ins Volle, in cm³/min."""
    return math.pi * durchmesser**2 / 4.0 * vf / 1000.0


def rechne(werkzeug, einsatz):
    """(n, vf, Q) für einen Einsatz dieses Werkzeugs; fehlt etwas, sind die Werte 0."""
    n = drehzahl(einsatz.vc, werkzeug.durchmesser)
    vf = vorschub(n, werkzeug.schneiden, einsatz.fz)
    if werkzeug.art == wz.BOHRER:
        q = zeitspanvolumen_bohren(werkzeug.durchmesser, vf)
    else:
        q = zeitspanvolumen(einsatz.ae, einsatz.ap, vf)
    return n, vf, q


# --- Eingriff und Spandicke (P-2026-09-25-48) --------------------------------

# Dünner als das schneidet eine Schneide kaum noch, sie reibt – Verschleiß
# ohne Abtrag. Grobe Grenze für Hartmetall, nur für einen Hinweis.
MINDEST_SPANDICKE = 0.01  # mm


def eingriffswinkel(ae, durchmesser):
    """Der Winkel φ, über den ein Zahn im Material ist, in Bogenmaß.

    cos φ = 1 − 2 · ae / D; eine Vollnut (ae ≥ D) hat 180°.
    """
    if ae <= 0 or durchmesser <= 0:
        return 0.0
    return math.acos(1.0 - 2.0 * min(ae, durchmesser) / durchmesser)


def spandicke_max(fz, ae, durchmesser):
    """Die größte Spandicke: fz · sin φ bei ae < D/2, sonst fz."""
    phi = eingriffswinkel(ae, durchmesser)
    if phi >= math.pi / 2:
        return fz
    return fz * math.sin(phi)


def spandicke_mittel(fz, ae, durchmesser):
    """Die mittlere Spandicke über den Eingriff: fz · (1 − cos φ) / φ."""
    phi = eingriffswinkel(ae, durchmesser)
    if phi <= 0:
        return 0.0
    return fz * (1.0 - math.cos(phi)) / phi


def fz_fuer_spandicke(spandicke, ae, durchmesser):
    """Das fz, bei dem die größte Spandicke `spandicke` beträgt (Spandickenausgleich)."""
    phi = eingriffswinkel(ae, durchmesser)
    if phi <= 0:
        return 0.0
    if phi >= math.pi / 2:
        return spandicke
    return spandicke / math.sin(phi)


# --- Strategien vergleichen (P-2026-09-25-49) --------------------------------


def schneidenweg_je_cm3(ae, ap, fz, schneiden, durchmesser):
    """Wie weit jede Stelle der Schneide durchs Material fährt, um 1 cm³ abzutragen, in m.

    Je Umdrehung trägt das Werkzeug ae · ap · fz · z ab; jede Stelle der
    Schneide im Eingriff fährt dabei den Bogen D/2 · φ. Für 1 cm³ (1000 mm³)
    braucht es 1000 / (ae · ap · fz · z) Umdrehungen – zusammen
    D · φ / (2 · ae · ap · fz · z) in m. Verschleiß wächst ungefähr mit diesem
    Weg (bei gleichem vc) – eine Faustregel, kein Standzeitmodell.
    """
    abtrag = ae * ap * fz * schneiden
    if abtrag <= 0 or durchmesser <= 0:
        return 0.0
    return durchmesser * eingriffswinkel(ae, durchmesser) / (2.0 * abtrag)


def spezifische_schnittkraft(spandicke_mittel_mm, kc11, mc):
    """kc = kc1.1 · h m^(−mc) in N/mm²; 0, wenn kc1.1 oder die Spandicke unbekannt ist."""
    if kc11 <= 0 or spandicke_mittel_mm <= 0:
        return 0.0
    return kc11 * spandicke_mittel_mm ** (-mc)


def schnittleistung(q, kc):
    """Pc = Q · kc / 60 000 in kW (Q in cm³/min, kc in N/mm²), ohne Wirkungsgrad der Maschine."""
    return q * kc / 60000.0


@dataclass
class Kennzahlen:
    """Was ein Einsatz leistet und was er die Schneide kostet – für den Vergleich."""

    q: float = 0.0  # cm³/min
    zeit: float = 0.0  # min für einheiten.vergleichsvolumen() (100 cm³, in inch 5 in³)
    schneidenweg: float = 0.0  # m je cm³
    ap: float = 0.0  # mm – so viel Schneide arbeitet
    schneidenlaenge: float = 0.0  # mm, 0 = unbekannt
    eingriff: float = 0.0  # Anteil der Umdrehung im Material, 0 … 0.5
    spandicke: float = 0.0  # größte, mm
    leistung: float = 0.0  # kW, 0 = unbekannt (kein kc1.1)
    drehmoment: float = 0.0  # Nm, 0 = unbekannt


def kennzahlen(werkzeug, einsatz, werkstoff=None):
    """Die Kennzahlen eines Fräs-Einsatzes; `werkstoff` (mit kc1.1) nur für die Leistung."""
    d = werkzeug.durchmesser
    n, _vf, q = rechne(werkzeug, einsatz)
    k = Kennzahlen(q=q, ap=einsatz.ap, schneidenlaenge=werkzeug.schneidenlaenge)
    k.zeit = einheiten.vergleichsvolumen() / q if q > 0 else 0.0
    k.schneidenweg = schneidenweg_je_cm3(einsatz.ae, einsatz.ap, einsatz.fz, werkzeug.schneiden, d)
    k.eingriff = eingriffswinkel(einsatz.ae, d) / (2 * math.pi)
    k.spandicke = spandicke_max(einsatz.fz, einsatz.ae, d)
    if werkstoff is not None and werkstoff.kc11 > 0:
        kc = spezifische_schnittkraft(
            spandicke_mittel(einsatz.fz, einsatz.ae, d), werkstoff.kc11, werkstoff.mc
        )
        k.leistung = schnittleistung(q, kc)
        k.drehmoment = k.leistung * 9550.0 / n if n > 0 else 0.0
    return k


def urteil(a, b, name_a, name_b):
    """Das Urteil über zwei Einsätze als Liste von (Schlüssel, Werte) für tr().

    Nur Aussagen, die die Zahlen tragen: Abtrag, Schneidenweg, und warum –
    genutzte Schneide und Eingriff –, dazu die Leistung, wenn sie bekannt ist.
    Die Oberfläche macht daraus Sätze.
    """
    saetze = []
    if a.q <= 0 or b.q <= 0:
        return [("wv.urteil.unvollstaendig", {})]
    schneller, langsamer = (b, a) if b.q >= a.q else (a, b)
    name_s, name_l = (name_b, name_a) if b.q >= a.q else (name_a, name_b)
    faktor_q = schneller.q / langsamer.q
    if faktor_q < 1.1:
        saetze.append(("wv.urteil.q_gleich", {}))
    else:
        saetze.append(("wv.urteil.q", {"schnell": name_s, "langsam": name_l, "faktor": faktor_q}))
    if a.schneidenweg > 0 and b.schneidenweg > 0:
        faktor_weg = langsamer.schneidenweg / schneller.schneidenweg
        if faktor_weg >= 1.1:
            saetze.append(("wv.urteil.weg_weniger", {"schnell": name_s, "faktor": faktor_weg}))
        elif faktor_weg <= 1 / 1.1:
            saetze.append(("wv.urteil.weg_mehr", {"schnell": name_s, "faktor": 1 / faktor_weg}))
        # Warum: worauf sich der Verschleiß verteilt und wie lange der Zahn heiß ist.
        if schneller.ap > langsamer.ap * 1.1:
            saetze.append(("wv.urteil.ap", {"ap_viel": schneller.ap, "ap_wenig": langsamer.ap}))
        if schneller.eingriff < langsamer.eingriff / 1.1:
            saetze.append(
                (
                    "wv.urteil.eingriff",
                    {
                        "name": name_s,
                        "anteil_wenig": schneller.eingriff * 100,
                        "anteil_viel": langsamer.eingriff * 100,
                    },
                )
            )
    if schneller.leistung > 0 and langsamer.leistung > 0:
        saetze.append(
            (
                "wv.urteil.leistung",
                {"name": name_s, "leistung": schneller.leistung, "andere": langsamer.leistung},
            )
        )
    for name, k in ((name_a, a), (name_b, b)):
        if 0 < k.spandicke < MINDEST_SPANDICKE:
            saetze.append(("wv.urteil.span_duenn", {"name": name, "h": k.spandicke}))
    return saetze
