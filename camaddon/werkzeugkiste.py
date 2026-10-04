# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Werkzeugkiste der Hersteller (W-007; Manuel, 2026-10-02: „Ich hätte gerne die
Werkzeugkiste vorgefüllt … Bohrer von Ceratizit … von Gühring 5596 alle metrischen
Gewindebohrer bis M30 … Fräser Jongen UNI-Mill VHM 494W … für jede Werkzeugart ein Beispiel …
mit Internetseite zum Bestellen, Link und Artikelnummer … wenn es bei irgendeinem Material keine
Daten geben sollte, dann schätze anhand der vorhandenen Daten …“).

Je Reihe Hersteller, Bezeichnung, die Größen mit ihren Maßen und Schnittwerte je Werkstoffklasse
(werkstoffe.KLASSEN), jede Klasse unter ihrer Kennung („M“) – Werte für M gelten für jeden
austenitischen Werkstoff (werkzeuge.Werkzeug.verwandter), ohne gewählten Werkstoff die für P1.
So hat ein Bohrer neun Zeilen statt fünfzig (bis P-2026-10-02-94 standen sie unter einem
Vertreter wie 1.4301; Manuel, 2026-10-03: lieber die Obergruppen).

Wo der Katalog des Herstellers sie nennt, sind Maße, Nummern und Schnittwerte die des Herstellers
(katalogwerte; nachgeschlagen am 2026-10-02 nachts – beim Bau der Kiste, P-2026-10-02-46, waren
seine Seiten gesperrt). Was er nicht nennt – andere Werkstoffklassen, Schlichten, Planen –, sind
Richtwerte, wie Kataloge sie für solche Werkzeuge nennen, aus Grundwerten je Einsatz für Stahl
bis 750 N/mm² und Faktoren je Klasse gerechnet. Die Bezeichnung jeder Reihe sagt, was woher
kommt, `quelle` ausführlich. Wo eine Artikelnummer fehlt, ist sie nicht belegt; der Link sucht
dann nach dem Werkzeug.

hinzufuegen() legt die gewählten Reihen in die eigene Werkzeugkiste: mit der nächsten freien
T-Nummer; was dort schon ist (gleicher Hersteller und Name), bleibt, wie es ist – auch mit den
Änderungen des Benutzers.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from . import katalogwerte as kw
from . import werkstoffe as ws
from . import werkzeuge as wz

# Faktoren auf vc und fz je Klasse, bezogen auf Stahl bis 750 N/mm² (P1) – wie sie sich in den
# Katalogen für Vollhartmetall/Hartmetall und für HSS ungefähr verhalten.
FAKTOREN_HM = {
    "P1": (1.0, 1.0),
    "P2": (0.67, 0.8),
    "M": (0.45, 0.7),
    "K": (0.85, 1.0),
    "N1": (2.2, 1.4),
    "N2": (1.1, 1.2),
    "N3": (1.4, 1.5),
    "S": (0.25, 0.6),
    "H": (0.33, 0.5),
}
FAKTOREN_HSS = {
    "P1": (1.0, 1.0),
    "P2": (0.57, 0.8),
    "M": (0.33, 0.6),
    "K": (0.83, 1.2),
    "N1": (2.0, 1.4),
    "N2": (1.33, 1.2),
    "N3": (1.0, 1.4),
    "S": (0.2, 0.5),
    "H": (0.1, 0.3),
}

# Grundwerte je Einsatz für P1: vc in m/min und fz je mm Durchmesser (fz = Wert · D) – oder,
# als dritte Zahl, ein fester fz (Platten, Bohrstangen).
GRUND_HM = {
    wz.VOLLNUT: (140.0, 0.004),
    wz.SCHRUPPEN: (180.0, 0.005),
    wz.DYNAMISCH: (230.0, 0.009),
    wz.SCHLICHTEN: (210.0, 0.004),
    wz.FASEN: (120.0, 0.004),
    wz.VERRUNDEN: (120.0, 0.004),
    wz.GEWINDEFRAESEN: (100.0, 0.003),
    wz.ZENTRIEREN: (80.0, 0.005),
    wz.AUSDREHEN: (180.0, 0.0, 0.1),
    wz.PLANEN: (280.0, 0.0, 0.2),
}
GRUND_HSS = {
    wz.VOLLNUT: (30.0, 0.004),
    wz.SCHRUPPEN: (30.0, 0.005),
    wz.SCHLICHTEN: (35.0, 0.004),
    wz.ZENTRIEREN: (20.0, 0.004),
    wz.SENKEN: (15.0, 0.002),
    wz.REIBEN: (8.0, 0.0033),
    wz.GEWINDEBOHREN: (15.0, 0.0),
}
# Der Messerkopf: Werte je Klasse wie für Wendeplatten mit 45° (vc, fz).
PLANEN_HM = {
    "P1": (280.0, 0.2),
    "P2": (220.0, 0.18),
    "M": (180.0, 0.15),
    "K": (250.0, 0.2),
    "N1": (600.0, 0.15),
    "N2": (300.0, 0.15),
    "N3": (400.0, 0.15),
    "S": (50.0, 0.12),
    "H": (100.0, 0.1),
}
# Vorschub je Umdrehung eines HSS-Spiralbohrers in Stahl bis 750 N/mm² über dem Durchmesser
# (Tabellenbuch); dazwischen geradlinig.
F_BOHRER = ((2.0, 0.04), (3.0, 0.06), (5.0, 0.10), (8.0, 0.15), (12.0, 0.20), (20.0, 0.28))
BOHREN_VC_HSS = 30.0  # m/min in P1
# VHM-Bohrer mit Innenkühlung (TiAlN, 5×D) in P1: vc um 100 m/min, f je Umdrehung wie die
# Kataloge für solche Bohrer (Ø 3 um 0,08, Ø 8,5 um 0,2, Ø 16 um 0,3) – Richtwerte.
F_BOHRER_HM = ((3.0, 0.08), (5.0, 0.12), (8.0, 0.18), (12.0, 0.24), (16.0, 0.30), (20.0, 0.34))
BOHREN_VC_HM = 100.0  # m/min in P1

RICHTWERTE = "Richtwerte (geschätzt)"


@dataclass(frozen=True)
class Reihe:
    """Eine Reihe gleicher Werkzeuge in mehreren Größen."""

    kennung: str
    art: str
    hersteller: str  # leer: ein Beispiel nach Norm, ohne belegten Hersteller
    titel: str  # „UNI-Mill VHM 494W HI06“
    quelle: str  # woher Maße, Nummern und Werte kommen
    # Je Größe die Felder des Werkzeugs ({"durchmesser": 12, "schneidenlaenge": 26, …}) und
    # "name", "artikel", "link" – was fehlt, ergänzt werkzeuge() aus der Reihe.
    groessen: tuple
    gemeinsam: dict = field(default_factory=dict)  # Felder für alle Größen
    bezeichnung: str = ""
    link: str = ""  # für alle Größen; leer: eine Suche nach Hersteller und Artikel
    katalog: str = ""  # leer: eine Suche nach dem Katalog
    schnittwerte: bool = True  # Drehwerkzeuge und Taster haben (noch) keine
    # Aus dem Katalog des Herstellers: {Durchmesser: {Klasse: {Art: (vc, fz, ap, ae)}}}
    # (katalogwerte) – was fehlt, wird geschätzt.
    katalogwerte: dict = field(default_factory=dict)

    @property
    def anzahl(self):
        return len(self.groessen)


