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
meldet). Eine Funktion, die im Arbeiter läuft, bekommt und liefert nur solche Daten. Platzhalter
stehen als Argument oder bis drei Ebenen tief in Listen, Tupeln und Wörterbüchern – nicht in
einer Folge mit mehr als FOLGE_DATEN Einträgen.

Was ein Arbeiter rechnet, darf selbst verteilen: `pool()` ist dort ein Unterpool, der beim Pool
des Hauptprozesses bestellt (Unteraufträge, P-2026-10-11-07).

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
from collections import OrderedDict
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
GEMEINSAM_JE_ARBEITER = 16  # so viele gemeinsame Daten behält ein Arbeiter, die ältesten gehen
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
        # Höchstens so viele Aufträge derselben `gruppe` rechnen zugleich (None: ohne Grenze) –
        # OpenCascade bremst sich auf den Zwillingen eines Kerns gegenseitig aus (P-2026-10-10-63).
        self.gruppe = None
        self.gleichzeitig = None
        self.bei_fertig = None
        self.bei_fortschritt = None
        self.arbeiter = None  # solange er läuft
        # Unteraufträge (P-2026-10-11-07): Hat ein Arbeiter den Auftrag bestellt, ist `eltern` der
        # Auftrag, an dem er dabei rechnete, und `fuer` (Arbeiter, seine Nummer dafür) – dorthin
        # geht das Ergebnis. Im Hauptprozess bestellt: beide None.
        self.eltern = None
        self.fuer = None

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
        # Woran er rechnet: außen zuerst, darüber, was er beim Warten auf seine Unteraufträge
        # selbst nimmt (P-2026-10-11-07).
        self.stapel = []
        self.wartet = False  # wartet auf Unteraufträge – liest und nimmt dabei eigene
        self.post = (
            []
        )  # Meldungen an ihn, bis er wieder liest (die Ergebnisse seiner Unteraufträge)
        self.gemeinsam = OrderedDict()  # Schlüssel der gemeinsamen Daten, die er hat, nach Alter
        self.gestartet = time.monotonic()
        self.zuletzt = self.gestartet  # wann er zuletzt einen Auftrag bekam oder abgab

    @property
    def auftrag(self):
        """Der äußere Auftrag, an dem er rechnet, oder None."""
        return self.stapel[0] if self.stapel else None

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
    """So viele Kerne hat der Rechner (mindestens 1) – alle Threads: Gemessen an der Hüllfläche
    der Kuppel (hoehenfeld, Blöcke von 8192 Paaren) sind 24 Arbeiter schneller als 12 (2,6 s
    gegen 3,1 s), bei OpenCascade (Kollision) gleich schnell."""
    return os.cpu_count() or 1


