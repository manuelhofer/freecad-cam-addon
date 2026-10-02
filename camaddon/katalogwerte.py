# SPDX-License-Identifier: LGPL-2.1-or-later
"""Maße, Nummern und Schnittwerte aus den Katalogen und Datenblättern der Hersteller (W-007;
Manuel, 2026-10-02 nachts: „kümmer dich auch um die werkzeugliste“) – nachgeschlagen, als ihre
Seiten erreichbar waren. Beim Bau der Werkzeugkiste (P-2026-10-02-46) waren sie gesperrt, alle
Werte waren geschätzt.

Schnittwerte je Reihe: {Durchmesser: {Werkstoffklasse: {Einsatzart: (vc, fz, ap, ae)}}} – vc in
m/min, fz, ap und ae in mm; ap oder ae None: wie werkzeuge.vorlage. Klassen wie werkstoffe.KLASSEN;
welche Gruppe des Katalogs für welche Klasse steht, sagt der Kommentar je Reihe. Was ein Katalog
nicht nennt, schätzt werkzeugkiste wie bisher.

Läuft ohne Oberfläche.
"""

from . import werkzeuge as wz

# --- Jongen VHM 494W (R) HI06 ---------------------------------------------------------------------
# Katalog „VHM 494W / 495W“, Stand 11/2025. Technische Daten Seite 5 (scharfkantig) und 6 (mit
# Eckenradius), Schnittdaten Seite 7–9: Eckfräsen → Schruppen, Vollnuten → Vollnut, Trochoidal →
# Dynamisch. Gruppen: P1 allgemeiner Baustahl, unlegierter Stahl; P2 niedrig legierter Stahl; M
# INOX austenitisch; K Grauguss GJL; S hoch-hitzebeständiger Stahl. Für Aluminium, Kupfer,
# Kunststoff und gehärteten Stahl nennt Jongen den 494W nicht.
JONGEN_494W_KATALOG = "https://www.jongen.de/out/downloads/89955f5df9f14a5fbf37de9818a400bc/de.pdf"
JONGEN_SUCHE = "https://www.jongen.de/index.php?lang=0&cl=search&searchparam="
JONGEN_494W_STAND = "Jongen-Katalog „VHM 494W / 495W“ 11/2025"
# Ø → (Bestell-Nr., Schneidenlänge l, Nutzlänge N, Hals-Ø d1, Schaft d, Gesamtlänge L); z 4, mit
# Innenkühlung, Fase 0,01 · D × 45°.
JONGEN_494W_MASSE = {
    6: ("VU494M06B-HI06", 13, 19, 5.5, 6, 58),
    8: ("VU494M08B-HI06", 18, 26, 7.3, 8, 64),
    10: ("VU494M10B-HI06", 22, 30, 9.3, 10, 73),
    12: ("VU494M12B-HI06", 26, 36, 11.2, 12, 84),
    14: ("VU494M14B-HI06", 30, 38, 13.2, 14, 84),
    16: ("VU494M16B-HI06", 34, 45, 15.0, 16, 93),
    20: ("VU494M20B-HI06", 42, 54, 19.0, 20, 104),
    25: ("VU494M25B-HI06", 54, 70, 24.0, 25, 130),
}
# Ø 4 und 5 gibt es nur mit Eckenradius (494W R): Ø → (Bestell-Nr., R, l, N, d1, d, L).
JONGEN_494W_R_MASSE = {
    4: ("VU494M04R04B-HI06", 0.4, 8, 13, 3.8, 6, 58),
    5: ("VU494M05R05B-HI06", 0.5, 10, 13, 4.8, 6, 58),
}
JONGEN_494W = {
    4: {
        "P1": {
            wz.SCHRUPPEN: (210.0, 0.023, 6.0, 1.8),
            wz.VOLLNUT: (180.0, 0.02, 3.3, 4.0),
            wz.DYNAMISCH: (250.0, 0.02, 7.8, 0.8),
        },
        "P2": {
            wz.SCHRUPPEN: (175.0, 0.017, 6.0, 1.6),
            wz.VOLLNUT: (145.0, 0.013, 3.6, 4.0),
            wz.DYNAMISCH: (230.0, 0.017, 7.8, 0.8),
        },
        "M": {
            wz.SCHRUPPEN: (115.0, 0.017, 5.6, 1.6),
            wz.VOLLNUT: (85.0, 0.013, 3.6, 4.0),
            wz.DYNAMISCH: (130.0, 0.013, 7.8, 0.7),
        },
        "K": {
            wz.SCHRUPPEN: (190.0, 0.023, 6.0, 1.8),
            wz.VOLLNUT: (135.0, 0.02, 3.3, 4.0),
            wz.DYNAMISCH: (215.0, 0.02, 7.8, 0.8),
        },
        "S": {
            wz.SCHRUPPEN: (55.0, 0.01, 4.4, 1.4),
            wz.VOLLNUT: (40.0, 0.01, 2.6, 4.0),
            wz.DYNAMISCH: (60.0, 0.01, 7.8, 0.5),
        },
    },
    5: {
        "P1": {
            wz.SCHRUPPEN: (210.0, 0.029, 7.5, 2.2),
            wz.VOLLNUT: (180.0, 0.025, 4.2, 5.0),
            wz.DYNAMISCH: (250.0, 0.025, 9.8, 1.0),
        },
        "P2": {
            wz.SCHRUPPEN: (175.0, 0.021, 7.5, 2.0),
            wz.VOLLNUT: (145.0, 0.017, 4.5, 5.0),
            wz.DYNAMISCH: (230.0, 0.021, 9.8, 1.0),
        },
        "M": {
            wz.SCHRUPPEN: (115.0, 0.021, 7.0, 2.0),
            wz.VOLLNUT: (85.0, 0.017, 4.5, 5.0),
            wz.DYNAMISCH: (130.0, 0.017, 9.8, 0.8),
        },
        "K": {
            wz.SCHRUPPEN: (190.0, 0.029, 7.5, 2.2),
            wz.VOLLNUT: (135.0, 0.025, 4.2, 5.0),
            wz.DYNAMISCH: (215.0, 0.025, 9.8, 1.0),
        },
        "S": {
            wz.SCHRUPPEN: (55.0, 0.013, 5.5, 1.7),
            wz.VOLLNUT: (40.0, 0.013, 3.2, 5.0),
            wz.DYNAMISCH: (60.0, 0.013, 9.8, 0.6),
        },
    },
    6: {
        "P1": {
            wz.SCHRUPPEN: (210.0, 0.035, 9.6, 2.7),
            wz.VOLLNUT: (180.0, 0.03, 7.2, 6.0),
            wz.DYNAMISCH: (250.0, 0.03, 11.7, 1.2),
        },
        "P2": {
            wz.SCHRUPPEN: (175.0, 0.025, 9.6, 2.4),
            wz.VOLLNUT: (145.0, 0.02, 6.6, 6.0),
            wz.DYNAMISCH: (230.0, 0.025, 11.7, 1.1),
        },
        "M": {
            wz.SCHRUPPEN: (115.0, 0.025, 9.3, 2.4),
            wz.VOLLNUT: (85.0, 0.02, 6.6, 6.0),
            wz.DYNAMISCH: (130.0, 0.02, 11.7, 1.0),
        },
        "K": {
            wz.SCHRUPPEN: (190.0, 0.035, 9.6, 2.7),
            wz.VOLLNUT: (135.0, 0.03, 7.2, 6.0),
            wz.DYNAMISCH: (215.0, 0.03, 11.7, 1.2),
        },
        "S": {
            wz.SCHRUPPEN: (55.0, 0.015, 7.5, 2.1),
            wz.VOLLNUT: (40.0, 0.015, 5.1, 6.0),
            wz.DYNAMISCH: (60.0, 0.015, 11.7, 0.7),
        },
    },
    8: {
        "P1": {
            wz.SCHRUPPEN: (210.0, 0.045, 12.8, 3.6),
            wz.VOLLNUT: (180.0, 0.04, 9.6, 8.0),
            wz.DYNAMISCH: (250.0, 0.04, 16.2, 1.6),
        },
        "P2": {
            wz.SCHRUPPEN: (175.0, 0.035, 12.8, 3.2),
            wz.VOLLNUT: (145.0, 0.03, 8.8, 8.0),
            wz.DYNAMISCH: (230.0, 0.035, 16.2, 1.5),
        },
        "M": {
            wz.SCHRUPPEN: (115.0, 0.035, 12.4, 3.2),
            wz.VOLLNUT: (85.0, 0.03, 8.8, 8.0),
            wz.DYNAMISCH: (130.0, 0.025, 16.2, 1.3),
        },
        "K": {
            wz.SCHRUPPEN: (190.0, 0.045, 12.8, 3.6),
            wz.VOLLNUT: (135.0, 0.04, 9.6, 8.0),
            wz.DYNAMISCH: (215.0, 0.04, 16.2, 1.6),
        },
        "S": {
            wz.SCHRUPPEN: (55.0, 0.025, 10.0, 2.8),
            wz.VOLLNUT: (40.0, 0.02, 6.8, 8.0),
            wz.DYNAMISCH: (60.0, 0.02, 16.2, 0.9),
        },
    },
    10: {
        "P1": {
            wz.SCHRUPPEN: (210.0, 0.06, 18.5, 4.5),
            wz.VOLLNUT: (180.0, 0.05, 12.0, 10.0),
            wz.DYNAMISCH: (250.0, 0.05, 20.9, 2.0),
        },
        "P2": {
            wz.SCHRUPPEN: (175.0, 0.04, 18.5, 4.0),
            wz.VOLLNUT: (145.0, 0.035, 11.0, 10.0),
            wz.DYNAMISCH: (230.0, 0.04, 20.9, 1.9),
        },
        "M": {
            wz.SCHRUPPEN: (115.0, 0.04, 17.5, 4.0),
            wz.VOLLNUT: (85.0, 0.035, 11.0, 10.0),
            wz.DYNAMISCH: (130.0, 0.035, 20.9, 1.6),
        },
        "K": {
            wz.SCHRUPPEN: (190.0, 0.06, 18.5, 4.5),
            wz.VOLLNUT: (135.0, 0.05, 12.0, 10.0),
            wz.DYNAMISCH: (215.0, 0.05, 20.9, 2.0),
        },
        "S": {
            wz.SCHRUPPEN: (55.0, 0.03, 14.5, 3.5),
            wz.VOLLNUT: (40.0, 0.025, 8.5, 10.0),
            wz.DYNAMISCH: (60.0, 0.025, 20.9, 1.1),
        },
    },
    12: {
        "P1": {
            wz.SCHRUPPEN: (210.0, 0.07, 22.2, 5.4),
            wz.VOLLNUT: (180.0, 0.06, 14.4, 12.0),
            wz.DYNAMISCH: (250.0, 0.06, 24.7, 2.4),
        },
        "P2": {
            wz.SCHRUPPEN: (175.0, 0.05, 22.2, 4.8),
            wz.VOLLNUT: (145.0, 0.045, 13.2, 12.0),
            wz.DYNAMISCH: (230.0, 0.05, 24.7, 2.3),
        },
        "M": {
            wz.SCHRUPPEN: (115.0, 0.05, 21.0, 4.8),
            wz.VOLLNUT: (85.0, 0.045, 13.2, 12.0),
            wz.DYNAMISCH: (130.0, 0.04, 24.7, 2.0),
        },
        "K": {
            wz.SCHRUPPEN: (190.0, 0.07, 22.2, 5.4),
            wz.VOLLNUT: (135.0, 0.06, 14.4, 12.0),
            wz.DYNAMISCH: (215.0, 0.06, 24.7, 2.4),
        },
        "S": {
            wz.SCHRUPPEN: (55.0, 0.035, 17.4, 4.2),
            wz.VOLLNUT: (40.0, 0.03, 10.2, 12.0),
            wz.DYNAMISCH: (60.0, 0.03, 24.7, 1.4),
        },
    },
    14: {
        "P1": {
            wz.SCHRUPPEN: (210.0, 0.085, 25.9, 6.3),
            wz.VOLLNUT: (180.0, 0.07, 16.8, 14.0),
            wz.DYNAMISCH: (250.0, 0.07, 28.5, 2.8),
        },
        "P2": {
            wz.SCHRUPPEN: (175.0, 0.06, 25.9, 5.6),
            wz.VOLLNUT: (145.0, 0.05, 15.4, 14.0),
            wz.DYNAMISCH: (230.0, 0.06, 28.5, 2.7),
        },
        "M": {
            wz.SCHRUPPEN: (115.0, 0.06, 24.5, 5.6),
            wz.VOLLNUT: (85.0, 0.05, 15.4, 14.0),
            wz.DYNAMISCH: (130.0, 0.045, 28.5, 2.3),
        },
        "K": {
            wz.SCHRUPPEN: (190.0, 0.085, 25.9, 6.3),
            wz.VOLLNUT: (135.0, 0.07, 16.8, 14.0),
            wz.DYNAMISCH: (215.0, 0.07, 28.5, 2.8),
        },
        "S": {
            wz.SCHRUPPEN: (55.0, 0.04, 20.3, 4.9),
            wz.VOLLNUT: (40.0, 0.035, 11.9, 14.0),
            wz.DYNAMISCH: (60.0, 0.04, 28.5, 1.6),
        },
    },
    16: {
        "P1": {
            wz.SCHRUPPEN: (210.0, 0.095, 29.6, 7.2),
            wz.VOLLNUT: (180.0, 0.08, 19.2, 16.0),
            wz.DYNAMISCH: (250.0, 0.08, 32.3, 3.2),
        },
        "P2": {
            wz.SCHRUPPEN: (175.0, 0.07, 29.6, 6.4),
            wz.VOLLNUT: (145.0, 0.055, 17.6, 16.0),
            wz.DYNAMISCH: (230.0, 0.065, 32.3, 3.1),
        },
        "M": {
            wz.SCHRUPPEN: (115.0, 0.07, 28.0, 6.4),
            wz.VOLLNUT: (85.0, 0.055, 17.6, 16.0),
            wz.DYNAMISCH: (130.0, 0.055, 32.3, 2.6),
        },
        "K": {
            wz.SCHRUPPEN: (190.0, 0.095, 29.6, 7.2),
            wz.VOLLNUT: (135.0, 0.08, 19.2, 16.0),
            wz.DYNAMISCH: (215.0, 0.08, 32.3, 3.2),
        },
        "S": {
            wz.SCHRUPPEN: (55.0, 0.05, 23.2, 5.6),
            wz.VOLLNUT: (40.0, 0.04, 13.6, 16.0),
            wz.DYNAMISCH: (60.0, 0.045, 32.3, 1.8),
        },
    },
    20: {
        "P1": {
            wz.SCHRUPPEN: (210.0, 0.12, 37.0, 9.0),
            wz.VOLLNUT: (180.0, 0.1, 24.0, 20.0),
            wz.DYNAMISCH: (250.0, 0.105, 39.9, 4.0),
        },
        "P2": {
            wz.SCHRUPPEN: (175.0, 0.085, 37.0, 8.0),
            wz.VOLLNUT: (145.0, 0.07, 22.0, 20.0),
            wz.DYNAMISCH: (230.0, 0.085, 39.9, 3.8),
        },
        "M": {
            wz.SCHRUPPEN: (115.0, 0.085, 35.0, 8.0),
            wz.VOLLNUT: (85.0, 0.07, 22.0, 20.0),
            wz.DYNAMISCH: (130.0, 0.065, 39.9, 3.3),
        },
        "K": {
            wz.SCHRUPPEN: (190.0, 0.12, 37.0, 9.0),
            wz.VOLLNUT: (135.0, 0.1, 24.0, 20.0),
            wz.DYNAMISCH: (215.0, 0.105, 39.9, 4.0),
        },
        "S": {
            wz.SCHRUPPEN: (55.0, 0.06, 29.0, 7.0),
            wz.VOLLNUT: (40.0, 0.05, 17.0, 20.0),
            wz.DYNAMISCH: (60.0, 0.055, 39.9, 2.3),
        },
    },
    25: {
        "P1": {
            wz.SCHRUPPEN: (210.0, 0.15, 46.2, 11.2),
            wz.VOLLNUT: (180.0, 0.125, 30.0, 25.0),
            wz.DYNAMISCH: (250.0, 0.13, 51.3, 5.0),
        },
        "P2": {
            wz.SCHRUPPEN: (175.0, 0.105, 46.2, 10.0),
            wz.VOLLNUT: (145.0, 0.09, 27.5, 25.0),
            wz.DYNAMISCH: (230.0, 0.105, 51.3, 4.8),
        },
        "M": {
            wz.SCHRUPPEN: (115.0, 0.105, 43.7, 10.0),
            wz.VOLLNUT: (85.0, 0.09, 27.5, 25.0),
            wz.DYNAMISCH: (130.0, 0.085, 51.3, 4.1),
        },
        "K": {
            wz.SCHRUPPEN: (190.0, 0.15, 46.2, 11.2),
            wz.VOLLNUT: (135.0, 0.125, 30.0, 25.0),
            wz.DYNAMISCH: (215.0, 0.13, 51.3, 5.0),
        },
        "S": {
            wz.SCHRUPPEN: (55.0, 0.075, 36.3, 8.7),
            wz.VOLLNUT: (40.0, 0.06, 21.3, 25.0),
            wz.DYNAMISCH: (60.0, 0.065, 51.3, 2.9),
        },
    },
}

