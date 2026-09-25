# SPDX-License-Identifier: LGPL-2.1-or-later
"""Nach Updates schauen, solange das Repository privat ist (P-2026-09-25-24).

Der Addon-Manager von FreeCAD kann private Repositories nicht aktualisieren
(ausprobiert, P-2026-09-25-23). Ist der Addon-Ordner ein Git-Klon – so legt
ihn die Anleitung im README an –, fragt das Addon selbst per Git bei GitHub
nach. Angemeldet wird mit dem, was auf dem Rechner schon eingerichtet ist
(Git bzw. GitHub Desktop); im Addon liegt kein Schlüssel.

Ausnahme von der Regel „keine Aufrufe externer Programme“: nur Git, nur hier.
Git darf nie nach einem Passwort fragen – es läuft ohne Fenster im
Hintergrund, eine Rückfrage würde ewig hängen.

Läuft ohne Oberfläche; die Oberfläche steht in gui_aktualisierung.py.
"""

import glob
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from . import ADDON_ORDNER

ZWEIG = "main"
ZEITLIMIT_S = 30

# Ergebnis der Prüfung.
AKTUELL = "aktuell"
NEU = "neu"
LOKAL_GEAENDERT = "lokal_geaendert"  # eigene Änderungen im Ordner: nicht blind überschreiben
KEIN_GIT_ORDNER = "kein_git_ordner"  # z. B. als ZIP installiert
KEIN_GIT = "kein_git"
FEHLER = "fehler"  # z. B. kein Netz, keine Anmeldung


@dataclass
class Ergebnis:
    status: str
    version_neu: str = ""
    version_jetzt: str = ""
    meldung: str = ""  # Text von Git bei FEHLER, für das Report-Fenster


def git_programm():
    """Pfad zu git: erst im Suchpfad, dann das von GitHub Desktop mitgebrachte."""
    gefunden = shutil.which("git")
    if gefunden:
        return gefunden
    # GitHub Desktop legt sein Git nicht in den Suchpfad (Windows).
    lokal = os.environ.get("LOCALAPPDATA", "")
    if lokal:
        muster = os.path.join(
            lokal, "GitHubDesktop", "app-*", "resources", "app", "git", "cmd", "git.exe"
        )
        kandidaten = sorted(glob.glob(muster))
        if kandidaten:
            return kandidaten[-1]
    return None


def _git(ordner, *argumente, git=None):
    umgebung = dict(os.environ)
    # Niemals nachfragen – ohne Fenster würde Git sonst endlos warten.
    umgebung.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "GIT_ASKPASS": ""})
    ergebnis = subprocess.run(
        [git or git_programm(), "-C", ordner, *argumente],
        capture_output=True,
        text=True,
        # Git gibt UTF-8 aus; ohne diese Angabe läse Python mit der Kodierung
        # des Systems (unter Windows meist nicht UTF-8) – package.xml enthält
        # Umlaute (gefunden im Test).
        encoding="utf-8",
        errors="replace",
        timeout=ZEITLIMIT_S,
        env=umgebung,
        stdin=subprocess.DEVNULL,
    )
    if ergebnis.returncode != 0:
        raise RuntimeError((ergebnis.stderr or ergebnis.stdout).strip())
    return ergebnis.stdout.strip()


def _version(xml_text):
    try:
        wurzel = ET.fromstring(xml_text)
        return wurzel.find("{*}version").text.strip()
    except (ET.ParseError, AttributeError):
        return "?"


def pruefe(ordner=ADDON_ORDNER, git=None):
    """Schaut bei GitHub nach, ob es einen neueren Stand gibt."""
    git = git or git_programm()
    if not os.path.isdir(os.path.join(ordner, ".git")):
        return Ergebnis(KEIN_GIT_ORDNER)
    if not git:
        return Ergebnis(KEIN_GIT)
    try:
        jetzt = _version(_git(ordner, "show", "HEAD:package.xml", git=git))
        _git(ordner, "fetch", "--quiet", "origin", ZWEIG, git=git)
        kopf = _git(ordner, "rev-parse", "HEAD", git=git)
        fern = _git(ordner, "rev-parse", f"origin/{ZWEIG}", git=git)
        if kopf == fern:
            return Ergebnis(AKTUELL, version_jetzt=jetzt)
        neu = _version(_git(ordner, "show", f"origin/{ZWEIG}:package.xml", git=git))
        geaendert = _git(ordner, "status", "--porcelain", "--untracked-files=no", git=git)
        try:
            _git(ordner, "merge-base", "--is-ancestor", "HEAD", f"origin/{ZWEIG}", git=git)
            nur_zurueck = True
        except RuntimeError:
            nur_zurueck = False  # eigene Commits im Ordner
        if geaendert or not nur_zurueck:
            return Ergebnis(LOKAL_GEAENDERT, version_neu=neu, version_jetzt=jetzt)
        return Ergebnis(NEU, version_neu=neu, version_jetzt=jetzt)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as fehler:
        return Ergebnis(FEHLER, meldung=str(fehler))


def aktualisiere(ordner=ADDON_ORDNER, git=None):
    """Holt den neuen Stand – nur vorwärts, nie über eigene Änderungen hinweg."""
    _git(ordner, "merge", "--ff-only", "--quiet", f"origin/{ZWEIG}", git=git or git_programm())
