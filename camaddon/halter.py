# SPDX-License-Identifier: LGPL-2.1-or-later
"""Werkzeughalter (W-002 Stufe D, spezifikation_halter.md).

Ein Halter sitzt zwischen Spindelnase und Werkzeug. Seine Kontur läuft von
der Spindelnase zum Werkzeug hin, in Abschnitten: je Länge, Ø oben (zur
Spindel) und Ø unten (zum Werkzeug) – gleiche Ø sind ein Zylinder, sonst ein
Kegel, rund um die Werkzeugachse. Was in der Spindel steckt, zählt nicht.
Die Spanntiefe sagt, wie tief der Schaft im Halter steckt; damit schätzt
werkzeuge.laenge_mit_halter() die Länge ab Spindelnase, solange niemand sie
gemessen hat.

Wie das Werkzeug zur Maschine steht, sagt der Halter (Stufe E, Manuel
2026-09-30): **gerade** – das Werkzeug in der Achse der Aufnahme, wie in einer
Frässpindel oder einem axialen VDI-Halter – oder **gewinkelt** – um `winkel`
gegen die Aufnahmeachse gekippt, um `drehung` um sie gedreht (von der
Bezugsrichtung X der Aufnahme aus), mit der Werkzeugachse `versatz` unter der
Aufnahme; bis dorthin reicht der Kopf. Dort liegt der Bezugspunkt: Von ihm aus
laufen die Kontur und die Länge des Werkzeugs längs der Werkzeugachse; beim
geraden Halter ist es die Spindelnase. lage() rechnet das.

Die Halter stehen in der Werkzeugbibliothek (werkzeuge.Bibliothek.halter),
jedes Werkzeug nennt die Kennung seines Halters. Läuft ohne Oberfläche.
"""

import math
import re
import uuid
from dataclasses import dataclass, field

from . import einheiten
from .sprache import tr
from .werkstoffe import mit_dezimalzeichen

# Die Werkzeugaufnahmen an der Spindel (W-022; Manuel, 2026-10-16: „die aufnahme an der maschine
# ... sollten wir in die maschine packen … natürlich muss man vorher die vollständigkeit der
# aufnahmen herstllen also nicht nur sk40 .. auch die anderen .. capto“): Name → (Norm, Ø des
# Flanschs, seine Länge ab der Spindelnase), in mm. Typische Maße zum Anfangen, keine
# Katalogwerte – wie die Vorlagen; „SK64“ gibt es nicht, gemeint ist wohl HSK-A63 (oder SK50).
# Die VDI-Halter des Revolvers haben ihre eigene Größe (maschine.vdi_groesse).
AUFNAHMEN = {
    "SK30": ("DIN 69871 / ISO 7388-1", 50.0, 19.1),
    "SK40": ("DIN 69871 / ISO 7388-1", 63.55, 19.1),
    "SK50": ("DIN 69871 / ISO 7388-1", 97.5, 19.1),
    "BT30": ("MAS 403 / JIS B 6339", 46.0, 20.0),
    "BT40": ("MAS 403 / JIS B 6339", 63.0, 27.0),
    "BT50": ("MAS 403 / JIS B 6339", 100.0, 38.0),
    "CAT40": ("ASME B5.50", 63.5, 19.1),
    "CAT50": ("ASME B5.50", 98.4, 19.1),
    "HSK-A32": ("DIN 69893 / ISO 12164", 32.0, 16.0),
    "HSK-A40": ("DIN 69893 / ISO 12164", 40.0, 20.0),
    "HSK-A50": ("DIN 69893 / ISO 12164", 50.0, 26.0),
    "HSK-A63": ("DIN 69893 / ISO 12164", 63.0, 26.0),
    "HSK-A80": ("DIN 69893 / ISO 12164", 80.0, 26.0),
    "HSK-A100": ("DIN 69893 / ISO 12164", 100.0, 29.0),
    "HSK-E32": ("DIN 69893 / ISO 12164", 32.0, 16.0),
    "HSK-E40": ("DIN 69893 / ISO 12164", 40.0, 20.0),
    "HSK-E50": ("DIN 69893 / ISO 12164", 50.0, 26.0),
    "HSK-F63": ("DIN 69893 / ISO 12164", 63.0, 26.0),
    "Capto C3": ("ISO 26623", 32.0, 15.0),
    "Capto C4": ("ISO 26623", 40.0, 18.0),
    "Capto C5": ("ISO 26623", 50.0, 20.0),
    "Capto C6": ("ISO 26623", 63.0, 22.0),
    "Capto C8": ("ISO 26623", 80.0, 30.0),
    "KM32": ("ISO 26622", 32.0, 15.0),
    "KM40": ("ISO 26622", 40.0, 18.0),
    "KM50": ("ISO 26622", 50.0, 20.0),
    "KM63": ("ISO 26622", 63.0, 22.0),
    "KM80": ("ISO 26622", 80.0, 30.0),
}
VORGABE_AUFNAHME = "SK40"  # ohne eingetragene Aufnahme – so waren die Vorlagen bis 0.260

# Wie ein Abschnitt aussieht (W-022 Punkt 3; Manuel, 2026-10-16, zum Bild eines HSK-Halters:
# „wenn die halter so ausschauen würden wäre cool .. also dem echten objekt nachempfunden“):
# FLANSCH der Flansch an der Spindel mit seiner Greiferrille, MUTTER die Spannmutter mit ihren
# Fasen; "" ein Zylinder oder Kegel, wie eingetragen. So zeichnen ihn das Bild und der Körper
# (profil, form). Reichweite, Wegkippen und 4 Achsen rechnen weiter mit dem vollen Abschnitt
# (radius_bei, groesster_durchmesser) – Rille und Fasen nehmen nur weg, das bleibt sicher.
FLANSCH, MUTTER = "flansch", "mutter"
# Die Flansche, gemessen an den Katalogzeichnungen bei hoffmann-group.com (P-2026-10-16-39;
# Manuel: „über die zeichnung ists vll doch leichter“): SK40 an 300470 und 302235 (Ø 63,55,
# 19,1 ab der Spindelnase), BT40 an 302760 32 (Ø 63, 27,0), HSK-A63 an 305390 32 (Ø 63, 26,0).
# Je Familie die Stücke ab der Spindelnase: (Länge in mm am gemessenen, Ø oben, Ø unten als
# Anteil am Ø des Flanschs); für eine andere Länge oder einen anderen Ø gestreckt. Vor dem Flansch
# von SK und BT steht der Kegel noch ein Stück aus der Spindel (Ø 44,45 an SK40).
_FLANSCHFORM = {
    "steil": (  # SK, CAT: Luft, Bund, V-Rille 3,4 tief, Bund
        (3.2, 0.70, 0.70),
        (5.0, 1.0, 1.0),
        (1.7, 1.0, 0.8875),
        (2.7, 0.8875, 0.8875),
        (1.7, 0.8875, 1.0),
        (4.8, 1.0, 1.0),
    ),
    "bt": (  # BT: Luft, breiter Bund, V-Rille 5 tief, Bund
        (1.9, 0.70, 0.70),
        (9.9, 1.0, 1.0),
        (2.7, 1.0, 0.843),
        (4.3, 0.843, 0.843),
        (2.6, 0.843, 1.0),
        (5.6, 1.0, 1.0),
    ),
    "hsk": (  # HSK (auch Capto, KM): Bund an der Plananlage, Rille weit hinten, Bund
        (14.9, 1.0, 1.0),
        (2.0, 1.0, 0.875),
        (2.4, 0.875, 0.875),
        (1.9, 0.875, 1.0),
        (4.8, 1.0, 1.0),
    ),
}
FLANSCH_MIN = 5.0  # mm – kürzer: ein Zylinder
# Die Spannmutter: vorn eine Fase unter 60° zur Achse, so lang (Anteil am Ø; ER32: 3,4 mm von
# Ø 50 auf 38,2), höchstens ein Drittel der Mutter.
MUTTER_FASE = 0.065
MUTTER_FASE_WINKEL = 60.0  # Grad zur Achse
_FLANSCH_SK40 = (19.1, 63.55, 63.55, FLANSCH)  # der erste Abschnitt der Vorlagen an der Spindel
# Flansche der Vorlagen bis 0.260.35 (SK und CAT 16 mm lang, SK40 Ø 63) – auch sie sind einer.
_ALTE_FLANSCHE = {(16.0, 50.0), (16.0, 63.0), (16.0, 97.5), (16.0, 63.5), (16.0, 98.4)}

