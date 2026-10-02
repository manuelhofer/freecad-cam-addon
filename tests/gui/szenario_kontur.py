# „Bearbeitung (Fräsen)“ mit der Kontur (W-006 S3e). Block 100 × 60 × 20 mit einer Tasche
# 40 × 30 (Ecken R 6), 15 tief; T1 Manuels Standardfräser Ø 12 (ae 1,5, ap 25: jede Kontur
# eine Lage). Eine Taschenwand anklicken, den Knopf drücken: Der Job entsteht, die Wand steht
# grün in der Liste („Wand, unten 5“), der Haken „Kontur“ ist gesetzt, „Planfräsen“ nicht. Die
# übrigen Wände dazu (Tasche und außen) und die Oberseite fürs Planfräsen: beide Blöcke rechnen
# ihre Vorschau. „Anlegen“: „Planfräsen T1“ und „Kontur T1“ (2 Konturen, 4 Lagen, 9 Bahnen).
# Doppelklick auf die Kontur öffnet das Fenster nur mit ihrem Block; ohne Haken „Schlichten“
# weniger Bahnen. Dann „Auf der Maschine prüfen“ mit der Beispiel-Fräse: Am Ende ist nirgends
# etwas ins Teil geschnitten und bleibt kein Rest stehen.
import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtCore

V = FreeCAD.Vector


