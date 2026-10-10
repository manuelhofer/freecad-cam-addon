# „Aus Datei einlesen …“ in „Werkzeuge der Hersteller“ (T-007, werkzeugkiste_datei): die
# Hoffmann-Datei aus beispiele/ (79 Reihen, ohne Dubletten, fünf Hinweise) kommt in die Kiste und
# steht im Baum; dieselbe Datei noch einmal ersetzt sich selbst; eine zweite Datei mit demselben
# Artikel unter anderer Kennung bleibt draußen – der Bericht sagt es; „Vorlage speichern …“
# schreibt das Beispiel; „Hinzufügen“ einer eingelesenen Reihe legt sie in die eigene Kiste, ein
# zweites Mal „gab es schon“.
import json
import os
import shutil
import tempfile

import FreeCADGui as Gui
from PySide import QtCore, QtGui

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300

    from camaddon import gui_werkzeuge
    from camaddon import werkzeuge as wz
    from camaddon import werkzeugkiste as wk
    from camaddon import werkzeugkiste_datei as wd

    shutil.rmtree(wd.ordner(), ignore_errors=True)
    wd.vergessen()
    wz.Bibliothek([]).speichern()
    eingebaut = len(wk.eingebaute())
    hoffmann = os.path.join(ADDON, "beispiele", "werkzeugkiste_hoffmann_2026-10-07.json")

    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d is not None, "keine Werkzeugverwaltung")
    if d is None:
        return
    d.knopf_kiste.click()
    yield from h.warte_auf(lambda: getattr(d, "kiste", None) is not None and d.kiste.isVisible())
    kiste = getattr(d, "kiste", None)
    h.pruefe(kiste is not None, "kein Fenster „Werkzeuge der Hersteller“")
    if kiste is None:
        return
    vorher = len(kiste.reihen_eintraege())
    h.bild("1_kiste", kiste)

    # --- Die Hoffmann-Datei einlesen ----------------------------------------------------------
    gui_werkzeuge.kiste_datei_waehlen = lambda _eltern, _ordner: hoffmann
    QtCore.QTimer.singleShot(0, kiste.knopf_einlesen.click)  # der Bericht ist modal
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 60000)
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        text = meldung.text()
        h.pruefe("79 Reihen mit 79 Größen" in text, f"Bericht: {text!r}")
        h.pruefe("7 Hinweise" in text and "ausgelassen" not in text, f"Bericht: {text!r}")
        h.bild("2_bericht", meldung)
        meldung.accept()
    else:
        h.pruefe(False, f"kein Bericht: {meldung}")
    yield 500
    b = kiste.bericht
    h.pruefe(
        b is not None
        and len(b.reihen) == 79
        and not b.doppelt
        and not b.fehler
        and len(b.hinweise) == 7,
        f"Prüfung: {b and (len(b.reihen), b.doppelt[:1], b.fehler[:1], len(b.hinweise))}",
    )
    h.pruefe(
        len(kiste.reihen_eintraege()) == vorher + 79,
        f"Baum: {len(kiste.reihen_eintraege())} statt {vorher + 79}",
    )
    h.pruefe(
        os.path.isfile(os.path.join(wd.ordner(), os.path.basename(hoffmann))),
        "Datei nicht im Ordner",
    )
    h.pruefe(len(wk.reihen()) == eingebaut + 79, f"reihen(): {len(wk.reihen())}")
    h.bild("3_baum", kiste)

    # --- Noch einmal dieselbe Datei: ersetzt sich selbst, nichts doppelt ------------------------
    QtCore.QTimer.singleShot(0, kiste.knopf_einlesen.click)  # der Bericht ist modal
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 60000)
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        h.pruefe("79 Reihen ersetzen" in meldung.text(), f"nochmal: {meldung.text()!r}")
        meldung.accept()
    else:
        h.pruefe(False, f"nochmal: kein Bericht: {meldung}")
    yield 500
    h.pruefe(len(kiste.reihen_eintraege()) == vorher + 79, "nochmal: der Baum hat sie doppelt")

    # --- Eine zweite Datei: derselbe Artikel unter anderer Kennung – bleibt draußen -------------
    ordner = tempfile.mkdtemp()
    with open(hoffmann, encoding="utf-8") as datei:
        daten = json.load(datei)
    erste = dict(daten["reihen"][0], kennung="szenario-nochmal", titel="Noch einmal derselbe")
    zweite_datei = os.path.join(ordner, "werkzeugkiste_szenario.json")
    with open(zweite_datei, "w", encoding="utf-8") as datei:
        json.dump({"format": wd.FORMAT, "version": 1, "reihen": [erste]}, datei, ensure_ascii=False)
    gui_werkzeuge.kiste_datei_waehlen = lambda _eltern, _ordner: zweite_datei
    QtCore.QTimer.singleShot(0, kiste.knopf_einlesen.click)  # der Bericht ist modal
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 60000)
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        text = meldung.text()
        h.pruefe(
            "kommt nichts" in text and "1 Größen ausgelassen" in text and "1 Hinweise" in text,
            f"Dublette: {text!r}",
        )
        h.pruefe("Artikel" in meldung.detailedText(), f"Einzelheiten: {meldung.detailedText()!r}")
        h.bild("4_dublette", meldung)
        meldung.accept()
    else:
        h.pruefe(False, f"Dublette: kein Bericht: {meldung}")
    yield 500
    h.pruefe(
        not os.path.isfile(os.path.join(wd.ordner(), "werkzeugkiste_szenario.json")),
        "Datei ohne Reihen im Ordner",
    )

    # --- Vorlage speichern ---------------------------------------------------------------------
    vorlage = os.path.join(ordner, "vorlage.json")
    gui_werkzeuge.vorlage_datei_waehlen = lambda _eltern, _ordner: vorlage
    QtCore.QTimer.singleShot(0, kiste.knopf_vorlage.click)
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 10000)
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        meldung.accept()
    yield 300
    h.pruefe(os.path.isfile(vorlage), "Vorlage fehlt")

    # --- Hinzufügen: nur die erste eingelesene Reihe, ein zweites Mal „gab es schon“ -----------
    kiste.alle_setzen(False)
    zeile = next(
        (z for z in kiste.reihen_eintraege() if z.data(0, QtCore.Qt.UserRole) == "holex-202770"),
        None,
    )
    h.pruefe(zeile is not None, "holex-202770 nicht im Baum")
    if zeile is None:
        return
    zeile.setCheckState(0, QtCore.Qt.Checked)
    h.pruefe(kiste.gewaehlt() == ["holex-202770"], f"gewählt: {kiste.gewaehlt()}")
    kiste.accept()
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 10000)
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        h.pruefe(
            "1 Werkzeuge hinzugefügt, 0 gab es schon" in meldung.text(),
            f"Hinzufügen: {meldung.text()!r}",
        )
        meldung.accept()
    else:
        h.pruefe(False, f"Hinzufügen: kein Bericht: {meldung}")
    yield 300
    h.pruefe(len(d.liste.eintraege()) == 1, f"{len(d.liste.eintraege())} Werkzeuge statt 1")
    h.bild("5_liste", d)
    bericht = d.aus_kiste_hinzufuegen(["holex-202770"])
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 10000)
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        meldung.accept()
    h.pruefe(not bericht.neu and bericht.schon_da == ["HOLEX 202770-12"], f"zweites Mal: {bericht}")
    yield 300
    shutil.rmtree(wd.ordner(), ignore_errors=True)
    shutil.rmtree(ordner, ignore_errors=True)
    wd.vergessen()
    d.accept()
    yield 500
