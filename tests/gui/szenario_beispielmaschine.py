# Beispielmaschinen zum Ausprobieren (W-001, Punkt 7b): „Maschine bearbeiten“
# ohne Baugruppe meldet das mit dem Knopf „Neue Maschine …“ (der leichte Weg steht
# vorn, der Selbstbau danach); der Knopf
# bietet die Bauarten zur Auswahl an – Drehmaschine, 3-Achs-Fräse, drei
# 5-Achs-Fräsen – und öffnet die gewählte samt Dialog. Die Drehmaschine hat
# einen Revolver: Dort gibt es das Feld „Revolverplatz“, an der Spindel der
# Fräse nicht. Genauso bei „Maschine verfahren“ in einem leeren Dokument –
# dort fahren X, Y und Z der 3-Achs-Fräse. Zum Schluss alle fünf als Bild.
import os

import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui

KNOPF = "Neue Maschine …"
SPALTEN = 3
BILD_B, BILD_H, BESCHRIFTUNG = 420, 320, 28


def knopf(meldung, text):
    return next((k for k in meldung.buttons() if k.text() == text), None)


def beispiel_waehlen(h, befehl, art, bilder, offen):
    """Ruft den Befehl auf, prüft die Meldung, klickt „Neue Maschine …“,
    wählt in der Auswahl `art` und lädt; wartet dann, bis `offen()` – der
    Dialog nach dem Laden ist da. `bilder`: Namen für Meldung und Auswahl."""
    from camaddon import beispielmaschine, gui_neue_maschine

    # Meldung und Auswahl blockieren, bis sie beantwortet sind.
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand(befehl))
    yield 800
    meldung = h.modal()
    h.pruefe(isinstance(meldung, QtGui.QMessageBox), f"{befehl}: keine Meldung ({meldung})")
    if not isinstance(meldung, QtGui.QMessageBox):
        return
    laden = knopf(meldung, KNOPF)
    h.pruefe(laden is not None, f"{befehl}: Knopf „{KNOPF}“ fehlt")
    h.pruefe(KNOPF in meldung.text(), f"Meldung: {meldung.text()!r}")
    h.pruefe(
        meldung.text().find(KNOPF) < meldung.text().find("Assembly"),
        f"der leichte Weg steht nicht vorn: {meldung.text()!r}",
    )
    h.bild(bilder[0], meldung)
    if laden is None:
        return
    laden.click()
    yield from h.warte_auf(lambda: gui_neue_maschine.NeueMaschineDialog.offen is not None)
    auswahl = gui_neue_maschine.NeueMaschineDialog.offen
    h.pruefe(auswahl is not None, f"{befehl}: keine Auswahl der Beispielmaschinen")
    if auswahl is None:
        return
    titel = [auswahl.liste.item(i).text() for i in range(auswahl.liste.count())]
    h.pruefe(titel == [beispielmaschine.titel(a) for a in beispielmaschine.ARTEN], f"{titel}")
    auswahl.liste.setCurrentRow(beispielmaschine.ARTEN.index(art))
    yield 200
    beschreibung = auswahl.beschreibung.text()
    h.pruefe(beschreibung == beispielmaschine.beschreibung(art), f"Beschreibung: {beschreibung!r}")
    h.bild(bilder[1], auswahl)
    auswahl.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield from h.warte_auf(offen)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_maschine, gui_verfahren
    from camaddon import verfahren as vf

    # Ohne Dokument: „Maschine bearbeiten“ – die Drehmaschine.
    yield from beispiel_waehlen(
        h,
        "CamAddon_MaschineBearbeiten",
        beispielmaschine.DREHMASCHINE,
        ("1_meldung_bearbeiten", "2_auswahl"),
        lambda: gui_maschine.MaschinenPanel.offen is not None,
    )
    doc = FreeCAD.ActiveDocument
    h.pruefe(
        doc is not None and doc.Label == "Beispiel Drehmaschine",
        f"Drehmaschine nicht geladen: {doc.Label if doc else None}",
    )
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(panel is not None, "„Maschine bearbeiten“ öffnet sich nicht nach dem Laden")
    if panel is None:
        return
    h.bild("3_bearbeiten_drehmaschine")
    # Auf dem Revolver gibt es das Feld „Revolverplatz“ (P-2026-09-26-52).
    # Die Plätze stehen unter „Revolver T – 12 Plätze“.
    platz = panel.aufnahmen.findItems("P1", QtCore.Qt.MatchStartsWith | QtCore.Qt.MatchRecursive)
    h.pruefe(bool(platz), "Revolverplatz P1 fehlt in der Liste")
    if platz:
        panel.aufnahmen.setCurrentItem(platz[0])
        yield 200
        zeilen = panel.details.formular.rowCount()
        h.pruefe(zeilen == 4, f"P1: {zeilen} Felder statt 4 (mit Revolverplatz)")
        h.bild("3b_revolverplatz")
    panel.reject()
    yield 500

    # In einem leeren Dokument: „Maschine verfahren“ – die 3-Achs-Fräse.
    FreeCAD.newDocument("Leer")
    yield 300
    yield from beispiel_waehlen(
        h,
        "CamAddon_MaschineVerfahren",
        beispielmaschine.FRAESE_3,
        ("4_meldung_verfahren", "5_auswahl_fraese"),
        lambda: gui_verfahren.VerfahrPanel.offen is not None,
    )
    panel = gui_verfahren.VerfahrPanel.offen
    h.pruefe(panel is not None, "„Maschine verfahren“ öffnet sich nicht nach dem Laden")
    if panel is None:
        return
    namen = sorted(vf.namen(panel.maschine, a) for a in panel.zeilen)
    h.pruefe(namen == ["Spindelachse", "X1", "Y1", "Z1"], f"Achsen: {namen}")
    h.bild("6_verfahren_grundstellung")
    for name, stellung in (("X1", 200), ("Y1", -100), ("Z1", -80)):
        achse = panel.achse(name)
        _regler, feld = panel.zeilen[achse]
        feld.setValue(stellung)
        yield 300
        ist = vf.gelenkstellung(achse.gelenk, achse.art)
        h.pruefe(abs(ist - stellung) < 1e-6, f"{name} steht auf {ist} statt {stellung}")
    h.bild("7_verfahren_x200_y-100_z-80")
    panel.reject()
    yield 500

    # Dann merkt sich die Auswahl die 3-Achs-Fräse – so steht sie beim nächsten Mal dort.
    h.pruefe(beispielmaschine.zuletzt_gewaehlt() == beispielmaschine.FRAESE_3, "nicht gemerkt")

    # Alle fünf als Bild: je Bauart die Maschine schräg von vorn.
    ordner = os.environ["CAMADDON_AUSGABE"]
    zeilen = (len(beispielmaschine.ARTEN) + SPALTEN - 1) // SPALTEN
    uebersicht = QtGui.QImage(
        SPALTEN * BILD_B, zeilen * (BILD_H + BESCHRIFTUNG), QtGui.QImage.Format_RGB32
    )
    uebersicht.fill(QtGui.QColor("white"))
    maler = QtGui.QPainter(uebersicht)
    for i, art in enumerate(beispielmaschine.ARTEN):
        beispielmaschine.lade(art)
        yield 800
        pfad = os.path.join(ordner, f"maschine_{art}.png")
        Gui.ActiveDocument.ActiveView.saveImage(pfad, BILD_B, BILD_H, "White")
        bild = QtGui.QImage(pfad)
        h.pruefe(not bild.isNull(), f"{art}: kein Bild")
        x, y = (i % SPALTEN) * BILD_B, (i // SPALTEN) * (BILD_H + BESCHRIFTUNG)
        maler.drawImage(QtCore.QPointF(x, y), bild)
        maler.drawText(
            QtCore.QRectF(x, y + BILD_H, BILD_B, BESCHRIFTUNG),
            QtCore.Qt.AlignCenter,
            beispielmaschine.titel(art),
        )
        os.remove(pfad)
    maler.end()
    uebersicht.save(os.path.join(ordner, "8_alle_beispielmaschinen.png"))
    # Die Szenarien schließen ihre Dokumente – sonst fragt FreeCAD beim Beenden.
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
