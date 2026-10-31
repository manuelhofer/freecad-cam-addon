# Die Kataloge als eigener Download (kataloge.py, gui_kataloge.py; Manuel, 2026-10-31: „"hey sollen
# wir die kataloginhalte downloaden …" … und dann ja nein vll“). Wie nach einem Update ohne die
# Kataloge im Addon (kataloge.PAKET leer), geladen wird von einem Webserver hier, nicht von GitHub.
# 1. Die Frage nach dem Start: „Ja, laden“, „Später“, „Nein“ mit der Größe des Downloads. „Später“
#    merkt sich die Wahl.
# 2. Der Katalog der Halter ohne Kataloge: leer, darüber der Satz und „Kataloge laden …“.
# 3. „Kataloge laden …“: das Fenster mit dem Fortschritt, am Ende „Fertig – n Dateien“; danach
#    füllt sich der Katalog der Halter, der Satz ist weg, die Wahl ist „ja“.
import functools
import http.server
import os
import shutil
import tempfile
import threading

import FreeCADGui as Gui
from PySide import QtCore, QtGui


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300

    from camaddon import gui_halter, gui_katalog, gui_kataloge, kataloge
    from camaddon import halter as hl
    from camaddon import halter_katalog as hk

    quelle = tempfile.mkdtemp()
    shutil.copytree(kataloge.PAKET, os.path.join(quelle, "camaddon"), dirs_exist_ok=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=quelle)
    handler.log_message = lambda *a, **k: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    kataloge.ADRESSE = f"http://127.0.0.1:{server.server_address[1]}/camaddon/"
    kataloge.PAKET = tempfile.mkdtemp()  # wie aus dem Update-Paket
    kataloge.geaendert()
    shutil.rmtree(kataloge.profil(), ignore_errors=True)
    h.pruefe(not kataloge.vorhanden(), "Kataloge schon da")

    # 1. Die Frage
    QtCore.QTimer.singleShot(0, gui_kataloge._nach_dem_start)
    yield from h.warte_auf(lambda: gui_kataloge.KatalogFrage.offen is not None, 10000)
    frage = gui_kataloge.KatalogFrage.offen
    h.pruefe(frage is not None, "keine Frage nach dem Start")
    if frage is None:
        return
    yield 300
    text = frage.findChildren(QtGui.QLabel)[0].text()
    h.pruefe("Download" in text and "MB" in text, f"Frage: {text!r}")
    h.bild("1_frage", frage)
    frage.knopf_spaeter.click()
    yield 300
    h.pruefe(gui_kataloge.KatalogFrage.offen is None, "„Später“ schließt nicht")
    h.pruefe(gui_kataloge.wahl() == kataloge.SPAETER, f"Wahl: {gui_kataloge.wahl()!r}")

    # 2. Der Katalog der Halter, noch leer
    def holen():
        reihen = list(hk.katalog_reihen())
        aufnahmen = list(dict.fromkeys(r.aufnahme for r in reihen))
        return reihen, [(a, f"{a} ({hl.AUFNAHMEN[a][0]})") for a in aufnahmen]

    reihen, gruppen = holen()
    k = gui_katalog.KatalogDialog(
        Gui.getMainWindow(),
        "Halter",
        "Katalog der Halter",
        reihen,
        gruppen,
        lambda reihe: reihe.aufnahme,
        gui_halter._katalog_zeile,
        holen,
    )
    k.show()
    yield 500
    zeile = k.kataloge_zeile
    h.pruefe(zeile is not None and zeile.isVisible(), "kein „Kataloge laden …“")
    h.pruefe(k.baum.topLevelItemCount() == 0, f"Katalog nicht leer: {k.baum.topLevelItemCount()}")
    h.bild("2_katalog_leer", k)
    if zeile is None:
        return

    # 3. Laden
    knopf = zeile.findChildren(QtGui.QPushButton)[0]
    QtCore.QTimer.singleShot(0, knopf.click)
    yield from h.warte_auf(lambda: gui_kataloge.LadenFenster.offen is not None, 10000)
    fenster = gui_kataloge.LadenFenster.offen
    h.pruefe(fenster is not None, "kein Fenster zum Laden")
    if fenster is None:
        return
    yield from h.warte_auf(lambda: fenster.ergebnis is not None, 120000)
    yield 500
    h.pruefe("Fertig" in fenster.text.text(), f"Laden: {fenster.text.text()!r}")
    h.bild("3_geladen", fenster)
    fenster.knopf_zu.click()
    yield 500
    h.pruefe(k.baum.topLevelItemCount() > 0, "der Katalog füllt sich nicht")
    h.pruefe(not zeile.isVisible(), "„Kataloge laden …“ steht noch da")
    h.pruefe(gui_kataloge.wahl() == kataloge.JA, f"Wahl nach dem Laden: {gui_kataloge.wahl()!r}")
    h.pruefe(not kataloge.fehlend(), f"fehlt: {kataloge.fehlend()[:2]}")
    h.bild("4_katalog_voll", k)
    k.reject()
    server.shutdown()
