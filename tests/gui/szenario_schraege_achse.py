# Schräge Achse in „Maschine bearbeiten“ (W-001, Stufe 3b, Schritte 1 und 2):
# An der Beispiel-Drehmaschine (Y rechtwinklig zu X) legt „+ Schräge Achse“
# den Eintrag „Schräge Achse Y1 – gleicht aus: X1, 0,0°“ an; die Felder zeigen
# Y1 und X1, die Namen im Programm Y und X, den Winkel aus der Baugruppe und
# ein Beispiel. Winkel 30 eingetragen: Die Y-Führung dreht sich, die Teile
# bleiben, und Eintrag und Beispiel zeigen 30,0° bzw. „Y1 +11,5 mm, X1
# −5,8 mm“; 95 lehnt ein Satz am Feld ab. Abbrechen stellt die Führung
# zurück. Wählt man Z1 als schräge Achse, wandert der Name im Programm mit
# (Z). Dann dieselbe Maschine mit einer schon um 30° gekippten Y-Führung:
# Der Eintrag zeigt gleich 30,0°. Entfernen lässt die graue Zeile „keine …“
# zurück.
import os
import sys

import FreeCAD
import FreeCADGui as Gui
from PySide import QtGui

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def zeilen(baum):
    return [baum.topLevelItem(i).text(0) for i in range(baum.topLevelItemCount())]


def texte(kasten):
    """Alle Beschriftungen im Kasten der gewählten Zeile, von oben nach unten."""
    return [w.text() for w in kasten.findChildren(QtGui.QLabel)]


def winkelfeld(panel):
    """Das Feld „Winkel“ – das dritte Textfeld nach den beiden Namen im Programm."""
    felder = panel.details.findChildren(QtGui.QLineEdit)
    return felder[2] if len(felder) > 2 else QtGui.QLineEdit()


def oeffnen(h, asm):
    from camaddon import gui_maschine

    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(asm)
    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield from h.warte_auf(lambda: gui_maschine.MaschinenPanel.offen is not None)


