# Prüft installieren.py ohne Netz: „GitHub“ ist ein ZIP-Archiv im Temp-Ordner,
# gelesen über eine file://-Adresse; der Addon-Manager ist eine eigene
# Parametergruppe, damit die echten Einstellungen unberührt bleiben.
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import FreeCAD

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "installieren", os.path.join(ADDON, "installieren.py")
)
inst = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inst)  # als Modul geladen: installiert dabei nichts

PARAMETER = "User parameter:BaseApp/Preferences/Mod/CamAddonTest/Addons"

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def github_zip(basis, version, dateien=None, name="stand.zip", mit_package=True):
    """Ein Archiv wie das von GitHub: alles in „freecad-cam-addon-main/“."""
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w") as archiv:
        archiv.writestr("freecad-cam-addon-main/", "")
        if mit_package:
            archiv.writestr(
                "freecad-cam-addon-main/package.xml",
                f'<package format="1" xmlns="https://wiki.freecad.org/Package_Metadata">'
                f"<version>{version}</version></package>",
            )
        for datei, inhalt in (dateien or {}).items():
            archiv.writestr(f"freecad-cam-addon-main/{datei}", inhalt)
    pfad = Path(basis, name)
    pfad.write_bytes(puffer.getvalue())
    return pfad.as_uri()


def repositories():
    return FreeCAD.ParamGet(PARAMETER).GetString("CustomRepositories", "")


basis = tempfile.mkdtemp()
mod = os.path.join(basis, "Mod")
ziel = os.path.join(mod, "freecad-cam-addon")

# Frisch installieren: Mod/ gibt es noch nicht.
e = inst.installiere(
    github_zip(basis, "1.0.0", {"InitGui.py": "# alt", "nur_alt.py": ""}), mod, PARAMETER
)
pruefe(e.status == inst.NEU and e.version == "1.0.0", f"frisch: {e}")
pruefe(Path(ziel, "InitGui.py").read_text() == "# alt", "frisch: InitGui.py fehlt")
pruefe(
    repositories() == "https://github.com/manuelhofer/freecad-cam-addon main\n",
    f"frisch: im Addon-Manager {repositories()!r}",
)
pruefe("1.0.0" in inst.text(e) and "neu starten" in inst.text(e), inst.text(e))

# Dieselbe Zeile noch einmal: ersetzt den Ordner ganz, trägt nicht doppelt ein.
e = inst.installiere(github_zip(basis, "1.1.0", {"InitGui.py": "# neu"}), mod, PARAMETER)
pruefe(
    e.status == inst.AKTUALISIERT and e.version == "1.1.0" and e.version_vorher == "1.0.0",
    f"aktualisiert: {e}",
)
pruefe(Path(ziel, "InitGui.py").read_text() == "# neu", "aktualisiert: alter Inhalt")
pruefe(not Path(ziel, "nur_alt.py").exists(), "aktualisiert: alte Datei blieb liegen")
pruefe(repositories().count("freecad-cam-addon") == 1, f"doppelt: {repositories()!r}")
pruefe(sorted(os.listdir(mod)) == ["freecad-cam-addon"], f"Reste in Mod/: {os.listdir(mod)}")

# Kaputter Download oder falsches Archiv: Die Installation bleibt, wie sie war.
for adresse, grund in (
    (Path(basis, "fehlt.zip").as_uri(), "fehlende Datei"),
    (github_zip(basis, "2.0.0", name="ohne.zip", mit_package=False), "ohne package.xml"),
):
    try:
        inst.installiere(adresse, mod, PARAMETER)
        fehler.append(f"{grund}: kein Fehler gemeldet")
    except (OSError, ValueError) as f:
        pruefe("privat" in inst.fehlertext(f), f"{grund}: Fehlertext {inst.fehlertext(f)!r}")
    pruefe(Path(ziel, "InitGui.py").read_text() == "# neu", f"{grund}: Installation verändert")
kein_zip = Path(basis, "kein.zip")
kein_zip.write_text("kein Archiv")
try:
    inst.installiere(kein_zip.as_uri(), mod, PARAMETER)
    fehler.append("kein ZIP: kein Fehler gemeldet")
except ValueError:
    pass

