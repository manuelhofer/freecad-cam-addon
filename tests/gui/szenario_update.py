# Update auf Knopfdruck: Auf „GitHub“ (nacktes Repo im Temp-Ordner) liegt
# eine neue Version; „Nach Updates suchen“ findet sie, der Hinweis erscheint,
# „Jetzt aktualisieren“ holt sie. Der Knopf hängt in der Werkzeugleiste; die
# Suche beim Start ist ab Werk aus (Gruppe „Updates“ in den Einstellungen).
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
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
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

    import FreeCADGui

    befehl = FreeCADGui.Command.get("CamAddon_UpdateSuchen")
    h.pruefe(befehl is not None, "Befehl „Nach Updates suchen“ fehlt")
    gefunden = []
    ga.von_hand_suchen(ordner=installiert, danach=lambda: gefunden.append(True))
    for _ in range(40):
        yield 250
        if gefunden:
            break
    yield 200
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
    h.pruefe(
        dialog.knopf_neustart.isVisible() and dialog.knopf_neustart.text() == "Jetzt neu starten",
        "kein Knopf „Jetzt neu starten“ nach dem Aktualisieren",
    )
    h.bild("2_aktualisiert", dialog)
    dialog.close()

    # „Jetzt neu starten“ – mit einem Ersatz für Hauptfenster und Programmstart: Schließt
    # das Fenster, startet FreeCAD neu; bricht man beim Schließen ab, startet nichts.
    class Fenster:
        def __init__(self, schliesst):
            self.schliesst = schliesst

        def close(self):
            return self.schliesst

    gestartet = []
    h.pruefe(
        ga.neu_starten(Fenster(True), lambda programm, argumente: gestartet.append(programm)),
        "neu_starten: schließt nicht",
    )
    h.pruefe(len(gestartet) == 1 and "reecad" in gestartet[0].lower(), f"gestartet: {gestartet}")
    h.pruefe(
        not ga.neu_starten(Fenster(False), lambda *_: gestartet.append("nochmal"))
        and len(gestartet) == 1,
        "neu_starten startet trotz Abbrechen",
    )

    seite = gui_sprachwahl.Einstellungsseite()
    seite.loadSettings()
    h.pruefe(not seite.update_beim_start.isChecked(), "„Beim Start suchen“ ist ab Werk an")
    seite.form.resize(520, 340)
    seite.form.show()
    yield 300
    h.bild("3_einstellungen", seite.form)
    seite.update_beim_start.setChecked(True)
    seite.saveSettings()
    h.pruefe(ga.suche_beim_start(), "Einschalten der Update-Suche wird nicht gespeichert")
    seite.update_beim_start.setChecked(False)
    seite.saveSettings()
    h.pruefe(not ga.suche_beim_start(), "Abschalten der Update-Suche wird nicht gespeichert")
    seite.form.close()

    # --- Ohne Pythons ssl (P-2026-09-30-33) ------------------------------------------------
    # Manuels FreeCAD meldete bei der Zeile aus dem README „unknown url type: https“: Pythons
    # ssl fehlte. Die Zeile lädt jetzt über den Netzzugang des Addon-Managers (Qt), die Suche
    # ohne Git ebenso – dann aus ihrem Thread, während die Oberfläche weiterläuft. „GitHub“ ist
    # ein HTTP-Server auf 127.0.0.1.
    import http.server
    import shutil
    import threading

    import FreeCAD
    import NetworkManager

    fern_xml = re.sub(
        r"<version>[^<]+</version>",
        "<version>9.9.9</version>",
        Path(ADDON, "package.xml").read_text("utf-8"),
    )
    dateien = {"/zeile.py": b"GELADEN = 42\n", "/package.xml": fern_xml.encode("utf-8")}

    class Github(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 – so heißt es in http.server
            inhalt = dateien.get(self.path)
            if inhalt is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(inhalt)))
            self.end_headers()
            self.wfile.write(inhalt)

        def log_message(self, *argumente):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Github)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    github = f"http://127.0.0.1:{server.server_address[1]}"
    # Der Addon-Manager nähme sonst den Proxy des Systems – auch für 127.0.0.1.
    am = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Addons")
    am.SetString("proxy_type", "none")
    am.SetBool("proxy_settings_migrated_2025", True)
    NetworkManager.ForceReinitializeNetworkManager()

    readme = Path(ADDON, "README.md").read_text("utf-8")
    zeile = next(z.strip() for z in readme.splitlines() if z.strip().startswith("import Network"))
    adresse = "https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py"
    h.pruefe(adresse in zeile, f"README-Zeile: {zeile!r}")
    namensraum = {}
    exec(zeile.replace(adresse, f"{github}/zeile.py"), namensraum)
    h.pruefe(namensraum.get("GELADEN") == 42, "die Zeile aus dem README lädt nicht über Qt")

    # Die Suche ohne Git, über Qt: installieren.py im Addon-Ordner nimmt den Weg über Qt, wie
    # ohne ssl für https – hier für http, weil „GitHub“ kein https spricht.
    ohne_git = os.path.join(basis, "ohne_git")
    os.makedirs(ohne_git)
    shutil.copy(os.path.join(ADDON, "package.xml"), ohne_git)
    text = Path(ADDON, "installieren.py").read_text("utf-8")
    immer_qt = 'return adresse.lower().startswith("https:") and not hasattr(http.client'
    h.pruefe(immer_qt in text, "installieren.py: _nur_ueber_qt() nicht gefunden")
    text = text.replace(immer_qt, "return True or (http.client")
    Path(ohne_git, "installieren.py").write_text(text, "utf-8")
    a.netz_vorbereiten(ohne_git)  # im Hauptthread, wie gui_aktualisierung.Suche.start()
    ergebnis = []
    threading.Thread(
        target=lambda: ergebnis.append(a.pruefe(ohne_git, adresse_version=f"{github}/package.xml")),
        daemon=True,
    ).start()
    for _ in range(80):
        yield 250
        if ergebnis:
            break
    h.pruefe(
        bool(ergebnis) and ergebnis[0].status == a.NEU and ergebnis[0].version_neu == "9.9.9",
        f"Suche über Qt im Thread: {ergebnis}",
    )
    server.shutdown()
