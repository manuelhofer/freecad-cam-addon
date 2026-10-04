# Schwenkdatensatz und Richtungsbezug (D-1, D-2; Manuel, 2026-10-04: „das muss je nach Maschine
# entschieden werden … das ist ja in der Maschinenkonfiguration eingerichtet“): die 5-Achs-
# Beispielmaschine Kopf/Tisch → „Maschine bearbeiten“: unter „Home und Werkzeugwechsel“ die Zeilen
# „Schwenkdatensatz“ (leer: der einzige der Maschine) und „Richtung bezogen auf“ (Rundachse 1).
# „TC1“ eingetippt und Rundachse 2 gewählt, steht beides an der Maschine. An der 3-Achs-Fräse
# fehlen die Zeilen.
import FreeCADGui as Gui


def tippen(widget, text):
    widget.setText(text)
    widget.editingFinished.emit()


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import FreeCAD

    from camaddon import beispielmaschine, gui_maschine
    from camaddon import maschine as m

    for bauplan, mit_zeilen in (
        (beispielmaschine.fuenfachs_kopf_tisch, True),
        (beispielmaschine.fraesmaschine, False),
    ):
        asm, ma = bauplan()
        Gui.activateWorkbench("AssemblyWorkbench")
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(asm)
        yield 500
        Gui.runCommand("CamAddon_MaschineBearbeiten")
        yield 1500
        panel = gui_maschine.MaschinenPanel.offen
        h.pruefe(panel is not None, f"{bauplan.__name__}: Dialog öffnet sich nicht")
        if panel is None:
            return
        feld, wahl = panel.feld_schwenkdatensatz, panel.wahl_schwenk_bezug
        h.pruefe(
            (feld is not None and wahl is not None) == mit_zeilen, f"{bauplan.__name__}: Zeilen"
        )
        if mit_zeilen and feld is not None and wahl is not None:
            h.pruefe(
                feld.text() == "" and feld.placeholderText() == "leer: der einzige der Maschine",
                f"Schwenkdatensatz: {feld.text()!r} {feld.placeholderText()!r}",
            )
            h.pruefe(wahl.currentData() == 1, f"Bezug vorbelegt: {wahl.currentData()}")
            tippen(feld, "TC1")
            yield 200
            wahl.setCurrentIndex(wahl.findData(2))
            yield 300
            h.pruefe(
                m.schwenkdatensatz(panel.maschine) == "TC1"
                and m.schwenk_bezug(panel.maschine) == 2,
                f"an der Maschine: {m.schwenkdatensatz(panel.maschine)!r}, "
                f"{m.schwenk_bezug(panel.maschine)}",
            )
            h.bild("1_schwenkdatensatz", panel.form)
        panel.reject()
        yield 500
        FreeCAD.closeDocument(asm.Document.Name)
        yield 300
