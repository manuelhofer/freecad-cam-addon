# SPDX-License-Identifier: LGPL-2.1-or-later
"""Einzelne Flächen einer Form, ohne alle auszupacken.

`form.Faces` baut je Aufruf alle Flächen als Python-Objekte – in FreeCAD 26.3 viermal so teuer
wie in 1.1 (Manuels Testteil, 26 Flächen: 0,52 statt 0,13 ms), und der Assistent fragt bei einem
Klick tausendfach nach einer einzelnen. `getElement` holt nur die eine (0,02 ms), dieselbe mit
derselben Orientierung (nachgeprüft an den drei Testteilen, auch gedreht; P-2026-10-11-79).
Läuft ohne Oberfläche.
"""

from collections import OrderedDict
from types import MappingProxyType

# Je Form ihr hashCode -> (die Form – festgehalten, damit OpenCascade ihren Speicher keiner anderen
# gibt –, {hashCode einer Fläche: ihre Nummer}) (nummern).
_NUMMERN = OrderedDict()
NUMMERN_FORMEN = 8


def flaeche(form, nummer):
    """Die Fläche `nummer` (0 ist „Face1“) – wie `form.Faces[nummer]`, ohne die anderen."""
    if nummer < 0:
        nummer += anzahl(form)
    return form.getElement(f"Face{nummer + 1}")


def anzahl(form):
    """Wie `len(form.Faces)`."""
    return form.countElement("Face")


# Ab so vielen gefragten Flächen alle auf einmal (`form.Faces`): `getElement` und `countElement`
# gehen je Aufruf alle Flächen durch – an einem Körper aus einem STL (17.848 Dreiecke) 0,3 ms je
# Fläche, in einer Schleife über alle quadratisch (P-2026-10-11-100: 100 s beim Wechsel zu
# Schritt 2 im 4-Achs-Assistenten).
EINZELN_BIS = 64


def flaechen(form, nummern_):
    """[(Nummer, Fläche)] der Flächen `nummern_` (0 ist „Face1“), die es gibt, in dieser
    Reihenfolge – wenige einzeln, viele auf einmal."""
    gesamt = anzahl(form)
    gibt_es = [n for n in nummern_ if 0 <= n < gesamt]
    if len(gibt_es) <= EINZELN_BIS:
        return [(n, form.getElement(f"Face{n + 1}")) for n in gibt_es]
    alle = form.Faces
    return [(n, alle[n]) for n in gibt_es]


def nummern(form):
    """{hashCode einer Fläche: ihre Nummer (0 ist „Face1“)} – für die Nachbarn einer Kante
    (`ancestorsOfType`); je Form einmal gerechnet, nur zum Lesen."""
    try:
        kennung = form.hashCode()
    except Exception:  # noqa: BLE001 – keine Form, die sich merken lässt
        return {f.hashCode(): i for i, f in enumerate(form.Faces)}
    eintrag = _NUMMERN.get(kennung)
    if eintrag is not None and eintrag[0].isSame(form):
        _NUMMERN.move_to_end(kennung)
        return eintrag[1]
    index = MappingProxyType({f.hashCode(): i for i, f in enumerate(form.Faces)})
    _NUMMERN[kennung] = (form, index)
    while len(_NUMMERN) > NUMMERN_FORMEN:
        _NUMMERN.popitem(last=False)
    return index


def mit_namen(form, namen):
    """[(Nummer, Fläche)] in der Reihenfolge der Form – mit `namen` („Face3“ …) nur diese, ohne
    alle Flächen auszupacken; None: alle."""
    if namen is None:
        return list(enumerate(form.Faces))
    gewaehlt = set()
    for name in namen:
        if isinstance(name, str) and name.startswith("Face") and name[4:].isdigit():
            gewaehlt.add(int(name[4:]) - 1)
    alle = anzahl(form) if gewaehlt else 0
    return [(n, flaeche(form, n)) for n in sorted(gewaehlt) if 0 <= n < alle]
