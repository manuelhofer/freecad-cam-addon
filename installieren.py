# SPDX-License-Identifier: LGPL-2.1-or-later
"""Installiert oder aktualisiert das CAM-Addon mit einer Zeile (P-2026-09-25-43).

In FreeCAD **Ansicht → Fenster → Python-Konsole** öffnen, eine der drei
Zeilen hineinkopieren, Enter, danach FreeCAD neu starten. Die erste lädt diese
Datei mit dem curl des Systems (Windows), die zweite über den Netzzugang des
Addon-Managers (Qt), die dritte über Pythons urllib:

    import subprocess as s; exec(s.run(["curl", "-sSfL", "https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py"], capture_output=True, check=True).stdout)
    import NetworkManager as n; n.InitializeNetworkManager(); exec(n.AM_NETWORK_MANAGER.blocking_get("https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py").data())
    import urllib.request as u; exec(u.urlopen("https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py").read())

Es braucht alle drei: Manchem FreeCAD fehlt Pythons ssl, dann meldet urllib
„unknown url type: https“ (Manuel, 2026-09-30) – dafür kam die Qt-Zeile
(P-2026-09-30-33). In FreeCAD 26.3.0RC1 unter Windows kommen beide nicht durch:
Qt gibt None („'NoneType' object has no attribute 'data'“), urllib hat kein
https (Manuel, 2026-10-10, B-017) – dort hilft nur curl, das Windows 10/11
mitbringt (P-2026-10-10-38). Warum Qt None gibt: Der Addon-Manager von 26.3
lehnt jede blockierende Anfrage im Hauptthread ab – aus der Konsole lädt die
Qt-Zeile dort auf keinem System; im Thread der Update-Suche lädt Qt weiter
(P-2026-10-10-50). Das ZIP lädt danach hole() auf demselben Weg:
urllib, wenn es kann, sonst Qt, sonst curl.

Was dabei passiert:

1. Der neueste Stand kommt als ZIP von GitHub in den Addon-Ordner von FreeCAD
   (`Mod/freecad-cam-addon`) – auf jedem Betriebssystem der richtige, ohne Git
   und ohne GitHub Desktop.
2. Ist das Addon schon so installiert, ersetzt dieselbe Zeile es durch den
   neuesten Stand. Ein Git-Klon (etwa von GitHub Desktop) bleibt unberührt,
   der aktualisiert sich selbst.
3. Das Addon wird im Addon-Manager als eigenes Repository eingetragen. Dann
   zeigt der Addon-Manager neue Versionen an und kann es wieder entfernen.

Funktioniert nur, solange das Repository öffentlich ist: Ein privates gibt
GitHub nur angemeldet heraus.

Die Datei läuft, bevor das Addon da ist. Deshalb steht alles in ihr selbst,
und ihre wenigen Texte stehen zweisprachig im Code statt in translations/ –
die Sprachwahl des Addons gibt es zu diesem Zeitpunkt noch nicht.
"""

import io
import os
import shutil
import subprocess
import tempfile
import threading
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass

import FreeCAD

REPOSITORY = "https://github.com/manuelhofer/freecad-cam-addon"
ZWEIG = "main"
ZIP_ADRESSE = f"{REPOSITORY}/archive/refs/heads/{ZWEIG}.zip"
# Der Ordner heißt wie das Repository: Daran erkennt der Addon-Manager, dass
# das Addon installiert ist.
ORDNER_NAME = "freecad-cam-addon"
# Dort speichert der Addon-Manager seine eigenen Repositories („Custom
# repositories“ in seinen Einstellungen): je Zeile „Adresse Zweig“.
ADDON_MANAGER = "User parameter:BaseApp/Preferences/Addons"
ZEITLIMIT_S = 60
# Kann Python kein https und Qt nicht einspringen – etwa ohne Oberfläche.
OHNE_HTTPS = (
    "Pythons ssl fehlt, und der Addon-Manager kann nicht laden"
    " / Python's ssl is missing and the Addon Manager cannot download"
)

# Mögliche Ergebnisse von installiere().
NEU = "neu"
AKTUALISIERT = "aktualisiert"
GIT_KLON = "git_klon"  # mit Git installiert: nichts angefasst

TITEL = "CAM-Addon"


