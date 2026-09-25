# SPDX-License-Identifier: LGPL-2.1-or-later
"""Installiert oder aktualisiert das CAM-Addon mit einer Zeile (P-2026-09-25-43).

In FreeCAD **Ansicht → Fenster → Python-Konsole** öffnen, diese Zeile
hineinkopieren, Enter, danach FreeCAD neu starten:

    import urllib.request as u; exec(u.urlopen("https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py").read())

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
import tempfile
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


def installiere(adresse=ZIP_ADRESSE, mod=None, parameter=ADDON_MANAGER):
    """Holt das Addon von `adresse` nach `mod`/freecad-cam-addon und trägt es im Addon-Manager ein.

    Wirft OSError (auch urllib.error.URLError) oder ValueError, wenn der
    Download oder das Archiv nicht taugt – eine vorhandene Installation bleibt
    dann, wie sie war.
    """
    mod = mod or mod_ordner()
    ziel = os.path.join(mod, ORDNER_NAME)
    if os.path.exists(os.path.join(ziel, ".git")):
        trage_in_addon_manager_ein(parameter)
        return Ergebnis(GIT_KLON, ziel, _version(ziel))

    with urllib.request.urlopen(adresse, timeout=ZEITLIMIT_S) as antwort:
        daten = antwort.read()
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
        f"Ist das Repository noch privat? Dann bitte nach der Anleitung mit"
        f" GitHub Desktop installieren (README).\n\n"
        f"The CAM Addon could not be installed:\n{fehler}\n\n"
        f"Is the repository still private? Then please follow the"
        f" GitHub Desktop instructions (README)."
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
