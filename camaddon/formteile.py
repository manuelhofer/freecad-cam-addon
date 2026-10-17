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


# Je (hashCode, Toleranz) einer Form: (die Form – festgehalten wie oben –, ihr Netz) (vernetzt).
_NETZE = OrderedDict()
NETZE_GEMERKT = 128


def vernetzt(form, toleranz):
    """(Punkte, Dreiecke) wie `form.tessellate(toleranz)` – aber an einer Kopie: tessellate am
    Original hängt das Netz an die Form (an alle, die ihre Flächen teilen), und wer sie danach
    gröber vernetzt, bekommt das feinere zurück; das Ergebnis hinge davon ab, was davor lief (drei
    Simultan-Tests nach P-2026-10-17-22, P-2026-10-18-68). Je Form (`isSame`: dieselbe Topologie,
    dieselbe Lage) und Toleranz die letzten NETZE_GEMERKT gemerkt – ein Klick im Assistenten
    vernetzt dieselben Flächen mehrmals (P-2026-10-18-71). Die Listen nicht verändern."""
    schluessel = (form.hashCode(), float(toleranz))
    eintrag = _NETZE.get(schluessel)
    if eintrag is not None and eintrag[0].isSame(form):
        _NETZE.move_to_end(schluessel)
        return eintrag[1]
    netz = form.copy(False, False).tessellate(toleranz)
    _NETZE[schluessel] = (form, netz)
    _NETZE.move_to_end(schluessel)
    while len(_NETZE) > NETZE_GEMERKT:
        _NETZE.popitem(last=False)
    return netz


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


# [(Form, Volumen)] – die zuletzt gefragten, die neueste vorn (volumen).
_VOLUMEN = []
VOLUMEN_MERKEN = 4


def volumen(form):
    """`form.Volume`, für dieselbe Form (isSame) nur einmal gerechnet – und für einen Körper aus
    einem STL aus seinem Netz (stl_teil.netz_fuer): OpenCascade braucht am Geist (68.242 Dreiecke)
    0,8 s je Aufruf, das Netz 2 ms – derselbe Wert (17 660,871 mm³). Der Assistent „Bearbeitung“
    fragt es je Vorschau mehrmals (Ziel, Merkschlüssel) und beim Anlegen des Jobs für jeden
    Körper im Dokument."""
    for nummer, (gemerkt, wert) in enumerate(_VOLUMEN):
        if gemerkt.isSame(form):
            if nummer:
                _VOLUMEN.insert(0, _VOLUMEN.pop(nummer))
            return wert
    wert = _netz_volumen(form)
    if wert is None:
        wert = form.Volume
    _VOLUMEN[:] = [(form, wert)] + _VOLUMEN[: VOLUMEN_MERKEN - 1]
    return wert


def _netz_volumen(form):
    """Das Volumen aus dem Netz eines Körpers aus einem STL (die Dreiecke zeigen nach außen,
    stl_teil.vorbereiten) – None für andere Formen."""
    from . import stl_teil

    try:
        netz = stl_teil.netz_fuer(form)
    except Exception:  # noqa: BLE001 – dann rechnet OpenCascade
        return None
    if netz is None:
        return None
    import numpy as np

    punkte, dreiecke = netz[0], netz[1]
    if not len(dreiecke):
        return None
    a, b, c = punkte[dreiecke[:, 0]], punkte[dreiecke[:, 1]], punkte[dreiecke[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
