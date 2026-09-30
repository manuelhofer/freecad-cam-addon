# SPDX-License-Identifier: LGPL-2.1-or-later
"""Nach Updates schauen – mit Git oder ohne (P-2026-09-25-24, P-2026-09-25-57).

Ist der Addon-Ordner ein Git-Klon (Anleitung mit GitHub Desktop im README),
fragt das Addon per Git bei GitHub nach. Angemeldet wird mit dem, was auf dem
Rechner schon eingerichtet ist (Git bzw. GitHub Desktop); im Addon liegt kein
Schlüssel. So geht es auch, solange das Repository privat ist – der
Addon-Manager von FreeCAD kann das nicht (ausprobiert, P-2026-09-25-23).

Kam das Addon ohne Git (Zeile aus dem README, installieren.py), liest es die
Version direkt aus der package.xml bei GitHub (HTTPS) und aktualisiert mit
installieren.py – dafür muss das Repository öffentlich sein.

Ausnahme von der Regel „keine Aufrufe externer Programme“: nur Git, nur hier.

Läuft ohne Oberfläche; die Oberfläche steht in gui_aktualisierung.py.
"""

import contextlib
import glob
import importlib.util
import os
import shutil
import subprocess
from dataclasses import dataclass

from . import ADDON_ORDNER, version_aus_xml

ZWEIG = "main"
ZEITLIMIT_S = 30  # je Git-Aufruf und Download; ohne Netz soll die Suche nicht ewig laufen
# Unter Windows öffnet ein Programm wie git.exe, aus FreeCAD (ohne Konsole)
# gestartet, sonst jedes Mal kurz ein schwarzes Konsolenfenster. Anderswo
# gibt es den Wert nicht, dort bleibt es bei 0.
OHNE_FENSTER = getattr(subprocess, "CREATE_NO_WINDOW", 0)
# Ohne Git: die Version steht in der package.xml auf GitHub.
ADRESSE_VERSION = (
    f"https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/{ZWEIG}/package.xml"
)

# Mögliche Ergebnisse der Suche.
AKTUELL = "aktuell"
NEU = "neu"
LOKAL_GEAENDERT = "lokal_geaendert"  # eigene Änderungen im Ordner: nicht blind überschreiben
KEIN_GIT = "kein_git"  # Git ist auf dem Rechner nicht zu finden
FEHLER = "fehler"  # z. B. kein Netz, keine Anmeldung


@dataclass
class Ergebnis:
    """Ergebnis von `pruefe()`."""

    status: str  # eine der Konstanten oben
    version_neu: str = ""
    version_jetzt: str = ""
    meldung: str = ""  # Gits Fehlertext bei FEHLER


def git_programm():
    """Pfad zu Git: erst im Suchpfad, dann das von GitHub Desktop mitgebrachte – oder None."""
    gefunden = shutil.which("git")
    if gefunden:
        return gefunden
    # GitHub Desktop legt sein Git unter Windows nicht in den Suchpfad.
    lokal = os.environ.get("LOCALAPPDATA", "")
    if lokal:
        muster = os.path.join(
            lokal, "GitHubDesktop", "app-*", "resources", "app", "git", "cmd", "git.exe"
        )
        kandidaten = sorted(glob.glob(muster))  # app-3.4.1, app-3.4.2, …: die neueste zuletzt
        if kandidaten:
            return kandidaten[-1]
    return None


def pruefe(ordner=ADDON_ORDNER, adresse_version=ADRESSE_VERSION):
    """Schaut bei GitHub nach, ob es einen neueren Stand gibt.

    Mit Git holt es dafür den Stand von GitHub (git fetch), ohne Git nur die
    package.xml. Keine Datei des Addons ändert sich – das tut erst
    `aktualisiere()`.
    """
    if not os.path.isdir(os.path.join(ordner, ".git")):
        return _vergleiche_per_https(ordner, adresse_version)
    git = git_programm()
    if git is None:
        return Ergebnis(KEIN_GIT)
    try:
        return _vergleiche_mit_github(git, ordner)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as fehler:
        return Ergebnis(FEHLER, meldung=str(fehler))


def netz_vorbereiten(ordner=ADDON_ORDNER):
    """Im Hauptthread vor der Suche aufrufen: Ohne Git lädt pruefe() mit installieren.hole(),
    und dessen Weg über Qt (wenn Pythons ssl fehlt) braucht den im Hauptthread angelegten
    Netzzugang des Addon-Managers."""
    if os.path.isdir(os.path.join(ordner, ".git")):
        return
    with contextlib.suppress(OSError):  # ohne installieren.py: Das meldet die Suche selbst.
        _installierer(ordner).netz_vorbereiten()


