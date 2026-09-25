# SPDX-License-Identifier: LGPL-2.1-or-later
"""Nach Updates schauen, solange das Repository privat ist (P-2026-09-25-24).

Der Addon-Manager von FreeCAD kann private Repositories nicht aktualisieren
(ausprobiert, P-2026-09-25-23). Ist der Addon-Ordner ein Git-Klon – so legt
ihn die Anleitung im README an –, fragt das Addon selbst per Git bei GitHub
nach. Angemeldet wird mit dem, was auf dem Rechner schon eingerichtet ist
(Git bzw. GitHub Desktop); im Addon liegt kein Schlüssel.

Ausnahme von der Regel „keine Aufrufe externer Programme“: nur Git, nur hier.

Läuft ohne Oberfläche; die Oberfläche steht in gui_aktualisierung.py.
"""

import glob
import os
import shutil
import subprocess
from dataclasses import dataclass

from . import ADDON_ORDNER, version_aus_xml

ZWEIG = "main"
ZEITLIMIT_S = 30  # je Git-Aufruf; ohne Netz soll die Suche nicht ewig laufen

# Mögliche Ergebnisse der Suche.
AKTUELL = "aktuell"
NEU = "neu"
LOKAL_GEAENDERT = "lokal_geaendert"  # eigene Änderungen im Ordner: nicht blind überschreiben
KEIN_GIT_ORDNER = "kein_git_ordner"  # z. B. als ZIP installiert
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


def pruefe(ordner=ADDON_ORDNER):
    """Schaut bei GitHub nach, ob es einen neueren Stand gibt.

    Holt dafür den Stand von GitHub (git fetch), ändert aber keine Datei des
    Addons – das tut erst `aktualisiere()`.
    """
    if not os.path.isdir(os.path.join(ordner, ".git")):
        return Ergebnis(KEIN_GIT_ORDNER)
    git = git_programm()
    if git is None:
        return Ergebnis(KEIN_GIT)
    try:
        return _vergleiche_mit_github(git, ordner)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as fehler:
        return Ergebnis(FEHLER, meldung=str(fehler))


def aktualisiere(ordner=ADDON_ORDNER):
    """Holt den neuen Stand – nur vorspulen, nie über eigene Änderungen hinweg."""
    _git(git_programm(), ordner, "merge", "--ff-only", "--quiet", f"origin/{ZWEIG}")


def _vergleiche_mit_github(git, ordner):
    jetzt = version_aus_xml(_git(git, ordner, "show", "HEAD:package.xml"))
    _git(git, ordner, "fetch", "--quiet", "origin", ZWEIG)
    if _git(git, ordner, "rev-parse", "HEAD") == _git(git, ordner, "rev-parse", f"origin/{ZWEIG}"):
        return Ergebnis(AKTUELL, version_jetzt=jetzt)

    neu = version_aus_xml(_git(git, ordner, "show", f"origin/{ZWEIG}:package.xml"))
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
    )
    if ergebnis.returncode != 0:
        raise RuntimeError((ergebnis.stderr or ergebnis.stdout).strip())
    return ergebnis.stdout.strip()
