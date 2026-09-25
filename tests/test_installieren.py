# Prüft installieren.py ohne Netz: „GitHub“ ist ein ZIP-Archiv im Temp-Ordner,
# gelesen über eine file://-Adresse; der Addon-Manager ist eine eigene
# Parametergruppe, damit die echten Einstellungen unberührt bleiben.
import importlib.util
import io
import os
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

# Die Zeile aus dem README lädt genau diese Datei.
readme = Path(ADDON, "README.md").read_text("utf-8")
zeile = 'exec(u.urlopen("https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py").read())'
pruefe(zeile in readme, "README: Installationszeile fehlt oder weicht ab")
pruefe(
    zeile in Path(ADDON, "installieren.py").read_text("utf-8"), "installieren.py: Zeile weicht ab"
)

FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod").RemGroup("CamAddonTest")

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