def rund_rechteck(x0, y0, x1, y1, r, z):
    kanten = [
        Part.makeLine(V(x0 + r, y0, z), V(x1 - r, y0, z)),
        Part.makeCircle(r, V(x1 - r, y0 + r, z), V(0, 0, 1), -90, 0),
        Part.makeLine(V(x1, y0 + r, z), V(x1, y1 - r, z)),
        Part.makeCircle(r, V(x1 - r, y1 - r, z), V(0, 0, 1), 0, 90),
        Part.makeLine(V(x1 - r, y1, z), V(x0 + r, y1, z)),
        Part.makeCircle(r, V(x0 + r, y1 - r, z), V(0, 0, 1), 90, 180),
        Part.makeLine(V(x0, y1 - r, z), V(x0, y0 + r, z)),
        Part.makeCircle(r, V(x0 + r, y0 + r, z), V(0, 0, 1), 180, 270),
    ]
    return Part.Wire(kanten)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_bearbeitung, gui_reichweite
    from camaddon import kontur as ko
    from camaddon import kontur_bahn as kb
    from camaddon import planfraesen as pf
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    wz.Bibliothek([t1]).speichern()

    doc = FreeCAD.newDocument("Tasche")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    tasche = Part.Face(rund_rechteck(30, 15, 70, 45, 6, 5)).extrude(V(0, 0, 20))
    teil.Shape = Part.makeBox(100, 60, 20).cut(tasche).removeSplitter()
    doc.recompute()
    alle = [f"Face{i + 1}" for i in range(len(teil.Shape.Faces))]
    waende = kb.waende(teil.Shape, alle)
    taschenwaende = [w.name for w in waende if abs(w.z_unten - 5.0) < 1e-6]
    aussenwaende = [w.name for w in waende if abs(w.z_unten) < 1e-6]
    h.pruefe(len(taschenwaende) == 8 and len(aussenwaende) == 4, f"Wände: {len(waende)}")
    erste = next(w.name for w in waende if abs(w.z_unten - 5.0) < 1e-6 and w.kanten[0].Length > 20)
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, erste)
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
    h.pruefe(panel.flaechen() == [erste], f"Flächen: {panel.flaechen()}")
    zeile = panel.flaechen_liste.item(0).text() if panel.flaechen_liste.count() else ""
    h.pruefe(zeile.startswith(erste) and "Wand, unten 5" in zeile, f"Liste: {zeile!r}")
    kontur, plan = panel.kontur, panel.plan
    h.pruefe(kontur.aktiv() and not plan.aktiv(), "Haken: Kontur an, Planfräsen aus")
    h.pruefe(kontur.fraeser() is not None and kontur.fraeser().nummer == 1, "Kontur: Fräser T1")
    einsatz = kontur.einsatz()
    h.pruefe(einsatz is not None and einsatz.art == wz.SCHRUPPEN, "Kontur: Einsatz Schruppen")
    h.pruefe(kontur.haken_felder["schlichten"].isChecked(), "Schlichten vorgewählt")
    yield from h.warte_auf(lambda: kontur.vorschau is not None, 30000)
    h.pruefe(not kontur.hinweis.text(), f"rot: {kontur.hinweis.text()!r}")
    text = kontur.ergebnis.text()
    # Eine Taschenwand allein: neben ihr steht die ganze Tasche – viele Bahnen nebeneinander
    # (eine Schrupplage bei ap 25 und das Schlichten).
    h.pruefe(text.startswith("→ 2 Lagen, 13 Bahnen"), f"Vorschau eine Wand: {text!r}")
    h.bild("1_eine_wand", panel.form)

    # Alle Wände der Tasche und außen dazu, die Oberseite fürs Planfräsen anhaken.
    for name in taschenwaende + aussenwaende:
        if name != erste:
            panel.flaeche_umschalten(name)
    plan.haken.setChecked(True)
    yield from h.warte_auf(lambda: kontur.vorschau is not None and plan.vorschau is not None, 60000)
    h.pruefe(plan.aktiv() and kontur.aktiv(), "beide Haken")
    text = kontur.ergebnis.text()
    h.pruefe(text.startswith("→ 2 Konturen: 4 Lagen, 9 Bahnen, etwa"), f"Vorschau: {text!r}")
    text_plan = plan.ergebnis.text()
    h.pruefe(
        text_plan.startswith("→ 1 Lagen,") or text_plan.startswith("→ 1 Lage"),
        f"Planfräsen: {text_plan!r}",
    )
    h.pruefe(panel.flaechen_liste.count() == 12, f"Liste: {panel.flaechen_liste.count()} Zeilen")
    h.bild("2_alle_waende", panel.form)

    # --- Anlegen: „Planfräsen T1“ und „Kontur T1“ ------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    h.pruefe(gui_bearbeitung.BearbeitungPanel.offen is None, "Fenster nach „Anlegen“ offen")
    ops = list(job.Operations.Group)
    h.pruefe(
        len(ops) == 2 and pf.ist_planfraesen(ops[0]) and ko.ist_kontur(ops[1]),
        f"Operationen: {[o.Label for o in ops]}",
    )
    if len(ops) < 2:
        return
    op = ops[1]
    h.pruefe(op.Label == "Kontur T1", f"Name: {op.Label}")
    h.pruefe(
        (op.Konturen, op.Lagen, op.Bahnen) == (2, 4, 9), f"{op.Konturen}, {op.Lagen}, {op.Bahnen}"
    )
    h.pruefe(
        sorted(op.Flaechen) == sorted(taschenwaende + aussenwaende), f"Flächen: {list(op.Flaechen)}"
    )
    namen = {b.Name for b in op.Path.Commands}
    h.pruefe("G2" in namen and "G3" in namen, f"keine Bögen: {namen}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("3_angelegt")

    # --- Ändern: Doppelklick öffnet das Fenster nur mit dem Block Kontur ------------------
    op.ViewObject.Proxy.doubleClicked(op.ViewObject)
    yield 1000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.zu_aendern is op, "Doppelklick öffnet nichts")
    if panel is None:
        return
    kontur = panel.kontur
    h.pruefe(panel.block_zu_aendern is kontur, "beim Ändern: nicht der Block Kontur")
    h.pruefe(not panel.plan.widget.isVisible(), "beim Ändern: der Block Planfräsen ist sichtbar")
    h.pruefe(kontur.fraeser() is not None and kontur.fraeser().nummer == 1, "beim Ändern: Fräser")
    h.pruefe(not panel.rohteilfelder.isEnabled(), "Rohteil beim Ändern änderbar")
    yield from h.warte_auf(lambda: kontur.vorschau is not None, 30000)
    h.bild("4_aendern", panel.form)
    kontur.haken_felder["schlichten"].setChecked(False)
    yield from h.warte_auf(lambda: kontur.vorschau is not None, 30000)
    text = kontur.ergebnis.text()
    h.pruefe(text.startswith("→ 2 Konturen: 2 Lagen, 7 Bahnen"), f"ohne Schlichten: {text!r}")
    kontur.haken_felder["schlichten"].setChecked(True)
    yield from h.warte_auf(lambda: kontur.vorschau is not None, 30000)
    h.pruefe(panel.accept() is True, "„Übernehmen“ ging nicht")
    yield 2000
    h.pruefe(op.Schlichten is True and op.Bahnen == 9, f"nach dem Ändern: {op.Bahnen} Bahnen")

    # --- Auf der Maschine prüfen: am Ende nichts ins Teil, nichts stehen geblieben ---------
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 500
    FreeCAD.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400  # siehe szenario_reichweite.py: 1.1.3 verarbeitet die Auswahl verzögert
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruef is None:
        return
    yield 800
    spieler = pruef.abspieler
    fahrt = spieler.abfahrt
    stationen = [s for s in fahrt.stationen if not s.eilgang]
    h.pruefe(len(stationen) > 100, f"{len(stationen)} Stationen im Vorschub")
    spieler.setze_zeit(fahrt.dauer)
    yield 800
    rest = spieler.rest.text()
    h.pruefe(
        rest.startswith("Am Ende bleiben 0,00 mm") and "nirgends ins Teil" in rest,
        f"{rest!r}",
    )
    Gui.SendMsgToActiveView("ViewFit")
    spieler.knopf_hinsehen.click()
    yield 500
    h.bild("5_pruefen_farben")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
