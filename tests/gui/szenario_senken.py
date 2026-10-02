# „Bearbeitung (Fräsen)“ mit „Zentrieren“, „Bohren“ und „Senken“ (W-006 S3g): Platte 100 × 60 × 10
# mit einer Durchgangsbohrung Ø 6,6 bei (25, 30) und einer 90°-Senkung Ø 12,4 darüber (wie für
# eine Senkschraube M6); T1 der Standardfräser Ø 12, T2 ein Bohrer Ø 6,6, T5 ein NC-Anbohrer
# Ø 10 90°, T6 ein Kegelsenker Ø 20 90° mit Spitze Ø 4. Die Wand der Bohrung anklicken: Bohren
# mit T2 bekommt den Haken. Die Senkung dazu: In der Liste „Senkung Ø 12,4, 90°“, Senken mit T6
# ist vorgeschlagen – „→ 1 Stelle, 4,2 mm tief“. Zentrieren von Hand an: „→ 1 Stelle, 3,5 mm
# tief“ (oben Ø 7,0 – die Oberkante der Senkung zählt). „Anlegen“: „Zentrieren T5“, „Bohren T2“,
# „Senken T6“ in dieser Reihenfolge. „Auf der Maschine prüfen“: am Ende nirgends ins Teil.
import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtCore

V = FreeCAD.Vector


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_bearbeitung, gui_reichweite
    from camaddon import bohrung_bahn as bb
    from camaddon import senken as sk
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    t2 = wz.Werkzeug(
        nummer=2,
        name="HSS 6.6",
        art=wz.BOHRER,
        durchmesser=6.6,
        schneiden=2,
        schneidenlaenge=60.0,
        spitzenwinkel=118.0,
        schneidstoff=wz.HSS,
    )
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.08)]
    t5 = wz.Werkzeug(
        nummer=5,
        name="NC 10",
        art=wz.NC_ANBOHRER,
        durchmesser=10.0,
        schneiden=2,
        schneidenlaenge=20.0,
        spitzenwinkel=90.0,
        schneidstoff=wz.VHM,
    )
    t5.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.ZENTRIEREN, vc=60.0, fz=0.05)]
    t6 = wz.Werkzeug(
        nummer=6,
        name="KS 20",
        art=wz.KEGELSENKER,
        durchmesser=20.0,
        schneiden=3,
        spitzenwinkel=90.0,
        spitzen_d=4.0,
        schneidstoff=wz.HSS,
    )
    t6.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SENKEN, vc=20.0, fz=0.08)]
    wz.Bibliothek([t1, t2, t5, t6]).speichern()

    doc = FreeCAD.newDocument("Senken")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    form = Part.makeBox(100, 60, 10).cut(Part.makeCylinder(3.3, 10, V(25, 30, 0)))
    teil.Shape = form.cut(Part.makeCone(3.3, 6.2, 2.9, V(25, 30, 7.1))).removeSplitter()
    doc.recompute()
    bohrung = next((b.name for b in bb.bohrungen(teil.Shape)), None)
    senkung = next((s.name for s in sk.senkungen(teil.Shape)), None)
    if bohrung is None or senkung is None:
        h.pruefe(False, f"Bohrung {bohrung}, Senkung {senkung}")
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, bohrung)
    yield 500

    # Die Koordinaten dieses Szenarios gelten im Modell – nicht an der Mitte oben, die neue
    # Vorgabe (P-2026-10-02-49).
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    bohren, zentrieren, senken = panel.bohren, panel.zentrieren, panel.senken
    yield from h.warte_auf(lambda: bohren.vorschau is not None, 60000)
    h.pruefe(bohren.aktiv() and bohren.fraeser().nummer == 2, "Bohren: nicht an oder nicht T2")
    h.pruefe(zentrieren.moeglich and not zentrieren.aktiv(), "Zentrieren: nicht möglich oder an")
    h.pruefe(not senken.moeglich, "Senken ohne Senkung möglich")

    # Die Senkung dazu: in der Liste, Senken vorgeschlagen mit T6.
    panel.flaeche_umschalten(senkung)
    yield from h.warte_auf(lambda: senken.vorschau is not None, 60000)
    yield 300
    zeilen = [panel.flaechen_liste.item(i).text() for i in range(panel.flaechen_liste.count())]
    h.pruefe(any("Senkung Ø 12,4, 90°" in z for z in zeilen), f"Liste: {zeilen}")
    h.pruefe(senken.aktiv() and senken.fraeser().nummer == 6, "Senken: nicht an oder nicht T6")
    text = senken.ergebnis.text()
    h.pruefe(text.startswith("→ 1 Stelle, 4,2 mm tief, etwa "), f"Senken: {text!r}")
    h.pruefe(bohren.aktiv(), "Bohren verliert mit der Senkung den Haken")

    zentrieren.haken.setChecked(True)
    yield from h.warte_auf(lambda: zentrieren.vorschau is not None, 60000)
    yield 300
    text = zentrieren.ergebnis.text()
    h.pruefe(text.startswith("→ 1 Stelle, 3,5 mm tief, etwa "), f"Zentrieren: {text!r}")
    h.bild("1_zentrieren_bohren_senken", panel.form)

    # --- Anlegen: Zentrieren, Bohren, Senken ------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 2000
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    h.pruefe(namen == ["Zentrieren T5", "Bohren T2", "Senken T6"], f"Operationen: {namen}")
    tiefen = [round(c.Parameters["Z"], 3) for o in ops for c in o.Path.Commands if c.Name == "G81"]
    h.pruefe(len(tiefen) == 3 and tiefen[0] == 6.5 and tiefen[2] == 5.8, f"Tiefen: {tiefen}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_angelegt")

    # --- Auf der Maschine prüfen ------------------------------------------------------------
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 500
    FreeCAD.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400  # 1.1.3 verarbeitet die Auswahl verzögert
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 120000)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruef is None:
        return
    yield 1000
    spieler = pruef.abspieler
    fahrt = spieler.abfahrt
    spieler.setze_zeit(fahrt.dauer)
    yield from h.warte_auf(lambda: spieler.rest.text().startswith("Am Ende"), 240000)
    rest = spieler.rest.text()
    h.pruefe(rest.startswith("Am Ende bleiben") and "nirgends ins Teil" in rest, f"{rest!r}")
    Gui.SendMsgToActiveView("ViewFit")
    spieler.knopf_hinsehen.click()
    yield 800
    h.bild("3_pruefen_farben")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
