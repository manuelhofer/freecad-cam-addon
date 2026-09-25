# Update-Hinweis: Auf „GitHub“ (nacktes Repo im Temp-Ordner) liegt eine neue
# Version; die Suche im Hintergrund findet sie, der Hinweis erscheint, „Jetzt
# aktualisieren“ holt sie. Dazu die Gruppe „Updates“ in den Einstellungen.
import os
import re
import subprocess
import tempfile
from pathlib import Path

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def git(*argumente, ordner=None):
    befehl = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.org"]
    if ordner:
        befehl += ["-C", ordner]
    subprocess.run(befehl + list(argumente), check=True, capture_output=True)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.accept()
    yield 300

    from camaddon import aktualisierung as a
    from camaddon import gui_aktualisierung as ga
    from camaddon import gui_sprachwahl

    basis = tempfile.mkdtemp()
    fern, installiert, arbeit = (
        os.path.join(basis, n) for n in ("github.git", "installiert", "arbeit")
    )
    git("clone", "-q", "--bare", "--branch", "main", ADDON, fern)
    git("clone", "-q", fern, installiert)
    git("clone", "-q", fern, arbeit)
    pfad = Path(arbeit, "package.xml")
    text = re.sub(r"<version>[^<]+</version>", "<version>9.9.0</version>", pfad.read_text("utf-8"))
    pfad.write_text(text, "utf-8")
    git("commit", "-q", "-am", "neu", ordner=arbeit)
    git("push", "-q", "origin", "HEAD:main", ordner=arbeit)

    gefunden = []
    suche = ga.Suche(lambda e: gefunden.append(ga.zeige(e, ordner=installiert)), ordner=installiert)
    suche.start()
    for _ in range(40):
        yield 250
        if gefunden:
            break
    dialog = ga.UpdateDialog.offen
    h.pruefe(
        bool(gefunden) and dialog is not None and dialog.isVisible(),
        "Update-Hinweis erscheint nicht",
    )
    if dialog is None:
        return
    h.pruefe(
        "9.9.0" in dialog.text.text(),
        f"Hinweis nennt die neue Version nicht: {dialog.text.text()!r}",
    )
    h.bild("1_update_hinweis", dialog)

    dialog.knopf_jetzt.click()
    yield 500
    h.pruefe("neu starten" in dialog.text.text(), f"nach dem Aktualisieren: {dialog.text.text()!r}")
    h.pruefe(
        a.pruefe(installiert).version_jetzt == "9.9.0", "Addon-Ordner wurde nicht aktualisiert"
    )
    h.bild("2_aktualisiert", dialog)
    dialog.close()

    seite = gui_sprachwahl.Einstellungsseite()
    seite.loadSettings()
    h.pruefe(seite.update_beim_start.isChecked(), "„Beim Start suchen“ ist nicht vorbelegt")
    seite.form.resize(520, 260)
    seite.form.show()
    yield 300
    h.bild("3_einstellungen", seite.form)
    seite.update_beim_start.setChecked(False)
    seite.saveSettings()
    h.pruefe(not ga.suche_beim_start(), "Abschalten der Update-Suche wird nicht gespeichert")
    seite.form.close()