# Vorlagen zum Anfangen, an SK40 nachgebaut nach den Katalogzeichnungen ihrer Vorbilder (VORBILD,
# P-2026-10-16-39) – (Spanntiefe, Abschnitte (Länge, Ø oben, Ø unten[, Art])), alles mm, ab der
# Spindelnase. Nach dem Flansch: die Rundung zum Körper, der Körper, beim Spannzangenfutter der
# Kegel auf den Gewindehals und die Mutter; beim Schrumpffutter der Kegel unter 4,5°. Mit einer
# anderen Aufnahme (AUFNAHMEN) bekommt eine Vorlage an der Spindel deren Flansch; der Körper
# darunter hängt am Spannsystem (ER32, Schrumpf …), nicht an der Aufnahme.
_VORLAGEN = {
    "er16": (
        20.0,
        (
            _FLANSCH_SK40,
            (4.8, 35.5, 28.0),
            (16.5, 28.0, 28.0),
            (3.0, 28.0, 22.0),
            (8.6, 22.0, 22.0),
            (18.0, 28.0, 28.0, MUTTER),
        ),
    ),
    "er25": (
        28.0,
        (
            _FLANSCH_SK40,
            (0.6, 43.7, 42.4),
            (16.3, 42.4, 42.4),
            (5.0, 42.4, 32.0),
            (8.0, 32.0, 32.0),
            (21.0, 42.0, 42.0, MUTTER),
        ),
    ),
    "er32": (
        40.0,
        (
            _FLANSCH_SK40,
            (1.0, 49.4, 48.0),
            (13.9, 48.0, 48.0),
            (4.0, 48.0, 40.0),
            (9.0, 40.0, 40.0),
            (23.0, 50.0, 50.0, MUTTER),
        ),
    ),
    "er40": (
        45.0,
        (
            _FLANSCH_SK40,
            (0.5, 49.3, 48.0),
            (15.4, 48.0, 48.0),
            (9.0, 50.0, 50.0),
            (26.0, 63.0, 63.0, MUTTER),
        ),
    ),
    "schrumpf_6": (
        26.0,
        (_FLANSCH_SK40, (2.0, 29.4, 27.1), (20.6, 27.1, 27.1), (38.3, 27.1, 21.0)),
    ),
    "schrumpf_12": (
        36.0,
        (_FLANSCH_SK40, (2.0, 34.4, 31.5), (11.3, 31.5, 31.5), (47.6, 31.5, 24.0)),
    ),
    # Lang und schlank (Manuel, 2026-10-24: „such auch nach neuen haltern von fräsern die schön
    # lang sind“) – für tiefe Stellen und 5 Achsen; nach den Zeichnungen ihrer Vorbilder. Die Kehle
    # nach dem Bund (gewölbt) in Sehnen, die außen liegen (an ER16 0,2 mm darüber); die Nase der
    # Schrumpffutter unter 4,5° und die Spannmutter der ER-Futter wie bei den kurzen (die
    # Zeichnung zeigt sie schwarz). Die Spanntiefe wie bei den kurzen und bei ER16 (das extra
    # schlanke) – die Seiten nennen keine.
    "er16_lang": (
        20.0,
        (
            _FLANSCH_SK40,
            (0.6, 43.5, 40.5),
            (2.0, 40.5, 36.6),
            (2.0, 36.6, 35.1),
            (4.0, 35.1, 34.2),
            (8.0, 34.2, 32.4),
            (8.0, 32.4, 30.8),
            (8.0, 30.8, 29.6),
            (8.0, 29.6, 28.8),
            (8.0, 28.8, 28.3),
            (62.7, 28.3, 28.3),
            (3.0, 28.3, 22.0),
            (8.6, 22.0, 22.0),
            (18.0, 28.0, 28.0, MUTTER),
        ),
    ),
    "er25_lang": (
        28.0,
        (
            _FLANSCH_SK40,
            (0.6, 44.0, 42.4),
            (106.3, 42.4, 42.4),
            (5.0, 42.4, 32.0),
            (8.0, 32.0, 32.0),
            (21.0, 42.0, 42.0, MUTTER),
        ),
    ),
    "schrumpf_6_lang": (
        26.0,
        (
            _FLANSCH_SK40,
            (1.7, 46.3, 41.9),
            (5.8, 41.9, 41.9),
            (4.2, 37.3, 37.3),
            (10.0, 37.3, 33.2),
            (10.0, 33.2, 30.1),
            (10.0, 30.1, 28.4),
            (11.0, 28.4, 27.1),
            (89.9, 27.1, 27.1),
            (38.3, 27.1, 21.0),
        ),
    ),
    "schrumpf_12_lang": (
        36.0,
        (
            _FLANSCH_SK40,
            (1.7, 43.5, 40.9),
            (6.0, 40.9, 40.9),
            (3.0, 40.0, 40.0),
            (11.0, 40.0, 35.6),
            (10.0, 35.6, 34.0),
            (10.0, 34.0, 32.9),
            (14.0, 32.9, 32.1),
            (74.4, 32.1, 32.1),
            (50.8, 32.1, 24.0),
        ),
    ),
    "spannzange_schlank": (
        20.0,
        (
            _FLANSCH_SK40,
            (0.5, 63.55, 35.4),
            (4.0, 35.4, 27.3),
            (135.3, 27.3, 12.9),
            (1.1, 12.9, 12.9),
        ),
    ),
    "weldon_20": (
        50.0,
        (_FLANSCH_SK40, (0.3, 53.3, 52.5), (30.8, 52.5, 52.5), (12.8, 52.5, 40.3)),
    ),
    "hydro_20": (
        50.0,
        (_FLANSCH_SK40, (19.3, 49.8, 49.8), (16.4, 48.3, 48.3), (9.5, 48.3, 39.3)),
    ),
    "aufsteck_22": (0.0, (_FLANSCH_SK40, (15.9, 48.0, 48.0))),
    "bohrfutter": (
        30.0,
        (_FLANSCH_SK40, (31.6, 43.0, 43.0), (29.0, 43.0, 22.0), (8.0, 22.0, 22.0)),
    ),
    # VDI30 axial mit ER25 nach HOLEX 319512 25 (A = 57 ab der Plananlage am Revolver): Kopf,
    # Hals, Mutter Ø 41,8.
    "vdi_er25": (28.0, ((21.7, 68.4, 68.4), (14.8, 32.0, 32.0), (20.5, 41.8, 41.8, MUTTER))),
    # Angetrieben je Spannzange: zuerst der Körper, zuletzt die Spannmutter.
    "vdi_radial_er16": (20.0, ((35.0, 50.0, 50.0), (20.0, 28.0, 28.0, MUTTER))),
    "vdi_radial_er20": (24.0, ((35.0, 50.0, 50.0), (22.0, 34.0, 34.0, MUTTER))),
    "vdi_radial_er25": (28.0, ((35.0, 50.0, 50.0), (24.0, 42.0, 42.0, MUTTER))),
    "vdi_radial_er32": (40.0, ((35.0, 60.0, 60.0), (28.0, 50.0, 50.0, MUTTER))),
    "vdi_axial_er16": (20.0, ((45.0, 55.0, 55.0), (25.0, 28.0, 28.0, MUTTER))),
    "vdi_axial_er20": (24.0, ((45.0, 55.0, 55.0), (25.0, 34.0, 34.0, MUTTER))),
    "vdi_axial_er25": (28.0, ((45.0, 55.0, 55.0), (27.0, 42.0, 42.0, MUTTER))),
    "vdi_axial_er32": (40.0, ((45.0, 60.0, 60.0), (30.0, 50.0, 50.0, MUTTER))),
    "winkelkopf_90": (25.0, ((30.0, 60.0, 60.0), (20.0, 32.0, 32.0))),
}
VORLAGEN = tuple(_VORLAGEN)  # in der Reihenfolge des Menüs
# Die Vorbilder der Vorlagen an SK40 – Artikel bei hoffmann-group.com (Manuel, 2026-10-16: „man
# kann ja auf das produkt verlinken“). An einer anderen Aufnahme verlinkt die Vorlage die Suche
# nach ihrer Art an dieser Aufnahme (SUCHE).
VORBILD = {
    "er16": "300470-16",
    "er25": "300470-25",
    "er32": "300470-32",
    "er40": "300470-40",
    "schrumpf_6": "302235-6",
    "schrumpf_12": "302235-12",
    "er16_lang": "300530-16",
    "er25_lang": "300530-25",
    "schrumpf_6_lang": "302278-6",
    "schrumpf_12_lang": "302278-12",
    "spannzange_schlank": "300784-2-6",
    "weldon_20": "300100-20",
    "hydro_20": "302028-20",
    "aufsteck_22": "301017-22",
    "bohrfutter": "302540-1-13",
    "vdi_er25": "319512-25",  # an VDI30
}
SUCHE = {
    "er16": "ER-Spannzangenfutter {aufnahme} ER16",
    "er25": "ER-Spannzangenfutter {aufnahme} ER25",
    "er32": "ER-Spannzangenfutter {aufnahme} ER32",
    "er40": "ER-Spannzangenfutter {aufnahme} ER40",
    "schrumpf_6": "Schrumpffutter {aufnahme} 6",
    "schrumpf_12": "Schrumpffutter {aufnahme} 12",
    "er16_lang": "ER-Spannzangenfutter {aufnahme} A = 160 ER16",
    "er25_lang": "ER-Spannzangenfutter {aufnahme} A = 160 ER25",
    "schrumpf_6_lang": "Schrumpffutter {aufnahme} A = 200 6",
    "schrumpf_12_lang": "Schrumpffutter {aufnahme} A = 200 12",
    "spannzange_schlank": "Spannzangenfutter extra schlank {aufnahme}",
    "weldon_20": "Flächenspannfutter {aufnahme} 20",
    "hydro_20": "Hydrodehnspannfutter {aufnahme} 20",
    "aufsteck_22": "Messerkopfaufnahme {aufnahme} 22",
    "bohrfutter": "Kurzbohrfutter {aufnahme}",
    "vdi_er25": "ER-Spannzangenhalter {aufnahme} ER25",
}
# Normreihen (Manuel, 2026-10-25 02:27: „extra lange aufnahmen .. wäre echt cool wenn du die
# halterdatenbank deutlichst erweiterst ... so richtig richtig dolle“): je Spannsystem alle Größen
# und Längen A (ab der Spindelnase, bis zur Stirn), an jeder Aufnahme. Die Kontur gerechnet aus
# typischen Maßen nach der Norm – keine Katalogwerte, kein Katalog nachgebaut (wie die Vorlagen:
# mit dem eigenen Halter vergleichen). Schlüssel „reihe:<Art>:<Größe>:<A>“.
REIHE = "reihe"
SCHRUMPF, ER, WELDON, HYDRO = "schrumpf", "er", "weldon", "hydro"
REIHEN = (SCHRUMPF, ER, WELDON, HYDRO)  # in der Reihenfolge des Menüs
REIHE_NORM = {
    SCHRUMPF: "DIN 69882-8",
    ER: "DIN ISO 15488",
    WELDON: "DIN 69882-4",
    HYDRO: "DIN 69882-7",
}
# Schrumpffutter, Nase unter 4,5°: Spann-Ø → (Ø der Nase, Spanntiefe). 6 bis 32 die Nasen der
# Norm (21/24/27/33/44); 3 bis 5 schlank, wie sie üblich sind.
SCHRUMPF_MASSE = {
    3.0: (10.0, 15.0),
    4.0: (11.0, 18.0),
    5.0: (13.0, 22.0),
    6.0: (21.0, 36.0),
    8.0: (21.0, 36.0),
    10.0: (24.0, 41.0),
    12.0: (24.0, 46.0),
    14.0: (27.0, 46.0),
    16.0: (27.0, 49.0),
    18.0: (33.0, 49.0),
    20.0: (33.0, 51.0),
    25.0: (44.0, 57.0),
    32.0: (44.0, 61.0),
}
SCHRUMPF_KEGEL = 4.5  # Grad je Seite
SCHRUMPF_NASE_DAZU = 8.0  # mm: so viel dicker als die Nase ist der schlanke Körper dahinter
SCHRUMPF_LAENGEN = (80.0, 120.0, 160.0, 200.0, 250.0, 300.0)
# ER: Größe → (Ø und Länge der Spannmutter, Spanntiefe, größter Schaft-Ø).
ER_MASSE = {
    "ER11": (19.0, 11.5, 18.0, 7.0),
    "ER16": (28.0, 18.0, 20.0, 10.0),
    "ER20": (34.0, 20.0, 24.0, 13.0),
    "ER25": (42.0, 21.0, 28.0, 16.0),
    "ER32": (50.0, 23.0, 40.0, 20.0),
    "ER40": (63.0, 26.0, 45.0, 26.0),
}
ER_LAENGEN = (70.0, 100.0, 160.0, 200.0, 250.0)
# Weldon und Hydrodehn: Spann-Ø → Ø vorn (Weldon: der Körper), Spanntiefe = Schaftlänge nach
# DIN 1835.
SCHAFTLAENGE = {
    6.0: 36.0,
    8.0: 36.0,
    10.0: 40.0,
    12.0: 45.0,
    14.0: 45.0,
    16.0: 48.0,
    18.0: 48.0,
    20.0: 50.0,
    25.0: 56.0,
    32.0: 60.0,
}
WELDON_D = {6.0: 25.0, 8.0: 28.0, 10.0: 35.0, 12.0: 42.0, 14.0: 44.0, 16.0: 48.0, 18.0: 50.0}
WELDON_D.update({20.0: 52.0, 25.0: 65.0, 32.0: 72.0})
WELDON_LAENGEN = (50.0, 63.0, 80.0, 100.0, 160.0)
HYDRO_D = {6.0: 26.0, 8.0: 28.0, 10.0: 30.0, 12.0: 32.0, 14.0: 34.0, 16.0: 38.0, 18.0: 40.0}
HYDRO_D.update({20.0: 40.0, 25.0: 50.0, 32.0: 60.0})
HYDRO_LAENGEN = (80.0, 100.0, 120.0, 150.0, 200.0)
REIHE_GROESSEN = {
    SCHRUMPF: tuple(SCHRUMPF_MASSE),
    ER: tuple(ER_MASSE),
    WELDON: tuple(SCHAFTLAENGE),
    HYDRO: tuple(SCHAFTLAENGE),
}
REIHE_LAENGEN = {
    SCHRUMPF: SCHRUMPF_LAENGEN,
    ER: ER_LAENGEN,
    WELDON: WELDON_LAENGEN,
    HYDRO: HYDRO_LAENGEN,
}
EXTRA_LANG_AB = 250.0  # mm: ab da heißt es „extra lang“, ab LANG_AB „lang“
LANG_AB = 160.0
REIHE_SUCHE = {
    SCHRUMPF: "Schrumpffutter {aufnahme} {groesse} A = {a}",
    ER: "ER-Spannzangenfutter {aufnahme} {groesse} A = {a}",
    WELDON: "Flächenspannfutter {aufnahme} {groesse}",
    HYDRO: "Hydrodehnspannfutter {aufnahme} {groesse}",
}