def suche(*worte):
    """Ein Link, der im Browser nach den Worten sucht – wo keine Seite belegt ist."""
    return "https://www.google.com/search?q=" + quote_plus(" ".join(w for w in worte if w))


def _zahl(wert):
    """„8.5“, „12“ – für Namen, die in die Steuerung gehen (mit Punkt)."""
    return f"{wert:g}"


# --- die Reihen ---------------------------------------------------------------------------

# Ceratizit CoreLine WPC UNI, VHM-Hochleistungsbohrer 5×D nach DIN 6537 (lang), Schaft DIN 6535
# HB, Innenkühlung, TiAlN, 140° – Manuels Bohrer (2026-10-03: „Artikel-Nr.: 1170311000 CoreLine –
# Hochleistungsbohrer, DIN 6537 – WPC UNI“). Die Artikelnummer ist 11703 + Ø in µm (1170308500 =
# Ø 8,5); je Durchmesserbereich (bis, Nutzlänge LU, Gesamtlänge, Schaft), nachgeschlagen am
# 2026-10-03 auf cuttingtools.ceratizit.com für Ø 3, 3,3, 4, 4,2, 5, 5,5, 6, 6,8, 7, 8,5, 9,
# 10,2, 11, 12,5, 15, 17 und 19. Ø 2 und 2,5 gibt es in der Reihe nicht.
_WPC_UNI = (
    (3.99, 23, 66, 6), (4.99, 29, 74, 6), (6.0, 35, 82, 6), (8.0, 43, 91, 8),
    (10.0, 49, 103, 10), (12.0, 56, 118, 12), (14.0, 60, 124, 14), (16.0, 63, 133, 16),
    (18.0, 71, 143, 18), (20.0, 77, 153, 20),
)  # fmt: skip
# Manuels Durchmesser (2026-10-02), ohne Ø 2 und 2,5.
_BOHRER = (
    3, 3.3, 4, 4.2, 4.5, 5, 6, 6.5, 6.8, 7, 8, 8.5, 8.8, 9, 10, 10.2, 10.5, 11, 11.8, 12, 12.5,
    13, 13.5, 14, 15, 15.5, 17, 17.5, 18, 19,
)  # fmt: skip
CERATIZIT_ARTIKEL = "https://cuttingtools.ceratizit.com/de/de/products/{artikel}.html"


def _wpc_uni(d):
    return next((lu, l1, schaft) for bis, lu, l1, schaft in _WPC_UNI if d <= bis + 1e-9)


def _bohrer():
    groessen = []
    for d in _BOHRER:
        nutz, gesamt, schaft = _wpc_uni(d)
        artikel = f"11703{round(d * 1000):05d}"
        groessen.append(
            {
                "durchmesser": float(d),
                "schneidenlaenge": float(nutz),
                "gesamtlaenge": float(gesamt),
                "schaft": float(schaft),
                "name": f"WPC D{_zahl(d)}",
                "artikel": artikel,
                "bezeichnung": (
                    "WPC-UNI." + f"{d:.2f}".replace(".", ",") + ".R.5D.DIN6535.IK.HB TiAlN"
                    f" · Bohrtiefe bis 5 × D · {RICHTWERTE}"
                ),
                "link": CERATIZIT_ARTIKEL.format(artikel=artikel),
                "katalog": CERATIZIT_ARTIKEL.format(artikel=artikel),
            }
        )
    return Reihe(
        kennung="ceratizit-wpc-uni-5d",
        art=wz.BOHRER,
        hersteller="Ceratizit",
        titel="CoreLine WPC UNI VHM-Hochleistungsbohrer 5×D, DIN 6537, IK, TiAlN, Ø 3–19",
        quelle=(
            "Ceratizit, cuttingtools.ceratizit.com (2026-10-03): Maße (Nutzlänge, Gesamtlänge, "
            "Schaft) und Artikelnummern je Größe von der Produktseite; Spitze 140°, Innenkühlung, "
            "TiAlN, Bohrtiefe bis 5 × D. Schnittwerte nennt die Seite nicht: Richtwerte für "
            "VHM-Bohrer mit Innenkühlung, je Werkstoffklasse geschätzt."
        ),
        groessen=tuple(groessen),
        gemeinsam={"schneiden": 2, "schneidstoff": wz.VHM, "spitzenwinkel": 140.0},
        bezeichnung=f"CoreLine WPC UNI, VHM, DIN 6537, 5 × D · {RICHTWERTE}",
        katalog=suche("Ceratizit", "CoreLine", "WPC UNI", "Katalog"),
    )


# Metrisches Regelgewinde bis M30: (M, Steigung, Gesamtlänge, Gewindelänge, Schaft) nach
# DIN 371 (bis M10, verstärkter Schaft) und DIN 376 (ab M12, Schaft durchfallend).
_GEWINDE = (
    (2, 0.4, 45, 8, 2.8), (2.5, 0.45, 50, 9, 2.8), (3, 0.5, 56, 11, 3.5), (4, 0.7, 63, 13, 4.5),
    (5, 0.8, 70, 16, 6), (6, 1.0, 80, 19, 6), (8, 1.25, 90, 22, 8), (10, 1.5, 100, 24, 10),
    (12, 1.75, 110, 29, 9), (14, 2.0, 110, 30, 11), (16, 2.0, 110, 32, 12),
    (18, 2.5, 125, 37, 14), (20, 2.5, 140, 37, 16), (22, 2.5, 140, 38, 18),
    (24, 3.0, 160, 45, 18), (27, 3.0, 160, 45, 20), (30, 3.5, 180, 48, 22),
)  # fmt: skip


GUEHRING_5596 = "https://webshop.guehring.de/5596"  # die Seite der Reihe im Gühring-Shop