def zeigen(h, panel):
    """Die Liste „Transformationen“ ins Bild rollen."""
    bereich = next(
        (
            b
            for b in Gui.getMainWindow().findChildren(QtGui.QScrollArea)
            if b.isAncestorOf(panel.form)
        ),
        None,
    )
    if bereich is not None:
        bereich.ensureWidgetVisible(panel.details, 0, 0)
        bereich.ensureWidgetVisible(panel.transformationen, 0, 0)
    yield 300


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import beispielmaschinen

    from camaddon import beispielmaschine, gui_maschine
    from camaddon import kette as kette_modul
    from camaddon import maschine as m
    from camaddon import verfahren as vf

    # --- Y rechtwinklig: der Eintrag zeigt 0,0° -----------------------------------
    asm, ma = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield 800
    yield from oeffnen(h, asm)
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(panel is not None, "„Maschine bearbeiten“ geht nicht auf")
    if panel is None:
        return
    h.pruefe(
        zeilen(panel.transformationen) == ["keine – nur nötig, wenn die Steuerung umrechnet"],
        f"leer: {zeilen(panel.transformationen)}",
    )
    h.pruefe(panel.knopf_schraeg.isEnabled(), "„+ Schräge Achse“ ist nicht bedienbar")
    h.pruefe(not panel.knopf_trafo_weg.isEnabled(), "„Entfernen“ ohne Auswahl bedienbar")
    panel.knopf_schraeg.click()
    yield 300
    h.pruefe(
        zeilen(panel.transformationen) == ["Schräge Achse Y1 – gleicht aus: X1, 0,0°"],
        f"Eintrag: {zeilen(panel.transformationen)}",
    )
    trafos = m.transformationen(ma)
    h.pruefe(len(trafos) == 1, f"{len(trafos)} Transformationen im Maschinenobjekt")
    beschriftungen = texte(panel.details)
    for erwartet in (
        "Schräge Achse:",
        "Gleicht aus:",
        "Y1 heißt im Programm:",
        "X1 heißt im Programm:",
        "Beispiel: Y +10,0 mm → Y1 +10,0 mm, X1 0,0 mm",
    ):
        h.pruefe(erwartet in beschriftungen, f"fehlt im Kasten: {erwartet!r} – {beschriftungen}")
    listen = panel.details.findChildren(QtGui.QComboBox)
    h.pruefe(
        [liste.currentText() for liste in listen] == ["Y1", "X1"],
        f"Auswahl: {[liste.currentText() for liste in listen]}",
    )
    felder = [f.text() for f in panel.details.findChildren(QtGui.QLineEdit)]
    h.pruefe(felder == ["Y", "X", "0,0"], f"Namen im Programm und Winkel: {felder}")
    h.pruefe(panel.knopf_trafo_weg.isEnabled(), "„Entfernen“ bei gewähltem Eintrag nicht bedienbar")
    yield from zeigen(h, panel)
    h.bild("1_rechtwinklig")

    # Winkel 30 eintragen: Die Führung dreht sich, die Teile bleiben, wo sie sind.
    teile = {o.Label: o for o in asm.Document.Objects if o.TypeId in ("Part::Box", "App::Part")}
    lagen = {n: FreeCAD.Placement(o.Placement) for n, o in teile.items()}
    winkelfeld(panel).setText("30")
    winkelfeld(panel).editingFinished.emit()
    yield 600
    h.pruefe(
        zeilen(panel.transformationen) == ["Schräge Achse Y1 – gleicht aus: X1, 30,0°"],
        f"nach 30 eingetragen: {zeilen(panel.transformationen)}",
    )
    h.pruefe(winkelfeld(panel).text() == "30,0", f"Feld: {winkelfeld(panel).text()}")
    beschriftungen = texte(panel.details)
    h.pruefe(
        "Beispiel: Y +10,0 mm → Y1 +11,5 mm, X1 −5,8 mm" in beschriftungen,
        f"Beispiel nach 30 eingetragen: {beschriftungen}",
    )
    bewegt = [n for n, o in teile.items() if not o.Placement.isSame(lagen[n], 1e-6)]
    h.pruefe(not bewegt, f"30 eingetragen, bewegt: {bewegt}")
    yield from zeigen(h, panel)
    h.bild("2_winkel_30_eingetragen")
    # 95 geht nicht: ein Satz am Feld, das Feld zeigt wieder 30,0.
    winkelfeld(panel).setText("95")
    winkelfeld(panel).editingFinished.emit()
    yield 300
    rot = [w for w in panel.details.findChildren(QtGui.QLabel) if w.text().startswith("Höchstens")]
    h.pruefe(bool(rot) and rot[0].isVisible(), "kein Satz bei 95°")
    h.pruefe(winkelfeld(panel).text() == "30,0", f"Feld nach 95: {winkelfeld(panel).text()}")
    h.bild("3_winkel_95_abgelehnt")

    # Z1 als schräge Achse: Der Name im Programm wandert mit (Y → Z). Die
    # Felder sind nach dem Eintragen neu – also neu holen.
    listen = panel.details.findChildren(QtGui.QComboBox)
    listen[0].setCurrentIndex(listen[0].findText("Z1"))
    yield 400
    h.pruefe(trafos and trafos[0].NameSchraeg == "Z", f"Name: {trafos[0].NameSchraeg}")
    h.pruefe(
        zeilen(panel.transformationen)[0].startswith("Schräge Achse Z1 – gleicht aus: X1, "),
        f"nach Z1: {zeilen(panel.transformationen)}",
    )
    panel.reject()  # verwirft den Eintrag und stellt die Führung zurück
    yield 500
    h.pruefe(not m.transformationen(ma), "Abbrechen verwirft den Eintrag nicht")
    kette = kette_modul.lies_kette(asm)
    achsen = {a.gelenk.Label: a for a in kette.achsen}
    quer = vf.plusrichtung(achsen["Y"]).dot(vf.plusrichtung(achsen["X"]))
    h.pruefe(abs(quer) < 1e-9, f"Abbrechen stellt die Führung nicht zurück ({quer})")

    # --- Y-Führung 30° schräg: 30,0° und das Beispiel ----------------------------------
    kette = kette_modul.lies_kette(asm)
    achsen = {a.gelenk.Label: a for a in kette.achsen}
    beispielmaschinen.kippe_fuehrung(achsen["Y"], 30, zu=vf.plusrichtung(achsen["X"]))
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    yield from oeffnen(h, asm)
    panel = gui_maschine.MaschinenPanel.offen
    if panel is None:
        return
    panel.knopf_schraeg.click()
    yield 300
    h.pruefe(
        zeilen(panel.transformationen) == ["Schräge Achse Y1 – gleicht aus: X1, 30,0°"],
        f"Eintrag bei 30°: {zeilen(panel.transformationen)}",
    )
    beschriftungen = texte(panel.details)
    erwartet = "Beispiel: Y +10,0 mm → Y1 +11,5 mm, X1 −5,8 mm"
    h.pruefe(erwartet in beschriftungen, f"fehlt bei 30°: {erwartet!r} – {beschriftungen}")
    h.pruefe(winkelfeld(panel).text() == "30,0", f"Feld bei 30°: {winkelfeld(panel).text()}")
    # Das Hervorheben in der 3D-Ansicht: beide Schlitten leuchten auf.
    panel.zeige(("transformation", m.transformationen(ma)[0]))
    yield 300
    yield from zeigen(h, panel)
    h.bild("4_schraeg_gebaut_30")

    # Entfernen: die graue Zeile ist wieder da, das Objekt weg.
    panel.transformationen.setCurrentItem(panel.transformationen.topLevelItem(0))
    panel.knopf_trafo_weg.click()
    yield 300
    h.pruefe(not m.transformationen(ma), "Entfernen lässt das Objekt stehen")
    h.pruefe(
        zeilen(panel.transformationen) == ["keine – nur nötig, wenn die Steuerung umrechnet"],
        f"nach Entfernen: {zeilen(panel.transformationen)}",
    )
    # Hilfe (?) zu den Transformationen.
    knopf = panel.form.findChild(QtGui.QToolButton, "hilfe_transformationen")
    h.pruefe(knopf is not None, "Hilfe-Knopf der Transformationen fehlt")
    if knopf is not None:
        knopf.click()
        yield 500
        fenster = [
            w
            for w in QtGui.QApplication.topLevelWidgets()
            if w.isVisible() and w.windowTitle().startswith("Hilfe")
        ]
        h.pruefe(bool(fenster), "Hilfe öffnet sich nicht")
        if fenster:
            h.bild("5_hilfe", fenster[0])
            fenster[0].close()
    panel.reject()
    yield 500
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