KATALOG_ARTIKEL = "https://www.hoffmann-group.com/DE/de/hom/p/{artikel}"
KATALOG_SUCHE = "https://www.hoffmann-group.com/DE/de/hom/v2/search?search={begriff}"
# Die angetriebenen VDI-Halter gibt es je Spannzange (Manuel, 2026-10-02: „warum bekomme ich bei
# dem VDI angetrieben radial und axial nur ER16?“) – im Menü „Neu“ je ein Untermenü:
# Gruppe → {Spannzange: Vorlage}.
GRUPPEN = {
    gruppe: {er: f"{gruppe}_{er.lower()}" for er in ("ER16", "ER20", "ER25", "ER32")}
    for gruppe in ("vdi_radial", "vdi_axial")
}
# Gewinkelte Vorlagen: (Winkel, Drehung in Grad, Versatz, Kopf-Ø in mm).
_GEWINKELT = {
    **dict.fromkeys(GRUPPEN["vdi_radial"].values(), (90.0, 0.0, 55.0, 55.0)),
    "winkelkopf_90": (90.0, 0.0, 110.0, 80.0),
}
# Die VDI-Vorlagen nennen keine Größe (Manuel, 2026-09-30: „man wird auf eine VDI 40 maschine
# keine VDI 30 halter verbauen können … also reicht VDI halter aus“): Ihre Beispielmaße gelten
# für VDI 30; mit der VDI-Größe der Maschine (maschine.vdi_groesse) wachsen die Ø des Körpers
# mit, und der Name nennt sie („VDI40 angetrieben radial · ER16“). Die Spannmutter (der letzte
# Abschnitt) bleibt: Ihr Ø hängt an der Spannzange, nicht an der Aufnahme.
VDI_VORLAGEN = ("vdi_er25", *(v for g in GRUPPEN.values() for v in g.values()))
VDI_BEZUG = 30.0  # mm: dafür gelten die Beispielmaße
# Die Schlüssel bis 0.33.0 – dieselben Vorlagen für VDI 30.
_ALTE_SCHLUESSEL = {
    "vdi30_er25": "vdi_er25",
    "vdi30_radial": "vdi_radial_er16",
    "vdi30_axial": "vdi_axial_er16",
}
# Bis 0.122 gab es angetrieben nur ER16; die Gruppe allein heißt weiter ER16.
_OHNE_SPANNZANGE = {gruppe: vorlagen["ER16"] for gruppe, vorlagen in GRUPPEN.items()}

