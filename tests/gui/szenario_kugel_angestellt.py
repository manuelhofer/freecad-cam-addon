# Kugelfräser angestellt, 5 Achsen simultan (W-015, Spezifikation Strategien 16.3 S2; Manuel,
# 2026-10-04: „Ja, so bauen“): eine Platte 60 × 60 × 10 mit Kuppel (Kugel R 25, oben z 20), die
# 5-Achs-Maschine Tisch/Tisch als zuletzt benutzte, ein Kugelfräser Ø 6. Die Kuppel anklicken →
# „Bearbeitung“: die Maschine steht oben, beim 3D-Schlichten der Haken „Anstellen (5 Achsen
# simultan)“ frei, nicht gesetzt. Gesetzt → „Anlegen“: „3D-Schlichten T3“ mit „Anstellen“, um X
# gekippt, je Satz eine Werkzeugachse. Mit dem Standardfräser statt der Kugel: der Haken gesperrt,
# „– geht mit einem Kugelfräser“. „Auf der Maschine prüfen“: mitten in der Bahn steht A schräg,
# C steht.
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
    from camaddon import maschinenspeicher as msp
    from camaddon import reichweite as rw
    from camaddon import schlichten3d as s3op
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
        name="Kugel 6",
        art=wz.KUGELFRAESER,
        durchmesser=6.0,
        schneiden=2,
        schneidenlaenge=12.0,
        gesamtlaenge=60.0,
        schneidstoff=wz.VHM,
    )
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
    wz.Bibliothek([wz.standardwerkzeug(), t3]).speichern()

    doc = FreeCAD.newDocument("Kuppel")
    doc.UndoMode = 1
    platte = Part.makeBox(60, 60, 10)
    kappe = Part.makeSphere(25, V(30, 30, -5)).common(Part.makeBox(60, 60, 15, V(0, 0, 10)))
    teil = doc.addObject("Part::Feature", "Kuppel")
    teil.Shape = platte.fuse(kappe).removeSplitter()
    doc.recompute()
    FreeCAD.setActiveDocument(doc.Name)
    kuppel = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if isinstance(f.Surface, Part.Sphere)
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, kuppel)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    eintrag = panel.maschine()
    h.pruefe(eintrag is not None and eintrag.art == msp.FRAESE_5, f"Maschine: {eintrag}")
    block = panel.schlichten3d
    yield from h.warte_auf(lambda: block.vorschau is not None, 180000)
    yield 500
    h.pruefe(block.aktiv(), "3D-Schlichten ohne Haken")
    h.pruefe(block.fraeser() is not None and block.fraeser().nummer == 3, "nicht T3")
    kasten = block.haken_felder.get("anstellen")
    h.pruefe(kasten is not None, "kein Haken „Anstellen“")
    if kasten is None:
        return
    h.pruefe(kasten.isEnabled() and not kasten.isChecked(), "„Anstellen“ gesperrt oder gesetzt")
    h.pruefe(kasten.text() == "Anstellen (5 Achsen simultan)", f"Haken: {kasten.text()!r}")

    # Mit dem Standardfräser: gesperrt, mit Grund; zurück zur Kugel: frei.
    standard = next(i for i, w in enumerate(block._fraeser) if w.nummer == 1)
    kugel = next(i for i, w in enumerate(block._fraeser) if w.nummer == 3)
    block.wahl_fraeser.setCurrentIndex(standard)
    yield 300
    h.pruefe(
        not kasten.isEnabled() and kasten.text().endswith("– geht mit einem Kugelfräser"),
        f"mit dem Schaftfräser: {kasten.isEnabled()}, {kasten.text()!r}",
    )
    block.wahl_fraeser.setCurrentIndex(kugel)
    yield 300
    h.pruefe(kasten.isEnabled(), "mit der Kugel wieder gesperrt")
    kasten.setChecked(True)
    panel.seite_zeigen(2)
    yield from h.warte_auf(lambda: block.vorschau is not None, 180000)
    yield 800
    h.bild("1_haken_anstellen", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = [o for o in job.Operations.Group if s3op.ist_schlichten3d(o)]
    h.pruefe(len(ops) == 1, f"Operationen: {[o.Label for o in job.Operations.Group]}")
    if not ops:
        return
    op = ops[0]
    h.pruefe(op.Anstellen and str(op.Kippachse) == "X", f"{op.Anstellen}, {op.Kippachse}")
    h.pruefe(
        len(op.Werkzeugachsen) == len(op.Path.Commands) > 100,
        f"{len(op.Werkzeugachsen)} Achsen, {len(op.Path.Commands)} Sätze",
    )

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
        if not s.ziel and abs(float(s.rund.get("A", 0.0))) > 10.0
    ]
    c_werte = {round(float(s.rund.get("C", 0.0)), 3) for s in fahrt.stationen if not s.ziel}
    h.pruefe(len(schraeg) > 100, f"Stationen mit A über 10°: {len(schraeg)}")
    h.pruefe(len(c_werte) == 1, f"C dreht: {sorted(c_werte)[:5]}")
    if schraeg:
        spieler.springe_zu_station(schraeg[len(schraeg) // 2])
    yield 600
    spieler.knopf_hinsehen.click()
    yield 800
    h.bild("2_angestellt_auf_der_maschine")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