def _gewindebohrer():
    groessen = []
    for m, p, gesamt, gewinde, schaft in _GEWINDE:
        # Die Nummer 5596 belegen die Händler von M3 bis M10 („05596 010.000“ für M10).
        belegt = 3 <= m <= 10
        artikel = f"5596 {m:.3f}".replace(".", ",") if belegt else ""
        groessen.append(
            {
                "durchmesser": float(m),
                "steigung": p,
                "schneidenlaenge": float(gewinde),
                "gesamtlaenge": float(gesamt),
                "schaft": float(schaft),
                "name": f"5596 M{_zahl(m)}",
                "artikel": artikel,
                "bezeichnung": (
                    f"Spiralnut, HSS-E, TiN, Typ VA, Form C, ISO 2/6H, Blauring · Kernloch "
                    f"Ø {_zahl(m - p)} · {RICHTWERTE}"
                ),
                "link": GUEHRING_5596,
            }
        )
    return Reihe(
        kennung="guehring-5596",
        art=wz.GEWINDEBOHRER_RECHTS,
        hersteller="Gühring",
        titel="5596 Maschinen-Gewindebohrer HSS-E, Spiralnut, Blauring, M2–M30",
        quelle=(
            "Gühring 5596 (Shop webshop.guehring.de/5596, 2026-10-02): Maschinen-Gewindebohrer "
            "für metrische ISO-Gewinde, HSS-E, TiN, Typ VA, Form C, ISO2/6H, rechts, Bohrtiefe "
            "3 × D, Grundloch. Die Tabelle der Größen lädt der Shop erst im Browser – Nummern "
            "nach Händlern (M3–M10, „05596 010.000“ für M10); M2, M2,5 und ab M12 (DIN 376) "
            "ohne belegte Nummer. Maße nach DIN 371/376. vc: Richtwerte für HSS-E-Gewindebohrer, "
            "je Werkstoffklasse geschätzt; der Vorschub ist die Steigung."
        ),
        groessen=tuple(groessen),
        gemeinsam={"schneidstoff": wz.HSS},
        katalog=GUEHRING_5596,
    )


GUEHRING_8330 = "https://webshop.guehring.de/8330"
GUEHRING_KATALOG_GEWINDE = (
    "https://guehring.com/wp-content/downloads/CH/GUHRING-CH_Gewindewerkzeuge_DE.pdf"
)
# Gühring 8330 aus dem Katalog „Top-Auswahl Gewindewerkzeuge“ (Gühring Schweiz, gültig bis
# 2026-12-31): (M, P, Schaft d2, Vierkant SW, Kernloch dk, l1, l2 Gewindelänge, l5) je Größe.
_GUEHRING_8330 = (
    (2, 0.4, 2.8, 2.1, 1.6, 45, 4.5, 13.5), (2.5, 0.45, 2.8, 2.1, 2.05, 50, 5, 14.5),
    (3, 0.5, 3.5, 2.7, 2.5, 56, 6, 18), (4, 0.7, 4.5, 3.4, 3.3, 63, 7.5, 21),
    (5, 0.8, 6, 4.9, 4.2, 70, 8.5, 25), (6, 1.0, 6, 4.9, 5, 80, 11, 30),
    (8, 1.25, 8, 6.2, 6.8, 90, 14, 35), (10, 1.5, 10, 8, 8.5, 100, 16, 39),
    (12, 1.75, 9, 7, 10.2, 110, 18.5, 49), (16, 2.0, 12, 9, 14, 110, 20, 54),
)  # fmt: skip


def _gewindebohrer_8330():
    """Gühring 8330 (Manuel, 2026-10-03: „Gewindebohrer von Gühring … webshop.guehring.de/8330,
    der hier?“) – Sackloch, HSS-E TiAlN, Form C, 3 × D, 6HX."""
    groessen = []
    for m, p, schaft, _sw, kernloch, gesamt, gewinde, _l5 in _GUEHRING_8330:
        groessen.append(
            {
                "durchmesser": float(m),
                "steigung": p,
                "schneidenlaenge": float(gewinde),
                "gesamtlaenge": float(gesamt),
                "schaft": float(schaft),
                "name": f"8330 M{_zahl(m)}",
                "artikel": f"8330 {m:.3f}",
                "bezeichnung": (
                    f"Sackloch, HSS-E, TiAlN, Form C, 6HX, DIN {371 if m <= 10 else 376} · "
                    f"Kernloch Ø {_zahl(kernloch)} · {RICHTWERTE}"
                ),
                "link": GUEHRING_8330,
            }
        )
    return Reihe(
        kennung="guehring-8330",
        art=wz.GEWINDEBOHRER_RECHTS,
        hersteller="Gühring",
        titel="8330 Maschinen-Gewindebohrer HSS-E TiAlN, Sackloch, 3 × D, M2–M16",
        quelle=(
            "Gühring 8330, Katalog „Top-Auswahl Gewindewerkzeuge“ von Gühring Schweiz (gültig bis "
            "2026-12-31, guehring.com): Bestell-Nr. „8330 12.000“, Steigung, Schaft, Gewindelänge "
            "l2, Gesamtlänge und Kernloch je Größe; HSS-E, TiAlN, DIN 371/376, rechts, Form C, "
            "3 × D, 6HX, Sackloch; geeignet für Stahl und rostfreien Stahl (P, M), bedingt für "
            "Guss, NE-Metalle und Titan. vc: Richtwerte für HSS-E-Gewindebohrer, je "
            "Werkstoffklasse geschätzt; der Vorschub ist die Steigung."
        ),
        groessen=tuple(groessen),
        gemeinsam={"schneidstoff": wz.HSS},
        katalog=GUEHRING_KATALOG_GEWINDE,
    )


# Jongens Werte gelten für jeden Durchmesser der Reihe; Schlichten und Planen nennt der Katalog
# nicht – sie nehmen vc und fz des Eckfräsens (wie die Richtwerte das Planen vom Schruppen).
JONGEN_TEXT = (
    f"Schnittwerte: {kw.JONGEN_494W_STAND} (Schlichten und Planen wie Eckfräsen; Aluminium, "
    f"Kupfer, Kunststoff und gehärteter Stahl {RICHTWERTE})"
)


def _jongen_werte():
    return {float(d): werte for d, werte in kw.JONGEN_494W.items()}


def _schaftfraeser():
    """Jongen VHM 494W HI06 – Manuels Fräser (Ø 12) und die Größen, die er nannte, die es
    scharfkantig gibt: Ø 6 bis 20 (Ø 3 gibt es in der Reihe nicht, Ø 4 und 5 nur mit Radius:
    _schaftfraeser_r)."""
    groessen = []
    for d in (6, 8, 10, 12, 16, 20):
        nummer, schneide, nutzlaenge, hals, schaft, gesamt = kw.JONGEN_494W_MASSE[d]
        groessen.append(
            {
                "durchmesser": float(d),
                "schneidenlaenge": float(schneide),
                "gesamtlaenge": float(gesamt),
                "schaft": float(schaft),
                "hals_d": float(hals),
                "hals_laenge": float(nutzlaenge - schneide),
                "name": f"494W D{d}",
                "artikel": nummer,
                "bezeichnung": f"VHM 494W-{d:02d} HI06 · {JONGEN_TEXT}",
                "link": kw.JONGEN_SUCHE + nummer,
            }
        )
    return Reihe(
        kennung="jongen-494w",
        art=wz.SCHAFTFRAESER,
        hersteller="Jongen",
        titel="UNI-Mill VHM 494W HI06, 4 Schneiden, Ø 6–20",
        quelle=(
            f"{kw.JONGEN_494W_STAND}: Bestell-Nr., Schneidenlänge, Nutzlänge, Hals, Schaft und "
            "Gesamtlänge (Seite 5), Schnittwerte für Eckfräsen, Vollnuten und trochoidal je "
            "Werkstoffgruppe und Durchmesser (Seite 7–9). Manuels Ø 12: VU494M12B-HI06 (auf dem "
            "Fräser V-53939-FB2). Ø 3 gibt es in der Reihe nicht, Ø 4 und 5 nur mit Eckenradius."
        ),
        groessen=tuple(groessen),
        gemeinsam={"schneiden": 4, "schneidstoff": wz.VHM},
        bezeichnung=f"UNI-Mill VHM 494W HI06 · {JONGEN_TEXT}",
        katalog=kw.JONGEN_494W_KATALOG,
        katalogwerte=_jongen_werte(),
    )