GERADE, GEWINKELT = "gerade", "gewinkelt"  # Halter.richtung


def aufnahme_oder_vorgabe(aufnahme):
    """Die Aufnahme, wenn sie bekannt ist (AUFNAHMEN) – sonst VORGABE_AUFNAHME."""
    return aufnahme if aufnahme in AUFNAHMEN else VORGABE_AUFNAHME


def vorlage_text(schluessel, vdi=0, aufnahme=None):
    """Name einer Vorlage: „Spannzangenfutter ER32 · SK40“ – mit der Aufnahme `aufnahme`
    (AUFNAHMEN; ohne: SK40). Die VDI-Vorlagen nennen die Größe `vdi` (mm), wenn eine bekannt ist:
    „VDI40 angetrieben radial · ER16“, sonst „VDI angetrieben radial · ER16“."""
    schluessel, vdi = _vorlage(schluessel, vdi)
    aufnahme = aufnahme_oder_vorgabe(aufnahme)
    if ist_reihe(schluessel):
        return reihe_text(schluessel, aufnahme)
    groesse = f"{vdi:g}" if vdi else ""
    for gruppe, vorlagen in GRUPPEN.items():
        for er, vorlage in vorlagen.items():
            if vorlage == schluessel:
                return {
                    "vdi_radial": tr("halter.vorlage.vdi_radial", groesse=groesse, er=er),
                    "vdi_axial": tr("halter.vorlage.vdi_axial", groesse=groesse, er=er),
                }[gruppe]
    return {
        "er16": tr("halter.vorlage.er16", aufnahme=aufnahme),
        "er25": tr("halter.vorlage.er25", aufnahme=aufnahme),
        "er32": tr("halter.vorlage.er32", aufnahme=aufnahme),
        "er40": tr("halter.vorlage.er40", aufnahme=aufnahme),
        "schrumpf_6": tr("halter.vorlage.schrumpf_6", aufnahme=aufnahme),
        "schrumpf_12": tr("halter.vorlage.schrumpf_12", aufnahme=aufnahme),
        "er16_lang": tr("halter.vorlage.er16_lang", aufnahme=aufnahme),
        "er25_lang": tr("halter.vorlage.er25_lang", aufnahme=aufnahme),
        "schrumpf_6_lang": tr("halter.vorlage.schrumpf_6_lang", aufnahme=aufnahme),
        "schrumpf_12_lang": tr("halter.vorlage.schrumpf_12_lang", aufnahme=aufnahme),
        "spannzange_schlank": tr("halter.vorlage.spannzange_schlank", aufnahme=aufnahme),
        "weldon_20": tr("halter.vorlage.weldon_20", aufnahme=aufnahme),
        "hydro_20": tr("halter.vorlage.hydro_20", aufnahme=aufnahme),
        "aufsteck_22": tr("halter.vorlage.aufsteck_22", aufnahme=aufnahme),
        "bohrfutter": tr("halter.vorlage.bohrfutter", aufnahme=aufnahme),
        "vdi_er25": tr("halter.vorlage.vdi_er25", groesse=groesse),
        "winkelkopf_90": tr("halter.vorlage.winkelkopf_90", aufnahme=aufnahme),
    }[schluessel]