def aktualisiere(ordner=ADDON_ORDNER, adresse_zip=None, parameter=None):
    """Holt den neuen Stand.

    Mit Git: nur vorspulen, nie über eigene Änderungen hinweg. Ohne Git: das
    ZIP von GitHub an die Stelle des Ordners, wie mit der Zeile aus dem README
    (installieren.py aus diesem Ordner; `adresse_zip` und `parameter` nur für
    die Prüfungen).
    """
    if not os.path.isdir(os.path.join(ordner, ".git")):
        installierer = _installierer(ordner)
        weitere = {"parameter": parameter} if parameter else {}
        installierer.installiere(adresse_zip or installierer.ZIP_ADRESSE, ziel=ordner, **weitere)
        return
    _git(git_programm(), ordner, "merge", "--ff-only", "--quiet", f"origin/{ZWEIG}")


def _vergleiche_per_https(ordner, adresse):
    jetzt = _version_in(ordner)
    try:
        # hole() lädt wie die Zeile aus dem README – auch, wenn Pythons ssl fehlt.
        daten = _installierer(ordner).hole(adresse, ZEITLIMIT_S)
        neu = version_aus_xml(daten.decode("utf-8"))
    except (OSError, ValueError) as fehler:  # kein Netz, privat (404), kaputt
        return Ergebnis(FEHLER, meldung=str(fehler))
    if not ist_neuer(neu, jetzt):
        return Ergebnis(AKTUELL, version_jetzt=jetzt)
    return Ergebnis(NEU, version_neu=neu, version_jetzt=jetzt)


def _version_in(ordner):
    try:
        with open(os.path.join(ordner, "package.xml"), encoding="utf-8") as datei:
            return version_aus_xml(datei.read())
    except OSError:
        return "?"


def _installierer(ordner):
    """installieren.py aus dem Addon-Ordner als Modul – dieselbe Datei wie für die Zeile im README."""
    spec = importlib.util.spec_from_file_location(
        "camaddon_installieren", os.path.join(ordner, "installieren.py")
    )
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def ist_neuer(neu, jetzt):
    """Ist Version `neu` höher als `jetzt`? Verglichen wird Zahl für Zahl: 0.3.10 > 0.3.9."""
    try:
        return _als_zahlen(neu) > _als_zahlen(jetzt)
    except ValueError:
        # Unlesbare Version: lieber einmal zu oft fragen als ein Update verschweigen.
        return neu != jetzt


def _als_zahlen(version):
    return tuple(int(teil) for teil in version.split("."))


def _vergleiche_mit_github(git, ordner):
    _git(git, ordner, "fetch", "--quiet", "origin", ZWEIG)
    jetzt = version_aus_xml(_git(git, ordner, "show", "HEAD:package.xml"))
    neu = version_aus_xml(_git(git, ordner, "show", f"origin/{ZWEIG}:package.xml"))
    # Gemeldet wird nur eine höhere Version. Änderungen ohne neue Version –
    # Tests, Doku, Aufräumen – kommen mit der nächsten Version mit. Sonst
    # hieße der Hinweis „neue Version 0.3.3, installiert ist 0.3.3“ (B-003).
    if not ist_neuer(neu, jetzt):
        return Ergebnis(AKTUELL, version_jetzt=jetzt)

    # Geänderte Dateien oder eigene Commits im Ordner: Dann entscheidet der
    # Benutzer selbst, statt dass das Update etwas überschreibt.
    geaendert = _git(git, ordner, "status", "--porcelain", "--untracked-files=no") != ""
    if geaendert or not _ist_vorfahr(git, ordner, "HEAD", f"origin/{ZWEIG}"):
        return Ergebnis(LOKAL_GEAENDERT, version_neu=neu, version_jetzt=jetzt)
    return Ergebnis(NEU, version_neu=neu, version_jetzt=jetzt)


def _ist_vorfahr(git, ordner, frueher, spaeter):
    """Liegt `frueher` in der Geschichte von `spaeter`? Nur dann lässt sich vorspulen."""
    try:
        _git(git, ordner, "merge-base", "--is-ancestor", frueher, spaeter)
    except RuntimeError:  # „nein“ meldet Git über den Rückgabewert
        return False
    return True


def _git(git, ordner, *argumente):
    """Führt `git -C <ordner> <argumente>` aus und gibt die Ausgabe zurück.

    Endet Git mit einem Fehler, wirft die Funktion RuntimeError mit Gits
    Fehlertext.
    """
    umgebung = dict(os.environ)
    # Git darf nie nach einem Passwort fragen: Es läuft ohne Fenster im
    # Hintergrund, eine Rückfrage würde ewig warten.
    umgebung.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "GIT_ASKPASS": ""})
    ergebnis = subprocess.run(
        [git, "-C", ordner, *argumente],
        capture_output=True,
        text=True,
        # Git gibt UTF-8 aus. Ohne diese Angabe läse Python mit der Kodierung
        # des Systems, unter Windows meist nicht UTF-8 – und package.xml
        # enthält Umlaute (gefunden im Test).
        encoding="utf-8",
        errors="replace",
        timeout=ZEITLIMIT_S,
        env=umgebung,
        stdin=subprocess.DEVNULL,
        creationflags=OHNE_FENSTER,
    )
    if ergebnis.returncode != 0:
        raise RuntimeError((ergebnis.stderr or ergebnis.stdout).strip())
    return ergebnis.stdout.strip()