def _schaftfraeser_r():
    """Jongen VHM 494W R HI06, Ø 4 und 5 – Manuel nannte sie; scharfkantig gibt es sie nicht."""
    groessen = []
    for d, (
        nummer,
        radius,
        schneide,
        nutzlaenge,
        hals,
        schaft,
        gesamt,
    ) in kw.JONGEN_494W_R_MASSE.items():
        groessen.append(
            {
                "durchmesser": float(d),
                "eckradius": float(radius),
                "schneidenlaenge": float(schneide),
                "gesamtlaenge": float(gesamt),
                "schaft": float(schaft),
                "hals_d": float(hals),
                "hals_laenge": float(nutzlaenge - schneide),
                "name": f"494W D{d} R{_zahl(radius)}",
                "artikel": nummer,
                "bezeichnung": f"VHM 494W-{d:02d} R{_zahl(radius * 10).zfill(2)} HI06 · {JONGEN_TEXT}",
                "link": kw.JONGEN_SUCHE + nummer,
            }
        )
    return Reihe(
        kennung="jongen-494w-r",
        art=wz.TORUSFRAESER,
        hersteller="Jongen",
        titel="UNI-Mill VHM 494W R HI06, Eckenradius, Ø 4 und 5",
        quelle=(
            f"{kw.JONGEN_494W_STAND}, Seite 6: Ø 4 mit R 0,4 und Ø 5 mit R 0,5 – Manuels Ø 4 und 5 "
            "gibt es nur so. Schnittwerte wie der 494W (Seite 7–9; beim Rampen φ um 30 % kleiner)."
        ),
        groessen=tuple(groessen),
        gemeinsam={"schneiden": 4, "schneidstoff": wz.VHM},
        bezeichnung=f"UNI-Mill VHM 494W R HI06 · {JONGEN_TEXT}",
        katalog=kw.JONGEN_494W_KATALOG,
        katalogwerte=_jongen_werte(),
    )


def _entgrater():
    """Garant 208165 – laut Datenblatt ein VHM-Entgrater spiralisiert mit 60° Spitzenwinkel
    (angenommen war ein Fasenfräser 90°)."""
    groessen = []
    katalog = {}
    for d, (gesamt, fz_stahl, datenblatt) in kw.GARANT_208165_MASSE.items():
        groessen.append(
            {
                "durchmesser": float(d),
                # Die Schneide geht bis an die Spitze: der Kegel mit 60° vom Ø bis zur Spitze.
                "schneidenlaenge": round(d / 2 / math.tan(math.radians(30.0)), 2),
                "gesamtlaenge": float(gesamt),
                "schaft": float(d),
                "name": f"208165 D{d}",
                "artikel": f"208165 {d}",
                "link": f"{kw.GARANT_208165_SEITE}{d}",
                "katalog": datenblatt,
            }
        )
        # fz nennt das Datenblatt für Stahl bis 900 N/mm²; die anderen Klassen mit den Faktoren
        # der Richtwerte.
        katalog[float(d)] = {
            klasse: {wz.FASEN: (vc, round(fz_stahl * FAKTOREN_HM[klasse][1], 3), None, None)}
            for klasse, vc in kw.GARANT_208165_VC.items()
        }
    return Reihe(
        kennung="garant-208165",
        art=wz.FASENFRAESER,
        hersteller="Garant",
        titel="208165 VHM-Entgrater spiralisiert 60°, TiSiN, Ø 6–16",
        quelle=(
            f"{kw.GARANT_208165_STAND}: VHM, TiSiN, 4 Schneiden, Spitzenwinkel 60°, Spiralwinkel "
            "35°, Schaft DIN 6535 HA, Gesamtlänge je Ø; vc je Werkstoffgruppe, fz je Ø für Stahl "
            "bis 900 N/mm² (die anderen Klassen mit Faktoren geschätzt; Kupfer und Messing nennt "
            "das Datenblatt nicht)."
        ),
        groessen=tuple(groessen),
        gemeinsam={
            "schneiden": 4,
            "schneidstoff": wz.VHM,
            "spitzenwinkel": 60.0,
            "spitzen_d": 0.0,
        },
        bezeichnung=(
            f"Garant 208165, VHM 60°, TiSiN · Schnittwerte: {kw.GARANT_208165_STAND} (fz außer "
            f"in Stahl und Kupfer/Messing {RICHTWERTE})"
        ),
        katalog="https://ecatalog.hoffmann-group.com/",
        katalogwerte=katalog,
    )


def _messerkopf():
    return Reihe(
        kennung="sandvik-coromill-345",
        art=wz.PLANFRAESER,
        hersteller="Sandvik Coromant",
        titel="CoroMill 345 Planfräser 45°, Ø 50, 4 Schneiden",
        quelle=(
            "Sandvik CoroMill 345, Ø 50 mit Aufnahme 22 mm, mittlere Teilung (4 Platten; die "
            "weite 345-050Q22-13L hat 3), Einstellwinkel 45°, ap bis 6. Werte für Stahl: vc "
            "280 m/min, fz 0,2 mm (bis 750 N/mm²) – Richtwerte für beschichtete Platten, je "
            "Werkstoffklasse geschätzt."
        ),
        groessen=(
            {
                "durchmesser": 50.0,
                "schneidenlaenge": 6.0,
                "gesamtlaenge": 40.0,
                "schaft": 22.0,
                "name": "CoroMill345 D50",
                "artikel": "345-050Q22-13M",
                "link": suche("Sandvik", "345-050Q22-13M"),
            },
        ),
        gemeinsam={"schneiden": 4, "schneidstoff": wz.VHM, "einstellwinkel": 45.0},
        bezeichnung=f"CoroMill 345, Platten 345R-1305M · {RICHTWERTE}",
        katalog=suche("Sandvik Coromant", "CoroMill 345", "PDF"),
    )