def reihe(art, groesse, laenge):
    """Der Schlüssel einer Normreihe: „reihe:schrumpf:12:200“."""
    return f"{REIHE}:{art}:{groesse if isinstance(groesse, str) else f'{float(groesse):g}'}:" + (
        f"{float(laenge):g}"
    )


def ist_reihe(schluessel):
    """Ist es der Schlüssel einer Normreihe (reihe)?"""
    return isinstance(schluessel, str) and schluessel.startswith(REIHE + ":")


def _reihe_lesen(schluessel):
    """(Art, Größe, A) – die Größe als Zahl (Spann-Ø), bei ER der Name („ER25“). KeyError, wenn es
    die Reihe oder Größe nicht gibt."""
    _r, art, groesse, laenge = schluessel.split(":")
    if art not in REIHEN:
        raise KeyError(schluessel)
    groesse = groesse if art == ER else float(groesse)
    if groesse not in REIHE_GROESSEN[art]:
        raise KeyError(schluessel)
    return art, groesse, float(laenge)


def laengen_text(laenge):
    """„A 200“, „A 200 lang“, „A 300 extra lang“."""
    if laenge >= EXTRA_LANG_AB:
        return tr("halter.reihe.extra_lang", a=f"{laenge:g}")
    if laenge >= LANG_AB:
        return tr("halter.reihe.lang", a=f"{laenge:g}")
    return tr("halter.reihe.a", a=f"{laenge:g}")


def reihe_text(schluessel, aufnahme=None):
    """„Schrumpffutter Ø12 · A 200 lang · SK40“."""
    art, groesse, laenge = _reihe_lesen(schluessel)
    groesse_ = groesse if art == ER else f"Ø{groesse:g}"
    werte = {
        "groesse": groesse_,
        "laenge": laengen_text(laenge),
        "aufnahme": aufnahme_oder_vorgabe(aufnahme),
    }
    # Die Schlüssel wörtlich – so findet sie die Sprachprüfung (test_sprache).
    if art == SCHRUMPF:
        return tr("halter.reihe.schrumpf", **werte)
    if art == ER:
        return tr("halter.reihe.er", **werte)
    if art == WELDON:
        return tr("halter.reihe.weldon", **werte)
    return tr("halter.reihe.hydro", **werte)


def reihe_gruppe_text(art):
    """Titel eines Untermenüs der Normreihen: „Schrumpffutter (DIN 69882-8)“."""
    norm = REIHE_NORM[art]
    if art == SCHRUMPF:
        return tr("halter.reihe.gruppe.schrumpf", norm=norm)
    if art == ER:
        return tr("halter.reihe.gruppe.er", norm=norm)
    if art == WELDON:
        return tr("halter.reihe.gruppe.weldon", norm=norm)
    return tr("halter.reihe.gruppe.hydro", norm=norm)


def reihe_groesse_text(art, groesse):
    """„Ø12“, „ER25“ – eine Größe im Untermenü."""
    return groesse if art == ER else f"Ø{float(groesse):g}"


def _reihe(schluessel, flansch_d):
    """(Spanntiefe, Abschnitte nach dem Flansch, Länge danach) einer Normreihe – die Kontur von
    der Spindel zur Stirn, A ab der Spindelnase. Der Körper nicht dicker als 0,76 · Ø des Flanschs
    (an SK40 48 mm, wie bei den Vorlagen)."""
    art, groesse, laenge = _reihe_lesen(schluessel)
    koerper_max = 0.76 * flansch_d
    if art == SCHRUMPF:
        nase, tiefe = SCHRUMPF_MASSE[groesse]
        steigung = 2.0 * math.tan(math.radians(SCHRUMPF_KEGEL))  # Ø je mm
        koerper_max = max(koerper_max, nase + SCHRUMPF_NASE_DAZU)  # ein kleiner Flansch (BT30)
        return tiefe, lambda rest: _schrumpf(rest, nase, steigung, koerper_max)
    if art == ER:
        mutter_d, mutter_l, tiefe, _schaft = ER_MASSE[groesse]
        return tiefe, lambda rest: _er(rest, mutter_d, mutter_l, koerper_max)
    if art == WELDON:
        d = min(WELDON_D[groesse], koerper_max)
        return SCHAFTLAENGE[groesse], lambda rest: _weldon(rest, d)
    d = min(HYDRO_D[groesse], koerper_max)
    return SCHAFTLAENGE[groesse], lambda rest: _hydro(rest, d)


def _schrumpf(rest, nase, steigung, koerper_max):
    """Schrumpffutter: vorn die Nase unter 4,5° auf SCHRUMPF_NASE_DAZU dicker, dahinter schlank
    bis zum Flansch – lang mit einem Übergang auf den dicken Körper davor (25 mm), kurz nur ein
    Bund (wie die Vorlagen nach ihren Vorbildern)."""
    kegel = min(SCHRUMPF_NASE_DAZU / steigung, max(rest - 13.0, 1.0))
    schlank = min(nase + steigung * kegel, koerper_max)
    kegel = (schlank - nase) / steigung
    uebrig = rest - kegel
    teile = []
    if uebrig > 45.0:
        dick = min(koerper_max, schlank + 12.0)
        teile.append((25.0, dick, schlank))
        uebrig -= 25.0
    teile += [(max(uebrig, 0.0), schlank, schlank), (kegel, schlank, nase)]
    return teile


def _er(rest, mutter_d, mutter_l, koerper_max):
    """ER-Spannzangenfutter: der Körper so dick wie die Mutter (höchstens wie die Vorlagen), ein
    Kegel auf den Gewindehals (0,8 · Mutter, 8,5 mm lang), die Mutter."""
    koerper = min(mutter_d, koerper_max)
    hals = 0.8 * mutter_d
    kegel = max((koerper - hals) / 2.0, 0.0) if koerper > hals else 0.0
    koerper_l = max(rest - mutter_l - 8.5 - kegel, 1.0)
    teile = [(koerper_l, koerper, koerper)]
    if kegel > 0:
        teile.append((kegel, koerper, hals))
    teile += [(8.5, hals, hals), (mutter_l, mutter_d, mutter_d, MUTTER)]
    return teile


def _weldon(rest, d):
    """Weldon-Aufnahme: ein Zylinder, vorn auf 0,77 · Ø abgeschrägt (12,8 mm an Ø 52,5)."""
    schraege = min(0.25 * d, max(rest - 1.0, 1.0))
    return [(max(rest - schraege, 1.0), d, d), (schraege, d, 0.77 * d)]


def _hydro(rest, d):
    """Hydrodehnspannfutter: der Körper 9 mm dicker als vorn, vorn ein Kegel von 9,5 mm."""
    dick = d + 9.0
    return [(max(rest - 9.5, 1.0), dick, dick), (9.5, dick, d)]


def gruppe_text(gruppe, vdi=0):
    """Titel eines Untermenüs (GRUPPEN): „VDI40 angetrieben radial“, ohne Größe „VDI angetrieben
    radial“."""
    groesse = f"{float(vdi):g}" if vdi else ""
    return {
        "vdi_radial": tr("halter.gruppe.vdi_radial", groesse=groesse),
        "vdi_axial": tr("halter.gruppe.vdi_axial", groesse=groesse),
    }[gruppe]


