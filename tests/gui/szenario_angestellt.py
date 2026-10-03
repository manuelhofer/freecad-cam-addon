# Kugelfräser angestellt als 3+2 (W-014/W-015, Spezifikation Strategien 16.3 S2): eine Platte
# 60 × 60 × 10 mit Kuppel (Kugel R 25, oben z 20), gespannt im Grundjob auf der 5-Achs-Maschine
# Tisch/Tisch. „Ebene schwenken“ ohne Fläche, „Oder Winkel“: 15° nach 90° → A15 C0. Darin das
# 3D-Schlichten der Kuppel mit einem Kugelfräser Ø 6 – dieselbe Fläche wie senkrecht, nur schneidet
# die Kugel oben nicht mit der Spitze. „Auf der Maschine prüfen“: mitten in der Bahn, das Werkzeug
# steht 15° schräg zur Kuppel; die Kollision prüft Werkzeug, Halter und Maschine.
import os
import tempfile

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

    import Path.Main.Job as PathJob
    from PySide import QtCore

    from camaddon import beispielmaschine, gui_reichweite, gui_schwenken
    from camaddon import job_schnittwerte as js
    from camaddon import maschine as mm
    from camaddon import reichweite as rw
    from camaddon import schlichten3d as s3op
    from camaddon import schwenken as sw
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    ordner = tempfile.mkdtemp()
    asm, maschine = beispielmaschine.lade(beispielmaschine.TISCH_TISCH)
    for ba in mm.betriebsarten(maschine):
        if ba.Art == mm.ART_LINEAR and ba.NcName == "Z1":
            ba.Wechsel, ba.WechselAn = 150.0, True  # Z ganz oben
    pfad_maschine = os.path.join(ordner, "fuenfachs.FCStd")
    asm.Document.saveAs(pfad_maschine)
    yield 300
    kugel = wz.Werkzeug(
        nummer=4, name="VHM Kugel 6", art=wz.KUGELFRAESER, durchmesser=6.0, schneiden=2,
        schneidenlaenge=12.0, gesamtlaenge=60.0,
    )  # fmt: skip
    kugel.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=120, fz=0.05)]
    bibliothek = wz.Bibliothek([kugel])
    bibliothek.speichern()
    ue.uebergeben(bibliothek)

    doc = FreeCAD.newDocument("Kuppel")
    platte = Part.makeBox(60, 60, 10)
    kappe = Part.makeSphere(25, V(30, 30, -5)).common(Part.makeBox(60, 60, 15, V(0, 0, 10)))
    teil = doc.addObject("Part::Feature", "Kuppel")
    teil.Shape = platte.fuse(kappe).removeSplitter()
    doc.recompute()
    FreeCAD.setActiveDocument(doc.Name)
    grundjob = PathJob.Create("Job", [teil])
    grundjob.Label = "Job Kuppel"
    grundjob.Stock.ExtZpos = 0.5
    doc.recompute()
    rw.merke_maschine(grundjob, pfad_maschine)
    doc.saveAs(os.path.join(ordner, "kuppel.FCStd"))
    yield 300

    # --- Ebene aus Winkeln -------------------------------------------------------------------
    Gui.Control.showDialog(gui_schwenken.SchwenkenPanel(grundjob))
    yield 500
    panel = gui_schwenken.SchwenkenPanel.offen
    h.pruefe(panel is not None, "„Ebene schwenken“ öffnet nicht")
    if panel is None:
        return
    panel.feld_neigung.setValue(15.0)
    panel.feld_richtung.setValue(90.0)
    panel.winkel_nehmen()
    panel.haken_bearbeiten.setChecked(False)
    h.pruefe(panel.ergebnis.text().endswith("A15 C0"), f"Ergebnis: {panel.ergebnis.text()!r}")
    h.pruefe(panel.accept() is True, "„OK“ ging nicht")
    yield 800
    ebenen = sw.ebenen_von(grundjob)
    h.pruefe(len(ebenen) == 1, f"Ebenen: {[e.Label for e in ebenen]}")
    if not ebenen:
        return
    ebene = ebenen[0]
    klon = vr.modell(ebene)
    kuppel = [
        f"Face{i + 1}" for i, f in enumerate(klon.Shape.Faces) if isinstance(f.Surface, Part.Sphere)
    ]
    einsatz = kugel.schnittwerte[wz.ALLE][0]
    tc = js.controller_ohne_transaktion(doc, ebene, kugel, einsatz)
    doc.recompute()
    op = s3op.lege_an(ebene, tc, 0.01, flaechen=kuppel)
    doc.recompute()
    h.pruefe(op is not None and len(op.Path.Commands) > 100, "3D-Schlichten in der Ebene ohne Bahn")
    yield 500

    # --- Auf der Maschine prüfen -------------------------------------------------------------
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, grundjob.Name)
    yield 300
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 30000)
    pruefung = gui_reichweite.PruefPanel.offen
    h.pruefe(pruefung is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruefung is None:
        return
    yield 1500
    spieler = pruefung.abspieler
    fahrt = spieler.abfahrt
    stationen = [i for i, s in enumerate(fahrt.stationen) if s.operation == 0 and not s.ziel]
    h.pruefe(len(stationen) > 100, f"Stationen: {len(stationen)}")
    if stationen:
        spieler.springe_zu_station(stationen[len(stationen) // 2])
    yield 600
    spieler.knopf_hinsehen.click()
    yield 800
    h.bild("1_angestellt_nah")
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("2_angestellt_ganz")
    bereich = getattr(pruefung, "kollision", None)
    if bereich is not None and hasattr(bereich, "pruefen"):
        bereich.pruefen()
        yield 500
        urteil = pruefung.urteil_kollision.text()
        h.pruefe(urteil.startswith("Nichts berührt sich"), f"Kollision: {urteil}")
        h.bild("3_kollision", pruefung.form)
