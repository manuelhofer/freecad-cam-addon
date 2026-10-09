# SPDX-License-Identifier: LGPL-2.1-or-later
"""Nebenrechner (T-006): Rechenarbeit in eigenen FreeCADCmd-Prozessen – auf allen Kernen, und das
Fenster bleibt bedienbar.

Das Addon rechnete bis dahin auf einem Kern, im Prozess der Oberfläche: Solange die Kollision
prüfte oder der 4-Achs-Assistent seine Vorschau rechnete, stand das Fenster (Manuel, 2026-10-04:
„es rechnen nur maximal 5 von meinen 24 Kernen“; 2026-10-09: „ein Lag … wo ich nichts klicken
kann … sowas muss unbedingt vermieden werden“). Python rechnet in einem Prozess nicht zwei Dinge
zugleich (GIL), und FreeCADs Dokumente vertragen keine Threads. Deshalb eigene Prozesse: Jeder
Arbeiter ist ein FreeCADCmd (nebenrechner_arbeiter.py) im Profil des Benutzers, aber mit eigener
Kopie von user.cfg und system.cfg – so überschreibt er beim Beenden nichts –, der über eine
Verbindung (multiprocessing.connection, mit Schlüssel) Aufträge bekommt – ein Modul des Addons,
eine Funktion, Argumente – und das Ergebnis zurückschickt.

Argumente und Ergebnisse müssen sich pickeln lassen. Dafür gibt es Platzhalter, die der Arbeiter
auflöst: `Form` (eine Part.Shape als BREP-Text), `Dokument` (eine gespeicherte Kopie, die der
Arbeiter öffnet und offen hält – `kopie()`), `Gemeinsam` (große Daten, die jeder Arbeiter einmal
bekommt und behält – `gemeinsam()`), `Fortschritt` (wird zur Funktion, die den Fortschritt
meldet). Eine Funktion, die im Arbeiter läuft, bekommt und liefert nur solche Daten.

Benutzung – im Prozess der Oberfläche oder in einer Prüfung:

    nr = nebenrechner.pool()
    auftraege = [nr.auftrag("kollision", "stueck", daten, bereich=b) for b in bereiche]
    ergebnisse = nr.warten(auftraege, zwischendurch=processEvents)

oder ohne Warten, für ein Fenster, das weiterlaufen soll: `auftrag.bei_fertig = funktion`; mit
Oberfläche fragt der Pool die Arbeiter selbst über einen QTimer ab, sonst `abfragen()`.
`auftrag.abbrechen()` beendet den Arbeiter, der daran rechnet – ein neuer kommt beim nächsten
Auftrag. Ohne FreeCADCmd neben FreeCAD (`verfuegbar()`) rechnet alles wie bisher im eigenen
Prozess; wer den Pool benutzt, fängt `NichtVerfuegbar` und rechnet dann selbst.

Das ist neben Git (aktualisierung.py) der zweite Fremdprozess des Addons – begründet in den
Arbeitsregeln, Abschnitt 7: FreeCADCmd liegt neben FreeCAD (`FreeCAD.ConfigGet("BinPath")`),
auf jedem System. Läuft ohne Oberfläche.
"""

import atexit
import contextlib
import json
import os
import queue
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from multiprocessing import connection

import FreeCAD

from . import ADDON_ORDNER, PARAMETER_PFAD

EINSTELLUNG_ANZAHL = "Nebenrechner"  # so viele Arbeiter; 0 = so viele wie Kerne
ARBEITER_SKRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "nebenrechner_arbeiter.py"
)
STARTZEIT = 60.0  # s: bis dahin muss sich ein Arbeiter gemeldet haben
LEERLAUF = 600.0  # s: so lange bleibt ein Arbeiter ohne Auftrag, dann endet er
TAKT = 0.02  # s: so oft sieht warten() nach den Arbeitern
UHR_MS = 30  # mit Oberfläche: so oft fragt der Pool die Arbeiter ab, solange etwas läuft
AUFRAEUMEN_MS = 60000  # mit Oberfläche: so oft beendet er Arbeiter im Leerlauf
KOPIEN_JE_DOKUMENT = 3  # so viele Kopien eines Dokuments bleiben liegen
EINSTELLUNGEN_DATEI = "einstellungen.FCParam"  # die Einstellungen des Addons für die Arbeiter
HALLO = "hallo"  # die erste Meldung eines Arbeiters: (HALLO, Nummer, PID)