def _zahl(wert):
    """Ein Maß aus der Datei: eine Zahl, nicht negativ; Unlesbares wird 0."""
    try:
        return max(float(wert), 0.0)
    except (TypeError, ValueError):
        return 0.0


def _winkel(wert, standard):
    """Ein Winkel aus der Datei (Grad), endlich; Unlesbares wird `standard`."""
    try:
        zahl = float(wert)
    except (TypeError, ValueError):
        return standard
    return zahl if abs(zahl) < 1e6 else standard


@dataclass
class Abschnitt:
    """Ein Stück der Kontur: Zylinder (gleiche Ø) oder Kegel, alles in mm."""

    laenge: float = 0.0  # entlang der Werkzeugachse
    d_oben: float = 0.0  # zur Spindel hin
    d_unten: float = 0.0  # zum Werkzeug hin
    art: str = ""  # FLANSCH, MUTTER – so sieht er aus (profil); "" wie eingetragen

    def als_dict(self):
        return {
            "laenge": self.laenge,
            "d_oben": self.d_oben,
            "d_unten": self.d_unten,
            "art": self.art,
        }

    @classmethod
    def aus_dict(cls, daten):
        art = daten.get("art")
        return cls(
            _zahl(daten.get("laenge")),
            _zahl(daten.get("d_oben")),
            _zahl(daten.get("d_unten")),
            art if art in (FLANSCH, MUTTER) else "",
        )


@dataclass
class Halter:
    """Ein Halter – eine Beschreibung, kein einzelnes Stück: Mehrere Werkzeuge können
    denselben haben."""

    kennung: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    bezeichnung: str = ""  # frei: Hersteller, Bestellnummer …
    spanntiefe: float = 0.0  # mm: so tief steckt der Schaft im Halter
    abschnitte: list = field(default_factory=list)  # vom Bezugspunkt zum Werkzeug hin
    richtung: str = GERADE  # GERADE oder GEWINKELT
    winkel: float = 90.0  # Grad zwischen Aufnahmeachse und Werkzeugachse (gewinkelt)
    drehung: float = 0.0  # Grad um die Aufnahmeachse, von ihrer Bezugsrichtung X aus
    versatz: float = 0.0  # mm längs der Aufnahmeachse bis zur Werkzeugachse (gewinkelt)
    kopf_d: float = 0.0  # mm: Ø des Kopfs von der Aufnahme bis zum Bezugspunkt
    aufnahme: str = ""  # an der Spindel: „SK40“, „HSK-A63“ … (AUFNAHMEN); "" unbekannt
    link: str = ""  # die Seite des Halters im Katalog (oder die Suche danach)
    # mm: genau diesen Schaft spannt er (Schrumpf-, Hydrodehn-, Weldonfutter aus dem Katalog der
    # Hersteller); 0: nicht bekannt, oder eine Spannzange (dann sagt es der Name, „ER16“).
    spann_d: float = 0.0

    @property
    def gewinkelt(self):
        return self.richtung == GEWINKELT

    @property
    def laenge(self):
        """Vom Bezugspunkt bis zur Nase des Halters, in mm – beim geraden Halter von der
        Spindelnase (im Katalog meist „A“)."""
        return sum(a.laenge for a in self.abschnitte)

    @property
    def groesster_durchmesser(self):
        return max((max(a.d_oben, a.d_unten) for a in self.abschnitte), default=0.0)

    def radius_bei(self, abstand):
        """Der Radius im Abstand `abstand` (mm) unter der Spindelnase – im Kegel dazwischen
        geradlinig; 0 außerhalb des Halters. An einer Stufe gilt der größere Radius."""
        if abstand < 0:
            return 0.0
        oben = 0.0
        radius = 0.0
        for a in self.abschnitte:
            unten = oben + a.laenge
            if oben <= abstand <= unten and a.laenge > 0:
                anteil = (abstand - oben) / a.laenge
                radius = max(radius, (a.d_oben + anteil * (a.d_unten - a.d_oben)) / 2)
            oben = unten
        return radius

    def kontur(self):
        """Die Kontur als Punkte (Abstand unter der Spindelnase, Radius) von oben nach unten –
        je Stück des Profils (profil) Anfang und Ende; zum Zeichnen."""
        punkte = []
        oben = 0.0
        for laenge, d_oben, d_unten in profil(self):
            punkte.append((oben, d_oben / 2))
            oben += laenge
            punkte.append((oben, d_unten / 2))
        return punkte

    def als_dict(self):
        return {
            "kennung": self.kennung,
            "name": self.name,
            "bezeichnung": self.bezeichnung,
            "spanntiefe": self.spanntiefe,
            "abschnitte": [a.als_dict() for a in self.abschnitte],
            "richtung": self.richtung,
            "winkel": self.winkel,
            "drehung": self.drehung,
            "versatz": self.versatz,
            "kopf_d": self.kopf_d,
            "aufnahme": self.aufnahme,
            "link": self.link,
            "spann_d": self.spann_d,
        }

    @classmethod
    def aus_dict(cls, daten):
        """Liest einen Eintrag; Unlesbares wird durch den Standardwert ersetzt."""
        h = cls()
        h.kennung = str(daten.get("kennung") or h.kennung)
        h.name = str(daten.get("name") or "")
        h.bezeichnung = str(daten.get("bezeichnung") or "")
        h.spanntiefe = _zahl(daten.get("spanntiefe"))
        abschnitte = daten.get("abschnitte")
        if isinstance(abschnitte, list):
            abschnitte = [a for a in abschnitte if isinstance(a, dict)]
            h.abschnitte = [Abschnitt.aus_dict(a) for a in abschnitte]
            if h.abschnitte and not any("art" in a for a in abschnitte):
                _flansch_erkennen(h.abschnitte[0])  # gespeichert vor 0.260.35
        h.richtung = GEWINKELT if daten.get("richtung") == GEWINKELT else GERADE
        h.winkel = min(max(_winkel(daten.get("winkel"), 90.0), 0.0), 180.0)
        h.drehung = _winkel(daten.get("drehung"), 0.0)
        h.versatz = _zahl(daten.get("versatz"))
        h.kopf_d = _zahl(daten.get("kopf_d"))
        h.aufnahme = str(daten.get("aufnahme") or "")
        h.link = str(daten.get("link") or "")
        h.spann_d = _zahl(daten.get("spann_d"))
        return h


def _flansch_erkennen(abschnitt):
    """Ein Abschnitt aus der Zeit vor Abschnitt.art: so lang und dick wie der Flansch einer
    Aufnahme (AUFNAHMEN, oder einer der Vorlagen bis 0.260.35) – dann ist er einer."""
    if abschnitt.d_oben != abschnitt.d_unten:
        return
    masse = (abschnitt.laenge, abschnitt.d_oben)
    if masse in _ALTE_FLANSCHE or any(masse == (l_, d) for _n, d, l_ in AUFNAHMEN.values()):
        abschnitt.art = FLANSCH


