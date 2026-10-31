# Halter (W-002 Stufe D): In der Werkzeugverwaltung ein Werkzeug mit 83 mm
# Gesamtlänge; neben der Länge ab Spindelnase grau der vorgeschlagene Halter (D-23: Schaft
# Ø 12 → ER25) und „Halter …“, im leeren Feld „leer: geschätzt 101 mit ER25“ (70 + Auskragung 26 + 5).
# Das Fenster „Halter“ ist leer; „Neu“ → „Spannzangenfutter ER32 · SK40“: die
# Kontur nach der Katalogzeichnung (Flansch Ø63,55 × 19,1 … Mutter Ø50), der Link zum Vorbild,
# „Länge 70,00 mm · größter Ø 63,55 mm“, das Bild zeigt Halter und Werkzeug, über OK „OK: T1 bekommt den
# Halter …“. Ein Abschnitt dazu (10 mm, Ø 42) macht ihn 80 mm lang, wieder weg
# 70 mm; Name „SK40 ER32 A70“. OK → das Werkzeug hat den Halter, im leeren Feld
# steht grau „leer: geschätzt 113 mit Halter“ (70 + 83 − 40). Abbrechen im Halter-Fenster
# verwirft einen neuen Halter. Speichern und neu laden: Halter und Zuordnung
# sind da. Löschen fragt und nennt T1; danach ist T1 ohne Halter.
import os

import FreeCADGui as Gui
from PySide import QtCore, QtGui
from PySide6 import QtTest

AUSGABE = os.environ["CAMADDON_AUSGABE"]


