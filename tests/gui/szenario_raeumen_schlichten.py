# Räumen mit „Wände danach schlichten“ und „Messstopp vor dem Schlichten“ (W-010, P-2026-10-02-44;
# Manuel, 2026-10-02: „Wenn ich jetzt Räumen gemacht habe und habe ein Aufmaß an den Wänden, aber
# am Boden nichts … brauch ich noch eine Möglichkeit, das Ganze zu schlichten … zwischen Schruppen
# und Schlichten eine Pause … gleich in derselben Maske“). Manuels Block 50 × 50 × 20 mit Zapfen
# Ø 10, 10 hoch; T1 der Standardfräser. Die Oberseite anklicken – Räumen gewinnt. In Schritt 3
# beide Haken: Das Ergebnis sagt „Messstopp, dann die Wände schlichten (1)“. „Anlegen“: Räumen,
# Messstopp (M5, M0, M3 mit der Drehzahl des Schlichtens), Wände schlichten – die Kontur am Zapfen
# mit Aufmaß und Breite 0,3 (nur der Zug an der Wand, mit dem Einsatz Schlichten). FreeCADs
# LinuxCNC-Postprozessor schreibt M0 zwischen die beiden, und danach läuft die Spindel wieder.
import importlib

import FreeCAD
import FreeCADGui as Gui
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

    from camaddon import gui_bearbeitung
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
    raeumen = panel.raeumen
    yield from h.warte_auf(lambda: raeumen.vorschau is not None, 60000)
    yield 500
    h.pruefe(raeumen.aktiv(), "Räumen nicht angehakt")
    schlichten = raeumen.haken_felder["wandschlichten"]
    stopp = raeumen.haken_felder["messstopp"]
    h.pruefe(not schlichten.isChecked() and not stopp.isEnabled(), "Vorgabe: ohne Schlichten")
    panel.knopf_weiter.click()
    panel.knopf_weiter.click()
    yield 300
    schlichten.setChecked(True)
    h.pruefe(stopp.isEnabled(), "Messstopp ohne Schlichten nicht wählbar")
    stopp.setChecked(True)
    yield from h.warte_auf(
        lambda: "Messstopp, dann die Wände schlichten" in raeumen.ergebnis.text()
    )
    text = raeumen.ergebnis.text()
    h.pruefe(text.endswith("(1)"), f"Ergebnis: {text!r}")
    h.bild("1_schlichten_messstopp", panel.form)

    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 1000
    job = panel.job
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    print(ascii(f"Operationen: {namen}"))
    h.pruefe(len(ops) == 3, f"Operationen: {namen}")
    if len(ops) != 3:
        return
    roh, halt, fein = ops
    h.pruefe(ra.ist_raeumen(roh), f"zuerst nicht Räumen: {roh.Label}")
    h.pruefe(ms.ist_messstopp(halt), f"dann kein Messstopp: {halt.Label}")
    zeilen = list(halt.Gcode)
    h.pruefe(
        zeilen[2:4] == ["M5", "M0"] and zeilen[1].startswith("G0 Z"),
        f"Messstopp: {zeilen}",
    )
    h.pruefe(halt.ToolController is roh.ToolController, "Messstopp mit einem anderen Controller")
    h.pruefe(
        ko.ist_kontur(fein) and list(fein.Flaechen) == [zapfen], f"Schlichten: {fein.Flaechen}"
    )
    h.pruefe(
        abs(float(fein.Aufmass) - 0.3) < 1e-6 and abs(float(fein.Breite) - 0.3) < 1e-6,
        f"Schlichten: Aufmaß {fein.Aufmass}, Breite {fein.Breite}",
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
    FreeCAD.closeDocument(doc.Name)
    yield 300