def profil(halter):
    """Die Abschnitte, wie der Halter aussieht – (Länge, Ø oben, Ø unten) von oben nach unten:
    der Flansch (FLANSCH) mit seiner Greiferrille und Fasen, die Spannmutter (MUTTER) mit Fasen,
    die anderen wie eingetragen. Nie dicker als der Abschnitt."""
    form = _FLANSCHFORM[flanschfamilie(halter.aufnahme)]
    stuecke = []
    for a in halter.abschnitte:
        if a.laenge <= 0:
            continue
        if a.art == FLANSCH and a.d_oben == a.d_unten:
            stuecke += _flansch_profil(a.laenge, a.d_oben, form)
        elif a.art == MUTTER and a.d_oben == a.d_unten:
            stuecke += _mutter_profil(a.laenge, a.d_oben)
        else:
            stuecke.append((a.laenge, a.d_oben, a.d_unten))
    return stuecke


def flanschfamilie(aufnahme):
    """Welche Flanschform (_FLANSCHFORM) eine Aufnahme hat: „steil“ (SK, CAT – auch ohne
    eingetragene), „bt“ oder „hsk“ (HSK, Capto, KM)."""
    aufnahme = aufnahme_oder_vorgabe(aufnahme)
    if aufnahme.startswith("BT"):
        return "bt"
    return "steil" if aufnahme.startswith(("SK", "CAT")) else "hsk"


def _flansch_profil(laenge, d, form):
    """Der Flansch in der Form seiner Familie (_FLANSCHFORM), auf seine Länge und seinen Ø
    gestreckt. Zu kurz dafür: ein Zylinder."""
    if laenge < FLANSCH_MIN:
        return [(laenge, d, d)]
    faktor = laenge / sum(stueck[0] for stueck in form)
    return [(lang * faktor, oben * d, unten * d) for lang, oben, unten in form]


def _mutter_profil(laenge, d):
    """Die Spannmutter: ihr Ø, vorn die Fase unter MUTTER_FASE_WINKEL zur Achse."""
    vorn = min(MUTTER_FASE * d, laenge / 3)
    quer = vorn * math.tan(math.radians(MUTTER_FASE_WINKEL))
    if d - 2 * quer <= 0:
        return [(laenge, d, d)]
    return [(laenge - vorn, d, d), (vorn, d, d - 2 * quer)]


def lage(halter):
    """Wie das Werkzeug in der Aufnahme sitzt (FreeCAD.Placement im LCS der Aufnahme): sein
    Bezugspunkt und seine Achse, Z von der Spitze weg. Ohne Halter und beim geraden Halter
    keine Verschiebung und keine Drehung. Die Spitze zeigt dann in Richtung
    (sin α · cos β, sin α · sin β, −cos α) mit α = winkel und β = drehung."""
    import FreeCAD

    if halter is None or not halter.gewinkelt:
        return FreeCAD.Placement()
    drehung = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), halter.drehung).multiply(
        FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), -halter.winkel)
    )
    return FreeCAD.Placement(FreeCAD.Vector(0, 0, -halter.versatz), drehung)


def seitlich(halter):
    """So weit reicht der Halter seitlich über die Werkzeugachse hinaus (mm): sein halber
    größter Ø, beim gewinkelten auch der Kopf – er endet um seinen Radius hinter der
    Werkzeugachse. 0 ohne Halter. Rundum (W-003) muss vor dem Futter so viel Platz sein,
    wenn es weiter ist als der Fräserradius – wie der Halter an der Maschine steht, weiß die
    Operation nicht, so ist es auf jeder Seite genug."""
    if halter is None:
        return 0.0
    breite = halter.groesster_durchmesser / 2
    if halter.gewinkelt and halter.versatz > 0:
        breite = max(breite, halter.kopf_d / 2)
    return breite


def form(halter):
    """Der Halter als Körper im LCS der Aufnahme: die Aufnahme bei Z = 0. Beim geraden zeigt
    das Werkzeug nach −Z; je Abschnitt ein Zylinder oder Kegel. Beim gewinkelten der Kopf –
    ein Zylinder längs der Aufnahmeachse bis über den Bezugspunkt hinaus, um seinen Radius
    (dort sitzt das Winkelgetriebe) –, dann die Abschnitte längs der Werkzeugachse
    (lage()). None ohne Kontur."""
    import FreeCAD
    import Part

    abgang = _abschnitte_form(halter)
    if not halter.gewinkelt:
        return abgang
    teile = [] if abgang is None else [abgang.transformed(lage(halter).toMatrix())]
    if halter.kopf_d > 0 and halter.versatz > 0:
        kopf = Part.makeCylinder(
            halter.kopf_d / 2,
            halter.versatz + halter.kopf_d / 2,
            FreeCAD.Vector(0, 0, 0),
            FreeCAD.Vector(0, 0, -1),
        )
        teile.append(kopf)
    return Part.makeCompound(teile) if teile else None


def _abschnitte_form(halter):
    """Die Abschnitte als Körper, wie er aussieht (profil): der Bezugspunkt bei Z = 0, das
    Werkzeug nach −Z."""
    import FreeCAD
    import Part

    teile = []
    oben = 0.0
    nach_unten = FreeCAD.Vector(0, 0, -1)
    for laenge, d_oben, d_unten in profil(halter):
        basis = FreeCAD.Vector(0, 0, -oben)
        r1, r2 = d_oben / 2, d_unten / 2
        if abs(r1 - r2) < 1e-9:
            if r1 > 0:
                teile.append(Part.makeCylinder(r1, laenge, basis, nach_unten))
        else:
            teile.append(Part.makeCone(r1, r2, laenge, basis, nach_unten))
        oben += laenge
    return Part.makeCompound(teile) if teile else None


def aus_vorlage(schluessel, vdi=None, aufnahme=None):
    """Ein neuer Halter aus einer Vorlage – mit Beispielmaßen, die die Bezeichnung nennt.
    `vdi`: die VDI-Größe der Maschine (mm) für die VDI-Vorlagen – die Ø des Körpers wachsen von
    VDI 30 aus mit (die Spannmutter nicht), der Name nennt sie; ohne Angabe die Maße für VDI 30
    und ein Name ohne Größe. `aufnahme`: die Aufnahme der Spindel (AUFNAHMEN) für die anderen –
    der Flansch statt dem von SK40, der Name nennt sie; ohne Angabe SK40."""
    schluessel, vdi = _vorlage(schluessel, vdi)
    if ist_reihe(schluessel):
        return _aus_reihe(schluessel, aufnahme)
    spanntiefe, abschnitte = _VORLAGEN[schluessel]
    faktor = vdi / VDI_BEZUG if vdi else 1.0
    an_der_spindel = schluessel not in VDI_VORLAGEN
    aufnahme = aufnahme_oder_vorgabe(aufnahme) if an_der_spindel else ""
    if an_der_spindel and abschnitte and tuple(abschnitte[0]) == _FLANSCH_SK40:
        _norm, flansch_d, flansch_l = AUFNAHMEN[aufnahme]
        abschnitte = ((flansch_l, flansch_d, flansch_d, FLANSCH), *abschnitte[1:])
    halter = Halter(
        name=vorlage_text(schluessel, vdi, aufnahme),
        aufnahme=aufnahme,
        bezeichnung=_bezeichnung(schluessel, aufnahme, vdi),
        link=katalog_link(schluessel, aufnahme, vdi),
        spanntiefe=spanntiefe,
        abschnitte=[_abschnitt(a, faktor) for a in abschnitte],
    )
    if schluessel in VDI_VORLAGEN:  # die Spannmutter wächst nicht mit der Aufnahme
        halter.abschnitte[-1] = _abschnitt(abschnitte[-1])
    if schluessel in _GEWINKELT:
        halter.richtung = GEWINKELT
        winkel, drehung, versatz, kopf_d = _GEWINKELT[schluessel]
        halter.winkel, halter.drehung = winkel, drehung
        halter.versatz, halter.kopf_d = versatz * faktor, kopf_d * faktor
    return halter