@dataclass
class Ergebnis:
    """Ergebnis von `installiere()`."""

    status: str  # NEU, AKTUALISIERT oder GIT_KLON
    ordner: str
    version: str = "?"
    version_vorher: str = ""


def mod_ordner():
    """Der Ordner, in dem FreeCAD Addons sucht – je Betriebssystem ein anderer."""
    return os.path.join(FreeCAD.getUserAppDataDir(), "Mod")


def installiere(adresse=ZIP_ADRESSE, mod=None, parameter=ADDON_MANAGER, ziel=None):
    """Holt das Addon von `adresse` nach `mod`/freecad-cam-addon und trägt es im Addon-Manager ein.

    `ziel` statt `mod`: genau dieser Ordner – so aktualisiert sich das Addon
    selbst (aktualisierung.py), auch wenn sein Ordner anders heißt.

    Wirft OSError (auch urllib.error.URLError) oder ValueError, wenn der
    Download (hole()) oder das Archiv nicht taugt – eine vorhandene Installation bleibt
    dann, wie sie war.
    """
    if ziel is None:
        mod = mod or mod_ordner()
        ziel = os.path.join(mod, ORDNER_NAME)
    else:
        mod = os.path.dirname(os.path.abspath(ziel))
    if os.path.exists(os.path.join(ziel, ".git")):
        trage_in_addon_manager_ein(parameter)
        return Ergebnis(GIT_KLON, ziel, _version(ziel))

    daten = hole(adresse)
    vorher = _version(ziel) if os.path.isdir(ziel) else ""
    os.makedirs(mod, exist_ok=True)
    # Ausgepackt wird außerhalb von Mod/: Bliebe ein halber Ordner liegen,
    # lüde FreeCAD ihn beim nächsten Start als zweites Addon.
    arbeit = tempfile.mkdtemp(prefix="camaddon-")
    try:
        neu = _entpacke(daten, arbeit)
        _ersetze(ziel, neu, arbeit)
    finally:
        shutil.rmtree(arbeit, ignore_errors=True)
    trage_in_addon_manager_ein(parameter)
    return Ergebnis(AKTUALISIERT if vorher else NEU, ziel, _version(ziel), vorher)


def hole(adresse, zeitlimit_s=ZEITLIMIT_S):
    """Lädt `adresse` und gibt die Bytes zurück; wirft OSError, wenn es nicht geht.

    Zuerst mit Pythons urllib. Manchem FreeCAD fehlt aber Pythons ssl – dann
    kann urllib kein https („unknown url type: https“) –, oder es kennt die
    Zertifikate nicht. Dann lädt Qt, über den Netzzugang des Addon-Managers
    von FreeCAD (mit dessen Proxy-Einstellungen), und lädt auch Qt nicht, das
    curl des Systems (B-017, P-2026-10-10-38).
    """
    if _nur_ueber_qt(adresse):
        return _hole_ohne_python(adresse, zeitlimit_s)
    try:
        with urllib.request.urlopen(adresse, timeout=zeitlimit_s) as antwort:
            return antwort.read()
    except urllib.error.URLError as fehler:
        if not (adresse.lower().startswith("https:") and _ist_ssl_fehler(fehler.reason)):
            raise
        try:
            return _hole_ohne_python(adresse, zeitlimit_s)
        except OSError:
            raise fehler from None  # die eigentliche Ursache: das Zertifikat


def _hole_ohne_python(adresse, zeitlimit_s):
    """Lädt, wenn urllib es nicht kann: erst über Qt, dann mit curl; wirft OSError mit beiden
    Gründen. In FreeCAD 26.3.0RC1 unter Windows fehlen Pythons ssl und Qts Download zugleich
    (Manuel, 2026-10-10) – curl bringt Windows 10/11 mit."""
    try:
        return _hole_mit_qt(adresse, zeitlimit_s)
    except OSError as qt_grund:
        try:
            return _hole_mit_curl(adresse, zeitlimit_s)
        except OSError as curl_grund:
            raise OSError(f"{qt_grund}; {curl_grund}") from None


