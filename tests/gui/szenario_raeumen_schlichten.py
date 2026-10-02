# „Schlichten danach“ (Spezifikation Strategien 12.4, Option A – Manuel, 2026-10-02: „genau so“;
# vorher zwei Haken im Räumen, W-010): Manuels Block 50 × 50 × 20 mit Zapfen Ø 10, 10 hoch; T1
# der Standardfräser. Die Oberseite anklicken – Räumen gewinnt; „Schlichten danach“ steht darunter,
# ohne Haken. Im Räumen 0,5 mm Aufmaß am Boden, dann „Schlichten danach“ mit Messstopp anhaken:
# vorgewählt T1 mit dem Einsatz „Schlichten“, das Ergebnis „→ Boden (0,5 mm) und 1 Wand (0,3 mm),
# etwa … – davor ein Messstopp“. „Anlegen“: Räumen, Messstopp (M5, M0, M3 mit der Drehzahl des
# Schlichtens), Boden schlichten (ein Räumen ohne Aufmaß am Boden), Wände schlichten (die Kontur
# am Zapfen mit Aufmaß und Breite 0,3). FreeCADs LinuxCNC-Postprozessor schreibt M0 zwischen
# Schruppen und Schlichten. „Auf der Maschine prüfen“: am Ende nirgends ins Teil und nichts stehen
# geblieben – auch keine Stufe am Boden.
import importlib

import FreeCAD
import FreeCADGui as Gui
import numpy as np
import Part