def _aus_reihe(schluessel, aufnahme):
    """Ein Halter aus einer Normreihe an der Aufnahme `aufnahme` (ohne: SK40): ihr Flansch, dann
    die Kontur der Reihe bis A."""
    from urllib.parse import quote

    aufnahme = aufnahme_oder_vorgabe(aufnahme)
    _norm, flansch_d, flansch_l = AUFNAHMEN[aufnahme]
    art, groesse, laenge = _reihe_lesen(schluessel)
    spanntiefe, kontur = _reihe(schluessel, flansch_d)
    abschnitte = [(flansch_l, flansch_d, flansch_d, FLANSCH), *kontur(laenge - flansch_l)]
    suche = REIHE_SUCHE[art].format(
        aufnahme=re.sub(r"(?<=[A-Za-z])(?=\d+$)", " ", aufnahme),
        groesse=groesse if art == ER else f"{groesse:g}",
        a=f"{laenge:g}",
    )
    return Halter(
        name=reihe_text(schluessel, aufnahme),
        aufnahme=aufnahme,
        bezeichnung=tr("halter.reihe.bezeichnung", norm=REIHE_NORM[art]),
        link=KATALOG_SUCHE.format(begriff=quote(suche)),
        spanntiefe=spanntiefe,
        abschnitte=[_abschnitt(a) for a in abschnitte if a[0] > 1e-6],
    )


def _artikel_text(artikel):
    """„300470 16“ – die Artikelnummer, wie der Katalog sie schreibt."""
    return artikel.replace("-", " ", 1)


def _bezeichnung(schluessel, aufnahme, vdi=0):
    """Woher die Maße einer Vorlage kommen: an SK40 (VDI-Vorlagen: an VDI30) von ihrem Vorbild,
    sonst der Körper von ihm und der Flansch der Aufnahme (VDI: auf die Größe `vdi` gestreckt);
    ohne Vorbild Beispielmaße."""
    artikel = VORBILD.get(schluessel)
    if not artikel:
        return tr("halter.beispielmasse")
    if schluessel in VDI_VORLAGEN and vdi and vdi != VDI_BEZUG:
        return tr("halter.vorbild_vdi", artikel=_artikel_text(artikel), groesse=f"{vdi:g}")
    if schluessel in VDI_VORLAGEN or aufnahme == VORGABE_AUFNAHME:
        return tr("halter.vorbild", artikel=_artikel_text(artikel))
    return tr("halter.vorbild_koerper", artikel=_artikel_text(artikel), aufnahme=aufnahme)


def katalog_link(schluessel, aufnahme, vdi=0):
    """Der Link zum Vorbild einer Vorlage im Katalog – an einer anderen Aufnahme als SK40 (an
    einer anderen VDI-Größe als 30) die Suche nach ihrer Art an dieser Aufnahme
    („ER-Spannzangenfutter HSK-A 63 ER32“). "" ohne."""
    from urllib.parse import quote

    artikel = VORBILD.get(schluessel)
    if not artikel:
        return ""
    if schluessel in VDI_VORLAGEN:
        if not vdi or vdi == VDI_BEZUG:
            return KATALOG_ARTIKEL.format(artikel=artikel)
        groesse = f"VDI {vdi:g}"
    elif aufnahme == VORGABE_AUFNAHME:
        return KATALOG_ARTIKEL.format(artikel=artikel)
    else:
        groesse = re.sub(r"(?<=[A-Za-z])(?=\d+$)", " ", aufnahme)  # „HSK-A63“ → „HSK-A 63“
    return KATALOG_SUCHE.format(begriff=quote(SUCHE[schluessel].format(aufnahme=groesse)))


def _abschnitt(vorlage, faktor=1.0):
    """Ein Abschnitt aus einer Zeile der Vorlagen (Länge, Ø oben, Ø unten[, Art]), die Ø mal
    `faktor`."""
    laenge, oben, unten, *art = vorlage
    return Abschnitt(laenge, oben * faktor, unten * faktor, art[0] if art else "")


# Der Halter, mit dem geprüft wird, solange beim Werkzeug keiner gewählt ist (D-23, Manuel
# 2026-10-03: „ja ja beides gut“): nach Schaft-Ø bis 10 ER16, bis 16 ER25, bis 20 ER32, darüber
# ER40; das Werkzeug steht Auskragung N + 5 mm heraus.
VORSCHLAG_BIS = ((10.0, "er16"), (16.0, "er25"), (20.0, "er32"))
VORSCHLAG_SONST = "er40"
VORSCHLAG_ZUGABE = 5.0  # mm über die Auskragung hinaus
VORSCHLAG_KENNUNG = "vorschlag:"


def vorschlag(schaft_d, aufnahme=None):
    """Der vorgeschlagene Halter für einen Schaft-Ø (mm) – eine Vorlage, nicht gespeichert; an
    der Werkzeugaufnahme `aufnahme` der Maschine (W-022; ohne: SK40)."""
    schluessel = next((s for bis, s in VORSCHLAG_BIS if schaft_d <= bis + 1e-9), VORSCHLAG_SONST)
    halter = aus_vorlage(schluessel, aufnahme=aufnahme)
    halter.kennung = VORSCHLAG_KENNUNG + schluessel
    return halter


def vorschlag_kurz(halter):
    """„ER25“ – der vorgeschlagene Halter kurz, für schmale Felder."""
    return halter.kennung[len(VORSCHLAG_KENNUNG) :].upper()


def ist_vorschlag(halter):
    """Ist es der vorgeschlagene Halter (vorschlag), kein gewählter?"""
    return halter is not None and halter.kennung.startswith(VORSCHLAG_KENNUNG)


def _vorlage(schluessel, vdi):
    """(Schlüssel, VDI-Größe oder 0): Ein alter Schlüssel „vdi30_…“ heißt VDI 30; für alles
    außer den VDI-Vorlagen zählt keine Größe."""
    if schluessel in _ALTE_SCHLUESSEL:
        schluessel, vdi = _ALTE_SCHLUESSEL[schluessel], vdi or VDI_BEZUG
    schluessel = _OHNE_SPANNZANGE.get(schluessel, schluessel)
    if schluessel not in VDI_VORLAGEN or not vdi:
        return schluessel, 0.0
    return schluessel, float(vdi)


def text(halter):
    """Für Listen und Auswahl: der Name – ohne Namen „Halter, 70 mm lang“."""
    if halter.name.strip():
        return halter.name.strip()
    laenge = f"{einheiten.gerundet(halter.laenge, einheiten.LAENGE):g}"
    zeichen = einheiten.gewaehltes_dezimalzeichen() or einheiten.PUNKT
    laenge = mit_dezimalzeichen(laenge, zeichen)
    return tr("halter.ohne_name", laenge=f"{laenge} {einheiten.einheit(einheiten.LAENGE)}")