class Fehler(Exception):
    """Ein Auftrag ist im Arbeiter gescheitert; der Text ist dessen Traceback. `art` ist der
    Name der Ausnahme dort („ValueError“), `satz` ihr Text – für Fehler, die zum Fachlichen
    gehören (eine Vorschau, die nicht geht), ohne den Traceback zu lesen."""

    def __init__(self, text, art="", satz=""):
        super().__init__(text)
        self.art = art
        self.satz = satz


class NichtVerfuegbar(Fehler):
    """Es gibt keine Nebenrechner (kein FreeCADCmd, oder die Arbeiter starten nicht)."""


class Abgebrochen(Fehler):
    """Der Auftrag wurde abgebrochen, bevor er fertig war."""


# --- Platzhalter -------------------------------------------------------------------------


@dataclass(frozen=True)
class Form:
    """Eine Form (Part.Shape) als BREP-Text – der Arbeiter macht wieder eine Form daraus."""

    brep: str

    @classmethod
    def von(cls, shape):
        return cls(shape.exportBrepToString())

    def form(self):
        import Part

        shape = Part.Shape()
        shape.importBrepFromString(self.brep)
        return shape


@dataclass(frozen=True)
class Gemeinsam:
    """Verweist auf Daten, die jeder Arbeiter einmal bekommt und für alle Aufträge behält
    (`Nebenrechner.gemeinsam`): das Teil, die Stationen – alles, was groß ist."""

    schluessel: str


@dataclass(frozen=True)
class Dokument:
    """Eine gespeicherte Kopie eines Dokuments (`Nebenrechner.kopie`); der Arbeiter öffnet sie
    einmal und gibt der Funktion das offene Dokument."""

    pfad: str


class Fortschritt:
    """Platzhalter: Der Arbeiter setzt dafür eine Funktion `fortschritt(anteil)` ein, die den
    Fortschritt (0 … 1) an den Auftrag meldet (`Auftrag.fortschritt`, `bei_fortschritt`)."""


# --- Aufträge ----------------------------------------------------------------------------


class Auftrag:
    """Ein Auftrag an einen Arbeiter: `funktion` aus `camaddon.<modul>` mit den Argumenten.

    `fertig` mit `ergebnis`, oder `fehler` (der Traceback aus dem Arbeiter), oder `abgebrochen`;
    `fortschritt` 0 … 1, wenn die Funktion ihn meldet. `bei_fertig(auftrag)` und
    `bei_fortschritt(auftrag)` ruft der Pool beim Abfragen – im Prozess der Oberfläche, nie
    aus einem Thread. `gewicht`: der Anteil am gemeinsamen Fortschritt (`fortschritt_von`)."""

    def __init__(self, pool, nummer, modul, funktion, args, kwargs):
        self._pool = pool
        self.nummer = nummer
        self.modul, self.funktion, self.args, self.kwargs = modul, funktion, args, kwargs
        self.fertig = False
        self.ergebnis = None
        self.fehler = None  # der Traceback aus dem Arbeiter
        self.fehlerart = ""  # der Name der Ausnahme dort
        self.fehlersatz = ""  # ihr Text
        self.abgebrochen = False
        self.fortschritt = 0.0
        self.gewicht = 1.0
        self.bei_fertig = None
        self.bei_fortschritt = None
        self.arbeiter = None  # solange er läuft

    @property
    def erledigt(self):
        """Fertig, gescheitert oder abgebrochen – jedenfalls nicht mehr unterwegs."""
        return self.fertig or self.fehler is not None or self.abgebrochen

    def abbrechen(self):
        """Nimmt den Auftrag zurück; läuft er, endet sein Arbeiter."""
        self._pool.abbrechen(self)

    def __repr__(self):
        return f"Auftrag({self.nummer}, {self.modul}.{self.funktion})"