# Ein Git-Klon (GitHub Desktop) bleibt unberührt.
os.makedirs(os.path.join(ziel, ".git"))
e = inst.installiere(github_zip(basis, "3.0.0", {"InitGui.py": "# drei"}), mod, PARAMETER)
pruefe(e.status == inst.GIT_KLON, f"Git-Klon: {e}")
pruefe(Path(ziel, "InitGui.py").read_text() == "# neu", "Git-Klon wurde überschrieben")

# Andere eigene Repositories bleiben; dieselbe Adresse mit „/“ oder „.git“ zählt als da.
FreeCAD.ParamGet(PARAMETER).SetString(
    "CustomRepositories",
    "https://example.org/anderes main\nhttps://github.com/manuelhofer/freecad-cam-addon.git/ main\n",
)
pruefe(not inst.trage_in_addon_manager_ein(PARAMETER), "Adresse mit .git/ nicht erkannt")
FreeCAD.ParamGet(PARAMETER).SetString("CustomRepositories", "https://example.org/anderes main")
pruefe(inst.trage_in_addon_manager_ein(PARAMETER), "fehlender Eintrag nicht ergänzt")
pruefe(
    repositories()
    == "https://example.org/anderes main\nhttps://github.com/manuelhofer/freecad-cam-addon main\n",
    f"andere Repositories: {repositories()!r}",
)

# Die drei Zeilen aus dem README – curl, Qt, urllib – laden genau diese Datei, und der Kopf von
# installieren.py nennt dieselben (P-2026-10-10-38).
readme = Path(ADDON, "README.md").read_text("utf-8")
kopf = Path(ADDON, "installieren.py").read_text("utf-8")
for zeile in (
    'exec(s.run(["curl", "-sSfL", "https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py"], capture_output=True, check=True).stdout)',
    'exec(n.AM_NETWORK_MANAGER.blocking_get("https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py").data())',
    'exec(u.urlopen("https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py").read())',
):
    pruefe(zeile in readme, f"README: Installationszeile fehlt oder weicht ab: {zeile[:40]}")
    pruefe(zeile in kopf, f"installieren.py: Zeile weicht ab: {zeile[:40]}")


# --- Ohne https in Python: über Qt (P-2026-09-30-33) -----------------------------------------
# Manchem FreeCAD fehlt Pythons ssl; urllib meldet dann „unknown url type: https“ (Manuel,
# 2026-09-30). hole() lädt dann über den Netzzugang des Addon-Managers (Qt). „GitHub“ ist hier
# ein kleiner HTTP-Server auf 127.0.0.1.
import http.client  # noqa: E402
import http.server  # noqa: E402
import ssl  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import urllib.error  # noqa: E402

# Die Entscheidung: nur https, und nur, wenn http.client ohne ssl kein HTTPSConnection hat.
pruefe(not inst._nur_ueber_qt("https://github.com/x"), "mit ssl: https über Qt")
mit_ssl = http.client.HTTPSConnection
del http.client.HTTPSConnection
try:
    pruefe(inst._nur_ueber_qt("https://github.com/x"), "ohne ssl: https nicht über Qt")
    pruefe(not inst._nur_ueber_qt(Path(basis, "x").as_uri()), "ohne ssl: file:// über Qt")
finally:
    http.client.HTTPSConnection = mit_ssl

# Kennt urllib das Zertifikat nicht, springt Qt ein, kann Qt es auch nicht, curl; können beide
# nicht, bleibt der Fehler von urllib. Andere Fehler (kein Netz) gehen nicht an Qt.
urlopen, hole_mit_qt, hole_mit_curl = (
    inst.urllib.request.urlopen,
    inst._hole_mit_qt,
    inst._hole_mit_curl,
)
geholt = []


def ohne_zertifikat(adresse, timeout):
    raise urllib.error.URLError(ssl.SSLCertVerificationError("certificate verify failed"))


def qt_laedt(adresse, zeitlimit_s):
    geholt.append(adresse)
    return b"qt"


def qt_scheitert(adresse, zeitlimit_s):
    raise OSError("auch Qt nicht")


def ohne_netz(adresse, timeout):
    raise urllib.error.URLError("timed out")


def curl_laedt(adresse, zeitlimit_s):
    return b"curl"


def curl_scheitert(adresse, zeitlimit_s):
    raise OSError("curl auch nicht")


