# Wegkippen, 5 Achsen simultan (W-015, Spezifikation Strategien 16.3 S4; Manuel, 2026-10-04: „Ja,
# bauen“): eine Kavität 50 × 50, 30 tief, Ecken R 10, unten eine Rundung R 8; die 5-Achs-Maschine
# Tisch/Tisch als zuletzt benutzte; ein Kugelfräser Ø 6 im Schrumpffutter, 27 mm Auskragung
# (senkrecht bräuchte er mit 2 mm Spiel gut 32). Die Rundungen anklicken → „Bearbeitung“: beim 3D-Schlichten die
# Haken „Anstellen“ und „Wegkippen“, frei. „Wegkippen“ setzen → „… – weggekippt reichen … mm
# Auskragung (senkrecht 32); dein Fräser steht 27 heraus“. „Anlegen“: „3D-Schlichten T3“ mit
# „Wegkippen“, je Satz eine Achse. „Auf der Maschine prüfen“: mitten in der Bahn steht der Tisch
# schräg, die Achsen in ihren Grenzen.
import os
import tempfile

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

    from camaddon import PARAMETER_PFAD, beispielmaschine, gui_bearbeitung, gui_reichweite
    from camaddon import halter as hl
    from camaddon import maschinenspeicher as msp
    from camaddon import reichweite as rw
    from camaddon import schlichten3d as s3op
    from camaddon import schlichten3d_bahn as s3
    from camaddon import werkzeuge as wz

    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.TISCH_TISCH)
    pfad_maschine = os.path.join(ordner, "fuenfachs.FCStd")
    asm.Document.saveAs(pfad_maschine)
    msp.merken_datei(pfad_maschine)
    FreeCAD.ParamGet(PARAMETER_PFAD).SetString(rw.ZULETZT_MASCHINE, pfad_maschine)
    yield 300
    t3 = wz.Werkzeug(
        nummer=3,
        name="Kugel 6 kurz",
        art=wz.KUGELFRAESER,
        durchmesser=6.0,
        schneiden=2,
        schneidenlaenge=12.0,
        gesamtlaenge=60.0,
        schneidstoff=wz.VHM,
    )
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
    bibliothek = wz.Bibliothek([wz.standardwerkzeug(), t3])
    halter = hl.aus_vorlage("schrumpf_6")
    halter.kennung = "halter-schrumpf-szenario"
    bibliothek.halter.append(halter)
    t3.halter = halter.kennung
    t3.laenge_spindelnase = float(halter.laenge) + 27.0
    bibliothek.speichern()

    doc = FreeCAD.newDocument("Kavitaet")
    doc.UndoMode = 1
    kav = Part.makeBox(50, 50, 40, V(35, 35, 15))
    kav = kav.makeFillet(10.0, [e for e in kav.Edges if e.BoundBox.ZLength > 1])
    kav = kav.makeFillet(
        8.0,
        [e for e in kav.Edges if abs(e.BoundBox.ZMax - 15) < 1e-6 and e.BoundBox.ZLength < 1e-6],
    )
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeBox(120, 120, 45).cut(kav).removeSplitter()
    doc.recompute()
    FreeCAD.setActiveDocument(doc.Name)
    rund = [
        f"Face{i + 1}"
        for i in range(len(teil.Shape.Faces))
        if s3.ist_freiform(teil.Shape, f"Face{i + 1}")
    ]
    h.pruefe(len(rund) >= 4, f"Rundungen: {rund}")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, rund[0])
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    for name in rund[1:]:
        panel.flaeche_umschalten(name)
    yield 1000
    block = panel.schlichten3d
    yield from h.warte_auf(lambda: block.vorschau is not None, 300000)
    yield 500
    h.pruefe(block.aktiv() and block.fraeser() is not None, "3D-Schlichten ohne Haken")
    weg = block.haken_felder.get("wegkippen")
    h.pruefe(weg is not None and weg.isEnabled() and not weg.isHidden(), "„Wegkippen“ nicht frei")
    if weg is None:
        return
    weg.setChecked(True)
    yield from h.warte_auf(
        lambda: block.vorschau is not None and "weggekippt" in block.ergebnis.text(), 300000
    )
    yield 800
    text = block.ergebnis.text()
    h.pruefe("weggekippt reichen" in text and "dein Fräser steht 27 heraus" in text, f"{text!r}")
    panel.seite_zeigen(2)
    yield 500
    h.bild("1_wegkippen", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = [o for o in job.Operations.Group if s3op.ist_schlichten3d(o)]
    h.pruefe(len(ops) == 1, f"Operationen: {[o.Label for o in job.Operations.Group]}")
    if not ops:
        return
    op = ops[0]
    h.pruefe(op.Wegkippen and not op.Anstellen, f"{op.Wegkippen}, {op.Anstellen}")
    h.pruefe(len(op.Werkzeugachsen) == len(op.Path.Commands) > 100, "Achsen je Satz")

    # --- Auf der Maschine prüfen ------------------------------------------------------------
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 120000)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruef is None:
        return
    yield 1500
    spieler = pruef.abspieler
    fahrt = spieler.abfahrt
    schraeg = [
        i
        for i, s in enumerate(fahrt.stationen)
        if not s.ziel and abs(float(s.rund.get("A", 0.0))) > 15.0
    ]
    h.pruefe(len(schraeg) > 50, f"Stationen mit A über 15°: {len(schraeg)}")
    if schraeg:
        spieler.springe_zu_station(schraeg[len(schraeg) // 2])
    yield 600
    spieler.knopf_hinsehen.click()
    yield 800
    h.bild("2_weggekippt_auf_der_maschine")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