def fortschritt_von(auftraege):
    """Der gemeinsame Fortschritt mehrerer Aufträge (0 … 1), nach ihrem Gewicht."""
    gesamt = sum(a.gewicht for a in auftraege)
    if gesamt <= 0:
        return 1.0
    return sum((1.0 if a.erledigt else a.fortschritt) * a.gewicht for a in auftraege) / gesamt


class _Arbeiter:
    """Ein FreeCADCmd-Prozess mit seiner Verbindung."""

    def __init__(self, nummer, prozess, ordner, protokoll):
        self.nummer = nummer
        self.prozess = prozess
        self.ordner = ordner
        self.protokoll = protokoll  # die offene Datei mit seiner Ausgabe
        self.verbindung = None  # bis er sich gemeldet hat
        self.auftrag = None  # woran er gerade rechnet
        self.gemeinsam = set()  # die Schlüssel der gemeinsamen Daten, die er schon hat
        self.gestartet = time.monotonic()
        self.zuletzt = self.gestartet  # wann er zuletzt einen Auftrag bekam oder abgab

    def lebt(self):
        return self.prozess.poll() is None

    def beenden(self):
        """Beendet den Prozess sofort und räumt seinen Ordner weg."""
        if self.verbindung is not None:
            with contextlib.suppress(OSError):
                self.verbindung.close()
            self.verbindung = None
        if self.lebt():
            self.prozess.kill()
        with contextlib.suppress(subprocess.TimeoutExpired, OSError):
            self.prozess.wait(timeout=5)
        with contextlib.suppress(OSError):
            self.protokoll.close()
        shutil.rmtree(self.ordner, ignore_errors=True)


# --- Der Pool ----------------------------------------------------------------------------


def anzahl_kerne():
    """So viele Kerne hat der Rechner (mindestens 1)."""
    return os.cpu_count() or 1


def gewuenschte_anzahl():
    """So viele Arbeiter darf der Pool haben: die Einstellung, sonst so viele wie Kerne."""
    anzahl = FreeCAD.ParamGet(PARAMETER_PFAD).GetInt(EINSTELLUNG_ANZAHL, 0)
    return anzahl if anzahl > 0 else anzahl_kerne()


def freecadcmd_pfad():
    """Der Pfad zu FreeCADCmd dieser FreeCAD-Installation, oder None. Zuerst neben FreeCAD
    (BinPath, der Ordner des laufenden Programms), zuletzt im PATH – dort könnte ein anderes
    FreeCAD liegen."""
    ordner = []
    for kandidat in (
        FreeCAD.ConfigGet("BinPath"),
        os.path.dirname(sys.executable or ""),
        os.path.join(FreeCAD.getHomePath(), "bin"),
    ):
        if kandidat and kandidat not in ordner:
            ordner.append(kandidat)
    namen = ("FreeCADCmd", "freecadcmd", "FreeCADCmd.exe", "freecadcmd.exe")
    for o in ordner:
        for name in namen:
            pfad = os.path.join(o, name)
            if os.path.isfile(pfad) and os.access(pfad, os.X_OK):
                return pfad
    for name in namen[:2]:
        pfad = shutil.which(name)
        if pfad:
            return pfad
    return None