def _hole_mit_curl(adresse, zeitlimit_s):
    """Lädt mit dem curl des Systems – Windows 10/11, macOS und die meisten Linux haben es; es
    prüft die Zertifikate selbst, unter Windows mit denen des Systems. Ausnahme von „keine
    Shell-Aufrufe“: nur hier, nur als letzter Weg (Arbeitsregeln, Abschnitt 7)."""
    curl = shutil.which("curl")
    if curl is None:
        raise OSError("curl fehlt / curl is missing")
    try:
        lauf = subprocess.run(
            [curl, "--silent", "--show-error", "--fail", "--location"]
            + ["--max-time", str(int(zeitlimit_s)), adresse],
            capture_output=True,
            timeout=zeitlimit_s + 10,
            stdin=subprocess.DEVNULL,
            # Unter Windows sonst bei jedem Aufruf kurz ein schwarzes Konsolenfenster.
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        raise OSError(f"{adresse}: curl – Zeitlimit / timed out") from None
    if lauf.returncode != 0:
        grund = lauf.stderr.decode("utf-8", "replace").strip()
        raise OSError(f"{adresse}: curl {lauf.returncode} ({grund})")
    return lauf.stdout


def netz_vorbereiten():
    """Legt den Netzzugang des Addon-Managers an, falls hole() ihn braucht. Im Hauptthread
    aufzurufen, bevor ein anderer Thread hole() ruft: Qt lädt nur in dem Thread, in dem der
    Netzzugang entstand, und nur dort läuft die Ereignisschleife. Ohne Oberfläche: nichts."""
    if not FreeCAD.GuiUp:
        return
    try:
        import NetworkManager
    except ImportError:
        return
    NetworkManager.InitializeNetworkManager()


def _nur_ueber_qt(adresse):
    """https, aber urllib kann es nicht: Pythons ssl fehlt – daran hängt http.client."""
    import http.client

    return adresse.lower().startswith("https:") and not hasattr(http.client, "HTTPSConnection")


def _ist_ssl_fehler(grund):
    """Scheiterte urllib an TLS – etwa an einem Zertifikat, das Python nicht kennt?"""
    try:
        import ssl
    except ImportError:
        return False
    return isinstance(grund, ssl.SSLError)


def _hole_mit_qt(adresse, zeitlimit_s):
    """Lädt über den Netzzugang des Addon-Managers (NetworkManager, Qt) – den braucht es
    mit Oberfläche, im Hauptthread angelegt (netz_vorbereiten())."""
    try:
        import NetworkManager
        from PySide import QtCore
    except ImportError as grund:
        raise OSError(f"{OHNE_HTTPS} ({grund})") from None
    if QtCore.QCoreApplication.instance() is None:
        raise OSError(OHNE_HTTPS)
    if NetworkManager.AM_NETWORK_MANAGER is None:
        if threading.current_thread() is not threading.main_thread():
            raise OSError(OHNE_HTTPS)  # in diesem Thread lüde er nie
        NetworkManager.InitializeNetworkManager()
    netz = NetworkManager.AM_NETWORK_MANAGER
    zeit_ms = int(zeitlimit_s * 1000)
    try:
        daten = netz.blocking_get(adresse, zeit_ms, disable_cache=True)
    except TypeError:  # Addon-Manager vor FreeCAD 1.1: ohne disable_cache
        daten = netz.blocking_get(adresse, zeit_ms)
    if daten is None:  # der Addon-Manager nennt den Grund in der Konsole
        raise OSError(f"{adresse}: über Qt nicht zu laden / could not be loaded via Qt")
    return bytes(daten.data()) if hasattr(daten, "data") else bytes(daten)


def _entpacke(daten, arbeit):
    """Packt das ZIP von GitHub aus; gibt den Ordner zurück, in dem package.xml liegt."""
    try:
        archiv = zipfile.ZipFile(io.BytesIO(daten))
    except zipfile.BadZipFile as fehler:
        raise ValueError(f"kein ZIP-Archiv ({fehler})") from None
    with archiv:
        # GitHub packt alles in einen Ordner „<repository>-<zweig>/“.
        oben = {name.split("/", 1)[0] for name in archiv.namelist()}
        if len(oben) != 1 or f"{next(iter(oben))}/package.xml" not in archiv.namelist():
            raise ValueError("das Archiv enthält kein FreeCAD-Addon (package.xml fehlt)")
        # extractall hält Einträge wie „../x“ oder „/x“ im Zielordner fest.
        archiv.extractall(arbeit)
    return os.path.join(arbeit, next(iter(oben)))


def _ersetze(ziel, neu, arbeit):
    """Setzt `neu` an die Stelle von `ziel`; misslingt das, kommt der alte Stand zurück."""
    if not os.path.exists(ziel):
        shutil.move(neu, ziel)
        return
    alt = os.path.join(arbeit, "vorher")
    shutil.move(ziel, alt)
    try:
        shutil.move(neu, ziel)
    except OSError:
        if os.path.exists(ziel):
            shutil.rmtree(ziel, ignore_errors=True)
        shutil.move(alt, ziel)
        raise


def _version(ordner):
    try:
        wurzel = ET.parse(os.path.join(ordner, "package.xml")).getroot()
        return wurzel.find("{*}version").text.strip()
    except (OSError, ET.ParseError, AttributeError):
        return "?"


def trage_in_addon_manager_ein(parameter=ADDON_MANAGER):
    """Trägt das Repository im Addon-Manager ein, falls es dort noch fehlt; True, wenn neu."""
    gruppe = FreeCAD.ParamGet(parameter)
    zeilen = [z for z in gruppe.GetString("CustomRepositories", "").split("\n") if z.strip()]
    if any(_gleiche_adresse(zeile.split()[0], REPOSITORY) for zeile in zeilen):
        return False
    zeilen.append(f"{REPOSITORY} {ZWEIG}")
    # Mit Zeilenende wie der Addon-Manager selbst, wenn er die Liste speichert.
    gruppe.SetString("CustomRepositories", "".join(z + "\n" for z in zeilen))
    return True


def _gleiche_adresse(a, b):
    def kern(adresse):
        adresse = adresse.strip().rstrip("/").lower()
        return adresse[: -len(".git")] if adresse.endswith(".git") else adresse

    return kern(a) == kern(b)


def text(ergebnis):
    """Die Rückmeldung an den Benutzer, deutsch und englisch."""
    if ergebnis.status == GIT_KLON:
        return (
            f"Das CAM-Addon ist hier schon mit Git installiert (z. B. GitHub Desktop)"
            f" und aktualisiert sich selbst. Nichts geändert.\n{ergebnis.ordner}\n\n"
            f"The CAM Addon is already installed with Git (e.g. GitHub Desktop)"
            f" and updates itself. Nothing changed."
        )
    if ergebnis.status == AKTUALISIERT:
        return (
            f"CAM-Addon aktualisiert: {ergebnis.version_vorher} → {ergebnis.version}.\n"
            f"Bitte FreeCAD neu starten.\n\n"
            f"CAM Addon updated: {ergebnis.version_vorher} → {ergebnis.version}.\n"
            f"Please restart FreeCAD."
        )
    return (
        f"CAM-Addon {ergebnis.version} ist installiert.\nBitte FreeCAD neu starten.\n\n"
        f"CAM Addon {ergebnis.version} is installed.\nPlease restart FreeCAD."
    )


def fehlertext(fehler):
    """Die Rückmeldung, wenn es nicht geklappt hat, deutsch und englisch."""
    return (
        f"Das CAM-Addon ließ sich nicht installieren:\n{fehler}\n\n"
        f"Dann bitte von Hand: auf GitHub Code → Download ZIP, weiter wie im README unter"
        f" „Geht keine der drei Zeilen“.\n\n"
        f"The CAM Addon could not be installed:\n{fehler}\n\n"
        f"Then please install by hand: on GitHub Code → Download ZIP, then as described in the"
        f" README under „Geht keine der drei Zeilen“."
    )


def _melde(meldung, fehler=False):
    """Zeigt die Meldung in einem Fenster, ohne Oberfläche in der Konsole."""
    (FreeCAD.Console.PrintError if fehler else FreeCAD.Console.PrintMessage)(meldung + "\n")
    if not FreeCAD.GuiUp:
        return
    import FreeCADGui
    from PySide import QtGui

    zeige = QtGui.QMessageBox.warning if fehler else QtGui.QMessageBox.information
    zeige(FreeCADGui.getMainWindow(), TITEL, meldung)


def starte():
    """Was die Zeile aus der Python-Konsole ausführt."""
    try:
        ergebnis = installiere()
    except (OSError, ValueError) as fehler:
        _melde(fehlertext(fehler), fehler=True)
        return None
    _melde(text(ergebnis))
    return ergebnis


# In der Python-Konsole und als Makro heißt das Modul „__main__“; beim Import
# (etwa in tests/test_installieren.py) passiert nichts.
if __name__ == "__main__":
    starte()
