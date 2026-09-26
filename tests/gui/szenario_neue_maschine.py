# „Neue Maschine …“ (W-001, Stufe 3b, Schritt 7): Der Knopf in der
# Werkzeugleiste öffnet die Auswahl der Bauarten. Bei der 3-Achs-Fräse steht
# „feste Maße“, bei der Drehmaschine die Maße, vorbelegt wie das Beispiel.
# Ein Weg Y von 0 bis 0 geht nicht: Eine rote Zeile sagt warum, der Dialog
# bleibt offen. Mit Name „Meine Drehmaschine“, Bettneigung 30°, Y schräg um
# 30°, Weg X −80 … 120 mm, 8 Plätzen und 4000 U/min entsteht ein neues
# Dokument; „Maschine bearbeiten“ öffnet sich mit der schrägen Achse
# „Y1 – gleicht aus: X1, 30,0°“ und acht Revolverplätzen.
import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_maschine, gui_neue_maschine
    from camaddon import maschine as m

    # Der Knopf hängt in der Werkzeugleiste.
    Gui.activateWorkbench("AssemblyWorkbench")
    yield 500
    leiste = next(
        (
            t
            for t in Gui.getMainWindow().findChildren(QtGui.QToolBar)
            if t.objectName() == "CAM-Addon" or t.windowTitle() == "CAM-Addon"
        ),
        None,
    )
    texte = [a.text() for a in leiste.actions()] if leiste is not None else []
    h.pruefe("Neue Maschine …" in texte, f"Knopf fehlt in der Werkzeugleiste: {texte}")

    # Die Auswahl blockiert, bis sie beantwortet ist.
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_NeueMaschine"))
    yield from h.warte_auf(lambda: gui_neue_maschine.NeueMaschineDialog.offen is not None)
    d = gui_neue_maschine.NeueMaschineDialog.offen
    h.pruefe(d is not None, "„Neue Maschine …“ öffnet keinen Dialog")
    if d is None:
        return
    h.pruefe(d.windowTitle() == "Neue Maschine", f"Titel: {d.windowTitle()!r}")

    # 3-Achs-Fräse: feste Maße.
    d.liste.setCurrentRow(beispielmaschine.ARTEN.index(beispielmaschine.FRAESE_3))
    yield 200
    h.pruefe(d.fest.isVisible() and not d.masse_bereich.isVisible(), "Fräse: Maße sichtbar")
    h.pruefe(d.masse() is None, "Fräse: Maße statt None")
    h.bild("1_fraese_feste_masse", d)

    # Drehmaschine: die Maße, vorbelegt wie das Beispiel.
    d.liste.setCurrentRow(beispielmaschine.ARTEN.index(beispielmaschine.DREHMASCHINE))
    yield 200
    h.pruefe(d.masse_bereich.isVisible() and not d.fest.isVisible(), "Drehmaschine: keine Maße")
    h.pruefe(d.masse() == beispielmaschine.DrehmaschinenMasse(), f"Vorbelegung: {d.masse()}")
    h.bild("2_drehmaschine_vorgabe", d)

    # Weg Y 0 … 0: geht nicht, der Dialog bleibt offen.
    von_y, bis_y = d.felder_weg["Y"]
    von_y.setValue(0)
    bis_y.setValue(0)
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 300
    h.pruefe(gui_neue_maschine.NeueMaschineDialog.offen is d, "Dialog mit Weg 0 … 0 zu")
    h.pruefe(
        d.fehler.isVisible() and d.fehler.text().startswith("Jeder Weg braucht ein Stück"),
        f"rote Zeile: {d.fehler.text()!r}",
    )
    h.bild("3_weg_ungueltig", d)

    # Eigene Maße eintragen und bauen; die rote Zeile geht beim ersten Ändern weg.
    von_y.setValue(-40)
    bis_y.setValue(50)
    h.pruefe(not d.fehler.isVisible(), "rote Zeile bleibt nach dem Ändern")
    d.feld_name.setText("Meine Drehmaschine")
    d.feld_bett.setValue(30)
    d.feld_y_winkel.setValue(30)
    von_x, bis_x = d.felder_weg["X"]
    von_x.setValue(-80)
    bis_x.setValue(120)
    d.feld_plaetze.setValue(8)
    d.feld_drehzahl.setValue(4000)
    yield 200
    h.bild("4_eigene_masse", d)
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield from h.warte_auf(lambda: gui_maschine.MaschinenPanel.offen is not None)
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(panel is not None, "„Maschine bearbeiten“ öffnet sich nicht nach dem Bauen")
    doc = FreeCAD.ActiveDocument
    h.pruefe(
        doc is not None and doc.Label == "Meine Drehmaschine",
        f"Dokument: {doc.Label if doc else None}",
    )
    if panel is None:
        return
    zeilen = [
        panel.transformationen.topLevelItem(i).text(0)
        for i in range(panel.transformationen.topLevelItemCount())
    ]
    h.pruefe(zeilen == ["Schräge Achse Y1 – gleicht aus: X1, 30,0°"], f"Transformation: {zeilen}")
    kopf = panel.aufnahmen.topLevelItem(0).text(0) if panel.aufnahmen.topLevelItemCount() else ""
    h.pruefe(kopf.endswith("8 Plätze"), f"Revolver: {kopf!r}")
    h.pruefe(panel.maschine.Label == "Meine Drehmaschine", f"Maschine: {panel.maschine.Label}")
    s1 = next(b for b in m.betriebsarten(panel.maschine) if b.NcName == "S1")
    h.pruefe(s1.Drehzahl == 4000, f"S1: {s1.Drehzahl}")
    Gui.SendMsgToActiveView("ViewFit")
    yield 300
    h.bild("5_gebaut_bearbeiten")
    panel.reject()
    yield 500
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
