# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Namen der Operationen: eindeutig im Dokument, ohne dass FreeCAD sie umbenennt.

FreeCAD macht doppelte Namen eindeutig, indem es die Ziffern am Ende ersetzt – aus einem zweiten
„Bohren T2“ wurde „Bohren T001“, und die Nummer des Werkzeugs war weg (zwei Tiefen beim Bohren,
zwei Konturen mit demselben Fräser, zwei Jobs in einem Dokument). eindeutig() hängt darum selbst
„ (2)“, „ (3)“ … an, bevor FreeCAD den Namen sieht. Läuft ohne Oberfläche.
"""

import re


def eindeutig(dokument, name, ausser=None):
    """`name` – oder „name (2)“, „name (3)“ …, wenn ein anderes Objekt im Dokument so heißt
    (`ausser`: das Objekt, das den Namen bekommt, zählt nicht)."""
    vergeben = {o.Label for o in dokument.Objects if o is not ausser}
    if name not in vergeben:
        return name
    n = 2
    while f"{name} ({n})" in vergeben:
        n += 1
    return f"{name} ({n})"


def nach_vorlage(name, vorlage):
    """Ist `name` einer, wie die Vorlage ihn vergibt – „Kontur T1“, auch „Kontur T1 (2)“?
    `vorlage`: der übersetzte Name mit „\\0“ an der Stelle des Werkzeugs."""
    vorne, _mitte, hinten = vorlage.partition("\0")
    muster = re.escape(vorne) + r"T\d+" + re.escape(hinten) + r"( \(\d+\))?"
    return re.fullmatch(muster, name) is not None