def physische_kerne():
    """So viele Kerne ohne ihre SMT-Zwillinge (mindestens 1): unter Linux aus /sys gezählt (Paket
    und Kern), sonst geschätzt – ab 8 Threads die Hälfte. Gemessen an der Kollision von Manuels
    4-Achs-Testteil (12 Kerne, 24 Threads): 8 Arbeiter 192 s, 12 → 183 s, 16 → 213 s, 24 → 238 s."""
    import glob

    kerne = set()
    try:
        for pfad in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/topology/core_id"):
            ordner = os.path.dirname(pfad)
            with open(os.path.join(ordner, "physical_package_id")) as paket, open(pfad) as kern:
                kerne.add((paket.read().strip(), kern.read().strip()))
    except OSError:
        kerne = set()
    if kerne:
        return len(kerne)
    threads = anzahl_kerne()
    return max(1, threads // 2) if threads >= 8 else threads


def gewuenschte_anzahl():
    """So viele Arbeiter darf der Pool haben: die Einstellung (EINSTELLUNG_ANZAHL im
    Parameter-System, 0 = selbst wählen), sonst so viele wie Kerne."""
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
        self._melder = {}  # Arbeiter -> QSocketNotifier (_melder_abgleichen)
        self._laden = []  # Module, die jeder Arbeiter gleich nach dem Start lädt (vorwaermen)
        self.in_arbeit = 0  # so viele Aufträge liefen bisher in Arbeitern (für Prüfungen)

    # --- Nach außen ------------------------------------------------------------------

    def verfuegbar(self):
        """Gibt es Nebenrechner? Ohne FreeCADCmd nicht; auch nicht, wenn die Arbeiter nicht
        starten (dann rechnet der Aufrufer selbst) – und nie in einem Arbeiter selbst: Ein
        Auftrag ist schon ein Stück, er verteilt nicht weiter."""
        if os.environ.get("CAMADDON_ARBEITER") == "1":
            return False
        return self._freecadcmd is not None and not self._fehlgeschlagen

    def auftrag(self, modul, funktion, *args, **kwargs):
        """Reiht `camaddon.<modul>.<funktion>(*args, **kwargs)` ein; gibt den Auftrag zurück.
        NichtVerfuegbar ohne Nebenrechner."""
        if not self.verfuegbar():
            raise NichtVerfuegbar(self._grund())
        self._zaehler += 1
        auftrag = Auftrag(self, self._zaehler, modul, funktion, args, kwargs)
        auftrag.gruppe, auftrag.gleichzeitig = getattr(self, "_gruppe", (None, None))
        self._warteschlange.append(auftrag)
        self._verteilen()
        self._uhren()
        return auftrag

    @contextlib.contextmanager
    def gruppe(self, name, gleichzeitig):
        """Die Aufträge, die in diesem Block entstehen, gehören zur Gruppe `name`: Höchstens
        `gleichzeitig` davon rechnen zugleich (Auftrag.gruppe) – gesetzt, bevor sie verteilt
        werden."""
        vorher = getattr(self, "_gruppe", (None, None))
        self._gruppe = (name, gleichzeitig)
        try:
            yield
        finally:
            self._gruppe = vorher

    def vorwaermen(self, module):
        """Startet die Arbeiter bis `anzahl` und lässt jeden die Module `module` (Namen in
        camaddon) laden, auch die, die später starten – für ein Fenster, dessen erste Rechnung
        sonst darauf wartete: Die Vorschau im 4-Achs-Assistenten verteilt auf alle Arbeiter, und
        jeder lud dafür erst 0,6–0,8 s seine Module (P-2026-10-11-13)."""
        if not self.verfuegbar():
            return
        neu = [m for m in module if m not in self._laden]
        self._laden.extend(neu)
        if neu:
            for arbeiter in self._arbeiter:
                if arbeiter.verbindung is not None:
                    with contextlib.suppress(OSError, EOFError):
                        arbeiter.verbindung.send(("laden", neu))
        while len(self._arbeiter) < self.anzahl and not self._fehlgeschlagen:
            self._starten()
        self._uhren()

    def gemeinsam(self, schluessel, wert):
        """Legt gemeinsame Daten ab; Aufträge verweisen mit Gemeinsam(schluessel) darauf. Der
        Schlüssel benennt den Wert (etwa ein Fingerabdruck des Inhalts): Gibt es ihn schon,
        bleibt der alte Wert, und die Arbeiter, die ihn haben, bekommen ihn nicht noch einmal."""
        if schluessel not in self._gemeinsam:
            self._gemeinsam[schluessel] = wert
        return Gemeinsam(schluessel)

    def vergessen(self, schluessel):
        """Gibt gemeinsame Daten frei – hier und in den Arbeitern."""
        self._gemeinsam.pop(schluessel, None)
        for arbeiter in self._arbeiter:
            if schluessel in arbeiter.gemeinsam and arbeiter.verbindung is not None:
                del arbeiter.gemeinsam[schluessel]
                with contextlib.suppress(OSError, EOFError):
                    arbeiter.verbindung.send(("vergiss", schluessel))

    def kopie(self, dokument, wiederverwenden=False):
        """Speichert eine Kopie des Dokuments für die Arbeiter; gibt Dokument(pfad) zurück. Je
        Dokument bleiben die letzten KOPIEN_JE_DOKUMENT liegen (ein Arbeiter hat die ältere
        vielleicht noch offen). Mit `wiederverwenden` die letzte, wenn sich das Dokument seitdem
        nicht geändert hat (_Aenderungen) – für Aufträge, die die Kopie nur lesen: Die Vorschau
        im 4-Achs-Assistenten speicherte nach jeder Eingabe neu, 0,44 s, in denen das Fenster
        stand (P-2026-10-11-08); die Arbeiter haben sie dann auch schon offen."""
        self._einrichten()
        ordner = os.path.join(self._ordner, "kopien")
        os.makedirs(ordner, exist_ok=True)
        name = dokument.Name
        pfade = self._kopien.setdefault(name, [])
        aenderungen = _Aenderungen.beobachten()
        if (
            wiederverwenden
            and pfade
            and aenderungen is not None
            and aenderungen.unveraendert(dokument, pfade[-1])
            and os.path.isfile(pfade[-1])
        ):
            return Dokument(pfade[-1])
        pfad = os.path.join(ordner, f"{name}-{len(pfade) + 1}.FCStd")
        while pfad in pfade or os.path.exists(pfad):
            pfad = os.path.join(ordner, f"{name}-{secrets.token_hex(3)}.FCStd")
        if aenderungen is not None:
            aenderungen.kopiert(dokument, pfad)
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
        for melder in self._melder.values():
            melder.setEnabled(False)  # sonst weckte er, solange er Ungelesenes hat, immer wieder
        try:
            self._verbindungen_annehmen()
            for arbeiter in list(self._arbeiter):
                self._lesen(arbeiter)
            self._verteilen()
            for arbeiter in list(self._arbeiter):
                self._post_senden(arbeiter)
        finally:
            self._in_abfrage = False
            for melder in self._melder.values():
                melder.setEnabled(True)
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
        nächsten Auftrag). Seine Unteraufträge fallen mit (_weich_abbrechen)."""
        if auftrag.erledigt:
            return
        if auftrag.fuer is not None:
            self._weich_abbrechen(auftrag)
            self._uhren()
            return
        auftrag.abgebrochen = True
        if auftrag in self._warteschlange:
            self._warteschlange.remove(auftrag)
        arbeiter = auftrag.arbeiter
        if arbeiter is not None:
            self._laufend.pop(auftrag.nummer, None)
            auftrag.arbeiter = None
            self._entfernen(arbeiter)
        self._nachkommen_abbrechen(auftrag)
        self._uhren()

    def beenden(self):
        """Beendet alle Arbeiter und räumt auf; der Pool lässt sich danach weiter benutzen."""
        for auftrag in list(self._laufend.values()) + self._warteschlange:
            auftrag.abgebrochen = True
        for arbeiter in list(self._arbeiter):
            self._entfernen(arbeiter)
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
            # Unteraufträge (P-2026-10-11-07): Der Arbeiter darf selbst verteilen – über diesen
            # Pool, so groß wie er.
            "unter": True,
            "anzahl": self.anzahl,
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
                    puffer_vergroessern(verbindung)
                    arbeiter.verbindung = verbindung
                    if self._laden:
                        with contextlib.suppress(OSError, EOFError):
                            verbindung.send(("laden", list(self._laden)))
                    self._je_gemeldet = True
                    break
            else:
                verbindung.close()  # ein Arbeiter, den es nicht mehr gibt

    # --- Verteilen und Lesen ------------------------------------------------------------

    def _verteilen(self):
        """Gibt wartende Aufträge an freie Arbeiter – je Gruppe höchstens so viele zugleich, wie
        sie darf (Auftrag.gleichzeitig); startet, was an Arbeitern fehlt. Ein Arbeiter, der auf
        seine Unteraufträge wartet, nimmt selbst welche davon (nur seine: So hängt nie ein
        Auftrag an Arbeitern, die alle warten)."""
        laufend = {}
        for arbeiter in self._arbeiter:
            if arbeiter.stapel and not arbeiter.wartet:
                gruppe = arbeiter.stapel[-1].gruppe
                if gruppe is not None:
                    laufend[gruppe] = laufend.get(gruppe, 0) + 1
        wartende = [a for a in self._arbeiter if a.stapel and a.wartet]
        freie = [a for a in self._arbeiter if not a.stapel]
        for arbeiter in wartende + freie:
            if not self._warteschlange:
                break
            if arbeiter.verbindung is None:
                continue
            auftrag = self._naechster(laufend, arbeiter.stapel[-1] if arbeiter.stapel else None)
            if auftrag is not None:
                self._senden(arbeiter, auftrag)
        startend = sum(1 for a in self._arbeiter if a.verbindung is None)
        fehlend = min(self._ausfuehrbar(laufend) - startend, self.anzahl - len(self._arbeiter))
        for _ in range(max(0, fehlend)):
            if self._fehlgeschlagen:
                break
            self._starten()

    def _naechster(self, laufend, von=None):
        """Der erste wartende Auftrag, dessen Gruppe noch einen frei hat – aus der Warteschlange
        genommen und in `laufend` gezählt; None, wenn keiner darf. Mit `von` nur einer, der
        darunter bestellt wurde (_stammt_von)."""
        for k, auftrag in enumerate(self._warteschlange):
            if von is not None and not _stammt_von(auftrag, von):
                continue
            gruppe = auftrag.gruppe
            if gruppe is None or auftrag.gleichzeitig is None:
                return self._warteschlange.pop(k)
            if laufend.get(gruppe, 0) < auftrag.gleichzeitig:
                laufend[gruppe] = laufend.get(gruppe, 0) + 1
                return self._warteschlange.pop(k)
        return None

    def _ausfuehrbar(self, laufend):
        """So viele wartende Aufträge dürften jetzt sofort rechnen (ihre Gruppe hat Platz)."""
        frei = {}
        anzahl = 0
        for auftrag in self._warteschlange:
            gruppe = auftrag.gruppe
            if gruppe is None or auftrag.gleichzeitig is None:
                anzahl += 1
                continue
            frei.setdefault(gruppe, max(0, auftrag.gleichzeitig - laufend.get(gruppe, 0)))
            if frei[gruppe] > 0:
                frei[gruppe] -= 1
                anzahl += 1
        return anzahl

    def _senden(self, arbeiter, auftrag):
        try:
            for schluessel in _gemeinsame_schluessel((auftrag.args, auftrag.kwargs)):
                if schluessel in arbeiter.gemeinsam:
                    arbeiter.gemeinsam.move_to_end(schluessel)
                    continue
                if schluessel not in self._gemeinsam:
                    raise KeyError(f"gemeinsame Daten „{schluessel}“ fehlen")
                arbeiter.verbindung.send(("daten", schluessel, self._gemeinsam[schluessel]))
                arbeiter.gemeinsam[schluessel] = True
                while len(arbeiter.gemeinsam) > GEMEINSAM_JE_ARBEITER:
                    alt, _ = arbeiter.gemeinsam.popitem(last=False)
                    arbeiter.verbindung.send(("vergiss", alt))
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
        arbeiter.stapel.append(auftrag)
        arbeiter.wartet = False
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
        art = nachricht[0]
        if art in _VOM_UNTERPOOL:
            self._unter_verarbeiten(arbeiter, nachricht)
            return
        nummer = nachricht[1]
        auftrag = self._laufend.get(nummer)
        if auftrag is None or auftrag.arbeiter is not arbeiter:
            return  # ein abgebrochener Auftrag, der doch noch etwas meldet
        if art == "fortschritt":
            auftrag.fortschritt = float(nachricht[2])
            if auftrag.bei_fortschritt is not None:
                auftrag.bei_fortschritt(auftrag)
            return
        weich_abgebrochen = auftrag.abgebrochen  # das Ergebnis verfällt, gemeldet ist es schon
        if weich_abgebrochen:
            pass
        elif art == "fertig":
            auftrag.ergebnis = nachricht[2]
            auftrag.fertig = True
        elif art == "fehler":
            auftrag.fehler = nachricht[2]
            auftrag.fehlerart, auftrag.fehlersatz = nachricht[3], nachricht[4]
        else:
            auftrag.fehler = f"unbekannte Meldung {art!r}"
        del self._laufend[nummer]
        auftrag.arbeiter = None
        if auftrag in arbeiter.stapel:
            arbeiter.stapel.remove(auftrag)
        arbeiter.wartet = False  # wartet er weiter, meldet er es wieder („warte“)
        arbeiter.zuletzt = time.monotonic()
        if not weich_abgebrochen:
            self._melden(auftrag)

    def _melden(self, auftrag):
        """Ein Auftrag ist erledigt: Ein Unterauftrag geht an seinen Besteller zurück, sonst ruft
        der Pool bei_fertig. Was er selbst bestellt hat und noch aussteht, fällt weg."""
        if auftrag.fuer is not None:
            self._zurueck(auftrag)
        elif auftrag.bei_fertig is not None:
            auftrag.bei_fertig(auftrag)
        self._nachkommen_abbrechen(auftrag)

    # --- Unteraufträge (P-2026-10-11-07) -------------------------------------------------
    #
    # Ein Arbeiter rechnet einen Auftrag – die Vorschau im 4-Achs-Assistenten etwa – und will
    # Teile davon verteilen (die Hüllfläche je Stellung, das Zusammenfassen der Spirale). Er hat
    # keinen eigenen Pool; über seine Verbindung bestellt er Unteraufträge hier (Unterpool),
    # der Pool reiht sie ein wie jeden Auftrag und schickt ihm die Ergebnisse. Solange er darauf
    # wartet, liest er und nimmt selbst welche davon: So kommen sie auch voran, wenn alle
    # Arbeiter warten. Ergebnisse gehen nur an einen Arbeiter, der liest (wartet oder frei ist)
    # – sonst blockierte das Senden, bis er fertig ist.

    def _unter_verarbeiten(self, arbeiter, nachricht):
        art = nachricht[0]
        if art == "unter":
            _, nummer, modul, funktion, args, kwargs, gruppe, gleichzeitig = nachricht
            self._zaehler += 1
            auftrag = Auftrag(self, self._zaehler, modul, funktion, args, kwargs)
            auftrag.gruppe, auftrag.gleichzeitig = gruppe, gleichzeitig
            auftrag.fuer = (arbeiter, nummer)
            auftrag.eltern = arbeiter.stapel[-1] if arbeiter.stapel else None
            if auftrag.eltern is None or auftrag.eltern.erledigt:
                auftrag.abgebrochen = True
                self._zurueck(auftrag)
            else:
                self._warteschlange.append(auftrag)
        elif art == "gemeinsam":
            self._gemeinsam.setdefault(nachricht[1], nachricht[2])
        elif art == "vergessen":
            self.vergessen(nachricht[1])
        elif art == "warte":
            arbeiter.wartet = bool(arbeiter.stapel)
            self._post_senden(arbeiter)
        elif art == "weiter":
            arbeiter.wartet = False
        elif art == "unter_ab":
            for auftrag in self._warteschlange + list(self._laufend.values()):
                if auftrag.fuer is not None and auftrag.fuer == (arbeiter, nachricht[1]):
                    self._weich_abbrechen(auftrag)
                    break

    def _zurueck(self, auftrag):
        """Das Ergebnis eines Unterauftrags an seinen Besteller – wenn es ihn noch gibt."""
        arbeiter, nummer = auftrag.fuer
        if arbeiter not in self._arbeiter:
            return
        if auftrag.fertig:
            arbeiter.post.append(("unter_fertig", nummer, auftrag.ergebnis))
        elif auftrag.fehler is not None:
            arbeiter.post.append(
                ("unter_fehler", nummer, auftrag.fehler, auftrag.fehlerart, auftrag.fehlersatz)
            )
        else:
            arbeiter.post.append(("unter_ab", nummer))
        self._post_senden(arbeiter)

    def _post_senden(self, arbeiter):
        """Schickt dem Arbeiter, was für ihn liegt – nur, wenn er liest."""
        if not arbeiter.post or arbeiter.verbindung is None:
            return
        if arbeiter.stapel and not arbeiter.wartet:
            return
        post, arbeiter.post = arbeiter.post, []
        try:
            for nachricht in post:
                arbeiter.verbindung.send(nachricht)
        except (OSError, EOFError, ValueError):
            pass  # die Verbindung ist weg – _lesen merkt es

    def _weich_abbrechen(self, auftrag):
        """Nimmt einen Unterauftrag zurück, ohne seinen Arbeiter zu beenden: Wartet er, fällt er
        weg; rechnet er, rechnet er zu Ende, und das Ergebnis verfällt. Der Besteller erfährt es
        gleich; was der Auftrag selbst bestellt hat, fällt mit."""
        if auftrag.erledigt:
            return
        auftrag.abgebrochen = True
        if auftrag in self._warteschlange:
            self._warteschlange.remove(auftrag)
        if auftrag.fuer is not None:
            self._zurueck(auftrag)
        self._nachkommen_abbrechen(auftrag)

    def _nachkommen_abbrechen(self, auftrag):
        """Alles, was unter `auftrag` bestellt wurde und noch aussteht, fällt weg."""
        for kind in self._warteschlange + list(self._laufend.values()):
            if not kind.erledigt and _stammt_von(kind, auftrag):
                self._weich_abbrechen(kind)

    def _gestorben(self, arbeiter, grund):
        """Ein Arbeiter ist weg: Sein Auftrag scheitert – außer, er wurde abgebrochen."""
        self._entfernen(arbeiter, grund)
        if not self._je_gemeldet and not any(a.verbindung is not None for a in self._arbeiter):
            # Noch nie hat sich einer gemeldet: Es gibt keine Nebenrechner.
            self._fehlgeschlagen = True
            FreeCAD.Console.PrintWarning(
                f"CAM-Addon: Nebenrechner {arbeiter.nummer} {grund} – es wird im eigenen Prozess "
                f"gerechnet (Ausgabe des Arbeiters: {self._protokoll_hinweis(arbeiter)}).\n"
            )
            self._alle_scheitern()

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
        for arbeiter in self._arbeiter:
            arbeiter.stapel, arbeiter.wartet, arbeiter.post = [], False, []
        for auftrag in wartend + laufend:
            auftrag.arbeiter = None
            self._melden(auftrag)

    def _entfernen(self, arbeiter, grund="beendet"):
        """Beendet den Arbeiter. Was er noch rechnete und nicht abgebrochen ist, scheitert."""
        if arbeiter in self._arbeiter:
            self._arbeiter.remove(arbeiter)
        self._melder_weg(arbeiter)  # vor dem Schließen der Verbindung
        arbeiter.beenden()
        stapel, arbeiter.stapel = arbeiter.stapel, []
        arbeiter.wartet, arbeiter.post = False, []
        for auftrag in reversed(stapel):
            self._laufend.pop(auftrag.nummer, None)
            auftrag.arbeiter = None
            if not auftrag.erledigt:
                auftrag.fehler = f"Nebenrechner {arbeiter.nummer} {grund}"
                self._melden(auftrag)

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
        # Auch solange Arbeiter starten: Erst das Abfragen nimmt ihre Verbindung an.
        if self.offen() or any(a.verbindung is None for a in self._arbeiter):
            if self._uhr is None:
                self._uhr = QtCore.QTimer()
                self._uhr.setInterval(UHR_MS)
                self._uhr.timeout.connect(self.abfragen)
                self._uhr.start()
        elif self._uhr is not None:
            self._uhr.stop()
            self._uhr = None
        self._melder_abgleichen(QtCore)
        if self._arbeiter:
            if self._aufraeumuhr is None:
                self._aufraeumuhr = QtCore.QTimer()
                self._aufraeumuhr.setInterval(AUFRAEUMEN_MS)
                self._aufraeumuhr.timeout.connect(self.abfragen)
                self._aufraeumuhr.start()
        elif self._aufraeumuhr is not None:
            self._aufraeumuhr.stop()
            self._aufraeumuhr = None

    def _melder_abgleichen(self, QtCore):  # noqa: N803 – das Modul
        """Unter Linux und macOS weckt je Arbeiter ein QSocketNotifier abfragen(), sobald er
        etwas schickt, solange etwas läuft: Die Unteraufträge eines Arbeiters warten so nicht auf
        den QTimer (bis UHR_MS je Weg, an der Vorschau des Testteils Hunderte Wege;
        P-2026-10-11-07). Unter Windows (Pipes) bleibt es beim QTimer."""
        if os.name != "posix":
            return
        sollen = [a for a in self._arbeiter if a.verbindung is not None] if self.offen() else []
        for arbeiter in list(self._melder):
            if arbeiter not in sollen:
                self._melder_weg(arbeiter)
        art = getattr(QtCore.QSocketNotifier, "Type", QtCore.QSocketNotifier).Read
        for arbeiter in sollen:
            if arbeiter not in self._melder:
                melder = QtCore.QSocketNotifier(arbeiter.verbindung.fileno(), art)
                melder.activated.connect(lambda *_: self.abfragen())
                melder.setEnabled(not self._in_abfrage)
                self._melder[arbeiter] = melder

    def _melder_weg(self, arbeiter):
        melder = self._melder.pop(arbeiter, None)
        if melder is not None:
            melder.setEnabled(False)
            melder.deleteLater()


class _Aenderungen:
    """Ein Beobachter der Dokumente (FreeCAD.addDocumentObserver): Je Dokument der Pfad seiner
    letzten Kopie, bis sich darin etwas ändert – ein Objekt, eine Eigenschaft, das Dokument
    selbst, Rückgängig. Was sich nicht zuordnen lässt, macht alle Kopien ungültig."""

    _einer = None

    @classmethod
    def beobachten(cls):
        """Der eine Beobachter (beim ersten Bedarf angemeldet); None, wenn FreeCAD keinen nimmt."""
        if cls._einer is None:
            try:
                einer = cls()
                FreeCAD.addDocumentObserver(einer)
            except Exception:  # noqa: BLE001 – ohne Beobachter wird jedes Mal gespeichert
                return None
            cls._einer = einer
        return cls._einer

    def __init__(self):
        self._kopie = {}  # Dokumentname -> Pfad der Kopie, solange es sich nicht geändert hat

    def unveraendert(self, dokument, pfad):
        return self._kopie.get(dokument.Name) == pfad

    def kopiert(self, dokument, pfad):
        self._kopie[dokument.Name] = pfad

    def _geaendert(self, dokument):
        try:
            self._kopie.pop(dokument.Name, None)
        except Exception:  # noqa: BLE001 – lässt sich nicht zuordnen: alle neu
            self._kopie.clear()

    def _objekt(self, obj, *_):
        try:
            dokument = obj.Document
        except Exception:  # noqa: BLE001
            self._kopie.clear()
            return
        self._geaendert(dokument)

    slotCreatedObject = slotDeletedObject = slotChangedObject = _objekt  # noqa: N815
    slotRelabelObject = _objekt  # noqa: N815

    def _dokument(self, dokument, *_):
        self._geaendert(dokument)

    slotCreatedDocument = slotDeletedDocument = slotChangedDocument = _dokument  # noqa: N815
    slotUndoDocument = slotRedoDocument = slotRelabelDocument = _dokument  # noqa: N815


class Unterpool:
    """Der Pool in einem Arbeiter (P-2026-10-11-07): dieselben Aufrufe wie Nebenrechner, nur
    bestellt er die Aufträge über die Verbindung beim Pool des Hauptprozesses, als Unteraufträge
    des Auftrags, an dem der Arbeiter gerade rechnet. In `warten()` liest er die Ergebnisse und
    rechnet, was der Pool ihm von seinen eigenen Unteraufträgen gibt (`verarbeiten`, die
    Hauptschleife des Arbeiters für eine Meldung). Die Vorschau im 4-Achs-Assistenten rechnete so
    auf einem Kern: am Testteil die Hüllfläche je Stellung (2,6 s beim Schruppen) und das
    Zusammenfassen der Spirale (1,8 s beim Schlichten) – jetzt auf allen."""

    def __init__(self, verbindung, anzahl, verarbeiten):
        self.anzahl = max(1, int(anzahl))
        self._verbindung = verbindung
        self._verarbeiten = verarbeiten
        self._zaehler = 0
        self._offen = {}  # Nummer -> Auftrag, bis sein Ergebnis da ist
        self._gesendet = set()  # die Schlüssel gemeinsamer Daten, die der Pool schon hat
        self._gruppe = (None, None)
        self._kopien = []
        self.in_arbeit = 0

    def verfuegbar(self):
        return self._verbindung is not None and self.anzahl >= 2

    def auftrag(self, modul, funktion, *args, **kwargs):
        if not self.verfuegbar():
            raise NichtVerfuegbar("kein Pool im Hauptprozess")
        self._zaehler += 1
        auftrag = Auftrag(self, self._zaehler, modul, funktion, args, kwargs)
        auftrag.gruppe, auftrag.gleichzeitig = self._gruppe
        try:
            self._verbindung.send(
                ("unter", auftrag.nummer, modul, funktion, args, kwargs) + self._gruppe
            )
        except (OSError, EOFError, ValueError, TypeError) as fehler:
            raise NichtVerfuegbar(f"Unterauftrag: {fehler!r}") from fehler
        self._offen[auftrag.nummer] = auftrag
        self.in_arbeit += 1
        return auftrag

    def vorwaermen(self, module):
        pass  # die Arbeiter des Pools laden selbst

    @contextlib.contextmanager
    def gruppe(self, name, gleichzeitig):
        vorher = self._gruppe
        self._gruppe = (name, gleichzeitig)
        try:
            yield
        finally:
            self._gruppe = vorher

    def gemeinsam(self, schluessel, wert):
        """Gibt die Daten dem Pool – einmal; er verteilt sie wie seine eigenen."""
        if schluessel not in self._gesendet:
            self._verbindung.send(("gemeinsam", schluessel, wert))
            self._gesendet.add(schluessel)
        return Gemeinsam(schluessel)

    def vergessen(self, schluessel):
        self._gesendet.discard(schluessel)
        with contextlib.suppress(OSError, EOFError):
            self._verbindung.send(("vergessen", schluessel))

    def kopie(self, dokument, wiederverwenden=False):  # noqa: ARG002 – wie Nebenrechner.kopie
        """Eine Kopie des Dokuments im Ordner des Arbeiters (die anderen öffnen sie dort)."""
        ordner = os.path.join(os.getcwd(), "kopien")
        os.makedirs(ordner, exist_ok=True)
        pfad = os.path.join(ordner, f"{dokument.Name}-{secrets.token_hex(4)}.FCStd")
        dokument.saveCopy(pfad)
        self._kopien.append(pfad)
        for alt in self._kopien[:-KOPIEN_JE_DOKUMENT]:
            with contextlib.suppress(OSError):
                os.remove(alt)
        del self._kopien[:-KOPIEN_JE_DOKUMENT]
        return Dokument(pfad)

    def warten(self, auftraege, zwischendurch=None):
        """Wie Nebenrechner.warten. Dabei liest der Arbeiter: Ergebnisse, gemeinsame Daten – und
        Aufträge, die er selbst rechnet (seine eigenen Unteraufträge)."""
        auftraege = list(auftraege)
        gemeldet = False
        try:
            while not all(a.erledigt for a in auftraege):
                if zwischendurch is not None and zwischendurch() is False:
                    for a in auftraege:
                        self.abbrechen(a)
                    break
                if not gemeldet:
                    self._verbindung.send(("warte",))
                    gemeldet = True
                # Hat er gerechnet, weiß der Pool nicht, ob er noch wartet.
                if self._verbindung.poll(TAKT) and self._lesen() == "auftrag":
                    gemeldet = False
        finally:
            with contextlib.suppress(OSError, EOFError):
                self._verbindung.send(("weiter",))
        for a in auftraege:
            if a.abgebrochen:
                raise Abgebrochen(repr(a))
            if a.fehler is not None:
                raise Fehler(a.fehler, a.fehlerart, a.fehlersatz)
        return [a.ergebnis for a in auftraege]

    def abfragen(self):
        while self._verbindung.poll(0):
            self._lesen()

    def abbrechen(self, auftrag):
        if auftrag.erledigt:
            return
        auftrag.abgebrochen = True
        self._offen.pop(auftrag.nummer, None)
        with contextlib.suppress(OSError, EOFError):
            self._verbindung.send(("unter_ab", auftrag.nummer))

    def offen(self):
        return bool(self._offen)

    def beenden(self):
        pass

    @property
    def arbeiter(self):
        return 0

    def _lesen(self):
        """Eine Meldung vom Pool; gibt ihre Art zurück. EOFError, wenn er weg ist."""
        nachricht = self._verbindung.recv()
        art = nachricht[0]
        if art in ("unter_fertig", "unter_fehler", "unter_ab"):
            auftrag = self._offen.pop(nachricht[1], None)
            if auftrag is None:
                return art
            if art == "unter_fertig":
                auftrag.ergebnis = nachricht[2]
                auftrag.fertig = True
            elif art == "unter_fehler":
                auftrag.fehler = nachricht[2]
                auftrag.fehlerart, auftrag.fehlersatz = nachricht[3], nachricht[4]
            else:
                auftrag.abgebrochen = True
        elif not self._verarbeiten(nachricht):
            raise EOFError("der Pool hat den Arbeiter beendet")
        return art


PUFFER = 4 * 1024 * 1024  # Byte: so viel darf eine Verbindung aufnehmen, ohne dass Senden wartet


def puffer_vergroessern(verbindung):
    """Gibt der Verbindung (ein Unix-Socket) einen Sendepuffer von PUFFER Byte, soweit das System
    ihn erlaubt (net.core.wmem_max). Mit den üblichen 208 KiB wartete der Prozess der Oberfläche
    bei jedem Auftrag über 208 KiB, bis der Arbeiter las – und der kam, wenn alle Kerne rechnen,
    erst spät dran: An der Hüllfläche je Stellung des 4-Achs-Testteils (96 Stücke à 240 KiB) stand
    er so 0,34 von 1,1 s (P-2026-10-11-09). Unter Windows (Pipes) nichts."""
    import socket

    try:
        dup = socket.fromfd(verbindung.fileno(), socket.AF_UNIX, socket.SOCK_STREAM)
    except (AttributeError, OSError, ValueError):
        return
    try:
        dup.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, PUFFER)
        dup.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, PUFFER)
    except OSError:
        pass
    finally:
        dup.close()


# Eine Liste oder ein Tupel mit mehr Einträgen ist Daten, kein Ort für Platzhalter: weder der Pool
# noch der Arbeiter sucht darin (die Stationen der Abfahrt: 330 000 Tupel, je Auftrag einmal
# durchsucht und im Arbeiter neu gebaut; P-2026-10-11-12).
FOLGE_DATEN = 1000


def ist_datenfolge(wert):
    return isinstance(wert, (list, tuple)) and len(wert) > FOLGE_DATEN


# Was ein Arbeiter über seinen Unterpool meldet (P-2026-10-11-07).
_VOM_UNTERPOOL = frozenset({"unter", "gemeinsam", "vergessen", "warte", "weiter", "unter_ab"})


def _stammt_von(auftrag, ahne):
    """Wurde `auftrag` unter `ahne` bestellt – von ihm oder einem seiner Unteraufträge?"""
    eltern = auftrag.eltern
    while eltern is not None:
        if eltern is ahne:
            return True
        eltern = eltern.eltern
    return False


def _gemeinsame_schluessel(wert, tiefe=0):
    """Die Schlüssel aller Gemeinsam-Platzhalter in `wert` – bis drei Ebenen tief in Listen,
    Tupeln und Wörterbüchern (tiefer sucht der Arbeiter auch nicht), nicht in langen Folgen
    (FOLGE_DATEN)."""
    if isinstance(wert, Gemeinsam):
        return {wert.schluessel}
    if tiefe >= 3 or ist_datenfolge(wert):
        return set()
    gefunden = set()
    if isinstance(wert, dict):
        for v in wert.values():
            gefunden |= _gemeinsame_schluessel(v, tiefe + 1)
    elif isinstance(wert, (list, tuple)):
        for v in wert:
            gefunden |= _gemeinsame_schluessel(v, tiefe + 1)
    return gefunden


def form_gemeinsam(pool, shape):
    """Eine Form (Part.Shape) als gemeinsame Daten – einmal je Arbeiter, nach dem Fingerabdruck
    ihres BREP-Texts; die Arbeiter bekommen daraus wieder eine Form. Gibt den Platzhalter
    zurück."""
    import hashlib

    brep = shape.exportBrepToString()
    kennung = hashlib.blake2b(brep.encode("utf-8"), digest_size=16).hexdigest()
    return pool.gemeinsam("form-" + kennung, Form(brep))


def ereignisse():
    """Fürs Warten auf die Arbeiter (`warten(..., zwischendurch=ereignisse)`): Das Fenster
    verarbeitet seine Ereignisse, ohne Oberfläche nichts; immer True (kein Abbruch)."""
    try:
        from PySide import QtGui
    except ImportError:
        return True
    if QtGui.QApplication.instance() is not None:
        QtGui.QApplication.processEvents()
    return True


def ereignisse_ohne_eingaben():
    """Wie ereignisse(), aber ohne Maus und Tastatur: Das Fenster zeichnet sich neu, nimmt aber
    keinen Klick an – für das Warten mitten in einer Neuberechnung (die Bahn einer Operation),
    wo ein Klick auf ein Objekt fiele, das gerade gerechnet wird (FreeCAD 26.3 stürzte so ab,
    P-2026-10-10-45). Immer True."""
    try:
        from PySide import QtCore, QtGui
    except ImportError:
        return True
    if QtGui.QApplication.instance() is not None:
        QtGui.QApplication.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)
    return True


def stuecke(anzahl, pool_groesse, je_arbeiter=4, mindestens=1):
    """[(von, bis)] – `anzahl` Dinge in Stücke für die Arbeiter: je Arbeiter `je_arbeiter`,
    keins kürzer als `mindestens`."""
    teile = max(1, min(pool_groesse * je_arbeiter, anzahl // max(1, mindestens)))
    grenzen = [round(k * anzahl / teile) for k in range(teile + 1)]
    return [(a, b) for a, b in zip(grenzen, grenzen[1:], strict=False) if b > a]


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


def _probe_verfuegbar():
    """Ob es im Arbeiter selbst Nebenrechner gibt (den Unterpool)."""
    return pool().verfuegbar()


def _probe_geladen(modul, dauer=0.0):
    """Hat der Arbeiter `camaddon.<modul>` schon geladen (vorwaermen)?"""
    geladen = "camaddon." + modul in sys.modules
    time.sleep(dauer)
    return geladen


def _probe_verschachtelt(werte, dauer=0.0, fehler=False):
    """Bestellt je Wert einen Unterauftrag _probe (im Arbeiter über den Unterpool) – die Summe
    der Quadrate; mit `fehler` noch einen, der scheitert."""
    p = pool()
    auftraege = [p.auftrag("nebenrechner", "_probe", x, dauer=dauer) for x in werte]
    if fehler:
        auftraege.append(p.auftrag("nebenrechner", "_probe_fehler"))
    return sum(p.warten(auftraege))


def _probe_tief(tiefe):
    """Zwei Unteraufträge je Ebene, `tiefe` Ebenen: 2 ** tiefe."""
    if tiefe <= 0:
        return 1
    p = pool()
    return sum(p.warten([p.auftrag("nebenrechner", "_probe_tief", tiefe - 1) for _ in range(2)]))


def _probe_gemeinsam_verschachtelt(zahlen):
    """Gemeinsame Daten aus dem Arbeiter, in zwei Unteraufträgen summiert."""
    p = pool()
    g = p.gemeinsam("probe-verschachtelt", list(zahlen))
    return p.warten([p.auftrag("nebenrechner", "_probe_summe", g, k) for k in (1, 2)])