V = FreeCAD.Vector


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from PySide import QtCore

    from camaddon import beispielmaschine, gui_bearbeitung, gui_reichweite
    from camaddon import hoehenfeld as hf
    from camaddon import kontur as ko
    from camaddon import messstopp as ms
    from camaddon import raeumen as ra
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    wz.Bibliothek([t1]).speichern()

    doc = FreeCAD.newDocument("ZapfenSchlichten")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = (
        Part.makeBox(50, 50, 20).fuse(Part.makeCylinder(5, 10, V(25, 25, 20)))
    ).removeSplitter()
    doc.recompute()
    flaeche = next(e.name for e in hf.ebenen_oben(teil.Shape) if abs(e.z - 20.0) < 1e-6)
    zapfen = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if "Cylinder" in str(f.Surface) and f.BoundBox.ZMin > 19.9
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, flaeche)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    raeumen, danach = panel.raeumen, panel.schlichten_danach
    yield from h.warte_auf(lambda: raeumen.vorschau is not None, 60000)
    yield 500
    h.pruefe(raeumen.aktiv(), "Räumen nicht angehakt")
    h.pruefe(danach.moeglich and not danach.aktiv(), "Schlichten danach: nicht da oder angehakt")
    h.pruefe("wandschlichten" not in raeumen.haken_felder, "die alten Haken im Räumen")
    panel.knopf_weiter.click()
    panel.knopf_weiter.click()
    yield 300
    raeumen.felder["aufmass_boden"].setText("0,5")
    danach.haken.setChecked(True)  # wie ein Klick: von Hand
    danach.haken_felder["messstopp"].setChecked(True)
    yield 1000
    yield from h.warte_auf(lambda: danach.vorschau is not None and raeumen.vorschau is not None)
    yield 500
    h.pruefe(
        danach.fraeser() is not None and danach.fraeser().nummer == 1, "Schlichten danach: nicht T1"
    )
    h.pruefe(
        danach.einsatz() is not None and danach.einsatz().art == wz.SCHLICHTEN,
        f"Schlichten danach: Einsatz {getattr(danach.einsatz(), 'art', None)}",
    )
    text = danach.ergebnis.text()
    h.pruefe(
        text.startswith("→ Boden (0,5 mm) und 1 Wand (0,3 mm), etwa ")
        and text.endswith("– davor ein Messstopp"),
        f"Ergebnis: {text!r}",
    )
    h.pruefe(not danach.hinweis.text(), f"rot: {danach.hinweis.text()!r}")
    h.bild("1_schlichten_danach", panel.form)

    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 1000
    job = panel.job
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    print(ascii(f"Operationen: {namen}"))
    h.pruefe(len(ops) == 4, f"Operationen: {namen}")
    if len(ops) != 4:
        return
    roh, halt, boden, fein = ops
    h.pruefe(
        ra.ist_raeumen(roh) and abs(float(roh.AufmassBoden) - 0.5) < 1e-6,
        f"zuerst nicht Räumen mit 0,5 am Boden: {roh.Label}",
    )
    h.pruefe(ms.ist_messstopp(halt), f"dann kein Messstopp: {halt.Label}")
    zeilen = list(halt.Gcode)
    h.pruefe(
        zeilen[2:4] == ["M5", "M0"] and zeilen[1].startswith("G0 Z"),
        f"Messstopp: {zeilen}",
    )
    h.pruefe(halt.ToolController is roh.ToolController, "Messstopp mit einem anderen Controller")
    h.pruefe(
        ra.ist_raeumen(boden)
        and float(boden.AufmassBoden) == 0.0
        and abs(float(boden.Aufmass) - 0.3) < 1e-6
        and list(boden.Flaechen) == [flaeche]
        and boden.Label.startswith("Boden schlichten T1"),
        f"Boden: {boden.Label!r}, {boden.AufmassBoden}, {boden.Aufmass}, {list(boden.Flaechen)}",
    )
    h.pruefe(
        ko.ist_kontur(fein) and list(fein.Flaechen) == [zapfen], f"Schlichten: {fein.Flaechen}"
    )
    h.pruefe(
        abs(float(fein.Aufmass) - 0.3) < 1e-6 and abs(float(fein.Breite) - 0.3) < 1e-6,
        f"Schlichten: Aufmaß {fein.Aufmass}, Breite {fein.Breite}",
    )
    h.pruefe(
        boden.ToolController is fein.ToolController
        and fein.ToolController is not roh.ToolController,
        "Boden und Wände: nicht derselbe Controller „Schlichten“",
    )
    h.pruefe(
        zeilen[4] == f"M3 S{round(float(fein.ToolController.SpindleSpeed))}",
        f"Wiederanlauf: {zeilen[4:]}",
    )
    h.pruefe(fein.Label.startswith("Wände schlichten T1"), f"Name: {fein.Label!r}")
    # Im Programm: M0 zwischen Räumen und Schlichten, danach wieder M3.
    post = None
    for name in ("linuxcnc_legacy_post", "linuxcnc_post"):
        try:
            modul = importlib.import_module(f"Path.Post.scripts.{name}")
        except ImportError:
            continue
        if hasattr(modul, "export"):
            post = modul
            break
    h.pruefe(post is not None, "kein LinuxCNC-Postprozessor")
    if post is not None:
        text = post.export(ops, "-", "--no-show-editor") or ""
        programm = [z.strip() for z in text.splitlines()]
        m0 = next((i for i, z in enumerate(programm) if z.split()[:1] == ["M0"]), None)
        h.pruefe(m0 is not None, "kein M0 im Programm")
        if m0 is not None:
            danach = programm[m0 + 1 :]
            h.pruefe(
                any(z.startswith("M3") for z in danach[:3]),
                f"nach M0 keine Spindel: {danach[:3]}",
            )
            vorher = [z for z in programm[:m0] if z.startswith("G1")]
            nachher = [z for z in danach if z.startswith(("G1", "G2", "G3"))]
            h.pruefe(bool(vorher) and bool(nachher), "M0 nicht zwischen Räumen und Schlichten")
    yield 500
    h.bild("2_angelegt")

    # --- Auf der Maschine prüfen: nichts stehen geblieben, keine Stufe am Boden --------------
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
    spieler.setze_zeit(spieler.abfahrt.dauer)
    yield from h.warte_auf(lambda: spieler.rest.text().startswith("Am Ende"), 300000)
    rest = spieler.rest.text()
    h.pruefe("nirgends ins Teil" in rest, f"{rest!r}")
    # Auf dem Boden – bis an die Wand des Zapfens – bleibt nichts stehen, auch keine Stufe. (Oben
    # auf dem Zapfen bleibt der Millimeter Rohteil: Den hat niemand angeklickt.)
    abtrag = pruef.bild.abtrag
    vergleich = abtrag.vergleich()
    teil = np.where(np.isfinite(abtrag._teil), abtrag._teil, np.nan)
    boden = np.isfinite(teil) & (np.abs(teil - np.nanmin(teil)) < 0.01)
    rest = np.nan_to_num(vergleich.rest, nan=0.0)
    h.pruefe(
        boden.sum() > 1000 and float(rest[boden].max()) < 0.1,
        f"auf dem Boden stehen geblieben: bis {float(rest[boden].max()):.2f} mm",
    )
    Gui.SendMsgToActiveView("ViewFit")
    spieler.knopf_hinsehen.click()
    yield 800
    h.bild("3_pruefen_farben")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
