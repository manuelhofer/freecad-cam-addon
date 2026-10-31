# „Werkzeuge der Hersteller“ (T-007, werkzeugkiste_datei): Die Hoffmann-Liste kommt mit dem Addon
# (camaddon/werkzeugkiste_daten/hoffmann.json, 77 Reihen; P-2026-10-16-48) und steht ohne Einlesen
# im Baum. „Aus Datei einlesen …“: eine eigene Datei mit fünf Reihen (andere Kennungen und
# Artikelnummern) kommt in die Kiste; dieselbe Datei noch einmal ersetzt sich selbst; eine zweite
# Datei mit einem Artikel, den es schon gibt, bleibt draußen – der Bericht sagt es; „Vorlage
# speichern …“ schreibt das Beispiel; „Hinzufügen“ einer Reihe legt sie in die eigene Kiste, ein
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
    mitgeliefert = wd.mitgelieferte()
    # hoffmann.json und die Kataloge der Hersteller (W-042, über 40 000 Größen).
    h.pruefe(
        sum(r.datei == "hoffmann.json" for r in mitgeliefert) == 77 and len(mitgeliefert) > 1000,
        f"mitgeliefert: {len(mitgeliefert)} Reihen",
    )
    h.pruefe(
        len(wk.reihen()) == eingebaut + len(mitgeliefert),
        f"reihen() ohne Datei: {len(wk.reihen())}",
    )
    ordner = tempfile.mkdtemp()
    with open(os.path.join(wd.mitgeliefert_ordner(), "hoffmann.json"), encoding="utf-8") as datei:
        daten = json.load(datei)
    # Eine eigene Datei: fünf Reihen mit anderen Kennungen und Artikelnummern (sonst wären sie
    # doppelt – es gibt sie ja schon).
    eigene_reihen = []
    for reihe in daten["reihen"][:5]:
        reihe = dict(reihe, kennung=reihe["kennung"] + "-szenario", titel=reihe["titel"] + " (S)")
        reihe["groessen"] = [
            dict(g, artikel=str(g.get("artikel", "")) + "-S") for g in reihe["groessen"]
        ]
        eigene_reihen.append(reihe)
    groessen = sum(len(r["groessen"]) for r in eigene_reihen)
    eigene = os.path.join(ordner, "werkzeugkiste_eigene.json")
    with open(eigene, "w", encoding="utf-8") as datei:
        json.dump({"format": wd.FORMAT, "version": 1, "reihen": eigene_reihen}, datei)

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
    h.pruefe(
        any(z.data(0, QtCore.Qt.UserRole) == "garant-208080" for z in kiste.reihen_eintraege()),
        "die mitgelieferte Reihe garant-208080 fehlt im Baum",
    )
    # Am Anfang ist nichts angehakt (P-2026-10-12-114).
    h.pruefe(kiste.gewaehlt() == [], f"schon angehakt: {kiste.gewaehlt()[:5]}")
    h.bild("1_kiste", kiste)

    # --- Die eigene Datei einlesen -------------------------------------------------------------
    gui_werkzeuge.kiste_datei_waehlen = lambda _eltern, _ordner: eigene
    QtCore.QTimer.singleShot(0, kiste.knopf_einlesen.click)  # der Bericht ist modal
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 60000)
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        text = meldung.text()
        h.pruefe(f"5 Reihen mit {groessen} Größen" in text, f"Bericht: {text!r}")
        h.pruefe("ausgelassen" not in text, f"Bericht: {text!r}")
        h.bild("2_bericht", meldung)
        meldung.accept()
    else:
        h.pruefe(False, f"kein Bericht: {meldung}")
    yield 500
    b = kiste.bericht
    h.pruefe(
        b is not None and len(b.reihen) == 5 and not b.doppelt and not b.fehler,
        f"Prüfung: {b and (len(b.reihen), b.doppelt[:1], b.fehler[:1])}",
    )
    h.pruefe(
        len(kiste.reihen_eintraege()) == vorher + 5,
        f"Baum: {len(kiste.reihen_eintraege())} statt {vorher + 5}",
    )
    h.pruefe(
        os.path.isfile(os.path.join(wd.ordner(), os.path.basename(eigene))),
        "Datei nicht im Ordner",
    )
    h.pruefe(len(wk.reihen()) == eingebaut + len(mitgeliefert) + 5, f"reihen(): {len(wk.reihen())}")
    h.bild("3_baum", kiste)

    # --- Noch einmal dieselbe Datei: ersetzt sich selbst, nichts doppelt ------------------------
    QtCore.QTimer.singleShot(0, kiste.knopf_einlesen.click)  # der Bericht ist modal
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 60000)
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        h.pruefe("5 Reihen ersetzen" in meldung.text(), f"nochmal: {meldung.text()!r}")
        meldung.accept()
    else:
        h.pruefe(False, f"nochmal: kein Bericht: {meldung}")
    yield 500
    h.pruefe(len(kiste.reihen_eintraege()) == vorher + 5, "nochmal: der Baum hat sie doppelt")

    # --- Eine zweite Datei: ein Artikel, den es schon gibt, unter anderer Kennung – draußen -----
    einzeln = next(r for r in daten["reihen"] if len(r["groessen"]) == 1)
    erste = dict(einzeln, kennung="szenario-nochmal", titel="Noch einmal derselbe")
    zweite_datei = os.path.join(ordner, "werkzeugkiste_szenario.json")
    with open(zweite_datei, "w", encoding="utf-8") as datei:
        json.dump({"format": wd.FORMAT, "version": 1, "reihen": [erste]}, datei, ensure_ascii=False)
    gui_werkzeuge.kiste_datei_waehlen = lambda _eltern, _ordner: zweite_datei
    QtCore.QTimer.singleShot(0, kiste.knopf_einlesen.click)  # der Bericht ist modal
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 60000)
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        text = meldung.text()
        h.pruefe("kommt nichts" in text and "1 Größen ausgelassen" in text, f"Dublette: {text!r}")
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

    # --- Hinzufügen: eine mitgelieferte Reihe mit einer Größe, ein zweites Mal „gab es schon“ ---
    kiste.alle_setzen(False)
    kennung = einzeln["kennung"]
    zeile = next(
        (z for z in kiste.reihen_eintraege() if z.data(0, QtCore.Qt.UserRole) == kennung), None
    )
    h.pruefe(zeile is not None, f"{kennung} nicht im Baum")
    if zeile is None:
        return
    zeile.setCheckState(0, QtCore.Qt.Checked)
    h.pruefe(kiste.gewaehlt() == [kennung], f"gewählt: {kiste.gewaehlt()}")
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
    bericht = d.aus_kiste_hinzufuegen([kennung])
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 10000)
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        meldung.accept()
    h.pruefe(not bericht.neu and len(bericht.schon_da) == 1, f"zweites Mal: {bericht}")
    yield 300
    shutil.rmtree(wd.ordner(), ignore_errors=True)
    shutil.rmtree(ordner, ignore_errors=True)
    wd.vergessen()
    d.accept()
    yield 500