def _holex_kugel():
    """HOLEX VHM-Vollradiusfräser TiAlN 207125, Ø 2 bis 12 – die günstige Kugel für Stahl,
    Edelstahl, Guss und Alu (Manuel, 2026-10-04: der Diabolo ist nur fürs Hartfräsen und teuer)."""
    groessen = []
    for d, (schneide, gesamt, schaft, _fz) in kw.HOLEX_KUGEL_MASSE.items():
        seite = kw.HOLEX_KUGEL_SEITE.format(d=d)
        groessen.append(
            {
                "durchmesser": float(d),
                "schneidenlaenge": float(schneide),
                "gesamtlaenge": float(gesamt),
                "schaft": float(schaft),
                "name": f"207125 D{d}",
                "artikel": f"207125 {d}",
                "link": seite,
                "katalog": seite,
            }
        )
    return Reihe(
        kennung="holex-kugel",
        art=wz.KUGELFRAESER,
        hersteller="Hoffmann Group",
        titel="HOLEX VHM-Vollradiusfräser TiAlN, 2 Schneiden, Ø 2 bis 12",
        quelle=(
            "Hoffmann Group, hoffmann-group.com/DE/de/hom/p/207125-<Ø> (2026-10-04): Maße, fz "
            "beim Kopierfräsen in Stahl, vc aus der Anwendertabelle (welche Gruppe welche "
            "Werkstoffklasse ist, geschätzt), ae und ap höchstens 0,05 · D. Netto ab 23,93 € – "
            "für P, M, K und N, nicht nur fürs Hartfräsen wie der Diabolo."
        ),
        groessen=tuple(groessen),
        gemeinsam={"schneiden": 2, "schneidstoff": wz.VHM},
        bezeichnung="HOLEX VHM-Vollradiusfräser TiAlN · Katalogwerte Kopieren, sonst Richtwerte",
        katalogwerte=kw.holex_kugel_werte(),
    )


def _holex_torus():
    """HOLEX Pro Steel VHM-Torusfräser HPC TiAlN 206357, Ø 6 bis 16 – günstig für Stahl,
    Edelstahl und Guss (bisher gab es nur Jongen Ø 4 und 5 und einen GARANT Ø 10)."""
    groessen = []
    for (d, r), (schneide, gesamt, schaft, _fb, _fn) in kw.HOLEX_TORUS_MASSE.items():
        seite = kw.HOLEX_TORUS_SEITE.format(
            d=d, r=_zahl(r).replace(".", "%2C") if r % 1 else f"{int(r)}%2C0"
        )
        groessen.append(
            {
                "durchmesser": float(d),
                "eckradius": float(r),
                "schneidenlaenge": float(schneide),
                "gesamtlaenge": float(gesamt),
                "schaft": float(schaft),
                "name": f"206357 D{d} R{_zahl(r)}",
                "artikel": f"206357 {d}/{r:.1f}".replace(".", ","),
                "link": seite,
                "katalog": seite,
            }
        )
    return Reihe(
        kennung="holex-torus",
        art=wz.TORUSFRAESER,
        hersteller="Hoffmann Group",
        titel="HOLEX Pro Steel VHM-Torusfräser HPC TiAlN, 4 Schneiden, Ø 6 bis 16",
        quelle=(
            "Hoffmann Group, hoffmann-group.com/DE/de/hom/p/206357-<Ø>@2F<R> (2026-10-04): Maße, "
            "fz beim Besäumen und Nutenfräsen, vc aus der Anwendertabelle (welche Gruppe welche "
            "Werkstoffklasse ist, geschätzt), Vollnut höchstens 0,05 · D tief. Netto ab 41,66 €."
        ),
        groessen=tuple(groessen),
        gemeinsam={"schneiden": 4, "schneidstoff": wz.VHM},
        bezeichnung="HOLEX Pro Steel VHM-Torusfräser HPC TiAlN · Katalogwerte Stahl, Inox, Guss",
        katalogwerte=kw.holex_torus_werte(),
    )


def _beispiel(kennung, art, titel, quelle, werte, name, schneidstoff=wz.VHM):
    """Ein Beispiel einer Art – Maße nach Norm oder wie üblich, ohne belegten Hersteller."""
    werte = dict(werte, name=name, link=suche(titel))
    return Reihe(
        kennung=kennung,
        art=art,
        hersteller="",
        titel=titel,
        quelle=quelle + " Hersteller und Artikelnummer selbst eintragen.",
        groessen=(werte,),
        gemeinsam={"schneidstoff": schneidstoff},
        bezeichnung=f"Beispiel · {RICHTWERTE}",
        katalog="",
        schnittwerte=wz.einsatzarten(art) is not None,
    )


HOFFMANN_SEITE = "https://www.hoffmann-group.com/DE/de/hom/p/{artikel}"


def _hoffmann(kennung, art, titel, artikel, werte, name, schneidstoff=wz.VHM, quelle=""):
    """Ein GARANT-Werkzeug der Hoffmann Group – Artikel, Maße und Link nachgeschlagen am
    2026-10-03 auf hoffmann-group.com (Manuel: „Hoffmann Group oder WEMAG sind Anlaufstellen,
    wo du alles bekommst … dort findet man dann auch alle Daten“). Schnittwerte nennt die Seite
    nur über ToolScout: Richtwerte, je Werkstoffklasse geschätzt. `artikel` wie auf der Seite
    („207424 10“); der Link nimmt die Form der Adresse („207424-10“)."""
    adresse = artikel.replace(" ", "-").replace("/", "@2F")
    seite = HOFFMANN_SEITE.format(artikel=adresse)
    werte = dict(werte, name=name, artikel=artikel, link=seite, katalog=seite)
    return Reihe(
        kennung=kennung,
        art=art,
        hersteller="Hoffmann Group",
        titel=titel,
        quelle=(
            f"Hoffmann Group, {seite} (2026-10-03): Artikel {artikel}, Maße von der Seite. "
            + (quelle + " " if quelle else "")
            + "Schnittwerte: Richtwerte, je Werkstoffklasse geschätzt."
        ),
        groessen=(werte,),
        gemeinsam={"schneidstoff": schneidstoff},
        bezeichnung=f"GARANT {titel} · {RICHTWERTE}",
        katalog=seite,
        schnittwerte=wz.einsatzarten(art) is not None,
    )