class Nebenrechner:
    """Ein Pool von Arbeitern; `anzahl` höchstens so viele (Vorgabe: gewuenschte_anzahl()).
    Arbeiter starten erst, wenn Aufträge da sind, und bleiben für die nächsten."""

    def __init__(self, anzahl=None):
        self.anzahl = max(1, anzahl or gewuenschte_anzahl())
        self._freecadcmd = freecadcmd_pfad()
        self._arbeiter = []
        self._warteschlange = []
        self._laufend = {}  # Auftragsnummer -> Auftrag
        self._gemeinsam = {}  # Schlüssel -> Wert
        self._zaehler = 0  # Aufträge
        self._gestartete = 0  # Arbeiter, je eine Nummer
        self._ordner = None
        self._listener = None
        self._schluessel = None
        self._neue = queue.Queue()  # (Nummer, Verbindung) aus dem Thread, der annimmt
        self._annehmer = None
        self._fehlgeschlagen = False  # kein Arbeiter hat sich je gemeldet
        self._je_gemeldet = False
        self._in_abfrage = False
        self._kopien = {}  # Dokumentname -> [Pfade der Kopien]
        self._uhr = None
        self._aufraeumuhr = None
        self.in_arbeit = 0  # so viele Aufträge liefen bisher in Arbeitern (für Prüfungen)

    # --- Nach außen ------------------------------------------------------------------

    def verfuegbar(self):
        """Gibt es Nebenrechner? Ohne FreeCADCmd nicht; auch nicht, wenn die Arbeiter nicht
        starten (dann rechnet der Aufrufer selbst)."""
        return self._freecadcmd is not None and not self._fehlgeschlagen

    def auftrag(self, modul, funktion, *args, **kwargs):
        """Reiht `camaddon.<modul>.<funktion>(*args, **kwargs)` ein; gibt den Auftrag zurück.
        NichtVerfuegbar ohne Nebenrechner."""
        if not self.verfuegbar():
            raise NichtVerfuegbar(self._grund())
        self._zaehler += 1
        auftrag = Auftrag(self, self._zaehler, modul, funktion, args, kwargs)
        self._warteschlange.append(auftrag)
        self._verteilen()
        self._uhren()
        return auftrag

    def gemeinsam(self, schluessel, wert):
        """Legt gemeinsame Daten ab; Aufträge verweisen mit Gemeinsam(schluessel) darauf. Ein
        neuer Wert unter einem alten Schlüssel ist ein Fehler – der Schlüssel benennt den Wert."""
        if schluessel in self._gemeinsam:
            raise ValueError(f"gemeinsame Daten „{schluessel}“ gibt es schon")
        self._gemeinsam[schluessel] = wert
        return Gemeinsam(schluessel)

    def vergessen(self, schluessel):
        """Gibt gemeinsame Daten frei (im eigenen Prozess; die Arbeiter behalten sie, bis sie
        enden)."""
        self._gemeinsam.pop(schluessel, None)

    def kopie(self, dokument):
        """Speichert eine Kopie des Dokuments für die Arbeiter; gibt Dokument(pfad) zurück. Je
        Dokument bleiben die letzten KOPIEN_JE_DOKUMENT liegen (ein Arbeiter hat die ältere
        vielleicht noch offen)."""
        self._einrichten()
        ordner = os.path.join(self._ordner, "kopien")
        os.makedirs(ordner, exist_ok=True)
        name = dokument.Name
        pfade = self._kopien.setdefault(name, [])
        pfad = os.path.join(ordner, f"{name}-{len(pfade) + 1}.FCStd")
        while pfad in pfade or os.path.exists(pfad):
            pfad = os.path.join(ordner, f"{name}-{secrets.token_hex(3)}.FCStd")
        dokument.saveCopy(pfad)
        pfade.append(pfad)
        for alt in pfade[:-KOPIEN_JE_DOKUMENT]:
            with contextlib.suppress(OSError):
                os.remove(alt)
        del pfade[:-KOPIEN_JE_DOKUMENT]
        return Dokument(pfad)

    def abfragen(self):
        """Nimmt entgegen, was die Arbeiter melden, verteilt wartende Aufträge, ruft die
        Rückrufe (bei_fertig, bei_fortschritt). Mit Oberfläche tut das ein QTimer, solange
        etwas läuft; sonst ruft es warten()."""
        if self._in_abfrage:
            return
        self._in_abfrage = True
        try:
            self._verbindungen_annehmen()
            for arbeiter in list(self._arbeiter):
                self._lesen(arbeiter)
            self._verteilen()
        finally:
            self._in_abfrage = False
        self._uhren()

    def warten(self, auftraege, zwischendurch=None):
        """Wartet, bis die Aufträge erledigt sind; gibt ihre Ergebnisse zurück (in der
        Reihenfolge). `zwischendurch()` wird dabei immer wieder gerufen – das Fenster
        verarbeitet damit seine Ereignisse –; gibt es False zurück, werden die Aufträge
        abgebrochen (Abgebrochen). Fehler mit dem Traceback, wenn einer scheiterte."""
        auftraege = list(auftraege)
        while True:
            self.abfragen()
            if all(a.erledigt for a in auftraege):
                break
            if zwischendurch is not None and zwischendurch() is False:
                for a in auftraege:
                    self.abbrechen(a)
                break
            self._ruhen(TAKT)
        for a in auftraege:
            if a.abgebrochen:
                raise Abgebrochen(repr(a))
            if a.fehler is not None:
                raise Fehler(a.fehler, a.fehlerart, a.fehlersatz)
        return [a.ergebnis for a in auftraege]

    def abbrechen(self, auftrag):
        """Nimmt den Auftrag zurück; läuft er, endet sein Arbeiter (ein neuer kommt beim
        nächsten Auftrag)."""
        if auftrag.erledigt:
            return
        auftrag.abgebrochen = True
        if auftrag in self._warteschlange:
            self._warteschlange.remove(auftrag)
        arbeiter = auftrag.arbeiter
        if arbeiter is not None:
            self._laufend.pop(auftrag.nummer, None)
            auftrag.arbeiter = None
            arbeiter.auftrag = None
            self._entfernen(arbeiter)
        self._uhren()

    def beenden(self):
        """Beendet alle Arbeiter und räumt auf; der Pool lässt sich danach weiter benutzen."""
        for arbeiter in list(self._arbeiter):
            self._entfernen(arbeiter)
        for auftrag in list(self._laufend.values()) + self._warteschlange:
            auftrag.abgebrochen = True
        self._laufend.clear()
        self._warteschlange.clear()
        if self._listener is not None:
            with contextlib.suppress(OSError):
                self._listener.close()
            self._listener = None
        self._annehmer = None
        if self._ordner is not None:
            shutil.rmtree(self._ordner, ignore_errors=True)
            self._ordner = None
        self._kopien.clear()
        self._uhren()

    @property
    def arbeiter(self):
        """So viele Arbeiter leben gerade (für Prüfungen und den Bericht)."""
        return len(self._arbeiter)

    def offen(self):
        """Läuft oder wartet noch ein Auftrag?"""
        return bool(self._laufend or self._warteschlange)

    # --- Starten und Verbinden ----------------------------------------------------------

    def _grund(self):
        if self._freecadcmd is None:
            return "FreeCADCmd nicht gefunden"
        return "die Arbeiter melden sich nicht"

    def _einrichten(self):
        """Ordner, Verbindung und Schlüssel – einmal, beim ersten Bedarf."""
        if self._listener is not None:
            return
        self._ordner = tempfile.mkdtemp(prefix="camaddon-nebenrechner-")
        self._schluessel = secrets.token_bytes(32)
        self._listener = connection.Listener(authkey=self._schluessel)
        self._annehmer = threading.Thread(
            target=self._annehmen, args=(self._listener,), name="camaddon-nebenrechner", daemon=True
        )
        self._annehmer.start()
        atexit.register(self.beenden)

    def _annehmen(self, listener):
        """Im eigenen Thread: nimmt Verbindungen an und liest die erste Meldung (HALLO, Nummer,
        PID); mehr tut der Thread nicht – alles andere läuft im Prozess der Oberfläche."""
        while True:
            try:
                verbindung = listener.accept()
            except (OSError, EOFError, connection.AuthenticationError):
                if self._listener is not listener:
                    return  # beendet
                continue
            try:
                hallo = verbindung.recv()
                if hallo[0] != HALLO:
                    raise ValueError(hallo)
            except Exception:
                verbindung.close()
                continue
            self._neue.put((hallo[1], verbindung))

    def _starten(self):
        """Startet einen Arbeiter: FreeCADCmd mit eigener user.cfg/system.cfg (Kopien), die
        Startdaten über stdin."""
        self._einrichten()
        self._gestartete += 1
        nummer = self._gestartete
        ordner = tempfile.mkdtemp(prefix=f"arbeiter-{nummer}-", dir=self._ordner)
        konfiguration = FreeCAD.ConfigGet("UserConfigPath")
        befehl = [self._freecadcmd]
        for schalter, name in (("-u", "user.cfg"), ("-s", "system.cfg")):
            kopie = os.path.join(ordner, name)
            quelle = os.path.join(konfiguration, name) if konfiguration else ""
            if quelle and os.path.isfile(quelle):
                shutil.copyfile(quelle, kopie)
            befehl += [schalter, kopie]
        befehl.append(ARBEITER_SKRIPT)
        einstellungen = os.path.join(ordner, EINSTELLUNGEN_DATEI)
        FreeCAD.ParamGet(PARAMETER_PFAD).Export(einstellungen)
        umgebung = dict(os.environ)
        umgebung["CAMADDON_ARBEITER"] = "1"
        umgebung.setdefault("QT_QPA_PLATFORM", "offscreen")
        protokoll = open(  # noqa: SIM115 – bleibt für den Prozess offen, beenden() schließt
            os.path.join(ordner, "protokoll.txt"), "w", encoding="utf-8"
        )
        from . import sprache

        start = {
            "adresse": self._listener.address,
            "schluessel": self._schluessel.hex(),
            "addon": ADDON_ORDNER,
            "nummer": nummer,
            "sprache": sprache.aktuelle_sprache(),
            "einstellungen": einstellungen,
        }
        try:
            prozess = subprocess.Popen(
                befehl,
                stdin=subprocess.PIPE,
                stdout=protokoll,
                stderr=subprocess.STDOUT,
                env=umgebung,
                cwd=ordner,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            prozess.stdin.write((json.dumps(start) + "\n").encode("utf-8"))
            prozess.stdin.flush()
            prozess.stdin.close()
        except OSError as fehler:
            protokoll.close()
            shutil.rmtree(ordner, ignore_errors=True)
            FreeCAD.Console.PrintWarning(f"CAM-Addon: Nebenrechner startet nicht: {fehler}\n")
            self._fehlgeschlagen = True
            self._alle_scheitern()
            return
        self._arbeiter.append(_Arbeiter(nummer, prozess, ordner, protokoll))

    def _verbindungen_annehmen(self):
        while True:
            try:
                nummer, verbindung = self._neue.get_nowait()
            except queue.Empty:
                return
            for arbeiter in self._arbeiter:
                if arbeiter.nummer == nummer and arbeiter.verbindung is None:
                    arbeiter.verbindung = verbindung
                    self._je_gemeldet = True
                    break
            else:
                verbindung.close()  # ein Arbeiter, den es nicht mehr gibt

    # --- Verteilen und Lesen ------------------------------------------------------------

    def _verteilen(self):
        """Gibt wartende Aufträge an freie Arbeiter; startet, was an Arbeitern fehlt."""
        for arbeiter in self._arbeiter:
            if not self._warteschlange:
                break
            if arbeiter.verbindung is None or arbeiter.auftrag is not None:
                continue
            self._senden(arbeiter, self._warteschlange.pop(0))
        startend = sum(1 for a in self._arbeiter if a.verbindung is None)
        fehlend = min(len(self._warteschlange) - startend, self.anzahl - len(self._arbeiter))
        for _ in range(max(0, fehlend)):
            if self._fehlgeschlagen:
                break
            self._starten()

    def _senden(self, arbeiter, auftrag):
        try:
            for schluessel in _gemeinsame_schluessel((auftrag.args, auftrag.kwargs)):
                if schluessel in arbeiter.gemeinsam:
                    continue
                if schluessel not in self._gemeinsam:
                    raise KeyError(f"gemeinsame Daten „{schluessel}“ fehlen")
                arbeiter.verbindung.send(("daten", schluessel, self._gemeinsam[schluessel]))
                arbeiter.gemeinsam.add(schluessel)
            arbeiter.verbindung.send(
                (
                    "auftrag",
                    auftrag.nummer,
                    auftrag.modul,
                    auftrag.funktion,
                    auftrag.args,
                    auftrag.kwargs,
                )
            )
        except KeyError as fehler:
            auftrag.fehler = str(fehler)
            self._melden(auftrag)
            return
        except (OSError, EOFError, ValueError) as fehler:
            # ValueError: etwas lässt sich nicht pickeln – das ist ein Fehler des Aufrufers.
            self._entfernen(arbeiter)
            auftrag.fehler = f"Senden an den Nebenrechner: {fehler!r}"
            self._melden(auftrag)
            return
        arbeiter.auftrag = auftrag
        arbeiter.zuletzt = time.monotonic()
        auftrag.arbeiter = arbeiter
        self._laufend[auftrag.nummer] = auftrag
        self.in_arbeit += 1

    def _lesen(self, arbeiter):
        if arbeiter.verbindung is not None:
            try:
                while arbeiter.verbindung.poll():
                    self._verarbeiten(arbeiter, arbeiter.verbindung.recv())
            except (EOFError, OSError):
                self._gestorben(arbeiter, "die Verbindung ist weg")
                return
        if not arbeiter.lebt():
            self._gestorben(arbeiter, f"beendet mit {arbeiter.prozess.returncode}")
        elif arbeiter.verbindung is None and time.monotonic() - arbeiter.gestartet > STARTZEIT:
            self._gestorben(arbeiter, "meldet sich nicht")
        elif (
            arbeiter.auftrag is None
            and not self._warteschlange
            and time.monotonic() - arbeiter.zuletzt > LEERLAUF
        ):
            self._entfernen(arbeiter)

    def _verarbeiten(self, arbeiter, nachricht):
        art, nummer = nachricht[0], nachricht[1]
        auftrag = self._laufend.get(nummer)
        if auftrag is None or auftrag.arbeiter is not arbeiter:
            return  # ein abgebrochener Auftrag, der doch noch etwas meldet
        if art == "fortschritt":
            auftrag.fortschritt = float(nachricht[2])
            if auftrag.bei_fortschritt is not None:
                auftrag.bei_fortschritt(auftrag)
            return
        if art == "fertig":
            auftrag.ergebnis = nachricht[2]
            auftrag.fertig = True
        elif art == "fehler":
            auftrag.fehler = nachricht[2]
            auftrag.fehlerart, auftrag.fehlersatz = nachricht[3], nachricht[4]
        else:
            auftrag.fehler = f"unbekannte Meldung {art!r}"
        del self._laufend[nummer]
        auftrag.arbeiter = None
        arbeiter.auftrag = None
        arbeiter.zuletzt = time.monotonic()
        self._melden(auftrag)

    def _melden(self, auftrag):
        if auftrag.bei_fertig is not None:
            auftrag.bei_fertig(auftrag)

    def _gestorben(self, arbeiter, grund):
        """Ein Arbeiter ist weg: Sein Auftrag scheitert – außer, er wurde abgebrochen."""
        auftrag = arbeiter.auftrag
        self._entfernen(arbeiter)
        if not self._je_gemeldet and not any(a.verbindung is not None for a in self._arbeiter):
            # Noch nie hat sich einer gemeldet: Es gibt keine Nebenrechner.
            self._fehlgeschlagen = True
            FreeCAD.Console.PrintWarning(
                f"CAM-Addon: Nebenrechner {arbeiter.nummer} {grund} – es wird im eigenen Prozess "
                f"gerechnet (Ausgabe des Arbeiters: {self._protokoll_hinweis(arbeiter)}).\n"
            )
            self._alle_scheitern()
        if auftrag is not None and not auftrag.erledigt:
            self._laufend.pop(auftrag.nummer, None)
            auftrag.arbeiter = None
            auftrag.fehler = f"Nebenrechner {arbeiter.nummer} {grund}"
            self._melden(auftrag)

    def _protokoll_hinweis(self, arbeiter):
        try:
            with open(os.path.join(arbeiter.ordner, "protokoll.txt"), encoding="utf-8") as datei:
                zeilen = [z.strip() for z in datei.read().splitlines() if z.strip()]
            return " | ".join(zeilen[-3:]) or "keine"
        except OSError:
            return "keine"

    def _alle_scheitern(self):
        for auftrag in list(self._laufend.values()) + list(self._warteschlange):
            if not auftrag.erledigt:
                auftrag.fehler = "Nebenrechner nicht verfügbar"
        wartend, self._warteschlange = self._warteschlange, []
        laufend, self._laufend = list(self._laufend.values()), {}
        for auftrag in wartend + laufend:
            auftrag.arbeiter = None
            self._melden(auftrag)

    def _entfernen(self, arbeiter):
        if arbeiter in self._arbeiter:
            self._arbeiter.remove(arbeiter)
        arbeiter.beenden()

    def _ruhen(self, dauer):
        """Wartet höchstens `dauer` – kürzer, sobald ein Arbeiter etwas schickt."""
        verbindungen = [a.verbindung for a in self._arbeiter if a.verbindung is not None]
        if verbindungen:
            try:
                connection.wait(verbindungen, timeout=dauer)
                return
            except (OSError, ValueError):
                pass
        time.sleep(dauer)

    # --- Mit Oberfläche: die Uhren ---------------------------------------------------------

    def _uhren(self):
        """Mit Oberfläche fragt ein QTimer die Arbeiter ab, solange etwas läuft; ein zweiter
        beendet Arbeiter im Leerlauf."""
        try:
            from PySide import QtCore
        except ImportError:
            return
        if QtCore.QCoreApplication.instance() is None:
            return
        if self.offen():
            if self._uhr is None:
                self._uhr = QtCore.QTimer()
                self._uhr.setInterval(UHR_MS)
                self._uhr.timeout.connect(self.abfragen)
                self._uhr.start()
        elif self._uhr is not None:
            self._uhr.stop()
            self._uhr = None
        if self._arbeiter:
            if self._aufraeumuhr is None:
                self._aufraeumuhr = QtCore.QTimer()
                self._aufraeumuhr.setInterval(AUFRAEUMEN_MS)
                self._aufraeumuhr.timeout.connect(self.abfragen)
                self._aufraeumuhr.start()
        elif self._aufraeumuhr is not None:
            self._aufraeumuhr.stop()
            self._aufraeumuhr = None


def _gemeinsame_schluessel(wert, tiefe=0):
    """Die Schlüssel aller Gemeinsam-Platzhalter in `wert` – bis drei Ebenen tief in Listen,
    Tupeln und Wörterbüchern (tiefer sucht der Arbeiter auch nicht)."""
    if isinstance(wert, Gemeinsam):
        return {wert.schluessel}
    if tiefe >= 3:
        return set()
    gefunden = set()
    if isinstance(wert, dict):
        for v in wert.values():
            gefunden |= _gemeinsame_schluessel(v, tiefe + 1)
    elif isinstance(wert, (list, tuple)):
        for v in wert:
            gefunden |= _gemeinsame_schluessel(v, tiefe + 1)
    return gefunden


_pool = None


def pool():
    """Der eine Pool des Addons (gestartet beim ersten Bedarf)."""
    global _pool
    if _pool is None:
        _pool = Nebenrechner()
    return _pool


# --- Für die Prüfung -------------------------------------------------------------------------


def _probe(x, dauer=0.0, fortschritt=None):
    """Rechnet x², meldet dabei Fortschritt – für tests/test_nebenrechner.py."""
    schritte = 10 if dauer > 0 else 1
    for i in range(schritte):
        if dauer > 0:
            time.sleep(dauer / schritte)
        if fortschritt is not None:
            fortschritt((i + 1) / schritte)
    return x * x


def _probe_form(form):
    """Das Volumen einer Form – kam sie als Platzhalter, hat der Arbeiter sie aufgelöst."""
    return form.Volume


def _probe_dokument(dokument, name):
    """Das Volumen des Objekts `name` im (vom Arbeiter geöffneten) Dokument."""
    return dokument.getObject(name).Shape.Volume


def _probe_summe(zahlen, faktor):
    """Die Summe gemeinsamer Daten mal `faktor`."""
    return sum(zahlen) * faktor


def _probe_fehler():
    raise ValueError("absichtlich")
