# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Arbeiter eines Nebenrechners – läuft in FreeCADCmd (nebenrechner.py startet ihn).

Liest eine Zeile JSON von stdin (Adresse, Schlüssel, Addon-Ordner, Nummer, Sprache,
Einstellungen), verbindet sich, meldet sich (HALLO) und wartet dann auf Aufträge: je Auftrag
`camaddon.<modul>.<funktion>(*args, **kwargs)`, die Platzhalter aus nebenrechner.py aufgelöst
(Form → Part.Shape, Dokument → das geöffnete Dokument, Gemeinsam → die einmal empfangenen Daten,
Fortschritt → eine Funktion, die ihn meldet). Das Ergebnis geht zurück („fertig“), ein Fehler als
Traceback („fehler“). Reißt die Verbindung ab (der Hauptprozess ist weg), endet der Arbeiter.
`nebenrechner.pool()` ist hier ein Unterpool: Was der Arbeiter rechnet, verteilt über den Pool
des Hauptprozesses weiter (P-2026-10-11-07).

FreeCADCmd führt diese Datei als Skript aus; `__name__` ist dann der Dateiname, deshalb schaltet
die Umgebungsvariable CAMADDON_ARBEITER die Hauptschleife frei – importiert tut die Datei nichts.
"""

import contextlib
import importlib
import json
import os
import sys
import time
import traceback

MELDEN_ALLE = 0.2  # s: so oft höchstens meldet eine Funktion ihren Fortschritt
DOKUMENTE_OFFEN = 3  # so viele Dokumentkopien bleiben offen, die älteste geht zu


def _verbinden(start):
    from multiprocessing.connection import Client

    adresse = start["adresse"]
    if isinstance(adresse, list):  # AF_INET: (Host, Port) kam als Liste
        adresse = tuple(adresse)
    return Client(adresse, authkey=bytes.fromhex(start["schluessel"]))


class _Dokumente:
    """Die geöffneten Dokumentkopien, je Pfad eine; eine geänderte Kopie unter demselben Pfad
    (andere Größe oder Zeit) wird neu geöffnet."""

    def __init__(self):
        self._offen = {}  # Pfad -> (Kennung, Dokument)
        self._reihe = []  # Pfade, zuletzt benutzt am Ende

    def hole(self, pfad):
        import FreeCAD

        stat = os.stat(pfad)
        kennung = (stat.st_size, stat.st_mtime_ns)
        eintrag = self._offen.get(pfad)
        if eintrag is None or eintrag[0] != kennung:
            if eintrag is not None:
                FreeCAD.closeDocument(eintrag[1].Name)
            dokument = FreeCAD.openDocument(pfad, hidden=True)
            self._offen[pfad] = (kennung, dokument)
        if pfad in self._reihe:
            self._reihe.remove(pfad)
        self._reihe.append(pfad)
        while len(self._reihe) > DOKUMENTE_OFFEN:
            alt = self._reihe.pop(0)
            FreeCAD.closeDocument(self._offen.pop(alt)[1].Name)
        return self._offen[pfad][1]


class _Fortschritt:
    """Meldet den Fortschritt an den Hauptprozess, höchstens alle MELDEN_ALLE Sekunden."""

    def __init__(self, verbindung, nummer):
        self._verbindung = verbindung
        self._nummer = nummer
        self._zuletzt = -1.0

    def __call__(self, anteil):
        jetzt = time.monotonic()
        if anteil >= 1.0 or jetzt - self._zuletzt >= MELDEN_ALLE:
            self._zuletzt = jetzt
            self._verbindung.send(("fortschritt", self._nummer, float(anteil)))
        return True


def _aufloesen(wert, gemeinsam, dokumente, fortschritt, tiefe=0):
    """Ersetzt die Platzhalter in `wert` – bis drei Ebenen tief in Listen, Tupeln und
    Wörterbüchern, nicht in langen Folgen (nebenrechner.FOLGE_DATEN)."""
    from camaddon import nebenrechner as nr

    if isinstance(wert, nr.Form):
        return wert.form()
    if isinstance(wert, nr.Gemeinsam):
        return gemeinsam[wert.schluessel]
    if isinstance(wert, nr.Dokument):
        return dokumente.hole(wert.pfad)
    if isinstance(wert, nr.Fortschritt):
        return fortschritt
    if tiefe >= 3 or nr.ist_datenfolge(wert):
        return wert
    if isinstance(wert, dict):
        return {
            k: _aufloesen(v, gemeinsam, dokumente, fortschritt, tiefe + 1) for k, v in wert.items()
        }
    if isinstance(wert, list):
        return [_aufloesen(v, gemeinsam, dokumente, fortschritt, tiefe + 1) for v in wert]
    if isinstance(wert, tuple):
        return tuple(_aufloesen(v, gemeinsam, dokumente, fortschritt, tiefe + 1) for v in wert)
    return wert


_verbindung = None
_gemeinsam = {}
_dokumente = None


def _ausfuehren(nachricht):
    """Rechnet einen Auftrag und schickt Ergebnis oder Fehler; False, wenn die Verbindung weg
    ist."""
    _, nummer, modul, funktion, args, kwargs = nachricht
    fortschritt = _Fortschritt(_verbindung, nummer)
    try:
        f = getattr(importlib.import_module("camaddon." + modul), funktion)
        args = _aufloesen(args, _gemeinsam, _dokumente, fortschritt)
        kwargs = _aufloesen(kwargs, _gemeinsam, _dokumente, fortschritt)
        ergebnis = f(*args, **kwargs)
        _verbindung.send(("fertig", nummer, ergebnis))
    except BaseException as fehler:  # noqa: BLE001 – jeder Fehler gehört zum Hauptprozess
        try:
            _verbindung.send(
                ("fehler", nummer, traceback.format_exc(), type(fehler).__name__, str(fehler))
            )
        except (OSError, EOFError):
            return False
    return True


def _verarbeiten(nachricht):
    """Eine Meldung des Hauptprozesses – in der Hauptschleife und beim Warten auf Unteraufträge
    (nebenrechner.Unterpool). False: Schluss."""
    art = nachricht[0]
    if art == "ende":
        return False
    if art == "daten":
        _gemeinsam[nachricht[1]] = _aufloesen(nachricht[2], _gemeinsam, _dokumente, None)
    elif art == "vergiss":
        _gemeinsam.pop(nachricht[1], None)
    elif art == "auftrag":
        return _ausfuehren(nachricht)
    elif art == "laden":  # vorwaermen: die Module schon jetzt, nicht beim ersten Auftrag
        for modul in nachricht[1]:
            # Scheitert es, dann eben beim Auftrag, mit dessen Fehler.
            with contextlib.suppress(Exception):
                importlib.import_module("camaddon." + modul)
    return True


def hauptschleife():
    global _verbindung, _dokumente
    start = json.loads(sys.stdin.readline())
    if start["addon"] not in sys.path:
        sys.path.insert(0, start["addon"])
    import FreeCAD

    from camaddon import PARAMETER_PFAD, sprache
    from camaddon import nebenrechner as nr

    if start.get("einstellungen") and os.path.isfile(start["einstellungen"]):
        FreeCAD.ParamGet(PARAMETER_PFAD).Import(start["einstellungen"])
    sprache.setze_sprache(start["sprache"])
    _verbindung = _verbinden(start)
    nr.puffer_vergroessern(_verbindung)
    _verbindung.send((nr.HALLO, start["nummer"], os.getpid()))
    _dokumente = _Dokumente()
    if start.get("unter"):
        # Was der Arbeiter rechnet, darf selbst verteilen – über den Pool des Hauptprozesses.
        nr._pool = nr.Unterpool(_verbindung, start.get("anzahl", 0), _verarbeiten)
    while True:
        try:
            nachricht = _verbindung.recv()
        except (EOFError, OSError):
            return
        if not _verarbeiten(nachricht):
            return


if os.environ.get("CAMADDON_ARBEITER") == "1":
    hauptschleife()