def _beispiele():
    """Je weitere Art ein Werkzeug – wo eins nachgeschlagen ist, ein echtes von der Hoffmann
    Group (GARANT), sonst eins, wie es in jeder Werkstatt liegt."""
    ueblich = "Maße wie üblich, Werte je Werkstoffklasse geschätzt."
    return (
        _hoffmann(
            "garant-torus", wz.TORUSFRAESER, "VHM-Torusfräser HPC ZOX Ø 10 R1, 3 Schneiden",
            "206260 10/1,0",
            {"durchmesser": 10.0, "eckradius": 1.0, "schneiden": 3, "schneidenlaenge": 22.0,
             "gesamtlaenge": 72.0, "schaft": 10.0},
            "206260 D10 R1",
        ),
        _hoffmann(
            "garant-kugel", wz.KUGELFRAESER,
            "Diabolo VHM-Vollradiusfräser HPC TiAlN Ø 10, 3 Schneiden", "207424 10",
            {"durchmesser": 10.0, "schneiden": 3, "schneidenlaenge": 18.0, "gesamtlaenge": 100.0,
             "schaft": 10.0},
            "207424 D10", quelle="Bis 65 HRC, Radiustoleranz ±0,005 mm.",
        ),
        _beispiel(
            "beispiel-konik", wz.KONIKFRAESER, "Konikfräser VHM Ø 4, 3°", ueblich,
            {"durchmesser": 4.0, "kegelwinkel": 3.0, "schneiden": 3, "schneidenlaenge": 20.0,
             "gesamtlaenge": 70.0, "schaft": 8.0},
            "Konik D4 3Grad",
        ),
        _beispiel(
            "beispiel-schwalbenschwanz", wz.SCHWALBENSCHWANZFRAESER,
            "Schwalbenschwanzfräser VHM Ø 20, 60°", ueblich,
            {"durchmesser": 20.0, "flankenwinkel": 60.0, "schneiden": 6, "schneidenlaenge": 6.0,
             "hals_d": 8.0, "gesamtlaenge": 60.0, "schaft": 12.0},
            "Schwalbe D20",
        ),
        _hoffmann(
            "garant-lollipop", wz.LOLLIPOPFRAESER, "VHM-Kugelfräser 220° TiAlN Ø 10, 2 Schneiden",
            "207175 10",
            {"durchmesser": 10.0, "schneiden": 2, "hals_d": 6.5, "hals_laenge": 30.0,
             "gesamtlaenge": 120.0, "schaft": 10.0},
            "207175 D10 220Grad",
            quelle="Hals-Ø und Halslänge nennt die Seite nicht – geschätzt.",
        ),
        _beispiel(
            "beispiel-radius", wz.RADIENFRAESER, "Viertelkreisfräser VHM R3", ueblich,
            {"durchmesser": 14.0, "profilradius": 3.0, "spitzen_d": 8.0, "schneiden": 3,
             "schneidenlaenge": 4.0, "gesamtlaenge": 60.0, "schaft": 12.0},
            "Radius R3",
        ),
        _beispiel(
            "beispiel-scheibennut", wz.NUTENFRAESER,
            "Scheibennutfräser HSS-E Ø 50 × 5, 12 Schneiden", ueblich,
            {"durchmesser": 50.0, "schneidenbreite": 5.0, "schneiden": 12, "hals_d": 16.0,
             "gesamtlaenge": 80.0, "schaft": 20.0},
            "Nut D50 B5", wz.HSS,
        ),
        _beispiel(
            "beispiel-formfraeser", wz.FORMFRAESER, "Formfräser VHM Ø 10, Profil nach Zeichnung",
            ueblich,
            {"durchmesser": 10.0, "schneiden": 2, "schneidenlaenge": 15.0, "gesamtlaenge": 72.0,
             "schaft": 10.0},
            "Form D10",
        ),
        _hoffmann(
            "garant-gewindefraeser", wz.GEWINDEFRAESER,
            "Master TM Schaft-Gewindefräser AlTiN M10 × 1,5, 6 Schneiden, IK", "139663 M10",
            {"durchmesser": 8.1, "steigung": 1.5, "flankenwinkel": 60.0, "schneiden": 6,
             "schneidenlaenge": 20.25, "gesamtlaenge": 82.0, "schaft": 12.0},
            "139663 M10",
            quelle="Bis 2 × D, mit Senkstufe 90°; der Hals nennt die Seite nicht – geschätzt.",
        ),
        _hoffmann(
            "garant-zentrierbohrer", wz.ZENTRIERBOHRER, "Zentrierbohrer HSS DIN 333 A 2,5",
            "111000 2,5",
            {"durchmesser": 2.5, "spitzenwinkel": 60.0, "schneiden": 2, "schneidenlaenge": 3.1,
             "gesamtlaenge": 45.0, "schaft": 6.3},
            "111000 A2.5", wz.HSS, quelle="Maße nach DIN 333 A.",
        ),
        _hoffmann(
            "garant-nc-anbohrer", wz.NC_ANBOHRER, "VHM-NC-Anbohrer 90° unbeschichtet Ø 10",
            "121020 10",
            {"durchmesser": 10.0, "spitzenwinkel": 90.0, "schneiden": 2, "schneidenlaenge": 24.0,
             "gesamtlaenge": 70.0, "schaft": 10.0},
            "121020 D10",
        ),
        _hoffmann(
            "garant-gewinde-links", wz.GEWINDEBOHRER_LINKS,
            "Maschinen-Gewindebohrer Linksgewinde HSS-E 6H M10 × 1,5", "132800 M10",
            {"durchmesser": 10.0, "steigung": 1.5, "schneidenlaenge": 24.0,
             "gesamtlaenge": 100.0, "schaft": 10.0},
            "132800 M10 LH", wz.HSS,
            quelle="Längen nach DIN 371 – die Seite war nicht im Einzelnen zu lesen.",
        ),
        _hoffmann(
            "garant-kegelsenker", wz.KEGELSENKER,
            "Präzisions-Kegelsenker 90° HSS DIN 335 C Ø 20,5, 3 Schneiden", "150152 20,5",
            {"durchmesser": 20.5, "spitzenwinkel": 90.0, "spitzen_d": 4.5, "schneiden": 3,
             "gesamtlaenge": 63.0, "schaft": 10.0},
            "150152 D20.5", wz.HSS,
        ),
        _beispiel(
            "beispiel-flachsenker", wz.FLACHSENKER, "Flachsenker DIN 373 für M8 (Ø 15) HSS",
            "Maße nach DIN 373, Werte geschätzt.",
            {"durchmesser": 15.0, "spitzen_d": 9.0, "schneiden": 3, "schneidenlaenge": 12.0,
             "gesamtlaenge": 100.0, "schaft": 12.5},
            "Flachsenker M8", wz.HSS,
        ),
        _hoffmann(
            "garant-reibahle", wz.REIBAHLE, "Maschinenreibahle H7 HSS-E Ø 10, 6 Schneiden",
            "163000 10",
            {"durchmesser": 10.0, "schneiden": 6, "schneidenlaenge": 38.0, "gesamtlaenge": 133.0,
             "schaft": 10.0},
            "163000 D10 H7", wz.HSS,
        ),
        _beispiel(
            "beispiel-bohrstange", wz.BOHRSTANGE, "Bohrstange mit Wendeplatte, ab Ø 16",
            ueblich,
            {"durchmesser": 16.0, "schneiden": 1, "schneidenlaenge": 50.0, "gesamtlaenge": 120.0,
             "schaft": 16.0},
            "Bohrstange D16",
        ),
        _beispiel(
            "beispiel-ausspindeln", wz.AUSSPINDELWERKZEUG, "Ausspindelkopf Ø 30", ueblich,
            {"durchmesser": 30.0, "schneiden": 1, "schneidenlaenge": 60.0, "gesamtlaenge": 120.0},
            "Ausspindel D30",
        ),
        _beispiel(
            "beispiel-taster", wz.TASTER, "3D-Taster, Kugel Ø 4", "Maße wie üblich.",
            {"durchmesser": 4.0, "gesamtlaenge": 100.0},
            "Taster D4",
        ),
    )  # fmt: skip


