# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Werkzeugkiste der Hersteller (W-007; Manuel, 2026-10-02: „Ich hätte gerne die
Werkzeugkiste vorgefüllt … Bohrer von Ceratizit … von Gühring 5596 alle metrischen
Gewindebohrer bis M30 … Fräser Jongen UNI-Mill VHM 494W … für jede Werkzeugart ein Beispiel …
mit Internetseite zum Bestellen, Link und Artikelnummer … wenn es bei irgendeinem Material keine
Daten geben sollte, dann schätze anhand der vorhandenen Daten …“).

Je Reihe Hersteller, Bezeichnung, die Größen mit ihren Maßen und Schnittwerte je Werkstoffklasse
(werkstoffe.KLASSEN): Stahl bis 750 N/mm² unter „Alle Werkstoffe“, jede andere Klasse unter einem
Werkstoff, der für sie steht (VERTRETER) – Werte für 1.4301 gelten für jeden austenitischen
(werkzeuge.Werkzeug.verwandter). So hat ein Bohrer neun Zeilen statt fünfzig.

Die Werte sind Richtwerte, wie Kataloge sie für solche Werkzeuge nennen, aus Grundwerten je
Einsatz für Stahl bis 750 N/mm² und Faktoren je Klasse gerechnet – die Seiten der Hersteller
waren beim Zusammenstellen nicht zu erreichen (P-2026-10-02-46). Darum sagt jede Reihe in ihrer
Bezeichnung „Richtwerte (geschätzt)“, und `quelle` sagt, was woher kommt. Wo eine Artikelnummer
fehlt, ist sie nicht belegt; der Link sucht dann nach dem Werkzeug.

hinzufuegen() legt die gewählten Reihen in die eigene Werkzeugkiste: mit der nächsten freien
T-Nummer; was dort schon ist (gleicher Hersteller und Name), bleibt, wie es ist – auch mit den
Änderungen des Benutzers.

