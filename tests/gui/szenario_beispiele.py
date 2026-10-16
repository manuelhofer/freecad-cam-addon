# „Beispiele laden …“ (gui_beispiele, Manuel 2026-10-16: alle Testteile im Repository, beim Laden
# wählbar): Im Menü „CAM-Addon“ steht der Befehl. Das Fenster nennt jede Datei mit Größe, keine
# angehakt („Laden“ grau), darüber „Alle anhaken“ und „Alle abhaken“ (Manuel, 2026-10-16); oben,
# wie viele es sind, wie groß zusammen und wohin sie kommen. Nur drei angehakt,
# „Laden“ (hier aus dem Repository statt von GitHub): „Fertig: 3 geladen, 0 waren schon da“, die
# Dateien liegen im Ordner, „Ordner öffnen“ geht. Ein zweites Mal: „0 geladen, 3 waren schon da“.
import os
import tempfile

import FreeCADGui as Gui
from PySide import QtCore, QtGui

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def aus_dem_repository(adresse, _zeitlimit):
    pfad = adresse.split("/main/", 1)[1]
    with open(os.path.join(ADDON, *pfad.split("/")), "rb") as quelle:
        return quelle.read()


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500
    from camaddon import beispiele as bsp
    from camaddon import gui_beispiele

    Gui.activateWorkbench("CAMWorkbench")
    yield 500
    menue = next(
        (
            m
            for m in Gui.getMainWindow().menuBar().findChildren(QtGui.QMenu)
            if m.title() == "CAM-Addon"
        ),
        None,
    )
    texte = [a.text() for a in menue.actions()] if menue is not None else []
    h.pruefe("Beispiele laden …" in texte, f"Menü: {texte}")

    wohin = tempfile.mkdtemp()
    dialog = gui_beispiele.BeispieleDialog(liste=bsp.liste(), wohin=wohin, hole=aus_dem_repository)
    dialog.show()
    yield 500
    h.pruefe(dialog.liste.count() == len(bsp.liste()) > 30, f"Einträge: {dialog.liste.count()}")

    def angehakt():
        return [
            i
            for i in range(dialog.liste.count())
            if dialog.liste.item(i).checkState() == QtCore.Qt.Checked
        ]

    h.pruefe(not angehakt(), f"zu Beginn angehakt: {angehakt()}")
    h.pruefe(not dialog.knopf_laden.isEnabled(), "„Laden“ ohne Haken nicht grau")
    dialog.knopf_alle.click()
    h.pruefe(len(angehakt()) == dialog.liste.count(), "„Alle anhaken“ hakt nicht alle an")
    h.pruefe(dialog.knopf_laden.isEnabled(), "„Laden“ mit Haken grau")
    dialog.knopf_keine.click()
    h.pruefe(not angehakt(), f"„Alle abhaken“: noch angehakt {angehakt()}")
    erste = dialog.liste.item(0).text()
    h.pruefe(" – " in erste and ("kB" in erste or "MB" in erste), f"Größe fehlt: {erste!r}")
    h.bild("1_fenster", dialog)
    kleine = [i for i, b in enumerate(dialog.beispiele) if b.bytes < 200_000][:3]
    for i in range(dialog.liste.count()):
        dialog.liste.item(i).setCheckState(
            QtCore.Qt.Checked if i in kleine else QtCore.Qt.Unchecked
        )
    dialog.knopf_laden.click()
    yield from h.warte_auf(lambda: dialog.stand.text().startswith("Fertig"), 30000)
    h.pruefe(
        dialog.stand.text().startswith("Fertig: 3 geladen, 0 waren schon da"),
        f"Stand: {dialog.stand.text()!r}",
    )
    h.pruefe(
        all(bsp.schon_da(dialog.beispiele[i], wohin) for i in kleine), "Dateien nicht im Ordner"
    )
    h.pruefe(dialog.knopf_ordner.isEnabled(), "„Ordner öffnen“ grau")
    h.bild("2_geladen", dialog)
    dialog.stand.setText("")
    dialog.knopf_laden.click()
    yield from h.warte_auf(
        lambda: "waren schon da" in dialog.stand.text() and dialog.knopf_laden.isEnabled(), 30000
    )
    yield 300
    h.pruefe(
        dialog.stand.text().startswith("Fertig: 0 geladen, 3 waren schon da"),
        f"zweites Mal: {dialog.stand.text()!r}",
    )
    dialog.reject()
    yield 300
    h.pruefe(gui_beispiele.BeispieleDialog.offen is None, "Fenster nicht zu")