try:
    inst.urllib.request.urlopen = ohne_zertifikat
    inst._hole_mit_qt = qt_laedt
    inst._hole_mit_curl = curl_scheitert
    pruefe(inst.hole("https://github.com/x") == b"qt", "Zertifikat: Qt springt nicht ein")
    inst._hole_mit_qt = qt_scheitert
    try:
        inst.hole("https://github.com/x")
        fehler.append("Zertifikat, Qt und curl scheitern: kein Fehler")
    except urllib.error.URLError as f:
        pruefe("certificate" in str(f), f"Zertifikat, Qt und curl scheitern: {f}")
    inst._hole_mit_curl = curl_laedt
    pruefe(inst.hole("https://github.com/x") == b"curl", "Zertifikat, Qt scheitert: kein curl")
    # Ohne Pythons ssl und ohne Qt – FreeCAD 26.3.0RC1 unter Windows (B-017): curl.
    nur_ueber_qt = inst._nur_ueber_qt
    inst._nur_ueber_qt = lambda adresse: True
    try:
        pruefe(inst.hole("https://github.com/x") == b"curl", "ohne ssl und Qt: kein curl")
        inst._hole_mit_curl = curl_scheitert
        try:
            inst.hole("https://github.com/x")
            fehler.append("ohne ssl, Qt und curl: kein Fehler")
        except OSError as f:
            pruefe("Qt" in str(f) and "curl" in str(f), f"ohne ssl, Qt und curl: {f}")
    finally:
        inst._nur_ueber_qt = nur_ueber_qt
    inst._hole_mit_curl = curl_scheitert
    inst.urllib.request.urlopen = ohne_netz
    inst._hole_mit_qt = qt_laedt
    geholt.clear()
    try:
        inst.hole("https://github.com/x")
        fehler.append("kein Netz: kein Fehler")
    except urllib.error.URLError:
        pruefe(not geholt, "kein Netz: an Qt gegeben")
finally:
    inst.urllib.request.urlopen, inst._hole_mit_qt = urlopen, hole_mit_qt
    inst._hole_mit_curl = hole_mit_curl

# Über Qt wirklich laden – den Netzzugang des Addon-Managers gibt es nur mit einer
# Qt-Anwendung; FreeCADCmd hat keine, also legt die Prüfung eine an.
github_zip(basis, "4.0.0", {"InitGui.py": "# vier"}, name="qt.zip")
dateien = {"/stand.zip": Path(basis, "qt.zip").read_bytes()}


class Github(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 – so heißt es in http.server
        if self.path == "/umleitung":  # wie GitHub: das ZIP liegt woanders, absolut angegeben
            self.send_response(302)
            self.send_header("Location", f"{github}/stand.zip")
            self.end_headers()
            return
        inhalt = dateien.get(self.path)
        if inhalt is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(inhalt)))
        self.end_headers()
        self.wfile.write(inhalt)

    def log_message(self, *argumente):  # keine Zeile je Anfrage in der Ausgabe
        pass


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Github)
threading.Thread(target=server.serve_forever, daemon=True).start()
github = f"http://127.0.0.1:{server.server_address[1]}"
# curl nähme sonst einen Proxy aus der Umgebung – auch für 127.0.0.1.
for name in ("no_proxy", "NO_PROXY"):
    os.environ[name] = ",".join(filter(None, [os.environ.get(name, ""), "127.0.0.1"]))

# --- curl, der letzte Weg (P-2026-10-10-38) --------------------------------------------------
# Mit dem echten curl vom selben „GitHub“: Umleitung wie bei GitHub, 404; und ohne curl.
if shutil.which("curl"):
    pruefe(
        inst._hole_mit_curl(f"{github}/umleitung", 10) == dateien["/stand.zip"],
        "curl: Umleitung nicht gefolgt",
    )
    try:
        inst._hole_mit_curl(f"{github}/fehlt.zip", 10)
        fehler.append("curl, 404: kein Fehler")
    except OSError as f:
        pruefe("curl" in str(f), f"curl, 404: {f}")
else:
    print("Hinweis: kein curl auf diesem Rechner – der echte Aufruf ist nicht geprüft")
which = shutil.which
shutil.which = lambda name: None
try:
    inst._hole_mit_curl(f"{github}/stand.zip", 10)
    fehler.append("ohne curl: kein Fehler")
except OSError as f:
    pruefe("curl fehlt" in str(f), f"ohne curl: {f}")
finally:
    shutil.which = which

from PySide import QtCore  # noqa: E402

app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
try:
    import NetworkManager
