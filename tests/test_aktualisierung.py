# Prüft die Update-Suche per Git mit echten Repositories in einem Temp-Ordner:
# „GitHub“ ist ein nacktes Repo, der Addon-Ordner ein Klon davon.
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import aktualisierung as a
from camaddon import version_aus_xml

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def git(*argumente, ordner=None):
    befehl = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.org"]
    if ordner:
        befehl += ["-C", ordner]
    subprocess.run(befehl + list(argumente), check=True, capture_output=True)


def neue_version(arbeit, version):
    """Setzt in `arbeit` eine neue Version und schiebt sie nach „GitHub“."""
    pfad = Path(arbeit, "package.xml")
    text = re.sub(
        r"<version>[^<]+</version>", f"<version>{version}</version>", pfad.read_text("utf-8")
    )
    pfad.write_text(text, "utf-8")
    git("commit", "-q", "-am", f"Version {version}", ordner=arbeit)
    git("push", "-q", "origin", "HEAD:main", ordner=arbeit)


basis = tempfile.mkdtemp()
fern = os.path.join(basis, "github.git")
installiert = os.path.join(basis, "Mod", "freecad-cam-addon")
arbeit = os.path.join(basis, "arbeit")
git("clone", "-q", "--bare", "--branch", "main", ADDON, fern)
git("clone", "-q", fern, installiert)
git("clone", "-q", fern, arbeit)
jetzt = version_aus_xml(Path(installiert, "package.xml").read_text("utf-8"))

e = a.pruefe(installiert)
pruefe(e.status == a.AKTUELL and e.version_jetzt == jetzt, f"frisch geklont: {e}")

neue_version(arbeit, "9.9.0")
e = a.pruefe(installiert)
pruefe(
    e.status == a.NEU and e.version_neu == "9.9.0" and e.version_jetzt == jetzt,
    f"nach neuer Version: {e}",
)

a.aktualisiere(installiert)
e = a.pruefe(installiert)
pruefe(e.status == a.AKTUELL and e.version_jetzt == "9.9.0", f"nach dem Aktualisieren: {e}")

# Neuer Stand ohne neue Version (Tests, Doku, Aufräumen): kein Hinweis, sonst
# hieße er „neue Version 9.9.0, installiert ist 9.9.0“ (B-003).
with open(os.path.join(arbeit, "docs", "STATUS_SNAPSHOT.md"), "a", encoding="utf-8") as datei:
    datei.write("\nnur Doku\n")
git("commit", "-q", "-am", "nur Doku", ordner=arbeit)
git("push", "-q", "origin", "HEAD:main", ordner=arbeit)
e = a.pruefe(installiert)
pruefe(e.status == a.AKTUELL and e.version_jetzt == "9.9.0", f"neuer Stand, alte Version: {e}")

# Versionen werden Zahl für Zahl verglichen, nicht als Text.
pruefe(a.ist_neuer("0.3.10", "0.3.9"), "0.3.10 gilt nicht als neuer als 0.3.9")
pruefe(not a.ist_neuer("0.3.3", "0.3.3"), "gleiche Version gilt als neuer")
pruefe(not a.ist_neuer("0.3.2", "0.3.3"), "ältere Version gilt als neuer")
pruefe(a.ist_neuer("0.4.0", "?"), "unlesbare Version: Update wird verschwiegen")

# Eigene Änderung im Addon-Ordner: nicht blind überschreiben.
with open(os.path.join(installiert, "README.md"), "a", encoding="utf-8") as datei:
    datei.write("\nlokal geändert\n")
neue_version(arbeit, "9.9.1")
e = a.pruefe(installiert)
pruefe(e.status == a.LOKAL_GEAENDERT and e.version_neu == "9.9.1", f"mit eigener Änderung: {e}")

# Kein Git-Ordner (z. B. als ZIP installiert) und kein Git auf dem Rechner.
pruefe(a.pruefe(tempfile.mkdtemp()).status == a.KEIN_GIT_ORDNER, "ZIP-Installation nicht erkannt")
original = a.git_programm
a.git_programm = lambda: None
pruefe(a.pruefe(installiert).status == a.KEIN_GIT, "fehlendes Git nicht erkannt")
a.git_programm = original

# GitHub nicht erreichbar: Fehler statt Hängen oder Absturz.
shutil.rmtree(fern)
e = a.pruefe(installiert)
pruefe(e.status == a.FEHLER and e.meldung, f"ohne erreichbares Repo: {e}")

shutil.rmtree(basis)
assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