# Die Formen der Wendeschneidplatten nach ISO 1832 – (Bezeichnung, Plattenwinkel, Einstellwinkel
# des üblichen Halters, Eckenradius).
_PLATTEN = (
    ("CNMG 120408", 80.0, 95.0, 0.8, "C – Rhombus 80°, Halter PCLNR"),
    ("DNMG 150608", 55.0, 93.0, 0.8, "D – Rhombus 55°, Halter PDJNR"),
    ("VNMG 160408", 35.0, 93.0, 0.8, "V – Rhombus 35°, Halter SVJBR"),
    ("WNMG 080408", 80.0, 95.0, 0.8, "W – Trigon 80°, Halter PWLNR"),
    ("TNMG 160408", 60.0, 91.0, 0.8, "T – Dreieck 60°, Halter PTGNR"),
    ("SNMG 120408", 90.0, 75.0, 0.8, "S – Quadrat 90°, Halter PSBNR"),
    ("RCMT 1204M0", 0.0, 0.0, 6.0, "R – rund Ø 12, Kopierhalter"),
)


def _drehen():
    groessen = []
    for iso, platte, einstellung, radius, text in _PLATTEN:
        groessen.append(
            {
                "plattenwinkel": platte,
                "einstellwinkel": einstellung,
                "eckradius": radius,
                "name": iso.replace(" ", ""),
                "artikel": iso,
                "bezeichnung": (
                    f"{text} · Stahl: vc 180–280 m/min, f 0,15–0,4 mm, ap 0,5–4 mm "
                    f"({RICHTWERTE})"
                ),
                "link": suche(iso, "Wendeschneidplatte"),
            }
        )
    return Reihe(
        kennung="iso-wendeplatten",
        art=wz.DREHWERKZEUG,
        hersteller="",
        titel="Drehen: Wendeschneidplatten nach ISO 1832 – C, D, V, W, T, S, R",
        quelle=(
            "Die Grundformen der Wendeschneidplatten (ISO 1832) mit dem üblichen Halter und "
            "Eckenradius 0,8 – jeder Hersteller führt sie unter dieser Bezeichnung. Schnittwerte "
            "stehen in der Bezeichnung: FreeCAD dreht (noch) nicht."
        ),
        groessen=tuple(groessen),
        gemeinsam={"schneidstoff": wz.VHM, "ausfuehrung": wz.RECHTS},
        katalog="",
        schnittwerte=False,
    )


def _einstechen():
    return (
        Reihe(
            kennung="beispiel-einstechen",
            art=wz.EINSTECHWERKZEUG,
            hersteller="",
            titel="Einstechplatte b 3, r 0,2",
            quelle="Eine Einstechplatte 3 mm wie üblich. Hersteller und Nummer selbst eintragen.",
            groessen=(
                {
                    "schneidenbreite": 3.0,
                    "eckradius": 0.2,
                    "stechtiefe": 10.0,
                    "name": "Einstich B3",
                    "bezeichnung": f"Beispiel · Stahl: vc 100–150 m/min, f 0,05–0,1 mm "
                    f"({RICHTWERTE})",
                    "link": suche("Einstechplatte 3 mm"),
                },
            ),
            gemeinsam={"schneidstoff": wz.VHM, "ausfuehrung": wz.RECHTS},
            schnittwerte=False,
        ),
        Reihe(
            kennung="beispiel-gewindedrehen",
            art=wz.GEWINDEDREHWERKZEUG,
            hersteller="",
            titel="Gewindedrehplatte 16ER AG60 (Teilprofil 60°)",
            quelle="Teilprofilplatte 60° für Außengewinde, wie üblich. Hersteller selbst eintragen.",
            groessen=(
                {
                    "flankenwinkel": 60.0,
                    "name": "16ER AG60",
                    "artikel": "16ER AG60",
                    "bezeichnung": f"Beispiel · Stahl: vc 100–150 m/min ({RICHTWERTE})",
                    "link": suche("16ER AG60"),
                },
            ),
            gemeinsam={"schneidstoff": wz.VHM, "ausfuehrung": wz.RECHTS},
            schnittwerte=False,
        ),
    )


def reihen():
    """Alle Reihen der Werkzeugkiste, Manuels zuerst."""
    return (
        _bohrer(),
        _gewindebohrer(),
        _gewindebohrer_8330(),
        _schaftfraeser(),
        _schaftfraeser_r(),
        _entgrater(),
        _messerkopf(),
        _holex_kugel(),
        _holex_torus(),
        *_beispiele(),
        _drehen(),
        *_einstechen(),
    )


def reihe(kennung):
    """Die Reihe mit dieser Kennung, oder None."""
    return next((r for r in reihen() if r.kennung == kennung), None)


# --- Werkzeuge und Werte ------------------------------------------------------------------


def werkzeuge(reihe):
    """Die Werkzeuge der Reihe, ohne T-Nummer (1), mit Schnittwerten je Werkstoffklasse."""
    ergebnis = []
    for groesse in reihe.groessen:
        werte = dict(reihe.gemeinsam, **groesse)
        w = wz.Werkzeug(art=reihe.art)
        for feld, wert in werte.items():
            if feld in ("link", "artikel", "name", "bezeichnung", "katalog"):
                continue
            setattr(w, feld, wert)
        w.name = werte.get("name", "")
        w.hersteller = reihe.hersteller
        w.artikel = werte.get("artikel", "")
        w.bezeichnung = werte.get("bezeichnung", reihe.bezeichnung)
        w.link = werte.get("link") or reihe.link or suche(reihe.hersteller, w.artikel, w.name)
        w.katalog = werte.get("katalog") or reihe.katalog
        if reihe.schnittwerte:
            katalog = reihe.katalogwerte.get(float(w.durchmesser))
            for klasse in ws.KLASSEN:
                w.schnittwerte[klasse] = einsaetze(w, klasse, katalog)
        ergebnis.append(w)
    return ergebnis


def richtwerte_moeglich(werkzeug):
    """Lassen sich für das Werkzeug Richtwerte rechnen? Es braucht Einsätze und, wo die Art
    einen hat, einen Durchmesser (fz hängt an ihm)."""
    if wz.einsatzarten(werkzeug.art) is None:
        return False
    return werkzeug.durchmesser > 0 or not wz.hat_feld(werkzeug, "durchmesser")


def richtwerte_eintragen(werkzeug):
    """Trägt die Richtwerte je Werkstoffklasse ein – wie bei den Werkzeugen der Hersteller, aus
    Art, Durchmesser, Schneiden und Schneidstoff (Manuel, 2026-10-02: „Beispielschnittwerte für
    die einzelnen Materialien und Bearbeitungsläufe … direkt mit anbieten, wenn jemand einen
    Fräser erstellen will“). Was schon eingetragen ist, bleibt; Stahl bis 750 N/mm² (P1)
    bekommt keine Zeilen, wenn es Zeilen für alle Werkstoffe gibt – die gelten dann für ihn
    (Manuels Standardfräser hat seine Werte dort). Gibt zurück, für wie viele Klassen neue
    Zeilen dazukamen."""
    if not richtwerte_moeglich(werkzeug):
        return 0
    neu = 0
    for klasse in ws.KLASSEN:
        if werkzeug.schnittwerte.get(klasse):
            continue
        if klasse == ws.KLASSEN[0] and werkzeug.schnittwerte.get(wz.ALLE):
            continue
        liste = einsaetze(werkzeug, klasse)
        if liste:
            werkzeug.schnittwerte[klasse] = liste
            neu += 1
    return neu