# --- Garant 208165 VHM-Entgrater spiralisiert 60°, TiSiN (Hoffmann Group) ------------------------
# Datenblätter der Hoffmann Group (Stand 2026-04): 4 Schneiden, Spitzenwinkel 60°, Spiralwinkel
# 35°, Schaft DIN 6535 HA h6; vc je Werkstoffgruppe, fz je Durchmesser in Stahl bis 900 N/mm².
# Gruppen: P1 Stahl < 750 N/mm²; P2 Stahl < 1100 N/mm²; M INOX < 900 N/mm²; K GG(G); N1 Alu
# (kurzspanend); N3 „Alu Kunststoffe“ (bedingt geeignet); S Ti > 850 N/mm²; H Stahl < 55 HRC
# (bedingt geeignet). Kupfer und Messing (N2) nennt das Datenblatt nicht.
GARANT_208165_SEITE = "https://www.hoffmann-group.com/DE/de/hom/p/208165-"
GARANT_208165_STAND = "Datenblatt der Hoffmann Group 04/2026"
# Ø → (Gesamtlänge L, fz in Stahl, Datenblatt oder "")
GARANT_208165_MASSE = {
    6: (57, 0.05, "https://assets.hoffmann-group.com/b/e/8/4/be8432e0-f1dd-40fd-9c6a-197e98089fe3/dsh_de-de_1851741.pdf"),
    8: (63, 0.06, ""),
    10: (72, 0.07, "https://assets.hoffmann-group.com/5/5/8/f/558f986f-b5e4-4417-a168-b5cf4f145fc2/dsh_de-de_1851748.pdf"),
    12: (83, 0.08, "https://assets.hoffmann-group.com/a/f/e/b/afebca43-5679-49c8-8a5c-3eef239082c6/dsh_de-de_1851746.pdf"),
    16: (93, 0.10, "https://assets.hoffmann-group.com/f/3/a/c/f3acfefc-c07d-4d5f-b375-40fed0a1216e/dsh_de-de_1851747.pdf"),
}  # fmt: skip
GARANT_208165_VC = {"P1": 115.0, "P2": 80.0, "M": 90.0, "K": 100.0, "N1": 300.0, "N3": 180.0,
                    "S": 50.0, "H": 35.0}  # fmt: skip