def tippen(feld, text):
    """Feld leeren, `text` Taste für Taste tippen, Enter."""
    feld.setFocus()
    feld.selectAll()
    QtTest.QTest.keyClick(feld, QtCore.Qt.Key_Delete)
    QtTest.QTest.keyClicks(feld, text)
    QtTest.QTest.keyClick(feld, QtCore.Qt.Key_Return)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300

    from camaddon import gui_halter, gui_werkzeuge
    from camaddon import werkzeuge as wz

    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d is not None and d.isVisible(), "Werkzeugverwaltung geht nicht auf")
    if d is None:
        return
    d.knopf_neu.click()
    yield 200
    tippen(d.feld_gesamtlaenge, "83")
    yield 200
    h.pruefe(d.feld_halter.count() == 1, f"Halter-Auswahl: {d.feld_halter.count()} Einträge")
    h.pruefe(
        d.feld_halter.currentText().startswith("Keiner gewählt – geprüft wird mit")
        and "ER25" in d.feld_halter.currentText(),
        f"Halter: {d.feld_halter.currentText()}",
    )
    h.pruefe(
        d.feld_laenge_spindelnase.placeholderText() == "leer: geschätzt 101 mit ER25",
        f"Platzhalter ohne Halter: {d.feld_laenge_spindelnase.placeholderText()!r}",
    )
    h.bild("0_vorschlag", d)

    # --- Das Fenster „Halter“: leer, dann aus der Vorlage ER32 ------------------------------
    QtCore.QTimer.singleShot(0, d.knopf_halter.click)
    yield 500
    f = gui_halter.HalterDialog.offen
    h.pruefe(f is not None and f.isVisible(), "Fenster „Halter“ geht nicht auf")
    if f is None:
        return
    h.pruefe(f.leer.isVisible() and not f.rahmen.isVisible(), "leer: Hinweis „Neu“ fehlt")
    h.pruefe(f.ok_hinweis.text() == "OK: T1 bleibt ohne Halter.", f"{f.ok_hinweis.text()!r}")
    h.bild("1_halter_leer", f)
    vorlage = next(a for a in f.menue_neu.actions() if a.text() == "Spannzangenfutter ER32 · SK40")
    vorlage.trigger()
    yield 300
    halter = f.gewaehlt
    h.pruefe(halter is not None and f.liste.count() == 1, "Vorlage legt keinen Halter an")
    # Nach der Katalogzeichnung (P-2026-10-16-39): Flansch, Rundung, Körper, Kegel, Hals, Mutter.
    h.pruefe(f.tabelle.rowCount() == 6, f"Kontur: {f.tabelle.rowCount()} Abschnitte")
    zellen = [f.tabelle.item(0, s).text() for s in range(3)]
    h.pruefe(zellen == ["19,1", "63,55", "63,55"], f"Flansch: {zellen}")
    # Flansch und Spannmutter je eine Zeile, gezeichnet mit Greiferrille und Fase (W-022).
    tipps = [f.tabelle.verticalHeaderItem(z).toolTip() for z in range(6)]
    h.pruefe(
        tipps[0].startswith("Flansch")
        and not any(tipps[1:5])
        and tipps[5].startswith("Spannmutter"),
        f"Art der Abschnitte: {tipps}",
    )
    # Der Link zum Vorbild im Katalog; „Öffnen“ geht.
    h.pruefe(
        f.feld_link.text() == "https://www.hoffmann-group.com/DE/de/hom/p/300470-32"
        and f.knopf_link.isEnabled(),
        f"Link: {f.feld_link.text()!r}",
    )
    h.pruefe(
        f.zusammenfassung.text() == "Länge 70,00 mm · größter Ø 63,55 mm",
        f"Zusammenfassung: {f.zusammenfassung.text()!r}",
    )
    h.pruefe(
        f.ok_hinweis.text() == "OK: T1 bekommt den Halter „Spannzangenfutter ER32 · SK40“.",
        f"{f.ok_hinweis.text()!r}",
    )
    h.pruefe(f.bild.halter is halter and f.bild.laenge == 113, f"Bild: {f.bild.laenge}")
    h.bild("2_er32", f)

    # Ein Abschnitt dazu und wieder weg; ein Name.
    f.tabelle.setCurrentCell(1, 0)
    f.abschnitt_dazu()
    f.tabelle.item(2, 0).setText("10")
    f.tabelle.item(2, 2).setText("42")
    yield 200
    h.pruefe(abs(halter.laenge - 80) < 1e-9, f"mit Abschnitt: {halter.laenge}")
    h.pruefe(f.tabelle.item(2, 1).text() == "48", "neuer Abschnitt nicht so dick wie der davor")
    # Die gewählte Zeile steht im Bild farbig (Manuel, 2026-10-25).
    f.tabelle.setCurrentCell(2, 0)
    yield 100
    h.pruefe(f.bild.markiert == 2, f"im Bild markiert: {f.bild.markiert}")
    h.bild("3_abschnitt", f)
    f.tabelle.setCurrentCell(2, 0)
    f.abschnitt_weg()
    h.pruefe(abs(halter.laenge - 70) < 1e-9, f"Abschnitt weg: {halter.laenge}")
    tippen(f.feld_name, "SK40 ER32 A70")
    yield 200
    h.pruefe(f.liste.item(0).text() == "SK40 ER32 A70", f"Liste: {f.liste.item(0).text()}")
    # „Spannt Ø“ (Halter.spann_d): eingetragen kommt er an; ein ER-Futter hat ihn leer.
    h.pruefe(f.feld_spann_d.text() == "", f"Spannt Ø vorher: {f.feld_spann_d.text()!r}")
    tippen(f.feld_spann_d, "12")
    yield 200
    h.pruefe(abs(halter.spann_d - 12) < 1e-9, f"Spannt Ø: {halter.spann_d}")
    tippen(f.feld_spann_d, "")
    yield 200
    h.pruefe(halter.spann_d == 0, f"Spannt Ø geleert: {halter.spann_d}")
    # Nur ein Komma in der Spanntiefe: OK schließt trotzdem, die Spanntiefe bleibt.
    f.feld_spanntiefe.setText(",")
    f.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 400
    h.pruefe(abs(halter.spanntiefe - 40) < 1e-9, f"Spanntiefe nach „,“: {halter.spanntiefe}")

    # --- Zurück beim Werkzeug: der Halter ist gewählt, die Länge geschätzt -------------------
    h.pruefe(gui_halter.HalterDialog.offen is None, "Halter-Fenster noch offen")
    h.pruefe(d.feld_halter.currentText() == "SK40 ER32 A70", f"{d.feld_halter.currentText()}")
    h.pruefe(
        d.feld_laenge_spindelnase.placeholderText() == "leer: geschätzt 113 mit Halter",
        f"Platzhalter mit Halter: {d.feld_laenge_spindelnase.placeholderText()!r}",
    )
    h.bild("4_werkzeug_mit_halter", d)

    # Wie weit T1 aus dem Halter schaut (P-2026-10-12-113): grau geschätzt 43 (113 − 70); 25
    # eingetragen → die Länge ab Spindelnase grau 95 = Halter + heraus, im Bild des Halters das
    # Maß 25 neben dem Fräser.
    h.pruefe(
        d.feld_ausspannlaenge.placeholderText() == "leer: geschätzt 43",
        f"Ausspannlänge leer: {d.feld_ausspannlaenge.placeholderText()!r}",
    )
    tippen(d.feld_ausspannlaenge, "25")
    yield 300
    h.pruefe(
        d.feld_laenge_spindelnase.placeholderText() == "leer: 95 = Halter + heraus",
        f"mit Ausspannlänge: {d.feld_laenge_spindelnase.placeholderText()!r}",
    )
    h.bild("4b_ausspannlaenge", d)
    QtCore.QTimer.singleShot(0, d.knopf_halter.click)
    yield 500
    f = gui_halter.HalterDialog.offen
    h.pruefe(f is not None and abs(f.bild.laenge - 95) < 1e-6, "Halter-Bild nicht mit 95")
    if f is not None:
        h.bild("4c_halter_mit_mass", f)
        f.knoepfe.button(QtGui.QDialogButtonBox.Cancel).click()
    yield 300
    d.werkzeug.ausspannlaenge = 0.0
    d._felder_fuellen()

    # Abbrechen verwirft: ein neuer Halter kommt nicht an.
    QtCore.QTimer.singleShot(0, d.knopf_halter.click)
    yield 500
    f = gui_halter.HalterDialog.offen
    if f is not None:
        f.neu()
        f.knoepfe.button(QtGui.QDialogButtonBox.Cancel).click()
    yield 300
    h.pruefe(len(d.bibliothek.halter) == 1, f"Abbrechen verwirft nicht: {len(d.bibliothek.halter)}")
    h.pruefe(d.feld_halter.count() == 2, "Auswahl nach Abbrechen")

    # --- Speichern und laden -----------------------------------------------------------------
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 500
    gespeichert = wz.Bibliothek.laden()
    h.pruefe([x.name for x in gespeichert.halter] == ["SK40 ER32 A70"], "Halter nicht gespeichert")
    werkzeug = gespeichert.werkzeuge[0] if gespeichert.werkzeuge else None
    h.pruefe(
        werkzeug is not None and gespeichert.halter_von(werkzeug) is gespeichert.halter[0],
        "Zuordnung nicht gespeichert",
    )

    # --- Löschen: Rückfrage nennt T1, danach ist T1 ohne Halter ------------------------------
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d.feld_halter.currentText() == "SK40 ER32 A70", "nach dem Laden kein Halter gewählt")
    QtCore.QTimer.singleShot(0, d.knopf_halter.click)
    yield 500
    f = gui_halter.HalterDialog.offen
    QtCore.QTimer.singleShot(0, f.loeschen)
    yield 500
    frage = h.modal()
    h.pruefe(isinstance(frage, QtGui.QMessageBox), f"keine Rückfrage beim Löschen: {frage}")
    if isinstance(frage, QtGui.QMessageBox):
        h.pruefe("T1" in frage.text(), f"Rückfrage ohne T1: {frage.text()!r}")
        h.bild("5_loeschen", frage)
        frage.button(QtGui.QMessageBox.Yes).click()
    yield 300
    h.pruefe(f.liste.count() == 0 and f.leer.isVisible(), "nicht gelöscht")
    f.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 300
    h.pruefe(d.feld_halter.currentIndex() == 0, "T1 hat noch einen Halter")
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 500
    gespeichert = wz.Bibliothek.laden()
    h.pruefe(gespeichert.halter == [], "Halter nach Löschen noch gespeichert")
    h.pruefe(gespeichert.werkzeuge[0].halter == "", "T1 nennt den gelöschten Halter")

    # --- Aus Datei (W-022): ein ER32-Futter an SK40 als STEP – die Kontur ab der Spindelnase ----
    # (das Ende des Steilkegels bei 68), A = 63,5, Flansch Ø 63, Mutter mit Fase; die Bezeichnung
    # nennt die Datei. Abbrechen verwirft ihn wieder.
    import FreeCAD
    import Part

    umriss = [
        (0, 0), (12, 0), (22, 68), (31.5, 68), (31.5, 74), (28, 76), (31.5, 78), (31.5, 84),
        (25, 84), (25, 130), (23.5, 131.5), (0, 131.5), (0, 0),
    ]  # fmt: skip
    flaeche = Part.Face(Part.makePolygon([FreeCAD.Vector(r, 0, z) for r, z in umriss]))
    datei = os.path.join(AUSGABE, "er32_sk40.step")
    flaeche.revolve(FreeCAD.Vector(), FreeCAD.Vector(0, 0, 1), 360).exportStep(datei)
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    QtCore.QTimer.singleShot(0, d.knopf_halter.click)
    yield 500
    f = gui_halter.HalterDialog.offen
    h.pruefe(f is not None, "Halter-Fenster für „Aus Datei“ fehlt")
    if f is None:
        return
    halter = f.aus_datei(datei)
    yield 300
    h.pruefe(halter is not None and f.gewaehlt is halter, "Halter aus Datei nicht angelegt")
    if halter is not None:
        h.pruefe(abs(halter.laenge - 63.5) < 0.5, f"A aus Datei: {halter.laenge}")
        h.pruefe(abs(halter.groesster_durchmesser - 63) < 0.1, f"Ø: {halter.groesster_durchmesser}")
        h.pruefe(halter.name == "er32_sk40", f"Name: {halter.name!r}")
        h.pruefe(
            f.feld_bezeichnung.text().startswith("Gemessen aus der Datei er32_sk40.step"),
            f"Bezeichnung: {f.feld_bezeichnung.text()!r}",
        )
        h.pruefe(f.tabelle.rowCount() >= 5, f"Abschnitte: {f.tabelle.rowCount()}")
        # Ohne Link sucht der Knopf im Katalog nach dem Namen.
        h.pruefe(
            f.knopf_link.text() == "Im Katalog suchen"
            and f.link_adresse().endswith("search?search=er32_sk40"),
            f"ohne Link: {f.knopf_link.text()!r} {f.link_adresse()!r}",
        )
    h.bild("6_aus_datei", f)
    f.knoepfe.button(QtGui.QDialogButtonBox.Cancel).click()
    yield 300
    d.knoepfe.button(QtGui.QDialogButtonBox.Cancel).click()
    yield 300