def einsaetze(werkzeug, klasse, katalog=None):
    """Die Einsätze des Werkzeugs für eine Werkstoffklasse – je Art, was sie anbietet; mit
    `katalog` ({Klasse: {Art: (vc, fz, ap, ae)}}, katalogwerte) die Werte des Herstellers, wo er
    sie nennt."""
    arten = wz.einsatzarten(werkzeug.art) or ()
    werte = (katalog or {}).get(klasse) or {}
    return [e for e in (_einsatz(werkzeug, art, klasse, werte) for art in arten) if e is not None]


def _aus_katalog(werkzeug, art, werte):
    """Der Einsatz mit den Werten des Herstellers – Schlichten und Planen, die Kataloge für
    Schaftfräser selten nennen, mit vc und fz des Schruppens (Eckfräsen); None ohne Werte."""
    eigen = werte.get(art)
    if eigen is None and art in (wz.SCHLICHTEN, wz.PLANEN) and wz.SCHRUPPEN in werte:
        vc, fz, _ap, _ae = werte[wz.SCHRUPPEN]
        eigen = (vc, fz, None, None)
    if eigen is None:
        return None
    vc, fz, ap, ae = eigen
    einsatz = wz.vorlage(werkzeug, art)
    einsatz.vc, einsatz.fz = vc, fz
    if ap:
        einsatz.ap = min(ap, werkzeug.schneidenlaenge) if werkzeug.schneidenlaenge else ap
    if ae:
        einsatz.ae = ae
    return _runden(einsatz)


def _einsatz(werkzeug, art, klasse, katalog=None):
    if katalog:
        einsatz = _aus_katalog(werkzeug, art, katalog)
        if einsatz is not None:
            return einsatz
    hss = werkzeug.schneidstoff == wz.HSS
    faktor_vc, faktor_fz = (FAKTOREN_HSS if hss else FAKTOREN_HM)[klasse]
    d = werkzeug.durchmesser
    if art == wz.BOHREN:
        f = _f_bohrer(d, F_BOHRER if hss else F_BOHRER_HM) * faktor_fz
        vc = (BOHREN_VC_HSS if hss else BOHREN_VC_HM) * faktor_vc
        return _runden(wz.Einsatz(art=art, vc=vc, fz=f / max(werkzeug.schneiden, 1)))
    if art == wz.PLANEN and werkzeug.art == wz.PLANFRAESER:
        vc, fz = PLANEN_HM[klasse]
        einsatz = wz.vorlage(werkzeug, art)
        einsatz.ae = round(0.7 * d, 2)  # 70 % des Ø: gleichmäßiger Eingriff
        einsatz.ap = 2.0
        einsatz.vc, einsatz.fz = vc, fz
        return _runden(einsatz)
    # Der Schaftfräser plant mit 0,7 D und 0,1 D tief (werkzeuge.vorlage) – vc und fz wie beim
    # Schruppen: Über D/2 ist der Span so dick wie fz.
    art_werte = wz.SCHRUPPEN if art == wz.PLANEN else art
    grund = (GRUND_HSS if hss else GRUND_HM).get(art_werte)
    if grund is None:
        grund = (GRUND_HM if hss else GRUND_HSS).get(art_werte)
        if grund is None:
            return None
    vc, je_d, *fest = grund
    fz = fest[0] if fest else je_d * d
    einsatz = wz.vorlage(werkzeug, art)
    einsatz.vc = vc * faktor_vc
    einsatz.fz = fz * faktor_fz
    if art == wz.GEWINDEBOHREN:
        einsatz.fz = 0.0  # der Vorschub ist die Steigung
    return _runden(einsatz)


def _f_bohrer(d, punkte=F_BOHRER):
    """Vorschub je Umdrehung des Bohrers in P1 – aus `punkte` (F_BOHRER für HSS, F_BOHRER_HM für
    VHM), dazwischen geradlinig, außen festgehalten."""
    if d <= punkte[0][0]:
        return punkte[0][1]
    for (d0, f0), (d1, f1) in zip(punkte, punkte[1:], strict=False):
        if d <= d1:
            return f0 + (f1 - f0) * (d - d0) / (d1 - d0)
    return punkte[-1][1]


def _runden(einsatz):
    einsatz.vc = float(max(round(einsatz.vc), 1)) if einsatz.vc else 0.0
    einsatz.fz = max(round(einsatz.fz, 3), 0.001) if einsatz.fz else 0.0
    einsatz.ae = round(einsatz.ae, 2)
    einsatz.ap = round(einsatz.ap, 2)
    return einsatz


# --- in die eigene Werkzeugkiste -------------------------------------------------------------


@dataclass
class Bericht:
    neu: list = field(default_factory=list)  # die hinzugefügten Werkzeuge
    schon_da: list = field(default_factory=list)  # die es schon gab (Name)


def hinzufuegen(bibliothek, kennungen):
    """Legt Werkzeuge der Kiste in `bibliothek` – je mit der nächsten freien T-Nummer. Jeder
    Eintrag in `kennungen` ist eine Reihe (ihre Kennung: alle Größen) oder eine einzelne Größe
    (Kennung, Nummer in der Reihe; Manuel, 2026-10-03: „EINZELNE Bohrer aufnehmen von einem
    Hersteller, nicht gleich alle“). Ein Werkzeug mit gleichem Hersteller und Namen gibt es
    schon: Es bleibt, wie es ist. Gespeichert wird hier nichts – das macht der Dialog mit OK
    oder Übernehmen."""
    bericht = Bericht()
    for eintrag in kennungen:
        kennung, nummer = eintrag if isinstance(eintrag, tuple) else (eintrag, None)
        gefunden = reihe(kennung)
        if gefunden is None:
            continue
        alle = werkzeuge(gefunden)
        if nummer is not None and not 0 <= nummer < len(alle):
            continue
        for werkzeug in alle if nummer is None else [alle[nummer]]:
            if _schon_da(bibliothek, werkzeug):
                bericht.schon_da.append(werkzeug.name)
                continue
            werkzeug.nummer = bibliothek.naechste_nummer()
            bibliothek.werkzeuge.append(werkzeug)
            bericht.neu.append(werkzeug)
    return bericht


def _schon_da(bibliothek, werkzeug):
    return any(
        w.art == werkzeug.art
        and w.hersteller == werkzeug.hersteller
        and (w.name == werkzeug.name or (werkzeug.artikel and w.artikel == werkzeug.artikel))
        for w in bibliothek.werkzeuge
    )
