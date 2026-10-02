# „Bearbeitung (Fräsen)“ an einer Sackbohrung, wie FreeCADs PartDesign-Bohrung sie zeichnet: Block
# 60 × 40 × 20, darin eine Bohrung M10 (ohne gezeichnetes Gewinde: Ø 8,5), 15 tief, mit der
# 118°-Spitze darunter. T1 der Standardfräser Ø 12, T2 ein Bohrer Ø 8,5 mit 118°, T7 ein
# Gewindefräser Ø 8 mit Steigung 1,5 und einem Zahn. Die Wand anklicken: In der Liste „Bohrung
# Ø 8,5, Grund 5, Spitze 118°“ – keine durchgehende (die Spitze ist Luft auf der Achse, am Rand
# steht der Boden). Bohren mit T2 bekommt den Haken – seine Spitze ist die des Modells; Gewinde
# fräsen von Hand an: „→ 1 × M10x1.5, … Umläufe“. „Anlegen“: „Bohren T2“ bohrt bis z 2,45 (die
# Spitze), „Gewinde fräsen T7“ bleibt über z 5,2 (0,2 über dem Grund der Wand). „Auf der Maschine
# prüfen“: am Ende nirgends ins Teil.
import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtCore

V = FreeCAD.Vector


def _teil_aus_partdesign():
    """Die Form eines PartDesign-Körpers mit einer Bohrung M10, 15 tief, Spitze 118°."""
    hilfe = FreeCAD.newDocument("PartDesignHilfe")
    koerper = hilfe.addObject("PartDesign::Body", "Body")
    quader = hilfe.addObject("PartDesign::AdditiveBox", "Box")
    koerper.addObject(quader)
    quader.Length, quader.Width, quader.Height = 60, 40, 20
    hilfe.recompute()
    skizze = hilfe.addObject("Sketcher::SketchObject", "Sketch")
    koerper.addObject(skizze)
    skizze.AttachmentSupport = [(quader, "Face6")]
    skizze.MapMode = "FlatFace"
    skizze.addGeometry(Part.Circle(V(30, 20, 0), V(0, 0, 1), 4), False)
    hilfe.recompute()
    bohrung = hilfe.addObject("PartDesign::Hole", "Hole")
    koerper.addObject(bohrung)
    bohrung.Profile = skizze
    bohrung.ThreadType = "ISOMetricProfile"
    bohrung.ThreadSize = "M10x1.5"
    bohrung.Threaded = True
    bohrung.ModelThread = False
    bohrung.DepthType = "Dimension"
    bohrung.Depth = 15
    bohrung.DrillPoint = "Angled"
    bohrung.DrillPointAngle = 118
    hilfe.recompute()
    form = koerper.Shape.copy()
    FreeCAD.closeDocument(hilfe.Name)
    return form


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
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    t2 = wz.Werkzeug(
        nummer=2,
        name="HSS 8.5",
        art=wz.BOHRER,
        durchmesser=8.5,
        schneiden=2,
        schneidenlaenge=60.0,
        spitzenwinkel=118.0,
        schneidstoff=wz.HSS,
    )
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.08)]
    t7 = wz.Werkzeug(
        nummer=7,
        name="GF 8 P1.5",
        art=wz.GEWINDEFRAESER,
        durchmesser=8.0,
        schneiden=3,
        steigung=1.5,
        schneidenlaenge=1.3,
        hals_d=6.0,
        hals_laenge=25.0,
        schaft=8.0,
        schneidstoff=wz.VHM,
    )
    t7.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.GEWINDEFRAESEN, vc=80.0, fz=0.05)]
    wz.Bibliothek([t1, t2, t7]).speichern()

    form = _teil_aus_partdesign()
    doc = FreeCAD.newDocument("Sackgewinde")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = form
    doc.recompute()
    loecher = bb.bohrungen(teil.Shape)
    h.pruefe(
        len(loecher) == 1 and not loecher[0].durch and abs(loecher[0].spitze - 118.0) < 0.01,
        f"Bohrung: {loecher}",
    )
    if not loecher:
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, loecher[0].name)
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
    bohren, fraesen = panel.bohren, panel.gewindefraesen
    yield from h.warte_auf(lambda: bohren.vorschau is not None, 60000)
    yield 1500
    zeilen = [panel.flaechen_liste.item(i).text() for i in range(panel.flaechen_liste.count())]
    h.pruefe(any("Bohrung Ø 8,5, Grund 5, Spitze 118°" in z for z in zeilen), f"Liste: {zeilen}")
    h.pruefe(bohren.aktiv() and bohren.fraeser().nummer == 2, "Bohren: nicht an oder nicht T2")
    h.pruefe(fraesen.moeglich and not fraesen.aktiv(), "Gewinde fräsen: nicht möglich oder an")
    fraesen.haken.setChecked(True)
    yield from h.warte_auf(lambda: fraesen.vorschau is not None, 60000)
    yield 300
    text = fraesen.ergebnis.text()
    h.pruefe(text.startswith("→ 1 × M10x1.5, ") and " – " not in text, f"Gewinde: {text!r}")
    h.pruefe(not fraesen.hinweis.text(), f"rot: {fraesen.hinweis.text()!r}")
    h.bild("1_sackgewinde", panel.form)

    # --- Anlegen: Bohren bis zur Spitze, Gewinde über dem Grund ------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 2500
    ops = list(job.Operations.Group)
    h.pruefe(
        [o.Label for o in ops] == ["Bohren T2", "Gewinde fräsen T7"],
        f"Operationen: {[o.Label for o in ops]}",
    )
    if len(ops) < 2:
        return
    tiefen = [round(c.Parameters["Z"], 2) for c in ops[0].Path.Commands if c.Name == "G81"]
    h.pruefe(tiefen == [2.45], f"Bohren bis {tiefen}")
    tiefste = min(c.Parameters["Z"] for c in ops[1].Path.Commands if "Z" in c.Parameters)
    h.pruefe(abs(tiefste - 5.2) < 1e-6, f"Gewinde fräsen am tiefsten {tiefste}")
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
