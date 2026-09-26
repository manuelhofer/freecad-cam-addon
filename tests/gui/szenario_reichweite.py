# „Auf der Maschine prüfen“ (W-001, Stufe 4a): Die Beispiel-Fräse in einem
# Dokument, ein Teil mit Job und eigener Bahn in einem zweiten. Den Job wählen,
# den Knopf drücken: Das Fenster öffnet sich im Dokument der Maschine – „Alle
# Achsen bleiben in ihren Grenzen.“ in Grün, darunter grau, was X1, Y1 und Z1
# brauchen, und dass mit der Länge des CAM-Werkzeugs gerechnet wurde. In den
# Feldern des Nullpunkts steht grau der Vorschlag (−50, −30, 1). X 300
# eintragen: rot „X1 fährt in „Eigene“ bis −470,00 mm, die Grenze ist
# −250,00 mm (bei X 170, Y 40, Z −5).“ Ein Klick darauf fährt die Maschine:
# X1 steht an −250. Schließen fährt alles zurück, zeigt wieder das Teil, und
# der Job merkt sich X 300; beim nächsten Öffnen steht 300 im Feld. Leeren und
# schließen – der Eintrag ist wieder weg.
import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore

BAHN = ["G0 X0 Y0 Z10", "G1 Z-5 F100", "G1 X150 Y20", "G2 X170 Y40 I0 J20", "G0 Z10"]


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import Path.Main.Job as PathJob
    import Path.Op.Custom as PathCustom

    from camaddon import beispielmaschine, gui_reichweite
    from camaddon import reichweite as rw
    from camaddon import verfahren as vf

    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 500
    teile = {o.Name: o for o in asm.Document.Objects if o.TypeId in ("Part::Box", "App::Part")}
    lagen = {n: FreeCAD.Placement(o.Placement) for n, o in teile.items()}

    def bewegt():
        return sorted(n for n, o in teile.items() if not o.Placement.isSame(lagen[n], 1e-6))

    teil = FreeCAD.newDocument("Teil")
    quader = teil.addObject("Part::Box", "Quader")
    quader.Length, quader.Width, quader.Height = 100, 60, 20
    teil.recompute()
    job = PathJob.Create("Job", [quader])
    op = PathCustom.Create("Eigene")
    op.Gcode = BAHN
    teil.recompute()
    yield 500

    def oeffnen():
        FreeCAD.setActiveDocument(teil.Name)
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(job)
        # Wie ein Benutzer: erst wählen, dann klicken. Gleich nach dem Anlegen
        # verarbeitet 1.1.3 die Auswahl im Baum verzögert und holte sonst das
        # Dokument des Jobs zurück nach vorn (ausprobiert, P-2026-09-26-85).
        yield 400
        QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))

    # --- Öffnen: alles in den Grenzen -------------------------------------------------------
    yield from oeffnen()
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None)
    panel = gui_reichweite.PruefPanel.offen
    h.pruefe(panel is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if panel is None:
        return
    yield 500
    h.pruefe(
        FreeCAD.ActiveDocument is asm.Document,
        f"Fenster nicht im Dokument der Maschine: {FreeCAD.ActiveDocument.Name}",
    )
    h.pruefe(Gui.Control.activeDialog(), "Aufgabenfenster nicht sichtbar")
    h.pruefe(
        panel.urteil.text() == "Alle Achsen bleiben in ihren Grenzen.",
        f"Urteil: {panel.urteil.text()!r}",
    )
    h.pruefe(not panel.liste.isVisible(), "Liste sichtbar ohne Überschreitung")
    platzhalter = [panel.felder_nullpunkt[a].placeholderText() for a in "XYZ"]
    h.pruefe(platzhalter == ["-50", "-30", "1"], f"Vorschlag im Feld: {platzhalter}")
    h.pruefe(
        panel.bereiche.text().startswith("Was die Bahn braucht (7 Punkte):\nX1 braucht "),
        f"Bereiche: {panel.bereiche.text()!r}",
    )
    h.pruefe(
        "gerechnet mit der Länge des CAM-Werkzeugs, 50,00 mm" in panel.hinweise.text(),
        f"Hinweise: {panel.hinweise.text()!r}",
    )
    h.bild("1_in_grenzen")

    # --- Nullpunkt X 300: X1 über die Grenze -----------------------------------------------
    panel.felder_nullpunkt["X"].setText("300")
    yield 800  # das Fenster rechnet kurz nach der Eingabe
    saetze = [panel.liste.item(i).text() for i in range(panel.liste.count())]
    h.pruefe(
        saetze
        == [
            "X1 fährt in „Eigene“ bis −470,00 mm, die Grenze ist −250,00 mm "
            "(bei X 170, Y 40, Z −5)."
        ],
        f"Überschreitungen: {saetze}",
    )
    h.pruefe(
        panel.urteil.text() == "Nicht alle Achsen bleiben in ihren Grenzen:",
        f"Urteil: {panel.urteil.text()!r}",
    )
    h.bild("2_ueber_der_grenze")

    # Ein Klick fährt die Maschine dorthin: X1 an seiner Grenze.
    panel.liste.setCurrentRow(0)
    panel.liste.itemClicked.emit(panel.liste.item(0))
    yield 500
    x1 = next(a for a in panel.pruefung.kette.achsen if vf.namen(panel.maschine, a) == "X1")
    stellung = panel.pruefung.verfahren.stellung(x1)
    h.pruefe(abs(stellung + 250) < 1e-6, f"X1 nach dem Klick: {stellung}")
    h.pruefe("Tisch" in bewegt(), f"bewegt: {bewegt()}")
    Gui.SendMsgToActiveView("ViewFit")
    yield 300
    h.bild("3_dorthin_gefahren")

    # --- Schließen: zurück, und der Job merkt sich X 300 ------------------------------------
    panel.reject()
    yield 800
    h.pruefe(gui_reichweite.PruefPanel.offen is None, "Fenster noch offen")
    h.pruefe(not bewegt(), f"Schließen fährt nicht zurück: {bewegt()}")
    h.pruefe(FreeCAD.ActiveDocument is teil, f"zurück beim Teil? {FreeCAD.ActiveDocument.Name}")
    h.pruefe(rw.eingetragener_nullpunkt(job) == {"X": 300.0}, f"{rw.eingetragener_nullpunkt(job)}")

    # Wieder öffnen: 300 steht im Feld. Leeren und schließen – der Eintrag ist weg.
    yield from oeffnen()
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None)
    panel = gui_reichweite.PruefPanel.offen
    yield 500
    h.pruefe(panel.felder_nullpunkt["X"].text() == "300", "X nicht gemerkt")
    h.pruefe(panel.liste.count() == 1, "Überschreitung nicht gleich da")
    panel.felder_nullpunkt["X"].setText("")
    yield 800
    h.pruefe(panel.urteil.text() == "Alle Achsen bleiben in ihren Grenzen.", "leer = Vorschlag")
    panel.reject()
    yield 800
    h.pruefe(rw.eingetragener_nullpunkt(job) == {}, f"{rw.eingetragener_nullpunkt(job)}")
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