except ImportError:  # FreeCADCmd nimmt den Addon-Manager nicht immer in den Suchpfad
    sys.path.append(os.path.join(FreeCAD.getHomePath(), "Mod", "AddonManager"))
    import NetworkManager
# Der Addon-Manager nähme sonst den Proxy des Systems – auch für 127.0.0.1.
am = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Addons")
proxy_vorher = am.GetString("proxy_type", "")
migriert_vorher = am.GetBool("proxy_settings_migrated_2025", False)
am.SetString("proxy_type", "none")
am.SetBool("proxy_settings_migrated_2025", True)
nur_ueber_qt = inst._nur_ueber_qt
inst._nur_ueber_qt = lambda adresse: True
try:
    mod_qt = os.path.join(basis, "ModQt")
    e = inst.installiere(f"{github}/umleitung", mod_qt, PARAMETER)
    pruefe(e.status == inst.NEU and e.version == "4.0.0", f"über Qt: {e}")
    try:
        inst.hole(f"{github}/fehlt.zip", 10)
        fehler.append("über Qt, 404: kein Fehler")
    except OSError as f:
        pruefe("Qt" in str(f), f"über Qt, 404: {f}")
    # B-017 (FreeCAD 26.3.0RC1 unter Windows): weder Pythons ssl noch Qt – curl installiert.
    if shutil.which("curl"):
        inst._hole_mit_qt = qt_scheitert
        try:
            e = inst.installiere(f"{github}/umleitung", os.path.join(basis, "ModCurl"), PARAMETER)
            pruefe(e.status == inst.NEU and e.version == "4.0.0", f"ohne ssl und Qt: {e}")
        finally:
            inst._hole_mit_qt = hole_mit_qt

    # Im Such-Thread (gui_aktualisierung): Der Netzzugang entstand im Hauptthread, und der
    # arbeitet derweil Ereignisse ab – wie FreeCADs Oberfläche.
    def im_thread(ergebnis):
        try:
            ergebnis.append(inst.hole(f"{github}/stand.zip", 10))
        except OSError as f:
            ergebnis.append(f)

    def warte(ergebnis):
        faden = threading.Thread(target=im_thread, args=(ergebnis,), daemon=True)
        faden.start()
        ende = time.monotonic() + 30
        while faden.is_alive() and time.monotonic() < ende:
            app.processEvents()
            time.sleep(0.01)
        return not faden.is_alive()

    ergebnis = []
    pruefe(warte(ergebnis), "im Such-Thread: hängt")
    pruefe(ergebnis == [dateien["/stand.zip"]], f"im Such-Thread: {ergebnis[:1]!r:.80}")
    # Ohne Netzzugang aus dem Hauptthread hinge der Such-Thread über Qt: Er meldet einen Fehler
    # – ohne curl – oder lädt mit curl (so sucht das Addon in B-017 nach Updates).
    angelegt = NetworkManager.AM_NETWORK_MANAGER
    NetworkManager.AM_NETWORK_MANAGER = None
    try:
        inst._hole_mit_curl = curl_scheitert
        ergebnis = []
        pruefe(warte(ergebnis), "ohne Netzzugang: hängt")
        pruefe(
            len(ergebnis) == 1 and isinstance(ergebnis[0], OSError),
            f"ohne Netzzugang: {ergebnis[:1]!r:.80}",
        )
        inst._hole_mit_curl = hole_mit_curl
        if shutil.which("curl"):
            ergebnis = []
            pruefe(warte(ergebnis), "ohne Netzzugang, mit curl: hängt")
            pruefe(
                ergebnis == [dateien["/stand.zip"]],
                f"ohne Netzzugang, mit curl: {ergebnis[:1]!r:.80}",
            )
    finally:
        NetworkManager.AM_NETWORK_MANAGER = angelegt
        inst._hole_mit_curl = hole_mit_curl
    inst.netz_vorbereiten()  # ohne Oberfläche: nichts
finally:
    inst._nur_ueber_qt = nur_ueber_qt
    server.shutdown()
    if proxy_vorher:
        am.SetString("proxy_type", proxy_vorher)
    else:
        am.RemString("proxy_type")
    if migriert_vorher:
        am.SetBool("proxy_settings_migrated_2025", True)
    else:
        am.RemBool("proxy_settings_migrated_2025")

FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod").RemGroup("CamAddonTest")

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