Läuft ohne Oberfläche.
"""

from dataclasses import dataclass, field
from urllib.parse import quote_plus

from . import werkzeuge as wz

# Unter welchem Werkstoff die Werte einer Klasse stehen – P1 unter „Alle Werkstoffe“: Damit
# rechnet jedes Werkzeug, solange kein Werkstoff gewählt ist.
VERTRETER = {
    "P1": wz.ALLE,
    "P2": "1.7225",  # 42CrMo4 vergütet
    "M": "1.4301",
    "K": "0.6025",  # GG-25
    "N1": "3.2315",  # EN AW-6082
    "N2": "2.0401",  # Ms 58
    "N3": "POM-C",
    "S": "3.7165",  # Titan Grade 5
    "H": "1.2379+H",  # 58–62 HRC
}

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

# DIN 338, kurze Spiralbohrer: (Durchmesser bis, Gesamtlänge l1, Spirallänge l2).
_DIN_338 = (
    (2.12, 49, 24), (2.36, 53, 27), (2.65, 57, 30), (3.00, 61, 33), (3.35, 65, 36),
    (3.75, 70, 39), (4.25, 75, 43), (4.75, 80, 47), (5.30, 86, 52), (6.00, 93, 57),
    (6.70, 101, 63), (7.50, 109, 69), (8.50, 117, 75), (9.50, 125, 81), (10.60, 133, 87),
    (11.80, 142, 94), (13.20, 151, 101), (14.00, 160, 108), (15.00, 169, 114),
    (16.00, 178, 120), (17.00, 184, 125), (18.00, 191, 130), (19.00, 198, 135),
    (20.00, 205, 140),
)  # fmt: skip
# Manuels Durchmesser (2026-10-02).
_BOHRER = (
    2, 2.5, 3, 3.3, 4, 4.2, 4.5, 5, 6, 6.5, 6.8, 7, 8, 8.5, 8.8, 9, 10, 10.2, 10.5, 11, 11.8,
    12, 12.5, 13, 13.5, 14, 15, 15.5, 17, 17.5, 18, 19,
)  # fmt: skip


def _din_338(d):
    return next((l1, l2) for bis, l1, l2 in _DIN_338 if d <= bis + 1e-9)


def _bohrer():
    groessen = []
    for d in _BOHRER:
        gesamt, spirale = _din_338(d)
        groessen.append(
            {
                "durchmesser": float(d),
                "schneidenlaenge": float(spirale),
                "gesamtlaenge": float(gesamt),
                "schaft": float(d),
                "name": f"HSS D{_zahl(d)}",
                "link": suche("Ceratizit", "ClassicLine", "DIN 338", "HSS", f"{_zahl(d)} mm"),
            }
        )
    return Reihe(
        kennung="ceratizit-classicline-din338",
        art=wz.BOHRER,
        hersteller="Ceratizit",
        titel="ClassicLine Spiralbohrer HSS DIN 338, 118°",
        quelle=(
            "Manuels Angabe: WL173060311 ClassicLine / 1170305000 · 0095923748 – diese Nummern "
            "ließen sich nicht nachschlagen. Maße nach DIN 338 (kurz), Spitze 118°. Werte: "
            "Richtwerte für HSS-Spiralbohrer (Tabellenbuch; Gühring nennt für HSS-E 32 m/min bis "
            "850 N/mm², 17 m/min bis 1000 N/mm²), je Werkstoffklasse geschätzt."
        ),
        groessen=tuple(groessen),
        gemeinsam={"schneiden": 2, "schneidstoff": wz.HSS, "spitzenwinkel": 118.0},
        bezeichnung=f"ClassicLine, HSS, DIN 338 · {RICHTWERTE}",
        katalog=suche("Ceratizit", "ClassicLine", "Katalog", "PDF"),
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
                    f"Spiralnut, HSS-E, TiN, ISO 2/6H, Blauring · Kernloch Ø {_zahl(m - p)}"
                    f" · {RICHTWERTE}"
                ),
                "link": suche("Gühring", "5596", f"M{_zahl(m)}"),
            }
        )
    return Reihe(
        kennung="guehring-5596",
        art=wz.GEWINDEBOHRER_RECHTS,
        hersteller="Gühring",
        titel="5596 Maschinen-Gewindebohrer HSS-E, Spiralnut, Blauring, M2–M30",
        quelle=(
            "Gühring 5596: HSS-E, TiN, Spiralnut für Sacklöcher, ISO 2/6H, DIN 371 (Händler: "
            "M3–M10, Nummer „05596 010.000“ für M10). M2, M2,5 und ab M12 (DIN 376) dieselbe Art "
            "ohne belegte Nummer – beim Händler prüfen. Maße nach DIN 371/376. vc: Richtwerte "
            "für HSS-E-Gewindebohrer, je Werkstoffklasse geschätzt; der Vorschub ist die Steigung."
        ),
        groessen=tuple(groessen),
        gemeinsam={"schneidstoff": wz.HSS},
        katalog=suche("Gühring", "Gewindebohrer", "Katalog", "PDF"),
    )


# DIN 6527 K (kurz): Durchmesser -> (Schneidenlänge, Gesamtlänge, Schaft); Ø 12 nach Jongen.
_DIN_6527_K = {
    3: (8, 57, 6), 4: (11, 57, 6), 5: (13, 57, 6), 6: (13, 57, 6), 8: (19, 63, 8),
    10: (22, 72, 10), 12: (26, 84, 12), 16: (32, 92, 16), 20: (38, 104, 20),
}  # fmt: skip


def _schaftfraeser():
    groessen = []
    for d, (schneide, gesamt, schaft) in _DIN_6527_K.items():
        artikel = f"VHM 494W-{d} HI06"
        if d == 12:
            artikel += " (V-53939-FB2)"  # so stand er auf Manuels Fräser
        groessen.append(
            {
                "durchmesser": float(d),
                "schneidenlaenge": float(schneide),
                "gesamtlaenge": float(gesamt),
                "schaft": float(schaft),
                "name": f"494W D{d}",
                "artikel": artikel,
                "link": suche("Jongen", "UNI-Mill", "494W", f"{d} mm"),
            }
        )
    return Reihe(
        kennung="jongen-494w",
        art=wz.SCHAFTFRAESER,
        hersteller="Jongen",
        titel="UNI-Mill VHM 494W HI06, 4 Schneiden, Ø 3–20",
        quelle=(
            "Jongen UNI-Mill VHM 494W HI06 (Manuels Ø 12: 494W-12 HI06, V-53939-FB2; "
            "Schneidenlänge 26, Gesamtlänge 84, Schaft 12, 4 Schneiden). Die anderen Größen mit "
            "den Längen nach DIN 6527 K und Nummern nach dem Muster von Ø 12 – prüfen. Werte: "
            "Richtwerte für VHM-Schaftfräser mit 4 Schneiden, je Werkstoffklasse geschätzt."
        ),
        groessen=tuple(groessen),
        gemeinsam={"schneiden": 4, "schneidstoff": wz.VHM},
        bezeichnung=f"UNI-Mill VHM 494W HI06 · {RICHTWERTE}",
        katalog=suche("Jongen", "UNI-Mill", "Katalog", "PDF"),
    )


def _entgrater():
    # Gesamtlänge wie DIN 6535 HA, Spitze 0,5 mm – angenommen.
    laengen = {6: 57, 8: 63, 10: 72, 12: 83, 16: 92}
    groessen = []
    for d, gesamt in laengen.items():
        groessen.append(
            {
                "durchmesser": float(d),
                "schneidenlaenge": round((d - 0.5) / 2, 2),
                "gesamtlaenge": float(gesamt),
                "schaft": float(d),
                "name": f"208165 D{d}",
                "artikel": f"208165 {d}",
                "link": f"https://www.hoffmann-group.com/DE/de/hom/p/208165-{d}",
            }
        )
    return Reihe(
        kennung="garant-208165",
        art=wz.FASENFRAESER,
        hersteller="Garant",
        titel="208165 Entgraten (Fasenfräser 90°), Ø 6–16",
        quelle=(
            "Garant 208165 (Manuels Angabe „208165 12“, Hoffmann Group). Die Seite war nicht zu "
            "erreichen: als VHM-Fasenfräser 90° mit 4 Schneiden angenommen, wie Garant 208070 und "
            "208071; Längen wie DIN 6535 HA – mit dem Katalog vergleichen. Werte: Richtwerte für "
            "VHM-Fasenfräser, je Werkstoffklasse geschätzt."
        ),
        groessen=tuple(groessen),
        gemeinsam={
            "schneiden": 4,
            "schneidstoff": wz.VHM,
            "spitzenwinkel": 90.0,
            "spitzen_d": 0.5,
        },
        bezeichnung=f"Garant 208165, VHM 90° · {RICHTWERTE}",
        katalog=suche("Garant", "Zerspanungshandbuch", "PDF"),
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


def _beispiele():
    """Je weitere Art ein Werkzeug, wie es in jeder Werkstatt liegt."""
    ueblich = "Maße wie üblich, Werte je Werkstoffklasse geschätzt."
    return (
        _beispiel(
            "beispiel-torus", wz.TORUSFRAESER, "Torusfräser VHM Ø 10 R1, 4 Schneiden", ueblich,
            {"durchmesser": 10.0, "eckradius": 1.0, "schneiden": 4, "schneidenlaenge": 22.0,
             "gesamtlaenge": 72.0, "schaft": 10.0},
            "Torus D10 R1",
        ),
        _beispiel(
            "beispiel-kugel", wz.KUGELFRAESER, "Kugelfräser VHM Ø 10, 2 Schneiden", ueblich,
            {"durchmesser": 10.0, "schneiden": 2, "schneidenlaenge": 10.0, "gesamtlaenge": 72.0,
             "schaft": 10.0},
            "Kugel D10",
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
        _beispiel(
            "beispiel-lollipop", wz.LOLLIPOPFRAESER, "Lollipopfräser VHM Ø 8", ueblich,
            {"durchmesser": 8.0, "schneiden": 4, "hals_d": 5.0, "hals_laenge": 20.0,
             "gesamtlaenge": 60.0, "schaft": 8.0},
            "Lollipop D8",
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
        _beispiel(
            "beispiel-gewindefraeser", wz.GEWINDEFRAESER,
            "Gewindefräser VHM M10 × 1,5, 3 Schneiden", ueblich,
            {"durchmesser": 8.0, "steigung": 1.5, "flankenwinkel": 60.0, "schneiden": 3,
             "schneidenlaenge": 20.0, "hals_d": 6.2, "hals_laenge": 22.0, "gesamtlaenge": 63.0,
             "schaft": 8.0},
            "GF M10x1.5",
        ),
        _beispiel(
            "beispiel-zentrierbohrer", wz.ZENTRIERBOHRER,
            "Zentrierbohrer DIN 333 A 2,5 × 6,3 HSS", "Maße nach DIN 333 A, Werte geschätzt.",
            {"durchmesser": 2.5, "spitzenwinkel": 60.0, "schneiden": 2, "schneidenlaenge": 3.1,
             "gesamtlaenge": 45.0, "schaft": 6.3},
            "Zentrier A2.5", wz.HSS,
        ),
        _beispiel(
            "beispiel-nc-anbohrer", wz.NC_ANBOHRER, "NC-Anbohrer VHM 90° Ø 10", ueblich,
            {"durchmesser": 10.0, "spitzenwinkel": 90.0, "schneiden": 2, "schneidenlaenge": 20.0,
             "gesamtlaenge": 72.0, "schaft": 10.0},
            "NC90 D10",
        ),
        _beispiel(
            "beispiel-gewinde-links", wz.GEWINDEBOHRER_LINKS,
            "Gewindebohrer M10 × 1,5 links, HSS-E", "Maße nach DIN 371, Werte geschätzt.",
            {"durchmesser": 10.0, "steigung": 1.5, "schneidenlaenge": 24.0,
             "gesamtlaenge": 100.0, "schaft": 10.0},
            "M10 LH", wz.HSS,
        ),
        _beispiel(
            "beispiel-kegelsenker", wz.KEGELSENKER, "Kegelsenker 90° DIN 335 C Ø 20,5 HSS",
            "Maße nach DIN 335 C, Werte geschätzt.",
            {"durchmesser": 20.5, "spitzenwinkel": 90.0, "spitzen_d": 4.5, "schneiden": 3,
             "gesamtlaenge": 63.0, "schaft": 10.0},
            "Senker90 D20.5", wz.HSS,
        ),
        _beispiel(
            "beispiel-flachsenker", wz.FLACHSENKER, "Flachsenker DIN 373 für M8 (Ø 15) HSS",
            "Maße nach DIN 373, Werte geschätzt.",
            {"durchmesser": 15.0, "spitzen_d": 9.0, "schneiden": 3, "schneidenlaenge": 12.0,
             "gesamtlaenge": 100.0, "schaft": 12.5},
            "Flachsenker M8", wz.HSS,
        ),
        _beispiel(
            "beispiel-reibahle", wz.REIBAHLE, "Maschinenreibahle Ø 10 H7 HSS-E, DIN 212",
            "Maße nach DIN 212, Werte geschätzt.",
            {"durchmesser": 10.0, "schneiden": 6, "schneidenlaenge": 38.0, "gesamtlaenge": 133.0,
             "schaft": 10.0},
            "Reibahle D10 H7", wz.HSS,
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
        _schaftfraeser(),
        _entgrater(),
        _messerkopf(),
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
            if feld in ("link", "artikel", "name", "bezeichnung"):
                continue
            setattr(w, feld, wert)
        w.name = werte.get("name", "")
        w.hersteller = reihe.hersteller
        w.artikel = werte.get("artikel", "")
        w.bezeichnung = werte.get("bezeichnung", reihe.bezeichnung)
        w.link = werte.get("link") or reihe.link or suche(reihe.hersteller, w.artikel, w.name)
        w.katalog = reihe.katalog
        if reihe.schnittwerte:
            for klasse, werkstoff in VERTRETER.items():
                w.schnittwerte[werkstoff] = einsaetze(w, klasse)
        ergebnis.append(w)
    return ergebnis


def einsaetze(werkzeug, klasse):
    """Die Einsätze des Werkzeugs für eine Werkstoffklasse – je Art, was sie anbietet."""
    arten = wz.einsatzarten(werkzeug.art) or ()
    return [e for e in (_einsatz(werkzeug, art, klasse) for art in arten) if e is not None]


def _einsatz(werkzeug, art, klasse):
    hss = werkzeug.schneidstoff == wz.HSS
    faktor_vc, faktor_fz = (FAKTOREN_HSS if hss else FAKTOREN_HM)[klasse]
    d = werkzeug.durchmesser
    if art == wz.BOHREN:
        f = _f_bohrer(d) * faktor_fz
        vc = BOHREN_VC_HSS * faktor_vc
        return _runden(wz.Einsatz(art=art, vc=vc, fz=f / max(werkzeug.schneiden, 1)))
    if art == wz.PLANEN and werkzeug.art == wz.PLANFRAESER:
        vc, fz = PLANEN_HM[klasse]
        einsatz = wz.vorlage(werkzeug, art)
        einsatz.ae = round(0.7 * d, 2)  # 70 % des Ø: gleichmäßiger Eingriff
        einsatz.ap = 2.0
        einsatz.vc, einsatz.fz = vc, fz
        return _runden(einsatz)
    grund = (GRUND_HSS if hss else GRUND_HM).get(art)
    if grund is None:
        grund = (GRUND_HM if hss else GRUND_HSS).get(art)
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


def _f_bohrer(d):
    """Vorschub je Umdrehung des HSS-Bohrers in P1 – aus F_BOHRER, außen festgehalten."""
    punkte = F_BOHRER
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
    """Legt die Werkzeuge der Reihen `kennungen` in `bibliothek` – je mit der nächsten freien
    T-Nummer. Ein Werkzeug mit gleichem Hersteller und Namen gibt es schon: Es bleibt, wie es
    ist. Gespeichert wird hier nichts – das macht der Dialog mit OK oder Übernehmen."""
    bericht = Bericht()
    for kennung in kennungen:
        gefunden = reihe(kennung)
        if gefunden is None:
            continue
        for werkzeug in werkzeuge(gefunden):
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
